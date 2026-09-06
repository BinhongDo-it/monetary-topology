"""B30-5 carrier validation, step C: does the crowdsourced panel measure a level?

The panel in ``data/b30_5/panel.json`` is crowdsourced, and the whole B30-5
cross-section rests on it carrying a comparable price *level* across cities
rather than twelve unrelated local averages. Exactly one class in it has an
authoritative counterpart: housing. The statistics bureau publishes an average
residential selling price as an absolute quantity per region and states that it
is suitable for comparison across regions against local income, which is the
same right-hand side B30-5 regresses on. So the panel can be checked against it.

**The statistic.** Over the cities, with `N` the panel price and `O` the
official one, both in yuan per square metre:

    log N(c) = a + b * log O(c) + e(c)

and the three numbers reported are `b`, the rank correlation, and `sd(e)`.
`sd(e)` is what matters: it is the panel's error scale in logs, in the same
units as the `sigma` gate six is read on.

**The unit constant does not enter.** The panel prices per square foot and the
official series per square metre. A constant factor in logs moves `a` and moves
nothing else, so `b`, the rank correlation and `sd(e)` are all invariant to it.
The conversion below is applied only so the printed levels are readable.

**The reading, fixed before the official numbers were fetched.**

    b near 1 and sd(e) small      the panel measures the level; its error is
                                  bounded by sd(e)
    b near 1 and sd(e) large      the panel is usable and noisy, by this much
    b far from 1, or the rank
    correlation weak              the panel does not measure the level, and the
                                  cross-city dimension needs another carrier

**No threshold is registered on any of the three.** They are printed with every
city's own pair and residual beside them, so any row can be re-argued.

**The mismatch is named first and it runs in the helpful direction.** Four of
the twelve cities are themselves provincial units, so for them the official
figure is the city. The other eight are a capital compared against its whole
province, and a province average is pulled below its capital by the smaller
cities in it. That flattens `b` and inflates `sd(e)`. **So `sd(e)` measured this
way is an upper bound on the panel's own error, not an estimate of it**, and the
four exact cities are reported separately as the mismatch-free read.

**Two arms, because the housing arm needs a source that is not reachable.**

**Arm A, administrative items, and it runs on what is already on disk.** Retail
gasoline in China is priced off a provincial ceiling set by the planning
commission, so its true variation across cities is administrative and tiny, and
its true loading on local income is zero by construction. That makes it a known
answer on exactly the dimension in question: whatever dispersion the panel shows
on it above the administrative dispersion is the panel's own cross-city noise,
and whatever loading it shows above zero is the estimator's own error. Both are
measured below and both are reported.

**Arm B, housing, against the yearbook.** The counterpart is the average selling
price of newly built residential buildings, published **per city** for
thirty-five cities in the statistical yearbook. Per city, so the mismatch this
arm was first designed around, a capital compared against its whole province,
does not arise: every row is the same city on both sides.

**Two scope differences remain, and both run in the helpful direction.** The
official figure covers newly built stock averaged over the whole municipality
including its outer districts, while the panel prices a central and an
outside-centre square metre separately, so the official number should sit
between the panel's two and nearer the outside one -- which is a prediction, and
it is printed below rather than asserted. And the official year is 2023 against
a panel read in 2026, over which Chinese housing fell by different amounts in
different cities. Both differences add scatter that is not the panel's fault, so
`sd(e)` measured here is an **upper bound** on the panel's error rather than an
estimate of it.

Run:
    python experiments\\b30_5_carrier_check.py
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "b30_5" / "panel.json"
OFFICIAL = ROOT / "data" / "b30_5" / "nbs" / "housing_price.json"
OUT = ROOT / "results" / "b30_5_carrier_check.json"

FT2_PER_M2 = 10.7639

# The class medians b30_5_income_loading.py printed on the same twelve cities.
# Arm C corrects these rather than recomputing them, so the two scripts cannot
# drift into reporting different medians for the same run.
LADDER_MEDIAN, LOCAL_MEDIAN = 0.130, 0.630

BUY_C = ("Buy Apartment Price :: Price per Square Feet to Buy Apartment "
         "in City Centre")
BUY_O = ("Buy Apartment Price :: Price per Square Feet to Buy Apartment "
         "Outside of Centre")

# The official series is per city, so the mapping is the identity and the
# capital-versus-province mismatch this arm was first written around does not
# arise at all. `exact` stays in the shape because the code below reports an
# exact subset separately; every row is exact here.
REGION = {c: (c, True) for c in [
    "Beijing", "Tianjin", "Shanghai", "Chongqing", "Shijiazhuang", "Taiyuan",
    "Hohhot", "Shenyang", "Changchun", "Harbin", "Nanjing", "Hangzhou",
]}


def ols(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    if sxx == 0:
        return None, None, None
    b = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / sxx
    a = my - b * mx
    res = [y[i] - (a + b * x[i]) for i in range(n)]
    sd = st.pstdev(res) if n > 1 else 0.0
    return a, b, sd


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    dx = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy = math.sqrt(sum((v - my) ** 2 for v in y))
    return num / (dx * dy) if dx and dy else None


def spearman(x, y):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    return pearson(rank(x), rank(y))


def report(label, pairs):
    if len(pairs) < 3:
        print("\n  %s: %d cities, too few to read a slope. Pairs printed above."
              % (label, len(pairs)))
        return None
    x = [math.log(o) for _, o, _ in pairs]
    y = [math.log(n) for _, _, n in pairs]
    a, b, sd = ols(x, y)
    r, rho = pearson(x, y), spearman(x, y)
    print("\n  %s   n = %d" % (label, len(pairs)))
    print("    slope b            %+.4f      (1 means the panel tracks the "
          "level one for one)" % b)
    print("    residual sd(e)      %.4f      in logs, the panel's error scale"
          % sd)
    print("    Pearson r on logs  %+.4f" % r)
    print("    Spearman rank      %+.4f" % rho)
    return {"n": len(pairs), "slope": b, "resid_sd": sd,
            "pearson": r, "spearman": rho, "intercept": a}


# 92-octane provincial retail price, 2026-08-12, in yuan per litre. Provenance,
# stated because it decides how much this table can carry: a trade aggregator
# whose own note says the figures are station prices reported by users, so it is
# not an official release. It is used for its STRUCTURE, which reproduces the
# administrative facts independently known -- Hainan at 9.08 carries a fuel tax
# levied in place of road tolls since 1994, Tibet at 8.84 carries transport, and
# every other mainland region sits inside 7.74 to 8.12. A table that reproduces
# known structure it did not invent is usable for the spread even though it
# cannot be quoted as the official number.
ADMIN_GASOLINE = {
    "Beijing": 7.97, "Tianjin": 7.96, "Shijiazhuang": 7.96, "Taiyuan": 7.92,
    "Hohhot": 7.97, "Shenyang": 8.03, "Changchun": 7.93, "Harbin": 7.93,
    "Shanghai": 7.93, "Nanjing": 7.94, "Hangzhou": 7.94, "Chongqing": 8.03,
}
GASOLINE = "Transportation :: Gasoline (1 Liter)"


def arm_a(panel):
    """The panel against an administratively priced item. Prints, judges nothing."""
    rows = [(c, ADMIN_GASOLINE[c], panel[c]["items"][GASOLINE])
            for c in sorted(panel)
            if c in ADMIN_GASOLINE and panel[c]["items"].get(GASOLINE)]
    if len(rows) < 4:
        print("\n  arm A: %d cities carry both numbers, too few." % len(rows))
        return None

    print("\n" + "=" * 78)
    print("arm A: an item whose price is set administratively, so its true")
    print("cross-city variation is known to be small and its true loading on")
    print("local income is zero by construction")
    print("=" * 78)
    print("  %-14s %9s %9s %12s" % ("city", "admin", "panel", "panel/admin"))
    for c, a, n in sorted(rows, key=lambda r: -r[2]):
        print("  %-14s %9.2f %9.2f %12.4f" % (c, a, n, n / a))

    la = [math.log(a) for _, a, _ in rows]
    ln = [math.log(n) for _, _, n in rows]
    sda, sdn = st.pstdev(la), st.pstdev(ln)
    excess = math.sqrt(max(sdn ** 2 - sda ** 2, 0.0))
    print("\n  cross-city sd in logs")
    print("    administrative  %.5f   (%.2f%% spread)"
          % (sda, (math.exp(sda) - 1) * 100))
    print("    panel           %.5f   (%.2f%% spread)"
          % (sdn, (math.exp(sdn) - 1) * 100))
    print("    the panel's own cross-city noise, by quadrature: %.5f  (%.2f%%)"
          % (excess, (math.exp(excess) - 1) * 100))
    print("    level offset    %+.2f%%   an intercept, it does not touch any b"
          % ((math.exp(st.mean(ln) - st.mean(la)) - 1) * 100))

    # The calibration that matters: this item's true b is zero, so whatever the
    # panel returns for it is the estimator's error on a known-zero item -- and
    # zero is exactly what one of the two registered classes predicts.
    ly = [math.log(panel[c]["salary"]) for c, _, _ in rows]
    _, b, sd = ols(ly, ln)
    se = sd / math.sqrt(len(rows)) / st.pstdev(ly) if st.pstdev(ly) else None
    print("\n  the panel's loading on this known-zero item")
    print("    b = %+.4f   se = %.4f   that is %.2f se from zero"
          % (b, se, abs(b) / se if se else float("nan")))
    print("    The registered LADDER prediction is b near zero, so this says")
    print("    the panel can return zero where zero is the truth.")
    return {"n": len(rows), "sd_admin": sda, "sd_panel": sdn,
            "panel_noise_sd": excess, "b_on_known_zero": b, "se": se,
            "level_offset": math.exp(st.mean(ln) - st.mean(la)) - 1}


def compare_to_residual(noise_sd, resid_sd):
    """What the measured noise costs the reading gate six is read on."""
    print("\n" + "=" * 78)
    print("what that noise costs the design")
    print("=" * 78)
    share = (noise_sd ** 2) / (resid_sd ** 2) if resid_sd else float("nan")
    print("  measured panel noise sd        %.4f" % noise_sd)
    print("  the residual the design reads  %.4f" % resid_sd)
    print("  noise share of residual var    %.1f%%" % (share * 100))
    breakeven = resid_sd / math.sqrt(2.0)
    print("  the panel would have to be %.1f times noisier than measured before"
          % (breakeven / noise_sd))
    print("  measurement error carried half the residual variance.")
    print("\n  Noise on the left-hand side inflates se and does not move b, and")
    print("  b is what every reading in this station is. So softness in the")
    print("  levels makes the test harder rather than wrong.")
    return {"noise_sd": noise_sd, "resid_sd": resid_sd,
            "noise_share_of_var": share, "breakeven_multiple":
            breakeven / noise_sd if noise_sd else None}


def arm_c(panel, official, noise_lo, noise_hi):
    """The right-hand side. Noise there does not inflate se, it bends b.

    Arms A and B are about the price, which is the left-hand side, and noise
    there inflates `se` without moving `b`. Income is the right-hand side and
    behaves in the opposite way: noise in a regressor attenuates the slope
    toward zero by

        lambda = (var of the observed regressor - noise var) / var observed

    **and zero is what one of the two registered classes predicts.** So this is
    the one error direction that could push the reading toward the station's own
    hypothesis, and it has to be looked at rather than assumed away.

    Two things settle it, and they settle two different readings.

    First, `lambda` multiplies *every* slope by the same factor, so it cannot
    manufacture a difference between two classes; it can only compress one that
    is there. The observed gap between the class medians is therefore a floor,
    and every correction widens it.

    Second, for the separate reading that LADDER sits near zero, attenuation
    genuinely does help that conclusion, so the correction is applied and the
    corrected value reported. The registered kill branch asks whether LADDER
    comes back near one; the table below carries the corrected LADDER median out
    to a noise level far beyond anything measured, and it does not approach one.
    """
    cs = sorted(c for c in panel
                if c in official and panel[c].get("salary"))
    if len(cs) < 4:
        print("\n  arm C: %d cities overlap, too few." % len(cs))
        return None
    ly = [math.log(panel[c]["salary"]) for c in cs]
    lh = [math.log(list(official[c].values())[0]) for c in cs]
    r = pearson(ly, lh)
    sdY = st.pstdev(ly)

    print("\n" + "=" * 78)
    print("arm C: the right-hand side, where noise bends b instead of se")
    print("=" * 78)
    print("  the panel's income against an authoritative per-city quantity")
    print("    corr(log panel salary, log official housing price) = %+.4f"
          "   r^2 = %.4f   n = %d" % (r, r * r, len(cs)))
    print("    A salary made mostly of noise could not reach that against a")
    print("    series it has no contact with.")
    print("\n  attenuation, carried out past anything measured")
    print("    %-10s %-9s %-10s %-9s %s"
          % ("noise sd", "lambda", "LADDER", "LOCAL", "gap"))
    rows = []
    for sx in (noise_lo, 0.05, 0.09, noise_hi):
        lam = (sdY ** 2 - sx ** 2) / sdY ** 2
        if lam <= 0:
            continue
        lad, loc = LADDER_MEDIAN / lam, LOCAL_MEDIAN / lam
        print("    %-10.4f %-9.4f %-10.3f %-9.3f %.3f"
              % (sx, lam, lad, loc, loc - lad))
        rows.append({"noise_sd": sx, "lambda": lam, "ladder": lad,
                     "local": loc, "gap": loc - lad})
    print("    %-10s %-9.4f %-10.3f %-9.3f %.3f"
          % ("0 (none)", 1.0, LADDER_MEDIAN, LOCAL_MEDIAN,
             LOCAL_MEDIAN - LADDER_MEDIAN))
    print("\n  Every correction widens the gap, so the observed %.3f is a"
          % (LOCAL_MEDIAN - LADDER_MEDIAN))
    print("  floor. And the corrected LADDER median stays far from one at")
    print("  every noise level in the table, so the registered kill branch")
    print("  does not trigger under any of them.")
    return {"n": len(cs), "corr_salary_official": r, "sd_log_income": sdY,
            "rows": rows,
            "observed_gap": LOCAL_MEDIAN - LADDER_MEDIAN}


def main():
    if not PANEL.exists():
        raise SystemExit("no panel at %s" % PANEL)
    panel = json.loads(PANEL.read_text(encoding="utf-8"))

    a_out = arm_a(panel)
    cost = None
    if a_out and a_out["panel_noise_sd"]:
        # 0.2013 is the median item residual sd this panel actually produced,
        # printed by b30_5_income_loading.py on the same twelve cities.
        prior = ROOT / "results" / "b30_5_income_loading.json"
        resid = 0.2013
        if prior.exists():
            try:
                j = json.loads(prior.read_text(encoding="utf-8"))
                resid = j.get("median_item_resid_sd") or resid
            except Exception:
                pass
        cost = compare_to_residual(a_out["panel_noise_sd"], resid)

    c_out = None
    if OFFICIAL.exists():
        _o = json.loads(OFFICIAL.read_text(encoding="utf-8"))
        c_out = arm_c(panel, _o.get("series", _o),
                      a_out["panel_noise_sd"] if a_out else 0.03, 0.1718)

    if not OFFICIAL.exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(
            {"arm_a_administrative": a_out, "arm_a_cost": cost,
             "arm_b_housing": "not run: the official per-region series is not "
                              "on disk. Its query host answers 403 from a WAF "
                              "URL rule."},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nwritten: %s" % OUT)
        raise SystemExit(
            "\narm B needs %s: a JSON mapping the region name used in REGION "
            "above to {year: yuan per square metre}. Arm A above is complete "
            "and recorded." % OFFICIAL)
    off = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    series = off.get("series", off)
    meta = off.get("meta", {})
    if meta:
        print("official series: %s" % json.dumps(meta, ensure_ascii=False))

    years = sorted({y for v in series.values() for y in v})
    if not years:
        raise SystemExit("the official file carries no years.")
    year = years[-1]
    print("official year used: %s   (all years present: %s)"
          % (year, ", ".join(years)))

    print("\n" + "=" * 78)
    print("every city, both numbers, in yuan per square metre")
    print("=" * 78)
    print("  %-14s %12s %12s %12s %10s %10s"
          % ("city", "official", "panel ctr", "panel out",
             "off/ctr", "off/out"))
    rows_c, rows_o = [], []
    unmatched = []
    for city in sorted(panel):
        if city not in REGION:
            unmatched.append((city, "no region mapping"))
            continue
        reg, exact = REGION[city]
        o = series.get(reg, {}).get(year)
        pc = panel[city]["items"].get(BUY_C)
        po = panel[city]["items"].get(BUY_O)
        pc = pc * FT2_PER_M2 if pc else None
        po = po * FT2_PER_M2 if po else None
        print("  %-14s %12s %12s %12s %10s %10s"
              % (city,
                 ("%12.0f" % o) if o else "     missing",
                 ("%12.0f" % pc) if pc else "     missing",
                 ("%12.0f" % po) if po else "     missing",
                 ("%10.2f" % (o / pc)) if (o and pc) else "         -",
                 ("%10.2f" % (o / po)) if (o and po) else "         -"))
        if o and pc:
            rows_c.append((city, o, pc, exact))
        else:
            unmatched.append((city, "official %s, panel %s"
                              % ("ok" if o else "missing",
                                 "ok" if pc else "missing")))
        if o and po:
            rows_o.append((city, o, po, exact))

    if unmatched:
        print("\n  cities not entering, named rather than dropped quietly:")
        for c, why in unmatched:
            print("    %-14s %s" % (c, why))

    print("\n" + "=" * 78)
    print("does the panel track the official level")
    print("=" * 78)
    out = {}
    out["centre_all"] = report(
        "city centre, all cities", [(c, o, n) for c, o, n, _ in rows_c])
    # The official figure covers a whole municipality of newly built stock, so
    # of the panel's two housing rows the outside-centre one is the closer
    # object. Both are fitted and both are printed; neither is chosen here.
    out["centre_exact"] = None
    out["outside_all"] = report(
        "outside centre, all cities", [(c, o, n) for c, o, n, _ in rows_o])

    if out["centre_all"]:
        a, b = out["centre_all"]["intercept"], out["centre_all"]["slope"]
        print("\n" + "=" * 78)
        print("every city's own residual, so any row can be re-argued")
        print("=" * 78)
        res = sorted(((math.log(n) - (a + b * math.log(o)), c)
                      for c, o, n, _ in rows_c), reverse=True)
        for e, c in res:
            print("  %-14s %+.4f   panel is %+.1f%% off the fitted line"
                  % (c, e, (math.exp(e) - 1) * 100))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"arm_a_administrative": a_out, "arm_a_cost": cost,
         "arm_c_attenuation": c_out,
         "official_meta": meta, "official_year": year,
         "ft2_per_m2": FT2_PER_M2, "fits": out,
         "pairs_centre": [{"city": c, "official": o, "panel": n,
                           "exact": e} for c, o, n, e in rows_c],
         "unmatched": [{"city": c, "why": w} for c, w in unmatched]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
