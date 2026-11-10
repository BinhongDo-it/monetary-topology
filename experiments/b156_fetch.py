"""B156 fetch: FOMC press releases 2017 onward, one raw HTML file per release.

The date list is read off the Board's calendar pages, so it is not typed by hand.
Every page is written to data/raw/b156/fomc/monetaryYYYYMMDDa.htm. A file already on
disk is kept if it parses (it carries the closing </html> and an #article block);
anything else is fetched again. Rerunning is safe and fetches only what is missing.

The four Optimal Blue rate series and the two Treasury yields come from FRED, which
refuses non-browser requests from this machine, so they were saved through the browser
by hand (data/SOURCES.md, B156 entry). This script checks them and does not fetch them.

    python experiments/b156_fetch.py
"""

import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b156"
FOMC = RAW / "fomc"
BASE = "https://www.federalreserve.gov"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
CALENDARS = [
    "/monetarypolicy/fomccalendars.htm",
    "/monetarypolicy/fomchistorical2017.htm",
    "/monetarypolicy/fomchistorical2018.htm",
    "/monetarypolicy/fomchistorical2019.htm",
    "/monetarypolicy/fomchistorical2020.htm",
] + [f"/monetarypolicy/fomchistorical{y}.htm" for y in range(2009, 2017)]
FIRST = "20090101"  # the fixed-scenario index starts 2009-04-29; release bands are needed from there
FRED_FILES = {
    "OBMMIC30YF": 2017, "OBMMIVA30YF": 2017, "OBMMIFHA30YF": 2017,
    "OBMMIJUMBO30YF": 2017, "DGS2": 1976, "DGS10": 1962,
}


def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception as exc:  # retried, then raised
            if attempt == 3:
                raise
            print(f"  retry {path}: {exc}")
            time.sleep(3 * (attempt + 1))


def complete(text):
    return "</html>" in text.lower() and 'id="article"' in text


def release_dates():
    dates = set()
    for page in CALENDARS:
        found = re.findall(r"monetary/?(20\d{6})a\.htm", get(page))  # 2009 and 2010 link the older /press/monetary/ form
        print(f"{page}: {len(found)} links")
        dates.update(d for d in found if d >= FIRST)
    return sorted(dates)


def check_fred():
    bad = []
    for sid, first_year in FRED_FILES.items():
        p = RAW / f"b156_fred_{sid}.csv"
        if not p.exists():
            bad.append(f"{sid}: missing")
            continue
        lines = p.read_text(encoding="utf-8").strip().split("\n")
        ok = (lines[0] == f"observation_date,{sid}"
              and lines[1].startswith(str(first_year))
              and re.match(r"\d{4}-\d{2}-\d{2},", lines[-1]))
        print(f"{sid}: {len(lines) - 1} rows, {lines[1]} .. {lines[-1]}")
        if not ok:
            bad.append(f"{sid}: header or ends wrong")
    return bad


MND_URL = "https://www.mortgagenewsdaily.com/charts/embed/mtg-rates-mnd-full"
MND_FILE = RAW / "mnd" / "mtg-rates-mnd-full_20261016.html"
MND_VA_URL = "https://www.mortgagenewsdaily.com/charts/embed/mtg-rates-thirty-year-va-full"
MND_VA_FILE = RAW / "mnd" / "mtg-rates-thirty-year-va-full_20261017.html"


def fetch_mnd():
    """Mortgage News Daily rate index page. Its chart carries the full daily history of every
    product as JSON. One dated copy, never overwritten; a copy without the FHA series is refetched."""
    MND_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MND_FILE.exists() and '"MND 30 Yr. FHA"' in MND_FILE.read_text(encoding="utf-8"):
        print(f"MND: kept {MND_FILE.name}")
        return
    req = urllib.request.Request(MND_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = r.read().decode("utf-8")
    if '"MND 30 Yr. FHA"' not in text or "</html>" not in text.lower():
        sys.exit("MND: page arrived without the FHA series or incomplete, not written")
    MND_FILE.write_text(text, encoding="utf-8", newline="")
    print(f"MND: wrote {MND_FILE.name}, {len(text)} characters")


def fetch_mnd_va():
    """The VA line has its own chart page; the full-index page carries no VA history."""
    if MND_VA_FILE.exists() and '"MND 30 Yr. fixed VA"' in MND_VA_FILE.read_text(encoding="utf-8"):
        print(f"MND VA: kept {MND_VA_FILE.name}")
        return
    req = urllib.request.Request(MND_VA_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = r.read().decode("utf-8")
    if '"MND 30 Yr. fixed VA"' not in text or "</html>" not in text.lower():
        sys.exit("MND VA: page arrived without the VA series or incomplete, not written")
    MND_VA_FILE.write_text(text, encoding="utf-8", newline="")
    print(f"MND VA: wrote {MND_VA_FILE.name}, {len(text)} characters")


def main():
    fetch_mnd()
    fetch_mnd_va()
    FOMC.mkdir(parents=True, exist_ok=True)
    dates = release_dates()
    print(f"{len(dates)} releases from {dates[0]} to {dates[-1]}")
    fetched = kept = 0
    for d in dates:
        p = FOMC / f"monetary{d}a.htm"
        if p.exists() and complete(p.read_text(encoding="utf-8")):
            kept += 1
            continue
        text = get(f"/newsevents/pressreleases/monetary{d}a.htm")
        if not complete(text):
            sys.exit(f"{d}: page arrived incomplete, not written")
        p.write_text(text, encoding="utf-8", newline="\n")
        fetched += 1
        time.sleep(0.5)
    print(f"releases: {fetched} fetched, {kept} already on disk")
    bad = check_fred()
    if bad:
        sys.exit("FRED files: " + "; ".join(bad))


if __name__ == "__main__":
    main()
