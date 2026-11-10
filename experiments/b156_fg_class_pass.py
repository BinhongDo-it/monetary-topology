"""B156: on forward-guidance days, how far one 30-year fixed mortgage moves for two borrower classes.

The rival premise is one intertemporal price schedule for every household: the budget
P_t C_t + Q_t B_{t+1} = B_t + W_t H_t + Pi_t, with no household index on Q_t (the 2026
prize committee's scientific background, section 4.2.1). Under that premise a spread
between two classes on the same contract can only be a constant wedge outside the
policy channel, so news about the future rate path moves both classes' rates alike and
the change in the spread on such a day is zero, drawn from the same distribution as on
any other day. Here the VA rate rides on Ginnie Mae securitisation and the conventional
rate on UMBS, two different edges, and nothing makes their responses equal.

Polarity of the rival criteria (11e, first clause bis): PASS means the rival's point
prediction failed on that cell, and then the grid is B. A reading that cannot be told
from the floor is the third state: passed None, grid unread.

    python experiments/b156_fg_class_pass.py            # run, write the record
    python experiments/b156_fg_class_pass.py --selftest # seeded failures, must all flip
"""

import argparse
import csv
import html
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b156"
OUT = ROOT / "results" / "b156_fg_class_pass.json"
SESSION = "B156"

SERIES = {"conv": "OBMMIC30YF", "va": "OBMMIVA30YF", "fha": "OBMMIFHA30YF",
          "jumbo": "OBMMIJUMBO30YF", "t2": "DGS2", "t10": "DGS10"}
ROWS = {"OBMMIC30YF": 2553, "OBMMIVA30YF": 2553, "OBMMIFHA30YF": 2553,
        "OBMMIJUMBO30YF": 2553, "DGS2": 13143, "DGS10": 16903}  # counted in the browser before saving
N_RELEASES = 149  # 2009-01-28 to 2026-09-16; bands need the releases the fixed-scenario index spans
EVENT_FIRST = "20170101"  # the class-type indices start 2017-01-03; earlier events are printed only
LANDMARKS = ("20190130", "20200916")  # "patient"; the outcome-based guidance
WINDOWS = (2, 5, 10)                   # trading days, the knob 11f scans
BANDS = (2, 5)                         # trading days excluded either side of any release
DEFAULT_H, DEFAULT_BAND = 2, 2
DRAWS = 2000                           # D51: at 300 draws a p near 0.05 moves by about 0.013
SEEDS = (156, 1561)
ALPHA = 0.05

FUT = re.compile(r"(gradual increases|patient|act as appropriate|until|soon be appropriate|"
                 r"policy firming|not expect it will be appropriate|additional adjustments|"
                 r"future adjustments|future increases|ongoing increases|any adjustments|"
                 # the zero-bound years write the path on the federal funds rate, not on the range
                 r"extended period|at least through|at least as long as|considerable time|well past|"
                 r"likely to occur sooner|likely to occur later|below levels)", re.I)
ACT = re.compile(r"((raise|lower|maintain|keep|reduce)[a-z]* (the|its|this|the current) target range"
                 r"|target range[^.]{0,80}remains appropriate)")
HOLD = re.compile(r"((maintain|keep)[a-z]* (the|its|this|the current) target range|target range[^.]{0,80}remains appropriate)")
PATH_OBJECT = re.compile(r"(target range|federal funds rate|policy firming)")

MAPPING_11C = (
    {"state": "nonzero, sign stable over the knobs", "maps_to": "rival point prediction fails", "verdict": True, "grid": "B"},
    {"state": "sign moves over the knobs", "maps_to": "cell not read (11f)", "verdict": None, "grid": "unread"},
    {"state": "inside the floor", "maps_to": "third state, no verdict", "verdict": None, "grid": "unread"},
)

RIVAL = {
    "rival_premise": "One intertemporal price schedule for every household: P_t C_t + Q_t B_{t+1} = B_t + W_t H_t + Pi_t, "
                     "with no household index on the bond price Q_t; the edge field is w = d(phi), the same for every class.",
    "rival_entailment": "An announcement that changes only the expected path of the policy rate reaches every household "
                        "through that one Q_t sequence. A spread between two borrower classes on the same contract can "
                        "then only be a constant wedge outside the policy channel, so its change over such a day is zero "
                        "and its change on rate news generally is zero: the VA minus conventional spread does not load on "
                        "the 10-year yield.",
    "cite": "Royal Swedish Academy of Sciences, Scientific background to the 2026 prize in economic sciences, "
            "'Microeconomic foundations of macroeconomic stabilization', section 4.2.1 'Consumers: enter Hall'.",
    "rival_shape": "point",
}


# ---------------------------------------------------------------- loading

def load_series(raw):
    out = {}
    for key, sid in SERIES.items():
        p = raw / f"b156_fred_{sid}.csv"
        rows = list(csv.reader(p.open(encoding="utf-8")))
        out[key] = {"header": rows[0], "n": len(rows) - 1,
                    "vals": {d: float(v) for d, v in rows[1:] if v not in ("", ".")}}
    return out


def statement_sentences(path):
    t = path.read_text(encoding="utf-8")
    if 'id="article"' not in t:
        return None
    body = t.split('id="article"', 1)[1]
    sents = []
    # Pages before 2011 open paragraphs with <P> and never close them, and put the vote in
    # the same paragraph as the statement; so split on the opening tag, any case, and cut each
    # paragraph at the vote, which also keeps dissenting views out of the path sentences.
    for p in re.split(r"<p\b[^>]*>", body, flags=re.I)[1:]:
        p = re.split(r"</p>|<div\b", p, maxsplit=1, flags=re.I)[0]
        s = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", p))).strip()
        s = re.split(r"Voting (for|against)", s)[0].strip()
        if len(s) < 40:
            continue
        sents += re.split(r"(?<=\.)\s+(?=[A-Z])", s)
    return sents


def releases(raw):
    rel = {}
    for f in sorted((raw / "fomc").glob("monetary*a.htm")):
        rel[f.stem[8:16]] = statement_sentences(f)
    return rel


def events_from_text(rel):
    """Rate unchanged and the set of rate-path sentences differs from the last statement's."""
    events, skipped, prev = [], [], None
    for d, sents in sorted(rel.items()):
        if sents is None:
            skipped.append(d)
            continue
        act = next((s for s in sents if ACT.search(s)), None)
        if act is None:
            skipped.append(d)
            continue
        path = frozenset(s for s in sents if PATH_OBJECT.search(s) and FUT.search(s))
        if prev is not None and HOLD.search(act) and path != prev:
            events.append({"date": d, "removed": sorted(prev - path), "added": sorted(path - prev)})
        prev = path
    return events, skipped


# ---------------------------------------------------------------- measurement

def panel(series):
    days = sorted(set(series["conv"]["vals"]) & set(series["va"]["vals"]) & set(series["fha"]["vals"])
                  & set(series["t2"]["vals"]) & set(series["t10"]["vals"]))
    arr = {k: np.array([series[k]["vals"][d] for d in days]) for k in ("conv", "va", "fha", "t2", "t10")}
    return days, arr


def iso(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def change(x, k, h):
    """Close of day k+h-1 against close of day k-1: the release day and h-1 days after."""
    return x[k + h - 1] - x[k - 1]


def windows(days, arr, rel_dates, h, band, overlap=False):
    """Change windows clear of every release by `band` trading days. Non-overlapping by
    default; with overlap=True every start day is kept, so the ten-day cells keep a few
    hundred windows, and the month-block bootstrap carries the dependence that brings."""
    idx = {d: i for i, d in enumerate(days)}
    near = set()
    for d in rel_dates:
        k = idx.get(iso(d))
        if k is None:  # release on a day with no print: take the next print
            k = next((i for i, dd in enumerate(days) if dd > iso(d)), None)
        if k is not None:
            near.update(range(k - band, k + h + band))
    rows = []
    k = 1
    while k + h - 1 < len(days):
        if not any(j in near for j in range(k - 1, k + h)):
            rows.append(k)
            k += 1 if overlap else h
        else:
            k += 1
    return rows


def spreads(arr, ks, h, cls):
    s = arr[cls] - arr["conv"]
    return np.array([change(s, k, h) for k in ks]), np.array([change(arr["t10"], k, h) for k in ks])


def ols_slope(y, x):
    xm = x - x.mean()
    return float((xm * (y - y.mean())).sum() / (xm * xm).sum())


def month_bootstrap(y, x, months, seed):
    rng = np.random.default_rng(seed)
    groups = {}
    for i, m in enumerate(months):
        groups.setdefault(m, []).append(i)
    keys = list(groups)
    out = []
    for _ in range(DRAWS):
        pick = rng.integers(0, len(keys), len(keys))
        ii = np.concatenate([groups[keys[j]] for j in pick])
        out.append(ols_slope(y[ii], x[ii]))
    out = np.sort(np.array(out))
    return float(out[int(0.05 * DRAWS)]), float(out[int(0.95 * DRAWS) - 1])


def slope_cell(days, arr, rel_dates, h, band, cls, seed=SEEDS[0], overlap=False):
    ks = windows(days, arr, rel_dates, h, band, overlap)
    y, x = spreads(arr, ks, h, cls)
    months = [days[k][:7] for k in ks]
    b = ols_slope(y, x)
    lo, hi = month_bootstrap(y, x, months, seed)
    return {"h": h, "band": band, "n": len(ks), "slope": b, "lo90": lo, "hi90": hi, "overlap": overlap,
            "excludes_zero": bool(lo > 0 or hi < 0), "sd_change": float(y.std())}


def event_cell(days, arr, rel_dates, events, h, band, cls, seeds=SEEDS, draws=None):
    draws = draws or DRAWS
    idx = {d: i for i, d in enumerate(days)}
    s = arr[cls] - arr["conv"]
    rows = []
    for e in events:
        k = idx.get(iso(e["date"]))
        if k is None:
            continue
        rows.append({"date": e["date"], "d_spread": float(change(s, k, h)),
                     "d_t2": float(change(arr["t2"], k, h)), "d_t10": float(change(arr["t10"], k, h))})
    ks = windows(days, arr, rel_dates, h, band)
    null = np.abs(np.array([change(s, k, h) for k in ks]))
    for r in rows:
        r["null_rank"] = float((null < abs(r["d_spread"])).mean())
    stat = float(np.mean([abs(r["d_spread"]) for r in rows])) if rows else float("nan")
    ps = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        dist = np.array([null[rng.choice(len(null), len(rows), replace=False)].mean() for _ in range(draws)])
        ps.append(float((dist >= stat).mean()))
    return {"h": h, "band": band, "rows": rows, "mean_abs": stat, "null_mean_abs": float(null.mean()),
            "null_n": int(len(null)), "perm_p": ps, "draws": draws}


def read_slope_cells(cells):
    """11f: the sign must hold over every knob point; then the default point decides."""
    signs = {math.copysign(1, c["slope"]) for c in cells}
    default = next(c for c in cells if c["h"] == DEFAULT_H and c["band"] == DEFAULT_BAND)
    if len(signs) > 1:
        return MAPPING_11C[1]
    return MAPPING_11C[0] if default["excludes_zero"] else MAPPING_11C[2]


def read_event_cells(cells):
    def above(c):
        return max(c["perm_p"]) <= ALPHA
    def resolved(c):  # D51: seed spread smaller than the distance to the line
        p = c["perm_p"]
        return len(p) >= 2 and abs(p[0] - p[1]) < abs(sum(p) / len(p) - ALPHA)
    if not all(resolved(c) for c in cells):
        return MAPPING_11C[2], "a permutation p is not resolved at %d draws" % max(c.get("draws", DRAWS) for c in cells)
    flags = {above(c) for c in cells}
    if len(flags) > 1:
        return MAPPING_11C[1], "above the floor on some knob points and not others"
    return (MAPPING_11C[0] if flags == {True} else MAPPING_11C[2]), ""


# ---------------------------------------------------------------- criteria

def crit(name, kind, passed, detail, extra=None):
    c = {"name": name, "kind": kind, "passed": None if passed is None else bool(passed), "detail": detail}
    c.update(extra or {})
    return c


def f6(x):
    return float(f"{x:.6f}")


def build_criteria(series, rel, events, skipped, slopes_va, slopes_fha, ev_va, ev_fha):
    cr = []
    bad = [f"{k} {series[k]['n']} rows" for k in series if series[k]["n"] != ROWS[SERIES[k]]
           or series[k]["header"] != ["observation_date", SERIES[k]]]
    nrel = sum(1 for v in rel.values() if v is not None)
    cr.append(crit("B156-1", "instrument", not bad and nrel == N_RELEASES and len(rel) == N_RELEASES,
                   "FRED files against the in-browser row counts: %s; releases with an #article block %d of %d"
                   % ("all match" if not bad else "; ".join(bad), nrel, N_RELEASES)))

    dates = [e["date"] for e in events]
    miss = [d for d in LANDMARKS if d not in dates]
    cr.append(crit("B156-2", "known_answer", not miss and len(events) > 0,
                   "%d events from the text rule: %s. Landmarks %s %s. Releases with no rate decision skipped: %s"
                   % (len(events), " ".join(dates), " ".join(LANDMARKS), "present" if not miss else "MISSING " + " ".join(miss),
                      " ".join(skipped))))

    m3 = read_slope_cells(slopes_va)
    d = next(c for c in slopes_va if c["h"] == DEFAULT_H and c["band"] == DEFAULT_BAND)
    cr.append(crit("B156-3", "rival", m3["verdict"],
                   "All non-event windows, VA minus conventional change on 10-year change: slope %.4f, 90%% month-block "
                   "interval [%.4f, %.4f], n %d (h=%d, band %d). Knob points (h, band, slope): %s. Reading: %s."
                   % (d["slope"], d["lo90"], d["hi90"], d["n"], d["h"], d["band"],
                      "; ".join("(%d, %d, %.4f%s)" % (c["h"], c["band"], c["slope"], "*" if c["excludes_zero"] else "")
                                for c in slopes_va), m3["state"]),
                   dict(RIVAL, grid=m3["grid"])))

    m4, why = read_event_cells(ev_va)
    e = next(c for c in ev_va if c["h"] == DEFAULT_H and c["band"] == DEFAULT_BAND)
    cr.append(crit("B156-4", "rival", m4["verdict"],
                   "Forward-guidance days, |change in VA minus conventional| mean %.4f against non-event mean %.4f "
                   "(n %d), permutation p %s at %d draws. Per day (date, spread, 2y, 10y, rank): %s. Knob points (h, band, p): %s. "
                   "Reading: %s%s."
                   % (e["mean_abs"], e["null_mean_abs"], e["null_n"], "/".join("%.3f" % p for p in e["perm_p"]), DRAWS,
                      "; ".join("%s %+.3f %+.2f %+.2f %.2f" % (r["date"], r["d_spread"], r["d_t2"], r["d_t10"], r["null_rank"])
                                for r in e["rows"]),
                      "; ".join("(%d, %d, %s)" % (c["h"], c["band"], "/".join("%.3f" % p for p in c["perm_p"])) for c in ev_va),
                      m4["state"], (", " + why) if why else ""),
                   dict(RIVAL, grid=m4["grid"])))

    f = next((c for c in slopes_fha if c["h"] == DEFAULT_H and c["band"] == DEFAULT_BAND), None)
    g = next((c for c in ev_fha if c["h"] == DEFAULT_H and c["band"] == DEFAULT_BAND), None)
    ok5 = f is not None and g is not None and all(map(math.isfinite, (f["slope"], g["mean_abs"]))) and g["rows"]
    cr.append(crit("B156-5", "own_reading", ok5,
                   "FHA minus conventional, printed as a gradient (the split is self-selected): slope %s interval [%s, %s]; "
                   "event mean |change| %s against %s, p %s"
                   % ((("%.4f" % f["slope"], "%.4f" % f["lo90"], "%.4f" % f["hi90"]) if f else ("none",) * 3) +
                      (("%.4f" % g["mean_abs"], "%.4f" % g["null_mean_abs"], "/".join("%.3f" % p for p in g["perm_p"])) if g else ("none",) * 3))))

    finite = all(math.isfinite(c[k]) for c in slopes_va for k in ("slope", "lo90", "hi90")) and len(slopes_va) == len(WINDOWS) * len(BANDS)
    h10 = [c for c in slopes_va if c["h"] == 10]
    cr.append(crit("B156-6", "instrument", finite,
                   "Six knob points computed: %s. Rate-sheet lag check: at h=10 the interval %s zero on %d of %d bands"
                   % ("yes" if finite else "NO", "excludes", sum(c["excludes_zero"] for c in h10), len(h10))))

    both = all(len(c["perm_p"]) == len(SEEDS) for c in ev_va)
    cr.append(crit("B156-7", "bookkeeping", both,
                   "Permutation floor at %d draws, seeds %s, printed per knob point; largest seed spread %.3f"
                   % (DRAWS, "/".join(map(str, SEEDS)),
                      max((abs(c["perm_p"][0] - c["perm_p"][-1]) for c in ev_va), default=float("nan")))))
    return cr


MND_FILE = RAW / "mnd" / "mtg-rates-mnd-full_20261016.html"
MND_NAMES = {"mnd_conv": "MND 30 Yr. Fixed", "mnd_fha": "MND 30 Yr. FHA"}


def load_mnd(path=MND_FILE):
    """Rate-sheet index at one fixed scenario per product (75 LTV and 780 FICO for the
    conventional line), so its day-to-day change carries no borrower composition. The page
    keeps intraday revisions; the last value of each New York calendar day is taken."""
    from datetime import datetime, timedelta
    t = path.read_text(encoding="utf-8")
    out = {}
    for key, desc in MND_NAMES.items():
        m = t.find('"description":"%s"' % desc)
        i = t.find('"data":[', m)
        j = t.find("]", i)
        last = {}
        for e in json.loads(t[i + 7:j + 1]):
            day = (datetime.strptime(e["d"][:19], "%Y-%m-%dT%H:%M:%S") - timedelta(hours=4)).strftime("%Y-%m-%d")
            last[day] = float(e["v"])
        out[key] = last
    return out


def mnd_panel(series, mnd, first, last):
    days = sorted(d for d in set(mnd["mnd_conv"]) & set(mnd["mnd_fha"]) & set(series["t10"]["vals"])
                  & set(series["t2"]["vals"]) if first <= d <= last)
    arr = {"conv": np.array([mnd["mnd_conv"][d] for d in days]), "fha": np.array([mnd["mnd_fha"][d] for d in days]),
           "t2": np.array([series["t2"]["vals"][d] for d in days]),
           "t10": np.array([series["t10"]["vals"][d] for d in days])}
    return days, arr


def mnd_cells(series, mnd, rel_dates, first, last, overlap=False):
    days, arr = mnd_panel(series, mnd, first, last)
    return days, [slope_cell(days, arr, rel_dates, h, b, "fha", overlap=overlap) for h in WINDOWS for b in BANDS]


MND_EVENT_DRAWS = 20000  # standard error of a p near 0.05 is about 0.0015
EARLY_LANDMARKS = ("20110809", "20141217")  # "at least through mid-2013"; "patient"


def fmt_slopes(cs):
    return "; ".join("(%d, %d, %.4f [%.4f, %.4f] n %d)" % (c["h"], c["band"], c["slope"], c["lo90"], c["hi90"], c["n"]) for c in cs)


def second_pass_criteria(va_ov, m_over_ov, m_long_ov, mnd_ev):
    """2026-10-17: overlapping windows for every slope cell, and the forward-guidance days of
    2009 to 2026 on the fixed-scenario quotes."""
    cr = []
    m9 = read_slope_cells(va_ov) if va_ov else MAPPING_11C[2]
    cr.append(crit("B156-9", "rival", m9["verdict"] if va_ov else None,
                   "VA minus conventional on the 10-year, overlapping windows, month-block interval: %s. Reading: %s."
                   % (fmt_slopes(va_ov), m9["state"]), dict(RIVAL, grid=m9["grid"])))

    ok10 = bool(m_over_ov) and bool(m_long_ov) and all(math.isfinite(c["slope"]) and c["n"] > 0 for c in m_over_ov + m_long_ov)
    cr.append(crit("B156-10", "own_reading", ok10,
                   "FHA minus conventional at fixed scenarios, overlapping windows. 2017-01-03 onward: %s; reading %s. "
                   "2009-04-29 to 2016-12-30: %s; reading %s."
                   % (fmt_slopes(m_over_ov), read_mnd(m_over_ov) if m_over_ov else "none",
                      fmt_slopes(m_long_ov), read_mnd(m_long_ov) if m_long_ov else "none")))

    d = next((c for c in mnd_ev if c["h"] == DEFAULT_H and c["band"] == DEFAULT_BAND), None)
    got = {r["date"] for r in d["rows"]} if d else set()
    miss = [x for x in EARLY_LANDMARKS if x not in got]
    m11, why = read_event_cells(mnd_ev) if mnd_ev and d and d["rows"] else (MAPPING_11C[2], "no event rows")
    ok11 = d is not None and len(d["rows"]) > 0 and not miss and math.isfinite(d["mean_abs"])
    cr.append(crit("B156-11", "own_reading", ok11,
                   "Forward-guidance days 2009 to 2026 on the fixed-scenario quotes, |change in FHA minus conventional|: "
                   "%s. Early landmarks %s %s. Knob points (h, band, mean, null mean, p; draws in the record): %s. Reading: %s%s."
                   % (("%d days, per day (date, spread, 2y, 10y, rank): " % len(d["rows"]) +
                       "; ".join("%s %+.3f %+.2f %+.2f %.2f" % (r["date"], r["d_spread"], r["d_t2"], r["d_t10"], r["null_rank"])
                                 for r in d["rows"])) if d else "none",
                      " ".join(EARLY_LANDMARKS), "present" if not miss else "MISSING " + " ".join(miss),
                      "; ".join("(%d, %d, %.4f, %.4f, %s)" % (c["h"], c["band"], c["mean_abs"], c["null_mean_abs"],
                                                               "/".join("%.3f" % p for p in c["perm_p"])) for c in mnd_ev),
                      m11["state"], (", " + why) if why else "")))
    return cr


def read_mnd(cells):
    m = read_slope_cells(cells)
    return m["state"]


def mnd_criterion(cells_overlap, cells_long, n_days):
    ok = bool(cells_overlap) and all(math.isfinite(c["slope"]) and c["n"] > 0 for c in cells_overlap + cells_long)
    fmt = fmt_slopes
    return crit("B156-8", "own_reading", ok,
                "FHA minus conventional at fixed scenarios (MND rate-sheet index), change on 10-year change. "
                "2017-01-03 onward, same release bands as B156-5: %s; reading %s. 2009-04-29 to 2016-12-30 "
                "(same release bands): %s; reading %s. Days with both lines: %d"
                % (fmt(cells_overlap), read_mnd(cells_overlap) if cells_overlap else "none",
                   fmt(cells_long), read_mnd(cells_long) if cells_long else "none", n_days))


def measure(series, rel, events):
    days, arr = panel(series)
    rd = list(rel)
    slopes_va = [slope_cell(days, arr, rd, h, b, "va") for h in WINDOWS for b in BANDS]
    slopes_fha = [slope_cell(days, arr, rd, h, b, "fha") for h in WINDOWS for b in BANDS]
    ev_va = [event_cell(days, arr, rd, events, h, b, "va") for h in WINDOWS for b in BANDS]
    ev_fha = [event_cell(days, arr, rd, events, h, b, "fha") for h in WINDOWS for b in BANDS]
    return days, slopes_va, slopes_fha, ev_va, ev_fha


# ---------------------------------------------------------------- self-test

def selftest():
    fails = []

    def ok(label, cond):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    rng = np.random.default_rng(7)
    n = 1500
    days = [f"2018-{1 + i // 120:02d}-{1 + (i % 120) // 5:02d}x{i}" for i in range(n)]  # sortable, 12 'months'
    t10 = np.cumsum(rng.normal(0, 0.05, n))
    conv = 4 + 0.8 * t10 + rng.normal(0, 0.03, n)
    flat = {"conv": conv, "va": conv - 0.3 + rng.normal(0, 0.03, n), "fha": conv - 0.2 + rng.normal(0, 0.03, n),
            "t2": t10, "t10": t10}
    loaded = dict(flat, va=conv - 0.3 - 0.25 * t10 + rng.normal(0, 0.03, n))
    ok("seed sanity: the loaded panel's VA really carries the 10-year", abs(np.corrcoef(loaded["va"] - loaded["conv"], t10)[0, 1]) > 0.5)
    for label, arr, want in (("flat spread reads inside the floor", flat, None), ("loaded spread reads B", loaded, True)):
        cells = [slope_cell(days, arr, [], h, b, "va") for h in WINDOWS for b in BANDS]
        ok("B156-3: " + label, read_slope_cells(cells)["verdict"] is want)
    flip = [{"h": 2, "band": 2, "slope": 0.1, "excludes_zero": True}, {"h": 5, "band": 2, "slope": -0.1, "excludes_zero": True}]
    ok("B156-3: a sign that moves over the knobs is not read", read_slope_cells(flip)["verdict"] is None)

    evs = [{"date": days[k].replace("-", "")[:8]} for k in (100, 400, 700, 1000, 1300)]
    for e, k in zip(evs, (100, 400, 700, 1000, 1300)):
        days[k] = iso(e["date"])
    days_s = days
    shocked = dict(flat, va=flat["va"].copy())
    for k in (100, 400, 700, 1000, 1300):
        shocked["va"][k:] += 0.4
    rel_dates = [e["date"] for e in evs]
    quiet = [event_cell(days_s, flat, rel_dates, evs, h, b, "va") for h in WINDOWS for b in BANDS]
    loud = [event_cell(days_s, shocked, rel_dates, evs, h, b, "va") for h in WINDOWS for b in BANDS]
    ok("B156-4: no event shift reads inside the floor", read_event_cells(quiet)[0]["verdict"] is None)
    ok("B156-4: a 40 bp event shift reads B", read_event_cells(loud)[0]["verdict"] is True)

    # the text rule and the file checks, on the real files with one thing broken each
    series, rel = load_series(RAW), releases(RAW)
    events, skipped = events_from_text(rel)
    events = [e for e in events if e["date"] >= EVENT_FIRST]
    days_r, sv, sf, ev, ef = measure(series, rel, events)
    good = build_criteria(series, rel, events, skipped, sv, sf, ev, ef)
    ok("real inputs: B156-1 passes", good[0]["passed"] is True)
    ok("real inputs: B156-2 passes", good[1]["passed"] is True)
    short = json.loads(json.dumps(series))
    short["va"]["n"] -= 7
    ok("B156-1: a truncated file is reported", build_criteria(short, rel, events, skipped, sv, sf, ev, ef)[0]["passed"] is False)
    broken = dict(rel)
    broken[next(iter(broken))] = None
    ok("B156-1: a release without its #article block is reported",
       build_criteria(series, broken, events, skipped, sv, sf, ev, ef)[0]["passed"] is False)
    thin = [e for e in events if e["date"] != LANDMARKS[0]]
    ok("B156-2: a list missing a landmark fails", build_criteria(series, rel, thin, skipped, sv, sf, ev, ef)[1]["passed"] is False)
    no_fha = [dict(c, rows=[]) for c in ef]
    ok("B156-5: an empty FHA event table fails", not build_criteria(series, rel, events, skipped, sv, sf, ev, no_fha)[4]["passed"])
    nan = [dict(c, slope=float("nan")) for c in sv]
    ok("B156-6: a knob point that did not compute fails",
       build_criteria(series, rel, events, skipped, nan, sf, ev, ef)[5]["passed"] is False)
    one = [dict(c, perm_p=c["perm_p"][:1]) for c in ev]
    ok("B156-7: a missing seed fails", build_criteria(series, rel, events, skipped, sv, sf, one, ef)[6]["passed"] is False)
    mnd = load_mnd()
    _, m_over = mnd_cells(series, mnd, list(rel), "2017-01-03", "9999")
    ok("real inputs: B156-8 computes", mnd_criterion(m_over, m_over, 1)["passed"] is True)
    ok("B156-8: an empty fixed-scenario panel fails", mnd_criterion([], [], 0)["passed"] is False)
    nan8 = [dict(c, slope=float("nan")) for c in m_over]
    ok("B156-8: a knob point that did not compute fails", mnd_criterion(nan8, m_over, 1)["passed"] is False)

    # second pass: overlapping windows and the 2009-2026 event cell
    for label, arr, want in (("flat spread reads inside the floor", flat, None), ("loaded spread reads B", loaded, True)):
        cells = [slope_cell(days_s, arr, [], h, b, "va", overlap=True) for h in WINDOWS for b in BANDS]
        ok("B156-9 (overlapping windows): " + label, read_slope_cells(cells)["verdict"] is want)
    ok("B156-9: overlapping windows keep more windows than non-overlapping",
       len(windows(days_s, flat, [], 10, 2, True)) > 5 * len(windows(days_s, flat, [], 10, 2)))
    all_ev, _ = events_from_text(rel)
    ok("event rule: the ten class-index events include 2018-01-31", "20180131" in [e["date"] for e in events])
    ndays, narr = mnd_panel(series, mnd, "2009-04-29", "9999")
    mev = [event_cell(ndays, narr, list(rel), all_ev, h, b, "fha") for h in (2,) for b in (2,)]
    sec = second_pass_criteria(m_over, m_over, m_over, mev)
    ok("real inputs: B156-11 passes with both early landmarks", sec[2]["passed"] is True)
    no_early = [e for e in all_ev if e["date"] != EARLY_LANDMARKS[0]]
    mev2 = [event_cell(ndays, narr, list(rel), no_early, 2, 2, "fha")]
    ok("B156-11: an event list missing 2011-08-09 fails", second_pass_criteria(m_over, m_over, m_over, mev2)[2]["passed"] is False)
    ok("B156-10: an empty overlapping panel fails", second_pass_criteria(m_over, [], m_over, mev)[1]["passed"] is False)
    ok("B156-9: no cells, no verdict", second_pass_criteria([], m_over, m_over, mev)[0]["passed"] is None)
    for m in MAPPING_11C:
        print("11c  %-38s -> %-30s verdict %s grid %s" % (m["state"], m["maps_to"], m["verdict"], m["grid"]))
    ok("11c: no undecided state carries a verdict", all(m["verdict"] is None for m in MAPPING_11C if m["grid"] == "unread"))
    print("selftest: %d failure(s)" % len(fails))
    return 1 if fails else 0


# ---------------------------------------------------------------- run

def cell_out(c):
    o = {k: (f6(v) if isinstance(v, float) else v) for k, v in c.items() if k not in ("rows", "perm_p")}
    if "perm_p" in c:
        o["perm_p"] = [f6(p) for p in c["perm_p"]]
    if "rows" in c:
        o["rows"] = [{k: (f6(v) if isinstance(v, float) else v) for k, v in r.items()} for r in c["rows"]]
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    series, rel = load_series(RAW), releases(RAW)
    all_events, skipped = events_from_text(rel)
    events = [e for e in all_events if e["date"] >= EVENT_FIRST]
    days, sv, sf, ev, ef = measure(series, rel, events)
    crits = build_criteria(series, rel, events, skipped, sv, sf, ev, ef)
    mnd = load_mnd()
    mdays, m_over = mnd_cells(series, mnd, list(rel), "2017-01-03", "9999")
    ldays, m_long = mnd_cells(series, mnd, list(rel), "2009-04-29", "2016-12-30")
    crits.append(mnd_criterion(m_over, m_long, len(mdays) + len(ldays)))
    pdays, parr = panel(series)
    va_ov = [slope_cell(pdays, parr, list(rel), h, b, "va", overlap=True) for h in WINDOWS for b in BANDS]
    _, m_over_ov = mnd_cells(series, mnd, list(rel), "2017-01-03", "9999", overlap=True)
    _, m_long_ov = mnd_cells(series, mnd, list(rel), "2009-04-29", "2016-12-30", overlap=True)
    ndays, narr = mnd_panel(series, mnd, "2009-04-29", "9999")
    # D51: at 2,000 draws the two-day p sat at 0.043 and 0.048, the seed gap wider than the distance to 0.05
    mnd_ev = [event_cell(ndays, narr, list(rel), all_events, h, b, "fha", draws=MND_EVENT_DRAWS) for h in WINDOWS for b in BANDS]
    crits.extend(second_pass_criteria(va_ov, m_over_ov, m_long_ov, mnd_ev))
    for e in all_events:
        print("event %s  -%d +%d sentences" % (e["date"], len(e["removed"]), len(e["added"])))
    for m in MAPPING_11C:
        print("11c  %-38s -> %-30s verdict %s" % (m["state"], m["maps_to"], m["verdict"]))
    failed = []
    for c in crits:
        print(("PASS   " if c["passed"] else ("VOID   " if c["passed"] is None else "FAILED[" + c["kind"] + "]: "))
              + c["name"] + "  " + c["detail"])
        if c["passed"] is False:
            failed.append(c["name"])
    rec = {
        "stage": "B156",
        "config": {"windows": list(WINDOWS), "bands": list(BANDS), "default_window": DEFAULT_H,
                   "default_band": DEFAULT_BAND, "draws": DRAWS, "seeds": list(SEEDS), "alpha": ALPHA,
                   "event_rule": {"path_regex": FUT.pattern, "action_regex": ACT.pattern, "hold_regex": HOLD.pattern,
                                  "path_object_regex": PATH_OBJECT.pattern},
                   "event_first_for_class_indices": EVENT_FIRST,
                   "series": SERIES, "first_day": days[0], "last_day": days[-1]},
        "events": events, "events_before_class_indices": [e for e in all_events if e["date"] < EVENT_FIRST], "skipped_releases": skipped,
        "slope_cells": {"va": [cell_out(c) for c in sv], "fha": [cell_out(c) for c in sf]},
        "event_cells": {"va": [cell_out(c) for c in ev], "fha": [cell_out(c) for c in ef]},
        "overlapping_window_cells": {"va": [cell_out(c) for c in va_ov], "mnd_fha_from_2017": [cell_out(c) for c in m_over_ov],
                                     "mnd_fha_2009_to_2016": [cell_out(c) for c in m_long_ov]},
        "mnd_event_cells": [cell_out(c) for c in mnd_ev],
        "mnd_fixed_scenario_cells": {"from_2017": [cell_out(c) for c in m_over], "2009_to_2016": [cell_out(c) for c in m_long],
                                     "source": "data/raw/b156/mnd/" + MND_FILE.name, "series": MND_NAMES},
        "mapping_11c": list(MAPPING_11C),
        "criteria": crits,
    }
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if not a.no_write:
        sys.path.insert(0, str(ROOT.parent))
        import safe_write  # noqa: E402
        if OUT.exists():
            safe_write.rewrite(OUT, "B156 record", lambda _old: text, session=SESSION)
        else:
            safe_write.create(OUT, "B156 record", text, session=SESSION)
        print("wrote %s (%d bytes)" % (OUT, len(text.encode("utf-8"))))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
