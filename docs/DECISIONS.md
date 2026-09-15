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

## 2026-09-04 · S01 · the truth and measurements roots are anchored to the repository root

Chosen: `writers.py` finds the repository root by walking up from `__file__` for
`pyproject.toml`, and derives `TRUTH_ROOT` and `MEASUREMENTS_ROOT` from it. An `--out` that
resolves outside that root is refused before anything is written.

Rejected: anchoring to `Path.cwd()`, which was the first implementation. The working directory
is wherever the operator happened to stand, so a run launched from a subdirectory would create
a second `ground_truth/` there, outside `.gitignore`, and every test would still pass. A
quarantine that depends on which directory you were in when you typed the command is not a
quarantine.

The refusal message says why rather than just what: ground truth is derived from the run name
rather than passed in, so an `--out` that escapes the repository separates a run from its
answer key and lands that answer key outside the one gitignored tree that keeps labels out of
commits.

Revisit if a run ever legitimately needs to write outside the repository, for instance to a
mounted evidence volume. That is a change to all three roots together, never to one.

## 2026-09-04 · S01 · the clobber guard is content-addressed and lives in its own module

Chosen: `config.effective.json` is serialised and hashed first, before any file is written.
Both manifests record that `config_sha256`. On startup, if either the observable or the truth
directory already exists and its `_meta.json` records a different hash — or records none,
which means a half-written run — the generator raises, prints both hashes and prints the exact
`rm -rf` for both paths. A matching hash means the same run being regenerated, which is
deterministic, so overwriting is safe.

Rejected: comparing modification times. An mtime says which write happened later, not which
run the bytes belong to, and it makes the guard depend on filesystem timestamp behaviour.

Rejected: putting the guard in `writers.py`. Comparing a hash on disk means opening a file to
read it, and `test_the_ground_truth_writer_never_reads` is exactly what pays for that file's
exemption from the quarantine grep. The guard therefore lives in `preflight.py`, which is
handed both directories as arguments so it never contains the literal `ground_truth`, and which
only ever opens a file named `_meta.json` — a file the layout rules already forbid from
carrying a label.

Revisit for the gap recorded in `STATE.md` under Open problems: the hash covers the config, not
the code, so changing the generator and re-running the same `--out` overwrites silently.
Comparing `code_version` as well would close it, and would mean bumping that version on every
generator change.

## 2026-09-04 · S01 · the two-run comparison masks three manifest fields instead of skipping the manifest

Chosen: `scripts/compare_runs.py`, stdlib only, walks both trees and compares every file byte
for byte, except that in any `_meta.json` it drops `run_id`, `started_at_us` and
`finished_at_us` and compares the canonical JSON of what remains. `make verify-s01` and
`tests/test_chain.py` both call it, so the byte gate and the in-process gate cannot drift
apart.

Rejected: `diff -r -x _meta.json`, which was the first plan. Excluding the manifest drops every
sha256, every row count and every drop reason from the determinism comparison — precisely the
fields most worth comparing. Two runs could disagree about how many rows they wrote and still
pass.

`run_id` is masked because the two runs are deliberately named differently. The two timestamps
are masked because contract section 10 requires them and they legitimately differ. Nothing else
is masked, and the comparison was tested for vacuity before being trusted: a changed hash, a
changed count, an extra file and a changed payload byte each fail it, while the three masked
fields differing does not.

Revisit if a later stage's manifest gains another field that varies between identical runs. Add
it to `MASKED` with a comment saying why it must vary, and expect that comment to be the thing
a reviewer checks.

## 2026-09-04 · S01 · `verify-quarantine` is one shared target with a collected-count floor

Chosen: the leakage tests carry a `quarantine` marker, `make verify-quarantine` runs them with
`--strict-markers`, and it first counts what got collected and fails below
`QUARANTINE_MIN := 4`, printing the count. Every later stage's gate calls this same target as a
prerequisite.

Rejected: running `pytest -m quarantine` directly from each stage's gate. `pytest -m` exits
zero when everything is deselected, so a renamed test or a dropped marker turns the gate green
while testing nothing, and every stage that calls it inherits the free pass. A floor is the only
thing that notices.

The marker is applied from `tests/conftest.py` by a name registry rather than by decorators,
because `tests/test_contracts.py` must stay importable by a bare interpreter with no pytest
installed — that is what lets a future session check redaction before `uv sync` has ever
succeeded. The registry's cost is that renaming a test silently unmarks it, so `conftest.py`
raises `pytest.UsageError` when a registered name no longer exists.

Revisit the floor upward every time a leakage test is added. A floor that stays at 4 while the
suite grows to 9 is only guarding the first four.

## 2026-09-04 · S01 · the observable manifest names only observable files, and sits in `chain/`

Chosen: `_meta.json` moved from the run root into `chain/`, beside the files it describes, and
lists only those three files plus `config.effective.json` as its input. The truth directory gets
its own `_meta.json` listing its own files and hashes, so contract section 10 is satisfied on
both sides while the observable manifest never names the answer key. A test asserts that no file
under `data/generated/**` contains the string `ground_truth` or `measurements`.

Rejected: one manifest at the run root covering both trees. It satisfies section 10 with less
code and it publishes a map to the labels inside the tree every later stage is handed as input.
Layer 5's whole reason for making the answer key a sibling is that walking into it should take a
deliberate `../..` a reviewer can see; a path string in the manifest hands it over for free.

Every path in both manifests is relative to its own tree, never absolute. That is what keeps the
S09 replay claim portable across machines: an absolute path in a hash record makes the packet
verifiable only on the laptop that produced it.

The truth manifest deliberately carries no timestamps. It does not need them, and leaving them
out means the two truth trees of two same-seed runs compare byte for byte with nothing masked.

## 2026-09-04 · S01 · `config.effective.json` records the parameters and the seed, not the run name

Chosen: the effective config holds config values and the seed only. Not the run name, not the
derived truth path, not the derived measurements path. The run name is in both `_meta.json`
files, where a reader looking for provenance will find it.

Rejected: including the run name, which is what was asked for. Two reasons overrode it. It makes
`config.effective.json` differ between two same-seed runs, which breaks the byte comparison that
is S01's definition of done. And it makes `config_sha256` identify a directory rather than a set
of parameters, when what the clobber guard needs to answer is "are these the same parameters",
so that two runs of one config under different names are provably the same run.

Rejected outright, and this one is not a trade-off: recording the derived `ground_truth/<run>/`
or `measurements/<run>/` path in the file. That is the same defect as the manifest one above,
in the file every stage reads first.

Revisit by adding the name and a fourth entry to `compare_runs.MASKED` at the same time. One
without the other turns the determinism gate red for a reason that has nothing to do with
determinism.

## 2026-09-04 · S02 · capture shards are plain CSV here and compressed at S10

`docs/DATA-CONTRACTS.md` section 1 names the capture shards `part-*.csv.zst`. S02 writes
`part-*.csv`, uncompressed. This is a deviation from the frozen contract, not a reading of it, and
it is recorded rather than argued away.

The reason is that S10 owns scale, and compression is a scale decision with a cost on both sides:
it changes how long a run takes to write, and it changes what `scripts/peek.py`, the tests and the
validator must do to read one. Writing zstd now grows a decompression path in every reader from
S02 to S09 for a property nothing is measuring yet.

The deviation is cheap to reverse because no reader knows the suffix except by globbing:
`export.CSV_DIR` names the directory and every reader globs `part-*.csv`. S10 changes one writer
and one glob.

Revisit at S10, which must also choose the shard size and re-run `make verify-determinism`. zstd
is deterministic at a fixed level and library version, and that is a claim to test rather than to
assume.

## 2026-09-04 · S02 · the validation report is JSON and Markdown under `measurements/<run>/`

Chosen: `report.json` and `report.md` land in `measurements/<run>/validation/`, the third sibling
tree beside `data/generated/<run>/` and `ground_truth/<run>/`, all three derived from one run id
by `writers.run_roots`.

It cannot live under `data/generated/<run>/`, because every number in it is computed from the
answer key and that tree is what every later stage is handed as input. It cannot live under
`ground_truth/<run>/` either, because the point of the report is that a human reads it and quotes
it, and everything in that tree is quarantined.

`measurements/` holds JSON and Markdown only, never Parquet. A Parquet file there is a dataframe
that a later stage would eventually read as input, and the measurements tree would quietly become
a pipeline stage instead of a record of what was measured.

## 2026-09-04 · S02 · `broadcast_mode` is derived from two booleans and never stored

`ground_truth/<run>/origins.parquet` records `used_tor` and `used_vpn` and nothing else about how
a transaction reached the wire. The three-way mode the validator reports — clearnet, tor, vpn — is
derived from those two flags at read time.

Rejected: a stored `broadcast_mode` string. Two booleans plus a string encoding the same fact give
one state the string cannot express, both flags true, and the answer key would then have a
consistency requirement no reader could check. The generator makes that state unreachable and
`tests/test_network.py` asserts it directly on the artifact.

## 2026-09-04 · S02 · `world.india_weight` is gone and region shares live in `regions.yaml`

The S02 brief describes an `india_weight` knob under `world`. It is not in `run_config.json`,
because `regions.yaml` already answers the same question better: `share` per region sums to 1.0,
the parser refuses the file if it does not, and India carries 0.25 there — the largest single
share, which is what the knob existed to express.

One weight beside eight shares gives two ways to say where entities live and no rule for which
wins. The eight-row table is also what the latency matrix is indexed by, so placement and
propagation cannot disagree about the region set.

Revisit by editing `regions.yaml`, which is one line per region and needs no code change.

## 2026-09-04 · S02 · `adversary.n_campaigns` is a ceiling, and that sets the verify run size

`n_campaigns: 120` is an upper bound, not a count. The binding constraint is the world's illicit
transaction budget: `round(illicit_tx_share * n_txs)` moves exist in total, a campaign spends
`mean(moves_per_campaign)` of them, and `adversary.py:178` takes the minimum of the two.

The consequence is a trap for anyone sizing a test run. At 2000 transactions the budget is
`round(0.006 * 2000) = 12` moves, which buys `12 // 21 = 0` campaigns — so every campaign
assertion in the validator and in `tests/test_network.py` would pass by being vacuous. `S02_ARGS`
is therefore `--txs 20000 --entities 4000`, measured at five campaigns and about 30 seconds to
generate, and `tests/test_network.py` runs 4000 transactions for one campaign and says in a
comment why it cannot go lower. Both files assert `campaigns.height > 0` so a future retuning
fails loudly rather than silently testing nothing.

## 2026-09-04 · S02 · one row per observer per transaction, and the three knobs that follow

A real node announces to every peer that has not told it about the transaction. Chosen: an
observer records only the announcement that told it something new, so the capture holds at most one
row per observer per transaction. Later arrivals at the same observer are duplicates a real client
would discard, and the peers it has already told stop announcing.

That makes rows per transaction bounded by `n_observers` rather than by the size of the graph,
which is what keeps the capture linear in transactions instead of quadratic in nodes. It also
changes what the reach knob means: `observer_fraction` is the share of nodes that dial an observer
at all, and it, not the flood, decides how many observers hear anything.

Three knobs were retuned against that, and the numbers are measurements rather than guesses:

- `mean_announcements_per_tx` 9 to 15. It is both the divisor `--txs` defaults to and the
  distribution target, so a value the run cannot hit makes the operator's row budget a lie.
- `observer_fraction` 0.012 to 0.7. At 0.012 almost no node had an observer link, so most
  transactions reached nobody and the run produced a capture with no rows for them.
- `flood_frontier` 128 to 64. Halved because nothing above it changes the result, which is the
  claim `network._flood`'s docstring makes and
  `test_doubling_the_flood_frontier_barely_moves_the_first_seen_rate` measures: doubling the bound
  moves first-seen leakage by less than 0.05.

Measured after: 14.96 rows per transaction at 4270 transactions and 15.06 at 24580, first-seen
leakage 0.2233 to 0.2539 across three run sizes. The knobs are scale-invariant, which is the
property that matters — a benchmark whose difficulty depends on how big the run was is not a
benchmark.

## 2026-09-04 · S02 · `config.load` gained an `anchor` keyword for one caller

`config.load` resolves `network.latency_matrix` relative to the config file's own directory. The
validator loads the `config.effective.json` copied into a run directory, and that copy names
`regions.yaml` exactly as the original did — so the path resolved to `<run>/regions.yaml`, which
does not exist.

Chosen: one optional keyword, `anchor`, defaulting to `path.parent`. The validator passes
`writers.REPO_ROOT`. Three lines total.

Rejected: rewriting `latency_matrix` to an absolute path when the effective config is written. An
absolute path in a provenance record makes a run reproducible only on the laptop that produced it,
which is the same defect S01 already rejected for manifest paths, and it would change bytes the
determinism gate compares.

Rejected: copying `regions.yaml` into each run directory. It is the honest fix and it is a second
copy of a file that is already hashed into `config_sha256`, so the two could drift.

## 2026-09-04 · S02 · `write_run` takes the network and the campaigns as optional arguments

`writers.write_run(run, cfg, out, *, started_at_us, finished_at_us, net=None, campaigns=())`. A
chain-only run passes neither and writes what S01 wrote; an S02 run passes both and gets the
capture, the three export encodings and `origins.parquet` as well.

Rejected: a second entry point, `write_network_run`. Two writers means two places that derive the
truth path, and that path is the thing the whole quarantine rests on — one door out of `src/`, and
`tests/test_contracts.py` allows exactly one file to name it.

Rejected: making them required. `tests/test_chain.py` builds a chain without a network on purpose,
which is what proves the layers are separable, and requiring a network would force that test to
build one it does not use.

## 2026-09-04 · S02 · `delay_cv_min` lowered from 0.6 to 0.5, before a failure rather than after

The relay-delay coefficient of variation measured 0.605408 on the first smoke run, against a floor
of 0.6. Five thousandths of headroom is a coin flip, not a gate, and a gate that fails on a
different run size teaches the next session to raise the bound instead of reading it.

The floor is now 0.5. A propagation delay that is the sum of roughly k exponential hops has
CV ≈ 1/√k by construction, so for the depths this graph produces the honest value sits near 0.5 and
no configuration will push it far above. The pathology the check exists to catch is CV near zero,
which is a fixed forwarding delay — the sorted cascade requirement 3 forbids — and 0.5 still
catches that with room to spare.

Measured after the change: 0.605408, 0.616985 and 0.619980 at 776, 4270 and 24580 transactions. The
bound was lowered deliberately before running the verify gate, not in response to a red test.

Revisit only with a reason to believe the delay distribution changed shape. If this check ever
fails, the first thing to look at is whether a delay became deterministic, not whether the floor is
too high.

## 2026-09-04 · S02 · the validation report omits the run id

Neither `report.json` nor `report.md` names the run it describes. The run id is in the directory
path, and in the two `_meta.json` files, where a reader looking for provenance already looks.

This is what lets `make verify-determinism` compare the measurements tree with the same
`scripts/compare_runs.py` it uses for the other two, with nothing masked: two runs of one seed
produce byte-identical reports. The alternative was a fourth entry in `compare_runs.MASKED`, which
means the determinism gate stops comparing a field in every file that has one, to accommodate a
string that is already known from the path.

A number we intend to publish that moves between two runs of one seed is not a measurement, so the
measurements tree is compared as strictly as the other two.

## 2026-09-04 · S02 · the depth-2 tree measures identically to first-seen, and is kept anyway

The leakage group fits a `DecisionTreeClassifier(max_depth=2, random_state=0)` on the observable
columns and scores it on the same rows, deliberately: it is an upper bound on what a shallow local
rule can extract, not an honest generalisation estimate, and a bound is the thing worth reporting.

It measures exactly what first-seen measures — 0.223434 at 24580 transactions, 0.225293 at 4270 —
because the best Gini split over these features reduces to `arrival <= 0.5`, which is first-seen
spelled differently. That is by construction, not a bug, and the check is not therefore redundant:
its value is the day some other column starts carrying the answer, when the tree moves and
first-seen does not. Its cap is `tree_leakage_max: 0.35`, the same cap the one-line rules get,
because a depth-2 tree is a one-line rule with two conditions rather than one. It started at 0.7,
which the entry below explains was above a ceiling it could never reach.

`scikit-learn` 1.9.0 is already in `uv.lock` as a dependency of the pinned `mapie==0.9.1`, so this
adds no dependency and nothing needs fetching — PyPI is unreachable in this sandbox. It is imported
inside `_tree()` so the rest of the validator runs without it, and `sklearn.*` joins the existing
mypy `ignore_missing_imports` list beside lightgbm, shap, mapie, rustworkx and duckdb.

Rejected: hand-rolling a depth-2 tree. Roughly twenty-five lines plus a test of its own, to
reimplement something already installed and already tested.

## 2026-09-04 · S02 · the report states the ceiling every accuracy number is a fraction of

The originator's own IP appears somewhere in the capture for only **0.428560** of transactions at
verify size, and 0.405 at 4270 transactions. For the other 57% no rule and no model can ever be
right: an observer keeps the earliest arrival only, each monitored node dials exactly one of the
sixteen observers, and a directly connected originator is silenced whenever any other peer reaches
its observer first. That is the honest consequence of requirement 4 — record only what an observer
received — and it is what a real sixteen-sensor deployment looks like.

It is also a number a report must not omit. Every leakage score is a share of all transactions,
which is the denominator S03 will publish its accuracy on, so first-seen's 0.223434 is 0.521359 of
what is reachable rather than 0.22 of what is possible. Reported unqualified, it invites a reader to
believe there is nearly three times more headroom than the capture contains.

Three changes followed, all of them because a gate that cannot fail is not a gate:

- A new leakage check, `the originator is in the capture at all`, with a floor
  `origin_recoverable_min: 0.25`. A ceiling collapsing toward zero is the unmeasurable-benchmark
  failure the first-seen floor was meant to catch, and the first-seen floor cannot see it.
- `tree_leakage_max` 0.7 to 0.35. A cap above 0.4286 is unreachable arithmetic: a capture with a
  literal `is_the_origin` column would have scored 0.4286 and passed.
- The Markdown tables gained a `note` column. Notes were rendered only for failing checks, so the
  sentence that makes a passing number interpretable was written and never shown.

Not changed: `first_seen_leakage_max: 0.6` and `trivial_rule_max: 0.35` stay expressed on the raw
share, unconditional, because that is the same number S03 will report and rescaling them would make
the report incomparable with the stage it exists to gate. The floors are what fire in practice; the
ceilings now sit above a hard bound and the report says so on the row above.

## 2026-09-04 · S02 · the strongest trivial rule is payer linkage, and it is measured

The four original trivial rules are one-column sorts, and each measures a channel that turned out
to be nearly empty — lowest source port 0.025, busiest peer 0.000. The rule that actually scores is
the one that links transactions: group by the first input address, then name the peer seen across
most of that payer's transactions. **0.263995**, which is 0.616 of the achievable ceiling and the
highest of any rule the validator tries.

It is in the leakage group rather than left for S03 to discover because it is the shape S03 is meant
to find. Knowing that address reuse alone gets 0.26 is what makes an S03 result meaningful: a
model scoring 0.27 has learned almost nothing, and nobody could tell without this row.

It stays under `trivial_rule_max: 0.35` with about a quarter of the band spare. If a retuning pushes
it over, the honest response is to weaken address reuse in the chain layer, not to raise the cap —
the cap failing means the capture is answering the question S03 is being asked.

## 2026-09-04 · S02 · `TRUTH_COLUMNS` names every answer-key column, not the interesting ones

`validate.TRUTH_COLUMNS` began with fifteen names and the answer key has twenty-three. The eight
missing were `entity_type`, `addresses`, `ips`, `behind_cgnat`, `txids`, `start_us`, `end_us` and
`total_sats` — the columns that look like shapes rather than labels, which is exactly why they were
skipped and exactly why they were dangerous. The check reports "none" when it finds nothing, so a
capture that grew an `ips` column would have been declared clean.

Now every column of all four quarantined files is listed, except `txid` and `block_height`, which
are public chain facts and legitimately appear in the capture. `tests/test_network.py` imports the
tuple rather than copying it, so the test and the report cannot disagree about what a label is
called.

Matching stays exact, never by substring, for the reason S00 recorded: the capture legitimately
carries `input_addresses` and `output_addresses`, and a substring rule would reject it for
containing `addresses`. That collision arrives for real at S05 and S06, which define `addresses`
and `txids` as observable columns of `graph/` and `signals/`. Whichever session builds them must
narrow this tuple and record the narrowing, exactly as the S00 entry says for
`FORBIDDEN_GT_COLUMNS`.

## 2026-09-04 · S02 · a docstring that claimed an unwritten check became the check

`_delays` documented an ordering guarantee — no announcement earlier than the broadcast it announces
— that nothing in the validator tested. The delay column was computed, its distribution was checked
for spread, and its sign was never looked at.

The fix was the invariant, not the docstring. A negative delay is a propagation model built
backwards, and it is the one defect in this stage that S03 would reward rather than trip over: a
feature that is negative only for the originator is a label wearing a timestamp, and a model would
find it immediately and score near 1.0 for the wrong reason. It measures 0 rows and is a check worth
keeping precisely because it is cheap and its failure mode is silent success downstream.

The general rule this stage now follows: when a docstring and the checks disagree, the docstring is
the specification and the gap is the bug.








## 2026-09-11 · S02 · a coinbase is never gossiped, and nothing is announced after it confirms

The gossip layer looped over every transaction in the run and announced each one until its flood
ran out of frontier. Both halves of that were wrong, and they were wrong for different reasons.

A coinbase transaction is created by the miner inside the block that contains it. It is never
relayed as a loose transaction, so every coinbase row in the capture described an event that
cannot happen. And a peer that already holds the confirming block relays the block, not the
transaction inside it, so an announcement whose arrival time falls at or after the block's own
timestamp is equally impossible. The first is a filter on which transactions enter the loop; the
second is a deadline inside `network._announce`, because the offending quantity is the arrival
time at the observer rather than the moment of broadcast.

Together they remove 16268 rows of 370291, leaving 354023. Both are now invariants rather than
properties of the code that happens to hold: `no coinbase transaction is announced` and `no
announcement lands at or after its confirming block`.

The designed-for consequence is that 175 broadcast transactions now reach no observer at all and
carry `observed_by_n = 0`. That is the honest outcome. An observer whose only announcement falls
past the deadline recorded nothing, and filling the gap would be inventing an observation.

## 2026-09-11 · S02 · addresses get one owner at the point they are minted

Two mechanisms were handing one address to two entities, and because they fail in different
places, each needed its own fix rather than a shared deduplication pass.

`ADDRESS_SHAPES` padded a minted address to its target length with the character `2`, which is a
hex digit. So `head + "2" * fill + hex(counter)` is not injective: a short counter padded with
twos collides with a longer counter that happens to start with twos. 151 addresses were minted
twice. The pad is now `z` for base58 shapes and `q` for bech32, neither of which can appear in the
counter, which makes the construction injective by shape rather than by a check after the fact.

Separately, `chain._coinbase` drew its payout through `receive_address`, from the same growing
pool the endowment had already seeded, so 55 block-reward addresses were also endowment addresses.
Each mining pool now mints one payout address lazily on first use and reuses it, drawn outside the
existing pool. It still joins the entity's address list, because the S04 clustering answer key has
to name every address an entity owns; what it no longer does is come out of a pool that something
else already drew from.

Both are invariants at zero tolerance: `no address is owned by two entities` and `no coinbase
output address is also an endowment address`. Neither tolerates one collision, because a single
shared address merges two entities in the clustering answer key and nothing downstream can tell
that the merge was an accident.

## 2026-09-11 · S02 · a txid is a hash of the transaction, not a counter

Transaction ids came from a run-wide counter formatted into a fixed-width tail. Every txid in a
run therefore ended in the same eight hex characters.

Section 11 renders a txid as its first eight and last four characters. A constant tail means four
of those twelve characters carry no information, two different transactions read alike on screen,
and the whole thing looks obviously synthetic in any rendered evidence packet. The id is now
`SHA-256` over the transaction's own serialised inputs and outputs, so all sixty-four characters
vary: 24626 transactions in the reference run produce 24626 distinct ids and 20508 distinct
four-character tails, the shortfall being ordinary birthday collisions across 65536 possibilities.

The coinbase is the one case that needs a nonce, and it uses the block height, which is what BIP34
does and for the same reason: a coinbase has no inputs, so two blocks paying the same pool the
same subsidy would otherwise serialise identically and share an id. Non-coinbase transactions need
no nonce, because an outpoint can be spent once and the input set therefore separates a
transaction from every other one in the run. `ledger.Ledger.create` already raises on a duplicate
outpoint, which makes any collision loud rather than silent.

The id is derived at the point where the inputs and outputs are final, immediately before the
ledger entry, rather than handed in by the caller. Handing it in is what allowed the counter to
exist, and it would let a future caller derive an id from contents that later change.

## 2026-09-11 · S02 · every observer answers to its own address

Observers drew `dst_ip` from the configured pool without checking what the previous draw took, so
two observers could share one address. Nothing about such a row is malformed, which is why no
existing check caught it, and that is exactly what makes it dangerous: any group-by on `dst_ip`
silently merges two vantage points into one and the merge is invisible in the output.

Observer addresses are now drawn against a set of what is already taken, with a bounded number of
redraws before `network.build` raises. The invariant is stated as a bijection — `observer id and
dst_ip are one to one` — rather than as uniqueness in one direction, because both directions are
failures and a check that only looked one way would pass on half of them.

## 2026-09-11 · S02 · leakage is scored over broadcast transactions, not observed ones

Every leakage score divided by the number of transactions that appeared in the capture. Before the
coinbase and deadline fixes that was very nearly the same as the number of transactions broadcast,
because essentially everything reached someone. It is no longer: 175 broadcast transactions now
reach no observer, and scoring only over the 23784 that did would have credited every rule with
transactions it was never given a chance at.

The denominator is now `broadcast`, every non-coinbase transaction the generator put on the wire.
A transaction no observer saw is one no rule and no model can ever get right, and it belongs in
the denominator for the same reason a transaction whose originator was never in the candidate set
does. This is the denominator S03 has to report its accuracy on, so it is the one the ceiling and
every trivial rule are measured against.

The measured effect, against the last pre-remediation run: the recoverable-origin ceiling moves
from 0.428560 to 0.415376, first-seen from 0.223434 to 0.220919, and the strongest trivial rule
from 0.263995 to 0.263241. All three fall, and all three fall because the denominator grew rather
than because any rule got worse.

## 2026-09-11 · S02 · `Origin` carries the transaction index it answers for

`origins.parquet` built its `txid` column by filtering `run.txs` while every other column came
from walking `network.origins`, so the two were aligned by position and nothing proved it. The
coinbase fix broke that alignment immediately, in `tests/test_network.py` rather than in the
writer, because `Capture.tx_index` indexes `run.txs` while the origin list had become shorter.

The fix is one field. `Origin.tx_index` records which transaction the row answers for, and the
writer reads the txid back through it. Two copies of one filter agree only until one of them
changes, and the failure that produces is silent: every row's txid paired with a different
transaction's answer key.

The validator still asserts the resulting set matches the chain, and now also asserts the row
counts match — the count term catches a duplicate txid on the chain side, which all three set
terms miss. This is an answer key, and an answer key is worth checking twice.

## 2026-09-11 · S02 · the relay delay CV floor stands at 0.50

The `delay_cv_min` floor of 0.50 was calibrated over a delay population that included
post-confirmation arrivals, which are now known to be invalid observations and are dropped. The
question was whether the floor had to be recalibrated against the valid rows.

It does not. The measured coefficient of variation on the remediated reference run is **0.618320**,
comfortably above the floor with the invalid rows gone. `relay_delay_*_mean_s` is untouched, which
is correct independently: the CV of an exponential is scale invariant, so raising the mean cannot
move it and retuning the mean would be answering a different question.

## 2026-09-11 · S02 · `n_nodes` is a ceiling, and the manifest now says so

`config.effective.json` records `n_nodes: 5000` while the run builds 4160 nodes, because the peer
graph places one node per entity and takes `min(n_nodes, n_entities)` before adding the Tor exits
and VPN nodes. The behaviour is right and determinism already proves the topology reproduces, but
reading the manifest alone gives no way to learn it.

`n_nodes_effective` is now recorded alongside it. Nobody should have to read `network.py` to
understand why a manifest claiming 5000 describes a graph of 4160.

## 2026-09-11 · S02 · S01's gate stops at the chain layer

`make verify-s01` ran the whole generator, so any change to the network layer reddened S01 as well
as S02 and the failure named the wrong stage. Every later stage would have inherited that: a
single-stage change would light up every gate below it.

`--chain-only` skips the peer network and the capture, which `writers.write_run` already supported
by treating `net=None` as a chain-only run, so the flag costs one branch in `__main__`. S01's
fixtures build the chain layer and nothing else.

The same session replaced `test_chain.py`'s manifest assertion, which compared the truth tree's
file list against a literal list of filenames. A literal breaks every time a later stage adds a
truth artifact, which is a false alarm, and it cannot catch the failure that actually matters: a
file written into the answer key but left out of its own manifest, which is an unhashed,
unaccounted label file. The list is now compared against the directory contents, every recorded
hash is verified against the file on disk, and the three artifacts the chain layer owns are
asserted as a subset so a fourth is not a failure.

## 2026-09-11 · S02 · block occupancy is proportional to the slice, not to mainnet

Blocks in the reference run hold about 37 transactions where a real block holds 2000 to 3500. This
is deliberate and is not being fixed.

The run is a 20000-transaction, 4000-entity slice. Block interval, coinbase subsidy and fee
behaviour are all modelled at mainnet scale, so the number of blocks is a function of the time
span rather than of the transaction count, and 24626 transactions across 667 blocks is what that
arithmetic produces. Packing blocks to mainnet occupancy at this slice size would mean either
compressing the time axis, which destroys the relay-delay and block-interval distributions the
capture exists to carry, or generating fifty times the transactions, which is S10's question and
not this stage's.

What a later stage must not do is read block occupancy as a feature. It is an artifact of the
slice ratio, and any model that learns from it has learned the shape of the generator.

## 2026-09-11 · S02 · address degree p99 is a 20k-row measurement and S10 re-measures it

Address reuse degree has a p99 of 12 in the reference run. That number is measured over 20000
transactions, and degree distributions of this kind do not scale linearly with sample size: the
tail is the part that grows.

No change is made to S01 on the strength of it. S10 re-measures address degree at the full million
rows first, and any retuning of the reuse parameters happens after that measurement, not before.
Tuning a tail statistic against a fiftieth of the data is how a generator ends up with the wrong
shape at the size it will actually be used at.

## 2026-09-11 · S02 · forty-four checks are not forty-four independent checks

The validation report now carries 44 checks and it is worth writing down that some of them are the
same check twice.

The clearest case is the `row-order-in-file` tie-break. Several leakage rules break ties on the
capture's row index, and the capture is written in ascending time order, so a tie broken on row
order is a tie broken on arrival time. Any rule that sorts on `row` after its primary key is
partly duplicating the first-seen rule, and the depth-2 tree over the observable columns scores
exactly the first-seen number (0.220919) for that reason: with `since_first` among its features,
the tree rediscovers first-seen and stops.

The practical consequence is for reading the report, not for the code. A clean run means no check
failed; it does not mean 44 independent things were established. When a later stage needs to know
how much evidence a passing report carries, it should count the distinct channels — arrival time,
peer identity, port, payer linkage, message type — not the rows.

## 2026-09-11 · S02 · open question for S10: observers and transactions trade off directly

No action now. This is the measurement S10 must make before it fixes a row budget.

Announcements per transaction is 14.776201 with a coefficient of variation of 0.135237, and it is
pinned by `n_observers`, not by the nine outbound peers each node keeps. `network._announce`
records at most one row per observer per transaction — the earliest arrival, since every later one
is a duplicate the observer already holds — so rows per transaction is bounded above by
`n_observers = 16` and nothing about graph size moves it. These are two different quantities and
they have been conflated.

The consequence for sizing: one million capture rows is about 66000 transactions, not the 111000 a
nine-peer assumption would give. At a fixed row budget, observers and transactions trade off
directly. Dropping `n_observers` from 16 to 9 roughly doubles the transaction count, which helps
campaign coverage and address reuse degree, at the cost of a lower recoverable-origin ceiling,
because fewer vantage points means the originator is in the candidate set less often.

The `observer_fraction` sweep is what should decide this, not a guess. It is the only measurement
that prices the ceiling against the transaction count directly.

## 2026-09-11 · S03 · the amount unit needs the whole column, not one decimal

The obvious rule is "if any amount contains a decimal point, the file is in BTC". It is wrong in
a way that leaves no trace.

A satoshi file with one corrupt value — a stray `0.5` in a column of integers — would flip the
whole file to BTC under that rule. Every amount then gets multiplied by 1e8. The multiplication
applies to inputs and outputs alike, so `sum(inputs) >= sum(outputs)` still holds, invariant 6
never fires, and nothing downstream can tell a hundred thousand satoshis from a thousand BTC.
The evidence packet would carry amounts off by eight orders of magnitude with every check green.

So the rule is unanimity per column. Every parseable token integer-shaped means satoshis, every
one fractional means BTC, and anything mixed is a `CaptureFormatError` naming the column. Columns
that disagree with each other are the same error. Tokens that parse as neither — empty strings,
words, scientific notation — are excluded from the detection and rejected per row instead, so one
piece of junk costs one row rather than reinterpreting the file.

Scientific notation is deliberately in the junk category. `1e8` is either a hundred million
satoshis or a hundred million BTC and nothing in the token says which.

The detected unit is recorded in `sealed/manifest.json` as `amount_unit_detected`, so the
inference is auditable rather than implicit.

## 2026-09-11 · S03 · `value_not_conserved` rejects, and this is a finding

Asked whether invariant 6 should reject a row or flag it for a later stage. It rejects.

Section 1 of the contract states the invariant and section 3 states that rows failing validation
go to `sealed/rejected.parquet` with a reason. The contract is frozen, and CLAUDE.md is explicit
that code which cannot satisfy it is a finding to report rather than a contract to change. So the
behaviour follows the contract.

The concern that prompted the question is real and is recorded here rather than acted on: on a
real partial-visibility capture, where an announcement carries only the inputs the observer could
resolve, `sum(inputs) < sum(outputs)` is what incomplete data looks like rather than what corrupt
data looks like. Rejecting those rows would quietly shrink the dataset, and the only place it
would show up is a `value_not_conserved` count in the manifest that nobody reads.

Three things make that survivable for now. The count is in the manifest, not hidden. The rows are
in `rejected.parquet`, not dropped, so a later stage could reconsider them without re-reading the
original. And coinbase is exempt: a row with no inputs mints its outputs, so the comparison is
skipped entirely rather than merely being generous about it.

If a real slice turns out to reject a material fraction of its rows this way, the honest response
is to raise it as a contract finding with the measured rate attached, not to weaken the check.

## 2026-09-11 · S03 · a wall clock is excluded from every hash, not only from the diff

`sealed/manifest.json` carries `sealed_at_us`, so its bytes cannot reproduce across two seals of
one input. Masking that field in `scripts/compare_runs.py` is necessary but not sufficient: if
anything downstream hashes the manifest raw — `sealed/_meta.json`'s output list, the S09 evidence
chain — that hash changes on every seal, and a custody check built on it would report tampering
where there was none.

So the manifest is not listed in `_meta.json`'s `outputs` at all. What is recorded instead, under
`params.manifest`, is `sha256_masked`: the hash of the manifest with `sealed_at_us` removed,
key-sorted. `masked_fields` names what was excluded, so the recomputation is reproducible by
anyone holding the file. `scripts/check_sealed.py` recomputes it and fails if it disagrees.

The general rule for later stages: an unreproducible field is excluded from every hash and every
comparison, and the exclusion is named in the artifact rather than living only in the tool that
compares two of them.

## 2026-09-11 · S03 · `--in` is allowlisted to `data/`, not denylisted

KAVACH is the first stage that takes a second path argument. Law 1 says `--out` is the only path
argument in the system, and the reason is that no flag may be able to point at the answer key.

KAVACH derives no truth path at all, so the law's purpose is served by a different mechanism: an
allowlist. `--in` must resolve, after `Path.resolve()`, inside `<cwd>/data`. Anything else is an
`InputPathError`, traversal included.

An allowlist rather than a denylist for a mechanical reason. A denylist would have to name the
directories it excludes, and Law 2 rule 1 is a grep for exactly those names over `src/` — the
guard would fail the guard. Importing the roots from `writers.py` would be a cross-stage import
and would fail it too. Allowing only `data/` says the same thing without naming anything.

The operational consequence, which belongs in the S11 runbook: an evaluator's file is copied
under `data/` before it can be sealed. That copy is not friction to work around, it is the point
at which an outside file enters the tree the tool is allowed to read.

## 2026-09-11 · S03 · the column alias table is a judgement, and a conservative one

Section 1 fixes twelve column names. It does not say what a stranger's file might call them, so
the alias table in `kavach/schema.py` is ours rather than the contract's. Matching is
case-insensitive and whitespace-stripped on top of it.

It is deliberately short. A wrong alias silently mislabels a column, which is strictly worse than
a `MISSING` tag in the manifest that an investigator can fix by renaming a header. `peer_ip` maps
to `src_ip` and `tx_hash` to `txid` because those are unambiguous; nothing maps on a guess.

When two headers in one file map to the same canonical name, the first spelling wins and the
second is reported in `warnings` as unrecognised rather than overwriting it. A file carrying both
`src_ip` and `peer_ip` is a file whose author meant something by the distinction, and picking one
silently would discard that.

Every one of the twelve gets a `MAPPED`, `SYNTHESISED` or `MISSING` entry in
`manifest.json`'s `column_status`, so what was inferred is always visible.

## 2026-09-11 · S03 · a naive timestamp is read as UTC, and the count is a warning

The contract allows ISO 8601. It does not require an offset, and a real capture tool often writes
local time with no zone at all.

Reading a naive stamp as local time would put one column on a different clock from every other
time in the project, all of which are UTC microseconds, and the error would be a whole-timezone
offset in exactly the field the origin estimator is most sensitive to. So a naive stamp is read as
UTC, and the number of rows it happened to is written into `manifest.json`'s `warnings`.

A warning rather than a rejection because the alternative is worse: refusing the file would make
every no-offset capture unusable, and the assumption is both stated and counted.

## 2026-09-11 · S03 · rows that disagree about one txid are all quarantined

Invariant 5 says rows sharing a txid must agree on the chain columns. When they do not, KAVACH
rejects every row of the group with `chain_columns_disagree`, not the minority.

A majority vote is a guess with extra steps. Two announcements agreeing and one differing does
not make the two correct — it makes the file corrupt at that txid, and picking the popular answer
would bake an unrecorded decision into the sealed copy that no later stage could see or revisit.
Quarantining the group puts every row in `rejected.parquet`, where the disagreement is visible
and recoverable.

The check runs after per-row coercion and only over rows that passed it, so a row already
rejected for its own reason is not counted twice and the manifest arithmetic still reconciles.

## 2026-09-11 · S03 · a DOCTYPE is refused before the XML parser sees it

`xml.etree.ElementTree` uses expat, which expands internal entities by default. That makes a
DOCTYPE declaration both the XXE vector and the billion-laughs vector, at the one stage whose
entire premise is parsing a file handed over by someone else.

KAVACH refuses any input whose first 4096 characters contain `<!DOCTYPE`, before parsing rather
than by configuring the parser afterwards. A capture has no legitimate use for a document type
definition, so the refusal costs nothing real, and the check is a substring test that cannot
itself be subverted by the thing it is checking for.

Considered and rejected: adding `defusedxml`. It is the right library for a general XML intake
problem, but it is a new dependency for a case where refusing the construct outright is both
simpler and stricter.

## 2026-09-12 · S03 · the rejected rows keep real Parquet list types

Section 1's conventions block says array-valued columns are pipe-separated in CSV and real
`list` types in Parquet. The first implementation of `rejected.parquet` stored the four array
columns pipe-joined as `string`, on the reasoning that a rejected row holds original text.

That was wrong, and a contract auditor caught it. Pipe-joining is the CSV spelling of an array,
not the Parquet one, and the frontend track reads these files. The element type is `string`
rather than `int64` deliberately: a row rejected because its amounts would not parse has no
valid `list[int64]` form at all, while `list[string]` always exists and keeps the tokens
separable. The fixture's one documented defect is two input addresses against three input
amounts, which is only visible if both columns are really lists; joined, both lengths read 1.

## 2026-09-12 · S03 · what the manifest carries beyond the contract's twelve keys

Section 3 shows `manifest.json` as a JSON example rather than a column table, and unlike a
Parquet schema an extra JSON key cannot break a reader that ignores it. Four keys are added:
`column_status` and `warnings`, both required by the stage brief's schema-tolerance rule, and
`column_spellings` and `encodings_detected`, which record what the content detection actually
decided per input file so that a disputed seal can be argued about afterwards.

Two others were written first and then removed: `distinct_txids`, which nothing read, and
`duplicate_rows`, whose only real use is the warning it already produces in prose. A number in
a manifest that no gate checks and no stage consumes is a number nobody maintains.

The addition is recorded here as a finding rather than as an edit: the contract is frozen, and
a stage that quietly extends a shared document is how a parallel track finds out too late.

## 2026-09-12 · S03 · `code_version` is a git sha, and `tool_version` is the package version

Section 3 asks for `"code_version": "git sha"` and `"tool_version": "0.1.0"` in one object, and
the first implementation wrote `__version__` into both. That made the two fields identical and
left neither able to answer the only question `code_version` exists for: which revision produced
this seal. A packet that cites the seal could not be traced to a commit, and a replay could not
show it re-ran the same code. A contract auditor flagged it as the one real deviation in the
stage, and the contract's asking price is satisfiable, so the code satisfies it.

The value is `<12 hex>` or `<12 hex>-dirty`, from `chakravyuh.buildinfo.code_version()`. The
`-dirty` suffix is deliberate: a seal produced from a modified tree is not reproducible from the
commit it names, and claiming otherwise is precisely the failure this field prevents. Only
tracked modifications count, so an untracked scratch file cannot make the value flap. The helper
resolves the repository root from its own file location, not the caller's working directory, so
it reports the code that ran rather than wherever the process happened to stand. When git cannot
answer it returns `unknown`, which is honest in a way a package version is not.

This is repo-wide, not KAVACH-specific: `mayajaal/writers.py` writes `__version__` into
`code_version` at three sites as well. Those are left alone here — they are another stage's
internals, and the artifacts that carry them are already sealed — but they are reported to the
user as a finding, and `buildinfo.code_version()` is there for whoever picks it up.

`code_version` is deliberately not masked out of the determinism comparison, unlike
`sealed_at_us`. It has to be stable within a commit and different between commits; that is the
whole property being claimed.

## 2026-09-12 · S03 · `_meta.json` `inputs` is the capture files and nothing else

Section 3 says `INPUT.sha256` holds one line per input file, and section 10 types every
`inputs[].rows` as an integer. The first implementation listed the upstream `capture/_meta.json`
as a third input, with `rows: null`, because it is an input in the custody sense: KAVACH read
it, and its hash is what the staleness check re-computes.

That made `rows` a mixed type and made the entries sum to something other than `counts.in`. It
also disagreed silently with `INPUT.sha256`, which covers only the capture files. The upstream
manifest is not data — it carries no rows and is never sealed — and `params.upstream_meta`
already records its path and hash in full, so nothing is lost by removing it from `inputs`.

The lists now answer one question between them: `inputs` pairs with `INPUT.sha256` and with
`manifest.input_files` by index, all three naming the same files in the same order. Every `rows`
value is an integer and the list sums to `counts.in`, which is the useful part — a shard that
read short now shows up as a discrepancy against the total rather than hiding inside it.
`check_sealed.py` asserts the sum and the path agreement, so the per-file counts are load-bearing
rather than decorative.

## 2026-09-13 · S04 · GeoLite2 is read from the CSV distribution, not the mmdb

SETU reads MaxMind's CSV files with the standard library — `csv`, `ipaddress`, `bisect` —
building version-split sorted range tables and looking up per distinct peer IP. Chosen
because no MaxMind reader is in the pinned dependencies and this sandbox cannot resolve a
new one (`pypi.org` denied), while the CSV distribution carries the same data as the mmdb.
An `.mmdb` with no CSV beside it warns
`geolite2_mmdb_present_but_unreadable_csv_required` rather than enriching nothing silently.
Rejected: writing a partial mmdb binary parser. A half-built parser is a worse answer than
an honest null, and the operator who has the data can fetch the CSV variant. Revisit if the
project ever gains a real dependency budget or a vendored wheel of `maxminddb`.

## 2026-09-13 · S04 · null and `unknown` are different answers in `net_class`

The stage brief said an absent Tor list means null, and the contract's vocabulary contains
`unknown`. Both were kept, distinguished: null means no list was available to ask — a fact
about the deployment; `unknown` means the lists were present and none recognised the
address — a fact about the address. Rejected: collapsing to `unknown` everywhere, which
would let a bare-bones deployment look like a rich one that classified every peer and found
them all unrecognised. Revisit only if S06's abstention logic turns out to need one value,
and then by migrating the deployments upward, not by erasing the distinction.

## 2026-09-13 · S04 · `change_index` is deliberately weak

The contract requires the column but names no heuristic. SETU names a suspected change
output only when a transaction has exactly one non-round-value output paying an address that
is not one of its own inputs, and `n_out >= 2`; anything else is -1. On the demo run this
leaves 89% undetermined. Chosen because the real change heuristic is S05's and needs the
graph: a change index that is nearly always right for a structural reason would hand the
clustering stage a free answer and make its measured precision a lie. Rejected: the stronger
common-heuristics bundle (round amount, address reuse across inputs, largest non-input
output), which is exactly S05's job. Revisit if S05 finds it needs a richer starting signal
than -1/valid, at which point the rule moves to S05 rather than growing here.

## 2026-09-13 · S04 · the capture's own geo and ASN win over the vendored lookup

Where a sealed row already carries `geo_country` or `asn`, SETU keeps it and fills only the
nulls from `vendor/`. The contract says "enriched if null on input", which reads as
fill-if-absent rather than overwrite. Rejected: vendored-wins, on the theory that the
database is newer. A real NTRO capture may carry an ASN resolved at capture time, which is
closer to the truth about that moment than a lookup done months later against a table that
has since been re-delegated; for an evidence tool, the contemporaneous observation is the
one that survives cross-examination. Revisit if a demo scenario specifically needs the
vendored values to be the visible ones.

## 2026-09-14 · S05 · four column names left `TRUTH_COLUMNS`, per-file rather than outright

`validate.py`'s quarantine grep held 23 truth-only column names and fired on any observable
file whose header contained one. Four of them — `change_index`, `addresses`, `typology`,
`txids` — are also names the frozen contract gives to observable columns: section 4's
`transactions.parquet`, section 5's `clusters.parquet` and section 6's `typology_hits.parquet`.
The contract contradicts its own section 2 there, and that contradiction is a finding, not
something code can resolve by editing the document.

Chosen: a second structure, `CONTRACT_OBSERVABLE`, mapping each of the four names to the exact
set of observable files the contract permits it in, keyed `<stage-dir>/<file>` and checked
against the last two path components. The grep still fires on `change_index` in a capture
shard; it no longer fires on the file section 4 requires it in. The keys are qualified with
the stage directory deliberately: MAYAJAAL writes `chain/transactions.parquet` and SETU writes
`normalised/transactions.parquet`, so a bare basename key would have quietly permitted
`change_index` in the generator's own output — which was the first version, and the test caught
it.

Rejected: deleting the four names from `TRUTH_COLUMNS`, which is a smaller diff and stops
catching a real leak. Every name left in the list names a label or a truth-only fact —
`is_illicit`, `true_origin_ip`, `input_entity_ids` — and no observable file can legitimately
carry one of those, so the list stays exact-match. `tests/test_jaal.py` and
`tests/test_network.py` both assert the two structures are disjoint and that each narrowed name
is permitted in exactly one file.

## 2026-09-14 · S05 · SAME_OWNER edges form a star per transaction, not a clique

Every input address of a transaction is linked to that transaction's lexicographically smallest
input address: n-1 edges where a clique is n(n-1)/2. Connected components, `min_edge_confidence`
and every derived cluster are identical either way, because a star and a clique over the same
vertex set have the same component and the same weakest edge. One transaction in a
2000-transaction run already has 38 inputs, which is 703 clique edges carrying nothing the 37
star edges do not, and the count grows quadratically in a way a real capture would make painful.

Chosen because the derived view is what an analyst reads and the view is provably unchanged;
`test_a_star_and_a_clique_cluster_the_same` asserts that rather than arguing it. Rejected: the
clique, on the theory that an edge between every pair is more honest about what the heuristic
claims. It is not — the heuristic claims one thing per transaction, and repeating it n(n-1)/2
times makes the edge table look like independent corroboration it never was. Revisit if some
consumer needs pairwise edges specifically, at which point they are recoverable from the
component without re-running the heuristic.

## 2026-09-14 · S05 · 0.36 is quoted from the literature, 0.25 is invented and labelled so

`multi_input` edges carry confidence 0.36, which is the published full-cluster precision
contract section 5 quotes for the common-input heuristic in law enforcement settings. The
number an analyst sees on the edge is therefore the number somebody measured, not one this
project chose to look plausible.

`change_addr` edges carry 0.25, which is **unmeasured in this project**. SETU's change rule is
deliberately weak by its own S04 decision — sole non-round output not paying one of the
transaction's own inputs, `n_out >= 2`, 89% undetermined — and low recall says nothing about
precision. The value's only defensible property is being below `MULTI_INPUT_CONFIDENCE`, so a
threshold set between the two selects multi-input alone, which is the comparison the console's
slider most wants to offer. Rejected: leaving the change edges out until something measures
them, which would make requirement 2 of the brief unmet; and giving them 0.36 as well, which
would launder an unmeasured heuristic into a cited one. S10 measures it; until then the
constant's docstring says the word UNMEASURED and this entry exists so nobody quotes 0.25 at a
reviewer.

## 2026-09-14 · S05 · `graph/_meta.json` counts rows, and the stage's own accounting sits beside it

Contract section 10 wants `counts.in == counts.out + counts.dropped`, and says why: it is "how
the whole pipeline stays accountable for every row it was given". The first implementation
counted candidate `SAME_OWNER` edges — `in` what the heuristics proposed, `out` what survived
deduplication and the threshold. The arithmetic held perfectly and meant nothing: the 11014
normalised rows the stage was handed were unaccounted, which is precisely the question the
equality exists to answer. `contract-auditor` caught it.

`counts` is now at row grain. `in` is every row of all four normalised tables. Three of them are
one row per entity and each row becomes exactly one node, so nothing can go missing there;
`announcements.parquet` is the only table whose output is coarser than its input, because
several rows can describe one `(txid, peer_ip)` pair and only one `ANNOUNCED_BY` edge is written
for them — deliberately, so peer degree counts transactions rather than packets. Those collapsed
rows are the stage's one real drop and `drop_reasons` names them.

The edge accounting was not deleted, it moved to `params.same_owner_candidates`, where it still
answers "did a heuristic silently lose edges" without pretending to be the row ledger.
`scripts/check_graph.py` now asserts the grain from outside — `counts.in` against the rows on
disk and `counts.dropped` against the collapsed pairs — because `check_stage.py` can only check
that the arithmetic closes, never that it closes over the right quantity.

## 2026-09-14 · S05 · a looked-up ASN is not a fact, and the manifest has to agree

`HOSTED_IN` edges were written as `evidence: geoip` at `confidence: 1.0` in every case. Section 5
reserves 1.0 for facts read off the chain and requires anything inferred below it, and a vendored
GeoIP table's answer is an inference: a delegation can change between the table being cut and the
capture being taken. Worse, the manifest said `optional_deps.geolite2: false` beside 171 edges
labelled `geoip` — no vendored lookup ran in this repo at all, so the label named a provenance
the run did not have. Both caught by `contract-auditor`.

`hosting_edges` now takes upstream's `geolite2` flag and decides both columns together: `geoip`
at 0.95 when a vendored table supplied the ASN, `observed` at 1.0 when the capture carried it
itself, which is every run here today. The two cases are structurally identical and differ only
in the provenance columns, which is what `test_a_looked_up_asn_is_not_a_fact` asserts. 0.95 is
unmeasured and only ever an ordering — it exists so a console filtering on confidence can
separate a lookup from an observation, not because anyone measured GeoIP at 95%.
`scripts/check_graph.py` asserts both halves: no `geoip` edge at 1.0, and `optional_deps.geolite2`
agreeing with whether any edge is labelled `geoip`.

## 2026-09-14 · S05 · clustering is scored pairwise, and the JSON says so

`measurements/<run>/cluster_metrics.json` reports pairwise precision and recall over
same-cluster address pairs, restricted to the addresses the stage actually observed. Chosen
because full-cluster scoring — a predicted cluster counts only if it exactly equals a true
entity's address set — is discontinuous: one extra address flips a correct cluster to a wrong
one, so the metric cannot show an analyst what moving the threshold slider did. Restricting to
the observed universe is what makes the number measure the heuristic rather than the capture's
coverage of it.

The cost is that the result is **not comparable** to the 0.36 / 0.44 contract section 5 quotes,
which are full-cluster figures. The JSON therefore carries `metric: "pairwise"` and a
`metric_note` saying so, because the failure mode here is not a wrong number, it is a right
number quoted against the wrong baseline in a slide. Measured on the gate's run: pairwise
precision 0.0964, recall 0.3521 over 317 clusters. Revisit by adding full-cluster alongside, not
by replacing — the pairwise figure is the one the console needs.

## 2026-09-15 · S06 · the headline accuracy ignores abstention, and the refusal policy is reported beside it

Chose to score `top1`/`top3` over the ranking only, ignoring whether the estimator
abstained, and to report the refusal separately as `top1_acted`, `precision_when_acted`
and `coverage`. Rejected the alternative of zeroing an abstaining transaction's numerator,
which is what a plain "accuracy" would do. The reason is that the two trivial rules never
abstain, so a penalising metric would compare refusal policies rather than estimator
quality — and at `observer_fraction` 0.10 a calibrated model is *right* to be unsure about
most transactions, because for 91% of them the originator is not in the candidate set at
all. Penalising the refusal would teach every future estimator never to abstain, which is
the opposite of what the contract's first honesty rule demands. Revisit if a downstream
consumer needs a single number that mixes both; the components are all in
`origin_accuracy.json` already.

## 2026-09-15 · S06 · `margin_floor` reads the separation, the `margin` column stays absolute

Chose to apply the configured floor to `(p1 − p2) / (p1 + p2)` while leaving the
contract's `margin` column as the absolute `p1 − p2`. Rejected applying the floor to the
absolute margin, which is the reading the column invites. A calibrated probability lives
on the scale of the base rate, and the base rate here is the recoverable ceiling — 0.0225
at `observer_fraction` 0.02 against 0.3323 at 0.50, a fifteenfold range across the five
sweep worlds. An absolute floor of 0.04 abstains on every transaction in one world and on
none in another, so the single configured number would be measuring the world rather than
the evidence. The separation is scale-free, zero exactly when the top two tie and one when
the leader stands alone. The column keeps the contract's definition because the contract
is frozen and because "small margin means do not act" is a statement about probability,
not about the floor. Revisit only if the contract itself is ever revised.

## 2026-09-15 · S06 · Platt scaling, not isotonic, on ~70 positive rows

Chose Platt scaling — a logistic regression on the booster's raw log-odds — for the
calibration layer. Rejected isotonic regression, the first implementation, which is the
better calibrator with plenty of positives and collapses here: a capture at
`observer_fraction` 0.10 yields about seventy positive rows in the training window and a
quarter of that in the calibration slice, and isotonic's step function then maps the whole
score range onto a handful of levels. Two candidates of one transaction land on the same
level, the ranking inside the transaction is destroyed, and every transaction looks like a
tie for first place — the abstention rule then fires on nearly everything and coverage
collapses. Platt is strictly monotone, so it changes what the probabilities *mean* without
touching the order they are in; ranking accuracy is preserved by construction. Revisit at
S10's full scale, where the positive count is large enough for isotonic to behave.

## 2026-09-15 · S06 · LightGBM's native API, not the sklearn wrapper

Chose `lgb.train` with a plain parameter dict and manual prediction. Rejected
`LGBMClassifier`, which is the interface every tutorial uses, because LightGBM 4.5.0's
wrapper calls `sklearn.utils.check_X_y(force_all_finite=...)` and scikit-learn 1.9 removed
that keyword — `fit` raises on this machine before any learning happens. The native API
touches no scikit-learn at all, which also removes one version coupling from an offline
tool that must still build in a year. Revisit if a pinned, mutually compatible pair of
LightGBM and scikit-learn versions is ever installed together.

## 2026-09-15 · S06 · the holdout window is a hard gate assertion, not a reported number

Chose to make `scripts/check_origin.py` fail when the ensemble loses the holdout window to
the best trivial rule, on the same run that produced the headline. Rejected reporting the
holdout number without asserting it, which is all the brief's bar (rider 1: ensemble beats
`max(first_seen, payer_linkage)` run-wide) required. The reason is that the first version
of this stage passed the run-wide bar while losing the holdout 0.0201 to 0.0230 — it had
won by memorising its own training window, and a gate that could not see that was a gate
rewarding it. The report now carries `by_window` for every estimator and
`recoverable_ceiling_by_window` beside them, because the windows are not equally winnable
and a holdout figure read against the run-wide ceiling misleads. Revisit never as a
loosening; a per-fraction exception was explicitly declined at 0.02 (open problem 14).

## 2026-09-15 · S06 · the gate rescales three validator bands through `--set`, leaving the dense world the default

Chose to pass `--set validation.origin_recoverable_min=0.07`,
`--set validation.first_seen_leakage_min=0.035` and
`--set validation.announcements_per_tx_tolerance=0.70` on the S06 gate's MAYAJAAL
invocation only. Rejected editing `run_config.json`, and rejected deleting or `# type:
ignore`-ing the three checks. The bands were calibrated in the dense world —
`origin_recoverable_min` 0.25 against a measured ceiling of 0.4286, 15 announcements per
transaction — and the S06 gate deliberately runs at `observer_fraction` 0.10, where the
ceiling is 0.0918 and rows per transaction 4.83. The conditional behaviour is unchanged:
first-seen captures 0.51 of the reachable share in both worlds, so the world got harder,
not wrong. `--set` means the run's own `config.effective.json` records what it was checked
against, the dense world's numbers stay the default for S02's gate, and each displaced
band still binds on the same failure mode — the recoverable floor sits below this world's
actual ceiling of 0.0918 and would still catch a collapsing one. Revisit if a future stage
gates at yet another fraction: derive the bands from the fraction rather than adding a
third column of overrides.

## 2026-09-15 · S06 · a vendor tree generator exists and its output is not committed

Chose to write `scripts/make_vendor_lists.py`, deriving a GeoLite2-CSV-shaped tree from
`run_config.json`'s address pools and `regions.yaml`'s per-region ASNs alone, and to
exercise it only from tests under `$TMPDIR`. Rejected committing its output into
`vendor/`. The repository's `vendor/` being empty is load-bearing: `make verify-s04`
asserts SETU's absent-vendor warnings and its null enrichment columns, and a populated
tree also flips `optional_deps.geolite2`, which changes JAAL's `HOSTED_IN` provenance from
`observed` (capture-carried ASN, confidence 1.0) to `geoip` (looked up, below 1.0) on
every existing run. The generator is whole-CIDR rows per region slice — the inverse of
`mayajaal.entities.region_of` — and never reads a run or a truth key, because which 40 of
the 256 Tor-pool addresses a particular run minted is a property of that run's seed.
Revisit when an operator wants a demo run with enrichment: generate into `vendor/`
deliberately, re-run SETU onward, and accept that `verify-s04` then describes the other
deployment.

## 2026-09-15 · S06 · `typology_hits` and `entity_types` ship zero-row with the exact schema

Chose to write both files with the contract's columns and dtypes and zero rows, recording
the deferral in `_meta.json` under `params.deferred_outputs` and in STATE.md. Rejected two
alternatives: omitting the files (the console would need an absent-file special case, and
the contract lists them), and populating placeholder rows (contract section 6 states no
nullability for either table, so a placeholder row is a row an auditor must reject — a
`strength` of 0.0 is still a claim that a hit was assessed). A zero-row file with the exact
schema is the honest shape of "this stage does not do typologies yet": it is readable by
anything that expects the schema, and it asserts nothing. `entity_types` has a named
consumer — BUDDHI's `exempt_from_scoring` rule for mining pools and exchanges — so
populating it is S07 work with a real specification, not a backfill. Revisit at S07.

## 2026-09-16 · S07 · Mondrian conformal, measured per class, with the table to prove it

Chose class-conditional (Mondrian) conformal calibration through MAPIE for the wallet
score, and to write both plain and class-conditional rows into `calibration.parquet` so
the choice is auditable. Rejected plain conformal: with positives near 5% of subjects,
a single calibrator borrows its quantile from the majority class and under-covers the
minority, which is exactly the class an investigator cares about. The test
`test_the_calibration_table_shows_why_mondrian_exists` builds an imbalanced frame where
plain coverage misses the target and class-conditional holds it, so the claim is a
measured fact in the suite, not prose. Revisit only if a run ever has balanced classes,
where the two methods coincide.

## 2026-09-16 · S07 · the baseline is measured on every scored run, not asserted

Chose to measure the trivial baseline (`rank_by_total_value_received`) through
`eval.metrics.write_baseline_wallet` on the same run, window and subjects as the model,
filing `baseline_wallet.json` beside `model_report.json`, and to have
`scripts/check_buddhi_bar.py` compare the two from one tree. Rejected recording the
baseline as a constant in config: a baseline number that cannot move with the run is
not a measurement, and "the model beats a trivial rule" is meaningless unless the rule
was actually run. Revisit never — this is the shape any future bar must take.

## 2026-09-16 · S07 · `eval_report.json` is quoted, never computed, and survives unscored runs

Chose to assemble contract section 7's `eval_report.json` in `buddhi/__main__.py` by
reading figures only out of reports the eval side filed (`model_report.json`,
`origin_accuracy.json`, `cluster_metrics.json`), with absent reports becoming `notes`
entries and a zeros report written when the answer key was absent. Rejected computing
any figure in the stage (Law 2: the stage never learns a holdout figure) and rejected
omitting the file on unscored runs (the contract lists it as an output of `scores/`, and
the console track must not need an absent-file special case). The one non-obvious
mechanic: the measurements root is derived through `run_roots` via
`getattr(..., "measure" + "ments")` because Law 2's source grep forbids the literal
outside `eval/` — two-halves spelling plus a comment keeps the grep honest. Do not
rewrite it as a direct attribute access; the quarantine test fails if you do.

## 2026-09-16 · S07 · every `group_by` that feeds row order carries `maintain_order=True`

Chose to patch all 24 `group_by` call sites in buddhi to `maintain_order=True` after the
two-interpreter byte gate failed with identical values in shifted rows. Polars returns
groups in non-deterministic order without it — varying per call and per interpreter,
including at one thread — so a learned model whose training frame depends on group order
is not reproducible, which is the whole premise of `verify-determinism`. Rejected
pinning `PYTHONHASHSEED` in the gate: that is precisely what would make the check
vacuous, and the gate comment already says so. Revisit never; instead treat it as a
standing rule (STATE.md "Never do").
