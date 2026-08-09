#!/usr/bin/env python3
"""Retrieve the FHFA NMDB aggregate series for B2 loop B. Run locally; needs network.

Pre-registered in ``docs/b2_loop_b.md``. Every filter below is fixed there and none
may be changed after results are seen.

Usage::

    python data/fetch_nmdb.py               # the pre-registered sample
    python data/fetch_nmdb.py --dry-run     # print the URLs and exit
    python data/fetch_nmdb.py --stamp-legacy

Writes one slim CSV per source file into ``data/raw/nmdb/`` plus a manifest. Files
already complete are skipped, so the script is resumable. Nothing is ever deleted:
a file that fails its integrity check is renamed aside with an ``.expired`` suffix
and the loader ignores it because the name no longer matches the convention.

The published files are small, tens of megabytes zipped, so this is minutes rather
than the hours the HMDA retrieval takes.

Why the rows are filtered here rather than at analysis time: the sample has to be
fixed before any result is visible, and a scripted retrieval whose exclusions are
in version control is the only way a reader can check that it was.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nmdb"
MANIFEST = ROOT / "data" / "raw" / "nmdb_manifest.json"

BASE = "https://www.fhfa.gov/document/d/nmdb"

# ---------------------------------------------------------------------------
# The pre-registered sample. Do not edit after retrieval begins.
# ---------------------------------------------------------------------------

#: Source files, as (local name, remote file, series set).
#:
#: Outstanding statistics carry the rate distribution of the *stock*, which is the
#: whole point of loop B: it is the only public series that says what rate the
#: existing holders are actually paying. New-origination statistics supply the
#: market rate, used for the unregistered wedge and for L2's bookkeeping.
#:
#: State-level outstanding statistics are a separate file from the national one,
#: not a subset of it, so both are retrieved.
SOURCES = (
    (
        "outstanding_national",
        "nmdb-outstanding-mortgage-statistics-national-census-areas-quarterly.zip",
    ),
    ("outstanding_states", "nmdb-outstanding-mortgage-statistics-states-quarterly.zip"),
    (
        "new_national",
        "nmdb-new-mortgage-statistics-national-census-areas-quarterly.zip",
    ),
)

#: The five contract-rate buckets, in order, with their numeric edges.
#:
#: The top bucket is open above. ``upper = None`` is carried through to the bound
#: computation, where it means the bucket contributes its lower edge and nothing
#: more, which can only make the bound smaller.
RATE_BUCKETS: tuple[tuple[str, float, float | None], ...] = (
    ("PCT_INTRATE_LT_3", 0.0, 3.0),
    ("PCT_INTRATE_3_4", 3.0, 4.0),
    ("PCT_INTRATE_4_5", 4.0, 5.0),
    ("PCT_INTRATE_5_6", 5.0, 6.0),
    ("PCT_INTRATE_GE_6", 6.0, None),
)

#: Series kept. Anything not here is dropped at retrieval, which is what keeps the
#: files small enough to commit a manifest for and read in one pass.
KEEP_SERIES = frozenset(
    [name for name, _, _ in RATE_BUCKETS] + ["AVE_INTRATE", "TOT_LOANS"]
)

#: Markets kept: the headline and the like-for-like comparison with loop A, which
#: sampled conventional first-lien purchase originations.
KEEP_MARKETS = frozenset(["All Mortgages", "Conventional Market"])

#: Geography levels kept. Census regions and divisions are dropped: they are
#: neither the national figure nor a jurisdiction, so they would only invite a
#: post-hoc choice of which aggregation to quote.
KEEP_GEOLEVELS = frozenset(["National", "State"])

#: Columns written out, in this order.
KEEP_COLUMNS = (
    "SERIESID",
    "GEOLEVEL",
    "GEOID",
    "GEONAME",
    "MARKET",
    "PERIOD",
    "YEAR",
    "QUARTER",
    "SUPPRESSED",
    "VALUE1",
    "VALUE2",
)

REQUEST_PAUSE_SECONDS = 1.0
TIMEOUT_SECONDS = 600

#: Marker written as the final line of a completed file. Its absence in a file that
#: otherwise parses means the file predates the marker, not that it is truncated;
#: see ``file_status``. That distinction exists because the HMDA script checked for
#: a marker it never wrote, which would have re-downloaded a finished sample.
SENTINEL = "# complete"


def url_for(remote: str) -> str:
    return f"{BASE}/{remote}"


def file_status(path: Path) -> tuple[str, str]:
    """Classify a cached file as ``complete``, ``legacy`` or ``bad``."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return "bad", f"unreadable: {exc}"
    if not text.strip():
        return "bad", "empty"
    lines = text.splitlines()
    if not lines[0].startswith(KEEP_COLUMNS[0]):
        return "bad", "header missing or wrong"
    if lines[-1].strip() == SENTINEL:
        return "complete", ""
    if len(lines) < 2:
        return "bad", "header only, no data rows"
    return "legacy", "no completion marker"


def slim(raw: bytes) -> tuple[list[list[str]], dict[str, int]]:
    """Unzip, keep the pre-registered rows, and count everything dropped.

    The counts are returned rather than logged away because a filter whose effect
    is unrecorded is indistinguishable from a filter chosen after the fact.
    """
    counts = {
        "read": 0,
        "kept": 0,
        "wrong_series": 0,
        "wrong_market": 0,
        "wrong_geo": 0,
    }
    rows: list[list[str]] = []

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not members:
            raise SystemExit(
                f"no CSV inside the archive; contents: {archive.namelist()}"
            )
        for member in members:
            with archive.open(member) as handle:
                text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(text)
                header = [c.strip().upper() for c in (reader.fieldnames or [])]
                missing = [c for c in KEEP_COLUMNS if c not in header]
                if missing:
                    raise SystemExit(
                        f"{member}: expected columns missing: {missing}\n"
                        f"header returned was: {header}\n"
                        "The published schema changed. Stop and update "
                        "KEEP_COLUMNS in this file rather than guessing."
                    )
                for raw_row in reader:
                    counts["read"] += 1
                    row = {
                        (k.strip().upper() if k else ""): (v or "").strip()
                        for k, v in raw_row.items()
                    }
                    if row.get("SERIESID") not in KEEP_SERIES:
                        counts["wrong_series"] += 1
                        continue
                    if row.get("MARKET") not in KEEP_MARKETS:
                        counts["wrong_market"] += 1
                        continue
                    if row.get("GEOLEVEL") not in KEEP_GEOLEVELS:
                        counts["wrong_geo"] += 1
                        continue
                    rows.append([row.get(c, "") for c in KEEP_COLUMNS])
                    counts["kept"] += 1
    return rows, counts


def fetch_one(name: str, remote: str, *, dry_run: bool) -> dict:
    url = url_for(remote)
    out = RAW / f"nmdb_{name}.csv"
    record = {"name": name, "url": url, "path": str(out.relative_to(ROOT))}

    if dry_run:
        print(url)
        return {**record, "status": "dry-run"}

    if out.exists():
        status, why = file_status(out)
        if status == "complete":
            return {**record, "status": "cached", "bytes": out.stat().st_size}
        if status == "legacy":
            print(f"  {name}: legacy file kept as-is ({why})")
            return {**record, "status": "cached-legacy", "bytes": out.stat().st_size}
        spoiled = out.with_suffix(f".csv.expired.{int(time.time())}")
        out.rename(spoiled)
        print(f"  {name}: refetching, {why} -> {spoiled.name}")

    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"  {name}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    rows, counts = slim(raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(KEEP_COLUMNS)
        writer.writerows(rows)
        # Last, so its presence means the write finished.
        fh.write(f"{SENTINEL}\n")

    return {
        **record,
        "status": "downloaded",
        "seconds": round(time.time() - started, 1),
        "zipped_bytes": len(raw),
        "rows": counts,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def stamp_legacy() -> int:
    """Append the completion marker to files that parse. Appends only."""
    if not RAW.exists():
        print(f"  no directory at {RAW.relative_to(ROOT)}")
        return 1
    stamped = already = left = 0
    for path in sorted(RAW.glob("*.csv")):
        status, why = file_status(path)
        if status == "complete":
            already += 1
        elif status == "legacy":
            with path.open("a", encoding="utf-8") as fh:
                fh.write(f"{SENTINEL}\n")
            stamped += 1
        else:
            print(f"  {path.name}: NOT stamped, {why}")
            left += 1
    print(f"\n  {stamped} stamped, {already} already marked, {left} left alone")
    return 0 if left == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stamp-legacy", action="store_true")
    args = ap.parse_args()

    if args.stamp_legacy:
        return stamp_legacy()

    print(f"NMDB retrieval: {len(SOURCES)} source files")
    print(f"  series:     {sorted(KEEP_SERIES)}")
    print(f"  markets:    {sorted(KEEP_MARKETS)}")
    print(f"  geolevels:  {sorted(KEEP_GEOLEVELS)}")
    print(f"  output:     {RAW.relative_to(ROOT)}\n")

    records = []
    for name, remote in SOURCES:
        rec = fetch_one(name, remote, dry_run=args.dry_run)
        records.append(rec)
        if rec["status"] == "downloaded":
            c = rec["rows"]
            print(
                f"  {name:<22} {c['kept']:>7,} kept of {c['read']:>9,} "
                f"({c['wrong_series']:,} series, {c['wrong_market']:,} market, "
                f"{c['wrong_geo']:,} geo dropped)  {rec['seconds']}s"
            )
            time.sleep(REQUEST_PAUSE_SECONDS)
        elif rec["status"].startswith("cached"):
            print(f"  {name:<22} cached")

    if args.dry_run:
        return 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "base": BASE,
                "series_kept": sorted(KEEP_SERIES),
                "markets_kept": sorted(KEEP_MARKETS),
                "geolevels_kept": sorted(KEEP_GEOLEVELS),
                "columns_kept": list(KEEP_COLUMNS),
                "rate_buckets": [
                    {"series": s, "lower": lo, "upper": hi}
                    for s, lo, hi in RATE_BUCKETS
                ],
                "records": records,
            },
            indent=2,
        )
        + "\n"
    )

    ok = sum(r["status"].startswith(("downloaded", "cached")) for r in records)
    print(f"\n  {ok}/{len(records)} files present")
    print(f"  wrote {MANIFEST.relative_to(ROOT)}")
    return 0 if ok == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
