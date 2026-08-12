#!/usr/bin/env python3
"""Retrieve the HMDA sample for B2 loop A. Run locally; needs network.

Pre-registered in ``docs/b2_measurement.md``. Every filter below is fixed there
and none may be changed after results are seen.

Usage::

    python data/fetch_hmda.py                    # the pre-registered sample
    python data/fetch_hmda.py --years 2024       # one year, for a quick check
    python data/fetch_hmda.py --states AZ        # one state, for a quick check
    python data/fetch_hmda.py --dry-run          # print the URLs and exit
    python data/fetch_hmda.py --product fha      # the graded placebo, section 8.1
    python data/fetch_hmda.py --stamp-legacy     # verify and mark pre-sentinel files

Writes one CSV per (msa, year) into ``data/raw/hmda/`` and a manifest recording
what was retrieved and when. Downloads are skipped if the file already exists, so
the script is resumable.

Why this is a script and not a manual download: the sample has to be fixed before
any result is visible, and a scripted retrieval is the only way a reader can check
that it was.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "hmda"
MANIFEST = ROOT / "data" / "raw" / "hmda_manifest.json"

API = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"

#: Loan programmes retrieved, each into its own directory.
#:
#: Conventional is the main sample. FHA and VA are the graded placebo registered in
#: section 8.1 of ``docs/b2_measurement.md``, and the load-bearing comparison there
#: is conventional against VA rather than against FHA.
#:
#: Separate directories, not a column in one directory. The conventional sample is
#: already retrieved and the loader globs a single directory non-recursively, so a
#: new programme cannot reach the existing files by any path. That is the whole
#: reason for the layout.
PRODUCTS: dict[str, tuple[str, str]] = {
    "conventional": ("Conventional:First Lien", "hmda"),
    "fha": ("FHA:First Lien", "hmda_fha"),
    "va": ("VA:First Lien", "hmda_va"),
}


def raw_dir(product: str) -> Path:
    return ROOT / "data" / "raw" / PRODUCTS[product][1]


def manifest_path(product: str) -> Path:
    return ROOT / "data" / "raw" / f"{PRODUCTS[product][1]}_manifest.json"


# ---------------------------------------------------------------------------
# The pre-registered sample. Do not edit after retrieval begins.
# ---------------------------------------------------------------------------

#: HMDA modern LAR carries rate spread for all loans only from 2018. Earlier
#: years reported it for higher-priced loans alone, which would select exactly
#: the tail this measurement is about. So loop A's window starts in 2018, and the
#: longer vintage range in the measurement design applies to loop B only.
YEARS = (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)

#: States, not metros, and all of them.
#:
#: The first draft queried the 50 largest CBSAs by code. Two problems surfaced on
#: the first real call, both before any loop sum was computed, and both recorded
#: here rather than quietly fixed.
#:
#: Divided CBSAs return nothing. HMDA reports ``derived_msa-md``, which for a
#: divided CBSA is the Metropolitan Division code, not the CBSA code. New York
#: (35620) and Los Angeles (31080) returned a header and zero rows. Hand-coding
#: the division codes for eleven divided metros is error-prone and every mistake
#: silently drops a metro.
#:
#: More to the point, metro is not a cell key. Cells are defined by census tract,
#: so the metro list only ever defined the sample frame. Dropping it removes a
#: selection rather than adding one: the sample goes from fifty chosen metros to
#: the whole country, which strictly enlarges it and cannot bias the result.
STATES = (
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
)

#: Retained only so the earlier draft's frame is recoverable for comparison.
LEGACY_MSAMDS = (
    "35620",
    "31080",
    "16980",
    "19100",
    "26420",
    "47900",
    "37980",
    "12060",
    "38060",
    "14460",
    "41860",
    "40140",
    "19820",
    "42660",
    "33100",
    "45300",
    "36740",
    "41180",
    "17140",
    "28140",
    "38900",
    "40900",
    "19740",
    "12580",
    "16740",
    "41700",
    "33460",
    "41940",
    "39580",
    "12420",
    "29820",
    "17460",
    "18140",
    "27260",
    "34980",
    "36420",
    "31140",
    "24860",
    "40060",
    "32820",
    "35380",
    "15380",
    "26900",
    "39300",
    "38300",
    "25540",
    "19660",
    "41620",
    "10740",
    "16700",
)

#: Filters sent to the API. Only two, and only because they cut the download.
#:
#: The first draft sent five and every call returned HTTP 400. Each filter works
#: alone, so the rejection is in the combination, and rather than guess which pair
#: the server dislikes, everything not needed for size reduction now happens
#: locally in ``keep_row``. That is the better arrangement regardless: an
#: exclusion written in our own code is visible, testable and recorded, whereas an
#: exclusion delegated to a query string is neither.
FILTERS = {
    # home purchase only. Refinance and cash-out are different transitions.
    "loan_purposes": "1",
    # First lien, one programme per retrieval. The main sample is conventional.
    # FHA and VA price by programme rather than by borrower, which is a different
    # mechanism and would contaminate the cell if mixed in; kept apart, that same
    # difference is exactly what makes them a placebo.
    "loan_products": PRODUCTS["conventional"][0],
}


def filters_for(product: str) -> dict[str, str]:
    return {**FILTERS, "loan_products": PRODUCTS[product][0]}


#: Applied locally, row by row, after download.
#:
#: ``action_taken == 1`` is not optional and its absence was the more serious of
#: the two bugs found on the first real call. Purchased loans, action taken 6,
#: report ``rate_spread`` as NA, and the first sample returned was almost entirely
#: those. Filtering to originations is what makes the field observable at all.
LOCAL_FILTERS = {
    "action_taken": "1",
    "lien_status": "1",
    "derived_dwelling_category": "Single Family (1-4 Units):Site-Built",
}

#: Columns kept from the returned LAR. Everything here is a property of the loan
#: or the property; nothing is a property of the borrower, by construction.
#: Note the hyphen in ``derived_msa-md``. The first draft wrote it with an
#: underscore, which does not match the header the API returns, so the column was
#: silently dropped. Nothing downstream used it, but a silently missing column is
#: exactly the failure mode that turns into a wrong number later.
KEEP = (
    "activity_year",
    "derived_msa-md",
    "state_code",
    "county_code",
    "census_tract",
    "occupancy_type",
    "lien_status",
    "loan_purpose",
    "derived_loan_product_type",
    "derived_dwelling_category",
    "action_taken",
    "rate_spread",
    "interest_rate",
    "loan_term",
    # Diagnostics, for the pre-registered falsification asking whether the
    # dispersion is accounted for by loan characteristics that are themselves
    # positions. Loan amount, property value and DTI are modified for privacy;
    # LTV and points are not.
    "loan_to_value_ratio",
    "debt_to_income_ratio",
    "discount_points",
    "total_loan_costs",
    "income",
    # The scoring model used, not the score. The score itself is redacted.
    "applicant_credit_score_type",
)

REQUEST_PAUSE_SECONDS = 1.0
TIMEOUT_SECONDS = 900


def build_url(state: str, year: int, product: str = "conventional") -> str:
    params = {"years": str(year), "states": state, **filters_for(product)}
    return f"{API}?{urllib.parse.urlencode(params)}"


def keep_row(row: dict) -> bool:
    """Local filters, applied after download so the exclusions are our own."""
    return all(row.get(k, "").strip() == v for k, v in LOCAL_FILTERS.items())


def slim(raw: bytes) -> tuple[list[str], list[list[str]]]:
    """Keep the pre-registered columns and drop rows with no reported spread.

    Rows without a spread are dropped rather than imputed. The count is recorded
    in the manifest so the exclusion is visible.
    """
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    header = [c for c in KEEP if c in (reader.fieldnames or [])]
    rows: list[list[str]] = []
    dropped_filter = 0
    dropped = 0
    for row in reader:
        if not keep_row(row):
            dropped_filter += 1
            continue
        spread = (row.get("rate_spread") or "").strip()
        if spread in ("", "NA", "Exempt"):
            dropped += 1
            continue
        try:
            float(spread)
        except ValueError:
            dropped += 1
            continue
        rows.append([row.get(c, "") for c in header])
    return header, rows, dropped, dropped_filter  # type: ignore[return-value]


#: Marker written as the final line of a completed file.
#:
#: Without it, an interrupted or partially recovered file is indistinguishable
#: from a complete one, and the analysis would load a truncated sample and report
#: a number for it. That is worse than having no data, because it fails silently.
#: A file lacking this marker is re-fetched rather than trusted.
SENTINEL = "# complete"


def file_status(path: Path) -> tuple[str, str]:
    """Classify a cached file as ``complete``, ``legacy`` or ``bad``.

    Three states rather than two, and the middle one exists because of a bug that
    would otherwise have cost hours.

    ``SENTINEL`` was defined and checked for, but ``fetch_one`` never wrote it. Every
    file retrieved before that was fixed therefore lacks the marker. Under a
    two-state test all of them classify as truncated, get renamed aside and get
    re-downloaded, which for the conventional sample means 408 files and
    20,071,900 rows going quiet for several hours over a marker the code itself
    failed to write.

    So a file with a valid header and at least one data row, but no marker, is
    ``legacy``: used as-is and reported, never renamed and never refetched.
    ``--stamp-legacy`` checks such files against the manifest's recorded row count
    and appends the marker where they agree, which upgrades them in place.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return "bad", f"unreadable: {exc}"
    if not text.strip():
        return "bad", "empty"
    lines = text.splitlines()
    if not lines[0].startswith("activity_year"):
        return "bad", "header missing or wrong"
    if lines[-1].strip() == SENTINEL:
        return "complete", ""
    if len(lines) < 2:
        return "bad", "header only, no data rows"
    return "legacy", "no completion marker; retrieved before the marker was written"


def data_row_count(path: Path) -> int:
    """Rows in a retrieved file, excluding header and any marker line."""
    with path.open(newline="", encoding="utf-8") as fh:
        return (
            sum(1 for row in csv.reader(fh) if row and not row[0].startswith("#")) - 1
        )


def stamp_legacy(product: str) -> int:
    """Append the completion marker to legacy files whose row count checks out.

    Appends only. Nothing is renamed, overwritten or removed. A file whose count
    disagrees with the manifest is left exactly as it is and reported, because a
    disagreement is the truncation the marker was meant to catch and guessing
    which side is right is not this function's job.
    """
    directory = raw_dir(product)
    if not directory.exists():
        print(f"  no directory at {directory.relative_to(ROOT)}")
        return 1

    expected: dict[str, int] = {}
    mpath = manifest_path(product)
    if mpath.exists():
        for rec in json.loads(mpath.read_text()).get("records", []):
            if "rows_kept" in rec:
                expected[Path(rec["path"]).name] = int(rec["rows_kept"])

    stamped = mismatched = already = 0
    for path in sorted(directory.glob("*.csv")):
        status, why = file_status(path)
        if status == "complete":
            already += 1
            continue
        if status == "bad":
            print(f"  {path.name}: NOT stamped, {why}")
            mismatched += 1
            continue
        want = expected.get(path.name)
        have = data_row_count(path)
        if want is not None and want != have:
            print(f"  {path.name}: NOT stamped, manifest says {want}, file has {have}")
            mismatched += 1
            continue
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{SENTINEL}\n")
        stamped += 1

    note = "" if expected else "  (no manifest found, row counts unverified)"
    print(
        f"\n  {stamped} stamped, {already} already marked, "
        f"{mismatched} left alone{note}"
    )
    return 0 if mismatched == 0 else 1


def fetch_one(
    state: str,
    year: int,
    *,
    dry_run: bool,
    recheck: bool = True,
    product: str = "conventional",
) -> dict:
    url = build_url(state, year, product)
    directory = raw_dir(product)
    out = directory / f"hmda_{state}_{year}.csv"
    record = {
        "state": state,
        "year": year,
        "product": product,
        "url": url,
        "path": str(out.relative_to(ROOT)),
    }

    if dry_run:
        print(url)
        return {**record, "status": "dry-run"}
    if out.exists():
        if not recheck:
            return {**record, "status": "cached", "bytes": out.stat().st_size}
        status, why = file_status(out)
        if status == "complete":
            return {**record, "status": "cached", "bytes": out.stat().st_size}
        if status == "legacy":
            # Used as-is. See ``file_status``: the marker's absence is this
            # script's fault, not evidence about the file.
            print(f"  {state} {year}: legacy file kept as-is ({why})")
            return {**record, "status": "cached-legacy", "bytes": out.stat().st_size}
        # Never deleted. The bad file is renamed out of the way so it stays on
        # disk for inspection, and the loader ignores it because the name no
        # longer matches the retrieval convention.
        spoiled = out.with_suffix(f".csv.expired.{int(time.time())}")
        out.rename(spoiled)
        print(f"  {state} {year}: refetching, {why} -> {spoiled.name}")

    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"  {state} {year}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    header, rows, dropped, dropped_filter = slim(raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
        # The marker goes on last, after the rows are on disk, so its presence
        # means the write finished. Omitting this was the bug ``file_status``
        # describes.
        fh.write(f"{SENTINEL}\n")

    return {
        **record,
        "status": "downloaded",
        "seconds": round(time.time() - started, 1),
        "rows_kept": len(rows),
        "rows_dropped_local_filter": dropped_filter,
        "rows_dropped_no_spread": dropped,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", nargs="*", type=int, default=list(YEARS))
    ap.add_argument("--states", nargs="*", default=list(STATES))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--product",
        choices=sorted(PRODUCTS),
        default="conventional",
        help="loan programme; each writes to its own directory",
    )
    ap.add_argument(
        "--stamp-legacy",
        action="store_true",
        help=(
            "append the completion marker to files retrieved before it was "
            "written, after checking their row counts against the manifest"
        ),
    )
    args = ap.parse_args()

    directory = raw_dir(args.product)
    mpath = manifest_path(args.product)

    if args.stamp_legacy:
        print(f"stamping legacy files in {directory.relative_to(ROOT)}")
        return stamp_legacy(args.product)

    print(
        f"HMDA loop A retrieval [{args.product}]: "
        f"{len(args.states)} states x {len(args.years)} years"
    )
    print(f"  api filters:   {filters_for(args.product)}")
    print(f"  local filters: {LOCAL_FILTERS}")
    print(f"  output:  {directory.relative_to(ROOT)}\n")

    records = []
    for year in args.years:
        for state in args.states:
            rec = fetch_one(
                str(state), year, dry_run=args.dry_run, product=args.product
            )
            records.append(rec)
            if rec["status"] == "downloaded":
                print(
                    f"  {state} {year}: {rec['rows_kept']:>7} kept, "
                    f"{rec['rows_dropped_local_filter']:>7} filtered, "
                    f"{rec['rows_dropped_no_spread']:>7} no spread, {rec['seconds']}s"
                )
                time.sleep(REQUEST_PAUSE_SECONDS)

    if args.dry_run:
        return 0

    # Merge with any existing manifest so a resumed run does not lose the
    # retrieval record of files it found cached rather than downloaded.
    merged: dict[str, dict] = {}
    if mpath.exists():
        for rec in json.loads(mpath.read_text()).get("records", []):
            merged[rec.get("path", "")] = rec
    for rec in records:
        prior = merged.get(rec.get("path", ""))
        if rec["status"].startswith("cached") and prior:
            merged[rec["path"]] = {**prior, "status": rec["status"]}
        else:
            merged[rec.get("path", "")] = rec
    all_records = list(merged.values())

    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "endpoint": API,
                "product": args.product,
                "api_filters": filters_for(args.product),
                "local_filters": LOCAL_FILTERS,
                "columns_kept": list(KEEP),
                "years": list(args.years),
                "states": list(args.states),
                "records": all_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    ok = sum(r["status"].startswith(("downloaded", "cached")) for r in records)
    legacy = sum(r["status"] == "cached-legacy" for r in records)
    kept = sum(r.get("rows_kept", 0) for r in records)
    print(f"\n  {ok}/{len(records)} files present, {kept:,} loans downloaded this run")
    if legacy:
        print(f"  {legacy} kept as legacy; run --stamp-legacy to mark them verified")
    print(f"  wrote {mpath.relative_to(ROOT)}")
    return 0 if ok == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
