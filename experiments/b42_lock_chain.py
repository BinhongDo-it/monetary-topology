"""Is a lock count a transit count? The river answers in its own arithmetic.

The B42 result document explains a null by saying that a lock counts grain
passing it, including grain loaded a hundred miles upstream, while the price
position counts what the elevators in one district buy. That was argued from
what the two things are, and an argument from definitions is worth having, but
this one makes an arithmetic prediction and the panel can score it.

If a lock is a transit count then flow cannot fall going downstream, and the
count at a lock below a confluence has to be about the sum of the counts on the
two branches above it. On the upper Mississippi, Lock 26 sits below the point
where the Illinois River joins, and La Grange is the Illinois River lock in the
panel, so Lock 26 should be about Lock 25 plus La Grange. Nothing about the
price side enters this, so the check cannot be tuned to give the answer that
suits the null.

    python experiments/b42_lock_chain.py --check --record

Reads only what is cached. No network, no key.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import statistics
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "b42" / "agtransport"
OUT = REPO / "results"

# Downstream order on the upper Mississippi. The Illinois River joins above
# Lock 26, which is why La Grange enters the additivity check and not the
# chain check.
CHAIN = [("MS Lock 15", "MS Lock 25"), ("MS Lock 25", "MS Lock 26"),
         ("MS Lock 26", "MS Locks 27")]
SINCE = "2016"


def load():
    rows, missing = [], 0
    for f in sorted(glob.glob(str(DATA / "*.json"))):
        rows += json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    by: dict = defaultdict(dict)
    for r in rows:
        if "tons" not in r:
            missing += 1
            continue
        try:
            t = float(r["tons"])
        except (TypeError, ValueError):
            continue
        by[(r["date"][:10], r["commodity"])][r["lock"]] = t
    return by, len(rows), missing


def corr(x, y) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return (sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
            if sx and sy else float("nan"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--since", default=SINCE)
    a = ap.parse_args()
    if not (a.check or a.record):
        ap.print_help(); return

    by, n_rows, missing = load()
    print(f"{n_rows} rows, {missing} of them with no tons field at all "
          f"(skipped, and printed rather than dropped in silence)")
    out = {"rows": n_rows, "rows_without_tons": missing, "since": a.since,
           "by_commodity": {}}

    for com in ("Corn", "Soybeans"):
        print(f"\n=== {com}, weeks since {a.since}")
        rec = {"chain": [], "additivity": None}
        for up, dn in CHAIN:
            x, y = [], []
            for (d, c), v in by.items():
                if c != com or d < a.since:
                    continue
                if up in v and dn in v:
                    x.append(v[up]); y.append(v[dn])
            if len(x) < 50:
                print(f"  {up} -> {dn}: n={len(x)}"); continue
            ge = sum(1 for p, q in zip(x, y) if q >= p) / len(x)
            rat = statistics.median((q + 1) / (p + 1) for p, q in zip(x, y))
            r = corr(x, y)
            print(f"  {up:<13} -> {dn:<13} n={len(x):>4}  corr={r:+.3f}"
                  f"  P(down>=up)={ge:.2f}  median ratio={rat:.2f}")
            rec["chain"].append(dict(upstream=up, downstream=dn, n=len(x),
                                     corr=r, p_nondecreasing=ge, ratio=rat))
        xs = []
        for (d, c), v in by.items():
            if c != com or d < a.since:
                continue
            if all(k in v for k in ("MS Lock 25", "IL La Grange", "MS Lock 26")):
                xs.append((v["MS Lock 25"], v["IL La Grange"], v["MS Lock 26"]))
        if len(xs) > 50:
            pred = [p + q for p, q, _ in xs]
            act = [c for _, _, c in xs]
            inc = [c - (p + q) for p, q, c in xs]
            r = corr(pred, act)
            ratio = statistics.median((c + 1) / (p + 1)
                                      for p, c in zip(pred, act))
            print(f"  additivity 26 ~ 25 + La Grange: n={len(xs)} corr={r:+.3f}"
                  f"  median actual/predicted={ratio:.2f}")
            print(f"    corr(26, 25 alone)       = "
                  f"{corr([p for p, _, _ in xs], act):+.3f}")
            print(f"    corr(26, La Grange alone) = "
                  f"{corr([q for _, q, _ in xs], act):+.3f}")
            print(f"    local increment 26-(25+LG): median "
                  f"{statistics.median(inc):+,.0f} tons, negative in "
                  f"{sum(1 for v in inc if v < 0) / len(inc):.0%} of weeks")
            rec["additivity"] = dict(
                n=len(xs), corr=r, ratio=ratio,
                corr_25_alone=corr([p for p, _, _ in xs], act),
                corr_lagrange_alone=corr([q for _, q, _ in xs], act),
                increment_median=statistics.median(inc),
                increment_share_negative=sum(1 for v in inc if v < 0) / len(inc))
        out["by_commodity"][com] = rec

    if a.record:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b42_lock_chain.json"
        dest.write_text(json.dumps(dict(
            stage="B42", diagnostic_only=True,
            diagnostic_reason="scores the transit reading of the lock panel "
                              "against the river's own arithmetic",
            **out), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
