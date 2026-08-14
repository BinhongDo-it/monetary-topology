"""A4 decision probe: can §10's discriminant be computed, and on whom?

**Status: diagnostic, not a registered criterion.** It scores nothing, moves no
threshold, writes no file and touches no mechanism. It exists because a design
ruling was about to be taken on three claims nobody had measured.

The fork it was built for
-------------------------

`docs/a4_causal_primitive.md` §10 registers `routed(X | C)` as A4's discriminant
and defines it on `a3c_load_bearing.py`'s divergence measure `D`, which needs
`κ_pay` and `κ_gate`. Those are `AssetSpec.terms_spread` and
`AssetSpec.gate_spread`. `A4Model` is a subclass of `Network` with no asset
layer, so as things stand §10 is registered against a class that cannot compute
it. Either A4 is reparented onto `A3Model` (甲) or §10 is set aside and A4 runs
on §4's Gini ratio with §16.2's injection (丙).

Three claims decide it and each is checkable in a few minutes.

1. **§10.2's population, intersected with §10.2's own stock constraint.** §10
   inherits A3c's paired population, the agents completing a round trip in every
   cell. §10.2 separately requires A4 be restricted to agents holding a stock.
   Nobody had taken the intersection.

2. **§10.3's window.** §10.3 moves A4's window to roughly rounds ten to forty,
   on the reasoning that the production layer's units survive to rounds 55-110
   even though its gate shuts on round 3, so an earlier window catches it still
   holding. That reasoning is about *units*, and the paired population is
   defined by *selling*. Whether the window does what it was written to do is a
   count.

3. **What `D` is made of under `C = 0`.** §10.1 argues that the holonomy `A(X)`
   has a structurally zero denominator under `C = 0` and that `routed(X | C)`
   avoids it. But `D` is a central-minus-peripheral tercile difference *by
   centrality*, and §10's own premise is that `uniform_access` gives a
   centrality spread of exactly zero. Whether the replacement inherited the
   defect it was written to remove is a comparison of arrays.

Why `cycles` is the hinge
-------------------------

`asset.py` increments `cycles[seller]` when a unit that was bought is sold, so
`cycles > 0` reads **has completed a round trip**, which is **has sold**. Upstairs
the gate stays open, so a financial-layer node sells and buys back and satisfies
`cycles > 0` and `held > 0` at once. Downstairs the gate shuts between rounds 3
and 15 (`a3_asset_channel.md` §6.4d), so selling is one-way: a production-layer
node that has sold cannot re-enter, and one that still holds has not sold. The
two conditions are close to mutually exclusive downstairs, and that is a fact
about the gate rather than about the horizon, which is why moving the window
cannot repair it.

What is reported
----------------

`--probe domain` prints, per horizon and seed, the size of the paired
population, of the holding population, of their intersection, and how much of
each sits in the financial layer, with the centrality percentile band of each.

`--probe spread` prints the cross-sectional spread of centrality and of the
terms matrix in both `C` arms. The terms spread is taken **per tier**:
`terms` is `(n, Q)` and `base_terms` differs by tier, so the range over the
whole matrix is the tier ladder and says nothing about dispersion across nodes.
This module got that wrong once before it was written down.

`--probe cells` compares A3c's four `κ` cells against the null, array by array,
in both `C` arms. Bitwise equality is the statistic, since the question is
whether the cells are distinct configurations or one configuration executed
four times.

A fourth claim, added after the ruling
--------------------------------------

The ruling went to 丙, which takes A4's stock from `PROJECT_PLAN` §16.2's
injection instead of from A3's asset layer. §16.2 describes that as opening a
switch that already exists. The same question therefore applies to it: what
position is the switch in now, and does moving it reach anyone.

`NetworkConfig.authority` defaults to `MonetaryAuthority(rule="endogenous")`,
not to `"none"`, so the switch is already open and every A0, A2, A3 and A4
number was produced with issuance running. The credit goes to
`self.injection_node`, one node, the financial-layer node of highest in-degree.
The only downward channel is `WageChannel.bill`, an **absolute** per-round flow
whose elasticity feeds back on the production layer's *own* spending rather than
on the financial layer's stock. So whether any amount of issuance reaches the
production layer is a bitwise comparison, and that is what `--probe injection`
asks. §16.2's registered deliverable, the injection amount at which `A(X)`
crosses one, presupposes the answer is yes.

Cost
----

Roughly two hundred and fifty model builds at the default settings, no writes,
no git.
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
)
from monetary_topology.config import (  # noqa: E402
    MonetaryAuthority,
    WageChannel,
)
from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkSpec,
)

REGISTERED_SEEDS = 5

#: A3c's registered dispersion and its mean-cost reference. Copied rather than
#: imported because importing an experiment from an experiment would make this
#: file's numbers depend on that file's CLI defaults.
KAPPA = 1.0

#: A3c's crossing of payment dispersion with gate dispersion, verbatim.
CELLS: dict[str, dict] = {
    "both": {"terms_spread": KAPPA, "gate_spread": KAPPA},
    "H1_only": {"terms_spread": KAPPA, "gate_spread": 0.0},
    "H0_only": {"terms_spread": 0.0, "gate_spread": KAPPA},
    "null": {"terms_spread": 0.0, "gate_spread": 0.0},
}

#: A3c's fixed block, verbatim. A3b's corrections are in.
FIXED = {
    "hold_mean_cost": True,
    "mean_cost_reference": KAPPA,
    "units_per_node": 1.1,
    "residual_owner": True,
    "proceeds": "seller",
}

#: Horizons for the domain probe. The first three bracket §10.3's window, the
#: last two are A3-6's shock round and A3c's registered horizon.
HORIZONS: tuple[int, ...] = (10, 20, 40, 150, 300)


def build(
    seed: int,
    rounds: int,
    *,
    uniform: bool = False,
    opening: str | None = None,
    **asset_kw,
) -> A3Model:
    """One run. ``opening`` defaults to the fix registered for the `C = 0` arm.

    Under `C = 1` the field is not read at all, so passing it there is a
    no-op asserted by ``tests/test_a4_uniform_opening.py``; it is passed anyway
    so that the two arms are constructed by one code path.
    """
    if opening is None:
        opening = "same_marginal" if uniform else "flat"
    model = A3Model(
        A3Config(
            asset=AssetSpec(**asset_kw),
            network=NetworkConfig(
                spec=NetworkSpec(
                    seed=seed,
                    uniform_access=uniform,
                    uniform_opening=opening,
                ),
                seed=seed,
                rounds=rounds,
            ),
        )
    )
    model.run()
    return model


def band(values: np.ndarray, pick: np.ndarray) -> str:
    """Percentile band of ``pick`` inside ``values``.

    The unit `a3_asset_channel.md` §5.3 reports in, so that the number here can
    be set beside the number there without conversion.
    """
    if pick.size == 0:
        return "empty"
    ranks = [100.0 * float((values < values[i]).mean()) for i in pick]
    return f"[{min(ranks):.1f}, {max(ranks):.1f}]"


def probe_domain(seeds: int) -> None:
    """Claims 1 and 2: who is in the intersection, at five horizons."""
    print("\nPROBE 1-2  the population §10 can compute `routed` on")
    print(
        "  Paired population is `cycles > 0` in every cell, as `a3c_load_"
        "bearing.py`.\n  Holding population is `units.sum(axis=1) > 0` in the "
        "`both` cell."
    )
    for rounds in HORIZONS:
        print(f"\n  --- horizon {rounds} rounds ---")
        print(
            "   seed  traders  (fin)  holders  (fin)  both  (fin)"
            "   trader band        both band"
        )
        agg = []
        for seed in range(seeds):
            models = {
                name: build(seed, rounds, **FIXED, **kw)
                for name, kw in CELLS.items()
            }
            both_cell = models["both"]
            n = both_cell._n
            shared = np.ones(n, dtype=bool)
            for m in models.values():
                shared &= m.cycles > 0
            held = np.asarray(both_cell.units).sum(axis=1) > 0
            fin = np.zeros(n, dtype=bool)
            fin[: both_cell.a3.network.spec.layer1_size] = True

            traders = np.flatnonzero(shared)
            holders = np.flatnonzero(held)
            overlap = np.flatnonzero(shared & held)
            row = (
                traders.size,
                int(fin[traders].sum()),
                holders.size,
                int(fin[holders].sum()),
                overlap.size,
                int(fin[overlap].sum()),
            )
            agg.append(row)
            print(
                f"   {seed:4d}  {row[0]:7d}  {row[1]:5d}  {row[2]:7d}"
                f"  {row[3]:5d}  {row[4]:4d}  {row[5]:5d}"
                f"   {band(both_cell.centrality, traders):>16s}"
                f"  {band(both_cell.centrality, overlap):>16s}"
            )
        a = np.array(agg, dtype=float).mean(axis=0)
        print(
            f"   mean  {a[0]:7.1f}  {a[1]:5.1f}  {a[2]:7.1f}  {a[3]:5.1f}"
            f"  {a[4]:4.1f}  {a[5]:5.1f}"
        )
        if a[4] > 0.0 and a[4] == a[5]:
            print(
                "   every agent in the intersection is in the financial layer, "
                "at every seed"
            )


def probe_spread(seeds: int, rounds: int) -> None:
    """Claim 3, first half: is the centrality spread under `C = 0` zero."""
    print("\nPROBE 3a  what the terciles are taken on, in each `C` arm")
    print(
        "   The count columns are the same three as probe 1-2, at one cell"
        " rather than\n   intersected, and they carry §9.3's fix: the flat"
        " opening is shown beside the\n   fixed one so the size of that defect"
        " in this arm is visible rather than argued."
    )
    print(
        "   arm                        centrality spread   terms spread"
        "   traders  holders   both"
    )
    for label, uniform, opening in (
        ("C=1 stratified", False, "flat"),
        ("C=0 uniform, flat opening", True, "flat"),
        ("C=0 uniform, same_marginal", True, "same_marginal"),
    ):
        cs, ts, tr, ho, bo = [], [], [], [], []
        for seed in range(seeds):
            m = build(
                seed,
                rounds,
                uniform=uniform,
                opening=opening,
                **FIXED,
                **CELLS["both"],
            )
            c = np.asarray(m.centrality, dtype=float)
            cs.append(float(c.max() - c.min()))
            t = np.asarray(m.terms, dtype=float)
            ts.append(float((t.max(axis=0) - t.min(axis=0)).max()))
            held = np.asarray(m.units).sum(axis=1) > 0
            tr.append(int((m.cycles > 0).sum()))
            ho.append(int(held.sum()))
            bo.append(int(((m.cycles > 0) & held).sum()))
        print(
            f"   {label:26s}  {np.mean(cs):.6e}   {np.mean(ts):.6e}"
            f"  {np.mean(tr):7.1f}  {np.mean(ho):7.1f}  {np.mean(bo):5.1f}"
        )


def probe_cells(seeds: int, rounds: int) -> None:
    """Claim 3, second half: are the four cells distinct under `C = 0`."""
    print("\nPROBE 3b  are A3c's four cells four configurations or one")
    for label, uniform in (("C = 1 stratified", False), ("C = 0 uniform", True)):
        print(f"\n   {label}")
        print(
            "    seed  cell      terms  gate   holdings  net_worth"
            "   (== the null, bitwise)"
        )
        for seed in range(seeds):
            ref = build(seed, rounds, uniform=uniform, **FIXED, **CELLS["null"])
            for name in ("both", "H1_only", "H0_only"):
                m = build(seed, rounds, uniform=uniform, **FIXED, **CELLS[name])
                eq = [
                    np.array_equal(m.terms, ref.terms),
                    np.array_equal(m.terms_gate, ref.terms_gate),
                    np.array_equal(m.holdings, ref.holdings),
                    np.array_equal(m.net_worth(), ref.net_worth()),
                ]
                print(
                    f"    {seed:4d}  {name:8s}"
                    + "".join(f"  {str(v):>6s}" for v in eq)
                )


def _plain(seed: int, rule: str, rounds: int, elasticity: float = 0.0):
    """One ordinary A2 run at a given issuance rule. No asset layer."""
    model = Network(
        NetworkConfig(
            spec=NetworkSpec(seed=seed),
            seed=seed,
            rounds=rounds,
            wages=WageChannel(elasticity=elasticity),
            authority=MonetaryAuthority(rule=rule, fixed_amount=10.0),
        )
    )
    history = model.run()
    return (
        model,
        np.asarray(history.issuance, dtype=float),
        np.asarray(history.holdings, dtype=float),
    )


def probe_injection(seeds: int, rounds: int) -> None:
    """Claim 4: does issuance reach anyone outside the financial layer."""
    print("\nPROBE 4  the issuance switch, as it stands")
    print(
        f"  {rounds} rounds, `initial_claims = 100.0`, `WageChannel.bill = 8.0`"
        " per round."
    )
    print(
        "\n   rule          issued    final total   fin share   prod share"
        "   prod median   prod max"
    )
    for rule in ("endogenous", "fixed", "none"):
        rows = []
        for seed in range(seeds):
            model, issuance, holdings = _plain(seed, rule, rounds)
            final = holdings[-1]
            k = model.config.spec.layer1_size
            rows.append(
                (
                    float(issuance.sum()),
                    float(final.sum()),
                    float(final[:k].sum() / final.sum()),
                    float(final[k:].sum() / final.sum()),
                    float(np.median(final[k:])),
                    float(final[k:].max()),
                )
            )
        a = np.array(rows).mean(axis=0)
        print(
            f"   {rule:12s}  {a[0]:8.1f}  {a[1]:12.1f}  {a[2]:10.1%}"
            f"  {a[3]:11.1%}  {a[4]:12.5f}  {a[5]:9.3f}"
        )

    print(
        "\n   The production block's whole holdings history, against `none`."
        "\n   Bitwise, because the question is whether the knob reaches the code"
        " at all.\n"
    )
    print(
        "   seed   elasticity   prod == none   fin == none"
        "   issued under endogenous"
    )
    for elasticity in (0.0, 0.5):
        for seed in range(seeds):
            model, _, base = _plain(seed, "none", rounds, elasticity)
            _, issued, endo = _plain(seed, "endogenous", rounds, elasticity)
            _, _, fixed = _plain(seed, "fixed", rounds, elasticity)
            k = model.config.spec.layer1_size
            prod = np.array_equal(endo[:, k:], base[:, k:]) and np.array_equal(
                fixed[:, k:], base[:, k:]
            )
            fin = np.array_equal(endo[:, :k], base[:, :k])
            print(
                f"   {seed:4d}   {elasticity:10.1f}   {str(prod):>12s}"
                f"   {str(fin):>11s}   {issued.sum():23.1f}"
            )

    print(
        "\n   the injection point: one node, chosen by in-degree inside layer 1"
    )
    for seed in range(seeds):
        model, _, _ = _plain(seed, "endogenous", rounds)
        print(
            f"     seed {seed}: injection_node = {model.injection_node}"
            f" of {model._n} nodes, layer1_size ="
            f" {model.config.spec.layer1_size}"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument(
        "--rounds",
        type=int,
        default=40,
        help="horizon for probes 3a and 3b; probe 1-2 sweeps its own",
    )
    ap.add_argument(
        "--probe",
        choices=("all", "domain", "spread", "cells", "injection"),
        default="all",
    )
    args = ap.parse_args()

    if args.probe in ("all", "domain"):
        probe_domain(args.seeds)
    if args.probe in ("all", "spread"):
        probe_spread(args.seeds, args.rounds)
    if args.probe in ("all", "cells"):
        probe_cells(min(args.seeds, 3), args.rounds)
    if args.probe in ("all", "injection"):
        # A2's registered horizon, not this module's `--rounds`, which exists
        # for the asset probes. Issuance compounds, so a short horizon would
        # understate the expansion and the bitwise question would look easier
        # than it is.
        probe_injection(args.seeds, 300)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
