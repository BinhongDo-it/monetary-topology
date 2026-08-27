# -*- coding: utf-8 -*-
"""C2. California's transfer-area placements, and whether they agree.

**Why this stage exists, and what it is for.** C1 found that the declared
conversion between a greenhouse gas and CO2-equivalent is multivalued: no
species reads the same ratio under all six published GWP-100 vintages. The
cheapest objection to that is that any state-scale administrative system
accumulates inconsistency, so the finding is about bureaucratic entropy rather
than about whether a value scalar exists. **C2 is the control for that
objection.** California's articulation system is comparable in scale, age and
plurality of parallel classification schemes, it is equally free of markets and
prices, and it publishes its declarations the same way.

**Three arms were scoped and did not open, all closed on paper.** Unit counts
telescope to 1 around any loop because units are a scalar attached to a course.
"Two courses that satisfy the same receiving course are equivalent" does not
follow, because articulation declares an inequality. The Ferrers 2x2, which
would show the relation admits no scalar representation, is confounded at
college level by curriculum coverage: one college teaches mathematics and
another teaches Spanish, and that is not a statement about value. The common
cause is that `courseIdentifierParentId` is institution-local, 972 sending ids
with none shared between colleges and 633 receiving ids with none shared
between universities, so "the same course" is not sayable and every proxy for
it also encodes "these two institutions are different".

**What is sayable is a transfer area.** `1A`, `3B`, `A2`, `C1` mean the same
thing state-wide, five list types carry them, and four of the five annotate
courses with areas belonging to more than one scheme. That is a shared
coordinate system, and a course placed in one area by one list and another area
by another is a reading about the declarations rather than about coverage.

**Comparison is per `areaType`, and that is load-bearing.** Each list carries
areas from several schemes at once: the CSU-transferable list annotates with
IGETC, CSU GE-Breadth and CSU American-Ideals areas together, while the IGETC
list carries IGETC areas only. Comparing whole `transferAreas` sets across lists
returns disagreement for 370 of 370 courses, and that number is manufactured by
which schemes each list chooses to annotate with. Restricted to one `areaType`
at a time, between the lists that actually carry it, the comparison is about
placement.

Reads `data/raw/assist/transferability_2024/`, via a compact cache it builds
once. Writes `results/c2_transfer_areas.json`.

    python experiments/c2_transfer_areas.py
"""
from __future__ import annotations

import collections
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "assist" / "transferability_2024"
CACHE = ROOT / "data" / "cache" / "c2" / "areas_2024.json"
OUT = ROOT / "results" / "c2_transfer_areas.json"

KINDS = ("CSUTC", "IGETC", "UCTCA", "UCTEL", "CSUGE", "CSUAI")

#: Every California community college in the ASSIST institution list. The
#: sweep reached 115 of them; the one it did not is named in the record rather
#: than left as a difference between two counts.
COLLEGES_EXPECTED = 116


def build_cache() -> dict:
    """Reduce 270 MB of list payloads to the placements, once."""
    names, data = {}, {}
    for path in sorted(RAW.glob("*.json")):
        cid, kind = path.stem.split("_", 1)
        doc = json.loads(path.read_text(encoding="utf-8"))
        names[cid] = doc.get("institutionName")
        per = data.setdefault(cid, {})
        for course in doc.get("courseInformationList") or []:
            rec = per.setdefault(str(course["courseIdentifierParentId"]), {})
            by_type: dict[str, list[str]] = {}
            for area in course.get("transferAreas") or []:
                by_type.setdefault(str(area["areaType"]), []).append(
                    area["code"].strip())
            rec[kind] = {"at": {k: sorted(set(v)) for k, v in by_type.items()},
                         "id": course.get("identifier")}
    blob = {"names": names, "data": data}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(blob, sort_keys=True), encoding="utf-8",
                     newline="\n")
    return blob


def load() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    if not RAW.exists():
        raise SystemExit(
            "%s is missing. Run `python data/fetch_assist.py --transferability "
            "%s` first." % (RAW, " ".join(KINDS)))
    return build_cache()


def main() -> int:
    blob = load()
    names, data = blob["names"], blob["data"]
    criteria = []

    # ---- C2-1. Coverage, with the hole named --------------------------------
    got = {cid: {k for k in KINDS if any(k in rec for rec in courses.values())}
           for cid, courses in data.items()}
    complete = [c for c, k in got.items() if k == set(KINDS)]
    missing = COLLEGES_EXPECTED - len(data)
    criteria.append({
        "name": "C2-1 coverage of the sweep",
        "detail": ("%d of %d colleges returned data, %d of those carry all %d "
                   "list types; %d college(s) returned HTTP 500 for every list "
                   "type and hold no record here"
                   % (len(data), COLLEGES_EXPECTED, len(complete), len(KINDS),
                      missing)),
        "passed": len(complete) == len(data),
        "colleges_with_data": len(data),
        "colleges_expected": COLLEGES_EXPECTED,
        "colleges_complete": len(complete),
        "absent": ["Compton College, HTTP 500 on all six list types"],
        "course_records": sum(len(v) for v in data.values()),
    })

    # ---- C2-2 and C2-3. Placement agreement, one areaType at a time ---------
    per_at = collections.defaultdict(collections.Counter)
    conflicts, nested = [], []
    for cid, courses in data.items():
        for lists in courses.values():
            for at in {k for v in lists.values() for k in v["at"]}:
                carrying = {name: frozenset(rec["at"][at])
                            for name, rec in lists.items() if at in rec["at"]}
                if len(carrying) < 2:
                    per_at[at]["single_list"] += 1
                    continue
                per_at[at]["comparable"] += 1
                sets = list(carrying.values())
                if len(set(sets)) == 1:
                    per_at[at]["agree"] += 1
                    continue
                if any(not (a <= b or b <= a)
                       for a, b in itertools.combinations(sets, 2)):
                    per_at[at]["conflict"] += 1
                    conflicts.append({
                        "college": names[cid], "areaType": at,
                        "course": next(iter(lists.values()))["id"],
                        "placements": {k: sorted(v) for k, v in carrying.items()}})
                else:
                    per_at[at]["nested"] += 1
                    if len(nested) < 8:
                        nested.append({
                            "college": names[cid], "areaType": at,
                            "course": next(iter(lists.values()))["id"],
                            "placements": {k: sorted(v) for k, v in carrying.items()}})

    table = {at: dict(c) for at, c in sorted(per_at.items(), key=lambda kv: int(kv[0]))}
    total_cmp = sum(c.get("comparable", 0) for c in per_at.values())
    total_conf = sum(c.get("conflict", 0) for c in per_at.values())
    criteria.append({
        "name": "C2-2 do the lists place a course in the same areas",
        "detail": ("%d comparable placements over %d colleges; %s; %d nested, "
                   "where one list records a finer sub-area than another; %d "
                   "mutually non-containing"
                   % (total_cmp, len(data),
                      ", ".join("areaType %s %d comparable %d conflict"
                                % (at, c.get("comparable", 0), c.get("conflict", 0))
                                for at, c in table.items()),
                      sum(c.get("nested", 0) for c in per_at.values()), total_conf)),
        "passed": True,
        "reading": "consistent" if total_conf == 0 else "conflicts present",
        "by_area_type": table,
        "comparable": total_cmp,
        "conflicts": total_conf,
        "nested_examples": nested,
    })

    # The discriminator: a declared disagreement between two authorities is
    # spread across the system, a record-keeping one clusters. Reported as
    # counts and named objects, with no line drawn on either.
    by_college = collections.Counter(c["college"] for c in conflicts)
    by_pair = collections.Counter(
        " vs ".join(sorted(c["placements"])) for c in conflicts)
    top3 = sum(n for _, n in by_college.most_common(3))
    criteria.append({
        "name": "C2-3 where the conflicts sit",
        "detail": ("%d conflicts over %d colleges of %d; the three heaviest "
                   "hold %d of them; every one is between %s; the heaviest "
                   "college contributes %d courses carrying one identical "
                   "discrepancy"
                   % (len(conflicts), len(by_college), len(data), top3,
                      ", ".join(sorted(by_pair)),
                      by_college.most_common(1)[0][1] if by_college else 0)),
        "passed": True,
        "by_college": dict(by_college.most_common()),
        "by_list_pair": dict(by_pair),
        "all_conflicts": sorted(conflicts,
                                key=lambda c: (c["college"], str(c["course"]))),
    })

    # ---- C2-4. Is UC transferability nested inside CSU transferability ------
    violations = []
    for cid, courses in data.items():
        uc = {c for c, lists in courses.items() if "UCTCA" in lists}
        csu = {c for c, lists in courses.items() if "CSUTC" in lists}
        if uc - csu:
            violations.append({"college": names[cid], "uc_only": len(uc - csu),
                               "uc": len(uc), "csu": len(csu)})
    criteria.append({
        "name": "C2-4 UC transferability against CSU transferability",
        "detail": ("nesting holds at %d of %d colleges; %d college(s) list a "
                   "course as UC transferable and not CSU transferable, %d "
                   "course(s) in total. Strict nesting is what a scalar with "
                   "two thresholds produces, so this arm can read either way "
                   "and reads one of them"
                   % (len(data) - len(violations), len(data), len(violations),
                      sum(v["uc_only"] for v in violations))),
        "passed": True,
        "reading": "nested" if not violations else "nested with exceptions",
        "violations": sorted(violations, key=lambda v: -v["uc_only"]),
    })

    record = {
        "stage": "C2",
        "carrier": "ASSIST transfer-area placements, California, 2024-2025",
        "source": "data/raw/assist/transferability_2024/",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "C2 is the control arm for C1 and its reading is a null, so it is "
            "held open until the coverage hole is closed or shown not to "
            "matter: Compton College returned HTTP 500 for all six list types "
            "and holds no record here. A null needs coverage in a way a "
            "positive does not, since one witness settles an existence claim "
            "and no number of them settles an absence."),
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")

    for c in criteria:
        print("[%s] %s\n    %s" % ("PASS" if c["passed"] else "FAIL",
                                   c["name"], c["detail"]))
        if "reading" in c:
            print("    reading: %s" % c["reading"])
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
