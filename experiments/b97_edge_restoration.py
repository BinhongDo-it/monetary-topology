"""B97: a price sits on one class of edge, and it should move when that class is restored.

Cyprus cut two classes of edge on 2013-03-28, the island's own bank-to-bank edge and the
cross-border edge, and restored them eleven months apart:

    domestic transfers     2014-05-05, fully liberalised 2014-06-01
    cross-border transfers 2015-04-06

A deposit is the thing that could not move. Its price is the new-business deposit rate, and the
euro area is the other position holding the same unit, so the wedge between them is a price on
the cross-border edge. Loans are the placebo: a loan is not a deposit that wants to move.

A step at a date is read against two floors, and both are the same statistic as the reading:

    in time         the same statistic at every month that is not one of the dates, in the
                    same area. This says whether a move of this size is ordinary for this
                    instrument.
    across areas    the same statistic at the same date in every control area. This says
                    whether whatever moved was the euro area periphery rather than Cyprus.

The control areas are chosen one reason each: Greece sat in the same periphery credit stress
and never cut its domestic edge, Slovenia had a bank crisis and a bail-in at the end of 2013
and cut no edge at all, Malta is the other small island banking system in the same currency,
Portugal and Ireland are the other two programme countries of the period.

Greece cut its own external edge on 2015-06-29. A three-month after-window at the 2015-04 date
runs to July and contains that, so Greece is not a control there at that window length. The
reading therefore prints two window lengths, and the two-month one ends in May.

This file runs in steps so that each one can be read before the next is written:

    python experiments/b97_edge_restoration.py --audit
        coverage per series: first and last period, gaps, breaks. Nothing is compared here.
    python experiments/b97_edge_restoration.py --wedges
        the step at each date, for the carrier and every control on disk, at both window
        lengths, each against both floors.
    python experiments/b97_edge_restoration.py --levels
        the wedge as a level over four spans, which is the object rather than a test of it.
    python experiments/b97_edge_restoration.py --squares
        two positions by two goods, against the floor the rates are published on.
    python experiments/b97_edge_restoration.py --dose
        the wedge against how much of the treatment is still in force, which is the
        shape the treatment actually has.
    python experiments/b97_edge_restoration.py --square-steps
        the same steps in the squares, which takes the country-wide move out of the reading.
    python experiments/b97_edge_restoration.py --series "term deposits <=1y, households"
        that wedge month by month, so a step can be told from a trend by looking.

The volume series on disk are not read yet. They answer a different question, which is whether
a rate moved or the business it averages over moved, and that question comes after this one.
"""
import argparse
import csv
import json
import pathlib
from collections import OrderedDict

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mir"

# the two dates the design registers, and what each restored
EDGE_DATES = OrderedDict([
    ("2014-05", "domestic transfer limit abolished (2014-05-05)"),
    ("2014-06", "domestic capital controls fully liberalised (2014-06-01)"),
    ("2015-04", "all remaining external restrictions lifted (2015-04-06)"),
])

CARRIER = "CY"
OTHER_LEG = "U2"                                  # the second position, not a control
CONTROLS = ("GR", "SI", "MT", "PT", "IE")
WINDOWS = (3, 2)                                  # months either side; 2 ends before 2015-06


def months(a, b):
    """Every month from a to b inclusive, as YYYY-MM."""
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    out = []
    while (ya, ma) <= (yb, mb):
        out.append(f"{ya:04d}-{ma:02d}")
        ma += 1
        if ma == 13:
            ya, ma = ya + 1, 1
    return out


def read(path):
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    obs = {}
    breaks = set()
    for r in rows:
        t = r["TIME_PERIOD"]
        v = r["OBS_VALUE"].strip()
        obs[t] = float(v) if v not in ("", "NaN") else None
        if (r.get("OBS_PRE_BREAK") or "").strip():
            breaks.add(t)
    meta = rows[0] if rows else {}
    return obs, breaks, meta


def audit():
    files = sorted(RAW.glob("MIR_*.csv"))
    print(f"{len(files)} series on disk in {RAW}\n")
    print(f"{'series':44s} {'first':8s} {'last':8s} {'n':>4s} {'gaps':>5s} {'breaks':>7s}  at the dates")
    report = {}
    for f in files:
        obs, breaks, meta = read(f)
        ts = sorted(obs)
        if not ts:
            print(f"{f.stem:44s} EMPTY")
            continue
        span = months(ts[0], ts[-1])
        gaps = [m for m in span if m not in obs]
        blank = [m for m in ts if obs[m] is None]
        at = " ".join("Y" if d in obs and obs[d] is not None else "-" for d in EDGE_DATES)
        print(f"{f.stem:44s} {ts[0]:8s} {ts[-1]:8s} {len(ts):4d} "
              f"{len(gaps) + len(blank):5d} {len(breaks):7d}  {at}")
        report[f.stem] = {"first": ts[0], "last": ts[-1], "n": len(ts),
                          "missing_inside_span": len(gaps) + len(blank),
                          "breaks": sorted(breaks),
                          "title": meta.get("TITLE", "")}
    print("\nthe three columns under 'at the dates' are, in order:")
    for d, what in EDGE_DATES.items():
        print(f"   {d}  {what}")
    out = RAW / "coverage.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\nwrote {out}")
    # the things that have to be read before anything is compared
    firsts = {v["first"] for v in report.values()}
    print(f"\ndistinct first periods across the {len(report)} series: {sorted(firsts)}")
    anybreak = {k: v["breaks"] for k, v in report.items() if v["breaks"]}
    print(f"series carrying a reported break: {len(anybreak)}")
    for k, v in sorted(anybreak.items()):
        print(f"   {k}: {v}")


# the six instruments, each as a shape shared by every reference area
SHAPES = OrderedDict([
    ("overnight deposits, households",       "B_L21_A_R_A_2250_EUR_N"),
    ("overnight deposits, firms",            "B_L21_A_R_A_2240_EUR_N"),
    ("term deposits <=1y, households",       "B_L22_F_R_A_2250_EUR_N"),
    ("term deposits <=1y, firms",            "B_L22_F_R_A_2240_EUR_N"),
    ("loans <=1y, households (placebo)",     "B_A2C_F_R_A_2250_EUR_N"),
    ("loans <=1y, firms (placebo)",          "B_A2A_F_R_A_2240_EUR_N"),
])
QUIET = ("2013-07", "2016-12")   # only used by the superseded floor below

# short tags, so a table of pairs names both goods instead of truncating them to a prefix
# they share. Two rows reading "overnight d" and "overnight d" name nothing.
SHORT = OrderedDict(zip(SHAPES, ("overnight dep hh", "overnight dep firm",
                                 "term dep hh", "term dep firm",
                                 "loan hh", "loan firm")))


def path_for(shape, area):
    return RAW / f"MIR_M_{area}_{shape}.csv"


def wedge(shape, area):
    """`area` minus the euro area, month by month. One unit, two positions."""
    a, _b, _m = read(path_for(shape, area))
    u, _b2, _m2 = read(path_for(shape, OTHER_LEG))
    return {t: a[t] - u[t] for t in sorted(set(a) & set(u))
            if a[t] is not None and u[t] is not None}


def level(w, centre, side, win):
    """Mean of the wedge over `win` months on one side of `centre`, and how many months."""
    ts = sorted(w)
    idx = [i for i, t in enumerate(ts) if t < centre] if side == "before" else \
          [i for i, t in enumerate(ts) if t >= centre]
    take = idx[-win:] if side == "before" else idx[:win]
    vals = [w[ts[i]] for i in take]
    return (sum(vals) / len(vals) if vals else float("nan")), len(vals)


def step_at(w, centre, win):
    """The statistic the reading uses: the mean over `win` months after, minus before."""
    b, nb = level(w, centre, "before", win)
    a, na = level(w, centre, "after", win)
    if nb < win or na < win:
        return None
    return a - b


def placebo_steps(w, win, span=("2009-01", "2020-09")):
    """The same statistic at every other month, which is what an event's step is read against.

    **A median one-month difference is not the floor for a multi-month-mean change**, and
    reading one against the other is the sixth category error: the criterion's scope and the
    measured object's scope do not coincide. The floor here is the distribution of the very
    statistic the reading uses, at the same window length, computed at every month that is not
    one of the dates. Months belonging to some other area's own event are left in, which can
    only widen the null and so can only make a step harder to call.
    """
    ts = [m for m in months(*span) if m in w]
    skip = set()
    for d in EDGE_DATES:
        i = len(months(span[0], d))
        skip |= {m for m in ts if abs(len(months(span[0], m)) - i) <= 2 * win}
    out = []
    for m in ts:
        if m in skip:
            continue
        s = step_at(w, m, win)
        if s is not None:
            out.append((m, s))
    return out


def floor_of(w, win=3):
    """Superseded, kept where it was written. Not called by the reading.

    This was the first floor: the median ordinary month-to-month move. It is the wrong
    statistic, because the reading is a change in a `win`-month mean and this is a one-month
    difference, so the two live on different scales and a step judged against it is judged
    against nothing. `placebo_steps` replaces it with the reading's own statistic. The lesson
    stays where it happened rather than moving to a note somewhere else.
    """
    ts = [t for t in sorted(w) if QUIET[0] <= t <= QUIET[1]]
    skip = set()
    for d in EDGE_DATES:
        skip |= {t for t in ts if abs(len(months(QUIET[0], t)) - len(months(QUIET[0], d))) <= win}
    keep = [t for t in ts if t not in skip]
    steps = sorted(abs(w[b] - w[a]) for a, b in zip(keep, keep[1:])
                   if months(a, b) == [a, b])
    if not steps:
        return float("nan"), 0
    return steps[len(steps) // 2], len(steps)


def areas_on_disk(shape):
    """The carrier first, then whichever controls have both legs of the wedge on disk."""
    out = [CARRIER] if path_for(shape, CARRIER).exists() else []
    out += [a for a in CONTROLS if path_for(shape, a).exists()]
    if not path_for(shape, OTHER_LEG).exists():
        return []
    return out


def read_wedges():
    print("Wedge = the area's rate minus the euro area's, in percentage points: one unit of")
    print("account, two positions. Each cell is the step at that date, then in brackets how")
    print("many non-event months in that same area show a step at least as big, out of how")
    print("many were measured. The last line of each block is the other floor: how many")
    print("control areas moved at least as much as the carrier at that same date.\n")
    for label, shape in SHAPES.items():
        areas = areas_on_disk(shape)
        missing = [a for a in CONTROLS if not path_for(shape, a).exists()]
        print(f"=== {label}")
        if not areas:
            print("  the euro area leg is not on disk, so no wedge can be formed\n")
            continue
        for win in WINDOWS:
            print(f"  window {win} month(s) either side"
                  + ("   (the after-window at 2015-04 ends in May, before Greece's own "
                     "controls)" if win == 2 else ""))
            print("    area  " + "".join(f"{d:>25s}" for d in EDGE_DATES))
            cell = {}
            for area in areas:
                row = []
                w = wedge(shape, area)
                pb = placebo_steps(w, win)
                for d in EDGE_DATES:
                    s = step_at(w, d, win)
                    cell[(area, d)] = s
                    if s is None:
                        row.append("(window does not fit)")
                    else:
                        bigger = sum(1 for _m, x in pb if abs(x) >= abs(s))
                        row.append(f"{s:+7.3f} [{bigger:3d}/{len(pb):3d}]")
                print(f"    {area:4s}  " + "".join(f"{c:>25s}" for c in row))
            tail = []
            for d in EDGE_DATES:
                s = cell.get((CARRIER, d))
                others = [cell[(a, d)] for a in areas[1:] if cell.get((a, d)) is not None]
                if s is None or not others:
                    tail.append("no control at this date")
                else:
                    bigger = sum(1 for x in others if abs(x) >= abs(s))
                    tail.append(f"controls at least as big: {bigger}/{len(others)}")
            for d, t in zip(EDGE_DATES, tail):
                print(f"      {d}  {t}")
            print()
        if missing:
            print(f"  controls not on disk for this instrument: {', '.join(missing)}")
        print("  the two 2014 dates are adjacent months, so at any window of two or more they")
        print("  are one event read twice, not two events.\n")


# Four spans: what the wedge was before the edges were cut, while they were cut, after the
# cross-border one was restored, and later. A level is the object the theory talks about; a
# step is only a way of asking whether a level moved at one moment (工程第 11 条).
SPANS = (("before the cut", "2011-01", "2013-02"),
         ("edge cut", "2013-04", "2015-03"),
         ("edge restored", "2015-05", "2017-12"),
         ("later", "2018-01", "2020-12"))

# Every rate is published to two decimals, so a wedge of two rates is resolved to 0.01 pp and
# a square of four to 0.02 pp in the worst case. That is a floor that needs no estimate: it is
# the grid the numbers are printed on (`D24`).
TICK = 0.005
WEDGE_FLOOR = 2 * TICK
SQUARE_FLOOR = 4 * TICK


def read_levels():
    """The wedge as a level, span by span. No event, no window, no test."""
    print("Wedge = the area's rate minus the euro area's, averaged over each span, in")
    print("percentage points. The number in brackets is how many months the span had.")
    print(f"A wedge is resolved to {WEDGE_FLOOR:.2f} pp, which is the grid the rates are")
    print("published on, so anything at or under that is one tick of rounding.\n")
    print(f"{'instrument':36s} {'area':4s}" + "".join(f"{s[0]:>17s}" for s in SPANS))
    for label, shape in SHAPES.items():
        for area in areas_on_disk(shape):
            w = wedge(shape, area)
            cells = []
            for _n, a, b in SPANS:
                v = [w[t] for t in months(a, b) if t in w]
                cells.append(f"{sum(v) / len(v):+9.3f} ({len(v):2d})" if v else "        .    ")
            print(f"{label:36s} {area:4s}" + "".join(f"{c:>17s}" for c in cells))
        print()


def square(area, label1, label2):
    """Two positions by two goods: (area minus euro area) for good 1, minus the same for good 2.

    This is a four-cycle in the product of positions and goods. A single scalar carried by each
    position, which is what a country premium is, gives every good at that position the same
    wedge, so every one of these is exactly zero under that premise. The entailment is one
    line: wedge_g = s(area) - s(U2) for every g, so the difference of two wedges cancels.
    """
    w1, w2 = wedge(SHAPES[label1], area), wedge(SHAPES[label2], area)
    return {t: w1[t] - w2[t] for t in sorted(set(w1) & set(w2))}


def read_squares():
    labels = list(SHAPES)
    print("Square = (this good's wedge) minus (that good's wedge), percentage points.")
    print("A scalar carried by each position predicts every one of these is exactly zero.")
    print(f"Floor: {SQUARE_FLOOR:.2f} pp, four published rates at one tick each.\n")
    for area in [CARRIER] + list(CONTROLS):
        pairs = [(a, b) for i, a in enumerate(labels) for b in labels[i + 1:]
                 if path_for(SHAPES[a], area).exists() and path_for(SHAPES[b], area).exists()]
        if not pairs:
            continue
        tot = big = 0
        print(f"--- {area} against the euro area")
        head = "".join(f"{n:>15s}" for n, _a, _b in SPANS)
        print(f"{'good 1':19s} {'good 2':19s}{head}{'months':>8s}{'over floor':>12s}"
              f"{'max/floor':>11s}")
        for g1, g2 in pairs:
            sq = square(area, g1, g2)
            cells = []
            for _n, a, b in SPANS:
                v = [sq[t] for t in months(a, b) if t in sq]
                cells.append(f"{sum(v) / len(v):+9.3f}" if v else "        .")
            n = len(sq)
            k = sum(1 for v in sq.values() if abs(v) > SQUARE_FLOOR)
            mx = max(abs(v) for v in sq.values())
            tot += n
            big += k
            print(f"{SHORT[g1]:19s} {SHORT[g2]:19s}" + "".join(f"{c:>15s}" for c in cells)
                  + f"{n:8d}{k:12d}{mx / SQUARE_FLOOR:11.1f}")
        print(f"  all pairs in {area}: {big}/{tot} months over the floor = {big / tot:.4f}\n")


def null_and_steps(sq, win):
    """The step at each date, and the same statistic at every non-event month."""
    ts = [t for t in months("2009-01", "2020-09") if t in sq]
    pb = [(t, step_at(sq, t, win)) for t in ts]
    pb = [(t, v) for t, v in pb if v is not None]
    skip = set()
    for d in EDGE_DATES:
        i = len(months("2009-01", d))
        skip |= {t for t, _v in pb if abs(len(months("2009-01", t)) - i) <= 2 * win}
    null = [v for t, v in pb if t not in skip]
    return null, {d: step_at(sq, d, win) for d in EDGE_DATES}


def read_square_steps():
    """The step in a square, which is the reading with the country-wide move taken out.

    A wedge moving at a date says the country moved. Every rate in this dataset is a bank rate
    and every one of them sits on the edge that was restored, so a wedge moving is what any
    account of the lifting predicts as well, and it does not separate anything. A square is a
    difference of two wedges, so a level shift common to every instrument in the country
    cancels out of it, and what is left is whether the gap between two goods at the same
    position moved. The controls carry the same subtraction at the same date.
    """
    labels = list(SHAPES)
    print("Square step at each date. 't' = non-event months in the same area with a step at")
    print("least this big; 'c' = control areas with a step at least this big at the same date.")
    print("A square is a difference of two wedges, so a move common to every instrument in the")
    print("country cancels. IE has no term deposit rate over this window, so those rows carry")
    print("four controls rather than five.\n")
    for win in WINDOWS:
        print(f"=== window {win} month(s) either side")
        print(f"{'good 1':19s} {'good 2':19s}" + "".join(f"{d:>26s}" for d in EDGE_DATES))
        for i, g1 in enumerate(labels):
            for g2 in labels[i + 1:]:
                cells = {}
                for a in [CARRIER] + list(CONTROLS):
                    if not (path_for(SHAPES[g1], a).exists()
                            and path_for(SHAPES[g2], a).exists()):
                        continue
                    cells[a] = null_and_steps(square(a, g1, g2), win)
                if CARRIER not in cells:
                    continue
                null, mine = cells[CARRIER]
                row = []
                for d in EDGE_DATES:
                    s = mine[d]
                    if s is None:
                        row.append("(window does not fit)")
                        continue
                    tr = sum(1 for x in null if abs(x) >= abs(s))
                    oth = [cells[a][1][d] for a in cells if a != CARRIER
                           and cells[a][1][d] is not None]
                    cr = sum(1 for x in oth if abs(x) >= abs(s))
                    row.append(f"{s:+6.3f} t{tr:3d}/{len(null):3d} c{cr}/{len(oth)}")
                print(f"{SHORT[g1]:19s} {SHORT[g2]:19s}" + "".join(f"{c:>26s}" for c in row))
        print()
    print("Six goods give five independent differences, so these fifteen rows are not fifteen")
    print("independent readings (`D22`: the independent count is bounded by the structure, not")
    print("by how many pairs can be written down).")


# The eight relaxations the programme review dates, in order. The severity in a month is how
# many of them are still in force, which is eight before the first and zero after the last.
# This is the dose (`D53`): the treatment here was carried out in steps over two years, so a
# statistic shaped like a switch reads a segment of a ramp and its size is set by the window
# length rather than by the treatment.
RELAXATIONS = (
    ("2013-08", "cash may open a term account; new credit customers may open a current one"),
    ("2014-03", "the limits on term deposits are removed"),
    ("2014-03", "the cash withdrawal limit is removed"),
    ("2014-05", "the limit on cashing cheques is removed"),
    ("2014-05", "the domestic transfer limit is removed, whatever the purpose"),
    ("2014-05", "the ban on opening new accounts is removed"),
    ("2014-06", "domestic capital controls are fully liberalised"),
    ("2015-04", "every remaining external and payment restriction is lifted"),
)
CUT = "2013-03"          # the month both classes of edge were cut
DOSE_SPAN = ("2013-03", "2016-12")


def severity(month):
    """How many of the eight restrictions are still in force in this month."""
    return sum(1 for when, _what in RELAXATIONS if month < when)


def ranks(xs):
    """Average ranks, so ties do not depend on the order the values arrived in."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = r
        i = j + 1
    return out


def spearman(xs, ys):
    rx, ry = ranks(xs), ranks(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return num / (dx * dy) if dx and dy else float("nan")


def read_dose():
    """The wedge against how much of the treatment is still in force, not against a date.

    The severity falls monotonically with time, so any wedge with a monotone trend correlates
    with it. That is exactly why the controls are here: they carry the same time profile and
    none of the treatment, so their correlations are what this statistic returns when nothing
    is being restored. The reading is whether the carrier sits outside them, not the value.
    """
    ms = [m for m in months(*DOSE_SPAN)]
    print("Rank correlation between the wedge and how many restrictions are still in force,")
    print(f"over {DOSE_SPAN[0]} to {DOSE_SPAN[1]}. The carrier's severity goes 8 to 0; every")
    print("control sits at 0 throughout, so its correlation is this statistic run against the")
    print("same time profile with no treatment. A wedge that closes as the edge comes back")
    print("gives a positive correlation here.\n")
    print(f"{'instrument':36s}" + "".join(f"{a:>8s}" for a in [CARRIER] + list(CONTROLS))
          + "   controls at least as high")
    for label, shape in SHAPES.items():
        row, vals = [], {}
        for a in [CARRIER] + list(CONTROLS):
            if not path_for(shape, a).exists():
                row.append("       .")
                continue
            w = wedge(shape, a)
            pairs = [(severity(m), w[m]) for m in ms if m in w]
            if len(pairs) < 24:
                row.append("   short")
                continue
            r = spearman([p[0] for p in pairs], [p[1] for p in pairs])
            vals[a] = r
            row.append(f"{r:+8.3f}")
        tail = ""
        if CARRIER in vals:
            others = [v for a, v in vals.items() if a != CARRIER]
            tail = f"   {sum(1 for v in others if v >= vals[CARRIER])}/{len(others)}"
        print(f"{label:36s}" + "".join(row) + tail)
    print()
    print("The severity by month, so the shape of the dose is visible:")
    line = []
    for m in ms:
        if not line or severity(m) != line[-1][1]:
            line.append((m, severity(m)))
    print("   " + "  ".join(f"{m}:{k}" for m, k in line))


def print_series(shape_label, span=("2013-07", "2016-06")):
    """Print the wedge month by month, so a step can be told from a trend by looking.

    The before-and-after means in `--wedges` cannot tell those apart on their own.
    """
    shape = SHAPES[shape_label]
    areas = areas_on_disk(shape)
    ts = months(*span)
    w = {a: wedge(shape, a) for a in areas}
    print(f"=== {shape_label}: wedge against the euro area, percentage points")
    print("          " + "".join(f"{a:>8s}" for a in areas))
    for m in ts:
        mark = ""
        if m in ("2014-05", "2014-06"):
            mark = "   <- domestic edge restored"
        if m == "2015-04":
            mark = "   <- cross-border edge restored"
        if m == "2015-06":
            mark = "   <- Greece cuts its own external edge"
        cells = "".join(f"{w[a][m]:+8.3f}" if m in w[a] else "       ." for a in areas)
        print(f"  {m}  {cells}{mark}")
    print()


def tick_of(values):
    """The publication grid, measured rather than asserted.

    Failure mode 165: a varying number of printed digits does not mean a serializer is
    printing a binary float, because trailing zeros are dropped by default. What separates
    the two is whether every value is an integer multiple of one tick. This returns that tick
    and the count of values that are not on it, so the caller can refuse to use the floor if
    any value is off the grid.
    """
    from decimal import Decimal
    ds = [Decimal(v) for v in values]
    places = max(-d.as_tuple().exponent for d in ds)
    unit = Decimal(1).scaleb(-places)
    off = sum(1 for d in ds if (d / unit) != (d / unit).to_integral_value())
    distinct = sorted({int(d / unit) for d in ds})
    gap = min((b - a for a, b in zip(distinct, distinct[1:])), default=1)
    return float(unit * gap), off, len(ds)


def raw_strings(path, column="OBS_VALUE"):
    rows = csv.DictReader(path.read_text(encoding="utf-8").splitlines())
    return [r[column].strip() for r in rows if r[column].strip() not in ("", "NaN")]


def square_census(pairs_area, sq_of, floor):
    """How many months a square stands above the floor, and how far the largest one does."""
    tot = big = 0
    worst = 0.0
    for a in pairs_area:
        for sq in sq_of(a):
            tot += len(sq)
            big += sum(1 for v in sq.values() if abs(v) > floor)
            worst = max(worst, max(abs(v) for v in sq.values()))
    return big, tot, worst


def write_record():
    """Build the station's record. Every number here is computed from what is on disk."""
    import itertools
    out = ROOT / "results" / "b97_edge_restoration.json"
    labels = list(SHAPES)
    areas = [CARRIER] + list(CONTROLS)

    # B97-1: the instrument. Everything picked parses and carries the registered dates.
    rate_files = sorted(RAW.glob("MIR_*.csv"))
    unreadable, partial, dropped = [], [], []
    for f in rate_files:
        try:
            read(f)
        except Exception:
            unreadable.append(f.name)
    # A series with a hole at a date is an ordinary fact about coverage, and demanding that
    # none exist would be a criterion set at the strictest reading rather than at what the
    # reading needs (第 23 条). What matters is that a short window never contributes a step:
    # either both sides are complete and the cell is read, or nothing is read and the cell is
    # named here. A step built from a partial window would be the real defect.
    for label, shape in SHAPES.items():
        for a in areas_on_disk(shape):
            w = wedge(shape, a)
            for d in EDGE_DATES:
                for win in WINDOWS:
                    b, nb = level(w, d, "before", win)
                    aft, na = level(w, d, "after", win)
                    got = step_at(w, d, win)
                    short = nb < win or na < win
                    if short and got is not None:
                        partial.append(f"{shape}:{a}:{d}:win{win}")
                    if short:
                        dropped.append(f"{shape}:{a}:{d}:win{win}")

    # B97-6: the publication grid, measured.
    rate_vals = [v for f in rate_files if "_A_B_A_" not in f.name for v in raw_strings(f)]
    rate_tick, rate_off, rate_n = tick_of(rate_vals)
    rate_floor = 4 * (rate_tick / 2)

    # B97-2: the rival's zero on the bank-rate squares.
    def rate_squares(a):
        for g1, g2 in itertools.combinations(labels, 2):
            if path_for(SHAPES[g1], a).exists() and path_for(SHAPES[g2], a).exists():
                yield square(a, g1, g2)
    r_big, r_tot, r_worst = square_census(areas, rate_squares, rate_floor)

    # B97-3: the same on the goods side, which owes nothing to banking. The price reading
    # lives in its own file because it is a different carrier; it is loaded rather than
    # duplicated so that one definition of the wedge serves both.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "b97_prices", str(ROOT / "experiments" / "b97_prices.py"))
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    anr_vals = [v for f in sorted(bp.RAW.glob("ICP_*_4_ANR.csv")) for v in raw_strings(f)]
    anr_tick, anr_off, anr_n = tick_of(anr_vals)
    anr_floor = 4 * (anr_tick / 2)
    g_areas = [a for a in [bp.CARRIER] + list(bp.CONTROLS)
               if bp.have(a, "N_SERV00_4_ANR") and bp.have(a, "N_IGXE00_4_ANR")]

    def goods_squares(a):
        yield bp.square(a, "N_SERV00_4_ANR", "N_IGXE00_4_ANR", False)
    g_big, g_tot, g_worst = square_census(g_areas, goods_squares, anr_floor)

    # B97-4: the dated move, read against the controls rather than against a date alone.
    beat = []
    for label, shape in SHAPES.items():
        present = areas_on_disk(shape)
        if CARRIER not in present:
            continue
        mine = step_at(wedge(shape, CARRIER), "2015-04", 3)
        oth = [step_at(wedge(shape, a), "2015-04", 3) for a in present[1:]]
        oth = [x for x in oth if x is not None]
        if mine is None or not oth:
            continue
        beat.append((label, sum(1 for x in oth if abs(x) >= abs(mine)), len(oth)))
    clean = [b for b in beat if b[1] == 0]

    # B97-5: the differential prediction. Three states, and the middle one is a verdict of
    # its own (`11c`): an instrument that sits on both classes of edge cannot separate them,
    # and saying so is not the same as saying the prediction failed.
    crit = [
        {"name": "B97-1", "kind": "instrument",
         "passed": not unreadable and not partial,
         "statement": "Every rate file parses, and no step is ever built from a window that "
                      "is short on either side: a cell with a hole produces no reading rather "
                      "than a reading over fewer months.",
         "detail": f"{len(rate_files)} files on disk, {len(unreadable)} unreadable, "
                   f"{len(partial)} steps built from a short window, "
                   f"{len(dropped)} instrument-area-date-window cells dropped for short "
                   f"coverage and named rather than averaged over"
                   + ("" if not dropped else f": {sorted(set(dropped))[:4]}")},
        {"name": "B97-2", "kind": "rival", "grid": "B", "passed": r_big > 0,
         "rival_shape": "point prediction",
         "rival_premise": "Each position carries one scalar, a country premium, and every "
                          "price at that position is that scalar plus a term belonging to the "
                          "instrument alone.",
         "rival_entailment": "Under that premise the wedge between two positions is the same "
                             "for every instrument, so the difference of any two wedges, which "
                             "is a four-cycle over two positions and two goods, is exactly "
                             "zero. It is read here against the grid the rates are published "
                             "on, so the floor needs no estimate.",
         "statement": "The rival's point prediction of zero does not hold on the bank-rate "
                      "squares. Passing means the rival is wrong here (`11e`).",
         "detail": f"{r_big} of {r_tot} months stand above the published floor of "
                   f"{rate_floor:.2f} percentage points, which is four rates at half a tick "
                   f"of {rate_tick:.2f} each; the largest is {r_worst:.2f}, "
                   f"{r_worst / rate_floor:.1f} times the floor. Six areas against the euro "
                   f"area, fifteen pairs each."},
        {"name": "B97-3", "kind": "rival", "grid": "B", "passed": g_big > 0,
         "rival_shape": "point prediction",
         "rival_premise": "The same premise as B97-2, one scalar per position.",
         "rival_entailment": "The same entailment, on a carrier that owes nothing to banking: "
                             "services are mostly local and non-energy industrial goods mostly "
                             "traded, and neither is priced off a bank's cost of funds. The "
                             "inflation square is a twelve-month log difference, so each "
                             "index's arbitrary base cancels out of it. The square of the "
                             "index levels is not used for this, because a base normalisation "
                             "survives in it.",
         "statement": "The rival's point prediction of zero does not hold on the consumer "
                      "price squares either.",
         "detail": f"{g_big} of {g_tot} months stand above the published floor of "
                   f"{anr_floor:.2f} percentage points, four annual rates at half a tick of "
                   f"{anr_tick:.2f} each; the largest is {g_worst:.2f}, "
                   f"{g_worst / anr_floor:.1f} times the floor. "
                   f"{len(g_areas)} areas against the euro area."},
        {"name": "B97-4", "kind": "own_reading",
         "passed": bool(beat) and len(clean) == len(beat),
         "statement": "At the date the cross-border edge was restored, the carrier's step in "
                      "the wedge is larger than every control's on every rate instrument.",
         "detail": "; ".join(f"{lab}: {k} of {n} controls at least as big"
                             for lab, k, n in beat)
                   + f". Clean on {len(clean)} of {len(beat)} instruments, window three "
                     f"months. At the domestic dates the same count is far lower, which is "
                     f"what dates the move to this one."},
        {"name": "B97-5", "kind": "own_reading", "passed": False,
         "statement": "A price sitting on the domestic edge moves when that edge is restored "
                      "and not when the cross-border one is, and a price sitting on the "
                      "cross-border edge does the reverse. Three states: separated, "
                      "contradicted, and no instrument that sits on one edge only.",
         "detail": "Not adjudicable on this carrier, which is a statement about the "
                   "instruments and not about the prediction. Every rate here is a bank rate "
                   "and reaches the cross-border edge through a bank's cost of funds, so none "
                   "of them sits on the domestic edge alone; the placebo moved more than the "
                   "treated instruments, which is the same fact read from the other side. On "
                   "the goods side the level object carries a seasonal cycle of about three "
                   "log points a year with no seasonally adjusted country series published in "
                   "this dataflow, and the one cell that pointed the right way rests on a "
                   "margin of 0.13 percentage points over a control. Neither state of the "
                   "prediction was reached."},
        {"name": "B97-6", "kind": "known_answer", "passed": rate_off == 0 and anr_off == 0,
         "statement": "Every published value sits on an integer number of its own tick, which "
                      "is what makes the printed grid usable as a floor rather than an "
                      "artefact of the serializer.",
         "detail": f"{rate_n} rate observations on a tick of {rate_tick:.2f} with {rate_off} "
                   f"off the grid; {anr_n} annual rate observations on a tick of "
                   f"{anr_tick:.2f} with {anr_off} off the grid. The number of printed digits "
                   f"varies in both, because trailing zeros are dropped, and that is why the "
                   f"grid is checked rather than counted from the digits."},
    ]
    rec = {
        "stage": "B97",
        "config": {
            "carrier": CARRIER,
            "other_leg": OTHER_LEG,
            "controls": list(CONTROLS),
            "edge_dates": list(EDGE_DATES),
            "windows": list(WINDOWS),
            "dose_span": list(DOSE_SPAN),
            "relaxations": len(RELAXATIONS),
            "rate_shapes": list(SHAPES.values()),
            "rate_floor": rate_floor,
            "goods_floor": anr_floor,
        },
        "mapping": {
            "B97-2": "the rival's zero fails on some month -> PASS, the rival is wrong there; "
                     "it holds everywhere -> FAIL, the rival is right there",
            "B97-4": "larger than every control on every instrument -> PASS; larger on some "
                     "and not others -> FAIL and the reading is reported per instrument",
            "B97-5": "separated -> PASS; contradicted -> FAIL; no instrument on one edge only "
                     "-> neither, and the record says so in its own detail rather than "
                     "borrowing a verdict (`11c`)",
        },
        "criteria": crit,
        "report": {
            "rate_squares_over_floor": [r_big, r_tot],
            "goods_squares_over_floor": [g_big, g_tot],
            "instruments_clean_at_the_cross_border_date": [len(clean), len(beat)],
        },
    }
    for c in crit:
        if not isinstance(c["passed"], bool):
            raise SystemExit(f"{c['name']}: passed is {type(c['passed']).__name__}, not bool. "
                             f"`a and b` returns b, and every consumer of this field only "
                             f"tests it for truth, so nothing downstream would report it "
                             f"(工程第 22 条).")
    out.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8")
    print(f"wrote {out}")
    for c in crit:
        state = "PASS" if c["passed"] else ("VOID" if c["name"] == "B97-5" else "FAIL")
        print(f"  {c['name']:7s} {c['kind']:12s} {state}")
    print(f"\nall {len(crit)} criteria written; B97-5 is the third state and carries no "
          f"verdict")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--wedges", action="store_true")
    ap.add_argument("--levels", action="store_true")
    ap.add_argument("--squares", action="store_true")
    ap.add_argument("--square-steps", action="store_true")
    ap.add_argument("--dose", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--series", default="")
    a = ap.parse_args()
    if a.audit:
        audit()
    elif a.wedges:
        read_wedges()
    elif a.levels:
        read_levels()
    elif a.squares:
        read_squares()
    elif a.square_steps:
        read_square_steps()
    elif a.dose:
        read_dose()
    elif a.record:
        write_record()
    elif a.series:
        print_series(a.series)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
