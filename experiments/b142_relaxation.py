"""B142: after a loop sum moves away, does it come back, and does that depend on who can cross?

This file runs in steps so that each one can be read before the next is written.

    python experiments/b142_relaxation.py --audit
        Counts what is on disk, carrier by carrier: how many series, at what frequency, how long,
        and the three shortest. Each carrier is loaded with its own station's loader, so the
        object counted is the object that station read. Nothing is compared.
    python experiments/b142_relaxation.py --selftest
        The instrument against known answers. It reads one record, b52_restoring_force.json,
        and writes nothing.
    python experiments/b142_relaxation.py --describe
        The object before any test of it: the autocorrelation of the steps, and how fast the
        k-step difference grows with k. One pass, no sampling.
    python experiments/b142_relaxation.py --plant
        What the instrument can and cannot tell apart at each carrier's own shape: a level with
        no restoring force and a planted one, both built on that carrier's own steps. With
        --formal every simulated panel also goes through the whole reading a real panel gets.

The readings are taken by b142_reading.py, which decides the cells, reads each one with the
functions here and keeps what it read; b142_record.py builds the record from what was kept.
Nothing in this file is changed by either.

A series here is one loop sum or one square sum followed through time. A carrier is the object
several series were read off. Series inside one carrier share their shocks, so the independent
unit across carriers is the carrier and not the series.

The statistic is the one b52_restoring_force.py reads. At every point where a series stands far
from its own median, count whether the next step goes back toward it. The centre is estimated
from the same path, so a level with no restoring force in it already reads well above one half,
and the null is therefore measured: the same count on paths rebuilt from the series' own steps.
That file is pure Python and stays the reference. The functions here are a second
implementation in arrays, checked against it by --selftest, because two of the carriers are a
thousand times longer than the panel that file was written for.

Two things are added to what that file does, and the selftest plants the fault behind each.

It rebuilds each series on its own, which is right when the series are independent. Series read
off one carrier are not: three exchange-rate pairs that share a leg are close to one series
counted three times, and a null that rebuilds them separately comes out too narrow by about the
square root of three. So here the dates are what is drawn, and every series takes its own steps
on the dates drawn. The reference's way, series by series, is kept as a mode.

It reads the observed proportion against a line, the null's mean plus 1.645 of its spread. That
line is where a panel with no restoring force should land one time in twenty, and on some
shapes it is not where one does land: on the daily covered-parity series 7 of 24 panels built
with no force in them landed above it. Two things measured on those steps push that way. They
are heavy-tailed, the largest one per cent carrying a third of the step sum of squares, and a
resample that can repeat the largest step or miss it reads 0.0023 lower than the same steps
reordered, two thirds of the floor. And they are negatively autocorrelated, which every block
boundary breaks. Reordering the dates without replacement did not remove it, 7 of 24 again,
and on the shortest panel it saw a planted force less often. So blocks are drawn with
replacement as the reference draws them, and the panel is also held against panels built from
its own steps with no force in them, read the same way. It counts as above only when it clears
every one of those as well as the line.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"

Z90 = 1.6448536269514722
TERCILE = 2.0 / 3.0     # a point is far from the centre when it is in the top third of deviations
MIN_POINTS = 4          # a path shorter than this is not counted; b52_restoring_force.reversion
MIN_SERIES = MIN_POINTS + 1   # a series is read when its rebuilt path, one point per step, has MIN_POINTS
#                         points: the count, the nulls and the panels with no force then cover the same series
MIN_UNITS = 3           # fewer series than this is not a reading; b52_restoring_force.one_reading
NSIM = 200
SEED = 42
SEED2 = 50_000          # the second seed of a settled reading is SEED + SEED2
DRAWS = (200, 800, 3200)
BUDGET = 2e8            # points times draws in one pass; past this a marginal reading is
#                         reported as marginal and no more draws are bought for it
HALF_LIVES = (1, 2, 4, 8, 16, 32, 64)          # in steps of whatever frequency is being read

# Block lengths as multiples of L ** (1/3), L the median series length. At L = 37 these are
# 2, 3, 4, 6, 8 and then 12, 16, which is the ladder b52_restoring_force.py printed and the two
# lengths it printed as a trend and did not use. The multiples travel with the length here.
# Past the eligible ones a resampled path is mostly one run of the original and the null turns
# into the observation.
ELIGIBLE = (0.6, 0.9, 1.2, 1.8, 2.4)
TREND = (3.6, 4.8)

LAGS = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048)
MIN_WINDOWS = 4         # a lag is read on a series only if it fits this many times end to end

STATES = {
    "above": "the series goes back more often than a level with no restoring force does",
    "inside": "not told apart from a level with no restoring force",
    "below": "the series goes back less often than a level with no restoring force does",
    "marginal": "two seeds do not agree on the side; not measured, no verdict",
    "unread": "too few series or too few far points; no reading and no verdict",
}


# ---------------------------------------------------------------------------------------------
# the stations' own loaders
# ---------------------------------------------------------------------------------------------

def station(name: str):
    """Import a station's own script as a module, without running its main."""
    if name in sys.modules:
        return sys.modules[name]
    if str(EXP) not in sys.path:
        sys.path.insert(0, str(EXP))
    spec = importlib.util.spec_from_file_location(name, EXP / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _day(t) -> dt.date:
    return t if isinstance(t, dt.date) else dt.date.fromisoformat(str(t)[:10])


def load_b9():
    m = station("b9_omega")
    spreads = m.read_spread_table()
    arms = {}
    for arm, tickers in (("main arm", m.MAIN_ARM), ("comparison arm", m.COMPARISON_ARM),
                         ("neither", m.NEITHER)):
        ser = {}
        for t in tickers:
            s = m.lambda_series(t, spreads)
            ser[t] = [(_day(d), s[d]["lam"]) for d in sorted(s)]
        arms[arm] = ser
    return {"arms": arms, "freq": "D", "min_common": MIN_UNITS,
            "caliber": "signed lambda = log(1 + premium) per fund-day, the station's own filter"}


def load_b3():
    m = station("b3_cip_slice")
    data = m.load()
    by = defaultdict(lambda: defaultdict(list))
    for (g, tenor, date), cur in data["dev"].items():
        d = m.parse_date(date)
        for c, x in cur.items():
            by[g][(c, tenor)].append((d, x))
    arms = {g: {u: sorted(v) for u, v in s.items()} for g, s in sorted(by.items())}
    # The station's object is the cross-currency cycle z(i,j) = x(i) - x(j) at one tenor. Taking
    # the date-common term out inside each tenor reads the same space in a symmetric basis.
    return {"arms": arms, "freq": "D", "min_common": MIN_UNITS, "group": lambda u: u[1],
            "caliber": "cip_govt in basis points per (currency, tenor), against the dollar"}


def load_b59():
    m = station("b59_reserve_class_rate")
    bp = {s: m.parse_bp(m.fetch(s))[0] for s in m.SERIES}
    arms = {}
    for adm, lo, hi in (("IOER", None, "2021-07-28"), ("IORB", m.BREAK, None)):
        ser = sorted((_day(d), float(v - bp["EFFR"][d])) for d, v in bp[adm].items()
                     if d in bp["EFFR"] and (lo is None or d >= lo) and (hi is None or d <= hi))
        arms[f"{adm} minus EFFR"] = {adm: ser}
    return {"arms": arms, "freq": "D",
            "caliber": "integer basis points on a 1 bp grid",
            "not_read": "the station says this net gap is not a loop against the scalar field, "
                        "and each era is one series"}


def load_b21():
    m = station("b21_cross_section")
    pan, _names = m.panel()
    ser = defaultdict(list)
    for d in sorted(pan):
        for pair, v in pan[d].items():
            ser[pair].append((_day(d), v))
    cuts = [_day(d) for d, _what in m.EVENTS]
    edges = [None] + cuts + [None]
    segs = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        label = (f"before {hi}" if lo is None else f"from {lo}" if hi is None else f"{lo} to {hi}")
        segs.append((label, lo, None if hi is None else hi - dt.timedelta(days=1)))
    return {"arms": {"A over H, log premium": dict(ser)}, "freq": "D", "min_common": m.MIN_PAIRS,
            "segments": segs, "segments_from": "b21_cross_section.EVENTS",
            "caliber": "log(P_A * rate / P_H) per pair-day, one rate for every pair"}


def load_b5():
    m = station("b5_squares")
    classes = m.load_agent_classes(m.RAW)
    keys = tuple(classes)
    dates = m.in_window(sorted(set().union(*(set(v) for v in classes.values()))),
                        (m.WINDOW_START, m.WINDOW_END))
    groups = defaultdict(dict)
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            s = m.pair_series(classes, left, right, dates)
            if s:
                groups[m.pair_group(left, right)][f"{left}-{right}"] = [(_day(d), v) for d, v in s]
    cut = m.INTERVENTION
    segs = [(f"before {cut}", None, cut - dt.timedelta(days=1)), (f"from {cut}", cut, None)]
    return {"arms": dict(groups), "freq": "D", "segments": segs,
            "segments_from": "parallel_rates.INTERVENTION",
            "caliber": "S - S' per pair-day in logs"}


def load_b52():
    rf = station("b52_restoring_force")
    cells = json.loads(rf.SRC.read_text(encoding="utf-8"))["cells"]
    arms = {}
    for base in ("I_TAX", "X_TAX", "X_VAT"):
        ser = defaultdict(list)
        for c in cells:
            if c.get(base) is not None:
                ser[c["geo"]].append((c["semester"], float(c[base])))
        arms[f"class square, {base}"] = {k: sorted(v) for k, v in ser.items()}
    segs = [(f"up to {rf.PRE_CRISIS_END}", None, rf.PRE_CRISIS_END)]
    return {"arms": arms, "freq": "S", "min_common": MIN_UNITS, "segments": segs,
            "segments_from": "b52_restoring_force.PRE_CRISIS_END",
            "caliber": "square sum per country-semester, read from the station's record"}


def load_b49():
    rec = json.loads((ROOT / "results" / "b49_energy_class_square.json").read_text(encoding="utf-8"))
    ser = defaultdict(list)
    for c in rec["cells"]:
        ser[c["country"]].append((str(c["year"]), float(c["square_sum"])))
    return {"arms": {"class square": {k: sorted(v) for k, v in ser.items()}}, "freq": "Y",
            "caliber": "square sum per country-year, read from the station's record",
            "not_read": "three years per country, so no series reaches four points"}


# Greece cut its own external edge on 2015-06-29 (b97_edge_restoration.py, its opening note) and is
# no control from then. That station leaves the month of an event out of the spans on either side
# of it, so the last month Greece is read as a control is May.
B97_CONTROL_ENDS = {"GR": "2015-05"}


def load_b97():
    m = station("b97_edge_restoration")
    labels = list(m.SHAPES)
    arms = {}
    for area in (m.CARRIER,) + tuple(m.CONTROLS):
        end = B97_CONTROL_ENDS.get(area)
        ser = {}
        for i, a in enumerate(labels):
            for b in labels[i + 1:]:
                ser[f"{m.SHORT[a]} x {m.SHORT[b]}"] = sorted(
                    (t, v) for t, v in m.square(area, a, b).items() if end is None or t <= end)
        arms[f"squares, {area} against the euro area"] = ser
    return {"arms": arms, "freq": "M", "segments": [(lab, lo, hi) for lab, lo, hi in m.SPANS],
            "segments_from": "b97_edge_restoration.SPANS", "control_ends": dict(B97_CONTROL_ENDS),
            "caliber": "two positions by two goods, percentage points; published tick 0.005"}


def load_b128():
    m = station("b128_a_rate_dose")
    data = m.load_rates()
    arms = {}
    for name, shapes in m.PRODUCT_SETS.items():
        arms[f"rates behind the interaction, {name}"] = {
            (area, shape): sorted(s.items()) for (area, shape), s in data.items()
            if shape in shapes and area in m.JOINED}
    return {"arms": arms, "freq": "M",
            "caliber": "monthly new-business rates per (country, product)",
            "not_read": "the same product in two countries sits under two sovereigns' deposit "
                        "cover, so the square is not one position held by two classes"}


LOADERS = (("B9", load_b9), ("B3", load_b3), ("B59", load_b59), ("B21", load_b21),
           ("B5", load_b5), ("B52", load_b52), ("B49", load_b49), ("B97", load_b97),
           ("B128", load_b128))


def carriers(only=None):
    """Yield (tag, carrier dict) with every arm as {unit: (times, values array)}."""
    for tag, loader in LOADERS:
        if only and tag not in only:
            continue
        try:
            c = loader()
        except SystemExit as e:
            yield tag, {"error": str(e)}
            continue
        except Exception as e:                              # printed by the caller, never swallowed
            yield tag, {"error": f"{type(e).__name__}: {e}"}
            continue
        c["arms"] = {arm: {u: ([t for t, _ in pts], np.array([v for _, v in pts], dtype=float))
                           for u, pts in ser.items()}
                     for arm, ser in c["arms"].items()}
        yield tag, c


# ---------------------------------------------------------------------------------------------
# shaping a panel: a window, a coarser calendar, the date-common term taken out
# ---------------------------------------------------------------------------------------------

def as_units(x):
    """{unit: (times, values)} from that, or from {unit: values} with the position as the time."""
    out = {}
    for u, v in x.items():
        if isinstance(v, tuple):
            out[u] = (list(v[0]), np.asarray(v[1], dtype=float))
        else:
            v = np.asarray(v, dtype=float)
            out[u] = (list(range(len(v))), v)
    return out


def values(units):
    return {u: vs for u, (_ts, vs) in units.items()}


def window(units, lo, hi):
    """Keep lo <= time <= hi; either end may be None."""
    out = {}
    for u, (ts, vs) in units.items():
        keep = [i for i, t in enumerate(ts) if (lo is None or t >= lo) and (hi is None or t <= hi)]
        if keep:
            out[u] = ([ts[i] for i in keep], vs[keep])
    return out


def thin(units, how):
    """Daily to the last observation of each ISO week ("W") or calendar month ("M").

    The last one actually observed, never a filled one. Keyed on the calendar, so there is no
    offset to choose.
    """
    out = {}
    for u, (ts, vs) in units.items():
        last = {}
        for i, t in enumerate(ts):
            key = tuple(t.isocalendar())[:2] if how == "W" else (t.year, t.month)
            last[key] = i                                   # times ascend, so the last write wins
        keep = [last[k] for k in sorted(last)]
        out[u] = ([ts[i] for i in keep], vs[keep])
    return out


def less_common(units, min_units, group=None):
    """Take out of every series the step that all series present on that date share.

    The common step between two consecutive dates is the mean step over the series observed on
    both. It is chained into a level and subtracted, so a series joining or leaving changes
    nothing: the composition of a mean of steps can change, a mean of levels would jump.
    Whatever enters every series on a date identically is removed identically, and a date with
    fewer than min_units series has no common step and is counted.
    """
    groups = defaultdict(dict)
    for u, tv in units.items():
        groups[group(u) if group else None][u] = tv
    out = {}
    st = {"steps": 0, "steps_without_a_common_term": 0, "common_ss": 0.0, "total_ss": 0.0}
    for us in groups.values():
        times = sorted({t for ts, _ in us.values() for t in ts})
        pos = {t: i for i, t in enumerate(times)}
        names = list(us)
        M = np.full((len(names), len(times)), np.nan)
        for r, u in enumerate(names):
            ts, vs = us[u]
            M[r, [pos[t] for t in ts]] = vs
        D = M[:, 1:] - M[:, :-1]
        seen = ~np.isnan(D)
        cnt = seen.sum(axis=0)
        tot = np.where(seen, D, 0.0).sum(axis=0)
        c = np.where(cnt >= min_units, tot / np.maximum(cnt, 1), 0.0)
        C = np.concatenate([[0.0], np.cumsum(c)])
        for u in names:
            ts, vs = us[u]
            out[u] = (ts, vs - C[[pos[t] for t in ts]])
        st["steps"] += len(times) - 1
        st["steps_without_a_common_term"] += int(np.sum(cnt < min_units))
        st["common_ss"] += float(np.sum(cnt * c * c))
        st["total_ss"] += float(np.where(seen, D * D, 0.0).sum())
    st["common_share_of_step_ss"] = (st["common_ss"] / st["total_ss"]) if st["total_ss"] else None
    return out, st


def step_days(units, freq):
    """Calendar days per step, measured from the dates where there are dates."""
    if freq == "S":
        return 365.25 / 2
    if freq == "Y":
        return 365.25
    if freq == "M" and not any(isinstance(ts[0], dt.date) for ts, _ in units.values() if ts):
        return 365.25 / 12
    spans = [(ts[-1] - ts[0]).days / (len(ts) - 1) for ts, _ in units.values() if len(ts) > 1]
    return float(np.median(spans)) if spans else None


def step_matrix(units):
    """Every series' steps laid on the carrier's common date axis.

    D[series, date] is the series' step that ends on that date, counted from its own previous
    observation, and NaN where the series has no observation on that date. A series keeps every
    one of its steps, whatever it skipped.
    """
    times = sorted({t for ts, _ in units.values() for t in ts})
    pos = {t: i for i, t in enumerate(times)}
    names = sorted(units, key=str)
    D = np.full((len(names), len(times)), np.nan)
    for r, u in enumerate(names):
        ts, vs = units[u]
        if len(vs) > 1:
            D[r, [pos[t] for t in ts[1:]]] = np.diff(vs)
    return names, D[:, 1:]


# ---------------------------------------------------------------------------------------------
# the statistic and its nulls, in arrays
# ---------------------------------------------------------------------------------------------

def counts(X, q=TERCILE):
    """X is (paths, points) for one series. Back and away counts per path.

    Line for line what b52_restoring_force.reversion does to one series: the centre is the
    path's own median, a point is far when its deviation is at or above the q quantile of that
    path's deviations, a zero step is not counted, and a step whose product with the deviation
    is negative goes back.
    """
    X = np.atleast_2d(np.asarray(X, dtype=float))
    n = X.shape[1]
    if n < MIN_POINTS:
        z = np.zeros(X.shape[0], dtype=np.int64)
        return z, z.copy()
    dev = X - np.median(X, axis=1)[:, None]
    a = np.abs(dev)
    k = min(n - 1, max(0, int(round(q * (n - 1)))))
    cut = np.partition(a, k, axis=1)[:, k]
    step = X[:, 1:] - X[:, :-1]
    use = (a[:, :-1] >= cut[:, None]) & (step != 0)
    back = use & (step * dev[:, :-1] < 0)
    nb = back.sum(axis=1)
    return nb, use.sum(axis=1) - nb


def observed(vals, q=TERCILE):
    back = away = 0
    per = {}
    for u in sorted(vals, key=str):
        v = vals[u]
        if len(v) < MIN_POINTS:
            per[str(u)] = {"points": int(len(v)), "used": 0}
            continue
        b, a = counts(v[None, :], q)
        back += int(b[0])
        away += int(a[0])
        per[str(u)] = {"points": int(len(v)), "used": int(b[0] + a[0]), "back": int(b[0])}
    n = back + away
    return {"back": back, "away": away, "n": n,
            "proportion": (back / n) if n else None, "per_unit": per}


def _integrate(steps, phi):
    """x[t] = phi * x[t-1] + step[t], from zero. phi = 1 is a level with no restoring force."""
    if phi == 1.0:
        return np.cumsum(steps, axis=1)
    return lfilter([1.0], [1.0, -phi], steps, axis=1)


def paths(v, kind, nsim, rng, block=None, phi=1.0):
    """Simulated paths for one series on its own, (nsim, length), or None when it is too short.

    walk     Gaussian steps at the series' own step scale; as many points as the series
    shuffle  the series' own steps in a random order; one point per step
    block    the series' own steps resampled in circular blocks; one point per step
    """
    d = np.diff(v)
    L = len(d)
    if kind == "walk":
        s = float(d.std(ddof=1)) if L >= 2 else 0.0
        steps = rng.normal(0.0, s if s > 0 else 1.0, size=(nsim, len(v)))
    elif kind == "shuffle":
        if L < 1:
            return None
        steps = rng.permuted(np.tile(d, (nsim, 1)), axis=1)
    elif kind == "block":
        if L < 2:
            return None
        b = min(int(block), L)
        nb = -(-L // b)
        starts = rng.integers(0, L, size=(nsim, nb))
        idx = ((starts[:, :, None] + np.arange(b)[None, None, :]) % L).reshape(nsim, nb * b)[:, :L]
        steps = d[idx]
    else:
        raise ValueError(kind)
    return _integrate(steps, phi)


def _q(sorted_x, p):
    return float(sorted_x[min(len(sorted_x) - 1, max(0, int(round(p * (len(sorted_x) - 1)))))])


def take(row, idx):
    """One series' steps on the dates drawn, in the order drawn.

    row is the series' line of the step matrix and idx is (nsim, dates drawn). Returns
    (nsim, the series' own number of steps) and how many slots stayed empty because the dates
    drawn held fewer of its steps than that. Empty slots are zero steps at the end of the path.
    """
    S = len(row)
    Lu = int(np.sum(~np.isnan(row)))
    if Lu == S:
        return row[idx[:, :S]], 0
    G = row[idx]
    V = ~np.isnan(G)
    rank = np.cumsum(V, axis=1) - 1
    rr, cc = np.nonzero(V & (rank < Lu))
    steps = np.zeros((idx.shape[0], Lu))
    steps[rr, rank[rr, cc]] = G[rr, cc]
    return steps, int((Lu - np.minimum(V.sum(axis=1), Lu)).sum())


def null(vals, kind, nsim, seed, q=TERCILE, block=None, phi=1.0, D=None, raw=False):
    """The pooled proportion on nsim simulated panels with a level that is not pulled back.

    Without D every series is rebuilt on its own, as the reference does: its steps shuffled, or
    resampled in circular blocks with replacement. With D, the step matrix of the panel, the
    dates are what is drawn: one sequence of dates per simulation, and every series takes its
    own steps on those dates, in that order. What the series share on a date they still share
    in the simulation. A shuffle is every date once in a random order. Blocks are circular and
    drawn with replacement, as the reference draws them; a series absent on a drawn date takes
    nothing there and goes on to its next one, so the sequence is drawn twice as long as the
    axis, and where even that leaves a series short its last steps are zero and are counted in
    padded_share. Gaussian paths are always drawn series by series: they carry no steps of the
    panel at all. With raw the per-simulation counts come back unsummarised, so that several
    panels can be pooled.
    """
    rng = np.random.default_rng(seed)
    back = np.zeros(nsim)
    tot = np.zeros(nsim)
    padded = taken = 0
    if D is None or kind == "walk":
        for u in sorted(vals, key=str):
            P = paths(vals[u], kind, nsim, rng, block, phi)
            if P is None or P.shape[1] < MIN_POINTS:
                continue
            b, a = counts(P, q)
            back += b
            tot += b + a
    else:
        S = D.shape[1]
        if kind == "shuffle":
            idx = rng.permuted(np.tile(np.arange(S), (nsim, 1)), axis=1)
        elif kind == "block":
            bl = min(int(block), S)
            nb = -(-(2 * S) // bl)
            starts = rng.integers(0, S, size=(nsim, nb))
            idx = ((starts[:, :, None] + np.arange(bl)[None, None, :]) % S).reshape(nsim, nb * bl)[:, :2 * S]
        else:
            raise ValueError(kind)
        for row in D:
            Lu = int(np.sum(~np.isnan(row)))
            if Lu < MIN_POINTS:
                continue
            steps, empty = take(row, idx)
            padded += empty
            taken += nsim * Lu
            b, a = counts(_integrate(steps, phi), q)
            back += b
            tot += b + a
    if raw:
        return back, tot
    return summarise(back, tot, kind=kind, block=block, phi=phi, padded_share=(padded / taken) if taken else 0.0)


def summarise(back, tot, **tags):
    ok = tot > 0
    ps = np.sort(back[ok] / tot[ok])
    out = dict(tags, sims=int(len(ps)), mean=None, sd=None)
    if len(ps) >= 2:
        out.update(mean=float(ps.mean()), sd=float(ps.std(ddof=1)), p05=_q(ps, 0.05), p95=_q(ps, 0.95))
    return out


def blocks_for(vals):
    L = float(np.median([len(v) for v in vals.values()]))
    p = L ** (1.0 / 3.0)
    eligible = sorted({max(2, int(round(m * p))) for m in ELIGIBLE})
    trend = sorted({int(round(m * p)) for m in TREND} - set(eligible))
    return L, p, eligible, trend


def acf1(x):
    n = len(x)
    if n < 3:
        return None
    m = x.mean()
    den = float(((x - m) ** 2).sum())
    if den <= 0:
        return None
    return float(((x[:-1] - m) * (x[1:] - m)).sum() / den)


def reading(units, *, sync=True, q=TERCILE, nsim=NSIM, seed=SEED, ladder=True, trend=True):
    """Observed proportion against the strictest eligible null, and what the panel could resolve.

    Three layers of null, all with no restoring force in the level: Gaussian steps, the panel's
    own steps in a random order, and the panel's own steps in blocks, which keeps their local
    order. The reading is held against whichever reads highest. With sync the last two draw
    dates for the whole panel; the floor is then the spread of the highest of those two layers,
    since Gaussian paths drawn series by series know nothing of what the series share. Without
    sync this is b52_restoring_force.one_reading, null for null.

    The ladder plants a force of a known half-life on top of the same block-resampled steps and
    asks which of those the panel would have told from the null: that list is what an "inside"
    reading excludes, and the rest is what it leaves open. The Gaussian ladder is the same
    force on Gaussian steps, a plain scale to place a reading on.
    """
    units = {u: tv for u, tv in as_units(units).items() if len(tv[1]) > 1}
    short = [u for u, tv in units.items() if len(tv[1]) < MIN_SERIES]
    units = {u: tv for u, tv in units.items() if len(tv[1]) >= MIN_SERIES}
    vals = values(units)
    out = {"units": len(vals) + len(short), "units_read": len(vals), "units_too_short": len(short),
           "q": q, "nsim": nsim, "seed": seed, "sync": sync}
    obs = observed(vals, q) if len(vals) >= MIN_UNITS else None
    if obs is None or not obs["n"]:
        out.update(state="unread", observed=None,
                   reason=(f"{len(vals)} series of at least {MIN_SERIES} points, {MIN_UNITS} needed"
                           if obs is None else "no far point followed by a step that is not zero"))
        return out
    L, p, eligible, trend_blocks = blocks_for(vals)
    D = step_matrix(units)[1] if sync else None
    nulls = {"gaussian_walk": null(vals, "walk", nsim, seed + 1, q),
             "shuffled_differences": null(vals, "shuffle", nsim, seed + 2, q, D=D)}
    for b in eligible:
        nulls[f"block_{b}"] = null(vals, "block", nsim, seed + 100 + b, q, block=b, D=D)
    nulls = {k: v for k, v in nulls.items() if v["mean"] is not None}
    carrying = {k: v for k, v in nulls.items() if not (sync and k == "gaussian_walk")}
    if not carrying:
        out.update(state="unread", observed=obs["proportion"], reason="no null could be built from the panel's steps")
        return out
    name = max(nulls, key=lambda k: nulls[k]["mean"])
    strict = nulls[name]
    wide = max(carrying, key=lambda k: carrying[k]["mean"])
    gap = obs["proportion"] - strict["mean"]
    floor = Z90 * carrying[wide]["sd"]
    if not floor > 0:
        out.update(state="unread", observed=obs["proportion"],
                   reason="the null has no spread on this shape, so there is no floor to hold the gap against")
        return out
    ac = [a for a in (acf1(np.diff(v)) for v in vals.values()) if a is not None]
    out.update(
        observed=obs["proportion"], back=obs["back"], away=obs["away"], n=obs["n"],
        median_length=L, usual_block=p, eligible_blocks=eligible,
        nulls={k: {"mean": v["mean"], "sd": v["sd"]} for k, v in nulls.items()},
        strict_null=name, strict_mean=strict["mean"], floor_from=wide, floor_sd=carrying[wide]["sd"],
        gap=gap, floor=floor,
        state="above" if gap > floor else "below" if gap < -floor else "inside",
        padded_share=max(v["padded_share"] for v in nulls.values()),
        step_acf1_median=float(np.median(ac)) if ac else None,
        step_acf1_negative=int(sum(a < 0 for a in ac)), step_acf1_units=len(ac),
    )
    if trend:
        out["trend_blocks_not_eligible"] = {
            b: null(vals, "block", nsim, seed + 300 + b, q, block=b, D=D)["mean"] for b in trend_blocks}
    if ladder:
        sb = carrying[wide]["block"] or max(eligible)
        own, gauss = [], []
        for H in HALF_LIVES:
            phi = 0.5 ** (1.0 / H)
            o = null(vals, "block", nsim, seed + 5000 + H, q, block=sb, phi=phi, D=D)
            g = null(vals, "walk", nsim, seed + 7000 + H, q, phi=phi)
            own.append({"half_life": H, "produces": o["mean"],
                        "separable": bool(o["mean"] - strict["mean"] > floor)})
            gauss.append({"half_life": H, "produces": g["mean"]})
        out.update(ladder_block=sb, ladder_on_own_steps=own, ladder_gaussian=gauss,
                   resolvable=[x["half_life"] for x in own if x["separable"]],
                   not_resolvable=[x["half_life"] for x in own if not x["separable"]],
                   rung_on_own_steps=locate(obs["proportion"], own) if gap > floor else None,
                   rung_gaussian=locate(obs["proportion"], gauss) if gap > floor else None)
    return out


def locate(p, ladder):
    """Which two rungs the observed proportion falls between. A faster force reads higher."""
    rungs = [(x["half_life"], x["produces"]) for x in ladder if x["produces"] is not None]
    if not rungs:
        return None
    if p >= rungs[0][1]:
        return {"at_or_faster_than": rungs[0][0]}
    for (h0, p0), (h1, p1) in zip(rungs[:-1], rungs[1:]):
        if p0 > p >= p1:
            return {"between": [h0, h1]}
    return {"slower_than": rungs[-1][0]}


def side(s):
    return "above" if s > 1 else "below" if s < -1 else "inside"


def agree(sa, sb):
    """Two readings of one position, each as gap over floor. The state both give, or None.

    They count as one measurement only when they fall on the same side and differ by less than
    the distance from their midpoint to the nearer line.
    """
    mid = 0.5 * (sa + sb)
    dist = min(abs(mid - 1.0), abs(mid + 1.0))
    return side(sa) if side(sa) == side(sb) and abs(sa - sb) < dist else None


def agree_rung(ta, tb):
    """The same for one ladder rung, which has a single line at one."""
    if (ta > 1) == (tb > 1) and abs(ta - tb) < abs(0.5 * (ta + tb) - 1.0):
        return "yes" if ta > 1 else "no"
    return "marginal"


def verdict(sa, sb, free):
    """The state of a reading: two seeds' positions, held against panels with no force in them.

    Above takes three things: both seeds over the line at one, the two close enough to count as
    one measurement, and both over every one of the panels that were built with no force. With
    nineteen such panels the last condition alone is passed one time in twenty by a panel that
    has no force either. Below is the mirror. Two seeds that do not agree are marginal; a
    reading over the line and not over the panels is inside.
    """
    st = agree(sa, sb)
    if st is None:
        return "marginal"
    if st == "above" and free and min(sa, sb) <= max(free):
        return "inside"
    if st == "below" and free and max(sa, sb) >= min(free):
        return "inside"
    return st


def _pos(r):
    if r["floor"] > 0:
        return r["gap"] / r["floor"]
    return 0.0 if r["gap"] == 0 else float(np.sign(r["gap"])) * 1e9


def settled(units, *, sync=True, q=TERCILE, seed=SEED, ladder=True, draws=DRAWS, budget=BUDGET, read=None):
    """reading() at two seeds, with more draws until the two agree which side of the line it is.

    A null built from too few draws does not fail, it prints a clean number. So the reading is
    taken twice. If the two do not agree the draws are quadrupled, up to the last entry of
    `draws` and only while a pass stays inside `budget`; what is still unsettled is reported as
    marginal and carries no verdict. Ladder rungs are settled the same way at the final number
    of draws, each to yes, no or marginal. `read` is reading() unless the selftest passes a
    scripted one to walk this loop.
    """
    read = read or reading
    units = as_units(units)
    points = sum(len(v) for v in values(units).values())
    for i, n in enumerate(draws):
        a = read(units, sync=sync, q=q, nsim=n, seed=seed, ladder=ladder, trend=True)
        if a["state"] == "unread":
            return a
        b = read(units, sync=sync, q=q, nsim=n, seed=seed + SEED2, ladder=ladder, trend=False)
        state = agree(_pos(a), _pos(b))
        if state or i + 1 == len(draws) or points * draws[i + 1] > budget:
            break
    a.update(draws=n, position=[_pos(a), _pos(b)], state_first_seed=a["state"], state=state or "marginal",
             second_seed={"strict_null": b["strict_null"], "strict_mean": b["strict_mean"],
                          "gap": b["gap"], "floor": b["floor"], "state": b["state"]})
    if ladder:
        for x, y in zip(a["ladder_on_own_steps"], b["ladder_on_own_steps"]):
            ta = (x["produces"] - a["strict_mean"]) / a["floor"] if a["floor"] > 0 else 1e9
            tb = (y["produces"] - b["strict_mean"]) / b["floor"] if b["floor"] > 0 else 1e9
            x["separable"] = agree_rung(ta, tb)
        own = a["ladder_on_own_steps"]
        a.update(resolvable=[x["half_life"] for x in own if x["separable"] == "yes"],
                 not_resolvable=[x["half_life"] for x in own if x["separable"] == "no"],
                 marginal_rungs=[x["half_life"] for x in own if x["separable"] == "marginal"])
        if a["state"] != "above":
            a.update(rung_on_own_steps=None, rung_gaussian=None)
    return a


# ---------------------------------------------------------------------------------------------
# the object before any test: how the k-step difference grows with k
# ---------------------------------------------------------------------------------------------

def profile(vals, lags=LAGS):
    """Mean squared k-step difference over the mean squared one-step difference, per lag.

    A level with no restoring force keeps growing in proportion to k, so the last column, the
    local slope in log-log, stays at one. A level that is pulled back stops growing once k is
    past the time the pull takes, and the slope falls to zero. Noise laid over a level with no
    restoring force does the opposite: the slope starts low and rises to one. A trend reads two.
    Nothing is sampled and no line is drawn: this is the object, printed.
    """
    rows = []
    for j, k in enumerate(lags):
        growth, slope = [], []
        for v in vals.values():
            if len(v) < MIN_WINDOWS * k + 1:
                continue
            d1 = float(np.mean(np.diff(v) ** 2))
            if d1 <= 0:
                continue
            dk = float(np.mean((v[k:] - v[:-k]) ** 2))
            growth.append(dk / d1)
            if j:
                prev = float(np.mean((v[lags[j - 1]:] - v[:-lags[j - 1]]) ** 2))
                if prev > 0 and dk > 0:
                    slope.append(np.log(dk / prev) / np.log(k / lags[j - 1]))
        if not growth:
            break
        g = np.array(growth)
        rows.append({"lag": k, "units": len(growth), "growth": float(np.median(g)),
                     "variance_ratio": float(np.median(g / k)),
                     "vr_q25": float(np.quantile(g / k, 0.25)), "vr_q75": float(np.quantile(g / k, 0.75)),
                     "slope": float(np.median(slope)) if slope else None})
    return rows


def centre_summary(vals, q=TERCILE):
    """Where each series' centre stands against zero, in units of its own far-deviation cut.

    Zero is the closed loop. A series can come back to its centre without closing: the centre
    itself can stand away from zero. The ratio is |median| over the q quantile of the deviations
    from that median, the same cut the count uses, so a ratio above one says the centre is
    further from zero than the series' own far points are from the centre. A series whose cut is
    zero (it sits on its median two thirds of the time or more) has no finite ratio: it is
    counted apart, as further from zero than its cut when its centre is not zero.
    """
    ratios, signs = [], []
    flat_away = flat_at_zero = 0
    for v in vals.values():
        if len(v) < MIN_POINTS:
            continue
        m = float(np.median(v))
        a = np.sort(np.abs(v - m))
        cut = float(a[min(len(a) - 1, max(0, int(round(q * (len(a) - 1)))))])
        if cut > 0:
            ratios.append(abs(m) / cut)
            signs.append(np.sign(m))
        elif m != 0:
            flat_away += 1
            signs.append(np.sign(m))
        else:
            flat_at_zero += 1
    if not ratios and not flat_away and not flat_at_zero:
        return None
    r = np.array(ratios)
    return {"units": len(r) + flat_away + flat_at_zero, "units_with_a_cut": len(r),
            "median_ratio": float(np.median(r)) if len(r) else None,
            "q25": float(np.quantile(r, 0.25)) if len(r) else None,
            "q75": float(np.quantile(r, 0.75)) if len(r) else None,
            "further_than_own_cut": int(np.sum(r > 1.0)) + flat_away,
            "zero_cut_centre_away_from_zero": flat_away, "zero_cut_centre_at_zero": flat_at_zero,
            "positive_centres": int(np.sum(np.array(signs) > 0))}


def step_summary(vals):
    ac = [a for a in (acf1(np.diff(v)) for v in vals.values() if len(v) > 3) if a is not None]
    lens = [len(v) for v in vals.values()]
    return {"units": len(vals), "points": int(sum(lens)),
            "median_length": float(np.median(lens)) if lens else None,
            "step_acf1_median": float(np.median(ac)) if ac else None,
            "step_acf1_negative": int(sum(a < 0 for a in ac)), "step_acf1_units": len(ac)}


# ---------------------------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------------------------

def audit(only=None) -> int:
    bad = 0
    for tag, c in carriers(only):
        print(f"\n== {tag}")
        if "error" in c:
            print(f"   NOT READ: {c['error']}")
            bad += 1
            continue
        print(f"   caliber: {c['caliber']}")
        if c.get("not_read"):
            print(f"   out of the reading: {c['not_read']}")
        for arm, units in c["arms"].items():
            lens = sorted((len(ts), str(u)) for u, (ts, _) in units.items())
            usable = sum(1 for n, _ in lens if n >= MIN_SERIES)
            zero = tot = 0
            for _ts, vs in units.values():
                tot += max(len(vs) - 1, 0)
                zero += int(np.sum(np.diff(vs) == 0))
            first = min(str(ts[0]) for ts, _ in units.values() if ts)
            last = max(str(ts[-1]) for ts, _ in units.values() if ts)
            print(f"   {arm}")
            print(f"      series {len(lens)}, of which {usable} carry at least {MIN_SERIES} points; "
                  f"points {sum(n for n, _ in lens)}; median length {np.median([n for n, _ in lens])}")
            print(f"      {first} to {last}; share of steps that are exactly zero "
                  f"{(zero / tot) if tot else float('nan'):.3f}")
            print(f"      shortest three {lens[:3]}; longest {lens[-1]}")
    return bad


def frequencies(freq):
    return ("D", "W", "M") if freq == "D" else (freq,)


def at(units, native, freq):
    return units if freq == native else thin(units, freq)


def _fmt_days(x):
    if x is None:
        return "    n/a"
    return f"{x:7.1f}d" if x < 400 else f"{x / 365.25:6.1f}y "


def describe(only=None) -> int:
    for tag, c in carriers(only):
        if "error" in c or c.get("not_read"):
            continue
        print(f"\n== {tag}   {c['caliber']}")
        for arm, units in c["arms"].items():
            sets = [("as the station read it", units, None)]
            if c.get("min_common"):
                lc, st = less_common(units, c["min_common"], c.get("group"))
                sets.append(("less the date-common term", lc, st))
            for label, us, st in sets:
                vals = values(us)
                s = step_summary(vals)
                sd = step_days(us, c["freq"])
                print(f"\n   {arm}, {label}")
                print(f"      series {s['units']}, points {s['points']}, median length {s['median_length']}, "
                      f"{sd:.2f} calendar days per step")
                if s["step_acf1_median"] is not None:
                    print(f"      lag-one autocorrelation of the steps: median {s['step_acf1_median']:+.4f}, "
                          f"negative in {s['step_acf1_negative']} of {s['step_acf1_units']}")
                if st:
                    print(f"      the common term carries {st['common_share_of_step_ss']:.4f} of the step sum of "
                          f"squares; {st['steps_without_a_common_term']} of {st['steps']} date steps had "
                          f"fewer than {c['min_common']} series and no common term")
                else:
                    cs = centre_summary(vals)
                    if cs:
                        mid = ("no series has a cut above zero" if cs["median_ratio"] is None else
                               f"median {cs['median_ratio']:.3f} [{cs['q25']:.3f}, {cs['q75']:.3f}]")
                        flat = cs["zero_cut_centre_away_from_zero"] + cs["zero_cut_centre_at_zero"]
                        print(f"      centre against zero, |median| over the far-deviation cut: {mid}; further "
                              f"from zero than the cut in {cs['further_than_own_cut']} of {cs['units']}; centre "
                              f"positive in {cs['positive_centres']}"
                              + (f"; cut of zero in {flat}, of which {cs['zero_cut_centre_away_from_zero']} with "
                                 f"a centre away from zero" if flat else ""))
                print("          lag  calendar  series   D(k)/D(1)   D(k)/(k D(1))   [q25, q75]        slope")
                for r in profile(vals):
                    sl = "      " if r["slope"] is None else f"{r['slope']:+.3f}"
                    print(f"      {r['lag']:>7}  {_fmt_days(r['lag'] * sd)}  {r['units']:>5}   {r['growth']:>9.3f}   "
                          f"{r['variance_ratio']:>13.4f}   [{r['vr_q25']:.4f}, {r['vr_q75']:.4f}]   {sl}")
    return 0


def draw(units, block, phi, rng):
    """One simulated panel on the carrier's own steps, dates drawn once for every series.

    The simulated panel has its own date axis, as long as the real one. A series has a step on
    a simulated date when it had one on the real date drawn for it, so what the series shared
    on a date they share here too, and a planted force acts along each series' own steps. Each
    series starts from zero, the level a planted force pulls toward, and the start is a point of
    the path: a series with every one of its steps drawn has as many points as the real one.
    """
    names, D = step_matrix(units)
    S = D.shape[1]
    b = min(int(block), S)
    nb = -(-S // b)
    starts = rng.integers(0, S, size=nb)
    idx = ((starts[:, None] + np.arange(b)[None, :]) % S).reshape(-1)[:S]
    out = {}
    for r, u in enumerate(names):
        g = D[r][idx]
        have = ~np.isnan(g)
        if have.sum() < 2:
            continue
        at_ = [int(i) for i in np.nonzero(have)[0]]
        path = _integrate(g[have][None, :], phi)[0]
        out[u] = ([at_[0]] + [i + 1 for i in at_], np.concatenate([[0.0], path]))
    return out


def free_positions(units, k, seed, q=TERCILE):
    """Where k panels with no restoring force land, each as gap over floor.

    Each is this panel's own steps with the dates drawn in blocks of about L ** (1/3), read by
    reading() like any panel. Their positions are what a level with no restoring force and
    these steps looks like to this instrument. The line at one is where such a panel should
    land one time in twenty; these say where it does land, and the real panel is held against
    them as well as against the line. A panel that could not be read is left out, so the list
    can be shorter than k; held() and plant_one() read nothing off a short list.
    """
    units = {u: tv for u, tv in as_units(units).items() if len(tv[1]) >= MIN_SERIES}
    if len(units) < MIN_UNITS:
        return []
    _L, p, _e, _t = blocks_for(values(units))
    b0 = max(2, int(round(p)))
    rng = np.random.default_rng(seed + 99)
    out = []
    for i in range(k):
        x = reading(draw(units, b0, 1.0, rng), q=q, seed=seed + 1000 * (i + 1), ladder=False, trend=False)
        if x["state"] != "unread":
            out.append(_pos(x))
    return out


def held(units, *, k=19, q=TERCILE, seed=SEED, ladder=True):
    """The whole reading of one panel: settled at two seeds, then held against panels with no force.

    The state on the line alone is kept beside the state, so a panel that clears the line and
    not the panels with no force is printed as exactly that. A verdict needs every one of the k
    panels with no force: if fewer could be read, the panel is unread and says how many were.
    """
    r = settled(units, q=q, seed=seed, ladder=ladder)
    if r["state"] == "unread":
        return r
    free = free_positions(units, k, seed, q)
    r.update(free_positions=free, free_requested=k, state_on_the_line=r["state"])
    if len(free) < k:
        r.update(state="unread", reason=f"only {len(free)} of the {k} panels with no force could be read")
    else:
        r["state"] = verdict(r["position"][0], r["position"][1], free)
    if r["state"] != "above" and ladder:
        r.update(rung_on_own_steps=None, rung_gaussian=None)
    return r


def plant_one(units, k, reps, seed, formal=False):
    """What this shape can tell apart, with nothing read off the real levels.

    The ideal column is the statistic's own reach: Gaussian paths of this shape with a planted
    half-life against Gaussian paths with none. Then whole simulated panels are read: k built
    from this carrier's own steps with no force, and `reps` with a planted force at two rungs.

    Two ways of reading them are kept apart. The quick one reads each planted panel once, at
    one seed, and counts it when it lands above the line and above every one of the k panels
    built from the input's steps. The formal one (formal=True) puts each planted panel through
    held(), the reading a real panel gets: two seeds with more draws until they agree, and k
    panels with no force built from that panel's own steps. Only the formal count says what a
    formal reading can see; the k panels with no force go through held() as well, which is the
    rate at which the formal reading calls a force where there is none.
    """
    units = {u: tv for u, tv in as_units(units).items() if len(tv[1]) > 1}
    lens = sorted(len(tv[1]) for tv in units.values())
    shape = {"series": len(lens), "shortest": lens[0] if lens else 0, "longest": lens[-1] if lens else 0}
    units = {u: tv for u, tv in units.items() if len(tv[1]) >= MIN_SERIES}
    vals = values(units)

    def unread(reason):
        return {"state": "unread", "units_read": len(vals), "reason": reason, **shape}
    if len(vals) < MIN_UNITS:
        return unread(f"{len(vals)} series of at least {MIN_SERIES} points, {MIN_UNITS} needed")
    walk = null(vals, "walk", NSIM, seed + 1)
    if walk["mean"] is None:
        return unread("no far point followed by a step on the Gaussian paths of this shape")
    ideal = []
    for H in HALF_LIVES:
        g = null(vals, "walk", NSIM, seed + 10 + H, phi=0.5 ** (1.0 / H))
        ideal.append({"half_life": H, "produces": g["mean"],
                      "separable": bool(g["mean"] - walk["mean"] > Z90 * walk["sd"])})
    seen = [x["half_life"] for x in ideal if x["separable"]]
    L, p, eligible, _ = blocks_for(vals)
    b0 = max(2, int(round(p)))
    free = free_positions(units, k, seed)
    if len(free) < k:
        return unread(f"only {len(free)} of the {k} panels with no force could be read")
    targets = []
    if seen:
        mid = seen[len(seen) // 2]
        targets.append(mid)
        if seen[-1] != mid:
            targets.append(seen[-1])
    planted = []
    for H in targets:
        rng = np.random.default_rng(seed + 199 + H)
        pos = []
        h_states = defaultdict(int)
        for r in range(reps):
            panel = draw(units, b0, 0.5 ** (1.0 / H), rng)
            x = reading(panel, seed=seed + 1000 * (r + 1) + H, ladder=False, trend=False)
            if x["state"] != "unread":
                pos.append(_pos(x))
            if formal:
                h_states[held(panel, k=k, seed=seed + 1000 * (r + 1) + H, ladder=False)["state"]] += 1
        row = {"half_life": H, "panels": len(pos), "over_line": int(sum(x > 1 for x in pos)),
               "over_every_free_panel": int(sum(x > 1 and x > max(free) for x in pos))}
        if formal:
            row["held"] = dict(h_states)
        planted.append(row)
    out = {"state": "read", "units_read": len(vals), **shape, "median_length": L, "eligible_blocks": eligible,
           "walk_mean": walk["mean"], "walk_sd": walk["sd"], "artefact_above_one_half": walk["mean"] - 0.5,
           "ideal": ideal, "ideal_separable": seen, "panel_block": b0,
           "free": {"panels": len(free), "min": float(min(free)), "median": float(np.median(free)),
                    "max": float(max(free)), "over_line": int(sum(x > 1 for x in free)),
                    "under_line": int(sum(x < -1 for x in free))},
           "planted": planted}
    if formal:
        rng = np.random.default_rng(seed + 99)              # the same k panels free_positions built
        size = defaultdict(int)
        for i in range(k):
            size[held(draw(units, b0, 1.0, rng), k=k, seed=seed + 1000 * (i + 1), ladder=False)["state"]] += 1
        out["free_held"] = dict(size)
    return out


def _states(d):
    return ", ".join(f"{k} {d[k]}" for k in ("above", "inside", "below", "marginal", "unread") if d.get(k))


def plant(only=None, k=19, reps=20, big_k=5, big_reps=2, big=100_000, freqs=None, formal=False) -> int:
    """Per carrier, arm, span and frequency. A shape past `big` points gets fewer panels: at
    that size they check that the code runs and where the no-force panels land, and the ideal
    column carries the reach. Twenty planted panels per rung on the small shapes, because the
    rungs near the edge of the reach are seen in some panels and not in others, and five gave
    four of five on one run and none of five on the next. With formal every panel also goes
    through held(), the reading a real panel gets."""
    for tag, c in carriers(only):
        if "error" in c or c.get("not_read"):
            continue
        print(f"\n== {tag}", flush=True)
        for arm, units in c["arms"].items():
            spans = [("whole window", None, None)] + list(c.get("segments", []))
            for seg, lo, hi in spans:
                us = units if (lo is None and hi is None) else window(units, lo, hi)
                for f in frequencies(c["freq"]):
                    if freqs and f not in freqs:
                        continue
                    t0 = time.perf_counter()
                    ut = at(us, c["freq"], f)
                    small = sum(len(v) for v in values(ut).values()) <= big
                    r = plant_one(ut, k if small else big_k, reps if small else big_reps, SEED, formal=formal)
                    head = f"   {arm} | {seg} | {f}"
                    cover = f"series {r['series']}, lengths {r['shortest']} to {r['longest']}"
                    if r["state"] == "unread":
                        print(f"{head}: not readable, {cover}: {r['reason']}", flush=True)
                        continue
                    sd = step_days(ut, f)
                    ideal = " ".join(f"{x['half_life']}{'+' if x['separable'] else '-'}" for x in r["ideal"])
                    reach = (f"up to {_fmt_days(max(r['ideal_separable']) * sd).strip()}"
                             if r["ideal_separable"] else "nothing")
                    fr = r["free"]
                    pl = "; ".join(f"half-life {x['half_life']}: over the line {x['over_line']}, over every "
                                   f"no-force panel {x['over_every_free_panel']}, of {x['panels']}"
                                   + (f"; whole reading: {_states(x['held'])}" if "held" in x else "")
                                   for x in r["planted"]) or "nothing planted: no rung of the ideal ladder is readable"
                    print(f"{head}: {cover}, read {r['units_read']}, median length {r['median_length']:.0f}, "
                          f"blocks {r['eligible_blocks']}, walk reads {r['walk_mean']:.4f}")
                    print(f"      ideal reach in steps [{ideal}], that is {reach}")
                    print(f"      no force, {fr['panels']} panels: positions {fr['min']:+.2f} / {fr['median']:+.2f} / "
                          f"{fr['max']:+.2f} (min / median / max), over the line {fr['over_line']}, under "
                          f"{fr['under_line']}"
                          + (f"; whole reading: {_states(r['free_held'])}" if "free_held" in r else "")
                          + f" | {pl}   ({time.perf_counter() - t0:.1f}s)", flush=True)
    return 0


# ---------------------------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------------------------

def selftest() -> int:
    rf = station("b52_restoring_force")
    fails = []

    def check(name, ok, detail=""):
        print(f"{'ok  ' if ok else 'FAIL'} {name}{(': ' + detail) if detail else ''}")
        if not ok:
            fails.append(name)

    # 1. the reference reproduces its own record, to the last digit a float sum allows
    rec = json.loads(rf.OUT.read_text(encoding="utf-8"))
    cells = json.loads(rf.SRC.read_text(encoding="utf-8"))["cells"]
    raw = defaultdict(list)
    for c in cells:
        if c.get(rf.BASE) is not None:
            raw[c["geo"]].append((c["semester"], float(c[rf.BASE])))
    lists = {k: [v for _, v in sorted(p)] for k, p in raw.items()}
    ref = rf.reversion(lists)
    b8 = rf.block_bootstrap_null(lists, 8, rf.NSIM, rf.SEED + 3000 + 8)
    check("reference reproduces the record's reading",
          ref["back"] == rec["reading"]["back"] and ref["away"] == rec["reading"]["away"],
          f"{ref['back']} back, {ref['away']} away")
    check("reference reproduces the record's strict null",
          abs(b8["mean"] - rec["block_bootstrap_nulls"][-1]["mean"]) < 1e-12,
          f"{b8['mean']:.12f} against {rec['block_bootstrap_nulls'][-1]['mean']:.12f}")

    # 2. the array counts are the reference counts, exactly, on the real panel and on awkward ones
    vals = {k: np.array(v) for k, v in lists.items()}
    mine = observed(vals)
    check("array counts equal the reference on the panel",
          (mine["back"], mine["away"]) == (ref["back"], ref["away"])
          and all(mine["per_unit"][k].get("back", 0) == ref["per_unit"][k].get("back", 0)
                  and mine["per_unit"][k]["used"] == ref["per_unit"][k]["used"] for k in lists),
          f"{mine['back']} back, {mine['away']} away")
    rng = np.random.default_rng(7)
    same = other_q_differs = 0
    for _ in range(60):
        panel = {}
        for u in range(12):
            n = int(rng.integers(1, 61))
            x = np.cumsum(rng.normal(size=n))
            panel[u] = np.round(x, int(rng.integers(0, 3)))     # ties and zero steps on purpose
        r0 = rf.reversion({u: list(map(float, v)) for u, v in panel.items()})
        m0 = observed(panel)
        same += (m0["back"], m0["away"]) == (r0["back"], r0["away"])
        m1 = observed(panel, q=0.5)
        other_q_differs += (m1["back"], m1["away"]) != (r0["back"], r0["away"])
    check("array counts equal the reference on 60 panels with ties, zero steps and short series",
          same == 60, f"{same} of 60")
    check("a different quantile is seen as different", other_q_differs > 50, f"{other_q_differs} of 60")
    twice = observed({k: v * 2.0 for k, v in vals.items()})
    check("the count does not move when a series is rescaled",
          (twice["back"], twice["away"]) == (mine["back"], mine["away"]))

    # 3. series by series, the array nulls are the reference nulls, within what two sets of
    #    2000 draws can differ by
    N = 2000
    shape = {k: (len(v), rf.sd([v[i + 1] - v[i] for i in range(len(v) - 1)])) for k, v in lists.items()}
    pairs = [("gaussian walk", rf.null_band(shape, 1.0, N, 11), null(vals, "walk", N, 11)),
             ("shuffled steps", rf.shuffled_diff_null(lists, N, 12), null(vals, "shuffle", N, 12)),
             ("gaussian, half-life 4", rf.null_band(shape, 0.5 ** 0.25, N, 13),
              null(vals, "walk", N, 13, phi=0.5 ** 0.25)),
             ("block 8, half-life 4", rf.block_bootstrap_null(lists, 8, N, 14, phi=0.5 ** 0.25),
              null(vals, "block", N, 14, block=8, phi=0.5 ** 0.25))]
    for b in (2, 3, 4, 6, 8):
        pairs.append((f"block {b}", rf.block_bootstrap_null(lists, b, N, 20 + b),
                      null(vals, "block", N, 20 + b, block=b)))
    for name, a, m in pairs:
        tol = 3.0 * np.sqrt(a["sd"] ** 2 / a["sims"] + m["sd"] ** 2 / m["sims"])
        check(f"null agrees with the reference: {name}", abs(a["mean"] - m["mean"]) <= tol,
              f"{a['mean']:.4f} against {m['mean']:.4f}, allowed {tol:.4f}")
    wrong = null(vals, "block", N, 26, block=6)
    right = rf.block_bootstrap_null(lists, 4, N, 24)
    tol = 3.0 * np.sqrt(wrong["sd"] ** 2 / N + right["sd"] ** 2 / N)
    check("a null at the wrong block length is seen as wrong", abs(wrong["mean"] - right["mean"]) > tol,
          f"block 6 {wrong['mean']:.4f} against block 4 {right['mean']:.4f}, allowed {tol:.4f}")

    # 4. the recursion
    e = rng.normal(size=(3, 50))
    loop = np.zeros_like(e)
    x = np.zeros(3)
    for t in range(50):
        x = 0.8 * x + e[:, t]
        loop[:, t] = x
    check("the recursion is the recursion", float(np.max(np.abs(_integrate(e, 0.8) - loop))) < 1e-12
          and np.array_equal(_integrate(e, 1.0), np.cumsum(e, axis=1)))

    # 5. the block ladder at the reference panel's length is the reference ladder
    L, p, eligible, trend = blocks_for(vals)
    check("block ladder at this length is 2, 3, 4, 6, 8 and then 12, 16",
          eligible == [2, 3, 4, 6, 8] and trend == [12, 16], f"L {L:.0f}: {eligible} then {trend}")

    # 6. thinning keeps the last observation of each week and month, and only observed ones
    days = [dt.date(2025, 1, 1) + dt.timedelta(days=i) for i in range(70)]
    days = [d for d in days if d.weekday() < 5 and d != dt.date(2025, 1, 31)]
    u = {"a": (days, np.arange(len(days), dtype=float))}
    wk, mo = thin(u, "W")["a"], thin(u, "M")["a"]
    check("monthly thinning ends January on the 30th when the 31st is missing",
          mo[0][0] == dt.date(2025, 1, 30) and mo[0][1] == dt.date(2025, 2, 28) and len(mo[0]) == 3,
          str([str(d) for d in mo[0]]))
    check("weekly thinning keeps Fridays, or the last day there is",
          all(d.weekday() == 4 or d in (dt.date(2025, 1, 30), days[-1]) for d in wk[0])
          and wk[0][0] == dt.date(2025, 1, 3), f"{len(wk[0])} weeks")

    # 7. the date-common term: planted, with a late joiner and a gap
    T = 40
    C = np.cumsum(rng.normal(size=T))
    times = list(range(T))
    panel = {}
    for i in range(6):
        keep = [t for t in times if not (i == 1 and t < 10) and not (i == 2 and 15 <= t < 22)]
        panel[i] = (keep, 3.0 * i + C[keep])
    lc, st = less_common(panel, 3)
    flat = max(float(np.ptp(v)) for _t, v in lc.values())
    check("a term every series shares is removed whole, through a late start and a gap",
          flat < 1e-9 and abs(st["common_share_of_step_ss"] - 1.0) < 1e-9, f"largest range left {flat:.2e}")
    idio = {i: (ts, vs + np.cumsum(rng.normal(size=len(ts)))) for i, (ts, vs) in panel.items()}
    lc2, _ = less_common(idio, 3)
    M = np.full((6, T), np.nan)
    for i, (ts, vs) in lc2.items():
        M[i, ts] = vs
    Dm = M[:, 1:] - M[:, :-1]
    check("after removal the mean step across series is zero on every date",
          float(np.nanmax(np.abs(np.nanmean(Dm, axis=0)))) < 1e-9)
    lc3, st3 = less_common(panel, 7)
    check("with too few series on every date nothing is removed, and that is counted",
          st3["steps_without_a_common_term"] == st3["steps"]
          and all(np.array_equal(lc3[i][1], panel[i][1]) for i in panel))

    # 8. the profile on shapes whose answer is arithmetic
    ramp = profile({"r": np.arange(200, dtype=float)}, lags=(1, 2, 4, 8))
    alt = profile({"a": np.array([(-1.0) ** i for i in range(200)])}, lags=(1, 2, 3))
    check("a ramp grows like k squared and reads slope two",
          [round(r["growth"], 9) for r in ramp] == [1.0, 4.0, 16.0, 64.0] and abs(ramp[-1]["slope"] - 2) < 1e-9)
    check("an alternating series is back where it was at even lags",
          [round(r["growth"], 9) for r in alt] == [1.0, 0.0, 1.0])
    walk_p = profile({i: np.cumsum(rng.normal(size=4000)) for i in range(40)}, lags=(1, 8, 64))
    noise_p = profile({i: rng.normal(size=4000) for i in range(40)}, lags=(1, 8, 64))
    check("a walk keeps a variance ratio near one and white noise loses it like 1/k",
          abs(walk_p[-1]["variance_ratio"] - 1) < 0.15 and abs(noise_p[-1]["variance_ratio"] - 1 / 64) < 0.005,
          f"walk {walk_p[-1]['variance_ratio']:.3f}, noise {noise_p[-1]['variance_ratio']:.4f}")

    base = np.arange(-3.0, 4.0)
    cs = centre_summary({"at zero": base, "up": base + 6.0, "down": base - 6.0})
    check("a centre at zero reads zero, and one six away with a cut of two reads three, whatever its sign",
          cs["units"] == 3 and cs["median_ratio"] == 3.0 and cs["q25"] == 1.5
          and cs["further_than_own_cut"] == 2 and cs["positive_centres"] == 1, str(cs))

    # 9. drawing dates for the whole panel
    def each_alone(panel, kind, n, seed, block=None):
        """The same drawing of dates, applied to every series as a panel of its own, then pooled."""
        back, tot = np.zeros(n), np.zeros(n)
        for i, (u, tv) in enumerate(sorted(as_units(panel).items(), key=lambda kv: str(kv[0]))):
            b, t = null({u: tv[1]}, kind, n, seed + 100 * i, block=block, D=step_matrix({u: tv})[1], raw=True)
            back += b
            tot += t
        return summarise(back, tot)

    g = np.random.default_rng(21)
    indep = {i: np.cumsum(g.normal(size=120)) for i in range(9)}
    Di = step_matrix(as_units(indep))[1]
    a = each_alone(indep, "block", N, 31, block=5)
    s = null(indep, "block", N, 32, block=5, D=Di)
    tol = 3.0 * np.sqrt(a["sd"] ** 2 / N + s["sd"] ** 2 / N)
    check("on independent series, one draw of dates for the panel and one per series give the same null",
          abs(a["mean"] - s["mean"]) <= tol and 0.8 < s["sd"] / a["sd"] < 1.25,
          f"mean {a['mean']:.4f} against {s['mean']:.4f}, spread {a['sd']:.4f} against {s['sd']:.4f}")
    one = np.cumsum(g.normal(size=120))
    copies = {i: one + 0.0 for i in range(9)}
    Dc = step_matrix(as_units(copies))[1]
    a = each_alone(copies, "block", N, 33, block=5)
    s = null(copies, "block", N, 34, block=5, D=Dc)
    check("on nine copies of one series, one draw of dates for the panel keeps the spread of one series",
          s["sd"] / a["sd"] > 0.7 * 3.0,
          f"spread {s['sd']:.4f} with one draw for the panel against {a['sd']:.4f} with one per copy; "
          f"nine independent series would give a ratio of one, nine copies give three")
    half_t = list(range(60, 121))
    ragged = {"full": (list(range(121)), np.cumsum(g.normal(size=121))),
              "late": (half_t, np.cumsum(g.normal(size=61))),
              "holes": ([t for t in range(121) if t % 7], np.cumsum(g.normal(size=len([t for t in range(121) if t % 7]))))}
    names, Dr = step_matrix(ragged)
    late = Dr[names.index("late")]
    check("the step matrix keeps every step of every series, on the date the step ends",
          all(int(np.sum(~np.isnan(Dr[r]))) == len(ragged[u][1]) - 1
              and np.allclose(Dr[r][~np.isnan(Dr[r])], np.diff(ragged[u][1])) for r, u in enumerate(names))
          and int(np.nonzero(~np.isnan(late))[0][0]) == 60,
          "a series that starts on date 60 has its first step on date 61, the column after 60 others")
    for kind, blk, sd0 in (("shuffle", None, 41), ("block", 4, 43)):
        a = each_alone(ragged, kind, N, sd0, block=blk)
        s = null(values(ragged), kind, N, sd0 + 1, block=blk, D=Dr)
        tol = 3.0 * np.sqrt(a["sd"] ** 2 / N + s["sd"] ** 2 / N)
        check(f"a late start and holes do not move the {kind} null when dates are drawn",
              s["mean"] is not None and abs(a["mean"] - s["mean"]) <= tol
              and (s["padded_share"] == 0.0 if kind == "shuffle" else s["padded_share"] < 0.02),
              f"{a['mean']:.4f} one draw per series against {s['mean']:.4f}, allowed {tol:.4f}; "
              f"padded {s['padded_share']:.4f}")
    jumps = np.random.default_rng(77)
    heavy = {i: np.cumsum(jumps.normal(size=2000) * np.where(jumps.random(2000) < 0.01, 7.0, 1.0)) for i in range(12)}
    Dh = step_matrix(as_units(heavy))[1]
    perm_h = null(heavy, "shuffle", N, 61)
    boot_h = null(heavy, "block", N, 62, block=1)
    date_h = null(heavy, "shuffle", N, 63, D=Dh)
    dateb_h = null(heavy, "block", N, 64, block=1, D=Dh)
    tol = 3.0 * np.sqrt(perm_h["sd"] ** 2 / N + boot_h["sd"] ** 2 / N)
    check("on heavy-tailed steps, resampling with replacement reads lower than the same steps reordered",
          perm_h["mean"] - boot_h["mean"] > tol,
          f"reordered {perm_h['mean']:.4f}, with replacement {boot_h['mean']:.4f}, allowed {tol:.4f}: "
          "the fault the panels with no force are there to measure")
    check("and drawing dates does the same as drawing each series, both ways",
          abs(date_h["mean"] - perm_h["mean"]) <= tol and abs(dateb_h["mean"] - boot_h["mean"]) <= tol,
          f"reordered {perm_h['mean']:.4f} and {date_h['mean']:.4f}; with replacement {boot_h['mean']:.4f} "
          f"and {dateb_h['mean']:.4f}")
    perm = g.permuted(np.tile(np.arange(Dr.shape[1]), (25, 1)), axis=1)
    exact = True
    for r, u in enumerate(names):
        got, empty = take(Dr[r], perm)
        own = np.sort(np.diff(ragged[u][1]))
        exact &= empty == 0 and got.shape == (25, len(own)) and all(np.array_equal(np.sort(x), own) for x in got)
    check("when every date is drawn once, every series gets exactly its own steps, each once", bool(exact))
    in_order = np.arange(Dr.shape[1])[None, :]
    nowhere = np.zeros((4, Dr.shape[1]), dtype=int)          # date 0 only, where "late" has no step
    got, empty = take(late, nowhere)
    check("dates drawn in their own order give a series its own steps in their own order",
          all(np.array_equal(take(Dr[r], in_order)[0][0], np.diff(ragged[u][1])) for r, u in enumerate(names)))
    check("a series with no step on any date drawn gets zero steps, and every one is counted as empty",
          empty == 4 * 60 and got.shape == (4, 60) and not got.any(), f"{empty} empty slots of {got.size}")
    noisy = {i: np.cumsum(g.normal(size=150)) + 3.0 * g.normal(size=150) for i in range(12)}
    Dn = step_matrix(as_units(noisy))[1]
    a3 = each_alone(noisy, "block", N, 51, block=3)
    s3 = null(noisy, "block", N, 52, block=3, D=Dn)
    s5 = null(noisy, "block", N, 53, block=5, D=Dn)
    tol = 3.0 * np.sqrt(a3["sd"] ** 2 / N + s3["sd"] ** 2 / N)
    check("on steps that carry their own order, blocks of 3 for the panel read what blocks of 3 per series do",
          abs(a3["mean"] - s3["mean"]) <= tol, f"{a3['mean']:.4f} against {s3['mean']:.4f}, allowed {tol:.4f}")
    r3 = null(noisy, "block", N, 54, block=3)
    check("and blocks of 3 drawn on dates read what the reference's blocks of 3 read",
          abs(r3["mean"] - s3["mean"]) <= tol, f"{r3['mean']:.4f} against {s3['mean']:.4f}, allowed {tol:.4f}")
    check("and blocks of 5 are seen as a different null", abs(a3["mean"] - s5["mean"]) > tol,
          f"{a3['mean']:.4f} against {s5['mean']:.4f}, allowed {tol:.4f}")
    fake = draw(as_units(copies), 5, 1.0, np.random.default_rng(3))
    check("a panel drawn from nine copies is nine copies",
          len(fake) == 9 and all(np.array_equal(fake[0][1], fake[i][1]) for i in fake))
    loose = draw(ragged, 5, 1.0, np.random.default_rng(4))
    pulled = draw(ragged, 5, 0.5, np.random.default_rng(4))
    check("a planted force acts along each series' own drawn steps",
          all(np.allclose(pulled[u][1][1:] - 0.5 * pulled[u][1][:-1], np.diff(loose[u][1]))
              and loose[u][0] == pulled[u][0] for u in loose) and len(loose) == 3)

    # 10. when two readings count as one measurement
    check("two readings agree only on one side and closer together than to the line",
          agree(1.4, 1.5) == "above" and agree(0.2, -0.1) == "inside" and agree(-1.8, -2.0) == "below"
          and agree(1.05, 0.95) is None and agree(1.02, 1.08) is None
          and agree_rung(1.5, 1.6) == "yes" and agree_rung(0.2, 0.4) == "no" and agree_rung(0.95, 1.1) == "marginal"
          and agree_rung(1.02, 1.3) == "marginal" and agree_rung(0.99, 0.7) == "marginal")
    check("a reading is above only over the line, measured, and over every panel that had no force",
          verdict(1.5, 1.6, [0.2, 1.2]) == "above" and verdict(1.5, 1.6, [0.2, 1.55]) == "inside"
          and verdict(1.5, 1.6, []) == "above" and verdict(1.05, 0.95, [0.0]) == "marginal"
          and verdict(-2.0, -2.2, [-1.5, 0.3]) == "below" and verdict(-2.0, -2.2, [-2.1, 0.0]) == "inside"
          and verdict(0.2, 0.3, [-5.0, 5.0]) == "inside")
    walks_above = noise_above = consistent = 0
    for i in range(20):
        g = np.random.default_rng(3000 + i)
        w = held({u: np.cumsum(g.normal(size=60)) for u in range(10)}, k=9, seed=i, ladder=False)
        n = held({u: g.normal(size=60) for u in range(10)}, k=9, seed=i, ladder=False)
        walks_above += w["state"] == "above"
        noise_above += n["state"] == "above"
        consistent += all(x["state"] == verdict(x["position"][0], x["position"][1], x["free_positions"])
                          and len(x["free_positions"]) == 9 for x in (w, n))
    check("the whole reading: 20 panels with no force seldom read above, 20 pulled back nearly always do",
          walks_above <= 3 and noise_above >= 17 and consistent == 20,
          f"{walks_above} of 20 with no force, {noise_above} of 20 pulled back")
    real_free = globals()["free_positions"]
    try:
        globals()["free_positions"] = lambda units, k, seed, q=TERCILE: [1e9]
        g = np.random.default_rng(32)
        blocked = held({u: g.normal(size=60) for u in range(10)}, k=1, ladder=False)
    finally:
        globals()["free_positions"] = real_free
    check("a panel that clears the line and not the panels with no force is inside, and says so",
          blocked["state"] == "inside" and blocked["state_on_the_line"] == "above",
          f"{blocked['state_on_the_line']} on the line, {blocked['state']} once held")
    g = np.random.default_rng(31)
    walks = {i: np.cumsum(g.normal(size=90)) for i in range(8)}
    fp = free_positions(walks, 6, 5)
    check("panels with no force are built, read, and land near the line or under it",
          len(fp) == 6 and all(np.isfinite(x) for x in fp) and max(fp) < 3.0 and min(fp) > -3.0,
          "positions " + " ".join(f"{x:+.2f}" for x in fp))

    def scripted(positions):
        """A stand-in for reading(): the position it reports is scripted per number of draws."""
        def f(units, *, nsim, seed, **_):
            p = positions[nsim][0 if seed == SEED else 1]
            return {"state": side(p), "gap": p, "floor": 1.0, "strict_null": "scripted", "strict_mean": 0.0}
        return f
    three = {i: np.arange(10.0) for i in range(3)}
    more = settled(three, ladder=False, draws=(10, 40, 160), read=scripted({10: (1.05, 0.95), 40: (1.3, 1.4)}))
    stuck = settled(three, ladder=False, draws=(10, 40), read=scripted({10: (1.05, 0.95), 40: (1.1, 0.9)}))
    capped = settled(three, ladder=False, draws=(10, 40), budget=30 * 39,
                     read=scripted({10: (1.05, 0.95), 40: (1.3, 1.4)}))
    check("two seeds that disagree buy more draws, stop when they agree, and stop at the budget",
          (more["draws"], more["state"]) == (40, "above") and (stuck["draws"], stuck["state"]) == (40, "marginal")
          and (capped["draws"], capped["state"]) == (10, "marginal"),
          f"{more['draws']} {more['state']}; {stuck['draws']} {stuck['state']}; {capped['draws']} {capped['state']}")

    # 11. the reading on panels whose answer is known
    r = reading(vals, sync=False)
    check("the reading's own numbers are consistent with each other",
          r["strict_mean"] == max(v["mean"] for v in r["nulls"].values())
          and abs(r["floor"] - 1.6448536269514722 * r["nulls"][r["strict_null"]]["sd"]) < 1e-15
          and r["state"] == ("above" if r["gap"] > r["floor"] else "below" if r["gap"] < -r["floor"] else "inside")
          and all(x["separable"] == (x["produces"] - r["strict_mean"] > r["floor"])
                  for x in r["ladder_on_own_steps"]))
    rs = settled(vals, sync=False)
    flag = {x["half_life"]: x["separable"] for x in rs["ladder_on_own_steps"]}
    check("on the reference panel, series by series, the settled reading lands where the record does",
          rs["state"] == "above" and rs["strict_null"] == "block_8"
          and abs(rs["strict_mean"] - rec["block_bootstrap_nulls"][-1]["mean"]) < 0.01
          and all(flag[h] != "no" for h in rec["half_lives_separable"])
          and all(flag[h] != "yes" for h in rec["half_lives_not_separable"])
          and flag[1] == "yes" and flag[2] == "yes" and flag[64] == "no",
          f"{rs['state']} at {rs['draws']} draws, strict {rs['strict_null']} {rs['strict_mean']:.4f} "
          f"(record {rec['block_bootstrap_nulls'][-1]['mean']:.4f}); rungs {flag}")
    walks = noises = 0
    for i in range(40):
        g = np.random.default_rng(1000 + i)
        w = reading({u: np.cumsum(g.normal(size=60)) for u in range(10)}, nsim=100, seed=i, ladder=False, trend=False)
        s = reading({u: g.normal(size=60) for u in range(10)}, nsim=100, seed=i, ladder=False, trend=False)
        walks += w["state"] == "above"
        noises += s["state"] == "above"
    check("40 panels with no restoring force: few read above", walks <= 8, f"{walks} of 40")
    check("40 panels pulled back at every step: nearly all read above", noises >= 32, f"{noises} of 40")
    shared_sync = shared_alone = 0
    for i in range(40):
        g = np.random.default_rng(2000 + i)
        common = np.cumsum(g.normal(size=60))
        pan = {u: common + 0.2 * np.cumsum(g.normal(size=60)) for u in range(10)}
        shared_sync += reading(pan, nsim=100, seed=i, ladder=False, trend=False)["state"] == "above"
        shared_alone += reading(pan, sync=False, nsim=100, seed=i, ladder=False, trend=False)["state"] == "above"
    check("40 panels of ten series sharing one walk: drawing dates keeps the false readings few",
          shared_sync <= 8, f"{shared_sync} of 40 drawing dates")
    check("the same 40 panels read series by series give more false readings, which is the fault planted",
          shared_alone > shared_sync, f"{shared_alone} of 40 series by series against {shared_sync}")
    g = np.random.default_rng(5)
    ar = {u: _integrate(g.normal(size=(1, 400)), 0.5 ** (1.0 / 4))[0] for u in range(20)}
    ra = settled(ar)
    check("a planted half-life of 4 is read above and placed next to 4 on the Gaussian ladder",
          ra["state"] == "above" and ra["rung_gaussian"] in ({"between": [2, 4]}, {"between": [4, 8]}),
          f"{ra['state']}, {ra['rung_gaussian']}")
    half = null(vals, "walk", 400, 3)
    check("a walk held against one half would be called a restoring force",
          half["mean"] - 0.5 > Z90 * half["sd"],
          f"a walk of this shape reads {half['mean']:.4f}, {(half['mean'] - 0.5) / half['sd']:.1f} of its own sd "
          "above one half")
    check("too few series is unread and carries no verdict",
          reading({0: np.arange(50.0), 1: np.arange(50.0)})["state"] == "unread"
          and reading({i: np.arange(3.0) for i in range(9)})["state"] == "unread")

    # 12. what the audit of 2026-10-06 planted
    four = reading({i: np.array([0.0, 1.0, -1.0, 0.0]) for i in range(3)})
    check("series of four points are not read, and the reading says the length it needs",
          four["state"] == "unread" and str(MIN_SERIES) in four["reason"] and four["units_too_short"] == 3,
          four.get("reason", ""))
    g = np.random.default_rng(91)
    mixed = {i: np.cumsum(g.normal(size=40)) for i in range(6)}
    with_short = dict(mixed, s1=np.array([0.0, 1.0, -1.0, 0.0]), s2=np.array([3.0, 1.0, 2.0, 5.0]))
    ra, rb = reading(mixed, nsim=50, ladder=False, trend=False), reading(with_short, nsim=50, ladder=False, trend=False)
    check("a series too short to be rebuilt enters neither the count nor the null",
          (ra["back"], ra["away"], ra["strict_mean"]) == (rb["back"], rb["away"], rb["strict_mean"])
          and rb["units_too_short"] == 2 and rb["units_read"] == 6)
    drawn = draw(as_units(mixed), 3, 1.0, np.random.default_rng(5))
    check("a drawn panel starts each series at zero and has as many points as the real one",
          all(len(drawn[u][1]) == len(mixed[u]) and drawn[u][1][0] == 0.0 and drawn[u][0][0] == 0
              and len(set(drawn[u][0])) == len(drawn[u][0]) for u in drawn) and len(drawn) == 6)
    try:
        globals()["free_positions"] = lambda units, k, seed, q=TERCILE: []
        g = np.random.default_rng(32)
        bare = held({u: g.normal(size=60) for u in range(10)}, k=5, ladder=False)
    finally:
        globals()["free_positions"] = real_free
    check("a panel whose panels with no force could not be read carries no verdict",
          bare["state"] == "unread" and bare["state_on_the_line"] == "above" and "0 of the 5" in bare["reason"],
          f"{bare['state_on_the_line']} on the line, {bare['state']} once held")
    five = held({i: np.array([-9.0, -10.0, 0.0, 1.0, 2.0]) for i in range(3)}, k=19, ladder=False)
    check("three series of five points: a verdict only with all nineteen panels read, otherwise unread",
          five["state"] == "unread" or len(five.get("free_positions", [])) == 19,
          f"{five['state']}: {five.get('reason', '')}")
    flat = centre_summary({i: np.full(8, 10.0) for i in range(3)})
    check("three series standing at ten are three centres away from zero, not nothing",
          flat is not None and flat["units"] == 3 and flat["further_than_own_cut"] == 3
          and flat["zero_cut_centre_away_from_zero"] == 3 and flat["positive_centres"] == 3
          and flat["median_ratio"] is None, str(flat))
    still = centre_summary({"a": np.zeros(8), "b": base + 6.0})
    check("a series standing at zero is counted at zero, beside one with a cut",
          still["units"] == 2 and still["zero_cut_centre_at_zero"] == 1 and still["further_than_own_cut"] == 1
          and still["median_ratio"] == 3.0, str(still))
    g = np.random.default_rng(17)
    strong = {u: _integrate(g.normal(size=(1, 80)), 0.5)[0] for u in range(8)}
    real_held = globals()["held"]
    try:
        globals()["held"] = lambda units, **kw: {"state": "inside"}
        deaf = plant_one(strong, 5, 4, SEED, formal=True)
    finally:
        globals()["held"] = real_held
    check("the formal count of a planted force is what held() says, not what one seed says",
          deaf["state"] == "read" and deaf["planted"] and all(x["held"] == {"inside": 4} for x in deaf["planted"])
          and any(x["over_every_free_panel"] > 0 for x in deaf["planted"]) and deaf["free_held"] == {"inside": 5},
          str([(x["half_life"], x["over_every_free_panel"], x["held"]) for x in deaf.get("planted", [])]))
    gr = dict(carriers({"B97"}))["B97"]["arms"]
    greece = [a for a in gr if ", GR " in a][0]
    check("Greece stops being a control before the month it cut its own edge",
          max(ts[-1] for ts, _ in gr[greece].values()) == B97_CONTROL_ENDS["GR"]
          and all(max(ts[-1] for ts, _ in gr[a].values()) > "2015-06" for a in gr if a != greece),
          f"last month {max(ts[-1] for ts, _ in gr[greece].values())}")

    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--audit", action="store_true", help="count what is on disk; compare nothing")
    ap.add_argument("--selftest", action="store_true", help="the instrument against known answers")
    ap.add_argument("--describe", action="store_true", help="step autocorrelation and growth of k-step differences")
    ap.add_argument("--plant", action="store_true", help="what each carrier's shape can tell apart")
    ap.add_argument("--only", nargs="*", help="carrier tags, for example B9 B21")
    ap.add_argument("--reps", type=int, default=20, help="simulated panels per planted case")
    ap.add_argument("--freqs", nargs="*", help="frequencies to plant at, for example W M")
    ap.add_argument("--formal", action="store_true",
                    help="with --plant: put every simulated panel through the whole reading as well")
    a = ap.parse_args()
    only = set(a.only) if a.only else None
    if a.selftest:
        return selftest()
    if a.audit:
        return 1 if audit(only) else 0
    if a.describe:
        return describe(only)
    if a.plant:
        return plant(only, reps=a.reps, freqs=set(a.freqs) if a.freqs else None, formal=a.formal)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
