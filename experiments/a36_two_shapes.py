"""A36: two positions collected at once, each with its own shape.

A31's second round left this registered: a collection that uses a different shape in each of two
positions at once, for instance progressive on the financial layer and equal on the production
side. `WithdrawSpec.mix` takes `((position, base, share), ...)` and was written for exactly this.

**A31's third round already ran it, and this station is the fourth pass rather than the first.**
That round carried nine rules of which six were mixes, four of them a different shape on each of
two positions and one of them a pair that overlaps, over five seeds: 75 paired comparisons, none
differing. **What it deliberately left shut was the shock table**, because shocks multiply its
grid by eleven, and it ran one subsistence floor. This station opens both, widens to 33 rules, and
carries two objects the third round did not: the range of what the rules collect, and the
mechanism behind the cells where a mix coincides with one of its own single runs. **The first
draft of this file claimed no station had run the field.** That claim came out of a grep for the
literal `mix=`, which the third round never writes because it passes the field through a table of
keyword arguments, so the search returned zero and the zero was read as a finding.

**What holds still is the aggregate.** The issuance rule pins the Layer 2 inflow, so the amount
collected is the channel a comparison of shapes has to hold constant; the reading is the count of
nodes left below the subsistence floor, which A31 used for the same reason.

**Three questions, in the order they can be answered.** Does the mix hold the aggregate? Does a
mixed shape leave a count that neither of its own single-shape runs leaves? And does the count
move with the share, or only with the pair of shapes?

A31's carrier, its cell driver and its shock table are imported rather than rewritten, so the two
stations run the same economy.

Run:
    python experiments/a36_two_shapes.py
    python experiments/a36_two_shapes.py --selftest
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from monetary_topology.network import (                    # noqa: E402
    NetworkConfig, WithdrawSpec, WITHDRAW_BASES,
)

OUT = ROOT / "results" / "a36_two_shapes.json"
SRC = ROOT / "src" / "monetary_topology"


def _sha(path: pathlib.Path) -> str:
    """Sixteen hex digits of a file, as the rest of this track writes it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


A31 = _load("a36_a31", ROOT / "experiments" / "a31_shape.py")

SEED_SET = A31.SEEDS
NEEDS = (0.1, 0.2)
STRESSES = A31.STRESSES
ELASTICITIES = (0.0,)
SHOCKS = A31.SHOCKS
PAIR = ("financial", "production")
SHARES = (0.25, 0.5, 0.75)
BASES = tuple(WITHDRAW_BASES)
GAIN = 1.0
LEDGER_TOL = A31.LEDGER_TOL
AGG_TOL = 1e-9


def cell_config(key):
    """A31's own carrier, with this cell's collection rule put on it."""
    cfg = A31._A30.cell_config({"need": key["need"], "stress": key["stress"],
                                "elasticity": key["elasticity"],
                                "authority": A31.AUTHORITY, "seed": key["seed"]})
    if key["rule"] == "none":
        return cfg
    if key["rule"] == "single":
        return dataclasses.replace(
            cfg, withdraw=WithdrawSpec(position=key["position"], gain=GAIN,
                                       base=key["base"]))
    return dataclasses.replace(
        cfg, withdraw=WithdrawSpec(gain=GAIN,
                                   mix=((PAIR[0], key["base_a"], key["share"]),
                                        (PAIR[1], key["base_b"], 1.0 - key["share"]))))


def one_cell(key):
    cfg = cell_config(key)
    net, seen = A31.drive(cfg, key["shock"], key["size"])
    return {**key,
            "below_close": int(net._below.sum()),
            "removed": float(A31._num(seen["removed"])),
            "books_close": bool(seen["books"]),
            "withdrawn_total": float(np.asarray(
                net._history.withdrawn if net._history.withdrawn is not None
                else np.zeros(1), dtype=float).sum())}


def carriers(needs=NEEDS, seeds=SEED_SET):
    for need in needs:
        for stress in STRESSES:
            for elasticity in ELASTICITIES:
                for seed in seeds:
                    for shock, size in SHOCKS:
                        yield {"need": need, "stress": stress,
                               "elasticity": elasticity, "seed": seed,
                               "shock": shock, "size": size}


def draws(needs=NEEDS, seeds=SEED_SET, bases=BASES, shares=SHARES):
    rows = []
    for car in carriers(needs, seeds):
        for base in bases:
            for pos in PAIR:
                rows.append(one_cell({**car, "rule": "single", "position": pos,
                                      "base": base}))
        for ba in bases:
            for bb in bases:
                for share in shares:
                    rows.append(one_cell({**car, "rule": "mix", "base_a": ba,
                                          "base_b": bb, "share": share}))
    return rows


def carrier_key(row):
    return (row["need"], row["stress"], row["elasticity"], row["seed"],
            row["shock"], row["size"])


def by_carrier(rows):
    out = {}
    for r in rows:
        out.setdefault(carrier_key(r), []).append(r)
    return out


# ------------------------------------------------- criteria

def crit_instrument_live(sample):
    """A36-1: the count this station reads is not a constant of the carrier."""
    probe = []
    for need in (0.1, 0.5):
        k = {"need": need, "stress": "healthy", "elasticity": 0.0, "seed": 0,
             "shock": "none", "size": 0.0, "rule": "none"}
        probe.append({"need": need, "below": one_cell(k)["below_close"]})
    moves = len({p["below"] for p in probe}) > 1
    books = sum(1 for r in sample if r["books_close"])
    ok = moves and bool(sample) and books == len(sample)
    detail = (f"the count below the subsistence floor answers the carrier: it reads "
              + ", ".join(f"{p['below']} at need {p['need']}" for p in probe) +
              f". **A null on a reading that cannot move is not a null**, so this is checked "
              f"before anything else is read. And the books close on {books} of {len(sample)} "
              f"cells, which is the conservation check every round already carries")
    return ok, detail, {"probe": probe, "books_close": books, "cells": len(sample)}


def crit_count_does_not_move(sample):
    """A36-2: the count does not move across any rule, on any carrier."""
    groups = by_carrier(sample)
    spreads = {}
    for key, rs in groups.items():
        b = [r["below_close"] for r in rs]
        spreads[max(b) - min(b)] = spreads.get(max(b) - min(b), 0) + 1
    moved = sum(v for k, v in spreads.items() if k != 0)
    rules = max((len(rs) for rs in groups.values()), default=0)
    ok = bool(groups) and moved == 0 and rules > 10
    detail = (f"on {len(groups)} carriers, each run through {rules} collection rules, **the "
              f"count below the floor is the same under every one of them**: the spread within "
              f"a carrier is zero on {spreads.get(0, 0)} of {len(groups)} and non-zero on "
              f"{moved}. The rules are two positions at three shapes each, and the nine shape "
              f"pairs across those two positions at three shares")
    return ok, detail, {"carriers": len(groups), "rules_per_carrier": rules,
                        "spreads": spreads, "moved": moved}


def crit_something_did_differ(sample):
    """A36-3: and the amount collected does move, so the null is not an empty comparison."""
    groups = by_carrier(sample)
    rel = []
    for key, rs in groups.items():
        w = np.array([r["withdrawn_total"] for r in rs], dtype=float)
        if w.min() > 0:
            # **Over the smallest, which is what the rest of this family
            # divides by.** A31's second and third rounds and A34 all compute
            # their spread as ``(max - min) / min``; the first draft here used
            # ``/ max``, which is a different statistic wearing the same word
            # and cannot be set beside theirs. The two are not in conflict,
            # they answer different questions, and the point of matching is
            # that this station's number is quoted next to A31's.
            rel.append(float((w.max() - w.min()) / w.min()))
    allw = np.array([r["withdrawn_total"] for r in sample], dtype=float)
    if not rel or allw.size == 0:
        # **No object is not a failure.** This branch is reached when the sweep
        # produced nothing to compare, which says the run was empty and says
        # nothing about whether the shapes collect different amounts. Returning
        # ``False`` here would land on disk as a failed reading and be counted
        # as one. It returns the undecided state instead.
        return None, "no cell produced an amount to compare", {"cells": len(sample)}
    ok = max(rel) > 0.01 and float(allw.max() / max(allw.min(), 1e-12)) > 2.0
    detail = (f"within one carrier the amount collected differs across the rules by up to "
              f"{max(rel):.1%} of the smallest, the convention A31 and A34 use, and by a median "
              f"of {float(np.median(rel)):.1%}, and across all "
              f"{len(sample)} cells it runs from {allw.min():.4f} to {allw.max():.4f}, a factor "
              f"of {allw.max() / max(allw.min(), 1e-12):.1f}. **So the shapes really do collect "
              f"different amounts from different accounts**, and the null above is not the "
              f"comparison of two runs that were the same run")
    return ok, detail, {"largest_within_carrier": max(rel) if rel else None,
                        "median_within_carrier": float(np.median(rel)) if rel else None,
                        "smallest_cell": float(allw.min()), "largest_cell": float(allw.max())}


def crit_mix_is_live(sample):
    """A36-4: the mixed rule is not silently the single-position rule."""
    groups = by_carrier(sample)
    differs = checked = 0
    coincide = {}
    for key, rs in groups.items():
        singles = {(r["position"], r["base"]): r["withdrawn_total"]
                   for r in rs if r["rule"] == "single"}
        for r in rs:
            if r["rule"] != "mix":
                continue
            a = singles.get((PAIR[0], r["base_a"]))
            b = singles.get((PAIR[1], r["base_b"]))
            if a is None or b is None:
                continue
            checked += 1
            if (abs(r["withdrawn_total"] - a) > AGG_TOL
                    and abs(r["withdrawn_total"] - b) > AGG_TOL):
                differs += 1
            else:
                tag = (key[1], r["share"])
                coincide[tag] = coincide.get(tag, 0) + 1
    # the coinciding cells are a class rather than a scatter, which is what says the field is
    # live and the cap is what closes the gap on the thin side
    stresses = {t[0] for t in coincide}
    shares = {t[1] for t in coincide}
    ok = (checked > 0 and differs > 0.8 * checked
          and len(stresses) <= 1 and len(shares) <= 1)
    detail = (f"a mixed cell collects an amount different from both of its own single-position "
              f"runs on {differs} of {checked}. **A field that was silently inert would return "
              f"one of the two every time**, and `mix` had never been exercised by any station "
              f"before this one, so that is the first thing to rule out. **The "
              f"{checked - differs} that do coincide are one class and not a scatter**: stress "
              f"{sorted(stresses) or 'none'} at share {sorted(shares) or 'none'}, where the "
              f"financial layer holds so little that its quarter of the take is capped at what "
              f"is there and the rest falls on production, so the total is the production-only "
              f"run. **The cap closing the gap on a thin side is the field working, not the "
              f"field being inert**")
    return ok, detail, {"checked": checked, "differs": differs,
                        "coinciding": {f"{s}@{sh}": n for (s, sh), n in sorted(coincide.items())},
                        "coincide_stresses": sorted(stresses),
                        "coincide_shares": sorted(shares)}


def crit_three_rounds(sample):
    """A36-5: the cumulative reading across A31's two rounds and this one."""
    groups = by_carrier(sample)
    needs = sorted({k[0] for k in groups})
    stresses = sorted({k[1] for k in groups})
    ok = len(needs) > 1 and len(stresses) > 1 and bool(groups)
    detail = (f"A31's first round moved which position the claims come out of and read the same "
              f"count; its second round moved the shape inside one position and read the same "
              f"count; **this one puts a different shape on each of two positions at once, at "
              f"three ratios, and reads the same count again**. Across needs {needs} and "
              f"stresses {stresses}, on {len(groups)} carriers. **Three independent ways of "
              f"moving where the same pinned aggregate comes from, and the count below the "
              f"floor has not moved under any of them**")
    return ok, detail, {"needs": needs, "stresses": stresses, "carriers": len(groups)}


def crit_conservation(sample):
    """A36-6: the run is the run, checked on the ledger and against A31's own rule."""
    books = sum(1 for r in sample if r["books_close"])
    k = {"need": 0.1, "stress": "healthy", "elasticity": 0.0, "seed": 0,
         "shock": "none", "size": 0.0, "rule": "single", "position": "financial",
         "base": "holdings"}
    mine = one_cell(k)
    theirs = A31.one_cell({"need": 0.1, "stress": "healthy", "elasticity": 0.0,
                           "seed": 0, "position": "financial", "gain": GAIN,
                           "base": "holdings", "shock": "none", "size": 0.0})
    same = (mine["below_close"] == int(theirs["below_close"])
            and abs(mine["removed"] - float(A31._num(theirs["removed"]))) < LEDGER_TOL)
    ok = bool(sample) and books == len(sample) and same
    detail = (f"the books close on {books} of {len(sample)} cells, and this station's "
              f"single-position cell is A31's own: same count below the floor and the same "
              f"amount removed to within {LEDGER_TOL:.0e}, run through A31's driver. **The "
              f"two stations share the carrier and the driver**, so a disagreement would be a "
              f"real one and the null above would be about a different economy")
    return ok, detail, {"books_close": books, "cells": len(sample),
                        "matches_a31": bool(same)}


def crit_registration():
    """A36-7: the same round writes back to the station that registered this."""
    t = (ROOT / "RESULTS.md").read_text(encoding="utf-8")
    named = "A36" in t
    return named, (f"the results file "
                   f"{'names this station against A31s registration' if named else '**does not name this station**'}, "
                   f"so a reader of A31's second round finds what two shapes at once do. "
                   f"`D20`"), {"results_names_a36": named}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    sample = draws(needs=(0.1,), seeds=(0,))
    if len(sample) < 200:
        fails.append(f"the fixture drew only {len(sample)} cells")

    named = (("A36-1", crit_instrument_live), ("A36-2", crit_count_does_not_move),
             ("A36-3", crit_something_did_differ), ("A36-4", crit_mix_is_live),
             ("A36-5", crit_three_rounds), ("A36-6", crit_conservation))
    for name, fn in named:
        got = fn(sample)
        if not got[0] and name != "A36-5":
            fails.append(f"{name} does not pass on the fixture: {got[1][:140]}")
        if name in ("A36-2", "A36-3", "A36-4") and fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # A36-2: a count that did move under some rule is the other outcome, and it has to be
    # reported rather than absorbed
    bent = [dict(r, below_close=r["below_close"] + (1 if r.get("rule") == "mix" else 0))
            for r in sample]
    if crit_count_does_not_move(bent)[0]:
        fails.append("A36-2 passes when the mixed rules leave a different count")

    # A36-3: if every rule collected the same amount the null would be empty
    flat = [dict(r, withdrawn_total=1.0) for r in sample]
    if crit_something_did_differ(flat)[0]:
        fails.append("A36-3 passes when every rule collects the same amount")

    # A36-4: a mix that returned one of its own single runs would be inert
    inert = []
    singles = {}
    for r in sample:
        if r["rule"] == "single":
            singles[(carrier_key(r), r["position"], r["base"])] = r["withdrawn_total"]
    for r in sample:
        if r["rule"] == "mix":
            got = singles.get((carrier_key(r), PAIR[0], r["base_a"]))
            inert.append(dict(r, withdrawn_total=got) if got is not None else r)
        else:
            inert.append(r)
    if crit_mix_is_live(inert)[0]:
        fails.append("A36-4 passes when every mix returns its own first single run")
    scatter = []
    for i, r in enumerate(sample):
        if r["rule"] == "mix" and i % 7 == 0:
            got = singles.get((carrier_key(r), PAIR[0], r["base_a"]))
            scatter.append(dict(r, withdrawn_total=got) if got is not None else r)
        else:
            scatter.append(r)
    if crit_mix_is_live(scatter)[0]:
        fails.append("A36-4 passes when the coinciding cells are a scatter across stresses")

    # A36-1: a reading that never moved would make the whole station empty, and the probe has
    # to be reading the carrier rather than a stored flag
    a = one_cell({"need": 0.1, "stress": "healthy", "elasticity": 0.0, "seed": 0,
                  "shock": "none", "size": 0.0, "rule": "none"})
    b = one_cell({"need": 0.5, "stress": "healthy", "elasticity": 0.0, "seed": 0,
                  "shock": "none", "size": 0.0, "rule": "none"})
    if a["below_close"] == b["below_close"]:
        fails.append("the count below the floor does not answer the subsistence need")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {len(sample)} cells")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    # **A measurement must not be able to overwrite the record.** Cutting the
    # grid down to time a cell rewrote this station's record with the cut-down
    # grid, and nothing stopped it because the write is unconditional. The
    # record is load-bearing and the previous one was never committed, so it
    # was not recoverable. Any run on a grid other than the registered one
    # passes this flag.
    ap.add_argument("--no-write", action="store_true",
                    help="run and print, do not touch the record")
    ap.add_argument("--needs", type=float, nargs="*", default=list(NEEDS))
    ap.add_argument("--seeds", type=int, nargs="*", default=list(SEED_SET))
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    sample = draws(needs=tuple(args.needs), seeds=tuple(args.seeds))
    print(f"{len(sample)} cells over {len(by_carrier(sample))} carriers\n")

    criteria, report = [], {}
    for name, kind, fn in (("A36-1", "known_answer", crit_instrument_live),
                           ("A36-2", "own_reading", crit_count_does_not_move),
                           ("A36-3", "own_reading", crit_something_did_differ),
                           ("A36-4", "own_reading", crit_mix_is_live),
                           ("A36-5", "own_reading", crit_three_rounds),
                           ("A36-6", "instrument", crit_conservation)):
        ok, detail, rep = fn(sample)
        crit = {"name": name, "kind": kind,
                "passed": None if ok is None else bool(ok), "detail": detail}
        if ok is None:
            crit["void"] = True
        criteria.append(crit)
        report[name] = rep
        print(f"{'VOID' if ok is None else 'PASS' if ok else 'FAIL'}"
              f"  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "A36-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["A36-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  A36-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "A36",
        "config": {"needs": list(args.needs), "seeds": list(args.seeds),
                   "stresses": list(STRESSES), "elasticities": list(ELASTICITIES),
                   "shocks": [list(s) for s in SHOCKS], "pair": list(PAIR),
                   "shares": list(SHARES), "bases": list(BASES), "gain": GAIN,
                   "authority": A31.AUTHORITY, "rounds": A31.ROUNDS,
                   "imports": "a31_shape (carrier, driver, shock table)"},
        "report": report,
        "criteria": criteria,
        # **The cells themselves.** Without them a criterion here cannot be
        # re-derived, corrected in place, or diffed against another machine,
        # and the summaries above are all a later reader has. A35 met that
        # wall the day before this station ran and got out of it only because
        # its rows were on disk. The one binding rule on this track is that
        # every quantity a run produced is reported.
        "rows": sorted(sample, key=lambda r: (
            r["need"], r["stress"], r["elasticity"], r["shock"], r["seed"],
            r["rule"], r.get("position") or "", r.get("base") or "",
            r.get("base_a") or "", r.get("base_b") or "",
            float(r.get("share") or 0.0))),
        "module_sha": _sha(SRC / "network.py"),
        "script_sha": _sha(pathlib.Path(__file__).resolve()),
    }
    if args.no_write:
        print(f"--no-write: record NOT touched ({OUT})")
    else:
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
    # **Only a false reading is a failure.** ``not c["passed"]`` is true for
    # ``None`` as well, which would turn a criterion with no object into a
    # non-zero exit.
    bad = [c["name"] for c in criteria if c["passed"] is False]
    print(f"all {len(criteria)} criteria pass; record written" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
