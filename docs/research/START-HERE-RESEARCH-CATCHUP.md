# Start here: what we learned, what works, and how to understand it

Written 2 October 2026 for the team. This is the reading entrance to the experiments, not an audit log. Start with the useful discoveries and the logic behind them. Read the detailed reports afterward, when their vocabulary makes sense.

## 1. Direct answer: did we try GNNs, and were they helpful?

**Yes. We actually trained graph neural networks, saved their weights, generated predictions and compared them with other models. Graph relationships helped.** There are two different groups of experiments:

1. Public Bitcoin transaction data: GCN, a documented GraphSAGE variant, neural embeddings with a tree classifier, and engineered graph-feature trees.
2. Our synthetic address/wallet–transaction–announcing-IP graphs: a trained static typed GNN, a temporal version with GRU memory, a shuffled-relationship control, and temporal embeddings with XGBoost/LightGBM.

The second group is especially relevant to our application because its node types correspond to our evidence. We did not train canonical HGT, TGN or TGAT. Our temporal model is a smaller custom typed message-passing network with memory across observation windows. It runs on CPU at the tested size; those experiments did not need your friend's GPU.

Here is the latest actual address-only replay, R47:

| Model | What it sees | Future-test average precision | Pooled Precision@20 |
| --- | --- | ---: | ---: |
| Local XGBoost | The address's 23 local summaries | 0.0538 | 0.55 |
| Static typed GNN | Address/TX/IP relationships and features | 0.2602 | 0.80 |
| Temporal typed GNN + GRU | Those relationships plus earlier window states | 0.2879 | 0.95 |
| Same temporal architecture, shuffled relationships | Features and memory, but subject relationships misassigned | 0.0778 | 0.45 |
| Temporal embeddings → XGBoost | Learned representation plus local features | 0.2675 | 0.90 |

The useful inference is: **which objects are connected carries information beyond the address's own summary.** The large deterioration after shuffling supports that interpretation. It is a control experiment: change the relationship alignment and see whether the benefit survives.

There is also a strong engineered graph-context tree with **329 inputs**, whose saved canonical address-window AP is **0.3148**. Thus “graph information helps” does not imply “a neural graph model is always the best way to use it.” The GNN's temporal memory is promising; the rich tree gives us a practical, explainable CPU implementation. They are competing ways of extracting useful relational information.

Read the pooled P@20 correctly: 0.95 means 19 of the highest-scoring 20 **address-window decisions across the pooled test** were positive. It does not mean 95% accuracy, 19 people or a 95% success rate in every window. R47's separate test-window P@20 values are 0.65, 1.00 and 0.00; the last window has no positives. This replay used previously consumed synthetic data. Earlier frozen new-world graph tests also produced positive ranking results, discussed in the temporal report.

A naming trap: the old default CLI's optional `--gnn` path is propagation plus SVD feeding LightGBM. That is a fixed graph embedding, **not** these trained neural networks.

### Why AP 0.2879 and Precision@20 95% can both be correct

They measure different parts of the ranking. In the R47 test there are **57,105 address-window decisions and 295 positives**, a prevalence of **0.5166%**. The approximate random-ranking AP reference is therefore 0.0052, not 0.50. Local XGBoost AP 0.0538 is about 10.4 times that prevalence; temporal GNN AP 0.2879 is about 55.7 times it. These ratios provide context, not an independent deployment guarantee.

Precision@20 examines only the first 20 decisions: the temporal GNN retrieves **19 positive decisions and one negative**. Average precision considers the entire ranking: it averages precision at the ranks where positives appear, equivalently summing precision weighted by the increase in recall. Later positives can be spread among many negatives even when the first 20 are excellent. AP is not accuracy or simply the fraction of correct predictions; average precision and trapezoidal PR-AUC are related but not identical calculations.

Those first 19 positives represent **19/295 = 6.44% recall** at a workload of 20 reviews. Thus a useful small queue and incomplete overall recovery can coexist. Pooled test ranking also differs from selecting 20 alerts in every separate window. Do not turn “95% pooled Precision@20” into “95% detection,” guaranteed future precision or person identification.

### Where are LightGBM and stronger graph-feature trees?

The small R47 table is an ablation of local features, aligned graph information and temporal memory. It is **not the complete model comparison**, and the default shipped LightGBM was not rerun as a matched R47 control. Rich graph-feature LightGBM was actually trained in R37:

| Earlier R37 experiment | Test AP | Pooled test Precision@20 |
| --- | ---: | ---: |
| Address XGBoost, 329 graph-context inputs | 0.3148 | 1.00 |
| Address LightGBM, 329 graph-context inputs | 0.2011 | 0.40 |
| CIOH-grouped XGBoost, 329 inputs | 0.3228 | 0.90 |
| CIOH-grouped LightGBM, 329 inputs | 0.2847 | 0.95 |

Address and CIOH rows have different evaluation subjects and cannot be treated as interchangeable scores. R37 is an earlier experiment, not another freshly trained R47 row. Its 329-input LightGBM is also distinct from the shipped 33-input LightGBM. See [the R37 feature recipe and full protocol](ADDRESS-ATOMIC-DETECTION-AND-UNCERTAINTY-ISOLATION.md#r37-stronger-handcrafted-graph-controls).

On public Elliptic data, graph-feature LightGBM achieved **AP 0.6566 and Precision@20 1.00**, versus local LightGBM AP 0.6366. That is another dataset and protocol, with 5.69% labeled-test prevalence; it does not override the synthetic results. See [the public-data comparison](EXTERNAL-GRAPH-MODEL-EXPERIMENT.md).

The positive conclusion is supported: relational information gives useful lead rankings through both neural and tree models. The remaining practical question is how that ranking performs at the declared review budget across independent worlds, without repeatedly counting the same underlying actor. A single complete matched benchmark of the shipped baseline, stronger tree and GNN is needed before choosing a production replacement.

## 2. The most useful architectural discovery

Your original concern was logical: if ownership clustering is wrong, does everything after it become meaningless?

That would be a serious dependency if every operation required a correct owner grouping. We found and implemented a way to separate the questions:

```text
Observed address / transaction / announcement evidence
                      │
          ┌───────────┼──────────────────┐
          ▼           ▼                  ▼
 Activity detection   Ownership          Network-source
 and lead ranking     hypotheses         candidates
          │           │                  │
          └───────────┼──────────────────┘
                      ▼
             Investigator's case
```

Suppose transaction T has inputs A and B, outputs C and D, and is announced by peers P and Q. Even if we cannot establish whether A and B belong to one owner, we still have the observed transaction endpoints, amounts and captured announcements. We can use those relationships to investigate activity associated with A or B.

**Address mode** makes each observed address its own subject. It does not consume JAAL's ownership ledger. We trained models on this representation and tested that inserting corrupt ownership claims cannot change its features or membership. This is an actual implementation boundary, not a reassuring sentence on the website.

Ownership proposals can then help an investigator connect leads without being a prerequisite for finding the leads. SHASTRA can add network evidence independently. If source evidence is insufficient, a money-flow lead can still be useful.

The big improvement is therefore not only a model. It is **containing uncertainty instead of making every layer inherit it**. That is the idea to understand before reading model parameters.

## 3. Vocabulary: the objects our experiments manipulate

| Term | Meaning here | Why it matters |
| --- | --- | --- |
| Address | A blockchain identifier appearing in inputs/outputs | Observable; not automatically a person or entire wallet |
| Transaction / TX | A transaction body identified by TXID | Several capture rows can describe the same TX |
| Announcement | One captured peer/observer/timing event about a TX | This is a network observation, not another payment |
| Peer / announcing IP | A captured node that relayed/announced the TX | Can be a relay rather than its original source |
| Subject | The object receiving one detector score | Can be a singleton address or a proposed owner group |
| Cluster | A grouping inferred from ownership evidence | Useful hypothesis; does not change the original addresses |
| Controller | A true simulated actor recorded in MAYAJAAL's answer key | Available for research evaluation, not directly observed by the deployed detector |
| Campaign | A generated sequence of adversarial fund movements | Lets us evaluate behaviour rather than calling every address permanently illicit |
| Window | A bounded period of observed activity | Defines what evidence was available for a particular decision |
| Snapshot | The graph/features constructed for that decision boundary | Prevents a later event from silently changing an earlier decision |
| Feature | A number describing observed activity or context | A model learns relationships between these inputs and training labels |
| Embedding | A learned vector representing an object's context | Can feed a neural head or a tree; its coordinates are not automatically human-readable |
| Queue | The ordered set of leads offered for review | Converts model scores into investigator workload |
| Support | The observed TXIDs associated with a candidate lead | Lets us measure evidence overlap without knowing true owners |
| Calibration | A fitted mapping or prediction-set construction | Separate from ranking; a high score alone is not established future precision |
| Frozen model | Saved weights/transforms/policy used without refitting on test data | Makes transfer and deployment tests meaningful |
| Replay | Run the saved recipe again and compare outputs | Tests reproducibility; does not create an independent dataset |

### A window, explained logically

Imagine observing transactions from Monday to Wednesday. Divide the observed time span into ten equal-duration intervals, numbered 0 through 9. These windows are **not** ten random buckets and are not necessarily equal numbers of transactions.

In the typed graph experiments:

```text
Time ──────────────────────────────────────────────────────►
   0   1   2   3     4   5       6          7   8   9
  └──── fit ────┘   calibration  validation  └── test ──┘
```

- Fit windows teach model weights and preprocessing statistics.
- Calibration windows fit the later score mapping.
- Validation chooses checkpoints/model settings and queue policies.
- Test windows measure later behaviour using the frozen choices.

At a window's end, a decision can use the declared observations available through that boundary. It cannot use window 8 to build a feature for a window 3 decision. A temporal model can carry an earlier state into a later window, because earlier observations would be available then. Its state must not carry future labels or future observations backward.

An address active in windows 7 and 8 can receive two decisions: `(address A, window 7)` and `(address A, window 8)`. This is why we say **address-window**. Similarly, controller-window retrieval can count the same controller in more than one time period.

Our SHASTRA experiments use a different decision clock: a short candidate horizon, typically five seconds after a TX's first observed announcement, plus strictly earlier history. Do not assume every layer uses the same ten-window graph clock.

## 4. What each detector is doing internally

### 4.1 Local tree: examine the subject's own behaviour

A local detector receives summaries such as how often an address sends, amounts, counterparties, output fan-out, dwell between receiving and sending, fee behaviour and timing burstiness.

These are informative but compressed. Two addresses can have similar totals while occupying different transaction neighborhoods. A local tree cannot distinguish those neighborhoods unless we supply relevant context.

The default application's LightGBM has 33 engineered inputs, including legacy source/typology summaries. The causal experiments use 23 local inputs after excluding ten upstream fields whose historical computation is not part of that causal recipe. **Those two pipelines are not an identical feature comparison.**

### 4.2 Rich graph-context tree: describe the neighborhood explicitly

For the 329-input engine, we keep the 23 local inputs and build a 38-number context for each transaction:

```text
  6 transaction-body values
+ 9 mean announcing-peer values
+23 mean funding-subject values
=38 transaction-context values
```

For the subject's incoming transactions and outgoing transactions separately, we calculate:

- log(1 + number of related transactions);
- mean, standard deviation, minimum and maximum of every context coordinate.

Each direction contributes `1 + 4×38 = 153` inputs. Total: `23 + 153 + 153 = 329`.

Why retain spread and extremes? A mean can hide that most transactions are ordinary while a few have very different fan-out, fees or announcing-peer context. A distribution summary gives the tree a way to see that difference. Incoming and outgoing sides also have different meanings and should not be collapsed into one neighborhood statistic.

The numerical recipe is label-free. We do not insert true controller IDs or “number of illicit neighbors.” Supervised labels teach the classifier only in the fitting partition.

This engine is implemented with frozen native XGBoost artifacts and lightweight numerical inference. It is not a GNN disguised by a different name. It uses graph information through engineered inputs.

### 4.3 Static typed GNN: learn how to combine neighbors

The GNN first maps each node type into a 32-number representation. It uses a separate learned transformation for subject features, TX features and IP features.

Then it builds a TX representation from:

```text
TX's own representation
+ mean message from funding subjects
+ mean message from announcing peers
```

It builds a subject representation from:

```text
subject's own representation
+ mean message from received transactions
+ mean message from spent transactions
```

Funding, receiving and announcing messages have separate learned matrices. That matters because “this peer announced a transaction” and “this address received funds” are different evidence relations. The classifier learns how those messages help the target.

Mean aggregation is an operation, not a magical reconstruction of every path. Its advantage is learning which combinations matter. The rich tree takes the complementary approach: we explicitly preserve selected neighborhood distributions and let the tree learn decisions over them.

### 4.4 Temporal GNN: retain earlier context

The temporal version adds a GRU, a gated recurrent unit. It combines the current subject representation with a pooled earlier state connected through previously observed addresses.

Logically, the gate learns how much earlier information to retain and how much to update using the present window. That can distinguish current behaviour preceded by a different history, even when current totals look alike. Memory continuity follows observed addresses, not a secret true-owner identifier.

Our implementation detaches previous states between windows during training. It is a window-memory model, not a canonical continuous-event TGN. Inside a window, detailed timing is mostly summarized by features; the GRU models history across windows.

### 4.5 Embeddings → XGBoost: separate representation learning from classification

The neural encoder produces a learned 32-number vector. We concatenate it with the 23 local inputs, giving the tree 55 inputs. The encoder learns context; the tree learns a classifier over that context.

This hybrid was actually trained. Its usefulness is an empirical question: the extra encoder can be worthwhile if it improves the chosen workload metric. SHAP on an embedding coordinate explains the tree's use of that coordinate, but does not by itself explain which original graph relationship made the coordinate large. That is why direct engineered graph inputs are attractive for the current explainable CPU lane.

### 4.6 Why shuffled graphs matter

If a graph model improves, the cause could be meaningful relationships, a more flexible classifier or another correlated shortcut. A shuffled control deliberately misassigns subject endpoints while keeping the overall experiment structure. It asks whether the graph's correspondence to the subject actually matters.

R47's temporal AP fell from 0.2879 to 0.0778. That is a useful positive clue about relational signal. It is not a complete proof that we isolated every possible capacity or simulator effect.

## 5. A queue is a separate decision from a model score

Suppose these are the first four candidates. This is a teaching example, **not an experiment result**:

| Candidate | Ranking score | Supporting TXIDs |
| --- | ---: | --- |
| A | 0.94 | T1, T2, T3 |
| B | 0.93 | T1, T2, T3 |
| C | 0.90 | T4, T5 |
| D | 0.88 | T6, T7 |

A plain top-three queue selects A, B and C. But A and B may give the investigator almost the same material to review. An evidence-diverse queue can select A, C and D instead. B still has a score; it was skipped for this review budget because its evidence overlaps too much.

Our implemented overlap measure is Jaccard:

```text
Jaccard(A, B) = count(shared supporting TXIDs)
               / count(TXIDs appearing in either support set)
```

Identical support gives 1; disjoint support gives 0. The implemented policy examines up to 2,000 ranked eligible candidates and greedily keeps up to 20 whose overlap with each already selected lead is at most 0.25. This cap was chosen on validation and frozen for transfer.

Crucially, the selector does **not** know which addresses share a true controller. It acts on observed TX support. Research then attaches hidden controller keys afterward to evaluate whether it retrieved a broader set of suspicious activity.

In two synthetic transfer worlds, the rich-tree diversity policy increased suspicious **controller-window** retrieval from **11 to 33** and **9 to 16** across three future windows. These totals can exceed 20 because there are three window queues. A controller can recur across windows, so they are not counts of distinct people over the entire capture.

This is one of the most useful findings for SIH: **an improved review policy can make the same detector more useful without requiring a larger model.** It also explains why model accuracy is not the whole product.

## 6. Metrics without confusion

**Precision@20:** of the 20 decisions put at the top, how many are actually positive under the declared test label? This connects directly to review workload. It should specify whether the queue is pooled or per window and whether evidence diversity was applied.

**Recall@20:** what share of all positive decisions did those 20 retrieve? High precision can still leave many cases undiscovered.

**Average precision, AP:** summarizes positive retrieval across the score ordering. Useful for rare positives. AP 0.2879 is not 28.79% accuracy. Our reports often use a PR-AUC label for AP; do not silently substitute a differently calculated area.

**Controller/campaign retrieval:** does the review budget cover different underlying simulated activity rather than repeatedly flagging related addresses? This is an evaluation diagnostic using truth, not an officer-visible identity claim.

**Source answered precision and coverage:** among the transactions for which SHASTRA answers, how often is the declared source/operator target correct, and what fraction of eligible transactions receive an answer? This is a different task from AML classification.

**Replay equality:** did a second implementation produce the same features/scores? This tests implementation fidelity, not whether the predictions are true.

The synthetic and Elliptic tasks have different nodes, labels, prevalence and splits. Compare models within a matched experiment; do not compare AP values across unrelated tables as if the highest number identifies the best architecture.

## 7. Positive findings worth understanding first

| Finding | What we actually established | Why it is useful |
| --- | --- | --- |
| Detection can operate without ownership merges | Address-mode models and corruption-isolation checks | JAAL ambiguity need not invalidate AML evidence |
| Relationships contain useful signal | Static/temporal models beat local controls in relevant synthetic experiments; shuffling reduces the gain | Justifies spending effort on the relational representation |
| A strong graph-feature tree is a serious option | Rich address XGBoost AP 0.3148 versus local 0.0538 in the matched canonical test | Useful graph learning need not imply GPU-dependent deployment |
| Temporal graph models are genuine challengers | Actual training and frozen transfer; extended-model P@20 0.55/0.95 versus local 0.30/0.75 on two new worlds | Supports continuing memory/sequence research |
| Queue policy affects investigation yield | Frozen evidence diversity increased controller-window retrieval | Improves use of analyst attention |
| The relational feature idea also works on public Bitcoin data | Matched Elliptic graph-feature LightGBM AP 0.6566 versus local 0.6366 | Evidence beyond the synthetic transaction mechanisms, for that classification task |
| Research artifacts can become usable inference | 324,395 rows across 20 exact feature/score port checks | Supports a portable CPU implementation |
| A lead can carry inspectable evidence | Working queue JSON, SHAP, complete retained TX endpoints, timed peer references and local viewer | Turns a ranked number into a case an officer can examine |
| Selective operator evidence can be useful | Frozen SHASTRA fresh-world answer precision 92.66% and 86.77% at about 5% coverage | A small supported answer set can accompany broader transaction investigation |

The result is a constructive architecture: **preserve observable evidence, score it, choose useful review material, and add ownership/source hypotheses without making them prerequisites.** These are findings under their recorded protocols. They are not claims that every source can be recovered or every result is already the default product.

## 8. What happened across the entire experiment programme?

Use this as a map, then follow the reading order below.

| Research track | Question | Work performed | Where to understand it |
| --- | --- | --- | --- |
| JAAL ownership | How should we propose and evaluate owner links? | Existing heuristics, mixer screening, learned output/change proposals with LR/RF/ExtraTrees/LightGBM, world comparisons, claim provenance | JAAL entity-resolution report; ownership controls |
| Time-correct BUDDHI | What evidence is available at each decision? | Point-in-time partitions, windowed features, chronological model comparisons and saved inference | Snapshot experiment; causal inference report |
| External Bitcoin graph learning | Does graph context help on public labelled TXs? | Local/graph trees, MLP, GCN, SAGE variant, shuffled topology and embedding/tree comparisons | External graph report |
| Synthetic typed/temporal graph learning | Do TX/IP neighborhoods and history improve ranking? | Static encoder, window GRU, hybrid heads, shuffled control, longer training and frozen new-world transfer | Temporal heterogeneous report; R47 replay |
| Ownership-independent detection | Must activity detection depend on clusters? | Address representation, isolation regression, richer controls and new-world tests | Address-atomic report |
| Review workload | Does ranking repeatedly surface the same evidence? | Observable overlap policy and controller-window evaluation | Address-atomic R40; investigative engine |
| SHASTRA | Which network candidates/operator answers are supported? | Causal candidate features, classifier alternatives, calibration, answer gates, frozen world transfer and observer-regime tests | Attribution/independent-world/coverage reports |
| Anomaly lane | Can unusualness provide additional leads? | Isolation Forest, feature autoencoder, graph autoencoder and fusion tests | AML anomaly report; not required for the main positive story |
| MAYAJAAL reproducibility | Can an experiment be reproduced with its actual world? | Effective configuration, historical chain replay and executed-source reconstruction | Config/replay audit |
| Implementation | Can a trained recipe run and produce reviewable cases? | Portable model export, independent feature port, stripped inference, queue construction and browser checks | Investigative engine; architecture audit |

GAT, canonical TGN/TGAT/HGT, larger Transformers and contrastive pretraining are future/researched possibilities, not things we can currently claim to have benchmarked. Named alternatives in a literature table are different from executed experiments.

## 9. Exact reading order for you now

### First pass: build the mental model

1. **This document.** Understand the meanings of subject, window, queue, graph context and model versus review policy.
2. [SIH investigative engine](SIH-INVESTIGATIVE-ENGINE.md). Read “What the research has positively established,” the architecture, exact feature recipe, queue construction and actual implementation. This explains the useful thing you can open and inspect today.
3. [Address-level detection and uncertainty isolation](ADDRESS-ATOMIC-DETECTION-AND-UNCERTAINTY-ISOLATION.md). Start with “The architectural finding,” then R34, R37, R39 and R40. This directly answers your concern that imperfect JAAL makes everything meaningless. R36 explains why address precision and meaningful review yield differ. Read R38 later for the attribution limit; it is not the entrance to the positive story.
4. [Trained temporal heterogeneous graph experiments](TEMPORAL-HETEROGENEOUS-GRAPH-EXPERIMENT.md). First read graph/inputs, neural equations and parameters, controls, and extended-model transfer. This is the actual GNN internals document, not a marketing description.
5. [Latest R47 results](DRISHTI-R47-READABILITY-AND-GRAPH-RESULTS.md). Read “Fresh executed graph benchmark” to understand the latest address-only replay, then the UI changes if you want to connect those results to what you see onscreen.

### Second pass: distinguish research from the product and learn the layers

6. [Production architecture and stack audit](../submission/PRODUCTION-ARCHITECTURE-AND-STACK-AUDIT.md). Read the integration matrix. It tells you which findings are implemented, which are the default and which still need a release handoff.
7. [Technical master](../CHAKRAVYUH-TECHNICAL-MASTER.md). Read sections 1–2 for the evidence model and execution, then 3–12 in stage order. Section 9 explains the 329-feature engine; section 10 explains the neural experiments. Read sections 13–15 for UI/API/deployment. Save the long appendices for checking exact schemas, parameters and code, rather than reading them first.
8. [JAAL entity-resolution research](JAAL-ENTITY-RESOLUTION-RESEARCH.md), followed by [ownership errors and controls](OWNERSHIP-ERROR-AND-TREE-CONTROLS.md). Now revisit how ownership hypotheses work and how their errors affect alternative representations.
9. [SHASTRA independent-world experiment](SHASTRA-INDEPENDENT-WORLD-EXPERIMENT.md). Read architecture and measured outcomes first. Then read [observation-coverage stress](SHASTRA-OBSERVATION-COVERAGE-STRESS.md) to understand why the observation regime belongs to an attribution policy.
10. [External graph experiment](EXTERNAL-GRAPH-MODEL-EXPERIMENT.md). This explains what changed when the task used public Bitcoin transaction data instead of our own synthetic typed graph.

### Third pass: complete the record and prepare the submission

11. [Research synthesis](RESEARCH-SYNTHESIS.md). Treat this as a living historical synthesis: later R34–R45 sections revise earlier assumptions. You now have enough context to understand those revisions without reading them as a list of reasons the project has no value.
12. [Decision and implementation plan](RESEARCH-DECISION-AND-IMPLEMENTATION-PLAN.md). Read how we decide whether to promote a tree, GNN or hybrid using actual investigation metrics.
13. [Experiment journal](EXPERIMENT-JOURNAL.md). This is the chronology/audit trail, **not the best first explanation**. Use it to ask “what happened in R37?” or trace a claim back to a script/report. The adjacent `events.jsonl` is machine-readable audit data, not a learning chapter.
14. [PPT review](../submission/SIH-PPT-REVIEW-AND-REPLACEMENT-COPY.md), then [four submission variants](../submission/SIH-SUBMISSION-VARIANTS.md). These translate the technical work into an evaluator-facing story. They are not substitutes for understanding the models.

If you only read three files today: **this guide → investigative engine → address-atomic report**. Then read the temporal GNN report when you want the learned architecture.

## 10. How to connect the reading to the application

Open DRISHTI's World screen and its investigative lead preview. Select a saved research window, choose a lead and inspect its actual activity, positive/negative model effects, TX endpoints and observed peers.

Ask five questions:

1. What exact subject and window received this score?
2. Which inputs describe its own activity, and which describe its neighbors?
3. Why did the queue retain this lead rather than a higher-scoring overlapping candidate?
4. Which lines are observed money/announcement evidence, and which are ownership/source hypotheses?
5. Which model/artifact produced the result, and is this a research queue or an archived main-pipeline case?

The default active application still uses LightGBM. The optional rich CPU queue viewer and trained temporal experiments are separate. Seeing them beside each other is useful for learning; it must not make their scores or signed packets appear interchangeable.

You have understood the central research when you can explain this sentence in your own words:

> We can rank suspicious observable activity without assuming perfect ownership, use graph context to improve that ranking, choose a less repetitive review queue, and let the investigator inspect the evidence separately from the model's hypotheses.

## Follow-up: can the ranking improve further?

A new [review-budget and tree–GNN blend experiment](RANKING-RECOVERY-AND-TREE-GNN-BLEND.md) combines saved scores using a validation-selected 75% tree / 25% temporal-GNN weight. Its exploratory test AP is .3381, and it retrieves 128 positives within 500 reviews versus 115 for the tree. At 50 reviews the GNN alone is stronger. Read this after the graph report to understand how complementary signals can help, and why the operating review budget matters.
