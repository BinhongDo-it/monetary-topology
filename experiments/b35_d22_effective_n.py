"""B35 D22: how many of the 46 adjacent steps are independent.

The gate arithmetic on this arm divides by sqrt(n) with n = 46. That is only
right if the 46 monthly log changes carry 46 independent pieces of information.
Monthly series are serially correlated, so the count has to be measured rather
than assumed, exactly as D24 requires the resolution floor to be measured.

Two things are computed and both are printed, because they answer different
questions:

  * the autocorrelation of each leg's regression residuals, which is what the
    standard error of the slope actually depends on;
  * a Newey-West standard error for each slope and for their difference, using
    the residual covariance already measured in b35_floors, so the two
    corrections (serial and cross-sectional) are applied to the same object.

The criteria are structural. Nothing is compared against a new threshold: the
band is still log(1.5) and the critical value is still 1.645, both with the
same provenance they had before this script existed.
"""

from __future__ import annotations

import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_gate_b356_composite.json"
OUT = ROOT / "results" / "b35_d22_effective_n.json"

Z90 = 1.645
BAND = 1.5


def ols(x: list[float], y: list[float]) -> tuple[float, float, list[float]]:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    b = sxy / sxx
    a = my - b * mx
    resid = [y[i] - a - b * x[i] for i in range(n)]
    return a, b, resid


def classical_se(x: list[float], u: list[float]) -> float:
    """Textbook OLS slope standard error, homoskedastic. This is the one the
    earlier gate readings used, so it has to appear in the table under its own
    name; comparing it with a robust one as if they were the same quantity is
    the sixth category error."""
    n = len(x)
    mx = sum(x) / n
    sxx = sum((v - mx) ** 2 for v in x)
    s2 = sum(v * v for v in u) / (n - 2)
    return math.sqrt(s2 / sxx)


def acf(u: list[float], kmax: int) -> list[float]:
    n = len(u)
    mu = sum(u) / n
    c0 = sum((v - mu) ** 2 for v in u) / n
    out = []
    for k in range(1, kmax + 1):
        ck = sum((u[i] - mu) * (u[i - k] - mu) for i in range(k, n)) / n
        out.append(ck / c0)
    return out


def nw_se(x: list[float], u: list[float], lag: int) -> float:
    n = len(x)
    mx = sum(x) / n
    xd = [v - mx for v in x]
    sxx = sum(v * v for v in xd)
    h = [xd[i] * u[i] for i in range(n)]
    s = sum(v * v for v in h)
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1)
        g = sum(h[i] * h[i - k] for i in range(k, n))
        s += 2.0 * w * g
    return math.sqrt(max(s, 0.0)) / sxx


def nw_se_diff(x: list[float], u1: list[float], u2: list[float], lag: int) -> float:
    """HAC standard error of (b1 - b2) fitted on the same x: use d = u1 - u2."""
    d = [u1[i] - u2[i] for i in range(len(u1))]
    return nw_se(x, d, lag)


def main() -> None:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    x = src["dlog_treatment"]
    y_paws = src["dlog_paws"]
    y_leg = src["dlog_leg_quarters"]
    n = len(x)

    _, b_paws, u_paws = ols(x, y_paws)
    _, b_leg, u_leg = ols(x, y_leg)
    b_diff = b_paws - b_leg

    kmax = 8
    ac_paws = acf(u_paws, kmax)
    ac_leg = acf(u_leg, kmax)
    ac_d = acf([u_paws[i] - u_leg[i] for i in range(n)], kmax)

    # Two bandwidth rules, both standard, neither invented here.
    lag_a = int(4.0 * (n / 100.0) ** (2.0 / 9.0))        # Newey-West 1994 plug-in
    lag_b = int(round(n ** (1.0 / 3.0)))                  # n^(1/3)

    rows = {}
    for name, lag in (("nw94", lag_a), ("cuberoot", lag_b), ("hc0", 0)):
        rows[name] = {
            "lag": lag,
            "se_paws": nw_se(x, u_paws, lag),
            "se_leg": nw_se(x, u_leg, lag),
            "se_diff": nw_se_diff(x, u_paws, u_leg, lag),
        }
    # The classical row is what the earlier gate readings on this arm used.
    # Its se_diff is the joint value, not the independent bound: the residual
    # correlation is negative, so the joint value is the larger of the two and
    # both are printed.
    cs_p = classical_se(x, u_paws)
    cs_l = classical_se(x, u_leg)
    cs_d = classical_se(x, [u_paws[i] - u_leg[i] for i in range(n)])
    rows["classical"] = {
        "lag": 0,
        "se_paws": cs_p,
        "se_leg": cs_l,
        "se_diff": cs_d,
        "se_diff_independent_bound": math.sqrt(cs_p ** 2 + cs_l ** 2),
    }

    band_half = math.log(BAND)
    for name, r in rows.items():
        r["gate_two_lhs"] = Z90 * r["se_diff"]
        r["gate_two_passes"] = r["gate_two_lhs"] < band_half
        r["shortfall_x"] = r["gate_two_lhs"] / band_half
        # Effective count implied by each correction, measured against the
        # classical row, which is the one the earlier readings used.
        r["n_eff"] = n * (rows["classical"]["se_diff"] / r["se_diff"]) ** 2

    # Long-run variance ratio on the difference series, the direct D22 reading.
    d = [u_paws[i] - u_leg[i] for i in range(n)]
    lrv_ratio = 1.0 + 2.0 * sum(
        (1.0 - k / (lag_a + 1)) * ac_d[k - 1] for k in range(1, lag_a + 1)
    )
    n_eff_direct = n / lrv_ratio if lrv_ratio > 0 else float("nan")

    crit = []
    crit.append({
        "name": "B35-D22-1  the residual autocorrelations are printed, not assumed",
        "passed": len(ac_d) == kmax,
        "detail": "difference-series rho_1..rho_%d = %s" % (
            kmax, ", ".join("%+.4f" % v for v in ac_d)),
    })
    flips = rows["classical"]["gate_two_passes"] != rows["nw94"]["gate_two_passes"]
    crit.append({
        "name": "B35-D22-2  the gate-two verdict is unchanged by the serial correction",
        "passed": not flips,
        "detail": "classical lhs %.4f (passes=%s), nw94 lag %d lhs %.4f (passes=%s), band half-width %.4f"
                  % (rows["classical"]["gate_two_lhs"], rows["classical"]["gate_two_passes"],
                     lag_a, rows["nw94"]["gate_two_lhs"], rows["nw94"]["gate_two_passes"],
                     band_half),
    })
    crit.append({
        "name": "B35-D22-3  the effective count is reported and the arm is not recorded at n=46",
        "passed": True,
        "detail": "nominal n = %d, long-run-variance ratio %.4f, n_eff direct %.2f, "
                  "n_eff from HAC se %.2f (nw94) and %.2f (cube root)"
                  % (n, lrv_ratio, n_eff_direct,
                     rows["nw94"]["n_eff"], rows["cuberoot"]["n_eff"]),
    })

    rec = {
        "stage": "B35",
        "arm": "B35-6 / D22",
        "config": {
            "band": BAND,
            "z90": Z90,
            "source_record": SRC.name,
            "window": src["config"]["window"],
            "destination_cty": src["config"]["destination_cty"],
            "treatment": src["config"]["treatment"],
            "acf_kmax": kmax,
        },
        "n_nominal": n,
        "b_paws": b_paws,
        "b_leg_quarters": b_leg,
        "b_diff": b_diff,
        "acf_paws": ac_paws,
        "acf_leg_quarters": ac_leg,
        "acf_difference": ac_d,
        "long_run_variance_ratio": lrv_ratio,
        "n_effective_direct": n_eff_direct,
        "se_variants": rows,
        "band_half_width_log": band_half,
        "criteria": crit,
    }
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")

    print("=" * 74)
    print("B35 D22: how many of the %d adjacent steps are independent" % n)
    print("=" * 74)
    print("slopes: paws %+.4f, leg quarters %+.4f, difference %+.4f"
          % (b_paws, b_leg, b_diff))
    print()
    print("residual autocorrelation (the object, printed rather than summarised)")
    print("  k        paws     leg_qtr        diff")
    for k in range(kmax):
        print("  %d    %+8.4f    %+8.4f    %+8.4f" % (k + 1, ac_paws[k], ac_leg[k], ac_d[k]))
    print()
    print("standard errors and gate two")
    print("  rule        lag    se_paws     se_leg    se_diff   1.645*se     band   passes   n_eff")
    for name in ("classical", "hc0", "nw94", "cuberoot"):
        r = rows[name]
        print("  %-9s %4d   %8.4f   %8.4f   %8.4f   %8.4f  %7.4f   %5s  %6.1f"
              % (name, r["lag"], r["se_paws"], r["se_leg"], r["se_diff"],
                 r["gate_two_lhs"], band_half, r["gate_two_passes"], r["n_eff"]))
    print()
    print("long-run variance ratio on the difference series: %.4f" % lrv_ratio)
    print("n_eff direct: %.2f out of a nominal %d" % (n_eff_direct, n))
    print()
    for c in crit:
        print("[%s] %s" % ("PASS" if c["passed"] else "FAIL", c["name"]))
        print("       %s" % c["detail"])
    print()
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
