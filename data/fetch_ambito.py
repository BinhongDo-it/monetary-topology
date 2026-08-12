"""Retrieve Ambito's peso-dollar quote series for stage B5.

Registered in ``docs/b5_orphan_prereg.md``; sourcing, the endpoint verification
and the decision to open the stage at all are in
``docs/b5_orphan_availability.md``.

Usage::

    python data/fetch_ambito.py
    python data/fetch_ambito.py --check      # classify what is cached, fetch nothing
    python data/fetch_ambito.py --force      # refetch chunks already cached

**This covers four of the seven series the stage needs.** The oficial leg's
headline mid (BCRA Comunicacion A 3500), the friction leg (Banco de la Nacion
counter rates) and the P2P leg come from endpoints that
``b5_orphan_availability.md`` did **not** verify, so they are not implemented
here. Writing a retriever against an unverified endpoint produces code whose
first real test is the day the data is needed -- which is exactly what happened
to the CCL path below.

**Provenance, at the top rather than in a footnote.** Ambito Financiero is a
newspaper. Every series in this file is a newspaper's quote, which is a step down
from every other source in this project, and ``b5_orphan_prereg.md`` §9.4 says so
in the write-up.

What this script does that a plain download would not
-----------------------------------------------------

**It never deletes.** A chunk that fails classification is renamed with an
``.expired.<timestamp>`` suffix and left in place. **This repository does not
delete**: a recursive delete once destroyed hours of retrieval, and the fix
was to make the loader recognise what it should read rather than to remove
what it should not.

**It detects truncation structurally rather than with a marker.**
``fetch_cip.py`` appends a sentinel line because a truncated CSV still parses as
a CSV. A truncated JSON array does not parse. Combined with an atomic write --
temporary file, then rename -- a chunk on disk is either wholly there or absent.
**So this script writes the bytes it received, verbatim, and adds nothing.**

**It asserts the number format on every row.** Ambito returns ``DD/MM/YYYY``
dates and **comma decimal separators**, with periods as thousands separators. A
parser that assumes the anglophone convention turns ``1.071,36`` into either
``1.07136`` or ``107136`` and never raises. The token regex rejects both readings
rather than trusting a plausibility band, which would not catch a
factor-of-a-hundred error at the 2019 end of the window where levels were near
sixty.

**It collapses each date to one row before doing anything else with it.** See
below: this endpoint does not return a daily series.

**It records anomalies and repairs nothing.** A row whose one-day change in the
log mid exceeds ``JUMP_THRESHOLD`` is written to the manifest as a
``DataAnomaly``. **Its value is not changed and the row is not dropped.** The
threshold's only job is to populate the list that criterion B5-10 computes the
headline with and without.

Three things learned from the first real run, 2026-08-11
--------------------------------------------------------

**The endpoint returns intraday snapshots, not a daily series, and nothing in
the availability check said so.** 385 of the first run's 5,248 rows were repeat
dates -- between two and nine rows for one day, with slightly different values.
Within-day log range: oficial median 0.00097 and p90 0.0049, informal median
0.0050 and p90 0.0165. That ambiguity is negligible against a hundred-percent
cepo-era gap and is **a third of the signal** against the few-percent gap that
remains after April 2025, which is the window criterion B5-8 reads. So the
collapse rule is load-bearing and is registered in ``b5_orphan_prereg.md`` §3.5:
**the row whose mid is that date's median mid, lower median on ties.**

Median rather than mean, and rather than first-or-last: on 21 August 2024
``dolar/oficial`` returns ``954.12 / 300.76 / 953.17`` for one date. The mean is
736 and belongs to no market; the median is 953.17. First-or-last would depend
on a within-day ordering this endpoint does not document -- there are no
timestamps. ``PROJECT_PLAN.md`` §11.2 is this project's standing lesson about
non-robust statistics under contamination.

**The anomaly scan was reading the wrong object.** Run on uncollapsed rows it
reported two "one-day changes" whose previous date equalled their own date --
within-day dispersion mistaken for a day-over-day jump. ``PROJECT_PLAN.md``
§11.11 rule 2: a guard must compare the quantity that is actually reported. It
now runs on the collapsed series.

**The CCL path in the availability check was inferred, not verified.**
``b5_orphan_availability.md`` §7.1 lists ``dolarrava/ccl`` with the parenthetical
"(same shape)". It 404s on every year. The working path is ``dolarrava/cl``,
verified 2026-08-11 against a ten-day range.
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

# **The registered constants and rules live in the package, not here.** A
# pre-registered threshold that exists in two files has two truths, and the one
# that gets edited is whichever the next reader happens to open. This script
# owns the network, the archive and the manifest; it owns no measurement
# decision.
from monetary_topology.parallel_rates import (
    ALL_AMBITO,
    JUMP_THRESHOLD,
    VALID_NAME,
    WINDOW_END,
    WINDOW_START,
    collapse_to_daily,
    is_superseded,
    parse_rows,
    scan_anomalies,
    within_day_dispersion,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "ambito_manifest.json"

BASE = "https://mercados.ambito.com/{path}/historico-general/{start}/{end}"

TIMEOUT_SECONDS = 120

#: Ambito is a newspaper serving a page, not an API with a published quota.
POLITE_DELAY_SECONDS = 1.5

#: A 5xx is retried; **a 4xx is not**, because a 404 is a statement about the
#: path and retrying it only repeats the question.
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0


class ServerUnavailable(Exception):
    """A 5xx that survived every retry, so bisection rather than failure.

    **This is a deterministic server-side fault on particular date boundaries,
    not throttling**, and the difference decides the fix. Bisected 2026-08-11 on
    ``dolarrava/cl``:

    ===========================  ========
    range                        result
    ===========================  ========
    ``2025-08-01/2025-08-07``    fine
    ``2025-08-12/2025-08-13``    fine
    ``2025-08-14/2025-08-15``    fine
    ``2025-08-13/2025-08-14``    **500**
    any range containing it      **500**
    ===========================  ========

    ``dolarrava/mep`` fails identically; both are the same Rava backend.
    Throttling would answer 429, would not reproduce on exactly the same range,
    and would not let the two halves through while refusing their union.

    **So no fixed chunk size is safe**: any window wider than a day can straddle
    a poisoned boundary. ``fetch_range`` bisects on this exception instead,
    down to single days, and records any single day that still fails.
    """


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunk_halves() -> list[tuple[int, int, date, date]]:
    """Split the window into half-year chunks, clipped at both ends.

    Chunking is what makes the retrieval resumable, which this repository
    requires of anything that downloads: retrieved data is treated as
    non-regenerable, so an interruption must cost one chunk rather than a run.
    Half-years are the starting unit; ``fetch_range`` narrows further wherever
    the endpoint refuses a span.
    """
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
    """Fetch, retrying server errors and never retrying client errors.

    A 5xx is the server saying it failed; a 404 is the server answering the
    question. Retrying the second one only asks it again.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "monetary-topology"})
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            if attempt == RETRY_ATTEMPTS:
                raise ServerUnavailable(f"HTTP {exc.code} after "
                                        f"{RETRY_ATTEMPTS} attempts") from exc
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
    """Rename, never remove. Returns the new path so it can be reported."""
    spoiled = path.with_suffix(f"{path.suffix}.expired.{int(time.time())}")
    path.rename(spoiled)
    print(f"    {path.name}: {why} -> kept as {spoiled.name}")
    return spoiled


def chunk_status(
    path: Path, fields: tuple[str, ...]
) -> tuple[str, str, list[dict]]:
    """Classify a cached chunk as ``complete``, ``empty`` or ``bad``.

    There is no marker to look for: a truncated JSON array does not parse, so
    parsing **is** the completeness test. ``empty`` is a header with no rows,
    which is a real answer for a range that predates a series rather than a
    fault -- the distinction ``fetch_hmda.py`` had to learn about missing
    markers, in a different costume.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return "bad", f"does not parse: {exc}", []
    try:
        rows = parse_rows(payload, fields)
    except ValueError as exc:
        return "bad", f"schema: {exc}", []
    if not rows:
        return "empty", "header only, no rows in range", []
    return "complete", "", rows


def write_atomic(path: Path, data: bytes) -> None:
    """Write through a temporary file and rename.

    This makes truncation impossible rather than merely detectable: an
    interrupted run leaves the temporary file, and the chunk on disk is either
    the previous complete one or absent.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def summarise(rows: list[dict], fields: tuple[str, ...]) -> dict:
    """The per-chunk numbers the manifest carries, all derived one way."""
    daily = collapse_to_daily(rows, fields)
    dispersion = within_day_dispersion(rows, fields)
    ranges = [d["log_range"] for d in dispersion]
    return {
        "rows": len(rows),
        "dates": len(daily),
        "collapsed_rows": len(rows) - len(daily),
        "dates_with_multiple_rows": len(dispersion),
        "within_day_log_range_max": round(max(ranges), 6) if ranges else 0.0,
        "first_date": daily[0]["date"] if daily else None,
        "last_date": daily[-1]["date"] if daily else None,
        "within_day_dispersion": dispersion,
        "anomalies": scan_anomalies(rows, fields),
    }


def load_bisected(path: Path) -> set[tuple[str, str, str]]:
    """Ranges a previous run found the endpoint refuses, from the manifest.

    **This caches the shape of the failure, not the data.** Without it every run
    re-asks for the same poisoned spans, waits out three retries with backoff at
    each internal node of the bisection tree, and rediscovers a tree it already
    knew: about seventy seconds per run across the two ``dolarrava`` series.

    ``--force`` ignores this, so a run can always re-probe and find the endpoint
    fixed.
    """
    if not path.exists():
        return set()
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a damaged manifest is not fatal here
        return set()
    return {
        (c["series"], c["range"][0], c["range"][1])
        for c in m.get("chunks", [])
        if c.get("status") == "bisected" and "range" in c and "series" in c
    }


def bisect_range(
    key: str, path_fragment: str, fields: tuple[str, ...],
    start: date, end: date, name: str, force: bool,
    known_bad: set[tuple[str, str, str]], why: str,
) -> list[dict]:
    """Split one refused range in two and fetch each half.

    Emits a ``bisected`` record for the node itself so the next run can replay
    the split instead of rediscovering it. That record carries no data and no
    hash; it is a note about the endpoint.
    """
    middle = start + (end - start) // 2
    print(f"    {name}: {why}, bisecting at {middle}")
    left = f"ambito_{key}_{start.isoformat()}_{middle.isoformat()}.json"
    right_start = middle + timedelta(days=1)
    right = f"ambito_{key}_{right_start.isoformat()}_{end.isoformat()}.json"
    node = {
        "name": name, "series": key, "status": "bisected",
        "range": [start.isoformat(), end.isoformat()],
        "reason": why, "split_at": middle.isoformat(),
    }
    return (
        [node]
        + fetch_range(key, path_fragment, fields, start, middle, left, force,
                      known_bad)
        + fetch_range(key, path_fragment, fields, right_start, end, right,
                      force, known_bad)
    )


def fetch_range(
    key: str, path_fragment: str, fields: tuple[str, ...],
    start: date, end: date, name: str, force: bool,
    known_bad: set[tuple[str, str, str]] | None = None,
) -> list[dict]:
    """Retrieve one date range, bisecting around the endpoint's bad boundaries.

    Returns **a list** of records, one per file written, because a range that
    hits a poisoned boundary comes back as two or more narrower files rather
    than as one. Each file still holds exactly one response, verbatim; nothing
    is stitched together on disk.

    The bisection floor is a single day. A day that still fails is recorded as
    ``unretrievable`` and **left absent** -- there is no substitute for it that
    would not be an invention.
    """
    known_bad = known_bad or set()
    out = RAW / name
    url = BASE.format(
        path=path_fragment, start=start.isoformat(), end=end.isoformat()
    )
    record: dict = {
        "name": name, "series": key, "url": url,
        "range": [start.isoformat(), end.isoformat()],
    }

    if (
        (key, start.isoformat(), end.isoformat()) in known_bad
        and not force
        and start < end
    ):
        return bisect_range(
            key, path_fragment, fields, start, end, name, force, known_bad,
            "known bad range from the manifest, not re-asked",
        )

    if out.exists() and not force:
        status, why, rows = chunk_status(out, fields)
        if status in ("complete", "empty"):
            stored = out.read_bytes()
            note = f"{len(rows):,} rows" if rows else "no rows in range"
            print(f"    {name}: cached, {note}")
            return [{
                **record, "status": f"cached-{status}",
                "sha256_stored": sha256(stored), **summarise(rows, fields),
            }]
        retire(out, why)

    try:
        raw = download(url)
    except ServerUnavailable as exc:
        if start >= end:
            print(f"    {name}: UNRETRIEVABLE {exc}", file=sys.stderr)
            return [{**record, "status": "unretrievable", "error": str(exc)}]
        return bisect_range(
            key, path_fragment, fields, start, end, name, force, known_bad,
            str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"    {name}: FAILED {exc}", file=sys.stderr)
        return [{**record, "status": "error", "error": str(exc)}]

    source_digest = sha256(raw)
    try:
        rows = parse_rows(json.loads(raw.decode("utf-8")), fields)
    except Exception as exc:  # noqa: BLE001
        # **Not written.** A response that does not parse is not archived as if
        # it were data; the error is reported and the chunk stays absent so the
        # next run retries it.
        print(f"    {name}: FAILED to parse: {exc}", file=sys.stderr)
        return [{**record, "status": "error", "error": f"parse: {exc}"}]

    # **Verbatim.** The bytes that arrived are the bytes stored, snapshots and
    # all. The collapse to one row per date is a measurement decision and lives
    # downstream of the archive, never inside it.
    write_atomic(out, raw)
    summary = summarise(rows, fields)
    bits = [f"{summary['rows']:,} rows"]
    if summary["collapsed_rows"]:
        bits.append(f"{summary['dates']} dates")
    if summary["anomalies"]:
        bits.append(f"{len(summary['anomalies'])} flagged")
    tail = f", {summary['first_date']} to {summary['last_date']}" if rows else ""
    print(f"    {name}: {', '.join(bits)}{tail}")
    return [{
        **record,
        "status": "downloaded" if rows else "empty",
        "bytes": len(raw),
        # **Two hashes, and they answer different questions.** Equal here because
        # nothing is appended, and both recorded anyway: ``fetch_cip.py``
        # compared a source hash against a file carrying a sentinel the source
        # did not have, and warned on every single run.
        "sha256_source": source_digest,
        "sha256_stored": sha256(out.read_bytes()),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **summary,
    }]


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

    seen = bad = mismatched = superseded = skipped = 0
    for path in sorted(RAW.glob("ambito_*.json")):
        if path.name == MANIFEST.name:
            continue
        match = VALID_NAME.match(path.name)
        if not match:
            # Reported, not removed. This is the whole point of ``VALID_NAME``.
            print(f"  {path.name}: not a recognised chunk name, left in place")
            skipped += 1
            continue
        if is_superseded(path.name):
            # The first run's whole-year chunking. Kept, never deleted, and not
            # counted as a fault: it is superseded, which is a different thing.
            print(f"  {path.name}: superseded whole-year chunk, left in place")
            superseded += 1
            continue
        key = match.group("series")
        _, fields = ALL_AMBITO[key]
        status, why, rows = chunk_status(path, fields)
        digest = sha256(path.read_bytes())
        if path.name not in recorded:
            verdict = "not in the manifest"
        elif digest == recorded[path.name]:
            verdict = "matches the manifest"
        else:
            verdict = "DOES NOT MATCH THE MANIFEST"
            mismatched += 1
        if status == "complete":
            daily = collapse_to_daily(rows, fields)
            detail = f", {len(rows):,} rows over {len(daily)} dates"
        else:
            detail = f" -- {why}"
        print(f"  {path.name}: {status}{detail}, sha256 {digest[:12]}, {verdict}")
        seen += 1
        if status == "bad":
            bad += 1

    if not seen:
        print("  nothing cached under the current chunking")
    print(f"  {seen} chunks, {bad} bad, {mismatched} hash mismatches, "
          f"{superseded} superseded, {skipped} unrecognised, all left in place")
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
    print("Ambito peso-dollar quote series, for stage B5")
    print(f"  window {WINDOW_START} to {WINDOW_END}, "
          f"{len(ALL_AMBITO)} series, {len(spans)} chunks each\n")

    known_bad = load_bisected(MANIFEST) if not args.force else set()
    if known_bad:
        print(f"  {len(known_bad)} ranges the endpoint refused before are "
              f"split without re-asking; --force re-probes them\n")

    chunks: list[dict] = []
    for key, (fragment, fields) in ALL_AMBITO.items():
        print(f"  {key} ({fragment})")
        for year, half, start, end in spans:
            name = f"ambito_{key}_{year}H{half}.json"
            got = fetch_range(key, fragment, fields, start, end, name,
                              args.force, known_bad)
            chunks.extend(got)
            if any(c["status"] in ("downloaded", "empty") for c in got):
                time.sleep(POLITE_DELAY_SECONDS)
        print()

    anomalies = [
        {"series": c["series"], **a}
        for c in chunks for a in c.get("anomalies", [])
    ]

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
                "jump_threshold": JUMP_THRESHOLD,
                "collapse_rule": (
                    "The endpoint returns intraday snapshots, not a daily "
                    "series. Each date is collapsed to the single row whose "
                    "mid is that date's median mid, lower median on ties. A "
                    "whole row is selected rather than a per-field statistic, "
                    "so bid and ask stay paired from one published quote. "
                    "Registered in b5_orphan_prereg.md 3.5. The raw files keep "
                    "every snapshot; nothing is dropped on disk."
                ),
                "provenance": (
                    "Ambito Financiero is a newspaper. These four series are a "
                    "newspaper's quotes, a step down from every other source in "
                    "this project, and b5_orphan_prereg.md 9.4 states it in the "
                    "write-up rather than in a footnote. The oficial leg's "
                    "headline mid (BCRA Com. A 3500), the friction leg (Banco "
                    "de la Nacion counter rates) and the P2P leg are not "
                    "retrieved here: their endpoints were not verified by the "
                    "availability check."
                ),
                "anomaly_policy": (
                    "Flagged dates are recorded and left unchanged. No value is "
                    "substituted and no row is dropped. Criterion B5-10 "
                    "computes the headline with and without them and reports "
                    "both."
                ),
                "anomalies": anomalies,
                "chunks": chunks,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {MANIFEST.relative_to(ROOT)}")

    failed = [c for c in chunks if c.get("status") == "error"]
    gone = [c for c in chunks if c.get("status") == "unretrievable"]
    split = [c for c in chunks if c.get("status") == "bisected"]
    held = [c for c in chunks
            if c.get("status") not in ("error", "unretrievable", "bisected")]
    rows = sum(c.get("rows", 0) for c in held)
    dates = sum(c.get("dates", 0) for c in held)
    collapsed = sum(c.get("collapsed_rows", 0) for c in held)
    print(f"  {len(held)} chunks held, {rows:,} rows over {dates:,} dates "
          f"({collapsed:,} intraday snapshots collapsed), "
          f"{len(anomalies)} anomalies recorded, {len(failed)} failed")
    if split:
        print(f"  {len(split)} ranges the endpoint refuses, recorded so the "
              f"next run splits them without asking")
    if anomalies:
        print("  anomalies are recorded, not repaired; see B5-10")
    if gone:
        print(f"  {len(gone)} single days the endpoint will not serve, "
              f"recorded and left absent:")
        for c in gone:
            print(f"    {c['series']} {c['range'][0]}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
