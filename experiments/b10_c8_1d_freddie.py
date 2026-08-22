"""B10 / C8-1d on Freddie: separating the contract payment from the habitual one.

Pre-registered in the B10 availability register §12, **before this file was
written**. Every reading it can return is declared there and nothing is added here.

Why this file exists
--------------------
C8-1d was registered and then, in the same ruling, registered as *not
runnable*. The reason, as it was written at the time:

    `P` 的下界估计的是借款人**习惯支付**的水平月供。一个每月都把还款凑成同一个
    整数的借款人，其 `P` 水平但不等于合同月供，**本测分不开两者**。分开需要放款侧
    字段（原始余额、原始利率、原始期限），且那些位置**不在 C0b 确认的锚点表里**。

Freddie publishes those three fields separately and two of the three have been
earned by behaviour rather than taken from a layout document
(the B10 availability register §10.1):

* original interest rate matches the first month's current rate to ``5e-4`` on
  **99.958%** of 1,362,490 loans;
* the identity ``remaining term + loan age == original term`` holds exactly on
  **99.924%**;
* original UPB is **not** earned: it sits on a $1,000 grid (100.000%), and §12.1
  shows that grid is the same size as the effect this stage is trying to detect.

So original UPB is never used as an input. §12.2's route is used instead.

The construction
----------------
The balance after ``k`` payments of a level-payment loan is the present value of
the payments still owed::

    U_k = U0 * [1 - (1+i)^(-(n-k))] / [1 - (1+i)^(-n)]

and ``n - k`` is not computed, it is **read**: it is perf field 6, whose identity
against loan age is the anchor above. Substituting the level payment gives the
contract payment **without the original balance appearing at all**::

    P_contract = U_k * i / (1 - (1+i)^(-rem_k))

The original balance is still backed out, but only to run §12.2's gate::

    U0_hat = U_k * [1 - (1+i)^(-n)] / [1 - (1+i)^(-rem_k)]

``U0_hat`` has to land inside ``orig U0 ± 500`` or the loan saw a curtailment
before month ``k`` and leaves the domain. That gate is structural: it is a
statement about an amortisation identity, not about the world.

The age-8 rule, which is not optional
-------------------------------------
The B10 availability register §11.3 measured Freddie's disclosure grid:
**Current Actual UPB is rounded to the nearest $1,000 for loan ages 0 to 6 and
reported to the cent from age 7.** So every ``P(t)`` for ``t`` in 1..7 is rounding
noise of order ±$1,000, two orders of magnitude above a real payment, and the
6->7 step is broken too because one side is rounded and the other is not.
**The first usable difference is age 7 to 8.** Records at age <= 7 leave the
estimator's domain and the count that left prints beside the reading.

Reading
-------
Three objects, all printed, **no threshold anywhere in this file**, and no line is drawn on an
estimator:

* ``P_impl / P_contract``      -> mass at 1.000 means the borrower pays the contract
* ``P_impl mod 10, 25, 50, 100`` -> mass above the background rate means rounding
* ``P_impl - P_contract``      -> mass on a positive round number means contract
  plus a fixed extra principal

The three can hold at once. §12.4 says that is a mixed population and it is
reported as one, not resolved by picking a cell.

Usage::

    python experiments/b10_c8_1d_freddie.py --selftest
    python experiments/b10_c8_1d_freddie.py --depth --only 2007 --only 2019
    python experiments/b10_c8_1d_freddie.py --depth
    python experiments/b10_c8_1d_freddie.py --run

Writes ``results/b10_c8_1d_depth.json`` / ``results/b10_c8_1d.json``, both with
``diagnostic_only`` set from the first version of the writer, so the
renderer skips it while the record stays on disk as evidence. Reads the archives with ``ZipFile.open`` and **never extracts
anything to disk**.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import statistics
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"

VINTAGES = tuple(range(1999, 2027))

# ---------------------------------------------------------------------------
# Field positions. Zero-based. Confirmed against the files themselves rather
# than against a layout document: `--depth` prints the field count of every
# archive and all twenty-eight read `orig = 31`, `perf = 35`
# (the B10 availability register §11.1).
# ---------------------------------------------------------------------------
P_SEQ, P_PERIOD, P_UPB, P_DELINQ, P_AGE, P_REM = 0, 1, 2, 3, 4, 5
P_MODFLAG, P_ZEROBAL, P_RATE = 7, 8, 10
O_UPB, O_RATE, O_AMORT, O_SEQ, O_TERM = 10, 12, 15, 19, 21

ORIG_FIELDS, PERF_FIELDS = 31, 35

#: §12.3. The first usable monthly difference is age 7 -> 8, because age <= 6 is
#: on the $1,000 grid and the 6 -> 7 step mixes a rounded side with an exact one.
MIN_AGE = 8

#: §12.2's gate. Half of the disclosure grid: `orig U0` is `U0` rounded to the
#: nearest $1,000, so an exact back-out must land within half a grid step. This
#: is not a tuned tolerance, it is the grid (§10.3, 100.000% of orig UPB values
#: are multiples of 1000).
U0_HALF_GRID = 500.0

#: §12.5's segment-length strata. Boundaries are the estimator's own: the lower
#: edge is `MIN_AGE`, and the rest double. The stratification exists so that the
#: minimum's upward bias on short segments is visible rather than argued.
LENGTH_BINS = ((8, 12), (13, 24), (25, 60), (61, 10 ** 9))

#: Round-number moduli reported against their own background rates.
MODULI = (10, 25, 50, 100)

#: Half-width of the "lands on a round number" window, in dollars. Half a cent,
#: because ``P_impl`` is built from balances reported to the cent.
ROUND_TOL = 0.005


def background_rate(m: float) -> float:
    """Chance a continuous dollar amount falls within ``ROUND_TOL`` of a multiple.

    **This is the window over the modulus, not one over the modulus.** ``P_impl``
    is continuous in dollars and cents, so landing on a multiple of 10 by chance
    has probability ``0.01 / 10 = 0.001``, not ``0.1``. Writing ``1/m`` here would
    be the background for an amount already known to be a whole number of
    dollars, and against that wrong baseline an observed 0.0066 reads as one
    fifteenth of chance when it is in fact six times chance. **The sign of the
    reading flips on this line**, so it is a function with its arithmetic written
    out rather than a literal.
    """
    return 2.0 * ROUND_TOL / m


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def annuity_factor(i: float, m: int) -> float:
    """``1 - (1+i)^(-m)``, the annuity numerator, guarded at ``i == 0``."""
    if m <= 0:
        return 0.0
    if i == 0.0:
        return float(m)
    return 1.0 - (1.0 + i) ** (-m)


def contract_payment(upb: float, i: float, rem: int) -> float:
    """The level payment implied by a balance, a rate and a remaining term.

    This is §12.2's substitution: the original balance cancels, so the $1,000
    grid it sits on never enters. ``rem`` is read from perf field 6.
    """
    if i == 0.0:
        return upb / rem if rem > 0 else float("nan")
    a = annuity_factor(i, rem)
    return float("nan") if a <= 0.0 else upb * i / a


def backout_u0(upb: float, i: float, rem: int, term: int) -> float:
    """Recover the original balance from a later one. §12.2's gate input."""
    a_rem, a_n = annuity_factor(i, rem), annuity_factor(i, term)
    return float("nan") if a_rem <= 0.0 else upb * a_n / a_rem


def implied_payment(upb_prev: float, upb_now: float, rate_pct: float) -> float:
    """C8-1c's formula, unchanged: principal retired plus interest accrued."""
    return (upb_prev - upb_now) + upb_prev * rate_pct / 1200.0


def next_period(period: int) -> int:
    """``YYYYMM`` plus one month."""
    y, m = divmod(period, 100)
    return y * 100 + m + 1 if m < 12 else (y + 1) * 100 + 1


# ---------------------------------------------------------------------------
# Reading. Streamed out of the archives, nothing extracted.
# ---------------------------------------------------------------------------

def archive(vintage: int) -> Path:
    return RAW / f"sample_{vintage}.zip"


def _lines(zf: zipfile.ZipFile, member: str):
    with zf.open(member) as raw:
        for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
            line = line.rstrip("\r\n")
            if line:
                yield line.split("|")


def read_orig(vintage: int) -> tuple[dict, dict]:
    """``{loan_seq: (orig_upb, rate, term)}`` for fixed-rate loans, plus counts."""
    out, counts = {}, {"rows": 0, "frm": 0, "arm_or_other": 0, "unparsed": 0,
                       "field_count": None}
    with zipfile.ZipFile(archive(vintage)) as zf:
        for f in _lines(zf, f"sample_orig_{vintage}.txt"):
            counts["rows"] += 1
            if counts["field_count"] is None:
                counts["field_count"] = len(f)
            if f[O_AMORT] != "FRM":
                counts["arm_or_other"] += 1
                continue
            try:
                out[f[O_SEQ]] = (float(f[O_UPB]), float(f[O_RATE]), int(f[O_TERM]))
                counts["frm"] += 1
            except (ValueError, IndexError):
                counts["unparsed"] += 1
    return out, counts


def loans(vintage: int):
    """Yield ``(loan_seq, [record, ...])``, records in file order.

    The performance file groups a loan's months together and in period order;
    the grouping is on the key change, so a file that ever stopped doing that
    would surface as many one-row loans in ``--depth`` rather than silently.
    """
    with zipfile.ZipFile(archive(vintage)) as zf:
        seq, batch = None, []
        for f in _lines(zf, f"sample_perf_{vintage}.txt"):
            if f[P_SEQ] != seq:
                if seq is not None:
                    yield seq, batch
                seq, batch = f[P_SEQ], []
            batch.append(f)
        if seq is not None:
            yield seq, batch


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------

def quiet_segments(records, tally=None):
    """Split one loan's months into constant-rate quiet segments. §12.3.

    A month joins the running segment when every one of these holds against the
    month before it: the periods are calendar-consecutive, both sides read
    delinquency ``00``, neither carries a modification flag, neither carries a
    zero-balance code, the balance is positive, the rate is unchanged, and the
    age is at least ``MIN_AGE``. Anything else closes the segment.

    Returns a list of ``(rate_pct, [(age, rem, upb), ...])``.
    """
    def bump(key):
        if tally is not None:
            tally[key] = tally.get(key, 0) + 1

    parsed = []
    for f in records:
        try:
            rec = (int(f[P_PERIOD]), float(f[P_UPB]), f[P_DELINQ], int(f[P_AGE]),
                   int(f[P_REM]), f[P_MODFLAG], f[P_ZEROBAL], float(f[P_RATE]))
        except (ValueError, IndexError):
            bump("unparsed_rows")
            continue
        parsed.append(rec)

    segments, cur, prev = [], [], None
    for rec in parsed:
        period, upb, delinq, age, rem, mod, zbal, rate = rec
        ok = True
        if age < MIN_AGE:
            bump("dropped_age_lt_8"); ok = False
        elif delinq != "00":
            bump("dropped_delinquent"); ok = False
        elif mod != "":
            bump("dropped_modified"); ok = False
        elif zbal != "":
            bump("dropped_zero_balance_code"); ok = False
        elif upb <= 0.0:
            bump("dropped_upb_nonpositive"); ok = False
        if not ok:
            prev = None
            if len(cur) >= 2:
                segments.append((cur[0][7], [(c[3], c[4], c[1]) for c in cur]))
            cur = []
            continue
        if prev is not None and period == next_period(prev[0]) and rate == prev[7]:
            cur.append(rec)
        else:
            if len(cur) >= 2:
                segments.append((cur[0][7], [(c[3], c[4], c[1]) for c in cur]))
            cur = [rec]
        prev = rec
    if len(cur) >= 2:
        segments.append((cur[0][7], [(c[3], c[4], c[1]) for c in cur]))
    return segments


def segment_reading(rate_pct: float, months, orig_upb: float, term: int):
    """One segment's numbers, with §12.2's gate reported rather than applied.

    Two contract payments come back, and §12.9 is why both are needed.

    ``p_contract`` is §12.2's: re-derived from the segment's own opening balance
    and remaining term, so the $1,000 grid on the original balance never enters.
    It is the payment **only when the loan followed the clean schedule up to this
    segment**, because extra principal lowers ``U_k`` without re-amortising a
    fixed-rate note, and the formula would read the lower balance as a smaller
    contract. That is what ``gate_pass`` records.

    ``p_contract_coarse`` is the original contract payment from the rounded
    original balance. It is valid whether or not the borrower paid extra, at the
    cost of the grid: a relative error bounded by ``500 / U0``, about 0.25% on a
    $200k loan. **Coarser instrument, unselected population.**
    """
    i = rate_pct / 1200.0
    age0, rem0, upb0 = months[0]
    u0_hat = backout_u0(upb0, i, rem0, term)
    gate_pass = math.isfinite(u0_hat) and abs(u0_hat - orig_upb) <= U0_HALF_GRID
    p_fine = contract_payment(upb0, i, rem0)
    p_coarse = contract_payment(orig_upb, i, term)
    if not (math.isfinite(p_coarse) and p_coarse > 0.0):
        return None
    implied = [implied_payment(months[k - 1][2], months[k][2], rate_pct)
               for k in range(1, len(months))]
    if not implied:
        return None
    return {
        "n_diffs": len(implied),
        "age_start": age0,
        "gate_pass": gate_pass,
        "p_contract": p_fine if math.isfinite(p_fine) and p_fine > 0.0 else None,
        "p_contract_coarse": p_coarse,
        "p_min": min(implied),
        "p_median": statistics.median(implied),
        "p_spread": max(implied) - min(implied),
        "u0_hat": u0_hat,
    }


def length_bin(n: int) -> str:
    for lo, hi in LENGTH_BINS:
        if lo <= n <= hi:
            return f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+"
    return "1-7"


#: Every stratum the run reports, shortest first. ``1-7`` is here because a
#: segment of two months yields one difference and the file must not drop that
#: mass quietly: a bounded domain that is not printed reads as full coverage.
BIN_ORDER = ("1-7",) + tuple(f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+"
                             for lo, hi in LENGTH_BINS)


# ---------------------------------------------------------------------------
# --selftest. §12.7. Truth is known because the schedules are constructed.
# ---------------------------------------------------------------------------

def schedule(u0: float, rate_pct: float, term: int, months: int, extra=None):
    """A clean level-payment schedule, optionally with a payment rule on top.

    ``extra(k, contract_payment)`` returns what the borrower actually pays in
    month ``k``. Default is the contract payment.
    """
    i = rate_pct / 1200.0
    pay = u0 * i / annuity_factor(i, term)
    bal, rows = u0, []
    for k in range(1, months + 1):
        interest = bal * i
        actual = pay if extra is None else extra(k, pay)
        bal = bal + interest - actual
        rows.append((k, term - k, bal))
    return pay, rows


def cmd_selftest() -> int:
    print("C8-1d selftest. Three checks, all on constructed schedules where the\n"
          "answer is known before the code runs. §12.7.\n")
    fails = []

    # 1. the implied-payment formula recovers the contract payment exactly
    pay, rows = schedule(237_431.17, 6.5, 360, 60)
    prev = 237_431.17
    worst = 0.0
    for _, _, bal in rows:
        worst = max(worst, abs(implied_payment(prev, bal, 6.5) - pay))
        prev = bal
    print(f"  1. implied payment vs contract payment, 60 months")
    print(f"     contract {pay:.6f}   worst absolute error {worst:.3e}")
    if worst > 1e-6:
        fails.append("implied payment does not recover the contract payment")

    # 2. the back-out recovers U0 from any month, and P_contract needs no U0
    print(f"  2. U0 back-out from month k, and the U0-free contract payment")
    worst_u0 = worst_p = 0.0
    for k, rem, bal in rows:
        worst_u0 = max(worst_u0, abs(backout_u0(bal, 6.5 / 1200, rem, 360)
                                     - 237_431.17))
        worst_p = max(worst_p, abs(contract_payment(bal, 6.5 / 1200, rem) - pay))
    print(f"     worst |U0_hat - U0| {worst_u0:.3e}   "
          f"worst |P_contract - P| {worst_p:.3e}")
    if worst_u0 > 1e-6 or worst_p > 1e-9:
        fails.append("back-out or U0-free contract payment is wrong")

    # 3. the three cells of §12.4 are reachable and are told apart
    print("  3. §12.4's three cells, each on a borrower built to land in it")
    cases = [
        ("contract payer", None),
        ("rounds up to the nearest 50", lambda k, p: math.ceil(p / 50.0) * 50.0),
        ("contract plus 100", lambda k, p: p + 100.0),
    ]
    for name, rule in cases:
        p_true, rws = schedule(237_431.17, 6.5, 360, 60, rule)
        prev, imp = 237_431.17, []
        for _, _, bal in rws:
            imp.append(implied_payment(prev, bal, 6.5))
            prev = bal
        pmin = min(imp)
        ratio, diff = pmin / p_true, pmin - p_true
        on50 = abs(round(pmin / 50.0) * 50.0 - pmin) < 0.005
        print(f"     {name:<28} P_min {pmin:10.2f}  ratio {ratio:7.4f}  "
              f"diff {diff:+8.2f}  on a 50 {str(on50):>5}")
    print("\n     Read: cell one shows ratio 1.0000 and is not on a 50; cell two\n"
          "     is on a 50 and its ratio is not 1; cell three has a round positive\n"
          "     diff. Three distinguishable shapes, so §12.4's cells are reachable\n"
          "     and the arm is an arm (纪律 15).")

    # 4. --grid-k's whole path, on a carrier built so the grid's effect is known
    print("\n  4. --grid-k on constructed loans: reporting rounded to $1,000\n"
          "     below age 7 and to the cent from age 7, truth known before the run")
    u0s = [137_000.0 + 137.0 * j for j in range(400)]   # phase equidistributed mod 1000
    rate, term, months = 6.5, 360, 24
    i = rate / 1200.0
    acc = grid_k_new_acc()
    for j, u0 in enumerate(u0s):
        per, rows = 200_001, []
        for k in range(0, months + 1):
            bal = sched_balance(u0, i, term, k)
            shown = round(bal / 1000.0) * 1000.0 if k < 7 else round(bal, 2)
            f = [""] * PERF_FIELDS
            f[P_SEQ], f[P_PERIOD] = f"F{j:05d}", str(per)
            f[P_UPB], f[P_AGE], f[P_REM] = f"{shown:.2f}", str(k), str(term - k)
            rows.append(f)
            per = next_period(per)
        # orig U0 is itself on the $1,000 grid, exactly as the real field is
        grid_k_absorb(acc, rows, (round(u0 / 1000.0) * 1000.0, rate, term))
    payload = grid_k_payload(acc)
    by = {r["age"]: r for r in payload["by_age"]}

    worst_share, worst_gap, worst_exact, worst_stat = 0.0, 0.0, 0.0, 0.0
    for t in range(1, 7):
        worst_share = max(worst_share, abs(by[t]["ongrid_share"]["1000"] - 1.0))
        worst_gap = max(worst_gap,
                        abs(by[t]["rate_frm"] - by[t]["pred_from_mean"]))
        # this carrier is one rate and one term, so the p distribution is tight
        # and the two statistics must agree. On real data they do not, and that
        # disagreement is the whole reason the mean replaced the median.
        worst_stat = max(worst_stat, abs(by[t]["p_mean_clipped"]
                                         - by[t]["p_median"]))
    for t in range(9, months + 1):
        worst_exact = max(worst_exact, by[t]["ongrid_share"]["1000"],
                          by[t]["rate_frm"])
    preds = [by[t]["pred_from_mean"] for t in range(1, months + 1)]
    monotone = all(b <= a + 1e-12 for a, b in zip(preds, preds[1:]))

    print(f"     ages 1-6 on the $1,000 grid: worst |share - 1| {worst_share:.3e}")
    print(f"     ages 1-6 observed vs 1 - p/g: worst gap {worst_gap:.4f}")
    print(f"     ages 9+ (reported to the cent): worst on-grid or frozen "
          f"{worst_exact:.4f}")
    print(f"     pred falls with age (p rises by amortisation): {monotone}")
    print(f"     median vs clipped mean of p on a one-rate carrier: "
          f"worst {worst_stat:.4f}")
    if worst_share > 1e-9:
        fails.append("constructed grid rows do not read as on-grid")
    if worst_gap > 0.05:
        fails.append("P(frozen) = 1 - p/g does not hold on a constructed carrier")
    if worst_exact > 0.05:
        fails.append("cent-reported ages do not read off-grid and moving")
    if not monotone:
        fails.append("predicted freeze rate is not monotone in age")
    if worst_stat > 1.0:
        fails.append("median and clipped mean of p disagree on a tight carrier")

    # the printer and the serialiser are part of the path. A syntax check proves
    # the file parses; only a call proves a line runs, and the line that broke
    # last time was the serialiser (MEASUREMENT.md failure mode 16).
    print_grid_k(payload)
    blob = json.dumps({"stage": "B10", "step": "grid_k", **payload},
                      indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob):,} bytes")

    # 5. --zero-upb's whole path, one constructed loan per registered branch
    print("\n  5. --zero-upb on constructed loans, one per branch of §5·4")

    def _row(seq, per, upb, age, code=""):
        f = [""] * PERF_FIELDS
        f[P_SEQ], f[P_PERIOD] = seq, str(per)
        f[P_UPB], f[P_AGE], f[P_REM] = f"{upb:.2f}", str(age), str(360 - age)
        f[P_ZEROBAL] = code
        return f

    ORIG = 331_000.0
    cases = [
        # (name, rows, expected bucket or None when it must not be counted)
        ("terminated", [_row("A", 200_001, 0.0, 0, "01"),
                        _row("A", 200_002, 0.0, 1),
                        _row("A", 200_003, 0.0, 2)], "terminated"),
        ("reporting gap", [_row("B", 200_001, 0.0, 0),
                           _row("B", 200_002, 0.0, 1),
                           _row("B", 200_003, 330_000.0, 2)], "reporting_gap"),
        ("never a balance", [_row("C", 200_001, 0.0, 0),
                             _row("C", 200_002, 0.0, 1),
                             _row("C", 200_003, 0.0, 2)],
         "never_reports_a_balance"),
        ("matches orig", [_row("D", 200_001, ORIG, 0)], None),
        ("off by one grid step", [_row("E", 200_001, ORIG - 1000.0, 0)], None),
    ]
    acc5 = zero_upb_new_acc()
    for _, rows, _ in cases:
        zero_upb_absorb(acc5, rows, ORIG)

    want = {"age0": 5, "mismatch": 4, "zero": 3}
    got = {k: acc5[k] for k in want}
    print(f"     counts {got}   expected {want}")
    if got != want:
        fails.append(f"--zero-upb counters read {got}, expected {want}")
    for name, _, bucket in cases:
        if bucket is None:
            continue
        n = acc5["bucket"].get(bucket, 0)
        print(f"     {name:<22} -> {bucket:<26} n={n}")
        if n != 1:
            fails.append(f"--zero-upb put {name} in the wrong branch")
    # the three branches must partition the zero rows, with nothing left over
    if sum(acc5["bucket"].values()) != acc5["zero"]:
        fails.append("--zero-upb branches do not partition the zero rows")

    # printer and serialiser are part of the path (MEASUREMENT.md 16)
    acc5["per_vintage"] = {2007: acc5["zero"]}
    print_zero_upb(acc5)
    blob5 = json.dumps({"stage": "B10", "step": "zero_upb", **acc5},
                       indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob5):,} bytes")

    # 6. --phase's whole path. Truth is known because the file IS the simulation.
    print("\n  6. --phase on constructed loans whose reported series is built by\n"
          "     the same rule the simulation assumes, so obs - sim must be 0")
    rate6, term6, months6 = 6.5, 360, 26
    i6 = rate6 / 1200.0
    acc6 = phase_new_acc()
    for j in range(300):
        u0 = 137_000.0 + 137.0 * j
        per, rows = 200_001, []
        for k in range(0, months6 + 1):
            f = [""] * PERF_FIELDS
            f[P_SEQ], f[P_PERIOD] = f"P{j:05d}", str(per)
            f[P_UPB] = f"{reported(u0, rate6, term6, k, 0.0):.2f}"
            f[P_AGE], f[P_REM] = str(k), str(term6 - k)
            rows.append(f)
            per = next_period(per)
        phase_absorb(acc6, rows, (round(u0 / 1000.0) * 1000.0, rate6, term6))
    pl6 = phase_payload(acc6)

    # the file was generated at theta = 0, so that column must be exactly 0
    # and the others must not be, or the sweep is inert
    worst_gap6 = 0.0
    best_other = 1.0
    for r in pl6["by_age"]["all"]:
        worst_gap6 = max(worst_gap6, abs(r["gap@0.0"]))
        if r["age"] <= 6:
            best_other = min(best_other,
                             min(abs(r[f"gap@{t}"]) for t in OFFSETS if t != 0.0))
    tgt0 = pl6["age0_mismatch"]["all"]["0.0"]
    tgt1 = pl6["age0_mismatch"]["all"]["1.0"]
    # the backed-out U0 must recover the exact one, so the phase must not be
    # the phase of the ROUNDED orig balance (which would pile up on bin 0)
    top = pl6["phase_top"]["all"][0]
    print(f"     loans {pl6['loans']}   backed out {pl6['backed_out']}"
          f"   gated {pl6['gated']}")
    print(f"     worst |obs - sim| at theta=0 (the generating rule): {worst_gap6:.3e}")
    print(f"     smallest |gap| at any other theta, ages 1-6: {best_other:.4f}"
          f"   (must not be ~0, or the sweep does nothing)")
    print(f"     age-0 target at theta=0: {tgt0 * 100:.4f}%   at theta=1:"
          f" {tgt1 * 100:.4f}%")
    print(f"     busiest $1 phase bin: {top['bin']} at {top['share'] * 100:.3f}%"
          f"   (a spike at 0 here would mean U0_hat came from the rounded orig)")
    if pl6["backed_out"] != 300:
        fails.append("--phase did not back out every constructed loan")
    if worst_gap6 > 1e-12:
        fails.append("--phase simulation disagrees with a file it generated")
    # NOT asserted: that another theta fits worse on the freeze profile. This
    # carrier's monthly principal is about 150, so a quarter month moves the
    # balance 37 dollars and almost never crosses a 1000 boundary. The freeze
    # profile therefore carries almost no information about theta, and that is
    # exactly why §5·5·6 anchors the criterion on the age-0 target instead.
    # The printed number stays, as the record of that weakness.
    if tgt0 > 0.01:
        fails.append("--phase theta=0 must reproduce the rounded orig, it did not")
    if tgt1 < 0.05:
        fails.append("--phase theta=1 must move the age-0 report, it did not")
    if top["share"] > 0.05:
        fails.append("--phase read the rounded orig balance as the phase")

    print_phase(pl6)
    blob6 = json.dumps({"stage": "B10", "step": "phase", **pl6},
                       indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob6):,} bytes")

    # 7. --amort's whole path, one constructed loan per branch
    print("\n  7. --amort on constructed loans: a fixed-rate one, a repricing\n"
          "     one with no mod flag, and one whose rate moves at a modification")

    def _rr(seq, per, rate, mod=""):
        f = [""] * PERF_FIELDS
        f[P_SEQ], f[P_PERIOD] = seq, str(per)
        f[P_RATE], f[P_MODFLAG] = f"{rate:.3f}", mod
        return f

    acc7 = amort_new_acc()
    amort_absorb(acc7, [_rr("F", 200_001, 6.5), _rr("F", 200_002, 6.5),
                        _rr("F", 200_003, 6.5)])                      # 2 pairs, 0 moves
    amort_absorb(acc7, [_rr("A", 200_001, 6.5), _rr("A", 200_002, 7.0),
                        _rr("A", 200_003, 7.0)])                      # 1 move, no flag
    amort_absorb(acc7, [_rr("M", 200_001, 6.5), _rr("M", 200_002, 4.0, "Y"),
                        _rr("M", 200_003, 4.0, "P")])                 # 1 move, flagged
    # a broken period chain must not be counted as a pair
    amort_absorb(acc7, [_rr("G", 200_001, 6.5), _rr("G", 200_006, 9.9)])
    amort_absorb_orig(acc7, [""] * 14 + ["X", "FRM", "Y"] + [""] * 14)

    want7 = {"pairs": 6, "rate_moves": 2,
             "moved_with_mod": 1, "moved_without_mod": 1}
    got7 = {k: acc7[k] for k in want7}
    print(f"     counts {got7}   expected {want7}")
    if got7 != want7:
        fails.append(f"--amort counters read {got7}, expected {want7}")
    if acc7["rate_moves"] != acc7["moved_with_mod"] + acc7["moved_without_mod"]:
        fails.append("--amort rate-move split does not add back to the total")
    if len(acc7["vals"][15]) != 1:
        fails.append("--amort did not read orig column 15")

    print_amort(acc7)
    blob7 = json.dumps({"stage": "B10", "step": "amort",
                        "cols": {str(c): acc7["vals"][c] for c in AMORT_COLS},
                        **{k: v for k, v in acc7.items() if k != "vals"}},
                       indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob7):,} bytes")

    # 8. --defer, §8·14. Constructed loans whose signatures are known first.
    print("\n  8. --defer: two constructed columns, two known signatures")

    def prow(period, upb, mod="", paydef="", **cols):
        """One perf row. `cols` keys are 1-indexed to match the field enumeration."""
        f = [""] * PERF_FIELDS
        f[P_SEQ] = "F0001"
        f[P_PERIOD] = str(period)
        f[P_UPB] = f"{upb:.2f}"
        f[P_DELINQ] = "00"
        f[P_MODFLAG] = mod
        f[P_PAY_DEFER] = paydef
        for k, v in cols.items():
            f[int(k[1:]) - 1] = v
        return f

    #: Loan A: column 12 turns positive on the very month the mod flag is set.
    #: That is §7·12's signature 1. Four consecutive months, one edge.
    loanA = [prow(200001, 100_000.0, c12="0.00"),
             prow(200002, 99_000.0, c12="0.00"),
             prow(200003, 98_000.0, mod="Y", c12="5000.00"),
             prow(200004, 97_000.0, c12="5000.00")]
    #: Loan B: column 21 turns positive in 202006 with no mod flag, and the
    #: payment-deferral flag is set on the same row. Signature 2 plus §8·14·3.
    loanB = [prow(202004, 80_000.0, c21=""),
             prow(202005, 79_500.0, c21="0.00"),
             prow(202006, 79_000.0, paydef="C", c21="3000.00")]
    #: Loan C: same calendar month as B, a different vintage, same shape. Two
    #: vintages sharing one period is what makes signature 2 readable.
    loanC = [prow(202005, 60_000.0, c21="0.00"),
             prow(202006, 59_500.0, paydef="C", c21="1500.00")]
    #: Loan D: column 12 jumps to positive across a PERIOD GAP. Not an edge.
    loanD = [prow(201001, 50_000.0, c12="0.00"),
             prow(201005, 49_000.0, c12="7000.00")]

    acc8 = defer_new_acc()
    defer_absorb(acc8, loanA, 2000)
    defer_absorb(acc8, loanB, 2020)
    defer_absorb(acc8, loanC, 2019)
    defer_absorb(acc8, loanD, 2010)
    pl8 = defer_payload(acc8)

    def chk8(name, got, want):
        ok = got == want
        print(f"     {name:<52}{str(got):>14}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--defer {name}: {got} != {want}")

    e12 = pl8["edges"].get("11")
    e21 = pl8["edges"].get("20")
    chk8("col 12 has exactly one rising edge", e12["n"] if e12 else None, 1)
    chk8("  and it sits on a modification month",
         round(e12["share_with_mod_flag"], 6) if e12 else None, 1.0)
    chk8("  the period gap in loan D produced no edge",
         acc8["gap_pairs"] >= 1, True)
    chk8("col 21 has two rising edges", e21["n"] if e21 else None, 2)
    chk8("  and neither sits on a modification month",
         round(e21["share_with_mod_flag"], 6) if e21 else None, 0.0)
    chk8("  both carry the payment-deferral flag (§8·14·3)",
         round(e21["share_with_pay_deferral_flag"], 6) if e21 else None, 1.0)
    chk8("  both land in one calendar period",
         round(e21["share_in_top_period"], 6) if e21 else None, 1.0)
    chk8("  across two vintages",
         e21["vintages_with_an_edge"] if e21 else None, 2)
    #: Blank and 0.00 are different facts and the shape table has to keep them
    #: apart, or "mostly zero" and "mostly blank" read the same.
    c21 = pl8["cols"]["20"]
    #: `rows` is every row the scan saw, not just the ones this column is set
    #: on, so 11 not 9. That is the point: 11 rows, 4 non-blank, 2 of those
    #: zero, 2 positive, and therefore 7 blank. **Blank and 0.00 are different
    #: facts**, and a shape table that folded them together would read
    #: "mostly zero" and "mostly blank" the same way.
    chk8("col 21: rows / nonblank / zero / positive",
         (c21["rows"], c21["nonblank"], c21["zero"], c21["positive"]),
         (11, 4, 2, 2))
    chk8("  so 7 rows are blank, and blank is not zero",
         c21["rows"] - c21["nonblank"], 7)
    #: A column nothing ever writes must still appear, with zeros.
    chk8("an all-blank column still appears in the table",
         pl8["cols"]["30"]["nonblank"], 0)
    chk8("every perf column is present", len(pl8["cols"]), PERF_FIELDS)
    chk8("median deferred amount on col 21", e21["median_amount"] if e21 else None,
         3000.0)

    print_defer(pl8)
    blob8 = json.dumps({"stage": "B10", "step": "defer", **pl8},
                       indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob8):,} bytes")

    #: The empty case has its own printed landing, and a printer that never
    #: runs on it is not tested (失效模式 16).
    pl_empty = defer_payload(defer_new_acc())
    import io as _io
    import sys as _sys
    _buf, _keep = _io.StringIO(), _sys.stdout
    _sys.stdout = _buf
    try:
        print_defer(pl_empty)
    finally:
        _sys.stdout = _keep
    chk8("no-edge case prints its own landing and stops",
         "§8·14·2 has nothing to read" in _buf.getvalue(), True)

    # 9. --defer2, §8·14·5. The reading with the "or" taken out.
    print("\n  9. --defer2: the corrected reading, on constructed payloads")

    def colrec(rows, nonblank, numeric, positive, zero, distinct, one_ix):
        return {"col_1indexed": one_ix, "rows": rows, "nonblank": nonblank,
                "numeric": numeric, "positive": positive, "zero": zero,
                "distinct": distinct,
                "distinct_capped_at": None if distinct is not None else 5000}

    #: Four columns whose verdicts are known before the code runs, built to be
    #: exactly the four shapes --defer's reading could not tell apart.
    R = 1_000_000
    pl9 = {"cols": {
        #: a balance: reported every row, zero on almost all of them, never negative
        "11": colrec(R, R, R, 9_000, 991_000, None, 12),
        #: a disposition amount: BLANK on almost every row. --defer's "or blank"
        #: let this through; §8·14·5's first 条件 does not.
        "14": colrec(R, 200, 200, 190, 10, None, 15),
        #: a counter: same zero/positive shape as the balance, few distinct
        "3": colrec(R, R, R, 30_000, 970_000, 102, 4),
        #: a balance-shaped column that goes negative
        "30": colrec(R, R, R, 9_000, 981_000, None, 31),
    }, "edges": {
        "11": {"n": 500, "median_amount": 9_769.33},
        "14": {"n": 190, "median_amount": 4_000.0},
        "3": {"n": 40_000, "median_amount": 1.0},
        "30": {"n": 600, "median_amount": 78.26},
    }}
    #: col 31 goes negative: numeric - positive - zero = 10,000
    pl9["cols"]["30"]["zero"] = 981_000
    sel9 = defer2_select(pl9)

    def chk9(name, got, want):
        ok = got == want
        print(f"     {name:<54}{str(got):>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--defer2 {name}: {got} != {want}")

    chk9("the balance passes", sel9["11"]["passes"], True)
    chk9("the blank-mostly disposition column fails, and on 条件 one",
         (sel9["14"]["passes"], sel9["14"]["first_failed"]),
         (False, "never_blank"))
    chk9("the counter fails, and on the distinct cap",
         (sel9["3"]["passes"], sel9["3"]["first_failed"]),
         (False, "distinct_past_the_cap"))
    chk9("the negative-going column fails, and on 条件 two",
         (sel9["30"]["passes"], sel9["30"]["first_failed"]),
         (False, "never_negative"))
    chk9("exactly one column passes",
         [sel9[k]["col_1indexed"] for k in sel9 if sel9[k]["passes"]], [12])

    #: The signature reader, on the three registered outcomes.
    def sigrec(edges, mod, flag, years, yv, vints):
        return {"edges": edges, "with_mod": mod, "with_flag": flag,
                "years": years, "year_vintages": yv, "vintages": vints}

    n1, _ = defer2_signature(sigrec(
        1000, 996, 4, {2010: 500, 2011: 500}, {2010: {1, 2}, 2011: {1, 2}},
        {1, 2}))
    chk9("mod share 0.996 reads signature 1", n1.startswith("signature 1"), True)
    n2, f2 = defer2_signature(sigrec(
        1000, 130, 760, {2019: 100, 2020: 800, 2021: 100},
        {2019: {1}, 2020: {1, 2, 3}, 2021: {2}}, {1, 2, 3}))
    chk9("flag 0.76 + one dominant year + most vintages reads signature 2",
         n2.startswith("signature 2"), True)
    chk9("  and the top year is named", f2["top_year"], 2020)
    #: The flag half alone is not enough: if the pile-up tracks vintage rather
    #: than the calendar, only one vintage reaches the top year.
    n3, _ = defer2_signature(sigrec(
        1000, 130, 760, {2019: 100, 2020: 800, 2021: 100},
        {2019: {1}, 2020: {1}, 2021: {2}}, {1, 2, 3}))
    chk9("flag high but the top year spans one vintage -> neither",
         n3, "neither signature")
    n4, _ = defer2_signature(sigrec(
        1000, 130, 200, {2010: 400, 2011: 300, 2012: 300},
        {2010: {1, 2}, 2011: {1, 2}, 2012: {1, 2}}, {1, 2}))
    chk9("both shares low -> neither", n4, "neither signature")

    #: Drive the printer over all four landings plus the unregistered zero case.
    import io as _io2
    import sys as _sys2

    def drive9(passing, detail, want, tag):
        payload = {"reading": sel9, "passing": passing, "detail": detail,
                   "rows": 10, "loans": 2}
        buf, keep = _io2.StringIO(), _sys2.stdout
        _sys2.stdout = buf
        try:
            print_defer2(payload)
        except Exception as exc:                       # noqa: BLE001
            _sys2.stdout = keep
            chk9(f"print_defer2 survives {tag}", type(exc).__name__, "no error")
            return
        finally:
            _sys2.stdout = keep
        txt = buf.getvalue()
        chk9(f"print_defer2 reads {tag}", want in txt, True)
        try:
            json.dumps(payload, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--defer2 json.dumps {tag}: {exc}")

    def det(one_ix, sig):
        return {str(one_ix - 1): {
            "col_1indexed": one_ix, "edges": 1000, "with_mod": 100,
            "with_flag": 760, "years": {2020: 800, 2019: 200},
            "year_vintages": {2020: [1, 2, 3], 2019: [1]},
            "vintages": [1, 2, 3], "signature": sig,
            "signature_facts": {"share_with_mod_flag": 0.1,
                                "share_with_pay_deferral_flag": 0.76,
                                "top_year": 2020, "top_year_edges": 800,
                                "top_year_is_a_plurality": True,
                                "vintages_in_top_year": 3,
                                "vintages_with_an_edge": 3,
                                "top_year_spans_most_vintages": True}}}

    drive9([12], det(12, "signature 2 (payment deferral)"),
           "FIRST BRANCH", "one column, signature 2")
    drive9([12], det(12, "signature 1 (deferred principal from a modification)"),
           "SECOND BRANCH", "one column, signature 1")
    drive9([12], det(12, "neither signature"), "THIRD BRANCH",
           "one column, neither")
    d4 = det(12, "signature 2 (payment deferral)")
    d4.update(det(31, "neither signature"))
    drive9([12, 31], d4, "FOURTH BRANCH", "two columns")
    drive9([], {}, "未命中", "no column at all")

    #: The rising-edge definition has to be the same one --defer used, or the
    #: two runs are not the same population (失效模式 18's second condition).
    acc9 = defer2_new_acc([11])
    defer2_absorb(acc9, loanA, 2000)
    defer2_absorb(acc9, loanD, 2010)
    chk9("defer2_absorb finds loan A's edge and not loan D's gap",
         acc9["edges"][11], 1)
    chk9("  and files it under the right calendar year",
         dict(acc9["years"][11]), {2000: 1})
    chk9("  and records the vintage that contributed",
         sorted(acc9["year_vintages"][11][2000]), [2000])
    acc9b = defer2_new_acc([20])
    defer2_absorb(acc9b, loanB, 2020)
    defer2_absorb(acc9b, loanC, 2019)
    chk9("  two vintages both reach 2020",
         (acc9b["edges"][20], sorted(acc9b["year_vintages"][20][2020])),
         (2, [2019, 2020]))
    chk9("  and the col 25 flag is counted", acc9b["with_flag"][20], 2)

    # 10. --balloon, §8·14·6. Constructed loans whose horizon is known first.
    print("\n  10. --balloon: the maturity anchor and the two-way horizon")

    def chk10(name, got, want):
        ok = got == want
        print(f"     {name:<54}{str(got):>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--balloon {name}: {got} != {want}")

    chk10("monthdiff crosses a year end", monthdiff(200101, 200012), 1)
    chk10("  and a whole term", monthdiff(203001, 200001), 360)
    chk10("  and is signed", monthdiff(200001, 200101), -12)
    chk10("_yyyymm rejects month 13", _yyyymm("200013"), None)
    chk10("_yyyymm rejects a non-digit", _yyyymm("20.01"), None)
    chk10("_yyyymm accepts a real one", _yyyymm(" 200001 "), 200001)

    def orow(term="360", **cols):
        f = [""] * ORIG_FIELDS
        f[O_SEQ] = "F0001"
        f[O_UPB] = "200000"
        f[O_RATE] = "6.5"
        f[O_AMORT] = "FRM"
        f[O_TERM] = term
        for k, v in cols.items():
            f[int(k[1:]) - 1] = v
        return f

    def brow(period, rem, defer="0.00"):
        f = [""] * PERF_FIELDS
        f[P_SEQ] = "F0001"
        f[P_PERIOD] = str(period)
        f[P_UPB] = "199000.00"
        f[P_REM] = str(rem)
        f[P_DEFER_BAL] = defer
        return f

    #: col 4 is a real maturity date, col 6 a first-payment date. Both are
    #: YYYYMM, so the appearance filter cannot tell them apart. **The two loans
    #: carry DIFFERENT terms on purpose**: that is the whole reason the anchor
    #: subtracts `term`. A maturity column gives the same offset whatever the
    #: term; anything measured from origination instead moves with it. With one
    #: term in the fixture both columns would anchor and the test would prove
    #: nothing — which is how this fixture was first written.
    acc10 = balloon_new_acc()
    o = orow(term="360", c4="203001", c6="200003")
    recs = [brow(200002, 359),
            brow(200003, 358),
            brow(200004, 357, defer="5000.00"),
            brow(200005, 356, defer="5000.00")]
    balloon_absorb(acc10, recs, o)
    o2 = orow(term="180", c4="201502", c6="200004")
    recs2 = [brow(200003, 179), brow(200004, 178, defer="1000.00")]
    balloon_absorb(acc10, recs2, o2)
    o3 = orow(term="240", c4="202004", c6="200006")
    recs3 = [brow(200005, 239), brow(200006, 238, defer="2000.00")]
    balloon_absorb(acc10, recs3, o3)

    chk10("both YYYYMM columns are enumerated",
          sorted(c + 1 for c in range(ORIG_FIELDS)
                 if acc10["yyyymm_rows"][c]), [4, 6])
    chk10("the maturity column anchors on one offset, whatever the term",
          dict(acc10["anchor"][3]), {-1: 3})
    chk10("  and the first-payment column spreads with the term",
          dict(acc10["anchor"][5]), {-359: 1, -179: 1, -239: 1})
    chk10("only the deferral rows are compared",
          acc10["defer_rows"], 4)
    chk10("  and the two paths agree there, at one offset",
          dict(acc10["cmp"][3]), {0: 4})

    pl10 = balloon_payload(acc10)
    chk10("payload names the maturity column's offset",
          pl10["cols"]["3"]["anchor_top"]["offset"], -1)
    chk10("  with share 1.0", pl10["cols"]["3"]["anchor_top"]["share"], 1.0)
    t5 = pl10["cols"]["5"]["anchor_top"]
    chk10("  and the first-payment column does not press",
          (t5 is not None) and (t5["share"] > 0.5), False)
    chk10("  its busiest offset holds only a third",
          round(t5["share"], 6), round(1 / 3, 6))

    import io as _io3
    import sys as _sys3

    def drive10(payload, want, tag):
        buf, keep = _io3.StringIO(), _sys3.stdout
        _sys3.stdout = buf
        try:
            print_balloon(payload)
        except Exception as exc:                       # noqa: BLE001
            _sys3.stdout = keep
            chk10(f"print_balloon survives {tag}", type(exc).__name__, "no error")
            return
        finally:
            _sys3.stdout = keep
        chk10(f"print_balloon reads {tag}", want in buf.getvalue(), True)
        try:
            json.dumps(payload, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--balloon json.dumps {tag}: {exc}")

    drive10(pl10, "§8·14·6·2 FIRST BRANCH", "agreement on every deferral row")

    #: One row where the two paths differ. §14.1 says "exactly", so this is the
    #: second branch and not a tolerance.
    acc11 = balloon_new_acc()
    balloon_absorb(acc11, recs, o)
    bad = [brow(200003, 179), brow(200004, 177, defer="1000.00")]
    balloon_absorb(acc11, bad, orow(term="180", c4="201502", c6="200004"))
    pl11 = balloon_payload(acc11)
    drive10(pl11, "§8·14·6·2 SECOND BRANCH", "one disagreeing row")

    #: No column presses: §8·14·6·1's second branch, and then §8·14·6·2 has no
    #: referent at all. A landing that is never printed is not tested.
    acc12 = balloon_new_acc()
    for j in (-359, -239, -179, -119):
        acc12["anchor"][5][j] = 1
        acc12["anchor_n"][5] += 1
        acc12["yyyymm_rows"][5] += 1
    drive10(balloon_payload(acc12), "SECOND BRANCH: no maturity path",
            "no column presses")

    #: Two columns press: §8·14·6·1's third branch, stop before §8·14·6·2.
    acc13 = balloon_new_acc()
    for c in (3, 5):
        acc13["anchor"][c][-1] = 100
        acc13["anchor_n"][c] = 100
        acc13["yyyymm_rows"][c] = 100
    drive10(balloon_payload(acc13), "THIRD BRANCH: more than one column",
            "two columns press")

    #: A loan whose orig row is missing, and one whose term will not parse.
    acc14 = balloon_new_acc()
    balloon_absorb(acc14, recs, None)
    bad_term = orow(term="360", c4="203001")
    bad_term[O_TERM] = "n/a"
    balloon_absorb(acc14, recs, bad_term)
    chk10("a loan with no orig row is counted, not skipped silently",
          acc14["loans_no_orig"], 1)
    chk10("a loan with an unreadable term likewise",
          acc14["loans_no_term"], 1)
    chk10("  and neither contributed an anchor", acc14["anchor_n"][3], 0)

    # 11. --balloon2, §8·14·6·5. The same fixture that fooled --balloon.
    print("\n  11. --balloon2: the anchor stratified by term")

    def chk11(name, got, want):
        ok = got == want
        print(f"     {name:<54}{str(got):>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--balloon2 {name}: {got} != {want}")

    #: The point of the fixture: **the term mix is lopsided**, which is exactly
    #: what defeated `--balloon` on the real book (72% thirty-year). Six loans,
    #: four of them 360-month, so the first-payment column's pooled top bucket
    #: holds 4/6 and would press. Stratified, it cannot.
    acc15 = balloon2_new_acc()
    fixture = [
        ("360", "203001", "200003", [brow(200002, 359)]),
        ("360", "203002", "200004", [brow(200003, 359)]),
        ("360", "203003", "200005", [brow(200004, 359)]),
        ("360", "203004", "200006", [brow(200005, 359)]),
        ("180", "201502", "200004", [brow(200003, 179)]),
        ("240", "202004", "200006", [brow(200005, 239)]),
    ]
    for term, mat, fp, recs_ in fixture:
        balloon2_absorb(acc15, recs_, orow(term=term, c4=mat, c6=fp))
    pl15 = balloon2_payload(acc15)

    chk11("the term strata are the data's own",
          pl15["loans_by_term"], {"180": 1, "240": 1, "360": 4})
    m = pl15["cols"]["3"]
    fp_ = pl15["cols"]["5"]
    chk11("the maturity column is invariant across strata",
          (m["invariant"], m["distinct_top_offsets"], m["top_offsets"]),
          (True, 1, [-1]))
    chk11("the first-payment column is not",
          (fp_["invariant"], fp_["distinct_top_offsets"]), (False, 3))
    chk11("  and its offsets are one per term",
          fp_["top_offsets"], [-359, -239, -179])
    chk11("the thinnest stratum is named", m["thinnest_stratum"][1], 1)

    #: The pooled test --balloon uses would have passed the first-payment
    #: column on this same fixture. That is the regression this mode exists for.
    pooled = {}
    for t, v in fp_["strata"].items():
        pooled[v["top_offset"]] = pooled.get(v["top_offset"], 0) + v["loans"]
    top_pooled = max(pooled.values()) / sum(pooled.values())
    chk11("pooled, the first-payment column WOULD have pressed",
          top_pooled > 0.5, True)

    def drive11(payload, want, tag):
        buf, keep = _io3.StringIO(), _sys3.stdout
        _sys3.stdout = buf
        try:
            print_balloon2(payload)
        except Exception as exc:                       # noqa: BLE001
            _sys3.stdout = keep
            chk11(f"print_balloon2 survives {tag}", type(exc).__name__, "no error")
            return
        finally:
            _sys3.stdout = keep
        chk11(f"print_balloon2 reads {tag}", want in buf.getvalue(), True)
        try:
            json.dumps(payload, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--balloon2 json.dumps {tag}: {exc}")

    drive11(pl15, "FIRST BRANCH", "exactly one invariant column")

    #: No column invariant.
    acc16 = balloon2_new_acc()
    for term, fp in (("360", "200003"), ("180", "200004")):
        balloon2_absorb(acc16, [brow(200002, 1)], orow(term=term, c6=fp))
    drive11(balloon2_payload(acc16), "SECOND BRANCH", "no invariant column")

    #: Two columns invariant: stop before §8·14·6·2.
    acc17 = balloon2_new_acc()
    for term, mat in (("360", "203001"), ("180", "201501")):
        f = orow(term=term, c4=mat)
        f[5] = mat                     # a second column carrying the same date
        balloon2_absorb(acc17, [brow(200001, 1)], f)
    pl17 = balloon2_payload(acc17)
    chk11("two columns can both be invariant",
          sorted(d["col_1indexed"] for d in pl17["cols"].values()
                 if d["invariant"]), [4, 6])
    drive11(pl17, "THIRD BRANCH", "two invariant columns")

    #: Coverage counters must not swallow anything.
    acc18 = balloon2_new_acc()
    balloon2_absorb(acc18, [brow(200001, 1)], None)
    bt = orow(term="n/a", c4="203001")
    balloon2_absorb(acc18, [brow(200001, 1)], bt)
    balloon2_absorb(acc18, [], orow(term="360", c4="203001"))
    chk11("no orig row, unreadable term and no period are each counted",
          (acc18["loans_no_orig"], acc18["loans_no_term"],
           acc18["loans_no_period"]), (1, 1, 1))
    chk11("  and none of them reached a stratum",
          sum(acc18["loans_by_term"].values()), 0)

    # 12. --balloon3, §8·14·6·6. Both invariants, on constructed strata.
    print("\n  12. --balloon3: the two invariants side by side")

    def chk12(name, got, want):
        ok = got == want
        print(f"     {name:<54}{str(got):>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--balloon3 {name}: {got} != {want}")

    def strat(pairs):
        """{term: (top_offset, loans)} -> the strata shape balloon2 emits."""
        return {str(t): {"loans": n, "top_offset": o, "top_n": n,
                         "top_share": 1.0, "distinct_offsets": 1}
                for t, (o, n) in pairs.items()}

    #: A maturity column: offset 0 whatever the term. A first-payment column:
    #: offset `1 - term`. **Lopsided term mix on purpose**, as on the real book.
    mat_s = strat({360: (0, 1000), 180: (0, 200), 240: (0, 50), 72: (-1, 3)})
    fp_s = strat({360: (-359, 1000), 180: (-179, 200), 240: (-239, 50),
                  72: (-72, 3)})

    lm = balloon3_loads(mat_s)
    lf = balloon3_loads(fp_s)
    chk12("maturity column: A wins", lm["verdict"], "A")
    chk12("  A's mode is the offset, not the term",
          lm["A_offset_constant"]["mode"], 0)
    chk12("  and it carries every stratum but the odd one",
          (lm["A_offset_constant"]["loans"], lm["A_offset_constant"]["strata"]),
          (1250, 3))
    chk12("first-payment column: B wins", lf["verdict"], "B")
    chk12("  B's mode is the constant it is measured by",
          lf["B_offset_plus_term_constant"]["mode"], 1)
    chk12("  A alone would have caught only the biggest stratum",
          lf["A_offset_constant"]["loans"], 1000)
    #: The regression this mode exists for: the one-sided test calls the
    #: first-payment column "not a maturity path" instead of "a different
    #: thing", and on a lopsided book it can even out-press.
    chk12("one-sided, both columns fail 'all strata equal'",
          (lm["A_offset_constant"]["strata"] == lm["n_strata"],
           lf["A_offset_constant"]["strata"] == lf["n_strata"]),
          (False, False))

    tie_s = strat({360: (0, 100), 180: (0, 100)})
    #: Two strata, offsets 0 and 0 -> A mode covers 200; B modes 360 and 180
    #: cover 100 each, so A wins. Build a real tie instead.
    tie_s = strat({360: (0, 100), 180: (-180, 100)})
    lt = balloon3_loads(tie_s)
    chk12("an exact tie is called a tie, not pushed to a side",
          lt["verdict"], "tie")

    def mkpl(cols2, cols1):
        return ({"cols": cols2, "loans_by_term": {}},
                {"cols": cols1, "defer_rows": 679416,
                 "defer_rows_rem_ok": 679416, "defer_rows_no_rem": 0})

    def cmp1(n, off, top_n, out=0):
        return {"cmp_top": {"offset": off, "n": top_n, "share": top_n / n},
                "cmp_n": n, "cmp_out": out,
                "cmp_hist": {str(off): top_n, "-163": 7, "-169": 5}}

    def drive12(cols2, cols1, want, tag, notwant=None):
        p2, p1 = mkpl(cols2, cols1)
        payload = balloon3_payload(p2, p1)
        buf, keep = _io3.StringIO(), _sys3.stdout
        _sys3.stdout = buf
        try:
            print_balloon3(payload)
        except Exception as exc:                       # noqa: BLE001
            _sys3.stdout = keep
            chk12(f"print_balloon3 survives {tag}", type(exc).__name__, "ok")
            return
        finally:
            _sys3.stdout = keep
        txt = buf.getvalue()
        ok = want in txt and not (notwant and notwant in txt)
        chk12(f"print_balloon3 reads {tag}", ok, True)
        try:
            json.dumps(payload, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--balloon3 json.dumps {tag}: {exc}")

    two_cols = {"1": {"col_1indexed": 2, "strata": fp_s},
                "3": {"col_1indexed": 4, "strata": mat_s}}
    drive12(two_cols, {"3": cmp1(679416, 0, 679416), "1": cmp1(679416, -359, 100)},
            "FIRST BRANCH", "one A-winner, deferral rows all agree")
    drive12(two_cols, {"3": cmp1(679416, 0, 455899), "1": cmp1(679416, -359, 100)},
            "SECOND BRANCH. 223,517 of 679,416", "one A-winner, some disagree")
    drive12(two_cols, {}, "no referent", "A-winner never meets a deferral row")
    drive12({"1": {"col_1indexed": 2, "strata": fp_s}}, {},
            "SECOND BRANCH. No column is measured from maturity",
            "no A-winner")
    drive12({"1": {"col_1indexed": 2, "strata": mat_s},
             "3": {"col_1indexed": 4, "strata": mat_s}}, {},
            "NOT complementary", "both columns land on A")
    drive12({"1": {"col_1indexed": 2, "strata": mat_s},
             "3": {"col_1indexed": 4, "strata": mat_s}}, {},
            "THIRD BRANCH", "two A-winners")

    # 13. --extend, §8·14·6·7. Constructed loans, answers known first.
    print("\n  13. --extend: a risen rem_legal, and the perf-side YYYYMM sweep")

    def chk13(name, got, want):
        ok = got == want
        print(f"     {name:<54}{str(got):>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--extend {name}: {got} != {want}")

    def erow(period, rem, defer="0.00", mod="", **cols):
        f = [""] * PERF_FIELDS
        f[P_SEQ] = "F0001"
        f[P_PERIOD] = str(period)
        f[P_UPB] = "199000.00"
        f[P_REM] = str(rem)
        f[P_DEFER_BAL] = defer
        f[P_MODFLAG] = mod
        for k, v in cols.items():
            f[int(k[1:]) - 1] = v
        return f

    def omat(mat):
        f = orow(term="360")
        f[O_MATURITY] = mat
        return f

    #: Loan A: term never re-set. mat 203001, so at 200004 the horizon is
    #: 360-3 = 357, and rem reads 357: the two paths agree on its deferral row.
    acc19 = extend_new_acc()
    loanA13 = [erow(200002, 359), erow(200003, 358),
               erow(200004, 357, defer="5000.00")]
    extend_absorb(acc19, loanA13, omat("203001"))
    #: Loan B: rem_legal RISES at 200004, by 120 months, on a row carrying the
    #: modification flag. Its deferral row then disagrees, because the orig
    #: maturity cannot follow.
    #: 358 -> 478 is a rise of exactly 120, so the fixture's intent is legible
    #: in the expected value rather than needing arithmetic to check.
    loanB13 = [erow(200002, 359), erow(200003, 358),
               erow(200004, 478, mod="Y"),
               erow(200005, 477, defer="3000.00")]
    extend_absorb(acc19, loanB13, omat("203001"))
    pl19 = extend_payload(acc19)

    chk13("the loan whose term was re-set is counted once",
          pl19["loans_with_a_rise"], 1)
    chk13("  the rise is one month, sized and dated",
          (pl19["rise_rows"], pl19["rise_size"], pl19["rise_year"]),
          (1, {"120": 1}, {"2000": 1}))
    chk13("  and the mod flag on that row is counted",
          pl19["rise_with_mod"], 1)
    chk13("the deferral rows split by the two paths",
          (pl19["defer_eq"], pl19["defer_ne"]), (1, 1))
    chk13("  agreeing row: its loan never rose",
          pl19["defer_eq_risen"], 0)
    chk13("  disagreeing row: its loan did",
          pl19["defer_ne_risen"], 1)
    chk13("  so the disagreeing share is the higher one",
          pl19["share_ne_risen"] > pl19["share_eq_risen"], True)

    #: A fall of exactly one is ordinary amortisation and must not be a rise;
    #: a gap in the period sequence must not manufacture one either.
    acc20 = extend_new_acc()
    extend_absorb(acc20, [erow(200002, 359), erow(200003, 358)], omat("203001"))
    chk13("an ordinary month is not a rise", acc20["rise_rows"], 0)
    acc21 = extend_new_acc()
    extend_absorb(acc21, [erow(200002, 100), erow(200008, 400)], omat("203001"))
    chk13("a jump across a period gap is not a rise", acc21["rise_rows"], 0)

    #: §8·14·6·7·2: a perf column carrying a monthly maturity date presses onto
    #: one offset against rem_legal; the period column itself does not.
    acc22 = extend_new_acc()
    for per, rem in ((200002, 359), (200003, 358), (200004, 357)):
        mm = per // 100 * 100 + per % 100
        fwd = (per // 100) * 12 + (per % 100 - 1) + rem
        mat_m = (fwd // 12) * 100 + (fwd % 12 + 1)
        extend_absorb(acc22, [erow(per, rem, c9=str(mat_m))], omat("203001"))
    pl22 = extend_payload(acc22)
    chk13("a monthly maturity column presses onto one offset",
          pl22["perf_cols"]["8"]["top"]["offset"], 0)
    chk13("  with share 1.0", pl22["perf_cols"]["8"]["top"]["share"], 1.0)
    chk13("the period column itself does not press",
          pl22["perf_cols"]["1"]["top"]["share"] > 0.5, False)

    def drive13(payload, want, tag, notwant=None):
        buf, keep = _io3.StringIO(), _sys3.stdout
        _sys3.stdout = buf
        try:
            print_extend(payload)
        except Exception as exc:                       # noqa: BLE001
            _sys3.stdout = keep
            chk13(f"print_extend survives {tag}", type(exc).__name__, "ok")
            return
        finally:
            _sys3.stdout = keep
        txt = buf.getvalue()
        ok = want in txt and not (notwant and notwant in txt)
        chk13(f"print_extend reads {tag}", ok, True)
        try:
            json.dumps(payload, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--extend json.dumps {tag}: {exc}")

    drive13(pl19, "FIRST BRANCH of §8·14·6·7·1", "re-set terms explain it")
    drive13(pl22, "FIRST BRANCH of §8·14·6·7·2", "a perf maturity column exists")
    flat = dict(pl19)
    flat["share_ne_risen"] = flat["share_eq_risen"]
    drive13(flat, "SECOND BRANCH: the two are equal", "the two shares equal")
    rev = dict(pl19)
    rev["share_ne_risen"], rev["share_eq_risen"] = 0.1, 0.9
    drive13(rev, "THIRD BRANCH", "the shares the wrong way round")
    empty = dict(pl19)
    empty["share_ne_risen"] = float("nan")
    drive13(empty, "has no referent", "one group empty")
    noperf = dict(pl19)
    noperf["perf_cols"] = {}
    drive13(noperf, "SECOND BRANCH: the perf side carries no monthly",
            "no perf YYYYMM column at all")

    # 14. --horizon, §8·14·6·8.
    print("\n  14. --horizon: is `period + rem_legal` naming a date")

    def chk14(name, got, want):
        ok = got == want
        print(f"     {name:<54}{str(got):>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--horizon {name}: {got} != {want}")

    chk14("monthdiff_add inverts monthdiff", monthdiff_add(200012, 1), 200101)
    chk14("  over a whole term", monthdiff_add(200001, 360), 203001)
    chk14("  and monthdiff undoes it",
          monthdiff(monthdiff_add(200704, 173), 200704), 173)

    def hrow(period, rem, mod="", defer="0.00", age=None, zb=""):
        f = [""] * PERF_FIELDS
        f[P_SEQ] = "F0001"
        f[P_PERIOD] = str(period)
        f[P_UPB] = "199000.00"
        f[P_REM] = str(rem)
        f[P_MODFLAG] = mod
        f[P_ZEROBAL] = zb
        f[P_DEFER_BAL] = defer
        if age is not None:
            f[P_AGE] = str(age)
        return f

    #: A loan that amortises normally names the same date every month; one that
    #: is re-cut on a Y row names a new one from then on.
    acc23 = horizon_new_acc()
    horizon_absorb(acc23, [hrow(200002, 359, age=1), hrow(200003, 358, age=2),
                           hrow(200004, 357, age=3)])
    chk14("an amortising loan never moves its date",
          (acc23["moved_y"], acc23["moved_not_y"]), (0, 0))
    chk14("  and all its pairs are non-Y",
          (acc23["pairs_y"], acc23["pairs_not_y"]), (0, 2))

    acc24 = horizon_new_acc()
    horizon_absorb(acc24, [hrow(200002, 359, age=1),
                           hrow(200003, 478, mod="Y", age=2),
                           hrow(200004, 477, mod="P", age=3)])
    chk14("a re-cut on a Y row moves it, and only there",
          (acc24["moved_y"], acc24["moved_not_y"]), (1, 0))
    chk14("  the P row after it does not move it again",
          (acc24["pairs_y"], acc24["pairs_not_y"]), (1, 1))
    chk14("  and the move is counted as an extension",
          (acc24["up"], acc24["down"]), (1, 0))

    #: A move on a row with no Y is the thing the second branch is about, and
    #: its shape has to be recorded, not just its count.
    acc25 = horizon_new_acc()
    horizon_absorb(acc25, [hrow(200002, 359, age=1),
                           hrow(200003, 350, age=2, zb="03",
                                defer="500.00")])
    chk14("a move with no Y is filed with its shape",
          (acc25["moved_not_y"], dict(acc25["not_y_size"]),
           dict(acc25["not_y_age"]), dict(acc25["not_y_zerobal"]),
           acc25["not_y_with_defer"]),
          (1, {-8: 1}, {2: 1}, {"03": 1}, 1))
    chk14("  and it counts as a shortening",
          (acc25["up"], acc25["down"]), (0, 1))

    #: §11 item 3: a counter that cannot fire is not a counter. A deferral row
    #: whose rem_legal will not parse must reach bad_bn_rows.
    acc26 = horizon_new_acc()
    horizon_absorb(acc26, [hrow(200002, 359, defer="900.00"),
                           hrow(200003, "n/a", defer="900.00")])
    chk14("a deferral row with no readable rem reaches bad_bn",
          (acc26["defer_rows"], acc26["bad_bn_rows"]), (2, 1))
    chk14("  and a gap in the period sequence yields no pair",
          horizon_payload(horizon_new_acc())["pairs_not_y"], 0)
    acc27 = horizon_new_acc()
    horizon_absorb(acc27, [hrow(200002, 359), hrow(200008, 300)])
    chk14("  nor does a jump across a period gap",
          (acc27["pairs_not_y"], acc27["moved_not_y"]), (0, 0))

    def drive14(payload, want, tag):
        buf, keep = _io3.StringIO(), _sys3.stdout
        _sys3.stdout = buf
        try:
            print_horizon(payload)
        except Exception as exc:                       # noqa: BLE001
            _sys3.stdout = keep
            chk14(f"print_horizon survives {tag}", type(exc).__name__, "ok")
            return
        finally:
            _sys3.stdout = keep
        chk14(f"print_horizon reads {tag}", want in buf.getvalue(), True)
        try:
            json.dumps(payload, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--horizon json.dumps {tag}: {exc}")

    base = horizon_payload(acc24)
    drive14(base, "FIRST BRANCH", "Y moves it and non-Y does not")
    flip = dict(base); flip["rate_y"], flip["rate_not_y"] = 0.001, 0.5
    drive14(flip, "the wrong way", "non-Y moves it more")
    same = dict(base); same["rate_y"] = same["rate_not_y"] = 0.25
    drive14(same, "equal at", "the two rates equal")
    still = dict(base); still["moved_y"] = still["moved_not_y"] = 0
    drive14(still, "THIRD BRANCH", "nothing moved at all")

    # 15. --balid, §8·18. Constructed loans whose true balance is known first.
    print("\n  15. --balid: which column is V's interest-bearing balance")

    def chk15(name, got, want, tol=None):
        ok = (abs(got - want) <= tol) if tol is not None else (got == want)
        shown = f"{got:,.4f}" if tol is not None else str(got)
        print(f"     {name:<54}{shown:>18}  (want {want})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"--balid {name}: {got} != {want}")

    U0, RATE, TERM, DEF = 200_000.0, 6.0, 360, 9_000.0
    Pc = contract_payment(U0, RATE / 1200.0, TERM)
    i = RATE / 1200.0

    def brow15(period, upb, defer=DEF, mod="", zb="", rate=RATE):
        f = [""] * PERF_FIELDS
        f[P_SEQ] = "F0001"
        f[P_PERIOD] = str(period)
        f[P_UPB] = f"{upb:.2f}"
        f[P_DELINQ] = "00"
        f[P_REM] = "300"
        f[P_MODFLAG] = mod
        f[P_ZEROBAL] = zb
        f[P_RATE] = f"{rate:.3f}"
        f[P_DEFER_BAL] = f"{defer:.2f}"
        return f

    #: **A world where H1 is true**: col 3 = interest-bearing + D, and the
    #: interest-bearing part amortises.
    ib0 = 150_000.0
    ib1 = ib0 * (1 + i) - Pc
    accA = balid_new_acc()
    balid_absorb(accA, [brow15(200002, ib0 + DEF), brow15(200003, ib1 + DEF)],
                 (U0, RATE, TERM), 2000)
    plA = balid_payload(accA)
    #: **The tolerance is half a cent, and it is not a fudge.** The fixture
    #: writes UPB with `.2f`, exactly as the file does, so a residual built
    #: from two reported balances carries the cent they are reported to. The
    #: first version asserted an exact zero and read 0.00105 — the fixture was
    #: right and the expectation was idealised. `ROUND_TOL` is already this
    #: file's name for half a cent, for the same reason.
    HC = ROUND_TOL
    chk15("H1 world: one pair kept", plA["kept"], 1)
    chk15("  resid_H1 is within half a cent of zero",
          plA["absmed_h1"], 0.0, tol=HC)
    chk15("  resid_H2 is within half a cent of D*i",
          plA["absmed_h2"], DEF * i, tol=HC)
    #: The identity has no reported balance in it: `r2 - r1 = D - D(1+i)`
    #: exactly, so this one really is machine dust.
    chk15("  and the algebraic identity holds to machine dust",
          plA["identity_absmed"], 0.0, tol=1e-9)

    #: **A world where H2 is true**: col 3 IS the interest-bearing balance.
    accB = balid_new_acc()
    balid_absorb(accB, [brow15(200002, ib0), brow15(200003, ib1)],
                 (U0, RATE, TERM), 2000)
    plB = balid_payload(accB)
    chk15("H2 world: resid_H2 is within half a cent of zero",
          plB["absmed_h2"], 0.0, tol=HC)
    chk15("  and resid_H1 is within half a cent of D*i",
          plB["absmed_h1"], DEF * i, tol=HC)
    #: **And the resolution the whole discriminant rests on**: the half cent
    #: the balances carry against the D*i the two hypotheses differ by.
    chk15("  D*i is four orders of magnitude above the half cent",
          round((DEF * i) / HC), 9000)

    #: The population's own exclusions, each on its own line.
    def one(rows, orig=(U0, RATE, TERM)):
        a = balid_new_acc()
        balid_absorb(a, rows, orig, 2000)
        return a

    a = one([brow15(200002, ib0 + DEF), brow15(200008, ib1 + DEF)])
    chk15("a period gap is dropped, not bridged", a["drop_gap"], 1)
    a = one([brow15(200002, ib0 + DEF, defer=0.0),
             brow15(200003, ib1 + DEF, defer=0.0)])
    chk15("no deferral outstanding is dropped", a["drop_defer"], 1)
    a = one([brow15(200002, ib0 + DEF),
             brow15(200003, ib1 + DEF, defer=DEF + 100)])
    chk15("a month the deferral itself moved is dropped",
          a["drop_defer_moved"], 1)
    a = one([brow15(200002, ib0 + DEF), brow15(200003, ib1 + DEF, rate=6.5)])
    chk15("a rate change is dropped", a["drop_rate"], 1)
    a = one([brow15(200002, ib0 + DEF), brow15(200003, ib1 + DEF, zb="01")])
    chk15("a zero-balance code is dropped", a["drop_zerobal"], 1)
    a = one([brow15(200002, ib0 + DEF), brow15(200003, ib1 + DEF)],
            orig=None)
    chk15("a loan with no orig row is counted", a["loans_no_orig"], 1)
    a = one([brow15(200002, ib0 + DEF, mod="P"), brow15(200003, ib1 + DEF)])
    chk15("a loan ever modified is excluded whole", a["loans_ever_mod"], 1)
    chk15("  and contributes no pairs", a["pairs"], 0)

    #: The coverage line has to partition, or it is decoration.
    accC = balid_new_acc()
    for rr in ([brow15(200002, ib0 + DEF), brow15(200003, ib1 + DEF)],
               [brow15(200002, ib0 + DEF), brow15(200008, ib1 + DEF)],
               [brow15(200002, ib0 + DEF, defer=0.0),
                brow15(200003, ib1 + DEF, defer=0.0)]):
        balid_absorb(accC, rr, (U0, RATE, TERM), 2000)
    plC = balid_payload(accC)
    chk15("dropped + kept = pairs",
          plC["dropped_total"] + plC["kept"], plC["pairs"])

    #: The printer, over all four registered landings.
    def drive15(mut, want, tag, notwant=None):
        p5 = dict(plA); p5.update(mut)
        buf, keep = _io3.StringIO(), _sys3.stdout
        _sys3.stdout = buf
        try:
            print_balid(p5)
        except Exception as exc:                       # noqa: BLE001
            _sys3.stdout = keep
            chk15(f"print_balid survives {tag}", type(exc).__name__, "ok")
            return
        finally:
            _sys3.stdout = keep
        txt5 = buf.getvalue()
        ok = want in txt5 and not (notwant and notwant in txt5)
        chk15(f"print_balid reads {tag}", ok, True)
        try:
            json.dumps(p5, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            fails.append(f"--balid json.dumps {tag}: {exc}")

    drive15({"absmed_h1": 0.01, "absmed_h2": 45.0, "absmed_di": 45.0},
            "FIRST BRANCH", "H1 wins", notwant="SECOND BRANCH")
    drive15({"absmed_h1": 45.0, "absmed_h2": 0.01, "absmed_di": 45.0},
            "SECOND BRANCH", "H2 wins", notwant="FIRST BRANCH")
    drive15({"absmed_h1": 20.0, "absmed_h2": 21.0, "absmed_di": 45.0},
            "THIRD BRANCH", "the two are within half of D*i")
    drive15({"absmed_h1": 900.0, "absmed_h2": 945.0, "absmed_di": 45.0},
            "FOURTH BRANCH", "neither is near zero")

    print("\n  " + ("FAILED: " + "; ".join(fails) if fails else
                    "all fifteen pass."))
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# --depth. §12.6. Estimates nothing.
# ---------------------------------------------------------------------------

def cmd_depth(only) -> int:
    vintages = only or VINTAGES
    print("C8-1d depth. Enumerates the domain and estimates nothing. §12.6.\n")
    print(f"  {'vintage':<8}{'orig/perf':>11}{'FRM':>9}{'loans':>9}"
          f"{'gated in':>10}{'seg all':>9}{'seg gate':>10}{'gate%':>8}"
          f"{'shortest 3':>16}")
    rows, totals = [], {}
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v:<8}{'missing':>11}")
            continue
        orig, ocounts = read_orig(v)
        tally, seg_lengths, gate_lengths, n_loans, n_gated = {}, [], [], 0, 0
        for seq, recs in loans(v):
            meta = orig.get(seq)
            if meta is None:
                tally["skipped_not_frm_or_absent"] = \
                    tally.get("skipped_not_frm_or_absent", 0) + 1
                continue
            n_loans += 1
            o_upb, rate, term = meta
            passed = False
            for seg_rate, months in quiet_segments(recs, tally):
                r = segment_reading(seg_rate, months, o_upb, term)
                if r is None:
                    tally["segment_unusable"] = tally.get("segment_unusable", 0) + 1
                    continue
                seg_lengths.append(r["n_diffs"])
                if r["gate_pass"]:
                    gate_lengths.append(r["n_diffs"])
                    passed = True
                else:
                    tally["segment_failed_u0_gate"] = \
                        tally.get("segment_failed_u0_gate", 0) + 1
            n_gated += 1 if passed else 0
        shortest = sorted(gate_lengths)[:3]
        fc = f"{ocounts['field_count']}/{PERF_FIELDS}"
        gshare = len(gate_lengths) / len(seg_lengths) if seg_lengths else 0.0
        print(f"  {v:<8}{fc:>11}{ocounts['frm']:>9}{n_loans:>9}"
              f"{n_gated:>10}{len(seg_lengths):>9}{len(gate_lengths):>10}"
              f"{gshare:>8.3f}{str(shortest):>16}")
        by_bin, by_bin_gate = {}, {}
        for n in seg_lengths:
            b = length_bin(n)
            by_bin[b] = by_bin.get(b, 0) + 1
        for n in gate_lengths:
            b = length_bin(n)
            by_bin_gate[b] = by_bin_gate.get(b, 0) + 1
        rows.append({"vintage": v, "orig_fields": ocounts["field_count"],
                     "frm_loans": ocounts["frm"], "arm_or_other": ocounts["arm_or_other"],
                     "loans_seen": n_loans, "loans_with_a_gated_segment": n_gated,
                     "segments_all": len(seg_lengths),
                     "segments_gate_pass": len(gate_lengths),
                     "gate_pass_share": (len(gate_lengths) / len(seg_lengths)
                                         if seg_lengths else 0.0),
                     "shortest_three_gate_pass": shortest,
                     "segments_by_length_all": by_bin,
                     "segments_by_length_gate_pass": by_bin_gate,
                     "drops": dict(sorted(tally.items()))})
        for k, n in tally.items():
            totals[k] = totals.get(k, 0) + n

    print("\n  rows that left the domain, summed over the vintages above:")
    for k, n in sorted(totals.items()):
        print(f"    {k:<32} {n:>12,d}")
    print("\n  Read: `dropped_age_lt_8` is §11.5's rule doing its job and it is\n"
          "  printed rather than silent. `segment_failed_u0_gate` is §12.2: a\n"
          "  curtailment before the segment's first month, which the amortisation\n"
          "  identity cannot see past. Nothing here is a threshold; the shortest\n"
          "  three segments per vintage are the number that decides what the\n"
          "  minimum estimator can be read on: the thinnest cell,\n"
          "  not the average.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_c8_1d_depth.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "c8_1d_depth",
         "diagnostic_only": True,
         "diagnostic_reason":
             "B8-1 has not been run on Fannie, so this stage's readings serve "
             "only the payment model decision in b8_omega.py and carry no omega "
             "claim. the B10 availability register §12.0.",
         "min_age": MIN_AGE, "u0_half_grid": U0_HALF_GRID,
         "vintages": rows, "drops_total": dict(sorted(totals.items()))},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --run. §12.4 and §12.5.
# ---------------------------------------------------------------------------

def cmd_run(only) -> int:
    vintages = only or VINTAGES
    print("C8-1d run. §12.4's three objects, §12.5's length strata. "
          "No threshold in this file.\n")
    arms = {"fine_gated": {}, "coarse_all": {}}
    for v in vintages:
        if not archive(v).exists():
            continue
        orig, _ = read_orig(v)
        for seq, recs in loans(v):
            meta = orig.get(seq)
            if meta is None:
                continue
            o_upb, rate, term = meta
            for seg_rate, months in quiet_segments(recs):
                r = segment_reading(seg_rate, months, o_upb, term)
                if r is None:
                    continue
                b = length_bin(r["n_diffs"])
                arms["coarse_all"].setdefault(b, []).append(
                    dict(r, ref=r["p_contract_coarse"]))
                if r["gate_pass"] and r["p_contract"] is not None:
                    arms["fine_gated"].setdefault(b, []).append(
                        dict(r, ref=r["p_contract"]))

    summary = {}
    for arm_name, strata in arms.items():
        print(f"\n{'=' * 72}\n  ARM: {arm_name}   "
              + ("§12.2's U0-free contract payment, on the segments that pass the\n"
                 "         gate. Sharp instrument, selected population (§12.9)."
                 if arm_name == "fine_gated" else
                 "the original contract payment from the rounded original\n"
                 "         balance, on every segment. Blunt instrument "
                 "(±500/U0), unselected.")
              + f"\n{'=' * 72}")
        summary[arm_name] = _report_arm(strata)
    return _write_run(summary)


def _report_arm(strata):
    out = {}
    for b in BIN_ORDER:
        rs = strata.get(b, [])
        if len(rs) < 2:
            if rs:
                print(f"  segment length {b}   n = {len(rs)}, too few for "
                      f"quantiles; the count prints and nothing is estimated.\n")
                out[b] = {"n": len(rs), "note": "n < 2, no quantiles"}
            continue
        ratios = [r["p_min"] / r["ref"] for r in rs]
        diffs = [r["p_min"] - r["ref"] for r in rs]
        n = len(rs)

        print(f"  segment length {b}   n = {n:,d}")
        print(f"    P_min / P_contract, share landing within")
        bands = ((1e-6, "1e-6"), (1e-4, "1e-4"), (1e-3, "1e-3"), (1e-2, "1e-2"))
        band_out = {}
        for eps, name in bands:
            share = sum(1 for x in ratios if abs(x - 1.0) <= eps) / n
            band_out[name] = share
            print(f"      |ratio - 1| <= {name:<6} {share:8.4f}")
        qs = statistics.quantiles(ratios, n=100)
        print(f"      p10 {qs[9]:.5f}  p50 {qs[49]:.5f}  p90 {qs[89]:.5f}")

        print(f"    P_min on a round number, against its own background rate")
        mod_out = {}
        for m in MODULI:
            hit = sum(1 for r in rs
                      if abs(round(r["p_min"] / m) * m - r["p_min"]) < ROUND_TOL) / n
            bg = background_rate(m)
            mod_out[str(m)] = {"share": hit, "background": bg,
                               "times_background": hit / bg if bg else None}
            print(f"      multiple of {m:<4} {hit:8.5f}   background {bg:.5f}"
                  f"   x{hit / bg:7.2f}")
        whole = sum(1 for r in rs
                    if abs(round(r["p_min"]) - r["p_min"]) < ROUND_TOL) / n
        bg1 = background_rate(1)
        mod_out["whole_dollar"] = {"share": whole, "background": bg1,
                                   "times_background": whole / bg1}
        print(f"      whole dollars     {whole:8.5f}   background {bg1:.5f}"
              f"   x{whole / bg1:7.2f}")

        print(f"    P_min - P_contract, share on a positive round number")
        pos_out = {}
        for m in MODULI:
            hit = sum(1 for d in diffs
                      if d > 0.5 and abs(round(d / m) * m - d) < ROUND_TOL) / n
            bg = background_rate(m)
            pos_out[str(m)] = {"share": hit, "background": bg,
                               "times_background": hit / bg if bg else None}
            print(f"      positive multiple of {m:<4} {hit:8.5f}"
                  f"   background {bg:.5f}   x{hit / bg:7.2f}")
        dq = statistics.quantiles(diffs, n=100)
        print(f"      diff p10 {dq[9]:+.2f}  p50 {dq[49]:+.2f}  p90 {dq[89]:+.2f}")

        spreads = [r["p_spread"] for r in rs]
        sq = statistics.quantiles(spreads, n=100)
        print(f"    within-segment spread of P: p50 {sq[49]:.2f}  p90 {sq[89]:.2f}\n")

        out[b] = {"n": n, "ratio_bands": band_out, "ratio_p10": qs[9],
                  "ratio_p50": qs[49], "ratio_p90": qs[89],
                  "p_min_on_multiple": mod_out, "diff_positive_multiple": pos_out,
                  "diff_p10": dq[9], "diff_p50": dq[49], "diff_p90": dq[89],
                  "spread_p50": sq[49], "spread_p90": sq[89]}
    return out


def _write_run(summary) -> int:
    print("\n  Read, per §12.4, three cells that can all hold at once:\n"
          "    mass at ratio 1.000 with the moduli at background -> the borrower\n"
          "      pays the contract, and b8_omega.py can use the contract payment;\n"
          "    moduli above background with no matching mass at 1.000 -> the\n"
          "      borrower rounds, and the actual level has to be carried per segment;\n"
          "    a positive round diff -> contract plus a fixed extra principal, and\n"
          "      what is carried is the difference rather than the level.\n"
          "  All three holding is a mixed population and is reported as one.\n"
          "  Per §12.5 the strata are the reading: the minimum is biased upward on\n"
          "  short segments, so a pattern that is present only in 8-12 is the\n"
          "  estimator and a pattern present in 61+ as well is the data.\n"
          "  Per §12.9 the two arms are read together: the fine arm's population is\n"
          "  selected on having paid no extra principal, which is the same trait as\n"
          "  cell one, so a mass at 1.000 there is partly built in. The coarse arm\n"
          "  is unselected and its moduli are still readable at the $10 level, so\n"
          "  it is the arm that carries cell two. Cell one is claimed only if the\n"
          "  coarse arm shows the mass as well.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_c8_1d.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "c8_1d",
         "diagnostic_only": True,
         "diagnostic_reason":
             "B8-1 has not been run on Fannie, so this stage's readings serve "
             "only the payment model decision in b8_omega.py and carry no omega "
             "claim. the B10 availability register §12.0.",
         "min_age": MIN_AGE, "u0_half_grid": U0_HALF_GRID,
         "moduli": list(MODULI), "arms": summary},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0



# ---------------------------------------------------------------------------
# --grid-k. The precondition B10 owes before handing the compatibility spec to B8. Registered before the code.
#
# The question is not "is Freddie's grid $1,000" (§11.3 already measured that).
# It is whether the arithmetic that makes the grid produce frozen months holds
# on this carrier:
#
#     P(frozen) = 1 - p/g      for p < g, phase uniform
#
# where `g` is the reporting step and `p` is the principal retired that month.
# If it does not hold here, the ratio `k = g/p` must not be handed to B8 and the
# handover shrinks to step one (the grid itself).
# ---------------------------------------------------------------------------

#: Freddie's reporting step, **measured** in §11.3, not assumed.
GRID_STEP = 1000.0

#: Candidate steps printed side by side, §10·9·2 step one. All printed, none
#: chosen. The shares are nested by construction (a multiple of 1000 is also a
#: multiple of 100); that nesting is the shape being read, not a defect.
GRID_CANDIDATES = (1.0, 10.0, 100.0, 1000.0, 10000.0)

#: Loan ages printed. Wide enough to hold §11.3's cliff (6 -> 7) and the o18
#: population boundary (age 8) with room on both sides.
GRID_AGES = tuple(range(1, 25))

#: `p` histogram bin width in dollars. A median to the dollar is far finer than
#: anything this check reads.
P_MAX = 5000


def on_grid(x: float, step: float) -> bool:
    """Is ``x`` a multiple of ``step``, to half a cent (``ROUND_TOL``)."""
    return abs(x - round(x / step) * step) < ROUND_TOL


def sched_balance(u0: float, i: float, term: int, k: float) -> float:
    """§12.2's identity run forward. ``k`` may be fractional (§5·5·6's sweep)."""
    a_n = annuity_factor(i, term)
    if a_n <= 0.0 or k >= term:
        return 0.0
    return u0 * annuity_factor(i, term - k) / a_n


def scheduled_principal(u0: float, rate_pct: float, term: int, k: int) -> float:
    """Principal retired in month ``k``, from ``(U0, i, n)`` and nothing else.

    **Not from differenced reported UPB.** Below age 7 the reported UPB *is* the
    grid this check is measuring, so differencing it to estimate `p` would put
    the answer inside its own construction (纪律 15, and the same trap §12.9
    caught in the U0 gate). The design file states this as structural in
    §10·9·3, and B8 is being asked to obey it on Fannie for the same reason.
    """
    if term <= 0 or k < 1 or k > term:
        return float("nan")
    i = rate_pct / 1200.0
    a = annuity_factor(i, term)
    if a <= 0.0:
        return float("nan")
    pay = u0 * i / a if i else u0 / term
    return pay - sched_balance(u0, i, term, k - 1) * i


def grid_k_new_acc() -> dict:
    return {"pairs": {}, "frozen": {}, "pairs_frm": {}, "frozen_frm": {},
            "rows": {}, "ongrid": {}, "phist": {},
            "pclip_sum": {}, "pclip_n": {},
            "o18_pairs": 0, "o18_frozen": 0,
            "relerr_sum": 0.0, "relerr_n": 0, "loans": 0}


def _bump(d: dict, key, n: int = 1) -> None:
    d[key] = d.get(key, 0) + n


def grid_k_absorb(acc: dict, recs, meta) -> None:
    """Fold one loan's performance rows into the accumulator.

    Split out from the scan so that ``--selftest`` can drive the **same** code
    with constructed rows whose truth is known. A syntax check proves a file
    parses, it does not prove a line ever runs (MEASUREMENT.md failure mode 16).
    """
    acc["loans"] += 1
    if meta is not None:
        u0, rate, term = meta
        if u0 > 0:
            acc["relerr_sum"] += U0_HALF_GRID / u0
            acc["relerr_n"] += 1
    prev = None
    for f in recs:
        try:
            per = int(f[P_PERIOD])
            upb = float(f[P_UPB])
            age = int(f[P_AGE])
        except (ValueError, IndexError):
            prev = None
            continue
        if upb > 0 and age in GRID_AGES_SET:
            _bump(acc["rows"], age)
            row = acc["ongrid"].setdefault(age, {})
            for g in GRID_CANDIDATES:
                if on_grid(upb, g):
                    _bump(row, g)
        if prev is not None:
            p0, u_prev, a0 = prev
            if per == next_period(p0) and u_prev > 0 and upb > 0:
                frozen = (u_prev == upb)
                # §10·4's population predicate, replicated bit for bit from
                # b10_o18_null.py so the cross-check is a cross-check.
                if not (a0 >= 8 and age >= 8):
                    acc["o18_pairs"] += 1
                    acc["o18_frozen"] += 1 if frozen else 0
                if age in GRID_AGES_SET:
                    _bump(acc["pairs"], age)
                    if frozen:
                        _bump(acc["frozen"], age)
                    if meta is not None:
                        _bump(acc["pairs_frm"], age)
                        if frozen:
                            _bump(acc["frozen_frm"], age)
                        p = scheduled_principal(meta[0], meta[1], meta[2], age)
                        if p == p and p >= 0.0:
                            # The histogram bin is clipped, the row is not
                            # dropped. An earlier version guarded with
                            # `p < P_MAX` and silently discarded the largest
                            # principals, which would have put the median and
                            # the mean on two different populations and made
                            # the two columns below incomparable.
                            _bump(acc["phist"].setdefault(age, {}),
                                  min(int(p), P_MAX - 1))
                            acc["pclip_sum"][age] = (
                                acc["pclip_sum"].get(age, 0.0)
                                + min(p, GRID_STEP))
                            _bump(acc["pclip_n"], age)
        prev = (per, upb, age)


GRID_AGES_SET = frozenset(GRID_AGES)


def _hist_median(h: dict) -> float:
    n = sum(h.values())
    if not n:
        return float("nan")
    half, run = n / 2.0, 0
    for b in sorted(h):
        run += h[b]
        if run >= half:
            return float(b) + 0.5
    return float("nan")


def grid_k_payload(acc: dict) -> dict:
    rows = []
    for t in GRID_AGES:
        pr, fr = acc["pairs"].get(t, 0), acc["frozen"].get(t, 0)
        pf, ff = acc["pairs_frm"].get(t, 0), acc["frozen_frm"].get(t, 0)
        p = _hist_median(acc["phist"].get(t, {}))
        npc = acc["pclip_n"].get(t, 0)
        pm = acc["pclip_sum"].get(t, 0.0) / npc if npc else float("nan")
        k = GRID_STEP / pm if pm == pm and pm > 0 else float("nan")
        # The crossing probability of one loan is min(p/g, 1); the population
        # share is therefore the **mean** of that, not the formula evaluated at
        # the median. `p` is right-skewed (a 15-year note retires roughly three
        # times the principal of a 30-year note at the same balance), so the
        # median understates the crossing rate and overstates the freeze rate.
        # Both columns are printed side by side rather than one replacing the
        # other, per §19·5: the judgement that changes a number sits next to it.
        pred = max(0.0, 1.0 - pm / GRID_STEP) if pm == pm else float("nan")
        pred_med = max(0.0, 1.0 - p / GRID_STEP) if p == p else float("nan")
        obs = ff / pf if pf else float("nan")
        n_rows = acc["rows"].get(t, 0)
        share = {str(int(g)): (acc["ongrid"].get(t, {}).get(g, 0) / n_rows
                               if n_rows else None)
                 for g in GRID_CANDIDATES}
        rows.append({"age": t, "pairs": pr, "frozen": fr,
                     "rate_all": (fr / pr if pr else None),
                     "pairs_frm": pf, "frozen_frm": ff,
                     "rate_frm": (obs if obs == obs else None),
                     "p_median": (p if p == p else None),
                     "p_mean_clipped": (pm if pm == pm else None),
                     "k_from_mean": (k if k == k else None),
                     "pred_from_mean": (pred if pred == pred else None),
                     "pred_from_median": (pred_med if pred_med == pred_med
                                          else None),
                     "rows": n_rows, "ongrid_share": share})
    return {"grid_step": GRID_STEP,
            "candidates": [int(g) for g in GRID_CANDIDATES],
            "o18_pairs": acc["o18_pairs"], "o18_frozen": acc["o18_frozen"],
            "u0_rel_error_mean": (acc["relerr_sum"] / acc["relerr_n"]
                                  if acc["relerr_n"] else None),
            "loans": acc["loans"], "by_age": rows}


def print_grid_k(payload: dict) -> None:
    print("\n  A. on-grid share of the reported UPB, by loan age, all loans")
    print("     (§10·9·2 step one, run on Freddie so B8 can compare shapes)")
    print(f"     {'age':>4}{'rows':>12}" +
          "".join(f"{'%'+str(int(g)):>10}" for g in GRID_CANDIDATES))
    for r in payload["by_age"]:
        sh = r["ongrid_share"]
        cells = "".join(
            f"{(sh[str(int(g))] * 100):>9.3f}%" if sh[str(int(g))] is not None
            else f"{'-':>10}" for g in GRID_CANDIDATES)
        print(f"     {r['age']:>4}{r['rows']:>12,}{cells}")

    print("\n  B. the identity  P(frozen) = 1 - E[min(p,g)]/g,  FRM only,"
          " p from the schedule")
    print("     Two columns for `pred`: the mean is the one the arithmetic asks"
          " for, the\n     median is what an earlier version used. Both printed,"
          " neither dropped.")
    print(f"     {'age':>4}{'pairs':>12}{'p_med':>9}{'p_mean':>9}{'k':>8}"
          f"{'pred_med':>10}{'pred':>9}{'obs':>9}{'obs-pred':>10}")
    for r in payload["by_age"]:
        if not r["pairs_frm"]:
            continue
        p, pm, k = r["p_median"], r["p_mean_clipped"], r["k_from_mean"]
        pred, pmed = r["pred_from_mean"], r["pred_from_median"]
        obs = r["rate_frm"]
        gap = (obs - pred) if (obs is not None and pred is not None) else None
        nan = float("nan")
        print(f"     {r['age']:>4}{r['pairs_frm']:>12,}"
              f"{(p if p is not None else nan):>9.2f}"
              f"{(pm if pm is not None else nan):>9.2f}"
              f"{(k if k is not None else nan):>8.3f}"
              f"{(pmed * 100 if pmed is not None else nan):>9.2f}%"
              f"{(pred * 100 if pred is not None else nan):>8.2f}%"
              f"{(obs * 100 if obs is not None else nan):>8.2f}%"
              f"{(gap * 100 if gap is not None else nan):>+9.2f}%")

    n, f = payload["o18_pairs"], payload["o18_frozen"]
    print("\n  C. cross-check against §10·4, same population predicate as "
          "b10_o18_null.py")
    print(f"     age<8 pairs {n:,}   frozen {f:,}   "
          f"rate {(f / n * 100 if n else float('nan')):.4f}%")
    print("     §10·4 prints 10,247,131 pairs and 4,901,368 frozen "
          "(47.8315%). Equal to the digit or the pair definitions differ,\n"
          "     and if they differ this check is not a cross-check.")

    e = payload["u0_rel_error_mean"]
    print(f"\n  D. `p` is built from orig U0, which sits on the $1,000 grid, so it\n"
          f"     carries a relative error of at most 500/U0. Mean over the loans\n"
          f"     used here: {(e * 100 if e is not None else float('nan')):.4f}%. "
          f"The fine arm is not run for `p`\n"
          f"     because that error is two orders below what this check reads,\n"
          f"     and the fine arm's gate selects on payment behaviour (§12.9).")

    print("\n  Read, per the criteria fixed before the run, and the reading is the shape not the level:\n"
          "    ages 1-6 show obs falling as age rises, and pred falls too ->\n"
          "      the identity's direction holds and `k` may go to B8;\n"
          "    obs does not fall with age -> principal is not the driver, the\n"
          "      identity fails, hand B8 step one only;\n"
          "    both fall but obs sits on one side of pred throughout -> a constant\n"
          "      factor (phase or mixture); `k` may still go, carrying that factor;\n"
          "    ages 7 and 8 do not drop to the background rate in table A -> §5·2's\n"
          "      boundary is read wrong, go back. This branch can overturn §5·2.")


def cmd_grid_k(only) -> int:
    vintages = only or VINTAGES
    print("C8-1d grid-k. The §10·9·7 precondition. Estimates no omega, reads no\n"
          "B8 prediction, and does not transfer to Fannie.\n")
    acc = grid_k_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        orig, _ = read_orig(v)
        for seq, recs in loans(v):
            grid_k_absorb(acc, recs, orig.get(seq))
        print(f"  {v}  done   loans so far {acc['loans']:,}")
    payload = grid_k_payload(acc)
    print_grid_k(payload)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_grid_k.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "grid_k",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Precondition for the compatibility spec handed to B8. Counts and a schedule identity only; no omega, no B8 "
             "prediction, and nothing here transfers to Fannie (§10·9·6).",
         **payload},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0



# ---------------------------------------------------------------------------
# --zero-upb. Registered before the code.
#
# §11.3/§5·2 判 the age-0 orig/perf mismatch to be double rounding. Rounding
# moves at most half a grid step, so the 975 loans whose age-0 perf UPB reads
# exactly 0.00 against a normal orig balance are not rounding. They are that
# explanation's residue, and this mode names them.
#
# The outcome map partitions on ONE variable at each level (the zero-balance
# code, then whether a positive UPB ever appears), never on a conjunction.
# MEASUREMENT.md failure mode 17.
# ---------------------------------------------------------------------------

ZERO_CODES = ("01", "02", "03", "09", "15", "96")


def read_orig_all(vintage: int) -> dict:
    """``{loan_seq: orig_upb}`` for **every** loan, not just the fixed-rate ones.

    ``read_orig`` filters to ``FRM`` because C8-1d needs a constant rate. §5·4
    is about a reporting convention, which has nothing to do with amortisation
    type, so filtering here would answer a different question.
    """
    out = {}
    with zipfile.ZipFile(archive(vintage)) as zf:
        for f in _lines(zf, f"sample_orig_{vintage}.txt"):
            try:
                out[f[O_SEQ]] = float(f[O_UPB])
            except (ValueError, IndexError):
                continue
    return out


def zero_upb_absorb(acc: dict, recs, orig_upb) -> None:
    """Fold one loan into the §5·4 accumulator. Split out so --selftest drives it."""
    first = None
    n_rows = 0
    later_positive = False
    gap = 0
    for f in recs:
        try:
            upb = float(f[P_UPB])
            age = int(f[P_AGE])
        except (ValueError, IndexError):
            continue
        n_rows += 1
        if age == 0 and first is None:
            first = f
        elif first is not None:
            if upb > 0:
                later_positive = True
            elif not later_positive:
                gap += 1
    if first is None:
        return
    acc["age0"] += 1
    if orig_upb is None:
        acc["no_orig"] += 1
        return
    try:
        upb0 = float(first[P_UPB])
    except (ValueError, IndexError):
        acc["unparsed"] += 1
        return
    if abs(upb0 - orig_upb) < ROUND_TOL:
        return
    acc["mismatch"] += 1
    if upb0 != 0.0:
        return
    acc["zero"] += 1
    code = first[P_ZEROBAL].strip() if len(first) > P_ZEROBAL else ""
    if code:
        acc["by_code"][code] = acc["by_code"].get(code, 0) + 1
        bucket = "terminated"
    elif later_positive:
        bucket = "reporting_gap"
        acc["gap_len"][min(gap, 24)] = acc["gap_len"].get(min(gap, 24), 0) + 1
    else:
        bucket = "never_reports_a_balance"
    acc["bucket"][bucket] = acc["bucket"].get(bucket, 0) + 1
    acc["rows_hist"][min(n_rows, 60)] = acc["rows_hist"].get(min(n_rows, 60), 0) + 1
    acc["orig_sum"] += orig_upb


def zero_upb_new_acc() -> dict:
    return {"age0": 0, "mismatch": 0, "zero": 0, "no_orig": 0, "unparsed": 0,
            "by_code": {}, "bucket": {}, "rows_hist": {}, "gap_len": {},
            "orig_sum": 0.0, "per_vintage": {}}


def print_zero_upb(acc: dict) -> None:
    print("\n  A. cross-check against §5·2 (hard gate, not a reading)")
    print(f"     age-0 loans {acc['age0']:,}   mismatched {acc['mismatch']:,}"
          f"   of those perf == 0.00: {acc['zero']:,}")
    print("     §5·2 prints 1,192,198 / 144,719 / 975. Equal to the digit, or the"
          " populations differ\n     and nothing below may be quoted.")

    print("\n  B. §5·4·1, partitioned on the zero-balance code")
    tot = max(acc["zero"], 1)
    for name in ("terminated", "reporting_gap", "never_reports_a_balance"):
        n = acc["bucket"].get(name, 0)
        print(f"     {name:<26}{n:>8,}{n / tot * 100:>9.2f}%")
    if acc["by_code"]:
        print("     codes on the terminated ones: "
              + ", ".join(f"{k}={v:,}" for k, v in sorted(acc["by_code"].items())))

    print("\n  C. rows per loan (the terminated reading predicts very few)")
    h = acc["rows_hist"]
    if h:
        n = sum(h.values())
        run = 0
        p50 = p90 = None
        for b in sorted(h):
            run += h[b]
            if p50 is None and run >= n * 0.5:
                p50 = b
            if p90 is None and run >= n * 0.9:
                p90 = b
        print(f"     n {n:,}   min {min(h)}   p50 {p50}   p90 {p90}   max {max(h)}"
              f"   (60 = clipped)")
    if acc["gap_len"]:
        print(f"     reporting-gap length: "
              + ", ".join(f"{k}:{v:,}" for k, v in sorted(acc["gap_len"].items())))

    print("\n  D. per vintage")
    for v in sorted(acc["per_vintage"]):
        print(f"     {v}  zero {acc['per_vintage'][v]:,}")

    print("\n  Read, per the criteria fixed before the run, one variable per level:\n"
          "    code non-empty -> the loan terminated in its first month and the\n"
          "      zero is the termination convention; §5·2's residue closes;\n"
          "    code empty and a positive UPB appears later -> a transient\n"
          "      reporting gap, named, and the gap-length distribution is printed;\n"
          "    code empty and no positive UPB ever -> this loan never reports a\n"
          "      balance. No name. Report as is and register it, do not explain it.")


def cmd_zero_upb(only) -> int:
    vintages = only or VINTAGES
    print("§5·4: naming the age-0 rows whose perf UPB reads exactly 0.00.\n"
          "Counts only. No omega, no B8 prediction, no transfer to Fannie.\n")
    acc = zero_upb_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        orig = read_orig_all(v)
        before = acc["zero"]
        for seq, recs in loans(v):
            zero_upb_absorb(acc, recs, orig.get(seq))
        acc["per_vintage"][v] = acc["zero"] - before
        print(f"  {v}  done   zero so far {acc['zero']:,}")
    print_zero_upb(acc)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_zero_upb.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "zero_upb",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Counts only; names the "
             "residue of §5·2's double-rounding explanation. Nothing here "
             "transfers to Fannie (§5·4·4).",
         **{k: v for k, v in acc.items()}},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0



# ---------------------------------------------------------------------------
# --phase. Registered before the code.
#
# §10·9's closed form assumes the origination phase is uniform. §14 measured it
# is not (22.7%-28.1% of borrowers take a round thousand). This mode drops the
# assumption instead of patching it: it rebuilds the reported series loan by
# loan from the schedule and the grid, so each loan's own phase enters, and
# compares to the observed series **on the same loans in the same pass**.
#
# The closed form is this simulation's uniform-phase special case, so the gap
# between them is the phase effect.
# ---------------------------------------------------------------------------

#: Loan age from which Freddie reports to the cent (§5·2, measured not assumed).
CENT_FROM_AGE = 7

#: `U0_hat` is backed out from the earliest row at or after this age, §14·2:
#: that point sits before almost any extra principal.
BACKOUT_AGE = 7


#: §5·5·6. The file's age-0 balance is already some way into the schedule
#: (§5·2 measured 12.1420% of age-0 rows differ from the rounded orig). How far
#: is **not assumed**: it is swept, because origination days fall all over the
#: month and the first reported period can be a stub.
OFFSETS = (0.0, 0.25, 0.50, 0.75, 1.00)

#: §5·5·6's independent target, and its producer, named per failure mode 18:
#: results/b10_zero_upb.json, 144,761 / 1,192,244, from `--zero-upb`.
AGE0_MISMATCH_TARGET = 0.121420


def reported(u0: float, rate_pct: float, term: int, k: float,
             theta: float = 0.0) -> float:
    """What the file would print at age ``k`` if the schedule and the grid were
    the whole story. Below ``CENT_FROM_AGE`` the grid, at or above it the cent.

    ``theta`` shifts the schedule index without shifting the reporting rule: the
    grid applies to the age the file calls it, the balance is taken ``theta``
    months further along. §5·5·6."""
    i = rate_pct / 1200.0
    bal = sched_balance(u0, i, term, k + theta)
    if k < CENT_FROM_AGE:
        return round(bal / GRID_STEP) * GRID_STEP
    return round(bal, 2)


def phase_new_acc() -> dict:
    return {"hist": {"gated": {}, "all": {}},
            "obs": {"gated": {}, "all": {}},
            "sim": {a: {t: {} for t in OFFSETS} for a in ("gated", "all")},
            "age0_diff": {a: {t: 0 for t in OFFSETS} for a in ("gated", "all")},
            "age0_n": {"gated": 0, "all": 0},
            "pairs": {"gated": {}, "all": {}},
            "loans": 0, "backed_out": 0, "gated": 0}


def phase_absorb(acc: dict, recs, meta) -> None:
    """Fold one loan in. Split out so --selftest drives the same code."""
    if meta is None:
        return
    orig_upb, rate, term = meta
    acc["loans"] += 1
    rows, anchor = [], None
    for f in recs:
        try:
            upb = float(f[P_UPB])
            age = int(f[P_AGE])
            rem = int(f[P_REM])
        except (ValueError, IndexError):
            continue
        if upb <= 0:
            continue
        rows.append((age, upb))
        if anchor is None and age >= BACKOUT_AGE:
            anchor = (upb, rem)
    if anchor is None:
        return
    u0 = backout_u0(anchor[0], rate / 1200.0, anchor[1], term)
    if not (u0 == u0) or u0 <= 0:
        return
    acc["backed_out"] += 1
    gated = abs(u0 - orig_upb) <= U0_HALF_GRID
    if gated:
        acc["gated"] += 1

    arms = ("all", "gated") if gated else ("all",)
    for arm in arms:
        h = acc["hist"][arm]
        # §11 item 9: bin by distance to the nearest grid point, not by `%`.
        # A true round thousand backs out to 1000k +/- 1e-9 and `int(u0 % 1000)`
        # sends the two sides to bins 999 and 0, splitting one spike in two.
        b = int(round(u0 - round(u0 / GRID_STEP) * GRID_STEP))
        h[b] = h.get(b, 0) + 1
        acc["age0_n"][arm] += 1
        for th in OFFSETS:
            if abs(reported(u0, rate, term, 0, th) - orig_upb) >= ROUND_TOL:
                acc["age0_diff"][arm][th] += 1

    by_age = {}
    for age, upb in rows:
        if age not in by_age:
            by_age[age] = upb
    for t in GRID_AGES:
        if t not in by_age or (t - 1) not in by_age:
            continue
        obs_frozen = (by_age[t - 1] == by_age[t])
        for arm in arms:
            _bump(acc["pairs"][arm], t)
            if obs_frozen:
                _bump(acc["obs"][arm], t)
        for th in OFFSETS:
            if (reported(u0, rate, term, t - 1, th)
                    == reported(u0, rate, term, t, th)):
                for arm in arms:
                    _bump(acc["sim"][arm][th], t)


def phase_payload(acc: dict) -> dict:
    out = {"loans": acc["loans"], "backed_out": acc["backed_out"],
           "gated": acc["gated"], "by_age": {}, "phase_top": {},
           "phase_bins": {}}
    out["age0_mismatch"] = {}
    for arm in ("all", "gated"):
        rows = []
        for t in GRID_AGES:
            n = acc["pairs"][arm].get(t, 0)
            if not n:
                continue
            o = acc["obs"][arm].get(t, 0) / n
            r = {"age": t, "pairs": n, "obs": o}
            for th in OFFSETS:
                m = acc["sim"][arm][th].get(t, 0) / n
                r[f"sim@{th}"] = m
                r[f"gap@{th}"] = o - m
            rows.append(r)
        out["by_age"][arm] = rows
        n0 = max(acc["age0_n"][arm], 1)
        out["age0_mismatch"][arm] = {
            str(th): acc["age0_diff"][arm][th] / n0 for th in OFFSETS}
        h = acc["hist"][arm]
        tot = max(sum(h.values()), 1)
        out["phase_top"][arm] = [
            {"bin": b, "n": h[b], "share": h[b] / tot}
            for b in sorted(h, key=lambda k: -h[k])[:10]]
        # coarse 50-dollar bins, so the shape is readable without 1000 rows
        coarse = {}
        for b, v in h.items():
            coarse[b // 50 * 50] = coarse.get(b // 50 * 50, 0) + v
        out["phase_bins"][arm] = {str(k): coarse[k] / tot for k in sorted(coarse)}
    return out


def print_phase(pl: dict) -> None:
    print(f"\n  loans {pl['loans']:,}   backed out {pl['backed_out']:,}"
          f"   through the U0 gate {pl['gated']:,}")

    for arm in ("all", "gated"):
        print(f"\n  A[{arm}]. phase of U0_hat mod 1000, top ten $1 bins"
              f"   (uniform background per bin = 0.100%)")
        for r in pl["phase_top"][arm]:
            print(f"     bin {r['bin']:>4}   n {r['n']:>9,}   {r['share'] * 100:>8.4f}%")

    print("\n  B. phase in $50 bins, both arms, share of loans")
    print(f"     {'bin':>5}{'all':>10}{'gated':>10}")
    for k in pl["phase_bins"]["all"]:
        a = pl["phase_bins"]["all"][k] * 100
        g = pl["phase_bins"]["gated"].get(k, 0.0) * 100
        print(f"     {k:>5}{a:>9.3f}%{g:>9.3f}%")

    print(f"\n  C. §5·5·6's independent target: share of loans whose simulated"
          f" age-0 report\n     differs from orig. Measured is"
          f" {AGE0_MISMATCH_TARGET * 100:.4f}%"
          f" (results/b10_zero_upb.json, --zero-upb).")
    print(f"     {'theta':>7}{'all':>10}{'gated':>10}{'|all-target|':>14}")
    best_t = None
    for th in OFFSETS:
        a = pl["age0_mismatch"]["all"][str(th)]
        g = pl["age0_mismatch"]["gated"][str(th)]
        d = abs(a - AGE0_MISMATCH_TARGET)
        if best_t is None or d < best_t[1]:
            best_t = (th, d)
        print(f"     {th:>7.2f}{a * 100:>9.4f}%{g * 100:>9.4f}%{d * 100:>13.4f}%")
    print(f"     closest theta on the target: {best_t[0]:.2f}")

    for arm in ("all", "gated"):
        print(f"\n  D[{arm}]. obs - sim by age, one column per theta"
              f"   (main arm is 'all', §5·5·5)")
        head = "".join(f"{'@' + format(t, '.2f'):>9}" for t in OFFSETS)
        print(f"     {'age':>4}{'pairs':>12}{'obs':>9}{head}")
        for r in pl["by_age"][arm]:
            if r["age"] > 8:
                continue
            cells = "".join(f"{r[f'gap@{t}'] * 100:>+8.2f}%" for t in OFFSETS)
            print(f"     {r['age']:>4}{r['pairs']:>12,}{r['obs'] * 100:>8.2f}%{cells}")
        row1 = pl["by_age"][arm][0]
        g1 = {t: row1[f"gap@{t}"] for t in OFFSETS}
        b1 = min(g1, key=lambda t: abs(g1[t]))
        signs = {(g > 0) for g in g1.values()}
        print(f"     theta minimising |age-1 gap| on this arm: {b1:.2f}"
              f"   (gap {g1[b1] * 100:+.2f}%)")
        print(f"     age-1 gap changes sign across the sweep: {len(signs) > 1}"
              f"   (§5·5·6: branch one needs this true, or no theta closes it)")

    print("\n  Read, per the criteria fixed before the run, three branches on one variable:\n"
          "    the theta that hits 12.1420% and the theta that minimises the\n"
          "      age-1 gap are the SAME -> the alignment holds, §5·5·4's limit\n"
          "      lifts and the age-1 refinement becomes readable;\n"
          "    they are DIFFERENT -> no constant offset satisfies both; the\n"
          "      alignment story dies and age 1 has another cause. Registered,\n"
          "      and 'off by a month' may not be used to explain it again;\n"
          "    NO theta hits the target -> the age-0 report is not the schedule\n"
          "      rounded at any point. Go back to §5·2 and re-ask what the\n"
          "      12.14% is. That is more basic than this alignment question.\n"
          "    theta = 0 should read near 0% on the target by construction; a\n"
          "      sizeable share there means the back-out error is larger than\n"
          "      expected, and that is itself a reading.\n"
          "\n  And per the criteria fixed before the run, on the SIGN over ages 2-6, one variable:\n"
          "    five negative -> the balance moves more than the schedule alone\n"
          "      does; the closed form is an upper bound and that is now measured;\n"
          "    five positive -> the simulation moves too much; the principal step\n"
          "      is wrong, go back, this is not a finding;\n"
          "    mixed -> phase explained the systematic part, the rest is noise\n"
          "      and §10·9's residue closes.\n"
          "  Refinement inside whichever branch lands, not a branch of its own:\n"
          "    age 1's gap. Under the closed form it was the lone positive at\n"
          "    +3.26. If it now sits on the same side as the rest, that outlier\n"
          "    was phase; if it is still alone, it was not.\n"
          "  Both arms must agree in sign before the first branch is claimed (§5·5·4).")


def cmd_phase(only) -> int:
    vintages = only or VINTAGES
    print("§5·5: origination phase, and whether schedule + rounding is enough.\n"
          "No uniform-phase assumption. No omega. Does not transfer to Fannie.\n")
    acc = phase_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        orig, _ = read_orig(v)
        for seq, recs in loans(v):
            phase_absorb(acc, recs, orig.get(seq))
        print(f"  {v}  done   backed out so far {acc['backed_out']:,}")
    pl = phase_payload(acc)
    print_phase(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_phase.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "phase",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Counts and a schedule "
             "simulation only; no omega, no B8 prediction, no transfer to "
             "Fannie (§5·5·4).",
         **pl},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0



# ---------------------------------------------------------------------------
# --amort. Registered before the code.
#
# `--depth` already reads `arm_or_other = 0` on all 28 archives, so orig column
# 15 is the constant "FRM". A constant column has no behaviour, so C0b cannot
# earn it: all that establishes is that the column is constant.
#
# The behavioural question does not need that column at all. An ARM reprices,
# and a repricing row carries no modification flag. So: count rate changes on
# consecutive rows of one loan, split by whether the modification flag is set.
# ---------------------------------------------------------------------------

#: orig column 15's neighbours, printed together because this station has been
#: burnt twice on column identity (§25: LTV cut one column high; a distinct
#: count capped by `most_common(5)`). No cap here.
AMORT_COLS = (14, 15, 16)


def amort_new_acc() -> dict:
    return {"vals": {c: {} for c in AMORT_COLS},
            "pairs": 0, "rate_moves": 0,
            "moved_with_mod": 0, "moved_without_mod": 0,
            "mod_rows": 0, "unparsed_rate": 0, "loans": 0}


def amort_absorb_orig(acc: dict, fields) -> None:
    for c in AMORT_COLS:
        if len(fields) > c:
            v = fields[c].strip()
            acc["vals"][c][v] = acc["vals"][c].get(v, 0) + 1


def amort_absorb(acc: dict, recs) -> None:
    """Consecutive-row rate moves for one loan, split on the modification flag."""
    acc["loans"] += 1
    prev = None
    for f in recs:
        try:
            per = int(f[P_PERIOD])
            rate = float(f[P_RATE])
        except (ValueError, IndexError):
            acc["unparsed_rate"] += 1
            prev = None
            continue
        mod = f[P_MODFLAG].strip() if len(f) > P_MODFLAG else ""
        if mod:
            acc["mod_rows"] += 1
        if prev is not None:
            p0, r0, m0 = prev
            if per == next_period(p0):
                acc["pairs"] += 1
                if abs(rate - r0) >= 1e-9:
                    acc["rate_moves"] += 1
                    if mod or m0:
                        acc["moved_with_mod"] += 1
                    else:
                        acc["moved_without_mod"] += 1
        prev = (per, rate, mod)


def print_amort(acc: dict) -> None:
    print("\n  A. orig columns 14/15/16, every distinct value, no cap (§2·5·2)")
    for c in AMORT_COLS:
        vals = acc["vals"][c]
        tot = max(sum(vals.values()), 1)
        shown = sorted(vals.items(), key=lambda kv: -kv[1])
        body = ", ".join(f"{k!r}={v:,} ({v / tot * 100:.3f}%)" for k, v in shown[:8])
        print(f"     col {c}: {len(vals)} distinct   {body}"
              + ("  ..." if len(shown) > 8 else ""))
    print("     A constant column is consistent with 'this is the amortisation"
          " type and the book is\n     all fixed', and equally with 'this is not"
          " that column'. It cannot tell them apart.")

    n = max(acc["pairs"], 1)
    print("\n  B. §2·5·1: rate moves on consecutive rows, split on the mod flag")
    print(f"     consecutive pairs        {acc['pairs']:>14,}")
    print(f"     rate moved               {acc['rate_moves']:>14,}"
          f"{acc['rate_moves'] / n * 100:>12.6f}%")
    print(f"       with a mod flag        {acc['moved_with_mod']:>14,}"
          f"{acc['moved_with_mod'] / n * 100:>12.6f}%")
    print(f"       WITHOUT a mod flag     {acc['moved_without_mod']:>14,}"
          f"{acc['moved_without_mod'] / n * 100:>12.6f}%")
    print(f"     rows carrying a mod flag {acc['mod_rows']:>14,}")
    print(f"     rows whose rate would not parse {acc['unparsed_rate']:>7,}")
    if acc["rate_moves"]:
        share = acc["moved_without_mod"] / acc["rate_moves"]
        print(f"     of all rate moves, the share with no mod flag: "
              f"{share * 100:.4f}%")

    print("\n  Read, per the criteria fixed before the run, one variable, three branches:\n"
          "    the no-mod-flag share of pairs is tiny -> the book behaves as\n"
          "      fixed rate; §12 item 2 closes and no triangle ever mixed two\n"
          "      products;\n"
          "    it is sizeable -> either the sample holds ARMs or the rate moves\n"
          "      for some other reason. Either way item 2 goes live and every\n"
          "      pooled reading of this station has to be re-read on that axis;\n"
          "    the rate column will not parse -> instrument error, go back.\n"
          "  No line is drawn on the share. The denominator and the with-mod\n"
          "  comparison are printed next to it, per §2·5·1.")


def cmd_amort(only) -> int:
    vintages = only or VINTAGES
    print("§2·5: ARM against FRM, asked as behaviour rather than as a column.\n"
          "Counts only. No omega, no B8 prediction.\n")
    acc = amort_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        with zipfile.ZipFile(archive(v)) as zf:
            for f in _lines(zf, f"sample_orig_{v}.txt"):
                amort_absorb_orig(acc, f)
        for seq, recs in loans(v):
            amort_absorb(acc, recs)
        print(f"  {v}  done   pairs so far {acc['pairs']:,}")
    print_amort(acc)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_amort.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "amort",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Counts only. Establishes "
             "how the rate behaves, not what the sample's product mix is "
             "(§2·5·3).",
         "cols": {str(c): acc["vals"][c] for c in AMORT_COLS},
         **{k: v for k, v in acc.items() if k != "vals"}},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --defer. Registered before the code.
#
# §8·13·2's first row fired, so the second carrier is to be run, and §8·14·0
# lists what `V` needs in the order the dependencies force. This mode does the
# first item only: **does the zero-interest split have a basis on Freddie.**
#
# **It does not hardcode a column.** §8·14·2's variable is *how many* columns
# behave like a zero-interest balance, so the scan enumerates all 35 and prints
# every one of them (§2·5·2: this station has misread a column position twice,
# and once had a distinct count silently capped at five).
#
# The two signatures are borrowed from §7·12's O24 ruling, which earned them on
# Fannie. **What travels is the question, not the answer.**
# ---------------------------------------------------------------------------

#: §2·1's col 25, zero-indexed. Used only for §8·14·3's cross-check, which is a
#: shape written down before the run, never a branch.
P_PAY_DEFER = 24

#: Distinct values are counted exactly until this many, then the set is dropped
#: and the count is printed as "> N". **The cap is printed, never silent**
#: (§10·9·9's "no silent caps", and §2·5·2's capped-at-five counter).
DISTINCT_CAP = 5000

#: A rising edge needs a previous row. Periods must be consecutive, same as
#: every other pair-based reading in this file (§2·5·0's denominator).
DEFER_TOP_PERIODS = 5


def _num(tok: str):
    """A float, or None. Blank is None, not zero: they are different facts."""
    t = tok.strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def defer_new_acc() -> dict:
    return {
        "cols": {c: {"rows": 0, "nonblank": 0, "numeric": 0, "positive": 0,
                     "zero": 0, "distinct": set(), "distinct_capped": False}
                 for c in range(PERF_FIELDS)},
        "edges": {c: {"n": 0, "with_mod": 0, "with_pay_defer": 0,
                      "periods": {}, "vintages": {},
                      "upb_step": [], "amount": []}
                  for c in range(PERF_FIELDS)},
        "rows": 0, "loans": 0, "short_fields": 0, "gap_pairs": 0,
    }


def defer_absorb(acc: dict, recs, vintage: int) -> None:
    """One loan. Per column: the shape counters, and the rising edges.

    A rising edge is `not positive` -> `positive` on **consecutive periods**.
    Blank and 0.00 are both `not positive` on the left, and they are counted
    apart in the shape table so the difference stays visible.
    """
    acc["loans"] += 1
    prev_vals = [None] * PERF_FIELDS
    prev_period = None
    prev_upb = None
    for f in recs:
        acc["rows"] += 1
        if len(f) < PERF_FIELDS:
            acc["short_fields"] += 1
        try:
            per = int(f[P_PERIOD])
        except (ValueError, IndexError):
            prev_period, prev_vals = None, [None] * PERF_FIELDS
            continue
        mod = f[P_MODFLAG].strip() if len(f) > P_MODFLAG else ""
        pdf = f[P_PAY_DEFER].strip() if len(f) > P_PAY_DEFER else ""
        upb_now = _num(f[P_UPB]) if len(f) > P_UPB else None
        consecutive = prev_period is not None and per == next_period(prev_period)
        if prev_period is not None and not consecutive:
            acc["gap_pairs"] += 1

        for c in range(PERF_FIELDS):
            tok = f[c] if len(f) > c else ""
            d = acc["cols"][c]
            d["rows"] += 1
            t = tok.strip()
            if t:
                d["nonblank"] += 1
            v = _num(tok)
            if v is not None:
                d["numeric"] += 1
                if v > 0:
                    d["positive"] += 1
                elif v == 0:
                    d["zero"] += 1
            if not d["distinct_capped"]:
                d["distinct"].add(t)
                if len(d["distinct"]) > DISTINCT_CAP:
                    d["distinct_capped"] = True
                    d["distinct"] = set()

            if consecutive and v is not None and v > 0:
                pv = prev_vals[c]
                if pv is None or pv <= 0:
                    e = acc["edges"][c]
                    e["n"] += 1
                    if mod:
                        e["with_mod"] += 1
                    if pdf:
                        e["with_pay_defer"] += 1
                    e["periods"][per] = e["periods"].get(per, 0) + 1
                    e["vintages"][vintage] = e["vintages"].get(vintage, 0) + 1
                    if len(e["amount"]) < 200_000:
                        e["amount"].append(v)
                        e["upb_step"].append(
                            (upb_now - prev_upb)
                            if (upb_now is not None and prev_upb is not None)
                            else float("nan"))
            prev_vals[c] = v
        prev_period, prev_upb = per, upb_now


def _med(xs):
    ys = sorted(x for x in xs if x == x)
    return float(ys[len(ys) // 2]) if ys else float("nan")


def defer_payload(acc: dict) -> dict:
    cols = {}
    for c, d in acc["cols"].items():
        cols[str(c)] = {
            "col_1indexed": c + 1,
            "rows": d["rows"], "nonblank": d["nonblank"],
            "numeric": d["numeric"], "positive": d["positive"],
            "zero": d["zero"],
            "distinct": (None if d["distinct_capped"] else len(d["distinct"])),
            "distinct_capped_at": DISTINCT_CAP if d["distinct_capped"] else None,
        }
    edges = {}
    for c, e in acc["edges"].items():
        if not e["n"]:
            continue
        tot = e["n"]
        per = sorted(e["periods"].items(), key=lambda kv: -kv[1])
        edges[str(c)] = {
            "col_1indexed": c + 1, "n": tot,
            "share_with_mod_flag": e["with_mod"] / tot,
            "share_with_pay_deferral_flag": e["with_pay_defer"] / tot,
            "top_periods": [{"period": k, "n": v, "share": v / tot}
                            for k, v in per[:DEFER_TOP_PERIODS]],
            "distinct_periods": len(e["periods"]),
            "share_in_top_period": (per[0][1] / tot) if per else None,
            "vintages_with_an_edge": len(e["vintages"]),
            "median_amount": _med(e["amount"]),
            "median_upb_step_at_edge": _med(e["upb_step"]),
            "amount_sampled": len(e["amount"]),
        }
    return {"cols": cols, "edges": edges,
            "rows": acc["rows"], "loans": acc["loans"],
            "short_fields": acc["short_fields"], "gap_pairs": acc["gap_pairs"]}


def print_defer(pl: dict) -> None:
    print("\n  A. every perf column, shape counters, nothing capped silently")
    print(f"     {'col':>4}{'rows':>13}{'nonblank':>12}{'numeric':>12}"
          f"{'positive':>11}{'zero':>13}{'distinct':>10}")
    for k in sorted(pl["cols"], key=int):
        d = pl["cols"][k]
        dist = ("> {:,}".format(d["distinct_capped_at"])
                if d["distinct"] is None else f"{d['distinct']:,}")
        print(f"     {d['col_1indexed']:>4}{d['rows']:>13,}{d['nonblank']:>12,}"
              f"{d['numeric']:>12,}{d['positive']:>11,}{d['zero']:>13,}"
              f"{dist:>10}")
    print("     col is 1-indexed, matching the published field enumeration.")
    print("     Reading, written before the run (§8·14·1): a zero-interest")
    print("     balance is mostly zero or blank, positive on a minority, and")
    print("     takes many distinct values where positive. A flag takes few")
    print("     distinct values. An identifier or a rate is set on every row.")
    print("     Sharpened before the run, because two columns can share the")
    print("     'mostly zero, sometimes positive' shape without being the same")
    print("     kind of thing: the delinquency counter does too. What separates")
    print("     them is already in these two tables. A currency amount runs")
    print(f"     past the {DISTINCT_CAP:,} distinct cap and shows a rising-edge")
    print("     median in the thousands; a counter takes about a hundred")
    print("     distinct values and steps by one.")

    print("\n  B. rising edges (not-positive -> positive on consecutive"
          " periods), per column")
    if not pl["edges"]:
        print("     none. No column in this file ever goes from zero to")
        print("     positive, so §8·14·2 has nothing to read. Report and stop.")
        return
    print(f"     {'col':>4}{'edges':>10}{'w/ mod flag':>13}{'w/ pay-def':>12}"
          f"{'periods':>9}{'top period':>12}{'vintages':>10}"
          f"{'med amount':>13}{'med UPB step':>14}")
    for k in sorted(pl["edges"], key=int):
        e = pl["edges"][k]
        print(f"     {e['col_1indexed']:>4}{e['n']:>10,}"
              f"{e['share_with_mod_flag']:>13.4f}"
              f"{e['share_with_pay_deferral_flag']:>12.4f}"
              f"{e['distinct_periods']:>9,}{e['share_in_top_period']:>12.4f}"
              f"{e['vintages_with_an_edge']:>10}"
              f"{e['median_amount']:>13,.2f}"
              f"{e['median_upb_step_at_edge']:>14,.2f}")

    print("\n  C. §8·14·1's two signatures, borrowed from §7·12's O24 ruling")
    print("     signature 1, 'deferred principal from a modification':")
    print("       the edge sits on a modification month. Fannie's field 63")
    print("       reads 0.996 to 1.000 there.")
    print("     signature 2, 'payment deferral':")
    print("       the edges pile into one calendar window and do not depend on")
    print("       vintage. Read `top period` and `periods` together: a large")
    print("       share in few periods across many vintages is signature 2.")
    print("     Neither is a line on a number. Both are shapes, and §8·14·2")
    print("     branches on which one a column shows, not on how large it is.")

    print("\n  D. §8·14·3's cross-check, a shape written down before the run")
    print("     Freddie's col 25 is a Payment Deferral flag, not a balance. If")
    print("     a column's edges coincide with that flag, that column is the")
    print("     deferral balance. Both sides are in this run on the same rows,")
    print("     so this is a same-population comparison (失效模式 18).")
    print("     It is a shape, not a branch.")

    print("\n  E. coverage")
    print(f"     rows {pl['rows']:,}   loans {pl['loans']:,}"
          f"   rows short of {PERF_FIELDS} fields {pl['short_fields']:,}"
          f"   non-consecutive pairs {pl['gap_pairs']:,}")
    print("     §8·14·2's verdict is not drawn here. It needs the shape of")
    print("     table A read against the reading printed under it, and this")
    print("     file does not draw it, because 'behaves like a balance' is a")
    print("     shape, and a line must not be drawn on an estimator.")


def cmd_defer(only) -> int:
    vintages = only or VINTAGES
    print("§8·14: does the zero-interest split have a basis on Freddie.\n"
          "Enumeration and edges only. No omega, no column assumed.\n")
    acc = defer_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        for seq, recs in loans(v):
            defer_absorb(acc, recs, v)
        print(f"  {v}  done   rows so far {acc['rows']:,}", flush=True)
    pl = defer_payload(acc)
    print_defer(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_defer.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "defer",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Enumeration and rising "
             "edges only; assumes no column identity (C0b). Decides only "
             "whether V's zero-interest split has a basis, not any omega.",
         "distinct_cap": DISTINCT_CAP,
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --defer2. Registered before the code.
#
# `--defer` landed §8·14·2's fourth branch and the landing could not be
# executed: the branch was chosen by a count and the landing needed the
# identities of the things counted (MEASUREMENT.md 失效模式 20). The defect was
# one word in the reading, "mostly zero **or blank**", which folds together two
# structurally opposite absences: "reported, and it is zero" and "not reported".
#
# This mode does not re-decide §8·14's landing. It runs §8·14·5's corrected
# reading, which is a conjunction of three structural facts plus the sharpening
# that was already registered, and it **prints the names, not the count**.
#
# It reads `b10_defer.json` for the column shapes, then makes ONE targeted pass
# for the calendar rollup of the columns that pass. `--defer` and
# `results/b10_defer.json` are not touched, so §8·14's landing keeps its
# producer (規矩 19 holds by construction, and the comparison is still to be
# run).
# ---------------------------------------------------------------------------

#: §8·14·5·1b. Fannie's field 63 reads 0.996 to 1.000 on the modification
#: month (§7·12), so signature one is written at that magnitude. **Not a line
#: drawn this round**: it is the number §7·12 measured.
SIG1_MOD_SHARE = 0.99

#: Signature two's flag half. §8·14·3's shape says "the same month", not
#: "sometimes the same month", so it is a plurality.
SIG2_FLAG_SHARE = 0.50

#: The registered sharpening from §8·14·2: a currency amount runs past the
#: distinct cap and its rising-edge median is in the thousands. Kept because it
#: is what separates a balance from the delinquency counter, which also reads
#: "mostly zero, positive on a minority".
SIG_AMOUNT_ORDER = 1000.0


def defer2_select(pl: dict) -> dict:
    """§8·14·5's reading, per column, with every condition's verdict kept.

    Returns one record per column. **The identities travel, not just the
    count** — that is the whole point of 失效模式 20's first 处置.
    """
    out = {}
    for k, c in pl["cols"].items():
        blank = c["rows"] - c["nonblank"]
        neg = c["numeric"] - c["positive"] - c["zero"]
        e = pl["edges"].get(k)
        med = e["median_amount"] if e else float("nan")
        conds = {
            "never_blank": blank == 0,
            "never_negative": neg == 0,
            "zero_is_the_majority": c["zero"] > c["rows"] / 2,
            "positive_is_a_minority": 0 < c["positive"] < c["rows"] / 2,
            "distinct_past_the_cap": c["distinct"] is None,
            "edge_median_in_the_thousands": bool(med >= SIG_AMOUNT_ORDER),
        }
        out[k] = {"col_1indexed": c["col_1indexed"], "blank": blank,
                  "zero": c["zero"], "positive": c["positive"],
                  "negative": neg,
                  "distinct": c["distinct"],
                  "edge_median": med, "edges": (e["n"] if e else 0),
                  "conds": conds, "passes": all(conds.values()),
                  "first_failed": next((n for n, v in conds.items() if not v),
                                       None)}
    return out


def defer2_new_acc(cols) -> dict:
    return {"cols": list(cols),
            "years": {c: {} for c in cols},
            "year_vintages": {c: {} for c in cols},
            "edges": {c: 0 for c in cols},
            "with_mod": {c: 0 for c in cols},
            "with_flag": {c: 0 for c in cols},
            "vintages": {c: set() for c in cols},
            "rows": 0, "loans": 0}


def defer2_absorb(acc: dict, recs, vintage: int) -> None:
    """Same rising-edge definition as `--defer`, restricted to the passing cols.

    Same definition on purpose: the two runs then share a population by
    construction, which is 失效模式 18's second condition.
    """
    acc["loans"] += 1
    prev = {c: None for c in acc["cols"]}
    prev_period = None
    for f in recs:
        acc["rows"] += 1
        try:
            per = int(f[P_PERIOD])
        except (ValueError, IndexError):
            prev_period, prev = None, {c: None for c in acc["cols"]}
            continue
        mod = f[P_MODFLAG].strip() if len(f) > P_MODFLAG else ""
        pdf = f[P_PAY_DEFER].strip() if len(f) > P_PAY_DEFER else ""
        consecutive = prev_period is not None and per == next_period(prev_period)
        for c in acc["cols"]:
            v = _num(f[c]) if len(f) > c else None
            if consecutive and v is not None and v > 0:
                pv = prev[c]
                if pv is None or pv <= 0:
                    yr = per // 100
                    acc["edges"][c] += 1
                    acc["years"][c][yr] = acc["years"][c].get(yr, 0) + 1
                    acc["year_vintages"][c].setdefault(yr, set()).add(vintage)
                    acc["vintages"][c].add(vintage)
                    if mod:
                        acc["with_mod"][c] += 1
                    if pdf:
                        acc["with_flag"][c] += 1
            prev[c] = v
        prev_period = per


def defer2_signature(rec: dict) -> tuple[str, dict]:
    """§8·14·5·1b, applied. Returns (name, the four facts it was read from)."""
    n = max(rec["edges"], 1)
    mod = rec["with_mod"] / n
    flag = rec["with_flag"] / n
    years = rec["years"]
    top_year = max(years, key=lambda y: years[y]) if years else None
    others = [v for y, v in years.items() if y != top_year]
    plurality = bool(years) and (not others or years[top_year] > max(others))
    vin_top = len(rec["year_vintages"].get(top_year, ()))
    vin_all = max(len(rec["vintages"]), 1)
    vin_majority = vin_top > vin_all / 2
    facts = {"share_with_mod_flag": mod, "share_with_pay_deferral_flag": flag,
             "top_year": top_year, "top_year_edges": years.get(top_year, 0),
             "top_year_is_a_plurality": plurality,
             "vintages_in_top_year": vin_top, "vintages_with_an_edge": vin_all,
             "top_year_spans_most_vintages": vin_majority}
    if mod >= SIG1_MOD_SHARE:
        return "signature 1 (deferred principal from a modification)", facts
    if flag > SIG2_FLAG_SHARE and plurality and vin_majority:
        return "signature 2 (payment deferral)", facts
    return "neither signature", facts


def defer2_payload(sel: dict, acc, passing) -> dict:
    recs = {}
    for c in passing:
        r = {"col_1indexed": c + 1,
             "edges": acc["edges"][c],
             "with_mod": acc["with_mod"][c],
             "with_flag": acc["with_flag"][c],
             "years": dict(sorted(acc["years"][c].items())),
             "year_vintages": {y: sorted(v)
                               for y, v in sorted(acc["year_vintages"][c].items())},
             "vintages": sorted(acc["vintages"][c])}
        name, facts = defer2_signature(
            {**r, "years": acc["years"][c],
             "year_vintages": acc["year_vintages"][c],
             "vintages": acc["vintages"][c]})
        r["signature"] = name
        r["signature_facts"] = {k: (sorted(v) if isinstance(v, set) else v)
                                for k, v in facts.items()}
        recs[str(c)] = r
    return {"reading": sel, "passing": [c + 1 for c in passing],
            "detail": recs, "rows": acc["rows"], "loans": acc["loans"]}


def print_defer2(pl: dict) -> None:
    sel = pl["reading"]
    print("\n  A. §8·14·5's reading, every column, and which条件 it fails first")
    print(f"     {'col':>4}{'blank':>13}{'zero':>13}{'positive':>11}"
          f"{'negative':>10}{'distinct':>10}{'edge med':>13}  first failed")
    for k in sorted(sel, key=int):
        r = sel[k]
        dist = "> cap" if r["distinct"] is None else f"{r['distinct']:,}"
        med = "-" if r["edge_median"] != r["edge_median"] else f"{r['edge_median']:,.2f}"
        why = "PASSES" if r["passes"] else r["first_failed"]
        print(f"     {r['col_1indexed']:>4}{r['blank']:>13,}{r['zero']:>13,}"
              f"{r['positive']:>11,}{r['negative']:>10,}{dist:>10}{med:>13}"
              f"  {why}")
    print("     条件, in order: never blank; never negative; zero is the")
    print("     majority; positive is a minority; distinct past the cap;")
    print("     rising-edge median in the thousands. The first three are what")
    print("     `--defer`'s reading folded into one 'mostly zero or blank'.")

    print(f"\n     columns that pass: {pl['passing'] or 'none'}"
          f"   count {len(pl['passing'])}")
    print("     **Named, not counted** (失效模式 20 处置一).")

    if pl["passing"]:
        print("\n  B. §8·14·5·1b's signature facts, per passing column")
        for k in sorted(pl["detail"], key=int):
            d = pl["detail"][k]
            f = d["signature_facts"]
            print(f"\n     col {d['col_1indexed']}   edges {d['edges']:,}")
            print(f"       with mod flag            {f['share_with_mod_flag']:.4f}"
                  f"   (signature 1 wants >= {SIG1_MOD_SHARE})")
            print(f"       with col 25 flag         "
                  f"{f['share_with_pay_deferral_flag']:.4f}"
                  f"   (signature 2 wants > {SIG2_FLAG_SHARE})")
            print(f"       top calendar year        {f['top_year']}"
                  f"  {f['top_year_edges']:,} edges"
                  f"   plurality {f['top_year_is_a_plurality']}")
            print(f"       vintages in that year    {f['vintages_in_top_year']}"
                  f" of {f['vintages_with_an_edge']}"
                  f"   majority {f['top_year_spans_most_vintages']}")
            ys = d["years"]
            tot = max(sum(ys.values()), 1)
            row = "  ".join(f"{y}:{v / tot * 100:.1f}%" for y, v in
                            sorted(ys.items(), key=lambda kv: -kv[1])[:8])
            print(f"       year shares (top 8)      {row}")
            print(f"       -> {d['signature']}")

    print("\n  C. Read, per the criteria fixed before the run, four branches")
    n = len(pl["passing"])
    if n == 0:
        print("     No column passes. The zero-interest split has no basis on")
        print("     this carrier, and that is not one of the four branches as")
        print("     registered: all four assume at least one. Per R01 未命中")
        print("     归「混合」, report and read nothing; the third branch's")
        print("     处置 (stop, do not name anything, go back to §2·1) is the")
        print("     nearest and is what this run buys.")
        return
    if n == 1:
        d = pl["detail"][str(pl["passing"][0] - 1)]
        sig = d["signature"]
        print(f"     Exactly one column: col {d['col_1indexed']}, {sig}.")
        if sig.startswith("signature 2"):
            print("     FIRST BRANCH. It is Fannie 108's counterpart. Fannie 63")
            print("     has no independent column here, so the interest-bearing")
            print("     balance is `col 3 - this column`, and **C13's")
            print("     double-carrier exclusion cannot be written on Freddie:")
            print("     `bad_c13` is identically false**. That travels with")
            print("     every Freddie omega.")
        elif sig.startswith("signature 1"):
            print("     SECOND BRANCH. It is Fannie 63's counterpart, and 108's")
            print("     has no independent column. Same consequence for C13.")
        else:
            print("     THIRD BRANCH. Neither signature. The zero-interest split")
            print("     has no basis. Stop; do not name it; back to §2·1.")
        return
    print(f"     {n} columns pass: {pl['passing']}")
    print("     FOURTH BRANCH. C13's counterpart exists. Exclude the loans that")
    print("     carry more than one, and print how many were excluded. **The")
    print("     identities are printed above**, so unlike §8·14·1's landing")
    print("     this one can actually be executed.")


def cmd_defer2(only) -> int:
    src = RESULTS / "b10_defer.json"
    if not src.exists():
        print(f"  {src.relative_to(ROOT)} is not on disk. Run --defer first.")
        return 1
    pl0 = json.loads(src.read_text(encoding="utf-8"))
    print("§8·14·5: the reading with the 'or' taken out, applied to --defer's\n"
          "own artefact, then one targeted pass for the calendar rollup.\n")
    sel = defer2_select(pl0)
    passing = [int(k) for k in sorted(sel, key=int) if sel[k]["passes"]]
    print(f"  columns passing §8·14·5's reading: "
          f"{[c + 1 for c in passing] or 'none'}")

    acc = defer2_new_acc(passing)
    if passing:
        vintages = only or VINTAGES
        for v in vintages:
            if not archive(v).exists():
                print(f"  {v}  missing")
                continue
            for seq, recs in loans(v):
                defer2_absorb(acc, recs, v)
            print(f"  {v}  done   rows so far {acc['rows']:,}", flush=True)
    else:
        print("  nothing to scan for.")
    pl = defer2_payload(sel, acc, passing)
    print_defer2(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_defer2.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "defer2", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Does not re-decide "
             "§8·14's landing; runs the corrected reading and prints the names. "
             "Reads results/b10_defer.json for the shapes, then one targeted "
             "pass for the calendar rollup. --defer is untouched.",
         "sig1_mod_share": SIG1_MOD_SHARE,
         "sig2_flag_share": SIG2_FLAG_SHARE,
         "sig_amount_order": SIG_AMOUNT_ORDER,
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --balloon. Registered before the code.
#
# §8·14·5 landed the first branch, so the deferral column is fixed and the
# balloon question finally has a domain: Fannie's `bad_bn` is
# `(zib > 0) & ~isfinite(bn)`, so the horizon is only ever demanded where the
# zero-interest balance is positive.
#
# Fannie builds the horizon two ways and asserts they agree exactly. Freddie's
# `rem_legal` is already earned; what is missing is the maturity path, which is
# the cross-check itself. The anchor for the maturity column uses the ALREADY
# EARNED term column, never `rem_legal`, so it does not close a loop.
# ---------------------------------------------------------------------------

#: The column that §8·14·5 landed on, zero-indexed. Written down rather than
#: rediscovered, because rediscovering it here would be a second opinion on a
#: settled reading.
P_DEFER_BAL = 11

#: §8·14·6·1's appearance narrowing. **Only narrows the candidate set**; the
#: pick is by behaviour. Printed, never silent.
YYYYMM_LO, YYYYMM_HI = 190001, 219912

#: How wide a window of `monthdiff - term` to keep per column. Outside it the
#: rows go into one overflow bucket that is printed, so nothing is dropped.
#: **Wide enough that a column which merely spreads still spreads visibly.** At
#: 24 the fixture's first-payment column put -359 and -179 into a single
#: overflow bucket, and a lump is not a spread: the printed table then said
#: "one bucket" about a column that has as many buckets as the book has terms.
#: 480 months is forty years, past any horizon this data carries.
ANCHOR_SPAN = 480


def monthdiff(a: int, b: int) -> int:
    """Months from YYYYMM `b` to YYYYMM `a`. Not `a - b`: 200101 - 200012 = 89."""
    return (a // 100 - b // 100) * 12 + (a % 100 - b % 100)


def _yyyymm(tok: str):
    t = tok.strip()
    if not t.isdigit():
        return None
    v = int(t)
    if not (YYYYMM_LO <= v <= YYYYMM_HI):
        return None
    if not (1 <= v % 100 <= 12):
        return None
    return v


def balloon_new_acc() -> dict:
    return {"anchor": {c: {} for c in range(ORIG_FIELDS)},
            "anchor_n": {c: 0 for c in range(ORIG_FIELDS)},
            "yyyymm_rows": {c: 0 for c in range(ORIG_FIELDS)},
            "cmp": {c: {} for c in range(ORIG_FIELDS)},
            "cmp_n": {c: 0 for c in range(ORIG_FIELDS)},
            "orig_loans": 0, "loans": 0, "rows": 0,
            "defer_rows": 0, "defer_rows_rem_ok": 0,
            "defer_rows_no_rem": 0, "defer_rows_no_period": 0,
            "loans_no_orig": 0, "loans_no_term": 0}


def balloon_absorb(acc: dict, recs, orig_fields) -> None:
    """One loan. The maturity anchor, and the two-way horizon on deferral rows.

    `orig_fields` is the raw orig row for this loan, or None. **Both halves are
    accumulated for every column that even looks like a YYYYMM**, because which
    column is the maturity one is decided by §8·14·6·1 after the scan, not here.
    """
    acc["loans"] += 1
    acc["rows"] += len(recs)
    if orig_fields is None:
        acc["loans_no_orig"] += 1
        return
    try:
        term = int(orig_fields[O_TERM])
    except (ValueError, IndexError):
        acc["loans_no_term"] += 1
        return

    cand = {}
    for c in range(ORIG_FIELDS):
        v = _yyyymm(orig_fields[c]) if len(orig_fields) > c else None
        if v is not None:
            cand[c] = v
            acc["yyyymm_rows"][c] += 1

    first = None
    for f in recs:
        try:
            per = int(f[P_PERIOD])
        except (ValueError, IndexError):
            continue
        if first is None:
            first = per
        d = _num(f[P_DEFER_BAL]) if len(f) > P_DEFER_BAL else None
        if d is None or d <= 0:
            continue
        acc["defer_rows"] += 1
        try:
            rem = int(f[P_REM])
        except (ValueError, IndexError):
            acc["defer_rows_no_rem"] += 1
            continue
        acc["defer_rows_rem_ok"] += 1
        for c, v in cand.items():
            diff = monthdiff(v, per) - rem
            key = diff if -ANCHOR_SPAN <= diff <= ANCHOR_SPAN else "out"
            acc["cmp"][c][key] = acc["cmp"][c].get(key, 0) + 1
            acc["cmp_n"][c] += 1

    if first is None:
        return
    for c, v in cand.items():
        diff = monthdiff(v, first) - term
        key = diff if -ANCHOR_SPAN <= diff <= ANCHOR_SPAN else "out"
        acc["anchor"][c][key] = acc["anchor"][c].get(key, 0) + 1
        acc["anchor_n"][c] += 1


def _mode(h: dict):
    """(key, count, share) of the busiest **integer** bucket, or None.

    **`"out"` is excluded from the contest, and the share is still taken over
    the whole table including it.** The overflow bucket is not a value: it is
    "did not land in any of them". Letting it win the mode makes a column that
    spreads over dozens of offsets read as though it pressed onto one, which is
    exactly what it did on the first draft of this file's selftest — the
    fixture's first-payment column scattered to -359 and -179, both fell into
    `"out"`, and its top share read 1.0000. Same family as the rule that
    `unparsable` may not merge `RA` with blank (§11).
    """
    ints = {k: v for k, v in h.items() if not isinstance(k, str)}
    if not ints:
        return None
    k = max(ints, key=lambda x: ints[x])
    n = sum(h.values())
    return k, ints[k], ints[k] / n


def balloon_payload(acc: dict) -> dict:
    cols = {}
    for c in range(ORIG_FIELDS):
        if not acc["anchor_n"][c] and not acc["yyyymm_rows"][c]:
            continue
        m = _mode(acc["anchor"][c])
        mc = _mode(acc["cmp"][c])
        a_out = acc["anchor"][c].get("out", 0)
        c_out = acc["cmp"][c].get("out", 0)
        cols[str(c)] = {
            "col_1indexed": c + 1,
            "yyyymm_rows": acc["yyyymm_rows"][c],
            "anchor_n": acc["anchor_n"][c],
            "anchor_top": (None if m is None else
                           {"offset": m[0], "n": m[1], "share": m[2]}),
            "anchor_out": a_out,
            "anchor_hist": {str(k): v for k, v in
                            sorted(acc["anchor"][c].items(),
                                   key=lambda kv: -kv[1])[:8]},
            "cmp_n": acc["cmp_n"][c],
            "cmp_top": (None if mc is None else
                        {"offset": mc[0], "n": mc[1], "share": mc[2]}),
            "cmp_out": c_out,
            "cmp_hist": {str(k): v for k, v in
                         sorted(acc["cmp"][c].items(),
                                key=lambda kv: -kv[1])[:8]},
        }
    return {"cols": cols,
            **{k: acc[k] for k in
               ("orig_loans", "loans", "rows", "defer_rows",
                "defer_rows_rem_ok", "defer_rows_no_rem",
                "loans_no_orig", "loans_no_term")}}


def print_balloon(pl: dict) -> None:
    print("\n  A. §8·14·6·1: every orig column that ever looks like a YYYYMM")
    print(f"     window {YYYYMM_LO}..{YYYYMM_HI}, month 01..12. "
          f"**Narrows the candidates, picks nothing.**")
    print(f"     {'col':>4}{'YYYYMM rows':>13}{'anchored':>11}"
          f"{'top offset':>12}{'its share':>11}{'beyond span':>13}"
          f"   next buckets")
    for k in sorted(pl["cols"], key=int):
        d = pl["cols"][k]
        t = d["anchor_top"]
        rest = "  ".join(f"{kk}:{vv:,}" for kk, vv in
                         list(d["anchor_hist"].items())[1:4])
        if t is None:
            print(f"     {d['col_1indexed']:>4}{d['yyyymm_rows']:>13,}"
                  f"{d['anchor_n']:>11,}{'none':>12}{'-':>11}"
                  f"{d['anchor_out']:>13,}   {rest}")
            continue
        print(f"     {d['col_1indexed']:>4}{d['yyyymm_rows']:>13,}"
              f"{d['anchor_n']:>11,}{str(t['offset']):>12}{t['share']:>11.5f}"
              f"{d['anchor_out']:>13,}   {rest}")
    print(f"     `beyond span` is the overflow past +-{ANCHOR_SPAN} months. It is")
    print("     **not eligible to be the top bucket**: it is not an offset, it")
    print("     is 'landed in none of them', and letting it win would make a")
    print("     scattered column read as a pressed one.")
    print("     Reading, written before the run: a maturity column presses the")
    print("     whole of `monthdiff(col, first period) - term` onto ONE integer.")
    print("     Anything else spreads. The two differ by orders of magnitude,")
    print("     not by a notch, so there is no line here.")
    print("     The anchor uses the term column, which §8·13·1 records as")
    print("     already earned at 99.924%, and never `rem_legal`, so it does")
    print("     not close a loop with the thing being tested.")

    print("\n  B. §8·14·6·2: the two paths on the deferral rows")
    print(f"     deferral rows seen {pl['defer_rows']:,}"
          f"   with a readable rem_legal {pl['defer_rows_rem_ok']:,}"
          f"   without {pl['defer_rows_no_rem']:,}")
    print(f"     {'col':>4}{'compared':>12}{'top offset':>12}{'its share':>11}"
          f"{'disagreeing':>13}   next buckets")
    for k in sorted(pl["cols"], key=int):
        d = pl["cols"][k]
        t = d["cmp_top"]
        if t is None or not d["cmp_n"]:
            continue
        rest = "  ".join(f"{kk}:{vv:,}" for kk, vv in
                         list(d["cmp_hist"].items())[1:4])
        print(f"     {d['col_1indexed']:>4}{d['cmp_n']:>12,}"
              f"{str(t['offset']):>12}{t['share']:>11.5f}"
              f"{d['cmp_n'] - t['n']:>13,}   {rest}")
    print("     `disagreeing` counts the rows outside the busiest bucket,")
    print(f"     **including everything beyond +-{ANCHOR_SPAN} months**.")
    print("     §14.1 says the two paths agree **exactly**, and b8_omega's own")
    print("     comment says a non-zero disagree is news about the file and not")
    print("     a tolerance to widen. So a non-zero here is the second branch.")

    print("\n  C. Read, per the criteria fixed before the run")
    #: §8·14·6·1's operational form, registered before this was written: the
    #: top bucket holds more loans than every other bucket put together. **A
    #: comparison, not a notch** — a real maturity column reads above 0.99 and
    #: an unrelated YYYYMM column spreads over dozens of buckets, so this test
    #: lands in the gap between them rather than beside either.
    pressed = [pl["cols"][k] for k in sorted(pl["cols"], key=int)
               if pl["cols"][k]["anchor_top"]
               and pl["cols"][k]["anchor_top"]["share"] > 0.5]
    print(f"     columns whose anchor presses onto one integer: "
          f"{[d['col_1indexed'] for d in pressed] or 'none'}")
    print("     (listed by name, not counted — 失效模式 20 处置一)")
    if not pressed:
        print("     §8·14·6·1 SECOND BRANCH: no maturity path exists. Then")
        print("     §8·14·6·2's THIRD BRANCH: the criterion has no referent,")
        print("     `balloon_horizon` on Freddie is a single uncrossed path,")
        print("     and it must never be written up as 'checked'.")
        return
    if len(pressed) > 1:
        print("     §8·14·6·1 THIRD BRANCH: more than one column presses.")
        print("     Print whether they agree with each other row for row before")
        print("     going on; this run does not go on.")
        return
    d = pressed[0]
    t, mc = d["anchor_top"], d["cmp_top"]
    print(f"     §8·14·6·1 FIRST BRANCH: col {d['col_1indexed']} is the maturity")
    print(f"     column, at offset {t['offset']} on {t['share']:.5f} of loans.")
    if mc is None or not d["cmp_n"]:
        print("     But it never meets a deferral row, so §8·14·6·2 has no")
        print("     referent either. Report the coverage and stop.")
        return
    bad = d["cmp_n"] - mc["n"]
    if bad == 0:
        print(f"     §8·14·6·2 FIRST BRANCH: the two paths agree on every one of")
        print(f"     the {d['cmp_n']:,} deferral rows, at offset {mc['offset']}.")
        print("     `balloon_horizon` carries over from Fannie as written.")
    else:
        print(f"     §8·14·6·2 SECOND BRANCH: {bad:,} of {d['cmp_n']:,} deferral")
        print(f"     rows disagree ({bad / d['cmp_n'] * 100:.4f}%). §14.1's")
        print("     'exactly' does not hold here. Report the shape of the")
        print("     difference; do not fix `bn` until it is settled.")
    print("\n     加细, inside whichever branch landed, not a branch itself:")
    print(f"       deferral rows with no readable rem_legal "
          f"{pl['defer_rows_no_rem']:,}"
          f"  ({pl['defer_rows_no_rem'] / max(pl['defer_rows'], 1) * 100:.4f}%)")
    print("       that is `bad_bn`'s population, and its size travels with any")
    print("       Freddie omega.")


def cmd_balloon(only) -> int:
    vintages = only or VINTAGES
    print("§8·14·6: the balloon horizon, and the cross-check Fannie has and\n"
          "Freddie has not been shown to have. No omega.\n")
    acc = balloon_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        raw = {}
        with zipfile.ZipFile(archive(v)) as zf:
            for f in _lines(zf, f"sample_orig_{v}.txt"):
                if len(f) > O_SEQ:
                    raw[f[O_SEQ]] = f
        acc["orig_loans"] += len(raw)
        for seq, recs in loans(v):
            balloon_absorb(acc, recs, raw.get(seq))
        print(f"  {v}  done   deferral rows so far {acc['defer_rows']:,}",
              flush=True)
    pl = balloon_payload(acc)
    print_balloon(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_balloon.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "balloon", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Enumerates the orig "
             "columns that look like a YYYYMM, anchors on the already-earned "
             "term column, and compares the two horizon paths on the deferral "
             "rows §8·14·5 defined. No omega.",
         "defer_column_1indexed": P_DEFER_BAL + 1,
         "yyyymm_window": [YYYYMM_LO, YYYYMM_HI],
         "anchor_span": ANCHOR_SPAN,
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --balloon2. Registered before the code
# written.
#
# `--balloon` landed §8·14·6·1's third branch: two columns pressed, 0.66615 and
# 0.87483. The reading was not loose; the assumption behind it was. It said an
# unrelated YYYYMM column "spreads over dozens of buckets, its top bucket does
# not reach ten per cent", and the top bucket read 66.6% because 72% of this
# book is thirty-year. **Spreading depends on the diversity of a third
# variable, and that variable is not diverse.**
#
# The fix restores the question the anchor was always asking: is the offset
# invariant to the term. Pooled, the invariance is invisible. Stratified by
# term, it *is* the criterion.
#
# `--balloon` and results/b10_balloon.json are untouched.
# ---------------------------------------------------------------------------


def balloon2_new_acc() -> dict:
    return {"by_term": {c: {} for c in range(ORIG_FIELDS)},
            "loans_by_term": {},
            "yyyymm_rows": {c: 0 for c in range(ORIG_FIELDS)},
            "loans": 0, "loans_no_orig": 0, "loans_no_term": 0,
            "loans_no_period": 0}


def balloon2_absorb(acc: dict, recs, orig_fields) -> None:
    """One loan: its term stratum, and each YYYYMM column's offset in it."""
    acc["loans"] += 1
    if orig_fields is None:
        acc["loans_no_orig"] += 1
        return
    try:
        term = int(orig_fields[O_TERM])
    except (ValueError, IndexError):
        acc["loans_no_term"] += 1
        return
    first = None
    for f in recs:
        try:
            first = int(f[P_PERIOD])
        except (ValueError, IndexError):
            continue
        break
    if first is None:
        acc["loans_no_period"] += 1
        return
    acc["loans_by_term"][term] = acc["loans_by_term"].get(term, 0) + 1
    for c in range(ORIG_FIELDS):
        v = _yyyymm(orig_fields[c]) if len(orig_fields) > c else None
        if v is None:
            continue
        acc["yyyymm_rows"][c] += 1
        off = monthdiff(v, first) - term
        d = acc["by_term"][c].setdefault(term, {})
        d[off] = d.get(off, 0) + 1


def balloon2_payload(acc: dict) -> dict:
    cols = {}
    for c in range(ORIG_FIELDS):
        if not acc["yyyymm_rows"][c]:
            continue
        strata = {}
        for term, h in sorted(acc["by_term"][c].items()):
            n = sum(h.values())
            top = max(h, key=lambda k: h[k])
            strata[str(term)] = {"loans": n, "top_offset": top,
                                 "top_n": h[top], "top_share": h[top] / n,
                                 "distinct_offsets": len(h)}
        offs = {v["top_offset"] for v in strata.values()}
        cols[str(c)] = {
            "col_1indexed": c + 1,
            "yyyymm_rows": acc["yyyymm_rows"][c],
            "strata": strata,
            "n_strata": len(strata),
            "distinct_top_offsets": len(offs),
            "top_offsets": sorted(offs),
            "invariant": len(offs) == 1,
            "thinnest_stratum": (min(((int(t), v["loans"])
                                      for t, v in strata.items()),
                                     key=lambda kv: kv[1]) if strata else None),
        }
    return {"cols": cols,
            "loans_by_term": {str(k): v for k, v in
                              sorted(acc["loans_by_term"].items())},
            **{k: acc[k] for k in ("loans", "loans_no_orig", "loans_no_term",
                                   "loans_no_period")}}


def print_balloon2(pl: dict) -> None:
    print("\n  A. the term strata, taken from the data, not binned here")
    tot = max(sum(pl["loans_by_term"].values()), 1)
    for t, n in sorted(pl["loans_by_term"].items(), key=lambda kv: -kv[1])[:12]:
        print(f"     term {t:>5}   loans {n:>10,}   {n / tot * 100:6.3f}%")
    print(f"     strata in all: {len(pl['loans_by_term'])}"
          f"   loans placed: {tot:,}")

    print("\n  B. §8·14·6·5's variable: top offset per stratum, per column")
    for k in sorted(pl["cols"], key=int):
        d = pl["cols"][k]
        th = d["thinnest_stratum"]
        print(f"\n     orig col {d['col_1indexed']}"
              f"   strata {d['n_strata']}"
              f"   distinct top offsets {d['distinct_top_offsets']}"
              f"   invariant {d['invariant']}")
        if th:
            print(f"       thinnest stratum: term {th[0]} with {th[1]:,} loans")
        rows = sorted(d["strata"].items(), key=lambda kv: -kv[1]["loans"])
        for t, v in rows[:10]:
            print(f"       term {t:>5}  loans {v['loans']:>10,}"
                  f"  top offset {v['top_offset']:>6}"
                  f"  share {v['top_share']:.5f}"
                  f"  distinct offsets {v['distinct_offsets']:>4}")
        if len(rows) > 10:
            print(f"       ... and {len(rows) - 10} thinner strata, all in the"
                  f" record file")
        if not d["invariant"]:
            odd = [(t, v["top_offset"], v["loans"]) for t, v in rows
                   if v["top_offset"] != rows[0][1]["top_offset"]]
            print(f"       strata disagreeing with the largest: {len(odd)}"
                  f"   e.g. {odd[:4]}")

    print("\n  C. Read, per the criteria fixed before the run, three branches")
    inv = [pl["cols"][k] for k in sorted(pl["cols"], key=int)
           if pl["cols"][k]["invariant"]]
    print(f"     columns whose top offset is the same in every stratum: "
          f"{[d['col_1indexed'] for d in inv] or 'none'}")
    print("     (named, not counted)")
    if not inv:
        print("     SECOND BRANCH. No maturity path. `balloon_horizon` on")
        print("     Freddie would be a single uncrossed path, and it must never")
        print("     be written up as checked.")
        return
    if len(inv) > 1:
        print("     THIRD BRANCH. More than one column is invariant. Print")
        print("     whether they agree row for row before going on; this run")
        print("     does not go on.")
        return
    d = inv[0]
    print(f"     FIRST BRANCH. orig col {d['col_1indexed']} is the maturity")
    print(f"     column: offset {d['top_offsets'][0]} in every one of its")
    print(f"     {d['n_strata']} term strata. That invariance is what the")
    print("     identity 'maturity date' consists of, and pooling the strata")
    print("     is what hid it in --balloon.")
    print("     §8·14·6·2 may now be read, on that column.")


def cmd_balloon2(only) -> int:
    vintages = only or VINTAGES
    print("§8·14·6·5: the anchor stratified by term, so the invariance it was\n"
          "always asking about is the criterion rather than a casualty.\n")
    acc = balloon2_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        raw = {}
        with zipfile.ZipFile(archive(v)) as zf:
            for f in _lines(zf, f"sample_orig_{v}.txt"):
                if len(f) > O_SEQ:
                    raw[f[O_SEQ]] = f
        for seq, recs in loans(v):
            balloon2_absorb(acc, recs, raw.get(seq))
        print(f"  {v}  done   loans so far {acc['loans']:,}", flush=True)
    pl = balloon2_payload(acc)
    print_balloon2(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_balloon2.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "balloon2", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Does not re-decide "
             "§8·14·6's landing. Strata are the data's own term values; no "
             "binning here. --balloon is untouched.",
         "yyyymm_window": [YYYYMM_LO, YYYYMM_HI],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --balloon3. Registered before the code
# written.
#
# `--balloon2` landed §8·14·6·5's second branch, whose wording is "the maturity
# path does not exist". The test was one-sided: it checked whether the top
# offset is constant, and read the failure of that as the absence of the whole
# kind. The complementary identity — `top offset + term` constant, i.e. a date
# measured from origination — was **named in the registration's own prose** and
# never written as a test. MEASUREMENT.md 失效模式 21.
#
# This mode tests both and reads which one holds. That turns the criterion into
# a comparison, which needs no scale, and it hands back a free cross-check: two
# columns landing on opposite invariants is itself a check.
#
# **No scan.** Both halves are arithmetic on artefacts already on disk, so the
# two runs share a population by construction (失效模式 18's second condition).
# ---------------------------------------------------------------------------


def balloon3_loads(strata: dict) -> dict:
    """The two invariants' loads, weighted by loans and not by strata.

    §8·14·6·6: 264 strata are mostly odd terms holding a handful of loans, so
    counting strata would give a one-loan stratum the same say as the
    thirty-year one.
    """
    A, B = {}, {}
    nA, nB = {}, {}
    total = 0
    for t, v in strata.items():
        term = int(t)
        n = v["loans"]
        total += n
        a, b = v["top_offset"], v["top_offset"] + term
        A[a] = A.get(a, 0) + n
        B[b] = B.get(b, 0) + n
        nA[a] = nA.get(a, 0) + 1
        nB[b] = nB.get(b, 0) + 1

    def best(h, ns):
        if not h:
            return None
        k = max(h, key=lambda x: h[x])
        return {"mode": k, "loans": h[k], "strata": ns[k],
                "share": h[k] / total if total else float("nan")}

    a, b = best(A, nA), best(B, nB)
    return {"total_loans": total, "n_strata": len(strata),
            "A_offset_constant": a, "B_offset_plus_term_constant": b,
            "verdict": (None if (a is None or b is None) else
                        "A" if a["loans"] > b["loans"] else
                        "B" if b["loans"] > a["loans"] else "tie")}


def balloon3_payload(pl2: dict, pl1: dict) -> dict:
    cols = {}
    for k, d in pl2["cols"].items():
        ld = balloon3_loads(d["strata"])
        odd = sorted(((int(t), v["top_offset"], v["loans"])
                      for t, v in d["strata"].items()
                      if ld["A_offset_constant"]
                      and v["top_offset"] != ld["A_offset_constant"]["mode"]),
                     key=lambda x: -x[2])
        cols[k] = {"col_1indexed": d["col_1indexed"], **ld,
                   "strata_off_A_mode": len(odd),
                   "loans_off_A_mode": sum(x[2] for x in odd),
                   "largest_off_A_mode": odd[:6],
                   #: §8·14·6·2's half, read off `--balloon`'s own table for
                   #: this same column. Not recomputed.
                   "deferral": (pl1.get("cols", {}).get(k) or {}).get("cmp_top"),
                   "deferral_n": (pl1.get("cols", {}).get(k) or {}).get("cmp_n", 0),
                   "deferral_out": (pl1.get("cols", {}).get(k) or {}).get("cmp_out", 0),
                   "deferral_hist": (pl1.get("cols", {}).get(k) or {}).get("cmp_hist", {})}
    return {"cols": cols,
            "defer_rows": pl1.get("defer_rows"),
            "defer_rows_rem_ok": pl1.get("defer_rows_rem_ok"),
            "defer_rows_no_rem": pl1.get("defer_rows_no_rem"),
            "loans_by_term": pl2.get("loans_by_term", {})}


def print_balloon3(pl: dict) -> None:
    print("\n  A. §8·14·6·6: the two invariants side by side, loan-weighted")
    print(f"     {'col':>4}   {'A: top offset constant':<34}"
          f"{'B: top offset + term constant':<34}verdict")
    for k in sorted(pl["cols"], key=int):
        d = pl["cols"][k]
        a, b = d["A_offset_constant"], d["B_offset_plus_term_constant"]
        fa = ("-" if a is None else
              f"mode {a['mode']:>5}  {a['loans']:>9,}  {a['share']:7.5f}"
              f"  {a['strata']:>3}/{d['n_strata']}")
        fb = ("-" if b is None else
              f"mode {b['mode']:>5}  {b['loans']:>9,}  {b['share']:7.5f}"
              f"  {b['strata']:>3}/{d['n_strata']}")
        print(f"     {d['col_1indexed']:>4}   {fa:<34}{fb:<34}{d['verdict']}")
    print("     A constant means the date is measured from maturity;")
    print("     B constant means it is measured from origination. **Both are")
    print("     identities**, and reading only A is what made --balloon2 call")
    print("     a first-payment column 'not a maturity path' rather than")
    print("     'a different thing' (失效模式 21).")
    print("     The verdict is which load is larger. A comparison, no scale.")

    print("\n  B. §8·14·6·6·2's free cross-check: do the two land opposite")
    verds = {pl["cols"][k]["col_1indexed"]: pl["cols"][k]["verdict"]
             for k in sorted(pl["cols"], key=int)}
    print(f"     {verds}")
    sides = set(v for v in verds.values() if v in ("A", "B"))
    if len(verds) >= 2 and len(sides) == 2:
        print("     Complementary. The check passes: two paths, two identities,")
        print("     not overlapping.")
        cross_ok = True
    elif len(verds) >= 2:
        print("     NOT complementary: they land on the same side. Either one")
        print("     identity is misread or the two columns are one quantity")
        print("     written twice. Print and stop; §8·14·6·2 does not open.")
        cross_ok = False
    else:
        print("     Only one column; the check has no referent.")
        cross_ok = True

    print("\n  C. Read, per the criteria fixed before the run, four branches")
    wins = [pl["cols"][k] for k in sorted(pl["cols"], key=int)
            if pl["cols"][k]["verdict"] == "A"]
    ties = [pl["cols"][k] for k in sorted(pl["cols"], key=int)
            if pl["cols"][k]["verdict"] == "tie"]
    if ties:
        print(f"     TIE, listed on its own (§11 item 4): "
              f"{[d['col_1indexed'] for d in ties]}")
        for d in ties:
            print(f"       col {d['col_1indexed']}: both loads "
                  f"{d['A_offset_constant']['loans']:,}")
    print(f"     columns where A wins: "
          f"{[d['col_1indexed'] for d in wins] or 'none'}   (named, not counted)")
    if not wins:
        print("     SECOND BRANCH. No column is measured from maturity, so that")
        print("     path does not exist and §8·14·6·2 lands on its third:")
        print("     `rem_legal` alone, uncrossed, never to be called checked.")
        return
    if len(wins) > 1:
        print("     THIRD BRANCH. More than one column. Print whether they")
        print("     agree row for row before going on; this run does not.")
        return
    d = wins[0]
    a = d["A_offset_constant"]
    print(f"     FIRST BRANCH. orig col {d['col_1indexed']} is the maturity")
    print(f"     column: offset {a['mode']} carries {a['loans']:,} loans"
          f" ({a['share']:.5f}) across {a['strata']} of {d['n_strata']} strata.")
    print("\n     加细, inside this branch, not a branch itself:")
    print(f"       strata off that offset: {d['strata_off_A_mode']}"
          f"   loans in them: {d['loans_off_A_mode']:,}")
    print(f"       largest of those: {d['largest_off_A_mode'][:4]}")
    print("       §8·14·6·5·2 wrote this shape down before the run: if only")
    print("       very thin strata disagree, the cheapest candidate is loans")
    print("       whose term was re-set, not that the column is wrong. It is a")
    print("       candidate; naming it needs its own registration.")

    if not cross_ok:
        print("\n     §8·14·6·6·2's cross-check did not pass, so §8·14·6·2")
        print("     does not open this round.")
        return
    print("\n  D. §8·14·6·2, read off --balloon's own table for that column")
    t, n = d["deferral"], d["deferral_n"]
    print(f"     deferral rows {pl['defer_rows']:,}"
          f"   with a readable rem_legal {pl['defer_rows_rem_ok']:,}"
          f"   without {pl['defer_rows_no_rem']:,}")
    if not n or t is None:
        print("     That column never meets a deferral row: no referent.")
        return
    bad = n - t["n"]
    print(f"     compared {n:,}   busiest offset {t['offset']}"
          f"   share {t['share']:.5f}   disagreeing {bad:,}"
          f"   beyond span {d['deferral_out']:,}")
    print(f"     next buckets: "
          f"{list(d['deferral_hist'].items())[1:5]}")
    if bad == 0:
        print("     FIRST BRANCH. The two paths agree on every deferral row.")
        print("     `balloon_horizon` carries over from Fannie as written.")
    else:
        print(f"     SECOND BRANCH. {bad:,} of {n:,} rows disagree"
              f" ({bad / n * 100:.4f}%).")
        print("     §14.1 says the two agree **exactly**, and b8_omega's own")
        print("     comment says a non-zero disagree is news about the file and")
        print("     not a tolerance to widen. Report the shape; do not set `bn`")
        print("     until it is settled.")


def cmd_balloon3(only) -> int:
    src2 = RESULTS / "b10_balloon2.json"
    src1 = RESULTS / "b10_balloon.json"
    for f in (src1, src2):
        if not f.exists():
            print(f"  {f.relative_to(ROOT)} is not on disk. Run it first.")
            return 1
    pl2 = json.loads(src2.read_text(encoding="utf-8"))
    pl1 = json.loads(src1.read_text(encoding="utf-8"))
    print("§8·14·6·6: both invariants, side by side. Arithmetic on two\n"
          "artefacts already on disk; no scan, no omega.\n")
    pl = balloon3_payload(pl2, pl1)
    print_balloon3(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_balloon3.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "balloon3", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Does not re-decide "
             "§8·14·6 or §8·14·6·5. Pure arithmetic on b10_balloon.json and "
             "b10_balloon2.json; both are left untouched.",
         "sources": ["results/b10_balloon.json", "results/b10_balloon2.json"],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --extend. Registered before the code
# written.
#
# §8·14·6·6 named orig col 4 the maturity column and §8·14·6·2 landed its
# second branch: the two horizon paths disagree on 32.8984% of deferral rows,
# every listed bucket negative. The structural candidate is that Freddie's
# maturity date sits on the static origination record while `rem_legal` is
# monthly, so a re-set term splits them. **Two things have to be measured
# before that is a reading rather than a story**, and this mode does both.
#
# The discriminant is structural, not statistical: under ordinary amortisation
# `rem_legal` falls by exactly one each month. A month where it RISES is direct
# evidence the term was re-set.
# ---------------------------------------------------------------------------

#: §8·14·6·6 named it. Written down rather than re-derived; re-deriving it here
#: would be a second opinion on a settled reading.
O_MATURITY = 3


def extend_new_acc() -> dict:
    return {
        # §8·14·6·7·1
        "defer_eq": 0, "defer_ne": 0,
        "defer_eq_risen": 0, "defer_ne_risen": 0,
        "rise_size": {}, "rise_year": {}, "rise_with_mod": 0, "rise_rows": 0,
        "loans_with_a_rise": 0,
        # §8·14·6·7·2
        "perf_yyyymm_rows": {c: 0 for c in range(PERF_FIELDS)},
        "perf_anchor": {c: {} for c in range(PERF_FIELDS)},
        # coverage
        "loans": 0, "rows": 0, "loans_no_orig": 0, "loans_no_mat": 0,
        "defer_no_rem": 0,
    }


def extend_absorb(acc: dict, recs, orig_fields) -> None:
    """One loan: does `rem_legal` ever rise, and how the deferral rows split."""
    acc["loans"] += 1
    acc["rows"] += len(recs)

    # ---- pass one: does this loan's rem_legal ever rise ------------------
    risen = False
    prev_rem = prev_per = None
    for f in recs:
        try:
            per = int(f[P_PERIOD])
            rem = int(f[P_REM])
        except (ValueError, IndexError):
            prev_rem = prev_per = None
            continue
        if prev_rem is not None and per == next_period(prev_per) and rem > prev_rem:
            risen = True
            acc["rise_rows"] += 1
            step = rem - prev_rem
            acc["rise_size"][step] = acc["rise_size"].get(step, 0) + 1
            yr = per // 100
            acc["rise_year"][yr] = acc["rise_year"].get(yr, 0) + 1
            mod = f[P_MODFLAG].strip() if len(f) > P_MODFLAG else ""
            if mod:
                acc["rise_with_mod"] += 1
        prev_rem, prev_per = rem, per
    if risen:
        acc["loans_with_a_rise"] += 1

    # ---- §8·14·6·7·2: the same YYYYMM narrowing, on the perf side --------
    for f in recs:
        try:
            per = int(f[P_PERIOD])
            rem = int(f[P_REM])
        except (ValueError, IndexError):
            continue
        for c in range(PERF_FIELDS):
            v = _yyyymm(f[c]) if len(f) > c else None
            if v is None:
                continue
            acc["perf_yyyymm_rows"][c] += 1
            off = monthdiff(v, per) - rem
            key = off if -ANCHOR_SPAN <= off <= ANCHOR_SPAN else "out"
            acc["perf_anchor"][c][key] = acc["perf_anchor"][c].get(key, 0) + 1

    # ---- §8·14·6·7·1: split the deferral rows the same way --balloon did --
    if orig_fields is None:
        acc["loans_no_orig"] += 1
        return
    mat = _yyyymm(orig_fields[O_MATURITY]) if len(orig_fields) > O_MATURITY else None
    if mat is None:
        acc["loans_no_mat"] += 1
        return
    for f in recs:
        d = _num(f[P_DEFER_BAL]) if len(f) > P_DEFER_BAL else None
        if d is None or d <= 0:
            continue
        try:
            per = int(f[P_PERIOD])
            rem = int(f[P_REM])
        except (ValueError, IndexError):
            acc["defer_no_rem"] += 1
            continue
        if monthdiff(mat, per) - rem == 0:
            acc["defer_eq"] += 1
            if risen:
                acc["defer_eq_risen"] += 1
        else:
            acc["defer_ne"] += 1
            if risen:
                acc["defer_ne_risen"] += 1


def extend_payload(acc: dict) -> dict:
    perf = {}
    for c in range(PERF_FIELDS):
        if not acc["perf_yyyymm_rows"][c]:
            continue
        m = _mode(acc["perf_anchor"][c])
        perf[str(c)] = {
            "col_1indexed": c + 1,
            "yyyymm_rows": acc["perf_yyyymm_rows"][c],
            "out": acc["perf_anchor"][c].get("out", 0),
            "top": (None if m is None else
                    {"offset": m[0], "n": m[1], "share": m[2]}),
            "hist": {str(k): v for k, v in
                     sorted(acc["perf_anchor"][c].items(),
                            key=lambda kv: -kv[1])[:8]},
        }
    eq, ne = acc["defer_eq"], acc["defer_ne"]
    return {
        "defer_eq": eq, "defer_ne": ne,
        "defer_eq_risen": acc["defer_eq_risen"],
        "defer_ne_risen": acc["defer_ne_risen"],
        "share_eq_risen": acc["defer_eq_risen"] / eq if eq else float("nan"),
        "share_ne_risen": acc["defer_ne_risen"] / ne if ne else float("nan"),
        "rise_size": {str(k): v for k, v in sorted(acc["rise_size"].items())},
        "rise_year": {str(k): v for k, v in sorted(acc["rise_year"].items())},
        "rise_with_mod": acc["rise_with_mod"], "rise_rows": acc["rise_rows"],
        "loans_with_a_rise": acc["loans_with_a_rise"],
        "perf_cols": perf,
        **{k: acc[k] for k in ("loans", "rows", "loans_no_orig",
                               "loans_no_mat", "defer_no_rem")},
    }


def print_extend(pl: dict) -> None:
    print("\n  A. §8·14·6·7·1: does `rem_legal` ever rise, split by the two paths")
    eq, ne = pl["defer_eq"], pl["defer_ne"]
    print(f"     {'group':<28}{'deferral rows':>15}{'loan ever rose':>17}"
          f"{'share':>10}")
    print(f"     {'paths agree (offset 0)':<28}{eq:>15,}"
          f"{pl['defer_eq_risen']:>17,}{pl['share_eq_risen']:>10.5f}")
    print(f"     {'paths disagree':<28}{ne:>15,}"
          f"{pl['defer_ne_risen']:>17,}{pl['share_ne_risen']:>10.5f}")
    print("     Both denominators printed, never a bare ratio (§2·5·1).")
    print("     `rem_legal` falls by exactly one under ordinary amortisation, so")
    print("     a month where it RISES is direct evidence the term was re-set.")
    print("     Structural, not a correlation.")

    print(f"\n     loans with at least one rise: {pl['loans_with_a_rise']:,}"
          f"   rising months: {pl['rise_rows']:,}"
          f"   of those carrying a mod flag: {pl['rise_with_mod']:,}")
    sz = sorted(((int(k), v) for k, v in pl["rise_size"].items()),
                key=lambda kv: -kv[1])[:8]
    print(f"     rise sizes, busiest eight: {sz}")
    yr = sorted(((int(k), v) for k, v in pl["rise_year"].items()),
                key=lambda kv: -kv[1])[:8]
    print(f"     rise years, busiest eight: {yr}")
    print("     Both are 加细 inside whichever branch lands, and the two shapes")
    print("     §8·14·6·7·3 wrote down before the run: sizes should pile on the")
    print("     terms modifications target, years on 2009-2016 and 2020-2022.")

    print("\n  B. §8·14·6·7·2: the same YYYYMM narrowing on the perf side")
    if not pl["perf_cols"]:
        print("     No perf column ever parses as a YYYYMM in the window.")
    else:
        print(f"     {'col':>4}{'YYYYMM rows':>14}{'top offset':>12}"
              f"{'its share':>11}{'beyond span':>13}   next")
        for k in sorted(pl["perf_cols"], key=int):
            d = pl["perf_cols"][k]
            t = d["top"]
            rest = "  ".join(f"{a}:{b:,}" for a, b in
                             list(d["hist"].items())[1:4])
            off = "none" if t is None else str(t["offset"])
            sh = "-" if t is None else f"{t['share']:.5f}"
            print(f"     {d['col_1indexed']:>4}{d['yyyymm_rows']:>14,}"
                  f"{off:>12}{sh:>11}{d['out']:>13,}   {rest}")
        print(f"     `beyond span` is the overflow past +-{ANCHOR_SPAN}; it is")
        print("     not eligible to be the top bucket (§11).")

    print("\n  C. Read, per the criteria fixed before the run")
    const = [pl["perf_cols"][k] for k in sorted(pl["perf_cols"], key=int)
             if pl["perf_cols"][k]["top"]
             and pl["perf_cols"][k]["top"]["share"] > 0.5]
    print(f"     perf columns whose offset presses onto one integer: "
          f"{[d['col_1indexed'] for d in const] or 'none'}   (named, not counted)")
    if len(const) == 1:
        print("     FIRST BRANCH of §8·14·6·7·2: this station picked the wrong")
        print("     column. §8·14·6·6·2's structural candidate is void; go back")
        print("     to §8·14·6·2 and compare against this one instead.")
    elif len(const) > 1:
        print("     THIRD BRANCH: more than one. Print, and use none of them")
        print("     until it is settled.")
    else:
        print("     SECOND BRANCH: the perf side carries no monthly maturity")
        print("     date. The first premise of §8·14·6·6·2's candidate holds.")

    print()
    a, b = pl["share_eq_risen"], pl["share_ne_risen"]
    if not (a == a and b == b):
        print("     §8·14·6·7·1 has no referent: one of the two groups is empty.")
        return
    if b > a:
        print(f"     FIRST BRANCH of §8·14·6·7·1: {b:.5f} against {a:.5f}.")
        print("     The disagreement is explained by the term being re-set.")
        print("     Freddie's maturity column is the one written at origination")
        print("     and it does not follow a re-contracting; `rem_legal` does.")
        print("     **Which of the two `V` should take is NOT settled here**")
        print("     (§8·14·6·7·4): Fannie prefers the maturity date only because")
        print("     the two agree there, and a preference that was never tested")
        print("     does not carry to a carrier where they do not.")
    elif b < a:
        print(f"     THIRD BRANCH: {b:.5f} against {a:.5f}, the wrong way round.")
        print("     Instrument or population error. Do not read; go back.")
    else:
        print(f"     SECOND BRANCH: the two are equal at {a:.5f}. A re-set term")
        print("     is not the explanation. Register it, and `bn` stays unset.")
    print("     `bn` is not set either way (§8·14·6·2's second branch).")


def cmd_extend(only) -> int:
    vintages = only or VINTAGES
    print("§8·14·6·7: is the 32.90% the loans whose term was re-set, and does\n"
          "the perf side carry a monthly maturity date at all. No omega.\n")
    acc = extend_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        raw = {}
        with zipfile.ZipFile(archive(v)) as zf:
            for f in _lines(zf, f"sample_orig_{v}.txt"):
                if len(f) > O_SEQ:
                    raw[f[O_SEQ]] = f
        for seq, recs in loans(v):
            extend_absorb(acc, recs, raw.get(seq))
        print(f"  {v}  done   deferral rows split "
              f"{acc['defer_eq']:,}/{acc['defer_ne']:,}", flush=True)
    pl = extend_payload(acc)
    print_extend(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_extend.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "extend", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Two independent "
             "variables, reported apart. Sets no bn (§8·14·6·2's second "
             "branch) and does not decide which horizon V should take "
             "(§8·14·6·7·4).",
         "maturity_col_1indexed": O_MATURITY + 1,
         "defer_col_1indexed": P_DEFER_BAL + 1,
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --horizon. Registered before the code
# written.
#
# `bn` is the last input of `V` still open on this carrier. §8·14·6·7 measured
# WHY the two horizon paths part; §8·14·6·8 asks which one to take, and it asks
# it as something measurable rather than as an argument: **is `period +
# rem_legal` naming a date at all.** If it is, it is constant per loan and moves
# only on the month a modification happens.
#
# `Y` and `P` are kept apart. §8·14·6·7·2 already paid for mixing them: `P`
# persists, so "every rise carries a flag" came out at 1.0000 and meant almost
# nothing. Only `Y` is a current-month event.
# ---------------------------------------------------------------------------


def horizon_new_acc() -> dict:
    return {"pairs_y": 0, "pairs_not_y": 0,
            "moved_y": 0, "moved_not_y": 0,
            "up": 0, "down": 0,
            "not_y_size": {}, "not_y_age": {}, "not_y_zerobal": {},
            "not_y_with_defer": 0,
            "bad_bn_rows": 0, "defer_rows": 0,
            "loans": 0, "rows": 0, "unparsed": 0}


def horizon_absorb(acc: dict, recs) -> None:
    """One loan: does `period + rem_legal` move, and on what kind of row."""
    acc["loans"] += 1
    acc["rows"] += len(recs)
    prev = None
    for f in recs:
        try:
            per = int(f[P_PERIOD])
        except (ValueError, IndexError):
            acc["unparsed"] += 1
            prev = None
            continue
        #: **`rem` is parsed apart from `per`, and the deferral census runs
        #: before the early exit.** Folded together, `bad_bn_rows` could never
        #: be incremented — the row would have left through `continue` first —
        #: and a counter that cannot fire is not a counter (§11 item 3).
        rem_ok = True
        try:
            rem = int(f[P_REM])
        except (ValueError, IndexError):
            rem_ok = False
        age = None
        try:
            age = int(f[P_AGE])
        except (ValueError, IndexError):
            pass
        mod = f[P_MODFLAG].strip() if len(f) > P_MODFLAG else ""
        zb = f[P_ZEROBAL].strip() if len(f) > P_ZEROBAL else ""
        d = _num(f[P_DEFER_BAL]) if len(f) > P_DEFER_BAL else None
        if d is not None and d > 0:
            acc["defer_rows"] += 1
            if not rem_ok:
                acc["bad_bn_rows"] += 1
        if not rem_ok:
            acc["unparsed"] += 1
            prev = None
            continue
        #: **The date this month names.** A loan whose term never changes names
        #: the same one every month.
        date = monthdiff_add(per, rem)
        if prev is not None:
            pper, pdate = prev
            if per == next_period(pper):
                is_y = (mod == "Y")
                if is_y:
                    acc["pairs_y"] += 1
                else:
                    acc["pairs_not_y"] += 1
                if date != pdate:
                    if is_y:
                        acc["moved_y"] += 1
                    else:
                        acc["moved_not_y"] += 1
                        step = monthdiff(date, pdate)
                        acc["not_y_size"][step] = \
                            acc["not_y_size"].get(step, 0) + 1
                        if age is not None:
                            acc["not_y_age"][age] = \
                                acc["not_y_age"].get(age, 0) + 1
                        acc["not_y_zerobal"][zb] = \
                            acc["not_y_zerobal"].get(zb, 0) + 1
                        if d is not None and d > 0:
                            acc["not_y_with_defer"] += 1
                    if monthdiff(date, pdate) > 0:
                        acc["up"] += 1
                    else:
                        acc["down"] += 1
        prev = (per, date)


def monthdiff_add(period: int, months: int) -> int:
    """YYYYMM `months` after YYYYMM `period`. The inverse of `monthdiff`."""
    m = (period // 100) * 12 + (period % 100 - 1) + months
    return (m // 12) * 100 + (m % 12 + 1)


def horizon_payload(acc: dict) -> dict:
    py, pn = acc["pairs_y"], acc["pairs_not_y"]
    return {
        "pairs_y": py, "pairs_not_y": pn,
        "moved_y": acc["moved_y"], "moved_not_y": acc["moved_not_y"],
        "rate_y": acc["moved_y"] / py if py else float("nan"),
        "rate_not_y": acc["moved_not_y"] / pn if pn else float("nan"),
        "up": acc["up"], "down": acc["down"],
        "not_y_size": {str(k): v for k, v in sorted(
            acc["not_y_size"].items(), key=lambda kv: -kv[1])[:12]},
        "not_y_age": {str(k): v for k, v in sorted(
            acc["not_y_age"].items(), key=lambda kv: -kv[1])[:12]},
        "not_y_zerobal": dict(sorted(acc["not_y_zerobal"].items(),
                                     key=lambda kv: -kv[1])),
        "not_y_with_defer": acc["not_y_with_defer"],
        "not_y_ages_distinct": len(acc["not_y_age"]),
        "defer_rows": acc["defer_rows"], "bad_bn_rows": acc["bad_bn_rows"],
        **{k: acc[k] for k in ("loans", "rows", "unparsed")},
    }


def print_horizon(pl: dict) -> None:
    print("\n  A. §8·14·6·8·1: does `period + rem_legal` move, and on what row")
    print(f"     {'row kind':<34}{'pairs':>14}{'the date moved':>16}{'rate':>11}")
    print(f"     {'carrying Y (modified this month)':<34}{pl['pairs_y']:>14,}"
          f"{pl['moved_y']:>16,}{pl['rate_y']:>11.6f}")
    print(f"     {'not carrying Y':<34}{pl['pairs_not_y']:>14,}"
          f"{pl['moved_not_y']:>16,}{pl['rate_not_y']:>11.6f}")
    print("     Y only. `P` persists once a loan has ever been modified, so a")
    print("     count against 'has a flag' is close to a tautology — §8·14·6·7·2")
    print("     paid for that once already.")
    print("     Both denominators printed, never a bare ratio (§2·5·1).")

    print(f"\n     of all the moves: up {pl['up']:,}   down {pl['down']:,}")

    print("\n  B. 加细: what the moves on rows WITHOUT a Y look like")
    print(f"     sizes (months), busiest twelve: "
          f"{list(pl['not_y_size'].items())[:12]}")
    print(f"     loan ages, busiest twelve:      "
          f"{list(pl['not_y_age'].items())[:12]}")
    print(f"     distinct ages they occur at:    {pl['not_y_ages_distinct']:,}")
    print(f"     zero-balance codes on them:     {pl['not_y_zerobal']}")
    print(f"     of them carrying a deferred balance: "
          f"{pl['not_y_with_defer']:,}")
    print("     §8·14·6·8·3, written before the run: if the first branch lands,")
    print("     these should be few AND should sit in a loan's first month or")
    print("     two. Spread across the whole life means `rem_legal` moves with")
    print("     no re-contracting, and the branch then travels with that.")

    print(f"\n  C. deferral rows {pl['defer_rows']:,}"
          f"   of them with no readable horizon {pl['bad_bn_rows']:,}")
    print("     That is `bad_bn`'s population under the second path.")

    print("\n  D. Read, per the criteria fixed before the run, three branches")
    ry, rn = pl["rate_y"], pl["rate_not_y"]
    if pl["moved_y"] + pl["moved_not_y"] == 0:
        print("     THIRD BRANCH. Nothing moved at all, which contradicts")
        print("     §8·14·6·7's 16,381 loans whose rem_legal rose. Instrument")
        print("     error; do not read, go back.")
        return
    if not (ry == ry and rn == rn):
        print("     One of the two groups is empty: no referent.")
        return
    if ry > rn:
        print(f"     FIRST BRANCH. {ry:.6f} against {rn:.6f}.")
        print("     `period + rem_legal` names the current legal maturity: it")
        print("     moves when the contract is re-cut and not otherwise. It is")
        print("     a clean date, so **`bn` takes it**, and orig col 4 is the")
        print("     one written at origination — kept for the record, out of V.")
        print("     This does not release V: the noise floor is still untouched")
        print("     (§8·13·1 item 1).")
    elif ry < rn:
        print(f"     SECOND BRANCH. {ry:.6f} against {rn:.6f}, the wrong way.")
        print("     `rem_legal` moves where no contract was re-cut, so it is not")
        print("     a clean date either. Neither path is trustworthy; `bn` stays")
        print("     unset and the second carrier's V stops here.")
    else:
        print(f"     SECOND BRANCH. The two rates are equal at {ry:.6f}.")
        print("     Same landing: `bn` stays unset.")


def cmd_horizon(only) -> int:
    vintages = only or VINTAGES
    print("§8·14·6·8: is `period + rem_legal` naming a date, or just moving.\n"
          "One variable, Y kept apart from P. No omega.\n")
    acc = horizon_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        for seq, recs in loans(v):
            horizon_absorb(acc, recs)
        print(f"  {v}  done   moves so far "
              f"{acc['moved_y']:,}/{acc['moved_not_y']:,}", flush=True)
    pl = horizon_payload(acc)
    print_horizon(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_horizon.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "horizon", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Decides only which "
             "horizon bn takes on this carrier; does not release V, whose noise "
             "floor is untouched. Does not touch Fannie's preference.",
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --balid. Registered before the code.
#
# `V`'s first factor is the interest-bearing balance. On Fannie that is
# `12 - 63 - 108`; on Freddie §8·14·5·2 wrote `col 3 - col 12` into a branch's
# wording and marked it **unverified**, because the variable that selected the
# branch was a signature and a signature does not test an identity.
#
# Two hypotheses, one discriminant, and it does not close a loop: on a quiet
# month where the deferred balance `D` is positive and unchanged,
#
#     H1 (col 3 contains D)   col3(t) = col3(t-1)(1+i) - P - D*i
#     H2 (col 3 does not)     col3(t) = col3(t-1)(1+i) - P
#
# and the two differ by `D*i`, about $41 a month against a balance reported to
# the cent. `P` comes from the ORIGINATION side, never from the column under
# test, so neither hypothesis is assumed in order to test it.
# ---------------------------------------------------------------------------

#: §8·18·1. `P` from `coarse_all`'s arm (§6·4): the origination balance, which
#: sits on the $1,000 grid, so `P` carries about 0.3% (§10·9·9) — around $3 on
#: a $1,000 payment, an order of magnitude under `D*i`.
#:
#: **The error moves both residuals by the same amount**, so the comparison
#: survives any `|eps| < D*i / 2`. The margin is printed, not assumed.
BALID_MODFLAGS = ("Y", "P")


def balid_new_acc() -> dict:
    return {"loans": 0, "rows": 0, "loans_ever_mod": 0, "loans_no_orig": 0,
            "pairs": 0,
            "drop_gap": 0, "drop_defer": 0, "drop_defer_moved": 0,
            #: No per-row modification-flag counter: §8·18·1 makes the flag
            #: a LOAN-level exclusion (P is the original payment), so a row
            #: could never reach one. A counter that cannot fire is not a
            #: counter (§11 item 3), and this file has paid for that twice.
            "drop_rate": 0, "drop_zerobal": 0,
            "drop_upb": 0, "drop_no_payment": 0,
            "kept": 0,
            "h1": [], "h2": [], "di": [], "ident": [],
            "by_vintage": {}, "sample_capped": False}


#: Samples kept for exact quantiles. Printed, never silent.
BALID_SAMPLE_CAP = 2_000_000


def balid_absorb(acc: dict, recs, orig, vintage: int) -> None:
    """One loan. `orig` is ``(orig_upb, rate, term)`` or None.

    §8·18·2's population: a quiet month with a deferral outstanding and
    unmoved, on a loan that has **never** been modified — because `P` is the
    original contract payment and one re-cut replaces it.
    """
    acc["loans"] += 1
    acc["rows"] += len(recs)
    if orig is None:
        acc["loans_no_orig"] += 1
        return
    for f in recs:
        m = f[P_MODFLAG].strip() if len(f) > P_MODFLAG else ""
        if m in BALID_MODFLAGS:
            acc["loans_ever_mod"] += 1
            return

    u0, rate0, term = orig
    prev = None
    for f in recs:
        try:
            per = int(f[P_PERIOD])
            upb = float(f[P_UPB])
            rate = float(f[P_RATE])
        except (ValueError, IndexError):
            prev = None
            continue
        d = _num(f[P_DEFER_BAL]) if len(f) > P_DEFER_BAL else None
        zb = f[P_ZEROBAL].strip() if len(f) > P_ZEROBAL else ""
        cur = (per, upb, rate, d, zb)
        if prev is None:
            prev = cur
            continue
        pper, pupb, prate, pd, pzb = prev
        prev = cur
        acc["pairs"] += 1
        if per != next_period(pper):
            acc["drop_gap"] += 1
            continue
        if d is None or pd is None or d <= 0 or pd <= 0:
            acc["drop_defer"] += 1
            continue
        if abs(d - pd) > 1e-9:
            #: A month where the deferral itself moved is not a quiet month for
            #: this identity: both hypotheses would have to model the move.
            acc["drop_defer_moved"] += 1
            continue
        if abs(rate - prate) > 1e-9:
            acc["drop_rate"] += 1
            continue
        if zb or pzb:
            acc["drop_zerobal"] += 1
            continue
        if upb <= 0 or pupb <= 0:
            acc["drop_upb"] += 1
            continue
        i = rate / 1200.0
        P = contract_payment(u0, rate0 / 1200.0, term)
        if not (P == P) or P <= 0:
            acc["drop_no_payment"] += 1
            continue
        acc["kept"] += 1
        r1 = (upb - d) - ((pupb - d) * (1.0 + i) - P)
        r2 = upb - (pupb * (1.0 + i) - P)
        di = d * i
        if len(acc["h1"]) < BALID_SAMPLE_CAP:
            acc["h1"].append(r1)
            acc["h2"].append(r2)
            acc["di"].append(di)
            #: §8·18·4's correction: `r2 - r1 = -D*i` is algebra, not a shape.
            #: Kept as a per-row residual so a code error is loud.
            acc["ident"].append((r2 - r1) + di)
        else:
            acc["sample_capped"] = True
        v = acc["by_vintage"].setdefault(vintage, {"n": 0, "h1": [], "h2": []})
        v["n"] += 1
        if len(v["h1"]) < 20_000:
            v["h1"].append(r1)
            v["h2"].append(r2)


def _absmed(xs):
    if not xs:
        return float("nan")
    y = sorted(abs(x) for x in xs)
    return y[len(y) // 2]


def _quant(xs, qs=(10, 50, 90)):
    if not xs:
        return [float("nan")] * len(qs)
    y = sorted(xs)
    return [float(y[min(len(y) - 1, max(0, int(round((q / 100) * (len(y) - 1)))))])
            for q in qs]


def balid_payload(acc: dict) -> dict:
    per_v = {}
    for v, d in sorted(acc["by_vintage"].items()):
        per_v[str(v)] = {"n": d["n"],
                         "absmed_h1": _absmed(d["h1"]),
                         "absmed_h2": _absmed(d["h2"])}
    drops = {k: acc[k] for k in
             ("drop_gap", "drop_defer", "drop_defer_moved", "drop_rate",
              "drop_zerobal", "drop_upb", "drop_no_payment")}
    return {"loans": acc["loans"], "rows": acc["rows"],
            "loans_ever_mod": acc["loans_ever_mod"],
            "loans_no_orig": acc["loans_no_orig"],
            "pairs": acc["pairs"], "kept": acc["kept"], "drops": drops,
            "dropped_total": sum(drops.values()),
            "absmed_h1": _absmed(acc["h1"]), "absmed_h2": _absmed(acc["h2"]),
            "q_h1": _quant(acc["h1"]), "q_h2": _quant(acc["h2"]),
            "q_di": _quant(acc["di"]),
            "absmed_di": _absmed(acc["di"]),
            "identity_absmed": _absmed(acc["ident"]),
            "identity_worst": (max(abs(x) for x in acc["ident"])
                               if acc["ident"] else float("nan")),
            "sampled": len(acc["h1"]), "sample_capped": acc["sample_capped"],
            "by_vintage": per_v}


def print_balid(pl: dict) -> None:
    print("\n  A. §8·18·3 item 1: the population, and every row it dropped")
    print(f"     loans {pl['loans']:,}   rows {pl['rows']:,}")
    print(f"     loans ever modified (P is the ORIGINAL payment) "
          f"{pl['loans_ever_mod']:,}")
    print(f"     loans with no orig row {pl['loans_no_orig']:,}")
    print(f"     consecutive-row pairs seen {pl['pairs']:,}")
    for k, v in pl["drops"].items():
        print(f"       {k:<20} {v:>12,}")
    print(f"       {'kept':<20} {pl['kept']:>12,}")
    ok = pl["dropped_total"] + pl["kept"] == pl["pairs"]
    print(f"     dropped + kept = {pl['dropped_total'] + pl['kept']:,}"
          f" against pairs {pl['pairs']:,}"
          f"   {'MATCH' if ok else 'DO NOT ADD UP'}")

    print("\n  B. the algebraic check, not a shape (§8·18·4's correction)")
    print(f"     (resid_H2 - resid_H1) + D*i, median |.| "
          f"{pl['identity_absmed']:.3e}   worst {pl['identity_worst']:.3e}")
    print("     This is identically zero by algebra: P cancels. Anything but")
    print("     floating-point dust here is a code error, not a finding.")

    print("\n  C. §8·18·2's variable, and the resolution it is read against")
    print(f"     D*i          p10 {pl['q_di'][0]:,.2f}"
          f"   p50 {pl['q_di'][1]:,.2f}   p90 {pl['q_di'][2]:,.2f}")
    print(f"     resid_H1     p10 {pl['q_h1'][0]:,.2f}"
          f"   p50 {pl['q_h1'][1]:,.2f}   p90 {pl['q_h1'][2]:,.2f}"
          f"   median |.| {pl['absmed_h1']:,.2f}")
    print(f"     resid_H2     p10 {pl['q_h2'][0]:,.2f}"
          f"   p50 {pl['q_h2'][1]:,.2f}   p90 {pl['q_h2'][2]:,.2f}"
          f"   median |.| {pl['absmed_h2']:,.2f}")
    print(f"     sampled {pl['sampled']:,}   capped {pl['sample_capped']}")
    print("     `P` carries about 0.3% of a payment (§10·9·9), and its error")
    print("     shifts BOTH residuals equally, so the comparison survives any")
    print("     |eps| < D*i / 2. The margin is the gap between the two medians")
    print("     above and the D*i median beside them.")

    print("\n  D. by vintage, because an identity that holds in some archives")
    print("     is not an identity")
    rows = list(pl["by_vintage"].items())
    for v, d in rows[:8]:
        print(f"       {v}  n {d['n']:>8,}   |H1| {d['absmed_h1']:>12,.2f}"
              f"   |H2| {d['absmed_h2']:>12,.2f}")
    if len(rows) > 8:
        print(f"       ... {len(rows) - 8} more vintages in the record file")
    flips = [v for v, d in rows
             if d["n"] >= 20 and not (d["absmed_h1"] < d["absmed_h2"])]
    print(f"     vintages with at least 20 rows where H1 is NOT the smaller: "
          f"{len(flips)}   {flips[:10]}")

    print("\n  E. Read, per the criteria fixed before the run, four branches")
    a1, a2, di = pl["absmed_h1"], pl["absmed_h2"], pl["absmed_di"]
    if not (a1 == a1 and a2 == a2 and di == di):
        print("     No referent: the population is empty.")
        return
    gap = abs(a1 - a2)
    print(f"     median |resid_H1| {a1:,.2f}   median |resid_H2| {a2:,.2f}"
          f"   median D*i {di:,.2f}   gap {gap:,.2f}")
    if gap < di / 2:
        print("     THIRD BRANCH. The two are closer together than half of")
        print("     D*i, so the discriminant has no referent on these rows.")
        print("     Check the population and whether P is usable; read nothing.")
        return
    if min(a1, a2) > di:
        print("     FOURTH BRANCH. Neither residual is near zero: both are")
        print("     larger than D*i itself. Neither hypothesis holds, so col 3")
        print("     does not amortise on deferral rows at all. That is more")
        print("     basic than this section; register it and stop the residual.")
        return
    if a1 < a2:
        print("     FIRST BRANCH. col 3 CONTAINS the deferred balance, so")
        print("     `bal_ib = col 3 - col 12`. §8·14·5·2's 'unverified' is")
        print("     discharged and the residual instrument may go on.")
    else:
        print("     SECOND BRANCH. col 3 does NOT contain it, so")
        print("     `bal_ib = col 3` and `zib` needs another source.")
        print("     §8·14·5·2's WORDING changes; none of its readings do.")


def cmd_balid(only) -> int:
    vintages = only or VINTAGES
    print("§8·18: which column is V's interest-bearing balance. One identity,\n"
          "two hypotheses, P taken from the origination side. No omega.\n")
    acc = balid_new_acc()
    for v in vintages:
        if not archive(v).exists():
            print(f"  {v}  missing")
            continue
        orig, _ = read_orig(v)
        for seq, recs in loans(v):
            balid_absorb(acc, recs, orig.get(seq), v)
        print(f"  {v}  done   kept so far {acc['kept']:,}", flush=True)
    pl = balid_payload(acc)
    print_balid(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_balid.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "balid", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Decides only which "
             "column V's first factor is; writes no residual and no omega. P "
             "comes from the origination side so neither hypothesis is assumed "
             "in order to test it.",
         "sample_cap": BALID_SAMPLE_CAP, **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="§12.7, on constructed schedules, before any real row")
    ap.add_argument("--depth", action="store_true",
                    help="§12.6, the gate: enumerates and estimates nothing")
    ap.add_argument("--run", action="store_true", help="§12.4 and §12.5")
    ap.add_argument("--amort", action="store_true",
                    help="§2·5: ARM vs FRM asked as rate behaviour, not as a column")
    ap.add_argument("--phase", action="store_true",
                    help="§5·5: origination phase, and schedule+rounding vs observed")
    ap.add_argument("--zero-upb", action="store_true",
                    help="§5·4: name the age-0 rows whose perf UPB is 0.00")
    ap.add_argument("--grid-k", action="store_true",
                    help="§10·9·7: the precondition owed before the B8 handover")
    ap.add_argument("--defer", action="store_true",
                    help="§8·14: does V's zero-interest split have a basis here")
    ap.add_argument("--defer2", action="store_true",
                    help="§8·14·5: the same question with the reading's 'or' out")
    ap.add_argument("--balloon", action="store_true",
                    help="§8·14·6: the balloon horizon and its cross-check")
    ap.add_argument("--balloon2", action="store_true",
                    help="§8·14·6·5: the same anchor, stratified by term")
    ap.add_argument("--balloon3", action="store_true",
                    help="§8·14·6·6: both invariants side by side, no scan")
    ap.add_argument("--extend", action="store_true",
                    help="§8·14·6·7: is the 32.90% the re-set terms")
    ap.add_argument("--horizon", action="store_true",
                    help="§8·14·6·8: which horizon bn takes on this carrier")
    ap.add_argument("--balid", action="store_true",
                    help="§8·18: which column is V's interest-bearing balance")
    ap.add_argument("--only", type=int, action="append",
                    help="restrict to a vintage, repeatable")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.depth:
        return cmd_depth(a.only)
    if a.run:
        return cmd_run(a.only)
    if a.grid_k:
        return cmd_grid_k(a.only)
    if a.zero_upb:
        return cmd_zero_upb(a.only)
    if a.phase:
        return cmd_phase(a.only)
    if a.amort:
        return cmd_amort(a.only)
    if a.balid:
        return cmd_balid(a.only)
    if a.horizon:
        return cmd_horizon(a.only)
    if a.extend:
        return cmd_extend(a.only)
    if a.balloon3:
        return cmd_balloon3(a.only)
    if a.balloon2:
        return cmd_balloon2(a.only)
    if a.balloon:
        return cmd_balloon(a.only)
    if a.defer2:
        return cmd_defer2(a.only)
    if a.defer:
        return cmd_defer(a.only)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
