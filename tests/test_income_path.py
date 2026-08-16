"""The income path, which the cascade stages take from A0 rather than invent.

``docs/a1_prereg.md`` §2 and ``cascade.py``'s own list: a cascade that wrote its
own shock would answer a question about the shock. These tests are about the
three identifications that make A0's output usable as a cascade input, and about
the two refusals that keep the control arm distinguishable from a mechanism that
did nothing.
"""

from __future__ import annotations

import pytest

from monetary_topology.calibration import DFA_COUNTS
from monetary_topology.income_path import (
    MINIMUM_MOVEMENT,
    OPENING_TOLERANCE,
    PathProblem,
    PathSpec,
    describe,
    flat_path,
    retention_path,
)


def test_the_opening_round_is_exactly_one() -> None:
    """The cascade's baseline is A0's opening, not a level chosen here."""
    path = retention_path(PathSpec(periods=24))
    assert path[0] == (1.0, 1.0, 1.0, 1.0)
    assert max(abs(v - 1.0) for v in path[0]) <= OPENING_TOLERANCE


def test_the_path_has_one_entry_per_stratum_and_per_period() -> None:
    path = retention_path(PathSpec(periods=37))
    assert len(path) == 37
    assert all(len(row) == len(DFA_COUNTS) for row in path)


def test_the_same_seed_gives_the_same_path() -> None:
    a = retention_path(PathSpec(periods=12, seed=3))
    b = retention_path(PathSpec(periods=12, seed=3))
    assert a == b
    assert retention_path(PathSpec(periods=12, seed=4)) != a


def test_stretching_holds_each_round_and_keeps_the_shape() -> None:
    """The robustness arm on the one identification nothing publishes.

    A verdict that moves when the same path is stretched is a verdict about
    'one round is one month' rather than about the cascade.
    """
    quick = retention_path(PathSpec(periods=36, seed=7))
    slow = retention_path(PathSpec(periods=36, seed=7, months_per_round=3))
    assert slow[0] == slow[1] == slow[2] == quick[0]
    assert slow[3] == quick[1]
    assert slow[6] == quick[2]


def test_a_stretched_path_needs_fewer_rounds() -> None:
    assert PathSpec(periods=60, months_per_round=1).rounds() == 60
    assert PathSpec(periods=60, months_per_round=3).rounds() == 20
    assert PathSpec(periods=61, months_per_round=3).rounds() == 21


def test_the_bottom_strata_lose_and_the_top_gain() -> None:
    """A0's own K shape, at the source, and the reason A1 does not invent one.

    Read off the mechanism rather than registered as a target: this test says
    the path is not flat and not uniform, which is what makes it a shock the
    cascade can be run on at all.
    """
    path = retention_path(PathSpec(periods=48, seed=7))
    last = path[-1]
    assert last[0] < 1.0 and last[1] < 1.0
    assert last[2] > 1.0 and last[3] > 1.0
    assert last[1] < last[0], "the next 40% is not the bottom half"


def test_a_degenerate_period_count_is_refused() -> None:
    with pytest.raises(PathProblem):
        retention_path(PathSpec(periods=0))
    with pytest.raises(PathProblem):
        retention_path(PathSpec(periods=12, months_per_round=0))


def test_the_control_is_built_here_and_not_asked_of_the_mechanism() -> None:
    """A mechanism that moved nothing would otherwise be indistinguishable
    from the zero-shock arm, which is checklist item 8 on this module."""
    control = flat_path(5, 4)
    assert control == [(1.0, 1.0, 1.0, 1.0)] * 5
    assert MINIMUM_MOVEMENT > 0.0


def test_describe_names_the_period_it_shows() -> None:
    rows = describe(retention_path(PathSpec(periods=24)))
    assert rows[0][0] == 0
    assert rows[-1][0] == 23
    assert describe([]) == []
