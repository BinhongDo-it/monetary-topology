"""Step three, piece six: the two counts that were located rather than resolved.

**One.** On nine market tags the site's own `free + paid` does not equal its `total`.
The walk of the paid listing matched the published `paid` on all nine, to zero, **so
the fault sits in `free` or in `total`** and the treatment variable is drawn from
`total`. The direction differs by tag: on Furry the free page alone reports `4,760`
against `3,377` unfiltered, which no consistent filter can do, while on the other
eight `free + paid` falls short of `total`.

**A walk of the unfiltered listing settles it, because a walk is a count and a
printed total is a claim.** Three tags are walked rather than nine: the smallest of
the short-falling ones, the largest of them, and the one whose gap runs the other
way. If the walked figure matches `total` the free counter is at fault; if it matches
`free + paid` the total counter is.

**Two.** Twelve projects post in `¥`, and the symbol is shared by two currencies about
twenty times apart in value, so the record holds them unconverted. **Their own pages
may name the currency**, which would either resolve them or confirm that nothing on
the site does. Twelve requests.

**Neither touches the registered reading**, which is taken in dollars with the sign
holding across the sale, currency and restore-to-regular settings. This closes two
open items rather than moving a number.

Usage::

    python data/fetch_b30_4_itch_close.py
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.error
import urllib.request
from html import unescape as html_unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "results" / "b30_4_itch_prices.json"
COUNTS = ROOT / "results" / "b30_4_itch_counts.json"
CACHE = ROOT / "data" / "raw" / "itch_total_pages"
PROJ = ROOT / "data" / "raw" / "itch_project_pages"
OUT = ROOT / "results" / "b30_4_close.json"

UA = "monetary-topology research binhongd@outlook.com"
DELAY_S = 1.5
MIN_BYTES = 4000
PER_PAGE = 36
EXTRA_PAGES = 5

#: smallest short-fall, largest short-fall, and the one whose gap runs the other way
WALK = ["working-simulator", "interactive-fiction", "furry"]

GAME_ID = re.compile(r'data-game_id="(\d+)"')
RESULTS = re.compile(r"([0-9][0-9,]*)\s*results?\b", re.I)
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
STRIP = re.compile(r"<[^>]+>")
#: three-letter codes the site may print beside an amount on a project page
CURCODE = re.compile(r"\b(JPY|CNY|RMB|USD|EUR|GBP|BRL|CAD|AUD)\b")
BUYISH = re.compile(r'<(?:a|div)(?=[^>]*class="[^"]*(?:buy_btn|buy_row|price)[^"]*")'
                    r'[^>]*>(.*?)</(?:a|div)>', re.S)


def text(s):
    return re.sub(r"\s+", " ", html_unescape(STRIP.sub(" ", s))).strip()


def slugify(url):
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:120]


def fetch(url, cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{slugify(url)}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace"), None, True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", errors="replace")
    dt = time.monotonic() - t0
    if len(body.encode("utf-8")) < MIN_BYTES:
        bad = cache / f"{slugify(url)}.html.partial"
        bad.write_text(body, encoding="utf-8", newline="\n")
        raise RuntimeError(f"{url} came back short; kept at {bad.name}, nothing deleted")
    path.write_text(body, encoding="utf-8", newline="\n")
    time.sleep(DELAY_S)
    return body, dt, False


def walk_total(slug, published_total):
    seen, page = set(), 1
    cap = math.ceil(max(published_total, 1) * 2 / PER_PAGE) + EXTRA_PAGES
    notes = []
    while page <= cap:
        u = (f"https://itch.io/games/tag-{slug}"
             + ("" if page == 1 else f"?page={page}"))
        try:
            html, _, _ = fetch(u, CACHE)
        except urllib.error.HTTPError as e:
            notes.append(f"{slug}: page {page} returned HTTP {e.code}")
            break
        ids = GAME_ID.findall(html)
        if not ids:
            break
        fresh = [g for g in ids if g not in seen]
        if not fresh:
            notes.append(f"{slug}: page {page} repeated the previous page")
            break
        seen.update(fresh)
        if len(ids) < PER_PAGE:
            page += 1
            break
        page += 1
    if page > cap:
        notes.append(f"{slug}: hit the page cap at {cap}, the walk may be short")
    return len(seen), page - 1, notes


def main():
    pr = json.loads(PRICES.read_text(encoding="utf-8"))
    cn = {r["slug"]: r for r in json.loads(COUNTS.read_text(encoding="utf-8"))["tags"]}

    rows, notes = [], []
    print("part one: a walk of the unfiltered listing on three tags\n")
    print(f"   {'tag':22s}{'total':>8s}{'free':>8s}{'paid':>7s}{'free+paid':>11s}"
          f"{'walked':>9s}  what it says")
    for slug in WALK:
        c = cn[slug]["counts"]
        walked, pages, n = walk_total(slug, c["total"])
        notes += n
        fp = c["free"] + c["paid"]
        near = lambda a, b: abs(a - b) <= max(3, 0.01 * b)
        says = ("the total counter is right, so the free counter is wrong"
                if near(walked, c["total"]) and not near(walked, fp) else
                "the free counter is right, so the total counter is wrong"
                if near(walked, fp) and not near(walked, c["total"]) else
                "neither, and the walk agrees with neither figure")
        rows.append({"slug": slug, "published": c, "free_plus_paid": fp,
                     "walked": walked, "pages": pages, "reading": says})
        print(f"   {slug:22s}{c['total']:>8,}{c['free']:>8,}{c['paid']:>7,}{fp:>11,}"
              f"{walked:>9,}  {says}")

    print("\npart two: the twelve projects priced in the shared symbol\n")
    yen = [(k, v) for k, v in pr["games"].items()
           if v.get("price_raw") and "¥" in v["price_raw"]]
    ys = []
    for gid, g in yen:
        try:
            html, _, _ = fetch(g["url"], PROJ)
        except urllib.error.HTTPError as e:
            ys.append({"game_id": gid, "http_error": e.code})
            print(f"   {str(g['title'])[:30]:32s} HTTP {e.code}")
            continue
        codes = sorted(set(CURCODE.findall(html)))
        bits = [text(b)[:60] for b in BUYISH.findall(html)][:3]
        ys.append({"game_id": gid, "title": g["title"], "url": g["url"],
                   "listing_raw": g["price_raw"], "currency_codes_on_page": codes,
                   "buy_controls": bits})
        print(f"   {str(g['title'])[:30]:32s} {g['price_raw'][:28]:30s} "
              f"codes {codes}  {bits[:1]}")

    named = [y for y in ys if y.get("currency_codes_on_page")]
    record = {
        "station": "B30-4",
        "what": ("step three piece six: a walk of the unfiltered listing on three of the "
                 "nine tags whose counts fail their own identity, and the project pages "
                 "of the twelve projects priced in a shared symbol"),
        "walked_tags": rows,
        "shared_symbol_projects": ys,
        "shared_symbol_pages_naming_a_currency": len(named),
        "notes": notes,
        "diagnostic_only": True,
        "diagnostic_reason": ("Closes two located items. Neither enters the registered "
                              "reading, which is taken in dollars."),
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"\n{'-' * 66}")
    print(f"project pages naming a currency: {len(named)} of {len(ys)}")
    for n in notes[:8]:
        print(f"   note: {n}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
