# DECISIONS — the choices made, dated, with the reason and the alternative rejected

## 2026-09-04 · S00 · IPv6 truncation keeps two hextets

CLAUDE.md specifies the redaction rule for IPv4 only: octets three and four become `x`. No
rule exists for IPv6, and the fixture contains an IPv6 peer, so `scripts/peek.py` had to
choose one. It keeps the first two hextets and appends `x`, which hides the same fraction of
the address as the IPv4 rule.

Rejected: truncating IPv6 to a `/64` prefix. That is the network operator's boundary, not a
privacy boundary, and it leaves enough of a SLAAC address to identify a single machine.

This is a choice, not an inherited contract. If a later stage needs a different width, the
rule lives in one function, `peek.truncate_ip`, and `tests/test_peek.py` pins it.

## 2026-09-04 · S00 · the forbidden ground-truth column set is matched exactly, never by substring

`docs/DATA-CONTRACTS.md` section 2 says no column name in that section may appear in any
observable artifact. Read literally that is unsatisfiable: section 2 lists `addresses`,
`typology` and `txids`, and sections 5 and 6 define those same names as observable columns of
`graph/` and `signals/`.

`tests/test_contracts.py` therefore matches column names exactly rather than by substring.
The capture legitimately carries `input_addresses` and `output_addresses`, and a substring
rule rejects the fixture for containing the forbidden name `addresses`.

Exact matching passes today because the capture schema and the section 2 schema share no
column name. It collides at S05 and S06, which are the stages that introduce the overlapping
names. Whichever session builds them must narrow `FORBIDDEN_GT_COLUMNS` to the names that are
genuinely labels rather than shapes, and record the narrowing here. The contract is frozen;
the test's reading of it is not.

## 2026-09-04 · S00 · the fixture rows are generated from a hand-authored table, not hand-typed

The brief asks for a hand-written capture. Chosen: hand-author the twenty-six transactions and
the peer roster as literals inside `scripts/make_fixtures.py`, and generate the CSV, JSONL and
XML from that one source. Every value a human chose is still chosen by a human; only the
serialisation is mechanical.

Rejected: typing all three files by hand. Three files times 197 rows is 591 hand-typed rows, and
nothing would guarantee that they agree with each other, nor that invariant 5 holds — rows
sharing a txid must carry byte-identical chain columns. Copying those columns from one `Tx`
literal makes invariant 5 true by construction instead of true by proofreading.

`tests/test_contracts.py` deliberately does not import the builder. It reads the three files back
off disk and compares them row by row, so a bug in the generator fails a test rather than being
trusted away. Revisit if an awkward case ever needs a row the table cannot express; add the
literal, do not hand-edit the output files.

## 2026-09-04 · S00 · `--seed 42` is recorded for provenance and never consumed

`make_fixtures.py` contains no random number generator at all. Every timestamp offset, amount and
peer assignment is an explicit value or an arithmetic function of the row index. The seed is
written into the XML header and the fixtures README so the provenance line is honest, and it
changes nothing if you change it.

Rejected: seeding a `random.Random(42)` and drawing the awkward cases from it. That reads more
like the rest of the project, but it makes byte identity depend on the stability of Python's
Mersenne Twister stream across interpreter versions, and it makes "row 39 exists to cover CGNAT"
a fact you can only discover by running the generator.

Revisit at S01. MAYAJAAL needs distributional variety, so it does need a seeded generator; the
determinism contract there is same-seed-same-bytes, not no-RNG.

## 2026-09-04 · S00 · `msg_type` is not correlated with arrival rank

Chosen: `msg_type` is `tx` for one row in four by position (`i % 4 == 2`) and `inv` otherwise,
independent of which peer announced first.

Rejected: the more realistic-looking pattern where the originating peer sends `tx` and every
relay sends `inv`. On a real wire that correlation is partly true, and that is exactly the
problem — it would make origin estimation a dictionary lookup on `msg_type`, SHASTRA would score
100% on the fixture, and every accuracy number the project publishes would be measuring a leak
rather than a method.

Revisit only with a measurement from real capture data, and if the correlation is put in, the
fixture must stop being the set that origin accuracy is reported on.

## 2026-09-04 · S00 · both test files are stdlib-only and carry a `__main__` runner

Chosen: `tests/test_contracts.py` and `tests/test_peek.py` import nothing outside the standard
library, and each ends with a loop that runs every `test_*` function and exits non-zero on
failure. `scripts/peek.py` reads CSV with the `csv` module for the same reason and imports polars
only inside `_load_parquet`.

Rejected: writing them as ordinary pytest tests against polars. That is shorter and it is what
later stages will do, but this session could not build the environment — see `STATE.md`, Open
problems 1 — and a test suite that cannot run is worth nothing. Being runnable under a bare
interpreter is also what lets a future session check redaction before `uv sync` has succeeded.

Revisit for later stages: S01 onward genuinely needs polars in its tests, and duplicating this
constraint there would be dogma. Keep it for these two files, which exist to check the things you
want checkable when the toolchain is broken.

## 2026-09-04 · S00 · fixture addresses pad between the marker and the tag

Chosen: `_addr` builds an address as prefix, the literal `fixture0`, then padding, then the
per-address tag, so the tag lands on the last characters.

Rejected: `.ljust(width, pad)`, which was the first implementation. It puts the padding last, so
every address ended in the same run of `q` or `2` characters, and CLAUDE.md's first-six-last-four
truncation rendered ninety distinct addresses as a handful of identical strings — the fixture
looked like it had almost no addresses in it. Ninety addresses now produce eighty-seven distinct
truncations; the three remaining collisions are inherent to a six-and-four rule and are left
alone.

Revisit never, but know the trap before editing `_addr`. Anything that pads at the end breaks
readability of every peek output downstream.

## 2026-09-04 · S01 · per-transaction truth lives in a third file, `ground_truth/chain_txs.parquet`

`docs/DATA-CONTRACTS.md` section 2 defines two tables, `entities` and `campaigns`, and neither
has a row per transaction. The chain layer nevertheless produces three facts that are answer
keys and must not be observable: which entity sent a transaction, which entity owned each
input, and which output was the change. Chosen: a third quarantined file,
`ground_truth/chain_txs.parquet`, with columns `txid`, `entity_id`, `input_entity_ids`
(list[str]), `change_index` (int32, `-1` when the remainder was below dust and no change
output exists), `heuristic_violation` (str) and `block_height`. It is named here because it is
not in the frozen contract and an undocumented file under `ground_truth/` is otherwise
indistinguishable from a leak.

`heuristic_violation` is a string, not a boolean: S05 has to report precision per heuristic,
and a boolean cannot say *which* heuristic a transaction breaks. Multiple violations join with
`|` after sorting, so the column is greppable and its order does not depend on the generator.

Rejected: adding the columns to `campaigns.parquet`. The contract's seven columns stay byte for
byte, and a campaign is not a transaction. The S01 brief asked for `change_index` in
`campaigns.parquet`; that line was an error in the brief and has been corrected to point here.

## 2026-09-04 · S01 · one write-only door out of `src/`, enforced by two assertions

`tests/test_contracts.py` greps every file under `src/` for the literal `ground_truth` and
allows exactly one hardcoded path, `src/chakravyuh/mayajaal/writers.py`. The exemption is paid
for by a second assertion: that same file may never load anything — no dataframe reader, no
text or byte load, no directory listing, and no file handle opened without an explicit write
mode. One door, and it opens outwards.

Rejected: reaching the path through a config key or a constant in another module. That is what
would make the grep bypassable by every later stage, and the grep is the primary leakage guard;
hiding the string would trade a mechanical check for a convention.

The visible cost is that section 10 wants a sha256 of every output and this module cannot write
a file and read it back. Every frame is therefore serialised into a `BytesIO`, the buffer is
hashed, and the buffer is written — the hash covers the bytes on disk because they are the same
bytes.

## 2026-09-04 · S01 · ground truth is one sibling directory per run

Truth for a run named `foo` goes to `ground_truth/foo/`, not to a shared pile at
`ground_truth/`. Two runs then cannot overwrite each other's answer key, and `make verify-s01`
can compare both halves of two same-seed runs — the observable files and the labels — rather
than only the observable ones. A generator that agreed on every capture byte and disagreed on
the answer key would otherwise pass.

The directory name is derived from the output path inside `writers.py`. It is deliberately not
a CLI argument: an argument for where truth lands is an argument that could point somewhere
unquarantined.

## 2026-09-04 · S01 · the endowment is a prehistory, dated one block before the run starts

Every entity begins with one to five UTXOs created by a synthetic transaction at
`start_height - 1`, drawn at `value_mu + endow_mu_offset` per type. Nothing in the run spends
into existence; the first real transaction spends coins that already exist.

Rejected: starting from an empty ledger and letting coinbases fund everyone. Coinbase maturity
is 100 blocks, so the first hundred blocks would contain no spendable money at all, and at the
sizes the tests run the whole run would be coinbases.

`endow_mu_offset` is the liquidity knob and it is the one to turn if the drop rate rises. At
2,000 attempted payments it produces one drop; a run that drops more is telling you entities
are too poor to pay what their type's amount distribution asks of them, and every drop is
counted by reason in `_meta.json` rather than silently skipped.

## 2026-09-04 · S01 · the multi-input rate is steered by a controller, not sampled

`chain.multi_input_rate` is a target the run must hit within
`validation.multi_input_rate_tolerance`, and whether a payment can consolidate depends on what
that sender happens to hold. Chosen: a proportional controller over the running rate — the
probability of asking for two or more inputs is `target + gain * (target - measured)`, clamped
to `[0, 1]`. Measured 0.377 against a 0.35 target at verify size.

Pool payouts feed the same controller, because the aggregate the test measures is every
non-coinbase transaction and a controller blind to a third of them would steer the wrong
number.

Rejected: an integral term. The run is a single sweep with no setpoint changes, so there is
nothing for it to integrate away. Marked in the code as a deliberate simplification.

## 2026-09-04 · S01 · `change_address_reuse` fires on most spends, and that is left alone

Roughly 62% of spends carry a `change_address_reuse` violation, because the three types whose
`change_policy` is `reuse` — exchange, service, mining_pool — hold most of the sender weight.
That is the honest consequence of the configured policies, not a bug, and it is why the
violation is recorded per transaction: S05 can report the change heuristic's precision on this
population instead of assuming it.

Revisit only by changing `change_policy` or the type shares in `run_config.json`, and only with
a reason to believe real exchanges rotate change addresses. Do not special-case the label.

## 2026-09-04 · S01 · `chain/` reuses section 1's column names verbatim

`chain/transactions.parquet` names its columns `txid`, `block_height`, `block_time_us`,
`input_addresses`, `output_amounts`, `script_types`, `fee_sats`, `vsize` — the names section 1
gives the capture rows, not new ones. S02 fans one transaction out into its announcements by
attaching observer columns, with nothing to rename and no mapping table to keep in step.

`is_coinbase` is the single addition. A coinbase is a public fact about a transaction that
anyone reading the chain can see, so it is not a label.

## 2026-09-04 · S01 · money is integer satoshis, and floats exist only at the draw boundary

Every amount, fee and subsidy is `int64` satoshis end to end. The lognormal draws that produce
amounts, fee rates and hashrate weights are floats, and they are cast to `int` in exactly two
functions, `_draw_sats` and `_fee_rate`, both of which clamp to their configured floor. After
that no float touches money: the fee is `fee_rate * vsize`, both integers, and `inputs ==
outputs + fee` is an exact integer identity the tests assert with no tolerance.

When change falls below `dust_threshold_sats` there is no change output and the remainder goes
to the miner as fee. That keeps the identity exact rather than creating an unspendable output.

## 2026-09-04 · S01 · two knobs that are sampling density, not physics

`chain.coin_select_window` (new at S01) bounds coin selection to the oldest N spendable UTXOs
per entity. Without it an exchange with thousands of coins turns selection into a full scan on
every payment. It is a performance bound with a behavioural side effect — selection is
oldest-first — so it lives in the config where it can be measured, not in the code.

`chain.txs_per_block` and `chain.min_blocks` decide how many blocks hold `n_txs`, floored so a
small test run still has a real timeline. Thirty transactions per block is not a claim about
real blocks; it is the density that gives coinbase maturity something to mature over at test
size. Both are read from `run_config.json` and neither has a default in code.

## 2026-09-04 · S01 · config keys the chain layer does not consume

`run_config.json` carries `network` (with `india_weight`), `adversary` (with
`illicit_tx_share`), `export` and `target_rows`, and S01 reads none of them for behaviour. They
belong to S02 and later, and they are left in the file rather than moved, because the file is
one world description and splitting it per stage would mean two files to keep consistent.

`target_rows` is the one to watch: `--txs` defaults to `target_rows //
mean_announcements_per_tx`, since the operator thinks in capture rows and one transaction
becomes about nine rows once S02 attaches announcements. The effective config written beside a
run leaves `target_rows` untouched — rewriting it would erase what the operator asked for.



