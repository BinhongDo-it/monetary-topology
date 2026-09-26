"""A51 block 2: location demand with leases, five seeds, the levy swept.

Carrier: block 1's (A48's bound cells, the core a location slice of the low tier, R0 1.16,
optional moves 0.02). Leases: a renter keeps the unit it chose for L rounds, optionally at the
rent it signed for. L reads against the carrier's own holding period of 25 rounds: residential
contracts are a thirtieth to a tenth of an owner's tenure, a renter's stay about a fifth, an
open-ended German tenancy close to the tenure itself; so L {1, 5, 25}.

Grid: landlord {public, listed 0.271} x g {0, 0.005} x core share {0.1, 0.3} x s {0.027,
0.083} x lease {L 1; L 5; L 5 rent locked; L 25; L 25 rent locked} x five seeds; the same
again at levy 0.15 and 0.25 (11f).

Checks, each with a planted error that must make it fail (--selftest):
  A51-2  instrument  block 1's structure check on every run (core never built, priced by the
                     premium, one unit per renter, every choice the cheapest affordable)
  A51-4  instrument  every lease holds: a renter kept on a lease sits on the tier and lessor it
                     signed for, pays the signed rent when rents are locked, and is never kept
                     L rounds or more after signing
  A51-5  instrument  L 1 is the block-1 matching, field for field (an implementation check)

Readings (own_reading), per seed, a sign read only where it holds at every seed and levy:
  who lives in the core (the wage earners' share of its tenants), whether it is full, the
  location rent a landlord collects and the one it leaves with tenants, the production
  layer's share; comparisons in COMPARE.

Run from the repo root:
    python experiments/a51_grid.py
    python experiments/a51_grid.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a51_block1  # noqa: E402
from a51_block1 import S_HIGH, S_LOW, split_asset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "a51_grid.json"
SEEDS = tuple(range(5))
LANDLORDS = ("public", "listed 0.271")
GS = (0.0, 0.005)
SHARES = (0.1, 0.3)
SS = (S_LOW, S_HIGH)
LEASES = {"L1": (1, False), "L5": (5, False), "L5 lock": (5, True), "L25": (25, False), "L25 lock": (25, True)}
LEVIES = (0.20, 0.15, 0.25)


def rules(landlord, g, s, lease, levy):
    L, lock = LEASES[lease]
    knob = {} if levy == 0.20 else {"levy_rate": levy}
    return a51_block1.rules_for(landlord, g, s, lease_rounds=L, lease_rent_lock=lock, **knob)


def lease_check(m) -> tuple[bool, list[str]]:
    L = m.rules.lease_rounds
    bad = []
    signed: dict[int, tuple[int, int]] = {}      # node -> (round signed, tier)
    dues: dict[tuple[int, int], set] = {}
    chosen = {(t, i): q for t, i, q, _, _ in m.location_choices}
    events = sorted([(t, 0, i, q, None, None) for (t, i), q in chosen.items()]
                    + [(t, 1, i, q, who, due) for t, i, q, who, due in m.lease_log])
    for t, kind, i, q, who, due in events:
        if kind == 0:
            signed[i] = (t, q)
            continue
        if i not in signed:
            bad.append(f"round {t}: node {i} kept without a lease")
            continue
        t0, q0 = signed[i]
        if q != q0:
            bad.append(f"round {t}: node {i} kept on tier {q}, signed {q0}")
        if t - t0 >= L:
            bad.append(f"round {t}: node {i} kept {t - t0} rounds after signing, lease {L}")
        # every kept entry of one lease pays the same due when rents are locked
        dues.setdefault((i, t0), set()).add(due)
    if m.rules.lease_rent_lock and any(len(v) > 1 for v in dues.values()):
        bad.append("a locked lease paid two different rents")
    return not bad, bad[:5]


def one(args):
    landlord, g, share, s, lease, levy, seed = args
    import warnings
    warnings.filterwarnings("ignore")
    import a47_block3
    m, secs = a47_block3.run(rules(landlord, g, s, lease, levy), seed=seed, asset=split_asset(share))
    s_ok, _ = a51_block1.structure_check(m)
    l_ok, _ = lease_check(m)
    return {"landlord": landlord, "g": g, "share": share, "s": s, "lease": lease, "levy": levy, "seed": seed,
            "seconds": round(secs, 3), "structure_ok": s_ok, "lease_ok": l_ok,
            "evictions": int(m.lease_evictions), **a51_block1.preview_row(m)}


def implementation_twin() -> tuple[bool, list[str]]:
    from a47_block1 import same
    import a47_block3
    d = []
    for ll in LANDLORDS:
        a, _ = a47_block3.run(a51_block1.rules_for(ll, 0.005, S_HIGH), seed=0, rounds=150, asset=split_asset(0.1))
        b, _ = a47_block3.run(a51_block1.rules_for(ll, 0.005, S_HIGH, lease_rounds=1), seed=0, rounds=150,
                              asset=split_asset(0.1))
        d += [f"{ll}: {f}" for f in ("holdings", "units", "price_history", "tenancy", "rent_history",
                                     "location_history") if not same(getattr(a, f), getattr(b, f))]
    return not d, d


KEY = ("landlord", "g", "share", "s")
QTY = ("core_tenants_last50", "employed_share_of_core_tenants", "location_rent_left_with_tenants_per_round",
       "location_rent_collected_per_round", "prod_share", "top_decile", "evictions", "core_households_end")


def by(rows, **k):
    return {x["seed"]: x for x in rows if all(x[a] == b for a, b in k.items())}


def compare(rows) -> dict:
    """Named per-seed differences, for every carrier cell."""
    out = {}
    for ll, g, share, s in itertools.product(LANDLORDS, GS, SHARES, SS):
        cell = dict(landlord=ll, g=g, share=share, s=s)
        base = by(rows, lease="L1", **cell)
        tag = f"{ll} | g {g} | share {share} | s {s}"
        for lease in ("L5", "L5 lock", "L25", "L25 lock"):
            x = by(rows, lease=lease, **cell)
            for q in ("core_tenants_last50", "prod_share", "location_rent_left_with_tenants_per_round"):
                v = [None if x[k][q] is None or base[k][q] is None else round(x[k][q] - base[k][q], 4) for k in SEEDS]
                out[f"{tag} | {lease} - L1 | {q}"] = v
    for g, share, s, lease in itertools.product(GS, SHARES, SS, LEASES):
        pub = by(rows, landlord="public", g=g, share=share, s=s, lease=lease)
        lst = by(rows, landlord="listed 0.271", g=g, share=share, s=s, lease=lease)
        out[f"public - listed | g {g} | share {share} | s {s} | {lease} | prod_share"] = \
            [round(pub[k]["prod_share"] - lst[k]["prod_share"], 4) for k in SEEDS]
    return out


def signs(v):
    return sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in v if x is not None})


def selftest() -> None:
    import a47_block3
    m, _ = a47_block3.run(rules("listed 0.271", 0.005, S_HIGH, "L5 lock", 0.20), seed=0, rounds=80,
                          asset=split_asset(0.1))
    assert lease_check(m)[0] and m.lease_log, "the lease arm must keep renters and pass"
    t, i, q, who, due = m.lease_log[3]
    m.lease_log[3] = (t, i, q + 1, who, due)
    assert not lease_check(m)[0], "A51-4 must catch a renter kept on another tier"
    m, _ = a47_block3.run(rules("listed 0.271", 0.005, S_HIGH, "L5 lock", 0.20), seed=0, rounds=80,
                          asset=split_asset(0.1))
    t, i, q, who, due = m.lease_log[0]
    m.lease_log.append((t + 10, i, q, who, due))
    assert not lease_check(m)[0], "A51-4 must catch a lease kept past its term"
    m, _ = a47_block3.run(rules("listed 0.271", 0.005, S_HIGH, "L5 lock", 0.20), seed=0, rounds=80,
                          asset=split_asset(0.1))
    t, i, q, who, due = m.lease_log[2]
    m.lease_log[2] = (t, i, q, who, due + 0.01)
    assert not lease_check(m)[0], "A51-4 must catch a locked lease paying two rents"
    try:
        replace(a51_block1.rules_for("public", 0.0, 0.0), lease_rounds=5)
    except ValueError:
        pass
    else:
        raise AssertionError("a lease without location demand must be refused")
    print("selftest ok: A51-4 catches a wrong tier, a lease past its term and a locked lease paying two rents; "
          "a lease without location demand is refused")


def main() -> int:
    workers = max(1, (os.cpu_count() or 2) - 1)
    ok5, d5 = implementation_twin()
    print(f"{'PASS' if ok5 else 'FAIL'} A51-5 [instrument]: L 1 equals the block-1 matching" + (f"; {d5}" if d5 else ""))
    jobs = [(ll, g, sh, s, lease, lv, sd) for ll, g, sh, s, lease, lv, sd in
            itertools.product(LANDLORDS, GS, SHARES, SS, LEASES, LEVIES, SEEDS)]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=2))
    print(f"{len(rows)} runs {time.perf_counter() - t0:.1f} s; {workers} workers")
    ok2 = all(r["structure_ok"] for r in rows)
    ok4 = all(r["lease_ok"] for r in rows)
    print(f"{'PASS' if ok2 else 'FAIL'} A51-2 [instrument]: structure holds in {len(rows)} runs")
    print(f"{'PASS' if ok4 else 'FAIL'} A51-4 [instrument]: every lease holds in {len(rows)} runs")

    base = [r for r in rows if r["levy"] == 0.20]
    print("\ncells, levy 0.20, mean over 5 seeds: " + " | ".join(QTY))
    summary = {}
    for ll, g, share, s, lease in itertools.product(LANDLORDS, GS, SHARES, SS, LEASES):
        rs = list(by(base, landlord=ll, g=g, share=share, s=s, lease=lease).values())
        smm = {}
        for q in QTY:
            v = [r[q] for r in rs if r[q] is not None]
            smm[q] = round(float(np.mean(v)), 4) if v else None
        smm["employed_share_min"] = min((r["employed_share_of_core_tenants"] for r in rs
                                         if r["employed_share_of_core_tenants"] is not None), default=None)
        name = f"{ll} | g {g} | share {share} | s {s} | {lease}"
        summary[name] = smm
        print(f"  {name:48s} " + " | ".join(str(smm[q]) for q in QTY))

    comp = {lv: compare([r for r in rows if r["levy"] == lv]) for lv in LEVIES}
    verdict = {}
    for name, v in comp[0.20].items():
        allsigns = set()
        for lv in LEVIES:
            allsigns |= set(signs(comp[lv][name]))
        verdict[name] = {"levy_0.20": v, "signs": sorted(allsigns),
                         "read": len(allsigns) == 1 and "0" not in allsigns}
    print("\ncomparisons read (one sign over 5 seeds x 3 levies), then not read:")
    for name, v in verdict.items():
        if v["read"]:
            print(f"  READ {v['signs'][0]} {name}: {v['levy_0.20']}")
    n_unread = sum(1 for v in verdict.values() if not v["read"])
    print(f"  {n_unread} of {len(verdict)} comparisons not read (sign moves or zero); all in the record")

    record = {"stage": "A51-grid",
              "criteria": [
                  {"name": "A51-5", "kind": "instrument", "passed": ok5, "detail": "L 1 equals the block-1 matching" + (f"; {d5}" if d5 else "")},
                  {"name": "A51-2", "kind": "instrument", "passed": ok2, "detail": f"structure holds in {len(rows)} runs"},
                  {"name": "A51-4", "kind": "instrument", "passed": ok4, "detail": f"every lease holds in {len(rows)} runs"}],
              "rows": rows, "cell_summary": summary, "comparisons": verdict,
              "config": {"landlords": list(LANDLORDS), "g": list(GS), "core_share": list(SHARES), "s": list(SS),
                         "leases": {k: list(v) for k, v in LEASES.items()}, "levies": list(LEVIES),
                         "seeds": list(SEEDS), "R0": a51_block1.R0, "tau_o": a51_block1.TAU_O}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if (ok2 and ok4 and ok5) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
