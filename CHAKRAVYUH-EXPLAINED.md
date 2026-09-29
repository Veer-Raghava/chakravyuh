# CHAKRAVYUH, explained like you built it

> Read this once, top to bottom, and you will understand the whole system — not just what it does,
> but *why* each piece exists, *what data* it holds, *where* that data physically sits, and *how* the
> next piece picks it up. No prior knowledge assumed. Plain words first, depth right after.
>
> This describes the system **as it is meant to be after the v2 remodel** (the ideal, finished
> state). Wherever v2 changed something, a short **`Changed from v1:`** line tells you what and why.

---

## 0 · How to read this (30 seconds)

The doc has three passes, and you can stop at any depth:

1. **The story** (§1–§4): the problem, the idea, and the words you need. Read this and you can
   explain the project to a friend.
2. **The eight layers** (§5–§13): one assembly line, eight stations. Each station uses the **same
   little template** so your brain never has to re-learn the format:
   - **In** (what it receives, from where) → **Does** (the work) → **Out** (what it produces) →
     **Next** (who reads that output) → **Files** (where the code lives) → **Changed from v1** →
     **Think about it** (a logical question or two to lock it in).
3. **The frontend + the hard questions** (§14–§16): what the screen actually shows, and the
   "wait, but what about…" questions a smart skeptic (or an NTRO reviewer) will ask.

You do **not** need to hold all eight layers in your head at once. Each one only cares about the
folder the previous one wrote. That's the whole trick. Keep going.

---

## 1 · The problem, told like a story

Someone runs a Bitcoin scam. Money lands in a Bitcoin address. You, the investigator, want to answer
one deceptively simple question: **who sent this, and where did it come from?**

Here is why that is brutally hard, and it comes down to two walls.

**Wall 1 — everybody shouts everybody's mail.** Bitcoin has no post office. When a payment is made,
the sender's computer whispers it to a few neighbour computers, who whisper it to *their* neighbours,
and within seconds thousands of computers are all shouting "I have this transaction!" So if you're
listening and you write down "the first computer I heard it from," you have almost certainly written
down a **relay** — a random middle-man — not the sender. The real sender is hidden inside a stampede
of echoes.

**Wall 2 — you only have a few ears.** You can't listen to the entire planet's worth of Bitcoin
computers. You have some listening posts. You hear a *slice* of the shouting. For a lot of
transactions, the sender's own whisper simply never reached any of your ears — it got drowned out
before it got to you. That information is *genuinely gone*. Not "we were lazy" gone. Physically gone.

That is the maze. In the Mahabharata, the **chakravyuh** is a spiral battle formation you can walk
into but can't walk out of. Bitcoin tracing is the same shape: easy to enter, near-impossible to
reverse. **CHAKRAVYUH** is our name for the whole engine that models and fights that maze.
**DRISHTI** (दृष्टि, "sight") is the eye we built to see through it — the screen the investigator
actually looks at. Brand line: *"See through the noise."*

The soul of the project, in one sentence: **we see as far as we honestly can, and we are honest
about where the dark begins.** We never paint the dark part as if it were lit.

---

## 2 · The idea (our solution, in one breath)

We stopped promising the impossible thing and started delivering the achievable, *useful* thing.

The impossible thing: "here is the exact laptop, at this exact IP, that sent the money." Physically
recoverable only 5–60% of the time (this is published science, not our excuse), **and** illegal for
us to display a full IP anyway under India's evidence rules. Chasing it was a trap.

The achievable thing — we call it the **attribution ladder**. Instead of one all-or-nothing answer,
we give an answer at whatever rung the evidence can honestly support:

| Rung | What we claim | How often we can | Shown on screen? |
|---|---|---|---|
| **L0** | the exact origin computer (IP) | rarely | **no** — officer-only, legal rule |
| **L1** | the **network operator / ISP (ASN)** it came from | **often** | **yes — this is the hero** |
| **L2** | the **region / country** | usually | yes |
| **L3** | a **short ranked shortlist** of suspect computers + confidence | yes | yes |

Why this is legitimate and not a dodge: attribution legally *stops* at the operator anyway (you
serve a notice to the ISP, not to a laptop); the suspect computers almost always collapse onto a
handful of operators, so **guessing the operator is far easier and more reliable than guessing the
exact machine**; and this is exactly what real forensic firms (Chainalysis, GraphSense) do. It's the
industry-correct answer, and it's one we can hit with high accuracy.

**One more move that makes everything downstream win:** we run the demo in a realistic
**"agency-grade" listening regime** — an intelligence agency sits at big internet exchange points and
hears ~60% of the network, not the 10% a lone academic hears. We don't hide the weaker regimes; we
publish the *whole curve* (§16). But we headline the number a national agency would actually get.

**`Changed from v1:`** the old system aimed the headline at L0 (exact host) in a pessimistic 10%
listening regime — so it looked weak *and* couldn't legally show its own answer. v2 aims at L1
(operator), runs the agency 60% regime as the demo default, and keeps the honesty curve as proof
rather than as an apology.

---

## 3 · The words you need (read once, refer back forever)

These are *the* nouns of the project. Everything else is built from them. Read slowly; each one is a
brick.

- **Transaction (tx).** One Bitcoin payment: some money goes *in*, some money comes *out*. Every tx
  has a unique 64-character hex fingerprint called a **txid** (e.g. `4a7f2c91…8b3e`). Think of a tx
  as a single receipt.
- **Input / output.** A tx's inputs are the coins being spent; its outputs are where they land.
  "Send 1 BTC to Bob, get 0.3 back as change" = 1 input, 2 outputs.
- **Address.** Where coins sit — like an account number or an envelope (`bc1q4f…9f4d`). A person can
  make thousands of them for free. This is *why* one human hides behind many addresses.
- **Wallet / entity.** The real actor — a person, an exchange, a scammer — who *controls* a bunch of
  addresses. We almost never see this directly. We **infer** it.
- **Cluster.** Our best *guess* that a set of addresses is controlled by the same wallet. A cluster
  is a **suspected wallet**, never a proven one. (More on why it's never certain in §8.)
- **Peer.** A computer on the Bitcoin network that passes transactions around. Every peer has an IP.
- **IP.** A computer's address on the internet, like a street address for a house. Peers have IPs.
- **Announcement.** The moment a peer says to the network "I have transaction X." One tx gets
  announced by *many* peers — that stampede of echoes is Wall 1. On average ~9–14 announcements per
  tx in our world.
- **Observer.** One of **our** listening computers that overhears announcements. We only ever know
  what our observers happened to hear. Few observers = we hear a thin slice (Wall 2).
- **Origin.** The one peer that *actually created and first sent* the tx — the sender's own machine.
  This is the needle we hunt. Everything else that announced the tx is just a relay.
- **ASN / network operator.** The big network that owns a whole block of IPs — an ISP or a hosting
  company (e.g. AS4808 = China Unicom). Every IP belongs to exactly one ASN. **This is L1, our
  hero:** naming the operator is our headline answer.
- **net_class.** *What kind* of connection an IP is: `residential`, `hosting`, `mobile`, `tor_exit`,
  `vpn_suspect`, or `unknown`. A residential origin is a very different story from a hosting one.
- **Abstain.** A first-class answer that means **"No answer available"** — the honest output when the
  evidence isn't there. Abstaining is *correct behaviour*, not a failure, and never a low score in
  disguise.

Two habits the whole codebase obeys, so learn them now:

- **Money is always satoshis, as a whole number (int64).** 1 BTC = 100,000,000 sats. We never use
  decimals for money (a float loses a penny at the eighth decimal, and this stuff prints into court
  evidence). We convert to "BTC" only at the very last moment, on screen.
- **Time is always UTC microseconds since 1970, as a whole number**, in columns ending `_us`. We
  convert to human India time only on screen.
- And: **`null` ≠ 0 ≠ "unknown".** A missing ASN is `null` and stays visibly different from zero.

---

## 4 · The whole thing in one picture

CHAKRAVYUH is an **assembly line of eight stations**, each with a Sanskrit name. Data enters as a
million raw radio-overhears and leaves as **one** court-ready proof packet. Each station reads the
previous station's output folder, does one job, and writes its own folder. That's it.

```
 raw captures
     │
     ▼
① MAYAJAAL   build the world   → makes the fake-but-realistic data + the sealed answer key
② KAVACH     seal the intake   → hash first, then load; reject bad rows; lose nothing silently
③ SETU       split the grain   → separate "the wire" (announcements) from "the money" (tx/addresses)
④ JAAL       draw the map      → build the graph; guess which addresses share an owner (clusters)
⑤ SHASTRA    estimate origin   → who sent it? give the L1/L2/L3 ladder + confidence, or abstain
⑥ BUDDHI     score the risk    → which wallets look illicit? calibrated, with uncertainty
⑦ VAANI      write the leads   → turn scores into plain-English ranked alerts + counter-evidence
⑧ PRAMAAN    seal the proof    → one signed, hash-chained, court-ready evidence packet
     │
     ▼
  DRISHTI (the frontend) reads snapshots of these outputs and shows them as 8 screens
```

The funnel that rides on top: **1,000,000 signals → 999,847 sealed → 111,043 untangled → 24,626 real
transactions → … → ~20 leads → 1 proof.** Every drop in that funnel is *accountable* — the system can
always answer "where did the other 900,000 go?" with a table, not a shrug (that's the `counts.in ==
counts.out + counts.dropped` rule every station obeys).

**A question you should be asking already:** *"Wait — MAYAJAAL makes fake data? Isn't that cheating?"*
Great instinct — hold it. The answer is §5 and again in §16. Short version: we generate a realistic
world **and a sealed answer key**, so we can actually *measure* whether the rest of the pipeline is
right — something you can never do on real chain data where the truth is unknown. And we can swap in
real-chain topology to prove we're not just marking our own homework.

---

## 4b · Where the data actually lives (there is no database)

This surprises people, so let's kill the confusion up front: **there is no database.** No Postgres,
no MySQL, no server holding rows. The whole pipeline is **files on disk.**

Each station writes **Parquet** files (a compact columnar table format — think "a spreadsheet saved
as a fast binary file") into its own folder inside a run directory. The next station opens those
files with **Polars** (a fast dataframe library, like pandas but quicker), does its work in memory,
and writes its own Parquet files out. Nobody queries a live server; everybody just reads the folder
in front of them.

```
measurements/<run_id>/
  ground_truth/   ← the sealed answer key (only the eval code may read this)
  sealed/         ← KAVACH's output
  normalised/     ← SETU's output   ← "everything downstream reads from here"
  graph/          ← JAAL's output
  signals/        ← SHASTRA's output
  scores/         ← BUDDHI's output
  alerts/         ← VAANI's output
  packets/        ← PRAMAAN's output
  _meta.json      ← in every folder: what ran, seed, row counts in/out, hashes
```

Why files and not a database? Because the tool must run **fully offline, air-gapped**, be **replayable
byte-for-byte** from a seed, and produce **court evidence** where every intermediate artifact can be
hashed and cited. A database would add a moving part with none of those guarantees. (There's a
`duckdb` line left in the dependencies from an early idea — it's never imported; v2 deletes it.)

**How the frontend gets data (the one seam — memorise this).** The frontend does **not** read Parquet
and does **not** need the Python running. One file, `src/chakravyuh/api/serialize.py`, is the single
place that turns pipeline outputs into the **JSON shapes the UI wants**. It feeds two mouths from that
one recipe:

```
serialize.py  ──┬──►  api/app.py            (a tiny FastAPI server on 127.0.0.1:8000, for live dev)
                └──►  scripts/export_ui_fixtures.py  ──►  data/fixtures/ui/*.json
                                                              │  (copied into the app)
                                                              ▼
                                          apps/drishti-v2/src/data/fixtures/*.json
                                                              │  (imported by)
                                                              ▼
                                          apps/drishti-v2/src/data/loader.ts   ← the UI reads THIS
```

Because both the live API and the static JSON come out of the *same* serializer, **the fixture shape
is identical to the API shape by construction** — the UI can be built entirely against the committed
JSON with no pipeline running, and it'll behave the same the day a live backend is plugged in. For the
demo we ship the static JSON (fixtures), so DRISHTI needs zero network.

Now, the eight stations.

---

## 5 · ① MAYAJAAL — build the world (the illusion-net)

**One line:** it *manufactures* a realistic Bitcoin world — the network, the wallets, the crimes, the
overheard announcements — **and writes down the secret answer key** so the rest of the pipeline can be
graded.

**The plain story.** You can't test a tracing tool on the real blockchain, because on the real
blockchain *nobody knows the true answers* — that's the whole reason the tool exists. So we build a
world where we, the makers, secretly know everything: which computer really sent each transaction,
which addresses really belong to the same criminal, which flows are really laundering. Then we hide
all of that in a locked drawer (`ground_truth/`), hand the pipeline only what a real observer would
actually see, and at the very end compare its guesses to the locked answers. That comparison is the
only reason we can put a *number* on how good we are.

Crucially, we do **not** stamp a label like "this is a peel chain" onto the data. We build *agents*
that behave like a peel-chain launderer would, and the pattern *emerges* — so when SHASTRA/BUDDHI
later detect it, that's a real detection, not us reading our own sticky note.

- **In:** a `run_config.json` (the world's settings: seed, size, how many observers, the
  observer regime, Tor share, campaign mix).
- **Does:** simulates a UTXO ledger (real Bitcoin accounting), spawns entities and laundering
  campaigns, propagates each transaction across a peer network with realistic **per-link random
  relay delays** (this delay model is the physics that SHASTRA later exploits), and places our
  **observers** on the network to overhear a fraction of it.
- **Out:** two things. (1) The **observable capture** — rows of "peer P announced tx T to observer O
  at time t," exactly the schema a real NTRO capture would have. (2) The **quarantined answer key**
  in `ground_truth/`: `origins.parquet` (who really sent each tx), `entities.parquet` (who really
  owns which addresses — the clustering answer), `campaigns.parquet` (which txs form one laundering
  operation).
- **Next:** KAVACH reads the observable capture. **Only** `src/chakravyuh/eval/` is ever allowed to
  open `ground_truth/` — a test greps the entire codebase to prove no other layer touches it. If a
  truth column ever leaked into a normal file, every measurement after it would be void.
- **Files:** `mayajaal/config.py` (the regime presets), `network.py` (peers, observers, biased
  placement), `ledger.py` (UTXO accounting), `entities.py` + `adversary.py` (actors + campaigns +
  the evasiveness knob), `chain.py`, `regions.py`, `weighted.py`, `export.py` + `writers.py` (emit
  capture + answer key), `preflight.py` (sanity checks before a run).
- **`Changed from v1:`** (1) the observer setup is now a **named regime** — `"agency"` (~60%
  coverage, observers biased to sit at big well-connected nodes like an ISP/IXP monitor) is the demo
  default, `"stealth"` (~10%, the old academic attacker) is kept for the honesty curve. (2) The answer
  key went **multi-granular** — it now records the true origin's **ASN, operator, net_class, and
  country**, not just the exact IP. (3) Campaigns got a `detectability` knob so most are catchable but
  an evasive minority honestly slips through (that's why recall is < 100% for a real reason, not a
  flat low number).

**Think about it.**
- *If MAYAJAAL knows the true origin, why is SHASTRA's job hard?* Because MAYAJAAL only hands
  downstream the **observable** rows. The truth is locked away. SHASTRA has to *reconstruct* it from
  the same partial echoes a real analyst would have.
- *Why random relay delays instead of instant propagation?* Because those tiny, per-link time
  differences are the **fingerprint** SHASTRA triangulates from later (§9). No delays, no timing
  signal, no origin estimation. The realism *is* the signal.

---

## 6 · ② KAVACH — seal the intake (the armour)

**One line:** it takes the raw capture, **hashes it before touching it**, loads it into clean typed
rows, and rejects bad rows *loudly* — so nothing is ever silently lost or silently changed.

**The plain story.** Before you analyse evidence, you have to prove you didn't tamper with it. KAVACH
("armour") is the chain-of-custody gate. The first thing it does is compute a SHA-256 hash of every
input file — a fingerprint of the exact bytes that arrived. From then on, anyone can prove the data
was never altered. Then it reads the messy input (timestamps in three different formats, amounts
maybe in BTC maybe in sats), coerces everything to the strict types the rest of the pipeline expects,
and — this is the important part — any row that fails a sanity check does **not** get thrown away. It
gets moved to a `rejected` file **with a written reason**. The golden rule: `rows_read` must equal
`rows_sealed + rows_rejected`. Always. A count that reconciles is how you answer "did you lose data?"
with a number instead of a shrug.

- **In:** the raw capture rows from MAYAJAAL (or a real NTRO file — same schema). One row = one
  announcement of one tx by one peer.
- **Does:** hash inputs → detect & normalise timestamp format and money unit → coerce to int64
  sats / `_us` times → add a stable `row_id` (its position in the original file, so any row is
  citable later) → run invariant checks (input addresses count == input amounts count; txid is
  64 hex chars; inputs ≥ outputs for non-coinbase; rows sharing a txid must agree on the chain
  columns). Failures go to `rejected` with a `reject_reason`.
- **Out:** `sealed/rows.parquet` (clean, typed, same grain as input minus rejects),
  `sealed/rejected.parquet` (bad rows + why), `sealed/INPUT.sha256` (the fingerprints), and
  `sealed/manifest.json` (rows read / sealed / rejected, formats detected).
- **Next:** SETU reads `sealed/rows.parquet`. PRAMAAN later reads the hashes and manifest for the
  chain-of-custody section of the evidence packet.
- **Files:** `kavach/readers.py` (format detection + loading), `kavach/schema.py` (the type
  contract + invariants), `kavach/seal.py` (hashing, row_id, manifest, reject routing).
- **`Changed from v1:`** essentially unchanged — KAVACH was already solid. It stays the frozen
  chain-of-custody guarantee the whole legal story rests on.

**Think about it.**
- *Why hash before parsing, not after?* Because you must be able to prove you analysed **the exact
  bytes you received**, not a cleaned-up version. Hash first = the fingerprint is of the real
  evidence.
- *Why keep rejected rows instead of dropping them?* Because at the demo finale someone will ask
  "where did those rows go?" — and "here is the rejected file with a reason per row" is an answer;
  silence is not.

---

## 7 · ③ SETU — split the grain (the bridge)

**One line:** it separates two things that were tangled together in every raw row — **the wire** (who
announced what, when) and **the money** (what the transaction actually moved) — into clean, separate
tables.

**The plain story.** Remember a raw row is "peer P told observer O about tx T," and it *also* carries
all of tx T's money details (inputs, outputs, amounts). So the money details are copy-pasted across
every echo of the same tx — wasteful and confusing. SETU ("bridge") splits the single messy stream
into four clean tables, each at the right **grain** (level of detail):

- **announcements** — one row per echo. This is *the wire*: the timing/network evidence.
- **transactions** — one row per unique tx. This is *the money*: inputs, outputs, fees, flags.
- **addresses** — one row per unique address.
- **peers** — one row per unique announcing computer.

It also *enriches* the wire: it renames `src_ip` → **`peer_ip`** (because "source" is misleading —
it's usually a relay, not the source) and `dst_ip` → **`observer_ip`**, and it looks up each IP in
offline lists to fill in `asn`, `as_org`, `net_class`, `geo_country`. And it computes the two timing
columns that matter most: `rank_in_tx` (was this the 1st, 2nd, 3rd… echo we saw of this tx?) and
`delta_first_us` (how long after the very first echo did this one arrive?).

- **In:** `sealed/rows.parquet` from KAVACH.
- **Does:** split into the four grains; enrich IPs from offline `vendor/` lists; compute per-tx
  ordering (`rank_in_tx`, `delta_first_us`), per-tx aggregates (`n_announcements`, `n_distinct_peers`,
  `announce_spread_us`, fee, `has_equal_outputs`, suspected `change_index`), and per-peer stats
  (`frac_rank_one` = how often this peer is the earliest — a suspiciously-often-first peer is
  interesting).
- **Out:** `normalised/announcements.parquet`, `transactions.parquet`, `addresses.parquet`,
  `peers.parquet`. Plus the two v2 additions below.
- **Next:** **everybody downstream reads from `normalised/`, never from `sealed/`.** JAAL builds the
  graph from it; SHASTRA reads the arrival timing; BUDDHI reads the money shapes.
- **Files:** `setu/normalise.py` (the grain split), `setu/enrich.py` (IP → ASN/net_class lookups),
  `setu/schema.py`.
- **`Changed from v1:`** two new outputs feed the stronger origin estimator: (1) a per-tx **arrival
  matrix** — for each tx, the list of `(observer, peer, time-seen)` — which is the exact substrate
  the timing triangulation needs; and (2) `normalised/asn_rollup.parquet`, one row per operator
  (ASN) summarising its announcement behaviour, which becomes the **prior** for the L1 operator
  guess.

**Think about it.**
- *Why is renaming `src_ip` to `peer_ip` a big deal and not just cosmetic?* Because the name `src_ip`
  quietly tricks you into believing the announcer is the sender. It usually isn't. The rename bakes
  the core insight of the whole project into the schema so nobody downstream forgets it.
- *Why split grains at all?* So each later layer reads only what it needs at the density it needs:
  SHASTRA wants the fine-grained wire; BUDDHI wants the per-tx and per-cluster money shapes. Mixing
  them would force every layer to de-duplicate the same tx 14 times.

---

## 8 · ④ JAAL — draw the map (the net)

**One line:** it turns the flat tables into a **graph** — dots and lines — and makes its most
important guess: **which addresses probably belong to the same owner** (clustering), always with a
confidence, never as a hard fact.

**The plain story.** "JAAL" means net/web. This layer builds the connection map: addresses, txs, and
peers become **nodes** (dots); the relationships between them become **edges** (lines). Some edges are
hard facts read straight off the chain ("this tx *spends* that coin" — confidence 1.0). Others are
*inferences*, and this is where the real forensic judgement lives.

The headline inference is **clustering**: deciding a bunch of addresses are one wallet. The classic
heuristic is *common-input ownership* — if two addresses were spent together as inputs to one tx,
they're probably the same owner (you needed both private keys). But here's the honesty that defines
the project: **a cluster is never a hard merge.** The multi-input heuristic is only ~0.36 precise in
real law-enforcement settings — it'd be wrong roughly two times in three if you treated it as
certain. So `SAME_OWNER` is stored as an **edge with a confidence and a named reason**, and the
frontend gives the analyst a **dial** to slide the confidence threshold and *watch the clusters grow
and shrink*. We surface 0.36 proudly as a *tunable* number, not a hidden weakness.

- **In:** `normalised/` tables from SETU.
- **Does:** create nodes (`addr:…`, `tx:…`, `peer:…`, `cluster:…`, `asn:…`) and edges (`SPENDS`,
  `RECEIVES`, `ANNOUNCED_BY`, `SAME_OWNER`, `HOSTED_IN`, `MEMBER_OF`); run clustering heuristics
  (multi-input at high confidence, change-address at explicitly *lower* confidence with
  counter-evidence attached); cut clusters at a chosen threshold.
- **Out:** `graph/nodes.parquet`, `graph/edges.parquet` (each edge carries `confidence` +
  `evidence` = which heuristic made it), `graph/clusters.parquet` (each cluster carries
  `min_edge_confidence` = its weakest link, and the `threshold` it was cut at).
- **Next:** SHASTRA and BUDDHI both read the graph — BUDDHI scores clusters (suspected wallets) as
  well as individual txs. The frontend's **Map** screen renders this directly.
- **Files:** `jaal/build.py` (nodes + edges), `jaal/cluster.py` (the heuristics + dial),
  `jaal/view.py` (produces the different graph views the UI asks for), `jaal/stage.py`.
- **`Changed from v1:`** it became a **dual graph**. v1 had one graph. v2 promotes the
  **actor/address graph** to a first-class, scored surface *alongside* the transaction graph (the
  shape the Elliptic++ research dataset uses), so BUDDHI can score both "this transaction" and "this
  wallet" and we can honestly show the two only partly agree. It also added a **peel-chain tracer**
  (follows the classic "spend a little, move the change, repeat" laundering pattern) and a
  **CoinJoin/mixer detector** that *sets aside* mixers with a reason, so we don't wrongly merge
  everyone who used the same mixer into one owner.

**Think about it.**
- *What exactly is a "cluster" vs a "wallet"?* A **wallet/entity** is the real owner (we can't see
  it). A **cluster** is our *estimate* of that owner, assembled from confidence-weighted edges. The
  dial exists precisely because the estimate has a knob and we refuse to pretend it doesn't.
- *Why must CoinJoin be set aside?* A CoinJoin deliberately mixes many people's coins into one tx
  with equal-value outputs. If you naively applied common-input ownership across it, you'd glue
  dozens of unrelated people into one fake mega-wallet. Detecting and excluding it is the difference
  between forensics and garbage.

---

## 9 · ⑤ SHASTRA — estimate the origin (the weapon) ★ the heart of the project

**One line:** given all the echoes of a transaction, it estimates **where it originated** — as the
operator (L1), the region (L2), and a short ranked shortlist of suspect peers (L3) with calibrated
confidence — or it honestly **abstains**.

**The plain story — the microphone analogy.** Imagine a gunshot in a city. You have several
microphones scattered around. Each hears the bang at a slightly different time. From those tiny time
differences — plus knowing how fast sound travels — you can triangulate roughly where the shot came
from. That's exactly SHASTRA. The "gunshot" is the transaction being born. The "microphones" are our
observers. The "bang arriving" is each announcement, with its `seen_us` timestamp. The "speed of
sound" is MAYAJAAL's known relay-delay model. SHASTRA runs the triangulation *backwards* to score,
for each candidate peer, **how likely it is that this peer is the source that produced the arrival
pattern we actually observed across all our microphones.**

Why the naive method fails (and this is the number that matters): the dumb approach is "whoever we
heard first is the sender." That's `first_spy`, and it's right only ~22% of the time — because the
first echo *you* caught is just the first relay that happened to reach one of your ears, not the
origin. SHASTRA's real estimator (`timing_mle`) uses *all* observers' timings together, which is why
it beats the naive baseline.

Then the **ladder** (the v2 reframe, §2): from the per-peer scores, SHASTRA rolls candidate mass up
to the **operator (ASN)** level — because even when it can't pin the exact machine, the suspects
usually cluster onto one or two ISPs, and naming the ISP is both easier and legally the real answer.
It reports L1 (operator) as the hero, L2 (region), and L3 (the top-k shortlist).

**Two honesty rules that are load-bearing:**
1. **`p_origin` is never renormalised to sum to 1.** If a tx's candidate probabilities add up to only
   0.4, that *shortfall* is the system saying "there's a 60% chance the true origin is someone we
   never even observed." Forcing it to sum to 1 would be a lie. The frontend renders the shortfall.
2. **Abstain is a real output.** When it's Tor, or only one observer saw it, or the top two candidates
   are too close to call (`margin` below a floor), SHASTRA refuses to rank and says **"No answer
   available."** That's the calm grey state on screen, not an error.

- **In:** `normalised/announcements.parquet` + the v2 arrival matrix + `asn_rollup` + the graph.
- **Does:** run the estimator stack (below) → produce per-candidate scores → roll up to ASN/region →
  decide abstain → also run **typology detection** (peel_chain, structuring, fan_out, coinjoin_like,
  rapid_hop) and a pre-scoring **entity-type** guess (exchange, mixer, mining pool…), which runs
  *before* any risk scoring so known services can be exempted.
- **Out:** `signals/origin_estimates.parquet` (one row per candidate peer per tx: `p_origin`, `rank`,
  `margin`, `features`, `estimator`, `abstain`, `abstain_reason`; v2 adds the L1/L2 attribution +
  shortlist), `signals/typology_hits.parquet`, `signals/entity_types.parquet`.
- **Next:** BUDDHI folds origin confidence into its risk features; VAANI turns the estimate into the
  plain-English lead; PRAMAAN prints the attribution in the packet. The frontend's **Origin** screen
  is this layer made visual (the candidate rings).
- **Files:** `shastra/estimate.py` (the estimator stack), `shastra/features.py` (the named inputs to
  each estimate), `shastra/typology.py` (laundering-pattern detectors), `shastra/schema.py`.
- **`Changed from v1:`** this is the biggest v2 change. v1 leaned on `first_spy` and scored only the
  exact host — unreachable and unshowable. v2 adds a real **estimator stack**, each independently
  runnable so `make compare-estimators` prints them side by side rather than us *asserting* the
  ensemble is best:
  1. `first_spy` — the naive baseline, kept only to be beaten.
  2. `timing_mle` — the real multi-observer maximum-likelihood triangulator (the microphone method).
  3. `asn_rollup` — lifts the scores to the operator level; **this is the headline L1 output.**
  4. `ensemble` — a calibrated blend of the above, trained across regimes so it doesn't overfit one
     coverage level.
  And the whole thing now outputs the **L0/L1/L2/L3 ladder** instead of one host guess.

**Think about it.**
- *Why report a shortlist instead of one name?* Because one name implies certainty we don't have. A
  calibrated top-k shortlist ("it's one of these five, most likely the first") is honest *and* more
  useful to an investigator — it's what a "conformal prediction set" is, just in plain clothes.
- *Why is L1 (operator) recoverable so much more often than L0 (host)?* Because many different
  candidate IPs sit inside the same ISP. Even if you can't tell *which* house, you can often tell
  *which street* — and in attribution, the street (the operator you serve a notice to) is the answer
  that actually matters.
- *Is abstaining just giving up?* No — it's the difference between a tool you can trust and one that
  bluffs. An investigator can act on "no answer" (go get more data); they can't recover from a
  confident wrong name that sends them at an innocent ISP.

---

## 10 · ⑥ BUDDHI — score the risk (discrimination)

**One line:** it looks at each suspected wallet (and each transaction) and asks **"does this look
illicit?"** — giving a calibrated risk with an honest uncertainty range, not a naked number.

**The plain story.** "BUDDHI" means discernment. This is the machine-learning layer, but the smart
part isn't the model — it's the *honesty scaffolding* around it. Illicit activity is rare (roughly
1 in 345 here), so a model that just shouts "suspicious!" a lot can look accurate while being useless.
BUDDHI does three things to stay trustworthy:

1. It scores on **shape, not labels.** The features are things an analyst could compute by hand:
   fan-in/out ratios, peel-chain depth, rapid-hop dwell time, structuring (amounts suspiciously
   clipped under reporting thresholds), CoinJoin participation, burstiness, fee anomalies. It reads
   *behaviour*, so it isn't secretly reading MAYAJAAL's answer key.
2. It **quantifies its own uncertainty** with *conformal prediction*: instead of "risk = 0.83," it
   outputs a calibrated interval and a label (`LIKELY_ILLICIT` / `UNCLEAR` / `LIKELY_LICIT` /
   `ABSTAIN`). The interval is what the screen shows.
3. It evaluates **inductively** — train on the past, test on the future — because that's the only
   protocol that reflects real deployment. No peeking at future data to flatter the score.

- **In:** the graph + clusters from JAAL, the money shapes from SETU, and origin confidence from
  SHASTRA (folded in as features like `mean_p_asn`).
- **Does:** compute morphological features → run the gradient-boosted model → wrap outputs in
  class-conditional conformal intervals → attach the **top SHAP features** (which inputs pushed this
  score, so it's explainable) → decide abstain.
- **Out:** `scores/wallet_scores.parquet` (`risk_score`, `label`, `conf_low`/`conf_high`, `model`,
  `top_features`), `scores/calibration.parquet` (did our 90%-confidence intervals actually contain
  the truth 90% of the time?), and `scores/eval_report.json` (the graded report card — see §16).
- **Next:** VAANI reads the scores + intervals + top features to write leads. The frontend reads the
  eval report for the honesty dashboards.
- **Files:** `buddhi/features.py` (feature engineering), `buddhi/model.py` (model + conformal
  calibration), `buddhi/stage.py`.
- **`Changed from v1:`** v1's illicit detector was imbalanced and faintly circular, and its strongest
  defence (validation on real data) was *planned, not built*. v2: (1) the **gradient-boosted model is
  the standalone workhorse** (the literature says boosted trees beat fancy graph neural nets under
  honest time-ordered evaluation); (2) it adds **campaign-level recall** as a headline (catching 1 tx
  of a 40-tx laundering chain = catching the chain); (3) — the credibility kill-shot — the *same model
  recipe* is now trained and scored on the **real, independently-labelled Elliptic/Elliptic++**
  dataset (vendored offline), and those real-data numbers ship right next to ours; (4) optional
  self-supervised graph embeddings can be switched on as extra features, but only kept if they
  measurably beat the baseline (`baseline_beaten` gate).

**Think about it.**
- *Why is "beats a fake 0.98 accuracy" the wrong goal?* Because a sophisticated reviewer reads 0.98
  as "you overfit your own synthetic data." An honest ~0.8 that also **replicates on real Elliptic
  data** is a far stronger claim — it proves the method, not the sandbox.
- *What does a conformal interval actually buy you?* Accountability. If we claim 90% coverage, the
  calibration file *measures* whether reality agreed. A model that can't keep its promise gets caught
  on its own slide.

---

## 11 · ⑦ VAANI — write the leads (speech)

**One line:** it turns cold scores into a **ranked queue of plain-English leads**, each with its
reasons *for*, its mandatory reasons *against*, and a flag for the single doubt that could close it.

**The plain story.** "VAANI" means voice. A risk score means nothing to an investigator; a sentence
does. VAANI writes, for each lead: a one-line headline generated from the actual features (not free
text), the evidence *for* it, and — this is mandatory, the pipeline *fails* if any lead lacks it — at
least one piece of **counter-evidence**, a reason it might be wrong. And one counter-finding can carry
`would_clear = true`, meaning "this single doubt, if it holds, is enough to drop the lead." That one
boolean is the difference between a tool that lists worries and a colleague who tells you which worry
actually matters.

- **In:** `scores/` from BUDDHI, `signals/` from SHASTRA (origin + typologies), `graph/` context.
- **Does:** rank subjects into the queue (default top 20) by severity; generate the headline;
  assemble evidence rows and counter rows; set `would_clear`; compute `attribution_ready`.
- **Out:** `alerts/alerts.parquet` (the queue: rank, severity, confidence interval, headline,
  operator-level origin fields, `attribution_ready`), `alerts/evidence.parquet` (reasons for),
  `alerts/counter.parquet` (reasons against, with `would_clear`).
- **Next:** PRAMAAN turns a chosen lead into the formal packet; the frontend's **Leads** screen
  renders the queue and each lead's card.
- **Files:** `vaani/gloss.py` (feature → plain sentence), `vaani/evidence.py`, `vaani/counters.py`
  (the mandatory reasons-against + `would_clear`), `vaani/redact.py` (truncates identifiers to the
  legal display form), `vaani/stage.py`.
- **`Changed from v1:`** the origin fields on each lead moved from host-level to **operator-level**
  (`origin_asn`, `origin_as_org`, `origin_net_class`, `p_asn` + shortlist size); the lone
  `origin_peer_ip` moved to packet-only. `attribution_ready` was redefined for the L1 world: **true
  when operator + net_class + a precise timestamp exist** (the exact host is no longer the gate). A
  new counter kind `cross_asn_ambiguous` fires when the shortlist is split across several operators.

**Think about it.**
- *Why force every alert to carry counter-evidence?* Because a one-sided tool trains investigators to
  trust it blindly, and that's how innocent people get chased. Mandatory counter-evidence makes doubt
  a first-class citizen.
- *What is `attribution_ready` gating?* Whether the packet can print its `{operator · region · UTC}`
  hero as court-ready. If the pieces aren't all there, the packet shows an honest "not ready" state
  instead of bluffing.

---

## 12 · ⑧ PRAMAAN — seal the proof (valid evidence)

**One line:** it takes one lead and turns it into a **single, signed, hash-chained, court-ready
evidence packet** where every number can be replayed and every identifier is legally redacted.

**The plain story.** "PRAMAAN" means proof/evidence. This is where analysis becomes something you can
hand to a court under India's BNSS 2023 (production notice) and BSA 2023 (evidence) laws. It writes a
`packet.json` (the machine record) and a `packet.pdf` (the human document) that state the subject, the
**attribution** (leading with the operator/region), the findings, the counter-findings, the confidence
interval, and a full **chain of custody** — every stage, its inputs, outputs, and hashes, back to the
sealed originals. It appends a leaf to a **Merkle log** (an append-only hash chain, so tampering is
detectable) and signs the packet with an **Ed25519** signature.

Three non-negotiables live here:
1. **No complete identifier on any rendered output.** PDFs and screens show `103.x.x.x`,
   `bc1q4f…9f4d`, txid `4a7f2c91…8b3e`. The full IP exists *only inside `packet.json`*, the machine
   artifact for the authorised officer. A test greps the generated PDFs for a full-address pattern and
   fails on a hit. **But SHA-256 hashes and Merkle roots are printed in full** — the law
   (BSA §63(4)) requires the hash to be complete to be valid evidence.
2. **`replay.expected_packet_sha256` must actually verify.** `make verify-replay` re-runs the whole
   pipeline from the sealed inputs with the recorded seed and checks the packet hash matches. If it
   doesn't, "the packet is not evidence, it is a screenshot."
3. **The Merkle head is printed** so a second analyst can independently check it.

- **In:** a chosen lead from VAANI + the chain of custody accumulated across all `_meta.json` files.
- **Does:** assemble the packet → redact all rendered identifiers → append the Merkle leaf → sign →
  record the replay command + expected hash.
- **Out:** `packets/<case_id>/`: `packet.json`, `packet.pdf`, `notice.pdf` (pre-filled production
  notice), `merkle.log`, `packet.sig`.
- **Next:** this is the end of the line. The frontend's **Proof** screen renders the packet exactly as
  the PDF would look.
- **Files:** `pramaan/packet.py` (assemble), `pramaan/documents.py` + `pramaan/pdflib.py` (render PDF
  offline, no external library that phones home), `pramaan/merkle.py`, `pramaan/ed25519.py`,
  `pramaan/stage.py`.
- **`Changed from v1:`** the on-screen hero changed from `{IP · port · UTC}` to
  **`{operator(ASN) · region · observed UTC}`** (the host IP retreats into the officer-only JSON), and
  `attribution_ready` became a **real field written here** instead of something the frontend had to
  guess. Everything about the hashes, signature, replay, and legal blocks stays byte-for-byte as
  before.

**Think about it.**
- *Why hashes in full but IPs redacted?* Different laws pulling different ways: privacy/redaction law
  forbids showing a full IP on a rendered doc; evidence law *requires* the full hash so the document
  can be verified. The packet obeys both at once.
- *Why does replay matter so much?* Because "we got this answer once" isn't evidence. "Anyone can
  re-run from these sealed bytes with this seed and get the identical signed packet" is.

---

## 13 · The grader you never see: `eval/` + the honesty curve

Not one of the eight stations, but the reason any number is trustworthy. `src/chakravyuh/eval/` is
the **only** code allowed to open the `ground_truth/` answer key. It compares the pipeline's guesses
to the truth and writes the report card (`scores/eval_report.json`).

The single most important thing it produces is the **observer-fraction curve**. A lone headline
accuracy for origin estimation would be meaningless, because the score depends almost entirely on how
much of the network you overhear. So instead of one number, eval reports accuracy **as a curve across
the whole regime ladder** (2%, 5%, 10%, 25%, 50%, 60%, 70% coverage), and in v2 it draws that curve
**per rung of the ladder** — the L1 (operator) curve sits well above the L0 (host) curve, and the L0
curve tracks the published 11–60% literature band. That curve is simultaneously our honesty proof
*and* our flex: we show exactly where we can and can't see.

- **Files:** `eval/validate.py`, `eval/metrics.py`, `eval/labels.py`, `eval/split.py` (the
  time-ordered train/test split).
- **`Changed from v1:`** origin accuracy is now reported **per granularity** (L0/L1/L2/L3), the
  ceiling is reported per granularity (L1 ceiling ≫ L0 ceiling) and reported *first*, and the
  `elliptic_external` real-data numbers ride alongside the synthetic ones.

**The gates (why you can trust the pipeline without reading every line).** Two make-targets are the
trust anchor: `make validate-data` checks for leakage — the "first-announcement" naive rule must
score in the 0.15–0.60 band (if it scored higher, truth is leaking into the observable data); and
`make verify` checks every stage's contracts, the quarantine rule, the replay, and determinism. Green
gates = the system did what it claims. Numbers come from `measurements/<run>/`, **never hand-typed.**

---

## 14 · DRISHTI — what the frontend actually receives and shows

DRISHTI is the eye. It's a React app (in `apps/drishti-v2/`) that runs fully offline. It never reads
Parquet and never runs Python. It reads a **handful of static JSON snapshots** — the same shapes the
live API would serve — imported through one file, `src/data/loader.ts`. Those JSON files are exported
from the backend by `scripts/export_ui_fixtures.py` (off `serialize.py`) and copied into
`apps/drishti-v2/src/data/fixtures/`.

**When does the frontend get data?** At **build time**, not live. For the demo, the JSON is baked in.
The moment a live backend is wanted, you swap the JSON imports in `loader.ts` for `fetch()` calls to
`127.0.0.1:8000` behind the *same names* — nothing else in the UI changes, because the shapes match.

**What files it receives** (each a snapshot of a layer's output):

| Fixture JSON | Comes from | Powers the screen | What the analyst sees |
|---|---|---|---|
| `manifest.json` | KAVACH + run meta | Intake | rows read/sealed/rejected, hashes, the funnel start |
| `transactions.json` | SETU | Untangle | the money/wire split, per-tx facts |
| `graph.json` | JAAL | Map | the fused peer↔money graph (aggregated) |
| `graph-address.json` | JAAL | Map | the address/actor-only view |
| `collapse.json` | JAAL | Map | the cluster **dial** data (watch clusters change) |
| `origin.json` | SHASTRA | Origin | the confident case: L1 operator + region + shortlist rings |
| `origin-abstain.json` | SHASTRA | Origin | the honest "No answer available" case |
| `alerts.json` | VAANI | Leads | the ranked lead queue |
| `alert.json` | VAANI | Leads | one lead's card: evidence, counter-evidence, `would_clear` |
| `packet.json` | PRAMAAN | Proof | the court-ready packet: attribution, hashes (full), signature |
| **`world.json`** *(v2 new)* | eval | World / Globe | the funnel + the per-granularity honesty curve + headline numbers |

**The eight screens = the eight layers, walked in order** (navigation is the top "Thread/Sutra"
sightline, no left sidebar): **Globe** (the world) → **Intake** (KAVACH) → **Untangle** (SETU) →
**Map** (JAAL) → **Origin** (SHASTRA) → **Leads** (VAANI) → **Proof** (PRAMAAN) → **World** (the eval
curves). Press `space` for the **Aperture** — a radial quick-switcher.

**`Changed from v1:`** the big one is **`world.json`** — v1 hardcoded the canonical numbers (41.5%,
the funnel) in the TypeScript, and different screens disagreed with each other. v2 makes them **one
real fixture from the actual run**, so nothing is hand-typed and everything is consistent. Also: the
Origin screen leads with the **operator** verdict and tints the candidate rings by ASN; Leads and
Proof show operator-level attribution; the Proof screen **reads** `attribution_ready` instead of
deriving it; and the Map gains the tx-graph ⇄ actor-graph toggle.

**Three things that are law on the frontend**, so you're never surprised:
- **Every identifier is truncated on screen** (`103.x.x.x`, `bc1q4f…9f4d`) — except SHA-256 hashes and
  Merkle roots, which are shown **in full** (evidence law).
- **All data is also in the DOM**, not trapped inside the 3D canvas — for accessibility and for
  no-WebGL fallback.
- **No network, ever.** Fonts, matcaps, everything vendored locally. It loads with networking off.

---

## 15 · Where we're strong, and where the edges are (say it with confidence)

The posture in the room is **confident rigour**: we are strong *and* we can point to exactly where our
limits are. That beats both "95% attribution!" (an expert instantly reads that as fake) and "we're
weak but honest" (defeatist — don't do this). Both extremes lose. The middle wins.

**Strengths — lead with these:**
- **Operator-level origin (L1) at high accuracy in the agency regime.** We answer the question that's
  legally actionable (which ISP), not the one that's impossible and unshowable (which laptop).
- **A real multi-observer estimator**, not a first-seen guess — and we prove it beats the baseline
  side-by-side (`make compare-estimators`).
- **Real-data replication.** The illicit-detection recipe reproduces on the independent Elliptic
  dataset. This is the "you solved your own invention" kill-shot, answered.
- **Everything is accountable and replayable.** Row counts reconcile at every stage; the packet
  re-runs to the same signed hash; ground truth is quarantined and a test proves it.
- **Honesty is a feature, shown as rigour** — the shortlist, the abstain state, mandatory
  counter-evidence, the tunable cluster dial, the per-granularity coverage curve.

**The honest edges (frame each as a deliberate, defended choice, never an apology):**
- **We can't name the exact host most of the time.** *Defence:* nobody can (11–60%, published), it's
  illegal to display anyway, and L1 is the real answer — we still publish the L0 curve as proof.
- **The 60% "agency" regime is generous.** *Defence:* it's a named national-vantage tier (a monitor
  at IXPs/ISPs), and we publish the full curve down to 2% so the assumption is explicit, not hidden.
- **A minority of cases genuinely slip** — Tor, single-observer, evasive campaigns. *Defence:* that's
  *why* recall is honestly below 1.0; we'd distrust any tool that claimed otherwise.
- **Clustering is only ~0.36 precise.** *Defence:* that's the published reality of the multi-input
  heuristic; we never hard-merge, we show it as a dial, and we attach counter-evidence.
- **The data is synthetic.** *Defence:* it has to be, to have an answer key to measure against — and
  we counter it four ways: the coverage curve matches literature, Elliptic replication on real data,
  real-slice mode (real chain topology), and parameter-holdout (train one regime, test another).

---

## 16 · The "wait, but…" questions (lock in the depth)

**Q: If the data is fake, does anything we measure mean anything?**
Yes — *more* than on real data. On the real chain you can never compute accuracy because the truth is
unknown. Our synthetic world has a locked answer key, so we can actually grade every layer. To prove
we're not just gaming our own sandbox, the illicit model *also* runs on real Elliptic data, and
`real-slice` mode drops real chain topology under our synthetic network.

**Q: Isn't running the demo at 60% coverage rigging it?**
It's choosing the customer's real operating point. NTRO sits at IXPs; it is not a lone academic at
10%. We don't hide 10% — it's on the same curve. We just headline the number the actual buyer gets.

**Q: What stops the pipeline from "cheating" by peeking at the answer key?**
A hard architectural wall: only `eval/` may read `ground_truth/`, and a test greps the whole source
tree to prove no other package references that path. If a truth column ever appears in an observable
file, `make validate-data` fails and every downstream number is declared void.

**Q: How do I know a given layer actually did its job?**
Green gates, not promises. Every stage writes `_meta.json` with `counts.in == counts.out + dropped`;
`make verify` checks every stage's contract, the quarantine, the replay, and determinism; the packet
re-runs to an identical signed hash. You verify the system by running the gates, not by trusting prose.

**Q: What's the difference between a peer, an observer, and the origin — again?**
A **peer** is any Bitcoin computer that relays txs. An **observer** is one of *our* listening peers.
The **origin** is the one peer that first created and sent the tx. Every announcement you see comes
from a peer; you only see the ones that reached an observer; the origin is the peer you're trying to
find among all the relaying peers.

**Q: Address vs wallet vs cluster vs entity?**
An **address** is one envelope for coins. An **entity/wallet** is the real owner controlling many
addresses (invisible to us). A **cluster** is our confidence-weighted *guess* at which addresses share
an owner — a suspected wallet. We never claim a cluster *is* the entity; the dial lets you see how the
guess changes as you demand more confidence.

**Q: Why does `p_origin` not sum to 1, and why is that good?**
Because "the true sender is someone we never observed" is a real outcome, and the missing probability
mass is exactly how we express it. Renormalising to 1 would erase that truth and force a false
certainty. The shortfall is information.

**Q: Where does the money-is-integers rule actually bite?**
Everywhere money is touched. Satoshis as int64 all the way through; convert to BTC only on screen. A
float would drop precision at the 8th decimal, and this number ends up in a court packet — so we never
risk it.

**Q: If I change one setting in `run_config.json`, what happens to the frontend numbers?**
You regenerate the run, eval recomputes, `export_ui_fixtures.py` re-emits the JSON (including
`world.json`), you copy it into the app, and the screens show the new numbers. No number is typed by
hand anywhere, so the whole chain stays consistent by construction.

---

## 17 · The 60-second version (say this out loud)

Bitcoin tracing is a maze: everyone relays everyone's transactions, so "who told us" isn't "who sent
it," and we only overhear part of the network, so some senders are genuinely invisible. CHAKRAVYUH is
our engine for that maze; DRISHTI is the eye that sees through it.

We stopped chasing the exact sender's computer (impossible most of the time, illegal to show) and
instead deliver the **network operator, the region, and a short ranked shortlist with honest
confidence** — the answer that's both achievable and legally actionable, run in the realistic
agency-grade regime a national buyer actually has.

Eight stations, each reading the last one's folder: **MAYAJAAL** builds a world with a secret answer
key, **KAVACH** seals the intake, **SETU** splits wire from money, **JAAL** maps it and clusters
wallets (never hard-merging), **SHASTRA** triangulates the origin like microphones locating a gunshot,
**BUDDHI** scores illicit risk with calibrated uncertainty and proves it on real Elliptic data,
**VAANI** writes plain-English leads with mandatory counter-evidence, **PRAMAAN** seals one signed,
replayable, court-ready packet. The frontend reads snapshots of those outputs as eight screens, fully
offline, every identifier redacted but every hash shown in full.

And the whole thing is trustworthy not because we say so, but because the gates are green: row counts
reconcile, ground truth is walled off, the packet replays to the same hash, and every headline number
comes from a real run — never hand-typed.












