"""The registered re-check: what empties the production layer of holders.

**Status: diagnostic, not a registered criterion.** It scores nothing, moves no
threshold, writes no file and touches no mechanism. `docs/a3_asset_channel.md`
§6.4c leaves one question open and this is it.

The question
------------

At the registered shock round of 150, `production_layer_with_asset` is empty in
**every** arm §6.4c ran, including with rent fully off. So rent is not what
strips the production layer of its units before the transfer lands, and §6.4c
records that whatever does it was not identified. That is the only open item
that could still move A3's conclusions, because it is the reason the shape
§16.1 wanted cannot be measured at the criterion's own shock round.

Two candidates, and they predict different series
-------------------------------------------------

Turnover is exogenous at `τ = 0.04`, so roughly four percent of held units come
back to the market each round whoever holds them, and a holder that never wins
one back decays with a half-life near `ln 2 / 0.04 ≈ 17` rounds. That matches
the counts §6.4c reports, `21/27/19` at round one down to `0/0/0` at 150. So the
units leave by construction. **The question is why none come back**, and there
are two answers with different fingerprints.

*The wall.* The price rises, the gate is `claims ≥ γ·P`, and production-layer
claims stop clearing it. Then the count of production nodes that could buy at
the current price goes to zero **before** their unit count does, and after that
the auction is irrelevant because they cannot enter it.

*The auction.* They can still clear the gate but lose every time, because the
bidder pool is claims-weighted and the financial layer holds far more claims.
Then the clearing count stays **positive** while units go to zero.

The two are distinguishable from one run with no counterfactual, which is why
this reads series rather than sweeping a parameter. The rent-off arm is carried
alongside only to say whether rent is what drains the claims that the gate is
read against; §6.4c has already shown rent is not what empties the layer.

Nothing here changes the model. The recording is a wrapper around
`_post_round` that calls the original first and then reads public state, in the
same spirit as `_shock_trace`'s hook.

Run
---

    python experiments/a3f_who_empties_downstairs.py
    python experiments/a3f_who_empties_downstairs.py --seeds 5 --rounds 300
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    A3Config,
    A3Model,
    AssetSpec,
    gate_clears,
    soft_gate,
)
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402

#: Fixed order, so the printed report does not depend on dict iteration.
ARMS = (
    ("registered", {}),
    ("rent-off", {"rent_rate": 0.0}),
)

#: Rounds the table is read at. The first is the opening, the middle four are
#: the counts §6.4c quotes, and 150 is A3-6's registered shock round.
MARKS = (1, 10, 20, 40, 80, 150, 299)


def trace(seed: int, rounds: int, **asset_kw) -> dict[str, np.ndarray]:
    """One run, recording per round what the two candidates disagree about."""
    spec = AssetSpec(**asset_kw)
    model = A3Model(
        A3Config(
            asset=spec,
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds
            ),
        )
    )
    prod = np.asarray(model._is_production, dtype=bool)
    rec: dict[str, list[float]] = {
        k: [] for k in ("prod_units", "fin_units", "prod_holders",
                        "prod_hard", "prod_soft", "price0", "prod_claims")
    }
    original = model._post_round

    def hook(t: int, _m=model, _p=prod, _o=original, _s=spec) -> None:
        _o(t)
        units = np.asarray(_m.units, dtype=float)
        held = units.sum(axis=1)
        hard = gate_clears(_m.holdings, _m.terms, _m.price, _s.open_tiers)
        soft, _stretched = soft_gate(
            _m.holdings, _m.terms, _m.price, _s.stretch, _s.open_tiers
        )
        rec["prod_units"].append(float(units[_p].sum()))
        rec["fin_units"].append(float(units[~_p].sum()))
        rec["prod_holders"].append(float((held[_p] > 0).sum()))
        rec["prod_hard"].append(float(hard[_p, 0].sum()))
        rec["prod_soft"].append(float(soft[_p, 0].sum()))
        rec["price0"].append(float(_m.price[0]))
        rec["prod_claims"].append(float(_m.holdings[_p].sum()))

    model._post_round = hook  # type: ignore[method-assign]
    model.run()
    return {k: np.array(v, dtype=float) for k, v in rec.items()}


def first_zero(a: np.ndarray) -> float:
    """First index from which the series is zero and stays zero, else nan."""
    nz = np.flatnonzero(a > 0)
    if nz.size == 0:
        return 0.0
    last = int(nz[-1])
    return float(last + 1) if last + 1 < a.size else float("nan")


def first_touch(a: np.ndarray) -> float:
    """First index at which the series is zero at all, else nan.

    **Read this one for the gates and `first_zero` for the units.** A node that
    sells its last unit holds the proceeds for a round, and proceeds can lift it
    back over `γ·P / s` for exactly that round, so the soft gate's *stays zero*
    round is one past the units' by construction rather than by finding. The
    round the gate **first** shuts is the quantity the two candidate
    explanations disagree about; the round it stops flickering is not.
    """
    z = np.flatnonzero(a <= 0)
    return float(z[0]) if z.size else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=300)
    args = ap.parse_args()

    print("=" * 78)
    print("What empties the production layer of holders, and why none come back")
    print(f"  {args.seeds} seeds, {args.rounds} rounds. Diagnostic; scores "
          f"nothing.")
    print("=" * 78)

    for name, kw in ARMS:
        runs = [trace(s, args.rounds, **kw) for s in range(args.seeds)]
        mean = {k: np.mean([r[k] for r in runs], axis=0) for k in runs[0]}
        print(f"\n{'-' * 78}\narm {name}"
              + (f"  {kw}" if kw else "  (the registered parameters)"))
        print("\n  round   prod units  fin units  prod holders   can buy"
              "  can stretch   price0")
        for t in MARKS:
            if t >= mean["prod_units"].size:
                continue
            print(f"  {t:>5}   {mean['prod_units'][t]:10.2f}"
                  f" {mean['fin_units'][t]:10.2f}"
                  f" {mean['prod_holders'][t]:13.2f}"
                  f" {mean['prod_hard'][t]:9.2f}"
                  f" {mean['prod_soft'][t]:12.2f}"
                  f" {mean['price0'][t]:8.3f}")

        # Per seed, because a mean over five seeds can put a zero where no seed
        # had one and the whole reading is about which series reaches zero
        # first.
        print("\n  per seed. Units: the round from which the layer holds "
              "nothing and keeps\n  holding nothing. Gates: the round each "
              "first shuts, which is the quantity\n  the two explanations "
              "disagree about (see `first_touch`).")
        print("    seed   units empty   hard gate shuts   soft gate shuts"
              "   soft stays shut")
        for i, r in enumerate(runs):
            print(f"    {i:>4}   {first_zero(r['prod_units']):11.0f}"
                  f"   {first_touch(r['prod_hard']):15.0f}"
                  f"   {first_touch(r['prod_soft']):15.0f}"
                  f"   {first_zero(r['prod_soft']):15.0f}")

        u = np.array([first_zero(r["prod_units"]) for r in runs])
        h = np.array([first_touch(r["prod_hard"]) for r in runs])
        s = np.array([first_touch(r["prod_soft"]) for r in runs])
        print(f"\n    the hard gate shut before the units ran out in "
              f"{int(np.sum(h < u))} of {len(runs)} seeds")
        print(f"    the soft gate shut before the units ran out in "
              f"{int(np.sum(s < u))} of {len(runs)} seeds")
        print(f"    median rounds between the soft gate shutting and the "
              f"units running out: {np.median(u - s):.0f}")
        print("    A wall predicts the gates shutting first and the units "
              "draining afterwards\n    at the turnover rate. An auction "
              "predicts the gates still open while the\n    units go.")

    print(f"\n{'=' * 78}")
    print("  Not scored. No threshold is registered for any of it, and nothing")
    print("  here reaches a criterion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
