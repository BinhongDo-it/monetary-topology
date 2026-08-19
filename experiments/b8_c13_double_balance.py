#!/usr/bin/env python3
"""C13: what field 12 contains when **both** zero-interest balances are standing.

Registered in the B8 inputs register §6.6.19, and the map from
outcome to disposition is written there before this ran. **Computes no ``omega``
and reads no prediction.**

--------------------------------------------------------------------------
This is a domain boundary, not a new defect
--------------------------------------------------------------------------

C11's criterion B ran on ``quiet_pairs(require_never_deferred=True)``, whose
sample carries **no field 63 by construction**, so what it settled is

    on loans without field 63, field 12 contains field 108.

C8-1 is the mirror: it settled that field 12 contains field 63, on a sample with
no field-108 layer in view. **Neither settled what field 12 holds when both are
positive at once**, and §14.1's ``V`` needs exactly that, because it wants to
write the interest-bearing balance as ``12 - 63 - 108``.

**Using a ruling past its domain is not the ruling being wrong.** The two middle
outcomes below therefore say "go back and check", not "amend the ruling": a
conflict would mean one of the two measurements was read past its own sample.

--------------------------------------------------------------------------
The criterion, same shape as C11's
--------------------------------------------------------------------------

The contract payment comes from the quiet months **before the earlier of the two
onsets**, where both balances are zero and all four readings coincide, so the
estimate is neutral between them. Then, on months where **both** are positive::

    A      ib = 12
    B63    ib = 12 - 63
    B108   ib = 12 - 108
    Bboth  ib = 12 - 63 - 108

Usage::

    python experiments/b8_c13_double_balance.py selftest   # no real archive
    python experiments/b8_c13_double_balance.py run
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_c10_contract_move as C  # noqa: E402
import b8_core as K  # noqa: E402
import b8_omega as W  # noqa: E402

OUT = K.ROOT / "results" / "b8_c13_double_balance.md"

#: Pit 30. Swept by ``scripts/b8_col_sweep.py``.
COLS = ["period", "rate", "upb", "rem_legal", "delinq", "mod_flag", "nib_upb",
        "defer_amt"]

MIN_QUIET = W.MIN_QUIET_FOR_PAYMENT
READINGS = ("A", "B63", "B108", "Bboth")

#: Above this median relative error, **no reading is called closest**, because
#: none of them reproduces the payment. **Anchored, not invented**: C11's
#: criterion B settled its own question at a median error of exactly 0.0000 on
#: this file, and the reported balance's cent grid puts the achievable floor
#: near 1e-5. A reading at 1e-1 is four orders of magnitude from reproducing
#: anything. §6.6.19.3's fifth branch stated this outcome without a number,
#: which was a gap in that registration; the number is fixed here, with its
#: source, and the gap is recorded rather than quietly filled.
NOT_CLOSE = 0.01


def measure(c: K.Core) -> dict:
    loan = c.loan_of_row()
    n = c.n_rows
    upb = c.row["upb"][:].astype(np.float64) / 100.0
    nib_r = c.row["nib_upb"][:].astype(np.int64)
    dfr_r = c.row["defer_amt"][:].astype(np.int64)
    nib = np.where((nib_r != K.U32_NA) & (nib_r > 0), nib_r, 0) / 100.0
    dfr = np.where((dfr_r != K.U32_NA) & (dfr_r > 0), dfr_r, 0) / 100.0
    non = nib > 0
    don = dfr > 0

    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]

    def first_of(mask):
        e = np.zeros(n, dtype=bool)
        e[1:] = mask[1:] & ~mask[:-1] & same[1:]
        rows = np.flatnonzero(e)
        out = np.full(c.n_loans, -1, dtype=np.int64)
        if rows.size:
            lr = loan[rows]
            out[lr[::-1]] = rows[::-1]
        return out

    f63, f108 = first_of(non), first_of(don)
    both_loan = (f63 >= 0) & (f108 >= 0)
    # the earlier of the two onsets, per loan
    earlier = np.where(both_loan, np.minimum(np.where(f63 < 0, n, f63),
                                             np.where(f108 < 0, n, f108)), -1)

    # payment from the quiet months strictly before that, per loan
    q = K.quiet_pairs(c, require_never_deferred=False, ib_net=False)
    qc = q["cur"]
    el = earlier[loan[qc]]
    pre = (el >= 0) & (qc < el)
    est = np.full(c.n_loans, np.nan)
    if pre.any():
        pl = loan[qc[pre]]
        pv = (q["obs_cents"][pre].astype(np.float64) / 100.0
              + q["p_upb_cents"][pre].astype(np.float64) / 100.0
              * (q["rate_milli"][pre].astype(np.float64) / 1000.0 / 1200.0))
        o = np.argsort(pl, kind="stable")
        pl, pv = pl[o], pv[o]
        st = np.flatnonzero(np.concatenate(([True], pl[1:] != pl[:-1])))
        cnt = np.diff(np.append(st, pl.size))
        for lid, s, k in zip(pl[st].tolist(), st.tolist(), cnt.tolist()):
            if k >= MIN_QUIET:
                est[lid] = K.modal_cluster(pv[s:s + k].tolist())[0]

    # months where BOTH are positive, quiet, and the loan has an estimate
    rate = c.row["rate"][:]
    rem = c.row["rem_legal"][:].astype(np.int64)
    dq = c.row["delinq"][:]
    per = c.row["period"][:].astype(np.int64)
    rawu = c.row["upb"][:]
    cur = np.arange(1, n, dtype=np.int64)
    prv = cur - 1
    ok = (loan[cur] == loan[prv]) & (per[cur] - per[prv] == 1)
    ok &= (dq[cur] == 0) & (dq[prv] == 0)
    ok &= (rate[cur] != K.U16_NA) & (rate[prv] != K.U16_NA)
    ok &= rate[cur] == rate[prv]
    ok &= (rem[cur] != K.U16_NA) & (rem[prv] != K.U16_NA)
    ok &= rem[prv] - rem[cur] == 1
    ok &= (rawu[cur] != K.U32_NA) & (rawu[prv] != K.U32_NA)
    ok &= (upb[cur] > 0) & (upb[prv] > 0)
    ok &= non[cur] & don[cur] & non[prv] & don[prv]      # BOTH standing
    ok &= np.isfinite(est[loan[cur]])
    sel = cur[ok]

    a = {
        "loans_both": int(both_loan.sum()),
        "loans_with_estimate": int((both_loan & np.isfinite(est)).sum()),
        "months_both_positive": int((non & don).sum()),
        "rows": int(n),
        "n": int(sel.size),
        "loans": int(np.unique(loan[sel]).size) if sel.size else 0,
    }
    if sel.size == 0:
        for r in READINGS:
            a[f"{r}_p50"] = a[f"{r}_p90"] = float("nan")
        a["winner"] = "not measurable"
        return a

    p = sel - 1
    i = rate[p].astype(np.float64) / 1000.0 / 1200.0
    P = est[loan[sel]]
    ibs = {
        "A": (upb[sel], upb[p]),
        "B63": (upb[sel] - nib[sel], upb[p] - nib[p]),
        "B108": (upb[sel] - dfr[sel], upb[p] - dfr[p]),
        "Bboth": (upb[sel] - nib[sel] - dfr[sel], upb[p] - nib[p] - dfr[p]),
    }
    med = {}
    for r, (cu, pv) in ibs.items():
        impl = (pv - cu) + pv * i
        e = np.abs(impl - P) / P
        a[f"{r}_p50"] = float(np.percentile(e, 50))
        a[f"{r}_p90"] = float(np.percentile(e, 90))
        med[r] = a[f"{r}_p50"]
    # **The fifth branch fires before the winner is meaningful.** §6.6.19.3's
    # last row is "all four far from P -> cannot be settled, exclude and
    # count". Printing a `closest` in that case is pit 32's family: a label
    # that reads like a measurement when it is only the least bad of four bad
    # readings. The anchor is not a threshold picked here: C11's criterion B
    # reproduced the payment at a **median error of 0.0000** on this same file,
    # and the cent grid puts the floor near 1e-5, so 1e-1 is not a
    # reproduction by four orders of magnitude.
    a["winner"] = min(med, key=med.get)
    a["best_p50"] = float(med[a["winner"]])
    a["settled"] = bool(a["best_p50"] <= NOT_CLOSE)
    if not a["settled"]:
        a["winner"] = f"none close (best {a['winner']})"
    a["readable"] = sel.size >= C.MIN_CELL
    return a


def _f(x):
    return "not measurable" if x != x else f"{x:.4f}"


def render(rows: list[dict]) -> str:
    L, A = [], None
    L.append("# C13: field 12 when both zero-interest balances are standing\n")
    A = L.append
    A("Generated by `experiments/b8_c13_double_balance.py`. **The map from "
      "outcome to disposition was fixed in the B8 inputs register "
      "§6.6.19 before this ran.**\n")
    A("\n**This is a domain boundary, not a new defect.** C11 settled that "
      "field 12 contains field 108 **on a sample with no field 63**; C8-1 "
      "settled that it contains field 63 with no field-108 layer in view. "
      "Neither covers both at once, and `V` wants `12 - 63 - 108`.\n")

    A("\n## 1. The population\n")
    A("| archive | loans carrying both | with a pre-onset estimate | "
      "months both positive | **usable months** | loans | readable |")
    A("|---|---|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {r['loans_both']:,} | "
          f"{r['loans_with_estimate']:,} | {r['months_both_positive']:,} | "
          f"**{r['n']:,}** | {r['loans']:,} | "
          f"{'yes' if r.get('readable') else '**NO**'} |")

    A("\n## 2. The criterion: which reading reproduces the contract payment\n")
    A("Payment estimated from the quiet months **before the earlier of the two "
      "onsets**, where both balances are zero and all four readings coincide.\n")
    A("| archive | A p50 | B63 p50 | B108 p50 | **Bboth p50** | A p90 | "
      "B63 p90 | B108 p90 | Bboth p90 | **closest** |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['name']} | {_f(r['A_p50'])} | {_f(r['B63_p50'])} | "
          f"{_f(r['B108_p50'])} | **{_f(r['Bboth_p50'])}** | "
          f"{_f(r['A_p90'])} | {_f(r['B63_p90'])} | {_f(r['B108_p90'])} | "
          f"{_f(r['Bboth_p90'])} | **{r['winner']}** |")
    A(f"\n**No reading is named closest above a median error of "
      f"{NOT_CLOSE:.0%}**, and the anchor is C11: its criterion B settled its "
      "own question at a median error of **0.0000** on this same file. "
      "Naming a winner among four readings that all miss by an order of "
      "magnitude would read like a measurement (pit 32's family).\n")

    A("\n## What this does not decide\n")
    A("- **It computes no `omega`.**\n")
    A("- **It does not amend C8-1 or C11.** Each holds inside its own sample; "
      "a conflict here would mean one of them was read past its domain, which "
      "is something to check, not to overwrite.\n")
    A("- It reads no prediction.\n")
    return "\n".join(L) + "\n"


def run(names: list[str]) -> int:
    out = []
    for name in names:
        with K.Core(name, cols=COLS, loan_cols=[]) as c:
            a = measure(c)
        a["name"] = name
        out.append(a)
        print(f"  {name}: both={a['loans_both']:,} months={a['n']:,} "
              f"winner={a['winner']} Bboth={_f(a['Bboth_p50'])} "
              f"B63={_f(a['B63_p50'])} B108={_f(a['B108_p50'])}",
              file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(out), encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# selftest: four mirrored fixtures, one per reading, so a criterion that always
# prefers one of them cannot pass.
# ---------------------------------------------------------------------------

def _synth(path: Path, holds: str) -> None:
    """One loan: quiet, then field 63 appears, then field 108 too, then quiet.

    ``holds`` says what the written field 12 includes: ``"both"``, ``"63"``,
    ``"108"`` or ``"none"``. **All four are generated and the selftest asserts
    the criterion picks the one the archive was built with**, which is the only
    way to show it discriminates rather than favours.
    """
    rate, rem, y, m, age = 6.0, 360, 2019, 1, 0
    i = rate / 1200.0
    bal = 200000.0
    pmt = float(K.level_payment([bal], [rate], [rem])[0])
    lines, nib, dfr = [], 0.0, 0.0
    for k in range(44):
        if k == 12:
            nib = 4000.0
        if k == 18:
            dfr = 2500.0
        extra = (nib if holds in ("both", "63") else 0.0) \
            + (dfr if holds in ("both", "108") else 0.0)
        f = [""] * K.NFIELDS
        f[1] = "950000000001"
        f[2] = f"{m:02d}{y:04d}"
        f[3] = "R"
        f[8] = f"{rate:.3f}"
        f[11] = f"{bal + extra:.2f}" if k >= 2 else "0.00"
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
        f[39] = "00"
        f[41] = "N"
        f[62] = f"{nib:.2f}" if nib else ""
        f[101] = "7"
        f[105] = "P" if dfr else "7"
        f[107] = f"{dfr:.2f}" if dfr else ""
        lines.append("|".join(f))
        bal = bal * (1 + i) - pmt
        rem -= 1
        age += 1
        m += 1
        if m == 13:
            m, y = 1, y + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")


def _tag(holds: str) -> str:
    import hashlib
    import inspect
    return hashlib.sha256(
        (inspect.getsource(_synth) + holds).encode()).hexdigest()[:8]


def selftest() -> int:
    fails = []
    want = {"both": "Bboth", "63": "B63", "108": "B108", "none": "A"}
    got = {}
    for j, (holds, expect) in enumerate(want.items()):
        root = K.CACHE / "_selftest_c13"
        zp = root / "raw" / f"209{j}Q2_{_tag(holds)}.zip"
        if not zp.exists():
            _synth(zp, holds)
        K.build_archive(zp, force=True, cache_root=root / "cache")
        with K.Core(zp.stem, cols=COLS, loan_cols=[],
                    cache_root=root / "cache") as c:
            a = measure(c)
        got[holds] = a
        print(f"  12 holds {holds:<5} months={a['n']:>3} winner={a['winner']:<6}"
              f" A={_f(a['A_p50'])} B63={_f(a['B63_p50'])} "
              f"B108={_f(a['B108_p50'])} Bboth={_f(a['Bboth_p50'])}",
              file=sys.stderr)
        if a["n"] < 5:
            fails.append(f"fixture `{holds}`: only {a['n']} usable months")
        elif not a["settled"]:
            fails.append(f"fixture `{holds}`: built to match exactly and read "
                         f"best {a['best_p50']:.4f}, above NOT_CLOSE")
        elif a["winner"] != expect:
            fails.append(f"fixture `{holds}`: criterion picked "
                         f"{a['winner']}, expected {expect}")

    # **The four fixtures must not all read the same**, or a criterion that
    # always names one reading would pass every one of them.
    if len({g["winner"] for g in got.values()}) < 4:
        fails.append("the four fixtures do not separate; a criterion that "
                     "always names one reading would pass")
    txt = render([dict(got["both"], name="fixture")])
    for _c in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {_c}")
    for need in ("## 1. The population", "## 2. The criterion"):
        if need not in txt:
            fails.append(f"render omits `{need}`")
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
