"""B30-5 on the bulk panel: the same criterion run once per country.

**What changed and why.** The station was written to run on Chinese cities and
stalled at twelve of them, because the source meters detail pages per calendar
month. The bulk archive carries thousands of cities across dozens of countries
and includes the salary row, so the same criterion can be run **inside each
country separately** and the results compared across countries.

Countries are not pooled. Pooling would put currencies, tax regimes and
different brand sets on one line and the coefficient would be about none of
them. Each country is its own carrier, and the criterion is the same one in all
of them.

**The statistic per country**, for item `i` over that country's cities `c`:

    log P(i,c) = a_i + b_i * log Y(c) + e(i,c)

then the median `b` over the LADDER items and over the LOCAL items, and the gap
between the two. **The class of each item is fixed in advance from its
description**, in `b30_5_income_loading.py`, and is not re-assigned per country.

**The summary is a count, not a line on an estimator.** In how many countries is
the LADDER median below the LOCAL median? If the class assignment carried no
information the sign would fall either way with probability one half, so the
count has an exact null and the two-sided sign-test probability is printed
beside it. No threshold is registered on any `b`, on any gap, or on the count.

**A limit stated before the run.** The class assignment was written for China.
Most of it travels without argument -- Levi's, Nike, a VW Golf and a McDonald's
meal are branded the same way everywhere, rent and apartment prices are
non-tradeable everywhere, a restaurant meal is produced where it is sold
everywhere. Two rows are shakier abroad than at home: packaged rice and milk are
branded groceries in some countries and bulk commodities in others. Every item's
own `b` is printed per country, so any row can be re-argued, and a country where
the assignment fails is a reading about that country's retail structure rather
than a verdict on the criterion.

Run:
    python experiments\\b30_5_global_classes.py
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "b30_5" / "column_map.json"
OUT = ROOT / "results" / "b30_5_global_classes.json"

MIN_CITIES = 12          # the registered minimum, unchanged
MIN_ITEMS_PER_CLASS = 4  # enough items to take a median of
SALARY_ITEM = ("Salaries And Financing :: Average Monthly Net Salary "
               "(After Tax)")


def ols_slope(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    if sxx == 0:
        return None, None
    b = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / sxx
    a = my - b * mx
    res = [y[i] - (a + b * x[i]) for i in range(n)]
    return b, st.pstdev(res)


def sign_test(k, n):
    """Two-sided exact probability of k or more of n at p = 1/2."""
    if n == 0:
        return None
    def C(n, r):
        return math.comb(n, r)
    tail = sum(C(n, r) for r in range(k, n + 1)) / (2.0 ** n)
    return min(1.0, 2.0 * tail)


def main():
    if not MAP.exists():
        raise SystemExit(
            "no column map at %s. Run data/read_b30_5_kaggle.py first: it "
            "names the columns against the twelve pages already read, and "
            "until they are named every class contrast would be computed on "
            "items in the wrong classes and would still print a number." % MAP)
    spec = json.loads(MAP.read_text(encoding="utf-8"))

    import csv
    import importlib.util
    s = importlib.util.spec_from_file_location(
        "loading", str(ROOT / "experiments" / "b30_5_income_loading.py"))
    loading = importlib.util.module_from_spec(s)
    s.loader.exec_module(loading)
    CLASS = loading.CLASS

    src = ROOT / spec["source_file"]
    with src.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    citycol, ctrycol = spec["city_column"], spec["country_column"]
    colitem = {c: m["item"] for c, m in spec["mapping"].items()}
    salcol = next((c for c, it in colitem.items() if it == SALARY_ITEM), None)
    if salcol is None:
        raise SystemExit(
            "the salary column was not named, so there is no right-hand side. "
            "read_b30_5_kaggle.py lists what it could not name. Nothing run.")

    by_country = {}
    for r in rows:
        by_country.setdefault((r[ctrycol] or "").strip(), []).append(r)

    def num(r, c):
        try:
            v = float(r[c])
            return v if v > 0 else None
        except (TypeError, ValueError, KeyError):
            return None

    results, skipped = [], []
    for country, crows in sorted(by_country.items()):
        usable = [r for r in crows if num(r, salcol)]
        if len(usable) < MIN_CITIES:
            skipped.append((country, "%d cities with a salary" % len(usable)))
            continue
        ly = [math.log(num(r, salcol)) for r in usable]
        per_item = {}
        for col, item in colitem.items():
            if item == SALARY_ITEM:
                continue
            pts = [(ly[i], math.log(v)) for i, r in enumerate(usable)
                   if (v := num(r, col))]
            if len(pts) < MIN_CITIES:
                continue
            b, sd = ols_slope([p[0] for p in pts], [p[1] for p in pts])
            if b is not None:
                per_item[item] = {"b": b, "n": len(pts), "resid_sd": sd,
                                  "class": CLASS.get(item, "?")}
        lad = [v["b"] for v in per_item.values() if v["class"] == "LADDER"]
        loc = [v["b"] for v in per_item.values() if v["class"] == "LOCAL"]
        if len(lad) < MIN_ITEMS_PER_CLASS or len(loc) < MIN_ITEMS_PER_CLASS:
            skipped.append((country, "LADDER %d, LOCAL %d items"
                            % (len(lad), len(loc))))
            continue
        results.append({
            "country": country, "cities": len(usable),
            "sd_log_income": st.pstdev(ly),
            "ladder_n": len(lad), "local_n": len(loc),
            "ladder_median": st.median(lad), "local_median": st.median(loc),
            "gap": st.median(loc) - st.median(lad),
            "items": per_item,
        })

    if not results:
        raise SystemExit("no country cleared the minimum. Nothing judged.")

    print("=" * 78)
    print("the same criterion, once per country. Countries are never pooled")
    print("=" * 78)
    print("  %-26s %6s %8s %8s %8s %8s"
          % ("country", "cities", "LADDER", "LOCAL", "gap", "sd(logY)"))
    for r in sorted(results, key=lambda r: -r["gap"]):
        print("  %-26s %6d %8.3f %8.3f %8.3f %8.3f"
              % (r["country"], r["cities"], r["ladder_median"],
                 r["local_median"], r["gap"], r["sd_log_income"]))

    n = len(results)
    k = sum(1 for r in results if r["gap"] > 0)
    p = sign_test(max(k, n - k), n)
    print("\n" + "=" * 78)
    print("the count, which is the reading")
    print("=" * 78)
    print("  countries meeting the minimum       %d" % n)
    print("  LADDER median below LOCAL median    %d" % k)
    print("  the other way                       %d" % (n - k))
    print("  two-sided sign test at one half     p = %.3g" % p)
    print("\n  The class assignment was fixed from item descriptions before any")
    print("  of this was read, and is the same in every country, so the count")
    print("  has an exact null and needs no threshold.")

    print("\n  kill branch: countries whose LADDER median sits above 0.5")
    hi = [r for r in results if r["ladder_median"] > 0.5]
    if hi:
        for r in hi:
            print("    %-26s LADDER %.3f" % (r["country"], r["ladder_median"]))
    else:
        print("    none")

    if skipped:
        print("\n  countries not entering, named rather than dropped quietly "
              "(%d):" % len(skipped))
        for c, why in skipped[:25]:
            print("    %-26s %s" % (c, why))
        if len(skipped) > 25:
            print("    ... and %d more, all in the record" % (len(skipped) - 25))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"min_cities": MIN_CITIES, "min_items_per_class": MIN_ITEMS_PER_CLASS,
         "countries": n, "gap_positive": k, "sign_test_p": p,
         "results": results,
         "skipped": [{"country": c, "why": w} for c, w in skipped]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
