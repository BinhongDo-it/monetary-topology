"""Fetch and parse the daily Zimbabwe market-rate posts from a web archive.

One post per calendar day; each post prints several quoted rates for the same
currency pair, each with a named source. The parser keeps them in long form
(date, label, source, value) so a rail that was never anticipated shows up as a
new row instead of being dropped.

Resumable: a saved page is re-fetched only when it fails the content check.
Run with --limit first to price one request before pricing the whole job.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "zw" / "mw"
INDEX = HERE / "raw" / "zw" / "mw_index.json"
OUT = HERE / "raw" / "zw" / "zw_rates_long.csv"

CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web/{ts}id_/{url}"
UA = "Mozilla/5.0 (compatible; research-fetch/1.0)"

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june",
     "july", "august", "september", "october", "november", "december"], 1)}

SLUG = re.compile(r"/(\d{1,2})-([a-z]+)-(\d{4})-market-rates/?$", re.I)


def get(url: str, tries: int = 4) -> bytes:
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last = e
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"{url}: {last}")


def build_index() -> dict[str, str]:
    """slug date (YYYY-MM-DD) -> wayback timestamp, one capture per post."""
    if INDEX.exists():
        return json.loads(INDEX.read_text(encoding="utf-8"))
    q = urllib.parse.urlencode({
        "url": "marketwatch.co.zw*",
        "from": "20190101", "to": "20220101",
        "fl": "timestamp,original",
        "collapse": "urlkey",
        "limit": "80000",
    })
    rows = get(f"{CDX}?{q}").decode("utf-8", "replace").splitlines()
    idx: dict[str, str] = {}
    for line in rows:
        parts = line.split()
        if len(parts) != 2:
            continue
        ts, url = parts
        m = SLUG.search(url)
        if not m:
            continue
        mon = MONTHS.get(m.group(2).lower())
        if mon is None:
            continue
        day = f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
        # keep the earliest capture of each post
        if day not in idx or ts < idx[day]:
            idx[day] = ts
        idx.setdefault(day + "|url", url)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, indent=1, sort_keys=True), encoding="utf-8")
    return idx


def looks_complete(text: str) -> bool:
    return "Market rates" in text and "OMIR" in text and "Share this post" in text


def to_text(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|tr|li|h\d|td|th)>", "\n", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)
    t = html.unescape(t)
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n")]
    return "\n".join(x for x in lines if x)


PUB = re.compile(
    r'(?is)(?:article:published_time"\s*content="|"datePublished"\s*:\s*")(\d{4})-(\d{2})-(\d{2})')


def reference_date(raw: bytes, slug_day: str) -> tuple[str, str]:
    """The date the rates refer to, and a note when it had to be corrected.

    The title carries the reference date, so it is the key. But posts written in
    the first days of January carry the previous year in the title, a typo the
    page's own published_time contradicts by about a year. Trust the title's day
    and month, take the year from the metadata when the two are far apart.
    """
    text = raw.decode("utf-8", "replace")
    m = PUB.search(text)
    if not m:
        return slug_day, ""
    pub = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    slug = dt.date.fromisoformat(slug_day)
    if abs((pub - slug).days) <= 60:
        return slug_day, ""
    try:
        fixed = dt.date(pub.year, slug.month, slug.day)
    except ValueError:
        fixed = pub
    return fixed.isoformat(), f"slug {slug_day} -> {fixed} (published {pub})"


TITLE = re.compile(r"^\d{1,2}\s+[A-Za-z]+\s+\d{4}\s*[-–]\s*Market rates\s*$", re.M)
NUM = r"([0-9][0-9,]*\.?[0-9]*)"
RE_OMIR = re.compile(r"^OMIR\s*" + NUM, re.M)
RE_RAIL = re.compile(r"^USD\s*/\s*([A-Z$]+)\s*" + NUM + r"?\s*\(([^)]+)\)", re.M)


def parse(text: str, day: str) -> list[tuple[str, str, str, str]]:
    """Return rows (date, pair, source, value). Main post only, sidebar excluded."""
    m = TITLE.search(text)
    if not m:
        return []
    tail = text[m.end():]
    stop = tail.find("Share this post")
    body = tail[:stop] if stop > 0 else tail[:400]
    rows: list[tuple[str, str, str, str]] = []
    om = RE_OMIR.search(body)
    if om:
        rows.append((day, "OMIR", "marketwatch", om.group(1).replace(",", "")))
    for pair, val, src in RE_RAIL.findall(body):
        rows.append((day, "USD/" + pair.replace("$", ""), src.strip(),
                     (val or "").replace(",", "")))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="fetch at most N new pages")
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--parse-only", action="store_true")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    idx = build_index()
    days = sorted(k for k in idx if "|" not in k)
    print(f"index: {len(days)} posts, {days[0]} .. {days[-1]}")

    fetched = 0
    t0 = time.time()
    if not args.parse_only:
        for day in days:
            path = RAW / f"{day}.html"
            if path.exists():
                try:
                    if looks_complete(to_text(path.read_bytes())):
                        continue
                except Exception:
                    pass
            if args.limit and fetched >= args.limit:
                break
            url = idx[day + "|url"]
            body = get(WB.format(ts=idx[day], url=url))
            path.write_bytes(body)
            fetched += 1
            ok = looks_complete(to_text(body))
            print(f"  {day}  {len(body):7d} bytes  complete={ok}")
            time.sleep(args.sleep)
        if fetched:
            print(f"fetched {fetched} in {time.time() - t0:.1f}s "
                  f"({(time.time() - t0) / fetched:.2f}s each)")

    rows: list[tuple[str, str, str, str]] = []
    bad: list[str] = []
    fixes: list[str] = []
    for day in days:
        path = RAW / f"{day}.html"
        if not path.exists():
            continue
        raw = path.read_bytes()
        ref, note = reference_date(raw, day)
        if note:
            fixes.append(note)
        got = parse(to_text(raw), ref)
        if got:
            rows.extend(got)
        else:
            bad.append(day)
    rows.sort()
    OUT.write_text(
        "date,pair,source,value\n" + "".join(",".join(r) + "\n" for r in rows),
        encoding="utf-8", newline="\n")
    srcs: dict[str, int] = {}
    for _, pair, src, _v in rows:
        srcs[f"{pair} ({src})"] = srcs.get(f"{pair} ({src})", 0) + 1
    print(f"parsed {len(rows)} rows over "
          f"{len({r[0] for r in rows})} days -> {OUT.name}")
    for k in sorted(srcs, key=lambda x: -srcs[x]):
        print(f"    {srcs[k]:5d}  {k}")
    if fixes:
        (RAW.parent / "date_corrections.txt").write_text(
            "\n".join(sorted(fixes)) + "\n", encoding="utf-8", newline="\n")
        print(f"date corrections: {len(fixes)} (see date_corrections.txt)")
        for f in sorted(fixes):
            print(f"    {f}")
    if bad:
        print(f"unparsed pages: {len(bad)}  first: {bad[:5]}")


if __name__ == "__main__":
    main()
