"""Argentina's simultaneous peso-dollar quotes: parse, collapse, load.

Stage B5. Registered in ``docs/b5_orphan_prereg.md``; sourcing and the ruling
that the stage may be opened at all are in ``docs/b5_orphan_availability.md``.

**This module owns the registered constants and the registered rules.**
``data/fetch_ambito.py`` imports them rather than restating them. A
pre-registered threshold that exists in two files has two truths, and the one
that gets edited is whichever the next reader happens to open.

What lives here
---------------

*Parsing*, because the endpoint's number format is a trap: ``DD/MM/YYYY`` dates,
**comma decimal separators**, periods grouping thousands. A parser assuming the
anglophone convention reads ``1.071,36`` as ``1.07136`` or ``107136`` and never
raises.

*The collapse*, because **the endpoint returns intraday snapshots and not a
daily series** -- a date can carry between two and nine rows with different
values and no timestamps. Registered rule (``b5_orphan_prereg.md`` §3.5): the
single row whose mid is that date's median mid, lower median on ties.

*The loader*, whose job is one guard: **no date may be counted twice.** Three
naming schemes sit in ``data/raw`` and the oldest overlaps the others in time.
A loader that globbed them all would double every date from 2020 to 2026 and
report a perfectly clean-looking panel.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from pathlib import Path

#: The four retrieved series, with the endpoint path and the quote fields each
#: returns. ``cl`` and not ``ccl``: the availability check listed
#: ``dolarrava/ccl`` by analogy and marked it "(same shape)"; it 404s.
#:
#: **MEP and CCL return a single ``Referencia`` and that is not a defect.** MEP
#: is a ratio of two bond prices, so it has no native two-sided quote. The
#: friction column therefore exists only for the oficial-blue pair, and
#: **constructing a synthetic spread for these two from any other series is
#: prohibited** (``b4_directed_edges.md`` §5.2).
SERIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "oficial": ("dolar/oficial", ("Compra", "Venta")),
    "informal": ("dolar/informal", ("Compra", "Venta")),
    "mep": ("dolarrava/mep", ("Referencia",)),
    "ccl": ("dolarrava/cl", ("Referencia",)),
}

#: Retrieved from the same endpoint, and **not an agent class.**
#:
#: The wholesale rate is stage B5's **test instrument**: it is the Ámbito side of
#: the zero calibration in `b5_orphan_prereg.md` §4.4, where the same number
#: published by argentinadatos in a different format must come back equal.
#:
#: **Kept out of ``SERIES`` deliberately, and this separation is load-bearing.**
#: Everything that enumerates agent classes -- ``load_panel``'s default,
#: ``coverage``, the pair enumeration -- reads ``SERIES``. A test instrument that
#: lived in the same dictionary would show up in the coverage table, then in a
#: pair, then in a headline, and nothing would have gone visibly wrong. The
#: wholesale rate is not an eligibility class: nobody is admitted to it by a rule
#: and excluded from it by another, which is the only thing this stage measures.
INSTRUMENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "mayorista": ("dolar/mayorista", ("Compra", "Venta")),
}

#: Everything retrieved from Ámbito, classes and instruments together. Used by
#: the fetcher and by the loader's field lookup, never by anything that forms
#: pairs.
ALL_AMBITO: dict[str, tuple[str, tuple[str, ...]]] = {**SERIES, **INSTRUMENTS}

#: The pairs for which ``S + S'`` is computable at all. Everything else enters
#: the headline only. Stated as data rather than as prose so that a criterion
#: cannot quietly ask for a friction term that does not exist.
TWO_SIDED_KEYS = frozenset(k for k, (_, f) in SERIES.items() if len(f) == 2)

#: ``b5_orphan_prereg.md`` §7. The start is the day exchange controls were
#: reimposed after the 2019 PASO crash, so the eligibility regime begins with
#: the window rather than inside it.
WINDOW_START = date(2019, 9, 1)
WINDOW_END = date(2026, 6, 30)

#: ``b5_orphan_prereg.md`` §7. The cepo removal.
INTERVENTION = date(2025, 4, 14)

#: ``b5_orphan_prereg.md`` §7. Symmetric 365-day bands; the intervention date
#: itself is in neither.
PRE_WINDOW = (date(2024, 4, 14), date(2025, 4, 13))
POST_WINDOW = (date(2025, 4, 15), date(2026, 4, 14))

#: ``b5_orphan_prereg.md`` §6A.3. The eight pre-quarters B5-13 named, kept as
#: B5-14's **second** rung rather than its primary one. It reaches back far
#: enough to enclose ``DEVALUATION``, across which a linear trend describes
#: nothing, and it is a different population from the one B5-8's ratios are
#: computed on, which is ``MEASUREMENT.md`` rule 1's window error waiting to
#: happen. Both rungs are reported whatever they show.
PRE_WINDOW_LONG = (date(2023, 4, 14), date(2025, 4, 13))

#: The December 2023 devaluation. Not a filter and not a criterion: it is marked
#: in B5-14's output so that a reader of the second rung can see the break
#: sitting inside the window the slope was fitted on.
DEVALUATION = date(2023, 12, 13)

#: ``b5_orphan_prereg.md`` §7. One-day change in the log mid, on the collapsed
#: daily series. Bookkeeper, not judge: its only job is to populate the list
#: that criterion B5-10 computes the headline with and without.
JUMP_THRESHOLD = 0.10

#: ``b5_orphan_prereg.md`` §7. A "one-day change" is only that if the two
#: observations are adjacent. Long weekends and Argentine holiday clusters reach
#: five or six days; beyond a week the neighbours are not neighbours.
MAX_GAP_DAYS = 7

#: Three naming schemes, all recognised so that none has to be deleted:
#:
#: - ``ambito_ccl_2019.json`` -- whole-year, the first run, **superseded**
#: - ``ambito_ccl_2019H2.json`` -- half-year, the normal unit
#: - ``ambito_ccl_2025-08-13_2025-08-13.json`` -- a bisected piece
VALID_NAME = re.compile(
    r"^ambito_(?P<series>oficial|informal|mep|ccl|mayorista)_"
    r"(?:(?P<year>\d{4})(?P<half>H[12])?"
    r"|(?P<start>\d{4}-\d{2}-\d{2})_(?P<end>\d{4}-\d{2}-\d{2}))\.json$"
)

#: ``1.071,36`` or ``1071,36`` or ``57,25``. A token carrying a period but no
#: comma is a format change and is rejected rather than guessed at.
NUMBER = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d+$|^\d+,\d+$")

DATE_FMT = "%d/%m/%Y"


class OverlappingChunks(Exception):
    """One date was found in two files that are both meant to be read.

    **The failure this exists to prevent does not look like a failure.** Three
    naming schemes sit in ``data/raw``; the whole-year files cover the same span
    as the half-year files that replaced them. A loader that read both would
    return every date from 2020 to 2026 twice, and a duplicated panel is not
    obviously wrong from any summary statistic computed on it -- the premium
    between two series would be unchanged, the counts would merely be double,
    and every criterion would run and pass on twice the sample it thinks it has.
    """


def is_superseded(name: str) -> bool:
    """True for the first run's whole-year files, which are kept but not read."""
    match = VALID_NAME.match(name)
    return bool(match and match.group("year") and not match.group("half"))


def parse_number(token: str) -> float:
    """Convert one quote token to a float, or raise.

    **Raises rather than returning a sentinel.** A quote that cannot be read is
    not a missing quote; it is a sign that the format changed, and continuing
    past it would put a silently wrong number into the headline.
    """
    token = token.strip()
    if not NUMBER.match(token):
        raise ValueError(
            f"quote token {token!r} does not match the registered "
            f"comma-decimal format; the endpoint's number format may have "
            f"changed and this code will not guess at it"
        )
    return float(token.replace(".", "").replace(",", "."))


def parse_rows(payload: object, fields: tuple[str, ...]) -> list[dict]:
    """Turn one endpoint response into dated rows, asserting the schema.

    The header is asserted rather than trusted: a renamed column would otherwise
    shift every value one position to the left and still parse. **This one has
    already happened here, with an underscore read for a hyphen.**

    **A header with no rows returns an empty list rather than raising.** The MEP
    series begins in March 2020, so the 2019 range is legitimately empty.
    """
    if not isinstance(payload, list) or not payload:
        raise ValueError("expected a non-empty JSON array")
    header = [str(c).strip() for c in payload[0]]
    if not header or header[0] != "Fecha":
        raise ValueError(
            f"expected first column 'Fecha', got {header[0] if header else None!r}"
        )
    missing = [f for f in fields if f not in header]
    if missing:
        raise ValueError(f"expected columns {missing} in header {header}")
    idx = {f: header.index(f) for f in fields}

    rows = []
    for raw in payload[1:]:
        cells = [str(c).strip() for c in raw]
        try:
            when = datetime.strptime(cells[0], DATE_FMT).date()
        except ValueError as exc:
            raise ValueError(
                f"date {cells[0]!r} is not {DATE_FMT}; the endpoint's date "
                f"format may have changed"
            ) from exc
        row = {"date": when.isoformat()}
        for field, i in idx.items():
            row[field.lower()] = parse_number(cells[i])
        rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return rows


def mid_of(row: dict, fields: tuple[str, ...]) -> float:
    """The geometric mid, which is what ``b4`` §5.1 defines ``w-hat`` on.

    ``b5_orphan_prereg.md`` §3.4: the claim is stated in logs, so it is
    aggregated in logs. The geometric mid is also what makes
    ``log(bid/mid) = -log(ask/mid)`` exact, which is why the spread cancels out
    of the headline instead of leaking into it.
    """
    if len(fields) == 1:
        return row[fields[0].lower()]
    return math.sqrt(row["compra"] * row["venta"])


def collapse_to_daily(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    """One row per date: the row whose mid is that date's median mid.

    Registered in ``b5_orphan_prereg.md`` §3.5.

    **A whole row is selected rather than a statistic computed per field.** The
    friction term is ``log(bid/ask)`` from one quote; a median bid paired with a
    median ask is a quote nobody published, and the spread of a manufactured
    quote is not a market's spread.

    **Median rather than mean**: on 21 August 2024 ``dolar/oficial`` returns
    ``954.12 / 300.76 / 953.17`` for one date. The mean is 736 and belongs to no
    market. **Median rather than first-or-last**: the
    endpoint publishes no timestamps, so a close is not identifiable.

    Ties and even counts take the **lower** median, fixed so the rule does not
    depend on sort stability.
    """
    by_date: dict[str, list[dict]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(row)
    out = []
    for when in sorted(by_date):
        same = by_date[when]
        if len(same) == 1:
            out.append(same[0])
            continue
        ordered = sorted(same, key=lambda r: mid_of(r, fields))
        out.append(ordered[(len(ordered) - 1) // 2])
    return out


def within_day_dispersion(
    rows: list[dict], fields: tuple[str, ...]
) -> list[dict]:
    """Per date carrying more than one row: how far apart those rows are.

    Reported so the choice ``collapse_to_daily`` makes is auditable instead of
    invisible. A reader who prefers a different rule can see what the
    disagreement was worth on each day.
    """
    by_date: dict[str, list[float]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(mid_of(row, fields))
    out = []
    for when in sorted(by_date):
        mids = [m for m in by_date[when] if m > 0]
        if len(by_date[when]) > 1 and len(mids) > 1:
            out.append({
                "date": when,
                "rows": len(by_date[when]),
                "log_range": round(math.log(max(mids)) - math.log(min(mids)), 6),
            })
    return out


def scan_anomalies(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    """Dates whose one-day log-mid change exceeds the registered threshold.

    **Runs on the collapsed series**, because the quantity the stage reports is
    the daily one. A gap longer than ``MAX_GAP_DAYS`` is recorded as a gap and
    resets the comparison chain rather than being reported as a one-day change.
    Both of those follow one rule -- a guard must compare the quantity that is
    actually reported -- and both were bugs here first.

    **Returns a list. Changes nothing.**
    """
    daily = collapse_to_daily(rows, fields)
    flagged = []
    previous = None
    for row in daily:
        mid = mid_of(row, fields)
        when = date.fromisoformat(row["date"])
        if mid <= 0:
            flagged.append({"date": row["date"], "reason": "non-positive mid",
                            "mid": mid})
            previous = None
            continue
        if previous is not None:
            gap = (when - previous["when"]).days
            if gap > MAX_GAP_DAYS:
                flagged.append({
                    "date": row["date"],
                    "reason": "gap in the series, comparison chain reset",
                    "previous_date": previous["date"],
                    "gap_days": gap,
                })
            else:
                change = math.log(mid) - math.log(previous["mid"])
                if abs(change) > JUMP_THRESHOLD:
                    flagged.append({
                        "date": row["date"],
                        "reason": "one-day log-mid change exceeds threshold",
                        "previous_date": previous["date"],
                        "previous_mid": round(previous["mid"], 4),
                        "mid": round(mid, 4),
                        "gap_days": gap,
                        "log_change": round(change, 4),
                    })
        previous = {"date": row["date"], "when": when, "mid": mid}
    return flagged


# --------------------------------------------------------------------- loading


def chunk_files(raw_dir: Path, key: str) -> list[Path]:
    """The files this loader will read for one series, superseded ones excluded.

    Anything that does not match ``VALID_NAME`` is **left in place and not
    read**, which is the arrangement that means nothing ever has to be deleted.
    """
    out = []
    for path in sorted(raw_dir.glob(f"ambito_{key}_*.json")):
        match = VALID_NAME.match(path.name)
        if not match or match.group("series") != key:
            continue
        if is_superseded(path.name):
            continue
        out.append(path)
    return out


def load_series(raw_dir: Path, key: str) -> list[dict]:
    """Every retrieved date for one series, collapsed to one row per date.

    Raises :class:`OverlappingChunks` if any date appears in two files. That is
    the guard this function exists for; see the exception's docstring for why a
    duplicated panel is not visible downstream.
    """
    if key not in ALL_AMBITO:
        raise KeyError(
            f"unknown series {key!r}; expected one of {sorted(ALL_AMBITO)}"
        )
    _, fields = ALL_AMBITO[key]

    seen: dict[str, str] = {}
    rows: list[dict] = []
    for path in chunk_files(raw_dir, key):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in collapse_to_daily(parse_rows(payload, fields), fields):
            first = seen.get(row["date"])
            if first is not None:
                raise OverlappingChunks(
                    f"{key} {row['date']} appears in both {first} and "
                    f"{path.name}; the loader would count it twice"
                )
            seen[row["date"]] = path.name
            rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return rows


def load_panel(raw_dir: Path, keys: tuple[str, ...] | None = None) -> dict:
    """``{series: {date: row}}`` for the requested series, defaulting to all."""
    wanted = keys if keys is not None else tuple(SERIES)
    return {
        key: {row["date"]: row for row in load_series(raw_dir, key)}
        for key in wanted
    }


def in_window(dates, window: tuple[date, date]) -> list[str]:
    first, last = window[0].isoformat(), window[1].isoformat()
    return sorted(d for d in dates if first <= d <= last)


def pair_dates(panel: dict, left: str, right: str) -> list[str]:
    """Dates on which **both** series have a quote.

    ``b5_orphan_prereg.md`` §7: a date enters an analysis only if every class
    that criterion needs has a quote on it. Missingness is reported per arm,
    never imputed and never forward-filled -- a forward-filled quote
    manufactures a day on which two classes agreed, which is the quantity in
    dispute.

    **The date sets therefore differ across pairs**, and every reported number
    has to say which one it was computed on.
    """
    for key in (left, right):
        if key not in panel:
            raise KeyError(f"{key!r} not loaded; panel has {sorted(panel)}")
    return sorted(set(panel[left]) & set(panel[right]))


# ------------------------------------------------- argentinadatos, the other format


#: The two argentinadatos series and what each is for. **Neither is an agent
#: class**, so neither appears in ``SERIES`` or ``INSTRUMENTS``.
ARGENTINADATOS_CASAS = {
    "mayorista": "zero calibration, the argentinadatos-format counterpart (4.4)",
    "tarjeta": "dating instrument for the tax regime (5.2)",
    "oficial": "candidate for the oficial friction leg, REJECTED (3.2a)",
    "cripto": "candidate for the P2P agent class, unvalidated (2.1, 9.4)",
}

#: **Retrieved as a candidate and not yet adopted.** ``b5_orphan_prereg.md`` §3.2
#: requires the oficial friction term to come from **one named dealer**, because
#: a range across bank counters would put dispersion between banks -- an agent
#: index -- into a quantity defined as one agent's round-trip cost.
#:
#: This series looks like a single dealer's posted board rather than a range: on
#: the dates checked by hand the spread is exactly ``50.00`` pesos, round and
#: constant, where Ámbito's ``dolar/oficial`` shows an unround spread that moves
#: every day. **That is a fingerprint and not a proof**, so ``experiments/
#: b5_friction.py`` validates it before anything uses it, on three axes: the
#: spread's constancy, agreement of the mid with BCRA inside the calibration
#: bounds, and the absence of the frozen runs that disqualified ``mayorista``.
OFICIAL_FRICTION_CANDIDATE = "argentinadatos_oficial"

#: **Retrieved as a candidate and not yet adopted.** ``b5_orphan_prereg.md`` §2.1
#: registers a fifth agent class, ``ARS/USDT`` P2P, whose eligibility is a
#: platform account rather than a state licence and which the April 2025
#: intervention therefore did not touch. It is the control unit B5-9, B5-12 and
#: B5-13 are written against.
#:
#: **It is the one series in this stage with no referee, and that is structural
#: rather than an oversight.** There is no central bank for a crypto market and no
#: second full-window collector: CriptoYa publishes bid and ask across thirty-six
#: venues but only for the current moment. So the audit in
#: ``experiments/b5_p2p.py`` can run the frozen-run test that caught ``mayorista``
#: and ``oficial``, and cannot run the third-party referee that
#: ``b5_orphan_availability.md`` §7.4 otherwise requires.
#:
#: **The bias this introduces has no clean sign**, which is worse than a known
#: direction: a stale control series would track ``blue`` through its own
#: staleness, and whether that inflates or deflates its premium against ``blue``
#: depends on which way ``blue`` moved. Stated here rather than in a footnote.
P2P_CANDIDATE = "argentinadatos_cripto"

#: See ``parse_argentinadatos_rows``. Two bands because the archive reaches back
#: to 2011, when the peso was near ``3.97``, while the registered window opens
#: near ``56`` and ends near ``1900``. One absolute band admitting both spans a
#: factor of five hundred and catches nothing in between.
PLAUSIBLE_ARCHIVE = (0.01, 10_000_000.0)
PLAUSIBLE_WINDOW = (10.0, 100_000.0)


def parse_argentinadatos_rows(payload: object, casa: str) -> list[dict]:
    """The **other** parser, and it must stay other.

    Ámbito serves ``["12/06/2025","1176,00","1185,00"]``: comma decimals,
    thousands separators, ``DD/MM/YYYY``. This serves
    ``{"compra":1176,"venta":1185,"fecha":"2025-06-12"}``: JSON numbers, ISO
    dates.

    **The zero calibration in ``b5_orphan_prereg.md`` §4.4 is built on these two
    being handled by two separate pieces of code that then have to agree on the
    number.** A parser lenient enough to read both would be lenient enough to
    misread either, and the arm would be testing one lenient reader against
    itself. So this one refuses the other's conventions explicitly rather than
    coping with them.
    """
    if not isinstance(payload, list) or not payload:
        raise ValueError("expected a non-empty JSON array")

    rows = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError(f"expected objects, got {type(entry).__name__}")
        got = entry.get("casa")
        if got != casa:
            raise ValueError(
                f"row is casa {got!r} but {casa!r} was requested; the path may "
                f"name a different series than the parser expects"
            )
        raw_date = entry.get("fecha")
        try:
            when = date.fromisoformat(str(raw_date))
        except ValueError as exc:
            raise ValueError(
                f"date {raw_date!r} is not ISO-8601. **This API uses ISO dates "
                f"and JSON numbers; Ambito uses DD/MM/YYYY and comma decimals.** "
                f"If this fires, the two conventions have been crossed"
            ) from exc
        inside = (
            WINDOW_START.isoformat() <= when.isoformat() <= WINDOW_END.isoformat()
        )
        band = PLAUSIBLE_WINDOW if inside else PLAUSIBLE_ARCHIVE
        out = {"date": when.isoformat()}
        for field in ("compra", "venta"):
            value = entry.get(field)
            if isinstance(value, str):
                raise ValueError(
                    f"{raw_date}: {field} arrived as the string {value!r}. This "
                    f"parser does not accept string quotes, because accepting "
                    f"them would mean guessing at a decimal convention"
                )
            if not isinstance(value, int | float):
                raise ValueError(f"{raw_date}: {field} is {value!r}, not a number")
            value = float(value)
            if not band[0] <= value <= band[1]:
                where = "inside" if inside else "outside"
                raise ValueError(
                    f"{raw_date}: {field} = {value} outside {band}, the band "
                    f"for rows {where} the registered window"
                )
            out[field] = value
        rows.append(out)

    if len({r["date"] for r in rows}) != len(rows):
        raise ValueError(
            "the same date appears twice. This API is expected to publish one "
            "row per date; Ambito's intraday-snapshot collapse is registered for "
            "Ambito and may not be borrowed here"
        )
    rows.sort(key=lambda r: r["date"])
    return rows


def argentinadatos_path(raw_dir: Path, casa: str) -> Path:
    return raw_dir / f"argentinadatos_{casa}.json"


def load_argentinadatos(raw_dir: Path, casa: str) -> list[dict]:
    """One argentinadatos series, one row per date, in date order."""
    if casa not in ARGENTINADATOS_CASAS:
        raise KeyError(
            f"unknown casa {casa!r}; expected one of {sorted(ARGENTINADATOS_CASAS)}"
        )
    path = argentinadatos_path(raw_dir, casa)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_argentinadatos_rows(payload, casa)


# -------------------------------------------------- BCRA, the third convention


#: ``DOLAR REFERENCIA COM 3500`` in BCRA's ``/Maestros/Divisas``. **Not ``USD``**,
#: which is a different series on the same API and would parse perfectly while
#: answering another question.
BCRA_CODE = "REF"

#: Pesos per dollar, 2019-2026. An absurdity check: this API returns JSON floats,
#: so there is no decimal convention here to flip.
BCRA_PLAUSIBLE = (10.0, 100_000.0)


def parse_bcra_rows(payload: object) -> list[dict]:
    """The **third** parser: JSON objects, ISO dates, and a paginated envelope.

    Every assertion is about a change that would still parse. The page limit in
    particular: a range wider than ``limit`` returns a well-formed response
    holding a prefix of the answer, and nothing downstream distinguishes a
    quarter that is missing from a quarter the central bank did not publish.
    """
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    if payload.get("status") != 200:
        raise ValueError(f"status {payload.get('status')!r}, expected 200")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("no 'results' list in the response")

    meta = payload.get("metadata", {}).get("resultset", {})
    count, limit = meta.get("count"), meta.get("limit")
    if isinstance(count, int) and isinstance(limit, int) and count >= limit:
        raise ValueError(
            f"response holds {count} rows against a page limit of {limit}; it "
            f"is truncated and the chunk must be narrowed rather than accepted"
        )

    rows = []
    for entry in results:
        when = entry.get("fecha")
        try:
            parsed = date.fromisoformat(str(when))
        except ValueError as exc:
            raise ValueError(f"date {when!r} is not ISO-8601") from exc
        detail = [
            d for d in entry.get("detalle", [])
            if d.get("codigoMoneda") == BCRA_CODE
        ]
        if len(detail) != 1:
            raise ValueError(
                f"{when}: expected exactly one {BCRA_CODE} entry, "
                f"got {len(detail)}"
            )
        value = detail[0].get("tipoCotizacion")
        if not isinstance(value, int | float):
            raise ValueError(f"{when}: tipoCotizacion is {value!r}, not a number")
        value = float(value)
        if not BCRA_PLAUSIBLE[0] <= value <= BCRA_PLAUSIBLE[1]:
            raise ValueError(
                f"{when}: reference rate {value} outside {BCRA_PLAUSIBLE}; the "
                f"decimal convention may have changed"
            )
        rows.append({"date": parsed.isoformat(), "reference": value})

    if len({r["date"] for r in rows}) != len(rows):
        raise ValueError("the same date appears twice in one response")
    rows.sort(key=lambda r: r["date"])
    return rows


def load_bcra_reference(raw_dir: Path) -> dict[str, float]:
    """``{date: A 3500}`` over every retrieved chunk."""
    out: dict[str, float] = {}
    for path in sorted(raw_dir.glob("bcra_ref_*.json")):
        for row in parse_bcra_rows(json.loads(path.read_text(encoding="utf-8"))):
            out[row["date"]] = row["reference"]
    return out


# --------------------------------------------------- composing the agent classes


#: Which source supplies each class's **headline mid**, per
#: ``b5_orphan_prereg.md`` §3.1. Written as data so that a criterion cannot ask
#: for a leg from a source the pre-registration did not assign to it.
#:
#: **``oficial`` does not come from Ámbito.** Ámbito's ``dolar/oficial`` is a
#: range across retail bank counters, and §3.2 rules that reading it as this
#: class would put dispersion across banks -- an agent index -- into the
#: headline. It is retrieved as a cross-check and is not this leg.
HEADLINE_SOURCE = {
    "oficial": "bcra",
    "informal": "ambito",
    "mep": "ambito",
    "ccl": "ambito",
}

#: Which classes have a friction term at all, and where it comes from. Empty
#: entries are **not** gaps to be filled: MEP and CCL are ratios of bond prices
#: and have no native two-sided quote, and constructing one from any other
#: series is prohibited (``b4_directed_edges.md`` §5.2).
#:
#: ``oficial``'s friction is Banco de la Nación's posted counter rates (§3.2) and
#: is **not retrieved yet**, so the class currently has a headline and no
#: friction.
FRICTION_SOURCE = {
    "oficial": None,
    "informal": "ambito",
    "mep": None,
    "ccl": None,
}

#: The class whose eligibility rule the 14 April 2025 intervention deleted: the
#: USD 200 monthly cap on individuals buying at the official rate.
TREATED_CLASS = "oficial"

#: ``b5_orphan_prereg.md`` §3.2b. **The friction column has no source**, so
#: B5-8's "something that should not move" is a set of pairs rather than a
#: column. A pair is treated if it contains the class whose rule was deleted.
#:
#: **Cleaner than the friction version it replaces**: that one needed the extra,
#: unargued assumption that round-trip costs do not respond to a change in
#: eligibility rules. This compares premia to premia, same units, same quotes,
#: same dates.
#:
#: **And weaker in one respect**, which the write-up states: MEP and CCL are not
#: untouched by everything. The cross-restriction between the official and
#: financial markets was removed on the intervention date and **reimposed in
#: September 2025**, inside the post-window. So the
#: control group is clean with respect to the deleted cap and not with respect to
#: every rule. ``informal`` is the only class whose access was never rule-bound,
#: which is why ``oficial-informal`` stays the headline pair.
UNTOUCHED_BY_THE_CAP = ("informal", "mep", "ccl")


def pair_group(left: str, right: str) -> str:
    """``treated`` if the pair contains the class whose rule was deleted."""
    return "treated" if TREATED_CLASS in (left, right) else "control"


def load_agent_classes(raw_dir: Path) -> dict[str, dict[str, tuple[float, float]]]:
    """``{class: {date: (bid, ask)}}`` composed per §3.1's source table.

    A class with no published spread gets ``bid == ask``, which is the honest
    encoding: its ``ω̄`` is then exactly zero rather than approximately zero, so
    a friction column built on it is visibly empty instead of quietly small.

    **The oficial leg is the central bank's reference and carries no spread**, so
    until Banco de la Nación's counter rates are retrieved that class has a
    headline mid and no friction term at all.
    """
    out: dict[str, dict[str, tuple[float, float]]] = {}
    ambito = load_panel(raw_dir, tuple(
        k for k, src in HEADLINE_SOURCE.items() if src == "ambito"
    ))
    for key, source in HEADLINE_SOURCE.items():
        if source == "bcra":
            out[key] = {d: (v, v) for d, v in load_bcra_reference(raw_dir).items()}
            continue
        fields = ALL_AMBITO[key][1]
        rows = ambito[key]
        if len(fields) == 1:
            field = fields[0].lower()
            out[key] = {d: (r[field], r[field]) for d, r in rows.items()}
        else:
            out[key] = {d: (r["compra"], r["venta"]) for d, r in rows.items()}
    return out


def coverage(panel: dict) -> dict:
    """Per series and per pair: how many dates, and how many in each window.

    This is the table ``b5_orphan_prereg.md`` §7 requires to accompany every
    result, produced from the same loader the results come from rather than
    counted separately.
    """
    keys = sorted(panel)
    series = {
        key: {
            "dates": len(panel[key]),
            "first": min(panel[key]) if panel[key] else None,
            "last": max(panel[key]) if panel[key] else None,
            "pre": len(in_window(panel[key], PRE_WINDOW)),
            "post": len(in_window(panel[key], POST_WINDOW)),
        }
        for key in keys
    }
    pairs = {}
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            both = pair_dates(panel, left, right)
            pairs[f"{left}-{right}"] = {
                "dates": len(both),
                "pre": len(in_window(both, PRE_WINDOW)),
                "post": len(in_window(both, POST_WINDOW)),
                "friction_available": (
                    left in TWO_SIDED_KEYS and right in TWO_SIDED_KEYS
                ),
            }
    return {"series": series, "pairs": pairs}
