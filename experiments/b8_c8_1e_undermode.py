#!/usr/bin/env python3
"""B8 C8-1e: what are the months that pay LESS than the level payment?

Registered in the B8 inputs register §6.2.6. Reads the core table
built by ``b8_core.py``, so it costs seconds rather than a full parse.

**The question.** C8-1c(b) classified every quiet performing month against its
segment's modal payment and found the deviations are two-sided::

                     at mode    below mode    above mode
    2002Q1            0.7354      0.0884        0.1762
    2019Q1            0.7540      0.0893        0.1566

**Above the mode is understood**: the borrower paid more than the contractual
payment, the balance runs ahead of schedule, and the mechanism is curtailment.
**Below the mode is not.** In a month whose delinquency status reads ``00``, the
balance fell by less than one level payment would move it, and nothing in the
file says why.

**Why it matters more than the larger above-mode share.** A month that pays less
reads ``V > V-hat`` in §14.2's construction, which is the same sign and the same
shape as a missed payment. **It manufactures leg 1's signal with no event behind
it**, and leg 1 is one of the two terms in §14.3's race that B8-1 turns on. It
also breaks B8-0a(i): a clean cure whose performing months include under-payments
does not return to the contractual schedule, so the gate's arithmetic zero does
not close.

**This reads no prediction and terminates nothing.** It is a description of a
population, run so that the B8-0a(i) tolerance is ruled on with the mechanism
known rather than guessed.

The discriminators, chosen before looking:

  1. **Interest-only.** If the payment covered exactly the interest and no
     principal, ``implied / (balance * rate/12)`` sits at 1.00 and ``obs`` is 0.
     That is a product feature, not an anomaly, and it would mean the
     level-payment model simply does not apply to those months.
  2. **Run structure.** An interest-only period is a long contiguous run. A
     posting glitch is a singleton. The run-length distribution separates them
     without needing to name either.
  3. **Position.** First or last pair of a segment points at a transition
     artefact rather than at borrower behaviour.
  4. **Termination.** A zero balance code (44) at or next to the row points at
     payoff mechanics.
  5. **What happens next.** If under-payment months are followed by a rising
     delinquency status, they are the leading edge of a delinquency the status
     field has not caught up with, and that is a very different object from a
     product feature.
  6. **The contrast.** Every profile is printed for the above-mode months too.
     A shape that both share is a property of the estimator; a shape only the
     below-mode months have is a property of them.

  7. **The number the B8-0a(i) ruling needs.** Of loans that look like a clean
     cure (status leaves ``00`` and returns, the modification flag never turns
     ``Y``, no deferred balance ever), what share carry an under-payment month
     anywhere. That is the contamination rate of the gate's own sample and it
     sizes the "restrict to the schedule-obeying subsample" option directly.

Usage::

    python experiments/b8_c8_1e_undermode.py --selftest
    python experiments/b8_c8_1e_undermode.py --only 2002Q1 --only 2019Q1
    python experiments/b8_c8_1e_undermode.py

Writes ``results/b8_c8_1e_undermode.md``. Requires the core table::

    python experiments/b8_core.py build
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b8_c8_1e_undermode.md"

#: Run lengths are reported in these buckets. An interest-only period runs for
#: years; a posting artefact does not.
RUN_BUCKETS = [(1, 1), (2, 2), (3, 5), (6, 11), (12, 23), (24, 59), (60, 10**9)]

#: Interest-ratio bins for discriminator 1. 1.00 is interest-only.
IR_EDGES = [-0.001, 0.001, 0.25, 0.50, 0.75, 0.95, 0.999, 1.001, 1.5, 10.0]
IR_LABELS = ["0 exactly", "(0, 0.25]", "(0.25, 0.50]", "(0.50, 0.75]",
             "(0.75, 0.95]", "(0.95, 1.00)", "1.00 exactly", "(1.00, 1.5]",
             "> 1.5"]


def runs_of(flag: np.ndarray, group: np.ndarray) -> np.ndarray:
    """Length of the maximal run of ``True`` that each ``True`` entry sits in,
    where runs may not cross a change in ``group``."""
    if flag.size == 0:
        return np.zeros(0, dtype=np.int64)
    brk = np.empty(flag.size, dtype=bool)
    brk[0] = True
    brk[1:] = (flag[1:] != flag[:-1]) | (group[1:] != group[:-1])
    rid = np.cumsum(brk) - 1
    length = np.bincount(rid)
    return np.where(flag, length[rid], 0)


def bucketise(lengths: np.ndarray) -> list[int]:
    return [int(((lengths >= lo) & (lengths <= hi)).sum())
            for lo, hi in RUN_BUCKETS]


def pct(a, b) -> str:
    return f"{a / b:.4f}" if b else "-"


class Arch:
    """Everything C8-1e reports for one archive."""

    def __init__(self, name: str):
        self.name = name


def analyse(name: str) -> Arch:
    a = Arch(name)
    c = K.Core(name, cols=["period", "rate", "upb", "loan_age", "rem_legal",
                           "delinq", "mod_flag", "zero_bal", "nib_upb",
                           "assist"],
               loan_cols=["orig_term"])
    try:
        q = K.quiet_pairs(c)
        seg = K.segment_ids(q)
        mode, lo, hi, ncand, seg_start, seg_count, implied = \
            K.segment_modes(q, seg)

        cur = q["cur"]
        p_upb = q["p_upb_cents"].astype(np.float64) / 100.0
        obs = q["obs_cents"].astype(np.float64) / 100.0
        i = q["rate_milli"].astype(np.float64) / 1000.0 / 1200.0
        interest = p_upb * i

        below = implied < lo
        above = implied > hi
        at = ~below & ~above
        a.n = implied.size
        a.n_at, a.n_below, a.n_above = int(at.sum()), int(below.sum()), \
            int(above.sum())
        a.n_seg = int(seg_count.size)

        # 1. interest-only test
        with np.errstate(divide="ignore", invalid="ignore"):
            ir = np.where(interest > 0, implied / interest, np.nan)
        a.ir_below = np.histogram(ir[below], bins=IR_EDGES)[0].tolist()
        a.ir_above = np.histogram(ir[above], bins=IR_EDGES)[0].tolist()
        a.obs_zero_below = int((obs[below] == 0).sum())
        a.obs_zero_above = int((obs[above] == 0).sum())
        a.obs_neg_below = int((obs[below] < 0).sum())

        # shortfall size, as a share of the modal payment
        short = (mode - implied) / np.where(mode > 0, mode, np.nan)
        a.short_q = np.nanpercentile(short[below], [10, 25, 50, 75, 90]).tolist()
        excess = (implied - mode) / np.where(mode > 0, mode, np.nan)
        a.excess_q = np.nanpercentile(excess[above],
                                      [10, 25, 50, 75, 90]).tolist()

        # 2. run structure, within a segment
        a.run_below = bucketise(runs_of(below, seg)[below])
        a.run_above = bucketise(runs_of(above, seg)[above])

        # 3. position in the segment
        pos = np.arange(implied.size) - np.repeat(seg_start, seg_count)
        last = np.repeat(seg_count, seg_count) - 1
        a.first_below = int((below & (pos == 0)).sum())
        a.last_below = int((below & (pos == last)).sum())
        a.first_above = int((above & (pos == 0)).sum())
        a.last_above = int((above & (pos == last)).sum())

        # 4. termination and assistance, on the current row of the pair
        zb = c.row["zero_bal"][:]
        assist = c.row["assist"][:]
        zb_cur = zb[cur]
        as_cur = assist[cur]
        a.zb_below = int((zb_cur[below] != K.U8_NA).sum())
        a.zb_above = int((zb_cur[above] != K.U8_NA).sum())
        a.assist_below = int((as_cur[below] != K.U8_NA).sum())
        a.assist_above = int((as_cur[above] != K.U8_NA).sum())

        # 5. what happens next: delinquency on the row after the pair
        dq = c.row["delinq"][:]
        loan_row = c.loan_of_row()
        nxt = np.minimum(cur + 1, c.n_rows - 1)
        same = loan_row[nxt] == loan_row[cur]
        dq_next = np.where(same, dq[nxt], K.U8_NA)
        a.next_delinq_below = int(((dq_next[below] > 0)
                                   & (dq_next[below] < 253)).sum())
        a.next_delinq_above = int(((dq_next[above] > 0)
                                   & (dq_next[above] < 253)).sum())
        a.next_known_below = int((dq_next[below] != K.U8_NA).sum())
        a.next_known_above = int((dq_next[above] != K.U8_NA).sum())

        # 6. loan age and original term
        age = c.row["loan_age"][:][cur].astype(np.float64)
        age[age == K.U16_NA] = np.nan
        a.age_below = np.nanpercentile(age[below], [10, 50, 90]).tolist()
        a.age_above = np.nanpercentile(age[above], [10, 50, 90]).tolist()
        a.age_all = np.nanpercentile(age, [10, 50, 90]).tolist()

        # concentration: how many loans carry any below-mode month
        lo_of_pair = q["loan"]
        a.n_loans_quiet = int(np.unique(lo_of_pair).size)
        a.n_loans_below = int(np.unique(lo_of_pair[below]).size)
        a.n_loans_above = int(np.unique(lo_of_pair[above]).size)

        # 7. the number the B8-0a(i) ruling needs
        starts = c.row_start.astype(np.int64)
        counts = c.n_per_loan.astype(np.int64)
        dq_ok = (dq > 0) & (dq < 253)
        modY = c.row["mod_flag"][:] == ord("Y")
        nibpos = (c.row["nib_upb"][:] != K.U32_NA) & (c.row["nib_upb"][:] > 0)
        ever_delinq = np.add.reduceat(dq_ok.astype(np.int64), starts) > 0
        ever_mod = np.add.reduceat(modY.astype(np.int64), starts) > 0
        ever_nib = np.add.reduceat(nibpos.astype(np.int64), starts) > 0
        ends_clean = dq[starts + counts - 1] == 0
        clean_cure = ever_delinq & ~ever_mod & ~ever_nib & ends_clean
        a.n_clean_cure = int(clean_cure.sum())

        has_below = np.zeros(c.n_loans, dtype=bool)
        has_below[np.unique(lo_of_pair[below])] = True
        has_above = np.zeros(c.n_loans, dtype=bool)
        has_above[np.unique(lo_of_pair[above])] = True
        has_quiet = np.zeros(c.n_loans, dtype=bool)
        has_quiet[np.unique(lo_of_pair)] = True
        a.cc_with_quiet = int((clean_cure & has_quiet).sum())
        a.cc_below = int((clean_cure & has_below).sum())
        a.cc_above = int((clean_cure & has_above).sum())
        a.cc_clean = int((clean_cure & has_quiet & ~has_below
                          & ~has_above).sum())
    finally:
        c.close()
    return a


def render(archs: list[Arch]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8 C8-1e: what are the months that pay less than the level payment?\n")
    A("Generated by `experiments/b8_c8_1e_undermode.py` from the core table. "
      "Registered in the B8 inputs register §6.2.6.\n")
    A("**No prediction is read here and no outcome terminates the stage.**\n")

    A("\n## 0. Reproduction of C8-1c(b) §1\n")
    A("Same quiet-month filter, same modal-cluster estimator. **These three "
      "rates must match `results/b8_c8_1c_contract_payment_b.md` §1.** They do "
      "not, and everything below is about a different population.\n")
    A("| archive | quiet months | segments | at mode | below | above |")
    A("|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.n:,} | {a.n_seg:,} | {pct(a.n_at, a.n)} | "
          f"**{pct(a.n_below, a.n)}** | {pct(a.n_above, a.n)} |")

    A("\n## 1. Is it interest-only\n")
    A("`implied payment / (previous balance * rate / 12)`. **At 1.00 exactly "
      "the payment covered the interest and no principal**, which is a product "
      "feature and means the level-payment model does not apply to those "
      "months. At 0 nothing was paid at all.\n")
    A("| archive | side | " + " | ".join(IR_LABELS) + " |")
    A("|---|---|" + "---|" * len(IR_LABELS))
    for a in archs:
        A(f"| {a.name} | below | " + " | ".join(f"{v:,}" for v in a.ir_below)
          + " |")
        A(f"| {a.name} | above | " + " | ".join(f"{v:,}" for v in a.ir_above)
          + " |")

    A("\n| archive | below, balance did not move | rate | below, balance rose "
      "| above, balance did not move |")
    A("|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.obs_zero_below:,} | "
          f"{pct(a.obs_zero_below, a.n_below)} | {a.obs_neg_below:,} | "
          f"{a.obs_zero_above:,} |")

    A("\n**How far off.** Shortfall is `(mode - implied) / mode` on below "
      "months, excess is `(implied - mode) / mode` on above months.\n")
    A("| archive | side | p10 | p25 | p50 | p75 | p90 |")
    A("|---|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | shortfall | "
          + " | ".join(f"{v:.3f}" for v in a.short_q) + " |")
        A(f"| {a.name} | excess | "
          + " | ".join(f"{v:.3f}" for v in a.excess_q) + " |")

    A("\n## 2. Run structure inside a segment\n")
    A("**A period runs for years. An artefact is a singleton.** Counts are of "
      "months, bucketed by the length of the run each month sits in.\n")
    hdr = ["1", "2", "3-5", "6-11", "12-23", "24-59", "60+"]
    A("| archive | side | " + " | ".join(hdr) + " |")
    A("|---|---|" + "---|" * len(hdr))
    for a in archs:
        A(f"| {a.name} | below | " + " | ".join(f"{v:,}" for v in a.run_below)
          + " |")
        A(f"| {a.name} | above | " + " | ".join(f"{v:,}" for v in a.run_above)
          + " |")

    A("\n## 3. Position, termination, assistance, and what happens next\n")
    A("| archive | side | first pair of segment | last pair | zero balance "
      "code set | assistance plan set | next row delinquent | of known |")
    A("|---|---|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | below | {a.first_below:,} | {a.last_below:,} | "
          f"{a.zb_below:,} | {a.assist_below:,} | {a.next_delinq_below:,} | "
          f"{pct(a.next_delinq_below, a.next_known_below)} |")
        A(f"| {a.name} | above | {a.first_above:,} | {a.last_above:,} | "
          f"{a.zb_above:,} | {a.assist_above:,} | {a.next_delinq_above:,} | "
          f"{pct(a.next_delinq_above, a.next_known_above)} |")

    A("\n## 4. Loan age, and how concentrated it is\n")
    A("| archive | side | age p10 | p50 | p90 | loans carrying any | of loans "
      "with a quiet month |")
    A("|---|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | all quiet | " + " | ".join(f"{v:.0f}" for v in a.age_all)
          + f" | {a.n_loans_quiet:,} | 1.0000 |")
        A(f"| {a.name} | below | " + " | ".join(f"{v:.0f}" for v in a.age_below)
          + f" | {a.n_loans_below:,} | {pct(a.n_loans_below, a.n_loans_quiet)} |")
        A(f"| {a.name} | above | " + " | ".join(f"{v:.0f}" for v in a.age_above)
          + f" | {a.n_loans_above:,} | {pct(a.n_loans_above, a.n_loans_quiet)} |")

    A("\n## 5. The number the B8-0a(i) ruling needs\n")
    A("A loan counts as **clean-cure shaped** when its delinquency status "
      "leaves `00` at least once, the modification flag never turns `Y`, no "
      "deferred balance ever appears, and it is performing on its last row. "
      "**This is a loan-level proxy for C5's population, not C5's own count**, "
      "which was taken per episode with a different script.\n")
    A("| archive | clean-cure shaped | with a quiet month | carrying a below "
      "month | rate | carrying an above month | rate | **entirely at mode** | "
      "rate |")
    A("|---|---|---|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.n_clean_cure:,} | {a.cc_with_quiet:,} | "
          f"{a.cc_below:,} | {pct(a.cc_below, a.cc_with_quiet)} | "
          f"{a.cc_above:,} | {pct(a.cc_above, a.cc_with_quiet)} | "
          f"**{a.cc_clean:,}** | **{pct(a.cc_clean, a.cc_with_quiet)}** |")

    A("\n**The last column sizes the option that restricts B8-0a(i) to the "
      "schedule-obeying subsample.** It is the count on which the gate's "
      "arithmetic zero can still be required to floating-point tolerance.\n")

    A("\n## What this does not decide\n")
    A("- **It does not name the mechanism.** It measures shape: whether the "
      "under-payments are a period or a singleton, whether they cover exactly "
      "the interest, where they sit, and what follows them. Naming needs a "
      "field the file may not carry, and C0b's caveat governs.")
    A("- **It does not decide the B8-0a(i) tolerance.** It supplies the counts "
      "that ruling needs.")
    A("- **The quiet-month filter was corrected on 2026-08-16 and this run "
      "is under the corrected one.** It still does not read field 44 as an "
      "exclusion, and §3's zero-balance-code column is still zero on every "
      "archive, but **payoff months no longer remain in the sample**: a pair "
      "whose later row reports a zero balance is a termination and is now "
      "excluded. The size and the location of what that removed is measured "
      "in `results/b8_quiet_delta.md`, not here. **The earlier text on this "
      "line said the filter was unchanged and that payoff months remained; "
      "both were true before that date and false after it.**")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def selftest() -> int:
    """Pure-function checks on the two fiddly helpers."""
    fails = []

    g = np.array([0, 0, 0, 0, 1, 1, 1])
    f = np.array([True, True, False, True, True, True, False])
    got = runs_of(f, g).tolist()
    want = [2, 2, 0, 1, 2, 2, 0]      # the run at index 3 stops at the group edge
    if got != want:
        fails.append(f"runs_of {got} want {want}")

    f2 = np.zeros(0, dtype=bool)
    if runs_of(f2, f2.astype(np.int64)).size != 0:
        fails.append("runs_of on an empty input")

    if bucketise(np.array([1, 1, 2, 4, 30, 200])) != [2, 1, 1, 0, 0, 1, 1]:
        fails.append(f"bucketise {bucketise(np.array([1, 1, 2, 4, 30, 200]))}")

    # the modal cluster must survive a minority of interest-only months, which
    # is the population this stage exists to look at
    P, B, i = 1264.14, 200000.0, 6.5 / 1200.0
    implied = [P] * 40 + [B * i] * 8
    mode, lo, hi, nc = K.modal_cluster(implied)
    if abs(mode - P) > 1e-9:
        fails.append(f"modal_cluster with 8 interest-only months: {mode:.4f}")
    if sum(1 for v in implied if v < lo) != 8:
        fails.append("interest-only months did not land below the cluster")

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
        archs.append(analyse(n))
        print(f"  done {n}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(archs))
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
