"""B36-10: a second cycle. Brazil's two suspensions of beef exports to China.

Why this arm exists. The 2025 United States episode has an administrative
switch and a tariff sitting on the same month, and the identification there
rests on scope and on a withdrawal-restoration argument. A second, independent
episode turns a story into a repeated measurement: a mechanism that holds on
two independent episodes is not overturned by one later failure, because that
failure then has to compete with "something else was different that time".

The independence condition is what carries that, so it is counted honestly.
Brazil 2021 and Brazil 2023 share a country and a proximate cause, so they are
one family, not two. Against the United States episode that is two independent
episodes, not three.

This family is also free of the confound. Neither Brazilian suspension involved
any tariff at all, so if the shape matches, an administrative switch alone is
enough to produce it.

Dates, from documents, fixed before the monthly series was looked at:

    episode one    suspended 2021-09-04, resumed 2021-12-15, about 3.5 months
    episode two    suspended 2023-02-23, resumed 2023-03-23, about 1 month
    United States  registrations lapsed 2025-03, renewed 2026-05-15, 14 months

Predictions are in the B36 result file, section R16, written before this ran.

Run:
    python b36_step4_brazil_switch.py
"""

import argparse
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

EPISODES = [
    ("one", "2021-09", "2021-12", ["2021-10", "2021-11"]),
    ("two", "2023-02", "2023-03", ["2023-03"]),
]
WIN = ("2017-01", "2026-06")


def months(a, b):
    ya, ma = int(a[:4]), int(a[5:])
    yb, mb = int(b[:4]), int(b[5:])
    out = []
    while (ya, ma) <= (yb, mb):
        out.append("%04d-%02d" % (ya, ma))
        ma += 1
        if ma == 13:
            ma, ya = 1, ya + 1
    return out


def walk_rows(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("data", "list", "result", "results", "rows", "items"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for k2 in ("list", "data", "rows"):
                    if isinstance(v.get(k2), list):
                        return v[k2]
    return []


def read_brazil(cache: Path):
    per = defaultdict(float)
    files = sorted(cache.glob("general_china_*.json"))
    if not files:
        raise SystemExit("no Brazil cache in %s. Run b36_step2_brazil.py first."
                         % cache)
    for f in files:
        if f.stem.endswith("_probe"):
            continue
        try:
            rows = walk_rows(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:
            print("  cache damaged, named and skipped: %s (%s)" % (f.name, e))
            continue
        for r in rows:
            y = str(r.get("year") or "")
            m = str(r.get("monthNumber") or "").zfill(2)
            if len(y) != 4 or len(m) != 2:
                continue
            try:
                per["%s-%s" % (y, m)] += float(str(r.get("metricKG") or 0))
            except ValueError:
                pass
    return per, len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    per, nf = read_brazil(root / "data" / "b36")

    allm = months(*WIN)
    have = [m for m in allm if m in per]
    print("=" * 74)
    print("B36-10: Brazilian beef to China, monthly, from %d cached year files"
          % nf)
    print("=" * 74)
    print("  months present: %d, %s to %s" % (len(have), have[0], have[-1]))

    # Gate six first: how noisy is this series month to month, on its own terms.
    ratios = []
    for i in range(1, len(allm)):
        a0, b0 = per.get(allm[i - 1], 0.0), per.get(allm[i], 0.0)
        if a0 > 0:
            ratios.append(b0 / a0)
    med = statistics.median(ratios)
    sd = statistics.pstdev(ratios)
    # Same correction as the cross product script: a month on month ratio is
    # bounded below by zero and unbounded above, so its raw standard deviation
    # is set by the upper tail and understates every fall. The dispersion that
    # answers "is this dip unusual" is the one on the log scale.
    ls = [math.log(r) for r in ratios if r > 0]
    lmed = statistics.median(ls)
    lsd = statistics.pstdev(ls)
    print("\ngate six, the series' own month on month noise")
    print("  raw scale: median %.4f, sd %.4f, n %d  (not the gate)"
          % (med, sd, len(ratios)))
    print("  log scale: median %.4f, sd %.4f  <- the gate is read here"
          % (lmed, lsd))
    print("  A dip has to be clear of this before any reading is taken.")

    rec = {"noise": {"median": med, "sd": sd, "n": len(ratios),
                     "log_median": lmed, "log_sd": lsd}, "episodes": {}}

    for name, susp, back, inside in EPISODES:
        pre = [m for m in allm if m < susp][-6:]
        post = [m for m in allm if m > back][:6]
        pre_mean = sum(per.get(m, 0.0) for m in pre) / max(len(pre), 1)
        post_mean = sum(per.get(m, 0.0) for m in post) / max(len(post), 1)
        print("\n" + "=" * 74)
        print("episode %s: suspended %s, resumed %s" % (name, susp, back))
        print("=" * 74)
        print("  %-9s %14s %10s" % ("month", "tonnes", "vs pre"))
        span = months(months("2016-01", susp)[-4], months(back, "2026-12")[3])
        for m in span:
            q = per.get(m, 0.0)
            mark = "  <-- inside the suspension" if m in inside else ""
            print("  %-9s %14.1f %9.3f%s"
                  % (m, q / 1e3, q / pre_mean if pre_mean else 0.0, mark))
        deep = [per.get(m, 0.0) / pre_mean for m in inside if pre_mean]
        print("\n  six months before  : %12.1f t per month" % (pre_mean / 1e3))
        print("  six months after   : %12.1f t per month" % (post_mean / 1e3))
        print("  months fully inside: %s" % ", ".join("%.3f" % d for d in deep))
        for d in deep:
            if d > 0:
                print("     that month is %.2f log sd below the median month "
                      "on month move" % ((lmed - math.log(d)) / lsd if lsd else 0))
        print("  recovery ratio     : %.4f"
              % (post_mean / pre_mean if pre_mean else float("nan")))
        # how long the trough actually lasted, at half the pre level
        trough = [m for m in allm
                  if susp <= m <= months(back, "2026-12")[6]
                  and pre_mean and per.get(m, 0.0) < 0.5 * pre_mean]
        print("  months below half the pre level: %d  %s"
              % (len(trough), trough))
        rec["episodes"][name] = {
            "suspended": susp, "resumed": back,
            "pre_mean_t": pre_mean / 1e3, "post_mean_t": post_mean / 1e3,
            "inside_ratios": deep,
            "recovery_ratio": post_mean / pre_mean if pre_mean else None,
            "months_below_half": trough,
        }

    print("\n" + "=" * 74)
    print("prediction three: does the trough length track the block length")
    print("=" * 74)
    print("  %-14s %14s %16s" % ("episode", "block, months", "below half, months"))
    print("  %-14s %14.1f %16d"
          % ("Brazil one", 3.5, len(rec["episodes"]["one"]["months_below_half"])))
    print("  %-14s %14.1f %16d"
          % ("Brazil two", 1.0, len(rec["episodes"]["two"]["months_below_half"])))
    print("  %-14s %14.1f %16s"
          % ("United States", 14.0, "14, read in R13"))
    print("  Three points on a line is the switch. Not on a line is something")
    print("  else, and the reading is written up as that.")

    out = Path(a.out) if a.out else root / "results" / "b36_brazil_switch.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
