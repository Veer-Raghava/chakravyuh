# S00 capture fixture

A hand-authored capture of 197 announcement rows covering 26 transactions, serialised to
three formats that describe the same capture:

| file | encoding |
|---|---|
| `capture/capture.csv` | pipe-joined list columns, empty field for null |
| `capture/capture.jsonl` | one JSON object per line, native lists, `null` for null |
| `capture/capture.xml` | repeated `<item>` children for lists, empty element for null |

Regenerate with `make fixtures`. Output is byte-identical across runs, which is why the
files are committed: `docs/DATA-CONTRACTS.md` section 11 requires the fixture set to be in
the repository so a contract change shows up as a diff.

`--seed 42` is recorded in the XML header for provenance but never consumed. There is no
random number generator in `scripts/make_fixtures.py`; every value is an explicit literal,
so byte identity is guaranteed by construction rather than by a reproducible stream.

These files are the S00 stand-in. MAYAJAAL replaces them at S02 with a generated capture at
scale, and this set stays as the small case a person can check by hand.

## The twelve awkward cases

Section 11 of the data contract names twelve cases a generator that flatters its downstream
stages would never produce. `row_id` is the zero-based index in file order, which is what
KAVACH assigns at load. Regenerate this table with `python3 scripts/make_fixtures.py --cases`.

| case | txid | row_id | rows | what to look at |
|---|---|---|---|---|
| coinbase, zero inputs | `f1a70001…0000` | 0–8 | 9 | `input_addresses` and `input_amounts` are both empty; `fee_sats` is 0, not negative |
| regular payout cadence | `f1a70002…0000` | 51–58 | 8 | first of three beats |
| regular payout cadence | `f1a70003…0000` | 134–141 | 8 | 600 s after the first |
| regular payout cadence | `f1a70004…0000` | 190–196 | 7 | 600 s after the second; all three share one input address |
| exactly one announcing peer | `f1a70005…0000` | 9 | 1 | no cascade to fit, so origin estimation must abstain |
| more than fifteen peers | `f1a70006…0000` | 10–26 | 17 | wide enough that a first-seen rule looks confident |
| two peers, same microsecond | `f1a70007…0000` | 27–32 | 6 | rows 3 and 4 carry an identical `timestamp`; rank must not assume a total order |
| first announcer is a Tor exit | `f1a70008…0000` | 33–38 | 6 | opener is `203.0.x.x` port 9001 |
| two wallets, one CGNAT address | `f1a70009…0000` | 39–44 | 6 | opener `203.0.x.x` source port 41000 |
| two wallets, one CGNAT address | `f1a70010…0000` | 45–50 | 6 | same `src_ip`, source port 41001, different transaction |
| equal value outputs | `f1a70011…0000` | 59–70 | 12 | four outputs of 250000 sats each, which defeats common-input-ownership |
| three-hop peel chain | `f1a70012…0000` | 71–79 | 9 | peels 40000 sats, keeps the change |
| three-hop peel chain | `f1a70013…0000` | 80–88 | 9 | spends hop 1's change address |
| three-hop peel chain | `f1a70014…0000` | 89–96 | 8 | spends hop 2's change address |
| IPv6 announcing peer | `f1a70015…0000` | 97–102 | 6 | opener is `2001:db8:x`; must not crash /24 aggregation |
| null ASN | `f1a70016…0000` | 103–108 | 6 | one peer's `asn` is null, not zero |
| malformed row | `f1a70026…0000` | 189 | 1 | two `input_addresses` against three `input_amounts` |

The remaining transactions (`f1a70017…0000` through `f1a70025…0000`) are ordinary traffic:
a four-input consolidation, a twelve-way fan-out, three near-equal transfers to one
destination, a merchant payment, an exchange deposit, a one-in one-out pass-through and one
filler. They exist so the awkward cases are a minority of the capture rather than all of it.

## The one intentional rejection

`f1a70026…0000` violates load invariant 3: `len(input_addresses)` is 2 and
`len(input_amounts)` is 3. KAVACH must quarantine it rather than load it, so the numbers
KAVACH reports for this fixture are fixed:

```
rows_read     197
rows_sealed   196
rows_rejected   1
```

`197 = 196 + 1`. A run that seals 197 rows has a broken validator, and a run that seals 195
is rejecting something it should have kept.

## Nulls

Three columns are nullable: `geo_country`, `asn` and `block_height`. `block_height` is null
for the 51 rows whose transaction is unconfirmed. `asn` is null for one row. `geo_country`
is never null in this fixture.

The XML form cannot distinguish an empty list from a null, because both serialise to an
empty element. That is not a defect to paper over. Section 1 fixes which columns are lists,
so a reader keyed on the column name recovers the distinction, and KAVACH has to be tolerant
of exactly this kind of format-specific ambiguity anyway.

## Why no identifier here can belong to anyone

An invented identifier can turn out to be real, and a forensics tool whose test data names a
live wallet has failed at its own premise. Every identifier is therefore either reserved for
documentation or structurally impossible, and `tests/test_contracts.py` asserts it rather
than trusting this paragraph:

| kind | scheme |
|---|---|
| peer IPv4 | RFC 5737: `192.0.2.0/24`, `203.0.113.0/24` |
| observer IPv4 | RFC 5737: `198.51.100.0/24` |
| peer IPv6 | RFC 3849: `2001:db8::/32` |
| ASN | RFC 5398 documentation range 64496–64511 |
| bech32 address | contains `i`, which is absent from the bech32 charset, so it can never decode |
| base58 address | contains `0`, which is absent from the base58 alphabet, so it can never checksum |
| txid | `f1a7`, a four-digit index, then 56 zeros: valid hex, obviously not a hash |

Addresses still carry real mainnet lengths (34, 42 and 62 characters) so a length-based
script type rule behaves here the way it will on real data.

## Two deliberate anti-leak choices

`msg_type` is **not** correlated with arrival rank. If the originator were the only peer
sending `tx` while relays sent `inv`, origin estimation would be a dictionary lookup and
every accuracy number this project reports would be meaningless.

Announcement gaps are uneven. An arithmetic cascade would let a wrong estimator score well
by fitting the schedule instead of the network.

## Not here yet

Section 11 also asks for a capture carrying only the twelve required columns, so KAVACH's
tolerance for missing optional columns can be tested. That belongs to S03, which is the
stage that has to handle it; adding it now would be a fixture with no test to justify it.
