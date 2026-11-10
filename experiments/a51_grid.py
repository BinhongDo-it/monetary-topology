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
  A51-4  instrument  every lease holds, read against the lease as it was signed: a renter kept
                     on a lease sits on the tier and with the lessor it signed with, is due the
                     signed rent when rents are locked and otherwise the rent the rule gives that
                     round, and is never kept L rounds or more after signing
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


def rent_due_by_rule(m, t: int, q: int, who: int) -> float:
    """The rent the rule gives on tier q in round t, from the histories: the cost price of the
    round for a cost-renting public landlord, otherwise the quote standing when round t collects
    (the close of round t - 1; the opening quote in round 0)."""
    from monetary_topology.housing_rules import LANDLORD
    rate = m.a3.asset.rent_rate
    if who == LANDLORD and m.rules.public_rent_cost:
        return rate * float(m.cost_price_history[t][q])
    if t > 0:
        return rate * float(m.price_history[t - 1][q])
    p0 = np.asarray(m.a3.asset.initial_price, dtype=float).copy()
    if m.rules.core_premium:
        p0[m._core_q] = m.opening_core_price
    return rate * float(p0[q])


def lease_check(m) -> tuple[bool, list[str]]:
    L = m.rules.lease_rounds
    bad = []
    signed: dict[int, tuple[int, int, int, float]] = {}      # node -> (round, tier, lessor, rent) as signed
    choices = {(t, i): q for t, i, q, _, _ in m.location_choices}
    for t, i, q, who, rent in m.lease_signings:
        if choices.get((t, i)) != q:
            bad.append(f"round {t}: node {i} signed for tier {q}, chose {choices.get((t, i))}")
    if L > 1 and len(m.lease_signings) != len(m.location_choices):
        bad.append(f"{len(m.location_choices)} choices, {len(m.lease_signings)} leases signed")
    close = lambda a, b: abs(a - b) <= 1e-12 * max(abs(b), 1e-300)
    events = sorted([(t, 0, i, q, who, rent) for t, i, q, who, rent in m.lease_signings]
                    + [(t, 1, i, q, who, due) for t, i, q, who, due in m.lease_log])
    for t, kind, i, q, who, due in events:
        if kind == 0:
            signed[i] = (t, q, who, due)
            continue
        if i not in signed:
            bad.append(f"round {t}: node {i} kept without a lease")
            continue
        t0, q0, who0, rent0 = signed[i]
        if q != q0:
            bad.append(f"round {t}: node {i} kept on tier {q}, signed {q0}")
        if who != who0:
            bad.append(f"round {t}: node {i} kept with lessor {who}, signed with {who0}")
        if t - t0 >= L:
            bad.append(f"round {t}: node {i} kept {t - t0} rounds after signing, lease {L}")
        want = rent0 if m.rules.lease_rent_lock else rent_due_by_rule(m, t, q, who)
        if not close(due, want):
            bad.append(f"round {t}: node {i} due {due}, the lease gives {want}")
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
       "location_rent_collected_per_round", "commute_saved_per_round", "prod_share", "top_decile", "evictions",
       "core_households_end", "core_tenant_rounds", "core_last_occupied_round", "location_rent_collected_total")


def lock_pairs(rows) -> dict:
    """A rent-locked lease against the same lease unlocked, same cell, levy and seed: which stored
    fields differ. 2 lease lengths x 16 cells x 3 levies x 5 seeds = 480 pairs."""
    idx = {(r["landlord"], r["g"], r["share"], r["s"], r["lease"], r["levy"], r["seed"]): r for r in rows}
    skip = {"seconds", "lease"}
    pairs = differing = 0
    listed, worst = [], 0.0
    whole = ("core_tenant_rounds", "core_last_occupied_round", "location_rent_collected_total",
             "location_rent_left_with_tenants_total", "commute_saved_total")
    whole_only = 0
    for key, a in idx.items():
        if not key[4].endswith(" lock"):
            continue
        b = idx[key[:4] + (key[4][:-5],) + key[5:]]
        pairs += 1
        fields = sorted(k for k in a if k not in skip and a[k] != b[k])
        if fields:
            differing += 1
            worst = max(worst, abs(a["prod_share"] - b["prod_share"]))
            whole_only += int(all(f in whole for f in fields))
            listed.append({"landlord": key[0], "g": key[1], "share": key[2], "s": key[3], "lease": key[4],
                           "levy": key[5], "seed": key[6], "fields": fields,
                           "prod_share_locked_minus_unlocked": round(a["prod_share"] - b["prod_share"], 4)})
    return {"pairs": pairs, "differing": differing, "differing_in_whole_run_totals_only": whole_only,
            "max_abs_prod_share_diff": round(worst, 4), "list": listed}


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
    # every renewal of one lease moved to the same wrong rent: no two rents differ, the signed one does
    m, _ = a47_block3.run(rules("listed 0.271", 0.005, S_HIGH, "L5 lock", 0.20), seed=0, rounds=80,
                          asset=split_asset(0.1))
    t0, i0 = m.lease_signings[0][:2]
    mine = [k for k, (t, i, q, who, due) in enumerate(m.lease_log) if i == i0 and t0 < t < t0 + 5]
    assert mine, "the first lease must have renewals"
    for k in mine:
        t, i, q, who, due = m.lease_log[k]
        m.lease_log[k] = (t, i, q, who, due + 0.01)
    assert not lease_check(m)[0], "A51-4 must catch a lease whose every renewal pays the same wrong rent"
    m, _ = a47_block3.run(rules("listed 0.271", 0.005, S_HIGH, "L5 lock", 0.20), seed=0, rounds=80,
                          asset=split_asset(0.1))
    t, i, q, who, due = m.lease_log[3]
    m.lease_log[3] = (t, i, q, who + 1, due)
    assert not lease_check(m)[0], "A51-4 must catch a renter kept with another lessor"
    m, _ = a47_block3.run(rules("listed 0.271", 0.005, S_HIGH, "L5", 0.20), seed=0, rounds=80,
                          asset=split_asset(0.1))
    assert lease_check(m)[0], "the unlocked lease arm must pass"
    t, i, q, who, due = m.lease_log[3]
    m.lease_log[3] = (t, i, q, who, due * 1.01)
    assert not lease_check(m)[0], "A51-4 must catch an unlocked renewal not at the round's rent"
    # the lock pairs
    a = {"landlord": "x", "g": 0.0, "share": 0.1, "s": 0.027, "lease": "L5", "levy": 0.2, "seed": 0, "seconds": 1.0,
         "prod_share": 0.2, "core_tenant_rounds": 5}
    b = dict(a, lease="L5 lock", seconds=2.0)
    assert lock_pairs([a, b])["differing"] == 0
    assert lock_pairs([a, dict(b, core_tenant_rounds=6)])["differing_in_whole_run_totals_only"] == 1
    assert lock_pairs([a, dict(b, prod_share=0.21)])["max_abs_prod_share_diff"] == 0.01
    try:
        replace(a51_block1.rules_for("public", 0.0, 0.0), lease_rounds=5)
    except ValueError:
        pass
    else:
        raise AssertionError("a lease without location demand must be refused")
    print("selftest ok: A51-4 catches a wrong tier, a lease past its term, a locked lease paying two rents, a "
          "lease whose every renewal pays the same wrong rent, another lessor and an unlocked renewal off the "
          "round's rent; the lock pairs count a differing field; a lease without location demand is refused")


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
        # the same share with tenant-rounds as the denominator, pooled over seeds
        tr = sum(r["core_tenant_rounds_last50"] for r in rs)
        smm["employed_share_by_tenant_rounds"] = round(sum(r["core_employed_tenant_rounds_last50"] for r in rs) / tr, 4) if tr else None
        smm["core_tenant_rounds_last50"] = int(tr)
        for q in ("core_choices", "core_choices_plain_full", "core_choices_no_wage", "core_choices_dear",
                  "core_choices_dear_plain_full"):
            smm[q] = int(sum(r[q] for r in rs))
        fd = [r["first_dear_core_choice_round"] for r in rs if r["first_dear_core_choice_round"] is not None]
        smm["first_dear_core_choice_round"] = sorted(fd)
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

    lp = lock_pairs(rows)
    print(f"\nrent locked against unlocked, same lease length: {lp['pairs']} pairs, {lp['differing']} differ in a stored "
          f"field ({lp['differing_in_whole_run_totals_only']} of them in whole-run totals only); largest gap in the "
          f"production-layer share {lp['max_abs_prod_share_diff']}")
    for x in lp["list"][:12]:
        print(f"  {x['landlord']} g {x['g']} share {x['share']} s {x['s']} {x['lease']} levy {x['levy']} seed {x['seed']}: "
              f"{len(x['fields'])} fields, share {x['prod_share_locked_minus_unlocked']:+.4f}")

    record = {"stage": "A51-grid",
              "criteria": [
                  {"name": "A51-5", "kind": "instrument", "passed": ok5, "detail": "L 1 equals the block-1 matching" + (f"; {d5}" if d5 else "")},
                  {"name": "A51-2", "kind": "instrument", "passed": ok2, "detail": f"structure holds in {len(rows)} runs"},
                  {"name": "A51-4", "kind": "instrument", "passed": ok4, "detail": f"every lease holds in {len(rows)} runs"}],
              "rows": rows, "cell_summary": summary, "comparisons": verdict, "lock_pairs": lp,
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
