"""B30-22 criterion D-prime, fourth instrument: grid-independent kink finder.

The third instrument (b30_22_icl_kink.py) used a centred ratio test on a fixed grid.
Diagnosis: the ratio only fires when the kink falls within h/4 of an evaluation point,
so its power depends on grid alignment, not on the size of the derivative jump. It
missed 5 of 13 genuine kinks, including the three largest (jump 4.38).

This version brackets instead of centring. On an interval [a,b] it compares the slope
of the left sixth with the slope of the right sixth. If they differ by more than TOL
the interval contains a kink and is bisected. Recursion to a width of 0.01 locates the
kink regardless of where the grid falls, and the recursion depth bounds the power:
any kink with a derivative jump above TOL is found.
"""
import json
import numpy as np

PLANS = {
    "plan2": dict(threshold=29385.0, share=0.09, T=30.0,
                  band_lo=29385.0, band_hi=52885.0, r_lo=0.00, r_hi=0.03),
    "plan5": dict(threshold=25000.0, share=0.09, T=40.0,
                  band_lo=None, band_hi=None, r_lo=0.00, r_hi=0.00),
}
TOL = 0.05          # smallest derivative jump the sweep is guaranteed to find
MIN_WIDTH = 0.01


def real_rate(p, y):
    if p["band_lo"] is None or y <= p["band_lo"]:
        return p["r_lo"]
    if y >= p["band_hi"]:
        return p["r_hi"]
    return p["r_lo"] + (y - p["band_lo"]) / (p["band_hi"] - p["band_lo"]) * (p["r_hi"] - p["r_lo"])


def f(p, P, y):
    pay = max(0.0, y - p["threshold"]) * p["share"]
    if pay <= 0.0:
        return 0.0
    r = real_rate(p, y)
    if r <= 0.0:
        t = min(P / pay, p["T"])
    elif pay > r * P:
        t = min(np.log(pay / (pay - r * P)) / r, p["T"])
    else:
        t = p["T"]
    return pay * t


def slope(p, P, a, b):
    return (f(p, P, b) - f(p, P, a)) / (b - a)


def find_kinks(p, P, a, b, out, depth=0):
    if b - a < MIN_WIDTH:
        j = slope(p, P, b, b + MIN_WIDTH) - slope(p, P, a - MIN_WIDTH, a)
        if abs(j) > TOL:
            out.append((0.5 * (a + b), float(j)))
        return
    w = (b - a) / 6.0
    sl, sr = slope(p, P, a, a + w), slope(p, P, b - w, b)
    if abs(sr - sl) <= TOL:
        return
    m = 0.5 * (a + b)
    find_kinks(p, P, a, m, out, depth + 1)
    find_kinks(p, P, m, b, out, depth + 1)


def clearing_income(p, P):
    lo, hi = p["threshold"] + 1.0, 1e7
    def clears(y):
        pay = max(0.0, y - p["threshold"]) * p["share"]
        if pay <= 0:
            return False
        r = real_rate(p, y)
        if r <= 0.0:
            return P / pay < p["T"]
        return pay > r * P and np.log(pay / (pay - r * P)) / r < p["T"]
    if not clears(hi):
        return None
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if clears(m):
            hi = m
        else:
            lo = m
    return 0.5 * (lo + hi)


def main():
    res, ok = {}, True
    for pname, p in PLANS.items():
        for P in (30000.0, 45000.0, 60000.0):
            named = {"threshold": p["threshold"]}
            if p["band_lo"] is not None:
                named["band_hi"] = p["band_hi"]
            ci = clearing_income(p, P)
            if ci is not None:
                named["clearing"] = ci
            out = []
            find_kinks(p, P, 20000.0, 200000.0, out)
            merged = []
            for y, j in sorted(out):
                if merged and y - merged[-1][0] < 1.0:
                    continue
                merged.append((y, j))
            unexplained = [(y, j) for y, j in merged
                           if all(abs(y - v) > 1.0 for v in named.values())]
            missed = {k: v for k, v in named.items()
                      if all(abs(v - y) > 1.0 for y, _ in merged)}
            key = f"{pname}_P{int(P)}"
            res[key] = dict(named={k: float(v) for k, v in named.items()},
                            found=[[float(y), float(j)] for y, j in merged],
                            unexplained=[[float(y), float(j)] for y, j in unexplained],
                            named_not_found=list(missed.keys()))
            if unexplained:
                ok = False
            print(f"{key:13s} found {len(merged)}: "
                  f"{[(round(y), round(j, 3)) for y, j in merged]}")
            print(f"{'':13s} named {{{', '.join(f'{k}:{v:,.0f}' for k, v in named.items())}}}  "
                  f"unexplained={[round(y) for y, _ in unexplained]}  "
                  f"named_not_found={list(missed.keys())}")
    with open("../results/b30_22_icl_kink2.json", "w") as fh:
        json.dump(dict(TOL=TOL, MIN_WIDTH=MIN_WIDTH, runs=res, no_unexplained=ok), fh, indent=2)
    print(f"\nTOL={TOL} (smallest derivative jump guaranteed found)")
    print(f"no unexplained kink in any run: {ok}")
    print("wrote ../results/b30_22_icl_kink2.json")


if __name__ == "__main__":
    main()
