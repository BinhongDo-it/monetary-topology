"""B42: turn a captured registration snapshot into a panel, and count the gates on it.

The readings this stage reported first were produced by throwaway shell one-liners.
The numbers were written down and the code was not, which makes them unreproducible
and leaves the criteria living nowhere. This file is where they live now: the same
counts, from a file, so that rerunning it gives the same string of numbers.

What the snapshot holds. One sheet, one section per futures contract, and each
section has its own set of delivery districts, because the exchange does not
partition space the same way for every commodity. Within a section the rows are
firm and town, the district columns carry certificates in store, and three columns
on the right carry the date the current balance took effect, the balance before it,
and the date that one took effect. Those three are the reason a single snapshot is
already a short history rather than a single point.

    python experiments/b42_registration_panel.py --describe   # print the object
    python experiments/b42_registration_panel.py --gate       # D18 and D22 counts
    python experiments/b42_registration_panel.py --events     # changes, with windows
    python experiments/b42_registration_panel.py --record     # write results/

Rows that are not facilities are not deleted, they are declined by a stated naming
rule and printed, so the filter can be audited instead of trusted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DAILY = REPO / "data" / "b42" / "_daily"
OUT = REPO / "results" / "b42_registration_panel.json"

# A facility row names a town and a state, like "MAUMEE, OH". Totals rows, blank
# rows and a date string that leaks into the location column on some days all fail
# this, which is how they are declined rather than removed. Same idea as the loader
# in the B2 stage: the rule is in the code, the files stay on disk.
TOWN = re.compile(r"^[A-Z0-9 .()'&/-]+,\s*[A-Z]{2}$")

# One row in the 2026-09-02 issue reads "HAVANA,, IL". A doubled separator is a
# typing defect in the source, not a different place, so it is repaired here and
# the repair is recorded, rather than being either silently accepted by a looser
# pattern or silently lost by a stricter one.
def normalise_town(t: str) -> tuple[str, bool]:
    fixed = re.sub(r",\s*,", ", ", t).strip()
    return fixed, fixed != t

PAIR = ("CORN FUTURES", "SOYBEAN FUTURES")
AMS_START = date(2020, 2, 1)   # first day of the basis cache this stage joins to


def latest_day() -> str:
    days = sorted({p.name.split("-", 1)[1][:10] for p in DAILY.glob("registration-*.xls")
                   if ".suspect" not in p.name})
    if not days:
        raise SystemExit(f"no registration snapshot in {DAILY}; run the capture first")
    return days[-1]


def parse(day: str | None = None) -> dict:
    import xlrd
    day = day or latest_day()
    path = DAILY / f"registration-{day}.xls"
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(0)
    val = lambda r, c: sh.cell_value(r, c)

    def as_date(x):
        if isinstance(x, float) and x > 1000:
            return xlrd.xldate.xldate_as_datetime(x, wb.datemode).date().isoformat()
        return None

    heads = [r for r in range(sh.nrows) if str(val(r, 1)).strip().lower() == "firm"]
    labels = {r: str(val(r, 0)).strip() for r in range(sh.nrows)
              if str(val(r, 0)).strip() and not str(val(r, 1)).strip()
              and "Under Registration" not in str(val(r, 0))}

    rows, declined, repairs = [], [], []
    for i, h in enumerate(heads):
        section = labels[max(k for k in labels if k < h)]
        end = heads[i + 1] - 2 if i + 1 < len(heads) else sh.nrows
        dcol = min(c for c in range(3, sh.ncols) if str(val(h, c)).strip() == "Date")
        districts = {c: str(val(h, c)).strip() for c in range(3, dcol)}
        firm = ""
        for r in range(h + 1, end):
            f, town = str(val(r, 1)).strip(), str(val(r, 2)).strip()
            if f:
                firm = f
            if not town:
                continue
            town, repaired = normalise_town(town)
            if not TOWN.match(town):
                declined.append({"section": section, "row": r, "location": town})
                continue
            if repaired:
                repairs.append({"section": section, "row": r, "location": town})
            cells = [(districts[c], float(val(r, c))) for c in range(3, dcol)
                     if val(r, c) != ""]
            if not cells:
                continue
            district, certs = cells[0]
            prev = val(r, 11)
            rows.append({
                "commodity": section, "firm": firm, "town": town,
                "district": district, "certificates": certs,
                "effective": as_date(val(r, dcol)),
                "previous": float(prev) if prev != "" else None,
                "previous_effective": as_date(val(r, 12)),
                "extra_districts": len(cells) - 1,
            })
    rows.sort(key=lambda d: (d["commodity"], d["town"], d["firm"], d["district"]))
    return {"day": day, "rows": rows, "declined": declined, "repairs": repairs,
            "sections": sorted({r["commodity"] for r in rows})}


def describe(p: dict) -> None:
    rows = p["rows"]
    print(f"snapshot {p['day']}   parsed rows {len(rows)}   "
          f"declined {len(p['declined'])}   repaired {len(p['repairs'])}")
    for d in p["repairs"]:
        print(f"   repaired separator: {d['section']} row {d['row']}  {d['location']!r}")
    print(f"\ndeclined rows, printed rather than dropped silently:")
    for d in p["declined"]:
        print(f"   {d['section']:28s} row {d['row']:3d}  {d['location']!r}")
    multi = [r for r in rows if r["extra_districts"]]
    print(f"\nrows carrying more than one district: {len(multi)}")
    print(f"\n{'commodity':28s} {'rows':>5} {'firms':>6} {'towns':>6} {'districts':>10} "
          f"{'nonzero':>8} {'certs':>10}")
    for s in p["sections"]:
        rs = [r for r in rows if r["commodity"] == s]
        print(f"{s:28s} {len(rs):5d} {len({r['firm'] for r in rs}):6d} "
              f"{len({r['town'] for r in rs}):6d} {len({r['district'] for r in rs}):10d} "
              f"{sum(1 for r in rs if r['certificates'] > 0):8d} "
              f"{sum(r['certificates'] for r in rs):10.0f}")
    print("\nEach section carries its own district names, so the exchange does not use "
          "one partition of space for every commodity:")
    for s in p["sections"]:
        ds = sorted({r["district"] for r in rows if r["commodity"] == s})
        print(f"   {s:28s} {ds}")


def gate(p: dict) -> dict:
    rows = p["rows"]
    by_town = defaultdict(set)
    for r in rows:
        by_town[r["town"]].add(r["commodity"])
    multi = {t: sorted(s) for t, s in by_town.items() if len(s) >= 2}
    pair_towns = sorted(t for t, s in by_town.items() if set(PAIR) <= s)
    b1 = (len(pair_towns) - 1) * (len(PAIR) - 1)
    g = {"towns": len(by_town), "towns_multi_commodity": len(multi),
         "pair": list(PAIR), "pair_towns": pair_towns, "b1": b1}
    print(f"D18  towns                     {g['towns']}")
    print(f"D18  towns with >=2 commodities {g['towns_multi_commodity']}")
    print(f"D22  {PAIR[0]} x {PAIR[1]}: {len(pair_towns)} shared towns, b1 = {b1}")
    for t in pair_towns:
        print(f"        {t}")
    print("\ntowns carrying three or more commodities:")
    for t, s in sorted(multi.items()):
        if len(s) >= 3:
            print(f"   {t:24s} {s}")
    return g


def events(p: dict, quiet: bool = False) -> list:
    ev = []
    for r in p["rows"]:
        if not r["effective"] or r["previous"] is None or not r["previous_effective"]:
            continue
        d1 = date.fromisoformat(r["effective"])
        d0 = date.fromisoformat(r["previous_effective"])
        ev.append({**r, "window_days": (d1 - d0).days,
                   "delta": r["certificates"] - r["previous"]})
    ev.sort(key=lambda e: (e["effective"], e["town"], e["commodity"]))
    if quiet:
        return ev
    print(f"changes carried by the snapshot itself: {len(ev)}")
    post = [e for e in ev if date.fromisoformat(e["effective"]) >= AMS_START]
    print(f"of those, effective on or after {AMS_START}: {len(post)}")
    g = gate(p) if False else None
    by_town = defaultdict(set)
    for r in p["rows"]:
        by_town[r["town"]].add(r["commodity"])
    pair_towns = {t for t, s in by_town.items() if set(PAIR) <= s}
    sel = [e for e in post if e["town"] in pair_towns and e["commodity"] in PAIR]
    print(f"of those, on the {PAIR[0]}/{PAIR[1]} rectangle: {len(sel)}")
    widths = sorted(e["window_days"] for e in sel)
    if widths:
        n = len(widths)
        print(f"\nwindow width in days: min {widths[0]}  median {widths[n//2]}  "
              f"max {widths[-1]}")
        for k in (1, 3, 7, 14, 30, 90):
            print(f"   events whose window is <= {k:3d} days: "
                  f"{sum(1 for w in widths if w <= k)}")
        print("\nThe window is the pair of dates the change sits between, not a single "
              "day. An event study needs the window narrow enough that nothing else "
              "explains the move, so the count at each width above is what the design "
              "can actually use, and it is smaller than the count of events.")
    to_zero = [e for e in sel if e["certificates"] == 0]
    from_zero = [e for e in sel if e["previous"] == 0]
    print(f"\ndirection: {len(to_zero)} of {len(sel)} end at zero, "
          f"{len(from_zero)} start from zero")
    yrs = sorted({e["effective"][:4] for e in sel if e["certificates"] != 0})
    print(f"   the {len(sel)-len(to_zero)} that do not end at zero fall in {yrs}")
    print("   That direction is the truncation, not the world. A snapshot keeps only "
          "the most recent change per row, and most rows currently sit at zero, so "
          "most preserved changes are the one that took them there. The retrospective "
          "set is therefore close to one-sided, and a forward panel is what supplies "
          "the other side.")
    towns = sorted({e["town"] for e in sel})
    zones = sorted({e["district"] for e in sel})
    print(f"\ncoverage: {len(towns)} of the shared towns carry an event, zones {zones}")
    for t in towns:
        n = sum(1 for e in sel if e["town"] == t)
        print(f"   {t:22s} {n}")
    print(f"\n{'effective':11s} {'window':>7} {'town':22s} {'commodity':16s} "
          f"{'district':8s} {'from':>8} {'to':>8}")
    for e in sel:
        print(f"{e['effective']:11s} {e['window_days']:7d} {e['town']:22s} "
              f"{e['commodity']:16s} {e['district']:8s} "
              f"{e['previous']:8.0f} {e['certificates']:8.0f}")
    return sel


def record(p: dict) -> None:
    g = gate(p)
    sel = events(p, quiet=True)
    by_town = defaultdict(set)
    for r in p["rows"]:
        by_town[r["town"]].add(r["commodity"])
    pair_towns = {t for t, s in by_town.items() if set(PAIR) <= s}
    usable = [e for e in sel
              if date.fromisoformat(e["effective"]) >= AMS_START
              and e["town"] in pair_towns and e["commodity"] in PAIR]
    payload = {
        "stage": "B42",
        "diagnostic_only": True,
        "diagnostic_reason": ("Gate counts and the event list from one snapshot. No "
                              "criterion is scored here; B42-4 needs the basis panel."),
        "snapshot_day": p["day"],
        "parsed_rows": len(p["rows"]),
        "declined_rows": p["declined"],
        "repaired_rows": p["repairs"],
        "sections": p["sections"],
        "gate": g,
        "events_on_pair_rectangle": usable,
        "events_by_window": {str(k): sum(1 for e in usable if e["window_days"] <= k)
                             for k in (1, 3, 7, 14, 30, 90)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1),
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--day", help="snapshot day, default the latest on disk")
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--events", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    p = parse(a.day)
    if a.describe: describe(p)
    if a.gate: gate(p)
    if a.events: events(p)
    if a.record: record(p)
    if not (a.describe or a.gate or a.events or a.record):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
