"""Retrieve the DFA group shares and the one Z.1 ratio stage A1 needs.

Registered in ``docs/a1_inputs_availability.md`` §1 and §5. Parsing and every
check live in ``monetary_topology.dfa``; this file retrieves, and refuses to
guess.

Usage::

    python data/fetch_dfa.py --discover    # what is in the archive, decide nothing
    python data/fetch_dfa.py --check       # classify the cache, fetch nothing
    python data/fetch_dfa.py               # read the pinned selection, write the inputs
    python data/fetch_dfa.py --force       # refetch, retiring the current files

Endpoints, verified 2026-08-13, all keyless::

    https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip
    https://fred.stlouisfed.org/graph/fredgraph.csv?id=HMLBSHNO
    https://fred.stlouisfed.org/graph/fredgraph.csv?id=CCLBSHNO

The FRED **API** needs a key; the graph CSV route above does not.

Why there is a discovery mode
-------------------------------
Seven of the eight DFA series this stage needs are **unverified**, and their
identifiers follow a stride regular enough to guess wrongly with confidence
(net worth runs ``...T01134`` / ``...N09161`` / ``...N40188`` / ``...B50215``).
A guess that lands on a real series with the wrong meaning produces a number
rather than an error. So ``--discover`` downloads the archive, writes an
inventory of every member and column, and stops. A human reads it once, pins the
selection into ``data/dfa_series.json``, and every later run reads that file.
**No series identifier appears anywhere in this repository's source.**

Two traps recorded before retrieval
-------------------------------------
**Z.1 was restructured on 2026-06-11.** ``B.101`` and ``L.101`` no longer exist;
the tables are ``S1M.b`` and ``S1M.s`` and the old addresses return 404. This
fetcher does not read those pages, and the note is here because the next fetcher
might.

**The seasonally adjusted twins carry the same titles.** ``HHMSDODNS`` and
``HCCSDODNS`` are the adjusted forms of the two series pinned here and differ in
value. The anchor check in ``dfa.mortgage_to_consumer_credit`` is what catches a
swap.
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

from monetary_topology.dfa import (
    GROUPS,
    INSTRUMENTS,
    AnchorProblem,
    Selection,
    SelectionProblem,
    ShareSumProblem,
    format_inventory,
    inventory,
    mortgage_to_consumer_credit,
    read_fred_csv,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SELECTION = ROOT / "data" / "dfa_series.json"
TEMPLATE = ROOT / "data" / "dfa_series.template.json"
MANIFEST = RAW / "dfa_manifest.json"

DFA_URL = (
    "https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip"
)
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
Z1_SERIES = {
    "home_mortgages": "HMLBSHNO",
    "consumer_credit": "CCLBSHNO",
}
#: The quarter A1's targets were written against. FRED dates a quarter by its
#: first day.
Z1_DATE = "2026-01-01"

TIMEOUT_SECONDS = 300
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0
MIN_ARCHIVE_BYTES = 100_000


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(url: str, timeout: int = TIMEOUT_SECONDS) -> bytes:
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    if path.exists():
        retire(path, "replaced")
    tmp.rename(path)


def archive_path() -> Path:
    return RAW / "dfa.zip"


def fred_path(name: str) -> Path:
    return RAW / f"z1_{name}.csv"


def ensure(path: Path, url: str, force: bool, minimum: int = 0) -> bytes:
    """Fetch unless cached. A cached file is returned rather than re-requested."""
    if path.exists() and not force:
        print(f"    {path.name}: cached, {path.stat().st_size:,} bytes")
        return path.read_bytes()
    print(f"    {path.name}: fetching {url}")
    raw = download(url)
    if len(raw) < minimum:
        raise ServerUnavailable(
            f"{path.name}: {len(raw):,} bytes, below {minimum:,}"
        )
    RAW.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(raw)
    if path.exists():
        retire(path, "replaced under --force")
    tmp.rename(path)
    return raw


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
def discover(force: bool) -> int:
    """Say what is in the archive. Decide nothing, write no input."""
    path = archive_path()
    ensure(path, DFA_URL, force, MIN_ARCHIVE_BYTES)
    members = inventory(path)
    report = format_inventory(members)
    out = RAW / "dfa_inventory.txt"
    write_text(out, report + "\n")
    print(report)
    print(f"  wrote {out.relative_to(ROOT)}")

    if not TEMPLATE.exists():
        template = {
            "_note": (
                "Fill this in from data/raw/dfa_inventory.txt, then save it as "
                "dfa_series.json. Every name must appear in the inventory. A "
                "group maps to a LIST of published categories because the "
                "publisher splits the top 1% in two; reading one of them alone "
                "silently drops nine tenths of the group. Nothing in this "
                "repository's source names a DFA category or column, and this "
                "file is the one place a selection is recorded."
            ),
            "vintage": "",
            "source": DFA_URL,
            "date": "",
            "member": "",
            "date_column": "",
            "category_column": "",
            "groups": {g: [] for g in GROUPS},
            "value_column": dict.fromkeys(INSTRUMENTS, ""),
        }
        write_text(TEMPLATE, json.dumps(template, indent=2, sort_keys=True) + "\n")
        print(f"  wrote {TEMPLATE.relative_to(ROOT)}")
    return 0


def check() -> int:
    """Classify what is cached and whether the pinned selection still reads."""
    status = 0
    for path in (archive_path(), *[fred_path(n) for n in Z1_SERIES]):
        if path.exists():
            print(f"  {path.name}: cached, {path.stat().st_size:,} bytes, "
                  f"sha256 {sha256(path.read_bytes())[:12]}")
        else:
            print(f"  {path.name}: absent")
            status = 1
    if not SELECTION.exists():
        print(f"  {SELECTION.name}: absent, run --discover and pin it")
        return 1
    try:
        selection = Selection.load(SELECTION)
        shares = validate(archive_path(), selection, selection.date)
    except (SelectionProblem, ShareSumProblem, AnchorProblem, KeyError) as exc:
        print(f"  {SELECTION.name}: BAD: {exc}")
        return 1
    for instrument, vector in sorted(shares.items()):
        print(f"  {instrument:<16} " + "  ".join(f"{v:.4f}" for v in vector))
    return status


def run(force: bool) -> int:
    if not SELECTION.exists():
        print(
            f"    {SELECTION.name} is absent. Run --discover, read "
            f"data/raw/dfa_inventory.txt, and pin the selection. This fetcher "
            f"does not guess a column.",
            file=sys.stderr,
        )
        return 1

    raw_archive = ensure(archive_path(), DFA_URL, force, MIN_ARCHIVE_BYTES)
    selection = Selection.load(SELECTION)
    date = selection.date

    try:
        shares = validate(archive_path(), selection, date)
    except (SelectionProblem, ShareSumProblem, AnchorProblem) as exc:
        print(f"    dfa.zip: FAILED {exc}", file=sys.stderr)
        return 1

    z1: dict[str, dict[str, float]] = {}
    for name, series in sorted(Z1_SERIES.items()):
        payload = ensure(fred_path(name), FRED_CSV.format(series=series), force)
        z1[name] = read_fred_csv(payload.decode("utf-8-sig", errors="replace"))
    try:
        ratio = mortgage_to_consumer_credit(
            z1["home_mortgages"], z1["consumer_credit"], Z1_DATE
        )
    except AnchorProblem as exc:
        print(f"    z1: FAILED {exc}", file=sys.stderr)
        return 1

    lines = ["instrument," + ",".join(GROUPS)]
    for instrument in INSTRUMENTS:
        vector = shares[instrument]
        lines.append(instrument + "," + ",".join(f"{v:.6f}" for v in vector))
    write_text(PROCESSED / "dfa_shares.csv", "\n".join(lines) + "\n")

    hm = z1["home_mortgages"][Z1_DATE]
    cc = z1["consumer_credit"][Z1_DATE]
    write_text(
        PROCESSED / "z1_ratio.csv",
        "date,home_mortgages,consumer_credit,mortgage_to_consumer_credit\n"
        f"{Z1_DATE},{hm:.1f},{cc:.1f},{ratio:.6f}\n",
    )

    print(f"\n  dfa vintage {selection.vintage}, date {date}")
    for instrument in INSTRUMENTS:
        print(f"    {instrument:<16} "
              + "  ".join(f"{v:.4f}" for v in shares[instrument]))
    print(f"  z1 {Z1_DATE}: mortgages {hm:,.0f} / consumer credit {cc:,.0f} "
          f"= {ratio:.4f}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "retrieved_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "A1",
                "dfa_url": DFA_URL,
                "dfa_sha256": sha256(raw_archive),
                "dfa_vintage": selection.vintage,
                "dfa_date": date,
                "selection_file": SELECTION.name,
                "selection_sha256": sha256(SELECTION.read_bytes()),
                "shares": {k: list(v) for k, v in sorted(shares.items())},
                "z1_series": Z1_SERIES,
                "z1_date": Z1_DATE,
                "z1_home_mortgages": hm,
                "z1_consumer_credit": cc,
                "mortgage_to_consumer_credit": ratio,
                "provenance": (
                    "Distributional Financial Accounts, shares by wealth group, "
                    "read from the publisher's own archive under a selection "
                    "pinned in data/dfa_series.json rather than from a guessed "
                    "series identifier. The Z.1 ratio is one-to-four-family "
                    "residential mortgages over consumer credit, both not "
                    "seasonally adjusted, both named instruments: it replaced a "
                    "ratio built on total liabilities, of which 12.4% is "
                    "neither instrument. See docs/a1_inputs_availability.md."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true",
                    help="enumerate the archive and write an inventory, then stop")
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch, retiring the current files rather than "
                         "overwriting them")
    args = ap.parse_args()

    print("DFA group shares and the Z.1 aggregate ratio, stage A1's inputs")
    if args.discover:
        return discover(args.force)
    if args.check:
        return check()
    return run(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
