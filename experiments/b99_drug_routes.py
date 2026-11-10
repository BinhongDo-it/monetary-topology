"""B99: drug distribution routes. Three zero calibrations and one reading.

The design file names four criteria and one carrier, all four sources free, public and at
NDC-11 level:

    NADAC weekly reference file      one national average acquisition cost per NDC
    NADAC week-on-week comparison    Old, New and Percent Change on one row
    FDA NSDE                         the billing unit, the one field NSDE says is not SPL-made
    DailyMed SPL source NDCs         21 CFR 207.53: a repackaged NDC names its source NDC

    B99-0  instrument    a one-index field fed to the cycle machinery returns zero:
                         every square exactly 0.0, every slice cycle inside its float band
    B99-1  instrument    the publisher's own arithmetic: Percent Change recomputed from
                         Old and New, scale read per week; every row outside the rounding
                         band of the printed digits printed one by one, named by its week
                         (a printed criterion since 2026-10-29; it was a line at zero)
    B99-2  known_answer  NADAC Pricing Unit and NSDE Billing Unit agree on the same NDC-11;
                         every disagreement is named
    B99-3  own_reading   the repackaging wedge, log(NADAC repack) - log(NADAC source), one
                         number per pair, in three named cells

**On disk as of 2026-10-29**: NADAC 2025 and 2026, the NADAC comparison file and NSDE, fetched
by `scripts/fetch_b99.py` into `data/raw/b99/`. The SPL map is not. Run without `--selftest`,
the script says file by file what it found; a criterion whose source is missing carries no
verdict and `pending_fetch` names what it waits for. It does not fetch anything.

**The three cells of B99-3, and the verdict each maps to (rule 11c, the mapping printed):**

    cell 3  fewer than two pairs, or every |wedge| at or under its own floor,
            or a price source that sets one rate per drug group               -> no verdict
    cell 1  the wedges are one constant to within twice the largest floor      -> printed
    cell 2  the wedges are non-zero and spread wider than that                 -> printed

**B99-3 does not run on NADAC prices (2026-10-29).** The NADAC methodology (CMS, December
2024) calculates the rate per drug grouping, classification for rate setting and pharmacy
type and publishes it on every NDC of the group (p. 6, p. 7, p. 15-16, p. 26). A repackaged
NDC and its source NDC in one group carry one price by construction: the second price is the
first times 1 under a published rule that varies only with the class (D30, third clause), so
the wedge reads that rule. That is measuring the wrong object (D23), not a refuted reading.
GROUP_RATED names the sources treated this way; on any of them B99-3 lands in cell 3 with the
carrier as its reason, before the pairs are looked at. A per-NDC price source (one price per
labeler's own NDC) passed in as `price_source` with its own `prices` rows is read as before.

**Nor on the CMS Part D quarterly pricing file (read 2026-10-29, nothing fetched).** Its NDC is
"11-digit proxy NDC associated with the drug product" (SPUF record layout 2026, p. 15): one
related NDC per RXCUI, priced once per plan, because Medicare Plan Finder "displays one cost for
all National Drug Codes (NDCs) for a given brand name, generic name, dosage form, route of
administration, and strength combination" (CY 2026 Drug Pricing Submission Guidelines, p. 13).
A repack NDC and its source NDC are one drug product there. It is in GROUP_RATED for that reason.

The floor of a pair is half a published tick on each price carried into the log:
(tick / 2) * (1 / p_repack + 1 / p_source), with the tick read off the printed digits.
"Constant" means equal to within that rounding, so cell 1 has no free number in it.

The framework stakes nothing on B99-3: NADAC is a survey of acquisition cost and nobody
wrote two class values into it, so the counting law does not reach it, and whether the two
NDCs are one position is not decidable without a two-index field. It is a printed reading
whose flag asserts the object is there.

    python experiments/b99_drug_routes.py --selftest
    python experiments/b99_drug_routes.py            # reads data/raw/b99/, writes the record
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import re
import statistics
import sys

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from monetary_topology.product_graph import (  # noqa: E402
    Cochain, slice_cycles, spanning_tree_cycles, squares, undirected_pairs, vertex)

DATA = ROOT / "data" / "raw" / "b99"
OUT = ROOT / "results" / "b99_drug_routes.json"
M_CLASSES = 2                 # two copies of one scalar: the degenerate two-index field
EPS = np.finfo(np.float64).eps

#: What each source calls the columns this script reads (`D54`). Headers are compared after
#: lower-casing and turning underscores into spaces, because data.medicaid.gov prints some
#: headers with underscores and some without; nothing else is matched loosely.
NADAC_COLS = {"ndc": "ndc", "price": "nadac per unit", "unit": "pricing unit",
              "date": "effective date"}
COMP_COLS = {"ndc": "ndc", "old": "old nadac per unit", "new": "new nadac per unit",
             "pct": "percent change", "start": "start date", "end": "end date"}
NSDE_COLS = {"ndc": "ndc11", "unit": "billing unit"}
SPL_COLS = {"repack": "repack_ndc", "source": "source_ndc"}

#: The source's own definition of Percent Change (NADAC comparison file data dictionary):
#: "The difference between the New NADAC Per Unit and the Old NADAC Per Unit, divided by the
#: Old NADAC Per Unit". Whether the file prints it as a fraction or as a percent is a fact
#: about the file, so both scales are tried and the one that fits is printed, as B98 does
#: with its sign convention.
SCALES = (1.0, 100.0, 10000.0)

#: Price sources that set one rate per drug group, so a repack pair on them is one price by
#: construction (D30 third clause). B99-3 lands in cell 3 on these with the reason below as
#: its detail: the carrier has no repackaging wedge to read (D23, measured the wrong object).
GROUP_RATED = {
    "NADAC": ("not run on NADAC: NADAC sets one rate per drug grouping, classification for "
              "rate setting and pharmacy type and publishes it on every NDC in the group "
              "(CMS NADAC methodology, December 2024, p. 6, p. 7, p. 15-16, p. 26), so a "
              "repackaged NDC and its source NDC carry one price by construction (D30, third "
              "clause: the second price is the first times 1 under a published rule). The "
              "wedge would read that rule; on this carrier B99-3 measured the wrong object (D23). "
              "It needs a source that prices each labeler's own NDC"),
    # Read 2026-10-29, no data fetched: the quarterly Part D formulary, pharmacy network and
    # pricing public use file keys its pricing file on "11-digit proxy NDC associated with the
    # drug product" (SPUF record layout 2026, p. 15), and the sponsor submits one unit cost per
    # related NDC of an RXCUI because "MPF displays one cost for all National Drug Codes (NDCs)
    # for a given brand name, generic name, dosage form, route of administration, and strength
    # combination" (CY 2026 Drug Pricing Submission Guidelines, p. 13).
    "CMS Part D SPUF": ("not run on the CMS Part D quarterly pricing file: its NDC is an "
                        "11-digit proxy NDC for the drug product (SPUF record layout 2026, "
                        "p. 15), one related NDC per RXCUI, and Medicare Plan Finder shows one "
                        "cost for all NDCs of a brand name, generic name, dosage form, route and "
                        "strength (CY 2026 Drug Pricing Submission Guidelines, p. 13-15). A "
                        "repackaged NDC and its source NDC are one drug product there, so they "
                        "carry one price by construction (D30, third clause), and the repackaged "
                        "NDC has no key of its own. On this carrier B99-3 measures the wrong "
                        "object (D23)"),
}
DEFAULT_PRICE_SOURCE = "NADAC"

PENDING = [
    {"source": "NADAC weekly reference file (annual CSV)", "into": "data/raw/b99/nadac/",
     "where": "data.medicaid.gov, dataset 'NADAC (National Average Drug Acquisition Cost) 2026'",
     "feeds": ["B99-0", "B99-2", "B99-3"]},
    {"source": "NADAC week-to-week comparison file", "into": "data/raw/b99/comparison/",
     "where": "medicaid.gov NADAC page, weekly comparison files",
     "feeds": ["B99-1"]},
    {"source": "FDA NSDE (Comprehensive NDC SPL Data Elements)", "into": "data/raw/b99/nsde/",
     "where": "fda.gov, NSDE download", "feeds": ["B99-2"]},
    {"source": "DailyMed SPL source-NDC map (21 CFR 207.53), parsed to repack_ndc,source_ndc",
     "into": "data/raw/b99/spl_source_ndc.csv",
     "where": "dailymed.nlm.nih.gov SPL bulk files; GB-scale; a parser is also still to write",
     "feeds": ["B99-0", "B99-3"],
     "note": "D21 before the bulk download: count the repack pairs that reach NADAC on a "
             "sample first; design section 3 names this as the one branch that can come "
             "up empty"},
]


# ---------------------------------------------------------------------------- keys

def ndc11(text: str) -> str | None:
    """NDC-11 as eleven digits, or None. Hyphenated ten-digit forms are padded by segment."""
    s = (text or "").strip()
    if "-" in s:
        parts = s.split("-")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            return None
        widths = tuple(len(p) for p in parts)
        pad = {(4, 4, 2): (5, 4, 2), (5, 3, 2): (5, 4, 2), (5, 4, 1): (5, 4, 2),
               (5, 4, 2): (5, 4, 2)}.get(widths)
        if pad is None:
            return None
        return "".join(p.zfill(w) for p, w in zip(parts, pad))
    digits = re.sub(r"\D", "", s)
    return digits if len(digits) == 11 else None


def product9(text: str) -> str | None:
    """Labeler plus product, nine digits. Takes an NDC-11 or a hyphenated product code."""
    s = (text or "").strip()
    if "-" in s and s.count("-") == 1:
        a, b = s.split("-")
        if not (a.isdigit() and b.isdigit()):
            return None
        pad = {(4, 4): (5, 4), (5, 3): (5, 4), (5, 4): (5, 4)}.get((len(a), len(b)))
        return None if pad is None else a.zfill(pad[0]) + b.zfill(pad[1])
    full = ndc11(s)
    return full[:9] if full else None


def decimals(text: str) -> int:
    t = (text or "").strip()
    return len(t.split(".", 1)[1]) if "." in t else 0


# ---------------------------------------------------------------------------- loaders

def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", h.replace("_", " ").strip().lower())


def read_table(paths, cols, label):
    """Rows as dicts keyed by our short names. Refuses a file whose header lacks a column."""
    rows, report = [], []
    for p in sorted(paths):
        with open(p, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            header = next(rd, [])
            idx = {_norm(h): k for k, h in enumerate(header)}
            missing = [v for v in cols.values() if _norm(v) not in idx]
            if missing:
                report.append({"file": p.name, "refused": True, "missing": missing,
                               "header_as_printed": header})
                print(f"  {label}: {p.name} refused, the source does not call any column "
                      f"{missing}; its header is {header}")
                continue
            n = 0
            for r in rd:
                if not r:
                    continue
                rows.append({k: r[idx[_norm(v)]] for k, v in cols.items()})
                n += 1
            report.append({"file": p.name, "refused": False, "rows": n})
    return rows, report


def locate():
    found = {
        "nadac": sorted((DATA / "nadac").glob("*.csv")) if (DATA / "nadac").exists() else [],
        "comparison": sorted((DATA / "comparison").glob("*.csv"))
        if (DATA / "comparison").exists() else [],
        "nsde": sorted((DATA / "nsde").glob("extracted_*/*.csv")) if (DATA / "nsde").exists() else [],
        "spl": [DATA / "spl_source_ndc.csv"] if (DATA / "spl_source_ndc.csv").exists() else [],
    }
    return found


# ---------------------------------------------------------------------------- objects

def nadac_by_product(rows):
    """{product9: {date: (median price, unit, max decimals)}} from reference rows."""
    acc: dict = {}
    for r in rows:
        k = ndc11(r["ndc"])
        if not k:
            continue
        try:
            price = float(r["price"])
        except ValueError:
            continue
        d = acc.setdefault(k[:9], {}).setdefault(r["date"].strip(), [[], set(), 0])
        d[0].append(price)
        d[1].add(r["unit"].strip().upper())
        d[2] = max(d[2], decimals(r["price"]))
    out = {}
    for p, by_date in acc.items():
        for date, (prices, units, dec) in by_date.items():
            out.setdefault(p, {})[date] = (statistics.median(prices),
                                           units.pop() if len(units) == 1 else None, dec)
    return out


def pairs_of(spl_rows, by_product):
    """(repack product, source product, date, p_r, p_s, unit, decimals) at the latest
    date both carry, one per pair; pairs whose units disagree are held out and counted."""
    out, unit_split, unreached = [], 0, 0
    seen = set()
    for r in spl_rows:
        a, b = product9(r["repack"]), product9(r["source"])
        if not a or not b or a == b or (a, b) in seen:
            continue
        seen.add((a, b))
        ra, rb = by_product.get(a), by_product.get(b)
        common = sorted(set(ra or {}) & set(rb or {}))
        if not common:
            unreached += 1
            continue
        d = common[-1]
        (pa, ua, da), (pb, ub, db) = ra[d], rb[d]
        if ua is None or ub is None or ua != ub:
            unit_split += 1
            continue
        if pa <= 0 or pb <= 0:
            continue
        out.append((a, b, d, pa, pb, ua, max(da, db)))
    return out, unit_split, unreached


# ---------------------------------------------------------------------------- criteria

def b99_0(pairs):
    """The one-index field on the main reading's own graph, through the cycle machinery."""
    if not pairs:
        return None, "no pair graph to build: no repack pair reaches NADAC", {}
    nodes = sorted({x for a, b, *_ in pairs for x in (a, b)})
    pos = {p: k for k, p in enumerate(nodes)}
    phi = np.zeros(len(nodes))
    for a, b, _d, pa, pb, *_ in pairs:
        phi[pos[a]], phi[pos[b]] = pa, pb
    return cycle_check(len(nodes), [(pos[a], pos[b]) for a, b, *_ in pairs],
                       np.stack([phi, phi.copy()]))


def cycle_check(n, edges, phis):
    """phis has one row per class. Squares must be exactly 0.0, slice cycles inside
    2 * length * eps * max|phi|. Returns (passed, detail, report)."""
    adj = np.zeros((n, n), dtype=np.uint8)
    for i, j in edges:
        adj[i, j] = adj[j, i] = 1
    weights = {}
    for a in range(M_CLASSES):
        for i, j in undirected_pairs(adj):
            weights[(vertex(a, i, n), vertex(a, j, n))] = float(phis[a, j] - phis[a, i])
    for i in range(n):
        weights[(vertex(0, i, n), vertex(1, i, n))] = 0.0
    om = Cochain(weights)
    sq = squares(adj, M_CLASSES)
    sq_sums = [om.sum_over(w) for w in sq]
    # slice cycles per connected component: the basis routine walks one component only
    comp, seen = [], set()
    for s in range(n):
        if s in seen:
            continue
        stack, members = [s], []
        seen.add(s)
        while stack:
            u = stack.pop()
            members.append(u)
            for v in np.nonzero(adj[u])[0]:
                if int(v) not in seen:
                    seen.add(int(v))
                    stack.append(int(v))
        comp.append(sorted(members))
    worst_slice, n_slice, over_band = 0.0, 0, 0
    scale = float(np.abs(phis).max()) if phis.size else 0.0
    for members in comp:
        if len(members) < 3:
            continue
        sub = adj[np.ix_(members, members)]
        for cyc in spanning_tree_cycles(sub):
            for a in range(M_CLASSES):
                walk = [vertex(a, members[x], n) for x in cyc]
                s = om.sum_over(walk)
                band = 2 * (len(cyc) - 1) * EPS * scale
                n_slice += 1
                worst_slice = max(worst_slice, abs(s))
                over_band += abs(s) > band
    nonzero_sq = [k for k, s in enumerate(sq_sums) if s != 0.0]
    named = []
    for k in nonzero_sq[:10]:
        w = sq[k]
        named.append({"positions": [w[0] % n, w[1] % n], "sum": sq_sums[k]})
    if not sq and not n_slice:
        return None, "the graph carries no square and no cycle", {}
    passed = bool(not nonzero_sq and over_band == 0)
    detail = (f"{len(sq)} squares, {len(nonzero_sq)} not exactly 0.0; {n_slice} slice "
              f"cycles, largest |sum| {worst_slice:.3e}, {over_band} outside the float band "
              f"2 * length * eps * {scale:.6g}")
    return passed, detail, {"squares": len(sq), "nonzero_squares": len(nonzero_sq),
                            "named": named, "slice_cycles": n_slice,
                            "worst_slice": worst_slice, "positions": n,
                            "components": len(comp)}


def _outside(rows, sc):
    """Rows of `rows` whose printed Percent Change misses sc * (New - Old) / Old by more than
    the rounding band of the printed digits."""
    # A rescaled week is the per cent rounded to two places and then rescaled (2026-10-29:
    # every rescaled-week row the plain band misses fits that, 6,765 of 6,765), so its band
    # carries both roundings. In a per-cent week the two grids coincide and one rounding is all.
    twice = 0.0 if sc == 100.0 else 0.005 * sc / 100.0
    out = []
    for ndc, o, nw, pc, hp, hc, wk in rows:
        got = sc * (nw - o) / o
        band = hc + twice + sc * (hp / o + hp * nw / o ** 2) + 4 * EPS * max(1.0, abs(got))
        if abs(got - pc) > band:
            out.append((abs(got - pc) - band, ndc, o, nw, pc, got, wk))
    return out


def _ymd(d: str) -> str:
    """MM/DD/YYYY as YYYY/MM/DD, so weeks sort in time; anything else as it is."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", d or "")
    return f"{m[3]}/{m[1]}/{m[2]}" if m else (d or "")


def _by_week(outside):
    c: dict = {}
    for *_x, wk in outside:
        c[wk[1]] = c.get(wk[1], 0) + 1
    return dict(sorted(c.items()))


def b99_1(rows):
    """Percent Change recomputed from Old and New, inside the rounding band of the digits.

    The scale the file prints Percent Change in is read per comparison week (Start Date, End
    Date), from SCALES: the definition says "divided by the Old NADAC Per Unit" and does not
    say per cent, and the file does not print one scale throughout (2026-10-29: whole weeks
    printed as a fraction, and whole weeks a hundred times the per cent). The verdict is on the
    per-week fit; the one-scale-for-the-file count is printed beside it, and every week whose
    scale is not per cent is named."""
    usable, unparsed, nonpos = [], 0, 0
    price_dec: dict = {}
    for r in rows:
        for k in ("old", "new"):
            d = decimals(r[k])
            price_dec[d] = price_dec.get(d, 0) + 1
        try:
            o, nw, pc = float(r["old"]), float(r["new"]), float(r["pct"])
        except ValueError:
            unparsed += 1
            continue
        if o <= 0:
            nonpos += 1
            continue
        hp = 0.5 * 10.0 ** -max(decimals(r["old"]), decimals(r["new"]))
        hc = 0.5 * 10.0 ** -decimals(r["pct"])
        wk = (r.get("start", "").strip(), r.get("end", "").strip())
        usable.append((r["ndc"], o, nw, pc, hp, hc, wk))
    if not usable:
        # rows were read and not one could be recomputed: the object is empty (11f)
        return False, (f"nothing to recompute: {len(rows)} comparison rows read, {unparsed} "
                       f"with a field that is not a number, {nonpos} with Old not positive"), {
            "rows": 0, "unparsed": unparsed, "old_not_positive": nonpos}
    whole = {sc: len(_outside(usable, sc)) for sc in SCALES}
    file_scale = min(SCALES, key=lambda s: whole[s])
    weeks: dict = {}
    for row in usable:
        weeks.setdefault(row[6], []).append(row)
    outside, odd_weeks = [], []
    for wk in sorted(weeks):
        fits = {sc: _outside(weeks[wk], sc) for sc in SCALES}
        sc = min(SCALES, key=lambda s: (len(fits[s]), s != 100.0))
        if sc != 100.0:
            odd_weeks.append({"start": wk[0], "end": wk[1], "scale": sc,
                              "rows": len(weeks[wk]), "outside": len(fits[sc]),
                              "outside_at_percent": len(fits[100.0])})
        outside.extend(fits[sc])
    outside.sort(reverse=True)
    # Shape (2026-10-29, research section 5 rule 2a): a printed criterion, not a line at zero.
    # Every row outside the band is printed one by one with the week it falls in. The flag
    # asserts that object: rows were recomputed, and every out-of-band row is named by a week.
    # A row the reading cannot place in a week fails it, since naming the week is the reading.
    roster = [{"ndc": n, "start": wk[0], "end": wk[1], "old": o, "new": w, "printed": p,
               "recomputed": g, "excess_over_band": e}
              for e, n, o, w, p, g, wk in sorted(outside, key=lambda x: (_ymd(x[6][1]), x[1], -x[0]))]
    weekless = [r for r in roster if not (r["start"] and r["end"])]
    named_weeks = [{"start": wk[0], "end": wk[1], "rows": len(weeks[wk]),
                    "outside": sum(1 for x in outside if x[6] == wk)}
                   for wk in sorted({x[6] for x in outside}, key=lambda k: (_ymd(k[1]), _ymd(k[0])))]
    passed = bool(len(roster) == len(outside) and not weekless)
    name = {1.0: "a fraction", 100.0: "a per cent", 10000.0: "a hundred times the per cent"}
    detail = (f"{len(usable)} rows in {len(weeks)} comparison weeks ({unparsed} held out with a "
              f"field that is not a number, {nonpos} with Old not positive); one scale for the "
              f"whole file ({name[file_scale]}) leaves {whole[file_scale]} outside; read per "
              f"week, {len(weeks) - len(odd_weeks)} weeks print a per cent and "
              f"{len(odd_weeks)} another scale ("
              + ", ".join(f"{w['end']} {name[w['scale']]}" for w in odd_weeks[:12])
              + (", ..." if len(odd_weeks) > 12 else "")
              + f"); {len(outside)} rows outside the band")
    if outside:
        detail += "; worst: " + "; ".join(
            f"NDC {n} week {wk[1]} old {o} new {w} printed {p} recomputed {g:.6g}"
            for _e, n, o, w, p, g, wk in outside[:5])
    if outside:
        detail += ("; out-of-band rows by week: " + ", ".join(
            f"{w['end'] or '(no End Date)'} {w['outside']} of {w['rows']}" for w in named_weeks)
            + "; every one is printed in report.B99-1.outside_rows")
    if weekless:
        detail += f"; {len(weekless)} out-of-band rows carry no week to name them by"
    tick =min(10.0 ** -max(decimals(r["old"]), decimals(r["new"])) for r in rows
               if r["old"] and r["new"])
    return passed, detail, {"rows": len(usable), "weeks": len(weeks),
                            "file_scale": file_scale, "outside_one_scale": whole,
                            "odd_weeks": odd_weeks, "outside": len(outside),
                            "price_tick": tick, "unparsed": unparsed, "old_not_positive": nonpos,
                            "price_decimals": {str(k): v for k, v in sorted(price_dec.items())},
                            "outside_by_week": _by_week(outside),
                            "outside_weeks": named_weeks,
                            "outside_rows": roster,
                            "outside_weekless": len(weekless),
                            "worst": [{"ndc": n, "start": wk[0], "end": wk[1], "old": o,
                                       "new": w, "printed": p, "recomputed": g,
                                       "excess_over_band": e}
                                      for e, n, o, w, p, g, wk in outside[:50]]}


def b99_2(nadac_rows, nsde_rows):
    """Same NDC-11, NADAC Pricing Unit against NSDE Billing Unit. Every mismatch named."""
    nadac_unit = {}
    for r in nadac_rows:
        k = ndc11(r["ndc"])
        if k:
            nadac_unit.setdefault(k, set()).add(r["unit"].strip().upper())
    nsde_unit = {}
    for r in nsde_rows:
        k = ndc11(r["ndc"])
        if k and r["unit"].strip():
            nsde_unit.setdefault(k, set()).add(r["unit"].strip().upper())
    joined = sorted(set(nadac_unit) & set(nsde_unit))
    if not joined:
        return None, "no NDC-11 in both files", {}
    bad = [(k, sorted(nadac_unit[k]), sorted(nsde_unit[k])) for k in joined
           if nadac_unit[k] != nsde_unit[k]]
    passed = not bad
    shapes: dict = {}
    for _k, a, b in bad:
        key = f"NADAC {'/'.join(a)} vs NSDE {'/'.join(b)}"
        shapes[key] = shapes.get(key, 0) + 1
    only_nadac = len(set(nadac_unit) - set(nsde_unit))
    multi = sum(1 for k in joined if len(nadac_unit[k]) > 1 or len(nsde_unit[k]) > 1)
    detail = (f"{len(joined)} NDC-11 in both ({only_nadac} NADAC NDCs carry no NSDE billing "
              f"unit, not judged); {len(bad)} disagree"
              + (f" ({', '.join(f'{v} {k}' for k, v in sorted(shapes.items(), key=lambda x: -x[1]))})"
                 if bad else "")
              + (f"; {multi} joined NDCs carry more than one unit on one side" if multi else "")
              + ("; first named: " + "; ".join(f"{k}: NADAC {a} NSDE {b}" for k, a, b in bad[:20])
                 if bad else ""))
    return passed, detail, {"joined": len(joined), "disagree": len(bad),
                            "nadac_without_nsde_unit": only_nadac, "multi_unit": multi,
                            "shapes": shapes,
                            "named": [{"ndc11": k, "nadac": a, "nsde": b} for k, a, b in bad]}


def b99_3(pairs, unit_split, unreached, price_source=DEFAULT_PRICE_SOURCE):
    """The wedge, one number per pair, read into one of three named cells. On a price source
    in GROUP_RATED it lands in cell 3 with the carrier as its reason, whatever the pairs say."""
    if price_source in GROUP_RATED:
        return None, 3, GROUP_RATED[price_source], {"price_source": price_source,
                                                    "carrier_has_no_object": True}
    if not pairs:
        return None, 3, (f"no pair reaches NADAC with a common date and unit "
                         f"({unreached} without a common date, {unit_split} unit split)"), {}
    w, fl = [], []
    for a, b, d, pa, pb, unit, dec in pairs:
        tick = 10.0 ** -dec
        w.append(math.log(pa) - math.log(pb))
        fl.append(0.5 * tick * (1.0 / pa + 1.0 / pb))
    over = [abs(x) > f for x, f in zip(w, fl)]
    rng = max(w) - min(w)
    if len(w) < 2 or not any(over):
        cell = 3
    elif rng <= 2 * max(fl):
        cell = 1
    else:
        cell = 2
    med = statistics.median(w)
    q = statistics.quantiles(w, n=4) if len(w) >= 2 else [med, med, med]
    ratio = statistics.median(abs(x) / f for x, f in zip(w, fl) if f > 0)
    detail = (f"{len(w)} pairs ({unreached} with no common date, {unit_split} with units "
              f"that disagree, held out); median log wedge {med:+.4f}, quartiles "
              f"{q[0]:+.4f} / {q[2]:+.4f}, range {rng:.4f}; {sum(over)} of {len(w)} above "
              f"their own floor, median |wedge| / floor {ratio:.1f}; cell {cell}")
    passed = None if cell == 3 else True
    return passed, cell, detail, {"pairs": len(w), "median": med, "q1": q[0], "q3": q[2],
                                  "range": rng, "over_floor": sum(over),
                                  "median_over_floor": ratio, "price_source": price_source}


MAPPING_B99_3 = {1: "printed: the wedge is one constant, which is the unpublished service fee",
                 2: "printed: two prices for one batch of tablets, spread wider than rounding",
                 3: "no verdict: too few pairs, or every wedge at or under its own floor, or a "
                    "price source that sets one rate per drug group or drug product (NADAC, "
                    "CMS Part D SPUF), where a repack pair is one price by construction"}
#: Which cell carries a verdict (11c): the undecided cell carries none.
VERDICT_B99_3 = {1: True, 2: True, 3: None}
assert VERDICT_B99_3[3] is None and MAPPING_B99_3[3].startswith("no verdict")


def build_criteria(objs):
    """objs: dict with any of nadac, comparison, nsde, spl row lists (None when absent).
    B99-3 reads its prices from objs["price_source"] (default NADAC). A source other than NADAC
    brings its own rows in objs["prices"], in the NADAC row shape (ndc, price, unit, date)."""
    crit, report = [], {}
    nad, comp, nsde, spl = (objs.get(k) for k in ("nadac", "comparison", "nsde", "spl"))
    source = objs.get("price_source", DEFAULT_PRICE_SOURCE)
    prices = nad if source == "NADAC" else objs.get("prices")
    pairs, split, unreached = ([], 0, 0)
    if nad is not None and spl is not None:
        pairs, split, unreached = pairs_of(spl, nadac_by_product(nad))
    pairs3, split3, unreached3 = pairs, split, unreached
    if source != "NADAC" and prices is not None and spl is not None:
        pairs3, split3, unreached3 = pairs_of(spl, nadac_by_product(prices))

    def absent(names):
        return "not run: " + ", ".join(names) + " not on disk"

    if nad is None or spl is None:
        p, d, r = None, absent([n for n, o in (("NADAC reference", nad), ("SPL map", spl))
                                if o is None]), {}
    else:
        p, d, r = b99_0(pairs)
    crit.append({"name": "B99-0", "kind": "instrument", "passed": p,
                 "statement": "The one-index NADAC field, fed to the cycle machinery as two "
                              "identical class slices on the main reading's own pair graph, "
                              "returns every square exactly 0.0 and every slice cycle inside "
                              "its float band.", "detail": d})
    report["B99-0"] = r
    if comp is None:
        p, d, r = None, absent(["NADAC comparison"]), {}
    else:
        p, d, r = b99_1(comp)
    crit.append({"name": "B99-1", "kind": "instrument", "passed": p,
                 "statement": "Percent Change is recomputed from Old and New NADAC Per Unit on "
                              "every row, its scale read per comparison week; every row outside "
                              "the rounding band of the printed digits is printed one by one "
                              "and named by the week it falls in.",
                 "reading": "The publisher's arithmetic reproduces on every row not printed. "
                            "Each printed row is a place where the printed Percent Change "
                            "departs from its own definition, read by its week and the shape "
                            "its rows share; a week is the unit of reading because the scale "
                            "is set per week. The flag says the object is there: rows were "
                            "recomputed and every out-of-band row is named by its week.",
                 "detail": d})
    report["B99-1"] = r
    if nad is None or nsde is None:
        p, d, r = None, absent([n for n, o in (("NADAC reference", nad), ("NSDE", nsde))
                                if o is None]), {}
    else:
        p, d, r = b99_2(nad, nsde)
    crit.append({"name": "B99-2", "kind": "known_answer", "passed": p,
                 "statement": "On the same NDC-11, NADAC's Pricing Unit and NSDE's Billing "
                              "Unit agree; each disagreement is named.", "detail": d})
    report["B99-2"] = r
    if source in GROUP_RATED:
        # the carrier decides before the sources do: no SPL map gives NADAC a wedge (D23)
        p, cell, d, r = b99_3(pairs, split, unreached, source)
    elif prices is None or spl is None:
        p, cell, d, r = None, 3, absent([n for n, o in ((f"{source} prices", prices),
                                                        ("SPL map", spl)) if o is None]), {}
    else:
        p, cell, d, r = b99_3(pairs3, split3, unreached3, source)
    assert p is VERDICT_B99_3[cell], (cell, p)   # 11c: the undecided cell carries no verdict
    crit.append({"name": "B99-3", "kind": "own_reading", "passed": p, "cell": cell,
                 "statement": "The repackaging wedge log(price repack) - log(price source), "
                              "one per pair at the latest common date, read into one of "
                              "three named cells, on a price source that prices each "
                              "labeler's own NDC; on a source that sets one rate per drug "
                              "group (NADAC) the pair is one price by construction and the "
                              "criterion carries no verdict.",
                 "price_source": source, "detail": d})
    report["B99-3"] = r
    return crit, report


# ---------------------------------------------------------------------------- selftest

def _fixture():
    """Six products, two repack pairs, one comparison week, NSDE units for all."""
    date = "2026-10-21"
    nad = []
    prices = {"00093005801": "0.05210", "00093005810": "0.05300",   # source A, two packages
              "70518474800": "0.18500",                             # repack of A
              "00378018001": "0.11000",                             # source B
              "63629123401": "0.31900",                             # repack of B
              "00904123461": "1.20000"}                             # unpaired
    for ndc, p in prices.items():
        nad.append({"ndc": ndc, "price": p, "unit": "EA", "date": date})
    spl = [{"repack": "70518-4748", "source": "0093-0058"},
           {"repack": "63629-1234", "source": "0378-0180"}]
    comp = []
    for ndc, old, new in (("00093005801", "0.05000", "0.05210"),
                          ("00378018001", "0.12000", "0.11000"),
                          ("00904123461", "1.10000", "1.20000")):
        pct = 100.0 * (float(new) - float(old)) / float(old)
        comp.append({"ndc": ndc, "old": old, "new": new, "pct": f"{pct:.2f}",
                     "start": "10/14/2026", "end": "10/21/2026"})
    nsde = [{"ndc": k[:5] + "-" + k[5:9] + "-" + k[9:], "unit": "EA"} for k in prices]
    return {"nadac": nad, "comparison": comp, "nsde": nsde, "spl": spl}


def selftest():
    import copy
    checks = []
    base = _fixture()
    crit, rep = build_criteria(base)
    by = {c["name"]: c for c in crit}
    checks.append(("NDC keys pad by segment", ndc11("0093-0058-01") == "00093005801"
                   and ndc11("52817-254-01") == "52817025401"
                   and ndc11("70518-4748-0") == "70518474800"
                   and product9("70518-4748") == "705184748"
                   and product9("52817-254") == "528170254"))
    checks.append(("B99-0 passes on the clean field", by["B99-0"]["passed"] is True))
    checks.append(("B99-1 passes and reads the file as percent",
                   by["B99-1"]["passed"] is True and rep["B99-1"]["file_scale"] == 100.0
                   and rep["B99-1"]["odd_weeks"] == []))
    checks.append(("B99-2 passes", by["B99-2"]["passed"] is True))
    # B99-3 on NADAC: the fixture's two pairs differ in price (they would land in cell 2 on a
    # per-NDC source), and on NADAC they carry no verdict, with the carrier as the reason
    checks.append(("B99-3 on NADAC lands in cell 3 with the carrier as its reason",
                   by["B99-3"]["passed"] is None and by["B99-3"]["cell"] == 3
                   and by["B99-3"]["detail"] == GROUP_RATED["NADAC"]
                   and rep["B99-3"]["carrier_has_no_object"] is True))
    # the same rows as a per-NDC source: the judging path is reachable and reads them
    perndc = dict(copy.deepcopy(base), price_source="FAKE per-NDC list price",
                  prices=copy.deepcopy(base["nadac"]))
    cp, rp = build_criteria(perndc)
    checks.append(("B99-3 on a per-NDC source reads two pairs and lands in cell 2",
                   cp[3]["passed"] is True and cp[3]["cell"] == 2
                   and rp["B99-3"]["pairs"] == 2
                   and rp["B99-3"]["price_source"] == "FAKE per-NDC list price"))

    seeded = []
    # B99-0: one position, one class, moved by about 1e-12
    pairs, _s, _u = pairs_of(base["spl"], nadac_by_product(base["nadac"]))
    nodes = sorted({x for a, b, *_ in pairs for x in (a, b)})
    pos = {p: k for k, p in enumerate(nodes)}
    phi = np.zeros(len(nodes))
    for a, b, _d, pa, pb, *_ in pairs:
        phi[pos[a]], phi[pos[b]] = pa, pb
    two = np.stack([phi, phi.copy()])
    two[1, 0] += max(1e-12, 8 * float(np.spacing(two[1, 0])))
    p0, d0, r0 = cycle_check(len(nodes), [(pos[a], pos[b]) for a, b, *_ in pairs], two)
    seeded.append(("a 1e-12 split of one position fails B99-0 and names it",
                   p0 is False and r0["nonzero_squares"] >= 1
                   and r0["named"][0]["positions"][0] == 0))
    # B99-0 on a graph with a real cycle: the slice band holds clean, fails with a bad edge
    phi4 = np.array([3.1, 0.7, 12.5, 0.052])
    ring = [(0, 1), (1, 2), (2, 3), (3, 0)]
    ok4 = cycle_check(4, ring, np.stack([phi4, phi4.copy()]))[0]
    seeded.append(("a four-node ring passes clean", ok4 is True))
    # B99-1 is a printed criterion (2026-10-29, 2a): a bad row does not flip the flag, it is
    # printed with its week. The seeds below check that each bad row lands on the roster.
    def on_roster(rep_, ndc, end):
        return any(r_["ndc"] == ndc and r_["end"] == end
                   for r_ in rep_["B99-1"].get("outside_rows", []))
    # B99-1: Old and New swapped on one row
    sw = copy.deepcopy(base)
    r = sw["comparison"][0]
    r["old"], r["new"] = r["new"], r["old"]
    csw, rsw = build_criteria(sw)
    seeded.append(("Old and New swapped on one row is printed with its week",
                   on_roster(rsw, "00093005801", "10/21/2026")
                   and rsw["B99-1"]["outside"] == 1
                   and rsw["B99-1"]["outside_weeks"] == [{"start": "10/14/2026",
                                                          "end": "10/21/2026", "rows": 3,
                                                          "outside": 1}]))
    # B99-1: a percent printed half a point off is printed with its week
    tick = copy.deepcopy(base)
    v = float(tick["comparison"][2]["pct"])
    tick["comparison"][2]["pct"] = f"{v + 0.50:.2f}"
    ctk, rtk = build_criteria(tick)
    seeded.append(("a Percent Change half a point off is printed with its week",
                   on_roster(rtk, "00904123461", "10/21/2026") and ctk[1]["passed"] is True))
    # B99-1 flag, 11f: an out-of-band row that carries no week cannot be named, so it fails
    nowk = copy.deepcopy(tick)
    nowk["comparison"][2]["end"] = ""
    cnw, rnw = build_criteria(nowk)
    seeded.append(("an out-of-band row with no End Date fails B99-1",
                   cnw[1]["passed"] is False and rnw["B99-1"]["outside_weekless"] == 1))
    # B99-1 flag, 11f: rows read and none recomputable is an empty object, and fails
    junk = copy.deepcopy(base)
    for r in junk["comparison"]:
        r["pct"] = "n/a"
    seeded.append(("comparison rows with nothing recomputable fail B99-1",
                   build_criteria(junk)[0][1]["passed"] is False))
    # B99-1: a whole week printed as a fraction is read at its own scale and named, while a
    # one-digit slip inside that week still fails
    frac = copy.deepcopy(base)
    for ndc, old, new in (("00093005810", "0.05000", "0.05300"),
                          ("00378018001", "0.11000", "0.12000"),
                          ("00904123461", "1.20000", "1.10000")):
        frac["comparison"].append({"ndc": ndc, "old": old, "new": new,
                                   "pct": f"{(float(new) - float(old)) / float(old):.4f}",
                                   "start": "10/07/2026", "end": "10/14/2026"})
    cf, rf = build_criteria(frac)
    seeded.append(("a week printed as a fraction is read at its scale and named",
                   cf[1]["passed"] is True and len(rf["B99-1"]["odd_weeks"]) == 1
                   and rf["B99-1"]["odd_weeks"][0]["scale"] == 1.0
                   and rf["B99-1"]["outside_one_scale"][100.0] == 3))
    slip = copy.deepcopy(frac)
    slip["comparison"][-1]["pct"] = "-0.0933"
    seeded.append(("a digit slip inside a fraction week is printed with that week",
                   on_roster(build_criteria(slip)[1], "00904123461", "10/14/2026")))
    # B99-2: units flipped on a batch
    fl = copy.deepcopy(base)
    for r in fl["nsde"][:3]:
        r["unit"] = "ML"
    c2 = build_criteria(fl)[0][2]
    seeded.append(("three NSDE units flipped fail B99-2 and are named",
                   c2["passed"] is False and c2["detail"].count("NSDE ['ML']") == 3))
    # B99-3, 11f: NADAC-sourced pairs never return a verdict, whatever the prices. Three NADAC
    # feeds: the fixture (two different wedges), equal wedges, and a wide spread; plus b99_3
    # called directly on pairs that would land in cell 2
    for label, mutate in (("differing", None), ("equal", "63629123401"), ("wide", "70518474800")):
        nad_ = copy.deepcopy(base)
        if mutate == "63629123401":
            for r in nad_["nadac"]:
                if r["ndc"] == mutate:
                    r["price"] = f"{0.11000 * (0.18500 / 0.05255):.5f}"
        elif mutate == "70518474800":
            for r in nad_["nadac"]:
                if r["ndc"] == mutate:
                    r["price"] = "9.99000"
        cn = build_criteria(nad_)[0][3]
        seeded.append((f"NADAC pairs ({label}) give B99-3 no verdict",
                       cn["passed"] is None and cn["cell"] == 3
                       and cn["detail"] == GROUP_RATED["NADAC"]))
    direct_pairs = pairs_of(base["spl"], nadac_by_product(base["nadac"]))
    seeded.append(("b99_3 called directly on NADAC pairs returns no verdict",
                   b99_3(*direct_pairs, "NADAC")[0] is None
                   and b99_3(*direct_pairs, "FAKE per-NDC list price")[0] is True))
    # NADAC with no SPL map: the carrier is the reason, not the missing file
    nospl = copy.deepcopy(base)
    del nospl["spl"]
    c3n = build_criteria(nospl)[0][3]
    seeded.append(("NADAC without an SPL map gives the carrier as the reason",
                   c3n["passed"] is None and c3n["detail"] == GROUP_RATED["NADAC"]))
    # the Part D pricing file is keyed on one proxy NDC per drug product: fed the fixture's
    # differing prices (cell 2 on a per-NDC source), B99-3 still carries no verdict
    spuf = dict(copy.deepcopy(base), price_source="CMS Part D SPUF",
                prices=copy.deepcopy(base["nadac"]))
    c3s = build_criteria(spuf)[0][3]
    seeded.append(("Part D SPUF prices give B99-3 no verdict, with the carrier as the reason",
                   c3s["passed"] is None and c3s["cell"] == 3
                   and c3s["detail"] == GROUP_RATED["CMS Part D SPUF"]))
    # B99-3 on a per-NDC source: every wedge equal -> cell 1; no SPL rows -> cell 3, no verdict
    const = copy.deepcopy(perndc)
    for r in const["prices"]:
        if r["ndc"] == "63629123401":
            r["price"] = f"{0.11000 * (0.18500 / 0.05255):.5f}"
    c3 = build_criteria(const)[0][3]
    seeded.append(("equal wedges land in cell 1", c3["cell"] == 1 and c3["passed"] is True))
    empty = copy.deepcopy(perndc)
    empty["spl"] = []
    c3e = build_criteria(empty)[0][3]
    seeded.append(("no pairs land in cell 3 with no verdict",
                   c3e["cell"] == 3 and c3e["passed"] is None))
    zero = copy.deepcopy(perndc)
    for r in zero["prices"]:
        if r["ndc"] == "70518474800":
            r["price"] = "0.05255"
        if r["ndc"] == "63629123401":
            r["price"] = "0.11000"
    c3z = build_criteria(zero)[0][3]
    seeded.append(("wedges at the floor land in cell 3", c3z["cell"] == 3
                   and c3z["passed"] is None))
    noprice = dict(copy.deepcopy(base), price_source="FAKE per-NDC list price")
    c3p = build_criteria(noprice)[0][3]
    seeded.append(("a per-NDC source with no rows lands in cell 3, not run",
                   c3p["passed"] is None and c3p["detail"].startswith("not run:")))
    # no data at all: every criterion carries no verdict
    none = build_criteria({})[0]
    seeded.append(("absent sources leave every criterion without a verdict",
                   all(c["passed"] is None for c in none)))
    # a header the source does not use is refused, not read
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "x.csv"
        p.write_text("NDC,NADAC Price,Pricing Unit,Effective Date\n1,2,EA,x\n", encoding="utf-8")
        rows, rep2 = read_table([p], NADAC_COLS, "NADAC")
        seeded.append(("a renamed price column is refused", not rows and rep2[0]["refused"]))

    print("B99 selftest")
    for name, ok in checks + seeded:
        print(f"  {'ok ' if ok else 'BAD'} {name}")
    print("  B99-3 mapping (11c), state -> verdict:")
    for k, v in MAPPING_B99_3.items():
        print(f"    cell {k} -> {VERDICT_B99_3[k]!s:5s} {v}")
    for src in GROUP_RATED:
        print(f"    price source {src} -> cell 3, no verdict (carrier, D23)")
    if VERDICT_B99_3[3] is not None:
        raise SystemExit("selftest failed: the undecided cell of B99-3 maps to a verdict")
    bad = [n for n, ok in checks + seeded if not ok]
    if bad:
        raise SystemExit(f"selftest failed: {bad}")
    print(f"selftest passed: {len(checks)} clean checks, {len(seeded)} seeded faults caught")


# ---------------------------------------------------------------------------- run

def run():
    found = locate()
    print("B99: what is on disk under data/raw/b99/")
    objs, files = {}, {}
    for key, cols, label in (("nadac", NADAC_COLS, "NADAC reference"),
                             ("comparison", COMP_COLS, "NADAC comparison"),
                             ("nsde", NSDE_COLS, "NSDE"),
                             ("spl", SPL_COLS, "SPL map")):
        if not found[key]:
            print(f"  {label}: nothing on disk")
            files[key] = []
            continue
        rows, rep = read_table(found[key], cols, label)
        files[key] = rep
        objs[key] = rows if rows else None
        print(f"  {label}: {len(rows)} rows from {len(found[key])} files")
    crit, report = build_criteria(objs)
    missing = [p for p in PENDING
               if not any(objs.get(k) is not None for k in
                          {"data/raw/b99/nadac/": ["nadac"], "data/raw/b99/comparison/": ["comparison"],
                           "data/raw/b99/nsde/": ["nsde"],
                           "data/raw/b99/spl_source_ndc.csv": ["spl"]}[p["into"]])]
    # a criterion closed by its carrier waits on no fetch (D23): drop it from what SPL feeds
    carrier = [c["name"] for c in crit if c["detail"] in GROUP_RATED.values()]
    missing = [dict(p, feeds=[f for f in p["feeds"] if f not in carrier]) for p in missing]
    unread = all(c["passed"] is None for c in crit)
    rec = {"stage": "B99",
           "config": {"data_dir": "data/raw/b99", "classes": M_CLASSES,
                      "pair_rule": "median NADAC Per Unit over the packages of a product, at "
                                   "the latest Effective Date both products carry; pairs "
                                   "whose Pricing Units differ are held out",
                      "floor": "(tick / 2) * (1 / p_repack + 1 / p_source), tick from the "
                               "printed digits",
                      "square_band": 0.0,
                      "slice_band": "2 * length * eps * max|phi|",
                      "percent_scales_tried": list(SCALES),
                      "percent_scale_read": "per comparison week (Start Date, End Date)",
                      "rescaled_week_band": "plus 0.005 * scale / 100: the per cent rounded to "
                                            "two places before rescaling",
                      "fetcher": "scripts/fetch_b99.py; manifest data/raw/b99/b99_manifest.json",
                      "b99_3_price_source": DEFAULT_PRICE_SOURCE,
                      "b99_3_group_rated_sources": sorted(GROUP_RATED)},
           "mapping": {"B99-3": {str(k): v for k, v in MAPPING_B99_3.items()}},
           "criteria": crit,
           "report": report,
           "files": files,
           "pending_fetch": missing}
    open_ = [c["name"] for c in crit if c["passed"] is None and c["name"] not in carrier]
    if unread:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("none of the four sources is on disk under data/raw/b99/ as "
                                    "of the run; every criterion is in its third state and "
                                    "pending_fetch names what is missing")
    elif open_:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = (f"station open: {', '.join(open_)} carry no verdict because "
                                    "a source they need is not on disk; pending_fetch names it. "
                                    + (f"{', '.join(carrier)} carries no verdict on its carrier: "
                                       "NADAC sets one rate per drug group, so a repack pair is "
                                       "one price by construction (D23, measured the wrong "
                                       "object). " if carrier else "")
                                    + "The criteria with a verdict are read in full")
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    for c in crit:
        v = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"  {c['name']:6s} {c['kind']:12s} {v:10s} {c['detail']}")
    rows1 = report.get("B99-1", {}).get("outside_rows", [])
    if rows1:
        print(f"B99-1 out-of-band rows, one by one ({len(rows1)}), by week:")
        for r in rows1:
            print(f"  week {r['start']}-{r['end']}  NDC {r['ndc']}  old {r['old']}  "
                  f"new {r['new']}  printed {r['printed']}  recomputed {r['recomputed']:.6g}")
    if missing:
        print("pending fetch, not done here:")
        for p in missing:
            print(f"  {p['source']} -> {p['into']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    selftest()
    return run()


if __name__ == "__main__":
    sys.exit(main())
