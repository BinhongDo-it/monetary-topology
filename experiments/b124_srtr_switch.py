"""B124: does the US 2020 liver reform have a donor type it left alone?

The UK carrier reads its DBD reform against DCD, whose rule did not change. Before the same
check of Theorem 46 (docs/b124_transport_dual.md) runs on the US carrier, this script reads
whether the 4 February 2020 acuity-circle policy moved DBD and DCD livers alike, from the
SRTR transplant records The Markup released (data/SOURCES.md, B124).

It also writes a slim cache of the transplant table, the fields later parts need, so the
135 MB archive is streamed once.

Reading, per month and donor type (adult recipients, deceased donors, liver only):
  shared      share with DON_ORG_SHARED = 1 (the liver left its recovering OPO's local unit)
  cross_opo   share where the recipient's OPO differs from the donor's OPO

Run:  python experiments/b124_srtr_switch.py [--selftest]
"""

import argparse
import csv
import gzip
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data" / "raw" / "investigation-organs-main.zip"
MEMBER = "investigation-organs-main/01_data/raw/04_transplant/TX_LI_22F218Records(2of2)-redacted.csv.gz"
CACHE = ROOT / "data" / "derived" / "b124" / "srtr_tx_slim.csv.gz"
OUT = ROOT / "results" / "b124_srtr_switch.json"
ROWS_EXPECTED = 192_982
FIELDS = ["REC_TX_DT", "CAN_LISTING_DT", "DON_TY", "DON_NON_HR_BEAT", "REC_TX_ORG_TY",
          "REC_TX_PROCEDURE_TY", "REC_AGE_AT_TX", "DON_ORG_SHARED", "REC_OPO_ID",
          "DON_OPO_CTR_ID", "REC_CTR_ID", "CAN_ABO", "DON_ABO", "CAN_LAST_SRTR_LAB_MELD",
          "CAN_LAST_SRTR_LAB_MELD_TY"]
REFORM = date(2020, 2, 4)
# Ages are released in bands; "5-Jan", "11-Jun" and "17-Dec" are 1-5, 6-11 and 12-17
# turned into dates by a spreadsheet.
ADULT_BANDS = {"18-34", "35-49", "50-64", "65+"}
WINDOW = ((2018, 1), (2022, 2))


def build_cache():
    n = 0
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_name(CACHE.name + ".partial.expired")
    with zipfile.ZipFile(ZIP) as z, z.open(MEMBER) as f, \
            gzip.open(f, "rt", encoding="utf-8", errors="replace", newline="") as g, \
            gzip.open(tmp, "wt", encoding="utf-8", newline="") as out:
        r = csv.reader(g)
        ix = {c: i for i, c in enumerate(next(r))}
        w = csv.writer(out, lineterminator="\n")
        w.writerow(FIELDS)
        for row in r:
            w.writerow([row[ix[c]] for c in FIELDS])
            n += 1
    if n != ROWS_EXPECTED:
        raise SystemExit(f"transplant table read {n} rows, expected {ROWS_EXPECTED}")
    tmp.replace(CACHE)
    return n


def load():
    if not CACHE.exists():
        build_cache()
    with gzip.open(CACHE, "rt", encoding="utf-8", newline="") as g:
        rows = list(csv.DictReader(g))
    if len(rows) != ROWS_EXPECTED:
        raise SystemExit(f"cache holds {len(rows)} rows, expected {ROWS_EXPECTED}")
    return rows


def mdy(s):
    m, d, y = s.split("/")
    return date(int(y), int(m), int(d))


def keep(r):
    return (r["DON_TY"] == "C" and r["REC_TX_ORG_TY"] == "LI: Liver"
            and r["REC_AGE_AT_TX"] in ADULT_BANDS
            and r["DON_NON_HR_BEAT"] in ("Y", "N") and r["REC_TX_DT"])


def monthly(rows):
    cells = {}
    for r in rows:
        if not keep(r):
            continue
        t = mdy(r["REC_TX_DT"])
        if not (WINDOW[0] <= (t.year, t.month) <= WINDOW[1]):
            continue
        k = ("DCD" if r["DON_NON_HR_BEAT"] == "Y" else "DBD", f"{t.year}-{t.month:02d}")
        c = cells.setdefault(k, [0, 0, 0])
        c[0] += 1
        c[1] += r["DON_ORG_SHARED"] == "1"
        c[2] += r["REC_OPO_ID"] != r["DON_OPO_CTR_ID"]
    return {f"{d} {m}": {"n": c[0], "shared": c[1] / c[0], "cross_opo": c[2] / c[0]}
            for (d, m), c in sorted(cells.items())}


def window_change(series, donor):
    """Mean share over the 12 months before the reform month and months 2 to 13 after it."""
    def mean(months, key):
        vals = [series[f"{donor} {m}"][key] for m in months if f"{donor} {m}" in series]
        return sum(vals) / len(vals)
    pre = [f"{y}-{m:02d}" for y, m in [(2019, k) for k in range(2, 13)] + [(2020, 1)]]
    post = [f"{y}-{m:02d}" for y, m in [(2020, k) for k in range(3, 13)] + [(2021, 1), (2021, 2)]]
    return {k: {"pre": mean(pre, k), "post": mean(post, k)} for k in ("shared", "cross_opo")}


def build(series):
    ch = {d: window_change(series, d) for d in ("DBD", "DCD")}
    jump = {d: ch[d]["cross_opo"]["post"] - ch[d]["cross_opo"]["pre"] for d in ch}
    crit = [
        {"name": "B124-S1", "kind": "instrument",
         "statement": "Both donor types have a reading in every month of the window",
         "passed": all(f"{d} {y}-{m:02d}" in series for d in ("DBD", "DCD")
                       for y in range(WINDOW[0][0], WINDOW[1][0] + 1) for m in range(1, 13)
                       if WINDOW[0] <= (y, m) <= WINDOW[1])},
        {"name": "B124-S2", "kind": "premise",
         "statement": "The cross-OPO share of DCD livers moves less at the reform than that of DBD livers",
         "passed": jump["DCD"] < jump["DBD"],
         "detail": f"cross-OPO change, pre 12 months to months 2-13 after: DBD {jump['DBD']:+.3f}, "
                   f"DCD {jump['DCD']:+.3f}"},
    ]
    return ch, crit


def selftest(series):
    swapped = {(k.replace("DBD", "X").replace("DCD", "DBD").replace("X", "DCD")): v
               for k, v in series.items()}
    assert build(series)[1][1]["passed"] != build(swapped)[1][1]["passed"], "S2 did not flip on swapped labels"
    thin = {k: v for k, v in series.items() if k != "DCD 2020-06"}
    assert not build(thin)[1][0]["passed"], "S1 did not flip on a missing month"
    print("selftest: 2/2 seeds flip their flag")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    series = monthly(load())
    if a.selftest:
        selftest(series)
        return 0
    ch, crit = build(series)
    for d in ("DBD", "DCD"):
        print(f"== {d}: month  n  shared  cross_opo")
        for k, v in series.items():
            if k.startswith(d) and k[-2:] in ("01", "04", "07", "10", "02"):
                print(f"  {k[4:]}  {v['n']:4d}  {v['shared']:.3f}  {v['cross_opo']:.3f}")
        print(f"  window means: {json.dumps(ch[d], sort_keys=True)}")
    for c in crit:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['statement']}"
              f"  {c.get('detail', '')}")
    rec = {"stage": "B124-S", "config": {"window": [list(WINDOW[0]), list(WINDOW[1])],
           "reform": REFORM.isoformat(), "filter": "deceased donor, liver only, recipient 18+"},
           "monthly": {k: {"n": v["n"], "shared": round(v["shared"], 4),
                           "cross_opo": round(v["cross_opo"], 4)} for k, v in series.items()},
           "window_change": {d: {k: {p: round(x, 4) for p, x in v.items()} for k, v in c.items()}
                             for d, c in ch.items()},
           "criteria": crit}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
