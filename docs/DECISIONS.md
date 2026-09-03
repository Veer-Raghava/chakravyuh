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
