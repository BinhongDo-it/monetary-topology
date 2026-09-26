"""B92: capital reversing, and why two techniques cannot produce it without reswitching.

Capital reversing is the half of the Cambridge controversy that says a lower rate of profit can
go with a less capital-intensive technique, so the rate does not measure a scarcity of capital.
B67's Corollary 12.3 already contains it in general form: **the value advanced is read off the
field and the field moves with the rate, so no quantity read off prices orders techniques
independently of the rate.** This station names it, measures it, and finds where the two-technique
case stops short of the general one.

**The measure.** A technique is a dated-labour profile, B74's object. With output as the unit,
`w(x) = 1 / c(x)` where `c(x) = sum_t l_t x^t` and `x = 1 + r`, net output per worker is `1 / L`
with `L = sum_t l_t`, and the value of capital per worker is `k = (1/L - w) / r`.

**At a crossing the wage is the same for both techniques, so `k_A > k_B` exactly when
`L_A < L_B`.** Capital reversing at a crossing is therefore the statement that the technique
adopted at the higher rate carries less labour in total.

**And `c_i(1) = L_i`.** So with one crossing above `x = 1`, the technique cheaper just below it is
cheaper all the way down to `x = 1`, where cheaper means less total labour, which is the opposite
of what reversing needs. **Two techniques cannot reverse without reswitching, and it is one line
of arithmetic rather than a property of any family.** Three can, because the two techniques
meeting on the envelope need not be the ones that own it at a zero rate.

B74's technique generator, Samuelson's 1966 pair and its root finder are imported rather than
rewritten.

Run:
    python experiments/b92_capital_reversing.py
    python experiments/b92_capital_reversing.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b74_roundaboutness as B74                           # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b92_capital_reversing.json"

SEED = 92
N_PAIRS = 4000                 # two-technique draws
N_FAMILIES = 4000              # three-or-more-technique draws
FAMILY_SIZES = (3, 6)
X_LO, X_HI = 1.0 + 1e-6, 4.0
X_GRID = 4000
BISECTION = 60
SIDE = 1e-4                    # how far either side of a root a crossing is read
TOL = 1e-12


def total_labour(profile):
    return float(sum(profile.values()))


def cost(profile, x):
    return float(sum(l * x ** t for t, l in profile.items()))


def capital_per_worker(profile, x):
    """`k = (y - w) / r` with `y = 1/L` net output per worker and `w = 1/c(x)`."""
    r = x - 1.0
    return ((1.0 / total_labour(profile)) - 1.0 / cost(profile, x)) / r


def crossings(a, b):
    """Roots of `c_a - c_b` above `x = 1` at which the cheaper technique actually changes.

    A root at which it does not is a tangency, and counting it as a switch would report a
    change of technique that no one would make.
    """
    deg = max(max(a), max(b))
    c = np.zeros(deg + 1)
    for t, l in a.items():
        c[t] += l
    for t, l in b.items():
        c[t] -= l
    out = []
    for x in B74.switch_points(c):
        if not (X_LO < x < X_HI):
            continue
        lo = "a" if cost(a, x - SIDE) < cost(b, x - SIDE) else "b"
        hi = "a" if cost(a, x + SIDE) < cost(b, x + SIDE) else "b"
        if lo != hi:
            out.append({"x": float(x), "below": lo, "above": hi})
    return out


def reverses(a, b, cross):
    """Does the technique adopted at the higher rate carry the larger capital per worker."""
    lo = a if cross["below"] == "a" else b
    hi = a if cross["above"] == "a" else b
    kl, kh = capital_per_worker(lo, cross["x"]), capital_per_worker(hi, cross["x"])
    return kh > kl + TOL, kl, kh


def envelope_owner(techs, x):
    return int(np.argmin([cost(t, x) for t in techs]))


def bisect_switch(techs, lo, hi, steps=None):
    """Narrow an owner change, so a switch is located rather than read off the grid."""
    steps = BISECTION if steps is None else steps
    a, b = lo, hi
    va = envelope_owner(techs, a)
    for _ in range(steps):
        m = 0.5 * (a + b)
        if envelope_owner(techs, m) == va:
            a = m
        else:
            b = m
    return a, b


def envelope_switches(techs, grid):
    owners = [envelope_owner(techs, x) for x in grid]
    out = []
    for i in range(1, len(owners)):
        if owners[i] != owners[i - 1]:
            a, b = bisect_switch(techs, float(grid[i - 1]), float(grid[i]))
            out.append({"x": 0.5 * (a + b), "bracket": b - a,
                        "below": owners[i - 1], "above": owners[i]})
    return out


def pair_draws(rng, n_pairs):
    out = []
    for _ in range(n_pairs):
        a, _la = B74.random_technique(rng)
        b, _lb = B74.random_technique(rng)
        if total_labour(a) <= 0.0 or total_labour(b) <= 0.0:
            continue
        cross = crossings(a, b)
        if not cross:
            continue
        rows = []
        for c in cross:
            rev, kl, kh = reverses(a, b, c)
            rows.append({**c, "reverses": bool(rev), "k_below": kl, "k_above": kh,
                         "L_below": total_labour(a if c["below"] == "a" else b),
                         "L_above": total_labour(a if c["above"] == "a" else b)})
        out.append({"L_a": total_labour(a), "L_b": total_labour(b),
                    "crossings": rows, "n_crossings": len(rows)})
    return out


def family_draws(rng, n_families):
    grid = np.linspace(X_LO, X_HI, X_GRID)
    out = []
    for _ in range(n_families):
        k = int(rng.integers(FAMILY_SIZES[0], FAMILY_SIZES[1]))
        techs = [B74.random_technique(rng)[0] for _ in range(k)]
        sw = envelope_switches(techs, grid)
        if not sw:
            continue
        owners = [sw[0]["below"]] + [s["above"] for s in sw]
        rows = []
        for s in sw:
            lo, hi = techs[s["below"]], techs[s["above"]]
            kl = capital_per_worker(lo, s["x"])
            kh = capital_per_worker(hi, s["x"])
            rows.append({**s, "reverses": bool(kh > kl + TOL), "k_below": kl, "k_above": kh,
                         "L_below": total_labour(lo), "L_above": total_labour(hi)})
        out.append({"k": k, "switches": rows,
                    "reswitching": len(owners) > len(set(owners)),
                    "labours": [total_labour(t) for t in techs],
                    "owner_at_zero_rate": int(np.argmin([total_labour(t) for t in techs])),
                    "profiles": [dict(t) for t in techs]})
    return out


def draws(rng, n_pairs=N_PAIRS, n_families=N_FAMILIES):
    return {"pairs": pair_draws(rng, n_pairs), "families": family_draws(rng, n_families)}


# ------------------------------------------------- criteria

def crit_samuelson(sample):
    """B92-1: Samuelson's 1966 pair, from B74's own constants, with a published answer."""
    a, b = dict(B74.SAMUELSON_A), dict(B74.SAMUELSON_B)
    cross = crossings(a, b)
    xs = [round(c["x"] - 1.0, 6) for c in cross]
    want = [round(r, 6) for r in B74.SAMUELSON_SWITCHES]
    wages = [abs(1.0 / cost(a, c["x"]) - 1.0 / cost(b, c["x"])) for c in cross]
    revs = [reverses(a, b, c)[0] for c in cross]
    ok = (xs == want and max(wages, default=1.0) < 1e-12 and revs == [False, True]
          and total_labour(a) < total_labour(b))
    detail = (f"Samuelson's 1966 pair, taken from B74's own constants: the two crossings are at "
              f"`r = {xs}` against the published `{want}`, the wage is equal at each to "
              f"{max(wages, default=float('nan')):.2e}, and capital reverses at "
              f"{[i for i, v in enumerate(revs) if v]} of the two, **the second and not the "
              f"first**. `L_A = {total_labour(a)}` against `L_B = {total_labour(b)}`, so at the "
              f"first crossing the technique taken at the higher rate carries more labour and at "
              f"the second it carries less. **Reswitching implies reversing at one of the two "
              f"switches and not at both**, which is the textbook reading and is what comes back")
    return ok, detail, {"switches": xs, "published": want, "reverses": revs,
                        "worst_wage_gap": max(wages, default=None),
                        "L_a": total_labour(a), "L_b": total_labour(b)}


def crit_pairs(sample):
    """B92-2: with two techniques, reversing appears only where an owner returns."""
    pairs = sample["pairs"]
    one = [p for p in pairs if p["n_crossings"] == 1]
    many = [p for p in pairs if p["n_crossings"] >= 2]
    rev_one = sum(1 for p in one if any(c["reverses"] for c in p["crossings"]))
    rev_many = sum(1 for p in many if any(c["reverses"] for c in p["crossings"]))
    ok = bool(one) and bool(many) and rev_one == 0 and rev_many == len(many)
    detail = (f"over {len(pairs)} two-technique draws that cross at all, "
              f"**{rev_one} of the {len(one)} with a single crossing reverse** and "
              f"**{rev_many} of the {len(many)} with two or more do**. Both ends are counted "
              f"on the same draws. The second half is the textbook statement that reswitching "
              f"brings reversing with it; **the first half is the one this station is here for**")
    return ok, detail, {"single_crossing": len(one), "reversing_single": rev_one,
                        "multi_crossing": len(many), "reversing_multi": rev_many}


def crit_mechanism(sample):
    """B92-3: why the first half of B92-2 is arithmetic and not a property of the draws."""
    one = [p for p in sample["pairs"] if p["n_crossings"] == 1]
    agree = sum(1 for p in one if p["crossings"][0]["L_above"] > p["crossings"][0]["L_below"])
    ok = bool(one) and agree == len(one)
    detail = (f"`c_i(1) = L_i`, so at a zero rate cheaper means less total labour. With one "
              f"crossing above `x = 1` the technique cheaper just below it is cheaper all the "
              f"way down to `x = 1`, hence carries the smaller `L`; and at a crossing the wage "
              f"is shared, so `k` is ordered the opposite way to `L`. **Reversing would need "
              f"the technique taken at the higher rate to carry the smaller `L`, and it carries "
              f"the larger on {agree} of {len(one)} single-crossing draws, without exception.** "
              f"So the first half of B92-2 is one line of arithmetic rather than a property of "
              f"this family, and the count is a check on the arithmetic")
    return ok, detail, {"single_crossing": len(one), "labour_ordered_as_predicted": agree}


def crit_families(sample):
    """B92-4: three techniques break it, because the pair that meets need not own x = 1."""
    fams = sample["families"]
    resw = [f for f in fams if f["reswitching"]]
    plain = [f for f in fams if not f["reswitching"]]
    found = [f for f in plain if any(s["reverses"] for s in f["switches"])]
    detached = sum(1 for f in found
                   for s in f["switches"] if s["reverses"]
                   and f["owner_at_zero_rate"] not in (s["below"], s["above"]))
    ok = bool(fams) and bool(found)
    ks = sorted({f["k"] for f in found})
    detail = (f"over {len(fams)} families of three to five techniques whose envelope has a "
              f"switch, **{len(found)} show reversing with no owner returning anywhere**, at "
              f"family sizes {ks}, against {len(resw)} families that do reswitch. **The "
              f"two-technique argument fails here for the reason it names**: the pair meeting on "
              f"the envelope need not include the technique that owns `x = 1`, and on "
              f"{detached} of the reversing switches neither side of the switch is that owner. "
              f"**So reversing without reswitching is a fact about three techniques and not "
              f"about two**, which is what the two-technique half could not have shown")
    return ok, detail, {"families": len(fams), "reswitching": len(resw),
                        "reversing_without_reswitching": len(found),
                        "sizes": ks, "switch_detached_from_zero_rate_owner": detached,
                        "examples": [f["profiles"] for f in found[:2]]}


EQUAL_LABOUR = ({0: 3.0, 1: 1.0, 2: 2.0}, {0: 1.0, 1: 4.0, 2: 1.0})
# two techniques that genuinely change places at x = 2 and carry the same total labour, 6 each


def crit_two_valued(sample):
    """B92-5: one price system, two capital values, and the condition that makes it two."""
    gaps, labour_gaps = [], []
    for p in sample["pairs"]:
        for c in p["crossings"]:
            base = max(abs(c["k_below"]), 1e-12)
            gaps.append(abs(c["k_above"] - c["k_below"]) / base)
            labour_gaps.append(abs(c["L_above"] - c["L_below"]))
    for f in sample["families"]:
        for s in f["switches"]:
            base = max(abs(s["k_below"]), 1e-12)
            gaps.append(abs(s["k_above"] - s["k_below"]) / base)
            labour_gaps.append(abs(s["L_above"] - s["L_below"]))
    g = np.array(gaps, dtype=float)
    lg = np.array(labour_gaps, dtype=float)
    # the constructed case the condition names: a real switch with the same total labour
    a, b = EQUAL_LABOUR
    tie = crossings(a, b)
    tie_gap = None
    if tie:
        x = tie[0]["x"]
        tie_gap = abs(capital_per_worker(a, x) - capital_per_worker(b, x))
    same_labour = int((lg <= TOL).sum())
    ok = (g.size > 0 and float(g.min()) > 0.0 and same_labour == 0
          and tie is not None and len(tie) == 1
          and tie_gap is not None and tie_gap <= TOL)
    med = float(np.median(g)) if g.size else float("nan")
    p10 = float(np.percentile(g, 10)) if g.size else float("nan")
    lo = float(g.min()) if g.size else float("nan")
    detail = (f"at a switch both techniques are in use at one wage and one rate, and their "
              f"capital per worker differs on all {g.size} switches drawn, by a median of "
              f"{med:.3f} of the smaller value, a tenth percentile of "
              f"{p10:.4f} and a smallest of {lo:.2e}. **So `k` takes two "
              f"values at one price system**, which is B67's Corollary 12.3 in its sharpest "
              f"form: a quantity read off the field is not a coordinate on the field. **The "
              f"reason reversing looks like an anomaly is that it is read as a property of a "
              f"technique**, and there is no such property to have a direction. **The two "
              f"values need the two techniques to carry different total labour, and that is "
              f"one line**: at a switch `c_a(x) = c_b(x)`, so the wage is shared, and "
              f"`k = (1/L - 1/c) / (x - 1)` then differs exactly when `L` does. Every switch "
              f"drawn here has `L_above != L_below`, {g.size - same_labour} of {g.size}, **so "
              f"the sample cannot show the other side and it is constructed instead**: "
              f"`C_A = 3 + x + 2x^2` and `C_B = 1 + 4x + x^2` change places at `x = 2` by this "
              f"station's own root finder, both carry `L = 6`, and their `k` differs by "
              f"{tie_gap if tie_gap is not None else float('nan'):.1e}, both being `7/78`. "
              f"**Equal labour is the only way to have a switch and one capital value**")
    return ok, detail, {"switches": int(g.size), "median_relative_gap": med,
                        "switches_with_equal_labour": same_labour,
                        "constructed_tie_gap": tie_gap,
                        "constructed_tie_crossings": len(tie) if tie else 0,
                        "tenth_percentile": p10, "smallest": lo}


def crit_located(sample):
    """B92-6: crossings are separated from tangencies, and envelope switches are bisected."""
    worst = max((s["bracket"] for f in sample["families"] for s in f["switches"]),
                default=float("inf"))
    step = (X_HI - X_LO) / (X_GRID - 1)
    a, b = dict(B74.SAMUELSON_A), dict(B74.SAMUELSON_B)
    tangent = crossings(a, a)                      # a technique against itself: every x is a root
    # the owner is the cheapest technique, and the cheapest at a zero rate is the one with the
    # least total labour, since `c_i(1) = L_i`. Checking the direction here rather than trusting
    # it: an envelope read upside down still produces switches and still produces reversing
    # counts, and nothing else in this station would notice
    wrong_end = 0
    for f in sample["families"]:
        first = f["switches"][0]["below"]
        if first != f["owner_at_zero_rate"]:
            wrong_end += 1
    ok = (bool(sample["families"]) and worst < step / 1e6 and tangent == []
          and wrong_end == 0)
    factor = step / worst if worst > 0 else float("inf")
    detail = (f"every envelope switch is narrowed by bisection from the grid interval it was "
              f"spotted in: the widest remaining bracket is {worst:.2e} against a grid step of "
              f"{step:.2e}, a factor of {factor:.1e}. **And a "
              f"root is only counted when the cheaper technique actually changes across it**: a "
              f"technique put against itself yields {len(tangent)} crossings, where counting "
              f"roots rather than changes would report a switch at every point. A tangency is a "
              f"root at which no one would change technique. **And the envelope is checked to "
              f"run the right way up**: the technique owning the lowest rate is the one with "
              f"the least total labour on every family, {wrong_end} exceptions, which follows "
              f"from `c_i(1) = L_i` and fails at once if the owner is taken as the dearest")
    return ok, detail, {"widest_bracket": worst, "grid_step": step,
                        "self_pair_crossings": len(tangent),
                        "owner_at_zero_rate_mismatches": wrong_end}


def crit_registration():
    """B92-7: the same round writes back to the stations this one draws on."""
    want = ["b67_prices_of_production.md", "b74_roundaboutness.md"]
    missing = [f for f in want
               if "b92_capital_reversing.md" not in (ROOT / "docs" / f).read_text(encoding="utf-8")]
    ok = not missing
    detail = (f"the stations this one draws on "
              f"{'each name it' if ok else '**do not all name it: ' + ', '.join(missing) + '**'}: "
              f"B67 for the corollary this measures and B74 for the technique object and the "
              f"Samuelson pair. `D20`")
    return ok, detail, {"missing_writebacks": missing}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(2)
    sample = draws(rng, 900, 700)
    if len(sample["pairs"]) < 80 or len(sample["families"]) < 80:
        fails.append(f"the fixture drew {len(sample['pairs'])} pairs and "
                     f"{len(sample['families'])} families")

    named = (("B92-1", crit_samuelson), ("B92-2", crit_pairs), ("B92-3", crit_mechanism),
             ("B92-4", crit_families), ("B92-5", crit_two_valued), ("B92-6", crit_located))
    empty = {"pairs": [], "families": []}
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:150]}")
        # B92-1 reads Samuelson's published pair, not this station's draws, so an empty
        # sample says nothing about it
        if name != "B92-1" and fn(empty)[0]:
            fails.append(f"{name} passes on an empty sample")

    # B92-1: the published answer has to be able to disagree, so a pair that is not Samuelson's
    # must not reproduce his two switch points
    a = dict(B74.SAMUELSON_A); a[2] = a[2] * 1.01
    bent = crossings(a, dict(B74.SAMUELSON_B))
    if [round(c["x"] - 1.0, 6) for c in bent] == [round(r, 6) for r in B74.SAMUELSON_SWITCHES]:
        fails.append("a bent Samuelson pair still returns his published switch points")

    # B92-2: if a single-crossing pair reversed, the two-technique statement would be false,
    # and the criterion has to report it rather than absorb it
    flipped = {"pairs": [dict(p, crossings=[dict(c, reverses=True) for c in p["crossings"]])
                         for p in sample["pairs"]],
               "families": sample["families"]}
    if crit_pairs(flipped)[0]:
        fails.append("B92-2 passes when single-crossing pairs reverse")

    # B92-3 is the arithmetic behind that, so bending the labour ordering has to break it
    bentL = {"pairs": [dict(p, crossings=[dict(c, L_above=c["L_below"] * 0.5)
                                          for c in p["crossings"]])
                       for p in sample["pairs"]],
             "families": sample["families"]}
    if crit_mechanism(bentL)[0]:
        fails.append("B92-3 passes when the technique taken at the higher rate carries less labour")

    # B92-4: with no reversing outside the reswitching families there is nothing to report,
    # and the criterion has to say so rather than pass on the reswitching ones
    noplain = {"pairs": sample["pairs"],
               "families": [dict(f, reswitching=True) for f in sample["families"]]}
    if crit_families(noplain)[0]:
        fails.append("B92-4 passes when every reversing family also reswitches")

    # B92-5: a gap of exactly zero would make `k` single-valued at the switch, which is the
    # reading's opposite
    zeroed = {"pairs": [dict(p, crossings=[dict(c, k_above=c["k_below"])
                                           for c in p["crossings"]])
                        for p in sample["pairs"]],
              "families": [dict(f, switches=[dict(s, k_above=s["k_below"])
                                             for s in f["switches"]])
                           for f in sample["families"]]}
    # B92-5: the condition is load-bearing, so a fixture with a switch at equal labour has to
    # be rejected rather than absorbed
    equal = {"pairs": [dict(p, crossings=[dict(c, L_above=c["L_below"]) for c in p["crossings"]])
                       for p in sample["pairs"]],
             "families": [dict(f, switches=[dict(s, L_above=s["L_below"]) for s in f["switches"]])
                          for f in sample["families"]]}
    if crit_two_valued(equal)[0]:
        fails.append("B92-5 passes when a switch carries equal total labour on both sides")

    if crit_two_valued(zeroed)[0]:
        fails.append("B92-5 passes when the two capital values coincide")

    # B92-6: with no bisection the bracket is the grid step
    global BISECTION
    saved, BISECTION = BISECTION, 0
    try:
        coarse = draws(np.random.default_rng(3), 20, 60)
        if crit_located(coarse)[0]:
            fails.append("B92-6 passes with no bisection at all")
    finally:
        BISECTION = saved

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {len(sample['pairs'])} pairs and "
          f"{len(sample['families'])} families")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pairs", type=int, default=N_PAIRS)
    ap.add_argument("--families", type=int, default=N_FAMILIES)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.pairs, args.families)
    print(f"{len(sample['pairs'])} two-technique draws that cross, "
          f"{len(sample['families'])} families whose envelope switches\n")

    criteria, report = [], {}
    for name, kind, fn in (("B92-1", "known_answer", crit_samuelson),
                           ("B92-2", "own_reading", crit_pairs),
                           ("B92-3", "own_reading", crit_mechanism),
                           ("B92-4", "own_reading", crit_families),
                           ("B92-5", "own_reading", crit_two_valued),
                           ("B92-6", "instrument", crit_located)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B92-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B92-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B92-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B92",
        "config": {"seed": args.seed, "pairs": args.pairs, "families": args.families,
                   "family_sizes": list(FAMILY_SIZES), "x_range": [X_LO, X_HI],
                   "x_grid": X_GRID, "bisection_steps": BISECTION, "side": SIDE,
                   "imports": "b74_roundaboutness"},
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
