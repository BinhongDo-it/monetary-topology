"""B88: the two margins cannot both be open, because they supply the same missing equation.

B87 left the field at the intensive step registered: it drew the graph there and read `b1`,
but did not solve for the wage, because two methods on one acre need B73's extra equation.
B73 has it. Joining them gives a constraint neither station could state alone.

**Count the extensive system.** With `k` lands all cultivated there are `k` price equations in
`k + 1` unknowns, the wage and one rent per land. It is short by one, and B72 closes it with a
boundary condition: the marginal land pays no rent.

**Count the mixed system.** Put a second method on one acre and there are `k + 1` equations in
the same `k + 1` unknowns. **It is square, so it closes itself**, and B73's cycle is what does
the closing. Keeping the boundary condition as well would over-determine it.

**So the boundary condition is not dropped by choice, it is displaced**, and what follows from
displacing it is that the land which used to be marginal starts paying rent. Free land
disappears at the intensive margin. The mixed system is viable exactly when the intensive
closure's wage lies on or below the extensive envelope, which is the same envelope rule B72
gave for lands, applied now to a closure rather than to a land.

B72's envelope solver and land generator and B73's intensive pair are imported rather than
rewritten, so a disagreement between the three stations is a real one.

Run:
    python experiments/b88_two_margins.py
    python experiments/b88_two_margins.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b72_land_and_rent as B72                            # noqa: E402
import b73_two_extensions as B73                           # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b88_two_margins.json"

SEED = 88
N_SYSTEMS = 3000
LANDS = (2, 7)                 # k drawn uniformly on [2, 7)
RATE = 0.05
YIELD = (1.05, 2.00)           # corn per acre under the second method, against 1.0 under the first
CORN_FACTOR = (1.0, 3.0)       # its corn input, as a multiple of the acre's own
LABOUR_FACTOR = (1.0, 3.0)     # its labour input, as a multiple of the acre's own
TOL = 1e-12


def extensive(alphas, lams, r):
    """B72's answer: the wage is the envelope and the land that attains it pays no rent."""
    w, marginal, rents = B72.solve(alphas, lams, r)
    return {"wage": float(w), "marginal": int(marginal), "rents": rents}


def mixed(alphas, lams, i, dose, r):
    """Land `i` worked by two methods, every land cultivated, and no boundary condition.

    B73's pair is the closure. The other lands' rents then follow from their own equations,
    which is where a boundary condition would have gone.
    """
    q2, c, d = dose
    w, rho_i, m = B73.intensive((1.0, q2), (alphas[i], alphas[i] * c),
                                (lams[i], lams[i] * d), r)
    if w is None:
        return None
    rents = 1.0 - (1.0 + r) * alphas - w * lams
    return {"wage": float(w), "rents": rents, "rho_own": float(rho_i),
            "det": float(np.linalg.det(m)), "land": int(i)}


def cell_of(w_int, w_ext, w_own):
    """One number against two thresholds. The middle cell is the one neither station had."""
    if not np.isfinite(w_int) or w_int <= 0.0:
        return "wage non-positive"
    if w_int > w_own + TOL:
        return "not worth operating on its own acre"
    if w_int > w_ext + TOL:
        return "profitable on its own acre and infeasible for the system"
    return "viable"


def draws(rng, n_systems):
    out = []
    for _ in range(n_systems):
        k = int(rng.integers(LANDS[0], LANDS[1]))
        alphas, lams = B72.random_lands(rng, k)
        own = B72.wage_curve(alphas, lams, RATE)
        if own.min() <= 0.0:
            continue
        ext = extensive(alphas, lams, RATE)
        if ext["wage"] <= 0.0:
            continue
        # one intensification technology per system, the same extra dose on whichever acre it
        # goes: that is what makes "which acre gets it" a reading rather than a draw
        dose = (float(rng.uniform(*YIELD)), float(rng.uniform(*CORN_FACTOR)),
                float(rng.uniform(*LABOUR_FACTOR)))
        per_land = [mixed(alphas, lams, i, dose, RATE) for i in range(k)]
        out.append({"k": k, "alphas": alphas, "lams": lams, "own": own, "ext": ext,
                    "dose": dose, "per_land": per_land,
                    "best": int(np.argmax(own))})
    return out


# ------------------------------------------------- criteria

def crit_reduces(sample):
    """B88-1: the rent equation is B72's, and the pair is solved as B73 solves it."""
    worst_rent = 0.0
    for s in sample:
        r_here = 1.0 - (1.0 + RATE) * s["alphas"] - s["ext"]["wage"] * s["lams"]
        worst_rent = max(worst_rent, float(np.abs(r_here - s["ext"]["rents"]).max()))
    # a pair solved by hand: q = (1, 1.5), a = (0.2, 0.5), l = (0.4, 0.9), r = 0
    # 1 = 0.2 + 0.4w + p and 1.5 = 0.5 + 0.9w + p, so 0.5 = 0.3 + 0.5w, w = 0.4, p = 0.64
    w_h, rho_h, _m = B73.intensive((1.0, 1.5), (0.2, 0.5), (0.4, 0.9), 0.0)
    hand = abs(w_h - 0.4) < 1e-12 and abs(rho_h - 0.64) < 1e-12
    ok = bool(sample) and worst_rent < 1e-12 and hand
    detail = (f"the rent this station writes on a land not being intensified reproduces B72's "
              f"own rent to {worst_rent:.2e} over {len(sample)} systems, and a pair solved by "
              f"hand at `q = (1, 1.5)`, `a = (0.2, 0.5)`, `l = (0.4, 0.9)`, `r = 0` gives "
              f"`w = 0.4` and `rho = 0.64` against the solver's {w_h:.10f} and {rho_h:.10f}. "
              f"**Both solvers are imported rather than copied**, so the three stations can "
              f"disagree")
    return ok, detail, {"worst_rent_gap": worst_rent, "hand_pair": bool(hand),
                        "systems": len(sample)}


def crit_counting(sample):
    """B88-2: extensive is short by one and mixed is square, so the boundary has to go."""
    worst_ext, least_mixed, n_mixed = 0.0, np.inf, 0
    shapes = set()
    for s in sample:
        k = s["k"]
        shapes.add(("extensive", k, k + 1))            # equations, unknowns
        marg = s["ext"]["marginal"]
        worst_ext = max(worst_ext, abs(float(s["ext"]["rents"][marg])))
        for m in s["per_land"]:
            if m is None:
                continue
            shapes.add(("mixed", k + 1, k + 1))
            n_mixed += 1
            least_mixed = min(least_mixed, abs(float(m["rents"][marg])))
    listed = sorted(shapes)
    counting_ok = all(eq + 1 == un for tag, eq, un in shapes if tag == "extensive") and \
                  all(eq == un for tag, eq, un in shapes if tag == "mixed")
    ok = bool(sample) and counting_ok and worst_ext < 1e-12 and least_mixed > 1e-9
    detail = (f"with `k` lands all cultivated there are `k` equations in `k + 1` unknowns, the "
              f"wage and one rent per land, and B72's boundary condition supplies the missing "
              f"one: the marginal land's rent is zero to {worst_ext:.2e}. **Put a second method "
              f"on one acre and there are `k + 1` equations in the same `k + 1` unknowns, so "
              f"the system closes itself and the boundary condition has nowhere to go.** "
              f"Measured rather than argued: over {n_mixed} mixed configurations the rent the "
              f"boundary condition would set to zero comes out at least {least_mixed:.4f} away "
              f"from it. **The extensive run is the control and gives exactly zero on the same "
              f"quantity**, so this is the two closures disagreeing and not a solver tolerance. "
              f"The shapes are printed rather than counted: "
              + "; ".join(f"{tag} k={eq if tag == 'extensive' else eq - 1} -> {eq} by {un}"
                          for tag, eq, un in listed))
    return ok, detail, {"worst_extensive_marginal_rent": worst_ext,
                        "least_mixed_marginal_rent": None if not np.isfinite(least_mixed)
                        else float(least_mixed),
                        "mixed_configurations": n_mixed,
                        "shapes": [list(x) for x in listed]}


def crit_cells(sample):
    """B88-3: one number against two thresholds, and the middle cell is the new one."""
    cells = {}
    for s in sample:
        for i, m in enumerate(s["per_land"]):
            w_int = np.inf if m is None else m["wage"]
            c = cell_of(w_int, s["ext"]["wage"], float(s["own"][i]))
            cells[c] = cells.get(c, 0) + 1
    named = ["wage non-positive", "not worth operating on its own acre",
             "profitable on its own acre and infeasible for the system", "viable"]
    ok = bool(sample) and all(cells.get(c, 0) > 0 for c in named)
    parts = "; ".join(f"{c} {cells.get(c, 0)}" for c in named)
    detail = (f"the mixed system's standing is one number, the intensive closure's wage, read "
              f"against two thresholds, the acre's own wage curve and the extensive envelope. "
              f"Four cells and all four occur on {sum(cells.values())} drawn configurations: "
              f"{parts}. **The third is the one neither B72 nor B73 could state**: the second "
              f"method pays a non-negative rent on its own acre and still drives some other "
              f"land's rent below zero, because it is the whole system's wage it moves. "
              f"**A one-land model cannot see it and an extensive model has no second method**")
    return ok, detail, {"cells": cells}


def crit_equivalence(sample):
    """B88-4: an implementation check, not a finding. The equivalence is algebra."""
    agree = total = 0
    for s in sample:
        for m in s["per_land"]:
            if m is None or m["wage"] <= 0.0:
                continue
            total += 1
            below = m["wage"] <= s["ext"]["wage"] + TOL
            feasible = float(m["rents"].min()) >= -TOL
            agree += int(below == feasible)
    ok = total > 0 and agree == total
    detail = (f"`w_int <= w_ext` and `every rent >= 0` agree on {agree} of {total} "
              f"configurations. **This is an implementation check and not a reading** "
              f"(`D35` second clause): a rent is `1 - (1+r)a - w l`, decreasing in the wage, "
              f"and the marginal land's is zero exactly at `w_ext`, so the two statements are "
              f"one statement. What it can catch is the code not implementing it")
    return ok, detail, {"agree": agree, "configurations": total}


def crit_no_free_land(sample):
    """B88-5: in the viable cell the land that was marginal pays rent."""
    viable = strictly = 0
    least = np.inf
    for s in sample:
        marg = s["ext"]["marginal"]
        for i, m in enumerate(s["per_land"]):
            if m is None:
                continue
            if cell_of(m["wage"], s["ext"]["wage"], float(s["own"][i])) != "viable":
                continue
            viable += 1
            rho_marg = float(m["rents"][marg])
            if rho_marg > TOL:
                strictly += 1
                least = min(least, rho_marg)
    ok = viable > 0 and strictly == viable
    detail = (f"on {strictly} of {viable} viable configurations the land that paid no rent "
              f"under extensive cultivation pays a strictly positive one once the second "
              f"method is in, the smallest being {0.0 if not np.isfinite(least) else least:.4f}. "
              f"**Free land disappears at the intensive margin**, and it does so because the "
              f"boundary condition that made it free is the equation the cycle replaced. "
              f"**Not implied by the cell being viable**: viability asks for rents at or above "
              f"zero and would be satisfied by a marginal rent of exactly zero, which is what "
              f"a boundary condition surviving the step would look like")
    return ok, detail, {"viable": viable, "strictly_positive": strictly,
                        "least": None if not np.isfinite(least) else float(least)}


def crit_which_land(sample):
    """B88-6: which acre gets the second method, and B87 assumed the wrong one."""
    picked_best = picked_marg = systems = differ = 0
    orders_same = orders_seen = 0
    for s in sample:
        ws = np.array([np.nan if m is None else m["wage"] for m in s["per_land"]])
        live = np.isfinite(ws) & (ws > 0.0)
        ok_cells = live & (ws <= s["ext"]["wage"] + TOL)
        if not ok_cells.any():
            continue
        systems += 1
        # the operated one is the cheapest intensification, so the one leaving the highest wage
        pick = int(np.where(ok_cells, ws, -np.inf).argmax())
        # the same choice made by fertility instead, over the same candidates: two rules, and
        # counting where they part is what says the closure is doing the choosing
        by_fert = int(np.where(ok_cells, np.asarray(s["own"], dtype=float), -np.inf).argmax())
        differ += int(pick != by_fert)
        picked_best += int(pick == s["best"])
        picked_marg += int(pick == s["ext"]["marginal"])
        if live.sum() >= 2:
            orders_seen += 1
            a = np.argsort(-np.asarray(s["own"])[live])
            b = np.argsort(-ws[live])
            orders_same += int(bool((a == b).all()))
    ok = (systems > 0 and differ > 0 and picked_best < systems
          and orders_same < orders_seen)
    detail = (f"one intensification technology per system, the same extra dose on whichever "
              f"acre it goes, so which acre gets it is a reading and not a draw. On {systems} "
              f"systems where some acre can take it, **the acre that does is the most fertile "
              f"one on {picked_best} of them and the marginal one on {picked_marg}**. The order "
              f"of fertility and the order by intensive closure are the same on {orders_same} "
              f"of {orders_seen} systems and differ on {orders_seen - orders_same}. "
              f"**Both choosing rules are run over the same candidates and they part on "
              f"{differ} of {systems} systems**, which is what says the closure and not the "
              f"fertility is choosing. "
              f"**B87 put the second method on the best land by fiat and that is wrong**; its "
              f"graph reading survives because any acre with two users closes a cycle, and its "
              f"field reading would not have")
    return ok, detail, {"systems": systems, "rules_part": differ, "picked_best": picked_best,
                        "picked_marginal": picked_marg, "orders_same": orders_same,
                        "orders_seen": orders_seen}


def crit_registration():
    """B88-7: the same round writes back to the three stations this one joins."""
    want = {"b87_demand_grip.md": "b88_two_margins.md",
            "b73_two_extensions.md": "b88_two_margins.md",
            "b72_land_and_rent.md": "b88_two_margins.md"}
    missing = [f for f, needle in want.items()
               if needle not in (ROOT / "docs" / f).read_text(encoding="utf-8")]
    ok = not missing
    detail = (f"the three files this station joins "
              f"{'each name it' if ok else '**do not all name it: ' + ', '.join(missing) + '**'}, "
              f"so a reader of any of them finds where the boundary condition went. `D20`")
    return ok, detail, {"missing_writebacks": missing}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(11)
    sample = draws(rng, 300)
    if len(sample) < 100:
        fails.append(f"the fixture drew only {len(sample)} systems")

    named = (("B88-1", crit_reduces), ("B88-2", crit_counting), ("B88-3", crit_cells),
             ("B88-4", crit_equivalence), ("B88-5", crit_no_free_land),
             ("B88-6", crit_which_land))
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:120]}")
        if fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # B88-1: a rent equation off by the rate is what a copied rather than imported formula
    # would look like
    bent = [dict(s, ext=dict(s["ext"], rents=s["ext"]["rents"] + 1e-6)) for s in sample]
    if crit_reduces(bent)[0]:
        fails.append("B88-1 passes when the rent equation and B72's disagree")

    # B88-2: if the mixed closure returned the extensive wage, the boundary condition would
    # survive the step and the whole station would be empty
    flat = []
    for s in sample:
        pl = [None if m is None else dict(m, rents=1.0 - (1.0 + RATE) * s["alphas"]
                                          - s["ext"]["wage"] * s["lams"])
              for m in s["per_land"]]
        flat.append(dict(s, per_land=pl))
    if crit_counting(flat)[0]:
        fails.append("B88-2 passes when the mixed closure agrees with the boundary condition")

    # B88-3: collapsing the two thresholds into one loses the middle cell, which is the only
    # thing this station reads that neither B72 nor B73 could
    one_threshold = {}
    for s in sample:
        for i, m in enumerate(s["per_land"]):
            w = np.inf if m is None else m["wage"]
            c = ("viable" if np.isfinite(w) and 0.0 < w <= s["ext"]["wage"] + TOL
                 else "not worth operating on its own acre")
            one_threshold[c] = one_threshold.get(c, 0) + 1
    if one_threshold.get("profitable on its own acre and infeasible for the system", 0) != 0:
        fails.append("the one-threshold probe still finds the middle cell")

    # B88-5: a marginal rent of exactly zero is what a boundary condition surviving the step
    # would look like, and the criterion has to reject it
    zeroed = []
    for s in sample:
        marg = s["ext"]["marginal"]
        pl = []
        for m in s["per_land"]:
            if m is None:
                pl.append(None); continue
            rr = m["rents"].copy(); rr[marg] = 0.0
            pl.append(dict(m, rents=rr))
        zeroed.append(dict(s, per_land=pl))
    if crit_no_free_land(zeroed)[0]:
        fails.append("B88-5 passes when the formerly marginal land is left paying nothing")

    # B88-6: if the acre that takes the second method were simply the most fertile one, the
    # station would be reporting B87's fiat back to itself. Order the closures by fertility and
    # the criterion has to reject it
    by_fertility = []
    for s in sample:
        own = np.asarray(s["own"], dtype=float)
        scale = s["ext"]["wage"] / (own.max() + 1.0)
        pl = [None if m is None else dict(m, wage=float(own[i] * scale))
              for i, m in enumerate(s["per_land"])]
        by_fertility.append(dict(s, per_land=pl))
    if crit_which_land(by_fertility)[0]:
        fails.append("B88-6 passes when the acre taken is always the most fertile one")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s) over {len(sample)} systems")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--systems", type=int, default=N_SYSTEMS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.systems)
    configs = sum(1 for s in sample for m in s["per_land"] if m is not None)
    print(f"{len(sample)} systems, {configs} mixed configurations\n")

    criteria, report = [], {}
    for name, kind, fn in (("B88-1", "known_answer", crit_reduces),
                           ("B88-2", "own_reading", crit_counting),
                           ("B88-3", "own_reading", crit_cells),
                           ("B88-4", "instrument", crit_equivalence),
                           ("B88-5", "own_reading", crit_no_free_land),
                           ("B88-6", "own_reading", crit_which_land)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B88-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B88-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B88-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B88",
        "config": {"seed": args.seed, "systems": args.systems, "lands": list(LANDS),
                   "rate": RATE, "yield": list(YIELD), "corn_factor": list(CORN_FACTOR),
                   "labour_factor": list(LABOUR_FACTOR),
                   "imports": "b72_land_and_rent, b73_two_extensions"},
        "report": report,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    bad = [c["name"] for c in criteria if not c["passed"]]
    print((f"all {len(criteria)} criteria pass; record written" if not bad
           else "FAILED: " + ", ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
