"""B134: the ICP's urban-rural dimension, urban prices filled into the rural cell.

Reads what `b134_fetch.py` put in data/raw/b134/. Nothing is fetched here.

The GDP product of the ICP gives one PPP per economy. The World Bank's poverty platform gave
China, India and Indonesia two, rural and urban, built by rule from the national PPP, the ratio of
urban to rural poverty lines and the urban share of ICP price collection (PIP handbook). Their ratio
therefore reads the poverty-line ratio (D30, third clause) and is not read here as a square. What is
read: how far the national PPP sits from the rural value, how many class values each country-round-
release writes, and where the line went when two became one.

Criteria (each has a planted error in --selftest that must make it fail):
  B134-1  instrument    the same round across releases: every change is either a merge (rural and
                        urban set equal to national) or below 1e-6 relative; anything else is listed
  B134-2  known_answer  four sentences in the stored documents: Chen and Ravallion treat China's 2005
                        ICP PPP as urban; the PIP handbook computes separate rural and urban PPPs for
                        China, India and Indonesia; the India note and the Indonesia brief each say the
                        separate urban-rural PPPs were replaced
  B134-3  own_reading   class values per country x round x release, and the release where two became one
  B134-4  own_reading   China: national over rural and urban over rural by round; where the national
                        value sits on the rural-to-urban interval
  B134-5  own_reading   where the line went: the India note's state-sector spatial deflators and the
                        Indonesia brief's regency-level deflator, quoted

Run from the repo root:
    python experiments/b134_readings.py
    python experiments/b134_readings.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b134"
OUT = ROOT / "results" / "b134_readings.json"
COUNTRIES = ("CHN", "IND", "IDN")
REL_TOL = 1e-6
SENTENCES = {
    "chen_ravallion_wps4703.pdf": "We treat the ICP’s PPP as an urban PPP",
    "pip_handbook_convert.html": "separate rural and urban PPPs are computed for China, India, and Indonesia",
    "wb_india_poverty_methodology_2025.pdf": "a single national PPP factor is applied to the real welfare aggregate",
    "wb_indonesia_poverty_brief.pdf": "separate urban and rural PPP conversion factors was discontinued",
}
MOVED = {
    "wb_india_poverty_methodology_2025.pdf": r"960 indices \(32 states x 2 sectors x 15 commodity groups\)",
    "wb_indonesia_poverty_brief.pdf": r"annual regency-level spatial deflator based on a Paasche-type index",
}


def text_of(name: str) -> str:
    p = RAW / name
    if name.endswith(".pdf"):
        t = " ".join((pg.extract_text() or "") for pg in pypdf.PdfReader(p).pages)
    else:
        t = p.read_text(encoding="utf-8", errors="replace")
        t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def load_all() -> dict:
    ppp = defaultdict(dict)      # (country, round, level) -> {release: value}
    for f in sorted(RAW.glob("pip_ppp_*.csv")):
        m = re.match(r"pip_ppp_(\d{8})_(\d{4})_", f.name)
        rel, rnd = m.group(1), m.group(2)
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["country_code"] in COUNTRIES:
                ppp[(r["country_code"], rnd, r["data_level"])][rel] = float(r["value"])
    texts = {n: text_of(n) for n in set(SENTENCES) | set(MOVED)}
    return {"ppp": dict(ppp), "texts": texts}


def classes(ppp, c, rnd, rel):
    ru, ur = ppp.get((c, rnd, "rural"), {}).get(rel), ppp.get((c, rnd, "urban"), {}).get(rel)
    if ru is None or ur is None:
        return None
    return 1 if abs(ru - ur) <= REL_TOL * abs(ur) else 2


def c1(data):
    ppp = data["ppp"]
    merges, noise, other = [], 0, []
    for (c, rnd, lvl), by in ppp.items():
        rels = sorted(by)
        for a, b in zip(rels, rels[1:]):
            x, y = by[a], by[b]
            if abs(y - x) <= REL_TOL * abs(x):
                noise += 1
                continue
            nat = ppp.get((c, rnd, "national"), {}).get(b)
            if lvl in ("rural", "urban") and nat is not None and abs(y - nat) <= REL_TOL * abs(nat):
                merges.append(f"{c} {rnd} {lvl}: {x:g} -> {y:g} (equal to national) in {b}")
            else:
                other.append(f"{c} {rnd} {lvl}: {x:g} -> {y:g} in {b}")
    passed = (noise + len(merges)) > 0 and not other
    detail = (f"release-to-release pairs unchanged to 1e-6: {noise}; rural or urban merged into national: "
              f"{len(merges)}; any other change: {len(other)}")
    return passed, detail, {"unchanged": noise, "merges": sorted(merges), "other": sorted(other)}


def c2(data):
    found = {n: (s in data["texts"].get(n, "")) for n, s in SENTENCES.items()}
    passed = all(found.values())
    detail = "; ".join(f"{n}: {'found' if ok else 'MISSING'}" for n, ok in found.items())
    return passed, detail, {n: {"sentence": SENTENCES[n], "found": ok} for n, ok in found.items()}


def c3(data):
    ppp = data["ppp"]
    table, drops = {}, []
    for c in COUNTRIES:
        for rnd in ("2011", "2017", "2021"):
            rels = sorted(ppp.get((c, rnd, "national"), {}))
            seq = [(rel, classes(ppp, c, rnd, rel)) for rel in rels]
            table[f"{c} {rnd}"] = {rel: k for rel, k in seq}
            for (r0, k0), (r1, k1) in zip(seq, seq[1:]):
                if k0 == 2 and k1 == 1:
                    drops.append(f"{c} {rnd}: two class values to one in release {r1}")
    passed = bool(table) and any(k for v in table.values() for k in v.values())
    detail = "; ".join(f"{k}: {sorted(set(v.values()))}" for k, v in table.items()) + \
             f". Two to one: {'; '.join(drops) if drops else 'none'}"
    return passed, detail, {"counts": table, "two_to_one": drops}


def c4(data):
    ppp = data["ppp"]
    rows = {}
    for rnd in ("2011", "2017", "2021"):
        rels = sorted(ppp.get(("CHN", rnd, "national"), {}))
        if not rels:
            continue
        rel = rels[-1]
        n, ru, ur = (ppp[("CHN", rnd, l)][rel] for l in ("national", "rural", "urban"))
        rows[rnd] = {"release": rel, "national": n, "rural": ru, "urban": ur,
                     "national_over_rural_pct": round(100 * (n / ru - 1), 2),
                     "urban_over_rural_pct": round(100 * (ur / ru - 1), 2),
                     "national_position_rural0_urban1": round((n - ru) / (ur - ru), 4)}
    passed = len(rows) == 3
    detail = "; ".join(f"{r}: national {v['national_over_rural_pct']} % above rural, urban "
                       f"{v['urban_over_rural_pct']} %, national at {v['national_position_rural0_urban1']} "
                       f"of the way to urban" for r, v in rows.items())
    return passed, detail, rows


def c5(data):
    got = {}
    for n, pat in MOVED.items():
        m = re.search(pat, data["texts"].get(n, ""))
        got[n] = None if m is None else m.group(0)
    passed = all(v is not None for v in got.values())
    detail = "; ".join(f"{n}: {v if v else 'not found'}" for n, v in got.items())
    return passed, detail, got


KINDS = {"B134-1": "instrument", "B134-2": "known_answer", "B134-3": "own_reading",
         "B134-4": "own_reading", "B134-5": "own_reading"}
FUNCS = {"B134-1": c1, "B134-2": c2, "B134-3": c3, "B134-4": c4, "B134-5": c5}


def build(data):
    return {n: f(data) for n, f in FUNCS.items()}


def selftest() -> None:
    data = load_all()
    base = build(data)
    assert all(v[0] for v in base.values()), {k: v[1] for k, v in base.items() if not v[0]}
    bad = copy.deepcopy(data)
    k = ("CHN", "2017", "rural")
    last = sorted(bad["ppp"][k])[-1]
    bad["ppp"][k][last] *= 1.01
    assert not c1(bad)[0], "B134-1 must catch an unexplained revision"
    bad = copy.deepcopy(data)
    bad["texts"]["pip_handbook_convert.html"] = "nothing here"
    assert not c2(bad)[0], "B134-2 must catch a missing sentence"
    bad = copy.deepcopy(data)
    bad["ppp"] = {}
    assert not c3(bad)[0], "B134-3 must fail with no table"
    bad = copy.deepcopy(data)
    bad["ppp"] = {k: v for k, v in bad["ppp"].items() if not (k[0] == "CHN" and k[1] == "2021")}
    assert not c4(bad)[0], "B134-4 must fail with a round missing"
    bad = copy.deepcopy(data)
    bad["texts"]["wb_indonesia_poverty_brief.pdf"] = ""
    assert not c5(bad)[0], "B134-5 must fail when the brief says nothing"
    print("selftest ok: all five flags pass on the data and each fails on its planted error")


def main() -> int:
    data = load_all()
    res = build(data)
    crit = []
    for name, (passed, detail, obj) in res.items():
        print(f"{'PASS' if passed else 'FAIL'} {name} [{KINDS[name]}]: {detail}")
        crit.append({"name": name, "kind": KINDS[name], "passed": passed, "detail": detail})
    record = {"stage": "B134", "criteria": crit, "objects": {n: o for n, (_, _, o) in res.items()},
              "config": {"countries": list(COUNTRIES), "rel_tol": REL_TOL}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
