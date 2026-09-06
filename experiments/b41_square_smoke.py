"""B41 smoke reading: build every admissible square from one cached report-day.

Reads only what b41_ams_probe.py has already written under data/b41/cache, so it
needs no network and no key.

A cell is (trade_loc, commodity, class, grade, delivery window, futures month).
Two rules decide what may enter a square, and both come from the report itself
rather than from a choice made here:

  1. Within one commodity, the two positions must carry the same delivery window
     and the same futures month. Differencing across months would import a
     calendar spread. Across commodities the window may differ, because a fixed
     effect of (commodity, window) cancels when the two positions are subtracted.
  2. A cell whose own basis range straddles two futures months is dropped whole,
     because its two endpoints are not on one measuring stick.

Quotes are ranges, so every square is reported twice: the midpoint, and the
envelope over all endpoint combinations. Zero inside the envelope is the middle
state of the three, not a failure.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from itertools import combinations, product
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b41" / "cache"

# Statutory pounds per bushel. A square is only clean when the two commodities
# share this number, otherwise a per-ton or per-car cost leaves a residue.
TEST_WEIGHT = {"Soybeans": 60, "Wheat": 60, "Corn": 56, "Oats": 32,
               "Barley": 48, "Sorghum": 56, "Rye": 56}


def load(slug_id: int, day: str) -> list[dict]:
    tag = day.replace("/", "_")
    hits = sorted(CACHE.glob(f"reports_{slug_id}_Report_Detail__*{tag}*.json"))
    if not hits:
        raise SystemExit(f"no cached Report Detail for {slug_id} on {day}. "
                         f"Run the probe with --fields {slug_id} "
                         f'--section "Report Detail" --day {day} first.')
    return json.loads(hits[0].read_text(encoding="utf-8"))["results"]


def position(r: dict) -> str:
    """A position is a named place and a facility type together.

    Several reports leave trade_loc empty and carry the whole report at one
    facility type, and several others quote two facility types at one named
    zone. Both are positions in the sense the square needs, so the key is the
    pair, with the facility type standing alone when the place is unnamed."""
    loc = (r.get("trade_loc") or "").strip()
    fac = (r.get("delivery_point") or "").strip()
    return f"{loc} | {fac}" if loc else fac


def cells(rows: list[dict]) -> dict:
    """(commodity, class, grade, window, month) -> {position: (lo, hi)}."""
    out: dict[tuple, dict[str, tuple[float, float]]] = {}
    dropped = []
    for r in rows:
        m_lo = r.get("basis Min Futures Month")
        m_hi = r.get("basis Max Futures Month")
        pos = position(r)
        lo, hi = r.get("basis Min"), r.get("basis Max")
        if not pos or lo is None or hi is None or not m_lo:
            dropped.append((pos, r.get("commodity"), "no position or no basis"))
            continue
        if m_lo != m_hi:
            dropped.append((pos, r.get("commodity"), f"range straddles {m_lo} / {m_hi}"))
            continue
        # protein, conventional, freight and trans_mode all vary between rows
        # in some reports and each of them is a terms difference rather than a
        # position difference, so they go in the key instead of being averaged
        # over. quote_type and sale Type are filtered rather than keyed: only a
        # basis bid belongs in this square.
        if r.get("quote_type") != "Basis" or r.get("sale Type") != "Bid":
            dropped.append((pos, r.get("commodity"),
                            f'{r.get("quote_type")} / {r.get("sale Type")}'))
            continue
        key = (r.get("commodity"), r.get("class") or "", r.get("grade") or "",
               f'{r.get("delivery_start") or "current"}~{r.get("delivery_end") or "current"}',
               m_lo, r.get("protein") or "", r.get("conventional") or "",
               r.get("freight") or "", r.get("trans_mode") or "")
        out.setdefault(key, {})[pos] = (float(lo), float(hi))
    return out, dropped


def window_gap(wa: str, wb: str) -> int | None:
    """Days between the two delivery windows, or None when it cannot be told.

    Zero means the two commodities are quoted for the same window, which is
    what the square needs: a position cost that moves with the horizon does
    not cancel when the horizons differ."""
    if wa == wb:
        return 0
    if "current" in wa or "current" in wb:
        return None
    try:
        a = date.fromisoformat(wa.split("~")[0])
        b = date.fromisoformat(wb.split("~")[0])
    except ValueError:
        return None
    return abs((a - b).days)


def squares(cells_by_key: dict, com_a: str, com_b: str) -> list[dict]:
    keys_a = [k for k in cells_by_key if k[0] == com_a]
    keys_b = [k for k in cells_by_key if k[0] == com_b]
    found = []
    for ka, kb in product(keys_a, keys_b):
        pa, pb = cells_by_key[ka], cells_by_key[kb]
        shared = sorted(set(pa) & set(pb))
        if len(shared) < 2:
            continue
        for i, j in combinations(shared, 2):
            ai, aj, bi, bj = pa[i], pa[j], pb[i], pb[j]
            mid = ((sum(ai) / 2 - sum(bi) / 2) - (sum(aj) / 2 - sum(bj) / 2))
            vals = [(x - y) - (z - w)
                    for x, z, y, w in product(ai, aj, bi, bj)]
            fac_i = i.split("|")[-1].strip()
            fac_j = j.split("|")[-1].strip()
            found.append(dict(key_a=ka, key_b=kb, pos_i=i, pos_j=j,
                              mid=mid, lo=min(vals), hi=max(vals),
                              positions=len(shared),
                              gap=window_gap(ka[3], kb[3]),
                              same_facility=fac_i == fac_j))
    return found


def mode_all(pair: list[str]) -> None:
    """Every cached day, counting only squares whose windows line up."""
    ca, cb = pair
    tot_all = tot_matched = tot_out = 0
    print(f"{'report':>7} {'state':<6} {'squares':>8} {'matched':>8} "
          f"{'0 outside':>10}  strongest clean square")
    for f in sorted(CACHE.glob("*Report_Detail*")):
        rows = json.loads(f.read_text(encoding="utf-8")).get("results") or []
        if not rows:
            continue
        rid, st = rows[0].get("slug_id"), rows[0].get("market_location_state")
        by_key, _ = cells(rows)
        found = squares(by_key, ca, cb)
        matched = [s for s in found
                   if s["gap"] == 0 and s["same_facility"]]
        out = [s for s in matched if not (s["lo"] <= 0 <= s["hi"])]
        tot_all += len(found); tot_matched += len(matched); tot_out += len(out)
        best = max(matched, key=lambda s: abs(s["mid"]), default=None)
        shown = ("" if best is None else
                 f'{best["mid"]:+7.2f}  [{best["lo"]:+.0f}, {best["hi"]:+.0f}]  '
                 f'{best["pos_i"]}  vs  {best["pos_j"]}')
        print(f"{str(rid):>7} {str(st):<6} {len(found):>8} {len(matched):>8} "
              f"{len(out):>10}  {shown}")
    print(f"\n{tot_all} squares in all, {tot_matched} clean (same facility type "
          f"on both sides, windows and months lined up), {tot_out} of those with "
          f"zero outside the envelope")
    print("One day per report. Units are cents per bushel, floor 1 cent.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=int, default=None)
    ap.add_argument("--day", default=None, metavar="MM/DD/YYYY")
    ap.add_argument("--pair", nargs=2, default=["Soybeans", "Wheat"])
    ap.add_argument("--all", action="store_true",
                    help="every cached Report Detail day, matched windows only")
    a = ap.parse_args()

    if a.all:
        return mode_all(a.pair)
    if not (a.report and a.day):
        ap.error("give --report and --day, or --all")
    rows = load(a.report, a.day)
    by_key, dropped = cells(rows)
    print(f"{len(rows)} rows, {len(by_key)} cell groups, {len(dropped)} rows dropped")
    for d in dropped:
        print(f"    dropped {d[0]!r} {d[1]!r}: {d[2]}")

    ca, cb = a.pair
    wa, wb = TEST_WEIGHT.get(ca), TEST_WEIGHT.get(cb)
    print(f"\npair {ca} ({wa} lb/bu) against {cb} ({wb} lb/bu): "
          f"{'equal, freight cancels exactly' if wa == wb else 'UNEQUAL, a per-car cost leaves a residue'}")

    found = squares(by_key, ca, cb)
    if not found:
        print("no admissible square on this day")
        return
    print(f"\n{len(found)} admissible squares (not independent; see b1 below)\n")
    hdr = f"{'i':<20}{'j':<20}{ca[:8]:<26}{cb[:8]:<26}{'mid':>8}{'envelope':>18}{'zero':>6}"
    print(hdr); print("-" * len(hdr))
    for s in sorted(found, key=lambda s: -abs(s["mid"])):
        wa_ = f'{s["key_a"][3]} {s["key_a"][4][:12]}'
        wb_ = f'{s["key_b"][3]} {s["key_b"][4][:12]}'
        zin = "in" if s["lo"] <= 0 <= s["hi"] else "OUT"
        print(f'{s["pos_i"]:<20}{s["pos_j"]:<20}{wa_:<26}{wb_:<26}'
              f'{s["mid"]:>+8.2f}{f"[{s[chr(108)+chr(111)]:+.1f}, {s[chr(104)+chr(105)]:+.1f}]":>18}{zin:>6}')

    best = max((s["positions"] for s in found), default=0)
    print(f"\nlargest position set shared by one commodity pairing: {best}")
    print(f"b1 for that block = (m-1)(n-1) = ({best}-1)(2-1) = {max(best - 1, 0)}")
    print("Units are cents per bushel. The floor is 1 cent.")


if __name__ == "__main__":
    main()
