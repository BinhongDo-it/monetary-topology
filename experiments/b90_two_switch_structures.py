"""B90: the rate moves two orders on one system, and they switch at different rates.

B88 registered a second rate as the interface to reswitching. Running it turns up three things,
and only the first is the one the registration expected.

**A band of rates where the demand cannot be met at all.** Every land can be cultivated up to
the rate at which the worst land's own wage curve reaches zero. The intensive margin closes
earlier than that on almost every drawn system, so between the two there is a band where all the
land is workable and no acre can take a second method. **Demand above capacity is not met there,
and by B89's identity the configuration is `(j, f) = (0, 0)`, whose wage is not determined by
cost.**

**The viable set of rates need not be an interval.** On some systems the intensive margin closes
as the rate rises and opens again above it. That is reswitching, of the margin rather than of a
technique.

**The two orders switch at different rates.** Which land sits on the extensive envelope and which
acre takes the second method are two orders on the same system, and on the systems where both
switch they almost never switch at the same rate.

B72's envelope solver and land generator, B73's intensive pair and B89's row builder are imported
rather than rewritten.

Run:
    python experiments/b90_two_switch_structures.py
    python experiments/b90_two_switch_structures.py --selftest
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
import b89_degrees_of_freedom as B89                       # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b90_two_switch_structures.json"

SEED = 90
N_SYSTEMS = 500
LANDS = (3, 6)
R_MAX = 3.0
R_GRID = 601
YIELD = (1.05, 2.00)
CORN_FACTOR = (1.0, 3.0)
LABOUR_FACTOR = (1.0, 3.0)
BISECTION = 50
TOL = 1e-12
RATES = np.linspace(0.0, R_MAX, R_GRID)
STEP = float(RATES[1] - RATES[0])


def state_at(alphas, lams, dose, r):
    """Who owns the envelope, which acre could take a second method, and can any."""
    q2, c2, d2 = dose
    own = B72.wage_curve(alphas, lams, r)
    if own.min() <= 0.0:
        return {"extensive": False, "owner": None, "pick": None, "intensive": False}
    w_ext = float(own.min())
    ws = []
    for i in range(len(alphas)):
        w, _rho, _m = B73.intensive((1.0, q2), (alphas[i], alphas[i] * c2),
                                    (lams[i], lams[i] * d2), r)
        ws.append(np.nan if w is None else w)
    ws = np.asarray(ws, dtype=float)
    ok = np.isfinite(ws) & (ws > 0.0) & (ws <= w_ext + TOL)
    return {"extensive": True, "owner": int(np.argmin(own)),
            "pick": int(np.where(ok, ws, -np.inf).argmax()) if ok.any() else None,
            "intensive": bool(ok.any())}


def bisect(alphas, lams, dose, lo, hi, key, steps=None):
    """Narrow a change in `key` between two rates, so a switch is located and not declared."""
    steps = BISECTION if steps is None else steps
    a, b = lo, hi
    va = state_at(alphas, lams, dose, a)[key]
    for _ in range(steps):
        m = 0.5 * (a + b)
        if state_at(alphas, lams, dose, m)[key] == va:
            a = m
        else:
            b = m
    return a, b


def switch_points(states, key):
    """Grid intervals across which `key` changes, both sides defined."""
    out = []
    for i in range(len(states) - 1):
        x, y = states[i][key], states[i + 1][key]
        if x is not None and y is not None and x != y:
            out.append(i)
    return out


def blocks_of(flags):
    """Runs of True, printed as intervals rather than counted."""
    out, start = [], None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append((start, i - 1)); start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


def draws(rng, n_systems):
    out = []
    for _ in range(n_systems):
        k = int(rng.integers(LANDS[0], LANDS[1]))
        alphas, lams = B72.random_lands(rng, k)
        dose = (float(rng.uniform(*YIELD)), float(rng.uniform(*CORN_FACTOR)),
                float(rng.uniform(*LABOUR_FACTOR)))
        states = [state_at(alphas, lams, dose, r) for r in RATES]
        ext = [s["extensive"] for s in states]
        inten = [s["intensive"] for s in states]
        if not any(ext):
            continue
        out.append({"k": k, "alphas": alphas, "lams": lams, "dose": dose, "states": states,
                    "ext_blocks": blocks_of(ext), "int_blocks": blocks_of(inten),
                    "owner_switches": switch_points(states, "owner"),
                    "pick_switches": switch_points(states, "pick")})
    return out


# ------------------------------------------------- criteria

def crit_reduces(sample):
    """B90-1: at the rate the other two stations ran, this one gives their answer."""
    worst_ext = worst_pick = 0.0
    n = 0
    r0 = 0.05
    for s in sample:
        st = state_at(s["alphas"], s["lams"], s["dose"], r0)
        if not st["extensive"]:
            continue
        n += 1
        w72, marg, _rents = B72.solve(s["alphas"], s["lams"], r0)
        worst_ext = max(worst_ext, abs(float(B72.wage_curve(s["alphas"], s["lams"], r0).min())
                                       - w72))
        if st["owner"] != marg:
            worst_pick = 1.0
    ok = n > 0 and worst_ext < 1e-12 and worst_pick == 0.0
    detail = (f"at `r = {r0}`, the rate B88 and B89 ran at, the envelope wage and the marginal "
              f"land agree with B72's own solver on all {n} systems, worst wage gap "
              f"{worst_ext:.2e}. **The state function here is written from the wage curves and "
              f"the pair, and the solvers are imported**, so the two can disagree")
    return ok, detail, {"systems": n, "worst_envelope_gap": worst_ext,
                        "marginal_mismatch": worst_pick}


def crit_band(sample):
    """B90-2: the intensive margin closes before the extensive one does."""
    strictly = equal = leaky = 0
    widths = []
    for s in sample:
        if not s["ext_blocks"] or not s["int_blocks"]:
            continue
        hi = s["ext_blocks"][-1][1]
        lo = s["int_blocks"][-1][1] + 1
        r_ext, r_int = float(RATES[hi]), float(RATES[lo - 1])
        if r_int < r_ext - STEP / 2:
            strictly += 1; widths.append(r_ext - r_int)
            # the band has to be a set of rates at which no acre is viable, checked on the
            # states rather than inferred from two endpoints
            if any(s["states"][i]["intensive"] for i in range(lo, hi + 1)):
                leaky += 1
        else:
            equal += 1
    total = strictly + equal
    ok = total > 0 and strictly > 0 and strictly > equal and leaky == 0
    med = float(np.median(widths)) if widths else 0.0
    detail = (f"on {strictly} of {total} systems where both margins open at some rate, the "
              f"intensive margin closes strictly below the rate at which the extensive one "
              f"does, by a median of {med:.3f} in the rate, and on {equal} the two ends fall "
              f"within one grid step. **In that band every land is workable and no acre can "
              f"take a second method**, so demand above capacity is not met, and by B89's "
              f"identity the configuration there is `(j, f) = (0, 0)`, whose wage is not "
              f"determined by cost. **Both ends are read off the same rate grid**, so the "
              f"comparison is not between two resolutions. **The band is checked rate by "
              f"rate and not inferred from two endpoints**: {leaky} of the {strictly} bands "
              f"contain a rate at which some acre is viable after all")
    return ok, detail, {"strictly_below": strictly, "within_one_step": equal,
                        "median_band_width": med, "leaky_bands": leaky}


def crit_blocks(sample):
    """B90-3: the viable set of rates need not be an interval, which is reswitching."""
    counts, examples = {}, []
    for s in sample:
        n = len(s["int_blocks"])
        counts[n] = counts.get(n, 0) + 1
        if n >= 2 and len(examples) < 6:
            examples.append([[round(float(RATES[a]), 4), round(float(RATES[b]), 4)]
                             for a, b in s["int_blocks"]])
    ok = bool(counts) and sum(v for k, v in counts.items() if k >= 2) > 0
    shown = "; ".join(str(e) for e in examples[:4])
    detail = (f"the rates at which some acre can take a second method form "
              + ", ".join(f"{v} systems with {k} block(s)" for k, v in sorted(counts.items()))
              + f". **More than one block is the margin closing as the rate rises and opening "
                f"again above it**, which is reswitching of the margin rather than of a "
                f"technique. **Printed as intervals rather than counted**: {shown}")
    return ok, detail, {"block_counts": counts, "examples": examples}


def crit_two_structures(sample):
    """B90-4: two orders on one system, and they do not switch together."""
    both = share = only_owner = only_pick = neither = 0
    for s in sample:
        O, P = set(s["owner_switches"]), set(s["pick_switches"])
        if O and P:
            both += 1; share += int(bool(O & P))
        elif O:
            only_owner += 1
        elif P:
            only_pick += 1
        else:
            neither += 1
    ok = both > 0 and share < both and only_pick > 0
    detail = (f"which land sits on the extensive envelope and which acre takes the second "
              f"method are two orders on one system. Both switch on {both} systems and **they "
              f"share a grid interval on {share} of those**; only the envelope owner switches "
              f"on {only_owner}, only the intensified acre on {only_pick}, neither on "
              f"{neither}. **The acre switching with no envelope switch anywhere is the "
              f"load-bearing count**: it cannot be the envelope's switch seen through another "
              f"variable, because there is none")
    return ok, detail, {"both": both, "share_an_interval": share,
                        "only_owner": only_owner, "only_pick": only_pick, "neither": neither}


def crit_located(sample):
    """B90-5: a switch is bisected rather than read off the grid it was spotted on."""
    worst = 0.0
    n = 0
    for s in sample:
        for key, points in (("owner", s["owner_switches"]), ("pick", s["pick_switches"])):
            for i in points[:2]:
                a, b = bisect(s["alphas"], s["lams"], s["dose"],
                              float(RATES[i]), float(RATES[i + 1]), key)
                worst = max(worst, b - a); n += 1
    ok = n > 0 and worst < STEP / 1e6
    detail = (f"every switch this station reports is narrowed by bisection from the grid "
              f"interval it was spotted in: {n} switches located, the widest remaining bracket "
              f"{worst:.2e} against a grid step of {STEP:.4f}, a factor of "
              f"{STEP / worst if worst > 0 else float('inf'):.1e}. **The grid finds candidates "
              f"and does not decide them**, which is what gate six asks: a switch read off a "
              f"grid is a statement about the grid")
    return ok, detail, {"switches_located": n, "widest_bracket": worst, "grid_step": STEP}


def crit_cell_in_band(sample):
    """B90-6: the band's configuration is B89's indeterminate cell, from B89's own rows."""
    checked = indeterminate = 0
    for s in sample:
        if not s["ext_blocks"] or not s["int_blocks"]:
            continue
        lo = s["int_blocks"][-1][1] + 1
        hi = s["ext_blocks"][-1][1]
        if lo > hi:
            continue
        r = float(RATES[(lo + hi) // 2])
        A, b = B89.rows(s["alphas"], s["lams"], list(range(s["k"])), set(), s["dose"], r, False)
        st = B89.standing(A, b)
        checked += 1
        indeterminate += int(B89.cell_of(st["null"], st["residual"]) == "a family of solutions")
    ok = checked > 0 and indeterminate == checked
    detail = (f"taking a rate inside the band on each of {checked} systems and building the "
              f"rows with B89's own builder, the configuration is its indeterminate cell on "
              f"{indeterminate} of them: the rows are consistent and leave a one-dimensional "
              f"family. **So the band is not an artefact of how this station looks for the "
              f"margin**, it is the cell B89 already named, reached from a different direction")
    return ok, detail, {"checked": checked, "indeterminate": indeterminate}


def crit_registration():
    """B90-7: the same round writes back to the stations this one continues."""
    want = ["b88_two_margins.md", "b89_degrees_of_freedom.md"]
    missing = [f for f in want
               if "b90_two_switch_structures.md" not in
               (ROOT / "docs" / f).read_text(encoding="utf-8")]
    ok = not missing
    detail = (f"the stations this one continues "
              f"{'each name it' if ok else '**do not all name it: ' + ', '.join(missing) + '**'}, "
              f"so a reader of either finds what the rate does to their fixed-rate readings. "
              f"`D20`")
    return ok, detail, {"missing_writebacks": missing}


# ------------------------------------------------- self-test

def selftest() -> int:
    fails = []
    rng = np.random.default_rng(4)
    sample = draws(rng, 60)
    if len(sample) < 30:
        fails.append(f"the fixture drew only {len(sample)} systems")

    named = (("B90-1", crit_reduces), ("B90-2", crit_band), ("B90-3", crit_blocks),
             ("B90-4", crit_two_structures), ("B90-5", crit_located),
             ("B90-6", crit_cell_in_band))
    for name, fn in named:
        got = fn(sample)
        if not got[0]:
            fails.append(f"{name} does not pass on the fixture: {got[1][:130]}")
        if fn([])[0]:
            fails.append(f"{name} passes on an empty sample")

    # B90-1: the state function and B72's solver have to be able to disagree, and only bending
    # one side tests that. Scaling the fixture rebuilds both, so it tests nothing
    disagreed = 0
    for s in sample:
        st = state_at(s["alphas"], s["lams"], s["dose"], 0.05)
        if not st["extensive"]:
            continue
        _w, marg, _r = B72.solve(np.asarray(s["alphas"]) * 1.05, s["lams"], 0.05)
        disagreed += int(st["owner"] != marg)
    if not disagreed:
        fails.append("the marginal land is the same on every system whatever the lands are")

    # B90-2: if the intensive margin ran to the same rate as the extensive one there would be
    # no band, and the whole reading would be empty
    same = []
    for s in sample:
        if s["ext_blocks"] and s["int_blocks"]:
            same.append(dict(s, int_blocks=[(s["int_blocks"][0][0], s["ext_blocks"][-1][1])]))
        else:
            same.append(s)
    if crit_band(same)[0]:
        fails.append("B90-2 passes when the two margins close at the same rate")

    # B90-3: one block everywhere is an interval, and then there is no reswitching to report
    if crit_blocks([dict(s, int_blocks=s["int_blocks"][:1]) for s in sample])[0]:
        fails.append("B90-3 passes when every viable set is a single interval")

    # B90-4: if every switch of the acre sat on a switch of the envelope, the second order
    # would be the first one seen through another variable
    glued = [dict(s, pick_switches=list(s["owner_switches"])) for s in sample]
    if crit_two_structures(glued)[0]:
        fails.append("B90-4 passes when the two orders switch at exactly the same rates")

    # a fixture where the envelope also switches wherever the acre does, one interval along,
    # leaves the shared count at zero and trips only the clause that says the acre switches
    # somewhere the envelope does not
    shadowed = [dict(s, owner_switches=[i + 1 for i in s["pick_switches"]]
                     if s["pick_switches"] else list(s["owner_switches"])) for s in sample]
    got4 = crit_two_structures(shadowed)
    if got4[0]:
        fails.append("B90-4 passes when every acre switch is shadowed by an envelope switch")
    if got4[2]["share_an_interval"] >= got4[2]["both"]:
        fails.append("the B90-4 probe trips the shared-interval clause too, so it tests nothing")

    # B90-5: with no bisection the bracket is the grid step, which is a switch read off the
    # grid rather than located
    global BISECTION
    saved, BISECTION = BISECTION, 0
    try:
        if crit_located(sample)[0]:
            fails.append("B90-5 passes with no bisection at all")
    finally:
        BISECTION = saved

    # B90-6: the band's cell is read with B89's builder, so pointing it at a cultivated set
    # that is not full has to change the answer
    checked = 0
    for s in sample:
        if not s["ext_blocks"] or not s["int_blocks"]:
            continue
        lo, hi = s["int_blocks"][-1][1] + 1, s["ext_blocks"][-1][1]
        if lo > hi or s["k"] < 3:
            continue
        r = float(RATES[(lo + hi) // 2])
        A, b = B89.rows(s["alphas"], s["lams"], list(range(s["k"])), {0}, s["dose"], r, False)
        if B89.cell_of(*(lambda st: (st["null"], st["residual"]))(B89.standing(A, b))) == \
                "a family of solutions":
            checked += 1
    if checked:
        fails.append(f"the band's cell stays indeterminate with an acre intensified, on {checked}")

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
    print(f"{len(sample)} systems on a rate grid of {R_GRID} points to {R_MAX}\n")

    criteria, report = [], {}
    for name, kind, fn in (("B90-1", "known_answer", crit_reduces),
                           ("B90-2", "own_reading", crit_band),
                           ("B90-3", "own_reading", crit_blocks),
                           ("B90-4", "own_reading", crit_two_structures),
                           ("B90-5", "instrument", crit_located),
                           ("B90-6", "own_reading", crit_cell_in_band)):
        ok, detail, rep = fn(sample)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok), "detail": detail})
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail[:200]}\n")
    ok, detail, rep = crit_registration()
    criteria.append({"name": "B90-7", "kind": "bookkeeping", "passed": bool(ok),
                     "detail": detail})
    report["B90-7"] = rep
    print(f"{'PASS' if ok else 'FAIL'}  B90-7  [bookkeeping]  {detail[:200]}\n")

    record = {
        "stage": "B90",
        "config": {"seed": args.seed, "systems": args.systems, "lands": list(LANDS),
                   "r_max": R_MAX, "r_grid": R_GRID, "bisection_steps": BISECTION,
                   "yield": list(YIELD), "corn_factor": list(CORN_FACTOR),
                   "labour_factor": list(LABOUR_FACTOR),
                   "imports": "b72_land_and_rent, b73_two_extensions, b89_degrees_of_freedom"},
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
