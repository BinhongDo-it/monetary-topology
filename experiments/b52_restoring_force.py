"""B52 second arm: the readable form of D48's fourth shape, run on the panel.

**What was registered and not done.** D48 says the fourth shape, "there is no
restoring force here", is itself a prediction. The class square's sign sits in that
shape: the counting law counts how many class values a programme writes and says
nothing about their order, so the framework has no reason to pin that sign. The
register then says what is missing: **"no restoring force" has to be separable from
"a restoring force we failed to see", and that reading had not been written.**

**The first version of this file wrote the null at one half and its own self-check
killed it.** With no restoring force, where a series sits looks like it carries no
information about its next move, so one half looks structural. It is not. The
centre a deviation is measured against is the series' own median, estimated from
the same realised path, and **a pure random walk put through this pipeline reads
0.7031 back** at a floor of 0.0727. The pull toward a sample-estimated centre is
mechanical and it is large. Every reading against one half was that artefact.

**So the null is measured rather than asserted**, which is what this repository
does everywhere else it needs a floor. Random walks matched to each country's own
length and step scale go through the identical pipeline, and their distribution of
the proportion is the null. The half-life ladder is built the same way: an AR(1)
with a planted half-life, matched the same way, run through the same code.

**Nothing is fitted and no line sits on an estimate.** Every quantity here is a
proportion produced by one procedure, and what it is compared against is the same
procedure on a series with no restoring force in it.

    python experiments/b52_restoring_force.py
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b52_europe_class_square.json"
OUT = ROOT / "results" / "b52_restoring_force.json"

BASE = "I_TAX"
Z90 = 1.6448536269514722
TERCILE = 2.0 / 3.0
HALF_LIVES = (1, 2, 4, 8, 16, 32, 64)
NSIM = 200            # each simulation is 33 short series; the whole file is milliseconds
SEED = 42


def median(xs):
    s = sorted(xs)
    n = len(s)
    return None if not n else (s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2]))


def quantile(xs, q):
    s = sorted(xs)
    if not s:
        return None
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def sd(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def reversion(series):
    """series: {unit: [values in order]}. One proportion, plus the counts."""
    back = away = 0
    large = []
    per_unit = {}
    for unit, pts in sorted(series.items()):
        if len(pts) < 4:
            per_unit[unit] = {"points": len(pts), "used": 0, "note": "too short to read"}
            continue
        m = median(pts)
        cut = quantile([abs(p - m) for p in pts], TERCILE)
        b = a = 0
        for i in range(len(pts) - 1):
            d = pts[i] - m
            if abs(d) < cut:
                continue
            step = pts[i + 1] - pts[i]
            if step == 0:
                continue
            large.append(abs(d))
            if step * d < 0:
                b += 1
            else:
                a += 1
        back += b
        away += a
        per_unit[unit] = {"points": len(pts), "used": b + a, "back": b, "away": a}
    n = back + away
    return {
        "back": back,
        "away": away,
        "n": n,
        "proportion_back": (back / n) if n else None,
        "median_large_deviation": median(large),
        "per_unit": per_unit,
    }


def simulate(shape, rng, phi):
    """shape: {unit: (length, step_sd)}. phi = 1.0 is a random walk."""
    out = {}
    for unit, (ln, s) in shape.items():
        x, pts = 0.0, []
        for _ in range(ln):
            x = phi * x + rng.gauss(0.0, s if s > 0 else 1.0)
            pts.append(x)
        out[unit] = pts
    return out


def shuffled_diff_null(series, nsim, seed):
    """Keep each country's own step distribution and destroy its order.

    The Gaussian walk assumes the steps are Gaussian and independent. If the real
    steps are fat-tailed or negatively autocorrelated, that alone produces reversion
    and the Gaussian null would understate the artefact. This null borrows the real
    steps and shuffles them, so it carries the step distribution and carries no order.
    """
    rng = random.Random(seed)
    diffs = {k: [v[i + 1] - v[i] for i in range(len(v) - 1)] for k, v in series.items()}
    ps = []
    for _ in range(nsim):
        sim = {}
        for k, d in diffs.items():
            dd = d[:]
            rng.shuffle(dd)
            x, pts = 0.0, []
            for step in dd:
                x += step
                pts.append(x)
            sim[k] = pts
        r = reversion(sim)
        if r["proportion_back"] is not None:
            ps.append(r["proportion_back"])
    return {
        "sims": len(ps),
        "mean": sum(ps) / len(ps),
        "sd": sd(ps),
        "p05": quantile(ps, 0.05),
        "p95": quantile(ps, 0.95),
    }


def acf1(x):
    n = len(x)
    if n < 3:
        return None
    m = sum(x) / n
    den = sum((v - m) ** 2 for v in x)
    if den <= 0:
        return None
    return sum((x[i] - m) * (x[i + 1] - m) for i in range(n - 1)) / den


def block_bootstrap_null(series, block, nsim, seed, phi=1.0):
    """Resample each unit's differences in circular blocks, then integrate.

    The shuffled null keeps the step distribution and destroys the step ORDER, so it
    removes any autocorrelation the real steps carry. Negative autocorrelation in the
    steps produces reversion in the level on its own, and averaging or measurement
    error in a semi-annual series is exactly where it comes from. Measured on this
    panel the differences carry a median lag-one autocorrelation of about -0.20, with
    25 of 33 countries negative, so this is not a hypothetical.

    Blocks keep that local structure and still integrate to a level with no restoring
    force in it, which is the null the reading actually has to clear.
    """
    rng = random.Random(seed)
    diffs = {k: [v[i + 1] - v[i] for i in range(len(v) - 1)] for k, v in series.items()}
    ps = []
    for _ in range(nsim):
        sim = {}
        for k, dv in diffs.items():
            L = len(dv)
            if L < 2:
                continue
            b = min(block, L)
            out = []
            while len(out) < L:
                s = rng.randrange(L)
                out.extend(dv[(s + j) % L] for j in range(b))
            x, pts = 0.0, []
            for step in out[:L]:
                x = phi * x + step
                pts.append(x)
            sim[k] = pts
        r = reversion(sim)
        if r["proportion_back"] is not None:
            ps.append(r["proportion_back"])
    return {
        "block": block,
        "phi": phi,
        "sims": len(ps),
        "mean": sum(ps) / len(ps),
        "sd": sd(ps),
        "p05": quantile(ps, 0.05),
        "p95": quantile(ps, 0.95),
    }


def null_band(shape, phi, nsim, seed):
    rng = random.Random(seed)
    ps = []
    for _ in range(nsim):
        r = reversion(simulate(shape, rng, phi))
        if r["proportion_back"] is not None:
            ps.append(r["proportion_back"])
    return {
        "sims": len(ps),
        "mean": sum(ps) / len(ps),
        "sd": sd(ps),
        "p05": quantile(ps, 0.05),
        "p95": quantile(ps, 0.95),
    }


PRE_CRISIS_END = "2021-S1"   # the station's own cut, fixed there and not searched over


def one_reading(series, seed_off, label):
    """Observed proportion against the strictest eligible null, for one slice."""
    shape = {k: (len(v), sd([v[i + 1] - v[i] for i in range(len(v) - 1)]))
             for k, v in series.items() if len(v) > 1}
    if len(shape) < 3:
        return {"label": label, "usable": False, "countries": len(shape)}
    r = reversion(series)
    if r["proportion_back"] is None:
        return {"label": label, "usable": False, "countries": len(shape)}
    cands = [("gaussian_walk", null_band(shape, 1.0, NSIM, seed_off)),
             ("shuffled_differences", shuffled_diff_null(series, NSIM, seed_off + 1))]
    cands += [(f"block_bootstrap_{b}",
               block_bootstrap_null(series, b, NSIM, seed_off + 10 + b))
              for b in (2, 3, 4, 6, 8)]
    nm, nl = max(cands, key=lambda kv: kv[1]["mean"])
    g = r["proportion_back"] - nl["mean"]
    fl = Z90 * nl["sd"]
    return {
        "label": label,
        "usable": True,
        "countries": len(shape),
        "n": r["n"],
        "observed": r["proportion_back"],
        "strict_null_name": nm,
        "strict_null": nl["mean"],
        "gap": g,
        "floor": fl,
        "separated": bool(g > fl),
        "all_nulls": {k: round(v["mean"], 6) for k, v in cands},
    }


def main() -> int:
    if not SRC.exists():
        print(f"input missing: {SRC}", file=sys.stderr)
        return 2
    cells = json.loads(SRC.read_text(encoding="utf-8"))["cells"]

    raw = defaultdict(list)
    for c in cells:
        v = c.get(BASE)
        if v is not None:
            raw[c["geo"]].append((c["semester"], float(v)))
    series = {k: [v for _, v in sorted(pairs)] for k, pairs in raw.items()}
    shape = {k: (len(v), sd([v[i + 1] - v[i] for i in range(len(v) - 1)])) for k, v in series.items()}

    read = reversion(series)
    walk = null_band(shape, 1.0, NSIM, SEED)
    shuf = shuffled_diff_null(series, NSIM, SEED + 1000)
    # Block length is load-bearing, so the whole ladder is printed and the choice is
    # not left to taste. The usual length for a series of L points is about L**(1/3),
    # which is 3.4 here at L = 38. Blocks are carried up to 8, which is already more
    # than twice that; beyond it the resampled series is mostly one contiguous run of
    # the original and the null degenerates into the observation itself, so those
    # lengths are printed as a trend and are not eligible to be the null.
    BLOCK_LADDER = (2, 3, 4, 6, 8)
    BLOCK_TREND = (12, 16)
    med_len = median([len(v) for v in series.values()])
    principled_block = med_len ** (1.0 / 3.0)
    blocks = [block_bootstrap_null(series, b, NSIM, SEED + 3000 + b) for b in BLOCK_LADDER]
    trend = [block_bootstrap_null(series, b, NSIM, SEED + 3500 + b) for b in BLOCK_TREND]
    # The steps this panel carries are negatively autocorrelated, so a null that
    # destroys their order understates what a level with no restoring force does.
    ac = [acf1([v[i + 1] - v[i] for i in range(len(v) - 1)]) for v in series.values()]
    ac = [a for a in ac if a is not None]
    ac_median = median(ac)
    ac_negative = sum(1 for a in ac if a < 0)
    cands = [("gaussian_walk", walk), ("shuffled_differences", shuf)] + [
        (f"block_bootstrap_{b['block']}", b) for b in blocks
    ]
    strict_name, strict = max(cands, key=lambda kv: kv[1]["mean"])
    STRICT_BLOCK = strict.get("block", 8)

    # the artefact this file exists to not fall for, measured
    artefact = walk["mean"] - 0.5
    gap = read["proportion_back"] - strict["mean"]
    floor = Z90 * strict["sd"]
    separated = abs(gap) > floor

    # Rule 11f, 2026-09-13. Five of this station's verdicts were a literal True.
    # None of the readings moves: what changes is that an arm which fails to
    # produce its object now says so instead of being written as printed. These
    # are not verdicts on the reading, which is deliberately left to the detail
    # (rule 11, print the object): they say the object is there to be printed.
    r3_object = (read["back"] + read["away"] == read["n"] and read["n"] > 0
                 and strict["sd"] > 0 and floor > 0)
    # R5's claim has a second half that is checkable: the null used is the
    # strictest of the eligible ones, not merely one of them.
    r5_strictest = (bool(blocks) and bool(ac)
                    and strict["mean"] == max(k[1]["mean"] for k in cands)
                    and strict_name not in {f"block_bootstrap_{b['block']}"
                                            for b in trend})

    # Seasonality is the obvious alternative and it is cheap to measure. The panel is
    # semi-annual: if the reversion is an S1-to-S2 alternation rather than a restoring
    # force, it disappears inside a single semester half, where consecutive points are
    # a year apart and the alternation cannot act.
    parity = {}
    for half in ("S1", "S2"):
        sub = {}
        for k, pairs in raw.items():
            pts = [v for s, v in sorted(pairs) if s.endswith(half)]
            if len(pts) >= 4:
                sub[k] = pts
        if not sub:
            continue
        r_sub = reversion(sub)
        cand_sub = [shuffled_diff_null(sub, NSIM, SEED + 2000 + (0 if half == "S1" else 1))]
        cand_sub += [block_bootstrap_null(sub, b, NSIM, SEED + 4000 + b) for b in (2, 4)]
        n_sub = max(cand_sub, key=lambda x: x["mean"])
        parity[half] = {
            "countries": len(sub),
            "n": r_sub["n"],
            "observed": r_sub["proportion_back"],
            "shuffled_null": n_sub["mean"],
            "null_sd": n_sub["sd"],
            "gap": r_sub["proportion_back"] - n_sub["mean"],
            "floor": Z90 * n_sub["sd"],
            "separated": bool(abs(r_sub["proportion_back"] - n_sub["mean"]) > Z90 * n_sub["sd"]),
        }
    parity_holds = all(v["separated"] for v in parity.values()) if parity else False
    # R6 is repeated inside each half, so both halves have to have been read
    r6_both_halves = len(parity) == 2 and all(
        v.get("observed") is not None and v.get("floor") is not None
        for v in parity.values())

    # The ladder has to be built on the same steps the null carries, or it compares a
    # Gaussian-step process against an autocorrelated-step null and the difference is
    # the step structure rather than the force. So the force is applied ON TOP of the
    # same block-bootstrapped steps, and the comparison is one-sided: a restoring force
    # can only push the proportion UP.
    ladder = []
    for H in HALF_LIVES:
        phi = 0.5 ** (1.0 / H)
        b = block_bootstrap_null(series, STRICT_BLOCK, NSIM, SEED + 5000 + H, phi=phi)
        ladder.append(
            {
                "half_life_semesters": H,
                "phi": round(phi, 6),
                "proportion_it_produces": round(b["mean"], 6),
                "separated_from_the_strict_null": bool(b["mean"] - strict["mean"] > floor),
            }
        )
    # The pipeline's own capability check, run in its own controlled setting: a planted
    # AR(1) with Gaussian steps against a Gaussian walk with the same steps. This asks
    # whether the code can see a force at all, which is a different question from
    # whether this panel can see one through its own step structure.
    planted = null_band(shape, 0.5 ** (1.0 / 4), NSIM, SEED + 7)
    planted_gap = planted["mean"] - walk["mean"]
    planted_separates = planted_gap > Z90 * walk["sd"]

    seen = [x["half_life_semesters"] for x in ladder if x["separated_from_the_strict_null"]]
    unseen = [x["half_life_semesters"] for x in ladder if not x["separated_from_the_strict_null"]]

    # ---- arm two: cut the energy shock out, using the station's own fixed cut ----
    pre = {}
    for k, pairs in raw.items():
        pts = [v for s, v in sorted(pairs) if s <= PRE_CRISIS_END]
        if len(pts) >= 4:
            pre[k] = pts
    pre_read = one_reading(pre, SEED + 8000, f"I_TAX up to {PRE_CRISIS_END}")
    # R7 formats pre_read's numbers, so an unusable window used to crash on the
    # format rather than be reported. The arm now says it did not produce a reading.
    r7_window_read = (pre_read.get("n") is not None and pre_read.get("n") > 0
                      and pre_read.get("observed") is not None
                      and pre_read.get("floor") is not None)

    # ---- arm three: the other two tax bases, full window ----
    base_arms = []
    for other in ("X_TAX", "X_VAT"):
        rawo = defaultdict(list)
        for c in cells:
            v = c.get(other)
            if v is not None:
                rawo[c["geo"]].append((c["semester"], float(v)))
        so = {k: [v for _, v in sorted(pr)] for k, pr in rawo.items() if len(pr) >= 4}
        base_arms.append(one_reading(so, SEED + 9000 + len(base_arms) * 100, other))

    criteria = [
        {
            "name": "B52-R1",
            "kind": "known_answer",
            "criterion": (
                "the pipeline reproduces the artefact it has to be read against, and "
                "separates a planted restoring force from a random walk"
            ),
            "passed": bool(artefact > 0.05 and planted_separates),
            "detail": (
                f"a random walk matched to this panel's own lengths and step scales "
                f"reads {walk['mean']:.4f} back, not 0.5, so the pull toward a "
                f"sample-estimated centre is {artefact:+.4f} and is mechanical. "
                f"A planted half-life of 4 semesters reads {planted['mean']:.4f} "
                f"against that walk, gap {planted_gap:+.4f} on a floor of "
                f"{Z90 * walk['sd']:.4f}, so the code can see a force when one is there. "
                f"The first version of this file wrote the null at one half and this "
                f"check killed it: every reading against one half was the artefact."
            ),
        },
        {
            "name": "B52-R2",
            "kind": "instrument",
            "criterion": (
                "print every country's series length and how many of its steps entered "
                "the reading; name the ones too short rather than dropping them"
            ),
            "passed": len(read["per_unit"]) > 0 and read["n"] > 0,
            "detail": (
                f"{len(read['per_unit'])} countries, {read['n']} large-deviation steps "
                f"entered, {NSIM} simulations per null, each matched country by country "
                "on length and step scale."
            ),
        },
        {
            "name": "B52-R3",
            "kind": "own_reading",
            "criterion": (
                "print the observed proportion against a measured random-walk null, "
                "with that null's own spread beside it"
            ),
            "passed": r3_object,
            "detail": (
                f"observed {read['proportion_back']:.4f} (back {read['back']}, away "
                f"{read['away']}); gaussian-walk null {walk['mean']:.4f} sd "
                f"{walk['sd']:.4f}; shuffled-differences null {shuf['mean']:.4f} sd "
                f"{shuf['sd']:.4f}; held against the stricter of the two "
                f"({strict_name}, {strict['mean']:.4f}, 5th to 95th {strict['p05']:.4f} "
                f"to {strict['p95']:.4f}); gap {gap:+.4f} against a floor of "
                f"{floor:.4f}. "
                + ("Separated." if separated else "Not separated: the class square's "
                   "path is not distinguishable from one with no restoring force in it.")
            ),
        },
        {
            "name": "B52-R5",
            "kind": "instrument",
            "criterion": (
                "a null carrying the panel's own step autocorrelation is computed, "
                "and the reading is held against the strictest null available"
            ),
            "passed": r5_strictest,
            "detail": (
                f"the steps this panel carries are negatively autocorrelated: median "
                f"lag-one {ac_median:+.4f}, negative in {ac_negative} of {len(ac)} "
                "countries. **A shuffled-difference null destroys exactly that**, so it "
                "understates what a level with no restoring force does, and holding the "
                "reading against it would score the step structure as a force. Block "
                "bootstraps keep the local step structure and still integrate to a walk: "
                + ", ".join(f"block {b['block']} reads {b['mean']:.4f}" for b in blocks)
                + f"; gaussian walk {walk['mean']:.4f}, shuffled {shuf['mean']:.4f}. "
                f"The usual block length at a median series of {med_len:.0f} points is "
                f"{principled_block:.1f}, and the ladder is carried to 8, more than "
                f"twice that. Beyond it the null degenerates into the observation: "
                + ", ".join(f"block {b['block']} reads {b['mean']:.4f}" for b in trend)
                + f", printed as a trend and not eligible. The strictest eligible null "
                f"is {strict_name} at {strict['mean']:.4f} and it is the one used."
            ),
        },
        {
            "name": "B52-R6",
            "kind": "own_reading",
            "criterion": (
                "the reading is repeated inside each semester half, where a "
                "half-yearly alternation cannot act"
            ),
            "passed": r6_both_halves,
            "detail": (
                "; ".join(
                    f"{h}: observed {v['observed']:.4f} against a shuffled null of "
                    f"{v['shuffled_null']:.4f}, gap {v['gap']:+.4f}, floor "
                    f"{v['floor']:.4f}, separated {v['separated']}"
                    for h, v in sorted(parity.items())
                )
                + ". Consecutive points inside one half are a year apart, so an "
                "S1-to-S2 alternation cannot produce this. "
                + ("Both halves separate, so the reading is not the alternation."
                   if parity_holds else
                   "Not both halves separate, so seasonality is not excluded and the "
                   "main reading is held to that scope.")
            ),
        },
        {
            "name": "B52-R7",
            "kind": "own_reading",
            "criterion": (
                "the reading repeated on a window stopping before the energy shock, "
                "at the cut this station already fixed and did not search over"
            ),
            "passed": r7_window_read,
            "detail": (
                (f"up to {PRE_CRISIS_END}: {pre_read['countries']} countries, "
                 f"n {pre_read.get('n')}, observed {pre_read.get('observed'):.4f} "
                 f"against {pre_read.get('strict_null_name')} at "
                 f"{pre_read.get('strict_null'):.4f}, gap {pre_read.get('gap'):+.4f} on a "
                 f"floor of {pre_read.get('floor'):.4f}, separated "
                 f"{pre_read.get('separated')}. "
                 if r7_window_read else
                 f"up to {PRE_CRISIS_END} the window produced no reading: "
                 f"{pre_read.get('countries')} countries, n {pre_read.get('n')}. "
                 f"The arm is reported as not read rather than formatted as a number. ")
                + "A shock that goes up and comes back down "
                "is by itself large deviations followed by moves back, so this is the "
                "alternative that has to be measured rather than argued away."
            ),
        },
        {
            "name": "B52-R8",
            "kind": "own_reading",
            "criterion": (
                "the reading repeated on the other two tax bases, so a force living in "
                "the tax component can be told from one in the price"
            ),
            "passed": sum(1 for a in base_arms if a.get("usable")) == 2,
            "detail": "; ".join(
                f"{a['label']}: observed {a['observed']:.4f} against {a['strict_null']:.4f} "
                f"({a['strict_null_name']}), gap {a['gap']:+.4f}, floor {a['floor']:.4f}, "
                f"separated {a['separated']}"
                for a in base_arms if a.get("usable")
            ) + ". Tax-excluded against tax-included is the cheapest split there is on "
                "this record, and administratively set tax rates are one of the three "
                "candidates registered for where a restoring force could come from.",
        },
        {
            "name": "B52-R4",
            "kind": "own_reading",
            "criterion": (
                "print which half-lives this panel could have told apart from a random "
                "walk, so the reading carries a bound and not a bare zero"
            ),
            "passed": len(ladder) > 0,
            "detail": (
                f"half-lives in semesters this panel separates from a level with no "
                f"restoring force, built on the panel's own steps: "
                f"{seen}; those it does not: {unseen}. The panel spans 38 semesters. "
                "This is the separation D48's fourth shape was registered as missing: "
                "the first list is what a reading of no restoring force excludes, the "
                "second is what it leaves open."
            ),
        },
    ]

    record = {
        "stage": "B52",
        "arm": "restoring force, the readable form of D48 shape four",
        "config": {
            "source_record": SRC.name,
            "base_tax": BASE,
            "tercile": TERCILE,
            "z90": Z90,
            "half_lives_semesters": list(HALF_LIVES),
            "nsim": NSIM,
            "seed": SEED,
        },
        "diagnostic_only": True,
        "diagnostic_reason": (
            "This arm adds a reading and changes no verdict of B52's registered "
            "criteria. It writes D48 shape four in a readable form and runs it once "
            "on a panel already on disk."
        ),
        "reading": read,
        "random_walk_null": walk,
        "shuffled_differences_null": shuf,
        "block_bootstrap_nulls": blocks,
        "block_trend_not_eligible": trend,
        "median_series_length": med_len,
        "principled_block_length": principled_block,
        "step_acf1_median": ac_median,
        "step_acf1_negative_countries": ac_negative,
        "strict_null_used": strict_name,
        "artefact_above_one_half": artefact,
        "gap_against_null": gap,
        "floor": floor,
        "separated_from_null": separated,
        "pre_crisis_arm": pre_read,
        "pre_crisis_end": PRE_CRISIS_END,
        "tax_base_arms": base_arms,
        "semester_parity": parity,
        "parity_both_separate": parity_holds,
        "planted_check": {"mean": planted["mean"], "gap": planted_gap,
                          "separates": planted_separates},
        "strict_block": STRICT_BLOCK,
        "half_life_ladder": ladder,
        "half_lives_separable": seen,
        "half_lives_not_separable": unseen,
        "criteria": criteria,
    }
    OUT.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}[{c['kind']}] {c['name']}: {c['detail'][:200]}")
    print()
    print(f"step acf1 median {ac_median:+.4f}, negative in {ac_negative}/{len(ac)}")
    print(f"nulls: walk {walk['mean']:.4f} | shuffled {shuf['mean']:.4f} | "
          + " | ".join(f"b{b['block']} {b['mean']:.4f}" for b in blocks))
    print(f"  (median length {med_len:.0f}, usual block {principled_block:.1f}; "
          "not eligible, degenerating: "
          + ", ".join(f"b{b['block']} {b['mean']:.4f}" for b in trend) + ")")
    print(f"observed {read['proportion_back']:.4f} | strict {strict_name} {strict['mean']:.4f} "
          f"| gap {gap:+.4f} floor {floor:.4f} | separated {separated}")
    print(f"pre-crisis (<= {PRE_CRISIS_END}): obs {pre_read.get('observed')} null "
          f"{pre_read.get('strict_null')} gap {pre_read.get('gap')} floor "
          f"{pre_read.get('floor')} sep {pre_read.get('separated')}")
    for a in base_arms:
        if a.get("usable"):
            print(f"{a['label']}: obs {a['observed']:.4f} null {a['strict_null']:.4f} "
                  f"gap {a['gap']:+.4f} floor {a['floor']:.4f} sep {a['separated']}")
    for h, v in sorted(parity.items()):
        print(f"   {h}: obs {v['observed']:.4f} null {v['shuffled_null']:.4f} "
              f"gap {v['gap']:+.4f} floor {v['floor']:.4f} sep {v['separated']}")
    for x in ladder:
        print(f"   H={x['half_life_semesters']:>2}  produces {x['proportion_it_produces']:.4f}  "
              f"separable {x['separated_from_the_strict_null']}")
    print(f"half-lives separable {seen}; not separable {unseen}")
    print("wrote", OUT.name)
    return 1 if any(c["passed"] is False for c in criteria) else 0


if __name__ == "__main__":
    raise SystemExit(main())
