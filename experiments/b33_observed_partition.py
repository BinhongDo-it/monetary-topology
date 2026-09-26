"""B33 arm one, observed side: what partition the published table actually carries.

Arm one read a tax code against itself: two filing statuses, a joint return and a
surviving spouse, take the same cell in every provision that prints a number and
are separated only by provisions that print none. The obvious next question is
whether they also pay the same at the same income, and the registered reading for
that was an ordering rather than a line: the pair sharing every printed number
should show a far smaller gap in effective rate than pairs that differ on printed
numbers.

That reading registered a third outcome before the file was opened, and it is the
one that fired. The analytical table with money in it does not report the two
apart. Its column blocks are

    All returns
    Returns of married persons filing jointly and returns of surviving spouses
    Returns of married persons filing separately
    Returns of heads of households
    Returns of single persons

which is four statuses in four blocks, and the merged one is exactly the pair that
shares every printed number in the code. The table's heading for that block is
almost word for word the heading of the rate section itself.

So the within-pair comparison is not available from this source. That is recorded
as the published aggregate being unable to reach it rather than as the quantity
being absent: the returns exist, the revenue service assessed each one knowing
which of the two it was, and a count of surviving-spouse returns is published
elsewhere. What is not published is any money broken out that way.

What the table does give is the other half of the registered ordering: the gaps
between statuses that do differ on printed numbers. Those are computed here, so
the size of the comparison that went missing is on the record rather than merely
described.

Usage
-----
    python b33_observed_partition.py
    python b33_observed_partition.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "b33"
ARM_ONE = ROOT / "results" / "b33_filing_status.json"
OUT = ROOT / "results" / "b33_observed_partition.json"

SHEET = "TBL12"
HEADER_ROW = 2                     # the row carrying the block headings
BLOCK_COLS = [1, 13, 25, 37, 49]   # first column of each block, read from r2
RETURNS, AGI, TAX = 0, 1, 11       # offsets inside a block
FIRST_BAND, LAST_BAND = 10, 27     # the all-returns panel, excluding the total
                                   # and the negative-income row above it

# What the code's own statuses are called here, so a block heading can be mapped
# to a set of them. Substrings, and chosen to survive a plural: the first version
# of the inspector wrote "head of household" and the table says "heads of
# households", which made one block invisible.
NAMES = {"joint": "MFJ", "surviving": "QSS", "separate": "MFS",
         "head": "HOH", "single": "SINGLE"}

STATE_MAP = {
    "reachable": {"verdict": "scored",
                  "reads": "the table reports the pair apart, so the gap in "
                           "effective rate can be read"},
    "not_reachable": {"verdict": None,
                      "reads": "the table folds the pair into one block, so this "
                               "source cannot reach the comparison. The quantity "
                               "exists and is assessed per return; what is absent "
                               "is a published breakout"},
}


def statuses_in(heading):
    low = " ".join(str(heading).split()).lower()
    if low.startswith("all returns"):
        return ["ALL"]
    found = [v for k, v in NAMES.items() if k in low]
    # "married persons filing jointly" contains both "joint" and "married"; MFS is
    # only claimed when the heading says separately.
    if "MFS" in found and "MFJ" in found:
        found.remove("MFS")
    return sorted(set(found))


def read_year(path):
    import pandas as pd
    f = pd.ExcelFile(path).parse(SHEET, header=None)
    blocks = []
    for c in BLOCK_COLS:
        blocks.append({"col": c,
                       "heading": " ".join(str(f.iat[HEADER_ROW, c]).split()),
                       "statuses": statuses_in(f.iat[HEADER_ROW, c])})
    bands = []
    for r in range(FIRST_BAND, LAST_BAND + 1):
        label = " ".join(str(f.iat[r, 0]).split())
        row = {"band": label, "by_status": {}}
        for b in blocks:
            if b["statuses"] == ["ALL"]:
                continue
            agi, tax = f.iat[r, b["col"] + AGI], f.iat[r, b["col"] + TAX]
            n = f.iat[r, b["col"] + RETURNS]
            try:
                agi, tax, n = float(agi), float(tax), float(n)
            except (TypeError, ValueError):
                continue
            if agi > 0:
                row["by_status"]["+".join(b["statuses"])] = {
                    "returns": n, "agi": agi, "tax": tax,
                    "effective_rate": tax / agi}
        if row["by_status"]:
            bands.append(row)
    return {"file": path.name, "shape": list(f.shape), "blocks": blocks,
            "bands": bands}


def price_list_partition():
    if not ARM_ONE.exists():
        return None
    rec = json.loads(ARM_ONE.read_text(encoding="utf-8"))
    return rec.get("report", {}).get("partition_numbers_only")


def as_partition(blocks):
    return sorted([sorted(b["statuses"]) for b in blocks
                   if b["statuses"] != ["ALL"]])


def analyse(years):
    price = price_list_partition()
    price_norm = sorted([sorted(b) for b in price]) if price else None
    out = {"years": [], "price_list_partition": price_norm,
           "state_map": STATE_MAP}
    for y in years:
        part = as_partition(y["blocks"])
        merged = [b for b in part if len(b) > 1]
        pair_apart = any(b == ["QSS"] for b in part)
        spreads = []
        for row in y["bands"]:
            rates = {k: v["effective_rate"] for k, v in row["by_status"].items()}
            if len(rates) >= 2:
                lo_k = min(rates, key=rates.get)
                hi_k = max(rates, key=rates.get)
                spreads.append({"band": row["band"],
                                "rates": rates,
                                "spread_pp": (rates[hi_k] - rates[lo_k]) * 100,
                                "lowest": lo_k, "highest": hi_k})
        out["years"].append({
            "file": y["file"], "shape": y["shape"],
            "headings": [b["heading"] for b in y["blocks"]],
            "partition": part, "blocks": len(part), "merged": merged,
            "matches_price_list": price_norm is not None and part == price_norm,
            "pair_reported_apart": pair_apart,
            "state": "reachable" if pair_apart else "not_reachable",
            "bands_read": len(y["bands"]),
            "spreads": spreads,
            "spread_min_pp": min((s["spread_pp"] for s in spreads), default=None),
            "spread_max_pp": max((s["spread_pp"] for s in spreads), default=None),
        })
    return out


def criteria(rep):
    ys = rep["years"]
    same = [y for y in ys if y["matches_price_list"]]
    reach = [y for y in ys if y["state"] == "reachable"]
    merged_pairs = sorted({"+".join(m) for y in ys for m in y["merged"]})
    spreads = [s for y in ys for s in y["spreads"]]
    return [
        {
            "name": "B33-21 the published table with money in it carries the "
                    "price list's partition, not the code's list of statuses, and "
                    "the block it merges is the pair that shares every printed "
                    "number",
            "kind": "own_reading",
            "passed": len(same) == len(ys) and merged_pairs == ["MFJ+QSS"],
            "detail": "%d of %d years match the price list partition %s; merged "
                      "block(s) across years: %s; blocks per year: %s"
                      % (len(same), len(ys), rep["price_list_partition"],
                         ", ".join(merged_pairs),
                         ", ".join("%s %d" % (y["file"], y["blocks"]) for y in ys)),
        },
        {
            "name": "B33-22 the within-pair gap in effective rate, which is what "
                    "the observed side of arm one was registered to read",
            "kind": "own_reading",
            "state_map": STATE_MAP,
            "state": "reachable" if reach else "not_reachable",
            "passed": False,
            "detail": "Not adjudicable: the published aggregate cannot reach it. "
                      "%d of %d years report the pair apart. The returns exist and "
                      "each was assessed knowing which of the two it was; a count "
                      "of surviving-spouse returns is published elsewhere. What is "
                      "absent is money broken out that way, so this is recorded as "
                      "out of reach and not as absent"
                      % (len(reach), len(ys)),
        },
        {
            "name": "B33-23 control: the fold is not indiscriminate. Every status "
                    "that differs from the others on a printed number is reported "
                    "in a block of its own, and the benchmark half of the "
                    "registered ordering is computed so the size of the missing "
                    "comparison is on the record",
            "kind": "known_answer",
            "passed": (all(len(y["merged"]) == 1 for y in ys)
                       and all(y["blocks"] == 4 for y in ys)
                       and len(spreads) > 0),
            "detail": "each year has exactly one merged block and four in total; "
                      "across-status spread in effective rate over %d band-years "
                      "runs %.2f to %.2f percentage points, median %.2f"
                      % (len(spreads),
                         min(s["spread_pp"] for s in spreads),
                         max(s["spread_pp"] for s in spreads),
                         sorted(s["spread_pp"] for s in spreads)[len(spreads) // 2]),
        },
        {
            "name": "B33-24 the price list's partition is read out of arm one's "
                    "record rather than typed here",
            "kind": "instrument",
            "passed": rep["price_list_partition"] is not None,
            "detail": "read from %s: %s" % (ARM_ONE.name,
                                            rep["price_list_partition"]),
        },
        {
            "name": "B33-25 every year read is named with its shape, its block "
                    "headings and how many bands came back, including any year "
                    "whose layout differs",
            "kind": "bookkeeping",
            "passed": (len(ys) > 0
                       and len({tuple(y["headings"]) for y in ys}) == 1),
            "detail": "%d years, %s; identical block headings across years: %s; "
                      "bands read: %s"
                      % (len(ys), ", ".join(y["file"] for y in ys),
                         len({tuple(y["headings"]) for y in ys}) == 1,
                         ", ".join("%s %d" % (y["file"], y["bands_read"])
                                   for y in ys)),
        },
    ]


def selftest():
    ok = True
    assert STATE_MAP["not_reachable"]["verdict"] is None, \
        "an unreachable comparison must carry no verdict"

    fake = {"file": "seed.xls", "shape": [49, 63],
            "blocks": [{"col": 1, "heading": "All returns", "statuses": ["ALL"]},
                       {"col": 13, "heading": "joint", "statuses": ["MFJ"]},
                       {"col": 17, "heading": "surviving", "statuses": ["QSS"]},
                       {"col": 25, "heading": "separately", "statuses": ["MFS"]},
                       {"col": 37, "heading": "heads", "statuses": ["HOH"]},
                       {"col": 49, "heading": "single", "statuses": ["SINGLE"]}],
            "bands": [{"band": "b", "by_status": {
                "MFJ": {"returns": 1, "agi": 100.0, "tax": 10.0,
                        "effective_rate": 0.10},
                "QSS": {"returns": 1, "agi": 100.0, "tax": 10.0,
                        "effective_rate": 0.10}}}]}
    r = analyse([fake])
    c = {x["name"].split()[0]: x for x in criteria(r)}
    if c["B33-22"]["state"] != "reachable":
        print("selftest: a table that reports the pair apart must read reachable")
        ok = False
    if c["B33-21"]["passed"]:
        print("selftest: B33-21 should fail when the table does not carry the "
              "price list partition")
        ok = False

    # A heading naming both joint and separately must not claim MFS.
    if statuses_in("Returns of married persons filing jointly and returns of "
                   "surviving spouses") != ["MFJ", "QSS"]:
        print("selftest: the joint block must map to exactly MFJ and QSS")
        ok = False
    if statuses_in("Returns of heads of households") != ["HOH"]:
        print("selftest: a plural heading must still map")
        ok = False

    print("selftest: %s" % ("all seeds behaved" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    files = sorted(p for p in SRC.glob("*in12ms.xls") if ".expired" not in p.name)
    if not files:
        print("no table in %s. Run b33_step0_fetch_soi.py first." % SRC)
        return 1
    years = [read_year(p) for p in files]
    rep = analyse(years)
    crit = criteria(rep)

    print("B33 arm one, observed side: the partition the published table carries\n")
    for y in rep["years"]:
        print("%s  %d x %d  blocks: %d  merged: %s  matches price list: %s"
              % (y["file"], y["shape"][0], y["shape"][1], y["blocks"],
                 ", ".join("+".join(m) for m in y["merged"]) or "none",
                 y["matches_price_list"]))
    print("\nprice list partition, read from arm one's record: %s"
          % rep["price_list_partition"])
    print("block headings as the table writes them:")
    for h in rep["years"][0]["headings"]:
        print("   %s" % h)
    print()
    y = rep["years"][-1]
    print("effective rate by band and published status, %s" % y["file"])
    keys = sorted({k for s in y["spreads"] for k in s["rates"]})
    print("%-28s %s   spread pp"
          % ("band", " ".join("%9s" % k for k in keys)))
    for s in y["spreads"]:
        cells = " ".join("%9.4f" % s["rates"][k] if k in s["rates"] else "%9s" % "-"
                         for k in keys)
        print("%-28s %s   %8.2f" % (s["band"][:28], cells, s["spread_pp"]))
    print()
    for c in crit:
        print("%-5s %-11s %s" % ("PASS" if c["passed"] else "FAIL", c["kind"],
                                 c["name"].split(" ", 1)[0]))
        print("      %s" % c["detail"])

    OUT.write_text(json.dumps({
        "stage": "B33",
        "config": {
            "arm": "one, observed side",
            "source": "Statistics of Income basic table 1.2, classified by size "
                      "of adjusted gross income and marital status",
            "years": [p.name for p in files],
            "sheet": SHEET, "block_first_columns": BLOCK_COLS,
            "band_rows": [FIRST_BAND, LAST_BAND],
            "effective_rate": "total income tax amount divided by adjusted gross "
                              "income less deficit, both taken from the same cell "
                              "block so no two definitions are divided",
            "price_list_source": ARM_ONE.name,
            "read_on": "2026-09-11",
        },
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit if c.get("state") != "not_reachable"
                    ) else 1


if __name__ == "__main__":
    sys.exit(main())
