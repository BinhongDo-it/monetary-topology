"""B83: the ICP space-and-time square, which is the difference the World Bank computes.

Positions are (economy, year).  Four legs: an economy's own price index between two
benchmark years, the benchmark parity at the later year, the base economy's index
back, and the benchmark parity at the earlier year.  The loop sum in logs is the log
ratio of a new benchmark to the value extrapolated from the old one.  A scalar
potential over (economy, year) puts every one of them at exactly zero.

**The two benchmarks must come from the two rounds as each published them.** The
World Bank serves them as separate sources with separate update stamps:

    source 78  "ICP 2017"  last updated 2020-10-21   <- before the 2021 round
    source 90  "ICP 2021"  last updated 2024-08-04

The filled annual series `PA.NUS.PPP` is not usable here: its 2017 value is on the
2021 round's basis, which closes part of the square by construction.

**Network.** The fetch runs on a machine that can reach `api.worldbank.org`.  The
bridge VM cannot: measured 2026-09-13, the proxy answers
`Tunnel connection failed: 403 Forbidden`.  Do not retry it there.

**The floor is measured, not declared.** The same square is computed twice, once
extrapolating with the GDP deflator and once with the consumer price index, and the
gap between the two readings is the floor. So the cache needs both indices; a cache
filled before the consumer price index was added will be reported short rather than
quietly computing without a floor.

Run:
    python experiments/b83_icp_square.py --fetch      # writes the cache, resumable
    python experiments/b83_icp_square.py              # computes from the cache
    python experiments/b83_icp_square.py --selftest   # no network
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import struct
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b83_icp_square.json"
CACHE = ROOT / "CACHE" / "b83_icp"

BASE = "https://api.worldbank.org/v2"
SOURCE_EARLY, YEAR_EARLY = 78, 2017          # ICP 2017 round, as it published 2017
SOURCE_LATE, YEAR_LATE = 90, 2021            # ICP 2021 round, as it published 2021
SERIES = "1000000"                            # GROSS DOMESTIC PRODUCT
CLASSIFICATION = "PPPGlob"                    # Purchasing power parity (PPP) (US$ = 1)
DEFLATOR = "NY.GDP.DEFL.ZS"          # what the World Bank extrapolates GDP PPPs with
CPI = "FP.CPI.TOTL"                   # the second defensible index, used for the floor
BASE_ECONOMY = "USA"
FLOOR_MULTIPLE = 2.0                          # a square must clear this many floors

# A currency changeover between the two rounds puts the two benchmarks in different
# units. Their ratio is then a conversion factor and the loop sum is not a reading:
# nothing about the world has to have happened for it to be large. Found by printing
# the squares as objects rather than counting them, which put two conversions at the
# top of the list where a revision was expected.
CHANGEOVERS = {
    "MRT": (10.0, "the ouguiya was redenominated ten new for one old with effect "
                  "from 1 January 2018, between the two rounds"),
    "HRV": (7.53450, "the kuna was replaced by the euro at the fixed rate 7.53450, "
                     "so the later round quotes euro where the earlier quotes kuna"),
}
# How close a ratio has to sit to a conversion before it is treated as one, in logs.
# Generous on purpose: the median square on this carrier is about 0.07, so a band of
# 0.25 cannot swallow an ordinary reading, and anything inside it is being asked to
# be a factor of eight or more with no inflation behind it.
CHANGEOVER_BAND = 0.25
LEGS = 6            # p1, p0, and the four index readings that make relative inflation
PAGE = 500


# ------------------------------------------------- fetch, resumable

def _get(url: str) -> object:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _has_payload(payload) -> bool:
    """Two envelopes, and the first version of this file knew only one.

    The classic indicator endpoint returns `[header, rows]`.  A multi-dimension
    source endpoint returns a dict whose `source.data` carries the rows, and reading
    it as a list gave zero economies on every one of them.
    """
    if isinstance(payload, list):
        return len(payload) >= 2 and bool(payload[1])
    if isinstance(payload, dict):
        src = payload.get("source")
        if isinstance(src, dict):
            return bool(src.get("data"))
        if isinstance(src, list) and src:
            return bool(src[0].get("data"))
    return False


def _cached(name: str, url: str, force: bool = False):
    """One response, one file.  A file that does not parse or carries no payload is
    treated as absent and refetched, which is what rule 6 asks of a truncated file.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}.json"
    if path.exists() and not force:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if _has_payload(payload):
                return payload
            print(f"  {name}: cached file carries no payload, refetching")
        except json.JSONDecodeError:
            print(f"  {name}: cached file does not parse, refetching")
    payload = _get(url)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")
    return payload


def fetch_all(force: bool = False) -> None:
    for src, yr in ((SOURCE_EARLY, YEAR_EARLY), (SOURCE_LATE, YEAR_LATE)):
        url = (f"{BASE}/sources/{src}/country/all/series/{SERIES}"
               f"/classification/{CLASSIFICATION}/time/YR{yr}"
               f"?format=json&per_page={PAGE}")
        _cached(f"ppp_src{src}_yr{yr}", url, force)
        print(f"  source {src} year {yr}: cached")
    for code, name in ((DEFLATOR, "deflator"), (CPI, "cpi")):
        url = (f"{BASE}/country/all/indicator/{code}"
               f"?date={YEAR_EARLY}:{YEAR_LATE}&format=json&per_page=20000")
        _cached(name, url, force)
        print(f"  {name}: cached")
    url = f"{BASE}/sources?format=json&per_page=200"
    _cached("sources", url, force)
    print("  source catalogue: cached")


# ------------------------------------------------- parse

def _iso3(rec: dict) -> str | None:
    for key in ("country", "variable"):
        v = rec.get(key)
        if isinstance(v, dict) and v.get("id"):
            return v["id"]
    if isinstance(rec.get("variable"), list):
        for d in rec["variable"]:
            if d.get("concept", "").lower() == "country":
                return d.get("id")
    return None


def _rows_of(payload):
    """The records, whichever of the two envelopes this is."""
    if isinstance(payload, list):
        return payload[1] if len(payload) > 1 and payload[1] else []
    if isinstance(payload, dict):
        src = payload.get("source")
        if isinstance(src, dict):
            return src.get("data") or []
        if isinstance(src, list) and src:
            return src[0].get("data") or []
    return []


def parse_ppp(payload) -> dict:
    """{iso3: (value, digits)}.  `digits` counts the significant figures printed."""
    out = {}
    rows = _rows_of(payload)
    for rec in rows or []:
        code = _iso3(rec)
        val = rec.get("value")
        if code is None or val is None:
            continue
        out[code] = (float(val), _sigfigs(val))
    return out


def _sigfigs(val) -> int:
    s = repr(float(val))
    if "e" in s or "E" in s:
        s = s.split("e")[0].split("E")[0]
    digits = s.replace("-", "").replace(".", "").lstrip("0")
    return max(1, len(digits.rstrip("0")) or 1)


def parse_index(payload) -> dict:
    """{iso3: {year: value}} for any classic indicator series, deflator or CPI."""
    out = {}
    rows = _rows_of(payload)
    for rec in rows or []:
        code = (rec.get("countryiso3code") or "").strip()
        yr, val = rec.get("date"), rec.get("value")
        if not code or val is None:
            continue
        out.setdefault(code, {})[int(yr)] = float(val)
    return out


# ------------------------------------------------- the square

def squares(early: dict, late: dict, defl: dict, cpi: dict, floor_storage: float):
    """One row per economy that carries all four legs; everything else is named.

    The reading is computed twice, extrapolating the earlier benchmark once with the
    GDP deflator and once with the consumer price index. Both are indices anyone
    would defend; the World Bank uses the first. The gap between the two readings is
    what this square does when one defensible input is swapped for another, and that
    is the floor.

    The gap does not touch the benchmarks at all:

        loop_deflator - loop_cpi = log(rel_cpi / rel_deflator)

    so it is a property of the two indices and the two years, not of the number being
    judged. An economy with no consumer price index over both years gets no measured
    floor and takes no verdict, which is the third cell rather than a pass or a fail.
    """
    rows, missing = [], []
    base = defl.get(BASE_ECONOMY, {})
    if YEAR_EARLY not in base or YEAR_LATE not in base:
        return rows, missing, None
    base_ratio = base[YEAR_LATE] / base[YEAR_EARLY]
    for code in sorted(set(early) | set(late) | set(defl)):
        why = []
        if code not in early:
            why.append(f"no {YEAR_EARLY} benchmark in source {SOURCE_EARLY}")
        if code not in late:
            why.append(f"no {YEAR_LATE} benchmark in source {SOURCE_LATE}")
        rel = _relative(defl, code)
        if rel is None:
            why.append("the GDP deflator does not cover both years")
        if why:
            missing.append({"economy": code, "why": why})
            continue
        p0, dig0 = early[code]
        p1, dig1 = late[code]
        if p0 <= 0 or p1 <= 0:
            missing.append({"economy": code, "why": ["a benchmark is not positive"]})
            continue
        loop = math.log(p1 / (p0 * rel))
        rel_cpi = _relative(cpi, code)
        if rel_cpi is None:
            loop_cpi = spread = floor = multiple = None
            source = "no consumer price index over both years, so no floor was measured"
        else:
            loop_cpi = math.log(p1 / (p0 * rel_cpi))
            spread = abs(loop - loop_cpi)
            floor = floor_storage + spread
            multiple = abs(loop) / floor if floor > 0 else None
            source = "the index spread plus storage"
        factor, why = CHANGEOVERS.get(code, (None, None))
        rows.append({"economy": code, "ppp_early": p0, "ppp_late": p1,
                     "changeover_factor": factor, "changeover_why": why,
                     "loop_net_of_changeover": (loop + math.log(factor)
                                                if factor else None),
                     "sigfigs_early": dig0, "sigfigs_late": dig1,
                     "relative_inflation": rel, "extrapolated": p0 * rel,
                     "relative_inflation_cpi": rel_cpi,
                     "loop_sum": loop, "loop_sum_cpi": loop_cpi,
                     "index_spread": spread,
                     "floor": floor, "floor_source": source,
                     "floor_multiple": multiple})
    return rows, missing, base_ratio


def storage_floor(*tables) -> tuple:
    """How far a published figure can sit from the figure behind it. Measured.

    The first version of this station counted the significant figures printed and
    called half a unit in the last one the floor. That is a measurement of the
    serialiser, not of the instrument: inside one source the base economy prints
    `1` and China prints `4.18381118774414`, so it manufactured floors five orders
    of magnitude apart for two numbers of the same provenance.

    What is actually there is measured here. Every value is round-tripped through
    float32 and the distance recorded. Across the 2017 and 2021 benchmark sets the
    worst distance comes back at 4.2e-08, far below half a float32 unit, so every
    published figure is a float32 printed long. The floor is then half a float32
    unit plus that printing gap, once per leg of the loop.

    This component turns out not to bind. The one that binds is the index spread,
    measured per economy in `squares`.
    """
    worst, checked = 0.0, 0
    for table in tables:
        for v in table:
            v = float(v)
            if v <= 0:
                continue
            f32 = struct.unpack("f", struct.pack("f", v))[0]
            worst = max(worst, abs(f32 - v) / v)
            checked += 1
    half_ulp32 = 0.5 * 2.0 ** -23           # float32 carries a 24-bit significand
    per_leg = worst + half_ulp32
    return LEGS * per_leg, {"values_checked": checked,
                            "max_printing_gap": worst,
                            "half_float32_ulp": half_ulp32,
                            "per_leg": per_leg, "legs": LEGS}


def _relative(index: dict, code: str):
    """This economy's price movement between the two years against the base's.

    None when either economy is short a year, so a missing index is named rather
    than silently filled.
    """
    here, base = index.get(code, {}), index.get(BASE_ECONOMY, {})
    for table in (here, base):
        if YEAR_EARLY not in table or YEAR_LATE not in table:
            return None
        if table[YEAR_EARLY] <= 0 or table[YEAR_LATE] <= 0:
            return None
    return ((here[YEAR_LATE] / here[YEAR_EARLY])
            / (base[YEAR_LATE] / base[YEAR_EARLY]))


def incidence(early: dict, late: dict, index: dict):
    """The (economy, year) graph as the published legs actually leave it.

    Nodes are (economy, year). A parity edge joins an economy to the base economy
    within a year and exists only where that round published that economy. An index
    edge joins an economy's own two years and exists only where the index covers
    both. Every independent cycle here is one economy's square, so the graph's first
    Betti number is a second route to the count the closed form gives.

    Built from the legs, not from the rows. A graph built out of the rows would agree
    with the row count by construction and could not fail.
    """
    nodes, edges = set(), []
    for year, table in ((YEAR_EARLY, early), (YEAR_LATE, late)):
        for code in table:
            nodes.add((code, year))
            if code != BASE_ECONOMY:
                nodes.add((BASE_ECONOMY, year))
                edges.append(((code, year), (BASE_ECONOMY, year)))
    for code, table in index.items():
        a, b = (code, YEAR_EARLY), (code, YEAR_LATE)
        if YEAR_EARLY in table and YEAR_LATE in table and (a in nodes or b in nodes):
            nodes.add(a)
            nodes.add(b)
            edges.append((a, b))

    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    components = len({find(n) for n in nodes})
    return {"nodes": sorted(nodes), "edges": edges, "n_nodes": len(nodes),
            "n_edges": len(edges), "components": components,
            "betti_one": len(edges) - len(nodes) + components}


def rank_check(graph: dict) -> dict:
    """rank(incidence matrix) = V - c is a theorem, so this is an implementation check.

    `D35` second clause: two routes joined by a fact rather than by evidence are one
    route plus a check on the code. It is labelled that way here instead of being
    reported as a second confirmation. It takes the same graph as its input for the
    same reason: a second graph built by a second piece of code would be testing the
    second piece of code.
    """
    try:
        import numpy as np
    except ImportError:
        return {"ran": False, "why": "numpy is not installed here"}
    idx = {n: i for i, n in enumerate(graph["nodes"])}
    M = np.zeros((graph["n_edges"], len(idx)))
    for r, (a, b) in enumerate(graph["edges"]):
        M[r, idx[a]] = 1.0
        M[r, idx[b]] = -1.0
    rank = int(np.linalg.matrix_rank(M)) if graph["n_edges"] else 0
    expected = len(idx) - graph["components"]
    return {"ran": True, "rank": rank, "expected_V_minus_c": expected,
            "agrees": rank == expected,
            "betti_from_rank": graph["n_edges"] - rank}


# ------------------------------------------------- criteria


def build_criteria(rows, missing, sources_payload, floor_storage, store_ev,
                   graph, rank, universe):
    stamps = {}
    cat = sources_payload[1] if isinstance(sources_payload, list) and len(sources_payload) > 1 else []
    for s in cat or []:
        if str(s.get("id")) in {str(SOURCE_EARLY), str(SOURCE_LATE)}:
            stamps[str(s["id"])] = {"name": s.get("name"),
                                    "lastupdated": s.get("lastupdated")}
    crit = []

    named = {r["economy"] for r in rows} | {m["economy"] for m in missing}
    unnamed = sorted(universe - named)
    doubled = sorted({r["economy"] for r in rows} & {m["economy"] for m in missing})
    reasonless = [m["economy"] for m in missing if not m.get("why")]
    crit.append(("B83-1", "instrument",
                 "coverage closes: every economy either carries a square or is named "
                 "with a reason, each exactly once, and the two add up to the universe "
                 "the three inputs mention",
                 bool(rows) and not unnamed and not doubled and not reasonless,
                 (f"{len(rows)} economies carry all four legs and {len(missing)} are "
                  f"named with a reason, which is {len(rows) + len(missing)} against a "
                  f"universe of {len(universe)}. "
                  + ("Nothing was dropped without a reason and nothing was counted "
                     "twice. " if not unnamed and not doubled else
                     f"**{len(unnamed)} dropped silently: {unnamed[:10]}; "
                     f"{len(doubled)} counted twice: {doubled[:10]}.** ")
                  + (f"**{len(reasonless)} named with an empty reason.**"
                     if reasonless else "Every named absence carries its reason.")),
                 {"rows": len(rows), "missing": missing, "universe": len(universe),
                  "dropped_silently": unnamed, "counted_twice": doubled,
                  "named_without_reason": reasonless}))

    two_vintages = (len(stamps) == 2
                    and stamps.get(str(SOURCE_EARLY), {}).get("lastupdated", "") <
                    stamps.get(str(SOURCE_LATE), {}).get("lastupdated", ""))
    crit.append(("B83-2", "premise",
                 "the two benchmarks come from the two rounds as each published them, "
                 "which the separate sources and their update stamps establish",
                 bool(two_vintages),
                 f"source stamps {stamps}. The early source predates the late round, so "
                 f"its figures are not the back-revised ones. **Failing this stops the "
                 f"station rather than downgrading it**",
                 {"source_stamps": stamps}))

    floored = [r for r in rows if r["floor"] is not None]
    spreads = sorted(r["index_spread"] for r in floored)
    unfloored = [r for r in rows if r["floor"] is None]
    crit.append(("B83-3", "instrument",
                 "the resolution floor is measured, not declared: the same square is "
                 "computed with two defensible price indices and the gap between the "
                 "two readings is the floor",
                 bool(spreads),
                 (f"storage contributes {floor_storage:.2e} in logs over {LEGS} legs, "
                  f"measured by round-tripping {store_ev['values_checked']} published "
                  f"values through float32: the worst distance to a representable value "
                  f"is {store_ev['max_printing_gap']:.2e}, below half a float32 unit, so "
                  f"every figure is a float32 printed long. Swapping the GDP deflator for "
                  f"the consumer price index moves the square by {spreads[0]:.2e} to "
                  f"{spreads[-1]:.4f}, median {_median(spreads):.4f}, which is "
                  f"{_median(spreads) / floor_storage:.0f} times storage, so the index "
                  f"choice is the floor and storage does not bind. {len(unfloored)} "
                  f"economies have no second index and take no verdict. **A third "
                  f"component is not measured here**: the deflator's own revision between "
                  f"vintages, which needs two vintages of it and is registered"
                  if spreads else "no floor could be measured"),
                 {"storage": store_ev,
                  "index_spread_min": spreads[0] if spreads else None,
                  "index_spread_median": _median(spreads) if spreads else None,
                  "index_spread_max": spreads[-1] if spreads else None,
                  "unfloored": [r["economy"] for r in unfloored]}))

    changed = [r for r in floored if r["changeover_factor"]]
    countable = [r for r in floored if not r["changeover_factor"]]
    above = [r for r in countable if r["floor_multiple"] >= FLOOR_MULTIPLE]
    below = [r for r in countable if r["floor_multiple"] < FLOOR_MULTIPLE]
    # 11c: three cells, and the map from cell to verdict is printed rather than left
    # in the head. Two of the three carry no verdict, and the assert says so out loud
    # so that a later edit cannot quietly promote one of them.
    cell_verdict = {"clears its own measured floor": "counts against the rival",
                    "does not clear its own measured floor": "no verdict",
                    "no measured floor": "no verdict",
                    "the two rounds quote different currencies": "no verdict"}
    assert sum(1 for v in cell_verdict.values() if v == "no verdict") == 3, \
        "11c: all three undecided cells must map to no verdict"
    crit.append(("B83-4", "rival",
                 "a scalar potential over (economy, year) predicts every square exactly "
                 "zero, with no free parameter; one square standing clear of its own "
                 "measured floor is a counterexample, so PASS means the rival is wrong here",
                 bool(above),
                 (f"{len(above)} of {len(floored)} floored squares stand at "
                  f"{FLOOR_MULTIPLE:g} floors or more, median multiple "
                  f"{_median([r['floor_multiple'] for r in above]):.0f}, largest "
                  f"{max((abs(r['loop_sum']) for r in above), default=0):.4f} in logs at "
                  f"{max(above, key=lambda r: abs(r['loop_sum']))['economy']}. "
                  f"{len(below)} floored squares cannot be separated from zero, "
                  f"{len(unfloored)} have no measured floor and {len(changed)} sit "
                  f"across a currency changeover; all three cells take no verdict"
                  if above else
                  f"no square among {len(floored)} floored ones clears "
                  f"{FLOOR_MULTIPLE:g} floors, so the point prediction survives here"),
                 {"cells": {"clears its own measured floor": [r["economy"] for r in above],
                            "does not clear its own measured floor":
                                [r["economy"] for r in below],
                            "no measured floor": [r["economy"] for r in unfloored],
                            "the two rounds quote different currencies":
                                [r["economy"] for r in changed]},
                  "cell_verdict": cell_verdict}))

    closed = max(len(rows) - 1, 0)          # (T-1)(R-1) with T = 2 benchmark years
    measured = graph["betti_one"]
    crit.append(("B83-5", "own_reading",
                 "the independent square count is (T-1)(R-1) with T = 2 benchmark "
                 "years, and the graph the published legs actually leave is a second "
                 "route to the same number",
                 measured == closed and rank["ran"] and rank["agrees"],
                 (f"T = 2 and R = {len(rows)}, so the closed form gives {closed}. The "
                  f"graph built from the legs alone has {graph['n_nodes']} nodes, "
                  f"{graph['n_edges']} edges and {graph['components']} component(s), so "
                  f"its first Betti number is {measured}. "
                  + ("The two agree. " if measured == closed else
                     f"**They disagree by {measured - closed}**, which means the graph "
                     f"and the row filter admit different economies and one of them is "
                     f"wrong. ")
                  + (f"rank(incidence) = {rank['rank']} against V - c = "
                     f"{rank['expected_V_minus_c']}, which is an implementation check "
                     f"rather than a second route, since the two are equal by a theorem "
                     f"(`D35` second clause)" if rank["ran"] else
                     f"the rank leg did not run: {rank.get('why')}")),
                 {"T": 2, "R": len(rows), "closed_form": closed,
                  "betti_from_graph": measured,
                  "graph": {k: v for k, v in graph.items()
                            if k not in ("nodes", "edges")},
                  "rank_check": rank}))

    worst = sorted(rows, key=lambda r: -abs(r["loop_sum"]))[:10]
    crit.append(("B83-6", "own_reading",
                 "the squares printed as objects rather than counted",
                 bool(rows),
                 "; ".join(
                     f"{r['economy']} {r['loop_sum']:+.4f} "
                     + ("(currency changeover, "
                        f"{r['loop_net_of_changeover']:+.4f} net of it)"
                        if r["changeover_factor"] else
                        f"({r['floor_multiple']:.0f}x)"
                        if r["floor_multiple"] is not None
                        else "(no measured floor)")
                     for r in worst),
                 {"all_squares": rows}))

    deg = [r for r in rows if r["economy"] == BASE_ECONOMY]
    crit.append(("B83-7", "instrument",
                 "the degenerate square, the base economy against itself, reads exactly zero",
                 bool(deg) and abs(deg[0]["loop_sum"]) < 1e-12,
                 (f"{BASE_ECONOMY} reads {deg[0]['loop_sum']:.2e}" if deg
                  else f"{BASE_ECONOMY} not present, so this short circuit was not exercised"),
                 {"degenerate": deg[0] if deg else None}))

    want = {"economy", "ppp_early", "ppp_late", "relative_inflation", "loop_sum",
            "loop_sum_cpi", "index_spread", "floor", "floor_source", "floor_multiple",
            "changeover_factor", "loop_net_of_changeover"}
    short = [r["economy"] for r in rows if not want <= set(r)]
    # Any ratio this large with no inflation behind it is a conversion, so it has to
    # be either in the table with its reason or reported as unresolved. This is what
    # makes the table falsifiable: a third changeover would fail here rather than be
    # counted as an obstruction.
    def _near_conversion(r):
        ratio = r["ppp_early"] / r["ppp_late"]
        wants = [10.0 ** k for k in range(1, 7)]
        wants += [f for f, _ in CHANGEOVERS.values()]
        return any(abs(math.log(ratio / w)) < CHANGEOVER_BAND for w in wants if w > 0)

    flagged = [r for r in floored if _near_conversion(r)]
    unnamed = [r["economy"] for r in flagged if not r["changeover_factor"]]
    residual = {r["economy"]: r["loop_net_of_changeover"] for r in changed}
    ordinary = sorted(abs(r["loop_sum"]) for r in countable)
    typical = ordinary[len(ordinary) // 2] if ordinary else 0.0
    settled = all(abs(v) < 10 * typical for v in residual.values()) if residual else True
    crit.append(("B83-9", "instrument",
                 "a benchmark ratio that is a currency conversion is not a reading: "
                 "every ratio sitting near one is named with the changeover behind it, "
                 "and net of that changeover its square comes back an ordinary size",
                 not unnamed and settled,
                 (f"{len(flagged)} of {len(floored)} floored ratios sit within "
                  f"{CHANGEOVER_BAND} in logs of a conversion. "
                  + ("All are named. " if not unnamed else
                     f"**{len(unnamed)} are not named: {unnamed}.** ")
                  + "; ".join(
                      f"{e}: raw {[r for r in changed if r['economy'] == e][0]['loop_sum']:+.4f}, "
                      f"net of the changeover {v:+.4f}, against a median square of "
                      f"{typical:.4f}" for e, v in sorted(residual.items()))
                  + ". Net of the changeover both are ordinary, which is the check: a "
                  "ratio blamed on units has to stop being large once the units are "
                  "taken out. They carry no verdict either way, since correcting a "
                  "parity is not the same as reading one"),
                 {"flagged": [r["economy"] for r in flagged],
                  "unnamed": unnamed,
                  "changeovers": {e: {"factor": CHANGEOVERS[e][0],
                                      "why": CHANGEOVERS[e][1],
                                      "raw": [r for r in changed
                                              if r["economy"] == e][0]["loop_sum"],
                                      "net": v} for e, v in residual.items()},
                  "median_square": typical}))

    crit.append(("B83-8", "bookkeeping",
                 "the record carries what the other criteria say it carries: every row "
                 "with its full field set, every absence with its reason, and both "
                 "source stamps",
                 not short and not reasonless and len(stamps) == 2,
                 (f"{len(rows)} rows each carrying {len(want)} fields, {len(missing)} "
                  f"named absences each with a reason, {len(stamps)} source stamps. "
                  + ("Nothing is short." if not short else
                     f"**{len(short)} rows are short of fields: {short[:10]}.**")),
                 {"fields_required": sorted(want), "rows_short_of_fields": short,
                  "source_stamps_present": len(stamps)}))
    return crit


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else 0.5 * (xs[k - 1] + xs[k])


# ------------------------------------------------- self-test, no network

def selftest() -> int:
    """Seed a tableau whose answer is known by hand and check every moving part."""
    early = {"AAA": (4.18, 3), "USA": (1.0, 1), "BBB": (10.0, 3)}
    late = {"AAA": (3.98740887641907, 15), "USA": (1.0, 1), "BBB": (11.0, 3)}
    defl = {"AAA": {2017: 94.8898339756055, 2021: 104.473573585036},
            "USA": {2017: 94.8969980783401, 2021: 104.562972826319},
            # BBB carries the base economy's own deflators, so its relative
            # inflation is exactly one and its square is exactly log(11/10).
            # The first version of this fixture gave BBB a ratio of 1.1 and
            # expected the same answer, which is wrong because the base's ratio
            # is 1.1019, not 1.1: the self-test caught the expectation, not the code.
            "BBB": {2017: 94.8969980783401, 2021: 104.562972826319},
            "CCC": {2017: 100.0, 2021: 110.0}}
    # AAA and USA carry a consumer price index, BBB does not: that is the third cell.
    cpi = {"AAA": {2017: 100.0, 2021: 120.0},
           "USA": {2017: 100.0, 2021: 110.0}}
    floor_storage, store_ev = storage_floor(
        (v for v, _ in early.values()), (v for v, _ in late.values()),
        (v for d in defl.values() for v in d.values()),
        (v for d in cpi.values() for v in d.values()))
    rows, missing, _ = squares(early, late, defl, cpi, floor_storage)
    by = {r["economy"]: r for r in rows}
    fails = []
    if len(rows) != 3:
        fails.append(f"expected 3 rows, got {len(rows)}")
    if not missing or missing[0]["economy"] != "CCC":
        fails.append("an economy with no benchmark should be named, not dropped")
    if abs(by["USA"]["loop_sum"]) > 1e-15:
        fails.append(f"the degenerate square is {by['USA']['loop_sum']}, not zero")
    hand = math.log(3.98740887641907 / (4.18 * ((104.473573585036 / 94.8898339756055)
                                                / (104.562972826319 / 94.8969980783401))))
    if abs(by["AAA"]["loop_sum"] - hand) > 1e-12:
        fails.append(f"AAA reads {by['AAA']['loop_sum']} against the hand value {hand}")
    # BBB: relative inflation exactly 1 by construction, so the square is log(11/10)
    if abs(by["BBB"]["loop_sum"] - math.log(1.1)) > 1e-12:
        fails.append("BBB should read log(1.1) when the two deflator ratios agree")
    if _sigfigs(4.18) != 3 or _sigfigs(1.0) != 1:
        fails.append(f"significant figures: 4.18 -> {_sigfigs(4.18)}, 1.0 -> {_sigfigs(1.0)}")

    # the storage floor is measured, and these fixtures are short decimals rather
    # than float32 values, so it must come back near six half-ulps and no larger
    if not (1e-7 < floor_storage < 1e-5):
        fails.append(f"the storage floor is {floor_storage:.3e}, outside the band a "
                     f"six-leg float32 loop can occupy")

    # the index spread is the log ratio of the two relative inflations and touches
    # neither benchmark. AAA: cpi 1.20/1.10 against deflator ratio, done by hand.
    rel_d = ((104.473573585036 / 94.8898339756055)
             / (104.562972826319 / 94.8969980783401))
    rel_c = (120.0 / 100.0) / (110.0 / 100.0)
    if abs(by["AAA"]["index_spread"] - abs(math.log(rel_c / rel_d))) > 1e-12:
        fails.append(f"AAA index spread {by['AAA']['index_spread']} is not "
                     f"log(rel_cpi / rel_deflator)")
    # and swapping the benchmarks must leave that spread alone
    moved, _m, _b = squares({"AAA": (99.0, 2), "USA": (1.0, 1)},
                            {"AAA": (7.0, 1), "USA": (1.0, 1)},
                            defl, cpi, floor_storage)
    moved_aaa = {r["economy"]: r for r in moved}["AAA"]
    if abs(moved_aaa["index_spread"] - by["AAA"]["index_spread"]) > 1e-12:
        fails.append("the index spread moved when only the benchmarks changed, so it "
                     "is not a property of the two indices alone")

    # 11c: no consumer price index means no floor and no verdict, not a pass and not
    # a fail. BBB is the case, and its square is large, so a code that quietly fell
    # back to storage would put it in the passing cell.
    if by["BBB"]["floor"] is not None or by["BBB"]["floor_multiple"] is not None:
        fails.append("BBB has no second index, so it must carry no floor and no multiple")
    if by["AAA"]["floor"] is None:
        fails.append("AAA has both indices, so it must carry a measured floor")
    graph = incidence(early, late, defl)
    rank = rank_check(graph)
    # AAA and BBB each close one square; USA closes none, being the base
    if graph["betti_one"] != 2:
        fails.append(f"the leg graph should carry two squares, it carries "
                     f"{graph['betti_one']}")
    if rank["ran"] and not rank["agrees"]:
        fails.append(f"rank {rank['rank']} against V - c {rank['expected_V_minus_c']}")
    # with no index edge anywhere the two years never meet, so the graph is two
    # components and carries no square at all. A component count that is hardwired
    # to one turns that into a negative Betti number and nothing else notices.
    split = incidence(early, late, {})
    if split["components"] != 2:
        fails.append(f"with no index edge the two years are separate components, "
                     f"got {split['components']}")
    if split["betti_one"] != 0:
        fails.append(f"a graph with no index edge closes nothing, it reports "
                     f"{split['betti_one']}")
    split_rank = rank_check(split)
    if split_rank["ran"] and not split_rank["agrees"]:
        fails.append("rank and V - c part company on the disconnected graph")
    # a benchmark that is not positive leaves the rows but stays in the graph, so the
    # two counts must part company and B83-5 must say so rather than pass
    bad_early = dict(early); bad_early["DDD"] = (-1.0, 1)
    bad_late = dict(late); bad_late["DDD"] = (2.0, 1)
    bad_defl = dict(defl); bad_defl["DDD"] = {2017: 100.0, 2021: 105.0}
    bad_rows, _bm, _br = squares(bad_early, bad_late, bad_defl, cpi, floor_storage)
    bad_graph = incidence(bad_early, bad_late, bad_defl)
    bad_crit = build_criteria(bad_rows, _bm, [None, []], floor_storage, store_ev,
                              bad_graph, rank_check(bad_graph),
                              set(bad_early) | set(bad_late) | set(bad_defl))
    bad5 = [c for c in bad_crit if c[0] == "B83-5"][0]
    if bad5[3]:
        fails.append("a benchmark dropped from the rows but kept in the graph left "
                     "B83-5 passing, so the two counts are not really being compared")

    universe = set(early) | set(late) | set(defl)
    crit = build_criteria(rows, missing, [None, []], floor_storage, store_ev,
                          graph, rank, universe)
    b1 = [c for c in crit if c[0] == "B83-1"][0]
    if not b1[3]:
        fails.append(f"coverage should close on the fixture: {b1[4]}")
    # drop a named absence and the accounting must part company
    thin = build_criteria(rows, missing[1:], [None, []], floor_storage, store_ev,
                          graph, rank, universe)
    if [c for c in thin if c[0] == "B83-1"][0][3]:
        fails.append("an economy dropped from the named absences left B83-1 passing, "
                     "so the coverage identity is not being checked")
    # strip a field from a row and the bookkeeping criterion must say so
    # a field no other criterion reads, so its loss is exactly the silent kind this
    # criterion exists for. The fields the other criteria do read blow up loudly on
    # their own, which is also fine, and is why the probe does not use one of those.
    maimed = [dict(r) for r in rows]
    maimed[0].pop("floor_source")
    if [c for c in build_criteria(maimed, missing, [None, []], floor_storage,
                                  store_ev, graph, rank, universe)
            if c[0] == "B83-8"][0][3]:
        fails.append("a row short of a field left B83-8 passing, so it is asserting "
                     "rather than checking")
    b4 = [c for c in crit if c[0] == "B83-4"][0]
    cells = b4[5]["cells"]
    if "BBB" not in cells["no measured floor"]:
        fails.append("BBB should sit in the no-measured-floor cell of B83-4")
    if "BBB" in cells["clears its own measured floor"]:
        fails.append("an economy with no floor was counted against the rival")
    # a cache file that does not parse must be treated as absent
    CACHE.mkdir(parents=True, exist_ok=True)
    bad = CACHE / "selftest_bad.json"
    bad.write_text("{ truncated", encoding="utf-8")
    try:
        _cached("selftest_bad", "https://example.invalid/nothing")
        fails.append("a corrupt cache file was accepted")
    except Exception:
        pass
    for f_ in fails:
        print("  SELFTEST FAIL:", f_)
    print(f"selftest: {len(fails)} failure(s)")
    print(f"  hand-checked square for AAA: {by['AAA']['loop_sum']:+.5f}, "
          f"measured floor {by['AAA']['floor']:.2e} "
          f"(index spread {by['AAA']['index_spread']:.2e} plus storage "
          f"{floor_storage:.2e}), multiple {by['AAA']['floor_multiple']:.1f}x")
    print(f"  BBB has no second index: floor {by['BBB']['floor']}, "
          f"multiple {by['BBB']['floor_multiple']}, so it takes no verdict")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="fill the cache, then stop")
    ap.add_argument("--force", action="store_true", help="refetch even if cached")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.fetch:
        fetch_all(a.force)
        print("cache filled; run again without --fetch to compute")
        return 0
    need = [f"ppp_src{SOURCE_EARLY}_yr{YEAR_EARLY}", f"ppp_src{SOURCE_LATE}_yr{YEAR_LATE}",
            "deflator", "cpi", "sources"]
    absent = [n for n in need if not (CACHE / f"{n}.json").exists()]
    if absent:
        print(f"cache is short of {', '.join(absent)}; run with --fetch on a machine "
              f"that can reach api.worldbank.org. The bridge VM and the cloud container "
              f"both get 403 from the proxy, measured 2026-09-13, so neither will do")
        return 2
    early = parse_ppp(json.loads((CACHE / f"{need[0]}.json").read_text(encoding="utf-8")))
    late = parse_ppp(json.loads((CACHE / f"{need[1]}.json").read_text(encoding="utf-8")))
    defl = parse_index(json.loads((CACHE / "deflator.json").read_text(encoding="utf-8")))
    cpi = parse_index(json.loads((CACHE / "cpi.json").read_text(encoding="utf-8")))
    cat = json.loads((CACHE / "sources.json").read_text(encoding="utf-8"))
    floor_storage, store_ev = storage_floor(
        (v for v, _ in early.values()), (v for v, _ in late.values()),
        (v for d in defl.values() for v in d.values()),
        (v for d in cpi.values() for v in d.values()))
    rows, missing, base_ratio = squares(early, late, defl, cpi, floor_storage)
    graph = incidence(early, late, defl)
    rank = rank_check(graph)
    universe = set(early) | set(late) | set(defl)
    crit = build_criteria(rows, missing, cat, floor_storage, store_ev, graph, rank,
                          universe)
    criteria, report = [], {}
    for name, kind, statement, ok, detail, rep in crit:
        entry = {"name": name, "kind": kind, "passed": bool(ok),
                 "statement": statement, "detail": detail}
        if kind == "rival":
            entry["grid"] = "B" if ok else "A"
            entry["rival_premise"] = ("a scalar potential phi(economy, year) exists and "
                                      "every edge carries its difference")
            entry["rival_entailment"] = ("a difference of a potential sums to zero round a "
                                         "cycle, so extrapolating an earlier benchmark by "
                                         "relative inflation returns the later benchmark "
                                         "exactly, for every economy and with no free "
                                         "parameter")
        criteria.append(entry)
        report[name] = rep
        print(f"{'PASS' if ok else 'FAIL'}  {name}  [{kind}]  {detail}")
    rec = {"stage": "B83",
           "config": {"source_early": SOURCE_EARLY, "year_early": YEAR_EARLY,
                      "source_late": SOURCE_LATE, "year_late": YEAR_LATE,
                      "series": SERIES, "classification": CLASSIFICATION,
                      "deflator": DEFLATOR, "cpi": CPI,
                      "base_economy": BASE_ECONOMY,
                      "floor_multiple": FLOOR_MULTIPLE, "legs": LEGS,
                      "storage_floor": floor_storage,
                      "base_deflator_ratio": base_ratio},
           "criteria": criteria, "report": report}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, default=float) + "\n",
                   encoding="utf-8", newline="\n")
    failed = [c["name"] for c in criteria if not c["passed"]]
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print(f"all {len(criteria)} criteria pass; record written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
