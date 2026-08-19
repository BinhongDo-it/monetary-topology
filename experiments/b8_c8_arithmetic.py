#!/usr/bin/env python3
"""B8 C8: the six arithmetic questions that must be settled before ``omega``.

Registered in the B8 inputs register §6 and specified in
``docs/b8_fannie_slice.md`` §14.8.

**None of these is a prediction and none of them can terminate the stage.** Every
outcome is a construction choice for ``omega``; the point of asking first is that
the choice is made against the file rather than against the result.

C8-1  does field 12 include field 63, or exclude it
C8-2  is field 64 a period amount or a cumulative one
C8-3  is field 63 a balance or a cumulative deferral
C8-4  at the modification month, does field 12 step up by the capitalised arrears
C8-5  do 17 and 19 agree, on the modification months specifically
C8-6  do 107 and 108 describe the deferral, and does 108 track the change in 63

**C8-1 is decided by an amortisation test and not by eyeballing a level.** For a
modified loan in a month where nothing happens, the fall in field 12 must equal the
scheduled principal payment of an amortising loan at rate (9) over (17) months on
*some* balance. Computing it both ways, once on ``12`` and once on ``12 - 63``, and
asking which ratio sits at 1.0, answers the question with the same arithmetic
``omega`` is going to use anyway.

**The control is the load-bearing part of C8-1.** The same test is run on loans that
carry no deferred balance at all, where the two hypotheses coincide. If that control
does not sit at 1.0, the amortisation model is wrong and **C8-1's discrimination
means nothing**; the test reports the control first for exactly that reason.

Design follows ``b8_field_audit.py``: one streaming pass per archive, a per-loan
state machine, constant memory, no sort. C0b established that each loan's rows are
one contiguous block, which is what makes that legal.

Usage::

    python experiments/b8_c8_arithmetic.py --only 2019Q1 --limit 2000000
    python experiments/b8_c8_arithmetic.py

Writes ``results/b8_c8_arithmetic.md``. Deterministic; progress to stderr only.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Fannie"
OUT = ROOT / "results" / "b8_c8_arithmetic.md"

DELIM = b"|"
NFIELDS = 113

F_LOAN, F_PERIOD = 2, 3
F_RATE, F_UPB = 9, 12
F_REM_LEGAL, F_MATDATE = 17, 19
F_DELINQ, F_MODFLAG = 40, 42
F_MODNIBUPB, F_FORGIVE = 63, 64
F_ADR, F_ADRCOUNT, F_DEFERAMT = 106, 107, 108

ADR_REAL = {b"P", b"C", b"D"}

#: Ratio histograms are binned rather than stored, so memory stays constant no
#: matter how many loans qualify. 0.01 wide, clipped into [-1, 3].
RBIN, RLO, RHI = 0.01, -1.0, 3.0


def rbin(x: float) -> int:
    return int(round(min(max(x, RLO), RHI) / RBIN))


def rmid(b: int) -> float:
    return b * RBIN


def quantiles(c: Counter, qs=(0.10, 0.25, 0.50, 0.75, 0.90)) -> list[float]:
    n = sum(c.values())
    if not n:
        return [float("nan")] * len(qs)
    keys = sorted(c)
    out, run, i = [], 0, 0
    for q in qs:
        target = q * n
        while i < len(keys) and run + c[keys[i]] < target:
            run += c[keys[i]]
            i += 1
        out.append(rmid(keys[min(i, len(keys) - 1)]))
    return out


def to_period(v: bytes) -> int:
    return int(v[2:]) * 100 + int(v[:2]) if len(v) == 6 and v.isdigit() else 0


def months_between(a: int, b: int) -> int:
    if not a or not b:
        return 0
    return (a // 100 - b // 100) * 12 + (a % 100 - b % 100)


def num(v: bytes):
    v = v.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def sched_principal(balance: float, rate_pct: float, n: int):
    """One month of scheduled principal on a level-payment amortising loan.

    This is exactly the drift that §14.2's ``V-hat`` carries forward, so a wrong
    answer here is a wrong ``omega`` and not only a wrong C8.
    """
    if balance is None or rate_pct is None or not n or n <= 0 or balance <= 0:
        return None
    i = rate_pct / 1200.0
    if i <= 0:
        return balance / n
    try:
        factor = (1.0 + i) ** (-n)
    except OverflowError:
        return None
    if factor >= 1.0:
        return None
    pmt = balance * i / (1.0 - factor)
    return pmt - balance * i


class LoanState:
    __slots__ = ("prev", "nrows", "nib_first_period", "nib_prev", "nib_ever",
                 "nib_decreased", "nib_last_row", "nib_distinct",
                 "fg_prev", "fg_ever", "fg_decreased", "fg_rows", "fg_distinct",
                 "mod_seen", "adr_code", "adr_count", "defer_amt",
                 "nib_at_defer", "defer_row")

    def __init__(self):
        self.prev = None            # the whole previous row, parsed to a tuple
        self.nrows = 0
        self.nib_first_period = 0
        self.nib_prev = None
        self.nib_ever = False
        self.nib_decreased = False
        self.nib_last_row = 0
        self.nib_distinct = set()
        self.fg_prev = None
        self.fg_ever = False
        self.fg_decreased = False
        self.fg_rows = 0
        self.fg_distinct = set()
        self.mod_seen = False
        self.adr_code = b""
        self.adr_count = None
        self.defer_amt = None
        self.nib_at_defer = None
        self.defer_row = 0


class Tally:
    def __init__(self, name: str):
        self.name = name
        self.rows = 0
        self.loans = 0

        # C8-1
        self.amort_ctrl = Counter()          # loans with no deferred balance
        self.amort_incl = Counter()          # ratio assuming 12 INCLUDES 63
        self.amort_excl = Counter()          # ratio assuming 12 EXCLUDES 63
        self.amort_ctrl_n = 0
        self.amort_nib_n = 0
        self.nib_gt_upb = 0                  # a level check, reported beside it
        self.nib_le_upb = 0
        self.onset_drop = Counter()          # (UPB_prev - UPB_at) / NIB_at
        self.onset_n = 0

        # C8-2
        self.fg_loans = 0
        self.fg_multi = 0
        self.fg_nondecreasing = 0
        self.fg_decreased = 0
        self.fg_distinct_hist = Counter()

        # C8-3
        self.nib_loans = 0
        self.nib_decreased = 0
        self.nib_blank_while_alive = 0
        self.nib_distinct_hist = Counter()

        # C8-4
        self.mod_step = Counter()            # (UPB_at - UPB_prev) / UPB_prev
        self.mod_step_n = 0
        self.mod_step_up = 0
        self.mod_step_down = 0
        self.mod_step_flat = 0

        # C8-5
        self.c5_rows = 0
        self.c5_exact = 0
        self.c5_diff = Counter()

        # C8-6
        self.adr_loans = 0
        self.adr_count_vals = Counter()
        self.adr_amt_missing = 0
        self.adr_amt_present = 0
        self.defer_vs_nib = Counter()        # 108 / 63
        self.defer_vs_nib_n = 0


def scan(path: Path, t: Tally, limit_rows: int) -> None:
    st = LoanState()
    cur_id = None

    def flush(s: LoanState) -> None:
        if cur_id is None:
            return
        t.loans += 1
        if s.nib_ever:
            t.nib_loans += 1
            if s.nib_decreased:
                t.nib_decreased += 1
            if s.nib_last_row < s.nrows:
                t.nib_blank_while_alive += 1
            t.nib_distinct_hist[min(len(s.nib_distinct), 10)] += 1
        if s.fg_ever:
            t.fg_loans += 1
            if s.fg_rows >= 2:
                t.fg_multi += 1
                if not s.fg_decreased:
                    t.fg_nondecreasing += 1
                else:
                    t.fg_decreased += 1
            t.fg_distinct_hist[min(len(s.fg_distinct), 10)] += 1
        if s.adr_code in ADR_REAL:
            t.adr_loans += 1
            t.adr_count_vals[
                (s.adr_count if s.adr_count is not None else "(blank)")] += 1
            if s.defer_amt is None:
                t.adr_amt_missing += 1
            else:
                t.adr_amt_present += 1
                if s.nib_at_defer:
                    t.defer_vs_nib[rbin(s.defer_amt / s.nib_at_defer)] += 1
                    t.defer_vs_nib_n += 1

    with zipfile.ZipFile(path) as zf:
        member = sorted(zf.namelist())[0]
        with zf.open(member) as fh:
            for line in fh:
                if limit_rows and t.rows >= limit_rows:
                    break
                line = line.rstrip(b"\r\n")
                if not line:
                    continue
                p = line.split(DELIM)
                if len(p) != NFIELDS:
                    continue
                t.rows += 1
                if t.rows % 5_000_000 == 0:
                    print(f"  {path.name}: {t.rows:,} rows", file=sys.stderr)

                lid = p[F_LOAN - 1]
                if lid != cur_id:
                    flush(st)
                    st = LoanState()
                    cur_id = lid
                st.nrows += 1

                period = to_period(p[F_PERIOD - 1])
                rate = num(p[F_RATE - 1])
                upb = num(p[F_UPB - 1])
                rem = num(p[F_REM_LEGAL - 1])
                rem = int(rem) if rem is not None else None
                matd = to_period(p[F_MATDATE - 1])
                delinq = p[F_DELINQ - 1].strip()
                mod = p[F_MODFLAG - 1].strip() == b"Y"
                nib = num(p[F_MODNIBUPB - 1])
                fg = num(p[F_FORGIVE - 1])
                adr = p[F_ADR - 1].strip()

                # ---------------- C8-5, on modification months ----------------
                if mod and rem is not None and matd and period:
                    t.c5_rows += 1
                    d = months_between(matd, period) - rem
                    if d == 0:
                        t.c5_exact += 1
                    t.c5_diff[min(max(d, -6), 6)] += 1

                # ---------------- C8-3 bookkeeping ----------------
                if nib is not None and nib > 0:
                    if not st.nib_ever:
                        st.nib_first_period = period
                    st.nib_ever = True
                    st.nib_last_row = st.nrows
                    st.nib_distinct.add(round(nib, 2))
                    if st.nib_prev is not None and nib < st.nib_prev - 0.005:
                        st.nib_decreased = True
                    st.nib_prev = nib

                # ---------------- C8-2 bookkeeping ----------------
                if fg is not None and fg > 0:
                    st.fg_ever = True
                    st.fg_rows += 1
                    st.fg_distinct.add(round(fg, 2))
                    if st.fg_prev is not None and fg < st.fg_prev - 0.005:
                        st.fg_decreased = True
                    st.fg_prev = fg

                # ---------------- C8-6 bookkeeping ----------------
                if adr in ADR_REAL and not st.adr_code:
                    st.adr_code = adr
                    st.adr_count = p[F_ADRCOUNT - 1].strip().decode("latin-1") \
                        or None
                    st.defer_amt = num(p[F_DEFERAMT - 1])
                    st.nib_at_defer = nib if nib and nib > 0 else st.nib_prev
                    st.defer_row = st.nrows

                prev = st.prev
                if prev is not None:
                    (p_period, p_rate, p_upb, p_rem, p_delinq, p_mod,
                     p_nib) = prev
                    consecutive = months_between(period, p_period) == 1

                    # ------------- C8-4: the step at the modification -------
                    if mod and not p_mod and consecutive and p_upb and upb \
                            is not None and p_upb > 0:
                        r = (upb - p_upb) / p_upb
                        t.mod_step[rbin(r)] += 1
                        t.mod_step_n += 1
                        if r > 0.001:
                            t.mod_step_up += 1
                        elif r < -0.001:
                            t.mod_step_down += 1
                        else:
                            t.mod_step_flat += 1

                    # ------------- C8-1a: the onset drop --------------------
                    if consecutive and p_nib in (None, 0.0) and nib and \
                            nib > 0 and p_upb and upb is not None:
                        t.onset_drop[rbin((p_upb - upb) / nib)] += 1
                        t.onset_n += 1

                    # ------------- C8-1b: the amortisation test -------------
                    # Quiet months only: performing, no flag change, the term
                    # decrements by one, the rate is unchanged.
                    quiet = (consecutive and delinq == b"00" and
                             p_delinq == b"00" and mod == p_mod and
                             rem is not None and p_rem is not None and
                             p_rem - rem == 1 and rate is not None and
                             p_rate is not None and abs(rate - p_rate) < 1e-9
                             and p_upb and upb is not None and p_upb > 0)
                    if quiet:
                        obs = p_upb - upb
                        if p_nib and p_nib > 0:
                            s_ex = sched_principal(p_upb, p_rate, p_rem)
                            s_in = sched_principal(p_upb - p_nib, p_rate, p_rem)
                            if s_ex and s_ex > 0:
                                t.amort_excl[rbin(obs / s_ex)] += 1
                            if s_in and s_in > 0:
                                t.amort_incl[rbin(obs / s_in)] += 1
                                t.amort_nib_n += 1
                            if nib is not None:
                                if nib > upb:
                                    t.nib_gt_upb += 1
                                else:
                                    t.nib_le_upb += 1
                        elif not st.nib_ever:
                            s_c = sched_principal(p_upb, p_rate, p_rem)
                            if s_c and s_c > 0:
                                t.amort_ctrl[rbin(obs / s_c)] += 1
                                t.amort_ctrl_n += 1

                st.prev = (period, rate, upb, rem, delinq, mod, nib)
                if mod:
                    st.mod_seen = True

    flush(st)


def qline(c: Counter) -> str:
    q = quantiles(c)
    return " | ".join(f"{v:.2f}" for v in q)


def render(tallies: list[Tally]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8 C8: the arithmetic behind `omega`\n")
    A("Generated by `experiments/b8_c8_arithmetic.py`. "
      "Registered in the B8 inputs register §6 and specified in "
      "`docs/b8_fannie_slice.md` §14.8.\n")
    A("**No prediction is read here and no outcome terminates the stage.**\n")

    A("\n## Scanned\n")
    A("| archive | rows | loans |")
    A("|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.rows:,} | {t.loans:,} |")

    A("\n## C8-1a The control, which decides whether C8-1b means anything\n")
    A("Quiet performing months in which **no** deferred balance is present and "
      "none has been seen yet on that loan, so the two hypotheses coincide. "
      "Ratio of the observed fall in field 12 to the scheduled principal "
      "payment computed from `(9, 12, 17)`. **If this is not at 1.00 the "
      "amortisation model is wrong and nothing below is readable, C8-1b "
      "included.**\n")
    A("A quiet month is: consecutive reporting periods, delinquency status "
      "`00` on both, no change in field 42, field 17 down by exactly one, "
      "field 9 unchanged.\n")
    A("| archive | n | p10 | p25 | median | p75 | p90 |")
    A("|---|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.amort_ctrl_n:,} | {qline(t.amort_ctrl)} |")

    A("\n## C8-1b Does field 12 include field 63\n")
    A("Same test on quiet months of loans that **do** carry a deferred "
      "balance, computed both ways. The hypothesis whose median sits at 1.00 "
      "is the one the file uses.\n")
    A("| archive | n | hypothesis | p10 | p25 | median | p75 | p90 |")
    A("|---|---|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.amort_nib_n:,} | 12 **includes** 63, "
          f"balance = 12 - 63 | {qline(t.amort_incl)} |")
        A(f"| {t.name} | {t.amort_nib_n:,} | 12 **excludes** 63, "
          f"balance = 12 | {qline(t.amort_excl)} |")

    A("\nTwo checks beside it. The onset drop is "
      "`(UPB before - UPB at) / NIB at` in the month the deferred balance "
      "first appears: **at 1.00 field 12 excludes 63, at 0.00 it includes "
      "it.** The level check counts rows where the deferred balance exceeds "
      "the reported UPB, which cannot happen if 12 includes 63.\n")
    A("| archive | onset n | p25 | median | p75 | NIB > UPB | NIB <= UPB |")
    A("|---|---|---|---|---|---|---|")
    for t in tallies:
        q = quantiles(t.onset_drop, (0.25, 0.50, 0.75))
        A(f"| {t.name} | {t.onset_n:,} | {q[0]:.2f} | {q[1]:.2f} | "
          f"{q[2]:.2f} | {t.nib_gt_upb:,} | {t.nib_le_upb:,} |")

    A("\n## C8-2 Is field 64 a period amount or a cumulative one\n")
    A("A cumulative field repeats or grows and never falls. A period amount "
      "appears on one row. **Subtracting a cumulative field every month "
      "forgives the same principal repeatedly.**\n")
    A("| archive | loans with 64 > 0 | on 2+ rows | of those, "
      "non-decreasing | of those, ever falls | median distinct values |")
    A("|---|---|---|---|---|---|")
    for t in tallies:
        med = "-"
        if t.fg_distinct_hist:
            n = sum(t.fg_distinct_hist.values())
            run = 0
            for k in sorted(t.fg_distinct_hist):
                run += t.fg_distinct_hist[k]
                if run >= n / 2:
                    med = str(k)
                    break
        A(f"| {t.name} | {t.fg_loans:,} | {t.fg_multi:,} | "
          f"{t.fg_nondecreasing:,} | {t.fg_decreased:,} | {med} |")

    A("\n## C8-3 Is field 63 a balance or a cumulative deferral\n")
    A("**A balance falls and can return to blank while the loan is still "
      "reporting. A cumulative total does neither.**\n")
    A("| archive | loans with 63 > 0 | ever falls | blank again while alive | "
      "median distinct values |")
    A("|---|---|---|---|---|")
    for t in tallies:
        med = "-"
        if t.nib_distinct_hist:
            n = sum(t.nib_distinct_hist.values())
            run = 0
            for k in sorted(t.nib_distinct_hist):
                run += t.nib_distinct_hist[k]
                if run >= n / 2:
                    med = str(k)
                    break
        A(f"| {t.name} | {t.nib_loans:,} | {t.nib_decreased:,} | "
          f"{t.nib_blank_while_alive:,} | {med} |")

    A("\n## C8-4 Does field 12 step up at the modification\n")
    A("`(UPB at - UPB before) / UPB before` on the month field 42 first turns "
      "`Y`. **A step up is capitalised arrears entering the balance. If the "
      "step is absent, the arrears are not in field 12 and leg 2's residual "
      "does not contain them.**\n")
    A("| archive | n | up | flat | down | p10 | p25 | median | p75 | p90 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.mod_step_n:,} | {t.mod_step_up:,} | "
          f"{t.mod_step_flat:,} | {t.mod_step_down:,} | "
          f"{qline(t.mod_step)} |")

    A("\n## C8-5 Do 17 and 19 agree on the modification months\n")
    A("`months(19 - 3) - 17`, on rows where field 42 reads `Y`.\n")
    A("| archive | rows | exact | rate | non-zero differences seen |")
    A("|---|---|---|---|---|")
    for t in tallies:
        rate = t.c5_exact / t.c5_rows if t.c5_rows else float("nan")
        nz = ", ".join(f"{k}:{v:,}" for k, v in sorted(t.c5_diff.items())
                       if k != 0)
        A(f"| {t.name} | {t.c5_rows:,} | {t.c5_exact:,} | {rate:.4f} | "
          f"{nz or '(none)'} |")

    A("\n## C8-6 Do 107 and 108 describe the deferral\n")
    A("On loans whose field 106 reaches `P`, `C` or `D`, read at the first "
      "such row. The ratio is `108 / 63`.\n")
    A("| archive | loans | 108 present | 108 blank | ratio n | p25 | median | "
      "p75 | 107 values |")
    A("|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        q = quantiles(t.defer_vs_nib, (0.25, 0.50, 0.75))
        vals = ", ".join(f"{k}:{v:,}"
                         for k, v in t.adr_count_vals.most_common(6))
        A(f"| {t.name} | {t.adr_loans:,} | {t.adr_amt_present:,} | "
          f"{t.adr_amt_missing:,} | {t.defer_vs_nib_n:,} | {q[0]:.2f} | "
          f"{q[1]:.2f} | {q[2]:.2f} | {vals or '(none)'} |")

    A("\n**A counting note.** `b8_field_audit.py` counted field 63 as set "
      "whenever it was non-blank, and its top value on modification rows is "
      "`0.00`. Here 63 counts only when it is **strictly positive**, so the "
      "loan counts in C8-3 are smaller than that audit's `63 ever set` column "
      "by exactly the loans whose only value is zero. Neither count is wrong; "
      "they answer different questions.\n")

    A("\n## What C8 does not decide\n")
    A("- It does not compute `omega`. It fixes the six inputs `omega` needs "
      "and nothing else.")
    A("- **A ratio sitting at 1.00 identifies an arithmetic convention, not a "
      "field name.** C0b's caveat still governs: fields 41, 49 and 109-113 "
      "remain unidentified and unused.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None,
                    help="archive stem, e.g. 2019Q1; repeatable")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N rows per archive (smoke test)")
    args = ap.parse_args()

    paths = sorted(RAW.glob("*.zip"))
    if args.only:
        keep = set(args.only)
        paths = [p for p in paths if p.stem in keep]
    if not paths:
        print(f"no archives under {RAW}", file=sys.stderr)
        raise SystemExit(1)

    tallies = []
    for p in paths:
        print(f"scanning {p.name}", file=sys.stderr)
        t = Tally(p.stem)
        scan(p, t, args.limit)
        print(f"  done {p.name}: {t.rows:,} rows, {t.loans:,} loans",
              file=sys.stderr)
        tallies.append(t)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(tallies), encoding="utf-8")
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
