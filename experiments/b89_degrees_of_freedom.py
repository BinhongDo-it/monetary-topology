"""B89: one identity covers every configuration of the two margins, and it has four cells.

B88 counted two configurations and found the extensive one short by a boundary condition and
the mixed one square. B89 counts all of them at once. Write `c` for the cultivated lands, `j`
for how many of them are worked by two methods, and `f = 1` when some cultivated land still has
spare capacity, so that a boundary condition applies, and `f = 0` when none has:

    equations - unknowns = j + f - 1

**So the system is square exactly when `j + f = 1`, and never for any other reason.** The two
square cells are the two stations already on the board: `(j, f) = (0, 1)` is B72's extensive
rent with the marginal land free, and `(1, 0)` is B88's mixed system with no free land. The
other cells are not modelling choices, they are arithmetic:

    j = 0, f = 0    short by one, and the wage is not determined by cost
    j >= 1, f = 1   over-determined: intensive cultivation does not coexist with spare capacity
    j >= 2          over-determined: at most one acre is worked by two methods

**The last two hold in general position and not otherwise.** More equations than unknowns leaves
the extra rows to be satisfied by the rest, which takes an exact coincidence among the technical
coefficients; a random draw misses that with probability one, so the sweep here can never meet it.
`B89-8` builds the exceptions from a recipe instead. **The identity is untouched by them**: counting
says a solution needs a coincidence, not that none exists.

**The missing equation in the first of those has a direction, and the direction is the labour
vector**: raise the wage by `delta` and every rent falls by `lambda_i delta`. The one degree of
freedom is the wage-rent frontier, and a cycle closure is what puts a point on it.

B72's envelope solver and land generator and B73's intensive pair are imported rather than
rewritten. B88's mixed closure is recomputed here from the same rows this station builds, which
is the point: the rows are the object and the two stations have to agree on them.

Run:
    python experiments/b89_degrees_of_freedom.py
    python experiments/b89_degrees_of_freedom.py --selftest
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
OUT = ROOT / "results" / "b89_degrees_of_freedom.json"

SEED = 89
N_SYSTEMS = 300
LANDS = (3, 7)
RATE = 0.05
YIELD = (1.05, 2.00)
CORN_FACTOR = (1.0, 3.0)
LABOUR_FACTOR = (1.0, 3.0)
TOL = 1e-12
CONSISTENT = 1e-9          # a residual below this is a solved system, above it is no solution
N_TUNED = 40               # constructed systems per over-determined cell, see `tuned`


def marginal_of(alphas, lams, cultivated, r):
    """The land with spare capacity is the one on the envelope, and it is the one that is free.

    Reading it off the wage curves rather than off the position in the list is what B89-1
    caught: taking the last land in the list disagrees with B72 whenever the list is not
    sorted by fertility, which is most of the time.
    """
    idx = np.asarray(sorted(cultivated))
    w_each = B72.wage_curve(alphas[idx], lams[idx], r)
    return int(np.argmin(w_each))


def rows(alphas, lams, cultivated, intensive, dose, r, boundary):
    """One row per operated method in the unknowns `(w, rho_1 .. rho_c)`, corn the unit.

    `boundary` adds the zero rent on the marginal land, which is what spare capacity buys.
    Nothing here knows about B72's or B73's solver: they have to agree with these rows.
    """
    q2, c2, d2 = dose
    A, b = [], []
    for pos, i in enumerate(cultivated):
        e = np.zeros(1 + len(cultivated)); e[0] = lams[i]; e[1 + pos] = 1.0
        A.append(e); b.append(1.0 - (1.0 + r) * alphas[i])
        if i in intensive:
            e2 = np.zeros(1 + len(cultivated)); e2[0] = lams[i] * d2; e2[1 + pos] = 1.0
            A.append(e2); b.append(q2 - (1.0 + r) * alphas[i] * c2)
    if boundary:
        e = np.zeros(1 + len(cultivated))
        e[1 + marginal_of(alphas, lams, cultivated, r)] = 1.0
        A.append(e); b.append(0.0)
    return np.array(A), np.array(b)


def tuned(rng, cell, r=RATE):
    """Systems built to make an over-determined cell consistent, which it can be.

    **Counting says nothing about solvability on its own.** More equations than unknowns means no
    solution **in general position**, and general position is what a random draw gives with
    probability one, so the sweep in `draws` can never meet the exceptions. They are built here
    instead, from a recipe rather than one lucky pair.

    `(2, 0)`: both acres worked by two methods. Each acre's own pair fixes the wage at
    `w_i = [q - 1 - (1+r) a_i (c - 1)] / [l_i (d - 1)]`, so choosing the `a_i` freely and setting
    `l_i` to put every `w_i` on one target makes the four rows agree.

    `(1, 1)`: intensive cultivation on the acre that also carries the zero-rent boundary. That
    acre's single method gives `w = [1 - (1+r) a] / l` and its second method gives
    `w = [q - (1+r) a c] / (l d)`, so the one choice `d = [q - (1+r) a c] / [1 - (1+r) a]` puts
    them on the same wage and the boundary costs nothing.
    """
    out = []
    for _ in range(N_TUNED):
        k = 2
        alphas = rng.uniform(0.15, 0.35, k)
        q2, c2 = float(rng.uniform(1.2, 1.8)), float(rng.uniform(1.5, 2.5))
        if cell == (2, 0):
            w_star = float(rng.uniform(0.3, 0.9))
            d2 = float(rng.uniform(1.5, 2.5))
            num = q2 - 1.0 - (1.0 + r) * alphas * (c2 - 1.0)
            if (num <= 0.0).any():
                continue
            lams = num / (w_star * (d2 - 1.0))
            intensive = {0, 1}
            boundary = 0
        else:
            lams = rng.uniform(0.3, 0.8, k)
            # the acre that carries the boundary is the one with the lowest wage curve
            m = int(np.argmin(B72.wage_curve(alphas, lams, r)))
            denom = 1.0 - (1.0 + r) * alphas[m]
            if denom <= 0.0:
                continue
            d2 = float((q2 - (1.0 + r) * alphas[m] * c2) / denom)
            if d2 <= 1.0:
                continue
            intensive = {m}
            boundary = 1
            w_star = float(denom / lams[m])
        if (lams <= 0.0).any():
            continue
        dose = (q2, c2, d2)
        A, b = rows(alphas, lams, list(range(k)), intensive, dose, r, boundary)
        st = standing(A, b)
        out.append({"cell": list(cell), "equations": st["equations"], "unknowns": st["unknowns"],
                    "residual": st["residual"], "wage": float(st["x"][0]),
                    "rents": [float(v) for v in st["x"][1:]],
                    "target_wage": w_star, "dose": [float(x) for x in dose],
                    "alphas": [float(x) for x in alphas], "lams": [float(x) for x in lams],
                    "rents_non_negative": bool(min(st["x"][1:]) >= -TOL)})
    return out


def standing(A, b):
    """Solve in least squares and read three things off it: shape, null dimension, residual."""
    x, _r, rank, _sv = np.linalg.lstsq(A, b, rcond=None)
    eq, un = A.shape
    return {"equations": int(eq), "unknowns": int(un), "null": int(un - rank),
            "residual": float(np.linalg.norm(A @ x - b)), "x": x}


def cell_of(null, residual):
    """Three states, and the middle one has to exist (rule 23)."""
    if residual > CONSISTENT:
        return "no solution"
    return "one solution" if null == 0 else "a family of solutions"


def draws(rng, n_systems):
    out = []
    for _ in range(n_systems):
        k = int(rng.integers(LANDS[0], LANDS[1]))
        alphas, lams = B72.random_lands(rng, k)
        if B72.wage_curve(alphas, lams, RATE).min() <= 0.0:
            continue
        dose = (float(rng.uniform(*YIELD)), float(rng.uniform(*CORN_FACTOR)),
                float(rng.uniform(*LABOUR_FACTOR)))
        # one intensification technology per acre as well, for the choice reading
        per_acre = [(float(rng.uniform(*YIELD)), float(rng.uniform(*CORN_FACTOR)),
                     float(rng.uniform(*LABOUR_FACTOR))) for _ in range(k)]
        cases = []
        for c in range(2, k + 1):
            cultivated = list(range(c))
            for j in (0, 1, 2):
                if j > c:
                    continue
                for f in (0, 1):
                    A, b = rows(alphas, lams, cultivated, set(cultivated[:j]), dose, RATE, f)
                    st = standing(A, b)
                    st.update({"c": c, "j": j, "f": f})
                    cases.append(st)
        out.append({"k": k, "alphas": alphas, "lams": lams, "dose": dose,
                    "per_acre": per_acre, "cases": cases})
    return out


def tuned_all(rng):
    return {"(2, 0)": tuned(rng, (2, 0)), "(1, 1)": tuned(rng, (1, 1))}


# ------------------------------------------------- criteria

def crit_reduces(sample):
    """B89-1: the two square cells are B72's answer and B88's, from their own solvers."""
    worst_ext = worst_int = 0.0
    n_ext = n_int = 0
    for s in sample:
        for cse in s["cases"]:
            c, j, f = cse["c"], cse["j"], cse["f"]
            idx = np.arange(c)
            if (j, f) == (0, 1):
                w72, _marg, _rents = B72.solve(s["alphas"][idx], s["lams"][idx], RATE)
                worst_ext = max(worst_ext, abs(float(cse["x"][0]) - w72)); n_ext += 1
            if (j, f) == (1, 0):
                q2, c2, d2 = s["dose"]
                w73, _rho, _m = B73.intensive((1.0, q2), (s["alphas"][0], s["alphas"][0] * c2),
                                              (s["lams"][0], s["lams"][0] * d2), RATE)
                worst_int = max(worst_int, abs(float(cse["x"][0]) - w73)); n_int += 1
    ok = bool(sample) and n_ext > 0 and n_int > 0 and worst_ext < 1e-9 and worst_int < 1e-9
    detail = (f"the rows this station builds know nothing about either solver, and the two "
              f"square cells come out as those solvers' own answers: `(j, f) = (0, 1)` matches "
              f"B72's envelope wage to {worst_ext:.2e} over {n_ext} cases and `(1, 0)` matches "
              f"B73's pair to {worst_int:.2e} over {n_int}. **Both are imported**, so the "
              f"three stations can disagree about the rows")
    return ok, detail, {"worst_extensive": worst_ext, "worst_intensive": worst_int,
                        "extensive_cases": n_ext, "intensive_cases": n_int}


def crit_identity(sample):
    """B89-2: equations minus unknowns is j + f - 1, printed as shapes rather than counted."""
    shapes, breaks = set(), []
    for s in sample:
        for cse in s["cases"]:
            shapes.add((cse["c"], cse["j"], cse["f"], cse["equations"], cse["unknowns"]))
            if cse["equations"] - cse["unknowns"] != cse["j"] + cse["f"] - 1:
                breaks.append({k: cse[k] for k in ("c", "j", "f", "equations", "unknowns")})
    listed = sorted(shapes)
    ok = bool(listed) and not breaks
    shown = "; ".join(f"c={c} j={j} f={f}: {eq} by {un}" for c, j, f, eq, un in listed[:9])
    widest = max((x[0] for x in listed), default=0)
    detail = (f"`equations - unknowns = j + f - 1` on all {len(listed)} distinct shapes drawn, "
              f"with `c` running 2 to {widest}. **Shapes printed rather than "
              f"counted**: {shown} and {max(0, len(listed) - 9)} more. **The identity is what "
              f"makes `j + f = 1` the square condition**, and both of its solutions are already "
              f"stations: `(0, 1)` is extensive rent with a free margin and `(1, 0)` is a "
              f"second method with none")
    return ok, detail, {"distinct_shapes": len(listed), "breaks": breaks,
                        "shapes": [list(x) for x in listed]}


def crit_solvability(sample):
    """B89-3: three states over the grid, and only j + f = 1 gives one solution."""
    seen = {}
    for s in sample:
        for cse in s["cases"]:
            key = (cse["j"], cse["f"])
            got = cell_of(cse["null"], cse["residual"])
            seen.setdefault(key, {}).setdefault(got, 0)
            seen[key][got] += 1
    want = {(0, 0): "a family of solutions", (0, 1): "one solution", (1, 0): "one solution",
            (1, 1): "no solution", (2, 0): "no solution", (2, 1): "no solution"}
    wrong = {k: v for k, v in seen.items()
             if k in want and (len(v) != 1 or want[k] not in v)}
    ok = bool(seen) and not wrong and set(want) <= set(seen)
    lines = "; ".join(f"(j={j}, f={f}) {list(v)[0]} on {sum(v.values())}"
                      for (j, f), v in sorted(seen.items()))
    detail = (f"every drawn case falls in one of three states and each `(j, f)` gives one of "
              f"them without exception: {lines}. **The two classical facts follow from the "
              f"identity in general position**: intensive cultivation does not coexist with "
              f"spare capacity, since `(1, 1)` has no solution, and at most one acre is worked "
              f"by two methods, since `(2, 0)` has none either. **The middle state exists** and "
              f"is `(0, 0)`, where the rows are consistent and leave a family. **General "
              f"position is not a hedge and it is not free**: more equations than unknowns "
              f"leaves the extra rows to be satisfied by the rest, which takes an exact "
              f"coincidence among the technical coefficients. A random draw misses those with "
              f"probability one, **so this sweep cannot meet them however large it is**, and "
              f"`B89-8` builds them instead")
    return ok, detail, {"states": {f"j{j}f{f}": v for (j, f), v in sorted(seen.items())},
                        "wrong": {f"j{k[0]}f{k[1]}": v for k, v in wrong.items()}}


def crit_frontier(sample):
    """B89-4: the missing equation has a direction, and it is the labour vector."""
    worst = 0.0
    n = 0
    for s in sample:
        for cse in s["cases"]:
            if (cse["j"], cse["f"]) != (0, 0):
                continue
            c = cse["c"]
            A, b = rows(s["alphas"], s["lams"], list(range(c)), set(), s["dose"], RATE, False)
            _u, sv, vt = np.linalg.svd(A)
            v = vt[-1]                                  # the null direction
            want = np.concatenate([[1.0], -np.asarray(s["lams"][:c], dtype=float)])
            v = v / v[0] if abs(v[0]) > 1e-12 else v
            worst = max(worst, float(np.abs(v - want).max())); n += 1
    ok = n > 0 and worst < 1e-9
    detail = (f"in the cell where the rows leave a family, the family is one-dimensional and "
              f"its direction is `(1, -lambda_1, ..., -lambda_c)` to {worst:.2e} over {n} "
              f"cases. **Raise the wage by one and every rent falls by that land's labour "
              f"input**, so the single missing equation is the one that says where on the "
              f"wage-rent frontier the economy sits. **A cycle closure is what puts a point on "
              f"it**, which is why the intensive step both adds a dimension to the graph and "
              f"removes one from the price system")
    return ok, detail, {"worst_direction_gap": worst, "cases": n}


def crit_choice(sample):
    """B89-5: give every acre its own second method and the choice is still not fertility."""
    systems = differ = picked_best = 0
    viable_counts = []
    for s in sample:
        k = s["k"]
        idx = list(range(k))
        own = B72.wage_curve(s["alphas"], s["lams"], RATE)
        w_ext = float(own.min())
        ws = []
        for i in idx:
            q2, c2, d2 = s["per_acre"][i]
            w, _rho, _m = B73.intensive((1.0, q2), (s["alphas"][i], s["alphas"][i] * c2),
                                        (s["lams"][i], s["lams"][i] * d2), RATE)
            ws.append(np.nan if w is None else w)
        ws = np.asarray(ws, dtype=float)
        ok_cells = np.isfinite(ws) & (ws > 0.0) & (ws <= w_ext + TOL)
        if not ok_cells.any():
            continue
        systems += 1
        viable_counts.append(int(ok_cells.sum()))
        pick = int(np.where(ok_cells, ws, -np.inf).argmax())
        by_fert = int(np.where(ok_cells, np.asarray(own, dtype=float), -np.inf).argmax())
        differ += int(pick != by_fert)
        picked_best += int(pick == int(np.argmax(own)))
    ok = systems > 0 and differ > 0 and picked_best < systems
    mean_v = float(np.mean(viable_counts)) if viable_counts else 0.0
    detail = (f"a separate second method drawn for each acre, so the acres differ in their "
              f"intensification as well as in their fertility. On {systems} systems with at "
              f"least one viable acre, a mean of {mean_v:.2f} acres are viable, the acre taken "
              f"is the most fertile on {picked_best}, and **the two choosing rules run over the "
              f"same candidates part on {differ}**. B88 read the same thing with one technology "
              f"per system; **giving each acre its own does not make fertility the rule**, it "
              f"only adds a second source of difference between them")
    return ok, detail, {"systems": systems, "rules_part": differ, "picked_best": picked_best,
                        "mean_viable_acres": mean_v}


def crit_floor(sample):
    """B89-6: the line between solved and not solved is measured, not declared."""
    solved, unsolved = [], []
    for s in sample:
        for cse in s["cases"]:
            (solved if cse["j"] + cse["f"] == 1 else
             unsolved if cse["j"] + cse["f"] > 1 else solved).append(cse["residual"])
    hi_solved = max(solved) if solved else np.inf
    lo_unsolved = min(unsolved) if unsolved else 0.0
    gap = lo_unsolved / hi_solved if hi_solved > 0 else np.inf
    ok = bool(solved) and bool(unsolved) and lo_unsolved > hi_solved and gap > 1e6
    detail = (f"the largest residual among the cases that have a solution is {hi_solved:.2e} "
              f"and the smallest among those that do not is {lo_unsolved:.2e}, a ratio of "
              f"{gap:.2e}. **The line is measured on this run rather than declared**, which is "
              f"what gate six asks of a floor: a tolerance chosen in advance would be a number "
              f"this station made up, and the separation here is wide enough that no choice "
              f"between the two orders of magnitude changes any verdict")
    return ok, detail, {"largest_solved_residual": hi_solved,
                        "smallest_unsolved_residual": lo_unsolved, "ratio": gap}


def crit_general_position(tuned_cells):
    """B89-8: the over-determined cells are consistent on a set the sweep cannot reach."""
    out = {}
    for name, rowset in tuned_cells.items():
        good = [r for r in rowset if r["residual"] < CONSISTENT]
        over = [r for r in good if r["equations"] > r["unknowns"]]
        nn = [r for r in over if r["rents_non_negative"]]
        out[name] = {"built": len(rowset), "consistent": len(good), "over_determined": len(over),
                     "rents_non_negative": len(nn),
                     "worst_residual": max((r["residual"] for r in rowset), default=None),
                     "example": over[0] if over else None}
    ok = (len(out) >= 2
          and all(v["built"] > 0 and v["over_determined"] == v["built"]
                  and v["consistent"] == v["built"] and v["rents_non_negative"] > 0
                  for v in out.values()))
    shown = "; ".join(f"{k}: {v['over_determined']} of {v['built']} built are over-determined "
                      f"and consistent, worst residual {v['worst_residual']:.1e}, "
                      f"{v['rents_non_negative']} of them with non-negative rents"
                      for k, v in sorted(out.items()))
    ex = out.get("(2, 0)", {}).get("example") or {}
    detail = (f"the two excluded cells, built rather than drawn: {shown}. **The recipe is one "
              f"line in each case.** For `(2, 0)`, each acre's own pair of methods fixes the "
              f"wage at `[q - 1 - (1+r) a_i (c - 1)] / [l_i (d - 1)]`, so putting every acre's "
              f"on one target by choice of `l_i` makes four rows in three unknowns agree: one "
              f"instance returns a wage of {ex.get('wage', float('nan')):.4f} with rents "
              f"{[round(x, 4) for x in ex.get('rents', [])]} at residual "
              f"{ex.get('residual', float('nan')):.1e}. For `(1, 1)`, the single choice "
              f"`d = [q - (1+r) a c] / [1 - (1+r) a]` on the boundary acre puts its two methods "
              f"on the same wage and the zero rent costs nothing. **So `equations - unknowns = "
              f"j + f - 1` is untouched and the exclusion it is usually read as is a "
              f"general-position statement**: counting tells you a solution needs a coincidence, "
              f"not that none exists. **These sit on a set of measure zero**, which is why "
              f"`B89-3` sees none of them and why it could not have")
    return ok, detail, out


def crit_registration():
    """B89-7: the same round writes back to the two stations this one generalises."""
    want = ["b88_two_margins.md", "b72_land_and_rent.md"]
    missing = [f for f in want
               if "b89_degrees_of_freedom.md" not in (ROOT / "docs" / f).read_text(encoding="utf-8")]
    ok = not missing
    detail = (f"the stations this one generalises "
              f"{'each name it' if ok else '**do not all name it: ' + ', '.join(missing) + '**'}, "
              f"so a reader of either finds the identity their two cases are cases of. `D20`")
    return ok, detail, {"missing_writebacks": missing}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(5)
    sample = draws(rng, 40)
    if len(sample) < 15:
        fails.append(f"the fixture drew only {len(sample)} systems")

    named = (("B89-1", crit_reduces), ("B89-2", crit_identity), ("B89-3", crit_solvability),
             ("B89-4", crit_frontier), ("B89-5", crit_choice), ("B89-6", crit_floor))
    tuned_cells = tuned_all(np.random.default_rng(89))
    got = crit_general_position(tuned_cells)
    if not got[0]:
        fails.append(f"B89-8 does not pass on the fixture: {got[1][:150]}")
    if crit_general_position({})[0]:
        fails.append("B89-8 passes on an empty construction")

    # B89-8: the point is that these are over-determined AND consistent, so a fixture where
    # they are square, or where the residual says no solution, has to be rejected
    for label, fn in (
            ("the built systems are square",
             lambda r: dict(r, unknowns=r["equations"])),
            ("the built systems have no solution",
             lambda r: dict(r, residual=1.0)),
            ("no built system has non-negative rents",
             lambda r: dict(r, rents_non_negative=False))):
        bent = {k: [fn(r) for r in v] for k, v in tuned_cells.items()}
        if crit_general_position(bent)[0]:
            fails.append(f"B89-8 passes when {label}")
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:130]}")
        if fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # B89-1: the rows and the imported solvers have to be able to disagree
    bent = [dict(s, alphas=np.asarray(s["alphas"]) + 1e-3) for s in sample]
    if crit_reduces(bent)[0]:
        fails.append("B89-1 passes when the rows and the solvers are built on different lands")

    # B89-2: the identity is what makes j + f = 1 the square condition, so a case whose shape
    # does not obey it has to be reported rather than absorbed
    off = []
    for s in sample:
        cs = [dict(x) for x in s["cases"]]
        cs[0]["equations"] += 1
        off.append(dict(s, cases=cs))
    if crit_identity(off)[0]:
        fails.append("B89-2 passes when one case's shape breaks the identity")

    # B89-3: dropping the middle state would turn the indeterminate cell into a solved one,
    # which is the whole reason the wage needs a closure at all
    twostate = []
    for s in sample:
        cs = [dict(x, null=0) for x in s["cases"]]
        twostate.append(dict(s, cases=cs))
    if crit_solvability(twostate)[0]:
        fails.append("B89-3 passes when the family of solutions is reported as one solution")

    # B89-4: the direction is the labour vector and not the corn one, and only bending the
    # expectation tests that. Exchanging both in the fixture rebuilds the rows too, so it
    # tests nothing
    matched_corn = 0
    for s in sample:
        for cse in s["cases"]:
            if (cse["j"], cse["f"]) != (0, 0):
                continue
            c = cse["c"]
            A, _b = rows(s["alphas"], s["lams"], list(range(c)), set(), s["dose"], RATE, False)
            v = np.linalg.svd(A)[2][-1]
            v = v / v[0] if abs(v[0]) > 1e-12 else v
            corn = np.concatenate([[1.0], -(1.0 + RATE) * np.asarray(s["alphas"][:c])])
            matched_corn += int(float(np.abs(v - corn).max()) < 1e-9)
    if matched_corn:
        fails.append(f"the null direction matches the corn vector on {matched_corn} cases")

    # B89-5: if the acre taken were the most fertile one, this would be B88's fiat again
    # B89-5: doses built so that each acre's closure wage is a fixed fraction of that acre's
    # own wage curve put the two rules in the same order, which is B88's fiat wearing a
    # different hat, and the criterion has to reject it
    fert = []
    for s in sample:
        own = np.asarray(B72.wage_curve(s["alphas"], s["lams"], RATE), dtype=float)
        frac = 0.5 * float(own.min()) / float(own.max())
        pa = [(1.0 + frac * (1.0 - (1.0 + RATE) * float(s["alphas"][i])), 1.0, 2.0)
              for i in range(s["k"])]
        fert.append(dict(s, per_acre=pa))
    if crit_choice(fert)[0]:
        fails.append("B89-5 passes when the closure order is built to match the fertility order")

    # the same fixture with the most fertile acre made unviable trips only the clause that
    # counts where the two rules part, so it is what says that clause is load-bearing
    fert2 = []
    for s in fert:
        pa = list(s["per_acre"])
        top = int(np.argmax(np.asarray(B72.wage_curve(s["alphas"], s["lams"], RATE))))
        pa[top] = (0.5, 1.0, 2.0)                       # a yield below one puts its wage negative
        fert2.append(dict(s, per_acre=pa))
    got5 = crit_choice(fert2)
    if got5[0]:
        fails.append("B89-5 passes when the two rules never part")
    if got5[2]["picked_best"] >= got5[2]["systems"]:
        fails.append("the B89-5 probe trips the other clause too, so it tests nothing")

    # B89-3: a grid missing the over-determined cells says nothing about them, and the
    # criterion has to notice rather than report the cells it happens to have
    thin = [dict(s, cases=[c for c in s["cases"] if c["j"] < 2]) for s in sample]
    if crit_solvability(thin)[0]:
        fails.append("B89-3 passes on a grid with no two-acre cases in it")

    # B89-6: a floor asserted rather than measured would pass on any separation at all
    flat = []
    for s in sample:
        cs = [dict(x, residual=1.0 if x["j"] + x["f"] > 1 else 0.5) for x in s["cases"]]
        flat.append(dict(s, cases=cs))
    if crit_floor(flat)[0]:
        fails.append("B89-6 passes on a separation of one order of magnitude")

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
    tuned_cells = tuned_all(rng)
    cases = sum(len(s["cases"]) for s in sample)
    print(f"{len(sample)} systems, {cases} configurations\n")

    criteria, report = [], {}
    for name, kind, fn in (("B89-1", "known_answer", crit_reduces),
                           ("B89-2", "own_reading", crit_identity),
                           ("B89-3", "own_reading", crit_solvability),
                           ("B89-4", "own_reading", crit_frontier),
                           ("B89-5", "own_reading", crit_choice),
                           ("B89-6", "instrument", crit_floor)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_general_position(tuned_cells)
    criteria.append({"name": "B89-8", "kind": "own_reading", "passed": bool(ok),
                     "detail": detail})
    report["B89-8"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B89-8  [own_reading]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B89-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B89-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B89-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B89",
        "config": {"seed": args.seed, "systems": args.systems, "lands": list(LANDS),
                   "rate": RATE, "yield": list(YIELD), "corn_factor": list(CORN_FACTOR),
                   "labour_factor": list(LABOUR_FACTOR), "consistent_below": CONSISTENT,
                   "imports": "b72_land_and_rent, b73_two_extensions"},
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
