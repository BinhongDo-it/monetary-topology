"""`NetworkConfig.injection_target`: the default reproduces, and it is the fix.

`PROJECT_PLAN.md` §16.2 registers two injection modes, topological and uniform,
and says explicitly that the contrast between them is the source's own volume 1
section 2 claim rather than an auxiliary assumption added to make A4 runnable.
Only the topological one was ever implemented, and `NetworkConfig.authority`
already defaults to `MonetaryAuthority(rule="endogenous")`, so the switch §16.2
proposed opening was already open and pointed at one node.

`experiments/a4a_domain_probe.py --probe injection` measured what that arm
delivers downstairs. Bitwise zero: about `3213` claims issued over three hundred
rounds against an opening stock of `100`, and the production layer's entire
holdings history `array_equal` to the same run with issuance off, at every seed,
with derived demand on and off.

Four claims, and each of the last three is as load-bearing as the first.

**The default must reproduce bitwise.** `top_node` is the branch every number in
this repository was produced under, so the switch has to be a rename of an
existing line rather than a reimplementation of it.

**The other arm must not be inert.** A field that reaches no code passes every
reproduction test perfectly, which is what `centrality_bins` did through two
sweeps.

**The other arm must move the thing the switch exists to move.** Non-inertness
is not enough: an arm that changed only the financial block would leave the
defect exactly where it was. The test is the one the probe ran, negated. Under
`uniform` the production layer's history must *stop* being `array_equal` to the
issuance-off run.

**And it must conserve.** Credit is a creation of claims, so the run's stock has
to grow by what the authority issued and not by a per-head rounding error times
two hundred nodes compounded over three hundred rounds.
"""

from __future__ import annotations

import numpy as np
import pytest

from monetary_topology.config import MonetaryAuthority, WageChannel
from monetary_topology.network import (
    INJECTION_TARGETS,
    Network,
    NetworkConfig,
    NetworkSpec,
)

SEED = 0
ROUNDS = 300


def _run(
    rule: str = "endogenous",
    target: str = "top_node",
    *,
    seed: int = SEED,
    rounds: int = ROUNDS,
    elasticity: float = 0.0,
):
    """One run, returning the model and its holdings history."""
    model = Network(
        NetworkConfig(
            spec=NetworkSpec(seed=seed),
            seed=seed,
            rounds=rounds,
            wages=WageChannel(elasticity=elasticity),
            authority=MonetaryAuthority(rule=rule, fixed_amount=10.0),
            injection_target=target,
        )
    )
    history = model.run()
    return model, np.asarray(history.holdings, dtype=float), history


def _prod(model: Network, holdings: np.ndarray) -> np.ndarray:
    return holdings[:, model.config.spec.layer1_size:]


def _fin(model: Network, holdings: np.ndarray) -> np.ndarray:
    return holdings[:, : model.config.spec.layer1_size]


class _Capture(Network):
    """Brackets the credit: holdings immediately before it and after it.

    `run` calls `_pre_round`, then credits, then calls `_wage_flow` before
    anything else touches `holdings`, so those two hooks are the only pair that
    brackets the credit and nothing else.

    Two things this exists to avoid. The recorded history cannot be used:
    `out["holdings"][t]` is written after the round's flows, by which time the
    credit has circulated and a per-head credit no longer looks like one. And
    differencing two runs cannot be used either, because a credit of `0.05`
    against holdings of order one loses its low bits in the subtraction, which
    is a property of the measurement and not of the credit. Bracketing inside
    one run lets the assertion be exact: it compares against the same IEEE
    operation the model performed.
    """

    def __init__(self, config: NetworkConfig) -> None:
        super().__init__(config)
        self.before: list[np.ndarray] = []
        self.after: list[np.ndarray] = []

    def _pre_round(self, t: int) -> None:
        self.before.append(self.holdings.copy())
        super()._pre_round(t)

    def _wage_flow(self):
        self.after.append(self.holdings.copy())
        return super()._wage_flow()


def _credit(target: str, rounds: int = 4) -> tuple[_Capture, int]:
    """A run bracketing its credits, and the first round that carries one.

    `rule="fixed"` so that the amount is a constant the test can name rather
    than a value the endogenous rule computed.
    """
    model = _Capture(
        NetworkConfig(
            spec=NetworkSpec(seed=SEED),
            seed=SEED,
            rounds=rounds,
            authority=MonetaryAuthority(rule="fixed", fixed_amount=10.0),
            injection_target=target,
        )
    )
    model.run()
    moved = [
        t
        for t in range(rounds)
        if not np.array_equal(model.before[t], model.after[t])
    ]
    assert moved, "no round credited anything, so there is nothing to test"
    return model, moved[0]


def test_default_is_top_node() -> None:
    """The status quo, stated once so it cannot drift."""
    assert NetworkConfig().injection_target == "top_node"


def test_injection_targets_are_the_two_documented_ones() -> None:
    assert INJECTION_TARGETS == ("top_node", "uniform")


def test_explicit_top_node_reproduces_the_default_bitwise() -> None:
    """Exact equality. This is a reproduction claim, not a tolerance."""
    _, a, _ = _run()
    _, b, _ = _run(target="top_node")
    assert np.array_equal(a, b)


def test_top_node_credits_exactly_one_node() -> None:
    """What the default does, asserted rather than left to a docstring.

    The credit is isolated at the first round that carries one, so this is a
    statement about where the money is put and not about where a round of
    circulation then takes it.
    """
    model, t = _credit("top_node")
    before, after = model.before[t], model.after[t]
    node = model.injection_node
    expected = before.copy()
    expected[node] += 10.0
    assert np.array_equal(after, expected)


def test_the_probe_result_holds_under_the_default() -> None:
    """The defect this switch exists for, asserted so it cannot quietly heal.

    Under `top_node` the production layer is bitwise indifferent to issuance.
    If this ever starts failing, something changed the downward channel and the
    switch's whole justification needs re-reading.
    """
    model, off, _ = _run(rule="none")
    _, endogenous, hist = _run(rule="endogenous")
    _, fixed, _ = _run(rule="fixed")
    assert float(np.asarray(hist.issuance).sum()) > 1000.0
    assert np.array_equal(_prod(model, endogenous), _prod(model, off))
    assert np.array_equal(_prod(model, fixed), _prod(model, off))
    assert not np.array_equal(_fin(model, endogenous), _fin(model, off))


def test_the_probe_result_holds_with_derived_demand_on() -> None:
    """`elasticity > 0` feeds back on the production layer's own spending.

    So it does not open a path from the financial layer's stock to the wage
    bill, and the bitwise result survives. Asserted because "the elasticity
    would fix it" is the first thing a reader will reach for.
    """
    model, off, _ = _run(rule="none", elasticity=0.5)
    _, on, _ = _run(rule="endogenous", elasticity=0.5)
    assert np.array_equal(_prod(model, on), _prod(model, off))


def test_uniform_is_not_inert() -> None:
    """The arm must reach code, or the field is `centrality_bins` again."""
    _, top, _ = _run(target="top_node")
    _, uni, _ = _run(target="uniform")
    assert not np.array_equal(top, uni), (
        "injection_target='uniform' reproduced the top-node run. Either the "
        "branch is not wired or the authority issued nothing."
    )


def test_uniform_moves_the_production_layer() -> None:
    """The claim the switch was written for, and it is stronger than inertness.

    Under `top_node` the production block is `array_equal` to the issuance-off
    run. Under `uniform` it must not be, or the switch has changed which node
    gets credited without changing who the credit reaches.
    """
    model, off, _ = _run(rule="none", target="uniform")
    _, on, _ = _run(rule="endogenous", target="uniform")
    assert not np.array_equal(_prod(model, on), _prod(model, off))


def test_uniform_credits_every_node_equally() -> None:
    """Per head. Not per layer, not weighted by degree, not weighted at all.

    Isolated at the credit for the same reason as the test above: by the time
    the round is recorded a per-head credit has circulated and no longer looks
    like one.
    """
    model, t = _credit("uniform")
    before, after = model.before[t], model.after[t]
    assert before.size == model._n
    assert np.array_equal(after, before + 10.0 / model._n)


def test_the_two_arms_credit_the_same_total() -> None:
    """One switch, one thing. It moves where the money lands, not how much.

    Without this the two arms could differ in the quantity issued as well, and
    every comparison across them would carry both changes at once, which is
    `MEASUREMENT.md` rule 4.
    """
    top, t_top = _credit("top_node")
    uni, t_uni = _credit("uniform")
    assert t_top == t_uni
    a = float(top.after[t_top].sum()) - float(top.before[t_top].sum())
    b = float(uni.after[t_uni].sum()) - float(uni.before[t_uni].sum())
    assert abs(a - 10.0) < 1e-9
    assert abs(b - 10.0) < 1e-9


def test_uniform_conserves_what_the_authority_issued() -> None:
    """The stock grows by the issued total, not by a per-head rounding error.

    The stock-flow assertion inside `run` compares holdings against holdings
    within a round and never sees the credit, so this is the only place the
    credited total is checked against the decided total.
    """
    model, holdings, history = _run(target="uniform")
    issued = float(np.asarray(history.issuance, dtype=float).sum())
    grown = float(holdings[-1].sum()) - model.config.initial_claims
    assert issued > 1000.0
    assert abs(grown - issued) < 1e-6


def test_uniform_with_issuance_off_reproduces_top_node_bitwise() -> None:
    """With nothing to credit the two arms are one arm.

    The branch is inside `if issued:`, so this guards that the field has no
    effect through any other path, in the same way `uniform_opening` is guarded
    against leaking into the stratified arm.
    """
    _, top, _ = _run(rule="none", target="top_node")
    _, uni, _ = _run(rule="none", target="uniform")
    assert np.array_equal(top, uni)


def test_an_unknown_target_is_rejected() -> None:
    with pytest.raises(ValueError, match="injection_target"):
        NetworkConfig(injection_target="helicopter")


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_both_results_hold_at_every_registered_seed(seed: int) -> None:
    """Five seeds, because the probe reported five and a switch justified by a
    five-seed measurement should be guarded on the same five."""
    model, off, _ = _run(rule="none", seed=seed)
    _, top, _ = _run(rule="endogenous", seed=seed, target="top_node")
    _, uni, _ = _run(rule="endogenous", seed=seed, target="uniform")
    assert np.array_equal(_prod(model, top), _prod(model, off))
    assert not np.array_equal(_prod(model, uni), _prod(model, off))
