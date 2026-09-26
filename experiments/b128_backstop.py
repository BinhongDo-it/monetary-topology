"""B128: the deposit backstop written as a feature, and B97's squares split by it (`D55`, design cell 1, 兜底方).

A deposit is backed by its country's deposit guarantee scheme (EUR 100,000 per depositor under the directive, paid
from that sovereign's means); a loan is not. So a square that pairs two products with the same cover cancels the
backstop between two countries, and a square that pairs different cover carries it.

B97 read 15 squares per carrier (six products paired), Cyprus and Greece each against the euro area aggregate, and
counted the months above a floor of 0.02 percentage points. Three of the 15 pairs have the same cover on both sides:
household overnight against household term deposits, corporate overnight against corporate term deposits, and
house-purchase loans against corporate loans. This reads B97's own raw files (data/raw/mir, fetched for B97), checks
first that it reproduces B97's counts, and then splits them.

    python experiments/b128_backstop.py
    python experiments/b128_backstop.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIR = ROOT / "data" / "raw" / "mir"
OUT = ROOT / "results" / "b128_backstop.json"
FLOOR = 0.02
B97 = {"CY": (2354, 2395), "GR": (3193, 3240)}
PRODUCTS = {"hh_overnight": "L21_A_R_A_2250", "nfc_overnight": "L21_A_R_A_2240", "hh_term": "L22_F_R_A_2250",
            "nfc_term": "L22_F_R_A_2240", "house": "A2C_F_R_A_2250", "nfc_loan": "A2A_F_R_A_2240"}
COVER = {"hh_overnight": "household deposit", "hh_term": "household deposit", "nfc_overnight": "corporate deposit",
         "nfc_term": "corporate deposit", "house": "loan", "nfc_loan": "loan"}


def load(area: str, shape: str) -> dict[str, float]:
    path = MIR / f"MIR_M_{area}_B_{shape}_EUR_N.csv"
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["OBS_VALUE"]:
                out[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    return out


def squares(series: dict[str, dict[str, dict[str, float]]], area: str) -> dict[tuple[str, str], dict]:
    out = {}
    for g, h in itertools.combinations(PRODUCTS, 2):
        a_g, a_h, u_g, u_h = series[area][g], series[area][h], series["U2"][g], series["U2"][h]
        months = sorted(set(a_g) & set(a_h) & set(u_g) & set(u_h))
        vals = [(a_g[m] - u_g[m]) - (a_h[m] - u_h[m]) for m in months]
        above = sum(abs(v) > FLOOR + 1e-9 for v in vals)   # B97's stated rule: at or under the floor is rounding
        raw = sum(abs(v) > FLOOR for v in vals)             # B97's code, where a square of exactly 0.02 can float over
        out[(g, h)] = {"months": len(months), "above": above, "above_raw": raw, "same_cover": COVER[g] == COVER[h],
                       "max_over_floor": round(max(abs(v) for v in vals) / FLOOR, 1) if vals else None}
    return out


def split(sq: dict) -> dict:
    same = [v for v in sq.values() if v["same_cover"]]
    mixed = [v for v in sq.values() if not v["same_cover"]]
    tot = lambda vs: (sum(v["above"] for v in vs), sum(v["months"] for v in vs))
    raw = (sum(v["above_raw"] for v in sq.values()), sum(v["months"] for v in sq.values()))
    return {"all": tot(sq.values()), "all_raw": raw, "same_cover": tot(same), "mixed_cover": tot(mixed)}


def build() -> dict:
    series = {a: {p: load(a, s) for p, s in PRODUCTS.items()} for a in ("CY", "GR", "U2")}
    rows, reproduced = {}, {}
    for area in ("CY", "GR"):
        sq = squares(series, area)
        sp = split(sq)
        rows[area] = {"split": sp, "pairs": {f"{g} / {h}": v for (g, h), v in sq.items()}}
        reproduced[area] = tuple(sp["all_raw"]) == B97[area]
    crit = [
        {"name": "B128-14", "kind": "known_answer",
         "statement": "the 15 squares per carrier, read from B97's own raw files with B97's comparison as coded, reproduce B97's counts",
         "passed": all(reproduced.values()),
         "detail": "; ".join(f"{a}: {rows[a]['split']['all_raw'][0]}/{rows[a]['split']['all_raw'][1]} against B97 {B97[a][0]}/{B97[a][1]}; "
                             f"with squares at exactly the floor counted as rounding, as B97 states: {rows[a]['split']['all'][0]}"
                             for a in rows)},
        {"name": "B128-15", "kind": "own_reading",
         "statement": "print, per carrier, how many months the three same-cover pairs (which the backstop cannot enter) stand above the floor, beside the twelve mixed-cover pairs",
         "passed": all(rows[a]["split"]["same_cover"][1] > 0 for a in rows),
         "detail": "; ".join(f"{a}: same cover {rows[a]['split']['same_cover'][0]}/{rows[a]['split']['same_cover'][1]}, "
                             f"mixed cover {rows[a]['split']['mixed_cover'][0]}/{rows[a]['split']['mixed_cover'][1]}" for a in rows)},
    ]
    return {"stage": "B128", "reading": "backstop as a feature; B97 squares split", "rows": rows, "criteria": crit,
            "config": {"floor_pp": FLOOR, "products": PRODUCTS, "cover": COVER},
            "source": {"rates": "data/raw/mir (B97's fetch)", "b97_counts": B97}}


def selftest() -> None:
    months = [f"2010-{m:02d}" for m in range(1, 13)]
    flat = {m: 1.0 for m in months}
    # a country premium only on deposits: same-cover squares cancel, mixed-cover squares do not
    dep = {m: 1.5 for m in months}
    series = {"CY": {p: (dep if COVER[p] != "loan" else flat) for p in PRODUCTS},
              "U2": {p: flat for p in PRODUCTS}}
    sp = split(squares(series, "CY"))
    assert sp["same_cover"][0] == 0 and sp["mixed_cover"][0] > 0, sp
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    out = build()
    for a, r in out["rows"].items():
        print(f"== {a}: all {r['split']['all']}, same cover {r['split']['same_cover']}, mixed cover {r['split']['mixed_cover']}")
        for k, v in r["pairs"].items():
            if v["same_cover"]:
                print(f"   {k:<30} {v['above']}/{v['months']}  max {v['max_over_floor']}x floor")
    for c in out["criteria"]:
        print(f"{c['name']} [{c['kind']}] {'PASS' if c['passed'] else 'FAIL'}: {c['detail']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
