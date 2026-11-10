"""B154: the federal milk marketing orders write four class prices on one tank of raw milk,
and only Class I carries a county term.

Object (handler side, dollars per hundredweight at 3.5 percent butterfat):

    P(k, c, t) = B_k(t) + 1[k = I] * d_v(c)      k in {I, II, III, IV}, c the plant's county
    S(I, k; c1, c2) = [P(I,c1) - P(k,c1)] - [P(I,c2) - P(k,c2)] = d_v(c1) - d_v(c2)

The rival is a scalar price field on positions: one price for one milk at one place,
whatever it is used for, so every such square is exactly zero.

Readings, all one pass over files already on disk, no sampling, no repetition:

  B154-0   instrument     the county table, three versions, read row by row
  B154-0b  instrument     all-order overview Class I prices minus each base county's
                          differential give one base price per month
  B154-1   known_answer   the rule text's own zero set (only Class I cites 7 CFR 1000.52)
  B154-2   rival          squares (I, k) x (c1, c2) above the publication floor, per version,
                          on the county table and on the Central order's printed plant lists
  B154-3   own_reading    the Central order's two location dollar lines and their gap
  B154-4   known_answer   printed plant location adjustments against the county table
  B154-4b  known_answer   the plant lists of the ten other orders against the county table and, in the
                          2008-05 to 2025-05 era, the .51(b) county entries of 1005, 1006 and 1007; a
                          city-only row takes its county from the other lists, then from the Census place file
                          (a place across counties at one price under the row's order and month; a unique
                          Census name variant)
  B154-5  bookkeeping    classes named, distinct class prices, the version-to-version map

Run:
    python experiments/b154_milk_orders.py --selftest
    python experiments/b154_milk_orders.py --mutation
    python experiments/b154_milk_orders.py --run
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, r"E:\better economics")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b154"
CACHE = ROOT / "data" / "cache" / "b154"
OUT = ROOT / "results" / "b154_milk_orders.json"
SESSION = "B154_1029e"
STAGE = "B154"

FLOORS = (1, 5, 10, 50)          # cents; 1 is the two-decimal publication grid
JACKSON = "29095"
FIRST_MONTH = (2000, 1)
LAST_MONTH = (2026, 9)

# Versions of the county table in 7 CFR 1000.52.
#   v2000: in force 2000-01-01 to 2025-05-31 (CFR 2000 print; the CFR 2024 print equals it
#          county by county and adds Broomfield, CO, 08014, so it is read off the 2024 print).
#   v2025: 2025-06-01 to 2026-09-17; the CFR 2026 print with the Shannon, SD placeholder
#          removed (91 FR 59047 explains the row as a renaming placeholder).
#   v2026: from 2026-09-18; the current eCFR text, which carries 91 FR 59047 (Morgan, OH
#          3.90 to 3.80; the Shannon row deleted). Month 2026-09 is read under v2026: the two
#          rows the correction changes carry no Central plant, so it reads the same either way.
VERSION_CUTS = (((2025, 5), "v2000"), ((2026, 8), "v2025"), ((9999, 12), "v2026"))
SHANNON = "46113"
MORGAN = "39115"
# The 2000 and 2024 prints give Pierce County, WA the four-digit code "5303". The
# name and state identify it uniquely and the 2026 print carries it as 53053.
FIPS_FIX = {("PIERCE", "WA", "5303"): "53053"}

ORDERS = {1: "Northeast", 5: "Appalachian", 6: "Florida", 7: "Southeast", 30: "Upper Midwest",
          32: "Central", 33: "Mid-East", 51: "California", 124: "Pacific Northwest",
          126: "Southwest", 131: "Arizona", 135: "Western"}
STATE_CODE = {"Massachusetts": "MA", "North Carolina": "NC", "Florida": "FL", "Georgia": "GA",
              "Illinois": "IL", "Missouri": "MO", "Ohio": "OH", "California": "CA",
              "Washington": "WA", "Texas": "TX", "Arizona": "AZ"}
ORDER_FILE = {1: "1001", 5: "1005", 6: "1006", 7: "1007", 30: "1030", 32: "1032", 33: "1033",
              51: "1051", 124: "1124", 126: "1126", 131: "1131"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


# --------------------------------------------------------------------------- helpers

def ym_str(ym):
    return f"{ym[0]:04d}-{ym[1]:02d}"


def month_range(a=FIRST_MONTH, b=LAST_MONTH):
    y, m = a
    while (y, m) <= b:
        yield (y, m)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def version_of(ym):
    for cut, v in VERSION_CUTS:
        if ym <= cut:
            return v
    raise ValueError(ym)


def num(tok):
    """A printed money or count token as Decimal; None if it is not one.

    Parentheses, a leading minus or a trailing minus mean negative; $ and commas drop."""
    t = tok.strip()
    if not t:
        return None
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    if t.endswith("-") and len(t) > 1:
        neg, t = (not neg), t[:-1]
    if t.startswith("-"):
        neg, t = (not neg), t[1:]
    elif t.startswith("+"):
        t = t[1:]
    if t.startswith("("):
        neg, t = True, t.lstrip("(")
    t = t.replace("$", "").replace(",", "").rstrip(")")
    if t.endswith("%"):
        t = t[:-1]
    if not re.fullmatch(r"\d*\.?\d+", t):
        return None
    try:
        v = Decimal(t)
    except InvalidOperation:
        return None
    return -v if neg else v


def cents(v: Decimal) -> int:
    return int((v * 100).to_integral_value())


def money(c: int) -> str:
    s = "-" if c < 0 else ""
    c = abs(c)
    return f"{s}{c // 100}.{c % 100:02d}"


def ratio(x) -> str:
    return "null" if x is None else f"{x:.6f}"


def page_lines(page):
    """Words in reading order on the page as displayed (rotation applied).

    Each line is a list of (x0, x1, text)."""
    import pymupdf
    m = page.rotation_matrix
    ws = []
    for w in page.get_text("words"):
        r = pymupdf.Rect(w[:4]) * m
        ws.append(((r.y0 + r.y1) / 2, r.x0, r.x1, w[4]))
    ws.sort()
    lines, cur, cy = [], [], None
    for y, x0, x1, t in ws:
        if cy is None or abs(y - cy) <= 3.0:
            cur.append((x0, x1, t))
            cy = y if cy is None else cy
        else:
            lines.append(sorted(cur))
            cur, cy = [(x0, x1, t)], y
    if cur:
        lines.append(sorted(cur))
    return lines


def ltext(line):
    return " ".join(t for _, _, t in line)


def merged_nums(line, start=0, pct=True):
    """Numeric tokens of a line from position start, gluing a lone '-' or '$' to the next."""
    out, pend = [], ""
    for x0, x1, t in line[start:]:
        if t in ("-", "$", "-$"):
            pend += t
            continue
        if not pct and t.endswith("%"):
            pend = ""
            continue
        v = num(pend + t)
        pend = ""
        if v is not None:
            out.append((x0, v, t))
    return out


def norm(s):
    s = s.upper().replace("SAINT ", "ST ").replace("’", "").replace("'", "")
    return re.sub(r"[^A-Z0-9]", "", s)


# --------------------------------------------------------------------------- county tables

def rows_xml(path):
    t = path.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<ROW>(.*?)</ROW>", t, re.S):
        out.append([re.sub(r"<[^>]+>", "", e).strip()
                    for e in re.findall(r"<ENT[^>]*>(.*?)</ENT>", m.group(1), re.S)])
    return out


def rows_lii(path):
    t = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"<tr>(.*?)</tr>", t, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", m.group(1), re.S)]
        if cells and cells[0].startswith("County/"):
            continue
        out.append(cells)
    return out


def table_from_rows(rows, label):
    """FIPS -> (name, state, cents). Records every row it could not take as printed."""
    tab, bad, fixes = {}, [], []
    for r in rows:
        if len(r) != 4:
            bad.append({"row": r, "why": "not four cells"})
            continue
        name, st, fips, val = r
        key = (name, st, fips)
        if key in FIPS_FIX:
            fixes.append({"name": name, "state": st, "printed": fips, "read_as": FIPS_FIX[key]})
            fips = FIPS_FIX[key]
        if not re.fullmatch(r"\d{5}", fips):
            bad.append({"row": r, "why": "FIPS not five digits"})
            continue
        if not re.fullmatch(r"\d+\.\d\d", val):
            bad.append({"row": r, "why": "value not on the two-decimal format"})
            continue
        if fips in tab:
            bad.append({"row": r, "why": "FIPS repeated"})
            continue
        tab[fips] = (name, st, cents(Decimal(val)))
    return {"label": label, "rows": len(rows), "tab": tab, "bad": bad, "fixes": fixes}


def load_tables():
    t2000 = table_from_rows(rows_xml(RAW / "rules" / "cfr2000_1000_52.xml"), "CFR 2000 print")
    t2024 = table_from_rows(rows_xml(RAW / "rules" / "cfr2024_1000_52.xml"), "CFR 2024 print")
    t2026 = table_from_rows(rows_xml(RAW / "rules" / "cfr2026_1000_52.xml"), "CFR 2026 print")
    lii = table_from_rows(rows_lii(RAW / "rules" / "lii_1000_52.html"), "eCFR current (LII)")
    return {"cfr2000": t2000, "cfr2024": t2024, "cfr2026": t2026, "lii": lii}


def build_versions(raw):
    v2000 = dict(raw["cfr2024"]["tab"])
    v2025 = {k: v for k, v in raw["cfr2026"]["tab"].items() if k != SHANNON}
    v2026 = dict(raw["lii"]["tab"])
    return {"v2000": v2000, "v2025": v2025, "v2026": v2026}


def check_tables(raw, versions):
    """B154-0. Returns (passed, detail dict)."""
    problems = []
    for k, t in raw.items():
        if t["bad"]:
            problems.append(f"{k}: {len(t['bad'])} rows off the printed format: {t['bad'][:3]}")
        if len(t["tab"]) + len(t["bad"]) != t["rows"]:
            problems.append(f"{k}: rows {t['rows']} != distinct FIPS {len(t['tab'])} + bad {len(t['bad'])}")
    a, b = raw["cfr2000"]["tab"], raw["cfr2024"]["tab"]
    only_b = sorted(set(b) - set(a))
    only_a = sorted(set(a) - set(b))
    diff_ab = sorted(k for k in set(a) & set(b) if a[k][2] != b[k][2])
    if only_a or diff_ab or only_b != ["08014"]:
        problems.append(f"2024 print is not the 2000 print plus Broomfield: only2000={only_a} "
                        f"only2024={only_b} differing={diff_ab[:5]}")
    # v2026 must equal the 2026 print plus the two changes in 91 FR 59047.
    c26 = raw["cfr2026"]["tab"]
    expect = {k: v for k, v in c26.items() if k != SHANNON}
    if MORGAN in expect:
        nm, st, _ = expect[MORGAN]
        expect[MORGAN] = (nm, st, 380)
    got = versions["v2026"]
    miss = sorted(set(expect) ^ set(got))
    neq = sorted(k for k in set(expect) & set(got) if expect[k][2] != got[k][2])
    if miss or neq:
        problems.append(f"current table != 2026 print + correction: symmetric difference {miss[:5]}, "
                        f"value differences {neq[:5]}")
    if SHANNON in c26 and c26[SHANNON][2] != 0:
        problems.append("Shannon, SD in the 2026 print is not the 0.00 placeholder")
    detail = {}
    for v, tab in versions.items():
        vals = Counter(x[2] for x in tab.values())
        grid = 10 if all(c % 10 == 0 for c in vals) else (5 if all(c % 5 == 0 for c in vals) else 1)
        detail[v] = {"rows": len(tab), "distinct_fips": len(set(tab)), "distinct_values": len(vals),
                     "min": money(min(vals)), "max": money(max(vals)), "step_cents": grid,
                     "values": {money(k): vals[k] for k in sorted(vals)}}
    detail["excluded"] = [{"fips": SHANNON, "from": "v2025",
                           "why": "0.00 placeholder left by the 2000 county rename; 91 FR 59047"}]
    detail["read_as"] = raw["cfr2024"]["fixes"] + raw["cfr2000"]["fixes"]
    detail["prints"] = {k: {"rows": t["rows"], "distinct_fips": len(t["tab"]), "off_format": len(t["bad"])}
                        for k, t in raw.items()}
    return (not problems), problems, detail


def version_map(old, new):
    """Every FIPS in the union goes to exactly one of four cells."""
    cells = {"changed": [], "same": [], "added": [], "removed": []}
    for f in sorted(set(old) | set(new)):
        if f in old and f in new:
            cells["changed" if old[f][2] != new[f][2] else "same"].append(f)
        elif f in new:
            cells["added"].append(f)
        else:
            cells["removed"].append(f)
    return cells


def delta_dist(old, new, changed):
    return Counter(new[f][2] - old[f][2] for f in changed)


# --------------------------------------------------------------------------- squares

def square_stats(values, floors=FLOORS):
    """values: location -> cents. Closed form over value counts."""
    cnt = Counter(values.values())
    n = sum(cnt.values())
    pairs = n * (n - 1) // 2
    zero = sum(c * (c - 1) // 2 for c in cnt.values())
    vs = sorted(cnt)
    above = {}
    for f in floors:
        s = 0
        for i, a in enumerate(vs):
            for b in vs[i + 1:]:
                if b - a > f:
                    s += cnt[a] * cnt[b]
        above[f] = s
    out = {"locations": n, "pairs": pairs, "zero": zero, "nonzero": pairs - zero,
           "independent_nonzero": max(len(vs) - 1, 0),
           "above_floor": {str(f): above[f] for f in floors},
           "rival_holds_share": ratio(zero / pairs) if pairs else "null"}
    if n >= 2:
        lo, hi = vs[0], vs[-1]
        lo_loc = sorted(k for k, v in values.items() if v == lo)
        hi_loc = sorted(k for k, v in values.items() if v == hi)
        out["max_square"] = money(hi - lo)
        out["max_square_cents"] = hi - lo
        out["max_square_between"] = [lo_loc[0], hi_loc[0]]
        out["max_square_low_locations"] = lo_loc[:5]
    return out


def layer_cell(stats, framework_nonzero):
    """Map one layer to its cell (11c). Returns (cell, why)."""
    if stats["locations"] < 2:
        return "unread", "fewer than two locations"
    answers = {f: stats["above_floor"][f] > 0 for f in stats["above_floor"]}
    if len(set(answers.values())) > 1:
        return "unread", f"answer flips across the floors {answers}"
    if all(answers.values()):
        return "B", "squares above every floor"
    if framework_nonzero:
        return "C", "every square inside the floor while the county table gives a non-zero one"
    return "unread", "both accounts give zero here; no opposite point prediction (11e sixth clause)"


def rival_verdict(cells):
    """Layer cells -> verdict, as the mapping is written: every layer B is PASS, any layer C is
    FAIL, and anything else (some layer unread) carries no verdict. A layer that is B does not
    stand in for one that is unread (11c)."""
    if any(c == "C" for c in cells.values()):
        return False
    if cells and all(c == "B" for c in cells.values()):
        return True
    return None


def pair_cells(fw, read, floor=FLOORS[0]):
    """Four-cell count over location pairs. fw, read: location -> cents (this framework's value
    and the printed one). The rival predicts every square zero. A: both predict zero and the
    reading is inside the floor; B: framework above the floor, reading above the floor; C:
    framework above the floor, reading inside it; both_unmet: framework zero, reading above."""
    groups = Counter((fw[k], read[k]) for k in read if k in fw)
    keys = sorted(groups)
    out = Counter()
    for i, a in enumerate(keys):
        na = groups[a]
        out["A"] += na * (na - 1) // 2
        for b in keys[i + 1:]:
            nb = groups[b]
            f_on = abs(a[0] - b[0]) > floor
            r_on = abs(a[1] - b[1]) > floor
            cell = ("B" if r_on else "C") if f_on else ("both_unmet" if r_on else "A")
            out[cell] += na * nb
    return {k: v for k, v in sorted(out.items()) if v}


def grid_of(passed, splits):
    """Criterion grid from the per-layer splits of the layers that were read."""
    tot = Counter()
    for s in splits.values():
        tot.update(s)
    tot = {k: v for k, v in sorted(tot.items()) if v}
    if not tot:
        return "unread", None
    if len(tot) == 1:
        return next(iter(tot)), None
    return "mixed", tot


# --------------------------------------------------------------------------- rule text (B154-1)

CLASS_OF_LETTER = {"a": "I", "b": "I", "c": "I", "d": "II", "e": "II", "f": "II", "g": "II",
                   "h": "III", "i": "III", "j": "IV", "k": "IV", "r": "ESL"}


def paragraphs(path):
    t = path.read_text(encoding="utf-8", errors="replace")
    i = t.find('class="section"')
    body = t[i:]
    j = body.find("</div>\n</div>\n</div>")
    ps = re.findall(r"<p[^>]*>(.*?)</p>", body if j < 0 else body[:j + 40], re.S)
    return [" ".join(html.unescape(re.sub(r"<[^>]+>", "", p)).split()) for p in ps]


def letters_of(paras):
    """Top-level paragraph letter -> joined text of it and its sub-paragraphs."""
    out, cur, nxt = {}, None, "a"
    for p in paras:
        m = re.match(r"\(([a-z])\)", p)
        if m and m.group(1) == nxt:
            cur = nxt
            nxt = chr(ord(nxt) + 1)
            out[cur] = p
        elif cur is not None:
            out[cur] += " " + p
    return out


def check_seller_side(order_75, order_61):
    """Seller side of B154-1. Each order's .75 adjusts payments for producer milk by the plant's
    location (the Class I price at the plant less the base point's), naming no class, and its .61
    pools those adjustments over all producer hundredweight. So a producer is paid one location
    term for milk of every class, and the square (k, k') x (c1, c2) on the seller side is zero."""
    if not order_75 or not order_61:
        return None, ["seller-side sections not read"], {}
    problems = []
    for o, t in sorted(order_75.items()):
        if "plant's location" not in t or "producer milk" not in t:
            problems.append(f"order {o} section .75 does not set the producer adjustment by plant location")
        if re.search(r"Class (II|III|IV)\b", t):
            problems.append(f"order {o} section .75 names a class other than I")
    for o, t in sorted(order_61.items()):
        if not re.search(r"\d{4}\.75", t):
            problems.append(f"order {o} section .61 does not pool the .75 adjustments")
    return (not problems), problems, {"orders_75_read": sorted(order_75), "orders_61_read": sorted(order_61)}


def check_rule_text(letters, order_51):
    """B154-1. letters: 1000.50 paragraph letter -> text. order_51: order -> text."""
    if not letters:
        return None, ["1000.50 not read"], {}
    cite = {k: ("1000.52" in v) for k, v in letters.items()}
    citing = sorted(k for k, v in cite.items() if v)
    county_classes = sorted({CLASS_OF_LETTER.get(k, "common") for k in citing})
    problems = []
    if set(citing) != {"b", "c"}:
        problems.append(f"letters citing 1000.52: {citing}, expected exactly b and c")
    if county_classes != ["I"]:
        problems.append(f"classes carrying the county term: {county_classes}")
    for o, txt in sorted(order_51.items()):
        if re.search(r"Class (II|III|IV)\b", txt):
            problems.append(f"order {o} section .51 names a class other than I")
    detail = {"letters_read": "".join(sorted(letters)), "citing_1000_52": citing,
              "county_classes": county_classes,
              "orders_51_read": sorted(order_51)}
    return (not problems), problems, detail


def zero_squares_between(classes_with_county, table, pairs_of=("II", "III", "IV")):
    """Squares the rule makes zero, counted non-zero over all county pairs.

    The three pairs among Classes II, III and IV; and Class I against the Class I ESL price.
    1000.50(r) is an adjustment to the Class I price, not a fifth use class: the ESL price is the
    Class I price plus the ESL term, so (I, I-ESL) x (c1, c2) is zero unless the ESL term itself
    carries the county differential (paragraph (r) citing 1000.52)."""
    res = {}
    st = square_stats({f: v[2] for f, v in table.items()})
    for i, a in enumerate(pairs_of):
        for b in pairs_of[i + 1:]:
            ca, cb = a in classes_with_county, b in classes_with_county
            res[f"{a}-{b}"] = 0 if ca == cb else st["nonzero"]
    res["I-(I-ESL)"] = st["nonzero"] if "ESL" in classes_with_county else 0
    return res


def base_county(text, tabs):
    m = re.search(r"established for ([A-Z][A-Za-z .']+?) County, ([A-Z][a-z]+(?: [A-Z][a-z]+)?)", text)
    if not m:
        return None, None
    name, state = m.group(1), m.group(2)
    st = STATE_CODE.get(state)
    for tab in tabs:
        for f, (nm, s2, _) in tab.items():
            if s2 == st and norm(nm) == norm(name):
                return f, f"{name} County, {state}"
    return None, f"{name} County, {state}"


# --------------------------------------------------------------------------- overview (all orders)

def parse_overview(path, year):
    import pymupdf
    doc = pymupdf.open(path)
    out = {"orders": {}, "footnote": None, "effective_may": False, "errors": []}
    text_all = ""
    for page in doc:
        text_all += page.get_text() + "\n"
        lines = page_lines(page)
        cols = None
        order = None
        for ln in lines:
            t = ltext(ln)
            if t.startswith("January") and "December" in t:
                cols = [((x0 + x1) / 2) for x0, x1, w in ln if w in MONTHS or w.startswith("Average")]
                continue
            m = re.search(r"\(#(\d+)\)", t)
            if m and not t.startswith("Class"):
                order = int(m.group(1))
                out["orders"].setdefault(order, {"diff_header": None, "series": {}})
                continue
            if t.startswith("FMO Totals"):
                order = None
                continue
            if order is None or cols is None:
                continue
            lab = None
            for key, pat in (("class1", r"^Class I Price"), ("sup", r"^(Statistical )?Uniform Price"),
                             ("ppd", r"^Producer Price Differential"), ("receipts", r"^Producer Receipts"),
                             ("u1", r"^Class I Utilization"), ("u2", r"^Class II Utilization"),
                             ("u3", r"^Class III Utilization"), ("u4", r"^Class IV Utilization")):
                if re.match(pat, t):
                    lab = key
                    break
            if lab is None:
                continue
            if lab == "class1":
                md = re.search(r"Diff\.\s*-\s*\$([\d.]+)", t)
                if md:
                    out["orders"][order]["diff_header"] = cents(Decimal(md.group(1)))
            vals = [None] * 13
            first = cols[0] - 40
            for x0, x1, w in ln:
                if x0 < first:
                    continue
                if w == "n/a":
                    continue
                v = num(w)
                if v is None:
                    continue
                c = (x0 + x1) / 2
                j = min(range(len(cols)), key=lambda i: abs(cols[i] - c))
                if vals[j] is not None:
                    out["errors"].append(f"{year} #{order} {lab}: two values in column {j}")
                vals[j] = v
            out["orders"][order]["series"][lab] = vals[:12]
    m = re.findall(r"(Appalachian|Florida|Southeast) \(FMO #(\d+)\): \$\+?(\d+\.\d\d)", text_all)
    if m:
        out["footnote"] = {int(o): cents(Decimal(v)) for _, o, v in m}
    out["effective_may"] = bool(re.search(r"Effective May 1", text_all))
    return out


def load_overviews():
    res = {}
    for y in range(2000, 2027):
        res[y] = parse_overview(RAW / "sums" / f"sum{y}.pdf", y)
    return res


def check_base_prices(ov, versions, bases, jitter=None):
    """B154-0b. Class I(o, t) - d_v(base_o) is one number per month. The .51(b) adjustments of
    orders 1005/1006/1007 are footnoted outside the Class I column and recorded beside it.

    A cell off the common base that prints the same Class I price as another order that month is
    a print slip only if the rest of its row (uniform price, PPD, receipts, utilization) is its
    own. If those columns equal the twin order's too, the parser read the twin's row: FAIL."""
    cells, unread, adj_used = [], [], Counter()
    for y, d in sorted(ov.items()):
        foot = d["footnote"] or {}
        for o, od in sorted(d["orders"].items()):
            s = od["series"].get("class1")
            if not s:
                continue
            for mi, v in enumerate(s):
                if v is None:
                    continue
                ym = (y, mi + 1)
                if ym > LAST_MONTH:
                    continue
                if o not in bases:
                    unread.append(f"{ym_str(ym)} #{o}")
                    continue
                vt = versions[version_of(ym)]
                dv = vt[bases[o]][2]
                # The overview prints the order adjustment of 1005/1006/1007 .51(b) in a footnote
                # and leaves it out of the Class I price column, so the residual takes no adjustment;
                # the footnote is recorded beside it.
                if o in foot and not (d["effective_may"] and mi + 1 < 5):
                    adj_used[(o, foot[o])] += 1
                p = cents(v) + (jitter.get((ym, o), 0) if jitter else 0)
                cells.append((ym, o, p - dv, p, dv, 0))
    by_m = defaultdict(list)
    for c in cells:
        by_m[c[0]].append(c)
    off, bases_m, dup = [], {}, []
    for ym, cs in sorted(by_m.items()):
        mode = Counter(c[2] for c in cs).most_common(1)[0][0]
        bases_m[ym] = mode
        good_prices = {c[3]: c[1] for c in cs if abs(c[2] - mode) <= 1}
        printed_all = {}
        y, mi = ym[0], ym[1] - 1
        for o2, od2 in ov[y]["orders"].items():
            s2 = od2["series"].get("class1") or []
            if mi < len(s2) and s2[mi] is not None:
                printed_all.setdefault(cents(s2[mi]), []).append(o2)
        for c in cs:
            if abs(c[2] - mode) > 1:
                twins = [o2 for o2 in printed_all.get(c[3], []) if o2 != c[1]]
                line = (f"{ym_str(ym)} #{c[1]}: {money(c[3])} - {money(c[4])} = {money(c[2])} "
                        f"against {money(mode)}")
                whole_row = []
                own = ov[y]["orders"][c[1]]["series"]
                for o2 in twins:
                    tw = ov[y]["orders"][o2]["series"]
                    keys = [k for k in own if k != "class1" and k in tw
                            and mi < len(own[k]) and mi < len(tw[k])
                            and own[k][mi] is not None and tw[k][mi] is not None]
                    if keys and all(own[k][mi] == tw[k][mi] for k in keys):
                        whole_row.append(o2)
                if whole_row:
                    off.append(line + f"; the whole row equals order(s) {sorted(whole_row)} that month, "
                                      f"so the row was read from another order")
                elif twins:
                    dup.append((c[1], line + f"; the cell repeats the price printed for order(s) {sorted(twins)}, "
                                             f"the rest of its row is its own"))
                else:
                    off.append(line)
    # A repeated cell is a print slip only while it is rare in its order. An order off in half
    # its months or more has a persistent offset, which is an instrument fault, so it fails.
    n_order = Counter(c[1] for c in cells)
    n_dup = Counter(o for o, _ in dup)
    off += [ln for o, ln in dup if n_dup[o] * 2 >= n_order[o]]
    dup = [ln for o, ln in dup if n_dup[o] * 2 < n_order[o]]
    # each year's header differential against the base county under the version of its last month
    hdr = []
    for y, d in sorted(ov.items()):
        last = None
        for o, od in d["orders"].items():
            s = od["series"].get("class1") or []
            for mi, v in enumerate(s):
                if v is not None:
                    last = max(last or (0, 0), (y, mi + 1))
        if last is None:
            continue
        for o, od in sorted(d["orders"].items()):
            if o in bases and od["diff_header"] is not None:
                want = versions[version_of(min(last, LAST_MONTH))][bases[o]][2]
                if od["diff_header"] != want:
                    hdr.append(f"{y} #{o}: header {money(od['diff_header'])}, table {money(want)}")
    within = sum(1 for c in cells if abs(c[2] - bases_m[c[0]]) <= 1)
    return {"cells": len(cells), "months": len(by_m), "within": within, "off": off, "unread": unread,
            "repeats_other_order": dup,
            "footnote_adjustment_cells": {f"#{o} +{money(a)}": n for (o, a), n in sorted(adj_used.items())},
            "header_mismatch": hdr, "base_by_month": {ym_str(k): money(v) for k, v in sorted(bases_m.items())}}


# --------------------------------------------------------------------------- Central announcements

def parse_pp(path):
    import pymupdf
    doc = pymupdf.open(path)
    r = {"pages": doc.page_count, "image_pages": [], "A": None, "A_src": None, "pool_add_p0": None,
         "pool_add_p2": None, "ppd": None, "sup": None, "pounds": {}, "total_pounds": None,
         "class_prices": {}, "esl": None, "plants": [], "plant_format": None, "jackson_footer": None,
         "classes_named": []}
    for pi, page in enumerate(doc):
        lines = page_lines(page)
        if not lines and page.get_images():
            r["image_pages"].append(pi)
            continue
        hdr = None
        fmt = None
        for li, ln in enumerate(lines):
            t = ltext(ln)
            # handler side
            if "Location Adjustment to Handlers" in t:
                k = [i for i, w in enumerate(ln) if w[2] == "Handlers"][0]
                ns = merged_nums(ln, k + 1)
                if ns:
                    r["A"], r["A_src"] = cents(ns[0][1]), f"p{pi}: Location Adjustment to Handlers"
            elif t.startswith("CLASS I LOCATION ADJUSTMENT"):
                ns = merged_nums(ln, 4)
                if ns:
                    r["A"], r["A_src"] = cents(ns[-1][1]), f"p{pi}: CLASS I LOCATION ADJUSTMENT"
            # producer side
            m = re.match(r"^(Add|Subtract|Less):? (Producer Location Adjustment|Location Adjustment to Producers)", t)
            if m:
                ns = merged_nums(ln, 4)
                if ns:
                    v = cents(ns[-1][1])
                    r["pool_add_p0"] = v if m.group(1) == "Add" else -v
            if t.startswith("LOCATION AND ZONE ADJUSTMENT"):
                ns = merged_nums(ln, 4)
                if ns:
                    r["pool_add_p2"] = cents(ns[-1][1])
            # prices
            if r["ppd"] is None and t.startswith("Producer Price Differential"):
                ns = merged_nums(ln, 3)
                if ns:
                    r["ppd"] = cents(ns[-1][1])
            if r["sup"] is None and t.startswith("Statistical Uniform Price") and ("3.5%" in t):
                ns = [x for x in merged_nums(ln, 3) if x[2] != "3.5%"]
                if ns:
                    r["sup"] = cents(ns[-1][1])
            if t.startswith("Class 1 ESL Adj"):
                ns = merged_nums(ln, 4)
                if ns:
                    r["esl"] = cents(ns[0][1])
            mc = re.match(r"^Class (I|II|III|IV)( Producer Milk)? ", t + " ")
            if mc and pi == 0 and mc.group(1) not in r["classes_named"]:
                r["classes_named"].append(mc.group(1))
                toks = [w for _, _, w in ln[2:]]
                pi_ = [i for i, w in enumerate(toks) if re.fullmatch(r"\d{1,3}([.,]\d{3})+", w)]
                if pi_:
                    w = toks[pi_[0]]
                    r["pounds"][mc.group(1)] = int(re.sub(r"[.,]", "", w))
                    if "." in w:
                        r.setdefault("misprints", []).append(f"Class {mc.group(1)} pounds printed {w}")
                    if mc.group(2) is None and len(toks) > pi_[0] + 1:
                        v = num(toks[pi_[0] + 1])
                        if v is not None:
                            r["class_prices"][mc.group(1)] = cents(v)
            if pi == 0 and (t.startswith("Total Producer Milk") or re.match(r"^100\.00 [\d,]+", t)):
                ns = merged_nums(ln, 0)
                big = [x for x in ns if x[1] > 1000000]
                if big and r["total_pounds"] is None:
                    r["total_pounds"] = int(big[0][1])
            mj = re.search(r"relative to Jackson County, MO, Class I differential of \$(\d+\.\d\d)", t)
            if mj:
                r["jackson_footer"] = cents(Decimal(mj.group(1)))
            # plant tables
            if t.startswith("Plant City State County"):
                hdr, fmt = ln, "county_name"
            elif t.startswith("Plant Name City, State County FIPS"):
                hdr, fmt = ln, "fips"
            elif t.startswith("Class I Differential Location Adjustment"):
                hdr, fmt = ln, "city_only"
            elif hdr is not None:
                row = plant_row(ln, hdr, fmt)
                if row:
                    row["page"] = pi
                    r["plants"].append(row)
                    r["plant_format"] = fmt
    return r


MONEY_TOKEN = re.compile(r"^[-+(]*\$?\d+\.\d\d\)?$")


def plant_row(ln, hdr, fmt):
    ns = [x for x in merged_nums(ln, 0, pct=False) if MONEY_TOKEN.match(x[2])]
    if fmt == "county_name":
        xs = {w: x0 for x0, x1, w in hdr}
        if len(ns) < 2:
            return None
        xd = ns[-2][0]
        state_x, county_x, city_x = xs.get("State"), xs.get("County"), xs.get("City")
        name = [w for x0, x1, w in ln if x0 < city_x - 3]
        city = [w for x0, x1, w in ln if city_x - 3 <= x0 < state_x - 3]
        st = [w for x0, x1, w in ln if state_x - 8 <= x0 < county_x - 5]
        county = [w for x0, x1, w in ln if county_x - 8 <= x0 < xd - 2]
        if len(st) != 1 or not county:
            return None
        return {"name": " ".join(name), "city": " ".join(city), "state": st[0], "county": " ".join(county),
                "diff": cents(ns[-2][1]), "rel": cents(ns[-1][1])}
    if fmt == "fips":
        f = [w for x0, x1, w in ln if re.fullmatch(r"\d{5}", w)]
        if len(f) != 1 or not ns:
            return None
        xs = {w: x0 for x0, x1, w in hdr}
        county_x = xs.get("County")
        fx = [x0 for x0, x1, w in ln if w == f[0]][0]
        county = [w for x0, x1, w in ln if county_x - 8 <= x0 < fx - 2]
        pre = [w for x0, x1, w in ln if x0 < county_x - 8]
        st = pre[-1] if pre and re.fullmatch(r"[A-Z]{2}", pre[-1]) else None
        city_x = xs.get("City,")
        city = None
        if city_x is not None and st:
            city = " ".join(w for x0, x1, w in ln if city_x - 8 <= x0 < county_x - 8 and w != st).rstrip(",") or None
        return {"name": " ".join(pre), "city": city, "state": st, "county": " ".join(county),
                "fips": f[0], "rel": cents(ns[-1][1])}
    if fmt == "city_only":
        if len(ns) < 2:
            return None
        xd = ns[-2][0]
        pre = [w for x0, x1, w in ln if x0 < xd - 2]
        st = pre[-1] if pre and re.fullmatch(r"[A-Z]{2}", pre[-1]) else None
        if st is None:
            return None
        return {"name": " ".join(pre), "city": city_from(pre), "state": st,
                "diff": cents(ns[-2][1]), "rel": cents(ns[-1][1])}
    return None


def city_from(pre):
    """'Name Co, LLC, City Words, ST' -> 'City Words'."""
    toks = pre[:-1]
    ends = [i for i, w in enumerate(toks) if w.endswith(",")]
    if not ends:
        return None
    last = ends[-1]
    prev = ends[-2] if len(ends) > 1 else None
    if prev is None:
        return None
    return " ".join(toks[prev + 1:last + 1]).rstrip(",")


def load_pp():
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / "pp_parsed_v1.json"
    files = sorted((RAW / "central").glob("pp*.pdf"))
    key = hashlib.sha256("|".join(f"{f.name}:{f.stat().st_size}" for f in files).encode()).hexdigest()
    src = Path(__file__).read_bytes()
    key = hashlib.sha256((key + hashlib.sha256(src).hexdigest()).encode()).hexdigest()
    if cf.exists():
        try:
            d = json.loads(cf.read_text(encoding="utf-8"))
            if d.get("key") == key:
                return d["months"]
        except Exception:
            pass
    months = {}
    for f in files:
        yy, mm = int(f.stem[2:4]), int(f.stem[4:6])
        months[ym_str((2000 + yy, mm))] = parse_pp(f)
    cf.write_text(json.dumps({"key": key, "months": months}, sort_keys=True), encoding="utf-8", newline="\n")
    return months


# --------------------------------------------------------------------------- Central arm (B154-3)

def t_from(A, Bp):
    return Bp - A


def synthetic_pool(plants, d0):
    """plants: list of (d, class_I_cwt, other_cwt). Returns (A, Bp) under the record's sign rules."""
    A = sum((d - d0) * c1 for d, c1, c2 in plants)
    Bp = sum((d - d0) * (c1 + c2) for d, c1, c2 in plants)
    return A, Bp


def central_arm(pp):
    rows, cover = [], {}
    for ym in month_range():
        k = ym_str(ym)
        r = pp.get(k)
        if r is None:
            cover[k] = "missing file"
            continue
        if r["pool_add_p0"] is None:
            cover[k] = "parse failure: producer line not read"
            continue
        if r["pool_add_p2"] is not None and r["pool_add_p2"] != r["pool_add_p0"]:
            cover[k] = f"parse failure: producer line page 0 {money(r['pool_add_p0'])} vs page 2 {money(r['pool_add_p2'])}"
            continue
        Bp = -r["pool_add_p0"]
        tot = r["total_pounds"] or sum(r["pounds"].values())
        row = {"month": k, "version": version_of(ym), "Bp": money(Bp),
               "ppd": money(r["ppd"]) if r["ppd"] is not None else None,
               "pool_cwt": f"{tot / 100:.2f}" if tot else None,
               "pounds": {c: r["pounds"].get(c) for c in ("I", "II", "III", "IV")}}
        if r["A"] is None:
            if r["image_pages"]:
                cover[k] = f"producer line only; the page that carries the handler line is a scanned image (pages {r['image_pages']})"
            else:
                cover[k] = "parse failure: handler line not read"
                continue
        else:
            cover[k] = "both lines read"
            T = t_from(r["A"], Bp)
            row.update({"A": money(r["A"]), "A_src": r["A_src"], "T": money(T),
                        "T_over_Bp": ratio(T / Bp) if Bp else None,
                        "T_per_pool_cwt": f"{T / 100 / (tot / 100):.4f}" if tot else None})
        rows.append(row)
    return rows, cover


def coverage_ok(cover):
    expect = [ym_str(ym) for ym in month_range()]
    if sorted(cover) != expect:
        return False, f"coverage covers {len(cover)} months, expected {len(expect)}"
    bad = [k for k, v in cover.items() if v.startswith("parse failure") or v == "missing file"]
    if bad:
        return False, f"parse failures: {bad[:10]}"
    return True, ""


# --------------------------------------------------------------------------- plant lists (B154-4, B154-2 record layer)

def county_index(versions, raw):
    idx = defaultdict(dict)
    for tab in list(versions.values()) + [raw["cfr2000"]["tab"]]:
        for f, (nm, st, _) in tab.items():
            idx[st].setdefault(norm(nm), f)
    return idx


def resolve_plants(pp, versions, raw):
    idx = county_index(versions, raw)
    city_map = defaultdict(set)
    rows = []
    for k in sorted(pp):
        for p in pp[k]["plants"]:
            q = dict(p)
            q["month"] = k
            if "fips" in q:
                f = q["fips"]
            elif "county" in q:
                c = norm(q["county"])
                f = idx.get(q["state"], {}).get(c)
                if f is None and c.endswith("CITY"):
                    f = idx.get(q["state"], {}).get(c[:-4])
            else:
                f = None
            q["resolved_fips"] = f
            if f and q.get("city"):
                city_map[(q["state"], norm(q["city"]))].add(f)
            rows.append(q)
    for q in rows:
        if q["resolved_fips"] is None and q.get("city"):
            s = city_map.get((q["state"], norm(q["city"])))
            if s and len(s) == 1:
                q["resolved_fips"] = next(iter(s))
                q["resolved_by"] = ("city seen with this county in the same listing"
                                    + ("; the printed county name matched no county" if "county" in q else ""))
    return rows


def check_plants(rows, versions, footers):
    ok, bad, unread, changeover, misprint = 0, [], [], [], []
    jackson_of_list = {}
    for q in rows:
        if q.get("resolved_fips") == JACKSON and "diff" in q and q["rel"] == 0:
            jackson_of_list.setdefault(q["month"], q["diff"])
    for q in rows:
        ym = tuple(int(x) for x in q["month"].split("-"))
        v = version_of(ym)
        f = q["resolved_fips"]
        if f is None or f not in versions[v] or JACKSON not in versions[v]:
            unread.append(f"{q['month']} {q['name']} ({q.get('city')}, {q['state']}): county not resolved")
            continue
        tab = versions[v]
        want_rel = tab[f][2] - tab[JACKSON][2]
        good = q["rel"] == want_rel and ("diff" not in q or q["diff"] == tab[f][2])
        if good:
            ok += 1
            continue
        own_j = jackson_of_list.get(q["month"])
        if ("diff" in q and q["rel"] == want_rel and own_j is not None and q["diff"] - q["rel"] != own_j):
            misprint.append(f"{q['month']} {q['name']} ({f}): printed diff {money(q['diff'])} and rel "
                            f"{money(q['rel'])} disagree with the list's own Jackson line {money(own_j)}; "
                            f"the rel agrees with the table")
            continue
        if ym == (2025, 6):
            old = versions["v2000"]
            if f in old and q["rel"] == old[f][2] - old[JACKSON][2]:
                changeover.append(f"{q['month']} {q['name']}: prints the v2000 value")
                continue
        bad.append(f"{q['month']} {q['name']} ({f}): printed rel {money(q['rel'])}"
                   f"{'' if 'diff' not in q else ', diff ' + money(q['diff'])}; table rel {money(want_rel)}, "
                   f"diff {money(tab[f][2])} ({v})")
    # A printed differential that disagrees with its own row is a print slip only while it is
    # alone in its month. Two or more in one month point at the differential column being
    # read wrong on that page, which is an instrument fault.
    per_month = Counter(m.split(" ", 1)[0] for m in misprint)
    bad += [m + " (not alone in its month)" for m in misprint if per_month[m.split(" ", 1)[0]] > 1]
    misprint = [m for m in misprint if per_month[m.split(" ", 1)[0]] == 1]
    for k, fj in sorted(footers.items()):
        v = version_of(tuple(int(x) for x in k.split("-")))
        if fj is not None and fj != versions[v][JACKSON][2]:
            bad.append(f"{k}: footer gives Jackson {money(fj)}, table {money(versions[v][JACKSON][2])}")
    return ok, bad, unread, misprint, changeover


def record_layer(rows, versions):
    """Per version: location -> printed relative adjustment (cents)."""
    out = {}
    for v in versions:
        vals, clash, skipped = defaultdict(Counter), [], 0
        for q in rows:
            ym = tuple(int(x) for x in q["month"].split("-"))
            if version_of(ym) != v:
                continue
            if q["resolved_fips"] is None:
                skipped += 1
                continue
            key = q["resolved_fips"]
            vals[key][q["rel"]] += 1
        loc = {}
        for key, c in vals.items():
            if len(c) > 1:
                clash.append(f"{key}: {dict((money(a), b) for a, b in c.items())}")
            loc[key] = c.most_common(1)[0][0]
        fw = sorted({versions[v][k][2] for k in loc if k in versions[v]})
        out[v] = {"values": loc, "clash": clash, "framework_nonzero": len(fw) > 1, "rows_unresolved": skipped}
    return out


# --------------------------------------------------------------------------- the ten other orders (ruled 2026-10-29)
#
# Each market administrator prints its own announcement. A plant list with a printed differential at
# the plant is read in four layouts, each by the column labels the page prints (rule D54); a page
# without those labels is not read, and its labels are kept in the coverage table.
#
#   state_county_rate  Upper Midwest: "State County Rate" columns, two blocks a page; Rate is the Class I
#                      differential at the plant's county, in dollars
#   fips_loc_adj       California: "Plant Name City/State County FIPS Code Loc. Adj."; Loc. Adj. is relative
#                      to the base county, whose differential the page's footnote prints
#   city_diff_adj      Pacific Northwest: "Class I Differential" and "Location Adjustment from King County, WA";
#                      rows give "Name, City, State" with both numbers
#   city_diff          Appalachian: "POOL DISTRIBUTING PLANTS" with "CLASS 1 DIFFERENTIAL"; rows give
#                      "Name, City, ST" with the differential at the plant

OTHER_ORDERS = {1001: "Northeast", 1005: "Appalachian", 1006: "Florida", 1007: "Southeast", 1030: "Upper Midwest",
                1033: "Mideast", 1051: "California", 1124: "Pacific Northwest", 1126: "Southwest", 1131: "Arizona"}
ORDERS_MANIFEST = RAW / "b154_orders_manifest.json"
STATE_NAME = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
              "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
              "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
              "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
              "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
              "Nevada": "NV", "Hampshire": "NH", "Jersey": "NJ", "Mexico": "NM", "York": "NY",
              "Carolina": None, "Dakota": None, "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
              "Pennsylvania": "PA", "Island": "RI", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
              "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "Wisconsin": "WI", "Wyoming": "WY"}
LOC_LABEL = re.compile(r"(Location Adjustment|Location Adjustments|Location Differential|Class I Differential at "
                       r"Location|Differential at Location|Zone Adjustment|Location and Zone)", re.I)
MONTH_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s*,?\s*(20\d\d)\b", re.I)

# The two location-dollar lines of each order's pool computation, by the words each order prints (D54).
# Each order's .61 adds "an amount equal to the minus location adjustments and subtract[s] an amount equal to
# the plus location adjustments computed pursuant to .75": that is the producer line, printed as the amount
# the pool adds. The handler line differs by order:
#   relative     the Class I value is computed at the base county and this line adjusts it to the plant's
#                location (the Central object A): Northeast, Mideast from 2022 and California print
#                "Less: Location Adjustment to Handlers"; Mideast to 2021 prints "Class I Location
#                Differential" with the Class I pounds before the amount; Appalachian prints "Location
#                Adjustment" under Class I, whose skim price already carries the base differential
#   at_location  "Class I Differential at Location": the Class I skim and butterfat are priced without any
#                differential and this line is the whole differential at the plants' locations (Florida,
#                Southeast, Pacific Northwest, Arizona); it is not A
#   not_given    Southwest's "Add: Class I Differential": the page does not say at which location
# Upper Midwest prints only the producer line.
POOL_LABELS = (
    (r"^Less:? Location Adjustment to Handlers\b", "handler", "relative"),
    (r"^Class I Location Differential\b", "handler", "relative"),
    (r"^Location Adjustment (?!to\b)(?=[-+(]*\$?[\d,]*\d\.\d\d)", "handler", "relative"),
    (r"^Class I Differential at Location\b", "handler", "at_location"),
    (r"^Add:? Class I Differential\b", "handler", "not_given"),
    (r"^Add:? Location Adjustment to Producers\b", "producer", "pool_add"),
    (r"^Net Producer Location Adjustments\b", "producer", "pool_add"),
    (r"^Location Adjustments\b", "producer", "pool_add"),
    (r"^Add:? Location Adjustment -- Producer and Unregulated Supply Plant Milk\b", "producer", "pool_add"),
    (r"^Add:? Location Differential Adjustments 61\(c\)", "producer", "pool_add"),
)


def _state_from_words(words):
    """'..., Portland, Oregon' -> 'OR'; '..., North Carolina' -> 'NC'; a two-letter code as is."""
    if not words:
        return None
    last = words[-1].rstrip(",")
    if re.fullmatch(r"[A-Z]{2}", last):
        return last
    if len(words) >= 2:
        two = words[-2].rstrip(",") + " " + last
        for full, code in (("North Carolina", "NC"), ("South Carolina", "SC"), ("North Dakota", "ND"),
                           ("South Dakota", "SD"), ("New Hampshire", "NH"), ("New Jersey", "NJ"),
                           ("New Mexico", "NM"), ("New York", "NY"), ("Rhode Island", "RI"),
                           ("West Virginia", "WV")):
            if two == full:
                return code
    return STATE_NAME.get(last)


def _city_before_state(words):
    """words end with the state; the city is the comma-delimited piece before it."""
    s = " ".join(words)
    parts = [p.strip() for p in s.split(",")]
    return parts[-2] if len(parts) >= 3 else None


def _rows_state_county_rate(ln, hdr_blocks):
    out = []
    for blk in hdr_blocks:
        ws = [w for w in ln if blk["lo"] <= w[0] < blk["hi"]]
        if not ws:
            continue
        st = [t for x0, x1, t in ws if blk["state"] - 8 <= x0 < blk["county"] - 4 and re.fullmatch(r"[A-Z]{2}", t)]
        county = [t for x0, x1, t in ws if blk["county"] - 8 <= x0 < blk["rate"] - 6]
        rate = [num(t) for x0, x1, t in ws if blk["rate"] - 14 <= x0 and re.fullmatch(r"\$?\d+\.\d\d", t)]
        name = [t for x0, x1, t in ws if x0 < blk["state"] - 8]
        if len(st) == 1 and county and len(rate) == 1:
            out.append({"name": " ".join(name), "state": st[0], "county": " ".join(county).rstrip("*"),
                        "diff": cents(rate[0])})
    return out


def parse_order_pdf(path):
    import pymupdf
    doc = pymupdf.open(path)
    r = {"pages": doc.page_count, "image_pages": [], "plants": [], "formats": [], "base_footer": None,
         "labels": [], "headers": []}
    for pi, page in enumerate(doc):
        lines = page_lines(page)
        if not lines:
            if page.get_images():
                r["image_pages"].append(pi)
            continue
        txt = "\n".join(ltext(ln) for ln in lines[:12])
        mo_ = re.search(r"Federal Order No\.?\s*(\d{1,3})\b", txt)
        porder = int(mo_.group(1)) if mo_ else None
        mm = MONTH_RE.search(txt)
        pmonth = ym_str((int(mm.group(2)), [m.lower() for m in MONTHS].index(mm.group(1).lower()) + 1)) if mm else None
        mode, blocks, fmt = None, None, None
        for ln in lines:
            t = ltext(ln)
            if LOC_LABEL.search(t) and len(t) < 140:
                r["labels"].append(f"p{pi}: {t}")
            for pat, side, meaning in POOL_LABELS:
                if re.match(pat, t):
                    ms = [x for x in merged_nums(ln, 0, pct=False) if re.fullmatch(r"[-+(]*\$?[\d,]*\d\.\d\d\)?-?", x[2])]
                    # the first two-decimal amount after the label: a subtotal may follow on the same line
                    r.setdefault("pool", []).append({"page": pi, "page_month": pmonth, "side": side,
                                                     "meaning": meaning, "label": t[:120], "page_order": porder,
                                                     "cents": cents(ms[0][1]) if ms else None})
                    break
            mf = re.search(r"relative to (.+?),? Class I differential of \$(\d+\.\d\d)", t)
            if mf:
                r["base_footer"] = {"place": mf.group(1), "diff": cents(Decimal(mf.group(2)))}
            toks = [w[2] for w in ln]
            # layout detection, by the labels the page prints
            if toks.count("Rate") >= 1 and "State" in toks and "County" in toks:
                rates = [w[0] for w in ln if w[2] == "Rate"]
                states = [w[0] for w in ln if w[2] == "State"]
                counties = [w[0] for w in ln if w[2] == "County"]
                if len(rates) == len(states) == len(counties):
                    # a block ends where the header's next word after its Rate begins
                    ri = [i for i, w in enumerate(ln) if w[2] == "Rate"]
                    bounds = [ln[i + 1][0] - 2 if i + 1 < len(ln) else 10 ** 6 for i in ri]
                    new = []
                    for k in range(len(rates)):
                        lo = 0 if k == 0 else bounds[k - 1]
                        hi = bounds[k] if k + 1 < len(rates) else 10 ** 6
                        new.append({"state": states[k], "county": counties[k], "rate": rates[k], "lo": lo, "hi": hi})
                    # a one-block header keeps the other block of an earlier two-block header on the page
                    if blocks and len(new) == 1 and len(blocks) == 2:
                        k = min(range(2), key=lambda j: abs(blocks[j]["rate"] - new[0]["rate"]))
                        blocks[k] = {**new[0], "lo": blocks[k]["lo"], "hi": blocks[k]["hi"]}
                    else:
                        blocks = new
                    mode = fmt = "state_county_rate"
                    r["headers"].append(f"p{pi}: {t}")
                    continue
            if ("FIPS" in toks or "Fips" in toks) and "County" in toks and ("City/State" in toks or "State" in toks):
                mode = fmt = "fips_loc_adj"
                r["headers"].append(f"p{pi}: {t}")
                continue
            if re.search(r"Class I Differential\s+Location Adjustment", t):
                mode = fmt = "city_diff_adj"
                r["headers"].append(f"p{pi}: {t}")
                continue
            if re.match(r"^POOL DISTRIBUTING PLANTS", t) and mode == "city_diff_adj":
                continue                      # a section line inside the two-number layout
            if re.match(r"^POOL DISTRIBUTING PLANTS", t):
                mode = fmt = "city_diff"
                r["headers"].append(f"p{pi}: {t}")
                continue
            if mode is None:
                continue
            ns = [x for x in merged_nums(ln, 0, pct=False) if MONEY_TOKEN.match(x[2])]
            rows = []
            if mode == "state_county_rate":
                rows = _rows_state_county_rate(ln, blocks)
            elif mode == "fips_loc_adj":
                f = [w for w in ln if re.fullmatch(r"\d{5}", w[2])]
                if len(f) == 1:
                    after = [x for x in ns if x[0] > f[0][0]]
                    pre = [w[2] for w in ln if w[0] < f[0][0]]
                    st = [w for w in pre if re.fullmatch(r"[A-Z]{2}", w)]
                    if after and st:
                        q = {"name": " ".join(pre), "state": st[-1], "fips": f[0][2]}
                        if len(after) >= 2:          # 2018-2019 layout: differential at the plant, then the adjustment
                            q.update({"diff": cents(after[0][1]), "rel": cents(after[1][1])})
                        else:
                            q["rel"] = cents(after[0][1])
                        rows = [q]
            elif mode == "city_diff_adj":
                if len(ns) == 2:
                    pre = [w[2] for w in ln if w[0] < ns[0][0] - 2]
                    st = _state_from_words(pre)
                    if st:
                        rows = [{"name": " ".join(pre), "city": _city_before_state(pre), "state": st,
                                 "diff": cents(ns[0][1]), "rel": cents(ns[1][1])}]
            elif mode == "city_diff":
                if ns:
                    pre = [w[2] for w in ln if w[0] < ns[0][0] - 2]
                    st = _state_from_words(pre)
                    if st:
                        rows = [{"name": " ".join(pre), "city": _city_before_state(pre), "state": st,
                                 "diff": cents(ns[0][1])}]
                if re.match(r"^COOPERATIVE ASSOCIATIONS", t):
                    mode = None
            for q in rows:
                q.update({"page": pi, "fmt": fmt, "page_month": pmonth})
                r["plants"].append(q)
        if fmt and fmt not in r["formats"]:
            r["formats"].append(fmt)
    return r


def order_files():
    """The files of the ten orders as the manifest lists them, plus the listed URLs the server did not serve."""
    if not ORDERS_MANIFEST.exists():
        return [], []
    m = json.loads(ORDERS_MANIFEST.read_text(encoding="utf-8"))
    files = sorted(((v["order"], v["unit"], v["key"], v["dest"], v["sha256"]) for k, v in m.items()
                    if not k.startswith("_") and not k.endswith("__error")), key=lambda x: (x[0], x[2]))
    errs = sorted((v["order"], v["unit"], v["key"], v.get("http"), v.get("check")) for k, v in m.items()
                  if k.endswith("__error") and k[:-7] not in m)
    return files, errs


def load_orders():
    files, errs = order_files()
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / "orders_parsed_v1.json"
    key = hashlib.sha256("|".join(f"{d}:{h}" for _, _, _, d, h in files).encode()).hexdigest()
    key = hashlib.sha256((key + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()).encode()).hexdigest()
    if cf.exists():
        try:
            d = json.loads(cf.read_text(encoding="utf-8"))
            if d.get("key") == key:
                return d["parsed"], errs
        except Exception:
            pass
    parsed = []
    for order, unit, k, dest, _h in files:
        r = parse_order_pdf(RAW / dest)
        r.update({"order": order, "unit": unit, "key": k, "dest": dest})
        parsed.append(r)
    cf.write_text(json.dumps({"key": key, "parsed": parsed}, sort_keys=True), encoding="utf-8", newline="\n")
    return parsed, errs


def file_month(r):
    """The month a file's rows belong to: the month in its name for a monthly file; for a yearly
    compilation, the month the page itself prints."""
    if r["unit"] == "month":
        k = r["key"][:6]
        return f"{k[:4]}-{k[4:6]}"
    return None


def order_rows(parsed, versions, raw, central_rows, places=None, b51=None, same_price_check=True):
    """Rows of the ten orders with a resolved county where one can be had from the page:
    a printed FIPS; a printed county name matched within the printed state; or, for a row that prints
    only a city, the county another row printed for that city and state (this order first, then any
    of the eleven), when it is unique. Absolute differential at the plant: the printed differential, or
    the printed relative adjustment plus the base differential the same page prints."""
    idx = county_index(versions, raw)
    rows = []
    for r in parsed:
        if r["unit"] == "month" and r["key"].endswith("rev"):
            continue
        for p in r["plants"]:
            q = dict(p)
            q["order"] = r["order"]
            q["month"] = file_month(r) or p.get("page_month")
            q["file"] = r["dest"]
            if q["month"] is None:
                continue
            if "diff" not in q and "rel" in q and r["base_footer"]:
                q["abs"] = q["rel"] + r["base_footer"]["diff"]
                q["abs_from"] = "printed adjustment plus the page's printed base differential"
            elif "diff" in q:
                q["abs"] = q["diff"]
                q["abs_from"] = "printed differential"
            f = None
            if q.get("fips"):
                f = q["fips"]
                q["resolved_by"] = "printed FIPS"
            elif q.get("county"):
                c = norm(q["county"])
                f = idx.get(q["state"], {}).get(c) or (idx.get(q["state"], {}).get(c[:-4]) if c.endswith("CITY") else None)
                if f:
                    q["resolved_by"] = "printed county name"
                elif idx.get(q["state"], {}).get(c + "CITY"):
                    # a Virginia independent city printed without "city" (Winchester)
                    f = idx[q["state"]][c + "CITY"]
                    q["resolved_by"] = "printed county name, read as the independent city of that name"
            q["resolved_fips"] = f
            rows.append(q)
    # revised Northeast files are not read twice: the base file of a revised month is dropped above only
    # when the revision is the one kept; Northeast prints no plant list, so nothing rides on it here.
    seen = defaultdict(lambda: defaultdict(set))
    for q in rows + [dict(c, order=1032) for c in central_rows]:
        if q.get("resolved_fips") and q.get("city"):
            seen[q["order"]][(q["state"], norm(q["city"]))].add(q["resolved_fips"])
    pooled = defaultdict(set)
    for o, d in seen.items():
        for k, s in d.items():
            pooled[k] |= s
    for q in rows:
        if q["resolved_fips"] is None and q.get("city"):
            k = (q["state"], norm(q["city"]))
            s = seen[q["order"]].get(k)
            if s and len(s) == 1:
                q["resolved_fips"], q["resolved_by"] = next(iter(s)), "city seen with this county in this order's lists"
            elif pooled.get(k) and len(pooled[k]) == 1:
                q["resolved_fips"], q["resolved_by"] = next(iter(pooled[k])), "city seen with this county in another order's lists"
    # last, the Census 2020 place-by-county file (ruled 2026-10-29): a place of the printed name in the
    # printed state that lies in one county gives that county; a place in several counties, or no place of
    # that name, leaves the row unresolved and names the candidates
    #
    # Second round (ruled 2026-10-29), for the rows the first left open:
    #  (a) a place in several counties: when every one of those counties carries the same rule value(s) under
    #      the row's order and month (rule_values: 1000.52, and the .51(b) entry where the text applies), the
    #      row takes that value; its location is written as the counties joined by '+' (no one county is
    #      picked), and the table is looked up at the first of them (table_key), which gives the same answer
    #      at any of them. Values not all equal: unresolved, each county's value printed.
    #  (b) no place of the printed name in the printed state: a Census place of that state whose name is the
    #      printed name's words followed by more words ('Boise' -> 'Boise City city'); unique only, then the
    #      one-county rule or (a) applies to it; the Census line is kept. Not unique, or none: unresolved.
    if places:
        lines = getattr(places, "lines", {})
        words = getattr(places, "words", {})
        for q in rows:
            if q["resolved_fips"] is not None or not q.get("city"):
                continue
            key = (q["state"], norm(q["city"]))
            cands = places.get(key, {})
            pkey = key
            if not cands:
                pw = tuple(w for w in (norm(t) for t in q["city"].split()) if w)
                hits = sorted(nm for nm, ws in words.get(q["state"], {}).items()
                              if pw and len(ws) > len(pw) and ws[:len(pw)] == pw)
                if len(hits) == 1:
                    pkey = (q["state"], hits[0])
                    cands = places.get(pkey, {})
                    q["census_variant"] = {"printed": q["city"], "census_place": sorted(set(cands.values())),
                                           "source_lines": [f"line {n}: {ln}" for _f, (n, ln)
                                                            in sorted(lines.get(pkey, {}).items())]}
                elif hits:
                    q["census_variant_candidates"] = {
                        "; ".join(sorted(set(places[(q["state"], nm)].values()))):
                            [f"line {n}: {ln}" for _f, (n, ln) in sorted(lines.get((q["state"], nm), {}).items())]
                        for nm in hits}
                    q["census_candidates"] = {}
                    continue
            via = (" (name variant: printed '" + q["city"] + "')") if pkey != key else ""
            if len(cands) == 1:
                q["resolved_fips"] = next(iter(cands))
                q["resolved_by"] = ("Census 2020 place-by-county file: the place " + cands[q["resolved_fips"]]
                                    + " lies in one county" + via)
            elif len(cands) > 1:
                vals = {f: rule_values(q, f, versions, b51) for f in sorted(cands)}
                same = all(vals.values()) and len(set(vals.values())) == 1
                if same or not same_price_check:
                    fs = sorted(cands)
                    q["resolved_fips"] = "+".join(fs)
                    q["table_fips"] = fs[0]
                    q["same_price_counties"] = {f: ([money(x) for x in vals[f]] if vals[f] else None) for f in fs}
                    q["resolved_by"] = ("Census 2020 place-by-county file: the place " + cands[fs[0]]
                                        + " lies in counties " + ", ".join(fs) + via
                                        + "; spans counties, each at the same price under this order and month")
                else:
                    q["census_candidates"] = dict(sorted(cands.items()))
                    q["census_candidate_prices"] = {f: (" or ".join(money(x) for x in vals[f]) if vals[f]
                                                        else "not in the table") for f in sorted(cands)}
            else:
                q["census_candidates"] = {}
    return rows


def table_key(q):
    """The county a row is looked up at in the county table: its resolved county, or, for a place that spans
    counties all at one price (resolved_fips written 'a+b'), the first of them."""
    return q.get("table_fips") or q.get("resolved_fips")


def rule_values(q, f, versions, b51):
    """The values the rule allows for row q at county f in the row's month (b_candidates), sorted; None when
    the county is not in that month's table."""
    v = version_of(tuple(int(x) for x in q["month"].split("-")))
    if f not in versions[v]:
        return None
    return tuple(sorted(val for val, _h in b_candidates(q, f, versions[v][f][2], b51)))


def load_places(path=None):
    """Census 2020 national place-by-county file: (state, normalized place name) -> {county FIPS: place name
    as printed}. The name is the printed PLACENAME with its trailing legal or statistical descriptor taken
    off ('city', 'town', 'CDP', 'village', a parenthesis, any run of lower-case words): 'Boise City city' is
    'Boise City', 'Winston-Salem city' is 'Winston-Salem'. Nothing else is rewritten."""
    path = path or RAW / "census" / "national_place_by_county2020.txt"
    if not path.exists():
        return None
    out = PlaceIndex()
    lines = path.read_text(encoding="utf-8").splitlines()
    head = lines[0].split("|")
    ix = {h: i for i, h in enumerate(head)}
    for n, ln in enumerate(lines[1:], start=2):
        x = ln.split("|")
        toks = x[ix["PLACENAME"]].split(" ")
        while len(toks) > 1 and (toks[-1].islower() or toks[-1] == "CDP" or toks[-1].startswith("(")
                                 or toks[-1].endswith(")")):
            toks.pop()
        k = (x[ix["STATE"]], norm(" ".join(toks)))
        f = x[ix["STATEFP"]] + x[ix["COUNTYFP"]]
        out.setdefault(k, {})[f] = x[ix["PLACENAME"]]
        out.lines[k][f] = (n, ln)
        out.words[k[0]][k[1]] = tuple(w for w in (norm(t) for t in toks) if w)
    return out


class PlaceIndex(dict):
    """(state, normalized place name) -> {county FIPS: place name as printed}; .lines keeps, per entry, the line
    number in the file and the line as printed; .words, per state, each place name's words (normalized) for
    the name-variant lookup."""
    def __init__(self):
        super().__init__()
        self.lines = defaultdict(dict)
        self.words = defaultdict(dict)


# States in which the Appalachian, Florida and Southeast marketing areas lie. From May 2008 to May 2025
# 1005.51(b), 1006.51(b) and 1007.51(b) added a Class I price adjustment by county on top of 1000.52.
# When that text is not on disk, a printed differential above the table in these states in those months
# is named with no verdict; when it is (ruled 2026-10-29, read below), the row is judged against it.
SE_B_STATES = {"AL", "AR", "FL", "GA", "IN", "IL", "KY", "LA", "MS", "MO", "NC", "SC", "TN", "VA", "WV"}
SE_B_WINDOW = ("2008-05", "2025-05")
SE_ORDERS = (1005, 1006, 1007)
B51_SOURCES = ("cfr2009", "cfr2020", "cfr2024", "ecfr20250201")
B51_ROW = re.compile(r"\b([A-Z]{2}) ([A-Z][A-Z .'\-]*?) (\d{5}) (\d+\.\d\d)\b")


def _xml_text(path):
    t = html.unescape(re.sub(r"<[^>]*>", " ", path.read_text(encoding="utf-8")))
    return re.sub(r"\s+", " ", t).strip()


def read_51b(text):
    """The .51(b) table of one print: {fips: (state, county, cents)}, plus the printed sentence that
    introduces it, its column labels as printed, and the source note."""
    i = text.find("(b) Adjustment to Class I prices.")
    if i < 0:
        return None
    lead = re.match(r"\(b\) Adjustment to Class I prices\.[^:]*:", text[i:])
    body = text[i + (lead.end() if lead else 0):]
    labels = re.match(r"\s*(State \S+ FIPS Class I price adjustment)", body)
    tab = {}
    for m in B51_ROW.finditer(body):
        tab[m.group(3)] = (m.group(1), m.group(2).strip(), cents(Decimal(m.group(4))))
    src = re.search(r"\[(\d+ FR [^\]]+)\]", body)
    a = re.search(r"\(a\) The Class I differential shall be[^(]*?\.\s*The Class I price shall be[^.]*?\.[^.]*?\.", text)
    return {"table": tab, "lead": lead.group(0) if lead else None, "labels": labels.group(1) if labels else None,
            "source_note": src.group(1) if src else None, "a": a.group(0) if a else None}


def load_51b():
    """The three orders' .51(b) as printed in the 2009, 2020 and 2024 CFR and in the eCFR text in force on
    2025-02-01, and the eCFR amendment dates. read is False when any file is missing."""
    out = {"read": True, "orders": {}}
    for o in SE_ORDERS:
        d = {"prints": {}, "amendments": None}
        for s in B51_SOURCES:
            p = RAW / "rules" / f"{s}_{o}_51.xml"
            if not p.exists():
                out["read"] = False
                continue
            txt = _xml_text(p)
            r = read_51b(txt)
            if r is None:
                out["read"] = False
                continue
            r["amendment_link"] = (re.search(r"Link to an amendment published at [^.]+\.[^.]*\.", txt) or [None])[0]
            d["prints"][s] = r
        pv = RAW / "rules" / f"ecfr_versions_{o}_51.json"
        if pv.exists():
            vv = json.loads(pv.read_text(encoding="utf-8"))["content_versions"]
            d["amendments"] = sorted({(v["amendment_date"], v["substantive"]) for v in vv})
        # the prints are compared on (state, FIPS, adjustment); a county name set in two words in one
        # print ('MC DOWELL' in 2009, 'MCDOWELL' later) is recorded, not counted as a difference
        tabs = [{f: (s, c) for f, (s, _n, c) in r["table"].items()} for r in d["prints"].values()]
        d["prints_agree"] = bool(tabs) and all(t == tabs[0] for t in tabs)
        last = d["prints"][B51_SOURCES[-1]]["table"] if B51_SOURCES[-1] in d["prints"] else None
        d["name_spelling_differences"] = sorted(
            f"{s} {f}: {r['table'][f][1]} / {last[f][1]}" for s, r in d["prints"].items() if last
            for f in r["table"] if f in last and r["table"][f][1] != last[f][1])
        d["table"] = last if tabs and d["prints_agree"] else None
        if d["table"] is None:
            out["read"] = False
        out["orders"][o] = d
    return out


def b_candidates(q, f, t, b51):
    """The values the rule allows at a row's plant. 1000.52 alone; in the (b) era, where the .51(b) text is
    read, the list of an Appalachian, Florida or Southeast order prices with its own (b) entry for the
    county (and 1000.52 alone where its table has none); another order's list prices 1000.52 alone, or
    1000.52 plus the (b) entry of the order whose table lists the county (the three tables share no county)."""
    if not (b51 and b51["read"] and SE_B_WINDOW[0] <= q["month"] <= SE_B_WINDOW[1]):
        return [(t, "1000.52")]
    tabs = {o: d["table"] for o, d in b51["orders"].items()}
    if q["order"] in tabs:
        e = tabs[q["order"]].get(f)
        return [(t + e[2], f"1000.52 plus {q['order']}.51(b)")] if e else [(t, "1000.52")]
    return [(t, "1000.52")] + [(t + tab[f][2], f"1000.52 plus {o}.51(b)") for o, tab in sorted(tabs.items()) if f in tab]


def _b51_record(b51, bases, versions, ov, bagree):
    """What the .51(b) text says, as printed, per order and print; and three checks on it: the prints give
    one table; the entry at each order's base county against the adjustment the all-order overview
    footnotes; the rows the earlier run named with no verdict (Calloway, KY; Rockingham, VA) against it."""
    if not b51:
        return None
    out = {"read": b51["read"], "orders": {}}
    foot = Counter()
    for d in ov.values():
        for o, a in (d.get("footnote") or {}).items():
            foot[(o, a)] += 1
    for o, d in b51["orders"].items():
        short = o - 1000
        tab = d["table"] or {}
        bf = bases.get(short) if bases else None
        rec = {"prints_read": sorted(d["prints"]), "prints_give_one_table": d["prints_agree"],
               "name_spelling_differences": d.get("name_spelling_differences"),
               "rows": len(tab), "states": dict(sorted(Counter(s for s, _n, _c in tab.values()).items())),
               "values": {money(k): n for k, n in sorted(Counter(c for _s, _n, c in tab.values()).items())},
               "ecfr_amendment_dates": d["amendments"],
               "verbatim": {s: {"a": r["a"], "b_lead": r["lead"], "column_labels": r["labels"],
                                "source_note": r["source_note"], "amendment_link": r["amendment_link"]}
                            for s, r in sorted(d["prints"].items())},
               "base_county": bf, "base_county_entry": money(tab[bf][2]) if bf in tab else None,
               "overview_footnote": sorted(money(a) for (oo, a), _n in foot.items() if oo == short),
               "counties_in_another_orders_table": sum(1 for o2, d2 in b51["orders"].items() if o2 != o
                                                       for f in tab if f in (d2["table"] or {}))}
        for f in ("21035", "51165"):
            if f in tab:
                rec.setdefault("entries_quoted", {})[f] = " ".join([tab[f][0], tab[f][1], f, money(tab[f][2])])
        out["orders"][str(o)] = rec
    out["rows_named_before_now_judged"] = dict(sorted(Counter(
        s.split(" (")[0].split(" ", 2)[2] + " (" + s.split(" (")[1].split(")")[0] + "), " + s.rsplit(", ", 1)[1]
        for s in bagree if " 1030 " in s).items()))
    return out


def check_order_plants(rows, versions, b51=None):
    """B154-4b. A resolved row agrees when its absolute differential equals the table at its county under
    the version in force that month (and its relative adjustment, where printed, equals the table's
    difference from the base the page prints); in the .51(b) era, when the (b) text is read, the values
    b_candidates allows."""
    ok, bad, unread, changeover, printed_only, b_named = 0, [], [], [], [], []
    b_agree = []
    for q in rows:
        if "abs" not in q:
            unread.append(f"{q['month']} {q['order']} {q['name']}: no differential and no base printed")
            continue
        v = version_of(tuple(int(x) for x in q["month"].split("-")))
        f = q["resolved_fips"]
        ft = table_key(q)
        if f is None or ft not in versions[v]:
            printed_only.append(q)
            continue
        t = versions[v][ft][2]
        cand = b_candidates(q, ft, t, b51)
        hit = [how for val, how in cand if val == q["abs"]]
        if hit:
            ok += 1
            if hit[0] != "1000.52":
                b_agree.append(f"{q['month']} {q['order']} {q['name']} ({f}): printed {money(q['abs'])} = table "
                               f"{money(t)} + {money(q['abs'] - t)}, {hit[0]}")
            continue
        if q["month"] == "2025-06" and ft in versions["v2000"] and q["abs"] == versions["v2000"][ft][2]:
            changeover.append(f"{q['month']} {q['order']} {q['name']} ({f}): prints the v2000 value")
            continue
        if (not (b51 and b51["read"]) and SE_B_WINDOW[0] <= q["month"] <= SE_B_WINDOW[1]
                and q["state"] in SE_B_STATES and q["abs"] > t):
            b_named.append(f"{q['month']} {q['order']} {q['name']} ({f}): printed {money(q['abs'])}, table "
                              f"{money(t)}; above the table by {money(q['abs'] - t)} "
                              f"in a state where the .51(b) county adjustments of 2008-2025 apply; (b) text not read")
            continue
        bad.append(f"{q['month']} {q['order']} {q['name']} ({f}, {q['resolved_by']}): printed {money(q['abs'])}, "
                   f"table {money(t)} ({v})" + (f"; the rule allows {[money(x) for x, _ in cand]}" if len(cand) > 1
                                                or cand[0][1] != "1000.52" else ""))
    # a city-only row the county could not be had for: its printed value has to be one the table
    # carries somewhere in its state that version (a weaker check, counted and printed, no verdict)
    by_state = {v: defaultdict(set) for v in versions}
    for v, tab in versions.items():
        for f, (_n, st, d) in tab.items():
            by_state[v][st].add(d)
    po_in = sum(1 for q in printed_only
                if q["abs"] in by_state[version_of(tuple(int(x) for x in q["month"].split("-")))].get(q["state"], ()))
    return ok, bad, unread, changeover, printed_only, po_in, b_named, b_agree


def order_layers(rows, central_rows, versions, footers, b51=None):
    """Per version: per order, and pooled over the eleven, county -> printed absolute differential.
    Central rows enter the pool with their printed differential, or, where the list prints only the
    adjustment relative to Jackson County, MO, that adjustment plus the Jackson differential the same
    announcement prints in its footer.

    The framework's value at a county is the value the rule allows for the row (b_candidates: 1000.52,
    or 1000.52 plus a .51(b) entry). A county is disputed, and its pairs leave the four-cell count, when a
    row there prints a value the rule does not allow, or when its rows carry two different rule values in
    one version (the same county priced by two orders)."""
    out = {}
    cen = []
    for q in central_rows:
        if q.get("resolved_fips") is None:
            continue
        if "diff" in q:
            a = q["diff"]
        elif footers.get(q["month"]) is not None:
            a = q["rel"] + footers[q["month"]]
        else:
            continue
        cen.append({"order": 1032, "month": q["month"], "resolved_fips": q["resolved_fips"], "abs": a})
    for v in versions:
        def in_v(q):
            return version_of(tuple(int(x) for x in q["month"].split("-"))) == v
        groups = defaultdict(list)
        for q in rows:
            if q.get("resolved_fips") and "abs" in q and in_v(q):
                groups[q["order"]].append(q)
        pooled = [q for g in groups.values() for q in g] + [q for q in cen if in_v(q)]
        for name, qs in [(f"order{o}_lists", g) for o, g in sorted(groups.items())] + [("eleven_order_lists", pooled)]:
            vals, clash, disputed, rule = defaultdict(Counter), [], set(), defaultdict(set)
            look = {}
            for q in qs:
                f = q["resolved_fips"]
                ft = table_key(q)
                look[f] = ft
                vals[f][q["abs"]] += 1
                if ft in versions[v]:
                    t = versions[v][ft][2]
                    hit = [val for val, _how in b_candidates(q, ft, t, b51) if val == q["abs"]]
                    if hit:
                        rule[f].add(hit[0])
                    else:
                        disputed.add(f)
            for f, s in rule.items():
                if len(s) > 1:
                    disputed.add(f)
            loc = {}
            for k, c in vals.items():
                if len(c) > 1:
                    clash.append(f"{k}: {dict((money(a), b) for a, b in c.items())}")
                loc[k] = c.most_common(1)[0][0]
            fwv = {k: (next(iter(rule[k])) if len(rule.get(k, ())) == 1 else versions[v][look[k]][2])
                   for k in loc if look[k] in versions[v]}
            fw = sorted(set(fwv.values()))
            out[f"{v}/{name}"] = {"values": loc, "clash": clash, "framework_nonzero": len(fw) > 1, "rows": len(qs),
                                  "disputed": sorted(disputed), "framework_values": fwv}
    return out


def order_coverage(parsed, errs, rows):
    """Rule 25: every file opened, with its pages, the layouts read and the rows taken, zero included."""
    per_file = defaultdict(lambda: {"rows": 0, "resolved": 0})
    for q in rows:
        per_file[q["file"]]["rows"] += 1
        per_file[q["file"]]["resolved"] += 1 if q.get("resolved_fips") else 0
    table = []
    for r in parsed:
        pf = per_file.get(r["dest"], {"rows": 0, "resolved": 0})
        table.append({"order": r["order"], "unit": r["unit"], "key": r["key"], "file": r["dest"],
                      "pages": r["pages"], "image_pages": r["image_pages"], "layouts": r["formats"],
                      "plant_rows": pf["rows"], "rows_county_resolved": pf["resolved"],
                      "base_footer": r["base_footer"]})
    not_served = [{"order": o, "unit": u, "key": k, "http": h, "check": c} for o, u, k, h, c in errs]
    summary = {}
    for o in sorted(OTHER_ORDERS):
        t = [x for x in table if x["order"] == o]
        summary[str(o)] = {"name": OTHER_ORDERS[o], "files_opened": len(t),
                           "files_monthly": sum(1 for x in t if x["unit"] == "month"),
                           "files_yearly": sum(1 for x in t if x["unit"] == "year"),
                           "files_with_a_plant_list_read": sum(1 for x in t if x["plant_rows"]),
                           "files_with_zero_plant_rows": sum(1 for x in t if not x["plant_rows"]),
                           "image_only_pages": sum(len(x["image_pages"]) for x in t),
                           "plant_rows": sum(x["plant_rows"] for x in t),
                           "rows_county_resolved": sum(x["rows_county_resolved"] for x in t),
                           "layouts": sorted({f for x in t for f in x["layouts"]}),
                           "months_with_rows": sorted({x["key"][:6] for x in t if x["plant_rows"] and x["unit"] == "month"})[:1]
                           + sorted({x["key"][:6] for x in t if x["plant_rows"] and x["unit"] == "month"})[-1:],
                           "listed_not_served": [f"{e['key']} ({e['http'] or e['check']})" for e in not_served
                                                 if e["order"] == o]}
    return table, summary, not_served


# --------------------------------------------------------------------------- B154-3b: the ten orders' location dollars

def _label_words(t):
    """The printed words of a pool line before its first number ('Class I Location Differential 585,181,985
    (277,289.92)' -> 'Class I Location Differential'); '61(c)' is a word."""
    out = []
    for w in t.split(" "):
        if re.fullmatch(r"[-+($]*[\d,]+(\.\d+)?\)?-?|\$", w):
            break
        out.append(w)
    return " ".join(out)


def order_pool(parsed):
    """Per order and month, the handler and producer lines as printed (POOL_LABELS). Monthly files give the
    month by their name, yearly compilations by the page. A revised file's value replaces the first one and
    the replaced value is kept. Two different values for one line in one month from unrevised files, or a
    label printed with no amount, is a parse failure."""
    lines, failures, revised, other = defaultdict(dict), [], [], []
    for r in sorted(parsed, key=lambda r: (r["order"], r["key"].endswith("rev"), r["key"])):
        rev = r["unit"] == "month" and r["key"].endswith("rev")
        for p in r.get("pool", []):
            m = file_month(r) or p["page_month"]
            if p.get("page_order") and 1000 + p["page_order"] != r["order"]:
                # a page that names another order (the Arizona file carries the Pacific Northwest page):
                # checked against that order's own file below, not read as this order's line
                other.append((1000 + p["page_order"], m, p["side"], p["cents"], r["dest"]))
                continue
            if m is None:
                failures.append(f"{r['order']} {r['dest']} p{p['page']}: {p['side']} line with no month")
                continue
            if p["cents"] is None:
                failures.append(f"{r['order']} {m} {r['dest']} p{p['page']}: label with no amount: {p['label']}")
                continue
            d = lines[r["order"]].setdefault(m, {})
            new = {"cents": p["cents"], "meaning": p["meaning"], "label": _label_words(p["label"]),
                   "file": r["dest"], "page": p["page"]}
            old = d.get(p["side"])
            if old is None or (old["cents"] == new["cents"] and old["meaning"] == new["meaning"]):
                d.setdefault(p["side"], new)
            elif rev and not old.get("revised"):
                revised.append(f"{r['order']} {m} {p['side']}: {money(old['cents'])} replaced by the revision's "
                               f"{money(new['cents'])}")
                d[p["side"]] = {**new, "revised": True}
            else:
                failures.append(f"{r['order']} {m} {p['side']}: {money(old['cents'])} ({old['file']}) and "
                                f"{money(new['cents'])} ({new['file']})")
    cross = {"agree": 0, "off": [], "own_line_absent": 0}
    for o, m, side, c, f in other:
        own = lines.get(o, {}).get(m, {}).get(side)
        if own is None:
            cross["own_line_absent"] += 1
        elif own["cents"] == c:
            cross["agree"] += 1
        else:
            cross["off"].append(f"{o} {m} {side}: {money(c)} on a page of {f}, {money(own['cents'])} in its own file")
    failures += cross["off"]
    return lines, failures, revised, cross


def order_pool_arm(parsed):
    """B154-3 on the ten orders. Where the handler line is the relative one, A is that line as printed,
    Bp is minus the producer line the pool adds, T = Bp - A (the Central convention); elsewhere both lines
    are printed and T is not formed."""
    lines, failures, revised, cross = order_pool(parsed)
    months = {o: {(file_month(r) or None) for r in parsed if r["order"] == o} for o in OTHER_ORDERS}
    rows, cover, per = defaultdict(list), {}, {}
    for o in sorted(OTHER_ORDERS):
        cov = Counter()
        meanings = Counter()
        for ym in month_range():
            k = ym_str(ym)
            d = lines.get(o, {}).get(k, {})
            h, p = d.get("handler"), d.get("producer")
            if h:
                meanings[h["meaning"]] += 1
            if h and p:
                st = "both lines read" + ("" if h["meaning"] == "relative" else f" (handler line {h['meaning']})")
            elif p:
                st = "producer line only"
            elif h:
                st = "handler line only"
            else:
                st = ("file opened, no pool computation printed" if (k in months[o] or any(
                    r["order"] == o and r["unit"] == "year" and r["key"] == k[:4] for r in parsed))
                      else "no file for this month")
            cov[st] += 1
            cover[f"{o}/{k}"] = st
            if not p:
                continue
            Bp = -p["cents"]
            row = {"month": k, "version": version_of(ym), "Bp": money(Bp), "producer_label": p["label"]}
            if h:
                row.update({"handler_label": h["label"], "handler_meaning": h["meaning"],
                            "handler_printed": money(h["cents"])})
                if h["meaning"] == "relative":
                    T = t_from(h["cents"], Bp)
                    row.update({"A": money(h["cents"]), "T": money(T),
                                "T_over_Bp": ratio(T / Bp) if Bp else None})
            rows[o].append(row)
        withT = [r for r in rows[o] if "T" in r]
        tb = sorted(float(r["T_over_Bp"]) for r in withT if r["T_over_Bp"] not in (None, "null"))
        by_v = {}
        for v in ("v2000", "v2025", "v2026"):
            rs = [r for r in withT if r["version"] == v]
            if rs:
                by_v[v] = {"months": len(rs), "T_negative": sum(1 for r in rs if r["T"].startswith("-")),
                           "T_sum": money(sum(cents(Decimal(r["T"])) for r in rs))}
        labels = sorted({(r.get("handler_label"), r.get("handler_meaning"), r["producer_label"]) for r in rows[o]},
                        key=str)
        per[str(o)] = {"name": OTHER_ORDERS[o], "coverage": dict(sorted(cov.items())),
                       "handler_meaning": dict(sorted(meanings.items())),
                       "labels_as_printed": [{"handler": a, "handler_meaning": b, "producer": c} for a, b, c in labels],
                       "months_with_T": len(withT), "T_zero": sum(1 for r in withT if cents(Decimal(r["T"])) == 0),
                       "T_over_Bp_median": f"{tb[len(tb) // 2]:.3f}" if tb else None,
                       "T_over_Bp_range": [f"{tb[0]:.3f}", f"{tb[-1]:.3f}"] if tb else None,
                       "by_version": by_v,
                       "first_last_month_read": [rows[o][0]["month"], rows[o][-1]["month"]] if rows[o] else None}
    return {"rows": {str(o): rs for o, rs in rows.items()}, "coverage": cover, "per_order": per,
            "failures": failures, "revised": revised, "pages_of_another_order": cross}


# --------------------------------------------------------------------------- B154-5

def class_counts(pp):
    rows, same = [], []
    for k in sorted(pp):
        r = pp[k]
        prices = dict(r["class_prices"])
        if r["esl"] not in (None, 0) and "I" in prices:
            prices["I-ESL"] = prices["I"] + r["esl"]
        named = len(set(r["classes_named"]))
        rows.append({"month": k, "classes_named": named,
                     "class_prices_printed": {c: money(v) for c, v in sorted(prices.items())},
                     "distinct_class_prices": len(set(prices.values())) if prices else None})
        vals = sorted(prices.items())
        for i, (a, x) in enumerate(vals):
            for b, y in vals[i + 1:]:
                if x == y:
                    same.append(f"{k}: {a} = {b} = {money(x)}")
    return rows, same


# --------------------------------------------------------------------------- depooling print

def depool_rows(ov, pp):
    """Class III and Class IV against each order's uniform price. A month where either price is
    not read carries null, not false, and is named; the counts are 'above in M of N readable'.

    Class III price, first source that reads: the Central announcement's printed Class III
    price (2021-07 on); Central's uniform price minus its PPD on the announcement; the same
    identity on the overview's Central row. Class IV: the announcement's printed price only."""
    c3, c3_src, c4 = {}, {}, {}
    for k, r in pp.items():
        if "III" in r["class_prices"]:
            c3[k], c3_src[k] = r["class_prices"]["III"], "announcement, printed Class III price"
        elif r["sup"] is not None and r["ppd"] is not None:
            c3[k], c3_src[k] = r["sup"] - r["ppd"], "announcement, uniform price minus PPD"
        if "IV" in r["class_prices"]:
            c4[k] = r["class_prices"]["IV"]
    for y, d in ov.items():
        s = d["orders"].get(32, {}).get("series", {})
        for mi in range(12):
            k = ym_str((y, mi + 1))
            if k in c3:
                continue
            su = s.get("sup", [None] * 12)[mi] if mi < len(s.get("sup", [])) else None
            pd_ = s.get("ppd", [None] * 12)[mi] if mi < len(s.get("ppd", [])) else None
            if su is not None and pd_ is not None:
                c3[k], c3_src[k] = cents(su) - cents(pd_), "overview, Central uniform price minus PPD"
    out = {}
    for y, d in sorted(ov.items()):
        for o, od in sorted(d["orders"].items()):
            s = od["series"]
            for mi in range(12):
                ym = (y, mi + 1)
                k = ym_str(ym)
                rec = s.get("receipts", [None] * 12)[mi]
                if rec is None:
                    continue
                sup = s.get("sup", [None] * 12)[mi]
                row = [k, str(int(rec))] + [
                    (None if s.get(u, [None] * 12)[mi] is None else f"{s[u][mi]:.2f}") for u in ("u1", "u2", "u3", "u4")]
                sc = cents(sup) if sup is not None else None
                row += [money(sc) if sc is not None else None,
                        (c3[k] > sc) if (sc is not None and k in c3) else None,
                        (c4[k] > sc) if (sc is not None and k in c4) else None]
                out.setdefault(str(o), []).append(row)
    summary = {}
    for o, rows in out.items():
        mom = []
        for a, b in zip(rows, rows[1:]):
            x, y2 = int(a[1]), int(b[1])
            if x:
                mom.append((y2 - x) / x)
        summary[o] = {"months": len(rows),
                      "class_III_readable": sum(1 for r in rows if r[7] is not None),
                      "class_III_above_uniform": sum(1 for r in rows if r[7]),
                      "class_III_unread_months": [r[0] for r in rows if r[7] is None],
                      "class_IV_readable": sum(1 for r in rows if r[8] is not None),
                      "class_IV_above_uniform": sum(1 for r in rows if r[8]),
                      "largest_monthly_fall": ratio(min(mom)) if mom else None,
                      "largest_monthly_rise": ratio(max(mom)) if mom else None}
    return out, summary, {k: c3_src[k] for k in sorted(c3_src)}


# --------------------------------------------------------------------------- criteria

def build(raw=None, versions=None, letters=None, order_51=None, ov=None, pp=None, bases=None,
          jitter=None, cover_drop=None, map_drop=None, plant_override=None, order_75=None, order_61=None,
          orders=None, order_override=None, places="load", b51="load", same_price_check=True):
    raw = raw or load_tables()
    versions = versions or build_versions(raw)
    crit, extra = [], {}

    ok0, prob0, det0 = check_tables(raw, versions)
    crit.append({"name": "B154-0", "kind": "instrument", "passed": ok0,
                 "statement": "each version of the county table is read row by row on the printed two-decimal "
                              "format; the current table equals the 2026 print plus the two changes of 91 FR 59047",
                 "mapping": {"every check holds": "PASS", "any check fails": "FAIL"},
                 "detail": "; ".join(prob0) if prob0 else
                 "; ".join(f"{v}: {d['rows']} rows, {d['distinct_values']} values {d['min']} to {d['max']}, step "
                           f"{d['step_cents']} cents" for v, d in det0.items() if v.startswith("v"))})
    extra["tables"] = det0

    # B154-1
    if letters is None:
        letters = letters_of(paragraphs(RAW / "rules" / "lii_1000_50.html"))
    if order_51 is None:
        order_51 = {o: " ".join(paragraphs(RAW / "rules" / f"lii_{fn}_51.html")) for o, fn in ORDER_FILE.items()}
    if order_75 is None:
        order_75 = {o: " ".join(paragraphs(RAW / "rules" / f"lii_{fn}_75.html")) for o, fn in ORDER_FILE.items()}
    if order_61 is None:
        order_61 = {o: " ".join(paragraphs(RAW / "rules" / f"lii_{fn}_61.html")) for o, fn in ORDER_FILE.items()}
    ok1, prob1, det1 = check_rule_text(letters, order_51)
    ok1s, prob1s, det1s = check_seller_side(order_75, order_61)
    cc = set(det1.get("county_classes", [])) if det1 else set()
    zs = zero_squares_between(cc, versions["v2026"])
    nz = {k: v for k, v in zs.items() if v}
    if ok1 is not None and nz:
        ok1, prob1 = False, prob1 + [f"non-zero squares the rule should make zero: {nz}"]
    if ok1 is not None:
        if ok1s is None:
            ok1, prob1 = None, prob1 + prob1s
        elif not ok1s:
            ok1, prob1 = False, prob1 + prob1s
    crit.append({"name": "B154-1", "kind": "known_answer", "passed": ok1,
                 "statement": "the rule's own zero set. Handler side: only the Class I skim and butterfat paragraphs "
                              "of 1000.50 cite 1000.52, so squares among Classes II, III and IV are zero, and so is "
                              "the square of Class I against the Class I ESL price (1000.50(r) adds a term to the "
                              "Class I price that does not cite 1000.52). Seller side: each order's .75 adjusts "
                              "payment for all producer milk by the plant's location, naming no class, and its .61 "
                              "pools it, so the producer side carries one location term for every class",
                 "mapping": {"all parts zero": "PASS", "any non-zero": "FAIL", "text not read": "no verdict"},
                 "detail": "; ".join(prob1) if prob1 else
                 f"letters read {det1['letters_read']}; citing 1000.52: {det1['citing_1000_52']}; classes with a "
                 f"county term: {det1['county_classes']}; non-zero squares: 0 over the "
                 f"{len([k for k in zs if 'ESL' not in k])} pairs among Classes II, III, IV and 0 on Class I against "
                 f"the Class I ESL price; {len(det1['orders_51_read'])} order .51 sections name no class but I; "
                 f"seller side: {len(det1s['orders_75_read'])} order .75 sections set the producer adjustment by "
                 f"plant location and name no class, {len(det1s['orders_61_read'])} order .61 sections pool it"})
    extra["rule_text"] = {"detail": det1, "seller_side": det1s, "squares_the_rule_makes_zero": zs}

    # bases
    if bases is None:
        bases, bnames = {}, {}
        for o, fn in ORDER_FILE.items():
            f, nmx = base_county(order_51[o], [versions["v2026"], versions["v2000"]])
            if f:
                bases[o] = f
                bnames[o] = nmx
        extra["base_counties"] = {str(o): {"fips": bases[o], "name": bnames[o],
                                           "v2000": money(versions["v2000"][bases[o]][2]),
                                           "v2025": money(versions["v2025"][bases[o]][2]),
                                           "v2026": money(versions["v2026"][bases[o]][2])} for o in sorted(bases)}

    # B154-0b
    ov = ov if ov is not None else load_overviews()
    bp = check_base_prices(ov, versions, bases, jitter)
    ok0b = (not bp["off"]) if bp["cells"] else None
    crit.append({"name": "B154-0b", "kind": "instrument", "passed": ok0b,
                 "statement": "all-order overview: Class I price minus the base county's differential is one base "
                              "price per month across orders; the 1005/1006/1007 .51(b) adjustments the overview "
                              "footnotes are outside the Class I column and recorded beside it",
                 "mapping": {"every cell within 0.01": "PASS", "any cell off": "FAIL, list printed",
                             "order whose base county is not on disk": "cells named, no verdict",
                             "cell printing the same Class I price as another order's cell that month, the rest of "
                             "its row its own, in fewer than half its order's months": "named, no verdict",
                             "cell whose whole row equals another order's row that month": "FAIL (row read from "
                                                                                          "another order)"},
                 "detail": f"{bp['cells']} order-month cells over {bp['months']} months; within 0.01 of the common "
                           f"base: {bp['within']}; off and failing: "
                           f"{len(bp['off'])}{(' ' + str(bp['off'][:6])) if bp['off'] else ''}; cells with no "
                           f"verdict (base county not on disk): {len(bp['unread'])} ({bp['unread'][0] if bp['unread'] else ''}"
                           f"{' .. ' + bp['unread'][-1] if len(bp['unread']) > 1 else ''}); cells repeating another "
                           f"order's printed price: {len(bp['repeats_other_order'])} {bp['repeats_other_order'][:7]}; "
                           f"cells whose year's overview footnotes a 1005/1006/1007 .51(b) adjustment, printed "
                           f"outside the Class I column: {bp['footnote_adjustment_cells']}; header differential "
                           f"against the table: {len(bp['header_mismatch'])} mismatches"
                           f"{(' ' + str(bp['header_mismatch'][:4])) if bp['header_mismatch'] else ''}"})
    extra["base_prices"] = bp

    # Central announcements
    pp = pp if pp is not None else load_pp()
    rows3, cover = central_arm(pp)
    if cover_drop:
        cover = {k: v for k, v in cover.items() if k != cover_drop}
    cov_ok, cov_why = coverage_ok(cover)
    both = [r for r in rows3 if "T" in r]
    syn_A, syn_Bp = synthetic_pool([(320, 500, 0), (250, 300, 0), (320, 0, 900)], 320)
    syn_T = t_from(syn_A, syn_Bp)
    ok3 = cov_ok and syn_T == 0 and bool(both)
    if cov_ok and not both:
        ok3 = None
    by_v = defaultdict(list)
    for r in both:
        by_v[r["version"]].append(r)
    seg = {v: {"months": len(rs), "T_sum": money(sum(cents(Decimal(r["T"])) for r in rs)),
               "T_negative_months": sum(1 for r in rs if r["T"].startswith("-"))} for v, rs in sorted(by_v.items())}
    cov_counts = Counter(v.split(";")[0].split(" (")[0] for v in cover.values())
    abs_t = sorted((abs(cents(Decimal(r["T"]))), r["month"]) for r in both)
    rival_t = ("the scalar price field predicts T = 0 (a position price the same for every class puts the "
               "handler-side location money on all pooled milk, as on the producer side); months with T = 0 among "
               f"the {len(both)}: {sum(1 for a, _ in abs_t if a == 0)}"
               + (f"; smallest |T| {money(abs_t[0][0])} ({abs_t[0][1]})" if abs_t else ""))
    crit.append({"name": "B154-3", "kind": "own_reading", "passed": ok3,
                 "statement": "Central order, month by month: handler location dollars A, producer location dollars "
                              "Bp, T = Bp - A, T / Bp and T per pooled hundredweight, by version; every month mapped "
                              "in the coverage table",
                 "mapping": {"object present, coverage complete, no parse failure": "PASS (printing criterion)",
                             "any parse failure or a month missing from the coverage": "FAIL",
                             "no month with both lines": "no verdict"},
                 "detail": f"coverage {dict(sorted(cov_counts.items()))}{('; ' + cov_why) if cov_why else ''}; "
                           f"months with both lines {len(both)}; by version {seg}; synthetic pool with all non-Class-I "
                           f"milk at the base county reads T = {money(syn_T)}; {rival_t}"})
    extra["central"] = {"rows": rows3, "coverage": cover, "by_version": seg}

    # plants
    prow = resolve_plants(pp, versions, raw)
    if plant_override:
        prow = plant_override(prow)
    footers = {k: r["jackson_footer"] for k, r in pp.items() if r["jackson_footer"] is not None}
    ok4n, bad4, unread4, misprint4, chg4 = check_plants(prow, versions, footers)
    ok4 = (not bad4) if ok4n else None
    crit.append({"name": "B154-4", "kind": "known_answer", "passed": ok4,
                 "statement": "Central plant lists: the printed location adjustment (and, where printed, the "
                              "differential at the plant) equal the county table at the plant's county, relative to "
                              "Jackson County, MO, under the version in force that month",
                 "mapping": {"every resolved row agrees": "PASS", "any row off": "FAIL, list printed",
                             "June 2025 row printing the v2000 value": "named, no verdict",
                             "county not resolved": "named, no verdict",
                             "printed differential disagreeing with its own row while the adjustment agrees, alone "
                             "in its month": "named, no verdict",
                             "two or more such rows in one month": "FAIL (differential column misread)"},
                 "detail": f"rows {len(prow)} over {len(set(q['month'] for q in prow))} months; agree {ok4n}; off "
                           f"{len(bad4)}{(' ' + str(bad4[:5])) if bad4 else ''}; changeover-month rows {len(chg4)}; "
                           f"rows named with no verdict: county not resolved {len(unread4)}"
                           f"{(' ' + str(unread4[:3])) if unread4 else ''}, printed differential disagreeing with its "
                           f"own row {len(misprint4)}{(' ' + str(misprint4[:3])) if misprint4 else ''}; rows resolved "
                           f"by the listing's city after the printed county name matched none: "
                           f"{sum(1 for q in prow if 'matched no county' in q.get('resolved_by', ''))}; Jackson footers "
                           f"read {len(footers)}"})
    extra["plants"] = {"rows": len(prow), "off": bad4, "no_verdict_rows": unread4 + misprint4,
                       "county_unresolved": unread4, "differential_misprint": misprint4, "changeover": chg4,
                       "formats": dict(Counter(pp[k]["plant_format"] or "none" for k in pp))}

    # the ten other orders (ruled 2026-10-29): B154-4b, and the record layer of B154-2 on eleven orders
    parsed, not_served = orders if orders is not None else load_orders()
    if places == "load":
        places = load_places()
    if b51 == "load":
        b51 = load_51b()
    orow = order_rows(parsed, versions, raw, prow, places, b51, same_price_check)
    if order_override:
        orow = order_override(orow)
    ok4b, bad4b, unread4b, chg4b, po4b, po_in, b4b, bagree4b = check_order_plants(orow, versions, b51)
    cov_table, cov_sum, cov_ns = order_coverage(parsed, not_served, orow)
    def _agrees(q):
        if "abs" not in q or not q.get("resolved_fips"):
            return False
        v_ = version_of(tuple(int(x) for x in q["month"].split("-")))
        f_ = table_key(q)
        return f_ in versions[v_] and any(val == q["abs"] for val, _h in
                                          b_candidates(q, f_, versions[v_][f_][2], b51))
    per_order = {str(o): {"rows": sum(1 for q in orow if q["order"] == o),
                          "agree": sum(1 for q in orow if q["order"] == o and _agrees(q)),
                          "county_unresolved": sum(1 for q in po4b if q["order"] == o)} for o in sorted(OTHER_ORDERS)}
    man_files = {d for _o, _u, _k, d, _h in order_files()[0]}
    cov_missing = sorted(man_files - {x["file"] for x in cov_table})
    ok4bv = (not bad4b and not cov_missing) if ok4b else None
    # rows that print a city but no county, and that no list ties to a county: their printed values, keyed by
    # city and state, per order and version (printed, not gating); and, where a row prints both the
    # differential and the adjustment from the base (Pacific Northwest), the base the two imply against the
    # table's value at the base county
    po_layers = {}
    for q in po4b:
        v_ = version_of(tuple(int(t) for t in q["month"].split("-")))
        po_layers.setdefault(f"{v_}/order{q['order']}_city_keyed", defaultdict(Counter))[
            f"{q.get('city') or q.get('county')}, {q['state']}"][q["abs"]] += 1
    po_stats = {}
    for k, d in sorted(po_layers.items()):
        vals = {loc: c.most_common(1)[0][0] for loc, c in d.items()}
        st_ = square_stats(vals)
        st_["clash"] = [f"{loc}: {dict((money(a), b) for a, b in c.items())}" for loc, c in d.items() if len(c) > 1]
        po_stats[k] = st_
    base_of = {1124: "53033", 1131: "04013", 1051: "06037"}   # King WA, Maricopa AZ, Los Angeles CA (.51(a))
    king = {"agree": 0, "off": [], "by_order": Counter()}
    for q in orow:
        if q["order"] in base_of and "diff" in q and "rel" in q:
            v_ = version_of(tuple(int(t) for t in q["month"].split("-")))
            bf = base_of[q["order"]]
            if q["diff"] - q["rel"] == versions[v_][bf][2]:
                king["agree"] += 1
                king["by_order"][str(q["order"])] += 1
            else:
                king["off"].append(f"{q['month']} {q['order']} {q['name']}: {money(q['diff'])} - ({money(q['rel'])}) "
                                   f"vs base county {bf} {money(versions[v_][bf][2])}")
    king["by_order"] = dict(sorted(king["by_order"].items()))
    crit.append({"name": "B154-4b", "kind": "known_answer", "passed": ok4bv,
                 "statement": "the plant lists of the ten other orders: the differential printed at a plant (or the "
                              "printed adjustment plus the base differential the same page prints) equals the county "
                              "table at the plant's county under the version in force that month",
                 "mapping": {"every row with a county agrees": "PASS", "any such row off": "FAIL, list printed",
                             "no order prints a row with a county": "no verdict",
                             "June 2025 row printing the v2000 value": "named, no verdict",
                             "row, 2008-05 to 2025-05, equal to the table plus the .51(b) entry the rule text lists "
                             "for its county (the listing order's own entry for an Appalachian, Florida or "
                             "Southeast list; the entry of the order whose table lists the county for another "
                             "order's list)": "agrees (counted with the agreeing rows and named)",
                             "row, 2008-05 to 2025-05, matching neither the table nor the table plus the .51(b) "
                             "entry the text allows": "FAIL, list printed",
                             "row above the table, 2008-05 to 2025-05, in a state where the 1005/1006/1007 .51(b) "
                             "county adjustments apply, while the .51(b) text is not on disk": "named, no verdict",
                             "row whose county the page does not give and no other list gives": "counted and named, "
                             "no verdict; its printed value checked against the values the table carries in its state",
                             "row with neither a differential nor a printed base": "named, no verdict",
                             "a file in the manifest missing from the coverage table": "FAIL (rule 25)"},
                 "detail": f"files opened {len(cov_table)} of {len(man_files)} in the manifest"
                           f"{(', missing ' + str(cov_missing[:5])) if cov_missing else ''}; "
                           f"rows {len(orow)} from {sum(1 for x in cov_table if x['plant_rows'])} files; with a county "
                           f"and agreeing {ok4b}; off {len(bad4b)}{(' ' + str(bad4b[:5])) if bad4b else ''}; "
                           f"changeover-month rows {len(chg4b)}; "
                           + (f"rows agreeing with the table plus the .51(b) entry the rule text lists for the county "
                              f"{len(bagree4b)} {dict(Counter(s.rsplit(', ', 1)[1] for s in bagree4b))}"
                              if b51 and b51["read"] else
                              f"rows above the table where the .51(b) adjustments apply, named with no verdict "
                              f"({'(b) text not read'}), {len(b4b)}")
                           + f"; county resolved from the Census 2020 place-by-county file "
                           f"{sum(1 for q in orow if q.get('resolved_by', '').startswith('Census'))} (place in one "
                           f"county {sum(1 for q in orow if q.get('resolved_by', '').startswith('Census') and 'table_fips' not in q and 'census_variant' not in q)}, "
                           f"place across counties each at the same price under the row's order and month "
                           f"{sum(1 for q in orow if 'table_fips' in q)}, Census name variant "
                           f"{sum(1 for q in orow if 'census_variant' in q and q.get('resolved_fips'))}); "
                           f"county not given on the page and not found in another "
                           f"list or in the place file {len(po4b)}, of which {po_in} print a value the table carries "
                           f"in that state; "
                           f"rows with no differential and no base printed {len(unread4b)}; rows printing both a "
                           f"differential and an adjustment from the base whose difference equals the table at the "
                           f"order's base county: {king['agree']} of {king['agree'] + len(king['off'])} "
                           f"{king['by_order']}; by order "
                           f"{ {o: d for o, d in per_order.items() if d['rows']} }; orders whose files print no plant "
                           f"list with a differential: "
                           f"{[OTHER_ORDERS[int(o)] for o, d in cov_sum.items() if not d['plant_rows']]}"})
    extra["orders"] = {"coverage": cov_table, "summary": cov_sum, "listed_not_served": cov_ns,
                       "printed_only_layers": po_stats, "base_check": king,
                       "off": bad4b, "changeover": chg4b, "b_adjustment_named": b4b, "no_value": unread4b,
                       "b_adjustment_agree": bagree4b,
                       "rule_51b": _b51_record(b51, bases, versions, ov, bagree4b),
                       "census_resolved": dict(sorted(Counter(
                           f"{q['order']} {q['city']}, {q['state']} -> {q['resolved_fips']} ({q['resolved_by'].split('the place ')[1].split(' lies')[0]})"
                           for q in orow if q.get("resolved_by", "").startswith("Census")).items())),
                       "census_not_resolved": dict(sorted(Counter(
                           f"{q['order']} {q['city']}, {q['state']}"
                           + (f" ({version_of(tuple(int(t) for t in q['month'].split('-')))}): place in several "
                              "counties, prices differ under this order and month: "
                              + ", ".join(f"{k} {v} {q['census_candidate_prices'][k]}"
                                          for k, v in q["census_candidates"].items())
                              if q.get("census_candidate_prices") else
                              (": place in several counties " + ", ".join(f"{k} {v}" for k, v in q["census_candidates"].items()))
                              if q.get("census_candidates") else
                              (": no unique Census name variant in this state; candidates "
                               + " | ".join(f"{k} ({'; '.join(v)})" for k, v in q["census_variant_candidates"].items()))
                              if q.get("census_variant_candidates") else
                              ": no Census place of this name, and none whose name begins with it, in this state")
                           for q in po4b if "census_candidates" in q).items())),
                       "census_cross_county_same_price": dict(sorted(Counter(
                           f"{q['order']} {q['city']}, {q['state']} "
                           f"({version_of(tuple(int(t) for t in q['month'].split('-')))}) -> {q['resolved_fips']}: "
                           + ", ".join(f"{k} {'/'.join(v) if v else 'not in the table'}"
                                       for k, v in q["same_price_counties"].items())
                           for q in orow if "table_fips" in q).items())),
                       "census_name_variant": {
                           f"{q['order']} {q['city']}, {q['state']}": {
                               "census_place": q["census_variant"]["census_place"],
                               "source_lines": q["census_variant"]["source_lines"],
                               "rows_resolved": sum(1 for r in orow if r.get("census_variant")
                                                    and r["order"] == q["order"] and r["city"] == q["city"]
                                                    and r["state"] == q["state"] and r.get("resolved_fips")),
                               "rows": sum(1 for r in orow if r.get("census_variant") and r["order"] == q["order"]
                                           and r["city"] == q["city"] and r["state"] == q["state"])}
                           for q in orow if q.get("census_variant")},
                       "county_unresolved": [f"{q['month']} {q['order']} {q['name']} ({q.get('city')}, {q['state']}): "
                                             f"printed {money(q['abs'])}" for q in po4b],
                       "county_unresolved_value_in_state_table": po_in,
                       "labels": {str(o): sorted({re.sub(r"\s*[-$(]*(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)\)?-?", "", lab.split(": ", 1)[1]).strip()
                                                  for x in parsed if x["order"] == o for lab in x["labels"]})[:40]
                                  for o in sorted(OTHER_ORDERS)},
                       "headers": {str(o): sorted({h.split(": ", 1)[1] for x in parsed if x["order"] == o
                                                   for h in x["headers"]})[:20] for o in sorted(OTHER_ORDERS)}}

    # B154-2
    layers, cells, splits = {}, {}, {}
    for v in versions:
        vals = {f: x[2] for f, x in versions[v].items()}
        st = square_stats(vals)
        layers[f"{v}/county_table"] = st
        cells[f"{v}/county_table"] = layer_cell(st, st["independent_nonzero"] > 0)
        splits[f"{v}/county_table"] = pair_cells(vals, vals)
    rl = record_layer(prow, versions)
    for v, d in rl.items():
        st = square_stats(d["values"])
        st["clash"] = d["clash"]
        st["rows_unresolved_left_out"] = d["rows_unresolved"]
        layers[f"{v}/central_lists"] = st
        cells[f"{v}/central_lists"] = layer_cell(st, d["framework_nonzero"])
        fw = {k: versions[v][k][2] for k in d["values"] if k in versions[v]}
        splits[f"{v}/central_lists"] = pair_cells(fw, d["values"])
    for key, d in sorted(order_layers(orow, prow, versions, footers, b51).items()):
        v = key.split("/")[0]
        st = square_stats(d["values"])
        st["clash"] = d["clash"]
        st["rows"] = d["rows"]
        # A county where some row prints a value other than the table's (B154-4b: a print off the table, or
        # the unread .51(b) adjustment) has no settled framework value; its pairs are left out of the
        # four-cell count and counted as unread (11c)
        st["disputed_locations"] = d["disputed"]
        nd = {k: x for k, x in d["values"].items() if k not in set(d["disputed"])}
        n_all, n_nd = len(d["values"]), len(nd)
        st["pairs_unread_disputed"] = n_all * (n_all - 1) // 2 - n_nd * (n_nd - 1) // 2
        layers[key] = st
        cells[key] = layer_cell(st, d["framework_nonzero"])
        fw = {k: d["framework_values"][k] for k in nd if k in d["framework_values"]}
        splits[key] = pair_cells(fw, nd)
    # The verdict reads the county table, the Central lists and the eleven orders' lists pooled. A single
    # order's list is printed with its own cell and does not gate: it is the pooled layer cut by who
    # prints the list, and 1000.52 is one table for all orders (D55).
    gate = {k for k in cells if k.endswith(("/county_table", "/central_lists", "/eleven_order_lists"))}
    passed2 = rival_verdict({k: c for k, (c, _) in cells.items() if k in gate})
    six = {k for k in cells if k.endswith(("/county_table", "/central_lists"))}
    read_splits = {k: s for k, s in splits.items() if cells[k][0] != "unread" and k in six}
    read_pool = {k: s for k, s in splits.items() if cells[k][0] != "unread" and k.endswith("/eleven_order_lists")}
    # grid_split reports the current version's county table only (ruled 2026-10-27): the earlier
    # versions are superseded tables and the plant lists are pairs of counties inside the table.
    # The sum over all three versions and both layers is printed as an extra reading.
    cur_key = f"{VERSION_CUTS[-1][1]}/county_table"
    grid2, split2 = grid_of(passed2, {k: s for k, s in read_splits.items() if k == cur_key})
    _all_grid, split_all = grid_of(passed2, read_splits)
    extra["grid_split_three_versions"] = {"layers": sorted(read_splits), "split": split_all}
    _pg, split_pool = grid_of(passed2, read_pool) if read_pool else (None, None)
    extra["grid_split_eleven_order_lists"] = {"layers": sorted(read_pool), "split": split_pool}
    zero_val = {v: sorted(f for f, x in versions[v].items() if x[2] == 0) for v in versions}
    note = ("; ".join(f"{k}: layer {c} ({why}), pairs {splits[k]}" for k, (c, why) in sorted(cells.items()))
            + f"; grid_split counts the current version's county table ({cur_key}) at the 0.01 floor; extra "
              f"reading, summed over the {len(read_splits)} read layers of the three versions: {split_all}; "
              f"the eleven orders' pooled plant lists, summed over the {len(read_pool)} read versions: {split_pool}; "
              "the verdict reads the county table, the Central lists and the pooled lists, and each order's own "
              "list is printed with its cell without gating. "
              "A counts county pairs with equal values: this "
              "framework predicts d(c1) - d(c2) = 0 there as the rival predicts zero, and the reading is zero. "
              "The seller side (B154-1) reads the same way: both accounts give the producer one location term "
              "for every class")
    rec2 = {"name": "B154-2", "kind": "rival", "passed": passed2, "grid": grid2}
    if split2:
        rec2["grid_split"] = split2
    crit.append({**rec2,
                 "grid_note": note,
                 "rival_premise": "on the handler (buyer) side, raw milk has one price at a position: same county, "
                                  "same month, same component basis, whatever the use, the class price a handler "
                                  "is charged is a scalar phi(c, t)",
                 "rival_entailment": "P(k, c, t) = phi(c, t) for every class k on the handler side, so "
                                     "S(I, k; c1, c2) = [phi(c1) - phi(c1)] - [phi(c2) - phi(c2)] = 0",
                 "rival_shape": "point",
                 "statement": "handler-side squares (I, k) x (c1, c2) above the floor, per version, on the county "
                              "table, on the Central plant lists and on the plant lists of the eleven orders pooled "
                              "(each order's own list printed beside); the framework's opposite point prediction is "
                              "d(c1) - d(c2)",
                 "mapping": {"every gating layer (county table, Central lists, pooled lists) has squares above all "
                             "four floors": "PASS (grid from the pair counts: "
                                                                             "B, or mixed with A where two counties "
                                                                             "share a value)",
                             "a layer all inside the floor while the county table gives a non-zero square":
                                 "FAIL, grid C",
                             "some layer read, some layer with fewer than two locations, or its answer flipping "
                             "across floors, or both accounts giving zero": "no verdict; read layers counted in "
                                                                           "grid_split, unread layers named",
                             "no layer read": "no verdict, grid unread"},
                 "detail": "; ".join(
                     f"{k}: {s['locations']} locations, {s['pairs']} pairs, {s['nonzero']} non-zero, above floors "
                     f"{s['above_floor']}, independent {s['independent_nonzero']}, max "
                     f"{s.get('max_square', 'n/a')} {s.get('max_square_between', '')}, rival holds on "
                     f"{s['rival_holds_share']}" for k, s in sorted(layers.items()))
                           + f"; zero-valued rows in a table: {zero_val}"})
    extra["squares"] = layers
    extra["squares_2000_print"] = square_stats({f: x[2] for f, x in raw["cfr2000"]["tab"].items()})

    # B154-5
    maps = {"v2000->v2025": version_map(versions["v2000"], versions["v2025"]),
            "v2025->v2026": version_map(versions["v2025"], versions["v2026"])}
    if map_drop:
        for m in maps.values():
            for cell in m.values():
                if map_drop in cell:
                    cell.remove(map_drop)
    map_ok = True
    for name, m in maps.items():
        a, b = name.split("->")
        union = set(versions[a]) | set(versions[b])
        got = [f for cell in m.values() for f in cell]
        if sorted(got) != sorted(union):
            map_ok = False
    crow, same = class_counts(pp)
    named_ok = bool(crow) and all(r["classes_named"] == 4 for r in crow)
    printed = [r for r in crow if r["distinct_class_prices"] is not None]
    ok5 = map_ok and named_ok
    deltas = {n: {money(k): v for k, v in sorted(delta_dist(versions[n.split('->')[0]], versions[n.split('->')[1]],
                                                            m["changed"]).items())} for n, m in maps.items()}
    crit.append({"name": "B154-5", "kind": "bookkeeping", "passed": ok5,
                 "statement": "classes named per month, distinct class prices where printed (the Class I ESL price as its own "
                              "price), "
                              "every FIPS mapped to changed, same, added or removed between versions, months with "
                              "two class prices equal named",
                 "mapping": {"maps complete and four classes named every month": "PASS",
                             "a FIPS missing from a map, or a month naming another count": "FAIL"},
                 "detail": f"months {len(crow)}, four classes named in {sum(1 for r in crow if r['classes_named'] == 4)}; "
                           f"class prices printed in {len(printed)} months, distinct counts "
                           f"{dict(Counter(r['distinct_class_prices'] for r in printed))}; maps "
                           f"{ {n: {c: len(v) for c, v in m.items()} for n, m in maps.items()} }; complete {map_ok}; "
                           f"equal-price months {len(same)}{(' ' + str(same[:6])) if same else ''}"})
    extra["counts"] = {"months": crow, "equal_prices": same,
                       "maps": {n: {c: (v if c != "same" else len(v)) for c, v in m.items()} for n, m in maps.items()},
                       "delta_distribution": deltas}

    # B154-3b: the location dollars of the ten other orders (2026-10-29), appended last so that the earlier
    # criteria keep their places in the record
    arm = order_pool_arm(parsed)
    rel = [o for o, d in arm["per_order"].items() if d["months_with_T"]]
    ok3b = (not arm["failures"] and not cov_missing) if rel else None
    if not rel and (arm["failures"] or cov_missing):
        ok3b = False
    allT = [r for o in rel for r in arm["rows"][o] if "T" in r]
    crit.append({"name": "B154-3b", "kind": "own_reading", "passed": ok3b,
                 "statement": "the ten other orders, month by month: the handler and producer location lines as each "
                              "order prints them, assigned by their printed words (D54); where the handler line is the "
                              "adjustment from the base county (Northeast, Mideast, California: 'Location Adjustment to "
                              "Handlers'; Mideast to 2021: 'Class I Location Differential'; Appalachian: 'Location "
                              "Adjustment' under Class I), A, Bp, T = Bp - A and T / Bp in the Central convention; "
                              "where it is the whole differential at the plants' locations ('Class I Differential at "
                              "Location': Florida, Southeast, Pacific Northwest, Arizona) or the page does not say "
                              "(Southwest), both lines printed and T not formed; Upper Midwest prints the producer "
                              "line only",
                 "mapping": {"lines read for every order that prints them, every manifest file opened, no month with "
                             "two values for one line": "PASS (printing criterion)",
                             "a month with two different values for one line in unrevised files, a label printed with "
                             "no amount, or a manifest file not opened": "FAIL",
                             "no order prints the relative handler line": "no verdict"},
                 "detail": f"orders with T: {[OTHER_ORDERS[int(o)] for o in rel]}; months with T {len(allT)}; "
                           f"T = 0 in {sum(1 for r in allT if cents(Decimal(r['T'])) == 0)} of them (the scalar price "
                           f"field predicts T = 0); per order "
                           + "; ".join(f"{d['name']}: {d['coverage']}, handler line {d['handler_meaning'] or 'not printed'}"
                                       + (f", T months {d['months_with_T']}, T/Bp median {d['T_over_Bp_median']} "
                                          f"range {d['T_over_Bp_range']}, by version {d['by_version']}"
                                          if d["months_with_T"] else "")
                                       for o, d in sorted(arm["per_order"].items()))
                           + f"; parse failures {len(arm['failures'])}{(' ' + str(arm['failures'][:4])) if arm['failures'] else ''}"
                           f"; values replaced by a revised file {len(arm['revised'])} {arm['revised'][:4]}"
                           f"; lines on a page that names another order, against that order's own file: "
                           f"{arm['pages_of_another_order']['agree']} agree, "
                           f"{len(arm['pages_of_another_order']['off'])} off, "
                           f"{arm['pages_of_another_order']['own_line_absent']} with no own line"})
    extra["orders_pool"] = arm

    # depooling, printed only
    dep, depsum, c3src = depool_rows(ov, pp)
    extra["depooling"] = {"columns": ["month", "producer_receipts_lb", "class_I_pct", "class_II_pct",
                                      "class_III_pct", "class_IV_pct", "uniform_price",
                                      "class_III_above_uniform", "class_IV_above_uniform"],
                          "rows": dep, "summary": depsum, "class_III_source": c3src,
                          "note": "null where the Class III or Class IV price or the order's uniform price is not read; counts are above-in-M-of-N-readable"}
    extra["overview_errors"] = {str(y): d["errors"] for y, d in ov.items() if d["errors"]}
    return crit, extra, versions, bases


def flags(crit):
    return {c["name"]: c["passed"] for c in crit}


# --------------------------------------------------------------------------- selftest and mutation

def _copy_versions(vs):
    return {k: dict(v) for k, v in vs.items()}


def selftest():
    raw = load_tables()
    vs = build_versions(raw)
    ov = load_overviews()
    pp = load_pp()
    letters = letters_of(paragraphs(RAW / "rules" / "lii_1000_50.html"))
    o51 = {o: " ".join(paragraphs(RAW / "rules" / f"lii_{fn}_51.html")) for o, fn in ORDER_FILE.items()}
    crit, extra, _, bases = build(raw, vs, letters, o51, ov, pp)
    base = flags(crit)
    print("baseline flags", base)
    fails = []

    def expect(label, cond):
        print(("ok   " if cond else "FAIL ") + label)
        if not cond:
            fails.append(label)

    # fixtures with known answers
    expect("num reads (813,809.91) as negative", num("(813,809.91)") == Decimal("-813809.91"))
    expect("num reads 1,685,491.11- as negative", num("1,685,491.11-") == Decimal("-1685491.11"))
    expect("square_stats closed form on {a:1,b:1,c:2}",
           square_stats({"a": 100, "b": 100, "c": 200})["nonzero"] == 2)
    A, Bp = synthetic_pool([(320, 500, 0), (250, 300, 0), (320, 0, 900)], 320)
    expect("synthetic pool with non-Class-I milk at the base reads T = 0", t_from(A, Bp) == 0)
    A, Bp = synthetic_pool([(320, 500, 0), (250, 300, 400)], 320)
    expect("synthetic pool with non-Class-I milk off the base reads T != 0", t_from(A, Bp) != 0)

    # B154-0 seeds
    r2 = json.loads(json.dumps({k: {**t, "tab": {f: list(x) for f, x in t["tab"].items()}} for k, t in raw.items()}))
    for t in r2.values():
        t["tab"] = {f: tuple(x) for f, x in t["tab"].items()}
    v2 = _copy_versions(vs)
    v2["v2026"].pop(sorted(v2["v2026"])[10])
    c, *_ = build(raw, v2, letters, o51, ov, pp, bases)
    expect("B154-0 flips when a row is dropped", flags(c)["B154-0"] is False)
    v2 = _copy_versions(vs)
    nm, st, _ = v2["v2026"][MORGAN]
    v2["v2026"][MORGAN] = (nm, st, 390)
    c, *_ = build(raw, v2, letters, o51, ov, pp, bases)
    expect("B154-0 flips when Morgan, OH goes back to 3.90", flags(c)["B154-0"] is False)
    rr = load_tables()
    rr["lii"]["bad"].append({"row": ["X", "OH", "39999", "3.805"], "why": "value not on the two-decimal format"})
    c, *_ = build(rr, vs, letters, o51, ov, pp, bases)
    expect("B154-0 flips on a three-decimal value", flags(c)["B154-0"] is False)

    # B154-0b seeds
    b2 = dict(bases)
    b2[1] = JACKSON
    c, *_ = build(raw, vs, letters, o51, ov, pp, b2)
    expect("B154-0b flips when an order's base county is swapped", flags(c)["B154-0b"] is False)
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, jitter={((2015, 6), 33): 10})
    expect("B154-0b flips when one order-month gains 0.10", flags(c)["B154-0b"] is False)

    # B154-0b: a whole row read from another order fails; a lone Class I price slip is named
    import copy
    ov2 = copy.deepcopy(ov)
    for k, s in ov2[2015]["orders"][30]["series"].items():
        if k in ov2[2015]["orders"][33]["series"]:
            ov2[2015]["orders"][33]["series"][k][5] = s[5]
    c, x, *_ = build(raw, vs, letters, o51, ov2, pp, bases)
    expect("B154-0b flips when Mid-East 2015-06 carries Upper Midwest's whole row", flags(c)["B154-0b"] is False)
    ov2 = copy.deepcopy(ov)
    ov2[2015]["orders"][33]["series"]["class1"][5] = ov2[2015]["orders"][30]["series"]["class1"][5]
    c, x, *_ = build(raw, vs, letters, o51, ov2, pp, bases)
    expect("B154-0b names a lone Class I price slip (rest of the row its own) and adds it to the list",
           flags(c)["B154-0b"] is True and len(x["base_prices"]["repeats_other_order"])
           == len(extra["base_prices"]["repeats_other_order"]) + 1)

    # B154-1 seeds
    l2 = dict(letters)
    l2["h"] = l2["h"] + " plus the adjusted Class I differential specified in § 1000.52"
    c, *_ = build(raw, vs, l2, o51, ov, pp, bases)
    expect("B154-1 flips when Class III gains a county term", flags(c)["B154-1"] is False)
    l2 = dict(letters)
    l2["e"] = l2["e"] + " § 1000.52"
    l2["b"] = l2["b"].replace("1000.52", "1000.5x")
    c, *_ = build(raw, vs, l2, o51, ov, pp, bases)
    expect("B154-1 flips when the citation moves into the Class II paragraph", flags(c)["B154-1"] is False)
    c, *_ = build(raw, vs, {}, o51, ov, pp, bases)
    expect("B154-1 gives no verdict when the text is not read", flags(c)["B154-1"] is None)
    l2 = dict(letters)
    l2["r"] = l2["r"] + " plus the differential in § 1000.52"
    c, *_ = build(raw, vs, l2, o51, ov, pp, bases)
    expect("B154-1 flips when the ESL term gains the county differential", flags(c)["B154-1"] is False)
    o75 = {o: " ".join(paragraphs(RAW / "rules" / f"lii_{fn}_75.html")) for o, fn in ORDER_FILE.items()}
    o75[32] = o75[32] + " for Class III milk only"
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, order_75=o75)
    expect("B154-1 flips when a .75 producer adjustment is tied to Class III", flags(c)["B154-1"] is False)
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, order_61={})
    expect("B154-1 gives no verdict when the seller-side .61 text is not read", flags(c)["B154-1"] is None)

    # B154-2 seeds
    const = {k: {f: (x[0], x[1], 300) for f, x in v.items()} for k, v in vs.items()}
    st = square_stats({f: x[2] for f, x in const["v2026"].items()})
    cell = layer_cell(st, st["independent_nonzero"] > 0)
    expect("B154-2 reads a constant table as the rival holding, with no verdict for us",
           st["rival_holds_share"] == "1.000000" and cell[0] == "unread")
    st = square_stats({"a": 300, "b": 300})
    expect("B154-2 maps a zero record against a non-zero table to grid C",
           layer_cell(st, True)[0] == "C" and rival_verdict({"x": "C", "y": "B"}) is False)
    expect("B154-2 gives no verdict when one layer is B and another unread (11c)",
           rival_verdict({"x": "B", "y": "unread"}) is None)
    expect("B154-2 pair cells: a table read against itself has only A and B, A = equal-value pairs",
           pair_cells({"a": 100, "b": 100, "c": 200}, {"a": 100, "b": 100, "c": 200}) == {"A": 1, "B": 2})
    expect("B154-2 pair cells: a reading flat where the framework is not lands in C",
           pair_cells({"a": 100, "b": 200}, {"a": 50, "b": 50}) == {"C": 1})

    def drop_v2000(rows):
        return [dict(q) for q in rows if version_of(tuple(int(x) for x in q["month"].split("-"))) != "v2000"]
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, plant_override=drop_v2000)
    r2 = {x["name"]: x for x in c}["B154-2"]
    expect("B154-2 gives no verdict when the v2000 plant-list layer has nothing to read, and names it",
           r2["passed"] is None and r2["grid"] == "mixed" and "v2000/central_lists: layer unread" in r2["grid_note"])
    v2 = _copy_versions(vs)
    v2["v2025"][SHANNON] = ("SHANNON", "SD", 0)
    st = square_stats({f: x[2] for f, x in v2["v2025"].items()})
    expect("B154-2 reads 7.40 with the Shannon placeholder back, and names it",
           st["max_square"] == "7.40" and st["max_square_between"][0] == SHANNON)
    r2b = {x["name"]: x for x in crit}["B154-2"]
    cur = {f: x[2] for f, x in vs[VERSION_CUTS[-1][1]].items()}
    want = pair_cells(cur, cur)
    expect("B154-2 grid_split is the current county table's pair counts, recomputed from the table",
           r2b.get("grid_split") == want and r2b["grid"] == ("mixed" if len(want) > 1 else next(iter(want))))
    v3 = _copy_versions(vs)
    ks = sorted(v3["v2000"])
    k0 = ks[5]
    k1 = next(k for k in ks if v3["v2000"][k][2] != v3["v2000"][k0][2])
    nm0, st0, _d0 = v3["v2000"][k0]
    v3["v2000"][k0] = (nm0, st0, v3["v2000"][k1][2])      # one v2000 row takes another county's value
    c3, x3, *_ = build(raw, v3, letters, o51, ov, pp, bases)
    r3 = {x["name"]: x for x in c3}["B154-2"]
    expect("B154-2: moving one v2000 value moves the three-version sum and leaves grid_split as it is",
           r3.get("grid_split") == r2b.get("grid_split")
           and x3["grid_split_three_versions"]["split"] != extra["grid_split_three_versions"]["split"])
    expect("B154-2 on the real tables: current maximum 5.70",
           extra["squares"]["v2026/county_table"]["max_square"] == "5.70")

    # B154-3 seeds
    first = sorted(pp)[0]
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, cover_drop=first)
    expect("B154-3 flips when a month is taken out of the coverage", flags(c)["B154-3"] is False)

    # B154-4 seeds
    def move_county(rows):
        out = [dict(q) for q in rows]
        for q in out:
            if q["resolved_fips"] == "08123":
                q["resolved_fips"] = "19153"
                break
        return out
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, plant_override=move_county)
    expect("B154-4 flips when one plant's county is swapped", flags(c)["B154-4"] is False)

    def shift_month(rows):
        out = [dict(q) for q in rows]
        for q in out:
            if q["month"] == "2026-06":
                q["month"] = "2025-04"
        return out
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, plant_override=shift_month)
    expect("B154-4 flips when a month's list is matched to the wrong version", flags(c)["B154-4"] is False)

    def bump_diff(n):
        def f(rows):
            out = [dict(q) for q in rows]
            hit = 0
            for q in out:
                if q["month"] == "2012-03" and "diff" in q and q.get("resolved_fips") not in (None, JACKSON):
                    q["diff"] += 10
                    hit += 1
                    if hit == n:
                        break
            return out
        return f
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, plant_override=bump_diff(1))
    expect("B154-4 names one misread differential and the count shows it",
           flags(c)["B154-4"] is True and len(x["plants"]["differential_misprint"])
           == len(extra["plants"]["differential_misprint"]) + 1)
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, plant_override=bump_diff(2))
    expect("B154-4 flips when two differentials in one month are misread", flags(c)["B154-4"] is False)

    # B154-4b and the eleven-order layer (ruled 2026-10-29). The real lists carry rows off the table, so
    # B154-4b's baseline is FAIL; each seed is planted on the lists with those rows taken out (which reads
    # PASS), so that a seed has a flag to flip, and the count of off rows is checked on the real lists too.
    orders = load_orders()
    f4b = flags(crit)["B154-4b"]
    base_off = len(extra["orders"]["off"])
    expect("B154-4b reads a verdict on the real lists (rows with a county exist)", f4b is not None)

    def _v(q):
        return version_of(tuple(int(t) for t in q["month"].split("-")))

    b51 = load_51b()

    def clean(rows):
        return [dict(q) for q in rows if not ("abs" in q and table_key(q) in vs[_v(q)]
                                              and q["abs"] not in [x for x, _h in b_candidates(
                                                  q, table_key(q), vs[_v(q)][table_key(q)][2], b51)])]
    c, xc, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean)
    expect("B154-4b reads PASS once the off rows are taken out", flags(c)["B154-4b"] is True)

    def swap_order_county(rows):
        out = clean(rows)
        for q in out:
            if q["order"] == 1030 and q.get("resolved_fips") == "55117" and q["month"] == "2015-03":
                q["resolved_fips"] = "27053"      # Sheboygan, WI read as Hennepin, MN
                break
        return out
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=swap_order_county)
    expect("B154-4b flips when one Upper Midwest plant's county is swapped", flags(c)["B154-4b"] is False)

    def shift_order_month(rows):
        out = clean(rows)
        for q in out:
            if q["order"] == 1051 and q["month"] == "2026-09":
                q["month"] = "2024-09"
        return out
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=shift_order_month)
    expect("B154-4b flips when California's 2026-09 list is matched to the v2000 table", flags(c)["B154-4b"] is False)

    def bump(state, month):
        def f(rows):
            out = clean(rows)
            for q in out:
                if q["state"] == state and q["month"] == month and q.get("resolved_fips") and "abs" in q:
                    q["abs"] += 30
                    break
            return out
        return f
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=bump("WI", "2015-03"))
    expect("B154-4b flips when a Wisconsin row reads 0.30 above the table", flags(c)["B154-4b"] is False)
    expect("B154-2: that county leaves the pooled four-cell count as disputed, and no C appears",
           len(x["squares"]["v2000/eleven_order_lists"]["disputed_locations"])
           == len(xc["squares"]["v2000/eleven_order_lists"]["disputed_locations"]) + 1
           and "'C'" not in {y["name"]: y for y in c}["B154-2"]["grid_note"].split("eleven_order_lists: ")[1][:200])

    def bump_real(rows):
        out = [dict(q) for q in rows]
        for q in out:
            if q["state"] == "WI" and q["month"] == "2015-03" and q.get("resolved_fips") and "abs" in q:
                q["abs"] += 30
                break
        return out
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=bump_real)
    expect("B154-4b on the real lists: one more off row is counted", len(x["orders"]["off"]) == base_off + 1)
    # the .51(b) text (ruled 2026-10-29, read): a row in the (b) era is judged against it
    expect("the .51(b) text is read: three orders, the prints give one table each, the base-county entry equals "
           "the overview footnote",
           b51["read"] and all(r["prints_give_one_table"] and [r["base_county_entry"]] == r["overview_footnote"]
                               for r in xc["orders"]["rule_51b"]["orders"].values()))
    n_bagree = len(xc["orders"]["b_adjustment_agree"])
    expect("B154-4b counts rows equal to the table plus their .51(b) entry as agreeing (none named without verdict)",
           n_bagree > 0 and not xc["orders"]["b_adjustment_named"])

    def bump_b(cents_):
        def f(rows):
            out = clean(rows)
            for q in out:
                if q["order"] == 1005 and "abs" in q and q.get("resolved_fips") and q["month"] <= SE_B_WINDOW[1]:
                    q["abs"] += cents_
                    break
            return out
        return f
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=bump_b(10))
    expect("B154-4b flips when an Appalachian row of the (b) era reads 0.10 off its 1000.52-plus-(b) value",
           flags(c)["B154-4b"] is False)
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean, b51=None)
    expect("with the .51(b) text not on disk the same rows are named with no verdict and the flag holds",
           flags(c)["B154-4b"] is True and len(x["orders"]["b_adjustment_named"]) == n_bagree)

    def drop_b_from_um(rows):
        out = clean(rows)
        for q in out:
            if q["order"] == 1030 and q.get("resolved_fips") == "21035" and q["month"] >= "2020-08" \
                    and q["month"] <= SE_B_WINDOW[1]:
                q["abs"] -= 30                      # Calloway printed at 1000.52 alone: allowed for a 1030 list
                break
        return out
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=drop_b_from_um)
    expect("an Upper Midwest row at 1000.52 alone in a (b) county still agrees (that order has no (b))",
           flags(c)["B154-4b"] is True)
    expect("B154-2: a county carrying two rule values in one version (Calloway, KY) leaves the four-cell count",
           "21035" in extra["squares"]["v2000/eleven_order_lists"]["disputed_locations"]
           and "21035" not in extra["squares"]["v2026/eleven_order_lists"]["disputed_locations"])
    expect("B154-2: Appalachian counties priced at 1000.52 plus (b) enter the four-cell count (none disputed)",
           extra["squares"]["v2000/order1005_lists"]["disputed_locations"] == []
           and extra["squares"]["v2000/order1005_lists"]["locations"] > 1)

    # the Census place file (ruled 2026-10-29)
    places = load_places()
    expect("place file: a place in one county gives it, a place in four counties gives four candidates",
           list(places[("TN", norm("Athens"))]) == ["47107"] and len(places[("NC", norm("High Point"))]) == 4)
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, places=None)
    expect("without the place file the city-only rows stay as before (1,609 unresolved)",
           len(x["orders"]["county_unresolved"]) == 1609 and flags(c)["B154-4b"] is False)
    row0 = next(q for q in order_rows(orders[0], vs, raw, resolve_plants(pp, vs, raw), places, b51)
                if q["order"] == 1005 and q.get("resolved_by", "").startswith("Census") and q["month"] == "2022-06")
    p2 = {k: dict(v) for k, v in places.items()}
    k0 = (row0["state"], norm(row0["city"]))
    wrong = next(f for f, x_ in sorted(vs["v2000"].items()) if x_[1] == row0["state"] and all(
        val != row0["abs"] for val, _h in b_candidates(row0, f, x_[2], b51)))
    p2[k0] = {wrong: "seeded place"}
    base_rows = order_rows(orders[0], vs, raw, resolve_plants(pp, vs, raw), places, b51)
    base_off_keys = {(q["file"], q["name"], q["month"]) for q in base_rows} - {
        (q["file"], q["name"], q["month"]) for q in clean(base_rows)}

    def clean_fixed(rows):      # takes out the rows off in the unseeded run, and only those
        return [dict(q) for q in rows if (q["file"], q["name"], q["month"]) not in base_off_keys]
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean_fixed, places=p2)
    expect(f"B154-4b flips when the place file puts {row0['city']}, {row0['state']} in another county ({wrong})",
           flags(c)["B154-4b"] is False)
    p2[k0] = {wrong: "seeded place", row0["resolved_fips"]: "seeded place"}
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean_fixed, places=p2)
    expect("a place seeded into two counties leaves its rows unresolved and names both candidates",
           flags(c)["B154-4b"] is True and any(row0["city"] in k and "several counties" in k
                                                for k in x["orders"]["census_not_resolved"]))

    # second round (ruled 2026-10-29): a place across counties at one price; a unique Census name variant
    xo = extra["orders"]
    cc = Counter()
    for k, n_ in xo["census_cross_county_same_price"].items():
        cc[k.split(" (")[0]] += n_
    expect("cross-county places at one price resolve (Charleston SC 23, North Charleston SC 8, High Point NC "
           "132 in v2000) and Portland OR and High Point v2025/v2026 stay unresolved with each county's price",
           cc == {"1005 Charleston, SC": 23, "1005 North Charleston, SC": 8, "1005 High Point, NC": 132}
           and any(k.startswith("1124 Portland, OR") and "prices differ" in k and "41067 Portland city 2.20" in k
                   for k in xo["census_not_resolved"])
           and any(k.startswith("1005 High Point, NC (v2025)") and "prices differ" in k
                   for k in xo["census_not_resolved"]))
    expect("name variant: Boise, ID is the Census place Boise City city in one county, its line kept",
           xo["census_name_variant"].get("1124 Boise, ID", {}).get("census_place") == ["Boise City city"]
           and any(ln.startswith("line 6428: ID|16|001|") for ln in
                   xo["census_name_variant"]["1124 Boise, ID"]["source_lines"]))
    rows_r2 = order_rows(orders[0], vs, raw, resolve_plants(pp, vs, raw), places, b51)
    ch0 = next(q for q in rows_r2 if q["order"] == 1005 and q.get("city") == "Charleston" and q["state"] == "SC")
    kch = ("SC", norm("Charleston"))
    differs = next(f for f, x_ in sorted(vs[_v(ch0)].items()) if x_[1] == "SC" and f not in places[kch]
                   and rule_values(ch0, f, vs, b51) != rule_values(ch0, "45019", vs, b51))
    p3 = copy.deepcopy(places)
    p3[kch] = {"45019": "Charleston city", differs: "seeded place"}
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean_fixed, places=p3)
    expect(f"a place seeded across two counties at different prices ({differs}) is not resolved, and both "
           "counties' prices are printed",
           flags(c)["B154-4b"] is True
           and not any(k.startswith("1005 Charleston, SC") for k in x["orders"]["census_cross_county_same_price"])
           and any(k.startswith("1005 Charleston, SC") and "prices differ" in k and differs in k
                   for k in x["orders"]["census_not_resolved"]))
    two_same = None
    for f1, x1 in sorted(vs[_v(ch0)].items()):
        if x1[1] != "SC" or f1 in places[kch] or rule_values(ch0, f1, vs, b51) is None \
                or ch0["abs"] in rule_values(ch0, f1, vs, b51):
            continue
        f2 = next((f for f, x2 in sorted(vs[_v(ch0)].items()) if x2[1] == "SC" and f != f1 and f not in places[kch]
                   and all(rule_values(r, f, vs, b51) == rule_values(r, f1, vs, b51) for r in rows_r2
                           if r["order"] == 1005 and r.get("city") == "Charleston" and r["state"] == "SC")), None)
        if f2:
            two_same = (f1, f2)
            break
    p3[kch] = {two_same[0]: "seeded place", two_same[1]: "seeded place"}
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean_fixed, places=p3)
    expect(f"a place seeded across two counties at one price that is not the printed one ({two_same}) resolves, "
           "and B154-4b flips", flags(c)["B154-4b"] is False
           and any(k.startswith("1005 Charleston, SC") for k in x["orders"]["census_cross_county_same_price"]))
    p4 = copy.deepcopy(places)
    p4[("ID", norm("Boise Heights"))] = {"16027": "Boise Heights CDP"}
    p4.lines[("ID", norm("Boise Heights"))] = {"16027": (0, "ID|16|027|seeded|00000|00000000|Boise Heights CDP")}
    p4.words["ID"][norm("Boise Heights")] = ("BOISE", "HEIGHTS")
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean_fixed, places=p4)
    expect("a second Census place whose name begins with Boise makes the variant not unique: Boise rows stay "
           "unresolved and both candidates are named",
           "1124 Boise, ID" not in x["orders"]["census_name_variant"]
           and any(k.startswith("1124 Boise, ID") and "no unique Census name variant" in k and "Boise City city" in k
                   and "Boise Heights CDP" in k for k in x["orders"]["census_not_resolved"]))
    boise = next(q for q in rows_r2 if q["order"] == 1124 and q.get("city") == "Boise")
    wrong_id = next(f for f, x_ in sorted(vs[_v(boise)].items()) if x_[1] == "ID" and x_[2] != boise["abs"])
    p5 = copy.deepcopy(places)
    p5[("ID", norm("Boise City"))] = {wrong_id: "Boise City city"}
    p5.lines[("ID", norm("Boise City"))] = {wrong_id: (0, "seeded")}
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=clean_fixed, places=p5)
    expect(f"B154-4b flips when the unique name variant puts Boise in another county ({wrong_id})",
           flags(c)["B154-4b"] is False)
    parsed, errs = orders
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=(parsed[1:], errs), order_override=clean)
    expect("B154-4b flips when a manifest file is left out of the coverage table", flags(c)["B154-4b"] is False)

    def flat_orders(rows):
        out = [dict(q) for q in rows]
        for q in out:
            if "abs" in q:
                q["abs"] = 200
        return out

    def flat_central(rows):
        out = [dict(q) for q in rows]
        for q in out:
            q["diff"], q["rel"] = 200, 0
        return out
    c, x, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=orders, order_override=flat_orders,
                     plant_override=flat_central)
    r2f = {y["name"]: y for y in c}["B154-2"]
    expect("B154-2 maps a flat pooled list against a non-zero table to C and FAIL",
           r2f["passed"] is False and "eleven_order_lists: layer C" in r2f["grid_note"])
    expect("B154-2: a single order's layer whose answer flips across the floors does not gate the verdict",
           any(k.endswith("/order1051_lists") and v["above_floor"]["50"] == 0 and v["above_floor"]["1"] > 0
               for k, v in extra["squares"].items()) and flags(crit)["B154-2"] is True)
    expect("B154-2: the six-layer three-version sum is the one recorded before the extension",
           extra["grid_split_three_versions"]["split"] == {"A": 623482, "B": 13873910})

    # B154-3b (2026-10-29): the ten orders' location dollars
    x3b = extra["orders_pool"]
    expect("B154-3b reads T on the four orders whose handler line is the relative one, and nowhere else",
           sorted(o for o, d in x3b["per_order"].items() if d["months_with_T"]) == ["1001", "1005", "1033", "1051"]
           and flags(crit)["B154-3b"] is True)
    expect("B154-3b: the Pacific Northwest lines printed on an Arizona page equal its own file",
           x3b["pages_of_another_order"]["agree"] >= 2 and not x3b["pages_of_another_order"]["off"])

    def seeded(fn):
        pz = copy.deepcopy(parsed)
        fn(pz)
        c_, x_, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=(pz, errs))
        return flags(c_)["B154-3b"], x_["orders_pool"]

    def first_with(pz, order):
        return next(r for r in pz if r["order"] == order and r.get("pool"))

    def dup_value(pz):
        r = first_with(pz, 1005)
        h = next(p for p in r["pool"] if p["side"] == "handler")
        r["pool"].append({**h, "cents": h["cents"] + 1})
    f3, _ = seeded(dup_value)
    expect("B154-3b flips when an unrevised file prints one line twice with two values", f3 is False)

    def no_amount(pz):
        r = first_with(pz, 1001)
        r["pool"][0] = {**r["pool"][0], "cents": None}
    f3, _ = seeded(no_amount)
    expect("B154-3b flips on a label printed with no amount", f3 is False)

    def relabel(pz):
        for r in pz:
            for p in r.get("pool", []):
                if r["order"] == 1005 and p["side"] == "handler":
                    p["meaning"] = "at_location"
    f3, a3 = seeded(relabel)
    expect("B154-3b: an Appalachian handler line read as the differential at location leaves the T orders",
           f3 is True and a3["per_order"]["1005"]["months_with_T"] == 0
           and a3["per_order"]["1001"]["months_with_T"] == x3b["per_order"]["1001"]["months_with_T"])

    def cross_off(pz):
        for r in pz:
            for p in r.get("pool", []):
                if p.get("page_order") and 1000 + p["page_order"] != r["order"]:
                    p["cents"] += 100
                    return
    f3, _ = seeded(cross_off)
    expect("B154-3b flips when another order's page in a file disagrees with that order's own file", f3 is False)

    def no_relative(pz):
        for r in pz:
            r["pool"] = [p for p in r.get("pool", []) if p["meaning"] != "relative"]
    f3, _ = seeded(no_relative)
    expect("B154-3b gives no verdict when no order prints the relative handler line", f3 is None)
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, orders=(parsed[2:], errs))
    expect("B154-3b flips when a manifest file is not opened", flags(c)["B154-3b"] is False)
    expect("B154-3b: Northeast 2026-06 reads A and T from the printed lines (A -4658418.96, Bp -21003509.18)",
           next(r for r in x3b["rows"]["1001"] if r["month"] == "2026-06")["A"] == "-4658418.96"
           and next(r for r in x3b["rows"]["1001"] if r["month"] == "2026-06")["T"] == "-16345090.22")

    # depooling: a month whose Class III price cannot be read carries null, not false
    pp2 = {k: dict(r) for k, r in pp.items()}
    pp2["2022-01"] = dict(pp2["2022-01"], class_prices={k: v for k, v in pp["2022-01"]["class_prices"].items()
                                                        if k != "III"}, sup=None)
    ov3 = copy.deepcopy(ov)
    ov3[2022]["orders"][32]["series"]["sup"][0] = None
    dep2, sum2, _ = depool_rows(ov3, pp2)
    row = [r for r in dep2["32"] if r[0] == "2022-01"][0]
    expect("depooling: an unread Class III month is null and named, and leaves the denominator",
           row[7] is None and "2022-01" in sum2["32"]["class_III_unread_months"]
           and sum2["32"]["class_III_readable"] == extra["depooling"]["summary"]["32"]["class_III_readable"] - 1)

    # B154-5 seed
    c, *_ = build(raw, vs, letters, o51, ov, pp, bases, map_drop=MORGAN)
    expect("B154-5 flips when a FIPS is taken out of the map", flags(c)["B154-5"] is False)

    # the seeds must not leak: the real run's flags are what they are
    expect("baseline has no None where a reading exists",
           all(base[k] is not None for k in ("B154-0", "B154-0b", "B154-1", "B154-3", "B154-4", "B154-5")))
    print("selftest", "passed" if not fails else f"FAILED {fails}")
    return not fails


def mutation():
    """Implementation faults planted in the inputs; at least one flag has to move each time."""
    raw = load_tables()
    vs = build_versions(raw)
    ov = load_overviews()
    pp = load_pp()
    letters = letters_of(paragraphs(RAW / "rules" / "lii_1000_50.html"))
    o51 = {o: " ".join(paragraphs(RAW / "rules" / f"lii_{fn}_51.html")) for o, fn in ORDER_FILE.items()}
    base_c, base_x, _, bases = build(raw, vs, letters, o51, ov, pp)
    base = flags(base_c)
    results = []

    def run(label, **kw):
        c, x, *_ = build(**kw)
        f = flags(c)
        moved = {k: (base[k], f[k]) for k in f if f[k] != base[k]}
        extra_move = ""
        if not moved:
            a = base_x["squares"]["v2025/county_table"].get("max_square")
            b = x["squares"]["v2025/county_table"].get("max_square")
            if a != b:
                moved = {"v2025 max square": (a, b)}
        if not moved and len(base_x["orders"]["off"]) != len(x["orders"]["off"]):
            moved = {"B154-4b off rows": (len(base_x["orders"]["off"]), len(x["orders"]["off"]))}
        results.append((label, moved))
        print(("caught " if moved else "MISSED ") + label, moved, extra_move)

    v2 = _copy_versions(vs)
    v2["v2025"][SHANNON] = ("SHANNON", "SD", 0)
    v2["v2026"][SHANNON] = ("SHANNON", "SD", 0)
    run("Shannon placeholder kept", raw=raw, versions=v2, letters=letters, order_51=o51, ov=ov, pp=pp, bases=bases)
    v2 = _copy_versions(vs)
    nm, st, _ = v2["v2026"][MORGAN]
    v2["v2026"][MORGAN] = (nm, st, 390)
    run("Morgan back to 3.90", raw=raw, versions=v2, letters=letters, order_51=o51, ov=ov, pp=pp, bases=bases)
    b2 = dict(bases)
    b2[32] = "17031" if bases[32] != "17031" else "29095"
    run("Central base county swapped", raw=raw, versions=vs, letters=letters, order_51=o51, ov=ov, pp=pp, bases=b2)
    v2 = _copy_versions(vs)
    v2["v2025"] = dict(vs["v2000"])
    run("v2025 read as v2000", raw=raw, versions=v2, letters=letters, order_51=o51, ov=ov, pp=pp, bases=bases)
    def rel_as_abs(rows):
        out = [dict(q) for q in rows]
        for q in out:
            if q["order"] == 1051 and "rel" in q and "diff" not in q:
                q["abs"] = q["rel"]          # the printed adjustment read as the differential, base dropped
        return out
    run("California adjustment read without its printed base", raw=raw, versions=vs, letters=letters,
        order_51=o51, ov=ov, pp=pp, bases=bases, order_override=rel_as_abs)

    def county_column_shift(rows):
        out = [dict(q) for q in rows]
        for q in out:
            if q["order"] == 1030 and q.get("resolved_fips"):
                q["resolved_fips"] = q["resolved_fips"][:2] + "%03d" % ((int(q["resolved_fips"][2:]) + 2) % 1000)
        return out
    run("Upper Midwest county resolved two codes off", raw=raw, versions=vs, letters=letters, order_51=o51, ov=ov,
        pp=pp, bases=bases, order_override=county_column_shift)
    b2_ = load_51b()
    t5, t7 = b2_["orders"][1005]["table"], b2_["orders"][1007]["table"]
    b2_["orders"][1005]["table"], b2_["orders"][1007]["table"] = t7, t5
    run(".51(b) tables of Appalachian and Southeast read the wrong way round", raw=raw, versions=vs, letters=letters,
        order_51=o51, ov=ov, pp=pp, bases=bases, b51=b2_)
    run("a place across counties keyed to its first county without the price check", raw=raw, versions=vs,
        letters=letters, order_51=o51, ov=ov, pp=pp, bases=bases, same_price_check=False)
    missed = [lab for lab, m in results if not m]
    print("mutation", "all caught" if not missed else f"MISSED {missed}")
    return not missed


# --------------------------------------------------------------------------- run

def run():
    crit, extra, versions, bases = build()
    for c in crit:
        print(f"{c['name']:8s} {c['kind']:12s} {c['passed']}  {c['detail'][:400]}")
    cfg = {
        "versions": {"v2000": "7 CFR 1000.52, 2024 print (equal to the 2000 print county by county, plus Broomfield, "
                              "CO); in force 2000-01 to 2025-05",
                     "v2025": "7 CFR 1000.52, 2026 print, Shannon County, SD row (46113, 0.00 placeholder) removed; "
                              "2025-06 to 2026-08",
                     "v2026": "eCFR current text (91 FR 59047: Morgan County, OH 3.90 to 3.80, Shannon row deleted); "
                              "2026-09 on"},
        "fips_read_as": {"PIERCE WA 5303": "53053"},
        "floors_cents": list(FLOORS),
        "floor_reason": "two-decimal publication grid of the county table and the announcements",
        "window": [ym_str(FIRST_MONTH), ym_str(LAST_MONTH)],
        "orders_and_base_counties": extra.get("base_counties"),
        "base_county_not_on_disk": {"135": "Western order, terminated 2004-04-01"},
        "order_adjustment_source": "each year's all-order overview footnote (1005.51(b), 1006.51(b), 1007.51(b)); "
                                   "applied from May 2008 and in every year whose overview carries the footnote",
        "sign_convention": {"A": "handler (Class I) location dollars as printed in the pool computation; negative "
                                 "when Class I plants sit below the base county",
                            "Bp": "minus the producer location dollars the pool adds back; negative when producers "
                                  "are paid below the base county",
                            "T": "Bp - A",
                            "check": "2026-06: A = -813809.91, Bp = -5801163.19, T = -4987353.28"},
        "plant_list_formats": {"county_name": "2000-01 to 2021-06 (except 2010-02)", "city_only": "2021-07 to 2024-03",
                               "fips": "2024-04 on"},
        "city_to_county": "a row with no county printed, or whose printed county name matches no county, takes "
                          "the county the same listing printed for that city and state in another row, when that "
                          "county is unique",
        "other_orders": {"ruled": "2026-10-29: the ten other orders' announcements, record layer extended from one "
                                  "order to eleven",
                         "files": "data/raw/b154/<part>/, manifest data/raw/b154/b154_orders_manifest.json "
                                  "(experiments/b154_fetch_orders.py)",
                         "layouts_read": {"state_county_rate": "Upper Midwest, State County Rate columns; Rate is the "
                                                               "differential at the plant's county",
                                          "fips_loc_adj": "California, FIPS and Loc. Adj. (2018-2019: Plant "
                                                          "Differential and Adjustment from Base Differential)",
                                          "city_diff_adj": "Pacific Northwest, Class I Differential and Location "
                                                           "Adjustment from King County, WA, by city",
                                          "city_diff": "Appalachian, CLASS 1 DIFFERENTIAL by city"},
                         "county_of_a_city_only_row": "the county another row printed for the same city and state, this "
                                                      "order's lists first, then the other ten; unique only",
                         "pooled_layer": "eleven_order_lists: every county with a printed differential in any order's "
                                         "list that version; Central rows that print only the adjustment take the "
                                         "Jackson differential printed in the same announcement's footer",
                         "comparability": "1000.52 is one table for all orders, written by the common rule; the "
                                          "differential at a county does not depend on which order prints it (D55)",
                         "census_place_file": "ruled 2026-10-29: data/raw/b154/census/national_place_by_county2020.txt "
                                              "(manifest data/raw/b154/b154_census_rules_manifest.json); a city-only "
                                              "row still unresolved takes the county of the Census 2020 place of the "
                                              "printed name in the printed state when that place lies in one county; "
                                              "a place in several counties, or no place of the name, leaves the row "
                                              "unresolved and names the candidates",
                         "census_cross_county": "ruled 2026-10-29: a place in several counties gives the row its "
                                                "value when every one of those counties carries the same rule value "
                                                "(1000.52, and the .51(b) entry where it applies) under the row's "
                                                "order and month; the location is the counties joined by '+', the "
                                                "table looked up at the first; values not all equal leave the row "
                                                "unresolved with each county's value printed",
                         "census_name_variant": "ruled 2026-10-29: no place of the printed name in the printed state: "
                                                "a place of that state whose name is the printed name's words "
                                                "followed by more words, unique only; the Census line is recorded; "
                                                "none, or more than one, leaves the row unresolved",
                         "rule_51b": "ruled 2026-10-29: 1005.51(b), 1006.51(b), 1007.51(b) as printed in the 2009, "
                                     "2020 and 2024 CFR (govinfo) and in the eCFR text in force on 2025-02-01; the "
                                     "four give one table per order on (state, FIPS, adjustment); each carries the one "
                                     "source note of March 17, 2008; read for months 2008-05 to 2025-05. An "
                                     "Appalachian, Florida or Southeast list prices a county at 1000.52 plus its own "
                                     "(b) entry; another order's list at 1000.52 alone or 1000.52 plus the entry of "
                                     "the order whose table lists the county (the three tables share no county)"},
        "single_order_layer_ruling": "ruled 2026-10-29: a single order's list is printed "
                                     "with its own cell and does not gate B154-2; basis D55, 1000.52 is one table "
                                     "shared by all orders",
    }
    rec = {"stage": STAGE, "config": cfg, "criteria": crit,
           "tables": extra["tables"], "rule_text": extra["rule_text"], "base_prices": extra["base_prices"],
           "central": extra["central"], "plants": extra["plants"], "squares": extra["squares"],
           "counts": extra["counts"], "depooling": extra["depooling"],
           "squares_2000_print": extra["squares_2000_print"],
           "overview_parse_errors": extra["overview_errors"], "orders": extra["orders"],
           "orders_pool": extra["orders_pool"]}
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    from safe_write import create, rewrite
    if OUT.exists():
        rewrite(OUT, "B154 record", lambda _old: text, session=SESSION)
    else:
        create(OUT, "B154 record", text, session=SESSION)
    print("wrote", OUT.name, len(text), "bytes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mutation", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.mutation:
        sys.exit(0 if mutation() else 1)
    if a.run:
        run()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
