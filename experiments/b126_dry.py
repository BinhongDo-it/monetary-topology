"""B126 dry-wine check: does a dry white fall on the same density axis as the sweet wines?

Reads data/b126/parsed/ and writes results/b126_dry.json. The main readings exclude Y d'Yquem
(a dry white, Bordeaux appellation) from the carrier by name; this script reads it on its own,
with the cross-house jump reading of experiments/b126_readings.py (B126-7), and puts Yquem's
sweet wine beside it as the thick-end reference. House levels are fitted on every wine read
here, the dry white included.

Criterion (`11d`):
  B126-15  own_reading  Y d'Yquem, cross-house pairs net of house level: density and the unit
                        median jump rank-correlate negatively at every one of the eight settings
                        (sizes x min pairs x clean). Three states, mapped in R.VERDICT (`11c`)

Run from the repo root:
    python experiments/b126_dry.py
    python experiments/b126_dry.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b126_readings as R  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

OUT = R.ROOT / "results" / "b126_dry.json"
DRY = "chateau-dyquem-y-bordeaux"
SWEET = "chateau-dyquem-premier-cru-superieur-sauternes"
SCAN = {"formats": ["750", "all"], "min_pairs": [3, 5], "clean": [0.0, 3.0]}
PERMS = 2000


def read_wine(lots, cov, wine: str) -> list[dict]:
    out = []
    for fm, mp, cl in itertools.product(SCAN["formats"], SCAN["min_pairs"], SCAN["clean"]):
        cfg = {"formats": fm, "lag": 3, "min_pairs": mp, "clean": cl}
        us = [u for u in R.units_from(lots, cov, cfg, "cross") if len(u["pairs"]) >= mp and u["slug"] == wine]
        row = {"cfg": cfg, "units": len(us), "rho": None, "p": None,
               "density_range": [min(u["density"] for u in us), max(u["density"] for u in us)] if us else None}
        if len(us) >= 5:
            x = [u["density"] for u in us]
            y = [st.median(p[0] for p in u["pairs"]) for u in us]
            r0 = spearmanr(x, y).statistic
            rng = random.Random(9)
            h = 0
            for _ in range(PERMS):
                xs = x[:]
                rng.shuffle(xs)
                h += spearmanr(xs, y).statistic <= r0
            row.update(rho=float(r0), p=(h + 1) / (PERMS + 1))
        out.append(row)
    return out


def read(lots, cov) -> dict:
    saved = dict(R.EXCLUDE)
    try:
        R.EXCLUDE.pop(DRY, None)
        R._CLEAN_CACHE.clear()
        dry, sweet = read_wine(lots, cov, DRY), read_wine(lots, cov, SWEET)
    finally:
        R.EXCLUDE.clear()
        R.EXCLUDE.update(saved)
        R._CLEAN_CACHE.clear()
    state = R.state_of([x["rho"] for x in dry])
    det = "; ".join(f"{x['cfg']['formats']}/k{x['cfg']['min_pairs']}/c{x['cfg']['clean']:g} {x['rho']:+.3f} (n={x['units']}, p {x['p']:.3f})"
                    for x in dry if x["rho"] is not None)
    crit = [{"name": "B126-15", "kind": "own_reading",
             "statement": "Y d'Yquem (dry white), cross-house pairs net of house level: thinner vintages jump further",
             "passed": R.VERDICT[state], "state": state, "state_map": R.VERDICT, "detail": det}]
    return {"dry": dry, "sweet_reference": sweet, "criteria": crit}


def report(r: dict) -> None:
    for name, rows in (("Y d'Yquem (dry)", r["dry"]), ("Yquem (sweet, reference)", r["sweet_reference"])):
        print(name)
        for x in rows:
            c = x["cfg"]
            rho = f"{x['rho']:+.3f} p {x['p']:.3f}" if x["rho"] is not None else "n/a"
            dr = f"{x['density_range'][0]:.2f}-{x['density_range'][1]:.2f}/yr" if x["density_range"] else ""
            print(f"  {c['formats']:>3} k{c['min_pairs']} c{c['clean']:g}: n={x['units']:>3}  rho {rho}  density {dr}")
    for c in r["criteria"]:
        print(f"\n{c['name']} {c['kind']} {c['passed']}  {c['state']}")


def run() -> int:
    lots = json.loads((R.PARSED / "lots.json").read_text(encoding="utf-8"))
    cov = json.loads((R.PARSED / "coverage.json").read_text(encoding="utf-8"))
    r = read(lots, cov)
    report(r)
    rec = {"stage": "B126", "arm": "dry",
           "config": {"scan": SCAN, "lag": 3, "perms": PERMS, "wine": DRY, "reference": SWEET,
                      "house_levels": "fitted on every wine read here, the dry white included",
                      "source": "data/b126/parsed/ via experiments/b126_parse.py"},
           **R.rnd(r)}
    OUT.write_text(json.dumps(rec, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT}")
    return 0


def selftest() -> int:
    """The verdict is computed from the rho list (`11f`): each state is seeded."""
    checks = [
        ("all negative reads True", R.VERDICT[R.state_of([-0.3, -0.1, -0.2])] is True),
        ("all positive reads False", R.VERDICT[R.state_of([0.3, 0.1])] is False),
        ("mixed reads no verdict", R.VERDICT[R.state_of([-0.3, 0.1])] is None),
        ("no rho reads no verdict", R.VERDICT[R.state_of([None, None])] is None),
    ]
    saved = dict(R.EXCLUDE)
    try:
        R.EXCLUDE.pop(DRY, None)
        checks.append(("the dry white is readable inside the block", DRY not in R.EXCLUDE))
    finally:
        R.EXCLUDE.clear()
        R.EXCLUDE.update(saved)
    checks.append(("the exclusion list is restored after the block", DRY in R.EXCLUDE))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    return selftest() if ap.parse_args().selftest else run()


if __name__ == "__main__":
    sys.exit(main())
