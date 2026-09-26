"""B124: Kleinrock's conservation law, placed on the directed square of b4.

**The square.** b4 section 5.1 takes a position edge (i, j), two classes a and b, and the two
orientations of the four-cycle,

    S  = w_a(i, j) + w_b(j, i)        S' = w_b(i, j) + w_a(j, i)

whose sum is twice the two classes' round-trip friction (symmetric part, never positive) and
whose difference is twice the index part (antisymmetric). rho = |S - S'| / -(S + S').

**A queue on it.** Take the positions to be two service places, an early one with wait T_e and
a late one with wait T_l. A member of class p who moves from place u to place v changes its
waiting cost by w_p (T_v - T_u), where w_p is the money value of the class's time, so the edge
weight in money is

    omega_p(u, v) = -w_p (T_v - T_u).

The square is the two classes exchanging places. Three readings follow, and this script checks
each on exact rationals:

1. In time units (w = 1 for everyone) the weight is the difference of one scalar on places, so
   every square is zero. That is Kleinrock's statement for a swap: reallocating waiting between
   classes creates and destroys no time. It is not the symmetric half of the money square; the
   symmetric half of a pure reallocation is zero.
2. In money units the index part is S - S' = 2 (w_b - w_a)(T_l - T_e): a holder attribute times
   a place attribute, the cross term of the price-theory outline's section 4.1b, item eight.
3. With no friction S and S' have opposite signs, so one orientation is a positive directed
   cycle: the two classes gain by trading places, which b4's Theorem 4 excludes. An allocation
   that stands needs a trading friction with -(S + S') >= |S - S'| (Theorem 6(4)). Where places
   cannot be traded, the edge is absent.

**The queue itself.** A two-class M/G/1 queue, first come first served against non-preemptive
priority (Cobham's formulas), with exponential service so E[S^2] = 2 x^2, all in Fractions:

    W0 = sum_p lambda_p E[S_p^2] / 2
    FCFS          W_p = W0 / (1 - rho)
    priority 1>2  W_1 = W0 / (1 - rho_1),   W_2 = W0 / ((1 - rho_1)(1 - rho))

Kleinrock: sum_p rho_p W_p is the same under both. The money dissipation rate
C = sum_p lambda_p w_p W_p then moves by

    dC = rho_a dW_a (w_a / x_a - w_b / x_b),

zero if and only if the two classes' value per unit of service is equal.

Run:
    python experiments/b124_kleinrock_square.py
    python experiments/b124_kleinrock_square.py --selftest
"""

import argparse
import json
import pathlib
import sys
from fractions import Fraction as F

# Parameter sets: (lambda_a, x_a, lambda_b, x_b, w_a, w_b). Loads kept below one.
CASES = [
    (F(1, 4), F(1), F(1, 4), F(1), F(10), F(1)),
    (F(1, 5), F(2), F(1, 10), F(1), F(3), F(7)),
    (F(3, 10), F(1, 2), F(1, 2), F(1), F(1), F(1)),
    (F(1, 10), F(3), F(1, 3), F(1, 2), F(12), F(2)),
    (F(2, 5), F(1), F(1, 5), F(3, 2), F(5), F(5)),
]
# Two-place swaps: (T_e, T_l, w_a, w_b, friction). friction is a round-trip cost per class per
# edge, added to both directions (symmetric), zero for a pure reallocation.
SWAPS = [
    (F(1), F(3), F(10), F(1), F(0)),
    (F(2), F(2), F(10), F(1), F(0)),
    (F(0), F(5), F(4), F(4), F(0)),
    (F(1), F(4), F(2), F(9), F(0)),
]


def waits(lam_a, x_a, lam_b, x_b, rule, w0_fn=None):
    """Mean waits (a, b) under FCFS or non-preemptive priority to a, exponential service."""
    ra, rb = lam_a * x_a, lam_b * x_b
    rho = ra + rb
    w0 = (lam_a * 2 * x_a * x_a + lam_b * 2 * x_b * x_b) / 2 if w0_fn is None else w0_fn(
        lam_a, x_a, lam_b, x_b)
    if rule == "fcfs":
        return w0 / (1 - rho), w0 / (1 - rho)
    return w0 / (1 - ra), w0 / ((1 - ra) * (1 - rho))


def swap_square(te, tl, wa, wb, friction, value=None):
    """S and S' on the two-place square, with the edge weight omega_p(u, v) = -w_p (T_v - T_u)
    plus a symmetric friction."""
    T = {"e": te, "l": tl}
    wv = {"a": wa, "b": wb} if value is None else value

    def om(p, u, v):
        return -wv[p] * (T[v] - T[u]) - friction

    s = om("a", "e", "l") + om("b", "l", "e")
    s2 = om("b", "e", "l") + om("a", "l", "e")
    return s, s2


def build(cases=CASES, swaps=SWAPS, wait_fn=waits, cost_w=None, sq_fn=swap_square):
    rows = []
    for lam_a, x_a, lam_b, x_b, w_a, w_b in cases:
        ra, rb = lam_a * x_a, lam_b * x_b
        fa, fb = wait_fn(lam_a, x_a, lam_b, x_b, "fcfs")
        pa, pb = wait_fn(lam_a, x_a, lam_b, x_b, "priority")
        cons_f, cons_p = ra * fa + rb * fb, ra * pa + rb * pb
        wa_c, wb_c = (w_a, w_b) if cost_w is None else cost_w(w_a, w_b)
        cf = lam_a * wa_c * fa + lam_b * wb_c * fb
        cp = lam_a * wa_c * pa + lam_b * wb_c * pb
        d_wa = pa - fa
        formula = ra * d_wa * (w_a / x_a - w_b / x_b)
        rows.append({"params": [str(v) for v in (lam_a, x_a, lam_b, x_b, w_a, w_b)],
                     "work_weighted_wait_fcfs": str(cons_f), "work_weighted_wait_priority": str(cons_p),
                     "conserved": cons_f == cons_p,
                     "dW_a": str(d_wa), "dW_b": str(pb - fb),
                     "money_rate_fcfs": "%.6f" % float(cf), "money_rate_priority": "%.6f" % float(cp),
                     "dC": str(cp - cf), "dC_formula": str(formula), "dC_matches": (cp - cf) == formula,
                     "value_per_service_equal": w_a / x_a == w_b / x_b, "dC_zero": cp == cf})
    sq = []
    for te, tl, wa, wb, fr in swaps:
        s, s2 = sq_fn(te, tl, wa, wb, fr)
        t1, t2 = sq_fn(te, tl, wa, wb, F(0), value={"a": F(1), "b": F(1)})
        sq.append({"T": [str(te), str(tl)], "w": [str(wa), str(wb)], "friction": str(fr),
                   "S": str(s), "S_prime": str(s2), "sym": str(s + s2), "index": str(s - s2),
                   "index_formula": str(2 * (wb - wa) * (tl - te)),
                   "index_matches": (s - s2) == 2 * (wb - wa) * (tl - te),
                   "time_unit_square_zero": t1 == 0 and t2 == 0,
                   "positive_cycle": s > 0 or s2 > 0})
    return {"queues": rows, "swaps": sq}


def _crit(name, kind, verdict, detail):
    return {"name": name, "kind": kind, "detail": detail, "passed": bool(verdict)}


def criteria(rep):
    q, s = rep["queues"], rep["swaps"]
    crits = []
    bad = [i for i, r in enumerate(q) if not r["conserved"]]
    crits.append(_crit(
        "B124-K1", "known_answer", bool(q) and not bad,
        "Kleinrock's conservation law read back from Cobham's formulas: the work-weighted wait "
        "sum_p rho_p W_p is the same under first come first served and under non-preemptive "
        "priority, exactly, on " + str(len(q)) + " parameter sets. Cases where it moves: "
        + (", ".join(map(str, bad)) if bad else "none") + "."))
    pure = [x for x in s if x["friction"] == "0"]
    idx_bad = [i for i, x in enumerate(s) if not x["index_matches"]]
    sym_bad = [i for i, x in enumerate(pure) if x["sym"] != "0"]
    tz_bad = [i for i, x in enumerate(pure) if not x["time_unit_square_zero"]]
    crits.append(_crit(
        "B124-K2", "own_reading", bool(pure) and not idx_bad and not sym_bad and not tz_bad,
        "on the two-place square, a pure reallocation has a zero symmetric part, its index part "
        "is 2 (w_b - w_a)(T_l - T_e), and in time units (w = 1) the square is zero. On a two-place "
        "swap the last holds by construction (the swap moves equal time), and what carries the "
        "conservation on a real queue is B124-K1. So Kleinrock's invariant is the zero time-unit "
        "square, not the symmetric half of the money square. "
        "Index mismatches: " + str(len(idx_bad)) + "; non-zero symmetric parts on pure swaps: "
        + str(len(sym_bad)) + "; time-unit squares not zero: " + str(len(tz_bad)) + ". Pure swaps "
        "with a positive directed cycle (the classes gain by trading places, which a standing "
        "allocation needs a friction to prevent): "
        + str(sum(1 for x in pure if x["positive_cycle"])) + " of " + str(len(pure)) + "."))
    dc_bad = [i for i, r in enumerate(q) if not r["dC_matches"]]
    still = [i for i, r in enumerate(q) if r["dW_a"] == "0"]
    crits.append(_crit(
        "B124-K3", "own_reading", bool(q) and not dc_bad and not still,
        "the money dissipation rate moves by dC = rho_a dW_a (w_a/x_a - w_b/x_b) between the two "
        "rules. Since the rule moves waiting in every case (dW_a non-zero), dC is zero exactly "
        "where the two classes' value per unit of service is equal. Cases where the formula "
        "misses: " + str(len(dc_bad)) + "; cases where the rule moves no waiting: "
        + str(len(still)) + ", of " + str(len(q)) + "; cases with dC zero: "
        + str(sum(1 for r in q if r["dC_zero"])) + ", each with equal value per unit of service: "
        + str(all(r["value_per_service_equal"] for r in q if r["dC_zero"])) + "."))
    return crits


def verdicts(**kw):
    return {c["name"]: c["passed"] for c in criteria(build(**kw))}


def selftest():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    ok("every criterion holds on the stated cases", all(verdicts().values()))

    def wrong_waits(lam_a, x_a, lam_b, x_b, rule, w0_fn=None):
        ra, rb = lam_a * x_a, lam_b * x_b
        w0 = (lam_a * 2 * x_a * x_a + lam_b * 2 * x_b * x_b) / 2
        if rule == "fcfs":
            return w0 / (1 - ra - rb), w0 / (1 - ra - rb)
        return w0 / (1 - ra), w0 / (1 - ra - rb)  # drops the (1 - rho_1) in class 2's wait
    ok("a priority formula that breaks conservation flips K1", verdicts(wait_fn=wrong_waits)["B124-K1"] is False)

    sw = [(F(1), F(3), F(10), F(1), F(2))] + SWAPS
    ok("a friction on the swap does not change the index part", verdicts(swaps=sw)["B124-K2"] is True)
    sw = [(F(1), F(3), F(10), F(1), F(0))]
    rep = build(swaps=sw)
    rep["swaps"][0]["sym"] = "1"
    ok("a non-zero symmetric part on a pure swap flips K2", criteria(rep)[1]["passed"] is False)
    rep = build()
    rep["swaps"][0]["index_matches"] = False
    ok("an index part off the formula flips K2", criteria(rep)[1]["passed"] is False)

    def no_w_on_b(te, tl, wa, wb, friction, value=None):
        return swap_square(te, tl, wa, F(1), friction, value)
    ok("a square that drops class b's time value flips K2", verdicts(sq_fn=no_w_on_b)["B124-K2"] is False)

    def fcfs_only(lam_a, x_a, lam_b, x_b, rule, w0_fn=None):
        return waits(lam_a, x_a, lam_b, x_b, "fcfs")
    ok("a rule that moves no waiting flips K3", verdicts(wait_fn=fcfs_only)["B124-K3"] is False)

    ok("costing the classes at each other's values flips K3",
       verdicts(cost_w=lambda a, b: (b, a))["B124-K3"] is False)

    s, s2 = swap_square(F(1), F(3), F(10), F(1), F(0))
    ok("hand value: T 1 and 3, w 10 and 1, index -36, S -18, S' +18",
       (s - s2, s, s2) == (F(-36), F(-18), F(18)))
    fa, fb = waits(F(1, 4), F(1), F(1, 4), F(1), "fcfs")
    pa, pb = waits(F(1, 4), F(1), F(1, 4), F(1), "priority")
    ok("hand value: equal loads 1/4, FCFS wait 1, priority 2/3 and 4/3",
       (fa, fb, pa, pb) == (F(1), F(1), F(2, 3), F(4, 3)))

    width = max(len(label) for label, _ in checks)
    for label, cond in checks:
        print(("PASS  " if cond else "FAIL  ") + label.ljust(width))
    bad = [label for label, cond in checks if not cond]
    print("")
    print("selftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="results/b124_kleinrock_square.json")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rep = build()
    for r in rep["queues"]:
        print("queue", r["params"], "conserved", r["conserved"], "dC", r["dC"], "formula", r["dC_formula"])
    for x in rep["swaps"]:
        print("swap T", x["T"], "w", x["w"], "S", x["S"], "S'", x["S_prime"], "sym", x["sym"],
              "index", x["index"], "positive cycle", x["positive_cycle"])
    crits = criteria(rep)
    failed = []
    for c in crits:
        print(("PASS   " if c["passed"] else "FAILED[" + c["kind"] + "]: ") + c["name"] + "  " + c["detail"])
        if not c["passed"]:
            failed.append(c["name"])
    record = {"stage": "B124", "config": {"cases": len(CASES), "swaps": len(SWAPS),
                                          "service": "exponential, E[S^2] = 2 x^2",
                                          "rules": ["first come first served", "non-preemptive priority to class a"],
                                          "arithmetic": "fractions.Fraction, exact"},
              "criteria": crits, "report": rep}
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("wrote " + str(out))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
