# CHAKRAVYUH / DRISHTI: SIH26146 Idea-PPT Review

Review of `Copy of SIH26146 Lazarus.pdf` (6 slides), done against the remodeled backend
(agency-v2 numbers in `world.json`), the current brand, and what SIH idea-round evaluators
actually score. Written to be blunt, because you asked for it. Any text below that is meant to
go **onto a slide** is written to your rules: no em-dashes, no weak-sounding phrasing, precise
terms.

---

## 0. Bottom line up front

The deck is already above the SIH average. It follows the five-heading format, it has a real
architecture diagram, a real risk table, real references, and actual UI screenshots. That last
part alone puts you ahead of most teams, who submit a wireframe they drew the night before.

But the PPT was built before the remodel, and it shows. There are three things that will cost
you if a sharp judge reads carefully, and three big things you actually built that the deck
never brags about.

**Three must-fix (they are internal contradictions a judge can catch):**

1. **Slide 2 says the origin is `IP 4 ORIGIN p = 0.87`. The slide-3 wireframe shows origin
   `likelihood 0.010`.** These are on the same deck and they contradict each other hard. Worse,
   `p = 0.87` for a single host contradicts your own slide-2 bullet that says you "keep the exact
   host sealed" and resolve to operator. Pick one story. The correct one is the remodel story:
   you rank a shortlist and resolve to the network operator, you do not crown a single host at
   0.87.
2. **"20 ranked leads" (slide 2) vs "200 ranked leads" (slide-3 wireframe) vs the real funnel
   (66,689 ranked leads, 9 court-ready proofs).** Three different numbers for the same thing.
   Lock one funnel across the whole deck.
3. **"8-Layer Gated Plan" (slide 4) but the slide-3 pipeline shows 9 boxes / Phase 0 to Phase 8
   (9 phases).** Decide whether DRISHTI is a pipeline layer or the interface that sits across all
   of them, and make both slides agree.

**Three big things you built and did not show (the missed flexes):**

1. **Your actual numbers.** Operator-level top-1 = **45.9%**, which is **2.46x** the naive
   first-seen baseline (18.7%). Campaign recall **95.4%**. Illicit-activity model on the public
   Elliptic set: **F1 76.6%, ROC-AUC 93.7%**. None of these appear anywhere. The one number you
   do show (p = 0.87) is the one that is wrong.
2. **You validated on real public data (Elliptic), not just your own synthetic world.** That is
   the single strongest answer to the obvious judge question "did you just grade your own
   homework?" It is not on the deck.
3. **You built a GNN, measured it, and it did not beat the simpler gradient-boosted model, so you
   shipped the simpler one.** That is a maturity signal NTRO-type evaluators love. Right now the
   deck shows PyTorch Geometric in the stack as if the GNN shipped, which is the opposite message.

Everything below is the detail.

---

## 1. How the SIH idea round is actually scored (so you optimize for the right thing)

The idea submission is judged by the **sponsoring organization** (here, the NTRO-side panel), not
by generic hackathon mentors. Scoring is done per criterion (SIH has historically used a 1-20 per
criterion scale, weighted to a total of 100), and the criteria map almost exactly to your five
content slides:

- **Proposed Solution**: is it novel, does it actually solve *this* problem statement, is the
  core idea clear in one read.
- **Technical Approach**: is the method real and specific, is the stack credible, does the team
  clearly understand the domain (this is where they decide "did they actually get it").
- **Feasibility & Viability**: can it be built in the time/kit available, have they thought about
  what breaks, is there a plan.
- **Impact & Benefits**: quantified impact (saves X, catches Y, helps Z), relevance to a real
  government need.
- **Research & References**: have they read the literature, are the sources real and credible.

What the guides and past winners consistently say matters:

- **First impression and clarity.** A clean, finished title slide. A judge scanning 40 decks
  penalizes anything that looks unfinished. (Your title slide literally still says "TITLE PAGE"
  as a heading. Fix that first, it reads as a template you forgot to edit.)
- **Quantified impact.** "Reduces triage from N cases to M" beats "makes triage faster."
- **Relevance to the exact problem statement.** They picked PS 26146 (Bitcoin transaction
  traffic). Every slide should visibly serve that, not general blockchain forensics.
- **Do not overcrowd; let one idea own each slide.** Consistent formatting across slides.
- **Show it is real.** Prototype screenshots and a working demo video move you from "idea" to
  "these people can execute." You already have both coming. Good.

Common elimination reasons: solving a generic problem instead of the stated one, no evidence of
feasibility, inconsistent or unsupported numbers, and looking unfinished. You are exposed on
"inconsistent numbers" right now (see section 0), so that is the highest-value fix.

---

## 2. Cross-slide contradictions (fix these before anything cosmetic)

These are the ones that hurt, because they show up when a judge reads the deck as a whole.

**2.1 The origin confidence, `p = 0.87` vs `likelihood 0.010`, and the sealed-host story.**
Slide 2's central diagram crowns `IP 4` as `ORIGIN` with `p = 0.87` in red while the other eight
are `RELAY`. That single visual does three wrong things at once:

- It contradicts the slide-3 wireframe, where the origin candidate shows `likelihood 0.010`.
- It contradicts your own slide-2 innovation bullet, which correctly says you "resolve the
  shortlist to operator (ASN + region) and keep the exact host sealed." You cannot both keep the
  host sealed and print a red 0.87 host on the hero diagram.
- 0.87 for a single host is an overclaim. Your real, defensible story is a *ranked shortlist* that
  resolves to the *operator*, and per-case host certainty is deliberately low and honest.

Fix: redraw the diagram so it shows what you actually do. Keep the "same TXID, nine announcing
peers" setup (that part is great and it is the core insight). Then instead of one red ORIGIN at
0.87, show a **shortlist** (say 2 to 3 peers glowing) that **resolves upward to an operator**
(ASN + region) with the exact host drawn as sealed/redacted (`103.x.x.x`). Caption it with the
run-level number that is true and strong: operator-level top-1 = 45.9%. See the ready-to-use
caption in section 5.

**2.2 Lead count: 20 vs 200 vs 66,689.** Slide 2 says "10^5 capture rows to 20 ranked leads."
The slide-3 "Leads" wireframe says "200 ranked leads." The real funnel is 906,560 signals to
32,787 transactions to 66,689 ranked leads to 9 court-ready proofs. Three numbers, one concept.
Lock the funnel (section 6) and use it identically everywhere. Also "10^5" is understated: your
run is ~906,560 signals, which is closer to 9 x 10^5.

**2.3 Eight layers or nine.** Slide 4 says "8-Layer Gated Plan." Slide 3 shows nine chevrons
(MAYAJAAL, KAVACH, SETU, JAAL, SHASTRA, BUDDHI, VAANI, DRISHTI, PRAMAAN) and Phase 0 through
Phase 8 (nine phases). The clean story: there are **8 backend layers** (MAYAJAAL to PRAMAAN) and
**DRISHTI is the interface that sits across all of them**, not a ninth pipeline stage. Pull
DRISHTI out of the chevron chain and show it as the lens over the pipeline, then slide 4's "8" is
correct.

**2.4 "DRISHTI = Console."** Slide 3 labels the DRISHTI chevron "Console." Your own naming rules
kill the word "Console." DRISHTI means sight/vision; it is the thing that lets an officer see
through the maze. Label it "the interface" or "how the analyst sees it," never "Console."

**2.5 "LightGBM (baseline)."** Slide 3's BUDDHI box calls LightGBM the "baseline." It is not the
baseline, it is the **model you shipped** (gbm_v2). Calling it "baseline" implies something better
came along, when in fact the fancier thing (the GNN) was measured and rejected. Relabel to
"gradient-boosted risk model" or "risk model (LightGBM)."

---

## 3. Slide-by-slide: what is good, what to change

### Slide 1: Title
**Good:** correct PS ID, correct official PS title, theme, category, team name. Clean layout.

**Change:**
- "TITLE PAGE" is still printed as a heading. Remove it. This is the single most "unfinished"
  thing on the deck and it is the first thing a judge sees.
- **Team ID is blank.** Fill it.
- There is **no product name anywhere on the title slide.** You have a genuinely memorable name
  (CHAKRAVYUH, the maze you cannot trace your way out of) and a strong interface name (DRISHTI).
  Judges remember named projects. Add the name and a one-line hook under the PS title. Suggested,
  on-rules copy:

  > **CHAKRAVYUH**, tracing Bitcoin back through the maze it hides in.
  > Seen through **DRISHTI**, the analyst's view.

- The brain-and-bulb clipart is the SIH template asset. Leave it, not worth your time.

### Slide 2: Our Solution / CHAKRAVYUH
**Good:** the "same TXID, nine announcing peers, only one may be the originator" framing is the
clearest one-line statement of your core insight on the whole deck. The four-step flow (Input,
Two-Layer Fusion, AI/ML, Output) is clean. The innovation column is on-brand: "resolve to operator,
keep host sealed," "calibrated confidence," "open benchmark with ground truth," "counter-evidence."
The "how it addresses the problem" strip (bridges the structural gap, defensible leads, offline) is
solid and relevant.

**Change:**
- The `p = 0.87` ORIGIN diagram (see 2.1). This is the top fix on the deck.
- The "20 ranked leads" number (see 2.2).
- "AI/ML Analysis: address clustering, anomaly detection, peel-chain / mixing detection, taint
  propagation" is a little generic and does not match your layer names. Tighten it to what you
  actually do: clustering and peel-chain tracing (JAAL), the origin estimator stack (SHASTRA), and
  the calibrated risk model (BUDDHI). "Anomaly detection" and "taint propagation" are vague; either
  back them with a specific method or drop them.
- The innovation box is where you should add **one line about Elliptic validation** (see section 5).

### Slide 3: Technical Approach
**Good:** this is your strongest technical slide. The layered pipeline with Sanskrit names plus a
plain gloss each, the phase timeline, a real and credible stack, and four actual UI screenshots.
Having working screens here is a real advantage.

**Change:**
- **SHASTRA is mislabeled "Forensic Heuristics."** This undersells your single most impressive
  layer. SHASTRA is a real **origin estimator stack**: first-seen baseline, then a multi-observer
  timing maximum-likelihood estimator (rumour-centrality style), then a roll-up to the network
  operator (ASN), then a calibrated shortlist. "Heuristics" makes it sound like if-else rules.
  Rename it "Origin Estimator" and describe the stack. This is where the domain-understanding
  points live.
- JAAL is fine as "Fused Graph," but it is also where peel-chain tracing and mixing/CoinJoin
  set-aside live. If SHASTRA gives up "peeling, mixing," move those words to JAAL so each layer
  owns its real job.
- "LightGBM (baseline)" in BUDDHI (see 2.5).
- The DRISHTI "Console" chevron (see 2.3, 2.4).
- **PyTorch Geometric in the stack.** Right now it sits among the shipped tools, implying the GNN
  is core. You actually benchmarked the GNN and set it aside. Either move it to a small "evaluated,
  see feasibility" spot, or better, turn the rejection into a flex (section 5.3). Do not let it
  read as "we shipped a GNN" when your feasibility slide correctly says the GNN is optional.
- Minor, low priority: the "Origin" wireframe shows an IP as `198.19.x.x` (two octets visible). Your
  own truncation contract is **first octet only** (`103.x.x.x`). If you ever re-shoot that screen,
  mask to one octet. It is tiny here, so it is a rebuild-note, not a blocker.

### Slide 4: Feasibility & Viability
**Good:** genuinely strong slide, and very on-brand for the honesty-as-rigour posture. "Runs on one
laptop," "processes millions of rows locally," "truly offline," and a real risk/mitigation table.
The mitigations are specific and defensible: never hard-merge clusters, class-conditional conformal
with an abstain band, test the origin estimator against Tor/VPN/relay delays, counter-explanation
and human review before action. This is exactly what a technical panel wants to see.

**Change:**
- "8-Layer Gated Plan" vs the 9 stages on slide 3 (see 2.3).
- "GPU optional for GNN training" appears twice-ish (here and implied on slide 3). Since the GNN is
  optional and did not win, soften to "GPU optional for the WebGL view and for optional GNN
  benchmarking." Keep it honest but do not imply the GNN is required.
- "Dataset Link: Nil" sits in the RISK column and reads as a weakness. It is actually a strength:
  you built a synthetic world **with a sealed answer key**, which is the only way to *measure*
  origin accuracy at all (you cannot get ground-truth origin from the real Bitcoin network). Reframe
  it out of the "risk" framing, for example as a small note: "No public dataset carries ground-truth
  origin, so we generate a synthetic world with a sealed answer key and measure against it." That
  turns a blank into a rigor point.
- "Origin Estimation Defeated -> report limits and abstain" is good honesty. Tighten the wording so
  it points at your actual fallback: "when a host cannot be pinned, we abstain on the host and still
  resolve the network operator and region." That keeps it honest without sounding defeated, which is
  the line you care about.

### Slide 5: Impact & Benefits
**Good:** the ₹19,813 crore figure is **correct** (NCRP/I4C reported ~₹19,812.96 crore lost to cyber
fraud in 2025). Good, keep it. The impact and benefit points are relevant and on-message: crypto
crime traceability, asset recovery, wallets into leads, offline sensitive-data handling, explainable
and counter-evidenced leads.

**Change:**
- **This slide has no hard performance number, and it should.** Impact is where a quantified flex
  lands hardest. Add one line with your real numbers (section 5.1). "Operator-level attribution
  reaches the right network operator 2.46x more often than the naive baseline" is a sentence a judge
  remembers.
- Small honesty note on the ₹19,813 crore: that figure is *all* cyber fraud in 2025, and about 77%
  of it was investment scams, not specifically crypto rails. A sharp judge might ask "how much is
  crypto?" You do not have to pre-empt it, but be ready in the viva, and consider phrasing it as
  "India lost ₹19,813 crore to cyber fraud in 2025, an increasing share of it moving through crypto
  rails" so the number stays honest and still points at your problem.

### Slide 6: Research & References
**Good:** a serious reading list with the right papers (Biryukov et al on P2P deanonymization,
Dandelion++, the Elliptic GCN paper, Elliptic++, Meiklejohn "A Fistful of Bitcoins," conformal
prediction, address-clustering reliability). This signals you read the field. GitHub link present.

**Change (you already know the slide is incomplete, so these are just the real issues):**
- **Verify every arXiv ID resolves.** A few IDs look like they may be mistyped or not real, in
  particular "Critical Re-Evaluation of GNNs under Temporal Shift (2604.19514)" and "How Reliable Is
  the Multi-Input Heuristic (2607.07414)." If a judge clicks one and it 404s, it undercuts the whole
  slide. Open each link once and confirm it loads and matches the title. Fix or replace any that do
  not.
- **Swap the I4C source.** You cite `prameyanews.com` for the ₹19,813 crore stat. For an NTRO
  audience, cite the primary or near-primary source instead: the PIB / MHA release or a major daily
  (The Indian Express and LiveMint both carried the exact NCRP figure). A government stat should
  point at a government or tier-1 source, not a regional news blog.
- Fill Prototype link and Video link (you said these are coming).

---

## 4. Cool stuff you built and did not put in the deck

These are the things that would make an NTRO panel lean forward. All of them are real (they are in
the remodel and `world.json`), and none are on the current PPT.

1. **Your real accuracy numbers.** Operator-level top-1 45.9%, which is 2.46x the naive first-seen
   baseline (18.7%). Host-level lifts from 25.3% to that 45.9% when you roll up to the operator, so
   resolving to the operator nearly doubles the useful hit rate. This is the core payoff of the whole
   remodel and it is invisible on the deck.
2. **Elliptic external validation.** You did not only test on your own synthetic world; you validated
   the illicit-activity model on the public Elliptic dataset and got F1 76.6%, ROC-AUC 93.7%,
   precision 89.2%. This is the answer to "did you just grade your own homework." Huge, and missing.
3. **The rejected GNN, kept as an integrity move.** You built graph-neural-net embeddings, measured
   them on an honest inductive/temporal split, they did not beat the gradient-boosted model on your
   own gate, so you shipped the simpler model. Teams that can say "we tried the shinier thing and
   dropped it because the data said so" read as mature. Right now the deck implies the opposite.
4. **The observer-fraction curve.** You can show how origin accuracy rises with how much of the
   network you can observe, and you name a realistic "agency" vantage (~60% coverage) as your demo
   regime while still showing the honest low-vantage end. That single curve is both a rigor artifact
   and a great talking point.
5. **The multi-granular attribution ladder.** Host (sealed, officer-only) -> operator/ASN (the hero,
   shown) -> region -> calibrated shortlist. This is the legally-clean, technically-honest structure
   that separates you from "we point at an IP." The slide-2 bullet hints at it; a tiny ladder graphic
   would make it land.
6. **The court-ready, reproducible, signed packet with real legal grounding.** PRAMAAN outputs a
   packet that is Ed25519-signed, hash-chained with a Merkle head, byte-for-byte reproducible from a
   seed and command, and structured to India's evidence law: production under **BNSS 2023 Section 94**
   and full-hash disclosure under **BSA 2023 Section 63(4)**. The deck shows an "Attribution Packet"
   box and a Proof screenshot, but never says "admissible" or cites the law. For a government
   forensics tool, admissibility is half the value. Name it.
7. **Measurement discipline / the sealed answer key + validation gates.** You have automated leakage
   checks (the naive first-seen rule is *required* to score within a known weak band, so you can prove
   you are not leaking the answer). "We can prove our own pipeline is not cheating" is a rare and
   strong claim.

---

## 5. Recommended additions (with copy-paste-ready, on-rules slide text)

All slide text below follows your rules: no em-dashes, plain and precise, nothing that sounds weak.

### 5.1 A metrics strip (highest value add)
Add a small horizontal strip of 4 numbers, either along the bottom of slide 2 or as a band on
slide 5. Use exactly these:

```
Operator-level origin, top-1        45.9%      (2.46x the naive baseline of 18.7%)
Campaign recall                     95.4%
Illicit model on public Elliptic    F1 76.6%,  ROC-AUC 93.7%
Court-ready proofs from one run     9          (from 66,689 ranked leads)
```

One-line framing under the strip:

> Measured on a synthetic world with a sealed answer key, and cross-checked on the public Elliptic
> dataset. Not self-reported accuracy on data we alone can see.

### 5.2 A comparison row (you asked about this specifically)
A tiny 3-column comparison lands the novelty fast. Fits on slide 2 under the diagram, or as a small
table.

```
                        Chain-only analytics     Traffic-only analysis     CHAKRAVYUH
Sees what moved              yes                       no                     yes
Sees who transmitted         no                        yes                    yes
Resolves the operator        no                        partial                yes (ASN + region)
Court-ready signed packet    varies                    no                     yes
Runs fully offline           usually no                n/a                    yes
```

Framing line:

> Chain analytics sees what moved. Traffic analysis sees who transmitted. Neither joins the two.
> CHAKRAVYUH does, and turns the join into a defensible, operator-level lead.

### 5.3 Reframe the GNN as an integrity flex
Replace the impression that a GNN shipped. On slide 3 or 4, one line:

> We benchmarked graph-neural-net embeddings against a gradient-boosted model on an honest
> time-ordered split. The simpler model won on our own gate, so we shipped it and kept the GNN as an
> optional, separately-benchmarked add-on.

This turns a hidden weakness (people will assume GNN = better and ask why you did not use it) into a
point in your favor.

### 5.4 Name the legal admissibility on PRAMAAN
On slide 3's PRAMAAN box or on slide 5, add:

> Every proof is an Ed25519-signed, hash-chained packet, reproducible byte-for-byte from its seed and
> command, and structured for production under BNSS 2023 Section 94 with full-hash disclosure under
> BSA 2023 Section 63(4).

### 5.5 (Optional, if you have room) the observer-fraction curve
A single small line chart: x-axis "share of the network observed," y-axis "origin top-1." Mark your
demo point at ~60% ("agency vantage"). Caption:

> Accuracy scales with how much of the network you can see. We report the honest curve, and run the
> demo at a realistic national-vantage coverage.

---

## 6. The numbers you are allowed to use (agency-v2, canonical)

Use these and only these. They come straight from `world.json`.

```
Funnel:   906,560 signals -> 32,787 transactions -> 87,896 owner groups scored
          -> 66,689 ranked leads -> 9 court-ready proofs
Origin:   operator (L1) top-1 = 45.9%   |  host (L0) top-1 = 25.3%
          naive first-seen = 18.7%      |  gap over naive = 2.46x
Ceilings: operator ceiling 93.4%  |  host ceiling 48.2%  |  region ceiling 95.9%
Illicit:  campaign recall 95.4%  |  Elliptic F1 76.6%, ROC-AUC 93.7%, precision 89.2%
Cluster:  same-owner confidence dial = 0.36 (tunable, not a single hard merge)
Vantage:  observer regime "agency", ~60% coverage; literature band 11% to 60%
```

**Delete on sight (retired v1 numbers, do not let these survive anywhere on the deck):**

```
"p = 0.87" single-host origin          -> replaced by shortlist + operator resolution
"20 ranked leads" / "10^5 rows"        -> use the real funnel above
41.5% ceiling, 22.1% naive             -> use 48.2%/93.4% ceilings, 18.7% naive
"~14 announcements per tx"             -> ~28 announcements per tx (if you cite echo at all)
"1,000,000 -> 1"                        -> use 906,560 -> 9
```

Per-case caution: there is a per-case packet probability around 13.6% in the fixture. Do not put it
on a slide and do not read it aloud. The strong, honest, system-level number is 45.9%; keep the two
separate.

---

## 7. The three links slide (your plan is right, one caveat)

Your instinct is correct: judges will not open the GitHub or watch the video if the deck itself is
not impressive, so the deck has to stand alone. Once it does, the three links (video, GitHub,
deployed) are what convert "good idea" into "these people shipped it." Two notes:

- Put the video link where it gets clicked: not only on slide 6, but a small "2-min demo" chip on
  slide 3 next to the prototype screenshots, right where a curious judge is already looking.
- If you deploy, label it "runs offline, hosted copy for review" so the deployed link does not seem
  to contradict your "air-gapped / never phones home" claim. The offline story is a selling point;
  protect it.

---

## 8. Priority order (do them in this sequence)

1. Remove "TITLE PAGE"; fill Team ID; add the product name + hook to slide 1.
2. Fix the slide-2 origin diagram: shortlist + operator resolution, sealed host, kill `p = 0.87`.
3. Lock one funnel everywhere; kill "20 leads" and "10^5"; make slide 2, slide 3, and the numbers
   agree.
4. Reconcile 8 vs 9 layers; pull DRISHTI out of the chevron chain as the interface; relabel away
   from "Console."
5. Rename SHASTRA to "Origin Estimator" and describe the estimator stack; relabel "LightGBM
   (baseline)" to "risk model."
6. Add the metrics strip (section 5.1). This is the biggest single credibility gain.
7. Add the comparison row (5.2) and the Elliptic-validation line (4.2 / 5.1 framing).
8. Reframe the GNN (5.3) and name legal admissibility on PRAMAAN (5.4).
9. Verify every arXiv link; swap the I4C source to a primary one; fill the video/prototype links.
10. Optional if room: attribution ladder graphic, observer-fraction curve.

Steps 1 to 5 are consistency and finish, and they are non-negotiable because they are internal
contradictions. Steps 6 to 8 are where you actually start to impress. Everything after is polish.

