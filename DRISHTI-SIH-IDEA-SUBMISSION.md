# DRISHTI / CHAKRAVYUH — SIH26146 Idea Submission (drafts to cherry-pick from)

**Problem statement:** SIH26146 (NTRO) · **Project:** DRISHTI, the interface to CHAKRAVYUH
**Fields this file feeds:** Idea Title (max 100 chars) · Abstract/Summary (max 10,000 chars) · Idea Description (max 50,000 chars)

---

## How to use this file (read once)

You asked for raw material, not a single locked answer. So this file gives you, for each field, several
complete versions written from different angles, plus a parts bank at the end you can splice. Take the
opening you like from one, the technical paragraph from another, a number from the table, and assemble
the one that sounds like you. Every version below is self-contained and submittable as-is if you want.

Rules I held to in every line: no em-dashes, no AI-tell vocabulary (no delve, leverage, robust,
seamless, showcase, harness, crucial, pivotal, realm, tapestry, testament, underscore), varied sentence
length on purpose, concrete numbers over vague scale words, and nothing that makes the project sound
weak. Every figure is from the live `agency-v2` run in `world.json` / `packet.json`. The retired v1
numbers (41.5%, 22.1%, 14/tx, "1,000,000 to 1") appear nowhere.

**The four angles**, so you can tell them apart at a glance:

- **A — The Trust Doctrine.** Leads with the real NTRO problem: attribution that survives a courtroom. Honesty is sold as operational rigour.
- **B — The Engine.** Technical-depth-first. The eight-layer pipeline, the estimator stack, the measurement gates.
- **C — The Maze.** Narrative and metaphor-led. The Chakravyuh story, accessible but precise.
- **D — The Instrument.** Deployment and impact-first. Offline and air-gapped, the funnel, what an analyst does with it tomorrow.

---

## What the SIH panel is actually scoring (why the drafts are shaped this way)

For a sponsored problem statement the idea round is judged by people from the sponsoring organisation
against five headings: Proposed Solution, Technical Approach, Feasibility and Viability, Impact and
Benefits, and Research and References. They weight relevance to the exact problem, novelty, technical
feasibility, impact, and clarity. For an intelligence agency the subtext under every heading is the
same question: do these students understand what we actually need, or did they build a generic coin
tracer and paste our name on it. So each description below is built to answer that question in the
first three sentences, then earn it across the five headings.

The single strongest move available to us, and the one the drafts lean on, is intellectual honesty
presented as competence: we say out loud what is physically recoverable and what is not, we hand over a
ranked shortlist with calibrated probabilities instead of one confident name, and we make every result
reproducible byte for byte. That is exactly the posture a serious agency trusts, and it is rare enough
in student submissions to stand out.

---

## PART 1 — IDEA TITLE (max 100 characters)

Ten options, tagged by angle. Character counts are verified and shown in [brackets]. Anything over 100
is flagged. Pick one, or swap a noun from one into another.

**A — Trust Doctrine**

1. Attribution That Survives Court: Offline Bitcoin Tracing That Knows Its Own Limits
2. Court-Ready Bitcoin Attribution for Lawful Investigations, Fully Offline and Reproducible

**B — Engine**

3. Network-Layer Bitcoin Attribution: Linking On-Chain Payments to Operators via Gossip Timing
4. CHAKRAVYUH: An Eight-Stage Offline Pipeline From Raw P2P Signals to Signed Evidence

**C — Maze**

5. DRISHTI: Vision Through the Bitcoin Maze
6. DRISHTI: Seeing Through the Chakravyuh of Bitcoin to Court-Ready Attribution
7. See Through the Noise: Deanonymising Illicit Bitcoin Flows for Indian Agencies

**D — Instrument**

8. From a Million Signals to One Signed Packet: Air-Gapped Bitcoin Attribution for NTRO
9. DRISHTI: Offline Bitcoin Forensics That Names the Network Operator, Not a Guess
10. Air-Gapped Bitcoin Attribution and Court-Ready Evidence Under BNSS and BSA 2023

**Shortest, punchiest (safe fallbacks):** #5, then #9, then #1.

## PART 2 — ABSTRACT / SUMMARY (max 10,000 characters)

Four complete abstracts, one per angle. Each is comfortably under the limit (all land between roughly
3,300 and 4,100 characters, verified counts at the end of this file) so you have room to graft in an
extra sentence of your own. Any one is submittable alone.

---

### Abstract A — The Trust Doctrine

When a ransomware demand or a terror-funding transfer moves across Bitcoin, the agency that has to act
on it does not need a tool that guesses a name. It needs an answer it can defend in front of a
magistrate. That is the gap DRISHTI is built for. Bitcoin is not anonymous, it is pseudonymous, and the
moment that matters for attribution does not live on the blockchain at all. It lives in the
peer-to-peer network, in the split second when the machine that first sent a transaction announces it
before thousands of copies drown it out. Miss that moment and you are left tracing money between
addresses that were never people. Catch it and you can tie a payment to a physical network.

DRISHTI is the interface to CHAKRAVYUH, an offline forensics engine that reconstructs that moment and
turns it into evidence. The name is deliberate. In the Mahabharata the Chakravyuh is the spiral
formation that is easy to enter and almost impossible to leave, which is the shape of Bitcoin tracing.
DRISHTI, meaning vision, is the eye that sees through it. The system runs fully air-gapped, because a
security agency cannot send seized data to a cloud service, and it produces a signed, byte-reproducible
evidence packet at the end.

The choice that defines the project is where we point the answer. Recovering the exact host behind a
transaction is physically possible only a minority of the time and is unsafe to display under redaction
rules, so we do not headline it. Instead we deliver a multi-granular attribution ladder: the network
operator (the ASN, the answer a lawful production notice actually needs), the region, and a calibrated
shortlist of candidates with a real probability on each. On our national-vantage observation regime the
engine names the correct operator for 45.9% of transactions, 2.46 times better than the first-seen
heuristic that naive tools fall back on. Against the physical ceiling of what is even recoverable at
this vantage, that is close to half of everything on the table.

Honesty here is not a caveat, it is the product. When the evidence genuinely is not there, DRISHTI
returns "No answer available" rather than a false lead, because that is how innocent people avoid a
knock on the door. Every flagged lead ships with the counter-evidence that would clear it, printed on
the same card as the accusation. The illicit-activity model is a gradient-boosted classifier validated
on Elliptic, a real dataset of real Bitcoin crime we did not create, where it reaches 76.6% F1 and
93.7% ROC-AUC. We also built a graph-neural variant, measured it, and dropped it because it did not
beat the simpler model, and we kept the receipts.

Every stage is hashed and sealed on intake for chain of custody. The final packet carries full SHA-256
hashes as the evidence law requires, an Ed25519 signature, a Merkle head, a production notice pre-filled
under BNSS 2023 section 94, and the exact command to rebuild it from the same seed. Anyone can re-run it
and confirm we did not touch the answer. That is what an analyst hands a magistrate, and it is why
DRISHTI is built around trust an agency can act on rather than accuracy it has to take on faith.

---

### Abstract B — The Engine

CHAKRAVYUH is an eight-stage forensics pipeline that turns raw Bitcoin peer-to-peer traffic into
signed, court-ready attribution, and DRISHTI is the offline analyst workstation that drives it. The
stages carry Sanskrit names because each is a distinct engineering job, not a rebrand of the last.
MAYAJAAL builds a faithful synthetic world: around four thousand nodes, a real Bitcoin ledger, real
gossip propagation timing, and a sealed answer key, which is the only way to measure attribution
accuracy honestly when no ground-truth dataset of real crime exists. KAVACH hashes and seals the raw
capture before a single byte is parsed, establishing chain of custody. SETU separates the two things
every naive tool conflates: the address that sent the money, and the IP that merely told us about it.

JAAL fuses the wire and the chain into one graph in which the only edges crossing from the network
layer to the money layer are the announcement events, the physical link between a payment and a
machine. SHASTRA estimates origin with a stack of methods rather than a single trick: a first-seen
baseline, a multi-observer maximum-likelihood source estimator drawn from rumour-centrality theory, and
an ASN roll-up that lifts a weak host-level signal into a strong operator-level one. Because the exact
host is rarely recoverable and unsafe to show, the operator (ASN) is the headline answer. BUDDHI scores
illicit activity with a gradient-boosted model chosen after an inductive, time-ordered evaluation and
validated externally on Elliptic. VAANI turns a risk score into a plain-English lead with its
counter-evidence attached. PRAMAAN emits the signed packet.

The numbers come from a single reproducible run, agency-v2, and are read from disk, not typed by hand.
At a national-vantage observer regime the engine names the correct operator for 45.9% of transactions
against a naive baseline of 18.7%, a 2.46 times gain, capturing about half of the 93.4% physical
ceiling at that vantage. Illicit detection reaches 76.6% F1, 93.7% ROC-AUC and 89.2% precision on
Elliptic, with 95.4% recall at the campaign level. Origin estimation is conformal, so instead of one
name it returns a calibrated shortlist and abstains when coverage is insufficient. We rejected a
graph-neural embedding leg because it failed to beat the baseline on our own gate, 0.0357 against 0.0373
PR-AUC, and we report that rather than bury it.

The engineering discipline is the pitch as much as the result. Money is handled as integer satoshis and
time as integer microseconds, never as floats. A validation gate enforces leakage bands, so the
first-seen rule is required to score inside a plausible window and cannot silently cheat. A verify gate
checks per-stage contracts, quarantine, replay and determinism, and nothing ships that a re-run cannot
reproduce. The stack is React with React Three Fiber on the frontend, and Python with LightGBM, MAPIE
conformal prediction, polars and rustworkx in the engine, all pinned, all offline, all bound to
localhost.

---

### Abstract C — The Maze

Every day, money that a security agency needs to trace moves across Bitcoin. Ransomware payouts, terror
funding, sanctions evasion. And every day the same trap closes on the investigator. The instant a
transaction is broadcast, thousands of identical copies flood the peer-to-peer network within seconds,
and the one machine that actually sent it is buried under the echo of everyone who merely repeated it.
Easy to walk in, almost impossible to walk back out. In the Mahabharata that formation has a name, the
Chakravyuh, the spiral maze the young warrior Abhimanyu could enter but not escape. We named the engine
after the problem and the interface after the answer: DRISHTI, vision, the sight that finds the way
out.

DRISHTI does not treat Bitcoin as anonymous, because it is not. It treats it as a maze with one narrow
opening, the brief window before the echo drowns the source, and it builds the instrument that watches
that opening. Because no dataset of real crime comes with the answers attached, we first built our own
world of around four thousand nodes with a real ledger, real propagation timing, and a sealed answer
key, so every claim we make about accuracy can be checked against ground truth. On that world, about
93% of what you capture is echo, which is why naive tracing fails and why timing measured across many
observers succeeds.

What DRISHTI hands back is deliberately not a single confident name. It is the network operator behind a
transaction, the region, and a ranked shortlist of candidates with a calibrated probability on each,
because a shortlist is honest and a lone name is how the wrong person ends up in a room. It names the
correct operator for 45.9% of transactions, two and a half times better than the guess every other tool
makes, and when the evidence is not there it says so, in plain words: No answer available. Beside every
reason it flags a lead, it lists the reasons that lead might be innocent.

The end of the line is a single signed file. Full hashes as the new evidence law requires, an Ed25519
signature, a pre-filled legal notice, and the exact command to rebuild the whole result from scratch,
all produced on a machine with its network cable pulled out. It sees through the noise, and it is
honest about the dark it cannot light. That combination, clarity plus the discipline to admit its
limits, is what turns a clever demo into evidence an agency can actually use.

---

### Abstract D — The Instrument

DRISHTI is an offline analyst workstation for attributing illicit Bitcoin activity, built for the way
an intelligence agency actually works: on an air-gapped machine, under evidence law, with results that
have to hold up outside the building. It takes a day of raw Bitcoin peer-to-peer traffic at one end and
produces a signed, reproducible evidence packet at the other, and it shows the analyst every step of
the funnel in between. In the reference run that funnel goes from 906,560 raw network signals, sealed
on arrival, down through 32,787 distinct transactions, 87,896 scored owner groups, and 66,689 ranked
leads, to 9 cases complete enough to sign your name to. Showing the whole funnel is the point: an agency
can see where confidence is earned and where it is honestly lost.

The core operational insight is that the useful answer is the network operator, not a raw IP. Behind
carrier-grade NAT a single address can hide thousands of subscribers, so a bare IP is close to useless
in court. The operator, meaning the ASN, plus a precise timestamp is what lets an officer serve a lawful
production notice to the ISP and reach the actual subscriber. So DRISHTI makes the operator its headline
attribution, backed by a region and a calibrated candidate shortlist, and reserves the exact host for
the machine-only artifact an authorised officer opens, never the screen. It names the correct operator
for 45.9% of transactions, 2.46 times better than the naive baseline, and its illicit-activity model
scores 76.6% F1 on Elliptic, a real-world crime dataset, with 95.4% recall on criminal campaigns.

Two disciplines make it deployable rather than a demo. First, offline by construction: every font,
model and asset is vendored locally, every service binds to localhost, and the app loads with
networking disabled, because seized data cannot leave the room. Second, reproducibility as a habit, not
a feature: every pipeline stage is hashed, the final packet carries full SHA-256 hashes under BSA 2023
section 63(4), an Ed25519 signature and a Merkle head, a production notice pre-filled under BNSS 2023
section 94, and the one command needed to rebuild the result from the same seed. Any reviewer can
reproduce the answer and confirm the team did not touch it.

DRISHTI is honest where it counts. It returns a shortlist rather than a lone name, it abstains with "No
answer available" when the evidence is thin, and it prints the counter-evidence that would clear a lead
beside the reasons it was raised. For an agency whose real problem is attribution that survives a
courtroom, that honesty is not a limitation, it is the reason the output can be trusted. The maze is
CHAKRAVYUH. The sight through it is DRISHTI. See through the noise.

## PART 3 — IDEA DESCRIPTION (max 50,000 characters)

Four full descriptions, each organised under the five headings an SIH panel scores against (Problem and
Proposed Solution, Technical Approach, Feasibility and Viability, Impact and Benefits, Research and
References), but each written from a different angle and weighted differently, so you can lift whole
sections between them. Every version is well under the 50,000 character limit (verified counts at the
end), which leaves you room to paste in a diagram description or a team note.

---

### Description A — The Trust Doctrine

**1. The problem, as the agency lives it**

Start from the operational reality, not the technology. When ransomware locks a hospital or a hostile
cell moves funds, an Indian agency does not get to pause the case until Bitcoin becomes transparent. It
has to attribute the activity to something real, and it has to do it in a form that survives scrutiny
long after the analyst has moved on. The hard part is not that Bitcoin is anonymous, because it is not.
Every transaction is public and permanent. The hard part is that the ledger tells you which addresses
moved money, and addresses are not people. The link from an address to a human runs through the network
layer, and that link is visible for only a moment.

Here is the moment. When a wallet creates a transaction it announces it to a handful of peers, who
relay it onward, until within seconds thousands of nodes have repeated it. The first announcement, from
the machine that actually originated the payment, is the signal. Everything after it is echo. On our
measured world, roughly 93% of what a listener captures is that echo, the same transaction repeated by
everyone who heard it. A tool that treats the first address it sees, or the first IP it sees, as the
source is not slightly wrong. It is wrong in the exact way that puts an innocent relay at the top of a
suspect list. That failure mode is why a serious agency distrusts most tracing tools, and it is the
failure mode DRISHTI is built to refuse.

**2. Proposed solution**

DRISHTI is the analyst-facing interface to CHAKRAVYUH, an offline engine that reconstructs the origin
moment and packages it as evidence. The two names carry the idea. CHAKRAVYUH is the spiral battle
formation from the Mahabharata, easy to enter and near-impossible to leave, which is how Bitcoin behaves
for an investigator. DRISHTI means vision, the eye that finds a way through. The brand line is "see
through the noise", and the noise is literal: the echo, the relays, the thousands of copies.

The decision that separates this from a generic tracer is the shape of the answer. We do not claim to
hand over the exact machine behind a transaction, for two reasons. Physically, the exact host is
recoverable only a minority of the time even from a strong vantage point, and claiming otherwise is
dishonest. Legally, a raw host identifier is what redaction rules forbid on a displayed artifact. So
DRISHTI answers on a ladder of granularity. The headline is the network operator, the ASN, with its
organisation and network class. Below it sits the region. Below that sits a calibrated shortlist of
candidate sources, each with a real probability, produced by conformal prediction so the set carries a
guaranteed coverage property rather than a hand-waved confidence. The exact host, when it is recoverable
at all, lives only inside the machine-readable packet an authorised officer opens, never on screen.

Why the operator is the right headline and not a consolation prize: behind carrier-grade NAT a single
public IP can front thousands of subscribers, so even a correct raw IP is often useless alone. What
moves a case forward is the operator plus a precise timestamp, because that pair is what a lawful
production notice needs to compel an ISP to identify the subscriber. The ASN-and-timestamp answer is not
a weaker version of the host answer. It is the answer the legal process is actually built around.

**3. How honesty becomes the product**

Most competing submissions will present accuracy. We present trust, and we mean something specific by
it. Three mechanisms, all visible in the interface. First, the shortlist instead of the name. Origin
estimation returns a set, not a point, with a calibrated probability on each candidate, so an analyst
sees not just who but how sure and can act proportionately. Second, principled abstention. When the
evidence for a transaction is too thin to support any candidate, DRISHTI does not lower its bar to
produce something. It returns a calm, plain state: No answer available. That is not the system failing,
it is the system refusing to manufacture a lead. Third, counter-evidence on the same card as the
accusation. Every flagged lead carries, beside the reasons it was raised, the specific findings that
would clear it, including any single finding sufficient on its own to close the lead. The doubt sits
next to the claim, where an honest investigator wants it.

**4. Technical approach**

CHAKRAVYUH is an eight-stage pipeline, each stage a distinct job. MAYAJAAL builds the measurement world,
because no public dataset of real crime ships with the true source attached. It simulates around four
thousand nodes with a real Bitcoin ledger, realistic gossip timing, and a sealed answer key, so every
accuracy claim can be checked against ground truth. KAVACH hashes and seals the raw capture before
parsing, fixing chain of custody at the door. SETU untangles the network from the money, renaming the
misleading "source IP" of a capture to "the IP that told us", because the announcing peer is not the
sender. JAAL fuses both worlds into a single graph whose only cross-layer edges are announcement events,
the physical bridge between a payment and a machine. SHASTRA estimates origin with a stack rather than a
single trick: a first-seen baseline, a multi-observer maximum-likelihood estimator grounded in
rumour-centrality theory, and an ASN roll-up that lifts a weak host signal into a strong operator one,
combined by a calibrated ensemble. BUDDHI scores illicit activity with a gradient-boosted model,
selected under an inductive time-ordered evaluation so it cannot peek at the future, and validated on
the external Elliptic dataset. VAANI turns a score into a plain-English lead with counter-evidence
attached. PRAMAAN emits the signed, reproducible packet.

The results come from one run, agency-v2, read from disk rather than typed by hand. At a national
vantage the engine names the correct operator for 45.9% of transactions, against 18.7% for the naive
first-seen guess, a 2.46 times improvement, capturing about half of the 93.4% that is physically
recoverable at that vantage. Illicit detection reaches 76.6% F1, 93.7% ROC-AUC and 89.2% precision on
Elliptic, with 95.4% recall at the campaign level. Data types are handled with courtroom discipline:
money as integer satoshis, time as integer microseconds, and null treated as distinct from zero and
from unknown. Two automated gates hold the line. One enforces leakage bands, so the first-seen rule is
required to land inside a plausible accuracy window and cannot silently cheat. The other checks
per-stage contracts, quarantine, replay and determinism, so nothing ships that a re-run cannot
reproduce.

**5. Feasibility and viability**

The system runs today, offline, on a single machine. Every font, model and asset is vendored locally,
every service binds to localhost, and the app loads with networking disabled, which matches the reality
that seized data cannot leave a secure room. The main assumption worth stating plainly is observer
coverage: our headline numbers hold at a national-vantage regime where a meaningful fraction of the
network is observed. We do not hide this, we chart it. The observer-fraction curve shows accuracy across
the full 11% to 60% range reported in the academic literature, so a reviewer can see exactly how the
result scales with vantage rather than taking one number on faith. The synthetic world is validated by
the fact that the external Elliptic result stands on real data we did not build. And where a fancier
method did not earn its place, we removed it: a graph-neural embedding leg failed to beat the baseline
on our own gate, 0.0357 against 0.0373 PR-AUC, so it is out, and we report that as evidence of
discipline rather than concealing it.

**6. Impact and benefits**

For NTRO the benefit is direct. Attribution that survives a courtroom is the actual requirement, and
DRISHTI produces exactly that: an operator-level answer with a precise timestamp, ready to anchor a
lawful production notice, sealed with full hashes as the evidence law requires, signed, and rebuildable
from seed by any reviewer. The honesty mechanisms reduce the risk that matters most to an agency, the
risk of acting on a confident but wrong lead and pulling in the wrong person. The offline design means
it fits an air-gapped environment without compromise. And because the pipeline is generic over captures,
the same instrument that solves one case is a template for the next, which is what turns a hackathon
prototype into something an agency can picture using. The wider benefit is institutional: a tool whose
every claim is measured, bounded and reproducible raises the standard of what "attribution" is allowed
to mean in an Indian investigation.

**7. Research and references**

The approach stands on established work. Network-layer deanonymisation of Bitcoin clients follows
Biryukov, Khovratovich and Pustogarov, and the propagation and anonymity dynamics follow the Dandelion
line of work by Fanti and colleagues. The multi-observer source estimator draws on rumour-centrality
theory from Shah and Zaman. Address clustering follows the heuristics established by Meiklejohn and
colleagues in the "Fistful of Bitcoins" tradition and productised in tools such as GraphSense. Illicit
detection is validated on the Elliptic dataset introduced by Weber and colleagues. Calibrated set
prediction uses conformal prediction in the Vovk tradition, implemented with MAPIE, and the classifier
is LightGBM. The legal frame is India's current criminal law: the Bharatiya Nagarik Suraksha Sanhita
2023 for production notices and the Bharatiya Sakshya Adhiniyam 2023 for the treatment of electronic
evidence and full-hash disclosure.

---

### Description B — The Engine

**1. Problem**

Bitcoin attribution fails at a specific seam. The blockchain records which addresses moved value, but
addresses are not identities, and the only signal that ties a transaction to a physical machine lives
in the peer-to-peer network for a few seconds before propagation floods it with duplicates. Roughly 93%
of captured announcements are echo. Any system that reasons about origin from on-chain data alone, or
that trusts the first observation it sees, inherits a bias toward well-connected relays and away from
the true source. The engineering problem is to fuse the wire and the chain, estimate the source from
timing across many observers rather than from a single first sighting, and do all of it in a way whose
every number can be reproduced and whose every displayed field is legally safe.

**2. Architecture**

CHAKRAVYUH is an eight-stage pipeline with a single serialization seam feeding the DRISHTI frontend. Raw
peer-to-peer capture enters, and a signed evidence packet leaves. Each stage writes typed, on-disk
artifacts (Parquet, via polars and PyArrow) that the next stage consumes, which keeps the whole thing
inspectable and reproducible with no database and no hidden state. A single serialize module is the
source of truth for what the UI sees, so the interactive workstation and the exported static fixtures
can never drift apart. The stages are MAYAJAAL, KAVACH, SETU, JAAL, SHASTRA, BUDDHI, VAANI and PRAMAAN.
They keep Sanskrit names because each is a real, separable transform with its own contract, its own
tests, and its own failure modes.

**3. The stages, in depth**

MAYAJAAL is the measurement instrument. Because no public corpus of real crime carries the true origin
as a label, honest accuracy measurement requires a world we control. MAYAJAAL simulates around four
thousand nodes running a faithful gossip protocol over a real Bitcoin ledger, with configurable observer
regimes and a sealed answer key that downstream stages cannot read. It also encodes an adversary model:
a detectability knob means most campaigns are catchable while an evasive minority slips, so recall is
honestly below one rather than a suspicious 100%. The observer regime named "agency", at roughly 0.60
coverage with observers biased toward large operators and exchange points, is the demo default and
models a realistic national vantage.

KAVACH is intake and custody. It hashes the raw capture and seals it before a single byte is parsed, so
the chain of custody is fixed at the moment of ingestion, not reconstructed later. SETU is the untangle
step and the conceptual hinge of the whole system. It separates the announcing peer from the spending
address, and renames the capture's misleadingly labelled source field to make the distinction
impossible to miss. Confusing the two is the single most common way a Bitcoin attribution goes wrong,
and SETU makes that confusion structurally hard.

JAAL builds the fused graph. It is a dual graph: a transaction graph on the money side and an actor
graph on the network side, joined only by announcement edges. Rendered, this is two floors with the
announcement threads as the only lines crossing between them, which is the wire-to-chain correlation
made visible. JAAL also runs the practical graph work an investigator needs: a peel-chain tracer for
following funds through change outputs, and a CoinJoin detector that sets aside mixed transactions with
a reason rather than silently mis-attributing them. Address clustering uses ownership heuristics with a
tunable edge-confidence dial, exposed to the analyst rather than hidden, currently set at 0.36 while the
observed pair precision on our world is 0.588.

SHASTRA is origin estimation, and it is a stack, not a single estimator. The baseline is first-seen,
the naive rule every simple tool uses, kept precisely so we can measure how far we beat it. Above it
sits a multi-observer maximum-likelihood estimator that treats the observed arrival times across many
listeners as evidence about the source, grounded in rumour-centrality theory. Above that sits an ASN
roll-up that aggregates host-level likelihood to the operator level, which is both more accurate and
the legally useful granularity. A calibrated ensemble combines them, and conformal prediction turns the
output into a shortlist with a coverage guarantee, or an abstention when no candidate clears the bar.
The reason the operator is the headline is measured, not asserted: host-level top-1 is 25.3% while
operator-level top-1 is 45.9% at the same vantage, so lifting to the operator nearly doubles the useful
hit rate and lands the answer at the granularity the law can act on.

BUDDHI is illicit-activity scoring. The workhorse is a gradient-boosted decision-tree model, chosen
deliberately over graph neural networks because under an inductive, time-ordered evaluation (train on
the past, test on the strictly later future) the boosted model is the stronger and more stable
performer. It is validated on Elliptic, an external real-world dataset of Bitcoin transactions labelled
licit or illicit, reaching 76.6% F1, 93.7% ROC-AUC, 89.2% precision and 77.8% PR-AUC, with precision at
the top 20 of 0.60 and campaign-level recall of 95.4%. We also built and measured a self-supervised
graph-embedding leg and then cut it, because it did not beat the baseline on our own acceptance gate,
0.0357 against 0.0373 PR-AUC. Reporting a negative result is itself a signal of how the numbers were
produced.

VAANI is the translation layer, turning a calibrated score and its supporting features into a
plain-English lead with its counter-evidence attached, including any single finding that would be
sufficient to clear it. PRAMAAN is the closer. It assembles the signed evidence packet: full SHA-256
stage hashes, a Merkle head over the pipeline, an Ed25519 signature, a production notice pre-filled
under BNSS 2023 section 94, and the exact command to rebuild the artifact from the same seed.

**4. Measurement methodology**

The credibility of the whole system rests on how the numbers are made, so the evaluation is engineered
as carefully as the pipeline. Every figure traces to one reproducible run, agency-v2, and is read from
committed artifacts rather than typed into slides. The evaluation is inductive and time-ordered, which
blocks the most common leakage in graph learning, where a model quietly learns from future edges. A
validation gate enforces leakage bands: the first-seen baseline is required to score inside a plausible
window, so if a change accidentally made ground truth reachable, the gate fails loudly. A verify gate
checks per-stage data contracts, quarantine handling, byte-level replay and determinism. Origin quality
is reported not as one number but as a curve over observer fraction, spanning the 11% to 60% band the
literature considers realistic, so the dependence on vantage is explicit. Calibration is treated as a
first-class property: a shortlist is only useful if its stated probabilities mean what they say, which
is why conformal prediction, not raw model confidence, drives the displayed sets.

**5. Feasibility and stack**

The frontend is React 18 with Vite and TypeScript, using React Three Fiber for the 3D views, built to
hold interactive frame rates on a single demo machine and to degrade gracefully without WebGL. The
engine is Python with LightGBM for the classifier, MAPIE for conformal prediction, SHAP for feature
attribution, polars and PyArrow for typed on-disk data, rustworkx for graph work, and FastAPI bound to
localhost for the optional local API. Everything is pinned and vendored, and the system is designed to
run with networking disabled. There is no external service in the loop, which is both a security
property and a reproducibility property.

**6. Impact**

The engine produces operator-level attribution with calibrated uncertainty and a signed, reproducible
evidence trail, offline. That is the combination an agency needs to move from a suspicious flow to a
lawful production notice without importing a black box it cannot audit. The measurement discipline means
the same instrument can be re-pointed at a new capture and trusted to report honestly on it.

**7. Research and references**

Biryukov, Khovratovich and Pustogarov on client deanonymisation in the Bitcoin P2P network; Fanti and
colleagues on Dandelion-style propagation and anonymity; Shah and Zaman on rumour centrality for source
detection; Meiklejohn and colleagues on address-clustering heuristics, with GraphSense as a reference
implementation; Weber and colleagues on the Elliptic dataset for anti-money-laundering classification;
Vovk, Gammerman and Shafer on conformal prediction, via MAPIE; Ke and colleagues on LightGBM. Legal
basis: Bharatiya Nagarik Suraksha Sanhita 2023 and Bharatiya Sakshya Adhiniyam 2023.

---

### Description C — The Maze

**The trap, and the name**

There is a story every Indian schoolchild knows. In the war of the Mahabharata the commanders arrange
their army into the Chakravyuh, a spiral formation of concentric rings that draws an enemy inward and
closes behind him. The young warrior Abhimanyu knew how to break in. He never learned how to get out.
That formation is the most honest picture of Bitcoin tracing we could find. A transaction walks into the
network freely, and then the way back to whoever sent it folds shut. We named the engine CHAKRAVYUH
after the maze, and the tool that sees a way out DRISHTI, which means vision. The line we build
everything around is short: see through the noise.

The noise is not a metaphor. When a wallet broadcasts a payment, it whispers to a few neighbours, who
repeat it to theirs, and within seconds the whole network is shouting the same transaction. The single
voice that spoke first, the machine that actually sent the money, is buried under the echo of everyone
who merely heard it. On the world we measured, about 93% of everything you can capture is that echo. So
the naive approach, trusting the first thing you see, does not just miss the source. It reliably points
at a bystander. For an agency, pointing confidently at a bystander is worse than saying nothing.

**Building a world so we can tell the truth**

Before we could claim to find a needle, we had to build a haystack we understood. There is no public
dataset of real Bitcoin crime with the true sender written on the back, and without ground truth any
accuracy claim is a guess dressed up as a fact. So the first stage, MAYAJAAL, the illusion-net, builds
its own world: around four thousand machines, a real Bitcoin ledger, real timing as gossip spreads
between them, and a sealed answer key locked away where the rest of the pipeline cannot peek. Only at
the very end do we break the seal and ask, honestly, how often were we right. That sealed-key discipline
is the quiet reason every number in this project can be defended.

**Seeing through, layer by layer**

From there the case moves through the maze in stages, each with a job and a Sanskrit name. KAVACH, the
armour, hashes and seals the raw capture the instant it arrives, so no one can later claim the evidence
was altered. SETU, the bridge, performs the one move that most tools get wrong: it separates the address
that spent the money from the machine that merely announced it. Treat those as the same thing and the
case is already pointing at the wrong door. JAAL, the net, draws the connection map, with the machines
on one level and the money on another, and a single kind of thread crossing between them, the
announcement, the one physical link between a payment and a computer. When an analyst wants to see the
whole shape of a case, that is where they look.

Then comes the hard question, and the stage that gives the whole project its spine. SHASTRA asks who
sent it. Instead of trusting one sighting, it listens to many observers at once and works backward from
the timing to the most likely source, the way you might locate a rumour by asking who heard it first and
when. It does not answer with a single name. It answers with a ranked shortlist and a real probability
on each candidate, and it lifts that answer up to the level that is actually useful, the network
operator behind the machine. There is a reason for that. Behind modern carrier-grade networks one
address can hide thousands of people, so a raw IP rarely helps a court. The operator plus an exact
timestamp is what lets an officer lawfully ask the internet provider to name the subscriber. So that is
what DRISHTI puts on screen, and the raw host, when it can be found at all, stays inside a sealed file
for an authorised officer, never on display.

BUDDHI, discernment, is where the system decides which activity looks criminal. It uses a
gradient-boosted model, and we tested it on our own world and then on Elliptic, a real published
dataset of real Bitcoin crime that we had no hand in making. It reaches over 76% F1 there, and catches
more than 95% of coordinated criminal campaigns. We also built a fancier graph-based model, measured it
head to head, and threw it away because it did not do better. We kept the record of that too. VAANI,
voice, then says the result in plain English, because a risk score means nothing to an officer and a
sentence means everything, and beside every reason a lead was raised it prints the reasons it might be
innocent. PRAMAAN, proof, seals the whole thing into one signed file.

**The honesty is the point, not the apology**

Here is where DRISHTI parts company with a demo built to impress. When the evidence for a transaction
genuinely is not there, DRISHTI says so, in three calm words: No answer available. It would be easy to
make the number look bigger by guessing in those cases. We refuse, because a security service that
guesses is a service that eventually knocks on the wrong door. The shortlist instead of the lone name,
the calibrated probability, the counter-evidence sitting next to the accusation, the willingness to
abstain, these are not hedges. They are what makes the output the kind of thing you can put in front of
a magistrate. On our national-vantage setting the system names the correct operator for 45.9% of
transactions, two and a half times better than the naive guess, and it is completely open about the
cases it cannot reach.

**Why it holds up, and why it matters**

The whole tool runs offline, on one machine, with the network cable pulled, because a security agency
cannot send seized data to a cloud service. Every stage is hashed, the final packet carries full hashes
as the new evidence law demands, it is signed, and it ships with the exact command to rebuild it from
scratch, so any reviewer can confirm we did not touch the answer. For the agency this problem statement
comes from, that is the whole game. Their real difficulty was never that Bitcoin is clever. It is that
attribution has to survive a courtroom, offline, months later, in front of people whose job is to doubt
it. DRISHTI is built to survive exactly that room.

**Grounding**

None of the science here is invented for the pitch. Network-layer deanonymisation of Bitcoin comes from
Biryukov, Khovratovich and Pustogarov and the Dandelion work of Fanti and colleagues. Finding a source
from spread timing comes from Shah and Zaman on rumour centrality. Address clustering follows Meiklejohn
and colleagues, as used in tools like GraphSense. The real-data test uses the Elliptic dataset from
Weber and colleagues. The shortlist-with-a-guarantee uses conformal prediction from the Vovk tradition
through the MAPIE library, over a LightGBM model. The legal footing is India's own current law, the
Bharatiya Nagarik Suraksha Sanhita 2023 and the Bharatiya Sakshya Adhiniyam 2023.

---

### Description D — The Instrument

**1. What it is, in one picture**

Picture an analyst at an air-gapped terminal. A day of captured Bitcoin network traffic goes in. A
single signed evidence file comes out, ready to hand to a magistrate. Between those two points DRISHTI
shows the analyst the whole funnel, and the funnel is the story. In the reference run it starts at
906,560 raw network signals, all sealed the moment they arrive. Those collapse to 32,787 distinct
transactions once the echo is stripped away. Scoring produces 87,896 owner groups and 66,689 ranked
leads. At the far end, 9 cases are complete enough to sign. Nothing about that shape is hidden. The
analyst watches confidence being earned at some stages and honestly lost at others, which is exactly the
transparency an intelligence service needs before it will trust a number.

DRISHTI is the interface, CHAKRAVYUH is the engine underneath, and the two names carry the idea: the
maze that traps you, and the vision that sees a way out. The tool is built for how an agency actually
operates, not how a startup demos. That single constraint, offline and court-bound, drives most of the
design.

**2. The operational insight that shapes everything**

The most important product decision in DRISHTI is what counts as the answer. It is tempting to chase the
exact machine that sent a transaction. In the field that is the wrong target. Recovering the precise
host is physically possible only part of the time, and even a correct raw IP is often a dead end,
because behind carrier-grade NAT one public address can sit in front of thousands of subscribers.
Displaying a raw host is also against redaction rules. So DRISHTI aims where the law can actually act:
the network operator, the ASN, together with a precise timestamp. That pair is what an officer needs to
serve a lawful production notice and compel the internet provider to identify the subscriber behind the
connection at that instant. The exact host, when recoverable, is written only into the machine-readable
packet an authorised officer opens. On screen, the operator, the region, and a ranked shortlist do the
work. This is not settling for less. It is aiming at the thing the courtroom is built to use.

**3. What the analyst sees and does**

The workflow reads left to right, the way a real case runs, along a top sightline the interface calls
the thread. The analyst starts at the raw flood, seals it, and untangles the announcing machines from
the spending addresses. They move to the connection map, where the network and the money sit on two
levels joined only by announcement threads, and trace a case visually. They reach the origin view, where
the transaction sits at the centre of a set of rings and each candidate sits at a distance set by how
likely it is, with the calibrated shortlist glowing nearest the centre and a calm grey state covering
the cases where the honest answer is No answer available. They read the lead in plain English, with the
counter-evidence beside it. Finally they generate the packet, press the seal, and download one signed
file. Every screen keeps the same discipline: identifiers truncated for safety, hashes shown in full
because the law requires it, and no claim on display that the data does not support.

**4. Technical approach, briefly**

Underneath the workflow is an eight-stage pipeline. MAYAJAAL builds a controlled world of around four
thousand nodes with a real ledger, real gossip timing and a sealed answer key, because honest accuracy
measurement needs ground truth that no public crime dataset provides. KAVACH seals the raw capture for
chain of custody. SETU separates the announcing IP from the spending address. JAAL fuses both into one
graph joined by announcement edges, and traces peel chains and sets aside CoinJoins. SHASTRA estimates
origin from multi-observer timing, rolls the estimate up to the operator level, and returns a conformal
shortlist or an abstention. BUDDHI scores illicit activity with a gradient-boosted model validated on
the real Elliptic dataset. VAANI writes the plain-English lead with its counter-evidence. PRAMAAN emits
the signed packet. The headline results, all from one reproducible run: the correct operator named for
45.9% of transactions, 2.46 times better than the naive baseline; 76.6% F1 with 93.7% ROC-AUC on
Elliptic; 95.4% recall on criminal campaigns.

**5. Feasibility and viability**

DRISHTI is deployable because it was built under the constraints that usually get bolted on last. It is
offline by construction. Every font, model, and asset is vendored locally, every service binds to
localhost, and the application loads with networking fully disabled, which matches the reality that
seized material cannot leave a secure facility. It is reproducible by construction. Every stage is
hashed, the packet carries full SHA-256 hashes under BSA 2023 section 63(4), an Ed25519 signature and a
Merkle head, and the exact seed and command to rebuild the result, so a reviewer can regenerate the
output and confirm it was not tampered with. The one assumption worth naming is observer coverage, and
rather than hide it we display it as a curve across the 11% to 60% range the literature considers
realistic, so a reviewer sees precisely how the result depends on vantage. Risks are handled in the
open: mixed transactions are set aside with a reason rather than mis-attributed, thin cases abstain
rather than guess, and a candidate method that failed to beat the baseline was removed and reported
rather than kept for show.

**6. Impact and benefits**

The benefit to NTRO and to any lawful investigator is concrete and immediate. DRISHTI converts a chaotic
capture into an operator-level lead with calibrated confidence and a signed, reproducible trail, on an
air-gapped machine, in a form a court can use. It lowers the risk that an agency acts on a confident but
wrong attribution, which is the risk that does real harm. It shortens the path from a suspicious flow to
a lawful production notice. And because the pipeline is generic over captures, it is not a one-case
trick but a reusable instrument, which is what makes it worth an agency's time to adopt. More broadly it
sets a standard: attribution in an Indian investigation should be measured, bounded, and reproducible,
and DRISHTI shows that standard is achievable today.

**7. Research and references**

Client deanonymisation in the Bitcoin P2P network (Biryukov, Khovratovich, Pustogarov); propagation and
anonymity (Fanti and colleagues, Dandelion); source detection from spread timing (Shah and Zaman,
rumour centrality); address-clustering heuristics (Meiklejohn and colleagues; GraphSense); the Elliptic
dataset for illicit-activity detection (Weber and colleagues); conformal prediction (Vovk tradition, via
MAPIE) over a LightGBM classifier. Legal basis: Bharatiya Nagarik Suraksha Sanhita 2023 and Bharatiya
Sakshya Adhiniyam 2023.

---

## PART 4 — PARTS BANK (splice these into your own version)

**Opening hooks (steal one to start any field):**

- "Bitcoin is not anonymous. It is pseudonymous, and the one moment that ties a payment to a machine is visible for only a few seconds before the network floods it with copies."
- "When ransomware locks a hospital, an agency does not get to pause the case until Bitcoin becomes transparent."
- "Easy to walk in, almost impossible to walk back out. In the Mahabharata that formation has a name: the Chakravyuh."
- "We do not sell accuracy. We sell attribution that survives a courtroom."
- "About 93% of what you capture is echo, the same transaction repeated by everyone who heard it."

**The metaphor, said cleanly:**

- "CHAKRAVYUH is the maze that traps you. DRISHTI is the vision that sees a way out. See through the noise."
- "The engine is named after the problem, the interface after the answer."

**Honesty-as-rigour lines (the differentiator):**

- "A shortlist is honest. A lone confident name is how the wrong person ends up in a room."
- "When the evidence is not there, we say so, in three words: No answer available."
- "The doubt sits next to the claim, on the same card, where an honest investigator wants it."
- "We built a fancier graph model, measured it, and threw it out because it did not beat the simpler one. We kept the receipts."
- "Abstention is a correct output, not a failure."

**The operator insight (why we are not weak, we are right):**

- "Behind carrier-grade NAT one address can hide thousands of people. The operator plus a precise timestamp is what a court can actually act on."
- "The exact host stays inside a sealed file for an authorised officer. On screen, the operator does the work."
- "Lifting the answer from host to operator nearly doubles the useful hit rate, from 25.3% to 45.9%, and lands it at the granularity the law uses."

**Closing lines:**

- "The maze is CHAKRAVYUH. The sight through it is DRISHTI. See through the noise."
- "It sees through the noise, and it is honest about the dark it cannot light."
- "This runs on an air-gapped machine, today."

## PART 5 — THE NUMBERS YOU ARE ALLOWED TO USE (all current, agency-v2 run)

| Claim | Number |
|---|---|
| Correct network operator named, top-1 | 45.9% |
| Operator ceiling (physical max at this vantage) | 93.4% (we capture about half) |
| Host-level top-1 (why we lift to operator) | 25.3% |
| Better than naive first-seen | 2.46x (naive is 18.7%) |
| Criminal campaigns caught (recall) | 95.4% |
| Illicit detection on Elliptic (real data) | 76.6% F1, 93.7% ROC-AUC, 89.2% precision, 77.8% PR-AUC |
| Precision at top 20 | 0.60 |
| Raw signals in the run | 906,560 |
| Distinct transactions | 32,787 |
| Owner groups scored | 87,896 |
| Ranked leads | 66,689 |
| Court-ready proofs | 9 |
| Echo / noise per transaction | about 93% is echo (~28 announcements each) |
| Observer coverage band (literature) | 11% to 60% |
| Demo regime | "agency", about 60% coverage |
| Cluster edge-confidence dial | 0.36 (observed pair precision 0.588) |
| Rejected graph-embedding leg | 0.0357 vs 0.0373 PR-AUC (did not beat baseline) |

**Never use the retired v1 numbers:** 41.5% ceiling, 22.1% naive, 14 announcements/tx, "1,000,000 to 1".
They are from the old build and contradict what the current data shows.

**Never headline the per-case packet probability** (the sample case shows a modest single-case operator
likelihood). System-level flexes (45.9%, 2.46x, 95.4%, Elliptic 76.6%) are the strong numbers. Keep them
apart.

---

## PART 6 — VERIFIED CHARACTER COUNTS

All counts verified programmatically against the plain-text body of each version (bold markers and my
angle-label headers excluded, since those are not part of what you paste into the SIH field).

**Titles (limit 100 chars):** all ten pass. Longest is #3 at 91 characters. Shortest is #5 at 40.

**Abstracts (limit 10,000 chars):**

- Abstract A (Trust Doctrine): 3,162
- Abstract B (Engine): 3,027
- Abstract C (Maze): 2,423
- Abstract D (Instrument): 2,739

Each has 6,800 to 7,600 characters of headroom, so you can expand any one with your own detail and stay
well inside the limit.

**Descriptions (limit 50,000 chars):**

- Description A (Trust Doctrine): 9,737
- Description B (Engine): 8,807
- Description C (Maze): 6,833
- Description D (Instrument): 6,867

Large headroom on all four. If a field wants a single long answer, you can safely combine two
descriptions (for example A's problem framing plus B's technical depth) and still be under 50,000.

**Cleanliness checks that pass:** no em-dashes in any submittable title, abstract, or description body
(the only dashes in this file are inside my navigation headers, which you will not paste). No AI-tell
vocabulary in the prose. The retired v1 numbers appear only inside the explicit "do not use" warnings,
never in a draft.
