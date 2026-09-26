"""B115: the sorghum deposit of 2018 and its end, read as a term moved in place and moved back
(Corollary 43.6, Corollary 43.1).

One file, data/b115_sorghum_fob.json: the US Grains Council's weekly FOB tables for yellow corn
(Gulf, PNW) and sorghum (NOLA, Texas), 2016-01-07 to 2018-08-02, every cell with its issue, delivery
month, basis, futures month and flat price in US$ per tonne, and every issue with the PDF it was read
from.

The steps. From 2018-04-18 importers of US sorghum paid a 178.6% deposit (Ministry of Commerce
announcement 2018 No. 38, issued 04-17); on 2018-05-18 the investigations ended and the deposits were
refunded (No. 44). Both touch only the relation from US sorghum to China, and so does the
investigation opened on 02-04, which moved no term in force. Three other dated documents touch several
relations at once, and the path across them is printed, not read: 04-04 the list naming corn and
sorghum, 05-19 the joint statement on agricultural exports, 06-16 list one (in force 07-06).

Corollary 43.6 here. With only the term of e = (US sorghum -> China) moved, every potential moves by
w_e Delta u, and by Theorem 42 u is smallest at the US sorghum end, so every other position, the Gulf
corn price among them, moves up against sorghum: sorghum against Gulf corn moves by at most 0 at the
deposit and by at least 0 at its end. The end puts the written term back where it stood before the
deposit (Corollary 43.1). The plateau before the deposit lies inside the investigation, and a forward
FOB quote there can already carry part of the expected deposit, which the end takes away as well; so
the two steps together move sorghum against Gulf corn by at least 0, and by 0 only if the quotes
before the deposit carried none of it.

The reading. A level is ln(sorghum flat) - ln(Gulf corn flat) for one issue and one delivery month,
the halves of a month averaged in logs. Levels are chained issue to issue over the delivery months
both issues quote, so the roll of delivery months does not enter; two issues with no month in common
start a new segment of the path. A move is the mean of the path over one plateau minus its mean over
another. Four settings of the plateaus are read, and a state counts only when all four give it. Each
move is set against the same move over windows of the same shape on the Thursday grid 2016-01-07 to
2018-02-01 whose span holds no dated sorghum document; the floor is the larger of the quote grid and
the median absolute placebo move.

Two checks on the source, both computed from the cells: a cell whose basis and flat price put its
futures month more than a cent a bushel away from the median of its issue and futures month, and a
cell hung on a futures month that ends before its delivery month. Flagged cells are printed and not
used.

    python experiments/b115_sorghum_step.py              # print, and write the record
    python experiments/b115_sorghum_step.py --selftest   # offline, planted faults
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import statistics
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = REPO / "data" / "b115_sorghum_fob.json"
OUT = REPO / "results" / "b115_sorghum_step.json"

BU_PER_T = 1000 / 25.401172       # a corn or sorghum bushel is 56 lb
IDENTITY_TOL = 0.01               # US$ per bushel
PORTS = ("NOLA", "TEXAS")
COMPARE = ("corn", "GULF")
FUTURES_MONTH = {"H": 3, "K": 5, "N": 7, "U": 9, "Z": 12}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
P0 = ("2018-04-05", 2)
SETTINGS = {"A": {"P1": ("2018-04-19", 5), "P2": ("2018-05-24", 4)},
            "B": {"P1": ("2018-04-26", 4), "P2": ("2018-05-24", 4)},
            "C": {"P1": ("2018-04-19", 5), "P2": ("2018-05-31", 3)},
            "D": {"P1": ("2018-04-26", 4), "P2": ("2018-05-31", 3)}}
DEFAULT = "A"
GRID = ("2016-01-07", "2018-02-01")
COVER = ("2018-01-04", "2018-08-02")
KNOWN = {"port": "NOLA", "before": "2018-04-12", "after": "2018-04-19", "change": -0.04,
         "source": "International Grains Council, as cited by Hansen, Marchant, Zhang and Grant, Choices 33(2), "
                   "2018: the US Gulf sorghum export price fell by about 4% after the 18 April announcement"}
ORDER = 10.0
MOVES = {"deposit": ("P0", "P1"), "end": ("P1", "P2"), "cancel": ("P0", "P2")}
NAMES = {("NOLA", "deposit"): "B115-10", ("TEXAS", "deposit"): "B115-11", ("NOLA", "end"): "B115-12",
         ("TEXAS", "end"): "B115-13", ("NOLA", "cancel"): "B115-14", ("TEXAS", "cancel"): "B115-15"}

MATCH, MISS, NOT_READ = "matches", "does not match", "not read"
VERDICT = {MATCH: True, MISS: False, NOT_READ: None}
R_BELOW, R_ABOVE = "below minus its floor", "above its floor"
R_WITHIN, R_NO_FLOOR = "within its floor", "floor not measured"
R_GAP = "a plateau with no level, or the two plateaus on different segments of the path"
R_SPLIT = "the window settings do not give one state"
MAPPING = (
    ("B115-10, B115-11", "deposit: " + R_BELOW, MATCH),
    ("B115-10, B115-11", "deposit: " + R_ABOVE, MISS),
    ("B115-12, B115-13", "end: " + R_ABOVE, MATCH),
    ("B115-12, B115-13", "end: " + R_BELOW, MISS),
    ("B115-14, B115-15", "cancel: " + R_ABOVE, MATCH),
    ("B115-14, B115-15", "cancel: " + R_BELOW, MISS),
    ("any", R_WITHIN, NOT_READ),
    ("any", R_NO_FLOOR, NOT_READ),
    ("any", R_GAP, NOT_READ),
    ("any", R_SPLIT, NOT_READ),
)


# ---------------------------------------------------------------- dates and months

def day(s: str) -> date:
    return date.fromisoformat(s)


def thursdays(first: str, n: int) -> list[str]:
    d0 = day(first)
    if d0.weekday() != 3:
        raise ValueError(f"{first} is not a Thursday")
    return [(d0 + timedelta(days=7 * k)).isoformat() for k in range(n)]


def grid_between(lo: str, hi: str) -> list[str]:
    return thursdays(lo, (day(hi) - day(lo)).days // 7 + 1)


def first_day(thursday: str) -> str:
    """The first day an issue's prices can hold: the Friday after the issue before."""
    return (day(thursday) - timedelta(days=6)).isoformat()


def month_key(label: str) -> str:
    parts = label.split()
    if parts and parts[0] in ("FH", "LH"):
        parts = parts[1:]
    if len(parts) == 2 and parts[1].isdigit():
        parts = parts[:1]
    if len(parts) != 1 or parts[0] not in MONTHS:
        raise ValueError(f"not a delivery month: {label!r}")
    return parts[0]


# ---------------------------------------------------------------- the source

def source_flags(cells: list[dict]) -> dict[int, list[str]]:
    """Index of each flagged cell -> the reasons, computed from the cells."""
    flags = collections.defaultdict(list)
    groups = collections.defaultdict(list)
    for i, c in enumerate(cells):
        groups[(c["issue"], c["contract"])].append(i)
    for key in sorted(groups):
        idx = groups[key]
        fut = {i: cells[i]["flat"] / BU_PER_T - cells[i]["basis"] for i in idx}
        med = statistics.median(fut[i] for i in idx)
        for i in idx:
            if abs(fut[i] - med) > IDENTITY_TOL:
                flags[i].append(f"implied futures {fut[i] - med:+.4f} $/bu from the median of {len(idx)} cells")
    for i, c in enumerate(cells):
        ahead = (FUTURES_MONTH[c["contract"]] - (MONTHS.index(month_key(c["month"])) + 1)) % 12
        if ahead >= 6:
            flags[i].append(f"hung on {c['contract']}, which ends before {month_key(c['month'])}")
    return dict(flags)


def levels(cells: list[dict], port: str) -> dict[str, dict[str, float]]:
    logs = collections.defaultdict(list)
    for c in cells:
        if (c["chart"], c["port"]) in (("sorghum", port), COMPARE):
            logs[(c["issue"], c["chart"], month_key(c["month"]))].append(math.log(c["flat"]))
    out = collections.defaultdict(dict)
    for (issue, chart, m) in sorted(logs, key=lambda k: (k[0], k[1], MONTHS.index(k[2]))):
        if chart != "sorghum":
            continue
        corn = logs.get((issue, "corn", m))
        if corn:
            out[issue][m] = statistics.fmean(logs[(issue, chart, m)]) - statistics.fmean(corn)
    return dict(out)


def chain(lv: dict[str, dict[str, float]]) -> tuple[dict, list]:
    path, links, seg, prev = {}, [], -1, None
    for issue in sorted(i for i in lv if lv[i]):
        common = [m for m in MONTHS if prev is not None and m in lv[issue] and m in lv[prev]]
        if not common:
            seg += 1
            tau, step = statistics.fmean(lv[issue][m] for m in MONTHS if m in lv[issue]), None
        else:
            step = statistics.fmean(lv[issue][m] - lv[prev][m] for m in common)
            tau = path[prev]["tau"] + step
        path[issue] = {"tau": tau, "segment": seg}
        links.append({"from": prev, "to": issue, "months": common, "step": step, "segment": seg})
        prev = issue
    return path, links


# ---------------------------------------------------------------- moves and floors

def move(path: dict, pre_w: list[str], post_w: list[str]) -> dict | None:
    a = [path[w] for w in pre_w if w in path]
    b = [path[w] for w in post_w if w in path]
    if not a or not b or len({x["segment"] for x in a + b}) != 1:
        return None
    return {"move": statistics.fmean(x["tau"] for x in b) - statistics.fmean(x["tau"] for x in a),
            "pre_n": len(a), "post_n": len(b)}


def gap_weeks(pre_w: list[str], post_w: list[str]) -> int:
    return (day(post_w[0]) - day(pre_w[-1])).days // 7 - 1


def placebo(path: dict, grid: list[str], n_pre: int, gap: int, n_post: int, steps: list[str]):
    rows, stepped, thin = [], 0, 0
    span = n_pre + gap + n_post
    for k in range(len(grid) - span + 1):
        pre_w, post_w = grid[k:k + n_pre], grid[k + n_pre + gap:k + span]
        lo, hi = first_day(pre_w[0]), post_w[-1]
        if any(lo <= t <= hi for t in steps):
            stepped += 1
            continue
        m = move(path, pre_w, post_w)
        if m is None:
            thin += 1
            continue
        rows.append({"pre": [pre_w[0], pre_w[-1]], "post": [post_w[0], post_w[-1]], "span": [lo, hi], **m})
    return rows, stepped, thin


def quote_step(values) -> float | None:
    vs = sorted({round(v, 6) for v in values})
    gaps = [g for g in (round(b - a, 6) for a, b in zip(vs, vs[1:])) if g > 0]
    return min(gaps) if gaps else None


def quote_grids(cells: list[dict]) -> dict:
    def rel(vs):
        step = quote_step(vs) if vs else None
        med = statistics.median(vs) if vs else None
        return {"step": step, "median": med, "relative": step / med if step and med else 0.0}
    corn = rel([c["flat"] for c in cells if (c["chart"], c["port"]) == COMPARE])
    ports = {p: rel([c["flat"] for c in cells if (c["chart"], c["port"]) == ("sorghum", p)]) for p in PORTS}
    return {"corn": corn, "sorghum": ports, "moves": {p: ports[p]["relative"] + corn["relative"] for p in PORTS}}


def independent(rows: list[dict]) -> int:
    n, last = 0, ""
    for r in sorted(rows, key=lambda r: r["pre"][0]):
        if r["pre"][0] > last:
            n += 1
            last = r["post"][1]
    return n


def floor_of(obs: float | None, rows: list[dict], grid: float) -> dict:
    if not rows:
        return {"windows": 0, "floor": None}
    xs = [abs(r["move"]) for r in rows]
    med = statistics.median(xs)
    return {"windows": len(xs), "independent": independent(rows), "median_abs": med, "max_abs": max(xs), "grid": grid,
            "floor": max(grid, med), "placebo_at_least_as_large": None if obs is None else sum(1 for x in xs if x >= abs(obs))}


def read_state(kind: str, obs: dict | None, floor: float | None) -> tuple[str, str]:
    if obs is None:
        return NOT_READ, R_GAP
    if floor is None:
        return NOT_READ, R_NO_FLOOR
    m = obs["move"]
    if m < -floor:
        return (MATCH, R_BELOW) if kind == "deposit" else (MISS, R_BELOW)
    if m > floor:
        return (MISS, R_ABOVE) if kind == "deposit" else (MATCH, R_ABOVE)
    return NOT_READ, R_WITHIN


def one_state(states: dict) -> tuple[str, str]:
    if len({s[0] for s in states.values()}) == 1:
        return tuple(states[DEFAULT] if DEFAULT in states else next(iter(states.values())))
    return NOT_READ, R_SPLIT


# ---------------------------------------------------------------- the run

def known_answer(cells: list[dict]) -> dict:
    logs = collections.defaultdict(list)
    for c in cells:
        if (c["chart"], c["port"]) == ("sorghum", KNOWN["port"]) and c["issue"] in (KNOWN["before"], KNOWN["after"]):
            logs[(c["issue"], month_key(c["month"]))].append(math.log(c["flat"]))
    months = [m for m in MONTHS if (KNOWN["before"], m) in logs and (KNOWN["after"], m) in logs]
    ours = statistics.fmean(statistics.fmean(logs[(KNOWN["after"], m)]) - statistics.fmean(logs[(KNOWN["before"], m)])
                            for m in months) if months else None
    theirs = math.log(1 + KNOWN["change"])
    ratio = None if ours is None else ours / theirs
    return {"months": months, "ours": ours, "theirs": theirs, "ratio": ratio,
            "passed": ratio is not None and 1 / ORDER <= ratio <= ORDER}


def step_table(path: dict, steps: list[dict]) -> list[dict]:
    issues = sorted(path)
    out = []
    for s in steps:
        t = s["date"]
        before = [i for i in issues if i < t]
        after = [i for i in issues if i > t]
        row = {"date": t, "before": before[-1] if before else None, "after": after[0] if after else None}
        if row["before"] and row["after"] and path[row["before"]]["segment"] == path[row["after"]]["segment"]:
            row["change"] = path[row["after"]]["tau"] - path[row["before"]]["tau"]
        else:
            row["change"] = None
        out.append(row)
    return out


def run(data: dict, settings: dict = SETTINGS, move_grids: dict | None = None) -> dict:
    cells = data["cells"]
    steps = sorted(s["date"] for s in data["steps"])
    flags = source_flags(cells)
    usable = [c for i, c in enumerate(cells) if i not in flags]
    grid = grid_between(*GRID)
    qg = quote_grids(usable)
    mg = move_grids if move_grids is not None else qg["moves"]
    ports = {}
    for port in PORTS:
        lv = levels(usable, port)
        path, links = chain(lv)
        per = {}
        for k, st in settings.items():
            weeks = {"P0": thursdays(*P0), "P1": thursdays(*st["P1"]), "P2": thursdays(*st["P2"])}
            res = {}
            for mv, (a, b) in MOVES.items():
                pre_w, post_w = weeks[a], weeks[b]
                gap = gap_weeks(pre_w, post_w)
                obs = move(path, pre_w, post_w)
                rows, stepped, thin = placebo(path, grid, len(pre_w), gap, len(post_w), steps)
                fl = floor_of(obs and obs["move"], rows, mg[port])
                res[mv] = {"pre": [pre_w[0], pre_w[-1]], "post": [post_w[0], post_w[-1]], "gap_weeks": gap,
                           "observed": obs, "placebo": rows, "placebo_spanning_a_step": stepped,
                           "placebo_without_a_level": thin, "floor": fl,
                           "state": list(read_state(mv, obs, fl.get("floor")))}
            per[k] = res
        in2018 = [i for i in sorted(path) if COVER[0] <= i <= COVER[1]]
        ports[port] = {
            "settings": per,
            "segments": [{"start": x["to"], "after": x["from"]} for x in links if x["step"] is None],
            "path_2018": [{"issue": i, "tau": path[i]["tau"], "segment": path[i]["segment"], "levels": lv[i],
                           "link": next(({"from": x["from"], "months": x["months"], "step": x["step"]}
                                         for x in links if x["to"] == i), None)} for i in in2018],
            "issues_2018_without_a_level": [i for i in sorted({c["issue"] for c in cells})
                                            if COVER[0] <= i <= COVER[1] and i not in path],
            "steps": step_table(path, data["steps"]),
        }
    issues_cells = collections.Counter((c["issue"], c["chart"]) for c in cells)
    expected = [t for t in grid_between(*COVER) if t not in data.get("coverage", {}).get("no_issue", [])]
    plateau_weeks = sorted({w for st in settings.values() for w in thursdays(*P0) + thursdays(*st["P1"]) + thursdays(*st["P2"])})
    return {"steps": steps, "grid": [grid[0], grid[-1], len(grid)], "quote_grids": qg, "move_grids_used": mg,
            "flags": [{"issue": cells[i]["issue"], "chart": cells[i]["chart"], "port": cells[i]["port"],
                       "month": cells[i]["month"], "basis": cells[i]["basis"], "contract": cells[i]["contract"],
                       "flat": cells[i]["flat"], "why": w} for i, w in sorted(flags.items())],
            "cells": len(cells), "cells_used": len(usable),
            "coverage_2018": {"expected": expected, "plateau_weeks": plateau_weeks,
                              "missing": [t for t in expected if not (issues_cells[(t, "corn")] and issues_cells[(t, "sorghum")])],
                              "plateau_weeks_not_expected": [w for w in plateau_weeks if w not in expected]},
            "ports": ports, "known_answer": known_answer(usable)}


# ---------------------------------------------------------------- criteria

def f4(x) -> str:
    return "n/a" if x is None else f"{x:+.4f}"


def criteria_for(o: dict) -> list[dict]:
    cov = o["coverage_2018"]
    b8 = [f"no tables for {t}" for t in cov["missing"]] + [f"plateau week {w} is not an issue" for w in cov["plateau_weeks_not_expected"]]
    b9 = []
    for port, pv in o["ports"].items():
        for k, sv in pv["settings"].items():
            for mv, r in sv.items():
                if not r["placebo"]:
                    b9.append(f"{port} {k} {mv}: no placebo window")
                for p in r["placebo"]:
                    if any(p["span"][0] <= t <= p["span"][1] for t in o["steps"]):
                        b9.append(f"{port} {k} {mv}: window {p['span'][0]}..{p['span'][1]} spans a dated document")
    out = [
        {"name": "B115-8", "kind": "instrument", "passed": not b8,
         "statement": "every issue from 2018-01-04 to 2018-08-02 has cells in both tables, and every plateau week "
                      "of every setting is such an issue",
         "detail": f"{len(cov['expected'])} issues expected, {len(cov['plateau_weeks'])} plateau weeks"
                   + (": " + "; ".join(b8[:6]) if b8 else "")},
        {"name": "B115-9", "kind": "instrument", "passed": not b9,
         "statement": "no placebo window kept spans a dated sorghum document, and every port, setting and move has "
                      "placebo windows",
         "detail": "; ".join(f"{port} {k}: " + ", ".join(f"{mv} {len(r['placebo'])} kept ({r['floor'].get('independent')} "
                                                          f"apart), {r['placebo_spanning_a_step']} spanning a document, "
                                                          f"{r['placebo_without_a_level']} without a level"
                                                          for mv, r in sv.items())
                             for port, pv in o["ports"].items() for k, sv in pv["settings"].items() if k == DEFAULT)
                   + (": " + "; ".join(b9[:6]) if b9 else "")},
    ]
    words = {"deposit": ("the deposit moved sorghum down against Gulf corn: only the term of US sorghum to China "
                         "moved, and by Theorem 42 the potential of the US sorghum end is the lowest of all "
                         "(Corollary 43.6)"),
             "end": ("the end of the investigations moved sorghum back up against Gulf corn, the same reading "
                     "with the term moved the other way (Corollary 43.6)"),
             "cancel": ("from before the deposit to after its end sorghum against Gulf corn moved by at least 0: "
                        "the end took away the deposit, and with it whatever part of the deposit the forward quotes "
                        "before it already carried (Corollaries 43.1 and 43.6)")}
    for (port, mv), name in NAMES.items():
        sv = o["ports"][port]["settings"]
        s = one_state({k: tuple(v[mv]["state"]) for k, v in sv.items()})
        where = "NOLA" if port == "NOLA" else "Texas"
        out.append({"name": name, "kind": "own_reading", "passed": VERDICT[s[0]],
                    "statement": f"{where}: " + words[mv],
                    "detail": f"{s[0]} ({s[1]}); " + "; ".join(
                        f"{k}: {f4((v[mv]['observed'] or {}).get('move'))} against floor {f4(v[mv]['floor'].get('floor'))}"
                        f" -> {v[mv]['state'][0]}" for k, v in sv.items())})
    order = ["B115-8", "B115-9", "B115-10", "B115-11", "B115-12", "B115-13", "B115-14", "B115-15"]
    out.sort(key=lambda c: order.index(c["name"]))
    ka = o["known_answer"]
    out.append({"name": "B115-16", "kind": "known_answer", "passed": bool(ka["passed"]),
                "statement": f"the NOLA sorghum flat price from the {KNOWN['before']} issue to the {KNOWN['after']} issue, "
                             "over the delivery months both quote, has the sign of the fall of about 4% that the "
                             "International Grains Council reports for the US Gulf sorghum export price after the "
                             "announcement, and lies within one order of magnitude of it",
                "detail": f"{f4(ka['ours'])} over {ka['months']}, theirs {f4(ka['theirs'])}, ratio {f4(ka['ratio'])}"})
    return out


# ---------------------------------------------------------------- output

def fmt(x: float, digits: int = 6) -> float:
    return float(f"{x:.{digits}g}")


def public(x):
    if isinstance(x, float):
        return fmt(x, 6) if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): public(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [public(v) for v in x]
    return x


def show(o: dict, criteria: list[dict]) -> None:
    print(f"cells {o['cells']}, used {o['cells_used']}, flagged {len(o['flags'])}; Thursday grid "
          f"{o['grid'][0]}..{o['grid'][1]} ({o['grid'][2]} weeks)")
    for f in o["flags"]:
        print(f"  flagged {f['issue']} {f['chart']:7s} {f['port']:5s} {f['month']:13s} {f['basis']:+.2f} {f['contract']} "
              f"{f['flat']:.2f}: {'; '.join(f['why'])}")
    for port, pv in o["ports"].items():
        print(f"\n{port}: segments start at " + ", ".join(s["start"] for s in pv["segments"]))
        print(f"  2018 issues without a level: {pv['issues_2018_without_a_level'] or 'none'}")
        for r in pv["path_2018"]:
            lk = r["link"] or {}
            print(f"  {r['issue']}  tau {f4(r['tau'])}  seg {r['segment']}  link {f4(lk.get('step'))} over "
                  f"{','.join(m[:3] for m in lk.get('months') or []) or '-'}  levels "
                  + " ".join(f"{m[:3]} {v:+.4f}" for m, v in r["levels"].items()))
        print("  documents: " + "; ".join(f"{s['date']} {s['before']}->{s['after']} {f4(s['change'])}" for s in pv["steps"]))
        for k, sv in pv["settings"].items():
            print(f"  setting {k}:")
            for mv, r in sv.items():
                fl, ob = r["floor"], r["observed"] or {}
                print(f"    {mv:7s} {r['pre'][0]}..{r['pre'][1]} -> {r['post'][0]}..{r['post'][1]} gap {r['gap_weeks']}: "
                      f"{f4(ob.get('move'))} ({ob.get('pre_n')}+{ob.get('post_n')} issues)  floor {f4(fl.get('floor'))}"
                      f"  max {f4(fl.get('max_abs'))}  windows {fl.get('windows')} ({fl.get('independent')} apart), "
                      f"{fl.get('placebo_at_least_as_large')} as large  -> {r['state'][0]} ({r['state'][1]})")
    ka = o["known_answer"]
    print(f"\nknown answer: {f4(ka['ours'])} over {ka['months']}, theirs {f4(ka['theirs'])}, ratio {f4(ka['ratio'])}")
    print("\nmapping")
    for m in MAPPING:
        print(f"  {m[0]:17s} {m[1]:80s} -> {m[2]} -> {VERDICT[m[2]]}")
    print()
    for c in criteria:
        print(f"{c['name']} [{c['kind']}] {c['passed']}: {c['detail']}")


# ---------------------------------------------------------------- self-test

def synthetic(deposit=-0.06, end=0.06, end_from="2018-05-24", texas_shift=-0.02, texas_extra=0.0, extra_steps=(),
              drop_issues=(), no_issue=("2018-01-25",)):
    """Every Thursday 2016-01-07 to 2018-08-02 quotes the three delivery months after its own, for Gulf and PNW
    corn and NOLA and Texas sorghum, each cell on the identity. Sorghum against Gulf corn is a month offset (so
    the roll of delivery months would move a naive reading) plus the deposit from 2018-04-19 and the end from
    end_from."""
    cells = []
    for t in grid_between("2016-01-07", "2018-08-02"):
        if t in no_issue or t in drop_issues:
            continue
        d = day(t)
        for k in (1, 2, 3):
            mo = (d.month + k - 1) % 12 + 1
            month = MONTHS[mo - 1]
            contract = next((c for c, fm in sorted(FUTURES_MONTH.items(), key=lambda x: x[1]) if fm >= mo), "H")
            fut = 3.8 + 0.1 * FUTURES_MONTH[contract] / 12
            gulf = (fut + 0.5) * BU_PER_T
            cells.append({"issue": t, "chart": "corn", "port": "GULF", "month": month, "basis": 0.5, "contract": contract, "flat": gulf})
            cells.append({"issue": t, "chart": "corn", "port": "PNW", "month": month, "basis": 0.8, "contract": contract,
                          "flat": (fut + 0.8) * BU_PER_T})
            lvl = 0.01 * mo + (deposit if t >= "2018-04-19" else 0.0) + (end if t >= end_from else 0.0)
            for port, shift in (("NOLA", 0.0), ("TEXAS", texas_shift + (texas_extra if t >= "2018-04-19" else 0.0))):
                flat = gulf * math.exp(lvl + shift)
                cells.append({"issue": t, "chart": "sorghum", "port": port, "month": month,
                              "basis": flat / BU_PER_T - fut, "contract": contract, "flat": flat})
    steps = [{"date": s} for s in ("2018-02-04", "2018-04-04", "2018-04-18", "2018-05-18", "2018-05-19", "2018-06-16",
                                   "2018-07-06") + tuple(extra_steps)]
    return {"cells": cells, "steps": steps, "coverage": {"no_issue": list(no_issue)}}


def selftest() -> int:
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    def close(a, b, tol=1e-9):
        return a is not None and b is not None and abs(a - b) <= tol

    def passed(o):
        return {c["name"]: c["passed"] for c in criteria_for(o)}

    tiny = {p: 1e-9 for p in PORTS}   # a quote grid is never zero; exact worlds leave rounding near 1e-16

    for label, want in (("LH June", "June"), ("FH April", "April"), ("March 25", "March"), ("December", "December")):
        expect(month_key(label) == want, f"the delivery month of {label!r} is misread")
    for label in ("Foo", "LH", "June 2 3", "Late June"):
        try:
            month_key(label)
            expect(False, f"{label!r} is read as a delivery month")
        except ValueError:
            pass
    try:
        thursdays("2018-04-18", 2)
        expect(False, "a plateau starting on a Wednesday passes")
    except ValueError:
        pass
    expect(first_day("2018-04-19") == "2018-04-13" and len(grid_between("2016-01-07", "2018-02-01")) == 109,
           "the week of an issue or the Thursday grid is miscounted")

    def cell(issue, chart, port, month, basis, contract, flat):
        return {"issue": issue, "chart": chart, "port": port, "month": month, "basis": basis, "contract": contract, "flat": flat}
    fut = 3.9
    small = [cell("2018-04-05", "corn", "GULF", "May", 0.5, "K", (fut + 0.5) * BU_PER_T),
             cell("2018-04-05", "corn", "PNW", "May", 0.8, "K", (fut + 0.8) * BU_PER_T),
             cell("2018-04-05", "sorghum", "NOLA", "May", 1.0, "K", (fut + 1.0) * BU_PER_T),
             cell("2018-04-05", "sorghum", "TEXAS", "May", 0.9, "K", (fut + 0.9 + 0.02) * BU_PER_T),
             cell("2018-04-05", "corn", "GULF", "June", 0.4, "N", (fut + 0.4) * BU_PER_T),
             cell("2018-04-05", "corn", "PNW", "June", 0.7, "N", (fut + 0.7 + 0.03) * BU_PER_T),
             cell("2018-04-05", "sorghum", "NOLA", "LH July", 0.8, "K", (fut + 0.8) * BU_PER_T),
             cell("2018-04-05", "sorghum", "TEXAS", "December", 0.8, "H", (fut + 0.8) * BU_PER_T),
             cell("2018-04-05", "sorghum", "TEXAS", "LH March", 0.8, "K", (fut + 0.8) * BU_PER_T)]
    fl = source_flags(small)
    expect(sorted(fl) == [3, 4, 5, 6], f"the source checks flag the wrong cells: {sorted(fl)}")
    expect(len(fl.get(6, [])) == 1 and "ends before" in fl[6][0], "a July quote hung on May futures is not flagged for it")

    two = [cell("2018-04-05", "corn", "GULF", "May", 0.5, "K", 180.0), cell("2018-04-05", "corn", "GULF", "LH May", 0.5, "K", 182.0),
           cell("2018-04-05", "corn", "PNW", "May", 0.8, "K", 190.0),
           cell("2018-04-05", "sorghum", "NOLA", "May", 1.0, "K", 200.0), cell("2018-04-05", "sorghum", "NOLA", "June", 1.0, "N", 210.0)]
    lv = levels(two, "NOLA")
    expect(list(lv) == ["2018-04-05"] and list(lv["2018-04-05"]) == ["May"]
           and close(lv["2018-04-05"]["May"], math.log(200.0) - (math.log(180.0) + math.log(182.0)) / 2),
           "halves of a month are not averaged in logs, PNW enters, or a month without Gulf corn gets a level")

    lvx = {"2018-01-04": {"January": 0.01, "February": 0.02},
           "2018-01-11": {"February": 0.02, "March": 0.03},
           "2018-01-18": {"March": 0.03 + 0.05, "April": 0.04 + 0.07},
           "2018-02-01": {"June": 0.5}}
    px, links = chain(lvx)
    expect(close(px["2018-01-04"]["tau"], 0.015) and close(px["2018-01-11"]["tau"], 0.015) and close(px["2018-01-18"]["tau"], 0.065),
           "the path does not chain over the months two issues share")
    expect(px["2018-02-01"]["segment"] == 1 and px["2018-01-18"]["segment"] == 0 and links[-1]["step"] is None,
           "two issues with no month in common do not start a new segment")
    expect(move(px, ["2018-01-04", "2018-01-11"], ["2018-01-18"]) == {"move": 0.065 - 0.015, "pre_n": 2, "post_n": 1}
           or close(move(px, ["2018-01-04", "2018-01-11"], ["2018-01-18"])["move"], 0.05), "a plateau move is misread")
    expect(move(px, ["2018-01-18"], ["2018-02-01"]) is None, "a move across two segments is read")
    expect(move(px, ["2018-01-25"], ["2018-02-01"]) is None, "a plateau with no level is read")

    rows = [{"move": 0.1, "pre": ["2016-01-07", "2016-01-14"], "post": ["2016-02-04", "2016-02-11"]},
            {"move": -0.2, "pre": ["2016-01-14", "2016-01-21"], "post": ["2016-02-11", "2016-02-18"]},
            {"move": 0.3, "pre": ["2016-03-03", "2016-03-10"], "post": ["2016-03-24", "2016-03-31"]},
            {"move": 0.05, "pre": ["2016-03-31", "2016-04-07"], "post": ["2016-04-28", "2016-05-05"]}]
    f = floor_of(0.25, rows, 0.5)
    expect(close(f["median_abs"], 0.15) and close(f["max_abs"], 0.3) and f["floor"] == 0.5 and f["placebo_at_least_as_large"] == 1,
           "the floor is not the larger of the grid and the median placebo move")
    expect(floor_of(0.25, rows, 0.0)["floor"] == f["median_abs"] and floor_of(0.1, [], 0.1)["floor"] is None,
           "the median placebo move is not the floor, or no window gives one")
    expect(independent(rows) == 2, "overlapping placebo windows are counted as apart")

    ob = lambda m: {"move": m, "pre_n": 1, "post_n": 1}
    expect(read_state("deposit", ob(-0.2), 0.2) == (NOT_READ, R_WITHIN) and read_state("deposit", ob(-0.21), 0.2) == (MATCH, R_BELOW)
           and read_state("deposit", ob(0.21), 0.2) == (MISS, R_ABOVE), "the deposit is misread at its floor")
    expect(read_state("end", ob(0.2), 0.2) == (NOT_READ, R_WITHIN) and read_state("end", ob(0.21), 0.2) == (MATCH, R_ABOVE)
           and read_state("end", ob(-0.21), 0.2) == (MISS, R_BELOW), "the end is misread at its floor")
    expect(read_state("cancel", ob(0.2), 0.2) == (NOT_READ, R_WITHIN) and read_state("cancel", ob(0.21), 0.2) == (MATCH, R_ABOVE)
           and read_state("cancel", ob(-0.21), 0.2) == (MISS, R_BELOW), "the two steps together are misread at their floor")
    expect(read_state("deposit", None, 0.2) == (NOT_READ, R_GAP) and read_state("cancel", ob(0.0), None) == (NOT_READ, R_NO_FLOOR),
           "a missing level or a missing floor is read")
    expect(one_state({"A": (MATCH, R_BELOW), "B": (MATCH, R_BELOW)}) == (MATCH, R_BELOW)
           and one_state({"A": (MATCH, R_ABOVE), "B": (NOT_READ, R_WITHIN)}) == (NOT_READ, R_SPLIT),
           "settings that disagree give a state")
    for group, how, state in MAPPING:
        if group == "any":
            expect(VERDICT[state] is None, f"the not-read row '{how}' points at a verdict")
        else:
            expect(VERDICT[state] in (True, False), f"the row '{group} {how}' gives no verdict")
    expect({m[1] for m in MAPPING if m[0] == "any"} == {R_WITHIN, R_NO_FLOOR, R_GAP, R_SPLIT},
           "a not-read reason in the mapping is never produced")

    # the whole reading on an exact world
    world = synthetic()
    base = run(world, move_grids=tiny)
    c = passed(base)
    want = {"B115-8": True, "B115-9": True, "B115-10": True, "B115-11": True, "B115-12": True, "B115-13": True,
            "B115-14": None, "B115-15": None, "B115-16": True}
    expect(c == want, f"the criteria of the exact world are misread: {c}")
    for port in PORTS:
        for k, sv in base["ports"][port]["settings"].items():
            expect(close(sv["deposit"]["observed"]["move"], -0.06) and close(sv["end"]["observed"]["move"], 0.06)
                   and close(sv["cancel"]["observed"]["move"], 0.0), f"{port} {k}: the moves of an exact world are misread")
            expect(all(abs(r["move"]) < 1e-9 for mv in MOVES for r in sv[mv]["placebo"]) and all(sv[mv]["placebo"] for mv in MOVES),
                   f"{port} {k}: a placebo window on a flat path moves, or none is kept")
    expect({k: [v[mv]["gap_weeks"] for mv in MOVES] for k, v in base["ports"]["NOLA"]["settings"].items()}
           == {"A": [0, 0, 5], "B": [1, 0, 5], "C": [0, 1, 6], "D": [1, 1, 6]}, "the weeks between the plateaus are miscounted")
    expect(not base["flags"] and not base["ports"]["NOLA"]["segments"][1:], "an exact world has flags or a broken path")
    expect(close(base["known_answer"]["ours"], -0.06) and base["known_answer"]["months"], "the known answer is misread")
    expect(json.dumps(public(base), sort_keys=True) == json.dumps(public(run(synthetic(), move_grids=tiny)), sort_keys=True),
           "two runs on one world differ")

    c = passed(run(synthetic(deposit=0.05, end=-0.05), move_grids=tiny))
    expect(c["B115-10"] is False and c["B115-12"] is False and c["B115-14"] is None and c["B115-16"] is False,
           f"sorghum rising at the deposit is read as matching: {c}")
    c = passed(run(synthetic(end=0.08), move_grids=tiny))
    expect(c["B115-12"] is True and c["B115-14"] is True and c["B115-15"] is True,
           f"an end that takes away more than the deposit is not read as the two steps together moving up: {c}")
    c = passed(run(synthetic(end=0.03), move_grids=tiny))
    expect(c["B115-12"] is True and c["B115-14"] is False and c["B115-15"] is False, f"an end that does not undo the deposit cancels: {c}")
    wide = {p: 0.05 for p in PORTS}
    split = run(synthetic(end_from="2018-05-31"), move_grids=wide)
    got = {k: v["end"]["state"][0] for k, v in split["ports"]["NOLA"]["settings"].items()}
    expect(got == {"A": NOT_READ, "B": NOT_READ, "C": MATCH, "D": MATCH}, f"the settings are not read one by one: {got}")
    c = passed(split)
    expect(c["B115-12"] is None and c["B115-10"] is True and c["B115-14"] is None, f"settings that disagree give a verdict: {c}")

    hole = synthetic()
    hole["cells"] = [x for x in hole["cells"] if not (x["issue"] in ("2018-04-05", "2018-04-12") and (x["chart"], x["port"]) == COMPARE)]
    o = run(hole, move_grids=tiny)
    c = passed(o)
    expect(c["B115-8"] is True and c["B115-10"] is None and c["B115-14"] is None and c["B115-12"] is True,
           f"a plateau without Gulf corn is read, or the PNW table is not enough for coverage: {c}")
    expect(o["ports"]["NOLA"]["settings"]["A"]["deposit"]["state"] == [NOT_READ, R_GAP], "a plateau with no level is not named")
    expect(passed(run(synthetic(drop_issues=("2018-05-03",)), move_grids=tiny))["B115-8"] is False, "a missing plateau issue passes")
    expect(passed(run(synthetic(drop_issues=("2018-07-19",)), move_grids=tiny))["B115-8"] is False, "a missing 2018 issue passes")
    expect(passed(run(synthetic(no_issue=("2018-01-25", "2018-07-19")), move_grids=tiny))["B115-8"] is True,
           "a week with no issue at all fails the coverage")
    expect(passed(run(synthetic(no_issue=("2018-01-25", "2018-05-03")), move_grids=tiny))["B115-8"] is False,
           "a plateau week with no issue passes")
    nosorg = synthetic()
    nosorg["cells"] = [x for x in nosorg["cells"] if not (x["issue"] == "2018-06-28" and x["chart"] == "sorghum")]
    expect(passed(run(nosorg, move_grids=tiny))["B115-8"] is False, "an issue without its sorghum table passes")
    st = {s["date"]: s for s in base["ports"]["NOLA"]["steps"]}
    expect(st["2018-04-18"]["before"] == "2018-04-12" and st["2018-04-18"]["after"] == "2018-04-19"
           and close(st["2018-04-18"]["change"], -0.06) and st["2018-05-19"]["before"] == "2018-05-17"
           and st["2018-05-19"]["after"] == "2018-05-24" and close(st["2018-05-18"]["change"], 0.06),
           "the path across a dated document is misread")
    qg = quote_grids([cell("2018-04-05", "corn", "GULF", "May", 0.5, "K", 100.00), cell("2018-04-12", "corn", "GULF", "May", 0.5, "K", 100.02),
                      cell("2018-04-05", "sorghum", "NOLA", "May", 0.5, "K", 200.00), cell("2018-04-12", "sorghum", "NOLA", "May", 0.5, "K", 200.05),
                      cell("2018-04-19", "sorghum", "NOLA", "May", 0.5, "K", 200.06)])
    expect(close(qg["corn"]["relative"], 0.02 / 100.01) and close(qg["sorghum"]["NOLA"]["relative"], 0.01 / 200.05)
           and close(qg["moves"]["NOLA"], 0.02 / 100.01 + 0.01 / 200.05) and qg["moves"]["TEXAS"] == qg["corn"]["relative"],
           "the quote grid of a move is misread")
    o = run(synthetic(texas_extra=-0.5), move_grids=tiny)
    c = passed(o)
    expect(close(o["known_answer"]["ours"], -0.06) and c["B115-11"] is True and c["B115-10"] is True
           and close(o["ports"]["TEXAS"]["settings"]["A"]["deposit"]["observed"]["move"], -0.56),
           "the ports are not read apart, or the known answer reads another port")

    bad = synthetic()
    k = next(i for i, x in enumerate(bad["cells"]) if x["issue"] == "2018-04-26" and (x["chart"], x["port"]) == COMPARE and x["month"] == "June")
    bad["cells"][k] = dict(bad["cells"][k], flat=bad["cells"][k]["flat"] * 1.02)
    o = run(bad, move_grids=tiny)
    expect([(x["issue"], x["month"]) for x in o["flags"]] == [("2018-04-26", "June")] and passed(o)["B115-10"] is True
           and close(o["ports"]["NOLA"]["settings"]["A"]["deposit"]["observed"]["move"], -0.06),
           "a Gulf flat off its identity is used, or flagging it moves the reading")

    o = run(synthetic(extra_steps=("2017-06-15",)), move_grids=tiny)
    r = o["ports"]["TEXAS"]["settings"]["A"]["cancel"]
    expect(r["placebo_spanning_a_step"] == 11 and not any(x["span"][0] <= "2017-06-15" <= x["span"][1] for x in r["placebo"]),
           f"a window across a dated document is kept ({r['placebo_spanning_a_step']} left out)")
    row = next(s for s in o["ports"]["TEXAS"]["steps"] if s["date"] == "2017-06-15")
    expect(row["before"] == "2017-06-08" and row["after"] == "2017-06-22",
           "an issue dated on the day of a document is put on one side of it")
    expect(passed(run(synthetic(deposit=-0.9, end=0.9), move_grids=tiny))["B115-16"] is False,
           "a fall twenty times the known answer passes")

    doctored = json.loads(json.dumps(base))
    rr = doctored["ports"]["NOLA"]["settings"]["C"]["end"]["placebo"]
    rr.append(dict(rr[0], span=["2018-05-01", "2018-06-01"]))
    expect(passed(doctored)["B115-9"] is False, "a placebo window across a dated document passes")
    doctored = json.loads(json.dumps(base))
    doctored["ports"]["TEXAS"]["settings"]["B"]["cancel"]["placebo"] = []
    expect(passed(doctored)["B115-9"] is False, "a move with no placebo window passes")

    for what in fails:
        print(f"SELFTEST FAIL  {what}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    o = run(data)
    criteria = criteria_for(o)
    show(o, criteria)
    record = {
        "stage": "B115",
        "config": {"data": "data/b115_sorghum_fob.json", "bu_per_t": BU_PER_T, "identity_tolerance_usd_bu": IDENTITY_TOL,
                   "ports": PORTS, "compare": COMPARE, "p0": P0, "settings": SETTINGS, "default_setting": DEFAULT,
                   "placebo_grid": GRID, "coverage_2018": COVER, "known_answer": KNOWN, "order_of_magnitude": ORDER,
                   "moves": MOVES, "steps": o["steps"],
                   "floor": "the larger of the quote grid and the median absolute move over placebo windows of the same shape"},
        "mapping": MAPPING,
        "criteria": criteria,
        "objects": o,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(public(record), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nrecord {OUT.relative_to(REPO)}")
    return 0 if all(c["passed"] is not False for c in criteria if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    raise SystemExit(main())
