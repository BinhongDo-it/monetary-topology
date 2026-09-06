"""B35-6: compute the criterion's own object, and the two gates the design file defers.

The criterion (design file, arm B35-6) is a ratio of two responses to a move in
the US domestic market, with a declared FAIL band of 1/1.5 .. 1.5. That is an
estimator against a pre-declared band, so gates D14 and D17 bind here.

Nothing on record has computed the criterion's object: earlier readings printed
UNCONDITIONAL volatility over the window, which is a different quantity. This
script computes the object and the gate arithmetic, and prints every input.

Treatment: dlog of the US domestic leg-quarter price (AMS 3649).
Outcomes:   dlog of the China export unit value, paws and leg quarters (Census).
"""
import json
import math
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b35_gate_b356.json"

# --- the three series, as printed in the results file section R16.2 -----------
# US domestic leg quarter, $/kg, from AMS 3649 Report Detail (Domestic Fresh).
# China export unit value, $/kg, from Census HS10 to CTY_CODE 5700.
MONTHS = ["2022-09", "2022-10", "2022-12", "2023-01", "2023-02", "2023-04",
          "2023-05", "2023-06", "2023-07", "2023-09", "2023-10"]
US_LQ = [0.9680, 0.8122, 0.7897, 0.7659, 0.9275, 1.0282, 1.0937, 1.0919, 1.0968, 0.9107, 0.9068]
CN_LQ = [0.7117, 0.8583, 0.8335, 0.8033, 0.7958, 0.8274, 0.8031, 0.9847, 0.8891, 0.9843, 1.1051]
CN_PAW = [1.8360, 1.8245, 1.7793, 1.8444, 1.8114, 1.7840, 1.7740, 1.8129, 1.9097, 1.9974, 1.9712]

BAND = 1.5           # FAIL if the two responses are within this factor of each other
Z90 = 1.645          # one-sided 5%, the constant D14 uses


def adjacent(months):
    """indices i where months[i+1] is the calendar month right after months[i]"""
    out = []
    for i in range(len(months) - 1):
        y0, m0 = map(int, months[i].split("-"))
        y1, m1 = map(int, months[i + 1].split("-"))
        if (y1 - y0) * 12 + (m1 - m0) == 1:
            out.append(i)
    return out


def ols(x, y):
    """slope through the origin is wrong here; fit y = a + b x, return b, se(b), r2"""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    b = sxy / sxx
    a = my - b * mx
    resid = [yi - (a + b * xi) for xi, yi in zip(x, y)]
    s2 = sum(r * r for r in resid) / (n - 2)
    se = math.sqrt(s2 / sxx)
    sst = sum((yi - my) ** 2 for yi in y)
    r2 = 1 - sum(r * r for r in resid) / sst if sst > 0 else float("nan")
    return {"b": b, "se": se, "r2": r2, "n": n, "a": a}


def main():
    idx = adjacent(MONTHS)
    print("months on record : %d" % len(MONTHS))
    print("adjacent steps   : %d   (gaps at %s)"
          % (len(idx), ", ".join(MONTHS[i] + "->" + MONTHS[i + 1]
                                 for i in range(len(MONTHS) - 1) if i not in idx)))

    dus = [math.log(US_LQ[i + 1] / US_LQ[i]) for i in idx]
    dlq = [math.log(CN_LQ[i + 1] / CN_LQ[i]) for i in idx]
    dpw = [math.log(CN_PAW[i + 1] / CN_PAW[i]) for i in idx]

    print("\nthe object, step by step (D14/D17 need it printed, not summarised):")
    print("  %-18s %9s %9s %9s" % ("step", "dlog US", "dlog CN lq", "dlog CN paw"))
    for k, i in enumerate(idx):
        print("  %-18s %+9.4f %+9.4f %+9.4f"
              % (MONTHS[i] + "->" + MONTHS[i + 1], dus[k], dlq[k], dpw[k]))
    print("  %-18s %+9.4f %+9.4f %+9.4f"
          % ("sd", statistics.stdev(dus), statistics.stdev(dlq), statistics.stdev(dpw)))

    fit_lq = ols(dus, dlq)
    fit_pw = ols(dus, dpw)
    print("\nresponse to the US move (this is the criterion's object):")
    print("  China leg quarters : b = %+.4f  se = %.4f  R2 = %+.4f" % (fit_lq["b"], fit_lq["se"], fit_lq["r2"]))
    print("  China paws         : b = %+.4f  se = %.4f  R2 = %+.4f" % (fit_pw["b"], fit_pw["se"], fit_pw["r2"]))

    diff = fit_lq["b"] - fit_pw["b"]
    se_diff = math.sqrt(fit_lq["se"] ** 2 + fit_pw["se"] ** 2)  # upper bound: ignores the shared regressor's covariance
    print("  difference b_lq - b_paw = %+.4f   se(diff, independent bound) = %.4f" % (diff, se_diff))

    # --- gate two: is the declared band readable at this se? ------------------
    half = math.log(BAND)
    print("\n=== gate two (D14), first段, no borrowed multiple ===")
    print("  declared FAIL band : ratio within 1/%.1f .. %.1f  ->  half width in logs = %.4f" % (BAND, BAND, half))
    print("  Z90 x se(diff)     = %.4f x %.4f = %.4f" % (Z90, se_diff, Z90 * se_diff))
    passes2 = Z90 * se_diff < half
    print("  %.4f %s %.4f   ->  gate two %s"
          % (Z90 * se_diff, "<" if passes2 else ">=", half, "PASSES" if passes2 else "DOES NOT PASS"))
    if not passes2:
        print("  shortfall multiple : %.2f x" % (Z90 * se_diff / half))

    # --- gate three: power at the declared band -------------------------------
    def phi(z):
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))
    power = phi(half / se_diff - Z90)
    print("\n=== gate three (D17) ===")
    print("  power at theta = the band edge = Phi(%.4f/%.4f - %.4f) = %.4f" % (half, se_diff, Z90, power))
    print("  floor is 0.50 -> %s" % ("PASSES" if power > 0.50 else "BELOW THE FLOOR, a FAIL here records as undecidable"))
    lr = (1 - 0.05) / (1 - power) if power < 1 else float("inf")
    print("  likelihood ratio of a non-rejection (1-alpha)/(1-power) = %.2f   (one bit = 2.00)" % lr)

    rec = {"stage": "B35", "arm": "B35-6",
           "diagnostic_only": True,
           "diagnostic_reason": "gate arithmetic and the criterion's object; the arm is not scored here because gate three has to be read first",
           "months": MONTHS, "adjacent_steps": len(idx),
           "dlog_us": dus, "dlog_cn_lq": dlq, "dlog_cn_paw": dpw,
           "fit_leg_quarters": fit_lq, "fit_paws": fit_pw,
           "b_diff": diff, "se_diff_independent_bound": se_diff,
           "band_half_width_log": half, "z90": Z90,
           "gate_two_lhs": Z90 * se_diff, "gate_two_passes": passes2,
           "gate_three_power": power, "gate_three_floor": 0.50,
           "likelihood_ratio_of_non_rejection": lr}
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\nwrote %s" % OUT.name)


if __name__ == "__main__":
    main()
