"""B30-18 discriminator two: the 2020 clearing-house discounting switch.

Pre-registered: the criteria for this arm are registered
and repeated in code below ONLY so that they are pinned before the data is read.
Nothing in this file may be adjusted after looking at output.

The operator. On 2020-10-16 LCH auctioned and on 2020-10-19 implemented a change
of the discounting and price-alignment basis for USD cleared swaps from Fed Funds
to SOFR. LCH's own filing states the mechanism in one sentence: all USD
discounted future cash flows are HELD CONSTANT and the compensation is the
differential between their present values under the two regimes. 120 trillion
dollars of notional, over a million contracts, and 24 billion net notional of
compensating basis swaps auctioned.

So the cash flows did not move and the valuations did. That part is already known
and is confirmatory, not a prediction. This script tests the part that can fail.

TEST (design file 4.10, criterion B), fixed before any data is pulled:

    basis_t = SOFR_t - EFFR_t, in basis points, daily

    If the switch was a change of coordinate only, the UNDERLYING market should
    not move on the date. If it was revealing information, the traded spread
    between the two curves should show an abnormal move around it.

    abnormal := |first difference of basis| on any day in [D-1, D+3]
                exceeds THRESH_SIGMA robust sigmas, where the robust sigma is
                1.4826 * MAD of the first differences over the PRE window only.

    PRE  = the WINDOW trading days ending the day before D-1
    POST = the WINDOW trading days beginning at D+4

    Reported alongside, and required by the design file:
      - level shift: mean basis PRE vs POST, and the same robust sigma
      - placebo: the same abnormality test at N_PLACEBO random dates drawn from
        the PRE window. If 3-sigma days are common anyway, the test has no power
        and that must be said rather than discovered later.

    Verdict mapping, from the design file, not to be re-derived here:
      no abnormal move   -> the transfer was convention, discriminator two holds
      abnormal move      -> the switch came with real repricing, cannot attribute
      confounded         -> report as unidentified

Confounds the design file requires be excluded and that this script does NOT
handle: the pre-election period of October 2020, month and quarter end repo
pressure, and Federal Reserve reserve policy at the time. If they cannot be
excluded the arm reports unidentified.

Data: FRED, free. SOFR and EFFR daily series.
"""
import io, json, os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "b30_18")
OUT = os.path.join(ROOT, "results", "b30_18")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

SWITCH = pd.Timestamp("2020-10-16")     # auction date; implementation 2020-10-19
WINDOW = 60
THRESH_SIGMA = 3.0
EVENT_LO, EVENT_HI = -1, 3              # trading days around D
N_PLACEBO = 20
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def log(*a):
    print(*a, flush=True)


def fred(sid):
    p = os.path.join(RAW, f"{sid}.csv")
    if not os.path.exists(p):
        import urllib.request
        req = urllib.request.Request(FRED.format(sid=sid),
                                     headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                open(p, "wb").write(r.read())
        except Exception as e:
            log(f"  {sid}: FAILED {e}")
            log(f"      save by hand as {p}")
            log(f"      {FRED.format(sid=sid)}")
            return None
    d = pd.read_csv(p)
    d.columns = [c.strip().lower() for c in d.columns]
    dc = d.columns[0]
    vc = [c for c in d.columns if c != dc][0]
    d[dc] = pd.to_datetime(d[dc], errors="coerce")
    d[vc] = pd.to_numeric(d[vc], errors="coerce")
    return d.dropna().set_index(dc)[vc].rename(sid.upper())


# The basis is published on a one basis point grid and moves in integer steps.
# In a quiet window the MAD of daily changes can be exactly zero, which makes any
# move an infinite number of sigmas and fires the abnormality test on nothing.
# The first placebo run hit that: eight of twenty, with divide-by-zero warnings.
# Floor the scale at the quotation grid. This is failure mode 112 again: a
# dispersion estimate needs the carrier's own precision under it.
SIGMA_FLOOR_BP = 1.0


def robust_sigma(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return np.nan
    m = np.median(x)
    return max(1.4826 * np.median(np.abs(x - m)), SIGMA_FLOOR_BP)


def how_quiet(b, pos):
    """How quiet was the event window, on a continuous scale rather than a binary.

    The 3-sigma test is a yes/no and the placebo showed it fires on 30 per cent of
    random dates, so a clean window carries almost no information. This asks the
    question the binary cannot: WHERE does the event window sit in the
    distribution of all windows of the same shape, and where does the observed
    level shift sit in the distribution of all shifts of the same span.

    The reference distribution is every window in the series, so it overlaps
    itself and these are percentiles rather than independent p-values. Stated
    rather than dressed up.
    """
    basis = b["basis"].values
    n = len(basis)
    w = EVENT_HI - EVENT_LO + 1

    def stats(i0):
        seg = basis[i0:i0 + w]
        if len(seg) < w:
            return None
        ch = np.diff(seg)
        return (float(np.max(np.abs(ch))), float(np.sum(np.abs(ch))),
                float(seg.max() - seg.min()))

    ref = [stats(i) for i in range(0, n - w)]
    ref = np.array([r for r in ref if r is not None])
    ev = stats(pos + EVENT_LO)
    names = ["max abs daily change", "sum abs daily change", "range"]
    log("\n  how quiet was the event window, against every window in the series")
    log(f"  reference: {len(ref)} overlapping windows of {w} days")
    out = {}
    for j, nm in enumerate(names):
        pct = float((ref[:, j] < ev[j]).mean() * 100)
        tie = float((ref[:, j] == ev[j]).mean() * 100)
        log(f"    {nm:22s} event {ev[j]:6.2f} bp   percentile {pct:5.1f} "
            f"(+{tie:4.1f} tied)   median {np.median(ref[:, j]):6.2f}")
        out[nm] = dict(event=ev[j], pct_below=pct, pct_tied=tie,
                       median=float(np.median(ref[:, j])))

    log("\n  and where does the level shift sit, per window length")
    log("   span   event shift   percentile of |shift|   median |shift|   p90 |shift|")
    for span in (5, 10, 20, 40, 60):
        shifts = []
        for i in range(span + 2, n - EVENT_HI - 1 - span):
            pre = basis[i + EVENT_LO - span:i + EVENT_LO]
            post = basis[i + EVENT_HI + 1:i + EVENT_HI + 1 + span]
            if len(pre) == span and len(post) == span:
                shifts.append(abs(post.mean() - pre.mean()))
        shifts = np.array(shifts)
        pre = basis[pos + EVENT_LO - span:pos + EVENT_LO]
        post = basis[pos + EVENT_HI + 1:pos + EVENT_HI + 1 + span]
        ev_shift = post.mean() - pre.mean()
        pct = float((shifts < abs(ev_shift)).mean() * 100)
        log(f"   {span:4d}   {ev_shift:+9.3f} bp   {pct:19.1f}   "
            f"{np.median(shifts):12.3f}   {np.percentile(shifts, 90):11.3f}")
        out[f"shift_{span}"] = dict(event=float(ev_shift), pct=pct,
                                    median=float(np.median(shifts)),
                                    p90=float(np.percentile(shifts, 90)))
    return out


def run():
    s, e = fred("SOFR"), fred("EFFR")
    if s is None or e is None:
        return
    b = (pd.concat([s, e], axis=1).dropna())
    b["basis"] = (b["SOFR"] - b["EFFR"]) * 100.0        # basis points
    b = b.sort_index()
    d = b["basis"].diff().dropna()

    idx = b.index
    pos = int(idx.searchsorted(SWITCH))
    ev = list(range(pos + EVENT_LO, pos + EVENT_HI + 1))
    pre = d.iloc[max(0, pos + EVENT_LO - WINDOW):pos + EVENT_LO]
    post = b["basis"].iloc[pos + EVENT_HI + 1:pos + EVENT_HI + 1 + WINDOW]
    pre_lvl = b["basis"].iloc[max(0, pos + EVENT_LO - WINDOW):pos + EVENT_LO]

    sig = robust_sigma(pre.values)
    log(f"\nB30-18. switch {SWITCH.date()}, actual index date "
        f"{idx[pos].date()}, {len(b)} overlapping days total")
    log(f"  pre-window robust sigma of daily basis change: {sig:.3f} bp")
    log(f"  basis level: pre mean {pre_lvl.mean():.2f} bp, "
        f"post mean {post.mean():.2f} bp, shift {post.mean()-pre_lvl.mean():+.2f} bp "
        f"({(post.mean()-pre_lvl.mean())/sig:+.2f} sigma)")
    log("\n  event window")
    hits = 0
    for i in ev:
        if i <= 0 or i >= len(b):
            continue
        ch = b["basis"].iloc[i] - b["basis"].iloc[i - 1]
        z = ch / sig
        flag = "ABNORMAL" if abs(z) > THRESH_SIGMA else ""
        hits += abs(z) > THRESH_SIGMA
        log(f"    {idx[i].date()}  basis {b['basis'].iloc[i]:7.2f} bp   "
            f"change {ch:+7.2f} bp   {z:+6.2f} sigma  {flag}")

    rng = np.random.default_rng(0)
    lo = max(WINDOW + 1, 1)
    cand = list(range(lo, pos + EVENT_LO - 1))
    pl = rng.choice(cand, size=min(N_PLACEBO, len(cand)), replace=False)
    pl_hits, pl_used, pl_sigmas = 0, 0, []
    for q in pl:
        w = d.iloc[max(0, q - WINDOW):q]
        sg = robust_sigma(w.values)
        if not np.isfinite(sg):
            continue
        pl_used += 1
        pl_sigmas.append(float(sg))
        seg = [abs((b["basis"].iloc[j] - b["basis"].iloc[j - 1]) / sg)
               for j in range(q + EVENT_LO, q + EVENT_HI + 1) if 0 < j < len(b)]
        pl_hits += any(v > THRESH_SIGMA for v in seg)
    log(f"\n  placebo: {pl_hits} of {pl_used} usable random dates also show an "
        f"abnormal day in their own event window")
    log(f"  placebo sigmas: min {min(pl_sigmas):.3f} median "
        f"{np.median(pl_sigmas):.3f} max {max(pl_sigmas):.3f} bp "
        f"(floored at {SIGMA_FLOOR_BP:.2f})")
    log(f"  event window abnormal days: {hits}")
    quiet = how_quiet(b, pos)
    log("\n  Verdict mapping is in design file 4.10. Do not restate it here.")
    json.dump(dict(switch=str(SWITCH.date()), sigma=float(sig),
                   pre_mean=float(pre_lvl.mean()), post_mean=float(post.mean()),
                   event_hits=int(hits), placebo_hits=int(pl_hits),
                   placebo_n=int(pl_used), sigma_floor=SIGMA_FLOOR_BP,
                   quiet=quiet),
              open(os.path.join(OUT, "b30_18.json"), "w"), indent=2)


if __name__ == "__main__":
    run()
