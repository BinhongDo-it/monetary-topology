"""Recheck of the same-place position count: print the pairs, not the count.

B42 result section R9.5 reports "17 same-place groups across the system" and
leans on it to say that the same-place family is the right carrier for this
arm. A group is not an instrument. Two positions at one named place produce a
square only when they quote at least two shared commodity identities on the
same day, and nothing in the count checked that.

The same shape has already cost this project twice today: a per-car comparison
paired by date without matching on tariff, and a position whose two commodities
turned out never to be quoted on the same days. So this file does what rule 11
says: print the object.

    python experiments/b42_same_place.py --enumerate
    python experiments/b42_same_place.py --enumerate --record

Reads only what is cached. No network, no key.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_square_smoke as S       # noqa: E402
import b41_persistence as P        # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b41" / "cache"
OUT = REPO / "results"


# Whether a shared place is a town or a region cannot be read off the label:
# "Toledo" and "Chicago" are cities while "South", "Purchase" and "Ohio River"
# are compass zones and river reaches. The published zone glossary that hangs
# on the footer of these reports is what settles it, so the two towns are
# listed here by hand rather than guessed from the string. The first version
# of this file tried to infer it from whether the label carried a dash, which
# marked Toledo as not-a-town, the one case the column exists for.
TOWNS = {"Toledo", "Chicago"}


def to_iso(s: str) -> str:
    """report_date arrives as MM/DD/YYYY. Sorted as text it puts December
    before February, so the first and last day of a window come out wrong
    while every count stays right, which is why the first version of this
    file printed windows that ended before they began. This is the third
    time this source's date format has done it, so the standing rule is that
    these dates never take part in an ordering operation in their native
    form."""
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        return f"{s[6:10]}-{s[0:2]}-{s[3:5]}"
    return s[:10]


def place_of(pos: str) -> str:
    """The geographic name inside a position key.

    A position is "trade_loc | facility". Two positions share a place when the
    trade_loc names the same town or zone, which happens two ways: one zone
    quoted at two facility types, and one town split into two zones by a
    suffix after a dash ("Toledo - On River"). Both are stripped here."""
    loc = pos.split(" | ")[0].strip() if " | " in pos else ""
    if not loc:
        return ""
    return loc.split(" - ")[0].strip()


def reports_cached() -> list[int]:
    ids = set()
    for f in CACHE.glob("reports_*_Report_Detail__*.json"):
        try:
            ids.add(int(f.name.split("_")[1]))
        except ValueError:
            continue
    return sorted(ids)


def scan(rid: int) -> dict:
    """Every same-place pair in one report, with what it can actually build."""
    by_day = P.load_all(rid)
    # position -> set of days ; (position, identity) -> set of days
    pos_days: dict[str, set] = defaultdict(set)
    cell_days: dict[tuple, set] = defaultdict(set)
    state = ""
    for day, rows in by_day.items():
        if not state:
            for r in rows:
                st = (r.get("market_location_state") or r.get("state") or "").strip()
                if st:
                    state = st
                    break
        cells, _ = S.cells(rows)
        for key, at in cells.items():
            for pos in at:
                pos_days[pos].add(day)
                cell_days[(pos, key)].add(day)

    by_place: dict[str, set] = defaultdict(set)
    for pos in pos_days:
        pl = place_of(pos)
        if pl:
            by_place[pl].add(pos)

    out = []
    for place, positions in sorted(by_place.items()):
        if len(positions) < 2:
            continue
        ps = sorted(positions)
        for a in range(len(ps)):
            for b in range(a + 1, len(ps)):
                i, j = ps[a], ps[b]
                both_pos = pos_days[i] & pos_days[j]
                shared = {k for (p, k) in cell_days if p == i} & \
                         {k for (p, k) in cell_days if p == j}
                # a square needs two identities present at both ends on one day
                per_day: dict[str, int] = defaultdict(int)
                for k in shared:
                    for d in cell_days[(i, k)] & cell_days[(j, k)]:
                        per_day[d] += 1
                square_days = sorted(to_iso(d) for d, n in per_day.items() if n >= 2)
                fac_i = i.split("|")[-1].strip()
                fac_j = j.split("|")[-1].strip()
                out.append(dict(
                    report=rid, state=state, place=place, pos_i=i, pos_j=j,
                    same_facility=fac_i == fac_j,
                    same_town=place in TOWNS,
                    days_i=len(pos_days[i]), days_j=len(pos_days[j]),
                    days_both=len(both_pos),
                    shared_identities=len(shared),
                    days_with_a_square=len(square_days),
                    first_square=square_days[0] if square_days else "",
                    last_square=square_days[-1] if square_days else "",
                ))
    return dict(report=rid, state=state, pairs=out,
                positions=len(pos_days), places=len(by_place))


def mode_enumerate(record: bool) -> None:
    rows, per_report = [], []
    for rid in reports_cached():
        try:
            r = scan(rid)
        except SystemExit as e:
            print(f"{rid}: {e}")
            continue
        per_report.append(dict(report=r["report"], state=r["state"],
                               positions=r["positions"], places=r["places"],
                               pairs=len(r["pairs"])))
        rows.extend(r["pairs"])

    groups = len({(r["report"], r["place"]) for r in rows})
    usable = [r for r in rows if r["days_with_a_square"] > 0]
    admitted = [r for r in usable if r["same_facility"]]
    print()
    print(f"reports scanned            {len(per_report)}")
    print(f"same-place groups          {groups}")
    print(f"same-place position pairs  {len(rows)}")
    print(f"pairs that build a square  {len(usable)}")
    print(f"  of those, same facility  {len(admitted)}   "
          f"(the existing B41 square filter admits only these)")
    print(f"  of those, at one named town "
          f"{len([r for r in admitted if r['same_town']])}"
          f"   (freight cannot enter a square inside one town)")
    print()
    hdr = (f"{'ST':<4}{'rid':>6}  {'place':<22}{'both':>6}{'ids':>5}"
           f"{'sqdays':>8} {'fac':>4} {'town':>5}  window")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda x: -x["days_with_a_square"]):
        win = (f'{r["first_square"]}..{r["last_square"]}'
               if r["first_square"] else "-")
        print(f'{r["state"]:<4}{r["report"]:>6}  {r["place"][:22]:<22}'
              f'{r["days_both"]:>6}{r["shared_identities"]:>5}'
              f'{r["days_with_a_square"]:>8} '
              f'{"same" if r["same_facility"] else "  - ":>4} '
              f'{"yes" if r["same_town"] else " - ":>5}  {win}')
    print()
    print("every pair, named:")
    for r in sorted(rows, key=lambda x: -x["days_with_a_square"]):
        print(f'  {r["days_with_a_square"]:>5}  {r["state"]} {r["place"]}: '
              f'{r["pos_i"]}  vs  {r["pos_j"]}')

    if record:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b42_same_place.json"
        dest.write_text(json.dumps(dict(
            stage="B42", diagnostic_only=True,
            diagnostic_reason=("recheck of R9.5: the published figure counted "
                               "candidate groups, this counts pairs that can "
                               "build a square"),
            reports=per_report,
            groups=groups, pairs=len(rows), pairs_with_a_square=len(usable),
            detail=sorted(rows, key=lambda x: (x["state"], x["place"])),
        ), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--enumerate", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    if a.enumerate:
        mode_enumerate(a.record)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
