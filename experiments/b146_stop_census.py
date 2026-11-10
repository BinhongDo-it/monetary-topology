"""B146, step one: count what a filing stop is on the mandi panel before reading anything.

A market files a row on a day it trades and its committee uploads. A missing row is
therefore several different things, and the row count cannot tell them apart:

* the market traded and nothing was uploaded: the record stopped, the price did not;
* the market did not trade: there was no price to upload;
* the market could not move goods in or out;
* the market could not hear a price from anywhere else.

Only the last two are statements about the market's edges. The first is a statement
about the edge that carries the record to the reader, and the second is a statement
about the thing that edge carries. This script counts stops and prints them next to
the calendar, so that the later reading starts from named stops and dated documents
and not from the bare absence of rows.

Nothing here scores anything. A stop lives between two filings, so it is indexed by
the pair (last filing, next filing) and never by a single date.

Usage::

    python experiments/b146_stop_census.py
    python experiments/b146_stop_census.py --commodity "Lentil (Masur)" --series Manipur
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
COMMODITIES = ("Lentil (Masur)", "Cowpea (Lobia-Karamani)", "White Peas")

#: The grid the census is printed on. Every cell is printed; no cell is a criterion.
GAP_FLOORS = (8, 15, 31, 61, 91, 181)
PRIOR_FLOORS = (5, 10, 15, 20)
PRIOR_WINDOW_DAYS = 30

#: Stops whose last filings fall within this many days of each other, in one state or
#: one district, are printed as one cluster. Three markets is the smallest group in
#: which "several markets stopped together" means more than a pair.
CLUSTER_WINDOW_DAYS = 3
CLUSTER_MIN_MARKETS = 3

#: Closures whose dates are fixed by the calendar. A detector that cannot see these
#: cannot see anything, so they are read back first.
FIXED_HOLIDAYS = ((1, 26, "26 Jan"), (8, 15, "15 Aug"), (10, 2, "2 Oct"))
NEIGHBOUR_DAYS = 7

Stop = collections.namedtuple("Stop", "state district market last nxt gap prior")


def read_csv(commodity):
    """Rows as (state, district, market, variety, arrivals, modal, date), plus counters.

    A row with an unreadable date is dropped and counted, because without a date it
    is not a filing on any day. A row with an unreadable price or arrival is kept
    with ``None`` there: it is still evidence that the market filed that day.
    """
    rows = []
    seen = short = undated = 0
    files = sorted((DATA / commodity).glob("*.csv"))
    for f in files:
        with f.open(encoding="utf-8", errors="replace", newline="") as fh:
            for r in csv.reader(fh):
                seen += 1
                if len(r) < 10:
                    short += 1
                    continue
                try:
                    d = datetime.datetime.strptime(r[9].strip(), "%d %b %Y").date()
                except ValueError:
                    undated += 1
                    continue
                try:
                    modal = float(r[8])
                except ValueError:
                    modal = None
                try:
                    arrivals = float(r[5])
                except ValueError:
                    arrivals = None
                rows.append((r[0].strip(), r[1].strip(), r[2].strip(), r[3].strip(),
                             arrivals, modal, d))
    return rows, {"files": len(files), "lines": seen, "short": short, "undated": undated,
                  "kept": len(rows)}


def filing_days(rows):
    per = collections.defaultdict(set)
    for s, dis, m, _, _, _, d in rows:
        per[(s, dis, m)].add(d)
    return {k: sorted(v) for k, v in per.items()}


def stops(per, min_gap=GAP_FLOORS[0]):
    out = []
    for (s, dis, m), days in sorted(per.items()):
        have = {d.toordinal() for d in days}
        for a, b in zip(days, days[1:]):
            g = (b - a).days
            if g < min_gap:
                continue
            prior = sum(1 for k in range(PRIOR_WINDOW_DAYS) if (a.toordinal() - k) in have)
            out.append(Stop(s, dis, m, a, b, g, prior))
    return out


def unit_grid(st):
    grid = {}
    for g in GAP_FLOORS:
        for p in PRIOR_FLOORS:
            grid[(g, p)] = sum(1 for e in st if e.gap >= g and e.prior >= p)
    return grid


def clusters(st, per, level, gap_floor, prior_floor):
    """Stops that begin together. ``level`` is "state" or "district"."""
    key = (lambda e: (e.state,)) if level == "state" else (lambda e: (e.state, e.district))
    pkey = (lambda k: (k[0],)) if level == "state" else (lambda k: (k[0], k[1]))
    days_of = collections.defaultdict(list)
    for k, days in per.items():
        days_of[pkey(k)].append(set(days))
    groups = collections.defaultdict(list)
    for e in st:
        if e.gap >= gap_floor and e.prior >= prior_floor:
            groups[key(e)].append(e)
    out = []
    for where, lst in sorted(groups.items()):
        lst.sort(key=lambda e: (e.last, e.district, e.market))
        i = 0
        while i < len(lst):
            j = i
            while j + 1 < len(lst) and (lst[j + 1].last - lst[i].last).days <= CLUSTER_WINDOW_DAYS:
                j += 1
            grp = lst[i:j + 1]
            markets = sorted({(e.district, e.market) for e in grp})
            if len(markets) >= CLUSTER_MIN_MARKETS:
                first = grp[0].last
                window = {first - datetime.timedelta(k) for k in range(PRIOR_WINDOW_DAYS)}
                active = sum(1 for ds in days_of[where] if ds & window)
                out.append({"where": where, "first_last": first, "last_last": grp[-1].last,
                            "markets": len(markets), "active": active,
                            "median_gap": statistics.median(e.gap for e in grp),
                            "median_resume": datetime.date.fromordinal(int(statistics.median(
                                e.nxt.toordinal() for e in grp))),
                            "districts": len({e.district for e in grp}),
                            "members": sorted((e.district, e.market, e.last) for e in grp)})
            i = j + 1
    return out


def national_counts(per):
    nat = collections.Counter()
    for days in per.values():
        for d in days:
            nat[d] += 1
    return nat


def fixed_holiday_table(nat):
    first, last = min(nat), max(nat)
    table = []
    for mm, dd, name in FIXED_HOLIDAYS:
        for y in range(first.year, last.year + 1):
            d = datetime.date(y, mm, dd)
            if not (first + datetime.timedelta(NEIGHBOUR_DAYS) <= d
                    <= last - datetime.timedelta(NEIGHBOUR_DAYS)):
                continue
            nb = [nat[d + datetime.timedelta(k)] for k in range(-NEIGHBOUR_DAYS, NEIGHBOUR_DAYS + 1)
                  if k != 0]
            table.append((name, y, nat[d], statistics.median(nb)))
    return table


#: the four (level, stop floor, prior floor) settings the cluster tables are printed at
CLUSTER_SETTINGS = (("state", 8, 10), ("state", 15, 10), ("district", 8, 10), ("district", 15, 10))


def census_record(rows):
    """Everything ``print_census`` prints, as one sorted structure for the record:
    the (stop length, prior filings) grid, every cluster at the four settings, the
    days with no row anywhere, and the fixed-closure table year by year."""
    per = filing_days(rows)
    st = stops(per)
    grid = unit_grid(st)
    nat = national_counts(per)
    days = sorted({r[6] for r in rows})
    cal = [days[0] + datetime.timedelta(n) for n in range((days[-1] - days[0]).days + 1)]
    empty = [d for d in cal if nat[d] == 0]
    longest = run = 0
    for d in cal:
        run = run + 1 if nat[d] == 0 else 0
        longest = max(longest, run)
    out = {"stops_at_least_%d_days" % GAP_FLOORS[0]: len(st),
           "unit_grid": [{"stop_floor": g, "prior_floor": p, "units": grid[(g, p)]}
                         for g in GAP_FLOORS for p in PRIOR_FLOORS],
           "days_with_no_row": {"count": len(empty), "sundays": sum(d.weekday() == 6 for d in empty),
                                "longest_run": longest},
           "fixed_closures": [{"day": name, "year": y, "filing": n, "neighbour_median": float("%.1f" % med)}
                              for name, y, n, med in fixed_holiday_table(nat)],
           "clusters": {}}
    for level, gap_floor, prior_floor in CLUSTER_SETTINGS:
        cl = clusters(st, per, level, gap_floor, prior_floor)
        cl = sorted(cl, key=lambda c: (-c["markets"], c["first_last"], c["where"]))
        out["clusters"]["%s_stop%d_prior%d" % (level, gap_floor, prior_floor)] = [
            {"rank": i + 1, "where": " / ".join(c["where"]), "markets": c["markets"], "active": c["active"],
             "share": float("%.4f" % (c["markets"] / max(c["active"], 1))),
             "first_last_filing": c["first_last"].isoformat(), "last_last_filing": c["last_last"].isoformat(),
             "median_stop_days": float("%.1f" % c["median_gap"]),
             "median_resume": c["median_resume"].isoformat(), "districts": c["districts"],
             "members": [[dis, m, last.isoformat()] for dis, m, last in c["members"]]}
            for i, c in enumerate(cl)]
    return out


def print_census(commodity):
    rows, counts = read_csv(commodity)
    print("=" * 96)
    print(commodity, counts)
    if not rows:
        print("  no rows read: this is not a clean result, the directory is empty or missing")
        return
    per = filing_days(rows)
    days = sorted({r[6] for r in rows})
    by_state = collections.Counter(k[0] for k in per)
    n_days = [len(v) for v in per.values()]
    print("  span %s .. %s, %d days with a row out of %d calendar days"
          % (days[0], days[-1], len(days), (days[-1] - days[0]).days + 1))
    print("  markets %d, states %d: %s" % (len(per), len(by_state),
          ", ".join("%s %d" % kv for kv in sorted(by_state.items(), key=lambda kv: (-kv[1], kv[0])))))
    qs = statistics.quantiles(n_days, n=4) if len(n_days) > 1 else [n_days[0]] * 3
    print("  filing days per market: min %d, quartiles %.0f / %.0f / %.0f, max %d"
          % (min(n_days), qs[0], qs[1], qs[2], max(n_days)))

    all_gaps = [(b - a).days for v in per.values() for a, b in zip(v, v[1:])]
    print("  gaps between consecutive filings: n %d; share of one day %.3f, up to 3 %.3f, "
          "up to 7 %.3f, over 14 %.4f, over 30 %.4f, over 90 %.4f"
          % (len(all_gaps), *(sum(c(g) for g in all_gaps) / len(all_gaps) for c in (
              lambda g: g == 1, lambda g: g <= 3, lambda g: g <= 7,
              lambda g: g > 14, lambda g: g > 30, lambda g: g > 90))))

    st = stops(per)
    grid = unit_grid(st)
    print("  (market, stop) units; rows are the stop's length in days, columns the filings "
          "in the %d days up to the last filing" % PRIOR_WINDOW_DAYS)
    print("     stop >=  " + "".join("prior >= %-4d" % p for p in PRIOR_FLOORS))
    for g in GAP_FLOORS:
        print("     %6d   " % g + "".join("%-13d" % grid[(g, p)] for p in PRIOR_FLOORS))

    nat = national_counts(per)
    cal = [days[0] + datetime.timedelta(n) for n in range((days[-1] - days[0]).days + 1)]
    empty = [d for d in cal if nat[d] == 0]
    longest = run = 0
    for d in cal:
        run = run + 1 if nat[d] == 0 else 0
        longest = max(longest, run)
    print("  calendar days with no row anywhere: %d, of which Sundays %d; longest run %d days"
          % (len(empty), sum(d.weekday() == 6 for d in empty), longest))

    print("  fixed-date closures read back: markets filing on the day / median of the %d "
          "neighbouring days" % (2 * NEIGHBOUR_DAYS))
    table = fixed_holiday_table(nat)
    for name in [h[2] for h in FIXED_HOLIDAYS]:
        cells = ["%d: %d / %.1f" % (y, n, med) for nm, y, n, med in table if nm == name]
        print("     %-7s %s" % (name, "   ".join(cells)))
    if table:
        day_sum = sum(n for _, _, n, _ in table)
        nb_sum = sum(med for _, _, _, med in table)
        below = sum(1 for _, _, n, med in table if n < med)
        print("     pooled: %d on the days against %.1f on their neighbours, ratio %.3f; "
              "%d of %d cells below their neighbours"
              % (day_sum, nb_sum, day_sum / nb_sum if nb_sum else float("nan"), below, len(table)))

    for level in ("state", "district"):
        for gap_floor, prior_floor in ((8, 10), (15, 10)):
            cl = clusters(st, per, level, gap_floor, prior_floor)
            print("  clusters of stops, %s level, stop >= %d days, prior filings >= %d, "
                  "%d or more markets within %d days: %d"
                  % (level, gap_floor, prior_floor, CLUSTER_MIN_MARKETS, CLUSTER_WINDOW_DAYS, len(cl)))
            print("     markets active share  last filings          median stop  resume      where")
            for c in sorted(cl, key=lambda c: (-c["markets"], c["first_last"], c["where"]))[:25]:
                print("     %7d %6d %5.2f  %s..%s  %11.0f  %s  %s"
                      % (c["markets"], c["active"], c["markets"] / max(c["active"], 1),
                         c["first_last"], c["last_last"], c["median_gap"], c["median_resume"],
                         " / ".join(c["where"])))


def print_series(commodity, state):
    """One state's markets: weekly filing counts, price steps and each series' own grain."""
    rows, _ = read_csv(commodity)
    rows = [r for r in rows if r[0] == state]
    series = collections.defaultdict(dict)
    for s, dis, m, v, arr, modal, d in rows:
        if modal is not None and modal > 0:
            series[(dis, m, v)][d] = (modal, arr)
    print("=" * 96)
    print("%s, %s: %d rows, %d (district, market, variety) series" % (commodity, state, len(rows),
                                                                    len(series)))
    if not series:
        return
    keys = sorted(series)
    print("  series                                   filings steps  share_flat  smallest  median   longest_flat")
    for k in keys:
        days = sorted(series[k])
        moves = [math.log(series[k][b][0]) - math.log(series[k][a][0]) for a, b in zip(days, days[1:])]
        nz = [abs(x) for x in moves if x != 0]
        run = best = 1
        for x in moves:
            run = run + 1 if x == 0 else 1
            best = max(best, run)
        print("  %-40s %7d %5d  %10.3f  %8s  %7s  %d"
              % (" / ".join(k)[:40], len(days), len(nz),
                 1 - len(nz) / len(moves) if moves else float("nan"),
                 ("%.4f" % min(nz)) if nz else "-", ("%.4f" % statistics.median(nz)) if nz else "-",
                 best))
    first = min(min(v) for v in series.values())
    last = max(max(v) for v in series.values())
    monday = first - datetime.timedelta(first.weekday())
    print("  filings per week, one column per series in the order above")
    while monday <= last:
        week = [monday + datetime.timedelta(i) for i in range(7)]
        print("     %s  %s" % (monday, " ".join("%d" % sum(d in series[k] for d in week) for k in keys)))
        monday += datetime.timedelta(7)
    print("  price steps (date, from -> to), filings with a positive modal price")
    for k in keys:
        days = sorted(series[k])
        steps = ["%s %g->%g" % (b, series[k][a][0], series[k][b][0])
                 for a, b in zip(days, days[1:]) if series[k][a][0] != series[k][b][0]]
        print("     %s: %d" % (" / ".join(k), len(steps)))
        for i in range(0, len(steps), 6):
            print("        " + "; ".join(steps[i:i + 6]))
    print("  median arrivals per filing, by month")
    months = sorted({(d.year, d.month) for v in series.values() for d in v})
    for y, mth in months:
        cells = []
        for k in keys:
            a = [series[k][d][1] for d in series[k]
                 if d.year == y and d.month == mth and series[k][d][1] is not None]
            cells.append(("%7.2f" % statistics.median(a)) if a else "      .")
        print("     %d-%02d %s" % (y, mth, " ".join(cells)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--commodity", action="append",
                    help="repeatable; default is every commodity of the yearly csv landing")
    ap.add_argument("--series", help="also print this state's markets one by one")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.perf_counter()
    for commodity in a.commodity or COMMODITIES:
        print_census(commodity)
        if a.series:
            print_series(commodity, a.series)
    # elapsed time goes to stderr: it varies per run and must not land in anything diffed
    print("elapsed %.1f s" % (time.perf_counter() - t0), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
