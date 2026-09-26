"""B93: what a continuum changes, on both indices, and one registered question reformulated.

Two registrations meet here. B77 registered whether a quadratic continuum carries a slope
reversal that survives refinement, none having been found. B86 registered whether the
componentwise minimum survives a continuum of methods per good, **which is B77's continuum with
the other index continuous**, so the two are one object read along two indices.

**B77's registered form is automatic and does not measure the family.** Its object is the rise in
the envelope's slope, `d/dx` of the cost at the owner. Every owner curve in that class is convex,
so inside any run of one owner the slope rises by construction, and refining the parameter grid
only shortens runs against a fixed `x` grid. **The well-posed object is capital per worker along
the envelope**, which is what a slope reversal means economically and what B92 measured on
discrete families.

Reformulated, the answer reverses: **capital reversing on a continuum is common relative to
discrete families and it does not collapse under refinement.** It also explains itself. B92 showed
reversing with no owner returning anywhere needs three techniques, because the pair meeting on
the envelope must not include the one
owning a zero rate; a continuum is always in that regime.

**And the count has to be split, because two different events raise `k`.** A rise at a change of
owner is capital reversing: the wage is shared at a switch, so one price system carries two capital
values. A rise with one owner throughout is a price Wicksell effect on that owner's own curve, and
no technique is chosen differently there. **The first version of this station counted them
together**, and at degree 2 more than half of what it reported was the second.

**A technique still leaves the envelope and comes back when the labels are dense.** The wobble
between neighbouring members does dissolve, leading by around `1e-8`; a return crossing the whole
family and leading by `1e-4` does not, and it survives a 64-fold refinement. **So the question
becomes whether the minimiser over the index is monotone in the rate**, which is well posed and
answered here in the negative.

**And the continuum removes B92's other reading.** There `k` is two-valued at a switch, one price
system carrying two capital values. Fill the family in and the owner moves continuously, so the
jump shrinks with the owner spacing and `k` becomes single-valued in the limit.

On the other index, the componentwise minimum is attained exactly when the minimiser stays inside
the method set, and when it is attained a single technique still attains it, which is B86's own
argument run per good and indifferent to cardinality.

B77's coefficient family and B92's capital measure are imported rather than rewritten.

Run:
    python experiments/b93_continuum_second_pass.py
    python experiments/b93_continuum_second_pass.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b77_continuum as B77                                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b93_continuum_second_pass.json"

SEED = 93
N_FAMILIES = 4000
DEGREES = (2, 3, 4, 5)
THETA_BASE = 300
THETA_LADDER = (100, 400, 1600, 6400)
COHORT = 25                    # reversing families followed through the ladder, per degree
FILL_LADDER = (5, 20, 80, 320, 1280)
X_LO, X_HI, X_POINTS = 1.02, 4.0, 1500
FLOOR = 0.02                   # every dated-labour coefficient is kept strictly positive
TOL = 1e-12
RETURN_SPAN = 0.02             # a return counts as wide when it crosses this share of the family
RETURN_MARGIN = 1e-5           # and when the returning member leads by this much at both spells
XS = np.linspace(X_LO, X_HI, X_POINTS)


def coefficients(co, n_theta):
    """A continuum of dated-labour profiles: each coefficient is a cubic in the index."""
    th = np.linspace(0.0, 1.0, n_theta)
    coef = co @ np.stack([th ** j for j in range(co.shape[1])])
    return coef - coef.min(axis=1, keepdims=True) + FLOOR


def envelope(coef, xs=XS):
    """Owner, envelope cost, and capital per worker along it. `C(theta, 1)` is total labour."""
    powers = np.stack([xs ** t for t in range(coef.shape[0])])
    C = coef.T @ powers
    idx = np.argmin(C, axis=0)
    c_min = C[idx, np.arange(len(xs))]
    labour = coef.sum(axis=0)[idx]
    k = (1.0 / labour - 1.0 / c_min) / (xs - 1.0)
    return idx, c_min, k


def poly_at(coef, members, x):
    """Cost of each named member at its own rate, both given as arrays of the same length."""
    powers = np.stack([x ** t for t in range(coef.shape[0])])
    return (coef[:, members] * powers).sum(axis=0)


def k_at(coef, members, x):
    """Capital per worker of each named member at its own rate."""
    return (1.0 / coef[:, members].sum(axis=0) - 1.0 / poly_at(coef, members, x)) / (x - 1.0)


def switch_rates(coef, idx, xs=XS, steps=80):
    """The rate at which each change of owner actually happens, by bisection on the pair.

    **The grid brackets a switch, it does not sit on it.** At `x_i` the old owner is cheaper and
    at `x_{i+1}` the new one is, so their cost difference changes sign inside, and the switch is
    the root. Bisection runs on all of a family's changes at once.
    """
    ch = np.nonzero(np.diff(idx) != 0)[0]
    if ch.size == 0:
        return (ch, np.empty(0, dtype=int), np.empty(0, dtype=int), np.empty(0),
                np.empty(0, dtype=bool))
    below, above = idx[ch], idx[ch + 1]
    lo, hi = xs[ch].astype(float).copy(), xs[ch + 1].astype(float).copy()
    flo = poly_at(coef, below, lo) - poly_at(coef, above, lo)
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        fm = poly_at(coef, below, mid) - poly_at(coef, above, mid)
        take = (flo * fm) <= 0.0
        hi = np.where(take, mid, hi)
        lo = np.where(take, lo, mid)
        flo = np.where(take, flo, fm)
    root = 0.5 * (lo + hi)
    # **A grid bracket can hold more than one change of owner, and then this root is not a
    # switch at all.** The pair is the owner at `x_i` and the owner at `x_{i+1}`; if some third
    # member is cheaper where those two cross, the envelope went through that member in
    # between and two changes have been merged into one. Bisecting a pair that never meets on
    # the envelope returns a rate at which neither is chosen, and any capital jump read there
    # is read between two techniques that are not adjacent. The refinement that would resolve
    # it costs a fresh envelope per bad bracket over up to `n_theta` members, so the bracket is
    # named rather than resolved: `on_env` is False and the caller drops it and counts it.
    powers = np.stack([root ** t for t in range(coef.shape[0])])
    cheapest = np.einsum("tm,tn->nm", coef, powers).min(axis=1)
    on_env = cheapest >= poly_at(coef, below, root) - 1e-12
    return ch, below, above, root, on_env


def reversal(coef, xs=XS):
    """Three readings, because a rise in `k` and a change of technique are different events.

    `rise` is the largest step up in capital per worker between adjacent rates, whoever owns the
    envelope. `rise_within_owner` is the largest such step where the owner does not change,
    which is a price Wicksell effect on that owner's own curve: no technique is chosen
    differently there.

    `rise_at_change` is capital reversing, **and it has to be read at the rate where the switch
    happens**. At that rate both members carry the same cost and therefore the same wage, so
    their capital per worker is two values of one price system. **Comparing `k` at two adjacent
    grid rates does not measure that**: it adds each member's own valuation drift between the
    two rates, and the published form of this station did exactly that. On draw 1,253 of the
    quadratic family it reports `+1.58e-06` where the switch itself carries `-1.69e-06`.
    """
    idx, _c, k = envelope(coef, xs)
    return reversal_from(coef, idx, k, xs)


def reversal_from(coef, idx, k, xs=XS):
    """`reversal` on an envelope already computed, so the sweep pays for it once."""
    dk = np.diff(k)
    same = np.diff(idx) == 0
    ch, below, above, xc, on_env = switch_rates(coef, idx, xs)
    keep = ch[on_env] if ch.size else ch
    at_change = ((k_at(coef, above[on_env], xc[on_env])
                  - k_at(coef, below[on_env], xc[on_env])) if keep.size else np.empty(0))
    return {"rise": float(dk.max()),
            "rise_within_owner": float(dk[same].max()) if same.any() else float("-inf"),
            "rise_at_change": float(at_change.max()) if keep.size else float("-inf"),
            "one_owner": bool(idx.max() == idx.min()),
            "owner_changes": int(ch.size),
            "owner_changes_on_envelope": int(keep.size),
            "owner_changes_merged": int(ch.size - keep.size),
            "owners": int(len(set(idx.tolist())))}


def owner_return(coef, idx, xs=XS):
    """Does a member leave the envelope and come back, and by how much does it lead when it does.

    Compressing the owner sequence and looking for `a ... b ... a` is the continuum form of
    technique return: it asks whether the minimiser over the index is non-monotone in the rate.
    **The margin is what separates a return from a tie**: adjacent members of a dense family are
    nearly identical, so the argmin wobbles between them at the last digits, and those wobbles
    lead by around `1e-8` while a real return leads by orders of magnitude more.
    """
    runs, pos = [int(idx[0])], [0]
    for i, v in enumerate(idx[1:], 1):
        if v != runs[-1]:
            runs.append(int(v))
            pos.append(i)
    seen, best, C = {}, None, None
    for q, v in enumerate(runs):
        if v in seen and q - seen[v] >= 2:
            a = seen[v]
            span = max(abs(u - v) for u in runs[a:q + 1])
            if best is None or span > best["span"]:
                if C is None:
                    C = coef.T @ np.stack([xs ** j for j in range(coef.shape[0])])
                lead = []
                for w in (a, q):
                    col = C[:, pos[w]].copy()
                    own = col[v]
                    col[v] = np.inf
                    lead.append(float((col.min() - own) / abs(own)))
                best = {"owner": v, "span": int(span), "margin": min(lead),
                        "members": int(coef.shape[1]), "sequence": runs[a:q + 1][:16]}
        seen.setdefault(v, q)
    return best


def per_good_costs(s, kind, r=0.05, w=1.0):
    """Unit cost of a method indexed by `s`, for two method sets.

    `interior`: the set is the closed `[0, 1]` and the trade-off turns inside it.
    `open_end`: the set is the half-open `(0, 1]` and the cost falls all the way toward the
    excluded end, so the infimum is not attained and the minimiser has no limit in the set.
    """
    if kind == "interior":
        a, lab = 0.2 + 0.6 * s ** 2, 0.9 - 0.5 * s
    else:
        a, lab = 0.2 + 0.6 * s, 0.9 - 0.1 * s
    return (1.0 + r) * a + w * lab


def argmin_on(kind, n):
    """`open_end` drops the excluded end point, which is what makes the set half-open."""
    s = np.linspace(0.0, 1.0, n)
    if kind == "open_end":
        s = s[1:]
    c = per_good_costs(s, kind)
    j = int(np.argmin(c))
    return {"s": float(s[j]), "cost": float(c[j]), "at_end": j in (0, len(s) - 1),
            "n": int(len(s))}


def draws(rng, n_families=N_FAMILIES):
    out = {"by_degree": {}, "best": {}, "fill": [], "per_good": {}, "returns": {}}
    best_return = None
    for deg in DEGREES:
        rises = at_change = one_owner = within = 0
        changes_total = changes_on_env = 0
        returns_any = returns_wide = at_change_no_return = 0
        best = -np.inf
        cohort = []
        for _ in range(n_families):
            co = rng.uniform(-1.0, 1.0, (deg + 1, 4))
            coef = coefficients(co, THETA_BASE)
            idx, _cm, kk = envelope(coef)
            r = reversal_from(coef, idx, kk)
            changes_total += r["owner_changes"]
            changes_on_env += r["owner_changes_on_envelope"]
            if r["rise"] > TOL:
                rises += 1
                if r["one_owner"]:
                    one_owner += 1
            if r["rise_within_owner"] > TOL:
                within += 1
            reverses = r["rise_at_change"] > TOL
            if reverses:
                at_change += 1
                # a cohort rather than the maximiser: selecting the largest rise at one
                # resolution selects on the statistic, and an artefact is exactly what would
                # win that selection. **Selected on the rise at a change of owner**, which is
                # the object B92 measured; the first version of this station selected on any
                # rise and so followed price Wicksell effects through the ladder as well
                if len(cohort) < COHORT:
                    cohort.append({"ladder": [
                        {"theta": nt,
                         "rise": float(reversal(coefficients(co, nt))["rise_at_change"])}
                        for nt in THETA_LADDER]})
            if r["rise_at_change"] > best:
                best = r["rise_at_change"]
            # technique return: does a member leave the envelope and come back
            ret = owner_return(coef, idx)
            # **B92's `12 / 1878` counts reversing with no owner returning anywhere, and this
            # station was setting its own count of every reversal against it.** Two techniques
            # reverse whenever they reswitch, `43 / 43` in B92's own record, so what needs
            # three is the kind with no return. Split here so the two figures are the same
            # object; the return test is already computed for every family, so it costs a flag.
            if reverses and ret is None:
                at_change_no_return += 1
            if ret is not None:
                returns_any += 1
                if (ret["span"] >= RETURN_SPAN * THETA_BASE
                        and ret["margin"] > RETURN_MARGIN):
                    returns_wide += 1
                    if best_return is None or ret["span"] > best_return["span"]:
                        best_return = dict(ret, degree=deg, co=co.tolist())
        out["by_degree"][str(deg)] = {"families": n_families, "reversing": at_change,
                                      "reversing_no_return": at_change_no_return,
                                      "owner_changes": changes_total,
                                      "owner_changes_on_envelope": changes_on_env,
                                      "rises_anywhere": rises, "one_owner_throughout": one_owner,
                                      "rises_within_one_owner": within,
                                      "largest_rise": float(best)}
        out["returns"][str(deg)] = {"families": n_families, "any": returns_any,
                                    "wide": returns_wide}
        out["best"][str(deg)] = cohort
    ladder = []
    if best_return is not None:
        co = np.array(best_return["co"])
        for nt in THETA_LADDER:
            coef = coefficients(co, nt)
            idx, _c, _k = envelope(coef)
            got = owner_return(coef, idx)
            ladder.append({"members": nt,
                           "span": int(got["span"]) if got else 0,
                           "margin": float(got["margin"]) if got else 0.0})
    out["return_example"] = {"best": best_return, "ladder": ladder}
    # how the two-valued k of a discrete family behaves as the family fills in
    for _ in range(60):
        co = rng.uniform(-1.0, 1.0, (4, 4))
        row = []
        for k_count in FILL_LADDER:
            coef = coefficients(co, k_count)
            idx, _c, _kk = envelope(coef)
            ch, below, above, xc, on_env = switch_rates(coef, idx)
            keep = ch[on_env] if ch.size else ch
            jumps = (np.abs(k_at(coef, above[on_env], xc[on_env])
                            - k_at(coef, below[on_env], xc[on_env]))
                     if keep.size else np.array([0.0]))
            row.append({"members": k_count, "owner_changes": int(ch.size),
                        "owner_changes_on_envelope": int(keep.size),
                        "owner_changes_merged": int(ch.size - keep.size),
                        "active_set": int(len(set(idx.tolist()))),
                        "largest_jump": float(jumps.max())})
        if row[0]["owner_changes"] > 0:
            out["fill"].append(row)
    for kind in ("interior", "open_end"):
        out["per_good"][kind] = [argmin_on(kind, n) for n in (2001, 20001, 200001)]
    return out


# ------------------------------------------------- criteria

def crit_registered_form(sample):
    """B93-1: why B77's registered object is automatic, checked on B77's own family."""
    rng = np.random.default_rng(777)
    convex = runs = 0
    rises = []
    for _ in range(20):
        co = rng.uniform(-1.0, 1.0, (3, 4))
        _a, _b, c = B77.coefficient_curves(co, np.linspace(0.0, 1.0, 400))
        convex += int(c.min() > 0.0)
        row = []
        for nt in (50, 800, 12800):
            _xs, own, slope = B77.family_envelope(co, nt, 2000, quadratic=True)
            row.append(float(np.diff(slope).max()))
            runs += int(len(set(own.tolist())))
        rises.append(row)
    arr = np.array(rises)
    all_positive = bool((arr > 0).all())
    stable = float(np.abs(arr[:, -1] - arr[:, 0]).max())
    ok = convex == 20 and all_positive
    detail = (f"every member of B77's quadratic family has a strictly positive leading "
              f"coefficient on {convex} of 20 drawn families, so **every owner curve is convex "
              f"and the slope rises inside any run of one owner by construction**. The rise is "
              f"positive on all {arr.size} readings, and refining the parameter grid by a "
              f"factor of 256 moves it by at most {stable:.2e} because the `x` grid is fixed "
              f"and runs stay longer than one `x` step. **So the registered object measures the "
              f"`x` grid and not the family**, and this station reads capital per worker along "
              f"the envelope instead, which is what a slope reversal means economically")
    return ok, detail, {"convex_families": convex, "rise_always_positive": all_positive,
                        "largest_move_under_refinement": stable}


def crit_reversal_common(sample):
    """B93-2: reversing on a continuum, counted by degree, and split from the other event."""
    by = sample["by_degree"]
    if not by:
        return None, ("no degree produced a family, so there is nothing to count "
                      "and no object; not evaluated, and it lands in the third "
                      "cell rather than on either verdict"), {}
    counts = {k: v["reversing"] for k, v in by.items()}
    no_ret = {k: v.get("reversing_no_return", 0) for k, v in by.items()}
    tot = {k: v["families"] for k, v in by.items()}
    solo = {k: v.get("one_owner_throughout", 0) for k, v in by.items()}
    anyrise = {k: v.get("rises_anywhere", 0) for k, v in by.items()}
    within = {k: v.get("rises_within_one_owner", 0) for k, v in by.items()}
    # the degree where the two events are most often confused, read off the draws
    worst = max(by, key=lambda k: solo[k] / max(anyrise[k], 1))
    ok = (bool(by) and all(0 < counts[k] < tot[k] for k in by)
          and all(solo[k] > 0 for k in by)
          and all(anyrise[k] >= counts[k] for k in by))
    shown = "; ".join(f"degree {k}: at a change of owner {counts[k]} of {tot[k]} "
                      f"({counts[k] / tot[k]:.1%}), inside one owner's own run {within[k]}, "
                      f"with one owner over the whole sweep {solo[k]}, anywhere {anyrise[k]}"
                      for k in sorted(by))
    detail = (f"capital per worker along the envelope, counted apart: {shown}. **The first "
              f"column is capital reversing, read at the rate where the switch happens**, where "
              f"both members carry one cost and therefore one wage. The others are price "
              f"Wicksell effects on a single owner's own curve, **where no technique is chosen "
              f"differently** and the value of one technique's capital simply moves with the "
              f"rate. **The first version of this station reported the last column under the "
              f"first column's name**, and at degree {worst} {solo[worst]} of {anyrise[worst]} "
              f"of it, {solo[worst] / max(anyrise[worst], 1):.0%}, had one owner from end to "
              f"end. **Neither all nor none at any degree**, so the "
              f"reading is a property of the drawn family. **B92 showed reversing with no owner "
              f"returning anywhere needs three "
              f"techniques**, because the pair meeting on the envelope must not include the one "
              f"owning a zero rate; **a continuum is always in that regime**, and every "
              f"reversal reads between {min(counts[k] / tot[k] for k in by):.1%} and "
              f"{max(counts[k] / tot[k] for k in by):.1%} here, **rising with the degree**. "
              f"**The figure comparable to B92's `12 / 1878` is the no-return one**, since "
              f"that is what B92 counted and two techniques reverse whenever they reswitch "
              f"(`43 / 43` in its own record): it reads between "
              f"{min(no_ret[k] / tot[k] for k in by):.2%} and "
              f"{max(no_ret[k] / tot[k] for k in by):.2%} here against "
              f"{12 / 1878:.2%} there, by degree "
              f"{ {k: no_ret[k] for k in sorted(by)} }")
    return ok, detail, {"counts": counts, "counts_no_return": no_ret, "totals": tot,
                        "one_owner_throughout": solo,
                        "rises_anywhere": anyrise, "rises_within_one_owner": within,
                        "largest": {k: by[k]["largest_rise"] for k in by}}


def crit_reversal_stable(sample):
    """B93-3: and it does not collapse when the parameter grid is refined."""
    per_degree, survivors_total, cohort_total, created_total = {}, 0, 0, 0
    for deg, cohort in sorted(sample["best"].items()):
        survives = collapses = 0
        created = 0
        for entry in cohort:
            lad = entry["ladder"]
            first, last = lad[0]["rise"], lad[-1]["rise"]
            # **Three states, because the registered wording has a presupposition the code did
            # not.** "Still positive and still more than half its coarse value" presupposes the
            # coarse value was positive. The cohort is selected at `THETA_BASE` while the
            # ladder starts below it, so a family can enter with a coarse rise at or under
            # zero; for those, half of it is under any positive number and the second half of
            # the test says nothing, leaving only the selection condition restated. Such a
            # family is one the refinement **created**, which is neither surviving nor
            # collapsing, and it is counted on its own line.
            if first <= TOL:
                created += 1
            elif last > TOL and last > 0.5 * first:
                survives += 1
            else:
                collapses += 1
        per_degree[deg] = {"cohort": len(cohort), "survives": survives,
                           "collapses": collapses, "created_by_refinement": created}
        survivors_total += survives
        created_total += created
        cohort_total += len(cohort)
    ok = cohort_total > 0 and survivors_total > 0
    shown = "; ".join(f"degree {d}: {v['survives']} of {v['cohort']} survive, "
                      f"{v['created_by_refinement']} created by the refinement"
                      for d, v in sorted(per_degree.items()))
    detail = (f"a cohort of up to {COHORT} families per degree **selected on a rise at a change "
              f"of owner**, not on any rise, each taken through a "
              f"parameter ladder from {THETA_LADDER[0]} to {THETA_LADDER[-1]}, a 64-fold "
              f"refinement: {shown}, **{survivors_total} of {cohort_total} in all, with "
              f"{created_total} more that the refinement created rather than preserved**. "
              f"A family counts as surviving when its coarse rise is positive and its fine "
              f"rise is still positive and still more than half of it; a family whose coarse "
              f"rise is not positive is counted on its own line, since for it the second "
              f"half of that test is vacuous and only the selection condition would remain. "
              f"**The cohort is taken in draw order rather than by the "
              f"largest rise**, because selecting the maximiser selects on the statistic and a "
              f"discretisation artefact is exactly what would win that selection. **B77 refined "
              f"one maximiser, saw it collapse, and registered the question as not found; both "
              f"outcomes occur and the survivors are the answer**, since the claim is an "
              f"existence claim")
    return ok, detail, {"per_degree": per_degree, "survivors": survivors_total,
                        "created_by_refinement": created_total,
                        "cohort": cohort_total, "ladder": list(THETA_LADDER)}


def crit_fill_in(sample):
    """B93-4: filling the family in removes B92's two-valued k."""
    rows = sample["fill"]
    grew, flat = [], []
    for row in rows:
        first, last = row[0], row[-1]
        (grew if last["active_set"] > 2 * first["active_set"] else flat).append(
            (first["largest_jump"], last["largest_jump"],
             first["active_set"], last["active_set"]))

    def median_ratio(rs):
        if not rs:
            return float("nan")
        return float(np.median([b / max(a, 1e-15) for a, b, _c, _d in rs]))

    r_grew, r_flat = median_ratio(grew), median_ratio(flat)
    owners_max = max((row[-1]["active_set"] for row in rows), default=0)
    ok = (bool(grew) and bool(flat) and r_grew < 0.5 and r_flat > r_grew
          and owners_max > 0)
    detail = (f"B92 reads `k` as two-valued at a switch, one price system carrying two capital "
              f"values. Filling the family in from {FILL_LADDER[0]} members to "
              f"{FILL_LADDER[-1]} **shrinks the jump where the active set fills in with it and "
              f"leaves it where the active set does not**: on {len(grew)} families whose active "
              f"set more than doubles the jump falls by a median factor of {r_grew:.3f}, and on "
              f"{len(flat)} whose active set stays put it changes by a median factor of "
              f"{r_flat:.3f}. **So the two-valuedness tracks the owners actually used and not "
              f"the members on offer.** The count of members that own the envelope somewhere "
              f"along the sweep runs to {owners_max} at {FILL_LADDER[-1]} members here, so it "
              f"is not bounded: **this is not B77's result and the first version of this "
              f"station cited it as though it were.** B77 bounds the processes running "
              f"together **at one rate** by the number of goods; this counts the members that "
              f"own the envelope **at some rate or another over a sweep**, and the two are "
              f"different objects that move in opposite directions under the same refinement, "
              f"which is B77's Theorem 22(2) in its own words. **The ladder also plateaus at "
              f"this station's `x` grid**, which is a statement about the grid and is printed")
    return ok, detail, {"families": len(rows), "active_set_grew": len(grew),
                        "active_set_flat": len(flat),
                        "median_ratio_when_growing": r_grew,
                        "median_ratio_when_flat": r_flat,
                        "owners_at_widest": owners_max,
                        "x_points": X_POINTS, "ladder": list(FILL_LADDER),
                        "rows": rows[:4]}


def crit_per_good(sample):
    """B93-5: the other index. Attained exactly when the minimiser stays inside the set."""
    inside = sample["per_good"]["interior"]
    outside = sample["per_good"]["open_end"]
    settles = abs(inside[-1]["s"] - inside[-2]["s"]) < 1e-3 and not inside[-1]["at_end"]
    marches = (outside[-1]["s"] < outside[0]["s"] / 10.0 and all(o["at_end"] for o in outside)
               and outside[-1]["cost"] < outside[0]["cost"])
    ok = settles and marches
    detail = (f"on a closed method set the minimising method settles: `s` goes "
              f"{inside[0]['s']:.5f}, {inside[1]['s']:.5f}, {inside[2]['s']:.5f} as the grid is "
              f"refined a hundredfold, interior throughout, and the cost converges to "
              f"{inside[-1]['cost']:.8f}. **On a half-open set whose cost falls toward the "
              f"excluded end it does not**: the minimiser sits at the end point at every "
              f"refinement and marches from {outside[0]['s']:.1e} to {outside[-1]['s']:.1e} "
              f"while the cost keeps falling, {outside[0]['cost']:.7f} to "
              f"{outside[-1]['cost']:.7f}. **That is what non-attainment looks like on a grid**: "
              f"not a minimum in the wrong place, but a minimiser with no limit in the set. "
              f"**So the non-substitution theorem survives a continuum of methods per good "
              f"exactly when the per-good minimum is attained**, and it fails by the infimum "
              f"escaping rather than by two goods wanting different techniques")
    return ok, detail, {"interior": inside, "open_end": outside}


def crit_single_technique(sample):
    """B93-6: an implementation check. Attainment per good gives a single technique."""
    rng = np.random.default_rng(863)
    goods, checked, beaten = 6, 0, 0
    s = np.linspace(0.0, 1.0, 4001)
    for _ in range(40):
        curves = []
        for _g in range(goods):
            shift = float(rng.uniform(0.1, 0.9))
            curves.append(1.05 * (0.2 + 0.6 * (s - shift) ** 2) + (0.9 - 0.5 * s))
        best = np.array([c[int(np.argmin(c))] for c in curves])
        # a technique is one method per good. Draw some and check none beats the per-good
        # choice in any component, which is what "the componentwise minimum is attained by a
        # single technique" says and what a broken independence would fail
        for _try in range(200):
            pick = rng.integers(0, len(s), goods)
            got = np.array([curves[g][pick[g]] for g in range(goods)])
            if (got < best - 1e-12).any():
                beaten += 1
        checked += 1
    worst = float(beaten)
    floors_ok = True
    direction_bad = 0
    for deg in DEGREES:
        for _ in range(10):
            co = rng.uniform(-1.0, 1.0, (deg + 1, 4))
            coef = coefficients(co, 200)
            floors_ok = floors_ok and bool(coef.min() >= FLOOR - 1e-15)
            # `C(theta, 1)` is total labour, so the owner at the lowest rate is the member with
            # the least of it. B92 learned this the same way: an envelope read upside down
            # still hands back readings of the right shape, and nothing else notices
            # at `x` just above one, not at this station's grid start of 1.02: the owner can
            # already have changed by there, and the fact being checked is about `x = 1`
            idx, _c, _k = envelope(coef, np.array([1.0 + 1e-9]))
            direction_bad += int(idx[0] != int(np.argmin(coef.sum(axis=0))))
    ok = checked == 40 and floors_ok and beaten == 0 and direction_bad == 0
    detail = (f"choosing the cheapest method for each of {goods} goods independently gives one "
              f"technique that attains the componentwise minimum: {checked * 200} drawn "
              f"techniques over {checked} method sets beat it in some component {beaten} "
              f"times. **This is an implementation check and not a reading** (`D35` "
              f"second clause): B86's Theorem 30(2) argument is per good and says nothing about "
              f"how many methods each good has, so a continuum changes nothing here as long as "
              f"each per-good minimum exists. **And every coefficient of every drawn profile "
              f"stays at or above {FLOOR}**, so each member is a real dated-labour profile "
              f"rather than one with a negative labour input at some date. **And the envelope "
              f"is checked to run the right way up**: the member owning the lowest rate is the "
              f"one with the least total labour, since `C(theta, 1)` is that labour, with "
              f"{direction_bad} exceptions over {len(DEGREES) * 10} families")
    return ok, detail, {"goods": goods, "checked": checked,
                        "coefficient_floor_holds": floors_ok,
                        "envelope_direction_bad": direction_bad}


def crit_return(sample):
    """B93-8: a technique still leaves the envelope and comes back when the labels are dense."""
    ret = sample.get("returns", {})
    ex = sample.get("return_example", {})
    best, ladder = ex.get("best"), ex.get("ladder") or []
    wide = sum(v.get("wide", 0) for v in ret.values())
    anyr = sum(v.get("any", 0) for v in ret.values())
    tot = sum(v.get("families", 0) for v in ret.values())
    held = [l for l in ladder
            if l["span"] >= RETURN_SPAN * l["members"] and l["margin"] > RETURN_MARGIN]
    ok = (tot > 0 and wide > 0 and best is not None and len(ladder) >= 3
          and len(held) == len(ladder) and anyr >= wide)
    if best is None or not ladder:
        return False, ("no drawn family carried a member that leaves the envelope and comes "
                       "back, so there is no return to follow through the ladder"), {
            "wide": wide, "any": anyr, "families": tot, "by_degree": ret}
    shown = ", ".join(f"{l['members']} members: span {l['span']}, lead {l['margin']:.2e}"
                      for l in ladder)
    detail = (f"compressing the owner sequence and looking for a member that leaves the "
              f"envelope and comes back: **{wide} of {tot} drawn families carry one that "
              f"crosses at least {RETURN_SPAN:.0%} of the family and leads by more than "
              f"{RETURN_MARGIN:.0e} at both spells**, against {anyr} that carry one at any "
              f"width. **The width and the lead are both needed**: adjacent members of a dense "
              f"family are nearly the same profile, so the argmin wobbles between neighbours at "
              f"around `1e-8`, and those wobbles are the thing a continuum really does dissolve. "
              f"The widest one found owns the envelope, loses it to member "
              f"{best['sequence'][1] if best and len(best['sequence']) > 1 else '?'} and takes "
              f"it back, crossing {best['span']} of {best['members']} members with a lead of "
              f"{best['margin']:.2e}, and **it survives the refinement ladder**: {shown}. "
              f"**So technique return is defined on a continuum and it happens.** The question "
              f"it becomes is whether the minimiser over the index is monotone in the rate, and "
              f"here it is not")
    return ok, detail, {"wide": wide, "any": anyr, "families": tot,
                        "by_degree": ret, "example": best, "ladder": ladder}


def crit_bracket_census(sample):
    """B93-9: how many grid brackets held more than one change of owner, and that they are out.

    A bracket is two adjacent grid rates whose owners differ. **It can hold more than one
    change**, and then bisecting the pair returns a rate at which neither of them is chosen and
    any capital jump read there is read between two techniques that are not adjacent on the
    envelope. Those brackets are named and dropped rather than resolved, because resolving one
    costs a fresh envelope over up to `n_theta` members. This criterion reports how many there
    were and checks that the drop actually happened: the on-envelope count plus the dropped
    count has to be the whole count, on every degree.
    """
    tot = on_env = 0
    per = {}
    for deg, v in sorted(sample["by_degree"].items()):
        t, o = v.get("owner_changes", 0), v.get("owner_changes_on_envelope", 0)
        if t < o or o < 0:
            return False, (f"degree {deg} reports {o} changes on the envelope out of {t}, "
                           f"which is not a subset"), {"by_degree": per}
        per[deg] = {"changes": t, "on_envelope": o, "merged": t - o,
                    "merged_share": (t - o) / t if t else 0.0}
        tot += t
        on_env += o
    ok = tot > 0 and on_env <= tot
    shown = "; ".join(f"degree {d}: {v['merged']} of {v['changes']} ({v['merged_share']:.2%})"
                      for d, v in sorted(per.items()))
    detail = (f"**{tot - on_env} of {tot} brackets held more than one change of owner "
              f"({(tot - on_env) / tot:.2%} over {len(per)} degrees)** and are dropped from "
              f"every reading that needs a switch rate: {shown}. The grid is {X_POINTS} points "
              f"over [{X_LO}, {X_HI}], so a bracket is about {(X_HI - X_LO) / X_POINTS:.4f} "
              f"wide, and a continuum of {THETA_BASE} members owning short runs inside one is "
              f"ordinary rather than rare. **The published form of this station bisected every "
              f"bracket as if it held one change**, which returns a rate at which neither "
              f"member is chosen and overstates the jump there; excluding them sharpened "
              f"B93-4's growing group by an order of magnitude and changed B93-3's cohort")
    return ok, detail, {"by_degree": per, "changes": tot, "on_envelope": on_env,
                        "merged": tot - on_env, "x_points": X_POINTS}


def crit_registration():
    """B93-7: the same round writes back to the three stations this one answers or corrects."""
    want = ["b77_continuum.md", "b86_non_substitution.md", "b92_capital_reversing.md"]  # D20
    missing = [f for f in want
               if "b93_continuum_second_pass.md" not in
               (ROOT / "docs" / f).read_text(encoding="utf-8")]
    ok = not missing
    detail = (f"the stations this one answers or corrects "
              f"{'each name it' if ok else '**do not all name it: ' + ', '.join(missing) + '**'}: "
              f"B77 for the reformulated registration, B86 for the other index, and B92 for "
              f"what a continuum does to its two readings. `D20`")
    return ok, detail, {"missing_writebacks": missing}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    sample = draws(np.random.default_rng(6), 250)
    if not sample["fill"] or not sample["by_degree"]:
        fails.append("the fixture drew nothing")

    named = (("B93-1", crit_registered_form), ("B93-2", crit_reversal_common),
             ("B93-3", crit_reversal_stable), ("B93-4", crit_fill_in),
             ("B93-5", crit_per_good), ("B93-6", crit_single_technique),
             ("B93-8", crit_return), ("B93-9", crit_bracket_census))
    empty = {"by_degree": {}, "best": {}, "fill": [], "per_good": sample["per_good"],
             "returns": {}, "return_example": {}}
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:140]}")
        # B93-1, B93-5 and B93-6 build their own objects rather than reading the sample
        if name in ("B93-2", "B93-3", "B93-4", "B93-8") and fn(empty)[0]:
            fails.append(f"{name} passes on an empty sample")

    # B93-2: all or none at a degree would make it a property of the construction
    for label, bend in (("all", lambda v: v["families"]), ("none", lambda _v: 0)):
        b = {"by_degree": {k: dict(v, reversing=bend(v))
                           for k, v in sample["by_degree"].items()},
             "best": sample["best"], "fill": sample["fill"], "per_good": sample["per_good"]}
        if crit_reversal_common(b)[0]:
            fails.append(f"B93-2 passes when {label} of the families reverse")

    # B93-2: the split is the whole point, so a fixture in which nothing is a price Wicksell
    # effect leaves the station with no contrast to report, and one where the third column is
    # smaller than the first is arithmetically impossible and has to be rejected
    for label, bend in (
            ("no family has one owner throughout", lambda v: dict(v, one_owner_throughout=0)),
            ("fewer families rise anywhere than rise at a change",
             lambda v: dict(v, rises_anywhere=0))):
        b = dict(sample, by_degree={k: bend(v) for k, v in sample["by_degree"].items()})
        if crit_reversal_common(b)[0]:
            fails.append(f"B93-2 passes when {label}")

    # B93-8: a return that does not survive refinement is a tie, and a fixture with none has
    # nothing to report
    for label, bent in (
            ("the widest return collapses under refinement",
             dict(sample.get("return_example", {}),
                  ladder=[dict(l, margin=(l["margin"] if i == 0 else 0.0))
                          for i, l in enumerate(sample.get("return_example", {}).get("ladder", []))])),
            ("no family carries a wide return", None)):
        if bent is None:
            b = dict(sample, returns={k: dict(v, wide=0) for k, v in sample["returns"].items()})
        else:
            b = dict(sample, return_example=bent)
        if crit_return(b)[0]:
            fails.append(f"B93-8 passes when {label}")

    # B93-3: if every cohort member collapsed there would be no witness, and if none did the
    # criterion would be reporting a construction rather than a search
    b = {"by_degree": sample["by_degree"], "fill": sample["fill"],
         "per_good": sample["per_good"],
         "best": {d: [{"ladder": [dict(e, rise=(e["rise"] if i == 0 else -abs(e["rise"])))
                                  for i, e in enumerate(c["ladder"])]}
                      for c in coh]
                  for d, coh in sample["best"].items()}}
    if crit_reversal_stable(b)[0]:
        fails.append("B93-3 passes when every family in the cohort collapses")

    # B93-4: the reading is that the jump tracks the active set, so a fixture in which it
    # shrinks regardless has to be rejected
    bent = []
    # **The target is the growing group's own measured ratio, not a constant.** A constant is
    # calibrated against the reading of the day it was written: this one was `0.02` against a
    # growing ratio near `0.03`, and when excluding merged brackets sharpened that ratio by an
    # order of magnitude the mutation stopped being a mutation while still looking like one.
    # A test whose strength depends on a number baked into it is silent exactly when the thing
    # it tests improves.
    grew_ratios = [r[-1]["largest_jump"] / max(r[0]["largest_jump"], 1e-15)
                   for r in sample["fill"] if r[-1]["active_set"] > 2 * r[0]["active_set"]]
    target = float(np.median(grew_ratios)) if grew_ratios else 0.02
    for row in sample["fill"]:
        if row[-1]["active_set"] > 2 * row[0]["active_set"]:
            bent.append(row)                       # leave the growing group alone
        else:
            ratio = row[-1]["largest_jump"] / max(row[0]["largest_jump"], 1e-15)
            bent.append([dict(e, largest_jump=e["largest_jump"] * (target / max(ratio, 1e-15)
                                                                   if i == len(row) - 1 else 1.0))
                         for i, e in enumerate(row)])
    b = {"by_degree": sample["by_degree"], "best": sample["best"],
         "per_good": sample["per_good"], "fill": bent}
    if crit_fill_in(b)[0]:
        fails.append("B93-4 passes when the flat group shrinks as much as the growing one")

    # B93-5: a closed set whose minimiser ran to an end point would be the other case, and a
    # half-open one whose minimiser settled would be this one
    swapped = {"by_degree": sample["by_degree"], "best": sample["best"], "fill": sample["fill"],
               "per_good": {"interior": sample["per_good"]["open_end"],
                            "open_end": sample["per_good"]["interior"]}}
    if crit_per_good(swapped)[0]:
        fails.append("B93-5 passes with the two method sets exchanged")

    # B93-1: a family of concave owners would make the registered object non-automatic, and
    # the criterion has to be reading convexity rather than asserting it
    # B93-9: a census that says more brackets are on the envelope than exist is a wiring error
    bent = {**sample, "by_degree": {k: dict(v, owner_changes_on_envelope=v["owner_changes"] + 1)
                                    for k, v in sample["by_degree"].items()}}
    if crit_bracket_census(bent)[0]:
        fails.append("B93-9 passes when more brackets are on the envelope than there are")

    th = np.linspace(0.0, 1.0, 400)
    _a, _b, c = B77.coefficient_curves(np.zeros((3, 4)), th)
    if c.min() <= 0.0:
        fails.append("B77's leading coefficient is not strictly positive on the zero family")

    for f in fails:
        print("FAIL", f)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


# ------------------------------------------------- main

def _crit(name, kind, ok, detail):
    """One criterion, with its third cell kept out of the two verdicts.

    A branch that finds no object to read returns None rather than False.
    Writing it as False would put it on the ledger as a reading that came out
    false, which the rule about the undecided cell forbids, and the census that
    counts failures reads a `void` field as well as the prose.
    """
    crit = {"name": name, "kind": kind, "detail": detail,
            "passed": None if ok is None else bool(ok)}
    if ok is None:
        crit["void"] = True
    return crit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--families", type=int, default=N_FAMILIES)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(args.seed)
    sample = draws(rng, args.families)
    print(f"{args.families} families per degree at {DEGREES}, "
          f"{len(sample['fill'])} fill-in families\n")

    criteria, report = [], {}
    for name, kind, fn in (("B93-1", "known_answer", crit_registered_form),
                           ("B93-2", "own_reading", crit_reversal_common),
                           ("B93-3", "own_reading", crit_reversal_stable),
                           ("B93-4", "own_reading", crit_fill_in),
                           ("B93-5", "own_reading", crit_per_good),
                           ("B93-6", "instrument", crit_single_technique),
                           ("B93-8", "own_reading", crit_return),
                           ("B93-9", "instrument", crit_bracket_census)):
        ok, detail, rep = fn(sample)
        criteria.append(_crit(name, kind, ok, detail))
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append(_crit("B93-7", "bookkeeping", ok, detail))
    report["B93-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B93-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B93",
        "config": {"seed": args.seed, "families": args.families, "degrees": list(DEGREES),
                   "theta_base": THETA_BASE, "theta_ladder": list(THETA_LADDER),
                   "cohort": COHORT, "fill_ladder": list(FILL_LADDER),
                   "x_range": [X_LO, X_HI], "x_points": X_POINTS, "floor": FLOOR,
                   "imports": "b77_continuum"},
        "report": report,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    # An undecided cell is not a failure, so it does not set the exit code.
    bad = [c["name"] for c in criteria if c["passed"] is False]
    held = [c["name"] for c in criteria if c["passed"] is None]
    if held:
        print("no object, third cell: " + ", ".join(held))
    print(f"all {len(criteria)} criteria pass; record written" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
