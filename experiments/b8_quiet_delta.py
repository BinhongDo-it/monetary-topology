#!/usr/bin/env python3
"""B8: the double report the 2026-08-16 quiet-filter correction owes.

Registered in the B8 inputs register §6.2.10.

**Why this file exists.** On 2026-08-16 ``b8_core.quiet_pairs`` gained
``upb[cur] > 0``: a pair whose later row reports a zero balance is a
termination, which is an event, so it is not a quiet month. R01 requires that a
change of convention on the same data be **re-run and double reported**. The
four scripts that import ``b8_core`` were re-run, and none of them prints how
many pairs the correction removed, so **the re-run did not discharge the
double report**. ``quiet_pairs`` computes the number and returns it as
``n_dropped_cur_zero``; nothing was reading it.

Neither could the number be recovered by comparing files. ``C8-1c(b)`` is
frozen on its own hand-written filter and counts quiet months only inside the
segments it could estimate on (881,715 of 916,104 on 2002Q1, the difference
being exactly its ``short`` plus ``min <= 0`` columns), so its §1 is a
different population and always was. The earlier ``C8-1e`` output was
overwritten without an ``.expired`` copy. **The only way to the number is to
measure it.**

**And the claim it has to settle is a real one.** §6.2.10 asserts that the
contamination sits *above* the mode, and therefore that the median and the
"8.8 per cent below the mode" finding are untouched. That is an argument, not a
measurement: a dropped pair carries ``obs`` equal to the **entire remaining
balance**, so it should land far above any plausible modal payment. §3 below
puts a number on it, and §3 is the section that can refute it.

Three tables:

  1. **How big.** Pairs under each convention, the drop, and its share. The
     two paths are cross-checked against each other rather than trusted.
  2. **What moved.** at / below / above the segment mode under **both**
     conventions, modes recomputed from scratch on each population, because
     removing a month from a segment can move that segment's mode.
  3. **Where the dropped pairs sat.** Their side under the old convention and
     the distribution of ``implied / mode``. **If they are not concentrated
     above the mode, §6.2.10's claim is wrong and this file says so.**

**No prediction is read here and no outcome terminates the stage.**

Usage::

    python experiments/b8_quiet_delta.py --selftest
    python experiments/b8_quiet_delta.py --only 2002Q1
    python experiments/b8_quiet_delta.py
"""
from __future__ import annotations

import argparse
import gc
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402

OUT = K.ROOT / "results" / "b8_quiet_delta.md"

#: Quantiles reported for the dropped pairs' ``implied / mode``. The top end is
#: carried because the interesting claim is that these sit far above the mode,
#: and a p50 alone cannot show "far".
QS = [0.01, 0.10, 0.50, 0.90, 0.99]

#: A dropped pair's implied payment is the whole balance plus one month of
#: interest, so the ratio is large and unbounded. It is clipped only for the
#: histogram, never for the quantiles.
HIST_EDGES = [0.0, 0.5, 0.95, 1.05, 2.0, 5.0, 20.0, 100.0, np.inf]


@dataclass
class Arch:
    name: str
    n_old: int = 0
    n_new: int = 0
    n_drop: int = 0
    n_drop_reported: int = 0
    seg_old: int = 0
    seg_new: int = 0
    # side counts, (at, below, above), one triple per convention
    old_side: tuple = (0, 0, 0)
    new_side: tuple = (0, 0, 0)
    # where the dropped pairs sat under the old convention
    drop_side: tuple = (0, 0, 0)
    drop_q: list = field(default_factory=list)
    drop_hist: list = field(default_factory=list)
    drop_ratio_finite: int = 0
    drop_mode_nonpos: int = 0
    # a dropped pair alone in its segment sets that segment's mode to a payoff
    drop_seg1: int = 0
    drop_seg2: int = 0
    seg_touched: int = 0
    seg_all_dropped: int = 0
    # attribution: which condition already excluded the terminal pairs
    new_identical: bool = False
    n_terminal: int = 0
    attr: dict = field(default_factory=dict)
    n_only_cur: int = 0
    fails: list = field(default_factory=list)


def _sides(q: dict, seg: np.ndarray):
    """(at, below, above) counts against the per-segment modal cluster.

    The membership test is the cluster, not equality with the mode: the mode is
    a cluster **mean** and no month equals it exactly. ``lo`` and ``hi`` are the
    cluster's own bounds, which is the same test C8-1c(b) and C8-1e use.
    """
    mode, lo, hi, _ncand, _start, _count, implied = K.segment_modes(q, seg)
    below = implied < lo
    above = implied > hi
    at = ~(below | above)
    return (int(at.sum()), int(below.sum()), int(above.sum())), mode, implied


#: The quiet predicate, condition by condition, in the order ``quiet_pairs``
#: applies them. Each entry is (label, function of (c, cur, prv) -> bool array
#: that is True when the condition **holds**). Kept as data so the attribution
#: cannot drift from a hand-written re-listing without the count moving.
def _conditions(c):
    period = c.row["period"].astype(np.int32)
    rate = c.row["rate"].astype(np.int32)
    upb = c.row["upb"].astype(np.int64)
    rem = c.row["rem_legal"].astype(np.int32)
    dq = c.row["delinq"]
    mf = c.row["mod_flag"]
    nib = c.row["nib_upb"].astype(np.int64)
    loan = c.loan_of_row()
    seen = c.cummax_within_loan((nib != K.U32_NA) & (nib > 0))
    return [
        ("same loan", lambda u, v: loan[u] == loan[v]),
        ("period present, both", lambda u, v: (period[u] != K.U16_NA)
         & (period[v] != K.U16_NA)),
        ("period steps by one", lambda u, v: (period[u] - period[v]) == 1),
        ("delinq 00, both", lambda u, v: (dq[u] == 0) & (dq[v] == 0)),
        ("mod flag unchanged", lambda u, v: (mf[u] == K._Y) == (mf[v] == K._Y)),
        ("**remaining term present, both**",
         lambda u, v: (rem[u] != K.U16_NA) & (rem[v] != K.U16_NA)),
        ("remaining term falls by one", lambda u, v: (rem[v] - rem[u]) == 1),
        ("**note rate present, both**", lambda u, v: (rate[u] != K.U16_NA)
         & (rate[v] != K.U16_NA)),
        ("note rate unchanged", lambda u, v: rate[u] == rate[v]),
        ("previous UPB present", lambda u, v: upb[v] != K.U32_NA),
        ("current UPB present", lambda u, v: upb[u] != K.U32_NA),
        ("never deferred up to here", lambda u, v: ~seen[u]),
    ]


def _attribute(c, upb):
    """Why the correction removes nothing: what already excluded these pairs.

    **This is the section that turns a redundant guard into a documented one.**
    The measurement said the correction removes zero pairs on the real file, so
    the inference behind it (a payoff pair enters the sample carrying the whole
    balance) was wrong. It was wrong because some *other* condition already
    excludes those pairs, and **which one matters**: the guard is dead only for
    as long as that condition stays. If it is ever relaxed, the guard becomes
    load bearing on the same day.

    The candidate set is every adjacent same-loan pair with a positive previous
    balance and a zero current balance, which is exactly a payoff as the file
    reports it. For each condition the count is **marginal**: how many
    candidates that condition alone rejects, not an exclusive partition, so the
    columns do not sum to the total and are not meant to.
    """
    n = c.n_rows
    cur = np.arange(1, n, dtype=np.int64)
    prv = cur - 1
    loan = c.loan_of_row()
    cand = (loan[cur] == loan[prv]) & (upb[prv] != K.U32_NA) \
        & (upb[prv] > 0) & (upb[cur] != K.U32_NA) & (upb[cur] == 0)
    u, v = cur[cand], prv[cand]
    total = int(u.size)

    attr = {}
    surv = np.ones(total, dtype=bool)
    for label, fn in _conditions(c):
        held = np.asarray(fn(u, v), dtype=bool)
        attr[label] = int((~held).sum())
        surv &= held
    return total, attr, int(surv.sum())


def measure(name: str) -> Arch:
    a = Arch(name)
    c = K.Core(name)
    try:
        upb = c.row["upb"].astype(np.int64)

        q_old = K.quiet_pairs(c, require_cur_positive=False)
        q_new = K.quiet_pairs(c)

        a.n_old = int(q_old["cur"].size)
        a.n_new = int(q_new["cur"].size)
        a.n_drop = a.n_old - a.n_new
        a.n_drop_reported = int(q_new["n_dropped_cur_zero"])

        # cross-check the two paths against each other. The corrected call must
        # be the old population restricted to a positive current balance, pair
        # for pair, or one of the two is doing something else.
        keep = upb[q_old["cur"]] > 0
        if not np.array_equal(q_old["cur"][keep], q_new["cur"]):
            a.fails.append(
                "the corrected filter is not the old one restricted to "
                "upb[cur] > 0")
        if a.n_drop != a.n_drop_reported:
            a.fails.append(
                f"n_dropped_cur_zero says {a.n_drop_reported:,} but the "
                f"populations differ by {a.n_drop:,}")
        # NOT a failure. On the real file the correction removes nothing, and
        # §4 says which condition already did the work. It was a failure while
        # the file claimed the correction was load bearing; it is a finding now.

        # every dropped pair must have a zero current balance, by construction.
        # asserted rather than assumed because it is one line.
        if int((upb[q_old["cur"][~keep]] != 0).sum()) != 0:
            a.fails.append("a dropped pair had a non-zero current balance")

        a.n_terminal, a.attr, a.n_only_cur = _attribute(c, upb)
        if a.n_only_cur != a.n_drop:
            a.fails.append(
                f"attribution says {a.n_only_cur:,} terminal pairs pass every "
                f"other condition, but the correction removed {a.n_drop:,}")

        seg_old = K.segment_ids(q_old)
        a.seg_old = int(seg_old.max()) + 1 if seg_old.size else 0
        a.old_side, mode_old, implied_old = _sides(q_old, seg_old)

        # the dropped pairs, scored on the OLD population's modes, which is the
        # population they were actually part of
        d_impl = implied_old[~keep]
        d_mode = mode_old[~keep]
        at_o, be_o, ab_o = 0, 0, 0
        if d_impl.size:
            _m, lo, hi, _n, start, count, _i = K.segment_modes(q_old, seg_old)
            d_lo, d_hi = lo[~keep], hi[~keep]
            be = d_impl < d_lo
            ab = d_impl > d_hi
            at_o = int((~(be | ab)).sum())
            be_o = int(be.sum())
            ab_o = int(ab.sum())

            # **How a dropped pair can fail to sit above the mode.** At most one
            # payoff exists per loan and a segment never spans loans, so a
            # segment holds at most one dropped pair. When that pair is the
            # segment's only member, the modal cluster is computed from the
            # payoff alone and the payoff **is** the mode; the pair then reads
            # "at mode" and its segment's mode is a whole balance rather than a
            # payment. With two members the cluster can still be dragged. Both
            # are counted rather than asserted away, because they are the route
            # by which the correction could move the below-mode share: a
            # segment whose mode was set by a payoff mis-scores its other
            # months.
            per_pair = count[seg_old]
            d_size = per_pair[~keep]
            a.drop_seg1 = int((d_size == 1).sum())
            a.drop_seg2 = int((d_size == 2).sum())
            dropped_per_seg = np.bincount(seg_old[~keep], minlength=count.size)
            a.seg_touched = int((dropped_per_seg > 0).sum())
            a.seg_all_dropped = int((dropped_per_seg == count).sum())
            del _m, lo, hi, _n, start, count, _i, d_lo, d_hi, be, ab
            del per_pair, d_size, dropped_per_seg

            good = d_mode > 0
            a.drop_mode_nonpos = int((~good).sum())
            ratio = d_impl[good] / d_mode[good]
            a.drop_ratio_finite = int(ratio.size)
            if ratio.size:
                a.drop_q = [float(x) for x in np.quantile(ratio, QS)]
                a.drop_hist = [int(x) for x in
                               np.histogram(ratio, bins=HIST_EDGES)[0]]
            del ratio, good
        a.drop_side = (at_o, be_o, ab_o)

        del mode_old, implied_old, d_impl, d_mode, seg_old, q_old
        gc.collect()

        if a.n_drop == 0:
            # The two populations were already checked equal pair for pair, so
            # the modal cluster is computed from the same numbers in the same
            # segments and a second pass can only reproduce the first. Skipped
            # because that pass is the expensive part of this file, **not**
            # because it is assumed: the equality it rests on is asserted in
            # §1 and a mismatch there is already a recorded failure.
            a.seg_new = a.seg_old
            a.new_side = a.old_side
            a.new_identical = True
            del q_new
        else:
            seg_new = K.segment_ids(q_new)
            a.seg_new = int(seg_new.max()) + 1 if seg_new.size else 0
            a.new_side, mode_new, implied_new = _sides(q_new, seg_new)
            del mode_new, implied_new, seg_new, q_new
        gc.collect()
    finally:
        c.close()
    return a


# ---------------------------------------------------------------------------


def rate(x, n):
    return f"{x / n:.4f}" if n else "-"


def report(archs: list[Arch]) -> str:
    L = []
    A = L.append
    A("# B8: what the quiet-filter correction actually removed\n")
    A("Generated by `experiments/b8_quiet_delta.py` from the core table. "
      "Registered in the B8 inputs register §6.2.10.\n")
    A("**This is the double report R01 requires**, and it is a separate file "
      "because the four scripts that were re-run under the corrected filter "
      "print their new numbers without printing the delta. **A re-run whose "
      "output cannot be differenced against the old convention does not "
      "discharge the double report.**\n")
    A("**Reads no prediction.**\n")

    A("\n## 1. How big the correction is\n")
    A("`old` is the filter as it stood before 2026-08-16, reproduced by "
      "`require_cur_positive=False`. `new` is the default. The two are also "
      "checked pair for pair against each other, not just by count.\n")
    A("| archive | pairs, old | pairs, new | **removed** | rate | "
      "n_dropped_cur_zero | segments, old | new |")
    A("|---|---|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.n_old:,} | {a.n_new:,} | **{a.n_drop:,}** | "
          f"{rate(a.n_drop, a.n_old)} | {a.n_drop_reported:,} | "
          f"{a.seg_old:,} | {a.seg_new:,} |")

    A("\n## 2. What it moved\n")
    A("Sides are against the per-segment modal cluster, **modes recomputed "
      "from scratch on each population**, because dropping a month from a "
      "segment can move that segment's mode. The `below` column is the one "
      "§6.2.6 reads a finding off.\n")
    if any(a.new_identical for a in archs):
        A("Where the correction removed nothing the two populations are the "
          "same pairs in the same segments, checked pair for pair in §1, so "
          "the `new` row is the `old` row and the second modal pass is not "
          "run. It is marked `=`.\n")
    A("| archive | conv | at mode | rate | below | **rate** | above | rate |")
    A("|---|---|---|---|---|---|---|---|")
    for a in archs:
        newtag = "**new** `=`" if a.new_identical else "**new**"
        for tag, (at, be, ab), n in (("old", a.old_side, a.n_old),
                                     (newtag, a.new_side, a.n_new)):
            A(f"| {a.name} | {tag} | {at:,} | {rate(at, n)} | {be:,} | "
              f"**{rate(be, n)}** | {ab:,} | {rate(ab, n)} |")

    A("\n## 3. Where the removed pairs sat, which is the section that can "
      "refute §6.2.10\n")
    A("Scored on the **old** population's modes, the population they were "
      "part of. §6.2.10 claimed the contamination sits above the mode. "
      "**If the `above` column is not overwhelming that claim is wrong, and "
      "if `removed` is zero there was no contamination to place and the "
      "claim was wrong in a stronger way.**\n")
    A("| archive | removed | at mode | below | **above** | **rate above** |")
    A("|---|---|---|---|---|---|")
    for a in archs:
        at, be, ab = a.drop_side
        A(f"| {a.name} | {a.n_drop:,} | {at:,} | {be:,} | **{ab:,}** | "
          f"**{rate(ab, a.n_drop)}** |")

    A("\nA segment holds at most one dropped pair, since a loan pays off once "
      "and a segment never spans loans. **When the dropped pair is the "
      "segment's only member, the modal cluster is computed from the payoff "
      "alone and the payoff is the mode**, so the pair reads `at mode` and "
      "that segment's mode was a whole balance rather than a payment. Those "
      "segments are the route by which the correction can move the below-mode "
      "share, so they are counted.\n")
    A("| archive | dropped, alone in segment | in a segment of two | "
      "segments touched | rate of old segments | **segments that were "
      "nothing but a payoff** |")
    A("|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.drop_seg1:,} | {a.drop_seg2:,} | "
          f"{a.seg_touched:,} | {rate(a.seg_touched, a.seg_old)} | "
          f"**{a.seg_all_dropped:,}** |")

    A("\n`implied / mode` on the removed pairs. A dropped pair pays off the "
      "whole balance, so this is large by construction and the quantiles say "
      "how large. Pairs whose segment mode is non-positive are excluded and "
      "counted.\n")
    A("| archive | scored | mode <= 0 | " +
      " | ".join(f"p{int(q * 100)}" for q in QS) + " |")
    A("|---|---|---|" + "---|" * len(QS))
    for a in archs:
        cells = " | ".join(f"{x:,.2f}" for x in a.drop_q) if a.drop_q \
            else " | ".join("-" for _ in QS)
        A(f"| {a.name} | {a.drop_ratio_finite:,} | {a.drop_mode_nonpos:,} | "
          f"{cells} |")

    A("\nHistogram of the same ratio.\n")
    lab = ["0-0.5", "0.5-0.95", "0.95-1.05", "1.05-2", "2-5", "5-20",
           "20-100", "100+"]
    A("| archive | " + " | ".join(lab) + " |")
    A("|---|" + "---|" * len(lab))
    for a in archs:
        cells = " | ".join(f"{x:,}" for x in a.drop_hist) if a.drop_hist \
            else " | ".join("-" for _ in lab)
        A(f"| {a.name} | {cells} |")

    A("\n## 4. Why it removes nothing: what already excluded these pairs\n")
    A("The correction is a **guard, not a repair**. The candidate set is every "
      "adjacent same-loan pair with a positive previous balance and a zero "
      "current balance, which is a payoff exactly as the file reports it. "
      "**The inference that these entered the quiet sample was wrong**, and "
      "this table is which condition was already keeping them out. Counts are "
      "marginal, so they do not sum to the total and are not meant to: a pair "
      "rejected by three conditions appears in all three columns.\n")
    A("**Why it is worth writing down rather than dropping the guard.** The "
      "guard is dead only for as long as the condition below stays. Relax "
      "that condition, and the guard becomes load bearing the same day.\n")
    labels = [k for k in (archs[0].attr if archs else {})]
    A("| archive | payoff pairs | " + " | ".join(labels) +
      " | **pass everything else** |")
    A("|---|---|" + "---|" * (len(labels) + 1))
    for a in archs:
        cells = " | ".join(f"{a.attr.get(k, 0):,}" for k in labels)
        A(f"| {a.name} | {a.n_terminal:,} | {cells} | "
          f"**{a.n_only_cur:,}** |")

    bad = [f for a in archs for f in a.fails]
    A("\n## 5. Consistency\n")
    if bad:
        A("**CHECKS FAILED. Nothing above is quotable until these are "
          "resolved.**\n")
        for f in bad:
            A(f"- {f}")
        A("")
    else:
        n_live = sum(1 for a in archs if a.n_drop > 0)
        A("All archives: the corrected filter is exactly the old population "
          "restricted to a positive current balance, pair for pair; "
          "`n_dropped_cur_zero` matches the observed difference; every "
          "removed pair carries a zero current balance; and the attribution "
          "in §4 reproduces the observed drop exactly, so its condition list "
          "has not drifted from `quiet_pairs`.\n")
        A(f"**The correction is live on {n_live} of {len(archs)} archives.** "
          "Where it is not, §4 is the whole content of this file.\n")

    A("\n## What this does not decide\n")
    A("- **It does not revisit whether the correction is right.** A balance "
      "going to zero is a termination and a termination is an event; that was "
      "ruled on 2026-08-16. This measures the size and the location of what "
      "the ruling removed, and on the real file that size is zero.")
    A("- **It does not license dropping the guard.** §4 names the condition "
      "doing the work; the guard costs one comparison and stops the class of "
      "pair the ruling excluded from ever entering by another route.")
    A("- **It does not re-report the four scripts.** Their outputs stand as "
      "re-run; this is the delta they owe.")
    A("- **It says nothing about the 46.65 per cent of below-mode months that "
      "remain unnamed** (O18). The correction touches the other side.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------


def selftest() -> int:
    """The fixture already carries head and tail zero-UPB rows, so the whole
    measurement runs on it end to end. **Built through the same versioned
    fixture path as ``b8_core``**, so a stale archive cannot make this pass
    vacuously either."""
    tag = K._fixture_tag()
    zp = K.SELFTEST_DIR / "raw" / f"2098Q1_{tag}.zip"
    cache_root = K.SELFTEST_DIR / "cache"
    if not zp.exists():
        K._synth(zp)
        print(f"  built fixture {zp.name}", file=sys.stderr)
    else:
        print(f"  reusing fixture {zp.name}", file=sys.stderr)
    K.build_archive(zp, force=True, cache_root=cache_root)

    fails = []
    c = K.Core(zp.stem, cache_root=cache_root)
    try:
        upb = c.row["upb"].astype(np.int64)
        q_old = K.quiet_pairs(c, require_cur_positive=False)
        q_new = K.quiet_pairs(c)
        keep = upb[q_old["cur"]] > 0
        drop = q_old["cur"].size - q_new["cur"].size
        if drop <= 0:
            fails.append("the fixture lost no pair, so this proves nothing")
        if not np.array_equal(q_old["cur"][keep], q_new["cur"]):
            fails.append("restriction does not reproduce the corrected call")
        if drop != q_new["n_dropped_cur_zero"]:
            fails.append("n_dropped_cur_zero does not match the difference")
        if int((upb[q_old["cur"][~keep]] != 0).sum()) != 0:
            fails.append("a dropped pair had a non-zero current balance")

        seg = K.segment_ids(q_old)
        (at, be, ab), mode, implied = _sides(q_old, seg)
        if at + be + ab != q_old["cur"].size:
            fails.append("the three sides do not partition the pairs")
        # a dropped pair hands over the whole balance, so on the synthetic
        # schedule it must land above its segment's cluster.
        _m, lo, hi, _n, _s, cnt, _i = K.segment_modes(q_old, seg)
        d_above = int((implied[~keep] > hi[~keep]).sum())
        # a dropped pair alone in its segment IS its segment's mode, so it
        # cannot sit above it. Every other one must, on a synthetic schedule
        # where the payment is exact.
        alone = int((cnt[seg][~keep] == 1).sum())
        if drop and d_above + alone < drop:
            fails.append(f"{drop - d_above - alone} dropped pairs neither sit "
                         f"above their cluster nor are alone in their "
                         f"segment, on a synthetic schedule where the payment "
                         f"is exact")
        if drop and alone == 0:
            fails.append("no dropped pair is alone in its segment, so the "
                         "singleton path is untested by this fixture")
        # **The attribution is a hand-written re-listing of the predicate and
        # can drift from it.** On the fixture the correction removes a real
        # number of pairs, so "passes every other condition" must reproduce
        # that number exactly. This is the only place the two are forced to
        # agree where the answer is not zero, and a zero on the real file
        # would hide any amount of drift.
        n_term, attr, only_cur = _attribute(c, upb)
        if only_cur != drop:
            fails.append(f"attribution says {only_cur} pairs pass every other "
                         f"condition, the correction removed {drop}. The "
                         f"condition list has drifted from quiet_pairs.")
        if n_term < drop:
            fails.append("fewer payoff pairs than removed pairs, impossible")
        print(f"  fixture: {q_old['cur'].size:,} old, {q_new['cur'].size:,} "
              f"new, {drop:,} removed, {d_above:,} above the cluster, "
              f"{alone:,} alone in their segment", file=sys.stderr)
        print(f"  attribution: {n_term:,} payoff pairs, {only_cur:,} pass "
              f"every other condition", file=sys.stderr)
    finally:
        c.close()

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok", file=sys.stderr)
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

    archs = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = measure(n)
        print(f"  {n}: {a.n_old:,} -> {a.n_new:,}, removed {a.n_drop:,} "
              f"({a.n_drop / a.n_old:.4f}), "
              f"{a.drop_side[2]:,} of them above the cluster", file=sys.stderr)
        for f in a.fails:
            print(f"  FAIL {n}: {f}", file=sys.stderr)
        archs.append(a)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report(archs), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}", file=sys.stderr)
    if any(a.fails for a in archs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
