# DEMO-CASES — the three cases the live demo walks

Chosen from the demo run `data/generated/s10-demo` (seed 42, `--txs 4000`, 76035 capture
rows, 16,162 alerts, vendor enrichment live). Re-picked at S10 from this run; the S08-era
txids no longer exist in any current run.

Each case is a signed packet under `data/generated/s10-demo/packets/<alert_id>/`
(`packet.json`, `packet.pdf`, `notice.pdf`, `packet.sig`).

## Case 1 — the clean attribution · `alw-02ea801ee567` (rank 9)

An alert whose origin estimate is present, high-margin and anchored: the ensemble answered,
the anchor peer is named, and the counter-evidence is the honest residual doubt (probability
mass shortfall, shared infrastructure) rather than a refusal. This is the "the tool can
actually attribute" beat. Packet signed, merkle head `0ad98437…`.

## Case 2 — the Tor abstention · `alw-d2b22e049560` (rank 19)

The subject's sends were announced through the vendored Tor exit pool (1,000 tor_exit rows
in the run's normalised announcements; the estimator declined on 100% of this subject's
sends). The alert ranks high on wallet risk and the tool still refuses to name a peer, with
the refusal as an explicit counter-evidence row. This is the "the tool would rather say
nothing than guess" beat. Packet signed, merkle head `85253296…`.

## Case 3 — the unattributable high-ranker · `alw-e53cbcbf18dc` (top-8)

A high-severity alert where the estimator answered on some sends but the anchor falls short
of the evidence bar, so `attribution_ready` is false and the counter-evidence names the
shortfall (observed mass below 1.0, low margin). This is the "high risk is not high
certainty" beat. Packet signed, merkle head `e9deebef…`.

## Why these three

They are the three outcomes the product can produce — attributed, refused, unattributable —
and every one ships with signed, replayable evidence (`--verify-replay` is byte-identical on
each). All three alerts exist in the committed demo run; nothing here is generated live.
