# DEMO-SCRIPT — the run of show, keystroke by keystroke

Five beats, one spoken sentence each. Everything is served from the precomputed
`s10-demo`; nothing regenerates. If a projector is waiting and you find yourself
regenerating data, stop — that is the failure this script exists to prevent.

Read `docs/DEMO-RUN.md` for what the artifact is and `docs/DEMO-CASES.md` for why these
cases. This file is only the choreography.

## Before the room fills

```bash
make demo
```

This serves the precomputed run and starts nothing you have to wait on:

- API on `http://127.0.0.1:8000` (loopback, read-only, `CHAKRAVYUH_RUN=s10-demo`).
- Console on `http://127.0.0.1:5173` (`VITE_SOURCE=api`, reads the API).

`make demo` prints `demo-smoke: attached API on :8000 healthy in <t>s` once the API is
serving — that line is your go signal. Open `http://127.0.0.1:5173/` and leave it on the
landing screen. Do **not** run `make demo-full` in front of the room; that rebuilds.

The case handles, memorised:

| beat | alert id |
|---|---|
| flagship attribution | `alw-86c94e363f0f` |
| high-risk, not ready | `alw-5ca3af6110cf` |

## Beat 1 — the capture is sealed

Keystrokes: open the **Seal** screen from the console rail (or, on the terminal,
`make peek P=data/generated/s10-demo/sealed/manifest.json`).

> "Everything after this point is traceable to sealed bytes — intake hashed the capture and
> quarantined the anomalies before any analysis ran."

## Beat 2 — the graph fused itself

Keystrokes: open the **Graph** screen, cluster level.

> "Same-owner addresses clustered from co-spend and link evidence, and every edge carries
> the confidence it was drawn with."

## Beat 3 — a wallet flagged with calibrated doubt

Keystrokes: open the **Alerts** queue, click the rank-1 alert `alw-86c94e363f0f`.

> "Top of the queue — risk 0.99 with a conformal interval that says what the model does not
> know, and the counter-evidence panel is the case against our own alert."

## Beat 4 — the tool says when it is not ready

Keystrokes: back to the queue, open `alw-5ca3af6110cf` (rank 17).

> "High wallet risk, and yet the tool flags it not ready to attribute — a lone address no
> cluster corroborates. Confident about the risk, honest that it cannot yet name it on a
> notice. That restraint is the product."

## Beat 5 — serve the notice

Keystrokes: open `alw-86c94e363f0f`, open its packet PDF and the BNSS s.94 notice PDF from
`data/generated/s10-demo/packets/alw-86c94e363f0f/`. The packet carries its signature
(`packet.sig`) and merkle head; state that it is signed and replayable from the sealed
inputs (the replay property is proven in the gate, not run live in front of the room).

> "Signed, replayable, and legal on the first read — the packet re-derives byte-identical
> from the sealed inputs."

## Running it a second time

Nothing accumulates state: the API is read-only and the console reloads from it on every
route. To reset to beat one, just reopen `http://127.0.0.1:5173/`.

```bash
make demo-reset
```

confirms the servers are still up and tells you the beat-one URL. You do not restart
anything between run-throughs. Ctrl-C in the `make demo` terminal tears both servers down.
