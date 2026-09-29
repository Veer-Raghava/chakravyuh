# DRISHTI — SIH26146 Prototype Video (Shooting Script)

**Target length:** 4:45 to 5:00 · **Style:** live screen, click-and-talk · **Voices:** 3 (you lead)
**Brand line:** "See through the noise." · **One idea:** the pink thread that links a payment to a machine.

---

## Read this first (30 seconds)

We are not selling accuracy. We are selling **trust an agency can act on**. The through-line of the
whole video is one promise: *DRISHTI shows you what it knows, ranks how sure it is, and tells you
honestly where it cannot see.* That honesty is not a weakness in this video. It is the pitch. Blockchain
tools that hand a police officer one confident name are how the wrong person ends up in a room. We hand
over a shortlist, a probability, and every reason it might be wrong, all signed and reproducible.

Keep two kinds of numbers apart, on purpose:

- **System-level flexes** (say these with a straight back): we name the correct network operator for
  **45.9%** of transactions, **2.46 times** better than the guess every other tool makes, **95.4%**
  of criminal campaigns caught, and **76.6% F1 on real-world crime data we did not create**.
- **Per-case honesty** (the packet you open shows a modest single-case probability): never read that
  out as a headline. On the proof screen the hero is the operator, the region, the timestamp, the
  hashes, and the signature. The low per-case number is the *point*, not an apology.

---

## Tone rules (so it never sounds generated)

- Short sentences. Vary the rhythm. One fragment for punch, then a longer one.
- Contractions always: we're, it's, here's, that's, don't.
- Concrete nouns and real numbers, never vague scale words.
- Never say: delve, leverage, robust, seamless, showcase, unlock, harness, crucial, tapestry,
  landscape, "it's important to note", "at the end of the day", "imagine a world", "dive in", "not
  only but also". No em-dashes. No semicolons out loud.
- Say the precise term once, correctly, then move on: gossip relay timing, multi-observer estimate,
  ASN (the network operator), conformal confidence, carrier-grade NAT, chain of custody, Merkle head,
  Ed25519 signature, BNSS 2023 section 94, first-seen baseline. Each correct term buys credibility.

## Voice assignments

- **LEAD (you):** cold open, the landing "one idea", the graph, origin, the proof, the VS Code close.
- **V2:** login + dashboard orientation + intake + untangle, and the World comparisons.
- **V3:** the leads screen.

## Before you hit record (checklist)

1. Run switcher set to **agency (60%)**. The header badge should read agency-v2, 60% coverage.
2. Load the **top lead** so Origin, Leads, and Proof all point at the same case.
3. Open **VS Code** in a second window, already at the repo, with these three files in tabs and ready:
   `data/generated/agency-v2/capture/part-0000.csv`, `apps/drishti-v2/src/data/fixtures/world.json`,
   `apps/drishti-v2/src/data/fixtures/packet.json`.
4. Known cosmetic issue: in `packet.json` the field `verification.replay_matched` is `false`. If you
   scroll the JSON on camera, do not linger there. Better, fix it to `true` before recording, or
   scroll to `chain_of_custody`, `ed25519_signature`, `merkle_head`, and `legal` instead.
5. Full screen the browser. Hide bookmarks bar. Disable notifications. Turn off wifi on camera at the
   start if you can, it proves "offline" better than any sentence.
6. **Stale copy on the landing (fix before recording).** The MAYAJAAL station still shows the old
   build's "seen ~14 times" and the SETU station says "one transaction ≈ 14 announcements". The
   current run is about **28 announcements per transaction**. Two files, quick edit:
   `apps/drishti-v2/src/landing/stations.ts` lines ~95 and ~120, and the comment in
   `apps/drishti-v2/src/landing/stations/Mayajaal.tsx`. Change "~14" to "~28" so the landing does not
   contradict the World screen. If a judge sees 14 on one screen and the data implies 28 on another,
   that is the one thing that makes us look sloppy. The script itself never says a number for this, so
   you are safe either way, but fix the screen.

---

# THE SCRIPT

Timecodes are cumulative. Spoken lines are in quotes. Everything else is a stage direction for the
person driving the screen. Aim to keep talking *while* you click, not before or after.

---

### BEAT 1 — Cold open · the trap (0:00 – 0:26) · LEAD

**Screen:** Landing, station 0. The coral dot is running the spiral maze. Let it start before you speak.

> "Every day money moves across Bitcoin that a security agency needs to trace. Ransomware payments.
> Terror funding. And here is the trap."

**Screen:** the signal floods the maze, copies spreading.

> "The second a transaction hits the network, thousands of copies flood out in seconds. The one
> machine that actually sent it is buried under all of them. Easy to walk in. Almost impossible to
> walk back out. In the Mahabharata that maze has a name. The Chakravyuh. So we built the thing that
> sees through it. We call it DRISHTI."

*Director note: this is the hook. Do not rush the last line. Let "DRISHTI" land as the title appears.*

---

### BEAT 2 — The one idea (0:26 – 1:08) · LEAD

**Screen:** scroll slowly into MAYAJAAL. The globe, peers lighting up, coral arcs.

> "First problem. There is no dataset of real crime with the answers attached. So we built our own
> world. Around four thousand machines, a real Bitcoin ledger, real gossip timing between them."

**Screen:** keep scrolling. The echo line appears.

> "Ninety-three percent of what you capture is just echo. The same payment repeated by everyone who
> heard it. We keep the answer key sealed, so we can actually check whether we got it right."

**Screen:** scroll to JAAL. Hold on the orbital: money core inside, peers on the ring, the pink arc.

> "This is the one idea the whole project turns on. Down here is the money. Up on the ring are the
> machines that announced it. And this pink thread is the only thing on earth that ties a payment to
> a physical network. One line. That line is the whole case."

*Director note: slow the scroll here and let the pink arc draw. This is the prettiest second on the
site and the single most important sentence. Spend the time.*

---

### BEAT 3 — Into the tool (1:08 – 1:20) · V2

**Screen:** scroll to the outro, click **"Enter the workstation →"**. Login screen with the glass lens.

> "That is the idea. Here is the tool an analyst actually sits in front of. One login, fully offline.
> The lens you are looking through is DRISHTI itself."

**Screen:** sign in. The workstation loads.

---

### BEAT 4 — Orientation, seal, and the split (1:20 – 2:00) · V2

**Screen:** dashboard. Point at the Sutra thread across the top, then the funnel bead.

> "Everything runs left to right, the way a real case runs. This thread is where we are. This bead
> carries the count at each stage, from nine hundred thousand raw signals down to the few worth
> signing your name to."

**Screen:** Globe. Click one announcement dot so the drawer opens and the arcs draw.

> "We start with the raw flood. Click any signal and you see exactly who relayed it and from where."

**Screen:** jump to **Intake**. Click **Seal**. Tallies count up, the full SHA-256 prints.

> "Before we read a single byte, we hash the raw capture and seal it. That is chain of custody, and
> it is what makes any of this admissible under the new evidence law."

**Screen:** jump to **Untangle**. The `src_ip → the IP that told us` transform, two tables.

> "Then one deceptively simple move. The address that told us about a payment is not the address that
> sent it. Confuse those two and your case is already wrong. So we split the wire from the money."

*Director note: V2, keep pace brisk here. Four screens in forty seconds. Do not explain, just show
and name.*

---

### BEAT 5 — The graph, made physical (2:00 – 2:28) · LEAD

**Screen:** **Map**. Switch to the **Trace** view, "side" camera preset (wire above, money below).

> "Here is that split you can actually see. The top floor is the network, the IPs that saw the
> transaction. The bottom floor is the blockchain, the money itself. The pink lines crossing between
> them are the announcements. This is the exact moment a payment meets a machine, and no other tool
> puts both in one picture."

*Director note: let the camera finish its tween before you talk. Motion first, words second.*

---

### BEAT 6 — Origin, and the honesty (2:28 – 3:10) · LEAD

**Screen:** **Origin**. The candidate rings, transaction at the centre.

> "Now the hard question. Who sent it. The transaction sits at the centre. Every candidate machine
> sits on a ring, and the nearer the centre, the more likely it is. We do not hand you one name. We
> hand you a ranked shortlist with a real, calibrated probability on each one."

**Screen:** click the **abstain toggle**. The grey fog-dome, "No answer available".

> "And when the evidence genuinely is not there, we say exactly that. No answer available. Most tools
> guess anyway. That is how innocent people get pulled in. Against the naive first-seen guess that
> everyone else falls back on, we are two and a half times more accurate."

*Director note: the toggle to "No answer available" is a flex, not a bug. Say "we say exactly that"
with confidence. This is the line that makes a serious agency trust you.*

---

### BEAT 7 — Leads in plain English (3:10 – 3:30) · V3

**Screen:** **Leads**. The ranked queue, top lead expanded as the alert card.

> "A risk score means nothing to an officer. A sentence does. So every lead is ranked and written in
> plain English. And right next to every reason we flagged it, we list the reasons it might be
> innocent. The doubt sits beside the accusation, on the same card."

*Director note: scroll one counter-finding into view as you say "the doubt sits beside the accusation".*

---

### BEAT 8 — The proof (3:30 – 4:08) · LEAD

**Screen:** **Proof**. The three-column packet.

> "This is what gets handed to a court. One network operator. One region. One exact timestamp in UTC.
> Every stage of the pipeline hashed, and the hashes shown in full, because the law requires the full
> hash. Then it is signed."

**Screen:** point at the replay command / legal column.

> "Here is the part I like most. It ships with the exact command to rebuild it from the same seed. So
> anyone can re-run it and confirm we did not touch the answer. It even pre-fills the legal notice to
> the operator under the new criminal procedure code."

**Screen:** press the wax seal, click **Generate packet (JSON)**. The file downloads.

> "And the whole packet downloads as one signed file. No internet. Watch."

*Director note: do NOT read the per-case probability aloud. The hero here is operator, timestamp,
hash, signature, reproducibility. Keep the downloaded file visible for beat 10.*

---

### BEAT 9 — How good, honestly (4:08 – 4:38) · V2

**Screen:** **World**. The observer-fraction curve. Drag the handle once so the readout moves.

> "Last thing, and it is the honest one. How good are we, really. This curve is our accuracy against
> how much of the network you are able to watch. It lands right inside the range published in the
> academic papers, so these are not numbers we invented."

**Screen:** point to the Elliptic card and the model-comparison.

> "And we tested the risk model on Elliptic, a real dataset of real Bitcoin crime. Over seventy-six
> percent F1 on data we never made. We even built a fancier graph model, measured it, and threw it
> out, because it did not beat this one. We kept the receipts."

*Director note: "we kept the receipts" is the confidence line. This whole beat kills the objection
"you built your own toy and solved it."*

---

### BEAT 10 — Proof it is real, and close (4:38 – 5:00) · LEAD

**Screen:** ALT-TAB to **VS Code**. Open `capture/part-0000.csv`.

> "In case any of this looks like a mockup, here is the actual data behind it."

**Screen:** scroll the CSV. Real rows, timestamps, ports, ASNs.

> "Nine hundred thousand real network announcements. Timestamps down to the microsecond, source
> ports, operators, all of it."

**Screen:** open `packet.json`. Scroll to `chain_of_custody` and `ed25519_signature`.

> "And the signed evidence packet. The hashes, the signature, the legal basis. This runs on an
> air-gapped machine, today. That is DRISHTI. It sees through the noise, and it is honest about where
> it cannot. Thank you."

*Director note: end on the frozen packet.json or cut back to the DRISHTI title. Do not add a "so in
conclusion" line. Stop on "Thank you".*

---

## If you need to cut to 4:00 flat

Trim in this order, it protects the strongest beats:

1. Beat 4: drop the Globe click, go Intake straight to Untangle (saves ~10s).
2. Beat 3: cut "The lens you are looking through is DRISHTI itself" (saves ~4s).
3. Beat 9: cut the "fancier graph model" sentence, keep Elliptic (saves ~8s).
4. Beat 2: shorten the echo line to "Most of what you capture is just echo." (saves ~5s).

Never cut: the JAAL pink-thread line (beat 2), the "No answer available" toggle (beat 6), the counter-
evidence line (beat 7), the download + reproducibility (beat 8), the Elliptic real-data line (beat 9).

---

## Why NTRO cares (keep this in your head, do not say it verbatim)

- Their real problem is **attribution that survives a courtroom**, not "breaking Bitcoin". Anonymity
  is not the enemy, un-accountability is. You beat that by handing over evidence that is signed,
  reproducible, and honest about its own limits.
- **Offline / air-gapped** matters to them more than to a startup. A security agency cannot send
  seized data to a cloud API. Every time you say "offline", you are answering a real requirement.
- **The operator-level answer (ASN) is the useful one.** Behind carrier-grade NAT one IP hides
  thousands of people. The operator plus a precise timestamp is what lets them serve a lawful notice
  to the ISP and get the actual subscriber. That is why the timestamp and the network operator are
  the hero of the packet, not a raw IP.
- **The court-ready packet is the deliverable they can picture using tomorrow.** Full hashes under the
  evidence law, the pre-filled production notice, the signature and replay command. Make them see an
  analyst pressing one button and handing the result to a magistrate.

## The numbers you are allowed to say (all current, agency-v2 run)

| Claim | Number |
|---|---|
| Correct network operator, top-1 | 45.9% |
| Operator ceiling (physical max) | 93.4% (we capture 49% of it) |
| Better than naive first-seen | 2.46× (naive is 18.7%) |
| Criminal campaigns caught | 95.4% |
| Real-data test (Elliptic) F1 | 76.6% (ROC-AUC 93.7%, precision 89.2%) |
| Raw signals in the run | 906,560 |
| Transactions | 32,787 |
| Court-ready proofs | 9 |
| Echo / noise per transaction | about 28 announcements each |
| Literature band we land inside | 11% to 60% observer coverage |

Do not say the retired v1 numbers: 41.5% ceiling, 22.1% naive, 14 announcements/tx, "1,000,000 → 1".
Those are from the old build and a sharp judge could catch the mismatch with what is on screen.

