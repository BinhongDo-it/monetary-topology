"""B135 yearbooks: what the exchanges' own statistical yearbooks say, with the
page of every number.

Reads the PDFs under ``data/raw/b135/exchange_yearbooks/`` (their origin,
size and hash in ``sources.json`` there) and writes
``data/processed/b135_yearbooks.json``. Nothing is fetched.

**Which year a volume holds.** A Shanghai volume ``N`` holds year ``N - 1``
and the year before it (its overview pages, three years); a Shenzhen volume
``N`` holds year ``N``. Checked on the market values, which appear in several
volumes and on Shanghai's 1990-2024 history page, and agree wherever they
overlap.

**How numbers are read.** The Shanghai history page is parsed row by row. The
overview rows and the Shenzhen ten-year charts are transcribed below with
file, page and column, and every transcribed number is checked to appear on
its page; a number that does not is an error, not a warning. The Shanghai 2019
volume has no text layer and is not read; the 2018 and 2020 volumes cover its
years.

    python experiments/b135_yearbooks.py            # check and write
    python experiments/b135_yearbooks.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIR = ROOT / "data" / "raw" / "b135" / "exchange_yearbooks"
OUT = ROOT / "data" / "processed" / "b135_yearbooks.json"

#: Shanghai stock block trades, all boards: (amount in 100M yuan, trades),
#: with the volume, page and column (1 = the year the volume reports).
SSE_BLOCK = {
    2011: (676.76, 2024, 2013, 25, 2), 2012: (565.50, 1842, 2013, 25, 1),
    2013: (910.65, 2348, 2015, 25, 2), 2014: (1365.75, 3187, 2015, 25, 1),
    2015: (2893.15, 4137, 2017, 26, 2), 2016: (2701.11, 6279, 2017, 26, 1),
    2017: (2083.24, 6169, 2018, 25, 1), 2018: (1593.95, 4531, 2020, 30, 2),
    2019: (1729.99, 5341, 2020, 30, 1), 2020: (2411.83, 10462, 2021, 30, 1),
    2021: (3724.47, 16817, 2023, 29, 2), 2022: (3113.09, 18336, 2023, 29, 1),
    2023: (3100.74, 18537, 2025, 28, 2), 2024: (2067.52, 12661, 2025, 28, 1),
}

#: Shanghai restricted shares, 100M shares: unlocked in the year, unlocked
#: shares sold in the year, the stock of unlocked restricted shares at year end.
SSE_UNLOCK = {
    2010: (3270.67, 829.27, 6841.82, 2013, 9, 3),
    2011: (1239.30, 243.78, 7837.35, 2013, 9, 2),
    2012: (1138.66, 277.55, 8698.45, 2013, 9, 1),
    2013: (3616.35, 544.82, 11735.91, 2015, 9, 2),
    2014: (657.52, 491.58, 11889.86, 2015, 9, 1),
    2015: (1119.01, 858.99, 12069.73, 2017, 10, 2),
    2016: (918.27, 725.75, 12262.25, 2017, 10, 1),
    2017: (1027.42, 580.57, 12673.78, 2018, 9, 1),
    2018: (1747.92, 589.01, 13814.61, 2020, 14, 2),
    2019: (1133.18, 1015.26, 13952.78, 2020, 14, 1),
}

#: Shenzhen, 10 billion yuan (market value) and 100M shares (share capital),
#: total and negotiable, from the ten-year pages.
SZSE_YEARS_A = list(range(2005, 2016))
SZSE_YEARS_B = list(range(2015, 2026))
SZSE = {
    "market_value_total": (SZSE_YEARS_A, [933, 1779, 5730, 2411, 5928, 8642, 6638, 7166, 8791, 12857, 23611],
                           "szse_yearbook_2015.pdf", 36),
    "market_value_negotiable": (SZSE_YEARS_A, [388, 858, 2853, 1291, 3645, 5077, 4207, 4736, 6305, 9513, 16380],
                                "szse_yearbook_2015.pdf", 36),
    "shares_total": (SZSE_YEARS_A, [2134, 2376, 2782, 3442, 3908, 5045, 6278, 7216, 8070, 9710, 12779],
                     "szse_yearbook_2015.pdf", 36),
    "shares_negotiable": (SZSE_YEARS_A, [934, 1177, 1511, 1617, 2601, 3411, 4506, 5257, 6266, 7375, 9626],
                          "szse_yearbook_2015.pdf", 36),
    "market_value_total_b": (SZSE_YEARS_B, [23611, 22308, 23576, 16541, 23741, 34192, 39639, 32422, 31000, 33041, 43241],
                             "szse_yearbook_2025.pdf", 35),
    "market_value_negotiable_b": (SZSE_YEARS_B, [16380, 15340, 16793, 12110, 18221, 26359, 31609, 26524, 25664, 28124, 37461],
                                  "szse_yearbook_2025.pdf", 35),
    "shares_total_b": (SZSE_YEARS_B, [12779, 16043, 18458, 19872, 21521, 22855, 24457, 25642, 26415, 26352, 26890],
                       "szse_yearbook_2025.pdf", 35),
    "shares_negotiable_b": (SZSE_YEARS_B, [9626, 11764, 13925, 15550, 17317, 18852, 20333, 22002, 22971, 23236, 24071],
                            "szse_yearbook_2025.pdf", 35),
}

FULLWIDTH = str.maketrans("０１２３４５６７８９．－", "0123456789.-")


def page_text(name: str, page: int) -> str:
    import pymupdf
    doc = pymupdf.open(DIR / name)
    t = doc[page - 1].get_text().translate(FULLWIDTH)
    # the 2020 volume sets its decimal point as a private-use glyph, U+1001B0
    t = t.replace("\U001001b0", ".").replace(". ", ".")
    return re.sub(r"\s+", " ", t)


def number_on_page(text: str, value, places: int) -> bool:
    s = f"{value:.{places}f}" if places else str(int(value))
    return s in text or s.replace(".00", "") in text


def check_sse_block(problems: list) -> dict:
    out = {}
    for y, (amt, n, vol, page, col) in SSE_BLOCK.items():
        t = page_text(f"sse_yearbook_{vol}.pdf", page)
        i = t.find("大宗交易")
        seg = t[i:i + 500] if i >= 0 else ""
        if not number_on_page(seg, amt, 2) or not number_on_page(seg, n, 0):
            problems.append(f"SSE block {y}: {amt} or {n} not in the block rows of volume {vol} page {page}")
        out[y] = {"amount_100m_yuan": amt, "trades": n, "volume": vol, "page": page, "column": col}
    return out


def check_sse_unlock(problems: list) -> dict:
    out = {}
    for y, (unl, sold, stock, vol, page, col) in SSE_UNLOCK.items():
        t = page_text(f"sse_yearbook_{vol}.pdf", page)
        for v in (unl, sold, stock):
            if not number_on_page(t, v, 2):
                problems.append(f"SSE unlock {y}: {v} not on volume {vol} page {page}")
        out[y] = {"unlocked_in_year": unl, "unlocked_sold_in_year": sold,
                  "unlocked_stock_year_end": stock, "unit": "100M shares",
                  "volume": vol, "page": page, "column": col}
    return out


def sse_history(problems: list) -> dict:
    t = page_text("sse_yearbook_2025.pdf", 669)
    rows = re.findall(r"(19\d\d|20\d\d) ([\d.]+) ([\d.]+) ([\d.]+) (—|[\d.]+) (—|[\d.]+)", t)
    out = {}
    for y, gdp, cap, _, nego, _ in rows:
        out[int(y)] = {"gdp_100m_yuan": float(gdp), "market_value_100m_yuan": float(cap),
                       "negotiable_100m_yuan": None if nego == "—" else float(nego)}
    if sorted(out) != list(range(1990, 2025)):
        problems.append(f"SSE history: years {min(out)}..{max(out)}, {len(out)} rows")
    return out


def check_szse(problems: list) -> dict:
    out = {}
    for key, (years, vals, name, page) in SZSE.items():
        t = page_text(name, page)
        for v in vals:
            if str(v) not in t:
                problems.append(f"SZSE {key}: {v} not on {name} page {page}")
        out[key] = {"years": years, "values": vals, "file": name, "page": page}
    # the two ten-year pages overlap in 2015 and must agree there
    for a, b in (("market_value_total", "market_value_total_b"),
                 ("market_value_negotiable", "market_value_negotiable_b"),
                 ("shares_total", "shares_total_b"), ("shares_negotiable", "shares_negotiable_b")):
        if SZSE[a][1][-1] != SZSE[b][1][0]:
            problems.append(f"SZSE {a}: 2015 differs between the two volumes")
    return out


def cross_checks(hist: dict, problems: list) -> None:
    """Values the overview rows repeat against the history page."""
    over = {2016: (284607.63, 240006.24, 2017, 10), 2014: (243974.02, 220495.87, 2015, 9),
            2012: (158698.44, 134294.45, 2013, 9)}
    for y, (cap, nego, vol, page) in over.items():
        t = page_text(f"sse_yearbook_{vol}.pdf", page)
        if not (number_on_page(t, cap, 2) and number_on_page(t, nego, 2)):
            problems.append(f"SSE overview {y} not on volume {vol} page {page}")
        h = hist.get(y, {})
        if h.get("market_value_100m_yuan") != cap or h.get("negotiable_100m_yuan") != nego:
            problems.append(f"SSE {y}: overview and history disagree")


def build() -> tuple[dict, list]:
    problems: list = []
    hist = sse_history(problems)
    rec = {"source": "data/raw/b135/exchange_yearbooks, origins in sources.json there",
           "sse_block_trades": check_sse_block(problems),
           "sse_restricted_shares": check_sse_unlock(problems),
           "sse_market_value": hist,
           "szse_ten_year": check_szse(problems)}
    cross_checks(hist, problems)
    return rec, problems


def selftest() -> bool:
    ok = True
    saved = dict(SSE_BLOCK)
    SSE_BLOCK[2014] = (1365.76, 3187, 2015, 25, 1)
    _, p = build()
    SSE_BLOCK.clear()
    SSE_BLOCK.update(saved)
    print(f"  a mistyped block amount is reported: {any('2014' in x for x in p)}")
    ok &= any("2014" in x for x in p)
    saved_z = SZSE["market_value_total"]
    SZSE["market_value_total"] = (saved_z[0], saved_z[1][:-1] + [23612], saved_z[2], saved_z[3])
    _, p = build()
    SZSE["market_value_total"] = saved_z
    print(f"  a mistyped Shenzhen value is reported: {any('SZSE' in x for x in p)}")
    ok &= any("SZSE" in x for x in p)
    _, p = build()
    print(f"  clean build: {len(p)} problems")
    ok &= not p
    return bool(ok)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        ok = selftest()
        print(f"selftest {'passed' if ok else 'FAILED'}")
        return 0 if ok else 1
    rec, problems = build()
    for p in problems:
        print("PROBLEM", p)
    if problems:
        return 1
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rec['sse_block_trades'])} block years, "
          f"{len(rec['sse_restricted_shares'])} unlock years, {len(rec['sse_market_value'])} "
          f"market-value years, {len(rec['szse_ten_year'])} Shenzhen series")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
