"""B113: the discount window edge. Among banks of one size, where does the fed funds price of
those that have borrowed at the window sit against the primary credit rate, and where does
the price of those that have not?

The position is overnight borrowing by a depository institution, and its price is the size
arm's RC-K reading (`experiments/b59_size_spread.py`: the quarter's expense on fed funds
purchased and repo sold over their quarterly average, where repo is absent at both quarter
ends). That reading is a quarter's average rate on one filed line. The form lets the average
be taken over daily or over Wednesday closes, and repo inside the quarter is not seen, so it
is the overnight fed funds price where the balance was fed funds throughout and the filed
average is the balance the expense accrued on. Wherever this file says a filer paid above the
rate, it means that reading stands above the quarter's mean primary credit rate; `DEFINITIONS`
puts the same words in each record. The posted price is the primary credit rate, which 12 CFR 201.4(a) offers "as a backup
source of funding to a depository institution that is in generally sound financial condition
in the judgment of the Reserve Bank", secured under 201.3(a)(2).

The class is read from the loans themselves (`experiments/b113_dw_loans.py`). A loan names
its borrower by ABA routing number, and the Call Report's panel of reporters carries the
number of every filer, so a loan joins to a filer through the panel of the quarter the loan
was made in. That quarter matters: one number can belong to two filers in two quarters
after a merger, while inside a quarter no number names two filers. The panel prints the
number without its leading zeros, and it is padded back to nine characters. A borrower that
files no Call Report, a credit union above all, does not join, and those are counted apart.
A loan whose number names a filer in some other quarter's panel is counted first, whatever the
name says, since an institution can change charter and keep its number. Those loans may belong
to a filer the class then misses in a quarter it is read, which moves a difference between the
classes toward zero. A number in no panel at all belongs to an institution outside the Call
Report: a credit union by name, or the rest, a foreign bank's branch above all.

Two ways of writing the class are printed side by side:
  - ever: at least one primary credit loan between 2010Q3 and 2024Q2
  - near: a primary credit loan within four quarters either side of the quarter read, only
    where the whole window lies inside the loan data
Secondary and seasonal credit do not make a filer part of the class: secondary credit goes to
institutions not eligible for primary credit, and seasonal credit is a separate program.

Stage one prints the objects: the join, the class, and per size band and quarter how many
filers with a readable fed funds price are in it. Stage two prints what a primary credit loan
looks like: the amounts that recur, the terms, per year how many loans sit at the amount that
recurs most, and each class member's largest loan and largest pledged collateral against its
own total assets. Stage three prints, per band and quarter and for each way of writing the
class, how many filers have a price and what share of them paid more than the quarter's mean
primary credit rate, with no line drawn on any of it. Stage four reads the class difference:
inside each band and quarter the filers are cut by the rank of their assets, outside minus inside
is taken inside each piece and weighted into spans of quarters, the inside share standing as the
instrument's floor, and filers are resampled whole for the standard error under two seeds.
Criteria come after these are looked at. Stage nine asks what came in after 2020: over stretches that
split the years after the rate stepped down to the top of the target range (the zero bound, the year the range
rose, March 2023 to the end of the loan data, and after it) and year by year, it prints the objects under the
difference, the rate's height over the effective federal funds rate, how many prices the instrument's step or
its rounding decides, and the difference itself. With `--instrument` it reads the difference again on the
readings the instrument decides: those the step alone does not put above the rate, those the rounding decides,
and those both keep. With `--timing` it splits the ever class at the quarter read by when the edge was used:
in the four quarters up to it, only before those, or for the first time after it. With `--hikes` it reads those
writings again where the quarter's range of the rate decides the reading whichever way the balance ran inside the
quarter, alone and together with the step and the rounding; `--arms stable` keeps filer-quarters whose two
quarter-end balances sit near the quarterly average. `--write-after-2020` writes what those four print to their own
record, `results/b113_after_2020.json`: the objects over stretches and years, the timing objects, and the readings
under every filter on both arms, pooled below $10 billion. `--crossed` prints what B113-5 reads: the class
difference at two heights over the effective federal funds rate, where the primary credit rate stood before 2020
and where it has stood since, in a span on each side.

    python experiments/b113_discount_window.py --classes
    python experiments/b113_discount_window.py --loans
    python experiments/b113_discount_window.py --above
    python experiments/b113_discount_window.py --readings [--draws 500 --seeds 1 2]
    python experiments/b113_discount_window.py --crossing [--draws 2000 --seeds 1 2 --arms all]
    python experiments/b113_discount_window.py --instrument [--draws 2000 --seeds 1 2 --arms all]
    python experiments/b113_discount_window.py --timing [--draws 2000 --seeds 1 2 --arms all]
    python experiments/b113_discount_window.py --hikes [--draws 2000 --seeds 1 2 --arms all stable]
    python experiments/b113_discount_window.py --write-after-2020 --draws 4000 --seeds 1 2
    python experiments/b113_discount_window.py --crossed [--draws 2000 --seeds 1 2]
    python experiments/b113_discount_window.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import b59_call_report as drv  # noqa: E402
import b59_size_spread as s59  # noqa: E402
import b113_dw_loans as dwl  # noqa: E402

POR_CACHE = ROOT / "data" / "cache" / "b113_por_aba.json"
DW_FIRST, DW_LAST = "2010Q3", "2024Q2"
NEAR = 4
POR_WANT = ("IDRSSD", "Primary ABA Routing Number")
CU_RE = re.compile(r"(\bCU\b|\bFCU\b|CREDIT UNION)", re.I)


PCR_CSV = ROOT / "data" / "b59" / "DPCREDIT.csv"

#: the ways a filer-quarter is written into a class; the second pair splits the ever class
GROUPS = ("outside ever", "ever", "ever, never above the recurring amount", "ever, above it at least once",
          "outside near", "near")

#: stretches of quarters the description is pooled over: the rate stood 25 to 50 basis points above
#: the top of the target range until 2020-03-16 and at the top from then on; the loan data end in 2024Q2
SPANS = (("2010Q1", "2019Q4"), ("2020Q1", "2020Q1"), ("2020Q2", "2024Q2"), ("2024Q3", "2026Q2"), ("2014Q1", "2019Q4"))
#: the last span overlaps the first: from 2014 the list of problem banks was a fraction of its 2010 length,
#: so it reads the earlier stretch with fewer institutions outside primary credit's soundness test


def pcr_quarters(text: str) -> dict:
    """{quarter: (mean, low, high)} of the daily primary credit rate, percent a year, from DPCREDIT as FRED writes it."""
    rows = list(csv.reader(io.StringIO(text)))
    head = rows[0] if rows else []
    if head[1:] != ["DPCREDIT"]:
        raise ValueError(f"expected one DPCREDIT column, found {head}")
    per = collections.defaultdict(list)
    for r in rows[1:]:
        if len(r) < 2 or not r[1].strip():
            continue
        y, m = int(r[0][:4]), int(r[0][5:7])
        per[f"{y}Q{(m - 1) // 3 + 1}"].append(float(r[1]))
    return {q: (sum(v) / len(v), min(v), max(v)) for q, v in sorted(per.items())}


def above_cells(obs, pcr: dict, ever: set, by_q: dict, small_only: set) -> tuple[list, int]:
    """Per quarter, band and way of writing the class: filers with a readable fed funds price, and how
    many of them paid more than the quarter's mean primary credit rate. The near writing exists only
    where its window lies inside the loan data. A quarter the rate file does not cover is counted and
    left out."""
    cells = collections.defaultdict(lambda: [0, 0])
    near_cache, uncovered = {}, 0
    for r, price in obs:
        rate = pcr.get(r.period)
        if rate is None:
            uncovered += 1
            continue
        if r.period not in near_cache:
            near_cache[r.period] = near_class(r.period, by_q)
        nc = near_cache[r.period]
        if r.rssd in ever:
            groups = ["ever", GROUPS[2] if r.rssd in small_only else GROUPS[3]]
        else:
            groups = ["outside ever"]
        if nc is not None:
            groups.append("near" if r.rssd in nc else "outside near")
        band = s59.band_of(r.assets)
        for g in groups:
            cell = cells[(r.period, band, g)]
            cell[0] += 1
            cell[1] += price > rate[0]
    return ([{"quarter": q, "band": b, "group": g, "filers": v[0], "above": v[1]}
             for (q, b, g), v in sorted(cells.items())], uncovered)


#: how finely a band is cut by assets inside each quarter before the classes are compared; 1 is no cut
SIZE_SPLITS = (1, 2, 4)

#: the three bands below $10 billion read together: every paired bin of theirs enters this group as well
POOLED = "all below 10bn"

#: the half added to each count before taking log odds, so an empty count has a finite log
#: (Haldane 1956, Annals of Human Genetics 20; Anscombe 1956, Biometrika 43)
LOGIT_ADD = 0.5

#: the fed funds arms of the size arm the readings run on: every row, or both quarter ends holding fed funds
ARMS = ("all", "persistent")

#: the arms written to the record: the two above, and every row away from a secondary credit loan
RECORD_ARMS = ("all", "persistent", "away from secondary credit")

#: (name, the group outside, the group inside) of each way the class difference is read
WRITINGS = (("ever", "outside ever", "ever"), ("near", "outside near", "near"),
            ("ever, never above the recurring amount", "outside ever", GROUPS[2]),
            ("ever, above it at least once", "outside ever", GROUPS[3]))


def span_of(q: str):
    return next((i for i, (lo, hi) in enumerate(SPANS) if lo <= q <= hi), None)


def spans_of(q: str) -> list:
    return [i for i, (lo, hi) in enumerate(SPANS) if lo <= q <= hi]


def size_bins(members: list, k: int) -> dict:
    """{rssd: bin} for the (rssd, assets) of one band and quarter: ranked by assets, ties by id, cut into k runs of ranks."""
    order = sorted(members, key=lambda m: (m[1], m[0]))
    return {rssd: (i * k) // len(order) for i, (rssd, _a) in enumerate(order)}


def reading_entries(obs, pcr: dict, ever: set, by_q: dict, small_only: set, spans=SPANS, keep=None,
                    writings=WRITINGS, timing=None, cap_of=None) -> dict:
    """Every filer-quarter with a price, written into the cells the class difference is read from.

    A cell is (writing, band, span, size split, quarter, size bin, side), side 0 outside the class and
    1 inside. A pair is an outside and an inside cell that share everything else and both hold a filer;
    only pairs enter the difference, so a size bin with one side empty drops out. `spans` are the stretches the
    quarters are pooled over, the criteria's by default. `keep(r, price, rate)`, where given, leaves out every
    filer-quarter it refuses before the size bins are cut, so the bins rank only the filers read. `timing(q)`,
    where given, names each class member's timing group at q, or is None where the groups are undefined; a
    writing whose inside is a timing group is read only in quarters where they are defined. `cap_of(r, rate)`,
    where given, is the height a price is read against and `keep` is asked at; the quarter's mean rate otherwise."""
    rows, near_cache, timing_cache = [], {}, {}
    for r, price in obs:
        rate, ss = pcr.get(r.period), [i for i, (lo, hi) in enumerate(spans) if lo <= r.period <= hi]
        if rate is None or not ss:
            continue
        cap = rate[0] if cap_of is None else cap_of(r, rate)
        if keep is not None and not keep(r, price, cap):
            continue
        if r.period not in near_cache:
            near_cache[r.period] = near_class(r.period, by_q)
            timing_cache[r.period] = None if timing is None else timing(r.period)
        rows.append((r, price > cap, ss, near_cache[r.period], s59.band_of(r.assets)))
    by_qb = collections.defaultdict(list)
    for r, _ab, _s, _nc, b in rows:
        by_qb[(r.period, b)].append((r.rssd, r.assets))
    bins = {(q, b, k, rssd): bn for (q, b), mem in by_qb.items() for k in SIZE_SPLITS
            for rssd, bn in size_bins(mem, k).items()}
    filers = sorted({r.rssd for r, *_x in rows})
    fidx = {f: i for i, f in enumerate(filers)}
    keys, key_index, cell, who, above = [], {}, [], [], []
    for r, ab, ss, nc, b in rows:
        groups = {"ever", GROUPS[2] if r.rssd in small_only else GROUPS[3]} if r.rssd in ever else {"outside ever"}
        if nc is not None:
            groups.add("near" if r.rssd in nc else "outside near")
        tc = timing_cache[r.period]
        if tc is not None and r.rssd in tc:
            groups.add(tc[r.rssd])
            if tc[r.rssd] != TIMING_GROUPS[2]:
                groups.add(BY_THEN)
        for w, (_name, out_g, in_g) in enumerate(writings):
            if tc is None and (in_g in TIMING_GROUPS or in_g == BY_THEN):
                continue
            side = 0 if out_g in groups else 1 if in_g in groups else None
            if side is None:
                continue
            for s, k in ((s, k) for s in ss for k in SIZE_SPLITS):
                key = (w, b, s, k, r.period, bins[(r.period, b, k, r.rssd)], side)
                if key not in key_index:
                    key_index[key] = len(keys)
                    keys.append(key)
                cell.append(key_index[key])
                who.append(fidx[r.rssd])
                above.append(1.0 if ab else 0.0)
    groups, gindex, out_ids, in_ids, gid = [], {}, [], [], []
    for key, i in key_index.items():
        if key[6] != 0 or key[:6] + (1,) not in key_index:
            continue
        for g in [key[:4]] + ([(key[0], POOLED, key[2], key[3])] if key[1] != s59.LARGEST else []):
            if g not in gindex:
                gindex[g] = len(groups)
                groups.append(g)
            out_ids.append(i)
            in_ids.append(key_index[key[:6] + (1,)])
            gid.append(gindex[g])
    return {"keys": keys, "cell": np.array(cell, dtype=np.int64), "who": np.array(who, dtype=np.int64),
            "above": np.array(above), "filers": filers, "groups": groups,
            "out_ids": np.array(out_ids, dtype=np.int64), "in_ids": np.array(in_ids, dtype=np.int64),
            "gid": np.array(gid, dtype=np.int64)}


def class_difference(e: dict, mult) -> dict:
    """Per group (writing, band, span, size split): outside share minus inside share of prices above the
    rate, each paired bin weighted by 1/(1/n_outside + 1/n_inside); the inside and outside shares under
    the same weights, and the paired bins used; and the same difference in log odds, each count moved
    by LOGIT_ADD, which no floor caps. `mult` is each filer's multiplicity: all ones for the reading, a
    draw of the bootstrap otherwise, so a filer drawn twice brings every quarter twice."""
    wgt = np.asarray(mult, dtype=float)[e["who"]]
    n = np.bincount(e["cell"], weights=wgt, minlength=len(e["keys"]))
    a = np.bincount(e["cell"], weights=wgt * e["above"], minlength=len(e["keys"]))
    no, ni = n[e["out_ids"]], n[e["in_ids"]]
    ok = (no > 0) & (ni > 0)
    so = np.divide(a[e["out_ids"]], no, out=np.zeros_like(no), where=ok)
    si = np.divide(a[e["in_ids"]], ni, out=np.zeros_like(ni), where=ok)
    w = np.zeros_like(no)
    w[ok] = 1.0 / (1.0 / no[ok] + 1.0 / ni[ok])
    G = len(e["groups"])
    W = np.bincount(e["gid"], weights=w, minlength=G)
    ao, ai = a[e["out_ids"]], a[e["in_ids"]]
    lodds = np.log((ao + LOGIT_ADD) / (no - ao + LOGIT_ADD)) - np.log((ai + LOGIT_ADD) / (ni - ai + LOGIT_ADD))
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.bincount(e["gid"], weights=w * (so - si), minlength=G) / W
        logit = np.bincount(e["gid"], weights=w * lodds, minlength=G) / W
        inside = np.bincount(e["gid"], weights=w * si, minlength=G) / W
        outside = np.bincount(e["gid"], weights=w * so, minlength=G) / W
    return {"d": d, "logit": logit, "inside": inside, "outside": outside,
            "bins": np.bincount(e["gid"], weights=ok, minlength=G)}


def span_change(groups: list, d) -> dict:
    """{(writing, band, size split): d in 2020Q2 to 2024Q2 minus d in 2010Q1 to 2019Q4}, where both exist."""
    at = {g: i for i, g in enumerate(groups)}
    out = {}
    for (w, b, s, k), i in at.items():
        if s == 0 and (w, b, 2, k) in at:
            out[(w, b, k)] = d[at[(w, b, 2, k)]] - d[i]
    return out


def bootstrap(e: dict, draws: int, seed: int, changes: bool = True) -> dict:
    """Draws of the class difference, in shares and in log odds, and of their change, resampling filers whole.
    Without `changes` the change is not drawn: spans other than the criteria's have no earlier and later span."""
    rng = np.random.default_rng(seed)
    nf = len(e["filers"])
    out = {"d": np.empty((draws, len(e["groups"]))), "logit": np.empty((draws, len(e["groups"])))}
    for i in range(draws):
        r = class_difference(e, np.bincount(rng.integers(0, nf, nf), minlength=nf))
        out["d"][i], out["logit"][i] = r["d"], r["logit"]
    if not changes:
        return out
    out["ch_keys"] = sorted(span_change(e["groups"], out["d"][0]))
    for name in ("d", "logit"):
        out["ch_" + name] = np.array([[span_change(e["groups"], row)[k] for k in out["ch_keys"]] for row in out[name]])
    return out


RESULT = ROOT / "results" / "b113_discount_window.json"

#: a reading is read past this many of its own standard errors: the D24 family's two, as in B18
LINE = 2.0

#: a rival verdict rests on every one of these at once: both ways of writing the class, each
#: under every size split and in both scales (ruled 2026-09-16)
VERDICT_WRITINGS = (0, 1)
VERDICT_ARM = "all"

#: a filer-quarter this close to a secondary credit loan is left out of the arm "away from
#: secondary credit": secondary credit goes to institutions not eligible for primary credit
SECONDARY_WINDOW = NEAR

RIVAL_PREMISE = ("overnight borrowing by a depository institution has one price at the position, and a rate "
                 "posted to every institution in generally sound financial condition caps it")
RIVAL_ENTAILMENT = ("if every sound institution can borrow at the posted rate, none pays more than it except "
                    "through the instrument's own noise, and that noise does not depend on whether the "
                    "institution has borrowed at the window; so inside a size band, quarter and asset bin the "
                    "share paying above the rate is the same outside the class and inside it, a difference of zero")

#: What the words in the two records mean. The price is an indicator built from two filed lines, and
#: "paying above the rate" is shorthand for where that indicator stands.
DEFINITIONS = {
    "price": "the RC-K indicator of experiments/b59_size_spread.py, percent a year: the quarter's expense on federal "
             "funds purchased and securities sold under agreements to repurchase (RIAD 4180, year to date, differenced) "
             "over the quarterly average of the same two liabilities together (RC-K 3353), read only where repo is zero "
             "at both quarter ends. It is a quarter's average rate on that line. The form lets the average be taken over "
             "daily or over Wednesday closes, and repo inside the quarter is not seen, so it is the price of overnight "
             "federal funds where the balance was federal funds throughout and the filed average is the balance the "
             "expense accrued on",
    "paying above the rate": "a filer-quarter whose price, so defined, stands above the quarter's mean primary credit "
                             "rate; a share paying above the rate is a share of filer-quarters",
    "class difference": "outside minus inside the class, of that share or of its log odds, inside a size band, quarter "
                        "and asset bin, weighted and pooled as the configuration says. The rival's zero rests on the "
                        "indicator's departures from the price paid not differing by class inside a bin",
    "crossed difference": "the class difference at one height in the span when the primary credit rate stood there, "
                          "minus the same in the other span. A share above a height is not linear in the level of "
                          "prices, and the readings kept change with the height, so a move of both classes' prices "
                          "between the spans enters it. It describes the two spans at the two heights; by itself it "
                          "does not isolate what the rate's height adds",
}

#: state of every verdict reading at once -> (passed, grid) for a rival criterion, and -> passed for the change
RIVAL_MAP = {"above": (True, "B"), "below": (True, "both_unmet"), "unread": (None, "unread")}
CHANGE_MAP = {"above": True, "below": False, "unread": None}

#: (state of the half that borrowed more, state of the half never above the recurring amount) -> shape
SPLIT_SHAPES = {
    ("above", "above"): "the edge alone", ("above", "unread"): "the edge in use",
    ("above", "below"): "the edge in use, the tested half the other way",
    ("unread", "above"): "the tested half alone", ("unread", "unread"): "unread",
    ("unread", "below"): "the tested half the other way",
    ("below", "above"): "third branch", ("below", "unread"): "third branch", ("below", "below"): "third branch"}


def ratio(a: float, b: float) -> float:
    return float("nan") if not b or not math.isfinite(b) else a / b


def band_members(b: str) -> list:
    return [x for x, *_y in s59.BANDS if x != s59.LARGEST] if b == POOLED else [b]


def reading_rows(e: dict, point: dict, boots: list) -> dict:
    """{(writing, band, span, size split): what is printed and recorded for the group}."""
    counts = collections.defaultdict(lambda: [0, 0])
    distinct = collections.defaultdict(lambda: (set(), set()))
    for c, f in zip(e["cell"].tolist(), e["who"].tolist()):
        key = e["keys"][c]
        counts[key[:4]][key[6]] += 1
        distinct[key[:4]][key[6]].add(f)
    rows = {}
    for gi, (w, b, s, k) in enumerate(e["groups"]):
        n, fs = [0, 0], (set(), set())
        for bb in band_members(b):
            n = [n[0] + counts[(w, bb, s, k)][0], n[1] + counts[(w, bb, s, k)][1]]
            fs = (fs[0] | distinct[(w, bb, s, k)][0], fs[1] | distinct[(w, bb, s, k)][1])
        d, lg = float(point["d"][gi]), float(point["logit"][gi])
        se_d = [float(np.nanstd(bt["d"][:, gi], ddof=1)) for bt in boots]
        se_l = [float(np.nanstd(bt["logit"][:, gi], ddof=1)) for bt in boots]
        rows[(w, b, s, k)] = {
            "d": d, "se_d": se_d, "z_d": ratio(d, float(np.mean(se_d))), "z_d_each_seed": [ratio(d, x) for x in se_d],
            "logit": lg, "se_logit": se_l, "z_logit": ratio(lg, float(np.mean(se_l))),
            "z_logit_each_seed": [ratio(lg, x) for x in se_l],
            "draws_read": sum(int(np.isfinite(bt["d"][:, gi]).sum()) for bt in boots),
            "inside": float(point["inside"][gi]), "outside": float(point["outside"][gi]), "bins": int(point["bins"][gi]),
            "filer_quarters": n, "filers": [len(fs[0]), len(fs[1])]}
    return rows


def change_rows(e: dict, point: dict, boots: list) -> dict:
    """{(writing, band, size split): the later span's difference minus the earlier span's, in shares and log odds}."""
    chd, chl = span_change(e["groups"], point["d"]), span_change(e["groups"], point["logit"])
    rows = {}
    for key in chd:
        idx = [bt["ch_keys"].index(key) for bt in boots]
        se_d = [float(np.nanstd(bt["ch_d"][:, i], ddof=1)) for bt, i in zip(boots, idx)]
        se_l = [float(np.nanstd(bt["ch_logit"][:, i], ddof=1)) for bt, i in zip(boots, idx)]
        d, lg = float(chd[key]), float(chl[key])
        rows[key] = {"d": d, "se_d": se_d, "z_d": ratio(d, float(np.mean(se_d))), "z_d_each_seed": [ratio(d, x) for x in se_d],
                     "logit": lg, "se_logit": se_l, "z_logit": ratio(lg, float(np.mean(se_l))),
                     "z_logit_each_seed": [ratio(lg, x) for x in se_l],
                     "draws_read": sum(int(np.isfinite(bt["ch_d"][:, i]).sum()) for bt, i in zip(boots, idx))}
    return rows


def state(zs) -> str:
    """above: every reading past +LINE; below: every one past -LINE; unread otherwise, a missing one included."""
    zs = list(zs)
    if zs and all(z >= LINE for z in zs):
        return "above"
    if zs and all(z <= -LINE for z in zs):
        return "below"
    return "unread"


def verdict_zs(rows: dict, s, writings=VERDICT_WRITINGS, seed=None) -> list:
    """The z of every verdict reading of span s (or of the change, s None), with the mean se or one seed's."""
    out = []
    for w in writings:
        for k in SIZE_SPLITS:
            r = rows.get((w, POOLED, s, k) if s is not None else (w, POOLED, k))
            if r is None:
                out += [float("nan"), float("nan")]
            elif seed is None:
                out += [r["z_d"], r["z_logit"]]
            else:
                out += [r["z_d_each_seed"][seed], r["z_logit_each_seed"][seed]]
    return out


def rate_known_answer(dw: dict, pcr_text: str) -> dict:
    """Every primary credit loan's rate against DPCREDIT on its day, or within two calendar days either
    side, where a Reserve Bank's effective date differs from New York's (data/SOURCES.md)."""
    pcr_quarters(pcr_text)
    rate = {r[0]: float(r[1]) for r in list(csv.reader(io.StringIO(pcr_text)))[1:] if len(r) > 1 and r[1].strip()}
    exact, near, miss = 0, 0, []
    for q, rec in sorted(dw.items()):
        for ln in rec.get("loans", []):
            if ln["type"] != "primary":
                continue
            if rate.get(ln["date"]) == ln["rate"]:
                exact += 1
                continue
            d0 = datetime.date.fromisoformat(ln["date"])
            if ln["rate"] in {rate.get((d0 + datetime.timedelta(days=j)).isoformat()) for j in range(-2, 3)}:
                near += 1
            else:
                miss.append(f"{ln['date']} {ln.get('district', '')} {ln['borrower']} {ln['rate']}")
    return {"exact": exact, "within_two_days": near, "unmatched": miss}


def build_criteria(total_loans: int, j: dict, rate_ka: dict, rows: dict, crossed: dict, stretch_rows: dict) -> dict:
    """Every flag here is computed from the object it names (11f); the maps above are the only verdicts."""
    crit = {}
    counted = len(j["matched"]) + sum(j["unmatched"].values())
    crit["B113-1"] = {
        "kind": "instrument", "passed": total_loans > 0 and counted == total_loans,
        "name": "every loan in the parsed files is counted once: joined to a filer, or not joined under one named reason",
        "detail": f"{total_loans:,} loans; {len(j['matched']):,} joined; not joined "
                  + "; ".join(f"{t}, {why} {n:,}" for (t, why), n in sorted(j["unmatched"].items()))
                  + f"; counted {counted:,}"}
    crit["B113-2"] = {
        "kind": "known_answer",
        "passed": rate_ka["exact"] + rate_ka["within_two_days"] > 0 and not rate_ka["unmatched"],
        "name": "every primary credit loan carries the primary credit rate of its day, or of a day within two "
                "calendar days, where a Reserve Bank's effective date differs from New York's",
        "detail": f"on the day {rate_ka['exact']:,}; within two days {rate_ka['within_two_days']:,}; "
                  f"neither {len(rate_ka['unmatched'])}" + (": " + "; ".join(rate_ka["unmatched"][:20]) if rate_ka["unmatched"] else "")}
    zs = verdict_zs(rows, 0)
    st = state(zs)
    passed, grid = RIVAL_MAP[st]
    lo, hi = SPANS[0]
    crit["B113-3"] = {
        "kind": "rival", "passed": passed, "grid": grid, "rival_shape": "point prediction",
        "rival_premise": RIVAL_PREMISE, "rival_entailment": RIVAL_ENTAILMENT,
        "name": f"{lo} to {hi}, banks below $10 billion: outside minus inside the discount window class, the share "
                f"paying above the quarter's mean primary credit rate is not zero, read in both writings of the class, "
                f"every size split and both scales at once",
        "detail": f"state {st}: every reading past {LINE:g} se maps to the rival's zero failing (B), every one past "
                  f"-{LINE:g} to both unmet, anything else to no verdict; readings in se "
                  + ", ".join(f"{z:+.2f}" for z in zs)}
    if grid == "unread":
        crit["B113-3"]["grid_note"] = {"B": "not claimed: some reading does not pass the line", "C": "not claimed"}
    for s, (name, (lo, hi)) in enumerate(STRETCH_CRITERIA):
        zs = verdict_zs(stretch_rows, s, writings=(BY_THEN_W,))
        st = state(zs)
        passed, grid = RIVAL_MAP[st]
        crit[name] = {
            "kind": "rival", "passed": passed, "grid": grid, "rival_shape": "point prediction",
            "rival_premise": RIVAL_PREMISE, "rival_entailment": RIVAL_ENTAILMENT,
            "name": f"{lo} to {hi}, banks below $10 billion: outside the discount window class minus its members that had "
                    f"used the window by the quarter read, the share paying above the quarter's mean primary credit rate "
                    f"is not zero, on readings the step alone does not put above the rate and the rounding decides, "
                    f"every size split and both scales at once",
            "detail": f"state {st}: every reading past {LINE:g} se maps to the rival's zero failing (B), every one past "
                      f"-{LINE:g} to both unmet, anything else to no verdict; readings in se "
                      + ", ".join(f"{z:+.2f}" for z in zs)}
        if grid == "unread":
            crit[name]["grid_note"] = {"B": "not claimed: some reading does not pass the line", "C": "not claimed"}
    zc = crossed_zs(crossed)
    stc = state(zc)
    (lo0, hi0), (lo1, hi1) = CROSSED_SPANS
    crit["B113-5"] = {
        "kind": "own_reading", "passed": CHANGE_MAP[stc],
        "name": f"the class difference moves with the rate: at the height over the effective federal funds rate where the "
                f"rate stood from {lo1} to {hi1} the difference is larger then than from {lo0} to {hi0}, and at the height "
                f"where it stood from {lo0} to {hi0} it is larger then than from {lo1} to {hi1}; banks below $10 billion, "
                f"members that had used the window by the quarter read against the class's outside, readings the "
                f"instrument decides at each height, every size split and both scales at once",
        "detail": f"state {stc}: every reading past {LINE:g} se maps to pass, every one past -{LINE:g} to fail, anything "
                  f"else to no verdict; readings in se, the later rate's height then the earlier's, "
                  + ", ".join(f"{z:+.2f}" for z in zc)}
    seeds = min(len(next(iter(rw.values()))["z_d_each_seed"]) if rw else 0 for rw in (rows, stretch_rows, crossed))
    split = {"B113-3": [state(verdict_zs(rows, 0, seed=sd)) for sd in range(seeds)]}
    for s, (name, _span) in enumerate(STRETCH_CRITERIA):
        split[name] = [state(verdict_zs(stretch_rows, s, writings=(BY_THEN_W,), seed=sd)) for sd in range(seeds)]
    split["B113-5"] = [state(crossed_zs(crossed, seed=sd)) for sd in range(seeds)]
    crit["B113-6"] = {
        "kind": "instrument", "passed": seeds >= 2 and all(len(set(v)) == 1 for v in split.values()),
        "name": "each seed's standard errors alone put every verdict of B113-3, B113-4a to B113-4c and B113-5 in the same state (D51)",
        "detail": "; ".join(f"{k}: {', '.join(v)}" for k, v in split.items()) + f"; seeds {seeds}"}
    return crit


def split_shape(rows: dict, s: int) -> dict:
    took, small = state(verdict_zs(rows, s, writings=(3,))), state(verdict_zs(rows, s, writings=(2,)))
    return {"half that borrowed more": took, "half never above the recurring amount": small,
            "shape": SPLIT_SHAPES[(took, small)],
            "z, half that borrowed more": verdict_zs(rows, s, writings=(3,)),
            "z, half never above": verdict_zs(rows, s, writings=(2,))}


def group_label(key: tuple) -> str:
    if len(key) == 4:
        w, b, s, k = key
        lo, hi = SPANS[s]
        return f"{WRITINGS[w][0]} | {b} | {lo if lo == hi else lo + ' to ' + hi} | cut {k}"
    w, b, k = key
    return f"{WRITINGS[w][0]} | {b} | cut {k}"


def stretch_label(key: tuple) -> str:
    w, b, s, k = key
    lo, hi = STRETCH_SPANS[s]
    return f"{STRETCH_WRITINGS[w][0]} | {b} | {lo} to {hi} | cut {k}"


def keep_in_record(key: tuple) -> bool:
    return key[1] == POOLED or key[-1] == max(SIZE_SPLITS)


def arm_obs(rows, arm: str, secondary: dict):
    if arm == "all":
        return s59.arm_rc_k(rows)
    if arm == "away from secondary credit":
        return [(r, c) for r, c in s59.arm_rc_k(rows)
                if not any(shift(q, -SECONDARY_WINDOW) <= r.period <= shift(q, SECONDARY_WINDOW) for q in secondary.get(r.rssd, ()))]
    return s59.arm_rc_k_split(rows, arm)


def run_record(draws: int, seeds: list, out=print) -> dict:
    dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
    index, clashes = aba_index(build_por(out=out))
    j = join(dw, index)
    ever, by_q = edge_classes(j["matched"])
    panel = s59.load_panel()
    lo = loan_object(j["matched"], panel)
    small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
    secondary = collections.defaultdict(set)
    for x in j["matched"]:
        if x["type"] == "secondary":
            secondary[x["rssd"]].add(x["quarter"])
    pcr_text = PCR_CSV.read_text(encoding="utf-8")
    pcr = pcr_quarters(pcr_text)
    qrows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
    readings, changes, shapes, all_rows = {}, {}, {}, {}
    for arm in RECORD_ARMS:
        e = reading_entries(arm_obs(qrows, arm, secondary), pcr, ever, by_q, small_only)
        point = class_difference(e, np.ones(len(e["filers"])))
        boots = [bootstrap(e, draws, sd) for sd in seeds]
        rr, cr = reading_rows(e, point, boots), change_rows(e, point, boots)
        all_rows[arm] = (rr, cr)
        readings[arm] = {group_label(k): v for k, v in sorted(rr.items()) if keep_in_record(k)}
        changes[arm] = {group_label(k): v for k, v in sorted(cr.items()) if keep_in_record(k)}
        shapes[arm] = {f"{SPANS[s][0]} to {SPANS[s][1]}": split_shape(rr, s) for s in (0, 2)}
        out(f"  arm {arm}: {len(e['filers']):,} filers, {len(e['cell']):,} entries")
    e4 = reading_entries(arm_obs(qrows, VERDICT_ARM, secondary), pcr, ever, by_q, small_only, spans=STRETCH_SPANS,
                         keep=step_and_rounding, writings=STRETCH_WRITINGS, timing=lambda q: edge_timing(q, by_q))
    b4 = [bootstrap(e4, draws, sd, changes=False) for sd in seeds]
    stretch_rows = reading_rows(e4, class_difference(e4, np.ones(len(e4["filers"]))), b4)
    out(f"  stretches after 2020Q1: {len(e4['filers']):,} filers, {len(e4['cell']):,} entries")
    _years, effr_q = s59.load_effr()
    cr5 = crossed_reading(arm_obs(qrows, VERDICT_ARM, secondary), pcr, effr_q, ever, by_q, small_only, draws, seeds)
    out(f"  heights for B113-5: {len(cr5['entries']['filers']):,} filers, {len(cr5['entries']['cell']):,} entries")
    total = sum(len(rec.get("loans", [])) for rec in dw.values())
    rate_ka = rate_known_answer(dw, pcr_text)
    crit = build_criteria(total, j, rate_ka, all_rows[VERDICT_ARM][0], cr5["effects"], stretch_rows)
    named, missed = possible_misses(j["elsewhere_primary"], index, ever)
    obs = s59.arm_rc_k(qrows)
    cells = class_cells(obs, ever, by_q)
    worst = {}
    for b, *_x in s59.BANDS:
        cs = [c for c in cells if c["band"] == b]
        we = min(cs, key=lambda c: (c["ever"], c["quarter"]))
        wo = min(cs, key=lambda c: (c["filers"] - c["ever"], c["quarter"]))
        nn = [c for c in cs if c["near"] is not None]
        wn = min(nn, key=lambda c: (c["near"], c["quarter"]))
        worst[b] = {"ever": [we["ever"], we["quarter"]], "outside ever": [wo["filers"] - wo["ever"], wo["quarter"]],
                    "near": [wn["near"], wn["quarter"]]}
    return {
        "stage": "B113",
        "definitions": DEFINITIONS,
        "config": {
            "loans_cache": "data/cache/b113_dw_loans.json", "loans_cache_sha256": s59.sha256_of(dwl.CACHE),
            "call_report_cache": "data/cache/b59_call_report.json", "call_report_cache_sha256": s59.sha256_of(drv.CACHE),
            "primary_credit_rate": "data/b59/DPCREDIT.csv", "primary_credit_rate_sha256": s59.sha256_of(PCR_CSV),
            "loan_data_span": [DW_FIRST, DW_LAST], "near_window_quarters": NEAR, "credit_union_pattern": CU_RE.pattern,
            "bands_thousands_of_dollars": [[n, a, b] for n, a, b in s59.BANDS], "pooled_bands": band_members(POOLED),
            "size_splits": list(SIZE_SPLITS), "spans": [list(x) for x in SPANS], "logit_add": LOGIT_ADD,
            "line_in_standard_errors": LINE, "verdict_writings": [WRITINGS[w][0] for w in VERDICT_WRITINGS],
            "verdict_arm": VERDICT_ARM, "arms": list(RECORD_ARMS), "secondary_window_quarters": SECONDARY_WINDOW,
            "bootstrap_draws": draws, "seeds": list(seeds),
            "stretch_criteria": [[name, list(span)] for name, span in STRETCH_CRITERIA], "stretch_verdict_writing": BY_THEN,
            "stretch_readings_kept": "the step alone does not put it above the rate, and the rounding decides it",
            "timing_window_quarters": NEAR,
            "effective_rate": "data/b59/EFFR.csv", "effective_rate_sha256": s59.sha256_of(s59.EFFR_CSV),
            "crossed_spans": [list(x) for x in CROSSED_SPANS], "crossed_heights": [name for name, _sign in CROSSED_POSITIONS],
            "crossed_writing": BY_THEN,
            "crossed_readings_kept": "the step alone does not put it above the height read, and the rounding decides it against that height"},
        "criteria": crit,
        "join": {"loans": total, "joined": len(j["matched"]),
                 "joined_primary": sum(1 for x in j["matched"] if x["type"] == "primary"),
                 "not_joined": {f"{t}, {why}": n for (t, why), n in sorted(j["unmatched"].items())},
                 "primary_numbers_in_another_quarters_panel": len(j["elsewhere_primary"]),
                 "filers_they_name": len(named), "of_them_outside_ever": len(missed),
                 "panel_periods_with_a_shared_number": sum(1 for v in clashes.values() if v)},
        "classes": {"ever": len(ever),
                    "primary_filers_per_quarter": [min(len(v) for v in by_q.values()), max(len(v) for v in by_q.values())],
                    "worst_cells": worst},
        "loans": {"primary_joined": lo["loans"], "recurring_amount": lo["mode"],
                  "top_amounts": [[a, k] for a, k in lo["top_amounts"]],
                  "members_by_band": {b: {"members": sum(1 for m in lo["members"] if m["band"] == b),
                                          "never_above_recurring": sum(1 for m in lo["members"] if m["band"] == b and m["never_above_mode"])}
                                      for b, *_x in s59.BANDS}},
        "rate_check": rate_ka,
        "readings": readings, "changes": changes, "split_shape": shapes,
        "stretch_readings": {stretch_label(k): v for k, v in sorted(stretch_rows.items()) if keep_in_record(k)},
        "crossed": {"shift_bp": 100.0 * cr5["shift_pp"], "heights_over_effective_rate_bp": cr5["heights_bp"],
                    "readings": {crossed_label(k): v for k, v in sorted(cr5["readings"].items()) if k[1] == POOLED},
                    "effects": {crossed_label(k): v for k, v in sorted(cr5["effects"].items())}},
    }


def shift(q: str, k: int) -> str:
    y, n = int(q[:4]), int(q[-1]) - 1 + k
    return f"{y + n // 4}Q{n % 4 + 1}"


def por_map(text: str) -> dict:
    """A panel-of-reporters file to {IDRSSD: nine-character ABA}; filers with no number are left out."""
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    head = [h.strip().strip('"') for h in rows[0]] if rows else []
    missing = [w for w in POR_WANT if w not in head]
    if missing:
        raise ValueError(f"panel of reporters lacks {missing}")
    ir, ia = head.index("IDRSSD"), head.index("Primary ABA Routing Number")
    out = {}
    for r in rows[1:]:
        if len(r) <= max(ir, ia):
            continue
        rssd, aba = r[ir].strip().strip('"'), r[ia].strip().strip('"')
        if rssd.isdigit() and aba.isdigit() and int(aba) > 0:
            out[rssd] = aba.zfill(9)
    return out


def build_por(out=print) -> dict:
    """{period: {IDRSSD: ABA}} for every single-period archive, reused while the archive's
    digest in the size arm's cache is the one it was read from."""
    b59 = json.loads(drv.CACHE.read_text(encoding="utf-8"))
    old = json.loads(POR_CACHE.read_text(encoding="utf-8")) if POR_CACHE.exists() else {}
    got, read, reused = {}, 0, 0
    for per, rec in sorted(b59.items()):
        if "Subset of Schedules" in rec["archive"]:
            continue
        if per in old and old[per]["sha256"] == rec["sha256"]:
            got[per] = old[per]
            reused += 1
            continue
        with zipfile.ZipFile(drv.RAW / rec["archive"]) as z:
            member = [i for i in z.infolist() if re.search(r"\bPOR\b", i.filename)]
            if len(member) != 1:
                out(f"  {per}: {len(member)} panel-of-reporters members, not read")
                continue
            got[per] = {"sha256": rec["sha256"], "archive": rec["archive"],
                        "aba": por_map(z.read(member[0]).decode("utf-8", "replace"))}
        read += 1
    POR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    POR_CACHE.write_text(json.dumps(got, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    out(f"  panels of reporters: {len(got)} period(s), {read} read, {reused} reused")
    return got


def aba_index(por: dict) -> tuple[dict, dict]:
    """{period: {ABA: IDRSSD}}, leaving out any number two filers carry in one period, and the count of those."""
    index, clashes = {}, {}
    for per, rec in por.items():
        seen = collections.defaultdict(set)
        for rssd, aba in rec["aba"].items():
            seen[aba].add(rssd)
        index[per] = {a: next(iter(s)) for a, s in seen.items() if len(s) == 1}
        clashes[per] = sum(1 for s in seen.values() if len(s) > 1)
    return index, clashes


def join(dw: dict, index: dict) -> dict:
    """Every loan to the filer its ABA names in the quarter of the loan."""
    matched, unmatched = [], collections.Counter()
    sample = collections.defaultdict(list)
    anywhere = set().union(*(set(v) for v in index.values())) if index else set()
    elsewhere = set()
    for q, rec in sorted(dw.items()):
        idx = index.get(q)
        for ln in rec.get("loans", []):
            rssd = idx.get(ln["aba"]) if idx is not None else None
            if rssd is None:
                if idx is None:
                    kind = "no panel for the quarter"
                elif ln["aba"] in anywhere:
                    kind = "number in another quarter's panel"
                elif CU_RE.search(ln["borrower"]):
                    kind = "credit union by name"
                else:
                    kind = "number in no panel"
                unmatched[(ln["type"], kind)] += 1
                if kind == "number in another quarter's panel" and ln["type"] == "primary":
                    elsewhere.add(ln["aba"])
                key = f"{ln['type']}, {kind}"
                if kind.startswith("number") and len(sample[key]) < 8:
                    sample[key].append(f"{ln['borrower']} ({ln['state']}) {ln['aba']} {q}")
                continue
            matched.append({"quarter": q, "rssd": rssd, "type": ln["type"], "date": ln["date"],
                            "amount": ln["amount"], "collateral": ln["collateral"],
                            "term": ln.get("term"), "aggregated": ln.get("aggregated", False)})
    return {"matched": matched, "unmatched": dict(unmatched), "unmatched_sample": dict(sample),
            "elsewhere_primary": sorted(elsewhere)}


def possible_misses(numbers, index: dict, ever: set) -> tuple[set, set]:
    """The filers that the numbers of primary loans not joined name in some other quarter's panel, and
    those of them outside the ever class: an upper bound on the class members the join misses, since
    a number can pass to another filer after a merger."""
    named = {per[a] for per in index.values() for a in numbers if a in per}
    return named, named - ever


def edge_classes(matched: list) -> tuple[set, dict]:
    """The ever class, and {quarter: set of filers with a primary credit loan in it}."""
    by_q = collections.defaultdict(set)
    for m in matched:
        if m["type"] == "primary":
            by_q[m["quarter"]].add(m["rssd"])
    return set().union(*by_q.values()) if by_q else set(), dict(by_q)


def near_class(q: str, by_q: dict, k: int = NEAR):
    """Filers with a primary credit loan within k quarters of q, or None where the window leaves the loan data."""
    lo, hi = shift(q, -k), shift(q, k)
    if lo < DW_FIRST or hi > DW_LAST:
        return None
    out = set()
    for j in range(-k, k + 1):
        out |= by_q.get(shift(q, j), set())
    return out


#: the powers of ten a ratio is printed in; the first bin takes everything below 1e-8, the last 1 and over
DECADES = tuple(range(-9, 1))


def decade(ratio: float):
    """The power of ten a positive ratio sits in, clipped to DECADES; None for zero."""
    if ratio <= 0:
        return None
    return max(DECADES[0], min(DECADES[-1], math.floor(math.log10(ratio) + 1e-12)))


def loan_object(matched: list, panel: dict) -> dict:
    """What a primary credit loan looks like, and each class member's largest loan against its own assets.

    The amount that recurs most is read off the loans, not set, and a member whose every loan is at
    most that amount is counted apart. A ratio is dollars over total assets, which are filed in
    thousands, in the quarter of the loan; a member's band is read in the quarter of its largest loan."""
    prim = [m for m in matched if m["type"] == "primary"]
    counts = collections.Counter(m["amount"] for m in prim)
    mode = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0] if counts else None
    years = collections.defaultdict(lambda: [0, 0, set(), set()])
    members = {}
    for m in prim:
        y = years[m["date"][:4]]
        y[0] += 1
        y[1] += m["amount"] == mode
        y[2].add(m["rssd"])
        if m["amount"] > mode:
            y[3].add(m["rssd"])
        p = members.setdefault(m["rssd"], {"loans": 0, "largest": m, "collateral": None})
        p["loans"] += 1
        if m["amount"] > p["largest"]["amount"]:
            p["largest"] = m
        assets = panel.get(m["quarter"], {}).get(m["rssd"], {}).get("2170")
        if assets and m.get("collateral") is not None:
            c = m["collateral"] / (assets * 1000.0)
            if p["collateral"] is None or c > p["collateral"]:
                p["collateral"] = c
    rows = []
    for rssd, p in sorted(members.items()):
        big = p["largest"]
        assets = panel.get(big["quarter"], {}).get(rssd, {}).get("2170")
        rows.append({"rssd": rssd, "loans": p["loans"], "largest": big["amount"],
                     "band": s59.band_of(assets) if assets else None,
                     "largest_over_assets": big["amount"] / (assets * 1000.0) if assets else None,
                     "collateral_over_assets": p["collateral"],
                     "never_above_mode": big["amount"] <= mode})
    return {"loans": len(prim), "aggregated": sum(1 for m in prim if m.get("aggregated")), "mode": mode,
            "top_amounts": counts.most_common(8), "amounts": sorted(m["amount"] for m in prim),
            "terms": collections.Counter(m["term"] for m in prim).most_common(6),
            "terms_at_mode": collections.Counter(m["term"] for m in prim if m["amount"] == mode).most_common(3),
            "years": {k: {"loans": v[0], "at_mode": v[1], "filers": len(v[2]), "never_above_mode": len(v[2] - v[3])}
                      for k, v in sorted(years.items())},
            "members": rows}


def class_cells(obs, ever: set, by_q: dict) -> list:
    """Per quarter and size band: filers with a readable fed funds price, how many are in each class."""
    cells = collections.defaultdict(lambda: {"filers": set(), "ever": set(), "near": set(), "near_defined": True})
    near_cache = {}
    for r, _c in obs:
        key = (r.period, s59.band_of(r.assets))
        cell = cells[key]
        cell["filers"].add(r.rssd)
        if r.rssd in ever:
            cell["ever"].add(r.rssd)
        if r.period not in near_cache:
            near_cache[r.period] = near_class(r.period, by_q)
        nc = near_cache[r.period]
        if nc is None:
            cell["near_defined"] = False
        elif r.rssd in nc:
            cell["near"].add(r.rssd)
    return [{"quarter": q, "band": b, "filers": len(v["filers"]), "ever": len(v["ever"]),
             "near": len(v["near"]) if v["near_defined"] else None}
            for (q, b), v in sorted(cells.items())]


def print_classes(j: dict, ever: set, by_q: dict, cells: list, clashes: dict, index: dict) -> None:
    n_primary = sum(1 for m in j["matched"] if m["type"] == "primary")
    un = j["unmatched"]
    print(f"  loans joined to a filer: {len(j['matched']):,} ({n_primary:,} primary credit)")
    print("  loans not joined, by type and why:")
    for (t, kind), n in sorted(un.items()):
        print(f"    {t:<10} {kind:<34} {n:>6,}")
    for t, s in j["unmatched_sample"].items():
        print(f"    sample, {t}: " + "; ".join(s[:5]))
    print(f"  panel periods with a number two filers carry: {sum(1 for v in clashes.values() if v)}")
    named, missed = possible_misses(j["elsewhere_primary"], index, ever)
    print(f"  primary loans with a number in another quarter's panel: {len(j['elsewhere_primary'])} numbers, naming "
          f"{len(named)} filers, {len(missed)} of them outside the ever class")
    print(f"  class ever: {len(ever):,} filers; filers with a primary loan per quarter, min {min(len(v) for v in by_q.values())}, "
          f"max {max(len(v) for v in by_q.values())}")
    bands = [b for b, *_x in s59.BANDS]
    print(f"\n  readable fed funds price: filers / in ever / in near, per quarter and band")
    print(f"  {'quarter':7} " + " ".join(f"{b[:14]:>22}" for b in bands))
    by = {(c["quarter"], c["band"]): c for c in cells}
    for q in sorted({c["quarter"] for c in cells}):
        parts = []
        for b in bands:
            c = by.get((q, b))
            parts.append(f"{'-':>22}" if c is None else
                         f"{c['filers']:>8} / {c['ever']:>5} / {'-' if c['near'] is None else c['near']:>5}")
        print(f"  {q:7} " + " ".join(parts))
    for b in bands:
        cs = [c for c in cells if c["band"] == b]
        we = min(cs, key=lambda c: (c["ever"], c["quarter"]))
        wo = min(cs, key=lambda c: (c["filers"] - c["ever"], c["quarter"]))
        nn = [c for c in cs if c["near"] is not None]
        wn = min(nn, key=lambda c: (c["near"], c["quarter"])) if nn else None
        print(f"  worst cells, {b}: ever {we['ever']} ({we['quarter']}), outside ever {wo['filers'] - wo['ever']} ({wo['quarter']})"
              + (f", near {wn['near']} ({wn['quarter']})" if wn else ""))


def print_loans(o: dict) -> None:
    n, mode = o["loans"], o["mode"]
    v = o["amounts"]
    at = [v[min(len(v) - 1, int(p * len(v)))] for p in (0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99)]
    print(f"  primary credit loans joined to a filer: {n:,} ({o['aggregated']:,} rows sum several loans of one day)")
    print("  amounts that recur most: " + "; ".join(f"{a:,.0f} x {k:,} ({k / n:.1%})" for a, k in o["top_amounts"]))
    print("  amount at p1 p10 p25 p50 p75 p90 p99: " + ", ".join(f"{a:,.0f}" for a in at))
    print("  term in days: " + "; ".join(f"{t} x {k:,} ({k / n:.1%})" for t, k in o["terms"]))
    print(f"  term of the loans at {mode:,.0f}: " + "; ".join(f"{t} x {k:,}" for t, k in o["terms_at_mode"]))
    print(f"\n  per year: loans / at {mode:,.0f} / filers / filers with no loan above {mode:,.0f} that year")
    for y, c in o["years"].items():
        print(f"  {y}  {c['loans']:>6,} / {c['at_mode']:>6,} / {c['filers']:>4} / {c['never_above_mode']:>4}")
    bands = [b for b, *_x in s59.BANDS]
    ms = o["members"]
    print(f"\n  class members by band in the quarter of their largest loan: members / every loan at most {mode:,.0f}"
          f" / loans per member p50 p90 max")
    for b in bands + [None]:
        g = [r for r in ms if r["band"] == b]
        if not g:
            continue
        nl = sorted(r["loans"] for r in g)
        print(f"  {b or 'no assets that quarter':<24} {len(g):>5} / {sum(r['never_above_mode'] for r in g):>5} / "
              f"{nl[len(nl) // 2]} {nl[min(len(nl) - 1, int(0.9 * len(nl)))]} {nl[-1]}")
    labels = ["<1e-8" if d == DECADES[0] else ">=1" if d == DECADES[-1] else f"1e{d}" for d in DECADES]
    for key, label, keep in (("largest_over_assets", "largest loan over total assets", lambda r: True),
                             ("collateral_over_assets", "largest collateral pledged over total assets", lambda r: True),
                             ("collateral_over_assets", f"the same, members whose every loan is at most {mode:,.0f}",
                              lambda r: r["never_above_mode"])):
        print(f"\n  {label}: class members per power of ten")
        print(f"  {'band':<24}" + "".join(f"{s:>7}" for s in labels) + "   zero or none")
        for b in bands:
            g = [r for r in ms if r["band"] == b and keep(r)]
            c = collections.Counter(decade(r[key]) if r[key] is not None else None for r in g)
            print(f"  {b:<24}" + "".join(f"{c.get(d, 0):>7}" for d in DECADES) + f"   {c.get(None, 0):>5}")


def print_above(cells: list, uncovered: int, pcr: dict, mode: float) -> None:
    by = {(c["quarter"], c["band"], c["group"]): c for c in cells}
    quarters = sorted({c["quarter"] for c in cells})
    near_defined = {c["quarter"] for c in cells if c["group"] in ("near", "outside near")}
    names = [g.replace("the recurring amount", f"{mode:,.0f}") for g in GROUPS]
    print(f"  filer-quarters with a price in a quarter the rate file does not cover: {uncovered}")
    for b, *_x in s59.BANDS:
        print(f"\n  {b}: filer-quarters and the share above the quarter's mean primary credit rate, pooled")
        print(f"  {'':<40}" + "".join(f"{lo + ' to ' + hi if lo != hi else lo:>22}" for lo, hi in SPANS))
        for g, name in zip(GROUPS, names):
            parts = []
            for lo, hi in SPANS:
                n = sum(c["filers"] for (q, bb, gg), c in by.items() if bb == b and gg == g and lo <= q <= hi)
                k = sum(c["above"] for (q, bb, gg), c in by.items() if bb == b and gg == g and lo <= q <= hi)
                parts.append(f"{n:>13,} {k / n:>7.3f}" if n else f"{'-':>21}")
            print(f"  {name:<40}" + " ".join(parts))
        print(f"\n  {b}: per quarter, filers and share above; rate mean, and * where the rate moved inside the quarter")
        print(f"  {'quarter':<7} {'rate':>6}  " + "".join(f"{s[:21]:>22}" for s in names))
        worst = {}
        for q in quarters:
            mean, low, high = pcr[q]
            parts = []
            for g in GROUPS:
                c = by.get((q, b, g))
                n = 0 if c is None else c["filers"]
                if (g not in ("near", "outside near") or q in near_defined) and (g not in worst or n < worst[g][0]):
                    worst[g] = (n, q)
                if c is None:
                    parts.append(f"{'-':>22}")
                    continue
                parts.append(f"{c['filers']:>14} {c['above'] / c['filers']:>7.3f}")
            print(f"  {q:<7} {mean:>6.3f}{'*' if high > low else ' '} " + "".join(parts))
        print("  worst cells, a quarter with none in the group counting as zero: "
              + "; ".join(f"{name} {worst[g][0]} ({worst[g][1]})" for g, name in zip(GROUPS, names) if g in worst))


def print_readings(e: dict, point: dict, boots: list, draws: int, seeds: tuple, mode: float, arm: str) -> None:
    names = [w[0].replace("the recurring amount", f"{mode:,.0f}") for w in WRITINGS]
    rows, chg = reading_rows(e, point, boots), change_rows(e, point, boots)
    band_order = {b: i for i, (b, *_x) in enumerate(s59.BANDS)}
    band_order[POOLED] = len(band_order)
    total = draws * len(boots)
    print(f"\n  ===== fed funds arm: {arm} =====")
    print(f"  filers resampled whole: {len(e['filers']):,}; draws per seed {draws}; seeds {seeds}")
    for w, name in enumerate(names):
        print(f"\n  {name}: outside minus inside, share above the rate; inside share under the same weights; paired bins")
        print(f"  {'band':<14} {'span':<18} {'cut':>3} {'difference':>10}  {'se, each seed':>15}  {'in se':>6}  {'log odds':>8}  {'se, each seed':>15}  {'in se':>6}  {'draws read':>10}"
              f"  {'inside':>6} {'outside':>7} {'bins':>5}  filer-quarters out / in, filers out / in")
        for key in sorted((g for g in rows if g[0] == w), key=lambda g: (g[2], band_order[g[1]], g[3])):
            _w, b, s, k = key
            r = rows[key]
            lo, hi = SPANS[s]
            ses = " ".join(f"{x:.3f}" for x in r["se_d"])
            sel = " ".join(f"{x:.3f}" for x in r["se_logit"])
            print(f"  {b:<14} {lo + ' to ' + hi if lo != hi else lo:<18} {k:>3} {r['d']:>+10.3f}  {ses:>15}  {r['z_d']:>+6.2f}  "
                  f"{r['logit']:>+8.3f}  {sel:>15}  {r['z_logit']:>+6.2f}  {r['draws_read']:>5}/{total:<4}  "
                  f"{r['inside']:>6.3f} {r['outside']:>7.3f} {r['bins']:>5}  "
                  f"{r['filer_quarters'][0]:,} / {r['filer_quarters'][1]:,}, {r['filers'][0]:,} / {r['filers'][1]:,}")
    print(f"\n  change, 2020Q2 to 2024Q2 minus 2010Q1 to 2019Q4: in shares, se each seed; in log odds, se each seed")
    for key in sorted(chg, key=lambda x: (x[0], band_order[x[1]], x[2])):
        w, b, k = key
        r = chg[key]
        ses = " ".join(f"{x:.3f}" for x in r["se_d"])
        sel = " ".join(f"{x:.3f}" for x in r["se_logit"])
        print(f"  {names[w]:<32} {b:<14} cut {k}  {r['d']:>+7.3f}  se {ses}  {r['z_d']:>+6.2f} se   {r['logit']:>+7.3f}  se {sel}  {r['z_logit']:>+6.2f} se  draws read {r['draws_read']}/{total}")
    nan = sum(int(np.isnan(bt["d"]).sum()) for bt in boots)
    print(f"\n  draw-group pairs with no paired bin: {nan}")


#: stage nine reads what came in after 2020 over these stretches, which are not the spans the criteria read: the
#: zero bound with the deposit surge; the year the target range rose; the failures of March 2023 through the end
#: of the loan data; and after it. The two stretches before 2020 stand as the reference.
CROSSING_SPANS = (("2010Q1", "2014Q4"), ("2015Q1", "2019Q4"), ("2020Q2", "2021Q4"), ("2022Q1", "2022Q4"),
                  ("2023Q1", "2024Q2"), ("2024Q3", "2026Q2"))

#: and year by year, the quarter the rate stepped down to the top of the target range read alone
YEAR_SPANS = (tuple((f"{y}Q1", f"{y}Q4") for y in range(2010, 2020)) + (("2020Q1", "2020Q1"), ("2020Q2", "2020Q4"))
              + tuple((f"{y}Q1", f"{y}Q4") for y in range(2021, 2027)))

#: quantiles printed of a side's price minus the rate
GAP_QUANTILES = (0.25, 0.5, 0.75)


def rounding_state(r, cap: float) -> str:
    """'above', 'not above' or 'undecided'. Expense and average are filed in whole thousands of dollars, and a
    quarter's expense after the first is the difference of two year-to-date figures, so the expense is known to
    half a thousand in the first quarter and to one thousand after it, and the average to half a thousand. A
    reading is decided only where every price those bounds allow lies on one side of the cap."""
    err = 0.5 if r.period.endswith("Q1") else 1.0
    low = 400.0 * max(r.expense - err, 0.0) / (r.average + 0.5)
    high = 400.0 * (r.expense + err) / (r.average - 0.5) if r.average > 0.5 else math.inf
    if low > cap:
        return "above"
    if high <= cap:
        return "not above"
    return "undecided"


def step_not_above(r, price: float, cap: float) -> bool:
    """One thousand dollars of expense on this average does not already read above the rate. Where it does, the
    arm (which admits only a positive expense) holds the filer-quarter only because it paid enough to file a
    thousand, so its reading is the instrument's step; below, a price at the rate still files a thousand after
    the first quarter."""
    return 400.0 / r.average <= cap


def rounding_decides(r, price: float, cap: float) -> bool:
    return rounding_state(r, cap) != "undecided"


def step_and_rounding(r, price: float, cap: float) -> bool:
    return step_not_above(r, price, cap) and rounding_decides(r, price, cap)


#: the readings stage nine reads again: (name, keep), every reading first
INSTRUMENT_FILTERS = (("every reading", None), ("the step alone does not put it above", step_not_above),
                      ("the rounding decides it", rounding_decides), ("both", step_and_rounding))


def range_decides(pcr: dict):
    """keep(r, price, cap) holding where the price lies above the quarter's highest primary credit rate or at or
    below its lowest. The rate a filer faced, weighted by how its balance ran inside the quarter, lies between the
    two, so a price outside them is above or not above that weighted rate whichever way the balance ran."""
    def keep(r, price: float, cap: float) -> bool:
        _mean, low, high = pcr[r.period]
        return price > high or price <= low
    return keep


def all_decide(pcr: dict):
    """keep(r, price, cap) holding where the step, the rounding and the quarter's range of the rate all decide the
    reading: one thousand of expense on the average does not read above the lowest rate, and every price the
    rounding allows lies above the highest rate or at or below the lowest."""
    def keep(r, price: float, cap: float) -> bool:
        _mean, low, high = pcr[r.period]
        return 400.0 / r.average <= low and (rounding_state(r, high) == "above" or rounding_state(r, low) == "not above")
    return keep


#: stage nine, third step: the ever class at the quarter read, by when the edge was used
TIMING_GROUPS = ("ever, used in the four quarters up to it", "ever, used only before those", "ever, first used after it")
#: the first two together: a member that has used the edge by the quarter read, with no loan after it counted
BY_THEN = "ever, used by then"
TIMING_WRITINGS = tuple((g, "outside ever", g) for g in (BY_THEN,) + TIMING_GROUPS)

#: after 2020Q1 the rival is read in three stretches, one criterion each (ruled 2026-09-16), on the members that
#: have used the edge by the quarter read, and on readings the step alone does not put above the rate and the
#: rounding decides; every size split in both scales at once
STRETCH_CRITERIA = (("B113-4a", ("2020Q2", "2021Q4")), ("B113-4b", ("2022Q1", "2022Q4")), ("B113-4c", ("2023Q1", "2024Q2")))
STRETCH_SPANS = tuple(span for _name, span in STRETCH_CRITERIA)
STRETCH_WRITINGS = WRITINGS + TIMING_WRITINGS
BY_THEN_W = [w[0] for w in STRETCH_WRITINGS].index(BY_THEN)

#: B113-5 reads the class difference at two heights over the effective federal funds rate in two spans: the height
#: where the primary credit rate stood in the later span and the one where it stood in the earlier (ruled 2026-09-17).
#: In each span one height is the quarter's own mean rate and the other is that rate moved by the difference between
#: the spans' mean heights of the rate over the effective rate. The earlier span starts where the four quarters before
#: lie inside the loan data, so the class written by then is defined; the later span is the stretch B113-4c reads.
CROSSED_SPANS = (("2011Q3", "2019Q4"), ("2023Q1", "2024Q2"))
#: (name, sign): at the later rate's height the later span minus the earlier; at the earlier rate's height the reverse,
#: so that the rate standing at a height counts positive at both
CROSSED_POSITIONS = (("at the later rate's height", 1.0), ("at the earlier rate's height", -1.0))
CROSSED_WRITINGS = ((BY_THEN, "outside ever", BY_THEN),)


def height_shift(pcr: dict, effr_q: dict, spans=CROSSED_SPANS) -> float:
    """The earlier span's mean height of the primary credit rate over the effective federal funds rate minus the later
    span's, in percentage points, over quarters both files cover."""
    means = []
    for lo, hi in spans:
        qs = [q for q in sorted(pcr) if lo <= q <= hi and q in effr_q]
        means.append(sum(pcr[q][0] - effr_q[q] for q in qs) / len(qs))
    return means[0] - means[1]


def crossed_position(q: str, mean: float, shift_pp: float, which: int, spans=CROSSED_SPANS) -> float:
    """The height read at quarter q, `which` 0 the later rate's and 1 the earlier rate's: in the span where the rate
    stood at that height, the quarter's own mean rate; in the other span, that rate moved by the shift."""
    later = spans[1][0] <= q <= spans[1][1]
    if which == 0:
        return mean if later else mean - shift_pp
    return mean + shift_pp if later else mean


def merge_entries(parts: list) -> dict:
    """One entries structure from parts that each carry a single writing: part i's writing becomes writing i, and
    the filers are pooled, so a draw resamples each filer once across every part."""
    filers = sorted(set().union(*(p["filers"] for p in parts)))
    fidx = {f: i for i, f in enumerate(filers)}
    keys, groups, cell, who, above, out_ids, in_ids, gid = [], [], [], [], [], [], [], []
    for i, p in enumerate(parts):
        ko, go = len(keys), len(groups)
        keys += [(i,) + tuple(k[1:]) for k in p["keys"]]
        groups += [(i,) + tuple(g[1:]) for g in p["groups"]]
        cell.append(p["cell"] + ko)
        who.append(np.array([fidx[f] for f in p["filers"]], dtype=np.int64)[p["who"]])
        above.append(p["above"])
        out_ids.append(p["out_ids"] + ko)
        in_ids.append(p["in_ids"] + ko)
        gid.append(p["gid"] + go)
    if len(set(keys)) != len(keys) or len(set(groups)) != len(groups):
        raise ValueError("merge_entries: two parts share a cell, so a part carries more than one writing")
    return {"keys": keys, "groups": groups, "filers": filers,
            "cell": np.concatenate(cell).astype(np.int64), "who": np.concatenate(who).astype(np.int64),
            "above": np.concatenate(above).astype(float), "out_ids": np.concatenate(out_ids).astype(np.int64),
            "in_ids": np.concatenate(in_ids).astype(np.int64), "gid": np.concatenate(gid).astype(np.int64)}


def crossed_effects(e: dict, point: dict, boots: list) -> dict:
    """{(height, size split): below $10 billion, the class difference at a height in the span where the rate stood
    there minus the same difference in the span where it did not, in shares and log odds, with each seed's standard
    error; groups of `e` are (height, band, span, size split)."""
    at = {g: i for i, g in enumerate(e["groups"])}
    rows = {}
    for p, (_name, sign) in enumerate(CROSSED_POSITIONS):
        for k in SIZE_SPLITS:
            ie, il = at.get((p, POOLED, 0, k)), at.get((p, POOLED, 1, k))
            if ie is None or il is None:
                continue

            def eff(arr, ie=ie, il=il, sign=sign):
                return sign * (arr[..., il] - arr[..., ie])

            se_d = [float(np.nanstd(eff(bt["d"]), ddof=1)) for bt in boots]
            se_l = [float(np.nanstd(eff(bt["logit"]), ddof=1)) for bt in boots]
            d, lg = float(eff(point["d"])), float(eff(point["logit"]))
            rows[(p, k)] = {"d": d, "se_d": se_d, "z_d": ratio(d, float(np.mean(se_d)) if se_d else float("nan")),
                            "z_d_each_seed": [ratio(d, x) for x in se_d],
                            "logit": lg, "se_logit": se_l, "z_logit": ratio(lg, float(np.mean(se_l)) if se_l else float("nan")),
                            "z_logit_each_seed": [ratio(lg, x) for x in se_l],
                            "draws_read": sum(int(np.isfinite(eff(bt["d"])).sum()) for bt in boots)}
    return rows


def crossed_zs(rows: dict, seed=None) -> list:
    """The z of every reading B113-5 rests on: each height, each size split, shares then log odds; a missing one nan."""
    out = []
    for p in range(len(CROSSED_POSITIONS)):
        for k in SIZE_SPLITS:
            r = rows.get((p, k))
            if r is None:
                out += [float("nan"), float("nan")]
            elif seed is None:
                out += [r["z_d"], r["z_logit"]]
            else:
                out += [r["z_d_each_seed"][seed], r["z_logit_each_seed"][seed]]
    return out


def crossed_label(key: tuple) -> str:
    if len(key) == 2:
        p, k = key
        return f"{CROSSED_POSITIONS[p][0]} | cut {k}"
    w, b, s, k = key
    lo, hi = CROSSED_SPANS[s]
    return f"{CROSSED_POSITIONS[w][0]} | {b} | {lo} to {hi} | cut {k}"


def crossed_reading(obs, pcr: dict, effr_q: dict, ever: set, by_q: dict, small_only: set, draws: int, seeds) -> dict:
    """The entries at each height, merged so a draw resamples filers once across both, and what B113-5 reads from them."""
    shift_pp = height_shift(pcr, effr_q)
    parts = [reading_entries(obs, pcr, ever, by_q, small_only, spans=CROSSED_SPANS, keep=step_and_rounding,
                             writings=CROSSED_WRITINGS, timing=lambda q: edge_timing(q, by_q),
                             cap_of=lambda r, rate, which=which: crossed_position(r.period, rate[0], shift_pp, which))
             for which in range(len(CROSSED_POSITIONS))]
    e = merge_entries(parts)
    point = class_difference(e, np.ones(len(e["filers"])))
    boots = [bootstrap(e, draws, sd, changes=False) for sd in seeds]
    heights = {}
    for which, (name, _sign) in enumerate(CROSSED_POSITIONS):
        for lo, hi in CROSSED_SPANS:
            qs = [q for q in sorted(pcr) if lo <= q <= hi and q in effr_q]
            heights[f"{name} | {lo} to {hi}"] = 100.0 * sum(crossed_position(q, pcr[q][0], shift_pp, which) - effr_q[q] for q in qs) / len(qs)
    return {"entries": e, "shift_pp": shift_pp, "heights_bp": heights,
            "readings": reading_rows(e, point, boots), "effects": crossed_effects(e, point, boots)}


def print_crossed(c: dict) -> None:
    print(f"\n  shift between the spans' heights of the rate over the effective rate: {100 * c['shift_pp']:.1f} bp")
    for name, h in c["heights_bp"].items():
        print(f"  height read, {name}: {h:+.1f} bp over the effective rate")
    print("\n  below $10 billion, members that had used the window by then against the class's outside, readings the "
          "instrument decides at each height: outside minus inside, share above the height, se each seed, in se; log odds")
    for key in sorted(k for k in c["readings"] if k[1] == POOLED):
        r = c["readings"][key]
        ses, sel = " ".join(f"{x:.3f}" for x in r["se_d"]), " ".join(f"{x:.3f}" for x in r["se_logit"])
        print(f"  {crossed_label(key):<62} {r['d']:+.3f} se {ses} {r['z_d']:+6.2f}   log odds {r['logit']:+.3f} se {sel} {r['z_logit']:+6.2f}"
              f"   inside {r['inside']:.3f} outside {r['outside']:.3f} bins {r['bins']:>4} filer-quarters {r['filer_quarters'][0]:,}/{r['filer_quarters'][1]:,}")
    print("\n  B113-5 readings: at the later rate's height, the later span minus the earlier; at the earlier rate's height, the reverse")
    for key, r in sorted(c["effects"].items()):
        ses, sel = " ".join(f"{x:.3f}" for x in r["se_d"]), " ".join(f"{x:.3f}" for x in r["se_logit"])
        print(f"  {crossed_label(key):<36} {r['d']:+.3f} se {ses} {r['z_d']:+6.2f}   log odds {r['logit']:+.3f} se {sel} {r['z_logit']:+6.2f}")


def edge_timing(q: str, by_q: dict, k: int = NEAR):
    """{rssd: timing group} for every class member at quarter q: a primary credit loan in the k quarters before q
    or in q; loans only before those; no loan by q, the first after it. None where the k quarters before q start
    before the loan data or q is past their end, since a loan there could not be seen."""
    lo = shift(q, -k)
    if lo < DW_FIRST or q > DW_LAST:
        return None
    current = set().union(*(m for qq, m in by_q.items() if lo <= qq <= q))
    before = set().union(*(m for qq, m in by_q.items() if qq < lo))
    after = set().union(*(m for qq, m in by_q.items() if qq > q))
    # a member in several sets takes the group merged last: a loan in the four quarters, then one before them
    return {**{x: TIMING_GROUPS[2] for x in after}, **{x: TIMING_GROUPS[1] for x in before},
            **{x: TIMING_GROUPS[0] for x in current}}


def timing_objects(obs, pcr: dict, by_q: dict, small_only: set, spans) -> dict:
    """Per span and timing group, below $10 billion, filer-quarters with a price in a quarter the rate file
    covers and the timing defined: filer-quarters, filers, how many filer-quarters belong to members never
    above the recurring amount, and by year the filer-quarters of the member's first loan after the quarter
    (first used after it) or last loan before the four quarters (used only before those)."""
    loans = collections.defaultdict(list)
    for qq, members in by_q.items():
        for x in members:
            loans[x].append(qq)
    cache, acc = {}, collections.defaultdict(lambda: {"n": 0, "filers": set(), "never_above": 0, "years": collections.Counter()})
    for r, _price in obs:
        ss = [i for i, (lo, hi) in enumerate(spans) if lo <= r.period <= hi]
        if r.period not in pcr or not ss or s59.band_of(r.assets) == s59.LARGEST:
            continue
        if r.period not in cache:
            cache[r.period] = edge_timing(r.period, by_q)
        tc = cache[r.period]
        if tc is None or r.rssd not in tc:
            continue
        g = tc[r.rssd]
        if g == TIMING_GROUPS[2]:
            year = min(qq for qq in loans[r.rssd] if qq > r.period)[:4]
        elif g == TIMING_GROUPS[1]:
            year = max(qq for qq in loans[r.rssd] if qq < shift(r.period, -NEAR))[:4]
        else:
            year = None
        for s in ss:
            a = acc[(s, g)]
            a["n"] += 1
            a["filers"].add(r.rssd)
            a["never_above"] += r.rssd in small_only
            if year is not None:
                a["years"][year] += 1
    return {key: {"filer_quarters": a["n"], "filers": len(a["filers"]), "never_above": a["never_above"],
                  "years": dict(sorted(a["years"].items()))} for key, a in sorted(acc.items())}


def print_timing_objects(objs: dict, spans, mode: float) -> None:
    print(f"\n  the ever class by when the edge was used, below $10 billion: filer-quarters, filers, filer-quarters of members "
          f"never above {mode:,.0f}; by year, the first loan after the quarter or the last before its four quarters")
    for s, (lo, hi) in enumerate(spans):
        for g in TIMING_GROUPS:
            o = objs.get((s, g))
            if o is None:
                continue
            years = ", ".join(f"{y} {n:,}" for y, n in o["years"].items())
            print(f"  {span_name(lo, hi):<18} {g:<42} {o['filer_quarters']:>6,} {o['filers']:>5,} {o['never_above']:>6,}  {years}")


def crossing_objects(obs, pcr: dict, effr_q: dict, ever: set, by_q: dict, spans) -> dict:
    """The objects under the class difference below $10 billion, per span, writing (ever, near) and side
    (outside, inside): filer-quarters and filers; the share paying above the quarter's mean rate; the share
    whose average is small enough that the least expense the arm admits, one thousand dollars, already reads
    above the rate, so that the reading is the instrument's step and not what was paid; the share the rounding
    leaves undecided; quartiles of the price minus the rate, and of the price minus the quarter's mean effective
    federal funds rate where the rate file covers the quarter, in basis points; the median average in thousands.
    Per span, the rate's mean height over the effective federal funds rate in basis points, and how many
    filer-quarters carry an expense or an average that is not a whole number of thousands."""
    acc = collections.defaultdict(lambda: {"n": 0, "filers": set(), "above": 0, "step": 0, "undecided": 0,
                                            "gap": [], "gap_effr": [], "average": []})
    near_cache, not_whole = {}, collections.Counter()
    for r, price in obs:
        rate = pcr.get(r.period)
        ss = [i for i, (lo, hi) in enumerate(spans) if lo <= r.period <= hi]
        if rate is None or not ss or s59.band_of(r.assets) == s59.LARGEST:
            continue
        if r.period not in near_cache:
            near_cache[r.period] = near_class(r.period, by_q)
        nc = near_cache[r.period]
        sides = [("ever", "inside" if r.rssd in ever else "outside")]
        if nc is not None:
            sides.append(("near", "inside" if r.rssd in nc else "outside"))
        cap = rate[0]
        undecided = rounding_state(r, cap) == "undecided"
        for s in ss:
            not_whole[s] += r.expense != round(r.expense) or r.average != round(r.average)
            for w, side in sides:
                a = acc[(s, w, side)]
                a["n"] += 1
                a["filers"].add(r.rssd)
                a["above"] += price > cap
                a["step"] += 400.0 / r.average > cap
                a["undecided"] += undecided
                a["gap"].append(100.0 * (price - cap))
                if r.period in effr_q:
                    a["gap_effr"].append(100.0 * (price - effr_q[r.period]))
                a["average"].append(r.average)
    cells = {key: {"filer_quarters": a["n"], "filers": len(a["filers"]), "above": a["above"] / a["n"],
                   "step_above": a["step"] / a["n"], "undecided": a["undecided"] / a["n"],
                   "gap_bp": [float(np.quantile(a["gap"], q)) for q in GAP_QUANTILES],
                   "gap_effr_bp": [float(np.quantile(a["gap_effr"], q)) for q in GAP_QUANTILES] if a["gap_effr"] else None,
                   "median_average": float(np.median(a["average"]))}
             for key, a in sorted(acc.items())}
    height = {}
    for s, (lo, hi) in enumerate(spans):
        qs = [q for q in sorted(pcr) if lo <= q <= hi and q in effr_q]
        if qs:
            height[s] = 100.0 * sum(pcr[q][0] - effr_q[q] for q in qs) / len(qs)
    return {"cells": cells, "rate_over_effr_bp": height, "not_whole": dict(not_whole)}


def span_name(lo: str, hi: str) -> str:
    if lo == hi:
        return lo
    if lo[:4] == hi[:4] and lo.endswith("Q1") and hi.endswith("Q4"):
        return lo[:4]
    return f"{lo} to {hi}"


def print_crossing_objects(objs: dict, spans, writing: str) -> None:
    cells = objs["cells"]
    print(f"\n  {writing}, below $10 billion, each pair outside / inside: the rate over the effective rate (bp); "
          f"filer-quarters; filers; share above the rate; share the step alone puts above; share the rounding leaves "
          f"undecided; price minus the rate at the quartiles (bp); median price minus the effective rate (bp); median average "
          f"($ thousands); not whole")
    print(f"  {'span':<18} {'rate-EFFR':>9} {'filer-quarters':>15} {'filers':>11} {'above':>11} {'step':>11} "
          f"{'undecided':>11}  {'price minus rate, outside':>25}  {'price minus rate, inside':>24}  {'minus EFFR':>11}  {'median average':>15} {'not whole':>9}")
    for s, (lo, hi) in enumerate(spans):
        o, i = cells.get((s, writing, "outside")), cells.get((s, writing, "inside"))
        if o is None or i is None:
            print(f"  {span_name(lo, hi):<18} {'-':>9}  one side has no filer-quarter")
            continue
        h = objs["rate_over_effr_bp"].get(s, float("nan"))
        go = "/".join(f"{x:+.0f}" for x in o["gap_bp"])
        gi = "/".join(f"{x:+.0f}" for x in i["gap_bp"])
        ge = "/".join("-" if c["gap_effr_bp"] is None else f"{c['gap_effr_bp'][1]:+.0f}" for c in (o, i))
        print(f"  {span_name(lo, hi):<18} {h:>+9.1f} {o['filer_quarters']:>7,}/{i['filer_quarters']:<7,} "
              f"{o['filers']:>5,}/{i['filers']:<5,} {o['above']:>5.3f}/{i['above']:<5.3f} {o['step_above']:>5.3f}/{i['step_above']:<5.3f} "
              f"{o['undecided']:>5.3f}/{i['undecided']:<5.3f}  {go:>25}  {gi:>24}  {ge:>11}  "
              f"{o['median_average']:>7,.0f}/{i['median_average']:<7,.0f} {objs['not_whole'].get(s, 0):>9}")


def print_crossing_readings(e: dict, point: dict, boots: list, spans, mode: float, arm: str,
                            writings=WRITINGS, order=(0, 1, 3, 2)) -> None:
    names = [w[0].replace("the recurring amount", f"{mode:,.0f}") for w in writings]
    at = {g: i for i, g in enumerate(e["groups"])}
    rows = reading_rows(e, point, boots) if boots else None
    how = f"se each seed from {len(boots[0]['d'])} draws" if boots else "point readings, no resampling"
    print(f"\n  class difference below $10 billion, arm {arm}: outside minus inside, share above the rate, and in log "
          f"odds; inside and outside shares under the same weights; paired bins; {how}")
    for w in order:
        print(f"\n  {names[w]}")
        for s, (lo, hi) in enumerate(spans):
            for k in SIZE_SPLITS if boots else (max(SIZE_SPLITS),):
                i = at.get((w, POOLED, s, k))
                if i is None:
                    continue
                if rows is None:
                    print(f"  {span_name(lo, hi):<18} cut {k}  {float(point['d'][i]):>+7.3f}  log odds {float(point['logit'][i]):>+7.3f}  "
                          f"inside {float(point['inside'][i]):.3f} outside {float(point['outside'][i]):.3f}  bins {int(point['bins'][i])}")
                    continue
                r = rows[(w, POOLED, s, k)]
                ses = " ".join(f"{x:.3f}" for x in r["se_d"])
                sel = " ".join(f"{x:.3f}" for x in r["se_logit"])
                print(f"  {span_name(lo, hi):<18} cut {k}  {r['d']:>+7.3f}  se {ses}  {r['z_d']:>+6.2f}   log odds {r['logit']:>+7.3f}  "
                      f"se {sel}  {r['z_logit']:>+6.2f}   inside {r['inside']:.3f} outside {r['outside']:.3f}  bins {r['bins']:>4}  "
                      f"filer-quarters {r['filer_quarters'][0]:,}/{r['filer_quarters'][1]:,}, filers {r['filers'][0]:,}/{r['filers'][1]:,}")


RESULT_AFTER_2020 = ROOT / "results" / "b113_after_2020.json"

#: the readings stage nine writes to its own record: (name, keep built from the rate file), every reading first
AFTER_2020_FILTERS = (("every reading", lambda pcr: None), ("the step alone does not put it above", lambda pcr: step_not_above),
                      ("the rounding decides it", lambda pcr: rounding_decides), ("both", lambda pcr: step_and_rounding),
                      ("the range decides it", range_decides), ("the step, the rounding and the range all decide it", all_decide))
#: (arm, the filters read on it): the stable arm is read under the filters `--hikes` read it under
AFTER_2020_ARMS = (("all", (0, 1, 2, 3, 4, 5)), ("stable", (0, 4, 5)))


def point_rows(e: dict, point: dict) -> dict:
    """{(writing, band, span, size split): the point reading with its shares, paired bins and counts}, no resampling."""
    counts = collections.defaultdict(lambda: [0, 0])
    distinct = collections.defaultdict(lambda: (set(), set()))
    for c, f in zip(e["cell"].tolist(), e["who"].tolist()):
        key = e["keys"][c]
        counts[key[:4]][key[6]] += 1
        distinct[key[:4]][key[6]].add(f)
    rows = {}
    for gi, (w, b, s, k) in enumerate(e["groups"]):
        n, fs = [0, 0], (set(), set())
        for bb in band_members(b):
            n = [n[0] + counts[(w, bb, s, k)][0], n[1] + counts[(w, bb, s, k)][1]]
            fs = (fs[0] | distinct[(w, bb, s, k)][0], fs[1] | distinct[(w, bb, s, k)][1])
        rows[(w, b, s, k)] = {"d": float(point["d"][gi]), "logit": float(point["logit"][gi]), "inside": float(point["inside"][gi]),
                              "outside": float(point["outside"][gi]), "bins": int(point["bins"][gi]),
                              "filer_quarters": n, "filers": [len(fs[0]), len(fs[1])]}
    return rows


def after_label(key: tuple, spans, writings) -> str:
    w, b, s, k = key
    return f"{writings[w][0]} | {b} | {span_name(*spans[s])} | cut {k}"


def objects_json(objs: dict, spans) -> dict:
    return {"cells": {f"{span_name(*spans[s])} | {w} | {side}": v for (s, w, side), v in objs["cells"].items()},
            "rate_over_effr_bp": {span_name(*spans[s]): v for s, v in objs["rate_over_effr_bp"].items()},
            "not_whole": {span_name(*spans[s]): v for s, v in objs["not_whole"].items()}}


def timing_json(objs: dict, spans) -> dict:
    return {f"{span_name(*spans[s])} | {g}": v for (s, g), v in objs.items()}


def run_after_2020(draws: int, seeds: list, out=print) -> dict:
    """What stage nine prints, to a record: objects, timing objects, and readings under each filter on each arm."""
    dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
    index, _clashes = aba_index(build_por(out=out))
    j = join(dw, index)
    ever, by_q = edge_classes(j["matched"])
    panel = s59.load_panel()
    lo = loan_object(j["matched"], panel)
    small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
    secondary = collections.defaultdict(set)
    for x in j["matched"]:
        if x["type"] == "secondary":
            secondary[x["rssd"]].add(x["quarter"])
    pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
    _years, effr_q = s59.load_effr()
    qrows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
    timing = lambda q: edge_timing(q, by_q)  # noqa: E731
    rec = {"stage": "B113", "part": "after 2020Q1", "definitions": DEFINITIONS,
           "objects": {}, "timing_objects": {}, "readings": {},
           "rate_moved_inside": sorted(q for q, (_m, low, high) in pcr.items() if high > low and "2010Q1" <= q <= "2026Q2")}
    obs_all = arm_obs(qrows, "all", secondary)
    for label, spans in (("stretches", CROSSING_SPANS), ("years", YEAR_SPANS)):
        rec["objects"][label] = objects_json(crossing_objects(obs_all, pcr, effr_q, ever, by_q, spans), spans)
        rec["timing_objects"][label] = timing_json(timing_objects(obs_all, pcr, by_q, small_only, spans), spans)
    for arm, which in AFTER_2020_ARMS:
        obs = arm_obs(qrows, arm, secondary)
        rec["readings"][arm] = {}
        for i in which:
            name, build_keep = AFTER_2020_FILTERS[i]
            keep = build_keep(pcr)
            e = reading_entries(obs, pcr, ever, by_q, small_only, spans=CROSSING_SPANS, keep=keep, writings=STRETCH_WRITINGS, timing=timing)
            boots = [bootstrap(e, draws, sd, changes=False) for sd in seeds]
            rows = reading_rows(e, class_difference(e, np.ones(len(e["filers"]))), boots)
            ey = reading_entries(obs, pcr, ever, by_q, small_only, spans=YEAR_SPANS, keep=keep, writings=STRETCH_WRITINGS, timing=timing)
            years = point_rows(ey, class_difference(ey, np.ones(len(ey["filers"]))))
            rec["readings"][arm][name] = {
                "stretches": {after_label(k, CROSSING_SPANS, STRETCH_WRITINGS): v for k, v in sorted(rows.items()) if k[1] == POOLED},
                "years": {after_label(k, YEAR_SPANS, STRETCH_WRITINGS): v for k, v in sorted(years.items())
                          if k[1] == POOLED and k[3] == max(SIZE_SPLITS)}}
            out(f"  arm {arm}, {name}: {len(e['filers']):,} filers, {len(e['cell']):,} entries")
    rec["config"] = {
        "loans_cache": "data/cache/b113_dw_loans.json", "loans_cache_sha256": s59.sha256_of(dwl.CACHE),
        "call_report_cache": "data/cache/b59_call_report.json", "call_report_cache_sha256": s59.sha256_of(drv.CACHE),
        "primary_credit_rate": "data/b59/DPCREDIT.csv", "primary_credit_rate_sha256": s59.sha256_of(PCR_CSV),
        "effective_rate": "data/b59/EFFR.csv", "effective_rate_sha256": s59.sha256_of(s59.EFFR_CSV),
        "loan_data_span": [DW_FIRST, DW_LAST], "near_window_quarters": NEAR, "timing_window_quarters": NEAR,
        "pooled_bands": band_members(POOLED), "size_splits": list(SIZE_SPLITS), "years_read_at_cut": max(SIZE_SPLITS),
        "logit_add": LOGIT_ADD, "gap_quantiles": list(GAP_QUANTILES), "stretches": [list(x) for x in CROSSING_SPANS],
        "years": [list(x) for x in YEAR_SPANS], "writings": [w[0] for w in STRETCH_WRITINGS],
        "filters": [name for name, _b in AFTER_2020_FILTERS],
        "arms": {arm: [AFTER_2020_FILTERS[i][0] for i in which] for arm, which in AFTER_2020_ARMS},
        "stable_arm_band_of_the_average": list(s59.STABLE), "bootstrap_draws": draws, "seeds": list(seeds)}
    return rec


def selftest() -> int:
    fails = []

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    expect(shift("2010Q3", -4) == "2009Q3" and shift("2024Q2", 4) == "2025Q2" and shift("2012Q4", 1) == "2013Q1",
           "quarters step across years")
    por_text = ("IDRSSD\tFDIC Certificate Number\tPrimary ABA Routing Number\tFinancial Institution Name\n"
                "111\t1\t22306847\tA\n222\t2\t0\tB\n333\t3\t\tC\n444\t4\t011000015\tD\n")
    m = por_map(por_text)
    expect(m == {"111": "022306847", "444": "011000015"},
           "a panel number loses no leading zero, and a filer with no number is left out")
    try:
        por_map("IDRSSD\tName\n111\tA\n")
        refused = ""
    except ValueError as e:
        refused = str(e)
    expect(refused.startswith("panel of reporters lacks") and "Primary ABA Routing Number" in refused,
           "a panel without the routing number column is refused, naming the column")
    por = {"2012Q1": {"aba": {"111": "022306847", "555": "099999999", "556": "099999999", "888": "123456789"}},
           "2012Q2": {"aba": {"777": "022306847", "999": "033333333"}}}
    index, clashes = aba_index(por)
    expect(index["2012Q1"] == {"022306847": "111", "123456789": "888"} and clashes == {"2012Q1": 1, "2012Q2": 0},
           "a number two filers carry in one period joins neither, and is counted")
    dw = {"2012Q1": {"loans": [
            {"aba": "022306847", "type": "primary", "borrower": "A BK", "state": "NY", "date": "2012-01-05", "amount": 1.0, "collateral": 9.0,
             "term": 3, "aggregated": True},
            {"aba": "271000000", "type": "primary", "borrower": "PEOPLES FCU", "state": "MI", "date": "2012-01-06", "amount": 1.0, "collateral": 9.0},
            {"aba": "123456789", "type": "seasonal", "borrower": "FARM ST BK", "state": "IA", "date": "2012-01-07", "amount": 1.0, "collateral": 9.0},
            {"aba": "555555555", "type": "secondary", "borrower": "WEAK BK", "state": "IL", "date": "2012-01-08", "amount": 1.0, "collateral": 9.0},
            {"aba": "033333333", "type": "seasonal", "borrower": "HARBOR CU", "state": "MA", "date": "2012-01-09", "amount": 1.0, "collateral": 9.0}]},
          "2012Q2": {"loans": [
            {"aba": "022306847", "type": "primary", "borrower": "A BK", "state": "NY", "date": "2012-04-05", "amount": 1.0, "collateral": 9.0},
            {"aba": "022306847", "type": "secondary", "borrower": "A BK", "state": "NY", "date": "2012-04-06", "amount": 1.0, "collateral": 9.0},
            {"aba": "123456789", "type": "primary", "borrower": "FARM ST BK", "state": "IA", "date": "2012-04-07", "amount": 1.0, "collateral": 9.0}]},
          "2012Q3": {"loans": [{"aba": "022306847", "type": "primary", "borrower": "A BK", "state": "NY", "date": "2012-07-05", "amount": 1.0, "collateral": 9.0}]}}
    j = join(dw, index)
    who = [(x["quarter"], x["rssd"]) for x in j["matched"]]
    expect(who == [("2012Q1", "111"), ("2012Q1", "888"), ("2012Q2", "777"), ("2012Q2", "777")],
           "a loan joins through the panel of its own quarter, so a number that changed hands names the right filer")
    expect((j["matched"][0]["term"], j["matched"][0]["aggregated"], j["matched"][1]["term"], j["matched"][1]["aggregated"])
           == (3, True, None, False),
           "a joined loan carries its term and whether its row sums several loans")
    expect(j["unmatched"] == {("primary", "credit union by name"): 1, ("secondary", "number in no panel"): 1,
                              ("primary", "number in another quarter's panel"): 1, ("seasonal", "number in another quarter's panel"): 1,
                              ("primary", "no panel for the quarter"): 1},
           "loans that do not join are counted by why: no panel, a number another quarter's panel carries whatever the name, credit union by name, the rest")
    expect(list(j["unmatched_sample"]) == ["secondary, number in no panel", "seasonal, number in another quarter's panel",
                                           "primary, number in another quarter's panel"],
           "and the two number reasons are sampled by name, the other two are not")
    ever, by_q = edge_classes(j["matched"])
    expect(ever == {"111", "777"} and by_q == {"2012Q1": {"111"}, "2012Q2": {"777"}},
           "only primary credit makes a filer part of the class: one whose only loan is seasonal is not in it")
    expect(j["elsewhere_primary"] == ["123456789"] and possible_misses(j["elsewhere_primary"], index, ever) == ({"888"}, {"888"})
           and possible_misses(j["elsewhere_primary"], index, ever | {"888"}) == ({"888"}, set()),
           "a primary loan's number that another quarter's panel carries names a filer, counted as a miss only outside the class")
    by_q2 = {"2011Q1": {"a"}, "2012Q1": {"b"}, "2012Q2": {"c"}, "2013Q1": {"d"}, "2013Q2": {"e"}}
    expect(near_class("2012Q1", by_q2) == {"a", "b", "c", "d"},
           "the near class takes four quarters either side and no more")
    expect(near_class("2010Q4", by_q2) is None and near_class("2024Q1", by_q2) is None
           and near_class("2011Q3", by_q2) is not None and near_class("2023Q2", by_q2) is not None,
           "and is undefined where its window leaves the loan data")
    R = s59.Row
    obs = [(R("2012Q1", "111", 1.0, 0.0, 1.0, 0.0, 1.0, 100_000.0, 1.0), 1.0),
           (R("2012Q1", "888", 1.0, 0.0, 1.0, 0.0, 1.0, 120_000.0, 1.0), 1.0),
           (R("2012Q1", "999", 1.0, 0.0, 1.0, 0.0, 1.0, 20_000_000.0, 1.0), 1.0)]
    cells = class_cells(obs, {"111"}, {"2012Q1": {"111"}})
    small = [c for c in cells if c["band"] == s59.SMALLEST][0]
    big = [c for c in cells if c["band"] == s59.LARGEST][0]
    expect(small == {"quarter": "2012Q1", "band": s59.SMALLEST, "filers": 2, "ever": 1, "near": 1}
           and big["filers"] == 1 and big["ever"] == 0,
           "per quarter and band, filers with a price are counted with how many are in each class")
    mt = [{"quarter": "2012Q1", "rssd": "A", "type": "primary", "date": "2012-01-05", "amount": 1000.0, "collateral": 5e6, "term": 1, "aggregated": False},
          {"quarter": "2012Q1", "rssd": "A", "type": "primary", "date": "2012-02-05", "amount": 1000.0, "collateral": 1e7, "term": 1, "aggregated": False},
          {"quarter": "2012Q1", "rssd": "B", "type": "primary", "date": "2012-01-20", "amount": 1000.0, "collateral": 1e6, "term": 1, "aggregated": False},
          {"quarter": "2012Q2", "rssd": "B", "type": "primary", "date": "2012-05-05", "amount": 5_000_000.0, "collateral": 2e7, "term": 3, "aggregated": True},
          {"quarter": "2012Q1", "rssd": "C", "type": "primary", "date": "2012-03-05", "amount": 1000.0, "collateral": None, "term": 1, "aggregated": False},
          {"quarter": "2012Q1", "rssd": "D", "type": "seasonal", "date": "2012-03-06", "amount": 9e8, "collateral": 9e8, "term": 28, "aggregated": False}]
    pn = {"2012Q1": {"A": {"2170": 100_000.0}, "B": {"2170": 50_000_000.0}}, "2012Q2": {"B": {"2170": 200_000.0}}}
    lo = loan_object(mt, pn)
    rows = {r["rssd"]: r for r in lo["members"]}
    expect(lo["mode"] == 1000.0 and lo["loans"] == 5 and lo["aggregated"] == 1
           and lo["top_amounts"] == [(1000.0, 4), (5_000_000.0, 1)] and lo["terms"] == [(1, 4), (3, 1)] and lo["terms_at_mode"] == [(1, 4)]
           and lo["years"] == {"2012": {"loans": 5, "at_mode": 4, "filers": 3, "never_above_mode": 2}},
           "the amount that recurs most is read off primary credit alone, and each year counts the filers never above it")
    expect(rows["A"]["band"] == s59.SMALLEST and abs(rows["A"]["largest_over_assets"] - 1e-5) < 1e-18
           and abs(rows["A"]["collateral_over_assets"] - 0.1) < 1e-15 and rows["A"]["never_above_mode"],
           "a loan over assets turns assets filed in thousands into dollars, and collateral keeps the member's largest ratio")
    expect(rows["B"]["band"] == s59.SMALLEST and abs(rows["B"]["largest_over_assets"] - 0.025) < 1e-15
           and not rows["B"]["never_above_mode"] and rows["B"]["loans"] == 2,
           "a member's band is read in the quarter of its largest loan, not of its first")
    expect(rows["C"]["band"] is None and rows["C"]["largest_over_assets"] is None and "D" not in rows,
           "a member with no assets that quarter has no band and no ratio, and seasonal credit makes no member")
    expect([decade(x) for x in (1e-5, 0.025, 5e-12, 3.0)] == [-5, -2, -9, 0] and decade(0.0) is None,
           "a ratio falls in the power of ten below it, clipped at both ends")
    pq = pcr_quarters("observation_date,DPCREDIT\n2012-01-03,0.50\n2012-03-30,1.00\n2012-04-02,0.75\n2012-06-29,\n")
    expect(pq == {"2012Q1": (0.75, 0.50, 1.00), "2012Q2": (0.75, 0.75, 0.75)},
           "the rate file gives each quarter its mean, low and high, and a blank day is skipped")
    try:
        pcr_quarters("observation_date,EFFR\n2012-01-03,0.10\n")
        refused = ""
    except ValueError as e:
        refused = str(e)
    expect(refused.startswith("expected one DPCREDIT column"), "a rate file whose column is not DPCREDIT is refused")
    ob = [(R("2012Q1", "111", 1.0, 0.0, 1.0, 0.0, 1.0, 100_000.0, 1.0), 0.80),
          (R("2012Q1", "888", 1.0, 0.0, 1.0, 0.0, 1.0, 120_000.0, 1.0), 0.75),
          (R("2012Q1", "999", 1.0, 0.0, 1.0, 0.0, 1.0, 20_000_000.0, 1.0), 2.00),
          (R("2009Q4", "111", 1.0, 0.0, 1.0, 0.0, 1.0, 100_000.0, 1.0), 1.00),
          (R("2024Q1", "111", 1.0, 0.0, 1.0, 0.0, 1.0, 100_000.0, 1.0), 5.00)]
    ac, unc = above_cells(ob, {"2012Q1": (0.75, 0.50, 1.00), "2024Q1": (5.50, 5.50, 5.50)},
                          {"111", "999"}, {"2011Q1": {"111"}}, {"111"})
    got = {(c["quarter"], c["band"], c["group"]): (c["filers"], c["above"]) for c in ac}
    S, L = s59.SMALLEST, s59.LARGEST
    expect(unc == 1 and got == {
        ("2012Q1", S, "ever"): (1, 1), ("2012Q1", S, GROUPS[2]): (1, 1), ("2012Q1", S, "outside ever"): (1, 0),
        ("2012Q1", S, "near"): (1, 1), ("2012Q1", S, "outside near"): (1, 0),
        ("2012Q1", L, "ever"): (1, 1), ("2012Q1", L, GROUPS[3]): (1, 1), ("2012Q1", L, "outside near"): (1, 1),
        ("2024Q1", S, "ever"): (1, 0), ("2024Q1", S, GROUPS[2]): (1, 0)},
           "a price counts above only past the quarter's mean rate, each writing of the class gets its cell, "
           "and near has none where its window leaves the loan data")
    R2 = s59.Row
    fx = []
    for q, prices in (("2012Q1", {"O1": 1.0, "O2": 0.75, "I1": 0.5, "I2": 0.5}), ("2020Q2", {"O1": 1.0, "O2": 1.0, "I1": 0.1, "I2": 0.1}),
                      ("2024Q3", {"O1": 6.0, "O2": 1.0, "I1": 1.0, "I2": 1.0})):
        for f, assets in (("O1", 100_000.0), ("I1", 110_000.0), ("O2", 200_000.0), ("I2", 210_000.0)):
            fx.append((R2(q, f, 1.0, 0.0, 1.0, 0.0, 1.0, assets, 1.0), prices[f]))
    for f, assets, price in (("O3", 2_000_000.0, 1.0), ("I3", 2_100_000.0, 0.5), ("O4", 20_000_000.0, 1.0), ("I4", 21_000_000.0, 0.5)):
        fx.append((R2("2012Q1", f, 1.0, 0.0, 1.0, 0.0, 1.0, assets, 1.0), price))
    ex = reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75), "2020Q2": (0.25, 0.25, 0.25), "2024Q3": (5.40, 5.40, 5.40)}, {"I1", "I2", "I3", "I4"},
                         {"2012Q1": {"I1", "I2"}, "2020Q2": {"I1", "I2"}}, {"I1"})
    pt = class_difference(ex, np.ones(len(ex["filers"])))
    at = {g: i for i, g in enumerate(ex["groups"])}
    S2 = s59.SMALLEST
    def dd(w, s, k, res=pt):
        i = at.get((w, S2, s, k))
        return None if i is None else round(float(res["d"][i]), 12)
    expect(size_bins([("b", 5.0), ("a", 5.0), ("c", 1.0)], 2) == {"c": 0, "a": 0, "b": 1},
           "a band is cut by the rank of assets, ties broken by id")
    expect((dd(0, 0, 1), dd(0, 0, 2), dd(0, 0, 4), dd(1, 0, 1), dd(2, 0, 1), dd(2, 0, 2), dd(3, 0, 1), dd(3, 0, 2))
           == (0.5, 0.5, None, 0.5, 0.5, 1.0, 0.5, 0.0),
           "the difference is outside minus inside inside each size bin, a bin with one side empty drops out, and each writing reads its own inside")
    expect(round(float(pt["inside"][at[(0, S2, 0, 1)]]), 12) == 0.0 and round(float(pt["outside"][at[(0, S2, 0, 1)]]), 12) == 0.5
           and int(pt["bins"][at[(0, S2, 0, 2)]]) == 2,
           "the inside share, the outside share and the paired bins are printed with it")
    expect(not any(k[0] == 1 and k[2] == 3 for k in ex["keys"]) and any(k[0] == 0 and k[2] == 3 for k in ex["keys"]),
           "the near writing has no cell in a quarter its window leaves the loan data, while ever does")
    m0 = np.ones(len(ex["filers"]))
    m0[ex["filers"].index("I2")] = 0
    p0 = class_difference(ex, m0)
    expect(int(p0["bins"][at[(0, S2, 0, 2)]]) == 1 and int(p0["bins"][at[(3, S2, 0, 1)]]) == 0,
           "a bin left with one side empty by a draw drops out of the pairs")
    m3 = np.ones(len(ex["filers"]))
    m3[ex["filers"].index("O1")] = 3
    p3 = class_difference(ex, m3)
    expect((dd(0, 0, 1, p3), dd(0, 0, 2, p3)) == (0.75, 0.6),
           "a filer drawn three times brings its quarters three times, and paired bins weigh 1/(1/n_out + 1/n_in)")
    ip, ib = at.get((0, POOLED, 0, 1)), at.get((0, s59.LARGEST, 0, 1))
    expect(ip is not None and ib is not None
           and round(float(pt["d"][ip]), 12) == round(2 / 3, 12) and round(float(pt["d"][ib]), 12) == 1.0
           and abs(float(pt["logit"][ip]) - (math.log(5) + 0.5 * math.log(9)) / 1.5) < 1e-12,
           "the three bands below 10bn pool their paired bins under the same weights, and the band above stays out")
    expect(abs(float(pt["logit"][at[(0, S2, 0, 1)]]) - math.log(5)) < 1e-12,
           "the log odds difference moves each count by a half, so an empty side still has a finite log")
    expect({k: round(float(v), 12) for k, v in span_change(ex["groups"], pt["d"]).items() if k[2] == 1 and k[1] == S2}
           == {(0, S2, 1): 0.5, (1, S2, 1): 0.5, (2, S2, 1): 0.5, (3, S2, 1): 0.5},
           "the change is the later span's difference minus the earlier span's")
    b1 = bootstrap(ex, 5, 7)
    b2 = bootstrap(ex, 5, 7)
    expect(np.array_equal(b1["d"], b2["d"], equal_nan=True) and b1["d"].shape == (5, len(ex["groups"]))
           and np.array_equal(b1["ch_logit"], b2["ch_logit"], equal_nan=True) and not np.array_equal(b1["logit"], b1["d"], equal_nan=True),
           "the bootstrap repeats under one seed, and carries the log odds apart from the shares")
    expect(spans_of("2015Q1") == [0, 4] and spans_of("2012Q1") == [0] and spans_of("2021Q1") == [2] and spans_of("2009Q4") == [],
           "a quarter belongs to every span it falls in, and the last span overlaps the first")
    expect((state([2.0, 3.1]), state([-2.5, -2.0]), state([2.5, 1.99]), state([2.5, float("nan")]), state([]))
           == ("above", "below", "unread", "unread", "unread"),
           "a state needs every reading past the line, and a missing reading leaves it unread")
    loans_ka = {"2012Q1": {"loans": [
        {"type": "primary", "date": "2012-01-03", "rate": 0.75, "borrower": "A", "district": "x"},
        {"type": "primary", "date": "2012-01-05", "rate": 1.00, "borrower": "B", "district": "x"},
        {"type": "seasonal", "date": "2012-01-05", "rate": 9.00, "borrower": "C", "district": "x"}]}}
    rate_text = "observation_date,DPCREDIT\n2012-01-03,0.75\n2012-01-05,0.75\n2012-01-06,1.00\n"
    ka = rate_known_answer(loans_ka, rate_text)
    loans_ka["2012Q1"]["loans"].append({"type": "primary", "date": "2012-01-03", "rate": 2.00, "borrower": "D", "district": "x"})
    ka_bad = rate_known_answer(loans_ka, rate_text)
    expect(ka["exact"] == 1 and ka["within_two_days"] == 1 and ka["unmatched"] == [] and len(ka_bad["unmatched"]) == 1,
           "a primary credit loan matches the rate of its day or of a day within two, and one that matches neither is named")

    def fake_rows(z0, z2, near2=None):
        rr = {}
        for w in (0, 1, 2, 3):
            for s, zz in ((0, z0), (2, near2 if (w == 1 and near2 is not None) else z2)):
                for k in SIZE_SPLITS:
                    rr[(w, POOLED, s, k)] = {"z_d": zz[0], "z_logit": zz[1], "z_d_each_seed": [zz[0], zz[2]],
                                             "z_logit_each_seed": [zz[1], zz[1]]}
        return rr

    def fake_changes(zz):
        return {(p, k): {"z_d": zz[0], "z_logit": zz[1], "z_d_each_seed": [zz[0], zz[2]], "z_logit_each_seed": [zz[1], zz[1]]}
                for p in range(len(CROSSED_POSITIONS)) for k in SIZE_SPLITS}

    def fake_stretch(zzs, other=(9.0, 9.0, 9.0)):
        rr = {}
        for w in range(len(STRETCH_WRITINGS)):
            for s, zz in enumerate(zzs):
                zz = zz if w == BY_THEN_W else other
                for k in SIZE_SPLITS:
                    rr[(w, POOLED, s, k)] = {"z_d": zz[0], "z_logit": zz[1], "z_d_each_seed": [zz[0], zz[2]],
                                             "z_logit_each_seed": [zz[1], zz[1]]}
        return rr

    jj = {"matched": [1, 2, 3], "unmatched": {("primary", "credit union by name"): 2, ("seasonal", "number in no panel"): 1}}
    ok_ka = {"exact": 10, "within_two_days": 0, "unmatched": []}
    cg = build_criteria(6, jj, ok_ka, fake_rows((3.0, 3.0, 3.1), (2.5, 2.5, 2.5), near2=(2.5, 1.9, 2.5)), fake_changes((0.5, 0.5, 0.5)),
                        fake_stretch([(2.5, 2.5, 2.5), (1.0, 1.0, 1.0), (3.0, 2.2, 3.0)], other=(-9.0, -9.0, -9.0)))
    got_cg = {k: (c["passed"], c.get("grid")) for k, c in cg.items()}
    expect(got_cg == {"B113-1": (True, None), "B113-2": (True, None), "B113-3": (True, "B"), "B113-4a": (True, "B"),
                      "B113-4b": (None, "unread"), "B113-4c": (True, "B"), "B113-5": (None, None), "B113-6": (True, None)},
           "the criteria map every reading past the line to B, one short of it to no verdict, and seeds that agree to a pass; "
           "each stretch reads the members that had used the window by then and no other writing")
    cb = build_criteria(7, jj, {"exact": 10, "within_two_days": 0, "unmatched": ["x"]},
                        fake_rows((-3.0, -2.5, -3.0), (2.5, 2.5, 2.5)), fake_changes((-2.5, -2.2, -2.4)),
                        fake_stretch([(-2.5, -2.5, -2.5), (2.5, 2.5, 1.5), (2.5, 1.9, 2.5)]))
    got_cb = {k: (c["passed"], c.get("grid")) for k, c in cb.items()}
    expect(got_cb == {"B113-1": (False, None), "B113-2": (False, None), "B113-3": (True, "both_unmet"), "B113-4a": (True, "both_unmet"),
                      "B113-4b": (True, "B"), "B113-4c": (None, "unread"), "B113-5": (False, None), "B113-6": (False, None)},
           "and each of them fails on its planted input: a loan lost, a rate unmatched, both sides unmet, a narrowing, "
           "and one seed alone moving a stretch's verdict across the line")
    cs = build_criteria(6, jj, ok_ka, fake_rows((2.5, 2.5, 1.5), (2.5, 2.5, 2.5)), fake_changes((0.5, 0.5, 0.5)),
                        fake_stretch([(2.5, 2.5, 2.5)] * 3))
    expect((cs["B113-3"]["grid"], cs["B113-6"]["passed"]) == ("B", False),
           "one seed alone moving the first span's verdict fails the seed check too")
    holed = fake_rows((3.0, 3.0, 3.0), (2.5, 2.5, 2.5))
    del holed[(1, POOLED, 0, max(SIZE_SPLITS))]
    sholed = fake_stretch([(2.5, 2.5, 2.5)] * 3)
    del sholed[(BY_THEN_W, POOLED, 2, max(SIZE_SPLITS))]
    ch_holed = build_criteria(6, jj, ok_ka, holed, fake_changes((0.5, 0.5, 0.5)), sholed)
    expect((ch_holed["B113-3"]["passed"], ch_holed["B113-3"]["grid"], ch_holed["B113-4a"]["grid"], ch_holed["B113-4c"]["grid"],
            ch_holed["B113-4c"]["passed"]) == (None, "unread", "B", "unread", None)
           and STRETCH_SPANS == (("2020Q2", "2021Q4"), ("2022Q1", "2022Q4"), ("2023Q1", "2024Q2"))
           and STRETCH_WRITINGS[BY_THEN_W][0] == BY_THEN,
           "a verdict reading that is missing leaves its criterion without a verdict, the near writing counts for the "
           "first span, and a stretch's own reading counts for the stretch")
    expect(split_shape(fake_rows((3.0, 3.0, 3.0), (2.5, 2.5, 2.5)), 0)["shape"] == "the edge alone"
           and SPLIT_SHAPES[("above", "unread")] == "the edge in use" and len(SPLIT_SHAPES) == 9,
           "the split's shape is named for every pair of states")
    rq = s59.Row

    def caught(fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except Exception as exc:  # a planted fault that raises is named by the check below, not left to stop the test
            return exc

    got_rs = [caught(rounding_state, rq(q, "x", 0.0, 0.0, 0.0, 0.0, ex_, 100_000.0, av), cap) for q, ex_, av, cap in (
        ("2012Q1", 3.0, 400.0, 1.0), ("2012Q2", 1.0, 1000.0, 0.30), ("2012Q1", 1.0, 1000.0, 0.30), ("2012Q1", 1.0, 1000.0, 0.15),
        ("2012Q2", 1.0, 1000.0, 0.15), ("2012Q2", 1.0, 10000.0, 0.50), ("2012Q2", 1.0, 0.5, 50.0), ("2012Q1", 1.0, 1.0, 200.0),
        ("2012Q2", 1.0, 2.0, 400.0), ("2012Q1", 1.0, 600.5, 1.0))]
    expect(got_rs == ["above", "undecided", "undecided", "above", "undecided", "not above", "undecided", "undecided", "undecided",
                      "not above"],
           "the rounding decides a reading only where every price the whole-thousand bounds allow lies on one side of the rate, "
           "the first quarter's expense known to half a thousand and a later quarter's to one")
    cobs = [(rq("2012Q1", "O", 0.0, 0.0, 0.0, 0.0, 2.0, 100_000.0, 800.0), 1.0),
            (rq("2012Q1", "I", 0.0, 0.0, 0.0, 0.0, 1.0, 200_000.0, 2000.0), 0.2),
            (rq("2012Q1", "L", 0.0, 0.0, 0.0, 0.0, 5.0, 20_000_000.0, 100.0), 20.0),
            (rq("2012Q2", "O", 0.0, 0.0, 0.0, 0.0, 1.875, 100_000.0, 1000.0), 0.75),
            (rq("2012Q3", "O", 0.0, 0.0, 0.0, 0.0, 1.0, 100_000.0, 100.0), 4.0),
            (rq("2024Q1", "I", 0.0, 0.0, 0.0, 0.0, 1.0, 100_000.0, 50.0), 8.0)]
    co = caught(crossing_objects, cobs, {"2012Q1": (0.75, 0.75, 0.75), "2012Q2": (0.75, 0.50, 1.00), "2012Q3": (0.75, 0.75, 0.75),
                                 "2024Q1": (5.50, 5.50, 5.50)},
                          {"2012Q1": 0.10, "2012Q2": 0.20, "2024Q1": 5.33}, {"I"}, {"2012Q1": {"I"}},
                          (("2012Q1", "2012Q4"), ("2024Q1", "2024Q4")))

    def cobj(c):
        return (c["filer_quarters"], c["filers"], round(c["above"], 9), round(c["step_above"], 9), round(c["undecided"], 9),
                [round(x, 9) for x in c["gap_bp"]], [round(x, 9) for x in c["gap_effr_bp"]], round(c["median_average"], 9))

    expect(isinstance(co, dict) and {k: cobj(v) for k, v in co["cells"].items()} == {
        (0, "ever", "outside"): (3, 1, 0.666666667, 0.333333333, 1.0, [12.5, 25.0, 175.0], [63.75, 72.5, 81.25], 800.0),
        (0, "ever", "inside"): (1, 1, 0.0, 0.0, 0.0, [-55.0, -55.0, -55.0], [10.0, 10.0, 10.0], 2000.0),
        (0, "near", "outside"): (3, 1, 0.666666667, 0.333333333, 1.0, [12.5, 25.0, 175.0], [63.75, 72.5, 81.25], 800.0),
        (0, "near", "inside"): (1, 1, 0.0, 0.0, 0.0, [-55.0, -55.0, -55.0], [10.0, 10.0, 10.0], 2000.0),
        (1, "ever", "inside"): (1, 1, 1.0, 1.0, 1.0, [250.0, 250.0, 250.0], [267.0, 267.0, 267.0], 50.0)},
           "the objects below 10bn count each side's filer-quarters, a price at the rate is not above it, the step reads "
           "one thousand of expense on the average, the price is set against the effective rate only in quarters its file covers, "
           "the band above 10bn stays out, and near has no side where it is undefined")
    expect(isinstance(co, dict) and {s: round(v, 9) for s, v in co["rate_over_effr_bp"].items()} == {0: 60.0, 1: 17.0}
           and co["not_whole"] == {0: 1, 1: 0},
           "the rate's height over the effective rate is the mean over quarters both files cover, and an expense "
           "that is not a whole thousand is counted")
    ex2 = reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75), "2020Q2": (0.25, 0.25, 0.25), "2024Q3": (5.40, 5.40, 5.40)}, {"I1", "I2", "I3", "I4"},
                          {"2012Q1": {"I1", "I2"}, "2020Q2": {"I1", "I2"}}, {"I1"}, spans=(("2020Q2", "2021Q4"),))
    expect(len(ex2["cell"]) == 42 and {k[2] for k in ex2["keys"]} == {0} and {k[4] for k in ex2["keys"]} == {"2020Q2"},
           "stretches other than the criteria's are read when given, and only the quarters inside them enter")
    b3 = bootstrap(ex2, 3, 7, changes=False)
    expect(set(b3) == {"d", "logit"} and b3["d"].shape == (3, len(ex2["groups"])),
           "and their draws carry no change, since those stretches have no earlier and later span")
    expect((span_name("2012Q1", "2012Q4"), span_name("2020Q1", "2020Q1"), span_name("2020Q2", "2020Q4"))
           == ("2012", "2020Q1", "2020Q2 to 2020Q4") and YEAR_SPANS[10:12] == (("2020Q1", "2020Q1"), ("2020Q2", "2020Q4"))
           and len(YEAR_SPANS) == 18,
           "a stretch is named by its year when it is one, and the quarter the rate stepped down stands alone")
    ek = reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75), "2020Q2": (0.25, 0.25, 0.25), "2024Q3": (5.40, 5.40, 5.40)}, {"I1", "I2", "I3", "I4"},
                         {"2012Q1": {"I1", "I2"}, "2020Q2": {"I1", "I2"}}, {"I1"}, keep=lambda r, p, c: not (r.rssd == "O1" and r.period == "2012Q1"))
    base = reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75), "2020Q2": (0.25, 0.25, 0.25), "2024Q3": (5.40, 5.40, 5.40)}, {"I1", "I2", "I3", "I4"},
                           {"2012Q1": {"I1", "I2"}, "2020Q2": {"I1", "I2"}}, {"I1"})
    o1 = base["filers"].index("O1")
    o1_2012 = sum(1 for c, w in zip(base["cell"].tolist(), base["who"].tolist()) if w == o1 and base["keys"][c][4] == "2012Q1")
    placed = {(ek["keys"][c][5], ek["keys"][c][6], ek["filers"][w]) for c, w in zip(ek["cell"].tolist(), ek["who"].tolist())
              if ek["keys"][c][:5] == (0, s59.SMALLEST, 0, 2, "2012Q1")}
    expect(len(ek["cell"]) == len(base["cell"]) - o1_2012 and o1_2012 > 0 and "O1" in ek["filers"]
           and placed == {(0, 1, "I1"), (0, 0, "O2"), (1, 1, "I2")},
           "a filer-quarter the filter refuses leaves every cell, and the size bins are cut again among the filers kept")
    rk = [(step_not_above(rq("2012Q2", "x", 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, av), 0.0, cap), rounding_decides(rq("2012Q2", "x", 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, av), 0.0, cap),
           step_and_rounding(rq("2012Q2", "x", 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, av), 0.0, cap)) for av, cap in ((1000.0, 0.30), (1000.0, 0.50), (10000.0, 0.50), (100.0, 5.0), (1000.0, 0.40))]
    expect(rk == [(False, False, False), (True, False, False), (True, True, True), (True, False, False), (True, False, False)]
           and [x[0] for x in INSTRUMENT_FILTERS] == ["every reading", "the step alone does not put it above", "the rounding decides it", "both"]
           and INSTRUMENT_FILTERS[0][1] is None,
           "the step keeps a reading only where a thousand of expense on its average is not above the rate, the rounding only "
           "where it decides, and both only where both do")
    byt = {"2011Q1": {"a"}, "2012Q1": {"b", "a"}, "2013Q2": {"c"}, "2012Q3": {"d"}, "2014Q1": {"a", "c"}, "2013Q1": {"e"}}
    T0, T1, T2 = TIMING_GROUPS
    expect(edge_timing("2013Q1", byt) == {"a": T0, "b": T0, "d": T0, "e": T0, "c": T2}
           and edge_timing("2013Q3", byt) == {"c": T0, "d": T0, "e": T0, "a": T1, "b": T1}
           and edge_timing("2011Q3", byt) == {"a": T0, "b": T2, "c": T2, "d": T2, "e": T2}
           and edge_timing("2011Q2", byt) is None and edge_timing("2024Q3", byt) is None,
           "a member is current with a loan in the four quarters up to the quarter read, earlier with loans only before "
           "those, later with none by then, and the split is undefined where a loan could not be seen")
    et = reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75), "2020Q2": (0.25, 0.25, 0.25), "2024Q3": (5.40, 5.40, 5.40)}, {"I1", "I2", "I3", "I4"},
                         {"2012Q1": {"I1", "I2"}, "2020Q2": {"I1", "I2"}}, {"I1"}, writings=WRITINGS + TIMING_WRITINGS,
                         timing=lambda q: {"I1": T0, "I2": T2, "I3": T1} if q == "2012Q1" else None)
    tw = {w: sorted({(ek_[4], ek_[6], ek_[1], et["filers"][wh]) for c_, wh in zip(et["cell"].tolist(), et["who"].tolist())
                     for ek_ in (et["keys"][c_],) if ek_[0] == w and ek_[3] == 1 and ek_[6] == 1}) for w in (4, 5, 6, 7)}
    outs = {w: sorted({(ek_[4], ek_[1]) for ek_ in et["keys"] if ek_[0] == w and ek_[3] == 1 and ek_[6] == 0}) for w in (4, 5, 6, 7)}
    out_all = [("2012Q1", s59.LARGEST), ("2012Q1", "1bn to 10bn"), ("2012Q1", s59.SMALLEST)]
    expect(tw == {4: [("2012Q1", 1, "1bn to 10bn", "I3"), ("2012Q1", 1, s59.SMALLEST, "I1")], 5: [("2012Q1", 1, s59.SMALLEST, "I1")],
                  6: [("2012Q1", 1, "1bn to 10bn", "I3")], 7: [("2012Q1", 1, s59.SMALLEST, "I2")]}
           and all(outs[w] == out_all for w in (4, 5, 6, 7))
           and [x[0] for x in TIMING_WRITINGS] == [BY_THEN, T0, T1, T2]
           and not any(k_[0] >= 4 for k_ in reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75)}, {"I1"}, {}, set())["keys"]),
           "each timing writing takes its own members inside and the class's outside, only in quarters the timing is defined, "
           "and used by then takes the current and the earlier members and not the later")
    tob = timing_objects([(rq("2013Q1", "c", 0.0, 0.0, 0.0, 0.0, 1.0, 100_000.0, 100.0), 4.0),
                          (rq("2013Q3", "a", 0.0, 0.0, 0.0, 0.0, 1.0, 100_000.0, 100.0), 4.0),
                          (rq("2013Q3", "b", 0.0, 0.0, 0.0, 0.0, 1.0, 20_000_000.0, 100.0), 4.0),
                          (rq("2013Q1", "a", 0.0, 0.0, 0.0, 0.0, 1.0, 100_000.0, 100.0), 4.0),
                          (rq("2011Q2", "a", 0.0, 0.0, 0.0, 0.0, 1.0, 100_000.0, 100.0), 4.0)],
                         {"2013Q1": (1.0, 1.0, 1.0), "2013Q3": (1.0, 1.0, 1.0), "2011Q2": (1.0, 1.0, 1.0)}, byt, {"c"}, (("2011Q1", "2014Q4"),))
    expect(tob == {(0, T0): {"filer_quarters": 1, "filers": 1, "never_above": 0, "years": {}},
                   (0, T1): {"filer_quarters": 1, "filers": 1, "never_above": 0, "years": {"2012": 1}},
                   (0, T2): {"filer_quarters": 1, "filers": 1, "never_above": 1, "years": {"2013": 1}}},
           "the timing objects date a later member by its first loan after the quarter and an earlier one by its last loan "
           "before the four quarters, and leave out the band above 10bn and quarters the timing is undefined")
    pr = {"2022Q2": (1.0, 0.5, 1.75)}
    rd, ad = range_decides(pr), all_decide(pr)
    expect([rd(rq("2022Q2", "x", 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0), p_, 1.0) for p_ in (2.0, 0.5, 1.0, 1.75, 0.49)]
           == [True, True, False, False, True],
           "the range decides a price above the quarter's highest rate or at or below its lowest, and nothing between")
    expect([ad(rq("2022Q2", "x", 0.0, 0.0, 0.0, 0.0, ex_, 1.0, av), 400.0 * ex_ / av, 1.0) for ex_, av in
            ((50.0, 10000.0), (10.0, 10000.0), (44.0, 10000.0), (45.0, 10000.0), (50.0, 500.0), (25.0, 10000.0))]
           == [True, True, False, True, False, False],
           "all three decide only where the rounding's whole interval clears the range and a thousand of expense does not "
           "read above the lowest rate")
    prw = point_rows(ex, pt)
    ipool = at.get((0, POOLED, 0, 1))
    expect(ipool is not None
           and {k: (v["filer_quarters"], v["filers"], round(v["d"], 12), v["bins"], round(v["inside"], 12), round(v["outside"], 12))
                for k, v in prw.items() if k in ((0, POOLED, 0, 1), (0, S2, 0, 1))}
           == {(0, POOLED, 0, 1): ([3, 3], [3, 3], round(2 / 3, 12), 2, round(float(pt["inside"][ipool]), 12),
                                  round(float(pt["outside"][ipool]), 12)),
               (0, S2, 0, 1): ([2, 2], [2, 2], 0.5, 1, 0.0, 0.5)},
           "a point row pools the counts of the bands below 10bn and carries the reading, its shares and its paired bins")
    small12 = [(rw, p_) for rw, p_ in fx if rw.period == "2012Q1" and rw.assets < 250_000]
    fx2 = small12 + [(s59.Row("2012Q2", rw.rssd, rw.ff, rw.rp, rw.ff_prev, rw.rp_prev, rw.expense, rw.assets, rw.average), p_)
                     for rw, p_ in small12]
    ex2p = reading_entries(fx2, {"2012Q1": (0.75, 0.75, 0.75), "2012Q2": (0.75, 0.75, 0.75)}, {"I1", "I2"}, {"2012Q1": {"I1", "I2"}}, {"I1"})
    pr2 = point_rows(ex2p, class_difference(ex2p, np.ones(len(ex2p["filers"]))))
    expect((pr2[(0, S2, 0, 1)]["filer_quarters"], pr2[(0, S2, 0, 1)]["filers"]) == ([4, 4], [2, 2]),
           "a filer read in two quarters of a stretch counts twice as filer-quarters and once as a filer")
    expect(after_label((BY_THEN_W, POOLED, 1, 4), CROSSING_SPANS, STRETCH_WRITINGS) == "ever, used by then | all below 10bn | 2015Q1 to 2019Q4 | cut 4"
           and after_label((0, POOLED, 3, 4), YEAR_SPANS, STRETCH_WRITINGS) == "ever | all below 10bn | 2013 | cut 4",
           "a reading in the stage nine record is labelled by writing, band, stretch and cut")
    oj = objects_json(co, (("2012Q1", "2012Q4"), ("2024Q1", "2024Q4"))) if isinstance(co, dict) else {}
    expect(sorted(oj.get("cells", {})) == ["2012 | ever | inside", "2012 | ever | outside", "2012 | near | inside",
                                             "2012 | near | outside", "2024 | ever | inside"]
           and {k: round(v, 9) for k, v in oj["rate_over_effr_bp"].items()} == {"2012": 60.0, "2024": 17.0}
           and oj["not_whole"] == {"2012": 1, "2024": 0}
           and sorted(timing_json(tob, (("2011Q1", "2014Q4"),))) == sorted(f"2011Q1 to 2014Q4 | {g}" for g in TIMING_GROUPS),
           "the objects and timing objects are keyed by stretch, writing and side in the record")
    expect([x[0] for x in AFTER_2020_FILTERS] == ["every reading", "the step alone does not put it above", "the rounding decides it",
                                                  "both", "the range decides it", "the step, the rounding and the range all decide it"]
           and AFTER_2020_FILTERS[0][1](pr) is None and AFTER_2020_FILTERS[3][1](pr) is step_and_rounding
           and [AFTER_2020_FILTERS[4][1](pr)(rq("2022Q2", "x", 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0), p_, 1.0) for p_ in (2.0, 1.0)] == [True, False]
           and AFTER_2020_ARMS == (("all", (0, 1, 2, 3, 4, 5)), ("stable", (0, 4, 5))),
           "the record reads every filter on the arm of every row and the three range filters on the stable arm")
    cm = fake_changes((3.0, 3.0, 3.0))
    for k in SIZE_SPLITS:
        cm[(1, k)] = {"z_d": 3.0, "z_logit": 1.0, "z_d_each_seed": [3.0, 3.0], "z_logit_each_seed": [1.0, 1.0]}
    c5 = [build_criteria(6, jj, ok_ka, fake_rows((3.0, 3.0, 3.0), (2.5, 2.5, 2.5)), cr, fake_stretch([(2.5, 2.5, 2.5)] * 3))["B113-5"]["passed"]
          for cr in (fake_changes((2.5, 2.5, 2.5)), cm)]
    expect(c5 == [True, None],
           "B113-5 passes where every reading at both heights clears the line, and one height's log odds short of it leaves no verdict")
    c56 = build_criteria(6, jj, ok_ka, fake_rows((3.0, 3.0, 3.0), (2.5, 2.5, 2.5)), fake_changes((2.5, 2.5, 1.5)),
                         fake_stretch([(2.5, 2.5, 2.5)] * 3))
    expect((c56["B113-5"]["passed"], c56["B113-6"]["passed"]) == (True, False),
           "one seed alone moving B113-5 across the line fails the seed check")
    fzs = {(p, k): {"z_d": 10 * p + k, "z_logit": -(10 * p + k), "z_d_each_seed": [p, k], "z_logit_each_seed": [k, p]}
           for p in (0, 1) for k in SIZE_SPLITS}
    expect(crossed_zs(fzs) == [1, -1, 2, -2, 4, -4, 11, -11, 12, -12, 14, -14] and crossed_zs(fzs, seed=1)[:2] == [1, 0]
           and math.isnan(crossed_zs({})[0]),
           "B113-5 reads the later rate's height then the earlier's, every size split, shares then log odds, a missing one as nan")
    hsh = caught(height_shift, {"2015Q1": (1.0, 1.0, 1.0), "2016Q1": (1.5, 1.5, 1.5), "2017Q1": (2.0, 2.0, 2.0), "2023Q1": (5.0, 5.0, 5.0)},
                 {"2015Q1": 0.4, "2016Q1": 0.9, "2023Q1": 4.83})
    expect(isinstance(hsh, float) and abs(hsh - 0.43) < 1e-12
           and [round(crossed_position(q_, m_, 0.45, wh), 12) for q_, m_, wh in (("2015Q1", 1.0, 0), ("2015Q1", 1.0, 1), ("2023Q2", 5.0, 0), ("2023Q2", 5.0, 1))]
           == [0.55, 1.0, 5.0, 5.45],
           "the shift is the earlier span's mean height over the effective rate minus the later's, over quarters both files cover, "
           "and each height is the rate itself in the span where the rate stood there and the rate moved by the shift in the other")
    ec1 = reading_entries(fx, {"2012Q1": (0.75, 0.75, 0.75)}, {"I1", "I2", "I3", "I4"}, {"2012Q1": {"I1", "I2"}}, {"I1"},
                          spans=(("2012Q1", "2012Q4"),), writings=WRITINGS[:1], cap_of=lambda r, rate: 0.6, keep=lambda r, p_, c_: c_ < 0.7)
    pc1 = caught(class_difference, ec1, np.ones(len(ec1["filers"])))
    i1 = {g: i for i, g in enumerate(ec1["groups"])}.get((0, S2, 0, 1))
    expect(i1 is not None and isinstance(pc1, dict) and round(float(pc1["d"][i1]), 12) == 1.0,
           "a price is read against the height given, and the filter is asked at that height")
    spans_x = (("2012Q1", "2012Q4"), ("2020Q2", "2020Q4"))
    pcr_x = {"2012Q1": (0.75, 0.75, 0.75), "2020Q2": (0.25, 0.25, 0.25)}
    parts_x = [reading_entries(fx, pcr_x, {"I1", "I2", "I3", "I4"}, {"2012Q1": {"I1", "I2"}, "2020Q2": {"I1", "I2"}}, {"I1"},
                               spans=spans_x, writings=WRITINGS[:1],
                               cap_of=lambda r, rate, wh=wh: crossed_position(r.period, rate[0], 0.3, wh, spans=spans_x)) for wh in (0, 1)]
    mx = caught(merge_entries, parts_x)
    fxe = caught(lambda: crossed_effects(mx, class_difference(mx, np.ones(len(mx["filers"]))), []))
    expect(isinstance(fxe, dict) and set(fxe) == {(p, k) for p in (0, 1) for k in (1, 2)} and round(fxe[(0, 1)]["d"], 12) == 1.0
           and round(fxe[(1, 1)]["d"], 12) == round(-1 / 3, 12),
           "at the later rate's height the reading is the later span's difference minus the earlier's, and at the earlier "
           "rate's height the earlier's minus the later's")
    parts_m = [reading_entries(fx, pcr_x, {"I1", "I2", "I3", "I4"}, {"2012Q1": {"I1", "I2"}}, {"I1"}, spans=spans_x, writings=WRITINGS[:1],
                               keep=kp) for kp in (None, lambda r, p_, c_: r.rssd != "I1")]
    mm = caught(merge_entries, parts_m)
    same = isinstance(mm, dict)
    if same:
        mult = np.ones(len(mm["filers"]))
        mult[mm["filers"].index("O1")] = 3
        mult[mm["filers"].index("I2")] = 2
        dm = class_difference(mm, mult)["d"]
        atm = {g: i for i, g in enumerate(mm["groups"])}
        for i, part in enumerate(parts_m):
            mp = np.array([mult[mm["filers"].index(f)] for f in part["filers"]])
            dp = class_difference(part, mp)["d"]
            same = same and all(np.isclose(dm[atm[(i,) + tuple(g[1:])]], dp[j], equal_nan=True) for j, g in enumerate(part["groups"]))
    try:
        merge_entries([parts_m[0], parts_x[0], {**parts_m[0]}])
        refused = False
    except ValueError:
        refused = True
    expect(same and len(mm["filers"]) == len(parts_m[0]["filers"]) and "I1" not in parts_m[1]["filers"] and not refused,
           "a merged draw resamples each filer once across the parts, so each part reads as it would under the same filers' draw")
    two = dict(parts_m[0])
    two["keys"] = parts_m[0]["keys"] + [(1,) + tuple(k[1:]) for k in parts_m[0]["keys"][:1]]
    try:
        merge_entries([two, two])
        refused2 = False
    except ValueError:
        refused2 = True
    expect(refused2, "parts that share a cell are refused")
    if fails:
        print("\n  selftest FAILED")
        return 1
    print("\n  selftest passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--classes", action="store_true", help="the join, the class, and the cells per quarter and band")
    ap.add_argument("--loans", action="store_true", help="what a primary credit loan looks like, and each class member's largest")
    ap.add_argument("--above", action="store_true", help="per band, quarter and class writing, the share paying above the primary credit rate")
    ap.add_argument("--readings", action="store_true", help="the class difference inside size bins, with filer bootstrap standard errors")
    ap.add_argument("--draws", type=int, default=500)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(RECORD_ARMS) + ["stable"])
    ap.add_argument("--write", action="store_true", help=f"compute the criteria and write the record to results/")
    ap.add_argument("--crossing", action="store_true", help="what came in after 2020: objects and the difference over stretches and years")
    ap.add_argument("--instrument", action="store_true", help="the difference over the stretches again, on the readings the instrument decides")
    ap.add_argument("--timing", action="store_true", help="the ever class split by when the edge was used, against the class's outside")
    ap.add_argument("--hikes", action="store_true", help="the writings again where the quarter's range of the rate decides the reading")
    ap.add_argument("--write-after-2020", action="store_true", help="write what stage nine prints to results/b113_after_2020.json")
    ap.add_argument("--crossed", action="store_true", help="what B113-5 reads: the class difference at the two rates' heights in the two spans")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.crossed:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
        _years, effr_q = s59.load_effr()
        obs = s59.arm_rc_k(s59.quarter_rows(panel, "2010Q1", "2026Q2"))
        print_crossed(crossed_reading(obs, pcr, effr_q, ever, by_q, small_only, a.draws, a.seeds))
        return 0
    if a.write_after_2020:
        rec = run_after_2020(a.draws, a.seeds)
        RESULT_AFTER_2020.write_text(json.dumps(s59.rounded(rec, 6), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8", newline="\n")
        print(f"wrote {RESULT_AFTER_2020.relative_to(ROOT).as_posix()}")
        return 0
    if a.write:
        rec = run_record(a.draws, a.seeds)
        RESULT.write_text(json.dumps(s59.rounded(rec, 6), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
        print(f"wrote {RESULT.relative_to(ROOT).as_posix()}")
        s59.print_criteria(rec["criteria"])
        failed = [k for k, c in rec["criteria"].items() if c["passed"] is False]
        if failed:
            print("\n  FAILED[" + ",".join(rec["criteria"][k]["kind"] for k in failed) + "]: " + ", ".join(failed))
        return 2 if failed else 0
    if a.classes:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        por = build_por()
        index, clashes = aba_index(por)
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        obs = s59.arm_rc_k(s59.quarter_rows(panel, "2010Q1", "2026Q2"))
        print_classes(j, ever, by_q, class_cells(obs, ever, by_q), clashes, index)
        return 0
    if a.loans:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        print_loans(loan_object(join(dw, index)["matched"], s59.load_panel()))
        return 0
    if a.above:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        obs = s59.arm_rc_k(s59.quarter_rows(panel, "2010Q1", "2026Q2"))
        cells, uncovered = above_cells(obs, pcr_quarters(PCR_CSV.read_text(encoding="utf-8")), ever, by_q, small_only)
        print_above(cells, uncovered, pcr_quarters(PCR_CSV.read_text(encoding="utf-8")), lo["mode"])
        return 0
    if a.readings:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        rows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
        pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
        secondary = collections.defaultdict(set)
        for x in j["matched"]:
            if x["type"] == "secondary":
                secondary[x["rssd"]].add(x["quarter"])
        for arm in a.arms:
            obs = arm_obs(rows, arm, secondary)
            e = reading_entries(obs, pcr, ever, by_q, small_only)
            point = class_difference(e, np.ones(len(e["filers"])))
            boots = [bootstrap(e, a.draws, s) for s in a.seeds]
            print_readings(e, point, boots, a.draws, tuple(a.seeds), lo["mode"], arm)
        return 0
    if a.hikes:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        rows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
        pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
        secondary = collections.defaultdict(set)
        for x in j["matched"]:
            if x["type"] == "secondary":
                secondary[x["rssd"]].add(x["quarter"])
        writings = WRITINGS + TIMING_WRITINGS
        order = (0, 1, len(WRITINGS))
        moved = sorted(q for q, (_m, low, high) in pcr.items() if high > low and "2010Q1" <= q <= "2026Q2")
        print(f"  quarters the rate moved inside: {len(moved)}: " + ", ".join(moved))
        for arm in a.arms:
            obs = arm_obs(rows, arm, secondary)
            for name, keep in (("every reading", None), ("the range decides it", range_decides(pcr)),
                               ("the step, the rounding and the range all decide it", all_decide(pcr))):
                print(f"\n  ===== fed funds arm: {arm}; readings kept: {name} =====")
                e = reading_entries(obs, pcr, ever, by_q, small_only, spans=CROSSING_SPANS, keep=keep, writings=writings,
                                    timing=lambda q: edge_timing(q, by_q))
                point = class_difference(e, np.ones(len(e["filers"])))
                boots = [bootstrap(e, a.draws, sd, changes=False) for sd in a.seeds]
                print_crossing_readings(e, point, boots, CROSSING_SPANS, lo["mode"], arm, writings=writings, order=order)
                e = reading_entries(obs, pcr, ever, by_q, small_only, spans=YEAR_SPANS, keep=keep, writings=writings,
                                    timing=lambda q: edge_timing(q, by_q))
                print_crossing_readings(e, class_difference(e, np.ones(len(e["filers"]))), [], YEAR_SPANS, lo["mode"], arm,
                                        writings=writings, order=order)
        return 0
    if a.timing:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        rows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
        pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
        secondary = collections.defaultdict(set)
        for x in j["matched"]:
            if x["type"] == "secondary":
                secondary[x["rssd"]].add(x["quarter"])
        writings = WRITINGS + TIMING_WRITINGS
        order = (0,) + tuple(range(len(WRITINGS), len(writings)))
        for arm in a.arms:
            obs = arm_obs(rows, arm, secondary)
            print(f"\n  ===== fed funds arm: {arm} =====")
            for spans in (CROSSING_SPANS, YEAR_SPANS):
                print_timing_objects(timing_objects(obs, pcr, by_q, small_only, spans), spans, lo["mode"])
            for name, keep in (INSTRUMENT_FILTERS[0], INSTRUMENT_FILTERS[-1]):
                print(f"\n  ===== fed funds arm: {arm}; readings kept: {name} =====")
                e = reading_entries(obs, pcr, ever, by_q, small_only, spans=CROSSING_SPANS, keep=keep, writings=writings,
                                    timing=lambda q: edge_timing(q, by_q))
                point = class_difference(e, np.ones(len(e["filers"])))
                boots = [bootstrap(e, a.draws, sd, changes=False) for sd in a.seeds]
                print_crossing_readings(e, point, boots, CROSSING_SPANS, lo["mode"], arm, writings=writings, order=order)
                e = reading_entries(obs, pcr, ever, by_q, small_only, spans=YEAR_SPANS, keep=keep, writings=writings,
                                    timing=lambda q: edge_timing(q, by_q))
                print_crossing_readings(e, class_difference(e, np.ones(len(e["filers"]))), [], YEAR_SPANS, lo["mode"], arm,
                                        writings=writings, order=order)
        return 0
    if a.instrument:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        rows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
        pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
        secondary = collections.defaultdict(set)
        for x in j["matched"]:
            if x["type"] == "secondary":
                secondary[x["rssd"]].add(x["quarter"])
        for arm in a.arms:
            obs = arm_obs(rows, arm, secondary)
            for name, keep in INSTRUMENT_FILTERS:
                print(f"\n  ===== fed funds arm: {arm}; readings kept: {name} =====")
                e = reading_entries(obs, pcr, ever, by_q, small_only, spans=CROSSING_SPANS, keep=keep)
                point = class_difference(e, np.ones(len(e["filers"])))
                boots = [bootstrap(e, a.draws, sd, changes=False) for sd in a.seeds]
                print_crossing_readings(e, point, boots, CROSSING_SPANS, lo["mode"], arm)
            print(f"\n  ===== fed funds arm: {arm}; readings kept: both; year by year =====")
            e = reading_entries(obs, pcr, ever, by_q, small_only, spans=YEAR_SPANS, keep=step_and_rounding)
            print_crossing_readings(e, class_difference(e, np.ones(len(e["filers"]))), [], YEAR_SPANS, lo["mode"], arm)
        return 0
    if a.crossing:
        dw = json.loads(dwl.CACHE.read_text(encoding="utf-8"))
        index, _clashes = aba_index(build_por())
        j = join(dw, index)
        ever, by_q = edge_classes(j["matched"])
        panel = s59.load_panel()
        lo = loan_object(j["matched"], panel)
        small_only = {m["rssd"] for m in lo["members"] if m["never_above_mode"]}
        rows = s59.quarter_rows(panel, "2010Q1", "2026Q2")
        pcr = pcr_quarters(PCR_CSV.read_text(encoding="utf-8"))
        _years, effr_q = s59.load_effr()
        secondary = collections.defaultdict(set)
        for x in j["matched"]:
            if x["type"] == "secondary":
                secondary[x["rssd"]].add(x["quarter"])
        for arm in a.arms:
            obs = arm_obs(rows, arm, secondary)
            print(f"\n  ===== fed funds arm: {arm} =====")
            for spans, draws in ((YEAR_SPANS, 0), (CROSSING_SPANS, a.draws)):
                objs = crossing_objects(obs, pcr, effr_q, ever, by_q, spans)
                for writing in ("ever", "near"):
                    print_crossing_objects(objs, spans, writing)
                e = reading_entries(obs, pcr, ever, by_q, small_only, spans=spans)
                point = class_difference(e, np.ones(len(e["filers"])))
                boots = [bootstrap(e, draws, sd, changes=False) for sd in a.seeds] if draws else []
                print_crossing_readings(e, point, boots, spans, lo["mode"], arm)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
