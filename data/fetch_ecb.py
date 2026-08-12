"""Retrieve the ECB daily euro reference rate, B6-A's external referee.

Registered in ``docs/b6_cuba_prereg.md`` §5 B6-4. This is the only source in
stage B6-A that is not the Banco Central de Cuba, and it exists because
everything else in the stage comes from one publisher.

Usage::

    python data/fetch_ecb.py
    python data/fetch_ecb.py --check      # classify what is cached, fetch nothing
    python data/fetch_ecb.py --force      # refetch even if cached

Endpoint, verified 2026-08-12::

    https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
        ?startPeriod=YYYY-MM-DD&endPeriod=YYYY-MM-DD&format=csvdata

Free, no key, no registration, one request covers the window.

What this referee can and cannot do
-----------------------------------

**It validates the source, not the pipeline.** ``b6_cuba_prereg.md`` §4.3 says
plainly that stage B6-A has **no zero calibration** over its window: the Cuban
analogue, elTOQUE's republication of the banks' posted rates, carries current
values only. This is weaker than a zero calibration and is stated as weaker. What
it establishes is that the euro column of the BCC table is the dollar column
times a real international cross rather than a fabricated or stale number.

**It is not a claim that the BCC copies the ECB.** On the seven overlapping days
available when B6-4 was written, the two agree to within 0.29% but track no fixed
lag: the closest match is same-day on one date and one business day back on
another. The BCC evidently runs its own fixing. That is why B6-4 registers a band
and not an envelope, and why the envelope clause was withdrawn; see the
pre-registration's changelog.

**It carries business days only**, so a Cuban publication day may have no
reference at all. That is coverage and it is reported. Nothing is interpolated:
an absent reference means the day does not enter B6-4, not that a nearby value
stands in for it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from monetary_topology.cuba_segments import (
    ECB_KEY,
    WINDOW_START,
    ecb_path,
    ecb_url,
    parse_ecb_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "ecb_manifest.json"

TIMEOUT_SECONDS = 120
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

#: Truncation detectors, not judgements about the data.
#:
#: The series is business-daily, so the longest legitimate run without an
#: observation is a weekend plus a cluster of TARGET holidays. Christmas is
#: inside this stage's window and closes 25 and 26 December, which with the
#: surrounding weekend can reach five calendar days. Ten leaves room for a
#: holiday pattern this stage has not seen while still firing on the hole a
#: truncated page would leave.
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


def check_coverage(observations: dict[str, float], start: date,
                   end: date) -> list[str]:
    """Raise on a short page; return the runs that are merely non-trading days."""
    if not observations:
        raise Truncated(f"no observations for {start} to {end}")
    days = sorted(date.fromisoformat(d) for d in observations)
    if days[0] > start + timedelta(days=MAX_GAP_DAYS):
        raise Truncated(
            f"first observation is {days[0]}, more than {MAX_GAP_DAYS} days "
            f"after the requested start {start}; the page may be cut at the front"
        )
    if (end - days[-1]).days > MAX_STALENESS_DAYS:
        raise Truncated(
            f"last observation is {days[-1]}, {(end - days[-1]).days} days "
            f"before the requested end {end}"
        )
    gaps = []
    for before, after in zip(days, days[1:], strict=False):
        span = (after - before).days
        if span > MAX_GAP_DAYS:
            raise Truncated(f"{span} days between {before} and {after}")
        if span > 1:
            gaps.append(f"{before}..{after}")
    return gaps


def check() -> int:
    """Classify what is cached and say so. Fetches nothing."""
    path = ecb_path(RAW)
    if not path.exists():
        print(f"  {path.name}: absent")
        return 1
    recorded = None
    if MANIFEST.exists():
        recorded = json.loads(
            MANIFEST.read_text(encoding="utf-8")
        ).get("sha256_stored")
    try:
        observations = parse_ecb_rows(path.read_text(encoding="utf-8"))
        status = f"{len(observations):,} observations"
        bad = False
    except ValueError as exc:
        status = f"BAD: {exc}"
        bad = True
    digest = sha256(path.read_bytes())
    if recorded is None:
        verdict = "not in the manifest"
    elif digest == recorded:
        verdict = "matches the manifest"
    else:
        verdict = "DOES NOT MATCH THE MANIFEST"
    print(f"  {path.name}: {status}, sha256 {digest[:12]}, {verdict}")
    return 1 if (bad or verdict.startswith("DOES NOT")) else 0


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
    out = ecb_path(RAW)
    url = ecb_url(WINDOW_START, end)
    print("ECB daily euro reference rate, B6-A's external referee")
    print(f"  window {WINDOW_START} to {end}, series {ECB_KEY}")
    # Printed rather than only recorded. A 4xx from an SDMX endpoint says
    # nothing about which part of the address was wrong, and the flow and the
    # key are two strings that look like one.
    print(f"  {url}\n")

    if out.exists() and not args.force:
        try:
            observations = parse_ecb_rows(out.read_text(encoding="utf-8"))
            check_coverage(observations, WINDOW_START, end)
        except (ValueError, Truncated) as exc:
            retire(out, str(exc))
        else:
            print(f"    {out.name}: cached, {len(observations):,} observations")
            return 0

    try:
        raw = download(url)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"    {out.name}: FAILED {exc}", file=sys.stderr)
        return 1

    try:
        observations = parse_ecb_rows(raw.decode("utf-8"))
        gaps = check_coverage(observations, WINDOW_START, end)
    except Exception as exc:  # noqa: BLE001
        print(f"    {out.name}: FAILED {exc}", file=sys.stderr)
        return 1

    write_atomic(out, raw)
    days = sorted(observations)
    print(f"    {out.name}: {len(observations):,} observations, "
          f"{days[0]} to {days[-1]}, {len(gaps)} non-trading runs")

    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "B6-A",
                "endpoint": url,
                "endpoint_verified": "2026-08-12",
                "series_key": ECB_KEY,
                "window": [WINDOW_START.isoformat(), end.isoformat()],
                "observations": len(observations),
                "first_date": days[0],
                "last_date": days[-1],
                "non_trading_runs": gaps,
                "provenance": (
                    "European Central Bank daily euro foreign-exchange "
                    "reference rates, US dollar against the euro, fixed at "
                    "14:15 CET. Free, no key. The only source in stage B6-A "
                    "that is not the Banco Central de Cuba. It validates the "
                    "source rather than the pipeline: b6_cuba_prereg.md 4.3 "
                    "states that this stage has no zero calibration over its "
                    "window, and this referee does not supply one. It is also "
                    "not a claim that the BCC copies the ECB; the two agree "
                    "within a band and track no fixed lag."
                ),
                "sha256_source": sha256(raw),
                "sha256_stored": sha256(out.read_bytes()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
