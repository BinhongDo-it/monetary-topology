"""A21: input-output coefficient perturbations, and who pays for them.

Coefficients are not fixed. Mariano, Verikios and Clements (Applied Economics
2025, working paper UWA 23-06) run 25 years of Australian tables and find that
coefficients change substantially, fixity holding only where the elasticity of
substitution is zero, which theirs mostly are not.

The perturbation is parameterised the way the literature decomposes it. The RAS
decomposition (Dietzenbacher and Hoekstra) splits a coefficient change into a
row part, a column part and a cell residual, A' = diag(r) A diag(s) + residual:

  ROW, substitution:  every buyer uses uniformly less of seller i per unit of
                      its own output.
  COLUMN, fabrication: buyer j's intermediate input intensity moves without
                      changing the mix it buys. That intensity IS the column
                      sum of A.

TECHNICAL PROGRESS is one directed trend on the row multiplier, not a synonym
for the multiplier: most of it cuts the logistics and labour per unit of
output, so downstream sellers' rows fall. OUTSOURCING is a directed trend on
the column multiplier and it runs the OTHER way: measured 1975-1985 the overall
intermediate input coefficient rose from 0.307 to 0.353, up 15% in a decade.
Measured substitution over the same window ran away from energy, metal products
and transport and toward computers, food and services, so even the row sign is
a property of the sector pair rather than of technology as such.

Four readings, all paired against the same seed:
  A21-3  row drift on production sellers, against a frozen matrix.
  A21-4  row drift on BOTH layers, against production-only: isolates the
         asymmetry rather than the drift.
  A21-5  column drift on production buyers, against a frozen matrix. Opposite
         sign to the row arm, because that is the sign the tables show.

Writes results/a21_technology.json. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
for d in (ROOT / "src", ROOT / "experiments"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from importlib.machinery import SourceFileLoader  # noqa: E402

_a19 = SourceFileLoader("a19", str(ROOT / "experiments" / "a19_industry.py")).load_module()
from monetary_topology.industry import IndustrySpec  # noqa: E402

DIGITS = 12
SEEDS = (0, 1, 2, 3, 4)

#: Per-period row drift on production sellers. The usable range is -0.001 to
#: -0.01: it compounds every round, so over 300 rounds -0.002 multiplies the
#: coefficients by 0.548 and -0.01 by 0.049. Past that the rows are not
#: drifting, they are being deleted.
DRIFT = -0.005

#: Per-period column drift on production buyers, positive because that is the
#: sign the tables show. Its ceiling is not a taste, it is Hawkins-Simon: the
#: column sum starts at ``column_sum`` and multiplies by ``(1 + d)`` every
#: round, so feasibility over the run needs
#:
#:     column_sum * (1 + d)^rounds < 1   =>   d < (1/column_sum)^(1/rounds) - 1
#:
#: which is 0.00231 here. 0.005 was tried first and raised the assertion at
#: round 139, exactly where the arithmetic says it would. That ceiling is the
#: asymmetry this arm exists to show: the fabrication direction has a hard cap,
#: because intermediate inputs cannot reach a whole unit of output, while the
#: substitution direction has no floor.
COL_DRIFT = 0.002

BASE = dict(_a19.ON, supply_elasticity=1.0, switch_rate=0.2, switch_cost=0.3,
            min_share=_a19.MIN_SHARE, recovery_friction=1.0, friction_spread=1.04)
SWEEP = (0.0, -0.001, -0.002, -0.005, -0.01)
CACHE = RESULTS / "a21_cache.json"


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str


def key(ind, seed):
    sp = IndustrySpec(**ind)
    return "|".join(f"{f.name}={getattr(sp, f.name)!r}" for f in fields(IndustrySpec)) \
        + f"|seed={seed}"


def load_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def measure(ind, seed, cache):
    k = key(ind, seed)
    if k in cache:
        return cache[k]
    h, m = _a19.run_full(ind, seed, _a19.LIVE)
    vol = float(np.asarray(h.total_volume, dtype=float).sum())
    l2 = float(np.asarray(h.layer2_inflow, dtype=float).sum())
    # Both are sums over the same flow matrix, so they share a denominator and
    # can be divided. layer1_volume is NOT usable here: it counts flow circling
    # *inside* layer 1, which is a different object from claims *landing in*
    # layer 2, and two readings on different definitions do not share a column.
    q = dict(
        total_volume=round(vol, DIGITS),
        l2_inflow_total=round(l2, DIGITS),
        l2_share=round(l2 / vol if vol else float("nan"), DIGITS),
        l2_support=round(float(h.effective_support_l2[-1]), DIGITS),
        active_nodes=float(h.active_nodes[-1]),
        switches=int(m._switch_count),
        column_sum_median=round(float(np.median(np.asarray(m._io).sum(0))), DIGITS),
    )
    cache[k] = q
    RESULTS.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")
    return q


READ = ("l2_share", "l2_support", "total_volume", "active_nodes")


def paired(name, treat, control, crit, out, cache):
    rows = []
    for s_ in SEEDS:
        t, c = measure(treat, s_, cache), measure(control, s_, cache)
        rows.append({k: round(t[k] - c[k], DIGITS) for k in READ}
                    | {"seed": s_, "sw_t": t["switches"], "sw_c": c["switches"]})
    print(f"\n{name}")
    print("  seed  " + "  ".join(f"{k:>16}" for k in READ))
    for r in rows:
        print(f"  {r['seed']:<4}  " + "  ".join(f"{r[k]:>16.6f}" for k in READ))
    summary = {}
    for k in READ:
        v = [r[k] for r in rows]
        p = sum(1 for x in v if x > 0)
        n = sum(1 for x in v if x < 0)
        summary[k] = dict(delta=v, positive=p, zero=len(v) - p - n, negative=n)
        print(f"  {k:>18}  {p} pos  {len(v)-p-n} zero  {n} neg"
              f"   [{min(v):+.6f}, {max(v):+.6f}]")
    print(f"  {'switches':>18}  treat {[r['sw_t'] for r in rows]}  "
          f"ctrl {[r['sw_c'] for r in rows]}")
    out[name] = dict(rows=rows, summary=summary)
    crit.append(Criterion(f"{name}: every seed and quantity returned a number",
                          all(np.isfinite(r[k]) for r in rows for k in READ),
                          f"{len(rows)} seeds x {len(READ)} quantities"))
    return summary


def main() -> int:
    argparse.ArgumentParser().parse_args()
    cache = load_cache()
    crit: list[Criterion] = []
    out: dict = {}
    print(f"  cache holds {len(cache)} runs")

    print("\nA21-2  row drift sweep at seed 0: what the knob moves, before reading it")
    print("  %-9s %-14s %-11s %-10s %-9s %s"
          % ("drift", "column sum med", "volume", "l2 share", "l2 supp", "switches"))
    sweep = []
    for d in SWEEP:
        q = measure(dict(BASE, row_drift=d), 0, cache)
        sweep.append(dict(drift=d, **q))
        print("  %-9s %-14.4f %-11.0f %-10.6f %-9.3f %d"
              % (d, q["column_sum_median"], q["total_volume"], q["l2_share"],
                 q["l2_support"], q["switches"]))
    out["A21-2 sweep"] = sweep
    sw = [r["switches"] for r in sweep]
    crit.append(Criterion("A21-2 the drift is not inert",
                          len(set(sw)) > 1,
                          f"switches across the sweep: {sw}"))

    print("\nA21-3  row drift on production sellers, against a frozen matrix")
    paired("A21-3 row drift vs frozen", dict(BASE, row_drift=DRIFT), dict(BASE),
           crit, out, cache)

    print("\nA21-4  the asymmetry itself: both layers drift, against production only")
    paired("A21-4 symmetric vs asymmetric",
           dict(BASE, row_drift=DRIFT, row_drift_financial=DRIFT),
           dict(BASE, row_drift=DRIFT), crit, out, cache)

    cap = (1.0 / BASE["column_sum"]) ** (1.0 / _a19.ROUNDS) - 1.0
    print(f"\nA21-5  column drift on production buyers, against a frozen matrix")
    print(f"  Hawkins-Simon caps the column drift at {cap:.5f} over "
          f"{_a19.ROUNDS} rounds; this arm runs at {COL_DRIFT}")
    out["A21-5 hawkins_simon_cap"] = round(cap, DIGITS)
    crit.append(Criterion("A21-5 the column arm is inside the feasibility cap",
                          COL_DRIFT < cap,
                          f"drift {COL_DRIFT} against cap {cap:.5f}; the cap is "
                          f"column_sum * (1+d)^rounds < 1, not a chosen bound"))
    paired("A21-5 col drift vs frozen", dict(BASE, col_drift=COL_DRIFT), dict(BASE),
           crit, out, cache)

    n_pass = sum(c.passed for c in crit)
    print(f"\n  {n_pass}/{len(crit)} criteria passed")
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / "a21_technology.json"
    p.write_text(json.dumps({
        "stage": "A21",
        "carrier": {"layer1_size": _a19.LAYER1_SIZE, "layer2_size": _a19.LAYER2_SIZE,
                    "rounds": _a19.ROUNDS, "seeds": list(SEEDS),
                    "industry": BASE, "row_drift": DRIFT, "col_drift": COL_DRIFT,
                    "sweep": list(SWEEP),
                    "live_setting": _a19.LIVE},
        "readings": out,
        "criteria": [{"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                     for c in crit],
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print(f"  wrote {p.relative_to(ROOT)}")
    return 0 if n_pass == len(crit) else 1


if __name__ == "__main__":
    raise SystemExit(main())
