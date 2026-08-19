#!/usr/bin/env python3
"""C10-4: which column actually carries the `deferred` tier.

Registered in the B8 inputs register §6.6.10, **and the map from
outcome to disposition is written there before this ran**. Pure counting on
confirmed fields. **Computes no ``omega`` and reads no prediction.**

--------------------------------------------------------------------------
Why this exists
--------------------------------------------------------------------------

§14.4 justifies giving `deferred` its own tier with the audit's deferral
triangle counts, 31,057 in COVID and 1,476 after 2022. Those come from
``b8_field_audit.py``'s ``tri_defer``, which hangs on ``defer_period``, which is
set from **field 106's ADR code** (`P`, `C`, `D`). ``b8_loops`` cuts the tier's
onset on **field 63** instead, and C10-3 measured that field 63's rising edges
are zero before 2009-01, 53.5 per cent inside HAMP and 6.6 per cent inside
COVID. **The tier is argued from one column's population and implemented on
another's.**

--------------------------------------------------------------------------
The criterion, and it is a conjunction
--------------------------------------------------------------------------

§14.4's own words are "a zero-interest balloon **at the unchanged maturity** and
**leaves rate and term alone**". Two conditions, both required::

    (a) the note rate does not move          field 9 equals the previous row
    (b) the maturity does not move           field 17 equals previous minus one

``still`` is **both at once**, reported as its own column. That is pit 29's
direct remedy: reading `rate` at 0.0082 and calling post-2022 "the payment
deferral shape" while `term` read 0.9950 on the same line is the error this
column exists to prevent. No reader should have to conjoin two columns by eye.

**Which column has a high `still` is the answer.** The dispositions for one
column, several columns and no column are all fixed in §6.6.10.3.

--------------------------------------------------------------------------
The two companion tables, both required by §6.6.10.4
--------------------------------------------------------------------------

**Pairing.** Counts alone cannot tell "field 108 is a superset of field 63"
from "the two cross". B10 §19.9's 13-to-18-fold gap is a count gap. The pairing
table compares each loan's **first** rising edge of each kind: same row, which
came first, or only one exists.

**Window distribution.** The three columns' rising edges by §6's windows, beside
C10-3's. Note the audit's `tri_defer` is a **loan-level triangle** count and
these are **row-level onsets**; they sit side by side to compare shape, not to
reconcile totals.

Usage::

    python experiments/b8_c10_4_tier_carrier.py selftest   # no real archive
    python experiments/b8_c10_4_tier_carrier.py run
    python experiments/b8_c10_4_tier_carrier.py run --only 2019Q1
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

OUT = K.ROOT / "results" / "b8_c10_4_tier_carrier.md"

#: **Exact, not generous.** A mutation sweep on 2026-08-17 dropped each entry
#: in turn and re-ran the selftest: `delinq` and `mod_flag` could be removed
#: without anything noticing, because nothing in this file reads them. A column
#: list that names more than it uses is a list nobody can check.
COLS = ["period", "rate", "upb", "rem_legal", "nib_upb", "defer_amt", "adr"]

#: Field 106's only values that mean a deferral. Transcribed from
#: ``b8_field_audit.ADR_REAL``, **not re-derived**. `7` is the "none of the
#: above" code and is not data: pit 1, which cost a full scan when v1 read the
#: ADR field as 62.5 per cent of rows.
ADR_REAL = frozenset(ord(x) for x in "PCD")

#: The candidate carriers, in the order the tables print them.
CARRIERS = ("nib", "defer", "adr")
CARRIER_DESC = {
    "nib": "field 63, non-interest-bearing UPB (what `b8_loops` cuts on today)",
    "defer": "field 108, total deferral amount",
    "adr": "field 106, ADR code P/C/D (**what §14.4's argument counts**)",
}


def onsets(c: K.Core) -> dict:
    """Rising edge row indices for each candidate column, within a loan.

    A loan whose **first** row already carries the state has no observable
    onset; that is left truncation and it is counted separately rather than
    being read as an onset or as an absence.
    """
    loan = c.loan_of_row()
    n = c.n_rows
    same = np.zeros(n, dtype=bool)
    same[1:] = loan[1:] == loan[:-1]

    nib = c.row["nib_upb"][:].astype(np.int64)
    dfr = c.row["defer_amt"][:].astype(np.int64)
    adr = c.row["adr"][:]

    on = {
        "nib": (nib != K.U32_NA) & (nib > 0),
        "defer": (dfr != K.U32_NA) & (dfr > 0),
        "adr": np.isin(adr, np.fromiter(ADR_REAL, dtype=adr.dtype)),
    }
    out = {"left_truncated": {}, "on_rows": {}, "rows": {}}
    first_rows = c.row_start.astype(np.int64)
    for k, m in on.items():
        e = np.zeros(n, dtype=bool)
        e[1:] = m[1:] & ~m[:-1] & same[1:]
        out["rows"][k] = np.flatnonzero(e)
        out["on_rows"][k] = int(m.sum())
        out["left_truncated"][k] = int(m[first_rows].sum())
    # pit 1 made visible rather than assumed away
    out["adr_code_7"] = int((adr == ord("7")).sum())
    out["adr_blank"] = int((adr == K.U8_NA).sum())
    return out


def first_per_loan(c: K.Core, rows: np.ndarray) -> np.ndarray:
    """Each loan's first onset row, or -1. ``rows`` must be ascending."""
    out = np.full(c.n_loans, -1, dtype=np.int64)
    if rows.size:
        loan = c.loan_of_row()[rows]
        # rows ascend, so the last write per loan would be the last onset;
        # reverse so the surviving write is the first.
        out[loan[::-1]] = rows[::-1]
    return out


def pairing(c: K.Core, o: dict) -> list[dict]:
    """Per loan, the first onset of each pair of columns, compared."""
    f = {k: first_per_loan(c, o["rows"][k]) for k in CARRIERS}
    out = []
    for i, a in enumerate(CARRIERS):
        for b in CARRIERS[i + 1:]:
            x, y = f[a], f[b]
            both = (x >= 0) & (y >= 0)
            out.append({
                "pair": f"{a} / {b}",
                "loans_a": int((x >= 0).sum()),
                "loans_b": int((y >= 0).sum()),
                "both": int(both.sum()),
                "same_row": int((both & (x == y)).sum()),
                "a_first": int((both & (x < y)).sum()),
                "b_first": int((both & (x > y)).sum()),
                "only_a": int(((x >= 0) & (y < 0)).sum()),
                "only_b": int(((x < 0) & (y >= 0)).sum()),
            })
    return out


def measure(c: K.Core) -> dict:
    start, end = W._row_bounds(c)
    rate_f = W.fill_within_loan(c.row["rate"][:], K.U16_NA, start, end)
    o = onsets(c)
    a = {"n_rows": int(c.n_rows), "n_loans": int(c.n_loans),
         "left_truncated": o["left_truncated"], "on_rows": o["on_rows"],
         "adr_code_7": o["adr_code_7"], "adr_blank": o["adr_blank"],
         "pairs": pairing(c, o), "all": {}, "win": {}}
    for k in CARRIERS:
        rows = o["rows"][k]
        a["all"][k] = C.contract_move(c, rows, rate_f)
        a["win"][k] = C.by_window(c, rows, rate_f)
    return a


def _still(d: dict) -> str:
    return ("not measurable" if not d["decidable"]
            else f"{d['still'] / d['decidable']:.4f}")


def render(rows: list[dict]) -> str:
    L, A = [], None
    L.append("# C10-4: which column carries the `deferred` tier\n")
    A = L.append
    A("Generated by `experiments/b8_c10_4_tier_carrier.py`. **The map from "
      "outcome to disposition was fixed in the B8 inputs register "
      "§6.6.10.3 before this ran.** Computes no `omega`, reads no "
      "prediction.\n")
    A("\n§14.4 defines a deferral as \"a zero-interest balloon **at the "
      "unchanged maturity** and **leaves rate and term alone**\". That is a "
      "**conjunction**, so it is printed as one column:\n")
    A("\n> `still` = the note rate did not move **and** field 17 fell by "
      "exactly one.\n")
    A("\nReading one half of a conjunction and declaring the shape is pit 29, "
      "committed on the previous table in this family. `rate` and `term` are "
      "printed beside `still` so the split is visible, **but `still` is the "
      "criterion**.\n")
    A("\n| column | what it is |")
    A("|---|---|")
    for k in CARRIERS:
        A(f"| `{k}` | {CARRIER_DESC[k]} |")

    A("\n## 1. The criterion: `still`, pooled over all onsets\n")
    A("| archive | column | onsets | decidable | **still** | rate moved | "
      "term moved | upb up |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        for k in CARRIERS:
            d = r["all"][k]
            A(f"| {r['name']} | `{k}` | {d['n']:,} | {d['decidable']:,} | "
              f"**{_still(d)}** | {C._fmt(d, 'rate')} | {C._fmt(d, 'term')} | "
              f"{C._fmt(d, 'upb')} |")

    A("\n## 2. The same, by window\n")
    A(f"Cells below {C.MIN_CELL} decidable rows are printed and marked "
      "**NO**, not dropped (`b2_measurement.md` §10, the floor C9 uses).\n")
    A("| archive | column | window | onsets | decidable | **still** | rate | "
      "term | readable |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        for k in CARRIERS:
            for d in r["win"][k]:
                if not d["n"]:
                    continue
                A(f"| {r['name']} | `{k}` | {d['window']} | {d['n']:,} | "
                  f"{d['decidable']:,} | **{_still(d)}** | "
                  f"{C._fmt(d, 'rate')} | {C._fmt(d, 'term')} | "
                  f"{'yes' if d['readable'] else '**NO**'} |")

    A("\n## 3. Pairing: superset or crossing\n")
    A("Each loan's **first** onset of each kind. **A count gap is not a "
      "property gap**: B10 §19.9 measured field 63 against field 108 at 13 to "
      "18 times and that alone cannot tell a superset from a crossing.\n")
    A("| archive | pair | loans with a | loans with b | both | same row | "
      "a first | b first | only a | only b |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        for p in r["pairs"]:
            A(f"| {r['name']} | {p['pair']} | {p['loans_a']:,} | "
              f"{p['loans_b']:,} | {p['both']:,} | **{p['same_row']:,}** | "
              f"{p['a_first']:,} | {p['b_first']:,} | {p['only_a']:,} | "
              f"{p['only_b']:,} |")

    A("\n## 4. Where the onsets sit, and pit 1 made visible\n")
    A("`adr = 7` is the \"none of the above\" code and is **not** a deferral "
      "(pit 1, which cost a full scan). Its count is printed so the exclusion "
      "is visible rather than assumed.\n")
    A("| archive | rows | nib on | defer on | adr P/C/D on | **adr = 7** | "
      "adr blank | left-trunc nib / defer / adr |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lt = r["left_truncated"]
        A(f"| {r['name']} | {r['n_rows']:,} | {r['on_rows']['nib']:,} | "
          f"{r['on_rows']['defer']:,} | {r['on_rows']['adr']:,} | "
          f"**{r['adr_code_7']:,}** | {r['adr_blank']:,} | "
          f"{lt['nib']:,} / {lt['defer']:,} / {lt['adr']:,} |")

    A("\n## What this does not decide\n")
    A("- **It computes no `omega`** and does not change §17's window rule; "
      "every disposition in §6.6.10.3 changes only which column the onset is "
      "cut on, and §17.9 guarantees that leaves the window alone.\n")
    A("- **It does not run C10-5** (balloon size against the number of missed "
      "payments). That is sharper but needs a payment estimate for deferred "
      "loans, which is O24 §2.1's open path; the two are one job.\n")
    A("- The audit's `tri_defer` is a **loan-level triangle** count and these "
      "are **row-level onsets**. Different objects; do not reconcile totals.\n")
    A("- It reads no prediction.\n")
    return "\n".join(L) + "\n"


def run(names: list[str]) -> int:
    rows = []
    for name in names:
        with K.Core(name, cols=COLS, loan_cols=[]) as c:
            a = measure(c)
        a["name"] = name
        rows.append(a)
        print(f"  {name}: " + "  ".join(
            f"{k} n={a['all'][k]['n']:,} still={_still(a['all'][k])}"
            for k in CARRIERS), file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rows), encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

#: One loan per case. ``(dq, nib, defer, adr, rate, term_bump)``; the last two
#: are ``None``/``0`` for "carry on unchanged". Every case's expectation is
#: stated in ``EXPECT`` and asserted, and **the three columns are given
#: different behaviour on purpose** so a mis-wired column cannot pass.
CASES = {
    # 63 rises and the contract moves: `still` must be 0 for nib
    "nib_moves": [("00", 0, 0, "", None, 0), ("01", 0, 0, "", None, 0),
                  ("02", 5000, 0, "", 3.0, 60), ("00", 5000, 0, "", None, 0)],
    # 108 rises and nothing moves: `still` must be 1 for defer
    "defer_still": [("00", 0, 0, "", None, 0), ("01", 0, 0, "", None, 0),
                    ("02", 0, 7000, "", None, 0), ("00", 0, 7000, "", None, 0)],
    # ADR P rises and nothing moves: `still` must be 1 for adr
    "adr_still": [("00", 0, 0, "", None, 0), ("01", 0, 0, "", None, 0),
                  ("02", 0, 0, "P", None, 0), ("00", 0, 0, "P", None, 0)],
    # ADR 7 is the none-of-the-above code and must NOT be an onset (pit 1).
    # **It starts blank and turns to `7`**, so a wrong ADR_REAL would produce a
    # rising edge here. The first version of this case carried `7` on every row
    # including the first, which is left truncation, so it could not produce an
    # onset under any definition and the test proved nothing. **A mutation run
    # caught that: adding `7` to ADR_REAL left the selftest green.**
    "adr_seven": [("00", 0, 0, "", None, 0), ("01", 0, 0, "", None, 0),
                  ("02", 0, 0, "7", None, 0), ("00", 0, 0, "7", None, 0)],
    # 63 and 108 rise on the same row: the pairing table must see it
    "nib_defer_same": [("00", 0, 0, "", None, 0), ("01", 0, 0, "", None, 0),
                       ("02", 4000, 4000, "", None, 0),
                       ("00", 4000, 4000, "", None, 0)],
    # 108 rises two months after 63: pairing must record `a first`
    "nib_then_defer": [("00", 0, 0, "", None, 0), ("01", 3000, 0, "", None, 0),
                       ("02", 3000, 0, "", None, 0),
                       ("03", 3000, 3000, "", None, 0),
                       ("00", 3000, 3000, "", None, 0)],
}

EXPECT_ONSETS = {"nib": 3, "defer": 3, "adr": 1}
#: Exact, not a threshold. `nib` has three fixture onsets and **one** of them
#: moves rate and term, so 2/3 is the right answer; the first version of this
#: test asserted "below 0.5" from a hand-wave about the fixture and failed on
#: correct output. **A pinned value catches a wiring change; a threshold picked
#: by eye catches the person who picked it.**
EXPECT_STILL = {"nib": 2.0 / 3.0, "defer": 1.0, "adr": 1.0}


def _synth(path: Path) -> list[str]:
    names = list(CASES)
    lines = []
    for L_, name in enumerate(names):
        lid = f"{920000000000 + L_}"
        rate, bal, rem, y, m, age = 5.0, 200000.0, 360, 2021, 1, 0
        for dq, nib, dfr, adr, rt, bump in CASES[name]:
            if rt is not None:
                rate = rt
            rem += bump
            f = [""] * K.NFIELDS
            f[1] = lid
            f[2] = f"{m:02d}{y:04d}"
            f[3] = "R"
            f[8] = f"{rate:.3f}"
            f[11] = f"{bal:.2f}"
            f[12] = "360"
            f[15] = str(age)
            f[16] = str(rem)
            f[17] = str(rem)
            f[18] = "012051"
            f[19] = "80"
            f[22] = "35"
            f[23] = "720"
            f[25] = "N"
            f[26] = "P"
            f[29] = "P"
            f[30] = "CA"
            f[39] = dq
            f[41] = "N"
            f[62] = f"{nib:.2f}" if nib else ""
            f[101] = "7"
            f[105] = adr
            f[107] = f"{dfr:.2f}" if dfr else ""
            lines.append("|".join(f))
            rem -= 1
            age += 1
            m += 1
            if m == 13:
                m, y = 1, y + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")
    return names


def _tag() -> str:
    import hashlib
    import inspect
    return hashlib.sha256(
        (inspect.getsource(_synth) + repr(CASES)).encode()).hexdigest()[:8]


def selftest() -> int:
    fails = []
    tag = _tag()
    root = K.CACHE / "_selftest_c104"
    zp = root / "raw" / f"2097Q1_{tag}.zip"
    if not zp.exists():
        _synth(zp)
        print(f"  built fixture {zp.name} (generator {tag})", file=sys.stderr)
    K.build_archive(zp, force=True, cache_root=root / "cache")
    # opened with COLS, not with every column: pit 30. A mutation sweep on
    # 2026-08-17 found this file was the only one of seven whose selftest did
    # not catch a column dropped from its own run-path list.
    with K.Core(zp.stem, cols=COLS, loan_cols=[],
                cache_root=root / "cache") as c:
        a = measure(c)

    for k in CARRIERS:
        d = a["all"][k]
        print(f"  {k:6} onsets={d['n']} decidable={d['decidable']} "
              f"still={_still(d)} rate={C._fmt(d, 'rate')} "
              f"term={C._fmt(d, 'term')}", file=sys.stderr)
        if d["n"] != EXPECT_ONSETS[k]:
            fails.append(f"{k}: {d['n']} onsets, expected {EXPECT_ONSETS[k]}")
    # pit 1: the `7` rows are present, they rise from blank, and they must not
    # have produced an onset. All three parts are needed or the check is empty.
    if a["adr_code_7"] == 0:
        fails.append("the fixture carries no `adr = 7` row, so the pit-1 "
                     "exclusion is untested")
    if a["adr_blank"] == 0:
        fails.append("no blank ADR row precedes the `7` rows, so a wrong "
                     "ADR_REAL could not produce a rising edge and the pit-1 "
                     "check is vacuous")
    # the three columns must not read the same, or a mis-wiring would pass
    got = {k: (a["all"][k]["still"] / a["all"][k]["decidable"]
               if a["all"][k]["decidable"] else None) for k in CARRIERS}
    for k, w in EXPECT_STILL.items():
        if got[k] is None or not np.isclose(got[k], w):
            fails.append(f"{k}: still={got[k]}, expected {w}")
    d = a["all"]["nib"]
    if d["rate"] != 1 or d["term"] != 1:
        fails.append(f"nib: rate moved {d['rate']}x, term {d['term']}x, "
                     "expected 1 and 1 on the same single onset")
    if len({round(v, 6) for v in got.values() if v is not None}) < 2:
        fails.append("the three columns read the same `still`; a mis-wired "
                     "column would pass unnoticed")

    pr = {p["pair"]: p for p in a["pairs"]}
    nd = pr["nib / defer"]
    print(f"  pairing nib/defer: both={nd['both']} same={nd['same_row']} "
          f"a_first={nd['a_first']} only_a={nd['only_a']} "
          f"only_b={nd['only_b']}", file=sys.stderr)
    if nd["same_row"] != 1:
        fails.append(f"nib/defer same_row={nd['same_row']}, expected 1")
    if nd["a_first"] != 1:
        fails.append(f"nib/defer a_first={nd['a_first']}, expected 1")
    if nd["only_a"] != 1 or nd["only_b"] != 1:
        fails.append(f"nib/defer only_a={nd['only_a']} only_b={nd['only_b']}, "
                     "expected 1 and 1")

    txt = render([dict(a, name="fixture")])

    # every table's rows must match its header's width. A published

    # results file was malformed on 2026-08-17 and the person who

    # generated it read it and quoted from it without noticing.

    for _c in K.check_markdown_tables(txt):

        fails.append(f"malformed table: {_c}")
    for need in ("## 1. The criterion", "## 2. The same, by window",
                 "## 3. Pairing", "## 4. Where the onsets sit"):
        if need not in txt:
            fails.append(f"render omits the section `{need}`")
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
