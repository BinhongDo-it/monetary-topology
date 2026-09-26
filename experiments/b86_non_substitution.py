"""B86: the non-substitution theorem, or demand cannot move this field.

B85 showed that with the basket held fixed a cheaper column raises the rate of
profit. **This station holds the rate fixed instead and reads the prices**, and the
same Perron monotonicity gives the classical non-substitution theorem: with one
primary factor, no joint production and constant returns, the cost-minimising
technique and therefore the whole price field depend on the rate and the available
methods only, and not on the composition of final demand.

The load-bearing half is not that prices have no demand term in them, which is true
by inspection of `p = (1+r)pA + wl`. It is that **the componentwise minimum over
techniques is attained by a single technique**, which is what makes "the cheapest
technique" definable without naming a demand vector at all.

Paper station: zero data. The generator is this station's own, since B69's builds
one method per good and this one needs several.

Run:
    python experiments/b86_non_substitution.py
    python experiments/b86_non_substitution.py --selftest
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b86_non_substitution.json"

SEED = 86
N_SYSTEMS = 60
GOODS = (2, 3, 4)
METHODS = (2, 3)
RATES = (0.0, 0.05, 0.10, 0.20)
N_DEMANDS = 6
TOL = 1e-10


# ------------------------------------------------- the model

def prices(a, l, r):
    """p = l [I - (1+r) A]^{-1}, labour the numeraire. None if not viable at r."""
    n = a.shape[0]
    m = np.eye(n) - (1.0 + r) * a
    try:
        p = l @ np.linalg.inv(m)
    except np.linalg.LinAlgError:
        return None
    if not np.all(np.isfinite(p)) or p.min() <= 0.0:
        return None
    return p


def viable(a, r):
    """The Perron root of (1+r)A below one, so the inverse is a positive series."""
    w = np.linalg.eigvals((1.0 + r) * a)
    return float(np.max(w.real)) < 1.0 - 1e-9


def techniques(methods):
    """Every way of picking one method per good. `methods[j]` is a list of (a_j, l_j)."""
    for choice in itertools.product(*[range(len(m)) for m in methods]):
        yield choice


def assemble(methods, choice):
    n = len(methods)
    a = np.zeros((n, n))
    l = np.zeros(n)
    for j, k in enumerate(choice):
        col, lab = methods[j][k]
        a[:, j] = col
        l[j] = lab
    return a, l


def draw_methods(rng, n, per_good):
    """`per_good` methods for each of `n` goods, all productive on their own."""
    out = []
    for _ in range(n):
        ms = []
        for _k in range(per_good):
            col = rng.uniform(0.02, 0.30, n)
            col *= rng.uniform(0.25, 0.75) / col.sum()      # column sum in a safe band
            ms.append((col, float(rng.uniform(0.3, 1.5))))
        out.append(ms)
    return out


def solve_system(methods, r):
    """Every viable technique with its price vector, and the componentwise minimum."""
    rows = []
    for choice in techniques(methods):
        a, l = assemble(methods, choice)
        if not viable(a, r):
            continue
        p = prices(a, l, r)
        if p is None:
            continue
        rows.append({"choice": choice, "a": a, "l": l, "p": p})
    if not rows:
        return None
    stack = np.array([x["p"] for x in rows])
    return {"rows": rows, "componentwise_min": stack.min(axis=0)}


# ------------------------------------------------- criteria

def crit_published(_sample):
    """B86-1: a two-good case worked by hand, so the machinery is anchored.

    A one-good economy is the smallest case where the answer is arithmetic:
    `p = l / (1 - (1+r) a)`, and the cheapest of two methods is the one with the
    smaller `p`, whichever way `l` and `a` trade off. Two goods with two methods
    each is then the smallest case where "componentwise" says anything.
    """
    a1, l1, r = 0.2, 1.0, 0.10
    hand = l1 / (1.0 - (1.0 + r) * a1)
    got = prices(np.array([[a1]]), np.array([l1]), r)
    one_good = got is not None and abs(float(got[0]) - hand) < 1e-12

    # two goods, two methods each, where the cheaper method for good 0 has more
    # labour and less input, so the choice is not readable off either column alone
    methods = [[(np.array([0.10, 0.05]), 0.40), (np.array([0.02, 0.05]), 0.62)],
               [(np.array([0.05, 0.10]), 0.50), (np.array([0.05, 0.30]), 0.20)]]
    s = solve_system(methods, r)
    ok_min = s is not None and any(
        np.allclose(x["p"], s["componentwise_min"], atol=1e-12) for x in s["rows"])
    ok = one_good and ok_min
    detail = (f"one good by hand: `l / (1 - (1+r)a)` = {hand:.10f}, the solver returns "
              f"{float(got[0]):.10f}. Two goods with two methods each, built so the "
              f"cheaper method for the first good carries more labour and less input "
              f"and so cannot be read off either column alone: the componentwise "
              f"minimum "
              + ("is attained by one of the four techniques"
                 if ok_min else "**is attained by none of them**")
              + f", at prices {np.array2string(s['componentwise_min'], precision=6)}"
              if s else ", and the system was not viable")
    return ok, detail, {"one_good_hand": hand, "one_good_solver": float(got[0]),
                        "two_good_min_attained": bool(ok_min)}


def crit_componentwise(sample):
    """B86-2: the componentwise minimum is attained by a single technique."""
    bad, tested = [], 0
    for s in sample:
        sol = s["solution"]
        tested += 1
        if not any(np.allclose(x["p"], sol["componentwise_min"], atol=1e-9)
                   for x in sol["rows"]):
            bad.append({"n": s["n"], "per_good": s["per_good"], "r": s["r"]})
    ok = tested > 0 and not bad
    detail = (f"over {tested} systems, each with every technique enumerated, the "
              f"componentwise minimum of the price vectors is attained by a single "
              f"technique on {tested - len(bad)} of them. **This is the half that makes "
              f"'the cheapest technique' definable without a demand vector**: without "
              f"it one would have to say cheapest for whom. It is the same Perron "
              f"monotonicity B85 uses with the basket fixed, read here with the rate "
              f"fixed instead"
              + ("" if not bad else f". **{len(bad)} counterexamples: {bad[:4]}**"))
    return ok, detail, {"systems": tested, "counterexamples": bad}


def crit_demand(sample):
    """B86-3: demand moves the quantities and leaves the field alone. Both halves."""
    worst_price, least_x = 0.0, float("inf")
    checked = 0
    for s in sample:
        sol = s["solution"]
        best = min(sol["rows"], key=lambda x: float(np.sum(x["p"])))
        a, p = best["a"], best["p"]
        base_p, base_x = None, None
        for d in s["demands"]:
            # the technique and the field are solved without ever seeing d
            x = np.linalg.solve(np.eye(a.shape[0]) - a, d)
            if x.min() <= 0.0:
                continue
            if base_p is None:
                base_p, base_x = p.copy(), x.copy()
                continue
            worst_price = max(worst_price, float(np.max(np.abs(p - base_p))))
            least_x = min(least_x, float(np.max(np.abs(x - base_x))))
            checked += 1
    ok = checked > 0 and worst_price < 1e-12 and least_x > 1e-6
    detail = (f"over {checked} demand pairs: the price field moves by at most "
              f"{worst_price:.2e} **while the quantity vector moves by at least "
              f"{least_x:.4f}**. Both halves are required. A field that did not move "
              f"is also what a demand vector that never reached the solve would look "
              f"like, and the quantity side moving is what says the demand was real. "
              f"Everything cohomological rides on the field, so no square, no `rho` "
              f"and no first Betti number responds to demand either")
    return ok, detail, {"pairs": checked, "worst_price_move": worst_price,
                        "least_quantity_move": least_x}


def _switches_with_demand(rng, n, per_good, r, tries, second_factor):
    """Look for a technique that changes with demand once a hypothesis is dropped.

    With a second primary factor the cheapest technique depends on the two factor
    prices, and those are fixed by demand through the factor market, so the search
    varies the factor price ratio, which is what a demand shift does to it.
    """
    found = []
    for _ in range(tries):
        methods = draw_methods(rng, n, per_good)
        if second_factor:
            land = [[float(rng.uniform(0.05, 1.5)) for _k in range(per_good)]
                    for _j in range(n)]
        winners = set()
        for ratio in (0.2, 1.0, 5.0):
            best, best_cost = None, None
            for choice in techniques(methods):
                a, l = assemble(methods, choice)
                if not viable(a, r):
                    continue
                if second_factor:
                    # labour plus land, priced at `ratio` per unit of land
                    lt = np.array([l[j] + ratio * land[j][choice[j]] for j in range(n)])
                else:
                    lt = l
                p = prices(a, lt, r)
                if p is None:
                    continue
                cost = float(np.sum(p))
                if best_cost is None or cost < best_cost - 1e-12:
                    best, best_cost = choice, cost
            if best is not None:
                winners.add(best)
        if len(winners) > 1:
            found.append({"n": n, "per_good": per_good, "r": r,
                          "winners": sorted(winners)})
    return found


def crit_second_factor(sample, rng, search=None):
    """B86-4: with two primary factors the technique moves. Found, not assumed."""
    search = search or _switches_with_demand
    found = search(rng, 3, 3, 0.05, 60, second_factor=True)
    control = search(rng, 3, 3, 0.05, 60, second_factor=False)
    ok = bool(found) and not control
    detail = (f"with a second primary factor priced at three different ratios, the "
              f"cost-minimising technique changes on {len(found)} of 60 drawn method "
              f"sets"
              + (f", for instance {found[0]['winners']}" if found else "")
              + f". **The same search with one primary factor changes on "
                f"{len(control)} of 60**, which is the control: a search that switched "
                f"under one factor too would be finding its own noise rather than the "
                f"failure of the hypothesis. The second factor is what a demand shift "
                f"reaches, since it moves the factor price ratio, and the theorem's "
                f"first hypothesis is exactly that there is nothing there to move")
    return ok, detail, {"switches_with_two_factors": len(found),
                        "switches_with_one_factor": len(control),
                        "examples": found[:4]}


def crit_joint(sample, rng, tries=200):
    """B86-5: joint production, where the componentwise minimum can go unattained."""
    found, tried = [], 0
    for _ in range(tries):
        n, per_good, r = 2, 2, 0.05
        methods = []
        for _j in range(n):
            ms = []
            for _k in range(per_good):
                inp = rng.uniform(0.02, 0.30, n)
                inp *= rng.uniform(0.25, 0.6) / inp.sum()
                outp = np.zeros(n)
                outp[_j] = 1.0
                outp[1 - _j] = float(rng.uniform(0.0, 0.6))     # the joint product
                ms.append((inp, outp, float(rng.uniform(0.3, 1.5))))
            methods.append(ms)
        stack = []
        for choice in itertools.product(*[range(per_good)] * n):
            aa = np.column_stack([methods[j][choice[j]][0] for j in range(n)])
            bb = np.column_stack([methods[j][choice[j]][1] for j in range(n)])
            ll = np.array([methods[j][choice[j]][2] for j in range(n)])
            m = bb - (1.0 + r) * aa
            try:
                p = ll @ np.linalg.inv(m)
            except np.linalg.LinAlgError:
                continue
            if not np.all(np.isfinite(p)) or p.min() <= 0.0:
                continue
            stack.append(p)
        if len(stack) < 2:
            continue
        tried += 1
        arr = np.array(stack)
        cw = arr.min(axis=0)
        if not any(np.allclose(p, cw, atol=1e-9) for p in arr):
            found.append({"componentwise_min": cw.tolist(),
                          "prices": [p.tolist() for p in arr]})
    ok = bool(found)
    detail = (f"under joint production, where a method makes more than one good, the "
              f"componentwise minimum is attained by no single technique on "
              f"{len(found)} of {tried} viable systems"
              + (f", the first at {np.array2string(np.array(found[0]['componentwise_min']), precision=5)}"
                 if found else "")
              + f". **B70 already showed that joint production parts the cycles from "
                f"the commodities**, so this failure is derived rather than newly "
                f"assumed: without one good per method there is no lattice of columns "
                f"for the monotonicity to run on"
              + ("" if found else ". Recorded as not found on this family rather than "
                                  "as not existing"))
    return ok, detail, {"found": len(found), "viable_systems": tried,
                        "examples": found[:2]}


def crit_enumeration(sample):
    """B86-6: the enumeration is complete, which everything above rests on."""
    bad = []
    for s in sample:
        want = s["per_good"] ** s["n"]
        got = s["enumerated"]
        if got != want:
            bad.append({"n": s["n"], "per_good": s["per_good"], "want": want, "got": got})
    ok = bool(sample) and not bad
    detail = (f"every technique is enumerated on {len(sample) - len(bad)} of "
              f"{len(sample)} systems: the count equals the product of the per-good "
              f"method counts. **Everything above is a statement about a minimum over "
              f"a set**, so a set that is short by one member would make all of it a "
              f"statement about a different set, and nothing else here would notice"
              + ("" if not bad else f". **{len(bad)} are short: {bad[:4]}**"))
    return ok, detail, {"short": bad}


def crit_registration():
    """B86-7: the relation to B85, written where B85 can be found from."""
    doc = (ROOT / "docs" / "b85_simultaneous.md").read_text(encoding="utf-8")
    named = "b86_non_substitution.md" in doc
    return named, (f"B85's file "
                   f"{'names this station as the same monotonicity with the rate held fixed instead of the basket' if named else '**does not name this station: the write-back is missing**'}. "
                   f"`D20`: the pair is written where a reader of either one finds it"), \
        {"b85_names_b86": named}


# ------------------------------------------------- sample

def draws(rng, n_systems):
    out = []
    for _ in range(n_systems):
        n = int(rng.choice(GOODS))
        per_good = int(rng.choice(METHODS))
        methods = draw_methods(rng, n, per_good)
        for r in RATES:
            sol = solve_system(methods, r)
            if sol is None or len(sol["rows"]) < 2:
                continue
            demands = [rng.uniform(0.1, 3.0, n) for _ in range(N_DEMANDS)]
            out.append({"n": n, "per_good": per_good, "r": r, "solution": sol,
                        "demands": demands, "enumerated": len(sol["rows"])})
    return out


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(999)
    sample = draws(rng, 8)
    if len(sample) < 8:
        fails.append(f"the fixture drew only {len(sample)} systems")

    ok, _, _ = crit_published(sample)
    if not ok:
        fails.append("the hand-checked case does not come back")

    # a componentwise minimum attained by nobody must fail B86-2
    broken = [dict(s) for s in sample]
    sol = dict(broken[0]["solution"])
    sol["componentwise_min"] = sol["componentwise_min"] - 1.0
    broken[0] = dict(broken[0], solution=sol)
    if crit_componentwise(broken)[0]:
        fails.append("a minimum attained by no technique left B86-2 passing")

    # a demand that never reaches the quantities must fail B86-3
    frozen = [dict(s, demands=[s["demands"][0]] * len(s["demands"])) for s in sample]
    if crit_demand(frozen)[0]:
        fails.append("identical demand vectors left B86-3 passing, so its second half "
                     "is not being required")

    # an enumeration short by one must fail B86-6
    short = [dict(s) for s in sample]
    short[0] = dict(short[0], enumerated=short[0]["enumerated"] - 1)
    if crit_enumeration(short)[0]:
        fails.append("an enumeration short by one left B86-6 passing")

    if crit_componentwise([])[0]:
        fails.append("B86-2 passed on an empty sample")

    # B86-4: a control that switches too means the search is finding its own noise,
    # and the criterion has to say so rather than keep the treatment arm's count
    def _both_switch(_rng, *_a, **_k):
        return [{"n": 3, "per_good": 3, "r": 0.05, "winners": [(0, 0, 0), (1, 1, 1)]}]
    if crit_second_factor(sample, rng, search=_both_switch)[0]:
        fails.append("a one-factor control that switches as often as the treatment "
                     "left B86-4 passing, so the control is not being read")

    # B86-5: it has to find its case, not assert it
    if crit_joint(sample, np.random.default_rng(3), tries=0)[0]:
        fails.append("B86-5 passed having searched nothing, so it asserts rather "
                     "than finds")

    # B86-1: the hand-checked arithmetic has to be compared
    real_prices = prices
    try:
        globals()["prices"] = lambda a, l, r: (
            None if real_prices(a, l, r) is None else real_prices(a, l, r) * 1.5)
        if crit_published(sample)[0]:
            fails.append("a solver off by half left B86-1 passing, so its hand value "
                         "is not being compared")
    finally:
        globals()["prices"] = real_prices

    for line in fails:
        print("  SELFTEST FAIL:", line)
    print(f"selftest: {len(fails)} failure(s) over {len(sample)} systems")
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
    print(f"{len(sample)} (system, rate) pairs, "
          f"{sum(s['enumerated'] for s in sample)} techniques enumerated\n")

    criteria, report = [], {}
    spec = [("B86-1", "known_answer", "a hand-checked case anchors the machinery",
             lambda: crit_published(sample)),
            ("B86-2", "own_reading", "the componentwise minimum is attained by a single "
             "technique, which is what makes the cheapest technique definable without "
             "a demand vector", lambda: crit_componentwise(sample)),
            ("B86-3", "own_reading", "demand moves the quantities and leaves the field "
             "alone", lambda: crit_demand(sample)),
            ("B86-4", "own_reading", "with a second primary factor the technique moves "
             "with demand", lambda: crit_second_factor(sample, np.random.default_rng(a.seed + 1))),
            ("B86-5", "own_reading", "under joint production the componentwise minimum "
             "can be attained by nobody", lambda: crit_joint(sample, np.random.default_rng(a.seed + 2))),
            ("B86-6", "instrument", "the enumeration over techniques is complete",
             lambda: crit_enumeration(sample)),
            ("B86-7", "bookkeeping", "the pair with B85 is written where either one is "
             "found from", crit_registration)]
    for name, kind, statement, fn in spec:
        ok, detail, rep = fn()
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")

    rec = {"stage": "B86",
           "config": {"seed": a.seed, "systems": a.systems, "goods": list(GOODS),
                      "methods_per_good": list(METHODS), "rates": list(RATES),
                      "demands_per_system": N_DEMANDS, "tol": TOL},
           "criteria": criteria, "report": report}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    bad = [c["name"] for c in criteria if not c["passed"]]
    if bad:
        print("FAILED: " + ", ".join(bad))
        return 1
    print(f"all {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
