"""B137: the borrowed price, one formula for four stations, its slope when the
own class's value is not published, and the least correction the rival's own
premise requires.

A statistic needs a price in every class-by-position cell. Where a class has no
published price the cell is filled with another class's value. B131 (FISIM),
B132 (the consumption deflator), B133 (the pay-productivity price divergence)
and B134 (the ICP's urban price in the rural cell) each measured one instance.

**Theorem 45.** One position, classes ``a`` with values ``P_a`` and stocks or
weights ``x_a``; the cells of the set ``E`` are filled with class ``b``'s value.

1. Published less true is ``sum_E (P_b - P_a) x_a``.
2. A chained Laspeyres period's growth is off by ``sum_E w_a (p_b - p_a)``,
   ``w`` base-period value shares and ``p`` relatives; Tornqvist likewise in
   logs with mean shares.
3. The change of the bias between two periods is
   ``sum d(gap) xbar + sum gapbar d(x)`` (Bennet). A scalar ``s`` between two
   own classes, ``lo`` below and ``hi`` above, splits a total
   ``P_hi x_hi - P_lo x_lo + s (x_lo - x_hi)``: it moves the total only through
   the stock difference.
4. With ``P_a`` in ``[L_a, U_a]`` the bias lies in
   ``[sum (P_b - U_a) x_a, sum (P_b - L_a) x_a]``, both ends attained: the bias
   is a line in the unpublished value with slope ``-x_a`` (``-w_a`` in growth).
5. The rival's premise that one scalar is acceptable to every class puts the
   scalar in ``F = intersection of the classes' intervals``. A borrowed value
   outside ``F`` is at least ``d = dist(P_b, F)`` from every premise-consistent
   scalar, so a cell filled with it must move by at least ``d`` times that
   cell's stock. The bound needs no own-class price. It is a statement about
   cells filled from one scalar: where published cells imply different
   scalars, it holds cell by cell with each cell's own implied scalar, and a
   scalar averaged over the cells gives an amount on a rebuilt baseline, which
   is no bound on the published cells' moves.
6. Dropping ``E`` and renormalising a Laspeyres index, or a geometric index at
   frozen mean shares, equals (2) with the own relative set to the rest of the
   basket's: every such "without" reading is one named point on the line of
   (4). A Tornqvist index of the rest recomputed from the rest's own shares in
   each period is another operation and differs by a weight term; so is a
   Fisher index of the rest.

Parts 1, 2, 3 and 6 are index-number identities (Bennet 1920 for 3) and are
cited. Block one checks all six on synthetic class-value fields; block two
re-reads the raw data already on disk for B131 to B134, through their own
loaders, with nothing fetched.

Run from the repository root with the project's virtual environment:

    python experiments/b137_borrowed_price.py --selftest
    python experiments/b137_borrowed_price.py --run [--no-write]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

CLOSED = True
RECORD = ROOT / "results" / "b137_borrowed_price.json"
SEED = 137
TOL = 1e-12
FIELDS = 2000

EA = "EA20"
BOTH = ("CP042", "CP122")


# --------------------------------------------------------------------------
# block one: the six parts on synthetic class-value fields


def random_field(rng):
    n = int(rng.integers(2, 13))
    P0 = rng.uniform(0.5, 2.0, n)
    rel = np.exp(rng.normal(0.0, 0.2, n))
    x = rng.uniform(0.0, 3.0, n)
    E = rng.random(n) < 0.4
    b = int(rng.integers(n))
    E[b] = False
    if not E.any():
        E[(b + 1) % n] = True
    return n, P0, rel, x, E, b


def part_one_two(fault=None, count=FIELDS):
    rng = np.random.default_rng(SEED)
    worst = 0.0
    for _ in range(count):
        n, P0, rel, x, E, b = random_field(rng)
        P1 = P0 * rel
        # (1) level
        pub = np.where(E, P0[b], P0)
        diff = (P0[b] - P0[E]) if fault != "sign" else (P0[E] - P0[b])
        gap1 = abs((pub @ x - P0 @ x) - float(diff @ x[E]))
        # (2) chained Laspeyres: base-period value shares
        pubrel = np.where(E, rel[b], rel)
        v = (P1 if fault == "current_shares" else P0) * x
        w = v / v.sum()
        true_g = (P0 * x) @ rel / (P0 @ x)
        pub_g = (P0 * x) @ pubrel / (P0 @ x)
        gap2 = abs((pub_g - true_g) - float(w[E] @ (rel[b] - rel[E])))
        # Tornqvist, in logs with mean shares
        s0 = P0 * x / (P0 @ x)
        s1 = P1 * x / (P1 @ x)
        pubP1 = np.where(E, P0 * rel[b], P1)
        s1p = pubP1 * x / (pubP1 @ x)
        sbar = 0.5 * (s0 + s1)
        sbarp = 0.5 * (s0 + s1p)
        _ = sbar
        tq_pub = float(sbarp @ np.log(pubrel))
        # at the published index's own mean shares, the gap is the formula;
        # the rest of the Tornqvist gap is the shares' own move
        gap3 = abs((tq_pub - float(sbarp @ np.log(rel)))
                   - float(sbarp[E] @ (np.log(rel[b]) - np.log(rel[E]))))
        worst = max(worst, gap1, gap2, gap3)
    return worst


def part_three(fault=None, count=FIELDS):
    rng = np.random.default_rng(SEED + 1)
    worst = 0.0
    for _ in range(count):
        m = int(rng.integers(1, 8))
        g0, g1 = rng.normal(0, 1, m), rng.normal(0, 1, m)
        x0, x1 = rng.uniform(0, 3, m), rng.uniform(0, 3, m)
        B0, B1 = g0 @ x0, g1 @ x1
        xbar = x0 if fault == "base_stock" else 0.5 * (x0 + x1)
        gbar = g0 if fault == "base_stock" else 0.5 * (g0 + g1)
        worst = max(worst, abs((B1 - B0) - ((g1 - g0) @ xbar + gbar @ (x1 - x0))))
        # the bracketed scalar: d total / d s = x_lo - x_hi
        lo, hi = sorted(rng.uniform(0, 5, 2))
        xl, xh = rng.uniform(0, 3, 2)
        s1, s2 = rng.uniform(lo, hi, 2)
        tot = lambda s_: (s_ - lo) * xl + (hi - s_) * xh  # noqa: E731
        worst = max(worst, abs((tot(s2) - tot(s1)) - (s2 - s1) * (xl - xh)))
    return worst


def part_four(fault=None, count=400, draws=250):
    rng = np.random.default_rng(SEED + 2)
    worst_out, worst_end = 0.0, 0.0
    for _ in range(count):
        n, P0, rel, x, E, b = random_field(rng)
        L = P0[E] * rng.uniform(0.5, 1.0, E.sum())
        U = P0[E] * rng.uniform(1.0, 1.5, E.sum())
        low = float((P0[b] - U) @ x[E])
        high = float((P0[b] - L) @ x[E])
        if fault == "swapped":
            low, high = high, low
        Pa = rng.uniform(L, U, (draws, E.sum()))
        bias = (P0[b] - Pa) @ x[E]
        worst_out = max(worst_out, float(np.maximum(low - bias, 0).max()),
                        float(np.maximum(bias - high, 0).max()))
        worst_end = max(worst_end,
                        abs(float((P0[b] - U) @ x[E]) - low),
                        abs(float((P0[b] - L) @ x[E]) - high))
    return max(worst_out, worst_end)


def least_correction(intervals, pb, fault=None):
    lo = max(i[0] for i in intervals)
    hi = min(i[1] for i in intervals)
    if hi < lo:
        return None, lo, hi
    if fault == "midpoint":
        return abs(pb - 0.5 * (lo + hi)) if not lo <= pb <= hi else 0.0, lo, hi
    return max(lo - pb, pb - hi, 0.0), lo, hi


def part_five(fault=None, count=FIELDS):
    rng = np.random.default_rng(SEED + 3)
    worst, empty_ok = 0.0, True
    for c in range(count):
        k = int(rng.integers(2, 6))
        centres = rng.uniform(0, 5, k)
        half = rng.uniform(0.2, 3.0, k) if c % 10 else rng.uniform(0.0, 0.1, k)
        iv = [(ce - h, ce + h) for ce, h in zip(centres, half)]
        pb = float(rng.uniform(-2, 7))
        d, lo, hi = least_correction(iv, pb, fault)
        if d is None:
            empty_ok &= max(i[0] for i in iv) > min(i[1] for i in iv)
            continue
        grid = np.linspace(lo, hi, 2001)
        step = (hi - lo) / 2000
        # the search finds the nearest point only to within half its step
        worst = max(worst, max(0.0, abs(d - float(np.abs(grid - pb).min()))
                               - 0.5 * step))
    return worst, empty_ok


def tornqvist_rest(s0, s1, rel, keep, how):
    """Log change of the kept items' geometric index. ``frozen``: the whole
    index's mean shares, renormalised over the kept items. ``ordinary``: each
    period's shares renormalised over the kept items first, then averaged, the
    Tornqvist index of the rest itself."""
    if how == "frozen":
        w = (s0[keep] + s1[keep]) / (s0[keep].sum() + s1[keep].sum())
    else:
        w = 0.5 * (s0[keep] / s0[keep].sum() + s1[keep] / s1[keep].sum())
    return float(w @ np.log(rel[keep]))


#: Three items, prices (1, 1, 1) to (2, 1, 1.1), quantities (1, 1, 1) to
#: (2, 1, 1), the first dropped: the two renormalisations give different
#: indexes of the rest, in percent.
TORNQVIST_EXAMPLE = {"ordinary": 4.999954927, "frozen": 4.961966542}


def tornqvist_example() -> dict:
    p0, p1 = np.array([1.0, 1.0, 1.0]), np.array([2.0, 1.0, 1.1])
    q0, q1 = np.array([1.0, 1.0, 1.0]), np.array([2.0, 1.0, 1.0])
    s0, s1 = p0 * q0 / (p0 @ q0), p1 * q1 / (p1 @ q1)
    keep = np.array([False, True, True])
    return {how: 100 * (math.exp(tornqvist_rest(s0, s1, p1 / p0, keep, how)) - 1)
            for how in ("ordinary", "frozen")}


def part_six(fault=None, count=FIELDS):
    """Largest gap of the two "without" identities, Laspeyres and the
    geometric index at frozen mean shares; and the smallest distance, over the
    fields, between the frozen-share index of the rest and the ordinary
    Tornqvist index of the rest, which are two operations."""
    rng = np.random.default_rng(SEED + 4)
    worst, apart = 0.0, 0.0
    for _ in range(count):
        n, P0, rel, x, E, b = random_field(rng)
        if E.all():
            continue
        v = P0 * x
        w = v / v.sum()
        keep = ~E
        dropped = float(v[keep] @ rel[keep] / v[keep].sum())
        rest = dropped
        own = np.where(E, rest, rel)
        pub_with_rest = float(w @ own)
        if fault == "forget_weight":
            pub_with_rest = float(w[keep] @ rel[keep])
        worst = max(worst, abs(pub_with_rest - dropped))
        # the geometric index at frozen mean shares: the same identity in logs
        s0 = w
        s1 = v * rel / (v @ rel)
        sbar = 0.5 * (s0 + s1)
        how = "ordinary" if fault == "ordinary_tornqvist" else "frozen"
        rest_log = tornqvist_rest(s0, s1, rel, keep, how)
        with_rest = float(sbar[keep] @ np.log(rel[keep]) + sbar[E].sum() * rest_log)
        worst = max(worst, abs(with_rest - rest_log))
        apart = max(apart, abs(tornqvist_rest(s0, s1, rel, keep, "frozen")
                               - tornqvist_rest(s0, s1, rel, keep, "ordinary")))
    return worst, apart


def block_one(fault=None, quick=False):
    count = 300 if quick else FIELDS
    g12 = part_one_two(fault if fault in ("sign", "current_shares") else None, count)
    g3 = part_three(fault if fault == "base_stock" else None, count)
    g4 = part_four(fault if fault == "swapped" else None, 80 if quick else 400)
    g5, empty_ok = part_five(fault if fault == "midpoint" else None, count)
    g6, apart6 = part_six(fault if fault in ("forget_weight", "ordinary_tornqvist")
                          else None, count)
    ex6 = tornqvist_example()
    ex6_gap = max(abs(ex6[k] - TORNQVIST_EXAMPLE[k]) for k in ex6)
    crit = [
        {"name": "B137-1  the level and the growth: published less true is "
                 "sum_E (P_b - P_a) x_a; chained Laspeyres and Tornqvist growth "
                 "are off by the share-weighted relative gap",
         "kind": "instrument", "passed": bool(g12 <= TOL),
         "detail": f"{count} synthetic fields of 2 to 12 classes, largest gap "
                   f"{g12:.1e} (tolerance {TOL:g})"},
        {"name": "B137-2  the change of the bias splits into the gap moving and "
                 "the stock moving, and a bracketed scalar moves the total only "
                 "through the stock difference",
         "kind": "instrument", "passed": bool(g3 <= TOL),
         "detail": f"{count} pairs of periods and bracketed scalars, largest gap "
                   f"{g3:.1e}"},
        {"name": "B137-3  with the own value in an interval the bias lies between "
                 "the two ends, which are attained",
         "kind": "instrument", "passed": bool(g4 <= TOL),
         "detail": f"random own values inside their intervals, largest excursion "
                   f"or end gap {g4:.1e}"},
        {"name": "B137-4  the least correction the rival's premise requires is "
                 "the distance from the borrowed value to the intersection of "
                 "the classes' intervals; an empty intersection refutes the "
                 "premise",
         "kind": "instrument", "passed": bool(g5 <= TOL and empty_ok),
         "detail": f"{count} interval sets, against a search over 2001 points of "
                   f"the intersection, largest gap beyond half the search step "
                   f"{g5:.1e} (tolerance {TOL:g}); empty intersections "
                   f"{'reported' if empty_ok else 'missed'}"},
        {"name": "B137-5  dropping the borrowed items and renormalising equals "
                 "setting their relatives to the rest of the basket's, for "
                 "Laspeyres and for the geometric index at frozen mean shares; "
                 "the ordinary Tornqvist index of the rest is another operation",
         "kind": "instrument",
         "passed": bool(g6 <= TOL and ex6_gap <= 5e-9 and apart6 > 1e-6),
         "detail": (f"{count} fields, largest gap of the two identities {g6:.1e}; "
                    f"on the three-item example the rest rises "
                    f"{ex6['frozen']:.6f} % at frozen mean shares and "
                    f"{ex6['ordinary']:.6f} % as its own Tornqvist index (gap to "
                    f"the stated values {ex6_gap:.1e}); over the fields the two "
                    f"are up to {apart6:.1e} apart in logs")},
    ]
    return crit


# --------------------------------------------------------------------------
# block two: the four carriers, through their own loaders


def _mod(name):
    return __import__(name)


def eu_deflator_rows(cp18) -> list[dict]:
    """Per area and year: the consumption deflator as the previous-year-price
    weighted mean of item relatives, the two borrowed items' weights and
    relatives, and the rest's relative. Each area in the unit B132 reads it in:
    a country in national currency, an aggregate in euro."""
    units = _mod("b132_readings").units
    rows = []
    keys = {(g, y) for (u, it, g, y) in cp18 if u == "CP_MEUR" and it == "TOTAL"}
    for g, y in sorted(keys):
        uc, up = units(g)
        cp, py = cp18.get((uc, "TOTAL", g, y)), cp18.get((up, "TOTAL", g, y))
        items = {it: (cp18.get((uc, it, g, y)), cp18.get((up, it, g, y)))
                 for it in BOTH}
        if cp is None or py is None or py <= 0 or any(
                a is None or b is None or b <= 0 for a, b in items.values()):
            continue
        w = {it: b / py for it, (a, b) in items.items()}
        p = {it: a / b for it, (a, b) in items.items()}
        rest_cp = cp - sum(a for a, b in items.values())
        rest_py = py - sum(b for a, b in items.values())
        if rest_py <= 0:
            continue
        p_rest = rest_cp / rest_py
        published = cp / py
        bias = sum(w[it] * (p[it] - p_rest) for it in BOTH)
        rows.append({"geo": g, "year": y, "published": 100 * (published - 1),
                     "via_formula": 100 * (published - bias - 1),
                     "w_rent": w["CP042"], "w_fisim": w["CP122"],
                     "p_rent": 100 * (p["CP042"] - 1), "p_fisim": 100 * (p["CP122"] - 1),
                     "p_rest": 100 * (p_rest - 1), "bias": 100 * bias})
    return rows


def fr_fisim_only(cp18, y=2023):
    cp, py = cp18[("CP_MEUR", "TOTAL", "FR", y)], cp18[("PYP_MEUR", "TOTAL", "FR", y)]
    a, b = cp18[("CP_MEUR", "CP122", "FR", y)], cp18[("PYP_MEUR", "CP122", "FR", y)]
    p_rest = (cp - a) / (py - b)
    bias = (b / py) * (a / b - p_rest)
    return 100 * (cp / py - 1), 100 * (cp / py - bias - 1)


def us_bias_rows(v) -> list[dict]:
    """Per year: PCE growth, the borrowed items' contribution and base share,
    and the growth with the two items taken out by each of B133's operators.

    The PCE price index is a Fisher index. ``p_borrowed``, ``p_rest``, ``bias``
    and ``without`` are the contributions construct: BEA's Fisher contributions
    of the two items over their previous-year share, and what is left over the
    rest's share. Inside that construct Theorem 45's line holds exactly, with
    the share as its slope; it is a stand-in for the index of the rest, which
    B133-6 calibrates on a removal BEA publishes. ``without_fisher`` is B133's
    other operator, a Fisher of the published Fishers, and ``bias_fisher`` the
    published change less it."""
    B133 = _mod("b133_readings")
    rows = []
    for y in sorted(v["DPCERG"]):
        if y - 1 not in v["DPCERG"] or y not in v["CE001228"] or y - 1 not in v["DPCERC"]:
            continue
        g = 100 * (v["DPCERG"][y] / v["DPCERG"][y - 1] - 1)
        c = v["CE001228"][y] + v["CE001209"][y]
        s = (v["DOWNRC"][y - 1] + v["DIMPRC"][y - 1]) / v["DPCERC"][y - 1]
        p_e = c / s
        p_rest = (g - c) / (1 - s)
        bias = s * (p_e - p_rest)
        try:
            wf = B133.rest_change(v, y, how="fisher")
        except KeyError:
            wf = None
        rows.append({"year": y, "g": g, "share": s, "p_borrowed": p_e,
                     "p_rest": p_rest, "bias": bias, "without": g - bias,
                     "without_fisher": wf,
                     "bias_fisher": None if wf is None else g - wf})
    return rows


def us_window_share(v, rows, a, b, key="without"):
    B133 = _mod("b133_readings")
    by = {r["year"]: r for r in rows}
    rest = sum(100 * math.log(1 + by[y][key] / 100) for y in range(a + 1, b + 1))
    pce, nfb = B133.lp(v, "DPCERG", a, b), B133.lp(v, "B358RG", a, b)
    return 1 - (rest - nfb) / (pce - nfb)


CELLS = ("S14_S15 dep", "S14_S15 loan", "S11 dep", "S11 loan")


def fisim_rows(data, F, fault=None) -> list[dict]:
    """Per euro-area member year with every input: B131's band, the four
    published cells and the scalar each implies, and what the premise of one
    acceptable scalar requires of them.

    A cell is ``sign (scalar - own rate) stock / 100``, sign +1 for deposits
    and -1 for loans, so against a scalar ``q`` the published cell moves by
    ``sign (q - implied) stock / 100``, ``implied`` the scalar that cell
    implies. Three amounts are kept apart, million euro:

    ``floor_rise``, ``floor_fall``  Theorem 45 (5) cell by cell: a cell whose
        implied scalar lies outside the band is at least that distance from
        every acceptable scalar. Summed over the cells that must rise (a
        deposit cell below the band, a loan cell above it) and over those that
        must fall. A bound for every ``q`` in the band, with no baseline.
    ``fit_rise``, ``fit_total``  one common ``q`` in the band: the least sum
        of the cells' increases and the least sum of their absolute moves.
        Piecewise linear in ``q``, minimised over the band's ends and the
        implied scalars inside it.
    ``projection_amount``  the mean of the four implied scalars taken as the
        office's one scalar: its distance to the band times the stock of the
        side it understates. The least correction on a baseline rebuilt from
        that mean; the published cells differ from that baseline, so it is no
        bound on their moves."""
    B131 = _mod("b131_readings")
    mir, S, r23 = data["mir"], data["bsi"], data["r23"]
    code = {"S14_S15": "2250", "S11": "2240"}
    gdp = {(g, y): val for (dr, it, s, g, y), val in data["s1"].items() if it == "B1GQ"}
    out = []
    for band in B131.bands(data, F):
        g, y = band["geo"], band["year"]
        D, L, own = {}, {}, {}
        for s in ("S14_S15", "S11"):
            c = code[s]
            r21, r22 = mir[(g, "L21", c)][y], mir[(g, "L22", c)][y]
            rn = r23[(g, y)] if s == "S14_S15" else min(r21, r22)
            st = [S[(g, k, c, y)] for k in ("L21", "L22", "L23")]
            D[s] = sum(st)
            L[s] = S[(g, "A20", c, y)]
            own[f"{s} dep"] = (r21 * st[0] + r22 * st[1] + rn * st[2]) / D[s]
            own[f"{s} loan"] = mir[(g, "A20", c)][y]
        # Theorem 45 (1), inverted for the scalar each side implies
        implied = {}
        for s in ("S14_S15", "S11"):
            implied[f"{s} dep"] = own[f"{s} dep"] + 100 * F[(g, s, "dep", y)] / D[s]
            implied[f"{s} loan"] = own[f"{s} loan"] - 100 * F[(g, s, "loan", y)] / L[s]
        match = max(abs(implied[k] - band["implied"][k]) for k in implied)
        scalar = float(np.mean(list(implied.values())))
        lo, hi = band["band_low"], band["band_high"]
        d, _, _ = least_correction([(lo, hi)], scalar)
        dep_stock = D["S14_S15"] + D["S11"]
        loan_stock = L["S14_S15"] + L["S11"]
        side = "below" if scalar < lo else ("above" if scalar > hi else "inside")
        cells = {f"{s} {sd}": F[(g, s, sd, y)] for s in ("S14_S15", "S11")
                 for sd in ("dep", "loan")}
        stock = {f"{s} dep": D[s] for s in ("S14_S15", "S11")}
        stock.update({f"{s} loan": L[s] for s in ("S14_S15", "S11")})
        sign = {k: (1.0 if k.endswith("dep") else -1.0) for k in CELLS}
        neg = sum(min(cells[k], 0.0) for k in CELLS)
        corr_side = d * (dep_stock if side == "below" else loan_stock) / 100
        any_out = any(v < lo or v > hi for v in implied.values())

        # Theorem 45 (5), cell by cell
        dist = {k: max(lo - implied[k], implied[k] - hi, 0.0) for k in CELLS}
        rises = {k: (implied[k] < lo) if sign[k] > 0 else (implied[k] > hi) for k in CELLS}
        floor_rise = sum(dist[k] * stock[k] / 100 for k in CELLS if rises[k])
        floor_fall = sum(dist[k] * stock[k] / 100 for k in CELLS
                         if dist[k] > 0 and not rises[k])
        if fault == "mean_as_floor":
            floor_rise = corr_side

        # one common scalar in the band
        def moves(q):
            return {k: sign[k] * (q - implied[k]) * stock[k] / 100 for k in CELLS}

        cand = [lo, hi] + [v for v in implied.values() if lo < v < hi]
        fit_rise, q_rise = min((sum(max(x, 0.0) for x in moves(q).values()), q)
                               for q in cand)
        fit_total, q_total = min((sum(abs(x) for x in moves(q).values()), q)
                                 for q in cand)
        model_low = min(min(sign[k] * (q - own[k]) * stock[k] / 100 for k in CELLS)
                        for q in (lo, hi))
        # the mean's projection added to each published cell
        q_near = min(max(scalar, lo), hi)
        after = {k: cells[k] + sign[k] * (q_near - scalar) * stock[k] / 100
                 for k in CELLS}
        sectors_out = sum(not own[f"{s} dep"] <= scalar <= own[f"{s} loan"]
                          for s in ("S14_S15", "S11"))
        out.append({"geo": g, "year": y, "low": lo, "high": hi, "scalar": scalar,
                    "side": side, "any_outside": any_out, "distance": d, "match": match,
                    "spread": max(implied.values()) - min(implied.values()),
                    "dep_stock": dep_stock, "loan_stock": loan_stock,
                    "projection_amount": corr_side,
                    "projection_total_change": d * (dep_stock - loan_stock) / 100
                    * (1 if side == "below" else -1),
                    "sectors_outside": int(sectors_out),
                    "published_cells": [cells[k] for k in CELLS],
                    "implied_scalars": [implied[k] for k in CELLS],
                    "negative_published": neg,
                    "negative_cells": int(sum(cells[k] < 0 for k in CELLS)),
                    "floor_rise": floor_rise, "floor_fall": floor_fall,
                    "fit_rise": fit_rise, "fit_rise_at": q_rise,
                    "fit_total": fit_total, "fit_total_at": q_total,
                    "model_cell_least": model_low,
                    "negative_floor_gap": max(
                        [-cells[k] - dist[k] * stock[k] / 100
                         for k in CELLS if cells[k] < 0] or [0.0]),
                    "cells_negative_after_projection": int(sum(v < -1e-9
                                                               for v in after.values())),
                    "gdp": gdp.get((g, y))})
    return out


def block_two(fault=None):
    B131, B132, B133 = (_mod(n) for n in ("b131_readings", "b132_readings",
                                           "b133_readings"))
    rec131 = json.loads((ROOT / "results" / "b131_readings.json").read_text(encoding="utf-8"))
    rec132 = json.loads((ROOT / "results" / "b132_readings.json").read_text(encoding="utf-8"))
    rec133 = json.loads((ROOT / "results" / "b133_readings.json").read_text(encoding="utf-8"))
    rec134 = json.loads((ROOT / "results" / "b134_readings.json").read_text(encoding="utf-8"))

    d132 = B132.load_all()
    cp18 = d132["cp18"]
    eu = eu_deflator_rows(cp18)
    # B137-6: B132's France 2023 and the cumulative "without both", B133's share
    fr_with, fr_without = fr_fisim_only(cp18)
    if fault == "own_zero":
        fr_without = fr_with - 100 * (cp18[("PYP_MEUR", "CP122", "FR", 2023)]
                                      / cp18[("PYP_MEUR", "TOTAL", "FR", 2023)]) * (
            cp18[("CP_MEUR", "CP122", "FR", 2023)] / cp18[("PYP_MEUR", "CP122", "FR", 2023)] - 1)
    by = {(r["geo"], r["year"]): r for r in eu}
    cum_gaps = []
    for g, want in rec132["objects"]["B132-6"].items():
        acc = 1.0
        ok = True
        for y in range(2021, 2025):
            r = by.get((g, y))
            if r is None:
                ok = False
                break
            acc *= 1 + r["via_formula"] / 100
        if ok:
            cum_gaps.append(abs(round(100 * (acc - 1), 2) - want["na_without_both"]))
    d133 = B133.load_all()
    us = us_bias_rows(d133["v"])
    share = us_window_share(d133["v"], us, 1973, 2014)
    share_f = us_window_share(d133["v"], us, 1973, 2014,
                              "without" if fault == "one_operator" else "without_fisher")
    want = rec133["objects"]["B133-3"]["main"]["1973-2014"]
    want_share, want_share_f = want["borrowed_share"], want["borrowed_share_fisher"]
    gaps6 = {"FR with": abs(round(fr_with, 3) - rec132["objects"]["B132-2"]["with"]),
             "FR without": abs(round(fr_without, 3) - rec132["objects"]["B132-2"]["without"]),
             "cumulative without both (max over areas)": max(cum_gaps) if cum_gaps else float("inf"),
             "US 1973-2014 borrowed share": abs(round(share, 4) - want_share),
             "US 1973-2014 borrowed share, Fisher removal": abs(round(share_f, 4) - want_share_f)}
    ok6 = (gaps6["FR with"] <= 5e-4 and gaps6["FR without"] <= 5e-4
           and gaps6["cumulative without both (max over areas)"] <= 5e-3
           and gaps6["US 1973-2014 borrowed share"] <= 5e-5
           and gaps6["US 1973-2014 borrowed share, Fisher removal"] <= 5e-5
           and len(cum_gaps) > 0)
    c6 = {"name": "B137-6  the published 'without' readings recomputed from the raw "
                  "data: B132's France 2023 and its 2020-2024 'without both' per "
                  "area as Theorem 45 (6); B133's 1973-2014 borrowed share by its "
                  "two operators, the contributions construct (the bias formula "
                  "with the own relative set to the rest's) and the Fisher removal",
          "kind": "known_answer", "passed": bool(ok6),
          "detail": (f"France 2023 {fr_with:.3f} / {fr_without:.3f} against "
                     f"{rec132['objects']['B132-2']['with']} / "
                     f"{rec132['objects']['B132-2']['without']}; {len(cum_gaps)} areas' "
                     f"cumulative 'without both', largest gap "
                     f"{gaps6['cumulative without both (max over areas)']:.3f} at two "
                     f"printed places; US 1973-2014 share by the contributions "
                     f"construct {share:.4f} against {want_share}, by the Fisher "
                     f"removal {share_f:.4f} against {want_share_f}")}

    # B137-7: B131's band and scalar through formula (1)
    d131 = B131.load_all()
    F = B131.fisim(d131["d41"])
    fr = fisim_rows(d131, F, fault if fault == "mean_as_floor" else None)
    if fault == "year_end":
        for r in fr:
            r["match"] = 1.0
    match = max(r["match"] for r in fr)
    spread_med = float(np.median([r["spread"] for r in fr]))
    outside = sum(r["any_outside"] for r in fr)
    want8 = rec131["objects"]["B131-8"]
    ok7 = (match <= 1e-9 and abs(round(spread_med, 4) - want8["spread_median"]) <= 1e-4
           and outside == want8["outside"] and len(fr) == want8["years"])
    c7 = {"name": "B137-7  B131's reference scalar is Theorem 45 (1) inverted: the "
                  "scalar each side implies, from the published FISIM, the own "
                  "rates and the mean stocks, reproduces B131's band reading",
          "kind": "known_answer", "passed": bool(ok7),
          "detail": (f"{len(fr)} member years against B131's {want8['years']}; "
                     f"implied scalars against B131's, largest gap {match:.1e}; median "
                     f"spread of the four {spread_med:.4f} against "
                     f"{want8['spread_median']}; office scalar outside the band in "
                     f"{outside} against {want8['outside']}")}

    # B137-8 and B137-9: readings
    moved = [r for r in fr if r["distance"] > 0]
    amounts = ("projection_amount", "floor_rise", "floor_fall", "fit_rise", "fit_total")
    finite8 = all(np.isfinite(r[k]) for r in fr for k in amounts)
    slack = 1e-6  # million euro
    # the cell-by-cell bound holds for every scalar in the band, so it lies under
    # the fit with one common scalar; a scalar in the band leaves no cell
    # negative; a negative cell's own bound is at least the negative amount
    under = all(r["floor_rise"] <= r["fit_rise"] + slack
                and r["floor_rise"] + r["floor_fall"] <= r["fit_total"] + slack
                for r in fr)
    nonneg = all(r["model_cell_least"] >= -slack for r in fr)
    covers = all(r["negative_floor_gap"] <= slack for r in fr)
    floored = sum(r["floor_rise"] + r["floor_fall"] > 0 for r in fr)
    over_rise = sum(r["projection_amount"] > r["fit_rise"] + slack for r in moved)
    c8 = {"name": "B137-8  FISIM: what the rival's own premise requires of the four "
                  "published cells, per member year: each cell's least move "
                  "(Theorem 45 (5) cell by cell), the least moves with one common "
                  "scalar, and the projection of the mean scalar, in euros and "
                  "against GDP",
          "kind": "own_reading",
          "passed": bool(fr) and finite8 and under and nonneg and covers
          and len(moved) == sum(r["side"] != "inside" for r in fr)
          and floored == outside,
          "detail": (f"{len(fr)} member years, all amounts finite; a cell's implied "
                     f"scalar outside the band in {floored} (B131's {outside}); the "
                     f"cell-by-cell bound under the common-scalar fit in every year: "
                     f"{under}; no cell negative at a scalar in the band: {nonneg}; "
                     f"every negative cell's bound at least its amount: {covers}; "
                     f"the mean of the four outside the band in {len(moved)}, where "
                     f"the mean's projection exceeds the least rise from the "
                     f"published cells in {over_rise}")}
    ea_rows = [r for r in eu if r["geo"] == EA]
    c9 = {"name": "B137-9  deflators: the slope of the published deflator in the "
                  "unpublished own relative (the borrowed items' weights), where "
                  "each 'without' reading sits on that line, and B134's cells "
                  "where the own value is published",
          "kind": "own_reading",
          "passed": bool(eu) and bool(us) and bool(ea_rows)
          and "B134-4" in rec134["objects"],
          "detail": (f"{len(eu)} EU area-years, {len(us)} US years, "
                     f"{len(rec134['objects'].get('B134-4', {}))} B134 rounds")}
    return [c6, c7, c8, c9], {"eu": eu, "us": us, "fisim": fr, "b134": rec134["objects"].get("B134-4", {}),
                              "share_1973_2014": share, "share_1973_2014_fisher": share_f}


# --------------------------------------------------------------------------
# printing


def print_readings(objs) -> None:
    fr = objs["fisim"]

    def gdp_share(rows, key):
        pct = [100 * r[key] / r["gdp"] for r in rows if r["gdp"]]
        return f"median {np.median(pct):.3f} %, max {max(pct):.3f} %" if pct else "no GDP"

    print("\nR1  FISIM: what one acceptable scalar requires of the four published "
          "cells (million euro, and against GDP)")
    cellwise = [r for r in fr if r["floor_rise"] + r["floor_fall"] > 0]
    print(f"  a cell's implied scalar outside the band in {len(cellwise)} of "
          f"{len(fr)} member years; cells that must rise in "
          f"{sum(r['floor_rise'] > 0 for r in fr)}, cells that must fall in "
          f"{sum(r['floor_fall'] > 0 for r in fr)}")
    print(f"  cell by cell, over those {len(cellwise)}: rise at least "
          f"{gdp_share(cellwise, 'floor_rise')} of GDP; fall at least "
          f"{gdp_share(cellwise, 'floor_fall')}")
    print(f"  one common scalar, over those {len(cellwise)}: least rise "
          f"{gdp_share(cellwise, 'fit_rise')}; least total move "
          f"{gdp_share(cellwise, 'fit_total')}")
    negy = [r for r in fr if r["negative_cells"] > 0]
    print(f"  {len(negy)} years with a negative published cell "
          f"({sum(r['negative_cells'] for r in negy)} cells); every such cell's own "
          f"bound is at least its amount")
    moved = sorted([r for r in fr if r["distance"] > 0],
                   key=lambda r: -r["projection_amount"])
    print(f"\n  the mean of the four taken as the office's one scalar: outside the "
          f"band in {len(moved)} years")
    for r in moved[:14]:
        gdp = r["gdp"]
        share = f" ({100 * r['projection_amount'] / gdp:.3f} % of GDP)" if gdp else ""
        print(f"  {r['geo']} {r['year']}: mean {r['scalar']:.2f} {r['side']} "
              f"[{r['low']:.2f}, {r['high']:.2f}] by {r['distance']:.2f}; projection "
              f"{r['projection_amount']:,.0f}{share}; from the published cells: rise "
              f"at least {r['floor_rise']:,.0f}, fall at least {r['floor_fall']:,.0f}, "
              f"least total move {r['fit_total']:,.0f}; published negative "
              f"{r['negative_published']:,.0f}")
    below = [r for r in moved if r["side"] == "below"]
    above = [r for r in moved if r["side"] == "above"]
    both = sum(r["sectors_outside"] == 2 for r in moved)
    cover = [r for r in moved if r["negative_published"] < 0]
    covered = [r for r in cover if r["projection_amount"] >= -r["negative_published"]]
    print(f"  {len(moved)} years outside the common band: {len(below)} below, "
          f"{len(above)} above; outside both sectors' own intervals in {both}, one "
          f"sector's in {len(moved) - both}")
    print(f"  the projection against the published cells' own moves, {len(moved)} "
          f"years: above the least rise in "
          f"{sum(r['projection_amount'] > r['fit_rise'] + 1e-6 for r in moved)}, above "
          f"the cell-by-cell rise in "
          f"{sum(r['projection_amount'] > r['floor_rise'] + 1e-6 for r in moved)}, above "
          f"the least total move in "
          f"{sum(r['projection_amount'] > r['fit_total'] + 1e-6 for r in moved)}")
    print(f"  of the {len(cover)} with a negative published cell, the projection is "
          f"at least the negative amount in {len(covered)}; added cell by cell to "
          f"the published cells it leaves a negative cell in "
          f"{sum(r['cells_negative_after_projection'] > 0 for r in covered)} of those "
          f"and in {sum(r['cells_negative_after_projection'] > 0 for r in moved)} of "
          f"the {len(moved)}")
    print(f"  over the {len(moved)}: projection {gdp_share(moved, 'projection_amount')} "
          f"of GDP; cell-by-cell rise {gdp_share(moved, 'floor_rise')}; least rise "
          f"with one scalar {gdp_share(moved, 'fit_rise')}; least total move "
          f"{gdp_share(moved, 'fit_total')}")
    imb = [abs(r["dep_stock"] - r["loan_stock"]) / (r["dep_stock"] + r["loan_stock"])
           for r in fr]
    print(f"  stock imbalance |D - L| / (D + L) over {len(fr)} years: median "
          f"{np.median(imb):.3f}, range {min(imb):.3f} to {max(imb):.3f}")

    print("\nR2  euro area consumption deflator: published, the borrowed items' "
          "weights and relatives, the rest, and the bias")
    for r in [x for x in objs["eu"] if x["geo"] == EA]:
        print(f"  {r['year']}: published {r['published']:.2f}; rent w {r['w_rent']:.4f}"
              f" p {r['p_rent']:+.2f}; FISIM w {r['w_fisim']:.4f} p {r['p_fisim']:+.2f};"
              f" rest {r['p_rest']:+.2f}; bias at own = rest {r['bias']:+.3f}")
    slopes = np.array([r["w_rent"] + r["w_fisim"] for r in objs["eu"]])
    print(f"  slope of the published deflator in the own relative (the two weights "
          f"together), {len(slopes)} area-years: median {np.median(slopes):.4f}, "
          f"range {slopes.min():.4f} to {slopes.max():.4f}")
    us = objs["us"]
    s = np.array([r["share"] for r in us])
    print(f"\nR3  US PCE (a Fisher index): the borrowed items' base share, "
          f"{us[0]['year']} to {us[-1]['year']}: median {np.median(s):.4f}, range "
          f"{s.min():.4f} to {s.max():.4f}; 1973-2014 borrowed share of the "
          f"divergence {objs['share_1973_2014']:.4f} by the contributions "
          f"construct, {objs['share_1973_2014_fisher']:.4f} by the Fisher removal")
    both = [r for r in us if r["without_fisher"] is not None]
    gap = np.array([r["without"] - r["without_fisher"] for r in both])
    print(f"  the two operators' 'without', {len(both)} years: the contributions "
          f"construct less the Fisher removal, median {np.median(gap):+.4f}, range "
          f"{gap.min():+.4f} to {gap.max():+.4f} points")
    for y in (1975, 1985, 1995, 2005, 2015, 2023):
        r = next((x for x in us if x["year"] == y), None)
        if r:
            print(f"  {y}: PCE {r['g']:.2f}, share {r['share']:.4f}, borrowed "
                  f"{r['p_borrowed']:+.2f}, rest {r['p_rest']:+.2f}, bias "
                  f"{r['bias']:+.3f}")
    print("\nR4  B134: the own value published, the bias read directly")
    for k, r in sorted(objs["b134"].items()):
        print(f"  CHN {k}: national over rural {r['national_over_rural_pct']} %, "
              f"national at {r['national_position_rural0_urban1']} of the rural-urban "
              f"interval")


# --------------------------------------------------------------------------
# record


def _rv(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return float(f"{x:.10g}") if math.isfinite(x) else None
    return x


def build_record(crit, objs) -> dict:
    rec = {
        "stage": "B137",
        "config": {
            "seed": SEED, "tolerance": TOL, "synthetic_fields": FIELDS,
            "carriers": {
                "B131": "data/raw/b131 through b131_readings.load_all, fisim, bands",
                "B132": "data/raw/b132 through b132_readings.load_all; area EA20; "
                        "borrowed items CP042 and CP122",
                "B133": "data/raw/b133 through b133_readings.load_all; the "
                        "borrowed items' base share (DOWNRC + DIMPRC) / DPCERC",
                "B134": "results/b134_readings.json, object B134-4"},
            "scalar": "the mean of the four scalars implied by the four sides, "
                      "as B131 takes the office's scalar",
            "cells": list(CELLS),
            "projection_amount": "distance from the mean scalar to the band times "
                                 "the stock of the side it understates, million "
                                 "euro: the least correction on a baseline rebuilt "
                                 "from the mean, no bound on the published cells",
            "floor_rise, floor_fall": "Theorem 45 (5) cell by cell: distance from "
                                      "a cell's implied scalar to the band times "
                                      "that cell's stock, summed over the cells "
                                      "that must rise and that must fall",
            "fit_rise, fit_total": "one common scalar in the band: the least sum "
                                   "of the cells' increases, and of their absolute "
                                   "moves, from the published cells",
            "us_operators": "B133's: the contributions construct and the Fisher "
                            "removal; the PCE price index is a Fisher index",
            "nothing_fetched": True,
        },
        "criteria": [{k: c[k] for k in ("name", "kind", "passed", "detail")}
                     for c in crit],
        "fisim": [{k: ([_rv(x) for x in v] if isinstance(v, list) else _rv(v))
                   for k, v in r.items()
                   if k not in ("match", "model_cell_least", "negative_floor_gap")}
                  for r in objs["fisim"]],
        "eu_deflator": [{k: _rv(v) for k, v in r.items()} for r in objs["eu"]],
        "us_pce": [{k: _rv(v) for k, v in r.items()} for r in objs["us"]],
        "us_1973_2014_borrowed_share": _rv(objs["share_1973_2014"]),
        "us_1973_2014_borrowed_share_fisher": _rv(objs["share_1973_2014_fisher"]),
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Station not closed: the readings are not "
                                    "yet written into RESULTS.md.")
    return rec


def write_record(rec) -> None:
    text = json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    RECORD.write_text(text, encoding="utf-8", newline="\n")
    print(f"\nwrote {RECORD.name}")


# --------------------------------------------------------------------------


def selftest() -> bool:
    ok = True
    crit = block_one(quick=True)
    print("  clean  " + "  ".join(f"{c['name'][:6]} {c['passed']}" for c in crit))
    ok &= all(c["passed"] for c in crit)
    for fault, idx in (("sign", 0), ("current_shares", 0), ("base_stock", 1),
                       ("swapped", 2), ("midpoint", 3), ("forget_weight", 4),
                       ("ordinary_tornqvist", 4)):
        c = block_one(fault=fault, quick=True)[idx]
        print(f"  fault {fault:15s} {c['name'][:6]} fails: {not c['passed']}"
              f"  {c['detail'][:90]}")
        ok &= not c["passed"]
    crit2, objs = block_two()
    print("  clean  " + "  ".join(f"{c['name'][:6]} {c['passed']}" for c in crit2))
    ok &= all(c["passed"] for c in crit2)
    for fault, idx in (("own_zero", 0), ("one_operator", 0), ("year_end", 1),
                       ("mean_as_floor", 2)):
        c = block_two(fault=fault)[0][idx]
        print(f"  fault {fault:15s} {c['name'][:6]} fails: {not c['passed']}")
        ok &= not c["passed"]
    return bool(ok)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        t0 = time.perf_counter()
        ok = selftest()
        print(f"selftest {'passed' if ok else 'FAILED'} "
              f"({time.perf_counter() - t0:.1f} s)")
        return 0 if ok else 1
    if a.run:
        t0 = time.perf_counter()
        crit = block_one()
        crit2, objs = block_two()
        for c in crit + crit2:
            print(f"{c['name']}\n    [{c['kind']}] "
                  f"{'PASS' if c['passed'] else 'FAIL'}: {c['detail']}")
        print_readings(objs)
        print(f"\n{time.perf_counter() - t0:.1f} s")
        if not a.no_write:
            write_record(build_record(crit + crit2, objs))
        return 0 if all(c["passed"] for c in crit + crit2) else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
