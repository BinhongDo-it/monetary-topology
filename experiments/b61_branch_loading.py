"""B61: does a market's deviation load on its branch or on its own conditions?

B30-5 as registered asks for regional deviation regressed on **the propagation
branch** and on **the region's own conditions**. The cross-sectional run of
2026-09-01 put only the second regressor in: log city income. The branch side has
never entered a regression. Rule 34 says the coarse version passing does not make
the fine version pass, so that limb is still open, and it is the limb the source
text is about: the difference should "correlate with the intermediary's own
deviation and not with the region's own conditions".

The prereg blocked the branch limb on timing, because a cross-section cannot tell
"inherited down a tree" from "a common cause reaching both regions". That whole
family of instruments shares one assumption: to separate inheritance from a common
cause you have to see who moved first. The instrument here does not use it. It
asks what the deviation correlates with, which needs an intermediary's identity
and not a clock.

Carrier: Agmarknet mandi day prices, three pulses, 2008-2017. The intermediary is
the market's own state, read leave-one-out so a market is never its own branch.
The region's own conditions are that market's own arrivals on that day.

Two constructions matter and both are in the criteria rather than only here.

* ``dev`` and ``dev_state`` share the term ``-nat(t)``, so they correlate through
  ``var(nat)`` even when the underlying series are independent. A day fixed effect
  absorbs it exactly, since ``nat(t)`` is constant across markets within a day.
  B61-2 prints the three correlations so the step is visible in the record.
* A state's price level relative to the country is persistent, so a shifted
  placebo on levels keeps most of the real loading. The monthly-change arm removes
  the persistent term by differencing, and its placebo falls to zero. Both arms
  are reported with their own floors; neither is picked over the other.

No threshold is registered on any coefficient. Each arm is read against a floor
that is measured on the same data by shifting the intermediary series, and the
comparison is "above its own floor" rather than a line on an estimate.

Usage::

    python experiments/b61_branch_loading.py
    python experiments/b61_branch_loading.py --commodity "White Peas"

Writes ``results/b61_branch_loading_<commodity>.json``.
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
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
RESULTS = ROOT / "results"

#: Whole and half-year shifts of the intermediary series. A shift shorter than a
#: season would keep part of the real alignment and put signal into the floor.
SHIFTS_DAYS = (180, 365, 730)

#: A market is only read where its state actually has an intermediary to read:
#: the market itself plus at least two other markets reporting that day, so the
#: leave-one-out median is taken over two or more series.
MIN_STATE_MARKETS = 3

#: A monthly change pairs a quote with the nearest earlier quote from the same
#: market inside this window. It is a window rather than a lag because mandi
#: reporting is irregular.
MONTH_LO, MONTH_HI = 25, 35

#: Floats are written at fixed precision. The last bits of a least-squares
#: solution belong to the BLAS build, and a derived file that differs on them
#: manufactures a diff that buries real ones.
ND = 6


def rd(x):
    """Round for the record, and keep None as None."""
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [rd(v) for v in x]
    if isinstance(x, dict):
        return {k: rd(v) for k, v in x.items()}
    if isinstance(x, float):
        return None if math.isnan(x) else round(x, ND)
    return x


#: The second fetch of the same portal returns one state-month per file, with the
#: state in the path and the market one level out from the ``columns`` key. It
#: carries no district, and this design does not use one: the intermediary is the
#: state. Reading it costs a second parser and buys a different commodity over a
#: partly different set of states, which is what a replication of this reading
#: needs after the leave-one-out showed the main carrier resting on two.
API_STATE_NAMES = {"7": "Chattisgarh", "12": "Haryana", "16": "Karnataka",
                   "19": "Madhya Pradesh", "20": "Maharashtra", "26": "Odisha",
                   "34": "Uttar Pradesh", "35": "Uttarakhand", "36": "West Bengal"}


@dataclass
class Config:
    commodity: str = "Lentil (Masur)"
    variety: str = "Other"
    source: str = "csv"
    min_state_markets: int = MIN_STATE_MARKETS
    month_lo: int = MONTH_LO
    month_hi: int = MONTH_HI
    shifts_days: tuple = SHIFTS_DAYS
    cluster: str = "state"


def read_rows_api(cfg):
    """The state-month JSON fetch. A row is (state, district, market, arrivals, modal, date).

    District is empty: this fetch does not carry one, and the branch here is the
    state. The market sits at ``markets[i].marketName``, one level out from the
    ``columns`` key, which describes only the innermost ``data`` array.
    """
    base = DATA / "api" / cfg.commodity
    rows, seen, malformed, unreadable, wrong_variety = [], 0, 0, 0, 0
    varieties = collections.Counter()
    for sd in sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []:
        state = API_STATE_NAMES.get(sd.name, sd.name)
        for f in sorted(sd.glob("*.json")):
            try:
                o = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                malformed += 1
                continue
            for m in o.get("markets") or []:
                market = m.get("marketName") or ""
                for day in m.get("dates") or []:
                    try:
                        d = datetime.datetime.strptime(str(day.get("arrivalDate")), "%d/%m/%Y").date()
                    except Exception:
                        unreadable += 1
                        continue
                    for r in day.get("data") or []:
                        seen += 1
                        varieties[r.get("variety")] += 1
                        if r.get("variety") != cfg.variety:
                            wrong_variety += 1
                            continue
                        try:
                            modal = float(r.get("modalPrice"))
                            arrivals = float(r.get("arrivals"))
                        except Exception:
                            unreadable += 1
                            continue
                        if modal <= 0 or arrivals <= 0:
                            unreadable += 1
                            continue
                        rows.append((state, "", market, arrivals, modal, d))
    return rows, {"lines": seen, "malformed": malformed,
                  "unreadable_or_nonpositive": unreadable,
                  "other_variety": wrong_variety,
                  "varieties_present": dict(varieties.most_common())}


def read_rows(cfg):
    """Return (rows, counters). A row is (state, district, market, arrivals, modal, date)."""
    if cfg.source == "api":
        return read_rows_api(cfg)
    rows, seen, malformed, unreadable, wrong_variety = [], 0, 0, 0, 0
    varieties = collections.Counter()
    for f in sorted((DATA / cfg.commodity).glob("*.csv")):
        for r in csv.reader(f.open(encoding="utf-8", errors="replace")):
            seen += 1
            if len(r) < 10:
                malformed += 1
                continue
            varieties[r[3].strip()] += 1
            if r[3].strip() != cfg.variety:
                wrong_variety += 1
                continue
            try:
                modal = float(r[8])
                arrivals = float(r[5])
                d = datetime.datetime.strptime(r[9].strip(), "%d %b %Y").date()
            except Exception:
                unreadable += 1
                continue
            if modal <= 0 or arrivals <= 0:
                unreadable += 1
                continue
            rows.append((r[0].strip(), r[1].strip(), r[2].strip(), arrivals, modal, d))
    return rows, {"lines": seen, "malformed": malformed,
                  "unreadable_or_nonpositive": unreadable,
                  "other_variety": wrong_variety,
                  "varieties_present": dict(varieties.most_common())}


def build(rows, cfg):
    """Deviation, leave-one-out branch deviation, and own conditions, per row kept."""
    byday = collections.defaultdict(list)
    for s, dis, m, arr, modal, d in rows:
        byday[d].append((s, m, arr, modal))

    recs, dropped_no_peers = [], 0
    for d, lst in byday.items():
        logs = [math.log(x[3]) for x in lst]
        nat = statistics.median(logs)
        bystate = collections.defaultdict(list)
        for (s, m, arr, _), lg in zip(lst, logs):
            bystate[s].append((m, lg, arr))
        for s, items in bystate.items():
            if len(items) < cfg.min_state_markets:
                dropped_no_peers += len(items)
                continue
            for i, (m, lg, arr) in enumerate(items):
                peers = [items[j][1] for j in range(len(items)) if j != i]
                recs.append((s, m, d, lg - nat, statistics.median(peers) - nat,
                             math.log(arr)))
    return recs, dropped_no_peers


def demean(a, g):
    out = np.empty_like(a)
    idx = collections.defaultdict(list)
    for i, x in enumerate(g):
        idx[x].append(i)
    for _, ii in idx.items():
        ii = np.array(ii)
        out[ii] = a[ii] - a[ii].mean()
    return out


def ols(y, xs, groups):
    """Least squares with a cluster-robust covariance, plus the iid one for scale."""
    A = np.column_stack([np.ones(len(y))] + list(xs))
    # Two fixed effects sweep a thin carrier flat: on a stratum where most markets
    # quote once, double-demeaning leaves a regressor identically zero and the
    # normal matrix is singular. A fit that cannot be formed is not a fit that
    # failed, so this returns nothing and the caller treats that shift as unbuilt.
    if np.linalg.matrix_rank(A) < A.shape[1]:
        return None
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    n, k = A.shape
    XtXi = np.linalg.inv(A.T @ A)
    se_iid = np.sqrt((r @ r / (n - k)) * np.diag(XtXi))
    idx = collections.defaultdict(list)
    for i, x in enumerate(groups):
        idx[x].append(i)
    meat = np.zeros((k, k))
    for _, ii in idx.items():
        ii = np.array(ii)
        u = (A[ii] * r[ii, None]).sum(axis=0)
        meat += np.outer(u, u)
    G = len(idx)
    c = G / (G - 1) * (n - 1) / (n - k) if G > 1 else 1.0
    se_cl = np.sqrt(np.diag(c * XtXi @ meat @ XtXi))
    ss = (y - y.mean()) @ (y - y.mean())
    # A cluster-robust meat matrix is a sum of G outer products, so its rank is at
    # most G. With fewer clusters than parameters the sandwich is singular and its
    # standard errors mean nothing. This is arithmetic, not a threshold: the check
    # is G >= k, where k is however many coefficients this fit has.
    return {"n": n, "clusters": G, "k": k, "cluster_rank_ok": bool(G >= k),
            "b_state": b[1], "b_arr": b[2],
            "se_state": se_cl[1], "se_arr": se_cl[2],
            "se_state_iid": se_iid[1], "se_arr_iid": se_iid[2],
            "r2": (1 - (r @ r) / ss) if ss > 0 else None}


def month_pairs(recs, cfg):
    """Index pairs (later, earlier) from one market, month_lo..month_hi days apart."""
    ords_ = [r[2].toordinal() for r in recs]
    bym = collections.defaultdict(list)
    for i, r in enumerate(recs):
        bym[(r[0], r[1])].append((ords_[i], i))
    pairs = []
    for _, lst in bym.items():
        lst.sort()
        ds = np.array([x[0] for x in lst])
        ii = [x[1] for x in lst]
        for p in range(len(lst)):
            cand = np.where((ds >= ds[p] - cfg.month_hi) & (ds <= ds[p] - cfg.month_lo))[0]
            if len(cand):
                pairs.append((ii[p], ii[cand[-1]]))
    return pairs


def arms(recs, cfg):
    """Both readings. Each shift is its own paired comparison on its own sample.

    A placebo is only a floor if it is computed on the same rows as the real fit
    it is compared with. The first implementation ran the real fit on every row
    and each placebo on whatever rows that shift happened to reach, which on a
    thin commodity meant a different number of clusters as well, so the two
    standard errors were not on the same scale and subtracting them was category
    error six. The second implementation took the intersection of all three
    shifts, which fixed the scale and then threw away most of the sample and five
    of eight clusters to do it: it tied the 180-day comparison to the 730-day
    one for no reason.

    What is done instead: for each shift, take the rows that shift can reach, and
    fit **both** the real branch series and the shifted one on exactly those rows.
    Every comparison is then within one sample with one cluster count, and no
    comparison is charged for another shift's coverage. The full-sample fit is
    reported beside them and no criterion reads it.
    """
    dev = np.array([r[3] for r in recs])
    dvs = np.array([r[4] for r in recs])
    loc = np.array([r[5] for r in recs])
    ords_ = np.array([r[2].toordinal() for r in recs])
    st = np.array([r[0] for r in recs])
    mk = np.array([r[0] + "|" + r[1] for r in recs])
    tbl = {(recs[i][0], ords_[i]): dvs[i] for i in range(len(recs))}
    out = {}

    # ---- levels: day and market fixed effects. The day effect removes the
    # shared -nat(t); the market effect removes each market's persistent level.
    def fit_levels(mask, x_branch):
        return ols(demean(demean(dev[mask], ords_[mask]), mk[mask]),
                   [demean(demean(x_branch[mask], ords_[mask]), mk[mask]),
                    demean(demean(loc[mask], ords_[mask]), mk[mask])], st[mask])

    allrows = np.ones(len(recs), dtype=bool)
    lev = {"per_shift": {},
           "real_full_sample": fit_levels(allrows, dvs) if len(recs) >= 20 else None}
    for sh in cfg.shifts_days:
        shifted = np.array([tbl.get((st[i], ords_[i] + sh), np.nan) for i in range(len(recs))])
        m = ~np.isnan(shifted)
        r = pl = None
        if m.sum() >= 20:
            r, pl = fit_levels(m, dvs), fit_levels(m, shifted)
        lev["per_shift"][sh] = (None if r is None or pl is None else
                                {"n": int(m.sum()), "real": r, "placebo": pl})
    out["levels"] = lev

    # ---- monthly changes: differencing removes the persistent term, so only the
    # day effect is needed. This is the arm whose floor falls away.
    pairs = month_pairs(recs, cfg)
    mch = {"pairs": len(pairs), "per_shift": {}, "real_full_sample": None}
    if len(pairs) >= 20:
        p0 = np.array([p[0] for p in pairs])
        p1 = np.array([p[1] for p in pairs])
        dd, da = dev[p0] - dev[p1], loc[p0] - loc[p1]
        dy, sy = ords_[p0], st[p0]
        ds_real = dvs[p0] - dvs[p1]

        def fit_month(mask, x_branch):
            return ols(demean(dd[mask], dy[mask]),
                       [demean(x_branch[mask], dy[mask]), demean(da[mask], dy[mask])],
                       sy[mask])

        mch["real_full_sample"] = fit_month(np.ones(len(pairs), dtype=bool), ds_real)
        for sh in cfg.shifts_days:
            a = np.array([tbl.get((sy[i], dy[i] + sh), np.nan) for i in range(len(dy))])
            b = np.array([tbl.get((sy[i], ords_[p1][i] + sh), np.nan) for i in range(len(dy))])
            m = ~np.isnan(a) & ~np.isnan(b)
            r = pl = None
            if m.sum() >= 20:
                r, pl = fit_month(m, ds_real), fit_month(m, (a - b))
            entry = (None if r is None or pl is None else
                     {"n": int(m.sum()), "real": r, "placebo": pl})
            if entry is not None:
                # Leave one state out. Printing the object rather than a count,
                # per rule 11: a cluster count says six, and the question the
                # count cannot answer is how many of the six carry the reading.
                jack = {}
                for drop in sorted(set(sy[m])):
                    m2 = m & (sy != drop)
                    r2 = pl2 = None
                    if m2.sum() >= 100:
                        r2, pl2 = fit_month(m2, ds_real), fit_month(m2, (a - b))
                    if r2 is None or pl2 is None or not (
                            r2["cluster_rank_ok"] and pl2["cluster_rank_ok"]):
                        jack[drop] = None
                        continue
                    den = math.sqrt(r2["se_state"] ** 2 + pl2["se_state"] ** 2)
                    jack[drop] = {"pairs_dropped": int(m.sum() - m2.sum()),
                                  "n": int(m2.sum()), "clusters": r2["clusters"],
                                  "real": r2["b_state"], "placebo": pl2["b_state"],
                                  "z": (r2["b_state"] - pl2["b_state"]) / den if den > 0 else None}
                entry["leave_one_state_out"] = jack
            mch["per_shift"][sh] = entry
    else:
        for sh in cfg.shifts_days:
            mch["per_shift"][sh] = None
    out["monthly_changes"] = mch

    y0 = demean(demean(dev, ords_), mk)
    x10 = demean(demean(dvs, ords_), mk)
    x20 = demean(demean(loc, ords_), mk)
    out["shared_term_diagnostic"] = {
        "raw": float(np.corrcoef(dev, dvs)[0, 1]),
        "day_fe": float(np.corrcoef(demean(dev, ords_), demean(dvs, ords_))[0, 1]),
        "day_and_market_fe": float(np.corrcoef(y0, x10)[0, 1]),
        "raw_dev_vs_local": float(np.corrcoef(dev, loc)[0, 1]),
        "day_and_market_fe_dev_vs_local": float(np.corrcoef(y0, x20)[0, 1]),
    }
    return out


def shift_gaps(arm, coef, se):
    """Per shift: real minus placebo on the same rows, over the combined error.

    The width is that combined standard error, which is this comparison's own
    measurement error and not a constant chosen here. Rule 11 bans a zero-width
    strict inequality, and the first version of this comparison had one: it fired
    the same day, on a coefficient whose real value and 730-day placebo agree to
    four decimals.
    """
    outs = {}
    for sh, d in arm["per_shift"].items():
        if d is None or not (d["real"]["cluster_rank_ok"] and d["placebo"]["cluster_rank_ok"]):
            outs[sh] = None
            continue
        r, p = d["real"], d["placebo"]
        diff = r[coef] - p[coef]
        den = math.sqrt(r[se] ** 2 + p[se] ** 2)
        outs[sh] = {"n": d["n"], "clusters": r["clusters"],
                    "real": r[coef], "placebo": p[coef],
                    "se_real": r[se], "se_placebo": p[se],
                    "diff": diff, "z": (diff / den if den > 0 else None)}
    return outs


def cell_of(gaps, full=None, coef=None):
    """Four cells. A reading has to clear, or fail to clear, on every shift.

    A shift only reaches the rows where the same state reported that many days
    later, and that subset is not a random draw from the sample: it is the rows
    where the state kept reporting. So a verdict also requires the coefficient on
    the shift's own subsample to sit on the same side of zero as the full-sample
    one. This is a structural consistency check and not a threshold. Where they
    disagree the subsample is not standing in for the sample and there is nothing
    to adjudicate; the coverage per shift is printed by B61-7 either way.
    """
    zs = [g["z"] for g in gaps.values() if g is not None and g["z"] is not None]
    if not zs:
        return "no_floor"
    if full is not None and coef is not None:
        fs = full[coef]
        subs = [g["real"] for g in gaps.values() if g is not None]
        if subs and any((s > 0) != (fs > 0) for s in subs):
            return "indistinguishable"
    if all(z > 1.0 for z in zs):
        return "above"
    if all(z < -1.0 for z in zs):
        return "below"
    return "indistinguishable"


#: Our own existence claim: this coefficient carries a loading. Reading it is
#: three-state per research rule 7.0. Not finding a regularity on one carrier is
#: not evidence against it, so the middle cell maps onto no verdict at all.
OURS_MAP = {"above": "clears its own shifted floor on every shift: read on this carrier",
            "below": "sits below its own floor on every shift by more than the combined "
                     "error: the opposite of what was registered, and that is a verdict",
            "indistinguishable": "within one combined standard error of its own floor on at "
                                 "least one shift: not read on this carrier, and no verdict",
            "no_floor": "no shift produced a readable placebo: no verdict"}
OURS_VERDICT = {"above": True, "below": False,
                "indistinguishable": None, "no_floor": None}

#: The rival's existence claim, and the polarity is inverted per rule 11e first
#: clause b: passed True means the rival was wrong. "Not supported" and "refuted"
#: are two states and rule 31 forbids collapsing them, so only the cell where the
#: rival's regressor falls below its own floor is a refutation.
RIVAL_MAP = {"above": "the rival's regressor clears its own floor on every shift: the "
                      "rival's prediction holds on this carrier",
             "below": "it sits below its own floor on every shift by more than the combined "
                      "error: the rival's prediction is refuted here",
             "indistinguishable": "it is within one combined standard error of its own floor: "
                                  "the rival's prediction is not supported here, and that is "
                                  "not the same state as refuted, so no verdict",
             "no_floor": "no shift produced a readable placebo: no verdict"}
RIVAL_VERDICT = {"above": False, "below": True,
                 "indistinguishable": None, "no_floor": None}


def grid_of(ours_cell, rival_cell):
    """Where this reading sits on the four-cell table, and when it sits nowhere.

    Rule 0b: the two theories are each scored against reality, not against each
    other. Our side predicts a loading on the branch and none on local
    conditions; the rival predicts a loading on local conditions.

    A cell needs a reading on both sides. `indistinguishable` and `no_floor` are
    the third state, and rule 31 forbids reading "not supported" as "refuted",
    so either of them on either side means there is no cell to name. The first
    version of this function tested `== "above"` and so folded "refuted" in with
    "not read", which is the collapse that rule forbids, and it then wrote the
    result as "mixed" and listed the cells it had not placed anything in. A key
    in the split is where a reader counts occupancy, so the split now carries
    counts and only for cells actually occupied; the prose that says why a cell
    is empty goes to the note, where nothing counts it.

    Returns (grid, split or None, note).
    """
    ours_read = ours_cell == "above"
    ours_refuted = ours_cell == "below"
    rival_read = rival_cell == "above"
    rival_refuted = rival_cell == "below"
    note = {"ours": OURS_MAP[ours_cell], "rival": RIVAL_MAP[rival_cell]}
    if not (ours_read or ours_refuted) or not (rival_read or rival_refuted):
        note["why"] = ("a cell needs a reading on both sides and at least one "
                       "side produced none here, so this criterion places "
                       "nothing on the table and names no cell")
        return "unread", None, note
    if ours_read and rival_refuted:
        note["why"] = ("our side read what it registered and the rival's fell "
                       "below its own floor: the distinguishing cell")
        return "B", None, note
    if ours_read and rival_read:
        note["why"] = ("our side read what it registered; the rival's regressor "
                       "also read, so on that regressor both accounts agree, "
                       "which by rule 0b is still scored as ours")
        return "mixed", {"B": 1, "A": 1}, note
    if ours_refuted and rival_read:
        note["why"] = ("our side is refuted here and the rival's held: the one "
                       "cell that counts against this framework")
        return "C", None, note
    note["why"] = ("both sides read and neither prediction held, which rule 0b "
                   "scores as a lead towards a wider account rather than as a "
                   "loss for either")
    return "both_unmet", None, note


def fmt_gaps(gaps, shifts):
    parts = []
    for sh in shifts:
        g = gaps.get(sh)
        if g is None:
            parts.append(f"{sh}d not built")
        else:
            z = "n/a" if g["z"] is None else f"{g['z']:+.2f}"
            parts.append(f"{sh}d real {g['real']:+.4f} (se {g['se_real']:.4f}) vs placebo "
                         f"{g['placebo']:+.4f} (se {g['se_placebo']:.4f}) on n {g['n']} over "
                         f"{g['clusters']} clusters, {z} combined se")
    return "; ".join(parts)


def criteria(cfg, counters, recs, dropped, out):
    crits = []
    states = sorted({r[0] for r in recs})
    markets = {(r[0], r[1]) for r in recs}
    days = {r[2] for r in recs}
    kept = len(recs)

    mch = out["monthly_changes"]
    lev0 = out["levels"]

    def usable_shifts(arm):
        ok, thin = [], []
        for sh in cfg.shifts_days:
            d = arm["per_shift"].get(sh)
            if d is None:
                continue
            (ok if d["real"]["cluster_rank_ok"] and d["placebo"]["cluster_rank_ok"]
             else thin).append(sh)
        return ok, thin

    ok_m, thin_m = usable_shifts(mch)
    ok_l, thin_l = usable_shifts(lev0)

    def phrase(name, arm, ok, thin, denom):
        return (f"{name}: {len(ok) + len(thin)} of {len(cfg.shifts_days)} shifts reach enough "
                f"of the {denom} rows to be fitted, {len(ok)} of them over at least as many "
                f"clusters as the fit has coefficients"
                + (f" ({', '.join(str(s) + 'd' for s in thin)} do not and are dropped)"
                   if thin else ""))

    crits.append({
        "name": "B61-0  every comparison is a real fit and a placebo on the same rows, over enough clusters to have a covariance",
        "kind": "premise", "passed": bool(ok_m or ok_l),
        "detail": (phrase("monthly changes", mch, ok_m, thin_m, mch["pairs"]) + "; "
                   + phrase("levels", lev0, ok_l, thin_l, kept)
                   + ". Each fitted shift runs the real branch series and the shifted one on "
                     "exactly the rows that shift reaches, so the two standard errors share a "
                     "sample and a cluster count. A cluster-robust meat matrix is a sum of one "
                     "outer product per cluster, so with fewer clusters than coefficients it is "
                     "singular and its standard errors carry nothing; that is arithmetic and "
                     "not a threshold. An arm with no surviving shift has no floor, and its "
                     "reading below is not adjudicable rather than failed")})

    crits.append({
        "name": "B61-1  the carrier parses and the branch has something to be read from",
        "kind": "instrument", "passed": kept > 0 and len(states) > 0,
        "detail": (f"{counters['lines']} lines, {counters['malformed']} malformed, "
                   f"{counters['other_variety']} of another variety, "
                   f"{counters['unreadable_or_nonpositive']} with an unreadable date or a "
                   f"non-positive price or arrival. {kept} rows kept across {len(states)} "
                   f"states, {len(markets)} markets and {len(days)} days; {dropped} rows "
                   f"dropped because their state had fewer than {cfg.min_state_markets} "
                   f"markets reporting that day, so no leave-one-out branch exists for them")})

    # Structural, not a comparison. The design sheet asks this criterion to print
    # three numbers so the absorbing step is visible in the record; the first
    # implementation asserted they fall monotonically, which is a claim about the
    # world that nothing registered, and it fired on two thin commodities.
    d = out["shared_term_diagnostic"]
    crits.append({
        "name": "B61-2  the shared subtraction is removed rather than left in",
        "kind": "instrument",
        "passed": all(v is not None and not math.isnan(v) for v in d.values()),
        "detail": (f"dev and dev_state both subtract nat(t), so they correlate through "
                   f"var(nat) even under independence. corr(dev, dev_state) is "
                   f"{d['raw']:.4f} raw, {d['day_fe']:.4f} under a day fixed effect which "
                   f"absorbs nat(t) exactly, and {d['day_and_market_fe']:.4f} with a market "
                   f"effect added. The regressions use the absorbed form. "
                   f"corr(dev, log arrivals) is {d['raw_dev_vs_local']:.4f} raw and "
                   f"{d['day_and_market_fe_dev_vs_local']:.4f} absorbed")})

    g3 = shift_gaps(mch, "b_state", "se_state")
    c3 = cell_of(g3, mch["real_full_sample"], "b_state")
    crits.append({
        "name": "B61-3  monthly changes: the branch loading against its own shifted floor",
        "kind": "own_reading", "passed": OURS_VERDICT[c3], "cell": c3,
        "cell_map": OURS_MAP,
        "detail": (fmt_gaps(g3, cfg.shifts_days) + f". Cell: {OURS_MAP[c3]}")})

    g4 = shift_gaps(mch, "b_arr", "se_arr")
    c4 = cell_of(g4, mch["real_full_sample"], "b_arr")
    grid, split, grid_note = grid_of(c3, c4)
    crits.append({
        "name": "B61-4  the rival's regressor: does the deviation load on the region's own conditions",
        "kind": "rival", "passed": RIVAL_VERDICT[c4], "cell": c4,
        "cell_map": RIVAL_MAP,
        "rival_shape": "direction",
        "rival_premise": ("A distance-weighted equilibrium: the value at a position is set "
                          "by that position's own conditions and its distance from the anchor. "
                          "This is the branch B30-5 names in as many words, 'loads on local "
                          "conditions -> the field is an equilibrium'."),
        "rival_entailment": ("If the field is generated that way then, once the day's national "
                             "level and the market's fixed position are held out, a market's "
                             "deviation is explained by its own supply conditions, and the "
                             "identity of the intermediary carries no further information. So "
                             "the coefficient on the market's own arrivals has to clear a floor "
                             "built by shifting the intermediary series, and the coefficient on "
                             "the intermediary must not."),
        "grid": grid,
        **({"grid_split": split} if split else {}),
        "grid_note": grid_note,
        "detail": (fmt_gaps(g4, cfg.shifts_days) + f". Cell: {RIVAL_MAP[c4]}")})

    lev = out["levels"]
    g5 = shift_gaps(lev, "b_state", "se_state")
    c5 = cell_of(g5, lev["real_full_sample"], "b_state")
    crits.append({
        "name": "B61-5  levels: the same pair read again, with its own floor",
        "kind": "own_reading", "passed": OURS_VERDICT[c5], "cell": c5,
        "cell_map": OURS_MAP,
        "detail": (fmt_gaps(g5, cfg.shifts_days) + f". Cell: {OURS_MAP[c5]}. A state's level "
                   f"relative to the country is persistent, so a shifted placebo keeps most "
                   f"of the real loading here; the monthly-change arm is the one that "
                   f"differences that term away")})

    def cov(arm, denom):
        parts = []
        for sh in cfg.shifts_days:
            d = arm["per_shift"].get(sh)
            if d is None:
                parts.append(f"{sh}d not built")
            else:
                parts.append(f"{sh}d {d['n']} of {denom} "
                             f"({100.0 * d['n'] / denom:.1f} percent) over "
                             f"{d['real']['clusters']} clusters, subsample b_state "
                             f"{d['real']['b_state']:+.4f}")
        return "; ".join(parts)

    crits.append({
        "name": "B61-6  what the counts are not",
        "kind": "bookkeeping", "passed": True,
        "detail": (f"{kept} rows come from {len(markets)} markets in {len(states)} states over "
                   f"{len(days)} days, and no count in this record is an independent-observation "
                   f"count. Standard errors are clustered on the state, which is the level the "
                   f"branch varies at; the iid figure is in every fit beside the clustered one. "
                   f"The three commodities are downstream of one market system, so a replication "
                   f"across them is not three independent samples")})
    fm, fl = mch["real_full_sample"], lev["real_full_sample"]
    crits.append({
        "name": "B61-7  how much of the sample each shift reaches, and whether it stands in for it",
        "kind": "instrument", "passed": True,
        "detail": (("monthly changes, full sample b_state "
                    + (f"{fm['b_state']:+.4f} over {fm['clusters']} clusters on n {fm['n']}: "
                       if fm else "not built: ")
                    + cov(mch, max(mch["pairs"], 1))
                    + ". Levels, full sample b_state "
                    + (f"{fl['b_state']:+.4f} over {fl['clusters']} clusters on n {fl['n']}: "
                       if fl else "not built: ")
                    + cov(lev, max(kept, 1))
                    + ". A shift reaches only the rows where the same state reported that "
                      "many days later, so a low coverage or a subsample coefficient far "
                      "from the full-sample one says the comparison above is running on a "
                      "selected slice. This criterion reports those numbers and judges "
                      "nothing"))})

    def jack_line(sh):
        d = mch["per_shift"].get(sh)
        if d is None or "leave_one_state_out" not in d:
            return f"{sh}d not built"
        g = shift_gaps(mch, "b_state", "se_state").get(sh)
        base = f"{g['z']:+.2f}" if g and g["z"] is not None else "n/a"
        parts = []
        for state, j in sorted(d["leave_one_state_out"].items()):
            if j is None:
                parts.append(f"{state} not readable without it")
            else:
                parts.append(f"{state} ({j['pairs_dropped']} pairs) leaves "
                             f"{j['n']} over {j['clusters']}, z {j['z']:+.2f}")
        return f"{sh}d base z {base}; dropping " + ", ".join(parts)

    crits.append({
        "name": "B61-8  how many states carry the monthly reading, one left out at a time",
        "kind": "instrument", "passed": True,
        "detail": ("; ".join(jack_line(sh) for sh in cfg.shifts_days)
                   + ". A cluster count says how many states there are and cannot say how "
                     "many of them carry the reading, so each is dropped in turn and the "
                     "figure reprinted. A state holding most of the pairs takes the reading "
                     "with it when dropped and that says nothing; a state holding few of "
                     "them and still moving the figure is the one to read. This criterion "
                     "prints and judges nothing")})

    return crits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commodity", default="Lentil (Masur)")
    ap.add_argument("--variety", default="Other")
    ap.add_argument("--min-state-markets", type=int, default=MIN_STATE_MARKETS)
    ap.add_argument("--source", choices=("csv", "api"), default="csv",
                    help="csv: the yearly per-commodity files, which carry state, "
                         "district and market. api: the state-month JSON fetch, which "
                         "carries state and market and no district")
    a = ap.parse_args(argv)
    cfg = Config(commodity=a.commodity, variety=a.variety,
                 min_state_markets=a.min_state_markets, source=a.source)

    rows, counters = read_rows(cfg)
    if not rows:
        print(f"B61: no usable row for {cfg.commodity} / variety {cfg.variety}")
        return 1
    recs, dropped = build(rows, cfg)
    print(f"B61: {cfg.commodity} / variety {cfg.variety}")
    print(f"  {counters['lines']} lines, {len(rows)} of this variety with a readable "
          f"price and arrival")
    print(f"  {len(recs)} rows keep a leave-one-out branch, {dropped} dropped for "
          f"fewer than {cfg.min_state_markets} markets in the state that day")
    if not recs:
        print("  no row has a branch to be read from")
        return 1
    out = arms(recs, cfg)

    for name in ("monthly_changes", "levels"):
        arm = out[name]
        full = arm["real_full_sample"]
        if full is None:
            print(f"  [{name}] not built")
            continue
        print(f"  [{name}] full sample n {full['n']}, {full['clusters']} state clusters: "
              f"b_state {full['b_state']:+.4f} (se {full['se_state']:.4f}), "
              f"b_arr {full['b_arr']:+.4f} (se {full['se_arr']:.4f})   [reported, not read]")
        for sh in cfg.shifts_days:
            d = arm["per_shift"].get(sh)
            if d is None:
                print(f"            shift {sh}d: not built")
                continue
            r, pl = d["real"], d["placebo"]
            print(f"            shift {sh}d on n {d['n']} over {r['clusters']} clusters: "
                  f"b_state real {r['b_state']:+.4f} (se {r['se_state']:.4f}) vs placebo "
                  f"{pl['b_state']:+.4f} (se {pl['se_state']:.4f}); "
                  f"b_arr real {r['b_arr']:+.4f} (se {r['se_arr']:.4f}) vs placebo "
                  f"{pl['b_arr']:+.4f} (se {pl['se_arr']:.4f})")

    record = {"stage": "B61",
              "config": {"commodity": cfg.commodity, "variety": cfg.variety,
                         "source": cfg.source,
                         "min_state_markets": cfg.min_state_markets,
                         "month_window_days": [cfg.month_lo, cfg.month_hi],
                         "shifts_days": list(cfg.shifts_days),
                         "cluster": cfg.cluster},
              "input": counters | {"rows_of_variety": len(rows),
                                   "rows_with_branch": len(recs),
                                   "rows_dropped_no_branch": dropped,
                                   "states": sorted({r[0] for r in recs}),
                                   "markets": len({(r[0], r[1]) for r in recs}),
                                   "days": len({r[2] for r in recs})},
              "readings": rd(out)}
    crits = criteria(cfg, counters, recs, dropped, out)
    record["criteria"] = crits

    print()
    for c in crits:
        mark = {True: "PASS", False: "FAIL", None: "----"}[c["passed"]]
        tag = f"FAILED[{c['kind']}]" if c["passed"] is False else mark
        print(f"  [{tag}] {c['name']}\n         {c['detail']}")
    n_pass = sum(1 for c in crits if c["passed"] is True)
    n_open = sum(1 for c in crits if c["passed"] is None)
    n_fail = sum(1 for c in crits if c["passed"] is False)
    print(f"\n  {n_pass}/{len(crits)} passed, {n_open} not adjudicated, {n_fail} failed\n")

    RESULTS.mkdir(parents=True, exist_ok=True)
    # The variety is part of the record's identity, because rule 49 makes it a
    # stratum and not noise: a price gap between varieties is not a price gap
    # between markets. Only a non-default variety takes a suffix, so the three
    # records already on disk and already cited keep their names.
    slug = cfg.commodity.split(" ")[0].lower().strip("(),")
    if cfg.source != Config.source:
        slug = cfg.source + "_" + "".join(c for c in cfg.commodity.lower() if c.isalnum())
    if cfg.variety != Config.variety:
        slug += "_" + "".join(c for c in cfg.variety.lower() if c.isalnum())
    p = RESULTS / f"b61_branch_loading_{slug}.json"
    p.write_text(json.dumps(record, indent=2, default=str, sort_keys=True) + "\n",
                 encoding="utf-8", newline="\n")
    print(f"  wrote {p.relative_to(ROOT)}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
