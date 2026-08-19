#!/usr/bin/env python3
"""B8 omega, block one: ``V``, ``V-hat``, ``r(t)``, and the contract payment.

Registered in ``docs/b8_fannie_slice.md`` §14 and §16, the B8 inputs register
§6.2.9. **This block computes no omega on real data and reads no prediction.**
It provides the construction, proves four properties of it against hand-built
schedules, and probes how much of the file carries an estimable contract
payment. The loop assembly and B8-0a are block two.

--------------------------------------------------------------------------
The construction, as registered
--------------------------------------------------------------------------

§14.1, **as amended 2026-08-17** by §6.6.20.6::

    V(t) =  PV[ level payment on the interest-bearing balance  12 - 63 - 108
                at rate (9), over (17) months ]
          + PV[ the zero-interest balance  63 + 108  as a balloon at (19) ]
          -  principal forgiven to date (64)

    and it is **not computed at all** on a loan that carries both zero-interest
    balances, which is C13's disposition (§6.6.20). That count travels with
    every figure derived from `V`.

discounted on the constant-maturity Treasury par yield at month ``t``,
interpolated to ``(17)``. **``omega < 0`` is a gain to the household.**

The amendment is one field wide and it matters. Until 2026-08-17 the balloon
read **field 63 alone**, on the strength of a docstring calling field 63 the
deferral. C10-4 (§6.6.11) measured that a field-63 rising edge moves the note
rate on 46.1 per cent of onsets and the legal maturity on 84.2, so field 63 is
a re-contracting and the deferral carrier is **field 108**; fields 108 and 106's
ADR code share a first onset on 35,617 loans with zero exceptions. Reading 63
alone put the whole deferral arm's balloon at zero. **The name was the defect
and it survived every arithmetic test in this file**, because none of them
opened an archive.

§14.2::

    V-hat(t) = the unchanged contract carried one month forward from t-1:
               same note rate, balance reduced by the scheduled principal
               payment, (17) reduced by one, same balloon, no forgiveness,
               no capitalisation. **Priced on the curve at t, not at t-1.**
    r(t)     = log V(t) - log V-hat(t)
    omega(leg) = sum of r(t) over the months of that leg

Corrections that already apply: the interest-bearing balance is ``12 - 63 - 108``
(C8-1, C11-1); the **amortisation** horizon is field 17 (§13.2) and the
**balloon** horizon is field 19 minus the reporting period (§14.1), which
`balloon_horizon` reads and which C11-3 confirmed agrees with field 17 on at
least 99.78 per cent of deferral rows; **the payment is carried as state and
is not re-derived from the current balance each month** (§6.2.5); field 64 is
zero on all six archives so the forgiveness term is identically zero here
(§6.2.1); field 44 needs no filter (§6.2.6.3).

--------------------------------------------------------------------------
Five properties proved here, before any real loan is touched
--------------------------------------------------------------------------

**P1. A month in which nothing contractual happens contributes exactly zero.**
That is §14.2's load-bearing claim and it holds.

**P2. On the contract triple the discount curve cancels completely.**
``V``'s first term is ``pmt(B, i, n) * annuity(d, n)`` and ``pmt`` is linear in
``B``, so ``V = B * k(i, d, n)``. ``V`` and ``V-hat`` share ``i``, ``n`` and
``d``, so ``k`` divides out and ``r(t) = log B_t - log B-hat_t``. Swept from
0.5 to 15 per cent, ``r`` does not move in the twelfth decimal.
**So B8-0a needs no Treasury data.** With a deferred balloon it does not cancel,
so B8-1 onward still does, and that series is not in this repository. Registered
as an open availability item for the prediction stage, not a blocker here.

**P3. §14.2's pricing warning is worth two orders of magnitude.** Pricing
``V-hat`` on the ``t-1`` curve instead of the ``t`` curve turns a residual of
-0.0005 into -0.026 on a 25 basis point move and +0.052 on a 50 basis point
move down. It is fifty to a hundred times the signal and it flips the sign.

**P4. The clean-cure round trip does NOT return zero, and this is a property of
the construction rather than of the data.** With ``f(B) = B(1+i) - P`` the loop
sum over ``k`` missed months and a reinstatement is::

    k * log B0  -  (k+1) * log f(B0)  +  log f^(k+1)(B0)

which vanishes only if ``f^(k+1)(B0) * B0^k == f(B0)^(k+1)``, and ``f`` is
affine rather than multiplicative, so it does not. On a perfectly clean
synthetic loan with no freeze and no curtailment the round trip returns -9e-6 to
-6e-4, eleven orders above floating point. **§14.5's sentence "on the contract
triple, that zero is arithmetic" is wrong**, and the closed form above is what
B8-0a's gate should compare against instead of zero.
``loop_residual_ideal`` computes it. **The selftest asserts the sum is NOT zero**
so that no later stage can quietly re-assume it is.

--------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------

    python experiments/b8_omega.py selftest      # touches no archive
    python experiments/b8_omega.py probe         # contract-payment coverage

``probe`` writes ``results/b8_omega_payment_coverage.md`` and computes no omega.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b8_omega_payment_coverage.md"

#: A contract period needs at least this many quiet pairs before its payment is
#: estimated. Two is the minimum a cluster can be drawn from; the probe reports
#: the whole distribution so a stricter floor can be chosen with the numbers in
#: hand rather than before.
MIN_QUIET_FOR_PAYMENT = 2

#: **The column list `probe` opens the core table with**, hoisted so the
#: selftest opens the fixture with the same one. Pit 30, third occurrence: a
#: selftest that never enters `probe` cannot see a column missing here, and
#: `defer_amt` reached a real run as a `KeyError` for exactly that reason. The
#: selftest now runs `probe` against `b8_core`'s fixture.
PROBE_COLS = ["period", "rate", "upb", "rem_legal", "delinq", "mod_flag",
              "nib_upb", "defer_amt"]
PROBE_LOAN_COLS = ["orig_term"]

#: **The column list `rows_for_V` needs**, which is a different list: it reads
#: field 19 for the balloon horizon and no delinquency or modification flag at
#: all. Kept separate rather than merged into `PROBE_COLS`, because a merged
#: list makes every entry look load-bearing to `scripts/b8_col_sweep.py` and a
#: dead entry stops being detectable. Both lists are swept.
V_COLS = ["period", "upb", "rem_legal", "mat_date", "nib_upb", "defer_amt"]


# ---------------------------------------------------------------------------
# the construction
# ---------------------------------------------------------------------------

def annuity(disc_pct, n):
    """PV of one unit per month for ``n`` months at an annual par yield."""
    d = np.asarray(disc_pct, dtype=np.float64) / 1200.0
    n = np.asarray(n, dtype=np.float64)
    out = np.where(d > 0, (1.0 - np.power(1.0 + d, -n)) / np.where(d > 0, d, 1.0), n)
    return out


def level_payment(balance, note_pct, n):
    """The level payment that amortises ``balance`` over ``n`` months."""
    return K.level_payment(balance, note_pct, n)


def V(balance_ib, note_pct, n, disc_pct, zib=0.0, balloon_n=None, forgiven=0.0):
    """§14.1 as amended by §6.6.20.6. Balances in currency units, rates in per
    cent.

    ``balance_ib`` is the **interest-bearing** balance ``12 - 63 - 108``
    (C8-1 for field 63, C11-1 for field 108). ``zib`` is the **zero-interest
    balance** ``63 + 108``, carried at zero interest to ``balloon_n`` months
    away, which §14.1 fixes at field 19 minus the reporting period.
    ``forgiven`` is field 64, identically zero on the six archives.

    **The parameter was called ``nib`` and read field 63 alone until
    2026-08-17.** C10-4 settled that field 63 is a re-contracting and that the
    deferral carrier is field 108, so the old name named the wrong field and
    the deferral arm's balloon was silently zero. §6.6.21.5 records the name
    itself as where the defect lived, which is why this one is spelled ``zib``
    and not after either field.

    **This function is not told which loan it is on, so it cannot enforce
    C13's refusal.** The loans carrying both balances are removed upstream by
    :func:`rows_for_V`, which is the only thing in this file that opens a core
    table for a ``V``.

    **``balloon_n`` is required whenever ``zib`` is positive.** Letting it
    default to the amortisation horizon prices the balloon at field 17 while
    §14.1 prices it at field 19. The two agree on this file to within C11-3's
    99.78 per cent, so the wrong one would have been invisible, and a default
    that silently picks a different field from the one the registration names
    is the exact shape of the defect above.
    """
    balance_ib = np.asarray(balance_ib, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    zib = np.asarray(zib, dtype=np.float64)
    forgiven = np.asarray(forgiven, dtype=np.float64)
    d = np.asarray(disc_pct, dtype=np.float64) / 1200.0

    if balloon_n is None:
        if np.any(zib > 0):
            raise ValueError(
                "V() was given a positive zero-interest balloon and no "
                "`balloon_n`. §14.1 prices the balloon at field 19 minus the "
                "reporting period; pass `balloon_horizon(c)[0]` sliced to the "
                "same rows. Defaulting to the amortisation horizon would "
                "price it at field 17 without saying so.")
        bn = n
    else:
        bn = np.asarray(balloon_n, dtype=np.float64)

    stream = level_payment(balance_ib, note_pct, n) * annuity(disc_pct, n)
    balloon = np.where(zib > 0, zib * np.power(1.0 + d, -bn), 0.0)
    return stream + balloon - forgiven


def balloon_horizon(c: K.Core) -> tuple[np.ndarray, dict]:
    """Months from the reporting period (3) to legal maturity (19), per row.

    §14.1 prices the balloon at field 19. Field 17 is the fallback where 19 is
    missing, which §14.1 explicitly permits ("where 19 is present it agrees
    with 17 exactly and either may be used") and C11-3 measured at agreement on
    at least 99.78 per cent of deferral rows. **The fallback is counted, not
    assumed**, and so is the disagreement: §14.1 says "exactly", so a non-zero
    ``disagree`` is news about the file and not a tolerance to widen.

    Returns ``(bn, info)``. ``bn`` is float64 with **NaN where neither field is
    usable**, which is loud in a way a zero or a sentinel is not.
    """
    n = c.n_rows
    mat = c.row["mat_date"][:].astype(np.int64)
    per = c.row["period"][:].astype(np.int64)
    rem = c.row["rem_legal"][:].astype(np.int64)

    d19 = mat - per
    ok19 = (mat != K.U16_NA) & (per != K.U16_NA) & (d19 > 0)
    ok17 = (rem != K.U16_NA) & (rem > 0)

    bn = np.full(n, np.nan)
    bn[ok17] = rem[ok17]
    bn[ok19] = d19[ok19]                     # field 19 wins where both are read
    return bn, {
        "rows": int(n),
        "from_19": int(ok19.sum()),
        "from_17_fallback": int((ok17 & ~ok19).sum()),
        "unavailable": int((~ok17 & ~ok19).sum()),
        "disagree": int((ok19 & ok17 & (d19 != rem)).sum()),
    }


def rows_for_V(c: K.Core) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Everything ``V`` needs from a core table, with the refusals applied.

    Returns ``(balance_ib, zib, balloon_n, info)``, the first three float64 per
    row in **currency units** and months, **all three NaN on any row that must
    not be read**. Three things make a row unreadable and each is counted:

      * its loan carries both zero-interest balances (C13, §6.6.20.6). **This
        is the refusal that has to travel with every figure.**
      * field 12 is blank, so the balance is a sentinel rather than a number.
      * neither field 19 nor field 17 gives a balloon horizon, **and only where
        the balloon is actually positive** — a row with no balloon needs no
        horizon and dropping it would be a filter on nothing.

    **NaN rather than a mask, deliberately.** A dropped row is invisible in a
    mean; a NaN is not, and every renderer in this repository already prints
    ``nan`` rather than swallowing it. The mask is returned in ``info`` as well,
    for the callers that want to count rather than propagate.
    """
    cls, cinfo = K.zero_interest_carrier(c)
    bal_c, zib_c = K.zero_interest_split(c)
    bn, binfo = balloon_horizon(c)

    excluded_loan = cls == K.CARRIER_BOTH
    bad_c13 = excluded_loan[c.loan_of_row()]
    bad_upb = c.row["upb"][:] == K.U32_NA
    zib = zib_c.astype(np.float64) / 100.0
    bad_bn = (zib > 0) & ~np.isfinite(bn)
    bad = bad_c13 | bad_upb | bad_bn

    bal = bal_c.astype(np.float64) / 100.0
    bal[bad] = np.nan
    zib[bad] = np.nan
    bn = np.where(bad, np.nan, bn)

    info = {
        "carrier": cinfo,
        "horizon": binfo,
        "rows": int(c.n_rows),
        "rows_dropped_c13": int(bad_c13.sum()),
        "rows_dropped_blank_upb": int((bad_upb & ~bad_c13).sum()),
        "rows_dropped_no_horizon": int((bad_bn & ~bad_c13 & ~bad_upb).sum()),
        "rows_readable": int((~bad).sum()),
        "loans_dropped_c13": int(excluded_loan.sum()),
        "bad": bad,
    }
    return bal, zib, bn, info


def carry_forward(balance_ib_prev, note_pct, payment):
    """§14.2's counterfactual balance: one month of the **contract** payment.

    ``payment`` is the contract payment carried as state, per §6.2.5. It is not
    re-derived from ``balance_ib_prev``, and re-deriving it is the defect C8-1a
    read as a median of 1.01 on 140 million months.
    """
    b = np.asarray(balance_ib_prev, dtype=np.float64)
    i = np.asarray(note_pct, dtype=np.float64) / 1200.0
    return b * (1.0 + i) - np.asarray(payment, dtype=np.float64)


def r_month(bal_now, bal_prev, note_pct, payment, n_now, disc_pct,
            zib_now=0.0, zib_prev=0.0, balloon_n=None,
            forgiven_now=0.0, forgiven_prev=0.0,
            note_prev=None, n_prev=None, balloon_n_prev=None):
    """``r(t) = log V(t) - log V-hat(t)``, both priced on the curve at ``t``.

    Passing a different ``disc_pct`` to the two sides is the error §14.2 calls
    invisible in code review and fatal, so this function takes one curve and
    uses it for both. See P3 in the module docstring for what it costs.

    ``zib_now`` and ``zib_prev`` were ``nib_now`` and ``nib_prev``. §14.2 says
    ``V-hat`` carries the **same** balloon forward, so the two differ exactly
    when the balloon moved, which is the deferral onset itself.

    **The three ``_prev`` arguments are the 2026-08-17 correction and they are
    load-bearing exactly where all the signal is.** §14.2 defines ``V-hat`` as
    *the unchanged contract carried one month forward from ``t-1``: same note
    rate, ``(17)`` reduced by one, same deferred balloon*. This function used
    ``note_pct`` and ``n_now`` on **both** sides. On a quiet month the note
    rate does not move and ``n_now == n_prev - 1``, so the two readings
    coincide and every property P1 through P5 passes either way. **At the
    modification month they do not coincide**: the rate moves on 46.1 per cent
    of onsets and the legal maturity on 84.2 (C10-4), and the old code priced
    the counterfactual at the *new* rate over the *new* term. That is leg 2,
    which §14.3 calls the dominant term, so the defect sat precisely on the
    quantity the stage is built to measure.

    Omitting them reproduces the old behaviour bit for bit, which is what keeps
    the four gate properties comparable across the change. **Nothing that reads
    a real archive may omit them**; `row_residuals` passes all three.
    """
    note_prev = note_pct if note_prev is None else note_prev
    n_prev = n_now if n_prev is None else n_prev
    if balloon_n_prev is None:
        balloon_n_prev = balloon_n
    v_now = V(bal_now, note_pct, n_now, disc_pct, zib_now, balloon_n,
              forgiven_now)
    b_hat = carry_forward(bal_prev, note_prev, payment)
    v_hat = V(b_hat, note_prev, n_prev, disc_pct, zib_prev, balloon_n_prev,
              forgiven_prev)
    return np.log(v_now) - np.log(v_hat)


def loop_residual_ideal(B0, note_pct, payment, k):
    """The clean-cure round trip's residual, in closed form. See P4.

    ``k`` missed months from a balance of ``B0``, then one reinstatement that
    pays every missed payment at once and puts the balance exactly where the
    uninterrupted schedule would have it.

    **This is what B8-0a's gate compares against. It is not zero.**
    """
    i = float(note_pct) / 1200.0
    P = float(payment)
    B0 = float(B0)

    def f(b):
        return b * (1.0 + i) - P

    b = B0
    for _ in range(int(k) + 1):
        b = f(b)
    return (int(k) * np.log(B0) - (int(k) + 1) * np.log(f(B0)) + np.log(b))


# ---------------------------------------------------------------------------
# the contract payment, as state
# ---------------------------------------------------------------------------

def _row_bounds(c: K.Core):
    """First and last row index of the loan each row belongs to, as int32."""
    start = np.repeat(c.row_start.astype(np.int32),
                      c.n_per_loan.astype(np.int64))
    end = start + np.repeat(c.n_per_loan.astype(np.int32),
                            c.n_per_loan.astype(np.int64)) - 1
    return start, end


def fill_within_loan(arr, na, start, end, backward=True):
    """Carry a field's last known value forward, and optionally backward too.

    **This is the fix for the defect block one's first probe read.** The core
    table stores a blank field as a sentinel, and comparing the sentinel to the
    real values on either side of it fires **two** spurious breaks. In 2002Q1
    that shattered 968,761 loans into 1,944,756 contract periods while the
    archive holds only 6,794 first-modification events and 404 deferrals, and it
    drove loan-level coverage down to half a per cent.

    A blank field 9 does not mean the note rate changed for a month and changed
    back. **The contract is a property of the period, not of the row**, so the
    value is carried across the gap. Rows in a loan with no known value at all
    stay blank and are counted.

    **Only field 9 is filled.** For fields 42 and 63 a blank is a state rather
    than a gap: §13.1 established that the modification flag reverts to ``N`` on
    three quarters of modified loans and that field 63 goes blank again on about
    eighty per cent of the pre-2008 cohorts. Filling those would erase a real
    transition, and back-filling them would erase the onset itself. The blank
    counts for all three fields are reported beside the break counts so the
    choice is visible rather than assumed.
    """
    n = arr.size
    idx = np.arange(n, dtype=np.int32)
    valid = arr != na
    prev = np.maximum.accumulate(np.where(valid, idx, np.int32(-1)))
    use = np.where(prev >= start, prev, idx)
    still = (arr[use] == na) if backward else np.zeros(n, dtype=bool)
    if still.any():
        nxt = np.minimum.accumulate(
            np.where(valid, idx, np.int32(n))[::-1])[::-1]
        use = np.where(still & (nxt <= end), nxt, use)
    return arr[use]


def rate_path_class(c: K.Core, rate_filled: np.ndarray):
    """Classify each loan by the shape of its note-rate path.

    `b8_fannie_slice.md` §7 filters to **fixed-rate** loans and **nothing in B8
    has ever applied that filter**, including the core table, which does not
    carry a product-type column. Product type, number of units and lien position
    are not in C0b's confirmed anchor set, and C0b's rule forbids naming a column
    on the strength of what its values look like.

    So the property is earned by behaviour instead: **a loan whose note rate
    moves only at a modification is fixed-rate.** Returns per-loan counts and a
    three-way class::

        fixed_never_mod   no rate change and no modification
        fixed_modified    at least one modification, no more rate changes than
                          modification events
        varies            more rate changes than modification events

    ``varies`` is the adjustable-rate shaped population. **This is a proxy and is
    labelled as one wherever it is quoted**, exactly as §2's programme-identifier
    proxy is.
    """
    starts = c.row_start.astype(np.int64)
    modY = c.row["mod_flag"][:] == ord("Y")
    loan = c.loan_of_row()

    chg = np.zeros(c.n_rows, dtype=np.int64)
    chg[1:] = ((rate_filled[1:] != rate_filled[:-1])
               & (loan[1:] == loan[:-1])).astype(np.int64)
    edge = np.zeros(c.n_rows, dtype=np.int64)
    edge[1:] = (modY[1:] & ~modY[:-1] & (loan[1:] == loan[:-1])).astype(np.int64)

    n_chg = np.add.reduceat(chg, starts)
    n_edge = np.add.reduceat(edge, starts)
    cls = np.where(n_chg > n_edge, 2, np.where(n_edge > 0, 1, 0)).astype(np.int8)
    return cls, n_chg, n_edge


def contract_periods(c: K.Core, fill: bool = True, attribute: bool = False):
    """A period id for **every row**, not only for quiet pairs.

    **This is a different object from ``b8_core.segment_ids``** and the two must
    not be conflated. ``segment_ids`` partitions the quiet-pair sequence and
    splits only on a change of field 9, which is what the C8-1c family needed.
    ``omega`` needs the contract payment on delinquent months too, so this
    partitions **rows** and splits on:

      * a change of loan,
      * a change of field 9, the note rate,
      * a rising edge of field 42, the modification flag, since a term-only
        modification moves the payment without moving the rate,
      * a rising edge of a positive field 63. **This was labelled "a deferral
        onset" and that label was wrong**; C10-4 (the B8 inputs register
        §6.6.11) measured that at a field-63 rising edge the note rate moves on
        46.1 per cent of onsets and the legal maturity on 84.2 per cent, so it
        is a re-contracting, which is what §14.3 leg 2 always said it was. The
        deferral onset is field 108. **The boundary stays exactly where it
        was**, because a re-contracting is a contract-period boundary; only the
        name changes, and **the output of this function is byte-identical
        before and after that correction**, so nothing downstream is re-based.

    A field-108 rising edge is deliberately **not** a boundary: C10-4 reads
    `still` at 0.9966 there, meaning the note rate and the legal maturity both
    hold, so the contract payment cannot have changed and a boundary would only
    cost coverage.

    The last two are conservative. An unnecessary boundary costs coverage,
    because the shorter period has fewer quiet months to estimate from. A
    missing boundary corrupts the estimate. The probe reports what coverage
    costs.
    """
    n = c.n_rows
    loan = c.loan_of_row()
    rate = c.row["rate"][:]
    mf = c.row["mod_flag"][:]
    nib = c.row["nib_upb"][:]

    if fill:
        start, end = _row_bounds(c)
        rate = fill_within_loan(rate, K.U16_NA, start, end, backward=True)
    modY = mf == ord("Y")
    nibpos = (nib != K.U32_NA) & (nib > 0)

    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]
    b_loan = ~same
    b_loan[0] = True
    b_rate = np.zeros(n, dtype=bool)
    b_rate[1:] = (rate[1:] != rate[:-1]) & same[1:]
    b_mod = np.zeros(n, dtype=bool)
    b_mod[1:] = modY[1:] & ~modY[:-1] & same[1:]
    b_nib = np.zeros(n, dtype=bool)
    b_nib[1:] = nibpos[1:] & ~nibpos[:-1] & same[1:]

    period = np.cumsum(b_loan | b_rate | b_mod | b_nib) - 1
    if not attribute:
        return period
    return period, {
        "loan": int(b_loan.sum()), "rate": int(b_rate.sum()),
        "mod": int(b_mod.sum()), "nib": int(b_nib.sum()),
        "rate_blank_rows": int((c.row["rate"][:] == K.U16_NA).sum()),
        "mod_blank_rows": int((c.row["mod_flag"][:] == K.U8_NA).sum()),
        "nib_blank_rows": int((c.row["nib_upb"][:] == K.U32_NA).sum()),
        "rate_unfillable": int((rate == K.U16_NA).sum()),
    }


def contract_payments(c: K.Core, period: np.ndarray, q: dict):
    """Modal payment per contract period, estimated from that period's quiet
    months and broadcast to every row.

    Returns ``(payment_of_row, known_of_row, per_period)`` where ``per_period``
    is a dict of arrays indexed by period id: ``n_quiet``, ``payment``,
    ``width``, ``ncand``.
    """
    nper = int(period[-1]) + 1 if period.size else 0
    p_of_pair = period[q["cur"]]

    obs = q["obs_cents"].astype(np.float64) / 100.0
    p_upb = q["p_upb_cents"].astype(np.float64) / 100.0
    i = q["rate_milli"].astype(np.float64) / 1000.0 / 1200.0
    implied = obs + p_upb * i

    order = np.argsort(p_of_pair, kind="stable")
    pp = p_of_pair[order]
    vv = implied[order]
    if pp.size:
        starts = np.flatnonzero(np.concatenate(([True], pp[1:] != pp[:-1])))
        counts = np.diff(np.append(starts, pp.size))
        ids = pp[starts]
    else:
        starts = counts = ids = np.zeros(0, dtype=np.int64)

    pay = np.full(nper, np.nan)
    width = np.full(nper, np.nan)
    ncand = np.zeros(nper, dtype=np.int32)
    nq = np.zeros(nper, dtype=np.int64)
    nq[ids] = counts

    for pid, s, cn in zip(ids.tolist(), starts.tolist(), counts.tolist()):
        if cn < MIN_QUIET_FOR_PAYMENT:
            continue
        m, lo, hi, k = K.modal_cluster(vv[s:s + cn].tolist())
        pay[pid], width[pid], ncand[pid] = m, hi - lo, k

    known = np.isfinite(pay)
    return pay[period], known[period], {
        "n_quiet": nq, "payment": pay, "width": width, "ncand": ncand,
        "known": known}


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def _coverage(c, q, period, cc, cls=None):
    """Coverage figures for one choice of period construction."""
    pay_row, known_row, per = contract_payments(c, period, q)
    loan = c.loan_of_row()
    bad = np.bincount(loan, weights=(~known_row).astype(np.float64),
                      minlength=c.n_loans)
    full = bad == 0
    nq = per["n_quiet"]
    w = per["width"][per["known"]]
    out = {
        "n_periods": int(per["payment"].size),
        "n_periods_known": int(per["known"].sum()),
        "periods_no_quiet": int((nq == 0).sum()),
        "periods_one_quiet": int((nq == 1).sum()),
        "nq_q": np.percentile(nq, [10, 50, 90]).tolist(),
        "width_q": (np.percentile(w, [50, 90]).tolist() if w.size
                    else [float("nan")] * 2),
        "multi_cand": int((per["ncand"][per["known"]] > 1).sum()),
        "rows_known": int(known_row.sum()),
        "loans_full": int(full.sum()),
        "cc_full": int((cc & full).sum()),
    }
    if cls is not None:
        keep = cls != 2                      # drop the adjustable-rate shape
        out["fixed_loans"] = int(keep.sum())
        out["fixed_full"] = int((keep & full).sum())
        out["cc_fixed"] = int((cc & keep).sum())
        out["cc_fixed_full"] = int((cc & keep & full).sum())
    return out


def probe(name: str, cache_root=None) -> dict:
    c = K.Core(name, cols=PROBE_COLS, loan_cols=PROBE_LOAN_COLS,
               cache_root=cache_root)
    try:
        # **Three readings, side by side in one run.** §6.6.17.1: the rule the
        # double report serves is "the output can be differenced against the
        # old reading", and three columns produced in a single run difference
        # more cleanly than two files produced on different days, because
        # nothing else can have moved between them.
        #
        #   legacy  the reading every earlier number in this file was made under
        #   net     only the balance corrected to 12 - 63 - 108   (C8-1, C11-1)
        #   open    that, plus the field-63 loans re-admitted     (O29 dir. 1)
        #
        # `open` is the live default as of 2026-08-17.
        q = K.quiet_pairs(c, require_never_deferred=True, ib_net=False)
        q_net = K.quiet_pairs(c, require_never_deferred=True, ib_net=True)
        q_open = K.quiet_pairs(c, require_never_deferred=False, ib_net=True)

        # the clean-cure-shaped population, C8-1e §5's definition
        #
        # **The field-108 screen is new on 2026-08-17 and it moves this
        # number.** `b8_0a_gate.find_clean_cures` grew the screen when C10-4
        # settled that the deferral carrier is field 108, and this copy did
        # not, so the two definitions of "clean cure" had silently come apart.
        # Both readings are printed, per R01: `clean_cure_legacy` is what every
        # earlier row of `b8_omega_payment_coverage.md` was made under.
        starts = c.row_start.astype(np.int64)
        counts = c.n_per_loan.astype(np.int64)
        dq = c.row["delinq"][:]
        dq_ok = (dq > 0) & (dq < 253)
        modY = c.row["mod_flag"][:] == ord("Y")
        nibp = (c.row["nib_upb"][:] != K.U32_NA) & (c.row["nib_upb"][:] > 0)
        dfrp = (c.row["defer_amt"][:] != K.U32_NA) & (c.row["defer_amt"][:] > 0)
        cc_legacy = ((np.add.reduceat(dq_ok.astype(np.int64), starts) > 0)
                     & (np.add.reduceat(modY.astype(np.int64), starts) == 0)
                     & (np.add.reduceat(nibp.astype(np.int64), starts) == 0)
                     & (dq[starts + counts - 1] == 0))
        cc = cc_legacy & (np.add.reduceat(dfrp.astype(np.int64), starts) == 0)

        a = {"name": name, "n_rows": c.n_rows, "n_loans": c.n_loans,
             "clean_cure": int(cc.sum()),
             "clean_cure_legacy": int(cc_legacy.sum())}

        # OLD: no fill. Reproduces the first probe's numbers exactly.
        p_old, attr_old = contract_periods(c, fill=False, attribute=True)
        a["old"] = _coverage(c, q, p_old, cc)
        a["attr_old"] = attr_old
        del p_old

        # NEW: fill within loan, plus the rate-path classification
        p_new, attr_new = contract_periods(c, fill=True, attribute=True)
        start, end = _row_bounds(c)
        rate_f = fill_within_loan(c.row["rate"][:], K.U16_NA, start, end)
        cls, n_chg, n_edge = rate_path_class(c, rate_f)
        a["cls"] = [int((cls == k).sum()) for k in (0, 1, 2)]
        a["new"] = _coverage(c, q, p_new, cc, cls)
        a["net"] = _coverage(c, q_net, p_new, cc, cls)
        a["open"] = _coverage(c, q_open, p_new, cc, cls)
        a["attr_new"] = attr_new
        a["pairs"] = {"legacy": int(q["cur"].size),
                      "net": int(q_net["cur"].size),
                      "open": int(q_open["cur"].size)}
    finally:
        c.close()
    return a


#: Horizons are integer months and the archives never exceed a few hundred, so
#: the curve is read once into a table rather than per row. A per-row read is a
#: Python call per row, which on 170 million rows is not a table lookup.
MAX_H = 600


def disc_of_row(c: K.Core, pos, tab) -> tuple[np.ndarray, dict]:
    """The curve read at each row's own month and horizon, per cent, NaN where
    it does not reach. §14.1: interpolated to field 17."""
    n = c.n_rows
    period = c.row["period"][:].astype(np.int64)
    rem = c.row["rem_legal"][:].astype(np.int64)

    mrow = np.full(n, -1, dtype=np.int64)
    known_m = period != K.U16_NA
    if known_m.any():
        keys = np.unique(period[known_m])
        lut = np.full(int(keys.max()) + 1, -1, dtype=np.int64)
        for mi in keys.tolist():
            lut[mi] = pos.get(int(mi), -1)
        mrow[known_m] = lut[period[known_m]]

    good = (mrow >= 0) & (rem >= 1) & (rem <= MAX_H)
    disc = np.full(n, np.nan)
    gi = np.flatnonzero(good)
    if gi.size:
        disc[gi] = tab[mrow[gi], rem[gi]]
    return disc, {
        "rows": int(n),
        "no_curve_that_month": int((mrow < 0).sum()),
        "horizon_out_of_table": int(((mrow >= 0) & ~good).sum()),
        "curve_nan": int((good & ~np.isfinite(disc)).sum()),
        "usable": int(np.isfinite(disc).sum()),
    }


def row_residuals(c: K.Core, disc, pay_row=None, known_row=None,
                  period_id=None) -> tuple[np.ndarray, np.ndarray, dict]:
    """``r(t)`` for **every row**, plus the mask of rows where it is computable.

    ``disc`` is the discount curve read at each row's horizon, in per cent, and
    NaN wherever the curve does not reach. **The caller supplies it** rather
    than this function building it, because the curve tables live in
    `b8_cmt_sensitivity` and importing them here would put the whole Treasury
    fetch behind this module's selftest.

    This is **the single copy** of the per-row residual. It was written twice:
    once here for the loop assembly and once in
    `b8_cmt_sensitivity2.per_row_r`, and the second copy still read the balance
    as ``12 - 63``, priced the balloon at field 17 and passed the old ``nib_``
    keywords. Two copies of the residual is how the sensitivity table and the
    loop sum end up measuring two different quantities and nobody notices.

    Returns ``(r, ok, info)``. Every row that is not ``ok`` has ``r`` NaN, and
    ``info`` says how many rows each condition removed, **counted in the order
    applied so the counts partition rather than overlap**.
    """
    n = c.n_rows
    period = c.row["period"][:].astype(np.int32)
    rate = c.row["rate"][:].astype(np.int32)
    rem = c.row["rem_legal"][:].astype(np.int32)

    bal, zib, bn, vinfo = rows_for_V(c)
    if period_id is None:
        period_id = contract_periods(c, fill=True)
    if pay_row is None or known_row is None:
        q = K.quiet_pairs(c)
        pay_row, known_row, _ = contract_payments(c, period_id, q)

    idx = np.arange(n, dtype=np.int64)
    start = np.repeat(c.row_start.astype(np.int64),
                      c.n_per_loan.astype(np.int64))
    same = idx > start                    # has a previous row in the same loan

    steps = []

    def step(name, cond, ok):
        new = ok & cond
        steps.append((name, int((ok & ~cond).sum())))
        return new

    ok = same.copy()
    steps.append(("first row of a loan", int((~same).sum())))
    # **The payment `V-hat` needs is the PREVIOUS row's**, not this row's.
    # §14.2's counterfactual is the contract as it stood at `t-1` carried one
    # month forward, so at the modification month it wants the pre-modification
    # payment, which lives in the previous contract period. Requiring a known
    # payment on *this* row would drop the modification month itself, and that
    # month is leg 2.
    prev_known = np.zeros(n, dtype=bool)
    prev_known[1:] = known_row[:-1]
    ok = step("no contract payment on the previous row", prev_known, ok)
    prev_ok = np.zeros(n, dtype=bool)
    prev_ok[1:] = np.isfinite(bal[:-1]) & (bal[:-1] > 0)
    ok = step("balance not readable (C13 refusal, blank 12, no horizon)",
              np.isfinite(bal) & (bal > 0) & prev_ok, ok)
    prev_field = np.zeros(n, dtype=bool)
    prev_field[1:] = ((rate[:-1] != K.U16_NA) & (rem[:-1] != K.U16_NA)
                      & (rem[:-1] > 1))
    ok = step("rate or horizon missing on either row",
              (rate != K.U16_NA) & (rem != K.U16_NA) & (rem > 0)
              & (period != K.U16_NA) & prev_field, ok)
    # the previous row's balloon needs a horizon too, and only when it exists.
    # Left as an explicit counted drop rather than letting a NaN horizon ride
    # through `np.where`'s unselected branch, where it is invisible.
    prev_bn = np.zeros(n, dtype=bool)
    prev_bn[1:] = (zib[:-1] <= 0) | (np.isfinite(bn[:-1]) & (bn[:-1] > 1))
    ok = step("previous row carries a balloon with no horizon", prev_bn, ok)
    ok = step("curve does not reach this month and horizon", np.isfinite(disc),
              ok)

    note = rate.astype(np.float64) / 1000.0
    remf = rem.astype(np.float64)

    # **The counterfactual balance must stay positive**, or `log V-hat` is not
    # a number. `b_hat = bal_prev * (1 + i) - P` goes non-positive near payoff,
    # when one more contract payment would clear the loan. The first real run
    # counted 303 to 1,948 such rows per archive under the name "r came back
    # non-finite on a row we admitted", which is a **symptom, not a cause**:
    # that backstop exists to catch what nobody predicted, and leaving a
    # predictable case in it means the backstop's count no longer means
    # "something unexpected happened".
    bhat_all = np.zeros(n)
    bhat_all[1:] = (bal[:-1] * (1.0 + note[:-1] / 1200.0) - pay_row[:-1])
    ok = step("the counterfactual balance would be non-positive (near payoff)",
              np.isfinite(bhat_all) & (bhat_all > 0), ok)

    r = np.full(n, np.nan)
    sel = np.flatnonzero(ok)
    if sel.size:
        # **Every `_prev` argument is passed.** `V-hat` is priced at the
        # previous row's rate, the previous row's horizon less one month, and
        # the previous row's balloon at the previous row's maturity less one
        # month. Omitting any of them prices the counterfactual on the new
        # contract, which is the 2026-08-17 defect in `r_month`'s docstring.
        r[sel] = r_month(
            bal[sel], bal[sel - 1], note[sel], pay_row[sel - 1],
            remf[sel], disc[sel],
            zib_now=zib[sel], zib_prev=zib[sel - 1],
            balloon_n=bn[sel],
            note_prev=note[sel - 1],
            n_prev=remf[sel - 1] - 1.0,
            balloon_n_prev=bn[sel - 1] - 1.0)
    # a NaN out of `r_month` on a row we called `ok` is a defect, not a filter
    bad = ok & ~np.isfinite(r)
    if bad.any():
        ok = ok & np.isfinite(r)
        steps.append(("r came back non-finite on a row we admitted",
                      int(bad.sum())))

    prev_zib = np.concatenate(([False], zib[:-1] > 0))
    info = {"rows": int(n), "ok": int(ok.sum()), "dropped": steps,
            "V": vinfo,
            "rows_with_balloon": int((ok & (zib > 0)).sum()),
            "rows_with_balloon_prev": int((ok & prev_zib).sum()),
            # **The only door the curve rules reach through** (§17.16). Handed
            # back as a mask because `b8_cmt_sensitivity2` reads its sweep on
            # exactly these rows, and it used to derive them from its own copy
            # of the balance.
            "balloon_row": ok & ((zib > 0) | prev_zib)}
    return r, ok, info


def pct(x, y):
    return f"{x / y:.4f}" if y else "-"


def render(rows: list[dict]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8 omega block one: contract-payment coverage\n")
    A("Generated by `experiments/b8_omega.py probe` from the core table. "
      "Registered in the B8 inputs register §6.2.9.\n")
    A("**No `omega` is computed here and no prediction is read.**\n")
    A("**Double reported, on two axes.** The `no fill` row is the period "
      "construction the first probe used, and the `filled` row carries a blank "
      "field across the gap inside a loan; both are under the **legacy** "
      "reading, so their figures must match this file as it stood before "
      "2026-08-17.\n")
    A("\nThe `net` and `open` rows are the 2026-08-17 rulings (§6.6.17), each "
      "isolating one change:\n")
    A("\n```\nlegacy   implied payment on field 12,      field-63 loans excluded\n"
      "net      implied payment on 12 - 63 - 108,  field-63 loans excluded\n"
      "open     implied payment on 12 - 63 - 108,  field-63 loans admitted\n```\n")
    A("\n**`open` is the live default.** Three readings in one run difference "
      "more cleanly than two files made on different days, because nothing "
      "else can have moved between them (§6.6.17.1). None of them is a "
      "criterion; they are ways of cutting the rows.\n")

    A("\n## 1. Where the breaks came from\n")
    A("A blank field is stored as a sentinel, so an isolated blank fires "
      "**two** breaks, one in and one out. The blank-row counts beside the "
      "break counts are what makes that visible.\n")
    A("| archive | build | breaks: loan | rate | mod edge | deferral | blank "
      "rate rows | rate blank after fill |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for lab, k in (("no fill", "attr_old"), ("filled", "attr_new")):
            d = a[k]
            A(f"| {a['name']} | {lab} | {d['loan']:,} | {d['rate']:,} | "
              f"{d['mod']:,} | {d['nib']:,} | {d['rate_blank_rows']:,} | "
              f"{d['rate_unfillable']:,} |")

    A("\n### 1.1 Qualifying quiet pairs under each reading\n")
    A("`net` must equal `legacy` in count: netting the balance changes the "
      "**value** an implied payment is computed from, never which pairs "
      "qualify. **A difference here would be a defect, not a result.**\n")
    A("| archive | legacy | net | **open** | open gain |")
    A("|---|---|---|---|---|")
    for a in rows:
        pr = a["pairs"]
        A(f"| {a['name']} | {pr['legacy']:,} | {pr['net']:,} | "
          f"**{pr['open']:,}** | +{pr['open'] - pr['legacy']:,} |")

    A("\n## 2. Contract periods and payment coverage\n")
    A("| archive | build | periods | with a payment | rate | no quiet pair | "
      "rate | quiet pairs p10 | p50 | p90 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for lab, k in (("no fill", "old"), ("filled", "new"),
                       ("net", "net"), ("**open**", "open")):
            d = a[k]
            A(f"| {a['name']} | {lab} | {d['n_periods']:,} | "
              f"{d['n_periods_known']:,} | "
              f"{pct(d['n_periods_known'], d['n_periods'])} | "
              f"{d['periods_no_quiet']:,} | "
              f"{pct(d['periods_no_quiet'], d['n_periods'])} | "
              + " | ".join(f"{v:.0f}" for v in d["nq_q"]) + " |")

    A("\n| archive | build | rows covered | rate | **loans fully covered** | "
      "rate | cluster width p50 | p90 | more than one candidate |")
    A("|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for lab, k in (("no fill", "old"), ("filled", "new"),
                       ("net", "net"), ("**open**", "open")):
            d = a[k]
            A(f"| {a['name']} | {lab} | {d['rows_known']:,} | "
              f"{pct(d['rows_known'], a['n_rows'])} | **{d['loans_full']:,}** | "
              f"**{pct(d['loans_full'], a['n_loans'])}** | "
              + " | ".join(f"{v:.3f}" for v in d["width_q"])
              + f" | {d['multi_cand']:,} |")

    A("\n## 3. The note-rate path, and §7's fixed-rate filter\n")
    A("**`b8_fannie_slice.md` §7 filters to fixed-rate loans and nothing in B8 "
      "has ever applied it**, this probe included. The core table carries no "
      "product-type column and product type is not in C0b's confirmed anchor "
      "set, so the property is earned by behaviour instead: **a loan whose note "
      "rate moves only at a modification is fixed-rate.** This is a proxy and "
      "is labelled as one wherever it is quoted.\n")
    A("| archive | no rate change, never modified | rate | modified, rate moves "
      "no more often | rate | **rate moves more often** | rate |")
    A("|---|---|---|---|---|---|---|")
    for a in rows:
        c0, c1, c2 = a["cls"]
        n = a["n_loans"]
        A(f"| {a['name']} | {c0:,} | {pct(c0, n)} | {c1:,} | {pct(c1, n)} | "
          f"**{c2:,}** | **{pct(c2, n)}** |")

    A("\n## 4. What block two actually has\n")
    A("Clean-cure shaped, as C8-1e §5 defines it, then fully covered, then "
      "restricted to the fixed-rate shape. **The last column is the pool "
      "B8-0a(i-a) draws from**, before the further restriction to loans whose "
      "every quiet month sits in its modal cluster.\n")
    A("**Double reported on the population as well, per R01.** `legacy` screens "
      "field 63 only, which is what every earlier version of this table was "
      "made under; `clean-cure shaped` adds the field-108 screen that "
      "`b8_0a_gate.find_clean_cures` has carried since C10-4 and this file had "
      "not. The two columns differ by exactly the loans that deferred without "
      "ever touching field 63.\n")
    A("| archive | legacy | clean-cure shaped | covered, no fill | "
      "covered, filled | rate | fixed-rate shape | **covered and fixed** | "
      "rate |")
    A("|---|---|---|---|---|---|---|---|---|")
    tot = [0, 0, 0, 0, 0, 0]
    for a in rows:
        o, n = a["old"], a["new"]
        A(f"| {a['name']} | {a['clean_cure_legacy']:,} | "
          f"{a['clean_cure']:,} | {o['cc_full']:,} | "
          f"{n['cc_full']:,} | {pct(n['cc_full'], a['clean_cure'])} | "
          f"{n['cc_fixed']:,} | **{n['cc_fixed_full']:,}** | "
          f"**{pct(n['cc_fixed_full'], a['clean_cure'])}** |")
        tot = [tot[0] + a["clean_cure"], tot[1] + o["cc_full"],
               tot[2] + n["cc_full"], tot[3] + n["cc_fixed"],
               tot[4] + n["cc_fixed_full"], tot[5] + a["clean_cure_legacy"]]
    A(f"| **Total** | **{tot[5]:,}** | **{tot[0]:,}** | **{tot[1]:,}** | "
      f"**{tot[2]:,}** | **{pct(tot[2], tot[0])}** | **{tot[3]:,}** | "
      f"**{tot[4]:,}** | **{pct(tot[4], tot[0])}** |")

    A("\n## What this does not decide\n")
    A("- **It computes no `omega`.** It reports coverage.")
    A("- The payment estimate is the modal implied payment of a period's quiet "
      "months, so it is the level payment the borrower habitually makes rather "
      "than the contractual one. C8-1d is registered and unrun.")
    A("- **The fixed-rate classification is a behavioural proxy**, not an "
      "identification of a product-type field. C0b's caveat governs.")
    A("- §7's other three filters, single family, first lien and owner "
      "occupied, are **still not applied**. Occupancy is field 30 and is "
      "confirmed, so it can be; the other two need fields the core table does "
      "not carry.")
    A("- `MIN_QUIET_FOR_PAYMENT` is 2. §2's distribution is printed so a "
      "stricter floor can be chosen against numbers rather than before.\n")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails = []
    B0, NOTE, N0 = 150000.0, 6.50, 300
    i = NOTE / 1200.0
    P = float(level_payment([B0], [NOTE], [N0])[0])
    sched = P - B0 * i

    def f(b):
        return b * (1.0 + i) - P

    # -- P1: a quiet month contributes exactly zero -----------------------
    for cmt in (0.5, 4.0, 9.0):
        r = float(r_month(f(B0), B0, NOTE, P, N0 - 1, cmt))
        if abs(r) > 1e-15:
            fails.append(f"P1 quiet month at CMT {cmt}: r = {r:.3e}")

    # -- P2: the curve cancels on the contract triple ----------------------
    bact = f(B0) - 0.37 * sched          # borrower paid a little extra
    rs = [float(r_month(bact, B0, NOTE, P, N0 - 1, cmt))
          for cmt in (0.5, 2.0, 4.0, 6.5, 9.0, 15.0)]
    if max(rs) - min(rs) > 1e-12:
        fails.append(f"P2 curve did not cancel: spread {max(rs) - min(rs):.3e}")
    if abs(rs[0] - (np.log(bact) - np.log(f(B0)))) > 1e-12:
        fails.append("P2 r is not the log balance ratio")

    # -- P2b: with a balloon it must NOT cancel ---------------------------
    rb = [float(r_month(bact, B0, NOTE, P, N0 - 1, cmt,
                        zib_now=5000.0, zib_prev=5000.0, balloon_n=N0 - 1))
          for cmt in (0.5, 15.0)]
    if abs(rb[0] - rb[1]) < 1e-7:
        fails.append("P2b the curve cancelled with a balloon, it should not")

    # -- P3: pricing V-hat on the t-1 curve ------------------------------
    def r_split(cmt_prev, cmt_now):
        vn = float(V(bact, NOTE, N0 - 1, cmt_now))
        vh = float(V(f(B0), NOTE, N0 - 1, cmt_prev))
        return np.log(vn) - np.log(vh)
    true_r = rs[0]
    for prev, now in ((4.0, 4.25), (4.0, 3.5)):
        bad = r_split(prev, now)
        if abs(bad) < 20 * abs(true_r):
            fails.append(f"P3 mispricing {prev}->{now} was not large: "
                         f"{bad:.3e} vs {true_r:.3e}")

    # -- P4: the round trip, streaming against the closed form ------------
    for Bx, nx, nn, k in ((150000.0, 6.50, 300, 1), (150000.0, 6.50, 300, 3),
                          (200000.0, 6.50, 360, 6), (80000.0, 7.50, 180, 6),
                          (300000.0, 3.75, 360, 2)):
        ix = nx / 1200.0
        Px = float(level_payment([Bx], [nx], [nn])[0])

        def fx(b, ix=ix, Px=Px):
            return b * (1.0 + ix) - Px

        # stream the ideal clean cure through r_month
        s, bprev, rem = 0.0, Bx, nn
        for _ in range(k):                       # missed months, balance flat
            rem -= 1
            s += float(r_month(Bx, bprev, nx, Px, rem, 4.0))
            bprev = Bx
        bsched = Bx
        for _ in range(k + 1):
            bsched = fx(bsched)
        rem -= 1
        s += float(r_month(bsched, bprev, nx, Px, rem, 4.0))

        closed = float(loop_residual_ideal(Bx, nx, Px, k))
        if abs(s - closed) > 1e-12:
            fails.append(f"P4 stream {s:.6e} vs closed form {closed:.6e} "
                         f"(B={Bx}, k={k})")
        # and the finding itself, locked in
        if abs(closed) < 1e-9:
            fails.append(f"P4 the round trip returned zero at B={Bx}, k={k}. "
                         f"If this ever fires the construction changed and "
                         f"b8_fannie_slice.md §16 has to be re-read.")
        if closed >= 0:
            fails.append(f"P4 residual not negative at B={Bx}, k={k}")

    # -- P5: the fill, and the shattering it repairs -----------------------
    NA = K.U16_NA
    # two loans, rows 0-5 and 6-9. loan A has an interior gap and a leading gap.
    arr = np.array([NA, 6500, 6500, NA, 6500, 6500,
                    NA, 4000, NA, 4000], dtype=np.uint16)
    start = np.array([0, 0, 0, 0, 0, 0, 6, 6, 6, 6], dtype=np.int32)
    end = np.array([5, 5, 5, 5, 5, 5, 9, 9, 9, 9], dtype=np.int32)

    fwd = fill_within_loan(arr, NA, start, end, backward=False)
    if fwd[0] != NA or fwd[6] != NA:
        fails.append("P5 forward-only fill invented a leading value")
    if fwd[3] != 6500 or fwd[8] != 4000:
        fails.append(f"P5 forward fill missed an interior gap: {fwd.tolist()}")

    both = fill_within_loan(arr, NA, start, end, backward=True)
    if both.tolist() != [6500, 6500, 6500, 6500, 6500, 6500,
                         4000, 4000, 4000, 4000]:
        fails.append(f"P5 two-way fill: {both.tolist()}")

    # no bleed across the loan boundary
    arr2 = np.array([6500, 6500, 6500, NA, NA, NA], dtype=np.uint16)
    s2 = np.array([0, 0, 0, 3, 3, 3], dtype=np.int32)
    e2 = np.array([2, 2, 2, 5, 5, 5], dtype=np.int32)
    if (fill_within_loan(arr2, NA, s2, e2, backward=True)[3:] != NA).any():
        fails.append("P5 the fill bled across a loan boundary")

    # the shattering itself: one interior blank fires two breaks unfilled
    raw = np.array([6500, 6500, NA, 6500, 6500], dtype=np.uint16)
    st = np.zeros(5, dtype=np.int32)
    en = np.full(5, 4, dtype=np.int32)
    nbrk_raw = int((raw[1:] != raw[:-1]).sum())
    filled = fill_within_loan(raw, NA, st, en, backward=True)
    nbrk_fill = int((filled[1:] != filled[:-1]).sum())
    if nbrk_raw != 2 or nbrk_fill != 0:
        fails.append(f"P5 shattering demo: raw {nbrk_raw} breaks, "
                     f"filled {nbrk_fill}, want 2 and 0")
    print(f"  P5 one blank field 9      {nbrk_raw} spurious breaks -> "
          f"{nbrk_fill} after the fill", file=sys.stderr)

    # -- one delinquent month is one scheduled principal in log V ---------
    r1 = float(r_month(B0, B0, NOTE, P, N0 - 1, 4.0))
    want = np.log(B0) - np.log(f(B0))
    if abs(r1 - want) > 1e-15:
        fails.append("a missed month did not read one scheduled principal")

    # -- P6: `V` refuses a balloon with no horizon ------------------------
    # §14.1 prices the balloon at field 19. The old signature let `balloon_n`
    # default to the amortisation horizon, which is field 17, and the two agree
    # closely enough on this file (C11-3, >=0.9978) that the substitution would
    # never have shown up in a number. **So it has to fail loudly instead.**
    try:
        V(B0, NOTE, N0, 4.0, zib=5000.0)
    except ValueError:
        pass
    else:
        fails.append("P6 V() priced a balloon with no `balloon_n`; the "
                     "field-17-for-field-19 substitution is silent again")
    # and the refusal must not fire when there is no balloon to price, or it
    # is a filter on every row rather than a guard
    try:
        V(B0, NOTE, N0, 4.0, zib=0.0)
    except ValueError:
        fails.append("P6 V() refused a row with no balloon at all")
    # the balloon must actually move V, or P6 guards a term that does nothing
    v_no = float(V(B0, NOTE, N0, 4.0))
    v_bl = float(V(B0, NOTE, N0, 4.0, zib=5000.0, balloon_n=N0))
    if not v_bl > v_no:
        fails.append(f"P6 the balloon did not raise V: {v_no} -> {v_bl}")
    print(f"  P6 balloon needs a horizon  V {v_no:,.2f} -> {v_bl:,.2f} "
          f"with a 5,000 balloon at {N0} months", file=sys.stderr)

    # -- P8: V-hat is priced on the OLD contract, and that is leg 2 --------
    # §14.2: *the unchanged contract carried one month forward from t-1*. On a
    # quiet month the old and new readings coincide, which is why P1 to P5 pass
    # under both. **The month where they differ is the modification month**,
    # and that is the only month leg 2 has.
    NEW_NOTE, NEW_N = NOTE - 2.0, N0 + 119     # rate cut, term extended
    bal_after = f(B0)                          # no capitalisation, isolate it
    r_old = float(r_month(bal_after, B0, NEW_NOTE, P, NEW_N, 4.0))
    r_new = float(r_month(bal_after, B0, NEW_NOTE, P, NEW_N, 4.0,
                          note_prev=NOTE, n_prev=N0 - 1))
    # the counterfactual is the OLD contract, so V-hat must not move when the
    # new terms move. Hand-computed, not compared to another call of the code.
    v_hat_want = float(V(carry_forward(B0, NOTE, P), NOTE, N0 - 1, 4.0))
    r_want = float(np.log(V(bal_after, NEW_NOTE, NEW_N, 4.0)))- np.log(v_hat_want)
    if abs(r_new - r_want) > 1e-12:
        fails.append(f"P8 corrected r = {r_new:.6e}, hand computation "
                     f"{r_want:.6e}")
    if abs(r_old - r_new) < 1e-3:
        fails.append(f"P8 the two readings differ by only {abs(r_old-r_new):.2e} "
                     "on a rate cut plus a term extension, so this fixture "
                     "cannot tell them apart and P8 proves nothing")
    # and they must still agree exactly on a quiet month, or the correction
    # silently re-bases every number this file has ever printed
    q_old = float(r_month(f(B0), B0, NOTE, P, N0 - 1, 4.0))
    q_new = float(r_month(f(B0), B0, NOTE, P, N0 - 1, 4.0,
                          note_prev=NOTE, n_prev=N0 - 1))
    if q_old != q_new:
        fails.append(f"P8 the two readings differ on a QUIET month "
                     f"({q_old!r} vs {q_new!r}); the correction is supposed to "
                     "be inert there")
    print(f"  P8 V-hat on the old contract  r {r_old:+.6e} -> {r_new:+.6e} "
          f"at a 2 pct rate cut and a 120 month extension, quiet month "
          f"unchanged", file=sys.stderr)

    print("  P1 quiet month            r = 0 exactly", file=sys.stderr)
    print(f"  P2 curve spread over 0.5-15 pct  {max(rs) - min(rs):.2e}  "
          f"(r = {rs[0]:+.6e})", file=sys.stderr)
    print(f"  P3 25bp mispricing        {r_split(4.0, 4.25):+.6f}  "
          f"vs true {true_r:+.6e}", file=sys.stderr)
    print(f"  P4 round trip k=1/3/6     "
          f"{float(loop_residual_ideal(B0, NOTE, P, 1)):+.3e} / "
          f"{float(loop_residual_ideal(B0, NOTE, P, 3)):+.3e} / "
          f"{float(loop_residual_ideal(B0, NOTE, P, 6)):+.3e}",
          file=sys.stderr)
    print(f"  omega1 per missed month   {r1:+.6e}", file=sys.stderr)

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    # **`probe` is exercised here, on `b8_core`'s fixture.** Until 2026-08-17
    # nothing in this selftest entered `probe`, so its column list was
    # unchecked and `defer_amt` surfaced as a `KeyError` on a real archive.
    # A guard that only fires in production is a guard that fires late.
    tag = K._fixture_tag()
    zp = K.SELFTEST_DIR / "raw" / f"2098Q1_{tag}.zip"
    if not zp.exists():
        K._synth(zp)
    K.build_archive(zp, force=True, cache_root=K.SELFTEST_DIR / "cache")
    a = probe(zp.stem, cache_root=K.SELFTEST_DIR / "cache")
    pr = a["pairs"]
    print(f"  probe on the fixture: pairs legacy {pr['legacy']:,} / net "
          f"{pr['net']:,} / open {pr['open']:,}", file=sys.stderr)
    if pr["net"] != pr["legacy"]:
        print("selftest FAILED: netting the balance changed which pairs "
              "qualify; it must only change the value they carry",
              file=sys.stderr)
        return 1
    if pr["open"] <= pr["legacy"]:
        print("selftest FAILED: admitting the field-63 loans gained no pairs, "
              "so the fixture does not exercise the flip", file=sys.stderr)
        return 1
    txt = render([a])
    # every table's rows must match its header's width. A published
    # results file was malformed on 2026-08-17 and the person who
    # generated it read it and quoted from it without noticing.
    for _c in K.check_markdown_tables(txt):
        # **early return, not `fails.append`.** This function drains `fails`
        # further up, so appending here would be inert — which is exactly what
        # it was when this check was first wired in, caught by injecting a
        # broken table and finding the selftest still green.
        print(f"selftest FAILED: malformed table: {_c}", file=sys.stderr)
        return 1
    for need in ("### 1.1 Qualifying quiet pairs", "net", "open"):
        if need not in txt:
            print(f"selftest FAILED: render omits `{need}`", file=sys.stderr)
            return 1

    # -- P7: `rows_for_V` on `b8_core`'s carrier fixture -------------------
    # **The one thing in this file that opens a table for a `V`.** It carries
    # C13's refusal, and a refusal that is never exercised on a loan it is
    # supposed to refuse is a comment.
    czp = K.SELFTEST_DIR / "raw" / "2096Q1_carrier.zip"
    K._synth_carrier(czp)
    K.build_archive(czp, force=True, cache_root=K.SELFTEST_DIR / "cache")
    with K.Core(czp.stem, cols=V_COLS,
                cache_root=K.SELFTEST_DIR / "cache") as cc_:
        bal, zib, bn, vinfo = rows_for_V(cc_)
        loan = cc_.loan_of_row()
        rem17 = cc_.row["rem_legal"][:].astype(np.float64)
        n_rows_c = cc_.n_rows
    per_loan = len(K.CARRIER_FIXTURE[0][1])
    want_excl = sum(1 for k in K.CARRIER_EXPECT if k == K.CARRIER_BOTH)
    skew_loan = len(K.CARRIER_FIXTURE) - 1        # the one with 19 != 17
    p7 = []
    if vinfo["loans_dropped_c13"] != want_excl:
        p7.append(f"loans_dropped_c13 {vinfo['loans_dropped_c13']} "
                  f"!= {want_excl}")
    if vinfo["rows_dropped_c13"] != want_excl * per_loan:
        p7.append(f"rows_dropped_c13 {vinfo['rows_dropped_c13']} "
                  f"!= {want_excl * per_loan}")
    # NaN, not a dropped row: a refused row must be loud in an average
    bad_loans = [i for i, k in enumerate(K.CARRIER_EXPECT)
                 if k == K.CARRIER_BOTH]
    if not bool(np.isnan(bal[np.isin(loan, bad_loans)]).all()):
        p7.append("a refused loan's balance came back as a number, not NaN")
    if bool(np.isnan(bal[~np.isin(loan, bad_loans)]).any()):
        p7.append("a readable loan's balance came back NaN")
    # **The balloon horizon must come from field 19, and this has to be
    # identifiable.** On six of the fixture's loans the two fields agree month
    # for month, exactly as §14.1 says the real file does, and while they agree
    # no test can tell which one was read. The last loan's field 19 is skewed
    # by `CARRIER_F19_SKEW` months so that the answer names the field.
    h = vinfo["horizon"]
    if h["from_19"] != n_rows_c:
        p7.append(f"balloon horizon fell back to field 17 on "
                  f"{h['from_17_fallback']} rows of a fixture that sets "
                  "field 19 on every one")
    if h["disagree"] != per_loan:
        p7.append(f"field 19 and field 17 disagree on {h['disagree']} rows, "
                  f"expected {per_loan}: the skewed loan is not in the "
                  "fixture, so nothing here can tell the two fields apart")
    sk = loan == skew_loan
    if not bool(np.allclose(bn[sk], rem17[sk] + K.CARRIER_F19_SKEW)):
        p7.append(f"on the skewed loan the horizon reads {bn[sk][:3].tolist()} "
                  f"against field 17's {rem17[sk][:3].tolist()}; §14.1 prices "
                  "the balloon at field 19 and this is field 17")
    if p7:
        for m in p7:
            print("selftest FAILED: P7 " + m, file=sys.stderr)
        return 1
    print(f"  P7 rows_for_V             {vinfo['rows_readable']:,} readable, "
          f"{vinfo['rows_dropped_c13']:,} rows refused on "
          f"{vinfo['loans_dropped_c13']} loans; horizon from field 19 on "
          f"{h['from_19']:,} rows, disagreeing with field 17 on "
          f"{h['disagree']:,}", file=sys.stderr)

    print("selftest: ok, eight properties hold and `probe` runs end to end",
          file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["selftest", "probe"])
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args()

    if args.command == "selftest":
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
        rows.append(probe(n))
        print(f"  done {n}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(rows))
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
