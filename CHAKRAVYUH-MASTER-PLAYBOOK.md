# CHAKRAVYUH
## The Complete Playbook — everything, from the problem to the last question they can throw at you

---

> **Read this once slowly. Read Part 5 twice. Walk into the room with Part 5 in your head.**

---

## How to use this document

| If you have... | Read this |
|---|---|
| 2 minutes | The 60-Second Version, right below |
| 20 minutes | Part 1 + the diagram in Part 2.2 + Part 5.1 |
| An hour | Everything |
| You're outside the cabin door | Appendix A (numbers) + Part 5.1 (killer questions) |

**Five sections:**

1. **The Problem** — what we were asked, why it's hard, why it matters. Nothing about our code.
2. **Our Solution** — the architecture, layer by layer, in plain language.
3. **What's Actually Built** — the real code, the real numbers, honestly.
4. **The Demo** — exactly how the presentation plays out, minute by minute.
5. **The Q&A Arsenal** — every hostile question and how you kill it.

---

# THE 60-SECOND VERSION

Someone sends a Bitcoin transaction. You want to know **who**.

The blockchain tells you *what moved* — amounts, wallets, timing. It never tells you *who*. There's no name attached to a Bitcoin address, ever.

But Bitcoin is a peer-to-peer network. Transactions get announced by real computers with real IP addresses. So the IP is the bridge from a pseudonymous wallet to an actual human being with an actual internet connection.

**The trap:** you cannot just take the first IP you see and call it the sender. Bitcoin *gossips*. Every node re-broadcasts every transaction it hears, after a deliberately randomised delay designed to hide the origin. The first IP you see is almost always a relay. It's an echo, not the shout.

**Our project** fuses the money layer and the network layer into one system that *estimates* the true origin with honest, calibrated confidence — and says "I don't know" when it doesn't know.

**The twist that makes this hard:** to prove a tool like this works, you need data where you already know the right answer. That data does not exist anywhere in the world. So we built it. That generator, **MAYAJAAL**, is the foundation of everything, and it's arguably a bigger contribution than the tool itself.

**Our numbers, measured, not claimed:** on our own honest data, the naive "first IP wins" approach gets it right **22%** of the time. The absolute best anyone could possibly do with what's observable is **41.5%**. We report both, because a tool that claims 95% is lying.

---

# PART 1 — THE PROBLEM

---

## 1.1 What we were actually asked to build

**Problem Statement SIH26146** — *AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic*
**Organisation:** National Technical Research Organisation (NTRO) · **Category:** Software · **Theme:** Cryptocurrency

NTRO is India's technical intelligence agency. It sits under the Prime Minister's Office. That single fact shapes everything about how this tool should be built, and we'll come back to it repeatedly — because it means **cloud-based, foreign-owned, closed-source tools are not an option for them**, no matter how good those tools are.

### What it says, in their words

The background paragraph, quoted:

> *"Bitcoin's pseudonymous, peer-to-peer design lets criminal actors move, layer, and cash out illicit funds — ransomware payments, darknet-market proceeds, extortion, and laundering — while evading traditional financial surveillance."*

And the objective, which is worth reading twice because **the entire architecture is hiding in one sentence**:

> *"The objective of problem statement is to design and build a complete system (**offline**) that ingests bulk Bitcoin transaction/network metadata (in CSV/JSON/XML), **correlates network-layer (IP/port/timing) observations with blockchain-layer (wallet/TXID/amount) data**, and applies AI/ML to detect anomalies, cluster entities, and generate prioritized, explainable investigative leads."*

Read that bolded phrase again. **The problem statement itself names the two layers and asks you to correlate them.** That is not our interpretation — that is the assignment, stated explicitly. Most teams will skim past it and build a blockchain dashboard.

### The five challenge objectives

| # | What they ask for | Where we do it |
|---|---|---|
| 1 | Ingest & parse a bulk metadata dataset (timestamp, src/dst IP & port, TXID, input/output wallet addresses, amounts, fee, script type) | **KAVACH** + **SETU** |
| 2 | Build an entity/transaction graph linking IPs, wallets, and transactions | **JAAL** |
| 3 | Implement an AI/ML detection use case with a working model — *"not just rules"* | **SHASTRA** + **BUDDHI** |
| 4 | Generate a ranked, explainable alert list (why a wallet/transaction was flagged, with a confidence score) | **VAANI** |
| 5 | Present findings via a simple dashboard or link-analysis visualisation | **DRISHTI** |

Note objective 2 says *"linking IPs, wallets, and transactions"* — **three node types, exactly the three JAAL builds.** And note the phrase in objective 3: *"not just rules."* They have anticipated teams submitting a rules engine with an AI label on it. They're telling you in advance that won't pass.

### The four suggested AI/ML focus areas

They name four, and we cover all four:

| Focus area | What they want | Ours |
|---|---|---|
| Entity Clustering | group wallets likely owned by one entity, using common-input-ownership + graph embeddings | **JAAL** |
| Anomaly Detection | flag statistically unusual transactions/flows | **BUDDHI** |
| Peeling-Chain / Mixing Detection | detect laundering-pattern sequences (peeling chains, CoinJoin-like structures) | **BUDDHI**, fed by **MAYAJAAL**'s agent-generated campaigns |
| Risk Scoring | propagate risk scores from seed illicit wallets via algorithms | **BUDDHI** |

### The deliverables, verbatim

- Workable complete **offline** solution for **Linux** platform
- Working prototype (code repo) with ingestion, correlation, and AI/ML model
- Short technical write-up: approach, model choice, and explainability method
- Dashboard/visualisation showing flagged entities and evidence for each flag

*"Offline"* appears twice in this document. *"Linux"* is specified. *"Evidence for each flag"* is specified. These are all sponsor-shaped requirements and we have designed to every one of them.

### The input schema

```
   txid            src_ip        dst_ip        src_port    dst_port
   timestamp       input_addresses           output_addresses
   input_amounts   output_amounts            geo_country      asn
```

Look carefully at that list. It has **two completely different kinds of data mashed into one row**:

```
   ┌─────────────────────────────┬─────────────────────────────┐
   │   BLOCKCHAIN THINGS         │   NETWORK THINGS            │
   ├─────────────────────────────┼─────────────────────────────┤
   │   txid                      │   src_ip, dst_ip            │
   │   input / output addresses  │   src_port, dst_port        │
   │   input / output amounts    │   timestamp (when seen)     │
   │   (fees, derived)           │   geo_country, asn          │
   └─────────────────────────────┴─────────────────────────────┘
        "what money moved"            "who was talking to whom"
```

That is not an accident. The word **"traffic"** in the title is a networking word, not a blockchain word. NTRO is not asking for another blockchain explorer. They're asking for something that reads the *wire*.

**This is the single most important observation in the entire project**, and here's why: most teams will see this schema, notice `src_ip`, and write the equivalent of

```sql
SELECT src_ip FROM transactions WHERE txid = '...'   -- "found the sender!"
```

That answer is wrong. Not "imprecise" — actually, provably, structurally wrong. Section 1.3 explains why. If you understand nothing else, understand that.

---

## 1.2 Bitcoin in five minutes (for judges who don't know, and for you)

You need to be able to explain this to a non-technical judge without blinking. Practice it.

### There are no accounts. There are coins.

Forget bank accounts. Bitcoin works like **cash in envelopes**.

When you receive Bitcoin, you receive a specific sealed envelope with a specific amount in it. That envelope is called a **UTXO** — an Unspent Transaction Output. You don't have "a balance of 5 BTC." You have a drawer with envelopes: one with 2 BTC, one with 2.5 BTC, one with 0.5 BTC.

To spend, you must **tear open whole envelopes**. You cannot take 1 BTC out of a 2 BTC envelope. You destroy the whole envelope and create new ones.

```
   You want to pay 1.2 BTC to a shop.
   Your drawer:  [2.0 BTC]  [0.5 BTC]  [3.0 BTC]

   You open the 2.0 envelope.

           2.0 BTC (torn open)
                │
                ├──────► 1.2 BTC  →  the shop
                ├──────► 0.79 BTC →  BACK TO YOU  ("change")
                └──────► 0.01 BTC →  the miner (the fee)
```

That 0.79 coming back to you is called **change**, exactly like cash change. And it's a goldmine for investigators — we'll come back to it.

### An address is not a person

A Bitcoin **address** is just a string like `bc1q4f…9f4d`. Anyone can create billions of them for free, offline, instantly. There's no registration, no KYC, no name attached. One person might use 10,000 addresses.

So the blockchain is **pseudonymous**: you can see every transaction ever made, perfectly, publicly, forever — and you have no idea who anyone is.

> **The line to say out loud:** *"The blockchain tells you everything about the money and nothing about the people."*

### How a transaction travels

This is the part almost everyone skips, and it's the part our whole project lives in.

When you hit send, your wallet doesn't upload to a server. There is no server. Your computer is connected to a handful of other computers ("peers") in a giant global mesh — roughly tens of thousands of reachable nodes.

Your node tells its peers: *"Hey, I have a new transaction, ID abc123."* That little message is called an **INV** (inventory announcement). Those peers tell *their* peers. And so on, until the whole planet knows in a few seconds.

```
                        YOU
                         │  "I have tx abc123"
            ┌────┬───────┼───────┬────┐
            ▼    ▼       ▼       ▼    ▼
           P1   P2      P3      P4   P5      ← your 8 direct peers
            │    │       │       │    │
        ┌───┴┐ ┌─┴──┐  ┌─┴─┐  ┌──┴┐ ┌─┴──┐
        ▼    ▼ ▼    ▼  ▼   ▼  ▼   ▼ ▼    ▼
       ... the entire network, within seconds ...
```

Bitcoin Core, the standard software, opens **8 outbound connections** by default and accepts up to 125 total. So the first wave of announcements for any transaction is **the originator plus its 8 peers = 9 nodes**. Remember the number 9; it shows up throughout our project.

### The crucial detail: the delay is deliberately random

Here's the thing that makes our problem hard, and it's the single most technically impressive thing you can say in that room.

A Bitcoin node **does not forward a transaction the instant it hears about it.** It waits. And the wait is a **random amount of time, drawn independently for every single peer, for every single transaction**.

Bitcoin Core's defaults: roughly **2 seconds on average toward outbound peers, 5 seconds toward inbound peers**, drawn from an exponential (Poisson) distribution.

**This is not a performance bug. It is a privacy feature, on purpose.** The developers added it specifically to stop people doing what we are doing.

Why does randomness beat a fixed delay? Because with a fixed delay, the transaction spreads out in a clean expanding ring, and you just walk back to the centre. With independent random delays, the ring gets *shredded*. A node three hops away might announce before a node one hop away, purely by luck.

```
   CLEAN CASCADE (fixed delay)          NOISY REALITY (random per-peer delay)
   ────────────────────────────         ────────────────────────────────────
   t=0.0  origin                        t=0.0  origin
   t=1.0  hop 1, hop 1, hop 1           t=0.4  hop 3  ← a distant node, first!
   t=2.0  hop 2, hop 2                  t=1.1  hop 1
   t=3.0  hop 3                         t=1.3  hop 2
                                        t=2.7  hop 1  ← a close node, late
   → walk backwards, trivially solved   → order tells you very little
```

> **Say this in the room:** *"Bitcoin has a built-in defence against exactly what we're trying to do. It randomises the relay delay per peer per transaction, specifically to destroy the ordering signal. That's why the honest published success rates for this problem are between 11% and 60% — that range is from Biryukov and Pustogarov, ACM CCS 2014, and it varies with how much of the network you're observing. Anyone claiming 95% is either lying or leaking."*

**Quick note for accuracy — you may get asked this:** there was a proposal called **Dandelion (BIP 156)** which would have routed transactions through a secret "stem" path before broadcasting. It was **never implemented in Bitcoin Core.** Other coins adopted it; Bitcoin did not. The randomised Poisson delay described above is the *actual* mechanism in the real network today. Knowing this distinction makes you look like you've read the source, not a blog post.

---

## 1.3 The trap: why the obvious answer is wrong

Here's what a typical team will build:

```sql
-- The wrong answer, in one line
SELECT src_ip AS sender FROM traffic WHERE txid = 'abc123' ORDER BY timestamp LIMIT 1
```

"Take the first IP that announced it. That's the sender."

**Why it fails:**

1. **You are almost never watching the originator.** You see maybe 10% of the network. The odds that the actual originator happens to be one of *your* direct peers are low. Usually every IP you see is a relay.

2. **Even when you do see it, the random delay reorders everything.** A relay's announcement can easily arrive before the originator's.

3. **The data has an echo problem.** One transaction produces many rows in the capture — one per observer that saw it. In our reference dataset, **354,023 rows represent only 24,626 transactions.** Roughly 93% of the rows are echo. If you treat every row as "a sender," you're wrong 93% of the time before you even start.

4. **VPNs, Tor, and CGNAT break it further.** A transaction sent over Tor shows you a Tor exit node's IP. That's not the sender and never will be. The correct answer there is *refuse to answer.*

### The number that proves it

We measured this on our own data, where we secretly know every right answer:

| Rule | How often it finds the true originator |
|---|---|
| First IP seen | **22.1%** |
| The IP that announced the most | 21.8% |
| Lowest numeric IP | 0.4% |
| Random guess | 2.9% |

First-seen gets it right about one time in five. **That is the bar every other team will hit and call a solution.**

### The ceiling — our best single insight

Now the number nobody else will have. We asked a question no one thinks to ask:

> *In what fraction of transactions is the true originator's IP even present in the capture at all?*

**Answer: 41.5%.**

In 58.5% of transactions, **the correct answer does not exist in the data**. The originator never announced to any of our observers. No algorithm — not ours, not Google's, not a trillion-parameter model — can find an answer that isn't there.

```
   ALL TRANSACTIONS
   ████████████████████████████████████████████████████████████
   ├──────────── 41.5% ────────────┤├──────── 58.5% ───────────┤
    originator IS in the capture      originator is NOT there
    (an answer is possible)           (the honest answer is
                                       "I don't know")

    Within that 41.5%, first-seen gets 22.1% of ALL transactions,
    which is 53% of everything that was actually achievable.
```

This reframes the entire project:

- A tool reporting "70% accuracy" on this problem is **mathematically impossible** and is either leaking or lying.
- The most valuable feature isn't accuracy. **It's knowing when to shut up.**
- Our real job: get as close to the 41.5% ceiling as we can, and *abstain* on the rest.

> **This is your single best line in the whole presentation:** *"We're the only team that can tell you what the ceiling is. On our data, only 41.5% of transactions even contain the right answer. So for the other 58.5%, our tool says 'I don't know' — and that's the correct answer, not a failure. An investigation destroyed by a confident wrong name is worse than one that got no name at all."*

---

## 1.4 The two layers, and why fusing them is the whole idea

```
   ╔═══════════════════════════════╗       ╔═══════════════════════════════╗
   ║       CHAIN LAYER             ║       ║      NETWORK LAYER            ║
   ║       "the money"             ║       ║      "the wire"               ║
   ╠═══════════════════════════════╣       ╠═══════════════════════════════╣
   ║  • wallet addresses           ║       ║  • IP addresses               ║
   ║  • transaction IDs            ║       ║  • source / dest ports        ║
   ║  • amounts, fees              ║       ║  • exact announcement times   ║
   ║  • inputs and outputs         ║       ║  • country, network operator  ║
   ╠═══════════════════════════════╣       ╠═══════════════════════════════╣
   ║  Public forever. Anyone can   ║       ║  Visible only if you were     ║
   ║  download all of it.          ║       ║  listening at that moment.    ║
   ║                               ║       ║  Gone forever if you weren't. ║
   ╠═══════════════════════════════╣       ╠═══════════════════════════════╣
   ║  Tells you WHAT and HOW MUCH  ║       ║  Tells you WHERE and WHO      ║
   ║  Never tells you WHO          ║       ║  Never tells you WHY          ║
   ╚═══════════════════════════════╝       ╚═══════════════════════════════╝
                    │                                    │
                    └───────────────┬────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │   FUSION — what we build      │
                    │                               │
                    │   money movement  +  identity │
                    │   = an actual investigation   │
                    └───────────────────────────────┘
```

**Why fusion is worth building, in one story:**

A victim in Pune reports losing ₹40 lakh to an investment scam. They have one thing: a Bitcoin address they sent money to.

*Chain-only analysis* (what commercial tools do brilliantly) says: the money went to that address, got split across 40 addresses, peeled through a chain of hops over six days, and ended up at a deposit address belonging to a foreign exchange. **Excellent. And the investigation stops there**, because the exchange is offshore and slow, and every entity in the chain is a random string.

*Add the network layer:* on day two of that chain, three of those transactions were announced by an IP that geolocates to an Indian ISP, from a residential connection, at 3:47 AM IST, from source port 51402.

Now you have something a court can act on. Under **BNSS 2023 Section 94**, an investigator can serve a production notice on that ISP: *"Who was assigned this IP at this timestamp from this source port?"* The ISP answers with a name and an address.

**That's the whole point.** The chain layer tells you the money's story. The network layer is the only bridge from that story to a human being.

### The thing that makes it technically hard

You cannot just do this:

```sql
JOIN chain_data ON network_data.src_ip = chain_data.sender   -- ❌ WRONG
```

Because `src_ip` is *whoever relayed it*, not *whoever sent it*. The join is a lie.

The correct operation is not a join at all. It's an **estimation problem**: gather many noisy observations across many transactions, and infer a probability distribution over candidate originators. That's Layer SHASTRA, and it's the scientific core of the project.

---

## 1.5 The hole in the world: why we had to build our own dataset

### Start here, because this single fact ends the argument before it starts

Section **iii** of the problem statement is titled **"Dataset: Parameters & Synthetic Generation."** It says, verbatim:

> *"Participants will work with a **synthetic dataset** modelled on real Bitcoin P2P/transaction fields (**no real seized or live-intercept data will be provided**). Minimum fields: timestamp, src_ip, dst_ip, src_port, dst_port, txid, input_addresses[], output_addresses[], input_amounts[], output_amounts[], geo_country/asn (integrate open source downloadable Geo IP database)."*

And at the bottom of the problem statement:

> **Dataset Link: Nil**

Read those two things together, because this is the most important paragraph in this entire document:

```
   ┌──────────────────────────────────────────────────────────────┐
   │  The problem statement REQUIRES a synthetic dataset.         │
   │  The problem statement PROVIDES no dataset.                  │
   │                                                              │
   │  → Building the generator is not a workaround.               │
   │  → It is the first mandatory deliverable of the problem.     │
   └──────────────────────────────────────────────────────────────┘
```

**Anyone who asks "why didn't you use real data?" has not read the problem statement.** Real data is explicitly excluded — no seized data, no live intercept. Synthetic data is explicitly required. And since none was supplied, generating it is *compliance*, not a shortcut.

> **The line, and deliver it calmly and without any defensiveness:** *"Section three of the problem statement is titled 'Dataset: Parameters and Synthetic Generation.' It requires a synthetic dataset and states that no real seized or live-intercept data will be provided. The Dataset Link field says 'Nil.' So the dataset was mandated and not supplied. Most teams will hand-write a few thousand rows in a script and move on. We treated it as the first real deliverable and built a full generator with an answer key — because without an answer key, nobody, including us, can measure whether any of this works."*

**Then add the kill shot:** *"And it turns out you cannot buy your way out of this one. There is no real dataset we could have used even if the rules allowed it. Here's why."*

### Why no such dataset exists anywhere in the world

Three separate claims, and only one of them is true.

| Claim | True? |
|---|---|
| "Bitcoin blockchain data doesn't exist" | **False.** All of it is public. Download it today. |
| "Bitcoin network traffic can't be observed" | **False.** Run a node, log the INV messages. Researchers have done it for a decade. |
| "A public dataset with **both layers plus a label saying which peer truly originated each transaction** exists" | **TRUE — it does not exist. Anywhere.** |

### Why that label can never exist for real data

Think about what it would take to *know*, with certainty, that IP `203.0.113.x` truly originated transaction `abc123` in the wild.

You'd need either:
- A confession or a seized device, for every transaction in your dataset, or
- To have already solved the problem you're trying to measure.

That's circular. **You cannot build a ground-truth set for real Bitcoin network origin without already having the answer.**

This is a well-known and genuinely fundamental measurement problem in the field. It's the reason academic results range from **11% to 60%** — different papers, different observer setups, different assumptions, no shared benchmark to compare against. Nobody can even agree on how to score each other.

### So what does everyone else do? They cheat, in one of two ways.

**Cheat 1 — "we sent the transactions ourselves."** Researchers broadcast their own transactions from known IPs and see if they can detect them. Fine, but that's a few hundred transactions from a handful of machines. It doesn't tell you what happens with mixers, CGNAT, Tor, or realistic traffic diversity.

**Cheat 2 — "we assume the first-seen IP is truth."** This is circular reasoning of the worst kind. You're using your baseline as your answer key, so your baseline scores 100% by construction and nothing can ever beat it.

### What we did instead

We built a complete, simulated Bitcoin world — **MAYAJAAL** — where we control everything and therefore *know* everything. Every transaction has a recorded true originator. Every address has a recorded true owner. Every criminal campaign has a recorded true membership.

Then we throw almost all of it away and only record **what a realistic partial observer would have actually seen.**

```
   ┌────────────────────────────────────────────────────────┐
   │  MAYAJAAL simulates the FULL world                     │
   │  ~4,000 nodes, full gossip, every announcement         │
   └───────────────────────┬────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌────────────────────┐    ┌──────────────────────────┐
   │  ANSWER KEY        │    │  THE CAPTURE             │
   │  locked in a vault │    │  only what our 16 spy    │
   │  no analysis code  │    │  nodes actually heard    │
   │  may ever read it  │    │  ~10% network coverage   │
   └────────────────────┘    └──────────────────────────┘
        used ONLY to grade         this is what the tool
        the tool afterwards        is allowed to see
```

> **The line:** *"We didn't invent the problem. We invented the measuring stick. The problem was already there — nobody could measure how well they were solving it."*

### This is standard practice, not a shortcut

Say this if anyone implies you took the easy route:

**IBM** built **AMLSim** and released the **AMLworld** synthetic datasets, and their **NeurIPS 2023** paper argues something counterintuitive and important: for anti-money-laundering benchmarking, **synthetic data is *better* than real data.**

Why? Because in real financial data, most money laundering is *never detected.* So your "not laundering" labels are heavily contaminated with undetected laundering. **Your negative class is poisoned and you can't tell by how much.** A model that scores well on that data might just be good at predicting *what got caught*, which is a completely different thing.

**Tide** (2026) is another open-source generator built on the same reasoning.

We're doing what the field does. In a field where the labels genuinely do not exist any other way.

---

## 1.6 Why this matters in the real world

### The specific gap this fills

Cryptocurrency-enabled crime is large, and India's share of it is large. These four figures are on our deck, each with its source printed beneath it, because **an unsourced number on a slide is worse than no number — it invites the one question you cannot answer.**

```
   $154 bn       received by illicit crypto addresses in 2025, up 162% year on year
                 ── Chainalysis 2026 Crypto Crime Report

   ₹19,813 cr    lost in India in 2025 across 21.8 lakh cheating-fraud complaints
                 on the National Cyber Crime Reporting Portal
                 ── I4C / MHA

   ~77%          of that loss came from investment-scheme fraud — the category
                 that most often settles in crypto
                 ── I4C data via MHA

   ₹8,690 cr     blocked or recovered through the Citizen Financial Cyber Fraud
                 Reporting and Management System, up to January 2026
                 ── I4C / MHA
```

**The fourth number is the one that matters most**, and most people would leave it out. The first three only establish that the problem is big. The fourth proves that **money is recoverable when it's caught early** — which is the entire economic argument for automated triage. Recovery is a race against hours. Faster triage means more victim money frozen before it moves.

If you only have room for two: keep **$154 bn** (establishes the domain) and **₹19,813 cr** (establishes that it's India's problem, in rupees).

### Who actually has this problem

Don't say "law enforcement agencies." That phrase costs nothing to say and earns nothing. Name them:

> **NTRO** · State Cyber Crime cells and CID cyber units · **Indian Cyber Crime Coordination Centre (I4C)** · **Enforcement Directorate** and **FIU-IND** · **CERT-In**

And describe the actual working day, because that's what makes it real:

> A three-officer cyber cell working a crypto extortion complaint **today**: manual joins across capture logs and block explorers, several days of work, and a wallet string at the end of it with nothing legally actionable attached.
>
> The same cell **with CHAKRAVYUH**: a ranked queue in minutes, and the top lead already resolved to the tuple an ISP can act on.

### The operational reality that makes this project matter

```
   WHAT AN INDIAN INVESTIGATOR HAS TODAY
   ─────────────────────────────────────
   ✓ Chain analysis  (via expensive foreign SaaS, or manual explorer work)
        → "the money went here, then here, then to an offshore exchange"
   ✗ Network-layer attribution
        → nothing. no tooling. no capability.
   ✗ Fusion of the two
        → does not exist as a product
   ✗ A sovereign, offline, court-ready evidence pipeline
        → does not exist
```

Chain analysis alone routinely dead-ends at a foreign exchange. Getting KYC records out of an offshore exchange takes an MLAT request — often months, frequently nothing. Meanwhile the trail goes cold.

**A domestic ISP responds to a BNSS §94 production notice in days.** The network layer is often the *faster* path to a human being, and it's the path nobody has tooling for.

### Why the sponsor being NTRO changes the design

This is a point most teams will completely miss, and it's worth hammering.

NTRO is an **intelligence agency**. Consider what that means for tooling:

| Requirement | Why | Do commercial tools meet it? |
|---|---|---|
| **Runs air-gapped** | Investigation data cannot touch the internet | ❌ All cloud SaaS |
| **No foreign dependency** | Cannot send Indian case data to a US company | ❌ Chainalysis, Elliptic, TRM are all US/UK |
| **Auditable internals** | Must justify every conclusion in court | ❌ Proprietary black boxes |
| **Deterministic + replayable** | Defence will demand reproduction | ❌ Not a design goal for SaaS |
| **Indian legal formats** | BNSS 2023, BSA 2023 | ❌ Built for US/EU procedure |

**Every single one of those is a design constraint we've actually implemented**, not a slide bullet:

- The entire pipeline runs offline. Fonts are vendored into the build. The API binds to `127.0.0.1` only, never `0.0.0.0`. There's an automated test that runs the whole demo with networking disabled.
- Same seed in, byte-identical output. Every time. Verified by a gate that runs the pipeline twice in two separate operating-system processes and compares hashes.
- The evidence packet is hash-chained and signed, and pre-fills a **BNSS 2023 §94** production notice.
- **BSA 2023 §63** governs electronic evidence in India and its certificate requires the hash value of the record. Our packet is built around that requirement from the ground up.

> **The line:** *"You cannot solve NTRO's problem by buying a Chainalysis licence. Not because Chainalysis is bad — it's excellent — but because an intelligence agency cannot upload national security investigation data to a foreign company's cloud. That's not a feature gap. It's a sovereignty requirement, and it's why this has to be built domestically."*

---

## 1.7 What "success" actually means here

Push back on the framing before someone else sets it for you.

**Wrong framing:** "How accurate is your tool?"
**Right framing:** "How much of what is *achievable* does your tool achieve, and does it know when it can't?"

The four things we're actually optimising for:

1. **Get close to the ceiling.** Not to 100%. To 41.5%, which is what's physically available.
2. **Abstain correctly.** Refusing to answer when the answer isn't there is a *correct output*, not a failure.
3. **Be calibrated.** When the tool says 80% confident, it should be right about 80% of the time. A well-calibrated 60% is far more useful in an investigation than an overconfident 90%.
4. **Be defensible.** Every output must survive a defence lawyer, a hostile expert witness, and a re-run six months later.

> **Say it:** *"We're not optimising for a big number on a slide. We're optimising for a number an investigating officer can put in a chargesheet without it collapsing in cross-examination."*

---

# PART 2 — OUR SOLUTION

---

## 2.1 The name, and why it's the right one

### CHAKRAVYUH — चक्रव्यूह

On the thirteenth day of the Kurukshetra war, Dronacharya arranged the Kaurava army into the **Chakravyuha** — a spiral, multi-layered battle formation, rotating rings within rings. Almost nobody alive knew how to break it.

Abhimanyu, sixteen years old, knew how to *enter* it. He'd heard the technique while still in his mother's womb. But Arjuna had stopped speaking before explaining how to get *out*. So Abhimanyu broke in alone, fought through ring after ring, and died inside — trapped by **partial knowledge that felt complete**.

Now look at a Bitcoin investigation:

```
   Money enters the maze.                    An investigator enters the maze.
   ─────────────────────                     ────────────────────────────────
   spirals through mixers                    can see every transaction
   peels through hop after hop               can follow every hop
   scatters into rings of addresses          and still cannot find the way out
   relays echo through the network           to a name
```

Bitcoin *is* a chakravyuha. Easy to walk into. Nearly impossible to walk back out of.

And the sharper half of the metaphor, the one worth actually saying in the room: **Abhimanyu died of a partial answer.** He knew the entry and mistook it for the whole thing.

That is *exactly* the failure mode of "the first IP is the sender." It's an answer that feels complete, gets you deep inside, and then collapses. A confident wrong name doesn't just fail — it actively destroys an investigation, because the real suspect is now nowhere near where you're looking.

> **The line:** *"We named it CHAKRAVYUH because the Bitcoin network is a maze you can enter but not exit — and because Abhimanyu died from a partial answer he mistook for the full one. Our system's most important feature is knowing which parts of the maze it hasn't solved."*

### Why Sanskrit names everywhere?

Three honest reasons, and give all three if you're asked:

1. **They're accurate.** Every name describes the component's actual function. These are not decorations bolted on afterward. Section by section below, you'll see the name is often the clearest one-word summary of what the thing does.
2. **Layered names for a layered system.** Chakravyuha *is* a formation of concentric layers. So is our pipeline. The metaphor holds all the way down.
3. **It's built in India, for an Indian agency, under Indian law.** A tool that pre-fills a BNSS §94 notice and satisfies a BSA §63 certificate ought to sound like it came from here.

Expect a judge to latch onto this. It's the most *memorable* thing about the project and it makes the architecture easy to recall. Learn one sentence per name — they're in every section below, in the **"Why this name"** boxes.

---

## 2.2 The whole system, one picture

```
 ═══════════════════════════════════════════════════════════════════════════════
                    THE GROUND WE STAND ON  (built first, built by us)
 ═══════════════════════════════════════════════════════════════════════════════

        ┌─────────────────────────────────────────────────────────────┐
        │                       MAYAJAAL   मायाजाल                    │
        │                       "the web of illusion"                 │
        │   A complete simulated Bitcoin world: entities, a real UTXO │
        │   ledger, a real P2P network with real gossip timing, and   │
        │   criminal agents who improvise rather than follow scripts. │
        │   Produces capture data that looks exactly like real data,  │
        │   plus a sealed ANSWER KEY nothing downstream may ever read.│
        └────────────────┬─────────────────────────┬──────────────────┘
                         │                         │
              capture files                    ANSWER KEY  🔒
              CSV · JSON · XML                 ground_truth/
              (what a spy node                 sealed in a vault
               would really see)               grading only
                         │                         │
 ════════════════════════╪═════════════════════════╪════════════════════════════
                    THE FORENSIC TOOL             ╎  (quarantined — the tool
 ════════════════════════╪═════════════════════════╪═══ cannot see this) ═══════
                         ▼                         ╎
      ┌──────────────────────────────────┐         ╎
 L0   │  KAVACH  कवच   "armour"          │         ╎
      │  The single front door. Hash the │         ╎
      │  raw bytes BEFORE parsing. Seal. │         ╎
      │  Quarantine every bad row with a │         ╎
      │  stated reason. Never guess.     │         ╎
      └──────────────┬───────────────────┘         ╎
                     │  sealed/rows.parquet        ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L1   │  SETU  सेतु   "the bridge"       │         ╎
      │  Split the two grains apart:     │         ╎
      │  announcements vs transactions.  │         ╎
      │  Rename src_ip → peer_ip so no   │         ╎
      │  one downstream can confuse a    │         ╎
      │  relay for a sender. Add geo/ASN.│         ╎
      └──────────────┬───────────────────┘         ╎
                     │  normalised/*.parquet       ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L2   │  JAAL  जाल   "the net"       ★   │         ╎
      │  FUSE BOTH LAYERS INTO ONE GRAPH.│         ╎
      │  addresses + transactions + peers│         ╎
      │  in a single structure. Cluster  │         ╎
      │  addresses by likely owner, with │         ╎
      │  CONFIDENCE, never a hard claim. │         ╎
      └──────────────┬───────────────────┘         ╎
                     │  graph/*.parquet            ╎
                     │                             ╎
        ╔════════════╪═══════════════════════════╗ ╎
        ║   ▼  INTERNAL HACKATHON DEMO ENDS HERE ║ ╎
        ║      (rendered by DRISHTI, below)      ║ ╎
        ╚════════════╪═══════════════════════════╝ ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L3   │  SHASTRA  शस्त्र/शास्त्र          │         ╎
      │  "the weapon" / "the treatise"   │         ╎
      │  THE SCIENTIFIC CORE. For each   │         ╎
      │  transaction, a calibrated       │         ╎
      │  probability per candidate peer  │         ╎
      │  — plus an explicit ABSTAIN when │         ╎
      │  the evidence cannot support any.│         ╎
      └──────────────┬───────────────────┘         ╎
                     │  signals/*.parquet          ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L4   │  BUDDHI  बुद्धि   "the intellect"│◄────────╫── labels, TRAINING
      │  Risk models over wallets and    │         ╎   WINDOW ONLY, through
      │  clusters. Strict time ordering  │         ╎   one audited door
      │  so it can never peek forward.   │         ╎
      │  Conformal prediction: statistical│        ╎
      │  guarantees, not vibes.          │         ╎
      └──────────────┬───────────────────┘         ╎
                     │  scores/*.parquet           ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L5   │  VAANI  वाणी   "speech"          │         ╎
      │  Turn a score into a sentence a  │         ╎
      │  human can act on — carrying its │         ╎
      │  own evidence AND the case       │         ╎
      │  AGAINST itself.                 │         ╎
      └──────────────┬───────────────────┘         ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L6   │  PRAMAAN  प्रमाण   "valid proof" │         ╎
      │  Hash-chained, signed, byte-for- │         ╎
      │  byte replayable evidence packet.│         ╎
      │  Pre-filled BNSS 2023 §94 notice.│         ╎
      │  Built for BSA 2023 §63.         │         ╎
      └──────────────┬───────────────────┘         ╎
                     ▼                             ╎
      ┌──────────────────────────────────┐         ╎
 L7   │  DRISHTI  दृष्टि   "vision"      │         ╎
      │  The interface. Offline, bound to│         ╎
      │  127.0.0.1, restrained and dense.│         ╎
      │  Looks like an intelligence tool,│         ╎
      │  not a startup landing page.     │         ╎
      └──────────────────────────────────┘         ╎
                                                   ╎
      ┌────────────────────────────────────────────▼──────────────┐
      │  EVAL  — the only code in the entire repo permitted to    │
      │  read the answer key. Predictions go in, numbers come out.│
      │  Enforced by an automated test, not by good intentions.   │
      └───────────────────────────────────────────────────────────┘
```

**One direction only.** A layer reads the layer above and writes files below. No layer ever reaches backwards, no layer imports another layer's code. Everything passes through **Parquet files on disk**.

That sounds boring. It's the most important structural decision in the project, and here's why:

- Any layer can be rebuilt, swapped, or debugged without touching the others.
- Two people can work on different layers on the same day with zero merge conflicts. *(This is exactly how the graph-visual work is happening in parallel right now.)*
- Every intermediate state is a file on disk you can open and inspect. When something looks wrong, you can literally look at it.
- Provenance is automatic: every output directory carries a `_meta.json` recording what produced it, from which inputs, with which hashes.

---

## 2.3 MAYAJAAL — the foundation

### माया + जाल — *maya* (illusion) + *jaal* (net, web) = "the web of illusion"

> ### Why this name
> In the Mahabharata, Maya the architect builds the **Maya Sabha** for the Pandavas — a palace so perfectly illusory that Duryodhana walks into a pool thinking it's polished floor, and falls into water thinking it's stone. The illusion isn't decorative. **It's indistinguishable from the real thing to anyone standing inside it.**
>
> That's precisely the design goal. MAYAJAAL builds a Bitcoin world that behaves exactly like the real one from the inside — real UTXO accounting, real gossip timing, real criminal behaviour — but we, standing outside it, know every single truth about it.
>
> And `jaal` means *net*, which is doubly right: it's a network simulator, and a net is what you catch things with.
>
> **One sentence for the room:** *"Maya built an illusion you couldn't tell from reality. That's our data generator: indistinguishable from real capture data, except we hold the answer key."*

### What it actually is

Not a dataset. **A machine that produces datasets.** You turn knobs and out comes a different world. That distinction matters enormously — a fixed dataset gives you one number, a generator gives you a *curve*, and a curve is a scientific result.

Six internal layers:

```
   ┌─ Layer 1 ─ ENTITIES ─────────────────────────────────────────────────┐
   │  A population with real proportions. Ten types:                      │
   │    individual 55% · merchant 12% · mule 12% · service 8%             │
   │    exchange 4% · scam 3% · mixer 2% · darknet_market 2%              │
   │    mining_pool 1% · ransomware 1%                                    │
   │  Each type has its own behaviour: how often it transacts, how much,  │
   │  whether it reuses addresses, how it consolidates funds.             │
   └──────────────────────────────────────────────────────────────────────┘
   ┌─ Layer 2 ─ THE CHAIN ────────────────────────────────────────────────┐
   │  A genuine UTXO ledger. Not a table of fake rows.                    │
   │  Five things it must get right, and does:                            │
   │    • value conservation in exact integer satoshis (no float drift)   │
   │    • change addresses that behave like real change                   │
   │    • multi-input transactions (this is what makes clustering work)   │
   │    • heavy-tailed values (most tiny, a few enormous — like reality)  │
   │    • address reuse, which real people genuinely do                   │
   └──────────────────────────────────────────────────────────────────────┘
   ┌─ Layer 3 ─ THE NETWORK ──────────────────────────────────────────────┐
   │  ~4,000 nodes in a realistic P2P topology. 8 outbound each.          │
   │  Geographic spread with realistic latency between regions.           │
   │  ★ THE CRITICAL PART: relay delay is Poisson, drawn independently    │
   │    per peer per transaction, mean 2s outbound / 5s inbound — the     │
   │    real Bitcoin Core defaults. This is what makes the problem hard.  │
   │  Tor and VPN traffic mixed in, which must produce abstentions.       │
   │  ★ observer_fraction: what % of the network we're listening to.      │
   └──────────────────────────────────────────────────────────────────────┘
   ┌─ Layer 4 ─ THE ADVERSARY ────────────────────────────────────────────┐
   │  Criminals are AGENTS, not patterns. See below — this is the         │
   │  cleverest part of the generator.                                    │
   └──────────────────────────────────────────────────────────────────────┘
   ┌─ Layer 5 ─ EXPORT ───────────────────────────────────────────────────┐
   │  Two separate trees. The capture (what a spy node saw). The answer   │
   │  key (locked away). Formats and messiness chosen to look like real   │
   │  captured data, not like clean simulator output.                     │
   └──────────────────────────────────────────────────────────────────────┘
   ┌─ Layer 6 ─ VALIDATION ───────────────────────────────────────────────┐
   │  44 automated checks. Hard invariants, distribution shapes, and      │
   │  LEAKAGE tests. Detailed in 2.11 — this is the honesty machine.      │
   └──────────────────────────────────────────────────────────────────────┘
```

### The adversary: agents, not patterns

This is the design decision to be proudest of, and it's easy to explain.

**The lazy way** to build criminal data: decide "a peel chain looks like *this*," then stamp 500 peel chains into your dataset.

**Why that's worthless:** you've now built a dataset where the criminal behaviour is defined by a template. Any model will learn the template. You'll report 99% accuracy, and you'll have measured absolutely nothing — because you're detecting *your own stamp*, not laundering.

> **The line:** *"If you stamp a pattern into your data, your detector is just finding the stamp. You've built a very expensive way to detect yourself."*

**What we do instead.** Each criminal entity is an **agent** with a goal (move value from A to safety), a budget, and a menu of moves:

```
   peel       shave a small amount off, keep the big remainder moving
   split      break one amount into several
   merge      pull several amounts back together
   mix        route through a mixing service
   hop        move to a fresh address for no reason but distance
   structure  deliberately keep amounts below a reporting threshold
   dwell      do nothing for a while (patience is a laundering technique)
   cash_out   exit to an exchange — the terminal move
```

At each step the agent picks a move based on its situation and its risk appetite. Sometimes it can't afford the move it wanted and adapts.

**The patterns are not inserted. They emerge.** Two agents with the same goal produce different-looking trails. A peel chain appears because peeling was rational, not because we drew one.

**Measured evidence that this works, and it's a great story:** we ran a diagnostic to check whether campaigns were being cut short by lack of funds. They weren't — across 56 decision points, zero moves failed for affordability. Four of five campaigns ended by *choosing* `cash_out`; one hit its move budget. Because `cash_out` is an absorbing state drawn at roughly 2.6%–12.7% per move, campaign lengths come out **geometrically distributed with a heavy tail of short ones** — which is what real laundering looks like. Nobody designed that distribution. It fell out of the mechanism.

> **That's the tell of a real simulation:** you go looking for a bug, and instead find that a realistic statistical property emerged on its own.

### observer_fraction — the most important knob in the project

```
   observer_fraction = what fraction of the network we are listening to

      0.02  ──  2% coverage   ── hardly anything is attributable
      0.05  ──  5%
      0.10  ── 10% coverage   ← our default. realistic for one agency.
      0.25  ── 25%
      0.50  ── 50% coverage   ── nation-state scale surveillance
```

Turning this knob **reproduces the entire 11%–60% range found in the published literature.** That's not a coincidence — it's strong evidence our simulation captures the real mechanism, because the same parameter that varies between real-world studies produces the same spread of results in ours.

> **The line that wins the methodology argument:** *"We never report a single accuracy number, because a single number on this problem is meaningless without saying how much of the network you were watching. We report the curve. If you tell me your coverage, I'll tell you what's achievable."*

### The four defences (memorise these — this is the attack you will get)

The attack: *"You invented the data, then solved your own invention."*

It's a fair attack. Here are four real answers, not excuses:

| # | Defence | What it means |
|---|---|---|
| 1 | **Parameter holdout** | The tool is evaluated on worlds generated with parameters it was never tuned on. If we'd secretly fitted to our own simulator, performance would collapse there. |
| 2 | **Real-slice mode** | MAYAJAAL can take the **real** Bitcoin transaction graph — a published dataset of 252M nodes and 785M edges over ~13 years — as its chain layer, and synthesise only the network layer on top. The money topology is then genuinely real. |
| 3 | **Report the curve, never the point** | Results are always a function of `observer_fraction`. You cannot cherry-pick a flattering configuration when the whole curve is on the slide. |
| 4 | **Cross-check against real labels** | The chain-layer risk models are validated against **Elliptic** — a real, independently labelled Bitcoin dataset (~203k nodes, ~234k edges, 166 features) that we had no hand in creating. |

**Be honest about the current state:** real-slice mode is *designed and specified*, not built. The architecture has the door in it. Saying "specified, not yet built, and here's exactly where it plugs in" is far stronger than bluffing, because a judge who catches a bluff stops believing everything else you said.

---

## 2.4 L0 · KAVACH — the armoured front door

### कवच — *kavach*, armour

> ### Why this name
> Karna was born wearing **kavacha and kundala** — divine armour fused to his skin, making him invulnerable. Indra had to *ask him to give it away*, because it could not be taken by force.
>
> KAVACH is the armour around the evidence. Every byte that enters the system passes through it and comes out **sealed** — hashed, provenance-stamped, tamper-evident. Nothing enters any other way. There is exactly one door.
>
> **One sentence:** *"Karna's armour couldn't be taken, only given. Our evidence seal is the same: once data is sealed at the door, you cannot alter it downstream without the hash proving you did."*

### What it does

**1. Hash the raw bytes *before* parsing anything.**

This ordering is the entire point and it's a legal requirement, not a technical nicety.

```
   ❌ WRONG:  read file → parse into rows → hash the parsed data
              (the hash now covers YOUR interpretation, not the evidence)

   ✅ RIGHT:  read raw bytes → SHA-256 the bytes → THEN parse
              (the hash covers exactly what you received, byte for byte)
```

If a defence lawyer asks "is this the same file the ISP gave you?", you need a hash of *the file*, not of your parse of the file. **BSA 2023 §63** governs electronic records in Indian courts, and its certificate requirement centres on the hash value. Hashing after parsing would make that certificate unsound.

**2. Detect format from *contents*, never from the filename.**

A file named `.csv` might be JSON. A file named `.json` might be compressed. So KAVACH sniffs the actual leading bytes: `<` means XML, `{` or `[` means JSON, the magic number `0x28B52FFD` means zstd compression (decompress, then sniff again), otherwise treat as delimited text.

*(That zstd case is a real bug we caught: our own generator emits `.zst` files, and the original sniffer would have tried to parse compressed binary as CSV.)*

**3. Refuse to guess about units — this one nearly bit us badly.**

Bitcoin amounts appear as either BTC (`0.00123`) or satoshis (`123000`). Get this wrong by a factor of 100,000,000 and every downstream number is garbage.

Our first rule was "if any value has a decimal point, it's BTC." **That rule is dangerous.** One malformed row in a satoshi file flips the entire column to BTC, multiplies everything by 1e8 — and because it multiplies *consistently*, value conservation still holds, so the safety check never fires. **A silent, total corruption that passes all tests.**

The fix:

```
   all values integer, no fractional part anywhere   →  satoshis
   whole column unambiguously fractional             →  BTC
   mixed or ambiguous                                →  HARD ERROR, naming the column
```

> **The principle, and it runs through the whole project:** *"When the system is unsure, it stops and says so. It never picks the likely option quietly. A loud failure is recoverable; a silent wrong answer is not."*

**4. Quarantine, with a reason, never a silent drop.**

Real data is filthy. Rows will be malformed. KAVACH separates every row into *sealed* (clean) or *rejected* (with a stated machine-readable reason), and the counts must balance exactly:

```
   rows_in  ==  rows_sealed  +  rows_rejected        ← checked automatically
```

You can always answer "what happened to the other 4,000 rows?" That question ends careers in court.

### This is also the answer to "what if NTRO gives you real data?"

**KAVACH is the adaptation point.** Real data arrives with different column names — `source_ip` instead of `src_ip`, `hash` instead of `txid`, `time` instead of `timestamp`. That's handled by an **alias table**: a piece of configuration mapping their names to ours. No code changes. Add rows to a table, re-run.

Everything downstream of KAVACH is already speaking our vocabulary and neither knows nor cares where the data came from.

> **The line:** *"Real NTRO data walks through exactly one door, and adapting to it means adding entries to a name-mapping table. We designed for that from the start because we always assumed the real schema wouldn't match ours exactly."*

---

## 2.5 L1 · SETU — the bridge between two worlds

### सेतु — *setu*, a bridge

> ### Why this name
> **Ram Setu** — the bridge built to reach Lanka, joining two land masses that could not otherwise be crossed.
>
> SETU joins the raw, messy, sealed world to the clean, structured, analysable world. But more precisely, it's the bridge between the **two data layers** — it's the layer that finally separates "what the network saw" from "what the money did," so they can be joined *correctly* later instead of naively.
>
> **One sentence:** *"Setu is the bridge to Lanka. Ours is the bridge from raw capture to clean structure — and the place where the two layers of the problem are formally separated so they can be fused properly later."*

### The one brilliant thing it does: the rename

The incoming data has a column called `src_ip`.

SETU renames it to **`peer_ip`**.

That's it. That's the whole trick, and it's one of my favourite decisions in the project.

**Why it matters:** `src_ip` *sounds* like "the IP that sent this." Any engineer, any analyst, any future team member reading `src_ip` next to a transaction will eventually write the wrong query. It's not a knowledge problem, it's a naming problem — the name invites the mistake.

`peer_ip` means "a peer that told us about this." It does not invite anything. You cannot write `WHERE peer_ip = sender` without noticing you're making something up.

> **The line, and judges love this one because it's so simple:** *"We renamed one column, and that rename encodes the single most important fact in the project. `src_ip` invites you to believe the first IP is the sender. `peer_ip` makes that mistake impossible to write without noticing. We designed the schema so the wrong answer is hard to say out loud."*

### Splitting the grains

One raw row contains two different things glued together. SETU separates them:

```
   ONE RAW ROW
   ┌────────────────────────────────────────────────────────────┐
   │ txid │ src_ip │ src_port │ ts │ in_addrs │ out_addrs │ amt  │
   └────────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
   ANNOUNCEMENTS                  TRANSACTIONS
   one row per "a peer            one row per actual
   said it saw this tx"           transaction
   ─────────────────────          ────────────────────
   txid, peer_ip, port,           txid, inputs, outputs,
   timestamp, geo, asn            amounts, fee
                                  DEDUPLICATED
   ~354,023 rows                  ~24,626 rows
   (≈ 14.4 per transaction)       (the truth of what moved)
```

**This is where the echo problem gets solved structurally.** In the raw capture, one transaction appears ~14 times. If you compute "total volume" over raw rows you'll overstate it by 14×. After SETU, there are 24,626 transactions and 354,023 observations *of* those transactions, and the difference is explicit in the schema instead of being a trap.

It also adds geolocation country and ASN (which network operator owns that IP) — and critically, records **`null`** when it genuinely doesn't know, rather than the string `"unknown"`.

> Small thing, real principle: `null` means "we have no information." `"unknown"` is a *claim* that the answer is unknown. In evidence, those are different, and conflating them means you can't distinguish "we didn't look" from "we looked and found nothing."

---

## 2.6 L2 · JAAL — the fusion (★ the demo centrepiece)

### जाल — *jaal*, a net or web

> ### Why this name
> A `jaal` is a **net** — and a net is two things at once. It's a *mesh*, a structure of interconnected nodes, which is literally what a graph is. And it's **what you catch things with**.
>
> JAAL is also where the two halves of MAYAJAAL's name come home: the illusion-net produced the world, the net catches what moved through it.
>
> **One sentence:** *"Jaal means net. It's a network of connections, and it's the thing you catch things with. Both meanings are the job."*

### What it does

JAAL takes the cleaned two-layer data and builds **one single graph containing both worlds**.

```
   ══════ NETWORK LAYER ══════╗        ╔══════ CHAIN LAYER ══════════════════

      ▲ peer (an IP we saw)   ║        ║   ◆ tx (a transaction)
              │               ║        ║        ▲        │
              │               ║        ║        │        │
              │   ╔═══════════╩════════╩═══╗    │input   │output
              └──▶║   ANNOUNCE EDGE  ★★★   ║────┘        ▼
                  ║  "this peer told us    ║          ● address
                  ║   about this tx"       ║             ┊
                  ║                        ║             ┊
                  ║  ← THIS IS THE FUSION  ║   addresses that likely
                  ╚════════════════════════╝   share an owner form a
                                               CLUSTER, and the cluster
                                               carries a CONFIDENCE number
                                               (≈0.36 on honest data)
                                               ────────┘
```

**Three node types, three edge types. That's it.** Deliberately minimal — a forensic graph that needs a legend with twelve entries is a graph nobody reads under pressure.

```
   NODES                                    EDGES
   ─────                                    ─────
   ● address   a Bitcoin wallet address     → input      address spent INTO a tx
   ◆ tx        a transaction                → output     tx paid OUT to an address
   ▲ peer      an IP seen on the wire       → announce   peer announced this tx  ★ fusion
```

### The announce edge is the entire project in one line

Everything else in this system is plumbing around that edge. It's the only place in any public Bitcoin tooling where "an IP address" and "a money movement" sit in the same structure as first-class connected objects.

**When you present, point at it and stop talking for a second.**

### Clustering with confidence — and why 0.36 is a *good* number

Address clustering means grouping addresses that probably belong to the same owner. Classic heuristics:

**Common-input-ownership:** if two addresses were spent as inputs to the *same* transaction, whoever signed it controlled both keys. Strong. Not certain — CoinJoin transactions deliberately combine inputs from strangers precisely to poison this heuristic.

**Change-address detection:** in a 2-output transaction where one output is a round number and the other is odd, the odd one is probably change returning to the sender.

```
   Transaction: 2.0 BTC in  →  1.20000000 BTC out  +  0.78912447 BTC out
                                    │                        │
                              round-ish                  oddly precise
                              the payment                probably CHANGE
                                                         → same owner as input
```

**Why we attach a confidence number to every cluster instead of just drawing a boundary:** these heuristics are *wrong sometimes, on purpose*. Privacy tooling exists specifically to break them. A cluster drawn as a hard boundary is a claim; a cluster drawn with confidence 0.36 is evidence.

**We expect around 0.36 on honest data**, and that number is not something we invented — **published measurement puts the multi-input clustering heuristic at 0.36 precision on full clusters in law-enforcement use.** Judges may hear that as a weak result. Here's the reframe:

> **The line:** *"Published measurement puts the multi-input clustering heuristic at about 0.36 precision on full clusters in actual law-enforcement use. So we never hard-merge two entities — ownership edges carry a confidence number and the analyst can move the threshold. If our clustering came back at 0.9, we'd treat it as a bug and go hunting for a leak, because real Bitcoin users break these heuristics deliberately. That's what privacy tooling is for."*

**Important caveat for honesty:** 0.36 is the *published expectation* our specification is built around. **JAAL is the next thing being built, so we have not measured our own number yet.** Say "published measurement puts this at 0.36, and our spec treats anything above 0.8 as a leak to investigate" — not "we measured 0.36." If a judge later reads the repo and finds no such measurement, one small bluff discredits everything true you said.

### Three rules JAAL follows

1. **Never permanently merge addresses into one node.** Clusters are a *layer on top* of the graph, never a rewrite of it. In forensics you must always be able to undo a guess — if a cluster turns out wrong six months later, you need the original structure intact underneath.

2. **The graph must never imply that an announcing peer is the sender.** An announce edge means "told us about." Most announcers are relays. The visual must show candidates as candidates. The actual origin answer comes from SHASTRA, as a probability, later.

3. **Never read the answer key.** JAAL builds the graph purely from observable data — exactly as it will have to on real NTRO data, where no answer key exists or ever could.

---

## 2.7 L3 · SHASTRA — the scientific core

### शस्त्र *shastra* (weapon) / शास्त्र *shāstra* (treatise, systematic knowledge)

> ### Why this name — this is the best one, use it
> Two words, one transliteration, and we mean **both**.
>
> **शस्त्र (shastra)** is a weapon. This is the sharp end of the tool — the component that actually names a suspect.
>
> **शास्त्र (shāstra)** is a treatise, a body of rigorous systematic knowledge — as in *Nyāya Shāstra*, *Artha Shāstra*. Formal, disciplined, method-bound.
>
> **A weapon without shāstra is just violence.** This component names suspects, which is the most dangerous thing the system does — so it is bound by the strictest method in the project: calibrated probabilities, statistical coverage guarantees, and an explicit right to refuse.
>
> **One sentence for the room:** *"Shastra is a pun and it's deliberate — शस्त्र is a weapon, शास्त्र is a rigorous treatise. This layer is the weapon, so it's the one held to the strictest method. A weapon without discipline is just violence."*

### The job

For each transaction: a **calibrated probability, for each candidate peer, of being the true originator** — or an explicit **ABSTAIN**.

Not "the sender is X." Rather:

```
   Transaction 4a7f2c91…8b3e

     peer  203.0.xx.xx        p = 0.41    ████████░░░░░░░░░░░░
     peer  198.51.xx.xx       p = 0.22    ████░░░░░░░░░░░░░░░░
     peer  192.0.xx.xx        p = 0.11    ██░░░░░░░░░░░░░░░░░░
     ... 6 others below 0.08

     ⚠ PREDICTION SET at 90% coverage: {203.0.xx.xx, 198.51.xx.xx}
       The true originator is in this set with 90% statistical
       confidence. It is NOT a single-name answer.
```

### Conformal prediction, explained simply

This is the most technically sophisticated idea in the project, and you can explain it without any mathematics.

**The problem with normal ML confidence:** a model says "87% confident." That number is usually meaningless — it's an artifact of how the model was trained, not a real-world frequency. Models are routinely 99% confident and wrong.

**Conformal prediction** gives you a different kind of output with an actual mathematical guarantee:

> *"Here is a **set** of answers. The true answer is in this set at least 90% of the time."*

And that 90% is **guaranteed by the method**, under mild assumptions — not hoped for, not fitted, not a training artifact.

The beautiful consequence:

```
   Easy transaction, strong evidence   →  set = { one peer }     ← a real lead
   Ambiguous evidence                  →  set = { three peers }  ← narrowed, honest
   No usable evidence                  →  set = { }  ABSTAIN     ← say nothing
```

**The set size automatically communicates difficulty.** The model doesn't have to guess how confident to sound — the hard cases produce big sets on their own.

We use **class-conditional (Mondrian) conformal prediction**, which means the coverage guarantee holds *per class* rather than only on average. That matters enormously with our class imbalance of roughly **1:345** — an average-case guarantee can be satisfied entirely by the majority class while the rare class, which is the one you actually care about, gets almost no coverage at all.

**The numbers make the point better than the explanation does:**

```
   At 1:345 class imbalance, targeting 90% coverage:

   plain conformal            rare class actually covered at  53%     ✗
   class-conditional (ours)   rare class actually covered at  90.6%   ✓
```

Plain conformal *technically* hits its 90% target — by covering the common class almost perfectly and the rare class barely half the time. The guarantee is satisfied on average and useless in practice. **The rare class is the entire point of a crime detection system.**

> **The line:** *"Standard ML gives you a confidence number that's basically vibes. Conformal prediction gives you a set with a mathematical coverage guarantee. But plain conformal at our 1:345 imbalance covers the rare class — the criminal one — at only 53%, while still reporting 90% overall. Class-conditional conformal holds it at 90.6%. That distinction is the difference between a guarantee that means something and a guarantee that's technically true and operationally worthless."*

### Abstention is the deliverable

Recall the ceiling: **only 41.5% of transactions even contain the true originator in the capture.**

A system that always produces a name is *wrong by construction* on the majority of cases. Abstention isn't a fallback — it's the mathematically correct output for most inputs.

> **The line:** *"An investigator with 100 confident answers where 58 are fabricated is worse off than an investigator with 41 answers and an honest 'I don't know' on the rest. The second one can be acted on. The first one destroys cases and reputations."*

---

## 2.8 L4 · BUDDHI — the judgment layer

### बुद्धि — *buddhi*, intellect, the discriminating faculty

> ### Why this name
> In Sāṃkhya philosophy, **buddhi** is specifically the faculty of *discrimination* — the power to tell one thing from another and arrive at a determination. It's not memory, not raw perception, not cleverness. It is **judgment**.
>
> That's a classifier, described precisely, two thousand years early. BUDDHI looks at a wallet and discriminates: ordinary or suspicious.
>
> **One sentence:** *"Buddhi isn't 'intelligence' loosely — in Samkhya it's the specific faculty of discrimination, of telling one thing from another. That's exactly what a classifier does."*

### What it does

Risk-scores wallets and clusters using gradient-boosted trees (LightGBM) over behavioural features: transaction timing, value distributions, address reuse, counterparty mix, and graph-structural position.

### Two disciplines that are non-negotiable

**1. Strict time ordering. The model may never see the future.**

The classic, fatal ML mistake in financial crime: train on data from January–December, test on a random sample from the same year. You've now let the model learn from March to predict February. Accuracy looks fantastic. **Deployment performance is a catastrophe**, because in production the future genuinely isn't available.

We enforce a single shared train/evaluate time split used by every stage that needs one. *(This was a real architectural fix: two different stages were originally free to define their own boundary, which would have let future information leak through the origin-probability feature with no test catching it. Now there's one split, and a test that asserts every consumer agrees on it.)*

**2. Calibration, not just accuracy.**

With a 1:345 imbalance, a model that predicts "not suspicious" for literally everything scores **99.7% accurate** and is completely worthless. So accuracy is not a metric we report. We report calibration, per-class coverage, and the precision/recall tradeoff at the operating point.

### Explanation, and counter-evidence

Every score carries **SHAP values** — a per-feature attribution of *why this particular wallet scored the way it did*.

And something I haven't seen elsewhere: **counter-evidence generation.** Alongside the reasons this wallet looks suspicious, the system generates the reasons it might be innocent.

> **The line:** *"Every alert carries the case against itself. If a wallet scores high on rapid consolidation, but that behaviour is also completely normal for a merchant settling daily receipts, the alert says so — in the alert, not in a footnote. An investigator should see the exculpatory evidence at the same moment as the incriminating evidence, not discover it in cross-examination."*

---

## 2.9 L5 · VAANI — the voice

### वाणी — *vāṇī*, speech

> ### Why this name
> **Vāṇī** is speech — Saraswati, goddess of knowledge, is *Vāgdevī*, the goddess of the word. The idea embedded in the name is that **knowledge only becomes useful when it can be articulated.**
>
> A risk score of `0.87` is not knowledge. It's a number. VAANI is the layer that turns it into a sentence a human being can act on.
>
> **One sentence:** *"Vaani is speech. A score of 0.87 means nothing to an investigating officer. This layer gives the analysis a voice — including the part that argues against itself."*

### What it does

Converts scores into structured, plain-language alerts that carry their own justification, their own uncertainty, and their own counter-argument.

```
   ┌──────────────────────────────────────────────────────────────────┐
   │ ⚠  ALERT · cluster c_0142 · elevated risk                        │
   │                                                                  │
   │ WHAT:      8 addresses, likely one owner (cluster confidence 0.36)│
   │ PATTERN:   peel chain — 14 hops over 6 days, each hop retaining   │
   │            92–97% of value, terminating at an exchange deposit    │
   │ NETWORK:   3 of 14 hops announced by peers in AS-xxxxx (IN)       │
   │            earliest announcement 03:47:12 IST, src port 51402     │
   │                                                                  │
   │ WHY FLAGGED (SHAP):                                              │
   │     + hop count well above population median          +0.31      │
   │     + value retention ratio typical of peeling        +0.24      │
   │     + terminal exchange deposit                       +0.19      │
   │                                                                  │
   │ ⚖ COUNTER-EVIDENCE — reasons this may be innocent:               │
   │     · this pattern also fits a merchant settling in tranches     │
   │     · cluster confidence is LOW (0.36); grouping may be wrong    │
   │     · 11 of 14 hops have NO network-layer observation at all     │
   │                                                                  │
   │ ORIGIN ATTRIBUTION:  ⊘ ABSTAINED on 11 of 14 hops                │
   │     originator not present in capture — no answer is available   │
   └──────────────────────────────────────────────────────────────────┘
```

Notice: the alert spends as much space undermining itself as supporting itself. **That is the design.**

---

## 2.10 L6 · PRAMAAN — proof that survives a courtroom

### प्रमाण — *pramāṇa*, a valid means of knowledge

> ### Why this name — the most intellectually precise name in the project
> In **Nyāya**, India's classical school of logic and epistemology, **pramāṇa** is a technical term with a very specific meaning: *the valid means by which knowledge is established*. Not the knowledge itself — **the mechanism that makes a claim count as knowledge.**
>
> The classical pramāṇas include **pratyakṣa** (perception), **anumāna** (inference), and **śabda** (reliable testimony).
>
> Now look at what our evidence packet contains:
>
> | Nyāya pramāṇa | Our packet |
> |---|---|
> | **pratyakṣa** — perception | the sealed capture. what was directly observed. |
> | **anumāna** — inference | SHASTRA and BUDDHI. what was reasoned from it. |
> | **śabda** — reliable testimony | the signed, hash-chained packet itself. |
>
> That is not a stretch. **An evidence packet is literally a pramāṇa**: the formal mechanism by which an observation becomes a claim a court can accept.
>
> **One sentence, and it's your best Sanskrit moment:** *"In Nyaya philosophy, pramāṇa isn't 'proof' loosely — it's the technical term for the valid means by which something becomes knowledge. That's exactly what an evidence packet is: the mechanism that turns an observation into something a court can accept. The name isn't decoration, it's the definition."*

### What it does

Produces a **signed, hash-chained, byte-for-byte replayable evidence packet.**

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  EVIDENCE PACKET                                                │
   ├─────────────────────────────────────────────────────────────────┤
   │  input file SHA-256    (hashed BEFORE parsing, by KAVACH)       │
   │       │  chained                                                │
   │       ▼                                                         │
   │  sealed rows hash  →  normalised hash  →  graph hash            │
   │       │                                                         │
   │       ▼                                                         │
   │  signals hash  →  scores hash  →  final conclusion hash         │
   ├─────────────────────────────────────────────────────────────────┤
   │  code version:  <git commit sha>                                │
   │  config used:   config.effective.json  (exactly what ran)       │
   │  random seed:   recorded                                        │
   ├─────────────────────────────────────────────────────────────────┤
   │  ⚖  PRE-FILLED BNSS 2023 §94 PRODUCTION NOTICE                  │
   │     to: <ISP>, requesting subscriber assigned <IP> at <UTC ts>  │
   │     from source port <port>                                     │
   └─────────────────────────────────────────────────────────────────┘
```

**Replayable** means something strict: hand this packet to the defence, and they can re-run the identical pipeline and get **byte-identical output**. Every hash matches. We enforce this with an automated gate that runs the pipeline **twice, in two separate operating-system processes**, and compares the bytes.

> Why two *processes* and not two runs in one process? Because Python randomises its hash seed per process. Two runs inside one process share a hash seed, so any nondeterminism caused by that seed would be invisible. Two separate processes catch it. That's the kind of detail that separates "we said it's deterministic" from "we tested that it's deterministic."

### The CGNAT problem, and why `src_port` is in the schema

Worth knowing because it explains an otherwise odd column, and it makes you look like you understand operational reality.

Most Indian mobile and broadband subscribers sit behind **Carrier-Grade NAT** — thousands of customers sharing one public IP simultaneously. So "IP 203.0.113.x" alone identifies thousands of people. Useless as evidence.

The tuple that actually resolves to one subscriber:

```
   { public IP  +  source port  +  precise UTC timestamp }
```

With all three, an ISP can pull the specific NAT session mapping and name one subscriber. With only the IP, they cannot, and a defence lawyer will make that point in about four seconds.

> **The line:** *"Notice that `src_port` is in the problem statement's schema. That's not decoration. Behind carrier-grade NAT, an IP address alone identifies thousands of subscribers — it's worthless in court. IP plus source port plus a precise timestamp identifies exactly one. That's why our evidence packet carries all three, and why we keep timestamps at microsecond precision through the whole pipeline."*

---

## 2.11 The honesty machine — how we stop ourselves cheating

This section wins the methodology argument. It's also the part nobody else will have thought about at all.

### The core danger

We built our own data. So the most likely failure isn't a bug — it's **accidentally making the problem easy and not noticing.** A subtle artifact in the generator that gives away the answer would produce spectacular results and a completely worthless system.

We defend against this with three mechanisms that are *code*, not intentions.

### Defence 1 — The quarantine

The answer key lives in a **physically separate directory tree** from the observable data:

```
   data/generated/<run>/     ← observable. any stage may read this.
   ground_truth/<run>/       ← the answer key. 🔒
   measurements/<run>/       ← numbers produced by grading. JSON/Markdown only.
```

Enforced by rules that are automatically tested, not merely documented:

- **Only** code under `src/chakravyuh/eval/` may even contain the *string* `ground_truth`. A test greps the entire source tree and fails the build otherwise.
- Exactly **one** write-only exception exists — the generator's own writer module, allowlisted by exact file path, with a comment in the source reading *"Do not ever widen this allowlist."*
- Labels reach models through **one audited function**, training window only, and never as raw truth.
- **Every stage has a test that physically moves the entire answer key directory away and runs the stage anyway.** If it still works, it genuinely never depended on truth.

> **The line:** *"The quarantine isn't a policy document, it's a test that fails the build. We have a test that deletes the answer key and runs the pipeline. If anything breaks, we cheated somewhere — and we find out in seconds instead of in a judge's question."*

### Defence 2 — Leakage tests, where we actively try to cheat

We wrote deliberately stupid rules and checked whether our own data rewards them. If a dumb rule scores high, the simulation leaked.

| Cheating rule | Score | What it means |
|---|---|---|
| First IP seen | 22.1% | in band. realistic difficulty. |
| Most frequent announcer | 21.8% | in band. |
| Lowest numeric IP | 0.4% | ✅ no ordering artifact |
| Random guess | 2.9% | ✅ baseline |
| **Ceiling (answer even present)** | **41.5%** | the physical limit |

Our specification sets an acceptance band of roughly **0.15 to 0.6** for the first-seen heuristic. Below that band the data is unrealistically hard; above it, something has leaked.

We landed at 0.221. **And we published that number rather than tuning until it looked better.**

> **The line:** *"We wrote cheating rules on purpose and checked whether our data rewards them. If 'pick the lowest IP' had scored well, our simulation would have an ordering artifact. It scores 0.4%. We designed tests to catch ourselves, and we report what they found."*

### Defence 3 — The verification gate

Every stage must pass an identical, non-negotiable gate before it's considered done:

```
   ✓  ruff check + ruff format --check      style and lint
   ✓  mypy                                  type checking (47 files clean)
   ✓  the stage's own test file             correctness
   ✓  make verify-quarantine                the answer key is untouchable
   ✓  TWO FULL RUNS, TWO PROCESSES,         determinism, byte-compared
      byte-identical output
   ✓  staleness check via upstream hashes   inputs haven't silently changed
   ✓  counts.in == counts.out + dropped     no row vanishes unexplained
```

That last one is an accounting identity that runs on every stage. **Not one row may disappear without being counted.**

*A real bug this caught, worth telling:* our `verify-quarantine` target originally passed **vacuously** — the test runner exits successfully when zero tests are selected, so renaming a marker would turn the check green while testing absolutely nothing. Fixed by requiring strict markers *and* a minimum collected-test floor. The check now fails if it finds fewer tests than it should.

> **The line:** *"A green check that tests nothing is worse than a red one, because it actively lies to you. We found one of those in our own build and fixed it."*

---

# PART 3 — WHAT'S ACTUALLY BUILT

> **Read this section before you let anyone open the repo in front of you.**
> The rule for this whole section: **say what exists, say what doesn't, never blur the line.** A judge who catches one exaggeration will discount everything else you said, including the parts that were true and impressive.

---

## 3.1 Status at a glance

```
   ████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░

   ✅ MAYAJAAL     generator, all 6 internal layers        BUILT · VERIFIED
   ✅ L0 KAVACH    sealed intake                           BUILT · VERIFIED
   ✅ L1 SETU      normalise + enrich                      BUILT · VERIFIED
   🔨 L2 JAAL      the fused graph                         NEXT — in progress
   🎨 L7 DRISHTI   graph visual                            IN PARALLEL (teammate)
   ─────────────────────────────────────────────────────────────────
   📋 L3 SHASTRA   origin estimator                        SPECIFIED
   📋 L4 BUDDHI    risk models                             SPECIFIED
   📋 L5 VAANI     alert generation                        SPECIFIED
   📋 L6 PRAMAAN   evidence packet                         SPECIFIED
```

**"Specified" is a real state, not a euphemism for "nothing."** Each of those has a written brief with a goal, its exact inputs and outputs, a definition of done expressed as a shell command that must pass, and a list of known traps. The data contracts between every stage are **frozen** — written down, agreed, and not changeable without an explicit amendment. That's why they can be built quickly and why two people can work on different ones simultaneously.

> **How to say this if asked:** *"Three stages and the generator are built and passing their gates. The graph is being built now. The four after that are specified with frozen data contracts — the interfaces between every stage are already fixed, which is why we can build them in parallel and why nothing downstream is blocked on a design decision."*

---

## 3.2 How to read the repo in 60 seconds

If you open the project in front of a judge, this is the tour. Practice it — fumbling through your own repo is a bad look.

```
   chakravyuh/
   │
   ├── src/chakravyuh/          ← ALL the logic. one folder per layer.
   │   │
   │   ├── mayajaal/            the generator (the world builder)
   │   │   ├── config.py        every knob, one place
   │   │   ├── entities.py      the population: 10 types, their behaviour
   │   │   ├── ledger.py        UTXO accounting, integer satoshis
   │   │   ├── chain.py         builds transactions
   │   │   ├── network.py       P2P topology + gossip + relay timing
   │   │   ├── adversary.py     criminal agents and their moves
   │   │   ├── validate.py      the 44 self-checks
   │   │   └── writers.py       ⚠ the ONE allowlisted truth-writer
   │   │
   │   ├── kavach/              L0 · intake
   │   │   ├── readers.py       CSV/JSON/XML/zstd content sniffing
   │   │   ├── schema.py        the alias table (real-data adaptation point)
   │   │   ├── seal.py          hash-before-parse, seal, quarantine
   │   │   └── __main__.py      CLI entry
   │   │
   │   ├── setu/                L1 · normalise + enrich
   │   │   ├── schema.py        output shapes
   │   │   ├── normalise.py     grain splitting, src_ip → peer_ip
   │   │   ├── enrich.py        geo / ASN attachment
   │   │   └── stage.py         orchestration
   │   │
   │   ├── eval/                🔒 THE ONLY code allowed to read the answer key
   │   │   ├── labels.py        training-window labels, one audited door
   │   │   ├── metrics.py       predictions in → numbers out
   │   │   └── validate.py
   │   │
   │   └── buildinfo.py         git sha of the running code
   │
   ├── scripts/                 ← standalone checkers (deliberately OUTSIDE the pipeline)
   │   ├── peek.py              look at any parquet file  (--counts <col> for histograms)
   │   ├── compare_runs.py      byte-compare two runs
   │   ├── check_sealed.py      validate a sealed output
   │   ├── check_stage.py       validate any stage output
   │   └── check_grain.py       verify row grain is what it claims
   │
   ├── tests/                   ← one test file per stage, plus contract tests
   │   ├── test_contracts.py    the quarantine tests live here
   │   ├── test_chain.py  test_network.py
   │   ├── test_kavach.py  test_setu.py  test_peek.py
   │
   ├── data/generated/<run>/    ← observable data. anything may read this.
   ├── ground_truth/<run>/      ← 🔒 the answer key. only eval/ may read.
   ├── measurements/<run>/      ← grading output. JSON + Markdown only.
   │
   ├── apps/drishti/            ← the frontend (teammate's parallel work)
   ├── run_config.json          ← the template config
   └── Makefile                 ← the orchestrator. every command lives here.
```

### Four things to point out on that tour

**1. One folder per layer, and no layer imports another layer.** Cross-stage imports are forbidden. Stages communicate *only* through Parquet files on disk. This is what makes the layers independently replaceable and lets two people work without conflicts.

**2. `scripts/` is outside the pipeline on purpose.** These are the *checkers*, and they're separate because **a stage that validates its own output is a student marking their own exam.** `check_grain.py` counts rows independently of the code that produced them, so if a stage miscounts, the disagreement surfaces immediately.

**3. Three sibling data trees, not one.** `data/generated/`, `ground_truth/`, `measurements/`. The separation is physical, not conventional, and it's enforced by tests.

**4. The Makefile is the only interface.** Nobody runs Python directly. Every action is a make target, which means every action is recorded, repeatable, and identical on every machine.

```bash
   make run-mayajaal     # generate a world
   make run-s03          # KAVACH: seal a capture
   make run-s04          # SETU: normalise and enrich
   make verify-s04       # run the full gate on S04
   make verify-quarantine # prove the answer key is untouchable
   make fixtures-ui      # export sample JSON for the frontend
```

---

## 3.3 The data flow, with real numbers

This is the actual measured path through the built stages. **These numbers are from real runs, not estimates.**

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  MAYAJAAL                                                           │
  │  generates a world from run_config.json                             │
  └──────────────────────────┬──────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ╔══════════════════════╗    ╔═══════════════════════════════╗
   ║  THE CAPTURE         ║    ║  🔒 ANSWER KEY                ║
   ║  354,023 rows        ║    ║  true originator per tx       ║
   ║  across 2 shards     ║    ║  true owner per address       ║
   ║  CSV / JSON / XML    ║    ║  true campaign membership     ║
   ║  .zst compressed     ║    ║                               ║
   ╚══════════╤═══════════╝    ║  NOTHING BELOW READS THIS     ║
              │                ╚═══════════════════════════════╝
              ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  L0 · KAVACH                                                        │
  │  SHA-256 the raw bytes FIRST · sniff format from content            │
  │  detect units (sats vs BTC) or HARD ERROR                           │
  │  → sealed/rows.parquet   +   rejected rows, each with a reason      │
  │  ✓ rows_in == rows_sealed + rows_rejected   (checked every run)     │
  └──────────────────────────┬──────────────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  L1 · SETU                                                          │
  │  split the grains · src_ip → peer_ip · attach geo + ASN             │
  │                                                                     │
  │    announcements: 354,023 rows   ("a peer told us about this tx")   │
  │    transactions:   24,626 rows   (what actually moved)              │
  │                    ─────────────                                    │
  │                    ≈ 14.4 announcements per transaction             │
  └──────────────────────────┬──────────────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  L2 · JAAL   ← being built now                                      │
  │  → graph/{nodes,edges,clusters}.parquet                             │
  └──────────────────────────┬──────────────────────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  make fixtures-ui  →  data/fixtures/ui/graph.json                   │
  │  ← this JSON file is the seam where the teammate's work plugs in    │
  └─────────────────────────────────────────────────────────────────────┘
```

### The two numbers to have memorised

**354,023 → 24,626.** Capture rows to actual transactions. Roughly 14 to 1.

That ratio *is* the echo problem, quantified. **93% of the rows in the capture are re-announcements of a transaction you've already seen.** Every team that treats a capture row as "a transaction" is inflating every count they produce by roughly 14×.

> **The line:** *"Our reference capture is 354,023 rows. It contains 24,626 transactions. Every other row is an echo. If you don't separate those two grains in your schema, every volume statistic you produce is wrong by a factor of fourteen, and you won't notice — because it's wrong consistently."*

### Why 14 and not 9?

Someone sharp may catch this, so know the answer cold. **They are two different quantities:**

- **9** is the size of the *first wave* — the originator plus Bitcoin Core's 8 default outbound connections. It's a property of **the Bitcoin protocol**.
- **14.4** is how many times *our observers* saw each transaction. It's a property of **how many observers we deployed** (`n_observers = 16`). Transactions get re-announced repeatedly across the network, and with 16 listening posts you catch more than the first wave.

> **Say:** *"Nine is the protocol's first wave: originator plus eight default outbound peers. Fourteen is what our sixteen observers actually recorded. Different quantities — one is about Bitcoin, one is about our deployment."*

---

## 3.4 Stage by stage, what it does and what it cost us

### MAYAJAAL · the generator — ✅ built

Configured entirely from `run_config.json`. The knobs that matter: `seed` (default 42), `target_rows` (1,000,000), `observer_fraction`, `n_observers`, the entity mix, `relay_delay_outbound_mean_s` / `relay_delay_inbound_mean_s`, Tor and VPN shares, campaign count and budgets.

**Scale:** at ~14.4 announcements per transaction, a 1,000,000-row target is roughly 66,000 transactions. To make a bigger dataset, raise `target_rows` and re-run — it's a machine, not a file.

**44 validation checks** run automatically. Three real bugs they caught, each worth telling because each is a good story:

**Bug 1 — addresses were not unique.** Our address-minting padded short addresses with the character `"2"`. But `2` **is a valid hex digit**, so two different entities could mint the identical address. Result: 151 addresses owned by 2+ entities. Fixed by padding with a non-hex base58 character.

> Why it matters: a forensic tool where two people can share an address is not a forensic tool. Address identity is the atom everything else is built on.

**Bug 2 — every transaction ID ended in the same 8 characters.** Our truncation policy shows the first 8 and last 4 characters of a txid. If every txid shares the same last 4, that half of the display **carries zero information** — you've made them look distinguishable while they aren't. Fixed by deriving txids as a hash of the transaction's actual serialised contents, using block height as the coinbase nonce (which is what **BIP34** specifies in real Bitcoin).

**Bug 3 — the Jarque-Bera test was the wrong test.** We were using it to check that transaction values are heavy-tailed. But Jarque-Bera tests for **non-normality**, and a uniform distribution is also non-normal — it would pass while being the opposite of heavy-tailed. Replaced with explicit quantile-ratio floors: p99/p50, p99.9/p50, and mean > median.

> **This is a great answer to "how do you know your data is realistic?"** — *"We had a statistical test that was technically passing and testing the wrong property. We caught it, replaced it with quantile ratios that test the thing we actually care about, and the data still passed. Finding that one mattered more than any test that was already green."*

**And a diagnostic that refuted our own theory,** which is the best kind of story to tell:

We suspected criminal campaigns were being cut short by running out of money. We instrumented it. **Zero of 56 decision points failed for affordability.** Four of five campaigns ended by *choosing* `cash_out`; one hit its move budget. Campaign length is geometric because `cash_out` is an absorbing state drawn at 2.6%–12.7% per move. **Our hypothesis was simply wrong, and the data was fine.**

> **The line:** *"We went looking for a bug, found our own hypothesis was wrong, and documented that. That's the part of the process nobody puts on a slide, and it's the part that means the numbers are real."*

---

### L0 · KAVACH — ✅ built

Full behaviour is in section 2.4. What it cost us:

**The units trap (the scariest bug in the project).** Covered in 2.4 — "any decimal means BTC" would let one malformed row silently multiply an entire column by 100,000,000 while still passing conservation checks. Now: all-integer means satoshis, unambiguously-fractional means BTC, **anything mixed or ambiguous is a hard error that names the offending column.**

**The zstd trap.** MAYAJAAL emits `.zst` compressed files. The content sniffer checked for `<` (XML) and `{` (JSON) and fell through to CSV otherwise — so it would have tried to parse compressed binary as text. Fixed by detecting the zstd magic number `0x28B52FFD` and decompressing *before* sniffing.

**The provenance trap.** The seal recorded `code_version`, but it was recording the *package version* (`0.1.0`) — identical to `tool_version` and therefore useless. You could not trace a sealed output back to the commit that produced it. Fixed with `buildinfo.py`, which returns the git sha in one of three honest forms:

```
   "a3f91c2e8b04"          clean checkout, exactly this commit
   "a3f91c2e8b04-dirty"    this commit plus uncommitted changes
   "unknown"               not a git checkout at all
```

The `-dirty` marker is the important one. **An evidence packet produced from uncommitted code must say so**, because that code cannot be recovered later. And this field is deliberately **not** excluded from determinism comparisons — if the code changed, the output *should* differ.

---

### L1 · SETU — ✅ built

Full behaviour in section 2.5. What it cost us:

**The Polars aggregation bug.** `pl.lit(None).first()` inside a `group_by().agg()` raises *"cannot aggregate a literal."* Fixed by materialising optional columns before the group-by. Small, but the kind of thing that eats an hour.

**The null-versus-"unknown" decision.** When geolocation can't resolve an IP, `net_class` is left as **`null`**, not the string `"unknown"`. As covered in 2.5: `null` means no information; `"unknown"` is a claim. In evidence, you must be able to distinguish "we didn't look" from "we looked and found nothing."

---

### L2 · JAAL — 🔨 next

Full design in section 2.6. Outputs `graph/{nodes,edges,clusters}.parquet`, then `make fixtures-ui` converts that to `graph.json` for the frontend.

**Known traps already written into its brief**, before a line is written:

- **Clustering precision above 0.8 means a leak, not a breakthrough.** Investigate, don't celebrate.
- Never permanently merge address nodes. Clusters are a layer on top.
- Cluster metrics go to `measurements/<run>/cluster_metrics.json` — **not** into `scores/`, which belongs to a later stage.

---

### L7 · DRISHTI — 🎨 in parallel

Being built by a teammate against a **frozen JSON contract**, which is why parallel work is possible without conflict:

```json
{
  "run_id": "s02-final",
  "stats": { "n_nodes": 1234, "n_edges": 5678, "n_clusters": 90 },
  "nodes": [{ "id": "n_00001", "type": "address", "label": "bc1q4f…9f4d",
              "layer": "chain", "cluster_id": "c_012", "size": 3, "risk": null }],
  "edges": [{ "source": "n_00001", "target": "n_00042", "type": "input", "weight": 1 }],
  "clusters": [{ "id": "c_012", "confidence": 0.36, "size": 8, "label": "cluster 12" }]
}
```

He builds against a sample file. JAAL later produces the real one at the same path, in the same shape. **The integration is one wire.**

**Stack, locked and non-negotiable:** React + TypeScript + Vite, CSS Modules (no Tailwind, no Material, no shadcn, no component library), **cosmos.gl** for the GPU force-directed graph, ECharts fully re-themed for charts, IBM Plex Sans + IBM Plex Mono **vendored as woff2 files** — no CDN, no Google Fonts, because the demo must run with the wifi off.

---

## 3.5 The truncation rule (know this before anything goes on a screen)

**No complete identifier appears anywhere on any screen or slide. Ever.**

Truncation happens **at write time, not at render time.** The full value never enters the display layer at all, so it cannot leak through a tooltip, a copy-paste, a CSV export, or a screenshot.

```
   IPv4        first two octets only        203.0.xx.xx
   IPv6        first two hextets only       2001:0db8:…
   address     first six + last four        bc1q4f…9f4d
   txid        first eight + last four      4a7f2c91…8b3e

   SHA-256 hashes and Merkle roots:  PRINTED IN FULL, deliberately
```

**Why hashes are the exception:** a hash is the thing a court needs disclosed under **BSA 2023 §63(4)**. Truncating it would destroy its entire evidentiary purpose. A hash also reveals nothing about the underlying identity — that's the point of a hash.

> **If a judge asks why identifiers are cut off:** *"That's deliberate and it's at the data layer, not the display layer — the full value never reaches the screen. Real capture data is intercept metadata, and a demo screen gets photographed. Hashes are the one thing we print in full, because Section 63(4) of the Bharatiya Sakshya Adhiniyam requires the hash value to be disclosed, and a truncated hash proves nothing."*

**This is a detail that makes you look serious.** Most teams will have full wallet addresses splashed across their demo without a second thought.

---

## 3.6 Being straight about what isn't built

Rehearse these. Delivered calmly and without apology, admitting a limit *builds* credibility. Delivered defensively, it destroys it.

| If asked | Say exactly this |
|---|---|
| "Is the origin estimator working?" | *"Not yet. It's the next major stage after the graph. What we have measured is the baseline it has to beat — first-seen at 22.1% — and the ceiling it can't exceed, 41.5%. We're one of the few teams that knows both of those numbers before writing the model."* |
| "Did you measure clustering precision?" | *"Not our own number yet — the graph stage is being built now. Published measurement puts this heuristic at about 0.36 precision in law-enforcement use, and our spec flags anything above 0.8 as a leak to investigate rather than a result to celebrate."* |
| "Does real-slice mode work?" | *"Specified, not built. The architecture has the door in it and the chain layer would come from a published dataset of 252 million nodes. It's the highest-value thing after the estimator."* |
| "Is the evidence packet done?" | *"Specified. The hashing it depends on is already live — intake hashes raw bytes before parsing, and every stage output carries provenance. The packet is the assembly of things that already exist."* |
| "How much is actually working?" | *"The generator and three stages, all passing an identical seven-point gate. The graph is in progress. Everything after that is specified with frozen contracts."* |

> **The meta-line, worth saying once:** *"We'd rather show you three stages that genuinely pass a strict gate than eight stages that mostly run. The gate is the same for every stage and it includes running the whole pipeline twice in separate processes and comparing the output byte for byte."*

---

# PART 4 — THE INTERNAL HACKATHON, START TO FINISH

> This is a **plan**, not a script to memorise word for word. Memorised presentations sound memorised. Learn the *beats* and the *lines in bold*; improvise the connective tissue.

---

## 4.1 The one decision that shapes everything else

**You are not presenting a finished product. You are presenting a solved hard problem and a half-built tool.**

Those need completely different presentations, and picking the wrong one is how strong teams lose.

```
   ❌ THE TRAP                          ✅ WHAT YOU DO INSTEAD
   ──────────                           ──────────────────────
   Demo the features you have,          Lead with the INSIGHT nobody else has,
   apologise for the ones you           show the working code as PROOF you can
   don't, hope nobody asks              execute, and name the remaining work
                                        with dates and definitions of done

   Sounds like: "we ran out of time"    Sounds like: "we know exactly where we are"
```

Your genuine advantages are not features. They are:

1. You know the **ceiling** (41.5%). Nobody else will even know that a ceiling exists.
2. You know the **baseline** (22.1%) because you built the measuring stick.
3. You understand **why the obvious answer is wrong**, and you can prove it in 20 seconds.
4. Your architecture is **already built to the exact deliverables** the problem statement names.

**None of those require the tool to be finished.** All of them require you to explain well. So the presentation is 70% explanation and 30% demo — and that's a strength, not a compromise.

---

## 4.2 The night before

A short checklist, because the failures here are stupid and preventable.

**Technical**
- Run the full pipeline end to end, **on the actual demo laptop**, **with the wifi off**. Not on your machine. Not with wifi on.
- Screenshot or screen-record every screen you plan to show. **This is your parachute.** If the live demo dies, you keep talking over stills and most people won't even register that something broke.
- Have the reference run's numbers open in a terminal you can point at.
- Charge everything. Bring the adapter. Check which connector the projector uses.

**Content**
- Print or open **Appendix A** (the numbers) and **Part 5.1** (the killer questions).
- Decide, out loud, who answers which category of question. See 4.6.
- Say the 90-second opener out loud three times. Time it. It is always longer than you think.

**The one rehearsal that actually matters**
- Have someone who isn't on the team ask you: *"So you made up your own data and then solved it? Isn't that cheating?"* Answer it out loud. If the answer isn't smooth and unbothered, rehearse it until it is. **That question decides your result.**

---

## 4.3 The run of show

Assume roughly 10 minutes plus questions. Compress or expand the demo section; never compress the first two minutes.

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │ 0:00  THE HOOK                                             90 sec    │
   │ 1:30  THE PROBLEM, AND WHY IT'S HARD                        2 min    │
   │ 3:30  THE ARCHITECTURE (Slide 3, the pipeline)              2 min    │
   │ 5:30  THE DEMO                                              3 min    │
   │ 8:30  WHERE WE ARE, HONESTLY                                1 min    │
   │ 9:30  THE CLOSE                                            30 sec    │
   │──────────────────────────────────────────────────────────────────────│
   │ Q&A   → Part 5                                                       │
   └──────────────────────────────────────────────────────────────────────┘
```

---

### BEAT 1 · 0:00–1:30 · The hook

**Goal: in 90 seconds, make them understand that the obvious answer is wrong.** If they leave with only one thing, this is it.

**Slide 1** is the title slide. Do not talk over it for more than one sentence.

> *"SIH26146, from NTRO. CHAKRAVYUH — an offline forensic workstation for Bitcoin traffic."*

**Move to Slide 2.** Its verdict line is the thesis:

```
   Nine peers announce the same transaction. Only one of them sent it.
   We score all nine, because the shortcut ends at the wrong door.
```

Then the spoken version:

> *"This problem statement is unusual, and most people will miss why. The dataset carries blockchain fields AND network fields — IPs, ports, announcement timings. Both layers, in one place.*
>
> *The obvious move is to join them on `src_ip` and call that the sender. That's wrong.*
>
> *Bitcoin doesn't broadcast — it **gossips**. Your transaction goes to a few peers, they pass it on, and every hop announces it again. So the same transaction shows up in the capture announced by around nine different peers, and eight of them are just forwarding it. Worse: Bitcoin deliberately randomises the delay before each peer forwards, per peer, per transaction — specifically to destroy the ordering that would give the sender away.*
>
> ***So the first IP you see is an echo, not the shout.***
>
> *In a real case, that shortcut points at an innocent person's internet connection. So instead of guessing, we estimate the probability that each peer is the originator — and we show what came second."*

**If there's a whiteboard, draw this while talking. It lands harder than any slide:**

```
        YOU ──┬──► peer ──► peer ──► peer
              ├──► peer ──► peer
              └──► peer ──► peer ──► peer

        capture sees:  9 IPs announced this transaction
        truth:         1 of them sent it
        naive tool:    picks whichever appeared first
        reality:       the delays are RANDOM, so first ≠ sender
```

**Then pause.** Let it sit for a beat before moving on. The pause is doing work.

---

### BEAT 2 · 1:30–3:30 · Why it's hard, and the number nobody else has

**Goal: establish that you've measured this problem, not just described it.**

> *"So we asked the obvious question: how well does the naive approach actually do? To answer that you need data where you already know the right answer — and that data does not exist anywhere in the world, for a reason I'll come back to.*
>
> *So we built it. And then we measured."*

**Put these four numbers up, or write them on the board:**

```
   first IP seen wins             22.1%
   most frequent announcer        21.8%
   lowest numeric IP               0.4%
   random guess                    2.9%
   ─────────────────────────────────────
   ★ THE CEILING                  41.5%
     (how often the true sender is even IN the data at all)
```

> *"First-seen gets it right about one time in five. That's the bar.*
>
> *But the number that actually matters is the last one. **In only 41.5% of transactions is the true originator present in our capture at all.** In the other 58.5%, the correct answer simply isn't in the data. No algorithm can find an answer that isn't there.*
>
> *That reframes the whole problem. Anyone who tells you they get 90% on this is either leaking or lying. Our job isn't to maximise a number — it's to get close to 41.5% and to say 'I don't know' on the rest.*
>
> ***An investigator with a hundred confident answers, where fifty-eight are fabricated, is worse off than one with forty honest answers.*** *A wrong name doesn't just fail — it sends an investigation to the wrong door."*

**Then, briefly, the dataset point. Don't over-explain — one clean pass:**

> *"On the data: section three of the problem statement is titled 'Dataset: Parameters and Synthetic Generation.' It requires a synthetic dataset, states that no real seized or live-intercept data will be provided, and the Dataset Link field says 'Nil.'*
>
> *So the dataset was mandated and not supplied. Most teams will write a script that spits out random rows. We built a proper generator — a real UTXO ledger, a real P2P topology, Bitcoin Core's actual relay timing defaults, and criminal agents that improvise instead of following templates. And crucially, it comes with an answer key, which is the only reason any of those numbers I just showed you exist."*

---

### BEAT 3 · 3:30–5:30 · The architecture

**Goal: show that this is engineered, not assembled. Use Slide 3.**

Verdict line: **"Eight sealed stages. One command. No network adapter."**

**Walk the pipeline diagram, one line each. Do not linger. Rhythm matters more than detail here:**

> *"MAYAJAAL builds the world and holds the answer key.*
> *KAVACH is the front door — it hashes the raw bytes before parsing anything, because a hash taken after parsing covers your interpretation, not the evidence.*
> *SETU normalises and enriches. It renames `src_ip` to `peer_ip`, and that rename is deliberate — it makes the most common mistake in this problem impossible to write without noticing.*
> *JAAL is the fused graph. IPs, wallets and transactions in one structure. **This is the centrepiece.***
> *SHASTRA estimates the origin, with calibrated probability and an explicit right to abstain.*
> *BUDDHI scores risk. SHAP for explanation, and counter-evidence generated alongside every alert.*
> *VAANI turns scores into sentences an officer can act on.*
> *PRAMAAN produces the signed, hash-chained, replayable evidence packet — with a pre-filled BNSS Section 94 production notice.*
> *DRISHTI is the console. Offline, bound to localhost."*

**Then the three things that make it engineering rather than a script:**

> *"Three things hold this together. First, **data flows one way** — no stage imports another, they communicate only through files on disk, which is why we can build in parallel.*
>
> *Second, **the answer key is quarantined**. It lives in a separate directory tree, only one module is allowed to read it, and we have a test that physically moves it away and runs the pipeline anyway. If anything breaks, we cheated somewhere.*
>
> *Third, **every stage passes the same gate**: lint, types, tests, the quarantine check, and two full runs in two separate operating-system processes, compared byte for byte. Two runs in one process can't catch hash-seed nondeterminism, because one process has one hash seed."*

**If they nod at the Sanskrit names — and they will — give them one line, then move on:**

> *"Every name does real work. Pramaan is the Nyaya term for the valid means by which something becomes knowledge — which is exactly what an evidence packet is. Shastra is a deliberate pun: शस्त्र is a weapon, शास्त्र is a rigorous treatise. That layer names suspects, so it's the one held to the strictest method."*

**Don't dwell.** Deliver it lightly and keep moving. Confidence is in the brevity — it should sound like an obvious detail, not a flourish you rehearsed.

---

### BEAT 4 · 5:30–8:30 · The demo

**Goal: prove the code is real. Not to show every feature.**

**The order matters.** Go dumb-to-smart, so the graph lands as a payoff:

**① The raw data (20 seconds).**
Open one capture file. Let them see it's genuinely messy — mixed formats, compression, real-looking columns.
> *"This is what a capture looks like. Three hundred and fifty-four thousand rows."*

**② Intake (30 seconds).**
Run the seal. Point at the hash and the quarantine count.
> *"Raw bytes hashed before anything is parsed. Rows that couldn't be trusted are quarantined with a stated reason, and the counts have to balance — rows in equals rows sealed plus rows rejected. We can always answer 'what happened to the other four thousand rows?'"*

**③ The grain split (30 seconds). This is an underrated moment — use it.**
> *"Three hundred and fifty-four thousand announcement rows. Twenty-four thousand actual transactions. Every other row is an echo of one you've already seen.*
>
> *If you don't separate those two grains, every volume number you produce is wrong by a factor of fourteen — and you won't notice, because it's wrong consistently."*

**④ THE GRAPH (90 seconds). This is the moment. Slow down.**

Show the fused graph. Then do these three things, in this order:

```
   a) Toggle to CHAIN ONLY
      "This is what every blockchain tool in the world shows you.
       Wallets and transactions. No people."

   b) Toggle to NETWORK ONLY
      "This is what a network analyst sees. IPs talking. No money."

   c) Toggle to BOTH  ← let it snap together, and stop talking
      "This is the fusion. That edge in the middle — a peer announcing
       a transaction — is the only place in any public Bitcoin tooling
       where an IP address and a money movement sit in the same
       structure as connected objects. Everything else we build is
       plumbing around that one edge."
```

**Then click a cluster:**
> *"Addresses we think share an owner. Notice it carries a **confidence number**, and notice the boundary is drawn softly. We never hard-merge two entities, because published measurement puts this heuristic at around 0.36 precision in real law-enforcement use. If ours came back at 0.9, we'd go hunting for a bug."*

**⑤ Truncation (10 seconds, in passing).** Somebody will notice the cut-off identifiers. Get ahead of it:
> *"You'll notice no full addresses or IPs anywhere. That's enforced at the data layer, not the display layer — the full value never reaches the screen. Hashes are the one thing we print in full, because Section 63(4) of the Bharatiya Sakshya Adhiniyam requires the hash value to be disclosed."*

**If the demo breaks:** don't debug in front of them. One beat, then:
> *"I'll show you the recorded run rather than spend your time on this."*
Switch to the screenshots and keep the same energy. **Do not apologise more than once.** Judges forgive technical failure; they don't forgive flustered.

---

### BEAT 5 · 8:30–9:30 · Where we are, honestly

**Goal: turn your incompleteness into evidence of discipline.**

> *"To be straight about status: the generator and three stages are built and passing that gate. The graph is being built now. The origin estimator, the risk models, the alerting and the evidence packet are specified — with frozen data contracts between every stage, which is why we can build them in parallel and why nothing downstream is blocked on a design decision.*
>
> *We'd rather show you three stages that genuinely pass a strict gate than eight that mostly run."*

**Then immediately turn it into a strength:**

> *"And the part that's built is the part that had to come first. Without the generator there's no answer key, without an answer key there's no measurement, and without measurement the estimator is just a model nobody can check. We built the measuring stick before the thing being measured. That ordering was deliberate."*

---

### BEAT 6 · 9:30–10:00 · The close

**Two sentences. Do not add a third. Do not trail off. Stop cleanly and invite questions.**

> *"Everyone in this room can build a dashboard over blockchain data. The hard part of this problem statement is the one sentence in the middle of the objective: correlate network-layer observations with blockchain-layer data. That correlation is wrong if you do it naively, it has a measurable ceiling, and nobody has published a benchmark for it — so we built the benchmark and then built the tool against it.*
>
> *We don't hand you a wallet address. We hand you an IP, a source port and an exact timestamp — the three values an ISP needs to identify one subscriber behind carrier-grade NAT, on a pre-filled notice under Section 94 of the BNSS. And we tell you when we don't know."*

---

## 4.4 The five things to say if you can only say five

If the room is chaotic, time is cut, or you freeze — these five, in any order:

1. **"The first IP is an echo, not the shout."** Bitcoin gossips with randomised delays.
2. **"Only 41.5% of transactions even contain the right answer. We say 'I don't know' on the rest."**
3. **"The problem statement required a synthetic dataset and supplied none. So we built a proper generator with an answer key."**
4. **"No public dataset has both layers with a ground-truth label. That's why this is unsolved in the open literature."**
5. **"We hand over an IP, a port and a timestamp on a servable legal notice — not a wallet address."**

---

## 4.5 Vocabulary discipline

**Use these** — they signal you've read the actual material: gossip / relay / originator · announcement set · common-input-ownership heuristic · change-address heuristic · peel chain · CoinJoin-like equal-output structure · structuring · dwell time · fan-out entropy · coinbase transaction · taint propagation · CGNAT · ASN · script type (P2PKH / P2SH / P2WPKH / P2TR) · chain of custody.

**Never use these** — every one of them makes you sound machine-generated: leverage · seamless · robust · cutting-edge · revolutionise · empower · holistic · game-changer · paradigm · unlock · harness the power of · next-generation · one-stop.

---

## 4.6 Who answers what

Decide this **before** you walk in. The worst look in a viva is two teammates starting to answer at once, then both stopping.

| Question type | Who takes it |
|---|---|
| Problem, gossip, why the naive join fails | the presenter |
| Data generation, realism, "isn't this cheating" | whoever knows MAYAJAAL best |
| The graph, clustering, the visual | whoever built DRISHTI |
| Code structure, testing, determinism | whoever runs the pipeline |
| Legal, impact, deployment | anyone — it's in Part 5, learn it |

**Three rules for the whole team:**

1. **One person answers. The others stay quiet** unless invited. Interjections read as disagreement even when they're additions.
2. **Answer in one or two sentences, then stop.** The single most common way a strong project loses a viva is a team member continuing to talk after the question has been answered.
3. **If you don't know: say so, then say what you'd do.** *"I don't know — I'd check X."* That reads as honest. Improvising reads as bluffing, and one caught bluff retroactively discredits everything true you said.

---

# PART 5 — THE Q&A ARSENAL

> **The most important part of this document. Read it twice.**
>
> **Who is asking:** at the internal round, the judges are generally **not** deep Bitcoin or ML specialists. That changes the threat model completely. They will not ask you to derive conformal prediction. They will ask **abstract, intuitive, and sometimes blunt** questions that come straight out of your own explanation — *"so is this real or not?"*, *"why should anyone care?"*, *"doesn't this already exist?"*
>
> **Those are harder to answer than technical questions, not easier.** A technical question has a technical answer. An abstract question has to be answered in the questioner's language, with confidence, in under thirty seconds, without jargon to hide behind.
>
> **Three rules for every answer below:**
> 1. **Answer the question first. Justify second.** Never open with background.
> 2. **Two sentences, then stop.** Expand only if asked.
> 3. **Never bluff.** *"I don't know, here's how I'd find out"* beats a confident invention every single time.

---

## 5.1 THE FOUR THAT DECIDE YOUR RESULT

Memorise these four. Not the wording — the *structure* of each answer.

---

### ⚠ Q1. "Both your layers don't exist in real life. You're working with a made-up situation, a made-up dataset, a made-up world. How is this even relevant?"

**This is the question. If you handle it well, you've won the room. If you fumble it, nothing else you said survives.**

**What NOT to say:** *"Well, the problem statement told us to."* That's technically true and it sounds like surrender. It concedes their framing — that you did something questionable and are hiding behind a rule. Never lead with it.

**The structure of the right answer: reject the premise, correct the facts, then explain what's actually synthetic and why it has to be.**

> *"I'd push back on the premise, because both layers are completely real.*
>
> *The blockchain layer is the most public dataset on earth — every Bitcoin transaction ever made is downloadable right now. The network layer is real too: any node on the Bitcoin network sees transaction announcements arriving from IP addresses. That's just how the protocol works. Researchers have been running listening nodes and doing exactly this analysis for over a decade — the 11-to-60-percent figure I mentioned is from an ACM paper in 2014.*
>
> *So neither layer is invented. **What's missing in the real world isn't the data. It's the answer key.***
>
> *To know for certain that a specific IP truly originated a specific transaction in the wild, you'd need a confession or a seized device — for every transaction in your dataset. Which means you'd have to already know the answer to the question you're trying to measure. It's circular. **That ground truth cannot exist for real data, ever.** That's exactly why published results range from 11% to 60% — there's no shared benchmark, so nobody can even score each other.*
>
> *So the real world has both layers and no answer key. We built a world where we control the answer key, so that for the first time the accuracy of this technique can actually be measured.*
>
> ***We didn't invent the problem. We invented the measuring stick.***
>
> *And the tool itself runs on real data unchanged — it never sees the answer key. It's architecturally forbidden to; we have a test that deletes the answer key and runs the whole pipeline to prove it. The synthetic part is only how we grade ourselves."*

**If they push again — "but your simulator could be wrong":**

> *"Completely fair, and we defend against it four ways. One, we evaluate on worlds generated with parameters the tool was never tuned on. Two, the generator can take the **real** Bitcoin transaction graph as its chain layer and synthesise only the network layer on top — that's specified, not yet built. Three, we never report a single accuracy number; we report a curve over how much of the network you're observing, so we can't cherry-pick. Four, the chain-layer models get validated against Elliptic, a real, independently labelled dataset we had nothing to do with.*
>
> *And the strongest evidence is the simplest: we wrote deliberately stupid cheating rules and checked whether our own data rewards them. 'Pick the lowest numeric IP' scores 0.4%. If we'd accidentally baked in an ordering artifact, that number would be high. **We built tests designed to catch ourselves, and we publish what they find.**"*

**The analogy, if they're still not convinced — good for non-technical judges:**

> *"It's the same reason crash-test dummies aren't real people and flight simulators aren't real flights. The question isn't 'is it real?' — it's 'does it preserve the mechanism you're testing?' Ours uses real UTXO accounting, Bitcoin Core's actual default topology, and Bitcoin Core's actual relay-delay defaults. The behaviour we measure emerges from those mechanisms. We didn't tune the numbers to look good — we built the mechanism and reported whatever came out, including the parts that were inconvenient."*

**Only now, at the very end, and lightly:**

> *"And for what it's worth, the problem statement does require a synthetic dataset and states that no real seized or live-intercept data will be provided. But I'd have argued for building it even if it hadn't."*

> **That last sentence is the whole trick.** It converts the rule from a hiding place into a confirmation — *we'd have done this anyway, and it happens the sponsor agrees.*

---

### ⚠ Q2. "Does this already exist? Who are your competitors?"

**Never say "no competitors."** It's false, everyone knows it's false, and it marks you as someone who didn't look. **Naming your competitors accurately and then explaining precisely where you sit is far more convincing than claiming empty space.**

> *"Yes, and I'll name them, because the gap is specific rather than general.*
>
> ***On the chain side:*** *Chainalysis, TRM Labs and Elliptic are excellent and genuinely dominant. Open-source there's BlockSci and GraphSense. All of them work purely on the blockchain — wallets, transactions, clusters.*
>
> ***On the network side:*** *this is academic rather than commercial. Koshy, and Biryukov and Pustogarov, ran listening nodes and published origin-inference results over a decade ago. Sites like bitnodes map network topology.*
>
> ***And that's the gap.*** *Chain analysis is a solved commercial problem. Network analysis is a solved academic problem. **Nobody has fused them into one deployable tool that produces court-ready evidence, because no dataset exists that has both layers with ground truth.** The commercial products don't do it because the IP layer isn't publicly available data they can buy. The academics don't do it because they build research code, not evidence pipelines.*
>
> *This problem statement hands us both layers. That's the whole opportunity."*

**Then the part that matters most to this sponsor:**

> *"There's also a reason NTRO can't simply buy Chainalysis. It's not a quality argument — their product is better than ours at what it does. It's that they're a US company running in their cloud, and an Indian intelligence agency cannot upload national-security investigation data to a foreign vendor's servers. Our entire system runs air-gapped on one workstation with the network adapter off. **That's not a feature we chose; it's the requirement that makes this a domestic build.**"*

**If asked "so what stops Chainalysis from just adding this?":**

> *"Nothing technical. But they'd need the network-layer capture, which means operating listening infrastructure, and they'd need to solve the benchmark problem we solved to prove it works. Mostly, though, it wouldn't fix the sovereignty problem — it'd still be their cloud. For NTRO's use case, the deployment model matters more than the algorithm."*

---

### ⚠ Q3. "There are hundreds of teams on this. How is your idea unique? How do you stand out?"

**Don't list features. Features sound like everyone else's features.** Lead with what most teams will get *wrong*, because that's a claim only you can make.

> *"I'll answer that by predicting what most teams will build, and I think I'll be close.*
>
> *Most will build a dashboard over the blockchain fields — wallet clustering, a risk score, a nice graph. Good-looking, and it ignores half the problem statement. **The objective explicitly says to correlate network-layer observations with blockchain-layer data.** The word 'traffic' is in the title, and it's a networking word, not a blockchain word.*
>
> *Of the teams that do use the IP fields, **almost all of them will join on `src_ip` and treat the first IP as the sender.** That's not a small inaccuracy — it's structurally wrong, because Bitcoin gossips with randomised per-peer delays. In a real case it points at an innocent person's connection. We can demonstrate that it's wrong in about twenty seconds, with numbers.*
>
> *So we stand out on four things:*
>
> ***One — we built the dataset that didn't exist.*** *Not a row generator. A real UTXO ledger, a real P2P topology with Bitcoin Core's actual relay timings, and criminal agents that improvise rather than stamping templates into the data.*
>
> ***Two — we know the ceiling.*** *Only 41.5% of transactions even contain the right answer. We're probably the only team who knows that number exists, and it's the number that tells you whether anyone else's claimed accuracy is honest.*
>
> ***Three — we abstain.*** *Our system refuses to answer on the majority of cases, with statistical guarantees about when. Everyone else will output a name every time, and be wrong most of the time without knowing it.*
>
> ***Four — the output is a legal document, not a wallet address.*** *An IP, a source port, and an exact UTC timestamp on a pre-filled BNSS Section 94 notice — the three values an ISP actually needs behind carrier-grade NAT."*

**The compressed version, if you only get one sentence:**

> *"Most teams will answer the blockchain half of the question. Of the ones who attempt the network half, most will get it structurally wrong in a way that names innocent people. We built the measuring stick that proves which of those is happening."*

---

### ⚠ Q4. "What exactly is MAYAJAAL? How did you build it? Is this legit? How does it actually work?"

> **Expect the heaviest questioning here.** It's the most unusual thing you've built, and unusual things attract suspicion. The instinct under pressure is to get defensive. **Do the opposite — get enthusiastic.** It's genuinely the most interesting part of the project. Treat the questions as interest, not attack, and the room follows your framing.

**The one-liner:**

> *"MAYAJAAL is a Bitcoin world simulator. It builds a complete little Bitcoin economy — people, wallets, real transactions, a real peer-to-peer network with real gossip timing, and criminals actively trying to launder money — and it records the truth about every single thing that happened. Then it throws almost all of that away and gives the tool only what a realistic eavesdropper would actually have seen."*

**"How did you build it?" — walk the six layers, one line each:**

> *"Six layers. **First**, a population: ten entity types in realistic proportions — individuals, merchants, exchanges, mules, mixers, darknet markets, ransomware operators — each with its own spending behaviour.*
>
> ***Second**, a genuine UTXO ledger. Not fake rows — actual Bitcoin accounting in integer satoshis, with change addresses, multi-input transactions and heavy-tailed values. Value is conserved exactly; no floating point anywhere.*
>
> ***Third**, the network: about four thousand nodes, eight outbound connections each, which is Bitcoin Core's default. And the critical piece — each node waits a **random** interval before forwarding, drawn independently per peer per transaction, with Bitcoin Core's actual default means of two seconds outbound and five inbound.*
>
> ***Fourth**, the adversary — and this is the part I'd point at. **Fifth**, export: two separate trees, one being what an observer saw, one being the answer key. **Sixth**, forty-four automated validation checks."*

**"Is it legit?" — four pieces of evidence, and lead with the counterintuitive one:**

> *"Here's the test I'd apply if I were you. **We wrote deliberately stupid cheating rules and checked whether our own data rewards them.***
>
> *'Pick the lowest numeric IP' — 0.4%. 'Pick the first IP you saw' — 22.1%. Against a ceiling of 41.5%.*
>
> ***Think about what that means.*** *If we'd secretly rigged the simulation to make ourselves look good, the naive rules would score high, because we'd have left the answer sitting near the surface. They don't. **Our own data is hard for us.** We built the tests specifically to catch ourselves cheating, and we publish what they find.*
>
> *Second: realism is in the **mechanism**, not the statistics. We didn't tune numbers until they matched a paper. We implemented real UTXO accounting, real topology and real relay timing, and reported whatever emerged.*
>
> *Third, the thing that convinced me most: **turning one knob — how much of the network we're listening to — reproduces the entire 11-to-60-percent range found in the published literature.** We never targeted that. It fell out. Different real-world studies had different observer coverage, and our parameter reproduces their spread. That's strong evidence we captured the actual mechanism.*
>
> *Fourth, forty-four automated checks, including ones we failed and fixed. One of them was a statistical test that was passing while testing the wrong property — we caught it and replaced it. Finding that mattered more than any test that was already green."*

**"Doesn't making your own data mean you can make it as easy as you want?"** — the sharpest version of this question:

> *"It does, and that's exactly why we don't get to be the judge of that — which is why the leakage tests exist, and why they're adversarial by design. If I wanted an easy dataset, 'first IP wins' would score 80%. It scores 22%. Our specification has an acceptance band of roughly 0.15 to 0.6 for that heuristic, written down before we measured: below it, the data's unrealistically hard; above it, something has leaked. We landed at 0.221 and published it rather than tuning until it flattered us.*
>
> *And the structural answer: **we evaluate on worlds generated with parameters the tool was never tuned on.** If we'd secretly fitted to our own simulator, performance would collapse there."*

**"What's the cleverest thing in it?"** — if you get this opening, take it:

> *"The adversary design. The lazy way to generate criminal data is to decide what a peel chain looks like and stamp five hundred of them into the dataset. **But then your detector is just finding your own stamp.** You'd report 99% accuracy and you'd have measured nothing.*
>
> *So our criminals are **agents**, not patterns. Each one has a goal, a budget, and a menu of moves — peel, split, merge, mix, hop, structure, dwell, cash out. At each step it picks based on its situation. **The laundering patterns aren't inserted. They emerge.** Two agents with the same goal produce different-looking trails.*
>
> *And here's the tell that it's working: we went looking for a bug — we thought campaigns were being cut short by running out of money. They weren't. Zero failures across fifty-six decisions. Campaign lengths turned out to be geometrically distributed with a heavy tail of short ones, which is what real laundering looks like — **and nobody designed that. It fell out of the mechanism.**"*

---

## 5.2 QUESTIONS FROM NON-TECHNICAL JUDGES

These come straight out of your own explanation. Answer in their language, with zero jargon.

**"Explain what your project does to someone who knows nothing about Bitcoin."**
> *"When someone sends Bitcoin, the public record shows the money moving but never who moved it — there are no names anywhere in Bitcoin. But Bitcoin runs over the internet, so computers with real IP addresses are passing these transactions around. Our tool watches that and works out which computer most likely sent it, with an honest confidence level — and it tells you when it can't tell. The IP is the only bridge from anonymous money to an actual person an ISP can identify."*

**"So can you catch criminals with this?"**
> *"We can't identify anyone ourselves, and no honest system can. What we produce is the input that makes lawful identification possible: an IP address, a source port and an exact timestamp, on a notice an investigating officer serves on an internet provider. **The provider does the identification, lawfully, and we designed it to stop exactly there on purpose.** Our job is to turn a wallet string into something with a legal next step."*

**"Why is this hard? Can't you just look at where it came from?"**
> *"That's exactly the intuition the whole problem hinges on, and it's wrong for a specific reason. Bitcoin doesn't send transactions directly — it passes them around like a rumour. Everyone who hears it repeats it. And the software deliberately waits a random amount of time before repeating, specifically so you can't tell who started it. So the first person you hear it from is almost never the person who started it. **It's an echo, not the shout.** We measured it: guessing 'first one I heard' is right about one time in five."*

**"How accurate is it?"** — *reframe, don't answer with a number*
> *"The honest answer is that 'accuracy' is the wrong frame here, and I can show you why. In only 41.5% of transactions is the true sender even present in the data at all — the rest were never observed. So the maximum possible score is 41.5%, not 100%. The naive approach gets 22%. Our job is to close that gap and to say 'I don't know' on the rest. **Anyone who tells you 90% on this problem is measuring something else.**"*

**"What if you're wrong and someone innocent gets accused?"** — *answer with visible seriousness; this is the right question to ask*
> *"That's the failure we designed against first, and there are four layers of defence. We output a probability, never a name. We show the second and third candidates. Every alert is generated together with **the strongest case against itself** — so if a pattern also fits a legitimate merchant settling daily receipts, that appears on the same screen, not in a footnote. And the system abstains outright when the evidence can't support an answer, which on our data is the majority of the time.*
>
> *There are also zero automated actions. A human decides everything. **The whole design assumes we will sometimes be wrong, and tries to make that survivable.**"*

**"Why the Sanskrit names?"**
> *"Three reasons. They're accurate — each one describes what the component actually does. Pramaan is the Nyaya philosophical term for the valid means by which something becomes knowledge, which is literally what an evidence packet is. Shastra is a deliberate pun: शस्त्र is a weapon, शास्त्र is a rigorous treatise, and that layer is the one that names suspects, so it's held to the strictest method.*
>
> *Second, Chakravyuha is a formation of concentric layers, and so is our system.*
>
> *Third — it's built in India, for an Indian agency, under Indian law. A tool that pre-fills a BNSS notice should probably sound like it came from here."*

**"Why is it called CHAKRAVYUH specifically?"**
> *"The Chakravyuha was the spiral formation Abhimanyu could enter but not escape — he knew how to get in, not how to get out, and he died inside it. That's a Bitcoin investigation: you can follow the money in, and you can't find your way out to a name.*
>
> *But the sharper half is that **Abhimanyu died of a partial answer he mistook for a complete one.** That's exactly the 'first IP is the sender' mistake — an answer that feels complete, gets you deep in, and then collapses. Our most important feature is knowing which parts of the maze we haven't solved."*

**"Is this legal? Isn't it surveillance?"**
> *"Everything we analyse is publicly broadcast. Bitcoin transactions are announced to anyone who connects to the network — running a node and recording what it's told is ordinary participation in a public protocol, not interception. There's no wiretap and no private communication involved.*
>
> *And our output is an input to a **legal** process, not a substitute for one. We stop at a production notice under Section 94 of the BNSS. The identification is done by an authorised agency with a lawful instrument. **We drew that boundary into the architecture deliberately** — the last two steps of our own diagram are labelled as someone else's job."*

**"What's the hardest part?"**
> *"Separating the originator from the relays. It's the one part of this problem with no public ground truth, which is precisely why we had to build a simulator that produces it."*

**"How long did this take? Did you use AI to build it?"** — *answer plainly; defensiveness here is what looks bad*
> *"We used AI tooling for implementation, the way you'd use any modern tooling. What it can't do is the part that matters: decide that the answer key needs to be physically quarantined, notice that a statistical test is passing while testing the wrong property, or catch that 'any decimal means BTC' would silently multiply an entire column by a hundred million while still passing conservation checks. **Those were our calls, and they're the reason the numbers are trustworthy.** Happy to walk through any of them."*

---

## 5.3 TECHNICAL QUESTIONS

**"Where is the AI? This sounds like rules."** — *the problem statement warns about this explicitly: "not just rules"*
> *"The heuristics are **features**, not the answer. They feed a LightGBM baseline and a graph model, and the confidence number comes from class-conditional conformal calibration rather than a softmax relabelled as confidence. We've also stated the condition for shipping the simpler model: if the graph network can't beat the baseline on a **future** time window, it doesn't go in."*

**"Why not just use a neural network / an LLM on all of it?"**
> *"Because the output has to survive cross-examination. A defence lawyer will ask why this wallet was flagged, and 'the network decided' ends the case. Every score we produce carries per-feature attribution and a counter-argument. We do run a local quantised model for narrative generation — locally, offline — but it never makes a determination. **It writes up a conclusion; it doesn't reach one.**"*

**"How do you know your model isn't just memorising?"**
> *"Strict time ordering — we never train on data from after the evaluation window. That's the classic fatal mistake in financial-crime ML: random train/test splits let the model learn from March to predict February, which looks brilliant and collapses in deployment. We enforce one shared train/evaluate boundary across every stage, with a test asserting all consumers agree on it. That was a real architectural fix — two stages were originally free to define their own, which would have leaked future information with nothing catching it."*

**"What's your accuracy / F1 / precision?"**
> *"For origin inference, the estimator isn't built yet — what we've measured is the baseline it must beat, 22.1%, and the ceiling it can't exceed, 41.5%. For risk classification: we don't report accuracy at all, and that's deliberate. At our 1:345 class imbalance, a model that says 'not suspicious' to everything scores 99.7% accurate and is worthless. We report calibration and per-class coverage. Plain conformal at that imbalance covers the rare class at 53% while claiming 90% overall; class-conditional holds it at 90.6%."*

**"Can it handle a million rows? What about the real blockchain?"**
> *"A million rows is our design target and the generator produces it — that's roughly 66,000 transactions at our observation rate. We use Polars and Parquet with columnar processing and stage-by-stage streaming, so memory doesn't scale with total size. The full blockchain is a different scale problem — that's the published 252-million-node graph, and it's why real-slice mode is designed to take chain topology from that dataset rather than trying to simulate at that scale."*

**"What happens with Tor or a VPN?"**
> *"The correct answer there is to refuse, and the system does. A Tor exit node's IP is not the sender and never will be, so producing a name would be actively harmful. We detect those cases and abstain, and we report degradation against Tor and VPN traffic **separately** rather than averaging it into a headline number that hides it."*

**"How do you know two addresses belong to the same person?"**
> *"We don't know — we estimate, and the distinction is the whole point. If two addresses are spent as inputs to the same transaction, whoever signed it controlled both keys. That's strong but not certain, because CoinJoin deliberately combines inputs from strangers to poison exactly that inference. So every cluster carries a confidence number and we never hard-merge. Published measurement puts this heuristic around 0.36 precision in law-enforcement use. **If ours came back at 0.9 we'd treat it as a bug.**"*

**"What if the real data has different column names?"**
> *"Then we add rows to a table. KAVACH is the single door into the system and it holds an alias table mapping incoming names to ours — `source_ip` to `src_ip`, `hash` to `txid`, and so on. No code changes. **Everything downstream already speaks our vocabulary and doesn't know or care where the data came from.** We assumed from the start that a real schema wouldn't match ours exactly."*

**"How do I know your results are reproducible?"**
> *"Same seed in, byte-identical output — and we test that rather than asserting it. Every stage runs twice, in two separate operating-system processes, and the outputs are compared byte for byte. Two runs inside one process can't catch hash-seed nondeterminism, because one process has one hash seed. Every output also records the git commit of the code that produced it, and marks it 'dirty' if there were uncommitted changes."*

**"Why Polars instead of pandas? Why these libraries?"**
> *"Polars for columnar performance and because its lazy evaluation makes the memory profile predictable at a million rows. Parquet between stages so every intermediate state is inspectable on disk. rustworkx for graph algorithms. LightGBM because gradient boosting is still the strongest baseline on tabular features and it's far more explainable than a deep model. MAPIE for conformal prediction. Everything pinned, everything offline-installable, nothing requiring a network call at runtime."*

---

## 5.4 THE HOSTILE ONES

**"This is just a school project. Nobody will ever use it."**
> *"Possibly — but the reason to build it isn't the code, it's the capability. Right now an Indian investigator has no network-layer attribution tooling at all. Whether they eventually use our code or someone rebuilds it properly, the benchmark we made is the part that outlives the hackathon, because nobody could measure this before. And it was specified by NTRO, who presumably know whether they need it."*

**"You didn't build most of what you're describing."**
> *"Correct, and I said so before you asked. The generator and three stages are built and passing a seven-point gate that includes byte-level determinism. The graph is being built now. The rest are specified with frozen data contracts. **What's built is the foundation the rest depends on** — without the answer key there's no measurement, and without measurement the estimator is a model nobody can check. We built the measuring stick first. That ordering was deliberate."*

**"Your numbers are low. 22%, 41%, 0.36. That's not impressive."**
> *"They're low because they're real, and I'd be far more worried if they were high. 41.5% is a **ceiling**, not a score — it's the fraction of cases where an answer exists at all. Against that, 22% isn't a failure, it's the naive baseline we have to beat. And 0.36 is published measurement from actual law-enforcement use.*
>
> *The teams reporting 95% on this problem have either leaked ground truth into their features or are measuring something easier than what they claim. **We can prove our numbers are honest because we wrote the tests designed to catch ourselves.** That's a harder thing to demonstrate than a big number, and it's the thing that matters if this is ever used in a case."*

**"What if I told you the whole premise is flawed, because serious criminals use Tor and you'll never see them?"**
> *"You'd be partly right, and it's the correct objection. Against a competent operator using Tor properly, we abstain — and we say so rather than hiding it in an average.*
>
> *But two things. Most crypto crime isn't run by careful professionals; it's volume fraud, and operational security fails constantly — one transaction sent before the VPN reconnected is enough. And in a layering chain of forty hops, you don't need all forty. **You need one.** A tool that abstains on thirty-nine and gives you a calibrated lead on the fortieth has done its job."*

**"Isn't this all a bit much for a hackathon? Why not build something simpler that works?"**
> *"Because the simple version is the wrong answer. The simple version joins on `src_ip`, which points at a relay, which in a real case is an innocent person's internet connection. **You can build the simple version in a day and it's actively harmful.** The three stages we finished are simple; what's not simple is proving they're correct, and that's where the time went."*

**"Your teammate built the frontend separately. How do you know it'll integrate?"**
> *"Because the interface was frozen before either side started. He builds against a sample JSON file at a fixed path in a fixed shape; the graph stage later writes the real one to the same path in the same shape. The integration is one wire. **That's the payoff of stages talking only through files on disk instead of importing each other** — it's also why he can work solo without ever blocking on me."*

**"What's the weakest part of your project?"**
> *Answer this honestly. Deflecting it is the only wrong move.*
>
> *"Two things. First, the origin estimator — the scientific core — isn't built yet. We've built everything needed to evaluate it honestly, which I'd argue is the harder half, but it isn't built.*
>
> *Second, and more fundamentally: **we cannot prove our simulator matches reality, only that it implements the real mechanisms.** Real-slice mode, which takes the chain layer from real published Bitcoin data, is the main defence against that, and it's specified rather than built. If you're asking what keeps me up, it's that one."*

---

## 5.5 QUESTIONS ABOUT THE FUTURE

**"What's next if you win?"**
> *"In order: finish the origin estimator, because it's the scientific core. Then real-slice mode, so the chain layer comes from real published Bitcoin data rather than ours. Then the evidence packet, which is mostly assembly of things that already exist. And then the thing I'd most want — **release the benchmark publicly**, so other people can be measured against it. Right now nobody can compare results on this problem at all."*

**"Could this work on other cryptocurrencies?"** — *have a teammate ask you this if nobody does*
> *"Yes, and it's the more interesting version of the project. **The estimator doesn't know it's looking at Bitcoin.** It needs a content identifier, a set of observers, and announcement times. That's true of any gossip-based peer-to-peer network — other chains, and overlay networks generally. Bitcoin is just the instance this problem statement gives us the data for."*

**"How would this actually get deployed?"**
> *"One commodity Linux workstation, air-gapped, inside the agency. A capture goes in on physical media, leads come out. No cloud, no licence, no case data leaving the building. The GeoIP database and model weights ship inside the image. **We run it with the network adapter switched off, and we test that it still works that way.**"*

---

## 5.6 THE THINGS THAT LOSE MARKS

Failures of manner, not knowledge. Each one is avoidable.

| Don't | Do |
|---|---|
| Say "no competitors" | Name them accurately, then say where you sit |
| Claim high accuracy | Give the ceiling, then your position against it |
| Get defensive about synthetic data | Get **enthusiastic** about it — it's your best work |
| Keep talking after answering | Two sentences, then **stop** |
| Two people answering at once | One voice per question, agreed in advance |
| Bluff a number you're unsure of | *"I don't want to quote a number I can't source"* |
| Apologise repeatedly for unbuilt parts | State status once, factually, then move on |
| Use "leverage", "robust", "cutting-edge" | Use the domain vocabulary in 4.5 |
| Show a full wallet address on screen | Truncated, always, and explain why if asked |
| Read your slides aloud | Slides support you; they aren't the script |

---

# APPENDIX A — THE NUMBERS

> **This is the page to have open on your phone outside the cabin.** Every number here is either measured by us or has a source printed next to it. **Never quote a number you can't attribute.**

### The five that matter most

```
   41.5%     THE CEILING. How often the true originator is even present
             in the capture at all. Nothing can score higher than this.
             ── measured, at observer_fraction 0.10

   22.1%     First-seen baseline. How often "the first IP wins" is right.
             ── measured

   354,023   Rows in our reference capture
      ↓
    24,626   Actual transactions in it (≈14.4 announcements each)
             ── measured. 93% of rows are echo.

   0.36      Published precision of the multi-input clustering heuristic
             on full clusters in law-enforcement use.
             ── published. NOT our own measurement yet.

   11%–60%   Published range for originating-IP inference from P2P
             observation, depending on observer coverage.
             ── Biryukov & Pustogarov, ACM CCS 2014
```

### Leakage / baseline table

| Rule | Score | Reading |
|---|---|---|
| First IP seen | 22.1% | in the 0.15–0.6 acceptance band ✓ |
| Most frequent announcer | 21.8% | in band ✓ |
| Lowest numeric IP | 0.4% | no ordering artifact ✓ |
| Random guess | 2.9% | baseline ✓ |
| **Ceiling** | **41.5%** | the physical limit |

### Bitcoin protocol facts

```
   8            default outbound connections (Bitcoin Core)
   9            originator + 8 peers = the first announcement wave
   125          default max total connections
   ~2 s         mean Poisson relay delay, outbound  (Core default)
   ~5 s         mean Poisson relay delay, inbound   (Core default)
   546 sats     standard dust threshold (P2PKH)
   BIP 156      Dandelion — PROPOSED, never implemented in Bitcoin Core
```

> **Know the Dandelion point.** If someone says "doesn't Dandelion prevent this?", the answer is: *"Dandelion was BIP 156 and it was never merged into Bitcoin Core. The real mechanism in the live network is the randomised per-peer Poisson relay delay, which is what we implement."*

### Our system

```
   ~4,000       nodes in the simulated network
   16           observer nodes (n_observers)
   0.10         default observer_fraction
                sweep: 0.02 · 0.05 · 0.10 · 0.25 · 0.50
   1,000,000    target rows (≈66,000 transactions at our rate)
   42           default seed
   44           validation checks in MAYAJAAL
   1:345        class imbalance
   53% → 90.6%  rare-class coverage: plain conformal → class-conditional
```

### Entity mix

```
   individual     55%        exchange        4%
   merchant       12%        scam            3%
   mule           12%        mixer           2%
   service         8%        darknet_market  2%
                             mining_pool     1%
                             ransomware      1%
```

### Impact figures (each with its source — always say the source)

```
   $154 bn      illicit crypto addresses received, 2025, +162% YoY
                ── Chainalysis 2026 Crypto Crime Report

   ₹19,813 cr   lost in India, 2025, across 21.8 lakh cheating-fraud
                complaints on the National Cyber Crime Reporting Portal
                ── I4C / MHA

   ~77%         of that loss from investment-scheme fraud
                ── I4C via MHA

   ₹8,690 cr    blocked/recovered via CFCFRMS up to January 2026
                ── I4C / MHA
```

### Legal

```
   BNSS 2023 §94       production notice to compel records from an ISP
                       (Bharatiya Nagarik Suraksha Sanhita)
   BSA 2023 §63(4)     electronic evidence; the certificate requires the
                       HASH VALUE of the record to be disclosed
                       (Bharatiya Sakshya Adhiniyam)
   Both in force from 1 July 2024.

   The tuple an ISP needs behind CGNAT:
       { public IP  +  source port  +  exact UTC timestamp }
   IP alone identifies thousands of subscribers. Useless in court.
```

### Truncation policy

```
   IPv4      first two octets          203.0.xx.xx
   IPv6      first two hextets         2001:0db8:…
   address   first 6 + last 4          bc1q4f…9f4d
   txid      first 8 + last 4          4a7f2c91…8b3e
   SHA-256   FULL — required by BSA §63(4)
```

### Reference datasets

```
   Elliptic          ~203k nodes, ~234k edges, 166 features.
                     REAL, independently labelled. Our cross-check.
   Bitcoin tx graph  252M nodes, 785M edges, ~13 years, ~670M txs,
                     ~34k labelled nodes. (Nature Sci Data, arXiv 2411.10325)
                     Source for real-slice mode. ORBITAAL is an alternative.
   AMLSim/AMLworld   IBM synthetic AML datasets. NeurIPS 2023.
                     The methodological precedent for synthetic benchmarking.
   Tide (2026)       open-source generator, same reasoning.
```

---

# APPENDIX B — GLOSSARY

**Announcement (INV)** — the small message a node sends saying "I have transaction X." What our capture is made of.

**ASN** — Autonomous System Number. Identifies which network operator owns an IP range.

**BIP** — Bitcoin Improvement Proposal. BIP 34 (block height in coinbase), BIP 156 (Dandelion, never merged).

**CGNAT** — Carrier-Grade NAT. Thousands of subscribers sharing one public IP. Why source port and timestamp are essential.

**Change address** — the output that returns leftover value to the sender. A key clustering signal.

**CoinJoin** — a transaction deliberately combining inputs from unrelated people, specifically to break the common-input heuristic.

**Common-input-ownership** — the heuristic that all inputs to one transaction share an owner. Strong, not certain.

**Conformal prediction** — produces a *set* of answers with a mathematical coverage guarantee, rather than a single answer with a made-up confidence.

**Dust** — an output too small to be economically spendable. 546 satoshis is the standard P2PKH threshold.

**Gossip** — the flooding protocol by which Bitcoin propagates transactions. Every node re-announces. The reason first-seen ≠ sender.

**Ground truth** — the answer key. Physically quarantined in our system; readable only by `eval/`.

**Heavy-tailed** — a distribution where most values are small but rare huge ones dominate the total. Real Bitcoin values are heavy-tailed.

**Merkle root** — a single hash summarising a whole set of hashes. Printed in full; a truncated hash proves nothing.

**Mondrian / class-conditional conformal** — conformal prediction where the coverage guarantee holds *per class*, essential under heavy imbalance.

**Observer fraction** — what share of the network we're listening to. The single most important knob in the project.

**Origin vs relay** — the central distinction. The originator sent it; a relay merely forwarded it. Most announcers are relays.

**Parquet** — columnar file format used between every stage.

**Peel chain** — laundering by repeatedly shaving small amounts off a large sum across many hops.

**Poisson relay delay** — the randomised wait before forwarding, drawn independently per peer per transaction. Bitcoin's actual privacy defence.

**SHAP** — per-feature attribution explaining why a specific prediction came out as it did.

**Satoshi** — the smallest Bitcoin unit. 100,000,000 sats = 1 BTC. All our accounting is in integer satoshis.

**Structuring** — deliberately keeping amounts below a reporting threshold.

**Taint propagation** — spreading a risk score through the transaction graph from known-illicit seeds (poison / haircut / FIFO variants).

**UTXO** — Unspent Transaction Output. The "sealed envelope" model. Bitcoin has no account balances.

---

# APPENDIX C — THE ONE-PAGE CRIB

*Everything that matters, on one screen.*

```
 ═══════════════════════════════════════════════════════════════════════
  WHAT              Fuse the blockchain layer and the network layer into
                    one graph, estimate who ORIGINATED each transaction,
                    abstain when you can't know, output a legal document.

  WHY HARD          Bitcoin gossips with RANDOM per-peer delays.
                    The first IP you see is an echo, not the shout.

  THE KILLER NUMBER Only 41.5% of transactions even CONTAIN the answer.
                    Naive first-seen gets 22.1%. Ceiling, not target.

  WHY OUR OWN DATA  The PS requires synthetic data and supplies none
                    ("Dataset Link: Nil"). And no real dataset can ever
                    have this answer key — you'd need a confession per
                    transaction. We built the measuring stick.

  THE LAYERS        MAYAJAAL  illusion-net   the world + the answer key
                    KAVACH    armour         hash before parse, seal
                    SETU      bridge         split grains, src_ip→peer_ip
                    JAAL      net            ★ THE FUSED GRAPH
                    SHASTRA   weapon/treatise origin estimate + abstain
                    BUDDHI    discrimination  risk models, calibrated
                    VAANI     speech          alerts + counter-evidence
                    PRAMAAN   valid knowledge signed, replayable packet
                    DRISHTI   vision          offline console

  BUILT             MAYAJAAL · KAVACH · SETU ✅   JAAL 🔨   rest 📋 specified

  UNIQUE            1. built the dataset that didn't exist
                    2. know the ceiling (nobody else does)
                    3. abstain, with statistical guarantees
                    4. output is a servable BNSS §94 notice, not a wallet

  COMPETITORS       Chainalysis/TRM/Elliptic = chain only.
                    Academia = network only. Nobody fuses them.
                    And NTRO can't put case data in a foreign cloud.

  THE CLOSE         "We don't hand you a wallet address. We hand you an
                    IP, a source port and an exact timestamp — the three
                    values an ISP needs behind CGNAT. And we tell you
                    when we don't know."
 ═══════════════════════════════════════════════════════════════════════
```

---

*CHAKRAVYUH · SIH26146 · offline two-layer attribution workstation for Bitcoin traffic*
