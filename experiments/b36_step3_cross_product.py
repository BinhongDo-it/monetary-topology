"""B36-9: three meats, one registration regime, one set of tariff dates.

The question this settles that a single series cannot. Beef exports to China
step down in one month, April 2025. Two candidate causes both sit in March
2025: a five year establishment registration under GACC decree 248 expiring
mid-March, and a retaliatory tariff effective March 10 with escalations in
April. A date cannot separate them because they share it.

What separates them is scope. Pork and poultry live under the same registration
regime with the same expiry and the same tariff decrees. If the step is a
tariff, all three step together. If it is the registration, only the meat whose
plants were not renewed steps.

Pork and poultry are meat, so "beef is special" has nowhere to stand. That is
why this ring comes before soybeans and sorghum.

The statistic, and it is a shape rather than a line:

    S_X(m) = mean(kg over m, m+1, m+2) / mean(kg over m-3, m-2, m-1)

Reported per meat: argmin S, min S, S at 2025-04, the median and the standard
deviation of S over the window. The verdict rests on whether the argmin months
coincide, which is a comparison between three months, not a threshold.

Criteria are in the B36 result file, section R14, written before the monthly
pork and poultry series had been looked at.

Run:
    python b36_step3_cross_product.py
"""

import argparse
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

MEATS = [("beef", ["0201", "0202"]),
         ("pork", ["0203"]),
         ("poultry", ["0207"])]
CHINA = "5700"
LEVEL = "HS10"
WIN = ("2025-01", "2026-03")   # months at which a step is looked for
BREAK = "2025-04"              # the month beef broke, named before this ran
BASE_YEAR = 2024               # the level each recovery is measured against
RECOVER = ("2025-07", "2026-06")


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


def read_series(cache: Path, heads):
    """Monthly kilograms, straight from the per cell cache.

    The cache holds one file per (head, year, month, destination, level) and
    each file is the raw API answer, header row first. Reading it here rather
    than a combined record keeps this script independent of which combined
    records happen to exist.
    """
    per = defaultdict(float)
    seen = 0
    for head in heads:
        for f in sorted(cache.glob("%s_*_%s_%s.json" % (head, CHINA, LEVEL))):
            parts = f.stem.split("_")
            y, m = int(parts[1]), int(parts[2])
            try:
                rows = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                print("  cache damaged, skipped and named: %s" % f.name)
                continue
            seen += 1
            if not rows or rows[0] == ["_empty"]:
                per["%04d-%02d" % (y, m)] += 0.0
                continue
            hdr = rows[0]
            if "QTY_1_MO" not in hdr:
                continue
            i = hdr.index("QTY_1_MO")
            for r in rows[1:]:
                try:
                    per["%04d-%02d" % (y, m)] += float(r[i] or 0)
                except (ValueError, IndexError):
                    pass
    return per, seen


def step(per, m, allm):
    i = allm.index(m)
    if i < 3 or i + 3 > len(allm):
        return None
    before = [per.get(x, 0.0) for x in allm[i - 3:i]]
    after = [per.get(x, 0.0) for x in allm[i:i + 3]]
    b = sum(before) / 3.0
    if b <= 0:
        return None
    return (sum(after) / 3.0) / b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    cache = root / "data" / "b35"

    allm = months("2016-01", "2026-12")
    win = months(*WIN)
    rec = {}
    series = {}

    print("=" * 74)
    print("B36-9: monthly kilograms to China, three meats, from the cell cache")
    print("=" * 74)
    for name, heads in MEATS:
        per, seen = read_series(cache, heads)
        series[name] = per
        have = [m for m in allm if m in per]
        print("  %-8s heads %-12s cells %3d   months present %d, %s to %s"
              % (name, "+".join(heads), seen, len(have),
                 have[0] if have else "-", have[-1] if have else "-"))

    print("\n" + "=" * 74)
    print("monthly tonnes, 2024-10 onward, so the break is visible raw")
    print("=" * 74)
    print("  %-9s %12s %12s %12s" % ("month", "beef", "pork", "poultry"))
    for m in months("2024-10", "2026-06"):
        print("  %-9s %12.1f %12.1f %12.1f"
              % (m, series["beef"].get(m, 0) / 1e3, series["pork"].get(m, 0) / 1e3,
                 series["poultry"].get(m, 0) / 1e3))

    print("\n" + "=" * 74)
    print("gate six first: is the step above each series' own monthly noise")
    print("=" * 74)
    for name, _ in MEATS:
        vals = [(m, step(series[name], m, allm)) for m in win]
        vals = [(m, v) for m, v in vals if v is not None]
        if len(vals) < 6:
            print("  %-8s too few usable months, nothing judged" % name)
            rec[name] = {"usable": len(vals)}
            continue
        xs = [v for _, v in vals]
        med = statistics.median(xs)
        sd = statistics.pstdev(xs)
        mm, mv = min(vals, key=lambda kv: kv[1])
        # Gate six is measured on the log scale, and the first version of this
        # script measured it on the raw one. S is a ratio of positive sums: it
        # cannot go below zero and has no ceiling, so its standard deviation is
        # set by the upper tail. On the beef series that made the same
        # multiplicative move read as 0.77 sd going down and 2.14 sd going up.
        # The statistic was asymmetric in a way the question is not. Logs fix
        # that by construction, and nothing else in this script changes: the
        # argmin months, the minima and the recovery ratios are untouched.
        ls = [math.log(v) for v in xs if v > 0]
        lmed = statistics.median(ls) if ls else 0.0
        lsd = statistics.pstdev(ls) if ls else 0.0
        sb_raw = (med - mv) / sd if sd else float("inf")
        sb = ((lmed - math.log(mv)) / lsd) if (lsd and mv > 0) else float("inf")
        at_break = dict(vals).get(BREAK)
        print("  %-8s argmin %s  minS %.4f  median %.4f" % (name, mm, mv, med))
        print("           raw scale: sd %.4f, min is %.2f sd below median "
              "(not the gate, kept so the change is visible)"
              % (sd, sb_raw))
        print("           log scale: sd %.4f, min is %.2f sd below median "
              "<- this is gate six" % (lsd, sb))
        print("           S at %s: %s" % (BREAK, "%.4f" % at_break
                                          if at_break is not None else "n/a"))
        rec[name] = {"argmin": mm, "min_S": mv, "median_S": med, "sd_S": sd,
                     "sd_below_median_raw": sb_raw,
                     "log_sd_S": lsd, "sd_below_median": sb,
                     "S_at_break": at_break}

    if "argmin" not in rec.get("beef", {}):
        print("\nbeef has no usable step statistic. Nothing judged.")
        return
    if rec["beef"]["sd_below_median"] < 1.0:
        print("\ngate six: the beef step is not clear of its own monthly noise "
              "(%.2f sd). The arm is undecided and readings one to three are "
              "not looked at." % rec["beef"]["sd_below_median"])
        verdict = "UNDECIDED at gate six"
    else:
        def near(x, y, k=1):
            return abs(months("2016-01", "2026-12").index(x) -
                       months("2016-01", "2026-12").index(y)) <= k
        bm = rec["beef"]["argmin"]
        others = [n for n in ("pork", "poultry") if "argmin" in rec.get(n, {})]
        with_beef = [n for n in others if near(rec[n]["argmin"], bm)]
        print("\n" + "=" * 74)
        print("reading one: where the step falls, not how deep it is")
        print("=" * 74)
        print("  beef steps at %s" % bm)
        for n in others:
            print("  %-8s steps at %s  %s"
                  % (n, rec[n]["argmin"],
                     "within one month of beef" if n in with_beef
                     else "NOT within one month of beef"))
        if not with_beef and near(bm, BREAK):
            verdict = ("BEEF SPECIFIC. The cause acts on beef and not on the "
                       "other two meats under the same regime.")
        elif len(with_beef) == len(others) and others:
            verdict = ("COMMON. All three step together, which is what a "
                       "tariff on all United States meat looks like.")
        else:
            verdict = "UNDECIDED, the pattern is neither of the two registered."
    print("\n  verdict, reading one: %s" % verdict)

    print("\n" + "=" * 74)
    print("reading two: depth, printed, no verdict attached")
    print("=" * 74)
    for name, _ in MEATS:
        if "min_S" in rec.get(name, {}):
            print("  %-8s min S %.4f" % (name, rec[name]["min_S"]))
    print("  A common month with grossly unequal depth means both causes are "
          "present; that is recorded as undecided with the composition named.")

    print("\n" + "=" * 74)
    print("reading three: did it come back after the middle of 2025")
    print("=" * 74)
    print("  %-8s %14s %14s %8s" % ("meat", "2024 mean t/mo",
                                    "%s..%s t/mo" % RECOVER, "ratio"))
    for name, _ in MEATS:
        per = series[name]
        b = [per.get(m, 0.0) for m in months("2024-01", "2024-12")]
        r = [per.get(m, 0.0) for m in months(*RECOVER) if m in per]
        bm_ = sum(b) / max(len(b), 1)
        rm = sum(r) / max(len(r), 1)
        print("  %-8s %14.1f %14.1f %8.4f"
              % (name, bm_ / 1e3, rm / 1e3, rm / bm_ if bm_ else float("nan")))
        rec.setdefault(name, {})["recovery_ratio"] = rm / bm_ if bm_ else None
    print("  A cause that was withdrawn cannot explain a state that persisted.")
    print("  Whether and how far the tariff was withdrawn is B36-8, a document")
    print("  read; this table does not assume it.")

    rec["_verdict_reading_one"] = verdict
    rec["_window"] = {"step": list(WIN), "break": BREAK,
                      "recovery": list(RECOVER), "base_year": BASE_YEAR}
    out = Path(a.out) if a.out else root / "results" / "b36_cross_product.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
