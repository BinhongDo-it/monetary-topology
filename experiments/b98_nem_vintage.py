"""B98 arm E: the class index, on a second electricity carrier.

Arm A to D run on one ISO's nodal prices, where every participant at a node
faces the same price. That is what `m = 1` means and it is why nothing in those
arms reaches the question the framework is actually about: what two different
parties are charged at one position. This arm answers it on a carrier where the
two parties are published separately.

Two net metering vintages in California. One exported kilowatt hour, one meter,
one hour, and two prices: a customer whose interconnection application landed on
or before 2023-04-14 is credited against the retail time-of-use schedule, and one
who came later is credited against the Avoided Cost Calculator's table, which
carries a value for every combination of month, hour and weekday or weekend. The
split is set by a date, it cannot be undone, and both schedules are filed.

**The rival to score against is not the naive one.** A single scalar on positions,
with everyone paying it, dies the moment two schedules are filed, and killing it
buys nothing. The rival with content is a potential plus a class constant,

    P(a, j) = phi(j) + psi(a),

which says the class difference is a pure level shift and the shape of price over
positions does not depend on the class. That is the empirical form of the rule
that a published conversion between two prices makes them one price: here nothing
is published, and whether the data happen to be a constant apart is the question.

**The framework does not predict either way on this arm and says so.** It permits
the shape to depend on the class; it does not require it. What is registered is
the rival's point prediction and the reading that settles it.

**And that is exactly why no criterion here is typed `rival`.** A rival criterion
passes when the rival is wrong and fails when the rival is right, and a rival that
is right is only a loss when this framework was right about the same cell in the
other direction. Here it never is: the framework permits both outcomes, so the
losing cell is unreachable, and a rival criterion whose losing cell is unreachable
either cannot fail or has to record a cell the grid rule forbids. The rival's
position is stated in the detail and settled by the reading; it is not given a
criterion of its own.

Positions that share a NEM-2 price are read off the data rather than imported
from a schedule: two positions are in one block when their NEM-2 credit is equal
to within its own tick. Inside a block the square is `-(P3(i) - P3(j))` by
construction and carries nothing about class; the reading lives on the pairs that
cross blocks. The two groups are reported apart and never summed, because summing
them makes the arm one that cannot fail.

Input: one joined table, one row per (utility, month, hour, daytype), with the
two credits. The join is a preprocessing step and E1 is what checks it.

Run:
    python experiments/b98_nem_vintage.py --probe <any csv>
    python experiments/b98_nem_vintage.py <joined csv>
    python experiments/b98_nem_vintage.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b98_nem_vintage.json"

# A credit per kilowatt hour. A table in dollars per megawatt hour lands two
# orders out and E1 is what says so rather than silently rescaling.
#: What this check is for: telling a table in $/kWh from one in $/MWh, which is
#: a factor of a thousand. It was first written as "every value inside (0, 2)",
#: and that is a line drawn where the arm E data happened to stop rather than
#: where the two units separate. Arm F's earlier batch reaches $2.52/kWh on
#: October evenings, which is a real price, and the check failed the whole run on
#: three rows. A megawatt-hour table would put its *middle* in the tens, so the
#: median is what separates the units and a single high cell does not.
#: `MAX_ANY` is two orders of magnitude above the highest published cell and an
#: order below where $/MWh begins; it catches a unit error without ruling on how
#: high an avoided cost may go.
PLAUSIBLE_MEDIAN = (0.0, 2.0)
MAX_ANY = 10.0

# Returned when no decimal step divides every value. It is not a grid; a reading
# whose floor rests on it has no floor, and E2 says so rather than using it.
FALLBACK_TICK = 10.0 ** -8

WANT = {
    "utility": (r"utilit", r"\biou\b"),
    "month": (r"month",),
    "hour": (r"hour",),
    "daytype": (r"daytype", r"day.?type", r"weekday"),
    "p_nem2": (r"nem.?2", r"legacy"),
    "p_nem3": (r"nem.?3", r"\bacc\b", r"net.?billing"),
}


def _norm(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def infer_tick(values):
    """The largest decimal step every value is an integer multiple of.

    Checked value by value rather than declared, which is the discipline a
    published grid gets: a grid asserted from the file's look rather than from
    its values is how a floor ends up set below what the publisher prints.
    """
    for places in range(0, 9):
        tick = 10.0 ** (-places)
        if all(abs(v / tick - round(v / tick)) < 1e-6 for v in values):
            return tick
    return FALLBACK_TICK


def find_header(path, limit=40):
    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        for index, row in enumerate(csv.reader(handle)):
            if index >= limit:
                break
            joined = " ".join(_norm(c) for c in row)
            if "hour" in joined and "month" in joined:
                return index, [c.strip() for c in row]
    return None, []


def pick_columns(header):
    picked, trouble = {}, []
    for key, patterns in WANT.items():
        hits = [i for i, cell in enumerate(header)
                if any(re.search(p, _norm(cell)) for p in patterns)]
        if not hits:
            trouble.append("no column matches " + key)
        else:
            if len(hits) > 1:
                trouble.append(key + " matches " + str(len(hits)) + " columns: "
                               + ", ".join(header[i] for i in hits))
            picked[key] = hits[0]
    return picked, trouble


def read_rows(path):
    start, header = find_header(path)
    if start is None:
        return [], [], ["no header row naming both a month and an hour column"]
    picked, trouble = pick_columns(header)
    if len(picked) < len(WANT):
        return [], header, trouble
    rows, seen = [], set()
    dupes = 0
    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        for index, raw in enumerate(csv.reader(handle)):
            if index <= start or not raw or len(raw) <= max(picked.values()):
                continue
            try:
                row = {
                    "utility": raw[picked["utility"]].strip(),
                    "month": int(float(raw[picked["month"]])),
                    "hour": int(float(raw[picked["hour"]])),
                    "daytype": raw[picked["daytype"]].strip().lower(),
                    "p2": float(raw[picked["p_nem2"]]),
                    "p3": float(raw[picked["p_nem3"]]),
                }
            except (ValueError, IndexError):
                continue
            key = (row["utility"], row["month"], row["hour"], row["daytype"])
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            row["key"] = key
            rows.append(row)
    if dupes:
        trouble.append(str(dupes) + " rows repeat a position key")
    return rows, header, trouble


def crit_join(rows, header, trouble):
    """E1: the two schedules meet on one position key, in one unit."""
    if trouble:
        return False, "; ".join(trouble)[:400], {}
    if not rows:
        return False, "the header was found and no row survived parsing", {}
    lo, hi = PLAUSIBLE_MEDIAN
    meds = []
    for col in ("p2", "p3"):
        xs = sorted(r[col] for r in rows)
        meds.append(xs[len(xs) // 2])
    off = [r for r in rows
           if r["p2"] < 0 or r["p3"] < 0
           or r["p2"] > MAX_ANY or r["p3"] > MAX_ANY]
    ok = all(lo <= m <= hi for m in meds) and not off
    hi_cell = max(max(r["p2"], r["p3"]) for r in rows)
    if ok:
        detail = (str(len(rows)) + " positions joined on (utility, month, hour, "
                  "daytype); the two medians are " + format(meds[0], ".5f")
                  + " and " + format(meds[1], ".5f") + " per kilowatt hour, and "
                  "the highest single cell is " + format(hi_cell, ".5f")
                  + ". **The unit is read off the middle of each column, not off "
                  "its extreme**: a table in dollars per megawatt hour puts its "
                  "median in the tens, while a high avoided cost in the right "
                  "unit is a price and not a fault")
    elif off:
        detail = (str(len(off)) + " rows carry a credit above "
                  + format(MAX_ANY, ".1f") + " or below zero per kilowatt hour, "
                  "which is what a table in the wrong unit looks like. First: "
                  + ", ".join(str(r["key"]) for r in off[:5]))
    else:
        detail = ("the column medians are " + format(meds[0], ".5f") + " and "
                  + format(meds[1], ".5f") + ", outside "
                  + str(PLAUSIBLE_MEDIAN) + " per kilowatt hour")
    return ok, detail, {"positions": len(rows), "out_of_range": len(off),
                        "median_p2": meds[0], "median_p3": meds[1],
                        "max_cell": hi_cell}


def ticks(rows):
    t2 = infer_tick([r["p2"] for r in rows])
    t3 = infer_tick([r["p3"] for r in rows])
    return t2, t3


def crit_level_shift(rows):
    """E2: the rival's point prediction, that the two differ by a constant.

    The verdict is structural. It asks whether a determinate reading was
    produced on at least two positions with the floor left where the values put
    it. The dispersion itself is printed and no line is drawn on it.
    """
    if len(rows) < 2:
        return None, ("fewer than two positions, so there is no constant to test. "
                      "No object, so this lands in the third cell and is not a "
                      "reading that came out false"), {}
    t2, t3 = ticks(rows)
    if min(t2, t3) <= FALLBACK_TICK:
        return None, ("no decimal grid divides every value on one side, so the "
                      "floor this reading is measured against does not exist, and "
                      "this reading was not evaluated. Ticks " + format(t2, ".0e")
                      + " and " + format(t3, ".0e")
                      + "; the grid is checked value by value and not declared"), {}
    floor = t2 + t3
    gaps = [r["p2"] - r["p3"] for r in rows]
    spread = max(gaps) - min(gaps)
    cell = ("branch one, a pure level shift: the difference is constant to within "
            "the floor the two published grids allow"
            if spread <= floor else
            "branch two, not a level shift: the difference moves with the position "
            "by more than the two grids allow")
    detail = (cell + ". The difference runs " + format(min(gaps), ".5f") + " to "
              + format(max(gaps), ".5f") + ", a spread of " + format(spread, ".5f")
              + " against a floor of " + format(floor, ".5f") + " (ticks "
              + format(t2, ".0e") + " and " + format(t3, ".0e")
              + ", read value by value), which is "
              + format(spread / floor, ".1f") + " times it. **The floor is the two "
              "publishers' own resolution and no threshold is drawn on the spread; "
              "the reading is the branch named above.**")
    return True, detail, {"tick_nem2": t2, "tick_nem3": t3, "floor": floor,
                          "min_gap": min(gaps), "max_gap": max(gaps),
                          "spread": spread}


def blocks_of(rows, tick2):
    """Positions sharing a NEM-2 credit, read off the data not off a schedule."""
    out = {}
    for r in rows:
        out.setdefault((r["utility"], round(r["p2"] / tick2)), []).append(r)
    return out


def crit_square(rows):
    """E3: the square, within a NEM-2 block and across blocks, reported apart."""
    if len(rows) < 2:
        return None, ("fewer than two positions, so there is no pair and no "
                      "object; this lands in the third cell"), {}
    t2, t3 = ticks(rows)
    floor = 2.0 * t2 + 2.0 * t3
    groups = blocks_of(rows, t2)
    within, across = [], []
    for a, b in itertools.combinations(rows, 2):
        if a["utility"] != b["utility"]:
            continue
        sq = (a["p2"] - b["p2"]) - (a["p3"] - b["p3"])
        same = round(a["p2"] / t2) == round(b["p2"] / t2)
        (within if same else across).append(abs(sq))
    if not within or not across:
        return None, ("only one of the two pair groups is populated: within "
                      + str(len(within)) + ", across " + str(len(across))
                      + ", so the two cannot be reported apart and there is no "
                      "object to read; this lands in the third cell"), {}
    def _say(name, xs):
        over = sum(1 for x in xs if x > floor)
        return (name + " " + str(len(xs)) + " pairs, median "
                + format(sorted(xs)[len(xs) // 2], ".5f") + ", max "
                + format(max(xs), ".5f") + ", " + str(over) + " above the floor "
                + format(floor, ".5f"))
    across_over = sum(1 for x in across if x > floor)
    cell = ("branch one, the shape depends on the class: the crossing pairs put "
            "the square above the floor"
            if across_over else
            "branch two, a pure level shift: the crossing pairs leave the square "
            "inside the floor, so one function of position plus a class constant "
            "covers both vintages")
    detail = (cell + ". " + _say("Crossing blocks:", across) + ". "
              + _say("Inside one block:", within)
              + ". **The two groups are never summed.** " + ARM["coarse"]
              + " The granularity behind the split is reported again as counts "
              "by the fourth criterion.")
    return True, detail, {"floor": floor, "within_pairs": len(within),
                          "across_pairs": len(across),
                          "across_above_floor": across_over,
                          "within_above_floor": sum(1 for x in within if x > floor),
                          "blocks": len(groups)}


def crit_granularity(rows):
    """E4: how many distinct values each side takes, printed before any reading."""
    if not rows:
        return None, ("no position to count, so there is no object; this lands in "
                      "the third cell"), {}
    t2, t3 = ticks(rows)
    n2 = len({(r["utility"], round(r["p2"] / t2)) for r in rows})
    n3 = len({(r["utility"], round(r["p3"] / t3)) for r in rows})
    ok = n2 > 1 and n3 > 1
    detail = (ARM["a"] + " takes " + str(n2) + " distinct values across "
              + str(len(rows)) + " positions and " + ARM["b"] + " takes "
              + str(n3) + ". **The coarser side caps what a square can resolve**, "
              "so the independent crossing pairs are bounded by that count and "
              "not by the position count."
              + ("" if ok else " **One side takes a single value, so the square "
                 "has no object and this run lands in its third cell.**"))
    return ok, detail, {"distinct_nem2": n2, "distinct_nem3": n3,
                        "positions": len(rows)}


#: What the two columns are called, per arm. Arm E puts a NEM-2 price beside a
#: NEM-3 price; arm F puts two NEM-3 batches beside each other. The criteria are
#: the same four questions either way, and only the names of the two classes and
#: the prefix change, so the arms share this code rather than a copy of it.
ARMS = {
    "E": {"prefix": "B98-E", "a": "the NEM-2 credit", "b": "the NEM-3 credit",
          "coarse": "Inside one block the NEM-2 credit is equal by construction, "
                    "so the square there is just the NEM-3 difference and "
                    "carries nothing about class; it is printed because the "
                    "granularity it reports belongs on the record."},
    "F": {"prefix": "B98-F", "a": "the earlier batch", "b": "the later batch",
          "coarse": "Both sides move here, so a within-block pair is one where "
                    "the earlier batch happens to repeat a value rather than one "
                    "where it is constant by construction; that group is small "
                    "and is reported apart only to keep the two arms' records "
                    "the same shape."},
}
ARM = ARMS["E"]


def evaluate(rows, header, trouble):
    e1 = crit_join(rows, header, trouble)
    e2 = crit_level_shift(rows)
    e3 = crit_square(rows)
    e4 = crit_granularity(rows)
    named = [(ARM["prefix"] + "1  the two schedules meet on one position key, in one unit",
              "instrument", e1),
             (ARM["prefix"] + "2  whether the two classes differ by a constant",
              "own_reading", e2),
             (ARM["prefix"] + "3  the square, within a block and across blocks, apart",
              "own_reading", e3),
             (ARM["prefix"] + "4  how many values each side takes, before any reading",
              "instrument", e4)]
    return [_crit(n, k, r) for n, k, r in named], [e1[2], e2[2], e3[2], e4[2]]


def _crit(name, kind, result):
    """One criterion, with its third cell kept out of the two verdicts.

    A branch that finds no object to read returns None rather than False.
    Writing it as False would put it on the ledger as a reading that came out
    false, which is the one thing the rule about the undecided cell forbids, and
    the census that counts failures reads both the prose and a `void` field, so
    the field is set here rather than left to a word in the detail.
    """
    verdict = result[0]
    crit = {"name": name, "kind": kind, "detail": result[1],
            "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        crit["void"] = True
    return crit


def probe(path):
    """Print the header before anything is picked from it (`D12`)."""
    start, header = find_header(path)
    if start is None:
        print("no header row naming both a month and an hour column in the first 40")
        with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
            for index, row in enumerate(csv.reader(handle)):
                if index >= 6:
                    break
                print("  row " + str(index) + ": " + ", ".join(row[:12]))
        return 1
    print("header on row " + str(start) + ", " + str(len(header)) + " columns")
    for index, cell in enumerate(header):
        print("  " + str(index).rjust(3) + "  " + cell)
    picked, trouble = pick_columns(header)
    print("")
    for key in WANT:
        print("  " + key.ljust(8) + " -> "
              + ("column " + str(picked[key]) + "  " + header[picked[key]]
                 if key in picked else "NOT FOUND"))
    for line in trouble:
        print("  trouble: " + line)
    return 0 if not trouble else 1


HEAD = ["utility", "month", "hour", "daytype", "nem2_credit", "nem3_acc"]


def _seed(p2_of, p3_of, months=(1, 7), hours=(2, 10, 18), utilities=("PGE",)):
    rows = [HEAD]
    for u in utilities:
        for m in months:
            for h in hours:
                rows.append([u, m, h, "weekday",
                             format(p2_of(m, h), ".5f"), format(p3_of(m, h), ".5f")])
    return rows


def _write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def _named(crits):
    return {c["name"].split()[0]: c for c in crits}


def selftest():
    import tempfile
    checks = []
    # NEM-2 is flat inside a season, NEM-3 moves with the hour: the shape depends
    # on the class and the crossing pairs have to say so
    shaped = _seed(lambda m, h: 0.30 if m == 7 else 0.20,
                   lambda m, h: 0.05 + 0.01 * h)
    # a pure level shift: both move together and differ by a constant
    shifted = _seed(lambda m, h: 0.25 + 0.01 * h, lambda m, h: 0.05 + 0.01 * h)
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        _write(d / "shaped.csv", shaped)
        got = _named(evaluate(*read_rows(d / "shaped.csv"))[0])
        checks.append(("all four pass on a clean joined table",
                       all(c["passed"] is True for c in got.values())))
        checks.append(("and none of them carries a void field",
                       not any("void" in c for c in got.values())))
        checks.append(("E2 calls a moving difference branch two",
                       "branch two" in got["B98-E2"]["detail"]))
        checks.append(("E3 calls the crossing pairs branch one",
                       "branch one" in got["B98-E3"]["detail"]))
        checks.append(("E4 reports the coarser side as coarser",
                       "takes 2 distinct values" in got["B98-E4"]["detail"]))

        _write(d / "shifted.csv", shifted)
        got = _named(evaluate(*read_rows(d / "shifted.csv"))[0])
        checks.append(("a pure level shift is called branch one by E2",
                       "branch one" in got["B98-E2"]["detail"]))
        checks.append(("and branch two by E3, which is the same statement",
                       "branch two" in got["B98-E3"]["detail"]))

        # seeded: a table in dollars per megawatt hour
        mwh = [list(r) for r in shaped]
        for r in mwh[1:]:
            r[4] = format(float(r[4]) * 1000.0, ".5f")
            r[5] = format(float(r[5]) * 1000.0, ".5f")
        _write(d / "mwh.csv", mwh)
        got = _named(evaluate(*read_rows(d / "mwh.csv"))[0])
        checks.append(("a table in the wrong unit drops E1", not got["B98-E1"]["passed"]))

        # and the other half of that: one real spike is not a unit error. The
        # first version of this check drew its line where arm E's data stopped,
        # and arm F's earlier batch reaches $2.52/kWh on October evenings, which
        # failed a whole run on three rows of true prices.
        spike = [list(r) for r in shaped]
        for r in spike[1:4]:
            r[-1] = "2.52139"
        _write(d / "spike.csv", spike)
        got = _named(evaluate(*read_rows(d / "spike.csv"))[0])
        checks.append(("three true spikes do not drop E1",
                       got["B98-E1"]["passed"] is True))

        # seeded: a repeated position key
        dup = [list(r) for r in shaped] + [list(shaped[1])]
        _write(d / "dup.csv", dup)
        got = _named(evaluate(*read_rows(d / "dup.csv"))[0])
        checks.append(("a repeated position key drops E1", not got["B98-E1"]["passed"]))

        # seeded: NEM-2 given hour by hour too, so no two positions share a block
        # and the within group empties out
        fine = _seed(lambda m, h: 0.20 + 0.011 * h + 0.1 * (m == 7),
                     lambda m, h: 0.05 + 0.01 * h)
        _write(d / "fine.csv", fine)
        got = _named(evaluate(*read_rows(d / "fine.csv"))[0])
        checks.append(("with no two positions in one block E3 refuses to read",
                       got["B98-E3"]["passed"] is None
                       and got["B98-E3"].get("void") is True))

        # seeded: one side constant, so the square has no object
        flat = _seed(lambda m, h: 0.25, lambda m, h: 0.05 + 0.01 * h)
        _write(d / "flat.csv", flat)
        got = _named(evaluate(*read_rows(d / "flat.csv"))[0])
        checks.append(("a constant NEM-2 side drops E4", not got["B98-E4"]["passed"]))
        checks.append(("and E4 says the reading has no object",
                       "third cell" in got["B98-E4"]["detail"]))

        # seeded: values on no decimal grid at all, so E2 has no floor
        offgrid = [list(r) for r in shaped]
        for i, r in enumerate(offgrid[1:], 1):
            r[5] = format(0.05 + i * 0.0123456789, ".10f")
        _write(d / "offgrid.csv", offgrid)
        got = _named(evaluate(*read_rows(d / "offgrid.csv"))[0])
        checks.append(("values on no decimal grid put E2 in its third cell",
                       got["B98-E2"]["passed"] is None
                       and got["B98-E2"].get("void") is True))
        checks.append(("and E2 says the floor does not exist",
                       "does not exist" in got["B98-E2"]["detail"]))

        # no criterion is typed rival, by the argument in the docstring
        got = _named(evaluate(*read_rows(d / "shaped.csv"))[0])
        checks.append(("no criterion is typed rival",
                       all(c["kind"] != "rival" for c in got.values())))

        # seeded: a renamed column
        renamed = [list(r) for r in shaped]
        renamed[0][4] = "credit_one"
        _write(d / "renamed.csv", renamed)
        got = _named(evaluate(*read_rows(d / "renamed.csv"))[0])
        checks.append(("a renamed credit column drops E1", not got["B98-E1"]["passed"]))
    for label, passed in checks:
        print("  " + ("ok  " if passed else "FAIL") + "  " + label)
    return 0 if all(p for _, p in checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--arm", choices=sorted(ARMS), default="E")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    global ARM
    ARM = ARMS[args.arm]
    if not args.path:
        ap.error("a path to the joined table is required")
    path = pathlib.Path(args.path)
    if not path.exists():
        print("not on disk: " + str(path))
        return 2
    if args.probe:
        return probe(path)
    rows, header, trouble = read_rows(path)
    crits, reports = evaluate(rows, header, trouble)
    for crit in crits:
        mark = ("NO OBJECT, third cell:" if crit["passed"] is None
                else "PASS" if crit["passed"]
                else "FAILED[" + crit["kind"] + "]:")
        print(mark + " " + crit["name"])
        print("    " + crit["detail"][:600])
    # One record per input. The path was a constant, so running the second rate
    # schedule overwrote the first one's reading, and rule 18a wants both on the
    # ledger. The name follows the input, which is also what `18d` asks of the
    # config block: the record says what it was run on.
    out = OUT.with_name(OUT.stem + "_" + path.stem.replace("joined_", "") + OUT.suffix)
    record = {
        "stage": ARM["prefix"],
        "config": {"source_name": path.name, "positions": len(rows),
                   "arm": ARM["prefix"], "class_a": ARM["a"], "class_b": ARM["b"],
                   "plausible_median": list(PLAUSIBLE_MEDIAN),
                   "max_any_cell": MAX_ANY},
        "report": {c["name"].split()[0]: r for c, r in zip(crits, reports)},
        "criteria": crits,
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    print("")
    print("wrote " + str(out.relative_to(ROOT)))
    # An undecided cell is not a failure, so it does not set the exit code.
    return 1 if any(c["passed"] is False for c in crits) else 0


if __name__ == "__main__":
    sys.exit(main())
