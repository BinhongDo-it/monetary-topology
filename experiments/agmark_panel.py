"""Build the (commodity, state, month) panel from the pulled Agmarknet responses and
describe it. No test here: the order is measure the worst cell, then describe, then decide
whether anything still needs testing.

Two quantities per cell, because the prediction is about the support set AGAINST volume,
not about either alone:
  markets   the number of markets that reported the commodity that month
  arrivals  the tonnage those markets reported

Read in differences, not ratios: on a base of two markets a ratio is meaningless and on a
base of zero it does not exist. Compare year totals rather than months, because a crop's
peak moves between years and a moved peak conserves the annual total.
"""
import json
import pathlib
import statistics
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = ROOT / "data" / "agmark" / "api"

# eNAM listing. The two 2019-2024 cohorts are only bracketed by the menu snapshots, so they
# carry a window rather than a day; the 2025 batches are dated by their announcements.
LISTED = {
    "Sponge gourd": ("2019-09", "2022-06"), "Chrysanthemum(Loose)": ("2019-09", "2022-06"),
    "Chrysanthemum": ("2019-09", "2022-06"),
    "Kodo Millet(Varagu)": ("2022-10", "2024-04"),
    "Foxtail Millet(Navane)": ("2022-10", "2024-04"),
    "Water chestnut": ("2025-02", "2025-02"),
    "Mustard Oil": ("2025-10", "2025-10"), "Broken Rice": ("2025-10", "2025-10"),
    "Ashwagandha": ("2025-10", "2025-10"),
}


def load():
    cells = {}
    for cdir in sorted(p for p in API.iterdir() if p.is_dir()):
        cid, name = cdir.name.split("_", 1)
        for sdir in sorted(p for p in cdir.iterdir() if p.is_dir()):
            for f in sorted(sdir.glob("*.json")):
                j = json.loads(f.read_text(encoding="utf-8"))
                mk = j.get("markets") or []
                arr = sum(d.get("total_arrivals") or 0
                          for m in mk for d in (m.get("dates") or []))
                # the state name is in the title, which is also what the fetch checked
                st = j["title"].rsplit("State/UT :", 1)[-1].strip()
                cells[(name, st, f.stem)] = (len(mk), round(arr, 2))
    return cells


cells = load()
pairs = sorted({(n, s) for n, s, _ in cells})
print("panel: %d cells, %d (commodity, state) pairs, %d months"
      % (len(cells), len(pairs), len({m for _, _, m in cells})))

print("\n=== annual market-months and annual arrivals, by pair ===")
print("  (a year's 'market-months' is the sum over its twelve monthly market counts)")
YEARS = [str(y) for y in range(2017, 2027)]
for name, st in pairs:
    per = defaultdict(lambda: [0, 0.0])
    for (n, s, ym), (mk, ar) in cells.items():
        if n == name and s == st:
            c = per[ym[:4]]
            c[0] += mk
            c[1] += ar
    full = [y for y in YEARS if y not in ("2017", "2026")]
    tot = [per[y][0] for y in full]
    cv = (statistics.stdev(tot) / statistics.mean(tot)) if len(tot) > 1 and sum(tot) else None
    lo, hi = LISTED.get(name, ("?", "?"))
    print("\n  %s | %s     listed %s..%s" % (name, st, lo, hi))
    print("    market-months " + " ".join("%s:%s" % (y, per[y][0]) for y in YEARS))
    print("    arrivals kt   " + " ".join("%s:%.0f" % (y, per[y][1] / 1000.0) for y in YEARS))
    print("    2018-2025 mean %.0f market-months, cv %s   <- this pair's resolution floor"
          % (statistics.mean(tot) if tot else 0,
             ("%.1f%%" % (100 * cv)) if cv else "n/a"))
