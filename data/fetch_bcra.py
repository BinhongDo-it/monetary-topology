"""Retrieve the BCRA Comunicacion A 3500 reference rate for stage B5.

Registered in ``docs/b5_orphan_prereg.md`` §3.1: **the headline mid for the
oficial class comes from the central bank, not from Ambito.** Ambito's
``dolar/oficial`` is a range across retail bank counters, and §3.2 rules that
using it as the oficial leg would put dispersion across banks -- which is an
agent index -- into the headline and into the friction term.

Usage::

    python data/fetch_bcra.py
    python data/fetch_bcra.py --check      # classify what is cached, fetch nothing
    python data/fetch_bcra.py --force      # refetch chunks already cached

**This is the one authoritative source in stage B5.** Every other series is a
newspaper's or an aggregator's quote. That is why the stage's provenance
paragraph can say at least one side of every premium comes from a central bank.

Endpoint, verified 2026-08-11::

    https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/REF
        ?fechadesde=YYYY-MM-DD&fechahasta=YYYY-MM-DD

Free, no key, no registration. The currency code is **``REF``**, listed in
``/Maestros/Divisas`` as ``DOLAR REFERENCIA COM 3500``. ``USD`` is a different
series on the same API and is **not** what §3.1 registers.

Three ways this API differs from Ambito's, each of which is a place to get it
wrong
--------------------------------------------------------------------------------

**Numbers are JSON floats with a period, not strings with a comma.** The Ambito
parser's comma rule would reject every row here, and a parser written for one
must not be pointed at the other. Both assert their own convention.

**One reference rate, no bid and no ask.** A central bank publishes a reference,
not a quote it will trade on. So the oficial class carries a headline mid from
here and **its friction term from somewhere else** -- Banco de la Nacion's posted
counter rates, per §3.2 -- and until that is retrieved the oficial class has no
friction column at all.

**The response is paginated and says so in its own metadata.** ``resultset``
carries ``count``, ``offset`` and ``limit``. A range wider than ``limit`` returns
a truncated page that is otherwise perfectly well formed, so the guard below
compares ``count`` against ``limit`` and **fails rather than accepting a short
answer**. Half-year chunks hold roughly 130 business days against a limit of
1000, so this should never fire; it exists because the failure it catches is
invisible.
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

# **The registered rules live in the package, not here.** The window, the
# currency code, the plausibility band and the parser all live beside Ambito's
# and argentinadatos' so that the three conventions cannot drift apart. This
# script owns the network, the archive and the manifest.
from monetary_topology.parallel_rates import (
    BCRA_CODE,
    WINDOW_END,
    WINDOW_START,
    parse_bcra_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "bcra_manifest.json"

BASE = (
    "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/{code}"
    "?fechadesde={start}&fechahasta={end}"
)

#: ``ambito_<key>_<start>_<end>.json`` has an analogue here so that the two
#: archives read the same way.
NAME = "bcra_ref_{year}H{half}.json"

TIMEOUT_SECONDS = 120
POLITE_DELAY_SECONDS = 1.0
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunk_halves() -> list[tuple[int, int, date, date]]:
    """Half-year chunks over the registered window, clipped at both ends."""
    out = []
    for year in range(WINDOW_START.year, WINDOW_END.year + 1):
        spans = (
            (date(year, 1, 1), date(year, 6, 30)),
            (date(year, 7, 1), date(year, 12, 31)),
        )
        for half, (first, last) in enumerate(spans, start=1):
            start = max(WINDOW_START, first)
            end = min(WINDOW_END, last)
            if start <= end:
                out.append((year, half, start, end))
    return out


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


def chunk_status(path: Path) -> tuple[str, str, list[dict]]:
    """``complete``, ``empty`` or ``bad``; parsing is the completeness test."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return "bad", f"does not parse: {exc}", []
    try:
        rows = parse_bcra_rows(payload)
    except ValueError as exc:
        return "bad", f"schema: {exc}", []
    if not rows:
        return "empty", "no rows in range", []
    return "complete", "", rows


def write_atomic(path: Path, data: bytes) -> None:
    """Temporary file, then rename, so a chunk is whole or absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def fetch_chunk(year: int, half: int, start: date, end: date,
                force: bool) -> dict:
    name = NAME.format(year=year, half=half)
    out = RAW / name
    url = BASE.format(code=BCRA_CODE, start=start.isoformat(), end=end.isoformat())
    record: dict = {
        "name": name, "series": "bcra_ref", "url": url,
        "range": [start.isoformat(), end.isoformat()],
    }

    if out.exists() and not force:
        status, why, rows = chunk_status(out)
        if status in ("complete", "empty"):
            print(f"    {name}: cached, {len(rows):,} rows")
            return {
                **record, "status": f"cached-{status}", "rows": len(rows),
                "first_date": rows[0]["date"] if rows else None,
                "last_date": rows[-1]["date"] if rows else None,
                "sha256_stored": sha256(out.read_bytes()),
            }
        retire(out, why)

    try:
        raw = download(url)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"    {name}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    try:
        rows = parse_bcra_rows(json.loads(raw.decode("utf-8")))
    except Exception as exc:  # noqa: BLE001
        print(f"    {name}: FAILED to parse: {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": f"parse: {exc}"}

    # Verbatim: the bytes that arrived are the bytes stored.
    write_atomic(out, raw)
    tail = f", {rows[0]['date']} to {rows[-1]['date']}" if rows else ""
    print(f"    {name}: {len(rows):,} rows{tail}")
    return {
        **record,
        "status": "downloaded" if rows else "empty",
        "bytes": len(raw),
        "rows": len(rows),
        "first_date": rows[0]["date"] if rows else None,
        "last_date": rows[-1]["date"] if rows else None,
        "sha256_source": sha256(raw),
        "sha256_stored": sha256(out.read_bytes()),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def check() -> int:
    """Classify what is cached and say so. Fetches nothing."""
    if not RAW.exists():
        print(f"  no directory at {RAW.relative_to(ROOT)}")
        return 1
    recorded: dict[str, str] = {}
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for c in m.get("chunks", []):
            if "sha256_stored" in c:
                recorded[c["name"]] = c["sha256_stored"]

    seen = bad = mismatched = 0
    for path in sorted(RAW.glob("bcra_ref_*.json")):
        status, why, rows = chunk_status(path)
        digest = sha256(path.read_bytes())
        if path.name not in recorded:
            verdict = "not in the manifest"
        elif digest == recorded[path.name]:
            verdict = "matches the manifest"
        else:
            verdict = "DOES NOT MATCH THE MANIFEST"
            mismatched += 1
        detail = f", {len(rows):,} rows" if status == "complete" else f" -- {why}"
        print(f"  {path.name}: {status}{detail}, sha256 {digest[:12]}, {verdict}")
        seen += 1
        if status == "bad":
            bad += 1
    if not seen:
        print("  nothing cached")
    print(f"  {seen} chunks, {bad} bad, {mismatched} hash mismatches")
    return 1 if (bad or mismatched) else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch chunks that are already cached")
    args = ap.parse_args()

    if args.check:
        return check()

    spans = chunk_halves()
    print("BCRA Comunicacion A 3500 reference rate, for stage B5")
    print(f"  window {WINDOW_START} to {WINDOW_END}, {len(spans)} chunks\n")

    chunks = []
    for year, half, start, end in spans:
        chunks.append(fetch_chunk(year, half, start, end, args.force))
        if chunks[-1]["status"] in ("downloaded", "empty"):
            time.sleep(POLITE_DELAY_SECONDS)

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
                "currency_code": BCRA_CODE,
                "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
                "provenance": (
                    "Banco Central de la Republica Argentina, Comunicacion A "
                    "3500 reference rate, currency code REF. Free, no key. This "
                    "is the one authoritative source in stage B5 and it "
                    "supplies the oficial class's headline mid; every other "
                    "series is a newspaper's or an aggregator's quote. It is a "
                    "reference rate and carries no bid or ask, so the oficial "
                    "class's friction term must come from Banco de la Nacion "
                    "instead, per b5_orphan_prereg.md 3.2."
                ),
                "chunks": chunks,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")

    failed = [c for c in chunks if c.get("status") == "error"]
    held = [c for c in chunks if c.get("status") != "error"]
    print(f"  {len(held)} chunks held, "
          f"{sum(c.get('rows', 0) for c in held):,} rows, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
