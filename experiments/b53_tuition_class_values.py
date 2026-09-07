"""B53: the counting law where the collisions are exact.

A published tuition schedule writes three classes -- in-district, in-state and
out-of-state -- and produces however many distinct dollar figures those three
carry. That is the counting law's object: a procedure partitions a set and the
number of values it produces is the number of DISTINCT class values it wrote,
not the number of classes it drew.

Why this corpus and not another. Every collision the tariff corpus reports is
bounded above by that survey rounding charges to two decimals, so it is an upper
bound at the published resolution rather than a count. Tuition is published in
whole dollars. No rounding turns two different figures into one, so a collision
here is a collision, and B53-3 checks that premise rather than assuming it.

The known answer this file can be caught on. A private institution has no
in-state and out-of-state distinction, so its three classes must carry one
figure. That answer comes from the institution's control code, which is
collected separately and not derived here, so B53-1 is a check and not a
restatement.

Criteria:

  B53-1  known answer: every private institution writes one value across the
         three classes. Institutions that do not are named, not counted.
  B53-2  print the object: how many institutions write 3 -> 1, 3 -> 2 and
         3 -> 3, split by control and by level of study.
  B53-3  the premise of exactness: every figure read is a whole dollar amount.
  B53-4  coverage, state by state, including the states that return nothing.

Missing values arrive as negative codes. A negative is an absence, not a fee of
minus two dollars, and rows carrying one are dropped and counted rather than
silently read.

Source: the Urban Institute Education Data API over IPEDS, public and keyless.
Responses are cached under data/cache/ipeds/ per endpoint and state, so an
interrupted run resumes and a rerun goes to the network zero times.

Run:

    python experiments\\b53_tuition_class_values.py
    python experiments\\b53_tuition_class_values.py --year 2019
    python experiments\\b53_tuition_class_values.py --refresh
"""

from __future__ import annotations

import collections
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "ipeds"
API = "https://educationdata.urban.org/api/v1/college-university/ipeds/"
UA = "monetary-topology/b53 (research; contact via repository)"
YEAR = 2020

# The three classes the schedule writes, in the source's own coding.
CLASSES = {2: "in-district", 3: "in-state", 4: "out-of-state"}
LEVELS = {1: "undergraduate", 2: "graduate"}
CONTROL = {1: "public", 2: "private nonprofit", 3: "private for-profit"}
PRIVATE = (2, 3)

STATES = [1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22,
          23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
          40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 53, 54, 55, 56,
          60, 66, 69, 72, 78]
NAMES = {1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT",
         10: "DE", 11: "DC", 12: "FL", 13: "GA", 15: "HI", 16: "ID", 17: "IL",
         18: "IN", 19: "IA", 20: "KS", 21: "KY", 22: "LA", 23: "ME", 24: "MD",
         25: "MA", 26: "MI", 27: "MN", 28: "MS", 29: "MO", 30: "MT", 31: "NE",
         32: "NV", 33: "NH", 34: "NJ", 35: "NM", 36: "NY", 37: "NC", 38: "ND",
         39: "OH", 40: "OK", 41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD",
         47: "TN", 48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV",
         55: "WI", 56: "WY", 60: "AS", 66: "GU", 69: "MP", 72: "PR", 78: "VI"}
OUT = ROOT / "results" / "b53_tuition_class_values.json"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(endpoint: str, year: int, fips: int, refresh: bool) -> list:
    """One state, one endpoint, all pages, cached as a single file."""
    path = CACHE / ("%s__%d__fips-%02d.json" % (endpoint, year, fips))
    if path.exists() and not refresh:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit("cached file is not valid JSON: %s (%s)"
                             % (path, exc))
        if not isinstance(data, list):
            raise SystemExit("cached file is not a list: %s" % path)
        return data
    url = "%s%s/%d/?fips=%d&format=json" % (API, endpoint, year, fips)
    rows, guard = [], 0
    while url and guard < 200:
        guard += 1
        try:
            page = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError) as exc:
            raise SystemExit(
                "could not reach the education data endpoint and no usable "
                "cache is on disk\n  url: %s\n  error: %s" % (url, exc))
        rows += page.get("results", [])
        url = page.get("next")
        if url:
            time.sleep(0.2)
    CACHE.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(rows, indent=1, sort_keys=True),
                    encoding="utf-8", newline="\n")
    os.replace(part, path)
    return rows


def main() -> int:
    argv = sys.argv[1:]
    refresh = "--refresh" in argv
    year = YEAR
    if "--year" in argv:
        year = int(argv[argv.index("--year") + 1])

    rec: dict = {
        "stage": "B53",
        "config": {
            "endpoint": API, "year": year, "states_requested": len(STATES),
            "classes": {str(k): v for k, v in CLASSES.items()},
            "levels": {str(k): v for k, v in LEVELS.items()},
            "control": {str(k): v for k, v in CONTROL.items()},
            "field": "tuition_fees_ft",
            "missing": "negative codes are absences and are dropped, not read "
                       "as fees",
            "refresh": refresh,
            "cache_dir": str(CACHE.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    print("B53-4  coverage, state by state (a state returning nothing is named)")
    print("  %-4s %8s %10s %10s %10s" % ("st", "tuition", "directory",
                                         "schools", "dropped"))
    control_of, schedules, coverage = {}, {}, {}
    total_dropped = 0
    for fips in STATES:
        dirrows = fetch("directory", year, fips, refresh)
        turows = fetch("academic-year-tuition", year, fips, refresh)
        for d in dirrows:
            if d.get("unitid") is not None:
                # The field is inst_control. Asking for "control" returns None
                # for every row, every institution then reads as unknown, and
                # B53-1 finds no private schedule to check. That is the shape
                # this file has to be able to report rather than pass through:
                # a criterion whose object is empty has nothing to say.
                control_of[d["unitid"]] = d.get("inst_control")
        dropped = 0
        seen = set()
        for r in turows:
            uid, lvl, cls = r.get("unitid"), r.get("level_of_study"), \
                r.get("tuition_type")
            fee = r.get("tuition_fees_ft")
            if uid is None or lvl not in LEVELS or cls not in CLASSES:
                continue
            seen.add(uid)
            if fee is None or (isinstance(fee, (int, float)) and fee < 0):
                dropped += 1
                continue
            schedules.setdefault((uid, lvl), {})[cls] = fee
        total_dropped += dropped
        coverage[NAMES[fips]] = {"tuition_rows": len(turows),
                                 "directory_rows": len(dirrows),
                                 "schools": len(seen), "dropped": dropped}
        print("  %-4s %8d %10d %10d %10d"
              % (NAMES[fips], len(turows), len(dirrows), len(seen), dropped))
    rec["coverage"] = coverage
    rec["dropped_negative"] = total_dropped
    empty = [s for s, c in coverage.items() if c["tuition_rows"] == 0]
    print("  states returning no tuition rows: %s" % (", ".join(empty) or "none"))
    print("  rows dropped for a negative code: %d" % total_dropped)

    # only schedules that wrote all three classes
    full = {k: v for k, v in schedules.items() if len(v) == len(CLASSES)}
    rec["schedules"] = {"with_all_three_classes": len(full),
                        "with_fewer": len(schedules) - len(full)}

    # ---- B53-3: the premise of exactness -----------------------------------
    nonint = [(uid, lvl, c, f) for (uid, lvl), v in full.items()
              for c, f in v.items() if float(f) != int(f)]
    rec["non_integer_fees"] = nonint[:40]
    print("\nB53-3  every figure a whole dollar amount")
    print("  schedules with all three classes: %d; non-integer figures: %d"
          % (len(full), len(nonint)))

    # ---- B53-2: the shapes -------------------------------------------------
    shape = collections.Counter()
    by_control_level = collections.defaultdict(collections.Counter)
    for (uid, lvl), v in full.items():
        n = len(set(v.values()))
        ctrl = control_of.get(uid)
        shape[n] += 1
        by_control_level[(ctrl, lvl)][n] += 1
    rec["shapes"] = {"overall": {str(k): v for k, v in sorted(shape.items())},
                     "by_control_and_level": {
                         "%s|%s" % (CONTROL.get(c, "unknown"), LEVELS.get(l, "?")):
                         {str(k): v for k, v in sorted(cnt.items())}
                         for (c, l), cnt in sorted(
                             by_control_level.items(),
                             key=lambda kv: (kv[0][0] or 9, kv[0][1]))}}
    print("\nB53-2  three classes written, how many distinct values produced")
    print("  overall: " + ", ".join("3 -> %d : %d" % (k, shape[k])
                                    for k in sorted(shape)))
    print("  %-22s %-14s %7s %7s %7s" % ("control", "level", "3->1", "3->2",
                                         "3->3"))
    for (c, l), cnt in sorted(by_control_level.items(),
                              key=lambda kv: (kv[0][0] or 9, kv[0][1])):
        print("  %-22s %-14s %7d %7d %7d"
              % (CONTROL.get(c, "unknown"), LEVELS.get(l, "?"),
                 cnt[1], cnt[2], cnt[3]))

    # ---- B53-1: the known answer -------------------------------------------
    offenders = []
    private_total = 0
    for (uid, lvl), v in full.items():
        if control_of.get(uid) in PRIVATE:
            private_total += 1
            if len(set(v.values())) > 1:
                offenders.append({"unitid": uid, "level": LEVELS[lvl],
                                  "control": CONTROL[control_of[uid]],
                                  "values": {CLASSES[c]: v[c] for c in sorted(v)}})
    # How well the two endpoints joined, printed rather than assumed. A
    # criterion resting on a join is only as good as the join.
    tuition_units = {uid for (uid, _lvl) in full}
    joined = {u for u in tuition_units if control_of.get(u) in CONTROL}
    rec["join"] = {
        "institutions_in_tuition": len(tuition_units),
        "matched_to_a_control_code": len(joined),
        "unmatched": len(tuition_units) - len(joined),
    }
    rec["private_with_more_than_one_value"] = offenders
    rec["private_schedules"] = private_total
    print("  join against the directory endpoint: %d of %d institutions carry "
          "a control code" % (len(joined), len(tuition_units)))
    print("\nB53-1  known answer: a private institution has no in-state and "
          "out-of-state distinction")
    print("  private schedules with all three classes: %d" % private_total)
    print("  of those, writing more than one value: %d" % len(offenders))
    for o in offenders[:25]:
        print("     %-8s %-13s %-20s %s"
              % (o["unitid"], o["level"], o["control"],
                 ", ".join("%s %s" % (k, v) for k, v in o["values"].items())))
    if len(offenders) > 25:
        print("     ... %d more, all in the record" % (len(offenders) - 25))

    rec["criteria"] = {
        "B53-1": {
            "kind": "known_answer",
            "name": "every private institution writes one value across the "
                    "three classes; the control code comes from a separate "
                    "endpoint, so this is a check and not a restatement. Three "
                    "states: no private schedule identified leaves nothing to "
                    "judge, none writing more than one value confirms it, any "
                    "writing more than one refutes it",
            "passed": None if private_total == 0 else (len(offenders) == 0),
            "state": ("no object: no private schedule was identified, so the "
                      "join or the control field is wrong and this criterion "
                      "has nothing to check")
                     if private_total == 0
                     else ("holds" if not offenders else "refuted"),
            "detail": "%d private schedules, %d write more than one value; "
                      "%d of %d institutions matched to a control code"
                      % (private_total, len(offenders), len(joined),
                         len(tuition_units)),
        },
        "B53-2": {
            "kind": "own_reading",
            "name": "how many schedules write 3 -> 1, 3 -> 2 and 3 -> 3, split "
                    "by control and level, printed with no line on it",
            "passed": len(full) > 0,
            "detail": ", ".join("3 -> %d : %d" % (k, shape[k])
                                for k in sorted(shape)),
        },
        "B53-3": {
            "kind": "premise",
            "name": "the premise that makes these collisions exact rather than "
                    "an upper bound: every figure is a whole dollar amount",
            "passed": len(nonint) == 0,
            "detail": "%d non-integer figures over %d schedules"
                      % (len(nonint), len(full)),
        },
        "B53-4": {
            "kind": "bookkeeping",
            "name": "coverage state by state, states returning nothing named "
                    "rather than absent",
            "passed": len(coverage) == len(STATES),
            "detail": "%d states requested, %d returned rows, empty: %s; %d "
                      "rows dropped for a negative code"
                      % (len(STATES), len(STATES) - len(empty),
                         ", ".join(empty) or "none", total_dropped),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\nwritten: %s" % OUT)
    for k in sorted(rec["criteria"]):
        c = rec["criteria"][k]
        mark = "PASS" if c["passed"] is True else (
            "FAIL" if c["passed"] is False else "N/A ")
        print("  %-7s %-4s %s" % (k, mark, c["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
