"""Is a reporting market's record complete and procedurally faithful?

The station's outcome counts markets with a positive arrival. Everything below
asks whether that count is a fact about trade or a fact about clerks. It is run
on the third-party scrape already on disk (2008-2017), because the questions are
about reporting behaviour and that does not need the newest data.

Five checks, each one a way the count could be wrong:
  1. rows that carry a price but no arrival -- a market present in the record but
     invisible to a count of positive arrivals;
  2. prices repeated verbatim from the market's previous reported day -- the
     signature of a clerk copying yesterday's sheet;
  3. arrivals repeated verbatim the same way;
  4. arrivals clustered near multiples of 100 across markets -- quintals entered
     into a tonnes field;
  5. how many days a month a reporting market actually reports.
"""
import csv
import math
import pathlib
import statistics
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
MON = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def rows(commodity):
    for f in sorted((DATA / commodity).glob("*.csv")):
        with f.open(encoding="utf-8", newline="") as fh:
            for r in csv.reader(fh):
                if len(r) < 10:
                    continue
                p = r[9].split()
                if len(p) != 3 or p[1] not in MON:
                    continue
                key = "%s|%s|%s" % (r[0], r[1], r[2])
                d = (int(p[2]), MON[p[1]], int(p[0]))
                yield key, r[3], r[5], r[6], r[7], r[8], d


# a directory under data/agmark is a commodity only if it holds the scrape's csv files.
# data/agmark/api/ is the API landing and holds json, so it is not one; reading it as a
# commodity divided by a zero row count.
for commodity in sorted(p.name for p in DATA.iterdir()
                        if p.is_dir() and any(p.glob("*.csv"))):
    n = blank_arr = 0
    per_market = defaultdict(list)
    for key, comm, arr, mn, mx, md, d in rows(commodity):
        n += 1
        try:
            a = float(arr)
        except ValueError:
            a = None
        if a is None or a <= 0:
            blank_arr += 1
        per_market[key].append((d, a, mn, mx, md))

    rep_price = rep_arr = pairs = 0
    tail = Counter()
    for key, recs in per_market.items():
        recs.sort()
        for x, y in zip(recs, recs[1:]):
            pairs += 1
            if (x[2], x[3], x[4]) == (y[2], y[3], y[4]):
                rep_price += 1
            if x[1] is not None and x[1] == y[1]:
                rep_arr += 1
        for _, a, _, _, _ in recs:
            if a and a > 0:
                tail[round(a % 1, 2)] += 1

    days = defaultdict(set)
    for key, recs in per_market.items():
        for d, a, _, _, _ in recs:
            days[(key, d[0], d[1])].add(d[2])
    per_month = [len(v) for v in days.values()]

    print("\n=== %s ===" % commodity)
    print("  rows                                   %8d" % n)
    print("  markets                                %8d" % len(per_market))
    print("  1. rows with no positive arrival       %8.2f%%" % (100.0 * blank_arr / n))
    print("  2. prices identical to prev report day %8.2f%%  (of %d consecutive pairs)"
          % (100.0 * rep_price / pairs if pairs else 0, pairs))
    print("  3. arrivals identical to prev report   %8.2f%%" % (100.0 * rep_arr / pairs if pairs else 0))
    whole = sum(c for frac, c in tail.items() if frac == 0.0)
    print("  4. arrivals that are whole numbers     %8.2f%%  (VOID: cannot separate a"
          % (100.0 * whole / max(sum(tail.values()), 1))
          + " quintal/tonne unit error from ordinary rounding at source, since both put"
          + " mass on whole numbers. Printed, not read.)")
    if per_month:
        q = sorted(per_month)
        print("  5. days reported per market-month      median %2d   p10 %2d   p90 %2d   (max 31)"
              % (statistics.median(per_month), q[len(q) // 10], q[9 * len(q) // 10]))
        print("     market-months with only 1 day        %8.2f%%"
              % (100.0 * sum(1 for v in per_month if v == 1) / len(per_month)))
