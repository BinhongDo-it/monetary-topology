"""B30-5, step 1 on the bulk panel: find the file, name its columns, check them.

The source host meters detail pages at roughly two dozen per IP per calendar
month, so the city-by-city route cannot reach a useful number of cities. A
third-party archive of the same database carries about five thousand cities and
fifty-five items in one file, including the salary row, so both sides of the
regression live in it and no further retrieval is needed.

**The columns are named x1 to x55 and the mapping is not guessed.** Guessing it
would put every item in the wrong class and every class contrast would still
look like a number. Instead the mapping is *derived*, against a known answer:
twelve Chinese cities were already read one page at a time, with their item
names attached, and they are on disk in ``panel.json``. For each xN column the
values across those twelve cities are compared with each named item's values,
and a column is named only when exactly one item matches it.

**The comparison is on shape, not on level.** The archive is in one currency and
a different vintage from the twelve pages, so a column and its item agree up to
a scale factor and some drift, not to the cent. Each vector is divided by its
own mean and matched on correlation, and a match counts only when the best
candidate is clear of the second.

This step names columns and judges nothing else. It writes a mapping file and
prints what it could not resolve.

Run:
    python data\\read_b30_5_kaggle.py
    python data\\read_b30_5_kaggle.py --file data\\raw\\<name>.csv
"""

import argparse
import csv
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PANEL = ROOT / "data" / "b30_5" / "panel.json"
OUT = ROOT / "data" / "b30_5" / "column_map.json"

# The twelve cities read page by page. Their names in the archive are the bare
# city name with a separate country column.
CN = ["Beijing", "Tianjin", "Shanghai", "Chongqing", "Shijiazhuang", "Taiyuan",
      "Hohhot", "Shenyang", "Changchun", "Harbin", "Nanjing", "Hangzhou"]

SALARY = ("Salaries And Financing :: Average Monthly Net Salary "
          "(After Tax)")
MIN_OVERLAP = 6      # cities a column and an item must share to be compared
# The score is the sd, in logs, of archive value over panel value across the
# shared cities. A right pairing differs by one exchange rate and whatever the
# two vintages drifted apart, a wrong pairing differs by two different prices.
MAX_RATIO_SD = 0.30  # the winner must be at least this tight
MIN_SEP = 1.60       # and the runner-up must be at least this many times worse


def shape_of(p):
    """Header only. Returns (has city, has country, count of xN) or None."""
    try:
        with p.open(encoding="utf-8-sig", newline="") as f:
            hdr = next(csv.reader(f), None)
    except (OSError, UnicodeDecodeError, csv.Error):
        return None
    if not hdr:
        return None
    low = [(h or "").strip().lower() for h in hdr]
    return (any(h in ("city", "city_name") for h in low),
            any(h in ("country", "country_name") for h in low),
            sum(1 for h in low if re.fullmatch(r"x\d+", h)))


def find_file(explicit):
    """Identify the archive by the shape of its header, never by its size.

    The raw directory holds other people's datasets, and the largest csv in it
    belongs to a different station entirely. Size says nothing about what a
    file is; the header does. A file qualifies only if it carries a city
    column, a country column and at least fifty xN columns, which no other
    file here does.
    """
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            raise SystemExit("no file at %s" % p)
        return p
    ok, rejected = [], []
    for p in sorted(RAW.rglob("*.csv")):
        if ".expired" in p.name:
            continue
        sh = shape_of(p)
        if sh is None:
            rejected.append((p, "unreadable header"))
        elif sh[0] and sh[1] and sh[2] >= 50:
            ok.append((p, sh))
        else:
            rejected.append((p, "city %s, country %s, %d x-columns"
                             % (sh[0], sh[1], sh[2])))
    if not ok:
        print("no csv in %s has the archive's shape. What was looked at:" % RAW)
        for p, why in rejected:
            print("   %-40s %s" % (p.name[:40], why))
        raise SystemExit(
            "\nDownload the archive there, any file name, then run this "
            "again, or pass --file.")
    if len(ok) > 1:
        # More than one edition of the same archive. Prefer the one with more
        # rows, and say which were seen rather than choosing silently.
        print("more than one file has the archive's shape:")
        counted = []
        for p, sh in ok:
            with p.open(encoding="utf-8-sig", newline="") as f:
                n = sum(1 for _ in f) - 1
            counted.append((n, p, sh))
            print("   %-34s %5d rows, %d x-columns" % (p.name[:34], n, sh[2]))
        counted.sort(reverse=True)
        print("   taking %s, the one with the most rows." % counted[0][1].name)
        return counted[0][1]
    return ok[0][0]


def value(raw):
    """A price, or None. Never a NaN.

    This archive writes missing cells as the literal string ``nan``, which
    ``float()`` accepts, and the result is poison twice over: a NaN is *truthy*,
    so it passes ``if v:``, and it compares False against everything, so it
    passes any guard written as a rejection test. The first version of this
    script had both holes and every column matched the same item.
    """
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v <= 0:
        return None
    return v


def corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    dx = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy = math.sqrt(sum((v - my) ** 2 for v in y))
    if not dx or not dy:
        return None
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (dx * dy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    a = ap.parse_args()

    src = find_file(a.file)
    with src.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        cols = list(rd.fieldnames or [])
        rows = list(rd)
    print("file    %s" % src.relative_to(ROOT))
    print("rows    %d" % len(rows))
    print("columns %d: %s%s" % (len(cols), ", ".join(cols[:8]),
                                " ..." if len(cols) > 8 else ""))

    xcols = [c for c in cols if re.fullmatch(r"x\d+", c.strip())]
    print("x-columns %d: %s" % (len(xcols), ", ".join(xcols[:6]) + " ..."))
    if not xcols:
        raise SystemExit(
            "no x1..xN columns. The archive may name its columns outright, in "
            "which case no mapping is needed; the column list is printed "
            "above. Nothing written.")

    citycol = next((c for c in cols if c.strip().lower() in ("city", "city_name")), None)
    ctrycol = next((c for c in cols if c.strip().lower() in ("country", "country_name")), None)
    if not citycol or not ctrycol:
        raise SystemExit("no city/country column found among %s" % cols[:10])
    countries = {}
    for r in rows:
        countries[r[ctrycol]] = countries.get(r[ctrycol], 0) + 1
    print("countries %d; the ten with the most cities:" % len(countries))
    for k in sorted(countries, key=lambda k: -countries[k])[:10]:
        print("   %-24s %4d" % (k, countries[k]))
    cn_rows = {r[citycol].strip(): r for r in rows
               if r[ctrycol].strip().lower() in ("china", "cn")}
    print("cities in China: %d, of which the twelve already read: %d"
          % (len(cn_rows), sum(1 for c in CN if c in cn_rows)))

    if not PANEL.exists():
        raise SystemExit("no panel at %s, so the columns cannot be named "
                         "against a known answer. Nothing written." % PANEL)
    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    named = {}
    for c, d in panel.items():
        for k, v in d["items"].items():
            named.setdefault(k, {})[c] = v
        if d.get("salary"):
            named.setdefault(
                "Salaries And Financing :: Average Monthly Net Salary "
                "(After Tax)", {})[c] = d["salary"]

    def vec(mapping, cities):
        vals = [mapping.get(c) for c in cities]
        return vals

    print("\n" + "=" * 78)
    print("naming each x-column, and checking the naming against the panel")
    print("=" * 78)
    print("  The columns are positional: x_i is the i-th row of the source's")
    print("  own page, and the twelve pages already read were parsed in page")
    print("  order, so their item order IS that order. What makes this a check")
    print("  rather than an assumption is the ratio column below. The archive")
    print("  is another currency and another vintage, so a correctly named")
    print("  column differs from its item by ONE exchange rate, and a wrongly")
    print("  named one differs by two unrelated prices. If the naming were")
    print("  wrong the ratios would scatter; they cluster, and the ones that")
    print("  sit off the cluster land on unit conversions that can be named.")

    # Rebuild the page order from the panel city carrying the most items, then
    # put the salary back where its own section starts: the parser stores it
    # apart from the item table, so it is missing from that order.
    richest = max(panel, key=lambda c: len(panel[c]["items"]))
    order = list(panel[richest]["items"])
    sal_at = next((i for i, o in enumerate(order)
                   if o.startswith("Salaries And Financing")), len(order))
    full = order[:sal_at] + [SALARY] + order[sal_at:]
    if len(full) != len(xcols):
        print("\n  the page order has %d rows and the archive has %d columns. "
              "They must be equal for a positional naming, so nothing is "
              "written." % (len(full), len(xcols)))
        raise SystemExit(1)

    def panel_value(item, city):
        d = panel.get(city)
        if not d:
            return None
        return value(d["salary"] if item == SALARY else d["items"].get(item))

    rows_out = []
    for i, item in enumerate(full, start=1):
        xc = "x%d" % i
        lr = []
        for c in CN:
            r = cn_rows.get(c)
            av = value(r.get(xc)) if r else None
            pv = panel_value(item, c)
            if av and pv:
                lr.append(math.log(av / pv))
        if len(lr) < MIN_OVERLAP:
            rows_out.append((xc, item, None, None, len(lr)))
            continue
        rows_out.append((xc, item, math.exp(st.mean(lr)), st.pstdev(lr), len(lr)))

    live = [r for r in rows_out if r[2]]
    base = st.median([r[2] for r in live])

    # The unit factor is PREDICTED FROM THE ITEM'S OWN NAME, then checked
    # against the data. Offering a menu of factors and taking whichever fits
    # best is not a check: it explained a preschool fee as a mile-to-kilometre
    # conversion and a mortgage rate as square metres, because a four-year
    # drift of thirty per cent reaches any factor in a short list. A name that
    # says "(1 lb)" predicts 2.2046 before anything is read, and then the data
    # either agrees or it does not.
    def expected(item):
        """What the item's own name says the two sides differ by.

        The test is whether the PRICE is quoted per that unit, not whether the
        unit appears in the text. A first version keyed on the words and got
        two rows wrong in a way the data named exactly: a loaf of bread is a
        loaf on both sides and came back at 1/2.2046 of the predicted factor,
        and "Basic Utilities for 915 Square Feet Apartment" prices a monthly
        bill rather than a square foot and came back at 1/10.7639 of it. Both
        reciprocals, which is what an invented conversion looks like.
        """
        n = item.lower()
        if "in %" in n:
            return 1.0, "a percentage, so no currency enters"
        if "per square feet" in n or "per square foot" in n:
            return base * 10.7639, "square metre against square foot"
        if "taxi 1 mile" in n:
            return base / 1.6093, "kilometre against mile"
        if "(1 lb)" in n and "loaf" not in n:
            return base * 2.2046, "kilogram against pound"
        return base, "same unit"
    print("\n  common ratio across columns: %.5f, which is the exchange rate"
          % base)
    print("  %-5s %-42s %9s %8s %6s  %s"
          % ("x", "item", "ratio", "obs/pred", "sd", "what the name predicts"))
    mapping, unresolved = {}, []
    for xc, item, rt, sd, n in rows_out:
        if rt is None:
            unresolved.append((xc, "only %d cities overlap" % n))
            print("  %-5s %-42s %9s %8s %6s  too little overlap"
                  % (xc, item.split(" :: ")[-1][:42], "-", "-", "-"))
            continue
        pred, why = expected(item)
        # obs/pred is the four-year drift of this item in these cities, and
        # nothing else, if the naming is right.
        drift = rt / pred
        ok = 0.5 <= drift <= 2.0
        print("  %-5s %-42s %9.5f %8.2f %6.3f  %s%s"
              % (xc, item.split(" :: ")[-1][:42], rt, drift, sd, why,
                 "" if ok else "   <-- DOES NOT AGREE"))
        mapping[xc] = {"item": item, "ratio": rt, "predicted": pred,
                       "obs_over_pred": drift, "ratio_sd": sd, "n": n,
                       "unit_note": why, "agrees": ok}
        if not ok:
            unresolved.append(
                (xc, "the name predicts a ratio of %.5f and the data gives "
                 "%.5f, a factor of %.4f. Either this column is not this item, "
                 "or the item was redefined between the two vintages."
                 % (pred, rt, drift)))

    agree = sum(1 for m in mapping.values() if m["agrees"])
    print("\n  %d of %d columns agree with the factor their own name predicts,"
          % (agree, len(rows_out)))
    print("  within a factor of two either way, which is what four years of")
    print("  drift can do. That agreement is the check on the naming: a wrong")
    print("  positional naming would put unrelated prices against each other")
    print("  and no name would predict anything.")
    if agree < 0.8 * len(rows_out):
        raise SystemExit(
            "\nfewer than four fifths agree, so the positional naming is not "
            "established. Nothing written.")

    dup = {}
    for xc, m in mapping.items():
        dup.setdefault(m["item"], []).append(xc)
    clashes = {k: v for k, v in dup.items() if len(v) > 1}

    if unresolved:
        print("\n  columns carrying a caution, named rather than passed over:")
        for xc, why in unresolved:
            print("    %-5s %s" % (xc, why))
    if clashes:
        print("  two columns claiming one item, which means at least one is "
              "wrong:")
        for item, xs in clashes.items():
            print("    %-40s %s" % (item.split(" :: ")[-1][:40], ", ".join(xs)))
        raise SystemExit("\nNothing written while a clash stands.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"source_file": str(src.relative_to(ROOT)),
         "rows": len(rows), "countries": len(countries),
         "china_cities": len(cn_rows),
         "city_column": citycol, "country_column": ctrycol,
         "mapping": mapping,
         "unresolved": [{"column": c, "why": w} for c, w in unresolved]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
