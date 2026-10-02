"""Research utilities; no production stage imports this package."""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def log(event, **details):
    with Path('docs/research/events.jsonl').open('a') as stream:
        stream.write(json.dumps({'utc_epoch': time.time(), 'event': event, **details}) + '\n')


def ranking(y, score):
    y, score = np.asarray(y, dtype=int), np.asarray(score, dtype=float)
    order = np.argsort(-score, kind='stable')
    result = {'n':len(y), 'positives':int(y.sum()), 'prevalence':float(y.mean())}
    for k in (20,50):
        available=min(k,len(y)); hits=int(y[order[:available]].sum())
        result[f'p_at_{k}']=hits/available if available else None
        result[f'hits_at_{k}']=hits
        result[f'r_at_{k}']=hits/int(y.sum()) if y.sum() else None
    if 0 < y.sum() < len(y):
        result.update(ap=float(average_precision_score(y,score)),auc=float(roc_auc_score(y,score)))
    else:
        result.update(ap=None,auc=None)
    if np.all((score>=0)&(score<=1)):
        result['brier']=float(brier_score_loss(y,score))
    return result


class Partition:
    def __init__(self, addresses):
        self.parent={a:a for a in addresses}
        self.size={a:1 for a in addresses}
        self.rejected=0

    def find(self,a):
        while self.parent[a]!=a:
            self.parent[a]=self.parent[self.parent[a]]
            a=self.parent[a]
        return a

    def merge(self,a,b,cap=None):
        if a not in self.parent or b not in self.parent: return
        x,y=self.find(a),self.find(b)
        if x==y: return
        if cap is not None and self.size[x]+self.size[y]>cap:
            self.rejected+=1;return
        if self.size[x]<self.size[y]:x,y=y,x
        self.parent[y]=x;self.size[x]+=self.size[y]

    def groups(self):
        out=defaultdict(list)
        for a in self.parent:out[self.find(a)].append(a)
        return list(out.values())


def partition_metrics(groups, owners, universe=None):
    """Exact contingency metrics in O(n), including singleton coverage, never O(n²) pairs."""
    allowed=set(owners) if universe is None else set(universe)&set(owners)
    true_counts=Counter(owners[a] for a in allowed)
    predicted=shared=0; bprecision=brecall=0.0; impure=non_single=0; maxsize=0
    covered=set()
    for group in groups:
        g=set(group)&allowed
        if not g:continue
        if covered&g:raise ValueError('partition overlap')
        covered|=g
        counts=Counter(owners[a] for a in g);n=len(g)
        predicted+=n*(n-1)//2
        shared+=sum(c*(c-1)//2 for c in counts.values())
        bprecision+=sum(c*c/n for c in counts.values())
        brecall+=sum(c*c/true_counts[o] for o,c in counts.items())
        if n>1:non_single+=1;impure+=int(len(counts)>1)
        maxsize=max(maxsize,n)
    # Unlinked observed addresses are singleton predicted clusters, not missing rows.
    for a in allowed-covered:
        bprecision+=1;brecall+=1/true_counts[owners[a]]
    true_pairs=sum(n*(n-1)//2 for n in true_counts.values())
    p=shared/predicted if predicted else 0.;r=shared/true_pairs if true_pairs else 0.
    return {'n_addresses':len(allowed),'predicted_pairs':predicted,'true_pairs':true_pairs,
            'shared_pairs':shared,'pair_precision':p,'pair_recall':r,
            'pair_f1':2*p*r/(p+r) if p+r else 0.,
            'b3_precision':bprecision/len(allowed),'b3_recall':brecall/len(allowed),
            'n_non_singleton':non_single,'n_impure_non_singleton':impure,
            'max_cluster_size':maxsize}
