"""Locate template rows on a DAI data page by the printed row lattice.

Why not the legend. The workbook prints legend pages that carry template row
numbers, but a legend page is not reliably the legend of the data pages that
follow it: applying legend p177's grid to data page p195 puts that page's crop
area row at template row 2.20, which is not an integer, so the two are not the
same sheet. Pairing by page order produced a one-row error on cotton that read
out as a plausible price, which is the failure this module removes.

What it uses instead. Rows sit on a lattice of fixed pitch. Fitting row number
against y on four legend pages gives 13.920 to 13.921 points with a maximum
residual of 0.02 points, so the pitch is a property of the document, not a
per-page estimate; estimating it per page from median gaps gives 12.5 to 15.5
and drifts by whole rows. The pitch is therefore fixed and one anchor on the
page itself sets the offset.

Anchors, both value-identified, both independently known:
  crop area   template row 3, 1e6 to 5e7 hectares
  official rate  template row 63, the published CNY/US$ series

Every fit is checked: the flag row of single M/X/H letters must land on integer
template row 2, and every anchor must land within LATTICE_TOL of an integer.

This module locates rows. It reads no criterion and applies no threshold.
"""
import re

# The pitch is per page, not per document. Four legend pages fit 13.920 to
# 13.921 with a 0.02 point residual, which looked like a constant, but the
# maize pages run about 15.5: the lattice positions there drift by 0.11 rows
# per row, so a fixed pitch walks a whole row off within twenty rows and reads
# a neighbour that still prints a plausible number. The pitch is therefore
# fitted on each page by requiring the printed rows to land on integers.
PITCH_RANGE = (12.8, 16.8)
PITCH_STEP = 0.005
INT_TOL = 0.12              # in rows, for calling a printed row integral
INT_MIN = 0.80              # fraction of printed rows that must be integral
LATTICE_TOL = 0.12
SNAP_TOL_ROWS = 0.25        # in rows, when reading a row back off the page

YEAR = re.compile(r"^(19[5-9]\d|20[0-1]\d)$")
FLAG = re.compile(r"^(M|X|H|HM|HX)$")

OFFICIAL_RATE = {
    1980: 1.50, 1981: 1.70, 1982: 1.89, 1983: 1.98, 1984: 2.32, 1985: 2.94,
    1986: 3.45, 1987: 3.72, 1988: 3.72, 1989: 3.77, 1990: 4.78, 1991: 5.32,
    1992: 5.51, 1993: 5.76, 1994: 8.62, 1995: 8.35, 1996: 8.31, 1997: 8.29,
    1998: 8.28, 1999: 8.28, 2000: 8.28, 2001: 8.28, 2002: 8.28, 2003: 8.28,
    2004: 8.28, 2005: 8.19,
}
RATE_TOL = 0.08


def as_float(s):
    s = s.replace(",", "").strip()
    if s in ("", "-", "n.a.", "na"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def page_rows(page):
    """[(y, [words])] grouped on a half-point grid, top to bottom."""
    d = {}
    for w in page.extract_words():
        d.setdefault(round(w["top"] * 2) / 2, []).append(w)
    return [(k, sorted(d[k], key=lambda z: z["x0"])) for k in sorted(d)]


def year_columns(rows):
    for _, cells in rows:
        ys = [c for c in cells if YEAR.match(c["text"])]
        if len(ys) >= 8:
            return [(int(c["text"]), (c["x0"] + c["x1"]) / 2) for c in ys]
    return []


def values(cells, centres, col_tol=30.0):
    out = {}
    for c in cells:
        mid = (c["x0"] + c["x1"]) / 2
        y, d = min(((y, abs(mid - x)) for y, x in centres), key=lambda t: t[1])
        if d <= col_tol:
            out[y] = c["text"]
    return out


def find_flag_row(rows):
    for y, cells in rows:
        if len(cells) >= 6 and all(FLAG.match(c["text"]) for c in cells):
            return y
    return None


def find_area_row(rows, after_y):
    """First row below `after_y` whose values look like a sown area in Ha."""
    for y, cells in rows:
        if after_y is not None and y <= after_y:
            continue
        n = sum(1 for c in cells
                if (v := as_float(c["text"])) is not None and 1e6 < v < 5e7)
        if n >= 6:
            return y
    return None


def find_rate_row(rows, centres):
    for y, cells in rows:
        got = {yr: as_float(v) for yr, v in values(cells, centres).items()}
        cmp = [(yr, got[yr], OFFICIAL_RATE[yr]) for yr in got
               if got.get(yr) and yr in OFFICIAL_RATE]
        if len(cmp) >= 4 and all(abs(v - t) / t <= RATE_TOL for _, v, t in cmp):
            return y, len(cmp)
    return None, 0


def fit_pitch(rows, y_flag, area_y, rate_y, anchor_y=None, anchor_row=2):
    """Pitch for this page, anchored at the flag row = template row 2.

    Ranked by the value anchors first and by lattice integrality only as a
    tie-break. Integrality alone picks the wrong pitch on a page whose rows are
    not all the same height: on one such page it preferred 13.81, at which 75%
    of rows are integral, over 13.92, at which the crop area lands exactly on
    template row 3. The anchors are independently known; integrality is not.

    Returns (pitch, integral_fraction, anchors_satisfied).
    """
    a_y = y_flag if anchor_y is None else anchor_y
    ys = [y for y, _ in rows if y != a_y]
    if len(ys) < 8:
        return None, 0.0, 0
    best = (None, -1.0, -1)
    p = PITCH_RANGE[0]
    while p <= PITCH_RANGE[1]:
        hits = 0
        if area_y is not None and abs(anchor_row + (area_y - a_y) / p - 3) <= LATTICE_TOL:
            hits += 1
        if rate_y is not None and abs(anchor_row + (rate_y - a_y) / p - 63) <= LATTICE_TOL:
            hits += 1
        n = sum(1 for y in ys
                if abs((y - a_y) / p - round((y - a_y) / p)) <= INT_TOL)
        frac = n / len(ys)
        if (hits, frac) > (best[2], best[1]):
            best = (p, frac, hits)
        p += PITCH_STEP
    return best


def fit(rows, centres):
    """Offset for row = 3 + (y - y_anchor)/PITCH, plus the checks it passed."""
    flag_y = find_flag_row(rows)
    area_y = find_area_row(rows, flag_y)
    rate_y, rate_hits = find_rate_row(rows, centres)

    # The block's first page is anchored on the letter row; the pages after it
    # carry no letters, so the official rate row anchors those. Both anchors are
    # value-identified and the second one is checked against a published series.
    if flag_y is not None:
        anchor_y, anchor_row = flag_y, 2
    elif rate_y is not None:
        anchor_y, anchor_row = rate_y, 63
    else:
        return None, {"why": "no anchor: neither a letter row nor the rate row"}
    pitch, frac, hits = fit_pitch(rows, anchor_y, area_y, rate_y,
                                  anchor_y, anchor_row)
    n_anchor = (area_y is not None) + (rate_y is not None)
    checks = {"pitch": None if pitch is None else round(pitch, 3),
              "integral_fraction": round(frac, 3),
              "value_anchors": f"{hits}/{n_anchor}",
              "rate_years_matched": rate_hits}
    if pitch is None:
        return None, {**checks, "why": "too few printed rows to fit a lattice"}
    # A page is accepted on its value anchors. Integrality alone is allowed to
    # carry a page only when there is no value anchor to check it against.
    if hits == 0 and frac < INT_MIN:
        return None, {**checks, "why": f"no value anchor satisfied and only "
                                       f"{frac:.0%} of printed rows are integral"}

    def row_of(y):
        return anchor_row + (y - anchor_y) / pitch

    checks["anchor"] = "flag=2" if flag_y is not None else "rate=63"
    if area_y is not None:
        ra = row_of(area_y)
        checks["area_row"] = round(ra, 3)
        if abs(ra - 3) > LATTICE_TOL:
            return None, {**checks, "why": f"crop area lands on {ra:.2f}, not 3"}
    if rate_y is not None:
        rr = row_of(rate_y)
        checks["rate_row"] = round(rr, 3)
        if abs(rr - 63) > LATTICE_TOL:
            return None, {**checks, "why": f"official rate lands on {rr:.2f}, not 63"}
    checks["anchors_used"] = [checks["anchor"]] + \
        (["area=3"] if area_y is not None and flag_y is not None else []) + \
        (["rate=63"] if rate_y is not None and flag_y is not None else [])
    return row_of, checks


def read(rows, centres, row_of, template_row):
    """Values of `template_row`, or {} if no printed row sits on that lattice point."""
    y = None
    for yy, _ in rows:
        if abs(row_of(yy) - template_row) <= SNAP_TOL_ROWS:
            if y is None or abs(row_of(yy) - template_row) < abs(row_of(y) - template_row):
                y = yy
    if y is None:
        return {}
    return values(dict(rows)[y], centres)
