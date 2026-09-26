"""Fetch the raw auction-result pages B126 reads: one page per (chateau, vintage) in Sauternes.

What this is for. B126 asks whether a price moves further at each sale when the object trades
less often. The unit is a chateau and a vintage; the same chateau's vintages trade at very
different rates, so the density gradient sits on the vintage with producer, region, grape and
rules held fixed.

This script only fetches. It does not parse. The parser is written after the raw pages have
been read, because the page summaries seen so far disagree with themselves (one half bottle
priced per 750 ml and the next not, the same lot listed under two dates).

Crawl, in three stages, all on one site:
  1  the region page: it links producer pages and wine slugs, with no year on either
  2  every producer page, which links more wine slugs, still with no year
  3  every slug page (/wine/<slug>), which lists every vintage that ever traded
  4  every vintage page (/wine/<slug>/<year>) at or after --since-year
A hard cap on pages (--max-pages) stops it whatever the queue holds. Yquem alone lists 135
vintages, so --since-year and --slugs are how the sample is kept to the size the design states.

Rules this obeys:
  - resumable: a page on disk that passes the checks is skipped
  - never deletes: a page that fails the checks is renamed with a .bad_<n> suffix and refetched
  - detects truncation: HTTP 200, at least MIN_BYTES, and a closing </html>
  - prints a render gap: a vintage page whose title counts lots but that has no history
    table. Refetching it once returned the same page, so it is kept and flagged, not retried
  - measured cost only (`D38`): each request prints its seconds; no total is quoted
  - polite: PAUSE seconds between requests

Run from the repo root with the venv active, on a machine that can reach the site:
    python experiments/b126_fetch.py --list                 # the plan, no network
    python experiments/b126_fetch.py --fetch --max-pages 12 # depth gate first (`D21`)
    python experiments/b126_fetch.py --fetch                # full
    python experiments/b126_fetch.py --check                # re-verify what is on disk, no network
    python experiments/b126_fetch.py --selftest             # seeded faults, no network
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b126" / "raw"
MANIFEST = RAW / "manifest.json"

SITE = "https://wineauction.ai"
REGION = SITE + "/regions/bordeaux/sauternes"
# One known-good vintage page, so the crawl reaches at least one chateau's vintages
# even if the region page turns out to render its list client-side.
SEED = [SITE + "/wine/chateau-rieussec-premier-cru-classe-sauternes/2001"]

MIN_BYTES = 2000
PAUSE = 1.5
TIMEOUT = 30
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

RE_PRODUCER = re.compile(r'href="(?:https://wineauction\.ai)?(/producers/[a-z0-9-]+)/?"')
RE_VINTAGE = re.compile(r'href="(?:https://wineauction\.ai)?(/wine/([a-z0-9-]+)/((?:18|19|20)\d{2}))/?"')
RE_SLUG = re.compile(r'href="(?:https://wineauction\.ai)?(/wine/([a-z0-9-]+))/?"')


RE_TITLE_LOTS = re.compile(rb"<title>[^<]*?\b(?:18|19|20)\d{2} Auction Prices[^<]*?([\d,]+) Lots")


def render_gap(body: bytes) -> bool:
    """A vintage page whose title counts lots but which carries no history table.

    Rieussec 2010: title `50 Lots`, the summary block present, no AuctionHistoryTable component
    and no row. Refetched 2026-09-23 and it came back the same (104,789 B then 105,118 B, still no
    table), so the gap is the site's and persistent, not a broken transfer. The page is therefore
    written like any other and the gap is printed; failing the checks would set it aside and
    fetch it again on every run. The parser carries the flag and reads the unit as not
    retrieved, never as zero sales."""
    m = RE_TITLE_LOTS.search(body)
    return bool(m) and int(m.group(1).replace(b",", b"")) > 0 and b"AuctionHistoryTable" not in body


def page_ok(status: int, body: bytes) -> tuple[bool, str]:
    if status != 200:
        return False, f"status {status}"
    if len(body) < MIN_BYTES:
        return False, f"only {len(body)} bytes"
    if b"</html>" not in body[-4096:].lower():
        return False, "no closing </html> in the last 4 KB"
    return True, "ok"


def links(body: bytes) -> tuple[set[str], dict[str, set[str]]]:
    """Producer paths, and vintage paths grouped by slug."""
    text = body.decode("utf-8", errors="replace")
    producers = set(RE_PRODUCER.findall(text))
    vintages: dict[str, set[str]] = {}
    for path, slug, _year in RE_VINTAGE.findall(text):
        vintages.setdefault(slug, set()).add(path)
    return producers, vintages


def fname(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".html"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def save_manifest(m: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=RAW, prefix="manifest.", suffix=".tmp.expired")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, sort_keys=True, indent=1, ensure_ascii=False)
    os.replace(tmp, MANIFEST)


def set_aside(path: Path) -> None:
    n = 1
    while path.with_name(path.name + f".bad_{n}").exists():
        n += 1
    path.rename(path.with_name(path.name + f".bad_{n}"))


def cached(url: str, m: dict) -> bytes | None:
    p = RAW / fname(url)
    if not p.exists():
        return None
    body = p.read_bytes()
    ok, why = page_ok(m.get(url, {}).get("status", 200), body)
    if ok:
        return body
    print(f"  on disk but fails ({why}), set aside: {p.name}")
    set_aside(p)
    return None


def get(url: str, m: dict) -> bytes | None:
    body = cached(url, m)
    if body is not None:
        return body
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  FAIL {url}  {type(e).__name__}: {e}")
        return None
    secs = time.perf_counter() - t0
    ok, why = page_ok(status, body)
    print(f"  {secs:6.2f} s  {len(body):8d} B  {status}  {'ok ' if ok else 'BAD'}  {url}"
          + ("  RENDER-GAP: title counts lots, no history table" if ok and render_gap(body) else ""))
    time.sleep(PAUSE)
    if not ok:
        print(f"         not written: {why}")
        return None
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / fname(url)).write_bytes(body)
    m[url] = {"file": fname(url), "bytes": len(body), "status": status,
              "sha256": hashlib.sha256(body).hexdigest(), "seconds": round(secs, 3)}
    save_manifest(m)
    return body


def bare_slugs(body: bytes) -> set[str]:
    text = body.decode("utf-8", errors="replace")
    with_year = {s for _p, s, _y in RE_VINTAGE.findall(text)}
    return {s for _p, s in RE_SLUG.findall(text)} | with_year


def crawl(max_pages: int, since_year: int, want: set[str] | None) -> None:
    m = load_manifest()
    done = 0
    slugs: set[str] = set()

    def keep(slug: str) -> bool:
        return want is None or slug in want

    print("stage 1  region")
    body = get(REGION, m)
    done += 1
    prods: list[str] = []
    if body is not None:
        prods = sorted(links(body)[0])
        slugs |= bare_slugs(body)
        print(f"  {len(prods)} producer links, {len(slugs)} wine slugs")

    print("stage 2  producers")
    for p in prods:
        if done >= max_pages:
            break
        b = get(SITE + p, m)
        done += 1
        if b is not None:
            slugs |= bare_slugs(b)
    for s in SEED:
        slugs.add(s.split("/wine/")[1].split("/")[0])
    # Named slugs are fetched whether or not a crawled page links them: the region page links
    # only part of the appellation (Climens, Coutet, Guiraud, La Tour Blanche and
    # Lafaurie-Peyraguey were missing on 2026-09-22), and a filter can only narrow what was found.
    if want:
        slugs |= want
    slugs = {s for s in slugs if keep(s)}
    print(f"  {len(slugs)} slugs kept")

    print("stage 3  slug pages, for the vintage list")
    vintages: set[str] = set()
    for s in sorted(slugs):
        if done >= max_pages:
            break
        b = get(f"{SITE}/wine/{s}", m)
        done += 1
        if b is None:
            continue
        _, vint = links(b)
        for slug, paths in vint.items():
            if keep(slug):
                vintages |= {p for p in paths if int(p.rsplit("/", 1)[1]) >= since_year}
    vintages |= {u[len(SITE):] for u in SEED}
    print(f"  {len(vintages)} vintage pages at or after {since_year}")

    print("stage 4  vintage pages")
    for v in sorted(vintages):
        if done >= max_pages:
            break
        get(SITE + v, m)
        done += 1

    have = sum(1 for u in m if re.search(r"/wine/[a-z0-9-]+/\d{4}$", u))
    print(f"\npages requested this run: {done} (cap {max_pages})")
    print(f"vintage pages on disk: {have}; slugs kept: {len(slugs)}; vintages wanted: {len(vintages)}")


def check() -> int:
    m = load_manifest()
    bad = 0
    for url, rec in sorted(m.items()):
        p = RAW / rec["file"]
        if not p.exists():
            print(f"MISSING  {url}")
            bad += 1
            continue
        body = p.read_bytes()
        ok, why = page_ok(rec.get("status", 200), body)
        sha = hashlib.sha256(body).hexdigest() == rec.get("sha256")
        if not (ok and sha):
            print(f"BAD      {url}  {why}{'' if sha else ', sha256 differs'}")
            bad += 1
    print(f"{len(m)} pages in the manifest, {bad} failing")
    return 1 if bad else 0


def selftest() -> int:
    good = (b"<html><body>" + b"x" * MIN_BYTES
            + b'<a href="/producers/chateau-rieussec">p</a>'
            + b'<a href="https://wineauction.ai/wine/chateau-rieussec-premier-cru-classe-sauternes/2001">a</a>'
            + b'<a href="/wine/chateau-rieussec-premier-cru-classe-sauternes/1990/">b</a>'
            + b'<a href="/wine/chateau-d-yquem-sauternes/2001">c</a>'
            + b'<a href="/wine/some-slug/tasting-notes">not a vintage</a>'
            + b'<a href="/wine/chateau-climens-barsac">bare slug, no year</a>'
            + b"</body></html>")
    checks = []
    checks.append(("good page passes", page_ok(200, good)[0] is True))
    checks.append(("non-200 fails", page_ok(403, good)[0] is False))
    checks.append(("short page fails", page_ok(200, good[:500])[0] is False))
    checks.append(("truncated page fails", page_ok(200, good[:-20])[0] is False))
    # the title sits past the first 20 KB on the real pages; the seed puts it there too
    head = (b"<html>" + b"x" * 30000
            + b"<title>X, Sauternes 2010 Auction Prices (2026) | Avg $61 \xc2\xb7 50 Lots</title>")
    checks.append(("a vintage page counting lots with no history table is a render gap, deep title and all",
                   render_gap(head + b"</html>") is True))
    checks.append(("a render gap still passes the checks, so it is kept and not refetched forever",
                   page_ok(200, head + b"</html>")[0] is True))
    checks.append(("the same page with its history table is no gap",
                   render_gap(head + b"AuctionHistoryTable</html>") is False))
    checks.append(("a vintage page counting zero lots and no table is no gap",
                   render_gap(head.replace(b"50 Lots", b"0 Lots") + b"</html>") is False))
    prods, vint = links(good)
    checks.append(("one producer link", prods == {"/producers/chateau-rieussec"}))
    checks.append(("two slugs, non-vintage path ignored",
                   set(vint) == {"chateau-rieussec-premier-cru-classe-sauternes", "chateau-d-yquem-sauternes"}))
    checks.append(("absolute and trailing-slash forms both read",
                   vint["chateau-rieussec-premier-cru-classe-sauternes"]
                   == {"/wine/chateau-rieussec-premier-cru-classe-sauternes/2001",
                       "/wine/chateau-rieussec-premier-cru-classe-sauternes/1990"}))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.html"
        p.write_bytes(b"x")
        set_aside(p)
        p.write_bytes(b"y")
        set_aside(p)
        names = sorted(q.name for q in Path(d).iterdir())
        checks.append(("set aside never overwrites", names == ["a.html.bad_1", "a.html.bad_2"]))
    checks.append(("bare slug read, and a deeper path is not one",
                   bare_slugs(good) == {"chateau-rieussec-premier-cru-classe-sauternes",
                                        "chateau-d-yquem-sauternes", "chateau-climens-barsac"}))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--max-pages", type=int, default=400)
    ap.add_argument("--since-year", type=int, default=1980)
    ap.add_argument("--slugs", default="", help="comma separated; empty means every slug the region gives")
    a = ap.parse_args()
    want = {s.strip() for s in a.slugs.split(",") if s.strip()} or None
    if a.selftest:
        return selftest()
    if a.check:
        return check()
    if a.list:
        print(f"region  {REGION}")
        for s in SEED:
            print(f"seed    {s}")
        print(f"raw     {RAW}")
        print(f"cap     {a.max_pages} pages, {PAUSE} s between requests")
        print(f"years   {a.since_year} and later")
        print(f"slugs   {'every slug the region gives' if want is None else sorted(want)}")
        return 0
    crawl(a.max_pages, a.since_year, want)
    return 0


if __name__ == "__main__":
    sys.exit(main())
