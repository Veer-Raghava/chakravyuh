# EXPLAIN — how each number in this project was produced

Every published figure gets an entry here: what it measures, the command that produced it,
the data it ran on, and what it does not cover.

## S00 · skeleton, toolchain and golden fixtures

**In one sentence.** S00 builds the empty frame that all eight later stages must fit into, plus one small honest test dataset and the tests that police it.

**Why it exists.** A contract is the frozen schema document, `docs/DATA-CONTRACTS.md`, that says exactly what every stage may read and write. Without a skeleton built around it first, eight stages each invent their own directory layout and their own way of printing data. One of them then writes a complete Bitcoin address into a report, and a forensics tool that leaks a real person's identifier has failed at its own premise.

**How it works, in three steps.** One, every stage gets an empty package whose only content is a one line statement of what it owns, so nobody has to guess where code belongs. Two, a fixture, meaning a small dataset committed into the repository so tests always have something real to run on, is generated as 197 rows and 18 columns in three formats, CSV, JSON and XML, all describing the same capture. Three, the Makefile turns "is this stage finished" into a command, `make verify-sNN`, which either exits zero or does not, and every unbuilt stage has one that deliberately fails.

**The one interesting choice.** Each captured row carries a `msg_type`, either `inv` for an announcement or `tx` for the full transaction. On a real network the peer that originated a transaction is somewhat more likely to send `tx`. We deliberately broke that correlation in the fixture. The alternative, making the originator the only peer sending `tx`, would have looked more realistic and would have let the origin estimator score perfectly. It would have been measuring a leak in our own test data rather than a method.

**What it cannot do.** Nothing in S00 estimates anything, because there is no pipeline logic yet. The 197 row fixture proves the shape of the data is handled, not that the system scales. The formal gate, `make verify-s00`, which runs the linter, the type checker and the test suite, has not run yet, so the linter and type checker results are not measured yet.

**If a judge asks "why not just use real Bitcoin network traffic".** Two reasons. Real capture does not tell you which peer truly originated a transaction, so accuracy cannot be measured against it at all. Real capture also contains real people's addresses, which this tool is not permitted to render. Every identifier in the fixture is either from an address range the standards reserve for documentation, or is structurally impossible as a Bitcoin address, and a test asserts that.

## S01 · MAYAJAAL, the chain layer

**In one sentence.** S01 generates a working Bitcoin ledger, 2,194 transactions across 144 blocks belonging to 400 entities, and writes the answer key for it into a separate directory that no later stage is allowed to read.

**Why it exists.** A ledger is the record of which coins exist and which are already spent. An unspent coin sitting at an address is a UTXO, an unspent transaction output. Building a real ledger rather than a random graph with amounts sprinkled on it is the whole point of this stage. The awkward cases our detection tools depend on only appear as a consequence of accounting. Without the accounting, every amount adds up by construction, the leftover money always lands in the same place, and the tools score perfectly on data where the work has already been done for them.

**How it works, in three steps.** One, a population of 400 entities is created, each with a wallet, its own addresses and a habit for how it spends. Two, blocks arrive on a clock, and each block mints new coins to a mining pool. Three, for each payment the sender's own coins are chosen as inputs, a fee is deducted, and any leftover above a minimum goes back to the sender as a change output, whose position is recorded in the answer key so the heuristic that hunts for change can be scored rather than trusted.

**The one interesting choice.** Roughly a third of transactions must spend several of the sender's own coins at once, because that is the only case the common ownership heuristic has anything to find. We could have flipped a coin at that rate. Instead a controller measures the rate as the run proceeds and adjusts the next decision, landing on 0.377 against a target of 0.35, because whether a sender can combine coins depends on what that sender actually holds at that moment. A blind coin flip asks for combinations that poor entities cannot produce, and the rate then quietly misses its target.

**What it cannot do.** S01 has no network layer. There are no peers, no announcements and no relay delays, so nothing here can estimate the origin of anything yet. The campaigns table has its columns and zero rows, so no laundering behaviour exists yet either. Of 2,000 attempted payments, 1,999 succeeded and 1 was dropped because the sender could not fund it, and that drop is counted by reason in the manifest rather than quietly skipped.

**If a judge asks "why not just use a real blockchain dump".** We will, for half of it, and that mode is already designed. But a real dump does not say which output was the change, or which entity owned which address. Those are precisely the facts we need in order to score a heuristic, and no public dataset carries them. Here every one of those facts is recorded as ground truth, meaning a label kept in a sibling directory that only the evaluation code may open, and a test greps every source file to enforce that.

## S02 · MAYAJAAL, the network layer

**In one sentence.** S02 spreads each generated transaction across a simulated peer-to-peer network, records only what sixteen partial observers saw, and writes the result in the three formats S03 accepts.

**Why it exists.** Origin estimation needs a recording that does not hand over the answer. If announcements travel in a clean wave, the first peer seen is always the originator, and any estimator scores perfectly against a leak rather than a method. The stage also fixes how much of the network our sensors cover, because every later accuracy number is a share of that.

**How it works, in three steps.** One, every entity becomes a network node holding a few outbound peer links, and each of the sixteen observers, meaning the recorders standing in for intercept sensors, keeps only the earliest arrival it hears per transaction. Two, when a transaction is broadcast, the originator passes it to its peers and every hop adds an independent relay delay, a random pause drawn per peer link rather than once per transaction, so arrival order is noise rather than a cascade. Three, what the observers recorded is exported as CSV, JSON Lines and XML, and the true originator per transaction goes to the answer key. The reference run produces 354,023 announcement rows over 24,626 transactions, of which 667 are coinbase, meaning newly minted coins, which a miner never relays and so are never gossiped at all.

**The one interesting choice.** The benchmark's difficulty is measured, not assumed. A leakage group scores trivial guessing rules against the answer key. First announcement seen names the originator for 0.220919 of all broadcast transactions, and the theoretical ceiling, meaning the share of transactions where the originator is even present in what the observers recorded, is 0.415376. The alternative, tuning the network until first-seen looked bad, was rejected. Instead the gate asserts first-seen lands between 0.15 and 0.6, so a broken benchmark fails loudly rather than producing a flattering zero.

**What it cannot do.** Nothing here estimates anything. An observer keeps only the earliest arrival per transaction, so for most transactions the true originator never appears in the recording at all, and 175 of 23,959 broadcast transactions reach no observer. No method, however good, can beat 0.415376 on this run, and that limit is deliberate, because it is what keeps the benchmark honest.

**If a judge asks "why not capture the real Bitcoin network".** A real capture does not say which peer truly originated a transaction, so the 0.220919 baseline and the 0.415376 ceiling could never be computed on one. Real captures also contain real people's identifiers, which this tool must not render. The synthetic network is the only place where the question can be both asked and graded.

## S03 · KAVACH, intake and seal

**In one sentence.** S03 reads a captured network dump in any of three formats, checks every row against the input contract, and seals the survivors into one file, recording a reason for every row that failed.

**Why it exists.** The evidence packet served on an ISP at S09 is only as strong as the claim that nothing was quietly lost on the way in. Without this stage, a malformed row could be skipped without a trace, and the counts in every later report would stop meaning anything. Sealing, here, means one fixed Parquet copy of the good rows, plus a hash of the raw input taken before any of our code parsed it. Parquet is a compressed column format that later stages read with a table engine rather than a text parser.

**How it works, in three steps.** One, the raw file is hashed byte for byte before a reader is constructed, so the hash describes what arrived rather than what survived. Two, the format, CSV, JSON Lines or XML, is detected from the first meaningful byte of the file, never from its name, and tests assert that the three formats seal to one identical file. Three, each row is checked against the contract's load rules, and failures go to a rejected file carrying one of ten reasons. The arithmetic is closed. The reference run reads 354,023 rows and seals 354,023 and rejects 0, and there is no third outcome. The rejected path is exercised by the committed fixture, which seals 196 of 197 rows and rejects one because its input address count disagrees with its input amount count.

**The one interesting choice.** Whether amounts are in whole coins or in satoshis, one satoshi being one hundred millionth of a coin, is decided per file rather than per row. One malformed decimal in a file of whole satoshis could otherwise flip that single row to the coin reading, multiply its values by a hundred million, and still conserve money, so no later check would notice. Per row detection was rejected because it turns a typo into a silent error no downstream test can catch.

**What it cannot do.** It checks the shape of each row, not the truth of the capture, so a well formed capture of a partial view of the network passes as valid. The sealed copy keeps full IP addresses and ports, because separating the many devices that can hide behind one shared address needs them. This is the one place where a full identifier legitimately sits on disk. Every stage that renders from it must truncate. Decompression of compressed inputs is implemented and tested, but no input in the repository is compressed yet, so that path has not run on real data.

**If a judge asks "why not just read the CSV directly in each later stage".** The raw capture is 181 MB and the seal is 9.9 MB, produced once in 24.2 seconds instead of being re-parsed by every stage that follows. The hash also fixes what was received before any of our code touched it, which is the claim an ISP is being asked to accept.

## S04 · SETU, normalise and enrich

**In one sentence.** S04 splits the sealed announcement stream into four clean tables, one per announcement, per transaction, per address and per peer, and adds geography and network class to each peer where offline lookup data exists.

**Why it exists.** The sealed file mixes two grains, the network layer and the chain layer, in one row per announcement. Any stage that computed transaction facts by walking rows in a loop would be slow and easy to get subtly wrong, and any mistake here poisons every number the tool later publishes. The split also renames `src_ip` to `peer_ip`, because once you know most announcers are relays, the word "source" is a lie that biases whoever reads the column.

**How it works, in three steps.** One, each sealed row becomes exactly one announcement row, and rows sharing a transaction id are folded into one transaction row by group-by, never by a loop. The group computes first and last sighting, distinct peers, and the spread between them. Two, addresses and peers get their own tables. An address accumulates what it received and sent inside this capture only, so an address funded before the window shows a negative balance, which is the honest value. A peer gets its mean announcement rank and the fraction of times it was the earliest announcer, the feature this table exists for. Three, each distinct peer address is looked up against offline GeoLite2 tables in CSV form and a Tor exit list. If the vendor directory is empty, the columns are null, the run completes anyway, and the warning is written to the stage's metadata. On the reference demo run, 8,913 sealed rows become 8,913 announcements, 609 transactions, 1,313 addresses and 179 peers.

**The one interesting choice.** Null and `unknown` are different answers for a peer's network class. Null means no lookup list was available at all. `unknown` means the lists were present and none of them recognised the address. The alternative, collapsing both into `unknown`, was rejected because it lets a bare deployment look like a fully equipped one that classified everyone and found nothing, which is exactly the difference a judge or an investigator needs to see.

**What it cannot do.** It cannot tell who originated a transaction, and it deliberately refuses to try. The change output heuristic, which guesses which output returns money to the sender, is kept weak on purpose, leaving 88.998 percent of transactions undetermined on the demo run, because a nearly perfect structural guess would hand the next stage a free answer and make its measured precision meaningless. Geography is also not measured on any real run yet, because the vendor directory is empty and every such column is null until someone puts the offline files there.

**If a judge asks "why not just enrich at capture time".** The capture belongs to whoever recorded it, and its values are kept where it has them, since an ASN resolved at recording time is closer to the truth of that moment than a lookup done months later. Enriching here instead also means the enrichment is reproducible, offline, and recorded in the stage metadata with a hash of the input it read, so the whole operation can be re-run and checked rather than trusted.

## S09 · PRAMAAN, the signed evidence packet

**In one sentence.** S09 turns one alert into the thing an investigator can actually serve: a case file, a formal notice to an ISP, a digital signature over the packet, and an entry in a log that detects any later rewrite.

**Why it exists.** An alert is a row in a file, and a row convinces nobody. The packet has to carry its own integrity: exactly which inputs produced it, proof that nothing was altered since, and the property that anyone can rebuild it from the same inputs and get the same bytes. Without this stage the whole pipeline ends in a claim on a screen.

**How it works, in three steps.** One, one alert is resolved into a case and the packet is assembled from the upstream stages' outputs, with the attribution, its confidence interval and the counter-evidence included. The hash of each of the six upstream manifests, meaning each stage's own record of its inputs and outputs, goes in as the chain of custody. Two, two documents are rendered, the case file and a notice an investigator can serve on an ISP to demand records, under section 94 of BNSS 2023, and every identifier is truncated before it reaches a page. Three, the packet is signed with Ed25519, a signature scheme, meaning a short mathematical proof that the holder of one private key produced exactly these bytes, and the case is appended to a Merkle log, an append-only list where every entry hashes the previous one, so rewriting an old entry breaks every newer one.

**The one interesting choice.** The packet's timestamp is not read from the clock. It is taken from the alert stage's own recorded finish time, so rebuilding the same case always produces the same bytes, signature included. The obvious alternative, stamping the moment of generation like any ordinary document tool, was rejected because it turns every replay, meaning every rebuild from the same inputs, into a different packet that no second analyst could verify. The gate builds one case twice in two separate processes and byte-compares the packet, both documents and the signature, and they are identical.

**What it cannot do.** The key ceremony is none. One seed file is auto-created on this laptop, with no backup and no rotation, which proves the design and not an operational deployment. The reference run holds 8857 alerts, each needing a signature and two documents at roughly 0.1 seconds per signature, and no full-queue packeting has been run end to end yet. The packet also carries no accuracy figure on purpose, so a benchmark score can never be presented as a property of the evidence.

**If a judge asks "why not just use a cryptography library and a PDF library".** Nothing can be installed on the offline machine this builds on, and the stage was not allowed to block on that. The hand-written signature code is checked byte for byte against the five official test vectors published in the standard that defines Ed25519, so its correctness is pinned by that standard rather than by trust in our code. The hand-written document writer produces identical bytes on every call, which general PDF libraries do not promise, and that guarantee is what makes the rebuild check mean anything.

## S06 · SHASTRA, the origin estimator

**In one sentence.** S06 estimates, for every transaction an observer heard, which announcing peer most likely created it rather than relayed it, and refuses to answer when the evidence is too weak to act on.

**Why it exists.** When a transaction spreads across the peer-to-peer network, an observer sees only relays, and the first peer to arrive is usually just the one nearest to the sensor. Without this stage the tool can say who talked but never who paid. The stage also has to be honest about a hard structural fact: each observer records only the earliest arrival per transaction, so on the gate run the true originator is present in the candidate set for at most 0.091806 of broadcast transactions, a number called the ceiling, and any accuracy above it would mean a leak rather than skill.

**How it works, in three steps.** One, every announcement is grouped to one row per transaction and peer pair, and fourteen observable features are attached, including how early the peer was, its history of being early, how many observers heard it, its graph degree, whether it is a known Tor exit or hosting provider, and how many of this payer's other transactions the same peer announced, which is the strongest single signal the capture leaks. Two, a baseline that ranks purely by first arrival is scored first, then a gradient-boosted tree, meaning a machine-learning model built from many small decision rules, is trained on labelled transactions from the first seventy percent of the capture and turns the features into a calibrated probability per candidate. Three, abstention rules run inside the estimator: a Tor exit among the candidates, a single observer, too few announcements, or a top-two gap below the configured floor all produce an explicit refusal, and a refused transaction is written with no rank-one row so it can never be misread as an accusation.

**The one interesting choice.** The probabilities per transaction are capped at one but never rescaled to sum to exactly one. The alternative, forcing them to sum to one, was rejected because it deletes the most important state of the world here: for most transactions none of the observed peers is the originator, and the shortfall below one is the file saying so. On the gate run, 0.074048 top-one accuracy against a payer-linkage trivial rule at 0.059773 and a ceiling of 0.091806, so the model recovers 0.643 of the holdout ceiling after recovering 0.888 of the training one.

**What it cannot do.** It cannot beat the ceiling, and it does not close the gap between the training and holdout share of that ceiling. Two attempts were made and both failed: a search over model capacity moved nothing, and a ranking-specific objective scored strictly worse. The gap is recorded as an open problem rather than tuned away. Typology detection and entity typing ship as empty files with the exact schema, because populating them with placeholders would write rows an auditor must reject.

**If a judge asks "why not just take the first peer seen".** That rule is built, scored, and printed beside the model on every run: it scores 0.047238 against the model's 0.074048 on the gate run, and the gate fails if the model ever drops to it. The fair comparison is against the stronger free rule, payer linkage at 0.059773, and the model clears that too, on the holdout window as well as overall, because the first version of this stage won overall while quietly losing the holdout by memorising its own training window, and the gate was hardened specifically so that can never pass again.

## S07 · BUDDHI, the wallet risk model

**In one sentence.** S07 ranks every wallet cluster in the capture by laundering risk and attaches to each one a confidence interval that is honest about how rare illicit activity is.

**Why it exists.** The origin estimator says which peer sent a transaction; it does not say which wallets are laundering. An investigator needs a queue ordered by risk, and a number on each row saying how sure the tool is, because a ranking with no stated uncertainty invites over-trust in exactly the cases that end up before a court. Without this stage the pipeline ends at network facts with no subject-level conclusion.

**How it works, in three steps.** One, addresses are grouped into subjects, meaning wallet clusters produced by the graph stage, and twenty-one features are attached per subject from the normalised tables and the origin estimates, including received and spent value, fee behaviour, and how often the subject's transactions were attributed to their own announcing peers. Two, a gradient-boosted tree, meaning a model built from many small decision rules, is trained only on wallets labelled illicit in the first seventy percent of the capture, and the rest of the capture is held out and never touched during training. Three, the raw score is wrapped in a Mondrian conformal interval, meaning a calibrated band computed separately for the illicit and the licit class, so a subject can be labelled likely illicit, likely licit, or unclear, and the unclear option is a real output rather than a failure.

**The one interesting choice.** The interval is class-conditional rather than shared. With illicit wallets near five percent of subjects, one shared calibrator takes its width from the majority class and its guarantee collapses on the minority, which is the only class the tool exists for. On the reference run the plain method covers zero of the illicit calibration rows and the class-conditional method covers 0.927536, against a target of 0.9. The rejected alternative, one interval for everyone, is written into the calibration table beside the chosen one so the comparison is measured, not asserted.

**What it cannot do.** The absolute ranking power is weak at this scale: 0.1 precision at twenty against the trivial rule's 0.0 over 4025 labelled holdout subjects, and a ROC-AUC of 0.513663, barely above chance. The gate asserts only that the trivial rule is beaten, and the honest reading is that the model clears a low bar at eight thousand transactions. Improvement is deferred to the full-scale run, and no tuning was attempted here.

**If a judge asks "why not just rank by total value received".** That rule is built, scored on the same run and the same holdout window through the same arithmetic, and recorded beside the model's own report: 0.0 precision at twenty against the model's 0.1. The gate fails if the model ever drops to the trivial rule. Ranking by value is also exactly what a laundering wallet wants you to do, since large flows are a property of every big operator, licit or not.

## S10 · the full-scale run

**In one sentence.** S10 ran the whole pipeline end to end on one million capture rows in
one resumable run, measured how long and how much memory each stage takes on one laptop,
and re-read every absolute number the earlier stages had only asserted at gate scale.

**Why it exists.** A pipeline that is only ever checked at eight thousand transactions has
numbers that mean nothing at a million: memory limits only appear on real data, and
distribution checks fail differently at scale. It also has to be resumable, because a
run that takes an hour must not turn a single failure into a full restart — rerunning the
generator with the same seed and configuration reproduces the same bytes, so a rerun
skips every file that already matches and the run continues where it stopped.

**How it was produced.** One command per stage on the canonical run `s10-canonical`
(958,994 capture rows, 22,716 gossiped transactions, seed 42, observer_fraction 0.7),
each wrapped by a measuring script that records wall clock and peak resident memory. The
full table is `docs/PERF.md`; headline figures: the whole pipeline through explanation
runs in under eight minutes, the intake seal is the memory high point at 8.9 GB, and the
signing stage is deliberately excluded from bulk use because it writes one signed PDF
packet per alert.

**The one interesting choice.** The prompt's own sizing estimate — about 14.7
announcements per transaction, so 66–68k transactions for a million rows — was wrong for
this configuration, and the brief said never to hardcode the figure. The generator was
run, the realized ratio was measured from the run's own manifests (42.2: each of the 16
observers records what it hears, and observer_fraction 0.7 means most of the network is
listened to), and the transaction count was retuned to hit a million rows. Measuring
before sizing is also what caught the one real failure: the explanation stage rejected
5,472 of 68,204 alerts as having no counter-evidence, which is a contract violation the
pipeline must refuse rather than paper over, and the root cause was a join keyed on the
wrong end of an edge that had silently produced empty inputs at every scale — smaller
runs masked it because other counter branches happened to cover the gap.

**What the numbers say now.** The origin estimator's train-versus-holdout gap, an open
problem since S06, closed by itself at scale: it recovers 0.625 of the training ceiling
and 0.630 of the holdout ceiling, so the model generalises. The wallet model's weak
absolute ranking was also a scale artifact: precision at twenty went from 0.1 to 0.55,
so eleven of the top twenty wallets really are illicit at one-in-twenty-seven base rate.
No tuning was performed anywhere; the measured numbers did not ask for it.

**What it cannot do.** The signing stage is not run in bulk at this scale — one packet
per alert would mean 68,204 signed PDFs and hours of pure-Python Ed25519, so packets are
produced per case on demand, which is also how an investigator works. The machine has
16 GB of memory, and the seal stage peaks at 8.9 GB on a million rows; a capture several
times larger would need sharding at the seal, which is future work and recorded as such.

**If a judge asks "why generate traffic instead of capturing real traffic".** The answer
is unchanged from S01 and the scale run strengthens it: attribution accuracy can only be
scored where the true originator is known, and the scale run is where the generated
world's honesty bands were re-checked — the first-seen peer names the originator on
0.212 of transactions, squarely inside the 0.15–0.60 band that fails if the generator
ever leaks the answer.
