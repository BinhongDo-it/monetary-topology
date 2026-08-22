"""B11 block A: does ROCR carry its own distressed-exchange marker.

Gate work on the free rating histories, done before the stage opens. Reads the
ROCR corporate files that ``data/fetch_rocr.py --pull Corporate`` leaves in
``data/raw/rocr/`` and answers three things that all have to be settled before
C11-0 is counted:

1. **Is there a machine-readable distressed-exchange marker inside the rating
   history itself.** The availability work assumed, when the gate was
   written, that the marker
   had to come from S&P's annual default study, a PDF, matched to the rating
   history by issuer name. The peek of 2026-08-17 showed Fitch publishing
   ``RD`` in the ``rating`` column and Moody's publishing probability-of-default
   ratings like ``Ba3-PD``, whose scale carries ``/LD`` and ``/D`` suffixes.
   **If the marker is already in the file, the PDF and the name matching both
   leave the critical path**, and the join becomes exact.

2. **C11-1 with an honest denominator.** The peek reported the fill rate of
   ``coupon_date`` / ``maturity_date`` / ``par_value`` over every row. Issuer
   level rows cannot carry contract terms, so that denominator understates the
   rate for the rows the contract present value is actually built from. This
   file reports the rate over the whole file and over instrument rows
   separately, and the second one is the number C11-1's 0.90 threshold is
   about.

3. **What the coupon column actually holds.** It is named ``coupon_date`` and
   the sampled values are ``7.25``. The ROCR element is ``CR``, a coupon rate,
   so the scraper's column name is wrong. **A rate read as a date is a silent
   failure**, so this file checks the values rather than the name and refuses
   to report a fill rate for that column without saying which it saw.

Usage::

    python data/fetch_rocr.py --pull Corporate --agency Moody --yes
    python experiments/b11_markers.py --agency Moody

    python experiments/b11_markers.py --agency Fitch     # the cross-check

What this file does not do
--------------------------
**It does not count loops.** C11-0 needs the investment-grade condition applied
along each issuer's rating path, and that is block B. This file establishes
which marker block B keys on. Splitting them means a wrong marker costs one
small script rather than the whole gate.

The record it writes carries ``diagnostic_only`` with a reason beside it: the
station is not closed, so none of the numbers here is one of its readings, and
the field says so on the record itself rather than somewhere a reader would
have to go looking. The evidence sits in ``results/`` and stays readable.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROCR = ROOT / "data" / "raw" / "rocr"
RESULTS = ROOT / "results"

#: Only files matching the publisher's naming convention are loaded. Same
#: device as ``experiments/b2_loop_a.py``: the loader ignores what it does not
#: recognise, so nothing ever has to be deleted to keep a directory clean.
VALID_NAME = re.compile(r"^(\d{8}) (.+) (Corporate|Financial|Insurance)\.csv$")

#: Asset classes that hold operating and financial companies. ``--asset-class
#: all`` takes the three together, which is the scope question B11 has to settle
#: before C11-0 is counted: a bank and an insurer are corporate credit, and
#: leaving them out is a choice about the domain rather than about the data.
CORPORATE_CLASSES = ("Corporate", "Financial", "Insurance")

#: The three windows are registered: fixed before any count was run, and not
#: touched since. The third one ran from 2022-01 to the present until
#: 2026-08-17, when the peek showed the newest Moody's snapshot on
#: ratingshistory.info is 2024-11-15 and its rating actions stop in 2023-12.
#: Truncated before any count, and the truncation is the registered form.
WINDOWS = (
    ("energy", "2015-01-01", "2016-12-31"),
    ("covid", "2020-01-01", "2021-12-31"),
    ("rates", "2022-01-01", "2023-12-31"),
)

#: 17g-7(b) coverage begins here. Anything earlier is a publisher going beyond
#: the rule, which Egan-Jones does; it is reported, never trimmed.
RULE_START = "2012-06-15"

CONTRACT_COLUMNS = ("coupon_date", "maturity_date", "par_value")

#: Two different questions, and the 2026-08-17 Moody's run showed they have
#: different answers, so they are counted apart.
#:
#: **Limited default** is the distressed-exchange-specific symbol. Moody's
#: writes it as a ``/LD`` suffix on the probability-of-default rating and Fitch
#: writes ``RD``. It is the counterpart of B8's modification: the contract is
#: signed again here, and coupon, par and maturity all move.
#:
#: **Default** is any failure to pay as promised: missed payment, bankruptcy,
#: distressed exchange, all of them. Moody's writes ``D-PD``, S&P writes ``D``.
#:
#: The Moody's corporate file carries the second and not the first: 224 distinct
#: symbols, **not one of them contains a slash**, while ``D-PD`` appears 351
#: times. So Moody's alone cannot tell a distressed exchange from a bankruptcy,
#: and the report prints both counts rather than one number that hides which
#: question got answered.
#: ``SD`` moved here from the general bucket on 2026-08-17. S&P's selective
#: default means the obligor defaulted on one obligation and kept paying the
#: rest, which is what a distressed exchange looks like on the scale; plain
#: ``D`` is the general case. **No file in hand uses ``SD``** (Fitch writes
#: ``RD``, Moody's writes ``D-PD``), so this changes no reading already taken,
#: and it is recorded before a file that would use it is read.
LIMITED_DEFAULT_SUFFIX = re.compile(r"/(LD|D)$")
LIMITED_DEFAULT_EXACT = frozenset({"RD", "SD"})
DEFAULT_EXACT = frozenset({"D", "DD", "DDD", "D-PD"})

#: ``(P)`` marks a provisional rating and ``.br`` / ``.mx`` / ``.za`` mark a
#: national scale. Neither changes which rung of the ladder the symbol is, so
#: both come off before the symbol is classified. Stripping them is why
#: ``(P)D-PD`` and ``D.br`` are not missed.
PROVISIONAL = re.compile(r"^\(P\)")
NATIONAL_SCALE = re.compile(r"\.[a-z]{2}$")

#: Instruments whose *name* says they have no fixed coupon. Kept as a reported
#: diagnostic, and it is weak: on Moody's corporate it matched **2** of 34,439
#: missing coupons, because the publisher's instrument names do not say
#: "floating". The load-bearing rule is the one below.
NO_FIXED_COUPON = re.compile(
    r"FLOAT|FLTG|\bFRN\b|VARIABLE RATE|ZERO COUPON|\bZCB\b|COMMERCIAL PAPER|\bCP\b|DISCOUNT NOTE",
    re.IGNORECASE,
)

#: A bank credit facility is a revolver or a term loan. It prices off a
#: reference rate plus a spread, so **there is no fixed coupon to report**, and
#: no data source of any price would supply one. Such an instrument was never in
#: the population ``V`` is defined on: the contract present value of
#: ``docs/b8_fannie_slice.md`` §3.1 needs a scheduled payment stream, and a
#: floating-rate loan has none until the reference rate is fixed.
#:
#: **This exclusion was written after the all-rows reading was seen** (0.7856 on
#: Moody's corporate, 2026-08-17), so R01 applies and the record reports both
#: denominators side by side, never one alone. It is a single rule stated by
#: mechanism rather than a list of terms picked for their effect: the six
#: credit-facility variants in the file account for 79.29% of every missing
#: coupon, and no further exclusion is taken once the threshold is met.
NO_FIXED_COUPON_TERM = re.compile(r"Bank Credit Facility", re.IGNORECASE)

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def pick_files(agency: str | None, classes: tuple[str, ...]) -> list[Path]:
    chosen = []
    for path in sorted(ROCR.glob("*.csv")):
        match = VALID_NAME.match(path.name)
        if not match:
            continue
        if match.group(3) not in classes:
            continue
        if agency and agency.lower() not in match.group(2).lower():
            continue
        chosen.append(path)
    return chosen


def output_slug(agency: str | None, classes: tuple[str, ...]) -> str:
    """One record per filter, so two runs cannot overwrite each other.

    The first version wrote a fixed ``b11_markers.json``, and the Fitch run
    silently replaced the Moody's one. A result file whose name does not carry
    what produced it is a result file that answers a question nobody can name
    afterwards.
    """
    who = re.sub(r"[^A-Za-z0-9]+", "", agency or "allagencies").lower()
    what = "".join(c[0] for c in classes).lower() if len(classes) > 1 else classes[0].lower()
    return f"b11_markers_{who}_{what}"


def obligor_key(row: dict) -> str:
    """One identity per rated entity, most specific identifier first.

    The composition is reported, because a key that falls back to the name for
    most rows is a different object from one grounded in an identifier, and
    C11-0's count is a count of these.
    """
    for column in ("obligor_identifier", "legal_entity_identifier", "issuer_identifier", "obligor_name", "issuer_name"):
        value = (row.get(column) or "").strip()
        if value:
            return f"{column}:{value}"
    return ""


def key_source(key: str) -> str:
    return key.split(":", 1)[0] if key else "(none)"


def window_of(date: str) -> str | None:
    for name, start, end in WINDOWS:
        if start <= date <= end:
            return name
    return None


def base_symbol(rating: str) -> str:
    value = PROVISIONAL.sub("", rating.strip()).strip('"')
    return NATIONAL_SCALE.sub("", value)


def classify_rating(rating: str) -> str | None:
    """``"limited_default"``, ``"default"``, or ``None``.

    Limited default is checked first because ``Ca-PD/LD`` is both, and the
    distressed-exchange-specific reading is the one B11 registered.
    """
    value = rating.strip()
    if not value:
        return None
    base = base_symbol(value)
    if LIMITED_DEFAULT_SUFFIX.search(value) or base in LIMITED_DEFAULT_EXACT:
        return "limited_default"
    if base in DEFAULT_EXACT:
        return "default"
    return None


def scan(path: Path) -> dict:
    ratings: collections.Counter = collections.Counter()
    action_class: collections.Counter = collections.Counter()
    object_type: collections.Counter = collections.Counter()
    slash_ratings: collections.Counter = collections.Counter()
    pd_ratings: collections.Counter = collections.Counter()

    kinds = ("limited_default", "default")
    marker_rows = {k: 0 for k in kinds}
    marker_by_symbol = {k: collections.Counter() for k in kinds}
    marker_keys: dict[str, set[str]] = {k: set() for k in kinds}
    marker_key_sources = {k: collections.Counter() for k in kinds}
    marker_window = {k: collections.Counter() for k in kinds}
    marker_dates: dict[str, list[str]] = {k: [] for k in kinds}

    # C11-1's mechanism question: where does a missing coupon sit.
    term_rows: collections.Counter = collections.Counter()
    term_coupon: collections.Counter = collections.Counter()
    missing_coupon_no_fixed = 0
    missing_coupon_named = 0
    coupon_exact_zero = 0

    schema_counts = {
        column: collections.Counter()
        for column in ("issuer_identifier_schema", "obligor_identifier_schema", "instrument_identifier_schema")
    }
    id_fill = {column: 0 for column in ("legal_entity_identifier", "CUSIP_number", "central_index_key")}

    total = 0
    ragged = 0
    action_dates: list[str] = []

    fill_all = {c: 0 for c in CONTRACT_COLUMNS}
    fill_instrument = {c: 0 for c in CONTRACT_COLUMNS}
    fill_fixed = {c: 0 for c in CONTRACT_COLUMNS}
    instrument_rows = 0
    fixed_coupon_rows = 0

    coupon_numeric = 0
    coupon_datelike = 0
    coupon_other = 0
    coupon_values: list[float] = []

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            total += 1
            if row.get(None) is not None or any(v is None for v in row.values()):
                ragged += 1
            rating = (row.get("rating") or "").strip()
            ratings[rating] += 1
            if "/" in rating:
                slash_ratings[rating] += 1
            if "-PD" in rating:
                pd_ratings[rating] += 1
            action_class[(row.get("rating_action_class") or "").strip()] += 1
            otype = (row.get("object_type_rated") or "").strip()
            object_type[otype] += 1

            date = (row.get("rating_action_date") or "").strip()
            if ISO_DATE.match(date):
                action_dates.append(date)

            for column in CONTRACT_COLUMNS:
                if (row.get(column) or "").strip():
                    fill_all[column] += 1
            coupon = (row.get("coupon_date") or "").strip()

            if otype == "Instrument":
                instrument_rows += 1
                for column in CONTRACT_COLUMNS:
                    if (row.get(column) or "").strip():
                        fill_instrument[column] += 1
                term = (row.get("rating_type_term") or "").strip() or "(blank)"
                term_rows[term] += 1
                if not NO_FIXED_COUPON_TERM.search(term):
                    fixed_coupon_rows += 1
                    for column in CONTRACT_COLUMNS:
                        if (row.get(column) or "").strip():
                            fill_fixed[column] += 1
                if coupon:
                    term_coupon[term] += 1
                else:
                    name = (row.get("instrument_name") or "").strip()
                    if name:
                        missing_coupon_named += 1
                        if NO_FIXED_COUPON.search(name):
                            missing_coupon_no_fixed += 1

            for column, counter in schema_counts.items():
                counter[(row.get(column) or "").strip() or "(blank)"] += 1
            for column in id_fill:
                if (row.get(column) or "").strip():
                    id_fill[column] += 1

            if coupon:
                if ISO_DATE.match(coupon):
                    coupon_datelike += 1
                else:
                    try:
                        parsed = float(coupon)
                    except ValueError:
                        coupon_other += 1
                    else:
                        coupon_numeric += 1
                        if parsed == 0.0:
                            coupon_exact_zero += 1
                        if len(coupon_values) < 400_000:
                            coupon_values.append(parsed)

            kind = classify_rating(rating)
            if kind:
                marker_rows[kind] += 1
                marker_by_symbol[kind][rating] += 1
                key = obligor_key(row)
                if key:
                    marker_keys[kind].add(key)
                    marker_key_sources[kind][key_source(key)] += 1
                if ISO_DATE.match(date):
                    marker_dates[kind].append(date)
                    bucket = window_of(date)
                    marker_window[kind][bucket or "outside"] += 1

    coupon_values.sort()
    action_dates.sort()
    for values in marker_dates.values():
        values.sort()

    def rate(hit: int, denominator: int) -> float:
        return round(hit / denominator, 4) if denominator else 0.0

    # Instrument-row terms ranked by how many coupons they are missing. This is
    # the table that says whether C11-1's shortfall is one class of instrument
    # or a flat gap across the file, and the two call for different rulings.
    coupon_by_term = sorted(
        (
            {
                "term": term,
                "instrument_rows": term_rows[term],
                "coupon_present": term_coupon[term],
                "fill": rate(term_coupon[term], term_rows[term]),
                "missing": term_rows[term] - term_coupon[term],
            }
            for term in term_rows
        ),
        key=lambda d: (-d["missing"], d["term"]),
    )
    missing_total = sum(d["missing"] for d in coupon_by_term)

    markers = {
        kind: {
            "rows": marker_rows[kind],
            "symbols": dict(marker_by_symbol[kind].most_common()),
            "distinct_obligors": len(marker_keys[kind]),
            "key_sources": dict(marker_key_sources[kind].most_common()),
            "date_span": [marker_dates[kind][0], marker_dates[kind][-1]] if marker_dates[kind] else None,
            "per_window": dict(sorted(marker_window[kind].items())),
            # Kept so a multi-file run can take the union rather than the sum.
            # Sorted, because the record has to be a pure function of the input.
            "obligor_keys": sorted(marker_keys[kind]),
        }
        for kind in kinds
    }

    return {
        "file": path.name,
        "fieldnames": fieldnames,
        "rows": total,
        "ragged_rows": ragged,
        "action_date_span": [action_dates[0], action_dates[-1]] if action_dates else None,
        "actions_before_rule_start": sum(1 for d in action_dates if d < RULE_START),
        "distinct_ratings": len(ratings),
        "rating_counts": dict(ratings.most_common()),
        "rating_action_class_counts": dict(action_class.most_common()),
        "object_type_counts": dict(object_type.most_common()),
        "ratings_containing_slash": dict(slash_ratings.most_common()),
        "ratings_containing_PD": dict(pd_ratings.most_common(40)),
        "instrument_rows": instrument_rows,
        "fixed_coupon_rows": fixed_coupon_rows,
        "contract_fill_all_rows": {c: rate(fill_all[c], total) for c in CONTRACT_COLUMNS},
        "contract_fill_instrument_rows": {c: rate(fill_instrument[c], instrument_rows) for c in CONTRACT_COLUMNS},
        "contract_fill_fixed_coupon_rows": {c: rate(fill_fixed[c], fixed_coupon_rows) for c in CONTRACT_COLUMNS},
        "credit_facility_share_of_missing_coupons": rate(
            sum(term_rows[t] - term_coupon[t] for t in term_rows if NO_FIXED_COUPON_TERM.search(t)),
            sum(term_rows[t] - term_coupon[t] for t in term_rows),
        ),
        "coupon_column_numeric": coupon_numeric,
        "coupon_column_datelike": coupon_datelike,
        "coupon_column_unparsed": coupon_other,
        "coupon_exact_zero": coupon_exact_zero,
        "coupon_quantiles": (
            [round(coupon_values[int(q * (len(coupon_values) - 1))], 4) for q in (0.0, 0.25, 0.5, 0.75, 1.0)]
            if coupon_values
            else None
        ),
        "coupon_by_term": coupon_by_term[:25],
        "coupon_missing_instrument_rows": missing_total,
        "coupon_missing_with_a_name": missing_coupon_named,
        "coupon_missing_named_no_fixed_coupon": missing_coupon_no_fixed,
        "identifier_schemas": {k: dict(v.most_common(10)) for k, v in sorted(schema_counts.items())},
        "identifier_fill": {k: rate(v, total) for k, v in sorted(id_fill.items())},
        "markers": markers,
    }


def report(summary: dict) -> None:
    print("=" * 78)
    print(summary["file"])
    print(f"  rows {summary['rows']:,}   ragged {summary['ragged_rows']:,}   "
          f"instrument rows {summary['instrument_rows']:,}")
    span = summary["action_date_span"]
    print(f"  rating_action_date span : {span[0]} .. {span[1]}" if span else "  no parsable action dates")
    if summary["actions_before_rule_start"]:
        print(f"  actions before {RULE_START} : {summary['actions_before_rule_start']:,} "
              "(publisher going beyond 17g-7(b), reported not trimmed)")
    print()

    print("  -- what the coupon column holds --")
    print(f"    numeric {summary['coupon_column_numeric']:,}   "
          f"date-like {summary['coupon_column_datelike']:,}   "
          f"unparsed {summary['coupon_column_unparsed']:,}")
    if summary["coupon_quantiles"]:
        print(f"    numeric quantiles (min q25 med q75 max): {summary['coupon_quantiles']}")
        print(f"    exactly zero: {summary['coupon_exact_zero']:,}")
        print("    Values in that range are coupon RATES. The column name says date and it lies.")
    print()

    print("  -- C11-1, threshold 0.90, BOTH denominators (R01) --")
    print(f"    instrument rows {summary['instrument_rows']:,}   "
          f"of which not a credit facility {summary['fixed_coupon_rows']:,}")
    for column in CONTRACT_COLUMNS:
        every = summary["contract_fill_all_rows"][column]
        inst = summary["contract_fill_instrument_rows"][column]
        fixed = summary["contract_fill_fixed_coupon_rows"][column]
        print(f"    {column:<14s} all {every:.4f} | instrument {inst:.4f} "
              f"{'PASS' if inst >= 0.90 else 'FAIL'} | fixed-coupon {fixed:.4f} "
              f"{'PASS' if fixed >= 0.90 else 'FAIL'}")
    print(f"    credit facilities are {summary['credit_facility_share_of_missing_coupons']:.4f} "
          "of every missing coupon")
    print("    The registered reading is the instrument-row one. The fixed-coupon")
    print("    column drops revolvers and term loans, which price off a reference")
    print("    rate and have no coupon for any source to report. Both are printed")
    print("    because the second denominator was written after the first was seen.")
    print()

    print("  -- where the missing coupons sit --")
    missing = summary["coupon_missing_instrument_rows"]
    named = summary["coupon_missing_with_a_name"]
    nofix = summary["coupon_missing_named_no_fixed_coupon"]
    print(f"    instrument rows missing a coupon : {missing:,}")
    print(f"      of which the instrument is named : {named:,}")
    print(f"      of which the name says it has no fixed coupon : {nofix:,}"
          + (f"  ({nofix / named:.4f} of named)" if named else ""))
    print("    A floating-rate note or a discount instrument has no fixed coupon")
    print("    by construction, so a blank there is the instrument's nature. The")
    print("    ruling on C11-1 turns on how much of the shortfall is that.")
    print("    top terms by missing coupons:")
    for entry in summary["coupon_by_term"][:8]:
        print(f"      {entry['term']!r:<34s} rows {entry['instrument_rows']:>7,}  "
              f"fill {entry['fill']:.4f}  missing {entry['missing']:>7,}")
    print()

    print("  -- the marker, two questions counted apart --")
    for kind, label in (("limited_default", "limited default (distressed exchange)"),
                        ("default", "default of any kind")):
        block = summary["markers"][kind]
        print(f"    {label}")
        print(f"      rows {block['rows']:,}   distinct obligors {block['distinct_obligors']:,}")
        if block["symbols"]:
            print(f"      symbols   : {block['symbols']}")
        if block["date_span"]:
            print(f"      date span : {block['date_span'][0]} .. {block['date_span'][1]}")
        if block["per_window"]:
            print(f"      per window: {block['per_window']}")
            print(f"      key source: {block['key_sources']}")
    if summary["ratings_containing_slash"]:
        print(f"    every rating containing '/' : {summary['ratings_containing_slash']}")
    else:
        print("    no rating symbol in this file contains '/', so no /LD is available here")
    if summary["ratings_containing_PD"]:
        print(f"    PD-suffixed ratings, first 12 : {list(summary['ratings_containing_PD'])[:12]}")
    print()

    print("  -- what a cross-agency join would key on --")
    print(f"    identifier fill : {summary['identifier_fill']}")
    for column, counts in summary["identifier_schemas"].items():
        print(f"    {column:<30s} {counts}")
    print()
    print(f"  rating_action_class : {summary['rating_action_class_counts']}")
    print(f"  object_type_rated   : {summary['object_type_counts']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--agency", help="substring filter on the agency name")
    parser.add_argument(
        "--asset-class",
        default="Corporate",
        help="one class, a comma-separated list, or 'all' for " + "+".join(CORPORATE_CLASSES),
    )
    args = parser.parse_args(argv)

    if args.asset_class.lower() == "all":
        classes = CORPORATE_CLASSES
    else:
        classes = tuple(c.strip() for c in args.asset_class.split(",") if c.strip())
    unknown = [c for c in classes if c not in CORPORATE_CLASSES]
    if unknown:
        print(f"Not corporate-credit asset classes: {unknown}. Known: {list(CORPORATE_CLASSES)}")
        return 2

    files = pick_files(args.agency, classes)
    if not files:
        print(f"No {'/'.join(classes)} files in {ROCR} for that filter.")
        print("Run: python data/fetch_rocr.py --pull Corporate --agency Moody --yes")
        return 2

    summaries = [scan(path) for path in files]
    for summary in summaries:
        report(summary)

    # Union, not sum. The same issuer can be rated in more than one class file,
    # and a sum would count it twice, which is the direction that flatters the
    # ceiling C11-0 has to clear.
    ld_keys: set[str] = set()
    d_keys: set[str] = set()
    for summary in summaries:
        ld_keys |= set(summary["markers"]["limited_default"]["obligor_keys"])
        d_keys |= set(summary["markers"]["default"]["obligor_keys"])
    ld_total, d_total = len(ld_keys), len(d_keys)
    if len(summaries) > 1:
        print("=" * 78)
        print(f"across {len(summaries)} file(s), deduplicated by obligor key:")
        print(f"  limited default : {ld_total:,} distinct obligors "
              f"(sum over files would be {sum(s['markers']['limited_default']['distinct_obligors'] for s in summaries):,})")
        print(f"  any default     : {d_total:,} distinct obligors")
    c11_1 = [
        (s["file"], min(s["contract_fill_instrument_rows"][c] for c in CONTRACT_COLUMNS))
        for s in summaries
    ]
    c11_1_fixed = [
        (s["file"], min(s["contract_fill_fixed_coupon_rows"][c] for c in CONTRACT_COLUMNS))
        for s in summaries
    ]

    RESULTS.mkdir(parents=True, exist_ok=True)
    record = {
        "stage": "B11-markers",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "C11-0 has not been counted. This record establishes which symbol block B "
            "keys on and reports C11-1 with the instrument-row denominator; none of "
            "the stage's registered predictions is evaluated here."
        ),
        "criteria": [
            {
                "name": "C11-1 as registered: contract terms on every instrument row",
                "passed": all(worst >= 0.90 for _, worst in c11_1),
                "diagnostic": True,
                "detail": "; ".join(f"{name}: worst of three = {worst:.4f}" for name, worst in c11_1),
            },
            {
                "name": "C11-1 restated: contract terms on fixed-coupon instrument rows",
                "passed": all(worst >= 0.90 for _, worst in c11_1_fixed),
                "diagnostic": True,
                "detail": (
                    "Denominator drops bank credit facilities, which have no fixed coupon to "
                    "report. Written after the row above was read, so both are carried. "
                    + "; ".join(f"{name}: worst of three = {worst:.4f}" for name, worst in c11_1_fixed)
                ),
            },
            {
                "name": "ROCR carries a distressed-exchange-specific marker (limited default)",
                "passed": ld_total > 0,
                "diagnostic": True,
                "detail": f"{ld_total} distinct obligors carry a limited-default symbol across {len(summaries)} file(s)",
            },
            {
                "name": "ROCR carries a marker for default of any kind",
                "passed": d_total > 0,
                "diagnostic": True,
                "detail": (
                    f"{d_total} distinct obligors carry a default symbol. This is a weaker "
                    "object than the criterion above: it does not separate a distressed "
                    "exchange from a missed payment or a bankruptcy."
                ),
            },
        ],
        "parameters": {
            "agency_filter": args.agency,
            "asset_classes": list(classes),
            "windows": [list(w) for w in WINDOWS],
            "rule_start": RULE_START,
            "limited_default_exact": sorted(LIMITED_DEFAULT_EXACT),
            "limited_default_suffix": LIMITED_DEFAULT_SUFFIX.pattern,
            "default_exact": sorted(DEFAULT_EXACT),
            "no_fixed_coupon_name": NO_FIXED_COUPON.pattern,
            "no_fixed_coupon_term": NO_FIXED_COUPON_TERM.pattern,
        },
        "files": summaries,
    }
    out = RESULTS / f"{output_slug(args.agency, classes)}.json"
    out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("=" * 78)
    print(f"written: {out}  (diagnostic_only, so RESULTS.md does not pick it up)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
