"""B10 / O18 follow-up: does the frozen balance carry a servicer's fingerprint?

Pre-registered in the B10 availability register §34, **before this file
was written**, and §34.0 voids one branch of §33.4's own reading first, for a
reason known before any number: Freddie's firm name sits on the origination
side, one value per loan, and servicing transfers. Attributing a 2015 frozen
month to the firm named at origination is wrong on every transferred loan, and
**attribution noise only pushes differences toward zero**. So the test can
confirm and cannot refute, and §33.4's "spread is ordinary, therefore the firm
is irrelevant" branch is gone.

Two confounds are handled by construction rather than by correction
-------------------------------------------------------------------
* **The calendar trend.** §33.3 measured the frozen rate falling from 18.08% to
  9.31% across the windows, so a firm concentrated in 2004-2007 reads high on
  vintage mix alone. Everything below is computed **inside one window**.
* **Within-loan dependence.** A loan contributes dozens of consecutive pairs and
  they are not independent; a per-pair standard error would call every
  difference significant. **The unit is the loan**: a loan's statistic is the
  share of its own pairs that are frozen, a firm's is the mean of those shares,
  and the standard error is their standard deviation over the root of the loan
  count. Clustering is structural here, not a post-hoc adjustment.

Earning the field
-----------------
C0b again, and the anchor is corporate history: **Countrywide stops appearing
after its 2008 acquisition.** A firm-name column has values whose vintage
support is bounded by real events. That anchor has nothing to do with whether a
balance moved, so the circle §32.1 avoided stays avoided.

Usage::

    python experiments/b10_o18_servicer.py --selftest
    python experiments/b10_o18_servicer.py --earn --only 2007
    python experiments/b10_o18_servicer.py --run

Writes ``results/b10_o18_servicer.json``, ``diagnostic_only``.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import statistics
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"

VINTAGE_RANGE = range(1999, 2027)
ORIG_FIELDS, PERF_FIELDS = 31, 35
O_SEQ = 19
P_SEQ, P_PERIOD, P_UPB = 0, 1, 2

WINDOWS = (("pre_crisis", 0, 2008), ("hamp", 2009, 2016), ("flex", 2017, 2019),
           ("covid", 2020, 2022), ("post2023", 2023, 9999))

#: §34.3. A firm below this many loans has a standard error dominated by its own
#: noise, because that standard error is a spread over the root of the loan
#: count. **Structural, not tuned.** Firms below it are pooled into one row and
#: the pooled count prints; they are not dropped.
MIN_LOANS = 200

#: §34.4's anchor. A firm-name column carries values whose vintage support is
#: cut off by real corporate history; this is the clearest such cut in the
#: sample. The anchor searches for **any** value with that shape and reports the
#: strongest, so the name below is a label for the reader, not a filter.
ACQUIRED_BEFORE = 2009

#: A value has to appear on this many loans before the last vintage it appears
#: in means anything. A code seen twice can "stop appearing" by chance.
MIN_VALUE_LOANS = 500

#: Appearance filter for §34.4: a firm-name column has many values and almost no
#: blanks. It enumerates and picks nothing (§25's rule).
FIRM_MIN_VALUES = 8
FIRM_MAX_BLANK = 0.1


def archive(v: int) -> Path:
    return RAW / f"sample_{v}.zip"


def vintages_on_disk() -> list:
    return [v for v in VINTAGE_RANGE if archive(v).exists()]


def _lines(zf, member):
    with zf.open(member) as raw:
        for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
            line = line.rstrip("\r\n")
            if line:
                yield line.split("|")


def window_of(period: int) -> str:
    y = period // 100
    for name, lo, hi in WINDOWS:
        if lo <= y <= hi:
            return name
    return "post2023"


def next_period(p: int) -> int:
    y, m = divmod(p, 100)
    return y * 100 + m + 1 if m < 12 else (y + 1) * 100 + 1


# ---------------------------------------------------------------------------
# §34.4: earning a firm-name column by corporate history.
# ---------------------------------------------------------------------------

def profile_orig(vintages) -> dict:
    """`col -> value -> set of vintages`, plus blanks. Appearance only."""
    seen = defaultdict(lambda: defaultdict(Counter))
    blank, rows = Counter(), 0
    for v in vintages:
        with zipfile.ZipFile(archive(v)) as zf:
            for f in _lines(zf, f"sample_orig_{v}.txt"):
                if len(f) < ORIG_FIELDS:
                    continue
                rows += 1
                for c in range(ORIG_FIELDS):
                    s = f[c].strip()
                    if s:
                        seen[c][s][v] += 1
                    else:
                        blank[c] += 1
    return {"seen": seen, "blank": blank, "rows": rows}


def firm_candidates(prof: dict) -> list:
    out = []
    for c, vals in prof["seen"].items():
        n = sum(sum(d.values()) for d in vals.values())
        tot = n + prof["blank"].get(c, 0)
        if not tot:
            continue
        if (len(vals) >= FIRM_MIN_VALUES
                and prof["blank"].get(c, 0) / tot <= FIRM_MAX_BLANK):
            out.append(c)
    return sorted(out)


#: The vintage axis has to reach this far past the cutoff before "stops at or
#: before {ACQUIRED_BEFORE}" says anything at all. On `--only 2007` every value
#: in every column stops in 2007, and the first version happily returned eleven
#: winning columns. **Same family as §25's anchor four printing DISAGREE when it
#: could not run**: a check that returns a verdict without the data to run on is
#: worse than one that returns nothing.
MIN_YEARS_AFTER_CUTOFF = 5


def anchor_corporate(prof: dict, cands, last_vintage: int) -> list:
    """Values that stop **abruptly** before the sample's end.

    "Stops early" alone does not identify a firm-name column: a note rate of 9%
    also stops appearing, and so does a 100% LTV. **The shape that separates
    them is abruptness.** A market variable fades out, so by its last active
    vintage its share is already a sliver of its peak; an acquired firm is
    writing a normal share of the book and then is gone. So each cut-off value
    is scored by

        abruptness = its share in its last active vintage / its peak share

    and a column is ranked by its best one. Nothing here is thresholded; the
    ranking is the instrument and the numbers print.

    A column is also required to carry at least one value that survives to the
    last vintage. A column where *everything* stops early is a column whose
    support ended, not a column of firms.
    """
    rows = []
    per_vint_tot = defaultdict(Counter)
    for c in cands:
        for val, vs in prof["seen"][c].items():
            for v, n in vs.items():
                per_vint_tot[c][v] += n
    for c in cands:
        survivors = sum(1 for vs in prof["seen"][c].values()
                        if max(vs) >= last_vintage - 1
                        and sum(vs.values()) >= MIN_VALUE_LOANS)
        cut = []
        for val, vs in prof["seen"][c].items():
            n = sum(vs.values())
            if n < MIN_VALUE_LOANS:
                continue
            last = max(vs)
            if last > ACQUIRED_BEFORE:
                continue
            shares = {v: k / max(1, per_vint_tot[c][v]) for v, k in vs.items()}
            peak = max(shares.values())
            ab = shares[last] / peak if peak else 0.0
            cut.append({"value": val[:38], "loans": n, "first": min(vs),
                        "last": last, "abruptness": round(ab, 4),
                        "last_share": round(shares[last], 4),
                        "peak_share": round(peak, 4)})
        cut.sort(key=lambda d: -d["abruptness"])
        rows.append({"col": c, "n_values": len(prof["seen"][c]),
                     "n_cut_off": len(cut), "survivors": survivors,
                     "best_abruptness": cut[0]["abruptness"] if cut else 0.0,
                     "time_ordering": time_ordering(prof["seen"][c]),
                     "biggest": cut[:4]})
    rows.sort(key=lambda d: (-(d["survivors"] > 0), -d["best_abruptness"]))
    return rows


def time_ordering(vals: dict) -> float:
    """How far the column's own value order tracks calendar time.

    **Abruptness alone still does not separate a firm from a date.** A date
    value exists at one instant by construction, so it stops at full size and
    scores 1.000; the first full run put a date column level with the firm
    column at exactly that score.

    What a date column has and a firm column does not is an **ordering**: sort
    the values and their mean vintage climbs with them. Sort firm names and it
    does not. This is a Spearman correlation between a value's rank in the
    column's own sorted order and its mean vintage, on the big values only.

    **It is reported, not used as a filter** (§34.7): the columns it marks as
    time-ordered are kept and run as **placebos**, because a partition of loans
    that has nothing to do with servicing is exactly what says whether a large
    `z` spread means servicing at all.
    """
    big = [(v, d) for v, d in vals.items() if sum(d.values()) >= MIN_VALUE_LOANS]
    if len(big) < 4:
        return float("nan")
    big.sort(key=lambda kv: kv[0])
    mean_vint = [sum(v * n for v, n in d.items()) / sum(d.values())
                 for _, d in big]
    n = len(big)
    order = sorted(range(n), key=lambda i: mean_vint[i])
    rank = [0] * n
    for r, i in enumerate(order):
        rank[i] = r
    xs = list(range(n))
    mx, my = (n - 1) / 2, (n - 1) / 2
    num = sum((a - mx) * (b - my) for a, b in zip(xs, rank))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs)
                    * sum((b - my) ** 2 for b in rank))
    return round(abs(num / den), 4) if den else float("nan")


# ---------------------------------------------------------------------------
# The measurement. Unit = loan, inside one window.
# ---------------------------------------------------------------------------

def scan_vintage(v: int, cols) -> dict:
    """`(window, col, firm) -> [per-loan frozen shares]` for one vintage."""
    firm = {}
    with zipfile.ZipFile(archive(v)) as zf:
        for f in _lines(zf, f"sample_orig_{v}.txt"):
            if len(f) >= ORIG_FIELDS:
                firm[f[O_SEQ]] = tuple(f[c].strip() for c in cols)

    out = defaultdict(list)
    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as raw:
            seq, rows = None, []

            def flush(sq, rr):
                if not sq or len(rr) < 2:
                    return
                names = firm.get(sq)
                if names is None:
                    return
                per_win = defaultdict(lambda: [0, 0])
                for i in range(1, len(rr)):
                    p0, u0 = rr[i - 1]
                    p1, u1 = rr[i]
                    if p1 != next_period(p0) or not (u0 > 0 and u1 > 0):
                        continue
                    w = per_win[window_of(p1)]
                    w[1] += 1
                    if u0 == u1:
                        w[0] += 1
                for win, (fz, tot) in per_win.items():
                    if tot:
                        for k, c in enumerate(cols):
                            out[(win, c, names[k])].append(fz / tot)

            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.split("|", 4)
                if f[P_SEQ] != seq:
                    flush(seq, rows)
                    seq, rows = f[P_SEQ], []
                try:
                    rows.append((int(f[P_PERIOD]), float(f[P_UPB])))
                except ValueError:
                    pass
            flush(seq, rows)
    return out


def firm_table(shares: dict, win: str, col: int) -> dict:
    """§34.2's `z` per firm, plus §34.3's concentration, inside one window."""
    per_firm = {name: v for (w, c, name), v in shares.items()
                if w == win and c == col and name}
    n_loans = {k: len(v) for k, v in per_firm.items()}
    total = sum(n_loans.values())
    if not total:
        return {"window": win, "col": col, "loans": 0}
    allv = [x for v in per_firm.values() for x in v]
    mu = statistics.fmean(allv)

    big = [k for k, n in n_loans.items() if n >= MIN_LOANS]
    small = [k for k in per_firm if k not in big]
    rows, zs = [], []
    for k in sorted(big, key=lambda k: -n_loans[k]):
        v = per_firm[k]
        m = statistics.fmean(v)
        sd = statistics.pstdev(v)
        se = sd / math.sqrt(len(v)) if len(v) > 1 else float("nan")
        z = (m - mu) / se if se and se == se and se > 0 else float("nan")
        rows.append({"firm": k[:34], "loans": len(v), "mean": round(m, 5),
                     "se": round(se, 6), "z": round(z, 2)})
        if z == z:
            zs.append(z)
    top5 = sum(sorted(n_loans.values(), reverse=True)[:5]) / total
    return {
        "window": win, "col": col, "loans": total, "grand_mean": round(mu, 5),
        "firms_total": len(per_firm), "firms_read": len(big),
        "loans_read": sum(n_loans[k] for k in big),
        "firms_pooled_small": len(small),
        "loans_pooled_small": sum(n_loans[k] for k in small),
        "top5_share": round(top5, 4),
        "z_sd": round(statistics.pstdev(zs), 3) if len(zs) > 1 else None,
        "z_p10_p50_p90": ([round(x, 2) for x in
                           statistics.quantiles(zs, n=10)[::4]]
                          if len(zs) >= 10 else None),
        "rows": rows[:12],
    }


#: How many columns the anchor may hand on. §34.4 says run every column that
#: shows the shape, and Freddie publishes a seller name and a servicer name, so
#: two is the expected answer. More than this means the anchor did not
#: discriminate and the run stops rather than measuring eleven columns.
MAX_FIRM_COLS = 3


def cmd_earn(only, verbose=True):
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    span_ok = max(vs) >= ACQUIRED_BEFORE + MIN_YEARS_AFTER_CUTOFF
    if not span_ok:
        print(f"§34.4 cannot run: the vintage axis is {vs[0]}..{vs[-1]} and the "
              f"anchor needs it to reach at least "
              f"{ACQUIRED_BEFORE + MIN_YEARS_AFTER_CUTOFF}.")
        print("  On a short axis every value 'stops before the cutoff' and the "
              "anchor returns\n  everything. **Not measurable, not a verdict.**")
        return []
    prof = profile_orig(vs)
    cands = firm_candidates(prof)
    rows = anchor_corporate(prof, cands, max(vs))
    won = [r["col"] for r in rows
           if r["n_cut_off"] > 0 and r["survivors"] > 0][:MAX_FIRM_COLS]
    if verbose:
        print(f"§34.4, earning a firm-name column. {prof['rows']:,} orig rows, "
              f"vintages {vs[0]}..{vs[-1]}.")
        print(f"  candidates by appearance (>= {FIRM_MIN_VALUES} values, "
              f"<= {FIRM_MAX_BLANK:.0%} blank): {cands}\n")
        print(f"  anchor: a value that stops at or before {ACQUIRED_BEFORE} "
              f"**abruptly** -- its share in its\n  last active vintage against "
              f"its peak share. A market variable fades; a firm is\n  writing a "
              f"normal share of the book and then is gone.")
        for r in rows[:6]:
            print(f"    col {r['col']:>3}  {r['n_values']:>5} values   "
                  f"{r['n_cut_off']:>3} cut off   {r['survivors']:>3} survive "
                  f"to the end   abruptness {r['best_abruptness']:.4f}   "
                  f"time-ordering {r['time_ordering']}")
            for b in r["biggest"][:3]:
                print(f"        {b['value']:<40} {b['loans']:>7,} loans  "
                      f"{b['first']}..{b['last']}  share {b['last_share']:.4f}"
                      f" vs peak {b['peak_share']:.4f}  ab {b['abruptness']:.3f}")
        by_col = {r["col"]: r for r in rows}
        print(f"\n  earned: {won}")
        print("  §34.7: time-ordering says which of these is a firm and which "
              "is a calendar.\n  The calendars are kept and run as **placebos**"
              ", because a partition of loans with\n  nothing to do with "
              "servicing is what says whether a large z spread means\n  "
              "servicing at all.")
        for c in won:
            to = by_col[c]["time_ordering"]
            kind = ("placebo (calendar)" if to == to and to > 0.9
                    else "firm candidate" if to == to and to < 0.5
                    else "unclear, run and label as unclear")
            print(f"    col {c:>3}  time-ordering {to}  ->  {kind}")
        if not won:
            print("    **none.** §34.4 stops here; do not widen the filter.")
        elif len(won) > 1:
            print("    more than one, so §34.4's rule applies: **run every one "
                  "and report every one.**\n    Freddie publishes both a seller "
                  "and a servicer name and this file does not\n    separate "
                  "them (§34.4).")
    return won


def cmd_run(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    cols = cmd_earn(only, verbose=True)
    if not cols:
        print("\n  No firm-name column earned. No measurement is printed.")
        return 1

    shares = defaultdict(list)
    for v in vs:
        for k, val in scan_vintage(v, cols).items():
            shares[k].extend(val)
        print(f"  scanned {v}")

    out = {"columns": cols, "min_loans": MIN_LOANS, "windows": {}}
    print(f"\n{'=' * 78}\n  §34.2. Unit = loan, inside one window. "
          f"z is (firm mean - window mean) / firm se.\n"
          f"  Under sampling alone z has a standard deviation of 1.\n"
          f"  **One-sided (§34.0): a large spread confirms, a small one cannot "
          f"refute.**\n{'=' * 78}")
    for col in cols:
        for name, _, _ in WINDOWS:
            t = firm_table(shares, name, col)
            out["windows"][f"col{col}|{name}"] = t
            if not t.get("loans"):
                continue
            zsd = t["z_sd"]
            verdict = ("no firms clear the floor" if t["firms_read"] < 2
                       else "z spread NOT ordinary -> firms really do differ"
                       if zsd and zsd > 3 else
                       "z spread near 1 -> **cannot refute** (§34.0), record "
                       "as unread")
            print(f"\n  col {col}  {name}   loans {t['loans']:,}   "
                  f"mean frozen share {t['grand_mean']}")
            print(f"    firms {t['firms_total']}, read {t['firms_read']} "
                  f"(>= {MIN_LOANS} loans, {t['loans_read']:,} loans), pooled "
                  f"small {t['firms_pooled_small']} "
                  f"({t['loans_pooled_small']:,} loans)")
            print(f"    top-5 share of loans {t['top5_share']:.1%}   "
                  f"z sd {zsd}   z p10/p50/p90 {t['z_p10_p50_p90']}")
            print(f"    -> {verdict}")
            for r in t["rows"][:6]:
                print(f"       {r['firm']:<36} loans {r['loans']:>7,}  "
                      f"mean {r['mean']:.5f}  z {r['z']:>9.2f}")

    print("\n  §34.2's three readings, written before these numbers:")
    print("    z sd far above 1   -> firms really differ; these months carry an "
          "accounting fingerprint\n                          and O18's 'why' "
          "has a direction: a reporting artefact, not a borrower state")
    print("    z sd near 1        -> **cannot refute** (§34.0). Attribution "
          "noise from servicing transfers\n                          and "
          "residual vintage mix both push toward zero. Record as unread.")
    print("    one or two outliers-> that is those firms' practice, not a "
          "general one. Name them,\n                          report their "
          "share of the window, **do not generalise**")
    print("\n  §34.5: this does not transfer to Fannie, and this file cannot "
          "see servicing\n  transfers at all -- Freddie's standard performance "
          "file carries no servicer column.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / "b10_o18_servicer.json"
    p.write_text(json.dumps(
        {"stage": "B10", "step": "o18_servicer", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §34. One-sided by "
             "construction (§34.0). No omega, no B8 prediction.",
         "one_sided_caveat":
             "Firm name is an origination-side field and servicing transfers; "
             "attribution noise attenuates. A small spread cannot refute.",
         **out}, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {p.relative_to(ROOT)}")
    return 0


def cmd_selftest() -> int:
    print("b10_o18_servicer selftest. Constructed cases, answers first.\n")
    fails = []

    def chk(name, got, want):
        ok = got == want
        print(f"  {name:<52} {str(got):<18} {'ok' if ok else f'FAIL {want}'}")
        if not ok:
            fails.append(name)

    print("  window_of and period arithmetic:")
    for p, w in ((200812, "pre_crisis"), (200901, "hamp"), (201701, "flex"),
                 (202001, "covid"), (202301, "post2023")):
        chk(f"    {p}", window_of(p), w)
    chk("    next_period rolls the year", next_period(200812), 200901)

    print("\n  anchor_corporate: abruptness, not merely stopping:")
    # col 1: a firm that vanishes at full size, beside one that survives
    # col 2: a market variable that fades out before it stops
    fade = Counter({v: max(1, 300 - 30 * (v - 1999)) for v in range(1999, 2009)})
    prof = {"seen": {1: {"ACQUIRED 2008": Counter({v: 300 for v in
                                                   range(1999, 2009)}),
                         "STILL HERE": Counter({v: 300 for v in
                                                range(1999, 2026)}),
                         "TOO SMALL": Counter({2001: 10})},
                     2: {"FADES": fade,
                         "SURVIVES": Counter({v: 300 for v in
                                              range(1999, 2026)})}},
            "blank": Counter()}
    r = {x["col"]: x for x in anchor_corporate(prof, [1, 2], 2025)}
    chk("    the abrupt one scores near 1", r[1]["best_abruptness"] > 0.9, True)
    chk("    the fading one scores far lower",
        r[2]["best_abruptness"] < r[1]["best_abruptness"], True)
    chk("    the acquired value is named", r[1]["biggest"][0]["value"],
        "ACQUIRED 2008")
    chk("    a value on 10 loans is not read",
        all(b["value"] != "TOO SMALL" for b in r[1]["biggest"]), True)
    chk("    both columns have a survivor", (r[1]["survivors"],
                                             r[2]["survivors"]), (1, 1))
    # a column where everything stops early is not a firm column
    prof2 = {"seen": {3: {f"V{k}": Counter({v: 300 for v in range(1999, 2009)})
                          for k in range(4)}}, "blank": Counter()}
    chk("    a column with no survivor is ranked last",
        anchor_corporate(prof2, [3], 2025)[0]["survivors"], 0)
    print("    (\"stops early\" alone does not identify anything: a 9% note "
          "rate and a\n     100% LTV also stop appearing. Abruptness is what "
          "separates them.)")

    print("\n  time_ordering: abruptness alone still cannot tell a firm from a "
          "calendar")
    cal = {f"{y}{mo:02d}": Counter({y: 600}) for y in range(1999, 2020)
           for mo in (3, 9)}
    names = ["ZETA", "ALPHA", "MIKE", "BRAVO", "YANKEE", "CHARLIE", "XRAY",
             "DELTA"]
    spans = [(1999, 2019), (2005, 2019), (1999, 2010), (2010, 2019),
             (1999, 2019), (1999, 2004), (2002, 2019), (1999, 2019)]
    firm = {n: Counter({v: 600 for v in range(a, b + 1)})
            for n, (a, b) in zip(names, spans)}
    chk("    a calendar column reads 1.0", time_ordering(cal), 1.0)
    chk("    a firm column reads far below it", time_ordering(firm) < 0.5, True)
    chk("    too few big values reads nan",
        time_ordering({"a": Counter({2000: 600})}) != time_ordering(
            {"a": Counter({2000: 600})}), True)
    print("    (a date value exists at one instant by construction, so it "
          "stops at full\n     size and scores abruptness 1.000. The first full "
          "run put a date column\n     level with the firm column at exactly "
          "that score. §34.7 keeps the\n     calendars and runs them as "
          "placebos rather than filtering them out.)")

    print("\n  firm_table, unit = loan and clustering by construction:")
    sh = {}
    sh[("hamp", 1, "A")] = [0.10] * 400
    sh[("hamp", 1, "B")] = [0.30] * 400
    sh[("hamp", 1, "TINY")] = [0.99] * 5
    t = firm_table(sh, "hamp", 1)
    chk("    both big firms are read", t["firms_read"], 2)
    chk("    the tiny one is pooled, not dropped", t["firms_pooled_small"], 1)
    chk("    and its loans are counted", t["loans_pooled_small"], 5)
    chk("    the grand mean includes everyone", round(t["grand_mean"], 4),
        round((0.10 * 400 + 0.30 * 400 + 0.99 * 5) / 805, 4))
    sh2 = {("hamp", 1, "A"): [0.10 + 0.001 * (i % 7) for i in range(400)],
           ("hamp", 1, "B"): [0.30 + 0.001 * (i % 7) for i in range(400)]}
    t2 = firm_table(sh2, "hamp", 1)
    chk("    two firms 20 points apart give a huge z spread",
        t2["z_sd"] > 100, True)
    sh3 = {("hamp", 1, f"F{k}"): [0.20 + 0.001 * (i % 11) for i in range(400)]
           for k in range(6)}
    t3 = firm_table(sh3, "hamp", 1)
    chk("    six identical firms give a z spread near zero",
        t3["z_sd"] < 1.0, True)
    print("    (the third case is the null: identical firms, and the statistic\n"
          "     does not manufacture a difference out of within-loan noise)")

    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--earn", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", action="append")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.earn:
        cmd_earn(a.only)
        return 0
    if a.run:
        return cmd_run(a.only)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
