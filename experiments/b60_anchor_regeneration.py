"""B60: does an anchor regenerate down a propagation chain?

Registered in the price-theory outline, 2026-08-31, before any of this data was
touched: if a level anchor regenerates, then two distant regions conditional on
the middle segment should be close to independent, while a field served by one
anchor reaching both directly should leave them conditionally dependent.

That sentence is conditional and its antecedent is false on this carrier, so the
conditional-independence reading is not scored here; B60-2 carries the premise
and the reason. What this carrier does return is the graded reading, B60-3, and
a near-far comparison does not need the antecedent. Read the criteria for which
is which before taking any number out of this file.

The design sheet is a four-box arithmetic sheet held outside this repository.
What it fixes and this file implements:

* Three arms. **Far**: two states, conditioning on a third. **Near**, the
  positive control: three districts inside one state, which must return a
  non-zero or the instrument is reading nothing and the stage has no object.
  **Replication**: the same triples on a second commodity.
  The third unit is any other unit of the same kind. It is not checked for lying
  between the two ends, and no propagation link between the three is verified,
  because no adjacency or routing data for these markets is on disk. What the
  two arms therefore compare is residual association after conditioning on one
  other market of the same kind, at two distances, and the arms are built the
  same way so the comparison between them is like for like. Betweenness would be
  needed by the conditional-independence reading, and that reading is withdrawn
  on the premise below, so building it would buy an argument nobody is now
  making.
* No line is drawn on the partial correlation. What carries is the difference
  between the near arm and the far arm on one instrument, read against a floor
  that is measured rather than declared.
* The floor is a time-shift placebo. Shifting one end's series by whole seasons
  destroys the real alignment and keeps the autocorrelation, which is what
  manufactures a spurious partial correlation on series this persistent: the
  lag-60-day autocorrelation of the two thickest states is 0.90 and 0.94. The
  daily reading shifts by days and the monthly one by calendar months, because
  a monthly change is stamped on the first of its month and a day count does
  not land there.
* Two readings, because they answer two questions and the design says to report
  both rather than pick. **Levels** is the object the claim is about, since an
  anchor supplies a constant. **Monthly changes** is shock transmission, and it
  is reported beside it with its own floor.

Usage::

    python experiments/b60_anchor_regeneration.py
    python experiments/b60_anchor_regeneration.py --commodity "Cowpea (Lobia-Karamani)"

Writes ``results/b60_anchor_regeneration.json``.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
RESULTS = ROOT / "results"

#: Whole-year and half-year shifts for the daily reading. A shift shorter than
#: the season would keep part of the real alignment, which would put signal into
#: the floor and bias the whole reading toward "nothing here".
SHIFTS_DAYS = (180, 365, 545, 730, 1095)

#: The same shifts for the monthly reading, in calendar months, because a
#: monthly change is stamped on the first of its month and a day count does not
#: land there. Measured 2026-09-10 on the month keys this file builds: of 113
#: month keys on Lentil, a 180-day shift finds a partner for 0 of them and a
#: 545-day shift for 0, because no run of six consecutive months is 180 days and
#: no run of eighteen is 545; 365 days finds 76, 730 finds 48 and 1095 finds 24,
#: the shortfalls being leap days. So the declared five-shift placebo was a
#: two-shift placebo on truncated windows, and the two that survived were
#: selected by where February 29 fell. Calendar months make every key match.
SHIFTS_MONTHS = (6, 12, 18, 24, 36)

#: A triple is only read where the middle actually mediates. This is not a
#: threshold on the estimate: it is the algebra of the statistic. The partial
#: correlation is (r_ab - r_am*r_mb) / sqrt((1-r_am^2)(1-r_mb^2)), which tends to
#: r_ab itself as the two legs go to zero, so a triple whose middle is
#: uncorrelated with the ends returns the unconditioned number under a
#: conditional name. Both legs are printed for every triple so the reader can see
#: this rather than take it.
MIN_OVERLAP = 100


@dataclass
class Config:
    commodity: str = "Lentil (Masur)"
    #: Districts per state entering the near arm, taken by coverage. Six gives
    #: sixty ordered triples per state, which is already more triples than there
    #: are independent regions, so the count is presentation not evidence.
    near_districts: int = 6
    #: A region enters at all only with this many dated observations. Not a
    #: power threshold: below it the correlation is not computable at the
    #: overlap the triples need. Set at 150 after checking it does not carry:
    #: at 150, 300 and 500 the far arm is identical to the printed digit on
    #: Lentil (levels 0.323, monthly changes 0.172, because every state clears
    #: the lowest of the three anyway) and the near arm moves only from 0.386 to
    #: 0.435 in levels and 0.312 to 0.320 in changes.
    #: 300 was excluding a whole commodity for nothing.
    #: The clause "with no verdict moving" stood at the end of that sentence
    #: until 2026-09-10 and was false: it had been checked on Lentil only. On
    #: Cowpea the levels cell of B60-3 turns over between 150 and 300. That is
    #: why the check is now a grid this file runs rather than a sentence this
    #: comment makes.
    min_days: int = 150
    monthly: bool = True


def load(commodity: str) -> tuple[list[list[str]], int, int]:
    rows, seen, bad = [], 0, 0
    for f in sorted((DATA / commodity).glob("*.csv")):
        with f.open(encoding="utf-8", errors="replace", newline="") as fh:
            for r in csv.reader(fh):
                seen += 1
                if len(r) >= 10:
                    rows.append(r)
                else:
                    bad += 1
    return rows, seen, bad


def parse_date(s: str):
    try:
        return datetime.datetime.strptime(s.strip(), "%d %b %Y").date()
    except ValueError:
        return None


def series(rows, key) -> tuple[dict, int]:
    """Log of the median modal price across the unit's markets, per date."""
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    dropped = 0
    for r in rows:
        d = parse_date(r[9])
        try:
            p = float(r[8])
        except ValueError:
            p = None
        if d is None or not p or p <= 0:
            dropped += 1
            continue
        acc[key(r)][d].append(p)
    out = {k: {t: math.log(statistics.median(v)) for t, v in dv.items()}
           for k, dv in acc.items()}
    return out, dropped


def to_monthly(s: dict) -> dict:
    """Month-end level, then the change from the previous month it follows.

    Keyed by the later month, so a gap does not silently become a longer change
    presented as a one-month one: a month whose predecessor is absent is dropped.
    """
    by_month = collections.defaultdict(list)
    for t, v in s.items():
        by_month[(t.year, t.month)].append(v)
    lvl = {k: statistics.median(v) for k, v in by_month.items()}
    out = {}
    for (y, m) in lvl:
        py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
        if (py, pm) in lvl:
            out[datetime.date(y, m, 1)] = lvl[(y, m)] - lvl[(py, pm)]
    return out


def back(t: datetime.date, k: int, unit: str) -> datetime.date:
    if unit == "months":
        y, m = t.year, t.month - k
        while m <= 0:
            m += 12
            y -= 1
        return datetime.date(y, m, 1)
    return t - datetime.timedelta(days=k)


def rho(sa: dict, sm: dict, sb: dict, keys):
    """(overlap, r_ab, r_am, r_mb, partial) on exactly these keys, or None."""
    a = np.array([sa[t] for t in keys])
    m = np.array([sm[t] for t in keys])
    b = np.array([sb[t] for t in keys])
    if min(a.std(), m.std(), b.std()) <= 0:
        return None
    c = np.corrcoef(np.vstack([a, m, b]))
    r_ab, r_am, r_mb = float(c[0, 2]), float(c[0, 1]), float(c[1, 2])
    den = math.sqrt(max(1e-12, (1 - r_am ** 2) * (1 - r_mb ** 2)))
    return len(keys), r_ab, r_am, r_mb, (r_ab - r_am * r_mb) / den


def partial(sa: dict, sm: dict, sb: dict, shift: int = 0, unit: str = "days",
            min_overlap: int = MIN_OVERLAP):
    """(overlap, r_ab, r_am, r_mb, partial) or None when the overlap is too thin."""
    if shift:
        sb = {back(t, shift, unit): v for t, v in sb.items()}
    keys = sorted(set(sa) & set(sm) & set(sb))
    if len(keys) < min_overlap:
        return None
    return rho(sa, sm, sb, keys)


def arm(triples, src, label, shifts, unit, min_overlap: int = MIN_OVERLAP):
    """Every triple's five numbers, plus its own shifted placebos.

    Two floors are built, and the second is the one the criteria read. A shifted
    series does not cover the same dates as the unshifted one, so the placebo and
    the fit it is a floor for are computed on different rows, and two standard
    errors on different row sets are not on one scale even though subtracting
    them still returns a tidy number. That is the seventeenth category error, and
    the fix it names is to run each placebo against the fit restricted to the
    rows that placebo can reach. Both are written to the record: the unmatched
    one because it is the number this file returned before 2026-09-10, and a code
    fix keeps the figure it corrects.
    """
    read, floor, m_read, m_floor = [], [], [], []
    for a, m, b in triples:
        sa, sm, sb = src[a], src[m], src[b]
        base = set(sa) & set(sm) & set(sb)
        got = partial(sa, sm, sb, min_overlap=min_overlap)
        if got is None:
            continue
        n, r_ab, r_am, r_mb, pr = got
        read.append({"a": str(a), "m": str(m), "b": str(b), "overlap": n,
                     "r_ab": r_ab, "r_am": r_am, "r_mb": r_mb, "partial": pr,
                     "weaker_leg": min(abs(r_am), abs(r_mb)),
                     "removed": (1 - pr / r_ab) if abs(r_ab) > 1e-9 else None})
        for k in shifts:
            sh = {back(t, k, unit): v for t, v in sb.items()}
            ks = set(sa) & set(sm) & set(sh)
            if len(ks) < min_overlap:
                continue
            g = rho(sa, sm, sh, sorted(ks))
            if g is None:
                continue
            floor.append(abs(g[4]))
            both = sorted(ks & base)
            if len(both) < min_overlap:
                continue
            w = rho(sa, sm, sb, both)
            u = rho(sa, sm, sh, both)
            if w is not None and u is not None:
                m_read.append(abs(w[4]))
                m_floor.append(abs(u[4]))
    return {"arm": label, "readings": read, "placebo_abs": sorted(floor),
            "matched_partial_abs": sorted(m_read),
            "matched_placebo_abs": sorted(m_floor)}


def quantiles(xs):
    if not xs:
        return None
    xs = sorted(xs)
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"n": len(xs), "min": xs[0], "p25": q(.25), "median": q(.5),
            "p75": q(.75), "p90": q(.90), "max": xs[-1]}


def autocorr_table(src, lags=(1, 5, 20, 60, 180)):
    out = {}
    for k, s in src.items():
        ks = sorted(s)
        row = {}
        for lag in lags:
            pa, pb = [], []
            for t in ks:
                u = t + datetime.timedelta(days=lag)
                if u in s:
                    pa.append(s[t]); pb.append(s[u])
            if len(pa) > 30:
                row[str(lag)] = float(np.corrcoef(pa, pb)[0, 1])
        out[str(k)] = row
    return out


def build(cfg: Config):
    """Filtered series for this run, and the unfiltered ones the knob grid needs.

    The CSVs are parsed once. The grid re-filters these dicts rather than
    re-reading the files, which is what makes nine extra passes cost seconds.
    """
    rows, seen, malformed = load(cfg.commodity)
    st_all, dropped = series(rows, lambda r: r[0])
    dt_all, _ = series(rows, lambda r: (r[0], r[1]))
    st_src = {k: v for k, v in st_all.items() if len(v) >= cfg.min_days}
    dt_src = {k: v for k, v in dt_all.items() if len(v) >= cfg.min_days}
    return rows, seen, malformed, dropped, st_src, dt_src, st_all, dt_all


def triples_far(states):
    out = []
    ss = sorted(states)
    for i, a in enumerate(ss):
        for b in ss[i + 1:]:
            for m in ss:
                if m not in (a, b):
                    out.append((a, m, b))
    return out


def triples_near(districts, per_state):
    by_state = collections.defaultdict(list)
    for k in districts:
        by_state[k[0]].append(k)
    out = []
    for s, ks in by_state.items():
        ks.sort(key=lambda k: -len(districts[k]))
        ks = ks[:per_state]
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                for m in ks:
                    if m not in (a, b):
                        out.append((a, m, b))
    return out


#: The two declared knobs, at the values the min_days note above already names.
#: A cell whose sign flips across this grid is not a reading: it is a number one
#: grid point happened to return, which is the shape rule 11 bans. The grid costs
#: nine passes of the arms, about half a minute on the thickest commodity, and it
#: is run every time rather than kept as a note, because a sensitivity that lives
#: in a comment is one nobody re-runs.
STABILITY_GRID = {"min_days": (150, 300, 500), "near_districts": (4, 6, 8)}


def cells_at(st_all, dt_all, min_days: int, near_districts: int):
    """The four near/far ratios at one grid point."""
    st = {k: v for k, v in st_all.items() if len(v) >= min_days}
    dt = {k: v for k, v in dt_all.items() if len(v) >= min_days}
    far, near = triples_far(st), triples_near(dt, near_districts)
    out = {}
    for name, s_src, d_src in (
            ("levels", st, dt),
            ("monthly_changes", {k: to_monthly(v) for k, v in st.items()},
                                {k: to_monthly(v) for k, v in dt.items()})):
        ov = 24 if name == "monthly_changes" else MIN_OVERLAP
        shifts, unit = ((SHIFTS_MONTHS, "months") if name == "monthly_changes"
                        else (SHIFTS_DAYS, "days"))
        got = {}
        for lab, tri, src in (("far", far, s_src), ("near", near, d_src)):
            r = arm(tri, src, lab, shifts, unit, min_overlap=ov)
            r["summary_matched_abs_partial"] = quantiles(r["matched_partial_abs"])
            r["summary_matched_floor_abs"] = quantiles(r["matched_placebo_abs"])
            got[lab] = ratio(r)
        out[name] = got
    return out


def stability(st_all, dt_all):
    """Per reading, is near-above-far unanimous across the declared knob grid?"""
    signs, points = collections.defaultdict(list), []
    for md in STABILITY_GRID["min_days"]:
        for nd in STABILITY_GRID["near_districts"]:
            for name, g in cells_at(st_all, dt_all, md, nd).items():
                n, f = g["near"], g["far"]
                s = None if (n is None or f is None) else bool(n > f)
                signs[name].append(s)
                points.append({"min_days": md, "near_districts": nd,
                               "reading": name, "near": n, "far": f,
                               "near_above_far": s})
    out = {}
    for name, ss in signs.items():
        read = [s for s in ss if s is not None]
        out[name] = {"points": len(ss), "readable": len(read),
                     "yes": sum(1 for s in read if s),
                     # None, not False: a grid that returns nothing readable has
                     # not shown a flip, it has shown nothing. Either way the
                     # cell is not read, and the two reasons print differently.
                     "unanimous": (all(read) or not any(read)) if read else None}
    return out, points


def ratio(arm_result, matched: bool = True):
    """How far the arm's typical reading sits above its own measured floor.

    The line is the floor and nothing else. No number is chosen here: the
    denominator is what this same statistic returns on the same series with the
    real alignment destroyed, which is what discipline 24 asks for and what a
    declared threshold would have replaced with a guess.
    """
    got = arm_result[("summary_matched_abs_partial" if matched
                      else "summary_abs_partial")]
    flo = arm_result[("summary_matched_floor_abs" if matched
                      else "summary_floor_abs")]
    if not got or not flo or flo["median"] <= 0:
        return None
    return got["median"] / flo["median"]


def criteria(out, st_src, dt_src, far, near, stab=None):
    """Five criteria. The three-state map is written per cell, per rule 11c.

    The middle cell of a three-state criterion maps to no verdict at all. A
    reading that sits at its floor and a reading that is not adjudicable are two
    different objects, and collapsing them is the error that rule 11c exists to
    stop: the code has to carry the distinction the design sheet wrote down.
    """
    cells = {}
    for reading, arms in out.items():
        for side in ("far", "near"):
            cells[(reading, side)] = ratio(arms[side])

    near_cells = {k: v for k, v in cells.items() if k[1] == "near" and v is not None}
    far_cells = {k: v for k, v in cells.items() if k[1] == "far" and v is not None}

    # B60-1. The positive control. Without it nothing else in this file means
    # anything, because a statistic that returns its floor everywhere returns its
    # floor here too and that is not a finding about anchors.
    # Three states here too. An arm with no measured floor is not an arm that
    # failed: it is an arm with nothing to read against, and rule 11c says the
    # undetermined cell may not be mapped onto either verdict.
    if not near_cells:
        near_ok = None
    elif all(v > 1.0 for v in near_cells.values()):
        near_ok = True
    elif all(v <= 1.0 for v in near_cells.values()):
        near_ok = False
    else:
        near_ok = None
    c1 = {"name": "B60-1  the near arm clears its own measured floor",
          "kind": "instrument", "passed": near_ok,
          "detail": (("the within-state arm sits at "
                      + ", ".join(f"{k[0]} {v:.2f}x" for k, v in sorted(near_cells.items()))
                      + " of its own shifted-placebo floor")
                     if near_cells else
                     "no near cell has a measured floor, so the instrument is not "
                     "shown to return a non-zero on this carrier and nothing else "
                     "here is adjudicable")}

    # B60-2. The strong form as registered: conditional on the middle, two
    # distant regions are close to independent. Three states, and the middle one
    # is mapped to no verdict.
    below = {k: v for k, v in far_cells.items() if v <= 1.0}
    above = {k: v for k, v in far_cells.items() if v > 1.0}
    if not far_cells:
        strong, cell = None, "no far reading"
    elif not above:
        strong, cell = True, "every far cell at or below its floor"
    elif not below:
        strong, cell = False, "every far cell above its floor"
    else:
        strong, cell = None, "far cells split"
    # Corrected 2026-09-09, and the correction is a reading of the registration
    # rather than of the data. The registered sentence is conditional: a distant
    # node grows its own fixed point "if no broadcast tops it up", written into
    # the registration on 2026-08-31 before any of this data was touched. The
    # first version of this criterion dropped that antecedent and scored an
    # unconditional claim nobody had made. On this carrier the antecedent is
    # false on two counts, both facts about the world: the dataset is itself a
    # national daily publication of every market's price, and lentil is one of
    # the five pulses whose support price the central government announces at the
    # start of the sowing season on its costs commission's recommendation. So the
    # far end is topped up by broadcast here, and the conditional-independence
    # prediction is not in play. This is now a premise criterion, and discipline
    # 11d says a premise that does not hold leaves the readings that depend on it
    # with nothing to judge rather than judging against them.
    c2 = {"name": "B60-2  premise: no broadcast reaches the far end of this carrier",
          "kind": "premise", "passed": False,
          "premise_source": ("Agmarknet publishes every market's daily price "
                             "nationally, and it is the source of this data; and "
                             "lentil is among the five pulses under a centrally "
                             "announced support price, set before the sowing "
                             "season on the costs commission's recommendation."),
          "withdrawn_form": {"was": "strong form: the far arm sits at its floor",
                             "why": ("scored the registration with its antecedent "
                                     "removed"),
                             "reading_kept": strong, "cell": cell},
          "detail": ("the premise does not hold on this carrier, so the "
                     "registered conditional-independence prediction has no "
                     "object here and the far arm's level is reported rather than "
                     "scored. Far cells at "
                     + ", ".join(f"{k[0]} {v:.2f}x" for k, v in sorted(far_cells.items()))
                     + f" of their own floors ({cell}), which on a carrier with "
                       "broadcast is the branch the registration names rather than "
                       "a reading against it")}

    # B60-3. The graded form. Regeneration is decay, so what it predicts before
    # it predicts independence is that the residual falls with distance.
    have = [(r, near_cells[(r, "near")], far_cells[(r, "far")])
            for r in out if (r, "near") in near_cells and (r, "far") in far_cells]
    # A cell whose sign flips across the two declared knobs is not read at all.
    # It is not a failure either: it is the undetermined cell, and rule 11c says
    # the undetermined cell may not be mapped onto a verdict in either direction.
    # Without this gate Cowpea's levels cell returned near 1.766 against far
    # 1.755 at the default grid point and was scored a pass on a margin of six
    # parts in a thousand, while five of the nine grid points put it the other
    # way round. That is a verdict bought by a knob, and it was bought in this
    # framework's favour, which is the direction the record is least likely to
    # question on its own.
    dropped = [] if stab is None else [p for p in have
                                       if stab.get(p[0], {}).get("unanimous") is not True]
    pairs = [p for p in have if p not in dropped]
    graded = [p for p in pairs if p[1] > p[2]]
    # No pair is not a failed comparison. An empty comparison mapped onto a
    # verdict is the same error as the undetermined cell mapped onto one.
    if not pairs:
        graded_ok = None
    elif len(graded) == len(pairs):
        graded_ok = True
    elif not graded:
        graded_ok = False
    else:
        graded_ok = None
    c3 = {"name": "B60-3  graded form: the residual is smaller between distant regions",
          "kind": "own_reading",
          "passed": graded_ok,
          "detail": ((f"{len(graded)} of {len(pairs)} readings have near above far, "
                      + "; ".join(f"{r}: near {n:.2f}x far {f:.2f}x" for r, n, f in pairs)
                      + ("" if not dropped else
                         ". Not read, because the sign flips across the declared "
                         "knob grid and a cell a knob can turn over is not a "
                         "reading: "
                         + "; ".join(
                             f"{r} (near {n:.2f}x far {f:.2f}x at the default point, "
                             f"{stab[r]['yes']} of {stab[r]['readable']} grid points "
                             f"put near above far)" for r, n, f in dropped)))
                     if pairs else
                     ("no reading has both a near and a far cell with a measured "
                      "floor, so there is nothing to compare"
                      if not have else
                      "every reading with both cells has a sign that flips across "
                      "the declared knob grid, so none of them is read"))}

    # B60-4. The rival's own prediction on this carrier, kept apart from ours.
    # Polarity, and it is this repository's convention rather than a choice: a
    # rival criterion passes when the rival's prediction fails. B52-3 is the
    # worked example, passing on zero hits in 1069 readable cells. Writing it the
    # other way round makes every later count of rival outcomes read backwards,
    # which is the whole reason discipline 11d asks for the kind at all. Three
    # states, and a split maps to no verdict.
    if not far_cells:
        rival_ok, rival_cell = None, "no far reading"
    elif not below:
        rival_ok, rival_cell = False, "the rival's prediction holds in every far cell"
    elif not above:
        rival_ok, rival_cell = True, "the rival's prediction fails in every far cell"
    else:
        rival_ok, rival_cell = None, "far cells split, so neither side is read"
    # Withdrawn 2026-09-09. The account this criterion scored was spatial
    # arbitrage holding two markets together directly. That is not the rival.
    # Arbitrage is the projection operator of this framework's own two-operator
    # table, which records that it only removes and never creates a value, so it
    # cannot be the account that supplies a level; and the rival-identification
    # step of the four-cell rule says in as many words that the arbitrage-capacity
    # family is a secondary dispute conducted after this framework's claim is
    # granted, not an opponent. Scoring it produced a loss in the only losing cell
    # against an opponent that does not exist. The registration's own opponent is
    # a field served by one anchor, and it makes no point prediction on this
    # statistic, so this station has no rival criterion. Kept rather than deleted,
    # with its reading, because a withdrawn criterion is a measurement of how the
    # opponent was misidentified.
    c4 = {"name": "B60-4  WITHDRAWN: scored an account that is not the rival",
          "kind": "bookkeeping",
          # No grid. A withdrawn criterion that is no longer typed as a rival's
          # prediction places nothing on the four-cell table, and the two
          # sentences below used to sit in `grid_split`, where a key is what a
          # reader counts as that cell being occupied. The C key in particular
          # is the only thing on this ledger that could make the one losing cell
          # read as filled. They are kept, as prose, where nothing counts them.
          "grid_note": {"B": "cells where the far arm falls to its floor, so the "
                             "framework reads the zero it registered and the rival does not",
                        "C": "cells where the far arm stays above its floor, so the "
                             "rival's prediction holds and the framework's does not",
                        "why": "both sentences are what this criterion would have "
                               "said while it was typed as a rival's prediction; "
                               "it was withdrawn, so neither cell is claimed"},
          "rival_premise": ("Spatial arbitrage in a connected trading network: two "
                            "markets trading one good are held together by traders "
                            "moving the good between them directly, so their prices "
                            "differ by transport cost alone."),
          "rival_entailment": ("A direct bilateral link is not routed through any "
                               "third market, so conditioning on a third market does "
                               "not remove it and the partial correlation of two "
                               "distant markets stays above what the same statistic "
                               "returns on shifted series."),
          "passed": None,
          "withdrawn": ("spatial arbitrage is this framework's own projection "
                        "operator, not an opposing account of where a level comes "
                        "from"),
          "detail": (f"withdrawn. Reading kept: {rival_cell}. {len(above)} of {len(far_cells)} far cells stay above the floor "
                     f"({', '.join(f'{k[0]} {v:.2f}x' for k, v in sorted(above.items()))}"
                     + (f"; below: {', '.join(f'{k[0]} {v:.2f}x' for k, v in sorted(below.items()))}"
                        if below else "") + ")")}

    # B60-5. What the triple count is not. Bookkeeping, and it is the number a
    # later reader would otherwise take from len(readings).
    detail = {"states_behind_far_triples": len(st_src),
              "districts_behind_near_triples": len(dt_src),
              "far_triples": len(far), "near_triples": len(near)}
    c5 = {"name": "B60-5  the triple count is reported as presentation, not as evidence",
          "kind": "bookkeeping", "passed": True,
          "detail": (f"{len(far)} far triples come from {len(st_src)} states and "
                     f"{len(near)} near triples from {len(dt_src)} districts. "
                     f"Triples sharing a series are not independent, so no count "
                     f"in this record is an independent-observation count")}
    # The design sheet's first cell, implemented rather than only written: if the
    # near arm does not clear its floor, the instrument is not shown to see a
    # non-zero, and a far arm sitting at its floor is then exactly what a dead
    # instrument returns. Every reading downstream of the control inherits its
    # state. Only the bookkeeping criterion is independent of it.
    if c1["passed"] is not True:
        for c in (c3,):
            c["passed"] = None
            c["detail"] = ("not adjudicable: the positive control B60-1 did not "
                           "clear, so this arm's reading cannot be told from what "
                           "a statistic with no resolution returns. Original "
                           "reading kept: " + c["detail"])
    return [c1, c2, c3, c4, c5], detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commodity", default=Config.commodity)
    ap.add_argument("--near-districts", type=int, default=Config.near_districts)
    ap.add_argument("--min-days", type=int, default=Config.min_days)
    a = ap.parse_args()
    cfg = Config(commodity=a.commodity, near_districts=a.near_districts,
                 min_days=a.min_days)

    rows, seen, malformed, dropped, st_src, dt_src, st_all, dt_all = build(cfg)
    print(f"B60: {cfg.commodity}")
    print(f"  {seen:,} lines, {malformed} malformed, {dropped} unreadable date or price")
    print(f"  {len(st_src)} states and {len(dt_src)} districts clear "
          f"{cfg.min_days} dated observations")

    far = triples_far(st_src)
    near = triples_near(dt_src, cfg.near_districts)
    print(f"  {len(far)} far triples, {len(near)} near triples\n")

    record = {"stage": "B60",
              "config": {"commodity": cfg.commodity,
                         "near_districts": cfg.near_districts,
                         "min_days": cfg.min_days,
                         "shifts_days": list(SHIFTS_DAYS),
                         "shifts_months": list(SHIFTS_MONTHS),
                         "min_overlap": MIN_OVERLAP,
                         "floor_rows": "matched"},
              "input": {"lines": seen, "malformed": malformed,
                        "unreadable_date_or_price": dropped,
                        "states_kept": sorted(st_src),
                        "districts_kept": len(dt_src)},
              "autocorrelation_levels": autocorr_table(st_src)}

    out = {}
    for name, src in (("levels", (st_src, dt_src)),
                      ("monthly_changes", ({k: to_monthly(v) for k, v in st_src.items()},
                                           {k: to_monthly(v) for k, v in dt_src.items()}))):
        s_src, d_src = src
        # A monthly change series has about a hundredth the points of a daily
        # level one, so the overlap a triple must clear is set per reading.
        ov = 24 if name == "monthly_changes" else MIN_OVERLAP
        shifts, unit = ((SHIFTS_MONTHS, "months") if name == "monthly_changes"
                        else (SHIFTS_DAYS, "days"))
        far_r = arm(far, s_src, "far", shifts, unit, min_overlap=ov)
        near_r = arm(near, d_src, "near", shifts, unit, min_overlap=ov)
        out[name] = {"far": far_r, "near": near_r}
        for r in (far_r, near_r):
            got = quantiles([abs(x["partial"]) for x in r["readings"]])
            flo = quantiles(r["placebo_abs"])
            r["summary_abs_partial"] = got
            r["summary_floor_abs"] = flo
            r["summary_matched_abs_partial"] = quantiles(r["matched_partial_abs"])
            r["summary_matched_floor_abs"] = quantiles(r["matched_placebo_abs"])
            r["ratio"] = ratio(r)
            r["ratio_unmatched"] = ratio(r, matched=False)
            pad = " " * (len(name) + len(r["arm"]) + 5)
            if got:
                print(f"  [{name}/{r['arm']}] {got['n']} triples, |partial| median "
                      f"{got['median']:.3f} p90 {got['p90']:.3f} max {got['max']:.3f}")
            else:
                print(f"  [{name}/{r['arm']}] no triple cleared the overlap")
            if r["ratio"] is not None:
                mp = r["summary_matched_floor_abs"]
                print(f"  {pad} {r['ratio']:.3f}x its own floor, from {mp['n']} "
                      f"placebo-and-fit pairs on matching rows")
            if r["ratio_unmatched"] is not None:
                print(f"  {pad} ({r['ratio_unmatched']:.3f}x with each placebo "
                      f"read against the full-window fit rather than its own rows)")
            if flo:
                print(f"  {pad} floor from {flo['n']} shifted placebos, median "
                      f"{flo['median']:.3f} p90 {flo['p90']:.3f} max {flo['max']:.3f}")
            else:
                # No floor is not a floor of zero. An arm with nothing to compare
                # against is not adjudicable, and the criteria below read it that
                # way rather than as a reading that cleared or failed.
                print(f"  {pad} no shifted placebo cleared the overlap, so this arm "
                      f"has no measured floor and is not adjudicable")
        print()
    record["readings"] = out
    stab, grid = stability(st_all, dt_all)
    record["knob_grid"] = {"grid": {k: list(v) for k, v in STABILITY_GRID.items()},
                           "per_reading": stab, "points": grid}
    for name, s in sorted(stab.items()):
        flag = {True: "unanimous",
                False: "FLIPS, so this cell is not read",
                None: "no readable grid point, so this cell is not read"}[s["unanimous"]]
        print(f"  [knobs/{name}] near above far at {s['yes']} of {s['readable']} "
              f"readable grid points ({s['points']} tried): {flag}")
    print()
    crits, detail = criteria(out, st_src, dt_src, far, near, stab)
    record["criteria"] = crits
    record["independent_units"] = detail
    for c in crits:
        mark = {True: "PASS", False: "FAIL", None: "----"}[c["passed"]]
        print(f"  [{mark}] {c['name']}\n         {c['detail']}")
    n_pass = sum(1 for c in crits if c["passed"] is True)
    n_open = sum(1 for c in crits if c["passed"] is None)
    print(f"\n  {n_pass}/{len(crits)} passed, {n_open} not adjudicated\n")

    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f"b60_anchor_regeneration_{cfg.commodity.split(' ')[0].lower()}.json"
    p.write_text(json.dumps(record, indent=2, default=str) + "\n",
                 encoding="utf-8", newline="\n")
    print(f"  wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
