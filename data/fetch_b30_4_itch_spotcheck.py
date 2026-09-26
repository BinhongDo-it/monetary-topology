"""Step three, piece five: does a project's own page say what the listing said.

**Three things about the listing price are already settled and none of them needed a
request.** The non-dollar prices are set by the seller rather than converted for
display: `83%` of the euro prices land on a round euro point and the best single
exchange rate that would explain them is one. A project's price is the same on every
tag page it appears on: of `16,057` projects appearing more than once, two differ,
and both of those are a sale starting mid-walk. And the source names the number
itself, in the title attribute it prints beside it: `Pay $X or more for this game`,
which is a floor and is what a seller posted.

**One thing is not settled and it needs the project's own page.** A project may offer
several paid downloads at different prices, and the listing shows one number. If that
number is not the project's own minimum then the collected distribution is of
something else, and nothing in the listing would say so.

**So this fetches a stratified sample of project pages and compares.** Twenty-four is
enough to catch a systematic mismatch; it is not enough to estimate a rate, and it is
not used as one. If the sample comes back clean the listing is taken at its word; if
anything differs, that is the signal to look at the whole thing rather than to
correct a percentage.

**It also collects each sampled project's own tag list**, which the browse grid does
not carry, so the per-project market count measured from the tag pages can be checked
against what the project itself declares.

Usage::

    python data/fetch_b30_4_itch_spotcheck.py
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.request
from html import unescape as html_unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "results" / "b30_4_itch_prices.json"
CACHE = ROOT / "data" / "raw" / "itch_project_pages"
OUT = ROOT / "results" / "b30_4_price_spotcheck.json"

UA = "monetary-topology research binhongd@outlook.com"
DELAY_S = 1.5
MIN_BYTES = 3000
SAMPLE = 24
SEED = 4

STRIP = re.compile(r"<[^>]+>")
#: The buy row on a project page, in whatever order the attributes come in.
BUY = re.compile(r'<div(?=[^>]*class="[^"]*buy_row[^"]*")[^>]*>(.*?)</div>\s*</div>', re.S)
PRICE_ANY = re.compile(r'([$£€]|R\$)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)|'
                       r'([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*([€£])')
BUY_BTN = re.compile(r'<a(?=[^>]*class="[^"]*buy_btn[^"]*")[^>]*>(.*?)</a>', re.S)
TAGLINK = re.compile(r'<a href="https://itch\.io/(?:games|c)/[^"]*tag-([a-z0-9\-]+)"[^>]*>')
TITLE = re.compile(r"<title>(.*?)</title>", re.S)


def text(s):
    return re.sub(r"\s+", " ", html_unescape(STRIP.sub(" ", s))).strip()


def slugify(url):
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:120]


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{slugify(url)}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace"), None, True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", errors="replace")
    dt = time.monotonic() - t0
    if len(body.encode("utf-8")) < MIN_BYTES:
        bad = CACHE / f"{slugify(url)}.html.partial"
        bad.write_text(body, encoding="utf-8", newline="\n")
        raise RuntimeError(f"{url} came back short; kept at {bad.name}, nothing deleted")
    path.write_text(body, encoding="utf-8", newline="\n")
    time.sleep(DELAY_S)
    return body, dt, False


def prices_on_page(html):
    """Every amount the buy controls carry, in cents, with its symbol."""
    out = []
    for seg in BUY_BTN.findall(html) + [m for m in BUY.findall(html)]:
        for a, b, c, dd in PRICE_ANY.findall(seg):
            sym = a or dd
            num = b or c
            if not num:
                continue
            out.append((sym, int(round(float(num.replace(",", "")) * 100))))
    return out


def main():
    rec = json.loads(PRICES.read_text(encoding="utf-8"))
    games = {k: v for k, v in rec["games"].items()
             if v.get("price_cents") and v.get("url") and not v.get("on_sale")}
    #: Stratified by price so the sample covers the range rather than its middle.
    by_band = {"under $2": [], "$2 to $5": [], "$5 to $15": [], "over $15": []}
    for k, v in games.items():
        c = v["price_cents"]
        band = ("under $2" if c < 200 else "$2 to $5" if c < 500
                else "$5 to $15" if c < 1500 else "over $15")
        by_band[band].append(k)
    rng = random.Random(SEED)
    pick = []
    for band, ks in by_band.items():
        rng.shuffle(ks)
        pick += [(band, k) for k in ks[:SAMPLE // len(by_band)]]

    rows, agree, differ = [], 0, 0
    print(f"{len(pick)} project pages, stratified by price band\n")
    for band, gid in pick:
        g = games[gid]
        try:
            html, dt, cached = fetch(g["url"])
        except urllib.error.HTTPError as e:
            rows.append({"game_id": gid, "band": band, "http_error": e.code,
                         "listing_cents": g["price_cents"]})
            print(f"   {band:10s} {str(g['title'])[:26]:28s} HTTP {e.code}")
            continue
        found = prices_on_page(html)
        cents = sorted({c for _, c in found})
        tags = sorted(set(TAGLINK.findall(html)))
        same = g["price_cents"] in cents
        lowest = (min(cents) == g["price_cents"]) if cents else None
        agree += bool(same)
        differ += not same
        rows.append({"game_id": gid, "band": band, "url": g["url"],
                     "listing_cents": g["price_cents"],
                     "listing_currency": g["price_currency"],
                     "page_amounts_cents": cents, "listing_is_on_page": same,
                     "listing_is_the_lowest": lowest,
                     "paid_options_on_page": len(cents), "page_tags": tags,
                     "tags_on_page": len(tags)})
        print(f"   {band:10s} {str(g['title'])[:26]:28s} listing "
              f"{g['price_cents']/100:>7.2f}   page {[c/100 for c in cents][:4]}"
              f"   {'same' if same else 'DIFFERS'}"
              f"{'' if lowest in (True, None) else ', not the lowest'}"
              f"   {len(tags)} tags")

    scored = [r for r in rows if "page_amounts_cents" in r]
    multi = [r for r in scored if r["paid_options_on_page"] > 1]
    tagcounts = [r["tags_on_page"] for r in scored if r["tags_on_page"]]
    record = {
        "station": "B30-4",
        "what": ("step three piece five: the listing price against the project's own "
                 "page, on a sample stratified by price band"),
        "sample_size": len(rows), "seed": SEED,
        "listing_price_found_on_page": agree,
        "listing_price_not_found": differ,
        "projects_with_more_than_one_paid_option": len(multi),
        "rows": rows,
        "diagnostic_only": True,
        "diagnostic_reason": ("A spot check. It is sized to catch a systematic mismatch "
                              "and is not a rate."),
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"\n{'-' * 66}")
    print(f"listing price present on the project's own page: {agree} of {len(scored)}")
    print(f"projects offering more than one paid option: {len(multi)}")
    if tagcounts:
        tagcounts.sort()
        print(f"tags declared on the project page: min {tagcounts[0]}, "
              f"median {tagcounts[len(tagcounts)//2]}, max {tagcounts[-1]}")
    print("A clean sample means the listing is taken at its word. Anything differing "
          "is a reason to look at the whole thing, not to correct a percentage.")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
