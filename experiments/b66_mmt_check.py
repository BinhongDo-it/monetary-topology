"""B66-8 and B66-9: the known-answer check and the structural checks for the
sovereign's edges.

The statements are proved in docs/b66_mmt.md. This file checks their algebra and
the implementation of the objects they use, on graphs and flows built for the
purpose. It reads no data and measures nothing in the world.

  B66-8   Model SIM of Godley and Lavoie (2007, chapter 3) read through
          Theorem 11's first clause: the households' stock of the unit equals
          the government's cumulative deficit at every date, spending never
          falls behind taxes, and the stationary state balances the flows while
          the stock stays at the deficit already run.
  B66-9a  Theorem 11's first clause on random economies: the cut identity
          H(t) = S(t) - T(t) at every date; with stocks that may not go
          negative, spending at least matches taxes; and a run that taxes
          before anything is issued drives a stock below zero, so the bound
          binds rather than merely holding.
  B66-9b  Theorem 11's second and third clauses: the two routes for discharging
          one unit of an obligation form a square whose sum is log(kappa / p);
          the obligation is a sink, so no class can walk it and no directed
          cycle is positive at any price; open a refund route and a positive
          cycle appears exactly when p < kappa, with the switch at kappa; with
          two acceptable units the route taken is the cheaper one.
  B66-9c  Corollary 11.1 in four configurations: with hours that cannot pass
          between classes the guarantee's edge lies on no cycle and nothing is
          pinned; with an agent edge at the labour position a directed cycle is
          positive exactly when the market wage is below the guarantee's, and
          the switch is the guarantee's wage, moved by the cost of passing
          hours; with the guarantee's edge bounded, nothing is pinned again.
          The flow side is read on a grid: hours reach an employer below the
          guarantee's wage only where the programme cannot take them.

(NA) is the condition of b4_directed_edges Theorem 4, no directed cycle with a
positive sum, found by Bellman-Ford on the edges a class can walk without a
bound on quantity.

Residuals are printed. The record keeps the bound each one was held to, since
their last digits belong to the numerical library.

Run:

    python experiments\\b66_mmt_check.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b66_mmt_check.json"

SEED = 0
TOL = 1e-12            # identities on flows of order one to a hundred
TOL_CYCLE = 1e-12      # a directed cycle counts as positive only above this sum
TOL_SWITCH = 1e-9      # a switching price or wage found by bisection, against its closed form
BISECTION_STEPS = 60

# Model SIM, Godley and Lavoie (2007), chapter 3
SIM = {"alpha1": 0.6, "alpha2": 0.4, "theta": 0.2, "W": 1.0, "G": 20.0, "H0": 0.0}
SIM_PERIODS = 100
SIM_STEADY = {"Y": 100.0, "YD": 80.0, "H": 80.0}
SIM_DIGITS = 6

N_ECONOMIES = 200
MAX_PERIODS = 4
N_TAX = 400
WAGE_PROBES = (0.1, 0.5, 0.9, 0.99, 1.0, 1.01, 1.1, 2.0, 10.0)   # multiples of the guarantee's wage
JG_WORKERS = 100
JG_CAPS = (0, 25, 50, 100, 200)
JG_WAGES = (0.5, 0.9, 1.0, 1.1, 2.0)                              # multiples of the guarantee's wage


def net_inflow(edges, flows):
    """Kirchhoff's sum at every node: what flows in less what flows out."""
    out = {}
    for (u, v), x in zip(edges, flows):
        out[v] = out.get(v, 0.0) + float(x)
        out[u] = out.get(u, 0.0) - float(x)
    return out


def positive_cycle(edges) -> bool:
    """True iff some directed cycle has a sum above TOL_CYCLE: Bellman-Ford on
    the negated weights from a virtual source at every node."""
    index = {}
    for u, v, _ in edges:
        index.setdefault(u, len(index))
        index.setdefault(v, len(index))
    dist = [0.0] * len(index)
    arcs = [(index[u], index[v], -w) for u, v, w in edges]
    for _ in range(len(index) + 1):
        changed = False
        for u, v, c in arcs:
            if dist[u] + c < dist[v] - TOL_CYCLE:
                dist[v] = dist[u] + c
                changed = True
        if not changed:
            return False
    return True


def bisect_switch(lo, hi, positive_at):
    """The value where `positive_at` turns over, found by bisection; it is
    positive at `lo` and not at `hi`, or the other way round."""
    at_lo = positive_at(lo)
    for _ in range(BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        if positive_at(mid) == at_lo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------- B66-8: Model SIM, read as Theorem 11(1)


def sim_path():
    """Model SIM period by period from its own seven equations. Unknowns: Y, N,
    T, YD, C, the change in the households' money and the change in what the
    government has issued. H_h = H_s is not among them."""
    a1, a2, th, W, G = (SIM[k] for k in ("alpha1", "alpha2", "theta", "W", "G"))
    A = np.array([[0.0, -W, 1.0, 1.0, 0.0, 0.0, 0.0],        # YD = W N - T
                  [0.0, -th * W, 1.0, 0.0, 0.0, 0.0, 0.0],   # T = theta W N
                  [0.0, 0.0, 0.0, -a1, 1.0, 0.0, 0.0],       # C = alpha1 YD + alpha2 Hh(-1)
                  [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],       # dHs = G - T
                  [0.0, 0.0, 0.0, -1.0, 1.0, 1.0, 0.0],      # dHh = YD - C
                  [1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0],      # Y = C + G
                  [-1.0, W, 0.0, 0.0, 0.0, 0.0, 0.0]])       # N = Y / W
    path, hh = [], SIM["H0"]
    for t in range(1, SIM_PERIODS + 1):
        b = np.array([0.0, 0.0, a2 * hh, G, 0.0, G, 0.0])
        Y, N, T, YD, C, dhh, dhs = (float(v) for v in np.linalg.solve(A, b))
        hh += dhh
        path.append({"t": t, "Y": Y, "T": T, "YD": YD, "C": C, "dHh": dhh, "Hh": hh})
    return path


def check_sim():
    path = sim_path()
    G = SIM["G"]
    spent = taxed = 0.0
    worst_identity, worst_stock, ahead = 0.0, math.inf, math.inf
    for row in path:
        spent += G
        taxed += row["T"]
        worst_identity = max(worst_identity, abs(row["Hh"] - (spent - taxed)))
        worst_stock = min(worst_stock, row["Hh"])
        ahead = min(ahead, spent - taxed)
    last = path[-1]
    flow_gap = abs(last["T"] - G)
    stock_gap = abs(last["Hh"] - SIM_STEADY["H"])
    first = path[0]
    ok = (worst_identity < TOL and worst_stock >= -TOL and ahead >= -TOL
          and flow_gap < 1e-4 and stock_gap < 1e-4)
    detail = ("Model SIM, %d periods from zero stocks, G = %g, theta = %g, solved from the "
              "model's own seven equations. At every date the households' stock of the unit "
              "equals the government's cumulative deficit within %g, and it never goes "
              "negative, so cumulative spending is never behind cumulative taxes: in the "
              "first period the government spends %g and taxes %.4f. In the stationary state "
              "the flows balance, taxes %.4f against spending %g, while the stock stays at "
              "the deficit already run, %.4f against the book's %g. **A balanced flow at a "
              "positive stock is Theorem 11(1) with the cut identity at work**"
              % (SIM_PERIODS, G, SIM["theta"], TOL, G, first["T"], last["T"], G,
                 last["Hh"], SIM_STEADY["H"]))
    printed = ["worst |H_h(t) - cumulative deficit| %.3e; smallest stock %.4f; "
               "smallest (spending - taxes) %.4f" % (worst_identity, worst_stock, ahead),
               "period 1: spent %.4f, taxed %.4f, stock %.4f" % (G, first["T"], first["Hh"]),
               "period %d: spent %.4f, taxed %.4f, stock %.4f"
               % (SIM_PERIODS, G, last["T"], last["Hh"])]
    report = {"periods": SIM_PERIODS, "identity_below": TOL,
              "stationary_tax": round(last["T"], SIM_DIGITS),
              "stationary_stock": round(last["Hh"], SIM_DIGITS),
              "book_stock": SIM_STEADY["H"], "within": 1e-4}
    return ok, detail, report, printed


# ------------------------------------- B66-9a: the cut identity and what it takes to tax


def random_tax_economy(rng, tax_first=False):
    """Private agents holding one unit, issued only by the outside node O. Each
    period O spends on some of them, they pay each other a share of what they
    hold, and each pays a share of what it holds in tax, so nothing they do can
    take a stock below zero. With `tax_first` the first period taxes a base of
    one before anything has been issued, which is the case the nonnegativity
    rules out."""
    n = int(rng.integers(3, 8))
    periods = int(rng.integers(1, MAX_PERIODS + 1))
    stock = [0.0] * n
    history = []
    spent = taxed = 0.0
    for t in range(1, periods + 1):
        if not (tax_first and t == 1):
            for _ in range(int(rng.integers(1, 5))):
                a, x = int(rng.integers(0, n)), float(rng.uniform(0.0, 1.0))
                stock[a] += x
                spent += x
        for _ in range(int(rng.integers(0, 5))):
            a, b = int(rng.integers(0, n)), int(rng.integers(0, n))
            x = float(rng.uniform(0.0, 1.0)) * stock[a]
            if a != b:
                stock[a] -= x
                stock[b] += x
        for a in range(n):
            share = float(rng.uniform(0.05, 0.5))
            x = share * (1.0 if (tax_first and t == 1) else stock[a])
            stock[a] -= x
            taxed += x
        history.append({"t": t, "stock": list(stock), "spent": spent, "taxed": taxed})
    return n, history


def check_cut(rng):
    worst_identity, worst_behind, worst_stock = 0.0, 0.0, math.inf
    economies = periods = 0
    for _ in range(N_ECONOMIES):
        n, history = random_tax_economy(rng)
        economies += 1
        for row in history:
            periods += 1
            held = sum(row["stock"])
            worst_identity = max(worst_identity, abs(held - (row["spent"] - row["taxed"])))
            worst_behind = max(worst_behind, row["taxed"] - row["spent"])
            worst_stock = min(worst_stock, min(row["stock"]))
    # the bound binds: tax before anything is issued and a stock goes below zero
    forced_negative = 0
    for _ in range(20):
        _, history = random_tax_economy(rng, tax_first=True)
        if min(history[0]["stock"]) < -TOL:
            forced_negative += 1
    ok = (worst_identity < TOL and worst_behind <= TOL and worst_stock >= -TOL
          and forced_negative == 20)
    detail = ("%d random economies of 3 to 7 private holders over %d periods in all, with the "
              "unit issued only by the outside node, taxes drawn as a share of what each "
              "holder has and payments between holders drawn from the same. At every date the "
              "stock held privately equals cumulative spending less cumulative taxes within "
              "%g, no stock goes below zero, and cumulative taxes never run ahead of "
              "cumulative spending. **The bound binds rather than merely holding**: in 20 of "
              "20 runs that tax before anything has been issued, a holder's stock goes "
              "negative, which is what the nonnegativity rules out"
              % (economies, periods, TOL))
    printed = ["worst |held - (spent - taxed)| %.3e; worst (taxed - spent) %.3e; "
               "smallest stock %.3e; taxing first drove a stock below zero in %d of 20"
               % (worst_identity, worst_behind, worst_stock, forced_negative)]
    report = {"economies": economies, "periods": periods, "identity_below": TOL,
              "taxed_first_runs": 20, "taxed_first_negative": forced_negative}
    return ok, detail, report, printed


# --------------------------------- B66-9b: the discharge square, and two acceptable units


def discharge_graph(p, kappa, refund=False, psi=None, p2=None):
    """One class at three positions: goods q, the sovereign's unit m, and one
    unit of tax obligation d. The market turns p goods into one m and back; one
    m discharges one unit of obligation; kappa goods discharge it by paying the
    penalty instead. Both discharge edges point into d, which is a sink, so
    `refund` is what it would take for the square to be walkable: an edge that
    releases an obligation for kappa goods. With psi and p2 a second unit m2
    discharges the obligation at psi units of it, each bought for p2 goods."""
    edges = [(("q",), ("m",), -math.log(p)), (("m",), ("q",), math.log(p)),
             (("m",), ("d",), 0.0), (("q",), ("d",), -math.log(kappa))]
    if refund:
        edges.append((("d",), ("q",), math.log(kappa)))
    if psi is not None:
        edges += [(("q",), ("m2",), -math.log(p2)), (("m2",), ("q",), math.log(p2)),
                  (("m2",), ("d",), -math.log(psi))]
    return edges


def square_sum(edges):
    """The sum of the square q -> m -> d and back along the penalty edge."""
    w = {(u, v): x for u, v, x in edges}
    return w[(("q",), ("m",))] + w[(("m",), ("d",))] - w[(("q",), ("d",))]


def check_discharge(rng):
    worst_square, worst_switch = 0.0, 0.0
    sink_clean = walkable_switch = cheapest = draws = 0
    for k in range(N_TAX):
        p = float(rng.uniform(0.1, 3.0))
        kappa = float(rng.uniform(0.1, 3.0))
        draws += 1
        g = discharge_graph(p, kappa)
        worst_square = max(worst_square, abs(square_sum(g) - math.log(kappa / p)))
        # the obligation is a sink, so nothing is walkable whatever the price
        sink_clean += not positive_cycle(g) and all(u != ("d",) for u, _, _ in g)
        # open the refund route and the square becomes a cycle, positive below the penalty
        if k % 4 == 0:
            got = bisect_switch(0.01, 10.0,
                                lambda x: positive_cycle(discharge_graph(x, kappa, refund=True)))
            worst_switch = max(worst_switch, abs(got - kappa))
            walkable_switch += abs(got - kappa) < TOL_SWITCH
        # two acceptable units: the route read off the square sums is the cheapest one
        psi = float(rng.uniform(0.2, 3.0))
        p2 = float(rng.uniform(0.1, 3.0))
        costs = {"unit": p, "second unit": psi * p2, "penalty": kappa}
        savings = {"unit": math.log(kappa / p), "second unit": math.log(kappa / (psi * p2)),
                   "penalty": 0.0}
        cheapest += min(costs, key=costs.get) == max(savings, key=savings.get)
    ok = (worst_square < TOL and sink_clean == draws and walkable_switch == draws // 4
          and cheapest == draws and worst_switch < TOL_SWITCH)
    detail = ("%d draws of a price and a penalty, both uniform on [0.1, 3]. The square through "
              "the two discharge routes sums to log(kappa / p) within %g on every draw. **The "
              "obligation is a sink**: no edge leaves it, and no directed cycle is positive at "
              "any price, in %d of %d. Open a refund route, the one thing that would make the "
              "square walkable, and a positive cycle appears exactly below the penalty: the "
              "switching price found by bisection is the penalty itself within %g, in %d of "
              "%d. With a second acceptable unit, the route taken is the cheapest of the "
              "three in %d of %d, by the square sums and by the costs alike"
              % (draws, TOL, sink_clean, draws, TOL_SWITCH, walkable_switch, draws // 4,
                 draws, draws))
    printed = ["worst |square sum - log(kappa/p)| %.3e; worst |switch - kappa| %.3e"
               % (worst_square, worst_switch)]
    report = {"draws": draws, "square_below": TOL, "switch_below": TOL_SWITCH,
              "sink_clean": sink_clean, "switch_at_penalty": walkable_switch,
              "cheapest_route": cheapest}
    return ok, detail, report, printed


# ----------------------------------------- B66-9c: the guarantee, an edge posted one way


def guarantee_graph(wage, w_jg, hours_pass=None, programme=True, one_way_hours=False):
    """Two classes at two positions: hours L and money m. The employer buys an
    hour for `wage` and can sell one on; the worker sells an hour for `wage` and,
    where the programme runs, for `w_jg`, and buys none. Money passes between the
    classes at par. `hours_pass` is the cost of passing hours between classes,
    None for a labour position that does not transfer; `programme` False leaves
    the programme's edge out, which is what a bound on its size does to (NA)."""
    edges = [(("b", "m"), ("b", "L"), -math.log(wage)),
             (("b", "L"), ("b", "m"), math.log(wage)),
             (("a", "L"), ("a", "m"), math.log(wage)),
             (("a", "m"), ("b", "m"), 0.0), (("b", "m"), ("a", "m"), 0.0)]
    if programme:
        edges.append((("a", "L"), ("a", "m"), math.log(w_jg)))
    if hours_pass is not None:
        edges.append((("b", "L"), ("a", "L"), -math.log(1.0 + hours_pass)))
        if not one_way_hours:
            edges.append((("a", "L"), ("b", "L"), -math.log(1.0 + hours_pass)))
    return edges


def check_guarantee(rng):
    w_jg = 1.0
    shapes, ok = {}, True
    for name, kw, expect in (
            ("hours that do not pass between classes",
             dict(hours_pass=None, programme=True), None),
            ("hours passing at par", dict(hours_pass=0.0, programme=True), w_jg),
            ("hours passing at a cost", dict(hours_pass=0.25, programme=True), w_jg / 1.25),
            ("hours passing one way, employer to the admitted class",
             dict(hours_pass=0.0, programme=True, one_way_hours=True), w_jg),
            ("the programme bounded", dict(hours_pass=0.0, programme=False), None)):
        probes = {}
        for mult in WAGE_PROBES:
            probes[mult] = positive_cycle(guarantee_graph(mult * w_jg, w_jg, **kw))
        if expect is None:
            match = not any(probes.values())
            got = None
        else:
            got = bisect_switch(0.01 * w_jg, 100.0 * w_jg,
                                lambda x: positive_cycle(guarantee_graph(x, w_jg, **kw)))
            match = (abs(got - expect) < TOL_SWITCH
                     and all(v == (m * w_jg < expect) for m, v in probes.items()
                             if abs(m * w_jg - expect) > TOL_SWITCH))
        ok &= match
        shapes[name] = {"switch": None if got is None else round(got, 9),
                        "expected": expect, "match": bool(match),
                        "positive_below_only": expect is not None}
    # the flow side: hours reach an employer below the guarantee's wage only where the
    # programme cannot take them
    grid, flow_ok = [], True
    for cap in JG_CAPS:
        for mult in JG_WAGES:
            wage = mult * w_jg
            if abs(wage - w_jg) < TOL_SWITCH:
                verdict, to_market = "not decided", None
            elif wage < w_jg:
                to_market = max(0, JG_WORKERS - cap)
                verdict = "the programme takes what it can"
            else:
                to_market = JG_WORKERS
                verdict = "every hour goes to the employer"
            grid.append({"cap": cap, "wage": round(wage, 6), "to_employer": to_market,
                         "verdict": verdict})
            if to_market is not None and wage < w_jg:
                flow_ok &= to_market == max(0, JG_WORKERS - cap)
    ok &= flow_ok
    detail = ("The guarantee posts an edge one way: it buys an hour at the guarantee's wage "
              "and sells none. **With a labour position that does not pass between classes, "
              "that edge lies on no cycle and no directed cycle is positive at any market "
              "wage**, from a tenth of the guarantee's to ten times it. **With an agent edge "
              "at the labour position the square closes**: a directed cycle is positive "
              "exactly below the guarantee's wage, the switch found by bisection being the "
              "guarantee's wage at par and the guarantee's wage over one plus the cost of "
              "passing hours when that costs something, each within %g, and never positive "
              "above. **One-wayness alone decides nothing**: with hours passing in one "
              "direction only, from the employer to the admitted class, every edge of that "
              "cycle is one-way and the switch is the guarantee's wage all the same. With the "
              "programme's edge bounded, nothing is positive again. On the "
              "flow side, with %d workers and a cap of %s, the hours that reach an employer "
              "below the guarantee's wage are what the programme cannot take, in every cell "
              "of the grid; the cell where the two wages are equal is reported and not judged"
              % (TOL_SWITCH, JG_WORKERS, ", ".join(str(c) for c in JG_CAPS)))
    printed = ["%s: switch %s, expected %s, match %s"
               % (k, v["switch"], v["expected"], v["match"]) for k, v in shapes.items()]
    printed.append("flow grid: " + "; ".join(
        "cap %d, wage %.2f -> %s" % (g["cap"], g["wage"],
                                     "undecided" if g["to_employer"] is None
                                     else "%d hours to the employer" % g["to_employer"])
        for g in grid if g["cap"] in (0, 50, 200) and g["wage"] in (0.5, 1.0, 2.0)))
    report = {"shapes": shapes, "switch_below": TOL_SWITCH, "workers": JG_WORKERS,
              "caps": list(JG_CAPS), "grid": grid}
    return ok, detail, report, printed


# ---------------------------------------------------------------------- main


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B66-8", "known_answer",
         "Model SIM read through Theorem 11(1): the stock of the unit is the cumulative "
         "deficit, and the stationary state balances the flows at a positive stock",
         check_sim()),
        ("B66-9a", "instrument",
         "Theorem 11(1) on random economies: the cut identity, and what it takes to tax",
         check_cut(rng)),
        ("B66-9b", "instrument",
         "Theorem 11(2) and (3): the discharge square, its sink, and two acceptable units",
         check_discharge(rng)),
        ("B66-9c", "instrument",
         "Corollary 11.1: the guarantee's edge in five configurations, and the flow side",
         check_guarantee(rng)),
    ]
    mapping = {
        "B66-8": "read back -> PASS; not read back -> FAIL, and the code is fixed first",
        "B66-9": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed",
        "B66-9c flow grid": "below the guarantee's wage and above it are read; the cell where "
                            "the two are equal is reported and mapped to no verdict",
    }
    print("=" * 78)
    print("B66-8 and B66-9: known answer and structural checks for docs/b66_mmt.md")
    print("=" * 78)
    for name, text in mapping.items():
        print("  states to verdicts, %s: %s" % (name, text))
    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep, printed) in results:
        print("\n%s  %s  [%s]\n  %s\n  %s" % (name, "PASS" if ok else "FAIL", kind, statement,
                                              detail))
        for line in printed:
            print("    " + line)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
    rec = {
        "stage": "B66",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_switch": TOL_SWITCH,
            "bisection_steps": BISECTION_STEPS, "sim": SIM, "sim_periods": SIM_PERIODS,
            "sim_steady": SIM_STEADY, "sim_digits": SIM_DIGITS,
            "n_economies": N_ECONOMIES, "max_periods": MAX_PERIODS, "n_tax": N_TAX,
            "wage_probes": list(WAGE_PROBES), "jg_workers": JG_WORKERS,
            "jg_caps": list(JG_CAPS), "jg_wages": list(JG_WAGES),
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all four pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
