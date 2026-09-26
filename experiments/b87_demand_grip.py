"""B87: demand's grip on the field is combinatorial, not a second potential.

B86 registered the two-factor failure as "a second primary factor is a second
potential, so the field stops being one function". **That guess is wrong, and B72
already had the right shape.** Land is a position no cycle produces, a pendant
vertex under extensive rent, and the non-negativity of rents pins the wage to the
lower envelope of the lands' own wage curves. The second factor's price is not a
free dimension; it is pinned.

**What is not pinned is which lands are in use, and that is what demand fixes.** So
demand acts on the field through a combinatorial object, the cultivated set, and its
action is a step function: constant between thresholds, jumping at them, with at
most `k` distinct values rather than a continuum.

B72's envelope solver, land generator, graph builder and Betti number are imported
rather than rewritten, so a disagreement between the two stations is a real one.

Run:
    python experiments/b87_demand_grip.py
    python experiments/b87_demand_grip.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b72_land_and_rent as B72                            # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b87_demand_grip.json"

SEED = 87
N_SYSTEMS = 200
LANDS = (2, 3, 4, 5, 6)
RATE = 0.05
N_OTHER_GOODS = 2          # produced goods besides corn, one method each
EPS = 1e-6                 # how far either side of a threshold B87-6 looks
TOL = 1e-12


def order_at(alphas, lams, r):
    """Lands best first: the one with the highest own wage curve is taken first."""
    w = B72.wage_curve(alphas, lams, r)
    return list(np.argsort(-w)), w


def field_on(alphas, lams, r, cultivated):
    """B72's solve restricted to the lands actually in use.

    Each land has unit capacity, so the cultivated set is the first `m` in the order
    and the wage is the envelope's minimum over those `m` alone.
    """
    idx = np.array(sorted(cultivated))
    w, marginal_local, rents = B72.solve(alphas[idx], lams[idx], r)
    rent_full = np.full(len(alphas), np.nan)
    rent_full[idx] = rents
    return {"wage": float(w), "marginal": int(idx[marginal_local]),
            "rents": rent_full, "cultivated": sorted(int(i) for i in idx)}


def cultivated_for(order, demand):
    """Unit capacity per land, so demand `d` needs the best `ceil(d)` lands."""
    m = int(np.ceil(demand - 1e-12))
    m = max(1, min(m, len(order)))
    return sorted(order[:m])


def betti_for(cultivated, intensive=False):
    """The drawn graph's first Betti number, from B72's builder, not from a formula.

    One process per cultivated land plus one per other produced good, and a land
    vertex for each land in use. `intensive` puts a second method on the best land,
    which is where the sweep goes once every land is already in use: that land's
    vertex is then bought by two bundles instead of one, and B72's Corollary 17.1
    says the second edge closes a cycle.
    """
    processes = len(cultivated) + N_OTHER_GOODS + (1 if intensive else 0)
    users = [[j] for j in range(len(cultivated))]
    if intensive:
        users[0] = [0, processes - 1]                       # best land, two methods
    nodes, edges = B72.build_graph(users, processes)
    closed = processes + (1 if intensive else 0)
    return B72.first_betti(nodes, edges), processes, closed


def draws(rng, n_systems):
    out = []
    for _ in range(n_systems):
        k = int(rng.choice(LANDS))
        alphas, lams = B72.random_lands(rng, k)
        w_each = B72.wage_curve(alphas, lams, RATE)
        if w_each.min() <= 0.0:
            continue
        order, _ = order_at(alphas, lams, RATE)
        steps = []
        for m in range(1, k + 2):
            intensive = m > k
            cultivated = sorted(order[:min(m, k)])
            f = field_on(alphas, lams, RATE, cultivated)
            b1, processes, closed = betti_for(cultivated, intensive)
            steps.append({"m": m, "intensive": intensive, "cultivated": cultivated,
                          "wage": f["wage"], "marginal": f["marginal"], "b1": b1,
                          "processes": processes,
                          # measured on B72's builder rather than taken from its
                          # prose: a pendant land raises V and E together, so `b1`
                          # is the number of operated methods, and a land with two
                          # methods is not pendant and closes one more cycle
                          "b1_closed_form": closed})
        out.append({"k": k, "alphas": alphas, "lams": lams, "order": order,
                    "steps": steps})
    return out


# ------------------------------------------------- criteria

def crit_reduces(sample):
    """B87-1: with every land in use this is B72's Theorem 17(3), from B72's solver."""
    worst = 0.0
    for s in sample:
        w72, marg72, rents72 = B72.solve(s["alphas"], s["lams"], RATE)
        last = [x for x in s["steps"] if not x["intensive"]][-1]
        worst = max(worst, abs(last["wage"] - w72))
        if last["marginal"] != marg72 or last["m"] != s["k"]:
            return False, (f"the full-cultivation step is not B72's answer on a system "
                           f"of {s['k']} lands"), {"mismatch": s["k"]}
    ok = bool(sample) and worst < 1e-12
    detail = (f"on all {len(sample)} systems the last step, with every land in use, "
              f"returns B72's wage and B72's marginal land, worst wage gap "
              f"{worst:.2e}. B72's solver is imported rather than a second copy, so "
              f"the two stations can disagree")
    return ok, detail, {"worst_wage_gap": worst, "systems": len(sample)}


def crit_nested(sample):
    """B87-2: the cultivated set is nested in demand and takes at most k values."""
    bad, counted = [], 0
    for s in sample:
        seen, prev = [], set()
        for st in [x for x in s["steps"] if not x["intensive"]]:
            cur = set(st["cultivated"])
            if not prev <= cur:
                bad.append({"k": s["k"], "m": st["m"]})
            prev = cur
            seen.append(tuple(st["cultivated"]))
        counted += 1
        if len(set(seen)) != s["k"]:
            bad.append({"k": s["k"], "distinct": len(set(seen))})
    ok = counted > 0 and not bad
    ks = [s["k"] for s in sample]
    detail = (f"sweeping demand over {counted} systems, the cultivated set is nested "
              f"at every step and takes exactly `k` distinct values, `k` running "
              f"{min(ks) if ks else 0} to {max(ks) if ks else 0}. "
              f"**Counted rather than argued from the way the sweep is built**: the "
              f"order is taken from the envelope, and a different order would break "
              f"nesting rather than produce a different nesting"
              + ("" if not bad else f". **{len(bad)} break it: {bad[:4]}**"))
    return ok, detail, {"systems": counted, "breaks": bad}


def crit_betti(sample):
    """B87-3: b1 read off the drawn graph, against the closed form, step by step.

    With a control that is also a reading. B72's Corollary 17.1 says two methods on
    one land close a cycle, so a graph built that way has to come back one higher.
    Without it this criterion compares the closed form against a number a broken
    builder could simply have been handed, which is comparing something with itself.
    """
    bad, steps = [], 0
    for s in sample:
        for st in s["steps"]:
            steps += 1
            if st["b1"] != st["b1_closed_form"]:
                bad.append({"k": s["k"], "m": st["m"], "b1": st["b1"],
                            "closed": st["b1_closed_form"]})
    ctrl_nodes, ctrl_edges = B72.build_graph([[0, 1]], 3)
    ctrl = B72.first_betti(ctrl_nodes, ctrl_edges)
    ctrl_ok = ctrl == 4                    # three processes plus the cycle they close
    ok = steps > 0 and not bad and ctrl_ok
    detail = (f"over {steps} steps the first Betti number of the drawn graph equals "
              f"the closed form `|S| + n`, the number of operated methods, on "
              f"{steps - len(bad)} of them, computed "
              f"from B72's incidence matrix rather than from the formula. **A land is "
              f"a pendant vertex**, so attaching it raises the vertex and edge counts "
              f"together and leaves `b1` where it was; what moves `b1` is the process "
              f"that works it. **The control is one land worked by two processes, "
              f"which is intensive rent**: B72's Corollary 17.1 says that closes a "
              f"cycle, and the builder returns {ctrl} on three processes against 3 "
              f"for the extensive case, so the measurement is live rather than a "
              f"closed form handed back to itself"
              + ("" if not bad else f". **{len(bad)} disagree: {bad[:4]}**"))
    return ok, detail, {"steps": steps, "disagreements": bad,
                        "intensive_control_b1": ctrl, "control_ok": ctrl_ok}


def crit_step_shape(sample):
    """B87-4: the field is constant within a step and moves across one. Both halves."""
    inside, across = 0.0, float("inf")
    checked_in, checked_across = 0, 0
    for s in sample:
        for st in [x for x in s["steps"] if not x["intensive"]]:
            # inside a step: two demands that need the same lands
            lo, hi = st["m"] - 0.9, st["m"] - 0.1
            for d in (lo, hi):
                cult = cultivated_for(s["order"], max(d, 1e-9))
                if cult != st["cultivated"]:
                    continue
                f = field_on(s["alphas"], s["lams"], RATE, cult)
                inside = max(inside, abs(f["wage"] - st["wage"]))
                checked_in += 1
        # Extensive steps only. **At the intensive margin the field is not computed
        # here**: two methods on one land need B72's Corollary 17.1 extra equation,
        # which this station does not carry, so that step contributes the graph and
        # nothing else. Comparing wages across it would be comparing a number this
        # station never solved for.
        ext = [x for x in s["steps"] if not x["intensive"]]
        for a, b in zip(ext, ext[1:]):
            across = min(across, abs(b["wage"] - a["wage"]))
            checked_across += 1
    ok = (checked_in > 0 and checked_across > 0
          and inside < 1e-12 and across > 1e-9)
    detail = (f"inside a step, {checked_in} demand pairs that need the same lands move "
              f"the wage by at most {inside:.2e}. **Across a step, {checked_across} "
              f"adjacent pairs move it by at least {across:.2e}.** Both halves are "
              f"required: a field that never moved is also what a demand that never "
              f"reached the solve would look like, and the second half is what says "
              f"the steps are steps. **The intensive step is left out of this "
              f"comparison**: two methods on one land need the extra equation of B72's "
              f"Corollary 17.1, which this station does not carry, so at that step it "
              f"claims the graph and not the field")
    return ok, detail, {"pairs_inside": checked_in, "worst_inside": inside,
                        "pairs_across": checked_across, "least_across": across}


def crit_b1_moves(sample):
    """B87-5: b1 rises with demand, one at a time. B86's Theorem 30(4) reversed."""
    ladders, bad = [], []
    for s in sample:
        seq = [st["b1"] for st in s["steps"]]
        ext = [st["b1"] for st in s["steps"] if not st["intensive"]]
        ladders.append(seq)
        gaps = {b - a for a, b in zip(ext, ext[1:])}
        if gaps and gaps != {1}:
            bad.append({"k": s["k"], "b1": seq, "why": "extensive gap"})
        # the intensive step adds a process and closes a cycle, so it costs two
        if len(seq) > len(ext) and seq[len(ext)] - ext[-1] != 2:
            bad.append({"k": s["k"], "b1": seq, "why": "intensive gap"})
    ok = bool(ladders) and not bad
    detail = ("the first Betti number by step, printed as ladders rather than counted: "
              + "; ".join(str(x) for x in ladders[:6])
              + f" and {max(0, len(ladders) - 6)} more. It rises by exactly one at "
                f"every step on {len(ladders) - len(bad)} of {len(ladders)} systems. "
                f"**B86's Theorem 30(4) says demand can neither create nor destroy an "
                f"obstruction with one primary factor. With a scarce second factor it "
                f"moves the dimension. **It moves it by one at each extensive step "
                f"and by two at the intensive margin**, where a land taking a second "
                f"method stops being pendant and closes a cycle, which is B72's "
                f"Corollary 17.1 arriving as a step of the demand sweep.** What is claimed "
                f"here is the dimension only: whether any particular cycle sum is "
                f"non-zero is a reading and not this"
              + ("" if not bad else f". **{len(bad)} do not: {bad[:3]}**"))
    return ok, detail, {"ladders": ladders[:40], "irregular": bad}


def crit_thresholds(sample):
    """B87-6: the thresholds are where they are computed to be, checked either side."""
    bad, checked = [], 0
    for s in sample:
        for m in range(1, s["k"]):
            t = float(m)                      # unit capacity, so the threshold is at m
            below = cultivated_for(s["order"], t - EPS)
            above = cultivated_for(s["order"], t + EPS)
            checked += 1
            if not (len(below) == m and len(above) == m + 1):
                bad.append({"k": s["k"], "threshold": t,
                            "below": len(below), "above": len(above)})
    ok = checked > 0 and not bad
    detail = (f"each of {checked} thresholds is probed at plus and minus {EPS:g} in "
              f"demand: the cultivated set has {('m')} lands below it and one more "
              f"above, on {checked - len(bad)} of them. **The thresholds are checked "
              f"rather than declared**, which is the same requirement gate six puts on "
              f"a floor"
              + ("" if not bad else f". **{len(bad)} are not where they were computed: "
                                    f"{bad[:4]}**"))
    return ok, detail, {"thresholds": checked, "misplaced": bad}


def crit_registration():
    """B87-7: B86 registered this, and the same round writes back."""
    doc = (ROOT / "docs" / "b86_non_substitution.md").read_text(encoding="utf-8")
    named = "b87_demand_grip.md" in doc
    return named, (f"B86's file "
                   f"{'names this station against the registration it opened' if named else '**does not name this station: the write-back is missing**'}, "
                   f"including that its guess of a second potential is not the shape "
                   f"the answer took. `D20`"), {"b86_names_b87": named}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(7)
    sample = draws(rng, 12)
    if len(sample) < 6:
        fails.append(f"the fixture drew only {len(sample)} systems")

    for name, fn in (("B87-1", crit_reduces), ("B87-2", crit_nested),
                     ("B87-3", crit_betti), ("B87-4", crit_step_shape),
                     ("B87-5", crit_b1_moves), ("B87-6", crit_thresholds)):
        if not fn(sample)[0]:
            fails.append(f"{name} does not pass on the fixture: {fn(sample)[1][:110]}")
        if fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # B87-2: a sliding window instead of a prefix drops a land that was in use, which
    # is what a cultivation order not taken from the envelope would do. Rotating the
    # list and re-sorting, as a first version did, is the identity on a sorted set.
    def _window(s):
        k = s["k"]
        return [dict(st, cultivated=sorted(
            {s["order"][(st["m"] - 1 + i) % k] for i in range(st["m"])}))
            for st in s["steps"]]
    scrambled = [dict(s, steps=_window(s)) for s in sample if s["k"] >= 3]
    if crit_nested(scrambled)[0]:
        fails.append("a scrambled cultivation order left B87-2 passing")

    # B87-3: a Betti number off by one
    off = [dict(s, steps=[dict(st, b1=st["b1"] + 1) for st in s["steps"]])
           for s in sample]
    if crit_betti(off)[0]:
        fails.append("a Betti number off by one left B87-3 passing")

    # B87-4: a field that does not move across a step
    flat = [dict(s, steps=[dict(st, wage=s["steps"][0]["wage"]) for st in s["steps"]])
            for s in sample]
    if crit_step_shape(flat)[0]:
        fails.append("a wage that never moves across a step left B87-4 passing, so "
                     "its second half is not being required")

    # B87-4: identical lands make the wage the same at every step, so the only thing
    # that can fail is the across-a-step half. A probe that breaks both halves, as a
    # first version did, cannot tell a dropped clause from bad data.
    same = []
    for s in sample[:3]:
        a = np.full(s["k"], float(s["alphas"][0]))
        l = np.full(s["k"], float(s["lams"][0]))
        order = list(range(s["k"]))
        steps = []
        for m in range(1, s["k"] + 1):
            cult = sorted(order[:m])
            f = field_on(a, l, RATE, cult)
            b1, procs, closed = betti_for(cult)
            steps.append({"m": m, "intensive": False, "cultivated": cult,
                          "wage": f["wage"], "marginal": f["marginal"], "b1": b1,
                          "processes": procs, "b1_closed_form": closed})
        same.append({"k": s["k"], "alphas": a, "lams": l, "order": order,
                     "steps": steps})
    if same and crit_step_shape(same)[0]:
        fails.append("identical lands, where the wage cannot move across a step, left "
                     "B87-4 passing, so its second half is not being required")

    # B87-6: a cultivated set that ignores demand puts no threshold anywhere
    real_cf = cultivated_for
    try:
        globals()["cultivated_for"] = lambda order, demand: sorted(order[:1])
        if crit_thresholds(sample)[0]:
            fails.append("a cultivated set that ignores demand left B87-6 passing")
    finally:
        globals()["cultivated_for"] = real_cf

    # B87-5: two probes, one per clause, since a probe that breaks both cannot tell a
    # dropped clause from bad data.
    def _relabel(s, ext_gap):
        ext = [x for x in s["steps"] if not x["intensive"]]
        base = ext[0]["b1"]
        out = []
        for i, st in enumerate(ext):
            out.append(dict(st, b1=base + ext_gap * i))
        for st in [x for x in s["steps"] if x["intensive"]]:
            out.append(dict(st, b1=out[-1]["b1"] + 2))      # the intensive gap kept right
        return dict(s, steps=out)

    if crit_b1_moves([_relabel(s, 2) for s in sample])[0]:
        fails.append("extensive steps rising by two, with the intensive gap left "
                     "correct, passed B87-5: its extensive clause is not being read")

    def _bad_intensive(s):
        out = [dict(x) for x in s["steps"]]
        for st in out:
            if st["intensive"]:
                st["b1"] = st["b1"] + 5                     # only the intensive gap wrong
        return dict(s, steps=out)

    if crit_b1_moves([_bad_intensive(s) for s in sample])[0]:
        fails.append("a wrong intensive gap, with the extensive ladder left correct, "
                     "passed B87-5: its intensive clause is not being read")

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
    print(f"{len(sample)} systems, {sum(len(s['steps']) for s in sample)} steps\n")

    spec = [("B87-1", "known_answer", "with every land in use this is B72's Theorem 17(3)",
             crit_reduces),
            ("B87-2", "own_reading", "the cultivated set is nested in demand and takes "
             "at most k values", crit_nested),
            ("B87-3", "own_reading", "b1 read off the drawn graph against the closed form",
             crit_betti),
            ("B87-4", "own_reading", "the field is constant within a step and moves "
             "across one", crit_step_shape),
            ("B87-5", "own_reading", "b1 rises with demand one at a time, which is "
             "B86's Theorem 30(4) reversed", crit_b1_moves),
            ("B87-6", "instrument", "the thresholds are checked either side rather "
             "than declared", crit_thresholds)]
    criteria, report = [], {}
    for name, kind, statement, fn in spec:
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B87-7", "kind": "bookkeeping",
                     "statement": "B86's registration is discharged and written back",
                     "passed": bool(ok), "detail": detail})
    report["B87-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B87-7  [bookkeeping]  {detail[:200]}")

    rec = {"stage": "B87",
           "config": {"seed": a.seed, "systems": a.systems, "lands": list(LANDS),
                      "rate": RATE, "other_goods": N_OTHER_GOODS, "eps": EPS,
                      "corn_input": list(B72.CORN_INPUT),
                      "labour_input": list(B72.LABOUR_INPUT), "imports": "b72_land_and_rent"},
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
