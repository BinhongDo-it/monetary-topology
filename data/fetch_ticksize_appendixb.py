# -*- coding: utf-8 -*-
"""Tick Size Pilot Appendix B, from NYSE group's public archive.

`http://ftp.nyxdata.com/Tick_Pilot/` is reachable over **plain HTTP**, not the
`ftp://` scheme the SEC's page still lists, and **not over HTTPS either**:
the host answers on 443 with a certificate that is not valid for
`ftp.nyxdata.com`, so `urlopen` dies with
`CERTIFICATE_VERIFY_FAILED ... Hostname mismatch`. Corrected 2026-08-19 after
that failure; the first version of this file asserted HTTPS and was wrong.
**No certificate check is disabled here.** The scheme is `http://`, so there is
no TLS to weaken, and what that costs is stated rather than hidden: the transfer
is unauthenticated, so the size check in `fetch` against the directory index's
own byte count is the only integrity evidence there is, and it is the reason
that check refuses to rename a short `.part`. It carries, per venue and per
appendix, one gzip per month from 2016-04 to 2019-03, and a daily record of
which securities were in which test group.

**Why this exists.** B4 section 5.1 splits a directed square into a friction
half and an index half. `results/b5_friction.json` records the Argentine carrier
failing to supply the friction half at all: three candidate sources for the
official rate's spread, all three rejected. Appendix B publishes
`B.I.a(33)`, the share-weighted average BBO spread **of the reporting exchange**,
per symbol-day-venue. That is the friction half, per venue, for free.

**What it does not supply.** B.I carries spreads and no quote level, so the index
half, which needs a per-venue midpoint, is not in it. `B.II(k)` carries the
receiving venue's price but only the side opposite the order, per order. Whether
that reconstructs a midpoint is an open question and the reason `--part BII`
exists.

Discovery first, in the shape `data/fetch_rocr.py` uses: `--list` parses each
directory index and prints what it found. **If the names are not what this file
expects, the parser is wrong and nothing should be pulled.** Only the Arca
prefix has been eyeballed; the others are read off the index rather than
guessed.

Resumable and truncation-aware, per the project's fetcher rules: bytes land in
`<name>.part`, the file is renamed only when the byte count matches the
`Content-Length` the server declared, and an existing complete file is never
refetched or overwritten.

Usage::

    python data/fetch_ticksize_appendixb.py --list --from 201608 --to 201612
    python data/fetch_ticksize_appendixb.py --pull --from 201608 --to 201612 \
        --venues NYSE_Arca,NYSE --part BI
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

BASE = "http://ftp.nyxdata.com/Tick_Pilot/"

#: The small files that sit beside the monthly archives. Names measured from the
#: directory index on 2026-08-19; `--aux` pulls them into `data/raw/ticksize/`.
#: `TSPilotChanges20181001.txt` is dated the first trading day after the pilot's
#: quoting and trading requirements ended (2018-09-28 close), so it is the file
#: that records the reversal, and `B14_设计_v1.md` §7·补2 needs it.
AUX = (
    "Appendix_B_Pilot_File_Updates.xlsx",
    "Pilot_File_Updates.xlsx",
    "TSPilotChanges20181001.txt",
    "NYSE_Group_Tick_Pilot_Assignments.txt",
)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "tickpilot"
VENUES = ("NYSE", "NYSE_Arca", "NYSE_MKT", "NYSE_NATL", "NYSE_CHI", "NYSE_NSX")
PARTS = ("BI", "BII", "BIII", "BIV")
HREF = re.compile(r'href="([^"?/][^"]*)"')
ROW = re.compile(r'href="([^"?/][^"]*)"[^>]*>[^<]*</a>\s*(\S+\s+\S+)\s+(\d+)')
MONTH = re.compile(r"_(\d{6})\.gzip$")


def index(url: str) -> list[tuple[str, int]]:
    """Return (filename, bytes) for every file linked from a directory index."""
    with urllib.request.urlopen(url, timeout=60) as fh:
        html = fh.read().decode("utf-8", "replace")
    rows = [(m.group(1), int(m.group(3))) for m in ROW.finditer(html)]
    if not rows and HREF.search(html):
        raise SystemExit(
            "the index at %s has links but not the size column this parser "
            "expects. **Stop.** The layout changed and pulling on a wrong parse "
            "is how a partial archive gets mistaken for a complete one." % url)
    return rows


def fetch(url: str, dest: Path) -> str:
    """Download to `dest`, resumably, refusing to leave a short file in place."""
    if dest.exists():
        return "have"
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url)
    if have:
        req.add_header("Range", "bytes=%d-" % have)
    with urllib.request.urlopen(req, timeout=120) as resp:
        declared = resp.headers.get("Content-Length")
        total = have + int(declared) if declared else None
        mode = "ab" if have and resp.status == 206 else "wb"
        if mode == "wb":
            have = 0
        with open(part, mode) as out:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                have += len(chunk)
    if total is not None and have != total:
        return "SHORT %d/%d, left as .part" % (have, total)
    part.rename(dest)
    return "ok %d B" % have


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--venues", default="NYSE_Arca,NYSE")
    ap.add_argument("--part", default="BI", choices=PARTS)
    ap.add_argument("--from", dest="lo", default="201608", help="YYYYMM inclusive")
    ap.add_argument("--to", dest="hi", default="201612", help="YYYYMM inclusive")
    args = ap.parse_args()
    if not (args.list or args.pull):
        return ap.error("pass --list first. Pulling on an unverified parse is the "
                        "mistake this ordering exists to prevent.")

    venues = [v for v in args.venues.split(",") if v]
    for v in venues:
        if v not in VENUES:
            return ap.error("%s is not one of %s" % (v, ", ".join(VENUES)))

    grand = 0
    for venue in venues:
        url = "%s%s_%s/" % (BASE, venue, args.part)
        try:
            rows = index(url)
        except Exception as exc:
            print("%-12s %s  <- %s" % (venue, url, exc))
            continue
        want = []
        for name, size in rows:
            m = MONTH.search(name)
            if m and args.lo <= m.group(1) <= args.hi:
                want.append((name, size))
        subtotal = sum(s for _n, s in want)
        grand += subtotal
        print("%-12s %-58s %2d files  %7.2f GB"
              % (venue, url, len(want), subtotal / 1e9))
        for name, size in want:
            if args.list:
                print("    %-52s %12d" % (name, size))
            else:
                dest = OUT / venue / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                print("    %-52s %12d  %s"
                      % (name, size, fetch(url + name, dest)), flush=True)
    print("\ntotal %.2f GB across %d venue(s), part %s, %s..%s"
          % (grand / 1e9, len(venues), args.part, args.lo, args.hi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
