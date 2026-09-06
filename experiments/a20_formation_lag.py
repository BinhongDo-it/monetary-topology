"""A20: formation lag as a per-industry property, and what it selects.

Volume Two section 3 makes one claim about formation lags that is not about
their existence: that they are HETEROGENEOUS, and that the heterogeneity is
what does the work. It orders four bases by lag, steel capacity at twenty to
thirty years down to reputation at a few. A19 gave every industry the same
recovery friction, so it could not read that claim at all.

This stage spreads the friction within each layer and reads what the spread
selects. The comparison is WITHIN the arm: industries sorted by their own
friction, bottom half against top half. Nothing is compared across arms with
different mean friction, so no normalising constant is needed anywhere.

Writes results/a20_formation_lag.json. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "experiments") not in sys.path:
    sys.path.insert(0, str(ROOT / "experiments"))

from importlib.machinery import SourceFileLoader  # noqa: E402

_a19 = SourceFileLoader("a19", str(ROOT / "experiments" / "a19_industry.py")).load_module()
from monetary_topology.industry import IndustrySpec, friction_vector  # noqa: E402

DIGITS = 12
SEEDS = (0, 1, 2, 3, 4)

#: The environments the reading is run in. One knob, the subsistence need, and
#: it is swept because the damage flag saturates at the registered value: at
#: 0.0914 only 54 of 180 production nodes are still alive and 18 of 20
#: industries are below the line at the close, which leaves that quantity two
#: cells to move in. At 0.06 the layer is neither full nor empty, 119 alive and
#: 14 industries below the line, so the same reading has room.
#:
#: Both are reported. A direction that holds in one environment and flips in the
#: other is a property of that point, not of the mechanism, and the only way to
#: find that out is to run both (D11).
ENVS = {"registered need=0.0914": dict(need=0.0914),
        "unsaturated need=0.06": dict(need=0.06)}

#: Log half-range of the spread. exp(2 * 1.04) = 8.0, which is the ratio
#: between the slowest and the fastest of the four bases the manuscript lists.
#: Not a free constant.
SPREAD = 1.04

#: Where the friction sits. Swept below rather than assumed: at 5.0 the
#: threshold has saturated and the spread moves nothing at all, which is the
#: first thing this stage measured.
FRICTION = 1.0

BASE = dict(_a19.ON, supply_elasticity=1.0, switch_rate=0.2, switch_cost=0.3,
            min_share=_a19.MIN_SHARE)
SWEEP = (0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
CACHE = RESULTS / "a20_cache.json"


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str


def key(ind, seed, env):
    sp = IndustrySpec(**ind)
    from dataclasses import fields as _f
    return "|".join(f"{f.name}={getattr(sp, f.name)!r}" for f in _f(IndustrySpec)) \
        + "|" + "|".join(f"env.{k}={env[k]!r}" for k in sorted(env)) \
        + f"|seed={seed}"


def load_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def measure(ind, seed, cache, env=None):
    env = dict(_a19.LIVE, **(env or {}))
    k = key(ind, seed, env)
    if k in cache:
        return cache[k]
    h, m = _a19.run_full(ind, seed, env)
    g = np.asarray(m._industry_of)
    hot = np.asarray(m._last_inflow) > float(h.epsilon_absolute)
    d = np.asarray(m._damaged_for)
    q = dict(
        switches=int(m._switch_count),
        damaged_for=[int(x) for x in d],
        hot_per_industry=[int(((g == i) & hot).sum()) for i in range(int(ind["count"]))],
        total_volume=round(float(np.asarray(h.total_volume).sum()), DIGITS),
        l2_support=round(float(h.effective_support_l2[-1]), DIGITS),
    )
    cache[k] = q
    RESULTS.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")
    return q


def _rank(x):
    """Average ranks, ties shared."""
    x = np.asarray(x, dtype=float)
    o = np.argsort(np.argsort(x, kind="stable"), kind="stable").astype(float)
    out = o.copy()
    for v in np.unique(x):
        m = x == v
        if m.sum() > 1:
            out[m] = o[m].mean()
    return out


def spearman(a, b):
    """Rank correlation across all twenty industries.

    This replaces the bottom-half against top-half sum that this stage used
    first. The sum is dominated by one member: the distribution of members per
    industry is heavy tailed, one industry carrying 20 to 38 while the rest
    carry 0 to 10, and removing whichever industry is largest FLIPS the sign of
    the half-to-half difference in every seed and both environments. A rank
    correlation over all twenty cannot be carried by one of them.
    """
    ra, rb = _rank(a), _rank(b)
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    d = float(np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
    return float((ra * rb).sum() / d) if d > 0 else float("nan")


def halves(ind):
    fv = friction_vector(IndustrySpec(**ind))
    o = np.argsort(fv)
    return fv, o[:len(o) // 2], o[len(o) // 2:]


def main() -> int:
    argparse.ArgumentParser().parse_args()
    cache = load_cache()
    crit: list[Criterion] = []
    out: dict = {}
    print(f"  cache holds {len(cache)} runs")

    # A20-1  where the knob has an object. Printed before it is read, because a
    # saturated threshold makes the spread inert and that is not a finding
    # about the mechanism (D28, and the three sweep-range misses A19 paid for).
    print("\nA20-1  friction sweep at seed 0, to find where the threshold saturates")
    print("  %-10s %-9s %-14s %s" % ("friction", "switches", "damaged/20", "hot total"))
    sweep = []
    for f in SWEEP:
        q = measure(dict(BASE, recovery_friction=f), 0, cache)
        dmg = sum(1 for x in q["damaged_for"] if x >= 0)
        sweep.append(dict(friction=f, switches=q["switches"], damaged=dmg,
                          hot=sum(q["hot_per_industry"])))
        print("  %-10.2f %-9d %-14d %d" % (f, q["switches"], dmg, sum(q["hot_per_industry"])))
    out["A20-1 sweep"] = sweep
    sat = [r for r in sweep if r["friction"] >= 2.0]
    moving = [r for r in sweep if 0.5 <= r["friction"] <= 1.0]
    ok = min(r["switches"] for r in moving) > max(r["switches"] for r in sat)
    crit.append(Criterion("A20-1 the read point is below saturation", ok,
                          f"switches at friction 0.5-1.0 are "
                          f"{[r['switches'] for r in moving]}, at 2.0-5.0 they are "
                          f"{[r['switches'] for r in sat]}"))

    # A20-2  mechanical effect of the spread itself (D28): a treatment that
    # moves nothing is inert, and the way to find out is to count what it moved.
    print(f"\nA20-2  mechanical effect of the spread at friction {FRICTION}")
    flat = measure(dict(BASE, recovery_friction=FRICTION, friction_spread=0.0), 0, cache)
    var = measure(dict(BASE, recovery_friction=FRICTION, friction_spread=SPREAD), 0, cache)
    same_d = sum(1 for a, b in zip(flat["damaged_for"], var["damaged_for"]) if a == b)
    same_h = sum(1 for a, b in zip(flat["hot_per_industry"], var["hot_per_industry"]) if a == b)
    n = len(flat["damaged_for"])
    print(f"  switches {flat['switches']} -> {var['switches']}")
    print(f"  industries reading the same: damage {same_d}/{n}, hot members {same_h}/{n}")
    print(f"  total volume {var['total_volume'] - flat['total_volume']:+.0f}, "
          f"L2 support {var['l2_support'] - flat['l2_support']:+.4f}")
    out["A20-2 mechanical"] = dict(flat=flat["switches"], spread=var["switches"],
                                   same_damage=same_d, same_hot=same_h, n=n)
    crit.append(Criterion("A20-2 the spread is not inert",
                          var["switches"] != flat["switches"] and same_h < n,
                          f"switches {flat['switches']} -> {var['switches']}, "
                          f"{n - same_h}/{n} industries change their hot count"))

    # A20-3  the reading, within the arm.
    ind = dict(BASE, recovery_friction=FRICTION, friction_spread=SPREAD)
    fv, lo, hi = halves(ind)
    print(f"\nA20-3  within the arm: {len(lo)} slow-to-recover industries against "
          f"{len(hi)} slower still")
    print(f"  friction bottom half {fv[lo].min():.3f}-{fv[lo].max():.3f}, "
          f"top half {fv[hi].min():.3f}-{fv[hi].max():.3f}")
    named = [("damaged industries", 0), ("damaged rounds", 1), ("hot members", 2)]
    per_env = {}
    for label, env in ENVS.items():
        print(f"\n  environment: {label}")
        print("  %-5s %-16s %-18s %-14s" % ("seed", "damaged lo/hi",
                                            "damaged-rounds lo/hi", "hot lo/hi"))
        rows = []
        for s_ in SEEDS:
            q = measure(ind, s_, cache, env)
            d = np.array(q["damaged_for"]); hc = np.array(q["hot_per_industry"])
            a = (int((d[lo] >= 0).sum()), int(d[lo][d[lo] >= 0].sum()), int(hc[lo].sum()))
            b = (int((d[hi] >= 0).sum()), int(d[hi][d[hi] >= 0].sum()), int(hc[hi].sum()))
            rows.append(dict(seed=s_, lo=a, hi=b))
            print("  %-5d %-16s %-18s %-14s" % (s_, f"{a[0]}/{b[0]}", f"{a[1]}/{b[1]}",
                                                f"{a[2]}/{b[2]}"))
        summary = {}
        for nm, i in named:
            v = [r["hi"][i] - r["lo"][i] for r in rows]
            p = sum(1 for x in v if x > 0); ng = sum(1 for x in v if x < 0)
            summary[nm] = dict(delta=v, positive=p, zero=len(v) - p - ng, negative=ng)
            print(f"  {nm:>20}  {v}   {p} pos  {len(v)-p-ng} zero  {ng} neg")
        per_env[label] = dict(rows=rows, summary=summary)
    out["A20-3 by environment"] = per_env

    # A20-6: the same question without splitting into halves, because the split
    # turned out to be the problem rather than the answer.
    print("\nA20-6  rank correlation of friction against each quantity, all "
          f"{len(fv)} industries")
    rho = {}
    for label, env in ENVS.items():
        print(f"  environment: {label}")
        print("  %-5s %-14s %-16s %-14s" % ("seed", "rho(f, hot)",
                                            "rho(f, dmg rounds)", "rho(f, damaged)"))
        per = {"hot": [], "damaged_rounds": [], "damaged": []}
        for s_ in SEEDS:
            q = measure(ind, s_, cache, env)
            hc = np.array(q["hot_per_industry"], dtype=float)
            d = np.array(q["damaged_for"], dtype=float)
            r_hot = spearman(fv, hc)
            r_len = spearman(fv, np.where(d >= 0, d, 0.0))
            r_bin = spearman(fv, (d >= 0).astype(float))
            per["hot"].append(round(r_hot, DIGITS))
            per["damaged_rounds"].append(round(r_len, DIGITS))
            per["damaged"].append(round(r_bin, DIGITS))
            print("  %-5d %-14.4f %-16.4f %-14.4f" % (s_, r_hot, r_len, r_bin))
        for nm, v in per.items():
            pos = sum(1 for x in v if x > 0)
            neg = sum(1 for x in v if x < 0)
            print("  %>18s" .replace(">", "") % nm
                  + "  " + " ".join(f"{x:+.3f}" for x in v)
                  + f"   {pos} pos  {neg} neg")
        rho[label] = per
    out["A20-6 rank correlation"] = rho

    # The half-sum is kept in the record and shown to be dominated, because the
    # domination IS the finding that moved this stage's headline.
    print("\n  why the halves were dropped: remove the single largest industry")
    dom = {}
    for label, env in ENVS.items():
        line = []
        for s_ in SEEDS:
            q = measure(ind, s_, cache, env)
            hc = np.array(q["hot_per_industry"], dtype=float)
            raw = int(hc[hi].sum() - hc[lo].sum())
            k = int(np.argmax(hc))
            h2 = hc.copy(); h2[k] = 0.0
            line.append((raw, int(h2[hi].sum() - h2[lo].sum()),
                         k, int(hc[k]), "hi" if k in set(hi.tolist()) else "lo"))
        dom[label] = [dict(raw=a, without_largest=b, industry=c, size=d, side=e)
                      for a, b, c, d, e in line]
        print(f"  {label}")
        print("    raw diff        " + " ".join(f"{a:+5d}" for a, _, _, _, _ in line))
        print("    without largest " + " ".join(f"{b:+5d}" for _, b, _, _, _ in line))
        print("    largest is      " + " ".join(f"{c:2d}({d:2d}){e}"
                                                for _, _, c, d, e in line))
    out["A20-3 half-sum domination"] = dom
    flipped = all(
        any(r["raw"] * r["without_largest"] < 0 for r in dom[lb]) for lb in ENVS)
    crit.append(Criterion(
        "A20-3 the half-sum is dominated by one industry", flipped,
        "removing the largest industry reverses the sign of the half-to-half "
        "difference in at least one seed of every environment"))

    # The point of running both: a direction that survives the environment is a
    # property of the mechanism, one that flips is a property of the point.
    print("\n  direction across environments")
    labels = list(ENVS)
    stable = []
    for nm, _ in named:
        signs = []
        for lb in labels:
            su = per_env[lb]["summary"][nm]
            signs.append("+" if su["positive"] > su["negative"] else
                         ("-" if su["negative"] > su["positive"] else "0"))
        ok = len(set(signs)) == 1 and signs[0] != "0"
        stable.append((nm, signs, ok))
        print(f"  {nm:>20}  {' '.join(f'{lb}: {sg}' for lb, sg in zip(labels, signs))}"
              f"   {'same direction' if ok else 'FLIPS'}")
    out["A20-3 direction across environments"] = {
        nm: dict(signs=sg, stable=ok) for nm, sg, ok in stable}
    crit.append(Criterion(
        "A20-3 at least one quantity keeps its direction across both environments",
        any(ok for _, _, ok in stable),
        "; ".join(f"{nm}: {' '.join(sg)}" for nm, sg, _ in stable)))

    n_pass = sum(c.passed for c in crit)
    print(f"\n  {n_pass}/{len(crit)} criteria passed")
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / "a20_formation_lag.json"
    p.write_text(json.dumps({
        "stage": "A20",
        "carrier": {"layer1_size": _a19.LAYER1_SIZE, "layer2_size": _a19.LAYER2_SIZE,
                    "rounds": _a19.ROUNDS, "seeds": list(SEEDS),
                    "industry": BASE, "friction": FRICTION, "spread": SPREAD,
                    "live_setting": _a19.LIVE},
        "friction_vector": [round(float(x), 6) for x in fv],
        "readings": out,
        "criteria": [{"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                     for c in crit],
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print(f"  wrote {p.relative_to(ROOT)}")
    return 0 if n_pass == len(crit) else 1


if __name__ == "__main__":
    raise SystemExit(main())
