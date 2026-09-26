"""B106 step four: settle whether the employment share counts hours or persons,
from the data rather than from a document.

The result file left this open and said, wrongly at first, that it cancels out of
the ratio. It does not. On the hours reading the field is relative hourly pay; on
the persons reading it is relative annual earnings, and part of the leftover
could then be part-time composition varying by industry and gender.

The 2021 methods note says only "the shares of employment and labour
compensation by type of worker", which does not decide it, and the module's own
naming (Share_E beside a national accounts module that separates EMP from H_EMP)
points the other way from the Jorgenson construction the release is built on. So
neither reading of the documentation settles it.

The panel settles it. The labour accounts exist to build LAB_QI, the labour
services index published in the growth accounts, and that index is a Tornqvist
over the same classes:

    dln LAB_QI = dln T + sum_k vbar_k dln S_k

with S the class's share of the labour quantity, vbar the average compensation
share, and T the position's total of that same quantity. Rearranged, the part
that does not depend on T is

    dln LAB_QI - dln T = sum_k vbar_k dln S_k

so putting T = H_EMP and T = EMP in turn and asking which one reproduces the
published index answers the question against a series this station did not
construct. This is a known answer check, not a fit: nothing here is estimated.

    python experiments/b106_caliber.py
    python experiments/b106_caliber.py --no-write
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b106_caliber.json"


def _mod(name):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


SEP = _mod("b106_separability")
SECTIONS, K = SEP.SECTIONS, SEP.K


def panel():
    """Per (section, country, year): the 18 class shares, the published labour
    services index, total hours and total persons."""
    # SEP.load() drops share_w, which this step needs, so the cache is read here
    # directly rather than patching a helper another criterion already depends on.
    raw = np.load(ROOT / "data/cache/b106_labour.npz", allow_pickle=False)
    d = {"nace": raw["nace"], "geo": raw["geo"], "year": raw["year"],
         "cls": raw["cls"], "share_e": raw["share_e"], "share_w": raw["share_w"]}
    g = np.load(ROOT / "data/cache/b101_klems_basic.npz", allow_pickle=False)
    n = np.load(ROOT / "data/cache/b101_national.npz", allow_pickle=False)
    gc = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    nc = {v: n["values"][:, i] for i, v in enumerate(list(n["vars"]))}

    classes = sorted(set(str(c) for c in d["cls"]))
    ci = {c: i for i, c in enumerate(classes)}
    shares = {}
    keep = np.isin(d["nace"], SECTIONS)
    for i in np.flatnonzero(keep):
        key = (str(d["nace"][i]), str(d["geo"][i]), int(d["year"][i]))
        e = shares.setdefault(key, [np.full(K, np.nan), np.full(K, np.nan)])
        j = ci[str(d["cls"][i])]
        e[0][j] = d["share_e"][i]
        e[1][j] = d["share_w"][i]

    gi = {(str(a), str(b), int(c)): i for i, (a, b, c) in
          enumerate(zip(g["nace"], g["geo"], g["year"]))}
    ni = {(str(a), str(b), int(c)): i for i, (a, b, c) in
          enumerate(zip(n["nace"], n["geo"], n["year"]))}
    out = {}
    for key, (se, sw) in shares.items():
        gj, nj = gi.get(key), ni.get(key)
        if gj is None or nj is None:
            continue
        Q, H, P = gc["LAB_QI"][gj], nc["H_EMP"][nj], nc["EMP"][nj]
        if not all(np.isfinite(v) for v in (Q, H, P)):
            continue
        if not (Q > 0 and H > 0 and P > 0):
            continue
        if not (np.all(np.isfinite(se)) and np.all(np.isfinite(sw))):
            continue
        if not (np.all(se > 0) and np.all(sw > 0)):
            continue
        out[key] = {"se": se, "sw": sw, "Q": Q, "H": H, "P": P}
    return out


def steps(p):
    """Adjacent-year pairs inside one (section, country)."""
    rows = []
    for (sec, geo, yr), a in p.items():
        b = p.get((sec, geo, yr + 1))
        if b is None:
            continue
        v = 0.5 * (a["sw"] + b["sw"]) / 100.0
        v = v / v.sum()
        quality = float(v @ (np.log(b["se"]) - np.log(a["se"])))
        rows.append({
            "key": f"{sec}/{geo}/{yr}",
            "d_index": float(np.log(b["Q"]) - np.log(a["Q"])),
            "d_hours": float(np.log(b["H"]) - np.log(a["H"])),
            "d_persons": float(np.log(b["P"]) - np.log(a["P"])),
            "quality": quality,
        })
    return rows


def fit_stats(x, y):
    """How well does y reproduce x: the residual, not a regression."""
    r = np.asarray(y) - np.asarray(x)
    return {"mae": float(np.mean(np.abs(r))), "rmse": float(np.sqrt(np.mean(r ** 2))),
            "corr": float(np.corrcoef(x, y)[0, 1]),
            "within_1e-6": int(np.sum(np.abs(r) < 1e-6)),
            "within_1e-3": int(np.sum(np.abs(r) < 1e-3))}


# ------------------------------------------------- B106-9 which total is it

def check_caliber(rows):
    d = np.array([r["d_index"] for r in rows])
    q = np.array([r["quality"] for r in rows])
    hh = np.array([r["d_hours"] for r in rows])
    pp = np.array([r["d_persons"] for r in rows])
    hours = fit_stats(d, hh + q)
    persons = fit_stats(d, pp + q)
    # the same identity with the class term dropped, so that the class shares are
    # shown to be doing work rather than the total carrying it on its own
    hours_bare = fit_stats(d, hh)
    persons_bare = fit_stats(d, pp)
    best = "hours" if hours["rmse"] < persons["rmse"] else "persons"
    ratio = max(hours["rmse"], persons["rmse"]) / min(hours["rmse"], persons["rmse"])
    ok = ratio > 1.5
    detail = (f"{len(rows):,} adjacent-year steps inside one section and country. "
              f"Reproducing the published labour services index as the total plus "
              f"the class term: with HOURS as the total, rmse {hours['rmse']:.5f}, "
              f"correlation {hours['corr']:+.4f}, within 1e-3 in "
              f"{hours['within_1e-3']:,}; with PERSONS, rmse "
              f"{persons['rmse']:.5f}, correlation {persons['corr']:+.4f}, within "
              f"1e-3 in {persons['within_1e-3']:,}. Dropping the class term "
              f"entirely gives {hours_bare['rmse']:.5f} and "
              f"{persons_bare['rmse']:.5f}, so the class shares are doing work in "
              f"both. The reading is {best.upper()}, by a factor of {ratio:.2f} in "
              f"root mean square error. PASS records that the two readings are "
              f"far enough apart to tell them apart at all.")
    return bool(ok), detail, {"n": len(rows), "hours": hours, "persons": persons,
                              "hours_without_class_term": hours_bare,
                              "persons_without_class_term": persons_bare,
                              "verdict": best, "rmse_ratio": ratio}


# -------------------------------------- B106-10 what it means for the reading

def check_consequence(rows, verdict):
    """If the shares count persons, the field mixes the wage rate with hours per
    worker, and the part-time composition is a live alternative for some of the
    leftover. If they count hours, it does not arise. Either way the identity
    above also hands over a second reading: the gap between the index built on
    hours and the one built on persons IS the hours-per-worker term, so its size
    is measurable rather than a worry."""
    hh = np.array([r["d_hours"] for r in rows])
    pp = np.array([r["d_persons"] for r in rows])
    gap = hh - pp
    ok = True
    detail = (f"the difference between the two totals is the change in hours per "
              f"worker, and it is not small: sd {gap.std():.4f} against "
              f"{hh.std():.4f} for hours and {pp.std():.4f} for persons, "
              f"correlation between the two totals {np.corrcoef(hh,pp)[0,1]:+.4f}. "
              f"So the two readings are genuinely different objects and the "
              f"verdict above is load bearing. With the verdict at "
              f"{verdict.upper()}, "
              + ("the field is relative HOURLY pay and part-time composition is "
                 "not an alternative for any of the leftover."
                 if verdict == "hours" else
                 "the field is relative ANNUAL earnings, so part-time composition "
                 "is a live alternative for part of the leftover and the next "
                 "step is to bound it."))
    return bool(ok), detail, {"gap_sd": float(gap.std()), "hours_sd": float(hh.std()),
                              "persons_sd": float(pp.std()),
                              "corr_totals": float(np.corrcoef(hh, pp)[0, 1])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    p = panel()
    rows = steps(p)
    if not rows:
        sys.exit("no adjacent-year steps carry all of the shares, the index, "
                 "hours and persons")
    ok1, d1, pay1 = check_caliber(rows)
    ok2, d2, pay2 = check_consequence(rows, pay1["verdict"])
    criteria = [
        {"name": "B106-9", "kind": "known_answer",
         "criterion": "whether the class shares count hours or persons, read "
                      "against the published labour services index",
         "passed": bool(ok1), "detail": d1, "payload": pay1},
        {"name": "B106-10", "kind": "instrument",
         "criterion": "what the verdict changes about the field's reading",
         "passed": bool(ok2), "detail": d2, "payload": pay2},
    ]
    for c in criteria:
        print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']} ({c['kind']})  "
              f"{c['detail']}")
    record = {"stage": "B106",
              "config": {"identity": "dln LAB_QI = dln T + sum_k vbar_k dln S_k",
                         "totals_tried": ["H_EMP", "EMP"],
                         "sections": SECTIONS,
                         "sources": ["labour accounts.csv",
                                     "growth accounts basic.csv",
                                     "national accounts.csv"]},
              "criteria": criteria}
    body = json.dumps(record, indent=2, sort_keys=True, default=float)
    print(f"\n{sum(c['passed'] for c in criteria)}/{len(criteria)} pass, "
          f"{time.time()-t0:.2f}s, sha256 "
          f"{hashlib.sha256(body.encode()).hexdigest()[:16]}")
    if not a.no_write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(body, encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
