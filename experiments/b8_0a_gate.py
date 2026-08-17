#!/usr/bin/env python3
"""B8-0a: the clean-cure round trip, block two.

Registered in ``docs/b8_fannie_slice.md`` §14.5 and §16, and
``docs/b8_inputs_availability.md`` §6.2.10. Reads the core table and the
construction in ``b8_omega.py``. **Reads no prediction.**

--------------------------------------------------------------------------
What the gate compares against, and why it is not zero
--------------------------------------------------------------------------

§14.5 required the round trip to return **zero to floating-point tolerance** and
called that zero arithmetic. ``b8_omega.py``'s P4 shows it is not. With
``f(B) = B(1+i) - P`` the loop sum over ``k`` missed months and a reinstatement
is ``k log B0 - (k+1) log f(B0) + log f^(k+1)(B0)``, which vanishes only if
``f`` were multiplicative, and it is affine. On a perfectly clean synthetic loan
the round trip returns -9e-6 to -6e-4, eleven orders above floating point.

**So the target is the closed form, not zero** (ruled 2026-08-16). The gate
compares two computations that share only ``(B0, i, P, k)``:

  * the **streaming** sum, walking the loan's rows month by month through
    ``b8_omega.r_month``,
  * the **closed form**, ``b8_omega.loop_residual_ideal``, four scalars.

Agreement to floating point says the payment is right, the dates line up and the
curve is applied consistently across both sides, which is exactly the three
things §14.5 wanted the gate to catch. This is the shape ``b1_theorem.py``'s
B1-6 already uses in this repository, an enumeration slow path against a closed
form, and ``OBJECTIONS.md`` A23 records its independent defence.

**The count is half the gate.** A loop only qualifies when its observed balance
path matches the ideal one: flat through the delinquency, and landing on
``f^(k+1)(B0)`` at the reinstatement, both to cent tolerance. **If the payment
estimate or the date alignment were wrong, almost no loop would qualify and that
count would collapse.** So the qualifying count tests ``P`` and the dates, and
the agreement tests the machinery.

--------------------------------------------------------------------------
The two readings
--------------------------------------------------------------------------

**B8-0a(i-a), the gate.** Loops on loans that are clean-cure shaped, fixed-rate
shaped, fully covered, and **every one of whose quiet months sits in its segment's
modal cluster**. Pass requires the streaming sum to equal the closed form to
floating point on every qualifying loop.

**B8-0a(i-b), a reading and not a gate.** The same residual on **all** clean-cure
loops, beside a noise floor drawn from never-delinquent loans over windows of
matched length. A never-delinquent window has ``k = 0``, so its closed form is
zero and its streaming sum is whatever freezes and curtailments put there. That
is the floor, and C8-1f measured its per-segment median absolute value at 2.55
to 4.19 per cent, which is why it is not used as a gate.

**Two limitations that travel with (i-a) wherever it is quoted**, per §16.3:
the subsample skews hard to the newest archives, and it is selected on payment
regularity, which correlates with the class index, so **it must not be reused as
the sample for any B8-4 shaped reading**.

Usage::

    python experiments/b8_0a_gate.py --selftest
    python experiments/b8_0a_gate.py

Writes ``results/b8_0a_gate.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K       # noqa: E402
import b8_omega as W      # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b8_0a_gate.md"

#: The **loose** ideal-path tolerance the first run used, kept so its numbers can
#: be reproduced. **It is incoherent with the agreement bound below**, which is
#: derived from half a cent, so a loop deviating by two or three cents passed the
#: path filter and then necessarily broke a bound that allows half a cent. That
#: is a construction defect independent of which way the verdict goes, and both
#: columns are reported side by side.
IDEAL_TOL_LOOSE = 0.05


def ideal_tol(note_pct, k):
    """The **derived** ideal-path tolerance, from the same half cent.

    The flat check compares two rounded balances, so it allows ``2 * HALF_CENT``.
    The endpoint check compares a rounded ``bal[b]`` against ``f^(k+1)`` of a
    rounded ``bal[a]``, and ``f``'s slope is ``1 + i``, so it allows
    ``HALF_CENT * (1 + (1+i)^(k+1))``. The looser of the two is returned. At
    every ``k`` from 1 to 6 it lands near one cent, against the five cents the
    first run used.
    """
    i = float(note_pct) / 1200.0
    return max(2.0 * HALF_CENT,
               HALF_CENT * (1.0 + (1.0 + i) ** (int(k) + 1)))

#: Half a cent. **The gate's tolerance is derived from this and from the loop's
#: own parameters, not chosen.** The file prints UPB to two decimals, so every
#: balance carries up to half a cent, and a criterion with a number in it needs a
#: source (纪律 5). The per-loop bound is
#:
#:     0.005 * ( (2 + i) * (k + 1)  +  (1 + i)^(k+1) ) / min(balance in the loop)
#:
#: The first term is the k+1 residuals, each of which reads one rounded balance
#: directly and one through ``f``, whose slope is ``1 + i``. The second is the
#: closed form's own sensitivity to the rounded ``B0`` it starts from, carried
#: through k+1 applications of ``f``. **The gate reports the maximum of
#: |stream - closed| divided by this bound and passes below one**, so the number
#: printed is a ratio against a derived quantity rather than against a constant
#: someone picked.
HALF_CENT = 0.005

#: Windows drawn from never-delinquent loans for the (i-b) floor, in months.
FLOOR_LENS = (2, 3, 4, 7)


def _prefix(flag: np.ndarray) -> np.ndarray:
    """``P[j] = sum(flag[:j])`` so a range sum is ``P[b+1] - P[a]``."""
    out = np.zeros(flag.size + 1, dtype=np.int64)
    np.cumsum(flag, out=out[1:])
    return out


def find_clean_cures(c: K.Core, require_no_defer: bool = True):
    """Every ``current -> delinquent -> current`` episode with nothing else in it.

    ``require_no_defer`` excludes windows carrying a positive **field 108**, and
    it is the 2026-08-17 correction (O28, `b8_inputs_availability.md` §6.6.17).
    The window already excluded a modification flag and a positive field 63 and
    said nothing about 108, because until C10-4 nobody had looked at that
    column. **A payment deferral moves missed payments into a balloon, which is
    an event, so a window carrying one is not a clean cure** — the same
    sentence that justifies excluding field 63.

    Pit 14 in its own words: a property held by a lucky precondition breaks at
    the first station that does not carry it. ``find_clean_cures`` was safe only
    because no earlier station read field 108.

    ``require_no_defer=False`` reproduces the pre-correction sample, which is
    what B8-0a(i-a)'s published numbers were produced on. **It is kept, not
    deleted**: a sample that cannot be reproduced cannot be checked.

    Returns ``(t0, start, end, k)`` as row indices. ``t0`` is the last current
    month before the episode, ``start`` the first delinquent month, ``end`` the
    first current month after, and ``k = end - start`` the number of missed
    months. §14.6 makes ``t0..end`` the loop window and the residual runs over
    ``t0+1 .. end``, which is ``k + 1`` months.

    An episode is dropped when any row of the window carries a modification flag
    or a positive deferred balance, when the reporting periods are not
    consecutive across the whole window, or when any field the residual needs is
    missing. Every drop is counted.
    """
    dq = c.row["delinq"][:]
    loan = c.loan_of_row()
    period = c.row["period"][:].astype(np.int64)
    n = c.n_rows

    dq0 = dq == 0
    dqp = (dq > 0) & (dq < 253)
    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]

    starts = np.flatnonzero(dqp & np.concatenate(([False], dq0[:-1])) & same)
    ends = np.flatnonzero(dq0 & np.concatenate(([False], dqp[:-1])) & same)
    if starts.size == 0 or ends.size == 0:
        z = np.zeros(0, dtype=np.int64)
        return z, z, z, z, {"raw": 0}

    # pair each start with the first end after it, then keep only pairs inside
    # one loan whose interior is entirely delinquent
    j = np.searchsorted(ends, starts, side="left")
    ok = j < ends.size
    starts, j = starts[ok], j[ok]
    ends_p = ends[j]
    keep = loan[starts] == loan[ends_p]
    starts, ends_p = starts[keep], ends_p[keep]
    t0 = starts - 1
    k = (ends_p - starts).astype(np.int64)
    drops = {"raw": int(starts.size)}

    def rng(pref, a, b):
        """sum over rows a..b inclusive"""
        return pref[b + 1] - pref[a]

    modY = c.row["mod_flag"][:] == ord("Y")
    nibp = (c.row["nib_upb"][:] != K.U32_NA) & (c.row["nib_upb"][:] > 0)
    gap = np.zeros(n, dtype=np.int64)
    gap[1:] = ((period[1:] - period[:-1] != 1) | ~same[1:]).astype(np.int64)
    notdq = (~dqp).astype(np.int64)

    p_mod, p_nib, p_gap, p_ndq = (_prefix(modY.astype(np.int64)),
                                  _prefix(nibp.astype(np.int64)),
                                  _prefix(gap), _prefix(notdq))

    m = rng(p_mod, t0, ends_p) == 0
    drops["mod_in_window"] = int((~m).sum())
    m &= rng(p_nib, t0, ends_p) == 0
    if require_no_defer:
        dfr = c.row["defer_amt"][:]
        p_dfr = _prefix(((dfr != K.U32_NA) & (dfr > 0)).astype(np.int64))
        no_d = rng(p_dfr, t0, ends_p) == 0
        # counted on its own, before the earlier conditions have had their turn,
        # so the figure reads as "what field 108 removes" rather than "what is
        # left over after everything else"
        drops["defer_in_window_alone"] = int((~no_d).sum())
        drops["defer_in_window"] = int((m & ~no_d).sum())
        m &= no_d
    m &= rng(p_gap, t0 + 1, ends_p) == 0
    m &= rng(p_ndq, starts, ends_p - 1) == 0

    upb = c.row["upb"][:]
    rate = c.row["rate"][:]
    m &= (upb[t0] != K.U32_NA) & (upb[t0] > 0) & (rate[t0] != K.U16_NA)
    drops["kept"] = int(m.sum())
    drops["dropped"] = int(starts.size - m.sum())
    return t0[m], starts[m], ends_p[m], k[m], drops


def rounding_bound(b_min, note_pct, k):
    """The most that cent-rounding alone can move ``stream - closed``."""
    i = float(note_pct) / 1200.0
    kk = int(k)
    return HALF_CENT * ((2.0 + i) * (kk + 1) + (1.0 + i) ** (kk + 1)) / b_min


def episode_sums(c: K.Core, pay_row, t0, ends, k):
    """Streaming residual, closed form, ideal-path flag, and rounding bound."""
    # **interest-bearing, `12 - 63 - 108`** (C8-1, C11-1), through the one
    # shared copy in `b8_core`. It used to net field 63 here by hand, which was
    # right for the population `find_clean_cures` returns (that screens both
    # fields) and would have gone quietly wrong the day the population widened.
    bal = K.zero_interest_split(c)[0].astype(np.float64) / 100.0
    rate = c.row["rate"][:].astype(np.float64) / 1000.0
    rem = c.row["rem_legal"][:].astype(np.float64)

    stream = np.empty(t0.size)
    closed = np.empty(t0.size)
    bound = np.empty(t0.size)
    pathdev = np.full(t0.size, np.nan)
    ideal = np.zeros(t0.size, dtype=bool)
    tight = np.zeros(t0.size, dtype=bool)
    bad = np.zeros(t0.size, dtype=bool)
    bad_closed = np.zeros(t0.size, dtype=bool)   # counted, not swallowed

    for e in range(t0.size):
        a, b = int(t0[e]), int(ends[e])
        P = float(pay_row[a])
        note = float(rate[a])
        i = note / 1200.0
        if not np.isfinite(P) or P <= 0 or note <= 0:
            bad[e] = True
            stream[e] = closed[e] = bound[e] = np.nan
            continue
        s = 0.0
        good = True
        bmin = bal[a]
        for t in range(a + 1, b + 1):
            bprev, bnow = bal[t - 1], bal[t]
            bhat = bprev * (1.0 + i) - P
            if bhat <= 0 or bnow <= 0:
                good = False
                break
            bmin = min(bmin, bnow, bhat)
            s += np.log(bnow) - np.log(bhat)
        if not good:
            bad[e] = True
            stream[e] = closed[e] = bound[e] = np.nan
            continue
        stream[e] = s
        bound[e] = rounding_bound(bmin, note, int(k[e]))
        tol_t = ideal_tol(note, int(k[e]))
        closed[e] = float(W.loop_residual_ideal(bal[a], note, P, int(k[e])))
        if not np.isfinite(closed[e]):
            bad_closed[e] = True
            # ``f(B0) <= 0``: the payment exceeds balance plus interest, which
            # is a loop on a loan within a payment or two of payoff. The closed
            # form has no logarithm there. **Counted rather than swallowed by a
            # later ``nanmax``**, which is the same silent drop this file
            # complains about elsewhere.
            bad[e] = True
            continue
        # the observed path against the ideal one
        dev_flat = float(np.max(np.abs(bal[a + 1:b] - bal[a]))) \
            if b > a + 1 else 0.0
        bs = bal[a]
        for _ in range(int(k[e]) + 1):
            bs = bs * (1.0 + i) - P
        dev = max(dev_flat, abs(bal[b] - bs))
        pathdev[e] = dev
        ideal[e] = bool(dev <= IDEAL_TOL_LOOSE)
        tight[e] = bool(dev <= tol_t)
    return stream, closed, ideal, tight, bad, bound, pathdev, bad_closed


#: The floor loop is per-loan python, so it is capped and **the cap is logged**.
#: A silent truncation reads as "covered everything" when it did not.
FLOOR_CAP = 30000


def noise_floor(c: K.Core, pay_row, rate_filled, lens=FLOOR_LENS,
                cap=FLOOR_CAP, screen_zib: bool = True):
    """The (i-b) floor: the same sum on never-delinquent loans.

    A window with no delinquency has ``k = 0``, so its closed form is zero and
    its streaming sum is whatever freezes and curtailments put there. One window
    per eligible loan, anchored at the loan's first row that has ``len`` further
    contiguous rows, so the draw does not depend on any outcome.

    ``screen_zib=False`` reproduces the population this table was published on
    before 2026-08-17: delinquency and the modification flag screened, **the
    two zero-interest balances not**. It exists so both readings come out of
    one run rather than out of two runs on different days (R01, §6.6.17.1), and
    it is not a switch anything should be run under going forward.
    """
    dq = c.row["delinq"][:]
    loan = c.loan_of_row()
    period = c.row["period"][:].astype(np.int64)
    bal = K.zero_interest_split(c)[0].astype(np.float64) / 100.0
    # **the filled rate**, not the raw column. A blank field 9 stores as 65535
    # and reads back as a 65.5 per cent note rate, which is the defect that left
    # this table empty on its first run.
    rate = np.where(rate_filled == K.U16_NA, np.nan,
                    rate_filled.astype(np.float64) / 1000.0)

    starts = c.row_start.astype(np.int64)
    counts = c.n_per_loan.astype(np.int64)
    dqp = ((dq > 0) & (dq < 253)).astype(np.int64)
    modY = (c.row["mod_flag"][:] == ord("Y")).astype(np.int64)
    # **The two zero-interest screens are new on 2026-08-17.** The floor is the
    # same sum on loans where nothing happened, and a loan carrying either
    # balance has had something happen to it: field 63 is a re-contracting
    # (C10-4) and field 108 is a deferral. Either one puts a step into the
    # balance path that the floor would then report as ambient noise, which
    # **raises the floor the gate is measured against** and makes the gate
    # easier to pass. `find_clean_cures` has screened both since C10-4 landed;
    # this mask screened neither, so the numerator and the denominator of the
    # (i-b) reading were drawn from two different populations.
    clean = ((np.add.reduceat(dqp, starts) == 0)
             & (np.add.reduceat(modY, starts) == 0))
    if screen_zib:
        nibr = c.row["nib_upb"][:]
        dfrr = c.row["defer_amt"][:]
        nibp = ((nibr != K.U32_NA) & (nibr > 0)).astype(np.int64)
        dfrp = ((dfrr != K.U32_NA) & (dfrr > 0)).astype(np.int64)
        clean = (clean
                 & (np.add.reduceat(nibp, starts) == 0)
                 & (np.add.reduceat(dfrp, starts) == 0))

    # **The window is anchored at the loan's first usable row, not its first
    # row.** Field 12 reads a literal zero on the opening rows of many loans,
    # which left this table empty on its first two runs. The anchor depends only
    # on which fields are present, never on an outcome, so it introduces no
    # selection on the quantity being measured.
    upb_raw = c.row["upb"][:]
    usable = ((upb_raw != K.U32_NA) & (upb_raw > 0)
              & (rate_filled != K.U16_NA))
    n = c.n_rows
    ii = np.arange(n, dtype=np.int64)
    first_ok = np.minimum.accumulate(np.where(usable, ii, n)[::-1])[::-1]
    anchor = first_ok[starts]
    last_row = starts + counts - 1
    out, why = {}, {}
    for L in lens:
        vals = []
        cand = np.flatnonzero(clean & (anchor + L <= last_row))
        w = {"clean_loans": int(clean.sum()), "candidates": int(cand.size),
             "no_anchor": int((clean & (anchor + L > last_row)).sum()),
             "capped_at": 0, "skip_gap": 0, "skip_pay": 0, "skip_rate": 0,
             "skip_path": 0, "examples": []}
        if cand.size > cap:
            w["capped_at"] = cap
            cand = cand[:cap]
        for li in cand.tolist():
            a = int(anchor[li])
            b = a + L
            if period[b] - period[a] != L:
                w["skip_gap"] += 1
                continue
            if not bool(usable[a:b + 1].all()):
                w["skip_path"] += 1
                continue
            P = float(pay_row[a])
            note = float(rate[a])
            if not np.isfinite(note) or note <= 0:
                w["skip_rate"] += 1
                continue
            if not np.isfinite(P) or P <= 0:
                w["skip_pay"] += 1
                continue
            i = note / 1200.0
            s, good = 0.0, True
            for t in range(a + 1, b + 1):
                bhat = bal[t - 1] * (1.0 + i) - P
                if bhat <= 0 or bal[t] <= 0:
                    good = False
                    break
                s += np.log(bal[t]) - np.log(bhat)
            if good:
                vals.append(s)
            else:
                w["skip_path"] += 1
                # **Print the values, do not guess at them.** The first run of
                # this table came back empty on all six archives and no amount
                # of reading the code settled why.
                if len(w["examples"]) < 5:
                    w["examples"].append({
                        "loan": int(li), "row0": a, "t": int(t),
                        "bal_prev": float(bal[t - 1]), "bal_now": float(bal[t]),
                        "bhat": float(bhat), "P": P, "note": note,
                        "upb_prev_raw": int(c.row["upb"][t - 1]),
                        "nib_prev_raw": int(c.row["nib_upb"][t - 1]),
                        "rate_raw": int(c.row["rate"][a]),
                        "rate_filled": int(rate_filled[a]),
                    })
        out[L] = np.array(vals)
        why[L] = w
    return out, why


#: **The column list `analyse` opens the core table with**, hoisted so the
#: selftest opens its fixture with the same one. Pit 30, and `defer_amt` is here
#: because O28's correction reads it.
GATE_COLS = ["period", "rate", "upb", "rem_legal", "delinq", "mod_flag",
             "nib_upb", "defer_amt"]
GATE_LOAN_COLS = ["orig_term"]


def analyse(name: str, floor_cap: int = 40000,
            require_no_defer: bool = True, cache_root=None) -> dict:
    c = K.Core(name, cols=GATE_COLS, loan_cols=GATE_LOAN_COLS,
               cache_root=cache_root)
    try:
        q = K.quiet_pairs(c)
        period_id = W.contract_periods(c, fill=True)
        pay_row, known_row, _ = W.contract_payments(c, period_id, q)

        # the (i-a) selection: every quiet month inside its modal cluster
        seg = K.segment_ids(q)
        mode, lo, hi, _, _, _, implied = K.segment_modes(q, seg)
        off = (implied < lo) | (implied > hi)
        loan_off = np.zeros(c.n_loans, dtype=bool)
        loan_off[np.unique(q["loan"][off])] = True
        has_quiet = np.zeros(c.n_loans, dtype=bool)
        has_quiet[np.unique(q["loan"])] = True

        start, end = W._row_bounds(c)
        rate_f = W.fill_within_loan(c.row["rate"][:], K.U16_NA, start, end)
        cls, _, _ = W.rate_path_class(c, rate_f)  # rate_f reused by the floor
        loan_row = c.loan_of_row()
        covered = np.bincount(loan_row,
                              weights=(~known_row).astype(np.float64),
                              minlength=c.n_loans) == 0
        eligible = has_quiet & ~loan_off & (cls != 2) & covered

        t0, st, en, k, drops = find_clean_cures(
            c, require_no_defer=require_no_defer)
        # **Field 12 reads a literal zero on the opening rows of many loans.**
        # Nothing in B8 had noticed, because the quiet filter requires a
        # positive previous UPB and find_clean_cures requires one at t0, so
        # every earlier reading skipped them by accident rather than on purpose.
        # It is measured here so the next stage does not rediscover it.
        upb_raw = c.row["upb"][:]
        zero_upb = upb_raw == 0
        idx_all = np.arange(c.n_rows, dtype=np.int64)
        lstart = np.repeat(c.row_start.astype(np.int64),
                           c.n_per_loan.astype(np.int64))
        lcount = np.repeat(c.n_per_loan.astype(np.int64),
                           c.n_per_loan.astype(np.int64))
        frac = (idx_all - lstart) / np.maximum(lcount, 1)
        a = {"name": name, "require_no_defer": require_no_defer,
             "drops": drops, "n_loops": int(t0.size),
             "n_rows": c.n_rows, "n_loans": c.n_loans,
             "n_eligible_loans": int(eligible.sum()),
             "zero_upb_rows": int(zero_upb.sum()),
             "zero_upb_frac_q": (np.percentile(frac[zero_upb],
                                               [10, 50, 90]).tolist()
                                 if zero_upb.any() else [float("nan")] * 3),
             "loans_zero_first": int(zero_upb[c.row_start.astype(np.int64)].sum()),
             }
        if t0.size == 0:
            a["empty"] = True
            return a

        (stream, closed, ideal, tight, bad, bound, pathdev,
         bad_closed) = episode_sums(c, pay_row, t0, en, k)
        sel = eligible[loan_row[t0]]
        a["n_loops_ia"] = int(sel.sum())
        a["n_bad"] = int(bad.sum())
        a["n_bad_closed"] = int(bad_closed.sum())
        a["n_bad_path"] = int((bad & ~bad_closed).sum())

        d = stream - closed
        okm = ~bad
        a["ideal_all"] = int((ideal & okm).sum())
        a["ideal_ia"] = int((ideal & okm & sel).sum())

        g = ideal & okm & sel
        a["ideal_ia_tight"] = int((tight & okm & sel).sum())
        a["pathdev_q"] = (np.nanpercentile(pathdev[g], [50, 90, 99]).tolist()
                          if g.any() else [float("nan")] * 3)
        for tag, gg in (("loose", g), ("tight", tight & okm & sel)):
            if gg.any():
                ratio = np.abs(d[gg]) / bound[gg]
                a[f"{tag}_n"] = int(gg.sum())
                a[f"{tag}_max"] = float(np.nanmax(np.abs(d[gg])))
                a[f"{tag}_bound_med"] = float(np.nanmedian(bound[gg]))
                a[f"{tag}_ratio_max"] = float(np.nanmax(ratio))
                a[f"{tag}_ratio_q"] = np.nanpercentile(
                    ratio, [50, 90, 99]).tolist()
                a[f"{tag}_pass"] = bool(a[f"{tag}_ratio_max"] < 1.0)
                a[f"{tag}_over"] = int((ratio >= 1.0).sum())
            else:
                for kk in ("n", "over"):
                    a[f"{tag}_{kk}"] = 0
                for kk in ("max", "bound_med", "ratio_max"):
                    a[f"{tag}_{kk}"] = float("nan")
                a[f"{tag}_ratio_q"] = [float("nan")] * 3
                a[f"{tag}_pass"] = False
        if g.any():
            a["closed_q"] = np.nanpercentile(closed[g], [10, 50, 90]).tolist()
            a["k_q"] = np.percentile(k[g], [10, 50, 90]).tolist()
        else:
            a["closed_q"] = a["k_q"] = [float("nan")] * 3

        # (i-b): the residual on every clean-cure loop
        r = d[okm]
        a["ib_n"] = int(r.size)
        a["ib_q"] = np.nanpercentile(r, [10, 25, 50, 75, 90]).tolist() \
            if r.size else [float("nan")] * 5
        a["ib_absmed"] = float(np.nanmedian(np.abs(r))) if r.size else float("nan")
        a["k_all_q"] = np.percentile(k[okm], [10, 50, 90]).tolist() \
            if okm.any() else [float("nan")] * 3

        def _floor_stats(fl):
            return {L: (int(v.size),
                        np.percentile(v, [10, 50, 90]).tolist()
                        if v.size else [float("nan")] * 3,
                        float(np.median(np.abs(v)))
                        if v.size else float("nan"))
                    for L, v in fl.items()}

        fl, why = noise_floor(c, pay_row, rate_f)
        a["floor_why"] = why
        a["floor"] = _floor_stats(fl)
        # **The pre-2026-08-17 population, printed beside it, not instead of
        # it.** The two zero-interest screens shrink the floor's draw, and a
        # floor is what the gate is judged against, so moving it silently would
        # be moving the bar. R01.
        fl_legacy, why_legacy = noise_floor(c, pay_row, rate_f,
                                            screen_zib=False)
        a["floor_legacy"] = _floor_stats(fl_legacy)
        a["floor_why_legacy"] = why_legacy
    finally:
        c.close()
    return a


def pct(x, y):
    return f"{x / y:.4f}" if y else "-"


def render(rows: list[dict]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8-0a: the clean-cure round trip\n")
    A("Generated by `experiments/b8_0a_gate.py` from the core table. "
      "Registered in `docs/b8_fannie_slice.md` §16 and "
      "`docs/b8_inputs_availability.md` §6.2.10.\n")
    A("**The gate's target is the closed form, not zero** (ruled 2026-08-16). "
      "`b8_omega.py` P4 shows the round trip returns -9e-6 to -6e-4 on a "
      "perfectly clean synthetic loan, because `f(B) = B(1+i) - P` is affine "
      "and the log ratio does not telescope.\n")
    A("**Reads no prediction.**\n")

    A("\n## 1. Episodes found\n")
    A("A clean cure is `current -> delinquent -> current` with no modification "
      "and no deferred balance anywhere in the window, consecutive reporting "
      "periods throughout, and the fields the residual needs present.\n")
    A("| archive | raw start-end pairs | kept | dropped | eligible loans for "
      "(i-a) | loops on them | unusable: path | **closed form has no log** |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        d = a["drops"]
        A(f"| {a['name']} | {d.get('raw', 0):,} | {d.get('kept', 0):,} | "
          f"{d.get('dropped', 0):,} | {a['n_eligible_loans']:,} | "
          f"{a.get('n_loops_ia', 0):,} | {a.get('n_bad_path', 0):,} | "
          f"**{a.get('n_bad_closed', 0):,}** |")
    A("\n**The last column is a loop within a payment or two of payoff**, where "
      "`f(B0) <= 0` and the closed form has no logarithm. It was previously "
      "swallowed by a later `nanmax`, which is the same silent drop this file "
      "complains about elsewhere, so it is counted here.\n")

    A("\n## 2. B8-0a(i-a), the gate\n")
    A("A loop qualifies when its observed balance path matches the ideal one: "
      "flat through the delinquency and landing on `f^(k+1)(B0)` at the "
      "reinstatement. **The qualifying count is half the gate**: a wrong payment "
      "or a date misalignment collapses it. `b8_0a_gate.py`'s selftest reads a "
      "payment one per cent wrong as moving the endpoint by $30.55.\n")
    A("**Both tolerances are now derived from the same half cent, and the run "
      "is double reported.** The first run used a loose $0.05 path tolerance "
      "against an agreement bound derived from half a cent, ten times tighter. "
      "A loop deviating by two or three cents passed the path filter and then "
      "necessarily broke the bound. That incoherence was a construction defect "
      "whichever way the verdict fell, so the `loose` column reproduces the "
      "first run and the `derived` column is coherent.\n")
    A("| | |")
    A("|---|---|")
    A("| path tolerance, loose | `$0.05`, the first run's constant |")
    A("| path tolerance, derived | `max(2h, h(1 + (1+i)^(k+1)))`, about one "
      "cent |")
    A("| agreement bound | `h((2+i)(k+1) + (1+i)^(k+1)) / min(balance)` |")
    A("| `h` | half a cent, the file's own UPB precision |")
    A("")
    A("| archive | loops | build | **ideal path** | rate | max abs(stream - "
      "closed) | median bound | **max ratio** | p50 | p90 | p99 | over 1 | "
      "**verdict** |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        nl = a.get("n_loops_ia", 0)
        for lab, tag, cnt in (("loose", "loose", a.get("ideal_ia", 0)),
                              ("**derived**", "tight",
                               a.get("ideal_ia_tight", 0))):
            rq = a.get(f"{tag}_ratio_q", [float('nan')] * 3)
            A(f"| {a['name']} | {nl:,} | {lab} | **{cnt:,}** | "
              f"{pct(cnt, nl)} | "
              f"{a.get(f'{tag}_max', float('nan')):.3e} | "
              f"{a.get(f'{tag}_bound_med', float('nan')):.3e} | "
              f"**{a.get(f'{tag}_ratio_max', float('nan')):.3f}** | "
              f"{rq[0]:.3f} | {rq[1]:.3f} | {rq[2]:.3f} | "
              f"{a.get(f'{tag}_over', 0):,} | "
              f"**{'PASS' if a.get(f'{tag}_pass') else 'FAIL'}** |")

    A("\n## O28's correction, double reported\n")
    A("`find_clean_cures` excluded a modification flag and a positive field 63 "
      "and **said nothing about field 108** until 2026-08-17. A payment "
      "deferral moves missed payments into a balloon, which is an event, so a "
      "window carrying one is not a clean cure. **`legacy` is the sample the "
      "published B8-0a(i-a) figures were produced on**, kept reproducible "
      "rather than overwritten (§6.6.17.3).\n")
    A("\n**The verdict cannot move and that is algebra, not luck**: "
      "`pass = ratio_max < 1.0`, `ratio_max` is a maximum over the qualifying "
      "loops, and a maximum cannot rise when loops are removed. What the pair "
      "below carries is **whether the contamination was sitting on the worst "
      "case**.\n")
    A("| archive | clean cures, legacy | **corrected** | removed | share | "
      "ideal path legacy | **corrected** | ratio_max legacy | **corrected** | "
      "verdict |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        lg = a.get("legacy", {})
        n0, n1 = lg.get("n_loops", 0), a.get("n_loops", 0)
        A(f"| {a['name']} | {n0:,} | **{n1:,}** | {n0 - n1:,} | "
          f"{pct(n0 - n1, n0)} | {lg.get('ideal_ia_tight', 0):,} | "
          f"**{a.get('ideal_ia_tight', 0):,}** | "
          f"{lg.get('tight_ratio_max', float('nan')):.3f} | "
          f"**{a.get('tight_ratio_max', float('nan')):.3f}** | "
          f"**{'PASS' if a.get('tight_pass') else 'FAIL'}** |")
    A("\n`removed` counted on its own, before the other window conditions have "
      "had their turn, is `defer_in_window_alone` in the drop table; the "
      "marginal figure is `defer_in_window`.\n")

    A("\n**How far the loose set actually deviates from the ideal path**, in "
      "dollars. This is what the derived tolerance cuts on.\n")
    A("| archive | path deviation p50 | p90 | p99 | k p10 | p50 | p90 | closed "
      "form p50 |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        pd = a.get("pathdev_q", [float('nan')] * 3)
        A(f"| {a['name']} | " + " | ".join(f"{v:.4f}" for v in pd) + " | "
          + " | ".join(f"{v:.0f}" for v in a.get("k_q", [float('nan')] * 3))
          + f" | {a.get('closed_q', [float('nan')] * 3)[1]:+.3e} |")

    A("\n## 2b. Field 12 reads a literal zero on many opening rows\n")
    A("**Nothing in B8 had noticed.** The quiet filter requires a positive "
      "previous UPB and `find_clean_cures` requires one at `t0`, so every "
      "earlier reading skipped these rows by accident rather than on purpose. "
      "The floor was the one table that anchored on a loan's first row, and it "
      "came back empty twice before the values were printed. The position "
      "column is the row's place inside its loan, 0 at the first row and 1 at "
      "the last.\n")
    A("| archive | rows with UPB = 0 | rate | position p10 | p50 | p90 | loans "
      "whose first row is one | rate |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        z = a.get("zero_upb_rows", 0)
        A(f"| {a['name']} | {z:,} | {pct(z, a.get('n_rows', 0) or 1)} | "
          + " | ".join(f"{v:.3f}" for v in a.get("zero_upb_frac_q",
                                                 [float('nan')] * 3))
          + f" | {a.get('loans_zero_first', 0):,} | "
          f"{pct(a.get('loans_zero_first', 0), a.get('n_loans', 0) or 1)} |")

    A("\n## 3. B8-0a(i-b), a reading and not a gate\n")
    A("`stream - closed form` on **every** clean-cure loop, whatever its path. "
      "Beside it the floor: the same sum on never-delinquent loans over windows "
      "of matched length, where the closed form is zero by construction.\n")
    A("| archive | loops | p10 | p25 | median | p75 | p90 | median abs | k p50 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        A(f"| {a['name']} | {a.get('ib_n', 0):,} | "
          + " | ".join(f"{v:+.3e}" for v in a.get("ib_q", [float('nan')] * 5))
          + f" | {a.get('ib_absmed', float('nan')):.3e} | "
          f"{a.get('k_all_q', [float('nan')] * 3)[1]:.0f} |")

    A("\n**The floor**, never-delinquent windows. **Every candidate is "
      "accounted for**, including the cap, because a silent truncation reads as "
      "full coverage when it is not.\n")
    A("| archive | window | clean loans | no anchor | candidates | capped at | "
      "skip: gap | rate | payment | path | **kept** | p10 | median | p90 | "
      "median abs |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        fw = a.get("floor_why", {})
        for Lk, (nn, qq, am) in sorted(a.get("floor", {}).items()):
            w = fw.get(Lk, {})
            A(f"| {a['name']} | {Lk} | {w.get('clean_loans', 0):,} | "
              f"{w.get('no_anchor', 0):,} | "
              f"{w.get('candidates', 0):,} | {w.get('capped_at', 0):,} | "
              f"{w.get('skip_gap', 0):,} | {w.get('skip_rate', 0):,} | "
              f"{w.get('skip_pay', 0):,} | {w.get('skip_path', 0):,} | "
              f"**{nn:,}** | "
              + " | ".join(f"{v:+.3e}" for v in qq) + f" | {am:.3e} |")

    A("\n**The same floor on the pre-2026-08-17 population** (R01). That one "
      "screened delinquency and the modification flag and **neither "
      "zero-interest balance**, so a loan that deferred or was re-contracted "
      "without ever going delinquent contributed its balance step to the floor "
      "as if it were ambient noise. **A floor is what the gate is judged "
      "against**, so the old and the new are printed side by side rather than "
      "one replacing the other. `screen_zib=False` is the switch and nothing "
      "should be run under it going forward.\n")
    A("| archive | window | clean loans | **kept** | median | median abs | "
      "clean loans, screened | **kept, screened** | median, screened | "
      "median abs, screened |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        fwl, fw = a.get("floor_why_legacy", {}), a.get("floor_why", {})
        new = a.get("floor", {})
        for Lk, (nn, qq, am) in sorted(a.get("floor_legacy", {}).items()):
            nn2, qq2, am2 = new.get(Lk, (0, [float("nan")] * 3, float("nan")))
            A(f"| {a['name']} | {Lk} | "
              f"{fwl.get(Lk, {}).get('clean_loans', 0):,} | **{nn:,}** | "
              f"{qq[1]:+.3e} | {am:.3e} | "
              f"{fw.get(Lk, {}).get('clean_loans', 0):,} | **{nn2:,}** | "
              f"{qq2[1]:+.3e} | {am2:.3e} |")

    A("\n**Failing examples**, up to five per archive and window, printed "
      "verbatim. The first run of this table came back empty on every archive "
      "and reading the code did not settle why, so the values are shown rather "
      "than reasoned about.\n")
    any_ex = False
    for a in rows:
        for Lk, w in sorted(a.get("floor_why", {}).items()):
            for ex in w.get("examples", []):
                if not any_ex:
                    A("| archive | window | loan | first row | t | bal[t-1] | "
                      "bal[t] | bhat | payment | note pct | upb[t-1] raw | "
                      "nib[t-1] raw | rate raw | rate filled |")
                    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
                    any_ex = True
                A(f"| {a['name']} | {Lk} | {ex['loan']:,} | {ex['row0']:,} | "
                  f"{ex['t']:,} | {ex['bal_prev']:,.2f} | {ex['bal_now']:,.2f} "
                  f"| {ex['bhat']:,.2f} | {ex['P']:,.2f} | {ex['note']:.3f} | "
                  f"{ex['upb_prev_raw']:,} | {ex['nib_prev_raw']:,} | "
                  f"{ex['rate_raw']:,} | {ex['rate_filled']:,} |")
    if not any_ex:
        A("None. Every candidate either passed or was skipped for a reason "
          "already counted above.\n")

    A("\n## What this does not decide\n")
    A("- **Two limitations travel with (i-a) wherever it is quoted**, per §16.3: "
      "the subsample skews hard to the newest archives, and it is selected on "
      "payment regularity, which correlates with the class index, so **it must "
      "not be reused as the sample for any B8-4 shaped reading**.")
    A("- The payment is the modal implied payment of a contract period's quiet "
      "months, so it is the level payment the borrower habitually makes rather "
      "than the contractual one. C8-1d is registered and unrun.")
    A("- The discount curve does not enter here at all. `b8_omega.py` P2 proves "
      "it cancels on the contract triple. **It does not cancel once a deferred "
      "balloon is present**, and the Treasury series this repository would need "
      "for that is not held. Registered for the prediction stage.")
    A("- B8-0a(ii), with fees and capitalisation, is not run here. Per §6.2.1 "
      "the forgiveness term is identically zero on these six archives, so that "
      "reading is already narrower than §14.5 registered.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def selftest() -> int:
    fails = []
    B0, NOTE, N0 = 150000.0, 6.50, 300
    i = NOTE / 1200.0
    P = float(W.level_payment([B0], [NOTE], [N0])[0])

    def f(b):
        return b * (1.0 + i) - P

    # an ideal clean cure with k missed months, streamed the way analyse does
    for k in (1, 2, 5):
        bal = [B0] + [B0] * k
        bs = B0
        for _ in range(k + 1):
            bs = f(bs)
        bal.append(bs)
        s = 0.0
        for t in range(1, len(bal)):
            s += np.log(bal[t]) - np.log(f(bal[t - 1]))
        closed = float(W.loop_residual_ideal(B0, NOTE, P, k))
        if abs(s - closed) > 1e-12:
            fails.append(f"ideal k={k}: stream {s:.6e} vs closed {closed:.6e}")
        if abs(closed) < 1e-9:
            fails.append(f"ideal k={k}: the closed form was zero")

    # a wrong payment must break the ideal-path test, which is the P check
    Pw = P * 1.01
    bs = B0
    for _ in range(3):
        bs = bs * (1.0 + i) - Pw
    good_end = B0
    for _ in range(3):
        good_end = f(good_end)
    tol_here = ideal_tol(NOTE, 3)
    if abs(bs - good_end) <= max(tol_here, IDEAL_TOL_LOOSE):
        fails.append("a 1 per cent wrong payment still looked ideal")
    # the derived tolerance must be near a cent, not near a nickel
    for kk in (1, 3, 6):
        t = ideal_tol(NOTE, kk)
        if not (0.009 < t < 0.012):
            fails.append(f"derived ideal tolerance at k={kk} is {t:.4f}")
    print(f"  derived path tolerance k=1/3/6  "
          f"{ideal_tol(NOTE, 1):.4f} / {ideal_tol(NOTE, 3):.4f} / "
          f"{ideal_tol(NOTE, 6):.4f}   (the first run used "
          f"{IDEAL_TOL_LOOSE:.2f})", file=sys.stderr)

    # a never-delinquent window on schedule sums to zero
    b, s = B0, 0.0
    for _ in range(6):
        nb = f(b)
        s += np.log(nb) - np.log(f(b))
        b = nb
    if abs(s) > 1e-15:
        fails.append(f"a clean window did not sum to zero: {s:.3e}")

    # the derived bound must cover a cent of rounding on every balance
    for k in (1, 3, 6):
        bnd = rounding_bound(140000.0, NOTE, k)
        worst = 0.0
        rng = np.random.default_rng(7)
        for _ in range(200):
            path = [B0] + [B0] * k
            tail = B0
            for _ in range(k + 1):
                tail = f(tail)
            path.append(tail)
            jit = [round(b + rng.uniform(-0.005, 0.005), 2) for b in path]
            s = sum(np.log(jit[t]) - np.log(f(jit[t - 1]))
                    for t in range(1, len(jit)))
            cl = float(W.loop_residual_ideal(jit[0], NOTE, P, k))
            worst = max(worst, abs(s - cl))
        if worst > bnd:
            fails.append(f"rounding bound too tight at k={k}: "
                         f"worst {worst:.3e} vs bound {bnd:.3e}")
        print(f"  k={k}: worst cent-jitter {worst:.3e}, derived bound "
              f"{bnd:.3e}, ratio {worst / bnd:.3f}", file=sys.stderr)

    print(f"  ideal k=1/2/5 closed form "
          f"{float(W.loop_residual_ideal(B0, NOTE, P, 1)):+.3e} / "
          f"{float(W.loop_residual_ideal(B0, NOTE, P, 2)):+.3e} / "
          f"{float(W.loop_residual_ideal(B0, NOTE, P, 5)):+.3e}",
          file=sys.stderr)
    print(f"  1 pct wrong payment moves the endpoint by "
          f"${abs(bs - good_end):,.2f} against a ${tol_here:.4f} tolerance",
          file=sys.stderr)
    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    # **A fixture that actually carries field 108.** `b8_core`'s synthetic
    # archive writes no field 108 at all, so running the correction against it
    # reports `legacy == corrected` and proves nothing — pit 19's free pass, hit
    # again. This one holds two clean cures, one of them with a deferred balance
    # inside its window, so the corrected sample must be exactly one smaller.
    import zipfile as _zip

    def _synth_defer(path):
        rate, rem, y, m, age = 6.0, 360, 2020, 1, 0
        i = rate / 1200.0
        lines = []
        for L_, dfr_on in ((0, False), (1, True)):
            bal = 200000.0
            pmt = float(K.level_payment([bal], [rate], [360])[0])
            rem, y, m, age = 360, 2020, 1, 0
            for kk, dq in enumerate(["00", "00", "00", "01", "02", "00", "00"]):
                f = [""] * K.NFIELDS
                f[1] = f"{940000000000 + L_}"
                f[2] = f"{m:02d}{y:04d}"
                f[3] = "R"
                f[8] = f"{rate:.3f}"
                f[11] = "0.00" if kk == 0 else f"{bal:.2f}"
                f[12] = "360"
                f[15] = str(age)
                f[16] = str(rem)
                f[17] = str(rem)
                f[18] = "012050"
                f[19] = "80"
                f[22] = "35"
                f[23] = "720"
                f[25] = "N"
                f[26] = "P"
                f[29] = "P"
                f[30] = "CA"
                f[39] = dq
                f[41] = "N"
                f[101] = "7"
                f[105] = "P" if (dfr_on and kk >= 4) else "7"
                f[107] = "1500.00" if (dfr_on and kk >= 4) else ""
                lines.append("|".join(f))
                if dq == "00" and kk > 0:
                    bal = bal * (1 + i) - pmt
                rem -= 1
                age += 1
                m += 1
                if m == 13:
                    m, y = 1, y + 1
        path.parent.mkdir(parents=True, exist_ok=True)
        with _zip.ZipFile(path, "w", _zip.ZIP_DEFLATED) as z:
            z.writestr("f.csv", "\n".join(lines) + "\n")

    dzp = K.SELFTEST_DIR / "raw" / "2094Q1_defer.zip"
    if not dzp.exists():
        _synth_defer(dzp)
    K.build_archive(dzp, force=True, cache_root=K.SELFTEST_DIR / "cache")
    with K.Core(dzp.stem, cols=GATE_COLS, loan_cols=GATE_LOAN_COLS,
                cache_root=K.SELFTEST_DIR / "cache") as dc:
        n_on = find_clean_cures(dc, require_no_defer=True)[0].size
        n_off = find_clean_cures(dc, require_no_defer=False)[0].size
        dr = find_clean_cures(dc, require_no_defer=True)[4]
    print(f"  field-108 fixture: clean cures {n_off} -> {n_on} "
          f"(dropped {dr.get('defer_in_window_alone', 0)})", file=sys.stderr)
    if n_off != 2 or n_on != 1:
        fails.append(f"field-108 fixture: expected 2 -> 1, got {n_off} -> {n_on}")
    if dr.get("defer_in_window_alone", 0) != 1:
        fails.append("the field-108 drop count did not fire on a window that "
                     "carries one")

    # **`analyse` is exercised end to end here**, on `b8_core`'s fixture.
    # Pit 30, fourth occurrence in this stage: until now this selftest was
    # arithmetic only and never opened a `Core`, so `GATE_COLS` was unchecked.
    tag = K._fixture_tag()
    zp = K.SELFTEST_DIR / "raw" / f"2098Q1_{tag}.zip"
    if not zp.exists():
        K._synth(zp)
    K.build_archive(zp, force=True, cache_root=K.SELFTEST_DIR / "cache")
    cr = K.SELFTEST_DIR / "cache"
    a1 = analyse(zp.stem, require_no_defer=True, cache_root=cr)
    a0 = analyse(zp.stem, require_no_defer=False, cache_root=cr)
    print(f"  analyse on the fixture: clean cures legacy {a0['n_loops']:,} -> "
          f"corrected {a1['n_loops']:,}", file=sys.stderr)
    if a1["n_loops"] > a0["n_loops"]:
        fails.append("the field-108 condition ADDED clean cures; it can only "
                     "remove them")
    if "defer_in_window_alone" not in a1["drops"]:
        fails.append("the field-108 drop is not counted")

    # **The floor's two zero-interest screens, R01's other half.** The switch
    # must be live on this fixture or the double report is two copies of one
    # number, which is the shape 坑 32 keeps coming back in.
    fl_new, fl_old = a1.get("floor", {}), a1.get("floor_legacy", {})
    cl_new = {L: a1["floor_why"][L]["clean_loans"] for L in fl_new}
    cl_old = {L: a1["floor_why_legacy"][L]["clean_loans"] for L in fl_old}
    if set(fl_new) != set(fl_old):
        fails.append("the two floor readings cover different window lengths")
    elif not any(cl_new[L] < cl_old[L] for L in fl_new):
        fails.append("the zero-interest screens removed no loan from the "
                     "floor on this fixture, so `screen_zib` is inert here "
                     "and the double report proves nothing")
    elif any(cl_new[L] > cl_old[L] for L in fl_new):
        fails.append("a zero-interest screen ADDED loans to the floor; it can "
                     "only remove them")
    else:
        L0 = sorted(fl_new)[0]
        print(f"  floor screens: clean loans {cl_old[L0]:,} -> {cl_new[L0]:,} "
              f"at window {L0}, medians {fl_old[L0][1][1]:+.3e} -> "
              f"{fl_new[L0][1][1]:+.3e}", file=sys.stderr)

    for _c in K.check_markdown_tables(render([dict(a1, legacy=a0)])):
        fails.append(f"malformed table: {_c}")
    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1

    print("selftest: ok, and `analyse` runs end to end", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())

    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()) \
        if root.exists() else []
    if args.only:
        keep = set(args.only)
        names = [n for n in names if n in keep]
    if not names:
        print("no core table. Run: python experiments/b8_core.py build",
              file=sys.stderr)
        raise SystemExit(1)

    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        # **Both readings in one run**, per §6.6.17.1: two columns produced
        # together difference more cleanly than two files made on different
        # days, because nothing else can have moved between them. `legacy` is
        # the pre-2026-08-17 sample the published B8-0a(i-a) numbers came from.
        a = analyse(n, require_no_defer=True)
        a["legacy"] = analyse(n, require_no_defer=False)
        rows.append(a)
        lg = a["legacy"]
        print(f"  done {n}: loops {lg['n_loops']:,} -> {a['n_loops']:,}, "
              f"ratio_max {lg.get('tight_ratio_max', float('nan')):.3f} -> "
              f"{a.get('tight_ratio_max', float('nan')):.3f}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(rows))
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
