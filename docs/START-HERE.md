# CHAKRAVYUH · START HERE

Two documents in this pack are for you to read. This one, and `SESSIONS.md`.
Everything else is written for Claude Code to read, not you. You will still understand
the project completely, because every build session ends by writing a short plain
English entry into `docs/EXPLAIN.md`. That file becomes your answer sheet.

---

## 1. Your dataset question, answered straight

**No, NTRO is not giving you a dataset.** The problem statement says `Dataset Link: Nil`
and `YouTube Link: Nil`. It also says the data *is* synthetic and describes the exact
fields it will contain. Read those two facts together and the situation is clear:

- They have told you the **shape** of the input, not supplied the input.
- At the grand finale a sponsor sometimes hands over a file on day one. You cannot
  plan around that, and you cannot demo without data before then.
- So the dataset is **ours to build**, and that is not a workaround. It is the only
  way to measure whether origin estimation works at all, because measuring it needs
  ground truth about who really sent each transaction, and no public dataset has that.

This is standard practice in exactly our field, not a hack. IBM's AML team built
AMLSim and released the AMLworld datasets for anti money laundering research, and
their paper argues that synthetic data is *better* than real data for benchmarking,
because the ground truth labels are complete while most real laundering is never
detected and therefore never labelled. Tide, published 2026, is another open source
generator built on the same reasoning. We are doing the accepted thing.

**The one rule that makes this safe:** our generator writes the PS field names exactly.
If someone hands us a real file at the finale, the loader takes it with no code change.
The generator is a source of test data, never a dependency of the product.

Since you sent the figshare and *Nature* links, this plan got better. Section 8 has the
revised version: real data for the transaction half, generated data only for the network
half. Read section 8 before you start S01.


---

## 2. What we are building, in five sentences

A capture file gives us rows of Bitcoin network traffic joined to transaction data.
The same transaction appears in many rows because Bitcoin gossips, so most of the IPs
we see are forwarders, not senders. We estimate, per transaction, which announcing
peer was the real originator, and we put a calibrated probability on it. We then rank
wallets by laundering risk, and every flag is stored with its cause, its confidence,
and the strongest argument against it. The output is an evidence packet an officer can
actually send to an ISP, hashed the way Indian evidence law now requires.

---

## 3. How the repo is organised, and why

```
chakravyuh/
  CLAUDE.md                 always in Claude's context. Kept short on purpose.
  STATE.md                  where the project is right now. Claude reads this first.
  SESSIONS.md               what to type each session, and why. Your day to day file.
  Makefile                  every command you will ever run
  docs/
    PROBLEM-STATEMENT.md    the PS, plus our reading of it
    ARCHITECTURE.md         the eight stages and what each one owns
    DATA-CONTRACTS.md       every schema, field by field. FROZEN.
    STAGE-BRIEFS.md         all twelve briefs in one file. S00 splits it into stages/
    DECISIONS.md            every real choice, with the reason and what we rejected
    EXPLAIN.md              plain English, written at the end of every session
    stages/S00..S11.md      one brief per session, split out of STAGE-BRIEFS.md
    MAYAJAAL-SPEC.md        the data generator design
    DRISHTI-SPEC.md         the frontend design, down to the pixel rules
    FEATURES.md             written at S07. Every model feature in plain English
    PERF.md                 written at S10. Per stage timings on your machine
    DEMO-CASES.md           written at S06 and S08. The three txids the demo uses
    DEMO-SCRIPT.md          written at S11. Five beats, keystrokes, what you say
  .claude/
    settings.json           permissions, so it stops asking you every time
    commands/               /stage /verify /handoff /explain /yourturn
    agents/                 three subagents that check work in a fresh context
  src/chakravyuh/
    kavach/ setu/ jaal/ shastra/ buddhi/ vaani/ pramaan/ mayajaal/
  apps/drishti/             the React frontend. Owned by the parallel track.
  data/
    fixtures/               tiny committed sample data. The contract made real.
    generated/              gitignored. Big files live here.
  scripts/peek.py           the only approved way to look at a data file
  tests/
```

Two things in that tree are load bearing and everything else follows from them.

**`docs/DATA-CONTRACTS.md` is frozen.** It defines the exact columns each stage reads
and writes. Once it exists, two people can build different stages at the same time
without ever touching the same file. A hook in `.claude/settings.json` blocks Claude
from editing it. If a contract genuinely needs to change, you change it yourself, on
purpose, and you tell both tracks.

**`data/fixtures/` holds tiny golden files** matching the contract, maybe two hundred
rows. Every stage can be built and tested against fixtures before the real generator
is finished. This is what lets the frontend start on day one instead of waiting.

---

## 4. The six rules that stop Claude going in circles

You said the model circles around and wastes tokens. That happens for one reason:
the session had no finish line it could test. Everything below is a fix for that.

**Rule 1. One session, one stage, one testable finish line.**
Every stage brief ends with a shell command. The session is over when that command
prints green. Not when the code "looks done". If the command does not exist yet, the
first thing the session does is write it.

**Rule 2. Plan before code, every time.**
First message of every session ends with "plan first, do not write code yet". You read
the plan, you approve or correct it, then you say go. This costs you ninety seconds and
saves entire sessions. Press Shift+Tab twice to enter plan mode if you prefer that.

**Rule 3. Name the files. Ban the wandering.**
The prompts in `SESSIONS.md` say `read @STATE.md and @docs/stages/S04-setu.md, read
nothing else yet`. Unprompted codebase exploration is the single biggest token sink in
a repo this size.

**Rule 4. Two strikes and it stops.**
`CLAUDE.md` tells Claude that if the same approach fails twice, it must stop, write what
it learned into `STATE.md`, and ask you. No third attempt at the same idea. This is the
exact rule that kills the circling.

**Rule 5. Never print data. Use `scripts/peek.py`.**
One `print(df.head(50))` of a thirty column frame can eat thousands of tokens and teach
you nothing. `peek.py` prints a fixed compact summary: row count, columns with types,
three truncated sample rows, null counts. `CLAUDE.md` bans ad hoc data printing.

**Rule 6. `/clear` between stages. Never mid stage.**
Start each stage with a clean context. Inside a stage, keep it. If you must compact
mid stage, run `/handoff` first so `STATE.md` holds the facts, then `/clear` and reload
from `STATE.md`. That is a cheaper and more reliable reset than `/compact`.

---

## 5. Making it stop asking you, without going full auto

You described exactly the setting you want and it exists. Claude Code has permission
modes, and rules are evaluated **deny first, then ask, then allow**, with the first
match winning. So the setup you want is:

- `defaultMode: "acceptEdits"` so file edits and ordinary file commands inside the
  project run without a prompt.
- An **allow list** naming the commands this project actually uses: `pytest`, `uv run`,
  `make`, `git status`, `git commit`, `npm run` and so on. Those go silent too.
- A **deny list** for the things that can hurt you: `rm -rf`, `git push`, `git reset
  --hard`, `git clean`, `sudo`. Deny wins over everything, including permissive modes,
  so this is a real seatbelt and not a suggestion.
- Anything not on either list still prompts. That is the behaviour you want: quiet for
  the hundred things you already trust, and a visible question for anything new.

Do **not** use `bypassPermissions`. It is the mode where a bad `rm` in a generated
script takes your `data/generated` directory with it, and you will not see it happen.

The ready made file is in `claude-config/settings.json` in this pack. Copy it to
`.claude/settings.json` in the repo. Run `/permissions` once inside a session to see the
live config and confirm it loaded. If Claude Code reports an unknown key, move
`defaultMode` up one level to the top of the JSON object and re run `/permissions`.
Nothing else in the file depends on where that key sits.

One more thing worth knowing: `curl` and `wget` are deliberately on neither list, so
they prompt. This project claims to run air gapped, and every download should be a
decision you consciously made. When you do download something, it goes into `vendor/`
and its SHA-256 goes into `vendor/MANIFEST.sha256`. That habit costs nothing now and
becomes a slide later.

---

## 6. Build order

No dates anywhere. This is a dependency order. Each row is one Claude Code session,
sometimes two if it fights you. Do them in this order because each one needs the one
above it, not because of any calendar.

| # | Stage | What exists at the end that did not before |
|---|---|---|
| S00 | Skeleton and contracts | `make verify` runs. Fixtures exist. Nothing else does. |
| S01 | MAYAJAAL chain layer | A valid UTXO ledger with entities, wallets, and labelled bad actors |
| S02 | MAYAJAAL network layer | Gossip announcements from a partial observer, in the PS row schema |
| S03 | KAVACH intake and seal | Any CSV, JSON or XML in that shape loads, hashes, and is sealed |
| S04 | SETU normalise and enrich | Geo and ASN attached, announcements separated from transactions |
| S05 | JAAL fused graph | One graph holding both layers, with clustering that reports confidence |
| S06 | SHASTRA origin estimator | **The idea.** P(originator) per announcing peer, measured against truth |
| S07 | BUDDHI models | LightGBM baseline, conformal calibration, time ordered evaluation |
| S08 | VAANI explanation | Every alert carries cause, confidence, and counter evidence |
| S09 | PRAMAAN evidence packet | Signed packet, Merkle log, pre filled BNSS notice, replayable |
| S10 | Scale | One million rows end to end, with timings you can quote |
| S11 | Demo hardening | One command, precomputed artifacts, and a fallback for everything |

Two notes on this table.

**S06 is the session that matters.** S00 to S05 are plumbing. Good plumbing, and the
deck needs it, but any competent team builds it. S06 is the part nobody else has. If you
have limited attention on any single day, spend it there.

**S10 and S11 are not optional polish.** A demo that takes ninety seconds to load in
front of judges has already lost. S11 exists so that the thing you show is precomputed,
instant, and has a working fallback if the laptop misbehaves.

The deck has an eight week gated timeline on Slide 4. That is for the evaluators, who
want to see that you can plan. It is not your build schedule. Do not let the two get
confused.

---

## 7. The parallel track, so a teammate is never blocked

The frontend is the thing that makes non technical people lean forward, and it sits at
the end of the data flow. If you build it last you will run out of attention. So it
does not wait.

**Track A is yours.** `src/chakravyuh/**`, `tests/**`, `docs/stages/**`.
**Track B is your teammate's.** `apps/drishti/**` and nothing else.

Track B starts the moment S00 is finished, because after S00 the fixtures exist. The
frontend is built against `data/fixtures/` through a single adapter file, so it renders
real looking screens before any real pipeline exists. When S04 lands, one adapter file
changes and the same screens fill with real data.

They never touch the same files, so `git` never asks either of you to resolve anything.
If you want it airtight, use a git worktree so both of you have a separate working copy
of the same repo:

```
git worktree add ../chakravyuh-ui stage/drishti
```

Rules for the boundary, and they are short. Track B may read `docs/DATA-CONTRACTS.md`
and `docs/DRISHTI-SPEC.md`. Track B may not edit anything under `src/`. If Track B needs
a field that does not exist, they open an entry in `docs/DECISIONS.md` and you decide.
Nobody edits the contract on their own.

One more parallel job that needs no coding skill and pays off enormously: whoever is on
the deck can be filling the six slides from the PPT pack at the same time, using screens
from Track B as they appear. Real screenshots on Slide 3 beat any diagram.

---

## 8. The dataset decision, and why the links your group sent change it

Your group found something genuinely useful. That figshare record is the data behind a
peer reviewed paper in *Nature Scientific Data*, "Bitcoin Research with a Transaction
Graph Dataset" (also arXiv 2411.10325). It holds **252 million nodes and 785 million
edges** across roughly thirteen years and about **670 million transactions**, every node
and edge timestamped, plus two labelled subsets, one of about **34,000 labelled nodes**.
Nodes are Bitcoin users, meaning already clustered address groups, and edges are
transactions between them. There is a sibling dataset called ORBITAAL, also in *Nature
Scientific Data*, covering 2009 to 2021 as entity to entity temporal graphs.

Now read that against our problem. Those datasets are the **chain layer** and nothing
else. No IP address, no port, no announcement time, no peer identity. That absence is
not an oversight in their work, it is the exact gap our whole idea sits in, and it is
why the deck can honestly say no public dataset carries both layers.

So the right call is a hybrid, and it is better than what I had planned:

**Use real data for the chain layer. Synthesise only the network layer.**

- The chain half comes from a real Bitcoin transaction graph slice. Real topology, real
  value distributions, real timing, real entity labels. We do not have to invent any of
  it, and we cannot get it wrong.
- The network half is generated by MAYAJAAL: peers, IPs, ASNs, geography, gossip
  announcements with per peer randomised delays, and a partial observer. This is the
  half that does not exist anywhere, so generating it is the only option available to
  anyone, including NTRO.
- Ground truth about the true originator comes from the generator, because the
  generator is the only thing that knows it.

Why this is the stronger design, in one sentence: the worst attack on a fully synthetic
benchmark is "you invented the data and then solved your own invention", and this design
answers it, because the half we did not invent is real and peer reviewed.

### So MAYAJAAL gets two modes, and the same output shape from both

```
mayajaal --source synthetic  --txs 100000 --seed 42 --out data/generated/run-A
mayajaal --source real-slice --graph vendor/btc-graph/ --txs 100000 --out data/generated/run-B
```

Identical columns out of both. Identical ground truth files out of both. Nothing
downstream knows or cares which mode produced its input.

Both modes exist for a reason and neither is a spare tyre.

**Synthetic mode is the workhorse.** It runs offline forever, has no licence question,
scales to any size, and is the only mode where you can dial a knob and ask what happens.
You need that to write the honest numbers on Slide 4. You cannot ask a real dataset
"what if the observer only sees 5% of the network", but you can ask the generator.

**Real slice mode is the credibility mode.** It is how you say, at the finale, that the
origin estimator was measured on real Bitcoin transaction topology and not only on your
own simulator. That sentence is worth a great deal and it costs one ingestion adapter.

Three things to be careful about, and I would rather say them now than have them bite:

1. **Check the licence before you ship anything.** Figshare records are usually CC BY but
   you must read the record's own licence line and record it in `docs/DECISIONS.md` with
   the date you checked. If it is not clearly redistributable, we use it locally for
   measurement and we ship only synthetic data in the repo.
2. **The full dataset is far too big for a laptop demo.** Do not try to load it. S01 has
   an explicit sampling step: pick a time window, pick a seed set of labelled entities,
   take a bounded neighbourhood around them, stop at a target transaction count.
3. **Never let the real slice become a dependency.** `make demo` must work with the
   network cable unplugged and `vendor/` empty. Synthetic mode is the default in every
   Makefile target for exactly this reason.

### The one number that explains the whole dataset

One row is **one announcement of one transaction by one peer**, not one transaction. The
chain columns repeat across every row that announces the same TXID. With a mean of nine
announcing peers, a **one million row capture is only about 111,000 transactions**. The
other 889,000 rows are echo.

Hold on to that number, because it is the entire pitch in arithmetic form. A tool that
treats a million rows as a million facts is wrong about 89% of its input. Say that
sentence in the demo and in the viva. It lands every time.

---

## 9. What "done" means, and how you check it without reading code

Every stage has three gates. You can check all three in under two minutes and none of
them require you to read a diff.

**Gate 1, the machine gate.** `make verify-sNN` exits zero. Claude is not allowed to call
a stage finished before this passes, and the command is written into the stage brief
before any code is written, so it cannot be quietly redefined later.

**Gate 2, the your hands gate.** Every stage brief ends with a short "your turn" block:
three commands for you to run and two values for you to change and re run. Doing it takes
five minutes and it is the difference between owning this project and hosting it. Run
`/yourturn` if the block is not in front of you.

**Gate 3, the explain gate.** Run `/explain`. Claude appends fifteen lines or fewer to
`docs/EXPLAIN.md` covering what the stage does, why it exists, the one design choice
inside it, and the honest limitation. Plain words, no jargon it has not already defined.
If you read that entry and cannot repeat it back in your own words, the stage is not done
and you should say so in the session rather than move on.

`docs/EXPLAIN.md` is the document you revise before the internal hackathon. By S11 it is
about twelve short entries and it covers everything anyone can ask you.

---

## 10. The demo, five beats

The demo is the deck executed. The five beats are the five verdict lines from the slides,
in order. That coherence is deliberate. When the thing on screen says exactly what the
slide said, a room stops evaluating you and starts believing you.

**Beat 1. This is one million rows and here is its fingerprint.**
Show the sealed input: row count, file hash, ingest time. Three seconds, no commentary.

**Beat 2. Most of it is echo.**
One million rows, 111,000 transactions. The screen collapses the pile into the real count
in front of them. This is where a non technical person first understands the problem.

**Beat 3. Nine peers announced this transaction. Only one sent it.**
The origin view. Eight thin grey beams, one thick orange beam, `p = 0.87` on it, and the
runner up shown underneath. This is the beat the whole project exists for. Do not rush it,
do not talk over it, and let someone in the room ask "how do you know" before you answer.

**Beat 4. Twenty leads, ranked, each with the case against it.**
The queue. Click the top lead. Cause, confidence, counter evidence, all on one screen.
Then click a mining pool that scored high and show the tool clearing it by itself.

**Beat 5. This is what an officer sends.**
The evidence packet. Public IP, source port, exact UTC timestamp, the hash, the pre
filled production notice. Then close the laptop lid, or turn off the wifi and re run it,
and say the one line: nothing left this machine.

Rehearse it as five beats, not as a feature tour. Six minutes total. Every feature that
does not serve a beat gets shown only if someone asks.

---

## 11. Your first thirty minutes

Do these in order and stop when the last one prints green. Nothing here needs a decision
from you.

1. Make an empty repo called `chakravyuh`, `git init`, and open it in Claude Code.
2. Copy this pack's `claude-config/settings.json` to `.claude/settings.json`, and the
   `commands/` and `agents/` folders to `.claude/commands/` and `.claude/agents/`.
3. Copy `CLAUDE.md`, `STATE.md` and `SESSIONS.md` to the repo root, and `ARCHITECTURE.md`,
   `DATA-CONTRACTS.md`, `STAGE-BRIEFS.md`, `MAYAJAAL-SPEC.md` and `DRISHTI-SPEC.md` into
   `docs/`. Rename `00-START-HERE.md` to `docs/START-HERE.md` so it travels with the project.
4. Copy `SIH26146.pdf` and the PPT build pack into `docs/reference/`.
5. Start a session, run `/permissions`, confirm the allow list loaded.
6. Open `SESSIONS.md`, read "The ritual, every single time", go to session S00, and paste
   prompt 1.

That is it. From there `SESSIONS.md` runs the project and this file is just the thing you
come back to when you want to remember why something is the way it is.

---

## 12. Two habits that will decide how this goes

**Read the plan, always.** The ninety seconds you spend reading the plan in plan mode is
the highest leverage time in this entire project. It is where you catch a wrong idea
before it becomes four hundred lines of code and an hour of your attention.

**When something feels vague, say so immediately.** Not later. The moment a session
produces something you cannot explain in your own words, stop and ask "explain this to me
in plain words and tell me what would break it". You already predicted that you would need
to do this. You will be right more often than you expect, because the person who is
confused about an explanation is very often looking at an explanation that is hiding
something.# CHAKRAVYUH · START HERE

Two documents in this pack are for you to read. This one, and `SESSIONS.md`.
Everything else is written for Claude Code to read, not you. You will still understand
the project completely, because every build session ends by writing a short plain
English entry into `docs/EXPLAIN.md`. That file becomes your answer sheet.

---

## 1. Your dataset question, answered straight

**No, NTRO is not giving you a dataset.** The problem statement says `Dataset Link: Nil`
and `YouTube Link: Nil`. It also says the data *is* synthetic and describes the exact
fields it will contain. Read those two facts together and the situation is clear:

- They have told you the **shape** of the input, not supplied the input.
- At the grand finale a sponsor sometimes hands over a file on day one. You cannot
  plan around that, and you cannot demo without data before then.
- So the dataset is **ours to build**, and that is not a workaround. It is the only
  way to measure whether origin estimation works at all, because measuring it needs
  ground truth about who really sent each transaction, and no public dataset has that.

This is standard practice in exactly our field, not a hack. IBM's AML team built
AMLSim and released the AMLworld datasets for anti money laundering research, and
their paper argues that synthetic data is *better* than real data for benchmarking,
because the ground truth labels are complete while most real laundering is never
detected and therefore never labelled. Tide, published 2026, is another open source
generator built on the same reasoning. We are doing the accepted thing.

**The one rule that makes this safe:** our generator writes the PS field names exactly.
If someone hands us a real file at the finale, the loader takes it with no code change.
The generator is a source of test data, never a dependency of the product.

Since you sent the figshare and *Nature* links, this plan got better. Section 8 has the
revised version: real data for the transaction half, generated data only for the network
half. Read section 8 before you start S01.


---

## 2. What we are building, in five sentences

A capture file gives us rows of Bitcoin network traffic joined to transaction data.
The same transaction appears in many rows because Bitcoin gossips, so most of the IPs
we see are forwarders, not senders. We estimate, per transaction, which announcing
peer was the real originator, and we put a calibrated probability on it. We then rank
wallets by laundering risk, and every flag is stored with its cause, its confidence,
and the strongest argument against it. The output is an evidence packet an officer can
actually send to an ISP, hashed the way Indian evidence law now requires.

---

## 3. How the repo is organised, and why

```
chakravyuh/
  CLAUDE.md                 always in Claude's context. Kept short on purpose.
  STATE.md                  where the project is right now. Claude reads this first.
  SESSIONS.md               what to type each session, and why. Your day to day file.
  Makefile                  every command you will ever run
  docs/
    PROBLEM-STATEMENT.md    the PS, plus our reading of it
    ARCHITECTURE.md         the eight stages and what each one owns
    DATA-CONTRACTS.md       every schema, field by field. FROZEN.
    STAGE-BRIEFS.md         all twelve briefs in one file. S00 splits it into stages/
    DECISIONS.md            every real choice, with the reason and what we rejected
    EXPLAIN.md              plain English, written at the end of every session
    stages/S00..S11.md      one brief per session, split out of STAGE-BRIEFS.md
    MAYAJAAL-SPEC.md        the data generator design
    DRISHTI-SPEC.md         the frontend design, down to the pixel rules
    FEATURES.md             written at S07. Every model feature in plain English
    PERF.md                 written at S10. Per stage timings on your machine
    DEMO-CASES.md           written at S06 and S08. The three txids the demo uses
    DEMO-SCRIPT.md          written at S11. Five beats, keystrokes, what you say
  .claude/
    settings.json           permissions, so it stops asking you every time
    commands/               /stage /verify /handoff /explain /yourturn
    agents/                 three subagents that check work in a fresh context
  src/chakravyuh/
    kavach/ setu/ jaal/ shastra/ buddhi/ vaani/ pramaan/ mayajaal/
  apps/drishti/             the React frontend. Owned by the parallel track.
  data/
    fixtures/               tiny committed sample data. The contract made real.
    generated/              gitignored. Big files live here.
  scripts/peek.py           the only approved way to look at a data file
  tests/
```

Two things in that tree are load bearing and everything else follows from them.

**`docs/DATA-CONTRACTS.md` is frozen.** It defines the exact columns each stage reads
and writes. Once it exists, two people can build different stages at the same time
without ever touching the same file. A hook in `.claude/settings.json` blocks Claude
from editing it. If a contract genuinely needs to change, you change it yourself, on
purpose, and you tell both tracks.

**`data/fixtures/` holds tiny golden files** matching the contract, maybe two hundred
rows. Every stage can be built and tested against fixtures before the real generator
is finished. This is what lets the frontend start on day one instead of waiting.

---

## 4. The six rules that stop Claude going in circles

You said the model circles around and wastes tokens. That happens for one reason:
the session had no finish line it could test. Everything below is a fix for that.

**Rule 1. One session, one stage, one testable finish line.**
Every stage brief ends with a shell command. The session is over when that command
prints green. Not when the code "looks done". If the command does not exist yet, the
first thing the session does is write it.

**Rule 2. Plan before code, every time.**
First message of every session ends with "plan first, do not write code yet". You read
the plan, you approve or correct it, then you say go. This costs you ninety seconds and
saves entire sessions. Press Shift+Tab twice to enter plan mode if you prefer that.

**Rule 3. Name the files. Ban the wandering.**
The prompts in `SESSIONS.md` say `read @STATE.md and @docs/stages/S04-setu.md, read
nothing else yet`. Unprompted codebase exploration is the single biggest token sink in
a repo this size.

**Rule 4. Two strikes and it stops.**
`CLAUDE.md` tells Claude that if the same approach fails twice, it must stop, write what
it learned into `STATE.md`, and ask you. No third attempt at the same idea. This is the
exact rule that kills the circling.

**Rule 5. Never print data. Use `scripts/peek.py`.**
One `print(df.head(50))` of a thirty column frame can eat thousands of tokens and teach
you nothing. `peek.py` prints a fixed compact summary: row count, columns with types,
three truncated sample rows, null counts. `CLAUDE.md` bans ad hoc data printing.

**Rule 6. `/clear` between stages. Never mid stage.**
Start each stage with a clean context. Inside a stage, keep it. If you must compact
mid stage, run `/handoff` first so `STATE.md` holds the facts, then `/clear` and reload
from `STATE.md`. That is a cheaper and more reliable reset than `/compact`.

---

## 5. Making it stop asking you, without going full auto

You described exactly the setting you want and it exists. Claude Code has permission
modes, and rules are evaluated **deny first, then ask, then allow**, with the first
match winning. So the setup you want is:

- `defaultMode: "acceptEdits"` so file edits and ordinary file commands inside the
  project run without a prompt.
- An **allow list** naming the commands this project actually uses: `pytest`, `uv run`,
  `make`, `git status`, `git commit`, `npm run` and so on. Those go silent too.
- A **deny list** for the things that can hurt you: `rm -rf`, `git push`, `git reset
  --hard`, `git clean`, `sudo`. Deny wins over everything, including permissive modes,
  so this is a real seatbelt and not a suggestion.
- Anything not on either list still prompts. That is the behaviour you want: quiet for
  the hundred things you already trust, and a visible question for anything new.

Do **not** use `bypassPermissions`. It is the mode where a bad `rm` in a generated
script takes your `data/generated` directory with it, and you will not see it happen.

The ready made file is in `claude-config/settings.json` in this pack. Copy it to
`.claude/settings.json` in the repo. Run `/permissions` once inside a session to see the
live config and confirm it loaded. If Claude Code reports an unknown key, move
`defaultMode` up one level to the top of the JSON object and re run `/permissions`.
Nothing else in the file depends on where that key sits.

One more thing worth knowing: `curl` and `wget` are deliberately on neither list, so
they prompt. This project claims to run air gapped, and every download should be a
decision you consciously made. When you do download something, it goes into `vendor/`
and its SHA-256 goes into `vendor/MANIFEST.sha256`. That habit costs nothing now and
becomes a slide later.

---

## 6. Build order

No dates anywhere. This is a dependency order. Each row is one Claude Code session,
sometimes two if it fights you. Do them in this order because each one needs the one
above it, not because of any calendar.

| # | Stage | What exists at the end that did not before |
|---|---|---|
| S00 | Skeleton and contracts | `make verify` runs. Fixtures exist. Nothing else does. |
| S01 | MAYAJAAL chain layer | A valid UTXO ledger with entities, wallets, and labelled bad actors |
| S02 | MAYAJAAL network layer | Gossip announcements from a partial observer, in the PS row schema |
| S03 | KAVACH intake and seal | Any CSV, JSON or XML in that shape loads, hashes, and is sealed |
| S04 | SETU normalise and enrich | Geo and ASN attached, announcements separated from transactions |
| S05 | JAAL fused graph | One graph holding both layers, with clustering that reports confidence |
| S06 | SHASTRA origin estimator | **The idea.** P(originator) per announcing peer, measured against truth |
| S07 | BUDDHI models | LightGBM baseline, conformal calibration, time ordered evaluation |
| S08 | VAANI explanation | Every alert carries cause, confidence, and counter evidence |
| S09 | PRAMAAN evidence packet | Signed packet, Merkle log, pre filled BNSS notice, replayable |
| S10 | Scale | One million rows end to end, with timings you can quote |
| S11 | Demo hardening | One command, precomputed artifacts, and a fallback for everything |

Two notes on this table.

**S06 is the session that matters.** S00 to S05 are plumbing. Good plumbing, and the
deck needs it, but any competent team builds it. S06 is the part nobody else has. If you
have limited attention on any single day, spend it there.

**S10 and S11 are not optional polish.** A demo that takes ninety seconds to load in
front of judges has already lost. S11 exists so that the thing you show is precomputed,
instant, and has a working fallback if the laptop misbehaves.

The deck has an eight week gated timeline on Slide 4. That is for the evaluators, who
want to see that you can plan. It is not your build schedule. Do not let the two get
confused.

---

## 7. The parallel track, so a teammate is never blocked

The frontend is the thing that makes non technical people lean forward, and it sits at
the end of the data flow. If you build it last you will run out of attention. So it
does not wait.

**Track A is yours.** `src/chakravyuh/**`, `tests/**`, `docs/stages/**`.
**Track B is your teammate's.** `apps/drishti/**` and nothing else.

Track B starts the moment S00 is finished, because after S00 the fixtures exist. The
frontend is built against `data/fixtures/` through a single adapter file, so it renders
real looking screens before any real pipeline exists. When S04 lands, one adapter file
changes and the same screens fill with real data.

They never touch the same files, so `git` never asks either of you to resolve anything.
If you want it airtight, use a git worktree so both of you have a separate working copy
of the same repo:

```
git worktree add ../chakravyuh-ui stage/drishti
```

Rules for the boundary, and they are short. Track B may read `docs/DATA-CONTRACTS.md`
and `docs/DRISHTI-SPEC.md`. Track B may not edit anything under `src/`. If Track B needs
a field that does not exist, they open an entry in `docs/DECISIONS.md` and you decide.
Nobody edits the contract on their own.

One more parallel job that needs no coding skill and pays off enormously: whoever is on
the deck can be filling the six slides from the PPT pack at the same time, using screens
from Track B as they appear. Real screenshots on Slide 3 beat any diagram.

---

## 8. The dataset decision, and why the links your group sent change it

Your group found something genuinely useful. That figshare record is the data behind a
peer reviewed paper in *Nature Scientific Data*, "Bitcoin Research with a Transaction
Graph Dataset" (also arXiv 2411.10325). It holds **252 million nodes and 785 million
edges** across roughly thirteen years and about **670 million transactions**, every node
and edge timestamped, plus two labelled subsets, one of about **34,000 labelled nodes**.
Nodes are Bitcoin users, meaning already clustered address groups, and edges are
transactions between them. There is a sibling dataset called ORBITAAL, also in *Nature
Scientific Data*, covering 2009 to 2021 as entity to entity temporal graphs.

Now read that against our problem. Those datasets are the **chain layer** and nothing
else. No IP address, no port, no announcement time, no peer identity. That absence is
not an oversight in their work, it is the exact gap our whole idea sits in, and it is
why the deck can honestly say no public dataset carries both layers.

So the right call is a hybrid, and it is better than what I had planned:

**Use real data for the chain layer. Synthesise only the network layer.**

- The chain half comes from a real Bitcoin transaction graph slice. Real topology, real
  value distributions, real timing, real entity labels. We do not have to invent any of
  it, and we cannot get it wrong.
- The network half is generated by MAYAJAAL: peers, IPs, ASNs, geography, gossip
  announcements with per peer randomised delays, and a partial observer. This is the
  half that does not exist anywhere, so generating it is the only option available to
  anyone, including NTRO.
- Ground truth about the true originator comes from the generator, because the
  generator is the only thing that knows it.

Why this is the stronger design, in one sentence: the worst attack on a fully synthetic
benchmark is "you invented the data and then solved your own invention", and this design
answers it, because the half we did not invent is real and peer reviewed.

### So MAYAJAAL gets two modes, and the same output shape from both

```
mayajaal --source synthetic  --txs 100000 --seed 42 --out data/generated/run-A
mayajaal --source real-slice --graph vendor/btc-graph/ --txs 100000 --out data/generated/run-B
```

Identical columns out of both. Identical ground truth files out of both. Nothing
downstream knows or cares which mode produced its input.

Both modes exist for a reason and neither is a spare tyre.

**Synthetic mode is the workhorse.** It runs offline forever, has no licence question,
scales to any size, and is the only mode where you can dial a knob and ask what happens.
You need that to write the honest numbers on Slide 4. You cannot ask a real dataset
"what if the observer only sees 5% of the network", but you can ask the generator.

**Real slice mode is the credibility mode.** It is how you say, at the finale, that the
origin estimator was measured on real Bitcoin transaction topology and not only on your
own simulator. That sentence is worth a great deal and it costs one ingestion adapter.

Three things to be careful about, and I would rather say them now than have them bite:

1. **Check the licence before you ship anything.** Figshare records are usually CC BY but
   you must read the record's own licence line and record it in `docs/DECISIONS.md` with
   the date you checked. If it is not clearly redistributable, we use it locally for
   measurement and we ship only synthetic data in the repo.
2. **The full dataset is far too big for a laptop demo.** Do not try to load it. S01 has
   an explicit sampling step: pick a time window, pick a seed set of labelled entities,
   take a bounded neighbourhood around them, stop at a target transaction count.
3. **Never let the real slice become a dependency.** `make demo` must work with the
   network cable unplugged and `vendor/` empty. Synthetic mode is the default in every
   Makefile target for exactly this reason.

### The one number that explains the whole dataset

One row is **one announcement of one transaction by one peer**, not one transaction. The
chain columns repeat across every row that announces the same TXID. With a mean of nine
announcing peers, a **one million row capture is only about 111,000 transactions**. The
other 889,000 rows are echo.

Hold on to that number, because it is the entire pitch in arithmetic form. A tool that
treats a million rows as a million facts is wrong about 89% of its input. Say that
sentence in the demo and in the viva. It lands every time.

---

## 9. What "done" means, and how you check it without reading code

Every stage has three gates. You can check all three in under two minutes and none of
them require you to read a diff.

**Gate 1, the machine gate.** `make verify-sNN` exits zero. Claude is not allowed to call
a stage finished before this passes, and the command is written into the stage brief
before any code is written, so it cannot be quietly redefined later.

**Gate 2, the your hands gate.** Every stage brief ends with a short "your turn" block:
three commands for you to run and two values for you to change and re run. Doing it takes
five minutes and it is the difference between owning this project and hosting it. Run
`/yourturn` if the block is not in front of you.

**Gate 3, the explain gate.** Run `/explain`. Claude appends fifteen lines or fewer to
`docs/EXPLAIN.md` covering what the stage does, why it exists, the one design choice
inside it, and the honest limitation. Plain words, no jargon it has not already defined.
If you read that entry and cannot repeat it back in your own words, the stage is not done
and you should say so in the session rather than move on.

`docs/EXPLAIN.md` is the document you revise before the internal hackathon. By S11 it is
about twelve short entries and it covers everything anyone can ask you.

---

## 10. The demo, five beats

The demo is the deck executed. The five beats are the five verdict lines from the slides,
in order. That coherence is deliberate. When the thing on screen says exactly what the
slide said, a room stops evaluating you and starts believing you.

**Beat 1. This is one million rows and here is its fingerprint.**
Show the sealed input: row count, file hash, ingest time. Three seconds, no commentary.

**Beat 2. Most of it is echo.**
One million rows, 111,000 transactions. The screen collapses the pile into the real count
in front of them. This is where a non technical person first understands the problem.

**Beat 3. Nine peers announced this transaction. Only one sent it.**
The origin view. Eight thin grey beams, one thick orange beam, `p = 0.87` on it, and the
runner up shown underneath. This is the beat the whole project exists for. Do not rush it,
do not talk over it, and let someone in the room ask "how do you know" before you answer.

**Beat 4. Twenty leads, ranked, each with the case against it.**
The queue. Click the top lead. Cause, confidence, counter evidence, all on one screen.
Then click a mining pool that scored high and show the tool clearing it by itself.

**Beat 5. This is what an officer sends.**
The evidence packet. Public IP, source port, exact UTC timestamp, the hash, the pre
filled production notice. Then close the laptop lid, or turn off the wifi and re run it,
and say the one line: nothing left this machine.

Rehearse it as five beats, not as a feature tour. Six minutes total. Every feature that
does not serve a beat gets shown only if someone asks.

---

## 11. Your first thirty minutes

Do these in order and stop when the last one prints green. Nothing here needs a decision
from you.

1. Make an empty repo called `chakravyuh`, `git init`, and open it in Claude Code.
2. Copy this pack's `claude-config/settings.json` to `.claude/settings.json`, and the
   `commands/` and `agents/` folders to `.claude/commands/` and `.claude/agents/`.
3. Copy `CLAUDE.md`, `STATE.md` and `SESSIONS.md` to the repo root, and `ARCHITECTURE.md`,
   `DATA-CONTRACTS.md`, `STAGE-BRIEFS.md`, `MAYAJAAL-SPEC.md` and `DRISHTI-SPEC.md` into
   `docs/`. Rename `00-START-HERE.md` to `docs/START-HERE.md` so it travels with the project.
4. Copy `SIH26146.pdf` and the PPT build pack into `docs/reference/`.
5. Start a session, run `/permissions`, confirm the allow list loaded.
6. Open `SESSIONS.md`, read "The ritual, every single time", go to session S00, and paste
   prompt 1.

That is it. From there `SESSIONS.md` runs the project and this file is just the thing you
come back to when you want to remember why something is the way it is.

---

## 12. Two habits that will decide how this goes

**Read the plan, always.** The ninety seconds you spend reading the plan in plan mode is
the highest leverage time in this entire project. It is where you catch a wrong idea
before it becomes four hundred lines of code and an hour of your attention.

**When something feels vague, say so immediately.** Not later. The moment a session
produces something you cannot explain in your own words, stop and ask "explain this to me
in plain words and tell me what would break it". You already predicted that you would need
to do this. You will be right more often than you expect, because the person who is
confused about an explanation is very often looking at an explanation that is hiding
something.# CHAKRAVYUH · START HERE

Two documents in this pack are for you to read. This one, and `SESSIONS.md`.
Everything else is written for Claude Code to read, not you. You will still understand
the project completely, because every build session ends by writing a short plain
English entry into `docs/EXPLAIN.md`. That file becomes your answer sheet.

---

## 1. Your dataset question, answered straight

**No, NTRO is not giving you a dataset.** The problem statement says `Dataset Link: Nil`
and `YouTube Link: Nil`. It also says the data *is* synthetic and describes the exact
fields it will contain. Read those two facts together and the situation is clear:

- They have told you the **shape** of the input, not supplied the input.
- At the grand finale a sponsor sometimes hands over a file on day one. You cannot
  plan around that, and you cannot demo without data before then.
- So the dataset is **ours to build**, and that is not a workaround. It is the only
  way to measure whether origin estimation works at all, because measuring it needs
  ground truth about who really sent each transaction, and no public dataset has that.

This is standard practice in exactly our field, not a hack. IBM's AML team built
AMLSim and released the AMLworld datasets for anti money laundering research, and
their paper argues that synthetic data is *better* than real data for benchmarking,
because the ground truth labels are complete while most real laundering is never
detected and therefore never labelled. Tide, published 2026, is another open source
generator built on the same reasoning. We are doing the accepted thing.

**The one rule that makes this safe:** our generator writes the PS field names exactly.
If someone hands us a real file at the finale, the loader takes it with no code change.
The generator is a source of test data, never a dependency of the product.

Since you sent the figshare and *Nature* links, this plan got better. Section 8 has the
revised version: real data for the transaction half, generated data only for the network
half. Read section 8 before you start S01.


---

## 2. What we are building, in five sentences

A capture file gives us rows of Bitcoin network traffic joined to transaction data.
The same transaction appears in many rows because Bitcoin gossips, so most of the IPs
we see are forwarders, not senders. We estimate, per transaction, which announcing
peer was the real originator, and we put a calibrated probability on it. We then rank
wallets by laundering risk, and every flag is stored with its cause, its confidence,
and the strongest argument against it. The output is an evidence packet an officer can
actually send to an ISP, hashed the way Indian evidence law now requires.

---

## 3. How the repo is organised, and why

```
chakravyuh/
  CLAUDE.md                 always in Claude's context. Kept short on purpose.
  STATE.md                  where the project is right now. Claude reads this first.
  SESSIONS.md               what to type each session, and why. Your day to day file.
  Makefile                  every command you will ever run
  docs/
    PROBLEM-STATEMENT.md    the PS, plus our reading of it
    ARCHITECTURE.md         the eight stages and what each one owns
    DATA-CONTRACTS.md       every schema, field by field. FROZEN.
    STAGE-BRIEFS.md         all twelve briefs in one file. S00 splits it into stages/
    DECISIONS.md            every real choice, with the reason and what we rejected
    EXPLAIN.md              plain English, written at the end of every session
    stages/S00..S11.md      one brief per session, split out of STAGE-BRIEFS.md
    MAYAJAAL-SPEC.md        the data generator design
    DRISHTI-SPEC.md         the frontend design, down to the pixel rules
    FEATURES.md             written at S07. Every model feature in plain English
    PERF.md                 written at S10. Per stage timings on your machine
    DEMO-CASES.md           written at S06 and S08. The three txids the demo uses
    DEMO-SCRIPT.md          written at S11. Five beats, keystrokes, what you say
  .claude/
    settings.json           permissions, so it stops asking you every time
    commands/               /stage /verify /handoff /explain /yourturn
    agents/                 three subagents that check work in a fresh context
  src/chakravyuh/
    kavach/ setu/ jaal/ shastra/ buddhi/ vaani/ pramaan/ mayajaal/
  apps/drishti/             the React frontend. Owned by the parallel track.
  data/
    fixtures/               tiny committed sample data. The contract made real.
    generated/              gitignored. Big files live here.
  scripts/peek.py           the only approved way to look at a data file
  tests/
```

Two things in that tree are load bearing and everything else follows from them.

**`docs/DATA-CONTRACTS.md` is frozen.** It defines the exact columns each stage reads
and writes. Once it exists, two people can build different stages at the same time
without ever touching the same file. A hook in `.claude/settings.json` blocks Claude
from editing it. If a contract genuinely needs to change, you change it yourself, on
purpose, and you tell both tracks.

**`data/fixtures/` holds tiny golden files** matching the contract, maybe two hundred
rows. Every stage can be built and tested against fixtures before the real generator
is finished. This is what lets the frontend start on day one instead of waiting.

---

## 4. The six rules that stop Claude going in circles

You said the model circles around and wastes tokens. That happens for one reason:
the session had no finish line it could test. Everything below is a fix for that.

**Rule 1. One session, one stage, one testable finish line.**
Every stage brief ends with a shell command. The session is over when that command
prints green. Not when the code "looks done". If the command does not exist yet, the
first thing the session does is write it.

**Rule 2. Plan before code, every time.**
First message of every session ends with "plan first, do not write code yet". You read
the plan, you approve or correct it, then you say go. This costs you ninety seconds and
saves entire sessions. Press Shift+Tab twice to enter plan mode if you prefer that.

**Rule 3. Name the files. Ban the wandering.**
The prompts in `SESSIONS.md` say `read @STATE.md and @docs/stages/S04-setu.md, read
nothing else yet`. Unprompted codebase exploration is the single biggest token sink in
a repo this size.

**Rule 4. Two strikes and it stops.**
`CLAUDE.md` tells Claude that if the same approach fails twice, it must stop, write what
it learned into `STATE.md`, and ask you. No third attempt at the same idea. This is the
exact rule that kills the circling.

**Rule 5. Never print data. Use `scripts/peek.py`.**
One `print(df.head(50))` of a thirty column frame can eat thousands of tokens and teach
you nothing. `peek.py` prints a fixed compact summary: row count, columns with types,
three truncated sample rows, null counts. `CLAUDE.md` bans ad hoc data printing.

**Rule 6. `/clear` between stages. Never mid stage.**
Start each stage with a clean context. Inside a stage, keep it. If you must compact
mid stage, run `/handoff` first so `STATE.md` holds the facts, then `/clear` and reload
from `STATE.md`. That is a cheaper and more reliable reset than `/compact`.

---

## 5. Making it stop asking you, without going full auto

You described exactly the setting you want and it exists. Claude Code has permission
modes, and rules are evaluated **deny first, then ask, then allow**, with the first
match winning. So the setup you want is:

- `defaultMode: "acceptEdits"` so file edits and ordinary file commands inside the
  project run without a prompt.
- An **allow list** naming the commands this project actually uses: `pytest`, `uv run`,
  `make`, `git status`, `git commit`, `npm run` and so on. Those go silent too.
- A **deny list** for the things that can hurt you: `rm -rf`, `git push`, `git reset
  --hard`, `git clean`, `sudo`. Deny wins over everything, including permissive modes,
  so this is a real seatbelt and not a suggestion.
- Anything not on either list still prompts. That is the behaviour you want: quiet for
  the hundred things you already trust, and a visible question for anything new.

Do **not** use `bypassPermissions`. It is the mode where a bad `rm` in a generated
script takes your `data/generated` directory with it, and you will not see it happen.

The ready made file is in `claude-config/settings.json` in this pack. Copy it to
`.claude/settings.json` in the repo. Run `/permissions` once inside a session to see the
live config and confirm it loaded. If Claude Code reports an unknown key, move
`defaultMode` up one level to the top of the JSON object and re run `/permissions`.
Nothing else in the file depends on where that key sits.

One more thing worth knowing: `curl` and `wget` are deliberately on neither list, so
they prompt. This project claims to run air gapped, and every download should be a
decision you consciously made. When you do download something, it goes into `vendor/`
and its SHA-256 goes into `vendor/MANIFEST.sha256`. That habit costs nothing now and
becomes a slide later.

---

## 6. Build order

No dates anywhere. This is a dependency order. Each row is one Claude Code session,
sometimes two if it fights you. Do them in this order because each one needs the one
above it, not because of any calendar.

| # | Stage | What exists at the end that did not before |
|---|---|---|
| S00 | Skeleton and contracts | `make verify` runs. Fixtures exist. Nothing else does. |
| S01 | MAYAJAAL chain layer | A valid UTXO ledger with entities, wallets, and labelled bad actors |
| S02 | MAYAJAAL network layer | Gossip announcements from a partial observer, in the PS row schema |
| S03 | KAVACH intake and seal | Any CSV, JSON or XML in that shape loads, hashes, and is sealed |
| S04 | SETU normalise and enrich | Geo and ASN attached, announcements separated from transactions |
| S05 | JAAL fused graph | One graph holding both layers, with clustering that reports confidence |
| S06 | SHASTRA origin estimator | **The idea.** P(originator) per announcing peer, measured against truth |
| S07 | BUDDHI models | LightGBM baseline, conformal calibration, time ordered evaluation |
| S08 | VAANI explanation | Every alert carries cause, confidence, and counter evidence |
| S09 | PRAMAAN evidence packet | Signed packet, Merkle log, pre filled BNSS notice, replayable |
| S10 | Scale | One million rows end to end, with timings you can quote |
| S11 | Demo hardening | One command, precomputed artifacts, and a fallback for everything |

Two notes on this table.

**S06 is the session that matters.** S00 to S05 are plumbing. Good plumbing, and the
deck needs it, but any competent team builds it. S06 is the part nobody else has. If you
have limited attention on any single day, spend it there.

**S10 and S11 are not optional polish.** A demo that takes ninety seconds to load in
front of judges has already lost. S11 exists so that the thing you show is precomputed,
instant, and has a working fallback if the laptop misbehaves.

The deck has an eight week gated timeline on Slide 4. That is for the evaluators, who
want to see that you can plan. It is not your build schedule. Do not let the two get
confused.

---

## 7. The parallel track, so a teammate is never blocked

The frontend is the thing that makes non technical people lean forward, and it sits at
the end of the data flow. If you build it last you will run out of attention. So it
does not wait.

**Track A is yours.** `src/chakravyuh/**`, `tests/**`, `docs/stages/**`.
**Track B is your teammate's.** `apps/drishti/**` and nothing else.

Track B starts the moment S00 is finished, because after S00 the fixtures exist. The
frontend is built against `data/fixtures/` through a single adapter file, so it renders
real looking screens before any real pipeline exists. When S04 lands, one adapter file
changes and the same screens fill with real data.

They never touch the same files, so `git` never asks either of you to resolve anything.
If you want it airtight, use a git worktree so both of you have a separate working copy
of the same repo:

```
git worktree add ../chakravyuh-ui stage/drishti
```

Rules for the boundary, and they are short. Track B may read `docs/DATA-CONTRACTS.md`
and `docs/DRISHTI-SPEC.md`. Track B may not edit anything under `src/`. If Track B needs
a field that does not exist, they open an entry in `docs/DECISIONS.md` and you decide.
Nobody edits the contract on their own.

One more parallel job that needs no coding skill and pays off enormously: whoever is on
the deck can be filling the six slides from the PPT pack at the same time, using screens
from Track B as they appear. Real screenshots on Slide 3 beat any diagram.

---

## 8. The dataset decision, and why the links your group sent change it

Your group found something genuinely useful. That figshare record is the data behind a
peer reviewed paper in *Nature Scientific Data*, "Bitcoin Research with a Transaction
Graph Dataset" (also arXiv 2411.10325). It holds **252 million nodes and 785 million
edges** across roughly thirteen years and about **670 million transactions**, every node
and edge timestamped, plus two labelled subsets, one of about **34,000 labelled nodes**.
Nodes are Bitcoin users, meaning already clustered address groups, and edges are
transactions between them. There is a sibling dataset called ORBITAAL, also in *Nature
Scientific Data*, covering 2009 to 2021 as entity to entity temporal graphs.

Now read that against our problem. Those datasets are the **chain layer** and nothing
else. No IP address, no port, no announcement time, no peer identity. That absence is
not an oversight in their work, it is the exact gap our whole idea sits in, and it is
why the deck can honestly say no public dataset carries both layers.

So the right call is a hybrid, and it is better than what I had planned:

**Use real data for the chain layer. Synthesise only the network layer.**

- The chain half comes from a real Bitcoin transaction graph slice. Real topology, real
  value distributions, real timing, real entity labels. We do not have to invent any of
  it, and we cannot get it wrong.
- The network half is generated by MAYAJAAL: peers, IPs, ASNs, geography, gossip
  announcements with per peer randomised delays, and a partial observer. This is the
  half that does not exist anywhere, so generating it is the only option available to
  anyone, including NTRO.
- Ground truth about the true originator comes from the generator, because the
  generator is the only thing that knows it.

Why this is the stronger design, in one sentence: the worst attack on a fully synthetic
benchmark is "you invented the data and then solved your own invention", and this design
answers it, because the half we did not invent is real and peer reviewed.

### So MAYAJAAL gets two modes, and the same output shape from both

```
mayajaal --source synthetic  --txs 100000 --seed 42 --out data/generated/run-A
mayajaal --source real-slice --graph vendor/btc-graph/ --txs 100000 --out data/generated/run-B
```

Identical columns out of both. Identical ground truth files out of both. Nothing
downstream knows or cares which mode produced its input.

Both modes exist for a reason and neither is a spare tyre.

**Synthetic mode is the workhorse.** It runs offline forever, has no licence question,
scales to any size, and is the only mode where you can dial a knob and ask what happens.
You need that to write the honest numbers on Slide 4. You cannot ask a real dataset
"what if the observer only sees 5% of the network", but you can ask the generator.

**Real slice mode is the credibility mode.** It is how you say, at the finale, that the
origin estimator was measured on real Bitcoin transaction topology and not only on your
own simulator. That sentence is worth a great deal and it costs one ingestion adapter.

Three things to be careful about, and I would rather say them now than have them bite:

1. **Check the licence before you ship anything.** Figshare records are usually CC BY but
   you must read the record's own licence line and record it in `docs/DECISIONS.md` with
   the date you checked. If it is not clearly redistributable, we use it locally for
   measurement and we ship only synthetic data in the repo.
2. **The full dataset is far too big for a laptop demo.** Do not try to load it. S01 has
   an explicit sampling step: pick a time window, pick a seed set of labelled entities,
   take a bounded neighbourhood around them, stop at a target transaction count.
3. **Never let the real slice become a dependency.** `make demo` must work with the
   network cable unplugged and `vendor/` empty. Synthetic mode is the default in every
   Makefile target for exactly this reason.

### The one number that explains the whole dataset

One row is **one announcement of one transaction by one peer**, not one transaction. The
chain columns repeat across every row that announces the same TXID. With a mean of nine
announcing peers, a **one million row capture is only about 111,000 transactions**. The
other 889,000 rows are echo.

Hold on to that number, because it is the entire pitch in arithmetic form. A tool that
treats a million rows as a million facts is wrong about 89% of its input. Say that
sentence in the demo and in the viva. It lands every time.

---

## 9. What "done" means, and how you check it without reading code

Every stage has three gates. You can check all three in under two minutes and none of
them require you to read a diff.

**Gate 1, the machine gate.** `make verify-sNN` exits zero. Claude is not allowed to call
a stage finished before this passes, and the command is written into the stage brief
before any code is written, so it cannot be quietly redefined later.

**Gate 2, the your hands gate.** Every stage brief ends with a short "your turn" block:
three commands for you to run and two values for you to change and re run. Doing it takes
five minutes and it is the difference between owning this project and hosting it. Run
`/yourturn` if the block is not in front of you.

**Gate 3, the explain gate.** Run `/explain`. Claude appends fifteen lines or fewer to
`docs/EXPLAIN.md` covering what the stage does, why it exists, the one design choice
inside it, and the honest limitation. Plain words, no jargon it has not already defined.
If you read that entry and cannot repeat it back in your own words, the stage is not done
and you should say so in the session rather than move on.

`docs/EXPLAIN.md` is the document you revise before the internal hackathon. By S11 it is
about twelve short entries and it covers everything anyone can ask you.

---

## 10. The demo, five beats

The demo is the deck executed. The five beats are the five verdict lines from the slides,
in order. That coherence is deliberate. When the thing on screen says exactly what the
slide said, a room stops evaluating you and starts believing you.

**Beat 1. This is one million rows and here is its fingerprint.**
Show the sealed input: row count, file hash, ingest time. Three seconds, no commentary.

**Beat 2. Most of it is echo.**
One million rows, 111,000 transactions. The screen collapses the pile into the real count
in front of them. This is where a non technical person first understands the problem.

**Beat 3. Nine peers announced this transaction. Only one sent it.**
The origin view. Eight thin grey beams, one thick orange beam, `p = 0.87` on it, and the
runner up shown underneath. This is the beat the whole project exists for. Do not rush it,
do not talk over it, and let someone in the room ask "how do you know" before you answer.

**Beat 4. Twenty leads, ranked, each with the case against it.**
The queue. Click the top lead. Cause, confidence, counter evidence, all on one screen.
Then click a mining pool that scored high and show the tool clearing it by itself.

**Beat 5. This is what an officer sends.**
The evidence packet. Public IP, source port, exact UTC timestamp, the hash, the pre
filled production notice. Then close the laptop lid, or turn off the wifi and re run it,
and say the one line: nothing left this machine.

Rehearse it as five beats, not as a feature tour. Six minutes total. Every feature that
does not serve a beat gets shown only if someone asks.

---

## 11. Your first thirty minutes

Do these in order and stop when the last one prints green. Nothing here needs a decision
from you.

1. Make an empty repo called `chakravyuh`, `git init`, and open it in Claude Code.
2. Copy this pack's `claude-config/settings.json` to `.claude/settings.json`, and the
   `commands/` and `agents/` folders to `.claude/commands/` and `.claude/agents/`.
3. Copy `CLAUDE.md`, `STATE.md` and `SESSIONS.md` to the repo root, and `ARCHITECTURE.md`,
   `DATA-CONTRACTS.md`, `STAGE-BRIEFS.md`, `MAYAJAAL-SPEC.md` and `DRISHTI-SPEC.md` into
   `docs/`. Rename `00-START-HERE.md` to `docs/START-HERE.md` so it travels with the project.
4. Copy `SIH26146.pdf` and the PPT build pack into `docs/reference/`.
5. Start a session, run `/permissions`, confirm the allow list loaded.
6. Open `SESSIONS.md`, read "The ritual, every single time", go to session S00, and paste
   prompt 1.

That is it. From there `SESSIONS.md` runs the project and this file is just the thing you
come back to when you want to remember why something is the way it is.

---

## 12. Two habits that will decide how this goes

**Read the plan, always.** The ninety seconds you spend reading the plan in plan mode is
the highest leverage time in this entire project. It is where you catch a wrong idea
before it becomes four hundred lines of code and an hour of your attention.

**When something feels vague, say so immediately.** Not later. The moment a session
produces something you cannot explain in your own words, stop and ask "explain this to me
in plain words and tell me what would break it". You already predicted that you would need
to do this. You will be right more often than you expect, because the person who is
confused about an explanation is very often looking at an explanation that is hiding
something.# CHAKRAVYUH · START HERE

Two documents in this pack are for you to read. This one, and `SESSIONS.md`.
Everything else is written for Claude Code to read, not you. You will still understand
the project completely, because every build session ends by writing a short plain
English entry into `docs/EXPLAIN.md`. That file becomes your answer sheet.

---
