#!/usr/bin/env python3
"""C11: what field 108's deferred balance is, and whether field 12 contains it.

Registered in the B8 inputs register §6.6.13, **and the map from
outcome to disposition is written there before this ran**. Same standing as C8:
counting and amortisation arithmetic that settle a construction choice, asked
against the file rather than against a result. **Computes no ``omega`` and reads
no prediction.**

--------------------------------------------------------------------------
Why now
--------------------------------------------------------------------------

The deferral arm carries **35,659 loops** after C10-4 re-cut it onto field 108.
§14.1's ``V`` puts only field 63 in the balloon, and C10-4 measured that fields
63 and 108 never rise on the same row, so **``V`` has no balloon at all on that
arm** while a balloon is the single thing §14.4 says a deferral does. C8-1
settled "field 12 contains field 63"; nobody has asked the same of field 108.

--------------------------------------------------------------------------
C11-1 has two criteria and the fast one is not the load-bearing one
--------------------------------------------------------------------------

**Criterion A, the single-month difference.** ``Δ12 / 108`` at the deferral
onset, read as a modal cluster with ``b8_core.modal_cluster``, the same copy
C8-1c uses. A mode at +1, -1 or 0 says the deferred amount was added to the
balance, taken out of it, or reclassified inside it. **It is contaminated by
capitalisation in the same month** and C10-4 already measured that the balance
steps up on 94.3 to 99.5 per cent of these rows, so it is reported as the quick
reading and not as the answer.

**Criterion B, amortisation consistency, which decides.** C10-4 measured that
the note rate and the legal maturity both hold across 99.66 per cent of
deferral onsets, so **the contract payment cannot have changed**. Estimate that
payment from the quiet months *before* the deferral, then ask which reading of
the interest-bearing balance reproduces it *after*::

    A:  implied = (12p - 12) + 12p * i                 field 12 is the IB balance
    B:  ib = 12 - 108 ;  implied = (ibp - ib) + ibp * i

The one whose implied payment sits closer to the pre-deferral estimate is the
right reading. **If neither is close, that contradicts C10-4 and nothing is
ruled here**; §6.6.13.1 fixes that outcome in advance.

Usage::

    python experiments/b8_c11_deferred_balance.py selftest   # no real archive
    python experiments/b8_c11_deferred_balance.py run
    python experiments/b8_c11_deferred_balance.py run --only 2019Q1
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402
import b8_loops as L  # noqa: E402
import b8_omega as W  # noqa: E402

OUT = K.ROOT / "results" / "b8_c11_deferred_balance.md"

#: **The column list `run` opens with**, and the selftest opens the fixture with
#: the same one. Pit 30: a selftest that takes every column cannot see a column
#: missing here.
COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq", "mod_flag",
        "nib_upb", "defer_amt"]

#: A post-deferral quiet month is only usable if the loan has a pre-deferral
#: payment estimate drawn from at least this many quiet pairs. Same floor as
#: ``b8_omega.MIN_QUIET_FOR_PAYMENT``, cited rather than re-chosen.
MIN_QUIET = W.MIN_QUIET_FOR_PAYMENT


def defer_onsets(c: K.Core):
    """Rising edges of a positive field 108, and each loan's first one."""
    dfr = c.row["defer_amt"][:].astype(np.int64)
    on = (dfr != K.U32_NA) & (dfr > 0)
    loan = c.loan_of_row()
    same = np.zeros(c.n_rows, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]
    e = np.zeros(c.n_rows, dtype=bool)
    e[1:] = on[1:] & ~on[:-1] & same[1:]
    rows = np.flatnonzero(e)
    first = np.full(c.n_loans, -1, dtype=np.int64)
    if rows.size:
        lr = loan[rows]
        first[lr[::-1]] = rows[::-1]
    return rows, first, on, dfr


def c11_1a(c: K.Core, rows: np.ndarray, dfr: np.ndarray) -> dict:
    """Criterion A: the modal cluster of ``Δ12 / 108`` at the onset."""
    if rows.size == 0:
        return {"n": 0, "mode": float("nan"), "width": float("nan"),
                "ncand": 0, "at_plus1": 0, "at_minus1": 0, "at_zero": 0}
    upb = c.row["upb"][:].astype(np.int64)
    d = (upb[rows] - upb[rows - 1]).astype(np.float64)
    amt = dfr[rows].astype(np.float64)
    ok = amt > 0
    r = d[ok] / amt[ok]
    # the cluster machinery works in currency units; a ratio has no cent grid,
    # so a fixed tolerance is used and its value is stated rather than inherited
    vals = sorted(r.tolist())
    clusters, cur = [], [vals[0]]
    for v in vals[1:]:
        (cur.append(v) if v - cur[-1] <= 0.01 else
         (clusters.append(cur), cur.clear(), cur.append(v)))
    clusters.append(cur)
    best = max(clusters, key=len)
    thr = 0.10 * len(vals)
    return {
        "n": int(r.size),
        "mode": float(sum(best) / len(best)),
        "width": float(best[-1] - best[0]),
        "ncand": int(sum(1 for cl in clusters if len(cl) >= thr)),
        "at_plus1": int((np.abs(r - 1.0) <= 0.01).sum()),
        "at_minus1": int((np.abs(r + 1.0) <= 0.01).sum()),
        "at_zero": int((np.abs(r) <= 0.01).sum()),
    }


def c11_1b(c: K.Core, first: np.ndarray, on: np.ndarray) -> dict:
    """Criterion B: which reading of the IB balance reproduces the pre-deferral
    contract payment on post-deferral quiet months.

    The payment is estimated from the loan's quiet pairs **strictly before** its
    first field-108 onset, clustered with ``b8_core.modal_cluster``, which is
    the single copy of that estimator. It is deliberately **not** taken from
    ``b8_omega.contract_payments``: that function reads field 12 as the
    interest-bearing balance, which is reading A, so using it would make A
    reproduce the target by construction. See the comment below.
    """
    loan = c.loan_of_row()
    n = c.n_rows
    upb = c.row["upb"][:].astype(np.float64) / 100.0
    dfr = c.row["defer_amt"][:].astype(np.int64)
    amt = np.where((dfr != K.U32_NA) & (dfr > 0), dfr, 0).astype(np.float64) / 100.0
    rate = c.row["rate"][:].astype(np.float64) / 1000.0 / 1200.0
    rem = c.row["rem_legal"][:].astype(np.int64)
    dq = c.row["delinq"][:]
    per = c.row["period"][:].astype(np.int64)
    raw = c.row["rate"][:]
    rawu = c.row["upb"][:]

    # **The payment must be estimated from PRE-deferral quiet months only.**
    # The first version took it from `b8_omega.contract_payments`, which reads
    # field 12 as the interest-bearing balance, that is **reading A**, and then
    # asked which reading reproduces it. A won by construction. The synthetic
    # fixture caught it: the `12 contains 108` and `12 excludes 108` archives
    # read identically, which cannot happen if the criterion discriminates.
    #
    # Before the onset the deferred balance is zero, so both readings coincide
    # and the estimate is neutral between them. `modal_cluster` is
    # `b8_core`'s single copy, not a second one.
    fo = first[loan]                                   # per row, -1 if none
    has = fo >= 0
    # **Pinned to the parameters this measurement was run under**, not left to
    # whatever the default is. The published C11 figures came from
    # `require_never_deferred=True`, which excluded the 1,276 loans carrying
    # both fields — the same loans C13 later found unmeasurable. After the
    # 2026-08-17 default flip a bare call would silently re-admit them and the
    # numbers would move for a reason that has nothing to do with C11.
    q = K.quiet_pairs(c, require_never_deferred=True, ib_net=False)
    qc = q["cur"]
    pre = has[qc] & (qc < fo[qc])
    pre_pay = np.full(n, np.nan)
    if pre.any():
        pl = loan[qc[pre]]
        pv = (q["obs_cents"][pre].astype(np.float64) / 100.0
              + q["p_upb_cents"][pre].astype(np.float64) / 100.0
              * (q["rate_milli"][pre].astype(np.float64) / 1000.0 / 1200.0))
        order = np.argsort(pl, kind="stable")
        pl, pv = pl[order], pv[order]
        st = np.flatnonzero(np.concatenate(([True], pl[1:] != pl[:-1])))
        cnt = np.diff(np.append(st, pl.size))
        est = np.full(c.n_loans, np.nan)
        for lid, s, k in zip(pl[st].tolist(), st.tolist(), cnt.tolist()):
            if k >= MIN_QUIET:
                est[lid] = K.modal_cluster(pv[s:s + k].tolist())[0]
        pre_pay = est[loan]

    # post-deferral quiet months: same loan, consecutive, performing, rate held,
    # field 17 down exactly one, both balances present and positive
    cur = np.arange(1, n, dtype=np.int64)
    prv = cur - 1
    ok = (loan[cur] == loan[prv]) & (per[cur] - per[prv] == 1)
    ok &= (dq[cur] == 0) & (dq[prv] == 0)
    ok &= (raw[cur] != K.U16_NA) & (raw[prv] != K.U16_NA)
    ok &= raw[cur] == raw[prv]
    ok &= (rem[cur] != K.U16_NA) & (rem[prv] != K.U16_NA) & (rem[prv] - rem[cur] == 1)
    ok &= (rawu[cur] != K.U32_NA) & (rawu[prv] != K.U32_NA)
    ok &= (upb[cur] > 0) & (upb[prv] > 0)
    ok &= on[cur] & on[prv]                    # the deferred balance is standing
    ok &= has[cur] & (cur > fo[cur])           # strictly after the onset
    ok &= np.isfinite(pre_pay[cur])
    sel = cur[ok]
    if sel.size == 0:
        return {"n": 0, "loans": 0,
                "A_p50": float("nan"), "A_p90": float("nan"),
                "B_p50": float("nan"), "B_p90": float("nan"), "B_wins": 0}
    p = sel - 1
    i = rate[p]
    P = pre_pay[sel]
    impl_A = (upb[p] - upb[sel]) + upb[p] * i
    ib_c, ib_p = upb[sel] - amt[sel], upb[p] - amt[p]
    impl_B = (ib_p - ib_c) + ib_p * i
    eA = np.abs(impl_A - P) / P
    eB = np.abs(impl_B - P) / P
    return {
        "n": int(sel.size), "loans": int(np.unique(loan[sel]).size),
        "A_p50": float(np.percentile(eA, 50)),
        "A_p90": float(np.percentile(eA, 90)),
        "B_p50": float(np.percentile(eB, 50)),
        "B_p90": float(np.percentile(eB, 90)),
        "B_wins": int((eB < eA).sum()),
    }


def c11_2(c: K.Core, on: np.ndarray, dfr: np.ndarray) -> dict:
    """Balance or cumulative: does field 108 ever fall, and ever return to zero."""
    loan = c.loan_of_row()
    n = c.n_rows
    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]
    val = np.where(on, dfr, 0)
    fall = np.zeros(n, dtype=bool)
    fall[1:] = same[1:] & on[1:] & on[:-1] & (val[1:] < val[:-1])
    # returning to zero. Pit 13: a termination row reports a zero balance and
    # then stops reporting contract state, so `rem_legal` blank is a
    # termination, not a payoff, and both counts are printed.
    rem = c.row["rem_legal"][:]
    back = np.zeros(n, dtype=bool)
    back[1:] = same[1:] & ~on[1:] & on[:-1]
    live = back & (rem != K.U16_NA)
    return {
        "fall_pairs": int(fall.sum()),
        "fall_loans": int(np.unique(loan[fall]).size) if fall.any() else 0,
        "back_to_zero_raw": int(back.sum()),
        "back_to_zero_live": int(live.sum()),
    }


def c11_3(c: K.Core, rows: np.ndarray) -> dict:
    """Does ``19 - reporting month`` still equal field 17 on deferral rows."""
    if rows.size == 0:
        return {"n": 0, "agree": 0, "unusable": 0}
    mat = c.row["mat_date"][:].astype(np.int64)
    per = c.row["period"][:].astype(np.int64)
    rem = c.row["rem_legal"][:].astype(np.int64)
    good = ((mat[rows] != K.U16_NA) & (per[rows] != K.U16_NA)
            & (rem[rows] != K.U16_NA))
    d = (mat[rows] - per[rows])[good]
    return {"n": int(rows.size), "agree": int((d == rem[rows][good]).sum()),
            "unusable": int((~good).sum())}


def c11_4(c: K.Core, first: np.ndarray) -> dict:
    """How many field-108 loans already carry a contract payment estimate."""
    period = W.contract_periods(c, fill=True)
    # same pinning as criterion B, and for the same reason
    q = K.quiet_pairs(c, require_never_deferred=True, ib_net=False)
    _pay, known_row, _per = W.contract_payments(c, period, q)
    has = first >= 0
    idx = first[has]
    pre = np.maximum(idx - 1, 0)
    loan = c.loan_of_row()
    bad = np.bincount(loan, weights=(~known_row).astype(np.float64),
                      minlength=c.n_loans)
    return {
        "loans": int(has.sum()),
        "pre_known": int(known_row[pre].sum()),
        "full_path": int((bad[has] == 0).sum()),
    }


def measure(c: K.Core) -> dict:
    rows, first, on, dfr = defer_onsets(c)
    return {"onsets": int(rows.size), "a": c11_1a(c, rows, dfr),
            "b": c11_1b(c, first, on), "two": c11_2(c, on, dfr),
            "three": c11_3(c, rows), "four": c11_4(c, first)}


def _f(x, spec=".4f"):
    return "not measurable" if x != x else format(x, spec)


def render(rows: list[dict]) -> str:
    L_, A = [], None
    L_.append("# C11: field 108's deferred balance, and whether field 12 holds it\n")
    A = L_.append
    A("Generated by `experiments/b8_c11_deferred_balance.py`. **The map from "
      "outcome to disposition was fixed in the B8 inputs register "
      "§6.6.13 before this ran.** Computes no `omega`, reads no prediction.\n")

    A("\n## 1. C11-1 criterion A: `Δ12 / 108` at the onset, the quick reading\n")
    A("**Contaminated by capitalisation in the same month** (C10-4: the balance "
      "steps up on 94.3 to 99.5 per cent of these rows), so this is the fast "
      "reading and criterion B is the answer.\n")
    A("**A modal ratio is only printed when a cluster carries at least ten per "
      "cent of the sample.** With no such cluster the largest one is whatever "
      "singleton sorted first, and printing its value would read exactly like a "
      "measured mode. Pit 23's family, fourth occurrence in this stage.\n")
    A("| archive | onsets | **modal ratio** | cluster width | candidates | "
      "at +1 | at -1 | at 0 |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        a = r["a"]
        mode = f"**{_f(a['mode'])}**" if a["ncand"] else "**no mode**"
        A(f"| {r['name']} | {a['n']:,} | {mode} | "
          f"{_f(a['width'])} | {a['ncand']} | {a['at_plus1']:,} | "
          f"{a['at_minus1']:,} | {a['at_zero']:,} |")

    A("\n## 2. C11-1 criterion B: which reading reproduces the contract payment\n")
    A("Post-deferral quiet months with the deferred balance standing, against "
      "the payment estimated **before** the first field-108 onset. C10-4 "
      "measured the rate and the maturity both hold across 99.66 per cent of "
      "those onsets, so the contract payment cannot have changed.\n")
    A("\n> **A** reads field 12 as the interest-bearing balance. "
      "**B** reads `12 - 108`.\n")
    A("| archive | months | loans | A err p50 | A p90 | **B err p50** | B p90 | "
      "**B closer on** |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        b = r["b"]
        sh = f"{b['B_wins'] / b['n']:.4f}" if b["n"] else "not measurable"
        A(f"| {r['name']} | {b['n']:,} | {b['loans']:,} | {_f(b['A_p50'])} | "
          f"{_f(b['A_p90'])} | **{_f(b['B_p50'])}** | {_f(b['B_p90'])} | "
          f"**{sh}** |")

    A("\n## 3. C11-2: balance or cumulative\n")
    A("A cumulative total never falls and never returns to zero. **Pit 13**: a "
      "termination row reports a zero balance and stops reporting contract "
      "state, so a blank field 17 there is a termination and not a payoff. "
      "Both counts are printed.\n")
    A("| archive | falling pairs | loans | back to zero, raw | "
      "**back to zero, still reporting** |")
    A("|---|---|---|---|---|")
    for r in rows:
        t = r["two"]
        A(f"| {r['name']} | {t['fall_pairs']:,} | {t['fall_loans']:,} | "
          f"{t['back_to_zero_raw']:,} | **{t['back_to_zero_live']:,}** |")

    A("\n## 4. C11-3: the balloon's maturity\n")
    A("§14.1 discounts the balloon to field 19. On deferral rows, does "
      "`19 - reporting month` still equal field 17?\n")
    A("| archive | deferral rows | **agree** | share | unusable |")
    A("|---|---|---|---|---|")
    for r in rows:
        t = r["three"]
        d = t["n"] - t["unusable"]
        A(f"| {r['name']} | {t['n']:,} | **{t['agree']:,}** | "
          f"{(t['agree'] / d if d else float('nan')):.4f} | {t['unusable']:,} |")

    A("\n## 5. C11-4: how many field-108 loans already have a payment\n")
    A("`quiet_pairs(require_never_deferred=True)` excludes **field 63** loans "
      "and says nothing about field 108, so these loans were never excluded. "
      "**This number bounds how large B8-3's deferral arm can be.** O24 is not "
      "declared narrowed here; this is the count a ruling would need.\n")
    A("| archive | field-108 loans | **payment known before the onset** | "
      "share | full path covered |")
    A("|---|---|---|---|---|")
    for r in rows:
        f4 = r["four"]
        n = f4["loans"]
        A(f"| {r['name']} | {n:,} | **{f4['pre_known']:,}** | "
          f"{(f4['pre_known'] / n if n else float('nan')):.4f} | "
          f"{f4['full_path']:,} |")

    A("\n## What this does not decide\n")
    A("- **It computes no `omega`.**\n")
    A(f"- The deferral onset is field {L.DEFER_FIELD}, read from `b8_loops` "
      "rather than typed here (pit 31).\n")
    A("- **It does not change `quiet_pairs`.** Whether field 108 should join "
      "the exclusion depends on criterion B's answer, and that ruling comes "
      "after this, not inside it.\n")
    A("- **It does not settle O28** (B8-0a's clean-cure sample carrying "
      "field-108 deferrals). Criterion B points at it; the ruling is separate.\n")
    A("- It reads no prediction.\n")
    return "\n".join(L_) + "\n"


def run(names: list[str]) -> int:
    out = []
    for name in names:
        with K.Core(name, cols=COLS, loan_cols=[]) as c:
            a = measure(c)
        a["name"] = name
        out.append(a)
        print(f"  {name}: onsets={a['onsets']:,} modal={_f(a['a']['mode'])} "
              f"B_p50={_f(a['b']['B_p50'])} A_p50={_f(a['b']['A_p50'])} "
              f"months={a['b']['n']:,} pre_known={a['four']['pre_known']:,}"
              f"/{a['four']['loans']:,}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(out), encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# selftest: a synthetic archive where field 12 DOES contain field 108, built
# from a real amortisation schedule so criterion B has a right answer to find.
# ---------------------------------------------------------------------------

def _synth(path: Path, contains: bool = True) -> None:
    """One loan: quiet, then a 3-month deferral, then quiet again.

    ``contains=True`` writes field 12 **including** the deferred amount, which
    is the reading criterion B must pick. ``contains=False`` is the mirror and
    is used by the mutation check inside the selftest, so the test cannot pass
    by always preferring B.
    """
    rate, rem, y, m, age = 6.0, 360, 2019, 1, 0
    i = rate / 1200.0
    bal = 200000.0
    pmt = float(K.level_payment([bal], [rate], [rem])[0])
    lines, deferred = [], 0.0
    for k in range(40):
        if 12 <= k < 15:                      # three missed months, deferred
            dq, add = "00", pmt - bal * i
            deferred += add
            bal_ib = bal                      # principal does not amortise
        else:
            dq = "00"
            bal_ib = bal
        rep = bal_ib + (deferred if contains else 0.0)
        f = [""] * K.NFIELDS
        f[1] = "930000000001"
        f[2] = f"{m:02d}{y:04d}"
        f[3] = "R"
        f[8] = f"{rate:.3f}"
        f[11] = f"{rep:.2f}" if k >= 2 else "0.00"
        f[12] = "360"
        f[15] = str(age)
        f[16] = str(rem)
        f[17] = str(rem)
        f[18] = "012049"
        f[19] = "80"
        f[22] = "35"
        f[23] = "720"
        f[25] = "N"
        f[26] = "P"
        f[29] = "P"
        f[30] = "CA"
        f[39] = dq
        f[41] = "N"
        f[101] = "7"
        f[105] = "P" if deferred else ""
        f[107] = f"{deferred:.2f}" if deferred else ""
        lines.append("|".join(f))
        if not (12 <= k < 15):
            bal = bal * (1 + i) - pmt
        rem -= 1
        age += 1
        m += 1
        if m == 13:
            m, y = 1, y + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")


def _tag(contains: bool) -> str:
    import hashlib
    import inspect
    return hashlib.sha256(
        (inspect.getsource(_synth) + str(contains)).encode()).hexdigest()[:8]


def _measure_fixture(contains: bool) -> dict:
    root = K.CACHE / "_selftest_c11"
    zp = root / "raw" / f"209{6 if contains else 5}Q1_{_tag(contains)}.zip"
    if not zp.exists():
        _synth(zp, contains=contains)
    K.build_archive(zp, force=True, cache_root=root / "cache")
    with K.Core(zp.stem, cols=COLS, loan_cols=[],
                cache_root=root / "cache") as c:
        return measure(c)


def selftest() -> int:
    fails = []
    inc = _measure_fixture(True)
    exc = _measure_fixture(False)
    for lab, a in (("12 contains 108", inc), ("12 excludes 108", exc)):
        b = a["b"]
        print(f"  {lab:<18} onsets={a['onsets']} months={b['n']} "
              f"A_p50={_f(b['A_p50'])} B_p50={_f(b['B_p50'])} "
              f"B_wins={b['B_wins']}", file=sys.stderr)

    if inc["onsets"] != 1 or exc["onsets"] != 1:
        fails.append("each fixture must produce exactly one deferral onset")
    if inc["b"]["n"] < 5:
        fails.append(f"only {inc['b']['n']} post-deferral quiet months usable; "
                     "criterion B has nothing to read")

    # **The test that matters: the criterion must pick the reading the fixture
    # was built with, and must pick the OTHER one on the mirrored fixture.**
    # Without the mirror, a criterion that always prefers B would pass.
    if not inc["b"]["B_p50"] < inc["b"]["A_p50"]:
        fails.append("on the `12 contains 108` fixture, B must be closer than A")
    if not exc["b"]["A_p50"] < exc["b"]["B_p50"]:
        fails.append("on the `12 excludes 108` fixture, A must be closer than B")

    # C11-2: the fixture's deferred amount only grows, so it must read as a
    # cumulative-shaped series here; that pins the direction of the test.
    if inc["two"]["fall_pairs"] != 0:
        fails.append(f"fixture 108 falls {inc['two']['fall_pairs']}x; it only "
                     "grows by construction")
    # C11-3: the fixture keeps 19 and 17 consistent, so agreement must be total
    t = inc["three"]
    if t["agree"] != t["n"] - t["unusable"] or t["n"] == 0:
        fails.append(f"C11-3 agreement {t['agree']} of {t['n'] - t['unusable']}")

    txt = render([dict(inc, name="fixture")])

    # every table's rows must match its header's width. A published

    # results file was malformed on 2026-08-17 and the person who

    # generated it read it and quoted from it without noticing.

    for _c in K.check_markdown_tables(txt):

        fails.append(f"malformed table: {_c}")
    for need in ("## 1. C11-1 criterion A", "## 2. C11-1 criterion B",
                 "## 3. C11-2", "## 4. C11-3", "## 5. C11-4"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
    # a fabricated mode must not be printable: force the no-mode branch
    blank = dict(inc, name="x", a=dict(inc["a"], ncand=0))
    if "no mode" not in render([blank]):
        fails.append("a zero-candidate modal ratio still prints as a number")
    if f"field {L.DEFER_FIELD}" not in txt:
        fails.append("the results file never names the deferral column in use")

    if fails:
        print("\nSELFTEST FAILED", file=sys.stderr)
        for x in fails:
            print(f"  - {x}", file=sys.stderr)
        return 1
    print("\nselftest ok", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["selftest", "run"])
    ap.add_argument("--only", action="append", default=None)
    a = ap.parse_args()
    if a.cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(run(a.only or ["2002Q1", "2006Q1", "2007Q1", "2012Q1",
                                    "2017Q1", "2019Q1"]))


if __name__ == "__main__":
    main()
