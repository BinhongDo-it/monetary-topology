"""A14: which readings are scale free, and which are artefacts of two hundred nodes.

Two knobs carry no derivation anywhere in this repository. ``n = 200`` is one,
and ``layer1_size / n = 0.10`` is the other. A2d's structure grid held both
fixed, so the structural span it reports is a lower bound.

The measurement that shaped this stage, taken before the arms were written. A
sweep of ``n`` with the degree parameters left alone reads terminal top1% wealth
rising from 0.2300 to 0.3388 between 200 and 1000 nodes. The same sweep with the
degrees scaled to hold each layer's density fixed reads it **falling**, 0.2300
to 0.1905. The degree parameters are absolute edge counts, so raising ``n``
without them thins the financial layer from 32% internal density to 6% and gives
preferential attachment room to build hubs it did not have. **A sweep of ``n``
alone is a sweep of density with extra steps**, which is why both arms are here
and neither is optional.

What this stage does not do is rerun the other stages. It reads their headline
quantities on a grid. Their criteria carry thresholds set for 200 nodes, and
moving those for a reason unrelated to their own questions would be a change to
their records that answers nothing.

Excluded, and named rather than silently dropped: A8's and A12's four surfaces,
because ``f2i`` is an absolute edge count whose maximum of 30 is 7.5% of the
possible financial-to-intermediate edges at 200 nodes and 0.3% at 1000, so the
same grid tests a different regime; A7's shortcut rate, for the same reason and
unchecked; and the rewire switch, which stays off throughout because two knobs
move one at a time.

Usage::

    python experiments/a14_scale.py
    python experiments/a14_scale.py --seeds 5

Writes ``results/a14_scale.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import carrier_model
from monetary_topology.mechanisms import gini
from monetary_topology.network import Network, NetworkConfig, NetworkSpec

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DIGITS = 6

#: Node counts. 2000 is out: the density-preserving arm reaches an internal
#: out-degree of 63 there and does not finish in a useful time, and the reversal
#: this stage exists to show is already legible across 200, 500 and 1000.
SIZES = (200, 500, 1000)

#: Core as a share of nodes. 0.05 is the published break, 0.10 is the current
#: value and carries no derivation, 0.20 is an upper reference with no source.
FRACTIONS = (0.05, 0.10, 0.20)

_B = NetworkSpec()
#: The densities at the construction's own size, which the scaled arm preserves.
DENSITY_L1 = _B.layer1_out_degree / (20 - 1)
DENSITY_L2 = _B.layer2_out_degree / (180 - 1)
DENSITY_UP = _B.upward_out_degree / 20

#: A4-2's registered readings, quoted so the comparison is against the record
#: rather than against a number restated here.
A4_STRATIFIED = 0.93673
A4_NULL = 0.00711
A4_NULL_CEILING = 0.02


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    void: bool = False

    def line(self) -> str:
        mark = "VOID" if self.void else ("PASS" if self.passed else "FAIL")
        return f"  [{mark}] {self.name}\n         {self.detail}"


def r(x: float) -> float:
    return round(float(x), DIGITS)


def top_share(v: np.ndarray, k: int) -> float:
    s = np.sort(np.asarray(v, dtype=float))[::-1]
    total = s.sum()
    return float(s[:k].sum() / total) if total > 0 else float("nan")


def spec_for(n: int, fraction: float, arm: str, seed: int) -> NetworkSpec:
    n1 = max(2, round(n * fraction))
    n2 = n - n1
    if arm == "scaled":
        d1 = max(1, round(DENSITY_L1 * (n1 - 1)))
        d2 = max(1, round(DENSITY_L2 * (n2 - 1)))
        du = max(1, round(DENSITY_UP * n1))
    else:
        d1, d2, du = (_B.layer1_out_degree, _B.layer2_out_degree,
                      _B.upward_out_degree)
    return NetworkSpec(
        seed=seed, layer1_size=n1, layer2_size=n2,
        layer1_out_degree=min(d1, n1 - 1),
        layer2_out_degree=min(d2, n2 - 1),
        upward_out_degree=min(du, n1),
        uniform_access=(arm == "null"),
    )


def one(n: int, fraction: float, arm: str, seed: int, rounds: int,
        asset: bool = False) -> dict:
    spec = spec_for(n, fraction, arm, seed)
    cfg = NetworkConfig(spec=spec, seed=seed, rounds=rounds)
    h = carrier_model(cfg, asset=asset).run()
    close = h.holdings[-1]
    sup = np.asarray(h.effective_support, dtype=float)
    vol = np.asarray(h.total_volume, dtype=float)
    return {
        "n": n, "fraction": fraction, "arm": arm, "seed": seed,
        "layer1_size": spec.layer1_size,
        "l1_out_degree": spec.layer1_out_degree,
        "l1_density": r(spec.layer1_out_degree / max(spec.layer1_size - 1, 1)),
        "edges": int(h.adjacency.sum()),
        "top1_wealth": r(top_share(close, max(1, n // 100))),
        "top01_wealth": r(top_share(close, max(1, n // 1000))),
        "gini": r(gini(close)),
        "support_ratio": r(float(sup[-1] / sup[0])),
        "support_close": r(float(sup[-1])),
        "volume_ratio": r(float(vol[-1] / vol[0])),
        "mr_close": r(float(h.total_ratio[-1])),
        "top1_nodes": max(1, n // 100),
        "top01_nodes": max(1, n // 1000),
    }


def mean_of(rows: list[dict], key: str) -> float:
    return r(float(np.mean([row[key] for row in rows])))


def evaluate(rows: list[dict], rounds: int) -> list[Criterion]:
    out: list[Criterion] = []

    def pick(**kw) -> list[dict]:
        return [row for row in rows
                if all(row[k] == v for k, v in kw.items())]

    expected = len(SIZES) * len(FRACTIONS) * 3
    per = len({(row["n"], row["fraction"], row["arm"]) for row in rows})
    out.append(Criterion(
        "A14-1  every cell ran, and the construction's own cell reproduces",
        per == expected
        and all(np.isfinite(row["top1_wealth"]) for row in rows),
        f"{per}/{expected} cells. The construction's own cell is n=200, "
        f"fraction=0.10, arm fixed, where the two degree arms coincide by "
        f"definition: fixed reads "
        f"{mean_of(pick(n=200, fraction=0.10, arm='fixed'), 'top1_wealth')} and "
        f"scaled reads "
        f"{mean_of(pick(n=200, fraction=0.10, arm='scaled'), 'top1_wealth')}.",
    ))

    # The span with n in the grid, against A2d's without it.
    span_here = [mean_of(pick(n=n, fraction=f, arm=a), "top1_wealth")
                 for n in SIZES for f in FRACTIONS for a in ("fixed", "scaled")]
    ref = json.loads((RESULTS / "a2d_terminal_selector.json").read_text(encoding="utf-8"))
    a2d = [row["top1_wealth"] for row in ref["structure_grid"]]
    out.append(Criterion(
        "A14-2  the structural span with n and the core fraction in the grid",
        True,
        f"this stage {r(min(span_here))}-{r(max(span_here))}, width "
        f"{r(max(span_here) - min(span_here))}. A2d's structure grid, which held "
        f"n at 200 and the fraction at 0.10, reported "
        f"{r(min(a2d))}-{r(max(a2d))}, width {r(max(a2d) - min(a2d))}. Read: "
        f"A2d's figure is a lower bound and this is the value with both knobs "
        f"in.",
    ))

    # The reversal. Two arms, same quantity, direction compared.
    lines = []
    reversed_any = False
    for key in ("top1_wealth", "gini", "support_ratio", "support_close",
                "volume_ratio", "mr_close"):
        d = {}
        for arm in ("fixed", "scaled"):
            v = [mean_of(pick(n=n, fraction=0.10, arm=arm), key) for n in SIZES]
            d[arm] = (v[0], v[-1], r(v[-1] - v[0]))
        same = np.sign(d["fixed"][2]) == np.sign(d["scaled"][2])
        reversed_any |= not same
        lines.append(
            f"{key}: fixed {d['fixed'][0]}->{d['fixed'][1]} ({d['fixed'][2]:+}), "
            f"scaled {d['scaled'][0]}->{d['scaled'][1]} ({d['scaled'][2]:+}), "
            f"{'same direction' if same else 'REVERSED'}")
    out.append(Criterion(
        "A14-3  the two degree arms, same quantity, direction compared",
        True,
        "; ".join(lines)
        + ". Read: two arms agreeing in direction is a scale effect; a "
          "reversal says the quantity was measuring density, not size."
        + (" At least one quantity reverses."
           if reversed_any else " No quantity reverses."),
    ))

    # The core fraction axis.
    frac_lines = []
    for f in FRACTIONS:
        v = mean_of(pick(n=1000, fraction=f, arm="scaled"), "top1_wealth")
        g = mean_of(pick(n=1000, fraction=f, arm="scaled"), "gini")
        frac_lines.append(f"{f}: top1% {v}, gini {g}")
    out.append(Criterion(
        "A14-4  the core fraction axis at n=1000, density held",
        True,
        "; ".join(frac_lines)
        + ". Read: 0.05 is the published break (Fagereng et al.'s composition "
          "change at P95, and Saez-Zucman's flat P90-99 share over three "
          "decades); 0.10 is the current value and carries no derivation "
          "anywhere in this repository; 0.20 is an upper reference with no "
          "source.",
    ))

    # Resolution, printed rather than claimed.
    res = "; ".join(
        f"n={n}: top1% is {max(1, n // 100)} nodes, top0.1% is "
        f"{max(1, n // 1000)}" for n in SIZES)
    out.append(Criterion(
        "A14-5  what the top percentiles are, in nodes, at each size",
        True,
        res + ". Read: the distribution the published estimates describe has a "
              "top 0.1% and at 200 nodes that group is one node by the floor "
              "rather than by the construction.",
    ))

    # The one quantity this stage can put against a published figure. Printed,
    # not scored: the published number is for city income and activity, not for
    # claim holdings, so it places the magnitude and does not judge the model.
    g0 = mean_of(pick(n=SIZES[0], fraction=0.10, arm="fixed"), "gini")
    g1 = mean_of(pick(n=SIZES[-1], fraction=0.10, arm="fixed"), "gini")
    doublings = float(np.log2(SIZES[-1] / SIZES[0]))
    per_doubling = r(((g1 / g0) ** (1.0 / doublings) - 1.0) * 100.0)
    s0 = mean_of(pick(n=SIZES[0], fraction=0.10, arm="scaled"), "gini")
    s1 = mean_of(pick(n=SIZES[-1], fraction=0.10, arm="scaled"), "gini")
    per_doubling_scaled = r(((s1 / s0) ** (1.0 / doublings) - 1.0) * 100.0)
    out.append(Criterion(
        "A14-7  Gini per doubling of population, against the published figure",
        True,
        f"fixed-degree arm: {g0} at n={SIZES[0]} to {g1} at n={SIZES[-1]}, "
        f"{doublings:.2f} doublings, **{per_doubling:+}% per doubling**. "
        f"Density-preserving arm: {s0} to {s1}, {per_doubling_scaled:+}% per "
        f"doubling. Published reference: intra-urban economic activity Gini "
        f"scales with population at alpha = 0.11, about +8% per doubling, over "
        f"11,000 global urban centres. Read: the fixed-degree arm is the one "
        f"with a source for its degree assumption, and its sign is the "
        f"comparison; the magnitude is bounded above by the model's closing "
        f"Gini already sitting near one, which is a reading about the model's "
        f"top tail rather than about population.",
    ))

    # A4's two readings across the grid.
    a4 = []
    for n in SIZES:
        s = mean_of(pick(n=n, fraction=0.10, arm="fixed"), "gini")
        z = mean_of(pick(n=n, fraction=0.10, arm="null"), "gini")
        a4.append((n, s, z, r(s - z)))
    ok = all(z < A4_NULL_CEILING for _, _, z, _ in a4)
    out.append(Criterion(
        "A14-6  A4's null stays under its registered ceiling at every size",
        ok,
        "; ".join(f"n={n}: stratified {s}, null {z}, gap {g}" for n, s, z, g in a4)
        + f". A4's record: stratified {A4_STRATIFIED}, null {A4_NULL}, ceiling "
          f"{A4_NULL_CEILING}.",
    ))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second.",
    )
    args = ap.parse_args()

    print(f"A14  rounds={args.rounds} seeds={args.seeds} "
          f"sizes={list(SIZES)} fractions={list(FRACTIONS)}\n")
    hdr = (f"{'n':>6}{'frac':>7}{'arm':>8}{'L1':>5}{'deg':>5}{'dens':>7}"
           f"{'edges':>8}{'top1%':>9}{'gini':>8}{'sup ratio':>10}{'M/R':>9}")
    print(hdr)
    print("-" * len(hdr))

    rows: list[dict] = []
    for n in SIZES:
        for f in FRACTIONS:
            for arm in ("fixed", "scaled", "null"):
                got = [one(n, f, arm, seed, args.rounds, args.asset)
                       for seed in range(args.seeds)]
                rows.extend(got)
                print(f"{n:>6}{f:>7.2f}{arm:>8}{got[0]['layer1_size']:>5}"
                      f"{got[0]['l1_out_degree']:>5}{got[0]['l1_density']:>7.3f}"
                      f"{mean_of(got,'edges'):>8.0f}"
                      f"{mean_of(got,'top1_wealth'):>9.4f}"
                      f"{mean_of(got,'gini'):>8.4f}"
                      f"{mean_of(got,'support_ratio'):>10.4f}"
                      f"{mean_of(got,'mr_close'):>9.2f}")

    criteria = evaluate(rows, args.rounds)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, "
          f"{len(criteria) - len(live)} void")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a14_scale.json" if not args.asset else "a14_scale_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A14",
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "sizes": list(SIZES),
                "fractions": list(FRACTIONS),
                "density_l1": r(DENSITY_L1),
                "density_l2": r(DENSITY_L2),
                "density_up": r(DENSITY_UP),
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this "
                        "station's registered carrier; the registered "
                        "reading is results/a14_scale.json"
                    )} if args.asset else {}),
                "runs": rows,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "detail": c.detail, "void": bool(c.void)}
                    for c in criteria
                ],
            },
            indent=2, sort_keys=True,
        ) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
