"""B129: the Berlin rent cap law, class values on one position, and the scalar index.

Every number here is read off a file in data/b129/raw (fetched by b129_fetch.py) or
transcribed from one, with the page named. No estimation is done in this script: the one
estimated quantity (B129-3) is a published difference-in-differences, transcribed.

Criteria, each with a `kind` (11d):
  B129-1 instrument    the §6 table as transcribed matches the enacted text, row by row
  B129-2 own_reading   number of distinct class values the statute writes, three layers
  B129-3 rival         the square (regulated/exempt x before/after) against the scalar field
  B129-4 own_reading   the month the scalar index moves after each legal date
  B129-5 own_reading   which of the index's two age classes falls more at the reduction step,
                       predicted from the cap table and the 2019 Mietspiegel before it is read
  B129-6 own_reading   the third class written by two statutes' different exemption dates

Every criterion's flag is computed from its object, and --selftest feeds each one an input
that must make it fail (11f).

Run from the repo root:
    python experiments/b129_readings.py
    python experiments/b129_readings.py --selftest
"""
from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b129" / "raw"
OUT = ROOT / "results" / "b129_readings.json"

# ---------------------------------------------------------------------------------------
# Transcriptions. Each block names its page.

#: MietenWoG Bln §6 Abs. 1. GVBl. Berlin 2020 Nr. 6, S. 50-51; identical in Drucksache
#: 18/2347 §6 (unamended by 18/2437, which touches §6 only in Abs. 4 and 5) and in
#: Hahn et al. (2023) Table 1. (row, band, equipment, EUR per m2)
CAP_TABLE = [
    (1, "bis 1918", "und", 6.45), (2, "bis 1918", "oder", 5.00), (3, "bis 1918", "ohne", 3.92),
    (4, "1919 bis 1949", "und", 6.27), (5, "1919 bis 1949", "oder", 5.22),
    (6, "1919 bis 1949", "ohne", 4.59),
    (7, "1950 bis 1964", "und", 6.08), (8, "1950 bis 1964", "oder", 5.62),
    (9, "1965 bis 1972", "und", 5.95), (10, "1973 bis 1990", "und", 6.04),
    (11, "1991 bis 2002", "und", 8.13), (12, "2003 bis 2013", "und", 9.80),
]
#: Drucksache 18/2347, Begruendung to §6 (p. 34 of the PDF): each cap is the 2013
#: Mietspiegel median (Mittelwert) of its row times the real wage index carried forward,
#: 104.9/94.2 = 1.114 for 2012-2018 and one more year at the geometric mean 1.018,
#: 1.114 * 1.018 = 1.134. (row -> 2013 median, EUR per m2)
MS2013_MEDIAN = {1: 5.69, 2: 4.41, 3: 3.46, 4: 5.53, 5: 4.60, 6: 4.05, 7: 5.36, 8: 4.96,
                 9: 5.25, 10: 5.33, 11: 7.17, 12: 8.64}
REAL_WAGE_FACTOR = 1.134
LABEL = {"und": "mit Sammelheizung und mit Bad", "oder": "mit Sammelheizung oder mit Bad",
         "ohne": "ohne Sammelheizung und ohne Bad"}
#: §6 Abs. 2: +10 % in buildings with at most two dwellings. §6 Abs. 3: +1 EUR, modern.
SMALL_BUILDING = 1.10
MODERN = 1.00
#: §5 Abs. 1: location adjustment (einfach, mittel, gut) and the 20 % overage line.
LOCATION = {"einfach": -0.28, "mittel": -0.09, "gut": +0.74}
OVERAGE = 1.20

#: Legal dates. Art. 4(1); WohnlageZVO of 23.11.2020; BVerfG 2 BvF 1/20, press release
#: Nr. 28/2021. Month keys are the first index month on or after the date.
DATES = {"in force": ("2020-02-23", "2020-03"),
         "reduction (§5)": ("2020-11-23", "2020-12"),
         "void (BVerfG published)": ("2021-04-15", "2021-05")}

#: Exemption lines. MietenWoG Bln §1 Nr. 3 as amended by 18/2437: first ready from
#: 1.1.2014. BGB §556f: first used and let after 1.10.2014.
DECKEL_EXEMPT_FROM = "2014-01-01"
BREMSE_EXEMPT_AFTER = "2014-10-01"

#: Hahn, Kholodilin, Waltl & Fongoni (2023), Management Science, Table 5 (p. 13 of the
#: open copy): Treatment x month, log asking rent, base January 2018. (estimate, s.e.)
#: The PDF's minus signs extract as U+FFFD; signs restored from the printed table.
HAHN_T5 = {
    "2018-02": (0.003, 0.015), "2018-03": (0.002, 0.014), "2018-04": (0.018, 0.015),
    "2018-05": (0.011, 0.015), "2018-06": (0.025, 0.015), "2018-07": (-0.009, 0.015),
    "2018-08": (0.004, 0.015), "2018-09": (0.008, 0.015), "2018-10": (0.001, 0.014),
    "2018-11": (-0.015, 0.014), "2018-12": (0.040, 0.015), "2019-01": (0.002, 0.014),
    "2019-02": (-0.015, 0.014), "2019-03": (0.001, 0.014), "2019-04": (-0.024, 0.014),
    "2019-05": (-0.040, 0.014), "2019-06": (-0.040, 0.014), "2019-07": (-0.042, 0.014),
    "2019-08": (-0.041, 0.015), "2019-09": (-0.037, 0.015), "2019-10": (-0.073, 0.015),
    "2019-11": (-0.056, 0.015), "2019-12": (-0.057, 0.016), "2020-01": (-0.076, 0.015),
    "2020-02": (-0.081, 0.016), "2020-03": (-0.170, 0.018), "2020-04": (-0.144, 0.019),
    "2020-05": (-0.090, 0.019), "2020-06": (-0.131, 0.018),
}
#: Table 6 (p. 14): Treatment x Post-E, Strategy A, N = 26,842.
HAHN_T6 = (-0.113, 0.019)
#: Announcement of the Eckpunkte, the date Hahn et al. use (4 June 2019).
ANNOUNCEMENT_MONTH = "2019-06"

#: Berliner Mietspiegeltabelle 2019 (Stichtag 01.09.2018), medians, full equipment
#: (Sammelheizung, Bad, IWC). Rows A-L: size class x location; columns 1-8: age bands.
#: Assigned to row and column by position on the page (read_mietspiegel), not by order.
MS_COLUMNS = {1: "bis 1918", 2: "1919-1949", 3: "1950-1964", 4: "1965-1972",
              5: "1973-1990 West", 6: "1973-1990 Ost", 7: "1991-2002", 8: "2003-2017"}
MS_LOCATION = {r: loc for rows, loc in (("ADGJ", "einfach"), ("BEHK", "mittel"),
                                        ("CFIL", "gut")) for r in rows}
#: Mietspiegel column -> the cap row (full equipment) that governs it.
MS_TO_CAP = {1: 1, 2: 4, 3: 7, 4: 9, 5: 10, 6: 10, 7: 11, 8: 12}
#: The index's own split: "gebaut bis 1948" and "ab 1949 und Einfamilienhaus".
INDEX_CLASS = {1: "bis 1948", 2: "bis 1948", 3: "ab 1949", 4: "ab 1949", 5: "ab 1949",
               6: "ab 1949", 7: "ab 1949", 8: "ab 1949"}

MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
             "September", "Oktober", "November", "Dezember"]


# ---------------------------------------------------------------------------------------
# Readers.

def pdf_text(name: str) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(RAW / name).pages)


def normalise(t: str) -> str:
    t = re.sub(r"-\s*\n\s*", "", t)          # hyphenated line breaks
    return re.sub(r"\s+", " ", t)


def read_index() -> dict[str, dict[str, float]]:
    """Monthly Nettokaltmieten index, both age classes, from both workbooks.

    Months present in both workbooks must agree cell for cell, or this raises.
    """
    import openpyxl
    series: dict[str, dict[str, float]] = {}
    for f in ("vpi_berlin_2020m12.xlsx", "vpi_berlin_2022m09.xlsx"):
        ws = openpyxl.load_workbook(RAW / f, data_only=True)["4"]
        year = None
        for row in ws.iter_rows(values_only=True):
            if isinstance(row[2], str) and row[2].startswith("Veränderung"):
                break
            if isinstance(row[0], int):
                year = row[0]
            if year is None or row[1] not in MONTHS_DE:
                continue
            key = f"{year}-{MONTHS_DE.index(row[1]) + 1:02d}"
            vals = {"zusammen": float(row[3]), "bis 1948": float(row[4]),
                    "ab 1949": float(row[5])}
            if key in series and series[key] != vals:
                raise ValueError(f"{key}: the two workbooks disagree: {series[key]} vs {vals}")
            series[key] = vals
    return dict(sorted(series.items()))


def read_mietspiegel() -> dict[str, dict[int, tuple[float, float, float]]]:
    """(median, low, high) by row and column, assigned by position on the page.

    Each cell prints its median on one line and its 3/4 range (the middle 75 %) on the
    line below, so `high` is about the 87.5th percentile of the cell's rents.
    """
    from pypdf import PdfReader
    pts: list[tuple[int, int, str]] = []

    def visit(text, cm, tm, _fd, _fs):
        t = text.strip()
        if re.fullmatch(r"\d{1,2},\d{2}", t):
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            pts.append((round(y), round(x), t))

    PdfReader(RAW / "mietspiegeltabelle2019.pdf").pages[0].extract_text(visitor_text=visit)
    edges = [800, 1000, 1300, 1600, 1900, 2200, 2450, 2700, 3000]
    ys = sorted({p[0] for p in pts}, reverse=True)
    if len(ys) != 24:
        raise ValueError(f"expected 12 rows x 2 lines, got {len(ys)} y-levels")
    col = lambda x: next(i for i in range(8) if edges[i] <= x < edges[i + 1]) + 1  # noqa: E731
    num = lambda s: float(s.replace(",", "."))  # noqa: E731
    grid: dict[str, dict[int, tuple[float, float, float]]] = {}
    for ry, rr, lab in zip(ys[0::2], ys[1::2], "ABCDEFGHIJKL", strict=True):
        med: dict[int, list[tuple[int, str]]] = {}
        rng: dict[int, list[tuple[int, str]]] = {}
        for y, x, t in pts:
            if y == ry:
                med.setdefault(col(x), []).append((x, t))
            elif y == rr:
                rng.setdefault(col(x), []).append((x, t))
        if set(med) != set(rng):
            raise ValueError(f"row {lab}: median and range columns differ {set(med)} {set(rng)}")
        grid[lab] = {}
        for c in sorted(med):
            lo_hi = sorted(rng[c])
            if len(lo_hi) != 2:
                raise ValueError(f"row {lab} col {c}: range has {len(lo_hi)} numbers")
            grid[lab][c] = (num(min(med[c])[1]), num(lo_hi[0][1]), num(lo_hi[1][1]))
    return grid


# ---------------------------------------------------------------------------------------
# Criteria. Each takes its object and returns (passed, detail, object-for-the-record).

def b129_1(table, enacted_text: str) -> tuple[bool | None, str, dict]:
    """Every transcribed row appears in the enacted text with its value, in order."""
    t = normalise(enacted_text)
    found, pos = [], 0
    for n, band, eq, v in table:
        pat = rf"{n}\.\s*{re.escape(band)}\s*{re.escape(LABEL[eq])}\s*" + \
              re.escape(f"{v:.2f}".replace(".", ",")) + r"\s*Euro"
        m = re.compile(pat).search(t, pos)
        found.append(m is not None)
        if m:
            pos = m.end()
    ok = all(found) and len(table) == 12
    miss = [table[i][0] for i, f in enumerate(found) if not f]
    return ok, (f"{sum(found)}/{len(table)} rows found in the enacted text in order"
                + (f"; missing rows {miss}" if miss else "")), {"rows_found": sum(found)}


def b129_1b(table, medians, factor) -> tuple[bool | None, str, dict]:
    """Each cap equals its 2013 median times the real wage factor, to the cent."""
    rows = {n: (medians.get(n), v, round(medians[n] * factor, 2) if n in medians else None)
            for n, _, _, v in table}
    off = [n for n, (_, cap, derived) in rows.items() if derived is None or abs(derived - cap) > 0.005]
    ok = bool(rows) and not off
    return ok, (f"{len(rows) - len(off)}/{len(rows)} caps equal 2013 median x {factor} to the cent"
                + (f"; off: rows {off}" if off else "")), {
        "rows": {str(n): {"median_2013": m, "cap": c, "median_x_factor": d}
                 for n, (m, c, d) in rows.items()}}


def class_values(table) -> dict[str, int]:
    base = sorted({v for *_, v in table})
    with_rules = sorted({round(v * s + m, 2) for v in base
                         for s in (1.0, SMALL_BUILDING) for m in (0.0, MODERN)})
    with_location = sorted({round(v + d, 2) for v in with_rules for d in LOCATION.values()})
    return {"base": len(base), "with §6(2)(3)": len(with_rules),
            "with §5 location": len(with_location),
            "combinations": len(base) * 4 * len(LOCATION),
            "range_min": min(with_location) if with_location else None,
            "range_max": max(with_location) if with_location else None}


def b129_2(table) -> tuple[bool | None, str, dict]:
    """Printing criterion: the object exists and each layer does not lose values."""
    c = class_values(table)
    ok = c["base"] >= 1 and c["base"] <= c["with §6(2)(3)"] <= c["with §5 location"]
    return ok, (f"base {c['base']}, with the two §6 surcharges {c['with §6(2)(3)']}, "
                f"with §5 location {c['with §5 location']} of {c['combinations']} "
                f"combinations, {c['range_min']:.2f} to {c['range_max']:.2f} EUR/m2"
                if c["base"] else "empty table"), c


def b129_3(t5, t6, announce) -> tuple[bool | None, str, dict]:
    """Rival: the square is zero. PASS means the rival is wrong.

    Floor (D24), measured: the largest absolute pre-announcement monthly coefficient.
    Nothing is chosen: the rival reading has to stand above what the same regression
    printed when no law existed.
    """
    pre = {k: v for k, v in t5.items() if k < announce}
    if not pre:
        return None, "no pre-announcement months, no floor", {}
    floor = max(abs(e) for e, _ in pre.values())
    sd_pre = statistics.pstdev(e for e, _ in pre.values())
    est, se = t6
    peak_k, (peak, peak_se) = min(t5.items(), key=lambda kv: kv[1][0])
    ok = abs(est) > floor
    return ok, (f"Treatment x Post-E {est:+.3f} (se {se:.3f}), {abs(est) / se:.1f} se; "
                f"floor = max |pre-announcement coefficient| over {len(pre)} months "
                f"= {floor:.3f}, reading is {abs(est) / floor:.2f} x floor; "
                f"sd of pre months {sd_pre:.4f}; largest month {peak_k} {peak:+.3f} "
                f"({abs(peak) / floor:.2f} x floor)"), {
        "estimate": est, "se": se, "floor": floor, "pre_months": len(pre),
        "sd_pre": round(sd_pre, 4), "peak_month": peak_k, "peak": peak}


def monthly_changes(series, cls):
    ks = list(series)
    return {ks[i]: round(series[ks[i]][cls] - series[ks[i - 1]][cls], 1)
            for i in range(1, len(ks))}


#: Periods for the slope reading. The freeze (§3, stichtag 18.06.2019) forbids any rise:
#: its signature is a slope going to zero, not a step (D53), so it is read as the mean
#: monthly change per period.
PERIODS = {"before announcement": ("2017-02", "2019-05"),
           "announcement to force": ("2019-06", "2020-02"),
           "freeze in force": ("2020-03", "2020-11")}


def lag(m0: str, m1: str) -> int:
    y0, a = map(int, m0.split("-"))
    y1, b = map(int, m1.split("-"))
    return (y1 - y0) * 12 + (b - a)


def b129_4(series, dates, pre_end="2019-06") -> tuple[bool | None, str, dict]:
    """Steps: first month after a legal date whose change exceeds every monthly change the
    class showed before the announcement (floor, measured). A step after the reduction date
    is credited to it only if it comes before the next legal date; a step after the void
    date is credited to it only if it reverses that class's reduction step, which is what
    voiding predicts. Slopes: mean monthly change in each period of PERIODS."""
    out = {}
    names = list(dates)
    for cls in ("bis 1948", "ab 1949"):
        ch = monthly_changes(series, cls)
        pre = [abs(v) for k, v in ch.items() if k < pre_end]
        if not pre:
            return None, "no pre-period", {}
        floor = max(pre)
        per: dict[str, dict] = {}
        for i, name in enumerate(names):
            m0 = dates[name][1]
            end = dates[names[i + 1]][1] if i + 1 < len(names) else None
            later = [k for k, v in ch.items() if k >= m0 and (end is None or k < end)
                     and abs(v) > floor]
            nxt = min(later) if later else None
            if nxt and name.startswith("void"):
                red = per.get("reduction (§5)", {}).get("change")
                if red is None or (red > 0) == (ch[nxt] > 0):
                    nxt = None
            per[name] = {"month": nxt, "change": ch[nxt] if nxt else None,
                         "lag_months": lag(m0, nxt) if nxt else None}
        slopes = {p: round(statistics.fmean(v for k, v in ch.items() if a <= k <= b), 3)
                  for p, (a, b) in PERIODS.items()}
        out[cls] = {"floor": floor, "dates": per, "mean_monthly_change": slopes}
    ok = any(d["month"] for d in out["bis 1948"]["dates"].values())
    txt = "; ".join(
        f"{cls}: step floor {o['floor']:.1f}, " + ", ".join(
            f"{n} -> {d['month'] or 'no step'}"
            + (f" ({d['change']:+.1f}, {d['lag_months']} mo after the first index month)"
               if d["month"] else "")
            for n, d in o["dates"].items())
        + "; mean monthly change " + ", ".join(f"{p} {s:+.3f}" for p, s in o["mean_monthly_change"].items())
        for cls, o in out.items())
    return ok, txt, out


#: The ways this station reads "how far a class sits above the §5 line", all declared here.
#: The reduction bites only rents above 120 % of the cap, the tail of each cell, so the
#: statistic is the 3/4 range's upper end (about the 87.5th percentile). Column 8
#: (2003-2017) holds exempt 2014-2017 dwellings the Mietspiegel does not separate, so it is
#: read with and without. 2 summaries x 2 column sets = 4 variants (11f).
#:
#: The cell median was a declared statistic in the first run (§R1) and split the vote 2 of 4.
#: Removed 2026-09-23 by ruling (§R2): the caps are themselves 2013 Mietspiegel medians
#: scaled by the real wage index (Drucksache 18/2347, Begruendung to §6), so a cell's median
#: over its cap reads how far that cell's median grew since 2012 against real wages, and the
#: §5 line cuts rents above 120 % of that, which the median of a cell reaches only where the
#: whole cell has moved. The object the reduction acts on is the tail.
VARIANTS = [(stat, summ, col8) for stat in ("upper",) for summ in ("mean_ratio", "share_above")
            for col8 in (True, False)]


def prediction_from_mietspiegel(grid, table) -> dict:
    """For each variant, which index class sits further above the §5 line."""
    cap = {n: v for n, _, _, v in table}
    cells = []
    for row, cols in grid.items():
        loc = MS_LOCATION[row]
        for c, (med, lo, hi) in cols.items():
            line = OVERAGE * (cap[MS_TO_CAP[c]] + LOCATION[loc])
            cells.append({"row": row, "col": c, "class": INDEX_CLASS[c], "median": med,
                          "low": lo, "high": hi, "line": round(line, 3),
                          "median_ratio": round(med / line, 4), "upper_ratio": round(hi / line, 4)})
    variants = []
    for stat, summ, col8 in VARIANTS:
        vals = {}
        for cls in ("bis 1948", "ab 1949"):
            r = [c[f"{stat}_ratio"] for c in cells if c["class"] == cls and (col8 or c["col"] != 8)]
            vals[cls] = (statistics.fmean(r) if summ == "mean_ratio" else sum(x > 1 for x in r) / len(r)) if r else None
        old_more = None if None in vals.values() else vals["bis 1948"] > vals["ab 1949"]
        variants.append({"statistic": stat, "summary": summ, "column_8": col8,
                         "bis 1948": round(vals["bis 1948"], 4), "ab 1949": round(vals["ab 1949"], 4),
                         "old_further_above": old_more})
    return {"variants": variants, "cells": cells}


#: B129-5's branches and what each maps to (11c: the undecided cells map to no verdict).
B129_5_MAP = {"old falls more": True, "new falls more": False, "equal within 0.1 point": None}


def b129_5(pred, series, step=("2021-01", "2021-03")) -> tuple[bool | None, str, dict]:
    vs = pred["variants"]
    if not vs or any(v["old_further_above"] is None for v in vs):
        return None, "no Mietspiegel cells", {}
    votes = [v["old_further_above"] for v in vs]
    if len(set(votes)) > 1:
        predicted_old = None
    else:
        predicted_old = votes[0]
    a, b = step
    drop = {k: round(series[b][k] - series[a][k], 1) for k in ("bis 1948", "ab 1949")}
    pct = {k: round(100 * (series[b][k] / series[a][k] - 1), 2) for k in drop}
    if abs(drop["bis 1948"] - drop["ab 1949"]) <= 0.1:
        branch = "equal within 0.1 point"
    else:
        branch = "old falls more" if drop["bis 1948"] < drop["ab 1949"] else "new falls more"
    verdict = B129_5_MAP[branch]
    # the prediction is read only if all declared variants agree (11f); else no verdict
    ok = None if (verdict is None or predicted_old is None) else (verdict == predicted_old)
    n_old = sum(votes)
    pred_txt = ("undecided: the declared variants split "
                f"{n_old} for 'bis 1948 further above' vs {len(votes) - n_old} against"
                if predicted_old is None else
                f"{'bis 1948' if predicted_old else 'ab 1949'} further above the line in all "
                f"{len(votes)} variants")
    return ok, (f"prediction {pred_txt}; read {a} -> {b}: bis 1948 {drop['bis 1948']:+.1f} "
                f"({pct['bis 1948']:+.2f} %), ab 1949 {drop['ab 1949']:+.1f} "
                f"({pct['ab 1949']:+.2f} %); branch '{branch}'"), {
        "predicted_old_falls_more": predicted_old, "variant_votes": votes,
        "drop_points": drop, "drop_pct": pct, "branch": branch,
        "mapping": {k: v for k, v in B129_5_MAP.items()}}


def b129_6(deckel_from: str, bremse_after: str, bgb_text: str) -> tuple[bool | None, str, dict]:
    """A third class exists iff the two exemption lines differ and both are in the texts."""
    in_bgb = "nach dem 1. Oktober 2014" in bgb_text
    ok = in_bgb and deckel_from < bremse_after
    return ok, (f"Deckel exempts first ready from {deckel_from}; Bremse exempts first used "
                f"and let after {bremse_after} (BGB §556f text {'found' if in_bgb else 'NOT found'}); "
                f"dwellings first ready in [{deckel_from}, {bremse_after}] sit outside the cap "
                f"and inside the Bremse" if ok else "no third class"), {
        "deckel_exempt_from": deckel_from, "bremse_exempt_after": bremse_after}


# ---------------------------------------------------------------------------------------

def build(enacted, series, grid, bgb) -> list[dict]:
    pred = prediction_from_mietspiegel(grid, CAP_TABLE)
    rows = [
        ("B129-1", "instrument", b129_1(CAP_TABLE, enacted)),
        ("B129-1b", "instrument", b129_1b(CAP_TABLE, MS2013_MEDIAN, REAL_WAGE_FACTOR)),
        ("B129-2", "own_reading", b129_2(CAP_TABLE)),
        ("B129-3", "rival", b129_3(HAHN_T5, HAHN_T6, ANNOUNCEMENT_MONTH)),
        ("B129-4", "own_reading", b129_4(series, DATES)),
        ("B129-5", "own_reading", b129_5(pred, series)),
        ("B129-6", "own_reading", b129_6(DECKEL_EXEMPT_FROM, BREMSE_EXEMPT_AFTER, bgb)),
    ]
    out = []
    for name, kind, (passed, detail, obj) in rows:
        rec = {"name": name, "kind": kind, "passed": passed, "detail": detail, "object": obj}
        if kind == "rival":
            rec.update({
                "grid": "B" if passed else ("unread" if passed is None else "C"),
                "rival_shape": "point",
                "rival_premise": "a scalar potential on positions; the price gap between two "
                                 "classes of dwelling is fixed by their quality",
                "rival_entailment": "between two dates at which no dwelling's physical quality "
                                    "changed, the gap does not move, so the square "
                                    "(regulated/exempt x before/after) sums to zero",
                "cite": "Hahn, Kholodilin, Waltl & Fongoni (2023), Management Science, "
                        "Tables 5 and 6",
            })
        out.append(rec)
    out.append({"name": "B129-5 prediction cells", "kind": "bookkeeping", "passed": bool(pred["cells"]),
                "detail": f"{len(pred['cells'])} Mietspiegel cells", "object": pred})
    return out


def main() -> int:
    enacted = pdf_text("gvbl_2020_nr6_mietenwog.pdf")
    series = read_index()
    grid = read_mietspiegel()
    bgb = html.unescape(re.sub(r"<[^>]+>", " ",
                               (RAW / "bgb_556f.html").read_text(encoding="utf-8", errors="replace")))
    crit = build(enacted, series, grid, bgb)
    for c in crit:
        flag = {True: "PASS", False: "FAIL", None: "----"}[c["passed"]]
        print(f"{flag} {c['name']} [{c['kind']}]: {c['detail']}")
    print("\nindex around the legal dates (Nettokaltmieten, 2015 = 100):")
    for k in [k for k in series if "2019-05" <= k <= "2021-07"]:
        v = series[k]
        print(f"  {k}  zusammen {v['zusammen']:6.1f}  bis 1948 {v['bis 1948']:6.1f}  "
              f"ab 1949 {v['ab 1949']:6.1f}")
    print("\nMietspiegel grid (medians):")
    for r, cols in grid.items():
        print(f"  {r} {MS_LOCATION[r]:8s} " + "  ".join(f"{c}:{v[0]:5.2f}/{v[2]:5.2f}" for c, v in cols.items()))
    record = {"stage": "B129", "criteria": crit,
              "config": {"overage_line": OVERAGE, "announcement_month": ANNOUNCEMENT_MONTH,
                         "reduction_step_read": ["2021-01", "2021-03"]},
              "source": "data/b129/raw via experiments/b129_fetch.py"}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


def selftest() -> None:
    enacted = pdf_text("gvbl_2020_nr6_mietenwog.pdf")
    series = read_index()
    grid = read_mietspiegel()
    # B129-1: one wrong value must fail
    bad = [r if r[0] != 7 else (7, r[1], r[2], 6.18) for r in CAP_TABLE]
    assert b129_1(CAP_TABLE, enacted)[0] is True
    assert b129_1(bad, enacted)[0] is False, "B129-1 must catch a wrong cap"
    # B129-1b: a wrong factor must fail
    assert b129_1b(CAP_TABLE, MS2013_MEDIAN, REAL_WAGE_FACTOR)[0] is True
    assert b129_1b(CAP_TABLE, MS2013_MEDIAN, 1.114)[0] is False, "B129-1b must catch a wrong factor"
    # B129-2: an empty table must fail
    assert b129_2([])[0] is False
    # B129-3: inflate one pre-announcement month above the reading, rival no longer wrong
    t5 = dict(HAHN_T5); t5["2018-12"] = (0.20, 0.015)
    assert b129_3(t5, HAHN_T6, ANNOUNCEMENT_MONTH)[0] is False
    # B129-4: a flat index moves nowhere
    flat = {k: {"zusammen": 100.0, "bis 1948": 100.0, "ab 1949": 100.0} for k in series}
    assert b129_4(flat, DATES)[0] is False
    # B129-5: swap the two classes' paths, the direction must fail
    swapped = {k: {**v, "bis 1948": v["ab 1949"], "ab 1949": v["bis 1948"]}
               for k, v in series.items()}
    pred = prediction_from_mietspiegel(grid, CAP_TABLE)
    unanimous = {**pred, "variants": [v for v in pred["variants"] if v["statistic"] == "upper"]}
    assert len({v["old_further_above"] for v in unanimous["variants"]}) == 1
    assert b129_5(unanimous, series)[0] is not None
    assert b129_5(unanimous, swapped)[0] is not b129_5(unanimous, series)[0], \
        "B129-5 must flip when the two classes' paths are swapped"
    #        equal paths land in the undecided cell, not in a verdict
    same = {k: {**v, "ab 1949": v["bis 1948"]} for k, v in series.items()}
    assert b129_5(unanimous, same)[0] is None
    #        and variants that split give no verdict whatever the index does
    split = {**pred, "variants": unanimous["variants"] + [{**unanimous["variants"][0],
             "old_further_above": not unanimous["variants"][0]["old_further_above"]}]}
    assert b129_5(split, series)[0] is None
    # B129-6: equal lines, or the BGB text missing, leave no third class
    assert b129_6("2014-01-01", "2014-01-01", "nach dem 1. Oktober 2014")[0] is False
    assert b129_6("2014-01-01", "2014-10-01", "")[0] is False
    # the Mietspiegel reader: the empty cells are where the page leaves them
    assert set(grid["A"]) == {1, 2, 3, 4, 5, 6} and 3 not in grid["J"], "empty cells moved"
    assert all(lo <= med <= hi for cols in grid.values() for med, lo, hi in cols.values()), \
        "every median must sit inside its own 3/4 range"
    print("selftest ok: every criterion fails on a planted error; B129-5 undecided maps to None")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
