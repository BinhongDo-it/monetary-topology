"""Is this loan population indexed? Count the object, because there is no label.

The loop residual on this carrier is built from the loan's own note rate and its
own contract payment, and the balance advances by `b -> b(1+i) - P`. Nothing is
marked to the world at any step, so the traversal may span months and admit no
common environmental drift: the object is closed and the balance has to
reconcile. That argument fails on exactly one subset, an instrument whose own
rate is indexed, because there the environment is written into the contract.

The cache carries no product field, so the subset cannot be read off a label. It
is measured instead: **a note rate that moves at a row which is not a
modification onset is the signature of an indexed contract.** Blanks are filled
within the loan first, because the core stores a missing field as a sentinel and
comparing it to its neighbours fires two spurious breaks.

    python experiments/b8_indexed_rate_count.py 2002Q1
"""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "experiments"))
import numpy as np
import b8_core as K
import b8_omega as O

ARCH = sys.argv[1] if len(sys.argv) > 1 else "2002Q1"
with K.Core(ARCH, cols=["rate", "mod_flag", "nib_upb", "period"]) as c:
    start, end = O._row_bounds(c)
    rate = c.row["rate"][:].astype(np.int64)
    na = int(np.max(rate))                    # report what the sentinel looks like
    print(f"archive {ARCH}: {c.n_rows:,} rows, {len(c.n_per_loan):,} loans")
    print(f"  rate: min {rate.min()}  max {rate.max()}  "
          f"n at U16_NA {int((rate == K.U16_NA).sum()):,}")
    filled = O.fill_within_loan(rate.copy(), K.U16_NA, start, end)
    filled = np.asarray(filled).astype(np.int64)
    mf = c.row["mod_flag"][:]
    nib = c.row["nib_upb"][:].astype(np.int64)
    mod_on = (mf == K._Y) | ((nib != K.U32_NA) & (nib > 0))

    idx = np.arange(c.n_rows, dtype=np.int64)
    not_first = idx > start                    # has a predecessor in the same loan
    known = (filled != K.U16_NA)
    prev_known = np.zeros(c.n_rows, dtype=bool)
    prev_known[1:] = known[:-1]
    changed = np.zeros(c.n_rows, dtype=bool)
    changed[1:] = filled[1:] != filled[:-1]
    changed &= not_first & known & prev_known

    # a change is "at a modification" if this row or either neighbour is an onset
    near_mod = mod_on.copy()
    near_mod[1:] |= mod_on[:-1]
    near_mod[:-1] |= mod_on[1:]

    n_chg = int(changed.sum())
    n_at = int((changed & near_mod).sum())
    n_away = n_chg - n_at
    loans_away = len(np.unique(np.searchsorted(c.row_start, idx[changed & ~near_mod],
                                               side="right") - 1))
    print(f"  note-rate changes after filling: {n_chg:,}")
    print(f"    at or beside a modification onset : {n_at:,}  ({n_at/max(n_chg,1):.4f})")
    print(f"    AWAY from any modification onset  : {n_away:,}  ({n_away/max(n_chg,1):.4f})")
    print(f"    loans carrying an away-change     : {loans_away:,} "
          f"of {len(c.n_per_loan):,}  ({loans_away/len(c.n_per_loan):.6f})")
