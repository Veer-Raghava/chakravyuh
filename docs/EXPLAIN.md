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
