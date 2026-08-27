"""B21: two more edges where the class difference is set by statute, not estimated.

The first arm on this carrier used dividend withholding. Enumerating the square
term by term showed that on the trading legs every charge is class-blind, so the
whole class-dependent content of this carrier is tax. **Two tax terms had not
been read.** Both come from Caishui [2014] 81 and both are larger than the
withholding.

    the twelve-month edge   A resident enterprise pays no enterprise income tax
                            on a listed dividend once it has held continuously
                            for twelve months, and pays it at 25 per cent
                            otherwise. Enterprise Income Tax Law article 26 with
                            article 83 of its implementing regulations, and
                            Caishui [2014] 81 carries the same threshold onto the
                            H line. **One threshold, both legs**, so the edge runs
                            on 4,226 leg-years rather than on one leg's share.
                            **The threshold is a date and the rate is a statute**,
                            so this is the dividend arm's own algebra evaluated at
                            a gap of 0.25 rather than 0.10 or 0.20.

    the capital-gains edge  A Hong Kong investor, enterprise or individual, is
                            exempt from tax on A-share transfer gains; a mainland
                            enterprise includes them in taxable income at 25 per
                            cent. Same edge, same statute, and an order of
                            magnitude above the withholding.

**What makes the pair worth running together is that the algebra predicts
opposite shapes.** Both indices are a difference of two logs, and expanding both
to third order:

    dividends        gap = closed - exact = +(2-ta-tb)(tb-ta)/2 * y^2 + ...
                     the third order term subtracts, so the ratio to prediction
                     sits below one and falls in the yield.
    capital gains    gap = closed - exact = -(tb^2-ta^2)/2 * x^2 + ...
                     the third order term adds to a negative, so the ratio to
                     prediction sits above one and rises in the gain.

**A pipeline that is right reproduces both, and one that is wrong cannot be wrong
in two opposite directions at once.** The first was measured at 0.995 falling to
0.878 across yield bands. This file asks for the second.

**The capital-gains edge then splits itself again, and the statute says which
way.** A loss is deductible where a gain is taxable, so the index reverses sign,
and in the expansion the running variable turns negative while the second-order
term does not care and the third-order term does. **So the loss branch is
predicted to mirror the gain branch**: below one and falling in the size of the
loss, where gains sit above one and rise. Same edge, same statute, same code, and
the direction turns on the sign of one variable.

**One limitation travels with the capital-gains edge and is not small.**
Withholding is deducted at source per payment with no netting. Enterprise income
tax is an annual entity-level computation, so a gain offsets losses elsewhere in
the entity and the twenty-five per cent is the rate at the margin for an entity
with taxable income, which is the class this names. It is not a per-position
deduction the way withholding is.

Usage::

    python experiments/b21_tax_edges.py
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b21_tax_edges.json"

# Caishui [2014] 81, Caishui [2016] 127, and Announcement 23 of 2023 for the extension.
DIV_LO, DIV_HI = 0.00, 0.25     # H-share dividend, mainland enterprise: >=12m, <12m
CGT_LO, CGT_HI = 0.00, 0.25     # A-share gain: Hong Kong investor, mainland enterprise

BANDS = [(0, .01), (.01, .02), (.02, .04), (.04, .07), (.07, .12), (.12, 9)]


def _index_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "b21ci", Path(__file__).with_name("b21_class_index.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def div_index(p1: float, d: float, ta: float, tb: float) -> float:
    return math.log((p1 + (1 - ta) * d) / (p1 + (1 - tb) * d))


def cgt_index(p1: float, d: float, g: float, ta: float, tb: float) -> float:
    """Gain taxed on realisation at the close of the holding period."""
    return math.log((p1 - ta * g + d) / (p1 - tb * g + d))


def bandtable(rows: list[tuple[float, float]], label: str) -> list[dict]:
    print(f"    {'band':>16} {'n':>6} {'median ratio':>14}")
    out = []
    for lo, hi in BANDS:
        v = sorted(r for x, r in rows if lo <= x < hi)
        if len(v) < 5:
            continue
        nm = f"{lo:.0%} to {hi:.0%}" if hi < 9 else f"over {lo:.0%}"
        print(f"    {nm:>16} {len(v):>6} {v[len(v) // 2]:>14.3f}")
        out.append({"band": nm, "n": len(v), "median_ratio": v[len(v) // 2]})
    return out


def main() -> int:
    ci = _index_module()
    sub = ci.rebuilt_amounts()
    a_rows, h_rows = [], []
    for r in ci.pairs():
        for leg, tk in (("A", r["a"]), ("H", r["h"])):
            for y, p0, p1, d in ci.holding_years(ci.load(tk), tk, sub):
                (a_rows if leg == "A" else h_rows).append(
                    {"name": r["name"], "tk": tk, "y": y, "p0": p0, "p1": p1, "d": d})
    if not a_rows or not h_rows:
        print("no usable leg-years")
        return 1

    crit = []

    # ---- edge one: the twelve-month enterprise dividend threshold, H leg ----
    print("the twelve-month edge. A resident enterprise pays no enterprise income")
    print("tax on a listed dividend once it has held for twelve months and 25 per")
    print("cent otherwise: Enterprise Income Tax Law article 26 with article 83 of")
    print("the implementing regulations, and Caishui [2014] 81 carrying the same")
    print("threshold onto the H line. **One threshold, so both legs.**")
    print("Same algebra as the first arm, evaluated at 0.25.\n")
    coef = 0.5 * (DIV_HI - DIV_LO) * (2 - DIV_LO - DIV_HI)
    print(f"    second order coefficient {coef:.5f}, "
          f"against 0.0950 and 0.0850 on the first arm")
    idx, rat = [], []
    for x in a_rows + h_rows:                 # one threshold, both legs
        e = 1e4 * div_index(x["p1"], x["d"], DIV_LO, DIV_HI)
        c = 1e4 * (DIV_HI - DIV_LO) * x["d"] / x["p1"]
        yld = x["d"] / x["p1"]
        pred = 1e4 * coef * yld ** 2
        idx.append(e)
        if pred > 1e-6:
            rat.append((yld, (c - e) / pred))
    idx.sort()
    v = sorted(r for _, r in rat)
    print(f"    index over {len(idx)} leg-years on both legs: "
          f"p10 {idx[len(idx)//10]:.1f}  "
          f"median {idx[len(idx)//2]:.1f}  p90 {idx[9*len(idx)//10]:.1f}  "
          f"max {idx[-1]:.1f}  bp")
    print(f"    ratio to prediction: p10 {v[len(v)//10]:.3f}  "
          f"median {v[len(v)//2]:.3f}  p90 {v[9*len(v)//10]:.3f}  max {v[-1]:.4f}")
    dv_bands = bandtable(rat, "dividend")
    ms = [b["median_ratio"] for b in dv_bands]
    crit.append({
        "name": "B21-13  the twelve-month edge reproduces the first arm's shape at "
                "a statutory gap of 0.25: below one and monotone down in the yield",
        "passed": bool(ms) and all(a >= b for a, b in zip(ms, ms[1:])) and v[-1] <= 1.0,
        "detail": f"coefficient {coef:.5f}; band medians "
                  + " ".join(f"{m:.3f}" for m in ms) + f"; max ratio {v[-1]:.4f}"})

    # ---- edge two: the capital-gains edge, A leg ----
    print("\nthe capital-gains edge. A Hong Kong investor is exempt on A-share")
    print("transfer gains; a mainland enterprise is taxed at 25 per cent.")
    print("**The algebra predicts the opposite shape**: the ratio sits above one")
    print("and rises in the gain, because here the third order term adds to a")
    print("negative second order term instead of subtracting from a positive one.\n")
    coef2 = 0.5 * (CGT_HI ** 2 - CGT_LO ** 2)
    print(f"    second order coefficient {-coef2:.5f} (negative by construction)")
    idx2, rat2, ng = [], [], 0
    for x in a_rows:
        g = x["p1"] - x["p0"]
        if g <= 0:
            ng += 1
            continue
        e = 1e4 * cgt_index(x["p1"], x["d"], g, CGT_LO, CGT_HI)
        c = 1e4 * (CGT_HI - CGT_LO) * g / (x["p1"] + x["d"])
        xx = g / (x["p1"] + x["d"])
        pred = -1e4 * coef2 * xx ** 2
        idx2.append(e)
        if abs(pred) > 1e-6:
            rat2.append((xx, (c - e) / pred))
    if not idx2:
        print("    no leg-year carries a positive gain")
        return 1
    idx2.sort()
    v2 = sorted(r for _, r in rat2)
    print(f"    leg-years with a gain {len(idx2)}, with a loss {ng} "
          f"(the loss branch is the next block, not a discard)")
    print(f"    index: p10 {idx2[len(idx2)//10]:.1f}  median {idx2[len(idx2)//2]:.1f}  "
          f"p90 {idx2[9*len(idx2)//10]:.1f}  max {idx2[-1]:.1f}  bp")
    print(f"    ratio to prediction: p10 {v2[len(v2)//10]:.3f}  "
          f"median {v2[len(v2)//2]:.3f}  p90 {v2[9*len(v2)//10]:.3f}  min {v2[0]:.4f}")
    cg_bands = bandtable(rat2, "gain")
    ms2 = [b["median_ratio"] for b in cg_bands]
    crit.append({
        "name": "B21-14  the capital-gains edge takes the opposite shape the same "
                "algebra predicts: above one and monotone up in the gain",
        "passed": bool(ms2) and all(a <= b for a, b in zip(ms2, ms2[1:]))
                  and v2[0] >= 1.0,
        "detail": f"coefficient {-coef2:.5f}; band medians "
                  + " ".join(f"{m:.3f}" for m in ms2) + f"; min ratio {v2[0]:.4f}"})
    # ---- edge two, the other branch: losses, where the statute reverses the sign ----
    print("\nthe same edge on its loss branch. A loss is deductible where a gain")
    print("is taxable, **so the statute reverses the index's sign**, and in the")
    print("expansion the third order term reverses with it while the second does")
    print("not. The prediction is the mirror image: below one, falling in size.\n")
    idx3, rat3 = [], []
    for x in a_rows:
        g = x["p1"] - x["p0"]
        if g >= 0:
            continue
        e = 1e4 * cgt_index(x["p1"], x["d"], g, CGT_LO, CGT_HI)
        c = 1e4 * (CGT_HI - CGT_LO) * g / (x["p1"] + x["d"])
        xx = g / (x["p1"] + x["d"])
        pred = -1e4 * coef2 * xx ** 2
        idx3.append(e)
        if abs(pred) > 1e-6:
            rat3.append((abs(xx), (c - e) / pred))
    idx3.sort()
    v3 = sorted(r for _, r in rat3)
    print(f"    leg-years with a loss {len(idx3)}")
    print(f"    index: p10 {idx3[len(idx3)//10]:.1f}  median {idx3[len(idx3)//2]:.1f} "
          f" p90 {idx3[9*len(idx3)//10]:.1f}  min {idx3[0]:.1f}  max {idx3[-1]:.1f}  bp")
    print(f"    **every one of them negative: {all(z < 0 for z in idx3)}**")
    print(f"    ratio to prediction: p10 {v3[len(v3)//10]:.3f}  "
          f"median {v3[len(v3)//2]:.3f}  p90 {v3[9*len(v3)//10]:.3f}  max {v3[-1]:.4f}")
    ls_bands = bandtable(rat3, "loss")
    ms3 = [b["median_ratio"] for b in ls_bands]
    crit.append({
        "name": "B21-16  on the loss branch the statute reverses the index's sign, "
                "and the shape mirrors: below one and monotone down in the size",
        "passed": all(z < 0 for z in idx3) and bool(ms3)
                  and all(a >= b for a, b in zip(ms3, ms3[1:])) and v3[-1] <= 1.0,
        "detail": f"{len(idx3)} loss leg-years, all negative, median "
                  f"{idx3[len(idx3)//2]:.1f} bp; band medians "
                  + " ".join(f"{m:.3f}" for m in ms3) + f"; max ratio {v3[-1]:.4f}"})

    crit.append({
        "name": "B21-15  neither statutory index is zero anywhere",
        "passed": idx[0] > 0 and idx2[0] > 0,
        "detail": f"smallest twelve-month index {idx[0]:.4f} bp over {len(idx)} "
                  f"leg-years; smallest capital-gains index {idx2[0]:.4f} bp over "
                  f"{len(idx2)}; largest on the loss branch {idx3[-1]:.4f} bp over "
                  f"{len(idx3)}"})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B21", "step": "tax_edges",
        "diagnostic_only": True,
        "diagnostic_reason": "Two further statutory edges found by enumerating the "
                             "square term by term. The capital-gains edge carries "
                             "a netting caveat stated in the module docstring.",
        "twelve_month": {"coefficient": coef, "leg_years": len(idx),
                         "index_bp": {"p10": idx[len(idx)//10],
                                      "median": idx[len(idx)//2],
                                      "p90": idx[9*len(idx)//10], "max": idx[-1],
                                      "min": idx[0]},
                         "bands": dv_bands, "max_ratio": v[-1]},
        "capital_gains_loss_branch": {
            "leg_years": len(idx3), "all_negative": all(z < 0 for z in idx3),
            "index_bp": {"p10": idx3[len(idx3)//10],
                         "median": idx3[len(idx3)//2],
                         "p90": idx3[9*len(idx3)//10], "min": idx3[0],
                         "max": idx3[-1]},
            "bands": ls_bands, "max_ratio": v3[-1]},
        "capital_gains": {"coefficient": -coef2, "leg_years": len(idx2),
                          "leg_years_with_loss": ng,
                          "index_bp": {"p10": idx2[len(idx2)//10],
                                       "median": idx2[len(idx2)//2],
                                       "p90": idx2[9*len(idx2)//10],
                                       "max": idx2[-1], "min": idx2[0]},
                          "bands": cg_bands, "min_ratio": v2[0]},
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, "
          f"{sum(1 for c in crit if c['passed'])} passing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
