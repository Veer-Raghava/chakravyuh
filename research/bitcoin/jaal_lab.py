"""Time-split learned ownership links and heuristic/partition ablations."""
from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from chakravyuh.jaal import cluster, mixer
from common import Partition, digest, log, partition_metrics, ranking, save

FEATURES=['n_in','n_out','log_input','log_output','output_fraction','min_input_fraction',
          'fee_fraction','script_match','all_input_scripts_match','fresh_output',
          'output_reuses_input','round_1k','round_10k','round_100k','log_output_gap',
          'input_amount_cv','equal_outputs','output_index_fraction']


def candidates(txs, addresses, owners):
    facts={r['address']:r for r in addresses.iter_rows(named=True)}
    records=[]; multi=[]
    for tx in txs.sort('first_seen_us','txid').iter_rows(named=True):
        inputs=sorted(set(tx['input_addresses']))
        if tx['is_coinbase'] or not inputs:continue
        itypes=[facts[a]['script_type'] for a in inputs]
        amounts=tx['input_amounts'];total=sum(amounts)
        outs=tx['output_amounts'];equal=len(set(outs))<len(outs)
        input_owners={owners.get(a) for a in inputs}
        pure=len(input_owners)==1 and None not in input_owners
        parent=inputs[0]
        m=[]
        for j,(a,amt) in enumerate(zip(tx['output_addresses'],outs,strict=True)):
            other=[v for k,v in enumerate(outs) if k!=j]
            typ=facts[a]['script_type'];match=typ in itypes
            fresh=facts[a]['first_seen_us']>=tx['first_seen_us']
            x=[len(inputs),len(outs),np.log1p(total),np.log1p(amt),amt/max(total,1),
               min(amounts)/max(amt,1),tx['fee_sats']/max(total,1),int(match),
               int(len(set(itypes))==1),int(fresh),int(a in inputs),
               int(amt%1000==0),int(amt%10000==0),int(amt%100000==0),
               np.log1p(abs(amt-np.mean(other))) if other else 0.,
               float(np.std(amounts)/max(np.mean(amounts),1)),int(equal),j/max(len(outs)-1,1)]
            row={'txid':tx['txid'],'time':tx['first_seen_us'],'src':parent,'dst':a,
                 'x':x,'y':int(pure and owners.get(a)==owners.get(parent)),
                 'eligible':not (equal and len(outs)>=3 and len(inputs)>=2)}
            records.append(row);m.append(row)
        multi.append({'tx':tx,'rows':m,'pure':int(pure)})
    return records,multi


def models(seed):
    return {
      'logistic':make_pipeline(StandardScaler(),LogisticRegression(max_iter=500,random_state=seed)),
      'random_forest':RandomForestClassifier(n_estimators=150,min_samples_leaf=8,n_jobs=4,random_state=seed),
      'extra_trees':ExtraTreesClassifier(n_estimators=150,min_samples_leaf=8,n_jobs=4,random_state=seed),
    }


def threshold(y,p,target=.99):
    # Validation only. No claim of a statistical 99% lower confidence guarantee.
    feasible=[]
    for cut in [.5,.7,.8,.9,.95,.97,.99,.995,.999]:
        chosen=p>=cut
        if chosen.sum()>=50 and y[chosen].mean()>=target:feasible.append(cut)
    return min(feasible) if feasible else 1.01


def run(run_id,out):
    started=time.perf_counter();root=Path('data/generated')/run_id
    ap=root/'normalised/addresses.parquet';tp=root/'normalised/transactions.parquet'
    truth=Path('ground_truth')/run_id/'entities.parquet'
    addresses=pl.read_parquet(ap);txs=pl.read_parquet(tp)
    entities=pl.read_parquet(truth)
    owners={a:r['entity_id'] for r in entities.iter_rows(named=True) for a in r['addresses']}
    universe=addresses['address'].to_list();owned=set(universe)&set(owners)
    records,multi=candidates(txs,addresses,owners)
    times=np.array([r['time'] for r in records]);first,last=times.min(),times.max()
    c1=int(first+.6*(last-first));c2=int(first+.8*(last-first))
    fit=times<c1;val=(times>=c1)&(times<c2);test=times>=c2
    x=np.array([r['x'] for r in records],dtype=np.float32);y=np.array([r['y'] for r in records])
    new_addresses={r['address'] for r in addresses.iter_rows(named=True) if r['first_seen_us']>=c2}
    mi=cluster.common_input_edges(txs);ch=cluster.change_edges(txs)
    policies={'singleton':[], 'current_both':mi.select('src','dst').rows()+ch.select('src','dst').rows(),
              'common_input_only':mi.select('src','dst').rows(), 'change_only':ch.select('src','dst').rows()}
    policies={k:[(a.removeprefix('addr:'),b.removeprefix('addr:')) for a,b in v] for k,v in policies.items()}
    rules={'fresh_unique':lambda r:r['x'][9] and not r['x'][10],
           'script_unique':lambda r:r['x'][7] and r['x'][8] and not r['x'][10],
           'optimal_change':lambda r:r['x'][0]>=2 and r['x'][5]>1 and not r['x'][10],
           'fresh_script_consensus':lambda r:r['x'][9] and r['x'][7] and r['x'][8] and not r['x'][10]}
    for name,predicate in rules.items():
        links=[]
        for tx in multi:
            r=[r for r in tx['rows'] if r['eligible'] and predicate(r)]
            if len(r)==1:links.append((r[0]['src'],r[0]['dst']))
        policies[name]=policies['common_input_only']+links
    scores={};trained={}
    for name,model in models(42).items():
        t=time.perf_counter();model.fit(x[fit],y[fit]);p=model.predict_proba(x)[:,1]
        cut=threshold(y[val],p[val]);trained[name]=(p,cut)
        scores[name]={'test':ranking(y[test],p[test]),'threshold':cut,'fit_seconds':time.perf_counter()-t,
                      'validation':ranking(y[val],p[val])}
    ds=lgb.Dataset(x[fit],label=y[fit],feature_name=FEATURES)
    t=time.perf_counter();booster=lgb.train({'objective':'binary','verbosity':-1,'num_threads':4,'seed':42,
                      'num_leaves':31,'min_data_in_leaf':30,'learning_rate':.05},ds,num_boost_round=180)
    p=booster.predict(x,num_threads=4);cut=threshold(y[val],p[val]);trained['lightgbm']=(p,cut)
    scores['lightgbm']={'test':ranking(y[test],p[test]),'validation':ranking(y[val],p[val]),
                       'threshold':cut,'fit_seconds':time.perf_counter()-t}
    out.mkdir(parents=True,exist_ok=True);booster.save_model(str(out/'change-lightgbm.txt'))
    for name,(p,cut) in trained.items():
        links=[]
        for tx in multi:
            options=[(p[i],r) for i,r in enumerate(records)] if False else []
        # One learned output per transaction, with a validation-selected cutoff.
        predicted={}
        for score,r in zip(p,records,strict=True):
            if not r['eligible'] or score<cut:continue
            if r['txid'] not in predicted or score>predicted[r['txid']][0]:predicted[r['txid']]=(score,r)
        links=[(r['src'],r['dst']) for _,r in predicted.values()]
        policies['mi_plus_'+name]=policies['common_input_only']+links
        # An independent learned-link partition reveals contamination already caused by CIOH.
        policies['only_'+name]=links
    # Guarded CIOH: reject bulk inputs. This is a sensitivity experiment, not a calibrated probability.
    restricted=mi
    good={r['tx']['txid'] for r in multi if r['tx']['n_in']<=3}
    guarded=cluster.common_input_edges(txs.filter(pl.col('txid').is_in(good))).select('src','dst').rows()
    policies['small_input_only']=[(a[5:],b[5:]) for a,b in guarded]
    partitions={};groups_by_policy={}
    for name,links in list(policies.items()):
        for cap in ([None,128] if name in ['current_both','mi_plus_lightgbm'] else [None]):
            policy=name+('_cap128' if cap else '')
            part=Partition(universe)
            for a,b in links:part.merge(a,b,cap)
            groups=part.groups();groups_by_policy[policy]=groups
            partitions[policy]={'all_observed':partition_metrics(groups,owners,owned),
                 'new_test_addresses':partition_metrics(groups,owners,new_addresses),'rejected_merges':part.rejected,
                 'candidate_link_precision':sum(owners.get(a)==owners.get(b) for a,b in links)/len(links) if links else None}
    mi_edge=policies['common_input_only'];ch_edge=policies['change_only']
    collaboration={'multiinput_transactions':sum(r['tx']['n_in']>=2 for r in multi),
       'mixed_owner_multiinput_transactions':sum(r['tx']['n_in']>=2 and not r['pure'] for r in multi),
       'mixer_rule_true':txs.filter(mixer.is_mixer()).height,
       'mi_edge_precision':sum(owners.get(a)==owners.get(b) for a,b in mi_edge)/len(mi_edge),
       'change_edge_precision':sum(owners.get(a)==owners.get(b) for a,b in ch_edge)/len(ch_edge)}
    result={'run':run_id,'features':FEATURES,'split_us':[c1,c2],'rows':{'fit':int(fit.sum()),'validation':int(val.sum()),'test':int(test.sum())},
       'models':scores,'partitions':partitions,'failure_diagnosis':collaboration,
       'hashes':{str(f):digest(f) for f in [ap,tp,truth]},'elapsed_seconds':time.perf_counter()-started,
       'scope':'exploratory within-seed temporal holdout; global partitions are retrospective; threshold tuned on validation only'}
    save(out/'jaal-results.json',result)
    save(out/'change-model-manifest.json',{'features':FEATURES,'threshold':trained['lightgbm'][1],
         'split_us':[c1,c2],'artifact_sha256':digest(out/'change-lightgbm.txt'),'source_hashes':result['hashes']})
    log('jaal_complete',run=run_id,out=str(out),seconds=result['elapsed_seconds'])
    return groups_by_policy,result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',default='agency-v2');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();run(args.run,args.out)
