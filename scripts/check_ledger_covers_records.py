#!/usr/bin/env python3
"""Which recorded criteria never reach the hand-written ledger.

The renderer that built RESULTS.md from the records was retired in favour of
writing the ledger by hand, and the ratchet that checked every record had a job
in the runner went with it. Both were retired for good reasons. What went with
them is the only thing that ever asked whether a criterion on disk reached the
index at all, and the renderer had been missing four whole stations when it was
retired, which is how anyone found out.

So this asks that one question and nothing else: a criterion carries an
identifier, and the identifier either appears in RESULTS.md or it does not.

It reports and does not gate, and the reason is in the ratchet it replaces. A
gate here needs an exemption list, and the last exemption list on this question
held two thirds of the population, which is not an exemption list. A station
section that reports its readings in prose without naming the criteria is a real
way to satisfy the load-bearing rule, and telling that apart from a station the
index forgot is a reading, not a regex. So the regex prints and the reading is
left where it belongs.

Two numbers are worth more than the total. One is records with no identifier in
the ledger at all, the shape the renderer failed in. The other is stations whose
name appears nowhere in the ledger in any spelling, which is that shape without
any room to argue about it.

    python scripts/check_ledger_covers_records.py
    python scripts/check_ledger_covers_records.py --root ../topology-fingerprints
    python scripts/check_ledger_covers_records.py --selftest
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from fail_census import VOID
except Exception:                          # pragma: no cover
    VOID = re.compile(r"\b(void|not evaluated|does not run|no object|nothing to "
                      r"pair|not adjudicable|not run|not reproduced|not tested)\b",
                      re.I)

#: A criterion identifier: a station token, then at least one dashed part.
#: `A3-8`, `B19-G-1`, `A2e-2`, `B35-PH-9` all match; a criterion named in a
#: sentence with no identifier does not, and those are counted separately.
TOK = re.compile(r"^([A-Za-z]{1,3}\d+[a-zA-Z]*(?:-[A-Za-z0-9]+)+)")
STATION = re.compile(r"^([A-Za-z]{1,3}\d+[a-zA-Z]*)")


def present(tok, ledger):
    """The token, not embedded in a longer identifier.

    Without the boundaries `B7-5` matches inside `B7-50`, and a check that
    counts a longer name as this one reports coverage it does not have.
    """
    return bool(re.search(rf"(?<![A-Za-z0-9-]){re.escape(tok)}(?![A-Za-z0-9-])",
                          ledger))


def station_present(tok, ledger):
    """A station is named when a criterion of its own names it.

    Same boundaries on either side, except that a following dash is allowed,
    because the ledger writes a station by writing one of its criteria. The
    strict form called a station forgotten when its criteria were all listed:
    `C11` is named on every line that says `C11-1`, and only the bare-token
    test could not see it. A digit still stops it, so `C11` is not read out of
    `C110`.
    """
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(tok)}(?![A-Za-z0-9])",
                          ledger))


def candidates(root):
    root = pathlib.Path(root).resolve()
    res = root / "results"
    if not res.is_dir():
        return []
    files = [p for p in res.rglob("*.json") if ".expired" not in p.name]
    rel = [str(p.relative_to(root)) for p in files]
    try:
        out = subprocess.run(["git", "-C", str(root), "check-ignore", "-z", "--stdin"],
                             input="\0".join(rel), capture_output=True, text=True)
        ign = {x for x in out.stdout.split("\0") if x}
    except Exception:
        ign = set()
    kept = [p for p, r in zip(files, rel) if r not in ign]
    # One record name can sit at the top level and again in a subdirectory. A
    # count of records is not a count of stations, and here the station is what
    # is being asked about, so the duplicates are folded by name.
    return sorted({p.name: p for p in kept}.values())


def scan(files, ledger):
    whole, partial, unnamed, stations = [], [], 0, {}
    for p in files:
        try:
            doc = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        cs = doc.get("criteria")
        if not isinstance(cs, list):
            continue
        rows = []
        for c in cs:
            if not isinstance(c, dict):
                continue
            nm = str(c.get("name") or c.get("criterion") or "").strip()
            m = TOK.match(nm)
            if not m:
                unnamed += 1
                continue
            rows.append((m.group(1), c.get("passed"),
                         bool(VOID.search(str(c.get("detail", ""))))))
        if not rows:
            continue
        for tok, _, _ in rows:
            s = STATION.match(tok).group(1)
            stations.setdefault(s, station_present(s, ledger))
        miss = [r for r in rows if not present(r[0], ledger)]
        if not miss:
            continue
        rec = {"record": pathlib.Path(p).name, "criteria": len(rows),
               "absent": len(miss),
               "absent_fail": sum(1 for _, ps, _ in miss if ps is False),
               "absent_fail_live": sum(1 for _, ps, v in miss
                                       if ps is False and not v),
               "tokens": [t for t, _, _ in miss]}
        (whole if len(miss) == len(rows) else partial).append(rec)
    return whole, partial, unnamed, stations


def selftest():
    ledger = "## B1 the first\n| PASS | B1-1 in the ledger |\n| FAIL | B1-2 also |\n"
    seeded = {
        "in.json": {"criteria": [
            {"name": "B1-1 in the ledger", "passed": True, "detail": "x"},
            {"name": "B1-2 also", "passed": False, "detail": "y"}]},
        "half.json": {"criteria": [
            {"name": "B1-1 in the ledger", "passed": True, "detail": "x"},
            {"name": "B1-3 not in the ledger", "passed": False, "detail": "y"}]},
        "out.json": {"criteria": [
            {"name": "B2-1 a station the ledger never names", "passed": False,
             "detail": "y"},
            {"name": "B2-2 and this one says it was not evaluated", "passed": False,
             "detail": "Void: nothing to read"}]},
        "prose.json": {"criteria": [
            {"name": "a criterion with no identifier", "passed": True, "detail": "x"}]},
    }
    with tempfile.TemporaryDirectory() as d:
        res = pathlib.Path(d) / "results"
        res.mkdir()
        for name, doc in seeded.items():
            (res / name).write_text(json.dumps(doc), encoding="utf-8")
        whole, partial, unnamed, stations = scan(sorted(res.glob("*.json")), ledger)
    ok = True
    if [r["record"] for r in whole] != ["out.json"]:
        ok = False
        print(f"  whole: expected out.json, got {[r['record'] for r in whole]}")
    if [r["record"] for r in partial] != ["half.json"]:
        ok = False
        print(f"  partial: expected half.json, got {[r['record'] for r in partial]}")
    if unnamed != 1:
        ok = False
        print(f"  unnamed: expected 1, got {unnamed}")
    if whole and (whole[0]["absent_fail"], whole[0]["absent_fail_live"]) != (2, 1):
        ok = False
        print(f"  the void one should not count as a live failure, got "
              f"{whole[0]['absent_fail']} and {whole[0]['absent_fail_live']}")
    if stations != {"B1": True, "B2": False}:
        ok = False
        print(f"  stations: expected B1 present and B2 absent, got {stations}")
    if present("B1-1", "B1-10 only") or not present("B1-1", "see B1-1."):
        ok = False
        print("  the boundary test counts a longer identifier as this one")
    if not station_present("C11", "| PASS | C11-1 the row |"):
        ok = False
        print("  a station is not seen when only its criteria are listed")
    if station_present("C11", "C110 is another thing"):
        ok = False
        print("  a station is read out of a longer number")
    print("selftest " + ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    root = pathlib.Path(argv[argv.index("--root") + 1] if "--root" in argv
                        else HERE.parent).resolve()
    ledger_path = root / "RESULTS.md"
    if not ledger_path.exists():
        print(f"no ledger at {ledger_path}")
        return 0
    ledger = ledger_path.read_text(encoding="utf-8")
    files = candidates(root)
    whole, partial, unnamed, stations = scan(files, ledger)

    absent_tokens = sorted({t for r in whole + partial for t in r["tokens"]})
    print(f"scanning {root.name}, {len(files)} records by name against RESULTS.md\n")
    print(f"{len(absent_tokens)} criterion identifiers do not appear in the ledger, "
          f"across {len(whole) + len(partial)} records")
    print(f"  {sum(r['absent_fail'] for r in whole + partial)} of them carry "
          f"passed=false, and "
          f"{sum(r['absent_fail_live'] for r in whole + partial)} of those say "
          f"nothing about being unevaluated")
    print(f"  {unnamed} further criteria carry no identifier to look up")

    print(f"\n{len(whole)} record(s) have no identifier in the ledger at all, "
          f"which is the shape the renderer failed in:")
    for r in sorted(whole, key=lambda r: (-r["absent_fail"], r["record"])):
        print(f"  {r['record']:46s} {r['criteria']:3d} criteria, "
              f"{r['absent_fail']} of them passed=false")

    if partial:
        print(f"\n{len(partial)} record(s) are partly in:")
        for r in sorted(partial, key=lambda r: (-r["absent_fail"], r["record"])):
            print(f"  {r['record']:46s} {r['absent']} of {r['criteria']} absent, "
                  f"{r['absent_fail']} of those passed=false")

    gone = sorted(s for s, ok in stations.items() if not ok)
    print(f"\n{len(gone)} station token(s) appear nowhere in the ledger in any "
          f"spelling: {', '.join(gone) if gone else 'none'}")
    print("\nreported, not gated: a section that reports its readings in prose "
          "without naming the criteria satisfies the load-bearing rule, and "
          "telling that apart from a forgotten station is a reading.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
