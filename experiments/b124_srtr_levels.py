"""B124: Theorem 46 read on the US carrier, within recipient blood group.

Theorem 46 (docs/b124_transport_dual.md): where levels are an allocation's shadow values,
centres joined by routes in use differ by the difference of the routes' terms. The 4 February
2020 acuity-circle policy replaced allocation by donation service area and region with
circles of 150, 250 and 500 nautical miles around the donor, so route terms depend less on
the route than before, and the theorem's reading is that centre levels within one blood group
move closer. DCD livers moved too, by less than half as much (results/b124_srtr_switch.json),
so they are read as a partial control.

Units: windows of 12 months aligned to the reform date, two before (W1, W2) and two after
(W3, W4). Cells: donor type x recipient blood group (O, A, B, AB) x transplant centre x window.
Levels, per cell, both printed:
  wait   median days from listing to transplant, on the log scale
  meld   median laboratory MELD at transplant (allocation MELD with exception points is not
         released in this file)
Floor per cell: se of the median = 1.2533 x IQR / 1.349 / sqrt N (log scale for wait).
Dispersion per (donor type, blood group, window): Q / df of the deviations of the centres
with N >= MIN_N from their precision-weighted mean. Structure per (blood group, window):
routes in use from donor OPO to transplant centre, and b1 = E - V + c.

Run:  python experiments/b124_srtr_levels.py [--selftest] [--min-n N]
"""

import argparse
import csv
import gzip
import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "derived" / "b124" / "srtr_tx_slim.csv.gz"
OUT = ROOT / "results" / "b124_srtr_levels.json"
ADULT_BANDS = {"18-34", "35-49", "50-64", "65+"}
GROUPS = {"O: O": "O", "A: A": "A", "A1: A1": "A", "A2: A2": "A", "B: B": "B",
          "AB: AB": "AB", "A1B: A1B": "AB", "A2B: A2B": "AB"}
WINDOWS = {"W1": (date(2018, 2, 4), date(2019, 2, 4)), "W2": (date(2019, 2, 4), date(2020, 2, 4)),
           "W3": (date(2020, 2, 4), date(2021, 2, 4)), "W4": (date(2021, 2, 4), date(2022, 2, 4))}
PRE, POST = ("W1", "W2"), ("W3", "W4")


def mdy(s):
    m, d, y = s.split("/")
    return date(int(y), int(m), int(d))


def window(t):
    for k, (a, b) in WINDOWS.items():
        if a <= t < b:
            return k
    return None


def load():
    out = []
    with gzip.open(CACHE, "rt", encoding="utf-8", newline="") as g:
        for r in csv.DictReader(g):
            if (r["DON_TY"] != "C" or r["REC_TX_ORG_TY"] != "LI: Liver"
                    or r["REC_AGE_AT_TX"] not in ADULT_BANDS or r["DON_NON_HR_BEAT"] not in ("Y", "N")
                    or r["CAN_ABO"] not in GROUPS or not r["REC_TX_DT"] or not r["CAN_LISTING_DT"]):
                continue
            t = mdy(r["REC_TX_DT"])
            w = window(t)
            if w is None:
                continue
            meld = r["CAN_LAST_SRTR_LAB_MELD"].split("MELD/PELD ")[-1] if r["CAN_LAST_SRTR_LAB_MELD_TY"] == "M" else ""
            out.append({"donor": "DCD" if r["DON_NON_HR_BEAT"] == "Y" else "DBD",
                        "group": GROUPS[r["CAN_ABO"]], "centre": r["REC_CTR_ID"],
                        "opo": r["DON_OPO_CTR_ID"], "window": w,
                        "wait": max((t - mdy(r["CAN_LISTING_DT"])).days, 0) + 1,
                        "meld": int(meld) if meld.isdigit() else None})
    return out


def quartiles(xs):
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return q[0], statistics.median(xs), q[2]


def cell_level(vals, log):
    xs = [math.log(v) for v in vals] if log else list(vals)
    q1, m, q3 = quartiles(xs)
    return {"N": len(xs), "median": m, "se": max(1.2533 * (q3 - q1) / 1.349 / math.sqrt(len(xs)), 1e-9)}


def dispersion(levels, min_n):
    pts = [v for v in levels.values() if v["N"] >= min_n]
    if len(pts) < 3:
        return None
    w = [1 / p["se"] ** 2 for p in pts]
    mean = sum(wi * p["median"] for wi, p in zip(w, pts)) / sum(w)
    q = sum(wi * (p["median"] - mean) ** 2 for wi, p in zip(w, pts))
    return {"centres": len(pts), "Q_over_df": q / (len(pts) - 1),
            "sd": statistics.stdev(p["median"] for p in pts),
            "median_floor": statistics.median(p["se"] for p in pts)}


def structure(rows):
    edges = {(r["opo"], r["centre"]) for r in rows}
    verts = {("o", a) for a, _ in edges} | {("c", b) for _, b in edges}
    parent = {v: v for v in verts}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v
    for a, b in edges:
        parent[find(("o", a))] = find(("c", b))
    comps = len({find(v) for v in verts})
    return {"routes": len(edges), "vertices": len(verts), "components": comps,
            "b1": len(edges) - len(verts) + comps}


def build(rows, min_n):
    disp, struct = {}, {}
    for donor in ("DBD", "DCD"):
        for g in ("O", "A", "B", "AB"):
            for w in WINDOWS:
                sub = [r for r in rows if r["donor"] == donor and r["group"] == g and r["window"] == w]
                by = {}
                for r in sub:
                    by.setdefault(r["centre"], []).append(r)
                key = f"{donor} {g} {w}"
                disp[key] = {
                    "wait": dispersion({c: cell_level([r["wait"] for r in v], True)
                                        for c, v in by.items() if len(v) >= 4}, min_n),
                    "meld": dispersion({c: cell_level([r["meld"] for r in v if r["meld"] is not None], False)
                                        for c, v in by.items()
                                        if sum(r["meld"] is not None for r in v) >= 4}, min_n)}
                if donor == "DBD":
                    struct[f"{g} {w}"] = structure(sub)

    def change(donor, level):
        out = {}
        for g in ("O", "A", "B", "AB"):
            pre = [disp[f"{donor} {g} {w}"][level] for w in PRE]
            post = [disp[f"{donor} {g} {w}"][level] for w in POST]
            if None in pre + post:
                out[g] = None
                continue
            out[g] = (sum(p["sd"] for p in post) - sum(p["sd"] for p in pre)) / 2
        return out
    ch = {f"{d} {lv}": change(d, lv) for d in ("DBD", "DCD") for lv in ("wait", "meld")}

    def all_fall(key):
        v = [x for x in ch[key].values() if x is not None]
        return bool(v) and len(v) == 4 and all(x < 0 for x in v)

    def dbd_below_dcd(level):
        a, b = ch[f"DBD {level}"], ch[f"DCD {level}"]
        pairs = [(a[g], b[g]) for g in a if a[g] is not None and b[g] is not None]
        return bool(pairs) and len(pairs) == 4 and all(x < y for x, y in pairs)
    crit = [
        {"name": "B124-U1", "kind": "own_reading",
         "statement": "Within each blood group, the spread of DBD centre medians of lab MELD at transplant "
                      "falls from the two windows before the reform to the two after",
         "passed": all_fall("DBD meld"), "detail": ch["DBD meld"]},
        {"name": "B124-U2", "kind": "own_reading",
         "statement": "Within each blood group, the spread of DBD centre log median waits falls across the reform",
         "passed": all_fall("DBD wait"), "detail": ch["DBD wait"]},
        {"name": "B124-U3", "kind": "own_reading",
         "statement": "Within each blood group the DBD fall in MELD spread exceeds the DCD fall",
         "passed": dbd_below_dcd("meld"), "detail": {"DBD": ch["DBD meld"], "DCD": ch["DCD meld"]}},
        {"name": "B124-U4", "kind": "own_reading",
         "statement": "Within each blood group the DBD fall in wait spread exceeds the DCD fall",
         "passed": dbd_below_dcd("wait"), "detail": {"DBD": ch["DBD wait"], "DCD": ch["DCD wait"]}},
    ]
    return disp, struct, ch, crit


def selftest(rows, min_n):
    import copy
    # spread the post-reform DBD MELD values by centre: U1 must fail
    bad = copy.deepcopy(rows)
    ids = sorted({r["centre"] for r in bad})
    rank = {c: i for i, c in enumerate(ids)}
    for r in bad:
        if r["donor"] == "DBD" and r["window"] in POST and r["meld"] is not None:
            r["meld"] += rank[r["centre"]] % 7 * 4
    assert not build(bad, min_n)[3][0]["passed"], "U1 did not flip on spread MELD"
    # make DCD waits identical across centres after the reform: U4 must fail
    bad = copy.deepcopy(rows)
    for r in bad:
        if r["donor"] == "DCD" and r["window"] in POST:
            r["wait"] = 60 + (hash(r["opo"]) % 3)
    assert not build(bad, min_n)[3][3]["passed"], "U4 did not flip on flattened DCD waits"
    print("selftest: 2/2 seeds flip their flag")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--min-n", type=int, default=10)
    a = ap.parse_args()
    rows = load()
    if a.selftest:
        selftest(rows, a.min_n)
        return 0
    disp, struct, ch, crit = build(rows, a.min_n)
    print(f"rows {len(rows)}; centres with N >= {a.min_n} per cell enter the dispersion")
    print("structure, DBD: routes  vertices  components  b1")
    for k, s in struct.items():
        print(f"  {k}  {s['routes']:4d}  {s['vertices']:3d}  {s['components']}  {s['b1']:4d}")
    for lv in ("meld", "wait"):
        print(f"dispersion of centre medians, {lv}: sd / Q/df / centres")
        for donor in ("DBD", "DCD"):
            for g in ("O", "A", "B", "AB"):
                cells = []
                for w in WINDOWS:
                    d = disp[f"{donor} {g} {w}"][lv]
                    cells.append("   n/a          " if d is None else
                                 f"{d['sd']:6.3f} {d['Q_over_df']:6.2f} {d['centres']:3d}")
                print(f"  {donor} {g:2s}  " + "  |  ".join(cells))
    for c in crit:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['statement']}")
        print(f"      {json.dumps(c['detail'], sort_keys=True)}")

    def rnd(x):
        if isinstance(x, float):
            return round(x, 4)
        if isinstance(x, dict):
            return {k: rnd(v) for k, v in x.items()}
        return x
    rec = {"stage": "B124-U", "doc": "docs/b124_transport_dual.md",
           "config": {"min_n": a.min_n, "windows": {k: [v[0].isoformat(), v[1].isoformat()] for k, v in WINDOWS.items()},
                      "meld": "laboratory MELD at transplant, MELD candidates only",
                      "wait": "days from listing to transplant plus one, log scale",
                      "filter": "deceased donor, liver only, recipient 18+"},
           "structure_dbd": struct, "dispersion": rnd(disp), "spread_change": rnd(ch),
           "criteria": rnd(crit)}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
