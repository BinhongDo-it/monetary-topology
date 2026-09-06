"""The support-set LEVEL read null. That is not the framework's prediction.

The prediction is that trade concentrates into fewer venues while volume rises, so the
object is not "how many markets filed a row" but "how many markets actually carry the
trade". Those are different numbers and the gap between them is the thing.

Per (commodity, state, year): pool each market's arrivals over the year, then
    raw      = markets that reported at all
    n_eff    = 1 / sum(share_i^2), the effective number of markets carrying the tonnage
    ratio    = n_eff / raw, how much of the nominal support set is real

n_eff is a within-cell distribution statistic, so unlike the raw count it does not move
just because a state changed how many mandis upload. That is the reason to expect a lower
resolution floor from it, and the floor is measured here rather than assumed.
"""
import json
import pathlib
import statistics
from collections import defaultdict

API = pathlib.Path(__file__).resolve().parents[1] / "data" / "agmark" / "api"
LISTED = {"Sponge gourd": "2019..2022", "Chrysanthemum(Loose)": "2019..2022",
          "Chrysanthemum": "2019..2022", "Kodo Millet(Varagu)": "2022..2024",
          "Foxtail Millet(Navane)": "2022..2024", "Water chestnut": "2025-02",
          "Mustard Oil": "2025-10", "Broken Rice": "2025-10", "Ashwagandha": "2025-10"}

year = defaultdict(lambda: defaultdict(float))       # (name,state,year) -> market -> tonnes
for cdir in sorted(p for p in API.iterdir() if p.is_dir()):
    for sdir in sorted(p for p in cdir.iterdir() if p.is_dir()):
        for f in sorted(sdir.glob("*.json")):
            j = json.loads(f.read_text(encoding="utf-8"))
            t = j["title"]
            nm = t.split("Commodity :", 1)[1].split(",")[0].strip()
            st = t.rsplit("State/UT :", 1)[-1].strip()
            for m in (j.get("markets") or []):
                v = sum(d.get("total_arrivals") or 0 for d in (m.get("dates") or []))
                if v > 0:
                    year[(nm, st, f.stem[:4])][m["marketName"]] += v

Y = [str(y) for y in range(2018, 2026)]
print("%-22s %-14s %-10s %6s %6s %6s   %s"
      % ("commodity", "state", "listed", "raw", "n_eff", "ratio", "n_eff by year 2018..2025"))
out = []
for (nm, st) in sorted({(a, b) for a, b, _ in year}):
    row = []
    for y in Y:
        mk = year.get((nm, st, y), {})
        tot = sum(mk.values())
        if not tot or len(mk) < 2:
            row.append((len(mk), float(len(mk) or 0)))
            continue
        hhi = sum((v / tot) ** 2 for v in mk.values())
        row.append((len(mk), 1.0 / hhi))
    raws = [r[0] for r in row]
    effs = [r[1] for r in row]
    if not sum(raws):
        continue
    cvr = statistics.stdev(raws) / statistics.mean(raws) if statistics.mean(raws) else 9
    cve = statistics.stdev(effs) / statistics.mean(effs) if statistics.mean(effs) else 9
    out.append((cve, nm, st, statistics.mean(raws), statistics.mean(effs), cvr, cve, effs))
out.sort()
for cve, nm, st, mr, me, cvr, _, effs in out:
    print("%-22s %-14s %-10s %6.1f %6.1f %6.2f   %s"
          % (nm[:22], st[:14], LISTED.get(nm, "?")[:10], mr, me, me / max(mr, 1e-9),
             " ".join("%.1f" % e for e in effs)))
print("\n%-22s %-14s %10s %10s" % ("commodity", "state", "cv(raw)", "cv(n_eff)"))
for cve, nm, st, mr, me, cvr, _, _ in out:
    flag = "  <- n_eff 的底更低" if cve < cvr * 0.75 else ""
    print("%-22s %-14s %9.1f%% %9.1f%%%s" % (nm[:22], st[:14], 100 * cvr, 100 * cve, flag))
