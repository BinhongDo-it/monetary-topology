"""B30-5 cross-sectional: does an item's price load on the branch or on income.

Registered in ``docs/b30_prereg.md``, section "B30-5 cross-sectional". The limit
is stated there and repeated here because it decides what may be said: a
cross-section separates *loads on the branch* from *loads on local conditions*,
and does **not** separate *inherited down a tree* from *one common cause reaching
both places*. Only timing separates those and the timing is not obtainable.

For item ``i`` over cities ``c``::

    log P(i,c) = a_i + b_i * log Y(c) + e(i,c)

LADDER items are predicted near ``b = 0``: one brand posts one number nationally
and local input costs are ignored. LOCAL items are predicted near ``b = 1``.
**The kill branch is B30-5's own: if LADDER also comes back near one, regional
deviation loads on local conditions and the propagation file is wrong.**

No threshold is registered on ``b``. The reading is whether the two class
distributions separate, reported with the gap where they do, in the shape this
project arrived at after repeatedly finding that a line on an estimator buys
nothing.

Item keys carry their section. The source prints ``Imported Beer (12 oz Small
Bottle)`` twice, once under Restaurants and once under Markets, and those two
sit in **different classes**. An unqualified label would silently merge them.

Input: a panel written by the retrieval step, ``data/b30_5/panel.json``::

    {"<city>": {"salary": float,
                "updated": "...", "contributors": "...",
                "items": {"<Section> :: <label>": float, ...}}, ...}

Run:
    python b30_5_income_loading.py
"""

import argparse
import io
import json
import math
import statistics as st
from pathlib import Path

# Class assignment, from b30_propagation.md section 12.9, applied to each item's
# description and never to its numbers. Fixed before any city beyond the
# original pair was retrieved.
CLASS = {}


def _add(cls, section, labels):
    for lab in labels:
        CLASS["%s :: %s" % (section, lab)] = cls


_add("STATE", "Transportation", [
    "One-Way Ticket (Local Transport)",
    "Monthly Public Transport Pass (Regular Price)",
    "Taxi Start (Standard Tariff)",
    "Taxi 1 mile (Standard Tariff)",
    "Taxi 1 Hour Waiting (Standard Tariff)",
    "Gasoline (1 Liter)",
])
_add("STATE", "Markets", ["Cigarettes (Pack of 20, Marlboro)"])
_add("STATE", "Utilities", [
    "Basic Utilities for 915 Square Feet Apartment "
    "(Electricity, Heating, Cooling, Water, Garbage)",
])
_add("LADDER", "Transportation", [
    "Volkswagen Golf 1.5 (or Equivalent New Compact Car)",
    "Toyota Corolla Sedan 1.6 (or Equivalent New Mid-Size Car)",
])
_add("LADDER", "Restaurants", [
    "Combo Meal at McDonald's (or Equivalent Fast-Food Meal)",
    "Cappuccino (Regular Size)",
])
_add("LADDER", "Markets", [
    "Milk (Regular, 1 Liter)",
    "Fresh White Bread (1 lb Loaf)",
    "White Rice (1 lb)",
    "Bottled Water (50 oz)",
    "Bottle of Wine (Mid-Range)",
    "Domestic Beer (16.9 oz Bottle)",
    "Imported Beer (12 oz Small Bottle)",
])
_add("LADDER", "Utilities", [
    "Mobile Phone Plan (Monthly, with Calls and 10GB+ Data)",
    "Broadband Internet (Unlimited Data, 60 Mbps or Higher)",
])
_add("LADDER", "Clothing And Shoes", [
    "Jeans (Levi's 501 or Similar)",
    "Summer Dress in a Chain Store (e.g. Zara or H&M)",
    "Nike Running Shoes (Mid-Range)",
    "Men's Leather Business Shoes",
])
_add("FRESH", "Markets", [
    "Eggs (12, Large Size)",
    "Local Cheese (1 lb)",
    "Chicken Fillets (1 lb)",
    "Beef Round or Equivalent Back Leg Red Meat (1 lb)",
    "Apples (1 lb)", "Bananas (1 lb)", "Oranges (1 lb)",
    "Tomatoes (1 lb)", "Potatoes (1 lb)", "Onions (1 lb)",
    "Lettuce (1 Head)",
])
_add("LOCAL", "Restaurants", [
    "Meal at an Inexpensive Restaurant",
    "Meal for Two at a Mid-Range Restaurant (Three Courses, Without Drinks)",
    "Domestic Draft Beer (1 Pint)",
    "Imported Beer (12 oz Small Bottle)",
    "Soft Drink (Coca-Cola or Pepsi, 12 oz Small Bottle)",
    "Bottled Water (12 oz)",
])
_add("LOCAL", "Sports And Leisure", [
    "Monthly Fitness Club Membership",
    "Tennis Court Rental (1 Hour, Weekend)",
    "Cinema Ticket (International Release)",
])
_add("LOCAL", "Childcare", [
    "Private Full-Day Preschool or Kindergarten, Monthly Fee per Child",
    "International Primary School, Annual Tuition per Child",
])
_add("LOCAL", "Rent Per Month", [
    "1 Bedroom Apartment in City Centre",
    "1 Bedroom Apartment Outside of City Centre",
    "3 Bedroom Apartment in City Centre",
    "3 Bedroom Apartment Outside of City Centre",
])
_add("LOCAL", "Buy Apartment Price", [
    "Price per Square Feet to Buy Apartment in City Centre",
    "Price per Square Feet to Buy Apartment Outside of Centre",
])

MIN_CITIES = 12       # gate six, registered
ORDER = ("LADDER", "FRESH", "STATE", "LOCAL")


def ols(xs, ys):
    """Slope, intercept and residual sd. Two points give no residual sd."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None, None, None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    if n <= 2:
        return b, a, None
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    sd = math.sqrt(sum(r * r for r in res) / (n - 2))
    return b, a, sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    src = Path(a.panel) if a.panel else root / "data" / "b30_5" / "panel.json"
    if not src.exists():
        raise SystemExit("no panel at %s. Retrieval writes it." % src)
    panel = json.loads(io.open(src, encoding="utf-8").read())

    print("=" * 78)
    print("B30-5 cross-sectional: %d cities in the panel" % len(panel))
    print("=" * 78)
    # Volume is printed beside every city and used to filter nothing. The
    # window column matters: the carrier widens to 18 months and stops
    # printing an entry count for thin cities, so a blank entry count is
    # itself the thin reading rather than a gap.
    print("  %-16s %10s %6s %8s %7s %7s %s"
          % ("city", "salary", "items", "entries", "contrib", "window", "est"))
    for city in sorted(panel):
        d = panel[city]
        sal = d.get("salary")
        print("  %-16s %10s %6d %8s %7s %7s %s"
              % (city, ("%10.2f" % sal) if sal else "   no salary",
                 len(d["items"]), d.get("entries") or "-",
                 d.get("contributors") or "-", d.get("window_months") or "-",
                 "est" if d.get("estimated_flag") else ""))

    # Nothing is dropped quietly. Labels the panel carries that the class table
    # does not know are named, and registered labels a city lacks are named.
    seen = set()
    for d in panel.values():
        seen |= set(d["items"])
    unknown = sorted(seen - set(CLASS))
    missing = sorted(set(CLASS) - seen)
    print("\n  labels in the data with no class: %d%s"
          % (len(unknown), ("  " + "; ".join(unknown[:4])) if unknown else ""))
    print("  registered labels no city carries: %d%s"
          % (len(missing), ("  " + "; ".join(missing[:4])) if missing else ""))
    if unknown:
        print("  Every one of those is listed in the record. A label the class")
        print("  table does not know is not silently discarded.")

    # A city with no income row has no x coordinate, so it cannot enter a
    # regression on income. It is named here rather than dropped quietly, and
    # rather than crashing the read: those are three different outcomes and
    # only the first one leaves a record.
    cities = sorted(c for c in panel if panel[c].get("salary"))
    no_income = sorted(set(panel) - set(cities))
    if no_income:
        print("\n  cities carrying no income row, named and excluded from the "
              "regression only: %s" % ", ".join(no_income))
    if len(cities) < MIN_CITIES:
        print("\n  gate six: %d cities against a registered minimum of %d. "
              "Nothing is judged." % (len(cities), MIN_CITIES))
        return
    logY = {c: math.log(panel[c]["salary"]) for c in cities}
    sdY = st.pstdev(list(logY.values()))

    rows = []
    for key, cls in sorted(CLASS.items()):
        pts = [(logY[c], math.log(panel[c]["items"][key]))
               for c in cities
               if key in panel[c]["items"] and panel[c]["items"][key] > 0]
        if len(pts) < MIN_CITIES:
            rows.append({"item": key, "class": cls, "n": len(pts),
                         "b": None, "se": None, "sigma": None})
            continue
        b, _, sig = ols([p[0] for p in pts], [p[1] for p in pts])
        se = (sig / math.sqrt(len(pts)) / sdY) if (sig and sdY) else None
        rows.append({"item": key, "class": cls, "n": len(pts),
                     "b": b, "se": se, "sigma": sig})

    live = [r for r in rows if r["b"] is not None]
    sigmas = [r["sigma"] for r in live if r["sigma"]]
    print("\n" + "=" * 78)
    print("gate six, on the measured numbers rather than the assumed ones")
    print("=" * 78)
    print("  cities %d, sd(log salary) %.4f, median item residual sd %.4f"
          % (len(cities), sdY, st.median(sigmas) if sigmas else float("nan")))
    med_se = st.median([r["se"] for r in live if r["se"]]) if live else None
    print("  median se(b) %.4f" % (med_se if med_se else float("nan")))
    print("  The design assumed sigma 0.20 and sd(log Y) 0.30. Whatever those")
    print("  turn out to be, the gate is read here and not on the assumption.")
    if med_se and med_se > 0.35:
        print("\n  se(b) is too large to tell b = 0 from b = 1. Undecided, and")
        print("  the class distributions below are printed without a verdict.")

    print("\n" + "=" * 78)
    print("every item, its class and its loading. Any row can be re-argued")
    print("=" * 78)
    for cls in ORDER:
        got = sorted([r for r in rows if r["class"] == cls],
                     key=lambda r: (r["b"] is None, r["b"]))
        print("\n  %s" % cls)
        for r in got:
            if r["b"] is None:
                print("    %-64s n %2d  too few cities" % (r["item"][:64], r["n"]))
            else:
                print("    %-64s n %2d  b %+.3f  se %.3f"
                      % (r["item"][:64], r["n"], r["b"], r["se"] or float("nan")))

    print("\n" + "=" * 78)
    print("the two distributions, and whether they separate")
    print("=" * 78)
    dist = {}
    for cls in ORDER:
        bs = sorted(r["b"] for r in rows if r["class"] == cls and r["b"] is not None)
        dist[cls] = bs
        if bs:
            print("  %-7s n %2d  min %+.3f  median %+.3f  max %+.3f"
                  % (cls, len(bs), bs[0], st.median(bs), bs[-1]))
    L, O = dist.get("LADDER", []), dist.get("LOCAL", [])
    verdict = "UNDECIDED"
    if L and O:
        gap = O[0] - L[-1]
        if gap > 0:
            print("\n  LADDER's largest is %+.3f and LOCAL's smallest is %+.3f."
                  % (L[-1], O[0]))
            print("  They separate with an empty gap of %.3f." % gap)
            verdict = ("SEPARATE. LADDER loads on the branch and LOCAL on local "
                       "conditions, with no item of either class between them.")
        else:
            print("\n  The two ranges overlap by %.3f. No empty gap." % (-gap))
            verdict = ("OVERLAP. The classes do not separate on this panel; the "
                       "medians are reported and the overlap with them.")
        if st.median(L) > 0.5:
            verdict = ("KILL BRANCH. LADDER's median loading is %+.3f, near one "
                       "rather than near zero: regional deviation loads on local "
                       "conditions and the propagation file is wrong."
                       % st.median(L))
    print("\n  verdict: %s" % verdict)
    print("\n  What this does not settle, per the registered limit: a "
          "cross-section")
    print("  cannot separate inheritance down a branch from one common cause")
    print("  reaching every city. That needs timing, and the timing is the half")
    print("  the carrier does not supply.")

    rec = {"cities": cities, "sd_log_salary": sdY, "n_cities": len(cities),
           "median_se_b": med_se, "unknown_labels": unknown,
           "missing_labels": missing, "items": rows,
           "class_ranges": {k: {"n": len(v), "min": v[0] if v else None,
                                "median": st.median(v) if v else None,
                                "max": v[-1] if v else None}
                            for k, v in dist.items()},
           "verdict": verdict}
    out = Path(a.out) if a.out else root / "results" / "b30_5_income_loading.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
