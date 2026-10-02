# R47: readable investigations and executed graph results

Completed 2026-10-02. This is a continuation of R46, preserving its source snapshots and artifact identity.

## Implemented

- JAAL Trace keeps its coins, central transaction block, wire beacons and animated flows. It shows four input addresses, four output addresses and six observed peers per independent page. Every source object remains reachable; displayed totals cover the complete transaction. The large browser case has 18 inputs, three outputs and 34 peers: five input pages and six peer pages passed navigation checks. Opening Trace closes the previous drawer. Camera framing adapts to narrow viewports.
- Removed invented all-to-all ownership lines from the focused diorama. Possible-change labels describe a hypothesis. Full ownership evidence remains available in the atlas and graph.
- VAANI has a bounded queue beside selected evidence, full-width details and inline row selection. It no longer opens a drawer that obscures the same evidence.
- SHASTRA uses a full-width header, fitted maze, paired verdict/first-seen panels, separate benchmark and candidate evidence, and a bounded candidate table. SETU uses parallel money/network panels, a bounded observer list and a two-column arrival trail. Mobile layouts stack and contain table overflow.
- Globe markers retain the small flat visual marks but receive invisible spherical hit targets of radius 0.07 scene units. A real browser click three pixels away from a projected mark opened evidence. Geographic index selection also works after a drag.
- The atlas heading keeps the local display font without italic styling.
- World now explicitly identifies models we actually trained, their protocol and observations. Research results remain separate from active-capture metrics.

## Correctness repair

`api.serialize.origin_estimate` previously selected the earliest and second-earliest announcements as the exported leader and runner-up, while its margin used model rank. This could contradict the probability-sorted table. The serializer now chooses these values by descending likelihood while keeping the shortlist in chronological order. On the illustrated case the runner-up changes from 3.57% to 4.19%; the 22.81% margin then agrees with 27.00% minus 4.19%.

All eight operational frontend exports were refreshed. Original signed packets remain archived bytes, preserving their signatures. A regression checks eight actual transactions, including a witness where announcement order differs from likelihood order.

## Fresh executed graph benchmark

Actual command and report identity are in `research/bitcoin/results/drishti-r47-graph-training/invocation.json`. Four CPU threads, seed42, width32, 60 epochs; separate fitting windows0–3, calibration4–5, validation6 and test7–9. Address mode excludes the ownership ledger entirely. Training seven candidates completed in 26.36 seconds on the available machine. These canonical data were already used in research, so this is an executed replay rather than an untouched generalization test.

| Candidate | Test average precision | Pooled P@20 |
| --- | ---: | ---: |
| mlp | 0.0758 | 0.25 |
| temporal_embeddings_xgboost | 0.2675 | 0.90 |
| typed_static | 0.2602 | 0.80 |
| typed_temporal_gru | 0.2879 | 0.95 |
| typed_temporal_shuffled | 0.0778 | 0.45 |
| xgboost_local | 0.0538 | 0.55 |
| xgboost_typed_features | 0.1902 | 0.60 |

Validation selected `typed_temporal_gru`. It uses typed mean messages and window GRU memory; it is not canonical HGT/TGN/TGAT. Test contains57,105 address-window decisions and295 positives. Its per-window P@20 is .65,1.00,0.00; the last window has no positives. AP for windows7/8 is .2709/.4128, undefined for9. Pooled19/20 does not imply19 distinct controllers. Graph alignment has a useful signal here: shuffled relations reduced AP to .0778. This supports continuing a graph challenger without making production clustering a prerequisite.

## Verification and audit

TypeScript/Vite build passed. Browser report contains13 completed checks, zero page errors and zero external requests, including offline interactions, all operational runs, mesh clicks, complete Trace paging, signed-packet fingerprint equality and mobile layouts. Screenshots were inspected; this inspection led to the additional SETU height cap, maze camera correction and table wrapper. Graph-boundary contracts:4passed. API plus origin regression:27passed, excluding the pre-existing API quarantine test. All758 focused traces were independently compared to stored edges after re-export. Ruff passed for changed Python code; build retains the existing bundle-size warning.

Initial browser verification failed because a broad text locator matched both the caption and candidate heading; narrowed it to the heading. Initial new regression formatting exceeded the repository line limit; formatted and reran lint. These were verification-script issues, recorded rather than hidden. No commits, canonical-data regeneration or production model replacement.
