"""B30-5 retrieval, item-major. One request returns every city for one item.

**Why the direction is reversed.** The station regresses, for each item, log
price on log income *across cities*. So `n` is the number of cities; items are
repeated readings, not degrees of freedom. City-major retrieval buys one city
per request and 55 items nobody asked for; item-major retrieval buys one item
per request and every city the source covers. On the ranking page that is over
five hundred cities worldwide and around a hundred and fifty in China, against
the thirty-one the city-major list registers. Twelve cities give a median
`se(b)` of 0.193; a hundred and forty give roughly 0.055.

**It also fits the budget.** The host answers 429 with a `Retry-After` set to a
date one month out, which is a quota resetting on a calendar. Eight or nine
items are enough to read the class contrast, and eight requests fit inside any
plausible monthly allowance.

**Currency does not enter.** Whatever currency the page serves, it multiplies
every city on that page by one constant, and a constant in logs moves only the
intercept. The known-answer check below is therefore written on *ratios*, which
carry no currency at all: each Chinese city's ranking value divided by the value
already in `panel.json` must be the same constant across cities. A parser that
reads the wrong column, or a page that switches currency or region, breaks that
constancy immediately.

**Nothing runs by default.** `--list` spends one request and enumerates the item
ids; `--items` fetches only the ids named. Pages are cached, so a re-run costs
nothing and a parser fix costs nothing.

Run:
    python data\\fetch_b30_5_items.py --list
    python data\\fetch_b30_5_items.py --items 101 --check-against-panel
    python data\\fetch_b30_5_items.py --items 100 101 105 ...
"""

import argparse
import json
import re
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape as _unescape
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "b30_5" / "rankings"
PANEL = ROOT / "data" / "b30_5" / "panel.json"
OUT = ROOT / "data" / "b30_5" / "item_panel.json"
MAIN = "https://www.numbeo.com/cost-of-living/city_price_rankings_main"
RANK = "https://www.numbeo.com/cost-of-living/city_price_rankings?itemId=%s"
UA = "monetary-topology research script"
PAUSE = 8.0

FT2_PER_M2 = 10.7639
# itemId 101 is price per square metre outside the centre. The panel carries the
# same quantity per square foot, so the two routes must agree up to one
# constant. These are the panel's own English city names as the ranking page
# prints them, "City, China".
CHECK_ITEM = "101"
CHECK_PANEL_KEY = ("Buy Apartment Price :: Price per Square Feet to Buy "
                   "Apartment Outside of Centre")


def get(url, key, force=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / ("%s.html" % re.sub(r"[^A-Za-z0-9_]+", "_", key))
    if p.exists() and not force:
        return p.read_text(encoding="utf-8", errors="replace"), True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        ra = e.headers.get("Retry-After") if e.headers else None
        if e.code in (500, 502, 503, 504):
            # A 5xx is the host having a moment, not a decision about this
            # client. The first version let it raise, and a --list that costs
            # one request died on a transient 503.
            raise SystemExit(
                "\nHTTP %s from the host, which is transient rather than a "
                "refusal. Nothing is cached and nothing is written; run the "
                "same command again." % e.code)
        if e.code == 429 and ra and not str(ra).strip().isdigit():
            raise SystemExit(
                "\nHTTP 429 and Retry-After is a date, %s. That is a quota "
                "resetting on a calendar, not a rate to back off from. "
                "Everything already cached is untouched and a later run "
                "resumes from it." % ra)
        raise
    p.write_text(html, encoding="utf-8")
    return html, False


def cells(fragment):
    t = re.sub(r"<[^>]+>", "\t", fragment)
    return [" ".join(_unescape(c).split()) for c in t.split("\t")]


def parse_rank(html):
    """Rows of (city string, value). Prints nothing, decides nothing."""
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cs = [c for c in cells(row) if c]
        if len(cs) < 2:
            continue
        # the first cell is a rank like "1." and the city carries a comma
        if not re.fullmatch(r"\d+\.?", cs[0]):
            continue
        city = next((c for c in cs[1:] if "," in c), None)
        if city is None:
            continue
        num = None
        for c in reversed(cs):
            m = re.fullmatch(r"[^\d]*([\d,]+(?:\.\d+)?)[^\d]*", c)
            if m:
                try:
                    num = float(m.group(1).replace(",", ""))
                except ValueError:
                    num = None
                if num is not None:
                    break
        if num is not None:
            out.append((city, num))
    return out


def check_against_panel(rows):
    """Currency-free: the ratio to the panel must be one constant."""
    if not PANEL.exists():
        print("  no panel on disk, the ratio check is skipped.")
        return True
    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    byname = {c.split(",")[0].strip(): v for c, v in rows}
    ratios = []
    for city, d in sorted(panel.items()):
        p = d["items"].get(CHECK_PANEL_KEY)
        r = byname.get(city)
        if p and r:
            ratios.append((city, r / (p * FT2_PER_M2)))
    if len(ratios) < 4:
        print("  only %d cities overlap the panel, too few to check. Nothing "
              "is written." % len(ratios))
        return False
    vals = [v for _, v in ratios]
    spread = max(vals) / min(vals)
    print("  ratio of the ranking value to the panel value, which must be one "
          "constant whatever currency the page serves:")
    for c, v in sorted(ratios, key=lambda x: -x[1]):
        print("    %-14s %10.4f" % (c, v))
    print("  %d cities, spread max/min = %.4f, mean %.4f, sd %.4f"
          % (len(vals), spread, st.mean(vals), st.pstdev(vals)))
    if spread > 1.02:
        print("\n  Those are not one constant. Either the column read is the "
              "wrong one, or the page served a different region or currency "
              "than the cached panel did. Nothing is written.")
        return False
    print("  One constant to within 2%. The two retrieval routes agree.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--items", nargs="*", default=[])
    ap.add_argument("--check-against-panel", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.list:
        html, cached = get(MAIN, "items_main", a.force)
        seen = {}
        for m in re.finditer(r'itemId=(\d+)[^>]*>(.*?)</a>', html, re.S):
            name = " ".join(_unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
            if name:
                seen.setdefault(m.group(1), name)
        print("%d item ids enumerated%s" % (len(seen), " [cache]" if cached else ""))
        for k in sorted(seen, key=lambda x: int(x)):
            print("  %-6s %s" % (k, seen[k]))
        if not seen:
            print("  none found. The page is cached at %s; fix the parser "
                  "against it rather than refetching." % CACHE)
        return

    if not a.items:
        raise SystemExit(
            "nothing requested, so nothing is fetched. Use --list once to "
            "enumerate the ids, then --items with the ids you want. Each id "
            "costs one request and returns every city the source covers.")

    panel = {}
    if OUT.exists():
        panel = json.loads(OUT.read_text(encoding="utf-8"))
    for item in a.items:
        html, cached = get(RANK % item, "item_%s" % item, a.force)
        rows = parse_rank(html)
        cn = [(c, v) for c, v in rows if c.endswith(", China")]
        print("item %-6s rows %-5d  China %-4d %s"
              % (item, len(rows), len(cn), "[cache]" if cached else ""))
        if not rows:
            raise SystemExit(
                "\nitem %s: the page is on disk at %s and the parser found no "
                "rows. That is a parser fault, not a missing item, and it must "
                "not be recorded as one. Nothing written." % (item, CACHE))
        if item == CHECK_ITEM or a.check_against_panel:
            if not check_against_panel(rows):
                raise SystemExit("\nthe cross-route check did not pass. "
                                 "Nothing written.")
        panel[item] = {"n_rows": len(rows),
                       "cities": {c: v for c, v in rows}}
        if not cached:
            time.sleep(PAUSE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(panel, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("\n%d items in %s" % (len(panel), OUT))


if __name__ == "__main__":
    main()
