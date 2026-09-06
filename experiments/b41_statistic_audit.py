"""Three assertions in the B41 record that were stated but never scored.

Each of these is one arithmetic away from being checkable, and each was left as
a sentence:

  the persistent statistic measures persistence rather than size, so a square
  that is large and reverses sign should read near zero on it while reading
  large on the magnitude column;

  Montana's twenty-eight interaction degrees of freedom overstate how many
  independent commodity directions its eight columns carry;

  Tennessee's year to year pattern is which months got sampled rather than a
  year effect.

    python experiments/b41_statistic_audit.py --check --record

Reads only what is cached. No network, no key.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_joint as J          # noqa: E402
import b41_magnitude as M      # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results"
MT, TN, SD, KS = 2771, 3088, 3186, 2886


def two_statistics(mats, df):
    """Exactly what b41_magnitude computes, on any stack of matrices."""
    mask = np.ones(mats[0].shape, bool)
    daily = [M.per_cycle(J.additive_residual(m, mask)[0], df) for m in mats]
    rp, _, _ = J.additive_residual(np.mean(mats, axis=0), mask)
    persistent = M.per_cycle(rp, df)
    magnitude = statistics.median(daily)
    return persistent, magnitude


def part_one() -> dict:
    """A field that is large and reverses sign, against one that does not."""
    print("\n=== 1. does the persistent statistic separate size from persistence")
    rng = random.Random(20260903)
    n, df = 400, 1
    base = np.array([[1.0, -1.0], [-1.0, 1.0]])   # a 2x2 with df 1
    out = {}
    for name, gen in (
        ("steady +12 every day", lambda: 12.0),
        ("+25 and -25, alternating", lambda i=[0]: (i.__setitem__(0, i[0] + 1),
                                                    25.0 if i[0] % 2 else -25.0)[1]),
        ("+25 and -25, at random", lambda: rng.choice([25.0, -25.0])),
        ("+25 and -25, 60/40 split", lambda: 25.0 if rng.random() < 0.6 else -25.0),
    ):
        mats = [base * gen() for _ in range(n)]
        p, m = two_statistics(mats, df)
        out[name] = dict(persistent=p, magnitude=m,
                         persistence=p / m if m else float("nan"))
        print(f"   {name:<28} persistent {p:7.2f}  magnitude {m:7.2f}  "
              f"persistence {p / m:6.3f}")
    print("   Tennessee on the same two columns: persistent 0.80, magnitude 12.50, "
          "persistence 0.064")
    return out


def part_two() -> dict:
    """How many independent commodity directions do those columns carry."""
    print("\n=== 2. how many independent directions the interaction actually has")
    out = {}
    for rid, cov, label in ((MT, 0.60, "MT  5 positions x 8 wheat grades"),
                            (KS, 0.60, "KS  8 positions x 2 commodities"),
                            (SD, 0.60, "SD  4 positions x 3 commodities")):
        with contextlib.redirect_stdout(io.StringIO()):
            got = M.panel(rid, cov)
        if not got:
            continue
        coms, poss, days, mats = got
        df = (len(poss) - 1) * (len(coms) - 1)
        mask = np.ones(mats[0].shape, bool)
        rp, _, _ = J.additive_residual(np.mean(mats, axis=0), mask)
        s = np.linalg.svd(rp, compute_uv=False)
        s = s[s > 1e-12]
        tot = float((s ** 2).sum())
        shares = [float(x ** 2 / tot) for x in s]
        eff = float(tot ** 2 / (s ** 4).sum())      # participation ratio
        print(f"   {label:<34} df {df:>3}   algebraic rank {len(s)}   "
              f"effective directions {eff:.2f}")
        print(f"      variance shares: " +
              "  ".join(f"{x:.3f}" for x in shares))
        out[label] = dict(report=rid, df=df, rank=len(s),
                          effective_directions=eff, shares=shares)
    return out


def part_three() -> dict:
    """Is Tennessee's year pattern a year effect or a month composition."""
    print("\n=== 3. Tennessee by year, as sampled and with months balanced")
    with contextlib.redirect_stdout(io.StringIO()):
        got = M.panel(TN, 0.40)
    coms, poss, days, mats = got
    df = (len(poss) - 1) * (len(coms) - 1)
    mask = np.ones(mats[0].shape, bool)
    per_day = {}
    for d, m in zip(days, mats):
        r, _, _ = J.additive_residual(m, mask)
        per_day[d] = float(r[0, 0])
    by_year = defaultdict(list)
    by_ym = defaultdict(list)
    for d, v in per_day.items():
        by_year[d[:4]].append(v)
        by_ym[(d[:4], d[5:7])].append(v)
    print(f"   {'year':<6}{'n':>5}{'months':>8}{'median as sampled':>20}"
          f"{'median, months balanced':>26}")
    out = {}
    for y in sorted(by_year):
        months = sorted({m for (yy, m) in by_ym if yy == y})
        raw = statistics.median(by_year[y])
        # balanced: one median per month present, then the median of those
        bal = statistics.median(statistics.median(by_ym[(y, m)]) for m in months)
        print(f"   {y:<6}{len(by_year[y]):>5}{len(months):>8}"
              f"{raw:>+20.2f}{bal:>+26.2f}")
        out[y] = dict(n=len(by_year[y]), months=len(months),
                      median=raw, median_month_balanced=bal)
    common = sorted({m for (_, m) in by_ym},
                    key=lambda m: -len({y for (y, mm) in by_ym if mm == m}))
    print(f"   months present per year differ: "
          + ", ".join(f"{y}:{len({m for (yy, m) in by_ym if yy == y})}"
                      for y in sorted(by_year)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    if not (a.check or a.record):
        ap.print_help(); return
    rec = dict(stage="B41", diagnostic_only=True,
               diagnostic_reason="scores three assertions that were stated in "
                                 "the record without being run",
               statistic_separation=part_one(),
               interaction_directions=part_two(),
               tennessee_by_year=part_three())
    if a.record:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b41_statistic_audit.json"
        dest.write_text(json.dumps(rec, ensure_ascii=False, indent=2,
                                   sort_keys=True), encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
