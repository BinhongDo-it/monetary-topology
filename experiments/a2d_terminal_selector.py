"""A2d: what selects the terminal distribution on the A2 network.

Volume One section 1 says spending inside a layer is functionally equivalent to
saving. A0-4 already read that on the four-stratum block carrier: Layer 2 inflow
was flat to ``0.000e+00`` across a top-stratum propensity sweep from 0.05 to
1.00, while A0-5 read the same sweep moving Layer 1 churn by a factor of 15.
This stage asks the same question on the network carrier, with the whole sigma
vector rather than the top stratum's propensity, and with the terminal
distribution rather than a flow level as the readout.

It then asks what does select it. Two candidates are already in the
construction and neither is a new parameter: whether the monetary authority
issues at all, and where issuance enters. A0-9 read ``issuance accumulates in
the layer it was issued to``, which attributes the concentration to the entry
point. On this carrier that attribution is testable, because
``injection_target`` has a uniform branch that spreads issuance over every node.

Three grids, one readout each, spans compared against each other rather than
against any constant:

  sigma grid       structure and issuance frozen, sigma swept
  structure grid   sigma and issuance frozen, one structural knob moved at a time
  issuance grid    sigma and structure frozen, rule and entry point moved

Usage::

    python experiments/a2d_terminal_selector.py
    python experiments/a2d_terminal_selector.py --rounds 300 --seeds 5

Writes ``results/a2d_terminal_selector.json``. Exits non-zero if any criterion
fails.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import carrier_model
from monetary_topology.config import MonetaryAuthority, SpendRule
from monetary_topology.mechanisms import gini
from monetary_topology.network import Network, NetworkConfig, NetworkSpec

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

DIGITS = 6

#: Financial-layer retention. The span brackets the construction's own 0.50 and
#: the value Kuznets (1953) tables 47-48 read for the top five percent in 1929,
#: which is 0.38. Neither endpoint carries a verdict; the grid is spacing.
RET_L1 = (0.20, 0.30, 0.38, 0.50, 0.65, 0.80)
#: Production-layer retention. Zero is the boundary the model reaches toward
#: the dissaving the same tables read at low income multiples; it cannot go
#: below, because ``SpendRule`` caps propensity at one.
RET_L2 = (0.00, 0.0625, 0.15, 0.30)

#: One structural knob moved at a time, everything else at its default. These
#: are the knobs the manuscript does not pin. ``layer1_size`` is paired with
#: ``layer2_size`` so the node count stays at 200 and the top-one-percent set
#: stays two nodes across the whole grid.
STRUCTURE = (
    ("layer1_size", (10, 15, 20, 30, 40)),
    ("layer1_out_degree", (3, 4, 6, 8, 10)),
    ("layer2_out_degree", (2, 3, 4, 6)),
    ("upward_out_degree", (1, 2, 3, 4)),
    ("layer1_initial_share", (0.50, 0.60, 0.679, 0.75, 0.90)),
)

ISSUANCE = (
    ("endogenous", "top_node"),
    ("endogenous", "uniform"),
    ("fixed", "top_node"),
    ("fixed", "uniform"),
    ("none", "top_node"),
    ("none", "uniform"),
)


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


def spend_from_retention(ret_l1: float, ret_l2: float) -> SpendRule:
    """Retention is ``1 - propensity`` and the network takes the per-layer mean,
    so the two production entries and the two financial entries each carry one
    value. Setting low equal to high removes the draw, which is what makes the
    grid a sweep of one number per layer rather than of a distribution."""
    p1, p2 = 1.0 - ret_l1, 1.0 - ret_l2
    return SpendRule(low=(p2, p2, p1, p1), high=(p2, p2, p1, p1))


def one(
    ret_l1: float,
    ret_l2: float,
    rule: str,
    target: str,
    seed: int,
    rounds: int,
    spec_kw: dict | None = None,
    cfg_kw: dict | None = None,
    asset: bool = False,
) -> dict:
    spec_kw = dict(spec_kw or {})
    cfg_kw = dict(cfg_kw or {})
    cfg = NetworkConfig(
        spec=NetworkSpec(seed=seed, **spec_kw),
        seed=seed,
        rounds=rounds,
        spend=spend_from_retention(ret_l1, ret_l2),
        authority=MonetaryAuthority(rule=rule),
        injection_target=target,
        **cfg_kw,
    )
    h = carrier_model(cfg, asset=asset).run()
    n = h.node_count
    close = h.holdings[-1]
    return {
        "top1_wealth": r(top_share(close, max(1, n // 100))),
        "top10_wealth": r(top_share(close, n // 10)),
        "gini": r(gini(close)),
        "support": r(float(h.effective_support[-1])),
        "issued": r(float(h.issuance.sum())),
        "claims_close": r(float(close.sum())),
    }


def mean_over_seeds(seeds: int, **kw) -> dict:
    rows = [one(seed=s, **kw) for s in range(seeds)]
    return {k: r(float(np.mean([row[k] for row in rows]))) for k in rows[0]}


def span(values) -> tuple[float, float, float]:
    v = np.asarray(values, dtype=float)
    return r(float(v.min())), r(float(v.max())), r(float(v.max() - v.min()))


def evaluate(sigma_rows, structure_rows, issuance_rows) -> list[Criterion]:
    out: list[Criterion] = []

    # 1. structural, about the code rather than about the world.
    n_expected = len(RET_L1) * len(RET_L2)
    n_struct = sum(len(vals) for _, vals in STRUCTURE)
    ok = (
        len(sigma_rows) == n_expected
        and len(structure_rows) == n_struct
        and len(issuance_rows) == len(ISSUANCE)
        and all(np.isfinite(row["top1_wealth"]) for row in sigma_rows)
        and all(np.isfinite(row["top1_wealth"]) for row in structure_rows)
        and all(np.isfinite(row["top1_wealth"]) for row in issuance_rows)
    )
    out.append(
        Criterion(
            "A2d-1  every cell of all three grids ran and returned a finite share",
            ok,
            f"sigma {len(sigma_rows)}/{n_expected}, structure "
            f"{len(structure_rows)}/{n_struct}, issuance "
            f"{len(issuance_rows)}/{len(ISSUANCE)}. The stock-flow identity is "
            f"asserted inside the loop, so reaching here is also the claim that "
            f"it held in every round of every cell.",
        )
    )

    # 2. the two spans, printed side by side. Reading declared before the run:
    #    whichever span is larger names the thing that moves the terminal
    #    distribution more. No line is drawn on either.
    s_lo, s_hi, s_w = span([row["top1_wealth"] for row in sigma_rows])
    t_lo, t_hi, t_w = span([row["top1_wealth"] for row in structure_rows])
    ratio = r(t_w / s_w) if s_w > 0 else float("inf")
    out.append(
        Criterion(
            "A2d-2  sigma's span on terminal top1% wealth against the structural span",
            True,
            f"sigma grid {s_lo}-{s_hi}, width {s_w}. structure grid {t_lo}-{t_hi}, "
            f"width {t_w}. structural width is {ratio}x the sigma width. "
            f"Read: the larger span names the knob that selects the terminal "
            f"distribution. This criterion prints both and does not draw a line.",
        )
    )

    # 3. issuance on against issuance off. Three states, all reachable.
    on = [row["top1_wealth"] for row in issuance_rows if row["rule"] != "none"]
    off = [row["top1_wealth"] for row in issuance_rows if row["rule"] == "none"]
    gap = r(min(on) - max(off))
    if gap <= 0:
        state = "overlap: issuance does not separate"
    elif gap > s_w:
        state = "separated by more than sigma's whole span"
    else:
        state = "separated, but by less than sigma's span"
    out.append(
        Criterion(
            "A2d-3  issuance on against issuance off",
            gap > 0,
            f"on {r(min(on))}-{r(max(on))}, off {r(min(off))}-{r(max(off))}, "
            f"gap {gap} against sigma's span {s_w}. State: {state}.",
        )
    )

    # 4. the entry point, at matched rule and matched sigma.
    pairs = []
    for rule in ("endogenous", "fixed", "none"):
        a = [row for row in issuance_rows if row["rule"] == rule and row["target"] == "top_node"]
        b = [row for row in issuance_rows if row["rule"] == rule and row["target"] == "uniform"]
        if a and b:
            pairs.append((rule, a[0]["top1_wealth"], b[0]["top1_wealth"],
                          r(abs(a[0]["top1_wealth"] - b[0]["top1_wealth"])),
                          a[0]["issued"], b[0]["issued"]))
    worst = max(p[3] for p in pairs)
    detail = "; ".join(
        f"{rule}: top_node {x} vs uniform {y}, |diff| {d}, issued {ia} vs {ib}"
        for rule, x, y, d, ia, ib in pairs
    )
    out.append(
        Criterion(
            "A2d-4  the entry point, at matched rule and matched sigma",
            True,
            f"{detail}. Largest |diff| {worst} against the on-off gap {gap}. "
            f"Read: an entry-point effect smaller than the on-off gap says the "
            f"concentration is not attributable to where issuance lands. "
            f"This criterion prints the pairs and does not draw a line.",
        )
    )
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

    # ``asset`` rides in ``base`` so it reaches ``one`` through the same
    # kwargs every other setting uses, and the three grids cannot end up
    # on different carriers.
    base = dict(rounds=args.rounds, seeds=args.seeds, asset=args.asset)
    print(f"A2d  rounds={args.rounds} seeds={args.seeds}\n")

    print("sigma grid, structure and issuance frozen")
    print(f"{'ret_L1':>8}{'ret_L2':>8}{'top1%':>10}{'gini':>9}{'support':>9}{'issued':>10}")
    sigma_rows = []
    for r1 in RET_L1:
        for r2 in RET_L2:
            m = mean_over_seeds(ret_l1=r1, ret_l2=r2, rule="endogenous",
                                target="top_node", **base)
            m |= {"ret_l1": r1, "ret_l2": r2}
            sigma_rows.append(m)
            print(f"{r1:>8.4f}{r2:>8.4f}{m['top1_wealth']:>10.4f}{m['gini']:>9.4f}"
                  f"{m['support']:>9.3f}{m['issued']:>10.1f}")

    print("\nstructure grid, sigma and issuance frozen at their defaults")
    print(f"{'knob':>22}{'value':>10}{'top1%':>10}{'gini':>9}{'support':>9}")
    structure_rows = []
    for knob, values in STRUCTURE:
        for v in values:
            spec_kw, cfg_kw = {}, {}
            if knob == "layer1_size":
                spec_kw = {"layer1_size": v, "layer2_size": 200 - v}
            elif knob == "layer1_initial_share":
                cfg_kw = {"layer1_initial_share": v}
            else:
                spec_kw = {knob: v}
            m = mean_over_seeds(ret_l1=0.50, ret_l2=0.0625, rule="endogenous",
                                target="top_node", spec_kw=spec_kw,
                                cfg_kw=cfg_kw, **base)
            m |= {"knob": knob, "value": v}
            structure_rows.append(m)
            print(f"{knob:>22}{v:>10}{m['top1_wealth']:>10.4f}{m['gini']:>9.4f}"
                  f"{m['support']:>9.3f}")

    print("\nissuance grid, sigma and structure frozen at their defaults")
    print(f"{'rule':>12}{'target':>10}{'top1%':>10}{'gini':>9}{'support':>9}"
          f"{'issued':>10}{'claims':>10}")
    issuance_rows = []
    for rule, target in ISSUANCE:
        m = mean_over_seeds(ret_l1=0.50, ret_l2=0.0625, rule=rule,
                            target=target, **base)
        m |= {"rule": rule, "target": target}
        issuance_rows.append(m)
        print(f"{rule:>12}{target:>10}{m['top1_wealth']:>10.4f}{m['gini']:>9.4f}"
              f"{m['support']:>9.3f}{m['issued']:>10.1f}{m['claims_close']:>10.1f}")

    criteria = evaluate(sigma_rows, structure_rows, issuance_rows)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, "
          f"{len(criteria) - len(live)} void")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a2d_terminal_selector.json" if not args.asset
        else "a2d_terminal_selector_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A2d",
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this station's "
                        "registered carrier; the registered reading is "
                        "results/a2d_terminal_selector.json"
                    )} if args.asset else {}),
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "retention_l1": list(RET_L1),
                "retention_l2": list(RET_L2),
                "sigma_grid": sigma_rows,
                "structure_grid": structure_rows,
                "issuance_grid": issuance_rows,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "detail": c.detail, "void": bool(c.void)}
                    for c in criteria
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
