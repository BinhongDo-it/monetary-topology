"""B36-5: United States beef to destinations other than China.

Route. The obvious way to get this is one fetch with CTY_CODE=* and a split on
the destination name. That route is closed, and it took two probes to find out
why. Without any destination predicate the feed returns a single aggregate row
per commodity-month. With CTY_CODE=* it does return 98 destinations, but the
list mixes countries with regions and trade blocs, AFRICA and APEC and ASEAN
and ASIA sitting beside ARUBA, and the destination code was never requested so
the two cannot be told apart after the fact. Adding up everything that is not
China would count much of the world several times.

So the arm is built out of two numbers that are each defined without reference
to that list:

    non-China  =  all countries  -  China

Both at COMM_LVL=HS10, because HS6 carries no quantity at all: a six digit
class covers ten digit lines whose units may differ, so there is no common unit
to report and UNIT_QY1 comes back as "-". Value is fine at HS6; quantity is not.

The bands are pinned in the B36 result file, section R8.2, before any non-China
number was looked at:

    ratio >= 0.75   PASS, the fall is specific to the China lane
    ratio <= 0.444  FAIL, the same fall happens everywhere, cause is US-side
    between         undecided

Run, after both fetches are on disk:
    python b35_step0_fetch.py --hs 0201 0202 --years 2016 2026 --cty total --level HS10
    python b35_step0_fetch.py --hs 0201 0202 --years 2016 2026 --cty 5700 --level HS10
    python b36_step1_dest_split.py
"""

import argparse
import io
import json
from collections import defaultdict
from pathlib import Path

BASE_YEARS = (2021, 2024)
TEST_YEAR = 2025
PASS_AT = 0.75
FAIL_AT = 0.444


def load(src: Path, label):
    if not src.exists():
        raise SystemExit("not on disk: %s\nSee the header of this file for the "
                         "two fetch commands." % src)
    recs = json.loads(io.open(src, encoding="utf-8").read())
    if not isinstance(recs, list) or not recs:
        raise SystemExit("%s is not a non-empty list" % src)
    names = sorted({(r.get("CTY_NAME") or "").strip() for r in recs})
    units = sorted({(r.get("UNIT_QY1") or "").strip() for r in recs})
    withq = sum(1 for r in recs
                if str(r.get("QTY_1_MO") or "0") not in ("0", "", "-"))
    print("%s: %d rows from %s" % (label, len(recs), src.name))
    print("   destinations       : %s" % (names if len(names) <= 4 else
                                          "%d distinct" % len(names)))
    print("   quantity units     : %s" % units)
    print("   rows with quantity : %d of %d" % (withq, len(recs)))
    if not withq:
        raise SystemExit("no row in %s carries a quantity. HS6 has none; refetch "
                         "at --level HS10." % src.name)
    if len(names) != 1:
        raise SystemExit("%s should hold exactly one destination bucket and "
                         "holds %d. Nothing subtracted." % (src.name, len(names)))
    return recs, names[0]


def by_year(recs):
    per = defaultdict(float)
    months = defaultdict(set)
    lines = defaultdict(float)
    for r in recs:
        y = int(r["_year"])
        try:
            q = float(str(r.get("QTY_1_MO") or 0).replace(",", ""))
        except ValueError:
            q = 0.0
        per[y] += q
        months[y].add(int(r["_month"]))
        lines[str(r.get("E_COMMODITY") or "?")] += q
    return per, months, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", default=None)
    ap.add_argument("--china", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    res = root / "results"
    ptot = Path(a.total) if a.total else res / "b35_census_raw_0201-0202_total.json"
    pcn = Path(a.china) if a.china else res / "b35_census_raw_0201-0202_5700.json"

    print("=" * 74)
    print("B36-5, non-China as all countries minus China")
    print("=" * 74)
    rt, nt = load(ptot, "all countries")
    rc, nc = load(pcn, "China      ")
    if "TOTAL" not in nt.upper():
        raise SystemExit("the first file is labelled %r, which is not the "
                         "all-countries aggregate. Nothing subtracted." % nt)
    if "CHINA" not in nc.upper():
        raise SystemExit("the second file is labelled %r, not China. Nothing "
                         "subtracted." % nc)

    tot, mt, lt = by_year(rt)
    cn, mc, lc = by_year(rc)

    print("\n" + "=" * 74)
    print("United States beef, HS 0201 plus 0202, tonnes")
    print("=" * 74)
    print("  %-6s %7s %14s %14s %14s" % ("year", "months", "all", "China",
                                         "non-China"))
    bad = []
    for y in sorted(tot):
        other = tot[y] - cn.get(y, 0.0)
        print("  %-6d %7d %14.0f %14.0f %14.0f"
              % (y, len(mt[y]), tot[y] / 1e3, cn.get(y, 0.0) / 1e3, other / 1e3))
        if other < 0:
            bad.append(y)
        if mt[y] != mc.get(y, set()):
            miss = sorted(mt[y] ^ mc.get(y, set()))
            print("         month coverage differs between the two files: %s"
                  % miss)
    if bad:
        raise SystemExit("China exceeds the all-countries total in %s. The two "
                         "files are not the same object; nothing judged." % bad)

    have = [y for y in range(BASE_YEARS[0], BASE_YEARS[1] + 1) if y in tot]
    if len(have) != 4 or TEST_YEAR not in tot:
        raise SystemExit("base window or test year incomplete. Nothing judged.")
    other = {y: tot[y] - cn.get(y, 0.0) for y in tot}
    mean_o = sum(other[y] for y in have) / len(have)
    mean_c = sum(cn.get(y, 0.0) for y in have) / len(have)
    r_o = other[TEST_YEAR] / mean_o
    r_c = cn.get(TEST_YEAR, 0.0) / mean_c if mean_c else float("nan")

    print("\n" + "=" * 74)
    print("B36-5, the number first")
    print("=" * 74)
    print("  window judged     : %d against the mean of %d to %d"
          % (TEST_YEAR, *BASE_YEARS))
    print("  months in %d      : %d of 12" % (TEST_YEAR, len(mt[TEST_YEAR])))
    print("  non-China ratio   : %.4f" % r_o)
    print("  China ratio       : %.4f   (B36-4 read 0.296 on the same level)"
          % r_c)
    print("  bands, pinned before looking: pass >= %.3f, fail <= %.3f"
          % (PASS_AT, FAIL_AT))
    if len(mt[TEST_YEAR]) < 12:
        v = "UNDECIDED, the test year is not complete in this record"
    elif r_o >= PASS_AT:
        v = "PASS, the fall is specific to the China lane"
    elif r_o <= FAIL_AT:
        v = "FAIL, the same fall happens elsewhere, cause is US-side"
    else:
        v = "UNDECIDED, between the two registered bands"
    print("  verdict           : %s" % v)

    # Same trend caveat as the Brazil side, section 9.7: printed, no verdict.
    print("\n  diagnostic, no verdict attached:")
    print("    %d against %d alone : %.4f"
          % (TEST_YEAR, BASE_YEARS[1], other[TEST_YEAR] /
             max(other[BASE_YEARS[1]], 1.0)))
    if 2026 in tot and mt[2026]:
        m = len(mt[2026])
        print("    2026 so far: %d months, non-China %.0f t, annualised %.0f t"
              % (m, other[2026] / 1e3, other[2026] * 12.0 / m / 1e3))

    print("\n  joint reading: B36-6 already read HELD UP at 1.4718, so the "
          "second row of the design's four-cell table is out either way.")

    rec = {"stage": "B36", "criterion": "B36-5 destination split",
           "route": "all countries minus China, both at HS10",
           "sources": [ptot.name, pcn.name],
           "window": {"base": list(BASE_YEARS), "test": TEST_YEAR},
           "bands": {"pass_at": PASS_AT, "fail_at": FAIL_AT},
           "tonnes": {str(y): {"all": tot[y] / 1e3,
                               "china": cn.get(y, 0.0) / 1e3,
                               "other": other[y] / 1e3,
                               "months": len(mt[y])} for y in sorted(tot)},
           "ratio_non_china": r_o, "ratio_china": r_c, "verdict": v}
    out = Path(a.out) if a.out else res / "b36_dest_split.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
