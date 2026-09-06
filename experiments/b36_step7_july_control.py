"""B36-7b: is Brazil's short July a collapse in the China lane, or an unfinished month.

Brazil shipped 82,714 tonnes of beef to China in July 2026 against 158,374 in
July 2025, a ratio of 0.522, and the fall is entirely in the dominant tariff
line: 02023000 is essentially the whole flow every month, and it is what halved.
A forced re-fetch on 2026-09-02 returned byte-identical data, so the source is
serving that figure rather than still filling it in.

**The tariff-line count cannot answer this and the first version of this check
used it.** Every line other than 02023000 carries zero or a few tonnes -- June's
five lines are 158,365 plus 12 plus three zeros -- so counting lines was
counting empty rows. That detector was reading nothing.

**What answers it is a control destination.** If Comex Stat's July is not
finished, every destination is short. If only the China lane is short, the month
is finished and the fall is in that lane.

**The reading, fixed here before the control is fetched.**

    controls also fall by about half     the month is unfinished; the fall is
                                         not read, and the fetch is repeated
                                         later
    controls hold and China alone falls  that is the collapse half of B36-1,
                                         read as such
    controls fall, but much less         both are present; report the two
                                         ratios and pick neither

**Why it matters that this is registered now.** The quota stands at 70% through
June with the ceiling projected weeks away, so a July collapse is exactly what
the arm predicted and exactly the reading that a person wants to be true. The
branches are written before the number arrives.

Run, after fetching the controls:
    python experiments\\b36_step2_brazil.py --years 2026 2026 --country CHILE
    python experiments\\b36_step2_brazil.py --years 2026 2026 --country EGYPT
    python experiments\\b36_step7_july_control.py
"""

import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "b36"
OUT = ROOT / "results" / "b36_july_control.json"
FOCUS = "china"
MONTH = 7


def monthly(slug, year):
    p = CACHE / ("general_%s_%d.json" % (slug, year))
    if not p.exists():
        return None
    out = {}
    for r in json.loads(p.read_text(encoding="utf-8"))["data"]["list"]:
        out[int(r["monthNumber"])] = out.get(int(r["monthNumber"]), 0.0) \
            + float(r["metricKG"]) / 1000.0
    return out


def main():
    slugs = sorted({p.name.split("general_")[1].rsplit("_", 1)[0]
                    for p in CACHE.glob("general_*_2026.json")})
    print("=" * 78)
    print("B36-7b: July in the China lane against July everywhere else")
    print("=" * 78)
    print("  destinations cached for 2026: %s" % ", ".join(slugs))
    if len(slugs) < 2:
        raise SystemExit(
            "\nonly the China lane is cached, so there is no control and "
            "nothing is read. Fetch at least one other destination first; the "
            "command is in this file's header. Nothing written.")

    rows = []
    print("\n  %-16s %10s %10s %8s %10s %8s %9s"
          % ("destination", "Jul 2025", "Jul 2026", "26/25", "Jun 2026",
             "Jul/Jun", "Jul/H1avg"))
    for sl in slugs:
        a, b = monthly(sl, 2025), monthly(sl, 2026)
        if not b or MONTH not in b:
            print("  %-16s  no 2026 month %d" % (sl, MONTH))
            continue
        yoy = (b[MONTH] / a[MONTH]) if (a and a.get(MONTH)) else None
        mom = b[MONTH] / b[MONTH - 1] if b.get(MONTH - 1) else None
        h1 = [b.get(k, 0.0) for k in range(1, MONTH)]
        vh1 = b[MONTH] / (sum(h1) / len(h1)) if h1 else None
        rows.append({"dest": sl, "jul25": a.get(MONTH) if a else None,
                     "jul26": b[MONTH], "yoy": yoy,
                     "jun26": b.get(MONTH - 1), "mom": mom, "vs_h1": vh1})
        print("  %-16s %10s %10.0f %8s %10s %8s %9s"
              % (sl, "%.0f" % a[MONTH] if (a and a.get(MONTH)) else "-",
                 b[MONTH], "%.3f" % yoy if yoy else "-",
                 "%.0f" % b[MONTH - 1] if b.get(MONTH - 1) else "-",
                 "%.3f" % mom if mom else "-",
                 "%.3f" % vh1 if vh1 else "-"))

    focus = next((r for r in rows if r["dest"] == FOCUS), None)
    ctrl = [r for r in rows if r["dest"] != FOCUS and r["mom"]]
    if not focus or not ctrl:
        raise SystemExit("\nthe China lane or every control is missing. "
                         "Nothing read.")

    # The registered branches ask whether the controls hold or fall with the
    # China lane. They were implemented year on year, and the controls were
    # fetched for 2026 only, so the same question is asked month on month
    # instead. That is a change of arithmetic and not of reading: "did July
    # come in short everywhere, or only in one lane" is what either one
    # answers, and an unfinished month is short on every comparison there is.
    # The year-on-year column is printed for whichever lane has it.
    med = sorted(r["mom"] for r in ctrl)[len(ctrl) // 2]
    key = "mom"
    print("\n  the controls are compared month on month, because they were")
    print("  fetched for 2026 only. An unfinished month is short on any")
    print("  comparison, so this answers the branch as written.")
    print("\n" + "=" * 78)
    print("the reading, on the branches written before the control was fetched")
    print("=" * 78)
    print("  China lane, July over June        %.3f" % focus["mom"])
    if focus["yoy"]:
        print("  China lane, July over July        %.3f" % focus["yoy"])
    print("  control median, July over June    %.3f" % med)
    print("  the China lane relative to it     %.3f" % (focus["mom"] / med))

    if med <= 0.70:
        verdict = ("UNFINISHED MONTH. The controls fall about as far, so the "
                   "source has not finished publishing July. The fall is not "
                   "read as anything, and the fetch is repeated later.")
    elif med >= 0.90 and focus["mom"] <= 0.70:
        verdict = ("COLLAPSE IN THE CHINA LANE. The controls hold and the "
                   "China lane alone halves. That is the collapse half of "
                   "B36-1, and it arrives with the quota at 70 per cent.")
    else:
        verdict = ("BOTH PRESENT. The controls fall too, but less. Both "
                   "ratios are reported and neither account is picked.")
    print("\n  %s" % verdict)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"month": MONTH, "rows": rows, "compared_on": key,
         "control_median": med, "focus_mom": focus["mom"],
         "focus_yoy": focus["yoy"], "verdict": verdict},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
