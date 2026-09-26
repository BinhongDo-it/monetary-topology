"""B125: fetch the raw file, on the machine that runs the project.

One source, public: the General Services Administration's City Pair Program contract awards for
fiscal years 2026 and 2027, the CSVs linked from the program's page. GSA regenerates it after each business
day, so the manifest's SHA-256 and retrieval time are what fix the copy a reading was taken off.

The machinery (checks, temporary names, setting aside instead of deleting, the manifest) is
B123's fetcher, imported rather than copied, so a fault fixed there is fixed here.

    python experiments/b125_fetch.py --plan
    python experiments/b125_fetch.py --fetch
    python experiments/b125_fetch.py --verify
    python experiments/b125_fetch.py --import DEST PATH   # one file saved by hand
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b123_fetch as f  # noqa: E402

RAW = f.REPO / "data" / "raw" / "b125"
f.MANIFEST_NAME = "b125_manifest.json"
f.PLAN = (
    {"dest": "gsa/awards_2026.csv", "kind": "csv",
     "url": "https://www.gsa.gov/system/files/awards_2026.csv"},
    # Fiscal year 2027, in force 2026-10-01 to 2027-09-30. It carries one column the 2026 file
    # does not, _CN_FARE; the other 23 are the same.
    {"dest": "gsa/awards_2027.csv", "kind": "csv",
     "url": "https://www.gsa.gov/system/files/awards_2027.csv"},
    # Aena's tariff guide, Spanish edition of August 2026, the latest listed on the airlines'
    # prices page on 2026-09-23. Per-airport passenger and security charges: the two items
    # Real Decreto 1316/2001 art. 2.4 (as amended by RD 1340/2007, from 2007-11-01) leaves out
    # of the resident discount's base. The Satellite blob link serves a cookie page to a
    # script; this press-room path serves the PDF. Python's TLS check fails on this machine's
    # chain, so the copy is taken with curl.exe and entered with --import.
    {"dest": "aena/guia-tarifas-aena_2026-08.pdf", "kind": "pdf", "browser": True,
     "url": "https://www.aena.es/doc/detalleprensa/260801-guia-tarifas-aena-agosto-2026.pdf"},
)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--import", dest="imp", nargs=2, metavar=("DEST", "PATH"))
    a = ap.parse_args()
    if a.plan:
        return f.cmd_plan()
    if a.verify:
        return f.cmd_verify(RAW)
    if a.imp:
        return f.cmd_import(*a.imp, raw=RAW)
    return f.cmd_fetch(RAW)


if __name__ == "__main__":
    sys.exit(main())
