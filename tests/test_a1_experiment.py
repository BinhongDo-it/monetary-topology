"""The arithmetic and the guards in ``experiments/a1_default_cascade.py``.

The model has its own tests and the readers have theirs. What sits between them
is this file's subject: turning five processed tables into one population. That
is where the last stage's one real break happened, when
``monetary_topology.scf`` renamed a key and the fetcher went on reading the old
one with every test green, and it is the layer with no owner unless one is
written for it.

Loaded by path, the way ``tests/test_b5_fetch.py`` loads ``data/fetch_ambito.py``:
the experiment is a script rather than an importable module, and the alternative
is not testing it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load():
    """The module has to be in ``sys.modules`` before it executes.

    ``from __future__ import annotations`` makes every annotation a string, and
    ``dataclass`` resolves those by looking its own module up in
    ``sys.modules``. Executing a module that is not registered there raises on
    the first dataclass, which is a property of the loader rather than of the
    experiment.
    """
    spec = importlib.util.spec_from_file_location(
        "a1_experiment", ROOT / "experiments" / "a1_default_cascade.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


A1 = load()


# ---------------------------------------------------------------------------
# A processed set that is internally consistent, so a break is the test's doing
# ---------------------------------------------------------------------------
CEX = (
    "group,income_before_taxes,necessities,rent,mortgage_payment,"
    "homeowner,mortgaged,renter\n"
    "bottom50,36891.20,15025.00,6162.00,2295.60,0.522000,0.190000,0.478000\n"
    "next40,127322.00,24709.00,5560.00,8301.00,0.742500,0.505000,0.257500\n"
    "next9,346942.00,35286.00,3592.00,20916.00,0.900000,0.700000,0.100000\n"
    "top1,346942.00,35286.00,3592.00,20916.00,0.900000,0.700000,0.100000\n"
)
UNITS = "reference_year,consumer_units,decile_sum\n2024,135760000,135761000\n"
SCF = (
    "group,homeownership_rate,population_share\n"
    "bottom50,0.390550,0.499984\n"
    "next40,0.924598,0.399992\n"
    "next9,0.952914,0.090010\n"
    "top1,0.961470,0.010013\n"
)
DFA = (
    "instrument,bottom50,next40,next9,top1\n"
    "consumer_credit,0.518000,0.349000,0.101000,0.033000\n"
    "home_mortgages,0.225000,0.490000,0.244000,0.041000\n"
    "net_worth,0.025000,0.296000,0.363000,0.316000\n"
)
Z1 = (
    "date,home_mortgages,consumer_credit,mortgage_to_consumer_credit\n"
    "2026-01-01,13820984.0,5073031.0,2.724404\n"
)

FILES = {
    "cex_income_necessities.csv": CEX,
    "cex_consumer_units.csv": UNITS,
    "scf_homeownership.csv": SCF,
    "dfa_shares.csv": DFA,
    "z1_ratio.csv": Z1,
}


def processed(tmp_path: Path, **overrides: str) -> Path:
    folder = tmp_path / "processed"
    folder.mkdir()
    payload = dict(FILES)
    payload.update(overrides)
    for name, text in payload.items():
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    A1.PROCESSED = folder
    return folder


def read(tmp_path: Path, **overrides: str):
    processed(tmp_path, **overrides)
    return A1.read_inputs()


# ---------------------------------------------------------------------------
# The three conversions, each of which has a guard
# ---------------------------------------------------------------------------
def test_the_aggregate_is_divided_by_the_tables_own_household_count(
    tmp_path: Path,
) -> None:
    inputs = read(tmp_path)
    assert inputs.credit_per_household == pytest.approx(
        5_073_031e6 / 135_760_000
    )
    assert inputs.credit_per_household == pytest.approx(37_368.6, rel=1e-4)


def test_a_household_count_in_thousands_is_refused(tmp_path: Path) -> None:
    """The one slip that would otherwise pass every ratio in the stage."""
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path,
             **{"cex_consumer_units.csv":
                "reference_year,consumer_units,decile_sum\n2024,135760,135761\n"})
    assert "millions of dollars" in str(caught.value)


def test_annual_figures_become_monthly_per_household(tmp_path: Path) -> None:
    inputs = read(tmp_path)
    spec = A1.population_spec(inputs, 100)
    stratum = A1.stratum_inputs(inputs, spec)
    assert stratum.income[0] == pytest.approx(36_891.20 / 12)
    assert stratum.basket[0] == pytest.approx(15_025.00 / 12)


def test_each_shelter_flow_is_divided_by_the_share_that_pays_it(
    tmp_path: Path,
) -> None:
    """A rent published over every consumer unit is larger per renter, and the
    payment is over the mortgaged rather than over every owner."""
    inputs = read(tmp_path)
    spec = A1.population_spec(inputs, 100)
    stratum = A1.stratum_inputs(inputs, spec)
    assert stratum.rent_per_renter[0] == pytest.approx(
        (6_162.00 / 12) / 0.478
    )
    assert stratum.mortgage_per_mortgaged[0] == pytest.approx(
        (2_295.60 / 12) / 0.190
    )


def test_the_three_tenures_come_from_the_cex_and_sum_to_one(
    tmp_path: Path,
) -> None:
    inputs = read(tmp_path)
    assert "CEX" in inputs.tenure_source
    for i in range(inputs.n_strata):
        total = (inputs.renter_share[i] + inputs.mortgaged_share[i]
                 + inputs.outright_share[i])
        assert total == pytest.approx(1.0, abs=1e-6)
    assert inputs.outright_share[0] == pytest.approx(0.522 - 0.190)


def test_the_second_arm_reranks_tenure_by_net_worth(tmp_path: Path) -> None:
    """Who owns is the SCF's; what fraction of owners still owe is the CEX's."""
    inputs = read(tmp_path)
    scf = A1.with_scf_tenure(inputs)
    assert "SCF" in scf.tenure_source
    assert scf.renter_share[0] == pytest.approx(1 - 0.390550)
    owners_borrowing = 0.190 / (0.190 + (0.522 - 0.190))
    assert scf.mortgaged_share[0] == pytest.approx(
        0.390550 * owners_borrowing
    )
    for i in range(inputs.n_strata):
        total = (scf.renter_share[i] + scf.mortgaged_share[i]
                 + scf.outright_share[i])
        assert total == pytest.approx(1.0, abs=1e-6)


def test_the_two_rankings_disagree_where_the_stage_lives(tmp_path: Path) -> None:
    """The ruling of 2026-08-15, as a number rather than a sentence.

    The middle group's rent per renter is the quantity that decided it: the
    income-ranked share puts it near 1,800 a month and the wealth-ranked share
    near 6,100, which is that group's whole rent spending divided by the few of
    them who rent by wealth.
    """
    inputs = read(tmp_path)
    scf = A1.with_scf_tenure(inputs)
    cex_rent = inputs.rent_annual[1] / 12 / inputs.renter_share[1]
    scf_rent = scf.rent_annual[1] / 12 / scf.renter_share[1]
    assert cex_rent == pytest.approx(1_799, rel=0.01)
    assert scf_rent > 3 * cex_rent


# ---------------------------------------------------------------------------
# The guards on the five files
# ---------------------------------------------------------------------------
def test_an_absent_file_names_itself_rather_than_defaulting(
    tmp_path: Path,
) -> None:
    folder = processed(tmp_path)
    (folder / "dfa_shares.csv").rename(folder / "dfa_shares.csv.expired")
    with pytest.raises(A1.InputProblem) as caught:
        A1.read_inputs()
    assert "dfa_shares.csv" in str(caught.value)


def test_a_processed_file_from_an_older_fetcher_names_the_column(
    tmp_path: Path,
) -> None:
    trimmed = "\n".join(
        ",".join(line.split(",")[:5]) for line in CEX.strip().splitlines()
    ) + "\n"
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path, **{"cex_income_necessities.csv": trimmed})
    assert "homeowner" in str(caught.value)


def test_a_missing_group_is_refused_rather_than_dropped(tmp_path: Path) -> None:
    trimmed = "\n".join(
        line for line in CEX.strip().splitlines() if not line.startswith("top1")
    ) + "\n"
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path, **{"cex_income_necessities.csv": trimmed})
    assert "top1" in str(caught.value)


def test_a_missing_instrument_row_is_refused(tmp_path: Path) -> None:
    trimmed = "\n".join(
        line for line in DFA.strip().splitlines()
        if not line.startswith("home_mortgages")
    ) + "\n"
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path, **{"dfa_shares.csv": trimmed})
    assert "home_mortgages" in str(caught.value)


def test_a_ratio_that_disagrees_with_its_own_levels_is_refused(
    tmp_path: Path,
) -> None:
    """Three columns from three dates would otherwise reconcile silently."""
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path, **{"z1_ratio.csv":
             "date,home_mortgages,consumer_credit,mortgage_to_consumer_credit\n"
             "2026-01-01,13820984.0,5073031.0,2.500000\n"})
    assert "implied" in str(caught.value)


def test_a_population_share_off_its_percentile_width_is_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path, **{"scf_homeownership.csv": SCF.replace(
            "0.499984", "0.450000").replace("0.399992", "0.449976")})
    assert "percentile width" in str(caught.value)


def test_two_vintages_in_the_count_file_are_refused(tmp_path: Path) -> None:
    with pytest.raises(A1.InputProblem) as caught:
        read(tmp_path, **{"cex_consumer_units.csv": UNITS
             + "2023,133000000,133001000\n"})
    assert "one national count" in str(caught.value)


# ---------------------------------------------------------------------------
# The population size, which is an estimation setting
# ---------------------------------------------------------------------------
def test_the_strata_sizes_follow_the_published_widths(tmp_path: Path) -> None:
    inputs = read(tmp_path)
    assert A1.counts_for(inputs, 100) == (50, 40, 9, 1)
    assert A1.counts_for(inputs, 10_000) == (5_000, 4_000, 900, 100)


def test_a_size_that_empties_a_stratum_is_refused(tmp_path: Path) -> None:
    """At fifty households the top 1% rounds to nothing, and a criterion that
    compares strata would report zero rather than say it is undefined."""
    inputs = read(tmp_path)
    with pytest.raises(A1.InputProblem) as caught:
        A1.counts_for(inputs, 20)
    assert "empty stratum" in str(caught.value)


# ---------------------------------------------------------------------------
# The representative arm is the collapse and nothing else
# ---------------------------------------------------------------------------
def test_the_collapse_is_the_population_weighted_mean(tmp_path: Path) -> None:
    inputs = read(tmp_path)
    one = A1.collapse(inputs)
    assert one.n_strata == 1
    expected = sum(
        v * s for v, s in zip(inputs.income_annual, inputs.population_share,
                              strict=True)
    ) / sum(inputs.population_share)
    assert one.income_annual[0] == pytest.approx(expected)
    assert one.consumer_credit_shares == (1.0,)
    assert one.mortgage_shares == (1.0,)


def test_the_collapse_keeps_the_aggregates_it_must_not_touch(
    tmp_path: Path,
) -> None:
    """The collapse is over households. The national levels are not per
    household and collapsing them would change the arm's scale as well as its
    heterogeneity, which would stop it being a control."""
    inputs = read(tmp_path)
    one = A1.collapse(inputs)
    assert one.consumer_units == inputs.consumer_units
    assert one.credit_per_household == inputs.credit_per_household
    assert one.mortgage_to_consumer_credit == inputs.mortgage_to_consumer_credit


def test_the_representative_arm_runs_at_one_household(tmp_path: Path) -> None:
    inputs = read(tmp_path)
    labelled = A1.arms(inputs, 5_000)
    assert [label for label, _, _ in labelled] == [
        "stratified",
        "stratified:permuted",
        "stratified:scf-tenure",
        "representative:mortgaged",
        "representative:outright",
        "representative:renter",
    ]
    for label, arm, _ in labelled:
        size = A1.arm_households(arm, 5_000)
        expected = 5_000 if label.startswith("stratified") else 1
        assert size == expected, label


def test_an_arm_whose_inputs_describe_no_population_is_refused(
    tmp_path: Path,
) -> None:
    """Section 2.6's rule, as behaviour rather than as a sentence.

    The wealth-ranked arm puts the bottom half's mortgaged households on a
    payment their published disposable cannot carry alongside their published
    consumer credit. The constructor refuses, and the refusal is a finding
    about that arm's inputs rather than a crash.
    """
    from monetary_topology.cascade import CostRule

    inputs = read(tmp_path)
    with pytest.raises(A1.ArmRefused) as caught:
        A1.build_arm(A1.with_scf_tenure(inputs), 100, 0, CostRule(), None)
    assert "must not be rescaled away" in str(caught.value)


def test_the_main_arm_is_constructible_at_a_dispersion_it_supports(
    tmp_path: Path,
) -> None:
    """At the published means the bottom half's mortgaged households spend
    0.862 of their disposable on debt service, and a Beta with that mean cannot
    carry the registered 0.25. The refusal is the model's, and it is reported
    as an arm that has no population rather than swallowed."""
    from monetary_topology.cascade import CostRule

    inputs = read(tmp_path)
    with pytest.raises(A1.ArmRefused) as caught:
        A1.build_arm(inputs, 100, 0, CostRule(), None)
    assert "point masses" in str(caught.value)

    A1.DISPERSION_OVERRIDE = 0.14
    try:
        houses = A1.build_arm(inputs, 100, 0, CostRule(), None)
        assert len(houses) == 100
    finally:
        A1.DISPERSION_OVERRIDE = None


def test_a_renter_only_arm_carries_no_mortgage_stock(tmp_path: Path) -> None:
    """The allocator refuses debt where nobody can carry it, which is right in
    the stratified arm and the wrong question in this one."""
    from monetary_topology.cascade import Tenure

    inputs = read(tmp_path)
    one = A1.collapse(inputs)
    spec = A1.population_spec(one, 1)
    stratum = A1.stratum_inputs(one, spec, tenure=Tenure.RENTER)
    assert stratum.mortgage_stock_per_mortgaged == (0.0,)
    assert stratum.mortgage_per_mortgaged == (0.0,)
    assert stratum.rent_per_renter[0] > 0.0


def test_a_mortgaged_only_arm_carries_no_rent(tmp_path: Path) -> None:
    from monetary_topology.cascade import Tenure

    inputs = read(tmp_path)
    one = A1.collapse(inputs)
    spec = A1.population_spec(one, 1)
    stratum = A1.stratum_inputs(one, spec, tenure=Tenure.MORTGAGED)
    assert stratum.rent_per_renter == (0.0,)
    assert stratum.mortgage_stock_per_mortgaged[0] > 0.0


def test_an_outright_arm_carries_neither_shelter_flow(tmp_path: Path) -> None:
    from monetary_topology.cascade import Tenure

    inputs = read(tmp_path)
    one = A1.collapse(inputs)
    spec = A1.population_spec(one, 1)
    stratum = A1.stratum_inputs(one, spec, tenure=Tenure.OUTRIGHT)
    assert stratum.rent_per_renter == (0.0,)
    assert stratum.mortgage_per_mortgaged == (0.0,)
    assert stratum.disposable(0, Tenure.OUTRIGHT) == pytest.approx(
        stratum.income[0] - stratum.basket[0]
    )


# ---------------------------------------------------------------------------
# The stage cannot report itself finished while it is not
# ---------------------------------------------------------------------------
def test_the_unwritten_criteria_are_named(tmp_path: Path) -> None:
    assert A1.NOT_YET_WRITTEN, "an empty list would read as a complete stage"
    for name in ("A1-2", "A1-3", "A1-7"):
        assert any(entry.startswith(name) for entry in A1.NOT_YET_WRITTEN), name


# ---------------------------------------------------------------------------
# The permutation arm: income rank and wealth rank are not the same ranking
# ---------------------------------------------------------------------------
def test_the_coupling_has_the_margins_it_was_given(tmp_path: Path) -> None:
    table = A1.coupling(A1.POPULATION_WEIGHTS)
    for row in table:
        assert sum(row) == pytest.approx(1.0)
    for i, want in enumerate(A1.POPULATION_WEIGHTS):
        column = sum(table[w][i] * A1.POPULATION_WEIGHTS[w]
                     for w in range(len(table)))
        assert column == pytest.approx(want, abs=1e-6)


def test_the_coupling_is_the_identity_at_perfect_correlation() -> None:
    """The check that the machinery does nothing when told to do nothing."""
    table = A1.coupling(A1.POPULATION_WEIGHTS, 1.0)
    for w, row in enumerate(table):
        assert row[w] == 1.0
        assert sum(row) == 1.0


def test_the_coupling_puts_most_of_a_group_on_its_own_rank() -> None:
    table = A1.coupling(A1.POPULATION_WEIGHTS)
    assert table[0][0] > 0.7
    assert table[0][0] > table[0][1] > table[0][2] > table[0][3]
    # And the tail it exists to expose: the top 1% by wealth is mostly not in
    # the top 1% by income.
    assert table[3][3] < 0.5


def test_a_correlation_of_one_collapses_the_arm_onto_the_main_one(
    tmp_path: Path,
) -> None:
    inputs = read(tmp_path)
    same = A1.permuted(inputs, 1.0)
    for cell, (w, _) in enumerate(
        [(w, i) for w in range(4) for i in range(4)]
    ):
        if same.population_share[cell] > 0:
            assert same.income_annual[cell] == pytest.approx(
                inputs.income_annual[w]
            )


def test_the_permuted_arm_is_a_grid_of_cells_reporting_by_wealth(
    tmp_path: Path,
) -> None:
    inputs = read(tmp_path)
    arm = A1.permuted(inputs)
    assert arm.n_strata == 16
    assert arm.cell_to_group == tuple(w for w in range(4) for _ in range(4))
    assert sum(arm.population_share) == pytest.approx(1.0)
    # Each wealth group keeps its own weight.
    for w in range(4):
        weight = sum(arm.population_share[w * 4 + i] for i in range(4))
        assert weight == pytest.approx(inputs.population_share[w], abs=1e-6)


def test_the_permutation_keeps_each_wealth_groups_debt(tmp_path: Path) -> None:
    """Only who sits in the group moves; the group's aggregate does not."""
    inputs = read(tmp_path)
    arm = A1.permuted(inputs)
    for w in range(4):
        share = sum(arm.consumer_credit_shares[w * 4 + i] for i in range(4))
        assert share == pytest.approx(inputs.consumer_credit_shares[w],
                                      abs=1e-9)
        mortgages = sum(arm.mortgage_shares[w * 4 + i] for i in range(4))
        assert mortgages == pytest.approx(inputs.mortgage_shares[w], abs=1e-9)


def test_the_permutation_moves_income_across_wealth_groups(
    tmp_path: Path,
) -> None:
    """The point of the arm, as a number: a fifth of the bottom half by wealth
    holds a middle income, and the cell is built with that income."""
    inputs = read(tmp_path)
    arm = A1.permuted(inputs)
    assert arm.income_annual[0] == inputs.income_annual[0]
    assert arm.income_annual[1] == inputs.income_annual[1]
    assert arm.population_share[1] / inputs.population_share[0] > 0.15


def test_an_empty_cell_hands_its_debt_to_its_own_group(tmp_path: Path) -> None:
    shares = (0.4, 0.3, 0.2, 0.1)
    counts = (10, 0, 5, 5)
    groups = (0, 0, 1, 1)
    moved = A1.redistribute(shares, counts, groups)
    assert moved[1] == 0.0
    assert moved[0] == pytest.approx(0.7)
    assert sum(moved[2:]) == pytest.approx(0.3)
    assert sum(moved) == pytest.approx(sum(shares))


def test_an_empty_reporting_group_is_still_refused(tmp_path: Path) -> None:
    inputs = A1.permuted(read(tmp_path))
    with pytest.raises(A1.InputProblem) as caught:
        A1.counts_for(inputs, 40)
    assert "reporting group" in str(caught.value)


def test_an_empty_cell_is_allowed_where_an_empty_group_is_not(
    tmp_path: Path,
) -> None:
    inputs = A1.permuted(read(tmp_path))
    counts = A1.counts_for(inputs, 4_000)
    assert 0 in counts, "the corners of the grid should be empty at this size"
    for w in range(4):
        assert sum(counts[w * 4:(w + 1) * 4]) > 0


# ---------------------------------------------------------------------------
# The dispersion is derived from the data, not chosen
# ---------------------------------------------------------------------------
def test_the_caps_are_reported_and_not_minimised_into_a_parameter(
    tmp_path: Path,
) -> None:
    """The rule that took the minimum had no fixed point.

    Each arm brings off-diagonal cells, among them one with a more extreme
    mean, so the minimum falls monotonically as arms accumulate. It is defined
    only over a closed list of arms and this stage's list was not closed.
    """
    inputs = read(tmp_path)
    report = A1.dispersion_report(inputs, 4_000)
    assert not hasattr(A1, "common_dispersion"), (
        "the minimising rule must not still be callable"
    )
    by_label = {label: cap for label, cap, _ in report}
    assert by_label["stratified:scf-tenure"] is None
    assert by_label["stratified:permuted"] < by_label["stratified"], (
        "adding an arm can only lower the cap, which is the whole problem"
    )
    assert A1.REGISTERED_DISPERSION == 0.25


def test_the_binding_cell_is_named(tmp_path: Path) -> None:
    inputs = read(tmp_path)
    report = A1.dispersion_report(inputs, 4_000)
    for label, supported, binding in report:
        assert binding, label
        if supported is not None:
            assert "mean" in binding
