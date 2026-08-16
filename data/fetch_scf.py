"""Retrieve the SCF summary extract and compute homeownership by wealth group.

Registered in ``docs/a1_inputs_availability.md`` §2. Parsing, the cut and both
anchors live in ``monetary_topology.scf``; this file retrieves, and refuses to
assume a coding.

Usage::

    python data/fetch_scf.py --discover   # what the extract contains, decide nothing
    python data/fetch_scf.py --check      # classify the cache, fetch nothing
    python data/fetch_scf.py              # read the pinned selection, write the input
    python data/fetch_scf.py --force      # refetch, retiring the current files

Endpoint, **unverified** at the time of writing::

    https://www.federalreserve.gov/econres/files/scfp2022excel.zip

The Board's own file listing for the summary extract names ``scfp2022excel.zip``
alongside the SAS and Stata forms, and ``/econres/files/`` is the directory the
Bulletin macro is served from. The full address was not retrieved before this
file was written, so ``--discover`` is also the step that proves it: a 404 says
the address is wrong, and nothing downstream runs on a guess.

Why there is a discovery mode
-------------------------------
The ownership variable's coding was **never verified**. A variable taking ``1``
and ``2`` says nothing about which value owns, and an inverted reading produces a
complete, plausible set of four rates with the K shape upside down. So
``--discover`` prints the distinct values of every candidate column with their
frequencies, a human pins the selection into ``data/scf_variables.json``, and the
published 66.1% overall rate is what confirms it.
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

from monetary_topology.scf import (
    GROUPS,
    PUBLISHED_OWNERSHIP_2022,
    AnchorProblem,
    Selection,
    SelectionProblem,
    format_profile,
    homeownership_by_group,
    profile,
    read_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SELECTION = ROOT / "data" / "scf_variables.json"
TEMPLATE = ROOT / "data" / "scf_variables.template.json"
MANIFEST = RAW / "scf_manifest.json"

WAVE = "2022"
SCF_URL = f"https://www.federalreserve.gov/econres/files/scfp{WAVE}excel.zip"

TIMEOUT_SECONDS = 300
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0
MIN_ARCHIVE_BYTES = 200_000


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
    return RAW / f"scfp{WAVE}excel.zip"


def ensure(path: Path, url: str, force: bool, minimum: int = 0) -> bytes:
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
    """Say what the extract contains. Decide nothing, compute no rate."""
    path = archive_path()
    ensure(path, SCF_URL, force, MIN_ARCHIVE_BYTES)
    rows = read_rows(path)
    columns = profile(rows)
    report = format_profile(columns, list(rows[0]), len(rows))
    out = RAW / f"scf{WAVE}_profile.txt"
    write_text(out, report + "\n")
    print(report[:4000])
    print(f"\n  wrote {out.relative_to(ROOT)}")

    if not TEMPLATE.exists():
        template = {
            "_note": (
                "Fill this in from the profile, then save it as "
                "scf_variables.json. owning_values must list the values of the "
                "ownership column that mean owning a primary residence, read "
                "off the profile rather than assumed: an inverted coding "
                "produces four plausible rates with the K shape upside down, "
                f"and is caught only by the published {PUBLISHED_OWNERSHIP_2022} "
                "overall rate. weight_divisor is 1 when the file's weight is "
                "already split across the implicate rows, which is the case for "
                "this extract; the weight total is what checks it."
            ),
            "wave": WAVE,
            "source": SCF_URL,
            "member": "",
            "weight_column": "",
            "networth_column": "",
            "ownership_column": "",
            "owning_values": [],
            "weight_divisor": 1,
        }
        write_text(TEMPLATE, json.dumps(template, indent=2, sort_keys=True) + "\n")
        print(f"  wrote {TEMPLATE.relative_to(ROOT)}")
    return 0


def check() -> int:
    path = archive_path()
    if path.exists():
        print(f"  {path.name}: cached, {path.stat().st_size:,} bytes, "
              f"sha256 {sha256(path.read_bytes())[:12]}")
    else:
        print(f"  {path.name}: absent")
        return 1
    if not SELECTION.exists():
        print(f"  {SELECTION.name}: absent, run --discover and pin it")
        return 1
    try:
        selection = Selection.load(SELECTION)
        result = homeownership_by_group(read_rows(path, selection.member),
                                        selection)
    except (SelectionProblem, AnchorProblem) as exc:
        print(f"  {SELECTION.name}: BAD: {exc}")
        return 1
    print(f"  wave {result['wave']}, "
          f"{result['weighted_population']:,.0f} weighted families")
    print("  " + "  ".join(
        f"{g} {r:.4f}" for g, r in zip(GROUPS, result["rates"], strict=True)
    ))
    return 0


def run(force: bool) -> int:
    if not SELECTION.exists():
        print(
            f"    {SELECTION.name} is absent. Run --discover, read the profile, "
            f"and pin the selection. This fetcher does not assume a coding.",
            file=sys.stderr,
        )
        return 1

    raw = ensure(archive_path(), SCF_URL, force, MIN_ARCHIVE_BYTES)
    selection = Selection.load(SELECTION)
    try:
        rows = read_rows(archive_path(), selection.member)
        result = homeownership_by_group(rows, selection)
    except (SelectionProblem, AnchorProblem) as exc:
        print(f"    scf: FAILED {exc}", file=sys.stderr)
        return 1

    rates = result["rates"]
    write_text(
        PROCESSED / "scf_homeownership.csv",
        "group,homeownership_rate,population_share\n"
        + "".join(
            f"{g},{r:.6f},{s:.6f}\n"
            for g, r, s in zip(GROUPS, rates, result["population_shares"],
                               strict=True)
        ),
    )

    print(f"\n  wave {result['wave']}, {result['records']:,} rows, "
          f"{result['weighted_population']:,.0f} weighted families")
    print(f"  overall {result['overall']:.4f} against the published "
          f"{PUBLISHED_OWNERSHIP_2022:.3f}")
    for group, rate, share in zip(GROUPS, rates, result["population_shares"],
                                  strict=True):
        print(f"    {group:<10} ownership {rate:.4f}   population {share:.4f}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "retrieved_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "A1",
                "url": SCF_URL,
                "wave": selection.wave,
                "sha256": sha256(raw),
                "selection_file": SELECTION.name,
                "selection_sha256": sha256(SELECTION.read_bytes()),
                "weight_divisor": selection.weight_divisor,
                "weighted_families": result["weighted_population"],
                "overall_ownership": result["overall"],
                "published_overall_ownership": PUBLISHED_OWNERSHIP_2022,
                "rates": dict(zip(GROUPS, rates, strict=True)),
                "population_shares": dict(
                    zip(GROUPS, result["population_shares"], strict=True)
                ),
                "provenance": (
                    "Survey of Consumer Finances summary extract, wave 2022, "
                    "computed rather than published: no source gives "
                    "homeownership by net worth percentile. Households are "
                    "ranked by NETWORTH, weighted, and cut at the 50th, 90th "
                    "and 99th weighted percentiles. The five implicate rows "
                    "are pooled; this extract's WGT is already split across "
                    "them, so the divisor is one. Three anchors are checked "
                    "before any rate is written: the weights must sum to a "
                    "national family count, the four groups must weigh 0.50, "
                    "0.40, 0.09 and 0.01 of the population, and the overall "
                    "rate must reproduce the Bulletin's published 66.1%. This "
                    "input is a 2022 vintage while the rest of the stage is "
                    "2024 to 2026; see docs/a1_inputs_availability.md."
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
                    help="profile the extract and stop")
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch, retiring the current files")
    args = ap.parse_args()

    print("SCF summary extract, homeownership by wealth group, stage A1")
    if args.discover:
        return discover(args.force)
    if args.check:
        return check()
    return run(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
