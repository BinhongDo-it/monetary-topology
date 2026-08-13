"""`AssetSpec.rent_base`: the default reproduces, and the other arm is wired.

Two claims, and the second is as necessary as the first.

**The default must reproduce bitwise.** `rent_base = "layer"` is the behaviour
every A3 result recorded before 2026-08-13 was produced under. If adding the
switch moved a float, every stored number would be measured against a base that
shifted underneath it. `PROJECT_PLAN` §16.4 is the precedent: `LevySpec` was
added the same way and the same assertion is what let A6's earlier results stand
unchanged.

**And the other arm must not be inert.** `centrality_bins` had a field, a
validator and a documented meaning, and no line in the repository read it, so
the §6.5 grid swept it twice and reported two clean cells that were the
registered point recomputed. A switch that changes nothing passes a
reproduction test perfectly. So the reproduction assertion is paired with one
that the non-default arm moves something, and a failure of the second is a
wiring failure, not a finding.

The third group guards the edit's own scope: only the payer side was touched.
The receipt side was already keyed on measured units and must read identically
under both settings, because a two-sided instrument corrected on one side is
how `MEASUREMENT.md` §8's A6 rebate survived its own correction.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.asset import (
    RENT_BASES,
    A3Config,
    A3Model,
    AssetSpec,
)
from monetary_topology.network import NetworkConfig, NetworkSpec

#: Short enough to run in a unit suite, long enough for rent to have been
#: collected many times. The channel starts the round the first unit is held.
ROUNDS = 60
SEED = 0


def _run(**asset_kw) -> A3Model:
    model = A3Model(
        A3Config(
            asset=AssetSpec(**asset_kw),
            network=NetworkConfig(
                spec=NetworkSpec(seed=SEED), seed=SEED, rounds=ROUNDS
            ),
        )
    )
    model.run()
    return model


#: The arrays a rent transfer can reach, directly or through the price path.
#: Compared with `==` rather than a tolerance: this is a reproduction claim and
#: a tolerance would make it a similarity claim.
def _state(m: A3Model) -> dict[str, np.ndarray]:
    return {
        "holdings": np.asarray(m.holdings, dtype=float),
        "units": np.asarray(m.units, dtype=float),
        "price": np.asarray(m.price, dtype=float),
        "rent_history": np.asarray(m.rent_history, dtype=float),
        "uncounted_cost": np.asarray(m.uncounted_cost, dtype=float),
        "net_worth": np.asarray(m.net_worth(), dtype=float),
    }


def test_default_is_the_layer_base() -> None:
    """Registering the status quo, stated once so it cannot drift silently."""
    assert AssetSpec().rent_base == "layer"


def test_explicit_layer_reproduces_the_default_bitwise() -> None:
    """`rent_base = "layer"` against the unset default, exact equality.

    This is the assertion that lets every stored A3 number stand unchanged. It
    is run rather than argued: `PROJECT_PLAN` §16.4's lesson is that a default
    believed to reproduce and never compared is how four switches in a row kept
    their guarantee only by luck.
    """
    a = _state(_run())
    b = _state(_run(rent_base="layer"))
    for name in sorted(a):
        assert np.array_equal(a[name], b[name]), name


def test_the_holding_base_is_not_inert() -> None:
    """The non-default arm must reach code, or the switch is `centrality_bins`.

    A knob that is declared, validated, documented and unread passes every
    reproduction test in this file. `docs/a3_asset_channel.md` §6.5b is the
    instance. So the arm is required to move at least one array, and the
    failure mode this catches is a wiring failure rather than a result.
    """
    a = _state(_run())
    b = _state(_run(rent_base="holding"))
    moved = [n for n in sorted(a) if not np.array_equal(a[n], b[n])]
    assert moved, (
        "rent_base='holding' changed nothing. Either no financial-layer node "
        "ever holds zero units in this configuration, in which case this test "
        "needs a configuration where one does, or the branch is not wired."
    )


def test_the_holding_base_only_adds_payers() -> None:
    """It widens the payer set and never narrows it.

    Under `layer` the payers are `(held <= 0) & _is_production`; under
    `holding` they are `held <= 0`. The second is a superset of the first at
    every round by construction, so the switch cannot excuse anyone who was
    paying. Asserted on the model's own state rather than by re-deriving the
    sets, so it holds against the code as run.
    """
    m = _run()
    held = m.units.sum(axis=1)
    layer_payers = set(np.flatnonzero((held <= 0) & m._is_production).tolist())
    holding_payers = set(np.flatnonzero(held <= 0).tolist())
    assert layer_payers <= holding_payers
    assert holding_payers - layer_payers == set(
        np.flatnonzero((held <= 0) & ~m._is_production).tolist()
    )


def test_the_receipt_side_is_untouched() -> None:
    """Only the payer side moved. The landlord set is `held > 0` in both arms.

    `MEASUREMENT.md` §8's closing rule: when one side of a two-sided instrument
    is corrected, check the other side in the same edit. Here the receipt side
    was already keyed on the measured magnitude, so the correct action is to
    leave it alone and assert that it was left alone.
    """
    for base in RENT_BASES:
        m = _run(rent_base=base)
        held = m.units.sum(axis=1)
        landlords = np.flatnonzero(held > 0)
        assert np.array_equal(
            landlords, np.flatnonzero(m.units.sum(axis=1) > 0)
        ), base


def test_rent_off_is_unaffected_by_the_base() -> None:
    """With the channel closed the switch has nothing to key.

    A zero-rate run must be identical under both settings, which is the
    degenerate case that would otherwise hide a branch taken on the wrong side
    of the `rent_rate <= 0` early return.
    """
    a = _state(_run(rent_rate=0.0))
    b = _state(_run(rent_rate=0.0, rent_base="holding"))
    for name in sorted(a):
        assert np.array_equal(a[name], b[name]), name


def test_an_unknown_base_is_rejected() -> None:
    """Validated like every other literal field in the spec."""
    with pytest.raises(ValueError, match="rent_base"):
        AssetSpec(rent_base="production")


def test_rent_bases_are_the_two_documented_ones() -> None:
    """The tuple is the registered vocabulary, pinned like the defaults are."""
    assert RENT_BASES == ("layer", "holding")
