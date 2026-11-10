"""A5 offer-unit probe: one resale draw per holding against one per unit.

**Status: diagnostic.** It scores nothing, moves no default and touches no
mechanism in ``src/``. The contrast rule lives in this file and nowhere else.

The question
------------

Resale in ``A3Model._offers`` draws once per positive ``(node, tier)`` holding at
rate ``tau``, and a holding that is drawn offers one unit. A holding of ``k``
units therefore turns its units over at ``tau / k``. The other natural rule
draws every unit on its own, so a holding of ``k`` units offers
``Binomial(k, tau)`` of them. The two agree while every holding is a single
unit, which the opening walk guarantees on the first day while
``residual_owner`` is off, as it is in stage A5, and they part as
units pile up in the same hands. ``docs/a5_reachability.md`` §8.10 records how
far apart they are by the end of stage A5's histories.

This reads stage A5 under both rules: the registered grid, the nine criteria
and who is holding at the end. Same seeds, same configuration, same code path
for everything except the draw. The two draws consume the asset stream
differently, so the arms diverge on random numbers even where the rules
coincide: under the cap every holding stays single and the trades still differ
(14.3 against 13.5 at ``rho = 0.25``). That is the floor for reading a contrast
as the rule's.

What it cannot say
------------------

Which rule describes a housing market better. That is a design question, and
A5's criteria coming back the same under both does not answer it. It says only
that A5's readings do not hang on the choice.

Usage::

    python experiments/a5b_offer_unit_probe.py
    python experiments/a5b_offer_unit_probe.py --selftest

Writes ``results/a5b_offer_unit_probe.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

import a5_reachability as a5  # noqa: E402

from monetary_topology.asset import A3Config, A3Model  # noqa: E402

RESULTS = ROOT / "results"

RULES = {
    "per_holding": "one draw per positive (node, tier) holding, one unit "
    "offered when drawn: the rule in src/monetary_topology/asset.py",
    "per_unit": "one draw per unit held, so a holding of k units offers "
    "Binomial(k, tau) of them: the contrast, defined in this file only",
}


class PerUnitOffers(A3Model):
    """The same model with the exogenous resale draw taken per unit.

    Stage A5 runs the exogenous arm only, so the forced arm is refused here
    instead of being re-implemented without a caller.
    """

    def _offers(self) -> list[tuple[int, int]]:
        spec = self.a3.asset
        if spec.arm == "forced":
            raise NotImplementedError("the contrast is defined for the exogenous arm")
        held = np.argwhere(self.units > 0)
        if held.size == 0:
            return []
        out: list[tuple[int, int]] = []
        if spec.turnover > 0.0:
            counts = self.units[held[:, 0], held[:, 1]].astype(int)
            taken = self._asset_rng.binomial(counts, spec.turnover)
            for (i, q), k in zip(held, taken, strict=True):
                out.extend([(int(i), int(q))] * int(k))
        # The parent appends one entry per round on this path, and the forced
        # arm's count is zero by construction here.
        self.forced_sales.append(0)
        return out


MODELS = {"per_holding": A3Model, "per_unit": PerUnitOffers}


def state(c: a5.Criterion) -> str:
    return (
        "diagnostic" if c.diagnostic
        else "void" if c.void
        else ("pass" if c.passed else "fail")
    )


def read(rule: str, seeds: range) -> dict[str, object]:
    """Stage A5 as its own driver reads it, with the model class swapped."""
    registered = a5.A3Model
    a5.A3Model = MODELS[rule]
    try:
        ends: dict[float, dict[str, float | None]] = {}
        grid = a5.sweep(seeds, ends)
        opening = a5.opening_table(
            seeds, tuple(sorted(set(a5.RHO_GRID) | set(a5.OPENING_FINE_GRID)))
        )
        holding = a5.who_stays(seeds, opening, ends)
        line4 = a5.a5_4(seeds)
        line7 = a5.a5_7(seeds)
        criteria = [
            a5.a5_1(grid, opening),
            a5.a5_2(grid, opening),
            a5.a5_3(grid, line4.passed),
            line4,
            a5.a5_5(seeds),
            a5.a5_6(seeds, line7.passed),
            line7,
            a5.a5_8(seeds),
            a5.a5_9(grid, seeds),
        ]
    finally:
        a5.A3Model = registered
    return {
        "grid": {str(k): v for k, v in grid.items()},
        "states": {c.name.split()[0]: state(c) for c in criteria},
        "details": {c.name.split()[0]: c.detail for c in criteria},
        "holding": holding,
    }


def planted_offers(model_class: type[A3Model]) -> int:
    """Offers from one node holding the whole stock, at ``tau = 1``.

    Three holdings and a hundred units. A draw per holding offers three; a draw
    per unit offers all hundred. The opening allocation is overwritten after
    construction, so nothing here depends on who bought what.
    """
    config = a5._config(0, a5.A5_4_START)
    asset = replace(config.asset, turnover=1.0, holding_period=1)
    model = model_class(A3Config(asset=asset, network=config.network))
    model.units[:] = 0.0
    model.units[0, :] = np.asarray(model.supply, dtype=float)
    return len(model._offers())


def selftest() -> int:
    stock = int(sum(a5._config(0, a5.A5_4_START).asset.units))
    per_holding = planted_offers(A3Model)
    per_unit = planted_offers(PerUnitOffers)
    checks = [
        ("a draw per holding offers one unit from each of three holdings", per_holding == 3),
        (f"a draw per unit offers all {stock} units at tau=1", per_unit == stock),
        ("the two rules are told apart by the planted state", per_holding != per_unit),
        # The states table has to be able to show a difference: a criterion
        # that passes under one rule and is void under the other must be listed.
        (
            "a planted difference in state is listed",
            differing({"A5-1": "pass"}, {"A5-1": "void"}) == ["A5-1"]
            and differing({"A5-1": "pass"}, {"A5-1": "pass"}) == [],
        ),
    ]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


def differing(a: dict[str, str], b: dict[str, str]) -> list[str]:
    return [k for k in a if a[k] != b[k]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=a5.REGISTERED_SEEDS)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if selftest():
        raise SystemExit("the self-test failed, so the contrast arm is not read")
    seeds = range(args.seeds)

    arms = {rule: read(rule, seeds) for rule in RULES}
    base, other = arms["per_holding"], arms["per_unit"]

    # The registered arm, read through this file's driver, has to be the stage's
    # own stored grid. If it is not, this probe is reading something else under
    # A5's name and the contrast means nothing.
    stored_path = RESULTS / "a5_reachability.json"
    matches = None
    if stored_path.exists():
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        if stored.get("seeds") == args.seeds and stored.get("rounds") == a5.ROUNDS:
            matches = stored["grid"] == json.loads(json.dumps(base["grid"]))
            if not matches:
                raise SystemExit(
                    "the registered arm does not reproduce results/"
                    "a5_reachability.json; rerun the stage before reading this"
                )

    differ = differing(base["states"], other["states"])
    print("A5 under two resale rules\n")
    for rule, text in RULES.items():
        print(f"  {rule}: {text}")
    print("\n  criterion   per holding   per unit")
    for name in base["states"]:
        print(
            f"  {name:<10}  {base['states'][name]:<12}  {other['states'][name]:<10}"
            + ("  <-- differs" if name in differ else "")
        )
    print(
        "\n  rho     share of net worth, end      trades                 "
        "production holders, end      largest holding, end"
    )
    for rho in a5.RHO_GRID:
        b, o = base["grid"][str(rho)], other["grid"][str(rho)]
        hb = base["holding"]["uncapped"][str(rho)]["end"]
        ho = other["holding"]["uncapped"][str(rho)]["end"]
        print(
            f"  {rho:<6g}  {b['share_end']:.4f} / {o['share_end']:.4f}              "
            f"{b['trades']:7.1f} / {o['trades']:7.1f}      "
            f"{b['survival']:8.4%} / {o['survival']:8.4%}         "
            f"{hb['largest_holding']:.0f} / {ho['largest_holding']:.0f}"
        )
    print(
        f"\n  {len(base['states']) - len(differ)} of {len(base['states'])} "
        f"criteria return the same state under both rules"
        + (f"; differing: {', '.join(differ)}" if differ else "")
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "a5b_offer_unit_probe.json"
    out.write_text(
        json.dumps(
            {
                "stage": "A5b",
                "diagnostic_only": True,
                "diagnostic_reason": (
                    "a contrast arm under a resale rule the model does not "
                    "use; stage A5's own readings are in a5_reachability.json"
                ),
                "config": {
                    "seeds": args.seeds,
                    "rounds": a5.ROUNDS,
                    "rho_grid": list(a5.RHO_GRID),
                    "rules": RULES,
                },
                "registered_arm_matches_stored_record": matches,
                "states": {
                    name: {rule: arms[rule]["states"][name] for rule in RULES}
                    for name in base["states"]
                },
                "states_that_differ": differ,
                "arms": arms,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
