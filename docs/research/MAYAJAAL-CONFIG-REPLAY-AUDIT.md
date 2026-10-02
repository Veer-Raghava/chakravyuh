# MAYAJAAL effective-configuration replay audit and fix

Date: 2026-10-01. R24. Actual full-scale diagnosis plus an implementation/regression test.

## Failure discovered during research

The R21 fresh seed-42 chain shared zero TXIDs with the stored agency-v2 capture despite using the same parameter values. That prevented treating it as an observation-only control. We investigated instead of attributing the discrepancy to random difficulty or quietly regenerating the baseline.

The saved effective configuration has the exact hash recorded in the old manifests: `1d6b92ac5d9bd159b2bba76e3d2f66132c2e32aa95f0c3ae64b120d5c8cc2027`. Loading the original `run_config.json` with the recorded agency regime and 24,000 transaction requests gives the **same effective parameter values** as loading the saved effective file. However, the weighted script categories had different iteration orders:

```text
Original JSON: p2wpkh, p2pkh, p2sh, p2tr, p2wsh
Sorted JSON:   p2pkh, p2sh, p2tr, p2wpkh, p2wsh
```

The old `_weights` loader preserved object insertion order. The cumulative weighted sampler maps each seeded random number to an interval/category in that order. Sorting a JSON object does not change its statistical weights, but **does change its seeded sample realization**. Script choices affect address construction, fee/vsize and later UTXO selection, so divergence propagates through the chain.

A full-size generation using the original input order produced **33,849 transactions**, matching the historical capture's chain count. **All 32,787 normalized captured TXIDs** existed in that generation, and **all 318 stored campaign TXIDs** matched. The earlier sorted-effective generation had33,919 transactions and no matching TXIDs. This isolates the configuration-order bug; it was not proof the baseline dataset was arbitrary or irrecoverably corrupted. Counts differ between chain and normalized capture because some transactions are not represented in the capture/accepted normalized observations.

A second replay bug appeared in the new test: `config.load(saved_effective)` ignored its recorded `n_transactions` unless the caller repeated `n_txs`. It computed `target_rows // mean_announcements_per_tx`, restoring37,037 requests from a1,200-request test world. CLI overrides should win when supplied, but saved effective counts must otherwise be honored.

## Implementation

Changed only `src/chakravyuh/mayajaal/config.py`:

1. Parse weighted script categories in a deterministic sorted order, independent of JSON formatting/object insertion order.
2. If no explicit `n_txs` override is supplied, use recorded `n_transactions` when present; ordinary input configurations retain the existing row-budget default.
3. Document these rules at the loader.

No model or existing canonical artifact was rewritten. No campaign distribution, script weight, observation coverage, illicit share or detectability knob was tuned for a detector. The statistical categorical distribution stays unchanged; **seeded output realizations from original unsorted historical input files can change**. This is a simulator recipe change and must be versioned. Historical agency-v2 artifacts remain frozen, and the full-scale matching diagnostic was run before the fix.

The R16–R23 research runners generated from already sorted effective files, so canonicalizing the loader's ordering preserves their script-category order. Their exact executed sources/results stay archived under original hashes. Do not erase older observations merely because the new generator can replay new effective configurations reliably.

## Regression evidence

New `tests/test_mayajaal_config_replay.py`:

- For seeds42/1337, generate a1,200-request/300-entity world from an input configuration, save sorted effective JSON, reload without repeating the transaction-count override, and compare complete chain transactions, population entities, campaign records and P2P network/capture/origins.
- Verify an explicit900-request override wins over a saved1,200-request count.

Before the fix, the new replay test failed for both seeds because the restored count was37,037. Full-scale diagnosis independently demonstrated the order failure with the transaction count explicitly held at24,000. After the fix all three new tests pass; existing chain/network tests pass. Strict mypy and Ruff pass for the loader/test. The broader focused layer run includes these new tests; its exact final count is in the journal.

Primary evidence: `research/bitcoin/results/mayajaal-config-order-replay.json`, `buddhi-seed42-replay-diagnostic.json`, the new tests, and pre-/post-fix source snapshots. No GPU, dependency installation, raw-format dataset export, canonical-world deletion or commit.

## Consequences for future research

An experiment manifest must capture source/module hashes, runtime versions, complete effective configuration, resolved input paths and region/vendor-file hashes, and explicit mapping-order policy. Save a world fingerprint and verify a replay before claiming observation-only comparisons. A git stamp ending `-dirty` plus a seed is insufficient provenance for an exact historical working tree.

The source/capture reloading path still needs explicit relative-file anchoring; the test supplies the repository root, and research runners already do so. Do not assume copying an effective file to a different directory preserves the meaning of `regions.yaml` without an input manifest. The fix establishes seeded replay for identical resolved inputs and tested current code; it does not claim every historical artifact or runtime version has been reconstructed.
