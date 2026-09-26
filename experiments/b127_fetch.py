"""Fetch Sotheby's handbag sale pages for B127: every lot with its title and final price.

What a sale page holds, read off one page on 2026-09-23 before this was written: a Next.js
page whose __NEXT_DATA__ carries an Apollo cache. Each lot is a LotCard (title with model,
size, leather, colour, hardware and year stamp; estimate; sale and date) and a BidState
(closed, number of bids, and for a sold lot `sold.premiums.finalPriceV2`, the price with the
buyer's premium). The page holds the first 48 lots; the auction's lotCardsConnection gives
totalCount. No URL parameter pages past them (see crawl()); a lot page lists every lot of its
sale, so the rest are reached one lot page at a time in stage two.

Which sales. The department page links part of the handbag sales. Sotheby's names them
handbags-accessories, handbags-accessories-2, ... and a few with a location code; this script
probes those names for each year. A name that answers 404 is recorded as absent, not retried.

Rules this obeys:
  - robots.txt: Crawl-delay 15 for every agent; lot and sale pages are not disallowed
  - resumable: a page on disk that passes the checks is skipped
  - never deletes: a page that fails the checks is renamed .bad_<n> and fetched again
  - checks: HTTP 200, a closing </html>, a __NEXT_DATA__ block that parses; a sale page with
    no LotCard is kept and flagged, not read as a sale with no lots
  - measured cost only (`D38`): each request prints its seconds

Run from the repo root on this machine:
    python experiments/b127_fetch.py --list
    python experiments/b127_fetch.py --fetch --years 2019-2026
    python experiments/b127_fetch.py --plan-lots --years 2019-2026   # stage two's cost, no network
    python experiments/b127_fetch.py --lots --years 2023-2026        # stage two
    python experiments/b127_fetch.py --check
    python experiments/b127_fetch.py --selftest
"""
from __future__ import annotations

import argparse
import collections
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
RAW = ROOT / "data" / "b127" / "raw"
MANIFEST = RAW / "manifest.json"
SITE = "https://www.sothebys.com"
DEPT = SITE + "/en/departments/handbags-and-accessories"
PAUSE = 15.0          # robots.txt: Crawl-delay: 15
TIMEOUT = 40
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BASES = ["handbags-accessories", "handbags-and-accessories"]
MAX_SUFFIX = 12
RE_SALE = re.compile(r'/en/buy/auction/(20\d\d)/([a-z0-9-]+)')
RE_NEXT = re.compile(rb'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def next_data(body: bytes) -> dict | None:
    m = RE_NEXT.search(body)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def lots_on(body: bytes) -> tuple[int, int | None, bool | None]:
    """(LotCards on this page, the auction's totalCount, hasNextPage)."""
    nd = next_data(body)
    if nd is None:
        return 0, None, None
    cache = nd.get("props", {}).get("pageProps", {}).get("apolloCache", {}) or {}
    cards = sum(1 for k in cache if k.startswith(("LotCard:", "LotV2:")))
    total = more = None
    for k, v in cache.items():
        if k.startswith("Auction:"):
            for kk, vv in v.items():
                if kk.startswith("lotCardsConnection") and isinstance(vv, dict):
                    total, more = vv.get("totalCount"), vv.get("hasNextPage")
    return cards, total, more


def page_ok(status, body: bytes) -> tuple[bool, str]:
    if status != 200:
        return False, f"status {status}"
    if b"</html>" not in body[-4096:].lower():
        return False, "no closing </html>"
    if next_data(body) is None:
        return False, "no __NEXT_DATA__ that parses"
    return True, "ok"


def fname(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".html"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_manifest(m: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=RAW, prefix="manifest.", suffix=".tmp.expired")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, sort_keys=True, indent=1, ensure_ascii=False)
    os.replace(tmp, MANIFEST)


def set_aside(p: Path) -> None:
    n = 1
    while p.with_name(p.name + f".bad_{n}").exists():
        n += 1
    p.rename(p.with_name(p.name + f".bad_{n}"))


def get(url: str, m: dict) -> tuple[int | str, bytes | None]:
    """Returns (status, body). Absent names (404) are remembered in the manifest."""
    rec = m.get(url)
    if rec and rec.get("status") == 404:
        return 404, None
    p = RAW / fname(url)
    if p.exists():
        body = p.read_bytes()
        ok, why = page_ok(200, body)
        if ok:
            return 200, body
        print(f"  on disk but fails ({why}), set aside: {p.name}")
        set_aside(p)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"}),
                                    timeout=TIMEOUT) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  FAIL {url}  {type(e).__name__}: {e}")
        time.sleep(PAUSE)
        return "error", None
    secs = time.perf_counter() - t0
    time.sleep(PAUSE)
    if status == 404:
        m[url] = {"status": 404, "seconds": round(secs, 3)}
        save_manifest(m)
        print(f"  {secs:6.2f} s  404  absent  {url}")
        return 404, None
    ok, why = page_ok(status, body)
    cards, total, more = lots_on(body) if ok else (0, None, None)
    flag = "" if cards else "  NO-LOTS"
    print(f"  {secs:6.2f} s  {len(body):8d} B  {status}  {'ok ' if ok else 'BAD'}  lots {cards} of {total}{flag}  {url}")
    if not ok:
        print(f"         not written: {why}")
        return status, None
    RAW.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    m[url] = {"file": fname(url), "bytes": len(body), "status": status, "lots": cards, "total": total,
              "sha256": hashlib.sha256(body).hexdigest(), "seconds": round(secs, 3)}
    save_manifest(m)
    return status, body


def sale_urls(years: range, dept_body: bytes | None) -> list[str]:
    seen = set()
    if dept_body:
        for y, s in RE_SALE.findall(dept_body.decode("utf-8", "replace")):
            if int(y) in years and re.search(r"handbag|accessor", s):
                seen.add(f"{SITE}/en/buy/auction/{y}/{s}")
    for y in years:
        for b in BASES:
            seen.add(f"{SITE}/en/buy/auction/{y}/{b}")
            for n in range(2, MAX_SUFFIX + 1):
                seen.add(f"{SITE}/en/buy/auction/{y}/{b}-{n}")
    return sorted(seen)


def dept_names() -> bytes | None:
    """The department page has no __NEXT_DATA__, so it is read for its links and not stored."""
    try:
        with urllib.request.urlopen(urllib.request.Request(DEPT, headers={"User-Agent": UA, "Accept-Language": "en"}),
                                    timeout=TIMEOUT) as r:
            body = r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  department page not read: {e}")
        body = None
    time.sleep(PAUSE)
    return body


def crawl(years: range, max_requests: int) -> None:
    """Stage one: every sale page. A sale page shows its first 48 lots and nothing more:
    ?page=2, ?p=2, ?offset=48 and ?lotFilter=AllLots&page=2 all return the same 48 (checked
    2026-09-23; the later lots load in the browser through an API that robots.txt disallows).
    The lots after the 48th are fetched in stage two, one lot page each."""
    m = load_manifest()
    urls = sale_urls(years, dept_names())
    print(f"{len(urls)} candidate sale names")
    done = 0
    for u in urls:
        if done >= max_requests:
            print("request cap reached")
            break
        fresh = u not in m
        get(u, m)
        done += fresh
    sales = [(u, r) for u, r in m.items() if r.get("status") == 200 and "?" not in u and u.count("/") == 7]
    print(f"\nrequests this run {done}; sale pages on disk {len(sales)}; lots on the site {sum(r.get('total') or 0 for _, r in sales)}")


def sale_pages(m: dict, years: range) -> list[tuple[str, dict]]:
    return sorted((u, r) for u, r in m.items() if r.get("status") == 200 and "?" not in u and u.count("/") == 7
                  and int(u.split("/auction/")[1].split("/")[0]) in years)


def F_cache(body: bytes) -> dict:
    nd = next_data(body) or {}
    return nd.get("props", {}).get("pageProps", {}).get("apolloCache", {}) or {}


def slug_of(v: dict) -> str | None:
    """A LotCard carries slug as {"lotSlug": ...}; a lot page's LotV2 carries it as a string."""
    s = v.get("slug")
    return s.get("lotSlug") if isinstance(s, dict) else s


def lots_seen(body: bytes) -> dict[str, str]:
    """lotId -> lot slug for the lots a page carries (LotCard or LotV2)."""
    c = F_cache(body)
    return {v["lotId"]: slug_of(v) for k, v in c.items()
            if k.startswith(("LotCard:", "LotV2:")) and v.get("lotId")}


def full_list(body: bytes) -> dict[str, str]:
    """From a lot page: every lot of the sale, lotId -> lot slug."""
    for k, v in F_cache(body).items():
        if k.startswith("Auction:"):
            for kk, vv in v.items():
                if kk.startswith("lotCards(") and isinstance(vv, list):
                    return {x["lotId"]: slug_of(x) for x in vv if x.get("lotId")}
    return {}


def results_hidden(body: bytes) -> bool:
    """Every lot on the page carries sold.__typename == "ResultHidden": the prices are shown
    only to a logged-in user (all of 2020, one 2023 sale). Its lot pages would carry none either."""
    st = [((v.get("sold") or {}).get("__typename")) for k, v in F_cache(body).items() if k.startswith("BidState:")]
    return bool(st) and all(x == "ResultHidden" for x in st)


def plan_lots(years: range) -> None:
    """Pages stage two needs, from the totals on disk; no network."""
    m = load_manifest()
    per = collections.Counter()
    hidden = []
    for u, r in sale_pages(m, years):
        y = int(u.split("/auction/")[1].split("/")[0])
        if results_hidden((RAW / r["file"]).read_bytes()):
            hidden.append((u.split("/auction/")[1], r.get("total")))
            continue
        per[y] += max((r.get("total") or 0) - (r.get("lots") or 0), 0) + 1
    print(f"  sales with results hidden (skipped): {hidden}")
    tot = sum(per.values())
    for y in sorted(per):
        print(f"  {y}: {per[y]:>5} lot pages  ~{per[y] * PAUSE / 3600:.1f} h")
    print(f"  all: {tot} lot pages ~{tot * PAUSE / 3600:.1f} h at {PAUSE:g} s each")


def stage_two(years: range, max_requests: int) -> None:
    """Every lot a sale page did not show, one lot page each. The first lot page of a sale
    gives the sale's full list; lots already read (on the sale page or an earlier lot page)
    are skipped."""
    m = load_manifest()
    done = 0
    for u, r in sale_pages(m, years):
        if done >= max_requests:
            print("request cap reached")
            break
        body = (RAW / r["file"]).read_bytes()
        if results_hidden(body):
            print(f"  results hidden, skipped: {u}")
            continue
        seen = lots_seen(body)
        if not seen:
            print(f"  no lots on the sale page, skipped: {u}")
            continue
        first_slug = next(iter(seen.values()))
        lp = f"{u}/{first_slug}"
        fresh = lp not in m
        st, lb = get(lp, m)
        done += fresh
        if lb is None:
            continue
        allv = full_list(lb)
        seen.update(lots_seen(lb))
        todo = [(i, s) for i, s in allv.items() if i not in seen and s]
        # lots already fetched on an earlier run
        todo = [(i, s) for i, s in todo if f"{u}/{s}" not in m or m[f"{u}/{s}"].get("status") != 200]
        print(f"{u.split('/auction/')[1]}: {len(allv)} lots, {len(seen)} read, {len(todo)} to fetch")
        for i, s in todo:
            if done >= max_requests:
                break
            fresh = f"{u}/{s}" not in m
            get(f"{u}/{s}", m)
            done += fresh
    print(f"\nrequests this run {done}")


def check() -> int:
    m = load_manifest()
    bad = 0
    for url, rec in sorted(m.items()):
        if rec.get("status") == 404:
            continue
        p = RAW / rec["file"]
        if not p.exists():
            print(f"MISSING {url}")
            bad += 1
            continue
        body = p.read_bytes()
        ok, why = page_ok(200, body)
        if not ok or hashlib.sha256(body).hexdigest() != rec["sha256"]:
            print(f"BAD {url} {why}")
            bad += 1
    print(f"{len(m)} entries, {bad} failing")
    return 1 if bad else 0


def selftest() -> int:
    nd = {"props": {"pageProps": {"apolloCache": {
        "LotCard:a": {"title": "x"}, "LotCard:b": {"title": "y"},
        "Auction:z": {'lotCardsConnection({"filter":"ALL","limit":48,"offset":0})': {"totalCount": 117, "hasNextPage": True}}}}}}
    good = (b'<html><script id="__NEXT_DATA__" type="application/json">' + json.dumps(nd).encode() + b"</script></html>")
    checks = [
        ("good page passes", page_ok(200, good)[0]),
        ("non-200 fails", not page_ok(403, good)[0]),
        ("no closing tag fails", not page_ok(200, good[:-10])[0]),
        ("no __NEXT_DATA__ fails", not page_ok(200, b"<html></html>")[0]),
        ("lots, total and next page read", lots_on(good) == (2, 117, True)),
        ("a page with no lot cards reads zero lots", lots_on(b'<html><script id="__NEXT_DATA__">{}</script></html>')[0] == 0),
        ("candidate names cover the suffixes", f"{SITE}/en/buy/auction/2025/handbags-accessories-12" in sale_urls(range(2025, 2026), None)),
        ("the department page's own names are kept", f"{SITE}/en/buy/auction/2025/handbags-accessories-zh2540" in
         sale_urls(range(2025, 2026), b'<a href="/en/buy/auction/2025/handbags-accessories-zh2540">')),
    ]
    lot_nd = {"props": {"pageProps": {"apolloCache": {
        "LotV2:a": {"lotId": "a", "slug": "x"},
        "Auction:z": {'lotCards({"countryOfOrigin":"US","filter":"ALL"})': [
            {"lotId": "a", "slug": {"lotSlug": "x"}}, {"lotId": "b", "slug": {"lotSlug": "y"}}]}}}}}
    lb = (b'<html><script id="__NEXT_DATA__" type="application/json">' + json.dumps(lot_nd).encode() + b"</script></html>")
    checks.append(("a lot page gives the sale's full list", full_list(lb) == {"a": "x", "b": "y"}))
    hid = {"props": {"pageProps": {"apolloCache": {"BidState:a": {"sold": {"__typename": "ResultHidden"}},
                                                   "BidState:b": {"sold": {"__typename": "ResultHidden"}}}}}}
    vis = {"props": {"pageProps": {"apolloCache": {"BidState:a": {"sold": {"__typename": "ResultHidden"}},
                                                   "BidState:b": {"sold": {"__typename": "ResultVisible"}}}}}}
    wrap = lambda d: b'<html><script id="__NEXT_DATA__">' + json.dumps(d).encode() + b"</script></html>"
    checks.append(("a sale with every result hidden is skipped", results_hidden(wrap(hid))))
    checks.append(("one visible result keeps the sale", not results_hidden(wrap(vis))))
    checks.append(("a lot page's own lot is read as seen", lots_seen(lb) == {"a": "x"}))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.html"
        p.write_bytes(b"x"); set_aside(p); p.write_bytes(b"y"); set_aside(p)
        checks.append(("set aside never overwrites", sorted(q.name for q in Path(d).iterdir()) == ["a.html.bad_1", "a.html.bad_2"]))
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for a in ("--list", "--fetch", "--lots", "--plan-lots", "--check", "--selftest"):
        g.add_argument(a, action="store_true")
    ap.add_argument("--years", default="2019-2026")
    ap.add_argument("--max-requests", type=int, default=400)
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    years = range(y0, y1 + 1)
    if a.selftest:
        return selftest()
    if a.check:
        return check()
    if a.plan_lots:
        plan_lots(years)
        return 0
    if a.lots:
        stage_two(years, a.max_requests)
        return 0
    if a.list:
        print(f"{len(sale_urls(years, None))} candidate names before the department page; pause {PAUSE} s")
        return 0
    crawl(years, a.max_requests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
