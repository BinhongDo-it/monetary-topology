"""B100: the three published shares of a global surgical package, and whether they add to one.

The publisher states the identity and hedges it in the same breath. The record
layout for the relative value file says of the preoperative, intraoperative and
postoperative percentage fields:

    The total of fields 17, 18, and 19 will usually equal one. Any variance is
    slight and results from rounding.

`D48` and `11e` say to read a claim at the strength its own wording gives it, so
this station reads two objects rather than one. The rows that do add to one are a
zero calibration whose band is fixed by the fields' own format, five decimals
each, worst case 1.5e-5 on the sum. The rows that do not are the list the word
"usually" points at, and the publisher does not say which rows those are. Nobody
has had a reason to count them, which is what makes the second object the one
worth having.

The file is not fetched here. Columns are found by name and never by position,
because a layout can be renumbered between years while a name is stable, and
guessing a position is the defect rule 24 is about.

**No criterion here scores a count against a line.** Rule 11 allows a criterion
to be structural, or a printed number with a reading declared in advance, and not
a threshold drawn on an estimate. So the number of rows inside the band is
printed and the verdicts are structural: the band is the published resolution and
was not moved, the partition loses no row, the units are shares rather than
percents, and the rows that carry no package carry no share either.

Run:
    python experiments/b100_global_package.py --probe <path to the RVU file>
    python experiments/b100_global_package.py <path to the RVU file>
    python experiments/b100_global_package.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b100_global_package.json"

# Each share is written 9v9(5) in the published layout, so each one is rounded to
# 1e-5 and the worst the sum can be off by rounding alone is three halves of that.
# The band is the publisher's resolution and is not ours to move: the banned
# shapes table forbids a threshold anchored on whatever this run happens to print.
TICK = 1e-5
PUBLISHED_BAND = 1.5 * TICK
BAND = PUBLISHED_BAND

# Global-period values that carry no global package at all. On those rows the
# three shares are zero by construction and their sum is zero rather than one.
NO_PACKAGE = ("000", "XXX", "MMM", "YYY", "ZZZ")

WANT = {
    "hcpcs": (r"hcpcs",),
    "global": (r"glob",),
    "pre": (r"pre.*op",),
    "intra": (r"intra.*op",),
    "post": (r"post.*op",),
}


def _norm(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def find_header(path, limit=40):
    """The first row that names an HCPCS column is the header, and it may be two.

    The published file carries several title rows above the real header, and how
    many varies. Searching for the column rather than counting rows is the same
    rule as finding the column by name: a count is a position.

    The 2026 release splits its column names over two rows, so the row naming
    HCPCS reads `GLOB`, `PRE`, `INTRA`, `POST` as `DAYS`, `OP`, `OP`, `OP` and
    three of the four wanted columns are simply not there under any name. The
    row above is folded in when it looks like a continuation rather than a title:
    mostly non-empty, and nothing in it parses as a number. A title row is
    almost all empty, so the test separates them without counting rows.
    """
    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        rows = []
        for index, row in enumerate(csv.reader(handle)):
            if index >= limit:
                break
            rows.append([cell.strip() for cell in row])
            if any("hcpcs" in _norm(cell) for cell in row):
                header = rows[-1]
                if index and _is_continuation(rows[-2]):
                    above = rows[-2]
                    header = [(above[i] + " " + cell).strip()
                              if i < len(above) else cell
                              for i, cell in enumerate(header)]
                return index, header
    return None, []


def _is_continuation(row):
    """Does this row carry the top half of the column names, or is it a title?

    A continuation fills most of its cells and none of them is a number. A title
    row leaves nearly everything blank. Both appear above the header in the
    published file, so this is what tells them apart.
    """
    filled = [c for c in row if c.strip()]
    if len(filled) < max(3, len(row) // 2):
        return False
    for cell in filled:
        try:
            float(cell.replace(",", ""))
            return False
        except ValueError:
            pass
    return True


def pick_columns(header):
    """Map each wanted field to a column index, by name. Ambiguity is reported."""
    picked, trouble = {}, []
    for key, patterns in WANT.items():
        hits = [i for i, cell in enumerate(header)
                if any(re.search(p, _norm(cell)) for p in patterns)]
        if not hits:
            trouble.append("no column matches " + key)
        elif len(hits) > 1 and key != "hcpcs":
            trouble.append(key + " matches " + str(len(hits)) + " columns: "
                           + ", ".join(header[i] for i in hits))
            picked[key] = hits[0]
        else:
            picked[key] = hits[0]
    return picked, trouble


def read_rows(path):
    start, header = find_header(path)
    if start is None:
        return [], [], ["no header row naming an HCPCS column in the first rows"]
    picked, trouble = pick_columns(header)
    if len(picked) < len(WANT):
        return [], header, trouble
    rows = []
    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        for index, raw in enumerate(csv.reader(handle)):
            if index <= start:
                continue
            if not raw or len(raw) <= max(picked.values()):
                continue
            code = raw[picked["hcpcs"]].strip()
            if not code:
                continue
            try:
                pre = float(raw[picked["pre"]].strip() or 0.0)
                intra = float(raw[picked["intra"]].strip() or 0.0)
                post = float(raw[picked["post"]].strip() or 0.0)
            except ValueError:
                continue
            rows.append({"hcpcs": code,
                         "global": raw[picked["global"]].strip().upper(),
                         "pre": pre, "intra": intra, "post": post})
    return rows, header, trouble


def split(rows):
    """Rows that carry a global package, and rows that cannot."""
    with_pkg = [r for r in rows if r["global"] not in NO_PACKAGE]
    without = [r for r in rows if r["global"] in NO_PACKAGE]
    return with_pkg, without


def gaps(rows):
    return [(abs(r["pre"] + r["intra"] + r["post"] - 1.0), r) for r in rows]


def crit_columns(rows, header, trouble):
    """B100-0: the three columns are there under their own names and read as shares."""
    if trouble:
        return False, "; ".join(trouble)[:400]
    if not rows:
        return False, "the header was found and no data row survived parsing"
    bad = [r["hcpcs"] for r in rows
           if not all(0.0 <= r[k] <= 1.0 for k in ("pre", "intra", "post"))]
    detail = (str(len(rows)) + " rows read by column name, header begins "
              + ", ".join(header[:4]) + "; every share lies in [0, 1]"
              if not bad else
              str(len(bad)) + " rows carry a share outside [0, 1], which is what a "
              + "file written in percents rather than shares looks like. First: "
              + ", ".join(bad[:8]))
    return not bad, detail


def crit_zero(with_pkg):
    """B100-1: the zero calibration, and it is structural rather than a line.

    Three things have to hold and each can fail. The band is the published
    resolution and was not moved. The partition loses no row. And at least one
    row sits inside the band, which is the check that the column is a share
    rather than a percent: a file in percents puts every row outside.
    """
    if not with_pkg:
        return None, ("no row carries a global period that has a package, so this "
                      "criterion has no object and was not evaluated; it lands in "
                      "the third cell rather than on either verdict")
    pairs = gaps(with_pkg)
    inside = [g for g, _ in pairs if g <= BAND]
    outside = [g for g, _ in pairs if g > BAND]
    worst = max(g for g, _ in pairs)
    faults = []
    if abs(BAND - PUBLISHED_BAND) > 1e-12:
        faults.append("the band is " + format(BAND, ".3e") + " and the published "
                      + "resolution is " + format(PUBLISHED_BAND, ".3e"))
    if len(inside) + len(outside) != len(pairs):
        faults.append("the partition drops rows")
    if not inside:
        faults.append("no row at all sits inside the band, so the column is not a "
                      "share on the scale this reads")
    detail = (str(len(inside)) + " of " + str(len(pairs))
              + " rows with a package sum to one inside the band their own format "
              + "allows (" + format(BAND, ".1e") + "), a share of "
              + format(len(inside) / len(pairs), ".4f") + ". Worst gap "
              + format(worst, ".3e") + ", " + format(worst / BAND, ".2f")
              + " times the band. **This line prints the count and draws no "
              + "threshold on it; the reading is B100-2.**")
    if faults:
        detail = "; ".join(faults) + "  |  " + detail
    return not faults, detail


def crit_usually(with_pkg):
    """B100-2: the rows the word usually points at, named rather than counted."""
    if BAND >= 0.5:
        return False, ("the band has been widened to " + format(BAND, ".1e")
                       + ", which swallows every object this criterion reads")
    pairs = gaps(with_pkg)
    outside = sorted([(g, r) for g, r in pairs if g > BAND],
                     key=lambda t: (-t[0], t[1]["hcpcs"]))
    by_global = {}
    for _, r in outside:
        by_global[r["global"]] = by_global.get(r["global"], 0) + 1
    if not outside:
        worst = max((g for g, _ in pairs), default=0.0)
        detail = ("branch one: no row with a package falls outside the band, so on "
                  "this file the identity is exact and the hedge in the layout "
                  "points at another year or another file. Worst gap "
                  + format(worst, ".3e") + ", "
                  + format(worst / BAND, ".2f") + " times the band")
    else:
        named = "; ".join(
            r["hcpcs"] + " global " + r["global"] + " "
            + format(r["pre"], ".5f") + "+" + format(r["intra"], ".5f") + "+"
            + format(r["post"], ".5f") + "="
            + format(r["pre"] + r["intra"] + r["post"], ".5f")
            for _, r in outside[:25])
        detail = ("branch two: " + str(len(outside)) + " of " + str(len(pairs))
                  + " rows fall outside the band, by global period "
                  + str(sorted(by_global.items()))
                  + ". Named, worst first: " + named)
    return True, detail[:1400]


def crit_no_package_is_zero(without):
    """B100-3: a row with no global package carries no share either.

    A known answer: those codes have nothing to split, so all three fields should
    be zero. A row that carries a share anyway is a named exception and this
    criterion is what finds it.
    """
    if not without:
        return None, ("no row carries a global period from " + ", ".join(NO_PACKAGE)
                      + ", which the published file always has, so the global "
                      + "column is not being read and this criterion was not "
                      + "evaluated; it lands in the third cell")
    nonzero = [r for r in without
               if abs(r["pre"]) + abs(r["intra"]) + abs(r["post"]) > BAND]
    named = "; ".join(r["hcpcs"] + " global " + r["global"] + " "
                      + format(r["pre"] + r["intra"] + r["post"], ".5f")
                      for r in nonzero[:15])
    detail = (str(len(without)) + " rows carry a global period with no package ("
              + ", ".join(NO_PACKAGE) + ") and are held out of B100-1 and B100-2. "
              + (("Of those, " + str(len(nonzero)) + " carry a share that is not "
                  "zero: " + named) if nonzero
                 else "Every one of them carries zero in all three fields."))
    return not nonzero, detail


def evaluate(rows, header, trouble):
    with_pkg, without = split(rows)
    c0 = crit_columns(rows, header, trouble)
    c1 = crit_zero(with_pkg)
    c2 = crit_usually(with_pkg)
    c3 = crit_no_package_is_zero(without)
    named = [("B100-0  the three shares are found by name and read as shares",
              "instrument", c0),
             ("B100-1  the band is the published one and the partition is whole",
              "known_answer", c1),
             ("B100-2  the rows the layout's word usually points at, named",
              "own_reading", c2),
             ("B100-3  a code with no global package carries no share",
              "known_answer", c3)]
    return [_crit(n, k, r) for n, k, r in named], with_pkg, without


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
    """Print the whole header before anything is picked from it.

    `D12` says enumerate before choosing. This station was written without the
    file in hand, so the first run prints the set and judges nothing.
    """
    start, header = find_header(path)
    if start is None:
        print("no header row naming an HCPCS column in the first 40 rows")
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
    print("picked by name:")
    for key in WANT:
        if key in picked:
            print("  " + key.ljust(7) + " -> column " + str(picked[key])
                  + "  " + header[picked[key]])
        else:
            print("  " + key.ljust(7) + " -> NOT FOUND")
    for line in trouble:
        print("  trouble: " + line)
    return 0 if not trouble else 1


SEED_ROWS = [
    ["a title row, ignored", "", "", "", ""],
    ["HCPCS", "GLOB DAYS", "PRE OP", "INTRA OP", "POST OP"],
    ["10000", "090", "0.10000", "0.69000", "0.21000"],
    ["10001", "090", "0.10000", "0.69001", "0.21000"],
    ["10002", "010", "0.09000", "0.80000", "0.11000"],
    ["10003", "090", "0.10000", "0.60000", "0.21000"],
    ["10004", "XXX", "0.00000", "0.00000", "0.00000"],
    ["10005", "000", "0.00000", "0.00000", "0.00000"],
]


def _write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def _named(crits):
    return dict((c["name"].split()[0], c) for c in crits)


def selftest():
    import copy
    import tempfile
    global BAND
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)
        base = tmpdir / "rvu.csv"
        _write(base, SEED_ROWS)
        rows, header, trouble = read_rows(base)
        crits, with_pkg, without = evaluate(rows, header, trouble)
        by = _named(crits)
        checks.append(("four rows with a package are found", len(with_pkg) == 4))
        checks.append(("two rows with no package are held out", len(without) == 2))
        checks.append(("all four criteria pass on a clean file",
                       all(c["passed"] is True for c in crits)))
        checks.append(("and none of them carries a void field",
                       not any("void" in c for c in crits)))
        checks.append(("B100-2 names the row that misses by 0.09",
                       "10003" in by["B100-2"]["detail"]))
        checks.append(("a miss of one tick stays inside the band",
                       "10001" not in by["B100-2"]["detail"]))

        seeded = []

        renamed = copy.deepcopy(SEED_ROWS)
        renamed[1][2] = "FIRST PART"
        path2 = tmpdir / "renamed.csv"
        _write(path2, renamed)
        got = _named(evaluate(*read_rows(path2))[0])
        seeded.append(("a renamed column drops B100-0", not got["B100-0"]["passed"]))

        percents = copy.deepcopy(SEED_ROWS)
        for row in percents[2:6]:
            row[2], row[3], row[4] = "10.0", "69.0", "21.0"
        path3 = tmpdir / "percents.csv"
        _write(path3, percents)
        got = _named(evaluate(*read_rows(path3))[0])
        seeded.append(("a file written in percents drops B100-0",
                       not got["B100-0"]["passed"]))

        keep = BAND
        BAND = 0.9
        got = _named(evaluate(rows, header, trouble)[0])
        seeded.append(("a moved band drops B100-1", not got["B100-1"]["passed"]))
        seeded.append(("a swallowing band drops B100-2", not got["B100-2"]["passed"]))
        BAND = keep

        dirty = copy.deepcopy(SEED_ROWS)
        dirty[6][3] = "0.40000"          # an XXX code carrying an intra share
        path4 = tmpdir / "dirty.csv"
        _write(path4, dirty)
        got = _named(evaluate(*read_rows(path4))[0])
        seeded.append(("a share on a code with no package drops B100-3",
                       not got["B100-3"]["passed"]))
        seeded.append(("and that row is named", "10004" in got["B100-3"]["detail"]))

        noglobal = copy.deepcopy(SEED_ROWS)
        for row in noglobal[2:]:
            row[1] = "090"
        path5 = tmpdir / "noglobal.csv"
        _write(path5, noglobal)
        got = _named(evaluate(*read_rows(path5))[0])
        seeded.append(("a file with no held-out rows puts B100-3 in its third cell",
                       got["B100-3"]["passed"] is None
                       and got["B100-3"].get("void") is True))
        seeded.append(("and that third cell is not an exit code",
                       not any(c["passed"] is False for c in got.values())))

        checks += seeded
    for label, passed in checks:
        print("  " + ("ok  " if passed else "FAIL") + "  " + label)
    return 0 if all(p for _, p in checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.path:
        ap.error("a path to the relative value file is required")
    path = pathlib.Path(args.path)
    if not path.exists():
        print("not on disk: " + str(path))
        return 2
    if args.probe:
        return probe(path)
    rows, header, trouble = read_rows(path)
    crits, with_pkg, without = evaluate(rows, header, trouble)
    for crit in crits:
        mark = ("NO OBJECT, third cell:" if crit["passed"] is None
                else "PASS" if crit["passed"]
                else "FAILED[" + crit["kind"] + "]:")
        print(mark + " " + crit["name"])
        print("    " + crit["detail"][:600])
    record = {
        "stage": "B100",
        "config": {"band": BAND, "tick": TICK, "no_package": list(NO_PACKAGE),
                   "source_name": path.name, "rows": len(rows),
                   "rows_with_package": len(with_pkg),
                   "rows_without_package": len(without)},
        "criteria": crits,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print("")
    print("wrote " + str(OUT.relative_to(ROOT)))
    # An undecided cell is not a failure, so it does not set the exit code.
    return 1 if any(c["passed"] is False for c in crits) else 0


if __name__ == "__main__":
    sys.exit(main())
