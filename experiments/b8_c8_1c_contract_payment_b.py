#!/usr/bin/env python3
"""B8 C8-1c(b): the same question, with an estimator that survives contact.

Registered in the B8 inputs register §6.2.5. Supersedes the floor
estimator in ``b8_c8_1c_contract_payment.py``, which is left unmodified so its
numbers stay on disk and both readings survive.

**Why there is a second version.** The first run scanned 2002Q1 and 2019Q1 in
full and returned four defects, all in the estimator and none in the data:

  D1  ``min`` is not robust. §3 read ``floor / re-derived`` at p25 = 0.80 and
      0.75. Under the hypothesis being tested the floor **is** the contract
      payment and cannot sit below the re-derived one. A single aberrant month
      inside a segment, a flat UPB or an interest-only month, sets the minimum
      and destroys the whole segment's estimate.
  D2  46.5 per cent of 2002Q1's quiet months and 34.3 per cent of 2019Q1's were
      dropped by the ``s_new > 0`` guard, which is D1's direct consequence, and
      the drop was neither counted nor reported. ``b8_fannie_slice.md`` §7
      requires a dropped record to be counted per arm.
  D3  §2 compared the two conventions on **different** samples while its heading
      claimed identical months. In absolute counts the floor convention put
      775,844 **fewer** 2002Q1 months at exactly 1.000, and the rate rose only
      because the denominator halved.
  D4  §3 read the gap at each segment's **earliest** row, where accumulated
      curtailment is smallest by construction, so it suppressed the upward tail
      the hypothesis predicts.

**What the first run did settle, and this one re-checks bit for bit.** Under the
re-derived convention, 33.11 per cent of 2002Q1's quiet months and 39.75 per cent
of 2019Q1's read the ratio at exactly 1.000. An off-by-one in the term predicts
at least 1.0059 for a 6.5 per cent loan at every n up to 480, so it predicts
almost no mass there. **That candidate is dead**, and §4 below reproduces the
reading that killed it.

**The five changes, all in the estimator and the bookkeeping. The quiet-month
filter is untouched**, because changing the criterion and the sampling in one
step makes the difference un-attributable.

  1. The payment estimate is the segment's **modal** implied payment to the cent,
     not its minimum. A level contract payment recurs; an aberration does not.
  2. Months **below** the mode and **above** it are counted separately. The
     curtailment hypothesis predicts almost nothing below. Mass below the mode
     means a third mechanism and the level-payment model is then incomplete.
     **This is the new refutation route.**
  3. Every dropped month is counted with its reason, and the two conventions are
     evaluated on **exactly** the months where both are computable.
  4. The gap is read at each segment's earliest **and** latest row.
  5. Segments carrying more than one modal candidate are counted, which catches a
     structural break inside a segment such as interest-only turning amortising.

**No prediction is read here and no outcome terminates the stage.**

Usage::

    python experiments/b8_c8_1c_contract_payment_b.py --selftest
    python experiments/b8_c8_1c_contract_payment_b.py --only 2002Q1 --only 2019Q1

Writes ``results/b8_c8_1c_contract_payment_b.md``. Deterministic; progress to
stderr only. Markdown and not JSON, so a glob over ``results/*.json`` misses it.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Fannie"
OUT = ROOT / "results" / "b8_c8_1c_contract_payment_b.md"

DELIM = b"|"
NFIELDS = 113

F_LOAN, F_PERIOD = 2, 3
F_RATE, F_UPB = 9, 12
F_REM_LEGAL = 17
F_DELINQ, F_MODFLAG = 40, 42
F_MODNIBUPB = 63

CBIN, CLO, CHI = 0.01, -1.0, 3.0
FBIN, FLO, FHI = 0.001, 0.900, 1.100

#: Two cent-roundings of the reported balance. It bounds the smallest deviation
#: this test can see, and that bound is stated rather than hidden.
CENT = 0.02

#: A value is a modal candidate when it carries at least this share of the
#: segment's months. More than one candidate means a structural break inside the
#: segment, which the level-payment model does not describe.
CAND_SHARE = 0.10

STRATA = (1, 6, 12, 24)


def cbin(x: float) -> int:
    return int(round(min(max(x, CLO), CHI) / CBIN))


def cmid(b: int) -> float:
    return b * CBIN


def fbin(x: float) -> int:
    return int(round(min(max(x, FLO), FHI) / FBIN))


def sbin(x: float) -> int:
    """Share histogram, 0.01 wide on [0, 1]."""
    return int(round(min(max(x, 0.0), 1.0) / 0.01))


def quantiles(c: Counter, qs=(0.10, 0.25, 0.50, 0.75, 0.90),
              mid=cmid) -> list[float]:
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
        out.append(mid(keys[min(i, len(keys) - 1)]))
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


def modal_cluster(implied: list[float]) -> tuple[float, float, float, int]:
    """The modal cluster of implied payments: ``(mean, lo, hi, n_candidates)``.

    **Clusters, not cent buckets.** The file prints UPB to two decimals so
    ``obs`` inherits a rounding at each end, which smears one true payment across
    two or three adjacent cent buckets. Counting buckets would therefore report
    several candidates on every segment and the statistic would be dead on
    arrival. Values within ``CENT`` of their neighbour join one cluster, the
    largest cluster is the estimate, and the estimate is that cluster's **mean**
    so the cent grid does not enter it.

    Ties on cluster size break to the smallest value, since the clusters are
    built in ascending order and ``max`` keeps the first maximum. Deterministic.

    Single linkage can chain, so the caller reports the modal cluster's width and
    a wide cluster is visible rather than silent.
    """
    vals = sorted(implied)
    clusters, cur = [], [vals[0]]
    for v in vals[1:]:
        if v - cur[-1] <= CENT:
            cur.append(v)
        else:
            clusters.append(cur)
            cur = [v]
    clusters.append(cur)
    best = max(clusters, key=len)
    thr = CAND_SHARE * len(implied)
    ncand = sum(1 for c in clusters if len(c) >= thr)
    return sum(best) / len(best), best[0], best[-1], ncand


class Seg:
    __slots__ = ("rate", "rows")

    def __init__(self, rate: float):
        self.rate = rate
        self.rows = []          # (obs, p_upb, p_rem)


class Tally:
    def __init__(self, name: str):
        self.name = name
        self.rows = 0
        self.loans = 0

        # Segment accounting. short + nonpositive_min must reproduce v1's
        # `dropped, under 2 months` column exactly.
        self.segments = 0
        self.drop_seg_short = 0
        self.drop_seg_nonpos_min = 0
        self.drop_seg_nonpos_mode = 0
        self.seg_mode_under_interest = 0     # level-payment model does not apply
        self.seg_multi_candidate = 0
        self.cand_hist = Counter()
        self.cluster_width = Counter()
        self.share_at_mode = Counter()       # per segment
        self.seg_all_at_mode = 0

        # Month accounting.
        self.quiet_months = 0
        self.m_at_mode = 0
        self.m_below_mode = 0
        self.m_above_mode = 0
        self.drop_m_old_nonpos = 0
        self.drop_m_mode_nonpos = 0
        self.paired = 0

        # Paired histograms, identical months on both.
        self.ratio_old_c = Counter()
        self.ratio_mod_c = Counter()
        self.ratio_old_f = Counter()
        self.ratio_mod_f = Counter()
        self.hit_old = 0
        self.hit_mod = 0

        self.strat_mod_c = {k: Counter() for k in STRATA}
        self.strat_hit_mod = {k: 0 for k in STRATA}
        self.strat_hit_old = {k: 0 for k in STRATA}
        self.strat_n = {k: 0 for k in STRATA}

        # Unpaired reproduction of v1's old column, on every quiet month of every
        # segment v1 kept. This must match v1 bit for bit.
        self.repro_old_c = Counter()
        self.repro_old_f = Counter()
        self.repro_n = 0
        self.repro_hit = 0

        # The gap, at both ends of the segment.
        self.gap_first = Counter()
        self.gap_last = Counter()
        self.gap_n = 0
        self.gap_first_unity = 0
        self.gap_last_unity = 0


def close_segment(seg: Seg, t: Tally) -> None:
    rows = seg.rows
    n = len(rows)
    if n < 2:
        t.drop_seg_short += 1
        return
    i = seg.rate / 1200.0
    implied = [obs + p_upb * i for (obs, p_upb, _) in rows]

    # v1's segment gate, kept so §4 reproduces v1's old column exactly.
    if min(implied) <= 0:
        t.drop_seg_nonpos_min += 1
        return

    mode, lo, hi, ncand = modal_cluster(implied)
    if mode <= 0:
        t.drop_seg_nonpos_mode += 1
        return

    t.segments += 1
    t.cand_hist[min(ncand, 6)] += 1
    if ncand > 1:
        t.seg_multi_candidate += 1
    t.cluster_width[cbin(hi - lo)] += 1

    under = 0
    at_mode = 0
    for (obs, p_upb, p_rem), pi in zip(rows, implied):
        t.quiet_months += 1
        if pi < lo:
            t.m_below_mode += 1
        elif pi > hi:
            t.m_above_mode += 1
        else:
            t.m_at_mode += 1
            at_mode += 1

        p_re = level_payment(p_upb, seg.rate, p_rem)
        s_old = (p_re - p_upb * i) if p_re else None
        s_mod = mode - p_upb * i
        if s_mod <= 0:
            under += 1

        # Unpaired reproduction of v1's old column.
        if s_old and s_old > 0:
            r = obs / s_old
            t.repro_old_c[cbin(r)] += 1
            t.repro_old_f[fbin(r)] += 1
            t.repro_n += 1
            if abs(r - 1.0) < 0.005:
                t.repro_hit += 1

        # Paired: both conventions or neither.
        if not (s_old and s_old > 0):
            t.drop_m_old_nonpos += 1
            continue
        if s_mod <= 0:
            t.drop_m_mode_nonpos += 1
            continue
        t.paired += 1
        ro, rm = obs / s_old, obs / s_mod
        t.ratio_old_c[cbin(ro)] += 1
        t.ratio_mod_c[cbin(rm)] += 1
        t.ratio_old_f[fbin(ro)] += 1
        t.ratio_mod_f[fbin(rm)] += 1
        ho = abs(ro - 1.0) < 0.005
        hm = abs(rm - 1.0) < 0.005
        t.hit_old += ho
        t.hit_mod += hm
        for k in STRATA:
            if n >= k:
                t.strat_mod_c[k][cbin(rm)] += 1
                t.strat_n[k] += 1
                t.strat_hit_mod[k] += hm
                t.strat_hit_old[k] += ho

    t.share_at_mode[sbin(at_mode / n)] += 1
    if at_mode == n:
        t.seg_all_at_mode += 1
    if under > n / 2:
        t.seg_mode_under_interest += 1

    # The gap at both ends. Earliest row is the one with the longest remaining
    # term, latest is the shortest. v1 read only the earliest, which is where
    # accumulated curtailment is smallest by construction.
    first = max(rows, key=lambda r: r[2])
    last = min(rows, key=lambda r: r[2])
    pf = level_payment(first[1], seg.rate, first[2])
    pl = level_payment(last[1], seg.rate, last[2])
    if pf and pf > 0 and pl and pl > 0:
        gf, gl = mode / pf, mode / pl
        t.gap_first[cbin(gf)] += 1
        t.gap_last[cbin(gl)] += 1
        t.gap_n += 1
        if abs(gf - 1.0) < 0.0005:
            t.gap_first_unity += 1
        if abs(gl - 1.0) < 0.0005:
            t.gap_last_unity += 1


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
                if nib is not None and nib > 0:
                    st.nib_ever = True

                prev = st.prev
                if prev is not None:
                    p_period, p_rate, p_upb, p_rem, p_delinq, p_mod = prev
                    # UNCHANGED from v1 and from b8_c8_arithmetic.py's control.
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
# Self-test. Case 3 is the regression for D1: the minimum fails there and the
# mode does not.
# ---------------------------------------------------------------------------

def _schedule(B0, RATE, N0, months, curtails=None, flats=()):
    """(rows, implied-payment inputs) for a level-payment loan.

    ``curtails`` is {month: extra}, ``flats`` is a set of months where the
    servicer reports no change in the balance at all.
    """
    curtails = curtails or {}
    i = RATE / 1200.0
    P0 = level_payment(B0, RATE, N0)
    bal, rem, rows = B0, N0, []
    for m in range(months):
        p_upb, p_rem = bal, rem
        if m in flats:
            pass                                  # balance does not move
        else:
            bal = bal - (P0 - bal * i) - curtails.get(m, 0.0)
        rem -= 1
        rows.append((p_upb - bal, p_upb, p_rem))
    return rows, P0, i


def selftest() -> int:
    fails = []
    B0, RATE, N0 = 200000.0, 6.5, 360

    # 1. Clean loan. Both conventions read 1.00 and the mode is the contract.
    rows, P0, i = _schedule(B0, RATE, N0, 60)
    implied = [o + b * i for (o, b, _) in rows]
    mode, lo, hi, nc = modal_cluster(implied)
    if abs(mode - P0) > 1e-9:
        fails.append(f"clean: mode {mode:.6f} vs contract {P0:.6f}")
    if nc != 1 or hi - lo > 1e-9:
        fails.append(f"clean: candidates {nc}, width {hi - lo:.4f}")
    for k, (obs, p_upb, p_rem) in enumerate(rows):
        s_old = level_payment(p_upb, RATE, p_rem) - p_upb * i
        if abs(obs / s_old - 1.0) > 1e-9:
            fails.append(f"clean: old convention off at {k}")

    # 2. One curtailment. The old convention drifts up and stays up, the mode
    #    still recovers the contract, and only the curtailment month is above.
    rows, P0, i = _schedule(B0, RATE, N0, 72, curtails={30: 5000.0})
    implied = [o + b * i for (o, b, _) in rows]
    mode, lo, hi, nc = modal_cluster(implied)
    if abs(mode - P0) > 1e-9:
        fails.append(f"curtail: mode {mode:.6f} vs contract {P0:.6f}")
    above = sum(1 for p in implied if p > hi)
    below = sum(1 for p in implied if p < lo)
    if above != 1 or below != 0:
        fails.append(f"curtail: above {above} (want 1), below {below} (want 0)")
    obs, p_upb, p_rem = rows[60]
    got = obs / (level_payment(p_upb, RATE, p_rem) - p_upb * i)
    if got <= 1.0 + 1e-9:
        fails.append(f"curtail: old convention did not drift, {got:.6f}")
    if abs(obs / (mode - p_upb * i) - 1.0) > 1e-9:
        fails.append("curtail: mode convention off on a quiet month")

    # 3. THE REGRESSION FOR D1. Three flat months inside an otherwise clean
    #    segment. The minimum is set by a flat month and collapses; the mode is
    #    untouched.
    rows, P0, i = _schedule(B0, RATE, N0, 60, flats={7, 8, 33})
    implied = [o + b * i for (o, b, _) in rows]
    mode, lo, hi, nc = modal_cluster(implied)
    floor = min(implied)
    if abs(mode - P0) > 1e-9:
        fails.append(f"flat: mode {mode:.6f} vs contract {P0:.6f}")
    if floor >= P0 - 1.0:
        fails.append(f"flat: minimum was supposed to collapse, got {floor:.2f}")
    bad = sum(1 for (_, b, _) in rows if floor - b * i <= 0)
    if bad == 0:
        fails.append("flat: minimum did not drive s_new non-positive")
    below = sum(1 for p in implied if p < lo)
    if below != 3:
        fails.append(f"flat: below-mode count {below}, want 3")
    print(f"  D1 regression: contract {P0:,.2f}, mode {mode:,.2f}, "
          f"min {floor:,.2f}, months the min would kill {bad}/{len(rows)}",
          file=sys.stderr)

    # 4. Two modal candidates when a segment breaks in the middle.
    a, P0, i = _schedule(B0, RATE, N0, 24)
    b, _, _ = _schedule(a[-1][1], RATE, N0 - 24, 24)
    mixed = [o + bal * i for (o, bal, _) in a] + [P0 * 1.5] * 12
    _, _, _, nc = modal_cluster(mixed)
    if nc < 2:
        fails.append(f"break: candidates {nc}, want at least 2")

    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        print(f"selftest: {len(fails)} failure(s)", file=sys.stderr)
        return 1
    print("selftest: ok, four cases", file=sys.stderr)
    return 0


def qline(c: Counter) -> str:
    return " | ".join(f"{v:.2f}" for v in quantiles(c))


def pct(a: int, b: int) -> str:
    return f"{a / b:.4f}" if b else "-"


def render(tallies: list[Tally]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8 C8-1c(b): the modal payment, and the accounting v1 owed\n")
    A("Generated by `experiments/b8_c8_1c_contract_payment_b.py`. Registered in "
      "the B8 inputs register §6.2.5.\n")
    A("**No prediction is read here and no outcome terminates the stage.** "
      "`b8_c8_arithmetic.py` and `b8_c8_1c_contract_payment.py` are both "
      "unmodified and their outputs stand beside this one. The quiet-month "
      "filter is identical to theirs.\n")

    A("\n## 0. Scanned, and every segment accounted for\n")
    A("`short` plus `min <= 0` must reproduce v1's `dropped, under 2 months` "
      "column exactly, because v1 lumped the two together.\n")
    A("| archive | rows | loans | segments kept | short | min <= 0 | sum | "
      "mode <= 0 |")
    A("|---|---|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.rows:,} | {t.loans:,} | {t.segments:,} | "
          f"{t.drop_seg_short:,} | {t.drop_seg_nonpos_min:,} | "
          f"{t.drop_seg_short + t.drop_seg_nonpos_min:,} | "
          f"{t.drop_seg_nonpos_mode:,} |")

    A("\n## 1. Levelness at the mode, and the sign of the deviations\n")
    A("**The below-mode column is the new refutation route.** A level "
      "contractual payment with occasional curtailment puts almost nothing "
      "below the mode. Mass below it means a third mechanism is present and the "
      "level-payment model is incomplete.\n")
    A("| archive | quiet months | at mode | rate | below mode | rate | above "
      "mode | rate |")
    A("|---|---|---|---|---|---|---|---|")
    for t in tallies:
        q = t.quiet_months
        A(f"| {t.name} | {q:,} | {t.m_at_mode:,} | {pct(t.m_at_mode, q)} | "
          f"{t.m_below_mode:,} | {pct(t.m_below_mode, q)} | "
          f"{t.m_above_mode:,} | {pct(t.m_above_mode, q)} |")

    A("\n**A wide modal cluster means single linkage chained**, so the width is "
      "printed rather than assumed small. Cent-rounding alone gives about "
      "0.02 to 0.04.\n")
    A("| archive | segments | every month at mode | rate | share at mode p10 "
      "| p50 | p90 | cluster width p50 | p90 | more than one candidate | rate | "
      "mode under interest |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        q = quantiles(t.share_at_mode, (0.10, 0.50, 0.90),
                      mid=lambda b: b * 0.01)
        w = quantiles(t.cluster_width, (0.50, 0.90))
        A(f"| {t.name} | {t.segments:,} | {t.seg_all_at_mode:,} | "
          f"{pct(t.seg_all_at_mode, t.segments)} | {q[0]:.2f} | {q[1]:.2f} | "
          f"{q[2]:.2f} | {w[0]:.2f} | {w[1]:.2f} | {t.seg_multi_candidate:,} | "
          f"{pct(t.seg_multi_candidate, t.segments)} | "
          f"{t.seg_mode_under_interest:,} |")

    A("\n## 2. The paired comparison, genuinely on identical months\n")
    A("A month enters only when **both** conventions are computable on it. "
      "Every exclusion is counted.\n")
    A("| archive | quiet months | paired | rate | dropped, old non-positive | "
      "dropped, mode under interest |")
    A("|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | {t.quiet_months:,} | {t.paired:,} | "
          f"{pct(t.paired, t.quiet_months)} | {t.drop_m_old_nonpos:,} | "
          f"{t.drop_m_mode_nonpos:,} |")

    A("\n| archive | convention | n | p10 | p25 | median | p75 | p90 | within "
      "0.005 of 1.00 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        A(f"| {t.name} | old, re-derived | {t.paired:,} | "
          f"{qline(t.ratio_old_c)} | {pct(t.hit_old, t.paired)} |")
        A(f"| {t.name} | new, modal | {t.paired:,} | {qline(t.ratio_mod_c)} | "
          f"{pct(t.hit_mod, t.paired)} |")

    A("\n### 2b. Stratified by segment length, both conventions\n")
    A("| archive | segment months | n | modal p10 | modal median | modal p90 | "
      "modal within 0.005 | old within 0.005 |")
    A("|---|---|---|---|---|---|---|---|")
    for t in tallies:
        for k in STRATA:
            q = quantiles(t.strat_mod_c[k], (0.10, 0.50, 0.90))
            A(f"| {t.name} | at least {k} | {t.strat_n[k]:,} | {q[0]:.2f} | "
              f"{q[1]:.2f} | {q[2]:.2f} | "
              f"{pct(t.strat_hit_mod[k], t.strat_n[k])} | "
              f"{pct(t.strat_hit_old[k], t.strat_n[k])} |")

    A("\n### 2c. Fine resolution around 1.00, paired\n")
    A("0.001 bins. **Read the absolute counts, not only the rates**, which is "
      "the error v1's §2c invited.\n")
    A("| archive | convention | at 1.000 | rate | within 0.002 | rate |")
    A("|---|---|---|---|---|---|")
    for t in tallies:
        for label, c in (("old, re-derived", t.ratio_old_f),
                         ("new, modal", t.ratio_mod_f)):
            n = sum(c.values())
            exact = c.get(fbin(1.0), 0)
            near = sum(v for k, v in c.items() if abs(k - fbin(1.0)) <= 2)
            A(f"| {t.name} | {label} | {exact:,} | {pct(exact, n)} | "
              f"{near:,} | {pct(near, n)} |")

    A("\n## 3. The payment gap, at both ends of the segment\n")
    A("`mode / re-derived payment`. **First** is the segment's longest-term "
      "row, where accumulated curtailment is smallest by construction and v1 "
      "read it alone. **Last** is its shortest-term row, where the accumulation "
      "is largest. The curtailment hypothesis predicts the last reading sits "
      "above the first; an off-by-one in the term predicts a narrow band near "
      "1.006 at both ends with almost nothing at 1.000.\n")
    A("| archive | segments | end | at 1.000 | rate | p25 | median | p75 | "
      "p90 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        for label, c, u in (("first", t.gap_first, t.gap_first_unity),
                            ("last", t.gap_last, t.gap_last_unity)):
            q = quantiles(c, (0.25, 0.50, 0.75, 0.90))
            A(f"| {t.name} | {t.gap_n:,} | {label} | {u:,} | "
              f"{pct(u, t.gap_n)} | {q[0]:.2f} | {q[1]:.2f} | {q[2]:.2f} | "
              f"{q[3]:.2f} |")

    A("\n## 4. Reproduction of v1's reading, unpaired\n")
    A("The re-derived convention on **every** quiet month of every segment v1 "
      "kept, which is v1's own sample. **These figures must match v1's `old, "
      "re-derived` row bit for bit.** They are what killed the off-by-one "
      "candidate, and a default that does not reproduce is a defect.\n")
    A("| archive | n | p10 | p25 | median | p75 | p90 | at 1.000 | rate | "
      "within 0.005 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for t in tallies:
        exact = t.repro_old_f.get(fbin(1.0), 0)
        A(f"| {t.name} | {t.repro_n:,} | {qline(t.repro_old_c)} | "
          f"{exact:,} | {pct(exact, t.repro_n)} | "
          f"{pct(t.repro_hit, t.repro_n)} |")

    A("\n## What this does not decide\n")
    A("- **It does not identify the contractual payment.** The mode estimates "
      "the level payment the borrower habitually makes. A borrower who rounds "
      "every payment up to the same larger number is indistinguishable here. "
      "That separation needs the origination fields and is **C8-1d**, "
      "registered and not run.")
    A("- **It does not compute `omega`.** It decides which payment "
      "`b8_omega.py` carries as state, and whether carrying one is enough.")
    A("- The quiet-month filter still does not read field 44, so a loan's "
      "payoff month is in the sample and lands at the clip ceiling. Bounded at "
      "1.3 to 2.9 per cent of rows. **Left in deliberately**: changing the "
      "criterion and the sampling in one step makes the difference "
      "un-attributable. It is fixed in `b8_omega.py`.")
    A("- A segment boundary is a change in field 9. Two modifications landing "
      "on the same rate with no intervening rate change merge into one segment. "
      "The multi-candidate count in §1 is the handle on that.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
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
