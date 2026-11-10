"""Which terms admit a node to the pool that prices a tier.

A3 P-C splits the terms in two: what is paid, and what admits. The price of a
tier follows the claims of its bidder pool, and the model admits to that pool on
the **payment** terms. So the cell that levels the payment terms also levels
the pricing pool, and the cell that levels the gate terms leaves it dispersed.
``pricing_pool`` counts where the pool as run parts from the pool the gate
terms would give, and these tests give it a case small enough to do by hand.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments import a3c_load_bearing as C  # noqa: E402


def by_hand(prices=((2.375,), (0.875,)), pool_0=(4.0,)) -> SimpleNamespace:
    """Three nodes, one tier, opening price one, no stretch, elasticity one.

    Payment terms 1, 2, 4 and gate terms 2, 2, 2. On opening claims of
    1.5, 2.5, 3.0 the payment terms admit the first two (pool 4.0) and the gate
    terms the last two (pool 5.5).
    """
    spec = SimpleNamespace(initial_price=(1.0,), stretch=1.0, open_tiers=(),
                           elasticity=1.0)
    return SimpleNamespace(
        a3=SimpleNamespace(asset=spec),
        terms=np.array([[1.0], [2.0], [4.0]]),
        terms_gate=np.array([[2.0], [2.0], [2.0]]),
        # round one: everyone clears both, pools 9.5 and 9.5
        # round two: payment admits nodes 0, 1 (3.5); gate admits 1, 2 (5.5)
        claims_history=[np.array([2.0, 2.5, 5.0]), np.array([1.0, 2.5, 3.0])],
        price_history=[np.array(p) for p in prices],
        _pool_0=np.array(pool_0),
    )


OPENING = np.array([1.5, 2.5, 3.0])


def test_the_pool_as_run_is_the_payment_terms_pool() -> None:
    got = C.pricing_pool(by_hand(), OPENING)
    assert got["opening_node_tiers"] == 2          # nodes 0 and 2 swap places
    assert got["rounds"] == 1                      # only the second round differs
    assert got["node_tier_rounds"] == 2
    # round one: 9.5 / 4.0 = 2.375 as run against 9.5 / 5.5 from the gate pool
    assert got["largest_relative_price_gap"] == pytest.approx(
        (2.375 - 9.5 / 5.5) / 2.375, abs=1e-8)
    assert got["as_run_reproduces_the_recorded_pool"] is True
    assert got["as_run_reproduces_the_recorded_prices"] is True


def test_the_instrument_says_so_when_it_is_not_reading_the_run() -> None:
    """Hand it prices and an opening pool formed on the gate terms: the pool it
    rebuilds from the payment terms is then not the run's, and it has to say so
    and not print a table against something the run never did."""
    other = by_hand(prices=((9.5 / 5.5,), (1.0,)), pool_0=(5.5,))
    got = C.pricing_pool(other, OPENING)
    assert got["as_run_reproduces_the_recorded_pool"] is False
    assert got["as_run_reproduces_the_recorded_prices"] is False


def test_tied_terms_give_one_pool() -> None:
    model = by_hand()
    model.terms_gate = model.terms
    got = C.pricing_pool(model, OPENING)
    assert (got["opening_node_tiers"], got["rounds"], got["node_tier_rounds"]) == (
        0, 0, 0)
    assert got["largest_relative_price_gap"] == 0.0


@pytest.fixture(scope="module")
def one_seed():
    seeds = range(1, 2)
    models, _population, _devs = C.build_all(seeds, C.REGISTERED_ROUNDS)
    return C.pricing_pools(seeds, C.REGISTERED_ROUNDS, models)


def test_the_registered_cells_at_one_seed(one_seed) -> None:
    cells = one_seed["by_cell"]
    # the two cells with tied terms have one pool, by construction
    for name in ("both", "null"):
        assert cells[name]["node_tier_rounds"] == 0
        assert cells[name]["largest_relative_price_gap"] == 0.0
    # levelling the gate leaves the pricing pool on the dispersed payment terms
    gate_levelled = cells["H1_only"]["by_seed"][0]
    assert gate_levelled["opening_node_tiers"] == 6
    assert (gate_levelled["rounds"], gate_levelled["node_tier_rounds"]) == (64, 194)
    # levelling the payment terms levels the pricing pool with them
    pay_levelled = cells["H0_only"]["by_seed"][0]
    assert pay_levelled["opening_node_tiers"] == 0
    assert (pay_levelled["rounds"], pay_levelled["node_tier_rounds"]) == (150, 674)
    assert pay_levelled["largest_relative_price_gap"] == pytest.approx(
        0.05257863, abs=1e-8)
    single = one_seed["single_channel_cells"]
    assert (single["runs"], single["rounds"], single["node_tier_rounds"]) == (
        2, 214, 868)
    assert single["largest_at"] == {"cell": "H0_only", "seed": 1}
    assert one_seed["instrument_reproduces_the_run"] is True


def test_construct_is_build_before_the_run() -> None:
    kw = {**C.FIXED, **C.CELLS["H1_only"]}
    fresh = C.construct(1, 5, **kw)
    assert fresh.claims_history == [] and fresh.price_history == []
    ran = C.build(1, 5, **kw)
    assert len(ran.claims_history) == 5
    # the opening pool the run was priced from is formed on these claims
    assert np.array_equal(fresh._pool_0, ran._pool_0)

# ---------------------------------------------------------------------------
# the same cells with the pool on the gate terms
# ---------------------------------------------------------------------------


def test_with_tied_terms_the_two_models_are_one_model() -> None:
    kw = {**C.FIXED, **C.CELLS["both"]}
    registered = C.build(2, 40, **kw)
    other = C.build(2, 40, _model=C.GatePooled, **kw)
    assert type(other) is C.GatePooled
    assert np.array_equal(registered.net_worth(), other.net_worth())
    assert np.array_equal(registered._pool_0, other._pool_0)


def test_the_other_model_prices_from_the_gate_terms_pool() -> None:
    kw = {**C.FIXED, **C.CELLS["H1_only"]}
    registered = C.construct(1, 5, **kw)
    other = C.construct(1, 5, _model=C.GatePooled, **kw)
    # same opening allocation, so the same claims, and two different pools
    assert np.array_equal(registered.holdings, other.holdings)
    assert not np.allclose(registered._pool_0, other._pool_0)
    assert C._on_the_gate_terms(other, other.holdings)
    assert not C._on_the_gate_terms(registered, registered.holdings)
    assert registered._pool_0[0] == pytest.approx(78.554699, abs=1e-6)
    assert other._pool_0[0] == pytest.approx(76.760796, abs=1e-6)


def test_the_comparison_arm_at_one_seed() -> None:
    seeds = range(1, 2)
    models, population, _devs = C.build_all(seeds, C.REGISTERED_ROUNDS)
    baseline, _ = C.build_baseline(seeds, C.REGISTERED_ROUNDS)
    registered = {
        n: C.summarise(n, kw, seeds, models, baseline, population)
        for n, kw in C.CELLS.items()
    }
    got = C.pool_on_gate_terms(seeds, C.REGISTERED_ROUNDS, registered)
    assert got["tied_cells_reproduce_the_registered_run"] is True
    assert got["pool_is_on_the_gate_terms"] is True
    cells = got["cells"]
    assert cells["both"]["gap_by_seed"] == [
        round(registered["both"]["gap_by_seed"][0], 6)]
    assert cells["null"]["gap_by_seed"] == [0.0]
    # the two single-channel cells are where the pool rule can show
    assert cells["H1_only"]["gap_by_seed"][0] != round(
        registered["H1_only"]["gap_by_seed"][0], 6)
    assert cells["H1_only"]["gap_by_seed"][0] == pytest.approx(23.95, abs=0.01)
    assert cells["H0_only"]["gap_by_seed"][0] == pytest.approx(1.54, abs=0.01)
    # hand it a registered arm that is not this one and the flag has to drop
    wrong = {n: dict(c) for n, c in registered.items()}
    wrong["both"] = dict(wrong["both"], gap_by_seed=[0.0])
    assert C.pool_on_gate_terms(seeds, C.REGISTERED_ROUNDS, wrong)[
        "tied_cells_reproduce_the_registered_run"] is False


def test_the_arm_says_so_when_it_ran_on_the_registered_pool(monkeypatch) -> None:
    """Swap the registered model in under the comparison arm's name. The cells
    then run on the payment-terms pool, and the arm's own check has to report
    that it was not priced from the gate terms."""
    seeds = range(1, 2)
    models, population, _devs = C.build_all(seeds, 60)
    baseline, _ = C.build_baseline(seeds, 60)
    registered = {
        n: C.summarise(n, kw, seeds, models, baseline, population)
        for n, kw in C.CELLS.items()
    }
    assert C.pool_on_gate_terms(seeds, 60, registered)[
        "pool_is_on_the_gate_terms"] is True
    monkeypatch.setattr(C, "GatePooled", C.A3Model)
    assert C.pool_on_gate_terms(seeds, 60, registered)[
        "pool_is_on_the_gate_terms"] is False
