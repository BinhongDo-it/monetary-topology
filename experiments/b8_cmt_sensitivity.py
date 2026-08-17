#!/usr/bin/env python3
"""B8: does the curve-construction choice move `r` more than the noise floor?

Registered in ``docs/b8_fannie_slice.md`` §16.11. **This measures whether the
two construction choices are load bearing. It does not make them.**

**Why measure before ruling.** `b8_cmt_availability.md` §3 says **62.5 per cent**
of triangle-completing modifications carry a remaining term past the longest
published tenor and **57.5 per cent** are past it by five years or more, so the
"what happens beyond 30 years" rule is not an edge case, it applies to most of
the sample and hardest to the term-extension modifications the stage exists to
measure. A rule that big has to be chosen on evidence.

**The comparison that decides it.** `b8_omega.py` P2 already showed the whole
curve level moving thirty-fold shifts `r` by about `7e-6` on a deferred balloon,
while the B8-0a(i-b) noise floor runs `6.5e-06` to `6.7e-05` by archive
(`b8_inputs_availability.md` §6.2.11.4). **If the spread across construction
rules sits below that floor, the choice is not load bearing and any rule
serves, which is itself a result. If it sits above, the choice must be ruled and
this file supplies the magnitude.**

**What is computed.** For each triangle-completing modification: the balance and
note rate at the modification row give a level payment over the remaining legal
term `n`; `V` is that stream discounted on the Treasury curve at horizon `n`.
`log V` is recomputed under each rule and the spread across rules is the
quantity that reaches `r`. **The spread, not the level**, because a common shift
cancels in `r` and a horizon-dependent one does not.

**Treasury governs.** FRED carries values in the 47 months Treasury publishes no
30-year for, and since the CMT is defined by its issuer, values the issuer does
not publish are not that curve. Those months are run with the 20-year as the
longest available tenor and are reported separately.

**No prediction is read here and no outcome terminates the stage.**

Usage::

    python experiments/b8_cmt_sensitivity.py --selftest
    python experiments/b8_cmt_sensitivity.py
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402
import b8_cmt_fetch as F  # noqa: E402
import b8_triangles as T  # noqa: E402

OUT = K.ROOT / "results" / "b8_cmt_sensitivity.md"

#: B8-0a(i-b), `b8_inputs_availability.md` §6.2.11.4. The bar this has to clear
#: to be load bearing. Per archive, median absolute loop sum.
FLOOR = {"2002Q1": 6.469e-06, "2006Q1": 7.909e-06, "2007Q1": 7.679e-06,
         "2012Q1": 1.138e-05, "2017Q1": 2.042e-05, "2019Q1": 6.707e-05}

#: Interpolation rules for a horizon between two published tenors.
INTERP = ["linear_in_tenor", "linear_in_log_tenor"]

#: Rules for a horizon past the longest published tenor. `cap` is the
#: conservative one and `linear_*` continue the last published segment.
BEYOND = ["cap", "linear_in_tenor", "linear_in_log_tenor"]


def month_curve(src: dict) -> dict:
    """{month_index: [(tenor_months, yield_pct)]}, ascending, monthly mean."""
    acc = defaultdict(dict)
    for (mi, lab), vals in src.items():
        n = F.TENOR_MONTHS.get(lab)
        if n is None or not vals:
            continue
        acc[mi][n] = sum(vals) / len(vals)
    return {mi: sorted(d.items()) for mi, d in acc.items()}


def yield_at(pts, n: int, interp: str, beyond: str) -> float | None:
    """The curve read at horizon ``n`` months under one pair of rules."""
    if not pts:
        return None
    ts = [t for t, _ in pts]
    ys = [y for _, y in pts]
    if n <= ts[0]:
        return ys[0]
    if n <= ts[-1]:
        for k in range(1, len(ts)):
            if n <= ts[k]:
                t0, t1, y0, y1 = ts[k - 1], ts[k], ys[k - 1], ys[k]
                if interp == "linear_in_log_tenor":
                    w = (math.log(n) - math.log(t0)) / (math.log(t1)
                                                        - math.log(t0))
                else:
                    w = (n - t0) / (t1 - t0)
                return y0 + w * (y1 - y0)
    # past the longest published tenor
    if beyond == "cap" or len(ts) < 2:
        return ys[-1]
    t0, t1, y0, y1 = ts[-2], ts[-1], ys[-2], ys[-1]
    if beyond == "linear_in_log_tenor":
        w = (math.log(n) - math.log(t0)) / (math.log(t1) - math.log(t0))
    else:
        w = (n - t0) / (t1 - t0)
    return y0 + w * (y1 - y0)


def pv(payment: float, n: int, y_pct: float) -> float:
    """PV of a level monthly payment over ``n`` months at an annual par yield."""
    i = y_pct / 100.0 / 12.0
    if abs(i) < 1e-12:
        return payment * n
    return payment * (1.0 - (1.0 + i) ** (-n)) / i


def level_payment(balance: float, rate_pct: float, n: int) -> float:
    i = rate_pct / 100.0 / 12.0
    if n <= 0:
        return 0.0
    if abs(i) < 1e-12:
        return balance / n
    return balance * i / (1.0 - (1.0 + i) ** (-n))


# ---------------------------------------------------------------------------


def collect_mods(names):
    """(archive, month_index, remaining term, balance, note rate) per mod."""
    out = []
    for name in names:
        with K.Core(name) as c:
            t = T.triangles(c)
            tri = t["triangle"]
            period = c.row["period"].astype(np.int32)
            rem = c.row["rem_legal"].astype(np.int32)
            upb = c.row["upb"].astype(np.int64)
            nib = c.row["nib_upb"].astype(np.int64)
            rate = c.row["rate"].astype(np.int32)
            is_mod = c.row["mod_flag"] == K._Y
            first_mod = T._first_pos_per_loan(c, is_mod)
            sel = tri & (first_mod >= 0)
            rows = first_mod[sel]
            mi, rl, ub, nb, rt = (period[rows], rem[rows], upb[rows],
                                  nib[rows], rate[rows])
            # C8's answer: field 12 includes field 63, so the interest-bearing
            # balance is 12 minus 63. A blank 63 is zero deferred, not missing.
            defer = np.where(nb == K.U32_NA, 0, nb)
            bal = (ub - defer).astype(np.float64) / 100.0
            ok = ((mi != K.U16_NA) & (rl != K.U16_NA) & (rl > 0)
                  & (ub != K.U32_NA) & (rt != K.U16_NA) & (bal > 0))
            for a, b, d, e in zip(mi[ok].tolist(), rl[ok].tolist(),
                                  bal[ok].tolist(),
                                  (rt[ok].astype(np.float64) / 1000.0)
                                  .tolist()):
                out.append((name, a, b, d, e))
        print(f"  {name}: {int(ok.sum()):,} priceable modifications",
              file=sys.stderr)
    return out


def run(names) -> int:
    tre, _ = F.load_treasury()
    if not tre:
        print("no Treasury curve on disk. Run: "
              "python experiments/b8_cmt_fetch.py fetch", file=sys.stderr)
        return 1
    curves = month_curve(tre)
    mods = collect_mods(names)
    if not mods:
        print("no priceable modifications", file=sys.stderr)
        return 1

    rules = [(i, b) for i in INTERP for b in BEYOND]
    per_arch = defaultdict(list)
    per_arch_beyond = defaultdict(list)
    n_no_curve = 0
    n_short = 0
    n_gap_month = 0

    longest = {}
    for mi, pts in curves.items():
        longest[mi] = pts[-1][0] if pts else 0

    for name, mi, n, bal, rate_pct in mods:
        pts = curves.get(mi)
        if not pts:
            n_no_curve += 1
            continue
        if longest[mi] < 360:
            n_gap_month += 1
        pay = level_payment(bal, rate_pct, n)
        logs = []
        for interp, beyond in rules:
            y = yield_at(pts, n, interp, beyond)
            if y is None:
                continue
            v = pv(pay, n, y)
            if v <= 0:
                continue
            logs.append(math.log(v))
        if len(logs) < 2:
            continue
        spread = max(logs) - min(logs)
        per_arch[name].append(spread)
        if n > longest[mi]:
            per_arch_beyond[name].append(spread)
        else:
            n_short += 1

    L = []
    A = L.append
    A("# B8: is the curve-construction choice load bearing?\n")
    A("Generated by `experiments/b8_cmt_sensitivity.py`. Registered in "
      "`docs/b8_fannie_slice.md` §16.11.\n")
    A("**This measures whether the choice matters. It does not make the "
      "choice.**\n")
    A(f"Rules crossed: interpolation {INTERP}, beyond the longest tenor "
      f"{BEYOND}, so {len(rules)} constructions per modification. The "
      "reported quantity is the **spread of `log V` across all of them**, "
      "which is what reaches `r`; a construction that shifts every horizon "
      "equally cancels in `r` and is not counted here.\n")
    A("**Reads no prediction.**\n")

    A("\n## 1. The spread against the B8-0a(i-b) noise floor\n")
    A("The floor is the median absolute loop sum on the same archive "
      "(`b8_inputs_availability.md` §6.2.11.4). **A spread below it means the "
      "choice cannot be seen through the measurement and any rule serves. "
      "Above it, the choice must be ruled.**\n")
    A("| archive | priced | **spread p50** | p90 | p99 | max | "
      "**(i-b) floor** | **p50 / floor** | **load bearing?** |")
    A("|---|---|---|---|---|---|---|---|---|")
    for name in names:
        v = np.asarray(per_arch.get(name, []))
        if not v.size:
            A(f"| {name} | 0 | - | - | - | - | - | - | - |")
            continue
        q = np.quantile(v, [.5, .9, .99])
        fl = FLOOR.get(name, float("nan"))
        A(f"| {name} | {v.size:,} | **{q[0]:.3e}** | {q[1]:.3e} | "
          f"{q[2]:.3e} | {v.max():.3e} | {fl:.3e} | "
          f"**{q[0] / fl:.2f}** | "
          f"**{'YES' if q[0] > fl else 'no'}** |")

    A("\n## 2. Only the horizons that actually run past the longest tenor\n")
    A("§1 pools every modification, and one whose horizon is inside the "
      "published tenors has **zero** spread from the `beyond` rule by "
      "construction, which drags the pooled median down. This table is the "
      "population the rule actually applies to.\n")
    A("| archive | past the longest tenor | **spread p50** | p90 | max | "
      "**p50 / floor** | **load bearing?** |")
    A("|---|---|---|---|---|---|---|")
    for name in names:
        v = np.asarray(per_arch_beyond.get(name, []))
        if not v.size:
            A(f"| {name} | 0 | - | - | - | - | - |")
            continue
        q = np.quantile(v, [.5, .9])
        fl = FLOOR.get(name, float("nan"))
        A(f"| {name} | {v.size:,} | **{q[0]:.3e}** | {q[1]:.3e} | "
          f"{v.max():.3e} | **{q[0] / fl:.2f}** | "
          f"**{'YES' if q[0] > fl else 'no'}** |")

    A("\n## 3. Accounting\n")
    A(f"- modifications with no curve for their month: **{n_no_curve:,}**\n"
      f"- modifications in a month whose longest published tenor is under 30 "
      f"years, that is inside the 2002-03..2006-01 gap: **{n_gap_month:,}**\n"
      f"- modifications whose horizon is inside the published tenors, where "
      f"the `beyond` rule contributes nothing: **{n_short:,}**\n")

    A("\n## What this does not decide\n")
    A("- **It does not choose either rule.** It says whether the choice can "
      "be seen through the measurement.")
    A("- **It does not price a single loop.** `V` here is a level annuity on "
      "the modification row, which is the horizon the rule acts on, not the "
      "full `omega` construction.")
    A("- **It says nothing about the 47-month gap's own rule.** In those "
      "months the longest tenor is the 20-year and the extrapolation distance "
      "is longer; §3 counts them and they are pooled above, not isolated.")
    A("- It reads no prediction.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


def selftest() -> int:
    """The pricing primitives, on cases whose answers are arithmetic."""
    fails = []
    # a level payment discounted at its own note rate returns the balance
    for bal, r, n in ((200000.0, 6.0, 360), (100000.0, 3.5, 180)):
        p = level_payment(bal, r, n)
        back = pv(p, n, r)
        if abs(back - bal) > 1e-6:
            fails.append(f"pv(level_payment) = {back}, want {bal}")
    # zero rate is the undiscounted sum
    if abs(pv(100.0, 12, 0.0) - 1200.0) > 1e-9:
        fails.append("zero-rate PV")

    pts = [(12, 1.0), (120, 3.0), (240, 4.0), (360, 4.5)]
    # a published tenor reads its own value under every rule
    for interp in INTERP:
        for beyond in BEYOND:
            for t, y in pts:
                got = yield_at(pts, t, interp, beyond)
                if abs(got - y) > 1e-12:
                    fails.append(f"{interp}/{beyond} at {t}: {got} != {y}")
    # cap is flat past the end, the others are not
    cap = yield_at(pts, 480, "linear_in_tenor", "cap")
    lin = yield_at(pts, 480, "linear_in_tenor", "linear_in_tenor")
    log = yield_at(pts, 480, "linear_in_tenor", "linear_in_log_tenor")
    if abs(cap - 4.5) > 1e-12:
        fails.append(f"cap at 480 = {cap}, want 4.5")
    if not (lin > cap and log > cap):
        fails.append("both extrapolations should continue an upward segment")
    if abs(lin - log) < 1e-9:
        fails.append("the two extrapolations coincide, so the beyond rule is "
                     "untested by this curve")
    # the two interpolations must differ strictly between tenors
    a = yield_at(pts, 200, "linear_in_tenor", "cap")
    b = yield_at(pts, 200, "linear_in_log_tenor", "cap")
    if abs(a - b) < 1e-9:
        fails.append("the two interpolations coincide at 200 months, so the "
                     "interp rule is untested")
    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print(f"selftest: ok  (480m: cap {cap:.4f}, linear {lin:.4f}, "
          f"log {log:.4f}; 200m: linear {a:.4f}, log {b:.4f})",
          file=sys.stderr)
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
                   if p.is_dir() and (p / "manifest.json").exists()
                   and not p.name.startswith("209")) if root.exists() else []
    if args.only:
        names = [n for n in names if n in set(args.only)]
    if not names:
        print("no core table.", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(run(names))


if __name__ == "__main__":
    main()
