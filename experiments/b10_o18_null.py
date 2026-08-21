"""B10 / O18: the null nobody tested. Does the balance sit still because nobody paid?

Pre-registered in the B10 availability register §41, **before this file
was written**, and §41.0 says the thing that has to be said first: four
instruments ran on O18 before this one, and none of them crossed the frozen
month against the delinquency field. **The plainest explanation of a balance
that does not move is that nobody paid**, and it was never tested.

Why the criterion is a difference and not a level
--------------------------------------------------
The delinquency field is **cumulative**: a borrower three months behind who
remits one instalment can still read 3, or drop to 2. So "is this month
delinquent" cannot answer "was this month paid". The difference can:

    delta = delinq(t) - delinq(t-1)

* ``+1``  one instalment short. §18 measured that this counter runs in 30-day
  buckets rather than calendar months, so a single bucket is a single miss.
* ``<= 0``  at least one instalment went in, level or catching up.
* ``>= +2``  §18's catch-up reporting, 30-day buckets against 31-day months.
  A third population, reported apart.

Where the main table runs
-------------------------
§40 已 assigned 55.3% of frozen months to the $1,000 disclosure grid at ages 0
to 6 and 2.07% to the assistance codes. **What has no name is the 3,778,406
months at age >= 8 carrying no code**, so the main table runs there and the
whole-population table prints beside it as a control.

The check that can overturn §38
--------------------------------
§41.2.1: if the grid explanation holds, the age <= 7 frozen months should be
**mostly ``delta <= 0``** -- the borrower is paying and the thousand-dollar grid
is hiding two or three hundred dollars of principal. **If that population is
mostly ``delta = +1`` instead, the grid explanation is in trouble**, because it
presumes payment. That route is left open on purpose.

Usage::

    python experiments/b10_o18_null.py --selftest
    python experiments/b10_o18_null.py --run --only 2007
    python experiments/b10_o18_null.py --run
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"

VINTAGE_RANGE = range(1999, 2027)
P_SEQ, P_PERIOD, P_UPB, P_DELINQ, P_AGE = 0, 1, 2, 3, 4

#: Earned in §33 by two behavioural anchors that never looked at the balance.
P_ASSIST = 29
ASSIST_CODES = ("F", "R", "T")

#: §40's split, unchanged. §11.3 measured the grid at ages 0 to 6 and §13 set
#: the first usable difference at 7 -> 8 for the same reason.
AGE_SPLIT = 8

#: §26.0's `digits` reading, settled against §3 on twenty-seven vintages: a
#: delinquency value is two digits, so `RA` and the blanks are not statuses and
#: get their own count rather than a number.
def parse_delinq(s: str):
    s = s.strip()
    return int(s) if len(s) == 2 and s.isdigit() else None


def archive(v: int) -> Path:
    return RAW / f"sample_{v}.zip"


def vintages_on_disk() -> list:
    return [v for v in VINTAGE_RANGE if archive(v).exists()]


def next_period(p: int) -> int:
    y, m = divmod(p, 100)
    return y * 100 + m + 1 if m < 12 else (y + 1) * 100 + 1


def delta_bucket(d: int) -> str:
    """§41.1's three buckets. A partition of the integers, so it is exhaustive."""
    if d >= 2:
        return "ge+2"
    if d == 1:
        return "+1"
    return "le0"


def population_of(age_ok: bool, coded: bool) -> str:
    """§41.2: the residue is the population with no name yet."""
    if not age_ok:
        return "grid_age_lt8"
    return "coded_age_ge8" if coded else "residue"


def scan_vintage(v: int) -> Counter:
    """`(population, frozen, bucket) -> n`, plus the unparsable count."""
    out = Counter()
    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as raw:
            seq, prev = None, None
            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.rstrip("\r\n").split("|")
                if f[P_SEQ] != seq:
                    seq, prev = f[P_SEQ], None
                try:
                    per = int(f[P_PERIOD])
                    upb = float(f[P_UPB])
                    age = int(f[P_AGE])
                except (ValueError, IndexError):
                    prev = None
                    continue
                # not `raw`: that name is the open zip member above, and
                # rebinding it inside the loop is a trap even where it happens
                # not to bite (the TextIOWrapper is already constructed).
                dq_raw = f[P_DELINQ].strip().upper()
                dq = parse_delinq(dq_raw)
                code = f[P_ASSIST].strip() if len(f) > P_ASSIST else ""
                cur = (per, upb, age, dq, code, dq_raw)
                if prev is not None:
                    p0, u0, a0, d0, _, raw0 = prev
                    if per == next_period(p0) and u0 > 0 and upb > 0:
                        frozen = "frozen" if u0 == upb else "moving"
                        pop = population_of(a0 >= AGE_SPLIT and age >= AGE_SPLIT,
                                            code in ASSIST_CODES)
                        if d0 is None or dq is None:
                            # §41.1 registered "`RA` and blanks counted apart"
                            # and the first version lumped them into one
                            # `unparsable` bucket. On 2007 that bucket is 6.18%
                            # of the very population O18 is about, which is too
                            # much of the object of study to leave unlabelled.
                            bad = [r for r, x in ((raw0, d0), (dq_raw, dq))
                                   if x is None]
                            out[(pop, frozen, "RA" if "RA" in bad
                                 else "blank_or_other")] += 1
                        else:
                            out[(pop, frozen, delta_bucket(dq - d0))] += 1
                prev = cur
    return out


BUCKETS = ("+1", "le0", "ge+2", "RA", "blank_or_other")


def table(acc: Counter, pop: str, frozen: str) -> dict:
    row = {b: acc[(pop, frozen, b)] for b in BUCKETS}
    tot = sum(row.values())
    return {"n": tot, "counts": row,
            "shares": {b: (row[b] / tot if tot else float("nan"))
                       for b in BUCKETS}}


def print_table(name: str, t: dict, note: str = "") -> None:
    print(f"    {name:<22} n {t['n']:>12,}   "
          + "  ".join(f"{b} {t['shares'][b]:>7.3%}" for b in BUCKETS)
          + (f"   {note}" if note else ""))


def cmd_run(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    acc = Counter()
    for v in vs:
        acc.update(scan_vintage(v))
        fz = sum(n for (_, f, _), n in acc.items() if f == "frozen")
        print(f"  scanned {v}   frozen so far {fz:>11,}")

    print(f"\n{'=' * 88}\n  §41.1. delta = delinq(t) - delinq(t-1). The counter "
          f"is cumulative, so a level\n  cannot answer 'was this month paid' and "
          f"a difference can.\n{'=' * 88}")

    out = {"populations": {}}
    print("\n  --- §41.2's main table: the residue, age >= 8 and no assistance "
          "code ---")
    for fr in ("frozen", "moving"):
        t = table(acc, "residue", fr)
        out["populations"][f"residue|{fr}"] = t
        print_table(f"residue / {fr}", t,
                    "<- the population O18 is about" if fr == "frozen" else "")

    print("\n  --- control: every population, frozen ---")
    for pop in ("grid_age_lt8", "coded_age_ge8", "residue"):
        t = table(acc, pop, "frozen")
        out["populations"][f"{pop}|frozen"] = t
        print_table(pop, t)
    print("\n  --- control: every population, moving ---")
    for pop in ("grid_age_lt8", "coded_age_ge8", "residue"):
        t = table(acc, pop, "moving")
        out["populations"][f"{pop}|moving"] = t
        print_table(pop, t)

    res = table(acc, "residue", "frozen")
    s = res["shares"]
    if s["+1"] > 0.5:
        v = ("§41.3 row one: **the null holds.** The residue is mostly a "
             "missed instalment. §32-§40's\n      numbers do not change and "
             "their wording does: they ran without this ruled out.")
    elif s["le0"] > 0.5:
        v = ("§41.3 row two: **the null fails.** By the counter the borrower "
             "paid and the balance still\n      did not move, so O18 really is "
             "about that, and the four instruments asked the right\n      "
             "question.")
    elif s["ge+2"] > 0.25:
        v = ("§41.3 row four: §18's catch-up reporting carries a large share. "
             "**A third population,\n      reported apart and not folded into "
             "either of the first two.**")
    else:
        v = ("§41.3 row three: **freezing is two things at once.** They must be "
             "quoted separately and\n      the four instruments' readings have "
             "to be re-read under that split.")
    print(f"\n  reading, written before the numbers:\n      {v}")

    grid = table(acc, "grid_age_lt8", "frozen")
    gs = grid["shares"]
    ok = gs["le0"] > gs["+1"]
    out["grid_check"] = {"le0": gs["le0"], "+1": gs["+1"],
                         "consistent_with_s38": bool(ok)}
    print(f"\n  --- §41.2.1: the check that can overturn §38 ---")
    print(f"    age <= 7 frozen months: delta <= 0 {gs['le0']:.3%}, "
          f"delta = +1 {gs['+1']:.3%}")
    print("    -> " + ("consistent with §38: the borrower is paying and the "
                       "thousand-dollar grid\n       hides it"
                       if ok else
                       "**INCONSISTENT with §38.** The grid explanation "
                       "presumes payment, and this\n       population is "
                       "mostly a missed instalment. Go back and check §38."))

    print("\n  §41.4: delta = +1 is a reporting fact. **Why an instalment was "
          "short is another\n  question and this file does not answer it.** "
          "Nothing here transfers to Fannie.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / "b10_o18_null.json"
    p.write_text(json.dumps(
        {"stage": "B10", "step": "o18_null", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §41. Counts only; "
             "no omega, no B8 prediction; does not transfer to Fannie (§41.4).",
         "age_split": AGE_SPLIT, "assist_col": P_ASSIST,
         "buckets": list(BUCKETS), **out},
        indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {p.relative_to(ROOT)}")
    return 0


def cmd_selftest() -> int:
    print("b10_o18_null selftest. Constructed cases, answers first.\n")
    fails = []

    def chk(name, got, want):
        ok = got == want
        print(f"  {name:<52} {str(got):<18} {'ok' if ok else f'FAIL {want}'}")
        if not ok:
            fails.append(name)

    print("  parse_delinq, §26.0's `digits` reading:")
    for s, w in (("00", 0), ("01", 1), ("98", 98), ("RA", None), ("", None),
                 (" 03 ", 3), ("3", None), ("100", None)):
        chk(f"    {s!r}", parse_delinq(s), w)
    print("    ('3' is one digit and '100' is three; the field is two digits\n"
          "     wide and anything else is not a status)")

    print("\n  delta_bucket is a partition of the integers:")
    for d, w in ((-5, "le0"), (-1, "le0"), (0, "le0"), (1, "+1"), (2, "ge+2"),
                 (37, "ge+2")):
        chk(f"    delta = {d}", delta_bucket(d), w)
    chk("    every integer lands somewhere",
        len({delta_bucket(d) for d in range(-50, 51)}), 3)

    print("\n  population_of, §41.2's split:")
    chk("    below the grid", population_of(False, False), "grid_age_lt8")
    chk("    below the grid, coded, still the grid",
        population_of(False, True), "grid_age_lt8")
    chk("    past it and coded", population_of(True, True), "coded_age_ge8")
    chk("    past it and bare is the residue",
        population_of(True, False), "residue")
    print("    (a coded month below the grid counts as grid, matching §40's\n"
          "     2 x 2 where the overlap cell `a` sits in the age column)")

    print("\n  table and the printer, actually called (MEASUREMENT mode 16):")
    acc = Counter({("residue", "frozen", "+1"): 700,
                   ("residue", "frozen", "le0"): 250,
                   ("residue", "frozen", "ge+2"): 40,
                   ("residue", "frozen", "RA"): 7,
                   ("residue", "frozen", "blank_or_other"): 3})
    t = table(acc, "residue", "frozen")
    chk("    n is the sum", t["n"], 1000)
    chk("    the +1 share", round(t["shares"]["+1"], 3), 0.7)
    chk("    shares sum to one",
        round(sum(t["shares"].values()), 9), 1.0)
    chk("    an empty cell is nan, not zero",
        table(Counter(), "residue", "frozen")["shares"]["+1"] !=
        table(Counter(), "residue", "frozen")["shares"]["+1"], True)
    print_table("residue / frozen", t, "<- printer exercised")
    chk("    and it serialises", "shares" in json.dumps(t, default=str), True)
    print("    (mode 16: a syntax check cannot prove a line runs. This calls\n"
          "     the printer and the serialiser, because that is where the last\n"
          "     one blew up after a 74.9M-row scan)")

    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", action="append")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.run:
        return cmd_run(a.only)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
