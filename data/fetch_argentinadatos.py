"""Retrieve argentinadatos' peso-dollar series for stage B5.

Two series, and **neither is an agent class**:

- **``mayorista``**, the wholesale rate. This is the argentinadatos side of the
  zero calibration in ``docs/b5_orphan_prereg.md`` §4.4. Ámbito publishes the
  same number in a completely different format, and the two must come back equal
  to the cent after passing through two different parsers.
- **``tarjeta``**, the card rate. **Not a known-answer arm**; §5 records why no
  such arm exists on free data. It is a *dating instrument*: within one publisher
  ``tarjeta / oficial`` is a construction identity, and running it across the
  window shows where the tax regime landed in the data.

Usage::

    python data/fetch_argentinadatos.py
    python data/fetch_argentinadatos.py --check   # classify, fetch nothing
    python data/fetch_argentinadatos.py --force   # refetch

Endpoint, verified 2026-08-11::

    https://api.argentinadatos.com/v1/cotizaciones/dolares/<casa>

Free, no key. Returns the **whole series in one array**, from 2019-12 to the
present, as objects with ISO dates and JSON floats. No pagination and no date
range, so there is nothing to chunk: one request, one file, one hash.

Why this is a separate script from ``fetch_ambito.py``
------------------------------------------------------

**The two conventions must never meet in one parser.** Ámbito serves
``["12/06/2025","1176,00","1185,00"]``: comma decimals, thousands separators,
``DD/MM/YYYY``. This API serves ``{"compra":1176,"venta":1185,"fecha":
"2025-06-12"}``: JSON numbers, ISO dates. A parser lenient enough to read both
would be lenient enough to misread either, and the zero calibration in §4.4 is
built precisely on the two conventions being handled by two separate pieces of
code that have to agree.

So this script asserts **its own** convention as strictly as the other asserts
its: ISO dates only, JSON numbers only, and a comma-decimal string is an error
rather than something to be repaired.

What the guards are for
-----------------------

**``casa`` is checked on every row.** The endpoint takes the series name in the
path, so a typo returns a different series that parses perfectly and is silently
the wrong quantity. This is the same failure the CCL path already produced once
in this stage, in the form that does 404 rather than the form that does not.

**Duplicate dates raise rather than being collapsed.** Unlike Ámbito, this API
is expected to publish one row per date. If it ever does not, that is a change in
what the series is, and it must stop the run rather than be folded by a rule
nobody registered for it. The collapse rule in ``parallel_rates.py`` is
registered for Ámbito's intraday snapshots and for nothing else.

**The series grows daily**, so a cached file is stale by construction rather than
wrong. ``--check`` reports the last date it holds; ``--force`` refetches. The
window ends 2026-06-30, so once the file reaches that date staleness stops
mattering for this stage.
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

# **The registered rules live in the package, not here.** This script owns the
# network, the archive and the manifest; the parser and its two bands live beside
# Ambito's so that the pair in b5_orphan_prereg.md 4.4b cannot drift apart.
#
# **Imported under its full name and never aliased to `parse_rows`.** That name
# means Ambito's parser both in the package and in fetch_ambito.py, and the whole
# calibration arm rests on those two never being confused. An alias here would
# put the two conventions under one name in a project whose only defence against
# mixing them is that they have different names.
from monetary_topology.parallel_rates import (
    ARGENTINADATOS_CASAS,
    WINDOW_END,
    WINDOW_START,
    parse_argentinadatos_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "argentinadatos_manifest.json"

BASE = "https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}"

NAME = "argentinadatos_{casa}.json"

TIMEOUT_SECONDS = 180
POLITE_DELAY_SECONDS = 1.0
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def in_window(rows: list[dict]) -> list[dict]:
    """The rows inside the registered window. Reported, never used to filter
    the archive: the file keeps everything that arrived."""
    first, last = WINDOW_START.isoformat(), WINDOW_END.isoformat()
    return [r for r in rows if first <= r["date"] <= last]


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


def series_status(path: Path, casa: str) -> tuple[str, str, list[dict]]:
    """``complete`` or ``bad``; parsing is the completeness test."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return "bad", f"does not parse: {exc}", []
    try:
        rows = parse_argentinadatos_rows(payload, casa)
    except ValueError as exc:
        return "bad", f"schema: {exc}", []
    if not rows:
        return "bad", "no rows", []
    return "complete", "", rows


def write_atomic(path: Path, data: bytes) -> None:
    """Temporary file, then rename, so the file is whole or absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def summarise(rows: list[dict], casa: str) -> dict:
    inside = in_window(rows)
    return {
        "casa": casa,
        "purpose": ARGENTINADATOS_CASAS[casa],
        "rows": len(rows),
        "first_date": rows[0]["date"] if rows else None,
        "last_date": rows[-1]["date"] if rows else None,
        "rows_in_window": len(inside),
        "window_first": inside[0]["date"] if inside else None,
        "window_last": inside[-1]["date"] if inside else None,
        "covers_window_end": bool(rows) and rows[-1]["date"] >= WINDOW_END.isoformat(),
    }


def fetch_casa(casa: str, force: bool) -> dict:
    name = NAME.format(casa=casa)
    out = RAW / name
    url = BASE.format(casa=casa)
    record: dict = {"name": name, "url": url}

    if out.exists() and not force:
        status, why, rows = series_status(out, casa)
        if status == "complete":
            print(f"    {name}: cached, {len(rows):,} rows "
                  f"to {rows[-1]['date']}")
            return {
                **record, "status": "cached",
                "sha256_stored": sha256(out.read_bytes()),
                **summarise(rows, casa),
            }
        retire(out, why)

    try:
        raw = download(url)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"    {name}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    try:
        rows = parse_argentinadatos_rows(
            json.loads(raw.decode("utf-8")), casa
        )
    except Exception as exc:  # noqa: BLE001
        print(f"    {name}: FAILED to parse: {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": f"parse: {exc}"}

    # Verbatim: the bytes that arrived are the bytes stored.
    write_atomic(out, raw)
    summary = summarise(rows, casa)
    print(f"    {name}: {summary['rows']:,} rows, "
          f"{summary['first_date']} to {summary['last_date']}, "
          f"{summary['rows_in_window']:,} in window")
    if not summary["covers_window_end"]:
        print(f"      NOTE: does not reach {WINDOW_END}; the series is still "
              f"growing and this file will need refetching")
    return {
        **record,
        "status": "downloaded",
        "bytes": len(raw),
        "sha256_source": sha256(raw),
        "sha256_stored": sha256(out.read_bytes()),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **summary,
    }


def check() -> int:
    """Classify what is cached and say so. Fetches nothing."""
    if not RAW.exists():
        print(f"  no directory at {RAW.relative_to(ROOT)}")
        return 1
    recorded: dict[str, str] = {}
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for c in m.get("series", []):
            if "sha256_stored" in c:
                recorded[c["name"]] = c["sha256_stored"]

    seen = bad = mismatched = stale = 0
    for casa in ARGENTINADATOS_CASAS:
        path = RAW / NAME.format(casa=casa)
        if not path.exists():
            print(f"  {path.name}: not retrieved")
            continue
        status, why, rows = series_status(path, casa)
        digest = sha256(path.read_bytes())
        if path.name not in recorded:
            verdict = "not in the manifest"
        elif digest == recorded[path.name]:
            verdict = "matches the manifest"
        else:
            verdict = "DOES NOT MATCH THE MANIFEST"
            mismatched += 1
        if status == "complete":
            summary = summarise(rows, casa)
            detail = (f", {summary['rows']:,} rows to {summary['last_date']}, "
                      f"{summary['rows_in_window']:,} in window")
            if not summary["covers_window_end"]:
                detail += f" -- STALE, short of {WINDOW_END}"
                stale += 1
        else:
            detail = f" -- {why}"
            bad += 1
        print(f"  {path.name}: {status}{detail}, sha256 {digest[:12]}, {verdict}")
        seen += 1
    print(f"  {seen} series, {bad} bad, {mismatched} hash mismatches, "
          f"{stale} short of the window end")
    return 1 if (bad or mismatched) else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch series that are already cached")
    args = ap.parse_args()

    if args.check:
        return check()

    print("argentinadatos peso-dollar series, for stage B5")
    print(f"  window {WINDOW_START} to {WINDOW_END}, "
          f"{len(ARGENTINADATOS_CASAS)} series\n")

    series = []
    for casa, purpose in ARGENTINADATOS_CASAS.items():
        print(f"  {casa} ({purpose})")
        series.append(fetch_casa(casa, args.force))
        if series[-1]["status"] == "downloaded":
            time.sleep(POLITE_DELAY_SECONDS)
        print()

    RAW.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "B5",
                "endpoint": BASE,
                "endpoint_verified": "2026-08-11",
                "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
                "provenance": (
                    "argentinadatos is a community aggregator, not a central "
                    "bank and not an exchange. Neither series retrieved here is "
                    "an agent class and neither enters the headline. mayorista "
                    "is the argentinadatos side of the zero calibration "
                    "(b5_orphan_prereg.md 4.4): Ambito publishes the same "
                    "number in a different format and the two must agree after "
                    "passing through two different parsers, which is what makes "
                    "the arm a test of this project's pipeline rather than of "
                    "the publishers. tarjeta is a dating instrument for the tax "
                    "regime (5.2); it is NOT a known-answer arm, because every "
                    "free tarjeta series is computed by its publisher from that "
                    "publisher's own oficial and cannot fail."
                ),
                "series": series,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {MANIFEST.relative_to(ROOT)}")

    failed = [s for s in series if s.get("status") == "error"]
    held = [s for s in series if s.get("status") != "error"]
    print(f"  {len(held)} series held, "
          f"{sum(s.get('rows_in_window', 0) for s in held):,} rows in window, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
