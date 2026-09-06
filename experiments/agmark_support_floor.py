"""How does a support-set count behave on Agmarknet, and what is its floor?

Before spending anything on the eNAM treated commodities, measure the instrument
on commodities that are NOT treated, across the thickness gradient the design
will have to live on (D36). The station's outcome is

    support(commodity, month) = number of distinct markets with positive arrivals

so the questions that decide whether it is readable at all are:
  1. what is the level, and how thin does the worst month get (rule 13 step 1);
  2. what is the month-on-month noise in an untreated series -- that is the
     floor gate D24 has to clear;
  3. how do 1 and 2 scale from a thick commodity to a thin one, because every
     treated commodity in this carrier sits at the thin end.

No thresholds are drawn on anything. Objects are printed.

Source: github.com/iancovert/Agmarknet, a third-party scrape of the portal,
columns: State, District, Market, Commodity, Group, Arrivals(t), Min, Max, Modal, Date
"""
import csv
import math
import pathlib
import statistics
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
MONTHS = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def read(commodity):
    """-> {(y, m): {market: arrivals_total}}"""
    out = defaultdict(lambda: defaultdict(float))
    for f in sorted((DATA / commodity).glob("*.csv")):
        with f.open(encoding="utf-8", newline="") as fh:
            for row in csv.reader(fh):
                if len(row) < 10:
                    continue
                state, dist, market, comm, grp, arr = row[0], row[1], row[2], row[3], row[4], row[5]
                date = row[9].strip()
                try:
                    a = float(arr)
                except ValueError:
                    continue
                if a <= 0:
                    continue
                parts = date.split()
                if len(parts) != 3 or parts[1] not in MONTHS:
                    continue
                ym = (int(parts[2]), MONTHS[parts[1]])
                out[ym]["%s|%s|%s" % (state, dist, market)] += a
    return out


def series(panel):
    ks = sorted(panel)
    return [(k, len(panel[k]), sum(panel[k].values())) for k in ks]


def dlogs(vals):
    d = []
    for a, b in zip(vals, vals[1:]):
        if a > 0 and b > 0:
            d.append(abs(math.log(b / a)))
    return d


print("%-26s %6s %8s %8s %8s %8s %9s %9s" %
      ("commodity", "months", "sup med", "sup min", "sup max", "kt med",
       "|dlog sup|", "|dlog kt|"))
rows = []
for c in sorted(p.name for p in DATA.iterdir() if p.is_dir()):
    panel = read(c)
    s = series(panel)
    if len(s) < 6:
        continue
    sup = [x[1] for x in s]
    qty = [x[2] for x in s]
    dsup, dqty = dlogs(sup), dlogs(qty)
    rows.append((c, s, sup, qty, dsup, dqty))
    print("%-26s %6d %8.1f %8d %8d %8.2f %9.4f %9.4f" %
          (c, len(s), statistics.median(sup), min(sup), max(sup),
           statistics.median(qty) / 1000.0,
           statistics.median(dsup), statistics.median(dqty)))

print("\nthe worst cell, per commodity (rule 13 step 1: the worst cell, not the mean)")
for c, s, sup, qty, dsup, dqty in rows:
    worst = sorted(s, key=lambda x: x[1])[:3]
    print("  %-26s %s" % (c, "  ".join("%04d-%02d: %d mkts" % (k[0], k[1], n)
                                       for k, n, _ in worst)))

print("\nfloor for gate D24: month-on-month |dlog(support)| in an UNTREATED series")
for c, s, sup, qty, dsup, dqty in rows:
    if not dsup:
        continue
    q = sorted(dsup)
    print("  %-26s n=%3d  median %.4f  p75 %.4f  p90 %.4f  max %.4f"
          % (c, len(dsup), statistics.median(dsup),
             q[int(.75 * len(q))], q[int(.90 * len(q))], max(dsup)))

print("\nthe gradient (D36): thinner commodity -> what happens to level and noise")
for c, s, sup, qty, dsup, dqty in sorted(rows, key=lambda r: statistics.median(r[2])):
    print("  %-26s support median %6.1f   |dlog support| median %.4f   rows-equivalent kt %.2f"
          % (c, statistics.median(s and [x[1] for x in s]),
             statistics.median(dsup) if dsup else float("nan"),
             statistics.median(qty) / 1000.0))
