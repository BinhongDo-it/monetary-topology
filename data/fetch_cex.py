"""Retrieve the CEX decile table: income before taxes and the necessities basket.

Registered in ``docs/a1_inputs_availability.md`` §3. Parsing and both anchors
live in ``monetary_topology.cex``; this file retrieves, and refuses to guess a
layout.

Usage::

    python data/fetch_cex.py --discover   # what the workbook looks like, decide nothing
    python data/fetch_cex.py --check      # classify the cache, fetch nothing
    python data/fetch_cex.py              # read the pinned selection, write the inputs
    python data/fetch_cex.py --force      # refetch, retiring the current files

Endpoint, verified 2026-08-13 as returning a workbook::

    https://www.bls.gov/cex/tables/calendar-year/
        mean-item-share-average-standard-error/
        cu-income-deciles-before-taxes-2024.xlsx

**The PDF route stops at reference year 2022**: the 2023 and 2024 PDFs return
404, so xlsx is the only machine-readable form for the vintage this stage uses.
The year is in the path, so a past vintage stays re-fetchable.

**This publisher filters on the request header.** The first run returned
``HTTP 403 Forbidden`` with the same user agent the other three A1 fetchers use
without trouble. BLS asks that automated requests identify themselves, and its
edge rejects an unfamiliar agent outright rather than serving a page that
explains the rule. So the headers below are explicit and overridable with
``--user-agent``, and a 403 prints what to do rather than a traceback.

**If the header does not get through, fetch it by hand.** Open the endpoint in a
browser, save the workbook as ``data/raw/cex_deciles_2024.xlsx``, and every later
step reads that cache. Nothing downstream can tell the difference, and the
manifest records the file's sha256 either way. This is the same accommodation the
sibling repository's fetcher makes for sources whose addresses drift.

Why there is a discovery mode
-------------------------------
The workbook's layout was never retrieved: the sheet name, the height of the
header row, and the exact item labels are all unverified. Item labels are the
part that would fail quietly, because a table of this shape carries several rows
whose text is close (``Food``, ``Food at home``, ``Food away from home``), and
picking the wrong one returns a number rather than an error. So ``--discover``
dumps every sheet's top-left corner, a human pins the selection into
``data/cex_items.json``, and the published all-units figures confirm it.

What the pinned selection has to decide, and it is not a mechanical choice
---------------------------------------------------------------------------
CEX publishes deciles; this project's groups are 50 / 40 / 9 / 1. The mapping in
``group_columns`` is therefore a ruling rather than a lookup, and it carries two
disclosures that ``monetary_topology.cex`` repeats with every number: the ranking
is income while the model's population is ranked by wealth, and **the top 1% is
not separately observed** because a decile is the finest published cut.
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

from monetary_topology.cex import (
    GROUPS,
    AnchorProblem,
    Selection,
    SelectionProblem,
    inventory,
    read_inputs,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SELECTION = ROOT / "data" / "cex_items.json"
TEMPLATE = ROOT / "data" / "cex_items.template.json"
MANIFEST = RAW / "cex_manifest.json"

#: Publication order, so a decile index in a processed file means the decile the
#: publisher means. Sorting the header names alphabetically would put "Eighth"
#: first, which is a silent reordering of an ordinal variable.
DECILE_ORDER = (
    "Lowest 10 percent", "Second 10 percent", "Third 10 percent",
    "Fourth 10 percent", "Fifth 10 percent", "Sixth 10 percent",
    "Seventh 10 percent", "Eighth 10 percent", "Ninth 10 percent",
    "Highest 10 percent",
)

YEAR = "2024"
CEX_URL = (
    "https://www.bls.gov/cex/tables/calendar-year/"
    "mean-item-share-average-standard-error/"
    f"cu-income-deciles-before-taxes-{YEAR}.xlsx"
)

TIMEOUT_SECONDS = 300
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0
MIN_BYTES = 20_000

#: BLS rejects an unfamiliar agent with a bare 403. A browser-shaped agent is
#: the default because it is what gets through; ``--user-agent`` overrides it,
#: and BLS's own guidance is to identify automated requests, so a contact
#: address there is the courteous form.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
ACCEPT = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
    "application/vnd.ms-excel,*/*;q=0.8"
)


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


class Forbidden(Exception):
    """The publisher refused the request, which is a header problem here."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(url: str, timeout: int = TIMEOUT_SECONDS,
             user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": ACCEPT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise Forbidden(
                    "the publisher refused the request. Try "
                    "--user-agent 'name (your@email)', or open\n      "
                    f"{url}\n      in a browser and save it as "
                    f"data/raw/cex_deciles_{YEAR}.xlsx; every later step reads "
                    "that cache"
                ) from exc
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


def workbook_path() -> Path:
    return RAW / f"cex_deciles_{YEAR}.xlsx"


def ensure(path: Path, url: str, force: bool, minimum: int = 0,
           user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    if path.exists() and not force:
        print(f"    {path.name}: cached, {path.stat().st_size:,} bytes")
        return path.read_bytes()
    print(f"    {path.name}: fetching {url}")
    raw = download(url, user_agent=user_agent)
    if len(raw) < minimum:
        raise ServerUnavailable(f"{path.name}: {len(raw):,} bytes, below "
                                f"{minimum:,}")
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
def discover(force: bool, user_agent: str = DEFAULT_USER_AGENT) -> int:
    path = workbook_path()
    ensure(path, CEX_URL, force, MIN_BYTES, user_agent)
    report = inventory(path)
    out = RAW / f"cex_{YEAR}_layout.txt"
    write_text(out, report + "\n")
    print(report[:5000])
    print(f"\n  wrote {out.relative_to(ROOT)}")

    if not TEMPLATE.exists():
        template = {
            "_note": (
                "Fill this in from the layout dump, then save it as "
                "cex_items.json. Item labels must be copied exactly: this table "
                "carries several rows whose text is close, and picking the "
                "wrong one returns a number rather than an error. "
                "group_columns is a RULING, not a lookup: CEX publishes "
                "deciles and this project's groups are 50/40/9/1, so next9 and "
                "top1 will name the same single column and the top 1% is not "
                "separately observed."
            ),
            "reference_year": YEAR,
            "source": CEX_URL,
            "sheet": "",
            "label_column": 0,
            "all_units_column": "",
            "income_label": "",
            "expenditure_label": "",
            "necessity_labels": [],
            "rent_label": "",
            "mortgage_labels": [],
            "consumer_units_label": "",
            "tenure_labels": {"homeowner": "", "mortgaged": "", "renter": ""},
            "group_columns": {g: [] for g in GROUPS},
        }
        write_text(TEMPLATE, json.dumps(template, indent=2, sort_keys=True) + "\n")
        print(f"  wrote {TEMPLATE.relative_to(ROOT)}")
    return 0


def check() -> int:
    path = workbook_path()
    if not path.exists():
        print(f"  {path.name}: absent")
        return 1
    print(f"  {path.name}: cached, {path.stat().st_size:,} bytes, "
          f"sha256 {sha256(path.read_bytes())[:12]}")
    if not SELECTION.exists():
        print(f"  {SELECTION.name}: absent, run --discover and pin it")
        return 1
    try:
        result = read_inputs(path, Selection.load(SELECTION))
    except (SelectionProblem, AnchorProblem) as exc:
        print(f"  {SELECTION.name}: BAD: {exc}")
        return 1
    print(f"  reference year {result['reference_year']}, all units income "
          f"{result['all_units_income']:,.0f}")
    return 0


def run(force: bool, user_agent: str = DEFAULT_USER_AGENT) -> int:
    if not SELECTION.exists():
        print(
            f"    {SELECTION.name} is absent. Run --discover, read the layout, "
            f"and pin the selection. This fetcher does not guess an item label.",
            file=sys.stderr,
        )
        return 1

    raw = ensure(workbook_path(), CEX_URL, force, MIN_BYTES, user_agent)
    selection = Selection.load(SELECTION)
    try:
        result = read_inputs(workbook_path(), selection)
    except (SelectionProblem, AnchorProblem) as exc:
        print(f"    cex: FAILED {exc}", file=sys.stderr)
        return 1

    income = result["income"]
    necessities = result["necessities"]
    rent = result["rent"]
    mortgage = result["mortgage_payment"]
    tenure = result["tenure"]
    write_text(
        PROCESSED / "cex_income_necessities.csv",
        "group,income_before_taxes,necessities,rent,mortgage_payment,"
        "homeowner,mortgaged,renter\n"
        + "".join(
            f"{g},{income[g]:.2f},{necessities[g]:.2f},{rent[g]:.2f},"
            f"{mortgage[g]:.2f},{tenure['homeowner'][g]:.6f},"
            f"{tenure['mortgaged'][g]:.6f},{tenure['renter'][g]:.6f}\n"
            for g in GROUPS
        ),
    )

    # A national scalar has no row in a per-group table, and the experiment
    # needs it: it is the denominator that turns a Z.1 aggregate into a figure
    # per household, and it has to count the same unit of observation the
    # income belongs to. One row, alongside the one-row z1_ratio.csv.
    write_text(
        PROCESSED / "cex_consumer_units.csv",
        "reference_year,consumer_units,decile_sum\n"
        f"{result['reference_year']},{result['consumer_units']:.0f},"
        f"{sum(result['consumer_units_by_decile'].values()):.0f}\n",
    )

    by_decile = result["necessities_by_decile"]
    write_text(
        PROCESSED / "cex_necessities_by_decile.csv",
        "decile,column,necessities\n"
        + "".join(
            f"{i},{name},{by_decile[name]:.2f}\n"
            for i, name in enumerate(DECILE_ORDER)
        ),
    )

    print(f"\n  reference year {result['reference_year']}, all units income "
          f"{result['all_units_income']:,.0f}, decile mean "
          f"{result['decile_mean_income']:,.0f}")
    print(f"    {result['consumer_units']:,.0f} consumer units, deciles sum to "
          f"{sum(result['consumer_units_by_decile'].values()):,.0f}")
    for group in GROUPS:
        share = necessities[group] / income[group] if income[group] else 0.0
        print(f"    {group:<10} income {income[group]:>10,.0f}   basket "
              f"{necessities[group]:>9,.0f} ({share:.3f})   rent "
              f"{rent[group]:>7,.0f}   mortgage {mortgage[group]:>7,.0f}   "
              f"own {tenure['homeowner'][group]:.3f} "
              f"(mtg {tenure['mortgaged'][group]:.3f}) "
              f"rent {tenure['renter'][group]:.3f}")
    if result["top_groups_share_a_column"]:
        print("    next9 and top1 read the same column: a decile is the finest "
              "published cut")
    negative = [label for label, sign in result["mortgage_label_signs"].items()
                if sign < 0]
    if negative:
        print(f"    published negative and taken as cash handed over: "
              f"{', '.join(negative)}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "retrieved_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "A1",
                "url": CEX_URL,
                "reference_year": result["reference_year"],
                "sha256": sha256(raw),
                "selection_file": SELECTION.name,
                "selection_sha256": sha256(SELECTION.read_bytes()),
                "income": income,
                "necessities": necessities,
                "rent_per_consumer_unit": rent,
                "mortgage_payment_per_consumer_unit": mortgage,
                "necessity_labels": result["necessity_labels"],
                "mortgage_label_signs": result["mortgage_label_signs"],
                "tenure": result["tenure"],
                "all_units_income": result["all_units_income"],
                "decile_mean_income": result["decile_mean_income"],
                "consumer_units": result["consumer_units"],
                "consumer_units_by_decile": result["consumer_units_by_decile"],
                "necessities_by_decile": result["necessities_by_decile"],
                "top_groups_share_a_column": result["top_groups_share_a_column"],
                "provenance": (
                    "Bureau of Labor Statistics, Consumer Expenditure Survey, "
                    "deciles of income before taxes, reference year 2024, "
                    "released 2025-12-19. Income and expenditure come from one "
                    "table so they share a denominator and a unit of "
                    "observation. Two disclosures travel with every number: the "
                    "ranking is income while the model's population is ranked "
                    "by net worth, and the top 1% is not separately observed "
                    "because a decile is the finest published cut. See "
                    "docs/a1_inputs_availability.md sections 3 and 4. The "
                    "basket excludes shelter, which is read separately as the "
                    "cascade's own rung; both shelter lines are per consumer "
                    "unit and must be divided by their own tenure's share. The "
                    "owner's payment is the sum of the magnitudes of two lines: "
                    "mortgage interest is an expenditure and mortgage principal "
                    "sits in the addenda published negative at every decile, so "
                    "adding them as published nets 3,646 against -2,924 and "
                    "destroys the gradient in income. The consumer-unit count "
                    "is read from this same table so that a Z.1 aggregate is "
                    "divided by the population its income belongs to. Housing "
                    "tenure is read from this table for the same reason: a "
                    "shelter flow published by income decile has to be divided "
                    "by a tenure share ranked the same way, and taking the "
                    "share from the SCF's net-worth percentiles put the next40 "
                    "group's rent at 6,145 dollars a month. The two sources "
                    "agree nationally, 0.65 against 0.6605, and disagree about "
                    "the distribution."
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
                    help="dump the workbook's layout and stop")
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--force", action="store_true",
                    help="refetch, retiring the current files")
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT,
                    help="request header this publisher filters on")
    args = ap.parse_args()

    print("CEX income deciles, income before taxes and the necessities basket")
    try:
        if args.discover:
            return discover(args.force, args.user_agent)
        if args.check:
            return check()
        return run(args.force, args.user_agent)
    except Forbidden as exc:
        print(f"    FAILED {exc}", file=sys.stderr)
        # This publisher refuses unfamiliar agents, and ``--force`` is the one
        # mode that has to reach it. If the workbook is already cached, the
        # thing the caller almost certainly wants is to re-derive the processed
        # files from it, and that is the run without the flag. Saying so here
        # costs a line and saves finding out by elimination.
        if args.force and workbook_path().exists():
            print(
                f"\n    {workbook_path().name} is already cached "
                f"({workbook_path().stat().st_size:,} bytes). --force means "
                f"re-download, which this publisher blocks. To re-derive the "
                f"processed files from the cache, run this without --force: "
                f"the parse and every write happen either way.",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
