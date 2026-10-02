# SIH title, abstract and description variants

2 October 2026. Four complete approaches, written against the inspected implementation. The user-supplied limits are title 100, abstract 10,000 and description 50,000 characters. Copy only the field text, not the editorial headings. The descriptions are intentionally much shorter than the maximum: additional characters are useful only when they add evidence or explain a decision.

## How to choose

A leads with the investigator workflow and is the recommended base. B foregrounds the strongest architectural insight. C gives the research/experimentation story more space. D foregrounds offline custody and reproducibility. These are four different priorities, not four claims of different products. All distinguish the default model from the working optional engine.

Use one abstract as a complete narrative. For the description, combine sections only after removing repeated pipeline explanations. Keep the figure units and engine-status sentences when transferring measured results. No version claims guaranteed source/person identification, a validated universal confidence threshold, deployed HGT/TGN or an already shipped offline container.

The source-based submission rationale and PPT edits are in [the review](SIH-PPT-REVIEW-AND-REPLACEMENT-COPY.md). No verified SIH rule establishes that filling character limits improves selection.

## Version 1: A — Investigator workflow

Title: 74 characters. Abstract: 2041. Description: 6934.

### Idea title

CHAKRAVYUH: Offline Bitcoin Evidence Fusion and Investigative Lead Ranking

### Abstract / summary

CHAKRAVYUH connects Bitcoin fund movement with captured network observations and turns bulk metadata into prioritized, explainable investigative leads. Built for offline Linux operation, it gives an investigator a direct route from a flagged address to its transactions, observed peers, model reasons and preserved evidence.

The prototype ingests CSV, JSON and XML, hashes original files, records rejected rows, and separates transaction bodies from repeated announcements. Its typed graph links addresses, transactions, announcing IPs and network operators. DRISHTI presents connected maps, paged money traces, source candidates and ranked leads. PRAMAAN produces signed case JSON and accompanying PDF documents with input hashes and replay information.

The default detection engine combines LightGBM with engineered behaviour, graph and network features and SHAP explanations. Our working optional CPU engine adds 329 address–transaction–announcer inputs and an evidence-diverse review queue. In two synthetic transfer tests, a frozen queue policy increased suspicious controller-window retrieval from 11 to 33 and from 9 to 16 across three future windows, improving the use of investigator attention.

We also tested the approach on public Elliptic Bitcoin data. Graph-feature LightGBM achieved average precision 0.6566 and 20 illicit transactions among its pooled top 20, compared with 0.6366 AP for matched local-feature LightGBM. This is a separate public-data experiment; synthetic queue results count controller-window retrieval, which can repeat an actor across windows.

A central design choice keeps activity detection independent of ownership clustering. Address-level transaction evidence remains usable while ownership and network-source hypotheses are investigated. Trained temporal graph models provide a measured research lane alongside the working CPU engines.

The result is an offline evidence workflow: learned prioritization, connected supporting observations, inspectable explanations and a verifiable case handover.

### Idea description

1. The investigation problem

The problem statement requires more than transaction classification. Blockchain records show which addresses fund and receive a transaction; captured network records show who announced that transaction to an observer, on which port and at what time. Repeated announcements are not new payments, and an announcing peer is not automatically the sender. An investigator needs both evidence layers in one view, with an ordered set of leads and enough supporting material to review each one.

CHAKRAVYUH is our offline Linux solution. DRISHTI is its investigation interface. The output is a ranked, explainable case lead, with observed money movement, captured network support, ownership hypotheses where available, and a record that can be exported and checked locally.

2. What happens to an input capture

KAVACH accepts bulk CSV, JSON/JSONL and XML. It hashes original files before parsing, retains the originals, and records accepted and rejected rows with reasons. SETU normalizes timestamps to UTC microseconds and values to integer satoshis. It separates transaction bodies from announcement events, so many observations of one TXID remain network evidence without becoming many payments. Local ASN/GeoIP lists supply network context when available; missing information remains explicit.

JAAL builds a typed graph of addresses, transactions, peers and network operators. Input and output edges retain amounts; announcement edges retain their observation meaning. Common-input and change rules propose likely shared ownership while preserving original address nodes and evidence. We do not need to erase the underlying graph to display a grouped view.

3. Learned detection and network evidence

The main BUDDHI pipeline uses a trained 33-feature LightGBM model. Its inputs cover activity, amounts, counterparties, fan-out, dwell, fee behaviour, ownership evidence and available source/typology summaries. SHAP supplies model-level reasons. SHASTRA separately ranks network-source candidates using arrival evidence and network history, with operator-level summaries and insufficient-evidence states. A useful AML lead can exist even when no reliable originating host can be named.

Our newer optional CPU engine scores explicit address/transaction/announcer decision windows using 329 engineered inputs. It combines local behaviour with typed neighborhood distributions and frozen XGBoost artifacts, and records positive and negative TreeSHAP contributions. Its runtime consumes normalized observations and a saved model, without reading evaluation answer keys or importing neural training code. This engine is implemented as an optional CLI and a World-screen local investigation viewer; the default stage pipeline remains LightGBM while the release handoff is completed.

4. A queue designed around investigator attention

Simply taking the highest-scoring addresses can spend several review slots on the same underlying transaction evidence. Our optional queue compares each candidate's observed supporting TXIDs and limits overlap before choosing up to 20 leads. This selection uses evidence, not hidden owner labels. Each selected lead includes a bounded graph with complete inputs/outputs for the retained transactions, exact amounts and captured announcing-peer observations.

We measured this choice in two synthetic transfer worlds. With the queue policy frozen, suspicious controller-window retrieval across three future windows improved from 11 to 33 and from 9 to 16. A controller may recur in another window; the finding is better retrieval per review budget in these tests, not verified identification of 33 people.

5. Evidence-driven model selection

MAYAJAAL gives us configurable transaction campaigns and captured propagation with separate ground truth. We use chronological fit, calibration, validation and test windows, graph-shuffling controls and independent generated worlds. We have actually trained tabular alternatives, typed static/temporal graph models and embedding/tree hybrids, rather than choosing a GNN because its name sounds stronger.

On our canonical synthetic address-window protocol, rich graph-context XGBoost achieved average precision 0.3148 against 0.0538 for the matched local-only tree. Separate public Elliptic experiments also compare local and graph-summary features. Public Bitcoin classification and synthetic network attribution are evaluated separately because their targets, labels and splits differ. Accuracy alone is insufficient for rare suspicious activity; Precision@20/50, average precision, retrieval diversity and evidence quality matter to the investigation workflow.

On public Elliptic Bitcoin data, our separately trained graph-feature LightGBM achieved average precision 0.6566 and 20 illicit transactions among its pooled top 20, versus AP 0.6366 for matched local-feature LightGBM. The temporal test comprised 11,184 labeled transactions, including 636 illicit; unknown labels remained graph context. Public transaction classification and synthetic address-window detection are separate experiments with different targets and prevalence.

6. What the officer sees and retains

DRISHTI connects the globe, transaction/peer map, paged money trace, origin candidates, ranked leads and proof views. A case contains model reasons and counter-evidence, including plausible benign explanations or weak source separation. The officer can examine a transaction's complete endpoints without a cluttered graph being treated as the entire evidence record. Run selection and saved research queues preserve which capture and engine produced the view.

PRAMAAN creates canonical JSON, deterministic PDFs, an Ed25519 signature, custody hashes and replay metadata for legacy pipeline cases. The current interface exports archived signed packets; a new research queue remains separately identified and does not inherit an old signature. The signature protects artifact integrity; follow-up investigation determines what the observations mean.

7. Practical deployment and next release

Core execution is CPU-based and requires no cloud service or CUDA. A stripped replay of the optional graph-context engine produced the same 20-lead packet in 2.69 seconds with 788.8 MiB peak process memory on the tested capture. Local browser interactions have been checked offline with zero external requests. These measurements establish a working prototype workload, not a universal performance guarantee.

The next release connects the frozen decision-window scorer to active VAANI cases and new PRAMAAN packets, then verifies a complete offline installation on a clean Linux host. The trained temporal graph model remains a controlled challenger until it improves the same review-budget workflow. Our contribution is a coherent investigation process: learned detection, connected evidence, explicit model effects, reviewable doubts and local artifact custody.

## Version 2: B — Ownership-independent intelligence

Title: 78 characters. Abstract: 2093. Description: 6812.

### Idea title

CHAKRAVYUH: Cluster-Independent Bitcoin Detection with Linked Network Evidence

### Abstract / summary

CHAKRAVYUH detects suspicious observable Bitcoin activity while keeping wallet ownership and network-source attribution as separate investigation questions. Its central architectural choice is address-level detection: a lead can be supported by transactions and captured announcements before an investigator resolves who controls the addresses.

Our offline Linux prototype ingests CSV/JSON/XML metadata, preserves input hashes and row-accounting records, normalizes amounts and timestamps, and builds a typed address–transaction–peer graph. The default LightGBM detector ranks activity with SHAP reasons. A working optional CPU engine learns from 329 local and typed-neighborhood inputs, with the ownership ledger excluded in address mode. Ownership proposals remain inspectable links in the evidence graph.

We tested this separation by corrupting ownership claims and checking that address-mode membership and features remained unchanged. The graph-context XGBoost model then placed 20 positive address-window decisions in its pooled top 20 on the canonical synthetic future-window test. Its AP was 0.3148, compared with 0.0538 for the local-feature control at 0.52% positive prevalence. These are synthetic decision-level measurements, with repeated actors possible.

A separate public Elliptic comparison achieved AP 0.6566 with graph-feature LightGBM, versus 0.6366 for matched local LightGBM. An independent CPU inference port reproduced features and scores exactly across 324,395 rows in 20 checks. Actual static and temporal graph models were also trained and compared.

DRISHTI connects ranked leads to money endpoints, captured IP/port/timing observations, model contributions and counter-evidence. PRAMAAN preserves main-pipeline cases as signed JSON and accompanying PDFs with custody and replay details. The optional engine has its own executable CLI and local evidence-queue viewer.

The contribution is a practical investigation architecture in which uncertain attribution does not erase useful detection: each lead retains the observed support needed for review and follow-up.

### Idea description

1. Why the evidence model matters

Bitcoin address grouping, suspicious-behaviour detection and network-source attribution answer different questions. Combining them into a single chain of assumptions can make one incorrect ownership merge distort every downstream result. The problem statement calls for correlated, explainable investigative leads. It does not require that every lead depend on recovering a perfect wallet identity first.

CHAKRAVYUH preserves the observations and makes these questions separable. An investigator can examine address-level money movement, inspect a proposed owner group, and review a network-source candidate without treating one as proof of the others. That architecture makes uncertainty manageable within a concrete investigation workflow.

2. From supplied metadata to linked evidence

KAVACH handles CSV, JSON/JSONL and XML input, hashes the original bytes before parsing, and accounts for row acceptance or rejection. SETU normalizes amounts to integer satoshis and timestamps to UTC microseconds. It stores one transaction body per consistent TXID and separate announcement rows containing the observed peer, port, observer and time. Conflicting transaction bodies are set aside instead of silently selecting whichever version arrived last.

JAAL constructs addresses, transactions, peers and ASN nodes with typed links. A payment is represented through address-to-transaction inputs and transaction-to-address outputs. A captured peer announcement is a network observation. Common-input and change proposals add reversible ownership evidence. A derived grouped view does not delete the addresses or turn heuristic weights into verified owner probabilities.

3. Detection independent of ownership recovery

The existing product scores subjects with a 33-feature LightGBM model and explains them with SHAP. Our implemented decision-window engine also supports address mode: one address per subject, with the ownership ledger excluded. It combines 23 local activity features with incoming/outgoing typed neighborhood summaries into 329 inputs for a frozen CPU XGBoost model.

The context includes transaction size/shape, fees, announcing-peer activity and network class, and adjacent funding-subject features. No neighbor labels are inserted. Training-only transformations and later calibration are stored with the model. At inference, the scorer reads only normalized observation artifacts and its saved manifest. Native TreeSHAP contributions must reconstruct the raw model margin before an output is accepted.

This engine has its own CLI and a working local evidence-queue viewer in DRISHTI's World screen. It is an implemented candidate, not a claim that the main LightGBM stage has already been replaced. The two routes are labelled so research results cannot be mistaken for the active archived case model.

4. What we tested

We tested ownership rules and alternative link proposals, point-in-time partitions, corrupted-ledger isolation, local and graph-context trees, actual typed neural models, window-linked temporal memory, graph-shuffling controls, and embedding/tree hybrids. Address mode demonstrates a practical way to contain ownership error rather than asking a neural model to make an uncertain cluster magically correct.

The rich graph-context tree obtained average precision 0.3148 on the canonical synthetic address-window future test, versus 0.0538 for the matched local-only tree. The independent lightweight inference port matched engineered features and model scores exactly for 324,395 rows over 20 checks. These tests support a working deployment path; they do not establish real-network sender-identification accuracy.

In the separate temporal graph experiment, learned relation context showed useful signal, and shuffled assignments reduced ranking quality. We keep that model as a challenger and compare it with strong engineered graph features rather than a weak tabular straw man. Public Elliptic experiments provide a separate Bitcoin transaction-classification check; their results are not pooled with synthetic IP-origin tests.

On public Elliptic Bitcoin data, our separately trained graph-feature LightGBM achieved average precision 0.6566 and 20 illicit transactions among its pooled top 20, versus AP 0.6366 for matched local-feature LightGBM. The temporal test comprised 11,184 labeled transactions, including 636 illicit; unknown labels remained graph context. Public transaction classification and synthetic address-window detection are separate experiments with different targets and prevalence.

5. Source evidence is a parallel path

SHASTRA uses arrival timing, observer context and earlier peer history to rank captured candidates and summarize operator-level evidence. An announcing IP can be a relay, VPN endpoint or Tor exit. The originating peer may not appear in the observations. The interface therefore presents source candidates and insufficient-evidence states rather than equating the highest score with a person's identity.

Importantly, a source refusal does not remove the address/TX evidence or suppress a useful AML lead. The investigator can continue reviewing fund movements and request additional evidence where necessary. This is the operational value of keeping the two layers connected while retaining their different meanings.

6. The review queue and evidence record

VAANI's main route produces ranked explanations and mandatory counter-evidence. The newer investigation queue additionally limits overlapping transaction support, so high scores from the same local evidence do not occupy the entire review budget. Each lead carries exact input/output amounts, bounded transaction context, captured timing/ports, signed positive/negative model effects and explicit truncation information.

DRISHTI makes that material accessible through linked visual and textual views. PRAMAAN signs canonical case JSON and produces PDFs with input hashes and replay information for the main pipeline. Research-queue exports stay distinct from those signed packets until the next adapter is released.

7. Deployment and contribution

The core stack is Python, Polars/Arrow, rustworkx and CPU tree models, with React/TypeScript/Three.js for the local interface. Runtime evidence stays local. The small trained graph model can also run on CPU; CUDA is not a prerequisite for the tested prototype. Complete clean-host packaging and automatic routing of the new engine to active signed cases are the next release steps.

The contribution is a tested architecture in which a lead can remain useful even when another inference layer cannot answer. An officer receives observable support, a learned ranking, explicit hypotheses and a reproducible record, instead of being asked to trust a chain of opaque certainty claims.

## Version 3: C — Experiment-driven engineering

Title: 74 characters. Abstract: 2091. Description: 7153.

### Idea title

CHAKRAVYUH: Experiment-Backed Bitcoin AML and Explainable Offline Evidence

### Abstract / summary

CHAKRAVYUH is an offline Bitcoin investigation prototype improved through executed model, graph and queue experiments. It correlates bulk transaction metadata with captured IP/port/timing observations, ranks suspicious activity using trained ML, and exposes the supporting evidence through DRISHTI.

We built MAYAJAAL as a configurable synthetic test harness with separate ground truth. Experiments compared ownership representations, causal graph features, tabular models, trained static and temporal GNNs, embedding/tree hybrids and evidence-overlap policies. The main practical findings were that relational context improves detection, address-level detection can avoid dependence on ownership heuristics, and reducing repeated transaction evidence increases investigative coverage.

The working 329-feature CPU graph-context XGBoost engine retrieved 20 positives in its pooled top 20 on the canonical synthetic address-window test. Its average precision was 0.3148 against 0.0538 for the local-feature tree at 0.52% positive prevalence. In two transfer worlds, a frozen diversity policy increased suspicious controller-window retrieval from 11 to 33 and 9 to 16 across three windows. These units can repeat an actor and do not imply person identification.

We separately evaluated public Elliptic Bitcoin transactions: graph-feature LightGBM achieved AP 0.6566 and pooled Precision@20 of 100%, versus AP 0.6366 for matched local LightGBM. A portable inference implementation reproduced features and scores exactly across 324,395 rows in 20 checks.

The default application uses LightGBM with SHAP. The optional graph-context engine has a CLI and a local World-screen investigation viewer; trained temporal models remain controlled challengers. KAVACH seals inputs, SETU separates transactions and announcements, JAAL links evidence, SHASTRA ranks source candidates, VAANI presents leads, and PRAMAAN signs case JSON with accompanying PDF documents.

The proposal offers a working CPU system and a reproducible improvement process, measured by useful evidence retrieved per review budget.

### Idea description

1. The idea

CHAKRAVYUH turns supplied Bitcoin transaction/network metadata into ranked, explainable investigative leads on an offline Linux workstation. The officer can follow a lead from model score to money-flow evidence, captured network observations and a preserved case artifact. The architecture is built to support investigation rather than to display an impressive model name.

2. A benchmark that exposes the hard parts

MAYAJAAL generates transaction activity, configurable laundering-like campaigns and captured P2P propagation. Observable files and ground-truth ownership/campaign/source records are kept separate. It lets us ask distinct questions: whether ownership links are accurate, whether a detector retrieves suspicious behaviour, whether captured source candidates are useful, and whether a review queue repeatedly presents the same evidence.

The simulator is a test harness, not a substitute for real-world validation or a prerequisite for operational ingestion. We preserve ordinary and evasive scenarios and record configurations. Independent generated seeds test transfer within those mechanisms; public Elliptic data provides a separate transaction-classification experiment. We do not compare results across those different tasks as though they came from one leaderboard.

On public Elliptic Bitcoin data, our separately trained graph-feature LightGBM achieved average precision 0.6566 and 20 illicit transactions among its pooled top 20, versus AP 0.6366 for matched local-feature LightGBM. The temporal test comprised 11,184 labeled transactions, including 636 illicit; unknown labels remained graph context. Public transaction classification and synthetic address-window detection are separate experiments with different targets and prevalence.

3. Experiments that changed our architecture

We investigated common-input/change ownership rules, point-in-time graph partitions and alternative learned link proposals. We trained tabular classifiers, richer graph-feature tree models, supervised static graph models, custom typed temporal graph/GRU models and embedding-to-tree hybrids. Shuffled-relation controls test whether graph assignment carries signal. Isolation Forest and reconstruction models were also tested; unusualness alone was not promoted into the AML score simply because it is an AI method.

One practical insight is that detection does not need a perfect ownership partition. Address-only graph models can consume address/TX/announcer evidence without consuming the ownership ledger. That lets an investigator review suspicious observable activity while keeping proposed owner groups as separate evidence.

Another finding concerns queue quality. Multiple highly ranked addresses can share the same transaction context. We implemented a label-free evidence-overlap cap and froze it before transfer tests. Across three future windows in two synthetic worlds, suspicious controller-window retrieval increased from 11 to 33 and from 9 to 16. This metric counts controller-window retrieval, so it is not a claim of finding 33 distinct people.

4. The deployable model path

The existing main BUDDHI stage uses 33 engineered inputs with LightGBM and SHAP. Its successor candidate is an implemented CPU graph-context XGBoost engine using 329 inputs. The latter summarizes local activity and typed incoming/outgoing neighborhood distributions. All transformations, feature order, model hash and Platt-calibration parameters are saved in a portable manifest.

On the canonical synthetic address-window protocol, graph-context XGBoost achieved average precision 0.3148 against 0.0538 for the matched local-only model. A trained temporal graph model is also available as a measured challenger. Selection records and operational retrieval matter more than picking a test metric after the fact. Chronological fit/calibration/validation/test windows, per-window Precision@20/50 and source precision/coverage are used for the relevant tasks.

We independently ported the graph-context feature recipe to lightweight inference and verified exact feature and score reproduction for 324,395 rows in 20 checks. A stripped runtime, without answer keys or Torch imports, reproduced the same 20-lead packet. A repeated measured replay took 2.69 seconds with 788.8 MiB peak process RSS on that workload.

5. The capture-to-case pipeline

KAVACH hashes original CSV/JSON/XML files before parsing and records accepted/rejected row accounting. SETU stores amounts as integer satoshis, times as UTC microseconds, unique transaction bodies and separate announcements. JAAL links addresses, transactions, peers and operators while retaining ownership proposals and their evidence. SHASTRA evaluates captured source candidates and operator summaries without making AML detection depend on an exact host answer.

VAANI turns model output into ranked explanations and counter-evidence. PRAMAAN creates canonical JSON, deterministic PDF documents, signatures and custody/replay references for main-pipeline cases. These layers are working modules, not only a planned architecture chart.

6. The local interface

DRISHTI uses React, TypeScript and Three.js for linked globe, money/network map, Trace, Origin, Leads and Proof views. The recent graph redesign keeps all endpoints reachable through bounded pages instead of overlapping them. Money edges retain complete transaction inputs/outputs; network edges remain observations. Saved run exports retain their provenance, and archived packet downloads preserve their original signed bytes.

The newer engine's queues can be inspected and imported locally in World, including model effects, amounts and graphs. This candidate lane does not silently replace the main application's LightGBM scores. The next release connects it to active lead routing and signs its own new evidence packets.

7. Why this is a practical SIH proposal

The trained detector, parsers, graph, explanation path, dashboard and signed artifacts exist. The demonstrated inference and browser flows operate locally without mandatory cloud or CUDA. The remaining release work is explicit: causal stage handoff, clean-host offline packaging and candidate-to-active-case integration.

The project offers both an investigation prototype and an empirical upgrade process. Results that do not improve the declared workflow are not forced into production. Graph learning remains available for further controlled tests, while the strongest portable evidence features are usable now.

Additional exploratory hybrid result: a saved-score experiment compared five tree/GNN blend weights and selected 75% graph-context XGBoost plus 25% temporal GNN using validation AP. On the already-used synthetic test, AP rose to 0.3381 from 0.3148 for the tree and 0.2879 for the GNN. Within 500 pooled reviews the blend retrieved 128 positive address-window decisions versus 115 for the tree. The GNN alone retrieved more at 50 reviews. This is exploratory evidence for complementary ranking signals, with independent-world confirmation required before promotion. It is not the production engine or a separately calibrated confidence model.

## Version 4: D — Offline evidence custody

Title: 78 characters. Abstract: 1973. Description: 6406.

### Idea title

DRISHTI by CHAKRAVYUH: Offline Bitcoin Leads with Explainable, Signed Evidence

### Abstract / summary

CHAKRAVYUH brings Bitcoin transaction intelligence onto an offline Linux workstation. Through DRISHTI, an investigator can move from bulk captured metadata to a ranked lead, inspect its money-flow and network evidence, and retain a verifiable case artifact without sending observations to a cloud service.

CSV/JSON/XML inputs are hashed before parsing and preserved with accepted/rejected row records. SETU separates unique transaction bodies from repeated peer announcements. JAAL connects addresses, transactions, peers and operators in a typed graph. LightGBM ranks suspicious activity with SHAP explanations; linked views show complete transaction endpoints, observed ports/timing, ownership hypotheses, source candidates and counter-evidence. PRAMAAN produces canonical signed JSON and accompanying PDFs with original-input hashes and replay information.

Our working optional CPU engine adds richer graph-context detection and an evidence-diverse queue. An independent inference port reproduced features and scores exactly across 324,395 rows in 20 checks. A stripped replay produced the same 20-lead packet in 2.69 seconds with 788.8 MiB peak process memory on the tested workload, without neural-training imports or evaluation answer keys. Local browser checks recorded zero external requests.

Model experiments also tested public Elliptic Bitcoin data. Graph-feature LightGBM achieved AP 0.6566 and 20 illicit transactions in its pooled top 20 under our declared temporal protocol. Synthetic transfer tests separately showed better suspicious controller-window retrieval after limiting overlapping transaction evidence.

Address-level activity detection remains usable while ownership and source hypotheses are unresolved. Main-pipeline cases and optional research queues retain their own model provenance and export paths. The system combines learned prioritization with evidence traceability, local operation and a checkable handover for further investigation.

### Idea description

1. The operational objective

CHAKRAVYUH is designed for the problem statement's offline investigation workflow: ingest bulk Bitcoin metadata, correlate blockchain and network observations, apply trained ML, produce prioritized explainable leads and show supporting evidence. DRISHTI is the local interface; PRAMAAN is the case-artifact layer. The proposal focuses on what an officer can inspect and retain after a model flags an address or transaction.

2. Evidence starts at ingestion

Before parsing, KAVACH records SHA-256 hashes of the delivered files and preserves their original bytes. It accepts CSV, JSON/JSONL and XML, coerces records into typed local tables, and accounts for every accepted or rejected row. Rejections have reasons; parsing does not silently erase the evidence of what was delivered.

SETU normalizes UTC timestamps and integer-satoshi amounts. It separates unique transaction bodies from announcements. The same TXID observed many times is one payment with many network observations. Local GeoIP/ASN and network-class lists supply context without live lookup requests. Unresolved information remains null rather than being turned into a made-up location.

3. A graph with explicit evidence meanings

JAAL connects addresses to input transactions, transactions to output addresses, peers to announced transactions and peers to network operators. Amounts are retained on money edges. Captured peer/port/time rows remain network evidence. Common-input and change heuristics add likely ownership relationships while retaining the underlying address nodes.

A derived owner grouping is useful for link analysis, but the system can also detect activity at address level. This prevents the entire workflow from depending on a single uncertain clustering decision. SHASTRA source estimates are similarly separate: a relay observation is not identity, and an insufficient source answer does not destroy the transaction evidence.

4. Trained, explainable detection

The main BUDDHI stage uses LightGBM with 33 engineered activity, flow, fee, temporal, ownership and available network/typology features. SHAP explains the features driving its score. VAANI creates ranked leads with readable evidence and mandatory counter-evidence, so the officer can see supporting reasons and plausible challenges together.

A working optional engine uses a frozen 329-feature CPU XGBoost model built from local address behaviour and typed transaction/announcer context. It validates artifact hashes and feature order, uses saved transformations and calibration parameters, and outputs signed positive/negative TreeSHAP contributions. The contributions reconstruct the raw model margin; the observed graph and amounts provide the factual context for reviewing them.

The optional engine has an executable CLI and local World-screen viewer. It has not silently replaced the default LightGBM stage or borrowed its signed packets. That explicit status makes model provenance maintainable as the application evolves.

5. Tests behind the implementation

MAYAJAAL is our configurable synthetic-world harness with separate answer keys. We used it to evaluate ownership rules, chronological features, observer coverage, tabular models, actual graph/temporal models and embedding/tree hybrids. Public Elliptic experiments remain a separate transaction-classification task.

The portable graph-context inference port reproduced engineered features and scores exactly for 324,395 rows in 20 checks. An isolated replay with only observation Parquets and model files, no answer keys and blocked Torch imports, reproduced the 20-lead packet. The measured repeat took 2.69 seconds with 788.8 MiB peak process RSS on the tested capture. These checks demonstrate a usable CPU inference path rather than relying on an assumed GPU deployment.

We also tested queue overlap control. In two synthetic transfer worlds, a frozen evidence-diversity policy increased suspicious controller-window retrieval from 11 to 33 and 9 to 16 across three future windows. The outcome concerns review slots and repeated-window retrieval, not verified human identities.

On public Elliptic Bitcoin data, our separately trained graph-feature LightGBM achieved average precision 0.6566 and 20 illicit transactions among its pooled top 20, versus AP 0.6366 for matched local-feature LightGBM. The temporal test comprised 11,184 labeled transactions, including 636 illicit; unknown labels remained graph context. Public transaction classification and synthetic address-window detection are separate experiments with different targets and prevalence.

6. Analyst review and signed handover

DRISHTI links the globe, ingestion record, transaction/network map, paged Trace, source candidates, leads and Proof. It provides local visual exploration alongside textual evidence. The graph retains all endpoints for displayed transactions, and bounded views record what context is omitted. Run identity and saved engine results remain distinguishable.

PRAMAAN assembles a canonical case JSON, PDF evidence document, notice template, Ed25519 signature and input/custody hashes. A Merkle-root log and replay checks support artifact verification. Full machine fields and redacted presentation fields have different roles. A signature verifies artifact authorship/integrity under a trusted key; it does not turn a model hypothesis into a legal finding.

The current UI exports original archived signed packets for main-pipeline cases. New research queues are exported separately. The next release adds their own signed-case adapter rather than presenting an old artifact as a new engine's proof.

7. Offline deployment and continuation

The stack uses Python, Polars/Arrow, rustworkx, CPU tree models and a React/TypeScript/Three.js frontend with local assets. The API is read-only and loopback. Browser checks ran offline with zero external requests; inference does not depend on cloud compute or CUDA. A full clean-host offline installer remains the packaging gate.

The release direction is to connect the frozen decision-window scorer, evidence-diverse queue and active case routing, then validate end-to-end reproduction and packaging. The trained temporal graph model remains available for measured future comparison. This gives the project a practical core today and a controlled route to richer modelling without sacrificing evidence traceability.
