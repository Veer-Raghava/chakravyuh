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
