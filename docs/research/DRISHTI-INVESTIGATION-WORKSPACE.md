# DRISHTI investigation workspace — R46

This update turns run selection and case selection into shared investigation state. It adds a readable flow atlas alongside the existing JAAL scene, exports actual run artifacts, and makes missing evidence explicit instead of substituting Agency data.

## Demo catalog

The default selector offers three curated demonstrations:

| Demo | Stored run | Purpose | Available outputs |
|---|---|---|---|
| Agency | `agency-v2` | Follow a complete investigation | Capture, normalization, graph, origin, ranked leads, five existing signed packets |
| Stealth | `_sweep-0.10` | Compare sparse network observation | Capture, normalization, graph and origin estimates; no generated alert queue or packet |
| Blind spots | `_sweep-0.02` | Inspect a minimally observed capture | Capture, normalization, graph and origin estimates; no generated alert queue or packet |

“All coverage runs” adds the 5%, 25%, 50%, 60% and 70% sweeps. These are different observation regimes, not eight independently trained models. Historical `s*-demo`, `s*-test`, canonical development runs and chain-only runs stay outside the user-facing catalog. Their stored artifacts remain available for research.

The published data is a build-time export of stored pipeline outputs. Newly generated backend runs appear after export and rebuild; the static console does not monitor the filesystem or launch pipeline jobs. JSON chunks load from the local application server, without an internet service. Run loading keeps the current investigation intact until the next artifact loads, handles loading errors and ignores stale asynchronous selections.

## Shared investigation state

`RunContext` owns the active run, selected transaction and selected alert. Changing a run resets case state and closes the properties drawer. Screens remount for the new run to reset local filters, camera choices and review state. The navigation funnel reads the active run's counts, and completion seals appear only where the run actually has a stage artifact. Navigating between stages closes stale properties.

Selecting a lead carries its actual originating transaction where exported. Moving from Globe into JAAL or SHASTRA preserves the transaction. Selecting a transaction clears a previous alert selection. PRAMAAN resolves a packet only for a matching exported case; it does not silently show the default packet for a different transaction. Missing-stage views offer the map or an explicit return to the featured case.

Partial payloads share a compile-time fixture contract with the baseline. Baseline values complete that contract internally, but stage availability checks block their presentation when an active-run artifact is missing. Globe geography is built from the run's own example cases rather than the currently selected origin override, preventing duplicate point keys when the unresolved case is selected.

## JAAL: two complementary views

### Flow atlas

The new default is a labeled transaction flow, with a searchable transaction index. Network observations occupy the upper band; input and output addresses occupy the lower band. Solid directed paths show value transfer. Dashed paths connect an observed transaction to announcing peers.

The atlas shows exact input and output amounts, transaction time and peer counts. Up to six input addresses, six output addresses and eight peers appear in the compact illustration; the displayed/available counts are printed. A table exposes every focused input and output in integer satoshis. Clicking an output finds later observed spends from the same address, with timestamps strictly after this transaction. Address reuse does not establish which UTXO was spent. Missing subsequent spends are described as absent from this bounded export, not absent from Bitcoin.

The transaction block opens the existing 3D trace. Other controls open the retained spatial graph and the matching origin estimate. “Possible change” is an ownership hypothesis from the graph, not an asserted common owner. The transaction index is a navigable graph index, not the ML alert ranking.

### Complete focused traces

The global graph stays capped for rendering. During implementation we found that this cap can omit transaction endpoints, making an apparent total computed from that scene incomplete. The exporter now reads the stored graph and includes every input edge, output edge and captured announcing-peer edge incident to each selectable transaction. It adds local ASN context and local ownership ties.

Eight operational runs contain **758 focused traces**: 94 for each of seven sweeps, plus 100 for Agency. The independent export verifier compares every focused incident edge with the original stored graph, including amount, timestamp, confidence and evidence fields. This is completeness relative to the stored capture graph, not full Bitcoin network coverage.

The global spatial scene is retained. Its transaction HTML tooltip and wrapper have passive pointer behavior, so hovering an identifier/time label cannot prevent the money block from opening Trace. Browser verification projects actual graph coordinates and clicks the rendered mesh.

## Other screens

- **Globe:** flat circular candidate markers and soft round ambient sprites replace raised/square marks. A country observation index selects real example trails. Arcs group peers reporting the same transaction; they are explicitly not reconstructed transport routes. Coordinates remain country centroids with jitter. Mobile layout gives the planet, index and legend separate rows.
- **KAVACH / Intake:** inspect the selected run's existing capture seal, arithmetic, file hashes and rejected rows. The button describes inspection rather than claiming an uploaded file was ingested.
- **SETU / Untangle:** a new arrival timeline shows observed delays for the selected origin example. Relay observations remain distinct from money transfers.
- **SHASTRA / Origin:** candidate comparison bars show relative lengths, with absolute likelihood percentages printed. The unresolved-example toggle updates shared transaction selection and restores the previous transaction when toggled back.
- **VAANI / Leads:** selecting a row changes the shared case and its featured evidence. Exported full details are available for the leading cases and packet-bearing cases. Other rows retain their real summaries. Cases without origin details are handled without inventing an estimate.
- **PRAMAAN / Proof:** choose between five actual Agency packets, review their existing custody and signature fields, and export JSON. Web Crypto computes the SHA-256 of the exact pretty-printed download bytes. This file fingerprint is separate from the backend's signed/canonical packet hash and Merkle head. Frontend review does not create a new signature.
- **MAYAJAAL / World:** existing coverage charts stay tied to the active run. The graph-context research viewer now offers executed windows 7, 8 and 9. These fixed model-generated research queues remain explicitly separate from the active capture's production queue and metrics. Local queue import/export remains supported.

Sanskrit tags and layer names are larger in navigation and screen headings. Visible loopback-address labels were removed from the application strip, World and login; actual local server binding remains unchanged. Reduced-motion preferences are read before the first render to avoid starting an animation and only disabling it afterward.

## Reproduce

From the repository root:

```bash
UV_CACHE_DIR=/tmp/uv-cache POLARS_MAX_THREADS=4 \
  uv run --offline --no-sync python scripts/export_drishti_runs.py

# Or refresh one run without replacing the other catalog entries:
UV_CACHE_DIR=/tmp/uv-cache POLARS_MAX_THREADS=4 \
  uv run --offline --no-sync python scripts/export_drishti_runs.py --runs agency-v2

npm --prefix apps/drishti-v2 run build

UV_CACHE_DIR=/tmp/uv-cache POLARS_MAX_THREADS=4 \
  uv run --offline --no-sync python research/bitcoin/verify_drishti_exports.py
```

Browser verification uses Playwright/Chromium as temporary development tooling and a local server on port 4183. The deployed application does not depend on Playwright. `verify_drishti_redesign.py` covers run selection, case handoffs, actual mesh clicks, packet fingerprints, all coverage runs, research snapshot selection, offline interactions and mobile overflow. `project_drishti_nodes.cjs` derives mesh click positions from the actual layout and camera geometry.

## Scope and remaining engineering

This is a frontend and artifact-export integration update. It does not replace LightGBM, retrain models, change nominal MAYAJAAL, repair the known API quarantine failure, or complete automatic ingestion into the newer graph-context engine. The research queues are working generated artifacts, not an automatic production-backend switch.

The packaged run chunks are several megabytes before compression. Coverage data loads on demand; Agency is included in the initial bundle. The Vite size warning remains. Later performance work can move large case data into local JSON assets and virtualize the index without changing evidence semantics.

Validation results and artifact identities are recorded in `research/bitcoin/results/drishti-redesign/`. This audit records failures and corrections as well as passing checks. No commits were made.
