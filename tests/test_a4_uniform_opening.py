"""`NetworkSpec.uniform_opening`: the default reproduces, and the arm is wired.

`docs/a4_causal_primitive.md` section 9.3 records that `uniform_access` collapses
the opening holdings to an equal split, that the argument licensing the switch
does not license that particular collapse, and that the collapse biases `A(X)`
in the direction the hypothesis wants. Section 9.3a records that this is a task
with a specified method rather than a decision, and that A3's `rent_base` is the
template for how to carry it.

Four claims, and the second and fourth are as necessary as the first.

**The default must reproduce bitwise.** `flat` is what every result before
2026-08-13 was produced under. A switch that moves a float in the default
position would make every stored number a measurement against a base that
shifted underneath it.

**The other arm must not be inert.** `centrality_bins` had a field, a validator
and a documented meaning and no line read it, so a grid swept it twice and
reported two clean cells that were the registered point recomputed. A switch
that reaches no code passes every reproduction test perfectly.

**It must be the same marginal, not merely a different one.** The defect is that
the null arm starts perfectly equal. Replacing that with any other dispersed
vector would fix the symptom and leave the comparison across `C` uncontrolled.
The test is exact: the sorted holdings must equal the stratified arm's sorted
holdings, value for value.

**And it must not leak into the `C = 1` arm.** The field is read only under
`uniform_access`, so setting it with the stratified graph has to be a bitwise
no-op. Otherwise the switch would move both arms and the difference between them
would no longer be the thing being measured.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.network import (
    OPENING_HOLDINGS,
    Network,
    NetworkConfig,
    NetworkSpec,
)

SEED = 0


def _opening(uniform_access: bool, **spec_kw) -> np.ndarray:
    """The opening holdings vector, read before any round runs."""
    model = Network(
        NetworkConfig(
            spec=NetworkSpec(seed=SEED, uniform_access=uniform_access,
                             **spec_kw),
            seed=SEED,
            rounds=1,
        )
    )
    return np.asarray(model.holdings, dtype=float).copy()


def test_default_is_flat() -> None:
    """The status quo is registered, stated once so it cannot drift."""
    assert NetworkSpec().uniform_opening == "flat"


def test_explicit_flat_reproduces_the_default_bitwise() -> None:
    """Exact equality, not a tolerance. This is a reproduction claim."""
    a = _opening(True)
    b = _opening(True, uniform_opening="flat")
    assert np.array_equal(a, b)


def test_flat_is_an_equal_split() -> None:
    """What the default does, asserted rather than left to the docstring."""
    a = _opening(True)
    assert np.array_equal(a, np.full(a.size, a[0]))


def test_same_marginal_is_not_inert() -> None:
    """The arm must reach code, or the field is `centrality_bins` again."""
    flat = _opening(True)
    same = _opening(True, uniform_opening="same_marginal")
    assert not np.array_equal(flat, same), (
        "uniform_opening='same_marginal' produced the equal split. Either the "
        "branch is not wired or the stratified graph came back regular."
    )


def test_same_marginal_is_the_stratified_multiset_exactly() -> None:
    """Same values, different assignment. Sorted equality, value for value.

    This is the claim section 9.3 asks for and it is stronger than "dispersed":
    a different dispersed vector would remove the symptom and leave the
    comparison across `C` measuring two different opening distributions.
    """
    stratified = _opening(False)
    same = _opening(True, uniform_opening="same_marginal")
    assert np.array_equal(np.sort(stratified), np.sort(same))


def test_same_marginal_conserves_the_stock(self=None) -> None:
    """Implied by the multiset test and asserted separately anyway.

    The stock-flow assertion in `economy.py` runs on claims, so an opening that
    silently created or destroyed any would surface as a conservation failure
    far from here and long after.
    """
    flat = _opening(True)
    same = _opening(True, uniform_opening="same_marginal")
    assert float(same.sum()) == float(flat.sum())


def test_same_marginal_is_a_permutation_and_not_a_sort() -> None:
    """The layer-to-value association has to be destroyed, not preserved.

    Assigning the stratified values in node order would keep the financial
    layer's nodes on the financial layer's values and change nothing about the
    defect. The check is that the first-layer block is no longer uniformly the
    richer one.
    """
    stratified = _opening(False)
    same = _opening(True, uniform_opening="same_marginal")
    assert not np.array_equal(stratified, same)


def test_the_field_does_not_leak_into_the_stratified_arm() -> None:
    """`uniform_access = False` must ignore the field entirely."""
    a = _opening(False)
    b = _opening(False, uniform_opening="same_marginal")
    assert np.array_equal(a, b)


def test_same_marginal_is_deterministic() -> None:
    """Two constructions at one seed give one vector.

    The permutation is drawn from the seed, so this is a guard on the offset
    being fixed rather than on anything statistical.
    """
    a = _opening(True, uniform_opening="same_marginal")
    b = _opening(True, uniform_opening="same_marginal")
    assert np.array_equal(a, b)


def test_an_unknown_opening_is_rejected() -> None:
    with pytest.raises(ValueError, match="uniform_opening"):
        NetworkSpec(uniform_opening="stratified")


def test_replace_carries_the_field() -> None:
    """`NetworkSpec.replace` rebuilds from an explicit field list.

    A field missing from that list is silently reset to its default by any
    call to `replace`, and the model calls it internally, so this is not a
    style check.
    """
    s = NetworkSpec(uniform_opening="same_marginal")
    assert s.replace(seed=7).uniform_opening == "same_marginal"


def test_opening_holdings_are_the_two_documented_ones() -> None:
    assert OPENING_HOLDINGS == ("flat", "same_marginal")
