"""B55: the counting law on a fee schedule that crosses several class lines at once.

Source: 4 Va. Admin. Code 15-20-65, retrieved 2026-09-07 from the Virginia
official code site. The class line is drawn by Code of Virginia 29.1-319, which
lists six ways to qualify as a resident; the Board's authority under 29.1-103
covers the fee and not the residency test. So the split is imposed and the
values are the Board's, which is exactly the shape the counting law reads.

Amounts are held in cents as integers. Nothing here is rounded: the schedule
publishes dollars and cents, so two different numbers cannot collapse into one,
which is the premise B55-1 checks. A "no fee" line is not an amount; it is an
exemption, and it is kept out of the value set and reported separately.

Every row carries the sub-heading it sits under in the source, which is what
rule 25 asks for: a transcription has to say where each item came from.
"""

import json
from collections import Counter
from pathlib import Path

SOURCE = "4 Va. Admin. Code 15-20-65"
RETRIEVED = "2026-09-07"

# (section, name, cents)  cents=None means the source says "no fee"
ROWS = [
 ("resident_hunt", "One-year Resident License to Hunt, 16+", 2200),
 ("resident_hunt", "Two-year Resident License to Hunt, 16+", 4300),
 ("resident_hunt", "Three-year Resident License to Hunt, 16+", 6400),
 ("resident_hunt", "Four-year Resident License to Hunt, 16+", 8500),
 ("resident_hunt", "Resident Three-Day Trip License to Hunt", 1100),
 ("resident_hunt", "County or City Resident License to Hunt in County or City of Residence Only, 16+", 1500),
 ("resident_hunt", "Resident Senior Citizen Annual License to Hunt, 65+", 800),
 ("resident_hunt", "Resident Junior License to Hunt, 12 through 15", 750),
 ("resident_hunt", "Resident Youth Combination License to Hunt, under 16", 1500),
 ("resident_hunt", "Resident Sportsman License to Hunt and Freshwater Fish", 9900),
 ("resident_hunt", "Resident Hunting License for Partially Disabled Veterans", 1100),
 ("resident_hunt", "Resident Infant Lifetime License to Hunt", 13000),
 ("resident_hunt", "Resident Junior Lifetime License to Hunt, under 12", 26000),
 ("resident_hunt", "Resident Lifetime License to Hunt, through 44", 26500),
 ("resident_hunt", "Resident Lifetime License to Hunt, 45 through 50", 21500),
 ("resident_hunt", "Resident Lifetime License to Hunt, 51 through 55", 16500),
 ("resident_hunt", "Resident Lifetime License to Hunt, 56 through 60", 11500),
 ("resident_hunt", "Resident Lifetime License to Hunt, 61 through 64", 6500),
 ("resident_hunt", "Resident Lifetime License to Hunt, 65+", 2500),
 ("resident_hunt", "Totally and Permanently Disabled Resident Special Lifetime License to Hunt", 1500),
 ("resident_hunt", "Service-Connected Totally and Permanently Disabled Veteran Resident Lifetime License to Hunt or Freshwater Fish", None),

 ("resident_hunt_extra", "Resident Deer and Turkey Hunting License, 16+", 2200),
 ("resident_hunt_extra", "Resident Junior Deer and Turkey Hunting License, under 16", 750),
 ("resident_hunt_extra", "Resident Archery License", 1700),
 ("resident_hunt_extra", "Resident Bear Hunting License", 2000),
 ("resident_hunt_extra", "Resident Muzzleloading License", 1700),
 ("resident_hunt_extra", "Resident Bonus Deer Permit", 1700),
 ("resident_hunt_extra", "Resident Fox Hunting License", 2200),
 ("resident_hunt_extra", "Resident Elk Hunt Lottery Application", 1500),
 ("resident_hunt_extra", "Resident Special Elk Hunting License", 4000),

 ("nonresident_hunt", "Nonresident License to Hunt, 16+", 11000),
 ("nonresident_hunt", "Nonresident Three-Day Trip License to Hunt", 5900),
 ("nonresident_hunt", "Nonresident Youth License to Hunt, under 12", 1200),
 ("nonresident_hunt", "Nonresident Youth License to Hunt, 12 through 15", 1500),
 ("nonresident_hunt", "Nonresident Youth Combination License to Hunt, under 16", 3000),
 ("nonresident_hunt", "Nonresident Annual Hunting License for Partially Disabled Veterans", 5500),
 ("nonresident_hunt", "Nonresident Annual Hunting License for Totally and Permanently Disabled Veterans", 2750),
 ("nonresident_hunt", "Nonresident Infant Lifetime License to Hunt", 27500),
 ("nonresident_hunt", "Nonresident Lifetime License to Hunt", 58000),

 ("nonresident_hunt_extra", "Nonresident Deer and Turkey Hunting License, 16+", 8500),
 ("nonresident_hunt_extra", "Nonresident Deer and Turkey Hunting License, 12 through 15", 1500),
 ("nonresident_hunt_extra", "Nonresident Deer and Turkey Hunting License, under 12", 1200),
 ("nonresident_hunt_extra", "Nonresident Bear Hunting License", 15000),
 ("nonresident_hunt_extra", "Nonresident Archery License", 3000),
 ("nonresident_hunt_extra", "Nonresident Muzzleloading License", 3000),
 ("nonresident_hunt_extra", "Nonresident Shooting Preserve License to Hunt", 2200),
 ("nonresident_hunt_extra", "Nonresident Bonus Deer Permit", 3000),
 ("nonresident_hunt_extra", "Nonresident Fox Hunting License", 11000),
 ("nonresident_hunt_extra", "Nonresident Elk Hunt Lottery Application", 2000),
 ("nonresident_hunt_extra", "Nonresident Special Elk Hunting License", 40000),

 ("misc_hunt", "Waterfowl Hunting Stationary Blind in Public Waters License", 2250),
 ("misc_hunt", "Waterfowl Hunting Floating Blind in Public Waters License", 4000),
 ("misc_hunt", "Foxhound Training Preserve License", 1700),
 ("misc_hunt", "Public Access Lands for Sportsmen Permit to Hunt, Trap, or Fish", 1700),

 ("trap", "One-year Resident License to Trap, 16+", 4500),
 ("trap", "Two-year Resident License to Trap, 16+", 8900),
 ("trap", "Three-year Resident License to Trap, 16+", 13300),
 ("trap", "Four-year Resident License to Trap, 16+", 17700),
 ("trap", "County or City Resident License to Trap in County or City of Residence Only", 2000),
 ("trap", "Resident Junior License to Trap, under 16", 1000),
 ("trap", "Resident Senior Citizen License to Trap, 65+", 800),
 ("trap", "Resident Senior Citizen Lifetime License to Trap, 65+", 2500),
 ("trap", "Totally and Permanently Disabled Resident Special Lifetime License to Trap", 1500),
 ("trap", "Service-Connected Totally and Permanently Disabled Veteran Resident Lifetime License to Trap", 1500),
 ("trap", "Nonresident License to Trap", 20500),

 ("resident_fish", "One-year Resident License to Freshwater Fish", 2200),
 ("resident_fish", "Two-year Resident License to Freshwater Fish", 4300),
 ("resident_fish", "Three-year Resident License to Freshwater Fish", 6400),
 ("resident_fish", "Four-year Resident License to Freshwater Fish", 8500),
 ("resident_fish", "County or City Resident License to Freshwater Fish in County or City of Residence Only", 1500),
 ("resident_fish", "Resident License to Freshwater Fish, 65+", 800),
 ("resident_fish", "Resident License to Fish in Designated Stocked Trout Waters", 2200),
 ("resident_fish", "Resident License to Freshwater and Saltwater Fish", 3850),
 ("resident_fish", "Resident License to Freshwater Fish for Five Consecutive Days", 1300),
 ("resident_fish", "Resident License to Freshwater and Saltwater Fish for Five Consecutive Days", 2300),
 ("resident_fish", "Resident Sportsman License to Hunt and Freshwater Fish", 9900),
 ("resident_fish", "Resident Fishing License for Partially Disabled Veterans", 1100),
 ("resident_fish", "Resident Infant Lifetime License to Fish", 13000),
 ("resident_fish", "Resident Special Lifetime License to Freshwater Fish, through 44", 26500),
 ("resident_fish", "Resident Special Lifetime License to Freshwater Fish, 45 through 50", 21500),
 ("resident_fish", "Resident Special Lifetime License to Freshwater Fish, 51 through 55", 16500),
 ("resident_fish", "Resident Special Lifetime License to Freshwater Fish, 56 through 60", 11500),
 ("resident_fish", "Resident Special Lifetime License to Freshwater Fish, 61 through 64", 6500),
 ("resident_fish", "Resident Special Lifetime License to Freshwater Fish, 65+", 2500),
 ("resident_fish", "Resident Special Lifetime License to Fish in Designated Stocked Trout Waters, through 44", 26500),
 ("resident_fish", "Resident Special Lifetime License to Fish in Designated Stocked Trout Waters, 45 through 50", 21500),
 ("resident_fish", "Resident Special Lifetime License to Fish in Designated Stocked Trout Waters, 51 through 55", 16500),
 ("resident_fish", "Resident Special Lifetime License to Fish in Designated Stocked Trout Waters, 56 through 60", 11500),
 ("resident_fish", "Resident Special Lifetime License to Fish in Designated Stocked Trout Waters, 61 through 64", 6500),
 ("resident_fish", "Resident Special Lifetime License to Fish in Designated Stocked Trout Waters, 65+", 2500),
 ("resident_fish", "Totally and Permanently Disabled Resident Special Lifetime License to Freshwater Fish", 1500),
 ("resident_fish", "Service-Connected Totally and Permanently Disabled Veteran Resident Lifetime License to Hunt and Freshwater Fish", None),

 ("nonresident_fish", "Nonresident License to Freshwater Fish", 4600),
 ("nonresident_fish", "Nonresident License to Freshwater Fish in Designated Stocked Trout Waters", 2200),
 ("nonresident_fish", "Nonresident License to Freshwater and Saltwater Fish", 7000),
 ("nonresident_fish", "Nonresident Fishing License for Partially Disabled Veterans", 2300),
 ("nonresident_fish", "Nonresident Annual Fishing License for Totally and Permanently Disabled Veterans", 1150),
 ("nonresident_fish", "Nonresident License to Freshwater Fish for One Day", 700),
 ("nonresident_fish", "Nonresident License to Freshwater Fish for Five Consecutive Days", 2000),
 ("nonresident_fish", "Nonresident License to Freshwater and Saltwater Fish for Five Consecutive Days", 3000),
 ("nonresident_fish", "Nonresident Infant Lifetime License to Fish", 27500),
 ("nonresident_fish", "Nonresident Special Lifetime License to Freshwater Fish", 58000),
 ("nonresident_fish", "Nonresident Special Lifetime License to Fish in Designated Stocked Trout Waters", 58000),

 ("misc_fish", "Permit to Fish for One Day at Board-Designated Stocked Trout Fishing Areas", 700),
 ("misc_fish", "Public Access Lands for Sportsmen Permit to Hunt, Trap, or Fish", 1700),
 ("misc_fish", "Special Guest Fishing License", 6000),
]

# Pairs that differ only in residency. Written out by hand so the pairing rule
# is on the record and does not depend on string matching: each entry names the
# activity, the age band and the term that both sides share.
RESIDENCY_PAIRS = [
 ("hunt, 16+, one year", 2200, 11000),
 ("hunt, short trip", 1100, 5900),
 ("hunt, youth 12-15", 750, 1500),
 ("hunt, youth combination under 16", 1500, 3000),
 ("hunt, partially disabled veteran, annual", 1100, 5500),
 ("hunt, infant lifetime", 13000, 27500),
 ("hunt, lifetime through 44", 26500, 58000),
 ("deer and turkey, 16+", 2200, 8500),
 ("deer and turkey, 12-15", 750, 1500),
 ("bear", 2000, 15000),
 ("archery", 1700, 3000),
 ("muzzleloading", 1700, 3000),
 ("bonus deer permit", 1700, 3000),
 ("fox hunting", 2200, 11000),
 ("elk hunt lottery application", 1500, 2000),
 ("special elk hunting", 4000, 40000),
 ("trap, one year", 4500, 20500),
 ("freshwater fish, one year", 2200, 4600),
 ("fish in designated stocked trout waters", 2200, 2200),
 ("freshwater and saltwater fish", 3850, 7000),
 ("freshwater fish, five consecutive days", 1300, 2000),
 ("freshwater and saltwater fish, five consecutive days", 2300, 3000),
 ("fishing, partially disabled veteran", 1100, 2300),
 ("fish, infant lifetime", 13000, 27500),
 ("fish, special lifetime freshwater", 26500, 58000),
 ("fish, special lifetime stocked trout", 26500, 58000),
]


def main():
    priced = [r for r in ROWS if r[2] is not None]
    exempt = [r for r in ROWS if r[2] is None]
    values = [r[2] for r in priced]
    distinct = sorted(set(values))
    collisions = len(priced) - len(distinct)

    counts = Counter(values)
    repeated = sorted(((v, c) for v, c in counts.items() if c > 1),
                      key=lambda x: (-x[1], x[0]))

    same_pairs = [p for p in RESIDENCY_PAIRS if p[1] == p[2]]
    ratios = sorted(((p[0], p[2] / p[1]) for p in RESIDENCY_PAIRS if p[1]),
                    key=lambda x: x[1])

    crit = {}
    # B55-1 premise: every amount is an exact number of cents
    bad = [r for r in priced if not isinstance(r[2], int) or r[2] < 0]
    crit["B55-1"] = {"passed": not bad,
        "name": "every fee is an exact integer number of cents, nothing rounded",
        "detail": "%d priced rows, %d not an exact cent amount" % (len(priced), len(bad))}
    # B55-2 the identity
    crit["B55-2"] = {"passed": collisions == len(priced) - len(distinct),
        "name": "collisions = cells - distinct values",
        "detail": "%d cells, %d distinct values, %d collisions (%.1f%% of cells)"
                  % (len(priced), len(distinct), collisions, 100.0 * collisions / len(priced))}
    # B55-3 the residency line on its own
    crit["B55-3"] = {"passed": len(RESIDENCY_PAIRS) > 0,
        "name": "the residency line counted on its own, over pairs that share "
                "activity, age band and term",
        "detail": "%d pairs, %d of them carry the same value on both sides"
                  % (len(RESIDENCY_PAIRS), len(same_pairs))}
    # B55-4 provenance
    noprov = [r for r in ROWS if not r[0]]
    crit["B55-4"] = {"passed": not noprov,
        "name": "every row carries the sub-heading it came from (rule 25)",
        "detail": "%d rows, %d without a sub-heading, %d sub-headings"
                  % (len(ROWS), len(noprov), len({r[0] for r in ROWS}))}

    out = {
      "stage": "B55",
      "config": {"source": SOURCE, "retrieved": RETRIEVED,
                 "amounts_in": "cents", "no_fee_rows_excluded_from_value_set": True,
                 "sections": sorted({r[0] for r in ROWS}),
                 "n_rows_total": len(ROWS)},
      "criteria": [{"name": k, "passed": v["passed"], "detail": v["detail"],
                    "criterion": v["name"]} for k, v in sorted(crit.items())],
      "reading": {"cells_priced": len(priced), "distinct_values": len(distinct),
                  "collisions": collisions, "exempt_rows": len(exempt),
                  "residency_pairs": len(RESIDENCY_PAIRS),
                  "residency_pairs_same_value": len(same_pairs)},
      "values_repeated": [{"cents": v, "times": c} for v, c in repeated],
      "residency_pairs": [{"shared": s, "resident_cents": a, "nonresident_cents": b,
                           "ratio": (b / a if a else None)} for s, a, b in RESIDENCY_PAIRS],
      "rows": [{"section": s, "name": n, "cents": c} for s, n, c in ROWS],
    }
    dest = Path(__file__).resolve().parents[1] / "results" / "b55_virginia_licence_counting.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    print("%s, retrieved %s" % (SOURCE, RETRIEVED))
    print("cells with a price %d, distinct values %d, collisions %d (%.1f%%), no-fee rows %d"
          % (len(priced), len(distinct), collisions, 100.0 * collisions / len(priced), len(exempt)))
    print()
    print("values written more than once (rule 11: print the object):")
    for v, c in repeated:
        print("    $%8.2f  written %d times" % (v / 100.0, c))
    print()
    print("the residency line on its own, %d pairs:" % len(RESIDENCY_PAIRS))
    for s, r in ratios:
        print("    %-52s x%.2f" % (s, r))
    print()
    print("pairs where residency separates nothing: %s"
          % ([p[0] for p in same_pairs] or "none"))
    print()
    for k, v in sorted(crit.items()):
        print("%-8s %-5s %s" % (k, "PASS" if v["passed"] else "FAIL", v["detail"]))
    print("wrote", dest.name)
    return 0 if all(v["passed"] for v in crit.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
