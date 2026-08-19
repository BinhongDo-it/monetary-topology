#!/usr/bin/env python3
"""B8 C8-1c: is C8-1a's deviation the recompute-versus-contract gap?

Registered in the B8 inputs register §6.2. Follows
``b8_c8_arithmetic.py``, which it does not modify: C8's output stays on disk
under the old convention so both readings survive.

**Why this exists.** C8-1a's control did not sit at 1.00. Five of six archives
read a median of 1.01 and upper quartiles of 1.10 to 2.12. The registered rule
makes that a failure of the amortisation model, and §14.2's ``V-hat`` calls the
same function, so it is settled before ``b8_omega.py`` is written.

**The hypothesis under test.** ``b8_c8_arithmetic.py`` recomputes the scheduled
principal from the current balance every month. The contractual payment is fixed
at origination and does not move when the balance does. Any historical
curtailment leaves the recomputed payment below the contractual one, and the gap
in the principal component is amplified by ``(1+i)**n``::

    observed / recomputed  =  1 + d * (1+i)**n
    d = (scheduled balance - actual balance) / actual balance

At 6.5 per cent over 300 months that factor is 4.47, so ``d`` of 0.22 per cent
reads 1.01 and ``d`` of 22 per cent reads 2.13. The observed quantiles have that
shape, and 2019Q1, the least seasoned archive, is the one that reads 1.00.

**What this script asks.** Per loan, on the same quiet months C8-1a used, read
the implied payment::

    P(t) = (UPB before - UPB at) + UPB before * rate / 1200

  1. Is ``P`` level inside a constant-rate segment of the loan? A fixed
     contractual payment is. A payment re-derived from the balance is not.
  2. Recomputing the ratio against the segment's own floor of ``P`` instead of
     against a re-derived payment, does it collapse onto 1.00?

**A collapse confirms the diagnosis. A failure to collapse refutes it**, and the
residual distribution is printed so the next hypothesis has something to work on.

**What this cannot decide, stated before it runs.** The floor of ``P`` estimates
the level payment the borrower habitually makes. A borrower who rounds every
payment up to the same larger number has a level ``P`` that is not the
contractual one, and this test cannot separate the two. That separation needs
the origination fields and it is **C8-1d**, registered in §6.2 and not run here.
**It does not affect the question this script asks**, which is whether the
payment is level at all.

**No prediction is read here and no outcome terminates the stage.**

Design follows ``b8_field_audit.py`` and ``b8_c8_arithmetic.py``: one streaming
pass per archive, a per-loan state machine, no sort. C0b established that each
loan's rows are one contiguous block, which is what makes that legal. Per-loan
buffering is bounded by that loan's own row count.

Usage::

    python experiments/b8_c8_1c_contract_payment.py --selftest
    python experiments/b8_c8_1c_contract_payment.py --only 2019Q1 --limit 2000000
    python experiments/b8_c8_1c_contract_payment.py --only 2002Q1 --only 2019Q1
    python experiments/b8_c8_1c_contract_payment.py

Writes ``results/b8_c8_1c_contract_payment.md``. Deterministic; progress to
stderr only. Output is markdown and not JSON, so ``render_results.py`` does not
glob it and ``RESULTS.md`` is untouched.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Fannie"
OUT = ROOT / "results" / "b8_c8_1c_contract_payment.md"

DELIM = b"|"
NFIELDS = 113

F_LOAN, F_PERIOD = 2, 3
F_RATE, F_UPB = 9, 12
F_REM_LEGAL = 17
F_DELINQ, F_MODFLAG = 40, 42
F_MODNIBUPB = 63

#: Coarse histogram, same bins as C8-1a so the two are read side by side.
CBIN, CLO, CHI = 0.01, -1.0, 3.0
#: Fine histogram around 1.00, because the question is whether a mass lands
#: exactly there and 0.01 bins cannot see that.
FBIN, FLO, FHI = 0.001, 0.900, 1.100

#: A month counts as "at the floor" when the implied payment matches the segment
#: floor to within two cent-roundings of the reported balance. The file prints
#: UPB to two decimals, so ``obs`` inherits up to a cent of rounding at each end
#: and a genuinely level payment can still spread by two. Taken from the file's
#: reporting precision, not tuned. It bounds the smallest curtailment this test
#: can see, and that bound is stated rather than hidden.
CENT = 0.02

#: A segment counts as level when this share of its months sits at the floor.
#: Levelness with occasional curtailments is the hypothesis; a payment that
#: wanders is the alternative, and a max-minus-min spread cannot tell them apart
#: because one curtailment sets the maximum.
LEVEL_SHARE = 0.80

#: Segment length strata. A floor drawn from few months is biased upward, which
#: pushes the recomputed ratio below 1.00, so the strata are reported rather
#: than a single pooled figure.
STRATA = (1, 6, 12, 24)


def cbin(x: float) -> int:
    return int(round(min(max(x, CLO), CHI) / CBIN))


def cmid(b: int) -> float:
    return b * CBIN


def fbin(x: float) -> int:
    return int(round(min(max(x, FLO), FHI) / FBIN))


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
        out.append(cmid(keys[min(i, len(keys) - 1)]))
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


def level_payment(balance: float, rate_pct: float, n: int):
    """The payment that amortises ``balance`` over ``n`` months at ``rate_pct``.

    This is the quantity ``b8_c8_arithmetic.py`` re-derives every month. C8-1c
    exists to test whether re-deriving it is the error.
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
    return balance * i / (1.0 - factor)


class Seg:
    """One constant-rate run of quiet months inside a single loan."""

    __slots__ = ("rate", "rows")

    def __init__(self, rate: float):
        self.rate = rate
        self.rows = []          # (obs, p_upb, p_rem)


class Tally:
    def __init__(self, name: str):
        self.name = name
        self.rows = 0
        self.loans = 0

        self.segments = 0
        self.seg_len_hist = Counter()

        # Levelness of the implied payment inside a segment.
        self.lvl_one_value = 0          # every month at the floor
        self.lvl_mostly = 0             # at least LEVEL_SHARE of months there
        self.lvl_spread = Counter()     # (max - min) / min, coarse bins
        self.at_floor_months = 0
        self.quiet_months = 0

        # The two ratios, on identical months.
        self.ratio_old_c = Counter()    # obs / recomputed scheduled principal
        self.ratio_new_c = Counter()    # obs / (floor payment - interest)
        self.ratio_old_f = Counter()
        self.ratio_new_f = Counter()
        self.hit_old = 0                # |ratio - 1| < 0.005
        self.hit_new = 0

        # Same, stratified by segment length.
        self.strat_new_c = {k: Counter() for k in STRATA}
        self.strat_hit_new = {k: 0 for k in STRATA}
        self.strat_n = {k: 0 for k in STRATA}

        # The payment gap itself: floor payment over re-derived payment.
        self.pay_gap = Counter()
        self.pay_gap_n = 0
        self.pay_gap_unity = 0          # segments where the two agree

        self.dropped_short = 0          # segments with fewer than two months


def close_segment(seg: Seg, t: Tally) -> None:
    rows = seg.rows
    if len(rows) < 2:
        t.dropped_short += 1
        return
    i = seg.rate / 1200.0
    implied = [obs + p_upb * i for (obs, p_upb, _) in rows]
    floor = min(implied)
    if floor <= 0:
        t.dropped_short += 1
        return

    t.segments += 1
    n = len(rows)
    t.seg_len_hist[min(n, 240)] += 1

    hi = max(implied)
    t.lvl_spread[cbin((hi - floor) / floor)] += 1
    if hi - floor <= CENT:
        t.lvl_one_value += 1

    # The payment gap, read once per segment on its longest-term row so the
    # comparison is against the re-derivation the old convention would make.
    obs0, p_upb0, p_rem0 = max(rows, key=lambda r: r[2])
    p_rederived = level_payment(p_upb0, seg.rate, p_rem0)
    if p_rederived and p_rederived > 0:
        t.pay_gap[cbin(floor / p_rederived)] += 1
        t.pay_gap_n += 1
        if abs(floor / p_rederived - 1.0) < 0.0005:
            t.pay_gap_unity += 1

    at_floor = 0
    for (obs, p_upb, p_rem), pi in zip(rows, implied):
        t.quiet_months += 1
        if pi - floor <= CENT:
            t.at_floor_months += 1
            at_floor += 1

        s_new = floor - p_upb * i
        p_re = level_payment(p_upb, seg.rate, p_rem)
        s_old = (p_re - p_upb * i) if p_re else None

        if s_old and s_old > 0:
            r = obs / s_old
            t.ratio_old_c[cbin(r)] += 1
            t.ratio_old_f[fbin(r)] += 1
            if abs(r - 1.0) < 0.005:
                t.hit_old += 1
        if s_new > 0:
            r = obs / s_new
            t.ratio_new_c[cbin(r)] += 1
            t.ratio_new_f[fbin(r)] += 1
            if abs(r - 1.0) < 0.005:
                t.hit_new += 1
            for k in STRATA:
                if n >= k:
                    t.strat_new_c[k][cbin(r)] += 1
                    t.strat_n[k] += 1
                    if abs(r - 1.0) < 0.005:
                        t.strat_hit_new[k] += 1

    if at_floor >= LEVEL_SHARE * n:
        t.lvl_mostly += 1


class LoanState:
    __slots__ = ("prev", "seg", "nib_ever")

    def __init__(self):
        self.prev = None
        self.seg = None
        self.nib_ever = False


def scan(path: Path, t: Tally, limit_rows: int) -> None:
    st = LoanState()
    cur_id = None

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
                    if st.seg is not None:
                        close_segment(st.seg, t)
                    if cur_id is not None:
                        t.loans += 1
                    st = LoanState()
                    cur_id = lid

                period = to_period(p[F_PERIOD - 1])
                rate = num(p[F_RATE - 1])
                upb = num(p[F_UPB - 1])
                rem = num(p[F_REM_LEGAL - 1])
                rem = int(rem) if rem is not None else None
                delinq = p[F_DELINQ - 1].strip()
                mod = p[F_MODFLAG - 1].strip() == b"Y"
                nib = num(p[F_MODNIBUPB - 1])
                # Set before the pair is read, which is the order
                # b8_c8_arithmetic.py uses, so the month a deferred balance
                # first appears is excluded from the control on both sides.
                if nib is not None and nib > 0:
                    st.nib_ever = True

                prev = st.prev
                if prev is not None:
                    p_period, p_rate, p_upb, p_rem, p_delinq, p_mod = prev
                    # C8-1a's quiet-month filter and its control restriction,
                    # both verbatim: the loan must have carried no deferred
                    # balance on any row so far. Keeping the sample identical is
                    # what makes the two conventions comparable.
                    quiet = (months_between(period, p_period) == 1 and
                             delinq == b"00" and p_delinq == b"00" and
                             mod == p_mod and
                             rem is not None and p_rem is not None and
                             p_rem - rem == 1 and
                             rate is not None and p_rate is not None and
                             abs(rate - p_rate) < 1e-9 and
                             p_upb and upb is not None and p_upb > 0 and
                             not st.nib_ever)
                    if quiet:
                        if st.seg is None or abs(st.seg.rate - p_rate) >= 1e-9:
                            if st.seg is not None:
                                close_segment(st.seg, t)
                            st.seg = Seg(p_rate)
                        st.seg.rows.append((p_upb - upb, p_upb, p_rem))

                st.prev = (period, rate, upb, rem, delinq, mod)

    if st.seg is not None:
        close_segment(st.seg, t)
    if cur_id is not None:
        t.loans += 1


# ---------------------------------------------------------------------------
# Self-test: a hand-built amortisation schedule, run through the same functions
# before anything touches a real loan. The discipline is HANDOFF_B8 §7 step 2.
# ---------------------------------------------------------------------------

def selftest() -> int:
    B0, RATE, N0 = 200000.0, 6.5, 360
    i = RATE / 1200.0
    P0 = level_payment(B0, RATE, N0)
    assert P0 is not None

    # Two schedules on the same contract, one curtailed and one not, so that
    # ``d`` is measured from the simulation and the closed form is tested
    # against it rather than derived from it.
    bal, rem = B0, N0
    clean = B0
    rows = []                       # (obs, p_upb, p_rem)
    dvals = []                      # (scheduled balance - actual) / actual
    CURTAIL_AT, CURTAIL = 30, 5000.0
    for m in range(72):
        p_upb, p_rem = bal, rem
        dvals.append((clean - bal) / bal)
        extra = CURTAIL if m == CURTAIL_AT else 0.0
        bal = bal - (P0 - bal * i) - extra
        clean = clean - (P0 - clean * i)
        rem -= 1
        rows.append((p_upb - bal, p_upb, p_rem))

    fails = []

    # 1. Before the curtailment the old convention is exact.
    for k in (0, 5, 29):
        obs, p_upb, p_rem = rows[k]
        s_old = level_payment(p_upb, RATE, p_rem) - p_upb * i
        if abs(obs / s_old - 1.0) > 1e-9:
            fails.append(f"old convention off at month {k}: {obs / s_old:.6f}")

    # 2. After it, the old convention reads 1 + d*(1+i)**n, with d taken from
    #    the parallel clean schedule.
    for k in (40, 60, 71):
        obs, p_upb, p_rem = rows[k]
        s_old = level_payment(p_upb, RATE, p_rem) - p_upb * i
        got = obs / s_old
        pred = 1.0 + dvals[k] * (1.0 + i) ** p_rem
        if got <= 1.0 + 1e-9:
            fails.append(f"no upward bias after curtailment at {k}: {got:.6f}")
        if abs(got - pred) > 1e-6:
            fails.append(f"closed form off at {k}: {got:.6f} vs {pred:.6f}")
        print(f"  month {k}: d={dvals[k]:.6f} amplifier="
              f"{(1.0 + i) ** p_rem:.4f} ratio={got:.6f}", file=sys.stderr)

    # 3. The floor convention returns exactly 1.00 in every non-curtailment
    #    month and strictly above 1.00 in the curtailment month.
    implied = [obs + p_upb * i for (obs, p_upb, _) in rows]
    floor = min(implied)
    if abs(floor - P0) > 1e-6:
        fails.append(f"floor missed the contract payment: {floor:.6f} vs {P0:.6f}")
    for k, (obs, p_upb, _) in enumerate(rows):
        r = obs / (floor - p_upb * i)
        if k == CURTAIL_AT:
            if r <= 1.0 + 1e-6:
                fails.append(f"curtailment month did not read above 1: {r:.6f}")
        elif abs(r - 1.0) > 1e-9:
            fails.append(f"floor convention off at month {k}: {r:.9f}")

    # 4. A schedule with no curtailment at all must read 1.00 both ways.
    bal2, rem2 = B0, N0
    for m in range(48):
        p_upb, p_rem = bal2, rem2
        bal2 = bal2 - (P0 - bal2 * i)
        rem2 -= 1
        obs = p_upb - bal2
        s_old = level_payment(p_upb, RATE, p_rem) - p_upb * i
        if abs(obs / s_old - 1.0) > 1e-9:
            fails.append(f"clean loan not at 1.00 under old convention at {m}")

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        print(f"selftest: {len(fails)} failure(s)", file=sys.stderr)
        return 1
    print("selftest: ok. contract payment "
          f"{P0:,.2f}, floor recovered {floor:,.2f}", file=sys.stderr)
    return 0


def qline(c: Counter) -> str:
    return " | ".join(f"{v:.2f}" for v in quantiles(c))


def pct(a: int, b: int) -> str:
    return f"{a / b:.4f}" if b else "-"


def render(tallies: list[Tally]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8 C8-1c: is C8-1a's deviation the recompute-versus-contract gap?\n")
    A("Generated by `experiments/b8_c8_1c_contract_payment.py`. Registered in "
      "the B8 inputs register §6.2.\n")
    A("**No prediction is read here and no outcome terminates the stage.** "
      "`b8_c8_arithmetic.py` is unmodified and its output stands beside this "
      "one.\n")

    A("\n## Scanned\n")
    A("| archive | rows | loans | quiet months | segments | dropped, under 2 "
      "months |")
    A("|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.rows:,} | {t.loans:,} | {t.quiet_months:,} | "
          f"{t.segments:,} | {t.dropped_short:,} |")

    A("\n## 1. Is the implied payment level inside a constant-rate segment\n")
    A("`P = (UPB before - UPB at) + UPB before * rate/1200`, on the quiet "
      "months of C8-1a's control. A fixed contractual payment gives one value "
      "per segment. **The spread column is `(max - min) / min`.**\n")
    A("| archive | segments | every month at the floor | rate | at least 80 "
      "per cent there | rate | months at the floor | rate | spread p50 | "
      "spread p90 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        q = quantiles(t.lvl_spread, (0.50, 0.90))
        A(f"| {t.name} | {t.segments:,} | {t.lvl_one_value:,} | "
          f"{pct(t.lvl_one_value, t.segments)} | {t.lvl_mostly:,} | "
          f"{pct(t.lvl_mostly, t.segments)} | {t.at_floor_months:,} | "
          f"{pct(t.at_floor_months, t.quiet_months)} | {q[0]:.2f} | "
          f"{q[1]:.2f} |")

    A("\n## 2. The decisive comparison, on identical months\n")
    A("**Old**: the ratio against a payment re-derived from the current "
      "balance, which is what C8-1a computed. **New**: the ratio against the "
      "segment's own floor payment. **A collapse of the new column onto 1.00 "
      "confirms the diagnosis. A failure to collapse refutes it.**\n")
    A("| archive | convention | n | p10 | p25 | median | p75 | p90 | within "
      "0.005 of 1.00 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        n_old = sum(t.ratio_old_c.values())
        n_new = sum(t.ratio_new_c.values())
        A(f"| {t.name} | old, re-derived | {n_old:,} | {qline(t.ratio_old_c)} "
          f"| {pct(t.hit_old, n_old)} |")
        A(f"| {t.name} | new, floor | {n_new:,} | {qline(t.ratio_new_c)} | "
          f"{pct(t.hit_new, n_new)} |")

    A("\n### 2b. The same, stratified by segment length\n")
    A("A floor drawn from few months is biased upward, which pushes the new "
      "ratio **below** 1.00. The strata show that bias rather than pooling it "
      "away.\n")
    A("| archive | segment months | n | p10 | median | p90 | within 0.005 |")
    A("|---|---|---|---|---|---|---|")
    for t in tallies:
        for k in STRATA:
            q = quantiles(t.strat_new_c[k], (0.10, 0.50, 0.90))
            A(f"| {t.name} | at least {k} | {t.strat_n[k]:,} | {q[0]:.2f} | "
              f"{q[1]:.2f} | {q[2]:.2f} | "
              f"{pct(t.strat_hit_new[k], t.strat_n[k])} |")

    A("\n### 2c. Fine resolution around 1.00\n")
    A("0.001 bins. The coarse table cannot distinguish a mass at 1.000 from a "
      "mass at 1.009, and that distinction is the whole question.\n")
    A("| archive | convention | at 1.000 | rate | within 0.002 | rate |")
    A("|---|---|---|---|---|---|")
    for t in tallies:
        for label, c in (("old, re-derived", t.ratio_old_f),
                         ("new, floor", t.ratio_new_f)):
            n = sum(c.values())
            exact = c.get(fbin(1.0), 0)
            near = sum(v for k, v in c.items() if abs(k - fbin(1.0)) <= 2)
            A(f"| {t.name} | {label} | {exact:,} | {pct(exact, n)} | "
              f"{near:,} | {pct(near, n)} |")

    A("\n## 3. The payment gap itself\n")
    A("Floor payment over the payment re-derived from the balance, one reading "
      "per segment taken on its longest-term row. **At 1.00 the two "
      "conventions agree and that segment contributes nothing to C8-1a's "
      "deviation.**\n")
    A("| archive | segments | at 1.000 | rate | p25 | median | p75 | p90 |")
    A("|---|---|---|---|---|---|---|---|")
    for t in tallies:
        q = quantiles(t.pay_gap, (0.25, 0.50, 0.75, 0.90))
        A(f"| {t.name} | {t.pay_gap_n:,} | {t.pay_gap_unity:,} | "
          f"{pct(t.pay_gap_unity, t.pay_gap_n)} | {q[0]:.2f} | {q[1]:.2f} | "
          f"{q[2]:.2f} | {q[3]:.2f} |")

    A("\n## What C8-1c does not decide\n")
    A("- **It does not identify the contractual payment.** The floor estimates "
      "the level payment the borrower habitually makes. A borrower who rounds "
      "every payment up to the same larger number is indistinguishable here. "
      "Separating the two needs the origination fields and is **C8-1d**, "
      "registered and not run.")
    A("- **It does not compute `omega`.** It decides which payment "
      "`b8_omega.py` carries as state.")
    A("- A segment boundary is a change in field 9. Two modifications landing "
      "on the same rate with no intervening rate change would merge into one "
      "segment and bias that segment's floor downward. The count of such cases "
      "is not separated here.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None,
                    help="archive stem, e.g. 2019Q1; repeatable")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N rows per archive (smoke test)")
    ap.add_argument("--selftest", action="store_true",
                    help="hand-built amortisation schedule, touches no archive")
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(selftest())

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
        print(f"  done {p.name}: {t.rows:,} rows, {t.loans:,} loans, "
              f"{t.segments:,} segments", file=sys.stderr)
        tallies.append(t)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(tallies))
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
