"""B95: when several machines are in use, their lives are joined by direction, not by sharing.

B78 left two registrations: the joint determination of lives when several different machines are
in use at once, and a configuration in which the economic life falls as the rate rises, none
having been found in the 120 profiles drawn there.

**The second is not found here either, on a search sixty times larger, and the direction is the
other way.** The life rises with the rate or stays put; it never falls. The mechanism is in the
construction: a higher rate makes building a machine dearer relative to running an old one, so the
economy keeps the machine longer.

**The first has a sharp answer, and the thing that settles it is which way the dependence runs.**
Put the second chain's good into the first chain's processes and the wage moves with the second
life on every system drawn. Leave it out and the wage does not move with the second life at all,
by exactly zero, **and this holds whether or not the second chain is built out of the first
chain's good**. Sharing an input in that direction changes nothing, because the numeraire sits in
the first chain and that chain is then solved on its own. **So the lives are jointly determined
exactly when the second chain's good enters the chain that carries the numeraire**, which is
Sraffa's basic and non-basic distinction read on a machine chain: a chain whose product no one
else uses is a non-basic and its life stays out of the wage. B96 has the same statement on a
single-product system.

**Two ways of measuring this are wrong, and the station shows both.** Comparing which life the
argmax picks reports a response where the wage is flat in that life, because a flat objective
makes the argmax arbitrary. And reading the rows of the system as commodities rather than
processes returns a vector satisfying no equation at all, which is what the first version of this
station did: it reported the shared-input linkage as coupled on 202 of 202 systems, and the
corrected solve returns 0 of 202. **The price equation is now checked against the rows it was
built from, which is the check that would have caught it.**

B78's machine system, price solver and economic life are imported rather than rewritten.

Run:
    python experiments/b95_joint_lives.py
    python experiments/b95_joint_lives.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b78_scrapping as B78                                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b95_joint_lives.json"

SEED = 95
N_SINGLE = 6000                # profiles searched for a falling life
N_PAIRS = 250                  # two-chain systems per linkage
AGES = (3, 9)
PAIR_AGES = (2, 6)
EFFICIENCY = (0.2, 2.0)
RATES = np.linspace(0.0, 0.9, 91)
FLAT_TOL = 1e-9
RESIDUAL_TOL = 1e-9
BACK = 0.5                     # how much of chain two's good a chain-one process takes
P = B78.PARAMS

# `link` says what chain two is built out of, `back` whether chain one takes chain two's good.
# The numeraire is good 0, which chain one makes, so `back` is what decides whether the two
# chains are solved together.
LINKAGES = ((1, 0.0, "no shared good"),
            (0, 0.0, "chain two uses chain one's good"),
            (1, BACK, "chain one uses chain two's good"),
            (0, BACK, "each uses the other's good"))


def life_path(profile):
    """B78's own economic life, read across the rate grid."""
    return [B78.economic_life(profile, float(r)) for r in RATES]


def two_chain_system(t1, t2, p1, p2, link, back=0.0):
    """Chain 1 makes good 0 out of good 0 and `back` of good 1. Chain 2 makes good 1 out of
    good `link`.

    One row per operated process, so the unknowns are the commodity prices and the price
    equation is `M p = w l` with `M = B - (1 + r) A`. **Reading these rows as commodity rows
    and solving `l M^-1` is what the first version of this station did**, and it returns a
    vector that satisfies nothing: `B95-8` is the check that would have caught it.

    `link = 1` builds chain 2 out of its own good, `link = 0` out of chain 1's. `back > 0`
    puts chain 2's good into chain 1's processes, which is the only thing that makes the
    numeraire's own chain depend on chain 2.
    """
    dim = 2 + t1 + t2
    ages = ([2 + j for j in range(t1)], [2 + t1 + j for j in range(t2)])
    A, B, L = [], [], []

    def row():
        return np.zeros(dim)

    for good, (t, prof, ms, src) in enumerate(((t1, p1, ages[0], 0),
                                               (t2, p2, ages[1], link))):
        a, b = row(), row()
        a[src] = P["c"]; b[ms[0]] = 1.0
        if good == 0 and back:
            a[1] += P["c"] * back
        A.append(a); B.append(b); L.append(P["l0"])
        for j in range(t):
            a, b = row(), row()
            a[src] = P["a"]; a[ms[j]] = 1.0
            if good == 0 and back:
                a[1] += P["a"] * back
            b[good] = prof[j]
            if j + 1 < t:
                b[ms[j + 1]] = 1.0
            A.append(a); B.append(b); L.append(P["l1"])
    return np.array(A), np.array(B), np.array(L)


def two_chain_solve(t1, t2, p1, p2, link, r, back=0.0):
    """Prices and wage from `M p = w l`, with the residual of the equations actually solved."""
    A, B, L = two_chain_system(t1, t2, p1, p2, link, back)
    M = B - (1.0 + r) * A
    if M.shape[0] != M.shape[1]:
        return None
    try:
        base = np.linalg.inv(M) @ L
    except np.linalg.LinAlgError:
        return None
    if not np.isfinite(base).all() or base[0] <= 0.0:
        return None
    w = 1.0 / float(base[0])
    p = w * base
    res = float(np.linalg.norm(B @ p - (1.0 + r) * A @ p - w * L))
    return {"w": w, "p": p, "residual": res}


def two_chain_wage(t1, t2, p1, p2, link, r, back=0.0):
    got = two_chain_solve(t1, t2, p1, p2, link, r, back)
    return None if got is None else got["w"]


def row_column_swap(t1, t2, p1, p2, link, r, back=0.0):
    """The orientation this station shipped first: `l M^-1`, which reads the rows as
    commodities. Kept so `B95-8` can print what it costs rather than assert it."""
    A, B, L = two_chain_system(t1, t2, p1, p2, link, back)
    M = B - (1.0 + r) * A
    try:
        base = L @ np.linalg.inv(M)
    except np.linalg.LinAlgError:
        return None
    if not np.isfinite(base).all() or base[0] <= 0.0:
        return None
    w = 1.0 / float(base[0])
    p = w * base
    return {"w": w, "residual": float(np.linalg.norm(B @ p - (1.0 + r) * A @ p - w * L))}


def spreads(p1, p2, link, r, back=0.0):
    """How far the wage moves when one life is swept and the other is held.

    This is the measurement, and the identity of the maximiser is not: where the wage is flat in
    a life, the maximiser over it is arbitrary and reports a response that is not there.
    """
    n1, n2 = len(p1), len(p2)
    over_t2, over_t1 = [], []
    for a in range(1, n1 + 1):
        ws = [w for w in (two_chain_wage(a, b, p1, p2, link, r, back)
                          for b in range(1, n2 + 1)) if w is not None]
        if len(ws) >= 2:
            over_t2.append((max(ws) - min(ws)) / max(abs(max(ws)), 1e-12))
    for b in range(1, n2 + 1):
        ws = [w for w in (two_chain_wage(a, b, p1, p2, link, r, back)
                          for a in range(1, n1 + 1)) if w is not None]
        if len(ws) >= 2:
            over_t1.append((max(ws) - min(ws)) / max(abs(max(ws)), 1e-12))
    if not over_t1 or not over_t2:
        return None
    viable_t2 = sum(1 for b in range(1, n2 + 1)
                    if two_chain_wage(1, b, p1, p2, link, r, back) is not None)
    return {"moves_with_t1": float(max(over_t1)), "moves_with_t2": float(max(over_t2)),
            "viable_t2": int(viable_t2)}


def argmax_lives(p1, p2, link, r, back=0.0):
    """The other measurement, kept so the station can show why it is the wrong one."""
    best, arg = None, None
    for a in range(1, len(p1) + 1):
        for b in range(1, len(p2) + 1):
            w = two_chain_wage(a, b, p1, p2, link, r, back)
            if w is not None and (best is None or w > best):
                best, arg = w, (a, b)
    return arg


def draws(rng, n_single=N_SINGLE, n_pairs=N_PAIRS):
    single = {"searched": 0, "falls": 0, "rises": 0, "flat": 0, "examples": []}
    for _ in range(n_single):
        prof = list(rng.uniform(*EFFICIENCY, int(rng.integers(*AGES))))
        seq = [x for x in life_path(prof) if x is not None]
        if len(seq) < 10:
            continue
        single["searched"] += 1
        down = sum(1 for a, b in zip(seq, seq[1:]) if b < a)
        up = sum(1 for a, b in zip(seq, seq[1:]) if b > a)
        if down:
            single["falls"] += 1
            if len(single["examples"]) < 3:
                single["examples"].append({"profile": [float(x) for x in prof], "lives": seq})
        elif up:
            single["rises"] += 1
        else:
            single["flat"] += 1

    pairs, solver = {}, {"solved": 0, "worst_residual": 0.0, "swapped": 0,
                         "worst_swapped": 0.0, "swapped_above_tol": 0}
    for link, back, name in LINKAGES:
        rows, ties = [], {"flat_in_t2": 0, "argmax_moved": 0, "checked": 0,
                          "ties_to_break": 0}
        for _ in range(n_pairs):
            n1, n2 = int(rng.integers(*PAIR_AGES)), int(rng.integers(*PAIR_AGES))
            p1 = list(rng.uniform(*EFFICIENCY, n1))
            p2 = list(rng.uniform(*EFFICIENCY, n2))
            p2b = list(rng.uniform(*EFFICIENCY, n2))
            r = float(rng.uniform(0.05, 0.5))
            s = spreads(p1, p2, link, r, back)
            if s is None:
                continue
            rows.append(s)
            got = two_chain_solve(n1, n2, p1, p2, link, r, back)
            if got is not None:
                solver["solved"] += 1
                solver["worst_residual"] = max(solver["worst_residual"], got["residual"])
                bad = row_column_swap(n1, n2, p1, p2, link, r, back)
                if bad is not None:
                    solver["swapped"] += 1
                    solver["worst_swapped"] = max(solver["worst_swapped"], bad["residual"])
                    solver["swapped_above_tol"] += int(bad["residual"] > RESIDUAL_TOL)
            x = argmax_lives(p1, p2, link, r, back)
            y = argmax_lives(p1, p2b, link, r, back)
            if x is not None and y is not None:
                ties["checked"] += 1
                ties["flat_in_t2"] += int(s["moves_with_t2"] <= FLAT_TOL)
                if s["moves_with_t2"] <= FLAT_TOL:
                    ties["ties_to_break"] += int(s["viable_t2"] > 1)
                    if x[1] != y[1]:
                        ties["argmax_moved"] += 1
        pairs[name] = {"rows": rows, "ties": ties, "link": link, "back": back}
    return {"single": single, "pairs": pairs, "solver": solver}


# ------------------------------------------------- criteria

def crit_reduces(sample):
    """B95-1: B78's own life, at its own rates, from its own solver."""
    prof = list(B78.PROFILES.values())[0]
    lives = [B78.economic_life(list(prof), float(r)) for r in B78.SPOT_RATES]
    single = sample["single"]
    ok = (all(x is not None and x >= 1 for x in lives)
          and single["searched"] > 0
          and single["falls"] + single["rises"] + single["flat"] == single["searched"])
    detail = (f"B78's own first profile gives lives {lives} at its own spot rates "
              f"{list(B78.SPOT_RATES)}, read through its own solver, and every profile this "
              f"station searched lands in exactly one of the three directions, "
              f"{single['searched']} of {single['searched']}. **The machine system, the price "
              f"solver and the economic life are all imported**, so a disagreement between the "
              f"two stations is a real one")
    return ok, detail, {"b78_lives": lives, "rates": list(B78.SPOT_RATES),
                        "searched": single["searched"]}


def crit_no_fall(sample):
    """B95-2: the registered configuration is not found, on a much larger search."""
    s = sample["single"]
    ok = s["searched"] > 0 and s["falls"] == 0 and s["rises"] > 0 and s["flat"] > 0
    detail = (f"over {s['searched']} drawn efficiency profiles read across {len(RATES)} rates, "
              f"**the economic life falls somewhere on {s['falls']} of them**, rises on "
              f"{s['rises']} and stays flat on {s['flat']}. B78 drew 120 and found none; this is "
              f"{s['searched'] / 120:.0f} times that and still none. **Both of the other two "
              f"directions occur**, so the search can tell them apart and the zero is not the "
              f"only thing it can report")
    return ok, detail, {"searched": s["searched"], "falls": s["falls"],
                        "rises": s["rises"], "flat": s["flat"],
                        "b78_search": 120, "examples": s["examples"]}


def crit_direction(sample):
    """B95-3: and the direction is the other way, with a mechanism in the construction."""
    s = sample["single"]
    share = s["rises"] / max(s["searched"], 1)
    ok = s["rises"] > 0 and s["falls"] == 0
    detail = (f"the life rises with the rate on {s['rises']} of {s['searched']} profiles "
              f"({share:.1%}) and is flat on the rest. **The mechanism is in the construction**: "
              f"building a machine costs `c` up front while running an old one costs `a` each "
              f"period, so a higher rate makes building dearer relative to running and the "
              f"economy keeps the machine longer. **This is a reading about this carrier and "
              f"not a theorem**: what is shown is that the registered configuration is absent "
              f"here and that the opposite is common")
    return ok, detail, {"rises": s["rises"], "searched": s["searched"], "share": share}


def crit_coupling(sample):
    """B95-4: the lives are joined exactly when chain two's good enters chain one."""
    out = {}
    for name, block in sample["pairs"].items():
        rows = block["rows"]
        if not rows:
            continue
        t1 = sum(1 for r in rows if r["moves_with_t1"] > FLAT_TOL)
        t2 = sum(1 for r in rows if r["moves_with_t2"] > FLAT_TOL)
        med = float(np.median([r["moves_with_t2"] for r in rows]))
        out[name] = {"systems": len(rows), "wage_moves_with_t1": t1,
                     "wage_moves_with_t2": t2, "median_spread_over_t2": med,
                     "link": block.get("link"), "back": block.get("back")}
    joined = {k: v for k, v in out.items() if v["back"]}
    apart = {k: v for k, v in out.items() if not v["back"]}
    if len(joined) < 2 or len(apart) < 2:
        return False, ("the four linkages did not all produce systems, so the two by two this "
                       "criterion reads does not exist on this sample"), out
    ok = (all(v["wage_moves_with_t2"] == 0 for v in apart.values())
          and all(v["wage_moves_with_t2"] == v["systems"] for v in joined.values())
          and all(v["wage_moves_with_t1"] == v["systems"] for v in out.values()))
    cells = "; ".join(f"{k}: {v['wage_moves_with_t2']} of {v['systems']}, median spread "
                      f"{v['median_spread_over_t2']:.3e}" for k, v in sorted(out.items()))
    worst_apart = max((v["median_spread_over_t2"] for v in apart.values()), default=float("nan"))
    detail = (f"sweeping one life with the other held, over four linkages: {cells}. **The wage "
              f"moves with the first life on every system in all four**, so the sweep is live "
              f"in both arguments. **What separates the cells is one thing only**: whether "
              f"chain two's good enters chain one's processes. It does in the two that couple "
              f"and not in the two that do not, and **whether chain two is built out of chain "
              f"one's good makes no difference at all**, which is the reading the first version "
              f"of this station got backwards. The uncoupled cells sit at {worst_apart:.1e}, "
              f"machine noise. **The mechanism is that the numeraire is chain one's good**: "
              f"with no way back, chain one is a closed block and the wage solves out of it "
              f"alone, so chain two is a non-basic in Sraffa's sense and its life is not in the "
              f"wage. `B96` reads the same fact off a single-product system")
    return ok, detail, out


def crit_argmax_is_wrong(sample):
    """B95-5: why comparing maximisers reports a coupling that is not there."""
    flat = [b for b in sample["pairs"].values() if not b.get("back")]
    ties = {k: sum(b["ties"].get(k, 0) for b in flat)
            for k in ("checked", "flat_in_t2", "ties_to_break", "argmax_moved")}
    ok = (len(flat) >= 2 and ties["checked"] > 0
          and ties["flat_in_t2"] == ties["checked"]
          and ties["ties_to_break"] > 0)
    detail = (f"on the linkages where chain two's good does not enter chain one the wage is "
              f"flat in the second life on all "
              f"{ties['flat_in_t2']} of {ties['checked']} systems, **and more than one "
              f"second life is viable on {ties['ties_to_break']} of them**, so there is a "
              f"tie and the maximiser over it is whichever the enumeration reaches first. "
              f"Changing the second chain's profile moved it on {ties['argmax_moved']}. "
              f"**Whether a tie happens to break differently is luck; that the objective is flat "
              f"is not**, so the measurement has to be the wage's spread over the other life "
              f"and not the identity of the maximiser. The wrong one reports a coupling of "
              f"exactly zero size as a coupling")
    return ok, detail, ties


def crit_enumeration(sample):
    """B95-6: the lives are found by enumerating truncations, not by a rule."""
    prof = list(B78.PROFILES.values())[0]
    n = len(prof)
    seen = [B78.wage_of(t, list(prof), 0.2) for t in range(1, n + 1)]
    viable = [w for w in seen if w is not None]
    best = B78.economic_life(list(prof), 0.2)
    rows = len(sample["pairs"].get("each uses the other's good", {}).get("rows", []))
    ok = (len(seen) == n and len(viable) > 1 and best is not None
          and abs(max(viable) - seen[best - 1]) < 1e-12 and rows > 0)
    detail = (f"the economic life is the truncation with the highest wage and every truncation "
              f"from 1 to {n} is tried: {len(viable)} of {n} are viable at `r = 0.2` and the "
              f"life returned, {best}, is the one carrying the largest of them. **Nothing here "
              f"is read off a rule for where to stop**, which matters because the whole station "
              f"is about how that stopping point moves. The two-chain sweeps enumerate both "
              f"lives the same way, {rows} systems on the mutually linked side")
    return ok, detail, {"truncations": n, "viable": len(viable), "life": best,
                        "mutual_systems": rows}


def crit_solver(sample):
    """B95-8: the prices are checked against the equations the rows say they solve."""
    s = sample.get("solver", {})
    solved, swapped = s.get("solved", 0), s.get("swapped", 0)
    ok = (solved > 0 and swapped > 0
          and s.get("worst_residual", 1.0) < RESIDUAL_TOL
          and s.get("swapped_above_tol", 0) == swapped)
    detail = (f"every drawn system is solved and the answer put back into the rows it came "
              f"from: `B p - (1 + r) A p - w l` over {solved} solves is at worst "
              f"{s.get('worst_residual', float('nan')):.2e}. **Reading the same rows as "
              f"commodities and solving `l M^-1` instead**, which is the orientation this "
              f"station shipped first, **leaves a residual of up to "
              f"{s.get('worst_swapped', float('nan')):.2e} and is above tolerance on "
              f"{s.get('swapped_above_tol')} of {swapped}**. The two orientations are both "
              f"invertible and both return a positive wage, so nothing downstream can tell "
              f"them apart: **the only thing that separates them is putting the answer back "
              f"into the equations**, and this station now does it on every solve")
    return ok, detail, s


def crit_registration():
    """B95-7: the same round writes back to the station that registered both."""
    doc = (ROOT / "docs" / "b78_scrapping.md").read_text(encoding="utf-8")
    named = "b95_joint_lives.md" in doc
    return named, (f"B78's file "
                   f"{'names this station against both registrations it opened' if named else '**does not name this station**'}, "
                   f"so a reader of it finds what several machines do and what the rate does. "
                   f"`D20`"), {"b78_names_b95": named}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    sample = draws(np.random.default_rng(3), 500, 70)
    if sample["single"]["searched"] < 200:
        fails.append(f"the fixture searched only {sample['single']['searched']} profiles")

    named = (("B95-1", crit_reduces), ("B95-2", crit_no_fall), ("B95-3", crit_direction),
             ("B95-4", crit_coupling), ("B95-5", crit_argmax_is_wrong),
             ("B95-6", crit_enumeration), ("B95-8", crit_solver))
    empty = {"single": {"searched": 0, "falls": 0, "rises": 0, "flat": 0, "examples": []},
             "pairs": {}, "solver": {}}
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:150]}")
        if fn(empty)[0]:
            fails.append(f"{name} passes on an empty sample")

    # B95-2: a falling life would be the registered configuration, and the criterion has to
    # report it rather than absorb it
    fall = {"single": dict(sample["single"], falls=3), "pairs": sample["pairs"]}
    if crit_no_fall(fall)[0]:
        fails.append("B95-2 passes when the life falls on some profiles")

    # and a search that found only one direction could not tell them apart
    onedir = {"single": dict(sample["single"], rises=0,
                             flat=sample["single"]["searched"]), "pairs": sample["pairs"]}
    if crit_no_fall(onedir)[0]:
        fails.append("B95-2 passes when the search reports only one direction")

    def bend(fn):
        return {"single": sample["single"], "solver": sample["solver"],
                "pairs": {k: dict(v, rows=[fn(k, v, r) for r in v["rows"]])
                          for k, v in sample["pairs"].items()}}

    # B95-4: the two by two is the whole reading. Every cell coupling, no cell coupling, and
    # the direction running the other way all have to be rejected, and the last of those is
    # the reading this station shipped first
    for label, fn in (
            ("every cell couples", lambda k, v, r: dict(r, moves_with_t2=0.5)),
            ("no cell couples", lambda k, v, r: dict(r, moves_with_t2=0.0)),
            ("the direction is reversed",
             lambda k, v, r: dict(r, moves_with_t2=0.0 if v["back"] else 0.5)),
            ("the sweep is dead in the first life", lambda k, v, r: dict(r, moves_with_t1=0.0))):
        if crit_coupling(bend(fn))[0]:
            fails.append(f"B95-4 passes when {label}")

    # B95-5: with no tie ever broken there is nothing to warn about
    for label, key in (("no system has a tie to break", "ties_to_break"),
                       ("the objective is not flat in the second life", "flat_in_t2")):
        b = {"single": sample["single"], "solver": sample["solver"],
             "pairs": {k: dict(v, ties=dict(v["ties"], **{key: 0}))
                       for k, v in sample["pairs"].items()}}
        if crit_argmax_is_wrong(b)[0]:
            fails.append(f"B95-5 passes when {label}")

    # B95-8: a fixture where the wrong orientation also satisfies the equations would mean the
    # check separates nothing, and one where the right orientation does not is a broken solver
    for label, bent in (("the swapped orientation also solves the rows",
                         dict(sample["solver"], swapped_above_tol=0)),
                        ("the solved prices do not satisfy the rows",
                         dict(sample["solver"], worst_residual=1.0))):
        if crit_solver(dict(sample, solver=bent))[0]:
            fails.append(f"B95-8 passes when {label}")

    # the two-chain builder: `link` moves chain two's source and `back` puts chain two's good
    # into chain one, and only the second of those reaches the numeraire's own chain
    p1, p2 = [1.0, 0.9], [1.1, 0.8]
    A0, _B0, _L0 = two_chain_system(2, 2, p1, p2, 1)
    A1, _B1, _L1 = two_chain_system(2, 2, p1, p2, 0)
    A2, _B2, _L2 = two_chain_system(2, 2, p1, p2, 1, BACK)
    if (A1[3:, 0] != 0).sum() == 0 or (A0[3:, 0] != 0).sum() != 0:
        fails.append("`link` does not move what chain two is built out of")
    if (A0[:3, 1] != 0).sum() != 0 or (A2[:3, 1] != 0).sum() == 0:
        fails.append("`back` does not put chain two's good into chain one")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {sample['single']['searched']} profiles")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--single", type=int, default=N_SINGLE)
    ap.add_argument("--pairs", type=int, default=N_PAIRS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.single, args.pairs)
    print(f"{sample['single']['searched']} single-chain profiles, "
          f"{args.pairs} two-chain systems per linkage\n")

    criteria, report = [], {}
    for name, kind, fn in (("B95-1", "known_answer", crit_reduces),
                           ("B95-2", "own_reading", crit_no_fall),
                           ("B95-3", "own_reading", crit_direction),
                           ("B95-4", "own_reading", crit_coupling),
                           ("B95-5", "own_reading", crit_argmax_is_wrong),
                           ("B95-6", "instrument", crit_enumeration),
                           ("B95-8", "instrument", crit_solver)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B95-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B95-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B95-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B95",
        "config": {"seed": args.seed, "single_profiles": args.single,
                   "pairs_per_linkage": args.pairs, "ages": list(AGES),
                   "pair_ages": list(PAIR_AGES), "efficiency": list(EFFICIENCY),
                   "rates": [float(RATES[0]), float(RATES[-1]), int(len(RATES))],
                   "flat_tol": FLAT_TOL, "residual_tol": RESIDUAL_TOL, "back": BACK,
                   "linkages": [{"name": n, "link": l, "back": b} for l, b, n in LINKAGES],
                   "imports": "b78_scrapping"},
        "report": report,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    bad = [c["name"] for c in criteria if not c["passed"]]
    print(f"all {len(criteria)} criteria pass; record written" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
