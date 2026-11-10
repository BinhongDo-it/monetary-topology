"""B142, the readings: every carrier cell read once, kept, and put together into the record.

    python experiments/b142_reading.py --work --only B9 B5 B97 B52
    python experiments/b142_reading.py --work --only B21 B3 --run-id r1      (several at once)
    python experiments/b142_reading.py --status
    python experiments/b142_reading.py --run
    python experiments/b142_reading.py --selftest

The instrument is b142_relaxation.py and nothing in it is changed here. This file decides which
cells are read, reads each one, keeps what it read, and builds the record from what was kept.

A cell is one carrier, one arm, one span, one frequency, and either the series as the station
read them or the same series less the step all of them share on a date. A cell gets up to four
things, each kept as its own file under data/cache/b142/:

    read    the centre against zero, the growth of the k-step difference, and the whole
            reading (two seeds, held against panels built from its own steps with no force)
    knob    the position on the line with the far-point quantile at one half and at four fifths
    quick   what the shape can tell apart, each planted panel read once at one seed
    cal     the same with every planted panel put through the whole reading, in parts

A file is written whole and then moved into place. A file that does not parse, has no completion
mark, or was made from other data or other settings is not read: the cell is run again. A
calibration part keeps every panel it has finished, and a restart draws the same panels in the
same order and reads only the ones it has not kept.

Several workers can run at once. Each takes a job by creating a claim file that carries the run
id it was started with, and passes over jobs claimed under the same id; a new run id ignores the
claims of an old one, so nothing has to be removed after a worker is stopped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

EXP = Path(__file__).resolve().parent
if str(EXP) not in sys.path:
    sys.path.insert(0, str(EXP))
import b142_relaxation as m  # noqa: E402

CACHE = m.ROOT / "data" / "cache" / "b142"
RECORD = m.ROOT / "results" / "b142_relaxation.json"
VERSION = 1
BIG = 100_000            # past this many points a cell gets fewer panels with no force
K_SMALL, K_BIG, K_B3_DAILY = 19, 5, 12
REPS_SMALL, REPS_BIG = 20, 2
KNOB_Q = (0.5, 0.8)
DAY = dt.timedelta(days=1)

# Stock Connect. The dates are the opening dates in the exchanges' own announcements; the rule
# that A+H shares come in as a class of their own, on the exchange where the A share is listed,
# is what turns the A share's exchange suffix into each pair's date. No list of eligible stocks
# is read.
CONNECT_OPEN = {"SS": dt.date(2014, 11, 17), "SZ": dt.date(2016, 12, 5)}
STAR_OPEN = dt.date(2021, 2, 1)
ENTRY_LAGS = (0, 10, 30)
# Steps of the Shanghai link after its opening, for the description only: the aggregate quota
# went on 2016-08-16, Shenzhen opened on 2016-12-05, the daily quota was quadrupled on 2018-05-01.
QUOTA_STEPS = (dt.date(2014, 11, 17), dt.date(2016, 8, 16), dt.date(2016, 12, 5), dt.date(2018, 5, 1))

B21_ARM = "A over H, log premium"
CAL_TIER1 = (("B21", B21_ARM, "whole window", "M"), ("B21", B21_ARM, "before own Connect opening", "M"),
             ("B21", B21_ARM, "from own Connect opening", "M"), ("B21", B21_ARM, "before own Connect opening", "W"),
             ("B3", "g10", "whole window", "M"), ("B3", "eme", "whole window", "M"))
CAL_TIER2 = tuple(("B21", B21_ARM, f"{ex}, 2014-11-17 to 2016-12-02", f) for ex in ("SH main", "SZ") for f in "MWD")


# ---------------------------------------------------------------------------------------------
# the cells
# ---------------------------------------------------------------------------------------------

def board(u: str) -> str:
    code, ex = u.split(".")
    if ex == "SS":
        return "STAR" if code.startswith("688") else "SH main"
    return "SZ"


def conversion(u: str) -> dt.date:
    b = board(u)
    return STAR_OPEN if b == "STAR" else CONNECT_OPEN["SS" if b == "SH main" else "SZ"]


def drop_first(units, n):
    return {u: (ts[n:], vs[n:]) for u, (ts, vs) in units.items() if len(ts) > n} if n else dict(units)


def connect_split(units, lag=0):
    """Each pair cut at its own date. Returns (before, after, counts).

    before: up to the day before the pair's exchange opened; STAR pairs have no before, since
    the rule does not settle whether their H leg was in before 2021-02-01, and what they had
    before that date goes into neither cell and is counted. after: from the pair's own date. A
    pair whose first panel date is on or after its date entered later; `lag` trading days are
    dropped from the start of those. The step across a date is in neither cell: each cell
    differences only its own points.
    """
    before, after = {}, {}
    n = {"pairs": len(units), "by_board": defaultdict(int), "star_pairs_with_points_before": 0,
         "star_points_not_read": 0, "entered_after_opening": 0, "both_sides": defaultdict(int)}
    for u, (ts, vs) in units.items():
        b, c = board(u), conversion(u)
        n["by_board"][b] += 1
        one = {u: (ts, vs)}
        early = m.window(one, None, c - DAY)
        late = m.window(one, c, None)
        if b == "STAR":
            if early:
                n["star_pairs_with_points_before"] += 1
                n["star_points_not_read"] += len(early[u][0])
        elif early:
            before.update(early)
        if late:
            if ts[0] >= c:
                n["entered_after_opening"] += 1
                late = drop_first(late, lag)
            after.update(late)
        if (b != "STAR" and early and late and len(early[u][0]) >= m.MIN_SERIES
                and u in late and len(late[u][0]) >= m.MIN_SERIES):
            n["both_sides"][b] += 1
    n["by_board"], n["both_sides"] = dict(n["by_board"]), dict(n["both_sides"])
    return before, after, n


def b21_segments(c):
    """(label, units, flags) for B21. flags: less, knob, stage."""
    units = c["arms"][B21_ARM]
    before, after, _n = connect_split(units)
    both = {u for u in before if u in after and len(before[u][0]) >= m.MIN_SERIES and len(after[u][0]) >= m.MIN_SERIES}
    out = [("whole window", units, {"less": True, "knob": True, "stage": 1}),
           ("before own Connect opening", before, {"less": True, "knob": True, "stage": 1}),
           ("from own Connect opening", after, {"less": True, "knob": True, "stage": 1}),
           ("from own Connect opening, pairs read on both sides", {u: after[u] for u in sorted(both)},
            {"knob": True, "stage": 1})]
    for lag in ENTRY_LAGS[1:]:
        out.append((f"from own Connect opening, entry lag {lag}", connect_split(units, lag)[1], {"stage": 2, "borrow": "from own Connect opening"}))
    sh, sz = CONNECT_OPEN["SS"], CONNECT_OPEN["SZ"]
    for ex in ("SH main", "SZ"):
        us = {u: tv for u, tv in units.items() if board(u) == ex}
        for lab, lo, hi in ((f"to {sh - 3 * DAY}", None, sh - DAY), (f"{sh} to {sz - 3 * DAY}", sh, sz - DAY),
                            (f"from {sz}", sz, None)):
            out.append((f"{ex}, {lab}", m.window(us, lo, hi), {"knob": True, "stage": 2, "cross": True}))
    for lab, lo, hi in c["segments"]:
        out.append((f"FX span, {lab}", m.window(units, lo, hi), {"stage": 5}))
    return out


def b21_descriptions(c):
    """Shanghai main-board pairs between the steps of the link: described, not tested."""
    us = {u: tv for u, tv in c["arms"][B21_ARM].items() if board(u) == "SH main"}
    edges = list(QUOTA_STEPS) + [None]
    out = [(f"SH main, to {QUOTA_STEPS[0] - 3 * DAY}", m.window(us, None, QUOTA_STEPS[0] - DAY))]
    for lo, hi in zip(edges[:-1], edges[1:]):
        lab = f"SH main, from {lo}" if hi is None else f"SH main, {lo} up to {hi}"
        out.append((lab, m.window(us, lo, None if hi is None else hi - DAY)))
    return out


def segments(tag, c):
    """(arm, label, units, flags) for every span of every arm of a carrier."""
    if tag == "B21":
        return [(B21_ARM, lab, us, fl) for lab, us, fl in b21_segments(c)]
    less = bool(c.get("min_common")) and tag in ("B9", "B3", "B52")
    out = []
    for arm, units in c["arms"].items():
        out.append((arm, "whole window", units, {"less": less, "knob": True, "stage": 1}))
        for lab, lo, hi in c.get("segments", []):
            out.append((arm, lab, m.window(units, lo, hi), {"knob": True, "stage": 1}))
    return out


def cell_key(tag, arm, seg, freq, variant="raw"):
    return f"{tag}|{arm}|{seg}|{freq}|{variant}"


def k_for(tag, freq, points):
    if points <= BIG:
        return K_SMALL
    return K_B3_DAILY if (tag == "B3" and freq == "D") else K_BIG


class Cells:
    """The cells of the carriers asked for, built once from the stations' loaders."""

    def __init__(self, only=None):
        self.carriers = {}
        self.cells = {}          # key -> dict(tag, arm, seg, freq, variant, units, flags, common)
        self.extra = {}
        for tag, c in m.carriers(only):
            if "error" in c:
                raise SystemExit(f"{tag}: {c['error']}")
            self.carriers[tag] = c
            if c.get("not_read"):
                continue
            for arm, seg, units, fl in segments(tag, c):
                lc = st = None
                if fl.get("less"):
                    lc, st = m.less_common(units, c["min_common"], c.get("group"))
                for f in m.frequencies(c["freq"]):
                    self.cells[cell_key(tag, arm, seg, f)] = dict(
                        tag=tag, arm=arm, seg=seg, freq=f, variant="raw", flags=fl,
                        units=m.at(units, c["freq"], f), common=None)
                    if lc is not None:
                        self.cells[cell_key(tag, arm, seg, f, "less")] = dict(
                            tag=tag, arm=arm, seg=seg, freq=f, variant="less", flags=dict(fl, knob=False),
                            units=m.at(lc, c["freq"], f), common=st)
            if tag == "B21":
                for lab, us in b21_descriptions(c):
                    self.cells[cell_key(tag, B21_ARM, lab, "D", "describe")] = dict(
                        tag=tag, arm=B21_ARM, seg=lab, freq="D", variant="describe", flags={"stage": 0},
                        units=us, common=None)

    def jobs(self):
        """(stage, cost, kind, key, part) in the order they should run."""
        tier1 = {cell_key(*t) for t in CAL_TIER1}
        tier2 = {cell_key(*t) for t in CAL_TIER2}
        js = []
        for key, c in self.cells.items():
            pts = points_of(c["units"])
            st = c["flags"].get("stage", 1)
            if c["variant"] == "describe":
                js.append((0, pts, "desc", key, None))
                continue
            js.append((st if c["variant"] == "raw" else st + 1, pts, "read", key, None))
            if c["flags"].get("knob"):
                js.append((3, pts, "knob", key, None))
            if c["variant"] == "raw" and c["tag"] in ("B21", "B3") and not c["flags"].get("borrow") \
                    and key not in tier1 and key not in tier2 and c["flags"].get("stage") != 5 \
                    and c["seg"] != "whole window":     # those shapes were planted on 2026-10-06 and are kept
                js.append((4, pts, "quick", key, None))
            if key in tier1 or key in tier2:
                stg = 6 if key in tier1 else 7
                for part in cal_parts(k_for(c["tag"], c["freq"], pts), REPS_SMALL if pts <= BIG else REPS_BIG):
                    js.append((stg, pts, "cal", key, part))
        for tag in self.carriers:
            if tag == "B9":
                js.append((0, 0, "extra", "B9|extras", None))
            if tag == "B21":
                js.append((0, 0, "extra", "B21|connect counts", None))
        js.sort(key=lambda j: (j[0], j[1], j[2], j[3], str(j[4])))
        return js


def points_of(units):
    return int(sum(len(tv[1]) for tv in units.values()))


def cal_parts(k, reps):
    """The parts a calibration is cut into. Rung parts carry a slot, 0 or 1, not a half-life:
    which half-lives are planted is decided by the head."""
    if reps <= 2:
        return [("free", 0, k), ("rung0", 0, reps), ("rung1", 0, reps)]
    h, r = k // 2, reps // 2
    return [("free", 0, h), ("free", h, k), ("rung0", 0, r), ("rung0", r, reps), ("rung1", 0, r), ("rung1", r, reps)]


# ---------------------------------------------------------------------------------------------
# the cache
# ---------------------------------------------------------------------------------------------

def fingerprint(units) -> str:
    h = hashlib.sha256()
    for u in sorted(units, key=str):
        ts, vs = units[u]
        h.update(str(u).encode("utf-8"))
        h.update(("|".join(str(t) for t in ts)).encode("utf-8"))
        h.update(np.ascontiguousarray(np.asarray(vs, dtype=float)).tobytes())
    return h.hexdigest()[:24]


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:90]


def cache_path(kind, key, part=None, cache=None):
    tail = "" if part is None else "__" + "_".join(str(x) for x in part)
    name = f"{kind}__{_slug(key)}__{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}{tail}.json"
    return (cache or CACHE) / name


def _plain(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (dt.date,)):
        return o.isoformat()
    raise TypeError(type(o).__name__)


def save(path, config, result, complete=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.partial")
    text = json.dumps({"complete": bool(complete), "config": config, "result": result},
                      default=_plain, ensure_ascii=False, sort_keys=True)
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def load(path, config=None, partial=False):
    """The kept result, or None when the file is absent, cut short, unfinished or made otherwise.

    With `config` the file's own config must equal it key for key. With partial an unfinished
    file is returned too, as (result, complete)."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        ok = isinstance(d, dict) and "complete" in d and "result" in d and "config" in d
    except (OSError, ValueError):
        return None
    if not ok or (config is not None and json.loads(json.dumps(config, default=_plain)) != d["config"]):
        return None
    if partial:
        return d["result"], bool(d["complete"])
    return d["result"] if d["complete"] else None


def base_config(kind, key, units, **more):
    return dict({"version": VERSION, "kind": kind, "key": key, "fingerprint": fingerprint(units),
                 "seed": m.SEED, "q": m.TERCILE, "draws": list(m.DRAWS), "budget": m.BUDGET,
                 "min_series": m.MIN_SERIES}, **more)


# ---------------------------------------------------------------------------------------------
# what is read off one cell
# ---------------------------------------------------------------------------------------------

def centre(vals, q=m.TERCILE):
    """centre_summary plus each series' median, and the median over series of its absolute value.

    The ratio has no unit and is what is compared across carriers. Inside one carrier, before
    and after a change, the absolute median is compared instead: the spread a ratio is divided
    by can itself change with the regime.
    """
    cs = m.centre_summary(vals, q)
    med = {str(u): float(np.median(v)) for u, v in vals.items() if len(v) >= m.MIN_POINTS}
    if cs is None:
        return None
    cs["median_by_series"] = med
    cs["abs_median_over_series"] = float(np.median([abs(x) for x in med.values()])) if med else None
    return cs


def shape_of(units, freq):
    lens = sorted(len(tv[1]) for tv in units.values())
    read = [n for n in lens if n >= m.MIN_SERIES]
    return {"series": len(lens), "series_read": len(read), "series_too_short": len(lens) - len(read),
            "points": int(sum(lens)), "shortest": lens[0] if lens else 0, "longest": lens[-1] if lens else 0,
            "median_length_read": float(np.median(read)) if read else None,
            "step_days": (m.step_days(units, freq) if any(n > 1 for n in lens) else None)}


def describe_cell(units, freq):
    vals = m.values(units)
    return {"shape": shape_of(units, freq), "centre": centre(vals), "steps": m.step_summary(vals) if vals else None,
            "profile": m.profile(vals) if vals else []}


def read_cell(units, freq, k):
    out = describe_cell(units, freq)
    out["k"] = k
    out["held"] = m.held(units, k=k) if units else {"state": "unread", "reason": "no series in this span"}
    return out


def knob_cell(units):
    out = {}
    for q in KNOB_Q:
        r = m.settled(units, q=q, ladder=False) if units else {"state": "unread", "reason": "no series in this span"}
        out[f"{q:.4f}"] = {k: r.get(k) for k in ("state", "position", "draws", "observed", "reason", "n")}
    return out


def quick_cell(units, k, reps):
    return m.plant_one(units, k, reps, m.SEED, formal=False)


# ---------------------------------------------------------------------------------------------
# calibration by the whole reading, in parts that can be stopped and taken up again
# ---------------------------------------------------------------------------------------------

def cal_head(units, k, seed=m.SEED):
    """Everything plant_one does before it reads a planted panel. Line for line that function."""
    units = {u: tv for u, tv in m.as_units(units).items() if len(tv[1]) > 1}
    lens = sorted(len(tv[1]) for tv in units.values())
    shape = {"series": len(lens), "shortest": lens[0] if lens else 0, "longest": lens[-1] if lens else 0}
    units = {u: tv for u, tv in units.items() if len(tv[1]) >= m.MIN_SERIES}
    vals = m.values(units)

    def unread(reason):
        return {"state": "unread", "units_read": len(vals), "reason": reason, **shape}
    if len(vals) < m.MIN_UNITS:
        return unread(f"{len(vals)} series of at least {m.MIN_SERIES} points, {m.MIN_UNITS} needed")
    walk = m.null(vals, "walk", m.NSIM, seed + 1)
    if walk["mean"] is None:
        return unread("no far point followed by a step on the Gaussian paths of this shape")
    ideal = []
    for H in m.HALF_LIVES:
        g = m.null(vals, "walk", m.NSIM, seed + 10 + H, phi=0.5 ** (1.0 / H))
        ideal.append({"half_life": H, "produces": g["mean"],
                      "separable": bool(g["mean"] - walk["mean"] > m.Z90 * walk["sd"])})
    seen = [x["half_life"] for x in ideal if x["separable"]]
    L, p, eligible, _ = m.blocks_for(vals)
    b0 = max(2, int(round(p)))
    free = m.free_positions(units, k, seed)
    if len(free) < k:
        return unread(f"only {len(free)} of the {k} panels with no force could be read")
    targets = []
    if seen:
        mid = seen[len(seen) // 2]
        targets.append(mid)
        if seen[-1] != mid:
            targets.append(seen[-1])
    return {"state": "read", "units_read": len(vals), **shape, "median_length": L, "eligible_blocks": eligible,
            "walk_mean": walk["mean"], "walk_sd": walk["sd"], "artefact_above_one_half": walk["mean"] - 0.5,
            "ideal": ideal, "ideal_separable": seen, "panel_block": b0, "free_list": [float(x) for x in free],
            "targets": targets}


def cal_part(units, head, part, k, seed=m.SEED, kept=None, keep=None, stop_after=None):
    """One part: panels lo..hi-1 of the no-force set, or of one planted rung.

    `kept` is what an earlier run of this part finished, {index: row}. Panels before lo and
    panels already kept are drawn and not read, so the random sequence is the one plant_one
    walks. `keep(rows)` is called after every panel read. stop_after cuts the run short, for the
    selftest. Returns (rows, complete).
    """
    name, lo, hi = part
    rows = {int(i): r for i, r in (kept or {}).items()}
    units = {u: tv for u, tv in m.as_units(units).items() if len(tv[1]) >= m.MIN_SERIES}
    b0 = head["panel_block"]
    if name == "free":
        H, phi, rng = None, 1.0, np.random.default_rng(seed + 99)
    else:
        slot = int(name[4:])
        if slot >= len(head["targets"]):
            return rows, True
        H = head["targets"][slot]
        phi, rng = 0.5 ** (1.0 / H), np.random.default_rng(seed + 199 + H)
    done = 0
    for i in range(hi):
        panel = m.draw(units, b0, phi, rng)
        if i < lo or i in rows:
            continue
        if stop_after is not None and done >= stop_after:
            return rows, False
        if H is None:
            rows[i] = {"held": m.held(panel, k=k, seed=seed + 1000 * (i + 1), ladder=False)["state"]}
        else:
            x = m.reading(panel, seed=seed + 1000 * (i + 1) + H, ladder=False, trend=False)
            rows[i] = {"pos": None if x["state"] == "unread" else m._pos(x),
                       "held": m.held(panel, k=k, seed=seed + 1000 * (i + 1) + H, ladder=False)["state"]}
        done += 1
        if keep:
            keep(rows)
    return rows, True


def cal_join(head, parts):
    """plant_one(formal=True)'s dictionary from a head and its finished parts.

    parts: {part: rows}. A rung or the no-force set with a panel missing is left out and named
    in `missing`, so a calibration that is not whole cannot be read as one.
    """
    if head["state"] == "unread":
        return dict(head)
    free = head["free_list"]
    out = {k: v for k, v in head.items() if k not in ("free_list", "targets")}
    out["free"] = {"panels": len(free), "min": float(min(free)), "median": float(np.median(free)),
                   "max": float(max(free)), "over_line": int(sum(x > 1 for x in free)),
                   "under_line": int(sum(x < -1 for x in free))}
    merged = defaultdict(dict)
    want = defaultdict(int)
    for (name, lo, hi), rows in parts.items():
        merged[name].update({int(i): r for i, r in rows.items()})
        want[name] = max(want[name], hi)
    missing = []
    planted = []
    for slot, H in enumerate(head["targets"]):
        rows = merged.get(f"rung{slot}", {})
        if len(rows) < want.get(f"rung{slot}", 1):
            missing.append(f"rung{slot}")
            continue
        pos = [rows[i]["pos"] for i in sorted(rows) if rows[i]["pos"] is not None]
        st = defaultdict(int)
        for i in sorted(rows):
            st[rows[i]["held"]] += 1
        planted.append({"half_life": H, "panels": len(pos), "over_line": int(sum(x > 1 for x in pos)),
                        "over_every_free_panel": int(sum(x > 1 and x > max(free) for x in pos)), "held": dict(st)})
    out["planted"] = planted
    rows = merged.get("free", {})
    if len(rows) < want.get("free", 1):
        missing.append("free")
    else:
        st = defaultdict(int)
        for i in sorted(rows):
            st[rows[i]["held"]] += 1
        out["free_held"] = dict(st)
    if missing:
        out["missing"] = missing
    return out


# ---------------------------------------------------------------------------------------------
# B9: calm against stress, and inside against outside the published creation fee
# ---------------------------------------------------------------------------------------------

def split_counts(v, flags, q=m.TERCILE):
    """The count of one series, split by a flag on the day the far point stands on.

    The centre and the cut are the whole series' own, as in the count; only the tally is split.
    Returns {True: [back, away], False: [back, away]}.
    """
    v = np.asarray(v, dtype=float)
    out = {True: [0, 0], False: [0, 0]}
    n = len(v)
    if n < m.MIN_POINTS:
        return out
    dev = v - np.median(v)
    a = np.abs(dev)
    k = min(n - 1, max(0, int(round(q * (n - 1)))))
    cut = np.partition(a, k)[k]
    step = np.diff(v)
    use = (a[:-1] >= cut) & (step != 0)
    back = use & (step * dev[:-1] < 0)
    fl = np.asarray(flags[:-1], dtype=bool)
    for f in (True, False):
        sel = fl if f else ~fl
        out[f] = [int(np.sum(back & sel)), int(np.sum(use & ~back & sel))]
    return out


def band_counts(lam, f_max):
    """Steps toward zero and away from it, for days inside and outside the band |lam| <= f_max."""
    lam, f_max = np.asarray(lam, dtype=float), np.asarray(f_max, dtype=float)
    step = np.diff(lam)
    use = step != 0
    toward = use & (step * lam[:-1] < 0)
    inside = np.abs(lam[:-1]) <= f_max[:-1]
    return {"inside": [int(np.sum(toward & inside)), int(np.sum(use & ~toward & inside))],
            "outside": [int(np.sum(toward & ~inside)), int(np.sum(use & ~toward & ~inside))]}


def b9_extras(flip=False):
    b9 = m.station("b9_omega")
    spreads = b9.read_spread_table()
    out = {"arms": {}, "fee_source": "b9_omega.FIXED_CREATION_FEE_USD over CREATION_UNIT_SHARES times the day's NAV"}
    for arm, tickers in (("main arm", b9.MAIN_ARM), ("comparison arm", b9.COMPARISON_ARM)):
        calm, stress, whole = [0, 0], [0, 0], [0, 0]
        band = {"inside": [0, 0], "outside": [0, 0]}
        funds_with_fee = 0
        fmax_bp = []
        for t in tickers:
            s = b9.lambda_series(t, spreads)
            days = sorted(s)
            lam = np.array([s[d]["lam"] for d in days])
            flags = np.array([bool(s[d]["calm"]) != flip for d in days])
            sc = split_counts(lam, flags)
            b, a = m.counts(lam[None, :])
            whole[0] += int(b[0])
            whole[1] += int(a[0])
            for j in (0, 1):
                calm[j] += sc[True][j]
                stress[j] += sc[False][j]
            fee = b9.FIXED_CREATION_FEE_USD.get(t)
            if fee is not None:
                funds_with_fee += 1
                fm = np.array([fee / (b9.CREATION_UNIT_SHARES * s[d]["nav"]) for d in days])
                fmax_bp.append(float(np.median(fm)) * 1e4)
                bc = band_counts(lam, fm)
                for g in band:
                    for j in (0, 1):
                        band[g][j] += bc[g][j]
        out["arms"][arm] = {"calm": calm, "stress": stress, "whole": whole, "band": band,
                            "funds_with_a_published_fee": funds_with_fee,
                            "median_f_max_bp": float(np.median(fmax_bp)) if fmax_bp else None}
    return out


# ---------------------------------------------------------------------------------------------
# the worker
# ---------------------------------------------------------------------------------------------

def claim(kind, key, part, run_id, cache=None):
    d = (cache or CACHE) / "claims"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (cache_path(kind, key, part).stem + f".{run_id}.claim")
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        return False
    os.write(fd, f"{os.getpid()}".encode("ascii"))
    os.close(fd)
    return True


def do_job(cells, kind, key, part, log=print):
    """Run one job unless what it would write is already kept. Returns 'kept', 'ran' or 'waits'."""
    if kind == "extra":
        path = cache_path(kind, key)
        cfg = {"version": VERSION, "kind": kind, "key": key}
        if load(path, cfg) is not None:
            return "kept"
        if key.startswith("B9"):
            res = b9_extras()
        else:
            res = connect_split(cells.carriers["B21"]["arms"][B21_ARM])[2]
            res["quota_steps"] = [d.isoformat() for d in QUOTA_STEPS]
        save(path, cfg, res)
        return "ran"
    c = cells.cells[key]
    units, freq = c["units"], c["freq"]
    pts = points_of(units)
    k = k_for(c["tag"], freq, pts)
    reps = REPS_SMALL if pts <= BIG else REPS_BIG
    if kind in ("desc", "read", "knob", "quick"):
        cfg = base_config(kind, key, units, **({"k": k} if kind in ("read", "quick") else {}),
                          **({"reps": reps} if kind == "quick" else {}),
                          **({"knob_q": list(KNOB_Q)} if kind == "knob" else {}))
        path = cache_path(kind, key)
        if load(path, cfg) is not None:
            return "kept"
        if kind == "desc":
            res = describe_cell(units, freq)
        elif kind == "read":
            res = read_cell(units, freq, k)
            if c["common"] is not None:
                res["common"] = c["common"]
        elif kind == "knob":
            res = knob_cell(units)
        else:
            res = quick_cell(units, k, reps)
        save(path, cfg, res)
        return "ran"
    if kind == "cal":
        hcfg = base_config("calhead", key, units, k=k)
        hpath = cache_path("calhead", key)
        head = load(hpath, hcfg)
        if head is None:
            head = cal_head(units, k)
            save(hpath, hcfg, head)
        cfg = base_config("cal", key, units, k=k, reps=reps, part=list(part))
        path = cache_path("cal", key, part)
        got = load(path, cfg, partial=True)
        if got is not None and got[1]:
            return "kept"
        if head["state"] == "unread":
            save(path, cfg, {})
            return "ran"
        kept = got[0] if got is not None else {}
        rows, complete = cal_part(units, head, tuple(part), k, kept=kept,
                                  keep=lambda r: save(path, cfg, {str(i): v for i, v in r.items()}, complete=False))
        save(path, cfg, {str(i): v for i, v in rows.items()}, complete=complete)
        return "ran"
    raise ValueError(kind)


def work(only, run_id, stages=None, kinds=None) -> int:
    t0 = time.perf_counter()
    cells = Cells(only)
    jobs = [j for j in cells.jobs() if (not stages or j[0] in stages) and (not kinds or j[2] in kinds)]
    print(f"[{os.getpid()}] {len(jobs)} jobs over {sorted(cells.carriers)}; loaded in {time.perf_counter() - t0:.1f}s",
          flush=True)
    ran = 0
    for stage, pts, kind, key, part in jobs:
        if run_id and not claim(kind, key, part, run_id):
            continue
        t1 = time.perf_counter()
        what = do_job(cells, kind, key, part)
        if what == "ran":
            ran += 1
            print(f"[{os.getpid()}] stage {stage} {kind} {key} {part or ''} points {pts}: "
                  f"{time.perf_counter() - t1:.1f}s", flush=True)
    print(f"[{os.getpid()}] done, {ran} jobs run, {time.perf_counter() - t0:.1f}s", flush=True)
    return 0


def status(only) -> int:
    cells = Cells(only)
    tot = defaultdict(lambda: [0, 0])
    waiting = []
    for stage, pts, kind, key, part in cells.jobs():
        p = cache_path("extra" if kind == "extra" else kind, key, part)
        got = load(p, partial=True)
        done = got is not None and got[1]
        tot[(stage, kind)][0] += 1
        tot[(stage, kind)][1] += int(done)
        if not done:
            n = len(got[0]) if (got is not None and kind == "cal") else 0
            waiting.append(f"   stage {stage} {kind} {key} {part or ''}" + (f" ({n} panels kept)" if n else ""))
    for (stage, kind), (n, d) in sorted(tot.items()):
        print(f"stage {stage} {kind:<6} {d:>4} of {n}")
    print(f"{len(waiting)} jobs not finished")
    for w in waiting:
        print(w)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", action="store_true", help="run the jobs that are not kept yet")
    ap.add_argument("--status", action="store_true", help="which jobs are kept and which are not")
    ap.add_argument("--only", nargs="*", help="carrier tags")
    ap.add_argument("--run-id", default="", help="workers started with the same id share the jobs out")
    ap.add_argument("--stages", nargs="*", type=int)
    ap.add_argument("--kinds", nargs="*")
    ap.add_argument("--run", action="store_true", help="build the record from what is kept")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    only = set(a.only) if a.only else None
    if a.selftest:
        import b142_record
        return b142_record.selftest()
    if a.work:
        return work(only, a.run_id, set(a.stages) if a.stages else None, set(a.kinds) if a.kinds else None)
    if a.status:
        return status(only)
    if a.run:
        import b142_record
        return b142_record.run()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
