"""B30-4, the combination-market gate: can this axis resolve the effect at all.

**This file opens no reading.** It answers one question before any statistic is taken on
the combination markets, which is whether an axis built from them can carry the effect
the single-tag axis already returned. If it cannot, the arm registers as not adjudicable
on this carrier and no entropy is read.

**Why the combination markets are worth an axis.** The registered reading runs
`price_point_entropy` against a destination's density over 151 single tags, and on that
axis **a thin tag is also an obscure one**. So one account of branch A survives it: the
prices scatter at the thin end because the sellers there are less practised, rather than
because there is no anchor to copy. **A destination made by intersecting two established
tags is thin without being obscure**, and its sellers are the ordinary sellers of two
well-known kinds, so an axis of those separates density from obscurity.

**The structure looks like the containment control withdrawn earlier on this arm, and the
mechanical bias runs the other way, which is what makes it admissible.** That control set
a tag against a subset of itself and a mixture is at least as spread as its own
component, so it leaned toward its own finding. Entropy is concave, so a parent's
price-point entropy is at least the weighted average over any partition of it, **which
predicts entropy rising with density, and the registered reading is the opposite sign**.
**And this file does not rest on that argument**: the resolution it reports is measured.

**The resolution is measured by planting, not by counting points.** An earlier version of
this gate estimated an effective `n` by inverting the sd of a permutation null, and a
seeded probe killed it: given an axis whose destinations all carry the *same* projects,
so that the axis holds one independent point, it reported an effective `n` of 62.
**The equal-n draw is why.** Two destinations with identical pools still get independent
samples, so their entropies vary independently and the null sd comes out as though they
were separate points. **The resampling injects the very independence the estimate was
supposed to measure**, by an amount nothing here can bound. So the gate does what this
arm's resolution ladder already did: **it plants an effect of the registered size and
reports how often the test catches it.** Planting carries the dependence and the draw
noise together, because both are present in the planted arm and in its null.

**Two axes, and only one of them is gated.**

- **the packed axis**: destinations chosen to share no project at all, so its
  independence is a fact about the sets rather than an estimate, and a plant on it has no
  conflict because no project is asked for two prices. **This is the axis the gate
  judges, and it is the conservative one.**
- **the full axis**: every destination passing the rule. Its correlation is printed as an
  object, its points overlap, and nothing here scores it.

**The floor is computed, never typed.** A one-sided test at `alpha = 0.05` has power
exactly one half at `theta = z * se`, so a floor at power one half is the same line as
the band gate. It is quoted for reference; **what the criterion uses is the measured
detection rate**, which needs no formula at all.

Run it:

    python experiments/b30_4_combo_gate.py            # the gate
    python experiments/b30_4_combo_gate.py --selftest # seeded probes, no record written

It writes ``results/b30_4_combo_gate.json``, marked as not a reading.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import random
import statistics
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
import b30_4_knob_sweep as sweep      # noqa: E402  the estimator is shared, never copied

ROOT = HERE.parent
PRICES = ROOT / "results" / "b30_4_itch_prices.json"
OUT = ROOT / "results" / "b30_4_combo_gate.json"

#: The effect the single-tag axis returned for this measure, weakest of the six registered
#: settings, taken as a magnitude. The sign the plant uses is negative, which is branch A.
REGISTERED_EFFECT = 0.260
ALPHA = 0.05
Z_ONE_SIDED = 1.645

MIN_PAID = sweep.EQUAL_N
PACK_TRIALS = 600
PACK_SEED = 7

#: The gate runs at one setting. The reading is registered across six, and the sweep
#: showed this measure's sign holds on all of them; resolution is what is at issue here.
GATE_SALE, GATE_CURRENCY = "all", "usd_only"

#: What the criterion is judged on: power above one half, the same line the band gate
#: draws, so nothing new is chosen here.
POWER_FLOOR = 0.50
#: A density span below this cannot carry a relation against density whatever the power.
SPAN_FLOOR = 10.0


def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def power_at(n, theta=REGISTERED_EFFECT, z=Z_ONE_SIDED):
    """Power of a one-sided rank test at `theta` with `n` independent points, for reference."""
    return 0.0 if n < 3 else _phi(theta * math.sqrt(n - 1) - z)


def floor_n(theta=REGISTERED_EFFECT, z=Z_ONE_SIDED):
    """The n at which that power is exactly one half, which is theta = z*se."""
    return 1.0 + (z / theta) ** 2


# ----- the destinations -----

def load():
    d = json.loads(PRICES.read_text(encoding="utf-8"))
    return d["games"], {s: set(t["ids"]) for s, t in d["tags"].items()}


def destinations(members, min_paid=MIN_PAID):
    """Every two-tag intersection that can carry the draw and is proper in both parents.

    "Established" is the median single-tag paid count, so the threshold is a property of
    this carrier rather than a number brought in from outside.
    """
    sizes = sorted(len(v) for v in members.values())
    established = statistics.median(sizes)
    out = []
    for a, b in itertools.combinations(sorted(members), 2):
        pool = members[a] & members[b]
        n = len(pool)
        if n < min_paid:
            continue
        smaller = min(len(members[a]), len(members[b]))
        if n >= smaller or smaller < established:
            continue
        out.append({"a": a, "b": b, "paid": n, "ids": pool,
                    "parent_a": len(members[a]), "parent_b": len(members[b])})
    return out, established, sizes


def span_of(dests):
    ns = [e["paid"] for e in dests]
    return max(ns) / min(ns)


def eligible(games, dests, sale=GATE_SALE, currency=GATE_CURRENCY):
    """Keep only destinations that can actually supply the draw at the gate's setting.

    **The count that decides whether a destination can be read is not its project count.**
    It is how many of those projects carry a usable price once the setting's filter has
    run, and at a dollars-only setting that is fewer. Packing on the project count and
    discovering the shortfall inside the statistic wastes independent points: the first
    version of this gate packed 50 and the statistic could only read 42 of them.
    **The project count stays the density**, because that is what a seller sees; only
    eligibility uses the usable count.
    """
    out = []
    for e in dests:
        pool = sweep.price_pool(games, sorted(e["ids"]), sale, currency)
        if len(pool) >= sweep.EQUAL_N:
            out.append({**e, "usable": len(pool)})
    return out


def pack_independent(dests, trials=PACK_TRIALS, seed=PACK_SEED):
    """Destinations sharing no project at all, keeping count and density span both large.

    Independence is a fact about the sets, so this axis needs no estimate. The search is a
    seeded restart because the packing is not unique and the sort order decides it.
    """
    rng = random.Random(seed)
    best, history = None, []
    for _ in range(trials):
        order = dests[:]
        rng.shuffle(order)
        order.sort(key=lambda e: -e["paid"] * rng.uniform(0.3, 1.0))
        taken, seen = [], set()
        for e in order:
            if e["ids"] & seen:
                continue
            taken.append(e)
            seen |= e["ids"]
        history.append((len(taken), span_of(taken)))
        if best is None or (len(taken), span_of(taken)) > (len(best), span_of(best)):
            best = taken
    return best, history


def project_overlap(dests):
    """Printed as objects rather than a score, so a packing that is not clean shows itself."""
    seen = {}
    for i, e in enumerate(dests):
        for g in e["ids"]:
            seen.setdefault(g, []).append(i)
    pairs = list(itertools.combinations(range(len(dests)), 2))
    touching = sum(1 for i, j in pairs if dests[i]["ids"] & dests[j]["ids"])
    return {"distinct_projects": len(seen),
            "projects_in_more_than_one": sum(1 for v in seen.values() if len(v) > 1),
            "largest_multiplicity": max((len(v) for v in seen.values()), default=0),
            "pairs_with_any_overlap": touching, "pairs_total": len(pairs)}


def knob_variants(games, members, established):
    """What the packing would be under the two knobs this gate could legitimately turn.

    **A gate that fails should say whether a declared knob opens it**, and it should say
    what turning that knob costs. Only one of these two is free. The currency knob widens
    the pool a destination draws from and changes nothing about what a destination is.
    **Dropping the requirement that both parents are established is not a knob**: it admits
    combinations of obscure tags, and separating thin from obscure is the entire reason
    this axis exists, so opening the gate that way removes the reason to walk through it.
    """
    import itertools as _it
    rows = []
    for require in (True, False):
        base = []
        for a, b in _it.combinations(sorted(members), 2):
            pool = members[a] & members[b]
            n = len(pool)
            if n < sweep.EQUAL_N:
                continue
            smaller = min(len(members[a]), len(members[b]))
            if n >= smaller or (require and smaller < established):
                continue
            base.append({"a": a, "b": b, "paid": n, "ids": pool,
                         "parent_a": len(members[a]), "parent_b": len(members[b])})
        for cur in ("usd_only", "all_face_value"):
            el = eligible(games, base, currency=cur)
            pk, _h = pack_independent(el)
            rows.append({"established_required": require, "currency": cur,
                         "destinations": len(base), "eligible": len(el),
                         "packed": len(pk), "span": span_of(pk),
                         "reference_power": power_at(len(pk)),
                         "keeps_the_axis_purpose": require})
    return rows


# ----- the statistic, shared with the reading -----

#: Decimals an entropy is rounded to before it is ranked.
#: **A rank is decided by whether two numbers are equal, and at this measure most of them
#: are.** On the packed axis 49 values hold 22 distinct levels, so 27 of the 49 sit in
#: ties, and four pairs are separated by `4.44e-16`, which is two ulp: the same level
#: reached by two summation orders. `math.log` is the platform's, so those last bits differ
#: between builds, a tie on one machine is a non-tie on the other, and the correlation
#: moves without any draw changing. Measured: the same file at the same seed read
#: `-0.172614` on one build and `-0.1646` on another, with the packed axis byte-identical.
#: Ten decimals sits six orders above the spurious gap and seven below the smallest real
#: one, which is set by how coarse an entropy of twelve draws can be.
RANK_DECIMALS = 10


def one_correlation(games, dests, rng, reps, sale=GATE_SALE, currency=GATE_CURRENCY):
    xs, ys = [], []
    for e in dests:
        pool = sweep.price_pool(games, sorted(e["ids"]), sale, currency)
        if len(pool) < sweep.EQUAL_N:
            continue
        med = statistics.median(
            [sweep.price_point_entropy(rng.sample(pool, sweep.EQUAL_N)) for _ in range(reps)])
        if med is None:
            continue
        xs.append(round(med, RANK_DECIMALS))     # see RANK_DECIMALS: ties decide the rank
        ys.append(e["paid"])
    if len(xs) < 5:
        return None, len(xs)
    return sweep.spearman(xs, ys), len(xs)


def permuted(games, rng):
    """The same projects with their prices dealt among them, every membership untouched."""
    keys = [k for k, v in games.items() if v.get("price_cents") and v["price_cents"] > 0]
    src = [games[k] for k in keys]
    idx = list(range(len(keys)))
    rng.shuffle(idx)
    out = dict(games)
    for pos, k in enumerate(keys):
        s = src[idx[pos]]
        g = dict(games[k])
        g["price_cents"], g["price_currency"] = s["price_cents"], s["price_currency"]
        g["on_sale"], g["sale_pct"] = s["on_sale"], s["sale_pct"]
        out[k] = g
    return out


# ----- the plant -----

def plant(dests, price_bag, slope, rng):
    """Give each project a price so a destination's price-point entropy falls with density.

    Each destination piles a fraction of its projects onto one point, the fraction rising
    with the destination's rank in density, and draws the rest from the carrier's own price
    distribution. **A project asked for two prices keeps whichever destination wrote last**,
    which is the collapse a dependent axis should suffer and a probe checks for.

    **The ids are sorted before they are walked, and that is load bearing.** A
    destination holds a set, and iterating a set of strings gives an order that is
    decided by the hash seed of the process. Feeding that order to a seeded sampler
    means **the seed no longer fixes the sample**: three runs of this file at one seed
    returned `-0.1269`, `-0.1268` and `-0.0919` for the same quantity before the sort
    was put in. The derived-file rule already asks for a fixed iteration order for
    anything written to disk; this is the same rule one step earlier, on anything a
    seeded draw reads.
    """
    order = sorted(range(len(dests)), key=lambda i: dests[i]["paid"])
    u = [0.0] * len(dests)
    for rank, i in enumerate(order):
        u[i] = rank / max(len(dests) - 1, 1)
    mode = collections.Counter(price_bag).most_common(1)[0][0]
    games = {}
    for i, e in enumerate(dests):
        pile = min(0.98, max(0.0, slope * u[i]))
        for gid in sorted(e["ids"]):
            price = mode if rng.random() < pile else rng.choice(price_bag)
            games[gid] = {"price_cents": price, "price_currency": "USD", "on_sale": False,
                          "sale_pct": None, "genre": "Action", "title": gid,
                          "url": "", "author": ""}
    return games


def calibrate(dests, price_bag, target, reps, seed, lo=0.0, hi=1.4, steps=14):
    """Bisect the pile slope until the planted correlation sits at the target magnitude."""
    for _ in range(steps):
        mid = (lo + hi) / 2.0
        rng = random.Random(seed)
        got, _ = one_correlation(plant(dests, price_bag, mid, rng), dests,
                                 random.Random(seed + 1), reps)
        if got is None:
            return mid, None
        if abs(got) < target:
            lo = mid
        else:
            hi = mid
    mid = (lo + hi) / 2.0
    rng = random.Random(seed)
    got, _ = one_correlation(plant(dests, price_bag, mid, rng), dests,
                             random.Random(seed + 1), reps)
    return mid, got


def detection_rate(dests, price_bag, slope, reps, shuffles, plants, seed):
    """How often a planted effect clears its own overlap-preserving null, one-sided.

    Returns the rate and every observed value, so the object is printable and not a score.
    """
    hits, seen = 0, []
    for p in range(plants):
        rng = random.Random(seed * 1000 + p)
        games = plant(dests, price_bag, slope, rng)
        obs, kept = one_correlation(games, dests, random.Random(seed * 1000 + p + 1), reps)
        if obs is None:
            continue
        null = []
        for s in range(shuffles):
            r2 = random.Random(seed * 100000 + p * 1000 + s)
            v, _ = one_correlation(permuted(games, r2), dests, r2, reps)
            if v is not None:
                null.append(v)
        if len(null) < 10:
            continue
        null.sort()
        cut = null[max(0, int(ALPHA * len(null)) - 1)]     # lower tail, branch A is negative
        seen.append({"observed": obs, "cut": cut, "kept": kept, "detected": obs <= cut})
        if obs <= cut:
            hits += 1
    return (hits / len(seen) if seen else None), seen


# ----- criteria, each computed from an object, each with a probe that flips it -----

def build_criteria(rate, null_rate, packed_n, packed_span, overlap):
    """Two criteria, and they ask about two different things.

    **The calibration and the power are separate questions and the first version of this
    file put them in one criterion.** That mislabels a shortfall of power as an anomaly
    caught by a known-answer check, and a known-answer FAIL in this project's records
    means the check found something wrong with the instrument and can name it. Here the
    instrument is sound: its false-positive rate sits on alpha. What is short is the axis.
    """
    out = []

    if null_rate is None:
        ka_passed, ka = None, "not evaluated: the unplanted arm returned too few replicates"
    elif null_rate <= 3 * ALPHA:
        ka_passed, ka = True, "the test does not find an effect where none was planted"
    else:
        ka_passed, ka = False, "the test finds an effect where none was planted"
    out.append({
        "name": "B30-4-3",
        "kind": "known_answer",
        "statement": ("Planting no effect at all into the packed axis is detected no more "
                      "often than a few times alpha, which is the calibration of the test "
                      "and is separate from whether the axis has the power to see a real "
                      "effect."),
        "passed": ka_passed,
        "detail": (f"unplanted detection rate "
                   f"{'none' if null_rate is None else format(null_rate, '.3f')} "
                   f"against alpha {ALPHA}: {ka}"),
    })

    clean = overlap["pairs_with_any_overlap"] == 0
    spans = packed_span >= SPAN_FLOOR
    if rate is None or ka_passed is None:
        passed, gate = None, "no verdict: the resolution was not measured"
    elif ka_passed is False:
        passed, gate = None, "no verdict: the test is not calibrated, so its power is not readable"
    elif not clean:
        passed, gate = False, ("not adjudicable: the packing is not clean, so its "
                               "independence is not a fact about the sets")
    elif not spans:
        passed, gate = False, ("not adjudicable: the independent destinations do not span "
                               "enough density to read a relation against it")
    elif rate <= POWER_FLOOR:
        passed, gate = False, ("not adjudicable on this carrier: the axis does not resolve "
                               "an effect of the registered size")
    else:
        passed, gate = True, "the arm opens on the packed axis"
    out.append({
        "name": "B30-4-4",
        "kind": "instrument",
        "statement": ("The packed axis is independent as a fact about its sets, spans at "
                      "least a decade of density, and catches a planted effect of the "
                      "registered size more than half the time. All three are computed."),
        "passed": passed,
        "detail": (f"{packed_n} destinations, {overlap['pairs_with_any_overlap']} of "
                   f"{overlap['pairs_total']} pairs touching, span factor {packed_span:.0f}, "
                   f"planted detection rate "
                   f"{'none' if rate is None else format(rate, '.3f')} against a floor of "
                   f"{POWER_FLOOR}, reference power at this n {power_at(packed_n):.3f}; {gate}"),
    })
    return {c["name"]: c for c in out}


# ----- self-test -----

def _synthetic(k, per, rng, shared=False):
    games, dests = {}, []
    shared_ids = None
    gid = 0
    for i in range(k):
        if shared and shared_ids is not None:
            ids = shared_ids
        else:
            ids = set()
            for _ in range(per):
                gid += 1
                ids.add(str(gid))
            if shared:
                shared_ids = ids
        for key in ids:
            games[key] = {"price_cents": 199, "price_currency": "USD", "on_sale": False,
                          "sale_pct": None, "genre": "Action", "title": key,
                          "url": "", "author": ""}
        dests.append({"a": f"t{i}a", "b": f"t{i}b", "paid": per + i * 3, "ids": ids,
                      "parent_a": per * 9, "parent_b": per * 9})
    return games, dests


def selftest():
    print("selftest")
    fails = []
    bag = [100, 199, 199, 299, 399, 499, 499, 499, 999, 1499, 1999]

    f = floor_n()
    assert abs(power_at(f) - 0.5) < 1e-9, "the reference floor is not where power is one half"
    print(f"  reference floor at effect {REGISTERED_EFFECT}: n = {f:.1f}, "
          f"power there {power_at(f):.6f}")

    rng = random.Random(11)
    _g, dis = _synthetic(50, 30, rng)
    slope, got = calibrate(dis, bag, REGISTERED_EFFECT, reps=25, seed=5)
    print(f"  disjoint synthetic: slope {slope:.4f} plants {got:+.3f}")
    rate, _ = detection_rate(dis, bag, slope, reps=25, shuffles=60, plants=12, seed=5)
    print(f"    planted detection rate {rate:.3f}, must be above {POWER_FLOOR}")
    if not (rate is not None and rate > POWER_FLOOR):
        fails.append("a planted effect of the registered size was not detected")

    flat, _ = detection_rate(dis, bag, 0.0, reps=25, shuffles=60, plants=12, seed=5)
    print(f"    unplanted detection rate {flat:.3f}, must be near alpha {ALPHA}")
    if not (flat is not None and flat <= 3 * ALPHA):
        fails.append("an unplanted axis was detected more often than alpha allows")

    _g2, dep = _synthetic(50, 30, random.Random(12), shared=True)
    dr, _ = detection_rate(dep, bag, slope, reps=25, shuffles=60, plants=12, seed=5)
    print(f"  every destination the same projects: detection rate {dr}, must be near alpha")
    if not (dr is not None and dr <= 3 * ALPHA):
        fails.append("an axis holding one independent point was reported as resolving")

    # the eligibility filter must drop a destination that cannot supply the draw
    thin_games = {"g1": {"price_cents": 199, "price_currency": "USD", "on_sale": False,
                         "sale_pct": None, "genre": "Action", "title": "g1",
                         "url": "", "author": ""}}
    thin_dest = [{"a": "x", "b": "y", "paid": 400, "ids": {"g1"},
                  "parent_a": 900, "parent_b": 900}]
    if eligible(thin_games, thin_dest):
        fails.append("the eligibility filter kept a destination with one usable price")
    fat_ids = {f"f{i}" for i in range(sweep.EQUAL_N)}
    fat_games = {k: {"price_cents": 199 + i, "price_currency": "USD", "on_sale": False,
                     "sale_pct": None, "genre": "Action", "title": k, "url": "", "author": ""}
                 for i, k in enumerate(sorted(fat_ids))}
    fat_dest = [{"a": "x", "b": "y", "paid": 400, "ids": fat_ids,
                 "parent_a": 900, "parent_b": 900}]
    keep = eligible(fat_games, fat_dest)
    if len(keep) != 1 or keep[0]["paid"] != 400:
        fails.append("the eligibility filter dropped a usable destination or moved its density")
    print("  the eligibility filter drops what cannot supply the draw and keeps the density")

    # a seeded draw must not depend on the order a destination's ids happen to arrive in
    ids_a = {f"o{i}" for i in range(40)}
    g_ord = {k: {"price_cents": 100 + 37 * i % 900, "price_currency": "USD",
                 "on_sale": False, "sale_pct": None, "genre": "Action", "title": k,
                 "url": "", "author": ""}
             for i, k in enumerate(sorted(ids_a))}
    d_fwd = [{"a": "p", "b": "q", "paid": 40, "ids": set(sorted(ids_a)),
              "parent_a": 900, "parent_b": 900},
             {"a": "r", "b": "s", "paid": 80, "ids": set(sorted(ids_a)),
              "parent_a": 900, "parent_b": 900}]
    d_rev = [{**e, "ids": set(reversed(sorted(ids_a)))} for e in d_fwd]
    v1, _ = one_correlation(g_ord, d_fwd, random.Random(7), 20)
    v2, _ = one_correlation(g_ord, d_rev, random.Random(7), 20)
    if v1 != v2:
        fails.append("a seeded draw moved when the ids were presented in another order")
    print("  a seeded draw does not move with the order the ids arrive in")

    # two values that are the same level reached two ways must rank as one level,
    # and a real difference must survive
    base = 2.094729047527649
    if round(base, RANK_DECIMALS) != round(base + 4.440892098500626e-16, RANK_DECIMALS):
        fails.append("rounding did not merge a two-ulp difference, so a tie is build dependent")
    if round(base, RANK_DECIMALS) == round(base + 1e-3, RANK_DECIMALS):
        fails.append("rounding merged a real difference between entropy levels")
    print("  a two-ulp difference ranks as one level and a real one still separates")

    clean = {"pairs_with_any_overlap": 0, "pairs_total": 100}
    dirty = {"pairs_with_any_overlap": 7, "pairs_total": 100}
    ok = build_criteria(0.80, 0.04, 50, 103.0, clean)
    assert ok["B30-4-3"]["passed"] and ok["B30-4-4"]["passed"], "a passing input did not pass"
    for label, args_, name, want in (
            ("low power", (0.30, 0.04, 50, 103.0, clean), "B30-4-4", False),
            ("low power must not touch the calibration",
             (0.30, 0.04, 50, 103.0, clean), "B30-4-3", True),
            ("finds nothing as something", (0.80, 0.40, 50, 103.0, clean), "B30-4-3", False),
            ("an uncalibrated test has no readable power",
             (0.80, 0.40, 50, 103.0, clean), "B30-4-4", None),
            ("no span", (0.80, 0.04, 50, 2.0, clean), "B30-4-4", False),
            ("dirty packing", (0.80, 0.04, 50, 103.0, dirty), "B30-4-4", False),
            ("unmeasured", (None, None, 50, 103.0, clean), "B30-4-3", None),
            ("unmeasured", (None, None, 50, 103.0, clean), "B30-4-4", None)):
        got_ = build_criteria(*args_)[name]["passed"]
        if got_ is not want:
            fails.append(f"{name} did not react to {label}: {got_!r} not {want!r}")
    print("  eight probes on the criteria, and the unmeasured cell carries no verdict")

    if fails:
        for x in fails:
            print("  FAILED:", x)
        return 1
    print("selftest ok")
    return 0


# ----- main -----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reps", type=int, default=50)
    ap.add_argument("--shuffles", type=int, default=120)
    ap.add_argument("--plants", type=int, default=20)
    ap.add_argument("--budget-seconds", type=float, default=2400.0)
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(selftest())

    games, members = load()
    dests, established, sizes = destinations(members)
    print(f"151-tag axis: paid counts {sizes[0]} to {sizes[-1]}, "
          f"established threshold (median) {established:.0f}")
    print(f"destinations passing the rule: {len(dests)}")
    ns = sorted(e["paid"] for e in dests)
    print(f"  paid counts {ns[0]} to {ns[-1]}, median {statistics.median(ns):.0f}")
    fr = sorted(e["paid"] / min(e["parent_a"], e["parent_b"]) for e in dests)
    print(f"  each as a share of its smaller parent: median {statistics.median(fr):.3f}, "
          f"max {fr[-1]:.3f}")
    print(f"\nreference floor at the registered effect {REGISTERED_EFFECT}: n = "
          f"{floor_n():.1f}   (power one half, the same line as the band gate)")

    elig = eligible(games, dests)
    print(f"\neligible at this setting, meaning able to supply the draw in dollars: "
          f"{len(elig)} of {len(dests)}")
    uu = sorted(e["usable"] for e in elig)
    print(f"  usable dollar prices in them: {uu[0]} to {uu[-1]}, "
          f"median {statistics.median(uu):.0f}")

    packed, history = pack_independent(elig)
    pn, pspan = len(packed), span_of(packed)
    counts = sorted(h[0] for h in history)
    ov = project_overlap(packed)
    pns = sorted(e["paid"] for e in packed)
    print(f"\npacked axis, sharing no project at all: {pn} destinations")
    print(f"  {len(history)} seeded restarts returned counts {counts[0]} to {counts[-1]}, "
          f"median {statistics.median(counts):.0f}")
    print(f"  density {pns[0]} to {pns[-1]} (factor {pspan:.0f}), "
          f"median {statistics.median(pns):.0f}")
    print(f"  overlap: {ov['projects_in_more_than_one']} project(s) in more than one, "
          f"{ov['pairs_with_any_overlap']} of {ov['pairs_total']} pairs touching")
    print(f"  reference power at this n: {power_at(pn):.3f}")

    bag = [g["price_cents"] for g in games.values()
           if g.get("price_cents") and g["price_cents"] > 0
           and g.get("price_currency") == "USD"]
    print(f"\nthe plant draws from the carrier's own {len(bag)} dollar prices")

    t0 = time.time()
    rng = random.Random(99)
    one, kept = one_correlation(permuted(games, rng), packed, rng, args.reps)
    unit = time.time() - t0
    projected = unit * args.shuffles * args.plants * 2
    print(f"one permuted correlation over {kept} packed destinations at {args.reps} draws: "
          f"{unit:.2f} s")
    print(f"  {args.plants} plants x {args.shuffles} shuffles, planted and unplanted: "
          f"{projected/60:.1f} min projected")
    if projected > args.budget_seconds:
        print(f"  over the budget of {args.budget_seconds/60:.1f} min; lower --plants, "
              f"--shuffles or --reps, or raise --budget-seconds deliberately")
        raise SystemExit(2)

    slope, planted_r = calibrate(packed, bag, REGISTERED_EFFECT, args.reps, seed=5)
    print(f"\ncalibration: pile slope {slope:.4f} plants a correlation of {planted_r:+.4f} "
          f"against a target magnitude of {REGISTERED_EFFECT}")

    rate, seen = detection_rate(packed, bag, slope, args.reps, args.shuffles,
                                args.plants, seed=5)
    flat, seen_flat = detection_rate(packed, bag, 0.0, args.reps, args.shuffles,
                                     args.plants, seed=6)
    print(f"planted detection rate: {rate:.3f} over {len(seen)} replicates")
    print(f"unplanted detection rate: {flat:.3f} over {len(seen_flat)} replicates "
          f"(alpha is {ALPHA})")

    obs_rng = random.Random(4242)
    r_packed, kp = one_correlation(games, packed, obs_rng, args.reps)
    r_full, kf = one_correlation(games, dests, obs_rng, args.reps)
    print(f"\nobserved, printed as objects and adjudicated nowhere in this file: "
          f"packed {r_packed:+.4f} over {kp}, full {r_full:+.4f} over {kf}")

    knobs = knob_variants(games, members, established)
    print("\nwhat a declared knob would do to the packing:")
    for r in knobs:
        mark = "" if r["keeps_the_axis_purpose"] else "   <- drops the reason for the axis"
        print(f"  established={str(r['established_required']):5s} {r['currency']:15s} "
              f"packed {r['packed']:3d}  reference power {r['reference_power']:.3f}{mark}")

    crit = build_criteria(rate, flat, pn, pspan, ov)
    for c in crit.values():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"  [{flag}] {c['name']} ({c['kind']}): {c['detail']}")

    record = {
        "station": "B30-4",
        "what": ("the combination-market gate: whether an axis of two-tag destinations can "
                 "carry the effect the single-tag axis returned. Resolution is measured by "
                 "planting. No price relation is adjudicated here."),
        "diagnostic_only": True,
        "diagnostic_reason": ("A gate, not a reading. The observed correlations are printed "
                              "as objects and are not scored; the arm they gate is not open."),
        "config": {"sale": GATE_SALE, "currency": GATE_CURRENCY, "equal_n": sweep.EQUAL_N,
                   "reps": args.reps, "shuffles": args.shuffles, "plants": args.plants,
                   "pack_trials": PACK_TRIALS, "pack_seed": PACK_SEED,
                   "registered_effect": REGISTERED_EFFECT, "alpha": ALPHA,
                   "power_floor": POWER_FLOOR, "span_floor": SPAN_FLOOR},
        "reference_floor_n": floor_n(),
        "established_threshold": established,
        "destinations": len(dests),
        "packed_axis": {
            "n": pn, "density_span_factor": pspan, "reference_power": power_at(pn),
            "overlap": ov,
            "restart_counts": {"min": counts[0], "max": counts[-1],
                               "median": statistics.median(counts)},
            "members": [{"a": e["a"], "b": e["b"], "paid": e["paid"],
                         "parent_a": e["parent_a"], "parent_b": e["parent_b"]}
                        for e in sorted(packed, key=lambda e: -e["paid"])],
        },
        "plant": {"slope": slope, "planted_correlation": planted_r,
                  "detection_rate": rate, "unplanted_detection_rate": flat,
                  "replicates": seen, "unplanted_replicates": seen_flat},
        "observed_not_adjudicated": {"packed_axis": r_packed, "full_axis": r_full,
                                     "kept_packed": kp, "kept_full": kf},
        "knob_variants": knobs,
        "criteria": list(crit.values()),
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8",
                   newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] is not False for c in crit.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
