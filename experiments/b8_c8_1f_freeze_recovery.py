#!/usr/bin/env python3
"""B8 C8-1f: is the frozen month paid back the next month?

Registered in ``docs/b8_inputs_availability.md`` §6.2.7. Reads the core table.

**What C8-1e left.** Roughly half of the below-mode months are months in which
the reported balance **did not move at all**, while the delinquency status reads
``00`` on both rows, field 17 falls by exactly one and the rate is unchanged.
They are overwhelmingly singletons, and their shortfall matches the principal
share of the payment to within two points on every archive, which is what a
frozen balance produces and what an interest-only period would also produce. Runs
of sixty months or more carry only 0.1 to 3.1 per cent of them, and Fannie
stopped originating interest-only before the 2012, 2017 and 2019 cohorts, so a
product feature does not explain the bulk of it.

**Why the answer changes the B8-0a(i) ruling.** If a frozen month is compensated
the following month, then over any window containing both, ``r(t) > 0`` at the
freeze and ``r(t) < 0`` at the catch-up and **they cancel by the same mechanism
that makes the clean-cure round trip cancel**. The artefact is then a timing
shuffle, not a level shift, and it contaminates ``omega`` only where a loop
boundary falls between the two. That is fixable by defining the loop window, and
it does not require restricting the gate to a schedule-obeying subsample.

If instead the balance never catches up, the deviation is permanent, it
accumulates over the window, and the subsample restriction is the only route
left.

**So this is a two-way test and both outcomes are mapped before the run:**

===========================  ==================================================
recovery at lag 1 dominates  timing shuffle. B8-0a(i) keeps a tight tolerance,
                             the loop window is defined so that a freeze and its
                             catch-up sit on the same side, and the residual is
                             bounded by the boundary cases counted in §5.
recovery is rare or slow     level shift. The subsample route (C8-1e §5's
                             19,090 loans) is the one left, and its skew toward
                             the newest archives is a stated limitation.
===========================  ==================================================

**No prediction is read here and no outcome terminates the stage.**

The four measurements:

  1. **The month after.** ``obs_next / scheduled_next`` on the quiet month
     immediately following a freeze, against the same statistic following an
     at-mode month as a control. Compensation puts a mass at 2.00 that the
     control does not have.
  2. **Recovery lag.** Within a segment, the cumulative deviation
     ``sum(obs - scheduled)`` returns to its pre-freeze level after how many
     months. Checked at lags 1 to 6, with everything else bucketed.
  3. **The segment net**, which is the statistic ``omega`` actually accumulates.
     ``sum(obs - scheduled) / sum(scheduled)`` per segment, split by whether the
     segment contains a freeze. **A timing shuffle nets to zero here and a level
     shift does not.**
  4. **Censoring.** How many freezes sit where their compensator could not be
     seen: at the last quiet month of a segment, or with a non-contiguous next
     quiet month. That bounds how much of "never recovered" is measurement.

It also **repairs C8-1e's assistance column**, which counted field 102 as set
whenever it was non-blank. `HANDOFF_B8.md` §3 records that ``7`` in that field
means none of the above and is not data, so the old column measured whether the
field was populated. The three states are separated here.

Usage::

    python experiments/b8_c8_1f_freeze_recovery.py --selftest
    python experiments/b8_c8_1f_freeze_recovery.py

Writes ``results/b8_c8_1f_freeze_recovery.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b8_c8_1f_freeze_recovery.md"

#: The cumulative deviation counts as recovered when it is back within this much
#: of its pre-freeze level. Ten per cent of one scheduled principal, floored at a
#: dollar so that several months of cent-rounding cannot fail it. Stated because
#: it is a choice, not a measurement.
REC_FRAC, REC_FLOOR = 0.10, 1.00

#: Lags checked explicitly. Compensation the following month is the hypothesis,
#: so the interesting resolution is at the short end.
MAX_LAG = 6

#: Ratio bins for the month after a freeze. 2.00 is one freeze paid back.
R_EDGES = [-1e9, 0.001, 0.5, 0.95, 1.05, 1.5, 1.95, 2.05, 3.0, 1e9]
R_LABELS = ["<= 0", "(0, 0.5]", "(0.5, 0.95]", "**1.00**", "(1.05, 1.5]",
            "(1.5, 1.95]", "**2.00**", "(2.05, 3.0]", "> 3.0"]

#: Loop windows to report in §5, in months.
WINDOWS = (3, 6, 12, 24)


def pct(a, b) -> str:
    return f"{a / b:.4f}" if b else "-"


def qs(x, p=(10, 25, 50, 75, 90)) -> list[float]:
    if x.size == 0:
        return [float("nan")] * len(p)
    return np.nanpercentile(x, p).tolist()


class Arch:
    def __init__(self, name):
        self.name = name


def analyse(name: str) -> Arch:
    a = Arch(name)
    c = K.Core(name, cols=["period", "rate", "upb", "rem_legal", "delinq",
                           "mod_flag", "nib_upb", "assist"],
               loan_cols=["orig_term"])
    try:
        q = K.quiet_pairs(c)
        seg = K.segment_ids(q)
        mode, lo, hi, ncand, seg_start, seg_count, implied = \
            K.segment_modes(q, seg)
        cur = q["cur"]
        n = implied.size
        a.n = n
        a.n_seg = int(seg_count.size)

        p_upb = q["p_upb_cents"].astype(np.float64) / 100.0
        obs = q["obs_cents"].astype(np.float64) / 100.0
        i = q["rate_milli"].astype(np.float64) / 1000.0 / 1200.0
        sched = mode - p_upb * i          # scheduled principal at the modal pay
        dev = obs - sched                 # what omega's residual is made of

        below = implied < lo
        above = implied > hi
        at = ~below & ~above
        frozen = below & (obs == 0.0)
        a.n_below, a.n_above, a.n_at = int(below.sum()), int(above.sum()), \
            int(at.sum())
        a.n_frozen = int(frozen.sum())

        # position inside the segment, and whether the next quiet pair is the
        # next row of the file
        pos = np.arange(n) - np.repeat(seg_start, seg_count)
        cnt = np.repeat(seg_count, seg_count)
        has_next = pos < cnt - 1
        contig = np.zeros(n, dtype=bool)
        contig[:-1] = (cur[1:] == cur[:-1] + 1)
        contig &= has_next

        # ---- 1. the month after -----------------------------------------
        def after(mask):
            m = mask & contig
            idx = np.flatnonzero(m)
            s = sched[idx + 1]
            good = s > 0
            r = obs[idx + 1][good] / s[good]
            return np.histogram(r, bins=R_EDGES)[0].tolist(), int(good.sum())

        a.after_frozen, a.after_frozen_n = after(frozen)
        a.after_at, a.after_at_n = after(at)

        # ---- 2. recovery lag ---------------------------------------------
        # cumulative deviation from the start of the segment, inclusive
        cum = np.cumsum(dev)
        base = np.repeat(cum[seg_start] - dev[seg_start], seg_count)
        C = cum - base                       # C[j] = sum of dev, start..j
        pre = np.empty(n)
        pre[:] = C - dev                     # C[j-1], and 0 at a segment start
        tol = np.maximum(REC_FLOOR, REC_FRAC * np.abs(sched))

        fidx = np.flatnonzero(frozen)
        lag = np.zeros(fidx.size, dtype=np.int8)      # 0 means not yet recovered
        room = cnt[fidx] - 1 - pos[fidx]              # months left in segment
        for m in range(1, MAX_LAG + 1):
            live = (lag == 0) & (room >= m)
            if not live.any():
                break
            j = fidx[live]
            ok = np.abs(C[j + m] - pre[j]) <= tol[j]
            sel = np.flatnonzero(live)[ok]
            lag[sel] = m
        a.lag_hist = [int((lag == m).sum()) for m in range(1, MAX_LAG + 1)]
        a.lag_none_room = int(((lag == 0) & (room >= MAX_LAG)).sum())
        a.lag_censored = int(((lag == 0) & (room < MAX_LAG)).sum())
        a.lag_n = int(fidx.size)

        # ---- 3. the segment net ------------------------------------------
        sdev = np.add.reduceat(dev, seg_start)
        ssch = np.add.reduceat(sched, seg_start)
        seg_frozen = np.add.reduceat(frozen.astype(np.int64), seg_start) > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            net = np.where(ssch > 0, sdev / ssch, np.nan)
        a.net_frozen = qs(net[seg_frozen])
        a.net_clean = qs(net[~seg_frozen])
        a.n_seg_frozen = int(seg_frozen.sum())
        # how much of a segment's net is explained by never-recovered freezes
        a.net_frozen_absmed = float(np.nanmedian(np.abs(net[seg_frozen])))
        a.net_clean_absmed = float(np.nanmedian(np.abs(net[~seg_frozen])))

        # ---- 4. censoring -------------------------------------------------
        a.frozen_last = int((frozen & ~has_next).sum())
        a.frozen_gap = int((frozen & has_next & ~contig).sum())

        # ---- assistance, repaired ----------------------------------------
        assist = c.row["assist"][:][cur]
        SEVEN = ord("7")
        for lab, m in (("below", below), ("above", above), ("frozen", frozen)):
            v = assist[m]
            setattr(a, f"as7_{lab}", int((v == SEVEN).sum()))
            setattr(a, f"asreal_{lab}",
                    int(((v != SEVEN) & (v != K.U8_NA)).sum()))
            setattr(a, f"asblank_{lab}", int((v == K.U8_NA).sum()))
            setattr(a, f"asn_{lab}", int(v.size))
    finally:
        c.close()
    return a


def render(archs: list[Arch]) -> str:
    L: list[str] = []
    A = L.append
    A("# B8 C8-1f: is the frozen month paid back the next month?\n")
    A("Generated by `experiments/b8_c8_1f_freeze_recovery.py` from the core "
      "table. Registered in `docs/b8_inputs_availability.md` §6.2.7.\n")
    A("**No prediction is read here and no outcome terminates the stage.**\n")

    A("\n## 0. The population\n")
    A("Same quiet-month filter and modal-cluster estimator as C8-1e, so these "
      "counts must match its §0 and its frozen-balance column.\n")
    A("| archive | quiet months | segments | below | frozen, balance did not "
      "move | of below |")
    A("|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.n:,} | {a.n_seg:,} | {a.n_below:,} | "
          f"{a.n_frozen:,} | {pct(a.n_frozen, a.n_below)} |")

    A("\n## 1. The month after a freeze\n")
    A("`observed fall / scheduled principal` on the **immediately next row** of "
      "the file, when that row is also a quiet month. **A mass at 2.00 is one "
      "freeze paid back.** The at-mode rows are the control: whatever shape "
      "they show is the estimator, not the freeze.\n")
    A("| archive | after | n | " + " | ".join(R_LABELS) + " |")
    A("|---|---|---|" + "---|" * len(R_LABELS))
    for a in archs:
        A(f"| {a.name} | **a freeze** | {a.after_frozen_n:,} | "
          + " | ".join(f"{v:,}" for v in a.after_frozen) + " |")
        A(f"| {a.name} | an at-mode month | {a.after_at_n:,} | "
          + " | ".join(f"{v:,}" for v in a.after_at) + " |")

    A("\n**Rates for the two bins that decide it.**\n")
    A("| archive | after | at 1.00 | rate | at 2.00 | rate |")
    A("|---|---|---|---|---|---|")
    for a in archs:
        for lab, h, nn in (("**a freeze**", a.after_frozen, a.after_frozen_n),
                           ("an at-mode month", a.after_at, a.after_at_n)):
            A(f"| {a.name} | {lab} | {h[3]:,} | {pct(h[3], nn)} | {h[6]:,} | "
              f"{pct(h[6], nn)} |")

    A("\n## 2. Recovery lag\n")
    A(f"Inside a segment, the cumulative `sum(observed - scheduled)` returns to "
      f"its pre-freeze level after how many months. Recovered means within "
      f"{REC_FRAC:.0%} of one scheduled principal, floored at "
      f"${REC_FLOOR:.2f}. **This tolerance is a choice, not a measurement.**\n")
    A("| archive | freezes | lag 1 | rate | 2 | 3 | 4 | 5 | 6 | not by 6, room "
      "to look | censored, segment ended |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in archs:
        h = a.lag_hist
        A(f"| {a.name} | {a.lag_n:,} | **{h[0]:,}** | **{pct(h[0], a.lag_n)}** "
          f"| {h[1]:,} | {h[2]:,} | {h[3]:,} | {h[4]:,} | {h[5]:,} | "
          f"{a.lag_none_room:,} | {a.lag_censored:,} |")

    A("\n## 3. The segment net, which is what `omega` accumulates\n")
    A("`sum(observed - scheduled) / sum(scheduled)` over a whole segment. "
      "**A timing shuffle nets to zero here. A level shift does not.** "
      "Segments carrying a freeze against segments carrying none.\n")
    A("| archive | segments | p10 | p25 | median | p75 | p90 | median of the "
      "absolute value |")
    A("|---|---|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} carrying a freeze | {a.n_seg_frozen:,} | "
          + " | ".join(f"{v:.4f}" for v in a.net_frozen)
          + f" | {a.net_frozen_absmed:.4f} |")
        A(f"| {a.name} no freeze | {a.n_seg - a.n_seg_frozen:,} | "
          + " | ".join(f"{v:.4f}" for v in a.net_clean)
          + f" | {a.net_clean_absmed:.4f} |")

    A("\n## 4. Censoring, and the loop window\n")
    A("A freeze whose compensator cannot be seen is not evidence that there is "
      "none.\n")
    A("| archive | freezes | at the last quiet month of its segment | rate | "
      "next quiet month is not the next row | rate |")
    A("|---|---|---|---|---|---|")
    for a in archs:
        A(f"| {a.name} | {a.n_frozen:,} | {a.frozen_last:,} | "
          f"{pct(a.frozen_last, a.n_frozen)} | {a.frozen_gap:,} | "
          f"{pct(a.frozen_gap, a.n_frozen)} |")

    A("\n**Share of freezes whose compensator sits inside a window of L "
      "months**, read off §2's lag histogram. This is the fraction that cancels "
      "inside a loop of that length, and one minus it bounds the boundary "
      "cases.\n")
    A("| archive | " + " | ".join(f"L = {w}" for w in WINDOWS) + " |")
    A("|---|" + "---|" * len(WINDOWS))
    for a in archs:
        row = []
        for w in WINDOWS:
            k = min(w - 1, MAX_LAG)
            row.append(pct(sum(a.lag_hist[:k]), a.lag_n))
        A(f"| {a.name} | " + " | ".join(row) + " |")

    A("\n## 5. Field 102, repaired\n")
    A("C8-1e counted this field as set whenever it was non-blank. "
      "`HANDOFF_B8.md` §3 records that **`7` means none of the above and is not "
      "data**, so that column measured whether the field was populated. The "
      "three states are separated here.\n")
    A("| archive | side | n | code `7` | rate | a real plan | rate | blank |")
    A("|---|---|---|---|---|---|---|---|")
    for a in archs:
        for lab in ("below", "above", "frozen"):
            nn = getattr(a, f"asn_{lab}")
            A(f"| {a.name} | {lab} | {nn:,} | {getattr(a, f'as7_{lab}'):,} | "
              f"{pct(getattr(a, f'as7_{lab}'), nn)} | "
              f"{getattr(a, f'asreal_{lab}'):,} | "
              f"{pct(getattr(a, f'asreal_{lab}'), nn)} | "
              f"{getattr(a, f'asblank_{lab}'):,} |")

    A("\n## What this does not decide\n")
    A("- **It does not name the mechanism.** A balance that freezes and catches "
      "up is consistent with a posting cut-off, with a servicer reporting the "
      "prior month's figure, and with other things. The shape is what is "
      "measured.")
    A("- **It does not decide the B8-0a(i) tolerance**, it supplies the counts.")
    A("- The recovery tolerance in §2 is a construction choice and is stated "
      "with the table rather than buried.")
    A("- Recovery is looked for **inside a segment only**, so a freeze in the "
      "month before a modification is censored by construction. §4 counts "
      "those.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def selftest() -> int:
    """A hand-built segment with a known freeze and a known catch-up."""
    fails = []
    B, RATE, N = 200000.0, 6.5, 360
    i = RATE / 1200.0
    P = float(K.level_payment([B], [RATE], [N])[0])

    bal, obs, sch = B, [], []
    FREEZE = 10
    for k in range(30):
        s = P - bal * i
        sch.append(s)
        if k == FREEZE:
            obs.append(0.0)                    # balance does not move
        elif k == FREEZE + 1:
            obs.append(s + sch[FREEZE])        # both months' principal at once
            bal -= sch[FREEZE]
        else:
            obs.append(s)
        bal -= s
    obs = np.array(obs)
    sch = np.array(sch)
    dev = obs - sch
    C = np.cumsum(dev)
    pre = C - dev

    if abs(C[FREEZE] - pre[FREEZE] + sch[FREEZE]) > 1e-6:
        fails.append("the freeze did not move the cumulative deviation")
    if abs(C[FREEZE + 1] - pre[FREEZE]) > 1e-6:
        fails.append(f"lag-1 recovery not exact: "
                     f"{C[FREEZE + 1] - pre[FREEZE]:.6f}")
    if abs(obs[FREEZE + 1] / sch[FREEZE + 1] - 2.0) > 0.01:
        fails.append(f"the month after did not read 2.00: "
                     f"{obs[FREEZE + 1] / sch[FREEZE + 1]:.4f}")
    if abs(dev.sum() / sch.sum()) > 1e-9:
        fails.append(f"a compensated segment did not net to zero: "
                     f"{dev.sum() / sch.sum():.3e}")

    # and a permanent shortfall must NOT net to zero
    obs2 = obs.copy()
    obs2[FREEZE + 1] = sch[FREEZE + 1]        # never caught up
    dev2 = obs2 - sch
    if abs(dev2.sum() / sch.sum()) < 1e-3:
        fails.append("an uncompensated freeze netted to zero")

    print(f"  compensated segment nets {dev.sum() / sch.sum():+.2e}, "
          f"uncompensated nets {dev2.sum() / sch.sum():+.4f}", file=sys.stderr)
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
