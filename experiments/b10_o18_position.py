"""B10 / O18: does a pair's position in its own loan explain the frozen balance?

Pre-registered in the B10 availability register §36, **before this file
was written**.

Where the question comes from
-----------------------------
§35.4 is arithmetic, not inference. The per-loan mean frozen share (0.146 to
0.286 by window) sits stably above the pooled per-pair rate (0.093 to 0.181),
by **1.37 to 1.62 in every window**, and the only thing that can mean is that
**loans with fewer pairs freeze more**. So the thing to ask is position: where
in a loan's own reporting sequence does a frozen month sit.

**Everything this file needs is in the reporting sequence itself.** No external
field is earned, so there is no attribution noise, no servicing transfer, and
none of the three rounds §34 spent discovering its field was the wrong shape.

Two confounds, both handled by stratifying rather than by correcting
--------------------------------------------------------------------
* **Length.** §35.4 just measured that short loans freeze more, and a short
  loan's pairs are nearly all "start" and "end" by construction. Comparing
  positions without stratifying compares lengths. So the comparison happens
  **inside a band of loans with the same number of pairs**, where every loan
  contributes the same count to each bucket.
* **Calendar.** §33.3 measured the frozen rate falling over time, and a loan's
  end is later than its start. That pushes the end **down**, so an end that
  still reads high is reading high against the confound; an end that reads low
  cannot be used to deny the effect. **One-sided, and in the useful direction.**
  The per-window table prints anyway.

And one population split that is not a confound but a distinction
-----------------------------------------------------------------
A loan's last month is either a payoff, a sale, an REO disposition or a
repurchase, **or** it is the archive running out. §36.2: those are not the same
end. A loan is terminated here when any row carries a zero balance code, which
`b10_c8_1d_freddie.py` already reads at `P_ZEROBAL` and §2 enumerated.

Usage::

    python experiments/b10_o18_position.py --selftest
    python experiments/b10_o18_position.py --run --only 2007
    python experiments/b10_o18_position.py --run
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"

VINTAGE_RANGE = range(1999, 2027)
P_SEQ, P_PERIOD, P_UPB = 0, 1, 2
P_AGE = 4
P_ZEROBAL = 8

#: §37.3's discriminant. §11.3 measured that Current Actual UPB is rounded to
#: the nearest $1,000 for loan ages 0 to 6 and reported to the cent from age 7,
#: and a thirty-year loan retires two or three hundred dollars of principal a
#: month early on. **So the first months can report the same rounded thousand
#: several times over, and the balance looks frozen because the disclosure
#: cannot see the payment, not because there was none.** `--min-age 8` is §13's
#: `MIN_AGE`, same number and same reason: age 7 is the first cent-reported
#: month, so the 6->7 step mixes a rounded side with an exact one and the first
#: usable difference is 7 -> 8.
DEFAULT_MIN_AGE = 8

WINDOWS = (("pre_crisis", 0, 2008), ("hamp", 2009, 2016), ("flex", 2017, 2019),
           ("covid", 2020, 2022), ("post2023", 2023, 9999))

#: §36.3. Three at each end, so a loan needs seven pairs before a middle
#: exists at all. **Structural**: with six or fewer the middle is empty and the
#: comparison has no second term.
EDGE = 3
MIN_PAIRS = 2 * EDGE + 1

#: Length bands, in pairs. The lower edge is `MIN_PAIRS` and the rest double,
#: the same shape as §12.5's segment bands. Loans below the floor are counted
#: and reported on their own (§36.3) rather than dropped: they are exactly the
#: population §35.4 pointed at.
BANDS = ((7, 12), (13, 24), (25, 60), (61, 120), (121, 10 ** 9))

POSITIONS = ("start", "middle", "end")


def archive(v: int) -> Path:
    return RAW / f"sample_{v}.zip"


def vintages_on_disk() -> list:
    return [v for v in VINTAGE_RANGE if archive(v).exists()]


def next_period(p: int) -> int:
    y, m = divmod(p, 100)
    return y * 100 + m + 1 if m < 12 else (y + 1) * 100 + 1


def window_of(period: int) -> str:
    y = period // 100
    for name, lo, hi in WINDOWS:
        if lo <= y <= hi:
            return name
    return "post2023"


def band_of(n: int):
    for lo, hi in BANDS:
        if lo <= n <= hi:
            return f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+"
    return None


def position_of(i: int, n: int) -> str:
    """`i` is zero-based among `n` pairs. §36.3's three buckets."""
    if i < EDGE:
        return "start"
    if i >= n - EDGE:
        return "end"
    return "middle"


def classify(rows, min_age: int = 0) -> dict:
    """One loan: its qualifying pairs, their positions, windows and frozenness.

    `rows` is ``[(period, upb, zerobal, age), ...]`` in file order. A pair
    qualifies when the periods are consecutive and both balances are positive,
    which is §32.2's definition unchanged.

    `min_age` applies §37.3's discriminant: **both** sides of the pair must be
    at or above it, because a pair spanning the grid boundary has one rounded
    balance and one exact one, which is the same trap §12.3 named on the 6 -> 7
    step. **Positions are computed after the filter**, so "start" means the
    start of what survives, and that is the point: if the grid is the whole
    story, the surviving start is no longer special.
    """
    pairs = []
    for i in range(1, len(rows)):
        p0, u0, _, a0 = rows[i - 1]
        p1, u1, _, a1 = rows[i]
        if p1 != next_period(p0) or not (u0 > 0 and u1 > 0):
            continue
        if min_age and (a0 < min_age or a1 < min_age):
            continue
        pairs.append((p1, u0 == u1))
    terminated = any(z for _, _, z, _ in rows)
    n = len(pairs)
    return {"n": n, "terminated": terminated,
            "pairs": [(position_of(i, n), window_of(p), fz)
                      for i, (p, fz) in enumerate(pairs)]}


def scan_vintage(v: int, min_age: int = 0) -> dict:
    out = {
        "loans": 0, "pairs": 0,
        # (band, terminated, position) -> [frozen, total]
        "cell": defaultdict(lambda: [0, 0]),
        # (band, terminated, position, window) -> [frozen, total]
        "cell_win": defaultdict(lambda: [0, 0]),
        # loans below the floor, §36.3
        "short_loans": 0, "short_pairs": 0, "short_frozen": 0,
        "short_by_n": defaultdict(lambda: [0, 0]),
        "terminated_loans": 0,
    }
    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as raw:
            seq, rows = None, []

            def flush(sq, rr):
                if sq is None or len(rr) < 2:
                    return
                c = classify(rr, min_age)
                out["loans"] += 1
                out["pairs"] += c["n"]
                if c["terminated"]:
                    out["terminated_loans"] += 1
                if c["n"] < MIN_PAIRS:
                    out["short_loans"] += 1
                    out["short_pairs"] += c["n"]
                    fz = sum(1 for _, _, f in c["pairs"] if f)
                    out["short_frozen"] += fz
                    s = out["short_by_n"][c["n"]]
                    s[0] += fz
                    s[1] += c["n"]
                    return
                b = band_of(c["n"])
                if b is None:
                    return
                for pos, win, fz in c["pairs"]:
                    k = (b, c["terminated"], pos)
                    out["cell"][k][1] += 1
                    out["cell_win"][(b, c["terminated"], pos, win)][1] += 1
                    if fz:
                        out["cell"][k][0] += 1
                        out["cell_win"][(b, c["terminated"], pos, win)][0] += 1

            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.split("|", 9)
                if f[P_SEQ] != seq:
                    flush(seq, rows)
                    seq, rows = f[P_SEQ], []
                try:
                    rows.append((int(f[P_PERIOD]), float(f[P_UPB]),
                                 bool(f[P_ZEROBAL].strip()), int(f[P_AGE])))
                except ValueError:
                    pass
            flush(seq, rows)
    return out


def merge(a, b):
    if a is None:
        return b
    for k in ("loans", "pairs", "short_loans", "short_pairs", "short_frozen",
              "terminated_loans"):
        a[k] += b[k]
    for k, v in b["cell"].items():
        a["cell"][k][0] += v[0]
        a["cell"][k][1] += v[1]
    for k, v in b["cell_win"].items():
        a["cell_win"][k][0] += v[0]
        a["cell_win"][k][1] += v[1]
    for k, v in b["short_by_n"].items():
        a["short_by_n"][k][0] += v[0]
        a["short_by_n"][k][1] += v[1]
    return a


def rate(pair):
    return pair[0] / pair[1] if pair[1] else float("nan")


def sign_table(acc, terminated: bool) -> dict:
    """§36.4: the sign of `end - middle` and `start - middle`, band by band."""
    rows, e_signs, s_signs = [], [], []
    for lo, hi in BANDS:
        b = f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+"
        r = {p: acc["cell"].get((b, terminated, p), [0, 0]) for p in POSITIONS}
        if min(v[1] for v in r.values()) == 0:
            rows.append({"band": b, "readable": False,
                         "n": {p: r[p][1] for p in POSITIONS}})
            continue
        rr = {p: rate(r[p]) for p in POSITIONS}
        de, ds = rr["end"] - rr["middle"], rr["start"] - rr["middle"]
        e_signs.append(de)
        s_signs.append(ds)
        rows.append({"band": b, "readable": True,
                     "rates": {p: round(rr[p], 5) for p in POSITIONS},
                     "n": {p: r[p][1] for p in POSITIONS},
                     "end_minus_middle": round(de, 5),
                     "start_minus_middle": round(ds, 5)})

    def verdict(xs):
        nz = [x for x in xs if x != 0.0]
        if len(nz) < 2:
            return "no_referent"
        if all(x > 0 for x in nz):
            return "all_positive"
        if all(x < 0 for x in nz):
            return "all_negative"
        return "mixed"

    return {"terminated": terminated, "rows": rows,
            "end_vs_middle": verdict(e_signs),
            "start_vs_middle": verdict(s_signs)}


def cmd_run(only, min_age: int = 0) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    acc = None
    for v in vs:
        acc = merge(acc, scan_vintage(v, min_age))
        print(f"  scanned {v}   loans {acc['loans']:>9,}   "
              f"pairs {acc['pairs']:>12,}")

    print(f"\n{'=' * 76}\n  §36.4. Position inside the loan's own sequence, "
          f"stratified by length.\n  Calendar pushes the end DOWN (§36.1), so a "
          f"high end reads against the confound\n  and a low end cannot deny "
          f"the effect. One-sided.\n{'=' * 76}")

    print(f"\n  §36.3's floor: loans with fewer than {MIN_PAIRS} pairs have no "
          f"middle and are not compared.")
    print(f"    {acc['short_loans']:,} loans, {acc['short_pairs']:,} pairs, "
          f"frozen {acc['short_frozen']:,} "
          f"({acc['short_frozen']/max(1,acc['short_pairs']):.4%})   "
          f"against {acc['pairs']:,} pairs overall")
    for n in sorted(acc["short_by_n"]):
        f_, t_ = acc["short_by_n"][n]
        print(f"      {n} pair(s): {t_:>10,}  frozen {f_/max(1,t_):>8.4%}")
    print(f"    **This is the population §35.4 pointed at, so its numbers "
          f"print rather than vanish.**")

    out = {"loans": acc["loans"], "pairs": acc["pairs"],
           "terminated_loans": acc["terminated_loans"],
           "short": {"loans": acc["short_loans"], "pairs": acc["short_pairs"],
                     "frozen": acc["short_frozen"],
                     "by_n": {str(k): v for k, v in acc["short_by_n"].items()}},
           "sign_tables": {}}

    for term in (True, False):
        t = sign_table(acc, term)
        out["sign_tables"]["terminated" if term else "still_reporting"] = t
        print(f"\n  --- {'terminated' if term else 'still reporting'} loans ---")
        print(f"    {'band':<8} {'start':>9} {'middle':>9} {'end':>9}   "
              f"{'end-mid':>9} {'start-mid':>10}   {'n(middle)':>11}")
        for r in t["rows"]:
            if not r["readable"]:
                print(f"    {r['band']:<8} not readable, some bucket is empty: "
                      f"{r['n']}")
                continue
            print(f"    {r['band']:<8} {r['rates']['start']:>9.5f} "
                  f"{r['rates']['middle']:>9.5f} {r['rates']['end']:>9.5f}   "
                  f"{r['end_minus_middle']:>+9.5f} "
                  f"{r['start_minus_middle']:>+10.5f}   {r['n']['middle']:>11,}")
        print(f"    end vs middle:   {t['end_vs_middle']}")
        print(f"    start vs middle: {t['start_vs_middle']}")

    et = out["sign_tables"]["terminated"]["end_vs_middle"]
    ec = out["sign_tables"]["still_reporting"]["end_vs_middle"]
    st = out["sign_tables"]["terminated"]["start_vs_middle"]
    if et == "all_positive" and ec != "all_positive":
        v = ("§36.4 row one: freezing piles up in the last months before a "
             "loan ends, and only\n      there. **That is a name for part of "
             "O18**: termination-adjacent reporting.")
    elif et == "all_positive" and ec == "all_positive":
        v = ("§36.4 row two: the end runs high whether or not the loan "
             "terminated, so it is the\n      **end of the sequence itself**, "
             "which looks more like the data cut. A name, but\n      not the "
             "same name.")
    elif st == "all_positive" and et != "all_positive":
        v = ("§36.4 row three: the **start** runs high, so this is a "
             "boarding artefact.")
    else:
        v = ("§36.4 row four: position does not explain it. **Then §35.4's "
             "1.37-1.62 is something\n      else and must not be explained "
             "anyway.**")
    print(f"\n  reading, written before the numbers:\n      {v}")

    print(f"\n  --- per calendar window (§36.4's last line) ---")
    winrows = {}
    for name, _, _ in WINDOWS:
        for term in (True, False):
            r = {p: [0, 0] for p in POSITIONS}
            for (b, t_, pos, w), v in acc["cell_win"].items():
                if w == name and t_ == term:
                    r[pos][0] += v[0]
                    r[pos][1] += v[1]
            if min(x[1] for x in r.values()) == 0:
                continue
            rr = {p: rate(r[p]) for p in POSITIONS}
            winrows[f"{name}|{'term' if term else 'open'}"] = {
                p: round(rr[p], 5) for p in POSITIONS}
            print(f"    {name:<11} {'term' if term else 'open':<5} "
                  f"start {rr['start']:.5f}  middle {rr['middle']:.5f}  "
                  f"end {rr['end']:.5f}   end-mid "
                  f"{rr['end']-rr['middle']:+.5f}")
    out["per_window"] = winrows
    print("    **Pooled across bands, so this table is the length confound "
          "again; it is here to\n    show the calendar shape, not to be read "
          "as a position effect** (§36.1).")

    RESULTS.mkdir(parents=True, exist_ok=True)
    tag = f"_age{min_age}" if min_age else ""
    p = RESULTS / f"b10_o18_position{tag}.json"
    p.write_text(json.dumps(
        {"stage": "B10", "step": "o18_position", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §36. Counts only; "
             "no omega, no B8 prediction. One-sided on the calendar (§36.1).",
         "edge": EDGE, "min_pairs": MIN_PAIRS, "min_age": min_age,
         "bands": [list(b) for b in BANDS], **out},
        indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {p.relative_to(ROOT)}")
    return 0


def cmd_selftest() -> int:
    print("b10_o18_position selftest. Constructed loans, answers first.\n")
    fails = []

    def chk(name, got, want):
        ok = got == want
        print(f"  {name:<54} {str(got):<22} {'ok' if ok else f'FAIL {want}'}")
        if not ok:
            fails.append(name)

    print("  position_of, and the floor that makes a middle exist:")
    chk("    7 pairs: three, one, three", [position_of(i, 7) for i in range(7)],
        ["start"] * 3 + ["middle"] + ["end"] * 3)
    chk("    6 pairs would have no middle",
        "middle" in [position_of(i, 6) for i in range(6)], False)
    chk("    MIN_PAIRS is that boundary", MIN_PAIRS, 7)

    print("\n  band_of:")
    for n, b in ((7, "7-12"), (12, "7-12"), (13, "13-24"), (60, "25-60"),
                 (121, "121+"), (99999, "121+"), (6, None)):
        chk(f"    {n}", band_of(n), b)

    print("\n  classify, on hand-built loans:")
    L = [(200001, 100.0, False, 1), (200002, 100.0, False, 2),
         (200003, 99.0, False, 3), (200004, 98.0, False, 4)]
    c = classify(L)
    chk("    three pairs from four rows", c["n"], 3)
    chk("    the first is frozen", [f for _, _, f in c["pairs"]],
        [True, False, False])
    chk("    and the loan is not terminated", c["terminated"], False)
    L2 = L + [(200005, 0.0, True, 5)]
    chk("    a zero-balance row marks termination",
        classify(L2)["terminated"], True)
    chk("    and it adds no pair, because a balance must be positive",
        classify(L2)["n"], 3)
    L3 = [(200001, 100.0, False, 1), (200003, 100.0, False, 3)]
    chk("    a calendar gap kills the pair", classify(L3)["n"], 0)
    chk("    min_age drops a pair with either side below it",
        classify(L, min_age=3)["n"], 1)
    chk("    and positions are computed after the filter",
        classify(L, min_age=3)["pairs"][0][0], "start")
    print("    (both sides must clear the age, because a pair straddling the\n"
          "     grid boundary has one rounded balance and one exact one --\n"
          "     the same trap §12.3 named on the 6 -> 7 step)")

    print("\n  sign_table verdicts:")
    acc = {"cell": defaultdict(lambda: [0, 0])}
    for lo, hi in BANDS:
        b = f"{lo}-{hi}" if hi < 10 ** 9 else f"{lo}+"
        acc["cell"][(b, True, "start")] = [100, 1000]
        acc["cell"][(b, True, "middle")] = [100, 1000]
        acc["cell"][(b, True, "end")] = [300, 1000]
    t = sign_table(acc, True)
    chk("    end above middle in every band", t["end_vs_middle"], "all_positive")
    chk("    start level with middle has no referent",
        t["start_vs_middle"], "no_referent")
    acc["cell"][("7-12", True, "end")] = [50, 1000]
    t2 = sign_table(acc, True)
    chk("    one band flipping makes it mixed", t2["end_vs_middle"], "mixed")
    acc2 = {"cell": defaultdict(lambda: [0, 0])}
    acc2["cell"][("7-12", True, "start")] = [1, 10]
    t3 = sign_table(acc2, True)
    chk("    an empty bucket is 'not readable', not a zero rate",
        t3["rows"][0]["readable"], False)
    print("    (the last one matters: a bucket with no pairs must not read as\n"
          "     a frozen rate of zero)")

    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", action="append")
    ap.add_argument("--min-age", type=int, default=0,
                    help=f"§37.3's discriminant; {DEFAULT_MIN_AGE} is §13's "
                         f"MIN_AGE and the same reason")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.run:
        return cmd_run(a.only, a.min_age)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
