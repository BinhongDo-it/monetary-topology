"""Two more discriminants, both cheap, both aimed at a specific alternative.

(a) Run length. A price that is genuinely sticky ends its run at some hazard
    each filing, so run lengths fall off geometrically. A clerk who copies once
    tends to copy again, so copying produces long runs that a geometric tail
    cannot reach. The readable number is the longest run and the share of rows
    sitting inside a run of five or more.

(b) The arrivals repeat rate rises with the gap even holding the market fixed,
    which is neither a copying signature (flat) nor a stability one (falling).
    The candidate explanation is selection on the value, not on the market: a
    market skips filing when little trades, so long-gap pairs are pairs of small
    arrivals, and small arrivals live on a short discrete list. The control is
    to require both endpoints >= 10 t and see whether the slope goes away.
"""
import csv
import pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
MON = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


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

    # ---- (a) runs of the identical price triple, consecutive filings --------
    runs = Counter()
    longest = (0, "")
    rows = 0
    for key, recs in per.items():
        cur = 1
        for x, y in zip(recs, recs[1:]):
            rows += 1
            if (x[2], x[3], x[4]) == (y[2], y[3], y[4]):
                cur += 1
            else:
                runs[cur] += 1
                if cur > longest[0]:
                    longest = (cur, key)
                cur = 1
        runs[cur] += 1
        if cur > longest[0]:
            longest = (cur, key)
    tot_rows = sum(k * v for k, v in runs.items())
    in5 = sum(k * v for k, v in runs.items() if k >= 5)
    in10 = sum(k * v for k, v in runs.items() if k >= 10)
    print("  runs of identical (min,max,modal) across consecutive filings")
    print("    run length:  " + "  ".join(
        "%d:%s" % (n, runs.get(n, 0)) for n in (1, 2, 3, 4, 5, 6, 8, 10, 15, 20)))
    print("    rows inside a run >= 5: %.2f%%   >= 10: %.2f%%   longest run %d  (%s)"
          % (100.0 * in5 / tot_rows, 100.0 * in10 / tot_rows, longest[0], longest[1]))
    # geometric benchmark fitted on the run>=1 mean, for the tail only
    mean = tot_rows / sum(runs.values())
    p = 1.0 / mean
    exp5 = sum(runs.values()) * (1 - p) ** 4
    print("    runs >= 5 observed %d, geometric with the same mean predicts %.0f"
          % (sum(v for k, v in runs.items() if k >= 5), exp5))

    # ---- (b) arrivals repeat by gap, both endpoints >= 10 t ----------------
    for floor, lbl in ((0.0, "all sizes"), (10.0, "both >= 10 t")):
        by_gap = defaultdict(lambda: [0, 0])
        for recs in per.values():
            for x, y in zip(recs, recs[1:]):
                g = min(y[0] - x[0], 15)
                if g < 1 or x[1] is None or y[1] is None:
                    continue
                if x[1] < floor or y[1] < floor:
                    continue
                c = by_gap[g]
                c[0] += 1
                c[1] += x[1] == y[1]
        cells = [(g, v) for g, v in sorted(by_gap.items()) if v[0] >= 200]
        if not cells:
            print("  arrivals repeat, %-12s (too few pairs, not read)" % lbl)
            continue
        print("  arrivals repeat, %-12s " % lbl + "  ".join(
            "g%d:%5.2f%%(%d)" % (g, 100.0 * v[1] / v[0], v[0]) for g, v in cells))
