#!/usr/bin/env python3
"""B8: the modification triangle, on the core table, reproducing C3/C4.

**This file is one chunk and it does one thing.** C9 counts triangle-completing
loans per ``(class x window)`` cell, and it cannot be written until the
population it counts is the same population C3/C4 counted. ``b8_field_audit.py``
found the triangles by a per-row state machine over the raw archives, before the
core table existed. Re-deriving them on the core table is a **second copy of a
predicate**, which is the defect ``b8_core.quiet_pairs`` exists to stop, so it
is written once here and **checked against the audit's published counts to the
unit** before anything is built on it.

The audit's test, transcribed from ``b8_field_audit.py`` ``flush()``::

    if s.mod_period:                                   # the loan was modified
        if s.seen_current and s.first_delinq and s.cured_after_mod:
            tri_mod[window_of(s.mod_period)] += 1

with the state updated **in this order within a row**: the deferred balance
first, the modification flag next, the delinquency status last. The order
matters: a row that turns the flag on and reads ``00`` counts as cured after
modification, not before it.

**Two transcription hazards, both counted rather than assumed away.**

1. ``delinq_of`` in the audit returns ``None`` for blank, for ``XX`` and for any
   non-digit, and ``int(v)`` otherwise, **including one-digit and three-digit
   strings**. ``b8_core.as_delinq`` deliberately sends a digit string of length
   other than two to 253 so that ``delinq == 0`` is exactly ``strip() == b"00"``.
   Where such a row exists the two disagree, so ``n_odd_delinq`` counts them.
2. ``cured_after_mod`` in the audit is set when the loan cures out of
   delinquency and **either** a modification **or** a deferred balance has
   already appeared. It is not a modification-only flag despite its name, and it
   is transcribed with the deferral arm intact.

Usage::

    python experiments/b8_triangles.py --selftest
    python experiments/b8_triangles.py verify        # reproduce C3/C4 or fail
    python experiments/b8_triangles.py              # write the census
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402

OUT = K.ROOT / "results" / "b8_triangles.md"

#: Transcribed from ``b8_field_audit.py`` WINDOWS, unchanged. The boundaries are
#: the modification-regime dates of `b8_fannie_slice.md` §6, not chosen here.
WINDOWS = [
    ("pre-crisis", 0, 200812), ("HAMP", 200901, 201612),
    ("Flex", 201701, 201912), ("COVID", 202001, 202212),
    ("post-2022", 202301, 999999),
]

#: ``b8_field_audit.py``'s own answer, per archive and window, from
#: ``results/b8_field_audit.md``. **This is the target, not a guide.** A
#: mismatch on any cell means one of the two implementations is wrong and
#: nothing may be built on either until it is resolved.
AUDIT_TOTAL_BY_WINDOW = {
    "pre-crisis": 3315, "HAMP": 33316, "Flex": 4655,
    "COVID": 7122, "post-2022": 2878,
}


#: window name to its index in ``WINDOWS``, so downstream code names a window
#: rather than hard-coding a position that a later insertion would shift.
WINDOWS_INDEX = {name: k for k, (name, _lo, _hi) in enumerate(WINDOWS)}


def _to_month_index(yyyymm: int) -> int:
    """A window bound in ``YYYYMM`` to the core table's month index.

    ``0`` and ``999999`` are the audit's open ends and are carried through as
    the extremes of the index rather than run through the date arithmetic.
    """
    if yyyymm <= 0:
        return -1
    if yyyymm >= 999999:
        return int(K.U16_NA)
    y, m = divmod(yyyymm, 100)
    return (y - K.EPOCH_YEAR) * 12 + (m - 1)


def _to_yyyymm(mi: np.ndarray) -> np.ndarray:
    """The inverse, for reporting only."""
    y, m = np.divmod(mi.astype(np.int64), 12)
    return (K.EPOCH_YEAR + y) * 100 + (m + 1)


def _last_pos_where(c: K.Core, mask: np.ndarray) -> np.ndarray:
    """Index of the most recent row of this loan, at or before each row, where
    ``mask`` holds. ``-1`` when there is none inside the loan.

    ``Core.cummax_within_loan`` answers the boolean form of this question and
    throws the position away. The position is what an ordering test needs, so it
    is kept here, with the same loan-boundary clamp so a run cannot leak from
    the previous loan.
    """
    idx = np.arange(c.n_rows, dtype=np.int64)
    last = np.maximum.accumulate(np.where(mask, idx, -1))
    start = np.repeat(c.row_start.astype(np.int64),
                      c.n_per_loan.astype(np.int64))
    return np.where(last >= start, last, -1)


def _first_pos_per_loan(c: K.Core, mask: np.ndarray) -> np.ndarray:
    """Per loan, the row index of its first row where ``mask`` holds, else -1.

    Computed by running the maximum backwards over the negated index, which is
    the same trick as ``_last_pos_where`` read from the other end, so the two
    cannot drift apart in their treatment of loan boundaries.
    """
    idx = np.arange(c.n_rows, dtype=np.int64)
    big = c.n_rows + 1
    rev = np.minimum.accumulate(np.where(mask, idx, big)[::-1])[::-1]
    end = np.repeat((c.row_start.astype(np.int64)
                     + c.n_per_loan.astype(np.int64)),
                    c.n_per_loan.astype(np.int64))
    first_in_loan = np.where(rev < end, rev, -1)
    return first_in_loan[c.row_start.astype(np.int64)]


def triangles(c: K.Core) -> dict:
    """Per loan: did it complete `current -> delinquent -> modified -> current`.

    Returns a dict of per-loan arrays plus the two hazard counts. Every array is
    one entry per loan, indexed the same way ``Core``'s loan columns are.
    """
    dv = c.row["delinq"]
    mf = c.row["mod_flag"]
    nib = c.row["nib_upb"].astype(np.int64)
    period = c.row["period"].astype(np.int32)

    # `d is not None` in the audit is "the field is a digit string". Two-digit
    # strings land on 0-98 here; 253 is the length-mismatch code and is exactly
    # the population where the two implementations can disagree.
    n_odd = int((dv == 253).sum())
    known = dv <= 98
    is_cur = known & (dv == 0)
    is_del = known & (dv != 0)
    is_mod = mf == K._Y
    is_nib = (nib != K.U32_NA) & (nib > 0)

    start = c.row_start.astype(np.int64)
    first_mod = _first_pos_per_loan(c, is_mod)
    first_del = _first_pos_per_loan(c, is_del)
    first_nib = _first_pos_per_loan(c, is_nib)
    first_cur = _first_pos_per_loan(c, is_cur)

    # seen_current: a performing row strictly before the first delinquent one.
    # The audit sets it inside `if d == 0: if not first_delinq`, and
    # first_delinq is set at the first delinquent row, so "before" is strict.
    never_del = first_del < 0
    seen_current = (first_cur >= 0) & (never_del | (first_cur < first_del))

    # in_delinq immediately before row r: the nearest known row before r was a
    # delinquent one. Positions rather than a boolean, because the test is an
    # ordering.
    prev = np.arange(c.n_rows, dtype=np.int64) - 1
    last_del = _last_pos_where(c, is_del)
    last_cur = _last_pos_where(c, is_cur)
    at_start = prev < np.repeat(start, c.n_per_loan.astype(np.int64))
    in_delinq_before = np.where(at_start, False,
                                last_del[np.maximum(prev, 0)]
                                > last_cur[np.maximum(prev, 0)])

    # the deferral arm is intact: the audit sets cured_after_mod when either a
    # modification or a deferred balance has already appeared.
    row_i = np.arange(c.n_rows, dtype=np.int64)
    fm = np.repeat(first_mod, c.n_per_loan.astype(np.int64))
    fn = np.repeat(first_nib, c.n_per_loan.astype(np.int64))
    started = ((fm >= 0) & (fm <= row_i)) | ((fn >= 0) & (fn <= row_i))
    cure_event = is_cur & in_delinq_before & started
    cured_after_mod = _first_pos_per_loan(c, cure_event) >= 0

    ever_mod = first_mod >= 0
    tri = ever_mod & seen_current & (first_del >= 0) & cured_after_mod

    # **The core table stores the period as a month index, not as YYYYMM.**
    # `b8_field_audit.py` compared YYYYMM integers against the window bounds
    # directly; here the bounds are converted once, in the same direction, so
    # the comparison is between the same units. A YYYYMM literal would silently
    # exceed the uint16 range and land every loan outside every window.
    mi = np.where(first_mod >= 0, period[np.maximum(first_mod, 0)], K.U16_NA)
    win = np.full(mi.size, -1, dtype=np.int8)
    known = (first_mod >= 0) & (mi != K.U16_NA)
    for k, (_name, lo, hi) in enumerate(WINDOWS):
        win = np.where(known & (win < 0)
                       & (mi >= _to_month_index(lo))
                       & (mi <= _to_month_index(hi)), k, win)
    mod_period = np.where(known, _to_yyyymm(mi), 0)

    return {
        "triangle": tri,
        "window": win,
        "mod_period": mod_period,
        "ever_mod": ever_mod,
        "seen_current": seen_current,
        "first_delinq": first_del >= 0,
        "cured_after_mod": cured_after_mod,
        "n_odd_delinq": n_odd,
    }


# ---------------------------------------------------------------------------


def _counts(t: dict) -> dict:
    out = {}
    for k, (name, _lo, _hi) in enumerate(WINDOWS):
        out[name] = int((t["triangle"] & (t["window"] == k)).sum())
    out["unclassified"] = int((t["triangle"] & (t["window"] < 0)).sum())
    return out


def cmd_verify(names: list[str]) -> int:
    total = {n: 0 for n, _, _ in WINDOWS}
    total["unclassified"] = 0
    odd = 0
    rows = []
    for n in names:
        with K.Core(n) as c:
            t = triangles(c)
        cnt = _counts(t)
        odd += t["n_odd_delinq"]
        for k, v in cnt.items():
            total[k] += v
        rows.append((n, cnt, int(t["triangle"].sum()),
                     int(t["ever_mod"].sum()), t["n_odd_delinq"]))
        print(f"  {n}: {int(t['triangle'].sum()):,} triangles, "
              f"{t['n_odd_delinq']:,} odd delinq codes", file=sys.stderr)

    fails = []
    for name, want in AUDIT_TOTAL_BY_WINDOW.items():
        got = total[name]
        if got != want:
            fails.append(f"{name}: core table says {got:,}, "
                         f"b8_field_audit.py said {want:,}, "
                         f"difference {got - want:+,}")
    if total["unclassified"]:
        fails.append(f"{total['unclassified']:,} triangles have a modification "
                     f"period outside every window")

    print(f"\n  {'window':12} {'core':>10} {'audit':>10} {'diff':>8}",
          file=sys.stderr)
    for name, want in AUDIT_TOTAL_BY_WINDOW.items():
        print(f"  {name:12} {total[name]:>10,} {want:>10,} "
              f"{total[name] - want:>+8,}", file=sys.stderr)
    print(f"  {'TOTAL':12} {sum(total.values()):>10,} "
          f"{sum(AUDIT_TOTAL_BY_WINDOW.values()):>10,} "
          f"{sum(total.values()) - sum(AUDIT_TOTAL_BY_WINDOW.values()):>+8,}",
          file=sys.stderr)
    if odd:
        print(f"\n  {odd:,} rows carry a digit delinquency status whose length "
              f"is not two. b8_core sends those to 253 and b8_field_audit.py "
              f"read them as integers, so they are where the two can differ.",
              file=sys.stderr)

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        print("\nThe core-table triangle is not the audit's triangle. "
              "**C9 must not be written on top of this until it is.**",
              file=sys.stderr)
        return 1
    print("\nverify: ok, the core table reproduces C3/C4 window for window",
          file=sys.stderr)
    return 0


def selftest() -> int:
    """A hand-built archive with one loan of each shape the test distinguishes.

    Each loan is written so that **exactly one clause** of the predicate decides
    it, so a transcription error in that clause shows up as one loan and not as
    a shifted total.
    """
    import hashlib
    import inspect
    import zipfile
    # **Key the name on THIS file's case table, not on b8_core's generator.**
    # HANDOFF_B8 §3 pit 19 is exactly this trap and it caught this file on its
    # first run: the fixture was named from `K._fixture_tag()`, the case table
    # here changed, the hash did not move, and the stale archive was reused.
    tag = hashlib.sha256(
        inspect.getsource(selftest).encode("utf-8")).hexdigest()[:8]
    zp = K.SELFTEST_DIR / "raw" / f"2097Q1_tri_{tag}.zip"
    cache_root = K.SELFTEST_DIR / "cache"

    # (label, [(delinq, modflag, nib, period)], expected triangle)
    P = 201701
    cases = [
        ("current then delinquent then modified then cured",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("60", "Y", "", P + 2), ("00", "Y", "", P + 3)], True),
        ("never current before the first delinquency",
         [("30", "N", "", P), ("60", "Y", "", P + 1),
          ("00", "Y", "", P + 2)], False),
        ("never delinquent",
         [("00", "N", "", P), ("00", "Y", "", P + 1),
          ("00", "Y", "", P + 2)], False),
        ("never modified",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("00", "N", "", P + 2)], False),
        ("modified but never cured after it",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("60", "Y", "", P + 2), ("90", "Y", "", P + 3)], False),
        ("cured before the modification, not after",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("00", "N", "", P + 2), ("00", "Y", "", P + 3)], False),
        ("cured after a deferral, then modified: the deferral arm",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("00", "N", "500.00", P + 2), ("00", "Y", "500.00", P + 3)], True),
        ("blank delinquency does not close a delinquency",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("", "Y", "", P + 2), ("00", "Y", "", P + 3)], True),
        ("XX does not read as current",
         [("00", "N", "", P), ("30", "N", "", P + 1),
          ("XX", "Y", "", P + 2), ("XX", "Y", "", P + 3)], False),
    ]

    if not zp.exists():
        zp.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for L, (_label, rows, _want) in enumerate(cases):
            lid = f"{910000000000 + L}"
            for dq, mod, nib, per in rows:
                f = [""] * K.NFIELDS
                f[1] = lid          # field 2, as b8_core._synth writes it
                f[2] = f"{per % 100:02d}{per // 100:04d}"
                f[3] = "R"
                f[8] = "4.500"
                f[11] = "200000.00"
                f[12] = "360"
                f[15] = "1"
                f[16] = "359"
                f[39] = dq
                f[41] = mod
                f[62] = nib
                lines.append("|".join(f))
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("f.csv", "\n".join(lines) + "\n")
        print(f"  built fixture {zp.name}", file=sys.stderr)
    else:
        print(f"  reusing fixture {zp.name}", file=sys.stderr)

    K.build_archive(zp, force=True, cache_root=cache_root)
    fails = []
    with K.Core(zp.stem, cache_root=cache_root) as c:
        t = triangles(c)
        got = t["triangle"]
        if got.size != len(cases):
            fails.append(f"{got.size} loans built, {len(cases)} expected")
        else:
            for (label, _rows, want), g in zip(cases, got.tolist()):
                if bool(g) != want:
                    fails.append(f"{label!r}: got {bool(g)}, expected {want}")
        win = t["window"]
        if got.size == len(cases) and int((win[got] != 2).sum()):
            fails.append("a fixture triangle did not land in the Flex window, "
                         "though every fixture modification is dated 2017")

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print(f"  {len(cases)} shapes, each decided by one clause", file=sys.stderr)
    print("selftest: ok", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", default="verify",
                    choices=["verify", "selftest"])
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest or args.command == "selftest":
        raise SystemExit(selftest())

    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()
                   and not p.name.startswith("209")) if root.exists() else []
    if args.only:
        keep = set(args.only)
        names = [n for n in names if n in keep]
    if not names:
        print("no core table. Run: python experiments/b8_core.py build",
              file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(cmd_verify(names))


if __name__ == "__main__":
    main()
