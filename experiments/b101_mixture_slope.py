"""B101 arm: is the share-mix slope a technology parameter, or an average over
whichever classes a country staffs that industry with?

`B101-11` records that the rival's restriction holds on this panel: footnote 20
prints `sigma_ijt = alpha_ij + beta_j ln(K/L)`, the slope carrying industry and
no country, and the cross-country spread of the fitted slope sits at the floor
built from each country's own two halves.  That criterion is deliberately not
scored, because this frame makes no competing point prediction about a slope.

This arm asks the question the frame does have a claim on.  If the price a class
is paid at a position is class-dependent, and `B106` measures exactly that on
these economies, then the labour share at a position is a composition-weighted
average rather than a scalar property of the position.  The fitted slope is then
a functional of the class mixture, bounded by the class-specific slopes and
placed inside that range by the mixture.  So it is not that there is no slope
and not that the slope is arbitrary: **there is a range, and where the position
sits inside it is set by a state that moves slowly.**

That has a consequence this panel can read.  Across the countries of one
industry, the spread of the fitted slope should be larger where the countries
staff that industry with more different mixtures.  Under the rival's reading
the slope is a technology parameter and carries no such term, so the relation
is flat.

Both sides are built the same way and neither carries an invented constant.  The
spread of a quantity across the countries of an industry is divided by a floor
built from each country's own two halves, so a panel with no cross-country
component reads one on both axes.

Nothing is fetched: `b101_klems_basic.npz` and `b106_labour.npz` are both on
disk, and the fitting routine is imported from the arm that registered it rather
than written a second time.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b101_beta_dispersion as BD          # noqa: E402  the registered fit

LABOUR = ROOT / "data" / "cache" / "b106_labour.npz"
OUT = ROOT / "results" / "b101_mixture_slope.json"

#: `B106`'s own separability step excludes these by name: they are aggregates
#: over sections rather than sections, so a country's mixture in them is a
#: mixture of mixtures and not comparable with a section's.
AGGREGATES = {"M-N", "MARKT", "NMARKT", "TOT", "TOT_IND"}

MIN_COUNTRIES = BD.MIN_COUNTRIES
MIN_YEARS_COMP = 6        # a country needs two halves of three years to give a floor


def tv(p, q):
    """Total variation distance between two composition vectors.  Scale free,
    bounded in [0, 1], and it needs no constant."""
    return 0.5 * float(np.abs(p - q).sum())


def compositions(path=LABOUR):
    """(industry, country) -> {year: 18-vector of employment shares, normalised}."""
    z = np.load(path, allow_pickle=True)
    nace, geo, year, cls = (z["nace"].tolist(), z["geo"].tolist(),
                            z["year"].tolist(), z["cls"].tolist())
    share = z["share_e"].tolist()
    classes = sorted(set(cls))
    idx = {c: i for i, c in enumerate(classes)}
    cells = collections.defaultdict(lambda: np.zeros(len(classes)))
    for i in range(len(nace)):
        cells[(nace[i], geo[i], int(year[i]))][idx[cls[i]]] += share[i]
    out = collections.defaultdict(dict)
    for (n, g, y), v in cells.items():
        s = v.sum()
        if s > 0:
            out[(n, g)][y] = v / s
    return dict(out), classes


def spread_over_floor(values, halves):
    """The same shape both axes use: how far apart the countries are, over how
    far apart one country is from itself.  A panel with no cross-country
    component reads one."""
    if len(values) < MIN_COUNTRIES or not halves:
        return None
    across = float(np.median(np.abs(np.asarray(values) -
                                    np.median(values)))) * 1.4826
    within = float(np.median(np.abs(np.asarray(halves)))) / np.sqrt(2.0)
    if within <= 0:
        return None
    return across / within, across, within


def composition_axis(comp, industry, countries):
    """Across: median pairwise distance between countries' mean mixtures.
    Within: each country's own first half against its own second half."""
    means, halves = {}, []
    for g in countries:
        ys = comp.get((industry, g))
        if not ys or len(ys) < MIN_YEARS_COMP:
            continue
        ts = sorted(ys)
        means[g] = np.mean([ys[t] for t in ts], axis=0)
        m = len(ts) // 2
        a = np.mean([ys[t] for t in ts[:m]], axis=0)
        b = np.mean([ys[t] for t in ts[m:]], axis=0)
        halves.append(tv(a, b))
    gs = sorted(means)
    if len(gs) < MIN_COUNTRIES or not halves:
        return None
    pairs = [tv(means[a], means[b])
             for i, a in enumerate(gs) for b in gs[i + 1:]]
    within = float(np.median(halves)) / np.sqrt(2.0)
    if within <= 0:
        return None
    return float(np.median(pairs)) / within, float(np.median(pairs)), within, gs


def spearman(x, y):
    """Rank correlation, written out so the reading carries no import that has
    to be checked for a tie convention."""
    def rank(v):
        order = np.argsort(np.argsort(v))
        return order.astype(float)
    rx, ry = rank(np.asarray(x, float)), rank(np.asarray(y, float))
    rx -= rx.mean(); ry -= ry.mean()
    d = float(np.sqrt((rx * rx).sum() * (ry * ry).sum()))
    return float((rx * ry).sum() / d) if d > 0 else None


def build(S, comp, industries=None):
    full, halves, _ = BD.betas(S)
    by_ind = collections.defaultdict(dict)
    half_by_g = collections.defaultdict(dict)
    for (n, g), (b, _se) in full.items():
        by_ind[n][g] = b
    for (n, g), (a, b) in halves.items():
        half_by_g[n][g] = a - b

    rows = []
    for n in sorted(by_ind):
        if n in AGGREGATES:
            continue
        if industries is not None and n not in industries:
            continue
        gs_beta = sorted(by_ind[n])
        ca = composition_axis(comp, n, gs_beta)
        if ca is None:
            continue
        comp_ratio, comp_across, comp_within, matched = ca
        bvals = [by_ind[n][g] for g in matched]
        #: the floor is built on the SAME countries the spread is built on.
        #: Taking it over every country in the industry would put the two
        #: sides of one ratio on two populations, which is the sixth category
        #: error, and it is invisible in the output: the ratio still prints.
        mhalves = [half_by_g[n][g] for g in matched if g in half_by_g[n]]
        sf = spread_over_floor(bvals, mhalves)
        if sf is None:
            continue
        beta_ratio, beta_across, beta_within = sf
        rows.append({"nace": n, "countries_matched": len(matched),
                     "beta_ratio": beta_ratio, "beta_across": beta_across,
                     "beta_within": beta_within,
                     "comp_ratio": comp_ratio, "comp_across": comp_across,
                     "comp_within": comp_within,
                     "median_beta": float(np.median(bvals))})
    return rows


def criteria(rows):
    n = len(rows)
    joined = n >= MIN_COUNTRIES
    worst = min((r["countries_matched"] for r in rows), default=0)
    rho = (spearman([r["comp_ratio"] for r in rows],
                    [r["beta_ratio"] for r in rows]) if n >= 3 else None)
    #: With this many industries the rank correlation's own scale is about
    #: 1/sqrt(n-1), so the reading is printed against it and no line is drawn.
    se = (1.0 / np.sqrt(n - 1)) if n > 1 else None
    return [
        {"name": "B101-36", "kind": "instrument",
         "text": "The two caches join on (industry, country) and every industry "
                 "read carries at least the minimum countries on both sides, "
                 "with the matched count printed per industry rather than a "
                 "mean over them.",
         "passed": bool(joined and worst >= MIN_COUNTRIES),
         "detail": "%d industries joined, fewest matched countries in any of "
                   "them %d, minimum required %d"
                   % (n, worst, MIN_COUNTRIES)},
        {"name": "B101-37", "kind": "own_reading",
         "text": "The relation between how differently the countries of an "
                 "industry staff it and how far apart their fitted slopes are. "
                 "Printed against the rank correlation's own scale, with no "
                 "line drawn on it.",
         "passed": rho is not None,
         "detail": "rank correlation %s across %d industries, its own scale "
                   "about %s; composition ratio median %.3f, slope ratio "
                   "median %.3f"
                   % (("%+.4f" % rho) if rho is not None else "none", n,
                      ("%.3f" % se) if se else "none",
                      float(np.median([r["comp_ratio"] for r in rows])) if rows else float("nan"),
                      float(np.median([r["beta_ratio"] for r in rows])) if rows else float("nan"))},
        {"name": "B101-38", "kind": "bookkeeping",
         "text": "Every industry read is named with both of its axes and both "
                 "of its floors, so a reader can rebuild either axis without "
                 "this script.",
         "passed": all(set(r) >= {"nace", "beta_across", "beta_within",
                                  "comp_across", "comp_within"} for r in rows)
                   and bool(rows),
         "detail": "%d industries carried in full" % n},
    ]


def main() -> int:
    S = BD.load()
    comp, classes = compositions()
    rows = build(S, comp)
    crits = criteria(rows)
    rec = {"stage": "B101", "step": "mixture_slope",
           "config": {"carrier": "EU KLEMS growth accounts BASIC joined to the "
                                 "labour accounts on (industry, country)",
                      "classes": len(classes),
                      "aggregates_excluded": sorted(AGGREGATES),
                      "min_countries": MIN_COUNTRIES,
                      "min_years_composition": MIN_YEARS_COMP,
                      "fit": "imported from b101_beta_dispersion, not rewritten"},
           "criteria": crits, "industries": rows}
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print("industry  matched  comp_ratio  beta_ratio  median_beta")
    for r in rows:
        print("  %-8s %5d   %9.3f  %10.3f  %+11.4f"
              % (r["nace"], r["countries_matched"], r["comp_ratio"],
                 r["beta_ratio"], r["median_beta"]))
    print()
    for c in crits:
        print("%-9s %-12s %-4s %s" % (c["name"], c["kind"],
                                      "PASS" if c["passed"] else "FAIL",
                                      c["detail"]))
    print("wrote %s" % OUT.name)
    return 0


def selftest() -> int:
    """Grow a failure for each criterion (discipline 11f)."""
    fails = []

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    S = BD.load()
    comp, _ = compositions()
    rows = build(S, comp)
    live = {c["name"]: c["passed"] for c in criteria(rows)}
    expect(all(live.values()), "the panel on disk passes every criterion")

    thin = [dict(r, countries_matched=MIN_COUNTRIES - 1) for r in rows]
    got = {c["name"]: c["passed"] for c in criteria(thin)}
    expect(not got["B101-36"], "an industry below the country minimum fails B101-36")

    expect(not criteria([])[1]["passed"],
           "no industries at all leaves B101-37 with nothing to read")
    expect(not criteria([])[2]["passed"],
           "and B101-38 with nothing to carry")

    stripped = [{k: v for k, v in r.items() if k != "comp_within"} for r in rows]
    expect(not criteria(stripped)[2]["passed"],
           "an industry missing a floor fails B101-38")

    #: the reading itself has to be able to come out either way: a panel whose
    #: composition axis is reversed must give the opposite rank correlation.
    flipped = [dict(r, comp_ratio=-r["comp_ratio"]) for r in rows]
    a = spearman([r["comp_ratio"] for r in rows], [r["beta_ratio"] for r in rows])
    b = spearman([r["comp_ratio"] for r in flipped], [r["beta_ratio"] for r in flipped])
    expect(a is not None and b is not None and abs(a + b) < 1e-9,
           "reversing one axis reverses the reading, so it is not written in")

    print("\nselftest " + ("FAILED" if fails else "passed"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
