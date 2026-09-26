"""Step three, piece one: find out what a tag's browse page actually prints.

**This is a probe and not a parser, and the distinction is the point.** The price
bands on these pages have been seen once, in passing, on two tags. Their labels,
their boundaries, whether they sum to the total, and whether the page takes an
arbitrary range instead are all unknown. A parser written against a guess fails in
the one way that teaches nothing: its regex misses and the page looks empty. So this
file casts a wide net and prints what it catches, with context, and the parser is
written afterwards against what came back.

**Three things it is here to settle, each one a registered open item:**

1. **The resolution of a dispersion read off the published bands** (`D24`). Four or
   five bins with an open top bin is a coarse histogram, and how coarse decides
   whether any dispersion read off it clears the floor. The bands have to be seen
   before that can be computed.
2. **Whether the binning is a knob** (`11f`). If the page accepts an arbitrary price
   range, the histogram can be made as fine as the question needs and the resolution
   problem dissolves. If it does not, the published bands are the instrument and
   their structure is the floor. The page's own filter links are the answer, so they
   are read rather than guessed at (`D26`, `D39`: the document that states it).
3. **Seconds per request at each scale** (`D38`). The thickest tag and the thinnest
   differ by a factor of about seven hundred in project count, and a constant taken
   from one of them would misprice the other. No hours are quoted from a constant.

**And two open items it can settle for the price of one request each**, because the
same URL machinery does it: whether a nested pair really nests in membership rather
than only in its name, and how much two names for one market overlap. The second was
recorded as not detectable from names, which is true of names and not of this page.

**No dispersion is computed here and no reading is written.** The record is marked
diagnostic, and every page is cached so the parser that follows costs nothing.

Usage, on a machine with network access::

    python data/fetch_b30_4_itch_pages.py            # cache-first, print everything
    python data/fetch_b30_4_itch_pages.py --refresh  # fetch again, ignoring cache
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from html import unescape as html_unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "itch_tag_pages"
OUT = ROOT / "results" / "b30_4_itch_page_probe.json"

UA = "monetary-topology research binhongd@outlook.com"
DELAY_S = 1.5
MIN_BYTES = 4000

#: Three scales off the market side of the split, and the counts the directory
#: printed for them. The thick one is also a nested parent, so the pair probes
#: below reuse it.
SCALES = [
    ("thick",  "horror",   114_000),
    ("middle", "fishing",    4_228),
    ("thin",   "nonogram",     161),
]

#: Two pairs, each answering a named open item for one request.
#:   nested    does Lovecraftian horror sit inside horror in membership, or only in
#:             its name? The axis step three reads is built on nested pairs, so the
#:             nesting is checked rather than assumed.
#:   synonym   picross and nonogram are one puzzle under two names, and they share no
#:             letters, which is why names cannot detect it. The intersection can.
PAIRS = [
    ("nested",  "horror",   "lovecraft"),
    ("synonym", "picross",  "nonogram"),
]

TAGSTRIP = re.compile(r"<[^>]+>")
#: Wide net. Anything in an href that could be a price control, so the page's own
#: vocabulary comes back rather than the vocabulary this file guessed.
PRICEY = re.compile(r'href="([^"]*(?:price|free|sale|paid|currency)[^"]*)"', re.I)
#: A count printed next to a label, in any of the shapes this site uses elsewhere.
COUNTISH = re.compile(r'class="(game_count|games_count|count)"[^>]*>(.*?)</', re.S)
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
#: The header line that states how many the current filter matched.
TOTALISH = re.compile(r"([0-9][0-9,]*)\s*(?:results?|projects?|games?)\b", re.I)


def text(s):
    return re.sub(r"\s+", " ", html_unescape(TAGSTRIP.sub(" ", s))).strip()


def slugify(url):
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[:120]


def fetch(url, refresh):
    """Return (html, seconds, bytes, from_cache). Short bodies are kept as .partial
    and raise, so a truncated read can never be parsed as a real one."""
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


def describe(html, label):
    """Print what the page carries, without asserting a structure."""
    out = {"label": label}
    t = TITLE.search(html)
    out["title"] = text(t.group(1)) if t else None

    tot = TOTALISH.search(html)
    out["first_total_phrase"] = text(tot.group(0)) if tot else None

    hrefs = []
    seen = set()
    for m in PRICEY.finditer(html):
        h = html_unescape(m.group(1))
        if h in seen:
            continue
        seen.add(h)
        lo = max(0, m.start() - 160)
        hi = min(len(html), m.end() + 260)
        hrefs.append({"href": h, "around": text(html[lo:hi])[:300]})
    out["price_like_links"] = hrefs

    counts = [text(m.group(2)) for m in COUNTISH.finditer(html)]
    out["count_spans"] = counts[:40]
    out["count_spans_total"] = len(counts)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    record = {
        "station": "B30-4",
        "what": ("step three piece one: a probe of the itch.io tag browse page, to "
                 "find the price bands, whether the binning is a knob, and the cost "
                 "per request at three scales"),
        "prices_used_in_any_reading": False,
        "timing": [],
        "pages": [],
        "pairs": [],
        "diagnostic_only": True,
        "diagnostic_reason": ("A probe. It establishes what the page prints and costs. "
                              "No dispersion is computed and no criterion is scored."),
    }

    for scale, slug, directory_count in SCALES:
        url = f"https://itch.io/games/tag-{slug}"
        html, dt, n, cached = fetch(url, args.refresh)
        d = describe(html, f"{scale}: tag-{slug}")
        d.update({"scale": scale, "slug": slug, "url": url,
                  "directory_count": directory_count, "bytes": n})
        record["pages"].append(d)
        record["timing"].append({"url": url, "bytes": n, "seconds": dt,
                                 "from_cache": cached})
        print(f"\n{'=' * 78}\n{scale.upper()}  tag-{slug}   "
              f"directory said {directory_count:,}   {n:,} bytes   "
              f"{'cached' if cached else f'{dt:.2f}s'}\n{'=' * 78}")
        print(f"  <title>            {d['title']}")
        print(f"  first total phrase {d['first_total_phrase']}")
        print(f"  count spans        {d['count_spans_total']} found; "
              f"first few: {d['count_spans'][:10]}")
        print(f"  price-like links   {len(d['price_like_links'])}")
        for h in d["price_like_links"][:14]:
            print(f"      {h['href']}")
            print(f"          ...{h['around'][:180]}")

    for kind, a, b in PAIRS:
        url = f"https://itch.io/games/tag-{a}/tag-{b}"
        try:
            html, dt, n, cached = fetch(url, args.refresh)
        except urllib.error.HTTPError as e:
            print(f"\nPAIR {kind}: tag-{a} + tag-{b} -> HTTP {e.code}, "
                  f"so this URL form is not the way to intersect two tags")
            record["pairs"].append({"kind": kind, "a": a, "b": b, "url": url,
                                    "http_error": e.code})
            continue
        tot = TOTALISH.search(html)
        phrase = text(tot.group(0)) if tot else None
        t = TITLE.search(html)
        record["pairs"].append({"kind": kind, "a": a, "b": b, "url": url,
                               "bytes": n, "title": text(t.group(1)) if t else None,
                               "first_total_phrase": phrase})
        record["timing"].append({"url": url, "bytes": n, "seconds": dt,
                                 "from_cache": cached})
        print(f"\nPAIR {kind}: tag-{a} + tag-{b}   {n:,} bytes   "
              f"{'cached' if cached else f'{dt:.2f}s'}")
        print(f"      <title>            {text(t.group(1)) if t else None}")
        print(f"      first total phrase {phrase}")

    measured = [t for t in record["timing"] if t["seconds"] is not None]
    print(f"\n{'-' * 78}")
    if measured:
        print("seconds by response size, measured this run and not taken from a constant:")
        for t in sorted(measured, key=lambda x: x["bytes"]):
            print(f"   {t['bytes']:>9,} bytes   {t['seconds']:>6.2f}s   {t['url']}")
    else:
        print("every page came from cache, so no seconds were measured this run. "
              "No hours are quoted from a constant.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    print("Nothing here is a reading. The parser is written against what printed above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
