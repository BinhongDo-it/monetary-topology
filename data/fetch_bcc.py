"""Retrieve the Banco Central de Cuba daily segment rates for stage B6-A.

Registered in ``docs/b6_cuba_prereg.md`` §10. Availability, and the ruling that
the stage may be opened, are in ``docs/b6_cuba_availability.md``.

Usage::

    python data/fetch_bcc.py
    python data/fetch_bcc.py --check      # classify what is cached, fetch nothing
    python data/fetch_bcc.py --force      # refetch even if cached

Endpoint, verified 2026-08-12::

    https://api.bc.gob.cu/v1/tasas-de-cambio/historico
        ?fechaInicio=YYYY-MM-DD&fechaFin=YYYY-MM-DD&codigoMoneda=USD

Free, no key, no registration, both ends of the range inclusive, and one request
returns the whole window. **This is the authoritative source for every class in
stage B6-A**, which is the opposite of stage B5's position: there, one leg came
from a central bank and the rest from a newspaper.

Four things this fetcher does that the Argentine ones did not have to
--------------------------------------------------------------------

**It asserts the reconciliation between two delivery paths rather than assuming
it.** The XLSX export carries every calendar day; the API carries only the days
a rate was published; the XLSX's extra days are forward fills. Guard 2 checks
that this is what they are, on every date. A date present in both on which the
two disagree is an error, not a fill.

**It records the publication-day set**, so that the estimator's domain
(prereg §3.2) comes from the data rather than from a hard-coded calendar. The
publication schedule changes inside the window, so a calendar written down today
would be wrong for the first eleven weeks.

**It validates the markup schedule instead of reading it.** The nineteen channel
columns are the base times a fixed vector; that vector is a registered constant
in ``cuba_segments.MARKUP_SCHEDULE`` and the XLSX files are its validator. Guard
1 is an exact equality, because the publisher truncates at four decimals and
``published_from`` reproduces that exactly.

**It never repairs.** A response that fails to parse is renamed with an
``.expired`` suffix and left in place; nothing is interpolated, and a missing day
is recorded as a missing day.

The XLSX files are not fetched
------------------------------

The export is behind a form on ``bc.gob.cu`` rather than behind a URL, so the six
files are downloaded by hand and dropped into ``data/raw/bcc_xlsx/``. The loader
accepts only names matching ``VALID_XLSX``, which is the same device
``parallel_rates.VALID_NAME`` uses: **a file that should not be read is ignored
by the code rather than deleted from the disk** (the project's engineering rule 5). If the
directory is absent, guards 1 and 2 are reported as not run, and they are
reported as not run rather than as passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from monetary_topology.cuba_segments import (
    CURRENCIES,
    SEGMENTS,
    WINDOW_START,
    GuardFailed,
    bcc_path,
    guard_fixed_in_dollars,
    guard_paths_reconcile,
    guard_schedule_invariant,
    parse_bcc_rows,
    read_xlsx_table,
    xlsx_files,
    xlsx_skipped,
    xlsx_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
XLSX_DIR = RAW / "bcc_xlsx"
MANIFEST = RAW / "bcc_manifest.json"

BASE = (
    "https://api.bc.gob.cu/v1/tasas-de-cambio/historico"
    "?fechaInicio={start}&fechaFin={end}&codigoMoneda={code}"
)

TIMEOUT_SECONDS = 120
POLITE_DELAY_SECONDS = 1.0
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

#: Truncation detectors, not judgements about the data.
#:
#: A page cut short by the server is otherwise perfectly well formed, so the two
#: assertions below are the only things that distinguish it from a short window.
#: ``MAX_GAP_DAYS`` is set well above the worst run observed on 2026-08-12, which
#: was six days; its job is to fire on a hole a truncated page would leave, not
#: to grade the publication schedule.
MAX_GAP_DAYS = 10
MAX_STALENESS_DAYS = 14


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


class Truncated(Exception):
    """A well-formed response that does not cover what was asked for."""


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


def write_atomic(path: Path, data: bytes) -> None:
    """Temporary file, then rename, so a response is whole or absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def check_coverage(rows: list[dict], start: date, end: date) -> list[str]:
    """Raise on a short page; return the gaps that are merely non-publication.

    Three assertions, and none of them is "the first row is ``WINDOW_START``".

    * the first row is on or after ``WINDOW_START``, and **which day it is gets
      recorded rather than asserted**;
    * the last row is no more than ``MAX_STALENESS_DAYS`` behind the request's
      end, because a page cut at the back would stop early and look ordinary;
    * no two consecutive publication days are more than ``MAX_GAP_DAYS`` apart.

    **A currency may join the table later than the stage's window opens.** The
    yuan does: its record begins on 2025-12-31 while every other currency begins
    on 2025-12-19. An assertion that the first row equals ``WINDOW_START`` reads
    that as a truncated page, which is what it did on the first thirteen-currency
    run.

    Front truncation is then not detectable on a first run, and pretending
    otherwise would be worse than saying so: the first date is written to the
    manifest, and ``--check`` compares a cached response against it, so a page
    that starts later than it did before fails on the next run rather than never.

    The current day is legitimately absent: it has not entered the historical
    record yet, which is why the staleness bound is in days rather than zero.
    """
    if not rows:
        raise Truncated(f"no rows for {start} to {end}")
    first = date.fromisoformat(rows[0]["date"])
    last = date.fromisoformat(rows[-1]["date"])
    if first < start:
        raise Truncated(
            f"first row is {first}, before the requested start {start}"
        )
    if (end - last).days > MAX_STALENESS_DAYS:
        raise Truncated(
            f"last row is {last}, {(end - last).days} days before the "
            f"requested end {end}"
        )
    gaps = []
    days = [date.fromisoformat(r["date"]) for r in rows]
    for before, after in zip(days, days[1:], strict=False):
        span = (after - before).days
        if span > MAX_GAP_DAYS:
            raise Truncated(f"{span} days between {before} and {after}")
        if span > 1:
            gaps.append(f"{before}..{after}")
    return gaps


def fetch_currency(code: str, start: date, end: date, force: bool) -> dict:
    out = bcc_path(RAW, code)
    url = BASE.format(start=start.isoformat(), end=end.isoformat(), code=code)
    record: dict = {
        "name": out.name,
        "currency": code,
        "url": url,
        "range": [start.isoformat(), end.isoformat()],
    }

    if out.exists() and not force:
        try:
            rows = parse_bcc_rows(json.loads(out.read_text(encoding="utf-8")))
            check_coverage(rows, start, end)
        except (ValueError, Truncated) as exc:
            retire(out, str(exc))
        else:
            print(f"    {out.name}: cached, {len(rows):,} publication days, "
                  f"from {rows[0]['date']}")
            return {
                **record,
                "status": "cached",
                "rows": len(rows),
                "first_date": rows[0]["date"],
                "last_date": rows[-1]["date"],
                "sha256_stored": sha256(out.read_bytes()),
            }

    try:
        raw = download(url)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"    {out.name}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    try:
        rows = parse_bcc_rows(json.loads(raw.decode("utf-8")))
        gaps = check_coverage(rows, start, end)
    except Exception as exc:  # noqa: BLE001
        print(f"    {out.name}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    write_atomic(out, raw)
    late = " (joins the table late)" if rows[0]["date"] != start.isoformat() else ""
    print(
        f"    {out.name}: {len(rows):,} publication days, "
        f"{rows[0]['date']} to {rows[-1]['date']}, {len(gaps)} gaps{late}"
    )
    return {
        **record,
        "status": "downloaded",
        "bytes": len(raw),
        "rows": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "gaps": gaps,
        "sha256_source": sha256(raw),
        "sha256_stored": sha256(out.read_bytes()),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def run_guards(record: dict[str, list[dict]]) -> dict:
    """Guards 1, 2 and 3 of prereg §6, reported as run or as not run."""
    panel = {
        code: {r["date"]: {t: r[t] for t in SEGMENTS} for r in rows}
        for code, rows in record.items()
    }
    out: dict = {}

    print("  guard 3, the fixed segments are fixed against the dollar")
    out["guard_3_fixed_in_dollars"] = guard_fixed_in_dollars(
        panel["USD"], panel["EUR"]
    )
    print(f"    {out['guard_3_fixed_in_dollars']}")

    files = xlsx_files(RAW)
    if not files:
        skipped = xlsx_skipped(RAW)
        why = (
            f"{len(skipped)} files present but none named as the loader expects "
            f"({', '.join(repr(n) for n in skipped[:4])})"
            if skipped else "no files"
        )
        print(f"  guards 1 and 2 NOT RUN: {why} in "
              f"{XLSX_DIR.relative_to(ROOT)}")
        out["guard_1_schedule_invariant"] = "not run"
        out["guard_2_paths_reconcile"] = "not run"
        return out

    print(f"  guard 1, the markup schedule, over {len(files)} files")
    checked = 0
    for (code, segment), path in sorted(files.items()):
        header, rows = read_xlsx_table(path)
        counts = guard_schedule_invariant(header, rows, f"{code} {segment}")
        checked += sum(counts.values())
    print(f"    {checked:,} exact equalities, 0 departures")
    out["guard_1_schedule_invariant"] = {"exact_equalities": checked}

    print("  guard 2, the XLSX is the API forward-filled")
    reconciled: dict[str, dict] = {}
    for (code, segment), path in sorted(files.items()):
        header, rows = read_xlsx_table(path)
        report = guard_paths_reconcile(
            panel[code], header, rows, segment, f"{code} {segment}",
            xlsx_snapshot(path),
        )
        reconciled[f"{code}_{segment}"] = report
        print(
            f"    {code} {segment}: {report['xlsx_days']} calendar days, "
            f"{report['api_days']} publication days, "
            f"{len(report['filled_days'])} forward-filled, "
            f"{len(report['provisional_days'])} provisional at the "
            f"{report['snapshot']} snapshot, "
            f"{len(report['back_filled_days'])} back-filled before "
            f"{report['first_published']}"
        )
    out["guard_2_paths_reconcile"] = reconciled
    return out


def check() -> int:
    """Classify what is cached and say so. Fetches nothing."""
    if not RAW.exists():
        print(f"  no directory at {RAW.relative_to(ROOT)}")
        return 1
    recorded: dict[str, str] = {}
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for c in m.get("responses", []):
            if "sha256_stored" in c:
                recorded[c["name"]] = c["sha256_stored"]

    seen = bad = mismatched = 0
    for code in CURRENCIES:
        path = bcc_path(RAW, code)
        if not path.exists():
            print(f"  {path.name}: absent")
            continue
        seen += 1
        try:
            rows = parse_bcc_rows(json.loads(path.read_text(encoding="utf-8")))
            status = f"{len(rows):,} publication days"
        except ValueError as exc:
            status = f"BAD: {exc}"
            bad += 1
        digest = sha256(path.read_bytes())
        if path.name not in recorded:
            verdict = "not in the manifest"
        elif digest == recorded[path.name]:
            verdict = "matches the manifest"
        else:
            verdict = "DOES NOT MATCH THE MANIFEST"
            mismatched += 1
        print(f"  {path.name}: {status}, sha256 {digest[:12]}, {verdict}")

    files = xlsx_files(RAW)
    skipped = xlsx_skipped(RAW)
    print(f"  {len(files)} xlsx files matching the naming convention"
          + (f", {len(skipped)} skipped: "
             + ", ".join(repr(n) for n in skipped[:4]) if skipped else ""))
    if not seen:
        print("  nothing cached")
    print(f"  {seen} responses, {bad} bad, {mismatched} hash mismatches")
    return 1 if (bad or mismatched or not seen) else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch even if cached")
    args = ap.parse_args()

    if args.check:
        return check()

    end = datetime.now(timezone.utc).date()
    print("Banco Central de Cuba, daily segment rates, for stage B6-A")
    print(f"  window {WINDOW_START} to {end}, {len(CURRENCIES)} currencies\n")

    responses = []
    for code in CURRENCIES:
        responses.append(fetch_currency(code, WINDOW_START, end, args.force))
        if responses[-1]["status"] == "downloaded":
            time.sleep(POLITE_DELAY_SECONDS)

    failed = [r for r in responses if r.get("status") == "error"]
    if failed:
        print(f"\n  {len(failed)} of {len(responses)} failed; guards not run")
        return 1

    print()
    record = {
        code: parse_bcc_rows(
            json.loads(bcc_path(RAW, code).read_text(encoding="utf-8"))
        )
        for code in CURRENCIES
    }
    try:
        guards = run_guards(record)
    except GuardFailed as exc:
        print(f"\n  GUARD FAILED: {exc}", file=sys.stderr)
        print("  Nothing downstream may run. prereg 6.", file=sys.stderr)
        return 1

    publication = {code: [r["date"] for r in rows] for code, rows in record.items()}
    RAW.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "B6-A",
                "endpoint": BASE,
                "endpoint_verified": "2026-08-12",
                "window": [WINDOW_START.isoformat(), end.isoformat()],
                "provenance": (
                    "Banco Central de Cuba, daily rates for segments I, II and "
                    "III. Free, no key, no registration, both ends of the range "
                    "inclusive. Authoritative for every agent class in stage "
                    "B6-A: one publisher supplies all three, which removes the "
                    "reporter confound stage B5 had to live with and removes "
                    "the zero calibration it had. The nineteen channel columns "
                    "are not retrieved; they are the base times the registered "
                    "markup schedule, validated against the hand-downloaded "
                    "XLSX exports by guard 1."
                ),
                "responses": responses,
                "publication_days": publication,
                "guards": guards,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")
    for code, days in publication.items():
        print(f"  {code}: {len(days):,} publication days, "
              f"{days[0]} to {days[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
