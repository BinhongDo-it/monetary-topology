#!/usr/bin/env python3
"""B8's residue, in one pass. §21.6's discriminant, and nothing else.

**Three of the five things called "residue" are already ruled not to run, with
reasons on record, and re-reading them as pending was an error.**

| item | status |
|---|---|
| C13-b | registered with a **trigger condition** (`b8_inputs_availability.md` §6.6.20.5): it runs when excluding those 1,276 loans becomes load-bearing. They are a small part of 85,308 loops. **The trigger has not fired**, so this is not pending, it is conditional |
| C10-5 | §6.6.11's own text: **"不做 C10-5"** -- it needs a payment estimator the file does not carry. A declined test, not an owed one |
| §19.2 secondary pairs | §19.2's own text: **"本节不跑，登记"**, because timing contrasts are blocked by the "the two endpoints have different arrears histories" objection, which §14.4 answered by moving B8-3's primary pair to the institutional contrast |

What is genuinely owed is two things, and only one of them needs new code:

1. **§21.6's leg-1 discriminant**, this file.
2. **`b8_cmt_sensitivity2`'s re-run** (O21's residue), which is that script's own
   `run` and needs nothing new here.

--------------------------------------------------------------------------
§21.6, the discriminant, verbatim
--------------------------------------------------------------------------

B8-1 measured leg 1 against its closed form and found the gap is **a month
count, not a proportion**: `n1 - eff` is 4.80, 4.97, 4.97, 4.93, 4.99, 3.98
across six archives whose `n1` runs from 11 to 16. A balance drifting during
delinquency would give a ratio; a constant integer offset does not. So the
reading is that **about five months inside leg 1 do not behave like missed
months**, and the natural candidate is that a payment lands in them: §17's
window is defined on `current`, not on whether anything was paid, and a loan
perpetually one month behind is never `current` while paying every month.

§21.6 registered the test:

> count, inside each leg-1 window, the months where `B(t) ~ B(t-1)` (flat, no
> payment) and the months where `B(t) ~ f(B(t-1))` (paid on schedule).
> **If the flat count equals `eff`, this is settled.**

Usage:

    python experiments/b8_residue.py run
    python experiments/b8_residue.py run --only 2019Q1
    python experiments/b8_residue.py selftest
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_omega as W                                           # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_loop_omega as Z8                                     # noqa: E402
import b8_cache as C                                           # noqa: E402

OUT = K.ROOT / "results" / "b8_residue.md"
COLS = Z8.COLS + ["zero_bal"]

#: A month counts as flat when the balance moved by less than this fraction of
#: itself. **Source, not a choice**: B8-0b measured the floor at half a cent
#: over a median balance of 165,000, which is 3.03e-08, so anything at that
#: scale is field 12's quantisation and anything above it is a real move.
FLAT_TOL = 1e-7

#: A month counts as on-schedule when the balance landed within this fraction
#: of `f(B(t-1)) = B(t-1) * (1 + i/1200) - P`. Looser than `FLAT_TOL` because
#: the contract payment is itself an estimate carried per contract period.
SCHED_TOL = 1e-4


def classify_leg1(c: K.Core, lp: dict, pay_row) -> dict:
    """Per loop, how many of leg 1's months were flat and how many were paid.

    Leg 1 is `[t_A + 1, t_M - 1]`, so the months examined are those rows and
    the comparison for each is against the row before it.

    **Three outcomes, and the third is the point.** A month is `flat` when the
    balance did not move, `sched` when it moved to where the contract says a
    payment puts it, and `other` when it did neither. If §21.6's reading is
    right, `flat` is `eff` and `sched` accounts for the missing five months.
    If `other` carries them, the delinquent balance is doing something neither
    model describes and that is a different finding.
    """
    tA, tM = lp["t_A"], lp["t_M"]
    bal_c, _z = K.zero_interest_split(c)
    bal = bal_c.astype(np.float64) / 100.0
    rate = c.row["rate"][:].astype(np.float64) / 1000.0
    pay = np.asarray(pay_row, dtype=np.float64)

    prev = np.empty(c.n_rows, dtype=np.float64)
    prev[1:] = bal[:-1]
    prev[0] = np.nan
    first = np.zeros(c.n_rows, bool)
    first[c.row_start.astype(np.int64)] = True
    prev[first] = np.nan

    with np.errstate(invalid="ignore", divide="ignore"):
        rel_flat = np.abs(bal - prev) / np.maximum(np.abs(prev), 1.0)
        sched = prev * (1.0 + rate / 1200.0) - pay
        rel_sched = np.abs(bal - sched) / np.maximum(np.abs(sched), 1.0)
    ok = np.isfinite(prev) & (prev > 0) & np.isfinite(bal)
    is_flat = ok & (rel_flat <= FLAT_TOL)
    is_sched = ok & ~is_flat & np.isfinite(sched) & (sched > 0) \
        & (rel_sched <= SCHED_TOL)
    is_other = ok & ~is_flat & ~is_sched

    pf = np.concatenate(([0], np.cumsum(is_flat.astype(np.int64))))
    ps = np.concatenate(([0], np.cumsum(is_sched.astype(np.int64))))
    po = np.concatenate(([0], np.cumsum(is_other.astype(np.int64))))
    pk = np.concatenate(([0], np.cumsum(ok.astype(np.int64))))

    def span(pre, a, b):                    # inclusive [a, b], b < a gives 0
        return pre[b + 1] - pre[a]

    lo, hi = tA + 1, tM - 1
    # **The loan-boundary guard above cannot fire, and that is asserted rather
    # than assumed.** Leg 1 starts at `t_A + 1` and `b8_loops.find_loops` keeps
    # `t_A` inside the loan, so a leg-1 window never opens on a loan's first
    # row. A mutation run showed removing the guard changes nothing, which
    # means it is either dead or untested; this counter decides which, and it
    # would fire if `find_loops` ever changed underneath.
    starts_first = int((first[np.minimum(lo, c.n_rows - 1)] & (lo <= hi)).sum())
    return {"flat": span(pf, lo, hi), "sched": span(ps, lo, hi),
            "other": span(po, lo, hi), "readable": span(pk, lo, hi),
            "n1": (tM - 1 - tA), "starts_first": starts_first}


def analyse(name: str, cache_root=None, pos=None, tab=None,
            core_root=None) -> dict:
    d = C.get(name, pos=pos, tab=tab, core_root=core_root or cache_root)
    s = d["sig"]
    c = K.Core(name, cols=COLS, cache_root=core_root or cache_root)
    try:
        q0 = K.quiet_pairs(c)
        pid0 = W.contract_periods(c, fill=True)
        pay0, _kn, _pp = W.contract_payments(c, pid0, q0)
        lp = {"t_A": np.asarray(s["t_A"]), "t_M": np.asarray(s["t_M"])}
        cl = classify_leg1(c, lp, pay0)
    finally:
        c.close()

    m = (s["measurable"].astype(bool) & (s["arm"] == L.ARM_MOD)
         & (np.asarray(s["n1"]) > 0))
    l1 = np.asarray(s["leg1"], float)[m]
    l1c = np.asarray(s["l1_closed"], float)[m]
    n1 = np.asarray(s["n1"], float)[m]
    good = np.isfinite(l1) & np.isfinite(l1c) & (np.abs(l1c) > 0)
    eff = np.full(l1.size, np.nan)
    eff[good] = n1[good] * l1[good] / l1c[good]
    sf = int(cl.pop("starts_first"))
    out = {k_: np.asarray(v)[m] for k_, v in cl.items()}
    return {"name": name, "n": int(m.sum()), "eff": eff,
            "starts_first": sf, **out}


def _f(x, k=3):
    return "nan" if not np.isfinite(x) else f"{x:.{k}f}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8 residue: §21.6's leg-1 discriminant\n")
    A("Generated by `experiments/b8_residue.py`. Registered in "
      "`docs/b8_fannie_slice.md` §21.6, written before this ran.\n")
    A("**Three of the five things called residue were already ruled not to "
      "run**, with reasons on record: C13-b has a trigger condition that has "
      "not fired, C10-5 was declined for want of a payment estimator, and "
      "§19.2's secondary pairs were declined because timing contrasts are "
      "blocked by the objection §14.4 answered. **Only this and "
      "`b8_cmt_sensitivity2`'s re-run were owed.**\n")
    A("B8-1 found leg 1 short of its closed form by a **constant integer "
      "month count** (`n1 - eff` = 4.80, 4.97, 4.97, 4.93, 4.99, 3.98) rather "
      "than by a proportion. §21.6's reading: about five months inside leg 1 "
      "are not missed months, most likely because a payment landed in them. "
      "§17's window is defined on `current`, **not on whether anything was "
      "paid**, and a loan perpetually one month behind is never `current` "
      "while paying every month.\n")
    A(f"`flat` is `|B(t) - B(t-1)|` within {FLAT_TOL:g} of the balance, whose "
      "source is B8-0b's floor (half a cent over a median balance of 165,000 "
      f"is 3.03e-08). `sched` is within {SCHED_TOL:g} of "
      "`B(t-1)*(1+i/1200) - P`. **`other` is neither, and if it carries the "
      "gap the reading is wrong and something else is happening.**\n")
    if not rows:
        return "\n".join(Ls) + "\n_no data_\n"

    A("\n## 1. The counts\n")
    A("`crosses` counts leg-1 windows that open on a loan's first row. It "
      "must be zero: `find_loops` keeps `t_A` inside the loan. **It is "
      "printed because a guard that cannot fire and a guard that is not "
      "tested look identical.**\n")
    A("| archive | loops | median `n1` | median `eff` | **median flat** | "
      "median sched | median other | unreadable | crosses |")
    A("|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        unread = np.median(a["n1"] - a["readable"]) if a["n"] else np.nan
        A(f"| {a['name']} | {a['n']:,} | "
          f"{_f(float(np.median(a['n1'])), 1)} | "
          f"{_f(float(np.nanmedian(a['eff'])))} | "
          f"**{_f(float(np.median(a['flat'])), 1)}** | "
          f"{_f(float(np.median(a['sched'])), 1)} | "
          f"{_f(float(np.median(a['other'])), 1)} | "
          f"{_f(float(unread), 1)} | {a['starts_first']} |")

    A("\n## 2. The verdict\n")
    A("§21.6: **if the flat count equals `eff`, this is settled.** The "
      "comparison is per loop, not per median, because two medians can agree "
      "while no loop does.\n")
    A("| archive | loops compared | **flat == round(eff)** | share | "
      "median `flat - eff` | **settled** |")
    A("|---|---|---|---|---|---|")
    tally = 0
    for a in rows:
        g = np.isfinite(a["eff"])
        if not g.any():
            continue
        hit = int((np.abs(a["flat"][g] - a["eff"][g]) < 0.5).sum())
        share = hit / int(g.sum())
        ok = share >= 0.9
        tally += ok
        A(f"| {a['name']} | {int(g.sum()):,} | **{hit:,}** | {share:.4f} | "
          f"{_f(float(np.median(a['flat'][g] - a['eff'][g])))} | "
          f"**{'yes' if ok else 'no'}** |")
    A(f"\n**{tally} of {len(rows)} archives settle.** Where they do, §21.6's "
      "open reading closes: leg 1's shortfall against the closed form is the "
      "months in which a payment landed while the loan was not `current`, and "
      "**nothing in B8-1's verdict moves**, because §21.6 already recorded "
      "that removing a quantity 1.2 to 1.6 times the measured leg 1 changed "
      "the net ratio by at most 11.5 per cent.\n")

    A("\n## What this does not decide\n")
    A("- **C13-b**, whose trigger has not fired.")
    A("- **C10-5**, declined for want of a payment estimator.")
    A("- **§19.2's secondary pairs**, declined because §14.4 replaced the "
      "timing contrast with the institutional one.")
    A("- **O21's residue**: `b8_cmt_sensitivity2`'s re-run is its own script.\n")
    return "\n".join(Ls) + "\n"


def selftest() -> int:
    fails: list[str] = []
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    cr = root / "cache"
    K.build_archive(zp, force=True, cache_root=cr)
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as c:
        months = np.unique(c.row["period"][:])
        months = months[months != K.U16_NA]
        pos, tab = Z8._flat_curve(months)
    a = analyse(zp.stem, cache_root=root / "loopcache", pos=pos, tab=tab,
                core_root=cr)
    if a["starts_first"] != 0:
        fails.append(f"{a['starts_first']} leg-1 windows open on a loan's "
                     "first row. `find_loops` used to keep `t_A` inside the "
                     "loan, so the previous-row array is being read across a "
                     "loan boundary")
    if a["n"] == 0:
        fails.append("no measurable modification loop with a leg 1 on the "
                     "fixture, so nothing below is tested")
    else:
        # **the fixture's delinquent runs are flat by construction** (pit 10),
        # so every leg-1 month must classify flat and none as sched or other.
        # If that ever stops holding, the classifier changed, not the world.
        if int(a["sched"].sum()) or int(a["other"].sum()):
            fails.append(f"the fixture's leg 1 classified "
                         f"{int(a['sched'].sum())} scheduled and "
                         f"{int(a['other'].sum())} other months; its "
                         "delinquent runs are flat on purpose")
        if not np.array_equal(a["flat"], a["n1"]):
            fails.append("flat months do not account for every leg-1 month on "
                         "a fixture whose runs are entirely flat")
        # and §21.6's own comparison must come out settled there, since the
        # fixture is the case the reading describes
        g = np.isfinite(a["eff"])
        if g.any() and not np.all(np.abs(a["flat"][g] - a["eff"][g]) < 0.5):
            fails.append("flat does not equal eff on a wholly flat fixture, "
                         "so the discriminant disagrees with itself")

    # -- the classifier, on rows built to be each of the three --------------
    # **A structural check cannot pin these three.** Each is driven with a
    # balance path whose class is known before the code runs. Two loans, so
    # the second loan's first row exercises the loan-boundary guard; a move of
    # one dollar on two hundred thousand, so the tolerance has something to
    # sit between; and an interest-only month, where flat and scheduled are
    # the same row and the priority between them decides the count.
    class _Fake:
        pass

    def _classify(bal, pay, tA, tM, rate=5.0):
        fk = _Fake()
        fk.n_rows = bal.size
        fk.row_start = np.array([0, 6], dtype=np.int64)
        fk.n_loans = 2
        fk.row = {"rate": np.full(bal.size, rate * 1000, dtype=np.uint16)}
        real = K.zero_interest_split
        try:
            K.zero_interest_split = lambda _c: (
                (bal * 100).astype(np.int64), np.zeros(bal.size, np.int64))
            return classify_leg1(fk, {"t_A": np.array(tA),
                                      "t_M": np.array(tM)},
                                 np.full(bal.size, pay))
        finally:
            K.zero_interest_split = real

    P = 1073.64
    B0 = 200000.0
    step = B0 * (1.0 + 5.0 / 1200.0) - P          # one scheduled month
    # loan 1 rows 0-5: flat, flat, one-dollar drop, scheduled, big drop
    # loan 2 rows 6-11: its first row must not read against row 5
    bal = np.array([B0, B0, B0, B0 - 1.0, step, 150000.0,
                    B0, B0, step, step, step, step])
    got = _classify(bal, P, [0, 6], [6, 12])
    # a window deliberately opened on loan 2's first row must be counted
    if _classify(bal, P, [0, 5], [6, 12])["starts_first"] != 1:
        fails.append("a leg-1 window opening on a loan's first row was not "
                     "counted, so the counter cannot report the condition it "
                     "exists to report")
    if got["starts_first"] != 0:
        fails.append("a window that does not open on a first row was counted "
                     "as one")
    if int(got["flat"][0]) != 2:
        fails.append(f"flat counted {int(got['flat'][0])}, expected 2")
    # **a one-dollar move on two hundred thousand is 5e-6**, above FLAT_TOL
    # and below a loose tolerance, so it is what makes the tolerance testable
    if int(got["other"][0]) != 2:
        fails.append(f"other counted {int(got['other'][0])}, expected 2: a "
                     f"one-dollar drop (5e-6 of the balance, above "
                     f"FLAT_TOL = {FLAT_TOL:g}) and a 25 per cent drop")
    if int(got["sched"][0]) != 1:
        fails.append(f"sched counted {int(got['sched'][0])}, expected 1")
    if int(got["flat"][0]) + int(got["sched"][0]) + int(got["other"][0]) \
            != int(got["readable"][0]):
        fails.append("the three classes do not partition the readable months")
    # **the loan boundary.** Loan 2 starts at row 6 with the same balance loan
    # 1 ended two rows above; if the previous-row array is not cut at the
    # boundary, row 6 reads against loan 1's last row and classifies.
    if int(got["readable"][1]) != 5:
        fails.append(f"loan 2 read {int(got['readable'][1])} months of its "
                     "five-month leg 1; its first row is being compared "
                     "against the previous loan's last row")
    # **flat and scheduled can be the same row.** An interest-only month has
    # `f(B) = B`, so both tests fire and the priority between them decides
    # whether the month is counted once or twice.
    io = np.array([B0] * 6 + [B0] * 6)
    g_io = _classify(io, B0 * 5.0 / 1200.0, [0, 6], [6, 12])
    if int(g_io["flat"][0]) != 5 or int(g_io["sched"][0]) != 0:
        fails.append(f"an interest-only run read {int(g_io['flat'][0])} flat "
                     f"and {int(g_io['sched'][0])} scheduled, expected 5 and "
                     "0. Both tests fire on those rows and `flat` must win, "
                     "or the months are counted twice and the classes stop "
                     "partitioning")
    if int(g_io["flat"][0]) + int(g_io["sched"][0]) + int(g_io["other"][0]) \
            != int(g_io["readable"][0]):
        fails.append("interest-only months are counted in two classes at once")
    # **a scheduled month must be seen as scheduled**, or `sched` is dead and
    # §21.6's candidate explanation cannot be confirmed or refuted
    b2 = np.empty(12)
    b2[0] = b2[6] = B0
    for i in list(range(1, 6)) + list(range(7, 12)):
        b2[i] = b2[i - 1] * (1.0 + 5.0 / 1200.0) - P
    g2 = _classify(b2, P, [0, 6], [6, 12])
    if int(g2["sched"][0]) != 5 or int(g2["flat"][0]) != 0:
        fails.append(f"a wholly on-schedule path read {int(g2['sched'][0])} "
                     f"scheduled and {int(g2['flat'][0])} flat, expected 5 "
                     "and 0; `sched` is the candidate explanation and a dead "
                     "`sched` column cannot confirm or refute it")

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. The counts", "## 2. The verdict"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    print(f"  fixture: {a['n']} loops, {int(a['flat'].sum())} flat months",
          file=sys.stderr)

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the three classes partition and `sched` is alive",
          file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: {a['n']:,} loops, median flat "
              f"{np.median(a['flat']):.1f} of {np.median(a['n1']):.1f}",
              file=sys.stderr)
    txt = render(rows)
    bad = K.check_markdown_tables(txt)
    if bad:
        for b in bad:
            print("MALFORMED " + b, file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt, encoding="utf-8")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["run", "selftest"])
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
    raise SystemExit(run(names))


if __name__ == "__main__":
    main()
