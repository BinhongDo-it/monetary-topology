"""Stage B6's registered constants, the BCC record, and the guards on it.

Registered in ``docs/b6_cuba_prereg.md`` §2, §3 and §6. Availability and the
ruling that the stage may be opened are in ``docs/b6_cuba_availability.md``.

The graph
---------

There is **one position edge**, ``CUP <-> USD``, with ``EUR`` entering only in
the triangle of prereg §2.4. What varies is the agent factor: the Banco Central
de Cuba prices the same conversion three ways on the same day, and which price
applies to you is fixed by legal status and by the operation being performed.

So every cycle here is **two agents on one edge**, which is Theorem 1's square,
and ``orphan_squares`` already owns that arithmetic. This module owns the source:
what the record is, which parts of it are constants rather than measurements, and
the five guards prereg §6 requires.

Two things about this source that shape every function below
------------------------------------------------------------

**The nineteen channel columns are one number times a fixed vector.** Every
channel is ``base * k`` with ``k`` from ``MARKUP_SCHEDULE``, constant across all
238 days and all six published files to within the four-decimal rounding. So a
square with both legs inside one segment is a construction identity with zero
variance, and prereg §2.2 forbids it as a headline. The same fact is the
known-answer arm of B6-3, which is why the schedule is a registered constant here
rather than a number read out of the file at run time.

**The XLSX carries every calendar day and the API carries only publication
days.** The XLSX's extra days are forward fills of the previous published value,
and the publication schedule changes inside the window: Sundays and Mondays are
absent through 2026-02-23 and publication is near daily from 2026-03-10. Running
an estimator on the filled calendar therefore puts a stale quote against a
moving one for two days in seven early on and almost never later, which is a
measurement error correlated with the level being measured and nothing in the
file reports it. prereg §3.2 rules the estimator onto publication days;
``publication_days`` is where that rule lives.

What is deliberately not here
-----------------------------

**No imputation across a one-way edge.** Segments I and II have no return leg,
so their ``w_bar`` is undefined rather than zero and there is no function here
that will supply one from another class, from a lag, or from a model
(``b4_directed_edges.md`` §5.2).

**No slice-against-square decomposition.** Theorem 2 does not extend to directed
graphs (``PROJECT_PLAN.md`` §12.10), and segments I and II are directed.
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Registered constants. prereg §6.
# ---------------------------------------------------------------------------

#: First publication day in the API. A request for 2025-01-01 to 2025-12-31
#: returns nine rows, all on or after this date, so **there is no pre-window
#: formal leg** and prereg §8 states that as scope rather than as a to-do.
WINDOW_START = date(2025, 12, 19)

#: The API's own field names, in the order the segments are numbered.
#:
#: The names are the source's, not this project's, and are kept verbatim so that
#: a reader can match a column here against the response body without a
#: translation table. ``tasaOficial`` is the 1x24 schedule for legal persons,
#: ``tasaPublica`` the 1x120 schedule for natural persons, ``tasaEspecial`` the
#: managed float opened on 2025-12-18.
SEGMENTS: dict[str, str] = {
    "I": "tasaOficial",
    "II": "tasaPublica",
    "III": "tasaEspecial",
}

#: The currencies retrieved. **None of them is a second carrier.** The stage's
#: object is ``CUP <-> USD``; every other currency exists so that the position
#: factor can be examined rather than assumed, which is B6-5 on one triangle and
#: B6-8 across all of them.
#:
#: Listed once and used three ways: the fetcher iterates it, ``VALID_XLSX`` is
#: built from it, and a file for a currency not on this list is skipped and
#: reported rather than read. A currency the stage has not registered is not a
#: bonus observation.
CURRENCIES = (
    "USD", "EUR", "CAD", "CHF", "GBP", "JPY", "MXN",
    "AUD", "NOK", "DKK", "SEK", "CNY", "RUB",
)

#: The dollar. Every other currency's ladder is compared against this one's,
#: which is what B6-8 asks.
BASE_CURRENCY = "USD"

#: How the bank quotes each currency, **in the bank's own words**.
#:
#: The page carries a footnote: the yen is published ``de manera indirecta``
#: while every other currency is ``de forma directa``. Direct means the column is
#: pesos per unit of the foreign currency; indirect means it is units of the
#: foreign currency per peso. The yen is inverted because a peso is worth a few
#: yen and a yen is worth a few pesos, so the direct column would carry no
#: significant figures at the published precision.
#:
#: **This is a registered source property, not an inference.** Two independent
#: checks confirm it and neither is how it was established: the segment ladder
#: runs `1/5` and `1/26` for the yen where every direct currency runs `5` and
#: `26` (``guard_quotation_orientation`` asserts exactly this, so a change of
#: convention stops the run), and `24 x 6.58062` recovers a plausible USD/JPY.
#: Determining the orientation from whichever choice makes B6-8 pass would be
#: fitting; determining it from a footnote is reading.
QUOTATION: dict[str, str] = {code: "direct" for code in CURRENCIES}
QUOTATION["JPY"] = "indirect"

#: The segment ladder, from the two fixed rates and the float. A direct currency
#: multiplies by these; an indirect one divides.
def segment_ladder(rates: dict[str, float]) -> dict[str, float]:
    """``{segment: rate / rate(I)}`` for one currency on one date."""
    anchor = rates["I"]
    if anchor <= 0:
        raise ValueError(f"non-positive anchor {anchor}")
    return {tag: rates[tag] / anchor for tag in rates}


def to_direct(rates: dict[str, float], currency: str) -> dict[str, float]:
    """Pesos per unit, whichever way the bank publishes the currency.

    The inversion is applied from ``QUOTATION`` and from nothing else. A caller
    cannot pass an orientation, because the orientation is a fact about the
    source rather than an argument.
    """
    how = QUOTATION[currency]
    if how == "direct":
        return dict(rates)
    if how == "indirect":
        return {tag: 1.0 / value for tag, value in rates.items()}
    raise GuardFailed(f"{currency}: unknown quotation {how!r}")

#: Segments whose class has **no return leg**, so that ``b4`` §5.2 types them
#: ``H0``. Stated as data rather than as prose so that a criterion cannot read
#: one of them as an ordinary two-way class by forgetting a sentence.
ONE_WAY_SEGMENTS = ("I", "II")

#: The float. The one segment on this carrier that quotes both directions.
TWO_WAY_SEGMENT = "III"

#: Channel markups, as published. ``k`` multiplies the segment's base rate.
#:
#: **This is the known-answer arm's answer key** (B6-3) and the object guard 1
#: validates against the XLSX. A channel that publishes only one side has only
#: that side here: writing the missing side as equal to the other would make its
#: friction exactly zero, which is the honest encoding elsewhere in this project
#: but is **wrong here**, because these channels do not fail to publish a spread,
#: they are one-directional services.
MARKUP_SCHEDULE: dict[str, dict[str, float]] = {
    "efectivo_ventanilla": {"compra": 0.980, "venta": 1.020},
    "efectivo_aeropuertos_hoteles": {"compra": 0.970, "venta": 1.060},
    "efectivo_domingos_feriados": {"compra": 0.965, "venta": 1.060},
    "transferencia_externa_a_cuenta": {"compra": 0.990},
    "transferencia_externa_a_efectivo": {"compra": 0.970},
    "compra_con_tarjetas_internacionales": {"compra": 0.980},
    "servicios_de_divisas_a_cup": {"compra": 0.990},
    "transferencia_de_divisas_a_cup": {"compra": 1.000},
    "transferencia_de_cup_a_divisas": {"venta": 1.015},
    "retiro_efectivo_cup_desde_cuenta_en_divisas": {"compra": 0.970},
    "deposito_efectivo_cup_a_cuenta_en_divisas": {"venta": 1.015},
    "deposito_efectivo_en_divisas_a_cuenta": {"compra": 0.980},
    "usd_legal_no_efectivo": {"compra": 0.990},
    "usd_legal_efectivo_cup_entrada_salida": {"compra": 0.980},
    "usd_legal_preferencial": {"compra": 0.990, "venta": 1.010},
}

#: The XLSX header each markup is validated against. The headers are Spanish and
#: carry accents; the keys above do not, so this mapping is the one place the two
#: spellings meet and the only place a header change has to be edited.
XLSX_HEADERS: dict[tuple[str, str], str] = {
    ("efectivo_ventanilla", "compra"): "Efectivo en Ventanilla - Compra",
    ("efectivo_ventanilla", "venta"): "Efectivo en Ventanilla - Venta",
    ("efectivo_aeropuertos_hoteles", "compra"):
        "Efectivo en Aeropuertos/Hoteles - Compra",
    ("efectivo_aeropuertos_hoteles", "venta"):
        "Efectivo en Aeropuertos/Hoteles - Venta",
    ("efectivo_domingos_feriados", "compra"):
        "Efectivo Domingos/Feriados - Compra",
    ("efectivo_domingos_feriados", "venta"):
        "Efectivo Domingos/Feriados - Venta",
    ("transferencia_externa_a_cuenta", "compra"):
        "Transferencia Externa a Cuenta - Compra",
    ("transferencia_externa_a_efectivo", "compra"):
        "Transferencia Externa a Efectivo - Compra",
    ("compra_con_tarjetas_internacionales", "compra"):
        "Compra con Tarjetas Internacionales - Compra",
    ("servicios_de_divisas_a_cup", "compra"):
        "Servicios de Divisas a CUP - Compra",
    ("transferencia_de_divisas_a_cup", "compra"):
        "Transferencia de Divisas a CUP - Compra",
    ("transferencia_de_cup_a_divisas", "venta"):
        "Transferencia de CUP a Divisas - Venta",
    ("retiro_efectivo_cup_desde_cuenta_en_divisas", "compra"):
        "Retiro de Efectivo CUP desde Cuenta en Divisas - Compra",
    ("deposito_efectivo_cup_a_cuenta_en_divisas", "venta"):
        "Depósito de Efectivo CUP a Cuenta en Divisas - Venta",
    ("deposito_efectivo_en_divisas_a_cuenta", "compra"):
        "Depósito de Efectivo en Divisas a Cuenta - Compra",
    ("usd_legal_no_efectivo", "compra"): "USD Legal No Efectivo - Compra",
    ("usd_legal_efectivo_cup_entrada_salida", "compra"):
        "USD Legal Efectivo CUP Entrada/Salida - Compra",
    ("usd_legal_preferencial", "compra"): "USD Legal Preferencial - Compra",
    ("usd_legal_preferencial", "venta"): "USD Legal Preferencial - Venta",
}

#: Decimals in the published series, both routes.
PUBLISHED_DECIMALS = 4

#: One unit in the last published place.
#:
#: **The publisher truncates, it does not round.** Checked on 2026-08-12 over
#: every channel column of all six published files: 27 132 of 27 132 values equal
#: ``floor(base * k * 1e4) / 1e4`` and none equals the rounded value. So the
#: error a published value carries is up to a **whole** unit in the last place
#: and is one-sided, not half a unit either way. Assuming rounding would put
#: B6-3's tolerance a factor of two too tight on every pair.
PUBLISHED_ULP = 10.0 ** (-PUBLISHED_DECIMALS)


def published_from(base: float, k: float) -> float:
    """The value the BCC publishes for a channel, from the base and its ``k``.

    Truncation at ``PUBLISHED_DECIMALS``, per ``PUBLISHED_ULP``. This is a model
    of the publisher's arithmetic, and B6-3 tests it as such: because it is
    exact rather than approximate, the criterion is a strict equality with
    nothing to slide, which is worth more than a tolerance derived from it.
    """
    scale = 10.0 ** PUBLISHED_DECIMALS
    return math.floor(base * k * scale) / scale

#: B6-1's tolerance. The two paths are the same arithmetic in a different order,
#: so anything above rounding is a bug rather than a precision question.
#: Precedent: B5-1, same constant, same reason.
MACHINERY_TOLERANCE = 1e-12

#: B6-6's factor. **Not chosen for this stage**: B3-3 and B5-6 both used it.
SIGNAL_OVER_NOISE = 4.0

#: B6-4's band on the implied euro cross against an independent reference.
#:
#: **One clause, not two.** A ``[t-1, t+1]`` envelope was registered alongside
#: this and has been withdrawn: the BCC does not copy the ECB, it runs its own
#: fixing, so an envelope tests *which* fixing rather than whether the euro leg
#: is a real cross. See ``b6_cuba_prereg.md`` §11. What survives is the check
#: B6-4 exists for: a fabricated or stale euro leg cannot stay inside one percent
#: of an independent reference across eight months.
CROSS_BAND = 0.01

#: The grid every published base rate lies on. Checked at retrieval over all
#: thirty-nine files, worst departure ``7.5e-9``. B6-8's tolerance is derived
#: from it rather than chosen: a small currency carries more relative rounding
#: than a large one, so a single constant would be loose on the pound and wrong
#: on the rouble.
BASE_ULP = 1e-5


def ladder_tolerance(anchor: float, other: float) -> float:
    """B6-8's tolerance for one currency's ladder rung on one date."""
    if anchor <= 0 or other <= 0:
        raise ValueError(f"non-positive rate {anchor} {other}")
    return BASE_ULP * (1.0 / anchor + 1.0 / other)


#: Anything outside this is not a rate. Ten orders of magnitude wide on purpose:
#: its job is to catch a schema change, a units change, or a zero, not to judge
#: the level.
#:
#: **The lower end has to admit sub-unit quotes and the first version did not.**
#: The yen is published indirectly and sits near `0.25`; the rouble is published
#: directly and sits near `0.29`. A band of `(1.0, 1e6)` was written when the
#: stage held two currencies, and it rejected both of them the moment the stage
#: held thirteen. Two currencies is not a sample.
PLAUSIBLE = (1.0e-4, 1.0e6)


# ---------------------------------------------------------------------------
# The API record
# ---------------------------------------------------------------------------


def parse_bcc_rows(payload: object) -> list[dict]:
    """Rows from one API response, validated rather than trusted.

    Endpoint, verified 2026-08-12::

        https://api.bc.gob.cu/v1/tasas-de-cambio/historico
            ?fechaInicio=YYYY-MM-DD&fechaFin=YYYY-MM-DD&codigoMoneda=USD

    Free, no key, no registration. Both endpoints of the range are inclusive.

    Three ways this differs from the Argentine sources, each a place to get it
    wrong.

    **Numbers are JSON numbers with a period.** The Ambito parser's comma rule
    would reject every row here. Both parsers assert their own convention rather
    than sniffing, so pointing one at the other's payload fails loudly.

    **Three rates per row, no bid and no ask.** A central bank publishes
    references. The channel quotes with spreads are reconstructed from
    ``MARKUP_SCHEDULE``, not retrieved, and only for the float.

    **A missing day is a real absence, not a hole to fill.** The API returns the
    days on which a rate was published; the XLSX forward-fills the rest. This
    parser records what arrived and never interpolates.
    """
    if not isinstance(payload, list):
        raise ValueError(f"expected a JSON array, got {type(payload).__name__}")
    out: list[dict] = []
    for i, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"row {i}: expected an object")
        try:
            when = str(item["fecha"])
        except KeyError as exc:
            raise ValueError(f"row {i}: no 'fecha'") from exc
        try:
            date.fromisoformat(when)
        except ValueError as exc:
            raise ValueError(f"row {i}: 'fecha' is not ISO: {when!r}") from exc
        row: dict = {"date": when}
        for tag, field in SEGMENTS.items():
            if field not in item:
                raise ValueError(f"row {i}: no {field!r}")
            value = item[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"row {i}: {field} is not a number: {value!r}")
            value = float(value)
            if not PLAUSIBLE[0] <= value <= PLAUSIBLE[1]:
                raise ValueError(f"row {i}: {field}={value} outside {PLAUSIBLE}")
            row[tag] = value
        out.append(row)
    seen = [r["date"] for r in out]
    if len(set(seen)) != len(seen):
        raise ValueError("the response repeats a date")
    if seen != sorted(seen):
        raise ValueError("the response is not in date order")
    return out


def bcc_path(raw_dir: Path, currency: str) -> Path:
    return Path(raw_dir) / f"bcc_{currency.lower()}.json"


#: The XLSX exports, downloaded by hand from the form on ``bc.gob.cu``.
#:
#: The export is behind a form rather than behind a URL, so the six files cannot
#: be fetched. The loader accepts only names matching this pattern, which is the
#: device ``parallel_rates.VALID_NAME`` uses: **a file that should not be read is
#: ignored by the code rather than deleted from the disk** (``CLAUDE.md`` rule 5).
#:
#: **The separators are optional, and the reason is a mistake worth recording.**
#: The download name is ``tasas-historicas-USD-Segmento-III-2026-08-12.xlsx``.
#: The first version of this pattern was written against a copy of that name
#: whose hyphens a file-transfer step had stripped, so it accepted a name the
#: source never produces and rejected all six real files, reporting the directory
#: as empty. Same failure as ``PROJECT_PLAN.md`` §14.6's rule about endpoints, one
#: level down: **a filename read off an intermediary is not the filename.** Both
#: forms are accepted now because either can reach the directory, and
#: ``xlsx_skipped`` says out loud what was not accepted.
VALID_XLSX = re.compile(
    r"^tasas-?historicas-?(?P<currency>" + "|".join(CURRENCIES) + r")"
    r"-?Segmento-?(?P<segment>III|II|I)"
    r"-?(?P<stamp>\d{4}-?\d{2}-?\d{2})\.xlsx$"
)


def xlsx_snapshot(path: Path) -> date:
    """The date the export was taken, read off its own filename.

    **Load-bearing, because the tail of a snapshot is provisional.** The site
    serves a complete calendar, so an export taken before the day's rate has been
    published carries that day as a forward fill of the previous published value.
    When the rate appears later, the API and the snapshot disagree on that row,
    and they disagree correctly: they were taken at different times.

    Guard 2 therefore compares values only on rows dated **before** the snapshot,
    and checks the rest as forward fills. The boundary comes from the filename
    rather than from the data, so it cannot be slid to wherever a disagreement
    happens to be.
    """
    m = VALID_XLSX.match(path.name)
    if not m:
        raise GuardFailed(f"{path.name} is not a name the loader accepts")
    stamp = m.group("stamp").replace("-", "")
    return date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8]))


def xlsx_skipped(raw_dir: Path) -> list[str]:
    """Names present in ``bcc_xlsx/`` that ``VALID_XLSX`` does not accept.

    **Reported rather than merely skipped.** "The directory is empty" and "the
    directory holds six files whose names the loader does not accept" produce the
    same behaviour and must not produce the same message: a browser that appends
    " (1)" to a second download would otherwise make six files invisible with no
    way to tell from the output. ``PROJECT_PLAN.md`` §11.11 collects guards that
    were silent when they should have spoken.
    """
    directory = Path(raw_dir) / "bcc_xlsx"
    if not directory.exists():
        return []
    return sorted(
        p.name for p in directory.iterdir()
        if p.is_file() and not VALID_XLSX.match(p.name)
    )


def xlsx_files(raw_dir: Path) -> dict[tuple[str, str], Path]:
    """``{(currency, segment): path}`` for names matching ``VALID_XLSX``.

    A name that does not match is skipped, never renamed and never removed, and
    ``xlsx_skipped`` is how a caller says so out loud. Two files for one pair is
    an error rather than a silent choice of whichever the filesystem returned
    first.
    """
    found: dict[tuple[str, str], Path] = {}
    directory = Path(raw_dir) / "bcc_xlsx"
    if not directory.exists():
        return found
    for path in sorted(directory.iterdir()):
        m = VALID_XLSX.match(path.name)
        if not m:
            continue
        key = (m.group("currency"), m.group("segment"))
        if key in found:
            raise GuardFailed(
                f"two files for {key}: {found[key].name} and {path.name}. "
                f"Keep one and rename the other with an .expired suffix."
            )
        found[key] = path
    return found


def load_bcc(raw_dir: Path, currency: str) -> dict[str, dict[str, float]]:
    """``{date: {segment: rate}}`` for one currency, from the cached response."""
    path = bcc_path(raw_dir, currency)
    if not path.exists():
        raise SystemExit(
            f"{path} is missing. Run 'python data/fetch_bcc.py' first."
        )
    rows = parse_bcc_rows(json.loads(path.read_text(encoding="utf-8")))
    return {r["date"]: {tag: r[tag] for tag in SEGMENTS} for r in rows}


def publication_days(record: dict[str, dict[str, float]]) -> list[str]:
    """The dates the API returned, sorted. prereg §3.2's estimator domain.

    A separate function with a name rather than ``sorted(record)`` at four call
    sites, because the rule it encodes is a registered one and a rule with no
    name gets dropped in a refactor.
    """
    return sorted(record)


# ---------------------------------------------------------------------------
# Channels, reconstructed rather than retrieved
# ---------------------------------------------------------------------------


def channel_quote(base: float, channel: str) -> tuple[float | None, float | None]:
    """``(bid, ask)`` for one channel, as ``base * k``.

    Returns ``None`` on a side the channel does not publish. A caller that wants
    a two-sided quote has to say so and handle the absence; defaulting the
    missing side to the present one would manufacture a zero spread on a service
    that has no second direction at all.
    """
    ks = MARKUP_SCHEDULE[channel]
    bid = base * ks["compra"] if "compra" in ks else None
    ask = base * ks["venta"] if "venta" in ks else None
    return bid, ask


def two_sided_channels() -> tuple[str, ...]:
    """Channels publishing both a buy and a sell, so ``S + S'`` exists on them."""
    return tuple(
        name for name, ks in MARKUP_SCHEDULE.items()
        if "compra" in ks and "venta" in ks
    )


def friction_bands() -> dict[str, float]:
    """``log(k_venta / k_compra)`` per two-sided channel: the round-trip width."""
    return {
        name: math.log(MARKUP_SCHEDULE[name]["venta"]
                       / MARKUP_SCHEDULE[name]["compra"])
        for name in two_sided_channels()
    }


def widest_friction_band() -> tuple[str, float]:
    """The widest round trip the table offers, and which channel it is.

    B6-6 divides by this. It is computed from the published schedule rather than
    written down as a number, so that a revision to the schedule moves the
    criterion's denominator instead of silently leaving it stale.
    """
    bands = friction_bands()
    name = max(bands, key=lambda k: bands[k])
    return name, bands[name]


def published_column(base: float, name: str) -> float:
    """The value the table publishes for one column key on one date.

    **The base is returned verbatim and every other column is truncated.** The
    distinction is not cosmetic and it is not a guess. ``base * 1.0 * 1e4`` is
    not exactly an integer in binary, so putting the base through the truncation
    would drop a digit from it: ``136.908`` becomes ``136.9079``.

    That the publisher does exactly that to its *channels* is visible in the
    table. ``transferencia_de_divisas_a_cup`` has ``k = 1.000``, and on 59 of the
    1 428 published rows it differs from the base column in the last place, in
    every case matching ``published_from(base, 1.0)`` rather than the base. So
    every channel goes through the same float multiply-and-truncate, including
    the one that multiplies by one, and the base column is the untruncated
    reference the channels are derived from.
    """
    if name == "base":
        return base
    channel, side = name.split(":")
    return published_from(base, MARKUP_SCHEDULE[channel][side])


def column_multipliers() -> dict[str, float]:
    """``{column: k}`` over the base and all nineteen channel columns.

    The base is ``1.0`` and is present, because B6-3's pairs include it: the
    reference rate is one of the twenty columns and excluding it would drop
    nineteen of the one hundred and ninety pairs.
    """
    out = {"base": 1.0}
    for name, ks in MARKUP_SCHEDULE.items():
        for side, k in ks.items():
            out[f"{name}:{side}"] = k
    return out


def index_tolerance(rate_a: float, rate_b: float) -> float:
    """B6-3's tolerance for one pair on one date, derived not chosen.

    The index part is ``2 (log r_b - log r_a)``. A published value of magnitude
    ``r`` is truncated, so it carries absolute error up to ``PUBLISHED_ULP``, its
    log carries up to ``PUBLISHED_ULP / r``, and the pair carries up to

        2 * PUBLISHED_ULP * (1/r_a + 1/r_b)

    which is about ``1.7e-5`` between two segment-I columns near 24 and about
    ``6.4e-7`` between two segment-III columns near 624. **A single registered
    constant would be loose on one and wrong on the other**, which is
    ``MEASUREMENT.md`` rule 6: the tolerance is the same order as the effect, and
    what it is relative to is written down beside it.

    **This is the fallback form of B6-3, not its primary form.** Because
    ``published_from`` reproduces the publisher's truncation exactly, the
    criterion can compare against the exact expected published values and needs
    no tolerance at all. This function exists for the diagnostic that reports how
    far the truncated columns sit from the ideal ``2 log(k_b/k_a)``, and for the
    case where guard 1 shows the truncation model has stopped holding.
    """
    if rate_a <= 0 or rate_b <= 0:
        raise ValueError(f"non-positive rate {rate_a} {rate_b}")
    return 2.0 * PUBLISHED_ULP * (1.0 / rate_a + 1.0 / rate_b)


def implied_cross(usd: dict[str, dict[str, float]],
                  eur: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """``{date: {segment: EUR/USD}}`` implied by the table's own two currencies.

    prereg §2.4: the BCC derives its euro rate by applying one international
    cross to the segment's dollar number, so this quantity should not depend on
    the segment. B6-5 measures that rather than assuming it, and B6-4 checks the
    result against a source outside Cuba.
    """
    out: dict[str, dict[str, float]] = {}
    for when in sorted(set(usd) & set(eur)):
        out[when] = {
            tag: eur[when][tag] / usd[when][tag] for tag in SEGMENTS
        }
    return out


# ---------------------------------------------------------------------------
# The graph, and the four readings of it. prereg §5, B6-6.
# ---------------------------------------------------------------------------

#: The two positions. Pesos and dollars, in that order, so that
#: ``vertex(cls, pos) = cls * N_POSITIONS + pos`` matches ``product_graph.vertex``
#: and ``directed.directed_square``.
CUP, USD_POS = 0, 1
N_POSITIONS = 2


def vertex(cls_index: int, position: int) -> int:
    return cls_index * N_POSITIONS + position


#: The four readings of the same table, prereg §5 B6-6.
#:
#: ``frozen`` says which position edges a frozen segment gets; ``agent_at`` says
#: at which positions the zero-weight agent edges exist. **The whole disagreement
#: between the readings is in these two fields**, which is why they are written
#: as configuration rather than as four builders: a reader comparing two rows
#: sees the entire difference.
#:
#: ``maximal`` believes the published columns. ``directed`` believes the
#: regulation and is the registered reading: a peso is a peso, so the agent edge
#: at ``CUP`` is two-way, while a segment-I dollar is tied to the licensed
#: operation, so there is no agent edge at ``USD``. The remaining two isolate
#: what each assumption contributes.
MODELS: dict[str, dict[str, object]] = {
    "maximal": {
        "frozen": "both",
        "agent_at": (CUP, USD_POS),
        "note": "believe the published columns; agent edges free everywhere",
    },
    "maximal_acquire_only": {
        "frozen": "cup_to_usd",
        "agent_at": (CUP, USD_POS),
        "note": "only the acquisition direction, but agent edges still free",
    },
    "directed": {
        "frozen": "cup_to_usd",
        "agent_at": (CUP,),
        "note": "the registered reading: entitlement acquires, and does not transfer",
    },
    "directed_flipped": {
        "frozen": "usd_to_cup",
        "agent_at": (CUP,),
        "note": "robustness: the entitlement surrenders rather than acquires",
    },
}


def build_segment_field(quotes: dict[str, tuple[float, float]],
                        keys: tuple[str, ...], model: str):
    """The directed field on ``Gamma`` for one date, under one reading.

    ``quotes`` maps a segment to ``(bid, ask)`` from the channel in use, with
    ``bid`` the rate at which the counter buys a dollar and ``ask`` the rate at
    which it sells one, so ``bid < ask``.

    The position weights are ``orphan_squares``' and are not restated here; a
    second copy of ``omega(CUP -> USD) = -log(ask)`` would be a second truth
    about what a quote means.

    **The agent legs are written in explicitly where they exist and omitted
    where they do not.** Omission is the point: ``DirectedField.value`` raises on
    an absent edge rather than falling back to the reverse, so a caller that
    tries to walk a square through a missing agent leg fails instead of
    returning a number (``b4`` §5.2).
    """
    from monetary_topology import directed
    from monetary_topology.orphan_squares import edge_weights

    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {list(MODELS)}")
    frozen = MODELS[model]["frozen"]
    agent_at = MODELS[model]["agent_at"]

    weights: dict[tuple[int, int], float] = {}
    for a, key in enumerate(keys):
        bid, ask = quotes[key]
        fwd, rev = edge_weights(bid, ask)
        one_way = key in ONE_WAY_SEGMENTS
        if not one_way or frozen in ("both", "cup_to_usd"):
            weights[(vertex(a, CUP), vertex(a, USD_POS))] = fwd
        if not one_way or frozen in ("both", "usd_to_cup"):
            weights[(vertex(a, USD_POS), vertex(a, CUP))] = rev

    for a in range(len(keys)):
        for b in range(len(keys)):
            if a == b:
                continue
            for pos in agent_at:
                weights[(vertex(a, pos), vertex(b, pos))] = 0.0
    return directed.DirectedField(weights, len(keys) * N_POSITIONS)


# ---------------------------------------------------------------------------
# The external referee: the ECB's daily euro reference rate
# ---------------------------------------------------------------------------

#: The one series B6-4 reads, in its two spellings, **which are not the same
#: string and cost one HTTP 400 to learn.**
#:
#: SDMX addresses a series as ``/service/data/{flow}/{key}``, so the path carries
#: ``EXR`` once as the flow and then ``D.USD.EUR.SP00.A`` as the key. The ``KEY``
#: column of the response carries the two joined, ``EXR.D.USD.EUR.SP00.A``.
#: Putting the joined form into the path yields
#: ``/service/data/EXR/EXR.D.USD.EUR.SP00.A``, which is well formed, looks right,
#: and is rejected. Both spellings live here so that the URL builder and the
#: response validator cannot drift apart, and ``ECB_URL`` below is the single
#: place either is assembled.
ECB_FLOW = "EXR"
ECB_SERIES = "D.USD.EUR.SP00.A"
ECB_KEY = f"{ECB_FLOW}.{ECB_SERIES}"


def ecb_url(start: date, end: date) -> str:
    """The verified endpoint, assembled in one place.

    Reproduces, character for character, the request verified on 2026-08-12::

        https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
            ?startPeriod=2026-08-01&endPeriod=2026-08-12&format=csvdata
    """
    return (
        f"https://data-api.ecb.europa.eu/service/data/{ECB_FLOW}/{ECB_SERIES}"
        f"?startPeriod={start.isoformat()}&endPeriod={end.isoformat()}"
        f"&format=csvdata"
    )

#: The ECB publishes to four decimals, same as the BCC.
ECB_DECIMALS = 4

#: Anything outside this is not a EUR/USD quote.
ECB_PLAUSIBLE = (0.5, 2.5)


def parse_ecb_rows(text: str) -> dict[str, float]:
    """``{date: USD per EUR}`` from the ECB's ``csvdata`` response.

    Endpoint, verified 2026-08-12::

        https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
            ?startPeriod=YYYY-MM-DD&endPeriod=YYYY-MM-DD&format=csvdata

    Free, no key, no registration.

    Two ways this differs from the BCC's response, each a place to get it wrong.

    **It is CSV with thirty-two columns, of which two are the data.** The rest are
    SDMX metadata. The key is asserted rather than assumed: ``EXR`` holds many
    series with this shape and a neighbouring one would parse perfectly and mean
    something else.

    **It carries business days only.** Weekends and TARGET holidays are absent,
    so a Cuban publication day may have no reference at all. That is coverage,
    not a gap to be filled, and B6-4 reports it rather than interpolating.
    """
    import csv as _csv
    import io as _io

    reader = _csv.DictReader(_io.StringIO(text))
    if reader.fieldnames is None or "TIME_PERIOD" not in reader.fieldnames:
        raise ValueError("no TIME_PERIOD column; this is not the csvdata format")
    out: dict[str, float] = {}
    for i, row in enumerate(reader):
        key = row.get("KEY", "")
        if key != ECB_KEY:
            raise ValueError(f"row {i}: KEY is {key!r}, expected {ECB_KEY!r}")
        when = row["TIME_PERIOD"]
        try:
            date.fromisoformat(when)
        except ValueError as exc:
            raise ValueError(f"row {i}: TIME_PERIOD {when!r} is not ISO") from exc
        raw = row["OBS_VALUE"]
        if raw == "":
            continue
        value = float(raw)
        if not ECB_PLAUSIBLE[0] <= value <= ECB_PLAUSIBLE[1]:
            raise ValueError(f"row {i}: {value} outside {ECB_PLAUSIBLE}")
        if when in out:
            raise ValueError(f"row {i}: {when} appears twice")
        out[when] = value
    if not out:
        raise ValueError("no observations in the response")
    return out


def ecb_path(raw_dir: Path) -> Path:
    return Path(raw_dir) / "ecb_eurusd.csv"


def load_ecb(raw_dir: Path) -> dict[str, float]:
    path = ecb_path(raw_dir)
    if not path.exists():
        raise SystemExit(
            f"{path} is missing. Run 'python data/fetch_ecb.py' first."
        )
    return parse_ecb_rows(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The XLSX export, read with the standard library
# ---------------------------------------------------------------------------

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _column_index(ref: str) -> int:
    """``'AB12' -> 27``. Zero-based, so a sparse row can be placed correctly."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - ord("A") + 1)
    return n - 1


def read_xlsx_table(path: Path) -> tuple[list[str], list[list[object]]]:
    """``(header, rows)`` from the first worksheet, using ``zipfile`` only.

    **No new dependency.** ``pyproject.toml`` pins numpy and matplotlib, and an
    xlsx is a zip of XML; adding ``openpyxl`` so that a validator can read a
    twenty-column sheet once would be a dependency the whole project then
    carries. Shared strings, inline strings and numbers are handled; anything
    else raises rather than being coerced, because a cell type this reader does
    not know about is a change in the export and should stop the run.
    """
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))

    table: list[list[object]] = []
    for row in sheet.iter(f"{_NS}row"):
        cells: dict[int, object] = {}
        for cell in row.findall(f"{_NS}c"):
            ref = cell.get("r") or ""
            kind = cell.get("t")
            if kind == "inlineStr":
                node = cell.find(f"{_NS}is")
                value: object = "".join(
                    t.text or "" for t in node.iter(f"{_NS}t")
                ) if node is not None else ""
            else:
                node = cell.find(f"{_NS}v")
                if node is None or node.text is None:
                    continue
                if kind == "s":
                    value = shared[int(node.text)]
                elif kind in (None, "n"):
                    value = float(node.text)
                elif kind == "str":
                    value = node.text
                else:
                    raise ValueError(f"{path.name}: unknown cell type {kind!r}")
            cells[_column_index(ref)] = value
        if not cells:
            continue
        table.append([cells.get(i) for i in range(max(cells) + 1)])

    if not table:
        raise ValueError(f"{path.name}: no rows")
    header = [str(h) if h is not None else "" for h in table[0]]
    return header, table[1:]


# ---------------------------------------------------------------------------
# The guards. prereg §6.
# ---------------------------------------------------------------------------


class GuardFailed(Exception):
    """A registered assertion about the source did not hold.

    Raised rather than reported. A guard is not a criterion: a guard that fires
    means the source is not what the pre-registration says it is, and every
    number downstream is about a different object.
    """


def _ticks(value: float) -> int:
    """A published value as an integer count of last-place units.

    Comparing integers rather than floats is what makes guard 1 an exact
    equality: a four-decimal value has no exact binary representation, so
    ``a == b`` on the floats would be a tolerance test wearing an equals sign.
    """
    return round(value * 10.0 ** PUBLISHED_DECIMALS)


def guard_schedule_invariant(header: list[str], rows: list[list[object]],
                             label: str) -> dict[str, int]:
    """Guard 1. Every channel equals ``published_from(base, k)``, exactly.

    Not "within rounding". The publisher truncates at four decimals and
    ``published_from`` reproduces that, so this is a strict equality on integer
    last-place counts and there is no tolerance in it to be widened later.

    Returns the count of exact matches per column, so a caller can print that
    the guard did work rather than only that it did not fail. A guard whose
    output is indistinguishable between "checked everything" and "checked
    nothing" is the failure mode ``PROJECT_PLAN.md`` §11.11 collects.

    **A revision to the markup schedule mid-window must stop the run** rather
    than be averaged over: ``MARKUP_SCHEDULE`` would then be piecewise, and
    B6-3's exact form would have to be withdrawn in favour of
    ``index_tolerance`` before anything is read.
    """
    if not header or header[0] != "Fecha":
        raise GuardFailed(f"{label}: first column is {header[:1]}, expected Fecha")
    base_col = 1
    checked: dict[str, int] = {}
    for key, column in XLSX_HEADERS.items():
        if column not in header:
            raise GuardFailed(f"{label}: no column {column!r}")
        j = header.index(column)
        k = MARKUP_SCHEDULE[key[0]][key[1]]
        n = 0
        for row in rows:
            base = row[base_col]
            value = row[j] if j < len(row) else None
            if not isinstance(base, float) or not isinstance(value, float):
                raise GuardFailed(f"{label}: non-numeric cell in {column!r}")
            if _ticks(value) != _ticks(published_from(base, k)):
                raise GuardFailed(
                    f"{label}: {column!r} is {value} where base {base} times "
                    f"{k} truncates to {published_from(base, k)}; the markup "
                    f"schedule or the publisher's arithmetic has changed"
                )
            n += 1
        if n == 0:
            raise GuardFailed(f"{label}: {column!r} has no rows to check")
        checked[column] = n
    return checked


def guard_paths_reconcile(api: dict[str, dict[str, float]],
                          header: list[str], rows: list[list[object]],
                          segment: str, label: str,
                          snapshot: date) -> dict[str, object]:
    """Guard 2. The XLSX is the API forward-filled, and nothing more.

    Two assertions, and the second is the one that matters:

    * a date in both must carry the same value, to the published rounding;
    * a date in the XLSX only, **after** the first published date, must equal the
      previous published value: a forward fill;
    * a date in the XLSX only **before** the first published date is a
      **back fill**, reported separately and never compared.

    **The third case is not a variant of the second and treating it as one was a
    silent hole.** A forward fill copies a value that existed; a back fill
    manufactures one for a day on which the source published nothing, and the
    yuan showed why that matters: its API record begins on 2025-12-31 while its
    export carries every day from 2025-12-18, so thirteen days of its history
    are the export's construction rather than the bank's publication. Read as
    forward fills they produced eight B6-8 failures that were an artefact of the
    reader.

    A date present in both on which the two disagree is an error and not a fill.
    A date in the XLSX only after the first publication that does not match the
    previous published value is not a forward fill either.
    """
    if segment not in SEGMENTS:
        raise GuardFailed(f"{label}: unknown segment {segment!r}")
    if not header or header[0] != "Fecha":
        raise GuardFailed(f"{label}: first column is {header[:1]}, expected Fecha")

    xlsx: dict[str, float] = {}
    for row in rows:
        when, base = row[0], row[1]
        if not isinstance(when, str) or not isinstance(base, float):
            raise GuardFailed(f"{label}: unreadable row {row[:2]!r}")
        xlsx[when] = base

    filled: list[str] = []
    provisional: list[str] = []
    back_filled: list[str] = []
    published = sorted(api)
    if not published:
        raise GuardFailed(f"{label}: the API record is empty")
    first_published = published[0]
    for when in sorted(xlsx):
        if date.fromisoformat(when) >= snapshot:
            # A row at or after the export's own date may be either: the day's
            # rate had not been published when the export was taken, so the site
            # filled it forward; or it had been published, and the row is real.
            # **Both are legitimate and which one it is depends on the minute the
            # download happened**, which is not a property of the source. So the
            # row is admitted if it matches either, and refused only if it
            # matches neither.
            earlier = [p for p in published if p < when]
            allowed = []
            if when in api:
                allowed.append(api[when][segment])
            if earlier:
                allowed.append(api[earlier[-1]][segment])
            if allowed and not any(
                _ticks(xlsx[when]) == _ticks(value) for value in allowed
            ):
                raise GuardFailed(
                    f"{label}: {when} is at or after the snapshot {snapshot} "
                    f"and reads {xlsx[when]}, which is neither the day's "
                    f"published value nor the previous one "
                    f"({', '.join(str(v) for v in allowed)})"
                )
            provisional.append(when)
            continue
        if when in api:
            got, want = xlsx[when], api[when][segment]
            if _ticks(got) != _ticks(want):
                raise GuardFailed(
                    f"{label}: {when} XLSX {got} against API {want}"
                )
            continue
        if when < first_published:
            # The export carries a complete calendar from the stage's window
            # start, so a currency that joined later has its pre-history
            # manufactured. Recorded, never compared, and excluded downstream.
            back_filled.append(when)
            continue
        earlier = [p for p in published if p < when]
        want = api[earlier[-1]][segment]
        if _ticks(xlsx[when]) != _ticks(want):
            raise GuardFailed(
                f"{label}: {when} is in the XLSX only but is {xlsx[when]}, "
                f"not the previous published {want}; it is not a forward fill"
            )
        filled.append(when)
    return {
        "xlsx_days": len(xlsx),
        "api_days": len(api),
        "filled_days": sorted(filled),
        "provisional_days": sorted(provisional),
        "back_filled_days": sorted(back_filled),
        "first_published": first_published,
        "snapshot": snapshot.isoformat(),
    }


def guard_fixed_in_dollars(usd: dict[str, dict[str, float]],
                           eur: dict[str, dict[str, float]]) -> dict[str, object]:
    """Guard 3. The fixed segments are fixed **against the dollar**.

    ``USD`` segments I and II must be constant over the window; ``EUR`` segments
    I and II must **not** be, because their CUP value inherits the international
    cross. An implementation that finds the euro fixed segments constant has a
    bug, and this is the cheapest place for it to surface.
    """
    out: dict[str, object] = {}
    for tag in ONE_WAY_SEGMENTS:
        usd_values = {usd[d][tag] for d in usd}
        eur_values = {eur[d][tag] for d in eur}
        if len(usd_values) != 1:
            raise GuardFailed(
                f"USD segment {tag} is not constant: {len(usd_values)} values"
            )
        if len(eur_values) < 2:
            raise GuardFailed(
                f"EUR segment {tag} is constant; the peg is against the dollar "
                f"and the euro leg must move with the cross"
            )
        out[f"usd_{tag}"] = next(iter(usd_values))
        out[f"eur_{tag}_distinct"] = len(eur_values)
    return out


def guard_quotation_orientation(table: dict[str, dict[str, float]],
                                label: str) -> dict[str, float]:
    """Guard 6. Each currency's ladder points the way ``QUOTATION`` says.

    The ladder is ``rate(II)/rate(I)`` and it is a regulated constant: the two
    fixed rates are 24 and 120, so a direct currency gives 5 and an indirect one
    gives one fifth. Nothing external is consulted.

    **This is a guard and not the means of discovery.** The orientation comes
    from the bank's own footnote; this asserts that the table still behaves the
    way the footnote says, so a change of convention stops the run instead of
    silently inverting one row of B6-8.
    """
    seen: dict[str, float] = {}
    anchor = table[BASE_CURRENCY]
    reference = anchor["II"] / anchor["I"]
    for code, rates in table.items():
        ladder = rates["II"] / rates["I"]
        seen[code] = ladder
        want = reference if QUOTATION[code] == "direct" else 1.0 / reference
        if abs(ladder / want - 1.0) > 1e-3:
            raise GuardFailed(
                f"{label}: {code} has ladder {ladder:.6f} where "
                f"{QUOTATION[code]} quotation gives {want:.6f}; the bank has "
                f"changed how it publishes this currency"
            )
    return seen


def guard_pair_is_across_segments(left: str, right: str) -> None:
    """Guard 4. No headline square with both legs inside one segment.

    prereg §2.2. Inside a segment the index part is ``2 log(k_b/k_a)``, the same
    constant on every date. B6-3 uses that on purpose and calls it a floor; every
    other caller has to come through here.
    """
    if left == right:
        raise GuardFailed(
            f"both legs are segment {left}; the index part there is a "
            f"construction identity (prereg 2.2). B6-3 is the only caller "
            f"permitted to use it, and it does so by a different route."
        )


def guard_no_imputation(segment: str, side: str) -> None:
    """Guard 5. A one-way segment has no second direction to ask for.

    ``b4`` §5.2: a number computed from a one-way edge by imputing the missing
    direction has imputed exactly the quantity in dispute. There is no code path
    that supplies one, and this function exists so that an attempt raises with
    the reason attached rather than returning a plausible float.
    """
    if segment in ONE_WAY_SEGMENTS:
        raise GuardFailed(
            f"segment {segment} has no return leg, so its {side} side is "
            f"undefined rather than missing. b4 5.2 prohibits supplying it "
            f"from another class, from a lag, or from a model."
        )
