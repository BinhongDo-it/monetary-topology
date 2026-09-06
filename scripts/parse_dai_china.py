"""Inventory the DAI China spreadsheet PDF: which commodity, which years,
which trade status, and are the two price legs present.

This writes an inventory. It scores no criterion and applies no threshold.

The source PDF was produced by Acrobat Paper Capture, i.e. it is a scan that
was OCR'd, so every digit passed through character recognition. Two anchors,
both independently known, run on every page and both must hold:

  anchor A  row 63, the official CNY/US$ rate, against the known series.
            Catches a row-offset slip and an OCR digit error together.
  anchor B  row 3 (crop area) and row 4 (production), against known magnitudes
            for China's major crops. Names the commodity and re-checks the page.

A page that fails an anchor is reported and skipped. Nothing is dropped quietly.

Usage:  python scripts/parse_dai_china.py [--pages 26,88,195]
"""
import argparse
import json
import re
from pathlib import Path

import pdfplumber

PDF = Path(__file__).resolve().parents[1] / "data" / "raw" / "dai" / "dai_china_wp29.pdf"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "dai" / "dai_china_pages.json"

YEAR = re.compile(r"^(19[5-9]\d|20[0-1]\d)$")
FLAG = re.compile(r"^(M|X|H|HM|HX)$")

# Official CNY per US$, annual average. Public series, used only as an anchor.
OFFICIAL_RATE = {
    1980: 1.50, 1981: 1.70, 1982: 1.89, 1983: 1.98, 1984: 2.32, 1985: 2.94,
    1986: 3.45, 1987: 3.72, 1988: 3.72, 1989: 3.77, 1990: 4.78, 1991: 5.32,
    1992: 5.51, 1993: 5.76, 1994: 8.62, 1995: 8.35, 1996: 8.31, 1997: 8.29,
    1998: 8.28, 1999: 8.28, 2000: 8.28, 2001: 8.28, 2002: 8.28, 2003: 8.28,
    2004: 8.28, 2005: 8.19,
}
RATE_TOL = 0.08          # relative; OCR of "3.72" is either right or badly wrong

# Known Chinese sown area (Mha) and yield (t/ha) for the major crops.
# Area alone does not separate wheat from maize; yield does, so the block is
# named on both and the two best candidates are always reported with a score.
# Used to name a block, never to adjust a number.
PROFILE = {
    "wheat":   dict(area=(22, 32), yld=(2.2, 4.6)),
    "rice":    dict(area=(27, 37), yld=(4.8, 7.0)),
    "maize":   dict(area=(17, 28), yld=(3.4, 6.0)),
    "soybean": dict(area=(6, 10),  yld=(1.1, 2.1)),
    "cotton":  dict(area=(4, 7),   yld=(0.5, 1.4)),
    "sugar":   dict(area=(1, 3),   yld=(40, 75)),
}


def _score(lo_hi, v):
    """0 inside the range, else distance in range-widths. Lower is better."""
    lo, hi = lo_hi
    if lo <= v <= hi:
        return 0.0
    return (lo - v if v < lo else v - hi) / (hi - lo)


def rows_of(page):
    """Group words into rows by `top`, then sort each row left to right."""
    out = {}
    for w in page.extract_words():
        out.setdefault(round(w["top"] / 4) * 4, []).append(w)
    return [(k, sorted(out[k], key=lambda z: z["x0"])) for k in sorted(out)]


def columns_of(header):
    """Column centres from the year header row."""
    return [(int(w["text"]), (w["x0"] + w["x1"]) / 2) for w in header]


def pick(cells, centres):
    """Assign each cell in a row to its nearest column centre."""
    got = {}
    for c in cells:
        mid = (c["x0"] + c["x1"]) / 2
        yr, d = min(((y, abs(mid - x)) for y, x in centres), key=lambda t: t[1])
        if d <= 30:
            got[yr] = c["text"]
    return got


def as_float(s):
    s = s.replace(",", "").strip()
    if s in ("", "-", "n.a.", "na"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def scan(pdf_path, only=None):
    pages, problems = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            if only and i not in only:
                continue
            rs = rows_of(page)
            if not rs:
                continue
            top, cells = rs[0]
            years = [c for c in cells if YEAR.match(c["text"])]
            if len(years) < 8:
                continue                      # not a block-head page
            centres = columns_of(years)
            rec = {"page": i, "years": [y for y, _ in centres]}

            body = rs[1:]
            flags = pick(body[0][1], centres) if body else {}
            rec["trade_status"] = {k: v for k, v in flags.items() if FLAG.match(v)}

            vals = [pick(r[1], centres) for r in body]
            def num_row(k):
                return {y: as_float(v) for y, v in vals[k].items()} if k < len(vals) else {}

            area = num_row(1)                 # legend row 3
            prod = num_row(2)                 # legend row 4
            rec["area_sample"] = {y: area.get(y) for y in rec["years"][:2]}
            rec["prod_sample"] = {y: prod.get(y) for y in rec["years"][:2]}

            # anchor B: name the block
            a = [v / 1e6 for v in area.values() if v]
            q = [v / 1e6 for v in prod.values() if v]
            ranked = []
            if a and q:
                ma, mq = sorted(a)[len(a) // 2], sorted(q)[len(q) // 2]
                yld = mq / ma if ma else None
                rec["area_Mha_median"] = round(ma, 2)
                rec["prod_Mt_median"] = round(mq, 2)
                rec["yield_t_per_ha"] = round(yld, 2) if yld else None
                if yld:
                    ranked = sorted(
                        ((g, round(_score(pr["area"], ma) + _score(pr["yld"], yld), 3))
                         for g, pr in PROFILE.items()), key=lambda kv: kv[1])[:2]
            rec["commodity_ranked"] = ranked or [("?", None)]
            rec["commodity_guess"] = [ranked[0][0]] if ranked and ranked[0][1] == 0 else ["?"]

            rec["_centres"] = centres
            rec["_body_rows"] = len(body)
            pages.append(rec)

        # anchor A runs over the whole block: a block-head page carries only the
        # first ~38 template rows, and the official rate is template row 63, so
        # it sits on a later page of the same block. Column x positions are the
        # same throughout a block, so the head page's centres are reused.
        heads = [r["page"] for r in pages]
        for r in pages:
            i = r["page"]
            nxt = min([h for h in heads if h > i], default=len(pdf.pages))
            r["rate_row"], r["rate_check"], r["rate_page"] = None, "not found", None
            for j in range(i, min(nxt, i + 12)):
                for k, cells in enumerate(x[1] for x in rows_of(pdf.pages[j])):
                    got = {y: as_float(v) for y, v in pick(cells, r["_centres"]).items()}
                    cmp = [(y, got[y], OFFICIAL_RATE[y]) for y in got
                           if got.get(y) and y in OFFICIAL_RATE]
                    if len(cmp) >= 4 and all(
                            abs(v - tgt) / tgt <= RATE_TOL for _, v, tgt in cmp):
                        r["rate_row"], r["rate_page"] = k, j
                        r["rate_check"] = f"ok on {len(cmp)} years (page {j})"
                        break
                if r["rate_row"] is not None:
                    break
            if r["rate_row"] is None:
                problems.append({"page": i, "why": "official rate row not located in block"})
            r.pop("_centres", None)
    return pages, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    args = ap.parse_args()
    only = {int(x) for x in args.pages.split(",") if x.strip()} or None
    pages, problems = scan(PDF, only)
    print(f"block-head pages: {len(pages)}   anchor-A failures: {len(problems)}")
    for r in pages[:12]:
        print(f"  p{r['page']:4d} {r['years'][0]}-{r['years'][-1]}"
              f"  {'/'.join(sorted(set(r['trade_status'].values()))) or '-':5s}"
              f"  area {r.get('area_Mha_median')}Mha  yld {r.get('yield_t_per_ha')}"
              f"  -> {r.get('commodity_ranked')}   rate: {r['rate_check']}")
    if not only:
        OUT.write_text(json.dumps({"pages": pages, "problems": problems},
                                  indent=2, sort_keys=True), encoding="utf-8",
                       newline="\n")
        print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
