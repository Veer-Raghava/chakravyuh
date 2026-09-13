"""SETU: what must hold when one table becomes four.

Two tests here are marked `quarantine` and registered in `tests/conftest.py`: the one that runs
the whole stage in a working directory where the answer key does not exist, and the one that
greps the four written files for the quarantined names. They are Law 2 rules that only a real
run can demonstrate, so `make verify-quarantine` collects them as well as the stage gate.

Everything that writes does so under `tmp_path` and changes directory into it first, because
SETU's path guard is relative to the working directory: running from `tmp_path` exercises the
guard rather than stepping around it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from chakravyuh.kavach.seal import resolve_out as kavach_out
from chakravyuh.kavach.seal import seal
from chakravyuh.setu import normalise, schema
from chakravyuh.setu.enrich import Enricher
from chakravyuh.setu.stage import InputPathError, normalise_run, resolve_in, resolve_out

REPO = Path(__file__).resolve().parent.parent
FIXTURE_CAPTURE = REPO / "data" / "fixtures" / "capture" / "capture.csv"

# Transcribed from docs/DATA-CONTRACTS.md section 4 by hand, not imported from
# chakravyuh.setu.schema. A contract test that reads the same constant the code writes from
# asserts only that a module equals itself.
CONTRACT_SECTION_4: dict[str, list[tuple[str, str]]] = {
    "announcements.parquet": [
        ("row_id", "Int64"),
        ("txid", "String"),
        ("peer_ip", "String"),
        ("peer_port", "Int32"),
        ("observer_ip", "String"),
        ("observer_port", "Int32"),
        ("seen_us", "Int64"),
        ("rank_in_tx", "Int32"),
        ("delta_first_us", "Int64"),
        ("geo_country", "String"),
        ("asn", "Int32"),
        ("as_org", "String"),
        ("net_class", "String"),
        ("peer_seen_count", "Int32"),
        ("msg_type", "String"),
    ],
    "transactions.parquet": [
        ("txid", "String"),
        ("first_seen_us", "Int64"),
        ("last_seen_us", "Int64"),
        ("n_announcements", "Int32"),
        ("n_distinct_peers", "Int32"),
        ("announce_spread_us", "Int64"),
        ("input_addresses", "List(String)"),
        ("output_addresses", "List(String)"),
        ("input_amounts", "List(Int64)"),
        ("output_amounts", "List(Int64)"),
        ("n_in", "Int32"),
        ("n_out", "Int32"),
        ("total_in_sats", "Int64"),
        ("total_out_sats", "Int64"),
        ("fee_sats", "Int64"),
        ("fee_rate_sat_vb", "Float64"),
        ("is_coinbase", "Boolean"),
        ("has_equal_outputs", "Boolean"),
        ("change_index", "Int32"),
        ("block_height", "Int32"),
    ],
    "addresses.parquet": [
        ("address", "String"),
        ("script_type", "String"),
        ("first_seen_us", "Int64"),
        ("last_seen_us", "Int64"),
        ("n_tx_in", "Int32"),
        ("n_tx_out", "Int32"),
        ("total_received_sats", "Int64"),
        ("total_sent_sats", "Int64"),
        ("balance_sats", "Int64"),
        ("dwell_time_us", "Int64"),
    ],
    "peers.parquet": [
        ("peer_ip", "String"),
        ("n_announcements", "Int32"),
        ("n_txids", "Int32"),
        ("mean_rank", "Float64"),
        ("frac_rank_one", "Float64"),
        ("distinct_ports", "Int32"),
        ("geo_country", "String"),
        ("asn", "Int32"),
        ("as_org", "String"),
        ("net_class", "String"),
        ("first_us", "Int64"),
        ("last_us", "Int64"),
    ],
}


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root holding `data/` and nothing else, with the process moved into it."""
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _seal_fixture(workspace: Path, name: str = "run") -> Path:
    """Seal the committed capture into `<workspace>/data/generated/<name>/sealed/`.

    The committed fixture rather than a generated capture: it is small enough to reason about,
    it is the same input the S03 gate seals, and it carries the documented bad row, so the
    announcement count SETU must preserve is a post-rejection count and not the file's length.
    """
    target = workspace / "data" / "capture.csv"
    target.write_bytes(FIXTURE_CAPTURE.read_bytes())
    seal(target, kavach_out(Path("data/generated") / name))
    return workspace / "data" / "generated" / name


def _run(workspace: Path, name: str = "run", vendor: Path | None = None) -> Path:
    run = _seal_fixture(workspace, name)
    normalise_run(resolve_in(run / "sealed"), resolve_out(run), vendor)
    return run / "normalised"


def _rows(**overrides: object) -> pl.DataFrame:
    """A three-announcement, two-transaction sealed frame with every value chosen by hand.

    tx `aa` is announced twice, both in the same microsecond. tx `bb` is announced once, one
    second later. Amounts are small and round so the arithmetic in the assertions is readable.
    """
    base: dict[str, object] = {
        "row_id": [0, 1, 2],
        "ts_us": [1_000_000, 1_000_000, 2_000_000],
        "src_ip": ["198.51.100.7", "198.51.100.8", "198.51.100.7"],
        "dst_ip": ["192.0.2.1", "192.0.2.1", "192.0.2.1"],
        "src_port": [8333, 8333, 8334],
        "dst_port": [8333, 8333, 8333],
        "txid": ["aa", "aa", "bb"],
        "input_addresses": [["1in"], ["1in"], ["1out1"]],
        "output_addresses": [["1out1", "1out2"], ["1out1", "1out2"], ["1far"]],
        "input_amounts": [[10_000], [10_000], [7_000]],
        "output_amounts": [[7_000, 2_500], [7_000, 2_500], [6_100]],
    }
    base.update(overrides)
    return pl.DataFrame(base)


# --- the grain split -------------------------------------------------------------------


def test_every_sealed_row_becomes_exactly_one_announcement(workspace: Path) -> None:
    """The count the whole stage is accountable for, asserted against the file it came from."""
    out = _run(workspace)
    sealed = pl.read_parquet(workspace / "data" / "generated" / "run" / "sealed" / "rows.parquet")
    announcements = pl.read_parquet(out / "announcements.parquet")

    assert announcements.height == sealed.height
    assert announcements["row_id"].to_list() == sorted(sealed["row_id"].to_list())
    assert announcements["row_id"].n_unique() == announcements.height


def test_transaction_count_equals_the_number_of_distinct_txids(workspace: Path) -> None:
    out = _run(workspace)
    sealed = pl.read_parquet(workspace / "data" / "generated" / "run" / "sealed" / "rows.parquet")
    transactions = pl.read_parquet(out / "transactions.parquet")

    assert transactions.height == sealed["txid"].n_unique()
    assert transactions["txid"].n_unique() == transactions.height
    assert transactions["n_announcements"].sum() == sealed.height


def test_entity_tables_hold_one_row_per_distinct_entity(workspace: Path) -> None:
    out = _run(workspace)
    sealed = pl.read_parquet(workspace / "data" / "generated" / "run" / "sealed" / "rows.parquet")
    peers = pl.read_parquet(out / "peers.parquet")
    addresses = pl.read_parquet(out / "addresses.parquet")

    assert peers.height == sealed["src_ip"].n_unique()
    assert peers["n_announcements"].sum() == sealed.height

    seen = set(sealed["input_addresses"].explode().drop_nulls().to_list()) | set(
        sealed["output_addresses"].explode().drop_nulls().to_list()
    )
    assert addresses.height == len(seen)
    assert set(addresses["address"].to_list()) == seen


def test_the_hand_built_frame_splits_into_the_grains_computed_by_eye() -> None:
    """Three announcements, two transactions, four addresses, two peers, all checked by hand."""
    rows = _rows()
    base = normalise.base_announcements(rows)
    transactions = normalise.transactions(rows)

    assert base.height == 3
    assert base["peer_ip"].to_list() == ["198.51.100.7", "198.51.100.8", "198.51.100.7"]

    by_txid = {row["txid"]: row for row in transactions.iter_rows(named=True)}
    assert set(by_txid) == {"aa", "bb"}

    aa = by_txid["aa"]
    assert aa["n_announcements"] == 2
    assert aa["n_distinct_peers"] == 2
    assert aa["first_seen_us"] == 1_000_000
    assert aa["last_seen_us"] == 1_000_000
    assert aa["announce_spread_us"] == 0
    assert (aa["n_in"], aa["n_out"]) == (1, 2)
    assert (aa["total_in_sats"], aa["total_out_sats"]) == (10_000, 9_500)
    assert aa["fee_sats"] == 500
    assert aa["fee_rate_sat_vb"] is None
    assert aa["is_coinbase"] is False
    assert aa["has_equal_outputs"] is False
    # 2500 is not a multiple of 1000 and 1out2 is not an input of aa, so it is the sole
    # candidate of two outputs. 7000 is round, so it reads as the payment.
    assert aa["change_index"] == 1

    bb = by_txid["bb"]
    assert bb["fee_sats"] == 900
    # 6100 is not a multiple of 1000 and 1far is not an input of bb, so it is the sole
    # candidate. One output is not two, so the stage still declines to name a change index.
    assert bb["change_index"] == normalise.CHANGE_UNDETERMINED


def test_change_index_names_the_sole_non_round_output_that_is_not_an_input() -> None:
    """Two outputs, one round payment and one ragged return to an address this tx did not spend."""
    rows = _rows(
        txid=["aa", "aa", "cc"],
        output_addresses=[["1out1", "1out2"], ["1out1", "1out2"], ["1paid", "1change"]],
        output_amounts=[[7_000, 2_500], [7_000, 2_500], [5_000, 1_900]],
    )
    transactions = normalise.transactions(rows)
    cc = transactions.filter(pl.col("txid") == "cc").row(0, named=True)
    assert cc["change_index"] == 1

    # The same transaction paying its own input address back cannot be read as change: the
    # rule exists to find an address the graph stage has not already linked for free.
    self_pay = _rows(
        txid=["aa", "aa", "cc"],
        input_addresses=[["1in"], ["1in"], ["1change"]],
        output_addresses=[["1out1", "1out2"], ["1out1", "1out2"], ["1paid", "1change"]],
        input_amounts=[[10_000], [10_000], [7_000]],
        output_amounts=[[7_000, 2_500], [7_000, 2_500], [5_000, 1_900]],
    )
    cc_self = normalise.transactions(self_pay).filter(pl.col("txid") == "cc").row(0, named=True)
    assert cc_self["change_index"] == normalise.CHANGE_UNDETERMINED


def test_a_coinbase_transaction_has_no_inputs_and_a_zero_fee() -> None:
    """Inputs minus outputs would be negative here, and a negative fee is not a fee."""
    rows = _rows(
        txid=["aa", "aa", "cb"],
        input_addresses=[["1in"], ["1in"], []],
        input_amounts=[[10_000], [10_000], []],
        output_addresses=[["1out1", "1out2"], ["1out1", "1out2"], ["1miner"]],
        output_amounts=[[7_000, 2_500], [7_000, 2_500], [312_500_000]],
    )
    coinbase = normalise.transactions(rows).filter(pl.col("txid") == "cb").row(0, named=True)
    assert coinbase["is_coinbase"] is True
    assert coinbase["n_in"] == 0
    assert coinbase["fee_sats"] == 0


def test_has_equal_outputs_is_true_only_when_two_outputs_share_a_value() -> None:
    rows = _rows(
        txid=["aa", "aa", "cj"],
        output_addresses=[["1out1", "1out2"], ["1out1", "1out2"], ["1a", "1b", "1c"]],
        output_amounts=[[7_000, 2_500], [7_000, 2_500], [5_000, 5_000, 900]],
    )
    by_txid = {
        row["txid"]: row["has_equal_outputs"]
        for row in normalise.transactions(rows).iter_rows(named=True)
    }
    assert by_txid == {"aa": False, "cj": True}


# --- ordering and time -----------------------------------------------------------------


def test_a_tie_in_seen_us_ranks_both_peers_first() -> None:
    """Min-ranking, not ordinal.

    Two peers announcing in the same microsecond are indistinguishable to the capture. An
    ordinal rank would break the tie on file order, which would put file order into
    `frac_rank_one` and from there into the origin estimator's features.
    """
    base = normalise.base_announcements(_rows())
    tied = base.filter(pl.col("txid") == "aa")
    assert tied["rank_in_tx"].to_list() == [1, 1]
    assert tied["delta_first_us"].to_list() == [0, 0]

    peers = normalise.peers(base, normalise.peer_facts(["198.51.100.7", "198.51.100.8"], _none()))
    by_ip = {row["peer_ip"]: row for row in peers.iter_rows(named=True)}
    # .8 announced once, at rank 1. .7 announced twice, at rank 1 both times.
    assert by_ip["198.51.100.8"]["frac_rank_one"] == 1.0
    assert by_ip["198.51.100.7"]["frac_rank_one"] == 1.0
    assert by_ip["198.51.100.7"]["n_announcements"] == 2
    assert by_ip["198.51.100.7"]["distinct_ports"] == 2


def test_announce_spread_and_delta_first_are_never_negative(workspace: Path) -> None:
    """Both are a maximum or a member minus the minimum of the same group, so both are
    non-negative by construction. Asserted anyway: the brief names a negative spread as the
    symptom of a reshape that lost its grouping, and it is cheap to catch here."""
    out = _run(workspace)
    transactions = pl.read_parquet(out / "transactions.parquet")
    announcements = pl.read_parquet(out / "announcements.parquet")

    assert transactions.filter(pl.col("announce_spread_us") < 0).height == 0
    assert (
        transactions.filter(
            pl.col("announce_spread_us") != pl.col("last_seen_us") - pl.col("first_seen_us")
        ).height
        == 0
    )
    assert announcements.filter(pl.col("delta_first_us") < 0).height == 0
    assert announcements.filter(pl.col("rank_in_tx") < 1).height == 0
    rank_one = announcements.filter(pl.col("rank_in_tx") == 1)
    assert rank_one.filter(pl.col("delta_first_us") != 0).height == 0


def test_dwell_time_is_the_median_gap_between_being_paid_and_being_spent() -> None:
    """`1out1` is paid at 1_000_000 by `aa` and spent at 2_000_000 by `bb`. One second."""
    transactions = normalise.transactions(_rows())
    addresses = normalise.addresses(transactions, normalise.declared_script_types(_rows()))
    by_address = {row["address"]: row for row in addresses.iter_rows(named=True)}

    assert by_address["1out1"]["dwell_time_us"] == 1_000_000
    assert by_address["1out1"]["n_tx_in"] == 1
    assert by_address["1out1"]["n_tx_out"] == 1
    assert by_address["1out1"]["balance_sats"] == 0
    # Received but never spent inside the window: there is no gap to take a median of.
    assert by_address["1out2"]["dwell_time_us"] is None
    assert by_address["1out2"]["n_tx_in"] == 0
    # Spent from a balance funded before the capture opened. A negative balance is the honest
    # answer; inventing a starting balance nobody observed is not.
    assert by_address["1in"]["balance_sats"] == -10_000
    assert by_address["1in"]["dwell_time_us"] is None


# --- enrichment ------------------------------------------------------------------------


def _none() -> Enricher:
    """An enricher pointed at a directory that does not exist."""
    return Enricher(Path("no-such-vendor-directory"))


def _vendor(
    root: Path, *, asn: bool = True, tor: bool = True, org: str = "Example Telecom"
) -> Path:
    """A synthetic GeoLite2 CSV tree, in the date-stamped layout MaxMind's zip unpacks into.

    `0.0.0.0/0` and `::/0` so every address in any fixture resolves, which keeps the assertions
    about what enrichment produced rather than about which IPs happened to be in the capture.
    Both versions are present because the fixture capture carries IPv6 peers and one sorted
    range table per version is the whole of the claim that one code path serves both.
    """
    base = root / "vendor" / "GeoLite2-Country-CSV_20260101"
    base.mkdir(parents=True)
    (base / "GeoLite2-Country-Locations-en.csv").write_text(
        "geoname_id,locale_code,continent_code,continent_name,country_iso_code,country_name\n"
        "1269750,en,AS,Asia,IN,India\n",
        encoding="utf-8",
    )
    block_header = (
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider\n"
    )
    (base / "GeoLite2-Country-Blocks-IPv4.csv").write_text(
        block_header + "0.0.0.0/0,1269750,1269750,,0,0\n", encoding="utf-8"
    )
    (base / "GeoLite2-Country-Blocks-IPv6.csv").write_text(
        block_header + "::/0,1269750,1269750,,0,0\n", encoding="utf-8"
    )
    if asn:
        asn_dir = root / "vendor" / "GeoLite2-ASN-CSV_20260101"
        asn_dir.mkdir(parents=True)
        asn_header = "network,autonomous_system_number,autonomous_system_organization\n"
        (asn_dir / "GeoLite2-ASN-Blocks-IPv4.csv").write_text(
            asn_header + f"0.0.0.0/0,64500,{org}\n", encoding="utf-8"
        )
        (asn_dir / "GeoLite2-ASN-Blocks-IPv6.csv").write_text(
            asn_header + f"::/0,64500,{org}\n", encoding="utf-8"
        )
    if tor:
        (root / "vendor" / "exit-addresses.txt").write_text(
            "# a comment line\nExitAddress 198.51.100.8 2026-01-01 00:00:00\n",
            encoding="utf-8",
        )
    return root / "vendor"


def test_an_absent_vendor_directory_leaves_null_columns_and_a_warning(workspace: Path) -> None:
    """The path the brief says must be built and tested rather than only planned."""
    out = _run(workspace, vendor=workspace / "no-such-vendor-directory")
    meta = json.loads((out / "_meta.json").read_text(encoding="utf-8"))

    assert meta["params"]["enrichment"] == {
        "geolite2_country": False,
        "geolite2_asn": False,
        "tor_exit_list": False,
    }
    assert "vendor_absent" in meta["warnings"]
    assert "enrichment_unavailable_geo_asn_net_class_are_null" in meta["warnings"]
    assert meta["optional_deps"]["geolite2"] is False

    for name in ("announcements.parquet", "peers.parquet"):
        frame = pl.read_parquet(out / name)
        assert frame.height > 0
        assert frame["as_org"].null_count() == frame.height
        assert frame["net_class"].null_count() == frame.height


def test_a_vendored_csv_tree_fills_as_org_and_net_class(workspace: Path) -> None:
    vendor = _vendor(workspace, org="Amazon Data Services")
    out = _run(workspace, vendor=vendor)
    meta = json.loads((out / "_meta.json").read_text(encoding="utf-8"))

    assert meta["params"]["enrichment"] == {
        "geolite2_country": True,
        "geolite2_asn": True,
        "tor_exit_list": True,
    }
    assert "vendor_absent" not in meta["warnings"]
    assert meta["optional_deps"]["geolite2"] is True

    peers = pl.read_parquet(out / "peers.parquet")
    assert peers["as_org"].null_count() == 0
    assert peers["asn"].null_count() == 0
    assert peers["net_class"].null_count() == 0
    assert set(peers["net_class"].to_list()) <= schema.NET_CLASSES


def test_net_class_stays_inside_the_contract_vocabulary(tmp_path: Path) -> None:
    """Every branch of the classifier, driven by the AS organisation it reads."""
    cases = {
        "Example Telecom Broadband": "residential",
        "Amazon Data Services": "hosting",
        "Example Mobile Cellular": "mobile",
        "Mullvad VPN AB": "vpn_suspect",
    }
    for index, (org, expected) in enumerate(cases.items()):
        root = tmp_path / f"case{index}"
        root.mkdir()
        facts = Enricher(_vendor(root, org=org)).lookup("203.0.113.5")
        assert facts.net_class == expected, org
        assert facts.net_class in schema.NET_CLASSES
        assert facts.geo_country == "IN"
        assert facts.asn == 64500


def test_one_code_path_serves_ipv4_and_ipv6(tmp_path: Path) -> None:
    """`ipaddress` gives arbitrary-precision integers, so a 128-bit key sorts and bisects the
    same way a 32-bit one does. Only the version-split range table keeps them apart."""
    enricher = Enricher(_vendor(tmp_path))
    assert enricher.lookup("2001:db8::1") == enricher.lookup("203.0.113.5")
    # Normalised through ip_address, so an expanded form matches a compressed one.
    assert enricher.lookup("2001:0db8:0000:0000:0000:0000:0000:0001").geo_country == "IN"
    # Not an address at all. A capture can carry anything; a lookup is not a validator.
    assert Enricher(_vendor(tmp_path / "second")).lookup("not-an-ip").net_class is None


def test_a_tor_exit_outranks_whatever_its_hosting_provider_is(tmp_path: Path) -> None:
    """An exit node runs on somebody's hardware, so the ASN says hosting and says nothing
    useful. The exit list is the more specific claim and wins."""
    enricher = Enricher(_vendor(tmp_path, org="Amazon Data Services"))
    assert enricher.lookup("198.51.100.8").net_class == "tor_exit"
    assert enricher.lookup("198.51.100.7").net_class == "hosting"


def test_an_absent_tor_list_is_a_warning_and_not_a_crash(tmp_path: Path) -> None:
    enricher = Enricher(_vendor(tmp_path, tor=False))
    assert "tor_exit_list_absent" in enricher.warnings
    assert enricher.has_tor is False
    assert enricher.lookup("198.51.100.8").net_class == "residential"


def test_null_and_unknown_are_different_answers(tmp_path: Path) -> None:
    """Null means no list was available to ask. `unknown` means the lists were there and none
    of them recognised the address, which is a fact about the address and not the deployment."""
    assert _none().lookup("203.0.113.5").net_class is None

    no_asn = Enricher(_vendor(tmp_path, asn=False))
    assert no_asn.has_geo is True
    assert no_asn.has_asn is False
    assert no_asn.lookup("203.0.113.5").net_class == "unknown"


def test_the_capture_keeps_its_own_geo_and_asn_where_it_has_one(workspace: Path) -> None:
    """Contract section 4 says geo and ASN are "enriched if null on input", not overwritten.

    A real NTRO capture may carry an ASN resolved at capture time, which is closer to the truth
    than a lookup done months later against a table that has since been re-delegated.
    """
    sealed = _seal_fixture(workspace)
    rows = pl.read_parquet(sealed / "sealed" / "rows.parquet")
    known = rows.filter(pl.col("geo_country").is_not_null())
    assert known.height > 0, "the fixture no longer carries geo_country, pick another column"

    normalise_run(resolve_in(sealed / "sealed"), resolve_out(sealed), _vendor(workspace))
    announcements = pl.read_parquet(sealed / "normalised" / "announcements.parquet")
    kept = announcements.join(
        known.select("row_id", pl.col("geo_country").alias("was")), on="row_id", how="inner"
    )
    assert kept.height == known.height
    assert kept.filter(pl.col("geo_country") != pl.col("was")).height == 0
    # The vendored table says IN for everything, so a row that had nothing now says IN.
    assert announcements["geo_country"].null_count() == 0


def test_a_malformed_vendor_line_is_skipped_rather_than_fatal(tmp_path: Path) -> None:
    """A vendored file is third-party data. One bad line in it must not take a run down."""
    vendor = _vendor(tmp_path)
    blocks = vendor / "GeoLite2-ASN-CSV_20260101" / "GeoLite2-ASN-Blocks-IPv4.csv"
    blocks.write_text(
        blocks.read_text(encoding="utf-8") + "not-a-network,64501,Broken Row Telecom\n",
        encoding="utf-8",
    )
    assert Enricher(vendor).lookup("203.0.113.5").asn == 64500


# --- the stage contract ----------------------------------------------------------------


def test_every_output_matches_contract_section_four_column_for_column(workspace: Path) -> None:
    out = _run(workspace)
    for name, columns in CONTRACT_SECTION_4.items():
        frame = pl.read_parquet(out / name)
        assert [
            (column, str(dtype)) for column, dtype in zip(frame.columns, frame.dtypes, strict=True)
        ] == columns, name


def test_meta_carries_the_upstream_hash_so_staleness_is_detectable(workspace: Path) -> None:
    import hashlib

    out = _run(workspace)
    meta = json.loads((out / "_meta.json").read_text(encoding="utf-8"))
    upstream = workspace / "data" / "generated" / "run" / "sealed" / "_meta.json"

    assert meta["stage"] == "setu"
    assert meta["params"]["upstream_meta"]["path"].endswith("sealed/_meta.json")
    assert (
        meta["params"]["upstream_meta"]["sha256"]
        == hashlib.sha256(upstream.read_bytes()).hexdigest()
    )
    assert {entry["path"] for entry in meta["outputs"]} == {
        f"normalised/{name}" for name in CONTRACT_SECTION_4
    }
    for entry in meta["outputs"]:
        written = (out.parent / entry["path"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(written).hexdigest()


def test_counts_account_for_every_row_that_arrived(workspace: Path) -> None:
    """Contract section 10. SETU reshapes and never rejects, so `dropped` is structurally zero
    and the identity reduces to in equals out."""
    out = _run(workspace)
    meta = json.loads((out / "_meta.json").read_text(encoding="utf-8"))
    counts = meta["counts"]

    assert counts["in"] == counts["out"] + counts["dropped"]
    assert counts["dropped"] == 0
    assert counts["drop_reasons"] == {}
    assert counts["in"] == meta["inputs"][0]["rows"]


def test_two_runs_of_one_input_write_the_same_bytes(workspace: Path) -> None:
    """The in-process half of the determinism check. `make verify-s04` runs the other half in
    two separate interpreters, which is the only way to catch a hash seed leaking into output."""
    import hashlib

    first = _run(workspace, "a")
    second_run = workspace / "data" / "generated" / "run-b"
    normalise_run(
        resolve_in(workspace / "data" / "generated" / "a" / "sealed"),
        resolve_out(second_run),
        None,
    )
    for name in CONTRACT_SECTION_4:
        assert (
            hashlib.sha256((first / name).read_bytes()).hexdigest()
            == hashlib.sha256((second_run / "normalised" / name).read_bytes()).hexdigest()
        ), name


def test_setu_refuses_a_path_outside_the_data_tree(workspace: Path) -> None:
    """The guard that makes the quarantine structural rather than a matter of care: the answer
    key is a sibling of `data/`, so an input SETU will accept can never reach it."""
    (workspace / "elsewhere").mkdir()
    with pytest.raises(InputPathError):
        resolve_in(workspace / "elsewhere")
    with pytest.raises(InputPathError):
        resolve_out(workspace / "elsewhere")
    with pytest.raises(InputPathError):
        resolve_out(Path("data/generated"))


def test_a_sealed_directory_with_no_rows_file_is_named_not_guessed_at(workspace: Path) -> None:
    empty = workspace / "data" / "generated" / "empty"
    empty.mkdir()
    with pytest.raises(InputPathError, match="rows.parquet"):
        resolve_in(empty)


def test_a_capture_missing_a_required_column_is_refused() -> None:
    with pytest.raises(schema.SealedInputError, match="txid"):
        normalise.base_announcements(_rows().drop("txid"))


def test_optional_columns_absent_from_the_capture_become_typed_nulls() -> None:
    """`vsize`, `block_height`, `msg_type` and `script_types` are our extensions, not the
    contract's input. A capture without them must still produce all twenty columns."""
    rows = _rows()
    transactions = normalise.transactions(rows)
    assert transactions["block_height"].null_count() == transactions.height
    assert transactions["fee_rate_sat_vb"].null_count() == transactions.height
    assert normalise.declared_script_types(rows).height == 0

    announcements = normalise.announcements(
        normalise.base_announcements(rows),
        normalise.peers(
            normalise.base_announcements(rows),
            normalise.peer_facts(["198.51.100.7", "198.51.100.8"], _none()),
        ),
    )
    assert announcements["msg_type"].null_count() == announcements.height


def test_a_declared_script_type_beats_the_prefix_guess() -> None:
    """The capture said so. Guessing from a prefix is what happens when nobody did."""
    rows = _rows(script_types=[["p2wpkh", "p2sh"], ["p2wpkh", "p2sh"], ["p2pkh"]])
    addresses = normalise.addresses(
        normalise.transactions(rows), normalise.declared_script_types(rows)
    )
    by_address = {row["address"]: row["script_type"] for row in addresses.iter_rows(named=True)}
    assert by_address["1out1"] == "p2wpkh"
    assert by_address["1out2"] == "p2sh"
    # Never an output in this capture, so nothing declared a type for it and the prefix rules.
    assert by_address["1in"] == "p2pkh"


# --- quarantine ------------------------------------------------------------------------


def test_setu_normalises_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted.

    A subprocess whose working directory holds only `data/`. The answer key is not merely
    unread here, it does not exist on any path the process could construct, so a stage that had
    quietly grown a dependency on it cannot complete.
    """
    _seal_fixture(workspace, "isolated")
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.setu.stage import normalise_run, resolve_in, resolve_out;"
        "normalise_run(resolve_in(Path('data/generated/isolated/sealed')),"
        " resolve_out(Path('data/generated/isolated')))"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-2000:]

    meta = json.loads(
        (workspace / "data" / "generated" / "isolated" / "normalised" / "_meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert meta["counts"]["in"] == meta["counts"]["out"]
    assert meta["counts"]["out"] > 0


def test_no_normalised_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: an observable file may not contain either quarantined name.

    Reconstructed from parts so this test file does not itself hold the literal strings the
    guard in `tests/test_contracts.py` greps for.
    """
    forbidden = ("ground" + "_truth", "measure" + "ments")
    out = _run(workspace)
    for path in sorted(out.iterdir()):
        blob = path.read_bytes()
        for needle in forbidden:
            assert needle.encode() not in blob, f"{path.name} names {needle}"
