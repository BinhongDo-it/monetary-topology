"""Step three, piece four: does the answer move on a knob, asked before it is read.

**This file computes no verdict and registers no criterion.** It exists because
`11f` says a cell whose sign turns over on a setting the station itself has declared
is not a cell to read, and the only way to know is to turn the settings. The
criterion asks whether the dispersion of a posted price rises as the comparables at
a destination thin out. Five things about that sentence are not fixed by it, and
each of them is a setting this station has already had to declare:

    which dispersion        sd of log price, IQR over median, Gini, MAD over median,
                            coefficient of variation
    which prices            every priced project, or excluding the ones on sale, or
                            excluding only the ones discounted to nothing
    which currencies        dollars alone, every currency at face value, or every
                            currency except the one whose symbol is shared by two
    which density           the tag's project count, or its paid count
    how thin is too thin    a floor on how many posted prices a tag must carry

**The summary is a rank correlation and carries no line.** Reading it against a
threshold would be the shape `D5` and criterion-form rule 11 forbid; what is read
here is whether the sign is the same at every setting, which needs no threshold at
all. **If the sign is stable the reading can be registered; if it turns over, the
sweep itself is the finding and the design has to change.**

**A null is run for a few settings rather than all of them** (`D12`: a run that only
confirms something already argued should be as small as will still catch a mistake).
Prices are shuffled across tags with the tag sizes held, which destroys any relation
between a tag's density and its dispersion while leaving every tag's sample size
exactly as it was. **That separates a real relation from one the sizes produce on
their own**, which matters here because a dispersion computed on twelve prices is a
different object from one computed on four thousand.

Usage::

    python experiments/b30_4_knob_sweep.py --selftest
    python experiments/b30_4_knob_sweep.py
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "results" / "b30_4_itch_prices.json"
COUNTS = ROOT / "results" / "b30_4_itch_counts.json"
OUT = ROOT / "results" / "b30_4_knob_sweep.json"

STATS = ("sd_log", "iqr_over_median", "gini", "mad_over_median", "cv")
SALES = ("all", "no_sale", "no_full_discount")
CURRENCIES = ("usd_only", "all_face_value", "all_but_ambiguous")
DENSITIES = ("tag_total", "tag_paid")
FLOORS = (1, 5, 10, 20)
#: The one setting that is not a knob of the design: how many shuffles the null gets.
#: Reported with its own spread so the null's resolution is visible (`D24`, `D51`).
SHUFFLES = 200


# ----- dispersion, five ways, each on a plain list of positive amounts -----

def sd_log(xs):
    ls = [math.log(x) for x in xs]
    return statistics.stdev(ls) if len(ls) > 1 else None


def iqr_over_median(xs):
    s = sorted(xs)
    med = statistics.median(s)
    if med <= 0 or len(s) < 4:
        return None
    q1, q3 = _quantile(s, 0.25), _quantile(s, 0.75)
    return (q3 - q1) / med


def gini(xs):
    s = sorted(xs)
    n = len(s)
    tot = sum(s)
    if n < 2 or tot <= 0:
        return None
    return (2 * sum((i + 1) * v for i, v in enumerate(s)) / (n * tot)) - (n + 1) / n


def mad_over_median(xs):
    med = statistics.median(xs)
    if med <= 0:
        return None
    return statistics.median([abs(x - med) for x in xs]) / med


def cv(xs):
    if len(xs) < 2:
        return None
    m = statistics.fmean(xs)
    return statistics.stdev(xs) / m if m > 0 else None


DISPERSION = {"sd_log": sd_log, "iqr_over_median": iqr_over_median, "gini": gini,
              "mad_over_median": mad_over_median, "cv": cv}


# ----- a third family: how far the mass piles onto a few price points -----
#
# **The word in the criterion is dispersion and the mechanism under it is anchoring,
# and those are not the same quantity.** Anchoring says a seller looks at the
# comparables and puts the price near them, which predicts that prices land on the
# same few points, not that the range narrows. Width is a proxy for that; the pile
# is the thing itself, and on this carrier it is large: 590 distinct price points
# with a dollar carrying 4,774 of them, five dollars 1,944 and $4.99 1,831.
#
# **A fourth family, the distance to the tag's own modal price, reads the same axis
# from the other side and is included for the same reason.**

def top1_share(xs):
    c = Counter(xs)
    return c.most_common(1)[0][1] / len(xs)


def top3_share(xs):
    c = Counter(xs)
    return sum(v for _, v in c.most_common(3)) / len(xs)


def distinct_per_n(xs):
    return len(set(xs)) / len(xs)


def price_point_entropy(xs):
    c = Counter(xs)
    n = len(xs)
    return -sum((v / n) * math.log(v / n) for v in c.values())


def log_dist_to_mode(xs):
    mode = Counter(xs).most_common(1)[0][0]
    return statistics.fmean([abs(math.log(x / mode)) for x in xs])


CONCENTRATION = {"top1_share": top1_share, "top3_share": top3_share,
                 "distinct_per_n": distinct_per_n,
                 "price_point_entropy": price_point_entropy,
                 "log_dist_to_mode": log_dist_to_mode}

#: Which way each moves if anchoring works: more comparables, tighter pile.
ANCHORING_SIGN = {"top1_share": +1, "top3_share": +1, "distinct_per_n": -1,
                  "price_point_entropy": -1, "log_dist_to_mode": -1}

CONC_REPS = 200   #: used for the observed and for its shuffles alike, see EQUAL_REPS

#: The settings the registered measure is run across. The width family went through
#: the sweep at the top of this file; the pile family had not, and a measure that has
#: only ever been run at one setting has not been checked at all (`11f`).
#: ``restore`` puts a discounted project back to the level it was discounted from,
#: which is the number its seller set, and it is a third option rather than a second
#: because it is neither keeping the sale price nor dropping the project.
REGISTERED_SETTINGS = [("all", "usd_only", False), ("all", "usd_only", True),
                       ("all", "all_face_value", False), ("all", "all_face_value", True),
                       ("no_sale", "usd_only", False), ("no_sale", "all_face_value", False)]


def restored_pool(games, ids, sale, currency):
    """The same pool, with a discounted project put back to its pre-sale level."""
    out = []
    for gid in ids:
        g = games.get(gid)
        if not g or not g.get("price_cents") or g["price_cents"] <= 0:
            continue
        if sale == "no_sale" and g["on_sale"]:
            continue
        if currency == "usd_only" and g["price_currency"] != "USD":
            continue
        c = g["price_cents"]
        if g["on_sale"] and g["sale_pct"] and g["sale_pct"] < 100:
            c = int(round(c / (1 - g["sale_pct"] / 100)))
        out.append(c)
    return out


def genre_entropy(games, ids):
    """How broad a tag is, measured from the genre of each of its paid projects.

    **This replaces the containment pair as the breadth control, and the reason is
    mechanical rather than a preference.** A containment pair sets a tag against a
    subset of itself, and the bigger side's price pool then contains the smaller
    side's pool plus everything else, so it is a mixture and is at least as spread as
    its own component almost by construction. That is set theory, not a market.
    Genre entropy measures breadth directly, on tags that need not be nested at all,
    and it comes free: the listing prints one genre per project and never two.
    """
    gs = [games[g]["genre"] for g in ids
          if games.get(g) and games[g].get("genre") and games[g].get("price_cents")]
    if len(gs) < EQUAL_N:
        return None
    c = Counter(gs)
    n = len(gs)
    return -sum((v / n) * math.log(v / n) for v in c.values())


def concentration_axis(pools, dens, fn, reps, seed):
    rng = random.Random(seed)
    xs, ys = [], []
    for s, p in pools.items():
        if len(p) < EQUAL_N or not dens.get(s):
            continue
        xs.append(dens[s])
        ys.append(statistics.median([fn(rng.sample(p, EQUAL_N)) for _ in range(reps)]))
    return spearman(xs, ys), len(xs)


def terciles(values):
    q = sorted(values)
    return q[len(q) // 3], q[2 * len(q) // 3]


def _quantile(sorted_xs, q):
    if not sorted_xs:
        return None
    pos = (len(sorted_xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_xs[int(pos)]
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


# ----- rank correlation, with ties averaged, and no threshold anywhere -----

def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(a, b):
    if len(a) < 3:
        return None
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return num / (da * db) if da and db else None


# ----- the settings applied to the collected prices -----

def price_pool(games, tag_ids, sale, currency):
    """The posted prices a tag contributes under one setting, in cents."""
    out = []
    for gid in tag_ids:
        g = games.get(gid)
        if not g or g["price_cents"] is None or g["price_cents"] <= 0:
            continue
        if sale == "no_sale" and g["on_sale"]:
            continue
        if sale == "no_full_discount" and g["sale_pct"] == 100:
            continue
        c = g["price_currency"]
        if currency == "usd_only" and c != "USD":
            continue
        if currency == "all_but_ambiguous" and c in (None, "JPY_or_CNY"):
            continue
        out.append(g["price_cents"])
    return out


def one_setting(games, tags, counts, stat, sale, currency, density, floor):
    xs, ys, used = [], [], []
    for slug, t in tags.items():
        pool = price_pool(games, t["ids"], sale, currency)
        if len(pool) < max(floor, 2):
            continue
        d = DISPERSION[stat](pool)
        if d is None:
            continue
        c = counts.get(slug, {}).get("counts", {})
        n = c.get("total") if density == "tag_total" else c.get("paid")
        if not n:
            continue
        xs.append(n)
        ys.append(d)
        used.append((slug, n, d, len(pool)))
    return spearman(xs, ys), len(xs), used


def null_distribution(games, tags, counts, stat, sale, currency, density, floor, seed):
    """Shuffle which game sits under which tag, holding every tag's size.

    A tag's dispersion then has nothing to do with its density while its sample size
    is exactly what it was, so a correlation that survives the shuffle is one the
    sizes produce by themselves.
    """
    rng = random.Random(seed)
    pool_by_tag = {s: price_pool(games, t["ids"], sale, currency) for s, t in tags.items()}
    sizes = {s: len(p) for s, p in pool_by_tag.items()}
    everything = [v for p in pool_by_tag.values() for v in p]
    dens = {}
    for slug in tags:
        c = counts.get(slug, {}).get("counts", {})
        dens[slug] = c.get("total") if density == "tag_total" else c.get("paid")
    out = []
    for _ in range(SHUFFLES):
        rng.shuffle(everything)
        i, xs, ys = 0, [], []
        for slug, k in sizes.items():
            chunk = everything[i:i + k]
            i += k
            if k < max(floor, 2) or not dens.get(slug):
                continue
            d = DISPERSION[stat](chunk)
            if d is None:
                continue
            xs.append(dens[slug])
            ys.append(d)
        r = spearman(xs, ys)
        if r is not None:
            out.append(r)
    return out


# ----- stage two: the size confound removed by design rather than by taste -----

EQUAL_N = 12       #: keeps 148 of 151 tags; the ladder of choices is printed below
EQUAL_REPS = 25    #: draws per tag for the axis and its shuffles, kept equal on both
                   #: sides because noise in a dispersion attenuates a correlation, so
                   #: a null estimated with fewer draws than the observed would be
                   #: pulled toward zero and make the observed look further out
PAIR_REPS = 400    #: draws per tag for the pair tests, measured not chosen
SEEDS = (1, 2, 3, 4, 5)   #: every count below is reported with its spread over these

# **Why the draws are not the same number in both places, and why any of this is here.**
#
# A tag's dispersion at equal n is an estimate, and at 25 draws it is a loose one.
# The pair count at containment 0.50 moved between 7 and 16 of 37 across five
# subsampling seeds, which is wider than the distance from either end to the
# half-way mark, so the count was not measured at all: it was a different number
# every time it was asked. That is `D51`, and it was found by asking twice.
#
# The number of draws it takes to stop moving was measured rather than guessed:
#
#     draws      sd_log        iqr_over_median      gini
#        25      7-16  sd 3.4   11-22  sd 4.4       12-16  sd 2.0
#       100      8-10  sd 0.8   18-21  sd 1.1       11-12  sd 0.5
#       400      8-12  sd 1.6   17-19  sd 0.9       11-15  sd 1.5
#      1200      8-11  sd 1.3   18-20  sd 0.8       11-13  sd 0.8
#
# It settles by a hundred and does not tighten much after four hundred, which is
# where the pair tests sit. **The axis in stage two keeps the lower figure and is
# reported with its spread instead of as a value**, because its shuffles cost two
# hundred runs apiece and it is not the reading: the pair test is.


def equal_n_dispersion(pool, stat, n, reps, seed):
    """Median dispersion over `reps` draws of exactly `n` prices.

    **Every tag contributing the same number of prices is what makes the null flat.**
    Without it a tag with four thousand prices reads wider than one with twelve for
    no reason but the draws, and since a thick tag has more paid projects the density
    axis and the sample size move together. Choosing a statistic that happens to be
    size-neutral would be picking the answer; holding the size removes the question.
    """
    if len(pool) < n:
        return None
    rng = random.Random(seed)
    ds = [DISPERSION[stat](rng.sample(pool, n)) for _ in range(reps)]
    ds = [d for d in ds if d is not None]
    return statistics.median(ds) if ds else None


def equal_n_axis(pools, dens, stat, n, reps, seed):
    xs, ys = [], []
    for s, p in pools.items():
        d = equal_n_dispersion(p, stat, n, reps, seed)
        if d is None or not dens.get(s):
            continue
        xs.append(dens[s])
        ys.append(d)
    return spearman(xs, ys), len(xs)


# ----- stage three: the breadth control, on containment measured not guessed -----

def containment_pairs(sets, pools, th, n):
    """(bigger, smaller) where the smaller sits mostly inside the bigger.

    **A thicker tag is not only a denser market, it is a coarser one**: Horror holds a
    one-dollar jam entry and a thirty-dollar commercial release, a narrow tag holds
    one kind of thing. So a relation across the whole axis cannot tell density from
    breadth. A pair whose smaller side sits inside the bigger holds the subject about
    fixed and varies the density, which is the control. **Containment is measured from
    the collected memberships rather than read off the names**, because the names were
    wrong about it in both directions.
    """
    out = []
    for a, b in itertools.permutations(sorted(sets), 2):
        if len(pools[a]) < n or len(pools[b]) < n:
            continue
        if len(sets[a]) < 2 * len(sets[b]):
            continue
        if sets[b] and len(sets[a] & sets[b]) / len(sets[b]) >= th:
            out.append((a, b))
    return out


def two_sided_binomial(k, n):
    """Exact tail at one half. No line is read against it; it is printed."""
    if n == 0:
        return None
    lo = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(lo + 1)) / 2 ** n)


def pair_test(pairs, disp, inflate=1.0):
    """How often the thinner side is the wider one, which is what branch A predicts.

    `inflate` widens the thinner side by a known factor, which turns the same test
    into a measurement of what this design can see (`D24`: the floor is measured).
    """
    thin = tot = 0
    for a, b in pairs:
        if disp.get(a) is None or disp.get(b) is None:
            continue
        tot += 1
        thin += (disp[b] * inflate) > disp[a]
    return thin, tot, two_sided_binomial(thin, tot)


def build_criteria(equal, conc, held):
    """The station's two criteria, computed from the objects above and not written in.

    **Neither draws a line on an estimate** (criterion-form rule 11): the first asks a
    structural question about the instrument, the second asks whether a sign is the
    same everywhere it was looked at. The sizes are printed in the detail and nothing
    is read against a threshold.
    """
    width = [r for r in equal if r["stat"] in DISPERSION]
    flat = [r for r in width if abs(r["null_mean"]) < 0.10]
    reg = next((r for r in conc if r["stat"] == "price_point_entropy"), None)
    reg_held = next((r for r in held if r["stat"] == "price_point_entropy"), None)

    c1 = {
        "name": "B30-4-1",
        "kind": "instrument",
        "statement": ("with every tag drawing the same number of prices, the shuffle "
                      "null of each width measure sits at zero, which is what says the "
                      "size confound is gone rather than merely smaller"),
        "passed": len(flat) == len(width) and len(width) == len(DISPERSION),
        "detail": ("nulls at equal n: "
                   + ", ".join(f"{r['stat']} {r['null_mean']:+.3f}" for r in width)),
    }

    signs, rhos = [], []
    if reg_held:
        for lab in ("narrow", "middle", "broad"):
            rr = reg_held["by_third"][lab]["rho_total_by_seed"]
            rhos += rr
            signs.append(1 if min(rr) > 0 else -1 if max(rr) < 0 else 0)
    c2 = {
        "name": "B30-4-2",
        "kind": "own_reading",
        "statement": ("the registered measure is price_point_entropy against the "
                      "destination's project count, with breadth held by genre entropy. "
                      "Branch A is a negative sign; the criterion asks whether the sign "
                      "is the same in every third of breadth and across seeds, and the "
                      "sizes are printed rather than read against a line"),
        "passed": bool(signs) and set(signs) == {-1},
        "detail": (
            f"rho by third and seed: {', '.join(f'{r:+.3f}' for r in rhos)}; "
            f"whole axis {min(reg['rho_by_seed']):+.3f} to {max(reg['rho_by_seed']):+.3f} "
            f"against a null of {reg['null_mean']:+.3f} +- {reg['null_sd']:.3f}, "
            f"z {reg['z']:+.1f}. A negative sign is branch A: the price points scatter "
            f"where the comparables thin out, so there is no anchor to attach to"
            if reg else "the registered measure did not return a value"),
    }
    return [c1, c2]


def load():
    p = json.loads(PRICES.read_text(encoding="utf-8"))
    c = json.loads(COUNTS.read_text(encoding="utf-8"))
    return p["games"], p["tags"], {r["slug"]: r for r in c["tags"]}


def selftest():
    """Seed a relation that must be found and a shuffle that must not be."""
    rng = random.Random(7)
    games, tags, counts = {}, {}, {}
    gid = 0
    for i in range(60):
        slug = f"t{i}"
        n = 40 + i * 40                 # density rises with i
        spread = 1.6 - i * 0.02         # dispersion falls as density rises
        ids = []
        for _ in range(30):
            gid += 1
            v = max(1, int(round(math.exp(rng.gauss(2.0, spread)) * 100)))
            games[str(gid)] = {"price_cents": v, "price_currency": "USD",
                               "on_sale": False, "sale_pct": None}
            ids.append(str(gid))
        tags[slug] = {"name": slug, "ids": ids}
        counts[slug] = {"counts": {"total": n, "paid": n // 10}}

    r, k, _ = one_setting(games, tags, counts, "sd_log", "all", "usd_only", "tag_total", 5)
    assert r is not None and k == 60, f"the seeded axis did not come through: {r}, {k}"
    assert r < -0.5, f"a planted falling relation read {r}, which is not it"
    print(f"  planted relation found: rho {r:+.3f} over {k} tags")

    nulls = null_distribution(games, tags, counts, "sd_log", "all", "usd_only",
                              "tag_total", 5, seed=1)
    lo, hi = min(nulls), max(nulls)
    assert lo < 0 < hi or abs(statistics.fmean(nulls)) < 0.25, (
        f"the shuffle kept a relation it should have destroyed: mean {statistics.fmean(nulls):+.3f}")
    assert r < lo, f"the planted relation sits inside its own null: {r} against {lo}"
    print(f"  shuffle destroys it: null mean {statistics.fmean(nulls):+.3f}, "
          f"range {lo:+.3f} to {hi:+.3f}, and the planted value sits outside it")

    # And a case with no relation at all must not produce one.
    for slug in tags:
        for g in tags[slug]["ids"]:
            games[g]["price_cents"] = max(1, int(round(math.exp(rng.gauss(2.0, 1.0)) * 100)))
    r2, _, _ = one_setting(games, tags, counts, "sd_log", "all", "usd_only", "tag_total", 5)
    assert abs(r2) < 0.4, f"a flat construction read {r2}"
    print(f"  flat construction reads rho {r2:+.3f}, which is no relation")

    # The size confound, planted on purpose, and planted with the real prices.
    #
    # **A synthetic price distribution will not reproduce it**, which was found by
    # trying: draws whose log is exactly Gaussian give a sample standard deviation
    # that barely moves with n, so a lognormal plant reads near zero and a probe
    # built on one passes without testing anything. The bias lives in the shape of
    # the real prices, which pile on a few round points (a dollar, five dollars,
    # $4.99, two dollars) over 590 distinct values and reach to five figures. So the
    # probe keeps the real prices and plants only the link between a tag's density
    # and how many prices it draws, which is the confound itself.
    #
    # Sizes span twelve to four thousand, matching the range on the disk. A narrower
    # plant reads weaker, and the assertion below says so rather than passing hollow.
    real = [g["price_cents"] for g in load()[0].values()
            if g.get("price_cents") and g.get("price_currency") == "USD"]
    assert len(real) > 1000, "the probe needs the collected prices and did not find them"
    # **The comparison is paired and repeated, because a single rank correlation over
    # sixty points carries a sampling error near 0.13 and asserting one against a line
    # is the shape criterion-form rule 11 forbids.** It was written that way first and
    # the assertion fired on noise twice. What is asserted instead is the gap between
    # the naive axis and the same axis at equal n, on the same planted data, averaged
    # over a few plants.
    naives, helds = [], []
    for seed in range(5):
        rng2 = random.Random(11 + seed)
        g2, t2, c2, pools2, dens2 = {}, {}, {}, {}, {}
        gid = 0
        for i in range(60):
            slug = f"s{i}"
            n_prices = int(round(12 * (1.1025 ** i)))
            density = int(round(100 * (1.1025 ** i)))
            ids = []
            for _ in range(n_prices):
                gid += 1
                g2[str(gid)] = {"price_cents": rng2.choice(real), "price_currency": "USD",
                                "on_sale": False, "sale_pct": None}
                ids.append(str(gid))
            t2[slug] = {"name": slug, "ids": ids}
            c2[slug] = {"counts": {"total": density, "paid": n_prices}}
            pools2[slug] = [g2[x]["price_cents"] for x in ids]
            dens2[slug] = density
        naives.append(one_setting(g2, t2, c2, "sd_log", "all", "usd_only", "tag_total", 2)[0])
        helds.append(equal_n_axis(pools2, dens2, "sd_log", EQUAL_N, EQUAL_REPS, seed)[0])

    mn, mh = statistics.fmean(naives), statistics.fmean(helds)
    assert mn - mh > 0.10, (
        f"the planted size confound did not show up as a gap ({mn:+.3f} against "
        f"{mh:+.3f}), so this probe is not testing what it claims to")
    assert abs(mh) < 0.15, f"holding the sample size left a relation: {mh:+.3f}"
    print(f"  planted size confound, real prices and synthetic sizes, 5 plants: "
          f"naive axis {mn:+.3f}, same axis at equal n {mh:+.3f}")

    # The pair test must read a planted widening and must not read a coin flip.
    sets2 = {s: set(t2[s]["ids"]) for s in t2}
    disp2 = {s: equal_n_dispersion(p, "sd_log", EQUAL_N, EQUAL_REPS, 5)
             for s, p in pools2.items()}
    fake = [(f"s{i}", f"s{j}") for i in range(30, 60) for j in (i - 30,)]
    t_, n_, p_ = pair_test(fake, disp2)
    assert p_ > 0.05, f"a pair test on interchangeable tags read a relation: {t_}/{n_}, p {p_}"
    t2_, n2_, p2_ = pair_test(fake, disp2, inflate=1.5)
    assert p2_ < 0.01 and t2_ > n2_ * 0.8, (
        f"the pair test missed a planted 1.5x widening: {t2_}/{n2_}, p {p2_}")
    print(f"  pair test: interchangeable tags {t_}/{n_} p {p_:.2f}, "
          f"a planted 1.5x widening {t2_}/{n2_} p {p2_:.3f}")

    # The pile measures. A thick market that copies lands on a few points; a thin one
    # with nothing to copy scatters. Plant exactly that and require it to be found,
    # then plant nothing and require it not to be. Both tags draw the same number of
    # prices, so nothing here can be the sample size.
    rng3 = random.Random(23)
    FOCAL = [100, 299, 499]
    SPREAD = [100 * k for k in range(1, 41)]
    piled, flat_, dens3 = {}, {}, {}
    for i in range(60):
        s = f"c{i}"
        dens3[s] = 100 + i * 100
        tight = i / 59.0                      # thicker tags pile harder
        piled[s] = [rng3.choice(FOCAL) if rng3.random() < tight else rng3.choice(SPREAD)
                    for _ in range(60)]
        flat_[s] = [rng3.choice(SPREAD) for _ in range(60)]
    got, _ = concentration_axis(piled, dens3, price_point_entropy, 100, 1)
    none_, _ = concentration_axis(flat_, dens3, price_point_entropy, 100, 1)
    assert got < -0.5, f"a planted pile was not found: entropy against density {got:+.3f}"
    assert abs(none_) < 0.25, f"a construction with no pile read {none_:+.3f}"
    print(f"  planted pile: entropy against density {got:+.3f}; with no pile planted "
          f"{none_:+.3f}")

    # And the breadth measure must read breadth. One genre or many, nothing else.
    g3 = {}
    narrow = {f"n{i}": [] for i in range(3)}
    for i, s in enumerate(narrow):
        ids = []
        for j in range(30):
            k = f"{s}-{j}"
            g3[k] = {"genre": "Puzzle", "price_cents": 100}
            ids.append(k)
        narrow[s] = ids
    wide_ids = []
    for j in range(30):
        k = f"w-{j}"
        g3[k] = {"genre": f"G{j % 10}", "price_cents": 100}
        wide_ids.append(k)
    e_narrow = genre_entropy(g3, narrow["n0"])
    e_wide = genre_entropy(g3, wide_ids)
    assert e_narrow is not None and e_wide is not None
    assert e_narrow < 0.01 < e_wide, (
        f"the breadth measure did not separate one genre from ten: "
        f"{e_narrow:.3f} against {e_wide:.3f}")
    print(f"  breadth measure: one genre reads {e_narrow:.3f}, ten read {e_wide:.3f}")

    # The criteria have to be able to fail (`11f`), so each is fed an input that
    # should turn it over and asserted to turn over.
    good_equal = [{"stat": s, "null_mean": -0.02} for s in DISPERSION]
    bad_equal = [{"stat": s, "null_mean": (0.45 if s == "gini" else -0.02)}
                 for s in DISPERSION]
    reg = [{"stat": "price_point_entropy", "rho_by_seed": [-0.28, -0.26],
            "null_mean": -0.02, "null_sd": 0.09, "z": -2.8}]
    def held_with(signs):
        return [{"stat": "price_point_entropy",
                 "by_third": {lab: {"rho_total_by_seed": [v, v - 0.01]}
                              for lab, v in zip(("narrow", "middle", "broad"), signs)}}]
    assert build_criteria(good_equal, reg, held_with([-0.2, -0.4, -0.2]))[0]["passed"]
    assert not build_criteria(bad_equal, reg, held_with([-0.2, -0.4, -0.2]))[0]["passed"], \
        "B30-4-1 did not fail on a displaced null"
    assert build_criteria(good_equal, reg, held_with([-0.2, -0.4, -0.2]))[1]["passed"]
    assert not build_criteria(good_equal, reg, held_with([-0.2, +0.4, -0.2]))[1]["passed"], \
        "B30-4-2 did not fail on a sign that turns over between thirds"
    assert not build_criteria(good_equal, reg, held_with([-0.2, 0.005, -0.2]))[1]["passed"], \
        "B30-4-2 did not fail on a third that straddles zero"
    print("  both criteria flip when fed an input that should flip them")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    games, tags, counts = load()
    print(f"{len(games):,} paid projects, {len(tags)} market tags\n")

    rows = []
    for stat, sale, cur, den, floor in itertools.product(
            STATS, SALES, CURRENCIES, DENSITIES, FLOORS):
        r, k, _ = one_setting(games, tags, counts, stat, sale, cur, den, floor)
        rows.append({"stat": stat, "sale": sale, "currency": cur, "density": den,
                     "floor": floor, "rho": r, "tags_used": k})

    got = [x for x in rows if x["rho"] is not None]
    neg = [x for x in got if x["rho"] < 0]
    pos = [x for x in got if x["rho"] > 0]
    print(f"{len(got)} of {len(rows)} settings produced a value")
    print(f"   negative (dispersion falls as the market thickens): {len(neg)}")
    print(f"   positive: {len(pos)}")
    if got:
        s = sorted(x["rho"] for x in got)
        print(f"   rho runs {s[0]:+.3f} to {s[-1]:+.3f}, median {s[len(s)//2]:+.3f}")

    print("\n  by dispersion measure, and by each other setting, so a mover is visible:")
    for key, values in (("stat", STATS), ("sale", SALES), ("currency", CURRENCIES),
                        ("density", DENSITIES), ("floor", FLOORS)):
        print(f"\n   {key}")
        for v in values:
            sub = [x["rho"] for x in got if x[key] == v]
            if not sub:
                continue
            sub.sort()
            sign = ("all negative" if sub[-1] < 0 else
                    "all positive" if sub[0] > 0 else "BOTH SIGNS")
            print(f"      {str(v):18s} n={len(sub):>3d}  {sub[0]:+.3f} to {sub[-1]:+.3f}"
                  f"   median {sub[len(sub)//2]:+.3f}   {sign}")

    # The null, for the settings at the two ends of the sweep and for one middle
    # one, rather than for all of them.
    got.sort(key=lambda x: x["rho"])
    picks = [got[0], got[len(got) // 2], got[-1]]
    nulls_out = []
    print(f"\n  the shuffle, {SHUFFLES} draws, for the lowest, middle and highest setting:")
    for p in picks:
        ns = null_distribution(games, tags, counts, p["stat"], p["sale"], p["currency"],
                               p["density"], p["floor"], seed=11)
        m, sd = statistics.fmean(ns), statistics.stdev(ns)
        z = (p["rho"] - m) / sd if sd else None
        nulls_out.append({**p, "null_mean": m, "null_sd": sd, "null_min": min(ns),
                          "null_max": max(ns), "z": z, "shuffles": SHUFFLES})
        print(f"      {p['stat']:16s} {p['sale']:16s} {p['currency']:18s} "
              f"{p['density']:10s} floor {p['floor']:>2d}")
        print(f"          observed {p['rho']:+.3f}   null {m:+.3f} +- {sd:.3f} "
              f"(range {min(ns):+.3f} to {max(ns):+.3f})   "
              f"{'z ' + format(z, '+.1f') if z is not None else ''}")

    # ---- stage two: the same axis with every tag contributing the same n ----
    pools = {s: price_pool(games, t["ids"], "all", "usd_only") for s, t in tags.items()}
    dens_total = {s: counts.get(s, {}).get("counts", {}).get("total") for s in tags}
    equal = []
    print(f"\n  the same axis with every tag contributing exactly {EQUAL_N} prices, "
          f"median of {EQUAL_REPS} draws, observed over {len(SEEDS)} seeds:")
    print(f"      {'statistic':18s}{'observed range':>18s}{'null mean':>11s}"
          f"{'null sd':>9s}{'z of the mean':>15s}")
    for st in STATS:
        seeded = [equal_n_axis(pools, dens_total, st, EQUAL_N, EQUAL_REPS, s)[0]
                  for s in SEEDS]
        r, k = statistics.fmean(seeded), equal_n_axis(
            pools, dens_total, st, EQUAL_N, EQUAL_REPS, SEEDS[0])[1]
        ns = []
        everything = [v for p in pools.values() for v in p]
        rs = random.Random(202)
        for _ in range(SHUFFLES):
            rs.shuffle(everything)
            i, sh = 0, {}
            for s, p in pools.items():
                sh[s] = everything[i:i + len(p)]
                i += len(p)
            rr, _ = equal_n_axis(sh, dens_total, st, EQUAL_N, EQUAL_REPS, 303)
            if rr is not None:
                ns.append(rr)
        mu, sd = statistics.fmean(ns), statistics.stdev(ns)
        equal.append({"stat": st, "rho_mean": r, "rho_by_seed": seeded, "tags": k,
                      "null_mean": mu, "null_sd": sd,
                      "z_of_mean": (r - mu) / sd if sd else None})
        print(f"      {st:18s}{min(seeded):>+9.3f} to {max(seeded):>+.3f}"
              f"{mu:>+11.3f}{sd:>9.3f}{(r - mu) / sd:>+15.1f}   (tags {k})")

    # ---- stage three: the breadth control over the containment ladder ----
    sets = {s: set(t["ids"]) for s, t in tags.items()}
    disp_by_seed = {st: {sd: {s: equal_n_dispersion(p, st, EQUAL_N, PAIR_REPS, sd)
                              for s, p in pools.items()}
                         for sd in SEEDS} for st in STATS}
    ladder = []
    print(f"\n  the breadth control by containment. SUPERSEDED 2026-09-17 by the genre"
          f"\n  measure below: a tag's pool contains its subset's pool plus everything"
          f"\n  else, so the bigger side is a mixture and at least as spread almost by"
          f"\n  construction. Kept because the numbers are real and the bias has a"
          f"\n  direction. Branch A predicts the thinner side is the wider one:")
    print(f"      {'contain >=':>11s}{'pairs':>7s}{'parents':>9s}  " +
          "  ".join(f"{st[:13]:>15s}" for st in STATS))
    for th in (0.30, 0.40, 0.50, 0.60, 0.70):
        ps = containment_pairs(sets, pools, th, EQUAL_N)
        row = {"containment": th, "pairs": len(ps),
               "distinct_bigger_sides": len({a for a, _ in ps}), "by_stat": {}}
        line = f"      {th:>11.2f}{len(ps):>7d}{row['distinct_bigger_sides']:>9d}  "
        for st in STATS:
            got = [pair_test(ps, disp_by_seed[st][sd]) for sd in SEEDS]
            ts = [g[0] for g in got]
            n = got[0][1]
            row["by_stat"][st] = {"thinner_wider_by_seed": ts, "pairs_scored": n,
                                  "p_by_seed": [g[2] for g in got]}
            line += f"  {min(ts):>3d}-{max(ts):<3d}/{n:<3d} p {max(g[2] for g in got):.2f}"
        ladder.append(row)
        print(line)

    # ---- stage four: what this design could see, measured by planting it ----
    resolution = []
    print(f"\n  what it would see. The thinner side is widened by a known factor and the"
          f"\n  same test rerun, so the floor is measured rather than declared (`D24`):")
    for th in (0.40, 0.50):
        ps = containment_pairs(sets, pools, th, EQUAL_N)
        print(f"      containment >= {th:.2f}, {len(ps)} pairs")
        print(f"         {'widened by':>11s}  " + "  ".join(f"{st[:13]:>15s}" for st in STATS))
        for infl in (1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.50):
            row = {"containment": th, "inflation": infl, "by_stat": {}}
            line = f"         {infl:>10.2f}x  "
            for st in STATS:
                got = [pair_test(ps, disp_by_seed[st][sd], inflate=infl) for sd in SEEDS]
                ts = [g[0] for g in got]
                n = got[0][1]
                row["by_stat"][st] = {"thinner_wider_by_seed": ts, "pairs_scored": n,
                                      "p_by_seed": [g[2] for g in got]}
                line += f"  {min(ts):>3d}-{max(ts):<3d} p {max(g[2] for g in got):.2f}"
            resolution.append(row)
            print(line)

    # ---- stage five: the pile on price points, with breadth measured directly ----
    #
    # The criterion says dispersion and the mechanism it tests is anchoring, and a
    # seller who copies a comparable lands on the same price point rather than inside
    # the same range. So this reads the pile, and it reads breadth off the genre of
    # every paid project instead of off a containment pair.
    breadth = {s: genre_entropy(games, t["ids"]) for s, t in tags.items()}
    breadth = {s: v for s, v in breadth.items() if v is not None}
    dens_paid = {s: counts.get(s, {}).get("counts", {}).get("paid") for s in tags}
    conc = []
    print(f"\n  the pile on price points, every tag drawing {EQUAL_N} prices, "
          f"{CONC_REPS} draws, observed over {len(SEEDS)} seeds.")
    print(f"  Anchoring predicts a tighter pile where comparables are thicker, which is"
          f"\n  a positive sign for the share measures and a negative one for the rest:")
    print(f"      {'statistic':22s}{'anchoring':>10s}{'observed range':>20s}"
          f"{'null mean':>11s}{'null sd':>9s}{'z':>7s}")
    everything = [v for p in pools.values() for v in p]
    # One shuffle serves every measure, because the shuffled pools do not depend on
    # which measure reads them. Written the other way this stage cost five times as
    # much for the same numbers.
    nulls_by_stat = {nm: [] for nm in CONCENTRATION}
    rs = random.Random(9)
    for _ in range(100):
        rs.shuffle(everything)
        i, sh = 0, {}
        for s, p in pools.items():
            sh[s] = everything[i:i + len(p)]
            i += len(p)
        rng = random.Random(1)
        draws = {s: [rng.sample(p, EQUAL_N) for _ in range(CONC_REPS)]
                 for s, p in sh.items() if len(p) >= EQUAL_N and dens_total.get(s)}
        for nm, fn in CONCENTRATION.items():
            xs = [dens_total[s] for s in draws]
            ys = [statistics.median([fn(d) for d in draws[s]]) for s in draws]
            r = spearman(xs, ys)
            if r is not None:
                nulls_by_stat[nm].append(r)
    obs_by_stat = {}
    for s_ in SEEDS:
        rng = random.Random(s_)
        draws = {s: [rng.sample(p, EQUAL_N) for _ in range(CONC_REPS)]
                 for s, p in pools.items() if len(p) >= EQUAL_N and dens_total.get(s)}
        for nm, fn in CONCENTRATION.items():
            xs = [dens_total[s] for s in draws]
            ys = [statistics.median([fn(d) for d in draws[s]]) for s in draws]
            obs_by_stat.setdefault(nm, []).append(spearman(xs, ys))
    for nm, fn in CONCENTRATION.items():
        obs = obs_by_stat[nm]
        ns = nulls_by_stat[nm]
        mu, sd = statistics.fmean(ns), statistics.stdev(ns)
        z = (statistics.fmean(obs) - mu) / sd if sd else None
        conc.append({"stat": nm, "anchoring_sign": ANCHORING_SIGN[nm],
                     "rho_by_seed": obs, "null_mean": mu, "null_sd": sd, "z": z})
        print(f"      {nm:22s}{ANCHORING_SIGN[nm]:>+10d}"
              f"{min(obs):>+11.3f} to {max(obs):>+.3f}{mu:>+11.3f}{sd:>9.3f}{z:>+7.1f}")

    # Breadth held directly, in thirds, for the measures whose null sits at zero.
    common = [s for s in pools if s in breadth and dens_total.get(s)
              and len(pools[s]) >= EQUAL_N]
    c1, c2 = terciles([breadth[s] for s in common])
    held = []
    print(f"\n  breadth held in thirds of genre entropy, {len(common)} tags, "
          f"thirds at {c1:.2f} and {c2:.2f}:")
    draws_by_seed = {}
    for sd_ in SEEDS[:3]:
        rng = random.Random(sd_)
        draws_by_seed[sd_] = {s: [rng.sample(pools[s], EQUAL_N) for _ in range(CONC_REPS)]
                              for s in common}
    # **Both families go through this stage, and the width family only arrived here
    # after the containment control was withdrawn.** While containment was the control
    # the width measures looked flat; held against a measured breadth they turn over
    # between one third and the next, which is `11f` and means they are not read.
    for nm, fn in {**DISPERSION, **CONCENTRATION}.items():
        d = {sd_: {s: statistics.median([fn(x) for x in draws_by_seed[sd_][s]])
                   for s in common} for sd_ in SEEDS[:3]}
        row = {"stat": nm, "family": "width" if nm in DISPERSION else "pile",
               "vs_breadth": spearman([breadth[s] for s in common],
                                                  [d[SEEDS[0]][s] for s in common]),
               "by_third": {}}
        line = f"      {nm:22s} against breadth {row['vs_breadth']:+.3f}   "
        for lab, f in (("narrow", lambda v: v <= c1), ("middle", lambda v: c1 < v <= c2),
                       ("broad", lambda v: v > c2)):
            sub = [s for s in common if f(breadth[s])]
            rr = [spearman([dens_total[s] for s in sub], [d[sd_][s] for s in sub])
                  for sd_ in SEEDS[:3]]
            rp = [spearman([dens_paid[s] for s in sub if dens_paid.get(s)],
                           [d[sd_][s] for s in sub if dens_paid.get(s)])
                  for sd_ in SEEDS[:3]]
            row["by_third"][lab] = {"n": len(sub), "rho_total_by_seed": rr,
                                    "rho_paid_by_seed": rp}
            line += f" {lab} {min(rr):+.2f}/{max(rr):+.2f}"
        # A measure whose sign is not the same in all three thirds is turning over on
        # a declared setting, which `11f` says is not a cell to read.
        signs = {1 if min(row["by_third"][l]["rho_total_by_seed"]) > 0 else
                 -1 if max(row["by_third"][l]["rho_total_by_seed"]) < 0 else 0
                 for l in ("narrow", "middle", "broad")}
        row["sign_stable_across_thirds"] = (len(signs) == 1 and 0 not in signs)
        held.append(row)
        print(line + ("" if row["sign_stable_across_thirds"] else "   TURNS OVER"))

    # The registered measure across the settings the sweep never ran it on.
    reg_settings = []
    print(f"\n  the registered measure across its own settings. Branch A is a negative"
          f"\n  sign, so the question is whether any setting turns it over:")
    print(f"      {'sale':10s}{'currency':17s}{'restore':9s}{'tags':>6s}"
          f"{'whole axis':>20s}{'narrow':>15s}{'middle':>15s}{'broad':>15s}")
    for sale, cur, restore in REGISTERED_SETTINGS:
        pl = {s: (restored_pool(games, t["ids"], sale, cur) if restore
                  else price_pool(games, t["ids"], sale, cur))
              for s, t in tags.items()}
        use = [s for s in pl if len(pl[s]) >= EQUAL_N and dens_total.get(s) and s in breadth]
        if len(use) < 10:
            continue
        t1, t2 = terciles([breadth[s] for s in use])
        d = {}
        for sd_ in SEEDS[:3]:
            rng = random.Random(sd_)
            d[sd_] = {s: statistics.median(
                [price_point_entropy(rng.sample(pl[s], EQUAL_N)) for _ in range(CONC_REPS)])
                for s in use}
        whole = [spearman([dens_total[s] for s in use], [d[sd_][s] for s in use])
                 for sd_ in SEEDS[:3]]
        row = {"sale": sale, "currency": cur, "restore_pre_sale_price": restore,
               "tags": len(use), "whole_axis_by_seed": whole, "by_third": {}}
        line = (f"      {sale:10s}{cur:17s}{str(restore):9s}{len(use):>6d}"
                f"{min(whole):>+10.3f}/{max(whole):<+9.3f}")
        for lab, f in (("narrow", lambda v: v <= t1), ("middle", lambda v: t1 < v <= t2),
                       ("broad", lambda v: v > t2)):
            sub = [s for s in use if f(breadth[s])]
            rr = [spearman([dens_total[s] for s in sub], [d[sd_][s] for s in sub])
                  for sd_ in SEEDS[:3]]
            row["by_third"][lab] = rr
            line += f"{min(rr):>+8.2f}/{max(rr):<+6.2f}"
        reg_settings.append(row)
        print(line)
    allv = [v for r in reg_settings for v in r["whole_axis_by_seed"]
            + [x for lab in r["by_third"] for x in r["by_third"][lab]]]
    print(f"      -> {len(allv)} values over {len(reg_settings)} settings, "
          f"{sum(1 for v in allv if v < 0)} negative, "
          f"range {min(allv):+.3f} to {max(allv):+.3f}")

    criteria = build_criteria(equal, conc, held)
    print("\n  criteria, computed from the objects above:")
    for c in criteria:
        print(f"      {'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]")
        print(f"            {c['detail'][:150]}")

    record = {
        "station": "B30-4",
        "criteria": criteria,
        "registered_measure_settings": reg_settings,
        "concentration": {"reps": CONC_REPS, "by_stat": conc,
                          "breadth_held": held,
                          "breadth_thirds": [c1, c2],
                          "breadth_measure": "genre entropy over the tag's paid projects"},
        "containment_superseded": ("the containment ladder above is kept for its numbers "
                                   "and is not the breadth control: a tag's pool contains "
                                   "its subset's pool plus everything else, so the bigger "
                                   "side is a mixture and at least as spread almost by "
                                   "construction"),
        "what": ("step three piece four: whether the sign of the dispersion against "
                 "density relation turns over on the settings this station has declared, "
                 "then the same axis with the sample size held, then the breadth control "
                 "over a containment ladder, then what the design could see"),
        "equal_n": {"n": EQUAL_N, "reps": EQUAL_REPS, "pair_reps": PAIR_REPS,
                    "seeds": list(SEEDS), "by_stat": equal},
        "containment_ladder": ladder,
        "resolution": resolution,
        "this_is_not_a_reading": True,
        "knobs": {"stat": list(STATS), "sale": list(SALES), "currency": list(CURRENCIES),
                  "density": list(DENSITIES), "floor": list(FLOORS)},
        "settings": rows,
        "sign_split": {"negative": len(neg), "positive": len(pos), "no_value": len(rows) - len(got)},
        "nulls": nulls_out,
        "shuffles": SHUFFLES,
        "diagnostic_only": False,
        "diagnostic_reason": ("Carries the station's registered reading as of 2026-09-17. "
                              "The sweep and the ladders inside it remain diagnostic; the "
                              "two criteria are not."),
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    print("Nothing here is a reading. What it answers is whether one can be taken.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
