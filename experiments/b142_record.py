"""B142, the record: what was kept by b142_reading.py, put together and scored.

    python experiments/b142_reading.py --run          builds results/b142_relaxation.json
    python experiments/b142_reading.py --selftest
    python experiments/b142_record.py --import-plant DIR

Nothing is sampled here. Every number in the record was read by a job of b142_reading.py and
kept; this file loads the carriers once, to know which cells there should be and to refuse a
kept file made from other data, and then only reads what is kept. A cell whose job has not run
is listed as not run and the record says it is not complete.

--import-plant reads the printed output of `b142_relaxation.py --plant [--formal]` and keeps each
cell's capacity line next to the others. Those runs are seeded, so the calibration jobs of
b142_reading.py reproduce them; importing saves running them twice.

Two quantities, kept apart everywhere. Reading one is where a series' centre stands against
zero. Reading two is whether it comes back to that centre, and how fast. A cell's state on
reading two is one of five: above, inside, below, marginal, unread. The last two carry no
verdict, and a criterion that needs such a cell is itself undecided: its flag is None.

There is no criterion on a rival's prediction. A scalar price field says every loop sum is zero
at all times, so it has no object for what happens after a loop sum has moved away; and this
framework makes no opposite point prediction in that cell. The sentence is carried in the detail
of B142-4.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

EXP = Path(__file__).resolve().parent
if str(EXP) not in sys.path:
    sys.path.insert(0, str(EXP))
import b142_relaxation as m  # noqa: E402
import b142_reading as R  # noqa: E402

VERDICT = ("above", "inside", "below")
INF = float("inf")
B97_TICK = 0.005

RIVAL_SENTENCE = ("No criterion is hung on a rival here. A scalar price field says every loop sum is zero at all "
                  "times, so it has no object for what a loop sum does after it has moved away, and this framework "
                  "makes no opposite point prediction in that cell.")

# ---------------------------------------------------------------------------------------------
# crossing types, read from each station's own rule text
#   A  someone crosses for others and the cost of crossing is published
#   B  someone crosses for others and the cost is not published
#   C  a third party keeps the two classes apart and nobody can cross
# ---------------------------------------------------------------------------------------------

TYPES = [
    {"line": "B9", "tag": "B9", "type": {"*": "A"},
     "source": "docs/b9_zero_holonomy.md, the edge table and section 16.4 (Select Sector SPDR Trust SAI)",
     "quote": "a fixed creation transaction fee of $500 for each Fund"},
    {"line": "B3", "tag": "B3", "type": {"*": "B"},
     "source": "docs/b3_slice_availability.md, section 7",
     "quote": "shadow price of balance-sheet capacity"},
    {"line": "B5 control", "tag": "B5", "arm": "control", "type": {"*": "B"},
     "source": "docs/b5_orphan_prereg.md, section 2.1",
     "quote": "anyone with a domestic brokerage account"},
    {"line": "B5 treated", "tag": "B5", "arm": "treated", "type": {"*": "C", "from 2025-04-14": "B", "whole window": "C"},
     "source": "docs/b5_orphan_prereg.md, sections 2.1 and 3.2b",
     "quote": "formerly a USD 200 monthly cap",
     "tie": "none: the official rate is written by the party that draws the graph"},
    {"line": "B97 Cyprus", "tag": "B97", "arm": "squares, CY against the euro area",
     "type": {"*": "B", "edge cut": "C", "whole window": "C"},
     "source": "experiments/b97_edge_restoration.py, RELAXATIONS and CUT",
     "quote": "every remaining external and payment restriction is lifted",
     "tie": "none while the edge is cut: the restrictions are written by decree"},
    {"line": "B97 controls", "tag": "B97", "arm_not": "squares, CY against the euro area", "type": {"*": "B"},
     "source": "experiments/b97_edge_restoration.py, CONTROLS; Greece is read to 2015-05",
     "quote": "every remaining external and payment restriction is lifted"},
    {"line": "B21", "tag": "B21", "type": {"*": "C"},
     "source": "experiments/b24_fungibility.py, opening note; experiments/b21_dropoff.py, opening note",
     "quote": "A and H shares cannot be exchanged for one another at any",
     "tie": "one anchor each class values where it stands: the same company declares one dividend"},
    {"line": "B52", "tag": "B52", "type": {"*": "C"},
     "source": "docs/b52_prereg.md, opening; Eurostat, Electricity price statistics (Statistics Explained)",
     "quote": "arrive through a metered network, so a household cannot",
     "tie": "one anchor each class's supplier values where it stands: both prices 'include the basic price of "
            "electricity, transmission and distribution charges'; the charges and taxes laid on top are written "
            "per class by the party that draws the graph"},
]

# The lines of the cross-carrier table: (tag, arm, span). One row each.
CROSS_ROWS = [
    ("B9", "main arm", "whole window"), ("B9", "comparison arm", "whole window"),
    ("B3", "g10", "whole window"), ("B3", "eme", "whole window"),
    ("B5", "control", "whole window"), ("B5", "treated", "before 2025-04-14"), ("B5", "treated", "from 2025-04-14"),
    ("B97", "squares, CY against the euro area", "before the cut"),
    ("B97", "squares, CY against the euro area", "edge cut"),
    ("B97", "squares, CY against the euro area", "edge restored"),
    ("B97", "squares, CY against the euro area", "later"),
    ("B97", "squares, GR against the euro area", "whole window"),
    ("B97", "squares, SI against the euro area", "whole window"),
    ("B97", "squares, MT against the euro area", "whole window"),
    ("B97", "squares, PT against the euro area", "whole window"),
    ("B97", "squares, IE against the euro area", "whole window"),
    ("B21", R.B21_ARM, "whole window"), ("B21", R.B21_ARM, "before own Connect opening"),
    ("B21", R.B21_ARM, "from own Connect opening"),
    ("B52", "class square, I_TAX", "whole window"),
]
RANKED = ("B9", "B3", "B5", "B52", "B97", "B21")


def type_line(types, tag, arm):
    for t in types:
        if t["tag"] != tag:
            continue
        if "arm" in t and t["arm"] != arm:
            continue
        if "arm_not" in t and t["arm_not"] == arm:
            continue
        return t
    return None


def line_complete(t):
    return bool(t and t.get("type") and all(t["type"].values()) and t.get("source") and t.get("quote"))


def type_of(types, tag, arm, seg):
    t = type_line(types, tag, arm)
    if not line_complete(t):
        return None
    return t["type"].get(seg, t["type"]["*"])


# ---------------------------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------------------------

def fixed(o):
    """Every float through one explicit format, so that two machines write the same text."""
    if isinstance(o, dict):
        return {str(k): fixed(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [fixed(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        x = float(o)
        if x != x or x in (INF, -INF):
            return None
        return float(f"{x:.6g}")
    return o


# ---------------------------------------------------------------------------------------------
# the printed output of --plant, kept as capacity lines
# ---------------------------------------------------------------------------------------------

def parse_plant(text):
    lines = text.splitlines()
    tag = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("== "):
            tag = ln[3:].strip()
        mt = re.match(r"   (.+?) \| (.+?) \| (\w): (.*)$", ln)
        if mt and tag:
            arm, seg, f, rest = mt.groups()
            c = {"tag": tag, "arm": arm, "seg": seg, "freq": f}
            if rest.startswith("not readable"):
                c.update(state="unread", reason=rest.split(": ", 1)[1] if ": " in rest else rest)
                yield c
            else:
                ideal = re.search(r"ideal reach in steps \[(.*?)\]", lines[i + 1])
                body = lines[i + 2]
                free, _, planted = body.partition(" | ")
                fm = re.search(r"no force, (\d+) panels: positions (\S+) / (\S+) / (\S+) .*?over the line (\d+), "
                               r"under (\d+)", free)
                st = lambda s: {k: int(v) for k, v in re.findall(r"(above|inside|below|marginal|unread) (\d+)", s)}
                c.update(state="read",
                         ideal_separable=[int(x[:-1]) for x in ideal.group(1).split() if x.endswith("+")],
                         free={"panels": int(fm.group(1)), "min": float(fm.group(2)), "median": float(fm.group(3)),
                               "max": float(fm.group(4)), "over_line": int(fm.group(5)), "under_line": int(fm.group(6))})
                if "whole reading:" in free:
                    c["free_held"] = st(free.split("whole reading:")[1])
                c["planted"] = []
                for part in re.split(r"; (?=half-life )", re.sub(r"\s+\(\d+\.\d+s\)\s*$", "", planted)):
                    pm = re.match(r"half-life (\d+): over the line (\d+), over every no-force panel (\d+), of (\d+)"
                                  r"(?:; whole reading: (.*))?", part)
                    if pm:
                        row = {"half_life": int(pm.group(1)), "over_line": int(pm.group(2)),
                               "over_every_free_panel": int(pm.group(3)), "panels": int(pm.group(4))}
                        if pm.group(5):
                            row["held"] = st(pm.group(5))
                        c["planted"].append(row)
                yield c
                i += 2
        i += 1


def import_plant(directory) -> int:
    n = 0
    for f in sorted(Path(directory).glob("*.txt")):
        for c in parse_plant(f.read_text(encoding="utf-8")):
            seg = c["seg"]
            if c["tag"] == "B21" and seg != "whole window":
                seg = f"FX span, {seg}"
            key = R.cell_key(c["tag"], c["arm"], seg, c["freq"])
            R.save(R.cache_path("calimport", key),
                   {"version": R.VERSION, "kind": "calimport", "key": key, "from": f.name}, c)
            n += 1
    print(f"{n} capacity lines kept")
    return 0


# ---------------------------------------------------------------------------------------------
# one cell, from what is kept
# ---------------------------------------------------------------------------------------------

HELD_KEYS = ("state", "state_on_the_line", "reason", "observed", "back", "away", "n", "units", "units_read",
             "units_too_short", "median_length", "eligible_blocks", "nulls", "strict_null", "strict_mean",
             "floor_from", "floor_sd", "gap", "floor", "position", "draws", "second_seed", "free_positions",
             "free_requested", "rung_on_own_steps", "rung_gaussian", "resolvable", "not_resolvable",
             "marginal_rungs", "ladder_block", "ladder_on_own_steps", "ladder_gaussian", "padded_share",
             "trend_blocks_not_eligible", "step_acf1_median", "step_acf1_negative", "step_acf1_units")


def capacity(kind, src, d, step_days):
    """One capacity line in one shape, whatever it was read from."""
    if d is None:
        return {"kind": "none"}
    if d.get("state") == "unread":
        return {"kind": kind, "from": src, "state": "unread", "reason": d.get("reason")}
    seen = d.get("ideal_separable", [])
    out = {"kind": kind, "from": src, "state": "read", "ideal_separable": seen,
           "ideal_reach_days": (max(seen) * step_days) if (seen and step_days) else None,
           "free": d.get("free"), "free_held": d.get("free_held"),
           "planted": [dict(p, days=(p["half_life"] * step_days) if step_days else None) for p in d.get("planted", [])]}
    if d.get("missing"):
        out["missing"] = d["missing"]
    return out


def knob_flips(state, knob):
    """True when the far-point quantile, moved to one half or four fifths, puts the cell on the other side."""
    if not knob or state not in ("above", "below"):
        return False
    other = "below" if state == "above" else "above"
    return any(v.get("state") == other for v in knob.values())


def build_cell(cells, key, cache=None):
    c = cells.cells[key]
    units, freq = c["units"], c["freq"]
    pts = R.points_of(units)
    k = R.k_for(c["tag"], freq, pts)
    reps = R.REPS_SMALL if pts <= R.BIG else R.REPS_BIG
    out = {"tag": c["tag"], "arm": c["arm"], "span": c["seg"], "freq": freq, "variant": c["variant"], "run": True}
    kind = "desc" if c["variant"] == "describe" else "read"
    got = R.load(R.cache_path(kind, key, cache=cache),
                 R.base_config(kind, key, units, **({"k": k} if kind == "read" else {})))
    if got is None:
        out.update(run=False, state="unread", reason="not run")
        return out
    out.update(shape=got["shape"], centre=got["centre"], steps=got["steps"], profile=got["profile"])
    if kind == "desc":
        return out
    h = got["held"]
    out["held"] = {kk: h[kk] for kk in HELD_KEYS if kk in h}
    out["k"] = got["k"]
    out["state"] = h["state"]
    if "common" in got:
        out["common"] = got["common"]
    sd = got["shape"]["step_days"]
    if c["flags"].get("knob") and c["variant"] == "raw":
        kn = R.load(R.cache_path("knob", key, cache=cache), R.base_config("knob", key, units, knob_q=list(R.KNOB_Q)))
        out["knob"] = kn
        if kn is None:
            out["knob_run"] = False
        elif knob_flips(out["state"], kn):
            out.update(state="unread", reason="the side flips when the far-point quantile is moved; not read",
                       state_before_the_knob=h["state"])
    # capacity: the whole-reading calibration if it is finished, else a single-seed trial
    if c["variant"] != "raw" or c["flags"].get("borrow"):
        seg = c["flags"].get("borrow", c["seg"])
        out["range"] = {"kind": "borrowed", "from": R.cell_key(c["tag"], c["arm"], seg, freq)}
        return out
    cap = None
    hcfg = R.base_config("calhead", key, units, k=k)
    head = R.load(R.cache_path("calhead", key, cache=cache), hcfg)
    if head is not None:
        parts = {}
        for part in R.cal_parts(k, reps):
            g = R.load(R.cache_path("cal", key, part, cache=cache),
                       R.base_config("cal", key, units, k=k, reps=reps, part=list(part)))
            if g is not None:
                parts[tuple(part)] = g
        j = R.cal_join(head, {p: parts.get(p, {}) for p in map(tuple, R.cal_parts(k, reps))})
        if not j.get("missing"):
            cap = capacity("whole reading", "calibrated here", j, sd)
        else:
            out["calibration_unfinished"] = j["missing"]
    if cap is None:
        q = R.load(R.cache_path("quick", key, cache=cache), R.base_config("quick", key, units, k=k, reps=reps))
        if q is not None:
            cap = capacity("single seed", "planted here", q, sd)
    if cap is None:
        imp = R.load(R.cache_path("calimport", key, cache=cache))
        if imp is not None:
            cap = capacity("whole reading" if "free_held" in imp else "single seed", "planting run of 2026-10-06", imp, sd)
    out["range"] = cap or {"kind": "none"}
    return out


# ---------------------------------------------------------------------------------------------
# a span's state over its frequencies, and before against after
# ---------------------------------------------------------------------------------------------

def rung_days(rung, sd):
    if not rung or sd is None:
        return None
    if "at_or_faster_than" in rung:
        return [0.0, rung["at_or_faster_than"] * sd]
    if "between" in rung:
        return [rung["between"][0] * sd, rung["between"][1] * sd]
    return [rung["slower_than"] * sd, INF]


def span_state(cells, tag, arm, span, variant="raw", freqs=None):
    """One state for a span from its frequencies, which read three time scales and are not a knob.

    above when some frequency reads above and none below, with the interval of the finest such
    frequency, placed on the Gaussian ladder (the plain scale; the ladder on the cell's own steps
    says what the cell could resolve and is kept beside it); below is the mirror; both ways is marginal. inside when every frequency that could
    be read is inside, with the longest half-life any of them could resolve. Anything else that
    has a frequency without a verdict is marginal; nothing read is unread.
    """
    by = {}
    for f in (freqs or ("D", "W", "M", "S")):
        c = cells.get(R.cell_key(tag, arm, span, f, variant))
        if c is None:
            continue
        h = c.get("held", {})
        sd = (c.get("shape") or {}).get("step_days")
        res = h.get("resolvable") or []
        by[f] = {"state": c["state"], "reason": c.get("reason") or h.get("reason"),
                 "interval_days": rung_days(h.get("rung_gaussian"), sd) if c["state"] == "above" else None,
                 "interval_on_own_steps_days": rung_days(h.get("rung_on_own_steps"), sd) if c["state"] == "above" else None,
                 "reach_days": (max(res) * sd) if (res and sd) else 0.0}
    read = {f: v for f, v in by.items() if v["state"] != "unread"}
    out = {"by_freq": by, "interval_days": None, "reach_days": None}
    if not read:
        out["state"] = "unread"
        return out
    ab = [f for f in read if read[f]["state"] == "above"]
    be = [f for f in read if read[f]["state"] == "below"]
    if ab and be:
        out["state"] = "marginal"
    elif ab:
        out.update(state="above", interval_days=read[ab[0]]["interval_days"], interval_from=ab[0])
    elif be:
        out["state"] = "below"
    elif all(v["state"] == "inside" for v in read.values()):
        out.update(state="inside", reach_days=max(v["reach_days"] for v in read.values()))
    else:
        out["state"] = "marginal"
    return out


def compare(before, after):
    """Is reading two faster after than before? faster, slower, not told apart, or no verdict."""
    b, a = before["state"], after["state"]
    if b not in VERDICT or a not in VERDICT:
        return {"state": "no verdict", "why": f"before is {b}, after is {a}"}
    if a == "above" and b == "above":
        bi, ai = before["interval_days"], after["interval_days"]
        if not bi or not ai:
            return {"state": "no verdict", "why": "an above reading without a rung"}
        if bi[0] >= ai[1]:
            return {"state": "faster", "why": "both above, the rungs do not overlap"}
        if ai[0] >= bi[1]:
            return {"state": "slower", "why": "both above, the rungs do not overlap"}
        return {"state": "not told apart", "why": "both above, the rungs overlap"}
    if a == "above" and b == "inside":
        ai = after["interval_days"]
        if ai and before["reach_days"] is not None and before["reach_days"] >= ai[1]:
            return {"state": "faster", "why": "after is above; before is inside and could resolve a force that fast"}
        return {"state": "no verdict", "why": "after is above; before is inside and could not resolve a force that fast"}
    if b == "above" and a == "inside":
        bi = before["interval_days"]
        if bi and after["reach_days"] is not None and after["reach_days"] >= bi[1]:
            return {"state": "slower", "why": "before is above; after is inside and could resolve a force that fast"}
        return {"state": "no verdict", "why": "before is above; after is inside and could not resolve a force that fast"}
    if a == "above" and b == "below":
        return {"state": "faster", "why": "after is above, before is below"}
    if b == "above" and a == "below":
        return {"state": "slower", "why": "before is above, after is below"}
    return {"state": "not told apart", "why": f"before is {b}, after is {a}"}


def abs_medians(cell, keep=None):
    if not cell or not cell.get("centre"):
        return {}
    return {u: abs(x) for u, x in cell["centre"]["median_by_series"].items() if keep is None or u in keep}


def med(xs):
    xs = list(xs)
    return float(np.median(xs)) if xs else None


# ---------------------------------------------------------------------------------------------
# the eight criteria. Each takes the record and returns (passed, detail); passed is True, False
# or None, and None means a cell it needs carries no verdict.
# ---------------------------------------------------------------------------------------------

def crit(name, kind, statement, passed, detail):
    out = {"name": name, "kind": kind, "statement": statement, "passed": passed, "detail": detail}
    if passed is None:
        out["undecidable"] = True
    return out


def share(rows, state="above"):
    n = sum(sum(r.values()) for r in rows)
    return (sum(r.get(state, 0) for r in rows) / n) if n else None


def crit1(rec):
    cells = rec["cells"]
    lacking, kinds = [], defaultdict(int)
    for key, c in cells.items():
        if c.get("variant") == "describe" or c.get("state") not in VERDICT:
            continue
        rg = c.get("range", {"kind": "none"})
        if rg["kind"] == "borrowed":
            rg = cells.get(rg["from"], {}).get("range", {"kind": "none"})
            kinds["borrowed from the same cell as the station read it"] += 1
        else:
            kinds[rg["kind"]] += 1
        if rg["kind"] not in ("whole reading", "single seed"):
            lacking.append(key)
    by = defaultdict(lambda: {"planted": [], "free": [], "line": [0, 0, 0, 0]})
    for c in cells.values():
        rg = c.get("range", {})
        if rg.get("kind") == "whole reading" and rg.get("state") == "read" and rg.get("planted"):
            p0, fr = rg["planted"][0], rg.get("free") or {}
            by[c["tag"]]["planted"].append(p0.get("held", {}))
            by[c["tag"]]["free"].append(rg.get("free_held", {}))
            ln = by[c["tag"]]["line"]
            for j, x in enumerate((p0.get("over_line", 0), p0.get("panels", 0), fr.get("over_line", 0), fr.get("panels", 0))):
                ln[j] += x
    rows = {}
    for t, v in sorted(by.items()):
        ln = v["line"]
        rows[t] = (share(v["planted"]), share(v["free"]), (ln[0] / ln[1]) if ln[1] else None, (ln[2] / ln[3]) if ln[3] else None)
    # Two things, both on the shorter planted rung against the panels with no force: the whole reading
    # calls the planted ones above more often, and so does the line alone. A null that sits too low
    # puts both kinds over the line alike, and the second comparison is what sees that.
    ok = all(None not in r and r[0] > r[1] and r[2] > r[3] for r in rows.values())
    txt = "; ".join(f"{t}: planted at the shorter rung read above {r[0]:.3f} and over the line {r[2]:.3f}, "
                    f"no force read above {r[1]:.3f} and over the line {r[3]:.3f}"
                    for t, r in rows.items() if None not in r)
    kd = ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
    if lacking:
        return None, (f"Not decided: {len(lacking)} cells carry a verdict and no finished capacity line "
                      f"({'; '.join(lacking[:4])}{' ...' if len(lacking) > 4 else ''}). Capacity lines by kind: {kd}. {txt}")
    if not rows:
        return None, "Not decided: no carrier has a whole-reading calibration."
    return bool(ok), f"Cells with a verdict by the kind of capacity line: {kd}. {txt}"


def crit2(rec):
    cov = rec["coverage"]
    tags = [r["tag"] for r in cov]
    want = list(rec["loaders"])
    unexplained = [r["tag"] for r in cov if not r["read"] and not r.get("reason")]
    ok = sorted(tags) == sorted(want) and not unexplained
    return bool(ok), (f"carriers listed {len(tags)} of {len(want)}; read {sum(r['read'] for r in cov)}; listed and not "
                      f"read with a reason {sum((not r['read']) and bool(r.get('reason')) for r in cov)}"
                      + (f"; missing {sorted(set(want) - set(tags))}" if set(want) - set(tags) else "")
                      + (f"; not read and no reason {unexplained}" if unexplained else ""))


def ranked(rec):
    return [t for t in RANKED if all(line_complete(x) for x in rec["types"] if x["tag"] == t)
            and any(x["tag"] == t for x in rec["types"])]


def crit3(rec):
    rk = ranked(rec)
    out = [t for t in RANKED if t not in rk]
    return (not out), (f"carriers in the ranking {len(rk)} of {len(RANKED)}: {', '.join(rk)}"
                       + (f"; out of it for an empty type, source or quote: {', '.join(out)}" if out else ""))


def crit4(rec):
    cells = rec["cells"]

    def ratio(tag, arm, span, f):
        c = cells.get(R.cell_key(tag, arm, span, f)) or {}
        return (c.get("centre") or {}).get("median_ratio")
    a = ratio("B9", "main arm", "whole window", "D")
    cs = {"B21, whole window": ratio("B21", R.B21_ARM, "whole window", "D"),
          "B5 pairs with the official rate, before 2025-04-14": ratio("B5", "treated", "before 2025-04-14", "D"),
          "B97 Cyprus, edge cut": ratio("B97", "squares, CY against the euro area", "edge cut", "M")}
    b9 = cells.get(R.cell_key("B9", "main arm", "whole window", "D")) or {}
    st = b9.get("state", "unread")
    one = None if (a is None or any(v is None for v in cs.values())) else all(v > a for v in cs.values())
    two = None if st not in VERDICT else (st == "above")
    passed = None if (one is None or two is None) else bool(one and two)
    f = lambda x: "n/a" if x is None else f"{x:.3f}"
    head = "" if passed is not None else "Not decided: a cell this needs carries no verdict or no ratio. "
    rung = (b9.get("held") or {}).get("rung_gaussian")
    return passed, (head + f"Reading one, centre against zero in units of the series' own far-deviation cut: type A "
                    f"(B9 main arm) {f(a)}; type C cells " + "; ".join(f"{k} {f(v)}" for k, v in cs.items())
                    + f". Every type C cell above the type A cell: {one}. Reading two on B9 main arm, daily: {st}"
                    + (f", on the Gaussian ladder {rung} in steps of one trading day" if rung else "") + ". " + RIVAL_SENTENCE)


def b5_comparison(rec, arm):
    cells = rec["cells"]
    bef = cells.get(R.cell_key("B5", arm, "before 2025-04-14", "D"))
    aft = cells.get(R.cell_key("B5", arm, "from 2025-04-14", "D"))
    mb, ma = med(abs_medians(bef).values()), med(abs_medians(aft).values())
    cmp_ = compare(span_state(cells, "B5", arm, "before 2025-04-14"), span_state(cells, "B5", arm, "from 2025-04-14"))
    return mb, ma, cmp_


def crit5(rec):
    mb, ma, cmp_ = b5_comparison(rec, "treated")
    f = lambda x: "n/a" if x is None else f"{x:.4f}"
    txt = (f"B5 pairs with the official rate: median over pairs of |median|, before {f(mb)}, after {f(ma)}; "
           f"reading two, after against before: {cmp_['state']} ({cmp_['why']}).")
    if mb is None or ma is None or cmp_["state"] == "no verdict":
        return None, "Not decided: one side of 2025-04-14 has no reading. " + txt
    moved = ma < mb
    cb, ca, cc = b5_comparison(rec, "control")
    txt += (f" The three pairs without the official rate, for comparison: |median| before {f(cb)}, after {f(ca)}; "
            f"reading two, after against before: {cc['state']}.")
    if cmp_["state"] == "faster":
        return bool(moved), txt
    return False, txt + f" The centre moved toward zero: {moved}; that half holds on its own, the other does not."


def crit6(rec):
    cells = rec["cells"]
    rows, bad, waiting = {}, [], []
    for tag in ("B9", "B3", "B21", "B52"):
        if any(c["tag"] == tag and c["variant"] == "less" and not c.get("run") for c in cells.values()):
            waiting.append(tag)
        got = [c for c in cells.values() if c["tag"] == tag and c["variant"] == "less" and c.get("run")]
        shares = sorted({round(c["common"]["common_share_of_step_ss"], 6) for c in got
                         if c.get("common") and c["common"].get("common_share_of_step_ss") is not None})
        rows[tag] = (len(got), shares)
        if not got or not shares or not all(0.0 <= s <= 1.0 for s in shares):
            bad.append(tag)
    not_read = sorted({f"{c['tag']} {c['arm']}" for c in cells.values()
                       if c["variant"] == "raw" and c["tag"] in ("B5", "B97")})
    if waiting:
        return None, f"Not decided: the cells less the date-common term have not all been run on {waiting}."
    return (not bad), ("; ".join(f"{t}: {n} cells read less the date-common term, its share of the step sum of squares "
                                 f"{', '.join(f'{s:.4f}' for s in sh) or 'n/a'}" for t, (n, sh) in rows.items())
                       + f". Listed and not read this way, the series are not interchangeable: {len(not_read)} arms of "
                         "B5 and B97." + (f" Missing or out of range: {bad}." if bad else ""))


def crit7(rec):
    x = (rec.get("b9") or {}).get("arms", {}).get("main arm")
    b3 = rec.get("b3_split") or {}
    if not x:
        return None, "Not decided: the calm and stress counts of B9 were not run."
    calm, stress, whole = x["calm"], x["stress"], x["whole"]
    ok = sum(calm) > 0 and sum(stress) > 0 and all(calm[j] + stress[j] == whole[j] for j in (0, 1)) \
        and b3.get("state") == "unread" and bool(b3.get("reason"))
    p = lambda v: "n/a" if not sum(v) else f"{v[0] / sum(v):.4f}"
    return bool(ok), (f"B9 main arm, far points by the station's own flag: calm back {calm[0]}, away {calm[1]} "
                      f"({p(calm)}); stress back {stress[0]}, away {stress[1]} ({p(stress)}); whole window back "
                      f"{whole[0]}, away {whole[1]}. B3: {b3.get('state')}, {b3.get('reason')}.")


def crit8(rec):
    rows = rec["cross_carrier"]
    by = defaultdict(int)
    for r in rows:
        by[r["type"]] += 1
    want = [(t, a, s) for t, a, s in CROSS_ROWS if t in ranked(rec)]
    have = [(r["tag"], r["arm"], r["span"]) for r in rows]
    same = all(r["type"] == type_of(rec["types"], r["tag"], r["arm"], r["span"]) for r in rows)
    ok = have == want and sum(by.values()) == len(rows) and same and None not in by
    return bool(ok), (f"rows {len(rows)} of {len(want)}; by type " + ", ".join(f"{k}: {v}" for k, v in sorted(by.items(), key=str))
                      + f"; types equal to the type table row for row: {same}. Order and counts only, no line drawn.")


CRITERIA = (
    ("B142-1", "known_answer", "every cell with a verdict has a capacity line that says how it was made, and where the "
     "whole reading was calibrated a planted force is read above more often than no force is", crit1),
    ("B142-2", "bookkeeping", "the coverage table lists every candidate carrier, read or not, with the reason", crit2),
    ("B142-3", "own_reading", "each ranked carrier's crossing type has a type, a source and a quote", crit3),
    ("B142-4", "own_reading", "type C centres stand further from zero than the type A centre, and the type A carrier "
     "comes back within the step", crit4),
    ("B142-5", "own_reading", "after the split is lifted on B5 the centre moves toward zero and comes back faster", crit5),
    ("B142-6", "own_reading", "the readings are repeated less the date-common term where series are interchangeable", crit6),
    ("B142-7", "own_reading", "B9 is counted apart on calm and stress days; B3 has no pinned cut and is not read", crit7),
    ("B142-8", "own_reading", "the cross-carrier table has one row per ranked carrier or span, typed as the type table", crit8),
)


def score(rec):
    out = []
    for name, kind, statement, fn in CRITERIA:
        passed, detail = fn(rec)
        out.append(crit(name, kind, statement, passed, detail))
    return out


# ---------------------------------------------------------------------------------------------
# putting the record together
# ---------------------------------------------------------------------------------------------

def coverage(carriers):
    rows = []
    for tag, _loader in m.LOADERS:
        c = carriers.get(tag)
        if c is None:
            continue
        arms = []
        for arm, units in c["arms"].items():
            lens = sorted((len(ts), str(u)) for u, (ts, _) in units.items())
            arms.append({"arm": arm, "series": len(lens), "series_read": sum(1 for n, _ in lens if n >= m.MIN_SERIES),
                         "points": sum(n for n, _ in lens), "median_length": float(np.median([n for n, _ in lens])),
                         "first": min(str(ts[0]) for ts, _ in units.values() if ts),
                         "last": max(str(ts[-1]) for ts, _ in units.values() if ts),
                         "shortest_three": [[n, u] for n, u in lens[:3]]})
        nread = sum(a["series_read"] for a in arms)
        rows.append({"tag": tag, "freq": c["freq"], "caliber": c["caliber"], "arms": arms,
                     "read": not c.get("not_read"), "reason": c.get("not_read"),
                     "series_of_readable_length": nread})
    return rows


def cross_rows(cells, types, order=CROSS_ROWS):
    rows = []
    complete = {t for t in RANKED if any(x["tag"] == t for x in types)
                and all(line_complete(x) for x in types if x["tag"] == t)}
    for tag, arm, span in order:
        if tag not in complete:
            continue
        freqs = ("W", "M") if tag == "B3" else None
        native = next((f for f in ("D", "M", "S") if R.cell_key(tag, arm, span, f) in cells), None)
        c = cells.get(R.cell_key(tag, arm, span, native)) if native else None
        cen = (c or {}).get("centre") or {}
        prof = (c or {}).get("profile") or []
        sd = ((c or {}).get("shape") or {}).get("step_days")
        last = prof[-1] if prof else None
        ss = span_state(cells, tag, arm, span, freqs=freqs)
        less = span_state(cells, tag, arm, span, "less", freqs=freqs)
        t = type_line(types, tag, arm) or {}
        rows.append({"tag": tag, "arm": arm, "span": span, "type": type_of(types, tag, arm, span),
                     "tie": t.get("tie"), "centre_against_zero": cen.get("median_ratio"),
                     "further_than_own_cut": cen.get("further_than_own_cut"), "series": cen.get("units"),
                     "abs_median_over_series": cen.get("abs_median_over_series"),
                     "longest_lag_days": (last["lag"] * sd) if (last and sd) else None,
                     "slope_at_longest_lag": last["slope"] if last else None,
                     "variance_ratio_at_longest_lag": last["variance_ratio"] if last else None,
                     "reading_two": ss["state"], "interval_days": ss["interval_days"], "reach_days": ss["reach_days"],
                     "by_freq": {f: v["state"] for f, v in ss["by_freq"].items()},
                     "less_common": less["state"] if less["by_freq"] else "not read this way",
                     "less_common_by_freq": {f: v["state"] for f, v in less["by_freq"].items()}})
    return rows


def b97_moves(cells):
    arm = "squares, CY against the euro area"
    cut = abs_medians(cells.get(R.cell_key("B97", arm, "edge cut", "M")))
    out = {}
    for span in ("before the cut", "edge restored", "later"):
        x = abs_medians(cells.get(R.cell_key("B97", arm, span, "M")))
        common = sorted(set(cut) & set(x))
        if not common:
            out[span] = {"state": "no verdict"}
            continue
        d = med(x[u] for u in common) - med(cut[u] for u in common)
        out[span] = {"abs_median": med(x[u] for u in common), "edge_cut_abs_median": med(cut[u] for u in common),
                     "squares_closer_to_zero": int(sum(x[u] < cut[u] for u in common)), "squares": len(common),
                     "state": "did not move" if abs(d) <= B97_TICK else ("closer to zero" if d < 0 else "further from zero")}
    return out


def b21_connect(cells, a_ratio):
    arm = R.B21_ARM
    B, A, AB = "before own Connect opening", "from own Connect opening", "from own Connect opening, pairs read on both sides"
    get = lambda span, f="D", v="raw": cells.get(R.cell_key("B21", arm, span, f, v))
    out = {}
    rb = ((get(B) or {}).get("centre") or {}).get("median_ratio")
    ra = ((get(A) or {}).get("centre") or {}).get("median_ratio")
    out["reading_one"] = {"before": rb, "after": ra, "type_A_cell": a_ratio,
                          "state": ("no verdict" if None in (rb, ra, a_ratio) else
                                    "both above the type A cell" if (rb > a_ratio and ra > a_ratio) else
                                    "not both above the type A cell")}
    xb = abs_medians(get(B))
    xa = abs_medians(get(AB))
    common = sorted(set(xb) & set(xa))
    out["direction"] = {"pairs": len(common), "before_abs_median": med(xb[u] for u in common),
                        "after_abs_median": med(xa[u] for u in common),
                        "pairs_closer_to_zero_after": int(sum(xa[u] < xb[u] for u in common)),
                        "state": "printed, no verdict: the direction is not pinned"}
    sb = span_state(cells, "B21", arm, B)
    sa = span_state(cells, "B21", arm, A)
    sab = span_state(cells, "B21", arm, AB)
    out["reading_two"] = {"before": sb, "after": sa, "after_same_pairs": sab,
                          "after_against_before": compare(sb, sa), "same_pairs_after_against_before": compare(sb, sab)}
    lags = {}
    for lag in R.ENTRY_LAGS:
        span = A if lag == 0 else f"{A}, entry lag {lag}"
        lags[str(lag)] = {f: (get(span, f) or {}).get("state", "unread") for f in "DWM"}
    flips = any({"above", "below"} <= {lags[str(l)][f] for l in R.ENTRY_LAGS} for f in "DWM")
    out["entry_lag"] = {"states": lags, "flips": flips}
    cross = {}
    for ex in ("SH main", "SZ"):
        for span in ("to 2014-11-14", "2014-11-17 to 2016-12-02", "from 2016-12-05"):
            lab = f"{ex}, {span}"
            c = get(lab) or {}
            cen = c.get("centre") or {}
            ss = span_state(cells, "B21", arm, lab)
            cross[lab] = {"series": (c.get("shape") or {}).get("series"), "centre_against_zero": cen.get("median_ratio"),
                          "abs_median_over_series": cen.get("abs_median_over_series"),
                          "reading_two": ss["state"], "by_freq": {f: v["state"] for f, v in ss["by_freq"].items()},
                          "interval_days": ss["interval_days"], "reach_days": ss["reach_days"]}
    out["cross"] = cross
    out["less_common"] = {span: span_state(cells, "B21", arm, span, "less") for span in ("whole window", B, A)}
    return out


def assemble(cells_obj, cache=None, types=TYPES):
    cells = {key: build_cell(cells_obj, key, cache) for key in cells_obj.cells}
    not_run = sorted(k for k, c in cells.items() if not c["run"])
    unfinished = sorted(k for k, c in cells.items() if c.get("calibration_unfinished") or c.get("knob_run") is False)
    rec = {"stage": "B142", "loaders": [t for t, _ in m.LOADERS], "types": copy.deepcopy(types), "cells": cells,
           "coverage": coverage(cells_obj.carriers)}
    cfg = {"version": R.VERSION, "kind": "extra"}
    rec["b9"] = R.load(R.cache_path("extra", "B9|extras", cache=cache), dict(cfg, key="B9|extras"))
    rec["b21_counts"] = R.load(R.cache_path("extra", "B21|connect counts", cache=cache), dict(cfg, key="B21|connect counts"))
    rec["b3_split"] = {"state": "unread", "reason": "the station pinned no shock date, so there is no cut to copy"}
    rec["cross_carrier"] = cross_rows(cells, rec["types"])
    a_ratio = ((cells.get(R.cell_key("B9", "main arm", "whole window", "D")) or {}).get("centre") or {}).get("median_ratio")
    comp = {}
    for arm in ("treated", "control"):
        mb, ma, cmp_ = b5_comparison(rec, arm)
        comp[f"B5 {arm}"] = {"before_abs_median": mb, "after_abs_median": ma, "reading_two_after_against_before": cmp_,
                             "before": span_state(cells, "B5", arm, "before 2025-04-14"),
                             "after": span_state(cells, "B5", arm, "from 2025-04-14")}
    comp["B97 Cyprus against its edge-cut span"] = b97_moves(cells)
    comp["B21 Stock Connect"] = b21_connect(cells, a_ratio)
    rec["comparisons"] = comp
    rec["complete"] = not not_run and not unfinished
    rec["not_run"] = not_run
    rec["unfinished"] = unfinished
    rec["criteria"] = score(rec)
    rec["config"] = {
        "far_point_quantile": m.TERCILE, "knob_quantiles": list(R.KNOB_Q), "min_series_points": m.MIN_SERIES,
        "min_series": m.MIN_UNITS, "seed": m.SEED, "second_seed_offset": m.SEED2, "draws": list(m.DRAWS),
        "budget_points_times_draws": m.BUDGET, "half_lives": list(m.HALF_LIVES), "block_multiples": list(m.ELIGIBLE),
        "no_force_panels": {"up_to_100000_points": R.K_SMALL, "above": R.K_BIG, "B3_daily": R.K_B3_DAILY},
        "planted_panels_per_rung": {"up_to_100000_points": R.REPS_SMALL, "above": R.REPS_BIG},
        "connect_open": {k: v.isoformat() for k, v in R.CONNECT_OPEN.items()}, "star_open": R.STAR_OPEN.isoformat(),
        "entry_lags_trading_days": list(R.ENTRY_LAGS), "quota_steps": [d.isoformat() for d in R.QUOTA_STEPS],
        "b97_control_ends": dict(m.B97_CONTROL_ENDS), "b97_tick": B97_TICK,
        "b3_state_from": ["W", "M"],
        "segments": {t: {"from": c.get("segments_from"), "spans": [[lab, str(lo), str(hi)] for lab, lo, hi in c.get("segments", [])]}
                     for t, c in cells_obj.carriers.items() if c.get("segments")},
        "calibration_tier_one": [R.cell_key(*t) for t in R.CAL_TIER1],
        "calibration_tier_two": [R.cell_key(*t) for t in R.CAL_TIER2],
    }
    return rec


def run(out=None) -> int:
    rec = assemble(R.Cells(None))
    text = json.dumps(fixed(rec), ensure_ascii=False, sort_keys=True, indent=1)
    (out or R.RECORD).write_text(text + "\n", encoding="utf-8", newline="\n")
    for c in rec["criteria"]:
        flag = {True: "PASS", False: "FAIL", None: "NOT DECIDED"}[c["passed"]]
        print(f"{flag:<12} {c['name']} [{c['kind']}] {c['detail']}\n")
    print(f"complete: {rec['complete']}; cells not run {len(rec['not_run'])}; unfinished {len(rec['unfinished'])}")
    return 0 if all(c["passed"] is not False for c in rec["criteria"]) else 1


# ---------------------------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------------------------

def toy_record():
    """A record in which every criterion holds, built by hand, for the faults below to be planted in."""
    def cell(tag, arm, span, f, state, ratio, meds, variant="raw", rung=None, res=(1, 2, 4), sd=1.0, rng="whole reading"):
        c = {"tag": tag, "arm": arm, "span": span, "freq": f, "variant": variant, "run": True, "state": state,
             "shape": {"step_days": sd, "series": len(meds)},
             "centre": {"median_ratio": ratio, "median_by_series": dict(meds), "units": len(meds),
                        "further_than_own_cut": 0, "abs_median_over_series": med(abs(x) for x in meds.values())},
             "profile": [{"lag": 1, "slope": None, "variance_ratio": 1.0}, {"lag": 2, "slope": 0.5, "variance_ratio": 0.7}],
             "held": {"state": state, "rung_on_own_steps": rung, "rung_gaussian": rung, "resolvable": list(res)}}
        if variant == "less":
            c["common"] = {"common_share_of_step_ss": 0.3}
            c["range"] = {"kind": "borrowed", "from": R.cell_key(tag, arm, span, f)}
        else:
            c["range"] = {"kind": rng, "state": "read",
                          "planted": [{"half_life": 2, "held": {"above": 16, "inside": 4}, "over_line": 18, "panels": 20}],
                          "free": {"over_line": 1, "panels": 19}, "free_held": {"above": 1, "inside": 18}}
        return c
    cells = {}

    def put(c):
        cells[R.cell_key(c["tag"], c["arm"], c["span"], c["freq"], c["variant"])] = c
    one = {"a": 0.001, "b": -0.001, "c": 0.002}
    far = {"a": 0.5, "b": 0.6, "c": 0.4}
    put(cell("B9", "main arm", "whole window", "D", "above", 0.08, one, rung={"at_or_faster_than": 1}))
    put(cell("B9", "main arm", "whole window", "D", "above", 0.08, one, "less"))
    put(cell("B9", "comparison arm", "whole window", "D", "above", 0.6, one))
    for arm in ("g10", "eme"):
        put(cell("B3", arm, "whole window", "W", "above", 0.8, far, rung={"between": [8, 16]}, sd=7.0, rng="single seed"))
        put(cell("B3", arm, "whole window", "W", "above", 0.8, far, "less"))
    put(cell("B5", "control", "whole window", "D", "above", 0.3, far, rung={"between": [16, 32]}))
    put(cell("B5", "treated", "before 2025-04-14", "D", "inside", 1.6, far, res=(1, 2, 4, 8, 16, 32)))
    put(cell("B5", "treated", "from 2025-04-14", "D", "above", 0.4, {k: v / 10 for k, v in far.items()},
             rung={"between": [2, 4]}))
    put(cell("B5", "control", "before 2025-04-14", "D", "above", 0.3, far, rung={"between": [16, 32]}))
    put(cell("B5", "control", "from 2025-04-14", "D", "above", 0.3, far, rung={"between": [16, 32]}))
    cy = "squares, CY against the euro area"
    for span, st, r in (("before the cut", "inside", 0.9), ("edge cut", "inside", 1.7), ("edge restored", "inside", 1.2),
                        ("later", "inside", 1.1)):
        put(cell("B97", cy, span, "M", st, r, far, sd=30.4))
    for a in ("GR", "SI", "MT", "PT", "IE"):
        put(cell("B97", f"squares, {a} against the euro area", "whole window", "M", "above", 1.0, far, sd=30.4,
                 rung={"between": [4, 8]}))
    for span in ("whole window", "before own Connect opening", "from own Connect opening"):
        put(cell("B21", R.B21_ARM, span, "D", "above", 2.9, far, rung={"slower_than": 64}))
    put(cell("B21", R.B21_ARM, "whole window", "D", "above", 2.9, far, "less"))
    put(cell("B52", "class square, I_TAX", "whole window", "S", "inside", 0.76, far, sd=182.6))
    put(cell("B52", "class square, I_TAX", "whole window", "S", "inside", 0.76, far, "less"))
    rec = {"stage": "B142", "loaders": [t for t, _ in m.LOADERS], "types": copy.deepcopy(TYPES), "cells": cells,
           "coverage": [{"tag": t, "read": t not in ("B59", "B49", "B128"),
                         "reason": None if t not in ("B59", "B49", "B128") else "named"} for t, _ in m.LOADERS],
           "b9": {"arms": {"main arm": {"calm": [600, 80], "stress": [700, 90], "whole": [1300, 170]}}},
           "b3_split": {"state": "unread", "reason": "the station pinned no shock date, so there is no cut to copy"}}
    rec["cross_carrier"] = cross_rows(cells, rec["types"])
    return rec


def selftest() -> int:
    import datetime as dt
    import tempfile
    fails = []

    def check(name, ok, detail=""):
        print(f"{'ok  ' if ok else 'FAIL'} {name}{(': ' + str(detail)) if detail != '' else ''}", flush=True)
        if not ok:
            fails.append(name)

    flag = lambda rec, name: next(c["passed"] for c in score(rec) if c["name"] == name)
    base = toy_record()
    got = {c["name"]: c["passed"] for c in score(base)}
    check("on the hand-built record every criterion holds", all(v is True for v in got.values()), got)

    # --- B142-1
    g = np.random.default_rng(17)
    strong = {u: m._integrate(g.normal(size=(1, 60)), 0.8)[0] for u in range(6)}
    ref = m.plant_one(strong, 5, 4, m.SEED, formal=True)
    head = R.cal_head(strong, 5)
    plist = [("free", 0, 2), ("free", 2, 5), ("rung0", 0, 2), ("rung0", 2, 4), ("rung1", 0, 2), ("rung1", 2, 4)]
    parts, cut_short = {}, 0
    for part in plist:
        rows, done = R.cal_part(strong, head, part, 5, stop_after=1)
        cut_short += int(not done)
        rows = json.loads(json.dumps({str(i): v for i, v in rows.items()}))      # as a kept file gives it back
        rows, done = R.cal_part(strong, head, part, 5, kept=rows)
        parts[part] = rows
    joined = R.cal_join(head, parts)
    same = json.dumps(ref, default=R._plain, sort_keys=True) == json.dumps(joined, default=R._plain, sort_keys=True)
    check("a calibration stopped in every part and taken up again equals the one run straight through",
          same and cut_short >= 4, f"parts cut short {cut_short}")
    hole = R.cal_join(head, {p: (parts[p] if p != ("rung0", 2, 4) else {}) for p in plist})
    check("a calibration with a part missing names it and gives no count for that rung",
          hole.get("missing") == ["rung0"] and len(hole["planted"]) == len(ref["planted"]) - 1, hole.get("missing"))
    cap = capacity("whole reading", "here", joined, 1.0)
    one = copy.deepcopy(base)
    for c in one["cells"].values():
        if c["tag"] == "B9" and c["variant"] == "raw":
            c["range"] = cap
    p_true, _ = crit1(one)
    real_null = m.null
    try:
        def half(vals, kind, nsim, seed, q=m.TERCILE, block=None, phi=1.0, D=None, raw=False):
            out = real_null(vals, kind, nsim, seed, q, block, phi, D, raw)
            if not raw and phi == 1.0 and out.get("mean") is not None:
                out["mean"] = 0.5
            return out
        m.null = half
        h2 = R.cal_head(strong, 5)
        p2 = {p: R.cal_part(strong, h2, p, 5)[0] for p in plist}
        j2 = R.cal_join(h2, p2)
    finally:
        m.null = real_null
    two = copy.deepcopy(base)
    for c in two["cells"].values():
        if c["variant"] == "raw":
            c["range"] = capacity("whole reading", "here", j2, 1.0)
    p_half, d_half = crit1(two)
    check("B142-1 holds on a real small calibration, and fails when the null is replaced by one half",
          p_true is True and p_half is False and j2["free"]["over_line"] == j2["free"]["panels"],
          f"with one half, no-force panels over the line {j2['free']['over_line']} of {j2['free']['panels']}")
    lack = copy.deepcopy(base)
    lack["cells"][R.cell_key("B5", "control", "whole window", "D")]["range"] = {"kind": "none"}
    check("B142-1 is not decided when a cell with a verdict has no capacity line", flag(lack, "B142-1") is None)

    # --- B142-2, B142-3, B142-8
    x = copy.deepcopy(base)
    x["coverage"] = [r for r in x["coverage"] if r["tag"] != "B49"]
    check("B142-2 fails when a carrier that reads zero series is dropped from the table", flag(x, "B142-2") is False)
    x = copy.deepcopy(base)
    next(t for t in x["types"] if t["line"] == "B3")["source"] = ""
    x["cross_carrier"] = cross_rows(x["cells"], x["types"])
    check("B142-3 fails when a source is emptied, and that carrier leaves the ranking and the table",
          flag(x, "B142-3") is False and "B3" not in ranked(x) and all(r["tag"] != "B3" for r in x["cross_carrier"]))
    x = copy.deepcopy(base)
    before = defaultdict(int)
    for r in x["cross_carrier"]:
        before[r["type"]] += 1
    for r in x["cross_carrier"]:
        r["type"] = {"B9": "C", "B21": "A"}.get(r["tag"], r["type"])
    after = defaultdict(int)
    for r in x["cross_carrier"]:
        after[r["type"]] += 1
    check("B142-8 fails when two carriers' types are exchanged, and the counts by type change",
          flag(x, "B142-8") is False and dict(before) != dict(after), f"{dict(before)} -> {dict(after)}")

    # --- B142-4
    cs = dict(m.carriers({"B9"}))["B9"]
    main = cs["arms"]["main arm"]
    real = m.held(main, k=19, ladder=False)
    rng = np.random.default_rng(7)
    _L, p, _e, _t = m.blocks_for(m.values(main))
    boot = m.draw(main, max(2, int(round(p))), 1.0, rng)
    resampled = m.held(boot, k=19, ladder=False)
    x = copy.deepcopy(base)
    x["cells"][R.cell_key("B9", "main arm", "whole window", "D")]["state"] = resampled["state"]
    check("B9 main arm reads above, its own steps resampled in blocks read inside, and B142-4 then fails",
          real["state"] == "above" and resampled["state"] == "inside" and flag(x, "B142-4") is False,
          f"real {real['state']}, resampled {resampled['state']}")
    g = np.random.default_rng(3)
    off = {u: 5.0 + np.cumsum(g.normal(size=200)) * 0.1 for u in range(8)}
    c_off = R.centre(off)
    c_dem = R.centre({u: v - np.median(v) for u, v in off.items()})
    x = copy.deepcopy(base)
    x["cells"][R.cell_key("B21", R.B21_ARM, "whole window", "D")]["centre"]["median_ratio"] = c_dem["median_ratio"]
    check("a series less its own median has its centre at zero, and B142-4 then fails",
          c_off["median_ratio"] > 1 and c_dem["median_ratio"] == 0.0 and flag(x, "B142-4") is False,
          f"{c_off['median_ratio']:.2f} -> {c_dem['median_ratio']:.2f}")
    x = copy.deepcopy(base)
    x["cells"][R.cell_key("B9", "main arm", "whole window", "D")]["state"] = "marginal"
    check("B142-4 is not decided when the type A cell is marginal", flag(x, "B142-4") is None)

    # --- B142-5
    x = copy.deepcopy(base)
    kb, ka = R.cell_key("B5", "treated", "before 2025-04-14", "D"), R.cell_key("B5", "treated", "from 2025-04-14", "D")
    x["cells"][kb], x["cells"][ka] = x["cells"][ka], x["cells"][kb]
    for k_, span in ((kb, "before 2025-04-14"), (ka, "from 2025-04-14")):
        x["cells"][k_] = dict(x["cells"][k_], span=span)
    check("B142-5 fails when the two sides of the date are exchanged", flag(x, "B142-5") is False)
    b5 = dict(m.carriers({"B5"}))["B5"]
    first = min(ts[0] for ts, _ in b5["arms"]["treated"].values())
    empty = m.window(b5["arms"]["treated"], None, first - dt.timedelta(days=1))
    moved = R.read_cell(empty, "D", 19)
    x = copy.deepcopy(base)
    x["cells"][kb] = dict(x["cells"][kb], state=moved["held"]["state"], centre=moved["centre"])
    check("with the date moved to the start of the window the span before it is unread and B142-5 is not decided",
          moved["held"]["state"] == "unread" and flag(x, "B142-5") is None, moved["held"].get("reason"))
    for b, a, want in (
            ({"state": "inside", "reach_days": 48.0, "interval_days": None}, {"state": "above", "interval_days": [3.0, 6.0]}, "faster"),
            ({"state": "inside", "reach_days": 4.0, "interval_days": None}, {"state": "above", "interval_days": [3.0, 6.0]}, "no verdict"),
            ({"state": "above", "interval_days": [10.0, 20.0]}, {"state": "above", "interval_days": [3.0, 6.0]}, "faster"),
            ({"state": "above", "interval_days": [3.0, 6.0]}, {"state": "above", "interval_days": [4.0, 9.0]}, "not told apart"),
            ({"state": "above", "interval_days": [3.0, 6.0]}, {"state": "inside", "reach_days": 30.0, "interval_days": None}, "slower"),
            ({"state": "inside", "reach_days": 9.0}, {"state": "inside", "reach_days": 3.0}, "not told apart"),
            ({"state": "marginal"}, {"state": "above", "interval_days": [3.0, 6.0]}, "no verdict")):
        if compare(b, a)["state"] != want:
            check(f"before against after: {b} then {a} is {want}", False, compare(b, a))
    check("before against after maps every pair of states to one of four, and no unread side to a verdict", True)

    # --- B142-6
    g = np.random.default_rng(11)
    T, n = 300, 6
    common = np.cumsum(g.normal(size=T))
    own = {u: np.cumsum(g.normal(size=T)) * 0.3 for u in range(n)}
    full = m.as_units({u: own[u] + common for u in range(n)})
    half_ = m.as_units({u: own[u] + common - 0.5 * common for u in range(n)})
    s_full = m.less_common(full, 3)[1]["common_share_of_step_ss"]
    s_half = m.less_common(half_, 3)[1]["common_share_of_step_ss"]
    lc = m.less_common(full, 3)[0]
    resid = float(np.mean([np.var(np.diff(lc[u][1]) - np.diff(own[u])) for u in range(n)]))
    left = float(np.mean([np.var(np.diff(half_[u][1]) - np.diff(own[u])) for u in range(n)]))
    check("a term every series shares is taken out whole; taken out by half, half of it is still there",
          s_full > s_half > 0.2 and resid < 0.25 * left and abs(left - 0.25 * np.var(np.diff(common))) < 0.05,
          f"share {s_full:.3f}, after half is removed {s_half:.3f}")
    x = copy.deepcopy(base)
    x["cells"][R.cell_key("B52", "class square, I_TAX", "whole window", "S", "less")]["common"]["common_share_of_step_ss"] = 1.5
    check("B142-6 fails when a common share is not between zero and one", flag(x, "B142-6") is False)

    # --- B142-7
    g = np.random.default_rng(5)
    v = np.cumsum(g.normal(size=300))
    fl = g.random(300) < 0.4
    a_, b_ = R.split_counts(v, fl), R.split_counts(v, ~fl)
    wb, wa = m.counts(v[None, :])
    check("counts split by a flag add up to the whole count, and the flag reversed exchanges the two groups",
          a_[True] == b_[False] and a_[False] == b_[True] and a_[True][0] + a_[False][0] == int(wb[0])
          and a_[True][1] + a_[False][1] == int(wa[0]) and a_[True] != a_[False], f"{a_}")
    x = copy.deepcopy(base)
    x["b9"]["arms"]["main arm"]["stress"] = [0, 0]
    check("B142-7 fails when one of the two groups is empty", flag(x, "B142-7") is False)
    x = copy.deepcopy(base)
    x["b3_split"] = {"state": "inside", "reason": ""}
    check("B142-7 fails when B3 is given a state without a pinned cut", flag(x, "B142-7") is False)
    bc = R.band_counts(np.array([0.5, 0.2, -0.3, 0.05, 0.0, 0.4]), np.full(6, 0.25))
    check("steps toward zero are counted apart inside and outside the fee band",
          bc == {"inside": [2, 1], "outside": [2, 0]}, bc)

    # --- the Connect split
    d0 = dt.date(2014, 11, 3)
    days = [d0 + dt.timedelta(days=i) for i in range(40)]
    late_days = [dt.date(2016, 12, 5) + dt.timedelta(days=i) for i in range(50)]
    star_days = [dt.date(2021, 1, 20) + dt.timedelta(days=i) for i in range(30)]
    toy = {"600001.SS": (days, np.arange(40.0)), "000001.SZ": (days, np.arange(40.0)),
           "601999.SS": (late_days, np.arange(50.0)), "688001.SS": (star_days, np.arange(30.0))}
    bf, af, cnt = R.connect_split(toy)
    bf10, af10, _ = R.connect_split(toy, 10)
    sh_b, sh_a = bf["600001.SS"][0], af["600001.SS"][0]
    check("a Shanghai pair is cut at 2014-11-17, with the step across the date in neither cell",
          sh_b[-1] == dt.date(2014, 11, 16) and sh_a[0] == dt.date(2014, 11, 17) and len(sh_b) + len(sh_a) == 40
          and (len(sh_b) - 1) + (len(sh_a) - 1) == 38)
    check("a Shenzhen pair has no after before 2016-12-05, and a STAR pair's days before 2021-02-01 are in no cell",
          "000001.SZ" in bf and "000001.SZ" not in af and "688001.SS" not in bf
          and af["688001.SS"][0][0] == dt.date(2021, 2, 1) and cnt["star_points_not_read"] == 12
          and cnt["star_pairs_with_points_before"] == 1, cnt)
    check("the entry lag drops days only from pairs that entered after their date",
          len(af10["601999.SS"][0]) == 40 and len(af["601999.SS"][0]) == 50 and len(af10["600001.SS"][0]) == len(sh_a)
          and len(af10["688001.SS"][0]) == len(af["688001.SS"][0]))

    # --- the cache
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cfg = R.base_config("read", "toy", m.as_units({0: np.arange(6.0)}), k=5)
        p = R.cache_path("read", "toy", cache=tmp)
        R.save(p, cfg, {"x": 1})
        ok1 = R.load(p, cfg) == {"x": 1}
        other = R.base_config("read", "toy", m.as_units({0: np.arange(7.0)}), k=5)
        ok2 = R.load(p, other) is None
        text = p.read_text(encoding="utf-8")
        p.write_text(text[: len(text) // 2], encoding="utf-8")
        ok3 = R.load(p, cfg) is None
        p.write_text(json.dumps({"config": cfg, "result": {"x": 1}}), encoding="utf-8")
        ok4 = R.load(p, cfg) is None
        R.save(p, cfg, {"x": 1}, complete=False)
        ok5 = R.load(p, cfg) is None and R.load(p, cfg, partial=True) == ({"x": 1}, False)
        check("a kept file is read back; one made from other data, cut short, without its completion mark, or "
              "unfinished is not", ok1 and ok2 and ok3 and ok4 and ok5, (ok1, ok2, ok3, ok4, ok5))
        c1 = R.claim("read", "toy", None, "r1", cache=tmp)
        c2 = R.claim("read", "toy", None, "r1", cache=tmp)
        c3 = R.claim("read", "toy", None, "r2", cache=tmp)
        check("a job is claimed once under one run id, and again under a new one", c1 and not c2 and c3)

    check("the far-point knob takes a verdict away only when it lands on the other side",
          knob_flips("above", {"0.5": {"state": "below"}}) and not knob_flips("above", {"0.5": {"state": "inside"}})
          and not knob_flips("inside", {"0.5": {"state": "below"}}))
    r = fixed({"a": 0.1 + 0.2, "b": [np.float64(1) / 3, float("nan")], 3: np.int64(4)})
    check("floats are written through one format", r == {"a": 0.3, "b": [0.333333, None], "3": 4}, r)

    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--import-plant", help="directory of printed --plant outputs to keep as capacity lines")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", help="with --run: write the record here instead of results/")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.import_plant:
        return import_plant(a.import_plant)
    if a.selftest:
        return selftest()
    if a.run:
        return run(Path(a.out) if a.out else None)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
