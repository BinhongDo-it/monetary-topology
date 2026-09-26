"""B85: several columns replaced at once, where the equivalence becomes an implication.

B69's Theorem 14(1) is an equivalence: with the basket held fixed, `r' > r` exactly
when the one column that changed is cheaper at the prices in force. Its results file
registered the several-column case as "the same argument, `pM' <= λp` holding on a
set of columns, not covered by this round's draws".

**Half of that is right.** The forward implication carries over with the same
Collatz-Wielandt step and not a word changed. **The converse does not**: a set in
which some columns get dearer and others cheaper can still raise the rate. So the
one-column equivalence is not the `|S| = 1` case of a several-column equivalence.
It is a property of `|S| = 1`: **the prices in force decide the sign only when one
column moves.**

What survives in general is a bracket, computable at the prices in force:

    min_j (pM')_j / p_j  <=  lambda'  <=  max_j (pM')_j / p_j

Below `lambda` it decides one way, above it the other, and **straddling it does not
decide**, which is a third cell rather than a failure.

Paper station: zero data. B69's system generator, Perron solver, basket and
Collatz-Wielandt bound are imported rather than rewritten.

Run:
    python experiments/b85_simultaneous.py
    python experiments/b85_simultaneous.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import b69_okishio as B69                                  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b85_simultaneous.json"

SEED = 85
N_SYSTEMS = 120
SET_SIZES = (1, 2, 3, 4)
N_SETS = 4                       # column sets drawn per system, basket and size
TOL = 1e-10


def substitution_set(rng, a, l, ks):
    """B69's substitution on each of a set of columns at once.

    Elementwise scaling of the old columns, so the zero pattern and therefore the
    irreducibility are preserved, which is B69's reason for that form.
    """
    a2, l2 = a.copy(), l.copy()
    for k in ks:
        a2[:, k] = a[:, k] * rng.uniform(*B69.SUB_SPREAD, a.shape[0])
        l2[k] = l[k] * float(rng.uniform(*B69.SUB_SPREAD))
    return a2, l2


def draws(rng, n_systems):
    """One sample, shared by every criterion, so they read the same draws."""
    out = []
    for _ in range(n_systems):
        a, l = B69.random_system(rng)
        if a is None:
            continue
        n = a.shape[0]
        v = B69.labour_values(a, l)
        if v.min() <= 0.0:
            continue
        for target in B69.VALUE_OF_BASKET:
            b = B69.basket_of_value(rng, v, target)
            r, p, m, lam = B69.rate_and_prices(a, l, b)
            if p.min() <= 0.0 or r <= 0.0:
                continue
            for size in SET_SIZES:
                if size > n:
                    continue
                for _s in range(N_SETS):
                    ks = sorted(rng.choice(n, size=size, replace=False).tolist())
                    a2, l2 = substitution_set(rng, a, l, ks)
                    lam_a2, _ = B69.perron(a2)
                    if lam_a2 >= 1.0:
                        continue
                    r2, p2, m2, lam2 = B69.rate_and_prices(a2, l2, b)
                    if p2.min() <= 0.0:
                        continue
                    ratios = (p @ m2) / p
                    changed = [float(ratios[k]) for k in ks]
                    costs_old = (p @ m)
                    costs_new = (p @ m2)
                    per_column = [float(costs_new[k] - costs_old[k]) for k in ks]
                    out.append({
                        "n": n, "size": size, "ks": ks,
                        "r": float(r), "r2": float(r2),
                        "lam": float(lam), "lam2": float(lam2),
                        # over every column. True, and useless as a discriminant:
                        # an unchanged column has (pM')_j = lambda p_j exactly, so
                        # this bracket contains lambda whenever one column is left
                        # alone, and therefore never decides anything.
                        "bracket_all": [float(np.min(ratios)), float(np.max(ratios))],
                        # over the columns that moved. This is the discriminant, and
                        # at one column its two ends coincide, which is why the old
                        # prices always decide there and only there.
                        "bracket_changed": [min(changed), max(changed)],
                        "cheaper_each": [c < -TOL for c in per_column],
                        "dearer_any": any(c > TOL for c in per_column),
                        "strictly_cheaper_any": any(c < -TOL for c in per_column),
                        "cost_change_by_column": per_column,
                        "a": a, "l": l, "b": b, "a2": a2, "l2": l2,
                    })
    return out


# ------------------------------------------------- criteria

def crit_single_column(sample):
    """B85-1: at |S| = 1 this reduces to B69's Theorem 14, decided the same way."""
    ones = [s for s in sample if s["size"] == 1]
    bad = []
    for s in ones:
        cheaper = s["cost_change_by_column"][0] < -TOL
        dearer = s["cost_change_by_column"][0] > TOL
        rose, fell = s["r2"] > s["r"] + TOL, s["r2"] < s["r"] - TOL
        if (cheaper and not rose) or (dearer and not fell):
            bad.append(s["ks"])
    ok = bool(ones) and not bad
    detail = (f"{len(ones)} single-column substitutions drawn on B69's own systems and "
              f"baskets, using B69's solver: the sign of the change in the rate is the "
              f"sign of the saving on {len(ones) - len(bad)} of {len(ones)}. "
              + ("The equivalence of Theorem 14(1) is read back here rather than "
                 "assumed, so this station and B69 can disagree."
                 if not bad else f"**{len(bad)} disagree: {bad[:6]}.**"))
    return ok, detail, {"single_column_draws": len(ones), "disagreements": bad}


def crit_forward(sample):
    """B85-2: every changed column cheaper implies the rate rises. The premise has to
    be reachable, or the criterion is counting zero cases."""
    prem = [s for s in sample if s["size"] > 1 and all(s["cheaper_each"])]
    bad = [s for s in prem if not s["r2"] > s["r"] + TOL]
    ok = bool(prem) and not bad
    detail = (f"of the several-column substitutions drawn, {len(prem)} have every "
              f"changed column cheaper at the prices in force, and the rate rises on "
              f"{len(prem) - len(bad)} of them. **The count of draws satisfying the "
              f"premise is in the verdict**: zero counterexamples holds vacuously on "
              f"zero cases, so the number that reached the premise is what says the "
              f"forward half was tested. The Collatz-Wielandt step B69 uses for one "
              f"column is unchanged: `pM' <= lambda p` with strict inequality "
              f"somewhere and `M'` irreducible gives `lambda' < lambda`"
              + ("" if not bad else f". **{len(bad)} counterexamples**"))
    return ok, detail, {"premise_reached": len(prem), "counterexamples": len(bad),
                        "counterexample_sets": [s["ks"] for s in bad[:8]]}


def crit_converse_fails(sample):
    """B85-3: the converse. Found, not assumed."""
    found = [s for s in sample
             if s["size"] > 1 and s["dearer_any"] and s["r2"] > s["r"] + TOL]
    multi = [s for s in sample if s["size"] > 1]
    ok = bool(found)
    if found:
        worst = max(found, key=lambda s: s["r2"] - s["r"])
        detail = (f"**{len(found)} of {len(multi)} several-column substitutions raise "
                  f"the rate while at least one changed column got dearer at the prices "
                  f"in force.** The largest lifts the rate from {worst['r']:.6f} to "
                  f"{worst['r2']:.6f} on columns {worst['ks']}, whose cost changes are "
                  + ", ".join(f"{c:+.4e}" for c in worst["cost_change_by_column"])
                  + ". So the equivalence of Theorem 14(1) does not extend: **the one "
                    "column case is not the |S| = 1 case of a several-column "
                    "equivalence, it is a property of |S| = 1**, and what makes it one "
                    "is that with a single column the prices in force see everything "
                    "that moved")
    else:
        detail = (f"no such configuration was found among {len(multi)} several-column "
                  f"substitutions on this family. **Recorded as not found rather than "
                  f"as not existing**: this draws elementwise rescalings of existing "
                  f"columns on one generator, and the search is not a proof")
    return ok, detail, {"found": len(found), "multi_column_draws": len(multi),
                        "examples": [{"ks": s["ks"], "r": s["r"], "r2": s["r2"],
                                      "cost_change": s["cost_change_by_column"]}
                                     for s in found[:6]]}


def cell_of(s):
    """Which of the three cells a draw falls in, at the prices in force.

    One function, so that a change to the discriminant reaches every reader of it.
    The first version had the loop use one expression and the single-column clause
    read the field directly, and a mutation that swapped the discriminant then
    slipped past the clause written to catch exactly that.
    """
    lo, hi = s["bracket_changed"]
    if hi < s["lam"] - TOL:
        return "below"
    if lo > s["lam"] + TOL:
        return "above"
    return "straddle"


def crit_bracket(sample):
    """B85-4: the bracket that decides is the one over the columns that moved.

    The bracket over every column is a theorem and is useless. An unchanged column
    has `(pM')_j = lambda p_j` exactly, so the moment one column is left alone the
    bracket contains `lambda` and cannot decide anything. **The first version of this
    criterion used it and reported that the old prices decide nothing at one column,
    which contradicts Theorem 14(1)**: the contradiction is what showed the object
    was wrong, and it was visible only because the counts were printed by set size.

    The discriminant is `[min, max]` of `(pM')_k / p_k` over `k in S`. At `|S| = 1`
    its ends coincide, which is exactly why the old prices always decide there.
    """
    cell_verdict = {"every changed column at or below lambda":
                    "the rate rises, decided at the old prices",
                    "every changed column at or above lambda":
                    "the rate falls, decided at the old prices",
                    "some changed columns each side of lambda":
                    "not decided at the old prices"}
    assert sum(1 for v in cell_verdict.values() if "not decided" in v) == 1, \
        "11c: exactly one cell may be the undecided one"
    holds_all, pinned, partial = 0, 0, 0
    below, above, straddle = [], [], []
    for s in sample:
        lo_a, hi_a = s["bracket_all"]
        if lo_a - TOL <= s["lam2"] <= hi_a + TOL:
            holds_all += 1
        # The all-column bracket has to contain lambda whenever a column is left
        # alone, since that column sits at lambda exactly. Where every column moved
        # there is nothing pinning it, so the claim is only about the partial sets.
        if s["size"] < s["n"]:
            partial += 1
            if lo_a - TOL <= s["lam"] <= hi_a + TOL:
                pinned += 1
        rose = s["r2"] > s["r"] + TOL
        {"below": below, "above": above, "straddle": straddle}[cell_of(s)].append(rose)
    both_ways = bool(straddle) and any(straddle) and not all(straddle)
    # At one column the two ends of the discriminant coincide, so nothing can
    # straddle: that is Theorem 14(1) and it is what tells the right bracket from
    # the wrong one. The all-column bracket puts every partial draw in the straddle
    # cell, single-column ones included, and this clause is what notices.
    singles = [s for s in sample if s["size"] == 1]
    singles_straddling = [s for s in singles if cell_of(s) == "straddle"]
    ok = (holds_all == len(sample) and pinned == partial and partial > 0
          and bool(below) and all(below)
          and bool(above) and not any(above) and both_ways
          and bool(singles) and not singles_straddling)
    detail = (f"the bracket over every column contains the new Perron root on "
              f"{holds_all} of {len(sample)} draws, **and on the {partial} draws that "
              f"leave at least one column alone it contains the old root {pinned} "
              f"times out of {partial}, which is why it decides nothing there**: an "
              f"unchanged column sits at lambda exactly and pins the bracket around "
              f"it. Over the changed columns "
              f"only: below lambda, {len(below)} draws and the rate rises on "
              f"{sum(below)}; above lambda, {len(above)} draws and the rate rises on "
              f"{sum(above)}; **straddling, {len(straddle)} draws, the rate rises on "
              f"{sum(straddle)} and falls on {len(straddle) - sum(straddle)}** -- both "
              f"outcomes inside that cell, which is what makes it undecided rather "
              f"than decorative. **None of the {len(singles)} single-column draws "
              f"straddles**, since there the two ends of the discriminant are the same "
              f"number: that is Theorem 14(1), and it is the clause that tells this "
              f"bracket from the all-column one, which puts every one of them in the "
              f"undecided cell")
    return ok, detail, {"bracket_all_holds": holds_all,
                        "partial_sets": partial,
                        "bracket_all_pinned_at_lambda": pinned,
                        "draws": len(sample),
                        "below": {"n": len(below), "rose": int(sum(below))},
                        "above": {"n": len(above), "rose": int(sum(above))},
                        "straddle": {"n": len(straddle), "rose": int(sum(straddle))},
                        "single_column_draws": len(singles),
                        "single_column_straddling": len(singles_straddling),
                        "cell_verdict": cell_verdict}


def crit_by_size(sample):
    """B85-5: how often the prices in force decide, by how many columns moved."""
    table = {}
    for s in sample:
        d = table.setdefault(s["size"], {"below": 0, "above": 0, "straddle": 0})
        d[cell_of(s)] += 1
    ok = bool(table)
    detail = ("how often the prices in force decide the sign, by the number of columns "
              "replaced at once: "
              + "; ".join(
                  f"{k} column{'s' if k > 1 else ''} -> decided "
                  f"{v['below'] + v['above']} of {sum(v.values())}"
                  for k, v in sorted(table.items()))
              + ". No line is drawn on any of these. **At one column the prices always "
                "decide, which is Theorem 14(1); the share falls as more columns move, "
                "and that fall is the content of this station**")
    return ok, detail, {"by_set_size": {str(k): v for k, v in sorted(table.items())}}


def crit_irreducible(sample):
    """B85-6: Theorem 14 needs M' irreducible, and on this family that is the basket.

    **The load-bearing half is the basket condition.** With `b > 0` and `l' > 0` the
    outer product `b l'` is strictly positive, so `M'` is a positive matrix whatever
    the substitution did to `A`, and the irreducibility test cannot come back false.
    Recomputing it is therefore a check on `B69.irreducible` rather than an
    independent reading, exactly the situation `D35`'s second clause describes, and
    it is guarded by putting a hand-made reducible matrix through the same test.

    Stated this way rather than as three independent clauses because the middle one
    cannot fail while the first holds, and a clause that cannot fail should say so
    instead of standing next to ones that can (rule 11f).
    """
    bad, thin_basket = [], []
    for s in sample:
        b, l2 = np.asarray(s["b"]), np.asarray(s["l2"])
        m2 = B69.augmented(np.asarray(s["a2"]), l2, b)
        if not B69.irreducible(m2):
            bad.append(s["ks"])
        # B69's own sufficient condition, and the reason irreducibility is free
        # here: a strictly positive basket against a strictly positive labour
        # vector makes `b l'` strictly positive, so `M'` is positive whatever the
        # substitution did to `A`.
        if not (b.min() > 0.0 and l2.min() > 0.0):
            thin_basket.append(s["ks"])
    control = np.array([[0.5, 0.0], [0.2, 0.5]])       # commodity 2 reaches nothing
    control_ok = not B69.irreducible(control)
    ok = bool(sample) and not bad and not thin_basket and control_ok
    detail = (f"`M'` is irreducible on {len(sample) - len(bad)} of {len(sample)} draws, "
              f"and the reason is the basket rather than the substitution: a generator "
              f"that produced a zero in the basket would break the theorem's "
              f"hypothesis rather than its conclusion. **The middle clause cannot fail "
              f"while the "
              f"first holds**, so it is a check on the irreducibility test and not a "
              f"third reading (`D35` second clause). The matrix is rebuilt from the "
              f"draw's own "
              f"inputs rather than read off a flag the draw stored. **The mechanism "
              f"is the basket, not the substitution**: the basket is strictly positive "
              f"and the new labour vector is strictly positive on "
              f"{len(sample) - len(thin_basket)} of {len(sample)} draws, so `b l'` is "
              f"strictly positive and `M'` is a positive matrix whatever the "
              f"substitution did to `A`. That is B69's own sufficient condition, read "
              f"back. A matrix that is reducible by hand is put through the same test "
              f"and comes back "
              f"{'reducible, so the test is live' if control_ok else '**irreducible, so the test is broken**'}"
              + ("" if not bad else f". **{len(bad)} are reducible: {bad[:6]}**"))
    return ok, detail, {"reducible_sets": bad, "thin_basket_sets": thin_basket,
                        "control_reports_reducible": control_ok}


def crit_registration():
    """B85-7: B69 registered this, and the same round writes back."""
    doc = (ROOT / "docs" / "b69_okishio.md").read_text(encoding="utf-8")
    named = "b85_simultaneous.md" in doc
    return named, (f"B69's registration of the several-column case is "
                   f"{'named against this station in its own file' if named else '**not written back: its file does not name this station**'}. "
                   f"`D20`: the source of a registration is written back in the round "
                   f"that discharges it"), {"b69_names_b85": named}


# ------------------------------------------------- self-test

def selftest() -> int:
    """Rule 11f: seed the failure rather than ask whether one is possible."""
    fails = []
    rng = np.random.default_rng(4242)
    sample = draws(rng, 6)
    if len(sample) < 40:
        fails.append(f"the fixture drew only {len(sample)} usable systems")

    # the bracket is a theorem, so it must hold on every draw, and it must be tight
    # enough to sit somewhere other than around everything
    for s in sample:
        lo, hi = s["bracket_all"]
        if not (lo - 1e-9 <= s["lam2"] <= hi + 1e-9):
            fails.append(f"the bracket {lo:.6f},{hi:.6f} misses lambda' {s['lam2']:.6f}")
            break

    # each criterion has to fail on an input built to make it fail
    doctored = [dict(s) for s in sample]
    for s in doctored:
        if s["size"] > 1 and all(s["cheaper_each"]):
            s["r2"] = s["r"] - 1.0                       # cheaper everywhere, rate falls
            break
    else:
        fails.append("no draw satisfies B85-2's premise, so its probe cannot be built")
    if crit_forward(doctored)[0]:
        fails.append("a cheaper-everywhere set with a falling rate left B85-2 passing")

    empty_premise = [s for s in sample if s["size"] == 1]
    if crit_forward(empty_premise)[0]:
        fails.append("B85-2 passed on a sample with no several-column draw at all, so "
                     "its premise count is not in the verdict")

    no_converse = [s for s in sample
                   if not (s["size"] > 1 and s["dearer_any"] and s["r2"] > s["r"] + TOL)]
    if crit_converse_fails(no_converse)[0]:
        fails.append("B85-3 claimed the converse fails on a sample containing no case")

    broken = [dict(s) for s in sample]
    broken[0] = dict(broken[0], bracket_all=[1e6, 1e6 + 1.0])
    if crit_bracket(broken)[0]:
        fails.append("a draw whose bracket misses the root left B85-4 passing")

    one_way = [dict(s, bracket_changed=[s["lam"] - 1.0, s["lam"] + 1.0],
                r2=s["r"] + 1.0)
               for s in sample]
    if crit_bracket(one_way)[0]:
        fails.append("a straddling cell that only ever rises left B85-4 passing, so the "
                     "undecided cell is not required to be undecided")

    # B85-1: a single column that got cheaper while the rate fell
    single = [dict(s) for s in sample]
    for s in single:
        if s["size"] == 1 and s["cost_change_by_column"][0] < -TOL:
            s["r2"] = s["r"] - 1.0
            break
    else:
        fails.append("no cheaper single-column draw, so B85-1's probe cannot be built")
    if crit_single_column(single)[0]:
        fails.append("a cheaper single column with a falling rate left B85-1 passing")

    # B85-4: the all-column bracket puts the single-column draws in the undecided cell
    wrong_bracket = [dict(s, bracket_changed=s["bracket_all"]) for s in sample]
    if crit_bracket(wrong_bracket)[0]:
        fails.append("using the all-column bracket as the discriminant left B85-4 "
                     "passing, so it does not tell the two brackets apart")

    # An empty basket takes `b l'` away, and then `M' = A'`, which the hand-made
    # reducible matrix is. Doctoring the stored flag would no longer prove anything,
    # since B85-6 recomputes from the inputs.
    red = [dict(s) for s in sample]
    red[0] = dict(red[0], a2=[[0.5, 0.0], [0.2, 0.5]], l2=[1.0, 1.0], b=[0.0, 0.0])
    if crit_irreducible(red)[0]:
        fails.append("an empty basket on a reducible A' left B85-6 passing")
    if crit_irreducible([dict(s, b=[0.0] * len(s["b"])) for s in sample])[0]:
        fails.append("a basket with a zero in it left B85-6 passing, so the sufficient "
                     "condition it names is not being checked")

    for line in fails:
        print("  SELFTEST FAIL:", line)
    print(f"selftest: {len(fails)} failure(s) over {len(sample)} drawn substitutions")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--systems", type=int, default=N_SYSTEMS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    rng = np.random.default_rng(a.seed)
    sample = draws(rng, a.systems)
    print(f"{len(sample)} substitutions drawn over {a.systems} systems\n")

    spec = [("B85-1", "known_answer", "at one column this reduces to B69's Theorem 14",
             crit_single_column),
            ("B85-2", "own_reading", "every changed column cheaper implies the rate rises",
             crit_forward),
            ("B85-3", "own_reading", "the converse does not extend to several columns",
             crit_converse_fails),
            ("B85-4", "own_reading", "the Collatz-Wielandt bracket and the three cells it "
             "maps to, one of which is undecided at the old prices", crit_bracket),
            ("B85-5", "own_reading", "how often the old prices decide, by how many columns "
             "moved", crit_by_size),
            ("B85-6", "instrument", "M' is irreducible, which Theorem 14 requires",
             crit_irreducible)]
    criteria, report = [], {}
    for name, kind, statement, fn in spec:
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B85-7", "kind": "bookkeeping", "passed": bool(ok),
                     "statement": "B69's registration is discharged and written back",
                     "detail": detail})
    report["B85-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B85-7  [bookkeeping]  {detail[:200]}")

    rec = {"stage": "B85",
           "config": {"seed": a.seed, "systems": a.systems, "set_sizes": list(SET_SIZES),
                      "sets_per_system": N_SETS, "sub_spread": list(B69.SUB_SPREAD),
                      "sizes": list(B69.SIZES), "column_sums": list(B69.COLUMN_SUMS),
                      "basket_values": list(B69.VALUE_OF_BASKET), "tol": TOL,
                      "imports": "b69_okishio"},
           "criteria": criteria, "report": report}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    bad = [c["name"] for c in criteria if not c["passed"]]
    if bad:
        print("FAILED: " + ", ".join(bad))
        return 1
    print(f"\nall {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
