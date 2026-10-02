# Submission sources, claims and provenance

Retrieved/reviewed 2 October 2026. Sources have different evidentiary roles. “Found online” is not sufficient to establish a national rubric or a model result. The copies, URLs, byte hashes and download failures are recorded under `research/bitcoin/results/submission-audit/sources/`.

## Selection and presentation sources

| Source | Role | What can be used | Limits |
| --- | --- | --- | --- |
| [Current official SIH FAQ](https://www.sih.gov.in/faqs) | Primary current administrative page | Online idea screening, offline finale; team/SPOC process | Does not provide judging percentages or prove judges ignore videos |
| [Official legacy College SPOC PDF](https://sih.gov.in/letters/Guidelines-College-SPOC.pdf) | Primary historical guidance | Qualitative selection dimensions | Visible text is 2024; do not silently relabel current; direct download returned 403 |
| [Official 2020 idea process](https://www.sih.gov.in/pdf/IdeasubmissionprocessSIH2020.pdf) | Historical primary field/process context | Title, description and presentation explain a proposal | Not a current deadline/weight/format authority; download returned 403 |
| [DSCE 2026 institutional portal](https://sih.dsce.in/sih) | Current institution source | Links to official 2026 template/guidelines | Its internal admission rules are not national weights |
| [New official 2026 guidelines URL](https://sih.gov.in/letters/SIH2026-Guidelines-College-SPOC.pdf) | Primary URL located through institution | Final authority if available through SPOC | 403 in this review; mirrored text mixes some year/date labels, so no deadline assertion |
| [New official 2026 template URL](https://www.sih.gov.in/letters/2026/SIH2026-IDEA-Presentation-Format.pptx) | Primary URL located through institution | Final template authority | 403 here; downloaded matching archive PDF and examined it |
| [Archive template/decks](https://github.com/DgrnBoi/SIH-Past-PPTS-2024) | Actual artifacts downloaded and rendered | Six-section presentation structure; example information hierarchy | Individual “winner” labels not independently confirmed |
| [Solar Masters institution account](https://www.spsu.ac.in/innovation-meets-excellence-solar-masters-winning-journey-at-smart-india-hackathon-2024/) | Primary institution winner story | Concrete presentation/prototype preparation example | Not evidence that a particular slide style causes winning |
| [Title/description/abstract guide mirror](https://www.scribd.com/document/929246520/SMART-INDIA-HACKATHON-IDEA-Submission-Guidelines-for-Students) | Corroborative mirror | Matches user-supplied 100/50,000/10,000 limits | Authenticated portal limits remain to be checked by submitter |
| [NN/G concise/scannable/objective study](https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/) | Primary usability research | Plain, concise and objective editorial principles | Historical web-reading study, not SIH jury research |
| [NN/G plain language for experts](https://www.nngroup.com/articles/plain-language-experts/) | Primary usability guidance | Technical expertise does not require inflated prose | No selection probability inferred |

Unofficial SIH-lookalike Vercel pages, coaching advice and public anecdotes were considered but not used to invent a national scoring table or a promise that evaluators never open supplementary links. The actual problem statement is the supplied `docs/reference/SIH26146.pdf`; no classified NTRO objectives were inferred.

## Technical references relevant to this deck

- [Weber et al., 2019, Bitcoin AML with graph convolutional networks](https://arxiv.org/abs/1908.02591): external transaction-classification context; not proof of our origin/IP recovery.
- [Elliptic++ multi-input graph dataset paper](https://arxiv.org/abs/2306.06108): richer graph benchmarking context; not our own dataset or deployed architecture.
- [Müller et al., 2026, multi-input reliability](https://arxiv.org/abs/2607.07414): ownership uncertainty context; reported cluster precision is not our per-edge probability.
- [Maganti, 2026, temporal-shift GNN re-evaluation](https://arxiv.org/abs/2604.19514): a preprint motivating evaluation controls; not consensus SOTA or our measured result. Page comments say code will be released despite the abstract's stronger availability wording.
- [Angelopoulos and Bates, conformal prediction introduction](https://arxiv.org/abs/2107.07511): prediction sets and their assumptions; not a justification for calling a heuristic score band a probability interval.

Use a few references with clear relevance, rather than a long unexplained citation list. Existing project literature reports contain additional primary papers; no borrowed paper metric is a replacement for a local experiment.

## Claim register

| Claim | Supporting local artifact / source | Allowed wording |
| --- | --- | --- |
| Default AML model is 33-feature LightGBM | `buddhi/features.py`, `model.py`, `stage.py` | “Default pipeline uses LightGBM” |
| Optional rich engine uses 329 inputs | `relational_inference.py`; native artifact manifests | “Working optional CPU graph-context engine” |
| Rich address AP .3148 vs local .0538 | Address/uncertainty and investigative-engine reports; saved same-protocol results | Synthetic future-window comparison, not universal performance |
| Queue retrieval 11→33 / 9→16 | Frozen rich-tree diversity transfer in address research | Suspicious controller-window retrieval across three windows; not distinct people |
| 324,395 exact-replay rows / 20 checks | `relational-inference-replay.json` | Independent port matches features and scores on checked cases |
| 2.69 s / 788.8 MiB | Stripped runtime resource replay recorded in investigative-engine report | One tested 20-lead workload; not full-app or arbitrary-scale guarantee |
| Neural graph models trained | Saved weights/scores; R47 graph-training report | Custom typed graph + window GRU; not canonical HGT/TGN/TGAT |
| Offline browser interactions | R47 UI report | Zero external requests during checks; not already bundled clean-host installer |
| Signed case artifacts | PRAMAAN source and archived packet byte/signature checks | Integrity/replay artifacts, not automatic court admissibility |
| Every stage release gate passes | Full test run shows one existing API quarantine failure | **Do not claim** |
| Product identifies sender/person or proves absence | No reliable validated policy | **Do not claim** |
| Dependencies already vendored into Docker image | No verified shipped image/bundle | **Do not claim** |
| 500 competitors / top-five result / internship | User ambition, no verified outcome | A goal, not a factual result or guarantee |

The descriptions select relevant strengths and need not list every negative experiment. Any specific performance/capability assertion must retain the status, target and unit necessary to understand it.

## 2 October update: public benchmark and exploratory blend

The revised portal abstracts/descriptions include graph-feature LightGBM Elliptic AP .6566 and pooled 20/20 positives from `research/bitcoin/results/elliptic-graph-benchmark.json`. This is a separate public-data experiment (11,184 labeled test transactions, 636 illicit), not a synthetic or default-engine performance claim. The research description additionally cites the validation-selected saved-score blend AP .3381 and 128 positives within 500 pooled reviews from `research/bitcoin/results/ranking-recovery-analysis/report.json`. The blend uses 75% rich address XGBoost and 25% R47 temporal GNN; no new model weights were trained, and the test was previously consumed. Full context: [ranking recovery and blend report](../research/RANKING-RECOVERY-AND-TREE-GNN-BLEND.md).
