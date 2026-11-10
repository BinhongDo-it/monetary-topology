"""B144 first look: the city x item price table read in units of the local salary,
at two scales. Exploratory, zero retrieval, nothing is scored.

The table is the third-party archive already on disk for B30-5 and B38
(data/raw/cost-of-living_v2.csv, 4,956 cities, 55 rows per city, one currency).
It carries a salary row, four rent rows and two purchase rows next to the goods
and services, so a price can be restated as a share of one month of local pay
without any exchange rate or price index.

Prints, in this order
  1. coverage, thinnest cells first
  2. per item, the slope of log price on log salary at two scales
       between  one point per country, the median over its cities
       within   cities inside one country, country means removed
     and each slope divided by the same-scale slope of one plain local row.
     Noise in the salary row scales every item's slope by one common factor at a
     given scale, so it cancels in that ratio. The ratio is still a quotient of
     two estimates and is printed here as a description only.
  3. the same within-country profile country by country, where it is thick enough
  4. one placebo: salaries shuffled inside each country
  5. for named countries, what one month of local pay buys, by kind of row

Item classes are the ones in experiments/b30_7_city_pair.py, assigned from the
item description. Housing rows are split out of LOCAL by name. The mobile plan
row is dropped at source (redefined between vintages) and the mortgage rate is
not a price.

Units. The item names come from pages displayed in imperial units; the archive
itself is metric, which is what the unit factors in column_map.json record
(1.6388 on the purchase rows is the exchange rate times 10.764). So the purchase
rows are per square metre, and block 5 prices a 60 square metre flat.

Run:
    python experiments\\b144_first_look.py
"""
import csv
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "raw" / "cost-of-living_v2.csv"
NAMES = ROOT / "data" / "b30_5" / "column_map.json"

STATE = ["x33", "x27", "x28", "x29", "x30", "x31", "x32", "x36"]
LADDER = ["x34", "x35", "x3", "x9", "x10", "x11", "x26", "x23", "x24", "x25",
          "x46", "x45", "x44", "x47", "x6", "x38"]
FRESH = [f"x{i}" for i in range(12, 23)]
LOCAL = ["x1", "x2", "x4", "x5", "x7", "x8", "x41", "x39", "x40", "x42", "x43"]
RENT = ["x48", "x49", "x50", "x51"]
BUY = ["x52", "x53"]
CLASSES = [("LADDER", LADDER), ("STATE", STATE), ("FRESH", FRESH),
           ("LOCAL", LOCAL), ("RENT", RENT), ("BUY", BUY)]
SAL, REF = "x54", "x1"       # salary row; reference row = inexpensive restaurant meal
MIN_WITHIN = 8               # cities a country needs to enter the pooled within slope
MIN_OWN = 40                 # cities a country needs to be printed on its own
SHOW = ["Singapore", "China", "United States", "South Korea", "Japan", "Germany",
        "Switzerland", "Hong Kong", "Taiwan", "India", "Vietnam", "Egypt",
        "Turkey", "Spain", "Australia"]


def load():
    rows = []
    with TABLE.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            d = {"city": r["city"], "country": r["country"]}
            for k, v in r.items():
                if k.startswith("x"):
                    try:
                        val = float(v)
                        d[k] = math.log(val) if val > 0 else None
                    except (TypeError, ValueError):
                        d[k] = None
            rows.append(d)
    return rows


def slope(pairs, least=3):
    n = len(pairs)
    if n < least:
        return None
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    sxx = sum((a - mx) ** 2 for a, _ in pairs)
    return sum((a - mx) * (b - my) for a, b in pairs) / sxx if sxx else None


def demeaned(by_c, x, shuffled=False):
    out = []
    for rs in by_c.values():
        if len(rs) < MIN_WITHIN:
            continue
        sal = [r[SAL] for r in rs]
        if shuffled:
            random.shuffle(sal)
        pr = [(s, r[x]) for s, r in zip(sal, rs) if r[x] is not None]
        if len(pr) < 5:
            continue
        ms = sum(a for a, _ in pr) / len(pr)
        mp = sum(b for _, b in pr) / len(pr)
        out += [(a - ms, b - mp) for a, b in pr]
    return out


def fmt(v, w=7, p=2):
    return " " * (w - 3) + "n/a" if v is None else f"{v:{w}.{p}f}"


def main():
    names = {k: v["item"].split(" :: ")[-1][:44] for k, v in
             json.loads(NAMES.read_text(encoding="utf-8"))["mapping"].items()}
    rows = load()
    with_sal = [r for r in rows if r[SAL] is not None]
    by_c = defaultdict(list)
    for r in with_sal:
        by_c[r["country"]].append(r)
    items = [x for _, cols in CLASSES for x in cols]

    print("== 1. coverage")
    print(f"cities {len(rows)}, with a salary row {len(with_sal)}, "
          f"countries with a salary row {len(by_c)}")
    sizes = sorted((len(v), k) for k, v in by_c.items())
    print("fewest cities:", sizes[:3], "| most:", sizes[-5:])
    print(f"countries with >= {MIN_WITHIN} salary-carrying cities:",
          sum(1 for n, _ in sizes if n >= MIN_WITHIN))
    fill = sorted((sum(1 for r in with_sal if r[x] is not None), x) for x in items)
    print("thinnest item rows (cities with both the item and the salary):",
          [(n, names[x]) for n, x in fill[:3]])

    cmed = {c: {x: (st.median([r[x] for r in rs if r[x] is not None])
                    if any(r[x] is not None for r in rs) else None)
                for x in items + [SAL]} for c, rs in by_c.items()}

    res = {}
    for x in items:
        bt = [(cmed[c][SAL], cmed[c][x]) for c in cmed if cmed[c][x] is not None]
        wi = demeaned(by_c, x)
        res[x] = (slope(bt), len(bt), slope(wi), len(wi))
    rb, rw = res[REF][0], res[REF][2]

    print(f"\n== 2. slope of log price on log salary; reference row = {names[REF]!r}")
    print(f"reference slopes: between {rb:.3f}, within {rw:.3f}")
    print(f"{'class':7} {'item':44} {'between':>8} {'n':>4} {'within':>8} {'n':>6}"
          f" {'rel_bt':>7} {'rel_wi':>7} {'wi/bt':>6}")
    agg = defaultdict(list)
    for k, cols in CLASSES:
        for x in sorted(cols, key=lambda x: res[x][0]):
            b_bt, n_bt, b_wi, n_wi = res[x]
            r1, r2 = b_bt / rb, b_wi / rw
            agg[k].append((r1, r2, b_bt, b_wi))
            print(f"{k:7} {names[x]:44} {b_bt:8.3f} {n_bt:4d} {b_wi:8.3f} {n_wi:6d}"
                  f" {r1:7.2f} {r2:7.2f} {r2 / r1:6.2f}")
    print("\nclass medians: absolute slope between | within, then relative between | within")
    for k, _ in CLASSES:
        v = agg[k]
        print(f"  {k:7} n={len(v):2d}   {st.median(a[2] for a in v):.3f} | "
              f"{st.median(a[3] for a in v):.3f}     {st.median(a[0] for a in v):.2f} | "
              f"{st.median(a[1] for a in v):.2f}")

    print(f"\n== 3. the within-country profile, country by country (>= {MIN_OWN} cities);"
          " each cell is the class median of item slope / own reference slope")
    print(f"{'country':16} {'n':>4} {'sd(logW)':>8} {'ref_b':>7} "
          + " ".join(f"{k:>7}" for k, _ in CLASSES))
    for n, c in sorted(((len(v), c) for c, v in by_c.items() if len(v) >= MIN_OWN),
                       reverse=True):
        rs = by_c[c]
        ref = slope([(r[SAL], r[REF]) for r in rs if r[REF] is not None], 8)
        cells = []
        for _, cols in CLASSES:
            v = [s / ref for s in (slope([(r[SAL], r[x]) for r in rs if r[x] is not None], 8)
                                   for x in cols if x != REF) if s is not None] if ref else []
            cells.append(st.median(v) if v else None)
        print(f"{c:16} {n:4d} {st.pstdev(r[SAL] for r in rs):8.3f} {fmt(ref)} "
              + " ".join(fmt(v) for v in cells))

    print("\n== 4. placebo: pooled within-country slope, real | salary shuffled inside country")
    random.seed(20261012)
    for k, cols in CLASSES:
        real = st.median(s for s in (slope(demeaned(by_c, x)) for x in cols) if s is not None)
        fake = st.median(s for s in (slope(demeaned(by_c, x, True)) for x in cols)
                         if s is not None)
        print(f"  {k:7} {real:7.3f} | {fake:7.3f}")

    def units(c, cols):
        v = [cmed[c][SAL] - cmed[c][x] for x in cols if cmed[c][x] is not None]
        return math.exp(st.median(v)) if v else float("nan")

    def one(c, x):
        return math.exp(cmed[c][SAL] - cmed[c][x]) if cmed[c][x] is not None else float("nan")

    print("\n== 5. one month of local net salary, in units of each kind of row "
          "(country medians over cities)")
    print(f"{'country':14} {'cities':>6} {'salary':>7} {'ladder':>7} {'fresh':>7} {'local':>7}"
          f" {'rent_1BR_out':>12} {'sqm_out':>9} {'years/60sqm':>13}")
    for c in SHOW:
        if c not in cmed:
            print(f"{c:14} not in table")
            continue
        sq = one(c, "x53")
        print(f"{c:14} {len(by_c[c]):6d} {math.exp(cmed[c][SAL]):7.0f} {units(c, LADDER):7.1f}"
              f" {units(c, FRESH):7.1f} {units(c, LOCAL):7.1f} {one(c, 'x49'):12.2f}"
              f" {sq:9.2f} {60 / sq / 12:13.1f}")
    us = "United States"
    print(f"\nthe same five numbers as ratios to the {us} row; one conversion factor per "
          "country would print one number across each line")
    for c in SHOW:
        if c not in cmed or c == us:
            continue
        five = [units(c, LADDER) / units(us, LADDER), units(c, FRESH) / units(us, FRESH),
                units(c, LOCAL) / units(us, LOCAL), one(c, "x49") / one(us, "x49"),
                one(c, "x53") / one(us, "x53")]
        print(f"{c:14} ladder {five[0]:5.2f}  fresh {five[1]:5.2f}  local {five[2]:5.2f}  "
              f"rent {five[3]:5.2f}  buy {five[4]:5.2f}   max/min {max(five) / min(five):5.1f}")


if __name__ == "__main__":
    main()
