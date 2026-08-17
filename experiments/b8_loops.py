#!/usr/bin/env python3
"""B8 loop assembly, block one: **the windows only. No ``omega`` is computed.**

Registered in ``docs/b8_fannie_slice.md`` §17 and
``claude-docs/B8_环窗口与曲线规则_预注册_v1.md``. **Reads no prediction.**

--------------------------------------------------------------------------
What this block does and, more importantly, what it does not
--------------------------------------------------------------------------

It finds every **registered loop** and prints the counts §17 requires. It does
not price anything, does not touch the Treasury curve, and does not call
``b8_omega.r_month``. That is block two, and splitting it here is deliberate: a
window that is off by one row is invisible in a residual and obvious in a count.

§17's window, restated as the three indices this module returns::

    t_A   the departure vertex, the last `current` row strictly before t_M
    t_M   the event onset. **Modification**: a rising edge of field 42 or of a
          positive field 63, whichever comes first, which is §14.3 leg 2
          verbatim. **Deferral**: a rising edge of a positive field 108, which
          is C10-4's answer to O27 (§6.6.11); field 63 used to be cut here and
          C10-4 measured that it is a re-contracting, not a deferral
    t_B   the return vertex, the FIRST `current` row at or after t_M

``t_B`` is "at or after", not "after", and that single word is §17.3: a row can
turn the modification flag on **and** read ``00``, which ``b8_triangles``'s
transcription note calls out, and then ``t_M == t_B`` and leg 3 is empty. Those
loops are counted separately here because §14.3 promises ``omega_3`` is
*measured* rather than assumed, and a loop whose leg 3 is empty by construction
would pad that reading with structural zeros.

**Two conditions §17 states are satisfied by construction, and are asserted
rather than filtered**, because an assertion that never fires is cheap and a
filter that never fires reads like a real one:

  * no `current` row strictly inside ``(t_A, t_B)``. Rows in ``(t_A, t_M)`` are
    non-current because ``t_A`` is the *last* current before ``t_M``; rows in
    ``[t_M, t_B)`` are non-current because ``t_B`` is the *first* current at or
    after ``t_M``.
  * every onset sharing a ``t_A`` lies in ``(t_A, t_B]``.

--------------------------------------------------------------------------
Why the anchor runs backwards from the modification
--------------------------------------------------------------------------

``b8_cmt_sensitivity2.triangle_window`` took the loan's **first** delinquent
row. §17.2 rejects that and the reason is not stylistic: a walk that passes
through `current` in the middle is two loops, and summing them as one erases
precisely the contrast §5's B8-3 is built on, "cure-then-redefault-then-modify"
against "modify-on-first-episode". The earlier cured episode is B8-0a's sample,
so folding it in also mixes the gate's population into the reading.

--------------------------------------------------------------------------
Counts, and why each one is printed rather than folded away
--------------------------------------------------------------------------

Every drop reason is reported twice: **marginal**, what it removes given the
conditions applied before it, and **alone**, what it would remove on the whole
candidate set. §15.5 and pit 22 both say a bare minimum without its load is
unreadable, and the two numbers differ exactly where conditions overlap.

Usage::

    python experiments/b8_loops.py selftest      # touches no real archive
    python experiments/b8_loops.py census        # counts, all six archives
    python experiments/b8_loops.py census --only 2019Q1
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402
import b8_triangles as T  # noqa: E402

OUT = K.ROOT / "results" / "b8_loops_census.md"

#: **The column list `census` opens the core table with**, hoisted so the
#: selftest can open the fixture with the same one. A selftest that opens every
#: column cannot see a column missing from this list, and that is how
#: `defer_amt` reached a real run as a `KeyError`.
CENSUS_COLS = ["period", "upb", "rem_legal", "delinq", "mod_flag", "nib_upb",
               "defer_amt"]

#: The two arms of §14.4. `both` is §17.4: a run carrying onsets of both kinds
#: walks `deferred -> modified`, an edge that is **not** among the five §14.4
#: registers, so it belongs to neither triangle.
#: **Which field the deferral onset is cut on, as a value rather than as
#: prose.** The `what this does not decide` block of `b8_c10_contract_move.md`
#: went on saying "field 63 is used" for a whole run after the column changed to
#: 108, because that sentence was typed into the renderer. A disclaimer is
#: documentation and documentation goes stale silently; deriving it from the
#: constant is the only version that cannot.
DEFER_FIELD = "108"
MOD_FIELDS = "42 or 63, whichever comes first"

ARM_MOD, ARM_DEFER, ARM_BOTH = 0, 1, 2
ARM_NAME = {ARM_MOD: "modification", ARM_DEFER: "deferral",
            ARM_BOTH: "both"}


# ---------------------------------------------------------------------------
# row-level helpers. Positions, not booleans, because every test here is an
# ordering and `Core.cummax_within_loan` throws the position away.
# ---------------------------------------------------------------------------

def _prefix(a: np.ndarray) -> np.ndarray:
    return np.concatenate(([0], np.cumsum(a.astype(np.int64))))


def _rng(pref: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Sum over rows ``a..b`` inclusive. Empty when ``b < a``."""
    return pref[np.maximum(b + 1, a)] - pref[a]


def _last_pos_strictly_before(c: K.Core, mask: np.ndarray) -> np.ndarray:
    """For every row, the last row of the same loan **strictly before** it where
    ``mask`` holds, else ``-1``.

    ``b8_triangles._last_pos_where`` answers the at-or-before form. Shifting it
    by one row is the whole difference, and the loan-start clamp has to be
    re-applied after the shift or row ``0`` of a loan inherits the previous
    loan's answer.
    """
    at_or_before = T._last_pos_where(c, mask)
    out = np.full(c.n_rows, -1, dtype=np.int64)
    out[1:] = at_or_before[:-1]
    out[c.row_start.astype(np.int64)] = -1   # a first row has nothing before
    start = np.repeat(c.row_start.astype(np.int64),
                      c.n_per_loan.astype(np.int64))
    return np.where(out >= start, out, -1)


def _first_pos_at_or_after(c: K.Core, mask: np.ndarray) -> np.ndarray:
    """For every row, the first row of the same loan **at or after** it where
    ``mask`` holds, else ``-1``.

    The reverse of the running minimum ``b8_triangles._first_pos_per_loan``
    uses, kept per row rather than reduced per loan, with the same exclusive
    end so a run cannot leak into the next loan.
    """
    idx = np.arange(c.n_rows, dtype=np.int64)
    big = np.int64(c.n_rows + 1)
    rev = np.minimum.accumulate(np.where(mask, idx, big)[::-1])[::-1]
    end = np.repeat(c.row_start.astype(np.int64)
                    + c.n_per_loan.astype(np.int64),
                    c.n_per_loan.astype(np.int64))
    return np.where(rev < end, rev, -1)


# ---------------------------------------------------------------------------
# the loop finder
# ---------------------------------------------------------------------------

def find_loops(c: K.Core) -> dict:
    """Every registered loop of §17, plus every count §17 requires.

    Returns ``{"t_A", "t_M", "t_B", "arm", "n_mod_onsets", "n_defer_onsets",
    "defer_row", "excluded_two_arms", "n_onsets", "loan", "counts"}``. The index
    arrays are one entry per surviving loop; ``counts`` carries the census.
    ``excluded_two_arms`` is the §17.4 population, **returned rather than
    dropped**, because C10-2 measures exactly what a rule excluded.
    """
    dv = c.row["delinq"][:]
    mf = c.row["mod_flag"][:]
    nib = c.row["nib_upb"][:].astype(np.int64)
    upb = c.row["upb"][:].astype(np.int64)
    rem = c.row["rem_legal"][:]
    period = c.row["period"][:].astype(np.int64)
    loan = c.loan_of_row()
    n = c.n_rows

    known = dv <= 98
    is_cur = known & (dv == 0)
    is_del = known & (dv != 0)
    is_unk = ~known                     # 253 odd length, 254 XX, 255 blank

    # **The modification onset is field 42 OR field 63, whichever comes first.**
    # That is §14.3 leg 2 verbatim: "The month (42) first reads `Y`, or (63) is
    # first set, whichever comes first". It is registered text, not a choice
    # made here, and C10-4 measured that it is the right text: at a field-63
    # rising edge the note rate moves on 46.1 per cent of onsets and the legal
    # maturity on 84.2 per cent, which is a re-contracting, not a deferral.
    mod_on = (mf == K._Y) | ((nib != K.U32_NA) & (nib > 0))

    # **The deferral onset is field 108**, per C10-4 (§6.6.11) settling O27.
    # `still`, the conjunction §14.4's own definition asks for, reads 0.9966 on
    # field 108 against 0.0513 on field 63. Field 108 and field 106's ADR code
    # rise on the same row for all 35,617 loans that carry either, across six
    # archives with no exception, so the two identify each other by behaviour,
    # which is what C0b requires and is stronger than an anchor. Field 108 is
    # taken because it carries the amount and `V`'s balloon needs an amount;
    # field 106 stays as the corroborating column.
    dfr = c.row["defer_amt"][:].astype(np.int64)
    dfr_on = (dfr != K.U32_NA) & (dfr > 0)

    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]
    mod_edge = np.zeros(n, dtype=bool)
    mod_edge[1:] = mod_on[1:] & ~mod_on[:-1] & same[1:]
    defer_edge = np.zeros(n, dtype=bool)
    defer_edge[1:] = dfr_on[1:] & ~dfr_on[:-1] & same[1:]

    # A loan whose FIRST row already carries the state has no observable onset.
    # That is left truncation, not an absent event, and merging the two is the
    # error pit 5 records in another guise.
    first_rows = c.row_start.astype(np.int64)
    counts = {
        "n_rows": int(n), "n_loans": int(c.n_loans),
        "left_truncated_mod": int(mod_on[first_rows].sum()),
        "left_truncated_defer": int(dfr_on[first_rows].sum()),
        "unknown_status_rows": int(is_unk.sum()),
    }

    onset = mod_edge | defer_edge
    rows = np.flatnonzero(onset)
    counts["onsets_raw"] = int(rows.size)
    counts["onsets_mod"] = int(mod_edge.sum())
    counts["onsets_defer"] = int(defer_edge.sum())
    # the two halves of the modification onset, so the change of definition is
    # auditable rather than only assertable
    f42 = np.zeros(n, dtype=bool)
    f42[1:] = (mf[1:] == K._Y) & (mf[:-1] != K._Y) & same[1:]
    nibp = (nib != K.U32_NA) & (nib > 0)
    f63 = np.zeros(n, dtype=bool)
    f63[1:] = nibp[1:] & ~nibp[:-1] & same[1:]
    counts["onsets_mod_field42"] = int(f42.sum())
    counts["onsets_mod_field63"] = int(f63.sum())
    counts["onsets_mod_both_same_row"] = int((f42 & f63).sum())

    last_cur = _last_pos_strictly_before(c, is_cur)
    first_cur = _first_pos_at_or_after(c, is_cur)

    tA_all = last_cur[rows]
    has_dep = tA_all >= 0
    counts["drop_no_current_before"] = int((~has_dep).sum())
    rows = rows[has_dep]
    tA_all = tA_all[has_dep]

    # tA is non-decreasing over ascending rows: it is non-decreasing inside a
    # loan and every row of loan k+1 exceeds every row of loan k, so grouping by
    # tA alone is a grouping by (loan, delinquency run) and needs no sort.
    assert np.all(np.diff(tA_all) >= 0), "tA is not sorted; grouping is invalid"

    starts = np.flatnonzero(np.concatenate(([True], tA_all[1:] != tA_all[:-1])))
    grp_n = np.diff(np.append(starts, tA_all.size))
    t_A = tA_all[starts]
    t_M = rows[starts]                       # onset rows ascend, so this is min
    n_mod = np.add.reduceat(mod_edge[rows].astype(np.int64), starts)
    n_defer = np.add.reduceat(defer_edge[rows].astype(np.int64), starts)
    counts["candidate_loops"] = int(t_A.size)

    # The first onset of each kind inside the run, kept because C10 needs the
    # row a deferred balance appeared on, which is not `t_M` when a
    # modification came first. `big` marks "this kind did not occur".
    big = np.int64(n + 1)
    first_mod_row = np.minimum.reduceat(
        np.where(mod_edge[rows], rows, big), starts)
    first_defer_row = np.minimum.reduceat(
        np.where(defer_edge[rows], rows, big), starts)

    t_B = first_cur[t_M]

    # ---- the conditions, in a fixed order, each reported twice -------------
    p_del = _prefix(is_del)
    p_unk = _prefix(is_unk)
    gap = np.zeros(n, dtype=np.int64)
    gap[1:] = ((period[1:] - period[:-1] != 1) | ~same[1:]).astype(np.int64)
    p_gap = _prefix(gap)

    closed = t_B >= 0
    tBs = np.where(closed, t_B, t_A)         # safe index for the vector tests

    ok_vertex_rem = ((rem[t_A] != K.U16_NA) & (rem[tBs] != K.U16_NA))
    ok_vertex_upb = ((upb[t_A] != K.U32_NA) & (upb[t_A] > 0)
                     & (upb[tBs] != K.U32_NA) & (upb[tBs] > 0))
    ok_not_first = ~np.isin(t_A, first_rows)
    ok_has_del = _rng(p_del, t_A + 1, tBs) >= 1
    ok_no_gap = _rng(p_gap, t_A + 1, tBs) == 0
    ok_one_arm = ~((n_mod > 0) & (n_defer > 0))

    # `not_closed` is a **precondition**, not one condition among several: with
    # no `t_B` the window does not exist and every other test is undefined on
    # it. The vector tests above substitute `t_A` for the missing `t_B` so the
    # indexing is safe, and that substitution makes an empty interval, which
    # every interior test then fails **for a reason that is not its own**.
    #
    # Reading the first run's output caught this: `no_delinquency` reported
    # `alone = 2` on a fixture carrying exactly one such case, the second being
    # `never_cures` bleeding in through the substitution. So the `alone` figures
    # for the interior tests are computed on the **closed** candidates only, and
    # the results file says so. Pit 22's shape: it was found by reading our own
    # table, not by a check.
    counts["drop_not_closed_alone"] = int((~closed).sum())
    counts["drop_not_closed"] = int((~closed).sum())
    counts["closed_candidates"] = int(closed.sum())

    tests = [
        ("two_arms", ok_one_arm),
        ("no_delinquency", ok_has_del),
        ("vertex_rem_blank", ok_vertex_rem),
        ("vertex_upb_zero", ok_vertex_upb),
        ("departure_is_first_row", ok_not_first),
        ("gap_in_window", ok_no_gap),
    ]
    keep = closed.copy()
    for name, good in tests:
        counts[f"drop_{name}_alone"] = int((closed & ~good).sum())
        counts[f"drop_{name}"] = int((keep & ~good).sum())
        keep &= good

    # `not_closed` splits: the archive ended while the loan was still reporting,
    # against a loan that stopped reporting altogether. Pit 13: termination is
    # marked by the contract state going blank, not by a zero-balance code.
    last_row = (c.row_start.astype(np.int64)
                + c.n_per_loan.astype(np.int64) - 1)[loan[t_A]]
    still_reporting = rem[last_row] != K.U16_NA
    counts["drop_not_closed_right_censored"] = int((~closed & still_reporting).sum())
    counts["drop_not_closed_terminated"] = int((~closed & ~still_reporting).sum())

    # §17.4 excludes the two-arm runs from both triangles. They are **returned**
    # rather than dropped on the floor: C10-2 has to measure them, and a
    # population excluded by a rule is exactly the population a later ruling
    # needs to look at. Only the closed ones, since the rest have no window.
    two = closed & ~ok_one_arm
    excl = {"t_A": t_A[two], "t_B": t_B[two],
            "mod_row": first_mod_row[two], "defer_row": first_defer_row[two],
            "loan": loan[t_A[two]]}

    t_A, t_M, t_B = t_A[keep], t_M[keep], t_B[keep]
    n_mod, n_defer, grp_n = n_mod[keep], n_defer[keep], grp_n[keep]
    first_defer_row = first_defer_row[keep]

    # the two conditions §17 says hold by construction. Cheap, and an assertion
    # that never fires does not read like a filter that never fires.
    p_cur = _prefix(is_cur)
    assert int(_rng(p_cur, t_A + 1, t_B - 1).sum()) == 0, \
        "a `current` row is strictly inside a window"
    assert bool(np.all((t_M > t_A) & (t_M <= t_B))), \
        "an onset lies outside its own window"

    arm = np.where(n_defer > 0, ARM_DEFER, ARM_MOD).astype(np.int8)
    counts["loops"] = int(t_A.size)
    counts["loops_mod_arm"] = int((arm == ARM_MOD).sum())
    counts["loops_defer_arm"] = int((arm == ARM_DEFER).sum())
    counts["loops_mod_equals_cure"] = int((t_M == t_B).sum())
    counts["loops_multi_onset"] = int((grp_n > 1).sum())
    counts["unknown_status_inside_windows"] = int(
        _rng(p_unk, t_A + 1, t_B).sum())
    counts["windows_with_unknown_status"] = int(
        (_rng(p_unk, t_A + 1, t_B) > 0).sum())
    counts["window_len_q"] = (np.percentile(t_B - t_A, [10, 50, 90]).tolist()
                              if t_A.size else [float("nan")] * 3)

    return {"t_A": t_A, "t_M": t_M, "t_B": t_B, "arm": arm,
            "n_mod_onsets": n_mod, "n_defer_onsets": n_defer,
            "defer_row": first_defer_row, "excluded_two_arms": excl,
            "n_onsets": grp_n, "loan": loan[t_A], "counts": counts}


def against_triangles(c: K.Core, lp: dict) -> dict:
    """§17.13: C3/C4 counts **loans**, §17 counts **loops**. Measure the gap.

    The difference runs both ways and neither direction may be assumed small,
    so both are printed: a loan can carry several loops, and a loan C3/C4 counts
    can carry none (a flag that turns `Y` while the loan is current, then a
    later episode, is §17.7's third class).
    """
    tri = T.triangles(c)["triangle"]
    has = np.zeros(c.n_loans, dtype=bool)
    has[lp["loan"][lp["arm"] == ARM_MOD]] = True
    return {
        "tri_loans": int(tri.sum()),
        "loop_loans_mod": int(has.sum()),
        "loops_mod": int((lp["arm"] == ARM_MOD).sum()),
        "tri_without_loop": int((tri & ~has).sum()),
        "loop_without_tri": int((has & ~tri).sum()),
    }


# ---------------------------------------------------------------------------
# selftest. Hand-placed cases, exact expectations, no real archive.
# ---------------------------------------------------------------------------

#: ``(dq, mod, nib, upb, skip_before, rate, term_bump, defer)`` per row, the
#: last four
#: optional. ``skip_before`` advances the reporting month without emitting a
#: row, which is how the real file shows a gap. ``rate`` overrides field 9 from
#: this row on, and ``term_bump`` adds months to field 17, which is a term
#: extension. **Those two exist so C10's arms do not all read zero**: an
#: end-to-end test whose every arm reads the same number cannot tell a correct
#: wiring from a wrong one, which is pit 19's "a check that does not require
#: the two sides to differ is a free pass".
CASES = {
    # a plain triangle: one loop on the modification arm
    "plain_mod": [
        ("00", "N", 0, 0), ("00", "N", 0, 0),
        ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 0, 1),
        ("03", "Y", 0, 1, 0, 3.5, 60), ("03", "Y", 0, 1),
        ("00", "Y", 0, 1), ("00", "Y", 0, 1),
    ],
    # no onset at all: B8-0a's population, zero loops here
    "clean_cure": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 0, 1),
        ("00", "N", 0, 1), ("00", "N", 0, 1),
    ],
    # cure, redefault, then modify. The departure vertex must be the current
    # row before the SECOND run, not the first. One loop.
    "cure_then_mod": [
        ("00", "N", 0, 0), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 0, 1),
        ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 0, 1),
        ("03", "Y", 0, 1), ("00", "Y", 0, 1),
    ],
    # §17.3: the flag turns on and the row reads 00 on the same row
    "mod_equals_cure": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 0, 1), ("03", "N", 0, 1),
        ("00", "Y", 0, 1, 0, 3.25), ("00", "Y", 0, 1),
    ],
    # §17.4: both onsets inside one run walks `deferred -> modified`.
    # **After C10-4 that means field 42 (or 63) together with field 108**, not
    # 42 together with 63: those two are now the same arm.
    "two_arms": [
        ("00", "N", 0, 0, 0, None, 0, 0), ("00", "N", 0, 1, 0, None, 0, 0),
        ("00", "N", 0, 1, 0, None, 0, 0), ("01", "N", 0, 1, 0, None, 0, 0),
        ("02", "Y", 0, 1, 0, None, 0, 0), ("03", "Y", 0, 1, 0, 4.0, 0, 5000),
        ("00", "Y", 0, 1, 0, None, 0, 5000),
    ],
    # **A second two-arm loan, deferral first.** One of them is not enough:
    # `b8_loop_omega` counted this population with `np.size` on a dict, which
    # returns 1, and with a single case in the fixture **no test could tell
    # that apart from the right answer**. It reached a published results file
    # as a 1 on all six archives. The ordering differs from `two_arms` too, so
    # the case earns its place twice.
    "two_arms_defer_first": [
        ("00", "N", 0, 0, 0, None, 0, 0), ("00", "N", 0, 1, 0, None, 0, 0),
        ("00", "N", 0, 1, 0, None, 0, 0), ("01", "N", 0, 1, 0, None, 0, 0),
        ("02", "N", 0, 1, 0, None, 0, 5000),
        ("03", "Y", 0, 1, 0, 4.0, 0, 5000),
        ("00", "Y", 0, 1, 0, None, 0, 5000),
    ],
    # §17.8: the flag reverts to N and turns on again inside one run
    "two_mod_onsets": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "Y", 0, 1), ("03", "N", 0, 1),
        ("04", "Y", 0, 1), ("00", "Y", 0, 1),
    ],
    # §17.7 class 1: the archive ends with the loan still delinquent
    "never_cures": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "Y", 0, 1), ("03", "Y", 0, 1),
    ],
    # §17.7 class 3: the flag turns on while the loan is current
    "mod_while_current": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("00", "Y", 0, 1), ("00", "Y", 0, 1),
    ],
    # a reporting gap inside the window
    "gap_in_window": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "Y", 0, 1),
        ("00", "Y", 0, 1, 1),
    ],
    # **Field 63 with no field 42 is now a MODIFICATION**, not a deferral.
    # C10-4: at a field-63 rising edge the rate moves 46.1 per cent of the time
    # and the maturity 84.2 per cent. This case is the direct assertion of the
    # change of definition, so it must read `modification`.
    "nib_is_modification": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 6000, 1), ("03", "N", 6000, 1),
        ("00", "N", 6000, 1),
    ],
    # the deferral arm: field 108 alone, rate and term untouched, which is what
    # C10-4 measured this population does on 99.66 per cent of its onsets
    "defer_triangle": [
        ("00", "N", 0, 0, 0, None, 0, 0), ("00", "N", 0, 1, 0, None, 0, 0),
        ("00", "N", 0, 1, 0, None, 0, 0), ("01", "N", 0, 1, 0, None, 0, 0),
        ("02", "N", 0, 1, 0, None, 0, 6000),
        ("03", "N", 0, 1, 0, None, 0, 6000),
        ("00", "N", 0, 1, 0, None, 0, 6000),
    ],
    # §17.6: the departure vertex lands on the zero-UPB opening rows
    "departure_zero_upb": [
        ("00", "N", 0, 0),
        ("01", "N", 0, 1), ("02", "Y", 0, 1),
        ("00", "Y", 0, 1),
    ],
    # a clean cure whose note rate changes on the cure row and which carries no
    # modification flag anywhere. `find_clean_cures` admits it, so it lands in
    # C10-1's **floor**, which is exactly the reporting noise that floor exists
    # to measure. Without it the floor reads zero and the multiple is undefined.
    "clean_cure_rate_blip": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("02", "N", 0, 1),
        ("00", "N", 0, 1, 0, 4.75), ("00", "N", 0, 1),
    ],
    # an unknown status row inside the window: a load figure, not a filter
    "unknown_inside": [
        ("00", "N", 0, 0), ("00", "N", 0, 1), ("00", "N", 0, 1),
        ("01", "N", 0, 1), ("XX", "N", 0, 1), ("02", "Y", 0, 1),
        ("00", "Y", 0, 1),
    ],
}

#: What each case must produce. **Written from §17, before the run.**
EXPECT = {
    "plain_mod": ("loop", ARM_MOD),
    "clean_cure": ("none", None),
    "cure_then_mod": ("loop", ARM_MOD),
    "mod_equals_cure": ("loop", ARM_MOD),
    "two_arms": ("drop", "two_arms"),
    "two_arms_defer_first": ("drop", "two_arms"),
    "two_mod_onsets": ("loop", ARM_MOD),
    "never_cures": ("drop", "not_closed"),
    "mod_while_current": ("drop", "no_delinquency"),
    "gap_in_window": ("drop", "gap_in_window"),
    "nib_is_modification": ("loop", ARM_MOD),
    "defer_triangle": ("loop", ARM_DEFER),
    "clean_cure_rate_blip": ("none", None),
    "departure_zero_upb": ("drop", "vertex_upb_zero"),
    "unknown_inside": ("loop", ARM_MOD),
}


#: Quiet, properly amortising months prepended to every case.
#:
#: **They exist for block two and they change nothing here.** ``t_A`` is the
#: *last* current row strictly before ``t_M``, so extra current rows in front
#: of a case cannot move it, and no entry in ``EXPECT`` reads a balance amount.
#: What they give is a contract period with enough quiet months for
#: `b8_omega.contract_payments` to estimate a payment from, without which
#: **every loop in this fixture is unmeasurable and `b8_loop_omega`'s
#: end-to-end run is over an empty set** (坑 23's family: a distribution over
#: nothing prints exactly like a measured one).
#:
#: `MIN_QUIET_FOR_PAYMENT` is 2 and `modal_cluster` wants a mode, so eight is
#: clear of both and short enough to keep the fixture readable.
LEAD_QUIET = 8

#: Quiet, amortising months appended after every case **except the ones a tail
#: would change the answer for**.
#:
#: Leg 3 lives in the **post-modification** contract period, and `r(t)` there
#: needs that period to have a contract payment, which needs quiet months
#: inside it. Without a tail every case has one or two rows after its
#: modification, `MIN_QUIET_FOR_PAYMENT` is never met, and **leg 3 is
#: unmeasurable in the fixture for a reason that has nothing to do with leg 3.**
TAIL_QUIET = 8

#: ``never_cures`` is the right-censored case: §17.7's first non-closure class
#: is *no return vertex exists*. **A quiet tail would give it one** and turn the
#: case into its own opposite. Listed by name with the reason, rather than left
#: as a silent asymmetry in the generator.
NO_TAIL = {"never_cures"}


def _synth_loops(path: Path) -> list[str]:
    """One loan per case, in ``CASES`` order, so loan ordinal is case ordinal.

    **The balance amortises on quiet months.** It used to be a constant
    200,000.00 on every row, under which a quiet pair's implied payment is pure
    interest and no contract payment is identified anywhere in the fixture.
    That was invisible while this file only counted windows.
    """
    names = list(CASES)
    lines = []
    for L, name in enumerate(names):
        lid = f"{910000000000 + L}"
        rate, bal, rem, y, m, age = 5.0, 200000.0, 360, 2010, 1, 0
        pmt = float(K.level_payment([bal], [rate], [rem])[0])
        case = list(CASES[name])
        tail = []
        if name not in NO_TAIL:
            hold = case[-1][1]           # keep the modification flag as it is
            tail = [("00", hold, 0, 1)] * TAIL_QUIET
        prev_mod = "N"
        for spec in [("00", "N", 0, 1)] * LEAD_QUIET + case + tail:
            dq, mod, nib, upb_pos = spec[0], spec[1], spec[2], spec[3]
            skip = spec[4] if len(spec) > 4 else 0
            dfr = spec[7] if len(spec) > 7 else 0
            if len(spec) > 5 and spec[5] is not None:
                rate = spec[5]
            if len(spec) > 6 and spec[6]:
                rem += spec[6]
            for _ in range(skip):
                m += 1
                if m == 13:
                    m, y = 1, y + 1
                rem -= 1
                age += 1
            f = [""] * K.NFIELDS
            f[1] = lid
            f[2] = f"{m:02d}{y:04d}"
            f[3] = "R"
            f[8] = f"{rate:.3f}"
            f[11] = f"{bal:.2f}" if upb_pos else "0.00"
            f[12] = "360"
            f[15] = str(age)
            f[16] = str(rem)
            f[17] = str(rem)
            f[18] = "012040"
            f[19] = "80"
            f[22] = "35"
            f[23] = "720"
            f[25] = "N"
            f[26] = "P"
            f[29] = "P"
            f[30] = "CA"
            f[39] = dq
            f[41] = mod
            f[62] = f"{nib:.2f}" if nib else ""
            f[107] = f"{dfr:.2f}" if dfr else ""
            f[101] = "7"
            f[105] = "7"
            lines.append("|".join(f))
            # amortise on a quiet, positive-balance month and hold otherwise.
            # A missed month is a month the balance does not fall, which is
            # §14.3 leg 1 and is what makes `omega1` positive.
            # amortise on a quiet, positive-balance month, but **not on the
            # modification onset itself**: that month is a re-contracting and
            # its balance is whatever the servicer wrote, not last month's
            # balance carried forward. Everything after the onset amortises
            # again, which is what gives leg 3 a payment to be measured with.
            if mod == "Y" and prev_mod != "Y" and rem > 0:
                # **a modification re-amortises**: the payment after it is the
                # level payment on the new rate and the new term. Without this
                # the fixture's post-modification payment equals its
                # pre-modification one, and then nothing can tell `V-hat`'s
                # payment being taken from the wrong contract period.
                pmt = float(K.level_payment([bal], [rate], [float(rem)])[0])
            elif dq == "00" and upb_pos:
                bal = bal * (1.0 + rate / 1200.0) - pmt
            prev_mod = mod
            rem -= 1
            age += 1
            m += 1
            if m == 13:
                m, y = 1, y + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")
    return names


def _fixture_tag() -> str:
    """Eight hex digits of **this module's** fixture generator.

    Pit 19's second half: the tag must hang on the source that writes the
    fixture, not on some other module's. ``b8_triangles`` hung its tag on
    ``b8_core``'s generator, changed its own case table, and silently reused a
    stale archive.
    """
    src = inspect.getsource(_synth_loops) + repr(CASES)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:8]


def selftest() -> int:
    tag = _fixture_tag()
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{tag}.zip"
    cache_root = root / "cache"
    if not zp.exists():
        names = _synth_loops(zp)
        print(f"  built fixture {zp.name} (generator {tag})", file=sys.stderr)
    else:
        names = list(CASES)
        print(f"  reusing fixture {zp.name} (generator {tag})", file=sys.stderr)

    K.build_archive(zp, force=True, cache_root=cache_root)
    fails = []
    # opened with CENSUS_COLS, not with every column: see the note there
    with K.Core(zp.stem, cols=CENSUS_COLS, loan_cols=[],
                cache_root=cache_root) as c:
        if int(c.n_loans) != len(names):
            fails.append(f"fixture has {c.n_loans} loans, {len(names)} cases")
        lp = find_loops(c)
        cnt = lp["counts"]
        per_loan = {}
        for k in range(lp["t_A"].size):
            per_loan.setdefault(int(lp["loan"][k]), []).append(int(lp["arm"][k]))

        for L, name in enumerate(names):
            want, detail = EXPECT[name]
            got = per_loan.get(L, [])
            if want == "loop":
                if len(got) != 1:
                    fails.append(f"{name}: expected 1 loop, got {len(got)}")
                elif got[0] != detail:
                    fails.append(f"{name}: arm {ARM_NAME[got[0]]}, "
                                 f"expected {ARM_NAME[detail]}")
            else:
                if got:
                    fails.append(f"{name}: expected no loop ({detail}), "
                                 f"got {len(got)}")
            print(f"  {name:<22} loops={len(got)} "
                  f"arms={[ARM_NAME[a] for a in got]}", file=sys.stderr)

        # Each named drop reason must fire exactly as many times as there are
        # cases expecting it, or a case was rejected for a different reason
        # than the one it tests. **Counted rather than fixed at one**, because
        # `two_arms` now has two cases: one of them made the §17.4 population
        # untestable, since a count of 1 is what `np.size` on a dict also
        # returns and `b8_loop_omega` shipped exactly that to a results file.
        wanted: dict[str, int] = {}
        for name, (want, detail) in EXPECT.items():
            if want == "drop":
                wanted[detail] = wanted.get(detail, 0) + 1
        for detail, k in wanted.items():
            if cnt.get(f"drop_{detail}", 0) != k:
                fails.append(f"drop_{detail} fired "
                             f"{cnt.get(f'drop_{detail}')} times, expected "
                             f"{k} (one per case expecting it)")

        if cnt["loops_mod_equals_cure"] != 1:
            fails.append(f"loops_mod_equals_cure {cnt['loops_mod_equals_cure']}"
                         " expected 1")
        if cnt["loops_multi_onset"] != 1:
            fails.append(f"loops_multi_onset {cnt['loops_multi_onset']}"
                         " expected 1")
        if cnt["windows_with_unknown_status"] != 1:
            fails.append("windows_with_unknown_status "
                         f"{cnt['windows_with_unknown_status']} expected 1")
        # the fixture must exercise every drop reason it claims to, or the test
        # is vacuous in the way pit 19 describes
        for k in ("drop_two_arms", "drop_not_closed", "drop_no_delinquency",
                  "drop_gap_in_window", "drop_vertex_upb_zero"):
            if cnt.get(k, 0) == 0:
                fails.append(f"{k} never fired; the fixture does not test it")

        # `against_triangles` is only reached by `census`, so without this it
        # is untested until it runs on a real archive. Its first version read
        # `["tri"]` where `b8_triangles` returns `["triangle"]`, which would
        # have surfaced as a KeyError after a full scan rather than here.
        # **A code path a selftest does not enter is not covered by it.**
        # pit 28: computed-and-unprinted is the failure mode this check exists
        # for. The onset split is new in this revision and must reach the file.
        txt = render([dict(lp["counts"], name="fixture",
                           **{f"tri_{k}": v
                              for k, v in against_triangles(c, lp).items()})])
        for _c in K.check_markdown_tables(txt):
            fails.append(f"malformed table: {_c}")
        for need in ("## 1. Loops found", "### 1.1 What the modification onset",
                     "## 2. Why a candidate", "### 2.1", "## 3. §17.13",
                     "## 4. Unknown delinquency"):
            if need not in txt:
                fails.append(f"render omits the section `{need}`")
        for need in ("field 42", "field 63", "field 108"):
            if need not in txt:
                fails.append(f"render never names `{need}`")

        tri_cmp = against_triangles(c, lp)
        print(f"  vs C3/C4: {tri_cmp}", file=sys.stderr)
        if tri_cmp["loops_mod"] != cnt["loops_mod_arm"]:
            fails.append("against_triangles disagrees with the census on the "
                         "modification-arm loop count")
        if tri_cmp["tri_without_loop"] < 1:
            fails.append("the fixture has no loan that C3/C4 counts and §17 "
                         "does not, so §17.13's two-way gap is untested")

        # cure_then_mod's departure vertex is the row before the SECOND run.
        # Checked by position rather than by count, because a count cannot tell
        # a right anchor from a wrong one.
        L = names.index("cure_then_mod")
        idx = [k for k in range(lp["t_A"].size) if int(lp["loan"][k]) == L]
        # **Expressed relative to the lead-in**, not as a bare 5. The lead-in
        # is a property of the generator and the anchor is a property of the
        # case, so a literal here would have to be edited every time the
        # generator changes and would look like a result while being an offset.
        want = LEAD_QUIET + 5
        if len(idx) == 1:
            off = int(lp["t_A"][idx[0]]) - int(c.row_start[L])
            if off != want:
                fails.append(f"cure_then_mod anchored at row {off}, "
                             f"expected {want}")
            else:
                print(f"  cure_then_mod t_A at loan row {off} (correct)",
                      file=sys.stderr)

    print(f"\n  counts: {cnt}", file=sys.stderr)
    if fails:
        print("\nSELFTEST FAILED", file=sys.stderr)
        for f in fails:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nselftest ok", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# census
# ---------------------------------------------------------------------------

def census(names: list[str]) -> int:
    rows = []
    for name in names:
        with K.Core(name, cols=CENSUS_COLS, loan_cols=[]) as c:
            lp = find_loops(c)
            a = dict(lp["counts"])
            a["name"] = name
            a.update({f"tri_{k}": v for k, v in
                      against_triangles(c, lp).items()})
            rows.append(a)
        print(f"  {name}: {a['loops']:,} loops", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rows), encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}", file=sys.stderr)
    return 0


def render(rows: list[dict]) -> str:
    L = []
    A = L.append
    A("# B8: the registered loop windows, block one\n")
    A("Generated by `experiments/b8_loops.py census`. Registered in "
      "`docs/b8_fannie_slice.md` §17.\n")
    A("**No `omega` is computed here and no prediction is read.** This block "
      "finds the windows and counts them; the residual is block two. A window "
      "that is off by one row is invisible in a residual and obvious in a "
      "count, which is why the split is here.\n")

    A("\n## 1. Loops found\n")
    A("| archive | onsets | candidates | **loops** | modification | deferral | "
      "`t_M == t_B` | multi-onset | window len p10 / p50 / p90 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        q = r["window_len_q"]
        A(f"| {r['name']} | {r['onsets_raw']:,} | {r['candidate_loops']:,} | "
          f"**{r['loops']:,}** | {r['loops_mod_arm']:,} | "
          f"{r['loops_defer_arm']:,} | {r['loops_mod_equals_cure']:,} | "
          f"{r['loops_multi_onset']:,} | "
          f"{q[0]:.0f} / {q[1]:.0f} / {q[2]:.0f} |")
    A("\n`t_M == t_B` is §17.3: the flag turns on and the row reads `00`, so "
      "leg 3 is empty **by construction**. Those loops must not be pooled into "
      "the `omega_3` reading §14.3 promises is measured rather than assumed.\n")

    A("\n### 1.1 What the modification onset is made of\n")
    A("**§14.3 leg 2 defines the modification onset as field 42 or field 63, "
      "whichever comes first**, and that is registered text. Before C10-4 this "
      "file cut field 63 as a *deferral* onset instead; C10-4 measured that at "
      "a field-63 rising edge the note rate moves on 46.1 per cent of onsets "
      "and the legal maturity on 84.2 per cent, which is a re-contracting. "
      "**The split is printed so the change of definition is auditable rather "
      "than only assertable.**\n")
    A("| archive | mod onsets | field 42 | field 63 | both on one row | "
      "deferral onsets (field 108) |")
    A("|---|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['onsets_mod']:,} | "
          f"{r['onsets_mod_field42']:,} | {r['onsets_mod_field63']:,} | "
          f"{r['onsets_mod_both_same_row']:,} | {r['onsets_defer']:,} |")

    A("\n## 2. Why a candidate was dropped\n")
    A("**Two columns per reason.** `marginal` is what it removes given the "
      "conditions before it; `alone` is what it would remove on its own. They "
      "differ exactly where conditions overlap, and a bare marginal cannot be "
      "read without its load (§15.5, pit 22).\n")
    A("**`not_closed` is a precondition, not one condition among several**, and "
      "the `alone` figures for every interior test are therefore computed on "
      "the **closed** candidates only. With no `t_B` the window does not exist "
      "and an interior test applied to it fails for a reason that is not its "
      "own. The first run of this file reported `no_delinquency` alone = 2 on a "
      "fixture holding one such case; the second was an unclosed candidate "
      "bleeding through the safe-index substitution. **Found by reading this "
      "table, not by a check.**\n")
    keys = ["not_closed", "two_arms", "no_delinquency", "vertex_rem_blank",
            "vertex_upb_zero", "departure_is_first_row", "gap_in_window"]
    A("| archive | " + " | ".join(f"{k}<br>marg / alone" for k in keys) + " |")
    A("|---" * (len(keys) + 1) + "|")
    for r in rows:
        cells = [f"{r[f'drop_{k}']:,} / {r[f'drop_{k}_alone']:,}" for k in keys]
        A(f"| {r['name']} | " + " | ".join(cells) + " |")

    A("\n### 2.1 `not_closed` splits two ways and they are different objects\n")
    A("A loan still reporting at the end of the archive is **right censored**; "
      "one that stopped reporting has terminated. Pit 13: termination is marked "
      "by the contract state going blank, not by the zero-balance code.\n")
    A("| archive | right censored | terminated | left-truncated mod | "
      "left-truncated deferral |")
    A("|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['drop_not_closed_right_censored']:,} | "
          f"{r['drop_not_closed_terminated']:,} | "
          f"{r['left_truncated_mod']:,} | {r['left_truncated_defer']:,} |")

    A("\n## 3. §17.13: C3/C4 counts loans, §17 counts loops\n")
    A("**The two are not the same object and the difference runs both ways.** "
      "A loan can carry several loops, and a loan C3/C4 counts can carry none. "
      "Printed rather than assumed small.\n")
    A("| archive | C3/C4 loans | loans with a mod loop | mod loops | "
      "**tri without loop** | **loop without tri** |")
    A("|---|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['tri_tri_loans']:,} | "
          f"{r['tri_loop_loans_mod']:,} | {r['tri_loops_mod']:,} | "
          f"**{r['tri_tri_without_loop']:,}** | "
          f"**{r['tri_loop_without_tri']:,}** |")

    A("\n## 4. Unknown delinquency status inside a window\n")
    A("§17.2's condition is that no `current` row sits inside. A row whose "
      "status is blank or `XX` is neither current nor delinquent, so it does "
      "**not** break the condition as registered. `find_clean_cures` is "
      "stricter, requiring the interior to be entirely delinquent. **The "
      "difference is printed rather than legislated**; if it is material, that "
      "is a ruling to make against these numbers.\n")
    A("| archive | unknown-status rows | inside a window | windows touched |")
    A("|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['unknown_status_rows']:,} | "
          f"{r['unknown_status_inside_windows']:,} | "
          f"{r['windows_with_unknown_status']:,} |")

    A("\n## What this does not decide\n")
    A("- **It computes no `omega`.** Block two does.\n")
    A("- It does not choose the deferral onset column. Field 63 is used here "
      "because that is what the code already cuts on; O24 and B10 §19.9 are "
      "open and §17.9 guarantees swapping the column does not change the "
      "window.\n")
    A("- It applies none of §7's unrun filters (single family, first lien, "
      "owner occupied, fixed rate).\n")
    A("- It reads no prediction.\n")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["selftest", "census"])
    ap.add_argument("--only", action="append", default=None)
    a = ap.parse_args()
    if a.cmd == "selftest":
        raise SystemExit(selftest())
    names = a.only or ["2002Q1", "2006Q1", "2007Q1", "2012Q1", "2017Q1",
                       "2019Q1"]
    raise SystemExit(census(names))


if __name__ == "__main__":
    main()
