"""B97, the goods side: a price that is not a bank rate, read at the same two dates.

Every instrument in the rate reading is a bank rate, so every one of them sits on the
cross-border edge through a bank's cost of funds. That is why the lifting moved all six of
them and why that reading cannot separate the edge from a general normalisation. A consumer
price is set by sellers of goods and services rather than by a bank's funding, so it is the
instrument that could have moved at one date and not the other.

Two things this file is careful about, both of them about scope:

    the null       these indices are not seasonally adjusted, and the carrier is a tourism
                   economy whose price level swings about three log points a year against the
                   euro area. A null pooled over every month has a different scope from a
                   statistic centred on one calendar month, so both nulls are printed: the
                   pooled one and the same-calendar-month one. The numbers differ.
    the dimension  an interest rate is a growth rate, so the quantity with its dimensions on
                   the goods side is the inflation differential, and the one with the
                   dimensions of a price level wedge is a cumulative interest factor. Both
                   readings are printed because the two comparisons disagree, and choosing
                   between them after seeing which one separates is the one real risk in this
                   kind of work.

    python experiments/b97_prices.py --steps      both objects, both nulls, both windows
    python experiments/b97_prices.py --seasonal   the same-month step for every year, so the
                                                  seasonal cycle is visible rather than assumed
"""
import argparse
import csv
import math
import pathlib
from collections import OrderedDict

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "hicp"

EDGE_DATES = OrderedDict([
    ("2014-05", "domestic transfer limit abolished (2014-05-05)"),
    ("2014-06", "domestic capital controls fully liberalised (2014-06-01)"),
    ("2015-04", "all remaining external restrictions lifted (2015-04-06)"),
])
CARRIER = "CY"
OTHER_LEG = "U2"
CONTROLS = ("GR", "SI", "MT", "PT", "IE")
WINDOWS = (3, 2)
EVENT_YEARS = (2013, 2014, 2015)

# label, key shape, whether the wedge is a log ratio (a level) or a plain difference (a rate)
OBJECTS = OrderedDict([
    ("relative price level, all items", ("N_000000_4_INX", True)),
    ("inflation differential, all items", ("N_000000_4_ANR", False)),
    ("inflation differential, services", ("N_SERV00_4_ANR", False)),
    ("inflation differential, core", ("N_XEF000_4_ANR", False)),
    ("inflation differential, food", ("N_FOOD00_4_ANR", False)),
    ("inflation differential, non-energy goods", ("N_IGXE00_4_ANR", False)),
    ("inflation differential, energy", ("N_NRGY00_4_ANR", False)),
    ("relative price level, services", ("N_SERV00_4_INX", True)),
    ("relative price level, non-energy goods", ("N_IGXE00_4_INX", True)),
])

# Two goods at two positions. Services are mostly local and non-energy industrial goods are
# mostly traded, and neither is priced off a bank's cost of funds, so this square owes nothing
# to banking. A single scalar carried by each position gives every good in that position the
# same wedge, so it predicts each of these is zero. A level shift common to everything sold in
# the carrier also cancels out of it, which is what the rate side could not do.
SQUARES = OrderedDict([
    ("services minus goods, inflation",
     ("N_SERV00_4_ANR", "N_IGXE00_4_ANR", False)),
    ("services minus goods, price level",
     ("N_SERV00_4_INX", "N_IGXE00_4_INX", True)),
    ("services minus energy, inflation",
     ("N_SERV00_4_ANR", "N_NRGY00_4_ANR", False)),
])


def months(a, b):
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    out = []
    while (ya, ma) <= (yb, mb):
        out.append(f"{ya:04d}-{ma:02d}")
        ma += 1
        if ma == 13:
            ya, ma = ya + 1, 1
    return out


def read(area, shape):
    path = RAW / f"ICP_M_{area}_{shape}.csv"
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    return {r["TIME_PERIOD"]: float(r["OBS_VALUE"])
            for r in rows if r["OBS_VALUE"].strip() not in ("", "NaN")}


def have(area, shape):
    return (RAW / f"ICP_M_{area}_{shape}.csv").exists()


def wedge(area, shape, log):
    a, u = read(area, shape), read(OTHER_LEG, shape)
    ts = sorted(set(a) & set(u))
    if log:
        return {t: 100.0 * (math.log(a[t]) - math.log(u[t])) for t in ts}
    return {t: a[t] - u[t] for t in ts}


def level_of(w, centre, side, win):
    ts = sorted(w)
    idx = [i for i, t in enumerate(ts) if t < centre] if side == "before" else \
          [i for i, t in enumerate(ts) if t >= centre]
    take = idx[-win:] if side == "before" else idx[:win]
    vals = [w[ts[i]] for i in take]
    return (sum(vals) / len(vals) if vals else float("nan")), len(vals)


def step_at(w, centre, win):
    b, nb = level_of(w, centre, "before", win)
    a, na = level_of(w, centre, "after", win)
    if nb < win or na < win:
        return None
    return a - b


def pooled_null(w, win, span=("2009-01", "2020-09")):
    """Every month that is not one of the dates. Right for a series with no seasonal cycle."""
    ts = [m for m in months(*span) if m in w]
    skip = set()
    for d in EDGE_DATES:
        i = len(months(span[0], d))
        skip |= {m for m in ts if abs(len(months(span[0], m)) - i) <= 2 * win}
    return [s for s in (step_at(w, m, win) for m in ts if m not in skip) if s is not None]


def same_month_null(w, centre, win):
    """The same calendar month in every other year, with the event years left out.

    A seasonal series has a different distribution in each calendar month, so this is the
    null whose scope matches a statistic centred on one of them.
    """
    mm = centre[5:7]
    out = []
    for y in range(2003, 2021):
        t = f"{y}-{mm}"
        if t == centre or y in EVENT_YEARS or t not in w:
            continue
        s = step_at(w, t, win)
        if s is not None:
            out.append(s)
    return out


def read_steps():
    print("Wedge against the euro area. A level object is 100 x log ratio, a rate object is a")
    print("plain difference in percentage points. Two nulls per cell: 'p' pools every month,")
    print("'s' takes the same calendar month in other years. These indices are not seasonally")
    print("adjusted, so the two nulls do not agree and the second is the one whose scope")
    print("matches the statistic.\\n")
    for label, (shape, log) in OBJECTS.items():
        areas = [a for a in [CARRIER] + list(CONTROLS) if have(a, shape)]
        if not have(OTHER_LEG, shape) or CARRIER not in areas:
            print(f"=== {label}: not on disk\\n")
            continue
        print(f"=== {label}")
        for win in WINDOWS:
            print(f"  window {win} month(s) either side")
            print("    area  " + "".join(f"{d:>28s}" for d in EDGE_DATES))
            cell = {}
            for a in areas:
                w = wedge(a, shape, log)
                pn = pooled_null(w, win)
                row = []
                for d in EDGE_DATES:
                    s = step_at(w, d, win)
                    cell[(a, d)] = s
                    if s is None:
                        row.append("(window does not fit)")
                        continue
                    sn = same_month_null(w, d, win)
                    kp = sum(1 for x in pn if abs(x) >= abs(s))
                    ks = sum(1 for x in sn if abs(x) >= abs(s))
                    row.append(f"{s:+6.2f} p{kp:3d}/{len(pn):3d} s{ks:2d}/{len(sn):2d}")
                print(f"    {a:4s}  " + "".join(f"{c:>28s}" for c in row))
            for d in EDGE_DATES:
                s = cell.get((CARRIER, d))
                oth = [cell[(a, d)] for a in areas[1:] if cell.get((a, d)) is not None]
                if s is None or not oth:
                    print(f"      {d}  no control at this date")
                else:
                    k = sum(1 for x in oth if abs(x) >= abs(s))
                    print(f"      {d}  controls at least as big: {k}/{len(oth)}")
            print()
    print("An interest rate is a growth rate, so the object with its dimensions here is the")
    print("inflation differential; the object with the dimensions of a rate wedge's level is a")
    print("cumulative interest factor. The two comparisons disagree in this data, and both are")
    print("printed rather than one being chosen after the fact.")


def read_seasonal():
    """The same-month step for every year, so the cycle is an object rather than an assumption."""
    for label, (shape, log) in OBJECTS.items():
        if not (have(CARRIER, shape) and have(OTHER_LEG, shape)):
            continue
        w = wedge(CARRIER, shape, log)
        print(f"=== {label}, carrier only. The step centred on each date's calendar month,")
        print("    year by year, and the calendar-year low and high of the wedge itself.")
        for d in ("2014-05", "2015-04"):
            mm = d[5:7]
            print(f"  month {mm}:")
            vals = []
            for y in range(2004, 2021):
                s = step_at(w, f"{y}-{mm}", 3)
                if s is None:
                    continue
                yr = [v for t, v in w.items() if t.startswith(str(y))]
                vals.append((y, s, min(yr), max(yr)))
            for y, s, lo, hi in vals:
                mark = "   <- the date" if f"{y}-{mm}" == d else ""
                print(f"    {y}  step {s:+7.3f}   year low {lo:+7.3f}  high {hi:+7.3f}{mark}")
            here = [s for y, s, _l, _h in vals if f"{y}-{mm}" == d]
            others = sorted((abs(s) for y, s, _l, _h in vals if f"{y}-{mm}" != d), reverse=True)
            if here and others:
                print(f"    the date is {abs(here[0]):.3f}, the largest other year is "
                      f"{others[0]:.3f}, a margin of {abs(here[0]) / others[0] - 1:+.0%}")
        print()


def square(area, shape1, shape2, log):
    w1, w2 = wedge(area, shape1, log), wedge(area, shape2, log)
    return {t: w1[t] - w2[t] for t in sorted(set(w1) & set(w2))}


def read_squares():
    print("Square = one good's wedge minus another's. A scalar carried by each position")
    print("predicts every one of these is zero, and a shift common to everything sold in the")
    print("carrier cancels out of it. Two nulls per cell: 'p' pools every month, 's' takes the")
    print("same calendar month in other years.\n")
    for label, (s1, s2, log) in SQUARES.items():
        areas = [a for a in [CARRIER] + list(CONTROLS) if have(a, s1) and have(a, s2)]
        if not (have(OTHER_LEG, s1) and have(OTHER_LEG, s2)) or CARRIER not in areas:
            print(f"=== {label}: not on disk\n")
            continue
        print(f"=== {label}")
        for win in WINDOWS:
            print(f"  window {win} month(s) either side")
            print("    area  " + "".join(f"{d:>28s}" for d in EDGE_DATES))
            cell = {}
            for a in areas:
                sq = square(a, s1, s2, log)
                pn = pooled_null(sq, win)
                row = []
                for d in EDGE_DATES:
                    v = step_at(sq, d, win)
                    cell[(a, d)] = v
                    if v is None:
                        row.append("(window does not fit)")
                        continue
                    sn = same_month_null(sq, d, win)
                    kp = sum(1 for x in pn if abs(x) >= abs(v))
                    ks = sum(1 for x in sn if abs(x) >= abs(v))
                    row.append(f"{v:+6.2f} p{kp:3d}/{len(pn):3d} s{ks:2d}/{len(sn):2d}")
                print(f"    {a:4s}  " + "".join(f"{c:>28s}" for c in row))
            for d in EDGE_DATES:
                v = cell.get((CARRIER, d))
                oth = [cell[(a, d)] for a in areas[1:] if cell.get((a, d)) is not None]
                if v is None or not oth:
                    print(f"      {d}  no control at this date")
                else:
                    k = sum(1 for x in oth if abs(x) >= abs(v))
                    print(f"      {d}  controls at least as big: {k}/{len(oth)}")
            print()
        sq = square(CARRIER, s1, s2, log)
        vals = [abs(v) for v in sq.values()]
        print(f"  the carrier's square runs {min(sq.values()):+.2f} to {max(sq.values()):+.2f} "
              f"over {len(sq)} months, median magnitude {sorted(vals)[len(vals) // 2]:.2f}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", action="store_true")
    ap.add_argument("--seasonal", action="store_true")
    ap.add_argument("--squares", action="store_true")
    a = ap.parse_args()
    if a.steps:
        read_steps()
    elif a.seasonal:
        read_seasonal()
    elif a.squares:
        read_squares()
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
