"""Step three, piece three: enumerate the posted price of every paid project.

**Why enumerate rather than read the published bins.** The page publishes four
cumulative price filters, which give three disjoint bins above zero with an open
top. A dispersion read off three bins is a dispersion of the binning as much as of
the prices, and the bin edges are the site's, not the question's. The listing prints
each project's own posted price, 36 to a page, so the whole distribution is
reachable for about the same money the bins cost. The bins stay as a cross-check on
the enumeration rather than as the reading.

**And the enumeration settles an instrument failure the counts turned up.** On nine
of a hundred and fifty-one tags, ``free + paid`` does not equal ``total``: the
largest is a tag where the free page alone reports more results than the unfiltered
page, which no consistent filter can do. The two listings are the same games in the
same order, so the populations agree and the counters do not. **A page count is a
claim; a walk of the pages is a count.** Each tag's enumerated total is compared
against its published paid count and the difference is recorded, which is a
known-answer check in the sense of `11d` and the reason the walk is worth its cost.

**The record separates games from memberships, on purpose.** A project carries
several tags, so a project competes in several markets at once, and counting it in
each tag's population is the fact rather than an error. Assigning it to one tag
instead would need a rule, and that rule would be a degree of freedom this design
does not have to spend. So the record holds one table of games keyed by id and one
list of ids per tag: the union is exact, each game's market count is exact, and the
aggregate ratio that stood in for it is no longer needed.

**The denominator is asked for rather than summed.** The census summed ten genre
counts and read the sum as a project count. The listing shows one genre per project
and never two, so a sum is the right shape, but the sum is over ten of the eighteen
genres the upload form offers and skips the projects that set none. One request to
the unfiltered games page prints the project count directly.

**No dispersion is computed here.** Prices only, and the record says so.

Usage, on a machine with network access::

    python data/fetch_b30_4_itch_prices.py --limit 12   # the twelve thinnest, audit
    python data/fetch_b30_4_itch_prices.py              # every market tag
    python data/fetch_b30_4_itch_prices.py --thickest   # thick end first instead

Thin tags come first by default, so a run stopped early leaves whole tags finished at
the end of the axis where projects are scarce. Every page is cached and the run is
resumable.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from html import unescape as html_unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "results" / "b30_4_tag_split.json"
COUNTS = ROOT / "results" / "b30_4_itch_counts.json"
CACHE = ROOT / "data" / "raw" / "itch_store_pages"
OUT = ROOT / "results" / "b30_4_itch_prices.json"

UA = "monetary-topology research binhongd@outlook.com"
DELAY_S = 1.5
MIN_BYTES = 4000
PER_PAGE = 36
#: A walk stops on an empty page. This only bounds a walk that never empties, and
#: hitting it is reported rather than treated as a finished tag.
EXTRA_PAGES = 5

#: Split on the id attribute, not on the cell's class.
#:
#: This site emits attributes in more than one order, and it has now cost this
#: station three times: the tag directory's second page put ``href`` before
#: ``class`` and parsed to zero cells, the heading format of a results file put a
#: space where a comma was expected, and here the cell div puts ``class`` second on
#: some pages and a splitter keyed on ``<div class="game_cell `` returns nothing at
#: all. **Each failure was silent and produced a clean empty result.** The id
#: attribute carries no such dependence, it appears exactly once per cell, and
#: everything a cell holds comes after it, so each split segment ends where the next
#: cell begins and cannot run into it.
CELL_SPLIT = 'data-game_id="'
GAME_ID = re.compile(r'^(\d+)"')

#: Every field is matched with lookaheads rather than by attribute position.
#:
#: The same order dependence cost this file three separate fields before it was
#: taken seriously: the cell splitter returned nothing on a third of the pages, and
#: then the price and author matchers silently returned nothing on those same pages
#: while the parse looked complete, leaving a quarter of a **paid** listing with no
#: price. Lookaheads do not consume, and ``[^>]*`` cannot cross the tag, so the
#: attributes may appear in any order.
TITLE_A = re.compile(r'<a(?=[^>]*class="title game_link")[^>]*>(.*?)</a>', re.S)
HREF = re.compile(r'<a(?=[^>]*class="[^"]*\btitle\b[^"]*game_link)'
                  r'(?=[^>]*href="([^"]+)")[^>]*>')
AUTHOR = re.compile(r'<div(?=[^>]*class="game_author")[^>]*>\s*<a[^>]*>(.*?)</a>', re.S)
GENRE = re.compile(r'<div(?=[^>]*class="game_genre")[^>]*>([^<]*)</div>')
PRICE_TAG = re.compile(r'<(?:a|div)(?=[^>]*class="price_tag([^"]*)")'
                       r'(?=[^>]*title="([^"]*)")[^>]*>')
#: ``Pay $1.94 or more for this game``. Two things about this string are not what a
#: first reading assumes, and both were found by keeping what would not parse rather
#: than dropping it. One seller in seven replaces the last word with their own noun
#: ("for this visual novel", "for this bundle-zine"), so the tail is not matched. And
#: **the site does not price only in dollars**: of the first cell on every market
#: tag, about one in thirty-five is in euros, pounds or reais, the symbol sits before
#: the number for some and after it for others, and dollars above a thousand carry a
#: separator. A currency read as a number is a unit error, so the symbol is captured
#: and carried rather than assumed away.
PAY = re.compile(
    r"Pay\s+(?:(?P<pre>R\$|A\$|C\$|NZ\$|\$|£|€)\s*)?"
    r"(?P<num>[0-9][0-9,]*(?:\.[0-9]{1,2})?)"
    r"\s*(?P<post>€|£|\$)?\s+or more", re.I)
SYMBOL = {"$": "USD", "R$": "BRL", "A$": "AUD", "C$": "CAD", "NZ$": "NZD",
          "£": "GBP", "€": "EUR"}
SALE_PCT = re.compile(r'<div(?=[^>]*class="sale_tag")[^>]*>-([0-9]+)%</div>')
PAGE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
RESULTS = re.compile(r"([0-9][0-9,]*)\s*results?\b", re.I)
STRIP = re.compile(r"<[^>]+>")


def text(s):
    return re.sub(r"\s+", " ", html_unescape(STRIP.sub(" ", s))).strip()


def slugify(url):
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:120]


def fetch(url, refresh):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{slugify(url)}.html"
    if path.exists() and not refresh:
        body = path.read_text(encoding="utf-8", errors="replace")
        return body, None, len(body.encode("utf-8")), True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", errors="replace")
    dt = time.monotonic() - t0
    n = len(body.encode("utf-8"))
    if n < MIN_BYTES:
        bad = CACHE / f"{slugify(url)}.html.partial"
        bad.write_text(body, encoding="utf-8", newline="\n")
        raise RuntimeError(f"{url} came back short ({n} bytes); kept at {bad.name}, "
                           f"nothing deleted")
    path.write_text(body, encoding="utf-8", newline="\n")
    time.sleep(DELAY_S)
    return body, dt, n, False


def parse_cells(html, unparsed):
    """Return {game_id: record} for every cell on the page.

    A cell whose price string does not read as a plain dollar amount keeps its raw
    string and is counted, because a price that cannot be parsed and a project with
    no price are two different things and neither is a zero.
    """
    out = {}
    for seg in html.split(CELL_SPLIT)[1:]:
        gid = GAME_ID.match(seg)
        if not gid:
            continue
        t = TITLE_A.search(seg)
        h = HREF.search(seg)
        a = AUTHOR.search(seg)
        g = GENRE.search(seg)
        pm = PRICE_TAG.search(seg)
        cls = pm.group(1) if pm else None
        raw = html_unescape(pm.group(2)) if pm else None
        cents = currency = None
        pay = PAY.search(raw) if raw else None
        if pay:
            cents = int(round(float(pay.group("num").replace(",", "")) * 100))
            sym = pay.group("pre") or pay.group("post")
            currency = SYMBOL.get(sym, sym)
        elif raw:
            unparsed.append(raw)
        sp = SALE_PCT.search(seg)
        out[gid.group(1)] = {
            "title": text(t.group(1)) if t else None,
            "url": h.group(1) if h else None,
            "author": text(a.group(1)) if a else None,
            "genre": text(g.group(1)) if g else None,
            "price_cents": cents,
            "price_currency": currency,
            "price_raw": raw,
            "on_sale": bool(cls and "sale" in cls),
            "sale_pct": int(sp.group(1)) if sp else None,
        }
    return out


def cell_count(html):
    """How many cells the page carries, counted independently of the parser.

    A parser that returns nothing looks exactly like a page with nothing on it, so
    the two are separated: this counts the id attributes directly and the caller
    asserts the parse recovered all of them.
    """
    return len(re.findall(r'data-game_id="\d+"', html))


def walk(slug, published, refresh, timing, notes):
    """Walk one tag's paid listing to the end. Returns (ids in order, pages read)."""
    seen, order, page = set(), [], 1
    cap = (math.ceil(published / PER_PAGE) + EXTRA_PAGES) if published else 50
    games = {}
    unparsed = []
    while page <= cap:
        u = (f"https://itch.io/games/store/tag-{slug}"
             + ("" if page == 1 else f"?page={page}"))
        try:
            html, dt, n, cached = fetch(u, refresh)
        except urllib.error.HTTPError as e:
            notes.append(f"{slug}: page {page} returned HTTP {e.code}, walk stopped")
            break
        timing.append({"url": u, "bytes": n, "seconds": dt, "from_cache": cached})
        cells = parse_cells(html, unparsed)
        on_page = cell_count(html)
        if len(cells) != on_page:
            notes.append(f"{slug}: page {page} carries {on_page} cell(s) and the parser "
                         f"recovered {len(cells)}; the markup has moved")
        # This is the paid listing, so a cell with no price at all is not a plausible
        # object. Three order-dependent matchers were caught by exactly this shape,
        # each of them silent, so it is asserted on every page rather than sampled.
        nopr = [g_ for g_, c in cells.items() if c["price_raw"] is None]
        if nopr:
            notes.append(f"{slug}: page {page} has {len(nopr)} cell(s) with no price on "
                         f"a paid listing, first {nopr[:3]}")
        fresh = [g for g in cells if g not in seen]
        if not cells:
            break
        if not fresh:
            notes.append(f"{slug}: page {page} repeated the previous page, walk stopped")
            break
        for g in fresh:
            seen.add(g)
            order.append(g)
        games.update(cells)
        if len(cells) < PER_PAGE:
            page += 1
            break
        page += 1
    if page > cap:
        notes.append(f"{slug}: hit the page cap at {cap}, so the walk may be short")
    return order, games, page - 1, unparsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--thickest", action="store_true",
                    help="thick end first; the default is thin first")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    split = json.loads(SPLIT.read_text(encoding="utf-8"))["rows"]
    counts = {r["slug"]: r for r in json.loads(COUNTS.read_text(encoding="utf-8"))["tags"]}
    tags = [r for r in split if r["class"] == "market"]
    tags.sort(key=lambda r: -r["count"] if args.thickest else r["count"])
    if args.limit:
        tags = tags[:args.limit]

    timing, notes, unparsed_all = [], [], []
    games, per_tag = {}, {}

    # The denominator, asked for rather than summed.
    site = {}
    try:
        html, dt, n, cached = fetch("https://itch.io/games", args.refresh)
        m, t = RESULTS.search(html), PAGE_TITLE.search(html)
        site = {"url": "https://itch.io/games",
                "results": int(m.group(1).replace(",", "")) if m else None,
                "title": text(t.group(1)) if t else None}
        timing.append({"url": site["url"], "bytes": n, "seconds": dt, "from_cache": cached})
        print(f"project count on the unfiltered games page: {site['results']}")
    except urllib.error.HTTPError as e:
        site = {"url": "https://itch.io/games", "http_error": e.code}
        print(f"the unfiltered games page returned HTTP {e.code}; the denominator is "
              f"still the sum of ten genres, which is a floor")

    print(f"\n{len(tags)} market tag(s), "
          f"{'thick' if args.thickest else 'thin'} end first, cache-first\n")
    print(f"{'#':>4s} {'tag':24s}{'said':>7s}{'walked':>8s}{'diff':>7s}{'pages':>6s}")

    for i, t in enumerate(tags, 1):
        slug = t["slug"]
        published = (counts.get(slug, {}).get("counts", {}) or {}).get("paid")
        order, g, pages, unp = walk(slug, published, args.refresh, timing, notes)
        unparsed_all += unp
        games.update(g)
        per_tag[slug] = {"name": t["name"], "published_paid": published,
                         "enumerated": len(order), "pages": pages, "ids": order}
        diff = (len(order) - published) if published is not None else None
        print(f"{i:>4d} {t['name'][:23]:24s}{str(published):>7s}{len(order):>8d}"
              f"{str(diff):>7s}{pages:>6d}"
              + ("   MISMATCH" if diff not in (0, None) else ""))

    # How many markets each paid project competes in, counted per
    # project rather than inferred from an aggregate ratio.
    membership = {}
    for slug, d in per_tag.items():
        for gid in d["ids"]:
            membership[gid] = membership.get(gid, 0) + 1
    homing = Counter(membership.values())

    homing_dict = {str(k): v for k, v in sorted(homing.items())}
    matched = sum(1 for d in per_tag.values()
                  if d["published_paid"] is not None
                  and d["enumerated"] == d["published_paid"])
    priced = sum(1 for g in games.values() if g["price_cents"] is not None)
    onsale = sum(1 for g in games.values() if g["on_sale"])
    by_cur = Counter(g["price_currency"] for g in games.values()
                     if g["price_cents"] is not None)
    #: A game whose whole price was taken off is at zero today and its posted price
    #: is not recoverable from the page, so it is counted rather than imputed.
    full_off = sum(1 for g in games.values() if g["sale_pct"] == 100)

    record = {
        "station": "B30-4",
        "what": ("step three piece three: the posted price of every paid project under "
                 "each market tag, enumerated from the listing"),
        "provenance": {
            "source": "itch.io public browse listings",
            "retrieved": "2026-09-16 and 2026-09-17, US locale, no account signed in",
            "what_each_row_is": ("one project's own posted minimum, which the site "
                                 "prints as 'Pay $X or more for this game', together "
                                 "with the currency the seller set, the genre the "
                                 "seller chose and the sale state at the moment of "
                                 "reading"),
            "what_it_is_not": ("not a transaction price: a buyer may pay above the "
                               "minimum, and a project on sale is recorded at its sale "
                               "price with the discount flagged"),
            "what_is_deliberately_absent": ("no project descriptions, no cover images "
                                            "and no page markup. The fetched HTML stays "
                                            "on the machine that fetched it and is "
                                            "excluded from the repository, because a "
                                            "description is text its seller wrote while "
                                            "a title and a price are facts"),
            "why_it_is_published": ("the site's listings change daily, so a later run "
                                    "reads a different column and the reading taken "
                                    "from this one could not otherwise be checked"),
        },
        "dispersion_computed": False,
        "per_page": PER_PAGE,
        "site": site,
        "games": games,
        "tags": per_tag,
        "membership_counts": homing_dict,
        "known_answer_check": {
            "what": ("each tag's walked count against the count its page printed; the "
                     "counts failed their own free plus paid identity on nine tags"),
            "tags_matching_exactly": matched,
            "tags_checked": sum(1 for d in per_tag.values()
                                if d["published_paid"] is not None),
        },
        "prices_by_currency": dict(by_cur.most_common()),
        "fully_discounted_games": full_off,
        "unparsed_price_strings": sorted(set(unparsed_all))[:200],
        "unparsed_price_count": len(unparsed_all),
        "notes": notes,
        "diagnostic_only": True,
        "diagnostic_reason": ("Prices only. No dispersion is computed and no criterion "
                             "is scored."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")

    print(f"\n{'-' * 70}")
    print(f"distinct paid games: {len(games):,}, of which {priced:,} carry a parseable "
          f"price and {onsale:,} are on sale")
    print(f"by currency: {dict(by_cur.most_common())}")
    print(f"games discounted to nothing, whose posted price the page no longer shows: "
          f"{full_off:,}")
    print(f"price strings that did not parse: {len(unparsed_all)}")
    print(f"tags whose walk matched the count their page printed: "
          f"{matched} of {record['known_answer_check']['tags_checked']}")
    print(f"market tags per paid game: {homing_dict}")
    for n_ in notes[:10]:
        print(f"   note: {n_}")
    measured = [x["seconds"] for x in timing if x["seconds"] is not None]
    if measured:
        s = sorted(measured)
        print(f"seconds per request this run: n={len(s)}, min {s[0]:.2f}, "
              f"median {s[len(s)//2]:.2f}, max {s[-1]:.2f}")
    else:
        print("every page came from cache, so no seconds were measured this run")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
