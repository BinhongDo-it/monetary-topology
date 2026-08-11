"""Unit tests for directed edges. Proofs are in ``docs/b4_directed_edges.md``.

These target the pieces the experiment composes, so a failure here localises to a
function rather than to a criterion. Hand-built examples throughout: a random
draw that happens to pass says less than a three-vertex graph whose answer can be
read off by eye.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.directed import (
    DirectedField,
    directed_square,
    from_antisymmetric,
    longest_walk,
    potential_interval,
    ray_is_valid,
    shift_breaks,
    simple_directed_cycles,
    sink_component,
    slack,
    split,
    strongly_connected_components,
    sub_potential,
    violation,
    worst_directed_cycle,
)


def triangle(a: float, b: float, c: float) -> DirectedField:
    """0 -> 1 -> 2 -> 0, one way round only. The cycle sum is ``a + b + c``."""
    return DirectedField({(0, 1): a, (1, 2): b, (2, 0): c}, 3)


# --------------------------------------------------------------------------
# construction guards
# --------------------------------------------------------------------------


def test_self_loop_rejected():
    with pytest.raises(ValueError, match="self-loop"):
        DirectedField({(0, 0): 1.0}, 2)


def test_vertex_out_of_range_rejected():
    with pytest.raises(ValueError, match="outside"):
        DirectedField({(0, 5): 1.0}, 2)


def test_value_does_not_invent_the_reverse():
    """The single most important difference from ``product_graph.Cochain``.

    That class returns ``-value(v, u)`` when only one orientation is stored.
    Doing so here would silently convert every one-way market into a two-way one,
    which is the case this module exists to keep separate.
    """
    f = DirectedField({(0, 1): 2.0}, 2)
    assert f.value(0, 1) == 2.0
    with pytest.raises(KeyError):
        f.value(1, 0)


def test_two_way_and_one_way_partition_the_edges():
    f = DirectedField({(0, 1): 1.0, (1, 0): -0.5, (1, 2): 3.0}, 3)
    assert f.two_way() == [(0, 1)]
    assert f.one_way() == [(1, 2)]


# --------------------------------------------------------------------------
# Theorem 4
# --------------------------------------------------------------------------


def test_cycles_enumerated_once_each():
    cycles = simple_directed_cycles(triangle(1.0, 1.0, 1.0))
    assert len(cycles) == 1
    assert cycles[0][0] == cycles[0][-1] == 0


def test_reverse_cycle_is_a_separate_cycle():
    """On a two-way graph each loop appears twice, once per orientation.

    Theorem 4's condition is therefore two inequalities per loop, which is what
    collapses it onto Theorem 1's equality when the field is antisymmetric. The
    complete digraph on three vertices has three two-cycles and two three-cycles,
    and the enumerator must find all five: missing an orientation would make
    ``worst_directed_cycle`` too permissive in exactly the direction that hides
    an arbitrage.
    """
    f = DirectedField(
        {(0, 1): 1.0, (1, 2): 1.0, (2, 0): 1.0,
         (0, 2): -5.0, (2, 1): -5.0, (1, 0): -5.0},
        3,
    )
    cycles = simple_directed_cycles(f)
    assert len(cycles) == 5
    lengths = sorted(len(c) - 1 for c in cycles)
    assert lengths == [2, 2, 2, 3, 3]
    three = sorted(round(f.sum_over(c), 9) for c in cycles if len(c) == 4)
    assert three == [-15.0, 3.0]


def test_positive_cycle_blocks_the_potential():
    f = triangle(1.0, 1.0, 1.0)
    phi, reason = sub_potential(f)
    assert phi is None
    assert "positive" in reason
    assert worst_directed_cycle(f)[0] == pytest.approx(3.0)


def test_negative_cycle_admits_a_potential():
    f = triangle(1.0, 1.0, -3.0)
    phi, reason = sub_potential(f)
    assert phi is not None and reason == ""
    assert violation(f, phi) <= 1e-12
    assert min(slack(f, phi).values()) >= -1e-12


def test_zero_cycle_is_the_boundary_and_admits_a_potential():
    """Theorem 4's condition is ``<= 0``, not ``< 0``. The boundary is included."""
    f = triangle(1.0, 1.0, -2.0)
    phi, _ = sub_potential(f)
    assert phi is not None
    assert violation(f, phi) <= 1e-12


def test_enumeration_and_bellman_ford_agree_on_a_hand_case():
    for c, expect_potential in ((-3.0, True), (-2.0, True), (-1.9, False)):
        f = triangle(1.0, 1.0, c)
        worst = worst_directed_cycle(f)[0]
        phi, _ = sub_potential(f)
        assert (phi is not None) == expect_potential
        assert (worst <= 1e-12) == expect_potential


# --------------------------------------------------------------------------
# Theorem 5
# --------------------------------------------------------------------------


def test_sink_component_found_and_none_when_strongly_connected():
    trap = DirectedField({(0, 1): 0.0, (1, 2): 0.0, (2, 1): 0.0}, 3)
    assert sink_component(trap) == [1, 2]

    loop = DirectedField({(0, 1): 0.0, (1, 2): 0.0, (2, 0): 0.0}, 3)
    assert len(strongly_connected_components(loop)) == 1
    assert sink_component(loop) is None


def test_the_ray_is_valid_on_a_trap():
    """The orphan currency in three vertices: 0 can enter the trap, never leave."""
    f = DirectedField({(0, 1): 0.0, (1, 2): 0.0, (2, 1): 0.0}, 3)
    phi, _ = sub_potential(f)
    assert phi is not None
    assert ray_is_valid(f, phi, [1, 2], np.array([0.0, 1.0, 1e3, 1e9])) <= 1e-6


def test_the_ray_is_not_valid_when_the_way_back_exists():
    f = DirectedField(
        {(0, 1): 0.0, (1, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}, 3
    )
    phi, _ = sub_potential(f)
    assert phi is not None
    assert shift_breaks(f, phi, [1, 2], 1e3) > 0.0


def test_interval_is_finite_iff_strongly_connected():
    loop = DirectedField({(0, 1): -1.0, (1, 2): -1.0, (2, 0): -1.0}, 3)
    lo, hi = potential_interval(loop, 0, 1)
    assert np.isfinite(lo) and np.isfinite(hi)
    assert lo <= hi + 1e-12

    trap = DirectedField({(0, 1): 0.0, (1, 2): 0.0, (2, 1): 0.0}, 3)
    lo, hi = potential_interval(trap, 0, 1)
    assert np.isfinite(lo)
    assert hi == float("inf")


def test_longest_walk_marks_unreachable_as_minus_infinity():
    f = DirectedField({(0, 1): 1.0}, 3)
    d = longest_walk(f, 0)
    assert d[0] == 0.0 and d[1] == 1.0 and d[2] == -np.inf


# --------------------------------------------------------------------------
# Theorem 6
# --------------------------------------------------------------------------


def test_split_is_the_canonical_decomposition():
    f = DirectedField({(0, 1): 1.0, (1, 0): -0.6}, 2)
    hat, bar = split(f)
    assert hat[(0, 1)] == pytest.approx(0.8)
    assert bar[(0, 1)] == pytest.approx(0.2)
    assert hat[(0, 1)] + bar[(0, 1)] == pytest.approx(f.value(0, 1))
    assert -hat[(0, 1)] + bar[(0, 1)] == pytest.approx(f.value(1, 0))


def test_split_skips_one_way_edges_rather_than_imputing_them():
    """Section 5.2: the absence is the criterion, so it must stay absent."""
    f = DirectedField({(0, 1): 1.0, (1, 0): -0.6, (1, 2): 2.0}, 3)
    hat, bar = split(f)
    assert set(hat) == {(0, 1)}
    assert set(bar) == {(0, 1)}


def test_positive_symmetric_part_is_an_arbitrage():
    """``w_bar > 0`` is a positive two-cycle, so no sub-potential may exist."""
    f = DirectedField({(0, 1): 1.0, (1, 0): 1.0}, 2)
    _, bar = split(f)
    assert bar[(0, 1)] > 0
    assert sub_potential(f)[0] is None


def test_antisymmetric_field_reduces_to_theorem_1():
    """Theorem 6(3). Every slack is zero and the potential is the exact one."""
    phi = np.array([0.0, 2.0, -1.0])
    weights = {
        (0, 1): phi[1] - phi[0],
        (1, 2): phi[2] - phi[1],
        (0, 2): phi[2] - phi[0],
    }
    f = from_antisymmetric(weights, 3)
    got, _ = sub_potential(f)
    assert got is not None
    assert max(abs(s) for s in slack(f, got).values()) <= 1e-12
    centred = got - got.min()
    assert np.allclose(centred, phi - phi.min(), atol=0, rtol=0)


# --------------------------------------------------------------------------
# section 5.1, the directed square
# --------------------------------------------------------------------------


def square_field(wa: float, wb: float, ba: float, bb: float) -> DirectedField:
    """Two classes, two positions, agent edges zero. ``ba``/``bb`` are the spreads."""
    w = {}
    for cls, (hat, bar) in enumerate(((wa, ba), (wb, bb))):
        u, v = cls * 2 + 0, cls * 2 + 1
        w[(u, v)] = hat + bar
        w[(v, u)] = -hat + bar
    for pos in range(2):
        w[(pos, 2 + pos)] = 0.0
        w[(2 + pos, pos)] = 0.0
    return DirectedField(w, 4)


def test_square_splits_into_friction_and_index():
    f = square_field(1.5, 0.4, -0.2, -0.3)
    s, s_rev = directed_square(f, 0, 1, 0, 1, 2)
    assert s + s_rev == pytest.approx(2 * (-0.2 + -0.3))
    assert s - s_rev == pytest.approx(2 * (1.5 - 0.4))


def test_common_spread_moves_the_friction_and_not_the_index():
    narrow = square_field(1.5, 0.4, -0.1, -0.1)
    wide = square_field(1.5, 0.4, -0.9, -0.9)
    s0, r0 = directed_square(narrow, 0, 1, 0, 1, 2)
    s1, r1 = directed_square(wide, 0, 1, 0, 1, 2)
    assert (s1 - r1) == pytest.approx(s0 - r0)
    assert (s1 + r1) != pytest.approx(s0 + r0)


def test_index_is_zero_when_the_classes_agree_however_wide_the_spread():
    """The case a design that reported ``S`` alone would get wrong."""
    f = square_field(1.5, 1.5, -2.0, -2.0)
    s, s_rev = directed_square(f, 0, 1, 0, 1, 2)
    assert s - s_rev == pytest.approx(0.0)
    assert s != pytest.approx(0.0)


def test_missing_agent_leg_raises_rather_than_defaulting_to_zero():
    f = square_field(1.5, 0.4, -0.2, -0.3)
    stripped = DirectedField(
        {k: v for k, v in f.weights.items() if k != (0, 2)}, 4
    )
    with pytest.raises(KeyError):
        directed_square(stripped, 0, 1, 0, 1, 2)
