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
