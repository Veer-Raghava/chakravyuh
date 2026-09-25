# DEMO-RUN — the precomputed artifact and how to serve it

Everything the demo shows is precomputed and committed to disk. Nothing regenerates live;
regeneration is a failure mode, not a feature, when a projector is waiting.

## The artifact

Run id: **`s10-demo`** at `data/generated/s10-demo/`.

- Produced by: `scripts/make_vendor_lists.py --out vendor/` (one-time, already done),
  then `uv run python -m chakravyuh.mayajaal --out data/generated/s10-demo --txs 4000`,
  then KAVACH → SETU → JAAL → SHASTRA → BUDDHI → VAANI, one command per stage (all
  default flags, `--score` on SHASTRA and BUDDHI).
- Size: ~77k capture rows (csv + jsonl + a 500-row xml sample), 5,285 transactions,
  16,162 alerts, 3 signed packets under `packets/`.
- The vendor tree is populated for this run only: `net_class` is live (residential,
  mobile, vpn_suspect, tor_exit), so SETU enrichment, SHASTRA's Tor abstention and
  BUDDHI's vpn/tor features all exercise their real paths. This is the deployment
  `make verify-s04` does not assert; that gate stays on the empty-vendor world.
- The canonical measured run `s10-canonical` is a different directory and is never
  touched by the demo; `make demo-full` never regenerates it.

## The three cases

`docs/DEMO-CASES.md` names them, with ranks, merkle heads and the beat each one plays:

| beat | alert id | rank |
|---|---|---|
| clean attribution | `alw-02ea801ee567` | 9 |
| Tor abstention | `alw-d2b22e049560` | 19 |
| high-risk, not ready to attribute | `alw-e53cbcbf18dc` | top 8 |

All three packets replay byte-identical via `--verify-replay`.

## Serving the console

```
CHAKRAVYUH_RUN=s10-demo make api       # binds 127.0.0.1:8000, read-only
```

The env var names the run id the API serves; the frontend in `apps/drishti` reads from
it. Serving is inference: the API never reads `ground_truth/`
or `measurements/`, and `test_api.py` proves it boots and serves with the answer key
absent.

## The five beats

1. **The capture is sealed.** Show `data/generated/s10-demo/sealed/manifest.json` and
   `INPUT.sha256`: intake hashed and quarantined anomalies before anything downstream
   ran. One line: "everything after this point is traceable to sealed bytes."
2. **The graph fused itself.** The console's graph view, cluster level. One line: "same
   owner addresses clustered from co-spend and link evidence, every edge carrying its
   confidence."
3. **A wallet is flagged with calibrated doubt.** The alerts queue, case 1
   (`alw-02ea801ee567`) opened. One line: "rank 9, the interval says what the model
   does not know, and the counter-evidence panel is the case against our own alert."
4. **The tool refuses on Tor.** Case 2 (`alw-d2b22e049560`). One line: "high risk on the
   wallet side, and the network side says nothing rather than guess — that refusal is
   the product."
5. **Serve the notice.** Case 3's packet PDF and the BNSS s.94 notice PDF, then
   `--verify-replay` live: the packet regenerates byte-identically. One line: "signed,
   replayable, and legal on the first read."

## Cold-start and reset

- `make demo-full` builds the whole demo artifact from an empty `data/generated/` (it
  regenerates `s10-demo` only; `s10-canonical` must already exist or be rebuilt by
  hand, and the demo never needs it).
- `make demo-reset` wipes and rebuilds `s10-demo` via `demo-full`, so the demo can be
  run repeatedly.
- Offline: no step touches the network. Fonts are vendored for the frontend; the API
  binds loopback only.
