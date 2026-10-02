# SIH investigative engine: positive findings and working implementation

Updated 2026-10-01, R42–R45. This checkpoint turns the useful graph-model research into an offline, explainable investigation prototype. The research goal is **more useful leads per investigator review budget**, with evidence that can be examined and exported.

## What the research has positively established

| Finding | Evidence | Practical value |
| --- | --- | --- |
| Observable graph information helps detection | Richer address XGBoost future-window AP .3148 versus .0538 for the matched local-only model | Fund-flow and announcing-peer context add useful signal in our simulator |
| Evidence diversity improves lead yield | Frozen rich-XGBoost policy retrieves 11→33 and 9→16 suspicious controller-window leads across three windows in two generated worlds | Fewer review slots consumed by overlapping transaction evidence |
| Detection works without ownership merges | Address-only models trained and evaluated; corrupt ledger isolation regression | JAAL ownership uncertainty is contained instead of becoming a prerequisite for every lead |
| Graph features also help on public Bitcoin data | Actual Elliptic graph-feature LightGBM AP .6566/F1 .6872 versus local LightGBM .6366/.6238 | An external-data experiment supports relational feature engineering beyond the simulator |
| Research weights can become a usable engine | Independent NumPy inference port reproduces 324,395 rows across 20 representation/window checks, features and scores exactly | A lightweight deployment path exists without importing Torch or research code |
| Scores become inspectable cases | Actual generated queues with SHAP, amounts, network observations and graph edges | An investigator can move from ranking to supporting evidence |

These are results under their declared protocols. The Elliptic and synthetic metrics have different targets, splits and prevalence and must not be compared as one leaderboard. The11→33 / 9→16 figures count controller-window retrieval: the same controller may recur in another window. They do not establish33 distinct people, guaranteed precision, global novelty or a competition ranking.

The useful contribution is an integrated investigative workflow: **learned relational detection → evidence-diverse queue → explainable case graph → portable packet**. NTRO's stated objective is prioritized, explainable investigative leads from correlated metadata. Our strongest demonstration should make that workflow immediate and inspectable.

## What was implemented in this checkpoint

1. `buddhi/relational_inference.py`: portable329-feature graph-context inference. Reads only normalised transactions, addresses, announcements and peer metadata; validates model schema/hash; applies frozen transformations; predicts with native CPU XGBoost; checks TreeSHAP margin reconstruction.
2. Portable native model artifacts for address-only and CIOH representations: nativeJSON plus a JSON manifest containing feature order, scalers, calibration and representation. Runtime inference does not load research pickle files. The exporter reads known local frozen research artifacts.
3. `vaani/investigation.py`: an executable offline queue generator. It selects leads using observed transaction support, builds case graphs, emits exact integer amounts and timed announcement references, shows signed model effects and suggests evidence-review steps.
4. An interactive World-screen investigation preview. Select a lead, inspect contributions and graph context, inspect amounts, and export the queue. Load another generated queue through a local JSON file input; validation rejects malformed, oversized or structurally inconsistent packets. Browser interactions require no server inference, GPU or external requests.
5. Actual replay, isolated-runtime, graph-boundary, money-amount, identifier-collision and browser interaction checks.

The default application stage still uses its shipped LightGBM. The new scorer is a working optional engine, and the new preview is a separate local packet viewer. Loading a queue does not silently replace the active run's metrics or backend. Raw ingestion continues through the existing KAVACH/SETU pipeline; the new CLI consumes its normalised outputs.

## Architecture

```text
Bulk CSV / JSON / XML
          │
 Existing KAVACH / SETU
          │
 Normalised transaction + address + announcement + peer artifacts
          │
          ├──────── JAAL ownership claims, with provenance
          │                     │
          │             Optional grouped graph view
          │
          ▼
 Decision-window address / TX / peer graph
          │
 Local features + typed two-hop neighborhood distributions
          │
 Frozen CPU XGBoost + TreeSHAP
          │
 Score ordering + observable evidence diversity
          │
 Case packet: amounts + timestamps + model effects + evidence graph
          │
 Local dashboard viewer / JSON export
```

SHASTRA attribution is an additional evidence path, not a mandatory dependency for scoring the monetary behavior. Announcing-peer edges identify observations, not verified originating hosts. Ownership hypotheses can be examined alongside a lead without first forcing them into an identity.

## Exact graph-context model recipe

There are23 local subject inputs: activity counts, gross sent/received amounts, balance, counterparties, output fan-out, coinbase receipt, equal outputs, fee rate, dwell, ownership evidence summaries, script diversity, fan-in, peel/structuring/timing and fee deviation. Address mode fixes one address per subject and excludes the entire ownership ledger.

For each transaction, the context vector contains:

- Six transaction attributes: input count, output count, total output satoshis, fee satoshis, fee rate and equal-output indicator.
- Nine mean announcing-peer attributes: log announcement/TX/observer counts and six network-class indicators.
- Twenty-three mean funding-subject attributes.

This yields38 context dimensions. For incoming and outgoing subject relations separately, summarize log(1+degree), then the mean, population standard deviation, minimum and maximum of each context dimension. Each relation contributes1 + 4×38=153 dimensions;23 + 2×153=**329 features**.

Labels and neighbor labels never enter these features. Node IDs establish joins and ordering, not input values. All event selection is bounded to the declared window. Ownership hypotheses are taken as of its end. Supplied peer classification is assumed to come from a fixed offline metadata snapshot.

Local inputs use signed log1p, transaction values nonnegative log1p, and peer counts log1p with network-class indicators. Type scalers fit only training windows 0–3. Frozen mean pooling uses float32; relation statistics accumulate in float64, clamp negative variance from rounding to zero, and cast the final input matrix to float32. Empty neighborhoods have zero context.

XGBoost parameters:300 trees, maximum depth 5, learning rate .05, minimum child weight 10, row/column sampling .9, CPU histogram tree algorithm, seed 42, four threads. Binary classification is calibrated with frozen Platt logistic parameters from windows 4–5. Window 6 chooses research settings; windows 7–9 evaluate future behavior. The JSON manifest preserves scaler/calibration parameters and feature names exactly.

Calibration produces a historical model-ranking score. Transfer calibration and a safe automatic alert threshold are not established. The viewer therefore labels it as a ranking score and provides the evidence and model effects for review.

## Evidence diversity and case construction

Take up to2,000 score-ordered eligible subjects. Each subject's support is its observed incoming/outgoing TXID set in the window. Greedily keep a lead if its pairwise transaction-set Jaccard overlap with already chosen leads is at most .25, stopping at 20. This parameter was selected on canonical validation in R40 and frozen for transfer. It is an optional investigative queue recipe, not a learned ownership classifier.

Only after this selection does research evaluation attach hidden controller/participation keys. The production selector accepts no such keys. Distinct transaction support does not prove distinct owners; fewer overlapping alerts are an observable workload benefit.

Each packet retains a bounded chronological context of up to 16 supporting transactions per lead. It includes all input/output endpoints for those transactions, exact integer satoshis, their observed timestamps and fees, and up to four distinct captured announcing peers per transaction with row/timing/port references. Graph truncation is explicitly recorded. Full capture retention belongs to KAVACH/SETU; this bounded view is not a substitute for it.

Money edges are address→transaction inputs and transaction→address outputs. They do not invent pairwise input-to-output attribution or exact taint allocation. Network edges are peer→observed transaction. ASN and class metadata enrich those peers without asserting origin.

Graph identifiers are content-derived references; display strings redact wallet/TX/IP identifiers. Two raw identifiers can have identical truncated labels while keeping different graph keys; a regression test checks this. The exported queue contains no truth labels. Structured scoreParquets remain local machine-readable artifacts.

TreeSHAP reports positive and negative contributions in the raw tree's log-odds space. Their sum, including the bias, must reconstruct the model margin. They explain model behavior, not causal wrongdoing. The prototype shows actual activity/counterparty facts alongside neighborhood contributions.

## Actual validation

- Independent port:20 checks, 324,395rows, maximum feature difference0.0 and score difference0.0. Empty windows pass. Runtime80.66 seconds for the exhaustive port/SHAP verification, not per-window production latency.
- Three held-out queues: generation and evaluation completed in5.02 seconds, excluding interpreter overhead. Each produced20-leads. Canonical controller-window retrieval for rich address XGBoost increased7→10 across those windows. These are replayed consumed test windows, not new performance confirmation.
- Isolated runtime: copied only four observationParquets and native model/manifest into a temporary directory. Blocked Torch imports with an import hook, copied no ground-truth files, imported no research package, and reproduced the20-lead packet exactly. Runtime2.62 seconds; this is a smoke proof, not full offline installation packaging.
- Python regression:97 passed / 3 existing skips,10 existing MAPIE warnings,54.64 seconds. New production modules and tests pass strict mypy and Ruff. Research scripts have an explicit dynamic-code annotation exemption.
- Browser: Chromium tested selection, SHAP details, SVG graph rendering, JSON export, local queue import, malformed-file rejection and exact import/export roundtrip. Interactions continued with the browser offline; zero external requests and zero page errors. Desktop/mobile screenshots and a graph screenshot were captured and inspected.
- Frontend: TypeScript/build pass. Vite still reports the application's existing large-bundle warning. No full release verification claim is made; the existing API quarantine issue and complete default-stage integration remain pending.

## Run it

From the repository root, using the prepared local environment and saved model artifact:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync \
  python -m chakravyuh.vaani.investigation \
  --normalised data/generated/agency-v2/normalised \
  --model research/bitcoin/results/relational-inference-artifacts/address \
  --start-us 1767617601829851 \
  --end-us 1767666624832117 \
  --output /tmp/chakravyuh-review-queue
```

The output directory must be new. Outputs are `scores.parquet`, `leads.json` and an inference/queue provenance manifest. The environment needs XGBoost 3.2.0 as used by these artifacts, plus the existing NumPy/Polars/SciPy dependencies. This command uses the prepared environment; bundling all Linux installation dependencies and wheels remains a deployment milestone.

Open DRISHTI's **World** screen, then **Open an investigative lead**. The built-in sample is a fixed synthetic window 8. Use **Open evidence queue · JSON** to load the CLI's `leads.json`. The entire packet stays on the local machine. Export preserves the imported packet. Limits are10 MB/file and1–200 leads in the preview.

## A five-minute SIH demonstration

1. Load a prepared metadata capture through the existing intake; show the sealed input record and normalized fields.
2. Open the transaction/address/network graph. Show monetary edges and captured announcement timing as separate evidence relations.
3. Open a model-ranked lead. Show actual activity, positive and countervailing SHAP contributions, and exact input/output amounts.
4. Show the evidence-diverse queue and explain how it avoids spending every review slot on repeated transactions. Present the measured retrieval comparison with its precise unit.
5. Open a second exported queue locally and export its evidence packet. Show the operator/source evidence only where the attribution policy is supported.

This is a concrete prototype story: trained AI, cross-layer correlation, graph evidence, analyst workload, explainability and offline portability. The viewer is already wired to generated packets; fully automatic intake→newengine→activecase routing is the next integration milestone.

## Best next investments

First package this flow from raw intake to active case without manual artifact moves. Then evaluate campaign-level retrieval and false-alert burden across independent seeds and placement/coverage regimes. Improve the queue's answer/no-alert policy separately from its diversity policy. Preserve nominal, moderately challenging and evasive synthetic scenarios under declared presets rather than modifying the generator after observing results.

Use the typed temporal model as a controlled challenger on the same investigator workloads. Move toward HGT/TGN or a hybrid only when it retrieves more useful cases or connects evidence the current model misses. GPU access can support those experiments, but the demonstrated engine already works on CPU.

A competitive submission should show a working investigator experience and measured improvement. Global novelty, top-five placement or an internship cannot be guaranteed from these experiments. The concrete, defensible advantage to build is useful evidence retrieval with reproducible explanations and a smooth offline workflow.

## Artifacts

- Replay: `research/bitcoin/results/relational-inference-replay.json`.
- Portable artifacts: `research/bitcoin/results/relational-inference-artifacts/`.
- Queues and measured replay: `research/bitcoin/results/investigation-demo-v2/`.
- Isolated runtime: `research/bitcoin/results/investigation-stripped-smoke.json`.
- Browser evidence: `research/bitcoin/results/investigation-ui/`.
- Full action history: [experiment journal](EXPERIMENT-JOURNAL.md), `events.jsonl`, historical executed source snapshots and checkpoint manifests.

Additional isolated resource measurement: a repeat exact20-lead packet replay completed in 2.69 seconds, including subprocess inference startup, with 788.8 MiB peak process RSS. It used the same normalised canonical capture and no Torch. This is one observed workload, not a scaling guarantee. The original R44 smoke report is preserved separately.
