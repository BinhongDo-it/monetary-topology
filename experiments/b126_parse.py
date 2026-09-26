"""Parse the B126 vintage pages on disk into lot rows, retail offers and a coverage table.

What a vintage page holds, read off the raw pages on 2026-09-23 before this was written:
  - an HTML table of past lots, one <tr data-testid="lot-row"> each, columns
    date, house, format, quantity, price per 750 ml, lot total, link
  - the same lots as a JSON array inside the Next.js payload (self.__next_f.push chunks),
    with the fields the table prints plus hammer price, lot url and end time
  - a second JSON "lots" array for upcoming lots (LiveLotsSection); not sales, not read
  - per-vintage summaries for the whole wine: lot_count, min, avg, max, last_sale_date
  - retail offers, HTML only, one <div data-testid="wine-detail-retail-offer-row"> each

Two things the pages do that the parser has to carry, both measured on the 67 pages:
  1  the table is a truncated window. The title prints min(lot_count, 50), and the table shows
     at most that many and often far fewer (Yquem 1995: 114 lots on the site, 13 rows, all
     from June and July 2026). So the rows are the most recent part of the history, and the
     site total is the summary's lot_count, not the row count.
  2  a page can come back without its history table at all (Rieussec 2010: title says 50 lots,
     the summary block is there, no AuctionHistoryTable component and no rows). That is a
     render gap, reported and refetched, never read as zero sales.

Criterion B126-1 (instrument), what this script prints:
  - every row traced to its page: the JSON record is matched to the HTML row in the same
    position, and date, house, format, quantity, unit price and total must agree
  - the 750 ml equivalent computed here from total, quantity and format_ml, against the
    page's own unit price; every disagreement printed
  - lots seen more than once (same lot url) collapsed, each dropped row printed
  - a coverage row per page, zero-row pages included, with site total, rows, and a flag
    for a truncated window and for a render gap

Run from the repo root:
    python experiments/b126_parse.py             # parse what is on disk, write data/b126/parsed/
    python experiments/b126_parse.py --selftest  # seeded faults, no disk
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b126" / "raw"
OUT = ROOT / "data" / "b126" / "parsed"
MANIFEST = RAW / "manifest.json"

RE_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.S)
RE_VINTAGE_URL = re.compile(r"/wine/([a-z0-9-]+)/(\d{4})$")
RE_ROW = re.compile(r'<tr[^>]*data-testid="lot-row"[^>]*>(.*?)</tr>', re.S)
RE_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
RE_TAG = re.compile(r"<[^>]+>")
RE_RETAIL = re.compile(r'data-testid="wine-detail-retail-offer-row"(.*?)(?=data-testid="wine-detail-retail-offer-row"|data-testid="wine-detail-retail-offers-panel"|</main>|$)', re.S)
# Units summed per 750 ml; the page prints whole dollars, so a gap of more than one is a real one.
ROUND_TOL = 1.0

DEC = json.JSONDecoder()
HOUSE_SEEN: set = set()


def payload(text: str) -> str:
    return "".join(json.loads('"' + c + '"') for c in RE_PUSH.findall(text))


def lot_arrays(p: str) -> list[list[dict]]:
    out = []
    for m in re.finditer(r'"lots":\[', p):
        v, _ = DEC.raw_decode(p, m.end() - 1)
        out.append(v)
    return out


def cell_text(s: str) -> str:
    return html.unescape(RE_TAG.sub("", s)).strip()


def html_rows(text: str) -> list[list[str]]:
    return [[cell_text(c) for c in RE_CELL.findall(r)] for r in RE_ROW.findall(text)]


def money(s: str) -> float | None:
    s = s.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def row_date(end_time: str) -> str:
    d = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def same_house(code: str, shown: str) -> bool:
    """The JSON carries a code (klwines, sothebys), the table a display name (K&L, Sotheby's).
    Same house when one, stripped to letters and digits, begins the other. The pairs seen are
    printed as a table in the run, so a wrong pairing is visible there."""
    a, b = alnum(code), alnum(shown)
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def match(rec: dict, row: list[str]) -> list[str]:
    """Fields where the JSON record and the HTML row disagree; empty means they agree."""
    bad = []
    if len(row) < 6:
        return ["row has fewer than six cells"]
    if row_date(rec["end_time"]) != row[0]:
        bad.append(f"date {row_date(rec['end_time'])!r} vs {row[0]!r}")
    house = (rec.get("auctions") or {}).get("house") or ""
    if not same_house(house, row[1]):
        bad.append(f"house {house!r} vs {row[1]!r}")
    # the JSON sometimes leaves format null; the table then prints format_ml
    fmt = rec.get("format") or (f"{rec['format_ml']}ml" if rec.get("format_ml") else None)
    if fmt != row[2]:
        bad.append(f"format {fmt!r} vs {row[2]!r}")
    if str(rec.get("quantity")) != row[3]:
        bad.append(f"quantity {rec.get('quantity')!r} vs {row[3]!r}")
    u = money(row[4])
    if rec.get("unit_price_usd") is not None and u is not None and abs(u - rec["unit_price_usd"]) > ROUND_TOL:
        bad.append(f"unit {rec['unit_price_usd']} vs {row[4]!r}")
    tot = money(row[5])
    if rec.get("sold_price_usd") is not None and tot is not None and abs(tot - rec["sold_price_usd"]) > ROUND_TOL:
        bad.append(f"total {rec['sold_price_usd']} vs {row[5]!r}")
    return bad


def history(arrays: list[list[dict]], rows: list[list[str]]) -> tuple[list[dict], str]:
    """The JSON array that is the history table: same length as the HTML rows, dates in order."""
    for a in arrays:
        if len(a) == len(rows) and all(row_date(r["end_time"]) == h[0] for r, h in zip(a, rows) if h):
            return a, "matched"
    for a in arrays:
        if len(a) == len(rows):
            return a, "matched by length only"
    return [], "no array matches the table"


def eq750(rec: dict) -> tuple[float | None, str]:
    total = rec.get("sold_price_usd")
    src = "sold"
    if total is None:
        total, src = rec.get("hammer_price_usd"), "hammer"
    q, ml = rec.get("quantity"), rec.get("format_ml")
    if total is None or not q or not ml:
        return None, "no price"
    return total / (q * ml / 750.0), src


def parse_page(url: str, text: str) -> dict:
    m = RE_VINTAGE_URL.search(url)
    slug, vint = m.group(1), int(m.group(2))
    title = html.unescape(re.search(r"<title>([^<]*)", text).group(1))
    p = payload(text)
    arrays = lot_arrays(p)
    rows = html_rows(text)
    has_table = "AuctionHistoryTable" in p
    hist, how = history(arrays, rows) if rows else ([], "no rows")
    sm = re.search(r'\{"vintage":%d,"lwin11":"\d+",(.*?)\}' % vint, p)
    summ = json.loads("{" + sm.group(1) + "}") if sm else {}
    tl = re.search(r"([\d,]+) Lots", title)
    lots, mism, checks = [], [], []
    for i, (rec, row) in enumerate(zip(hist, rows)):
        if len(row) > 1:
            HOUSE_SEEN.add(((rec.get("auctions") or {}).get("house"), row[1]))
        bad = match(rec, row)
        if bad:
            mism.append({"row": i, "why": bad})
        # JSON format null, format_ml not 750, table printing 750ml: the page states two sizes
        # for one lot and the lot name carries neither. The price per 750 ml differs by the
        # ratio of the two, so the row is tagged and kept out of the reading.
        conflict = any(w.startswith("format ") for w in bad)
        e, src = eq750(rec)
        site = rec.get("unit_price_usd")
        if e is not None and site is not None and abs(e - site) > ROUND_TOL:
            checks.append({"row": i, "own_750": round(e, 2), "site_unit": site, "src": src,
                           "format_ml": rec.get("format_ml"), "quantity": rec.get("quantity")})
        lots.append({"slug": slug, "vintage": vint, "date": rec["end_time"][:10],
                     "end_time": rec["end_time"], "house": (rec.get("auctions") or {}).get("house"),
                     "format_ml": rec.get("format_ml"), "quantity": rec.get("quantity"),
                     "sold_usd": rec.get("sold_price_usd"), "hammer_usd": rec.get("hammer_price_usd"),
                     "site_unit_usd": site, "own_750_usd": None if e is None else round(e, 4),
                     "price_src": src, "lot_url": rec.get("lot_url"), "id": rec.get("id"),
                     "lot_number": rec.get("lot_number"), "raw_name": rec.get("raw_wine_name"),
                     "format_json": rec.get("format"), "format_conflict": conflict,
                     "currency": rec.get("currency") or (rec.get("auctions") or {}).get("currency"),
                     "hammer_local": rec.get("hammer_price"),
                     # A lot in another currency whose "USD" hammer equals its local hammer was
                     # never converted (Acker's HKD sale of 2026-07-25: HK$18,000 printed as
                     # $18,000). A converted lot shows the two apart (HK$12,800 -> $1,632).
                     "fx_missing": (bool(rec.get("currency")) and rec.get("currency") != "USD"
                                    and rec.get("hammer_price") is not None
                                    and rec.get("hammer_price_usd") is not None
                                    and abs(rec["hammer_price"] - rec["hammer_price_usd"]) < 1),
                     "auction": (rec.get("auctions") or {}).get("auction_name"),
                     "page": url, "row": i})
    site_total = summ.get("lot_count")
    cov = {"page": url, "slug": slug, "vintage": vint, "title_lots": int(tl.group(1).replace(",", "")) if tl else None,
           "site_lots": site_total, "html_rows": len(rows), "json_rows": len(hist), "how": how,
           "has_table": has_table,
           "render_gap": (not has_table) and bool(site_total),
           "truncated": site_total is not None and site_total > len(rows),
           "first": min((l["date"] for l in lots), default=None),
           "last": max((l["date"] for l in lots), default=None),
           "summary": summ}
    ret = retail(text, url, slug, vint)
    pn = RE_PANEL_N.search(RE_SCRIPT.sub("", text))
    cov["retail_panel"] = int(next(g for g in pn.groups() if g)) if pn else None
    cov["retail_rows"] = len(ret)
    return {"cov": cov, "lots": lots, "mismatch": mism, "unit_check": checks, "retail": ret}


RE_SCRIPT = re.compile(r"<script\b.*?</script>", re.S)
RE_PANEL_N = re.compile(r'data-testid="wine-detail-retail-offers-panel".*?Retail Offers.*?\((?:<!-- -->)?(\d+)(?:<!-- -->)?\)', re.S)


def retail(text: str, url: str, slug: str, vint: int) -> list[dict]:
    """Rendered offer rows only. The same rows sit again inside the payload scripts, so the
    scripts are cut out first or offers are read twice."""
    text = RE_SCRIPT.sub("", text)
    out = []
    for blk in RE_RETAIL.findall(text):
        a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        spans = [cell_text(s) for s in re.findall(r"<span[^>]*>(.*?)</span>", blk, re.S)]
        merch = re.search(r"<div[^>]*>([^<]*?) · ", blk)
        # price block: <span>label</span><span>price</span>, then <span>/ 750ml</span><span>per 750</span>.
        # The label is a size ("3000ml") or a word ("Bottle"), and the price carries a symbol
        # ("£864") or a code ("SGD 5,859"); both kept as printed.
        pairs = re.findall(r"<div[^>]*><span[^>]*>([^<]*)</span><span[^>]*>([^<]*)</span></div>", blk)
        pairs = [(html.unescape(x).strip(), html.unescape(y).strip()) for x, y in pairs]
        per = next((y for x, y in pairs if x.startswith("/")), None)
        main = next(((x, y) for x, y in pairs if not x.startswith("/") and re.search(r"\d", y)), (None, None))
        out.append({"slug": slug, "vintage": vint, "page": url,
                    "merchant": html.unescape(merch.group(1)).strip() if merch else None,
                    "offer_url": html.unescape(a.group(1)) if a else None,
                    "offer_title": cell_text(a.group(2)) if a else None,
                    "stock": next((s for s in spans if "stock" in s.lower()), None),
                    "format": main[0], "price": main[1], "per_750": per})
    return out


def dedupe(lots: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns kept rows, dropped duplicates, and rows of mixed lots.

    A lot is (house, auction, lot number). The lot url is not a key: one house links a whole
    sale's results PDF from every lot in it.
    Same lot inside one unit: a duplicate; the latest end time is kept, the rest dropped.
    Same lot on more than one unit: a mixed lot (a vertical or an assortment). Its total is the
    whole lot's and is printed again on every vintage it holds, so no per-bottle price for any
    one vintage can be read off it; every row of it is set aside.
    Rows without a lot number are never merged."""
    by: dict[tuple, list[dict]] = {}
    for l in lots:
        # the date is in the key because some houses reuse one sale name for every sale
        # (Dreweatts lot 33 turns up in July 2024 and March 2025 under the same name)
        k = ("id", l["id"]) if l["lot_number"] in (None, "") else (l["house"], l["auction"], l["lot_number"], l["date"])
        by.setdefault(k, []).append(l)
    kept, dropped, mixed = [], [], []
    for k in sorted(by, key=str):
        g = sorted(by[k], key=lambda l: l["end_time"])
        if len({(l["slug"], l["vintage"]) for l in g}) > 1:
            mixed.extend(g)
            continue
        kept.append(g[-1])
        dropped.extend(g[:-1])
    # A second pass for houses that file one lot under two sale names (HDH posts a results
    # PDF per date, and the same lot number, contents and price turn up in two of them):
    # same unit, house, lot number, quantity, size and total is the same lot.
    by2: dict[tuple, list[dict]] = {}
    for l in kept:
        if l["lot_number"] in (None, ""):
            by2.setdefault(("id", l["id"]), []).append(l)
        else:
            by2.setdefault((l["slug"], l["vintage"], l["house"], l["lot_number"], l["quantity"],
                            l["format_ml"], l["sold_usd"]), []).append(l)
    kept = []
    for k in sorted(by2, key=str):
        g = sorted(by2[k], key=lambda l: l["end_time"])
        kept.append(g[-1])
        dropped.extend(g[:-1])
    return kept, dropped, mixed


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def run() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pages = sorted((u, r) for u, r in m.items() if RE_VINTAGE_URL.search(u))
    covs, lots, mism, checks, ret = [], [], [], [], []
    for url, rec in pages:
        text = (RAW / rec["file"]).read_text(encoding="utf-8")
        r = parse_page(url, text)
        covs.append(r["cov"])
        lots += r["lots"]
        mism += [dict(x, page=url) for x in r["mismatch"]]
        checks += [dict(x, page=url) for x in r["unit_check"]]
        ret += r["retail"]
    kept, dropped, mixed = dedupe(lots)

    print(f"vintage pages: {len(pages)}")
    print("\ncoverage (slug tail, vintage, site lots, title lots, html rows, json rows, first, last, flags)")
    for c in sorted(covs, key=lambda c: (c["slug"], c["vintage"])):
        flags = " ".join(f for f, on in (("TRUNCATED", c["truncated"]), ("RENDER-GAP", c["render_gap"]),
                                         ("ZERO-ROWS", c["html_rows"] == 0)) if on)
        print(f"  {c['slug'][-24:]:>24} {c['vintage']}  site {str(c['site_lots']):>4}  title {str(c['title_lots']):>3}"
              f"  html {c['html_rows']:>3}  json {c['json_rows']:>3}  {c['first'] or '-':>10} {c['last'] or '-':>10}  {c['how'] if c['how'] not in ('matched', 'no rows') else ''} {flags}")
    trunc = [c for c in covs if c["truncated"]]
    gaps = [c for c in covs if c["render_gap"]]
    print(f"\ntruncated windows: {len(trunc)} / {len(covs)}; render gaps: {len(gaps)}")
    for c in gaps:
        print(f"  RENDER-GAP  {c['page']}  (site says {c['site_lots']} lots; refetch)")
    top = sorted((c["html_rows"] for c in covs), reverse=True)[:10]
    print(f"upper tail of html rows: {top}")

    print(f"\nHTML vs JSON disagreements: {len(mism)}")
    names = {(l["page"], l["row"]): l for l in lots}
    for x in mism:
        l = names.get((x["page"], x["row"]), {})
        print(f"  {x['page']}  row {x['row']}: {'; '.join(x['why'])}   name on lot: {l.get('raw_name')!r}")
    print(f"\nown 750 ml equivalent vs page unit price, gaps over ${ROUND_TOL:.0f}: {len(checks)}")
    for x in checks:
        print(f"  {x['page']}  row {x['row']}: own {x['own_750']} ({x['src']}, {x['quantity']} x {x['format_ml']} ml) vs site {x['site_unit']}")
    srcs = {}
    for l in kept:
        srcs[l["price_src"]] = srcs.get(l["price_src"], 0) + 1
    print(f"\nlot rows: {len(lots)}; duplicates dropped: {len(dropped)}; mixed-lot rows set aside: {len(mixed)};"
          f" kept: {len(kept)}; price source {srcs}")
    for d in dropped:
        print(f"  DROPPED  {d['slug'][-24:]} {d['vintage']}  {d['end_time'][:10]}  {d['house']} lot {d['lot_number']}  {d['auction']}")
    for d in mixed:
        print(f"  MIXED    {d['slug'][-24:]} {d['vintage']}  {d['end_time'][:10]}  {d['house']} lot {d['lot_number']}  total {d['sold_usd']}")
    print(f"\nhouse code -> name on the table, as paired: {sorted(HOUSE_SEEN, key=str)}")

    # Same unit, house, size, quantity and total under different lot keys. Either separate
    # identical lots or one lot relisted; the page cannot tell which. Neither is merged here,
    # but each group is tagged, because a relisted lot read as two sales is a jump of zero.
    groups: dict[tuple, list[dict]] = {}
    for l in kept:
        groups.setdefault((l["slug"], l["vintage"], l["house"], l["format_ml"], l["quantity"], l["sold_usd"]), []).append(l)
    rep = [g for g in groups.values() if len(g) > 1]
    for n, g in enumerate(sorted(rep, key=lambda g: (g[0]["slug"], g[0]["vintage"], g[0]["end_time"]))):
        for l in g:
            l["repeat_group"] = n
    same_day = sum(1 for g in rep if len({l["date"] for l in g}) == 1)
    print(f"\nidentical rows under different lot keys: {len(rep)} groups, {sum(len(g) for g in rep)} rows;"
          f" all on one day in {same_day} groups, spread over days in {len(rep) - same_day}")
    for g in sorted(rep, key=lambda g: (g[0]["slug"], g[0]["vintage"])):
        if len({l["date"] for l in g}) > 1:
            print(f"  ACROSS DAYS  {g[0]['slug'][-24:]} {g[0]['vintage']}  {g[0]['house']}  {g[0]['quantity']} x {g[0]['format_ml']}"
                  f"  total {g[0]['sold_usd']}  dates {sorted(l['date'] for l in g)}  lots {[l['lot_number'] for l in g]}")

    cur = {}
    for r in ret:
        c = re.match(r"^\D+", r["price"] or "")
        cur[c.group(0) if c else None] = cur.get(c.group(0) if c else None, 0) + 1
    print(f"\nretail offers: {len(ret)} on {len({r['page'] for r in ret})} pages; currency symbols {cur}")
    off = [(c["slug"][-24:], c["vintage"], c["retail_panel"], c["retail_rows"]) for c in covs
           if c["retail_panel"] != c["retail_rows"] and not (c["retail_panel"] is None and c["retail_rows"] == 0)]
    print(f"pages with no retail panel at all: {sum(1 for c in covs if c['retail_panel'] is None and c['retail_rows'] == 0)}")
    print(f"pages where the panel's own count differs from rows parsed: {off}")
    for r in ret:
        if r["price"] is None:
            print(f"  NO PRICE  {r['slug'][-24:]} {r['vintage']}  {r['merchant']}  {r['offer_url']}")

    dump(OUT / "coverage.json", sorted(covs, key=lambda c: (c["slug"], c["vintage"])))
    dump(OUT / "lots.json", sorted(kept, key=lambda l: (l["slug"], l["vintage"], l["end_time"], l["lot_url"] or "")))
    dump(OUT / "lots_dropped.json", sorted(dropped, key=lambda l: (l["slug"], l["vintage"], l["end_time"])))
    dump(OUT / "lots_mixed.json", sorted(mixed, key=lambda l: (l["slug"], l["vintage"], l["end_time"])))
    dump(OUT / "retail.json", sorted(ret, key=lambda r: (r["slug"], r["vintage"], r["offer_url"] or "")))
    dump(OUT / "checks.json", {"html_json_mismatch": mism, "unit_check": checks})
    print(f"\nwritten: {OUT}")
    return 0


def selftest() -> int:
    def rec(day, house="zachys", q=6, fmt="750ml", ml=750, sold=1586, unit=264, url="u1"):
        return {"end_time": f"2026-06-{day:02d}T23:59:59+00:00", "auctions": {"house": house},
                "format": fmt, "format_ml": ml, "quantity": q, "sold_price_usd": sold,
                "hammer_price_usd": None, "unit_price_usd": unit, "lot_url": url, "id": url}

    def row(day, house="Zachys", fmt="750ml", q="6", unit="$264", tot="$1,586"):
        return [f"Jun {day}, 2026", house, fmt, q, unit, tot]

    def enc(o):
        # the payload is compact JSON inside a JS string literal, as on the site
        return json.dumps(json.dumps(o, separators=(",", ":")))[1:-1]

    def page(recs, rows, table=True, lot_count=None):
        chunks = enc({"lots": recs})
        live = enc({"lots": []})
        comp = json.dumps("AuctionHistoryTable")[1:-1] if table else ""
        summ = enc({"summaries": [{"vintage": 2019, "lwin11": "10177572019",
                                   "lot_count": len(recs) if lot_count is None else lot_count}]})
        trs = "".join('<tr data-testid="lot-row">' + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
        return (f"<html><title>X 2019 Auction Prices | {min(len(recs) if lot_count is None else lot_count, 50)} Lots</title>"
                f'<script>self.__next_f.push([1,"{live}"])</script><script>self.__next_f.push([1,"{chunks}"])</script>'
                f'<script>self.__next_f.push([1,"{comp}"])</script><script>self.__next_f.push([1,"{summ}"])</script>'
                f"<table>{trs}</table></html>")

    U = "https://wineauction.ai/wine/x/2019"
    checks = []
    good = parse_page(U, page([rec(26), rec(20, url="u2")], [row(26), row(20)]))
    checks.append(("clean page: two rows, no disagreement, no unit gap",
                   len(good["lots"]) == 2 and not good["mismatch"] and not good["unit_check"]))
    checks.append(("clean page is not flagged", not good["cov"]["truncated"] and not good["cov"]["render_gap"]))
    bad_q = parse_page(U, page([rec(26)], [row(26, q="12")]))
    checks.append(("quantity disagreement between JSON and HTML is caught", bool(bad_q["mismatch"])))
    half = parse_page(U, page([rec(26, ml=375, sold=1586, unit=264)], [row(26)]))
    checks.append(("half bottle priced as if 750 ml is caught", bool(half["unit_check"])))
    gap = parse_page(U, page([], [], table=False, lot_count=50))
    checks.append(("no history table with lots on the site is a render gap, not zero sales",
                   gap["cov"]["render_gap"] and gap["cov"]["html_rows"] == 0))
    empty = parse_page(U, page([], [], table=True, lot_count=0))
    checks.append(("a real empty table is not a render gap", not empty["cov"]["render_gap"]))
    trunc = parse_page(U, page([rec(26)], [row(26)], lot_count=114))
    checks.append(("fewer rows than the site total is a truncated window", trunc["cov"]["truncated"]))
    same = [dict(l, lot_number="7", auction="A") for l in good["lots"]]
    kept, dropped, mixed = dedupe(same)
    checks.append(("the same lot twice in one unit keeps one, returns the other", len(kept) == 1
                   and len(dropped) == 1 and kept[0]["end_time"] > dropped[0]["end_time"]))
    kept, dropped, mixed = dedupe([same[0], dict(same[1], vintage=2018, date=same[0]["date"])])
    checks.append(("the same lot on two vintages on one day is a mixed lot, set aside whole", len(mixed) == 2 and not kept))
    kept, dropped, mixed = dedupe([same[0], dict(same[1], vintage=2018)])
    checks.append(("one lot number under one sale name in two different sales is two lots", len(kept) == 2 and not mixed))
    kept, dropped, mixed = dedupe([dict(l, lot_url="one.pdf", lot_number=str(i), auction="A")
                                   for i, l in enumerate(good["lots"])])
    checks.append(("two lots sharing one results url stay two lots", len(kept) == 2 and not dropped))
    kept, dropped, mixed = dedupe([dict(same[0], auction="PDF 1"), dict(same[1], auction="PDF 2")])
    checks.append(("one lot filed under two sale names is one lot", len(kept) == 1 and len(dropped) == 1))
    kept, dropped, mixed = dedupe([dict(same[0], auction="PDF 1"), dict(same[1], auction="PDF 2", sold_usd=999)])
    checks.append(("same lot number at a different price stays two lots", len(kept) == 2))
    flagged = parse_page(U, page([rec(26, fmt=None, ml=375, sold=1586, unit=529)], [row(26, unit="$529")]))
    checks.append(("null format with 375 ml against a table saying 750ml is tagged a format conflict",
                   flagged["lots"][0]["format_conflict"] and not flagged["unit_check"]))
    shifted = parse_page(U, page([rec(26), rec(20, url="u2")], [row(20), row(26)]))
    checks.append(("rows in a different order from the JSON are caught", bool(shifted["mismatch"])))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    return selftest() if a.selftest else run()


if __name__ == "__main__":
    sys.exit(main())
