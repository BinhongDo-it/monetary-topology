"""B33 step zero: fetch the revenue service's basic table classified by size of
adjusted gross income and marital status.

This is the observed side of arm one. Arm one read a tax code against itself and
found two filing statuses sharing every printed number; whether they also pay the
same at the same income is a different question and it needs this table.

Runs on a machine with ordinary internet. The gateway in front of the sandboxes
denies this host by policy, on both sides, so this one is run locally.

    python experiments/b33_step0_fetch_soi.py
    python experiments/b33_step0_fetch_soi.py --years 2023

Downloads are treated as irreplaceable. The script resumes a partial file rather
than starting over, refuses to overwrite a complete one, and checks that what
landed is really a workbook instead of reading a truncated file in silence.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "b33"
UA = "Mozilla/5.0 (research; one table, once)"
URL = "https://www.irs.gov/pub/irs-soi/%sin12ms.xls"
YEARS = [2023, 2022, 2021]

# An .xls is an OLE2 compound file; an .xlsx is a zip. Anything else that lands
# under these names is an error page or a truncation, and must not be parsed.
MAGIC = {b"\xd0\xcf\x11\xe0": "xls (OLE2)", b"PK\x03\x04": "xlsx (zip)"}


def head(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        n = r.headers.get("Content-Length")
        return int(n) if n and n.isdigit() else None


def magic_of(path):
    with path.open("rb") as f:
        h = f.read(8)
    for m, name in MAGIC.items():
        if h.startswith(m):
            return name
    return None


def get(url, path, expect):
    """Resume if a partial file is there, otherwise fetch whole."""
    have = path.stat().st_size if path.exists() else 0
    if expect is not None and have == expect:
        return "already complete", have
    headers = {"User-Agent": UA}
    mode = "wb"
    if have and expect is not None and have < expect:
        headers["Range"] = "bytes=%d-" % have
        mode = "ab"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as r:
        if mode == "ab" and r.status != 206:
            mode, have = "wb", 0          # server ignored the range, start over
        with path.open(mode) as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
    return ("resumed" if mode == "ab" else "fetched"), path.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*", default=YEARS)
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)

    bad = 0
    for y in args.years:
        yy = "%02d" % (y % 100)
        url, path = URL % yy, DEST / ("%sin12ms.xls" % yy)
        try:
            expect = head(url)
        except Exception as e:
            print("%d  HEAD failed: %s %s" % (y, type(e).__name__, e))
            expect = None
        try:
            how, n = get(url, path, expect)
        except Exception as e:
            print("%d  FETCH FAILED: %s %s  (file left as is, nothing deleted)"
                  % (y, type(e).__name__, e))
            bad += 1
            continue

        kind = magic_of(path) if path.exists() and path.stat().st_size else None
        short = expect is not None and n < expect
        ok = kind is not None and not short
        print("%d  %-16s %9d bytes  expected %-9s  %-12s %s"
              % (y, how, n, "?" if expect is None else expect,
                 kind or "NOT A WORKBOOK", "ok" if ok else "*** SUSPECT ***"))
        if not ok:
            bad += 1
            print("      %s kept on disk under its own name. Nothing is deleted; "
                  "re-run to resume." % path.name)

    print("\ndestination: %s" % DEST)
    if bad:
        print("%d file(s) suspect. Do not parse them until this prints clean."
              % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
