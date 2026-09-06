"""B30-22 criterion D-prime, continuous-time closed form.

The monthly version (b30_22_icl.py) produced hundreds of spurious breakpoints on
Plan 2: the clearing MONTH is an integer, so it steps down as income rises and each
step is a tiny kink. That is quantisation of the instrument, not a class written by
the procedure. Failure mode 112: a reading needs a stated floor taken from the
instrument's own precision. Here the fix is to remove the quantisation instead of
setting a floor, by solving the amortisation in continuous time.

Constant real income y, constant real rate r(y), continuous repayment at rate
pay = max(0, y - threshold) * share.

    balance(t) = P e^{rt} - (pay/r)(e^{rt} - 1)          r > 0
    balance(t) = P - pay t                                r = 0

Clears at t* = (1/r) ln( pay / (pay - rP) ) when pay > rP, else never.
Lifetime total = pay * min(t*, T).
"""
import json
import numpy as np

PLANS = {
    "plan2": dict(threshold=29385.0, share=0.09, T=30.0,
                  band_lo=29385.0, band_hi=52885.0, r_lo=0.00, r_hi=0.03),
    "plan5": dict(threshold=25000.0, share=0.09, T=40.0,
                  band_lo=None, band_hi=None, r_lo=0.00, r_hi=0.00),
}


def real_rate(p, y):
    if p["band_lo"] is None or y <= p["band_lo"]:
        return p["r_lo"]
    if y >= p["band_hi"]:
        return p["r_hi"]
    f = (y - p["band_lo"]) / (p["band_hi"] - p["band_lo"])
    return p["r_lo"] + f * (p["r_hi"] - p["r_lo"])


def total_paid(p, P, y):
    pay = max(0.0, y - p["threshold"]) * p["share"]
    if pay <= 0.0:
        return 0.0, None
    r = real_rate(p, y)
    if r <= 0.0:
        t_star = P / pay
    elif pay > r * P:
        t_star = np.log(pay / (pay - r * P)) / r
    else:
        t_star = np.inf
    t = min(t_star, p["T"])
    return pay * t, (t_star if np.isfinite(t_star) and t_star <= p["T"] else None)


def main():
    ys = np.arange(18000.0, 150000.001, 5.0)
    res = {}
    for pname, p in PLANS.items():
        for P in (30000.0, 45000.0, 60000.0):
            tot = np.array([total_paid(p, P, y)[0] for y in ys])
            d = np.diff(tot) / np.diff(ys)
            dd = np.abs(np.diff(d))
            # floor: the largest second difference seen on a stretch the procedure
            # writes nothing on, here 100k-150k for plan5 and 120k-150k for plan2
            quiet = (ys[2:] > (120000.0 if pname == "plan2" else 100000.0))
            floor = float(np.max(dd[quiet])) if quiet.any() else 0.0
            thr = max(floor * 10.0, 1e-12)
            idx = np.where(dd > thr)[0]
            bps, run = [], []
            for i in idx:
                if run and i == run[-1] + 1:
                    run.append(i)
                else:
                    if run:
                        bps.append(float(ys[run[len(run) // 2] + 1]))
                    run = [i]
            if run:
                bps.append(float(ys[run[len(run) // 2] + 1]))
            k = int(np.argmax(tot))
            clear = next((float(y) for y in ys if total_paid(p, P, y)[1] is not None), None)
            key = f"{pname}_P{int(P)}"
            res[key] = dict(peak_income=float(ys[k]), peak_total=float(tot[k]),
                            peak_over_principal=float(tot[k] / P),
                            clearing_income=clear, floor=floor, threshold_used=thr,
                            monotone=bool(np.all(np.diff(tot) >= -1e-9)),
                            n_breakpoints=len(bps), breakpoints=bps)
            print(f"{key:13s} peak {ys[k]:>9,.0f} -> {tot[k]:>10,.0f} ({tot[k]/P:.2f}x)  "
                  f"clears from {clear if clear else float('nan'):>9,.0f}  "
                  f"monotone={np.all(np.diff(tot) >= -1e-9)!s:5s}  "
                  f"floor={floor:.2e}  breaks={[round(b) for b in bps]}")
    with open("../results/b30_22_icl_cont.json", "w") as f:
        json.dump(res, f, indent=2)
    print("\nwrote ../results/b30_22_icl_cont.json")


if __name__ == "__main__":
    main()
