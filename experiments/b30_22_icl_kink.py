"""B30-22 criterion D-prime, third instrument: separate kinks from curvature.

The first instrument (monthly simulation) reported quantisation steps as breakpoints.
The second (continuous closed form) removed that but still reported points where the
curvature crossed an absolute threshold on the second difference. Neither could tell a
kink from a smooth bend.

Discriminator, with its own floor:

    J(y, h) = [f(y+h) - f(y)]/h  -  [f(y) - f(y-h)]/h

At a genuine kink J converges to the size of the derivative jump as h shrinks.
On a smooth stretch J = f''(y) h + O(h^2), so it shrinks in proportion to h.
Evaluate at h and h/4 and take the ratio:

    ratio = |J(y, h/4)| / |J(y, h)|      ~ 1.0 at a kink,  ~ 0.25 on a smooth bend

Floor: |J| must also exceed EPS_J, set from the scale of f and double precision,
so that ratios computed from numerical noise are discarded.
"""
import json
import numpy as np

PLANS = {
    "plan2": dict(threshold=29385.0, share=0.09, T=30.0,
                  band_lo=29385.0, band_hi=52885.0, r_lo=0.00, r_hi=0.03),
    "plan5": dict(threshold=25000.0, share=0.09, T=40.0,
                  band_lo=None, band_hi=None, r_lo=0.00, r_hi=0.00),
}
EPS_J = 1e-6          # pounds per pound of income, per unit; noise floor
KINK_RATIO = 0.6      # ratio above this counts as a kink, below as smooth curvature


def real_rate(p, y):
    if p["band_lo"] is None or y <= p["band_lo"]:
        return p["r_lo"]
    if y >= p["band_hi"]:
        return p["r_hi"]
    f = (y - p["band_lo"]) / (p["band_hi"] - p["band_lo"])
    return p["r_lo"] + f * (p["r_hi"] - p["r_lo"])


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


def jump(p, P, y, h):
    return (f(p, P, y + h) - f(p, P, y)) / h - (f(p, P, y) - f(p, P, y - h)) / h


def clearing_income(p, P):
    """Lowest income at which the loan clears strictly before T. Bisection."""
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
        mid = 0.5 * (lo + hi)
        if clears(mid):
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def scan(p, P, ys, h=4.0):
    out = []
    for y in ys:
        j1 = jump(p, P, y, h)
        j2 = jump(p, P, y, h / 4.0)
        if abs(j1) < EPS_J:
            continue
        ratio = abs(j2) / abs(j1)
        if ratio > KINK_RATIO:
            out.append((float(y), float(j2), float(ratio)))
    # collapse neighbours
    merged = []
    for y, j, r in out:
        if merged and y - merged[-1][0] <= 3 * h:
            if abs(j) > abs(merged[-1][1]):
                merged[-1] = (y, j, r)
        else:
            merged.append((y, j, r))
    return merged


def main():
    res = {}
    ys = np.arange(20000.0, 150000.001, 5.0)
    for pname, p in PLANS.items():
        for P in (30000.0, 45000.0, 60000.0):
            named = {"threshold": p["threshold"]}
            if p["band_lo"] is not None:
                named["band_hi"] = p["band_hi"]
            ci = clearing_income(p, P)
            if ci is not None:
                named["clearing"] = ci
            # (a) test each named candidate
            at_named = {}
            for k, y in named.items():
                j1, j2 = jump(p, P, y, 4.0), jump(p, P, y, 1.0)
                ratio = abs(j2) / abs(j1) if abs(j1) > EPS_J else 0.0
                at_named[k] = dict(income=float(y), jump=float(j2), ratio=float(ratio),
                                   is_kink=bool(abs(j1) > EPS_J and ratio > KINK_RATIO))
            # (b) global sweep for any kink elsewhere
            found = scan(p, P, ys)
            unexplained = [t for t in found
                           if all(abs(t[0] - v) > 20.0 for v in named.values())]
            key = f"{pname}_P{int(P)}"
            res[key] = dict(named=at_named,
                            n_kinks_found=len(found),
                            kinks_found=[t[0] for t in found],
                            unexplained=[t[0] for t in unexplained])
            names = ", ".join(f"{k}@{v['income']:,.0f}:{'KINK' if v['is_kink'] else 'smooth'}"
                              for k, v in at_named.items())
            print(f"{key:13s} {names}")
            print(f"{'':13s} global sweep found {len(found)} kink(s) at "
                  f"{[round(t[0]) for t in found]}; unexplained {[round(t[0]) for t in unexplained]}")
    with open("../results/b30_22_icl_kink.json", "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote ../results/b30_22_icl_kink.json")


if __name__ == "__main__":
    main()
