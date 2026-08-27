"""B10 / O18 on Freddie: naming the months where the balance does not move.

Pre-registered in the B10 availability register §32, **before this file
was written**. Every reading it can return is declared there.

What is already known and what is not
-------------------------------------
B8 §6.2.6 ruled out four candidates for the frozen months (interest-only, a
repayment arrangement, the settlement month, the leading edge of a delinquency
run); freezing accounts for 53.35% of the below-cluster months and **46.65% is
unnamed**. That residue is O18.

B10 §13 measured the same thing on Freddie and added the mechanism: of
1,618,044 month differences on the 2007 vintage, **84,275 (5.208%)** carry a
balance identical to the month before, and their ``P(t) / P_contract`` has a
median of **0.8086**, which is the interest share of a thirty-year payment
early in its life. A month whose balance did not move has ``P(t) = UPB * rate /
1200`` and nothing else.

**That is arithmetic, and it does not say why the month did not move.** O18
asks the second question, and Freddie carries a field Fannie does not: a
borrower-assistance status with forbearance, repayment plan and trial period as
separate codes. Fannie's 102/106 carries the `7` = "none of the above" trap
that cost a full scan once.

Earning the field, and why the anchors avoid a circle
------------------------------------------------------
C0b: appearance may enumerate, only behaviour may pick (§25's rule, unchanged).

* **A trial period implies a modification soon after.** A trial period *is* the
  months before a permanent modification, so months carrying that code should be
  followed by a modification flag inside a year at a rate far above baseline.
* **Forbearance piles into the COVID window.** The CARES Act forbearance of
  2020-21 was one enormous event, so one code's occurrences should concentrate
  there to a degree nothing else does.

**Neither anchor looks at whether the balance moved**, which is the whole point:
the thing being explained is kept out of the thing doing the identifying. Both
anchors must land on the same column or the field is not earned and §32.1 stops
the run before any cross-tabulation is read.

Usage::

    python experiments/b10_o18_assistance.py --selftest
    python experiments/b10_o18_assistance.py --earn --only 2019
    python experiments/b10_o18_assistance.py --run

Writes ``results/b10_o18_assistance.json``, ``diagnostic_only``.
**No omega. No B8 prediction. No triangles.** (§32.4)
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"
sys.path.insert(0, str(ROOT / "experiments"))

VINTAGE_RANGE = range(1999, 2027)
PERF_FIELDS = 35

#: Positions already earned. `b10_c8_1d_freddie.py` §11.1 confirmed the perf
#: width on twenty-eight archives; §2 enumerated the columns; the modification
#: flag and the balance are used here and neither is being re-identified.
P_SEQ, P_PERIOD, P_UPB, P_DELINQ = 0, 1, 2, 3
P_MODFLAG = 7
P_AGE = 4
MODFLAG_MOD = ("Y", "P")

#: §39.1's age split. §11.3 measured that Current Actual UPB is rounded to the
#: nearest $1,000 for ages 0 to 6 and reported to the cent from age 7, and §38.1
#: measured that those months carry **55.3% of every frozen month** at a rate of
#: 47.83%. Crossing the assistance code against that split turns §38.3's
#: "about 41.8%" from an upper bound into an exact residue, and prints the
#: overlap `a` that §38.3 never computed.
AGE_SPLIT = 8

#: §32.1's appearance filter. Enumerates, never picks.
MAX_LEVELS = 5
MIN_BLANK_SHARE = 0.5

#: **A column cannot be earned by predicting itself.** Anchor one's outcome is
#: "a modification follows", read off `P_MODFLAG`, so that column and every
#: sub-field of it are circular by construction: on the first run the top three
#: rows were `col 7 = 'Y'`, `col 23 = 'N'` and `col 7 = 'P'`, all at rate
#: 1.00000, and the real signal (`col 29 = 'T'`, lift 73.7) sat fourth.
#:
#: §25's constants block already carried this rule -- *"a column cannot be
#: earned twice, and leaving the note rate in the FICO candidate set would let
#: it win its own anchor trivially"* -- and this file did not carry it over.
#: Same family as §22.4.2: **the rule was written correctly and the
#: implementation had nothing in it that could make the rule fire.**
#:
#: The exclusion is structural, not a name list: a candidate whose non-blank
#: rows sit inside the modification flag's non-blank rows is a sub-field of the
#: outcome. The measured containment prints beside every exclusion, so a column
#: dropped at 0.991 looks different from one dropped at 1.000.
CIRCULAR_CONTAINMENT = 0.99

#: How long after a trial period a modification still counts as "soon after".
#: **A property of the instrument, declared before the run**: Fannie's trial
#: periods ran three to four months and HAMP's ran three plus extensions, so a
#: year is generous rather than tuned. The lift is reported against the same
#: window computed on all other months, so the window cancels out of the
#: comparison and only its generosity remains.
TRIAL_WINDOW_MONTHS = 12

#: §4's calendar windows, by the month's own period.
WINDOWS = (("pre_crisis", 0, 2008), ("hamp", 2009, 2016), ("flex", 2017, 2019),
           ("covid", 2020, 2022), ("post2023", 2023, 9999))

#: The COVID forbearance window for anchor two. Two years, and the anchor is a
#: **ranking** across codes rather than a threshold on any one of them.
COVID_YEARS = (2020, 2021)


def archive(vintage: int) -> Path:
    return RAW / f"sample_{vintage}.zip"


def vintages_on_disk() -> list:
    return [v for v in VINTAGE_RANGE if archive(v).exists()]


def perf_loans(vintage: int):
    """Yield ``(loan_seq, [fields, ...])``, one loan at a time, in file order."""
    with zipfile.ZipFile(archive(vintage)) as zf:
        with zf.open(f"sample_perf_{vintage}.txt") as raw:
            seq, batch = None, []
            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.rstrip("\r\n").split("|")
                if f[P_SEQ] != seq:
                    if seq is not None:
                        yield seq, batch
                    seq, batch = f[P_SEQ], []
                batch.append(f)
            if seq is not None:
                yield seq, batch


def next_period(p: int) -> int:
    y, m = divmod(p, 100)
    return y * 100 + m + 1 if m < 12 else (y + 1) * 100 + 1


def months_between(a: int, b: int) -> int:
    return (b // 100 - a // 100) * 12 + (b % 100 - a % 100)


def window_of(period: int) -> str:
    y = period // 100
    for name, lo, hi in WINDOWS:
        if lo <= y <= hi:
            return name
    return "post2023"


# ---------------------------------------------------------------------------
# One pass. The anchors and the cross-tabulation are computed together because
# they are independent by construction (§32.1): neither anchor looks at whether
# the balance moved. The cross-tabulation is **not printed** unless the anchors
# land (§32.5).
# ---------------------------------------------------------------------------

def scan(vintage: int, candidates=None) -> dict:
    out = {
        "vintage": vintage, "rows": 0, "loans": 0,
        "levels": defaultdict(Counter),         # col -> value -> n
        "blank": Counter(), "seen_cols": 0,
        # anchor one: (col, value) -> [n_with_mod_soon, n_total]
        "trial": defaultdict(lambda: [0, 0]),
        "mod_soon_baseline": [0, 0],
        "nonblank": Counter(), "nonblank_with_mod": Counter(),
        # anchor two: (col, value) -> year -> n
        "by_year": defaultdict(lambda: defaultdict(int)),
        # the cross-tabulation
        "pairs": 0, "frozen": 0,
        "frozen_by_code": defaultdict(Counter),     # col -> code -> n
        "moving_by_code": defaultdict(Counter),
        "frozen_by_window_code": defaultdict(Counter),   # (col,win) -> code
        "pairs_by_window": Counter(),
        "frozen_by_window": Counter(),
        # §39.1's 2 x 2, keyed (col, "lt8"/"ge8", code)
        "frozen_by_age_code": Counter(),
        "pairs_by_age": Counter(),
    }
    for seq, rows in perf_loans(vintage):
        out["loans"] += 1
        out["rows"] += len(rows)
        n = len(rows)
        if n and out["seen_cols"] == 0:
            out["seen_cols"] = len(rows[0])
        per = [int(r[P_PERIOD]) for r in rows]
        modrow = [r[P_MODFLAG].strip() in MODFLAG_MOD for r in rows]
        # index of the first modification at or after each row, for anchor one
        nxt_mod = [None] * n
        last = None
        for i in range(n - 1, -1, -1):
            if modrow[i]:
                last = per[i]
            nxt_mod[i] = last

        cols = candidates if candidates is not None else range(len(rows[0]))
        for i, r in enumerate(rows):
            soon = (nxt_mod[i] is not None
                    and 0 <= months_between(per[i], nxt_mod[i])
                    <= TRIAL_WINDOW_MONTHS)
            out["mod_soon_baseline"][0] += 1 if soon else 0
            out["mod_soon_baseline"][1] += 1
            for c in cols:
                if c >= len(r):
                    continue
                v = r[c].strip()
                if not v:
                    out["blank"][c] += 1
                    continue
                out["levels"][c][v] += 1
                out["nonblank"][c] += 1
                if r[P_MODFLAG].strip():
                    out["nonblank_with_mod"][c] += 1
                t = out["trial"][(c, v)]
                t[0] += 1 if soon else 0
                t[1] += 1
                out["by_year"][(c, v)][per[i] // 100] += 1

        # the cross-tabulation, on consecutive pairs with both balances positive
        for i in range(1, n):
            if per[i] != next_period(per[i - 1]):
                continue
            try:
                a, b = float(rows[i - 1][P_UPB]), float(rows[i][P_UPB])
            except ValueError:
                continue
            if not (a > 0 and b > 0):
                continue
            out["pairs"] += 1
            win = window_of(per[i])
            out["pairs_by_window"][win] += 1
            try:
                ages = ("ge8" if (int(rows[i - 1][P_AGE]) >= AGE_SPLIT
                                  and int(rows[i][P_AGE]) >= AGE_SPLIT)
                        else "lt8")
            except ValueError:
                ages = "lt8"
            out["pairs_by_age"][ages] += 1
            froz = (a == b)
            if froz:
                out["frozen"] += 1
                out["frozen_by_window"][win] += 1
            for c in cols:
                if c >= len(rows[i]):
                    continue
                code = rows[i][c].strip() or "(blank)"
                if froz:
                    out["frozen_by_code"][c][code] += 1
                    out["frozen_by_window_code"][(c, win)][code] += 1
                    out["frozen_by_age_code"][(c, ages, code)] += 1
                else:
                    out["moving_by_code"][c][code] += 1
    return out


def merge(acc: dict, one: dict) -> dict:
    if acc is None:
        return one
    for k in ("rows", "loans", "pairs", "frozen"):
        acc[k] += one[k]
    acc["blank"].update(one["blank"])
    acc["pairs_by_window"].update(one["pairs_by_window"])
    acc["frozen_by_window"].update(one["frozen_by_window"])
    for c, cnt in one["levels"].items():
        acc["levels"][c].update(cnt)
    for c, cnt in one["frozen_by_code"].items():
        acc["frozen_by_code"][c].update(cnt)
    for c, cnt in one["moving_by_code"].items():
        acc["moving_by_code"][c].update(cnt)
    for k, cnt in one["frozen_by_window_code"].items():
        acc["frozen_by_window_code"][k].update(cnt)
    for k, t in one["trial"].items():
        acc["trial"][k][0] += t[0]
        acc["trial"][k][1] += t[1]
    for k, d in one["by_year"].items():
        for y, n in d.items():
            acc["by_year"][k][y] += n
    acc["mod_soon_baseline"][0] += one["mod_soon_baseline"][0]
    acc["mod_soon_baseline"][1] += one["mod_soon_baseline"][1]
    acc["nonblank"].update(one["nonblank"])
    acc["nonblank_with_mod"].update(one["nonblank_with_mod"])
    acc["frozen_by_age_code"].update(one["frozen_by_age_code"])
    acc["pairs_by_age"].update(one["pairs_by_age"])
    acc["seen_cols"] = acc["seen_cols"] or one["seen_cols"]
    return acc


def candidates_of(acc: dict) -> list:
    """§32.1's appearance filter: few values, mostly blank. Picks nothing."""
    out = []
    for c, cnt in acc["levels"].items():
        tot = sum(cnt.values()) + acc["blank"].get(c, 0)
        if not tot:
            continue
        if len(cnt) <= MAX_LEVELS and acc["blank"].get(c, 0) / tot >= MIN_BLANK_SHARE:
            out.append(c)
    return sorted(out)


def circular_cols(acc: dict, cands) -> dict:
    """Candidates whose non-blank rows sit inside the outcome's. See the
    `CIRCULAR_CONTAINMENT` note: these cannot be earned by anchor one."""
    out = {}
    for c in cands:
        nb = acc["nonblank"].get(c, 0)
        if not nb:
            continue
        share = acc["nonblank_with_mod"].get(c, 0) / nb
        if c == P_MODFLAG or share >= CIRCULAR_CONTAINMENT:
            out[c] = round(share, 5)
    return out


def anchor_trial(acc: dict, cands) -> list:
    """A trial period is followed by a modification. Ranked by lift.

    Columns that are sub-fields of the outcome are removed first, because a
    column cannot be earned by predicting itself (`CIRCULAR_CONTAINMENT`).
    """
    b_hit, b_tot = acc["mod_soon_baseline"]
    base = b_hit / b_tot if b_tot else 0.0
    circ = circular_cols(acc, cands)
    rows = []
    for (c, v), (hit, tot) in acc["trial"].items():
        if c not in cands or c in circ or tot < 100:
            continue
        rate = hit / tot
        rows.append({"col": c, "code": v, "n": tot, "rate": round(rate, 5),
                     "lift": round(rate / base, 3) if base else float("inf")})
    rows.sort(key=lambda d: -d["lift"])
    return rows


def anchor_covid(acc: dict, cands) -> list:
    """Forbearance piles into 2020-21. Ranked by that share, not thresholded."""
    rows = []
    for (c, v), years in acc["by_year"].items():
        if c not in cands:
            continue
        tot = sum(years.values())
        if tot < 100:
            continue
        cov = sum(n for y, n in years.items()
                  if COVID_YEARS[0] <= y <= COVID_YEARS[1])
        rows.append({"col": c, "code": v, "n": tot,
                     "covid_share": round(cov / tot, 5),
                     "peak_year": max(years, key=years.get)})
    rows.sort(key=lambda d: -d["covid_share"])
    return rows


#: Rows read in the appearance pass. **The enumeration does not need the whole
#: file**: a column's value set and blank share are visible in the first tens of
#: thousands of rows, and the appearance step picks nothing anyway (§32.1). The
#: first version looped all thirty-five columns over every one of 74.94M rows
#: and did not finish a single vintage inside a minute.
PROFILE_ROWS = 200_000


def profile_pass(vintages) -> dict:
    """Column shapes from a bounded prefix. Enumerates, never picks."""
    lev, blank, rows, ncol = defaultdict(Counter), Counter(), 0, 0
    for v in vintages:
        for _, batch in perf_loans(v):
            for r in batch:
                ncol = ncol or len(r)
                rows += 1
                for c in range(len(r)):
                    s = r[c].strip()
                    if s:
                        lev[c][s] += 1
                    else:
                        blank[c] += 1
            if rows >= PROFILE_ROWS:
                break
        if rows >= PROFILE_ROWS:
            break
    return {"levels": lev, "blank": blank, "rows": rows, "cols": ncol}


def cmd_earn(only, verbose=True) -> tuple:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    prof = profile_pass(vs)
    cands = candidates_of(prof)
    if verbose:
        print(f"§32.1, earning the field.")
        print(f"  appearance pass: {prof['rows']:,} rows, {prof['cols']} "
              f"columns (bounded, and it picks nothing)")
        print(f"  candidates: {cands}")
        for c in cands:
            tot = sum(prof["levels"][c].values()) + prof["blank"].get(c, 0)
            print(f"    col {c:>3}  blank {prof['blank'].get(c,0)/tot:.1%}   "
                  f"{dict(prof['levels'][c].most_common(6))}")
        print()
    if not cands:
        print("  **no candidate columns.** Behaviour cannot pick from nothing.")
        return {"levels": defaultdict(Counter), "blank": Counter()}, []
    acc = None
    for v in vs:
        acc = merge(acc, scan(v, candidates=cands))
        if verbose:
            print(f"  scanned {v}  rows {acc['rows']:>12,}  "
                  f"pairs {acc['pairs']:>12,}  frozen {acc['frozen']:>11,}")
    if verbose:
        print(f"\n  {len(vs)} vintages, {acc['rows']:,} perf rows.")
        t = anchor_trial(acc, cands)
        b_hit, b_tot = acc["mod_soon_baseline"]
        circ = circular_cols(acc, cands)
        print(f"\n  --- anchor 1: a trial period implies a modification within "
              f"{TRIAL_WINDOW_MONTHS} months ---")
        print(f"    excluded as sub-fields of the outcome (a column cannot be "
              f"earned by predicting itself):")
        for c, s in sorted(circ.items()):
            print(f"      col {c:>3}  {s:.5f} of its non-blank rows also carry "
                  f"a modification flag"
                  + ("   <- the outcome column itself" if c == P_MODFLAG
                     else ""))
        print(f"    baseline over all rows: {b_hit/b_tot:.5f}")
        for r in t[:6]:
            print(f"    col {r['col']:>3} = {r['code']!r:<5}  rate "
                  f"{r['rate']:.5f}  lift {r['lift']:>8.3f}  n = {r['n']:,}")

        cv = anchor_covid(acc, cands)
        print(f"\n  --- anchor 2: forbearance piles into "
              f"{COVID_YEARS[0]}-{COVID_YEARS[1]} ---")
        for r in cv[:6]:
            print(f"    col {r['col']:>3} = {r['code']!r:<5}  covid share "
                  f"{r['covid_share']:.4f}  peak {r['peak_year']}  "
                  f"n = {r['n']:,}")

        c1 = t[0]["col"] if t else None
        c2 = cv[0]["col"] if cv else None
        ok = c1 is not None and c1 == c2
        print(f"\n  anchor 1 picks col {c1}, anchor 2 picks col {c2}  ->  "
              f"{'EARNED' if ok else '**NOT EARNED**, §32.1 stops here'}")
        if not ok:
            print("    Two anchors on two columns is not an identification. Do "
                  "not widen a filter until they agree.")
    return acc, cands


def two_by_two_table(acc: dict, col: int, codes) -> dict:
    """§39.1: every frozen month, by the age grid and by the assistance code.

    The two names §38.3 listed are both **attributes of a month**, so their
    union is a set operation and the residue `d` is exact rather than the bound
    §38.3 reported. The termination-adjacent excess is **not** here: it is a
    rate difference and does not name a set of months (§39.0, §39.2).
    """
    cell = Counter()
    for (c_, ag, code), n in acc["frozen_by_age_code"].items():
        if c_ != col:
            continue
        cell[(ag, "code" if code in codes else "none")] += n
    a_ = cell[("lt8", "code")]
    b_ = cell[("ge8", "code")]
    c_ = cell[("lt8", "none")]
    d_ = cell[("ge8", "none")]
    tot = a_ + b_ + c_ + d_
    return {"a_lt8_code": a_, "b_ge8_code": b_, "c_lt8_nocode": c_,
            "d_ge8_nocode": d_, "union": a_ + b_ + c_, "residue": d_,
            "frozen_total": tot, "age_split": AGE_SPLIT,
            "pairs_by_age": dict(acc["pairs_by_age"])}


def print_two_by_two(t: dict) -> None:
    a_, b_, c_, d_ = (t["a_lt8_code"], t["b_ge8_code"],
                      t["c_lt8_nocode"], t["d_ge8_nocode"])
    tot = max(1, t["frozen_total"])
    print(f"\n{'=' * 74}\n  §39.1's 2 x 2 over every frozen month. "
          f"The grid is age <= {AGE_SPLIT - 1} (§11.3, §38.1).\n{'=' * 74}")
    print(f"    {'':<12} {'age <= 7':>14} {'age >= 8':>14} {'row':>14}")
    print(f"    {'F/R/T':<12} {a_:>14,} {b_:>14,} {a_ + b_:>14,}")
    print(f"    {'(blank)':<12} {c_:>14,} {d_:>14,} {c_ + d_:>14,}")
    print(f"    {'col':<12} {a_ + c_:>14,} {b_ + d_:>14,} {tot:>14,}")
    print(f"\n    named by either name (a+b+c) {a_ + b_ + c_:>12,}  "
          f"{(a_ + b_ + c_) / tot:>8.4%}")
    print(f"    **residue d, exact, not a bound**  {d_:>12,}  {d_ / tot:>8.4%}")
    print(f"    overlap a (code AND grid)          {a_:>12,}  "
          f"{a_ / max(1, a_ + b_):>8.4%} of all coded frozen months")
    print("\n  §39.3, written before these numbers:")
    print("    a is most of the coded months -> the code's independent "
          "contribution is far below\n      §33.1's 2.16%, and that section "
          "must be quoted with this line")
    print("    a is small                    -> the two names barely overlap "
          "and §33.1's 2.16% adds\n      to the grid directly")
    print("    d below §38.3's 41.8%         -> the bound tightens; report the "
          "exact value")
    print("    d above it                    -> **§38.3 subtracted too much**, "
          "which is exactly the\n      defect §39.0 named: a rate difference "
          "treated as an attribute")
    print("\n  §39.2: the termination-adjacent excess (§38.2) is **not** in this "
          "table and must not\n  be subtracted from d. It is a rate difference "
          "inside d, describing its shape, not a\n  slice taken out of it.")


def cmd_run(only, age_split: bool = False) -> int:
    acc, cands = cmd_earn(only, verbose=True)
    t, cv = anchor_trial(acc, cands), anchor_covid(acc, cands)
    col = t[0]["col"] if t and cv and t[0]["col"] == cv[0]["col"] else None
    if col is None:
        print("\n  Field not earned. §32.5: no cross-tabulation is printed, "
              "because a reading whose field is not identified is not a "
              "reading.")
        return 1

    codes = sorted(acc["levels"][col])
    fz, mv = acc["frozen_by_code"][col], acc["moving_by_code"][col]
    print(f"\n{'=' * 74}\n  §32.2, on column {col}. "
          f"pairs {acc['pairs']:,}, frozen {acc['frozen']:,} "
          f"({acc['frozen']/max(1,acc['pairs']):.4%})\n"
          f"  **Denominator differs from §13's 5.208%, which ran on gated "
          f"segments. The two are not compared (§32.2).**\n{'=' * 74}")

    print(f"\n  frozen -> code")
    named = 0
    for code in ["(blank)"] + codes:
        n = fz.get(code, 0)
        if not n:
            continue
        if code != "(blank)":
            named += n
        print(f"    {code!r:<10} {n:>10,}  {n/max(1,acc['frozen']):>8.4%}")
    print(f"    {'NAMED':<10} {named:>10,}  "
          f"{named/max(1,acc['frozen']):>8.4%}   <- coverage")
    print(f"    {'RESIDUE':<10} {acc['frozen']-named:>10,}  "
          f"{(acc['frozen']-named)/max(1,acc['frozen']):>8.4%}   "
          f"<- **§32.2's main deliverable: still unnamed**")

    print(f"\n  code -> frozen (the other direction)")
    for code in codes:
        f_, m_ = fz.get(code, 0), mv.get(code, 0)
        if f_ + m_ == 0:
            continue
        print(f"    {code!r:<10} months {f_+m_:>10,}   frozen {f_:>10,}  "
              f"{f_/(f_+m_):>8.4%}")
    f_, m_ = fz.get("(blank)", 0), mv.get("(blank)", 0)
    print(f"    {'(blank)':<10} months {f_+m_:>10,}   frozen {f_:>10,}  "
          f"{f_/max(1,f_+m_):>8.4%}   <- §32.3 row three compares against this")

    print(f"\n  per window (§32.3 row four: do not collapse these)")
    print(f"    {'window':<11} {'pairs':>11} {'frozen':>10} {'froz%':>8}  "
          + "  ".join(f"{c!r:>9}" for c in codes) + f"  {'named%':>8}")
    per_win = {}
    for name, _, _ in WINDOWS:
        p = acc["pairs_by_window"].get(name, 0)
        fr = acc["frozen_by_window"].get(name, 0)
        cc = acc["frozen_by_window_code"].get((col, name), Counter())
        nm = sum(cc.get(c, 0) for c in codes)
        per_win[name] = {"pairs": p, "frozen": fr,
                         "by_code": {c: cc.get(c, 0) for c in codes},
                         "named": nm}
        if not p:
            continue
        print(f"    {name:<11} {p:>11,} {fr:>10,} {fr/p:>8.3%}  "
              + "  ".join(f"{cc.get(c,0):>9,}" for c in codes)
              + f"  {nm/max(1,fr):>8.3%}")

    print("\n  §32.3, and the readings were written before these numbers:")
    print("    the three codes are the MAJORITY of frozen months -> these "
          "months are institutional\n      assistance on this carrier; report "
          "the coverage and list the remainder separately")
    print("    the three codes are a MINORITY -> naming covers part of it "
          "only. **The remainder is\n      still unnamed**; O18 narrows on "
          "this carrier, it does not close")
    print("    the codes sit at the same share on frozen and moving months -> "
          "the field is unrelated\n      to freezing and is not O18's answer")
    print("    the windows differ in shape -> quote per window; COVID "
          "forbearance and HAMP trial\n      periods are not one thing")
    print("\n  §32.4: this name does NOT transfer to Fannie. B8 may check for "
          "a compatible shape\n  and compatibility is not identification.")

    two_by_two = None
    if age_split:
        two_by_two = two_by_two_table(acc, col, codes)
        print_two_by_two(two_by_two)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_o18_assistance.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "o18_assistance", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §32. Naming only; "
             "no omega, no B8 prediction. The name does not transfer to Fannie "
             "(§32.4).",
         "column_earned": col,
         "anchor_trial": t[:6], "anchor_covid": cv[:6],
         "pairs": acc["pairs"], "frozen": acc["frozen"],
         "frozen_by_code": dict(fz), "moving_by_code": dict(mv),
         "named": named, "residue": acc["frozen"] - named,
         "per_window": per_win,
         "two_by_two_age_code": two_by_two,
         "age_split_on": bool(age_split),
         "trial_window_months": TRIAL_WINDOW_MONTHS},
        indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_selftest() -> int:
    print("b10_o18_assistance selftest. Constructed cases, answers first.\n")
    fails = []

    def chk(name, got, want):
        ok = got == want
        print(f"  {name:<50} {str(got):<20} {'ok' if ok else f'FAIL {want}'}")
        if not ok:
            fails.append(name)

    print("  period arithmetic:")
    chk("    next_period rolls the year", next_period(200912), 201001)
    chk("    and does not otherwise", next_period(200901), 200902)
    chk("    months_between across a year", months_between(200911, 201002), 3)
    chk("    months_between is signed", months_between(201002, 200911), -3)

    print("\n  window_of:")
    for p, w in ((200801, "pre_crisis"), (200901, "hamp"), (201612, "hamp"),
                 (201701, "flex"), (201912, "flex"), (202001, "covid"),
                 (202212, "covid"), (202301, "post2023")):
        chk(f"    {p}", window_of(p), w)

    print("\n  candidates_of, appearance only:")
    acc = {"levels": {1: Counter({"F": 10, "R": 5}),
                      2: Counter({str(i): 3 for i in range(9)}),
                      3: Counter({"Y": 900})},
           "blank": Counter({1: 985, 2: 973, 3: 100})}
    chk("    few values and mostly blank survives", candidates_of(acc), [1])
    print("    (col 2 has nine values, col 3 is only 10% blank; neither is\n"
          "     rejected by name or by what it means, only by shape)")

    print("\n  anchor_trial, lift against the baseline:")
    acc2 = {"levels": {}, "trial": {(1, "T"): [190, 200], (1, "F"): [20, 400]},
            "mod_soon_baseline": [1000, 10000],
            "nonblank": Counter({1: 600}), "nonblank_with_mod": Counter({1: 6})}
    rows = anchor_trial(acc2, [1])
    chk("    the trial code leads", rows[0]["code"], "T")
    chk("    with lift 9.5", rows[0]["lift"], 9.5)
    chk("    and the other code is below baseline", rows[1]["lift"], 0.5)

    print("\n  a column cannot be earned by predicting itself:")
    acc4 = {"levels": {}, "trial": {(1, "T"): [190, 200], (7, "Y"): [500, 500],
                                    (2, "N"): [300, 300]},
            "mod_soon_baseline": [1000, 10000],
            "nonblank": Counter({1: 600, 7: 500, 2: 300}),
            "nonblank_with_mod": Counter({1: 6, 7: 500, 2: 300})}
    chk("    the outcome column and its sub-field are named",
        sorted(circular_cols(acc4, [1, 2, 7])), [2, 7])
    chk("    and neither reaches the ranking, which keeps only col 1",
        [r["col"] for r in anchor_trial(acc4, [1, 2, 7])], [1])
    print("    (a perfect 1.00000 on this anchor is what a sub-field of the\n"
          "     outcome scores; the real code scored 0.679 on real data and\n"
          "     sat fourth until these two were removed)")

    print("\n  anchor_covid, share in the window:")
    acc3 = {"levels": {}, "by_year": {
        (1, "F"): {2019: 10, 2020: 400, 2021: 400, 2022: 10},
        (1, "T"): {2010: 500, 2020: 20, 2021: 10}}}
    rows = anchor_covid(acc3, [1])
    chk("    forbearance leads on the covid share", rows[0]["code"], "F")
    chk("    its peak year is inside the window",
        rows[0]["peak_year"] in COVID_YEARS, True)
    chk("    the other code peaks in HAMP", rows[1]["peak_year"], 2010)

    print("\n  the two anchors must agree, and disagreement is not a tie-break:")
    a = anchor_trial(acc2, [1])[0]["col"]
    b = anchor_covid(acc3, [1])[0]["col"]
    chk("    same column here", a == b, True)

    print("\n  §39.1's 2 x 2, **and the printer is actually called**:")
    # Why this case exists. The first version of `--age-split` was patched in
    # by text replacement; one replacement matched and one silently did not, so
    # `two_by_two` was referenced and never defined. `ast.parse` passed, because
    # an undefined name is a runtime error, and the defect surfaced only after a
    # 74.9M-row scan had finished and the JSON writer reached for it.
    # **A syntax check cannot catch a missing definition. Calling the code can.**
    acc = {"frozen_by_age_code": Counter({
        (29, "lt8", "F"): 7, (29, "ge8", "F"): 3,
        (29, "lt8", "(blank)"): 500, (29, "ge8", "(blank)"): 490,
        (7, "lt8", "F"): 999}),          # another column must not leak in
        "pairs_by_age": Counter({"lt8": 1000, "ge8": 9000})}
    t = two_by_two_table(acc, 29, ["F", "R", "T"])
    chk("    a, the overlap", t["a_lt8_code"], 7)
    chk("    b, coded and past the grid", t["b_ge8_code"], 3)
    chk("    c, the grid alone", t["c_lt8_nocode"], 500)
    chk("    d, the exact residue", t["d_ge8_nocode"], 490)
    chk("    union is a+b+c", t["union"], 510)
    chk("    and the four cells account for everything",
        t["a_lt8_code"] + t["b_ge8_code"] + t["c_lt8_nocode"]
        + t["d_ge8_nocode"], t["frozen_total"])
    chk("    another column does not leak in", t["frozen_total"], 1000)
    print_two_by_two(t)
    payload = json.dumps({"two_by_two_age_code": t}, default=str)
    chk("    and it serialises", "d_ge8_nocode" in payload, True)

    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--earn", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", action="append")
    ap.add_argument("--age-split", action="store_true",
                    help="§39.1's 2 x 2. Off by default and the counters it "
                         "adds touch nothing else, so every existing number "
                         "reproduces bit for bit (SESSION_INIT lesson four).")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.earn:
        cmd_earn(a.only)
        return 0
    if a.run:
        return cmd_run(a.only, a.age_split)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
