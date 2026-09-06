"""Enumerate every SEC self-regulatory organisation notice in the Federal Register.

WHY THIS EXISTS. One arm asks whether a procedure travels with a change of control.
A filed rating plan does not, and the reason is structural: it is observable because
it is lodged with a regulator per entity, and being lodged per entity is what stops
it moving. The channel that does not have that problem is one where keeping the
incumbent procedure is not an option, and an exchange fee schedule is that: it is
published, it is tiered, every amendment to it is filed under Rule 19b-4 and printed
in the Federal Register with a date, and when an exchange stops operating its fee
schedule stops being filed and its members are priced by another one.

WHAT IS COLLECTED. Every Federal Register notice issued by the SEC, title and date
only, across the requested years. The self-regulatory notices carry a title of a very
regular shape:

    Self-Regulatory Organizations; <exchange>; Notice of Filing and Immediate
    Effectiveness of a Proposed Rule Change To Amend Its Fee Schedule

so the exchange name and whether the filing touches fees are both readable off the
title without retrieving a single document. Nothing is downloaded beyond the index.

WHY THE INDEX RATHER THAN A FILTERED QUERY. Titles vary: "Fee Schedule", "Fees
Schedule", "Price List", "Transaction Fees". Filtering server-side on one of those
loses the others and the loss is silent. The whole index is small, it is fetched
once, and every later screen runs on disk.

RESUME AND INTEGRITY. One file per month under data/raw/fr_sec/. A month already on
disk with a matching stored count is skipped. A month whose stored count disagrees
with the row count is refetched rather than read, so a truncated file cannot be used
by accident. Delete nothing to refetch: rename the month's file and it is refetched.

    python data/fetch_sro_filings.py            # 2005 to the current year
    python data/fetch_sro_filings.py 2014 2019  # a range
"""
import calendar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.federalregister.gov/api/v1/documents.json"
FIELDS = ["document_number", "publication_date", "title", "html_url"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", "fr_sec")
PER_PAGE = 1000
PAUSE = 0.4


def month_url(year, month, page):
    last = calendar.monthrange(year, month)[1]
    q = [
        ("conditions[agencies][]", "securities-and-exchange-commission"),
        ("conditions[publication_date][gte]", f"{year:04d}-{month:02d}-01"),
        ("conditions[publication_date][lte]", f"{year:04d}-{month:02d}-{last:02d}"),
        ("per_page", str(PER_PAGE)),
        ("page", str(page)),
        ("order", "oldest"),
    ]
    q += [("fields[]", f) for f in FIELDS]
    return API + "?" + urllib.parse.urlencode(q)


def get(url, tries=4):
    """One request, with a bounded retry. A failure raises rather than returning {}."""
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "tariff-structure-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)
    raise RuntimeError("unreachable")


def stored(path):
    """Rows and the count the server reported when they were written, or None.

    A file whose header count disagrees with its row count is reported as None so
    the month is refetched. A truncated write is therefore never read as complete.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            lines = [l for l in f.read().split("\n") if l.strip()]
        if not lines:
            return None
        head = json.loads(lines[0])
        rows = [json.loads(l) for l in lines[1:]]
    except (ValueError, OSError):
        return None
    if head.get("_count") != len(rows):
        return None
    return rows


def fetch_month(year, month):
    path = os.path.join(OUT, f"{year:04d}-{month:02d}.jsonl")
    have = stored(path)
    if have is not None:
        return len(have), True

    first = get(month_url(year, month, 1))
    count = first.get("count") or 0
    rows = list(first.get("results") or [])
    pages = first.get("total_pages") or 1
    for p in range(2, pages + 1):
        time.sleep(PAUSE)
        rows += list(get(month_url(year, month, p)).get("results") or [])

    if count and len(rows) != count:
        raise RuntimeError(
            f"{year}-{month:02d}: server said {count}, {len(rows)} came back. "
            "Not written. Rerun; if it repeats the month exceeds the API's "
            "pagination depth and has to be split by day.")

    tmp = path + ".partial"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"_count": len(rows), "_year": year, "_month": month},
                           sort_keys=True) + "\n")
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)          # the file appears complete or not at all
    return len(rows), False


def main(y0, y1):
    os.makedirs(OUT, exist_ok=True)
    total = read = 0
    for year in range(y0, y1 + 1):
        got = hit = 0
        for month in range(1, 13):
            n, cached = fetch_month(year, month)
            got += n
            hit += 1 if cached else 0
            if not cached:
                time.sleep(PAUSE)
        total += got
        read += hit
        print(f"{year}  {got:6d} notices   {hit:2d}/12 months already on disk",
              flush=True)
    print(f"\n{total} SEC notices across {y1 - y0 + 1} years, "
          f"{read} of {(y1 - y0 + 1) * 12} months read from disk")
    print(f"written under {os.path.relpath(OUT, os.path.dirname(OUT))}/")


if __name__ == "__main__":
    import datetime
    a = sys.argv[1:]
    lo = int(a[0]) if a else 2005
    hi = int(a[1]) if len(a) > 1 else datetime.date.today().year
    main(lo, hi)
