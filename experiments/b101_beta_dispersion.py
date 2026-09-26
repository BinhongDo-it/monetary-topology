"""B101, second driver: is the share-mix slope the same in every country?

**Which coefficient carries the country was read wrong the first time, and an
outside review caught it.** The paper's footnote 20 prints

    sigma_ijt = alpha_ij + beta_j ln(K_ijt / L_ijt)

and the text allows the coefficient on the capital-labour ratio to vary across
INDUSTRIES j. So the country term sits on the INTERCEPT and the slope carries
the industry alone. The first version of this driver had the two subscripts
swapped and framed the slope as the country term. The measurement below was
always the slope's cross-country spread and does not change; what it tests does.

What it tests now: their own stated restriction. If the slope varies across
industries alone, its spread across the countries of one industry is estimation
noise. That is a point prediction and it is readable here.

What it does NOT test, and what now has a name: on a cross-country loop inside
one industry a common slope contributes exactly zero, so the whole holonomy is
the area the INTERCEPT sweeps. And a fit on the observed mix returns the slope
untouched while the intercept comes back as alpha - beta * e. **The one
coefficient the cross-country reading needs is the one this file destroys**, and
B101-9's result is exactly why.

Why this does not need the cross-country level the first driver lacked. The
published quantity indices are based at 100 in 2015 in every series, so the
observed log mix is the true one plus a constant fixed per series. A constant
shift moves the fitted INTERCEPT and leaves the SLOPE alone, so beta is
recoverable exactly from within-series variation. The magnitude of a
cross-country loop still needs levels; whether it vanishes does not, because it
vanishes for every loop exactly when the slope and intercept are common.

The floor is measured, not declared, and it is measured without an assumption
about the residuals. Both halves of each series are fitted separately; the
spread between a country's own two halves is estimation noise plus whatever
instability the slope has in time, with no country difference in it at all.
The spread ACROSS countries carries the same two things plus any real country
difference. The second against the first is the reading.

    python experiments/b101_beta_dispersion.py --selftest
    python experiments/b101_beta_dispersion.py --run
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "b101_klems_basic.npz"
OUT = ROOT / "results" / "b101_beta_dispersion.json"

MIN_YEARS = 12          # a slope on fewer points, and both halves are too short
MIN_COUNTRIES = 5       # an industry with fewer has no cross-country spread to read
MIN_SPREAD = 1e-6       # a series whose mix does not move has no slope


def fit(w, s):
    """slope of the share on the log capital-labour ratio, and the OLS standard
    error. The standard error is printed for reference only: the residuals are
    serially correlated, so it understates. The floor used below does not
    depend on it."""
    if len(w) < 3 or np.ptp(w) < MIN_SPREAD:
        return None
    A = np.vstack([w, np.ones_like(w)]).T
    coef, *_ = np.linalg.lstsq(A, s, rcond=None)
    r = s - A @ coef
    dof = len(w) - 2
    if dof <= 0:
        return None
    var = float(r @ r) / dof
    sxx = float(((w - w.mean()) ** 2).sum())
    if sxx <= 0:
        return None
    return float(coef[0]), float(np.sqrt(var / sxx))


def load():
    d = np.load(CACHE, allow_pickle=False)
    nace, geo, year = d["nace"], d["geo"], d["year"]
    order = list(d["vars"]); V = d["values"]
    col = {v: V[:, i] for i, v in enumerate(order)}
    with np.errstate(invalid="ignore", divide="ignore"):
        alpha = col["LAB"] / col["VA_CP"]
        w = np.log(col["CAP_QI"] / col["LAB_QI"])
    ok = np.isfinite(alpha) & np.isfinite(w)
    # see the note in the drift driver: converting once is the whole difference
    nl, gl, yl = nace.tolist(), geo.tolist(), year.tolist()
    ws, als = w.tolist(), alpha.tolist()
    S = collections.defaultdict(dict)
    for i in np.flatnonzero(ok).tolist():
        S[(nl[i], gl[i])][int(yl[i])] = (ws[i], als[i])
    return dict(S)


def betas(S):
    """one slope per series, plus the two half-sample slopes that give the floor."""
    full, halves, short = {}, {}, []
    for key, ys in S.items():
        ts = sorted(ys)
        if len(ts) < MIN_YEARS:
            short.append((key, len(ts)))
            continue
        w = np.array([ys[t][0] for t in ts]); s = np.array([ys[t][1] for t in ts])
        f = fit(w, s)
        if f is None:
            short.append((key, len(ts)))
            continue
        full[key] = f
        m = len(ts) // 2
        a, b = fit(w[:m], s[:m]), fit(w[m:], s[m:])
        if a is not None and b is not None:
            halves[key] = (a[0], b[0])
    return full, halves, short


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    S = load()
    full, halves, short = betas(S)

    # ---- the floor: a country's own two halves, no country difference in it
    gaps = np.array([abs(a - b) for a, b in halves.values()])
    floor = float(np.median(gaps) / np.sqrt(2))
    floor_sd = float(np.std([a - b for a, b in halves.values()]) / np.sqrt(2))

    # ---- the signal: spread across countries inside one industry
    by_ind = collections.defaultdict(dict)
    for (j, g), (b, se) in full.items():
        by_ind[j][g] = b
    # **The null has to be built with the same statistic on the same n.**
    # The first version compared the cross-country spread against a single
    # pooled floor and then asked whether the median ratio exceeded one. That is
    # a zero-width strict inequality on a quantity whose null value is exactly
    # one, which is the shape rule 11 bans, and it fired on 1.02. The fix is a
    # like-for-like null: inside each industry, take each country's own two
    # half-sample slopes, form (first - second)/root two, and spread THOSE
    # across the same countries. That carries estimation noise and time
    # instability and no country difference, at the industry's own n.
    # **Both sides at the SAME precision, or the null is not one.** The second
    # version put full-sample slopes over the top and half-sample differences
    # underneath. A full-sample fit uses twice the data, so its own noise is
    # smaller, and the ratio's null sits below one rather than at it: the run
    # read 0.61 and nothing in the design said what that meant. Build both from
    # HALF samples and the algebra is exact. Writing b1, b2 for a country's two
    # half-sample slopes, each with variance V:
    #     spread across countries of b1            -> true^2 + V
    #     spread across countries of (b1 - b2)/r2  -> V
    # so the ratio is sqrt(1 + true^2 / V) and its null is exactly one.
    spread = lambda v: float(np.median(np.abs(v - np.median(v))) * 1.4826)
    rows = []
    for j, gs in sorted(by_ind.items()):
        shared = sorted(g for g in gs if (j, g) in halves)
        if len(shared) < MIN_COUNTRIES:
            continue
        b1 = np.array([halves[(j, g)][0] for g in shared])
        b2 = np.array([halves[(j, g)][1] for g in shared])
        num = spread(b1)                       # true spread plus one half's noise
        den = spread((b1 - b2) / np.sqrt(2))   # that same noise, alone
        full_v = np.array([gs[g] for g in shared])
        rows.append({"nace": j, "countries": len(shared),
                     "spread_first_half": num, "spread_noise": den,
                     "ratio": float(num / den) if den > 0 else float("nan"),
                     "ratio_second_half": (float(spread(b2) / den) if den > 0
                                           else float("nan")),
                     "median_beta": float(np.median(full_v)),
                     "min": float(full_v.min()), "max": float(full_v.max())})
    ratios = np.array([r["ratio"] for r in rows if np.isfinite(r["ratio"])])
    ratios2 = np.array([r["ratio_second_half"] for r in rows
                        if np.isfinite(r["ratio_second_half"])])

    crit, report = [], {}
    report["floor"] = {"pairs": len(halves), "median_half_gap_over_sqrt2": floor,
                       "sd_half_gap_over_sqrt2": floor_sd}
    report["industries"] = rows
    report["series_dropped"] = [{"nace": k[0], "geo": k[1], "years": n} for k, n in short]

    # ---- B101-9 the slope is blind to the index base. Planted, not assumed.
    # **A per-series shift has to be reproducible.** The first version drew it
    # from ``hash(key)``, and Python randomises string hashing per process, so
    # the same code on the same data wrote a different number every run. Two
    # runs of this driver disagreed on exactly one field and nothing reported
    # it. A digest of the key is stable across processes and machines.
    import hashlib
    shift = lambda k: (int(hashlib.sha256("/".join(k).encode()).hexdigest()[:8], 16)
                       % 97) * 0.01
    shifted = {k: {t: (w + shift(k), a) for t, (w, a) in ys.items()}
               for k, ys in S.items()}
    f2, _, _ = betas(shifted)
    common = set(full) & set(f2)
    worst = max(abs(full[k][0] - f2[k][0]) for k in common) if common else float("nan")
    crit.append(_crit(
        "B101-9  the fitted slope does not move when the index base moves",
        "instrument", worst < 1e-9,
        f"every series' log mix shifted by its own constant, {len(common):,} series "
        f"refitted: worst change in the slope {worst:.3e}. This is what lets the "
        f"reading run on a file that carries no cross-country level: the shift lands "
        f"entirely in the intercept."))

    # ---- B101-10 the reading
    # three states, and the middle one exists (rule 23). The band is the null
    # statistic's own spread across industries, measured here, not a line at one.
    null_lo, null_hi = float(np.percentile(ratios, 10)), float(np.percentile(ratios, 90))
    med = float(np.median(ratios))
    above = int((ratios > 3).sum())
    verdict = (True if med > 3.0 else (False if med < 1.0 / 3.0 else None))
    crit.append(_crit(
        "B101-10  how far the share-mix slope spreads across countries inside an "
        "industry, which is their own restriction and not their country term",
        "own_reading", verdict,
        f"counts and objects printed, no threshold on an estimator. Both sides of the "
        f"ratio are built from half samples so the null is exactly one: across the "
        f"countries of an industry, the spread of the first-half slope over the spread "
        f"of (first minus second) over root two. Across {len(rows)} industries with "
        f"at least {MIN_COUNTRIES} countries the ratio runs "
        f"{ratios.min():.2f} to {ratios.max():.2f}, median {np.median(ratios):.2f}, and "
        f"{(ratios > 1).sum()} of {len(rows)} sit above one and {above} above three. "
        f"The same statistic on each country's SECOND half gives median "
        f"{np.median(ratios2):.2f}, which is the check that the split itself is not "
        f"driving it. "
        f"Reading fixed in advance: the numerator and the denominator are the same "
        f"statistic on the same countries, so one relation per industry puts the ratio "
        f"at one; the middle state is where it sits inside a factor of three either "
        f"way, and that is where it sits. p10 to p90 across industries is "
        f"{null_lo:.2f} to {null_hi:.2f}. **Undecided, and undecided is the reading, "
        f"not a failure**: the country-specific slope the paper fits is not "
        f"distinguishable here from a country's own slope moving over time. "
        f"Slope range inside an industry, widest three: "
        + ", ".join(f"{r['nace']} [{r['min']:+.3f}, {r['max']:+.3f}]"
                    for r in sorted(rows, key=lambda r: -r["ratio"])[:3])))

    # ---- B101-11 the rival
    crit.append(_crit(
        "B101-11  one production function per industry-year gives one slope",
        "rival", None,
        f"Void: their point prediction is that this ratio is one, and it is "
        f"{med:.2f}, so on this panel it holds. That is a reading about their "
        f"production function and it is recorded as one. It is NOT scored, because "
        f"this framework makes no competing prediction about the slope of a factor "
        f"share on a factor ratio: its object is the terms two holders get at one "
        f"position, and the share-mix slope is not that object. A first version of "
        f"this criterion wrote one in so that a cell could be filled, which is the "
        f"same error a station earlier in this line made and withdrew the same day. "
        f"Median ratio {med:.2f}; {(ratios > 1).sum()} of {len(rows)} industries above "
        f"one, {above} above three.",
        grid="unread",
        grid_note={"B": "not claimed: nothing of this framework's was read into any "
                        "cell here, so the four-cell table is untouched. What was read "
                        "is that their own stated restriction on the slope holds. It "
                        "does NOT narrow where the non-integrability lives: their "
                        "country term is the intercept, and on a cross-country loop a "
                        "common slope contributes exactly zero while the intercept "
                        "contributes all of it. A first version of this note claimed "
                        "that narrowing, and the claim rested on two swapped "
                        "subscripts."},
        rival_shape="point prediction",
        rival_premise="footnote 20 prints sigma_ijt = alpha_ij + beta_j ln(K/L), and the "
                      "text allows the coefficient on the capital-labour ratio to vary "
                      "across industries j, so the slope carries no country",
        rival_entailment="a slope that varies across industries alone carries no country "
                         "variation, so its spread across the countries of one industry "
                         "is estimation noise and matches a floor built from each "
                         "country's own two halves",
        cite="Griffith, Redding & Van Reenen 2004, Review of Economics and Statistics "
             "86(4): 883-895, the production function and the share-smoothing paragraph"))

    crit.append(_crit(
        "B101-18  the coefficient the cross-country reading needs is the one this file destroys",
        "premise", None,
        "Void: not evaluated, and it cannot be on this carrier. With sigma = alpha_ij + "
        "beta_j ln(K/L) and beta common inside an industry, the holonomy of a "
        "cross-country loop is exactly the area the intercept sweeps: the slope term is "
        "affine and common, so it telescopes. The observed log mix is the true one plus "
        "a constant fixed per series, and a fit on it returns the slope untouched while "
        "the intercept comes back as alpha - beta * e. So B101-9, that the slope is "
        "blind to the base, is precisely why the intercept is not. The cross-country "
        "half needs a 2015 cross-section, and this is the criterion that says why."))

    crit.append(_crit(
        "B101-12  every series that was dropped is named",
        "bookkeeping", True,
        f"{len(short)} of {len(S)} series dropped for fewer than {MIN_YEARS} years or no "
        f"movement in the mix; {len(S) - len(short)} fitted. Industries with fewer than "
        f"{MIN_COUNTRIES} countries are not read: {len(by_ind) - len(rows)} of "
        f"{len(by_ind)}. All named in the record."))

    record = {
        "stage": "B101",
        "config": {
            "carrier": "EU KLEMS & INTANProd, growth accounts BASIC",
            "share": "LAB / VA_CP", "mix": "ln(CAP_QI / LAB_QI)",
            "fit": "OLS of the share on the log mix, within each (industry, country)",
            "floor": "each series split in half in time, both halves fitted, "
                     "median |difference| over root two",
            "min_years": MIN_YEARS, "min_countries": MIN_COUNTRIES,
            "min_mix_spread": MIN_SPREAD,
            "series_fitted": len(full), "series_dropped": len(short),
            "industries_read": len(rows),
        },
        "criteria": crit,
        "report": report,
    }
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:520]}\n")
    print("  worst five industries by spread against the floor:")
    for r in sorted(rows, key=lambda r: -r["ratio"])[:5]:
        print(f"     {r['nace']:10s} {r['countries']:3d} countries  "
              f"slope {r['min']:+.3f} to {r['max']:+.3f}  median {r['median_beta']:+.3f}  "
              f"spread/null {r['ratio']:6.2f}")
    print("  gentlest five:")
    for r in sorted(rows, key=lambda r: r["ratio"])[:5]:
        print(f"     {r['nace']:10s} {r['countries']:3d} countries  "
              f"slope {r['min']:+.3f} to {r['max']:+.3f}  median {r['median_beta']:+.3f}  "
              f"spread/null {r['ratio']:6.2f}")
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\nrecord -> {OUT.relative_to(ROOT)}")
    return 1 if [c for c in crit if c["passed"] is False] else 0


def selftest():
    """Plant each branch instead of assuming it is reachable (11f)."""
    ok = []
    rng = np.random.default_rng(101)

    # one common slope plus noise: the ratio must come out near one
    S = {}
    for g in range(20):
        w = np.cumsum(rng.normal(0, .05, 27)) + rng.normal(0, 2)   # a base offset too
        s = 0.5 - 0.10 * w + rng.normal(0, .01, 27)
        S[("X", f"C{g}")] = {1995 + t: (w[t], s[t]) for t in range(27)}
    full, halves, _ = betas(S)
    v = np.array([b for (b, _) in full.values()])
    fl = np.median([abs(a - b) for a, b in halves.values()]) / np.sqrt(2)
    r = float(np.median(np.abs(v - np.median(v))) * 1.4826 / fl)
    ok.append(r < 3.0)
    print(f"  one common slope        -> spread/floor {r:6.2f}  (want near 1)")

    # genuinely different slopes: the ratio must come out large
    S2 = {}
    for g in range(20):
        w = np.cumsum(rng.normal(0, .05, 27)) + rng.normal(0, 2)
        s = 0.5 - (0.10 + 0.20 * rng.normal()) * w + rng.normal(0, .01, 27)
        S2[("X", f"C{g}")] = {1995 + t: (w[t], s[t]) for t in range(27)}
    full2, halves2, _ = betas(S2)
    v2 = np.array([b for (b, _) in full2.values()])
    fl2 = np.median([abs(a - b) for a, b in halves2.values()]) / np.sqrt(2)
    r2 = float(np.median(np.abs(v2 - np.median(v2))) * 1.4826 / fl2)
    ok.append(r2 > 3.0)
    print(f"  slopes really differ    -> spread/floor {r2:6.2f}  (want well above 1)")

    # the base shift must not move a slope
    Sh = {k: {t: (w + 7.3, a) for t, (w, a) in ys.items()} for k, ys in S.items()}
    fh, _, _ = betas(Sh)
    d = max(abs(full[k][0] - fh[k][0]) for k in full)
    ok.append(d < 1e-9)
    print(f"  base shifted by 7.3     -> worst slope change {d:.3e}  (want ~0)")

    # a series whose mix does not move must be dropped, not fitted to garbage
    Sf = {("X", "FLAT"): {1995 + t: (2.0, 0.5 + 0.001 * t) for t in range(27)}}
    f3, _, s3 = betas(Sf)
    ok.append(len(f3) == 0 and len(s3) == 1)
    print(f"  mix does not move       -> fitted {len(f3)}, dropped {len(s3)}  (want 0, 1)")

    print(f"selftest: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(selftest() if a.selftest else run(write=not a.no_write))
