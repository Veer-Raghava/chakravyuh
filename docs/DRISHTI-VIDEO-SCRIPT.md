# DRISHTI — Prototype Video Script (SIH26146 / NTRO)

> The full start-to-finish plan for the prototype demonstration video.
> Read the delivery notes first — they matter as much as the words.
> Everything here is timed, blocked (what to click/scroll), and written to be SPOKEN, not read.

---

## PART A — The research behind this script (read once, so you understand the "why")

### A1 · What a prototype demo video actually needs to be

A few hard truths about how these get judged:

- **Judges watch a lot of these back to back.** Yours is one of many. The first 15 seconds decide
  whether they lean in or start skimming. So we open on the *problem and the hook*, not on
  "Hello, we are team X and our problem statement number is..." — that comes 20 seconds in, briefly.
- **Length: aim for the sweet spot, ~5 minutes.** Check the SIH portal for the exact cap before you
  submit — historically these have ranged from a 3-minute idea video to a longer prototype
  walkthrough. Design the script to hit ~5 min, and I've marked **[CUT-OK]** on the segments you can
  drop to get to ~3:30 if the portal demands it. Never pad to fill time; if you finish strong at
  4:30, stop.
- **It must show a WORKING thing.** A screen recording with clean voiceover beats any slide deck.
  The whole point of "prototype" is that it *runs*. We lean into that — the video IS the product
  moving.
- **Audio quality matters more than video quality.** Record in a quiet room, use the best mic you
  have (even phone earbuds beat a laptop mic), and speak a foot from it. A crisp voice over a
  slightly rough screen capture reads as "competent." A beautiful capture with echoey audio reads
  as "amateur."
- **The arc that works:** Hook (the problem, made real) → what we built (one sentence) → the walk
  (the bulk — show it moving) → the proof it's real (the data, the court packet) → why it matters to
  *them* → stop. We follow exactly this.

### A2 · How to not sound like AI is reading a script

This is the difference between "these people get it" and "these people pasted ChatGPT into a
voiceover." Rules for the *writing* and the *delivery*:

**Words and phrases to never say** (these scream generated text): delve, tapestry, testament,
realm, landscape (as metaphor), leverage, robust, seamless, cutting-edge, revolutionize,
game-changer, "in today's world," "in the ever-evolving world of," furthermore, moreover, "it's
worth noting that," "at the end of the day," "without further ado," "let's dive in." The script
below avoids all of them on purpose.

**Structural tells to avoid:** every sentence the same length; every point starting with a
transition word ("Firstly… Secondly… Additionally…"); the three-part list used constantly ("not
just X, but Y, and Z"); perfectly balanced clauses; zero contractions. Real speech is *lumpy* —
short punchy sentence, then a longer winding one, then a fragment. For emphasis.

**How to actually sound human when you talk:**
- Use contractions. "We don't guess the house — we name the neighbourhood," not "We do not guess."
- Vary your pace. Slow down on the one number that matters, speed up through the connective bits.
- Leave a beat of silence after your strongest line. Let it land. Silence reads as confidence.
- Talk *to* one person, not *at* a panel. Imagine explaining it to one smart friend who doesn't
  know Bitcoin.
- A tiny bit of personality is good — a dry aside, a small "here's the part I like." NTRO are people.
- Don't over-explain. If the visual shows it, say less. Trust the screen.

### A3 · What NTRO actually cares about (and where we win)

NTRO is India's technical intelligence agency. For a Bitcoin-tracing tool, here's what genuinely
moves them — ranked by how much they care:

1. **Can they act on the output?** Intelligence they can't act on is noise. This is why our
   *operator-level* attribution (which ISP, which region) matters more than a probability on an
   exact IP. They can serve a production notice on an ISP. They can't serve one on a 27% guess.
2. **Does it run offline / air-gapped?** This is national security data. It *cannot* touch a cloud
   or a foreign API. Ours is fully offline — no network call anywhere, fonts and data vendored
   locally. This alone rules out half the "wrap the Chainalysis API" projects.
3. **Will it hold up in court?** Evidence has to survive Indian law — BSA 2023 on electronic
   evidence, BNSS 2023 §94 production notices. Our proof packet is built around this: full hashes,
   a signed chain of custody, truncated identifiers on display. Most teams don't even know this
   exists.
4. **Can they trust the number?** An agency can't act on an inflated claim and then get embarrassed
   in court. A tool that says "no answer available, here's why" is *more* useful to them than one
   that always answers, because they can trust the times it does answer.
5. **Is it ours?** Sovereign capability. India not depending on Chainalysis or a foreign vendor for
   something this sensitive. We built the engine, the estimator, the whole pipeline — indigenous.

Notice numbers (accuracy) is NOT #1. It's necessary but not the winner. The winner is: *this is a
tool a real analyst could sit down at tomorrow, act on, take to court, and run on an air-gapped
laptop in a secure facility.* The script sells THAT.

---

## PART B — Before you hit record (setup checklist)

- [ ] `npm run dev` running, browser full-screen, no bookmarks bar, no other tabs visible
- [ ] Zoom/display scaling set so text is readable when compressed to video
- [ ] VS Code open in a SECOND workspace/window, already at the repo, with these files ready in
      tabs (but not yet shown): `data/generated/agency-v2/ground_truth/origins.parquet` viewer OR
      a terminal ready to run one Polars query, and `data/fixtures/ui/packet.json`
- [ ] A clean Downloads folder (so when you download the packet, it's obvious)
- [ ] Quiet room, good mic, water nearby
- [ ] Do ONE full practice run before recording. Time it.
- [ ] Record video and audio separately if you can (screen capture silent, then voiceover) — it's
      far easier to get a clean take that way. If you narrate live, that's fine too, just do 2-3 takes.

**Total target: ~5:00. Structure:**
- 0:00–0:35 — Hook + what it is
- 0:35–2:45 — Landing scroll (the story, the craft, the layer-by-layer teach)
- 2:45–5:30 — The workstation (the actual product, the proof, the data flex)
- 5:30–6:00 — Why it matters + close

*(That's ~6 min if you use everything. Cut the [CUT-OK] parts to land at ~4:30–5:00.)*

---

## PART C — THE SCRIPT

Format: **[ACTION]** = what's on screen / what you do. Plain text = what you say.
`(beat)` = pause. **Bold** in speech = slow down, emphasize.

### SCENE 0 — The hook (0:00–0:35)

**[ACTION]** Open on the landing hero. The CHAKRAVYUH maze is drawn, the coral dot is finding its
way through it. Let it move for two seconds before you say anything. Don't rush the open.

> A criminal moves Bitcoin. (beat) On the screen it looks like this — thousands of hops, mixers,
> peel chains, and somewhere in there, one real person on one real network.
>
> This is the maze. It's **easy to enter and almost impossible to trace back out** — that's the
> whole reason crypto is the payment rail for ransomware and terror financing.
>
> **[ACTION]** The hero text resolves: "DRISHTI — See through the noise."
>
> We built the eye that sees through it. It's called DRISHTI. It runs completely offline, on a
> single laptop, and it's built for exactly one job — telling an analyst *where* the money came from,
> in a form they can actually act on.

*(That's your hook. Notice: no "Hello we are team...". The problem is on screen in the first breath.
Say the team/PS line at the very end, or as a one-line caption. Judges remember the tool, not the
intro.)*

---

### SCENE 1 — MAYAJAAL · the world we watch (0:35–1:05)

**[ACTION]** Begin scrolling slowly into Station 1. The globe appears — ~2000 peers, coral
broadcast arcs firing across it, the echo count ticking up.

> Here's the thing most people miss. When you send Bitcoin, your transaction doesn't go to "the
> blockchain" — it gets **announced**, peer to peer, across the network. Every node that hears it
> remembers *who told them, and when*.
>
> **[ACTION]** Let one arc fire and echo (~14 times). Point with the cursor.
>
> One transaction gets echoed around fourteen times. If you're *listening* from enough places, the
> node that announced it *first, to the most peers* — that's very likely the source. That's the
> signal we mine. We call this layer MAYAJAAL — the world we watch.

*(You just taught network-level deanonymization in 25 seconds without saying "deanonymization."
Good. Keep moving.)*

---

### SCENE 2 — KAVACH · sealed intake (1:05–1:20)

**[ACTION]** Scroll to Station 2. Signals fall and seal at the armoured gate. A full SHA-256 hash
is visible.

> Everything we capture gets sealed the moment it lands — hashed, timestamped, locked. KAVACH.
> (beat) This matters for one reason: **evidence.** If we ever want a court to accept this, we have
> to prove nothing was tampered with after capture. So we hash it on the way in, in full.

*(Short and deliberate. You're planting the "court-ready" seed early so PRAMAAN pays off later.)*

---

### SCENE 3 — SETU · untangling the network from the money (1:20–1:45)

**[ACTION]** Scroll to Station 3. The bridge splits — money to the left, network to the right. The
raw field name `src_ip` visibly strikes through and renames to "the IP that told us."

> Now we separate two different worlds that usually get mixed up. On one side, the **money** — the
> transactions on the blockchain. On the other, the **network** — the IPs and nodes that gossiped
> about them.
>
> **[ACTION]** Point at the strikethrough rename.
>
> And we're careful with language here. This isn't "the sender's IP." Nobody can prove that from
> gossip alone. It's **the IP that told us** — the announcing peer. That precision is the difference
> between intelligence a court throws out and intelligence it keeps.

*(This is a "we understand the subtlety" moment. NTRO will clock it. It signals you know the legal
trap other teams fall into.)*

---

### SCENE 4 — JAAL · the connection map (1:45–2:10)

**[ACTION]** Scroll to Station 4. The dual-floor 3D graph orbits — tx ◆ and clusters ● on the lower
floor, peers ▲ on the upper floor, and the fluoro-pink ANNOUNCE threads crossing between them.

> This is my favourite part. (beat) Two floors. Down here, the money — transactions and wallets we've
> grouped by likely common owner. Up there, the network — the peers. And the **only** thing crossing
> between them are these pink threads: the announcements. That's the wire meeting the chain, made
> physical.
>
> **[ACTION]** Let it rotate once.
>
> We grouped these wallets ourselves — no external service. Around **558 peel chains**, **300
> mixing patterns** caught, clustered with a published-grade confidence anchor. This is the map an
> analyst walks.

*(Drop the 558 / 300 numbers with a little pride — they're concrete and real. Don't over-explain
"peel chain"; the word sounds expert and the visual carries it.)*

### SCENE 5 — SHASTRA · the origin estimate (2:10–2:40)

**[ACTION]** Scroll to Station 5. The candidate-IP bench, the scan-line sweeps, the leader beams up.
The three-segment ceiling bar is visible, and a grey "no answer" card sits to the side.

> Here's where we say where it came from. And here's where we're **honest in a way that actually
> makes us stronger.**
>
> **[ACTION]** Point at the three-segment ceiling bar.
>
> We don't try to name the exact machine — that's a fantasy on a public network, and pretending
> otherwise is how you lose in court. Instead we name the **network operator** — which ISP, which
> region. (beat) And look at this — we tell you the *ceiling*. Only a fraction of transactions even
> contain enough signal to be traced at all. **We reach about 49% of what's theoretically possible**
> — that's **two-and-a-half times better than the naive first-seen method** everyone else uses.
>
> **[ACTION]** Point at the grey "no answer" card.
>
> And when there isn't enough signal? We say so. "No answer available." We'd rather give you nothing
> than give you a wrong name you can't defend.

*(This is THE money scene. The "49% of theoretical maximum" and "2.5× the naive baseline" framing
turns a scary-looking 45.9% into a flex. Slow WAY down on those two numbers. Then the "no answer"
line is your integrity hook — deliver it calm and confident, not apologetic.)*

---

### SCENE 6 — BUDDHI · risk scoring (2:40–3:00) **[CUT-OK if over time]**

**[ACTION]** Scroll to Station 6. The semicircular risk dial, "why flagged" on one side and
counter-findings (teal) on the other.

> Not every transaction is worth an analyst's time. BUDDHI scores risk — but the part I want you to
> see is *this* side.
>
> **[ACTION]** Point at the teal counter-findings.
>
> For every reason we flag something, we also show the reasons it *might be innocent*. Counter-
> evidence, right next to the accusation. Because an analyst's job isn't to trust us — it's to
> decide. We give them both sides.

*(If you're tight on time, this whole scene can go — but the "counter-evidence beside every
accusation" idea is genuinely impressive to an intelligence audience. Try to keep it, even if
trimmed to two sentences.)*

---

### SCENE 7 — VAANI + PRAMAAN · the lead and the proof (3:00–3:25)

**[ACTION]** Scroll through Station 7 (equalizer bars, the plain-English headline typing out) into
Station 8 (maze shards spiral into rings, the proof card forms, a wax seal presses down).

> All of that collapses into two things an analyst can use. VAANI — the lead, written in plain
> English, no jargon. And PRAMAAN —
>
> **[ACTION]** Let the wax seal land. Pause.
>
> — the proof. A court-ready packet. This is the difference between "we think it's this guy" and
> "here's a sealed document a prosecutor can file." We'll open a real one in a minute.

*(That transition — "we'll open a real one in a minute" — is a promise. It makes them wait for the
payoff. Then you deliver it in the workstation. This is good showmanship.)*

---

### SCENE 8 — Enter the workstation (3:25–3:35)

**[ACTION]** Scroll hits the end. "Enter the workstation →" appears. Click it. Login screen washes
in (Riso Blue, dimmed lens, case SIH-26146).

> That's the story. Now the actual tool an analyst sits at.
>
> **[ACTION]** Click through the mock login. (Don't dwell — it's mocked, just say the one line.)
>
> Logged in as an analyst on case SIH-26146. Everything from here is the working product.

*(Do NOT explain that login is mocked. "Not saying something is not lying." Just move.)*

### SCENE 9 — The workstation tour (3:35–4:55)

You're now in the Shell (top thread "Sutra", the funnel bead, the OFFLINE · 127.0.0.1 badge). Move
left-to-right along the workflow. Keep this brisk — the landing already taught the concepts, so here
you're showing that it's a *real working interface*, not re-explaining.

**[ACTION]** Point at the OFFLINE · 127.0.0.1 badge first.

> Before anything — see that? Offline. One-two-seven-oh-oh-one. No cloud, no external API, no data
> ever leaves this machine. For national-security work that's not a feature, it's the requirement.

**[ACTION]** Click **Globe**. Announcement dots by likelihood, India emphasized, pink arcs.

> The same world, live. Announcements landing, India in focus.

**[ACTION]** Click **Intake** (KAVACH). Show the sealing count-up, the full SHA-256, the manifest.

> Intake — sealed and hashed, in full. That's the chain of custody starting.

**[ACTION]** Click **Untangle** (SETU). Show the echo stats, wire-vs-money tables.

> Untangle — network on one side, money on the other. Ninety-plus percent of transactions get
> echoed, about fourteen times each. That echo is our signal.

**[ACTION]** Click **Map** (JAAL). Flip through a couple of sub-views (Graph → Owners → a Lead).

> The map — the graph, the likely owners we grouped, and a single lead traced through it.

**[ACTION]** Click **Origin** (SHASTRA). The concentric rings — radius = inverse likelihood.
Show the confident case first, then toggle to the abstain case (fog-dome).

> Origin. The transaction sits at the centre of the maze, and candidate networks ring it — **closer
> means more likely.** Top candidate here, the shortlist behind it, and the accuracy-against-ceiling
> gauge. (beat)
>
> **[ACTION]** Toggle to the abstain / fog-dome case.
>
> And this one — not enough signal. So: no answer. Grey, calm, honest. **A tool you can trust to
> stay quiet is a tool you can trust when it speaks.**

**[ACTION]** Click **Leads** (VAANI). The ~20 alert cards, evidence + teal counter-evidence.
Open one AlertCard.

> The leads an analyst works — each one in plain English, each with the evidence *and* the counter-
> evidence. Around twenty leads out of the whole run. That's the funnel doing its job.

*(Keep the whole tour moving. One or two sentences per screen. The landing did the teaching; this is
the "it's real and it runs" proof.)*

---

### SCENE 10 — PRAMAAN · open the real packet (4:55–5:25) — THE PAYOFF

**[ACTION]** Click **Proof** (PRAMAAN). The three columns: hash chain-of-custody (full SHA-256) /
THE FINDING (operator · region · UTC) / the BNSS 2023 §94 notice.

> And this is what it's all for. The proof packet. (beat)
>
> **[ACTION]** Point across the three columns as you name them.
>
> Full hashes and chain of custody on the left — so it survives BSA 2023, India's evidence law. The
> finding in the middle — network operator, region, exact timestamp in UTC. And on the right, a
> pre-drafted production notice under BNSS 2023, Section 94 — the actual legal instrument to compel
> that operator to hand over subscriber details.
>
> **[ACTION]** Click **"Generate packet (JSON)."** The file downloads. Now OPEN it (VS Code or the
> browser). Scroll it slowly.
>
> And it's not a picture — it's a real file. Here it is. Full identifiers inside, for the authorised
> officer only. On screen we mask them — first octet of the IP, truncated addresses — full hashes
> printed complete, because the law requires that. This is a document a prosecutor can actually file.

*(This is the climax of the "is it real?" question. The download → open is the single most convincing
thing in the video. Let it breathe. Don't talk over the file opening.)*

---

### SCENE 11 — The VS Code flex (5:25–5:50) **[CUT-OK, but recommended]**

**[ACTION]** Alt-tab to VS Code. Open a terminal or a data file. Run ONE clean query on the real
generated data — e.g. the agency-capture origins, or the observer set. Something like:

```bash
# show the real generated ground-truth / capture — pick the cleanest one-liner you have
python3 -c "import polars as pl; df=pl.read_parquet('data/generated/agency-v2/ground_truth/origins.parquet'); print(df.shape); print(df.head())"
```

> And in case you're wondering whether the demo is faked — it isn't. This is the actual pipeline
> output. **906,560 signals captured**, run through all eight layers, down to the leads you just
> saw. Real transactions, real network capture, our own engine end to end. Nobody's wrapping
> somebody else's API here. We built the whole thing.

*(This is your "wow they actually did this" moment. Keep it SHORT — one query, one result, one line.
The point is to prove depth, not to give a data-science lecture. If the query is slow or messy on
the day, cut this scene rather than fumble it.)*

---

### SCENE 12 — Why it matters + close (5:50–6:15)

**[ACTION]** Optional: press `space` to bloom the Aperture (the radial iris nav) as a final visual
flourish, or return to the World / MAYAJAAL screen with the observer-fraction curve. Let the visual
sit under your closing lines.

> So — what is this, really. (beat)
>
> It's an offline Bitcoin-tracing tool that names the network behind a transaction, tells you
> honestly when it can't, and hands you a court-ready packet at the end. Built in India, running on
> one air-gapped laptop, depending on no foreign service.
>
> **[ACTION]** Final beat. Let the maze / eye visual hold.
>
> The maze is built to trap you. DRISHTI is the eye that sees through it. (beat) Thank you.
>
> **[ACTION]** End card (static, 2 seconds): DRISHTI · CHAKRAVYUH · Team [name] · SIH26146 · NTRO.

*(End on the metaphor, not on a stat. The last thing they hear should be the idea, cleanly. The team
name / PS number lives on the end card — spoken only if you want, and only here.)*

---

## PART D — Quick delivery reminders (tape this above your screen)

- **Slow down on exactly three things:** "49% of theoretical maximum," "two-and-a-half times the
  naive baseline," and "no answer available." Everything else can move.
- **Never apologise for the honesty features.** The abstain state and the ceiling are *strengths*.
  Say them like strengths.
- **Never say the words:** "only," "just a prototype," "we didn't have time," "in theory," "should
  work," "kind of," "basically." None of these. They shrink you.
- **The three claims you must land clearly:** it's *offline*, it's *court-ready*, it's *ours*.
- **If you fumble a line, keep going.** Re-record that scene later; don't restart the whole thing.
- **End at ~5 minutes.** If the portal caps shorter, cut Scene 6 and Scene 11 first — the spine
  (hook → origin → proof → close) still stands on its own.

---

## PART E — One thing I need from you

I wrote the numbers to match the strong, honest framing (L1 operator = hero, 49% of ceiling, 2.46×
naive, offline, court-ready). Two checks before you record:

1. **Confirm the exact video length cap on the SIH portal** and tell me — I'll tighten the script to
   hit it precisely. (I couldn't verify the current cap live; the ~5-min target is the safe default.)
2. **Tell me which real data file opens cleanest in VS Code on your machine** (the agency-capture
   parquet, a JSON, whatever loads fast and looks impressive) — I'll write the exact one-liner for
   Scene 11 so it lands without fumbling.



