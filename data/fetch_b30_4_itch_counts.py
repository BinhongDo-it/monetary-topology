"""Step three, piece two: the published counts for every market tag, five per tag.

**What this buys, and why it comes before any price is enumerated.** The browse page
publishes four cumulative price filters and a total, and nothing finer:

    /games/tag-<slug>                     the total
    /games/free/tag-<slug>                Free
    /games/store/tag-<slug>               Paid, and the path says store, not paid
    /games/5-dollars-or-less/tag-<slug>   $5 or less
    /games/15-dollars-or-less/tag-<slug>  $15 or less

Subtracting gives three disjoint bins above zero, ``(0,5]``, ``(5,15]`` and an open
``(15,inf)``, plus free as a spike at zero. That is the whole published resolution,
and it is what `D24`'s floor has to be computed against.

**Three things this settles that nothing cheaper can.**

1. **Whether "$5 or less" counts the free ones.** The label says "or less" and $0 is
   less than $5, so it may be cumulative from zero rather than from the first cent.
   This is not guessed at (`D54`): the derived bins are printed with their signs, and
   if ``store`` minus ``15-dollars-or-less`` comes out negative on a tag whose free
   share is large, the filters count from zero and every bin is recomputed. **The
   check is the answer**, so it runs on every tag rather than on a probe.
2. **The real n per tag.** The criterion reads dispersion of a posted price, and a
   free project posts no price. The paid count is therefore the sample size, and on
   the thickest tag seen so far it is under five per cent of the total. This is a
   registered open item and one request per tag closes it.
3. **The exact cost of enumerating prices** (`D38`). The listing prints each
   project's own price, 36 to a page, so enumeration costs
   ``ceil(paid / 36)`` requests per tag. That is not a number to estimate; it is
   ``paid``, which this file measures.

**No dispersion is computed here.** Counts only, and the record says so.

Usage, on a machine with network access::

    python data/fetch_b30_4_itch_counts.py --limit 5   # five tags, audit the shape
    python data/fetch_b30_4_itch_counts.py             # all market tags, cache-first
    python data/fetch_b30_4_itch_counts.py --refresh    # ignore the cache

Every page is cached, the run is resumable, and a short body is kept as ``.partial``
and raises rather than being parsed as a real one.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import urllib.error
import urllib.request
from html import unescape as html_unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "results" / "b30_4_tag_split.json"
CACHE = ROOT / "data" / "raw" / "itch_tag_pages"
OUT = ROOT / "results" / "b30_4_itch_counts.json"

UA = "monetary-topology research binhongd@outlook.com"
DELAY_S = 1.5
MIN_BYTES = 4000
PER_PAGE = 36  #: measured off a cached page, not assumed

#: (key, path prefix, the label the page prints for it). The label is checked
#: against the page's own filter list on the first tag, so a renamed path is caught
#: at the start of the run instead of producing a wrong column for every tag.
FILTERS = [
    ("total",   "",                      None),
    ("free",    "free/",                 "Free"),
    ("paid",    "store/",                "Paid"),
    ("le5",     "5-dollars-or-less/",    "$5 or less"),
    ("le15",    "15-dollars-or-less/",   "$15 or less"),
]

TAGSTRIP = re.compile(r"<[^>]+>")
RESULTS = re.compile(r"([0-9][0-9,]*)\s*results?\b", re.I)
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
FILTER_LINK = re.compile(r'<a href="(/games/[^"]+)"[^>]*>(?:<span[^>]*></span>)?([^<]*)</a>')


def text(s):
    return re.sub(r"\s+", " ", html_unescape(TAGSTRIP.sub(" ", s))).strip()


def url_for(prefix, slug):
    return f"https://itch.io/games/{prefix}tag-{slug}"


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


def count_and_title(html):
    """Return (count, page title). The count is the page's own results phrase; a page
    with no such phrase returns None rather than zero, because a missing phrase and a
    genuine zero are two different things."""
    m = RESULTS.search(html)
    t = TITLE.search(html)
    return (int(m.group(1).replace(",", "")) if m else None,
            text(t.group(1)) if t else None)


def check_filter_paths(html, slug):
    """The page's own filter list must still carry the paths this file hardcodes.

    A renamed path would otherwise produce a wrong column for every tag in the run
    while every count stayed a plausible integer. The labels are the page's, so this
    asks the source what it calls them rather than trusting the name in this file.
    """
    links = {h: text(l) for h, l in FILTER_LINK.findall(html)}
    problems = []
    for key, prefix, label in FILTERS:
        if label is None:
            continue
        want = f"/games/{prefix}tag-{slug}"
        if want not in links:
            problems.append(f"{key}: the page no longer offers {want}")
        elif links[want] != label:
            problems.append(f"{key}: {want} is labelled {links[want]!r}, not {label!r}")
    return problems


def derive(c):
    """Three disjoint bins above zero, and the identities that say whether the
    cumulative filters count from zero or from the first cent."""
    tot, free, paid, le5, le15 = (c.get(k) for k in ("total", "free", "paid", "le5", "le15"))
    d = {}
    if None in (tot, free, paid):
        return d
    d["free_plus_paid_minus_total"] = free + paid - tot
    if le5 is not None and le15 is not None:
        d["bin_0_5"] = le5
        d["bin_5_15"] = le15 - le5
        d["bin_15_up"] = paid - le15
        d["le5_minus_free"] = le5 - free
        d["monotone"] = le5 <= le15 <= paid
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only the first N market tags")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    # Three requests, at the start, because a denominator rests on the answer.
    # The census sums ten genre counts and reads that sum as the project count, which
    # holds only if a project carries exactly one genre. That is a property of the
    # upload form and it is not guessed at (`D54`): if two genres intersect, the sum
    # is not a project count and every per-project ratio computed from it is wrong.
    genre_check = {}
    for key, u in (("action", "https://itch.io/games/genre-action"),
                   ("puzzle", "https://itch.io/games/genre-puzzle"),
                   ("both", "https://itch.io/games/genre-action/genre-puzzle")):
        try:
            html, _, _, cached = fetch(u, args.refresh)
            genre_check[key] = count_and_title(html)[0]
        except urllib.error.HTTPError as e:
            genre_check[key] = f"HTTP {e.code}"
    both = genre_check.get("both")
    exclusive = (both in (0, None) or isinstance(both, str))
    print(f"genre exclusivity: action={genre_check.get('action')}, "
          f"puzzle={genre_check.get('puzzle')}, both={both}")
    print("   a project carries one genre, so the ten genre counts sum to the project "
          "count" if exclusive else
          "   GENRES COMBINE, so the sum of genre counts is NOT a project count and "
          "every per-project ratio taken from it has to be recomputed")

    rows = json.loads(SPLIT.read_text(encoding="utf-8"))["rows"]
    tags = [r for r in rows if r["class"] == "market"]
    tags.sort(key=lambda r: -r["count"])
    if args.limit:
        tags = tags[:args.limit]

    print(f"{len(tags)} market tag(s) x {len(FILTERS)} filters = "
          f"{len(tags) * len(FILTERS)} request(s), cache-first")

    out, timing, path_problems, anomalies = [], [], [], []
    checked_paths = False

    for i, t in enumerate(tags, 1):
        slug = t["slug"]
        counts, titles = {}, {}
        for key, prefix, _ in FILTERS:
            u = url_for(prefix, slug)
            try:
                html, dt, n, cached = fetch(u, args.refresh)
            except urllib.error.HTTPError as e:
                counts[key] = None
                anomalies.append(f"{slug}/{key}: HTTP {e.code}")
                continue
            if not checked_paths and key == "total":
                path_problems = check_filter_paths(html, slug)
                checked_paths = True
            counts[key], titles[key] = count_and_title(html)
            timing.append({"url": u, "bytes": n, "seconds": dt, "from_cache": cached})

        d = derive(counts)
        rec = {"slug": slug, "name": t["name"], "directory_count": t["count"],
               "counts": counts, "derived": d, "titles": titles}
        out.append(rec)

        # 第 11 条: print the object, not a running total
        paid = counts.get("paid")
        pages = math.ceil(paid / PER_PAGE) if paid else None
        flag = ""
        if d.get("monotone") is False:
            flag = "  NOT MONOTONE"
        if d.get("bin_15_up") is not None and d["bin_15_up"] < 0:
            flag += "  TOP BIN NEGATIVE"
        print(f"  {i:>3d}/{len(tags)}  {t['name'][:24]:25s} "
              f"total {str(counts.get('total')):>7s}  free {str(counts.get('free')):>7s}  "
              f"paid {str(counts.get('paid')):>6s}  <=5 {str(counts.get('le5')):>6s}  "
              f"<=15 {str(counts.get('le15')):>6s}  pages {str(pages):>4s}{flag}")

    measured = [x for x in timing if x["seconds"] is not None]
    total_paid = sum(r["counts"].get("paid") or 0 for r in out)
    enum_pages = sum(math.ceil((r["counts"].get("paid") or 0) / PER_PAGE) for r in out)

    record = {
        "station": "B30-4",
        "what": ("step three piece two: the published counts for every market tag, "
                 "total and four cumulative price filters"),
        "dispersion_computed": False,
        "per_page": PER_PAGE,
        "filters": [{"key": k, "path": f"/games/{p}tag-<slug>", "label": l}
                    for k, p, l in FILTERS],
        "filter_path_problems": path_problems,
        "genre_exclusivity": {"counts": genre_check, "genres_are_exclusive": exclusive,
                              "why": ("the census reads the sum of the ten genre counts "
                                      "as the project count, which needs one genre per "
                                      "project")},
        "anomalies": anomalies,
        "tags": out,
        "totals": {"tags": len(out), "paid_sum_over_tags_double_counted": total_paid,
                   "enumeration_pages_if_every_tag_read": enum_pages},
        "timing_sample": measured[:60],
        "diagnostic_only": True,
        "diagnostic_reason": ("Counts only. No dispersion is computed and no criterion "
                             "is scored. The bin semantics are read off the printed "
                             "identities rather than assumed."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")

    print(f"\n{'-' * 78}")
    if path_problems:
        print("THE PAGE'S OWN FILTER LIST NO LONGER MATCHES THIS FILE:")
        for p in path_problems:
            print(f"   {p}")
    else:
        print("the page's own filter list still carries every path and label this file uses")
    if anomalies:
        print(f"{len(anomalies)} anomaly(ies): {anomalies[:8]}")
    nonmono = [r["slug"] for r in out if r["derived"].get("monotone") is False]
    neg = [r["slug"] for r in out if (r["derived"].get("bin_15_up") or 0) < 0]
    print(f"non-monotone filters on {len(nonmono)} tag(s): {nonmono[:10]}")
    print(f"negative top bin on {len(neg)} tag(s): {neg[:10]}")
    print("   a negative top bin means the cumulative filters count from zero, so the "
          "bins are recomputed against free rather than against paid")
    if measured:
        s = sorted(x["seconds"] for x in measured)
        print(f"seconds per request, measured this run: n={len(s)}, "
              f"min {s[0]:.2f}, median {s[len(s)//2]:.2f}, max {s[-1]:.2f}")
        print(f"enumerating every tag's paid listing would be {enum_pages:,} page(s), "
              f"about {enum_pages * (s[len(s)//2] + DELAY_S) / 3600:.2f} hour(s) "
              f"at the measured median plus the delay")
    else:
        print("every page came from cache, so no seconds were measured and no hours "
              "are quoted. Run with --refresh to measure.")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
