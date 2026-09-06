"""Is an 18% repeat rate a clerk copying yesterday's sheet, or a price that held?

The discriminant is the gap. A price that genuinely held is more likely to be
unchanged across one day than across ten, so a real-stability repeat rate decays
in the gap. A copied sheet does not care how old the sheet is, so a clerical
repeat rate is flat.

Two more, both cheap:
  - all three prices repeating at once is far rarer by chance than the modal
    price alone repeating. If the triple tracks the single, the row was copied.
  - the last digit of the arrivals figure. A measured quantity spreads its last
    digit; an invented one piles onto 0 and 5.
"""
import csv
import pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
MON = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def daynum(y, m, d):
    return (y * 372) + (m * 31) + d          # ordering only, gaps are approximate


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
    by_gap = defaultdict(lambda: [0, 0, 0, 0])   # gap -> [pairs, triple, modal, arrivals]
    for recs in per.values():
        for x, y in zip(recs, recs[1:]):
            g = min(y[0] - x[0], 15)
            if g < 1:
                continue
            c = by_gap[g]
            c[0] += 1
            if (x[2], x[3], x[4]) == (y[2], y[3], y[4]):
                c[1] += 1
            if x[4] == y[4]:
                c[2] += 1
            if x[1] is not None and x[1] == y[1]:
                c[3] += 1

    print("\n=== %s ===" % commodity)
    print("  gap  pairs   all 3 prices   modal only   arrivals")
    for g in sorted(by_gap):
        n, t, mo, a = by_gap[g]
        if n < 200:
            continue
        print("  %3d %7d      %6.2f%%       %6.2f%%     %6.2f%%"
              % (g, n, 100.0 * t / n, 100.0 * mo / n, 100.0 * a / n))

    tot = sum(v[0] for v in by_gap.values())
    tri = sum(v[1] for v in by_gap.values())
    mod = sum(v[2] for v in by_gap.values())
    print("  all gaps: triple %.2f%%, modal alone %.2f%%  -> triple is %.0f%% of modal"
          % (100.0 * tri / tot, 100.0 * mod / tot, 100.0 * tri / max(mod, 1)))

    last = Counter()
    for recs in per.values():
        for _, a, _, _, _ in recs:
            if a and a > 0:
                last[int(round(a * 100)) % 10] += 1
    s = sum(last.values())
    print("  last digit of arrivals (x100, so the paise place):")
    print("     " + "  ".join("%d:%4.1f%%" % (d, 100.0 * last[d] / s) for d in range(10)))
    q = Counter()
    for recs in per.values():
        for _, a, _, _, _ in recs:
            if a and a >= 1:
                q[int(a) % 10] += 1
    s2 = sum(q.values())
    print("  last digit of the whole-tonne part:")
    print("     " + "  ".join("%d:%4.1f%%" % (d, 100.0 * q[d] / s2) for d in range(10)))
