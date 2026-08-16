"""Tests for the SCF homeownership computation, on synthetic extracts, no network.

The failure this input can produce silently is an inverted ownership coding: it
yields four complete, plausible rates with the K shape upside down. The published
overall rate is the only thing that separates the two readings, so most of what
follows is about that check and the population cut it rests on.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from monetary_topology.scf import (
    GROUPS,
    POPULATION_BAND,
    POPULATION_SHARES,
    PUBLISHED_OWNERSHIP_2022,
    WEIGHT_DIVISOR,
    AnchorProblem,
    Selection,
    SelectionProblem,
    assign_groups,
    extract,
    format_profile,
    homeownership_by_group,
    ownership_rate,
    profile,
    read_rows,
)

MEMBER = "SCFP2022.csv"
ROOT = Path(__file__).resolve().parents[1]


#: Weight per row such that the fixture sums to a plausible family count. The
#: real extract splits a household's weight across its five implicate rows, so
#: the fixture does too and the divisor is one.
def row_weight(n: int) -> float:
    return 131_000_000.0 / (n * IMPLICATE_ROWS)


IMPLICATE_ROWS = 5


def build_rows(
    n: int = 1000,
    owning_code: str = "1",
    renting_code: str = "2",
    ownership_by_rank=None,
) -> list[dict[str, str]]:
    """One household per rank, five implicate rows each.

    The weight is already split across the implicates, as it is in the published
    extract, so summing it over every row gives the family count once.

    ``ownership_by_rank(rank_fraction)`` decides tenure, so a test can put the
    owners anywhere in the distribution. The default reproduces the published
    overall rate with ownership rising in wealth, which is the real shape.
    """
    if ownership_by_rank is None:
        def ownership_by_rank(fraction: float) -> bool:
            # 66.1% of households own, and they are the wealthier ones.
            return fraction >= 1.0 - PUBLISHED_OWNERSHIP_2022

    weight = row_weight(n)
    rows: list[dict[str, str]] = []
    for i in range(n):
        fraction = (i + 0.5) / n
        owns = ownership_by_rank(fraction)
        for implicate in range(IMPLICATE_ROWS):
            rows.append(
                {
                    "YY1": str(i),
                    "Y1": f"{i}{implicate}",
                    "WGT": f"{weight:.6f}",
                    "NETWORTH": f"{(i + 1) * 1000.0:.1f}",
                    "HOUSECL": owning_code if owns else renting_code,
                    "INCOME": f"{(i + 1) * 10.0:.1f}",
                }
            )
    return rows


def write_archive(path: Path, rows: list[dict[str, str]]) -> Path:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(MEMBER, buffer.getvalue())
    return path


def write_selection(path: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "wave": "2022",
        "source": "test",
        "member": MEMBER,
        "weight_column": "WGT",
        "networth_column": "NETWORTH",
        "ownership_column": "HOUSECL",
        "owning_values": ["1"],
        "weight_divisor": WEIGHT_DIVISOR,
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def selection(tmp_path: Path, **overrides: object) -> Selection:
    return Selection.load(write_selection(tmp_path / "sel.json", **overrides))


# ---------------------------------------------------------------------------
# Discovery settles the coding rather than assuming it
# ---------------------------------------------------------------------------
def test_the_profile_reports_the_values_a_coding_would_be_read_from() -> None:
    columns = profile(build_rows(100))
    names = {c.name for c in columns}
    assert "HOUSECL" in names
    assert "NETWORTH" in names
    assert "WGT" in names
    assert "INCOME" not in names, "the profile should not list every column"
    housecl = next(c for c in columns if c.name == "HOUSECL")
    assert housecl.n_values == 2
    assert dict(housecl.common).keys() == {"1", "2"}


def test_the_profile_renders_with_the_header_and_the_row_count() -> None:
    rows = build_rows(20)
    body = format_profile(profile(rows), list(rows[0]), len(rows))
    assert f"{len(rows)} rows" in body
    assert "HOUSECL" in body
    assert "full header" in body


def test_one_csv_is_expected_in_the_archive(tmp_path: Path) -> None:
    path = tmp_path / "two.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("a.csv", "X\n1\n")
        z.writestr("b.csv", "X\n1\n")
    with pytest.raises(SelectionProblem):
        read_rows(path)


# ---------------------------------------------------------------------------
# The cut, and the population identity it must satisfy
# ---------------------------------------------------------------------------
def test_the_cut_reproduces_the_population_shares(tmp_path: Path) -> None:
    records = extract(build_rows(2000), selection(tmp_path))
    groups = assign_groups(records)
    total = sum(r.weight for g in groups for r in g)
    shares = tuple(sum(r.weight for r in g) / total for g in groups)
    for got, want in zip(shares, POPULATION_SHARES, strict=True):
        assert got == pytest.approx(want, abs=2e-3)


def test_the_groups_are_ordered_in_net_worth(tmp_path: Path) -> None:
    records = extract(build_rows(2000), selection(tmp_path))
    groups = assign_groups(records)
    tops = [max(r.networth for r in g) for g in groups]
    assert tops == sorted(tops)


def test_the_divisor_moves_the_population_and_no_share(tmp_path: Path) -> None:
    """A wrong divisor is invisible to every scale-free quantity.

    This is why the weight total is checked at all: the rates and the shares are
    identical under either divisor, so neither can see the error."""
    rows = build_rows(500)
    right = homeownership_by_group(rows, selection(tmp_path))
    wrong = homeownership_by_group(rows, selection(tmp_path, weight_divisor=5),
                                   check_anchors=False)
    assert right["rates"] == pytest.approx(wrong["rates"])
    assert right["population_shares"] == pytest.approx(wrong["population_shares"])
    assert right["overall"] == pytest.approx(wrong["overall"])
    assert wrong["weighted_population"] == pytest.approx(
        right["weighted_population"] / 5
    )


def test_a_divisor_applied_where_it_should_not_be_is_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(AnchorProblem) as caught:
        homeownership_by_group(build_rows(500),
                               selection(tmp_path, weight_divisor=5))
    assert "divisor" in str(caught.value)


def test_the_weight_total_lands_in_the_band(tmp_path: Path) -> None:
    result = homeownership_by_group(build_rows(500), selection(tmp_path))
    low, high = POPULATION_BAND
    assert low <= result["weighted_population"] <= high


# ---------------------------------------------------------------------------
# The anchor that catches an inverted coding
# ---------------------------------------------------------------------------
def test_the_published_overall_rate_is_reproduced(tmp_path: Path) -> None:
    result = homeownership_by_group(build_rows(2000), selection(tmp_path))
    assert result["overall"] == pytest.approx(PUBLISHED_OWNERSHIP_2022, abs=1e-2)


def test_an_inverted_coding_is_refused(tmp_path: Path) -> None:
    """Reading the renting code as owning lands near 34% and must fail."""
    with pytest.raises(AnchorProblem) as caught:
        homeownership_by_group(
            build_rows(2000), selection(tmp_path, owning_values=["2"])
        )
    assert "0.339" in str(caught.value) or "owning_values" in str(caught.value)


def test_a_coding_that_matches_nothing_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SelectionProblem):
        extract(build_rows(100), selection(tmp_path, owning_values=["7"]))


def test_a_selection_without_a_coding_fails_at_load(tmp_path: Path) -> None:
    with pytest.raises(SelectionProblem):
        selection(tmp_path, owning_values=[])


def test_a_missing_column_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SelectionProblem):
        extract(build_rows(100), selection(tmp_path, networth_column="NOPE"))


# ---------------------------------------------------------------------------
# The shape the stage actually needs
# ---------------------------------------------------------------------------
def test_ownership_rises_with_wealth_on_a_realistic_extract(
    tmp_path: Path,
) -> None:
    result = homeownership_by_group(build_rows(2000), selection(tmp_path))
    rates = result["rates"]
    assert rates[0] < rates[1] <= rates[2] <= rates[3]
    assert rates[3] == pytest.approx(1.0)


def test_a_flat_extract_is_a_legal_reading_and_must_not_raise(
    tmp_path: Path,
) -> None:
    """Ownership independent of wealth passes both anchors, as it should.

    Sixty-six of every hundred households own, so every group is exactly 0.66
    and the shape the stage is looking for is simply absent. An anchor that
    fired here would be refusing a result rather than a defect."""
    def flat(fraction: float) -> bool:
        return (int(fraction * 10_000) % 100) < 66

    result = homeownership_by_group(
        build_rows(10_000, ownership_by_rank=flat), selection(tmp_path)
    )
    assert result["overall"] == pytest.approx(0.66, abs=1e-3)
    for rate in result["rates"]:
        assert rate == pytest.approx(0.66, abs=1e-3)


def test_a_wrong_weight_column_leaves_the_population_identity_intact(
    tmp_path: Path,
) -> None:
    """The population check cannot catch a wrong weight, and here is why.

    The cut is defined on the weighted distribution, so the four groups weigh
    0.50, 0.40, 0.09 and 0.01 whatever the weights are. Only the published
    overall rate notices, and only because the wrong weight moves it."""
    rows = build_rows(2000)
    scale = 131_000_000.0 / sum(float(r["NETWORTH"]) for r in rows)
    for row in rows:
        row["WGT"] = f"{float(row['NETWORTH']) * scale:.6f}"

    loose = homeownership_by_group(rows, selection(tmp_path),
                                   check_anchors=False)
    for got, want in zip(loose["population_shares"], POPULATION_SHARES,
                         strict=True):
        assert got == pytest.approx(want, abs=2e-3)
    assert loose["overall"] > PUBLISHED_OWNERSHIP_2022

    with pytest.raises(AnchorProblem) as caught:
        homeownership_by_group(rows, selection(tmp_path))
    assert "owning_values" in str(caught.value)


def test_rows_with_no_weight_are_dropped_rather_than_counted(
    tmp_path: Path,
) -> None:
    rows = build_rows(200)
    for row in rows[:10]:
        row["WGT"] = "0"
    records = extract(rows, selection(tmp_path))
    assert len(records) == len(rows) - 10


def test_the_rate_is_weighted_rather_than_counted(tmp_path: Path) -> None:
    rows = build_rows(100)
    for row in rows:
        if row["HOUSECL"] == "1":
            row["WGT"] = f"{row_weight(100) * 10:.6f}"
    result = homeownership_by_group(rows, selection(tmp_path),
                                    check_anchors=False)
    counted = sum(1 for r in rows if r["HOUSECL"] == "1") / len(rows)
    assert result["overall"] > counted


def test_ownership_rate_of_nothing_is_zero() -> None:
    assert ownership_rate([]) == 0.0


# ---------------------------------------------------------------------------
# The contract between the module and its fetcher
# ---------------------------------------------------------------------------
RESULT_KEYS = {
    "wave",
    "rates",
    "population_shares",
    "overall",
    "records",
    "weighted_population",
}


def test_the_result_carries_exactly_the_documented_keys(tmp_path: Path) -> None:
    result = homeownership_by_group(build_rows(500), selection(tmp_path))
    assert set(result) == RESULT_KEYS


def test_the_fetcher_only_reads_keys_the_module_returns(tmp_path: Path) -> None:
    """This break happened, and nothing caught it.

    ``homeownership_by_group`` renamed a key, ``fetch_scf.py`` went on printing
    the old one, and the suite stayed green because nothing here loaded the
    fetcher. The repository already tests fetchers by path elsewhere; this reads
    the fetcher's source instead, which needs no network and no cache.
    """
    source = (ROOT / "data" / "fetch_scf.py").read_text(encoding="utf-8")
    read: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "result"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            read.add(node.slice.value)
    # A guard that finds nothing to check would pass for the wrong reason.
    assert read, "no result[...] reads were found; this check is not working"
    produced = set(homeownership_by_group(build_rows(500), selection(tmp_path)))
    assert read <= produced, (
        f"the fetcher reads keys the module does not return: "
        f"{sorted(read - produced)}"
    )
