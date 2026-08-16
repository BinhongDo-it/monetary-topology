"""Retrieve one vintage of the New York Fed Household Debt and Credit workbook.

Registered in ``docs/a1_availability.md`` 8 item 1. Stage A1 scores two of its
levels against one sheet of this workbook, and this is how the file arrives in
this repository rather than being read across a boundary from a sibling one.

Usage::

    python data/fetch_hhdc.py                     # the pinned vintage
    python data/fetch_hhdc.py --check             # classify the cache, fetch nothing
    python data/fetch_hhdc.py --vintage 2026Q2    # a different quarter, kept separately
    python data/fetch_hhdc.py --force             # refetch, retiring the current file

Endpoint, verified 2026-08-13::

    https://www.newyorkfed.org/medialibrary/interactives/householdcredit/
        data/xls/HHD_C_Report_2026Q1.xlsx

Free, no key, no registration. Older quarters resolve under the same pattern,
which is what makes a past vintage re-fetchable rather than merely archived.

Three properties of this fetcher, each answering a rule
--------------------------------------------------------
**One file per vintage.** ``CLAUDE.md`` item 6 treats retrieved data as
non-regenerable. The filename carries the quarter, so a later quarter can never
land on the file an earlier criterion was written against. The sibling
repository's fetcher writes every vintage to one name, which is how a 2026Q1
workbook ends up one URL bump away from replacement; that is a note for that
repository and this one does not copy the habit.

**Nothing is removed.** A cached file that fails validation, and the file being
replaced under ``--force``, are renamed with an ``.expired`` suffix and left in
place (``CLAUDE.md`` item 5). A partial download that fails validation is renamed
rather than unlinked for the same reason: it is evidence about what the server
returned.

**Validation happens before the file takes its name.** The download lands as a
``.partial``, is opened and checked by ``monetary_topology.hhdc.validate``, and
only then is moved into place. A truncated or restructured workbook therefore
never occupies the path that later code will read (``CLAUDE.md`` item 6, second
half: recognise a damaged file rather than read it in silently).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from monetary_topology.hhdc import (
    PINNED_VINTAGE,
    WorkbookProblem,
    validate,
    workbook_path,
    workbook_url,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "hhdc_manifest.json"

TIMEOUT_SECONDS = 180
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

#: A quarterly workbook of forty-odd sheets. Anything much smaller is an error
#: page that arrived with a 200, which this publisher does return.
MIN_BYTES = 200_000


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(url: str, timeout: int = TIMEOUT_SECONDS) -> bytes:
    """Fetch, retrying server errors and never retrying client errors."""
    req = urllib.request.Request(url, headers={"User-Agent": "monetary-topology"})
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            if attempt == RETRY_ATTEMPTS:
                raise ServerUnavailable(
                    f"HTTP {exc.code} after {RETRY_ATTEMPTS} attempts"
                ) from exc
            wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"      HTTP {exc.code}, retry {attempt} in {wait:.0f}s")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == RETRY_ATTEMPTS:
                raise
            wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"      {exc}, retry {attempt} in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def retire(path: Path, why: str) -> Path:
    """Rename, never remove."""
    spoiled = path.with_suffix(f"{path.suffix}.expired.{int(time.time())}")
    path.rename(spoiled)
    print(f"    {path.name}: {why} -> kept as {spoiled.name}")
    return spoiled


def check(vintage: str) -> int:
    """Classify what is cached and say so. Fetches nothing."""
    path = workbook_path(RAW, vintage)
    if not path.exists():
        print(f"  {path.name}: absent")
        return 1
    digest = sha256(path.read_bytes())
    try:
        summary = validate(path, vintage)
    except WorkbookProblem as exc:
        print(f"  {path.name}: BAD: {exc}")
        return 1
    recorded = None
    if MANIFEST.exists():
        entry = json.loads(MANIFEST.read_text(encoding="utf-8")).get(vintage, {})
        recorded = entry.get("sha256_stored")
    if recorded is None:
        verdict = "not in the manifest"
    elif digest == recorded:
        verdict = "matches the manifest"
    else:
        verdict = "DOES NOT MATCH THE MANIFEST"
    print(
        f"  {path.name}: stock {summary['stock_quarters']} quarters to "
        f"{summary['stock_last']} on sheet {summary['stock_sheet']}, "
        f"flow {summary['flow_quarters']} to {summary['flow_last']} on "
        f"{summary['flow_sheet']}, {summary['anchors_checked']} anchors checked"
    )
    print(f"  {path.name}: sha256 {digest[:12]}, {verdict}")
    return 1 if verdict.startswith("DOES NOT") else 0


def record(vintage: str, url: str, path: Path, raw: bytes,
           summary: dict[str, object]) -> None:
    """Merge this vintage into the manifest, never dropping another one."""
    existing: dict[str, object] = {}
    if MANIFEST.exists():
        existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing[vintage] = {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": "A1",
        "endpoint": url,
        "endpoint_verified": "2026-08-13",
        "file": path.name,
        "bytes": len(raw),
        "sha256_source": sha256(raw),
        "sha256_stored": sha256(path.read_bytes()),
        "summary": summary,
        "provenance": (
            "Federal Reserve Bank of New York, Quarterly Report on Household "
            "Debt and Credit, underlying data workbook. Source line on every "
            "sheet: New York Fed Consumer Credit Panel/Equifax. The panel "
            "itself is not public; access to the microdata is limited to "
            "Federal Reserve System researchers and their coauthors under a "
            "vendor contract, so this workbook is the public artifact and "
            "there is no second, independent source for the same figures. "
            "Two tables matter to stage A1 and they are different quantities: "
            "the share of outstanding balance ninety or more days delinquent, "
            "and the annualised share of balances newly entering that state. "
            "See docs/a1_availability.md sections 3 and 8."
        ),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(existing, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch, retiring the current file rather than "
                         "overwriting it")
    ap.add_argument("--vintage", default=PINNED_VINTAGE,
                    help=f"quarter to retrieve, default {PINNED_VINTAGE}")
    args = ap.parse_args()

    vintage = args.vintage.upper()
    if args.check:
        return check(vintage)

    out = workbook_path(RAW, vintage)
    url = workbook_url(vintage)
    print("NY Fed Household Debt and Credit, stage A1's two published levels")
    print(f"  vintage {vintage}, pinned vintage {PINNED_VINTAGE}")
    # Printed rather than only recorded: a 404 from this publisher says nothing
    # about which part of the address was wrong, and the quarter appears in the
    # path in two different letter cases across their own pages.
    print(f"  {url}\n")

    if out.exists() and not args.force:
        try:
            summary = validate(out, vintage)
        except WorkbookProblem as exc:
            retire(out, str(exc))
        else:
            print(
                f"    {out.name}: cached, stock {summary['stock_quarters']} "
                f"quarters to {summary['stock_last']}"
            )
            return 0

    try:
        raw = download(url)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"    {out.name}: FAILED {exc}", file=sys.stderr)
        return 1

    if len(raw) < MIN_BYTES:
        print(
            f"    {out.name}: FAILED {len(raw):,} bytes, below {MIN_BYTES:,}; "
            f"this publisher serves error pages with a 200",
            file=sys.stderr,
        )
        return 1

    RAW.mkdir(parents=True, exist_ok=True)
    partial = out.with_suffix(out.suffix + ".partial")
    partial.write_bytes(raw)
    try:
        summary = validate(partial, vintage)
    except Exception as exc:  # noqa: BLE001 - a bad zip raises here too
        retire(partial, f"downloaded but rejected: {exc}")
        print(f"    {out.name}: FAILED {exc}", file=sys.stderr)
        return 1

    if out.exists():
        retire(out, "replaced under --force")
    partial.rename(out)

    print(
        f"    {out.name}: {len(raw):,} bytes, stock "
        f"{summary['stock_quarters']} quarters to {summary['stock_last']} on "
        f"sheet {summary['stock_sheet']}, flow {summary['flow_quarters']} to "
        f"{summary['flow_last']} on sheet {summary['flow_sheet']}, "
        f"{summary['anchors_checked']} anchors checked"
    )

    record(vintage, url, out, raw, summary)
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
