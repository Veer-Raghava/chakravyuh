# DEMO-CASES — the leads the walkthrough opens

Chosen from the demo run `data/generated/s10-demo` (seed 42, `--txs 24000`, ~960k capture
rows, 32,781 transactions, 64,114 alerts). Selection is by role, computed from the run at
build time — the top three alerts by rank, plus the highest-ranked alert the tool marks
**not ready to attribute** — so no case id is ever hand-copied and the set survives a
regenerate.

Each case is a signed packet under `data/generated/s10-demo/packets/<alert_id>/`, and every
packet replays byte-identical via `--verify-replay`. The current Merkle head over all four
packets is `2d0906aa…`.

## Case 1 — the flagship attribution · `alw-86c94e363f0f` (rank 1)

The top of the queue. A predicted cluster whose sends carry a coinjoin mark (a high share of
equal-value outputs) and a high count of SHASTRA typology hits; risk **0.994**, conformal
interval flush at the target. The origin estimator names the announcing network address for
its transaction rather than a relay, so the alert is **ready to attribute** and the packet
carries a servable notice. The counter-evidence panel is not empty: it states the benign
reading of both the coinjoin and the fan-out patterns the alert rests on, so the analyst sees
the case against the alert in the same view. This is the "here is a lead we can actually
attribute and serve" beat. Packet signed, Merkle head `ce920ef2…`.

## Case 2 — a second independent lead · `alw-a7177926cc03` (rank 2)

A different cluster, the same morphology: coinjoin-marked, typology-heavy, risk **0.994**,
attributable. It shows the top of the queue is not one lucky hit — the model concentrates
genuinely risky clusters where an investigator looks first. Packet signed, Merkle head
`278c7f12…`.

## Case 3 — a third independent lead · `alw-95f69548c542` (rank 3)

As case 2: an independent cluster, coinjoin-marked and typology-heavy, risk **0.994**,
attributable. Three flagship leads in the top three, each with its own counter-evidence.
Packet signed, Merkle head `3ac7eb5b…`.

## Case 4 — high risk, **not ready** to attribute · `alw-5ca3af6110cf` (rank 17)

The honesty beat. Risk **0.978** — this wallet is near the very top of the queue — and yet
the tool flags it **not ready to attribute**. The reason is in its own evidence: the subject
is a single address that no clustering heuristic linked to anything else. High risk, no
corroborating cluster, so the tool refuses to put a name on a notice and says so on the face
of the alert. Confident about the risk, honest about the limit. Packet signed, Merkle head
`2d0906aa…`.
