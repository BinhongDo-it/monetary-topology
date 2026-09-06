"""B30-22 criterion D-prime, fifth and final instrument: no pruning, stated resolution.

Instrument history, each fault named:
  1  monthly simulation      : integer clearing month -> hundreds of quantisation kinks
  2  continuous + |f''| > c  : cannot tell a kink from a smooth bend
  3  centred ratio test      : fires only if a kink lands within h/4 of a grid point,
                               so its power tracks grid alignment, not jump size;
                               missed 5 of 13 genuine kinks including the three largest
  4  recursive end-slope     : prunes an interval whose two end sixths have equal slope,
                               which is exactly what happens when the interval contains
                               an even number of kinks; missed both kinks in 2 of 6 runs
  5  this one                : uniform interval slopes, no pruning at all

Resolution: interval width W. Any kink is located to within W.
Floor: a change in consecutive interval slopes above TOL. A kink of size J shows up as
consecutive slope changes summing to J, so every kink with |J| > TOL is found.
"""
import json
import numpy as np

PLANS = {
    "plan2": dict(threshold=29385.0, share=0.09, T=30.0,
                  band_lo=29385.0, band_hi=52885.0, r_lo=0.00, r_hi=0.03),
    "plan5": dict(threshold=25000.0, share=0.09, T=40.0,
                  band_lo=None, band_hi=None, r_lo=0.00, r_hi=0.00),
}
W = 1.0
TOL = 0.02
LO, HI = 20000.0, 200000.0


def real_rate(p, y):
    if p["band_lo"] is None or y <= p["band_lo"]:
        return p["r_lo"]
    if y >= p["band_hi"]:
        return p["r_hi"]
    return p["r_lo"] + (y - p["band_lo"]) / (p["band_hi"] - p["band_lo"]) * (p["r_hi"] - p["r_lo"])


def f_vec(p, P, ys):
    pay = np.maximum(0.0, ys - p["threshold"]) * p["share"]
    r = np.array([real_rate(p, y) for y in ys])
    t = np.full_like(ys, p["T"])
    zero = r <= 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        t_zero = np.where(pay > 0, P / np.where(pay > 0, pay, 1.0), np.inf)
        ok = (~zero) & (pay > r * P)
        t_pos = np.where(ok, np.log(np.where(ok, pay / np.where(ok, pay - r * P, 1.0), 1.0)) / np.where(r > 0, r, 1.0), p["T"])
    t = np.where(zero, np.minimum(t_zero, p["T"]), np.minimum(t_pos, p["T"]))
    return np.where(pay > 0, pay * t, 0.0)


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
    ys = np.arange(LO, HI + W, W)
    res, ok = {}, True
    for pname, p in PLANS.items():
        for P in (30000.0, 45000.0, 60000.0):
            v = f_vec(p, P, ys)
            sl = np.diff(v) / W
            ch = np.diff(sl)
            idx = np.where(np.abs(ch) > TOL)[0]
            groups, run = [], []
            for i in idx:
                if run and i == run[-1] + 1:
                    run.append(i)
                else:
                    if run:
                        groups.append(run)
                    run = [i]
            if run:
                groups.append(run)
            found = [(float(ys[g[0] + 1]), float(sum(ch[j] for j in g))) for g in groups]
            named = {"threshold": p["threshold"]}
            if p["band_lo"] is not None:
                named["band_hi"] = p["band_hi"]
            ci = clearing_income(p, P)
            if ci is not None:
                named["clearing"] = ci
            unexplained = [(y, j) for y, j in found
                           if all(abs(y - vv) > 3 * W for vv in named.values())]
            not_found = [k for k, vv in named.items()
                         if all(abs(vv - y) > 3 * W for y, _ in found)]
            key = f"{pname}_P{int(P)}"
            res[key] = dict(named={k: float(vv) for k, vv in named.items()},
                            found=[[y, j] for y, j in found],
                            unexplained=[[y, j] for y, j in unexplained],
                            named_with_no_kink=not_found)
            if unexplained:
                ok = False
            print(f"{key:13s} kinks {[(round(y), round(j, 3)) for y, j in found]}")
            print(f"{'':13s} named {{{', '.join(f'{k}:{vv:,.0f}' for k, vv in named.items())}}}"
                  f"  unexplained={[round(y) for y, _ in unexplained]}"
                  f"  named_with_no_kink={not_found}")
    with open("../results/b30_22_icl_kink3.json", "w") as fh:
        json.dump(dict(W=W, TOL=TOL, range=[LO, HI], runs=res, no_unexplained=ok), fh, indent=2)
    print(f"\nresolution W={W} pound, floor TOL={TOL} on the slope change")
    print(f"no unexplained kink in any run: {ok}")
    print("wrote ../results/b30_22_icl_kink3.json")


if __name__ == "__main__":
    main()
