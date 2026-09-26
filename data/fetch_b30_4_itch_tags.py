"""Step one of the B30-4 tag census: names and counts only, no price is read.

**Why this exists.** B30-4 reads the dispersion of an entry price against the
density of comparables at a destination. The carrier is itch.io, chosen because the
count of a category comes off the platform's own register rather than off anyone's
crawl, and because the creator puts the tag on the project. The treatment variable
is the size of a tag, and this file buys the whole treatment axis in one pass: the
tag directory prints a count beside every tag, so sixteen pages give every tag's
size without asking each tag in turn.

**What this file deliberately does not do.** It does not fetch a single price. The
split of the vocabulary into the tags that name a kind of thing and the tags that
name an attribute is applied to the names alone and recorded before any price band
is pulled, and a fetcher that carried prices in the same pass would make that order
unenforceable.

**Resolution of the printed count.** The directory abbreviates above ten thousand,
`505k projects`, and prints exactly below it, `7,246 projects`. The abbreviation is
a fixed publication format, so the resolution is three significant figures and it
is relative rather than absolute. That bites only where the count is large, and the
thin end, which is the end this arm reads, is printed exactly. An exact figure for
any single tag costs one request against its own browse page and is not taken here.

Resumable: every page is cached under ``data/raw/itch_tags`` and a cached page is
not refetched. A page that parses to zero tags is quarantined with a ``.partial``
suffix and left in place, and the run stops rather than walking past it.

Cost: measured, never assumed. The seconds per page are timed and printed per page
and as a median; no total is quoted from a constant.

Usage, on a machine with network access::

    python data/fetch_b30_4_itch_tags.py --probe     # page one only, print the parse
    python data/fetch_b30_4_itch_tags.py             # all pages, cache-first
    python data/fetch_b30_4_itch_tags.py --refresh 3 # fetch page three again
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
import urllib.error
import urllib.request
from html import unescape as html_unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "itch_tags"
OUT = ROOT / "results" / "b30_4_itch_tag_census.json"
MANIFEST = CACHE / "manifest.json"

BASE = "https://itch.io/tags"
UA = "monetary-topology research binhongd@outlook.com"
DELAY_S = 1.5
MIN_BYTES = 4000

#: Each directory entry is one ``<li class="tag_cell">``. The cell opens with a
#: header link wrapping five preview images, so a forward search from the first
#: link inside a cell runs past the cell boundary on image-heavy cards and picks up
#: the next card's count. Parsing per cell removes that failure mode entirely.
CELL_OPEN = '<li class="tag_cell">'
#: ``<a class="tag_title" href="/games/tag-horror">Horror</a>``, and the same
#: attributes in the other order, which the directory also emits. Two lookaheads
#: make the order irrelevant, and they cannot cross the tag because of ``[^>]``.
#: The directory mixes genre cells in with the tag cells, both carrying counts,
#: so the axis is captured rather than skipped.
#: A third cell shape carries neither prefix, ``/games/local-multiplayer``. It is
#: a feature axis rather than a tag or a genre, and it is captured under its own
#: kind so that the skipped count stays a real anomaly rather than a known one.
TITLE = re.compile(
    r'<a(?=[^>]*class="tag_title")'
    r'(?=[^>]*href="/([a-z\-]+)/(?:(tag|genre)-)?([a-z0-9][a-z0-9\-]*)")[^>]*>(.*?)</a>',
    re.S)
#: ``<span class="games_count"><strong>505k projects</strong>``. Anchored on the
#: class so the "N this week" figure beside it can never be read instead.
COUNT = re.compile(r'class="games_count"><strong>([0-9][0-9,]*(?:\.[0-9]+)?)\s*([km]?)\s*projects',
                   re.I)
TAGS = re.compile(r"<[^>]+>")


def widen(num, suffix):
    """Return (value, how the page printed it). The second element is kept so the
    record shows which values are abbreviated and which are exact."""
    raw = num.replace(",", "")
    if suffix.lower() == "k":
        return int(round(float(raw) * 1_000)), "abbreviated"
    if suffix.lower() == "m":
        return int(round(float(raw) * 1_000_000)), "abbreviated"
    return int(float(raw)), "exact"


def page_url(n):
    return BASE if n == 1 else f"{BASE}?page={n}"


def fetch(n, refresh):
    """Return (html, seconds). ``seconds`` is None when the page came from cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"page_{n:02d}.html"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8", errors="replace"), None
    req = urllib.request.Request(page_url(n), headers={"User-Agent": UA})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", errors="replace")
    dt = time.monotonic() - t0
    if len(body.encode("utf-8")) < MIN_BYTES:
        bad = CACHE / f"page_{n:02d}.html.partial"
        bad.write_text(body, encoding="utf-8", newline="\n")
        raise RuntimeError(f"page {n} came back short ({len(body)} chars); kept at {bad.name}")
    path.write_text(body, encoding="utf-8", newline="\n")
    time.sleep(DELAY_S)
    return body, dt


def parse(html):
    """Split on the cell container and read the title and the count inside each
    cell. Returns (rows, cells_seen, skipped): a cell that is missing either field
    is counted in ``skipped`` rather than dropped in silence, so a shape change
    shows up as a number instead of as a shorter list. Returns no rows when the
    container itself has moved, which the caller treats as a stop."""
    rows, skipped = [], 0
    segments = html.split(CELL_OPEN)[1:]
    for seg in segments:
        t = TITLE.search(seg)
        c = COUNT.search(seg)
        if not t or not c:
            skipped += 1
            continue
        value, how = widen(c.group(1), c.group(2))
        rows.append({
            "kind": t.group(2) or "feature",
            "slug": t.group(3),
            "name": html_unescape(TAGS.sub("", t.group(4))).strip(),
            "scope": t.group(1),
            "count": value,
            "printed_as": how,
        })
    return rows, len(segments), skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="page one only, print the parse")
    ap.add_argument("--pages", type=int, default=16)
    ap.add_argument("--refresh", type=int, default=0, help="fetch this page again")
    args = ap.parse_args()

    pages = 1 if args.probe else args.pages
    tags = {}
    timings = []
    total_skipped = 0
    first_seen = {}
    if MANIFEST.exists():
        first_seen = json.loads(MANIFEST.read_text(encoding="utf-8")).get("first_seen", {})

    for n in range(1, pages + 1):
        try:
            html, dt = fetch(n, refresh=(args.refresh == n))
        except (urllib.error.URLError, RuntimeError) as exc:
            print(f"page {n:2d}: STOP, {exc}")
            return 2
        rows, cells, skipped = parse(html)
        if not rows:
            bad = CACHE / f"page_{n:02d}.html"
            if bad.exists():
                bad.rename(bad.with_suffix(".html.partial"))
            print(f"page {n:2d}: STOP, parsed zero tags out of {cells} cell(s); the page "
                  f"shape has moved. Kept at page_{n:02d}.html.partial, nothing deleted.")
            return 2
        total_skipped += skipped
        if dt is not None:
            timings.append(dt)
            first_seen.setdefault(f"page_{n:02d}", time.strftime("%Y-%m-%d", time.gmtime()))
        for r in rows:
            tags.setdefault((r["kind"], r["slug"]), r)
        shown = "cached" if dt is None else f"{dt:.2f}s"
        print(f"page {n:2d}: {len(rows):4d} of {cells:4d} cells, {skipped} skipped, "
              f"{shown}, running total {len(tags)}")

    if args.probe:
        for r in sorted(tags.values(), key=lambda d: -d["count"])[:25]:
            print(f"  {r['count']:>9,}  {r['printed_as']:<12} {r['scope']:<12} {r['name']}")
        print("\nprobe only: nothing was written to results/")
        return 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"first_seen": first_seen}, indent=2, sort_keys=True),
                        encoding="utf-8", newline="\n")

    rows = sorted(tags.values(), key=lambda d: (d["kind"], -d["count"], d["slug"]))
    exact = sum(1 for r in rows if r["printed_as"] == "exact")
    by_kind = {k: sum(1 for r in rows if r["kind"] == k) for k in sorted({r["kind"] for r in rows})}
    record = {
        "station": "B30-4",
        "what": "itch.io tag directory, names and counts only. No price is read here.",
        "config": {"base": BASE, "pages": pages, "delay_s": DELAY_S},
        "source": {"directory": BASE,
                   "collected": sorted(set(first_seen.values())) or ["from cache"]},
        "resolution": ("counts above ten thousand are printed to three significant figures "
                       "with a k or m suffix; below that they are printed exactly"),
        "cells_skipped": total_skipped,
        "by_kind": by_kind,
        "scopes": sorted({r["scope"] for r in rows}),
        "tags_total": len(rows),
        "printed_exactly": exact,
        "printed_abbreviated": len(rows) - exact,
        "span": {k: {"largest": max(r["count"] for r in rows if r["kind"] == k),
                      "smallest": min(r["count"] for r in rows if r["kind"] == k)}
                 for k in by_kind},
        "tags": rows,
        "diagnostic_only": True,
        "diagnostic_reason": ("Step one of three. The split of these names into market tags and "
                              "attribute tags is not applied here, and no price band has been "
                              "pulled, so nothing in this file is a reading of B30-4."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")

    print(f"\n{len(rows)} entries {by_kind}, {exact} printed exactly, "
          f"{len(rows) - exact} abbreviated, {total_skipped} cell(s) skipped")
    for k in by_kind:
        sub = [r["count"] for r in rows if r["kind"] == k]
        print(f"  {k:<6} span {min(sub):,} to {max(sub):,}")
    if timings:
        print(f"seconds per page, measured: min {min(timings):.2f}, "
              f"median {statistics.median(timings):.2f}, max {max(timings):.2f} "
              f"over {len(timings)} fetched page(s)")
    else:
        print("seconds per page: not measured this run, every page came from cache. "
              "No hours are quoted from a constant.")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
