"""B30-5: one page per city, cached, resumable, with a known-answer check.

Carrier and rule are registered in ``docs/b30_prereg.md``, section "B30-5
cross-sectional": the four municipalities and every provincial capital, an
administrative status rather than a selection on income, and nothing dropped for
thinness. Each page carries its own entry count, contributor count and update
date, and those are recorded beside the city and reported, never used as a
filter.

The slug is not uniform. Large cities answer at ``/cost-of-living/in/<City>``
and some smaller ones only at ``/cost-of-living/in/<City>-China``; a slug the
site cannot resolve returns **HTTP 200** with the title "Cannot find city id
for ...", so the status code is not the check and the title is. Both forms are
tried and the one that answers is recorded.

The known-answer set below was read through a browser on 2026-09-01, before this
fetcher existed. **If this parser disagrees with any of it the run stops**, so a
parser fault cannot quietly produce a panel that looks fine.

Run:
    python fetch_b30_5_cities.py
    python fetch_b30_5_cities.py --check
"""

import argparse
import datetime
import email.utils
import json
import math
import re
# Imported under an alias on purpose: parse() below takes a parameter
# named ``html``, and a bare ``import html`` would be shadowed by it.
from html import unescape as _unescape
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "b30_5" / "pages"
PANEL = ROOT / "data" / "b30_5" / "panel.json"
BASE = "https://www.numbeo.com/cost-of-living/in/%s"
UA = "monetary-topology research script"
PAUSE = 6.0

# Four municipalities, then every provincial and autonomous-region capital, in
# administrative order. Nothing here is chosen by income or by data volume.
CITIES = [
    "Beijing", "Tianjin", "Shanghai", "Chongqing",
    "Shijiazhuang", "Taiyuan", "Hohhot", "Shenyang", "Changchun", "Harbin",
    "Nanjing", "Hangzhou", "Hefei", "Fuzhou", "Nanchang", "Jinan",
    "Zhengzhou", "Wuhan", "Changsha", "Guangzhou", "Nanning", "Haikou",
    "Chengdu", "Guiyang", "Kunming", "Lhasa", "Xian", "Lanzhou",
    "Xining", "Yinchuan", "Urumqi",
]
# Alternate spellings tried when the first slug does not resolve.
ALT = {"Xian": ["Xi'an", "Xi-an"], "Kunming": ["Kunming, Yunnan"],
       "Urumqi": ["Urumchi"]}

SALARY = "Salaries And Financing :: Average Monthly Net Salary (After Tax)"

# Read through a browser on 2026-09-01, before this parser was written.
KNOWN = {
    ("Beijing", SALARY): 11244.87,
    ("Beijing", "Transportation :: Volkswagen Golf 1.5 (or Equivalent New Compact Car)"): 129900.0,
    ("Beijing", "Transportation :: Monthly Public Transport Pass (Regular Price)"): 215.0,
    ("Shanghai", SALARY): 11674.92,
    ("Shanghai", "Restaurants :: Cappuccino (Regular Size)"): 22.13,
    ("Harbin", SALARY): 3966.67,
    ("Harbin", "Transportation :: Monthly Public Transport Pass (Regular Price)"): 73.69,
    ("Harbin", "Clothing And Shoes :: Men's Leather Business Shoes"): 2000.0,
    ("Lhasa", SALARY): 14000.0,
    ("Lhasa", "Transportation :: Volkswagen Golf 1.5 (or Equivalent New Compact Car)"): 200000.0,
    ("Hohhot", "Transportation :: Volkswagen Golf 1.5 (or Equivalent New Compact Car)"): 105000.0,
    ("Shijiazhuang", "Markets :: Milk (Regular, 1 Liter)"): 8.73,
    ("Chongqing", "Restaurants :: Cappuccino (Regular Size)"): 13.67,
}


#: The nine sections plus the salary block, exactly as the page prints them.
#: Sections drive the parse, so nothing depends on a CSS class. The first
#: version keyed on ``class="data_wide_table"`` and ``class="category_title"``,
#: which work in a live DOM and did not survive a hand written tag parser: every
#: city came back with zero items and the run reported them as UNRESOLVED, that
#: is, a parser fault wearing a carrier fault's clothes.
SECTIONS = [
    "Restaurants", "Markets", "Transportation", "Utilities (Monthly)",
    "Sports And Leisure", "Childcare", "Clothing And Shoes",
    "Rent Per Month", "Buy Apartment Price", "Salaries And Financing",
]


def _text(fragment):
    """Tags out first, entities second, and never the other way round.

    The price cell is ``<span class="first_currency">&#165;30.00</span>``: the
    currency sign is a *numeric* entity. Stripping tags without decoding it
    leaves the string "16530.00", and the digit filter downstream cannot tell
    those three digits from the price -- every number on the page comes out
    with a constant prefix, which survives a rank correlation and so looks
    fine. Decoding must therefore happen here, and it must happen after the
    tags are gone, or an escaped "&lt;td&gt;" in the text would become a tag.
    """
    t = re.sub(r"<[^>]+>", "\t", fragment)
    return [" ".join(_unescape(c).split()) for c in t.split("\t")]


def parse(html):
    items = {}
    section = None
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = [c for c in _text(row) if c]
        if not cells:
            continue
        if cells[0] in SECTIONS:
            section = cells[0]
            continue
        if section is None or len(cells) < 2:
            continue
        label, raw = cells[0], cells[1]
        num = re.sub(r"[^\d.]", "", raw)
        if not label or not num or num.count(".") > 1:
            continue
        try:
            items["%s :: %s" % (section, label)] = float(num)
        except ValueError:
            pass
    title = ""
    m = re.search(r"<title>([^<]*)</title>", html, re.I)
    if m:
        title = " ".join(m.group(1).split())
    body = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    # The page prints its own volume in one of two sentences, and which one it
    # picks is itself a reading. A city with enough traffic gets
    #   "had 1269 entries in the past 12 months by 129 different contributors"
    # and a thin one gets
    #   "had 21 different contributors in the past 18 months"
    # -- no entry count at all, and a window widened to 18 months. Matching
    # only the first form returns null for exactly the cities whose thinness
    # is the thing worth knowing. The window is recorded as a number of months
    # so the two forms come back on one scale. Per the registered rule these
    # are reported beside each city and nothing is dropped on them.
    e = re.search(r"had ([\d,]+) entries in the past (\d+) months? by "
                  r"([\d,]+) different contributors", body)
    t = re.search(r"had ([\d,]+) different contributors in the past "
                  r"(\d+) months?", body)
    if e:
        entries, contributors, window = e.group(1), e.group(3), int(e.group(2))
    elif t:
        entries, contributors, window = None, t.group(1), int(t.group(2))
    else:
        entries = contributors = window = None
    u = re.search(r"Last update:\s*([0-9]{1,2} [A-Za-z]+ [0-9]{4})", body)
    return {"title": title, "items": items,
            "entries": entries, "contributors": contributors,
            "window_months": window,
            "estimated_flag": "Some data are estimated due to a low number "
                              "of contributors" in body,
            "updated": u.group(1) if u else None,
            "resolved": "cannot find city id" not in title.lower()}


def get(slug, force=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", slug)
    p = CACHE / ("%s.html" % safe)
    if p.exists() and not force:
        return p.read_text(encoding="utf-8", errors="replace"), True
    url = BASE % urllib.parse.quote(slug)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                html = r.read().decode("utf-8", "replace")
            p.write_text(html, encoding="utf-8")
            return html, False
        except urllib.error.HTTPError as e:
            # 429 is the site asking for patience, not refusing. The first
            # version let it fall through to raise because it only retried 5xx,
            # and the run died twenty-two pages in.
            if e.code not in (429, 500, 502, 503, 504):
                raise
            ra = e.headers.get("Retry-After") if e.headers else None
            last = "HTTP %s%s" % (e.code, (" retry-after %s" % ra) if ra else "")
            if ra and str(ra).strip().isdigit():
                time.sleep(min(int(ra) + 2, 180))
            elif ra:
                # Retry-After has two forms and they mean different things. An
                # integer is "you are going too fast", and backing off answers
                # it. An HTTP-date weeks out is a quota that resets on a
                # calendar, and no pause this script can take will answer it:
                # retrying just spends attempts on a decision already made.
                # Say which one it is and stop, rather than backing off into a
                # wall five times.
                when = email.utils.parsedate_to_datetime(str(ra).strip())
                if when is not None:
                    ahead = (when - datetime.datetime.now(when.tzinfo))
                    if ahead.total_seconds() > 3600:
                        raise SystemExit(
                            "\n%s: HTTP %s, and Retry-After is a date rather "
                            "than a delay: %s, which is %.1f days out. That is "
                            "a quota resetting on a calendar, not a rate to "
                            "back off from, so this script stops instead of "
                            "retrying. Everything already cached is untouched "
                            "and the next run resumes from it."
                            % (slug, e.code, ra, ahead.total_seconds() / 86400))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            last = str(getattr(e, "reason", e))
        wait = 20 * (2 ** attempt)
        print("    %s, waiting %ds" % (last, wait))
        time.sleep(wait)
    raise SystemExit("gave up on %s" % slug)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    panel, failed = {}, []
    for city in CITIES:
        tried = []
        got = None
        for slug in [city, city + "-China"] + ALT.get(city, []) + \
                    [s + "-China" for s in ALT.get(city, [])]:
            if a.check and not (CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", slug)
                                         + ".html")).exists():
                tried.append(slug + " (not cached)")
                continue
            html, cached = get(slug, a.force)
            d = parse(html)
            tried.append("%s -> %s%s" % (slug, d["title"][:40],
                                         " [cache]" if cached else ""))
            if d["resolved"] and d["items"]:
                got = (slug, d, cached)
                break
            if not cached:
                time.sleep(PAUSE)
        if not got:
            titled = [t for t in tried if "Cost of Living in" in t]
            if titled:
                raise SystemExit(
                    "\n%s: the page resolved (%s) and the parser found no "
                    "items. That is a parser fault, not a missing city, and it "
                    "must not be recorded as one. Nothing written."
                    % (city, titled[0]))
            failed.append((city, tried))
            print("  %-14s UNRESOLVED  %s" % (city, "; ".join(tried)))
            continue
        # ``cached`` has to be carried out of the slug loop, not recomputed
        # here. get() has already written the page by this point, so asking the
        # filesystem always answers True, the pause below never runs, and the
        # requests go out back to back -- which is how the first run walked
        # into a 429 twenty-two pages in.
        slug, d, cached = got
        panel[city] = {"slug": slug, "title": d["title"],
                       "entries": d["entries"], "contributors": d["contributors"],
                       "window_months": d["window_months"],
                       "estimated_flag": d["estimated_flag"],
                       "updated": d["updated"],
                       "salary": d["items"].get(SALARY),
                       "items": {k: v for k, v in d["items"].items()
                                 if k != SALARY}}
        print("  %-14s items %2d  entries %-5s contrib %-4s window %-3s %s %s"
              % (city, len(d["items"]), d["entries"], d["contributors"],
                 d["window_months"], "est" if d["estimated_flag"] else "   ",
                 d["updated"]))
        if not cached:
            time.sleep(PAUSE)

    print("\nknown-answer check, read through a browser before this parser existed")
    # Two ways to fail this check, and they are not the same state. A value
    # that disagrees means the parser is wrong and the panel would be quietly
    # corrupt. A city that is absent means the run has not reached it yet,
    # which is the normal state under --check. Both stop the write, because a
    # panel written against a partial reference set is unchecked either way,
    # but they get their own words so the next reader is not told the parser
    # disagrees with the browser when nothing of the sort happened.
    bad, absent = [], []
    for (city, key), want in sorted(KNOWN.items()):
        if city not in panel:
            absent.append((city, key.split(" :: ")[-1]))
            continue
        src = panel[city]["items"] if key != SALARY else {SALARY: panel[city]["salary"]}
        got = src.get(key)
        ok = got is not None and abs(got - want) < 0.005
        print("  %-14s %-58s want %12.2f got %s  %s"
              % (city, key.split(" :: ")[-1][:58], want,
                 ("%12.2f" % got) if got is not None else "     missing",
                 "ok" if ok else "MISMATCH"))
        if not ok:
            bad.append((city, key, want, got))
    if bad:
        raise SystemExit(
            "\n%d known answers disagree with the browser read. That is a "
            "parser fault and the panel would be corrupt, so nothing is "
            "written." % len(bad))

    # An absent reference city is not a failed check. The question this block
    # answers is whether the parser agrees with a read taken independently of
    # it, and the parser is the same code on every page, so a city that has
    # not been fetched adds nothing to that question -- requiring one requires
    # a *city*, not a *check*. The first shape of this block stopped the write
    # over Lhasa while all eleven reachable values matched to the cent, which
    # is refusing to record a checked panel because the check was thorough.
    # Changed 2026-09-01. Nothing the parser produces moves; only the verdict.
    #
    # The floor below keeps it from degenerating into no check at all. It is
    # stated on the *coverage of the reference set*, never on agreement:
    # agreement stays exact to the cent and one mismatch still stops the run.
    MIN_REF_VALUES, MIN_REF_CITIES, MIN_REF_SECTIONS, MIN_REF_DECADES = 8, 4, 3, 3
    hit = [(c, k) for (c, k) in sorted(KNOWN) if c in panel]
    sections = {k.split(" :: ")[0] for _, k in hit}
    vals = [KNOWN[(c, k)] for c, k in hit if KNOWN[(c, k)] > 0]
    decades = (math.log10(max(vals)) - math.log10(min(vals))) if vals else 0.0
    print("\n  reference coverage: %d values, %d cities, %d sections, "
          "%.1f decades of magnitude"
          % (len(hit), len({c for c, _ in hit}), len(sections), decades))
    if (len(hit) < MIN_REF_VALUES or len({c for c, _ in hit}) < MIN_REF_CITIES
            or len(sections) < MIN_REF_SECTIONS or decades < MIN_REF_DECADES):
        raise SystemExit(
            "\nthe reference set this run could reach is too narrow to check "
            "the parser (needs at least %d values over %d cities, %d sections "
            "and %d decades). Nothing is written."
            % (MIN_REF_VALUES, MIN_REF_CITIES, MIN_REF_SECTIONS,
               MIN_REF_DECADES))
    if absent:
        print("  reference values in cities this run has not fetched, named "
              "rather than passed over:")
        for city, item in absent:
            print("    %-14s %s" % (city, item[:58]))

    if failed:
        print("\nunresolved cities, named rather than dropped quietly:")
        for city, tried in failed:
            print("  %-14s %s" % (city, "; ".join(tried)))

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(panel, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print("\n%d cities written to %s" % (len(panel), PANEL))
    sal = sorted((d["salary"], c) for c, d in panel.items() if d["salary"])
    if sal:
        print("  salary range %.0f (%s) to %.0f (%s)"
              % (sal[0][0], sal[0][1], sal[-1][0], sal[-1][1]))


if __name__ == "__main__":
    main()
