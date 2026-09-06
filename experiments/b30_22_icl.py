"""B30-22 criterion D-prime: breakpoints of lifetime total paid as a function of income.

Carrier: UK income-contingent student loans, Plan 2 and Plan 5.
Terms from House of Commons Library briefing CBP-10654.

Everything is in REAL terms, so RPI = 0. Plan 5's rate is RPI only, hence 0 real.
Plan 2's post-study rate runs from RPI at the lower band edge to RPI+3% at the upper,
hence 0% to 3% real, linear in between. Thresholds held fixed in real terms.

Income path: constant real income. This is the strong simplification registered
in chunk twenty-four; conclusions are about the shape under this simplification.
"""
import json
import numpy as np

PLANS = {
    "plan2": dict(threshold=29385.0, rate=0.09, years=30,
                  band_lo=29385.0, band_hi=52885.0, real_lo=0.00, real_hi=0.03),
    "plan5": dict(threshold=25000.0, rate=0.09, years=40,
                  band_lo=None, band_hi=None, real_lo=0.00, real_hi=0.00),
}


def real_rate(p, income):
    if p["band_lo"] is None:
        return p["real_lo"]
    if income <= p["band_lo"]:
        return p["real_lo"]
    if income >= p["band_hi"]:
        return p["real_hi"]
    f = (income - p["band_lo"]) / (p["band_hi"] - p["band_lo"])
    return p["real_lo"] + f * (p["real_hi"] - p["real_lo"])


def lifetime_total(p, principal, income):
    """Monthly simulation. Returns (total paid, months to clear or None)."""
    r_m = real_rate(p, income) / 12.0
    pay_m = max(0.0, income - p["threshold"]) * p["rate"] / 12.0
    bal = principal
    total = 0.0
    for m in range(p["years"] * 12):
        bal *= (1.0 + r_m)
        if bal <= 0.0:
            return total, m
        step = min(pay_m, bal)
        bal -= step
        total += step
        if bal <= 1e-9:
            return total, m + 1
    return total, None


def curve(p, principal, incomes):
    return np.array([lifetime_total(p, principal, y)[0] for y in incomes])


def breakpoints(incomes, totals, tol):
    """Income values where the slope of totals-vs-income changes by more than tol."""
    d = np.diff(totals) / np.diff(incomes)
    dd = np.diff(d)
    idx = np.where(np.abs(dd) > tol)[0]
    # collapse runs of adjacent indices to their centre
    out, run = [], []
    for i in idx:
        if run and i == run[-1] + 1:
            run.append(i)
        else:
            if run:
                out.append(incomes[run[len(run) // 2] + 1])
            run = [i]
    if run:
        out.append(incomes[run[len(run) // 2] + 1])
    return out


def main():
    incomes = np.arange(18000.0, 150001.0, 25.0)
    res = {}
    for pname, p in PLANS.items():
        for principal in (30000.0, 45000.0, 60000.0):
            tot = curve(p, principal, incomes)
            peak_i = int(np.argmax(tot))
            # clearing income: lowest income at which the loan is repaid before write-off
            cleared = [lifetime_total(p, principal, y)[1] is not None for y in incomes]
            clear_income = None
            for y, c in zip(incomes, cleared):
                if c:
                    clear_income = float(y)
                    break
            bps = breakpoints(incomes, tot, tol=1e-3)
            key = f"{pname}_P{int(principal)}"
            res[key] = dict(
                plan=pname, principal=principal,
                peak_income=float(incomes[peak_i]), peak_total=float(tot[peak_i]),
                total_at_peak_over_principal=float(tot[peak_i] / principal),
                clearing_income=clear_income,
                total_at_150k=float(tot[-1]),
                monotone_nondecreasing=bool(np.all(np.diff(tot) >= -1e-6)),
                breakpoints=[float(b) for b in bps],
            )
            print(f"{key:14s} peak at income {incomes[peak_i]:>9,.0f} "
                  f"total {tot[peak_i]:>10,.0f} ({tot[peak_i]/principal:.2f}x principal)  "
                  f"clears from {clear_income if clear_income else float('nan'):>9,.0f}  "
                  f"monotone={np.all(np.diff(tot) >= -1e-6)}  "
                  f"breaks={[round(b) for b in bps]}")
    # plan2 vs plan5 same income same principal
    print()
    print("cohort comparison, principal 45,000, same constant real income:")
    for y in (25000, 30000, 40000, 55000, 80000, 120000):
        t2 = lifetime_total(PLANS["plan2"], 45000.0, float(y))[0]
        t5 = lifetime_total(PLANS["plan5"], 45000.0, float(y))[0]
        print(f"  income {y:>7,}  plan2 {t2:>10,.0f}   plan5 {t5:>10,.0f}   diff {t2-t5:>10,.0f}")
        res[f"cohort_{y}"] = dict(income=y, plan2=float(t2), plan5=float(t5), diff=float(t2 - t5))
    with open("../results/b30_22_icl.json", "w") as f:
        json.dump(res, f, indent=2)
    print("\nwrote ../results/b30_22_icl.json")


if __name__ == "__main__":
    main()
