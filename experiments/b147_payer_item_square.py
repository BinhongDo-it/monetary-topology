"""B147: the payer-by-item square on a hospital's own published price file.

A United States hospital must publish, under 45 CFR 180.50, one machine-readable file with the
charge it has negotiated with each payer and plan for each item, and since 2024-07-01 the method
by which that charge is set: a percentage of billed charges, a fee schedule, a case rate, a per
diem, or other. Row i is an item as the file prints it, column a is a payer and plan, and P(a, i)
is the printed dollar price. For two columns and two rows the square is

    S(a, b; i, k) = ln P(a, i) - ln P(a, k) - ln P(b, i) + ln P(b, k).

With r_i = ln P(a, i) - ln P(b, i) on the rows two columns share, S = r_i - r_k, so every square of
a column pair is zero exactly when r is one constant on those rows: the two columns are then one
price list and a factor that depends on the payer alone.

**What is read.** For each column pair the rows are sorted by the methods the file prints on them:

    PP  both cells a percentage of billed charges     FF  both a fee schedule
    PF  one a percentage, the other a fee schedule    CC  both a case rate     DD  both a per diem

The first three are charged per item, so they share a billing unit and are also read pooled. A row
where the two cells are charged in different units (a per diem against a case rate, an item price
against a case rate) is not read: the product form speaks of the total paid for an episode, and the
length of stay is not in the file. Cells whose method is "other", or that carry only an algorithm
text, are not read either. They are counted.

**The price of a cell.** The printed negotiated dollar amount when there is one. Otherwise, for a
percentage-of-billed-charges cell, the printed percentage times the row's printed gross charge.
A percentage cell on a row without a gross charge has no price. A printed price of one cent or less
is a placeholder for an item that is not paid separately and is not read. The other order (percentage times
gross first, printed dollar second) is a declared knob and is swept.

**The floor is the printing grid.** A printed dollar amount moves by one cent (by one dollar in a
column that never prints cents); a price built from a percentage moves by one cent of the gross
charge and by one unit of the last decimal the percentage is printed to. Each row's r therefore
sits in an interval, and a column pair is consistent with one constant exactly on the rows whose
intervals share a point. The script finds the point covered by the most intervals; the rows whose
interval does not contain it are the squares (n - 1 on each column pair) that stand above the floor (each against
a row of the modal class). Counting against the modal constant gives the fewest non-zero squares
any constant could leave. Multiplying every floor by 2 and by 5 is the second declared knob.

**The zero domain is named before any price is read.** Where both columns print a percentage of
billed charges and the same pair of percentages on two rows, the square is zero by arithmetic. On
cells that also print the dollar amount this is a known answer the file can fail.

Run from the repository root:

    python experiments/b147_payer_item_square.py
    python experiments/b147_payer_item_square.py --selftest
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import b147_parse as bp  # noqa: E402
import b147_fetch as bf  # noqa: E402
import b147_price_base as pbase  # noqa: E402

M_P, M_F, M_C, M_D = bp.M_P, bp.M_F, bp.M_C, bp.M_D
PLACEHOLDER = 0.01               # a printed price of one cent or less stands for "no separate payment"; not read
EPS = 1e-9                       # absorbs float noise in a log of a product; far below one cent on any price here
CATS = ["PP", "PF", "FF", "CC", "DD", "per_item"]
FLOOR_MULTS = [1.0, 2.0, 5.0]
RULES = ["dollar_first", "computed_first"]
MIN_COMMON = [2, 10, 50]         # rows two columns must share before they can be put in one class
GARFIELD_PCT = [95.0, 90.0, 85.0, 95.0, 75.0]   # the five columns in file order, read from the file's first rows


# ---------------------------------------------------------------- numbers for the record

def sig(x, n=6):
    if x is None:
        return None
    x = float(x)
    if not math.isfinite(x):
        return None
    if x == 0:
        return 0.0
    return float("%.*g" % (n, x))


# ---------------------------------------------------------------- prices and columns

GROSS_LOW_LABEL = "on a row whose gross charge is one dollar or less (printed beside the reading, not part of it)"


def prepare(h: dict, rule: str = "dollar_first", merge: bool = True, gross_cap: float | None = None) -> dict:
    """Prices, floors and one sorted array set per column. Counts what was left out and why.

    gross_cap: when set, every cell on a row whose gross charge is at most this many dollars is left out. The
    reading does not use it; it is the second reading printed beside the first, because a gross of one dollar
    is a stand-in for an item the hospital does not charge separately, and a percentage of it is the same kind
    of stand-in as a price of one cent (placeholder rule)."""
    a = h["arr"]
    ncol = len(h["col_keys"])
    meth = a["meth"]
    has_d = np.isfinite(a["dollar"]) & (a["dollar"] > 0)
    has_c = (meth == M_P) & np.isfinite(a["pct"]) & (a["pct"] > 0) & np.isfinite(a["gross"]) & (a["gross"] > 0)
    computed = np.where(has_c, a["pct"] * a["gross"] / 100.0, np.nan)
    if rule == "dollar_first":
        use_d = has_d
    elif rule == "computed_first":
        use_d = has_d & ~has_c
    else:
        raise ValueError(rule)
    price = np.where(use_d, a["dollar"], computed)
    unit_known = np.isin(meth, (M_P, M_F, M_C, M_D))
    placeholder = unit_known & np.isfinite(price) & (price > 0) & (price <= PLACEHOLDER)
    readable = unit_known & np.isfinite(price) & (price > PLACEHOLDER)

    both = has_d & has_c
    agree = int((np.abs(a["dollar"][both] - computed[both]) <= 0.0100001).sum())
    left = {"method other or not printed": int((~unit_known).sum()),
            "no price: algorithm text only, or a percentage without a gross charge":
                int((unit_known & ~readable & ~placeholder).sum()),
            "a price of one cent or less (a placeholder, not a price)": int(placeholder.sum())}
    if gross_cap is not None:
        low = np.isfinite(a["gross"]) & (a["gross"] > 0) & (a["gross"] <= gross_cap)
        low_row = np.zeros(int(a["row"].max()) + 1 if len(a["row"]) else 0, dtype=bool)
        low_row[a["row"][low]] = True
        on_low = low_row[a["row"]] if len(a["row"]) else np.zeros(0, dtype=bool)
        left[GROSS_LOW_LABEL] = int((readable & on_low).sum())
        readable = readable & ~on_low

    # a (row, column) printed more than once: keep it when every printing agrees, drop it otherwise
    key = a["row"].astype(np.int64) * ncol + a["col"]
    idx = np.flatnonzero(readable)
    order = idx[np.argsort(key[idx], kind="stable")]
    ks = key[order]
    start = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]]) if len(ks) else np.array([], dtype=int)
    if len(ks):
        pmin = np.minimum.reduceat(price[order], start)
        pmax = np.maximum.reduceat(price[order], start)
        mmin = np.minimum.reduceat(meth[order], start)
        mmax = np.maximum.reduceat(meth[order], start)
        count = np.diff(np.r_[start, len(ks)])
        good = (pmin == pmax) & (mmin == mmax)
        keep = order[start[good]]
        left["printed more than once with different prices or methods"] = int(count[~good].sum())
        left["repeat printings that agree (one kept)"] = int((count[good] - 1).sum())
    else:
        keep = order
    keep = np.sort(keep)

    # the printing grid of each column's dollar amounts
    tick = np.full(ncol, 0.01)
    whole = []
    for c in range(ncol):
        k = keep[(a["col"][keep] == c) & use_d[keep]]
        if len(k) >= 30 and int(a["ddec"][k].max()) == 0:
            tick[c] = 1.0
            whole.append(c)
    pdec = a["pdec"].astype(np.float64)
    flog_d = tick[a["col"]] / np.where(price > 0, price, np.nan)
    flog_c = 0.01 / np.where(a["gross"] > 0, a["gross"], np.nan) + (10.0 ** -pdec) / np.where(a["pct"] > 0, a["pct"], np.nan)
    flog = np.where(use_d, flog_d, flog_c)

    cols = {}
    for c in range(ncol):
        k = keep[a["col"][keep] == c]
        if not len(k):
            continue
        o = np.argsort(a["row"][k], kind="stable")
        k = k[o]
        cols[c] = {"name": " | ".join(h["col_keys"][c]), "payer": h["col_keys"][c][0], "members": [c],
                   "rows": a["row"][k].astype(np.int64), "logp": np.log(price[k]), "flog": flog[k],
                   "meth": meth[k].astype(np.int8), "pct": np.where(np.isfinite(a["pct"][k]), a["pct"][k], -1.0),
                   "printed": use_d[k], "price": price[k]}
    merged = []
    if merge:
        seen = {}
        for c in sorted(cols):
            col = cols[c]
            signature = (col["payer"], col["rows"].tobytes(), col["price"].tobytes(), col["meth"].tobytes())
            if signature in seen:
                first = cols[seen[signature]]
                first["members"].append(c)
                first["name"] += " + " + h["col_keys"][c][1]
                merged.append(c)
            else:
                seen[signature] = c
        for c in merged:
            cols.pop(c)
    return {"id": h["id"], "cols": cols, "left_out": left, "columns_printed": ncol,
            "columns_after_merging_identical_plans": len(cols), "merged_away": len(merged),
            "whole_dollar_columns": [" | ".join(h["col_keys"][c]) for c in whole],
            "dollar_and_percentage_both_printed": int(both.sum()),
            "of_which_dollar_equals_percentage_times_gross_to_the_cent": agree,
            "cells_read": int(sum(len(v["rows"]) for v in cols.values())), "rule": rule}


# ---------------------------------------------------------------- the estimator

def modal_constant(r: np.ndarray, f: np.ndarray):
    """The point covered by the most intervals [r - f, r + f]; which rows contain it."""
    n = len(r)
    lo, hi = r - f, r + f
    vals = np.concatenate([lo, hi])
    typ = np.concatenate([np.zeros(n, dtype=np.int8), np.ones(n, dtype=np.int8)])
    order = np.lexsort((typ, vals))
    depth = np.cumsum(np.where(typ[order] == 0, 1, -1))
    j = int(depth.argmax())
    v = vals[order]
    c = 0.5 * (v[j] + v[j + 1]) if j + 1 < len(v) else v[j]
    inside = (lo <= c) & (c <= hi)
    return c, inside


def category_masks(ma: np.ndarray, mb: np.ndarray) -> dict:
    pp = (ma == M_P) & (mb == M_P)
    ff = (ma == M_F) & (mb == M_F)
    pf = ((ma == M_P) & (mb == M_F)) | ((ma == M_F) & (mb == M_P))
    return {"PP": pp, "PF": pf, "FF": ff, "CC": (ma == M_C) & (mb == M_C), "DD": (ma == M_D) & (mb == M_D),
            "per_item": pp | pf | ff}


def read_pairs(prep: dict, floor_mult: float = 1.0, eps: float = EPS, cats=CATS, row_keys=None,
               keep_examples: bool = True) -> dict:
    cols = prep["cols"]
    ids = sorted(cols)
    pairs = []
    mult = {c: [] for c in cats}
    size = {c: [] for c in cats}
    named = {"pairs": 0, "independent_squares": 0, "above_floor": 0, "vacuous_independent_squares": 0}
    unit_mismatch_rows = 0
    examples = []
    for x in range(len(ids)):
        A = cols[ids[x]]
        for y in range(x + 1, len(ids)):
            B = cols[ids[y]]
            common, ia, ib = np.intersect1d(A["rows"], B["rows"], assume_unique=True, return_indices=True)
            if not len(common):
                continue
            r = A["logp"][ia] - B["logp"][ib]
            f = (A["flog"][ia] + B["flog"][ib]) * floor_mult + eps
            ma, mb = A["meth"][ia], B["meth"][ib]
            masks = category_masks(ma, mb)
            unit_mismatch_rows += int(len(common) - masks["per_item"].sum() - masks["CC"].sum() - masks["DD"].sum())
            rec = {"a": ids[x], "b": ids[y], "common_rows": int(len(common))}
            for cat in cats:
                m = masks[cat]
                n = int(m.sum())
                entry = {"rows": n}
                if n >= 2:
                    c, inside = modal_constant(r[m], f[m])
                    above = int(n - inside.sum())
                    entry.update({"independent_squares": n - 1, "above_floor": above, "constant": float(c)})
                    if above:
                        dev = np.abs(r[m][~inside] - c)
                        mult[cat].append(dev / f[m][~inside])
                        size[cat].append(dev)
                        if keep_examples and cat == "PF" and row_keys is not None:
                            rows_m = common[m]
                            w = np.flatnonzero(~inside)
                            top = w[int(np.argmax(dev / f[m][~inside]))]
                            ref = np.flatnonzero(inside)[0]
                            examples.append((float((dev / f[m][~inside]).max()), ids[x], ids[y],
                                             int(rows_m[top]), int(rows_m[ref]), float(r[m][top] - r[m][ref])))
                rec[cat] = entry
            # the zero domain the file names: both cells a percentage, and the same printed pair of percentages
            m = masks["PP"] & (A["pct"][ia] > 0) & (B["pct"][ib] > 0)
            if int(m.sum()) >= 2:
                pa, pb = A["pct"][ia][m], B["pct"][ib][m]
                real = A["printed"][ia][m] & B["printed"][ib][m]
                rr, fr = r[m], f[m]
                groups = {}
                code = np.round(pa * 1e6).astype(np.int64) * 1000003 + np.round(pb * 1e6).astype(np.int64)
                for g in np.unique(code):
                    k = code == g
                    kr = k & real
                    if int(kr.sum()) >= 2:
                        c, inside = modal_constant(rr[kr], fr[kr])
                        groups[int(g)] = (int(kr.sum()) - 1, int(kr.sum() - inside.sum()))
                    if int((k & ~real).sum()) >= 2:
                        named["vacuous_independent_squares"] += int((k & ~real).sum()) - 1
                if groups:
                    named["pairs"] += 1
                    named["independent_squares"] += sum(v[0] for v in groups.values())
                    named["above_floor"] += sum(v[1] for v in groups.values())
                    rec["named_zero"] = {"independent_squares": sum(v[0] for v in groups.values()),
                                         "above_floor": sum(v[1] for v in groups.values())}
            pairs.append(rec)
    out = {"pairs": pairs, "unit_mismatch_rows": unit_mismatch_rows, "named_zero": named, "by_category": {}}
    for cat in cats:
        with_rows = [p for p in pairs if p[cat]["rows"] >= 2]
        mm = np.concatenate(mult[cat]) if mult[cat] else np.array([])
        ss = np.concatenate(size[cat]) if size[cat] else np.array([])
        indep = sum(p[cat]["independent_squares"] for p in with_rows)
        above = sum(p[cat]["above_floor"] for p in with_rows)
        out["by_category"][cat] = {
            "row_and_column_pair_cells": int(sum(p[cat]["rows"] for p in pairs)),
            "column_pairs": len(with_rows),
            "column_pairs_with_a_square_above_floor": sum(1 for p in with_rows if p[cat]["above_floor"]),
            "column_pairs_all_within_floor": sum(1 for p in with_rows if not p[cat]["above_floor"]),
            "independent_squares": int(indep), "above_floor": int(above),
            "share_above_floor": sig(above / indep) if indep else None,
            "median_multiple_of_floor": sig(np.median(mm)) if len(mm) else None,
            "p10_multiple_of_floor": sig(np.percentile(mm, 10)) if len(mm) else None,
            "median_abs_log_gap": sig(np.median(ss)) if len(ss) else None,
            "p90_abs_log_gap": sig(np.percentile(ss, 90)) if len(ss) else None}
    if keep_examples and row_keys is not None:
        examples.sort(reverse=True)
        out["examples_PF"] = [example(prep, row_keys, e) for e in examples[:3]]
        thin = sorted((p["PF"]["rows"], cols[p["a"]]["name"], cols[p["b"]]["name"]) for p in pairs if p["PF"]["rows"] > 0)
        out["thinnest_PF_column_pairs"] = [{"rows": t[0], "a": t[1], "b": t[2]} for t in thin[:3]]
    return out


def example(prep, row_keys, e) -> dict:
    multiple, a, b, row_i, row_k, s = e
    cols = prep["cols"]

    def cell(c, row):
        col = cols[c]
        j = int(np.searchsorted(col["rows"], row))
        return {"price": sig(col["price"][j], 10), "method": bp.METHODS[int(col["meth"][j])]}

    def label(row):
        k = row_keys[row]
        return {"description": k[6], "codes": ["%s %s" % (t, c) for t, c in k[0]], "setting": k[1]}

    return {"multiple_of_floor": sig(multiple), "square_log": sig(s), "column_a": cols[a]["name"],
            "column_b": cols[b]["name"], "row_i": label(row_i), "row_k": label(row_k),
            "P_a_i": cell(a, row_i), "P_b_i": cell(b, row_i), "P_a_k": cell(a, row_k), "P_b_k": cell(b, row_k)}


def classes(prep: dict, pairs: list, min_common: int, share: float = 1.0) -> list:
    """Columns whose price ratio is one constant on the per-item rows they share, joined into classes.

    The classes are the connected components of the graph whose edges are such column pairs with at
    least ``min_common`` shared rows. Their number is not the fewest common price bases: a chain of
    compatible pairs can join two columns that differ on the rows those two share, and two columns
    that share fewer rows than ``min_common`` stay apart even where one base fits both. The fewest common
    price bases, with a joint check over every set, is computed apart (b147_price_base.fewest_bases).
    """
    ids = sorted(prep["cols"])
    parent = {c: c for c in ids}

    def find(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for p in pairs:
        e = p["per_item"]
        if e["rows"] >= max(2, min_common) and (e["rows"] - e["above_floor"]) >= share * e["rows"]:
            parent[find(p["a"])] = find(p["b"])
    groups = {}
    for c in ids:
        groups.setdefault(find(c), []).append(c)
    out = []
    for members in sorted(groups.values(), key=lambda m: (-len(m), m)):
        letters = np.concatenate([prep["cols"][c]["meth"] for c in members])
        out.append({"members": [prep["cols"][c]["name"] for c in members],
                    "cells_by_method": {bp.METHODS[m]: int((letters == m).sum()) for m in range(4) if int((letters == m).sum())}})
    return out


# ---------------------------------------------------------------- the Medicare Part B drug payment limit (B147-8)

ASP_DIR = bp.RAW / "cms_asp"
CLFS_DIR = bp.RAW / "clfs"        # fetched 2026-10-29 after the AMA CPT licence was accepted by hand
ASP_IDS = ["asp_2024q4", "asp_2025q1", "asp_2025q2", "asp_2025q3", "asp_2025q4",
           "asp_2026q1", "asp_2026q2", "asp_2026q3", "asp_2026q4"]
#: the design named the four 2026 quarters; the four 2025 quarters were added on the same day so the knob
#: reaches the quarters a file dated early 2026 may have loaded
KNOB_QUARTERS = ["asp_2025q1", "asp_2025q2", "asp_2025q3", "asp_2025q4",
                 "asp_2026q1", "asp_2026q2", "asp_2026q3", "asp_2026q4"]
#: the quarter whose file covers each hospital file's last_updated_on
DEFAULT_QUARTER = {"garfield": "asp_2026q1", "ohsu": "asp_2026q1", "cheshire": "asp_2026q1", "uihc": "asp_2026q1",
                   "uihc_dt": "asp_2026q1", "mh_tmc": "asp_2026q2", "cvmc": "asp_2026q4", "deaconess": "asp_2024q4"}
ASP_TITLE = "Payment Allowance Limits for Medicare Part B Drugs"
ASP_HEADER = ["HCPCS Code", "Short Description", "HCPCS Code Dosage", "Payment Limit"]
ASP_TICK = 0.001                 # the payment limit is printed to three decimals
DRUG_CODE_TYPES = ("HCPCS", "CPT")   # CPT is level I of HCPCS; the limit file lists both kinds of code
ROWS_OFF_PRINTED = 100           # rows off the constant printed per column (all of them below this count)
MAPPING_B147_8 = {
    "two or more shared drug rows, most of them on one constant times the default quarter's limit, and every row "
    "off that constant is a row on which a column with a different constant is off by the same ratio":
        "not read, no verdict (third cell): listed with those rows; the deviation sits on the row, that is on the "
        "limit printed for that code or the base the hospital uses for it (the limit files on disk are later "
        "revisions of each quarter), and not on the column's contract",
    "two or more shared drug rows, and the column's price is one constant times the limit of the default quarter":
        "follows the payment limit: the constant c is printed",
    "two or more shared drug rows, the column follows the limit of no quarter in the knob set":
        "does not follow the payment limit: rows above the floor and the median gap printed",
    "fewer than two shared drug rows in every quarter": "not read, in no cell",
    "the column follows another quarter's limit and not the default quarter's (the answer moves on the quarter knob)":
        "not read, listed with the quarters it follows",
}


def load_asp(path: Path) -> dict:
    """One quarter's payment limit file: code -> (limit, dosage). Header compared with the expected names (D54)."""
    import csv
    import io
    import zipfile
    out = {"file": path.name, "member": None, "title": None, "effective": None, "note_1": None,
           "header": None, "header_matches": False, "codes": {}, "rows": 0, "ambiguous_codes": 0,
           "limit_decimals_max": 0}
    with zipfile.ZipFile(path) as z:
        mem = [i for i in z.infolist() if i.filename.lower().endswith(".csv")
               and ("payment limit file" in i.filename.lower() or "asp pricing file" in i.filename.lower())]
        if len(mem) != 1:
            return out
        out["member"] = mem[0].filename
        stamp = re.search(r"(\d{2})(\d{2})(\d{2})\.csv$", mem[0].filename)
        # the date CMS put in the member's name: each file on disk is the revision current on the day it was fetched
        out["revision_in_member_name"] = ("20%s-%s-%s" % (stamp.group(3), stamp.group(1), stamp.group(2))
                                          if stamp else None)
        text = z.read(mem[0]).decode("cp1252", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    hdr = None
    for i, row in enumerate(rows):
        cell = (row[0] if row else "").strip()
        if out["title"] is None and cell:
            out["title"] = cell
        if cell.startswith("Effective") and out["effective"] is None:
            out["effective"] = cell
        if cell.startswith("Note 1") and out["note_1"] is None:
            out["note_1"] = cell
        if cell == "HCPCS Code":
            hdr = i
            break
    if hdr is None:
        return out
    out["header"] = [c.strip() for c in rows[hdr] if c.strip()]
    out["header_matches"] = [c.strip() for c in rows[hdr][:4]] == ASP_HEADER and out["title"] == ASP_TITLE
    seen = {}
    for row in rows[hdr + 1:]:
        if len(row) < 4 or not row[0].strip():
            continue
        code = row[0].strip().upper()
        v, dec = bp.num(row[3])
        if not (v == v and v > 0):
            continue
        out["rows"] += 1
        out["limit_decimals_max"] = max(out["limit_decimals_max"], dec)
        if code in seen and seen[code][0] != v:
            seen[code] = (float("nan"), "")
        else:
            seen[code] = (v, row[2].strip())
    out["ambiguous_codes"] = sum(1 for v in seen.values() if v[0] != v[0])
    out["codes"] = {k: v for k, v in seen.items() if v[0] == v[0]}
    return out


def load_asp_tables(raw_dir: Path = ASP_DIR) -> dict:
    tables = {}
    for q in ASP_IDS:
        name = bf.ASP_FILES[q].replace("/", "_")       # the fetcher's file name on disk
        p = raw_dir / name
        if p.exists():
            t = load_asp(p)
            t["id"] = q
            tables[q] = t
    return tables


def drug_code_of_rows(row_keys: list) -> tuple[list, dict]:
    """For each row, its one HCPCS (or CPT) code, or None; and counts of why rows are not drug rows."""
    out, why = [], {"rows with exactly one HCPCS or CPT code": 0, "rows with two or more": 0, "rows with none": 0}
    for k in row_keys:
        codes = {c.strip().upper() for t, c in k[0] if str(t).strip().upper() in DRUG_CODE_TYPES and c.strip()}
        if len(codes) == 1:
            out.append(codes.pop())
            why["rows with exactly one HCPCS or CPT code"] += 1
        else:
            out.append(None)
            why["rows with two or more" if codes else "rows with none"] += 1
    return out, why


def asp_rows(codes_of_row: list, table: dict, tick: float = ASP_TICK):
    """(rows, ln limit, floor in logs) for the rows whose one code is in the limit file; rows ascending.
    tick is the reference table's printing grid (0.001 for the drug payment limit, 0.01 for the lab fee schedule)."""
    rows, lim = [], []
    for i, c in enumerate(codes_of_row):
        if c is not None and c in table["codes"]:
            rows.append(i)
            lim.append(table["codes"][c][0])
    lim = np.array(lim, dtype=np.float64)
    return np.array(rows, dtype=np.int64), np.log(lim), tick / lim if len(lim) else np.zeros(0)


def asp_column(col: dict, rows, logl, fl, share: float = 1.0, asp_floor: bool = True, eps: float = EPS) -> dict:
    """One hospital column against the payment-limit pseudo-column, on drug rows charged per item."""
    per_item = (col["meth"] == M_P) | (col["meth"] == M_F)
    crow = col["rows"][per_item]
    common, ia, ib = np.intersect1d(crow, rows, assume_unique=True, return_indices=True)
    n = int(len(common))
    out = {"shared_drug_rows": n}
    if n < 2:
        out["state"] = "unread"
        return out
    lp, fp = col["logp"][per_item][ia], col["flog"][per_item][ia]
    r = lp - logl[ib]
    f = fp + (fl[ib] if asp_floor else 0.0) + eps
    c, inside = modal_constant(r, f)
    within = int(inside.sum())
    gap = np.abs(r[~inside] - c)
    out.update({"state": "follows" if within >= share * n else "does_not_follow", "within_floor": within,
                "above_floor": n - within, "constant_c": sig(math.exp(c), 6),
                "follows_at_99_percent_of_rows": within >= 0.99 * n,
                "tier_reached": max([m for m in MIN_COMMON if n >= m] or [0]),
                "median_abs_log_gap_above": sig(np.median(gap)) if len(gap) else None,
                "methods_on_shared_rows": {bp.METHODS[m]: int((col["meth"][per_item][ia] == m).sum())
                                           for m in (M_P, M_F) if int((col["meth"][per_item][ia] == m).sum())}})
    # kept for the reading across columns and taken off before the record is written
    out["_aux"] = {"logc": float(c), "rows_above": common[~inside], "dev_above": r[~inside] - c, "f_above": f[~inside],
                   "f_median": float(np.median(f[inside])) if within else float(np.median(f))}
    return out


def rows_the_deviation_travels_with(dq: dict, need_distinct_c: bool = True) -> tuple[dict, dict]:
    """Rows on which a column is off its constant times the limit by the same ratio as another column with a
    different constant. Only columns whose constant is carried by most of their shared drug rows take part, so
    that each has a constant to be off from. A ratio shared by two contracts with different multipliers sits on
    the row, which points at the limit printed for that code, and not at either contract.

    Returns (rows shared by each column, the shared rows with their ratio and how many columns carry them)."""
    cand = [c for c, d in dq.items() if d["state"] == "does_not_follow" and d["within_floor"] > d["above_floor"]]
    by_col = {c: set() for c in cand}
    rows = {}
    for x in range(len(cand)):
        X = dq[cand[x]]["_aux"]
        for y in range(x + 1, len(cand)):
            Y = dq[cand[y]]["_aux"]
            if need_distinct_c and abs(X["logc"] - Y["logc"]) <= X["f_median"] + Y["f_median"]:
                continue
            common, ia, ib = np.intersect1d(X["rows_above"], Y["rows_above"], assume_unique=True, return_indices=True)
            if not len(common):
                continue
            same = np.abs(X["dev_above"][ia] - Y["dev_above"][ib]) <= X["f_above"][ia] + Y["f_above"][ib]
            for row, dev in zip(common[same].tolist(), X["dev_above"][ia][same].tolist()):
                by_col[cand[x]].add(row)
                by_col[cand[y]].add(row)
                rows.setdefault(row, [dev, set()])[1].update((cand[x], cand[y]))
    return by_col, rows


def travel_table(shared_rows: dict, codes_of_row: list) -> list:
    """Shared rows grouped by code and ratio: one code sits on several rows (departments, settings)."""
    g = {}
    for r, (dev, cols) in shared_rows.items():
        k = (codes_of_row[r], sig(math.exp(dev), 5))
        t = g.setdefault(k, [0, 0])
        t[0] += 1
        t[1] = max(t[1], len(cols))
    return sorted(([k[0], k[1], v[0], v[1]] for k, v in g.items()), key=lambda x: (-x[3], -x[2], x[0], x[1]))


def asp_reading(prep: dict, row_keys: list, tables: dict, default_q: str, share: float = 1.0,
                asp_floor: bool = True, classes2: list | None = None, need_distinct_c: bool = True,
                knob: list | None = None, tick: float = ASP_TICK) -> dict:
    """B147-8 for one hospital: every column in one of four cells, the default quarter and the quarter knob.
    B147-9 reads the laboratory fee schedule through the same function with its own knob and printing grid."""
    if default_q not in tables or not tables[default_q]["header_matches"]:
        return {"state": "void", "why": "the payment limit file of the default quarter %s is not on disk or its "
                                        "header does not read as expected" % default_q}
    codes_of_row, why = drug_code_of_rows(row_keys)
    quarters = [default_q] + [q for q in (KNOB_QUARTERS if knob is None else knob)
                              if q != default_q and q in tables and tables[q]["header_matches"]]
    per_q = {}
    drug_rows = {}
    for q in quarters:
        rows, logl, fl = asp_rows(codes_of_row, tables[q], tick=tick)
        drug_rows[q] = int(len(rows))
        per_q[q] = {c: asp_column(col, rows, logl, fl, share=share, asp_floor=asp_floor) for c, col in prep["cols"].items()}
    shared_by_col, shared_rows = rows_the_deviation_travels_with(per_q[default_q], need_distinct_c=need_distinct_c)
    aux = {c: per_q[default_q][c].get("_aux") for c in prep["cols"]}
    for q in quarters:
        for d in per_q[q].values():
            d.pop("_aux", None)
    cls = {}
    if classes2:
        for i, cl in enumerate(classes2):
            for nme in cl["members"]:
                cls[nme] = i
    cells = {"follows": [], "does_not_follow": [], "unread": [], "moved_on_quarter_knob": [],
             "unresolved_reference_row": []}

    def rows_off(c):
        x = aux[c]
        o = np.argsort(-np.abs(x["dev_above"]), kind="stable")[:ROWS_OFF_PRINTED]
        return [[codes_of_row[int(x["rows_above"][j])], sig(math.exp(float(x["dev_above"][j])), 5),
                 int(x["rows_above"][j]) in shared_by_col.get(c, set())] for j in o]

    for c, col in prep["cols"].items():
        d = per_q[default_q][c]
        follows_in = [q for q in quarters if per_q[q][c]["state"] == "follows"]
        readq = [(per_q[q][c]["within_floor"] / per_q[q][c]["shared_drug_rows"], q) for q in quarters
                 if per_q[q][c]["state"] != "unread"]
        best = max(readq) if readq else None
        entry = {"column": col["name"], "default_quarter": d, "quarters_followed": follows_in,
                 "class_at_2_rows": cls.get(col["name"]),
                 "best_quarter": None if best is None else
                 {"quarter": best[1], "share_of_rows_within_floor": sig(best[0], 4),
                  "constant_c": per_q[best[1]][c]["constant_c"], "shared_drug_rows": per_q[best[1]][c]["shared_drug_rows"]}}
        if d["state"] == "does_not_follow" and d["within_floor"] > d["above_floor"]:
            # the object behind the cell: every row off the constant, its code, ratio to c times the limit, and
            # whether another column with a different constant is off by the same ratio on it
            entry["rows_off_the_constant"] = rows_off(c)
        if d["state"] == "follows":
            cells["follows"].append(entry)
        elif follows_in:
            cells["moved_on_quarter_knob"].append(entry)
        elif d["state"] == "does_not_follow" and c in shared_by_col and \
                len(shared_by_col[c]) == d["above_floor"]:
            cells["unresolved_reference_row"].append(entry)
        elif d["state"] == "does_not_follow":
            cells["does_not_follow"].append(entry)
        else:
            cells["unread"].append(entry)
    placed = sorted(e["column"] for v in cells.values() for e in v)
    # printed, not judged: columns whose best quarter puts at least 99 in 100 shared drug rows on one constant
    near = sorted(([e["column"], e["best_quarter"]["quarter"], e["best_quarter"]["constant_c"],
                    e["best_quarter"]["share_of_rows_within_floor"], e["best_quarter"]["shared_drug_rows"]]
                   for v in cells.values() for e in v
                   if e["best_quarter"] and e["best_quarter"]["shared_drug_rows"] >= 10
                   and e["best_quarter"]["share_of_rows_within_floor"] >= 0.99), key=lambda x: (-x[3], x[0]))
    return {"state": "read", "default_quarter": default_q, "quarters_read": quarters, "drug_rows_by_quarter": drug_rows,
            "at_99_percent_of_rows_best_quarter": near,
            "row_codes": why, "cells": cells,
            # as (code, ratio to c times the limit, rows with that code and ratio, most columns off by it on one row)
            "rows_the_deviation_travels_with": travel_table(shared_rows, codes_of_row),
            "revision_of_the_default_quarter_file": tables[default_q].get("revision_in_member_name"),
            "counts": {k: len(v) for k, v in cells.items()},
            "partition_covers": placed == sorted(col["name"] for col in prep["cols"].values()),
            "squares_zero_by_construction_on_following_columns":
                int(sum(e["default_quarter"]["shared_drug_rows"] - 1 for e in cells["follows"]))}


def clfs_state(tables: dict | None = None) -> dict:
    """What B147-8 says about the laboratory half: since 2026-10-29 that half is its own criterion, B147-9."""
    if tables is None:
        tables = load_clfs_tables() if CLFS_DIR.exists() else {}
    read = sorted(q for q, t in tables.items() if t["header_matches"])
    if not read:
        return {"state": "unread", "why": "the Clinical Laboratory Fee Schedule files are not on disk; their download "
                                          "on cms.gov goes through the AMA CPT licence page"}
    return {"state": "read in B147-9", "files": read}


# ---------------------------------------------------------------- the Clinical Laboratory Fee Schedule (B147-9)

CLFS_IDS = ["clfs_2024q4", "clfs_2025q1", "clfs_2025q2", "clfs_2025q3", "clfs_2025q4",
            "clfs_2026q1", "clfs_2026q2", "clfs_2026q3", "clfs_2026q4"]
CLFS_KNOB = ["clfs_2025q1", "clfs_2025q2", "clfs_2025q3", "clfs_2025q4",
             "clfs_2026q1", "clfs_2026q2", "clfs_2026q3", "clfs_2026q4"]
#: the same quarter as B147-8: the one whose file covers each hospital file's last_updated_on
CLFS_DEFAULT_QUARTER = {k: "clfs_" + v[4:] for k, v in DEFAULT_QUARTER.items()}
CLFS_TITLE = "Clinical Diagnostic Laboratory Fee Schedule"
CLFS_HEADER = ["YEAR", "HCPCS", "MOD", "EFF_DATE", "INDICATOR", "RATE"]
#: the record layout in the same zip: "Payment Rate: Payment amount associated with each HCPCS code";
#: "Modifier: Where modifier is shown, QW denotes a CLIA waived test"; "Indicator: National or local pricing
#: indicator"; the text file's picture for the rate is 99999.99
CLFS_TICK = 0.01
MAPPING_B147_9 = {
    "two or more shared laboratory rows, most of them on one constant times the default quarter's rate, and every "
    "row off that constant is a row on which a column with a different constant is off by the same ratio":
        "not read, no verdict (third cell): listed with those rows; the deviation sits on the row (the rate printed "
        "for that code, or the unit the hospital prices it in), not on the column's contract",
    "two or more shared laboratory rows, and the column's price is one constant times the rate of the default quarter":
        "follows the laboratory fee schedule: the constant c is printed",
    "two or more shared laboratory rows, the column follows the rate of no quarter in the knob set":
        "does not follow the laboratory fee schedule: rows above the floor and the median gap printed",
    "fewer than two shared laboratory rows in every quarter": "not read, in no cell",
    "the column follows another quarter's rate and not the default quarter's (the answer moves on the quarter knob)":
        "not read, listed with the quarters it follows",
}


def load_clfs(path: Path) -> dict:
    """One quarter's laboratory fee schedule: code -> (rate, ""). Only rows with no modifier and the national
    pricing indicator N are kept; a code printed twice with two such rates is dropped. Header compared with the
    expected names and the title with the expected words (D54)."""
    import csv
    import io
    import zipfile
    out = {"file": path.name, "member": None, "title": None, "header": None, "header_matches": False, "codes": {},
           "rows": 0, "rows_with_a_modifier": 0, "rows_not_national": 0, "rows_zero_rate": 0, "ambiguous_codes": 0,
           "rate_decimals_max": 0, "indicators": {}, "modifiers": {}, "effective_dates": {}}
    with zipfile.ZipFile(path) as z:
        mem = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
        if len(mem) != 1:
            return out
        out["member"] = mem[0].filename
        text = z.read(mem[0]).decode("cp1252", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    hdr = None
    for i, row in enumerate(rows):
        cell = (row[0] if row else "").strip()
        if out["title"] is None and cell:
            out["title"] = cell
        if cell == "YEAR":
            hdr = i
            break
    if hdr is None:
        return out
    out["header"] = [c.strip() for c in rows[hdr] if c.strip()]
    out["header_matches"] = [c.strip() for c in rows[hdr][:6]] == CLFS_HEADER and CLFS_TITLE in (out["title"] or "")
    seen = {}
    for row in rows[hdr + 1:]:
        if len(row) < 6 or not row[1].strip():
            continue
        out["rows"] += 1
        code, mod, ind = row[1].strip().upper(), row[2].strip().upper(), row[4].strip().upper()
        out["indicators"][ind] = out["indicators"].get(ind, 0) + 1
        out["effective_dates"][row[3].strip()] = out["effective_dates"].get(row[3].strip(), 0) + 1
        if mod:
            out["modifiers"][mod] = out["modifiers"].get(mod, 0) + 1
            out["rows_with_a_modifier"] += 1
            continue
        if ind != "N":
            out["rows_not_national"] += 1
            continue
        v, dec = bp.num(row[5])
        if not (v == v and v > 0):
            out["rows_zero_rate"] += 1
            continue
        out["rate_decimals_max"] = max(out["rate_decimals_max"], dec)
        if code in seen and seen[code][0] != v:
            seen[code] = (float("nan"), "")
        else:
            seen[code] = (v, "")
    out["ambiguous_codes"] = sum(1 for v in seen.values() if v[0] != v[0])
    out["codes"] = {k: v for k, v in seen.items() if v[0] == v[0]}
    return out


def load_clfs_tables(raw_dir: Path = CLFS_DIR) -> dict:
    tables = {}
    for q in CLFS_IDS:
        p = raw_dir / (bf.CLFS_FILES[q] + ".zip")
        if p.exists():
            t = load_clfs(p)
            t["id"] = q
            tables[q] = t
    return tables


def clfs_reading(prep: dict, row_keys: list, tables: dict, default_q: str, classes2: list | None = None,
                 share: float = 1.0, ref_floor: bool = True, need_distinct_c: bool = True,
                 knob: list | None = None) -> dict:
    """B147-9 for one hospital: the B147-8 reading with the laboratory fee schedule as the pseudo-column, on rows
    carrying exactly one HCPCS or CPT code that the fee schedule lists."""
    if default_q not in tables or not tables[default_q]["header_matches"]:
        return {"state": "void", "why": "the laboratory fee schedule file of the default quarter %s is not on disk or "
                                        "its header does not read as expected" % default_q}
    r = asp_reading(prep, row_keys, tables, default_q, share=share, asp_floor=ref_floor, classes2=classes2,
                    need_distinct_c=need_distinct_c, knob=CLFS_KNOB if knob is None else knob, tick=CLFS_TICK)
    r["lab_rows_by_quarter"] = r.pop("drug_rows_by_quarter")
    r.pop("revision_of_the_default_quarter_file", None)
    codes_of_row, _ = drug_code_of_rows(row_keys)
    lab = [c for c in codes_of_row if c is not None and c in tables[default_q]["codes"]]
    r["lab_rows_by_code_range_default_quarter"] = {
        "CPT 80000-89999": sum(1 for c in lab if len(c) == 5 and c.isdigit() and c[0] == "8"),
        "other codes on the fee schedule": sum(1 for c in lab if not (len(c) == 5 and c.isdigit() and c[0] == "8"))}
    return r


# ---------------------------------------------------------------- two campuses of one entity (printed, not judged)

def campus_keys(h: dict, sig_rows: dict, sig_cols: dict):
    """(keys, prices) of the cells that print a dollar amount, keyed by (payer, plan, codes); keys that carry two
    prices in one file are dropped. The signature dictionaries are shared so two files get the same keys."""
    a = h["arr"]
    rsig = np.array([sig_rows.setdefault(tuple(tuple(x) for x in k[0]), len(sig_rows)) for k in h["row_keys"]],
                    dtype=np.int64)
    csig = np.array([sig_cols.setdefault(tuple(c), len(sig_cols)) for c in h["col_keys"]], dtype=np.int64)
    ok = np.isfinite(a["dollar"]) & (a["dollar"] > PLACEHOLDER)
    key = rsig[a["row"][ok]] * 1_000_003 + csig[a["col"][ok]]
    price = a["dollar"][ok]
    o = np.lexsort((price, key))
    key, price = key[o], price[o]
    start = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]) if len(key) else np.zeros(0, dtype=int)
    if not len(key):
        return key, price, 0
    pmin = np.minimum.reduceat(price, start)
    pmax = np.maximum.reduceat(price, start)
    good = pmin == pmax
    return key[start[good]], pmin[good], int((~good).sum())


def campus_identity(ka, pa, kb, pb) -> dict:
    common, ia, ib = np.intersect1d(ka, kb, assume_unique=True, return_indices=True)
    eq = np.abs(pa[ia] - pb[ib]) < 0.005
    return {"keys_in_first": int(len(ka)), "keys_in_second": int(len(kb)), "common_keys": int(len(common)),
            "equal_to_the_cent": int(eq.sum()), "share_equal": sig(eq.mean()) if len(common) else None}


# ---------------------------------------------------------------- one hospital

def pair_seconds(prep: dict, sample: int = 40) -> float:
    """Seconds one column pair takes in read_pairs, timed on up to `sample` pairs (printed, never recorded)."""
    import time
    ids = sorted(prep["cols"])
    pairs = [(ids[x], ids[y]) for x in range(len(ids)) for y in range(x + 1, len(ids))][:sample]
    if not pairs:
        return 0.0
    sub = {"cols": {c: prep["cols"][c] for p in pairs for c in p}}
    t0 = time.perf_counter()
    read_pairs(sub, keep_examples=False)
    n = len(sub["cols"])
    return (time.perf_counter() - t0) / max(1, n * (n - 1) // 2)


def read_hospital(h: dict, sweep: bool = True, asp_tables: dict | None = None, default_q: str | None = None,
                  verbose: bool = False, gross_check: bool = True, clfs_tables: dict | None = None,
                  clfs_default_q: str | None = None) -> dict:
    prep = prepare(h)
    if verbose:
        m = len(prep["cols"])
        s = pair_seconds(prep)
        print("   cost before reading: %d columns, %d column pairs x 6 readings x %.4f s a pair = %.0f s"
              % (m, m * (m - 1) // 2, s, m * (m - 1) / 2 * 6 * s), flush=True)
    main = read_pairs(prep, row_keys=h["row_keys"])
    rep = {k: prep[k] for k in prep if k not in ("cols",)}
    rep["columns"] = [{"name": c["name"], "cells": int(len(c["rows"])),
                       "by_method": {bp.METHODS[m]: int((c["meth"] == m).sum()) for m in range(4) if int((c["meth"] == m).sum())}}
                      for c in prep["cols"].values()]
    rep.update({k: main[k] for k in main if k != "pairs"})
    rep["classes"] = {str(mc): classes(prep, main["pairs"], mc) for mc in MIN_COMMON}
    rep["classes_at_99_percent_of_rows"] = classes(prep, main["pairs"], 10, share=0.99)
    rep["k"] = {str(mc): len(rep["classes"][str(mc)]) for mc in MIN_COMMON}
    rep["k_at_99_percent_of_rows"] = len(rep["classes_at_99_percent_of_rows"])
    rep["fewest_common_price_bases"] = pbase.fewest_bases(prep, main["pairs"], eps=EPS)
    inside = {n: i for i, cl in enumerate(rep["classes"][str(MIN_COMMON[0])]) for n in cl["members"]}
    names = {c: v["name"] for c, v in prep["cols"].items()}
    rep["column_pairs_inside_one_class_with_a_square_above_floor"] = sum(
        1 for p in main["pairs"] if p["per_item"]["rows"] >= 2 and p["per_item"]["above_floor"]
        and inside[names[p["a"]]] == inside[names[p["b"]]])
    rep["partition_covers"] = sorted(n for cl in rep["classes"][str(MIN_COMMON[0])] for n in cl["members"]) == \
        sorted(c["name"] for c in prep["cols"].values())
    # D22: the squares in this record are n - 1 on each column pair, summed over pairs; pairs that share a column
    # are not independent of one another, and the whole file has at most (m - 1)(n - 1) independent squares
    m_cols = len(prep["cols"])
    n_rows = int(len(np.unique(np.concatenate([c["rows"] for c in prep["cols"].values()])))) if m_cols else 0
    rep["d22"] = {"columns": m_cols, "rows_with_a_read_cell": n_rows,
                  "independent_squares_at_most": (m_cols - 1) * (n_rows - 1) if m_cols and n_rows else 0}
    if gross_check:
        pg = prepare(h, gross_cap=1.0)
        low = pg["left_out"][GROSS_LOW_LABEL]
        g = {"cells_on_such_rows": low}
        if low:
            gr = read_pairs(pg, row_keys=h["row_keys"])
            g["by_category"] = gr["by_category"]
            g["examples_PF"] = gr.get("examples_PF", [])[:1]
            del gr
        del pg
        rep["rows_with_gross_at_most_one_dollar_left_out"] = g
    rep["sweep_PF"] = []
    if sweep:
        for rule in RULES:
            p2 = prep if rule == "dollar_first" else prepare(h, rule=rule)
            for fm in FLOOR_MULTS:
                if rule == "dollar_first" and fm == 1.0:
                    s = main["by_category"]["PF"]
                else:
                    s = read_pairs(p2, floor_mult=fm, cats=["PF"], keep_examples=False)["by_category"]["PF"]
                rep["sweep_PF"].append({"rule": rule, "floor_multiple": fm, "column_pairs": s["column_pairs"],
                                        "column_pairs_with_a_square_above_floor": s["column_pairs_with_a_square_above_floor"],
                                        "independent_squares": s["independent_squares"], "above_floor": s["above_floor"]})
    if asp_tables is not None:
        rep["asp"] = asp_reading(prep, h["row_keys"], asp_tables, default_q or "asp_2026q1",
                                 classes2=rep["classes"][str(MIN_COMMON[0])])
    if clfs_tables is not None:
        rep["clfs"] = clfs_reading(prep, h["row_keys"], clfs_tables, clfs_default_q or "clfs_2026q1",
                                   classes2=rep["classes"][str(MIN_COMMON[0])])
    return rep


def garfield_check(h: dict) -> dict:
    a = h["arr"]
    ncol = len(h["col_keys"])
    per_col = [sorted(set(np.round(a["pct"][a["col"] == c], 6).tolist())) for c in range(ncol)]
    gross, mn, mx = [], [], []
    for e in h["row_extra"]:
        g, lo, hi = bp.num(e[0])[0], bp.num(e[1])[0], bp.num(e[2])[0]
        if g == g and g > 0 and lo == lo:
            gross.append(g); mn.append(lo); mx.append(hi)
    gross, mn, mx = np.array(gross), np.array(mn), np.array(mx)
    lowest = min(GARFIELD_PCT) / 100.0
    return {"all_cells_percent_of_billed": bool((a["meth"] == M_P).all()) and len(a["meth"]) > 0,
            "percentages_by_column": per_col,
            "rows_with_gross_and_min": int(len(gross)),
            "min_equals_lowest_percentage_times_gross": int((np.abs(mn - lowest * gross) <= 5.1e-5).sum()),
            "max_equals_gross": int((np.abs(mx - gross) <= 5.1e-5).sum()),
            "max_equals_highest_percentage_times_gross": int((np.abs(mx - max(GARFIELD_PCT) / 100.0 * gross) <= 5.1e-5).sum())}


def synthetic(perturb: bool = False) -> dict:
    """A rank-one table, P = c_a * u_i, with exact floors: the estimator must return nothing above floor."""
    rng = np.random.default_rng(147)
    n, m = 60, 6
    u = np.exp(rng.normal(3.0, 1.0, n))
    c = np.exp(rng.normal(0.0, 0.3, m))
    P = np.outer(c, u)
    if perturb:
        P[2, 17] *= 1.0 + 1e-9
    cols = {a: {"name": "col %d" % a, "payer": "p%d" % a, "members": [a], "rows": np.arange(n, dtype=np.int64),
                "logp": np.log(P[a]), "flog": np.zeros(n), "meth": np.full(n, M_F, dtype=np.int8),
                "pct": np.full(n, -1.0), "printed": np.ones(n, dtype=bool), "price": P[a]} for a in range(m)}
    out = read_pairs({"cols": cols}, floor_mult=1.0, eps=1e-12, cats=["FF"], keep_examples=False)
    s = out["by_category"]["FF"]
    return {"columns": m, "rows": n, "independent_squares": s["independent_squares"], "above_floor": s["above_floor"]}


# ---------------------------------------------------------------- criteria

RIVAL = {
    "rival_premise": "The total price payer m pays hospital j for treating condition d is w_d * p_mj, with the "
                     "weight w_d the same for every payer.",
    "rival_entailment": "Take logs: ln P(m, d) = ln w_d + ln p_mj. The second difference over two payers and two "
                        "items cancels w and p separately, so every square is exactly zero.",
    "rival_shape": "point prediction of zero",
    "cite": "Gowrisankaran, Nevo and Town, 'Mergers When Prices Are Negotiated: Evidence from the Hospital "
            "Industry', NBER Working Paper 18875 (March 2013), 'the base price multiplied by the disease weight'.",
}

MAPPING_B147_4 = {
    "a column pair with rows charged by two methods has a square above the floor, on every knob setting":
        "PASS: the product form is wrong there",
    "such column pairs exist and every square on them is within the floor, on every knob setting":
        "no verdict, grid A: the product form holds there and both accounts read zero",
    "no column pair has two rows charged by the two per-item methods, or the answer moves on a declared knob":
        "no verdict (passed = None)",
}


def _crit(name, kind, verdict, detail, extra=None):
    c = {"name": name, "kind": kind, "detail": detail, "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        c["void"] = True
    if extra:
        c.update(extra)
    return c


def rival_verdict(reports: dict):
    """(verdict, B pairs, A pairs, per-setting answers) from the PF sweep of every hospital."""
    settings = {}
    for rep in reports.values():
        for s in rep["sweep_PF"]:
            k = (s["rule"], s["floor_multiple"])
            t = settings.setdefault(k, [0, 0])
            t[0] += s["column_pairs"]
            t[1] += s["column_pairs_with_a_square_above_floor"]
    main = settings.get(("dollar_first", 1.0), [0, 0])
    if main[0] == 0:
        return None, 0, 0, settings
    answers = {v[1] > 0 for v in settings.values() if v[0] > 0}
    if len(answers) != 1 or any(v[0] == 0 for v in settings.values()):
        return None, main[1], main[0] - main[1], settings
    return answers.pop(), main[1], main[0] - main[1], settings


def build_criteria(reports: dict, garfield: dict, syn: dict, syn_bad: dict, manifest_ids: list,
                   asp_files: dict | None = None, clfs: dict | None = None, clfs_files: dict | None = None) -> list:
    crits = []
    others = {k: v for k, v in reports.items() if k != "garfield"}

    # B147-0
    ok0 = syn["independent_squares"] > 0 and syn["above_floor"] == 0 and syn_bad["above_floor"] > 0
    crits.append(_crit("B147-0", "instrument", ok0,
                       "A planted table P = c_a * u_i (%d columns, %d rows) gives %d squares counted pair by pair, %d above an "
                       "exact floor; with one cell multiplied by 1 + 1e-9 the estimator reports %d."
                       % (syn["columns"], syn["rows"], syn["independent_squares"], syn["above_floor"], syn_bad["above_floor"])))

    # B147-1
    g = reports.get("garfield")
    if g is None or garfield is None:
        crits.append(_crit("B147-1", "known_answer", None, "The calibration file was not read."))
    else:
        pcts = garfield["percentages_by_column"]
        one_each = all(len(p) == 1 for p in pcts) and [p[0] for p in pcts] == GARFIELD_PCT
        pooled = g["by_category"]["per_item"]
        squares_zero = pooled["column_pairs"] == 10 and pooled["above_floor"] == 0 and \
            g["by_category"]["PP"]["independent_squares"] == pooled["independent_squares"]
        min_ok = garfield["rows_with_gross_and_min"] > 0 and \
            garfield["min_equals_lowest_percentage_times_gross"] == garfield["rows_with_gross_and_min"]
        ok1 = garfield["all_cells_percent_of_billed"] and one_each and squares_zero and min_ok
        crits.append(_crit("B147-1", "known_answer", ok1,
                           "Garfield County Health Center: every cell is a percentage of billed charges; percentages by "
                           "column %s (expected %s); %d column pairs, %d squares counted pair by pair, %d above the floor; the "
                           "file's own minimum column equals the lowest percentage times gross on %d of %d rows. Printed "
                           "and not judged: its maximum column equals gross on %d rows and the highest percentage times "
                           "gross on %d."
                           % (pcts, GARFIELD_PCT, pooled["column_pairs"], pooled["independent_squares"], pooled["above_floor"],
                              garfield["min_equals_lowest_percentage_times_gross"], garfield["rows_with_gross_and_min"],
                              garfield["max_equals_gross"], garfield["max_equals_highest_percentage_times_gross"])))

    # B147-2
    pf_cells = {k: v["by_category"]["PF"]["row_and_column_pair_cells"] for k, v in reports.items()}
    pf_pairs = {k: v["by_category"]["PF"]["column_pairs"] for k, v in reports.items()}
    same = {k: sum(v["by_category"][c]["above_floor"] for c in ("PP", "FF", "CC", "DD")) for k, v in reports.items()}
    ok2 = sum(pf_pairs[k] for k in others) > 0
    crits.append(_crit("B147-2", "premise", ok2,
                       "Cells that qualify (one row, two columns, both priced, both charged per item, one a percentage of "
                       "billed charges and the other a fee schedule), by file: %s. Column pairs with at least two such rows: "
                       "%s. Rows on same-method column pairs that stand off that pair's constant: %s. Thinnest three "
                       "column pairs by file: %s."
                       % (pf_cells, pf_pairs, same,
                          {k: [t["rows"] for t in v.get("thinnest_PF_column_pairs", [])] for k, v in reports.items()})))

    # B147-3
    ok3 = len(reports) > 0 and all(v["partition_covers"] and v["k"][str(MIN_COMMON[0])] >= 1 for v in reports.values())
    crits.append(_crit("B147-3", "own_reading", ok3,
                       "Number of connected classes k per file (columns joined through chains of column pairs whose ratio "
                       "is one constant on every per-item row they share; rows required to share 2 / 10 / 50; and at 99 in "
                       "100 rows): %s. Columns after merging plans of one payer that print identical cells: %s. The member "
                       "lists and each class's method labels are in the record. k counts connected classes and is not the "
                       "fewest common price bases: two columns of one class can still differ on the rows those two share "
                       "(column pairs inside one class with a square above the floor: %s), and two columns sharing fewer "
                       "rows than required stay in separate classes even where one base fits both. Whether one base fits "
                       "a class takes a joint check over all its columns, which this script does not run."
                       % ({k: "%s / %s / %s; %s" % (v["k"]["2"], v["k"]["10"], v["k"]["50"], v["k_at_99_percent_of_rows"])
                           for k, v in reports.items()},
                          {k: v["columns_after_merging_identical_plans"] for k, v in reports.items()},
                          {k: v["column_pairs_inside_one_class_with_a_square_above_floor"] for k, v in reports.items()})))

    # B147-4
    verdict, nb, na, settings = rival_verdict(others)
    extra = dict(RIVAL)
    extra["mapping"] = MAPPING_B147_4
    extra["knob_settings"] = [{"rule": k[0], "floor_multiple": k[1], "column_pairs": v[0],
                               "column_pairs_with_a_square_above_floor": v[1]} for k, v in sorted(settings.items())]
    if verdict is None:
        extra["grid"] = "unread"
        extra["grid_note"] = "No column pair with two rows charged by the two per-item methods, or the answer moved on a knob."
    elif na and nb:
        extra["grid"] = "mixed"
        extra["grid_split"] = {"A": na, "B": nb}
    else:
        extra["grid"] = "B" if nb else "A"
    tot = {c: sum(v["by_category"]["PF"][c] for v in others.values()) for c in ("independent_squares", "above_floor")}
    extra["rival_holds_share"] = sig(1 - tot["above_floor"] / tot["independent_squares"]) if tot["independent_squares"] else None

    def holds(keys):
        s = sum(others[k]["by_category"]["PF"]["independent_squares"] for k in keys)
        return sig(1 - sum(others[k]["by_category"]["PF"]["above_floor"] for k in keys) / s) if s else None

    extra["rival_holds_share_by_file"] = {k: holds([k]) for k in sorted(others)
                                          if others[k]["by_category"]["PF"]["independent_squares"]}
    entity_files = [k for k in others if k in bp.SAME_ENTITY]
    if len(entity_files) > 1:
        # one legal entity, two files that nearly repeat each other: the pooled share counts it twice
        extra["rival_holds_share_one_file_per_entity"] = {
            "keeping " + keep: holds([k for k in others if k not in bp.SAME_ENTITY or k == keep]) for keep in sorted(entity_files)}
        extra["column_pairs_above_floor_one_file_per_entity"] = {
            "keeping " + keep: sum(others[k]["by_category"]["PF"]["column_pairs_with_a_square_above_floor"]
                                   for k in others if k not in bp.SAME_ENTITY or k == keep) for keep in sorted(entity_files)}
        extra["grid_note"] = ("Column pairs and squares are counted file by file; %s are two files of one legal entity "
                              "whose cells nearly repeat each other, so the pooled counts carry that entity twice. The "
                              "counts with one of its files kept are in rival_holds_share_one_file_per_entity and "
                              "column_pairs_above_floor_one_file_per_entity." % " and ".join(sorted(entity_files)))
    if verdict is False:
        # every such pair reads zero: the two columns are one base after all, which is the cell where both
        # accounts say zero. That is grid A, and grid A is not written as a loss, so no verdict is carried.
        extra["grid"] = "A"
        extra.pop("grid_split", None)
        extra["grid_note"] = "The product form holds on every such pair; both accounts read zero there."
        verdict_out = None
    else:
        verdict_out = verdict
    crits.append(_crit("B147-4", "rival", verdict_out,
                       "On column pairs whose shared rows are charged by a percentage of billed charges in one column and a "
                       "fee schedule in the other: %d column pairs across %d files, %d with a square above the floor and %d "
                       "with every square within it; %d squares counted pair by pair (n - 1 on each column pair, summed "
                       "over pairs; pairs that share a column are not independent of one another, and the bound on "
                       "independent squares of each whole file is in d22), %d above the floor. By file (pairs, pairs "
                       "above, squares, above, median multiple of the floor, median absolute log gap): %s. The count of "
                       "pairs above the floor on each knob setting is in knob_settings; the verdict is read only when "
                       "every setting gives the same answer. A criterion of this kind passes when the rival's point "
                       "prediction fails."
                       % (na + nb, sum(1 for v in others.values() if v["by_category"]["PF"]["column_pairs"]), nb, na,
                          tot["independent_squares"], tot["above_floor"],
                          {k: (v["by_category"]["PF"]["column_pairs"], v["by_category"]["PF"]["column_pairs_with_a_square_above_floor"],
                               v["by_category"]["PF"]["independent_squares"], v["by_category"]["PF"]["above_floor"],
                               v["by_category"]["PF"]["median_multiple_of_floor"], v["by_category"]["PF"]["median_abs_log_gap"])
                           for k, v in others.items()}), extra))

    # B147-5
    nz = {k: v["named_zero"] for k, v in reports.items()}
    real = sum(v["independent_squares"] for v in nz.values())
    above = sum(v["above_floor"] for v in nz.values())
    unnamed_zero = {k: {c: v["by_category"][c]["column_pairs_all_within_floor"] for c in ("PF", "FF")} for k, v in reports.items()}
    label_only = {k: (v["by_category"]["PP"]["independent_squares"], v["by_category"]["PP"]["above_floor"]) for k, v in reports.items()}
    verdict5 = None if real == 0 else above == 0
    crits.append(_crit("B147-5", "known_answer", verdict5,
                       "Zero domain named from the method and percentage columns alone (both cells a percentage of billed "
                       "charges, same printed pair of percentages), read on cells that also print the dollar amount: %d "
                       "squares counted pair by pair, %d above the floor. By file: %s. Squares in the same named domain whose price "
                       "is itself the percentage times gross are zero by construction and are counted apart "
                       "(vacuous_independent_squares). Named by the method label alone (both a percentage, whatever the "
                       "percentages), squares counted pair by pair and how many are above the floor: %s. Not named and zero: column "
                       "pairs with every square within the floor although one column is a fee schedule (PF) or both are (FF): %s."
                       % (real, above, nz, label_only, unnamed_zero)))

    # B147-6
    same_dollar = {k: {c: {x: v["by_category"][c][x] for x in ("column_pairs", "column_pairs_all_within_floor",
                                                                 "independent_squares", "above_floor", "share_above_floor",
                                                                 "median_abs_log_gap")}
                       for c in ("FF", "CC", "DD")} for k, v in others.items()}
    n6 = sum(v[c]["independent_squares"] for v in same_dollar.values() for c in v)
    crits.append(_crit("B147-6", "own_reading", n6 > 0,
                       "Squares where both columns print a dollar price by the same method (fee schedule against fee "
                       "schedule, case rate against case rate, per diem against per diem), by file: %s. The zero cell here "
                       "means two columns are one schedule at two multiples. The framework names no direction on these "
                       "pairs, so no rival is attached." % same_dollar))

    # B147-7
    covered = sorted(reports)
    ok7 = covered == sorted(manifest_ids) and all(v["cells_read"] > 0 for v in reports.values())
    crits.append(_crit("B147-7", "bookkeeping", ok7,
                       "Coverage: files read %s against files in the manifest %s. For each file the record carries the "
                       "template version, the date, lines, rows, columns, cells by method, cells left out and why (%s), rows "
                       "where the two cells are charged in different units (%s), columns that print whole dollars only "
                       "(%s), and cells that print both a dollar amount and a percentage with how many agree to the cent (%s)."
                       % (covered, sorted(manifest_ids), {k: v["left_out"] for k, v in reports.items()},
                          {k: v["unit_mismatch_rows"] for k, v in reports.items()},
                          {k: len(v["whole_dollar_columns"]) for k, v in reports.items()},
                          {k: (v["dollar_and_percentage_both_printed"], v["of_which_dollar_equals_percentage_times_gross_to_the_cent"])
                           for k, v in reports.items()})))
    if asp_files is not None:
        crits[-1]["detail"] += (" Reference tables read beside the hospital files (kind reference, not in the hospital "
                                "list): %s." % asp_files)

    # B147-8
    crits.append(b147_8_criterion(reports, clfs))

    # B147-9
    crits.append(b147_9_criterion(reports, clfs_files))
    return crits


def b147_8_criterion(reports: dict, clfs: dict | None = None) -> dict:
    read = {k: v["asp"] for k, v in reports.items() if v.get("asp") and v["asp"]["state"] == "read"}
    extra = {"mapping": MAPPING_B147_8, "clfs_half": clfs or clfs_state()}
    if not read:
        return _crit("B147-8", "own_reading", None,
                     "Void: no payment limit file of a default quarter was read, so no column could be set against it. "
                     "The laboratory fee schedule half: %s." % extra["clfs_half"]["state"], extra)
    counts = {k: v["counts"] for k, v in read.items()}
    placed = sum(v["follows"] + v["does_not_follow"] for v in counts.values())
    covers = all(v["partition_covers"] for v in read.values())
    follows = {k: [(e["column"], e["default_quarter"]["constant_c"], e["default_quarter"]["shared_drug_rows"],
                    e["class_at_2_rows"]) for e in v["cells"]["follows"]] for k, v in read.items()}
    moved = {k: [(e["column"], e["quarters_followed"]) for e in v["cells"]["moved_on_quarter_knob"]]
             for k, v in read.items() if v["cells"]["moved_on_quarter_knob"]}
    void = sorted(k for k, v in reports.items() if v.get("asp") and v["asp"]["state"] != "read")
    unresolved = {k: [(e["column"], e["default_quarter"]["constant_c"], e["default_quarter"]["within_floor"],
                       e["default_quarter"]["shared_drug_rows"]) for e in v["cells"].get("unresolved_reference_row", [])]
                  for k, v in read.items() if v["cells"].get("unresolved_reference_row")}
    travels = {k: v.get("rows_the_deviation_travels_with") for k, v in read.items() if v.get("rows_the_deviation_travels_with")}
    revisions = {k: v.get("revision_of_the_default_quarter_file") for k, v in read.items()}
    detail = ("Each hospital column set against the Medicare Part B drug payment limit as a pseudo-column on rows "
              "carrying exactly one HCPCS or CPT code that the limit file lists, cells charged per item. The limit "
              "files on disk are the revisions current when they were fetched; the revision date CMS put in each "
              "default-quarter file's name, by hospital: %s. Columns most of whose shared drug rows sit on one constant "
              "times the limit, and every row off it a row on which a column with a different constant is off by the "
              "same ratio, are a third cell with no verdict, because the deviation sits on the row (the limit printed "
              "for that code, or the unit or base the hospital uses for it) and not on the column's contract: as (column, c, rows within the floor, shared drug rows) %s; those "
              "rows as (code, ratio to c times the limit, rows, most columns off by that ratio on one row) %s. Columns by "
              "cell (follows, does not follow, fewer than two shared drug rows, moved on the quarter knob, the third "
              "cell): " % (revisions, unresolved, travels))
    detail += ("%s. "
              "Columns that follow, as (column, constant c, shared drug rows, class index in B147-3 at two rows): %s. "
              "Columns listed because they follow another quarter's limit and not the default quarter's: %s. "
              "Printed and not judged, columns whose best quarter puts at least 99 in 100 of at least ten shared drug "
              "rows on one constant, as (column, quarter, c, share, rows): %s. "
              "Drug rows matched in the default quarter: %s. Squares between a following column and the "
              "pseudo-column are zero by the choice of the cell and are only counted: %s. Hospitals not read "
              "(no default-quarter file): %s. Laboratory fee schedule half: %s. The framework names no direction "
              "here, so no rival is attached."
              % (counts, follows, moved,
                 {k: v["at_99_percent_of_rows_best_quarter"] for k, v in read.items() if v["at_99_percent_of_rows_best_quarter"]},
                 {k: v["drug_rows_by_quarter"][v["default_quarter"]] for k, v in read.items()},
                 {k: v["squares_zero_by_construction_on_following_columns"] for k, v in read.items()},
                 void, extra["clfs_half"]["state"]))
    return _crit("B147-8", "own_reading", placed > 0 and covers, detail, extra)


def b147_9_criterion(reports: dict, clfs_files: dict | None = None) -> dict:
    """Columns against the Clinical Laboratory Fee Schedule: the B147-8 cells on laboratory rows."""
    read = {k: v["clfs"] for k, v in reports.items() if v.get("clfs") and v["clfs"]["state"] == "read"}
    extra = {"mapping": MAPPING_B147_9}
    if clfs_files is not None:
        extra["fee_schedule_files"] = clfs_files
    if not read:
        return _crit("B147-9", "own_reading", None,
                     "Void: no laboratory fee schedule file of a default quarter was read, so no column could be set "
                     "against it.", extra)
    counts = {k: v["counts"] for k, v in read.items()}
    placed = sum(v["follows"] + v["does_not_follow"] for v in counts.values())
    covers = all(v["partition_covers"] for v in read.values())
    follows = {k: [(e["column"], e["default_quarter"]["constant_c"], e["default_quarter"]["shared_drug_rows"],
                    e["class_at_2_rows"]) for e in v["cells"]["follows"]] for k, v in read.items()}
    moved = {k: [(e["column"], e["quarters_followed"]) for e in v["cells"]["moved_on_quarter_knob"]]
             for k, v in read.items() if v["cells"]["moved_on_quarter_knob"]}
    void = sorted(k for k, v in reports.items() if v.get("clfs") and v["clfs"]["state"] != "read")
    unresolved = {k: [(e["column"], e["default_quarter"]["constant_c"], e["default_quarter"]["within_floor"],
                       e["default_quarter"]["shared_drug_rows"]) for e in v["cells"].get("unresolved_reference_row", [])]
                  for k, v in read.items() if v["cells"].get("unresolved_reference_row")}
    travels = {k: v.get("rows_the_deviation_travels_with")[:20] for k, v in read.items()
               if v.get("rows_the_deviation_travels_with")}
    detail = ("Each hospital column set against the Medicare Clinical Laboratory Fee Schedule (national rate, rows "
              "with no modifier) as a pseudo-column on rows carrying exactly one HCPCS or CPT code that the fee "
              "schedule lists, cells charged per item; floor one cent on the hospital cell plus one cent on the "
              "printed rate. Laboratory rows matched in the default quarter: %s; of which CPT 80000-89999 and other "
              "codes: %s. Columns by cell (follows, does not follow, fewer than two shared laboratory rows, moved on "
              "the quarter knob, the third cell): %s. Columns that follow, as (column, constant c, shared laboratory "
              "rows, class index in B147-3 at two rows): %s. Columns listed because they follow another quarter's "
              "rate and not the default quarter's: %s. Third cell, as (column, c, rows within the floor, shared "
              "rows): %s; the rows the deviation travels with, first twenty by file, as (code, ratio to c times the "
              "rate, rows, most columns off by that ratio on one row): %s. Printed and not judged, columns whose best "
              "quarter puts at least 99 in 100 of at least ten shared laboratory rows on one constant, as (column, "
              "quarter, c, share, rows): %s. Squares between a following column and the pseudo-column are zero by "
              "the choice of the cell and are only counted: %s. Hospitals not read (no default-quarter file): %s. "
              "The framework names no direction here, so no rival is attached."
              % ({k: v["lab_rows_by_quarter"][v["default_quarter"]] for k, v in read.items()},
                 {k: v["lab_rows_by_code_range_default_quarter"] for k, v in read.items()},
                 counts, follows, moved, unresolved, travels,
                 {k: v["at_99_percent_of_rows_best_quarter"] for k, v in read.items() if v["at_99_percent_of_rows_best_quarter"]},
                 {k: v["squares_zero_by_construction_on_following_columns"] for k, v in read.items()}, void))
    return _crit("B147-9", "own_reading", placed > 0 and covers, detail, extra)


# ---------------------------------------------------------------- selftest

def fixture(P, meth, pct=None, gross=None, dollar_printed=True, names=None) -> dict:
    """A hospital dict from a (columns x rows) price table and a table of method codes."""
    m, n = P.shape
    row, col, me, dollar, ddec, pc, pdec, gr, algo = [], [], [], [], [], [], [], [], []
    for a in range(m):
        for i in range(n):
            if not np.isfinite(P[a, i]):
                continue
            row.append(i); col.append(a); me.append(int(meth[a, i]))
            dollar.append(round(float(P[a, i]), 2) if dollar_printed else float("nan"))
            ddec.append(2)
            pc.append(float(pct[a, i]) if pct is not None else float("nan")); pdec.append(0)
            gr.append(float(gross[i]) if gross is not None else float("nan")); algo.append(False)
    arr = {"row": np.array(row, dtype=np.int32), "col": np.array(col, dtype=np.int32), "meth": np.array(me, dtype=np.int8),
           "dollar": np.array(dollar), "ddec": np.array(ddec, dtype=np.int8), "pct": np.array(pc),
           "pdec": np.array(pdec, dtype=np.int8), "gross": np.array(gr), "algo": np.array(algo, dtype=bool)}
    return {"id": "fixture", "arr": arr, "meta": {},
            "row_keys": [[[["CPT", str(i)]], "outpatient", "", "", "", "facility", "item %d" % i] for i in range(n)],
            "col_keys": [(names[a] if names else "payer %d" % a, "plan") for a in range(m)],
            "row_extra": [[str(gross[i]) if gross is not None else None,
                           str(round(0.75 * gross[i], 4)) if gross is not None else None,
                           str(gross[i]) if gross is not None else None, None] for i in range(n)]}


def selftest() -> int:
    fails = []

    def ok(label, cond):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    rng = np.random.default_rng(7)
    n = 80
    gross = np.round(np.exp(rng.normal(5.5, 1.0, n)), 2)
    sched = np.round(np.exp(rng.normal(4.5, 1.0, n)), 2)       # a fee schedule that is not a multiple of gross

    # a Garfield-like file: five percentage columns, no dollar printed
    pct5 = np.array(GARFIELD_PCT)[:, None] * np.ones((5, n))
    gar = fixture(pct5 * gross / 100.0, np.full((5, n), M_P), pct=pct5, gross=gross, dollar_printed=False)
    rep_g = read_hospital(gar)
    chk_g = garfield_check(gar)

    # a two-base file: two percentage columns that print dollars, two fee-schedule columns, one case-rate column
    P = np.vstack([0.80 * gross, 0.60 * gross, 1.10 * sched, 1.45 * sched, 7.0 * sched])
    meth = np.vstack([np.full(n, M_P), np.full(n, M_P), np.full(n, M_F), np.full(n, M_F), np.full(n, M_C)])
    pct = np.vstack([np.full(n, 80.0), np.full(n, 60.0), np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)])
    two = fixture(P, meth, pct=pct, gross=gross)
    rep_t = read_hospital(two)

    syn, syn_bad = synthetic(False), synthetic(True)

    def crit(reports, garfield=chk_g, s=syn, sb=syn_bad, ids=None):
        cs = build_criteria(reports, garfield, s, sb, ids if ids is not None else sorted(reports))
        return {c["name"]: c for c in cs}

    base = crit({"garfield": rep_g, "two": rep_t})
    for name in ("B147-0", "B147-1", "B147-2", "B147-3", "B147-4", "B147-5", "B147-6", "B147-7"):
        ok(name + " passes on the planted files", base[name]["passed"] is True)
    ok("planted two-base file: k = 3 (percentage columns, fee-schedule columns, the case-rate column alone)",
       rep_t["k"]["2"] == 3)
    ok("planted two-base file: 4 PF column pairs, all above the floor; FF and PP pairs all within it",
       rep_t["by_category"]["PF"]["column_pairs"] == 4 and rep_t["by_category"]["PF"]["column_pairs_with_a_square_above_floor"] == 4
       and rep_t["by_category"]["FF"]["above_floor"] == 0 and rep_t["by_category"]["PP"]["above_floor"] == 0)
    ok("planted Garfield-like file: k = 1 and no qualifying cell",
       rep_g["k"]["2"] == 1 and rep_g["by_category"]["PF"]["row_and_column_pair_cells"] == 0)
    ok("a case rate against an item price is counted as a unit mismatch and not read",
       rep_t["unit_mismatch_rows"] == 4 * n)

    # B147-0: the estimator that reports nothing on a perturbed table
    ok("B147-0 fails when the perturbed table reads as clean", crit({"garfield": rep_g, "two": rep_t}, sb=syn)["B147-0"]["passed"] is False)
    ok("B147-0 fails when the clean table reads as dirty", crit({"garfield": rep_g, "two": rep_t}, s=syn_bad)["B147-0"]["passed"] is False)

    # B147-1: one column's percentage changed by a point on half the rows
    pct_bad = pct5.copy()
    pct_bad[2, : n // 2] += 1.0
    gar_bad = fixture(pct_bad * gross / 100.0, np.full((5, n), M_P), pct=pct_bad, gross=gross, dollar_printed=False)
    ok("B147-1 fails when one column's percentage moves by a point on half the rows",
       crit({"garfield": read_hospital(gar_bad), "two": rep_t}, garfield=garfield_check(gar_bad))["B147-1"]["passed"] is False)
    gar_min = copy.deepcopy(gar)
    gar_min["row_extra"][3][1] = str(round(0.80 * gross[3], 4))
    ok("B147-1 fails when one row's minimum is not the lowest percentage times gross",
       crit({"garfield": rep_g, "two": rep_t}, garfield=garfield_check(gar_min))["B147-1"]["passed"] is False)
    ok("B147-1 gives no verdict when the calibration file is absent", crit({"two": rep_t}, garfield=None)["B147-1"]["passed"] is None)

    # B147-2: only the calibration file
    ok("B147-2 fails when the only file is the calibration file", crit({"garfield": rep_g})["B147-2"]["passed"] is False)

    # B147-3: a column missing from the partition
    rep_cut = copy.deepcopy(rep_t)
    rep_cut["classes"]["2"][0]["members"].pop()
    rep_cut["partition_covers"] = sorted(x for cl in rep_cut["classes"]["2"] for x in cl["members"]) == \
        sorted(c["name"] for c in rep_cut["columns"])
    ok("B147-3 fails when a column is missing from the partition",
       crit({"garfield": rep_g, "two": rep_cut})["B147-3"]["passed"] is False)

    # B147-4: a rank-one table carrying both labels; and no PF pair at all
    P1 = np.vstack([0.80 * gross, 0.60 * gross, 1.10 * gross, 1.45 * gross])
    one = fixture(P1, meth[:4], pct=pct[:4], gross=gross)
    rep_one = read_hospital(one)
    c4 = crit({"garfield": rep_g, "one": rep_one})["B147-4"]
    ok("B147-4 does not pass (grid A, no verdict) on a rank-one table that carries both method labels",
       c4["passed"] is None and c4["grid"] == "A")
    c4n = crit({"garfield": rep_g})["B147-4"]
    ok("B147-4 gives no verdict, grid unread, when no column pair mixes the two methods",
       c4n["passed"] is None and c4n["grid"] == "unread" and "grid_split" not in c4n)
    ok("B147-4 on the planted file is grid B with both rival fields", base["B147-4"]["grid"] == "B"
       and base["B147-4"]["rival_premise"] and base["B147-4"]["rival_entailment"])
    # a gap that is above the floor at one multiple and inside it at five: the verdict must not be read
    Pk = np.vstack([0.80 * gross, 1.10 * gross * (1 + 0.03 / np.maximum(gross, 1.0) * (np.arange(n) % 2))])
    knob = fixture(Pk, np.vstack([np.full(n, M_P), np.full(n, M_F)]), pct=np.vstack([np.full(n, 80.0), np.full(n, np.nan)]), gross=gross)
    rep_k = read_hospital(knob)
    moves = len({s["column_pairs_with_a_square_above_floor"] > 0 for s in rep_k["sweep_PF"]}) == 2
    ok("the knob fixture does move between floor multiples", moves)
    ok("B147-4 gives no verdict when the answer moves on a declared knob",
       crit({"garfield": rep_g, "knob": rep_k})["B147-4"]["passed"] is None)

    # B147-5: one percentage column relabelled as a fee schedule
    ok("planted two-base file: the named zero domain has squares and none above the floor",
       rep_t["named_zero"]["independent_squares"] == n - 1 and rep_t["named_zero"]["above_floor"] == 0)
    meth_sw = meth.copy()
    meth_sw[1] = M_F
    rep_sw = read_hospital(fixture(P, meth_sw, pct=pct, gross=gross))
    ok("B147-5 gives no verdict when a relabelled column empties the named domain",
       crit({"garfield": rep_g, "two": rep_sw})["B147-5"]["passed"] is None)
    P_bad = P.copy()
    P_bad[1, ::2] *= 1.07                                     # the printed dollars depart from the printed percentage
    rep_pb = read_hospital(fixture(P_bad, meth, pct=pct, gross=gross))
    ok("B147-5 fails when printed dollars depart from the printed percentage in the named domain",
       crit({"garfield": rep_g, "two": rep_pb})["B147-5"]["passed"] is False)

    # B147-6: nothing to read
    ok("B147-6 fails when no same-method dollar pair exists", crit({"garfield": rep_g})["B147-6"]["passed"] is False)

    # B147-7: one file missing
    ok("B147-7 fails when a file in the manifest was not read",
       crit({"garfield": rep_g, "two": rep_t}, ids=["garfield", "two", "third"])["B147-7"]["passed"] is False)

    # the estimator's parts
    r = np.array([0.0, 0.0, 0.0, 1.0, 1.0])
    c, inside = modal_constant(r, np.full(5, 1e-9))
    ok("modal constant picks the larger class", abs(c) < 1e-6 and inside.tolist() == [True, True, True, False, False])
    c, inside = modal_constant(np.array([0.0, 2.0]), np.array([1.0, 1.0]))
    ok("two intervals that touch at one point share that point", inside.tolist() == [True, True] and abs(c - 1.0) < 1e-12)
    dup = fixture(P, meth, pct=pct, gross=gross)
    for k in dup["arr"]:
        dup["arr"][k] = np.concatenate([dup["arr"][k], dup["arr"][k][:2]])
    dup["arr"]["dollar"][-1] += 5.0
    pd = prepare(dup)
    ok("a cell printed twice with two prices is dropped, one printed twice alike is kept once",
       pd["left_out"]["printed more than once with different prices or methods"] == 2
       and pd["left_out"]["repeat printings that agree (one kept)"] == 1)
    whole = fixture(np.round(P), meth, pct=pct, gross=gross)
    whole["arr"]["ddec"][:] = 0
    ok("a column that never prints cents gets a one-dollar grid", len(prepare(whole)["whole_dollar_columns"]) == 5)
    cent = fixture(P, meth, pct=pct, gross=gross)
    cent["arr"]["dollar"][cent["arr"]["col"] == 2] = np.where(np.arange(n) % 10 == 0, 0.01, cent["arr"]["dollar"][cent["arr"]["col"] == 2])
    pc = prepare(cent)
    ok("a printed price of one cent is counted as a placeholder and not read",
       pc["left_out"]["a price of one cent or less (a placeholder, not a price)"] == n // 10
       and pc["cells_read"] == prepare(two)["cells_read"] - n // 10)
    low = fixture(P, meth, pct=pct, gross=np.where(np.arange(n) % 8 == 0, 1.0, gross))
    pl0, pl1 = prepare(low), prepare(low, gross_cap=1.0)
    ok("rows with a one-dollar gross are left out only in the reading printed beside, and counted",
       pl1["left_out"][GROSS_LOW_LABEL] == 5 * (n // 8) and pl1["cells_read"] == pl0["cells_read"] - 5 * (n // 8)
       and GROSS_LOW_LABEL not in pl0["left_out"])
    ok("the d22 bound is printed per file: (m - 1)(n - 1)", rep_t["d22"]["independent_squares_at_most"] == 4 * (n - 1))
    twin = fixture(np.vstack([P[2], P[2], P[3]]), np.full((3, n), M_F), names=["X", "X", "Y"])
    ok("two plans of one payer printing identical cells are merged into one column",
       prepare(twin)["columns_after_merging_identical_plans"] == 2)

    # the fewest common price bases: bounds that meet, a conflict that forces the bound up, a cycle the joint check catches
    fb_t = rep_t["fewest_common_price_bases"]
    ok("planted two-base file: lower bound 2 = upper bound 2, the case-rate column has no per-item cell",
       fb_t["lower_bound"] == fb_t["upper_bound"] == fb_t["minimum"] == 2
       and fb_t["columns_without_per_item_cells"] == ["payer 4 | plan"] and fb_t["conflicts_differing_from_the_square_reading"] == 0)
    fb_one = rep_one["fewest_common_price_bases"]
    ok("a rank-one table needs one base", fb_one["minimum"] == 1 and fb_one["conflicting_column_pairs"] == 0)
    P1c = P1.copy()
    P1c[3, : n // 2] *= 1.05                                  # one column off the common base on half its rows
    fb_c = read_hospital(fixture(P1c, meth[:4], pct=pct[:4], gross=gross))["fewest_common_price_bases"]
    ok("a column that conflicts with the others forces the lower bound to 2", fb_c["lower_bound"] == 2 and fb_c["minimum"] == 2)
    nan = np.nan
    Pcy = np.array([[10.0, 20.0, nan, nan, 50.0, 60.0],      # a and b agree on rows 0-1, b and c on rows 2-3,
                    [10.0, 20.0, 30.0, 40.0, nan, nan],      # a and c on rows 4-5 at ratio 1/2: every pair has
                    [nan, nan, 30.0, 40.0, 100.0, 120.0]])   # one constant, the three columns have no base together
    cyc = prepare(fixture(Pcy, np.full((3, 6), M_F)))
    fb_y = pbase.fewest_bases(cyc)
    ok("three columns that agree pair by pair and not around the cycle: lower bound 1, upper bound 2, no minimum printed",
       fb_y["conflicting_column_pairs"] == 0 and fb_y["lower_bound"] == 1 and fb_y["upper_bound"] == 2
       and fb_y["minimum"] is None and fb_y["colour_classes_split_by_the_joint_check"] == 1)
    ok("without the joint check the same cycle would read as one base (the check is what catches it)",
       pbase.fewest_bases(cyc, joint_check=False)["upper_bound"] == 1)
    pc_y = pbase.per_item_columns(cyc)
    good_alpha = pbase.alpha_from_pairs([0, 1], pbase.pair_intervals(pc_y, EPS), 0.0)
    bad_alpha = dict(good_alpha)
    bad_alpha[1] += 0.01
    ok("the row check passes a correct factor and fails one moved by 0.01 in log",
       pbase.row_check(pc_y, [0, 1], good_alpha)["passes"] and not pbase.row_check(pc_y, [0, 1], bad_alpha)["passes"])
    ok("a clique search out of budget still returns a valid clique, marked unfinished",
       pbase.maximum_clique([0, 1, 2], {0: {1, 2}, 1: {0, 2}, 2: {0, 1}}, budget=0) == ([], False)
       and pbase.maximum_clique([0, 1, 2], {0: {1, 2}, 1: {0, 2}, 2: {0, 1}})[0] == [0, 1, 2])

    # ---- B147-8: columns against the payment limit
    for label, cond in selftest_b147_8():
        ok(label, cond)
    # ---- B147-9: columns against the laboratory fee schedule
    for label, cond in selftest_b147_9():
        ok(label, cond)
    print("\n%d failed" % len(fails))
    return 1 if fails else 0


def asp_fixture():
    """Six columns on 30 drug rows plus 5 rows that carry no drug code, and two quarters of limits."""
    rng = np.random.default_rng(8)
    nd = 30
    L1 = np.exp(rng.normal(3.0, 1.2, nd))                 # the true limits of the default quarter
    L2 = L1 * np.exp(rng.normal(0.0, 0.05, nd))           # another quarter: every limit moves a little
    t1 = {"header_matches": True, "codes": {"J%04d" % i: (round(float(L1[i]), 3), "1 MG") for i in range(nd)}}
    t2 = {"header_matches": True, "codes": {"J%04d" % i: (round(float(L2[i]), 3), "1 MG") for i in range(nd)}}
    n = nd + 5
    base = np.r_[1.06 * L1, np.exp(rng.normal(5, 1, 5))]
    cols = {
        "asp_plus_6": base.copy(),
        "one_row_1pct_off": base.copy(),
        "one_shared_row": np.r_[1.06 * L1[:1], np.full(nd - 1, np.nan), base[nd:]],
        "one_row_tenfold_unit": base.copy(),
        "fifty_times": np.r_[50.0 * L1, base[nd:]],
        "follows_other_quarter": np.r_[1.06 * L2, base[nd:]],
        # one row off by the same ratio in two columns with different constants: the deviation sits on the row
        "row3_off_at_1_02": np.r_[1.02 * L1, base[nd:]],
        "row3_off_at_1_05": np.r_[1.05 * L1, base[nd:]],
        # the same, plus a row of its own: does not follow
        "row3_and_row20_off": np.r_[1.04 * L1, base[nd:]],
        # one row off by the same ratio in two columns with the same constant: nothing separates row from column
        "row9_off_twin_a": np.r_[1.03 * L1, base[nd:]],
        "row9_off_twin_b": np.r_[1.03 * L1, base[nd:]],
    }
    for k in ("row3_off_at_1_02", "row3_off_at_1_05", "row3_and_row20_off"):
        cols[k][3] *= 0.93
    cols["row3_and_row20_off"][20] *= 1.2
    for k in ("row9_off_twin_a", "row9_off_twin_b"):
        cols[k][9] *= 0.9
    cols["one_row_1pct_off"][7] *= 1.01
    cols["one_row_tenfold_unit"][11] *= 10.0
    names = list(cols)
    Pm = np.vstack([cols[k] for k in names])
    h = fixture(Pm, np.full(Pm.shape, M_F), names=names)
    h["row_keys"] = ([[[["HCPCS", "J%04d" % i], ["NDC", "0000-%04d" % i]], "outpatient", "", "1", "MG", "facility", "drug %d" % i]
                      for i in range(nd)]
                     + [[[["CPT", "9%04d" % i]], "outpatient", "", "", "", "facility", "item %d" % i] for i in range(5)])
    return h, {"q1": t1, "q2": t2}, names


def selftest_b147_8():
    global KNOB_QUARTERS
    h, tables, names = asp_fixture()
    prep = prepare(h)
    saved = KNOB_QUARTERS
    KNOB_QUARTERS = ["q1", "q2"]
    try:
        r = asp_reading(prep, h["row_keys"], tables, "q1")
        cell = {e["column"].split(" | ")[0]: k for k, v in r["cells"].items() for e in v}
        c_of = {e["column"].split(" | ")[0]: e["default_quarter"]["constant_c"] for e in r["cells"]["follows"]}
        out = [
            ("B147-8 seed 1: a column at 1.06 times the limit on 30 rows follows it, c printed 1.06",
             cell.get("asp_plus_6") == "follows" and abs(c_of.get("asp_plus_6", 0) - 1.06) < 1e-3),
            ("B147-8 seed 2: the same column with one row times 1.01 does not follow",
             cell.get("one_row_1pct_off") == "does_not_follow"),
            ("B147-8 seed 3: a column with one shared drug row is not read", cell.get("one_shared_row") == "unread"),
            ("B147-8 seed 4: one row priced for ten units does not follow", cell.get("one_row_tenfold_unit") == "does_not_follow"),
            ("B147-8: a column at 50 times the limit follows (the limit's own printing grid is in the floor)",
             cell.get("fifty_times") == "follows"),
            ("B147-8: a column that follows another quarter's limit is listed, not placed",
             cell.get("follows_other_quarter") == "moved_on_quarter_knob"),
            ("B147-8: rows without a drug code are not read; the partition covers every column",
             r["drug_rows_by_quarter"]["q1"] == 30 and r["partition_covers"]),
        ]
        out += [
            ("B147-8: two columns with different constants off by the same ratio on the same row are the third cell",
             cell.get("row3_off_at_1_02") == "unresolved_reference_row" and cell.get("row3_off_at_1_05") == "unresolved_reference_row"),
            ("B147-8: a column off on that shared row and on a row of its own does not follow",
             cell.get("row3_and_row20_off") == "does_not_follow"),
            ("B147-8: two columns with the same constant off on the same row do not follow (nothing separates the row)",
             cell.get("row9_off_twin_a") == "does_not_follow" and cell.get("row9_off_twin_b") == "does_not_follow"),
            ("B147-8: the shared row is printed with its code and ratio",
             any(x[0] == "J0003" and abs(x[1] - 0.93) < 1e-3 and x[2] == 1 for x in r["rows_the_deviation_travels_with"])),
        ]
        m3 = asp_reading(prep, h["row_keys"], tables, "q1", need_distinct_c=False)
        cell3 = {e["column"].split(" | ")[0]: k for k, v in m3["cells"].items() for e in v}
        out.append(("B147-8 seed 6c: with the different-constant condition dropped the twin columns move to the third "
                    "cell (mutation seen)", cell3.get("row9_off_twin_a") == "unresolved_reference_row"))
        # seed 5: no payment limit file gives a void flag
        rv = asp_reading(prep, h["row_keys"], {}, "q1")
        crit_v = b147_8_criterion({"x": {"asp": rv}}, {"state": "unread"})
        out.append(("B147-8 seed 5: without the limit file the flag carries no verdict", crit_v["passed"] is None))
        crit_ok = b147_8_criterion({"x": {"asp": r}}, {"state": "unread"})
        out.append(("B147-8 passes on the planted file", crit_ok["passed"] is True))
        # a criterion that reads nothing must fail: every column unread
        r_empty = copy.deepcopy(r)
        r_empty["cells"]["unread"] += r_empty["cells"]["follows"] + r_empty["cells"]["does_not_follow"]
        r_empty["cells"]["follows"], r_empty["cells"]["does_not_follow"] = [], []
        r_empty["counts"] = {k: len(v) for k, v in r_empty["cells"].items()}
        out.append(("B147-8 fails when no column lands in either read cell",
                    b147_8_criterion({"x": {"asp": r_empty}}, {"state": "unread"})["passed"] is False))
        r_cut = copy.deepcopy(r)
        r_cut["partition_covers"] = False
        out.append(("B147-8 fails when the cells do not cover every column",
                    b147_8_criterion({"x": {"asp": r_cut}}, {"state": "unread"})["passed"] is False))
        # seed 6: mutations of the rule must be caught by the seeds above
        m1 = asp_reading(prep, h["row_keys"], tables, "q1", share=0.9)
        cell1 = {e["column"].split(" | ")[0]: k for k, v in m1["cells"].items() for e in v}
        out.append(("B147-8 seed 6a: with share written as 0.9 the one-percent row is no longer caught (mutation seen)",
                    cell1.get("one_row_1pct_off") == "follows"))
        m2 = asp_reading(prep, h["row_keys"], tables, "q1", asp_floor=False)
        cell2 = {e["column"].split(" | ")[0]: k for k, v in m2["cells"].items() for e in v}
        out.append(("B147-8 seed 6b: with the limit's floor written as 0 the fifty-times column breaks (mutation seen)",
                    cell2.get("fifty_times") != "follows"))
    finally:
        KNOB_QUARTERS = saved
    return out


def clfs_fixture():
    """Columns on 30 laboratory rows plus 5 rows with no code on the schedule, and two quarters of rates printed to
    the cent; the hospital prices are built from the unrounded rate and printed to the cent."""
    rng = np.random.default_rng(9)
    nl = 30
    R1 = np.exp(rng.normal(3.0, 1.0, nl))
    R2 = R1 * np.exp(rng.normal(0.0, 0.05, nl))
    t1 = {"header_matches": True, "codes": {"8%04d" % i: (round(float(R1[i]), 2), "") for i in range(nl)}}
    t2 = {"header_matches": True, "codes": {"8%04d" % i: (round(float(R2[i]), 2), "") for i in range(nl)}}
    extra = np.exp(rng.normal(5, 1, 5))
    cols = {
        "at_rate": np.r_[1.00 * R1, extra],
        "at_80": np.r_[0.80 * R1, extra],
        "one_row_1pct_off": np.r_[1.00 * R1, extra],
        "one_shared_row": np.r_[R1[:1], np.full(nl - 1, np.nan), extra],
        "forty_times": np.r_[40.0 * R1, extra],
        "follows_other_quarter": np.r_[1.00 * R2, extra],
        "row5_off_at_1_00": np.r_[1.00 * R1, extra],
        "row5_off_at_1_25": np.r_[1.25 * R1, extra],
        "row9_twin_a": np.r_[1.10 * R1, extra],
        "row9_twin_b": np.r_[1.10 * R1, extra],
    }
    for k in ("row9_twin_a", "row9_twin_b"):
        cols[k][9] *= 0.9
    cols["one_row_1pct_off"][7] *= 1.01
    for k in ("row5_off_at_1_00", "row5_off_at_1_25"):
        cols[k][5] *= 0.9
    names = list(cols)
    Pm = np.vstack([cols[k] for k in names])
    h = fixture(Pm, np.full(Pm.shape, M_F), names=names)
    h["row_keys"] = ([[[["CPT", "8%04d" % i]], "outpatient", "", "", "", "facility", "lab %d" % i] for i in range(nl)]
                     + [[[["CPT", "9%04d" % i]], "outpatient", "", "", "", "facility", "item %d" % i] for i in range(5)])
    return h, {"q1": t1, "q2": t2}, names


def selftest_b147_9():
    import io
    import tempfile
    import zipfile
    h, tables, names = clfs_fixture()
    prep = prepare(h)
    r = clfs_reading(prep, h["row_keys"], tables, "q1", knob=["q1", "q2"])
    cell = {e["column"].split(" | ")[0]: k for k, v in r["cells"].items() for e in v}
    c_of = {e["column"].split(" | ")[0]: e["default_quarter"]["constant_c"] for e in r["cells"]["follows"]}
    out = [
        ("B147-9 seed 1: a column at the rate on 30 rows follows it, c printed 1",
         cell.get("at_rate") == "follows" and abs(c_of.get("at_rate", 0) - 1.0) < 1e-3),
        ("B147-9 seed 1b: a column at 80 percent of the rate follows it, c printed 0.8",
         cell.get("at_80") == "follows" and abs(c_of.get("at_80", 0) - 0.8) < 1e-3),
        ("B147-9 seed 2: the same column with one row times 1.01 does not follow",
         cell.get("one_row_1pct_off") == "does_not_follow"),
        ("B147-9 seed 3: a column with one shared laboratory row is not read", cell.get("one_shared_row") == "unread"),
        ("B147-9: a column at 40 times the rate follows (the rate's own cent is in the floor)",
         cell.get("forty_times") == "follows"),
        ("B147-9: a column that follows another quarter's rate is listed, not placed",
         cell.get("follows_other_quarter") == "moved_on_quarter_knob"),
        ("B147-9: two columns with different constants off by the same ratio on one row are the third cell",
         cell.get("row5_off_at_1_00") == "unresolved_reference_row" and cell.get("row5_off_at_1_25") == "unresolved_reference_row"),
        ("B147-9: rows without a code on the schedule are not read; 30 lab rows, all CPT 8xxxx; the partition covers",
         r["lab_rows_by_quarter"]["q1"] == 30 and r["partition_covers"]
         and r["lab_rows_by_code_range_default_quarter"] == {"CPT 80000-89999": 30, "other codes on the fee schedule": 0}),
    ]
    crit_ok = b147_9_criterion({"x": {"clfs": r}})
    out.append(("B147-9 passes on the planted file", crit_ok["passed"] is True))
    rv = clfs_reading(prep, h["row_keys"], {}, "q1")
    out.append(("B147-9 seed 5: without the fee schedule file the flag carries no verdict",
                rv["state"] == "void" and b147_9_criterion({"x": {"clfs": rv}})["passed"] is None))
    out.append(("B147-9 gives no verdict when no hospital carries the laboratory reading",
                b147_9_criterion({"x": {}})["passed"] is None))
    r_empty = copy.deepcopy(r)
    r_empty["cells"]["unread"] += r_empty["cells"]["follows"] + r_empty["cells"]["does_not_follow"]
    r_empty["cells"]["follows"], r_empty["cells"]["does_not_follow"] = [], []
    r_empty["counts"] = {k: len(v) for k, v in r_empty["cells"].items()}
    out.append(("B147-9 fails when no column lands in either read cell",
                b147_9_criterion({"x": {"clfs": r_empty}})["passed"] is False))
    r_cut = copy.deepcopy(r)
    r_cut["partition_covers"] = False
    out.append(("B147-9 fails when the cells do not cover every column",
                b147_9_criterion({"x": {"clfs": r_cut}})["passed"] is False))
    m1 = clfs_reading(prep, h["row_keys"], tables, "q1", share=0.9, knob=["q1", "q2"])
    cell1 = {e["column"].split(" | ")[0]: k for k, v in m1["cells"].items() for e in v}
    out.append(("B147-9 seed 6a: with share written as 0.9 the one-percent row is no longer caught (mutation seen)",
                cell1.get("one_row_1pct_off") == "follows"))
    m2 = clfs_reading(prep, h["row_keys"], tables, "q1", ref_floor=False, knob=["q1", "q2"])
    cell2 = {e["column"].split(" | ")[0]: k for k, v in m2["cells"].items() for e in v}
    out.append(("B147-9 seed 6b: with the rate's floor written as 0 the forty-times column breaks (mutation seen)",
                cell2.get("forty_times") != "follows"))
    m3 = clfs_reading(prep, h["row_keys"], tables, "q1", need_distinct_c=False, knob=["q1", "q2"])
    cell3 = {e["column"].split(" | ")[0]: k for k, v in m3["cells"].items() for e in v}
    out.append(("B147-9: two columns with the same constant off on the same row do not follow",
                cell.get("row9_twin_a") == "does_not_follow" and cell.get("row9_twin_b") == "does_not_follow"))
    out.append(("B147-9 seed 6c: with the different-constant condition dropped the twin columns move to the third "
                "cell (mutation seen)", cell3.get("row9_twin_a") == "unresolved_reference_row"))
    # the loader: header and title compared (D54), rows with a modifier, local pricing and two rates set aside
    text = ("2026 Clinical Diagnostic Laboratory Fee Schedule ,,,,,,\n"
            "YEAR,HCPCS,MOD,EFF_DATE,INDICATOR,RATE,SHORTDESC\n"
            "2026,80047,,20260101,N,00010.50,a\n"
            "2026,80047,QW,20260101,N,00009.00,a\n"
            "2026,81479,,20260101,L,00000.00,b\n"
            "2026,85025,,20260101,N,00007.77,c\n"
            "2026,85025,,20260401,N,00007.90,c\n")
    bad = text.replace("RATE", "AMOUNT")
    got = {}
    with tempfile.TemporaryDirectory() as td:
        for tag, body in (("good", text), ("bad", bad)):
            zp = Path(td) / (tag + ".zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("CLFS.csv", body)
            got[tag] = load_clfs(zp)
    g = got["good"]
    out.append(("B147-9 loader: one code kept at 10.5, the QW row and the local row set aside, the code printed with "
                "two rates dropped",
                g["header_matches"] and g["codes"] == {"80047": (10.5, "")} and g["rows_with_a_modifier"] == 1
                and g["rows_not_national"] == 1 and g["ambiguous_codes"] == 1))
    out.append(("B147-9 loader: a header whose sixth name is not RATE does not read as the fee schedule",
                got["bad"]["header_matches"] is False))
    return out


# ---------------------------------------------------------------- main

def config_block(census: dict, manifest: dict | None = None, asp_tables: dict | None = None,
                 clfs_tables: dict | None = None) -> dict:
    manifest = manifest or {}
    added = {k: {x: manifest[k].get(x) for x in ("url", "bytes", "sha256", "etag", "server_last_modified")}
             for k in sorted(manifest) if k in ("uihc", "uihc_dt") or k in ASP_IDS}
    cfg = {"files": {k: {x: v[x] for x in ("hospital_name", "layout", "version", "last_updated_on", "source",
                                              "source_bytes", "source_sha256")} for k, v in census.items()},
            "files_added_2026_10_14": added,
            "payment_limit": {"default_quarter": DEFAULT_QUARTER, "knob_quarters": KNOB_QUARTERS,
                              "files_read": sorted(asp_tables or {}), "drug_row": "exactly one HCPCS or CPT code on the "
                              "row, and the code in the limit file; cells charged per item", "floor_added": ASP_TICK,
                              "cells": "follows (default quarter); does not follow (no quarter in the knob set); unread "
                                       "(fewer than two shared drug rows); listed (follows another quarter, not the default); "
                                       "third cell, no verdict (most rows on one constant, every row off it shared with a "
                                       "column of a different constant at the same ratio)",
                              "revisions_in_member_names": {q: t.get("revision_in_member_name")
                                                            for q, t in sorted((asp_tables or {}).items())}},
            "row_key": "every (code, type) on the line, setting, modifiers, drug unit and type, billing class, description",
            "column_key": "(payer name, plan name); plans of one payer that print identical cells are one column",
            "price_rule": "printed negotiated dollar; else printed percentage times printed gross on a percentage cell",
            "billing_unit_rule": "percentage of billed charges and fee schedule are per item; case rate per case; per diem "
                                 "per day; other and unprinted are not read",
            "placeholder": "a price of one cent or less is not read",
            "printed_beside_the_reading": "the same reading with every row whose gross charge is one dollar or less "
                                          "left out (rows_with_gross_at_most_one_dollar_left_out); a percentage of a "
                                          "one-dollar gross is a stand-in of the same kind as a one-cent price",
            "squares": "each column pair contributes n - 1 squares on its n shared rows, summed over pairs; pairs that "
                       "share a column are not independent of one another; a whole file of m columns and n rows has at "
                       "most (m - 1)(n - 1) independent squares (d22 in each file's report)",
            "index_of_the_iowa_files": "https://uihc.org/cms-hpt.txt (read 2026-10-14) names both Iowa files as its "
                                       "mrf-url lines; the fetcher asked www.healthcare.uiowa.edu/cms-hpt.txt, which "
                                       "answers 404",
            "floor": "one cent on a printed dollar (one dollar in a column that prints no cents); one cent of gross plus "
                     "one unit of the percentage's last printed decimal on a computed price; plus %g" % EPS,
            "knobs": {"floor_multiples": FLOOR_MULTS, "price_rules": RULES, "min_common_rows": MIN_COMMON},
            "parser_version": bp.PARSER_VERSION}
    if clfs_tables:
        cfg["laboratory_fee_schedule"] = {
            "licence": "AMA CPT end-user licence on cms.gov accepted by hand 2026-10-29 before the files were fetched",
            "files": {k: {x: manifest[k].get(x) for x in ("url", "bytes", "sha256", "server_last_modified")}
                      for k in sorted(manifest) if k in CLFS_IDS},
            "default_quarter": CLFS_DEFAULT_QUARTER, "knob_quarters": CLFS_KNOB,
            "lab_row": "exactly one HCPCS or CPT code on the row, and the code on the fee schedule with no modifier "
                       "and pricing indicator N; cells charged per item",
            "floor_added": CLFS_TICK,
            "cells": "the five cells of B147-8, read against the fee schedule's rate"}
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="results/b147_payer_item_square.json")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--trust-cache", action="store_true",
                    help="read data/cache/b147 without the source files (a copy of the cache on another machine)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    manifest = json.loads((bp.RAW / "b147_manifest.json").read_text(encoding="utf-8"))
    manifest_ids = [k for k, v in manifest.items() if v.get("kind") in ("csv", "zip", "json")]
    asp_tables = load_asp_tables()
    for q, t in asp_tables.items():
        print("payment limit file %s: %s; header %s (expected first four %s); %d codes, %d ambiguous; at most %d decimals"
              % (q, t["effective"], t["header"], ASP_HEADER, len(t["codes"]), t["ambiguous_codes"], t["limit_decimals_max"]))
        print("   its own words: %r / %r" % (t["title"], t["note_1"]))
    clfs_tables = load_clfs_tables()
    for q, t in clfs_tables.items():
        print("laboratory fee schedule %s (%s): title %r; header %s (expected first six %s); %d rows, %d codes kept, "
              "%d ambiguous, %d with a modifier %s, %d not national, %d at zero; indicators %s; at most %d decimals"
              % (q, t["member"], t["title"], t["header"], CLFS_HEADER, t["rows"], len(t["codes"]), t["ambiguous_codes"],
                 t["rows_with_a_modifier"], t["modifiers"], t["rows_not_national"], t["rows_zero_rate"],
                 t["indicators"], t["rate_decimals_max"]))
    reports, census, garfield = {}, {}, None
    sig_rows, sig_cols, campus = {}, {}, {}
    for hid in (a.only or bp.HOSPITALS):
        h = bp.load(hid, trust_cache=a.trust_cache)
        census[hid] = bp.census(h)
        bp.print_census(census[hid])
        reports[hid] = read_hospital(h, asp_tables=asp_tables, default_q=DEFAULT_QUARTER.get(hid), verbose=True,
                                     clfs_tables=clfs_tables if clfs_tables else None,
                                     clfs_default_q=CLFS_DEFAULT_QUARTER.get(hid))
        if hid == "garfield":
            garfield = garfield_check(h)
        if hid in bp.SAME_ENTITY:
            campus[hid] = campus_keys(h, sig_rows, sig_cols)
        del h
        print("   peak memory of this process so far %.2f GB" % ((bp.peak_memory_bytes() or 0) / 1e9), flush=True)
        rep = reports[hid]
        print("   columns %d -> %d after merging identical plans; cells read %d; left out %s"
              % (rep["columns_printed"], rep["columns_after_merging_identical_plans"], rep["cells_read"], rep["left_out"]))
        for cat in CATS:
            s = rep["by_category"][cat]
            print("   %-8s cells %9d  pairs %5d (above %5d, within %5d)  squares %9d  above floor %9d  share %s  median x floor %s  median |log gap| %s"
                  % (cat, s["row_and_column_pair_cells"], s["column_pairs"], s["column_pairs_with_a_square_above_floor"],
                     s["column_pairs_all_within_floor"], s["independent_squares"], s["above_floor"], s["share_above_floor"],
                     s["median_multiple_of_floor"], s["median_abs_log_gap"]))
        print("   named zero domain %s   unit-mismatch rows %d   k %s   k at 99%% of rows %d"
              % (rep["named_zero"], rep["unit_mismatch_rows"], rep["k"], rep["k_at_99_percent_of_rows"]))
        fb = rep["fewest_common_price_bases"]
        print("   fewest common price bases (printed beside B147-3, not judged): k %s, lower bound %d%s, upper bound %d, "
              "minimum %s; conflicting pairs %d, colour classes split %d, cells checked jointly %d, columns without "
              "per-item cells %d, conflicts differing from the square reading %s"
              % (rep["k"]["2"], fb["lower_bound"], "" if fb["lower_bound_search_finished"] else " (search budget ran out)",
                 fb["upper_bound"], fb["minimum"], fb["conflicting_column_pairs"], fb["colour_classes_split_by_the_joint_check"],
                 fb["per_item_cells_checked_jointly"], len(fb["columns_without_per_item_cells"]),
                 fb["conflicts_differing_from_the_square_reading"]))
        for cl in rep["classes"]["10"][:6]:
            print("     class of %2d: %s  %s" % (len(cl["members"]), "; ".join(cl["members"][:4]) + (" ..." if len(cl["members"]) > 4 else ""),
                                               cl["cells_by_method"]))
        for e in rep.get("examples_PF", [])[:1]:
            print("     example: " + json.dumps(e, ensure_ascii=False))
        if rep.get("asp"):
            x = rep["asp"]
            print("   B147-8 %s: %s" % (x["state"], x.get("counts", x.get("why"))))
            for e in (x.get("cells", {}).get("follows", []))[:8]:
                print("     follows the limit: %s  c %s  rows %s" % (e["column"], e["default_quarter"]["constant_c"],
                                                                     e["default_quarter"]["shared_drug_rows"]))
        if rep.get("clfs"):
            x = rep["clfs"]
            print("   B147-9 %s: %s  lab rows %s" % (x["state"], x.get("counts", x.get("why")),
                                                    x.get("lab_rows_by_code_range_default_quarter")))
            for e in (x.get("cells", {}).get("follows", []))[:8]:
                print("     follows the lab fee schedule: %s  c %s  rows %s" % (
                    e["column"], e["default_quarter"]["constant_c"], e["default_quarter"]["shared_drug_rows"]))
        sys.stdout.flush()

    campus_reading = None
    if len(campus) == 2:
        (ka, pa, da), (kb, pb, db) = campus["uihc_dt"], campus["uihc"]
        campus_reading = campus_identity(ka, pa, kb, pb)
        campus_reading.update({"first": "uihc_dt", "second": "uihc", "keys_dropped_two_prices_in_one_file": [da, db],
                               "key": "(payer, plan, every code and code type on the row); cells that print a dollar amount"})
        print("\ntwo campuses of one entity, printed and not judged: %s" % campus_reading)
    asp_files = {q: {"effective": t["effective"], "member": t["member"], "codes": len(t["codes"]),
                     "header_matches": t["header_matches"], "revision_in_member_name": t.get("revision_in_member_name")}
                 for q, t in asp_tables.items()}
    syn, syn_bad = synthetic(False), synthetic(True)
    clfs_files = {q: {"member": t["member"], "title": t["title"], "header": t["header"],
                      "header_matches": t["header_matches"], "rows": t["rows"], "codes": len(t["codes"]),
                      "ambiguous_codes": t["ambiguous_codes"], "rows_with_a_modifier": t["rows_with_a_modifier"],
                      "rows_not_national": t["rows_not_national"], "rows_zero_rate": t["rows_zero_rate"],
                      "rate_decimals_max": t["rate_decimals_max"]} for q, t in clfs_tables.items()}
    crits = build_criteria(reports, garfield, syn, syn_bad, manifest_ids, asp_files=asp_files,
                           clfs=clfs_state(clfs_tables), clfs_files=clfs_files or None)
    print("")
    failed = []
    for c in crits:
        mark = "VOID   " if c["passed"] is None else ("PASS   " if c["passed"] else "FAILED[" + c["kind"] + "]: ")
        if c["passed"] is False:
            failed.append(c["name"])
        print(mark + c["name"] + "  " + c["detail"])
    record = {"stage": "B147", "config": config_block(census, manifest, asp_tables, clfs_tables), "criteria": crits,
              "census": census,
              "report": reports, "garfield_check": garfield, "synthetic": {"clean": syn, "perturbed": syn_bad},
              "not_fetched": [x for x in bf.NOT_FETCHED if not x.get("fetched_as")],
              "fetched_after_the_first_round": [x for x in bf.NOT_FETCHED if x.get("fetched_as")],
              "two_campuses_one_entity": campus_reading,
              "payment_limit_files": {q: {k: t[k] for k in ("effective", "member", "title", "note_1", "header",
                                                            "header_matches", "rows", "ambiguous_codes",
                                                            "limit_decimals_max", "revision_in_member_name")}
                                      for q, t in asp_tables.items()},
              "laboratory_fee_schedule_files": {q: {k: t[k] for k in ("member", "title", "header", "header_matches",
                                                                      "rows", "ambiguous_codes", "rows_with_a_modifier",
                                                                      "modifiers", "rows_not_national", "rows_zero_rate",
                                                                      "indicators", "effective_dates", "rate_decimals_max")}
                                                for q, t in clfs_tables.items()}}
    if not a.only:
        out = REPO / a.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                       encoding="utf-8", newline="\n")
        print("\nwrote " + str(out.relative_to(REPO)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
