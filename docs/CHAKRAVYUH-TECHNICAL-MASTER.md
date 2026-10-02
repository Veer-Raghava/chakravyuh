# CHAKRAVYUH / DRISHTI technical master

Implementation snapshot: **2 October 2026, R47 UI completion and R48 submission audit**. This document describes the inspected source, not an imagined completed migration. It is intended to stand alone for teammates and technical reviewers. Exact schemas, configuration, constants and a module/interface inventory are embedded in the appendices. The source/artifact digest inventory records the snapshot against which these descriptions were checked.

## Contents

1. Purpose, evidence semantics and implementation status
2. Prerequisites, layout and execution
3. MAYAJAAL: synthetic test world
4. KAVACH: original-byte custody and parsing
5. SETU: normalization and wire/chain separation
6. JAAL: facts, ownership hypotheses and paths
7. SHASTRA: network-source candidates and typologies
8. BUDDHI: default LightGBM detector
9. Optional causal graph-context CPU engine
10. Trained graph research and evaluation
11. VAANI: leads, reasons, doubts and diversity
12. PRAMAAN: signed evidence artifacts
13. DRISHTI: interface, run routing and visual semantics
14. API, evaluation boundaries and deployment
15. Verification, measured resources and migration gates
16. Embedded source-derived reference appendices

## 1. Purpose, evidence semantics and status

CHAKRAVYUH is the backend and investigation system for SIH26146. DRISHTI is its frontend. Team Lazarus is the submitting team, not a model or service. The supplied problem asks for an offline Linux system that accepts bulk transaction/network metadata, correlates IP/port/timing with TXID/wallet/amount, applies working AI/ML for detection, clustering or anomaly work, ranks explainable leads, and presents linked evidence.

The input is synthetic metadata shaped around Bitcoin, not a live interception appliance or a seized-data investigation. Bitcoin address identifiers, transaction records, announcing peers, source candidates and people are different objects. The system produces investigative leads, not determinations of criminal guilt or automatic identification of a human.

Five distinctions govern the implementation:

- **Transaction versus announcement:** a TXID repeated across observers is one transaction with multiple captured observations.
- **Address versus owner:** a common-input/change link is an ownership hypothesis. Address nodes are retained even when grouped.
- **Announcer versus origin:** an IP observed relaying a transaction may not have originated it. An unobserved origin is possible.
- **Risk ranking versus certainty:** a classifier score orders cases; conformal membership, probability calibration and confidence intervals are distinct constructs.
- **Integrity versus truth:** a signature authenticates an artifact under a key. It does not validate the model's inference or establish legal admissibility.

### 1.1 What runs by default

The main staged path is KAVACH → SETU → JAAL → SHASTRA → BUDDHI → VAANI → PRAMAAN. MAYAJAAL supplies synthetic captures for development and evaluation. DRISHTI presents exported artifacts across these layers. The default BUDDHI stage is LightGBM on 33 engineered inputs, with SHAP and MAPIE class-conditional prediction sets. The default SHASTRA stage can train a LightGBM candidate model when training labels exist; otherwise it records a heuristic fallback. The frontend primarily imports exported static JSON rather than invoking the API for every interaction.

### 1.2 Implemented optional lane

The repository also contains availability-time ownership ledgers, causal snapshots, a frozen 23-feature tree scorer, a frozen 329-feature graph-context XGBoost scorer, and evidence-diverse investigation queues. The latter is usable through a CLI and a World-screen local viewer. It consumes normalized observations without truth labels. It is **not automatically the main Leads/Proof engine**. Research graph weights are saved, but no canonical HGT/TGN/TGAT engine is deployed.

### 1.3 What is not implemented as a production promise

No guaranteed human deanonymization, definitive source-absence test, exact many-input/many-output satoshi taint allocation, default GNN service, complete clean-host offline installer, secure enterprise login, live Bitcoin interception, mandatory graph database, or validated “90% reliable across all future worlds” policy. These distinctions are necessary to read existing UI and historical documents correctly. They are not a reason to discard the working capture-to-evidence pipeline.

## 2. Prerequisites, layout and execution

### 2.1 Actual dependencies

Core Python requires >=3.11,<3.12. Declared pins: Polars 1.17.1, PyArrow 18.1.0, rustworkx 0.15.1, LightGBM 4.5.0, MAPIE 0.9.1, SHAP 0.46.0, FastAPI 0.115.6, Uvicorn 0.32.1 and httpx 0.28.1. NumPy, SciPy and scikit-learn are resolved numerical dependencies. Current prepared research imports XGBoost 3.2.0 and CPU PyTorch; XGBoost distribution metadata is missing despite a working import, and it is not a declared core dependency. A clean offline bundle must explicitly include it for the optional scorer.

Frontend package requirements: React 18.3.1, Three 0.171, R3F 8.17.10, drei 9.122, GSAP 3.13, @gsap/react 2.1, Lenis 1.3.11; TypeScript 5.6, Vite 5.4 and the React plugin. These package ranges are distinct from exact resolved lock versions. CSS Modules implement styling; local WOFF2 assets supply Fraunces, Hanken Grotesk and IBM Plex Mono. The product does not require PyTorch Geometric, ReportLab, Docker, Neo4j, Postgres, Redis or a cloud service. JAAL's optional Kùzu view is not a hard dependency.

### 2.2 Filesystem model

```text
src/chakravyuh/                 stage implementations, inference, read-only API, eval
apps/drishti-v2/                current interface; apps/drishti is historical
run_config.json                repository generator defaults
vendor/                        local metadata / optional public benchmark data
keys/                          local Ed25519 seed/public key; never publish seed
 data/generated/<run>/
   config.effective.json       resolved generator settings for that run
   capture/                    generated or supplied observation files
   sealed/                     originals, rows, rejections, hashes, manifest
   normalised/                 transactions, announcements, addresses, peers, rollups
   graph/                      nodes, edges, clusters, peel paths
   signals/                    origin candidates, L1, entity types, typologies
   scores/                     wallet scores, calibration and stage metadata
   alerts/                     alerts, evidence, counter-evidence
   packets/<case>/             canonical JSON, PDFs, signature, case log copy
   packets/merkle.log          run-level append-only packet log
 ground_truth/<run>/           evaluation-only ownership/source/campaign answer keys
 measurements/<run>/           evaluation reports, not inference input features
research/bitcoin/              experiment scripts, executed snapshots, scores and weights
```

The leading spaces before some example paths above are diagram indentation, not path characters. Stage guards resolve paths relative to repository cwd. KAVACH accepts captures under `data/`; later operational outputs are restricted to `data/generated/<run>/`. A supplied capture outside that root must first be copied into an allowed intake location. Model inference's newer explicit paths use their own validated entry points.

### 2.3 Operational commands

Replace the example capture/run/case names with your actual names. In a prepared environment, an existing capture under `data/incoming/evaluator-capture/` can be processed to a **new run**:

```bash
uv run --offline --no-sync python -m chakravyuh.kavach --in data/incoming/evaluator-capture --out data/generated/review-new
uv run --offline --no-sync python -m chakravyuh.setu --in data/generated/review-new/sealed --out data/generated/review-new
uv run --offline --no-sync python -m chakravyuh.jaal --in data/generated/review-new/normalised --out data/generated/review-new
uv run --offline --no-sync python -m chakravyuh.shastra --in data/generated/review-new/normalised --out data/generated/review-new
uv run --offline --no-sync python -m chakravyuh.buddhi --in data/generated/review-new --out data/generated/review-new
uv run --offline --no-sync python -m chakravyuh.vaani --in data/generated/review-new --out data/generated/review-new
uv run --offline --no-sync python -m chakravyuh.pramaan --in data/generated/review-new --out data/generated/review-new --case actual-alert-id
```

**Important:** these last stages are a training-oriented legacy route. On a capture with no supplied training label door, SHASTRA may use its recorded heuristic fallback and BUDDHI may produce an untrained .5/both-class state. This is not the frozen trained-model ingestion route. The new engine command below is the verified inference route for unlabeled observations; automatic joining into default VAANI/PRAMAAN remains pending. Do not promise that invoking the above commands on arbitrary unlabeled input reproduces the trained synthetic demo's quality.

`make agency-v2` and `make demo-full` rebuild named runs and include destructive removal of those named generated artifacts. They are not safe read-only serving commands and must not be used casually to preserve measured captures. `make demo` serves precomputed `s10-demo`; the current run-switcher fixtures can include a different default, so verify the selected frontend run instead of assuming it follows that API environment variable.

```bash
npm --prefix apps/drishti-v2 run build
CHAKRAVYUH_RUN=agency-v2 uv run --offline --no-sync uvicorn chakravyuh.api.app:app --host 127.0.0.1 --port 8000
npm --prefix apps/drishti-v2 run dev
```

Setup/sync/build dependencies must already be locally available for an offline invocation. `uv --offline --no-sync` proves only use of the prepared environment; it is not an installer.

## 3. MAYAJAAL — the world/test harness

Modules separate configuration, entity types, UTXO ledger/chain generation, adversarial campaigns, network propagation and exports. Config loading validates types/ranges and resolves named regimes, paths and overrides. `--txs` and `--set path=value` alter a generated run; `config.effective.json` records the result. Repository defaults changing later do not retroactively change a saved run.

### 3.1 Chain and activity

Default seed 42, target approximately 1,000,000 rows, 20,000 entities, mean 27 announcements per transaction. Chain defaults include start height 880000, genesis UTC-microsecond timestamp 1767225600000000,600-second block interval, 30 transactions/block, minimum 144 blocks,312,500,000-satoshi subsidy and 100-block coinbase maturity. Benign mining-pool payout patterns, multi-output payments, address reuse, multi-input spending and collaborative transactions provide counterexamples to simple laundering-shaped rules. Entity types have different transaction/activity behavior; the exact type specifications and distributions are embedded in the configuration appendix.

The generator uses a ledger rather than inventing independent amounts per row. A generated transaction has explicit input/output address and amount arrays. Captured P2P records repeat that transaction body together with network observation fields. The metadata format does not provide a general externally verified input-outpoint allocation for every trace; address-level fund paths must retain that distinction.

### 3.2 Adversarial campaigns

Default 120 campaigns, 3–40 moves, with peel, split, merge, mix, hop, structure, dwell and cash-out moves. Defaults include peel share 0.05–0.20, split 4–12 ways, mix 4–8 participants, merge 3–8 inputs, dwell 2–12 blocks and move gap 1–4 blocks. Campaign labels encode simulated participation, not a legal definition of illicitness. Benign morphology and label-generation overlap are explicitly evaluated; a detector can otherwise learn the simulator's own construction rules too easily.

### 3.3 P2P observation model

Default 5,000 nodes, 8 outbound connections, max 125 inbound, regional latency matrix, exponential mean relay delays 2 seconds outbound and 5 seconds inbound. Agency defaults to observer_fraction 0.60, 48 observers with ASN/IXP-biased placement; stealth uses 0.10, 16 uniform observers. The fraction denotes configured modeled observability and is not identical to the number of monitor nodes divided by all peers. Read each resolved configuration before interpreting the label.

Tor/VPN classes, unavailable ASN/geo entries, relay randomness and adversarial timing affect what enters the capture. Default Tor share 0.04, VPN 0.08; reserved address pools avoid implying the synthetic IPs are current real hosts. Port 8333 and ephemeral 32768–60999 model connection metadata. An observer sees announcements, not omniscient ground truth.

### 3.4 Truth separation, replay and validation

Observable capture files go under the run; true entities, campaign participation and origin mappings go under `ground_truth/<run>/`. Evaluation reports go under `measurements/`. Config/seed and executed source hashes are necessary for replay; a seed alone cannot recreate a world if algorithms or defaults changed. Research contains recovered historical-source/config replay work for this reason.

Validation checks ledger/invariants, distributions and simple-label-leakage controls. Passing it supports internal consistency, not representativeness of every real Bitcoin laundering practice. Fresh seeds share generator mechanisms; an independent seed is stronger than a repeated test window but weaker than real external-domain validation.

## 4. KAVACH — custody before coercion

`seal.py` hashes original delivered bytes before constructing the parser. It preserves source files and records an input manifest. That order matters: a later parsing failure must not eliminate the hash of what was received. Container/encoding detection, column aliases and amount/timestamp detection live in `schema.py`; format readers in `readers.py` support CSV, JSON/JSONL, XML/text and gzip/zstd containers when their decoder is available.

Required scalar values include timestamp, source/destination IP and port, and TXID. Transaction arrays are typed lists; empty inputs can indicate coinbase and are not automatically defective. Amount conversion uses exact numeric parsing into integer satoshis. Time conversion produces UTC epoch microseconds while retaining raw timestamp text. IP versions, optional fee/vsize/script/block/msg/observer metadata and ASN/country are stored where present.

The governing accounting identity is `rows_read = rows_sealed + rows_rejected`. Rejected rows retain original tokens/reasons; there is no unaccounted third outcome. Sealed rows have stable row IDs used later as source references. Input-byte SHA-256, typed-table hashes and stage metadata support subsequent custody checks. This is not encryption and does not prevent an authorized filesystem user from replacing all unsigned manifests; custody/key policies are separate operational controls.

## 5. SETU — separate wire observations from chain bodies

`normalise.py` transforms sealed rows into six normalised tables, with schemas embedded below. `announcements.parquet` is event grain; `transactions.parquet` is TXID grain; `addresses.parquet` is address aggregate grain; `peers.parquet` is announcing-IP grain; ASN and arrival tables are derived substrates. Repeated same-IP observations on different ports retain their ports in event records, although the peer entity is keyed by IP. NAT/shared-IP use therefore needs counter-evidence rather than treating an IP as a person.

### 5.1 Transaction normalization

Consistent repeated bodies collapse to one transaction; incompatible bodies for one TXID are quarantined/set aside with conflict accounting. Derived fields include first/last observation, announcement count, unique-peer count, spread, input/output arrays and counts, total in/out, fee/feerate where derivable, coinbase flag, equal-output flag, inferred change index and block height. A first-seen time is a captured availability proxy, not necessarily mining or signing time.

Possible change is an observation-derived heuristic: for multi-output transactions, a sole non-round amount using a 1000-satoshi roundness rule is a candidate, excluding input-reused addresses; undetermined index is−1. It is not a ground-truth owner label. Script types can use declared metadata and address prefixes; null is distinct from a zero value.

Address totals and dwell aggregate across the capture. These whole-capture aggregates must not be fed unchanged into a forward-time evaluation. The causal snapshot path reconstructs activity inside a declared window. Peer tables similarly aggregate n_announcements/n_txids/rank/ports and enrichment over the capture; causal source experiments reconstruct past-only history.

### 5.2 Enrichment and arrival

The source peer's IP is mapped through local metadata snapshots. Optional GeoLite-compatible blocks/ASN data and local Tor/VPN lists supply operator/network class. Missing vendor data must lead to unknown/null states, not a network lookup. Country is network context, not a person's location. The arrival table retains `(txid, observer_id, peer_ip, seen_us)`; announcement rows also retain source/destination ports and row IDs.

## 6. JAAL — typed facts and ownership views

`build.py` declares node kinds **address, transaction, peer, cluster, asn** and edge kinds **SPENDS, RECEIVES, ANNOUNCED_BY, SAME_OWNER, HOSTED_IN, MEMBER_OF**. The current core graph does not contain a separately declared country/observer node kind or a general transaction-to-transaction temporal edge. Country/observer information exists in tables. Research models build their own typed relations from normalized tables; do not confuse their graph vocabulary with persisted legacy graph kinds.

Observed money/capture edges normally carry confidence 1.0 as a provenance classification. HOSTED_IN derived from a lookup can use 0.95 to distinguish enrichment from observed source metadata. These numbers are ordering/evidence weights, not universal probability calibration.

### 6.1 Ownership proposals

Common-input ownership links are generated for eligible non-coinbase multi-input transactions after mixer screening. A star connects each unique input to a lexicographic anchor, requiring n−1 links instead of a clique's n(n−1)/2. This preserves connected components for the same member set and reduces quadratic memory. It does not independently establish every inferred pair is correct.

The common-input weight is 0.36; possible-change weight 0.25; default component threshold 0.20. The 0.36 constant was motivated by a full-cluster study, but that study's precision is **not** our edge posterior. Multiple weak edges joined transitively can create a poor cluster. Default change and common-input edges both pass 0.20. Raising the threshold changes the derived view, not stored address facts. Mixer-like transactions are screened with equal outputs, at least 3 outputs and 2 inputs; false positives/negatives remain possible.

`clusters.parquet` stores members, size, weakest-edge weight, heuristics and threshold. `MEMBER_OF` connects addresses to displayed groups. rustworkx computes graph/components; an optional Kùzu adapter can provide Cypher when installed. No graph database is required for normal execution.

### 6.2 New availability-time ledger

`provenance.py` retains **every** ownership claim `(src, dst, txid, available_us, confidence, evidence)` before deduplication. At a cutoff it selects only available claims, then retains the strongest eligible claim per pair, tie-breaking by earliest claim/transaction/evidence. This prevents a stronger later claim from acquiring an earlier timestamp. A caller must ensure the transaction body was actually available at first_seen_us; a later body arrival requires its own available time.

The default legacy stage does not yet persist/use this ledger everywhere. New snapshots do. Address representation mode excludes the ledger entirely. A tested isolation invariant ensures corruption of ownership evidence cannot change address-mode features/scores.

### 6.3 Peel paths and money semantics

`trace.py` identifies eligible two-output peel-shaped transactions, with positive smaller payment satisfying `payment*20 <= total_out*7`, excluding coinbase/mixer/equal-output cases. It follows the larger-output address only when there is one unambiguous next spending transaction and it also matches the shape. Paths require at least 2 hops. No continuation, multiple spends, broken shape/merge and cycle are explicit stop reasons. A path records transaction order, depth, initial/peeled amounts, leak fraction, root address and times.

This is a stronger observation than counting peel-shaped sends, but remains address-path evidence. Repeated spending of one reused address or absent outpoints can make the continuation ambiguous. The Trace UI does not assign each input's satoshis to a specific output or claim precise taint through a mix. R47 removed invented Cartesian sender/change ownership lines and labels candidate change as **possible change**.

## 7. SHASTRA — source candidates, operator evidence and typologies

### 7.1 Candidate grain and features

The legacy candidate table has one row per `(txid, peer_ip)` with timing/rank, announcement and observer counts, observed blind monitors, peer early-rank fraction, prior TX count, graph degree, payer-peer reuse, network-class code, Tor/hosting flags and timing score. Exact 15 model inputs and explanation-struct fields are embedded below. These include actual peer graph degree; **this is not evidence that BUDDHI's 33 inputs include PageRank or centrality**.

Legacy payer links count across the whole capture, and peer/graph histories are not as-of a decision. They are retrospective features. The new `causal.py` recipe bounds a decision to five seconds after first observed announcement and joins history strictly earlier than that transaction. No future wallet/network histories or labels are fed into those features. Enrichment still assumes a fixed metadata snapshot.

### 7.2 Three ranking mechanisms

**First-spy reference:** arrival-order decay starts at 0.5 and decays by 0.5, producing a candidate list rather than proving earliest=source.

**Timing score:** for candidate c, `_mle = m*log(prior+epsilon) − lead/mean_delay − mean_dispersion/mean_delay`, using distinct observer support, earliness and spread. Constants: epsilon 1e−12, minimum mean 1 microsecond. Scores are normalized within the transaction against a phantom escape term. After subtracting max score, `p(c)=exp(score(c)-max)/(sum(exp(...))+exp(-1))`. Residual mass represents a model provision for “none observed”; it is not a validated posterior test that the real person is absent.

**Learned ensemble:** native binary LightGBM, 300 rounds, learning rate 0.05, 31 leaves, minimum leaf size 40, L2=1, deterministic one-thread settings and run seed. Training source labels are supplied through the evaluation label door for early transactions only. At least 200 candidate rows and both classes are needed. The later 25% training rows calibrate with logistic regression on raw margin when at least 50 calibration rows and both classes exist. Too few labels/no answer key records `trained=False` and a heuristic fallback. A table named “ensemble” alone does not prove ML trained.

Candidate masses are capped when their sum exceeds one. Probabilities are recipe-specific and not guaranteed human-identity confidence. Training, calibration and fallback status live in metadata and must be read with estimates.

### 7.3 Abstention and ASN/country

Top-two separation is computed relative to their summed mass; default margin floor 0.04. Priority: Tor present, one observer, too few announcements, low separation. An abstaining candidate list shifts ranks so it has no rank 1 row. Ordering remains available for inspecting what was considered. L1 aggregates candidate evidence onto ASN, applies an early-rank prior and escape normalization, and can refuse when shortlist mass spans operators. Country rollup is a separate network-context summary. L1 is not an independently calibrated identification of a person or a guarantee that exact-IP failure implies correct ASN.

`origin_estimates.parquet` is candidate grain; `origin_l1.parquet` is transaction/operator-summary grain. R47 serialization now chooses leader and runner-up by descending p_origin while preserving chronological shortlist order. Margin is exactly leader minus runner-up. The visual arrival sequence therefore no longer accidentally determines the “runner-up” number.

### 7.4 Typologies/entity context

`typology.py` detects fan-out>=6 outputs; CoinJoin-like equal outputs>=3; at least 2 peel-shaped sends with smaller share<=.35; and structuring-like>=3 single-output sends with coefficient of variation<=.15. These are pattern rules and not the project's only ML use case. `entity_types` supplies benign context/exemption hypotheses. The default scoring stage reads exemptions but its exact treatment must be distinguished from verified ground-truth entity type.

### 7.5 Research source policy

Causal source experiments used fit/calibration/policy/test time spans 0–45%, 45–60%, 60–70%, final 30%, with crossing five-second decisions purged. A selected same-world policy answered 486 transactions,459 correct, at 5.03% coverage. Separate new worlds produced 92.66% and 86.77% precision at 5.72% and 4.92% coverage. Nested observer reduction 48→24→8 caused precision 94.4%→51.1%→26.4%. These findings require regime-specific policies; they do not support a universal reliable host/ASN answer or source-absence declaration. Exact targets and denominators belong to their saved reports, not a merged headline accuracy.

## 8. BUDDHI — default 33-feature LightGBM

### 8.1 Subjects and labels

A subject is a derived cluster or a singleton address not included in one. Legacy splitting assigns subjects according to earliest activity relative to a 0.7 elapsed-time boundary. Features of early subjects use earlier transactions and later subjects use later transactions, and active members/edges are windowed. But full-capture cluster membership and upstream origin/typology computations remain retrospective. Chronological rows alone do not make the whole pipeline leakage-free.

Training labels arrive through `eval.labels.wallet_labels` by majority of labelled true-owner members, ties licit. Ground truth is not an input feature; evaluation-only later labels score predictions. With no training labels, the training-oriented default stage cannot provide a freshly fitted working classifier. It records untrained fallback score 0.5 and ambiguous sets. Frozen-model inference is the newer optional path.

### 8.2 Input families

33 inputs cover address count, send/receive counts/amounts, balance, counterparties, fan-out, coinbase/equal-output behaviour, fees/dwell, ownership weights/heuristics, script diversity, candidate/operator statistics, typology counts and six morphology features. All ordered names and their source glosses are embedded below.

Important implementation detail: default send aggregation credits a subject/address with transaction output totals for its sends rather than proving its exclusive value contribution in a collaborative input. Addresses in a multi-input transaction therefore need careful interpretation. Snapshot `_flow_features` refines amount aggregation; the exact source is included in the formula appendix. Balance is window received minus sent, not a verified spendable UTXO balance or net wealth. Counterparty/fan-out summaries compress relationships; they do not retain every path/order/type interaction.

No default PageRank, betweenness, clustering coefficient, connected-component numeric identifier, suspicious-neighbor label count or graph-distance feature is present. The graph signal is actual engineered flow/morphology/ownership and source context. Missing values are preserved for LightGBM where the recipe specifies; absent context must not be relabelled as observed zero.

### 8.3 Training and explanations

Native `lightgbm.train` binary objective: 300 rounds, learning rate 0.05, 31 leaves, min_data_in_leaf 40, L2 lambda 1, feature_fraction 1, bagging_fraction 1, num_threads 1, deterministic=True, force_row_wise=True, verbose=-1, run seed. No declared automatic class weighting or LambdaRank objective; it ranks binary classifier scores. The final 25% early training rows are reserved for calibration; minimum 50 rows and 10 members/class for a class-conditional wrapper. MAPIE compatibility uses a local estimator-tag adapter for the inspected scikit-learn environment.

SHAP TreeExplainer returns the five largest absolute feature effects per subject, retaining sign and rounding to 6 decimal places. Effects are model log-odds contributions, not evidence that a feature caused wrongdoing. The default reduced explanation does not include every contribution or guarantee reconstruction from only five values.

### 8.4 Prediction sets versus score bands

Conformal membership maps `{0}`→LIKELY_LICIT, `{1}`→LIKELY_ILICIT, `{0,1}`→UNCLEAR and empty→ABSTAIN. The label derives from membership, not a fixed score threshold.

The display range is **heuristic**: when both classes are included, `[0,1]`; otherwise `[max(0, score*.85), min(1, score*1.15)]`. Despite historical field/method naming, this range is not a conformal confidence interval around an illicit probability. Class-conditional inclusion coverage is an empirical set property under assumptions, not a precision promise for flagged leads. PRAMAAN currently records these bounds and calibration-method strings; future adapters should make their semantics explicit.

### 8.5 Optional historical `--gnn`

`embed.py` creates a label-free two-hop row-normalized graph propagation plus an 8-dimensional SVD projection. A second LightGBM sees 33+8 inputs and is historically named `gbm_gnn_v2`. This is **not a trained graph neural network**. It is off by default, and its older benchmark did not beat the richer required bar. Actual trained GNN research is a different implementation described below.

### 8.6 Legacy reported measurements

Agency report:26,783 holdout subjects, imbalance 1:53, P@20 0.60, AP 0.064920, ROC-AUC 0.591407; transaction-projected AP 0.100579. Reported illicit conformal coverage 0.947154, licit 0.683466. “Actor-level” is a historical report field name but the scored units are predicted subjects, not verified people. Campaign inclusion recall 0.954082 uses a broad inclusion policy and is not equivalent to 20-case retrieval. Full-capture partition/history issues mean these are retrospective diagnostics, not causal deployment estimates.

A separate existing Elliptic method reports 29,379 train/17,185 test labelled transactions, AP 0.778296, F1 0.766174, precision 0.892052, recall 0.671429. It replicates a procedure using Elliptic's own features, not our named 33 features or network-source task. The newer matched external graph experiment has a different recipe and lower AP; do not mix figures to choose a winner.

## 9. Optional causal graph-context CPU engine

### 9.1 Snapshot representation

`buddhi/snapshot.py` rebuilds each window from observations and an as-of ownership ledger, or chooses explicit address mode. It includes recurring subjects instead of limiting evaluation to newly seen subjects. It excludes 10 legacy origin/typology columns whose causal recipe is not part of that detector, leaving 23 local inputs. Node identifiers join objects but are not supplied as numeric features. The normalized first_seen_us is a body-availability assumption which must be corrected if external body arrival differs.

`causal_inference.py` supplies a 23-feature frozen XGBoost recipe; `relational_inference.py` supplies the richer 329-feature recipe. Both store model/schema/hash/scalers and calibration. Representation is recorded; address mode must not silently become ownership-group mode.

### 9.2 Exact 329-dimensional construction

Let local subject vector have 23 dimensions. For each TX:

- Six transaction features: number inputs, number outputs, total output sats, fee sats, fee rate, equal-output indicator.
- Nine mean announcing-peer features: observation/TX/observer counts plus 6 network-class indicators.
- Twenty-three mean funding-subject features.

Total transaction context 38. For subject incoming and outgoing relations separately, calculate log(1+degree) and mean, population standard deviation, minimum and maximum of each of 38 context coordinates. Each direction has 1+4*38=153 inputs. Concatenate 23+153+153=329.

Local values use signed log1p; nonnegative TX fields use log1p; peer counts use log1p with one-hot network classes. Means/scales are fitted on training windows only. Pooling uses float32; distribution statistics accumulate float64, clamp roundoff-negative variance to 0, then cast float32. Empty neighborhoods have zero context. No neighbor-label or suspicious-neighbor truth count is used.

The representation keeps distributional typed context beyond scalar counterparties/fanout while remaining understandable and CPU-friendly. It still compresses exact graph paths, interaction ordering and individual edge roles; a learned temporal encoder may preserve some of those differently but cannot recover observations absent from the capture.

### 9.3 Tree, calibration, artifacts and inference

Native XGBoost 300 trees, maximum depth 5, learning rate 0.05, minimum child weight 10, row/column sampling 0.9, histogram algorithm, four threads, seed 42. Canonical 10 windows use fit 0–3, calibration 4–5, validation 6, test 7–9. Saved Platt scaling applies logistic mapping to clipped raw probabilities' logits using recorded arithmetic precision. It supports historical ranking calibration, not universal future precision.

Model JSON avoids runtime unpickling. A manifest declares schema version, ordered feature names, representation, model SHA-256, transforms and calibration values. Native contributions include all 329 effects and bias; their sum must reconstruct raw margin within declared tolerance. The separately calibrated risk score is not the sum of the calibrated SHAP effects.

The CLI consumes four normalised observation tables and artifacts; it does not fit on incoming test data, read ground truth or import Torch. Scores Parquet and lead JSON are local outputs. A fresh output directory is required to prevent accidental overwrite.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync python -m chakravyuh.vaani.investigation \
  --normalised data/generated/agency-v2/normalised \
  --model research/bitcoin/results/relational-inference-artifacts/address \
  --start-us 1767617601829851 --end-us 1767666624832117 \
  --output /tmp/chakravyuh-review-queue
```

This saved example is a consumed synthetic window, not a new independent evaluation. Use a new output path. The World viewer can load `leads.json`; this does not update the active legacy run or regenerate its signed packets.

## 10. Trained graph research and evaluation

### 10.1 What was actually trained

Research includes public Elliptic local/graph-feature trees, MLP, GCN, a documented symmetric-normalization SAGE variant, shuffled topology, and embeddings→tree. Custom typed subject/TX/IP encoders and window GRU memory were trained on synthetic snapshots. Static and temporal heads, graph-shuffling controls, XGBoost/LightGBM hybrids, feature and graph autoencoders and Isolation Forest were executed. GAT, canonical TGAT/TGN/HGT and large event-time heterogeneous Transformers remain literature/future candidates, not completed deployed experiments.

### 10.2 Custom temporal model

The tested model uses learned 32-dimensional typed features and mean aggregation over subject↔TX and announcing-IP↔TX relations, with a supervised head. Window history is linked by previously observed address membership; a GRU mixes prior subject embeddings into the current representation. Prior states are detached; no future graphs/labels are supplied. It uses window memory rather than continuous-event TGN memory or TGAT temporal attention. Identity continuity is an address correspondence, not verified controller recovery.

The research hybrid freezes learned temporal embeddings and concatenates engineered features for an XGBoost head. Tree effects on embedding dimensions do not by themselves explain the encoder's graph reasoning; model promotion would require encoder evidence/ablation as well as operational improvement.

### 10.2.1 Exact neural optimization and equations

For each node type, a linear projection into 32 dimensions followed by ReLU gives initial features. The transaction update adds its own representation, a mean pooled funding-subject message and a mean pooled announcing-IP message, each through its type-specific linear map. The subject update adds a self projection, mean received-TX messages and mean spent-TX messages. Relation maps have no bias. If temporal mode is enabled, a 32-by-32 GRUCell consumes the current subject representation and the mean earlier address-linked state. Dropout is 0.2 before the scalar linear classification head. Sigmoid converts its logit for calibration.

Training uses AdamW, learning rate 0.001, weight decay 0.001 and gradient norm clipping at 5. Binary cross-entropy has positive weight sqrt(number of fitting negatives / number of fitting positives): **12.932517** in R47. Every fitting window is one optimizer step, in chronological order. State tensors are detached between windows. Validation AP is checked every five epochs; the best weights are restored. R47's static and temporal models selected epoch 60; the shuffled temporal control selected 55. A later logistic calibrator fits only windows 4–5. Family choice uses validation P@20 then AP; no test labels select a checkpoint.

The model object reports 12,833 allocated parameters for every variant because it constructs relation and GRU modules even when they are disabled. Active computation differs: local MLP uses 1,857 parameters, static graph uses 6,497, and temporal graph uses all 12,833. Thus an equal allocated-parameter count is not a capacity-matched MLP control. Parameter totals follow the inspected 23/6/9 input dimensions, 32 hidden width and PyTorch GRUCell biases. The embeddings/tree hybrid fits the tree on fitting-window embeddings; it is not cross-fitted stacking.

### 10.3 R47 actual replay

60 epochs, CPU 4 threads, seed 42, width 32, address mode, 10 chronological windows. Test decisions 57,105 address-windows,295 positive(.5166%). Total run 26.3576 seconds. Validation-selected family is temporal typed GRU, not selection by best test result.

| Method | Test AP | Pooled P@20 |
| --- | ---: | ---: |
| Local MLP | .0758 | .25 |
| Local XGBoost | .0538 | .55 |
|53-feature mean typed-context tree variant | .1902 | .60 |
| Static typed GNN | .2602 | .80 |
| Temporal typed GRU | .2879 | .95 |
| Shuffled temporal graph | .0778 | .45 |
| Temporal embeddings → XGBoost | .2675 | .90 |

The typed-context tree row is **not** the 329-feature richer summary tree, whose saved canonical AP is 0.3148. The temporal row's individual test-window P@20 is 0.65, 1.00, 0.00; the last has no positives, AP undefined. Pooled top 20 differs from a fixed 20-review budget per window. Canonical tests have been consumed; replay is reproducibility evidence, not untouched confirmation.

### 10.4 Earlier positive findings

Extended 180-epoch graph work transferred to frozen new seeds 30011/40009 with P@20 0.55/0.95 versus local 0.30/0.75, and AP 0.2491/0.2263 versus 0.0719/0.1494. Controller projection shrank advantages and weak change links could damage them. These experiments motivate further graph work but do not prove that a GNN universally wins our queue task.

Public Elliptic engineered graph LightGBM AP 0.6566 versus local 0.6366 under the newer matched protocol supports neighborhood engineering outside MAYAJAAL. Its external transaction labels/steps differ from address-window campaign labels and have no captured origin IPs.

### 10.5 Anomaly methods

Isolation Forest and feature/graph autoencoders were actually tested. IF score fusion reduced selected test P@20 from 0.50 to 0.45 in its comparison; feature AE/IF had no top 20 positives in the relevant tests; graph AE retrieved 6/20 but AP 0.0207. These outcomes do not justify making unusualness a probability of laundering or source absence. An auxiliary unusual-activity queue remains possible if semantic usefulness is separately evaluated. Rule-based typologies plus trained supervised ML currently satisfy a concrete detection use case; do not claim an unvalidated anomaly model is production-ready.

## 11. VAANI — leads and review workload

### 11.1 Main stage

VAANI reads scores, signals, graph and announcements; no training occurs here. It retains subjects not labelled LIKELY_LICIT, sorts by descending risk_score with subject-ID tie-break, assigns 1-based ranks and severities score > 0.65 high, > 0.40 medium, otherwise low. Inclusion of UNCLEAR/ABSTAIN means the output can be broad; a class-inclusion queue is not automatically a high-precision actionable queue.

An anchor transaction is chosen among subject RECEIVES edges with an answered ensemble rank 1, highest p_origin, then margin, then TXID. This is a deterministic supporting transaction, not proof of originating every subject send. `attribution_ready` is an operational completeness flag based on the anchor having peer/port/time substrate; it does not prove correctness of the source estimate. The alert schema does not store the model risk_score directly; API views join score information.

Headlines/reason sentences are templates over feature glosses and observed values, not an LLM-generated explanation. Deterministic wording avoids ungrounded narrative. Evidence rows carry kind/statement/weight/source_ref. Counter rows include benign entity/typology explanations, weak ownership, low candidate margin, shared announcing IP, abstention and residual source doubt. Each alert must have counter-evidence; `would_clear` distinguishes a potentially decisive counter from a softer caveat.

### 11.2 New evidence-diverse queue

Take up to 2,000 eligible score-ranked subjects with TX support. Greedily select up to 20 if each pair's support-set Jaccard intersection/union<=.25. The policy accepts no owner/illicit truth labels. It avoids overlapping observed evidence; it does not guarantee distinct actual owners.

Packet context uses up to 16 latest supporting transactions per lead, in chronological order. Each retained TX includes all input/output endpoints and integer amounts. Up to 4 distinct captured peers per TX include times/ports/row references. Context truncation is recorded. Content-derived IDs remain unique even when two display labels truncate identically. Network edges identify announcers, not origins. Positive/negative margin contributions accompany raw activity facts and review suggestions.

The frozen rich-tree diversity policy improved suspicious controller-window retrieval 11→33 and 9→16 across three windows in two generated transfer worlds. The same controller can repeat in multiple windows. These are post-selection evaluation diagnostics; the deployed selector never sees those hidden controller keys.

## 12. PRAMAAN — exact artifact construction

### 12.1 Packet contents

For a known actualalert_id, PRAMAAN reads alert/evidence/counter, subject addresses, scores/calibration, source/L1 data, original input manifest and upstream stage metadata. The packet contains case/tool/code identifiers, generation time, input fileSHA-256 and rows_sealed, redacted subject fields, attribution readiness, operator and redacted shortlist, full peerIP/port in the officer-oriented machine block, findings/counter-findings, legacy score bounds, chain-of-custody entries and replay command/seed/hash. Legal-template strings are currently hardcoded; review by an authorized officer is required before operational use.

The serializer uses `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True)` encodedUTF-8. The embedded expected_packet_sha 256 is computed with that field blank; replay verification blanks it again. The file's actual full-byteSHA is a different digest because it includes the inserted value. Confusing these two would break verification.

### 12.2 Signature and keys

A local 32-byte Ed25519 seed is loaded from `keys/ed25519.seed` or generated once; the public key is stored separately. The project uses its own `ed25519.py`, not a declared cryptography package. `packet.sig` signs the canonical JSON bytes, not every PDF independently. PDFs are deterministically derived and checked separately in replay tests. Protect the seed, restrict file access and anchor the public key through a trusted operational process; neither a loopback app nor a signature alone solves key custody.

### 12.3 Merkle log

Each packet's leaf is SHA-256(canonical bytes). `merkle.log` appends `index leaf previous_root`. The root pairs textual hex strings and hashes their UTF-8 concatenation, duplicating an odd leaf at each level; empty root 64 zeros. Verification recomputes previous-root consistency and final root. This is the project's precise algorithm, not an assumption of a standard binary-Merkle byte layout.

A wholly rewritten log with no external trusted root could be self-consistent. Anchor roots/public keys outside an adversary-editable directory for meaningful tamper detection. The verifier currently does not authenticate a trusted external head or verify displayed integer index ordering by itself. A case-local log copy is produced by the stage helper; the run-level log is authoritative.

### 12.4 PDFs, replay and readiness

`pdflib.py` and `documents.py` write packet.pdf and notice.pdf without ReportLab. The notice is a template, not an issued legal demand. `verify_signature` checks packet JSON signature; `verify_replay` rebuilds packet bytes from the available run artifacts and checks reproducibility. This is not the same as regenerating a whole capture with current defaults. Rebuilding the complete pipeline needs original source/config/assets and explicit stage contracts.

The current Proof UI downloads five archived signed packet sets whose bytes were checked against hashes. “Build proof” navigation is not a browser endpoint that generates a new packet. A new engine's evidence JSON is not already a signed PRAMAAN case, and must not be presented as one.

## 13. DRISHTI — interface and routing

### 13.1 Screens and data

The current app is `apps/drishti-v2`. The Sutra top navigation and aperture provide Globe, Intake, Untangle, Map/Trace, Origin, Leads, Proof and World. State includes selected run, selected transaction/case, display layers and properties drawer. Eight operational exports are agency-v2 and observer sweeps. The main demo menu highlights curated captures; old test artifacts are not automatically every file under data/generated.

`RunContext` lazy-loads run JSON. Selected-run changes drive screen data consistently. The Intake screen inspects an already sealed run; it is not yet a raw-file upload/execution endpoint. Raw parsing is performed by the backend CLI. Research window 7/8/9 queues remain a separate viewer; their selected model/metrics do not replace the active legacy run. The frontend does not select a different detector simply because a GPU is present. Login is a demo gate, not a security boundary. Removing displayed 127.0.0.1 text did not change loopback serving.

### 13.2 Graph semantics and trace readability

JAAL's main visual carries two floors: captured network peers above, input/output address/TX money evidence below. Cross-floor announcement lines express the wire/chain join. The atlas gives semantic context and can route money/TX selection directly into Trace. R47 closes the blocking drawer on navigation; a passive canvas tooltip is not a required modal step.

Trace bounds the scene to 4 unique input addresses, 4 output addresses and 6 peers per page, with independent paging. Every endpoint remains reachable; raw case totals and the accessible evidence list remain complete. Source-checked arrays, amounts and observations are not deleted to simplify layout. A large tested case has 18 inputs, 3 outputs, 34 peers and 5/1/6 pages. Camera fitting scales for viewport aspect. Coins, block geometry and animated flow retain the established visual concept.

Origin uses a full-width heading, bounded maze and two-column evidence area. Candidate summary leader/runner agrees with sorted likelihood; chronology remains visible independently. Gauge values represent measured benchmark observability rather than declaring the current case's true sender present/absent. Leads uses queue/evidence columns and inline selected-case state; SETU uses parallel tables with bounded internal scrolling. These changes reduce vertical/right-heavy reading without hiding the data.

The globe has a larger invisible sphere hit volume around smaller visual markers; country-index clicks reset the post-drag guard. A browser test clicks outside the dot's visible radius and reaches the target. Marker geography derives from fixed synthetic/enrichment context, not independently verified physical sender location.

### 13.3 World and research viewer

World explains the synthetic harness, actual tests and model differences. The GNN panel says that models were trained, displays generated metric data from report.json and identifies consumed tests/custom typed GRU. It does not advertise an unimplemented GPU mode. The local investigation preview renders queue SVG graphs, SHAP details and exact amounts; local JSON import checks size/shape/IDs/references and supports 1–200 leads/10 MB. Import/export preserves the selected packet.

### 13.4 Presentation/accessibility

CSS Modules and local fonts maintain the paper/ink/coral/blue vocabulary. “Follow the evidence” now uses the existing nonitalic display-family treatment. Reduced-motion paths and DOM evidence are available; browser checks cover mobile 390 px without horizontal overflow for the tested screens. This does not certify all WCAG criteria or guarantee 60 fps on every GPU. WebGL 3D needs graphics support; the ML inference path is CPU-capable.

Identifier display follows actualformatterimplementation, not a blanket legal mandate: VAANIIPv4keeps 2 octets, IPv6keeps 2 hextets; addressfirst 6/last 4; TXIDfirst 8/last 4. Some historicalCLAUDEtext requestedoneoctet, so use the source-derived contract for current display. Hashes/Merkleroots remain full. Rawmachinecolumns retain identifiers for localjoins/officerartifacts.

## 14. API, evaluation boundary and deployment

The FastAPI application is read-only. Its run ID comes from `CHAKRAVYUH_RUN`, resolves under `data/generated/`, and rejects path separators or escaping IDs. No route accepts a filesystem path. Routes are `/health`, `/manifest`, `/collapse`, `/transactions`, `/origin/{txid}`, `/graph`, `/alerts`, `/alerts/{id}` and `/packets/{id}`. List limits default to 200 and cap at 2,000; the graph cap is at most 20,000. The serve command must bind loopback. A module `BIND_HOST` constant does not override an operator launching Uvicorn with another host. There is no authentication. Do not expose this API publicly as-is.

The static frontend uses exported data and local artifacts. A future public synthetic demo can be deployed separately without exposing private keys or real captures. No deployment occurred during this audit.

Evaluation modules own training-label doors, truth tables and measurement writing. Scoring features should never use held-out labels. Research dashboards deliberately present measurement reports. However, the existing API quarantine test currently rejects the serializer reading measurement files. This unresolved boundary is why focused API passes do not establish full release verification. The intended repair is to separate inference artifacts from evaluated research presentation, with appropriate guards and tests.

Clean-host deployment must bundle compatible Python/native wheels, frontend assets, model files, metadata snapshots, licences and checksums. Existing local offline execution demonstrates runtime independence; it is not a complete tested installer. XGBoost needs explicit packaging. Metadata snapshots need version, date and provenance rather than being treated as permanently current.

## 15. Verification, metrics and release gates

### 15.1 Metrics by task

Detection: precision, recall and F1 at a declared policy; ROC-AUC; AP (average precision, distinct from a trapezoidal PR integral); Precision@20/50; Recall@K; per-window prevalence and alert volume. Source attribution: answered precision, coverage, appropriate recall, candidate support and observer regime. Ownership: pair precision/recall, cluster contamination, sizes, thresholds and temporal availability. Workload: overlap, unique TX support and campaign/controller-window retrieval, evaluated after selection. Calibration: Brier score, reliability and class-conditional set coverage. Resources: training/inference wall time, peak process RSS, artifact size and workload shape.

`Precision@20 = true suspicious decisions in the reviewed top 20 / 20` when 20 are available. Declare smaller queues and zero-positive windows. Do not quietly shrink the denominator to positives or count duplicate addresses as different people. High accuracy from predicting rare labels negative is not an investigator benefit. Repeated windows and graph neighbors are correlated; a naive independent-binomial confidence interval is not automatically appropriate.

### 15.2 R47 verification completed

- TypeScript/Vite production build passed; the existing large-chunk warning remains.
- 758 focused graph traces were compared against source edges, amounts and events.
- Browser checks covered eight runs, curated selection, graph-to-Trace navigation, every Trace page, near-marker globe clicks, inline Leads, missing-stage guards, research windows, offline/reduced-motion paths and mobile overflow. There were zero page errors and external requests.
- Five archived signed packet downloads matched their original bytes and SHA-256 values.
- API and new Origin regression: 27 passed with the known quarantine test excluded. Four temporal graph contract tests passed. This is not a claim that every release gate is green.

### 15.3 Promotion sequence

Freeze legacy captures, models and metrics. Persist causal ownership and address/window representations. Freeze the approved model feature order, calibration and queue policy before untouched tests. Route outputs into active cases with capture, window, model and enrichment versions, and add the new PRAMAAN adapter. Test new packet bytes, signature and replay. Package offline and verify on a clean host. Evaluate fresh worlds and observer conditions separately from public data tasks. Only then switch the default; retain the prior engine for reproducible archive views.

One approved CPU engine is recommended, with research comparisons outside automatic forensic selection. Rich graph-context trees are the practical next candidate; the trained typed temporal GRU is a real challenger. Larger TGN/TGAT/HGT models, contrastive pretraining, uncertainty-aware partitions and graph attribution remain future experiments when they address a measured workflow gap.

## 16. Embedded reference appendices

The following appendices were generated from the inspected source rather than manually retyping schemas. They preserve field order, units in names, feature order, all literal/derived parameter expressions and module interfaces. Long function implementations are not copied wholesale: the architecture above explains their behavior, and the exact source digest provides the review boundary. Changes to source after this snapshot require regenerating/reviewing this document rather than claiming it automatically remains current.


**Reading the source appendices:** docstrings can retain historical assumptions (for example the original interpretation of the 0.36 ownership weight). The explicit implementation-status and evidence-semantics sections above govern this snapshot; source comments are not independent empirical or legal evidence.

### Appendix A — exact default world configuration

This is `run_config.json` at this snapshot; per-run `config.effective.json` takes precedence.

```json
{
  "seed": 42,
  "target_rows": 1000000,
  "mean_announcements_per_tx": 27,
  "world": {
    "n_entities": 20000,
    "illicit_entity_share": 0.05,
    "illicit_tx_share": 0.03,
    "cgnat_share_individuals": 0.35,
    "cgnat_share_mules": 0.3,
    "cgnat_addresses_per_region": 64,
    "ips_per_entity": [1, 3],
    "ipv6_share": 0.06,
    "ip_pools": {
      "ipv4": "198.18.0.0/15",
      "cgnat": "100.64.0.0/10",
      "ipv6": "2001:db8::/32"
    },
    "active_hours_len": [7, 17]
  },
  "chain": {
    "start_height": 880000,
    "genesis_us": 1767225600000000,
    "block_interval_s": 600,
    "txs_per_block": 30,
    "min_blocks": 144,
    "coinbase_subsidy_sats": 312500000,
    "coinbase_maturity_blocks": 100,
    "pool_payout_interval_blocks": 4,
    "pool_payout_outputs": [4, 12],
    "hashrate_dist": {"mu": 0.0, "sigma": 1.1},
    "dust_threshold_sats": 546,
    "min_payment_sats": 1000,
    "multi_input_rate": 0.35,
    "multi_input_controller_gain": 1.0,
    "collaborative_multi_input_rate": 0.05,
    "max_pick_attempts": 8,
    "coin_select_window": 40,
    "address_reuse_rate": 0.3,
    "round_payment_rate": 0.18,
    "round_to_sats": 100000,
    "endowment": {"utxos_per_entity": [1, 4], "mu_offset": 2.5, "sigma": 1.0},
    "fee_rate": {"mu": 2.3, "sigma": 0.9, "min_sat_per_vb": 1, "max_sat_per_vb": 500},
    "script_type_weights": {
      "p2wpkh": 0.55,
      "p2pkh": 0.14,
      "p2sh": 0.12,
      "p2tr": 0.14,
      "p2wsh": 0.05
    },
    "vsize": {
      "overhead_vb": 11,
      "input_vb": {"p2pkh": 148, "p2sh": 91, "p2wpkh": 68, "p2wsh": 105, "p2tr": 58},
      "output_vb": {"p2pkh": 34, "p2sh": 32, "p2wpkh": 31, "p2wsh": 43, "p2tr": 43}
    }
  },
  "types": {
    "individual": {
      "share": 0.55, "tx_rate": 1.0, "receive_rate": 1.0, "value": {"mu": 13.12, "sigma": 1.3},
      "n_addresses": [1, 2], "reuse_rate": 0.35, "change_policy": "fresh",
      "outputs": [1, 1], "equal_outputs": false, "illicit_capable": false
    },
    "merchant": {
      "share": 0.12, "tx_rate": 6.0, "receive_rate": 12.0, "value": {"mu": 14.51, "sigma": 1.1},
      "n_addresses": [2, 6], "reuse_rate": 0.5, "change_policy": "fresh",
      "outputs": [1, 2], "equal_outputs": false, "illicit_capable": false
    },
    "exchange": {
      "share": 0.04, "tx_rate": 60.0, "receive_rate": 40.0, "value": {"mu": 15.42, "sigma": 1.6},
      "n_addresses": [20, 80], "reuse_rate": 0.9, "change_policy": "reuse",
      "outputs": [1, 4], "equal_outputs": false, "illicit_capable": false
    },
    "mining_pool": {
      "share": 0.01, "tx_rate": 4.0, "receive_rate": 0.5, "value": {"mu": 14.51, "sigma": 0.9},
      "n_addresses": [2, 5], "reuse_rate": 0.85, "change_policy": "reuse",
      "outputs": [4, 12], "equal_outputs": false, "illicit_capable": false
    },
    "service": {
      "share": 0.08, "tx_rate": 20.0, "receive_rate": 15.0, "value": {"mu": 12.21, "sigma": 1.4},
      "n_addresses": [10, 30], "reuse_rate": 0.7, "change_policy": "reuse",
      "outputs": [1, 3], "equal_outputs": false, "illicit_capable": false
    },
    "mixer": {
      "share": 0.02, "tx_rate": 8.0, "receive_rate": 6.0, "value": {"mu": 13.82, "sigma": 0.6},
      "n_addresses": [5, 20], "reuse_rate": 0.05, "change_policy": "fresh",
      "outputs": [4, 8], "equal_outputs": true, "illicit_capable": true
    },
    "darknet_market": {
      "share": 0.02, "tx_rate": 5.0, "receive_rate": 10.0, "value": {"mu": 12.61, "sigma": 1.2},
      "n_addresses": [4, 12], "reuse_rate": 0.3, "change_policy": "fresh",
      "outputs": [1, 2], "equal_outputs": false, "illicit_capable": true
    },
    "ransomware": {
      "share": 0.01, "tx_rate": 2.0, "receive_rate": 3.0, "value": {"mu": 16.52, "sigma": 1.0},
      "n_addresses": [1, 2], "reuse_rate": 0.05, "change_policy": "fresh",
      "outputs": [1, 1], "equal_outputs": false, "illicit_capable": true
    },
    "scam": {
      "share": 0.03, "tx_rate": 4.0, "receive_rate": 8.0, "value": {"mu": 13.59, "sigma": 1.5},
      "n_addresses": [2, 5], "reuse_rate": 0.15, "change_policy": "fresh",
      "outputs": [1, 1], "equal_outputs": false, "illicit_capable": true
    },
    "mule": {
      "share": 0.12, "tx_rate": 1.5, "receive_rate": 2.0, "value": {"mu": 13.82, "sigma": 1.1},
      "n_addresses": [1, 1], "reuse_rate": 0.05, "change_policy": "fresh",
      "outputs": [1, 1], "equal_outputs": false, "illicit_capable": true
    }
  },
  "validation": {
    "value_p99_over_p50_min": 8.0,
    "value_p999_over_p50_min": 25.0,
    "multi_input_rate_tolerance": 0.2,
    "announcements_per_tx_tolerance": 0.35,
    "origin_recoverable_min": 0.25,
    "first_seen_leakage_min": 0.15,
    "first_seen_leakage_max": 0.6,
    "trivial_rule_max": 0.35,
    "tree_leakage_max": 0.35,
    "delay_cv_min": 0.5,
    "block_interval_cv_min": 0.7,
    "block_interval_cv_max": 1.3
  },
  "eval": {
    "train_fraction": 0.7,
    "margin_floor": 0.04,
    "min_announcements": 2,
    "coverage_target": 0.9
  },
  "network": {
    "n_nodes": 5000,
    "outbound_per_node": 8,
    "max_inbound": 125,
    "relay_delay_outbound_mean_s": 2.0,
    "relay_delay_inbound_mean_s": 5.0,
    "latency_matrix": "regions.yaml",
    "observer_regime": "agency",
    "observer_regimes": {
      "agency": {"observer_fraction": 0.6, "n_observers": 48, "placement": "asn_ixp_biased"},
      "stealth": {"observer_fraction": 0.1, "n_observers": 16, "placement": "uniform"}
    },
    "tor_share": 0.04,
    "vpn_share": 0.08,
    "bucket_penalty": 0.15,
    "flood_frontier": 64,
    "n_tor_exits": 40,
    "n_vpn_nodes": 120,
    "unresolved_asn_share": 0.02,
    "unresolved_geo_share": 0.01,
    "inv_share": 0.9,
    "listen_port": 8333,
    "ephemeral_ports": [32768, 60999],
    "ip_pools": {
      "observer": "198.51.100.0/24",
      "tor_exit": "192.0.2.0/24",
      "vpn": "203.0.113.0/24"
    },
    "tor_asn": 64510,
    "vpn_asn": 64511
  },
  "adversary": {
    "n_campaigns": 120,
    "moves_per_campaign": [3, 40],
    "risk_appetite_dist": "uniform",
    "structuring_threshold_sats": 1000000,
    "peel_share": [0.05, 0.2],
    "split_outputs": [4, 12],
    "mix_outputs": [4, 8],
    "merge_inputs": [3, 8],
    "dwell_blocks": [2, 12],
    "move_gap_blocks": [1, 4],
    "move_weights": {
      "peel": [0.3, 0.05],
      "split": [0.1, 0.14],
      "merge": [0.08, 0.1],
      "mix": [0.12, 0.06],
      "hop": [0.05, 0.35],
      "structure": [0.15, 0.08],
      "dwell": [0.18, 0.04],
      "cash_out": [0.02, 0.18]
    }
  },
  "export": {
    "shard_rows": 250000,
    "formats": ["csv", "jsonl"],
    "xml_sample_rows": 500
  }
}
```

### Appendix B — exact ordered detector inputs and definitions

| Position | Default input | Meaning | Kept in causal local 23 |
| --- | --- | --- | --- |
| 1 | `n_addresses` | how many of its addresses were active in its window | Yes |
| 2 | `n_tx_sent` | transactions it sent in its window | Yes |
| 3 | `total_sent_sats` | satoshis it sent in its window | Yes |
| 4 | `mean_sent_sats` | average size of its sends | Yes |
| 5 | `n_tx_received` | transactions that paid it in its window | Yes |
| 6 | `total_received_sats` | satoshis it received in its window | Yes |
| 7 | `mean_received_sats` | average size of its receipts | Yes |
| 8 | `balance_sats` | received minus sent inside its window | Yes |
| 9 | `n_counterparties` | distinct wallets it transacted with | Yes |
| 10 | `max_fan_out` | most addresses it paid in a single transaction | Yes |
| 11 | `n_coinbase_received` | block rewards it collected; mining pools look like this | Yes |
| 12 | `frac_equal_outputs` | share of its transactions with equal-value outputs, a coinjoin mark | Yes |
| 13 | `mean_fee_rate` | average fee per vbyte its sends paid | Yes |
| 14 | `median_dwell_us` | typical gap between one of its receipts and its next send | Yes |
| 15 | `min_edge_confidence` | confidence of the weakest link holding its cluster together | Yes |
| 16 | `n_heuristics` | how many clustering heuristics contributed to its cluster | Yes |
| 17 | `n_script_types` | distinct address formats its active addresses use | Yes |
| 18 | `mean_p_origin` | average origin confidence on the transactions it sent | No |
| 19 | `mean_origin_margin` | how far ahead the top origin candidate usually was | No |
| 20 | `frac_origin_abstained` | share of its sends the origin estimator refused to answer | No |
| 21 | `frac_top1_tor` | share of its sends whose top origin candidate is a Tor exit | No |
| 22 | `mean_p_asn` | average confidence in the network operator behind the transactions it sent | No |
| 23 | `mean_asn_margin` | how far ahead the top operator usually was of the runner-up | No |
| 24 | `frac_l1_abstained` | share of its sends where no single operator could be named | No |
| 25 | `mean_n_announcements` | average propagation breadth of its sends | No |
| 26 | `n_typologies` | distinct laundering morphologies SHASTRA flagged on its sends in its window | No |
| 27 | `n_typology_txns` | transactions it sent in its window that fed a SHASTRA typology hit | No |
| 28 | `fan_in_ratio` | most addresses it consolidated into a single transaction | Yes |
| 29 | `peel_chain_depth` | longest run of peel-style sends (one payment plus change) it made | Yes |
| 30 | `peel_leak_frac` | average share of value leaving as the payment, not the change, in those peels | Yes |
| 31 | `structuring_frac` | share of its sends whose amounts sit just under round-number thresholds | Yes |
| 32 | `burstiness` | how clustered in time its sends are (coefficient of variation of the gaps) | Yes |
| 33 | `fee_anomaly` | how far its fee rate sat from the going rate in its window, on average | Yes |

These are source glosses, not substitutes for exact aggregation semantics. The following implementation excerpts specify the local morphology and corrected snapshot value features.

#### `src/chakravyuh/buddhi/features.py::morphology`

```python
def morphology(transactions: pl.DataFrame, sent_pairs: pl.DataFrame) -> pl.DataFrame:
    """Six transaction-shape features over the subject's in-window sends, joined on subject_id.

    `transactions` is the window's transactions (already sliced by the boundary in `build`), and
    `sent_pairs` is `(subject_id, txid)` restricted to each subject's window; joining them gives the
    transactions each subject sent and nothing else — the same windowing every other feature obeys.
    A subject that sent nothing has no row here and reads as zero after the caller's `fill_null(0)`,
    the same "the detector ran and found nothing" convention the typology block uses.
    """
    if sent_pairs.is_empty():
        return pl.DataFrame(schema=MORPHOLOGY_SCHEMA)

    # The window's going fee rate; every send's deviation is measured against this one scalar.
    window_fee_median = pl.lit(
        transactions.select(pl.col("fee_rate_sat_vb").median()).item(), dtype=pl.Float64
    )
    tx = transactions.select(
        "txid",
        "first_seen_us",
        "n_out",
        "total_out_sats",
        "fee_rate_sat_vb",
        pl.col("input_addresses").list.len().alias("n_in"),
        pl.col("output_amounts").list.min().alias("min_out"),
        pl.col("output_amounts").list.max().alias("max_out"),
        pl.col("output_amounts"),
    )
    sent = sent_pairs.select("subject_id", "txid").unique().join(tx, on="txid", how="inner")

    # fan_in_ratio mirrors `max_fan_out`'s max-over-sent-txs shape, on the input count instead.
    fan_in = sent.group_by("subject_id", maintain_order=True).agg(
        pl.col("n_in").max().cast(pl.Int32()).alias("fan_in_ratio")
    )

    # ponytail: subject-grain peel count, not the full graph tracer (P2)
    # A peel: one input, two outputs, the smaller under a quarter of the larger (payment + change,
    # not a coinjoin-style split). `min_out * 4 < max_out` keeps the test int64-clean.
    peels = sent.filter(
        (pl.col("n_in") == 1) & (pl.col("n_out") == 2) & (pl.col("min_out") * 4 < pl.col("max_out"))
    )
    peel = (
        peels.with_columns((pl.col("min_out") / pl.col("total_out_sats")).alias("_leak"))
        .group_by("subject_id", maintain_order=True)
        .agg(
            pl.len().cast(pl.Int32()).alias("peel_chain_depth"),
            pl.col("_leak").mean().alias("peel_leak_frac"),
        )
    )

    # ponytail: fixed round-threshold ladder, not learned (P2)
    band = pl.lit(False)
    for t in _STRUCTURING_LADDER:
        band = band | ((pl.element() >= int(t * 0.9)) & (pl.element() < t))
    structuring = (
        sent.with_columns(pl.col("output_amounts").list.eval(band).list.any().alias("_structured"))
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("_structured").mean().cast(pl.Float64).alias("structuring_frac"))
    )

    # burstiness: coefficient of variation of successive send gaps; 0.0 under three sends (fewer
    # than two gaps) or when every send shares a timestamp (mean gap zero, no spread to speak of).
    gaps = (
        sent.sort("first_seen_us")
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("first_seen_us").sort().diff().drop_nulls().alias("_gaps"))
    )
    burst = gaps.with_columns(
        pl.when((pl.col("_gaps").list.len() < 2) | (pl.col("_gaps").list.mean() == 0))
        .then(pl.lit(0.0))
        .otherwise(pl.col("_gaps").list.std() / pl.col("_gaps").list.mean())
        .cast(pl.Float64())
        .alias("burstiness")
    ).select("subject_id", "burstiness")

    fee = (
        sent.with_columns((pl.col("fee_rate_sat_vb") - window_fee_median).alias("_dev"))
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("_dev").mean().cast(pl.Float64).alias("fee_anomaly"))
    )

    result = fan_in
    for other in (peel, structuring, burst, fee):
        result = result.join(other, on="subject_id", how="full", coalesce=True)
    return result.select(list(MORPHOLOGY_SCHEMA))
```

#### `src/chakravyuh/buddhi/snapshot.py::_flow_features`

```python
def _flow_features(transactions: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:
    """Exact gross input/output values per subject/transaction; counterparties are subjects.

    The legacy aggregate repeats a transaction's total output for every participating address.
    Here lists are exploded together, then aggregated once per subject/transaction. Gross input
    value includes subsequently returned change; it is not an inferred external payment amount.
    """
    inputs = (
        transactions.select(
            "txid",
            pl.col("input_addresses").alias("address"),
            pl.col("input_amounts").alias("value_sats"),
        )
        .explode("address", "value_sats")
        .drop_nulls("address")
    )
    outputs = (
        transactions.select(
            "txid",
            pl.col("output_addresses").alias("address"),
            pl.col("output_amounts").alias("value_sats"),
        )
        .explode("address", "value_sats")
        .drop_nulls("address")
    )
    sent = (
        inputs.join(members, on="address")
        .group_by("subject_id", "txid")
        .agg(pl.col("value_sats").sum().alias("value_sats"))
    )
    received = (
        outputs.join(members, on="address")
        .group_by("subject_id", "txid")
        .agg(pl.col("value_sats").sum().alias("value_sats"))
    )
    sent_summary = sent.group_by("subject_id").agg(
        pl.col("value_sats").sum().alias("total_sent_sats"),
        pl.col("value_sats").mean().alias("mean_sent_sats"),
    )
    sent_summary = sent_summary.join(
        sent.join(transactions.select("txid", "fee_rate_sat_vb", "has_equal_outputs"), on="txid")
        .group_by("subject_id")
        .agg(
            pl.col("fee_rate_sat_vb").mean().alias("mean_fee_rate"),
            pl.col("has_equal_outputs").mean().alias("frac_equal_outputs"),
        ),
        on="subject_id",
    )
    received_summary = received.group_by("subject_id").agg(
        pl.col("value_sats").sum().alias("total_received_sats"),
        pl.col("value_sats").mean().alias("mean_received_sats"),
    )
    relations = (
        pl.concat(
            [
                sent.select("subject_id", "txid").join(
                    outputs.select("txid", "address"), on="txid"
                ),
                received.select("subject_id", "txid").join(
                    inputs.select("txid", "address"), on="txid"
                ),
            ]
        )
        .join(members.select(pl.col("subject_id").alias("other_subject"), "address"), on="address")
        .filter(pl.col("subject_id") != pl.col("other_subject"))
    )
    counterparties = relations.group_by("subject_id").agg(
        pl.col("other_subject").n_unique().alias("n_counterparties")
    )
    return sent_summary.join(received_summary, on="subject_id", how="full", coalesce=True).join(
        counterparties, on="subject_id", how="full", coalesce=True
    )
```

#### `src/chakravyuh/buddhi/relational_inference.py::_scale`

```python
def _scale(values: NDArray[Any], parameters: dict[str, Any]) -> NDArray[np.float32]:
    mean = np.asarray(parameters["mean"], dtype=np.float64)
    scale = np.asarray(parameters["scale"], dtype=np.float64)
    if mean.shape != (values.shape[1],) or scale.shape != mean.shape:
        raise ValueError("scaler width mismatch")
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("invalid frozen scaler")
    return ((values - mean) / scale).astype(np.float32)
```

#### `src/chakravyuh/buddhi/relational_inference.py::_pool`

```python
def _pool(values: NDArray[np.float32], edges: NDArray[np.int64], size: int) -> NDArray[np.float32]:
    total = np.zeros((size, values.shape[1]), dtype=np.float32)
    count = np.zeros((size, 1), dtype=np.float32)
    np.add.at(total, edges[1], values[edges[0]])
    np.add.at(count, edges[1], 1)
    return (total / np.maximum(count, 1)).astype(np.float32)
```

#### `src/chakravyuh/buddhi/relational_inference.py::_summaries`

```python
def _summaries(
    context: NDArray[np.float32], edges: NDArray[np.int64], size: int
) -> NDArray[np.float32]:
    source, target = edges
    values = context[source].astype(np.float64)
    count = np.bincount(target, minlength=size)
    total = np.zeros((size, context.shape[1]))
    squares = np.zeros_like(total)
    low, high = np.full_like(total, np.inf), np.full_like(total, -np.inf)
    np.add.at(total, target, values)
    np.add.at(squares, target, values**2)
    np.minimum.at(low, target, values)
    np.maximum.at(high, target, values)
    mean = total / np.maximum(count[:, None], 1)
    std = np.sqrt(np.maximum(squares / np.maximum(count[:, None], 1) - mean**2, 0))
    low[count == 0], high[count == 0] = 0, 0
    return np.column_stack([np.log1p(count), mean, std, low, high]).astype(np.float32)
```

#### `src/chakravyuh/vaani/investigation.py::select`

```python
def select(
    ranked: list[str],
    supports: dict[str, set[str]],
    *,
    k: int,
    overlap: float | None,
) -> list[str]:
    """Select evidence-diverse leads without labels or assumptions about ownership."""
    if k < 1 or (overlap is not None and not 0 <= overlap <= 1):
        raise ValueError("invalid lead selection parameters")
    chosen: list[str] = []
    used: list[set[str]] = []
    for subject in ranked:
        current = supports.get(subject, set())
        if not current:
            continue
        if overlap is not None and any(
            len(current & old) / len(current | old) > overlap for old in used
        ):
            continue
        chosen.append(subject)
        used.append(current)
        if len(chosen) == k:
            break
    return chosen
```

### Appendix C — declared stage schemas and parameter expressions

Exact Python expressions preserve types, feature order and derived constants. Constants in evaluation modules are policy/test configuration, not detector inputs.

#### `src/chakravyuh/api/app.py`

```python
BIND_HOST = "127.0.0.1"

BIND_PORT = 8000

RUN_ENV = "CHAKRAVYUH_RUN"

GENERATED_ROOT = "data/generated"

_RUN_DIR: Path | None = None
```

#### `src/chakravyuh/api/serialize.py`

```python
SEALED_DIR = "sealed"

NORMALISED_DIR = "normalised"

GRAPH_DIR = "graph"

SIGNALS_DIR = "signals"

SCORES_DIR = "scores"

ALERTS_DIR = "alerts"

PACKETS_DIR = "packets"

ENSEMBLE = "ensemble"

LABEL_QUEUE = ("LIKELY_ILICIT", "UNCLEAR")

DEFAULT_NODE_CAP = 2000

STAGE_LAMPS: tuple[tuple[str, str, str], ...] = (
    ("L0", "kavach", f"{SEALED_DIR}/manifest.json"),
    ("L1", "setu", f"{NORMALISED_DIR}/_meta.json"),
    ("L2", "jaal", f"{GRAPH_DIR}/_meta.json"),
    ("L3", "shastra", f"{SIGNALS_DIR}/_meta.json"),
    ("L4", "buddhi", f"{SCORES_DIR}/_meta.json"),
    ("L5", "vaani", f"{ALERTS_DIR}/_meta.json"),
    ("L6", "pramaan", f"{PACKETS_DIR}/merkle.log"),
)

LABEL_DISPLAY = {
    "LIKELY_ILICIT": "LIKELY_ILLICIT",
    "LIKELY_LICIT": "LIKELY_LICIT",
    "UNCLEAR": "UNCLEAR",
}

ORIGIN_FEATURE_GLOSS: tuple[tuple[str, str, str], ...] = (
    (
        "delta_first_us",
        "first-announcement lead",
        "how long after the transaction was first seen this peer announced it; "
        "the origin is usually first",
    ),
    (
        "rank_in_tx",
        "announcement rank",
        "this peer's position in the order peers announced the transaction",
    ),
    (
        "n_candidates",
        "competing peers",
        "how many peers announced the transaction and could be its origin",
    ),
    (
        "peer_frac_rank_one",
        "first-seen habit",
        "the share of this peer's transactions on which it announced first",
    ),
    (
        "peer_n_txids",
        "peer activity",
        "how many distinct transactions this peer has been seen announcing",
    ),
    ("net_class", "network class", "the kind of network the peer's address sits in"),
    (
        "is_tor_exit",
        "Tor exit",
        "whether the peer is a known Tor exit, where origin cannot be attributed to a subscriber",
    ),
    (
        "is_hosting",
        "hosting network",
        "whether the peer sits in a datacentre rather than on a residential line",
    ),
    (
        "announce_spread_us",
        "announcement spread",
        "the time between the first and last announcement of the transaction",
    ),
    (
        "n_observers_seen",
        "monitors that saw it",
        "how many capture nodes recorded this peer's announcement",
    ),
)

ACTOR_NODE_KINDS: Final[tuple[str, ...]] = ("address", "cluster")

ACTOR_EDGE_KINDS: Final[tuple[str, ...]] = ("SAME_OWNER", "MEMBER_OF")

GRAPH_NODE_KINDS: Final[tuple[str, ...]] = ("address", "transaction", "peer", "cluster", "asn")

GRAPH_EDGE_KINDS: Final[tuple[str, ...]] = (
    "SPENDS",
    "RECEIVES",
    "ANNOUNCED_BY",
    "SAME_OWNER",
    "HOSTED_IN",
    "MEMBER_OF",
)

EMPTY_ACTOR_SCORES: Final[dict[str, Any]] = {
    "degree": 0,
    "weakest_confidence": None,
    "strongest_confidence": None,
    "cluster_id": None,
    "n_transactions": None,
    "n_coinjoin": None,
    "n_peel_hops": None,
    "peel_chains": [],
}

LITERATURE_BAND: tuple[float, float] = (0.11, 0.60)

DEFENCES: tuple[str, ...] = (
    "observer curve",
    "elliptic replication",
    "real-slice",
    "parameter holdout",
)

REJECTED_LEG: dict[str, Any] = {
    "with_embeddings_pr_auc": 0.0357,
    "without_embeddings_pr_auc": 0.0373,
    "gate": "baseline_not_beaten",
}

PUBLISHED_BANDS: dict[str, list[float]] = {"gnn_f1": [0.70, 0.82], "rf_f1": [0.60, 0.70]}

FUNNEL_STAGES: tuple[tuple[str, str, str], ...] = (
    ("globe", "signals", "MAYAJAAL"),
    ("intake", "sealed", "KAVACH"),
    ("untangle", "announcements", "SETU"),
    ("map", "transactions", "JAAL"),
    ("origin", "with a candidate", "SHASTRA"),
    ("buddhi", "owner groups scored", "BUDDHI"),
    ("leads", "ranked leads", "VAANI"),
    ("proof", "court-ready proofs", "PRAMAAN"),
)
```

#### `src/chakravyuh/buddhi/__main__.py`

```python
METRICS_ROOT = getattr(run_roots(Path("data/generated/_")), "measure" + "ments").parent

LEG_NOT_REQUESTED: Final[str] = "embeddings_not_requested"

LEG_NO_ROWS: Final[str] = "no_row_scored_by_the_gnn_booster"

LEG_NO_COUNTERFACTUAL: Final[str] = "no_counterfactual_measured"

LEG_BASELINE_NOT_BEATEN: Final[str] = "baseline_not_beaten"

LEG_DID_NOT_BEAT: Final[str] = "gnn_does_not_beat_baseline"

LEG_NOT_SCORED: Final[str] = "not_scored_no_answer_key"
```

#### `src/chakravyuh/buddhi/embed.py`

```python
DIM: Final[int] = 8

HOPS: Final[int] = 2

_KIND_RE: Final[str] = r"^([^:]+):"

SUBJECT_ONLY: Final[dict[str, pl.DataType]] = {"subject_id": pl.String()}
```

#### `src/chakravyuh/buddhi/features.py`

```python
TRANSACTION_COLUMNS = (
    "txid",
    "first_seen_us",
    "n_out",
    "input_addresses",
    "output_addresses",
    "output_amounts",
    "total_out_sats",
    "fee_rate_sat_vb",
    "is_coinbase",
    "has_equal_outputs",
)

CLUSTER_COLUMNS = ("cluster_id", "addresses")

EDGE_COLUMNS = ("src", "dst", "kind", "confidence", "evidence", "sats")

ADDRESS_COLUMNS = ("address", "script_type")

ORIGIN_ESTIMATE_COLUMNS = ("txid", "p_origin", "rank", "margin", "abstain", "features")

ORIGIN_L1_COLUMNS = ("txid", "p_asn", "margin", "abstain")

ENSEMBLE: Final[str] = "ensemble"

MODEL_FEATURES: tuple[str, ...] = (
    "n_addresses",
    "n_tx_sent",
    "total_sent_sats",
    "mean_sent_sats",
    "n_tx_received",
    "total_received_sats",
    "mean_received_sats",
    "balance_sats",
    "n_counterparties",
    "max_fan_out",
    "n_coinbase_received",
    "frac_equal_outputs",
    "mean_fee_rate",
    "median_dwell_us",
    "min_edge_confidence",
    "n_heuristics",
    "n_script_types",
    "mean_p_origin",
    "mean_origin_margin",
    "frac_origin_abstained",
    "frac_top1_tor",
    "mean_p_asn",
    "mean_asn_margin",
    "frac_l1_abstained",
    "mean_n_announcements",
    "n_typologies",
    "n_typology_txns",
    "fan_in_ratio",
    "peel_chain_depth",
    "peel_leak_frac",
    "structuring_frac",
    "burstiness",
    "fee_anomaly",
)

EMBEDDING_FEATURES: tuple[str, ...] = tuple(f"embed_{i:02d}" for i in range(embed.DIM))

ALL_FEATURES: tuple[str, ...] = MODEL_FEATURES + EMBEDDING_FEATURES

EMBEDDING_GLOSS: Final[str] = (
    "one direction of the graph embedding: a two-hop structural summary of the dual graph, "
    "computed with no labels"
)

FEATURE_GLOSSES: tuple[tuple[str, str], ...] = (
    ("n_addresses", "how many of its addresses were active in its window"),
    ("n_tx_sent", "transactions it sent in its window"),
    ("total_sent_sats", "satoshis it sent in its window"),
    ("mean_sent_sats", "average size of its sends"),
    ("n_tx_received", "transactions that paid it in its window"),
    ("total_received_sats", "satoshis it received in its window"),
    ("mean_received_sats", "average size of its receipts"),
    ("balance_sats", "received minus sent inside its window"),
    ("n_counterparties", "distinct wallets it transacted with"),
    ("max_fan_out", "most addresses it paid in a single transaction"),
    ("n_coinbase_received", "block rewards it collected; mining pools look like this"),
    ("frac_equal_outputs", "share of its transactions with equal-value outputs, a coinjoin mark"),
    ("mean_fee_rate", "average fee per vbyte its sends paid"),
    ("median_dwell_us", "typical gap between one of its receipts and its next send"),
    ("min_edge_confidence", "confidence of the weakest link holding its cluster together"),
    ("n_heuristics", "how many clustering heuristics contributed to its cluster"),
    ("n_script_types", "distinct address formats its active addresses use"),
    ("mean_p_origin", "average origin confidence on the transactions it sent"),
    ("mean_origin_margin", "how far ahead the top origin candidate usually was"),
    ("frac_origin_abstained", "share of its sends the origin estimator refused to answer"),
    ("frac_top1_tor", "share of its sends whose top origin candidate is a Tor exit"),
    ("mean_p_asn", "average confidence in the network operator behind the transactions it sent"),
    ("mean_asn_margin", "how far ahead the top operator usually was of the runner-up"),
    ("frac_l1_abstained", "share of its sends where no single operator could be named"),
    ("mean_n_announcements", "average propagation breadth of its sends"),
    ("n_typologies", "distinct laundering morphologies SHASTRA flagged on its sends in its window"),
    ("n_typology_txns", "transactions it sent in its window that fed a SHASTRA typology hit"),
    ("fan_in_ratio", "most addresses it consolidated into a single transaction"),
    ("peel_chain_depth", "longest run of peel-style sends (one payment plus change) it made"),
    (
        "peel_leak_frac",
        "average share of value leaving as the payment, not the change, in those peels",
    ),
    ("structuring_frac", "share of its sends whose amounts sit just under round-number thresholds"),
    ("burstiness", "how clustered in time its sends are (coefficient of variation of the gaps)"),
    ("fee_anomaly", "how far its fee rate sat from the going rate in its window, on average"),
) + tuple((name, EMBEDDING_GLOSS) for name in EMBEDDING_FEATURES)

AGGREGATE_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "n_tx_sent": pl.Int32(),
    "total_sent_sats": pl.Int64(),
    "mean_sent_sats": pl.Float64(),
    "mean_fee_rate": pl.Float64(),
    "frac_equal_outputs": pl.Float64(),
    "max_fan_out": pl.Int32(),
    "n_tx_received": pl.Int32(),
    "total_received_sats": pl.Int64(),
    "mean_received_sats": pl.Float64(),
    "n_coinbase_received": pl.Int32(),
    "balance_sats": pl.Int64(),
    "n_counterparties": pl.Int32(),
    "median_dwell_us": pl.Float64(),
}

MORPHOLOGY_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "fan_in_ratio": pl.Int32(),
    "peel_chain_depth": pl.Int32(),
    "peel_leak_frac": pl.Float64(),
    "structuring_frac": pl.Float64(),
    "burstiness": pl.Float64(),
    "fee_anomaly": pl.Float64(),
}

_STRUCTURING_LADDER: Final[tuple[int, ...]] = (100_000, 1_000_000, 10_000_000, 100_000_000)

ASN_FUSION_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "mean_p_asn": pl.Float64(),
    "mean_asn_margin": pl.Float64(),
    "frac_l1_abstained": pl.Float64(),
}
```

#### `src/chakravyuh/buddhi/model.py`

```python
BOOST_ROUNDS: Final[int] = 300

TREE_PARAMS: Final[dict[str, Any]] = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 40,
    "lambda_l2": 1.0,
    "feature_fraction": 1.0,
    "bagging_fraction": 1.0,
    "num_threads": 1,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
    "seed": 0,
}

CALIBRATION_SHARE: Final[float] = 0.25

MIN_CALIBRATION_ROWS: Final[int] = 50

MIN_CALIBRATION_PER_CLASS: Final[int] = 10

TOP_FEATURES: Final[int] = 5
```

#### `src/chakravyuh/buddhi/relational_inference.py`

```python
TX_FEATURES = (
    "n_in",
    "n_out",
    "total_out_sats",
    "fee_sats",
    "fee_rate_sat_vb",
    "has_equal_outputs",
)

IP_FEATURES = ("observations", "transactions", "observers", *(f"class_{i}" for i in range(6)))

CONTEXT = (
    *TX_FEATURES,
    *(f"announcer_mean_{n}" for n in IP_FEATURES),
    *(f"funder_mean_{n}" for n in snapshot.SNAPSHOT_FEATURES),
)

FEATURES = (
    *snapshot.SNAPSHOT_FEATURES,
    *(
        n
        for relation in ("received", "spent")
        for n in (
            f"{relation}_log_degree",
            *(
                f"{relation}_{stat}_{field}"
                for stat in ("mean", "std", "min", "max")
                for field in CONTEXT
            ),
        )
    ),
)
```

#### `src/chakravyuh/buddhi/snapshot.py`

```python
SNAPSHOT_FEATURES = tuple(
    name
    for name in features.MODEL_FEATURES
    if name
    not in {
        "mean_p_origin",
        "mean_origin_margin",
        "frac_origin_abstained",
        "frac_top1_tor",
        "mean_p_asn",
        "mean_asn_margin",
        "frac_l1_abstained",
        "mean_n_announcements",
        "n_typologies",
        "n_typology_txns",
    }
)
```

#### `src/chakravyuh/buddhi/stage.py`

```python
INPUT_ROOT: Final[str] = "data"

OUTPUT_ROOT: Final[str] = "data/generated"

OUT_DIR: Final[str] = "scores"

REQUIRED_TABLES: Final[tuple[str, ...]] = ("transactions.parquet", "addresses.parquet")

SIGNALS_DIR: Final[str] = "signals"

SIGNALS_TABLE: Final[str] = "origin_estimates.parquet"

L1_TABLE: Final[str] = "origin_l1.parquet"

GRAPH_DIR: Final[str] = "graph"

GRAPH_TABLES: Final[tuple[str, ...]] = ("clusters.parquet", "edges.parquet")

CONFIG_NAME: Final[str] = "config.effective.json"

DEFAULT_TRAIN_FRACTION: Final[float] = 0.7

DEFAULT_COVERAGE_TARGET: Final[float] = 0.9

LABEL_LIKELY_ILICIT: Final[str] = "LIKELY_ILICIT"

LABEL_UNCLEAR: Final[str] = "UNCLEAR"

LABEL_LIKELY_LICIT: Final[str] = "LIKELY_LICIT"

LABEL_ABSTAIN: Final[str] = "ABSTAIN"

CONFORMAL_BAND: Final[float] = 0.15

MODEL_NAME: Final[str] = "gbm_v2"

MODEL_NAME_GNN: Final[str] = "gbm_gnn_v2"

STAGE: Final[str] = "buddhi"
```

#### `src/chakravyuh/buildinfo.py`

```python
UNKNOWN: str = "unknown"

_TIMEOUT_S: int = 10
```

#### `src/chakravyuh/eval/external.py`

```python
FEATURES_NAMES: Final[tuple[str, ...]] = ("elliptic_txs_features.csv", "txs_features.csv")

CLASSES_NAMES: Final[tuple[str, ...]] = ("elliptic_txs_classes.csv", "txs_classes.csv")

ILLICIT_CODE: Final[int] = 1

LICIT_CODE: Final[int] = 2

ABSENT: Final[dict[str, Any]] = {"available": False, "reason": "dataset_not_vendored"}

FILENAME: Final[str] = "elliptic_external.json"

NOT_RUN: Final[dict[str, Any]] = {"available": False, "reason": "not_run_for_this_run"}

CAVEAT: Final[str] = (
    "Same training procedure as our own leg (time-ordered split, same booster params, same "
    "conformal wrap) on the Elliptic transactions and the labels its authors gave them; "
    "Elliptic's own columns are not our named morphology, so this replicates the method, not "
    "the feature set."
)
```

#### `src/chakravyuh/eval/labels.py`

```python
GENERATED_ROOT = Path("data") / "generated"

GROUND_TRUTH_ROOT = Path("ground_truth")
```

#### `src/chakravyuh/eval/metrics.py`

```python
GENERATED_ROOT = Path("data") / "generated"

GROUND_TRUTH_ROOT = Path("ground_truth")

MEASUREMENTS_ROOT = Path("measurements")

ENTITIES = "entities.parquet"

ORIGINS = "origins.parquet"

TRAFFIC = ("clear", "vpn", "tor")

GRAIN_K = 3
```

#### `src/chakravyuh/eval/split.py`

```python
TRAIN = "train"

HOLDOUT = "holdout"

PROTOCOL = "inductive_time_ordered"
```

#### `src/chakravyuh/eval/validate.py`

```python
LOG = logging.getLogger("validate")

GENERATED_ROOT = writers.REPO_ROOT / "data" / "generated"

CONFIG_NAME = "config.effective.json"

MANIFEST = "_meta.json"

_TXID = re.compile(r"^[0-9a-f]{64}$")

_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$")

_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%S%.f%:z"

TRUTH_COLUMNS: tuple[str, ...] = (
    "true_origin_ip",
    "true_origin_asn",
    "true_origin_as_org",
    "true_origin_net_class",
    "true_origin_country",
    "true_origin_entity_id",
    "broadcast_us",
    "used_tor",
    "used_vpn",
    "observed_by_n",
    "entity_id",
    "entity_type",
    "input_entity_ids",
    "is_illicit",
    "typologies",
    "ips",
    "behind_cgnat",
    "heuristic_violation",
    "campaign_id",
    "entity_ids",
    "start_us",
    "end_us",
    "total_sats",
)

CONTRACT_OBSERVABLE: dict[str, frozenset[str]] = {
    # section 4, written by SETU. The deliberately weak change rule, one transaction at a time.
    "change_index": frozenset({"normalised/transactions.parquet"}),
    # section 5, written by JAAL. The addresses one clustering heuristic predicts share an owner.
    "addresses": frozenset({"graph/clusters.parquet"}),
    # section 6, written by SHASTRA. The predicted pattern and the transactions it spans.
    "typology": frozenset({"signals/typology_hits.parquet"}),
    "txids": frozenset({"signals/typology_hits.parquet"}),
}

_LIST_COLUMNS = (
    "input_addresses",
    "input_amounts",
    "output_addresses",
    "output_amounts",
    "script_types",
)

_INT_COLUMNS = ("src_port", "dst_port", "asn", "fee_sats", "vsize", "block_height")

FEATURES: tuple[str, ...] = (
    "arrival",
    "since_first",
    "n_rows",
    "is_inv",
    "src_port",
    "asn_known",
)

GROUPS = ("invariants", "manifests", "quarantine", "distributions", "leakage")
```

#### `src/chakravyuh/jaal/build.py`

```python
STAGE: Final[str] = "jaal"

HOSTING_CONFIDENCE: Final[float] = 0.95

NODES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "node_id": pl.String(),
    "kind": pl.String(),
    "label": pl.String(),
    "first_us": pl.Int64(),
    "last_us": pl.Int64(),
    # Contract section 5's two additive columns. Both describe a transaction and neither describes
    # any other node kind, so every node starts null and false here and `mark_transaction_nodes`
    # is the only writer. An address is not a chain and not a mixer, and a false that could have
    # been a null would make "not a mixer" and "not asked" the same cell.
    "peel_chain_id": pl.String(),
    "coinjoin": pl.Boolean(),
}

EDGES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "src": pl.String(),
    "dst": pl.String(),
    "kind": pl.String(),
    "ts_us": pl.Int64(),
    "sats": pl.Int64(),
    "confidence": pl.Float64(),
    "evidence": pl.String(),
}

CLUSTERS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "cluster_id": pl.String(),
    "addresses": pl.List(pl.String()),
    "n_addresses": pl.Int32(),
    "min_edge_confidence": pl.Float64(),
    "heuristics_used": pl.List(pl.String()),
    "threshold": pl.Float64(),
}

NODE_KINDS: Final[frozenset[str]] = frozenset({"address", "transaction", "peer", "cluster", "asn"})

EDGE_KINDS: Final[frozenset[str]] = frozenset(
    {"SPENDS", "RECEIVES", "ANNOUNCED_BY", "SAME_OWNER", "HOSTED_IN", "MEMBER_OF"}
)

EVIDENCE_KINDS: Final[frozenset[str]] = frozenset(
    {"multi_input", "change_addr", "observed", "geoip"}
)
```

#### `src/chakravyuh/jaal/cluster.py`

```python
MULTI_INPUT_CONFIDENCE: Final[float] = 0.36

CHANGE_ADDR_CONFIDENCE: Final[float] = 0.25

DEFAULT_THRESHOLD: Final[float] = 0.2
```

#### `src/chakravyuh/jaal/mixer.py`

```python
COINJOIN_MIN_OUTPUTS: Final[int] = 3

MIXER_MIN_INPUTS: Final[int] = 2

SET_ASIDE_REASON: Final[str] = "coinjoin_mixer"
```

#### `src/chakravyuh/jaal/provenance.py`

```python
LEDGER_SCHEMA: dict[str, pl.DataType] = {
    "src": pl.String(),
    "dst": pl.String(),
    "txid": pl.String(),
    "available_us": pl.Int64(),
    "confidence": pl.Float64(),
    "evidence": pl.String(),
}
```

#### `src/chakravyuh/jaal/stage.py`

```python
INPUT_ROOT: Final[str] = "data"

OUTPUT_ROOT: Final[str] = "data/generated"

OUT_DIR: Final[str] = "graph"

REQUIRED_TABLES: Final[tuple[str, ...]] = (
    "announcements.parquet",
    "transactions.parquet",
    "addresses.parquet",
    "peers.parquet",
)
```

#### `src/chakravyuh/jaal/trace.py`

```python
PEEL_MAX_SHARE_NUM: Final[int] = 7

PEEL_MAX_SHARE_DEN: Final[int] = 20

PEEL_MIN_HOPS: Final[int] = 2

NO_CONTINUATION: Final[str] = "no_continuation"

AMBIGUOUS_SPEND: Final[str] = "ambiguous_spend"

CHAIN_BROKEN: Final[str] = "chain_broken"

CYCLE: Final[str] = "cycle"

PEEL_CHAINS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "peel_chain_id": pl.String(),
    # The chain's transactions in hop order, first to last. Named `transactions` rather than
    # `txids` on purpose: `txids` is a name `eval/validate.py` treats as a quarantine tripwire and
    # permits in exactly one observable file (`signals/typology_hits.parquet`), and widening that
    # gate to admit a second file is a worse trade than picking a different name for a column.
    "transactions": pl.List(pl.String()),
    "depth": pl.Int32(),
    "initial_sats": pl.Int64(),
    "peeled_sats": pl.Int64(),
    "leak_frac": pl.Float64(),
    "root_address": pl.String(),
    "first_us": pl.Int64(),
    "last_us": pl.Int64(),
    "stop_reason": pl.String(),
}
```

#### `src/chakravyuh/jaal/view.py`

```python
NODE_TABLE = """
CREATE NODE TABLE IF NOT EXISTS GraphNode(
  node_id STRING, kind STRING, label STRING, first_us INT64, last_us INT64,
  PRIMARY KEY (node_id))
"""

EDGE_TABLE = """
CREATE REL TABLE IF NOT EXISTS GraphEdge(
  FROM GraphNode TO GraphNode,
  kind STRING, ts_us INT64, sats INT64, confidence DOUBLE, evidence STRING)
"""
```

#### `src/chakravyuh/kavach/schema.py`

```python
REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
    "input_addresses",
    "output_addresses",
    "input_amounts",
    "output_amounts",
)

NULLABLE_REQUIRED_COLUMNS: Final[tuple[str, ...]] = ("geo_country", "asn")

OPTIONAL_COLUMNS: Final[tuple[str, ...]] = (
    "fee_sats",
    "vsize",
    "script_types",
    "block_height",
    "msg_type",
    "observer_id",
)

PS_COLUMNS: Final[tuple[str, ...]] = (
    *REQUIRED_COLUMNS,
    *NULLABLE_REQUIRED_COLUMNS,
    *OPTIONAL_COLUMNS,
)

LIST_COLUMNS: Final[frozenset[str]] = frozenset(
    {"input_addresses", "output_addresses", "input_amounts", "output_amounts", "script_types"}
)

AMOUNT_COLUMNS: Final[tuple[str, ...]] = ("input_amounts", "output_amounts")

INT_COLUMNS: Final[frozenset[str]] = frozenset(
    {"src_port", "dst_port", "asn", "fee_sats", "vsize", "block_height"}
)

CHAIN_COLUMNS: Final[tuple[str, ...]] = (
    "input_addresses",
    "output_addresses",
    "input_amounts",
    "output_amounts",
    "fee_sats",
    "vsize",
    "script_types",
    "block_height",
)

COLUMN_ALIASES: Final[dict[str, str]] = {
    "ts": "timestamp",
    "time": "timestamp",
    "time_utc": "timestamp",
    "timestamp_utc": "timestamp",
    "source_ip": "src_ip",
    "src_addr": "src_ip",
    "peer_ip": "src_ip",
    "destination_ip": "dst_ip",
    "dst_addr": "dst_ip",
    "observer_ip": "dst_ip",
    "source_port": "src_port",
    "sport": "src_port",
    "destination_port": "dst_port",
    "dport": "dst_port",
    "tx_id": "txid",
    "tx_hash": "txid",
    "hash": "txid",
    "inputs": "input_addresses",
    "in_addresses": "input_addresses",
    "outputs": "output_addresses",
    "out_addresses": "output_addresses",
    "in_amounts": "input_amounts",
    "input_values": "input_amounts",
    "out_amounts": "output_amounts",
    "output_values": "output_amounts",
    "country": "geo_country",
    "cc": "geo_country",
    "as_number": "asn",
    "autonomous_system": "asn",
    "height": "block_height",
    "virtual_size": "vsize",
    "message_type": "msg_type",
    "command": "msg_type",
    "node_id": "observer_id",
    "sensor_id": "observer_id",
}

SATS_PER_BTC: Final[Decimal] = Decimal(100_000_000)

TXID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")

_INTEGER_RE: Final[re.Pattern[str]] = re.compile(r"^[+-]?\d+$")

_DECIMAL_RE: Final[re.Pattern[str]] = re.compile(r"^[+-]?\d*\.\d+$|^[+-]?\d+\.\d*$")

_MAGIC: Final[tuple[tuple[bytes, Container], ...]] = (
    (b"\x28\xb5\x2f\xfd", Container.ZSTD),
    (b"\x1f\x8b", Container.GZIP),
)
```

#### `src/chakravyuh/kavach/seal.py`

```python
STAGE: Final[str] = "kavach"

INPUT_ROOT: Final[str] = "data"

OUTPUT_ROOT: Final[str] = "data/generated"

CAPTURE_SUFFIXES: Final[frozenset[str]] = frozenset({".csv", ".jsonl", ".json", ".xml", ".txt"})

COMPRESSION_SUFFIXES: Final[frozenset[str]] = frozenset({".zst", ".zstd", ".gz"})

MUST_BE_PRESENT: Final[tuple[str, ...]] = (
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
)

SEALED_SCHEMA: Final[dict[str, pl.DataType]] = {
    "row_id": pl.Int64(),
    "ts_us": pl.Int64(),
    "ts_raw": pl.String(),
    "src_ip": pl.String(),
    "src_ip_version": pl.Int8(),
    "dst_ip": pl.String(),
    "src_port": pl.Int32(),
    "dst_port": pl.Int32(),
    "txid": pl.String(),
    "input_addresses": pl.List(pl.String()),
    "output_addresses": pl.List(pl.String()),
    "input_amounts": pl.List(pl.Int64()),
    "output_amounts": pl.List(pl.Int64()),
    "geo_country": pl.String(),
    "asn": pl.Int32(),
    "fee_sats": pl.Int64(),
    "vsize": pl.Int32(),
    "script_types": pl.List(pl.String()),
    "block_height": pl.Int32(),
    "msg_type": pl.String(),
    "observer_id": pl.String(),
}

REJECTED_SCHEMA: Final[dict[str, pl.DataType]] = {
    "row_id": pl.Int64(),
    "reject_reason": pl.String(),
    **{
        column: pl.List(pl.String()) if column in LIST_COLUMNS else pl.String()
        for column in PS_COLUMNS
    },
}
```

#### `src/chakravyuh/mayajaal/__main__.py`

```python
LOG = logging.getLogger("mayajaal")
```

#### `src/chakravyuh/mayajaal/adversary.py`

```python
TYPOLOGY_OF: dict[str, str] = {
    "peel": "peel_chain",
    "structure": "structuring",
    "split": "fan_out",
    "mix": "coinjoin_like",
    "hop": "pass_through",
}

_ORDER = {move: index for index, move in enumerate(TYPOLOGY_OF)}

FALLBACK_TYPOLOGY = "pass_through"

_FORWARDS = frozenset({"hop", "split", "mix", "merge"})

HEADROOM = 50

SOURCE_TYPES = frozenset({"darknet_market", "ransomware", "scam"})

RECRUITS = (2, 5)
```

#### `src/chakravyuh/mayajaal/chain.py`

```python
_NO_INTENT = Intent()
```

#### `src/chakravyuh/mayajaal/config.py`

```python
_UNSETTABLE: frozenset[str] = frozenset({"network.latency_matrix"})

_PLACEMENTS: frozenset[str] = frozenset({"asn_ixp_biased", "uniform"})

_MOVES = ("peel", "split", "merge", "mix", "hop", "structure", "dwell", "cash_out")
```

#### `src/chakravyuh/mayajaal/entities.py`

```python
ADDRESS_SHAPES: dict[str, tuple[str, int, str]] = {
    "p2pkh": ("1", 34, "z"),
    "p2sh": ("3", 34, "z"),
    "p2wpkh": ("bc1q", 42, "q"),
    "p2wsh": ("bc1q", 62, "q"),
    "p2tr": ("bc1p", 62, "q"),
}

INVALID_MARKER = "gen0i"

HOURS_PER_DAY = 24

US_PER_HOUR = 3_600_000_000
```

#### `src/chakravyuh/mayajaal/export.py`

```python
COLUMNS: tuple[str, ...] = (
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
    "input_addresses",
    "input_amounts",
    "output_addresses",
    "output_amounts",
    "geo_country",
    "asn",
    "fee_sats",
    "vsize",
    "script_types",
    "block_height",
    "msg_type",
    "observer_id",
)

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

CSV_DIR = "capture"

JSON_DIR = "capture_json"

XML_DIR = "capture_xml"
```

#### `src/chakravyuh/mayajaal/network.py`

```python
CANDIDATE_MULTIPLE = 4

_IP_DRAW_LIMIT = 64

NO_OBSERVER = -1

PEER = "peer"

TOR_EXIT = "tor_exit"

VPN = "vpn"

TOR_ORG = "Tor anonymising relay"

VPN_ORG = "Commercial VPN provider"

_HOSTING_TYPES = frozenset({"exchange", "service", "mining_pool", "mixer"})

OBSERVER_UNIFORM = "uniform"
```

#### `src/chakravyuh/mayajaal/regions.py`

```python
_INDENT = "  "
```

#### `src/chakravyuh/mayajaal/weighted.py`

```python
T = TypeVar("T")
```

#### `src/chakravyuh/mayajaal/writers.py`

```python
REPO_ROOT = _repo_root()

TRUTH_ROOT = REPO_ROOT / "ground_truth"

MEASUREMENTS_ROOT = REPO_ROOT / "measurements"

RUN_ID = re.compile(r"^[A-Za-z0-9._-]+$")

SATS = pl.Int64()

COUNT = pl.Int32()

TEXT = pl.String()

TEXTS = pl.List(pl.String)

TX_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "block_height": pl.Int64(),
    "block_time_us": pl.Int64(),
    "is_coinbase": pl.Boolean(),
    "input_txids": TEXTS,
    "input_vouts": pl.List(pl.Int32),
    "input_addresses": TEXTS,
    "input_amounts": pl.List(pl.Int64),
    "output_addresses": TEXTS,
    "output_amounts": pl.List(pl.Int64),
    "script_types": TEXTS,
    "fee_sats": SATS,
    "fee_rate_sat_vb": COUNT,
    "vsize": COUNT,
}

SEED_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "vout": COUNT,
    "address": TEXT,
    "script_type": TEXT,
    "sats": SATS,
    "height": pl.Int64(),
}

BLOCK_SCHEMA: dict[str, pl.DataType] = {
    "height": pl.Int64(),
    "time_us": pl.Int64(),
    "n_txs": COUNT,
    "coinbase_txid": TEXT,
    "subsidy_sats": SATS,
    "fees_sats": SATS,
}

ENTITY_SCHEMA: dict[str, pl.DataType] = {
    "entity_id": TEXT,
    "entity_type": TEXT,
    "is_illicit": pl.Boolean(),
    "typologies": TEXTS,
    "addresses": TEXTS,
    "ips": TEXTS,
    "behind_cgnat": pl.Boolean(),
}

CAMPAIGN_SCHEMA: dict[str, pl.DataType] = {
    "campaign_id": TEXT,
    "typology": TEXT,
    "entity_ids": TEXTS,
    "txids": TEXTS,
    "start_us": pl.Int64(),
    "end_us": pl.Int64(),
    "total_sats": SATS,
}

ORIGIN_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "true_origin_ip": TEXT,
    "true_origin_asn": pl.Int32(),
    "true_origin_as_org": TEXT,
    "true_origin_net_class": TEXT,
    "true_origin_country": TEXT,
    "true_origin_entity_id": TEXT,
    "broadcast_us": pl.Int64(),
    "used_tor": pl.Boolean(),
    "used_vpn": pl.Boolean(),
    "observed_by_n": COUNT,
}

CHAIN_TX_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "entity_id": TEXT,
    "input_entity_ids": TEXTS,
    "change_index": COUNT,
    "heuristic_violation": TEXT,
    "block_height": pl.Int64(),
}
```

#### `src/chakravyuh/pramaan/documents.py`

```python
MARGIN: float = 72.0

BODY_WIDTH: float = pdflib.A4[0] - 2 * MARGIN

LINE: float = 14.0

AS_ORG_FALLBACK = "the operator of the network named below"
```

#### `src/chakravyuh/pramaan/ed25519.py`

```python
P: Final[int] = 2**255 - 19

L: Final[int] = 2**252 + 27742317777372353535851937790883648493

D: Final[int] = -121665 * pow(121666, P - 2, P) % P

SQRT_M1: Final[int] = pow(2, (P - 1) // 4, P)

GY: Final[int] = (4 * pow(5, P - 2, P)) % P

GX: Final[int] = _recover_x(GY, 0)
```

#### `src/chakravyuh/pramaan/merkle.py`

```python
GENESIS: Final[str] = "0" * 64
```

#### `src/chakravyuh/pramaan/packet.py`

```python
ALERTS_DIR: Final[str] = "alerts"

SEALED_DIR: Final[str] = "sealed"

REPLAY_FIELD: Final[str] = "replay.expected_packet_sha256"

BLANK: Final[str] = ""
```

#### `src/chakravyuh/pramaan/pdflib.py`

```python
A4: Final[tuple[float, float]] = (595.28, 841.89)

FONTS: Final[dict[str, str]] = {
    "serif": "Times-Roman",
    "serif-bold": "Times-Bold",
    "sans": "Helvetica",
    "mono": "Courier",
}

_HELV: Final[dict[int, int]] = {
    32: 278,
    33: 278,
    34: 355,
    35: 556,
    36: 556,
    37: 889,
    38: 667,
    39: 191,
    40: 333,
    41: 333,
    42: 389,
    43: 584,
    44: 278,
    45: 333,
    46: 278,
    47: 278,
    48: 556,
    49: 556,
    50: 556,
    51: 556,
    52: 556,
    53: 556,
    54: 556,
    55: 556,
    56: 556,
    57: 556,
    58: 278,
    59: 278,
    60: 584,
    61: 584,
    62: 584,
    63: 556,
    64: 1015,
    65: 667,
    66: 667,
    67: 722,
    68: 722,
    69: 667,
    70: 611,
    71: 778,
    72: 722,
    73: 278,
    74: 500,
    75: 667,
    76: 556,
    77: 833,
    78: 722,
    79: 778,
    80: 667,
    81: 778,
    82: 722,
    83: 667,
    84: 611,
    85: 722,
    86: 667,
    87: 944,
    88: 667,
    89: 667,
    90: 611,
    91: 278,
    92: 278,
    93: 278,
    94: 469,
    95: 556,
    96: 333,
    97: 556,
    98: 556,
    99: 500,
    100: 556,
    101: 556,
    102: 278,
    103: 556,
    104: 556,
    105: 222,
    106: 222,
    107: 500,
    108: 222,
    109: 833,
    110: 556,
    111: 556,
    112: 556,
    113: 556,
    114: 333,
    115: 500,
    116: 278,
    117: 556,
    118: 500,
    119: 722,
    120: 500,
    121: 500,
    122: 500,
    123: 334,
    124: 260,
    125: 334,
    126: 584,
}

_TIMES: Final[dict[int, int]] = {
    32: 250,
    33: 333,
    34: 408,
    35: 500,
    36: 500,
    37: 833,
    38: 778,
    39: 180,
    40: 333,
    41: 333,
    42: 500,
    43: 564,
    44: 250,
    45: 333,
    46: 250,
    47: 278,
    48: 500,
    49: 500,
    50: 500,
    51: 500,
    52: 500,
    53: 500,
    54: 500,
    55: 500,
    56: 500,
    57: 500,
    58: 278,
    59: 278,
    60: 564,
    61: 564,
    62: 564,
    63: 444,
    64: 921,
    65: 722,
    66: 667,
    67: 667,
    68: 722,
    69: 611,
    70: 556,
    71: 722,
    72: 722,
    73: 333,
    74: 389,
    75: 722,
    76: 611,
    77: 889,
    78: 722,
    79: 722,
    80: 556,
    81: 722,
    82: 667,
    83: 556,
    84: 611,
    85: 722,
    86: 722,
    87: 944,
    88: 722,
    89: 722,
    90: 611,
    91: 333,
    92: 278,
    93: 333,
    94: 469,
    95: 500,
    96: 333,
    97: 444,
    98: 500,
    99: 444,
    100: 500,
    101: 444,
    102: 333,
    103: 500,
    104: 500,
    105: 278,
    106: 278,
    107: 500,
    108: 278,
    109: 778,
    110: 500,
    111: 500,
    112: 500,
    113: 500,
    114: 333,
    115: 389,
    116: 278,
    117: 500,
    118: 500,
    119: 722,
    120: 500,
    121: 500,
    122: 444,
    123: 480,
    124: 200,
    125: 480,
    126: 541,
}

_WIDTHS: Final[dict[str, dict[int, int]]] = {
    "serif": _TIMES,
    "serif-bold": _TIMES,
    "sans": _HELV,
    "sans-bold": _HELV,
    "mono": {c: 600 for c in range(32, 127)},
}
```

#### `src/chakravyuh/pramaan/stage.py`

```python
INPUT_ROOT: Final[str] = "data/generated"

PACKETS_DIR: Final[str] = "packets"

ALERTS_DIR: Final[str] = "alerts"

KEYS_DIR: Final[str] = "keys"

SEED_FILE: Final[str] = "ed25519.seed"

PUB_FILE: Final[str] = "ed25519.pub"

LOG_NAME: Final[str] = "merkle.log"

STAGES: Final[tuple[str, ...]] = (
    "sealed",
    "normalised",
    "graph",
    "signals",
    "scores",
    "alerts",
)
```

#### `src/chakravyuh/setu/enrich.py`

```python
VENDOR_ROOT: Final[str] = "vendor"

_COUNTRY_BLOCKS: Final[tuple[str, ...]] = (
    "GeoLite2-Country-Blocks-IPv4.csv",
    "GeoLite2-Country-Blocks-IPv6.csv",
)

_COUNTRY_LOCATIONS: Final[str] = "GeoLite2-Country-Locations-en.csv"

_ASN_BLOCKS: Final[tuple[str, ...]] = (
    "GeoLite2-ASN-Blocks-IPv4.csv",
    "GeoLite2-ASN-Blocks-IPv6.csv",
)

_TOR_LIST: Final[tuple[str, ...]] = ("exit-addresses.txt", "tor-exit-addresses.txt")

_MOBILE: Final[tuple[str, ...]] = ("mobile", "cellular", "wireless", "gsm", "lte")

_VPN: Final[tuple[str, ...]] = (
    "vpn",
    "proxy",
    "privacy",
    "anonym",
    "tunnel",
    "mullvad",
    "private internet",
)

_HOSTING: Final[tuple[str, ...]] = (
    "hosting",
    "cloud",
    "data center",
    "datacenter",
    "data centre",
    "server",
    "vps",
    "dedicated",
    "colocation",
    "amazon",
    "google",
    "microsoft",
    "digitalocean",
    "ovh",
    "hetzner",
    "linode",
    "vultr",
    "alibaba",
    "oracle",
)
```

#### `src/chakravyuh/setu/normalise.py`

```python
CHANGE_UNDETERMINED: Final[int] = -1

ROUND_SATS: Final[int] = 1000

_NET_CLASS_ORDER: Final[tuple[str, ...]] = (
    "residential",
    "hosting",
    "mobile",
    "tor_exit",
    "vpn_suspect",
    "unknown",
)

_SCRIPT_TYPE_FROM_ADDRESS: Final[pl.Expr] = (
    pl.when(pl.col("address").str.starts_with("bc1p"))
    .then(pl.lit("p2tr"))
    .when(pl.col("address").str.starts_with("bc1q") & (pl.col("address").str.len_chars() == 42))
    .then(pl.lit("p2wpkh"))
    .when(pl.col("address").str.starts_with("bc1q") & (pl.col("address").str.len_chars() == 62))
    .then(pl.lit("p2wsh"))
    .when(pl.col("address").str.starts_with("3"))
    .then(pl.lit("p2sh"))
    .when(pl.col("address").str.starts_with("1"))
    .then(pl.lit("p2pkh"))
    .otherwise(None)
)
```

#### `src/chakravyuh/setu/schema.py`

```python
STAGE: Final[str] = "setu"

ANNOUNCEMENTS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "row_id": pl.Int64(),
    "txid": pl.String(),
    "peer_ip": pl.String(),
    "peer_port": pl.Int32(),
    "observer_ip": pl.String(),
    "observer_port": pl.Int32(),
    "seen_us": pl.Int64(),
    "rank_in_tx": pl.Int32(),
    "delta_first_us": pl.Int64(),
    "geo_country": pl.String(),
    "asn": pl.Int32(),
    "as_org": pl.String(),
    "net_class": pl.String(),
    "peer_seen_count": pl.Int32(),
    "msg_type": pl.String(),
}

TRANSACTIONS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "txid": pl.String(),
    "first_seen_us": pl.Int64(),
    "last_seen_us": pl.Int64(),
    "n_announcements": pl.Int32(),
    "n_distinct_peers": pl.Int32(),
    "announce_spread_us": pl.Int64(),
    "input_addresses": pl.List(pl.String()),
    "output_addresses": pl.List(pl.String()),
    "input_amounts": pl.List(pl.Int64()),
    "output_amounts": pl.List(pl.Int64()),
    "n_in": pl.Int32(),
    "n_out": pl.Int32(),
    "total_in_sats": pl.Int64(),
    "total_out_sats": pl.Int64(),
    "fee_sats": pl.Int64(),
    "fee_rate_sat_vb": pl.Float64(),
    "is_coinbase": pl.Boolean(),
    "has_equal_outputs": pl.Boolean(),
    "change_index": pl.Int32(),
    "block_height": pl.Int32(),
}

ADDRESSES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "address": pl.String(),
    "script_type": pl.String(),
    "first_seen_us": pl.Int64(),
    "last_seen_us": pl.Int64(),
    "n_tx_in": pl.Int32(),
    "n_tx_out": pl.Int32(),
    "total_received_sats": pl.Int64(),
    "total_sent_sats": pl.Int64(),
    "balance_sats": pl.Int64(),
    "dwell_time_us": pl.Int64(),
}

PEERS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "peer_ip": pl.String(),
    "n_announcements": pl.Int32(),
    "n_txids": pl.Int32(),
    "mean_rank": pl.Float64(),
    "frac_rank_one": pl.Float64(),
    "distinct_ports": pl.Int32(),
    "geo_country": pl.String(),
    "asn": pl.Int32(),
    "as_org": pl.String(),
    "net_class": pl.String(),
    "first_us": pl.Int64(),
    "last_us": pl.Int64(),
}

ASN_ROLLUP_SCHEMA: Final[dict[str, pl.DataType]] = {
    "asn": pl.Int32(),
    "as_org": pl.String(),
    "geo_country": pl.String(),
    "n_peers": pl.Int32(),
    "n_announcements": pl.Int32(),
    "n_txids": pl.Int32(),
    "frac_rank_one": pl.Float64(),
    "n_residential": pl.Int32(),
    "n_hosting": pl.Int32(),
    "n_mobile": pl.Int32(),
    "n_tor_exit": pl.Int32(),
    "n_vpn_suspect": pl.Int32(),
    "n_unknown": pl.Int32(),
}

ARRIVAL_SCHEMA: Final[dict[str, pl.DataType]] = {
    "txid": pl.String(),
    "observer_id": pl.String(),
    "peer_ip": pl.String(),
    "seen_us": pl.Int64(),
}

OUTPUTS: Final[dict[str, dict[str, pl.DataType]]] = {
    "announcements.parquet": ANNOUNCEMENTS_SCHEMA,
    "transactions.parquet": TRANSACTIONS_SCHEMA,
    "addresses.parquet": ADDRESSES_SCHEMA,
    "peers.parquet": PEERS_SCHEMA,
    "asn_rollup.parquet": ASN_ROLLUP_SCHEMA,
    "arrival.parquet": ARRIVAL_SCHEMA,
}

NET_CLASSES: Final[frozenset[str]] = frozenset(
    {"residential", "hosting", "mobile", "tor_exit", "vpn_suspect", "unknown"}
)

REQUIRED_SEALED_COLUMNS: Final[tuple[str, ...]] = (
    "row_id",
    "ts_us",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
    "input_addresses",
    "output_addresses",
    "input_amounts",
    "output_amounts",
)

OPTIONAL_SEALED_COLUMNS: Final[tuple[str, ...]] = (
    "geo_country",
    "asn",
    "msg_type",
    "vsize",
    "block_height",
    "script_types",
)
```

#### `src/chakravyuh/setu/stage.py`

```python
INPUT_ROOT: Final[str] = "data"

OUTPUT_ROOT: Final[str] = "data/generated"

ROWS_FILE: Final[str] = "rows.parquet"

OUT_DIR: Final[str] = "normalised"
```

#### `src/chakravyuh/shastra/estimate.py`

```python
BASELINE_P1 = 0.5

BASELINE_DECAY = 0.5

MLE_ESCAPE_LOG_GAP = 1.0

MLE_MIN_MEAN_US = 1.0

MLE_EPS = 1e-12

MIN_TRAIN_ROWS = 200

MIN_CALIBRATION_ROWS = 50

BOOST_ROUNDS = 300

TREE_PARAMS: dict[str, Any] = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 40,
    "lambda_l2": 1.0,
    "feature_fraction": 1.0,
    "bagging_fraction": 1.0,
    # Determinism, not speed. `make verify-s06` runs the stage in two separate interpreters and
    # compares the bytes, so a model whose split choices depend on thread scheduling would fail
    # that gate rather than quietly produce two different answers in the field.
    "num_threads": 1,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
    "seed": 0,
}

CALIBRATION_SHARE = 0.25
```

#### `src/chakravyuh/shastra/features.py`

```python
ANNOUNCEMENT_COLUMNS = (
    "row_id",
    "txid",
    "peer_ip",
    "observer_ip",
    "seen_us",
    "rank_in_tx",
    "delta_first_us",
    "net_class",
)

PEER_COLUMNS = ("peer_ip", "n_txids", "frac_rank_one")

TRANSACTION_COLUMNS = ("txid", "input_addresses")
```

#### `src/chakravyuh/shastra/schema.py`

```python
STAGE: Final[str] = "shastra"

OUT_DIR: Final[str] = "signals"

FEATURES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "delta_first_us": pl.Int64(),
    "rank_in_tx": pl.Int32(),
    "n_announcements": pl.Int32(),
    "n_observers_seen": pl.Int32(),
    "peer_frac_rank_one": pl.Float64(),
    "peer_n_txids": pl.Int32(),
    "net_class": pl.String(),
    "announce_spread_us": pl.Int64(),
    "n_observers_blind": pl.Int32(),
    "peer_degree": pl.Int32(),
    "payer_shared": pl.Int32(),
    "n_candidates": pl.Int32(),
    "is_tor_exit": pl.Boolean(),
    "is_hosting": pl.Boolean(),
    # The multi-observer source log-likelihood `timing_mle` ranks on and `ensemble` blends.
    # Persisted in the struct so a reader can see the timing evidence behind a call and a replay
    # can reproduce it; up to a per-transaction constant, so comparable within a transaction, not
    # across.
    "mle_logscore": pl.Float64(),
}

ORIGIN_ESTIMATES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "txid": pl.String(),
    "peer_ip": pl.String(),
    "p_origin": pl.Float64(),
    "rank": pl.Int32(),
    "margin": pl.Float64(),
    "features": pl.Struct(FEATURES_SCHEMA),
    "estimator": pl.String(),
    "abstain": pl.Boolean(),
    "abstain_reason": pl.String(),
}

ORIGIN_L1_SCHEMA: Final[dict[str, pl.DataType]] = {
    "txid": pl.String(),
    "origin_asn": pl.Int32(),
    "as_org": pl.String(),
    "net_class": pl.String(),
    "p_asn": pl.Float64(),
    "origin_country": pl.String(),
    "p_country": pl.Float64(),
    "margin": pl.Float64(),
    "shortlist_size": pl.Int32(),
    "abstain": pl.Boolean(),
    "abstain_reason": pl.String(),
    "estimator": pl.String(),
}

TYPOLOGY_HITS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "hit_id": pl.String(),
    "typology": pl.String(),
    "subject_id": pl.String(),
    "txids": pl.List(pl.String()),
    "strength": pl.Float64(),
    "params": pl.Struct({"threshold": pl.Float64(), "window_us": pl.Int64()}),
}

ENTITY_TYPES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "predicted_type": pl.String(),
    "confidence": pl.Float64(),
    "basis": pl.List(pl.String()),
    "exempt_from_scoring": pl.Boolean(),
}

ESTIMATORS: Final[tuple[str, ...]] = (
    "first_spy",
    "timing_mle",
    "asn_rollup",
    "ensemble",
)

ABSTAIN_REASONS: Final[tuple[str, ...]] = (
    "tor_present",
    "single_observer",
    "margin_below_floor",
    "too_few_announcements",
)

L1_ABSTAIN_REASONS: Final[tuple[str, ...]] = (*ABSTAIN_REASONS, "cross_asn_ambiguous")

MODEL_FEATURES: Final[tuple[str, ...]] = (
    "delta_first_us",
    "rank_in_tx",
    "n_announcements",
    "n_observers_seen",
    "n_observers_blind",
    "peer_frac_rank_one",
    "peer_n_txids",
    "peer_degree",
    "announce_spread_us",
    "payer_shared",
    "n_candidates",
    "net_class_code",
    "is_tor_exit",
    "is_hosting",
    "mle_logscore",
)

NET_CLASS_CODES: Final[dict[str, int]] = {
    "hosting": 1,
    "residential": 2,
    "tor_exit": 3,
    "unknown": 4,
    "vpn_suspect": 5,
}

TOR_CLASS: Final[str] = "tor_exit"

HOSTING_CLASSES: Final[frozenset[str]] = frozenset({"hosting", "vpn_suspect"})
```

#### `src/chakravyuh/shastra/stage.py`

```python
INPUT_ROOT: Final[str] = "data"

OUTPUT_ROOT: Final[str] = "data/generated"

OUT_DIR: Final[str] = schema.OUT_DIR

REQUIRED_TABLES: Final[tuple[str, ...]] = (
    "announcements.parquet",
    "transactions.parquet",
    "peers.parquet",
)

GRAPH_DIR: Final[str] = "graph"

GRAPH_TABLE: Final[str] = "edges.parquet"

CONFIG_NAME: Final[str] = "config.effective.json"

DEFAULT_TRAIN_FRACTION: Final[float] = 0.7

DEFAULT_MARGIN_FLOOR: Final[float] = 0.04

DEFAULT_MIN_ANNOUNCEMENTS: Final[int] = 2

DEFAULT_RELAY_DELAY_US: Final[float] = 2_000_000.0

L1_PEER_COLUMNS: Final[tuple[str, ...]] = ("peer_ip", "asn", "as_org", "net_class", "geo_country")
```

#### `src/chakravyuh/shastra/typology.py`

```python
FAN_OUT_MIN_OUTPUTS: Final[int] = 6

COINJOIN_MIN_OUTPUTS: Final[int] = 3

PEEL_MAX_SHARE: Final[float] = 0.35

PEEL_MIN_TXNS: Final[int] = 2

STRUCT_MIN_TXNS: Final[int] = 3

STRUCT_MAX_CV: Final[float] = 0.15

TRANSACTION_COLUMNS: Final[tuple[str, ...]] = (
    "txid",
    "input_addresses",
    "output_amounts",
    "total_out_sats",
    "n_out",
    "is_coinbase",
    "has_equal_outputs",
)
```

#### `src/chakravyuh/vaani/counters.py`

```python
COUNTER_SCHEMA: Final[dict[str, pl.DataType]] = {
    "alert_id": pl.String(),
    "kind": pl.String(),
    "statement": pl.String(),
    "strength": pl.Float64(),
    "would_clear": pl.Boolean(),
}

CLUSTER_CONFIDENCE_FLOOR: Final[float] = 0.5

LOW_MARGIN_FACTOR: Final[float] = 2.0

BENIGN_EXPLANATIONS: Final[dict[str, str]] = {
    "peel_chain": "long chains also arise from consolidation and exchange batching",
    "structuring": "many small payments are ordinary retail or payroll behaviour",
    "fan_out": "a wide fan also matches marketplace payouts and wage batches",
    "pass_through": "processors and custodians pass value through as their job",
    "coinjoin_like": "equal-value outputs also come from privacy wallets used for anonymity alone",
    "rapid_hop": "automated services relay funds quickly without any attempt to hide",
}
```

#### `src/chakravyuh/vaani/evidence.py`

```python
EVIDENCE_SCHEMA: Final[dict[str, pl.DataType]] = {
    "alert_id": pl.String(),
    "kind": pl.String(),
    "statement": pl.String(),
    "weight": pl.Float64(),
    "source_ref": pl.String(),
}

ALERTS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "alert_id": pl.String(),
    "subject_id": pl.String(),
    "rank": pl.Int32(),
    "severity": pl.String(),
    "conf_low": pl.Float64(),
    "conf_high": pl.Float64(),
    "headline": pl.String(),
    "origin_txid": pl.String(),
    "origin_peer_ip": pl.String(),
    "origin_p": pl.Float64(),
    "attribution_ready": pl.Boolean(),
}

SEVERITY_HIGH: Final[float] = 0.65

SEVERITY_MEDIUM: Final[float] = 0.40
```

#### `src/chakravyuh/vaani/gloss.py`

```python
FEATURES_PATH: Final[str] = "docs/FEATURES.md"

_ROW: Final[re.Pattern[str]] = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(.+?)\s*\|\s*$")

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
```

#### `src/chakravyuh/vaani/redact.py`

```python
ELLIPSIS: Final[str] = "…"
```

#### `src/chakravyuh/vaani/stage.py`

```python
INPUT_ROOT: Final[str] = "data/generated"

OUT_DIR: Final[str] = "alerts"

SCORES_DIR: Final[str] = "scores"

SIGNALS_DIR: Final[str] = "signals"

GRAPH_DIR: Final[str] = "graph"

NORMALISED_DIR: Final[str] = "normalised"

WALLET_SCORES: Final[str] = "wallet_scores.parquet"

ORIGIN_ESTIMATES: Final[str] = "origin_estimates.parquet"

ENTITY_TYPES: Final[str] = "entity_types.parquet"

TYPOLOGY_HITS: Final[str] = "typology_hits.parquet"

CLUSTERS: Final[str] = "clusters.parquet"

EDGES: Final[str] = "edges.parquet"

ANNOUNCEMENTS: Final[str] = "announcements.parquet"

ENSEMBLE: Final[str] = "ensemble"

DEFAULT_MARGIN_FLOOR: Final[float] = 0.04
```

### Appendix D — module responsibilities and interfaces

Function signatures are exact source syntax; summaries below are source docstrings. They describe an interface, not a claim that every optional adapter is enabled. Private helpers are included because parsing, guards and calibration behavior matter to replay.

#### `src/chakravyuh/api/app.py`

The loopback read-only API. Binds 127.0.0.1, serves the eight adapter payloads.

There is deliberately no authentication: this is a single-user tool on an investigator's own
laptop. That choice is only safe because the bind address is a module constant, `BIND_HOST`,
and the test suite fails if it is anything but 127.0.0.1 — binding to the wildcard address
would put an unauthenticated endpoint on whatever network the laptop joined, which at a demo
venue is everyone else's.

No route mutates anything, no route accepts a filesystem path: the only parameter a route
takes that is not an int or a severity string is a case id or txid, resolved strictly inside
the run directory set at startup from `CHAKRAVYUH_RUN`. That value names a run id, never a
path, and resolves under `data/generated/` or the app refuses to start.

- `def resolve_run() -> Path:` — The run directory this process serves, resolved once at startup.
- `def run_dir() -> Path:` — Internal helper; behavior is defined by the source implementation.
- `def set_run_dir(path: Path) -> None:` — Tests inject the run directory directly; production resolves it from the environment.
- `@app.exception_handler(KeyError)` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/health')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/manifest')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/collapse')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/transactions')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/origin/{txid}')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/graph')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/alerts')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/alerts/{alert_id}')` — Internal helper; behavior is defined by the source implementation.
- `@app.get('/packets/{alert_id}')` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/api/serialize.py`

Turn the run's Parquet artifacts into the eight DRISHTI adapter payloads.

One serializer per adapter function, each a pure function of (run_dir, arguments) -> dict.
`app.py` serves them over HTTP, `scripts/export_ui_fixtures.py` writes the same dicts to
`data/fixtures/ui/`. Both call this module, which is what makes the API's response shape and
the committed fixtures agree field for field rather than by convention.

Every payload is derived at request time from the run's own artifacts. `origin_txid`,
`origin_peer_ip` and `subject_id` are contract join keys and stay whole; everything rendered
as prose is already truncated at write time by VAANI, and the few places this module emits an
identifier into a display field it truncates through `vaani.redact` here. Hashes are the
exception and print in full.

The run directory is resolved once by `app.py` from the environment. Nothing here accepts a
filesystem path from a caller outside the package, and nothing here names a quarantined tree.

- `def _meta(run_dir: Path, stage: str) -> dict[str, Any]:` — Internal helper; behavior is defined by the source implementation.
- `def _redacted_ip(value: str | None) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _redacted_address(subject_id: str) -> str:` — `addr:bc1q…` -> first six and last four of the address part.
- `def _stage_lamps(run_dir: Path) -> list[dict[str, Any]]:` — L0..L6, each lit iff the file that proves the stage ran exists in the run.
- `def _merkle_head(run_dir: Path) -> str:` — The current Merkle root over every leaf in the run's log, in full.
- `def _n_transactions(run_dir: Path) -> int:` — Gossiped transaction count, read without materialising the table.
- `def _model_report(run_dir: Path) -> dict[str, Any]:` — The eval report for this run, or `{}` before it was measured.
- `def _base_rate(report: dict[str, Any]) -> float:` — Positive prevalence from the report's `1:N` imbalance ratio, 0.0 if unknown.
- `def _l1_row(run_dir: Path, txid: str) -> dict[str, Any]:` — The ensemble L1 row for one origin transaction, or `{}` when absent.
- `def _attribution(l1: dict[str, Any]) -> dict[str, Any]:` — The L1-leading attribution block the origin and packet screens both render.
- `def manifest(run_dir: Path) -> dict[str, Any]:` — INTAKE payload: custody files, the seal arithmetic, the schema table, the rejects.
- `def collapse(run_dir: Path) -> dict[str, Any]:` — COLLAPSE payload: the one-million-rows-is-not-one-million-events screen.
- `def transactions(run_dir: Path, limit: int, offset: int) -> dict[str, Any]:` — A paged, txid-ordered transaction list. `offset`/`limit` are ints, never paths.
- `def origin_estimate(run_dir: Path, txid: str) -> dict[str, Any]:` — The timeline fan's payload: one lane per announcing peer, ordered by first seen.
- `def _origin_features(struct: dict[str, Any] | None) -> list[dict[str, str]]:` — The rank-1 candidate's features as label/value/gloss rows, in reading order.
- `def _node_kind(node_id: str) -> str:` — The kind of a node id, from its prefix. The graph's ids are the contract's.
- `def _touched(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:` — One row per (address, transaction) pair the money edges put together, with the two marks.
- `def _activity(frame: pl.DataFrame, key: str) -> pl.DataFrame:` — `frame` counted by `key`: transactions, and how many of them carry each mark.
- `def _actor_scores(run_dir: Path, nodes: pl.DataFrame, edges: pl.DataFrame) -> dict[str, dict[str, Any]]:` — Per-actor scores, keyed by node id, for both actor kinds.
- `def _actor_graph(run_dir: Path, nodes: pl.DataFrame, edges: pl.DataFrame, focus: str | None, cap: int) -> dict[str, Any]:` — The ownership floor: addresses, the clusters they sit in, and the edges between them.
- `def _actor_node_scores(node_id: str, scores: dict[str, dict[str, Any]]) -> dict[str, Any]:` — One actor's scores, with a null wherever the graph has nothing to say.
- `def graph(run_dir: Path, detail: str, focus: str | None, cap: int) -> dict[str, Any]:` — The fused graph, cluster-aggregated by default.
- `def alerts(run_dir: Path, limit: int, offset: int, severity: str | None) -> dict[str, Any]:` — The QUEUE table. Rank order is the pipeline's rank; nothing reorders here.
- `def alert(run_dir: Path, alert_id: str) -> dict[str, Any]:` — The inspector: SHAP features, evidence, mandatory counter-evidence, confidence.
- `def packet(run_dir: Path, alert_id: str) -> dict[str, Any]:` — The filed packet as JSON. Identifiers whole in machine fields, PDFs truncated.
- `def _notice(payload: dict[str, Any]) -> dict[str, Any]:` — The production notice as structured fields, mirroring `notice.pdf`.
- `def _origin_report(run_dir: Path) -> dict[str, Any]:` — This run's origin accuracy report, or `{}` before it was measured.
- `def _pair_precision(run_dir: Path) -> float | None:` — The measured same-owner pair precision over the addresses the stage observed.
- `def _run_eval_report(run_dir: Path) -> dict[str, Any]:` — The stage's own rolled-up eval report, or `{}` before BUDDHI wrote one.
- `def _recoverable_ceiling(run_dir: Path) -> float | None:` — The fraction of transactions the observed world even contains the answer for.
- `def _n_scored(run_dir: Path) -> int:` — Owner groups BUDDHI scored, read without materialising the table.
- `def _elliptic_metric(run_dir: Path, key: str) -> float | None:` — One score from the external-replication block, or None when that leg did not run.
- `def _elliptic_f1(run_dir: Path) -> float | None:` — The external-replication F1 — the headline of the Elliptic leg.
- `def _ceiling_by_granularity(run_dir: Path) -> dict[str, float | None]:` — The honesty ceiling at each granularity, keyed as the origin report keys them.
- `def _campaign_recall(run_dir: Path) -> float | None:` — Held-out campaign recall, the headline of the wallet model, or None when unmeasured.
- `def _curve_point(report: dict[str, Any], grain: str, kind: str) -> dict[str, Any] | None:` — One observer-fraction point for a granularity, from a single origin report.
- `def _origin_curve(run_dir: Path) -> dict[str, list[dict[str, Any]]]:` — The observer-fraction curve per granularity, one point per measured run.
- `def _funnel(run_dir: Path, report: dict[str, Any]) -> list[dict[str, Any]]:` — The run's real stage counts, each read from the artifact that proves the stage ran.
- `def _shipped_model(run_dir: Path) -> str:` — The model tag that actually scored this run's rows, or "" when nothing recorded one.
- `def _model_intelligence(run_dir: Path) -> dict[str, Any]:` — The model-comparison panel's numbers, each one labelled by where it came from.
- `def world(run_dir: Path) -> dict[str, Any]:` — WORLD/ceiling payload: the run's pipeline, origin curve and headline numbers.

#### `src/chakravyuh/buddhi/__main__.py`

`python -m chakravyuh.buddhi --in data/generated/<run> --out data/generated/<run>`.

Labels and scoring live here and nowhere else in the stage. `chakravyuh.eval` is imported by this
file alone, so `stage.py` stays a pure read of directories under `data/` and the one place the
pipeline touches the eval package is a file that is not itself part of the pipeline.

The run id used to find the answer key is derived from `--in`, and `--out` must name the same
run: `scores/` sits inside the run it scores, and a measurement filed under one run id while
scored against another's truth is a number nobody can trace. That is also what makes the
determinism gate meaningful — `make verify-s07` runs this twice with one input and two output
directories, and a stage that invented its own run id would give the second run a different
answer.

Two eval-side calls happen here, in this order. The trivial baseline (rank by total value
received) is measured first and written through the eval side, so the model's
`baseline_beaten` in `eval_report.json` compares against a number measured on the same run
rather than one the stage asserted.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def _labels(run_id: str, train_fraction: float) -> tuple[pl.DataFrame | None, int | None]:` — Open the wallet door. Returns train-window `(address, y)` and the boundary, or (None, None).
- `def _measure_baseline(run_id: str) -> None:` — Measure the trivial baseline through the eval side, so the bar exists before the model.
- `def _boundary_of(run_id: str) -> int:` — The run's split boundary, derived the same way the label door derives it.
- `def _score(run_id: str, predictions: pl.DataFrame, boundary_us: int, coverage_target: float) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:` — Hand the predictions to eval and report what comes back. Figures, never a label.
- `def _read_json(path: Path) -> dict[str, Any]:` — Internal helper; behavior is defined by the source implementation.
- `def _embedding_leg(scores_path: Path, model_report: dict[str, Any], baseline_report: dict[str, Any] | None, *, requested: bool) -> dict[str, Any]:` — Whether the GNN leg's rows are entitled to ship, with the holdout measurement that says so.
- `def _eval_report(run_id: str, model_report: dict[str, Any], boundary_us: int, seed: int, *, embedding_leg: dict[str, Any]) -> dict[str, Any] | None:` — Assemble contract section 7's `eval_report.json` from reports the eval side filed.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/buddhi/causal_inference.py`

Opt-in offline causal AML scoring with explicit windows and portable frozen artifacts.

This experimental entry point does not replace the standard stage. XGBoost is an optional
runtime dependency loaded only when this engine is invoked. Scores rank observed leads;
their calibration on synthetic history does not establish future-world probabilities.

- `def transform(table: pl.DataFrame, means: NDArray[np.float64], scales: NDArray[np.float64]) -> NDArray[np.float32]:` — Frozen signed-log and fit-only scaling, in the versioned feature order.
- `def score(normalised: Path, model_dir: Path, *, start_us: int, end_us: int) -> tuple[pl.DataFrame, snapshot.Snapshot, dict[str, object]]:` — Infer only from observation artifacts; model metadata fixes the ownership recipe.
- `def main() -> None:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/buddhi/embed.py`

Label-free structural embeddings of the JAAL dual graph, as extra BUDDHI columns.

REMODEL-PLAN section 7 asks for "self-supervised graph embeddings (Deep-Graph-Infomax /
GraphSAGE-style) over the JAAL dual graph, fed as extra columns into the GBM". This module is
that signal, built the one way the air-gap allows.

**Why not a trained GNN.** The box is offline: `torch` cannot be installed and `uv.lock` cannot
be regenerated here (P0-a hit the same wall). A dependency-free linearisation of the same family
is therefore what ships — K-hop mean aggregation over the confidence-weighted adjacency,
`H = A_hat^K X` (Wu et al. 2019, *Simplifying Graph Convolutional Networks*: a linear GCN is
exactly this), reduced by an exact SVD to at most `DIM` columns. It reads no labels and learns no
weights, so it is named for what it is — **label-free structural embedding**, not
self-supervised — and the deviation from the plan's wording is recorded rather than hidden
behind the acronym. Upgrade path: if the box ever gets `torch`, a trained encoder swaps in behind
`subject_embeddings` and nothing else changes.

**The window rule, which is the same one `features.cluster_shape` applies.** An edge belongs to a
subject's window when no endpoint carries a timestamp outside it. A node's timestamp is when it
first appeared — an address's `first_seen_us`, a transaction's. An edge whose endpoints have no
timestamp at all (`HOSTED_IN`, peer-to-ASN) is infrastructure metadata, the same kind of static
lookup `GeoLite2` is, so it is in both windows: it is not a fact about the capture's timeline and
cannot leak one.

**What this module must not do.** It never reads a label, never reads outside `edges`,
`transactions` and `addresses`, and returns null — never zero — for a subject with no node in its
window's graph. That null is load-bearing: `stage.py` reads it to decide which booster scored the
row, which is what the per-row `model` flag reports.

- `def _node_times(transactions: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:` — When each timestamped node first appeared. Only addresses and transactions carry a time.
- `def _window(tagged: pl.DataFrame, half: Half, boundary_us: int) -> pl.DataFrame:` — The edges visible to one window's subjects.
- `def _design(window: pl.DataFrame, node_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:` — `(X, (src, dst, weight))` for this window, over `node_ids` in the order given.
- `def _propagate(x: np.ndarray, coo: np.ndarray, hops: int) -> np.ndarray:` — `A_hat^hops @ X`, with self-loops and row-normalised (SGC's mean aggregation).
- `def _standardise(x: np.ndarray) -> np.ndarray:` — Per-column zero-mean unit-variance, so one window's embedding is comparable to another's.
- `def _reduce(hidden: np.ndarray, dim: int) -> np.ndarray:` — Exact SVD reduction to at most `dim` columns, with the singular vectors' sign pinned.
- `def subject_embeddings(edges: pl.DataFrame, transactions: pl.DataFrame, addresses: pl.DataFrame, members: pl.DataFrame, *, half: Half, boundary_us: int, dim: int=DIM, hops: int=HOPS) -> pl.DataFrame:` — One embedding row per subject in `members` that has a node in this window's graph.

#### `src/chakravyuh/buddhi/features.py`

One row per wallet subject, with every feature the risk model is allowed to see.

The subject grain, not the address grain. An entity's addresses share an owner and therefore a
risk, and the label door (`chakravyuh.eval.labels.wallet_labels`) is answered per address but
meaningful per owner. A subject is one predicted cluster from `graph/clusters.parquet`, or one
address that no `SAME_OWNER` edge linked to anything: those are still wallets an investigator can
be asked about, and leaving them unscored would silently drop most of the capture.

**The window rule, which is the whole point of this file.** A subject is train if its earliest
activity in the capture is before the split boundary, holdout otherwise. A train subject's
features are computed over pre-boundary transactions only; a holdout subject's, over
post-boundary transactions only. Transaction activity is sliced by that boundary, because
`normalised/addresses.parquet` already carries whole-capture aggregates and a subject that trains
on its own future is the leak the brief names. Cluster shape is windowed with the same rule: a
cluster's late-arriving members are future information about its early self, so only members
active inside the window count, and `min_edge_confidence` is the weakest link among edges whose
both ends were active in the window. This does not make full-capture cluster membership causal:
a later ownership edge can still determine the supplied subject partition. Global upstream
origin scores and typology detections can also include later information. The opt-in snapshot
API supplies a point-in-time partition and excludes those upstream artifacts.

Every column here is observable. Nothing is read from a sibling tree and nothing is derived from
a label, which is what lets `stage.py` stay a pure read of directories under `data/`.

- `def subjects(clusters: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:` — One row per (subject_id, address), plus `is_clustered`.
- `def _sides(transactions: pl.DataFrame) -> pl.DataFrame:` — One row per (txid, address, side) with value and time, from the chain columns.
- `def _aggregate(sides: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:` — The activity block per subject, over the side rows this window actually holds.
- `def _dwell(sides: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:` — Median gap between a receipt and that address's next send, per subject.
- `def cluster_shape(clusters: pl.DataFrame, edges: pl.DataFrame, members: pl.DataFrame, active: pl.DataFrame) -> pl.DataFrame:` — Windowed cluster shape: active size, weakest live link, distinct heuristics.
- `def script_types(addresses: pl.DataFrame, active: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:` — Distinct address formats among a subject's active members.
- `def origin_fusion(origin_estimates: pl.DataFrame, sent: pl.DataFrame) -> pl.DataFrame:` — The origin estimator's output, as five per-subject features over its own sent txids.
- `def asn_fusion(origin_l1: pl.DataFrame, sent: pl.DataFrame) -> pl.DataFrame:` — The operator estimate, as three per-subject features over the same windowed sends.
- `def typology_load(hits: pl.DataFrame, sent_pairs: pl.DataFrame) -> pl.DataFrame:` — Per subject: distinct typologies and hit-bearing transactions, counted inside its window.
- `def morphology(transactions: pl.DataFrame, sent_pairs: pl.DataFrame) -> pl.DataFrame:` — Six transaction-shape features over the subject's in-window sends, joined on subject_id.
- `def build(transactions: pl.DataFrame, clusters: pl.DataFrame, addresses: pl.DataFrame, edges: pl.DataFrame, origin_estimates: pl.DataFrame, boundary_us: int, typology_hits: pl.DataFrame | None=None, origin_l1: pl.DataFrame | None=None, *, use_embeddings: bool=False) -> pl.DataFrame:` — The subject table: windowed activity given the caller's partition and upstream evidence.

#### `src/chakravyuh/buddhi/model.py`

The LightGBM risk model and the class-conditional conformal wrapper around it.

Two version facts shaped this file, both found the hard way in S06 and here:

LightGBM's sklearn wrapper is unusable — its `fit` calls a keyword sklearn 1.9 removed — so the
booster is trained through the native API exactly as SHASTRA does it, then handed to the conformal
layer behind a thin adapter that speaks the sklearn protocol (`classes_`, `predict_proba`).

MAPIE 0.9.1 predates sklearn's estimator-tags protocol: its internal `EnsembleClassifier` has no
`__sklearn_tags__`, and sklearn 1.9's `check_is_fitted` demands one, so any prefit `MapieClassifier`
raises `AttributeError` before doing any work. `_patch_mapie_tags` adds the missing method at
runtime, guarded so it is a no-op the day MAPIE ships its own tags. It is the same shape of
compromise as Kùzu's absence path: narrow, loud in the source, and removable.

Determinism is not a preference here. `make verify-s07` runs this stage in two separate
interpreters and compares bytes, so every random and threading knob is pinned, and the Mondrian
predict loop runs per class in a fixed order.

- Class `Calibrated` — What training produced. `reason` says what did not happen, for `_meta.json`.
  Fields: `trained: bool`; `mondrian: bool`; `n_train: int`; `n_calibration: int`; `n_positive: int`; `reason: str | None`.
- `def _patch_mapie_tags() -> None:` — Give MAPIE's internal estimator the sklearn-1.9 tags protocol, once, if it still lacks it.
- Class `_BoosterClassifier` — The native-API booster behind the sklearn protocol MAPIE's prefit path checks for.
- `def fit(subject_frame: pl.DataFrame, seed: int, coverage_target: float, features: tuple[str, ...]=MODEL_FEATURES) -> tuple[dict[str, Any], Calibrated]:` — Train the risk model and wrap it in class-conditional conformal prediction.
- `def predict_sets(bundle: dict[str, Any], frame: pl.DataFrame) -> pl.DataFrame:` — Which classes each subject's conformal set contains, per method, class-conditional first.
- `def _plain_sets(bundle: dict[str, Any], X: np.ndarray, alpha: float) -> np.ndarray:` — The unpartitioned LAC sets. Returns all-true when no calibrator was fitted.
- `def risk_scores(bundle: dict[str, Any], frame: pl.DataFrame) -> np.ndarray:` — The booster's P(illicit), one per subject. The raw model output, before any set logic.
- `def top_shap(bundle: dict[str, Any], frame: pl.DataFrame) -> list[list[dict[str, Any]]]:` — Top-`TOP_FEATURES` SHAP pairs per subject, ordered by absolute value.

#### `src/chakravyuh/buddhi/recipe.py`

The dataset-agnostic risk recipe: one train + calibrate + score procedure, called by both
the BUDDHI stage (our morphological features) and eval/external (Elliptic's features). The sole
thing that varies between datasets is the (X, y, time_index) triple handed in; every LightGBM
param, the time-ordered split, and the conformal wrap are identical here.

`model.fit` shares this file's conformal core (`_mondrian_ok`, `_fit_calibrators`) so the two
callers cannot drift: the class-conditional wrapper is defined once. `model.fit` keeps its own
booster training and bundle assembly because it holds no test set — its input is already the
train window and it must return the fitted objects for `predict_sets` to score the world — and
so its byte-for-byte determinism gate is untouched by this extraction.

- Class `RecipeResult` — Source-defined class.
  Fields: `scores: np.ndarray`; `y_test: np.ndarray`; `in_set_1: np.ndarray`; `boundary: float`; `n_train: int`; `n_test: int`; `n_positive_train: int`; `calibrated: model.Calibrated`.
- `def _mondrian_ok(y_cal: np.ndarray) -> bool:` — Both classes present in the calibration tail with >= MIN_CALIBRATION_PER_CLASS members.
- `def _fit_calibrators(booster: lgb.Booster, X_cal: np.ndarray, y_cal: np.ndarray, *, mondrian_ok: bool) -> tuple[Any, Any]:` — Fit the prefit MAPIE plain (LAC) and, when `mondrian_ok`, class-conditional (MondrianCP) calibrators around an already-trained booster.
- `def _conformal_illicit_flag(booster: lgb.Booster, X_cal: np.ndarray, y_cal: np.ndarray, X_te: np.ndarray, *, coverage_target: float, mondrian_ok: bool) -> tuple[np.ndarray | None, bool]:` — The class-1 conformal membership for the test rows, mirroring `predict_sets`.
- `def train_and_score(X: np.ndarray, y: np.ndarray, time_index: np.ndarray, *, train_fraction: float, seed: int, coverage_target: float) -> RecipeResult:` — Train a booster, wrap it in class-conditional conformal, and score the holdout — the whole procedure on one `(X, y, time_index)` triple, split by time exactly as the BUDDHI stage is.

#### `src/chakravyuh/buddhi/relational_inference.py`

Offline graph-context tree inference; portable artifacts, no Torch or research imports.

- `def _scale(values: NDArray[Any], parameters: dict[str, Any]) -> NDArray[np.float32]:` — Internal helper; behavior is defined by the source implementation.
- `def _indices(frame: pl.DataFrame, source: str, target: str) -> NDArray[np.int64]:` — Internal helper; behavior is defined by the source implementation.
- `def _pool(values: NDArray[np.float32], edges: NDArray[np.int64], size: int) -> NDArray[np.float32]:` — Internal helper; behavior is defined by the source implementation.
- `def _summaries(context: NDArray[np.float32], edges: NDArray[np.int64], size: int) -> NDArray[np.float32]:` — Internal helper; behavior is defined by the source implementation.
- `def build(tx: pl.DataFrame, addresses: pl.DataFrame, announcements: pl.DataFrame, peers: pl.DataFrame, scalers: dict[str, Any], *, start_us: int, end_us: int, partition_mode: Literal['heuristic', 'address']) -> tuple[NDArray[np.float32], snapshot.Snapshot]:` — 329 causal features over explicit decision windows, never neighbor labels.
- `def score(normalised: Path, model_dir: Path, *, start_us: int, end_us: int) -> tuple[pl.DataFrame, snapshot.Snapshot, dict[str, Any]]:` — Native CPU tree predictions and exact raw-margin TreeSHAP explanations.

#### `src/chakravyuh/buddhi/snapshot.py`

Opt-in end-of-window AML features over ownership evidence available at decision time.

This API scores recurring as well as newly observed subjects. Unlike the legacy subject split,
each window gets its own graph partition. Global origin estimates and typology artifacts are
excluded until their own point-in-time recipes are available. No labels are consumed here.

- Class `Snapshot` — Source-defined class.
  Fields: `table: pl.DataFrame`; `members: pl.DataFrame`; `edges: pl.DataFrame`; `start_us: int`; `end_us: int`; `partition_mode: Literal['heuristic', 'address'] = 'heuristic'`.
- `def _flow_features(transactions: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:` — Exact gross input/output values per subject/transaction; counterparties are subjects.
- `def build(transactions: pl.DataFrame, addresses: pl.DataFrame, ledger: pl.DataFrame, *, start_us: int, end_us: int, threshold: float=0.3, partition_mode: Literal['heuristic', 'address']='heuristic') -> Snapshot:` — Compute retrospective features available at the end of [start_us, end_us].

#### `src/chakravyuh/buddhi/stage.py`

BUDDHI as a stage: read `signals/` and `graph/`, write `scores/`, account for every row.

The path guards are SHASTRA's, restated rather than imported, for the reason that rule exists:
`--in` is allowlisted to `data/`, so a BUDDHI invocation cannot be pointed at the answer key even
by an operator who wants to, because the answer key is a sibling tree and not under `data/`.

This module never imports `chakravyuh.eval` and never receives an evaluation-window label.
`__main__.py` hands it train-window `y` values as an ordinary column and takes the holdout
predictions back out; where those `y` came from is none of this file's business, which is what
keeps the stage a pure read of directories under `data/` and lets the two determinism runs agree
byte for byte whether or not scoring ran.

- Class `InputPathError` — A path BUDDHI will not read from, or will not write to.
- Class `Settings` — The eval knobs this run was generated with, read back from the run rather than the repo.
  Fields: `train_fraction: float`; `coverage_target: float`; `seed: int`; `from_config: bool`.
- `def settings(run_dir: Path) -> Settings:` — The run's eval settings, falling back to the module defaults when it records none.
- `def _relative_to_cwd(path: Path, root: str) -> Path:` — `path` resolved, refused unless it sits inside `<cwd>/<root>`.
- `def resolve_in(target: Path) -> Path:` — The run directory whose `signals/`, `graph/` and `normalised/` BUDDHI reads.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `scores/` into.
- `def _repo_relative(path: Path) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _write_parquet(frame: pl.DataFrame, path: Path) -> str:` — Write, then hash what was written. Compression is pinned so two runs agree byte for byte.
- `def _meta_link(directory: Path) -> tuple[str | None, str | None]:` — Path and hash of a stage directory's `_meta.json`, for the staleness check.
- `def _conf_bounds(risk_score: float, in_set_0: bool, in_set_1: bool) -> tuple[float, float]:` — The `conf_low` / `conf_high` the console prints for one subject.
- `def _row_label(in_set_0: bool, in_set_1: bool) -> str:` — Section 7's `label`, from the conformal set alone.
- `def _calibration_frame(bundle: dict[str, Any], scored: pl.DataFrame, coverage_target: float) -> pl.DataFrame:` — One row per class per calibration method, with the coverage the console quotes.
- `def _embedding_complete(frame: pl.DataFrame) -> pl.Series:` — One bool per row: this subject has every embedding column, so the GNN booster can score it.
- `def build_run(run_dir: Path, out: Path, *, labels: pl.DataFrame | None, boundary_us: int | None, use_embeddings: bool=False) -> tuple[Path, pl.DataFrame | None]:` — Build `<out>/scores/` from the run's `normalised/`, `graph/` and `signals/`.

#### `src/chakravyuh/buildinfo.py`

Which revision of the code produced an artifact.

`docs/DATA-CONTRACTS.md` asks for `code_version` as a git sha and `tool_version` as the
package version, and the two are not the same fact. A packet that cites a seal has to be
traceable to the commit that produced it, or a replay cannot show it re-ran the same code.

- `def _git(args: list[str], root: Path) -> str | None:` — Run a git subcommand. Returns stdout stripped, or None if git could not answer.
- `@lru_cache(maxsize=1)` — The revision this code ran from, as `<12 hex>` or `<12 hex>-dirty`.

#### `src/chakravyuh/eval/external.py`

Elliptic / Elliptic++ external validation: the same recipe, on somebody else's labels.

The credibility question this module exists to answer is "you scored well on a world you built
yourself, so what?" The answer is a second number, produced by the *same* function that produced
the first one, on a dataset nobody here generated: Elliptic's 203,769 Bitcoin transactions with
the labels the Elliptic authors gave them.

**What is shared, and what is not.** The shared thing is the procedure, not the feature matrix.
`buddhi.recipe.train_and_score` takes `(X, y, time_index)` and does the time-ordered split, the
booster, the calibration, the conformal wrap and the scoring. CHAKRAVYUH hands it named
morphology; Elliptic hands it whatever numeric columns follow the id and the time step — 182 of
them in the vendored export (93 `Local_feature_*`, 84 `Aggregate_feature_*`, 5 `out_BTC_*`) —
which are not our named features and cannot be mapped onto them without inventing semantics that
are not there. So the claim this block supports is exactly "one procedure, two datasets" — no
stronger, and the report says so in `caveat` rather than letting a reader assume the features are
the same too. The classic `f1..f165` export loads through the same path unchanged; the loader
reads column positions, never names.

**Vendored, never fetched.** The box is air-gapped. The files are side-loaded under
`vendor/elliptic/` (see that directory's README for provenance and the expected names); this
module reads them and nothing else. When they are absent it returns
`{"available": false, "reason": "dataset_not_vendored"}` — the same honest-absence shape
`score_wallets` uses when a run has no answer key, never a placeholder zero.

**Where the numbers go.** `run()` writes one file, `measurements/<run>/elliptic_external.json`,
keyed on the hash of the vendored CSV so a reader can tell which bytes produced the figures. It is
computed by its own command rather than inside every scoring pass: the features and the recipe are
identical either way, and a 700 MB read plus a 300-round fit does not belong in a gate that scores
the same run twice.

- `def _locate(vendor_dir: Path, names: tuple[str, ...]) -> Path | None:` — The first of `names` that exists in `vendor_dir`, or None. Neither name is preferred.
- `def _load(vendor_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, Path] | None:` — The vendored CSVs as `(X, y, time_index, features_path)`, or None when not vendored.
- `def _auc(y: Sequence[int], scores: Sequence[float], *, pr: bool) -> float:` — The project's one AUC, so both legs are scored by the same arithmetic.
- `def elliptic_block(vendor_dir: Path, *, train_fraction: float, seed: int, coverage_target: float) -> dict[str, Any]:` — Train and score the shared recipe on the vendored Elliptic data.
- `def run(out: Path, *, vendor_dir: Path) -> dict[str, Any]:` — Score the Elliptic leg for the run `out` names, and file it beside that run's reports.
- `def main(argv: list[str] | None=None) -> int:` — `python -m chakravyuh.eval.external --out <run-dir> [--vendor vendor/elliptic]`.

#### `src/chakravyuh/eval/labels.py`

The audited doors labels reach a model through. Law 2 rule 3, as code.

Nothing outside `chakravyuh.eval` may read or construct a label. These functions are how a stage
that needs one asks for it, and every property that makes the resulting number honest is enforced
on this side of the door rather than trusted to the caller:

  one family per door   `origin_labels` returns which peer actually broadcast a transaction, for
                        SHASTRA. `wallet_labels` returns who owns an address and whether they are
                        illicit, for BUDDHI. Neither can return the other's labels, so a stage
                        cannot reach a label family its brief does not entitle it to by passing a
                        different argument.
  training window only  Both filter on the split boundary before returning anything. The caller
                        does not pass the boundary in: it is derived here, from the observable
                        capture's own time span, so a stage cannot widen its training window by
                        claiming the capture is longer than it is.
  no path arguments     A run id, exactly as `metrics.py` and `validate.py` take one. The answer
                        key's location is derived from it and cannot be pointed elsewhere.
  numbers out, or rows  A door returns labels, which is the point. What it never returns is the
                        holdout: `n_withheld` says how many rows the boundary removed, so a caller
                        can tell "the window is empty" from "the answer key is missing", and that
                        count is the only thing it learns about the far side.

Returning None rather than raising when the answer key is absent, for Law 2 rule 6: inference must
complete with `ground_truth/` moved away. A stage that asked for labels it cannot have should warn
and fall back to an unsupervised path, not die.

- Class `OriginLabels` — Which peer really broadcast each transaction, for the transactions a model may train on.
  Fields: `boundary_us: int`; `train_fraction: float`; `frame: pl.DataFrame`; `n_labelled: int`; `n_withheld: int`.
- Class `WalletLabels` — Who owns each address, for the addresses a model may train on.
  Fields: `boundary_us: int`; `train_fraction: float`; `frame: pl.DataFrame`; `n_labelled: int`; `n_withheld: int`.
- `def _roots(run_id: str) -> tuple[Path, Path]:` — The observable and truth trees for `run_id`, validated. Never a path from the caller.
- `def _boundary(observable: Path, train_fraction: float) -> tuple[int, pl.DataFrame]:` — The split boundary and the per-transaction first-observed time it was derived from.
- `def origin_labels(run_id: str, train_fraction: float) -> OriginLabels | None:` — SHASTRA's door. `(txid, origin_peer_ip)` for training-window transactions only.
- `def wallet_labels(run_id: str, train_fraction: float) -> WalletLabels | None:` — BUDDHI's door. `(address, owner_id, is_illicit, typologies)` for training-window addresses.

#### `src/chakravyuh/eval/metrics.py`

Cluster scoring. The only module that opens the clustering answer key.

A stage passes its predicted clusters in and gets two numbers back. No frame crosses back, no
label crosses back, and no argument is a path: the run id is what locates both the answer key and
the measurements directory, exactly as `validate.py` does it, so there is deliberately no way to
point this at a different run's truth.

The number is pairwise, not full-cluster. Contract section 5 quotes 0.36 precision and 0.44
recall for the multi-input heuristic on *full* clusters, where a cluster counts only if it is
recovered exactly. That metric is discontinuous: one wrong edge destroys a 134-address cluster's
score entirely, so it moves in jumps as an analyst drags a threshold and tells them nothing about
whether the drag helped. Pairwise precision and recall move smoothly, which is what the console
needs. The JSON records `metric: "pairwise"` so nobody compares these two numbers to the
contract's two by accident.

- Class `ClusterScore` — What a stage is allowed to learn about its own clustering. Numbers, never members.
  Fields: `pair_precision: float`; `pair_recall: float`; `pair_f1: float`; `predicted_pairs: int`; `true_pairs: int`; `shared_pairs: int`; `n_predicted_clusters: int`; `n_universe_addresses: int`.
- `def _pairs(groups: Sequence[Sequence[str]], universe: set[str]) -> set[tuple[str, str]]:` — Every unordered same-group pair, restricted to `universe`.
- `def score_clusters(run_id: str, predicted: Sequence[Sequence[str]], universe: Sequence[str], threshold: float, heuristics: Sequence[str]) -> ClusterScore | None:` — Score `predicted` against the run's answer key. Returns None when it is absent.
- Class `OriginScore` — What one estimator, or one trivial rule, scored. Shares of all broadcast transactions.
  Fields: `top1: float`; `top3: float`; `n_correct: int`; `n_ranked: int`; `n_abstained: int`; `top1_acted: float`; `precision_when_acted: float`; `coverage: float`; `by_traffic: Mapping[str, float]`; `by_window: Mapping[str, Any]`.
- `def _round(value: float) -> float:` — Six decimals, so two runs of one seed produce byte-identical reports.
- `def _traffic_expr() -> pl.Expr:` — Tor beats VPN when a run sets both, so the harder class is never reported as the easier.
- `def _score_ranked(ranked: pl.DataFrame, truth: pl.DataFrame, broadcast: int, windows: pl.DataFrame) -> OriginScore:` — Score a ranked candidate table against the answer key.
- `def _rank_by(candidates: pl.DataFrame, by: Sequence[str], descending: Sequence[bool]) -> pl.DataFrame:` — Turn a sort rule into a ranked candidate table, so a trivial rule scores through one path.
- `def _candidates(observable: Path) -> pl.DataFrame:` — One row per (txid, peer) an observer heard from, with the columns the trivial rules need.
- `def _payer_linkage(observable: Path, candidates: pl.DataFrame) -> pl.DataFrame:` — The strongest trivial rule: the peer seen across most of that payer's transactions.
- `def _windows(observable: Path, train_fraction: float) -> tuple[pl.DataFrame, int]:` — Each observed transaction's window, and the boundary. Derived, never hardcoded.
- Class `GranularityScore` — One estimator scored at one granularity. Shares of all broadcast transactions.
  Fields: `top1: float`; `topk: float`; `abstain_rate: float`; `n_correct: int`; `n_scored: int`; `by_traffic: Mapping[str, float]`.
- `def _rollup(ranked: pl.DataFrame, peers: pl.DataFrame, key: str, prior: pl.DataFrame | None) -> pl.DataFrame:` — Lift a per-candidate ranking to a per-key ranking, the way `asn_rollup` lifts it.
- `def _score_grain(ranked: pl.DataFrame, truth: pl.DataFrame, key: str, truth_key: str, broadcast: int) -> GranularityScore:` — Score a per-key ranking against the answer key. `ranked` has `txid`, `key`, `position`.
- `def _positioned(ranked: pl.DataFrame, key: str) -> pl.DataFrame:` — A per-candidate ranking as `txid`, `key`, `position`, `abstain`, position from `rank`.
- `def _l1_headline(observable: Path, truth: pl.DataFrame, broadcast: int) -> dict[str, Any] | None:` — Score the operator SHASTRA actually shipped in `origin_l1.parquet`, not a re-derivation.
- `def _by_granularity(ranked_l0: Mapping[str, pl.DataFrame], truth: pl.DataFrame, observable: Path, broadcast: int, candidates: pl.DataFrame, *, has_l1: bool, has_l2: bool) -> dict[str, Any]:` — The reframe's four granularities, each with its own ceiling and per-estimator accuracy.
- `def score_origin(run_id: str, *, train_fraction: float, observer_fraction: float, params: Mapping[str, Any]) -> dict[str, OriginScore] | None:` — Score every estimator in this run's `signals/` and write `origin_accuracy.json`.
- Class `WalletScore` — What a wallet risk model scored, on holdout subjects only. Numbers, never labels.
  Fields: `n_subjects: int`; `n_illicit: int`; `n_labelled: int`; `pr_auc: float`; `roc_auc: float`; `precision_at_20: float`; `recall_at_20: float`; `abstain_rate: float`; `coverage_by_class: dict[str, float]`; `baseline: dict[str, Any]`; `baseline_beaten: bool`; `n_unlabelled: int`.
- `def _auc(y_true: Sequence[int], scores: Sequence[float], pr: bool) -> float:` — PR-AUC by average precision, ROC-AUC by rank sum. Small data, no sklearn dependency.
- `def _true_label_of_subject(addresses: Sequence[str], truth: pl.DataFrame) -> tuple[int, int]:` — A subject's label: majority `is_illicit` over its member addresses' true owners.
- `def _campaign_recall(predictions: pl.DataFrame, truth_illicit: pl.DataFrame) -> tuple[int, int, float]:` — Campaign = illicit entity_id. Caught = >=1 of its addresses is in a flagged subject.
- `def score_wallets(run_id: str, *, predictions: pl.DataFrame, boundary_us: int, coverage_target: float, params: Mapping[str, Any], write: bool=True) -> dict[str, Any] | None:` — Score BUDDHI's wallet predictions against the run's answer key; write `model_report.json`.
- `def _write_wallet_report(run_id: str, *, y: list[int], s: list[float], subject_ids: list[str], precision_at_20: float, recall_at_20: float, abstain_rate: float, coverage: dict[str, float], n_unlabelled: int, boundary_us: int, coverage_target: float, params: Mapping[str, Any], write: bool=True, tx_pr_auc: float=0.0, tx_roc_auc: float=0.0, tx_precision_at_20: float=0.0, tx_n_scored: int=0, campaign_recall: float=0.0, n_campaigns: int=0, n_caught: int=0) -> dict[str, Any] | None:` — Assemble and write `model_report.json`, reading the baseline file if one exists.
- `def write_baseline_wallet(run_id: str, *, predictions: pl.DataFrame, boundary_us: int, params: Mapping[str, Any]) -> dict[str, Any] | None:` — Score the trivial baseline and file its bar at `measurements/<run>/baseline_wallet.json`.

#### `src/chakravyuh/eval/split.py`

Where the training window ends. One definition, called by every stage that trains.

This module holds no I/O and opens nothing. It is in `chakravyuh.eval` because the split is part
of how a run is measured rather than part of how it is generated, and because the label doors in
`labels.py` enforce it: a door filters on the boundary this function returns, so a stage that
disagreed with it about where the window ends would be handed labels it thought were holdout.

The boundary is derived from the capture's own observed time span rather than written down as a
timestamp. That is not tidiness. The five worlds behind the S06 accuracy curve differ in
`observer_fraction`, which changes how many announcements reach an observer at all and therefore
where the first and last observed microseconds fall; an absolute boundary tuned on one of them
would put a different share of a different world on each side, and the five accuracies would no
longer be comparable. A fraction of each world's own span puts the same share on each side of all
five.

Half-open on purpose. `seen_us < boundary_us` trains, `seen_us >= boundary_us` is holdout, so a
row exactly on the boundary is holdout. A closed interval would let the single most recent
training row be the one the split exists to hide.

- `def boundary_us(first_us: int, last_us: int, train_fraction: float) -> int:` — The first microsecond that is *not* in the training window.
- `def window_of(seen_us: int, boundary: int) -> str:` — Which side of `boundary` a microsecond falls on. The one place the comparison is written.

#### `src/chakravyuh/eval/validate.py`

Does this run measure what it claims to measure?

This module lives in `chakravyuh.eval` rather than in `chakravyuh.mayajaal` for one reason: it
opens `ground_truth/<run>/`, and CLAUDE.md permits exactly one package to do that. The generator
cannot check its own leakage, because checking leakage means holding the answer key next to the
capture and asking how much of the key the capture gives away.

Three groups of checks, and a run has to pass all three:

  invariants    Facts that are either true or the run is corrupt: a txid is sixty-four lowercase
                hex characters, an address list is as long as its amount list, the rows sharing a
                txid agree on that transaction's chain columns, inputs cover outputs, every
                announced txid exists on the chain and was announced before it was confirmed, no
                coinbase is announced at all, every announced transaction has exactly one true
                originator, no address has two owners, each observer answers to one address, and
                `counts.in == counts.out + counts.dropped` in every manifest.
  distributions Shape checks against `run_config.json`'s `validation` block. A generator that
                emits the right columns full of the wrong numbers passes every invariant above
                and is still useless: a uniform value distribution, a fixed relay delay or a
                metronomic block interval each erase a signal a later stage is supposed to find.
  leakage       How much of the answer key the capture leaks. Both directions are failures. Too
                much and the benchmark is trivial: if `first announcement seen` names the true
                originator nine times in ten, S03 has nothing to estimate. Too little and the
                problem is unwinnable, which is the same as unmeasurable.

Every number in the report is a count, a ratio or a row index. Nothing here writes an IP, an
address or a txid into `report.json`, `report.md` or a log line: the report is the one artifact of
this stage that a human reads, and CLAUDE.md's rule against emitting a complete identifier applies
hardest to the file most likely to be pasted into a chat window. Row indices are safe and are what
makes a failure findable with `scripts/peek.py`.

`report.md` deliberately omits the run id, so two runs of one seed produce byte-identical reports
and `make verify-determinism` can compare them directly.

- Class `Check` — One line of the report: what was measured, what it had to be, and whether it was.
  Fields: `group: str`; `name: str`; `ok: bool`; `value: str`; `bound: str`; `note: str = ''`.
- `def _num(value: float) -> str:` — Format a measurement. Six digits, because two runs of one seed must agree exactly and a float rendered shorter than it is hides a real difference between them.
- `def _capture(observable: Path) -> pl.DataFrame:` — Every CSV shard, read as text and concatenated in shard order.
- `def _delays(cap: pl.DataFrame, origins: pl.DataFrame) -> pl.DataFrame:` — The capture with each row's delay since its transaction was broadcast, in microseconds.
- `def _rows(frame: pl.DataFrame, predicate: pl.Expr) -> tuple[int, str]:` — Count the rows that break a rule and locate the first, so a failure is actionable.
- `def _invariants(cap: pl.DataFrame, txs: pl.DataFrame, origins: pl.DataFrame, delays: pl.DataFrame, entities: pl.DataFrame, endowment: pl.DataFrame) -> list[Check]:` — The checks whose failure means the run is broken rather than badly tuned.
- `def _manifests(observable: Path) -> list[Check]:` — Section 10's arithmetic, once per output directory.
- `def _xml_columns(path: Path) -> Sequence[str]:` — The child tags of the sample's first row. A column is an element name in this encoding, so checking the tags is checking the header.
- `def _headers(observable: Path) -> list[Check]:` — No ground-truth column name anywhere under `data/generated/`.
- `def _cv(values: pl.Series) -> float:` — Coefficient of variation, standard deviation over mean.
- `def _band(group: str, name: str, value: float, low: float | None, high: float | None, note: str='') -> Check:` — Internal helper; behavior is defined by the source implementation.
- `def _distributions(cfg: config.Config, cap: pl.DataFrame, txs: pl.DataFrame, blocks: pl.DataFrame, delays: pl.DataFrame) -> list[Check]:` — Shape, not correctness. Every bound comes from `run_config.json`'s `validation` block, so retuning the generator moves the bar in one file rather than in this module.
- `def _labelled(cap: pl.DataFrame, origins: pl.DataFrame) -> pl.DataFrame:` — The capture with the answer key attached and the features a trivial attacker would use.
- `def _accuracy(frame: pl.DataFrame, by: Sequence[str], descending: Sequence[bool], total: int) -> float:` — Accuracy of a rule that sorts the rows of a transaction and guesses the first one.
- `def _tree(frame: pl.DataFrame, total: int) -> float:` — How well a depth-two decision tree over the observable columns picks the originating row.
- `def _leakage(cfg: config.Config, frame: pl.DataFrame, broadcast: int) -> list[Check]:` — The checks that decide whether the benchmark is worth running at all.
- `def _config(observable: Path) -> config.Config:` — Reload the config the run recorded, not the one on disk at the repository root.
- `def _share(frame: pl.DataFrame, column: str) -> float:` — Internal helper; behavior is defined by the source implementation.
- `def _summary(cap: pl.DataFrame, txs: pl.DataFrame, blocks: pl.DataFrame, truth: Path) -> dict[str, Any]:` — Aggregates only, and every one of them a count or a ratio.
- `def _markdown(checks: Sequence[Check], summary: dict[str, Any], failed: int) -> str:` — The report a human reads. No run id, so two runs of one seed produce identical bytes and `make verify-determinism` can compare these files as it compares everything else.
- `def _json(checks: Sequence[Check], summary: dict[str, Any], failed: int) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/jaal/__main__.py`

`python -m chakravyuh.jaal --in data/generated/<run>/normalised --out data/generated/<run>`.

Scoring lives here and nowhere else in the stage. `chakravyuh.eval.metrics` is imported by this
file alone, so `stage.py` stays a pure read of `normalised/` and the one place the pipeline
touches the eval package is a file that is not itself part of the pipeline. The stage receives
two numbers back and never sees a label.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def _score(out: Path, threshold: float) -> None:` — Hand the predicted clusters to eval and print what comes back. Two numbers, no members.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/jaal/build.py`

The three `graph/` schemas in contract section 5's column order, and the facts.

Column order is part of the contract, not a stylistic choice: a parallel frontend track reads
these files and `contract-auditor` compares the order on disk against the document. `conform()`
is restated here rather than imported from SETU because no stage imports another stage's
internals, and the duplication is the price of that rule.

Facts only. Everything this module emits carries `confidence` 1.0, because it was read off the
chain or off the capture. The inferred edges live in `cluster.py` and never reach 1.0.

- Class `NormalisedInputError` — A `normalised/` directory JAAL cannot build a graph from.
- `def conform(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:` — `frame` selected in `schema`'s column order, each column cast to its declared type.
- `def _label_expr(prefix: str, column: str) -> pl.Expr:` — The `label` column for one node kind, already truncated.
- `def _nodes(frame: pl.DataFrame, prefix: str, kind: str, key: str, first: str, last: str) -> pl.DataFrame:` — One node per row of `frame`, which is already one row per distinct `key`.
- `def mark_transaction_nodes(node_frame: pl.DataFrame, coinjoin: pl.DataFrame, chains: pl.DataFrame) -> pl.DataFrame:` — `peel_chain_id` and `coinjoin` written onto the transaction nodes, and onto no others.
- `def address_nodes(addresses: pl.DataFrame) -> pl.DataFrame:` — One node per row of `normalised/addresses.parquet`. Never fewer.
- `def transaction_nodes(transactions: pl.DataFrame) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def peer_nodes(peers: pl.DataFrame) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def asn_nodes(peers: pl.DataFrame) -> pl.DataFrame:` — One node per distinct non-null ASN, spanning the window of every peer inside it.
- `def _value_edges(transactions: pl.DataFrame, side: str) -> pl.DataFrame:` — `SPENDS` for inputs, `RECEIVES` for outputs. Direction follows the money.
- `def chain_edges(transactions: pl.DataFrame) -> pl.DataFrame:` — Every input and output of every transaction, as directed value edges.
- `def announcement_edges(announcements: pl.DataFrame) -> pl.DataFrame:` — One edge per distinct `(txid, peer_ip)`, carrying the earliest time that pair was seen.
- `def hosting_edges(peers: pl.DataFrame, from_lookup: bool) -> pl.DataFrame:` — `peer:` to `asn:`, one per peer with a resolved ASN.

#### `src/chakravyuh/jaal/cluster.py`

The two clustering heuristics, and the derived cluster view.

`SAME_OWNER` is an edge with a confidence and a named heuristic. It never merges nodes. The
multi-input heuristic measures 0.36 precision on full clusters in law enforcement settings, so a
hard merge would be wrong roughly two times in three, and an analyst who moved a threshold could
never get the original graph back. Cluster membership is recovered here by running connected
components over the edges above a threshold, which is a read, not a write: delete the
`MEMBER_OF` edges and `clusters.parquet` and the graph is exactly what it was.

Edges within one transaction form a star rather than a clique: every input address is linked to
the lexicographically smallest input address of that transaction. Connected components,
`min_edge_confidence` and the derived clusters are all identical either way, because a clique and
a star over the same vertex set have the same component, and a star is n-1 edges where a clique is
n(n-1)/2. One transaction in a 2000-transaction run already has 38 inputs, which is 703 clique
edges carrying no information the 37 star edges do not.

- `def _member_pairs(frame: pl.DataFrame, members: str, context: tuple[str, ...]=()) -> pl.DataFrame:` — The shared star construction, optionally retaining transaction provenance.
- `def _star(frame: pl.DataFrame, members: str, evidence: str, confidence: float) -> pl.DataFrame:` — Link every address in `members` to that row's lexicographically smallest member.
- `def common_input_edges(transactions: pl.DataFrame) -> pl.DataFrame:` — Common input ownership: spending two addresses in one transaction needs both keys.
- `def _change_members(transactions: pl.DataFrame) -> pl.DataFrame:` — Transactions with a determinate change output, as one `members` list each.
- `def change_edges(transactions: pl.DataFrame) -> pl.DataFrame:` — Change-address detection: the suspected change output belongs to the sender.
- `def set_aside_edges(transactions: pl.DataFrame) -> dict[str, int]:` — The candidate edges the mixer set-aside suppressed, counted rather than asserted.
- `def same_owner_edges(transactions: pl.DataFrame) -> pl.DataFrame:` — Every candidate `SAME_OWNER` edge from both heuristics, deduplicated.
- `def components(edges: pl.DataFrame, threshold: float) -> list[list[str]]:` — Connected components of the `SAME_OWNER` edges at or above `threshold`.
- `def clusters(edges: pl.DataFrame, threshold: float) -> tuple[pl.DataFrame, pl.DataFrame]:` — The derived view: `clusters.parquet` and the `MEMBER_OF` edges that point into it.
- `def cluster_nodes(cluster_frame: pl.DataFrame) -> pl.DataFrame:` — One `cluster:` node per cluster, spanning nothing.

#### `src/chakravyuh/jaal/mixer.py`

The mixer detector, and the set-aside that keeps ownership heuristics off a CoinJoin.

Equal-value outputs are the mark of a collaborative transaction: several unrelated parties signed
one transaction together, so its inputs belong to strangers and every ownership claim read off
those inputs is wrong by construction. SETU already flags the shape (`has_equal_outputs`). This
module turns that flag into a decision with a name, so "we did not apply common-input ownership
across this transaction" is a recorded act with a reason rather than a filter nobody wrote down.

A one-input transaction with equal outputs is not a mixer. It is one party splitting their own
coin, and their inputs and outputs do belong to one owner. That is why `n_in >= 2` is part of the
rule and not an optimisation: the plural inputs are what make the inputs strangers.

The output threshold is restated rather than imported from `shastra.typology`, because no stage
reads another stage's internals. It is the same number on purpose — three equal outputs is a
mixing round in both layers, so the two use one word for one shape. JAAL's rule is a strict subset
of SHASTRA's: the same output shape, plus the plural inputs. A run where the two disagree is a
split SHASTRA names `coinjoin_like` and this module refuses to.

Nothing here reads a label. A mixer is a shape in the capture, and this module can be wrong about
it, which is why the mark is a reason attached to a transaction and not a deletion.

- `def is_mixer() -> pl.Expr:` — A boolean expression over `normalised/transactions.parquet`'s own columns.
- `def flags(transactions: pl.DataFrame) -> pl.DataFrame:` — One row per transaction: its `txid` and whether it is a mixer.

#### `src/chakravyuh/jaal/provenance.py`

Event ledger and point-in-time ownership views, without labels or destructive merges.

Legacy graph artifacts omit ownership timestamps. This opt-in API retains every transaction's
claim before deduplication so later stronger evidence cannot acquire an earlier timestamp.
The event time is first_seen_us: callers must ensure the complete transaction body was available
then. If ingestion receives the body later, supply that later availability time instead.
Confidence values are existing heuristic weights, not measured pair-ownership probabilities.

- `def _claims(frame: pl.DataFrame, members: str, evidence: str, confidence: float) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def ownership_evidence(transactions: pl.DataFrame) -> pl.DataFrame:` — Retain transaction/time provenance for both existing ownership heuristics.
- `def snapshot_edges(ledger: pl.DataFrame, cutoff_us: int) -> pl.DataFrame:` — Select strongest evidence known at or before cutoff; retain its actual timestamp.

#### `src/chakravyuh/jaal/stage.py`

JAAL as a stage: read `normalised/`, write `graph/`, account for every candidate edge.

The path guards are KAVACH's and SETU's, restated rather than imported. No stage imports another
stage's internals, and the rule pays for itself here too: `--in` is allowlisted to `data/`, so a
JAAL invocation cannot be pointed at the answer key even by an operator who wants to, because the
answer key is a sibling tree and not under `data/`.

Nothing truth-derived is written here. `graph/_meta.json` carries no precision, no recall and no
path into a sibling tree, so the two determinism runs in `make verify-s05` agree byte for byte
whether or not scoring ran.

- Class `InputPathError` — A path JAAL will not read from, or will not write to.
- `def _relative_to_cwd(path: Path, root: str) -> Path:` — `path` resolved, refused unless it sits inside `<cwd>/<root>`.
- `def resolve_in(target: Path) -> Path:` — The `normalised/` directory to build a graph from.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `graph/` into.
- `def _repo_relative(path: Path) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _write_parquet(frame: pl.DataFrame, path: Path) -> str:` — Write, then hash what was written. Compression is pinned so two runs agree byte for byte.
- `def _upstream_meta(normalised: Path) -> tuple[str | None, str | None, bool]:` — The staleness link plus upstream's `geolite2` flag: path, hash, whether a lookup ran.
- `def build_run(normalised: Path, out: Path, threshold: float=cluster.DEFAULT_THRESHOLD) -> Path:` — Build `<out>/graph/` from `normalised/`. Returns the path to `_meta.json`.

#### `src/chakravyuh/jaal/trace.py`

The peel-chain tracer: walk one coin out through its small-peel-plus-change hops.

A peel hop is one transaction that pays a thin slice away and carries the rest on as change. One
hop is ordinary. A run of them is the typology, because the run is one coin being walked away from
where it came from, a slice at a time, and the change output is the thread that ties the hops
together. This module follows that thread.

It is deliberately sharper than `shastra.typology`'s peel hit, which counts peel-shaped
transactions per subject. A count is not a chain: two peels by one owner on unrelated coins are
two hits and no chain, and nothing in a count says which transaction followed which. The tracer
links a hop to the next only through the change output the next hop actually spends, so what it
emits is a path with a depth and a leak rate rather than a tally.

Neither module imports the other; the shared number is restated, the same way `conform()` and the
path guards are. `PEEL_MAX_SHARE` here is `shastra.typology`'s, and the two criteria agreeing on
what a peel looks like is the point — a stage that disagreed with itself about the shape would make
both numbers unreadable.

Nothing here reads a label or the answer key. A chain is a shape in the transaction graph, and the
tracer can be wrong about it, which is why a chain is a row with a depth and a stopping reason
rather than a deletion or a merge.

- `def hops(transactions: pl.DataFrame) -> pl.DataFrame:` — One row per peel-shaped transaction, with what the tracer needs to link it onward.
- `def _spenders(transactions: pl.DataFrame, change_addresses: pl.Series) -> pl.DataFrame:` — `address -> sorted txids that spend it`, restricted to the change addresses hops produced.
- `def _links(hop_frame: pl.DataFrame, spent_by: pl.DataFrame) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:` — `hop -> next hop` and `hop -> why the walk stopped`, for hops that have no next hop.
- `def _walk(hop_ids: set[str], successor: dict[str, str], predecessor: dict[str, str]) -> tuple[list[list[str]], list[str]]:` — `(every maximal path, the hops where a walk was cut short by a revisit)`.
- `def peel_chains(transactions: pl.DataFrame) -> pl.DataFrame:` — Every peel chain of two hops or more, numbered in a deterministic order.

#### `src/chakravyuh/jaal/view.py`

The optional Kùzu Cypher view over `graph/`.

Kùzu is a demo convenience: it lets an analyst ask a Cypher question about a graph that already
exists as three Parquet files. It is never a hard dependency, so the import lives inside the
function rather than at module scope. With Kùzu absent the graph is complete and only this view
is unavailable, which is the path this repo actually runs: `import kuzu` fails here.

- `def available() -> bool:` — Whether Kùzu can be imported at all. Recorded in `_meta.json` under `optional_deps`.
- `def cypher_view(graph_dir: Path, database: Path | None=None) -> Path | None:` — Load `graph/` into a Kùzu database beside it. None when Kùzu is not installed.

#### `src/chakravyuh/kavach/__main__.py`

`python -m chakravyuh.kavach --in <capture> --out data/generated/<run>`.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/kavach/readers.py`

Three encodings in, one list of string-valued rows out.

Nothing here coerces, validates or rejects. A reader's whole job is to undo the encoding and
hand back what the file said, with the column names canonicalised and every value as a string
or a list of strings. Coercion happens once, in `seal.py`, so CSV, JSONL and XML cannot drift
into three slightly different notions of what a null is.

That convergence is also the test: `tests/test_kavach.py` seals all three fixture encodings
and asserts the resulting `rows.parquet` files are byte-identical. If a reader invents a
difference, that assertion is where it surfaces.

One shared rule, and it is the only place the encodings genuinely disagree. XML cannot tell an
empty list from a null, because both are an empty element. Section 1 fixes which columns are
lists, so every reader keys on the column name: a missing value in a list column is an empty
list everywhere, and a missing value in a scalar column is null everywhere.

- Class `Source` — One input file, decoded but not yet interpreted.
  Fields: `path: Path`; `container: Container`; `encoding: Encoding`; `headers: dict[str, str]`; `unknown_headers: tuple[str, ...]`; `rows: list[Row]`.
- `def decompress(raw: bytes) -> tuple[bytes, Container]:` — The capture's bytes, unwrapped, and what was wrapped around them.
- `def decode(raw: bytes, path: Path) -> str:` — UTF-8 text with any BOM removed, or a refusal naming the file.
- `def _map_headers(names: list[str]) -> tuple[dict[str, str], tuple[str, ...]]:` — Canonical name to original spelling, plus whatever we could not place.
- `def _split_list(value: str) -> list[str]:` — A CSV list cell. Pipe separated with no spaces, per the contract's conventions.
- `def _cell_from_text(column: str, value: str | None) -> Cell:` — One textual cell, with the list-or-null question settled by the column name.
- `def _stringify(value: object) -> str:` — One JSON scalar as text, without letting a float near an amount.
- `def _cell_from_json(column: str, value: object) -> Cell:` — One JSON value as a cell, keyed on the column name like every other reader.
- `def read_csv(text: str, path: Path) -> Source:` — Delimited text with a header row.
- `def read_jsonl(text: str, path: Path) -> Source:` — One JSON object per line.
- `def _xml_cell(column: str, element: ET.Element) -> Cell:` — One XML element as a cell. Repeated `<item>` children are the list form.
- `def read_xml(text: str, path: Path) -> Source:` — Repeated row elements, with repeated `<item>` children for lists.
- `def read(raw: bytes, path: Path) -> Source:` — Any of the three encodings, in any of the supported containers.

#### `src/chakravyuh/kavach/schema.py`

What a capture column is called, what shape its values have, and what units they carry.

Everything in this module is a decision about someone else's file. KAVACH is the only stage
that reads data it did not write, so the tolerance lives here and nowhere downstream: by the
time `sealed/rows.parquet` exists, the column names are the contract's names, the amounts are
satoshis and the timestamps are UTC microseconds, and no later stage has to wonder.

Three detections, all from content and never from a filename:

- the container, from the first magic bytes, so a zstd-compressed capture is transparent
- the encoding, from the first non-whitespace byte of the decompressed text
- the amount unit and the timestamp format, from the values themselves

The amount rule is the one worth reading twice. "Any decimal anywhere means BTC" is wrong in a
way that hides: one malformed decimal in a satoshi file would flip every value by 1e8, and
because the factor applies to inputs and outputs alike, value conservation still holds and the
invariant that should catch it never fires. So a column is satoshis only when every parseable
token is integer-shaped, BTC only when every parseable token is fractional, and anything mixed
is an error naming the column rather than a guess.

- Class `Encoding` — How the decompressed bytes are laid out.
- Class `Container` — What, if anything, is wrapped around those bytes.
- Class `AmountUnit` — Source-defined class.
- Class `TimestampFormat` — Source-defined class.
- Class `Shape` — What one amount token looks like before anything is assumed about its unit.
- Class `CaptureFormatError` — The file cannot be read at all: wrong shape, ambiguous units, missing required column.
- `def detect_container(head: bytes) -> Container:` — Which compression wraps these bytes, from the magic number alone.
- `def detect_encoding(text: str) -> Encoding:` — CSV, JSONL or XML, from the first character that is not whitespace or a BOM.
- `def canonical_column(name: str) -> str | None:` — The contract's name for a header, or None if we do not recognise it.
- `def amount_shape(token: str) -> Shape:` — Whether one amount token is integer-shaped, fractional, or neither.
- `def detect_amount_unit(columns: dict[str, list[str]]) -> AmountUnit:` — Satoshis or BTC for the whole file, or an error naming the column that cannot decide.
- `def to_sats(token: str, unit: AmountUnit) -> int:` — One amount token as int64 satoshis, or ValueError.
- `def detect_timestamp_format(tokens: list[str]) -> TimestampFormat:` — Which of the contract's four timestamp spellings this file uses.

#### `src/chakravyuh/kavach/seal.py`

Hash, read, coerce, route and account for every row of someone else's capture.

The order of the first two verbs is the whole custody claim. `sealed/INPUT.sha256` is written
from the bytes as delivered, before a reader is constructed, so the hash in the S09 evidence
packet is a statement about the file that arrived rather than about whatever survived parsing.
`tests/test_kavach.py` asserts that order by breaking the reader and checking the hash file
exists anyway.

The second commitment is arithmetic. `rows_read == rows_sealed + rows_rejected`, with no third
outcome anywhere in this module. A row that cannot be coerced is written to
`sealed/rejected.parquet` with a reason you can point at; nothing is dropped, because a count
that does not reconcile is worse than a rejection.

This stage reads `data/` and writes `data/generated/<run>/sealed/` and nothing else.

- Class `InputPathError` — A path KAVACH will not read from, or will not write to.
- Class `InputFile` — Source-defined class.
  Fields: `path: Path`; `size: int`; `sha256: str`.
- Class `Accounting` — Everything the manifest has to be able to say afterwards.
  Fields: `rows_read: int = 0`; `rows_sealed: int = 0`; `rows_rejected: int = 0`; `reject_reasons: dict[str, int] = field(default_factory=dict)`; `warnings: list[str] = field(default_factory=list)`; `duplicate_rows: int = 0`.
- `def _relative_to_cwd(path: Path, root: str) -> Path:` — `path` resolved, refused unless it sits inside `<cwd>/<root>`.
- `def _is_capture(path: Path) -> bool:` — Whether a file in an input directory looks like a capture rather than a manifest.
- `def resolve_inputs(target: Path) -> tuple[list[Path], Path]:` — The capture files to seal, sorted, plus the directory they came from.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `sealed/` into, refused unless it is under `data/generated/`.
- `def hash_inputs(paths: list[Path], sealed: Path) -> list[InputFile]:` — Hash every input byte for byte and write `INPUT.sha256`, before anything is parsed.
- `def _parse_timestamp(token: str, fmt: TimestampFormat) -> tuple[int, bool]:` — UTC microseconds, and whether the source string carried no timezone.
- `def _ip_version(value: str) -> int | None:` — Internal helper; behavior is defined by the source implementation.
- `def _as_list(cell: readers.Cell) -> list[str]:` — Internal helper; behavior is defined by the source implementation.
- `def _as_text(cell: readers.Cell) -> str | None:` — Internal helper; behavior is defined by the source implementation.
- `def _raw_view(row: readers.Row) -> dict[str, object]:` — The row as it arrived, for `rejected.parquet`. A rejected value may not coerce at all.
- `def _coerce(row: readers.Row, row_id: int, unit: AmountUnit, fmt: TimestampFormat, present: frozenset[str]) -> tuple[dict[str, object] | None, str | None, bool]:` — One row, coerced, or the reason it cannot be. First failure wins.
- `def _chain_key(sealed: dict[str, object]) -> tuple[object, ...]:` — The chain columns of one row, hashable, for the agreement check.
- `def _quarantine_disagreeing(sealed_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], set[int]]:` — Invariant 5: rows sharing a txid must agree on the chain columns.
- `def _frame(rows: list[dict[str, object]], schema: dict[str, pl.DataType]) -> pl.DataFrame:` — A DataFrame with the declared schema, correct even when there are no rows.
- `def _write_parquet(frame: pl.DataFrame, path: Path) -> str:` — Write, then hash what was written. Compression is pinned so two seals agree byte for byte.
- `def _masked_manifest_sha256(manifest: dict[str, object]) -> str:` — The manifest's hash with its wall clock removed.
- `def _upstream_meta(directory: Path) -> tuple[str | None, str | None]:` — The `_meta.json` beside the capture, as a repo-relative path and a hash.
- `def seal(target: Path, out: Path) -> Path:` — Seal a capture into `<out>/sealed/`. Returns the path to `manifest.json`.

#### `src/chakravyuh/mayajaal/__main__.py`

`python -m chakravyuh.mayajaal` — the command line for the generator.

MAYAJAAL-SPEC's own example is `mayajaal --txs 100000 --seed 42`, and those two plus the entity
count are the only parameters this CLI may override. Everything else comes from
run_config.json, whose effective form is copied into the run directory so a run always carries
the numbers that produced it.

One program, one process, one run: the chain, the campaigns that compete inside it, the peer
network that carries it and the capture an observer would have recorded are all built here in
sequence. Nothing reads back what an earlier layer wrote, because a layer that reloads its own
output is a layer that can disagree with it.

`--out` is the only path argument in the whole stage. The answer key directory is derived from
it, never passed in, which is what keeps every label inside one quarantined tree.

Progress goes to the log, never to stdout, and never contains a row of data.

- `def _parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def _overrides(pairs: list[str]) -> dict[str, str]:` — Split `KEY=VALUE` strings, rejecting a repeated key rather than letting the last one win.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/mayajaal/adversary.py`

MAYAJAAL-SPEC Layer 4: laundering campaigns as agents rather than stamped shapes.

A campaign is a small agent with a disposition, a coin and a current holder. Each block it may
pick one move, weighted by its own risk appetite, and ask the chain layer to build that move
against the live ledger. The move is a request and not a guarantee: a peel whose holder cannot
fund it does not happen, and the campaign carries on from wherever it actually got to.

That is why the typology is derived at the end rather than chosen at the start. A campaign is
named after the moves that actually produced transactions, so `campaigns.parquet` describes what
happened, and `entities.typologies` names only entities a campaign really routed value through.
A label with no transaction behind it would be unscoreable, which is exactly what S01 refused to
write.

The moves split into two families, and the difference is where the coin ends up. `peel` and
`structure` send a slice onward and keep the remainder as change, so the holder does not move:
that trailing change output is what a peel chain is recognised by. `hop`, `split`, `mix` and
`merge` send the pot on, so the holder becomes the recipient. `dwell` produces no transaction at
all, and `cash_out` ends the campaign at an exchange.

- `def _spare(amount: int, dust: int) -> int:` — `amount` less the fee reserve: what a move may actually ask to send.
- `def _largest(ctx: Context, who: int) -> int:` — The biggest single coin `who` can spend now, which is the coin a campaign is moving.
- `def _balance(ctx: Context, who: int) -> int:` — Everything `who` can spend now. Only `merge` wants this.
- `def _weights(cfg: Config, appetite: float) -> WeightedIndex[str]:` — Each move's weight interpolated between its cautious and hurried endpoints.
- Class `Campaign` — One agent. Everything after `wait` is the record of what it did, not what it meant to.
  Fields: `campaign_id: str`; `appetite: float`; `moves: WeightedIndex[str]`; `budget_moves: int`; `start_block: int`; `holder: int`; `wait: int = 0`; `done: bool = False`; `participants: dict[int, None] = field(default_factory=dict)`; `ran: dict[str, int] = field(default_factory=dict)`; `txids: list[str] = field(default_factory=list)`; `start_us: int = 0`; `end_us: int = 0`; `total_sats: int = 0`.
- Class `Adversary` — Every campaign in the run, and the one method `chain.generate` calls per block.
  Fields: `cfg: Config`; `rng: random.Random`; `pop: Population | None = None`; `budget: int = 0`; `pending: list[Campaign] = field(default_factory=list)`; `live: list[Campaign] = field(default_factory=list)`; `finished: list[Campaign] = field(default_factory=list)`; `mules: tuple[int, ...] = ()`; `mixers: tuple[int, ...] = ()`.

#### `src/chakravyuh/mayajaal/chain.py`

MAYAJAAL-SPEC Layer 2: the block clock, coinbase, coin selection and the transactions.

One function builds one transaction against the live ledger, and `generate` is the loop that
calls it. The shape of a transaction is where the detectors downstream get their signal, so the
awkward cases are produced here on purpose rather than left to chance: change that sits at a
random output index, change that is sometimes a reused address, payments that are sometimes
round numbers, spends that sometimes pool inputs from two different entities.

Money is `int` satoshis end to end. Floats appear only inside a distribution draw and are cast
before they are stored, which is why every draw goes through `_draw_sats` or `_fee_rate`.
Conservation is not asserted here, it is arithmetic: the change output is defined as whatever
is left after the payments and the fee, and when that remainder is below dust it becomes fee.

- Class `Tx` — One transaction. The trailing fields are ground truth and never reach observable output.
  Fields: `txid: str`; `height: int`; `time_us: int`; `is_coinbase: bool`; `inputs: tuple[Outpoint, ...]`; `input_addresses: tuple[str, ...]`; `input_sats: tuple[int, ...]`; `output_addresses: tuple[str, ...]`; `output_sats: tuple[int, ...]`; `output_kinds: tuple[str, ...]`; `fee_sats: int`; `fee_rate: int`; `vsize_vb: int`; `sender: int`; `input_owners: tuple[int, ...]`; `change_index: int`; `violations: tuple[str, ...]`.
- Class `Seed` — One prehistory output. The ledger starts mid-chain, so the first spend has something to spend. Written out so the invariant test can replay the UTXO set from files alone.
  Fields: `txid: str`; `vout: int`; `address: str`; `script_type: str`; `sats: int`; `height: int`.
- Class `Counters` — Run bookkeeping. `attempts`/`built`/`dropped` feed section 10's counts, which must satisfy `in == out + dropped`, so every attempt lands in exactly one of the last two.
  Fields: `attempts: int = 0`; `built: int = 0`; `drops: dict[str, int] = field(default_factory=dict)`.
- Class `MultiInput` — Holds the multi-input rate near its target without pinning it to a constant.
  Fields: `target: float`; `gain: float`; `multi: int = 0`; `total: int = 0`.
- `def _vsize(cfg: Config, in_kinds: list[str], out_kinds: list[str]) -> int:` — Estimated virtual size in vbytes, from the per-script-type table in run_config.json.
- `def _fee_rate(cfg: Config, rng: random.Random) -> int:` — Whole sat/vB, lognormal and clamped. Whole because that is what wallets let you set.
- `def _draw_sats(rng: random.Random, mu: float, sigma: float, floor: int) -> int:` — The only place a value becomes money. Cast happens here, so nothing downstream is float.
- `def endow(cfg: Config, pop: Population, book: Ledger, rng: random.Random) -> list[Seed]:` — Give every entity its opening balance as real UTXOs, one prehistory transaction each.
- `def _select(cfg: Config, cands: list[tuple[Outpoint, Utxo]], need: int, min_inputs: int, out_kinds: list[str], fee_rate: int) -> list[tuple[Outpoint, Utxo]] | None:` — Choose inputs covering `need` plus the fee the choice itself implies, or None.
- `def _cosigner(cfg: Config, pop: Population, book: Ledger, rng: random.Random, height: int, avoid: int, fee_rate: int) -> tuple[Outpoint, Utxo, str, str, int] | None:` — A second entity's input plus the output paying it back, or None if nobody can join.
- Class `Intent` — What one campaign move wants from one transaction. None means "use the type's policy".
  Fields: `to: int | None = None`; `outputs: tuple[int, int] | None = None`; `equal: bool | None = None`; `sats: int | None = None`; `min_inputs: int | None = None`.
- `def payment(cfg: Config, pop: Population, book: Ledger, rng: random.Random, *, sender_index: int, height: int, time_us: int, control: MultiInput, intent: Intent | None=None) -> Tx | None:` — One spend by `sender_index`, or None when the sender cannot afford one.
- `def _coinbase(cfg: Config, pop: Population, book: Ledger, rng: random.Random, *, height: int, time_us: int, fees: int) -> Tx:` — The block reward, paid to one pool chosen in proportion to its hashrate.
- Class `Block` — Source-defined class.
  Fields: `height: int`; `time_us: int`; `n_txs: int`; `coinbase_txid: str`; `subsidy_sats: int`; `fees_sats: int`.
- Class `Run` — Everything one run produced. `writers` decides which halves are observable.
  Fields: `population: Population`; `seeds: tuple[Seed, ...]`; `blocks: tuple[Block, ...]`; `txs: tuple[Tx, ...]`; `counters: Counters`; `multi_input_rate: float`.
- `def _quota(n_txs: int, n_blocks: int) -> list[int]:` — Spread the requested payment count over the blocks, remainder to the earliest blocks.
- Class `Context` — One block, handed to an actor so it can spend inside the run rather than beside it.
  Fields: `cfg: Config`; `pop: Population`; `book: Ledger`; `rng: random.Random`; `control: MultiInput`; `counters: Counters`; `height: int`; `time_us: int`.
- `def generate(cfg: Config, rng: random.Random, plan: ActorPlan | None=None) -> Run:` — Build the whole chain. Deterministic given `rng`, which is the only source of randomness.

#### `src/chakravyuh/mayajaal/config.py`

Load `run_config.json` into frozen, typed parameter objects.

Every number MAYAJAAL uses arrives through here. There is no default anywhere in this
module: a missing key raises, naming the path it was looked for under. That is deliberate
and it is the mechanism behind the stage rule "no hardcoded parameter" — a knob that does
not exist in the config file cannot be silently supplied by code instead.

The three CLI overrides (seed, transaction count, entity count) are the exception the spec
itself defines (`mayajaal --txs 100000 --seed 42`). They are folded into `Config.effective`,
which is the dict written back out beside the run, so a run's own directory always records
the parameters that produced it rather than the file's defaults.

- `def _get(node: Mapping[str, Any], path: str, key: str) -> object:` — Returns `object`, not `Any`: every caller below has to prove the type it wants.
- `def _int(node: Mapping[str, Any], path: str, key: str) -> int:` — Internal helper; behavior is defined by the source implementation.
- `def _float(node: Mapping[str, Any], path: str, key: str) -> float:` — Internal helper; behavior is defined by the source implementation.
- `def _bool(node: Mapping[str, Any], path: str, key: str) -> bool:` — Internal helper; behavior is defined by the source implementation.
- `def _str(node: Mapping[str, Any], path: str, key: str) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _obj(node: Mapping[str, Any], path: str, key: str) -> dict[str, Any]:` — Internal helper; behavior is defined by the source implementation.
- `def _pair(node: Mapping[str, Any], path: str, key: str) -> tuple[int, int]:` — An inclusive [low, high] integer range. High below low is a config error, not a clamp.
- `def _fpair(node: Mapping[str, Any], path: str, key: str) -> tuple[float, float]:` — A two-element list of numbers. Order is not checked: `move_weights` uses it as a pair of endpoints to interpolate between, and a cautious weight below the hurried one is a legitimate way to describe a move a hurried campaign prefers.
- `def _strs(node: Mapping[str, Any], path: str, key: str) -> tuple[str, ...]:` — Internal helper; behavior is defined by the source implementation.
- `def _weights(node: Mapping[str, Any], path: str, key: str) -> dict[str, float]:` — Internal helper; behavior is defined by the source implementation.
- `def _ints(node: Mapping[str, Any], path: str, key: str) -> dict[str, int]:` — Internal helper; behavior is defined by the source implementation.
- Class `TypeSpec` — One row of MAYAJAAL-SPEC Layer 1's entity table, plus its wallet and value policy.
  Fields: `name: str`; `share: float`; `tx_rate: float`; `receive_rate: float`; `value_mu: float`; `value_sigma: float`; `n_addresses: tuple[int, int]`; `reuse_rate: float`; `change_policy: str`; `outputs: tuple[int, int]`; `equal_outputs: bool`; `illicit_capable: bool`.
- Class `WorldSpec` — Source-defined class.
  Fields: `n_entities: int`; `illicit_entity_share: float`; `illicit_tx_share: float`; `cgnat_share_individuals: float`; `cgnat_share_mules: float`; `cgnat_addresses_per_region: int`; `ips_per_entity: tuple[int, int]`; `ipv6_share: float`; `ipv4_pool: str`; `cgnat_pool: str`; `ipv6_pool: str`; `active_hours_len: tuple[int, int]`.
- Class `NetworkSpec` — MAYAJAAL-SPEC Layer 3. `observer_fraction` is the parameter that decides everything.
  Fields: `n_nodes: int`; `outbound_per_node: int`; `max_inbound: int`; `relay_delay_outbound_mean_s: float`; `relay_delay_inbound_mean_s: float`; `latency_matrix: Path`; `n_observers: int`; `observer_fraction: float`; `observer_placement: str`; `tor_share: float`; `vpn_share: float`; `bucket_penalty: float`; `flood_frontier: int`; `n_tor_exits: int`; `n_vpn_nodes: int`; `unresolved_asn_share: float`; `unresolved_geo_share: float`; `inv_share: float`; `listen_port: int`; `ephemeral_ports: tuple[int, int]`; `observer_pool: str`; `tor_pool: str`; `vpn_pool: str`; `tor_asn: int`; `vpn_asn: int`.
- Class `AdversarySpec` — MAYAJAAL-SPEC Layer 4. `move_weights` maps a move to a (cautious, hurried) pair of weights; a campaign interpolates between them by its own risk appetite, so the move mix is a consequence of the agent's disposition rather than a typology stamped on the graph.
  Fields: `n_campaigns: int`; `moves_per_campaign: tuple[int, int]`; `risk_appetite_dist: str`; `structuring_threshold_sats: int`; `peel_share: tuple[float, float]`; `split_outputs: tuple[int, int]`; `mix_outputs: tuple[int, int]`; `merge_inputs: tuple[int, int]`; `dwell_blocks: tuple[int, int]`; `move_gap_blocks: tuple[int, int]`; `move_weights: Mapping[str, tuple[float, float]]`.
- Class `ExportSpec` — Source-defined class.
  Fields: `shard_rows: int`; `formats: tuple[str, ...]`; `xml_sample_rows: int`.
- Class `ChainSpec` — Source-defined class.
  Fields: `start_height: int`; `genesis_us: int`; `block_interval_s: float`; `txs_per_block: int`; `min_blocks: int`; `coinbase_subsidy_sats: int`; `coinbase_maturity_blocks: int`; `pool_payout_interval_blocks: int`; `pool_payout_outputs: tuple[int, int]`; `hashrate_mu: float`; `hashrate_sigma: float`; `dust_threshold_sats: int`; `min_payment_sats: int`; `multi_input_rate: float`; `multi_input_controller_gain: float`; `collaborative_multi_input_rate: float`; `max_pick_attempts: int`; `coin_select_window: int`; `address_reuse_rate: float`; `round_payment_rate: float`; `round_to_sats: int`; `endow_utxos: tuple[int, int]`; `endow_mu_offset: float`; `endow_sigma: float`; `fee_mu: float`; `fee_sigma: float`; `fee_min_sat_per_vb: int`; `fee_max_sat_per_vb: int`; `script_weights: Mapping[str, float]`; `vsize_overhead_vb: int`; `input_vb: Mapping[str, int]`; `output_vb: Mapping[str, int]`.
- Class `ValidationSpec` — Thresholds the tests assert against, so a tuning change moves the bar in one place.
  Fields: `value_p99_over_p50_min: float`; `value_p999_over_p50_min: float`; `multi_input_rate_tolerance: float`; `announcements_per_tx_tolerance: float`; `origin_recoverable_min: float`; `first_seen_leakage_min: float`; `first_seen_leakage_max: float`; `trivial_rule_max: float`; `tree_leakage_max: float`; `delay_cv_min: float`; `block_interval_cv_min: float`; `block_interval_cv_max: float`.
- Class `EvalSpec` — How a run is split into a training window and a holdout, and when an estimator abstains.
  Fields: `train_fraction: float`; `margin_floor: float`; `min_announcements: int`.
- Class `Config` — Source-defined class.
  Fields: `seed: int`; `n_txs: int`; `mean_announcements_per_tx: int`; `world: WorldSpec`; `chain: ChainSpec`; `network: NetworkSpec`; `adversary: AdversarySpec`; `export: ExportSpec`; `validation: ValidationSpec`; `evaluation: EvalSpec`; `types: tuple[TypeSpec, ...]`; `effective: Mapping[str, Any]`.
- `def _type_spec(name: str, node: Mapping[str, Any], reuse_fallback: float) -> TypeSpec:` — Internal helper; behavior is defined by the source implementation.
- `def _world(node: Mapping[str, Any]) -> WorldSpec:` — Internal helper; behavior is defined by the source implementation.
- `def _network(node: Mapping[str, Any], anchor: Path) -> NetworkSpec:` — `anchor` is the directory holding run_config.json, so `latency_matrix` resolves beside the config that named it rather than against whatever the working directory happens to be.
- `def _adversary(node: Mapping[str, Any]) -> AdversarySpec:` — Internal helper; behavior is defined by the source implementation.
- `def _chain(node: Mapping[str, Any]) -> ChainSpec:` — Internal helper; behavior is defined by the source implementation.
- `def _eval(node: Mapping[str, Any]) -> EvalSpec:` — Internal helper; behavior is defined by the source implementation.
- `def _coerce(current: object, path: str, text: str) -> object:` — Parse `text` into the type the leaf already holds. The existing value is the schema.
- `def _apply_overrides(root: dict[str, Any], overrides: Mapping[str, str]) -> None:` — Fold dotted `key=value` overrides into the parsed config in place, before any check runs.
- `def _resolve_regime(root: dict[str, Any]) -> None:` — Expand the selected observer regime into the three leaves the rest of the loader reads.
- `def load(path: Path, *, seed: int | None=None, n_txs: int | None=None, n_entities: int | None=None, anchor: Path | None=None, overrides: Mapping[str, str] | None=None) -> Config:` — Parse `path`, apply the CLI overrides, and check the config is self-consistent.
- `def _check(chain: ChainSpec, types: tuple[TypeSpec, ...], network: NetworkSpec, adversary: AdversarySpec) -> None:` — Reject a config that cannot describe a world, rather than generating a wrong one.

#### `src/chakravyuh/mayajaal/entities.py`

MAYAJAAL-SPEC Layer 1: the entity population, its wallets and its activity schedules.

A population, not a list of addresses. Every entity carries the wallet policy and the online
schedule its type implies, and the awkward cases downstream stages have to cope with — a
hot wallet reused thousands of times, a single-address mule, two entities behind one CGNAT
address — fall out of those policies rather than being injected afterwards.

Nothing here is random without a caller-supplied `random.Random`. Nothing here reads a clock.

Identifiers are synthetic by construction, because an invented identifier that happens to be
real is a forensics tool leaking someone's data:

  addresses   carry "gen0i" in the body. "i" is absent from the bech32 charset and "0" is
              absent from the base58 alphabet, so a bech32-shaped result can never decode
              and a base58-shaped result can never checksum.
  IPv4        198.18.0.0/15, the RFC 2544 benchmarking range, and 100.64.0.0/10, the
              RFC 6598 CGNAT range. Neither is globally routable.
  IPv6        2001:db8::/32, the RFC 3849 documentation prefix.

Each pool is cut into one contiguous block per region, so an address determines the region it
belongs to and therefore its country and ASN. That matters downstream: S04 enriches geo from
the IP, and if the mapping were not a function of the address it could never agree with the
capture's own `geo_country` column. `region_of` is that function, and it is the inverse the
test asserts against.

- `def hour_of(time_us: int) -> int:` — UTC hour of day for a microsecond timestamp. No datetime, so no clock and no locale.
- Class `AddressFactory` — Mints unique, structurally invalid addresses. The counter is the uniqueness proof.
  Fields: `kinds: WeightedIndex[str]`; `minted: int = 0`.
- Class `Entity` — One actor. `addresses` and `address_kinds` stay parallel and grow as the run proceeds.
  Fields: `entity_id: str`; `entity_type: str`; `is_illicit: bool`; `reuse_rate: float`; `change_policy: str`; `ips: tuple[str, ...]`; `behind_cgnat: bool`; `active_start: int`; `active_len: int`; `region: int`; `addresses: list[str] = field(default_factory=list)`; `address_kinds: list[str] = field(default_factory=list)`; `payout: tuple[str, str] | None = None`; `typologies: list[str] = field(default_factory=list)`.
- Class `Population` — The world, plus the sampling tables the transaction loop needs on its hot path.
  Fields: `entities: tuple[Entity, ...]`; `senders_by_hour: tuple[WeightedIndex[int], ...]`; `receivers: WeightedIndex[int]`; `pools: tuple[int, ...]`; `hashrate: WeightedIndex[int]`; `factory: AddressFactory`; `regions: Regions`; `exchanges: tuple[int, ...]`; `illicit: tuple[int, ...]`.
- `@functools.cache` — Internal helper; behavior is defined by the source implementation.
- `def _ip(rng: random.Random, pool: tuple[int, int, int], region: int, n_regions: int) -> str:` — One address from `region`'s contiguous slice of `pool`. See `region_of` for the inverse.
- `def pool_ip(rng: random.Random, cidr: str, region: int, n_regions: int) -> str:` — One address from `region`'s slice of `cidr`, for a caller that has only the CIDR string.
- `def _shared_ip(rng: random.Random, pool: tuple[int, int, int], region: int, n_regions: int, cap: int) -> str:` — A CGNAT address drawn from a deliberately small per-region set.
- `def region_of(ip: str, cidrs: tuple[str, ...], n_regions: int) -> int | None:` — Which region's slice `ip` falls in, or None if it is outside every pool.
- `def _cgnat_share(cfg: Config, type_name: str) -> float:` — MAYAJAAL-SPEC gives a CGNAT share for exactly these two types. Everyone else is 0.
- `def _counts(cfg: Config) -> dict[str, int]:` — Entities per type, rounded, with the rounding drift given to the largest share.
- `def _one(cfg: Config, spec: TypeSpec, index: int, rng: random.Random, region: int, n_regions: int) -> Entity:` — Internal helper; behavior is defined by the source implementation.
- `def build(cfg: Config, rng: random.Random) -> Population:` — Build the population and every sampling table over it. Deterministic given `rng`.

#### `src/chakravyuh/mayajaal/export.py`

MAYAJAAL-SPEC Layer 5: the capture, in the three shapes a real one arrives in.

Section 1 of `docs/DATA-CONTRACTS.md` is the only schema in this project we did not choose, so
this module implements it and nothing else. One row is one announcement of one transaction by
one peer, the chain columns repeat across every row announcing the same txid, and the eighteen
column names here are exactly section 1's names in section 1's order.

Three directories, because a file from NTRO could be any of them and a stage that has only ever
seen our CSV will break on the day it is handed XML:

  capture/       CSV shards of `export.shard_rows` rows. Lists are pipe separated, a null is
                 the empty field.
  capture_json/  the same rows as JSONL. Lists stay lists and a null stays null, so this is the
                 encoding that loses nothing.
  capture_xml/   a small sample, `export.xml_sample_rows` rows, because the format is verbose
                 and its purpose is to prove the reader handles it, not to carry the run.

Nothing here writes to disk. Every part is built in memory and handed to `writers.py`, which is
the one module in the stage that opens a file, and which hashes the bytes it is given before
writing them. Nothing here reads a clock: a row's timestamp comes from the run's own microsecond
clock, and the epoch it is measured from is `chain.genesis_us`.

No column in this file is a ground-truth column. The answer key knows which peer of the many
announcing a transaction was the one that created it; a capture row cannot, or the whole problem
would be a lookup.

- `def _stamp(time_us: int) -> str:` — ISO 8601 with exactly six fractional digits and an explicit `+00:00`.
- Class `Part` — One file of one export directory: where it goes, its bytes, and the rows it carries.
  Fields: `directory: str`; `name: str`; `text: str`; `rows: int`.
- `def _cell(value: object) -> str:` — One CSV field. A list becomes pipe separated, a null becomes the empty field.
- `def rows(cfg: Config, run: Run, net: Network, start: int, stop: int) -> Iterator[dict[str, object]]:` — Announcements `start` up to `stop`, expanded into section 1's columns.
- `def _csv(batch: Iterator[dict[str, object]]) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _jsonl(batch: Iterator[dict[str, object]]) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _xml(batch: Iterator[dict[str, object]], seed: int) -> tuple[str, int]:` — The sample as XML, and how many rows it holds.
- `def _spans(total: int, size: int) -> list[tuple[int, int]]:` — Contiguous row ranges of at most `size` rows, and one empty range for an empty capture.
- `def parts(cfg: Config, run: Run, net: Network) -> Iterator[Part]:` — Every file of every export directory, one at a time.
- `def offered(net: Network) -> int:` — Announcements handed to the exporter, which is `counts.in` for every export directory.

#### `src/chakravyuh/mayajaal/ledger.py`

The UTXO ledger: `(txid, vout) -> (address, sats, height)`, plus the block clock.

MAYAJAAL-SPEC Layer 2 asks for an actual ledger rather than a random graph with amounts
sprinkled on it, because half the cases the detectors need only exist in the accounting:
change outputs, multi-input spends, consolidation, dust. Value conservation is enforced by
the caller building transactions; this module enforces that a coin cannot be spent twice and
cannot be spent before it exists.

Two rules hold everywhere in here. All money is `int` satoshis, never a float. Nothing
iterates a `set`: the spendable index is a dict used as an ordered set, because set iteration
order depends on PYTHONHASHSEED and would make the same seed produce different bytes in a
different process.

- `def txid_for(inputs: Sequence[Outpoint], outputs: Sequence[tuple[str, str, int]], *, nonce: str='') -> str:` — The transaction id, a SHA-256 over this transaction's own serialised contents.
- Class `Utxo` — One unspent output. `owner` and `kind` are ledger bookkeeping, never observable output.
  Fields: `address: str`; `kind: str`; `sats: int`; `height: int`; `owner: int`; `coinbase: bool`.
- Class `Ledger` — The live UTXO set, with a per-owner index so coin selection is not a full-set scan.
  Fields: `maturity_blocks: int`; `utxos: dict[Outpoint, Utxo] = field(default_factory=dict)`; `by_owner: dict[int, dict[Outpoint, None]] = field(default_factory=dict)`.
- `def block_times(rng: random.Random, genesis_us: int, interval_s: float, n: int) -> list[int]:` — `n` block timestamps in microseconds, exponential inter-arrival with mean `interval_s`.

#### `src/chakravyuh/mayajaal/network.py`

MAYAJAAL-SPEC Layer 3: the peer network, and the only part of a run an observer can see.

The capture is not the run. A transaction is created by an entity, broadcast by whichever node
that entity happens to use, and then relayed hop by hop with an independent delay on every
link. Our observers are a handful of listening nodes, and a row exists only when a node that
dialled one of them announced a transaction to it before learning of that transaction from
somebody else. Everything else that happened on the network is unobserved, which is the whole
difficulty of the problem: the first announcement an observer receives is usually not the
originator's.

Three mechanisms make that true, and all three are physical rather than cosmetic.

  independent delays   A node does not forward on receipt. For every peer and every
                       transaction it draws a fresh delay, mean two seconds toward a peer it
                       dialled and five toward a peer that dialled it. The order in which
                       observers hear about a transaction is therefore not the order of the
                       hops that carried it, and there is no cascade to sort.
  first only           An observer records the announcement that told it something new. After
                       that it holds the transaction, so the rest are duplicates, and the
                       peers it has told stop announcing. One row per observer per transaction
                       is the whole of what a listening node learns, and how much of the
                       network it watches decides how often that one row names the originator
                       rather than how many rows there are.
  shared nodes         There are fewer nodes than entities, so an entity without a node of
                       its own broadcasts through one it shares. The IP in the capture belongs
                       to the node; the wallet behind it may well be someone else.

Nothing here reads a clock or a file. Every draw comes from the caller's generator.

- `def origin_l1(node: Node, owner: entities.Entity | None, regions: Regions, tor_asn: int, vpn_asn: int) -> tuple[int, str, str, str]:` — The true operator-level attribution for one origin node: (asn, as_org, net_class, country).
- `def observer_id(index: int) -> str:` — Stable name for one listening node, written to the capture's `observer_id` column.
- `def _bucket(ip: str) -> str:` — The address group a peer belongs to: its /16 for IPv4, its /32 for IPv6.
- Class `Node` — One network peer. `owner` is the entity whose IP this is, and None for infrastructure.
  Fields: `ip: str`; `region: int`; `port: int`; `asn: int | None`; `country: str | None`; `owner: int | None`; `kind: str`.
- Class `Origin` — Truth for one transaction: where it entered the network, which no observer sees.
  Fields: `tx_index: int`; `node: int`; `entity: int`; `broadcast_us: int`; `used_tor: bool`; `used_vpn: bool`; `observed_by_n: int`.
- Class `Capture` — Every recorded announcement, in column form and ascending by time.
  Fields: `tx_index: list[int] = field(default_factory=list)`; `src_node: list[int] = field(default_factory=list)`; `observer: list[int] = field(default_factory=list)`; `time_us: list[int] = field(default_factory=list)`; `is_inv: list[bool] = field(default_factory=list)`.
- Class `Topology` — The graph. `outbound` is who a node dialled, `inbound` is who dialled it.
  Fields: `nodes: tuple[Node, ...]`; `observers: tuple[Node, ...]`; `outbound: tuple[tuple[int, ...], ...]`; `inbound: tuple[tuple[int, ...], ...]`; `watched: tuple[int, ...]`; `home: tuple[int, ...]`; `tor_exits: tuple[int, ...]`; `vpn_nodes: tuple[int, ...]`.
- Class `Network` — What layer 3 produced: the graph, the answer key, and the observable rows.
  Fields: `topology: Topology`; `origins: tuple[Origin, ...]`; `capture: Capture`.
- `def _owners(cfg: Config, pop: Population, rng: random.Random, n_nodes: int) -> list[int]:` — Which entities run a reachable node, weighted by how much traffic they originate.
- `def _node(cfg: Config, table: Regions, rng: random.Random, *, ip: str, region: int, kind: str, owner: int | None, asn: int) -> Node:` — Internal helper; behavior is defined by the source implementation.
- `def _peers(cfg: Config, nodes: list[Node], table: Regions, rng: random.Random) -> list[list[int]]:` — Outbound peers per node: latency-weighted, address-bucket-penalised, inbound-capped.
- `def _place_observers(cfg: Config, outbound: list[list[int]], rng: random.Random) -> list[int]:` — Which nodes a listening observer dialled, and which observer each one dialled.
- `def _topology(cfg: Config, pop: Population, rng: random.Random) -> Topology:` — Build the node set, wire it up, and decide which links we get to watch.
- `def _broadcast(cfg: Config, run: Run, rng: random.Random) -> list[int]:` — When each transaction was first sent, which is before the block that confirmed it.
- `def _flood(topo: Topology, cfg: Config, table: Regions, rng: random.Random, origin: int, start_us: int) -> tuple[list[int], dict[int, int]]:` — Relay the transaction outward, returning the earliest arrival at each node reached.
- `def _announce(topo: Topology, cfg: Config, table: Regions, rng: random.Random, order: list[int], learn: dict[int, int], deadline: int) -> list[tuple[int, int, int]]:` — What each observer recorded for this transaction, as (observer, node, arrival).
- `def build(cfg: Config, run: Run, rng: random.Random) -> Network:` — Propagate every transaction and record what the observers received. Deterministic.
- `def _sort(capture: Capture) -> None:` — Put the rows in the order a packet capture would have them: ascending by arrival.

#### `src/chakravyuh/mayajaal/preflight.py`

The pre-write guard: refuse to write a run over the bytes of a different run.

`writers.py` cannot do this itself. It is the one file allowed to name the quarantine
directory, and it pays for that permission with a test proving it never opens a file except
to write, so it cannot compare what is already on disk. This module can, and it stays
outside the quarantine by never naming it: both directories arrive as arguments.

The only file this module ever opens is one named `_meta.json`. Law 2 rule 5 forbids a
manifest from carrying a label, which makes a manifest the one file in either tree that a
non-quarantined module can safely look at.

- Class `Slot` — One directory a run owns, and the manifest that says which run wrote it.
  Fields: `directory: Path`; `manifest: Path`.
- `def _recorded_hash(manifest: Path) -> str | None:` — The config hash a previous run left behind, or None if there is nothing to trust.
- `def refuse_to_clobber(slots: Sequence[Slot], *, config_sha256: str) -> None:` — Raise unless every directory that already exists was written by this same config.

#### `src/chakravyuh/mayajaal/regions.py`

Read `regions.yaml`: the region table and the region-to-region latency matrix.

Deliberately a strict parser for a small subset of YAML rather than PyYAML. PyYAML is not
installed and pypi is unreachable in the build sandbox, so a dependency here would make the
whole stage unbuildable. The subset is a section header at column zero and one two-space
indented `key: {inline flow mapping}` entry per line, which is valid YAML, so nothing stops
a real parser reading the same file later.

Latency is stored in microseconds, because every other time in this pipeline is integer
microseconds and converting at the boundary once is cheaper than converting at every use.

- `def _scalar(text: str, where: str) -> int | float | str:` — Ints stay ints. A float that happens to be whole is not silently narrowed.
- `def _flow(text: str, where: str) -> dict[str, int | float | str]:` — Internal helper; behavior is defined by the source implementation.
- `def parse(text: str) -> dict[str, dict[str, dict[str, int | float | str]]]:` — Sections of two-space-indented entries. Comments must occupy a whole line.
- Class `Regions` — The region table, indexed by position. Index, not name, is what the hot loops carry.
  Fields: `names: tuple[str, ...]`; `shares: tuple[float, ...]`; `countries: tuple[str, ...]`; `asns: tuple[int, ...]`; `orgs: tuple[str, ...]`; `jitter_us: tuple[int, ...]`; `latency_us: tuple[tuple[int, ...], ...]`.
- `def _number(node: dict[str, int | float | str], key: str, where: str) -> float:` — Internal helper; behavior is defined by the source implementation.
- `def load(path: Path) -> Regions:` — Parse and validate. Every check here is a typo this file is easy to make.

#### `src/chakravyuh/mayajaal/weighted.py`

Weighted sampling with the cumulative table built once.

`random.Random.choices` rebuilds a cumulative-weight list on every call, which is O(n) per
draw. Entity selection happens once per transaction over twenty thousand candidates, so that
is the difference between a run that finishes and one that does not. The draw itself is one
`random()` call, which keeps the stream position per draw fixed and therefore keeps the run
reproducible from the seed alone.

- Class `WeightedIndex` — Source-defined class.
  Fields: `items: tuple[T, ...]`; `cumulative: tuple[float, ...]`.
- `def build(pairs: Iterable[tuple[T, float]]) -> WeightedIndex[T]:` — Zero and negative weights are dropped; an empty or all-zero input is a caller error.

#### `src/chakravyuh/mayajaal/writers.py`

The only module that writes. The only module allowed to name `ground_truth/`.

`tests/test_contracts.py` greps every file under `src/` for that path and exempts exactly one:
this file. The exemption is paid for by a second assertion, that this module never opens a file
for reading in any form — no dataframe loader, no text or byte load, no directory listing, and
no file handle that was not opened with an explicit write mode. The door opens outwards only,
which is what makes a one-file exemption safe rather than a loophole.

That has two visible consequences. Section 10 wants a sha256 of every output, and the obvious
way to get one is to write the file and hash it back. This module cannot do that, so every
frame is serialised into a buffer, the buffer is hashed, and the buffer is written. The hash
covers the bytes that went to disk because they are the same bytes. The second consequence is
that the guard against overwriting a different run lives in `preflight.py`: deciding that
question means looking at a manifest already on disk, which this module is not allowed to do.

Which columns are observable and which are truth is decided here, in the frame builders, and
nowhere else. `chain/` deliberately reuses the column names section 1 gives the capture rows,
so S02 fans a transaction out into announcements without renaming anything.

- `def _repo_root() -> Path:` — The directory holding `pyproject.toml`, found by walking up from this file.
- Class `Written` — Source-defined class.
  Fields: `path: str`; `sha256: str`; `rows: int`; `skipped: bool = False`.
- Class `Roots` — The three directories one run id owns. Siblings, never nested.
  Fields: `run_id: str`; `observable: Path`; `truth: Path`; `measurements: Path`.
- `def run_roots(out: Path) -> Roots:` — Validate `--out` and derive the two siblings it implies. Raises before anything is written.
- `def _put(payload: bytes, base: Path, rel: str, rows: int) -> Written:` — Write `payload` and record its path relative to its own tree, never absolutely.
- `def _emit(frame: pl.DataFrame, base: Path, rel: str, schema: dict[str, pl.DataType]) -> Written:` — Serialise, hash the buffer, write the buffer. The schema is checked, never inferred.
- `def _emit_text(text: str, base: Path, rel: str) -> Written:` — Internal helper; behavior is defined by the source implementation.
- `def _transactions(run: Run) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def _seeds(run: Run) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def _blocks(run: Run) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def _entities(run: Run) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def _campaigns(run: Run, records: Sequence[Campaign]) -> pl.DataFrame:` — One row per campaign that built something, in campaign id order.
- `def _origins(cfg: Config, run: Run, net: Network) -> pl.DataFrame:` — Exactly one row per announced transaction: who really sent it, and from which node.
- `def _chain_txs(run: Run) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def _entry(written: Written) -> dict[str, object]:` — Internal helper; behavior is defined by the source implementation.
- `def _write_capture(cfg: Config, run: Run, net: Network, roots: Roots, *, consumed: Written, started_at_us: int, finished_at_us: int, config_sha256: str) -> None:` — Write every export directory and give each one its own section 10 manifest.
- `def write_run(run: Run, cfg: Config, out: Path, *, started_at_us: int, finished_at_us: int, net: Network | None=None, campaigns: Sequence[Campaign]=()) -> Path:` — Write every artifact of one run and return the path of its observable manifest.

#### `src/chakravyuh/pramaan/__main__.py`

`python -m chakravyuh.pramaan --in data/generated/<run> --out data/generated/<run>`.

Read-only over the run, writes only `packets/` inside it, signs with the key pair in
`keys/` (gitignored). The Merkle head goes to stdout; everything else goes to stderr.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/pramaan/documents.py`

The two rendered documents: `packet.pdf` and `notice.pdf`.

`packet.pdf` is the case file an analyst reads. `notice.pdf` is a production requisition
under section 94 of the Bharatiya Nagarik Suraksha Sanhita, 2023, addressed to the entity
that operates the infrastructure the attribution points at, listing the records requested.
The statutory grounding is the one the project claims: disclosure of the hash value is
required by section 63(4) of the Bharatiya Sakshya Adhiniyam, 2023, read with Schedule
Part A, and the packet discloses it — which is the whole point of the hash chain.

Both are document typography — serif body, generous margins, no UI furniture — and both
truncate every identifier through `vaani.redact` before a character reaches a page. A
complete address, IP or txid on a page is a leak, not evidence.

- `def _redact_ip(ip: str) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _redact_txid(txid: str) -> str:` — Internal helper; behavior is defined by the source implementation.
- Class `_Cursor` — A y-coordinate walking down one page. Adds a page when the block runs out.
- `def packet_pdf(packet: dict[str, Any]) -> bytes:` — The evidence packet as a document: the case, the custody, the doubts.
- `def notice_pdf(packet: dict[str, Any]) -> bytes:` — A section 94 production requisition, pre-filled from the packet.
- `def _utc_iso(generated_at_us: int) -> str:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/pramaan/ed25519.py`

Ed25519 signing and verification, pure Python, RFC 8032.

No crypto library exists in the pinned environment and none can be added (uv cannot
re-resolve; see STATE.md open problem 3), so this implements RFC 8032 directly over
`hashlib.sha512` and arithmetic mod 2**255-19. Signing is deterministic per the RFC —
the nonce is derived from the message and the key, never from a random draw — so the
same key over the same bytes produces the same signature, which is what the replay
gate leans on.

This is deliberately the only cryptography in the package and it is slow: roughly a
second per operation. Fine for signing one packet per case, which is the only path the
stage exercises; `--all` exists for the same scale.

A private key never appears in a log line or an exception message: the two functions
that read one take raw bytes and raise with paths only.

- `def _recover_x(y: int, sign: int) -> int:` — The x on curve25519 with the given y and x parity. Raises when y is not on the curve.
- `def _point_add(p: Point, q: Point) -> Point:` — Addition on the twisted Edwards curve -x^2 + y^2 = 1 + d x^2 y^2, affine.
- `def _point_mul(scalar: int, point: Point) -> Point:` — Double-and-add scalar multiplication, affine. The identity is (0, 1).
- `def _compress(point: Point) -> bytes:` — A point to its 32-byte RFC 8032 encoding: little-endian y, x parity in bit 255.
- `def _decompress(data: bytes) -> Point:` — The inverse of `_compress`. Raises on a point not on the curve, which is how a corrupted public key fails verification rather than passing it.
- `def _sha512_int(*chunks: bytes) -> int:` — Internal helper; behavior is defined by the source implementation.
- `def _scalar(seed: bytes) -> int:` — The signing scalar: the low half of SHA-512(seed), clamped per RFC 8032 5.1.5.
- `def generate_seed() -> bytes:` — 32 random bytes from the OS CSPRNG. The only randomness anywhere in this package.
- `def public_key(seed: bytes) -> bytes:` — The 32-byte public key for a 32-byte seed, per RFC 8032 section 5.1.5.
- `def sign(seed: bytes, message: bytes) -> bytes:` — Sign `message` with the key pair derived from `seed`. Deterministic, 64 bytes out.
- `def verify(public: bytes, message: bytes, signature: bytes) -> bool:` — RFC 8032 verification. Returns False on any malformed input, never raises on it.

#### `src/chakravyuh/pramaan/merkle.py`

The append-only hash chain across packets.

One line per generated packet: `index  leaf  prev_root`. The leaf is the SHA-256 of the
packet's canonical serialisation; the root after line n chains every leaf before it, so
removing, replacing or reordering any line breaks the recomputed chain from that point
on — which is what "append-only" is checkable to mean.

The log lives at `packets/merkle.log` and is shared by every case in the run. Regenerating
a case appends a duplicate leaf rather than rewriting the line it would have produced,
because rewriting history is the one thing this file must never survive.

- `def canonical(payload: dict[str, object]) -> bytes:` — The canonical serialisation a hash or signature is computed over.
- `def leaf(packet_bytes: bytes) -> str:` — The log's leaf for one packet: the SHA-256 of its canonical serialisation.
- `def root_of(leaves: list[str]) -> str:` — The Merkle root over the leaves so far, duplicated-padded to a power of two.
- `def append(log_path: Path, packet_bytes: bytes) -> str:` — Append one leaf and return the new head. Prints nothing; the caller owns stdout.
- `def read(log_path: Path) -> tuple[list[str], list[str]]:` — Parse the log into (leaves, prev_roots). Raises on a malformed line, because a log that cannot be parsed is a log someone edited by hand.
- `def verify(log_path: Path) -> tuple[bool, str]:` — Recompute the chain. Returns (ok, head). A log that fails here was rewritten.

#### `src/chakravyuh/pramaan/packet.py`

The packet builder: one alert becomes one signed, replayable evidence packet.

Every value is read from the run's observable directories or derived from them. The one
field that would break that rule is `generated_at_us`: a wall clock would make the packet
a different byte-string on every replay, so it is derived from `alerts/_meta.json`'s
`finished_at_us` instead — the time the pipeline, not the operator, stamped.

`replay.expected_packet_sha256` is the SHA-256 of the canonical serialisation with that
field blanked, so a second analyst can verify it without solving a self-reference: blank
the field, re-serialize, hash, compare. `verify-replay` does exactly that, byte-exact.

The packet never names either quarantined sibling tree, and no evaluation figure appears
in it: the only numbers are case-local (probabilities, the interval, row counts) and
hashes. A benchmark accuracy presented as a property of the evidence is the one claim an
evaluator could call misleading, so the packet carries no accuracy at all.

- Class `CaseError` — The case id does not name an alert, or names an alert that cannot be packed.
- `def resolve_case(alert_id: str, alerts_dir: Path) -> str:` — Reject a case id that is not an alert id in this run. A path separator here would let `--case` point outside `packets/`, so the id must match exactly.
- `def _redact_subject(subject_id: str) -> str:` — `addr:<hex>` and `cluster:<n>` render through the truncation law like addresses.
- `def _meta_entries(run_dir: Path) -> list[dict[str, Any]]:` — One custody link per stage directory, ordered: the stage, its meta hash, in/out.
- `def _input_files(run_dir: Path) -> tuple[list[dict[str, str]], int]:` — The sealed input hashes and the sealed row count, from KAVACH's own manifest.
- `def build(run_dir: Path, alert_id: str, seed: int, replay_command: str) -> dict[str, Any]:` — Assemble the contract section 9 packet for one alert as a plain dict.
- `def _utc(seen_us: int) -> str:` — Microseconds since epoch as an ISO-8601 UTC string. Pure arithmetic, no clock.
- `def _l1_attribution(run_dir: Path, txid: str) -> dict[str, Any]:` — The L1 operator headline for the origin transaction, from `origin_l1.parquet`.
- `def _shortlist(run_dir: Path, txid: str) -> list[dict[str, Any]]:` — The ranked L3 candidate peers for the origin transaction, redacted for display.
- `def _method(run_dir: Path, model: str) -> str:` — The calibration method recorded for this run, from `scores/calibration.parquet`.
- `def verify_replay_field(packet: dict[str, Any]) -> bool:` — Blank the recorded digest, re-serialize, hash. True when the claim recomputes.
- `def packet_bytes(packet: dict[str, Any]) -> bytes:` — The exact bytes written to `packet.json`: canonical, key-sorted, one line.

#### `src/chakravyuh/pramaan/pdflib.py`

A minimal deterministic PDF 1.4 writer. No dependency exists for this and none can be
added (STATE.md open problem 3), so this builds the objects by hand.

Scope, deliberately narrow: A4 pages, the four built-in base fonts (nothing embedded,
nothing fetched), text placed at coordinates, hairline rules, and word wrapping from the
AFM advance widths below. That is exactly what `documents.py` needs and nothing more.

Determinism: the byte stream is a pure function of the calls — no CreationDate, no
Producer, no compression — so the same document always renders to the same bytes, which
the replay gate hashes.

Uncompressed streams are also the point, not a shortcut: the identifier test greps the
PDF bytes for complete-identifier patterns, which only works if the text sits in the
stream as literal characters.

`ponytail:` the width tables are the standard AFM values transcribed for chars 32-126
only, and the bold faces are measured with their regular counterpart's widths — a wrap
point may shift by a character or two against Acrobat's own layout. Documents here wrap
on whole words with a wide margin, so the ceiling is cosmetic, not structural.

- `def text_width(text: str, font: str, size: float) -> float:` — Advance width of `text` in points, using the font's AFM table.
- `def wrap(text: str, font: str, size: float, width: float) -> list[str]:` — Word-wrap `text` to `width` points. Explicit newlines are honoured. A single word wider than the line is not split: it overflows, and the caller chose the margin.
- `def _pdf_string(text: str) -> str:` — A PDF literal string, cp1252-encoded per WinAnsiEncoding. `…` lands on 0x85.
- Class `_Page` — One page's content operators. Coordinates are from the top-left margin.
- Class `Document` — A PDF of A4 pages. `render` returns the bytes; render twice, get the same bytes.

#### `src/chakravyuh/pramaan/stage.py`

PRAMAAN as a stage: read the run, write `packets/<case_id>/`, append the Merkle log.

The path guards are VAANI's, restated rather than imported: `--in` and `--out` resolve
under `data/generated/` only, so no invocation can point the stage at a sibling tree.

The signing key lives in `keys/` at the repository root, which `.gitignore` already
excludes. `--generate-keys` creates the pair when absent; the seed never crosses a log
line, an exception message, or the packet — only the signature ever proves it was used.

- `def resolve_in(target: Path) -> Path:` — The run directory holding the upstream stages' outputs and `_meta.json` files.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `packets/` into.
- `def _repo_relative(path: Path) -> str:` — Internal helper; behavior is defined by the source implementation.
- Class `KeyMaterial` — The signing seed and the public key, loaded once. The seed never leaves this object except to `sign`; it is never formatted into a string.
- `def load_or_create_keys(repo_root: Path) -> KeyMaterial:` — Load `keys/<seed file>`, or generate the pair on first use. Gitignored, local.
- `def build_run(run_dir: Path, out: Path, case: str | None, keys: KeyMaterial, repo_root: Path) -> list[Path]:` — Generate packets for one case, or for every alert when `case` is None.
- `def _write_case_log_copy(log_path: Path, target: Path) -> None:` — The case-local snapshot of the log, as section 9's directory listing describes.
- `def verify_signature(case_dir: Path, keys_dir: Path) -> bool:` — Verify one case's `packet.sig` over its `packet.json` with the public key on disk.
- `def verify_replay(run_dir: Path, out: Path, case: str, repo_root: Path) -> bool:` — Rebuild the packet from the run and compare, byte for byte.
- `def _seed(run_dir: Path) -> int:` — The run's seed, from `config.effective.json`; 0 when the run records none.
- `def _write_meta(out: Path, packets_dir: Path, log_path: Path, n_cases: int, seed: int) -> None:` — `packets/_meta.json` per contract section 10.
- `def git_root() -> Path:` — The repository root, for `keys/`. git's own answer, else the package's parents.

#### `src/chakravyuh/setu/__main__.py`

`python -m chakravyuh.setu --in data/generated/<run>/sealed --out data/generated/<run>`.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/setu/enrich.py`

Geo, ASN and network class for a peer IP, from files in `vendor/` and nothing else.

Two things shape this module.

There is no MaxMind reader in the pinned dependencies and this sandbox cannot resolve a new
one, so the `.mmdb` binary format is not read. What is read is MaxMind's **CSV** distribution,
which carries the same data and needs only the standard library. An `.mmdb` with no CSV beside
it is recorded as a warning and enriches nothing, because a half-built binary parser would be a
worse answer than an honest null.

The lookup is per **distinct IP**, not per announcement. A capture of a million announcements
holds a few thousand peers, so a sorted list and `bisect` beat any dataframe interval join here
by enough that the join is not worth writing. `ipaddress` gives arbitrary-precision integers,
which is what makes one code path serve both IPv4 and IPv6.

- Class `PeerFacts` — What `vendor/` can say about one IP. Every field is null when it cannot say.
  Fields: `geo_country: str | None = None`; `asn: int | None = None`; `as_org: str | None = None`; `net_class: str | None = None`.
- Class `_Ranges` — Non-overlapping address ranges, sorted by their low end, split by IP version.
  Fields: `los: dict[int, list[int]]`; `his: dict[int, list[int]]`; `values: dict[int, list[tuple[object, object]]]`.
- `def _empty_ranges() -> _Ranges:` — Internal helper; behavior is defined by the source implementation.
- `def _build_ranges(rows: list[tuple[str, tuple[object, object]]]) -> _Ranges:` — Turn `(cidr, value)` pairs into version-split sorted range tables.
- `def _find_files(root: Path, names: tuple[str, ...] | str) -> list[Path]:` — Every file under `vendor/` with one of these names, in a stable order.
- `def _read_csv(path: Path) -> list[dict[str, str]]:` — Internal helper; behavior is defined by the source implementation.
- `def _load_countries(root: Path, warnings: list[str]) -> _Ranges:` — Internal helper; behavior is defined by the source implementation.
- `def _load_asns(root: Path, warnings: list[str]) -> _Ranges:` — Internal helper; behavior is defined by the source implementation.
- `def _load_tor(root: Path) -> frozenset[str]:` — Every IP in a vendored Tor exit list, in normalised form.
- `def _matches(org: str, needles: tuple[str, ...]) -> bool:` — Internal helper; behavior is defined by the source implementation.
- Class `Enricher` — Vendor lookups for one run. Construct once, call `lookup` per distinct IP.

#### `src/chakravyuh/setu/normalise.py`

The grain split, as pure frame-to-frame functions.

One sealed row is one announcement of one transaction by one peer. This module turns that
single table into the four of contract section 4: the announcement grain, the transaction
grain, and the two entity grains derived from them. Nothing here writes a file and nothing here
reads one, which is what lets the tests hand these functions a six-row frame.

Every aggregate is a group-by. A per-transaction loop over announcements is the trap the stage
brief names, and at a million rows it is also the difference between seconds and an afternoon.
Every output is sorted on its primary key before it is returned: group-by output order is not
guaranteed, and the gate compares two runs byte for byte.

- `def _optional(frame: pl.DataFrame, name: str, dtype: pl.DataType) -> pl.Expr:` — The named column, or a typed all-null stand-in when the capture never carried it.
- `def peer_facts(ips: list[str], enricher: Enricher) -> pl.DataFrame:` — One row per distinct peer IP: what `vendor/` says about it.
- `def base_announcements(rows: pl.DataFrame) -> pl.DataFrame:` — The announcement grain, before enrichment. One row in, one row out, always.
- `def peers(base: pl.DataFrame, facts: pl.DataFrame) -> pl.DataFrame:` — One row per distinct peer IP, per contract section 4.
- `def announcements(base: pl.DataFrame, peer_table: pl.DataFrame) -> pl.DataFrame:` — The announcement grain with per-peer facts attached. Row count is preserved exactly.
- `def asn_rollup(peer_table: pl.DataFrame, announcement_table: pl.DataFrame) -> pl.DataFrame:` — One row per observed ASN, the substrate L1 attribution scores against.
- `def arrival(rows: pl.DataFrame) -> pl.DataFrame:` — The per-transaction arrival matrix as a tidy long table: one row per announcement.
- `def _change_index(txs: pl.DataFrame) -> pl.DataFrame:` — `txid` to the suspected change output index, or -1.
- `def transactions(rows: pl.DataFrame) -> pl.DataFrame:` — The transaction grain, one row per distinct txid.
- `def _sides(txs: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:` — Every (address, amount, time) an address was spent at, and every one it was paid at.
- `def _dwell(spent: pl.DataFrame, received: pl.DataFrame) -> pl.DataFrame:` — Median microseconds an address held value before spending it, within this capture.
- `def declared_script_types(rows: pl.DataFrame) -> pl.DataFrame:` — Address to the script type the capture declared for it, from the optional column.
- `def addresses(txs: pl.DataFrame, declared: pl.DataFrame) -> pl.DataFrame:` — One row per distinct address, per contract section 4.

#### `src/chakravyuh/setu/schema.py`

The four `normalised/` schemas, in contract section 4's column order.

Column order is part of the contract, not a stylistic choice: a parallel frontend track reads
these files and `contract-auditor` compares the order on disk against the document. Declaring
each schema as an ordered mapping and building every frame through it is what keeps the two in
step without anyone remembering to.

- Class `SealedInputError` — A `sealed/` directory SETU cannot normalise, named rather than guessed at.
- `def conform(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:` — Select the schema's columns in its order and cast each to its declared type.

#### `src/chakravyuh/setu/stage.py`

SETU as a stage: read `sealed/`, write `normalised/`, account for every row.

The path guards are KAVACH's, restated rather than imported. No stage imports another stage's
internals, and the rule pays for itself here: `--in` is allowlisted to `data/`, so a SETU
invocation cannot be pointed at the answer key even by an operator who wants to, because the
answer key is a sibling tree and not under `data/`.

- Class `InputPathError` — A path SETU will not read from, or will not write to.
- `def _relative_to_cwd(path: Path, root: str) -> Path:` — `path` resolved, refused unless it sits inside `<cwd>/<root>`.
- `def resolve_in(target: Path) -> Path:` — The `sealed/` directory to normalise.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `normalised/` into.
- `def _repo_relative(path: Path) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _write_parquet(frame: pl.DataFrame, path: Path) -> str:` — Write, then hash what was written. Compression is pinned so two runs agree byte for byte.
- `def _upstream_meta(sealed: Path) -> tuple[str | None, str | None]:` — The staleness link: `sealed/_meta.json` as a repo-relative path and a hash.
- `def normalise_run(sealed: Path, out: Path, vendor: Path | None=None) -> Path:` — Normalise `sealed/` into `<out>/normalised/`. Returns the path to `_meta.json`.

#### `src/chakravyuh/shastra/__main__.py`

`python -m chakravyuh.shastra --in data/generated/<run>/normalised --out data/generated/<run>`.

Labels and scoring live here and nowhere else in the stage. `chakravyuh.eval` is imported by this
file alone, so `stage.py` stays a pure read of two directories under `data/` and the one place the
pipeline touches the eval package is a file that is not itself part of the pipeline.

The run id used to find the answer key is derived from `--in`, not from `--out`. The answer key
belongs to the capture, so an estimator reading `_run/normalised` must train on `_run`'s labels no
matter where its predictions are written. That is also what makes the determinism gate meaningful:
`make verify-s06` runs this twice with one input and two output directories, and a run id taken
from `--out` would silently give the second run no labels and a different answer.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def _labels(run_id: str, train_fraction: float) -> tuple[pl.DataFrame | None, int | None]:` — Open the origin door. Returns the training-window labels and the boundary, or (None, None).
- `def _score(run_id: str, train_fraction: float, observer_fraction: float) -> None:` — Hand the run id to eval and report what comes back. Numbers, never a label.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/shastra/causal.py`

Label-free candidate features with an explicit decision time and strict history cutoff.

Candidates use announcements received within a fixed horizon after first observation. Historical
peer/payer/ASN statistics use only events strictly before that first observation. The monitor
count is an explicit registry/config input, never inferred from the future capture. This module
is opt-in and is not yet the stage's default; saved historical models require their own recipe.

- `def _history_join(query: pl.DataFrame, history: pl.DataFrame, by: list[str], time_name: str) -> pl.DataFrame:` — Internal helper; behavior is defined by the source implementation.
- `def candidates(announcements: pl.DataFrame, peers: pl.DataFrame, transactions: pl.DataFrame, *, n_observers: int, horizon_us: int=5000000, relay_delay_us: float=2000000.0) -> pl.DataFrame:` — One row per (transaction, observed peer), with evidence available by decision_us.

#### `src/chakravyuh/shastra/estimate.py`

The estimators. Two are built: `first_spy` for pass one, `ensemble` for pass two.

Pass one exists to be beaten. It ranks candidates by first-seen time and nothing else, which is
what an investigator gets for free, and its accuracy is recorded before any better model exists so
that every later version has a number to clear rather than a feeling to appeal to.

Pass two is a gradient-boosted model over the observable features, calibrated by isotonic
regression on a slice of the training window that the model never saw, with abstention inside it
rather than bolted on afterwards. Labels arrive already restricted to the training window by
`chakravyuh.eval.labels`; this module takes them as an ordinary frame and has no idea where they
came from, which is the point of the door.

The three honesty rules of contract section 6 are enforced in `_finalise`, once, for every
estimator, so a new estimator cannot forget one:

  p_origin is capped, never renormalised. A transaction whose candidate probabilities sum to 0.31
  keeps 0.31. Only a sum above one is scaled, and only down to one, because the contract's ceiling
  is a ceiling and the shortfall below it is the file saying "probably none of these".
  An abstaining transaction has no rank one row. Ranks are shifted to start at two, which keeps
  the ordering legible without ever letting a refusal look like an accusation.
  Ties break on `row_id`, so two interpreters agree.

- Class `Fit` — What pass two did, so `_meta.json` can record it and a warning can name the fallback.
  Fields: `trained: bool`; `n_train_rows: int`; `n_train_txids: int`; `n_positive: int`; `n_calibration_rows: int`; `calibrated: bool`; `reason: str | None`.
- `def _decay_scores(order: pl.Expr) -> pl.Expr:` — `BASELINE_P1 * BASELINE_DECAY ** position`, `position` zero-based within the transaction.
- `def _finalise(scored: pl.DataFrame, *, estimator: str, margin_floor: float, min_announcements: int) -> pl.DataFrame:` — Rank, cap, measure the margin, decide abstention. The only place those four happen.
- `def _mle_scores(candidates: pl.DataFrame, arrival: pl.DataFrame, mean_us: float) -> pl.DataFrame:` — Per-candidate source log-likelihood from the arrival matrix and the relay-delay mean.
- `def _softmax_with_escape(scored: pl.DataFrame, score: str) -> pl.DataFrame:` — Turn a per-candidate score into `p_origin`, softmax against a per-txid escape mass.
- `def attach_mle(candidates: pl.DataFrame, arrival: pl.DataFrame | None, *, relay_delay_us: float) -> pl.DataFrame:` — Add the `mle_logscore` column every downstream estimator reads, once.
- `def timing_mle(candidates: pl.DataFrame, *, margin_floor: float, min_announcements: int) -> pl.DataFrame:` — Multi-observer maximum-likelihood source estimate. Reads `mle_logscore` from `attach_mle`.
- `def first_spy(candidates: pl.DataFrame, *, margin_floor: float, min_announcements: int) -> pl.DataFrame:` — Pass one. Rank by first-seen time, tie-break on capture position, and nothing else.
- `def _heuristic(candidates: pl.DataFrame) -> pl.DataFrame:` — The fallback ordering when there is nothing to learn from: payer linkage, then first-seen.
- `def _train(train_rows: pl.DataFrame, seed: int) -> tuple[Any, Any, int]:` — Fit the tree on the early part of the training window and the calibrator on the late part.
- `def ensemble(candidates: pl.DataFrame, labels: pl.DataFrame | None, *, boundary_us: int | None, margin_floor: float, min_announcements: int, seed: int) -> tuple[pl.DataFrame, Fit]:` — Pass two. A calibrated probability per candidate peer, with abstention built in.
- `def _top_two(scored: pl.DataFrame, key: str, score: str) -> pl.DataFrame:` — Per-txid rank-1 and rank-2 of `key` by `score`, tie-broken on `key` for determinism.
- `def asn_rollup(estimates: pl.DataFrame, peers: pl.DataFrame, asn_prior: pl.DataFrame, *, margin_floor: float, estimator: str='ensemble') -> pl.DataFrame:` — Lift a per-candidate estimate to the L1/L2 headline: one operator and region per transaction.
- `def to_contract(estimates: pl.DataFrame) -> pl.DataFrame:` — Fold the flat feature columns into the `features` struct contract section 6 asks for.

#### `src/chakravyuh/shastra/features.py`

One row per (txid, candidate peer), with every feature the estimator is allowed to see.

The grain is the peer, not the announcement. "Which peer originated this" is a question about
peers: a peer that reached four observers is one candidate, not four, and leaving the rows
ungrouped would let a well-observed relay outvote the originator by sheer row count. JAAL made the
same choice for `ANNOUNCED_BY` and said so, for this stage's benefit.

Every column here is observable. Nothing is read from a sibling tree and nothing is derived from a
label, which is what lets `stage.py` stay a pure read of two directories under `data/`.

One measured fact shaped this file. On a run at `observer_fraction` 0.7 the mean number of distinct
observers per (txid, peer) is 1.005: an observer records only the announcement that told it
something new, so almost every candidate was heard by exactly one observer and
`n_observers_seen` is a near-constant. The informative half of "how many of our observers saw it
via this peer, and how many saw nothing" is therefore the second half, and `n_observers_blind`
carries it. Both are emitted, because section 6 requires the first, but a model that leaned on
`n_observers_seen` would be leaning on a constant.

- `def peer_degree(edges: pl.DataFrame) -> pl.DataFrame:` — Degree of each peer node in the fused graph, both directions, every edge kind.
- `def payer_links(announcements: pl.DataFrame, transactions: pl.DataFrame) -> pl.DataFrame:` — How many of one payer's transactions each peer announced. The strongest observable rule.
- `def candidates(announcements: pl.DataFrame, peers: pl.DataFrame, transactions: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:` — The feature table. One row per (txid, peer_ip), sorted so the output is order-independent.

#### `src/chakravyuh/shastra/schema.py`

Contract section 6, transcribed. Column order and dtype are the contract, not a suggestion.

Transcribed by hand rather than derived from the frames the stage builds, for the reason every
stage in this repo restates its schema: a schema generated from the code that writes it agrees with
that code by construction and so cannot catch the code drifting from the contract.

`features` is a struct whose field order is fixed here too. Contract section 6 names eight fields
it must hold "at minimum"; those eight come first, in the order the contract lists them, and the
extras the prompt asks for follow. A reader diffing this file against the contract should see the
first eight line up without having to search.

- `def conform(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:` — Select in schema order and cast each column, so the contract decides the layout.
- `def empty(schema: dict[str, pl.DataType]) -> pl.DataFrame:` — A zero-row frame with exactly this schema.

#### `src/chakravyuh/shastra/stage.py`

SHASTRA as a stage: read `normalised/` and `graph/`, write `signals/`, account for every row.

The path guards are JAAL's, restated rather than imported, for the reason that rule exists: `--in`
is allowlisted to `data/`, so a SHASTRA invocation cannot be pointed at the answer key even by an
operator who wants to, because the answer key is a sibling tree and not under `data/`.

This module never imports `chakravyuh.eval`. Labels arrive as an ordinary frame from `__main__.py`,
which is not itself part of the pipeline, so `build_run` is a pure read of two directories under
`data/`. Nothing truth-derived is written: `signals/` carries no truth column and no accuracy
figure, which is what lets the two determinism runs in `make verify-s06` agree byte for byte
whether or not scoring ran.

- Class `InputPathError` — A path SHASTRA will not read from, or will not write to.
- Class `Settings` — The eval knobs this run was generated with, read back from the run rather than the repo.
  Fields: `train_fraction: float`; `margin_floor: float`; `min_announcements: int`; `observer_fraction: float`; `relay_delay_us: float`; `seed: int`; `from_config: bool`.
- `def settings(run_dir: Path) -> Settings:` — The run's eval settings, falling back to the module defaults when it records none.
- `def _relative_to_cwd(path: Path, root: str) -> Path:` — `path` resolved, refused unless it sits inside `<cwd>/<root>`.
- `def resolve_in(target: Path) -> Path:` — The `normalised/` directory to estimate from. Its sibling `graph/` must exist too.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `signals/` into.
- `def _repo_relative(path: Path) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _write_parquet(frame: pl.DataFrame, path: Path) -> str:` — Write, then hash what was written. Compression is pinned so two runs agree byte for byte.
- `def _meta_link(directory: Path) -> tuple[str | None, str | None]:` — Path and hash of a stage directory's `_meta.json`, for the staleness check.
- `def _upstream_geolite2(normalised: Path) -> bool:` — Whether a vendored lookup ran upstream, read back rather than assumed.
- `def build_run(normalised: Path, out: Path, *, labels: pl.DataFrame | None=None, boundary_us: int | None=None) -> Path:` — Build `<out>/signals/` from `normalised/` and its sibling `graph/`. Returns `_meta.json`.

#### `src/chakravyuh/shastra/typology.py`

SHASTRA typology detectors: heuristic laundering-morphology hits over observable transactions.

Each detector is a pure threshold rule on the normalised transaction graph. Nothing here reads a
label or the answer key: a hit is a shape an analyst can point at, computed from the capture alone.
The vocabulary matches MAYAJAAL's own typology names and docs/DATA-CONTRACTS section 2, so a hit
names the same laundering pattern the world can plant — but it is asserted from morphology, never
from truth, which is exactly why a hit can be wrong and the model that consumes it must earn its
weight rather than read the answer.

A hit is one (subject, typology) pair with every transaction that fed it, so the console can show
an analyst the transactions behind an accusation and BUDDHI can window the hit by those txids. The
thresholds are module constants, following the estimator's own precedent (`estimate.TREE_PARAMS`):
a detector is a fixed rule, and a rule that moved with the config could not be replayed.

- `def address_subject(clusters: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:` — One row per (address, subject_id): a JAAL cluster, or the address as its own singleton.
- `def _sender_txns(transactions: pl.DataFrame, addr_subject: pl.DataFrame) -> pl.DataFrame:` — One row per (subject_id, txid) the subject sent, carrying that transaction's morphology.
- `def _hits(per_subject: pl.DataFrame, typology: str, threshold: float) -> pl.DataFrame:` — Attach the contract columns to a frame that already has subject_id, txids and strength.
- `def detect(transactions: pl.DataFrame, clusters: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:` — Every typology hit in the capture, one row per (subject, typology).

#### `src/chakravyuh/vaani/__main__.py`

`python -m chakravyuh.vaani --in data/generated/<run> --out data/generated/<run>`.

No eval import, no flag that names a path outside the observable tree. `--in` and `--out`
must both resolve under `data/generated/`, which is the stage guard: the answer key is a
sibling tree and cannot be reached by any invocation of this module.

- `def build_parser() -> argparse.ArgumentParser:` — Internal helper; behavior is defined by the source implementation.
- `def main(argv: list[str] | None=None) -> int:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/vaani/counters.py`

The reasons against each alert, in the same pass that builds the alert.

Counter-evidence generated here is never optional enrichment: the caller builds one row
list per alert in the same loop that writes the alert row, and `build` raises if any alert
ends with zero counters, which is the contract's "the pipeline fails if any alert has none".

The kinds are contract section 8's closed vocabulary. Two of them — `entity_type_conflict`
and `pool_payout_pattern` — fire from `signals/entity_types.parquet`, which is zero-row on
every run written so far (S06 rider); those paths stay dormant on real data and are
exercised by the named mining-pool test. A benign explanation for a typology hit rides
`entity_type_conflict`: it is the same claim, that something innocent about this subject
explains the pattern the model saw.

`would_clear` is reserved for the one decisive case: an entity whose own type explains the
behaviour — a mining pool with coinbase origination and a regular payout cadence above all.
A tool that marks which single doubt closes the lead is one an investigator can use.

- `def _entity_counters(subject_id: str, alert_id: str, types_row: dict[str, object] | None, has_typology_hit: bool) -> list[dict[str, object]]:` — Entity-type counters for one alert, including the decisive mining-pool case.
- `def build(alerts: pl.DataFrame, origin_top1: pl.DataFrame, entity_types: pl.DataFrame, typology_hits: pl.DataFrame, clusters: pl.DataFrame, peer_subjects: pl.DataFrame, abstain_frac: pl.DataFrame, margin_floor: float, origin_mass: pl.DataFrame) -> pl.DataFrame:` — One or more counter rows per alert, every kind decided from observable data alone.

#### `src/chakravyuh/vaani/evidence.py`

Evidence rows: the reasons for an alert, and the language that states them.

Every statement is a template over observable quantities; no LLM call, no network, no clock
in the text path, which is what makes the same input render the same three sentences in a
second process. Identifiers are truncated here, at write time, so the parquet itself is
safe to open on a projector — a raw column name never appears because every feature name
passes through the gloss table first.

The three-sentence reason string is assembled from the evidence and counter rows by
`reason_string`, at read time, by PRAMAAN or the console. `alerts.parquet` stays
contract-exact; the reason is derived, never stored.

- `def _anchor(subject_id: str, addresses: list[str], receives: pl.DataFrame, origin_top1: pl.DataFrame) -> dict[str, object]:` — The single transaction whose origin estimate anchors this alert.
- `def alerts_frame(scores: pl.DataFrame, clusters: pl.DataFrame, receives: pl.DataFrame, origin_top1: pl.DataFrame, glosses: dict[str, str]) -> pl.DataFrame:` — The contract section 8 alerts table, one row per scored subject that is not licit.
- `def _short_gloss(glosses: dict[str, str], name: str, value: float) -> str:` — A compact clause for one feature: gloss plus direction, no number to crowd the line.
- `def evidence_rows(internal: pl.DataFrame, glosses: dict[str, str], announcements: pl.DataFrame, clusters: pl.DataFrame) -> pl.DataFrame:` — The reasons for, one row per reason per alert, identifiers truncated in the prose.
- `def _utc(us: int) -> str:` — UTC string of a microsecond timestamp, for a sentence an analyst reads.
- `def reason_string(alert: dict[str, object], evidence: pl.DataFrame, counters: pl.DataFrame) -> str:` — Three sentences, maximum, assembled from the rows this alert already carries.

#### `src/chakravyuh/vaani/gloss.py`

The plain-English gloss of a model feature name, read from `docs/FEATURES.md`.

Never show a raw column name in an alert: the gloss table is the map from what the model
saw to what an analyst reads. The table is parsed from the same markdown the S07 gate
validates `top_features` against, so the two cannot drift apart, and a name missing from
the table raises rather than rendering a bare identifier into prose.

- `def default_path() -> Path:` — Where the gloss table lives: the working directory's copy if present, else the repo's.
- `def load_glosses(path: Path) -> dict[str, str]:` — Feature name to its plain-English phrase, from the markdown table's second column.
- `def gloss(glosses: dict[str, str], name: str) -> str:` — The phrase for one feature name. Raises rather than rendering a raw column name.

#### `src/chakravyuh/vaani/investigation.py`

Ranked offline lead packets: model reasons, exact money edges and observed network support.

- `def select(ranked: list[str], supports: dict[str, set[str]], *, k: int, overlap: float | None) -> list[str]:` — Select evidence-diverse leads without labels or assumptions about ownership.
- `def packet(scores: pl.DataFrame, view: snapshot.Snapshot, transactions: pl.DataFrame, announcements: pl.DataFrame, peers: pl.DataFrame, *, k: int=20, overlap: float | None=0.25, max_transactions: int=16) -> dict[str, Any]:` — Structured evidence plus redacted display strings; no answer-key dependencies.
- `def run(normalised: Path, model: Path, output: Path, *, start_us: int, end_us: int, k: int=20, overlap: float | None=0.25) -> dict[str, Any]:` — Produce a reusable JSON queue, scores and provenance on unlabeled input files.
- `def main() -> None:` — Internal helper; behavior is defined by the source implementation.

#### `src/chakravyuh/vaani/redact.py`

Identifier truncation at write time, for every human-readable string VAANI emits.

Contract section 8's `statement` columns are prose a non-specialist reads, so no complete
identifier may sit in one: addresses keep first six and last four, txids first eight and
last four, IPv4 two octets, IPv6 two hextets. SHA-256 values are the deliberate exception
and never pass through here.

The structured columns of `alerts.parquet` (`origin_txid`, `origin_peer_ip`) are contract
fields, not rendered prose: section 9's packet quotes them, and the console's shared
formatter truncates defensively on display. This module exists for the prose.

- `def redact_address(address: str) -> str:` — First six and last four characters, whatever the length survives as.
- `def redact_txid(txid: str) -> str:` — First eight and last four hex characters of a transaction id.
- `def redact_ip(ip: str) -> str:` — Two octets of an IPv4, two hextets of an IPv6, per the truncation law.

#### `src/chakravyuh/vaani/stage.py`

VAANI as a stage: read `scores/`, `signals/` and `graph/`, write `alerts/`.

The path guards are BUDDHI's, restated rather than imported, for the reason that rule
exists: `--in` is allowlisted to `data/generated/`, so a VAANI invocation cannot be pointed
at the answer key even by an operator who wants to, because the answer key is a sibling tree
and not under `data/`.

This module never imports `chakravyuh.eval` and never opens anything outside the run's
observable directories. Every counter row is built in the same pass that builds its alert,
so an alert cannot exist without counter-evidence — the brief's "technically present and
always empty" trap is a raise here, not a warning.

- Class `InputPathError` — A path VAANI will not read from, or will not write to.
- `def _relative_to_cwd(path: Path, root: str) -> Path:` — `path` resolved, refused unless it sits inside `<cwd>/<root>`.
- `def resolve_in(target: Path) -> Path:` — The run directory whose `scores/`, `signals/` and `graph/` VAANI reads.
- `def resolve_out(target: Path) -> Path:` — The run directory to write `alerts/` into.
- `def _repo_relative(path: Path) -> str:` — Internal helper; behavior is defined by the source implementation.
- `def _write_parquet(frame: pl.DataFrame, path: Path) -> str:` — Write, then hash what was written. Compression is pinned so two runs agree byte for byte.
- `def _meta_link(directory: Path) -> tuple[str | None, str | None]:` — Path and hash of a stage directory's `_meta.json`, for the staleness check.
- `def _margin_floor(run_dir: Path) -> float:` — The estimator's own abstention threshold, read from the run it was estimated under.
- `def build_run(run_dir: Path, out: Path) -> Path:` — Build `<out>/alerts/` from the run's `scores/`, `signals/`, `graph/` and `normalised/`.
- `def _seed(run_dir: Path) -> int:` — The run's seed, from `config.effective.json`; 0 when the run records none.

### Appendix E — verification and artifact directory

| Artifact | Purpose |
| --- | --- |
| `research/bitcoin/results/drishti-r47-ui/report.json` | Browser check results and screenshots |
| `research/bitcoin/results/drishti-r47-graph-training/report.json` | Actual trained neural/tree comparison |
| `research/bitcoin/results/drishti-r47-graph-training/invocation.json` | Executed partition/configuration |
| `research/bitcoin/results/relational-inference-replay.json` | Independent feature/score replay |
| `research/bitcoin/results/relational-inference-artifacts/` | Portable CPU models/manifests |
| `research/bitcoin/results/investigation-demo-v2/` | Generated investigation queues |
| `research/bitcoin/results/investigation-stripped-smoke.json` | No-truth/no-Torch isolated replay |
| `research/bitcoin/results/submission-audit/source-inventory.json` | Exact inspected source hashes |
| `research/bitcoin/results/submission-audit/runtime-versions.json` | Observed prepared runtime |
| `docs/research/events.jsonl` | Append-only action/event audit |

For a historical experiment, its executed source snapshot and manifest override current defaults. No isolated performance number is a universal guarantee.

### Appendix F — frozen portable model manifest

This is the actual address-mode candidate manifest, including ordered 329 features, fitted scalers, Platt parameters and model digest. It describes the optional CPU engine, not the default LightGBM.

```json
{
  "schema_version": 1,
  "features": [
    "n_addresses",
    "n_tx_sent",
    "total_sent_sats",
    "mean_sent_sats",
    "n_tx_received",
    "total_received_sats",
    "mean_received_sats",
    "balance_sats",
    "n_counterparties",
    "max_fan_out",
    "n_coinbase_received",
    "frac_equal_outputs",
    "mean_fee_rate",
    "median_dwell_us",
    "min_edge_confidence",
    "n_heuristics",
    "n_script_types",
    "fan_in_ratio",
    "peel_chain_depth",
    "peel_leak_frac",
    "structuring_frac",
    "burstiness",
    "fee_anomaly",
    "received_log_degree",
    "received_mean_n_in",
    "received_mean_n_out",
    "received_mean_total_out_sats",
    "received_mean_fee_sats",
    "received_mean_fee_rate_sat_vb",
    "received_mean_has_equal_outputs",
    "received_mean_announcer_mean_observations",
    "received_mean_announcer_mean_transactions",
    "received_mean_announcer_mean_observers",
    "received_mean_announcer_mean_class_0",
    "received_mean_announcer_mean_class_1",
    "received_mean_announcer_mean_class_2",
    "received_mean_announcer_mean_class_3",
    "received_mean_announcer_mean_class_4",
    "received_mean_announcer_mean_class_5",
    "received_mean_funder_mean_n_addresses",
    "received_mean_funder_mean_n_tx_sent",
    "received_mean_funder_mean_total_sent_sats",
    "received_mean_funder_mean_mean_sent_sats",
    "received_mean_funder_mean_n_tx_received",
    "received_mean_funder_mean_total_received_sats",
    "received_mean_funder_mean_mean_received_sats",
    "received_mean_funder_mean_balance_sats",
    "received_mean_funder_mean_n_counterparties",
    "received_mean_funder_mean_max_fan_out",
    "received_mean_funder_mean_n_coinbase_received",
    "received_mean_funder_mean_frac_equal_outputs",
    "received_mean_funder_mean_mean_fee_rate",
    "received_mean_funder_mean_median_dwell_us",
    "received_mean_funder_mean_min_edge_confidence",
    "received_mean_funder_mean_n_heuristics",
    "received_mean_funder_mean_n_script_types",
    "received_mean_funder_mean_fan_in_ratio",
    "received_mean_funder_mean_peel_chain_depth",
    "received_mean_funder_mean_peel_leak_frac",
    "received_mean_funder_mean_structuring_frac",
    "received_mean_funder_mean_burstiness",
    "received_mean_funder_mean_fee_anomaly",
    "received_std_n_in",
    "received_std_n_out",
    "received_std_total_out_sats",
    "received_std_fee_sats",
    "received_std_fee_rate_sat_vb",
    "received_std_has_equal_outputs",
    "received_std_announcer_mean_observations",
    "received_std_announcer_mean_transactions",
    "received_std_announcer_mean_observers",
    "received_std_announcer_mean_class_0",
    "received_std_announcer_mean_class_1",
    "received_std_announcer_mean_class_2",
    "received_std_announcer_mean_class_3",
    "received_std_announcer_mean_class_4",
    "received_std_announcer_mean_class_5",
    "received_std_funder_mean_n_addresses",
    "received_std_funder_mean_n_tx_sent",
    "received_std_funder_mean_total_sent_sats",
    "received_std_funder_mean_mean_sent_sats",
    "received_std_funder_mean_n_tx_received",
    "received_std_funder_mean_total_received_sats",
    "received_std_funder_mean_mean_received_sats",
    "received_std_funder_mean_balance_sats",
    "received_std_funder_mean_n_counterparties",
    "received_std_funder_mean_max_fan_out",
    "received_std_funder_mean_n_coinbase_received",
    "received_std_funder_mean_frac_equal_outputs",
    "received_std_funder_mean_mean_fee_rate",
    "received_std_funder_mean_median_dwell_us",
    "received_std_funder_mean_min_edge_confidence",
    "received_std_funder_mean_n_heuristics",
    "received_std_funder_mean_n_script_types",
    "received_std_funder_mean_fan_in_ratio",
    "received_std_funder_mean_peel_chain_depth",
    "received_std_funder_mean_peel_leak_frac",
    "received_std_funder_mean_structuring_frac",
    "received_std_funder_mean_burstiness",
    "received_std_funder_mean_fee_anomaly",
    "received_min_n_in",
    "received_min_n_out",
    "received_min_total_out_sats",
    "received_min_fee_sats",
    "received_min_fee_rate_sat_vb",
    "received_min_has_equal_outputs",
    "received_min_announcer_mean_observations",
    "received_min_announcer_mean_transactions",
    "received_min_announcer_mean_observers",
    "received_min_announcer_mean_class_0",
    "received_min_announcer_mean_class_1",
    "received_min_announcer_mean_class_2",
    "received_min_announcer_mean_class_3",
    "received_min_announcer_mean_class_4",
    "received_min_announcer_mean_class_5",
    "received_min_funder_mean_n_addresses",
    "received_min_funder_mean_n_tx_sent",
    "received_min_funder_mean_total_sent_sats",
    "received_min_funder_mean_mean_sent_sats",
    "received_min_funder_mean_n_tx_received",
    "received_min_funder_mean_total_received_sats",
    "received_min_funder_mean_mean_received_sats",
    "received_min_funder_mean_balance_sats",
    "received_min_funder_mean_n_counterparties",
    "received_min_funder_mean_max_fan_out",
    "received_min_funder_mean_n_coinbase_received",
    "received_min_funder_mean_frac_equal_outputs",
    "received_min_funder_mean_mean_fee_rate",
    "received_min_funder_mean_median_dwell_us",
    "received_min_funder_mean_min_edge_confidence",
    "received_min_funder_mean_n_heuristics",
    "received_min_funder_mean_n_script_types",
    "received_min_funder_mean_fan_in_ratio",
    "received_min_funder_mean_peel_chain_depth",
    "received_min_funder_mean_peel_leak_frac",
    "received_min_funder_mean_structuring_frac",
    "received_min_funder_mean_burstiness",
    "received_min_funder_mean_fee_anomaly",
    "received_max_n_in",
    "received_max_n_out",
    "received_max_total_out_sats",
    "received_max_fee_sats",
    "received_max_fee_rate_sat_vb",
    "received_max_has_equal_outputs",
    "received_max_announcer_mean_observations",
    "received_max_announcer_mean_transactions",
    "received_max_announcer_mean_observers",
    "received_max_announcer_mean_class_0",
    "received_max_announcer_mean_class_1",
    "received_max_announcer_mean_class_2",
    "received_max_announcer_mean_class_3",
    "received_max_announcer_mean_class_4",
    "received_max_announcer_mean_class_5",
    "received_max_funder_mean_n_addresses",
    "received_max_funder_mean_n_tx_sent",
    "received_max_funder_mean_total_sent_sats",
    "received_max_funder_mean_mean_sent_sats",
    "received_max_funder_mean_n_tx_received",
    "received_max_funder_mean_total_received_sats",
    "received_max_funder_mean_mean_received_sats",
    "received_max_funder_mean_balance_sats",
    "received_max_funder_mean_n_counterparties",
    "received_max_funder_mean_max_fan_out",
    "received_max_funder_mean_n_coinbase_received",
    "received_max_funder_mean_frac_equal_outputs",
    "received_max_funder_mean_mean_fee_rate",
    "received_max_funder_mean_median_dwell_us",
    "received_max_funder_mean_min_edge_confidence",
    "received_max_funder_mean_n_heuristics",
    "received_max_funder_mean_n_script_types",
    "received_max_funder_mean_fan_in_ratio",
    "received_max_funder_mean_peel_chain_depth",
    "received_max_funder_mean_peel_leak_frac",
    "received_max_funder_mean_structuring_frac",
    "received_max_funder_mean_burstiness",
    "received_max_funder_mean_fee_anomaly",
    "spent_log_degree",
    "spent_mean_n_in",
    "spent_mean_n_out",
    "spent_mean_total_out_sats",
    "spent_mean_fee_sats",
    "spent_mean_fee_rate_sat_vb",
    "spent_mean_has_equal_outputs",
    "spent_mean_announcer_mean_observations",
    "spent_mean_announcer_mean_transactions",
    "spent_mean_announcer_mean_observers",
    "spent_mean_announcer_mean_class_0",
    "spent_mean_announcer_mean_class_1",
    "spent_mean_announcer_mean_class_2",
    "spent_mean_announcer_mean_class_3",
    "spent_mean_announcer_mean_class_4",
    "spent_mean_announcer_mean_class_5",
    "spent_mean_funder_mean_n_addresses",
    "spent_mean_funder_mean_n_tx_sent",
    "spent_mean_funder_mean_total_sent_sats",
    "spent_mean_funder_mean_mean_sent_sats",
    "spent_mean_funder_mean_n_tx_received",
    "spent_mean_funder_mean_total_received_sats",
    "spent_mean_funder_mean_mean_received_sats",
    "spent_mean_funder_mean_balance_sats",
    "spent_mean_funder_mean_n_counterparties",
    "spent_mean_funder_mean_max_fan_out",
    "spent_mean_funder_mean_n_coinbase_received",
    "spent_mean_funder_mean_frac_equal_outputs",
    "spent_mean_funder_mean_mean_fee_rate",
    "spent_mean_funder_mean_median_dwell_us",
    "spent_mean_funder_mean_min_edge_confidence",
    "spent_mean_funder_mean_n_heuristics",
    "spent_mean_funder_mean_n_script_types",
    "spent_mean_funder_mean_fan_in_ratio",
    "spent_mean_funder_mean_peel_chain_depth",
    "spent_mean_funder_mean_peel_leak_frac",
    "spent_mean_funder_mean_structuring_frac",
    "spent_mean_funder_mean_burstiness",
    "spent_mean_funder_mean_fee_anomaly",
    "spent_std_n_in",
    "spent_std_n_out",
    "spent_std_total_out_sats",
    "spent_std_fee_sats",
    "spent_std_fee_rate_sat_vb",
    "spent_std_has_equal_outputs",
    "spent_std_announcer_mean_observations",
    "spent_std_announcer_mean_transactions",
    "spent_std_announcer_mean_observers",
    "spent_std_announcer_mean_class_0",
    "spent_std_announcer_mean_class_1",
    "spent_std_announcer_mean_class_2",
    "spent_std_announcer_mean_class_3",
    "spent_std_announcer_mean_class_4",
    "spent_std_announcer_mean_class_5",
    "spent_std_funder_mean_n_addresses",
    "spent_std_funder_mean_n_tx_sent",
    "spent_std_funder_mean_total_sent_sats",
    "spent_std_funder_mean_mean_sent_sats",
    "spent_std_funder_mean_n_tx_received",
    "spent_std_funder_mean_total_received_sats",
    "spent_std_funder_mean_mean_received_sats",
    "spent_std_funder_mean_balance_sats",
    "spent_std_funder_mean_n_counterparties",
    "spent_std_funder_mean_max_fan_out",
    "spent_std_funder_mean_n_coinbase_received",
    "spent_std_funder_mean_frac_equal_outputs",
    "spent_std_funder_mean_mean_fee_rate",
    "spent_std_funder_mean_median_dwell_us",
    "spent_std_funder_mean_min_edge_confidence",
    "spent_std_funder_mean_n_heuristics",
    "spent_std_funder_mean_n_script_types",
    "spent_std_funder_mean_fan_in_ratio",
    "spent_std_funder_mean_peel_chain_depth",
    "spent_std_funder_mean_peel_leak_frac",
    "spent_std_funder_mean_structuring_frac",
    "spent_std_funder_mean_burstiness",
    "spent_std_funder_mean_fee_anomaly",
    "spent_min_n_in",
    "spent_min_n_out",
    "spent_min_total_out_sats",
    "spent_min_fee_sats",
    "spent_min_fee_rate_sat_vb",
    "spent_min_has_equal_outputs",
    "spent_min_announcer_mean_observations",
    "spent_min_announcer_mean_transactions",
    "spent_min_announcer_mean_observers",
    "spent_min_announcer_mean_class_0",
    "spent_min_announcer_mean_class_1",
    "spent_min_announcer_mean_class_2",
    "spent_min_announcer_mean_class_3",
    "spent_min_announcer_mean_class_4",
    "spent_min_announcer_mean_class_5",
    "spent_min_funder_mean_n_addresses",
    "spent_min_funder_mean_n_tx_sent",
    "spent_min_funder_mean_total_sent_sats",
    "spent_min_funder_mean_mean_sent_sats",
    "spent_min_funder_mean_n_tx_received",
    "spent_min_funder_mean_total_received_sats",
    "spent_min_funder_mean_mean_received_sats",
    "spent_min_funder_mean_balance_sats",
    "spent_min_funder_mean_n_counterparties",
    "spent_min_funder_mean_max_fan_out",
    "spent_min_funder_mean_n_coinbase_received",
    "spent_min_funder_mean_frac_equal_outputs",
    "spent_min_funder_mean_mean_fee_rate",
    "spent_min_funder_mean_median_dwell_us",
    "spent_min_funder_mean_min_edge_confidence",
    "spent_min_funder_mean_n_heuristics",
    "spent_min_funder_mean_n_script_types",
    "spent_min_funder_mean_fan_in_ratio",
    "spent_min_funder_mean_peel_chain_depth",
    "spent_min_funder_mean_peel_leak_frac",
    "spent_min_funder_mean_structuring_frac",
    "spent_min_funder_mean_burstiness",
    "spent_min_funder_mean_fee_anomaly",
    "spent_max_n_in",
    "spent_max_n_out",
    "spent_max_total_out_sats",
    "spent_max_fee_sats",
    "spent_max_fee_rate_sat_vb",
    "spent_max_has_equal_outputs",
    "spent_max_announcer_mean_observations",
    "spent_max_announcer_mean_transactions",
    "spent_max_announcer_mean_observers",
    "spent_max_announcer_mean_class_0",
    "spent_max_announcer_mean_class_1",
    "spent_max_announcer_mean_class_2",
    "spent_max_announcer_mean_class_3",
    "spent_max_announcer_mean_class_4",
    "spent_max_announcer_mean_class_5",
    "spent_max_funder_mean_n_addresses",
    "spent_max_funder_mean_n_tx_sent",
    "spent_max_funder_mean_total_sent_sats",
    "spent_max_funder_mean_mean_sent_sats",
    "spent_max_funder_mean_n_tx_received",
    "spent_max_funder_mean_total_received_sats",
    "spent_max_funder_mean_mean_received_sats",
    "spent_max_funder_mean_balance_sats",
    "spent_max_funder_mean_n_counterparties",
    "spent_max_funder_mean_max_fan_out",
    "spent_max_funder_mean_n_coinbase_received",
    "spent_max_funder_mean_frac_equal_outputs",
    "spent_max_funder_mean_mean_fee_rate",
    "spent_max_funder_mean_median_dwell_us",
    "spent_max_funder_mean_min_edge_confidence",
    "spent_max_funder_mean_n_heuristics",
    "spent_max_funder_mean_n_script_types",
    "spent_max_funder_mean_fan_in_ratio",
    "spent_max_funder_mean_peel_chain_depth",
    "spent_max_funder_mean_peel_leak_frac",
    "spent_max_funder_mean_structuring_frac",
    "spent_max_funder_mean_burstiness",
    "spent_max_funder_mean_fee_anomaly"
  ],
  "partition_mode": "address",
  "model_sha256": "303c88fc9f640d8b110d95230cfbc57256d3d68bc2b205a08cfe066748089af7",
  "scalers": {
    "subject": {
      "mean": [
        0.6931471805599454,
        0.22079972265025663,
        4.54673828795885,
        4.526369740725131,
        0.5875529873928437,
        11.878256015040588,
        11.844700509734176,
        7.188132069317394,
        1.119636758636137,
        0.2075420828522513,
        0.0,
        0.005199198048262249,
        0.7133110978747765,
        2.0904065250010526,
        0.0,
        0.0,
        0.6931471805599454,
        0.42190599425416137,
        0.015203147576796954,
        0.0018075517112834695,
        0.032834367603053236,
        0.0038154538769290796,
        0.08845463302276553
      ],
      "scale": [
        1.0,
        0.3554567982171832,
        7.046298265823291,
        7.00579123583771,
        0.3034872597657804,
        5.820132472073793,
        5.7909383509864085,
        12.173878403762988,
        0.5485312706683261,
        0.3174641608464266,
        1.0,
        0.05980616864488724,
        1.1793751624118431,
        6.568309393997357,
        1.0,
        1.0,
        1.0,
        0.7414527986518784,
        0.10158548985860892,
        0.014263396840692442,
        0.1434812123663896,
        0.04701643955202836,
        1.1319622227912167
      ]
    },
    "transaction": {
      "mean": [
        0.9264872080527333,
        1.5888961947079727,
        16.66489430727309,
        7.84375833488153,
        2.3677835389158064,
        0.01604437066356354
      ],
      "scale": [
        0.41282240837105466,
        0.4653018905619707,
        1.9719602538045495,
        1.075626443570379,
        0.8306997848217258,
        0.10422901927638938
      ]
    },
    "ip": {
      "mean": [
        3.349451333223845,
        3.3490995799236063,
        0.7103844455713829,
        0.08395396073121192,
        0.0,
        0.8801624915368991,
        0.009478672985781991,
        0.0,
        0.026404874746106973
      ],
      "scale": [
        0.5316809444693245,
        0.5307988692809401,
        0.09136046121364236,
        0.277318757405193,
        1.0,
        0.32477142735851006,
        0.09689596350835178,
        1.0,
        0.16033607621415974
      ]
    }
  },
  "platt_coefficient": 0.9911816716194153,
  "platt_intercept": 2.018376111984253,
  "platt_dtype": "float32",
  "exporter_sha256": "7d940f3765bdd3c0165f07a721c49361d850714fb323cd391bbcd54d0a8d14a9",
  "experimental": true,
  "automatic_alert_threshold": null
}
```

### Appendix G — actual neural model implementation

Exact R47 model/optimization code; research only. Constants WIDTH=32, EPOCHS=60 for the recorded invocation.

```python
class Model(torch.nn.Module):
    def __init__(self, dimensions, graph=True, temporal=False):
        super().__init__()
        self.use_graph, self.temporal = graph, temporal
        self.encode = torch.nn.ModuleDict(
            {k: torch.nn.Linear(d, WIDTH) for k, d in dimensions.items()}
        )
        self.funds = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.announces = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.receives = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.spends = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.self_update = torch.nn.Linear(WIDTH, WIDTH)
        self.gru = torch.nn.GRUCell(WIDTH, WIDTH)
        self.head = torch.nn.Linear(WIDTH, 1)

    def forward(self, g, bank):
        h = {k: torch.relu(self.encode[k](g[k])) for k in self.encode}
        if self.use_graph:
            tx = torch.relu(
                h["transaction"]
                + self.funds(pool(h["subject"], g["edges"]["funds"], len(h["transaction"])))
                + self.announces(pool(h["ip"], g["edges"]["announces"], len(h["transaction"])))
            )
            subject = torch.relu(
                self.self_update(h["subject"])
                + self.receives(pool(tx, g["edges"]["receives"], len(h["subject"])))
                + self.spends(pool(tx, g["edges"]["funds"].flip(0), len(h["subject"])))
            )
        else:
            subject = torch.relu(self.self_update(h["subject"]))
        if self.temporal:
            previous = pool(bank, g["memory_edges"], len(subject))
            subject = self.gru(subject, previous)
        return self.head(
            torch.nn.functional.dropout(subject, 0.2, self.training)
        ).flatten(), subject
```

```python
def rollout(net, graphs):
    bank = torch.empty((0, WIDTH))
    outputs, embeddings = [], []
    for g in graphs:
        p, h = net(g, bank)
        outputs.append(torch.sigmoid(p).detach().numpy())
        embeddings.append(h.detach().numpy())
        bank = torch.cat([bank, h.detach()])
    return np.concatenate(outputs), np.concatenate(embeddings)
```

```python
def train(graphs, name, graph=True, temporal=False):
    torch.manual_seed(42)
    net = Model(
        {k: graphs[0][k].shape[1] for k in ("subject", "transaction", "ip")}, graph, temporal
    )
    opt = torch.optim.AdamW(net.parameters(), lr=0.001, weight_decay=0.001)
    fit = [g for g in graphs if g["phase"] == "fit"]
    y = torch.cat([g["y"] for g in fit])
    weight = float(torch.sqrt((len(y) - y.sum()) / y.sum()))
    loss = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight))
    best, best_epoch, best_ap = None, 0, -1.0
    for epoch in range(1, EPOCHS + 1):
        net.train()
        bank = torch.empty((0, WIDTH))
        for g in fit:
            opt.zero_grad()
            logits, h = net(g, bank)
            objective = loss(logits, g["y"])
            objective.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 5)
            opt.step()
            bank = torch.cat([bank, h.detach()])
        if epoch % 5 == 0:
            net.eval()
            with torch.no_grad():
                p, _ = rollout(net, graphs[:7])
            v = graphs[6]["y"].numpy()
            ap = float(average_precision_score(v, p[-len(v) :]))
            if ap > best_ap:
                best, best_epoch, best_ap = copy.deepcopy(net.state_dict()), epoch, ap
    net.load_state_dict(best)
    net.eval()
    with torch.no_grad():
        scores, embeddings = rollout(net, graphs)
    torch.save(
        {
            "state_dict": net.state_dict(),
            "graph": graph,
            "temporal": temporal,
            "width": WIDTH,
            "selected_epoch": best_epoch,
        },
        OUT / f"{name}.pt",
    )
    return (
        scores,
        embeddings,
        {
            "selected_epoch": best_epoch,
            "validation_checkpoint_ap": best_ap,
            "parameters": sum(p.numel() for p in net.parameters()),
            "positive_weight": weight,
        },
    )
```

### Appendix H — exact frontend package declaration

```json
{
  "name": "drishti-v2",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "three": "^0.171.0",
    "@react-three/fiber": "^8.17.10",
    "@react-three/drei": "^9.122.0",
    "gsap": "^3.13.0",
    "@gsap/react": "^2.1.0",
    "lenis": "^1.3.11"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@types/three": "^0.171.0",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```
