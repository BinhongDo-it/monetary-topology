"""B35: the "big volume => small volatility" rival, measured three ways.

Reads only what is already on disk (results/b35_census_raw.json). Zero collection.

Three tests, in ascending order of how much they can settle:

  1. CROSS-CUT, chicken only. Reproduces the reading already on record and
     re-runs it on a wider window. Cannot separate the rival from the claim,
     because across chicken cuts volume and substitution-class thickness move
     together by construction.
  2. CROSS-CUT with pork. Pork carcasses and bone-in hams/shoulders carry a
     deep domestic quotation AND a larger volume to the same destination than
     every chicken cut except paws. If volume is what makes a series quiet,
     these must be the quietest rows in the table.
  3. WITHIN-CUT, paws only. Substitution class is held at "none" for the whole
     series while volume moves by a large factor. A volume law must show up here.

Every table prints the object. No thresholds are drawn on any estimate.
"""
import json
import math
import pathlib
import statistics
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "b35_census_raw.json"
OUT = ROOT / "results" / "b35_volume_rival.json"

CHINA = "5700"

# Substitution class at the origin, as recorded in the design file. This is the
# treatment variable, not an estimate.
CUTS = {
    "0207140045": ("chicken paws",            "none"),
    "0207140025": ("chicken legs",            "thick"),
    "0207140010": ("chicken leg quarters",    "thickest"),
    "0207140030": ("chicken wings",           "thickest"),
    "0207140090": ("chicken meat NESOI",      "mixed basket"),
    "0207140050": ("chicken offal",           "thin"),
    "0203294000": ("pork NESOI",              "thick, mixed basket"),
    "0203229000": ("pork hams/shoulders b-i", "thick, quoted daily"),
    "0203210000": ("pork carcasses",          "thick, quoted daily"),
}


def load():
    rows = json.loads(RAW.read_text(encoding="utf-8"))
    series = defaultdict(dict)  # hs10 -> (y,m) -> (value, qty)
    for r in rows:
        if r["CTY_CODE"] != CHINA:
            continue
        hs = r["E_COMMODITY"]
        if hs not in CUTS:
            continue
        try:
            v = float(r["ALL_VAL_MO"])
            q = float(r["QTY_1_MO"])
        except (TypeError, ValueError):
            continue
        series[hs][(r["_year"], r["_month"])] = (v, q)
    return series


def monthly(series_one, lo, hi, floor_kg):
    """-> sorted [(ym, unit_value, qty)] inside [lo,hi] with qty above floor."""
    out = []
    for ym, (v, q) in sorted(series_one.items()):
        if not (lo <= ym <= hi):
            continue
        if q <= floor_kg or v <= 0:
            continue
        out.append((ym, v / q, q))
    return out


def stats(pts):
    """median qty (kt) and median |dlog(unit value)| over ADJACENT months only."""
    if len(pts) < 3:
        return None
    qty = statistics.median(p[2] for p in pts) / 1e6
    d = []
    for a, b in zip(pts, pts[1:]):
        (ya, ma), (yb, mb) = a[0], b[0]
        if (yb - ya) * 12 + (mb - ma) != 1:
            continue  # a gap is not a month-on-month change
        d.append(abs(math.log(b[1] / a[1])))
    if len(d) < 3:
        return None
    return {"n_months": len(pts), "n_steps": len(d),
            "qty_kt": qty, "dlog_med": statistics.median(d)}


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def cross_cut(series, lo, hi, floor_kg, keys, label):
    rows = []
    for hs in keys:
        s = stats(monthly(series.get(hs, {}), lo, hi, floor_kg))
        if s:
            s.update(hs=hs, name=CUTS[hs][0], subclass=CUTS[hs][1])
            rows.append(s)
    rows.sort(key=lambda r: -r["qty_kt"])
    print("\n=== %s  window %s..%s  floor %d kg ===" % (label, lo, hi, floor_kg))
    print("%-26s %-22s %6s %6s %9s %9s" %
          ("cut", "substitution class", "mons", "steps", "qty kt", "|dlog|"))
    for r in rows:
        print("%-26s %-22s %6d %6d %9.2f %9.4f" %
              (r["name"], r["subclass"], r["n_months"], r["n_steps"],
               r["qty_kt"], r["dlog_med"]))
    if len(rows) >= 3:
        rho = pearson([math.log(r["qty_kt"]) for r in rows],
                      [r["dlog_med"] for r in rows])
        print("  corr( log qty , |dlog| ) = %+.4f   over n = %d cuts" % (rho, len(rows)))
        quiet = min(rows, key=lambda r: r["dlog_med"])
        big = max(rows, key=lambda r: r["qty_kt"])
        print("  quietest row : %-26s qty %8.2f kt" % (quiet["name"], quiet["qty_kt"]))
        print("  largest row  : %-26s |dlog| %8.4f" % (big["name"], big["dlog_med"]))
    else:
        rho = float("nan")
    return {"label": label, "lo": list(lo), "hi": list(hi), "floor_kg": floor_kg,
            "rows": rows, "corr": rho}


def within_cut(series, hs, lo, hi, floor_kg, win=12):
    """Rolling window on ONE cut: substitution class is constant along it."""
    pts = monthly(series.get(hs, {}), lo, hi, floor_kg)
    print("\n=== WITHIN-CUT  %s  %s..%s  floor %d kg  window %d ===" %
          (CUTS[hs][0], lo, hi, floor_kg, win))
    print("  %d usable months" % len(pts))
    out = []
    print("  %-9s %-9s %9s %9s %6s" % ("from", "to", "qty kt", "|dlog|", "steps"))
    for i in range(0, len(pts) - win + 1):
        seg = pts[i:i + win]
        s = stats(seg)
        if not s:
            continue
        a = "%04d-%02d" % seg[0][0]
        b = "%04d-%02d" % seg[-1][0]
        print("  %-9s %-9s %9.2f %9.4f %6d" % (a, b, s["qty_kt"], s["dlog_med"], s["n_steps"]))
        out.append({"from": a, "to": b, **s})
    if len(out) >= 3:
        rho = pearson([math.log(r["qty_kt"]) for r in out],
                      [r["dlog_med"] for r in out])
        qs = [r["qty_kt"] for r in out]
        print("  corr( log qty , |dlog| ) = %+.4f   over n = %d windows" % (rho, len(out)))
        print("  volume swing inside the cut: %.2f .. %.2f kt  = %.2f x" %
              (min(qs), max(qs), max(qs) / min(qs)))
    else:
        rho = float("nan")
    return {"hs": hs, "name": CUTS[hs][0], "win": win, "windows": out, "corr": rho}


def sqrt_law(res, target, comparator):
    """How much quieter is `target` than a 1/sqrt(volume) law predicts, vs `comparator`?
    The sqrt law has no theoretical source in this project; it is printed as an
    object, never used as a criterion (D5)."""
    by = {r["name"]: r for r in res["rows"]}
    if target not in by or comparator not in by:
        return None
    t, c = by[target], by[comparator]
    ratio_q = t["qty_kt"] / c["qty_kt"]
    pred = 1.0 / math.sqrt(ratio_q)
    obs = t["dlog_med"] / c["dlog_med"]
    print("  sqrt-law check  %s vs %s : qty x%.2f -> predicted %.4f, observed %.4f, excess quiet %.2fx"
          % (target, comparator, ratio_q, pred, obs, pred / obs))
    return {"target": target, "comparator": comparator, "qty_ratio": ratio_q,
            "predicted": pred, "observed": obs, "excess_quiet": pred / obs}


def main():
    series = load()
    chicken = [k for k in CUTS if k.startswith("0207")]
    allcuts = list(CUTS)
    rec = {"stage": "B35", "diagnostic_only": True,
           "diagnostic_reason": "station not closed; these readings test a rival explanation, they do not score any registered criterion",
           "cross_cut": [], "within_cut": [], "sqrt": []}

    # 1. chicken only, the window on record and the wider one
    for lo, hi, lab in [((2022, 9), (2023, 12), "CHICKEN load-bearing window (on record)"),
                        ((2020, 1), (2023, 12), "CHICKEN widened"),
                        ((2020, 1), (2024, 6), "CHICKEN widened to the 2024-06 break")]:
        r = cross_cut(series, lo, hi, 0, chicken, lab)
        rec["cross_cut"].append(r)
        s = sqrt_law(r, "chicken paws", "chicken leg quarters")
        if s:
            s["window"] = lab
            rec["sqrt"].append(s)
        s = sqrt_law(r, "chicken paws", "chicken legs")
        if s:
            s["window"] = lab
            rec["sqrt"].append(s)

    # 2. the breaker: pork rows carry more volume AND a deep domestic quotation
    for lo, hi, lab in [((2020, 1), (2023, 12), "CHICKEN + PORK widened"),
                        ((2022, 9), (2023, 12), "CHICKEN + PORK load-bearing window")]:
        rec["cross_cut"].append(cross_cut(series, lo, hi, 0, allcuts, lab))

    # 3. within-cut, substitution class held constant.
    #    Two spans on purpose: the full one crosses China's 2015-01..2019-11 ban
    #    on US poultry, so its low-volume end is a different trade regime, not the
    #    same cut carrying less. The 2020-01 span is one regime throughout.
    for hs in ["0207140045", "0207140010"]:
        rec["within_cut"].append(within_cut(series, hs, (2016, 1), (2024, 6), 0, 12))
    for hs in ["0207140045", "0207140010"]:
        rec["within_cut"].append(within_cut(series, hs, (2020, 1), (2024, 6), 0, 12))

    # floor sensitivity, printed not chosen
    for floor in [50_000, 200_000, 1_000_000]:
        rec["cross_cut"].append(
            cross_cut(series, (2020, 1), (2023, 12), floor, allcuts,
                      "CHICKEN + PORK widened, floor sensitivity"))

    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\nwrote %s" % OUT.name)


if __name__ == "__main__":
    main()
