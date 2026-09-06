"""Control for the composition confound in agmark_repeat.py.

The gap-1 population and the gap-15 population are not the same markets: a
market that reports every day contributes almost only gap-1 pairs, and a market
that reports twice a month contributes almost only long ones. So the decay in
the pooled repeat rate could be composition rather than decay.

Three things here, all cheap:

  1. Hold the market fixed. For each market with enough pairs in both buckets,
     compare its own short-gap rate to its own long-gap rate. Report the paired
     signs, not a pooled number.
  2. Print the triple/modal ratio by gap. A copied sheet repeats all three
     prices at once, so a copy component has ratio 1 and is flat; as the
     decaying genuine component dies off, a copy hypothesis predicts the ratio
     RISES toward 1. Falling refutes it in its own signature.
  3. Last digit of arrivals restricted to >= 10 tonnes. Below 10 the whole-tonne
     part IS the number, so its last digit carries the magnitude, not a
     trailing-digit signature. The restriction is what makes the test a test.
"""
import csv
import pathlib
import statistics
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
MON = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
SHORT = 1
LONG = 7
MIN_PAIRS = 30


def daynum(y, m, d):
    return (y * 372) + (m * 31) + d


def load(commodity):
    per = defaultdict(list)
    for f in sorted((DATA / commodity).glob("*.csv")):
        with f.open(encoding="utf-8", newline="") as fh:
            for r in csv.reader(fh):
                if len(r) < 10:
                    continue
                p = r[9].split()
                if len(p) != 3 or p[1] not in MON:
                    continue
                key = "%s|%s|%s" % (r[0], r[1], r[2])
                try:
                    a = float(r[5])
                except ValueError:
                    a = None
                per[key].append((daynum(int(p[2]), MON[p[1]], int(p[0])),
                                 a, r[6], r[7], r[8]))
    for k in per:
        per[k].sort()
    return per


for commodity in sorted(p.name for p in DATA.iterdir()
                        if p.is_dir() and any(p.glob("*.csv"))):
    per = load(commodity)
    print("\n=== %s ===" % commodity)

    # ---- 2. triple / modal ratio by gap -------------------------------------
    by_gap = defaultdict(lambda: [0, 0, 0, 0])
    for recs in per.values():
        for x, y in zip(recs, recs[1:]):
            g = min(y[0] - x[0], 15)
            if g < 1:
                continue
            c = by_gap[g]
            c[0] += 1
            c[1] += (x[2], x[3], x[4]) == (y[2], y[3], y[4])
            c[2] += x[4] == y[4]
            c[3] += x[1] is not None and x[1] == y[1]
    print("  gap  pairs   modal   triple   triple/modal   arrivals")
    for g in sorted(by_gap):
        n, t, mo, a = by_gap[g]
        if n < 200:
            continue
        print("  %3d %7d  %6.2f%%  %6.2f%%      %5.1f%%      %6.2f%%"
              % (g, n, 100.0 * mo / n, 100.0 * t / n,
                 100.0 * t / max(mo, 1), 100.0 * a / n))

    # ---- 1. paired within-market comparison --------------------------------
    per_mkt = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # sN,sTri,sArr, lN,lTri,lArr
    for key, recs in per.items():
        for x, y in zip(recs, recs[1:]):
            g = y[0] - x[0]
            if g < 1:
                continue
            slot = 0 if g <= SHORT else (3 if g >= LONG else None)
            if slot is None:
                continue
            c = per_mkt[key]
            c[slot] += 1
            c[slot + 1] += (x[2], x[3], x[4]) == (y[2], y[3], y[4])
            c[slot + 2] += x[1] is not None and x[1] == y[1]

    both = [(k, v) for k, v in per_mkt.items() if v[0] >= MIN_PAIRS and v[3] >= MIN_PAIRS]
    print("  markets with >= %d pairs in BOTH buckets (gap<=%d and gap>=%d): %d of %d"
          % (MIN_PAIRS, SHORT, LONG, len(both), len(per_mkt)))
    for lbl, off in (("price triple", 1), ("arrivals", 2)):
        if not both:
            break
        d = [(100.0 * v[off] / v[0]) - (100.0 * v[3 + off] / v[3]) for _, v in both]
        down = sum(1 for x in d if x > 0)
        print("    %-12s short minus long, per market: median %+7.2f pp   "
              "short higher in %d / %d markets" % (lbl, statistics.median(d), down, len(d)))

    # ---- 3. last digit, arrivals >= 10 t only -------------------------------
    for lo, hi, lbl in ((1, 10, "1..10 t"), (10, 1e18, ">= 10 t")):
        q = Counter()
        for recs in per.values():
            for _, a, _, _, _ in recs:
                if a and lo <= a < hi:
                    q[int(a) % 10] += 1
        s = sum(q.values())
        if s < 500:
            print("  last digit, %-8s n=%d  (too few, not read)" % (lbl, s))
            continue
        print("  last digit, %-8s n=%6d   %s   [0]+[5] = %.1f%% (uniform 20%%)"
              % (lbl, s, " ".join("%d:%4.1f" % (d, 100.0 * q[d] / s) for d in range(10)),
                 100.0 * (q[0] + q[5]) / s))
