"""Bolivia's official and parallel exchange rates, for stage B15.

``docs/b15_bolivia_prereg.md`` is the authority and it is **sealed**: every
threshold in §6.1 is reproduced below verbatim and none of them may be edited
here. Changing one is a §12 changelog action in that document, not an edit in
this file.

``docs/bolivia_availability.md`` §6 is the other authority, and it is the one
that governs what this module is allowed to believe. **Everything known about
these sources on the day this was written came through a tool that returns a
language model's summary of a page rather than the page.** That is enough to
know an endpoint exists and what shape its header is. It is not enough to know
one number, and one such summary reported a value for a date that has not
happened. So this module is written to *find out* what the sources serve rather
than to assert it, and every place where it would otherwise have to guess is a
recorded fact in the manifest instead of a constant here.

What that costs, concretely
---------------------------

**The payload format of S1 is not known and is sniffed.** ``xls.php`` is a PHP
endpoint whose name is a filename and not a promise. It may serve an OLE2
workbook, a zipped OOXML workbook, or an HTML table with a spreadsheet
content-type, which is the commonest of the three from an endpoint shaped like
this one. ``sniff`` reports which, ``guard_truncation`` applies the check that
belongs to that format, and nothing downstream assumes.

**So the ODS of the same year is fetched beside the XLS.** The BCB serves
``xls.php``, ``ods.php`` and ``pdf.php`` for one year. ODS is a zip of XML and
is parseable from the standard library alone; a BIFF workbook is not, and this
project's dependency set is ``numpy`` and ``matplotlib``. Fetching both costs
three extra requests against a registered budget of "low tens" and buys two
things: a parse path that exists whatever ``xls.php`` turns out to serve, and
**B15-2's known-answer arm as an independent-format check rather than as a
replay of bytes fetched here.** Two exports of one year by one publisher through two
serialisers must agree row for row, and if they do not, that is the instrument
reporting on itself. ``b15_bolivia_prereg.md`` §3.1 names ``xls.php`` as S1 and
that remains the source of record; the ODS is retrieval machinery under §10 and
is registered as such in the manifest.

**Nothing here prints a Bolivian rate.** Row counts, spans, digests, formats and
guard verdicts, and no value. The stage's whole claim is that its register
closed before its data existed, and B15-3 and B15-4 are decided from the
archive rather than from a look at it. Keeping the retrieval layer silent about
levels costs nothing and removes the one way that claim could quietly stop being
true. It is a property of this file, not a rule imposed on anything downstream.

The three elTOQUE lessons, applied
-----------------------------------

``b6b_eltoque_prereg.md`` §12 records them and they are not re-learned here.

**A documented rate limit is a claim and the measured one is the fact.**
elTOQUE's published specification said 60 per minute; the key carried ten per
156 seconds, a twenty-fourth of it, and the difference was ten hours against
thirty-five minutes. So ``--probe-headers`` exists: one request per source,
every header printed, nothing written, before any pass is planned.

**A negative ``Retry-After`` is not a delay.** One came back ``-11``. Clamping
it to a second is an immediate retry wearing a delay's clothes.
``throttle_wait`` takes ``Retry-After``, then ``X-RateLimit-Reset``, then a
backoff of this file's own, **taking each only when it is positive**.

**A header that does not decrement cannot pace a run.**
``X-RateLimit-Remaining`` read ``10`` on all fifteen probe requests including
the three that were refused. Pacing here comes from a floor and from the
publisher's own stated politeness, and the headers are recorded and disbelieved.

What this file will not do
---------------------------

**It does not delete.** ``retire`` renames with an ``.expired`` suffix and
leaves the file in place. **Nothing in this repository deletes**, a discipline written after a deletion
cost several hours of downloads.

**It does not fill.** A date the source does not serve is a date the source does
not serve, in either direction, at any resolution. ``guard_no_fill``.

**It does not read a truncated file as a short one.** ``guard_truncation``
exists because it already happened: the first read of ``all.csv`` returned 1,162
lines ending in the middle of a number, and a reader without this check would
have recorded 2024-08-01 as the end of a series that runs to today.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import zipfile
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Registered constants. `b15_bolivia_prereg.md` §6.1, copied verbatim.
#
# **These are sealed.** Four of them are B6's own values carried over unchanged
# so that the two carriers are judged by one ruler, and that is the entire point
# of the stage: A_SHARE, CRITICAL_SPREAD, NULL_DRAWS and NULL_SEED are B6-15's
# and B6-14's. Editing any value in this block silently makes B15 a different
# experiment from the one that was registered while nothing had been
# downloaded. If one has to move, it moves in that document's §12 with the old
# value left visible, and only then here.
# ---------------------------------------------------------------------------

WINDOW_OPEN_DATE = date(2024, 7, 21)      # S3's first observation
EVENT_DATE = date(2026, 6, 29)            # first day the new regime governs
SIGNING_DATE = date(2026, 6, 26)          # RM 245 and RD 88/2026
CUSTOMS_SWITCH_DATE = date(2026, 7, 6)    # Art. 20 leaves the frozen 6.96
TZ = "America/La_Paz"                     # UTC-4, no DST
ORDINARY_SPAN = 86_399                    # asserted on every day, not assumed
STATUTORY_SPREAD = 0.10                   # RD 88/2026 Art. 6, bolivianos
SPREAD_SHARE = 0.99                       # B15-5
UNCROSSED_SHARE = 0.99                    # B15-3, the deciding orientation
CROSSED_SHARE_MAX = 0.50                  # B15-3, the rejected orientation
TCO_RECOMPUTE_SHARE = 0.99                # B15-6
A_SHARE = 0.95                            # B15-7, B6-15's threshold unchanged
CRITICAL_SPREAD = 0.02                    # B15-7, B6-15's threshold unchanged
CYCLE_DETERMINED = 0.99                   # B15-8
AGREEMENT_SHARE = 0.50                    # B15-11
NULL_DRAWS, NULL_SEED = 999, 0            # B15-10, B6-B's values

#: The one honest exposure, named here so that a reader of the code meets it.
#:
#: **CLOSED 2026-08-19.** ``STATUTORY_SPREAD`` was registered from a summary of
#: the BCB's PDF rather than from the PDF, and ``b15_bolivia_prereg.md`` §11 row
#: two recorded it as the register's one honest exposure. The PDF was then
#: supplied and read from disk, and Art. 6 says what the summary said it says,
#: word for word, so **B15-5 and B15-7 stand exactly as registered and no value
#: moved.** Kept here rather than deleted because the grep that finds this
#: constant should find the outcome and not only the worry.
STATUTORY_SPREAD_SOURCE = (
    "RD 88/2026 Art. 6, read from the PDF on 2026-08-19: 'Se denomina valor "
    "referencial de venta del USD al que resulte de sumar al TCO 10 centavos "
    "de boliviano. Las Entidades Financieras no podran vender USD por encima "
    "del valor referencial de venta.' Confirms the registered 0.10. "
    "b15_bolivia_prereg.md §11 and §12; readings in b15_bolivia_results.md §0."
)

# ---------------------------------------------------------------------------
# The day boundary. §3.3.
# ---------------------------------------------------------------------------

#: Bolivia has kept UTC-4 with no daylight saving since 1932 and observes none
#: in the registered window. **That is why ``ORDINARY_SPAN`` is a constant here
#: and was a per-day computation in ``cuba_informal``**, where a fall-back night
#: made one window 25 hours less a second and the API refused it after 310 days
#: of the same request shape.
#:
#: Written out rather than derived at run time so that a registered constant does
#: not depend on the host having ``tzdata`` installed, which it does not on the
#: author's machine. A test recomputes this from ``zoneinfo`` and fails if the
#: zone's history has moved, skipping with a note when ``tzdata`` is absent.
#: This is the same treatment ``HAVANA_FALL_BACK`` gets and for the same reason.
UTC_OFFSET_HOURS = -4
DST_TRANSITIONS: tuple[date, ...] = ()


def local_span_seconds(day: date) -> int:
    """Elapsed seconds in ``00:00:00`` to ``23:59:59`` local, on this date.

    Constant by the zone's own history rather than by assumption, and asserted
    per day by ``guard_span`` because the assertion is free and the equivalent
    assumption was wrong on the other carrier.
    """
    del day
    return ORDINARY_SPAN


# ---------------------------------------------------------------------------
# The sources. §3.1.
# ---------------------------------------------------------------------------

BCB_YEAR_URL = "https://www.bcb.gob.bo/tiposDeCambioHistorico/{fmt}.php?anio={year}"

#: The years the registered window touches. 2024-07-21 to today, so three files.
#: The selector reaches back to 1940 and the whole series is under 90 requests
#: if it is ever wanted; it is not wanted, and asking for it would be a request
#: budget spent on a span no criterion reads.
BCB_YEARS = (2024, 2025, 2026)

#: S1 as registered, and the format that is actually parseable beside it. §10.
BCB_FORMATS = ("xls", "ods")

S3_ALL_URL = "https://api.dolarbluebolivia.click/v1/chart/all.csv"

#: The header ``bolivia_availability.md`` §3.2.1 records. **Asserted, not
#: assumed**: if the file arrives with a different header the run stops, because
#: every criterion in arm II is a statement about which of these columns is
#: which and a silently renamed column would be answered rather than noticed.
S3_ALL_HEADER = ("datetime", "official_buy", "official_sell",
                 "blue_buy", "blue_sell")

#: **A guess, and marked as one.** ``b15_bolivia_prereg.md`` §2.4 and §6.2 refer
#: to an ``oficial.csv`` from this publisher carrying a ``kind`` column with at
#: least ``referencial`` and ``unificado``, and ``guard_kind_column`` is
#: registered against it. The URL was never seen. It is tried once, and a
#: refusal is recorded as a fact rather than raised, so that the manifest can
#: say honestly whether ``guard_kind_column`` was exercised at all.
S3_OFICIAL_URL = "https://api.dolarbluebolivia.click/v1/chart/oficial.csv"

#: The attribution the publisher's terms ask for, sent on every request and
#: recorded in the manifest. §10.
S3_ATTRIBUTION = "Powered by dolarbluebolivia.click"

#: The terms position, in full, because §10 registers the tension rather than
#: resolving it quietly. Reuse is permitted with the attribution above,
#: commercial use is allowed, the public endpoint carries no visit limit and the
#: publisher asks for no polling faster than 60 seconds, **and the same terms
#: say bulk downloads and historical data require registration for a beta API.**
#: ``/v1/chart/all.csv`` is served without a key and is therefore public. The
#: two statements are in tension, and the registered resolution is to register
#: or to fall back to S4 plus S5 **rather than to pull quietly**. So the fetcher
#: will not pull this file without ``--s3-bulk-acknowledged`` on the command
#: line: I resolve it explicitly and the flag is where that is recorded.
S3_TERMS = (
    "dolarbluebolivia.click permits reuse with attribution and commercial use, "
    "sets no visit limit on the public endpoint, asks for no polling faster "
    "than 60 seconds, and states that bulk downloads and historical data "
    "require registration for its beta API. /v1/chart/all.csv is served "
    "without a key. bolivia_availability.md §3.2.1, b15_bolivia_prereg.md §10."
)

#: S2. `b15_bolivia_prereg.md` §3.1: per bank and per rate tier, the rate, the
#: number of operations and the amount in USD, **compra only**, with a CSV
#: export and a date selector running from 2026-06-26. It is the microdata
#: behind Art. 5.I and the only source that can settle B15-6, which is the
#: formal leg's zero calibration and the one criterion §7.1 says would be the
#: most interesting single result this stage could return if it failed.
#:
#: **The query parameters are not known.** The page carries a form and the form
#: names are what has to be read; `--probe-s2` fetches the page, stores it, and
#: prints every input, select and form action it finds, so the parameters come
#: from the page rather than from a guess.
S2_URL = "https://www.bcb.gob.bo/tco_reporte_detalle_historico.php"

#: S2's two endpoints, read off the page's own form on 2026-08-19 rather than
#: guessed. `--probe-s2` printed them and they are:
#:
#: - the detail page takes `?fecha=YYYY-MM-DD` and returns **one day's
#:   microdata**: a grid of rate tier by bank carrying the operation count and
#:   the amount in USD in each cell, a `TOTAL` row, and a `TCO` row giving each
#:   bank's own weighted average and the aggregate;
#: - `tco_tcreferencial_descargar_csv.php` takes `?desde=&hasta=` and returns
#:   the daily series in one request.
#:
#: **The `fecha` on the detail page is the operations date, not the vigencia
#: date.** The page's default of 2026-08-18 carries a TOTAL BANCOS TCO of 11.52,
#: and 11.52 is what the aggregators file under 2026-08-19. That is Art. 5.III
#: read off two publishers at once and it is an independent confirmation of
#: B15-4's verdict from the BCB's own page.
S2_DETAIL_URL = "https://www.bcb.gob.bo/tco_reporte_detalle_historico.php"
S2_CSV_URL = "https://www.bcb.gob.bo/tco_tcreferencial_descargar_csv.php"

S4_URL = "https://paralelo.bo/api/v1/historical.csv"

#: `bolivia_availability.md` §3.2.2. Daily, from 2024-01-01, no key, CC-BY 4.0.
#: **Median only in history**, which is the elTOQUE limit again, so §2.2's
#: `guard_no_one_sided_in_friction` keeps it out of every spread, round trip and
#: cycle weight. It enters as an index series and as a check on the level, which
#: is what B15-11 needs it for.
S4_HEADER = ("date", "median_bob_per_usd")
S4_CITATION = "paralelo.bo (https://paralelo.bo), CC-BY 4.0"

#: `bolivia_availability.md` §3.2.3. The auditable one: every observation is
#: fixed by a commit, so the series can be reconstructed as of any past date and
#: a silent revision is visible in the history. B6-B had to build a manifest
#: with two digests a day to get a weaker version of this.
#:
#: **The branch is not known and is not guessed.** Both candidates are tried and
#: the one that answers is recorded, because a raw URL on the wrong branch
#: returns a 404 that reads exactly like a deleted file.
S5_REPO = "mauforonda/dolares"
S5_BRANCHES = ("main", "master")
S5_RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{name}"
S5_FILES = ("buy.csv", "sell.csv", "buy_oficial.csv", "sell_oficial.csv",
            "buy_oficial_completo.csv", "buy_oficial_monto.csv")

#: Politeness floors, per source, in seconds between requests. **Floors, not
#: rates**: a header asking for longer wins, a header asking for shorter is
#: recorded and ignored. S3's number is the publisher's own stated request; the
#: BCB states nothing, and five seconds against three requests is a rounding
#: error against being a good guest.
POLITE_FLOOR_SECONDS = {"bcb": 5.0, "dolarblue": 60.0,
                        "paralelo": 5.0, "github": 2.0}


#: B15-2's known answers, written down once and replayed on every run.
#:
#: **Recorded 2026-08-19 from the first retrieval**, which is the only moment at
#: which they can be recorded: before this the archive did not exist locally,
#: and after any later run they would be a copy of whatever is on disk rather
#: than a claim about it. `B6-10` is the precedent and the failure it catches is
#: a source that silently revises.
#:
#: The prefix digest is the one that means something. `all.csv` is a growing
#: archive, so its body digest moves whenever the publisher appends a quarter of
#: an hour; the digest of the records describing a past that has already closed
#: must not.
PROBE_RECORD = {
    "dolarblue_all.csv": {
        "sha256_prefix": ("39dd158ef40bb8ed2626a2d9a625301e"
                          "b8f97f641d8f4e921906b643ce0ecdb1"),
        "prefix_cutoff": "2026-06-29",
        "records_before_cutoff": 69_657,
        "first_record": "2024-07-21 17:36:42",
    },
}

#: **S1 carries no body digest here on purpose.** `ods.php` is a PHP export
#: rebuilt per request, so its bytes are not promised to be stable and a digest
#: over them would be a guard that cries on every run without ever having been
#: shown to mean anything. What is checked on S1 is content, and the content
#: check is `ADUANA_ANCHOR` below, which is stronger because its answer does not
#: come from the publisher being checked.

#: The one known answer that did not come from an endpoint, and therefore the
#: strongest one this stage has.
#:
#: `data/raw/bolivia/aduana_comunicado_2026-06_RM245.pdf` states
#: `el tipo de cambio de 6,96 Bs/USD vigente al 26/06/2026`. **Whatever reading
#: of S1's annual table is adopted, it must reproduce this cell**, and the
#: statement comes from a Bolivian state body rather than from a rate publisher.
#: `b15_bolivia_prereg.md` §3.4 registers it as the confirming check.
ADUANA_ANCHOR = {"day": 26, "month": "JUNIO", "venta": 6.96, "compra": 6.86,
                 "source": "aduana_comunicado_2026-06_RM245.pdf, §4.6"}


class GuardFailed(Exception):
    """A registered guard refused. Nothing downstream may run."""


# ---------------------------------------------------------------------------
# Format sniffing, and the truncation check that belongs to each format.
# ---------------------------------------------------------------------------

OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
ZIP_MAGIC = b"PK\x03\x04"
ZIP_EOCD = b"PK\x05\x06"
PDF_MAGIC = b"%PDF-"


def sniff(body: bytes) -> str:
    """What arrived, by its bytes and not by the URL that asked for it.

    An endpoint called ``xls.php`` is a filename, not a promise. The commonest
    thing a PHP export of this shape serves is an HTML table with a spreadsheet
    content-type, and reading that with a workbook parser fails in a way that
    looks like a corrupt download rather than like a wrong assumption.
    """
    if body.startswith(OLE2_MAGIC):
        return "ole2"
    if body.startswith(ZIP_MAGIC):
        return "zip"
    if body.startswith(PDF_MAGIC):
        return "pdf"
    head = body[:4096].lstrip()
    if head[:1] == b"<":
        return "html"
    try:
        text = body[:4096].decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = body[:4096].decode("latin-1")
        except UnicodeDecodeError:
            return "unknown"
    if "<html" in text.lower() or "<table" in text.lower():
        return "html"
    lines = text.splitlines()
    if lines and "," in lines[0]:
        return "csv"
    return "unknown"


def guard_truncation(body: bytes, fmt: str, declared_length: int | None,
                     label: str) -> dict[str, object]:
    """The payload is whole, by a check that belongs to its own format.

    **Written because it already happened.** The first read of ``all.csv``
    returned 1,162 lines ending in the middle of a number on 2024-08-01, and a
    reader without this check records that date as the end of a series that runs
    to today. ``b15_bolivia_prereg.md`` §6.2.

    Two independent checks where both are available, and the report says which
    ran. ``Content-Length`` is the strong one and is often absent under chunked
    transfer; the structural one is always available and is what catches a
    payload that was cut at a record boundary the transport was happy with.
    """
    report: dict[str, object] = {
        "format": fmt,
        "bytes": len(body),
        "declared_length": declared_length,
        "length_checked": declared_length is not None,
        "structural_check": None,
    }
    if declared_length is not None and len(body) != declared_length:
        raise GuardFailed(
            f"{label}: Content-Length says {declared_length:,} and "
            f"{len(body):,} arrived. That is a truncation, not a short file. "
            f"Nothing is written and nothing is read."
        )
    if len(body) == 0:
        raise GuardFailed(f"{label}: empty payload.")

    if fmt == "csv":
        report["structural_check"] = "last record complete"
        text = decode(body)
        lines = text.splitlines()
        if not text.endswith(("\n", "\r")):
            # Not fatal on its own. A file may legitimately end without a
            # newline, so the record-shape test below is what decides.
            report["ends_without_newline"] = True
        if len(lines) < 2:
            raise GuardFailed(f"{label}: {len(lines)} line(s); no records.")
        width = len(next(csv.reader([lines[0]])))
        last = next(csv.reader([lines[-1]]))
        if len(last) != width:
            raise GuardFailed(
                f"{label}: the header has {width} fields and the last record "
                f"has {len(last)}. The payload was cut inside a record. This "
                f"is the failure guard_truncation was written for."
            )
        # **Which columns are numeric is read from the file, not assumed.**
        # The first version asserted that every field after the first is a
        # number, which is a schema assumption wearing a wholeness check's
        # clothes. It fired on `oficial.csv`, whose last column is `kind` and
        # whose last record ends in the perfectly complete word `unificado`,
        # and it took the whole run's manifest down with it. A column is
        # checked only where the records before it are numeric.
        sample = [next(csv.reader([line])) for line in lines[1:-1][-200:]]
        sample = [row for row in sample if len(row) == width]
        numeric: list[int] = []
        categorical: list[int] = []
        for k in range(1, width):
            seen = [row[k] for row in sample if row[k]]
            if len(seen) < 5:
                continue                       # too little to say anything
            if all(_looks_numeric(v) for v in seen):
                numeric.append(k)
                if last[k] and not _looks_numeric(last[k]):
                    raise GuardFailed(
                        f"{label}: column {k} is numeric in every one of the "
                        f"{len(seen)} preceding records and the last record "
                        f"has {last[k]!r}. Cut inside a value."
                    )
                continue
            # **A string column still has a wholeness check, and it is a
            # better one.** A categorical column has a closed vocabulary, so a
            # last record ending in `unif` where every earlier row says
            # `unificado` is a cut and is detectable, while `not a number` says
            # nothing at all about it.
            vocabulary = set(seen)
            if len(vocabulary) > 20:
                continue                       # free text, nothing to check
            categorical.append(k)
            if last[k] and last[k] not in vocabulary:
                raise GuardFailed(
                    f"{label}: column {k} takes {sorted(vocabulary)} in the "
                    f"preceding records and the last record has {last[k]!r}, "
                    f"which is not one of them. Cut inside a value."
                )
        report["numeric_columns_checked"] = numeric
        report["categorical_columns_checked"] = categorical
    elif fmt == "zip":
        report["structural_check"] = "end of central directory present"
        if ZIP_EOCD not in body[-70_000:]:
            raise GuardFailed(
                f"{label}: no zip end-of-central-directory record. A zip is "
                f"read from its tail, so a truncated one has no directory at "
                f"all rather than a short one."
            )
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                bad = archive.testzip()
        except zipfile.BadZipFile as exc:
            raise GuardFailed(f"{label}: unreadable zip: {exc}") from exc
        if bad is not None:
            raise GuardFailed(f"{label}: CRC failure on {bad}.")
    elif fmt == "ole2":
        report["structural_check"] = "sector-aligned, header sane"
        if len(body) < 1536 or len(body) % 512 != 0:
            raise GuardFailed(
                f"{label}: {len(body):,} bytes is not a whole number of 512 "
                f"byte sectors above the minimum. An OLE2 file always is."
            )
    elif fmt == "html":
        report["structural_check"] = "closing table tag present"
        text = decode(body).lower()
        if "<table" in text and "</table>" not in text:
            raise GuardFailed(
                f"{label}: an opened table with no closing tag. Truncated."
            )
    elif fmt == "pdf":
        report["structural_check"] = "%%EOF present"
        if b"%%EOF" not in body[-2048:]:
            raise GuardFailed(f"{label}: no %%EOF marker. Truncated.")
    else:
        report["structural_check"] = "none available for this format"
    return report


def _looks_numeric(field: str) -> bool:
    return re.fullmatch(r"[+-]?\d{1,3}(?:[ ,]\d{3})*(?:[.,]\d+)?|"
                        r"[+-]?\d*[.,]?\d+(?:[eE][+-]?\d+)?",
                        field.strip()) is not None


def decode(body: bytes) -> str:
    """Bytes to text, trying the encodings a Bolivian public site actually uses.

    Recorded rather than guessed downstream: the chosen encoding goes in the
    manifest, because a page that decodes under ``latin-1`` and not ``utf-8``
    is a fact about the source and the sort of thing that changes under a site
    redesign without anything else changing.
    """
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("latin-1", errors="replace")


def decoding_used(body: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            body.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1/replace"


# ---------------------------------------------------------------------------
# Digests. Two per response, and the second one is the one that means something.
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_rows(rows: list[tuple[str, ...]]) -> str:
    """A digest of the measurement rather than of the envelope.

    ``fetch_eltoque`` needed this because the response carried a server clock,
    so the same day refetched produced different bytes. Here the reason is
    different and the treatment is the same: **``all.csv`` is a growing
    archive**, so its body digest changes every time the publisher appends a
    quarter of an hour, and a body digest is therefore useless as an equality
    test across two fetches. What has to be stable is the part of the file that
    describes days that have already happened.

    Digested over the field strings exactly as served, never over parsed floats.
    A publisher who changes ``10.17`` to ``10.170`` has changed the file and
    this should say so; a float round trip would hide it, and hiding a silent
    revision is the one thing B15-2 exists to prevent.
    """
    payload = "\n".join("\x1f".join(row) for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def digest_prefix(rows: list[tuple[str, ...]], before: str) -> str:
    """``digest_rows`` over the records strictly older than ``before``.

    This is B15-2's comparison across two fetches of a growing file. The prefix
    of an archive that describes a closed past must not move; if it does, the
    publisher revised history, and that is a finding about the instrument rather
    than a fetch to retry.
    """
    return digest_rows([row for row in rows if row and row[0] < before])


# ---------------------------------------------------------------------------
# Parsers. Standard library only, because this project's dependency set is
# `numpy` and `matplotlib` and a fetcher is not the place to widen it.
# ---------------------------------------------------------------------------

def parse_csv(body: bytes) -> tuple[tuple[str, ...], list[tuple[str, ...]]]:
    """Header and records, as strings, with nothing coerced.

    Returning strings is deliberate. Coercion is a reading and readings belong
    to the criteria; a fetcher that parsed ``6,86`` as six point eight six or
    as six hundred and eighty six would be deciding the decimal convention of
    the carrier in the retrieval layer, silently, on the first row.
    """
    text = decode(body)
    reader = csv.reader(io.StringIO(text))
    rows = [tuple(row) for row in reader if row]
    if not rows:
        return (), []
    return rows[0], rows[1:]


ODS_NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}


def parse_ods(body: bytes) -> list[tuple[str, ...]]:
    """Every cell of the first sheet, as text, on a rectangular grid.

    **Three things this has to get right, and the first version got one of
    them.** The BCB's annual table is a matrix, days down and months across, so
    a cell's meaning is its column index and nothing else. Anything that moves
    a column silently relabels a month.

    1. ``table:number-columns-repeated`` stands for a run of identical cells and
       an ODS writer uses it for runs of blanks. Expanding it is what the first
       version did.
    2. ``table:covered-table-cell`` is the tail of a merged range. **It occupies
       real columns and carries no text**, so a reader that skips the element
       shortens the row and shifts everything after it. The BCB merges its month
       headers across two columns, so skipping these moves every month label.
    3. **Trailing empty cells are not padding, they are columns.** The first
       version popped them, which is what broke this file: a day row ending in
       empty months came back short, and a caller indexing by column got a
       different month depending on how late in the year the row ran out of
       data. **Every count stayed right while every identity moved**, which is
       the twelfth entry of this project's range-error family, exactly.

    Rows are returned padded to the widest row, so column `k` is column `k` in
    every row.
    """
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        content = archive.read("content.xml")
    root = ET.fromstring(content)
    grid: list[list[str]] = []
    for table in root.iter(f"{{{ODS_NS['table']}}}table"):
        for row in table.iter(f"{{{ODS_NS['table']}}}table-row"):
            cells: list[str] = []
            for cell in list(row):
                tag = cell.tag.rsplit("}", 1)[-1]
                if tag not in ("table-cell", "covered-table-cell"):
                    continue
                repeat = int(cell.get(
                    f"{{{ODS_NS['table']}}}number-columns-repeated", "1"))
                if repeat > 1024:      # a trailing run to the sheet's edge
                    repeat = 1
                value = cell.get(f"{{{ODS_NS['office']}}}value")
                if value is None:
                    value = cell.get(f"{{{ODS_NS['office']}}}date-value")
                if value is None:
                    parts = [node.text or "" for node in
                             cell.iter(f"{{{ODS_NS['text']}}}p")]
                    value = " ".join(part.strip() for part in parts).strip()
                cells.extend([value] * repeat)
            grid.append(cells)
        break                          # first sheet only
    if not grid:
        return []
    width = max(len(row) for row in grid)
    return [tuple(row + [""] * (width - len(row))) for row in grid]


#: The BCB annual table's shape, asserted rather than assumed.
#:
#: One column for the day of month and twelve month blocks of two, `VENTA` then
#: `COMPRA`. Checked by ``bcb_grid`` on every read, because a sheet that grows a
#: column is a sheet whose months have all moved.
BCB_GRID_WIDTH = 25
BCB_MONTHS = ("ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
              "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE")


def bcb_grid(body: bytes) -> dict[str, object]:
    """The annual table as a grid, with its own labels read back out of it.

    **Returns the labels rather than trusting them.** The month header row and
    the `VENTA`/`COMPRA` sub-header are read from the sheet and reported, and
    the day rows are keyed by the integer in their first cell. Nothing here maps
    a column to a calendar month: that mapping is a reading, it is not what the
    labels say on this file after 2026-06-26, and it belongs to a criterion with
    an external anchor rather than to a parser.
    """
    grid = parse_ods(body)
    if not grid:
        raise GuardFailed("empty ODS")
    width = len(grid[0])
    labels = next((row for row in grid if "ENERO" in row), None)
    sub = next((row for row in grid if row and row[0] == "PAIS"), None)
    days: dict[int, tuple[str, ...]] = {}
    for row in grid:
        head = row[0].strip() if row else ""
        if head.isdigit() and 1 <= int(head) <= 31:
            days[int(head)] = row
    prom = next((row for row in grid if row and row[0] == "PROM"), None)
    return {
        "width": width,
        "width_expected": BCB_GRID_WIDTH,
        "width_ok": width == BCB_GRID_WIDTH,
        "month_label_columns": (
            {label: i for i, label in enumerate(labels) if label in BCB_MONTHS}
            if labels else {}
        ),
        "subheader": list(sub) if sub else [],
        "days": days,
        "prom": list(prom) if prom else [],
        "rows": len(grid),
    }


def parse_html_table(body: bytes) -> list[tuple[str, ...]]:
    """Every ``<tr>`` of every ``<table>``, cells as text.

    The fallback for an ``xls.php`` that serves markup, which is what an
    endpoint of this shape most often does.
    """
    from html.parser import HTMLParser

    class Rows(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.rows: list[tuple[str, ...]] = []
            self._row: list[str] = []
            self._cell: list[str] | None = None

        def handle_starttag(self, tag: str, attrs) -> None:
            if tag == "tr":
                self._row = []
            elif tag in ("td", "th"):
                self._cell = []

        def handle_endtag(self, tag: str) -> None:
            if tag in ("td", "th") and self._cell is not None:
                self._row.append(" ".join("".join(self._cell).split()))
                self._cell = None
            elif tag == "tr" and self._row:
                self.rows.append(tuple(self._row))
                self._row = []

        def handle_data(self, data: str) -> None:
            if self._cell is not None:
                self._cell.append(data)

    parser = Rows()
    parser.feed(decode(body))
    return parser.rows


def rows_of(body: bytes, fmt: str) -> list[tuple[str, ...]]:
    """Whatever arrived, as a list of string rows, or an honest refusal.

    An OLE2 workbook is the one format this returns nothing for, and it says so
    rather than returning an empty list that reads like an empty file. The ODS
    of the same year is the parse path in that case, which is why it is fetched.
    """
    if fmt == "csv":
        header, records = parse_csv(body)
        return ([header] if header else []) + records
    if fmt == "zip":
        return parse_ods(body)
    if fmt == "html":
        return parse_html_table(body)
    if fmt == "ole2":
        raise NotImplementedError(
            "OLE2 workbook. The standard library does not read BIFF and this "
            "project's dependencies are numpy and matplotlib. The ODS export "
            "of the same year carries the same table and is fetched beside it."
        )
    raise NotImplementedError(f"no parser for format {fmt!r}")


def spanish_number(text: str) -> float | None:
    """A Bolivian published number: dots group thousands, the comma decimates.

    `11,5150` is eleven and a half, `50.049.980` is fifty million. Reading
    either with `float()` gives a number that is wrong by a factor of a thousand
    or raises, and the first is worse. **A dash is the page's own way of writing
    absent and it comes back as `None`**, never as zero, because a bank with no
    operations in a tier is not a bank that traded nothing at that rate; it did
    not trade there at all and it must leave the weighted average rather than
    enter it with weight zero.
    """
    text = text.strip()
    if text in ("", "-", "--"):
        return None
    try:
        return float(text.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def bcb_tco_detail(body: bytes) -> dict[str, object]:
    """One day of S2's microdata, as the grid Anexo II's formula wants.

    Returns the bank names, the tier rows as `(rate, {bank: (count, amount)})`,
    the per-bank totals, and the per-bank `TCO` row the page prints, which is
    what a recomputation is compared against. **Fifteen comparisons a day, not
    one**: each bank's own weighted average plus the aggregate.
    """
    rows = parse_html_table(body)
    if len(rows) < 4:
        raise GuardFailed("S2 detail: fewer than four table rows; no grid")
    banks = [b.strip() for b in rows[0][1:]]
    tco_row = next((r for r in rows if r and r[0].strip().upper() == "TCO"),
                   None)
    total_row = next((r for r in rows if r and r[0].strip().upper() == "TOTAL"),
                     None)
    if tco_row is None or total_row is None:
        raise GuardFailed("S2 detail: no TOTAL or TCO row")
    tiers = []
    for r in rows:
        rate = spanish_number(r[0]) if r else None
        if rate is None or len(r) < 1 + 2 * len(banks):
            continue
        cells = {}
        for j, bank in enumerate(banks):
            count = spanish_number(r[1 + 2 * j])
            amount = spanish_number(r[2 + 2 * j])
            if amount is not None:
                cells[bank] = (count, amount)
        if cells:
            tiers.append((rate, cells))
    return {
        "banks": banks,
        "tiers": tiers,
        "published_tco": {b: spanish_number(tco_row[1 + j])
                          for j, b in enumerate(banks)
                          if 1 + j < len(tco_row)},
        "totals": {b: (spanish_number(total_row[1 + 2 * j]),
                       spanish_number(total_row[2 + 2 * j]))
                   for j, b in enumerate(banks)
                   if 2 + 2 * j < len(total_row)},
    }


#: The BCB's exchange-rate index. `bolivia_availability.md` §3.1 records the
#: year selector reaching back to 1940, and §3.3 records that the BCB publishes
#: `Bs / Euro` and `DEG` beside the dollar. **Which parameter selects the
#: currency is not known**, and `--probe-euro` reads it off the page's own form
#: rather than guessing, for the reason `--probe-s2` exists: a guessed parameter
#: on a BCB endpoint returns 200 and somebody else's table.
S6_INDEX_URL = "https://www.bcb.gob.bo/tiposDeCambioHistorico/"


def describe_form(body: bytes, limit: int = 120,
                  options_per_select: int = 6) -> list[str]:
    """Every form, input, select, option and data link a page carries.

    Shared by the probes rather than written twice. **A page's form is the only
    honest source of its own query parameters**, and this project has now paid
    for that twice: once when `?fecha=` had to be found, and once when a page
    answered a guessed parameter with another day's grid.

    **Options are capped per select and the cap says what it hid.** The BCB's
    rate index carries a year selector with seventy-seven options reaching back
    to 1940, and a flat output cap let that one list eat the budget and truncate
    everything after it. A probe whose job is to show what a page offers must
    not be silenceable by the longest thing on the page.
    """
    from html.parser import HTMLParser

    class Reader(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.found: list[str] = []
            self._select: str | None = None
            self._seen: dict[str, int] = {}

        def handle_starttag(self, tag: str, attrs) -> None:
            a = dict(attrs)
            if tag == "form":
                self.found.append(f"form action={a.get('action')!r} "
                                  f"method={a.get('method')!r}")
            elif tag == "input":
                self.found.append(
                    f"  input name={a.get('name')!r} type={a.get('type')!r} "
                    f"value={a.get('value')!r}")
            elif tag == "select":
                self._select = a.get("name")
                self.found.append(f"  select name={a.get('name')!r}")
            elif tag == "option" and self._select:
                self._seen[self._select] = self._seen.get(self._select, 0) + 1
                n = self._seen[self._select]
                if n <= options_per_select:
                    self.found.append(f"    option value={a.get('value')!r}")
                elif n == options_per_select + 1:
                    self.found.append("    option ... (more, counted below)")
            elif tag == "a" and any(
                    ext in a.get("href", "").lower()
                    for ext in (".csv", ".xls", ".xlsx", ".ods", ".php")):
                self.found.append(f"  link href={a.get('href')!r}")

        def handle_endtag(self, tag: str) -> None:
            if tag == "select":
                self._select = None

    reader = Reader()
    reader.feed(decode(body))
    out = reader.found[:limit]
    for name, count in reader._seen.items():
        if count > options_per_select:
            out.append(f"  select {name!r} carries {count} options in total")
    if len(reader.found) > limit:
        out.append(f"  ... {len(reader.found) - limit} further lines not shown")
    return out


def echoed_date(body: bytes) -> str | None:
    """The date S2's detail page says it is showing, from its own form.

    **This exists because the endpoint lies by omission and it was caught doing
    it.** Asking `?fecha=` for a Saturday returns HTTP 200 with a complete,
    well-formed grid, and the grid is **another day's**. Twenty-one of
    fifty-five requested days came back byte-identical to the page's default,
    and a `has_grid` check saw a grid on every one of them and passed.

    The page does say which day it is showing: its date input carries
    `value="YYYY-MM-DD"`. Reading it is the whole guard, and it is the same
    lesson as B6-9's replay arm from the other direction. There the response
    carried no date of its own and an off-by-one could not be detected from the
    body, so a probe record had to be kept. **Here the body does carry the
    date and it simply was not read.**
    """
    match = re.search(rb'<input[^>]*name=["\']fecha["\'][^>]*>', body, re.I)
    if not match:
        return None
    value = re.search(rb'value=["\']([0-9]{4}-[0-9]{2}-[0-9]{2})["\']',
                      match.group(0))
    return value.group(1).decode() if value else None


def guard_echoed_date(body: bytes, requested: str, label: str) -> str:
    """The page shown is the page asked for, or the difference is returned.

    Returns the echoed date. **Does not raise**: a fallback is a fact about the
    endpoint and about that calendar day, not a corrupt download, and Anexo II
    §4 says a non-business day carries the previous business day's TCO. What
    would be wrong is counting it as an observation of the day requested.
    """
    echoed = echoed_date(body)
    if echoed is None:
        raise GuardFailed(f"{label}: the page carries no date input to check")
    return echoed


#: S2's CSV, which carries everything the 55 daily pages carry and says which
#: two dates each row has. Header block of seven lines, then a two-line column
#: header, then one row per (cutoff date, rate tier) with a `N°`/`Monto` pair
#: per bank, and a `TOTAL` and a `TCO` row closing each day.
S2_SERIES_DELIMITER = ";"


def bcb_tco_series(body: bytes) -> dict[str, dict]:
    """S2's whole range, keyed by `Fecha de corte`.

    **The two date columns are the point.** `Fecha de corte` is the day the
    operations happened and `Vigencia` is the day the resulting TCO governs, and
    the BCB prints both. Operations of Friday 2026-06-26 are `vigente` on Monday
    2026-06-29, which is Art. 5.III and Anexo II §4's weekend rule in one row.
    **This is the third independent confirmation of B15-4's verdict and the only
    one that comes from a column header rather than from an inference.**
    """
    text = decode(body).lstrip("\ufeff")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.startswith('"Fecha de corte"')), None)
    if start is None:
        raise GuardFailed("S2 series: no 'Fecha de corte' header row")
    reader = csv.reader(io.StringIO("\n".join(lines[start:])),
                        delimiter=S2_SERIES_DELIMITER)
    header = next(reader)
    banks = [header[j].strip() for j in range(3, len(header), 2)
             if header[j].strip()]
    # The header block states the source's own range, and the last cutoff date
    # in it is **the last day the BCB had computed a TCO for when the file was
    # served**. A day past it is not a holiday; it is a day whose 20:00
    # publication had not happened yet. Art. 5.III is why the two are different
    # and why they must not be counted together.
    corte_range = None
    for line in lines[:start]:
        if line.startswith('"Rango de fecha de corte"'):
            parts = line.split(S2_SERIES_DELIMITER)
            if len(parts) >= 3:
                corte_range = (parts[1].strip(), parts[2].strip())
    out: dict[str, dict] = {"__corte_range__": corte_range} if corte_range \
        else {}
    for row in reader:
        if len(row) < 3 or not row[0].strip():
            continue
        corte, vigencia, kind = row[0].strip(), row[1].strip(), row[2].strip()
        day = out.setdefault(corte, {"vigencia": vigencia, "banks": banks,
                                     "tiers": [], "published_tco": {},
                                     "totals": {}})
        if kind.upper() == "TCO":
            day["published_tco"] = {
                b: spanish_number(row[3 + 2 * j])
                for j, b in enumerate(banks) if 3 + 2 * j < len(row)}
        elif kind.upper() == "TOTAL":
            day["totals"] = {
                b: (spanish_number(row[3 + 2 * j]),
                    spanish_number(row[4 + 2 * j]))
                for j, b in enumerate(banks) if 4 + 2 * j < len(row)}
        else:
            rate = spanish_number(kind)
            if rate is None:
                continue
            cells = {}
            for j, b in enumerate(banks):
                if 4 + 2 * j >= len(row):
                    continue
                amount = spanish_number(row[4 + 2 * j])
                if amount is not None:
                    cells[b] = (spanish_number(row[3 + 2 * j]), amount)
            if cells:
                day["tiers"].append((rate, cells))
    return out


def vigencia_days(field: str) -> list[str]:
    """The days one S2 row's TCO governs, from the row's own `Vigencia` field.

    **The field is usually one date and is sometimes a range.** Thirty-four of
    thirty-five rows read `2026-07-13`; one reads `2026-08-06 al 2026-08-10`,
    which is the Independence Day holiday, the bridge Friday after it, the
    weekend and the Monday. **So the BCB states the span its forward-fill covers
    rather than leaving it to be inferred**, and Anexo II §4's weekend rule is
    visible per row instead of only in the statute.
    """
    field = field.strip()
    if " al " not in field:
        return [field] if field else []
    first, last = (part.strip() for part in field.split(" al ", 1))
    try:
        start, end = date.fromisoformat(first), date.fromisoformat(last)
    except ValueError:
        return [field]
    return [(start + timedelta(days=n)).isoformat()
            for n in range((end - start).days + 1)]


def s1_column_for_month(grid: dict, dated: dict[str, float],
                        tolerance: float = 5e-3) -> dict[int, int]:
    """Which S1 column actually holds each month, settled against dated values.

    **The 2026 sheet's month labels and its data part company at the reform.**
    The sheet opens a fresh two-column block for post-reform June while the
    twelve month headers stay where they are, so every month from the reform
    onward sits one block to the right of its label. Every count on the sheet
    stays correct and every identity after June moves, which is the twelfth
    entry of this project's range-error family.

    **The labels are therefore not read.** `dated` is a mapping of ISO date to
    published value from a source that states its dates, and each value is
    looked up at its own day-of-month across every column. A month whose values
    land in one column has that column, and one whose values scatter does not
    get a guess.

    Returns `{month number: column index}` for the months it can settle, and
    omits the ones it cannot.
    """
    votes: dict[int, dict[int, int]] = {}
    for iso, value in dated.items():
        day, month = int(iso[8:10]), int(iso[5:7])
        row = grid["days"].get(day)
        if row is None:
            continue
        for col in range(1, grid["width"]):
            cell = row[col]
            if not cell:
                continue
            try:
                if abs(float(cell) - value) < tolerance:
                    votes.setdefault(month, {})
                    votes[month][col] = votes[month].get(col, 0) + 1
            except ValueError:
                continue
    settled: dict[int, int] = {}
    for month, counts in votes.items():
        ranked = sorted(counts.items(), key=lambda kv: -kv[1])
        # A month is settled only when one column carries strictly more of its
        # dated values than any other. A tie is left unsettled rather than
        # broken, because breaking it is the guess this function exists to
        # avoid.
        if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
            settled[month] = ranked[0][0]
    return settled


def s1_daily(grid: dict, columns: dict[int, int], year: int,
             fallback: dict[int, int] | None = None) -> dict[str, float]:
    """S1's grid as ISO date to value, once the columns are settled.

    **Filed by vigencia.** The value at day `d` of the column that holds month
    `m` is the rate in force on `year-m-d`, which is B15-4's verdict arriving
    from a fourth source: S1's own grid agrees with S2's `Vigencia` column, with
    the step-time histogram and with the Aduana anchor.

    **A month can span two column blocks and June 2026 does.** The reform fell
    on the 26th, so days 1 to 26 sit in the block labelled JUNIO carrying a
    `VENTA`/`COMPRA` pair, and days 27 to 30 sit in the next block carrying a
    single post-reform value. A resolver that gives each month one column loses
    the pegged half, **and losing it costs the Aduana anchor**, which is the one
    dated observation §5 registers for B15-9.

    So `fallback` names a second column per month, consulted where the settled
    one is empty. Nothing is invented: a date carries a value only if some
    column of the sheet has one for it.
    """
    fallback = fallback or {}
    out: dict[str, float] = {}
    for month in set(columns) | set(fallback):
        for day, row in grid["days"].items():
            iso = f"{year:04d}-{month:02d}-{day:02d}"
            for col in (columns.get(month), fallback.get(month)):
                if col is None or col >= len(row) or not row[col]:
                    continue
                try:
                    out[iso] = float(row[col])
                except ValueError:
                    continue
                break
    return out


def anexo_ii(tiers: list, banks: list[str]) -> float | None:
    """`TCO_t = sum(TC_it * M_it) / sum(M_it)`, over every cell of the grid.

    `RD 88/2026` Anexo II section 2, with `i` ranging over bank-and-tier cells.
    The aggregate excludes the page's own `TOTAL BANCOS` column, which is a sum
    and would double every operation.
    """
    num = den = 0.0
    for rate, cells in tiers:
        for bank in banks:
            if bank in cells and cells[bank][1]:
                num += rate * cells[bank][1]
                den += cells[bank][1]
    return num / den if den else None


# ---------------------------------------------------------------------------
# Guards. §6.2.
# ---------------------------------------------------------------------------

def guard_header(header: tuple[str, ...], expected: tuple[str, ...],
                 label: str) -> None:
    """The columns are the ones the register was written against.

    B15-3 is a statement about which of these columns is the ask and which is
    the bid. A publisher who renames or reorders them turns that criterion into
    a question about a different file, and the whole of arm III is gated on
    B15-3, so this is checked before anything is stored rather than after.
    """
    got = tuple(name.strip().lower() for name in header)
    want = tuple(name.strip().lower() for name in expected)
    if got != want:
        raise GuardFailed(
            f"{label}: header is {got} and the register was written against "
            f"{want}. bolivia_availability.md §3.2.1. Stopping, because B15-3 "
            f"is a claim about which column is which side."
        )


def guard_span(days: list[date]) -> None:
    """Every day in the window is ``ORDINARY_SPAN`` seconds long. §3.3.

    Asserted rather than assumed. The assertion is free and the equivalent
    assumption on the other carrier was wrong, cost a day of retrieval, and was
    discovered only because the API refused a window it had accepted 310 times.
    """
    for day in days:
        if local_span_seconds(day) != ORDINARY_SPAN:
            raise GuardFailed(
                f"{day} spans {local_span_seconds(day)} seconds against "
                f"{ORDINARY_SPAN}. {TZ} is registered as UTC-4 with no "
                f"daylight saving and this says otherwise."
            )


def guard_no_fill(served: set[str], values: dict[str, object]) -> None:
    """A date the source did not serve carries nothing. §6.2.

    Neither direction, at any resolution. B6-A admitted a back-fill as a
    forward-fill once, the failure it produced was read as an economic finding
    for several hours, and the retraction is in ``b6_cuba_prereg.md`` §11.
    """
    invented = sorted(set(values) - served)
    if invented:
        raise GuardFailed(
            f"{len(invented)} dates carry values and were not served, first "
            f"{invented[0]}. Absence is a reading and is stored as one."
        )


def guard_press_free(constants: dict[str, object]) -> None:
    """No number that entered this project through press or a fetch summary is
    an input to any criterion. §6.3.

    The list of such numbers is in ``bolivia_availability.md`` §6. **One of them
    is a value the BCB's 2026 annual table was reported to carry for
    2026-08-31, a date that has not happened**, and it is discarded. This check
    is cheap and is run against the registered constants on every pass, and it
    passes because that block contains none of them, which is the state the
    register was closed in.
    """
    forbidden = {
        11.57: "parallel ask, press, bolivia_availability.md §4.4",
        11.62: "derived ceiling from a press TCO, §4.4",
        11.52: "TCO, press, §4.4",
        9.73: "TCO for 2026-06-29, press, §6",
        9.7: "TCO, press, §1 and §4.3",
    }
    for name, value in constants.items():
        if isinstance(value, float) and value in forbidden:
            raise GuardFailed(
                f"registered constant {name} = {value} is "
                f"{forbidden[value]}. guard_press_free, prereg §6.3."
            )


def registered_constants() -> dict[str, object]:
    """The §6.1 block, as data, so ``guard_press_free`` can be run on it."""
    return {
        "STATUTORY_SPREAD": STATUTORY_SPREAD,
        "SPREAD_SHARE": SPREAD_SHARE,
        "UNCROSSED_SHARE": UNCROSSED_SHARE,
        "CROSSED_SHARE_MAX": CROSSED_SHARE_MAX,
        "TCO_RECOMPUTE_SHARE": TCO_RECOMPUTE_SHARE,
        "A_SHARE": A_SHARE,
        "CRITICAL_SPREAD": CRITICAL_SPREAD,
        "CYCLE_DETERMINED": CYCLE_DETERMINED,
        "AGREEMENT_SHARE": AGREEMENT_SHARE,
    }


# ---------------------------------------------------------------------------
# Small helpers the manifest reports through.
# ---------------------------------------------------------------------------

def window_days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def datetime_span(rows: list[tuple[str, ...]]) -> dict[str, object]:
    """First and last timestamp, row count, and whether time runs forwards.

    **Reported, not enforced.** A duplicate or an out-of-order timestamp in a
    published archive is a property of the archive, and turning it into a guard
    here would decide, in the retrieval layer, a question that belongs to a
    criterion.
    """
    stamps = [row[0] for row in rows if row and row[0]]
    if not stamps:
        return {"rows": 0, "first": None, "last": None,
                "monotonic": None, "duplicates": None}
    return {
        "rows": len(stamps),
        "first": stamps[0],
        "last": stamps[-1],
        "monotonic": all(a <= b for a, b in zip(stamps, stamps[1:])),
        "duplicates": len(stamps) - len(set(stamps)),
    }


def bcb_url(year: int, fmt: str) -> str:
    return BCB_YEAR_URL.format(fmt=fmt, year=year)


def utc_stamp() -> str:
    """A timestamp for the manifest, which is not a checked generated file."""
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rendered(criterion: dict, name: str, detail: str) -> dict:
    """Give a criterion dict the four keys a criteria block is read by.

    The contract is ``name``, ``passed``, ``detail`` and ``void``.
    These records were written with ``criterion`` and ``verdict`` instead, and
    nothing caught it, because every one of them carried ``diagnostic_only``
    while the stage was open and the renderer skips those entirely. **Flipping
    that field at closure is what first exercised the contract**, and it died
    on a ``KeyError`` naming no file. A record whose rendering is never
    exercised is the same shape as a guard nobody runs.

    Both key sets are kept. The reader of a record wants ``criterion`` and the
    readings beside it; the renderer wants its four. Writing one dict that
    answers both is cheaper than two dicts that can disagree.

    ``void`` is read off the dict rather than passed in, so that a criterion
    which becomes void inside its own function cannot be labelled live here by
    a caller that has not looked. A void criterion is marked ``VOID`` by the
    renderer before ``passed`` is consulted, and ``passed`` is set False for it
    so that no caller can read a bare absence as a pass.
    """
    void = bool(criterion.get("void"))
    criterion["name"] = name
    criterion["detail"] = detail
    criterion["void"] = void
    criterion["passed"] = False if void else bool(criterion.get("passed"))
    return criterion


#: The other publisher's stamps carry an explicit offset, so they are an
#: absolute clock this repository does not have to trust anyone about:
#: ``2024-08-05T20:41-04:00``. S3's column carries no offset at all.
S5_CLOCK_FILE = "mauforonda_buy.csv"
#: Shifts tried when locating S3's clock against S5's. Wide enough to contain
#: every offset the two candidates could sit at and every neighbouring hour, so
#: that a peak at the expected place is a peak and not the edge of the scan.
CLOCK_SCAN_HOURS = range(-6, 7)


def _hourly_last(series, shift_h=0):
    """Last value in each clock hour, after shifting the stamps."""
    from datetime import timedelta
    out = {}
    for when, value in series:
        key = (when + timedelta(hours=shift_h)).replace(
            minute=0, second=0, microsecond=0)
        out[key] = value
    return out


def _hourly_diffs(hourly):
    """First differences between adjacent hours only.

    Gaps are dropped rather than bridged. A difference across a six-hour hole
    is not an hourly move and averaging it in is how a lag scan loses its peak.
    """
    from datetime import timedelta
    keys = sorted(hourly)
    return {b: hourly[b] - hourly[a] for a, b in zip(keys, keys[1:])
            if b - a == timedelta(hours=1)}


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return None if sx == 0 or sy == 0 else (
        sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (sx * sy))


def clock_scan(s3_series, s5_series):
    """Where does S3's undeclared clock sit against S5's declared one?

    **Both series scrape the same book**, so a price move is one event with two
    records of it. Shifting one against the other and correlating hourly first
    differences puts a peak at the offset between the two clocks, and the
    location of that peak is a measurement rather than a reading of anybody's
    documentation.

    Returns the whole profile, not a verdict. **The caller prints it**, because
    a scan that reports only its argmax cannot be told apart from a scan with
    no peak at all, and this one has to be able to say "no peak" out loud.

    `s3_series` and `s5_series` are both ``[(naive datetime, float)]``. S5's
    stamps must already be converted to the same wall clock the caller wants to
    compare against; this function does no timezone arithmetic of its own.
    """
    d5 = _hourly_diffs(_hourly_last(s5_series))
    profile = {}
    for shift in CLOCK_SCAN_HOURS:
        d3 = _hourly_diffs(_hourly_last(s3_series, shift))
        common = sorted(set(d3) & set(d5))
        if len(common) < 500:
            profile[shift] = (None, len(common))
            continue
        profile[shift] = (_pearson([d3[t] for t in common],
                                   [d5[t] for t in common]), len(common))
    scored = [(r, s) for s, (r, _) in profile.items() if r is not None]
    return {"profile": profile,
            "peak": max(scored)[1] if scored else None,
            "peak_r": max(scored)[0] if scored else None}


#: Where arm III reads its gate from. §6.3's ``guard_typing_first`` says arm III
#: does not run unless B15-3 and B15-4 both resolve, and B15-4's own criterion
#: says a void there suspends arm III.
TYPING_RECORD = "b15_typing.json"


def arm_iii_runs(results_dir) -> tuple[bool, str]:
    """Does §6.3's gate let arm III count this run?

    **Read out of the typing record rather than restated here.** The gate was
    a hard-coded constant in each arm III script for one round, which meant
    three files each carried their own copy of a verdict that lives in one
    place, and a change to that verdict reached none of them. It is a lookup
    now, so a criterion that resolves later flips these records without anybody
    remembering to.

    Returns ``(runs, why)``. ``why`` is written into the record, so it has to
    say which criterion suspended the arm and where that is recorded.
    """
    import json
    path = results_dir / TYPING_RECORD
    if not path.exists():
        return False, (f"arm II has not run: {TYPING_RECORD} is not on disk, "
                       f"and the gate is read from it rather than assumed")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("arm_iii_runs"):
        return True, ""
    voided = [c.get("criterion") for c in record.get("criteria", [])
              if c.get("void")]
    return False, (
        f"arm III is suspended: {', '.join(voided) or 'arm II'} void in "
        f"results/{TYPING_RECORD}. B15-4's criterion says a void there "
        f"suspends arm III, so this record is a reading and not a verdict "
        f"until that criterion resolves")


# ---------------------------------------------------------------------------
# The euro leg. Register §3.3 put the euro on the rate index and it is not
# there: that endpoint takes `?anio=` and its own heading says it is the
# dollar. It is on a second BCB endpoint, one calendar day per request, which
# is the same shape as S2's microdata and is disclosed as such.
# ---------------------------------------------------------------------------

#: One day's whole `Tabla de Cotizaciones`: the TCO, twenty-odd currencies,
#: the UFV, gold, silver and SOFR. Takes day, month and year separately.
S7_COTIZACIONES_URL = (
    "https://www.bcb.gob.bo/librerias/indicadores/otras/otras_imprimir2.php")

#: The outside cross, register §3 S6. Ninety days in one request covers the
#: whole post-event window; the full history is a second file and is not
#: fetched unless the pre-event era is asked for.
S6_ECB_90D_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
S6_ECB_HIST_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"

SPANISH_MONTHS = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10,
    "NOVIEMBRE": 11, "DICIEMBRE": 12,
}


def strip_tags(text: str) -> str:
    """Markup out, one space between what is left.

    **Deliberately not a parser.** The rows wanted here are identified by a
    three-letter currency code followed by numbers, and that survives any
    rearrangement of the table markup, which a column-index parser does not.
    `parse_ods` is in this file because a column index was the meaning of a
    cell there; here it is not, and reading position would be borrowing a
    fragility from a place that had no choice about it.
    """
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text)).strip()


def cotizaciones_date(text: str) -> str | None:
    """The date the page says it is showing, off its own heading.

    **This exists because `?fecha=` lied once already.** S2's day endpoint
    answers 200 with another day's grid when the day it was asked for has
    none, and twenty-one requested days came back byte-identical before
    anybody read the page's own statement of what it was showing. A day
    endpoint is guilty until it echoes the date.
    """
    flat = strip_tags(text).upper()
    hit = re.search(r"COTIZACIONES\s+DEL\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚ]+)"
                    r"\s+(?:DE\s+|DEL\s+)?(\d{4})", flat)
    if not hit:
        return None
    month = SPANISH_MONTHS.get(hit.group(2))
    if month is None:
        return None
    return f"{int(hit.group(3)):04d}-{month:02d}-{int(hit.group(1)):02d}"


def cotizaciones(body: bytes) -> dict:
    """One day's table: the echoed date, the TCO, and every code with numbers.

    Returns ``{"date": iso or None, "rows": {CODE: [floats]}}``. **Every number
    on a code's row is kept, in order, and none is named here.** The euro row
    carries bolivianos per euro and the rate in foreign-currency terms, and
    which is which is a reading to declare where it is used, not a guess to
    bake into a parser that cannot check it.

    A code appearing more than once keeps its first occurrence, and the count
    of repeats is returned, because a table that lists a currency twice is a
    thing the caller has to know about rather than a thing to average.
    """
    text = decode(body)
    flat = strip_tags(text)
    rows: dict[str, list[float]] = {}
    repeats: dict[str, int] = {}
    ambiguous: dict[str, list[str]] = {}
    raw: dict[str, list[str]] = {}
    for hit in re.finditer(r"\b([A-Z]{3})\b((?:\s+-?[\d.,]+){1,4})", flat):
        code = hit.group(1)
        numbers, undecidable = [], []
        for token in hit.group(2).split():
            value = bcb_number(token)
            if value is None:
                undecidable.append(token)
            else:
                numbers.append(value)
        if undecidable:
            ambiguous[code] = undecidable
        if not numbers:
            continue
        if code in rows:
            repeats[code] = repeats.get(code, 1) + 1
            continue
        rows[code] = numbers
        # **The tokens as printed, kept beside the floats.** B15-12's band is
        # one tick of the published euro series, and a tick is a count of
        # decimals: it is a property of the string the publisher wrote, and
        # recovering it from a float is guessing at a representation rather
        # than reading a publication.
        raw[code] = [tok for tok in hit.group(2).split()
                     if re.fullmatch(r"-?[\d.,]+", tok)]
    return {"date": cotizaciones_date(text), "rows": rows,
            "repeated_codes": repeats,
            "ambiguous_codes": ambiguous, "raw": raw}


def bcb_number(token: str) -> float | None:
    """A number off this endpoint, with the separator convention checked.

    Returns the value, or ``None`` when the token is ambiguous. **Ambiguous is
    a third answer and it has to be one**, because two of the three cases here
    are decidable and one is not:

    * a dot last, with or without commas before it, is dot-decimal and
      comma-thousands: ``0.86386``, ``4,343.81``. Decided;
    * a comma **after** a dot is the other convention entirely, which would
      mean the page changed under us. **Raises**, because returning a number
      for it would move a magnitude while every count stayed right;
    * **a comma with no dot at all is not decidable from the token.**
      ``6,090`` is six thousand and ninety under one convention and six point
      zero nine under the other, and nothing inside the token says which.

    **The first version raised on the third case and that was wrong twice
    over.** It is not the same fact as the second case, and it took the whole
    page down over rows nothing in this stage reads: seventeen of fifty-seven
    days died on a Korean won or an Argentine peso while the euro and the
    dollar on those same pages were unambiguous. **That is `guard_truncation`
    firing on `oficial.csv`'s `kind` column all over again** — a check on a
    field that gates nothing taking the run with it — and it is the second
    time this file has done it.

    **The caller decides what an ambiguous row costs it.** For B15-12 the
    answer is nothing: the euro row and the dollar row are dot-decimal on every
    page seen.
    """
    token = token.strip()
    if not token or not re.fullmatch(r"-?[\d.,]+", token):
        return None
    last_dot, last_comma = token.rfind("."), token.rfind(",")
    if last_comma >= 0 and last_dot >= 0 and last_comma > last_dot:
        raise GuardFailed(
            f"{token!r} puts a comma after a dot, so this page is not "
            f"dot-decimal any more; bcb_number's convention has to be re-read "
            f"before any number off it is used")
    if last_comma >= 0 and last_dot < 0:
        return None
    try:
        return float(token.replace(",", ""))
    except ValueError:
        return None


def ecb_rates(body: bytes) -> dict[str, dict[str, float]]:
    """The ECB reference-rate XML, as ``{date: {currency: rate}}``.

    Rates are units of the currency per one euro, which is the ECB's own
    convention and is stated here because inverting it silently is how a
    referee becomes the thing it was refereeing.
    """
    text = body.decode("utf-8", errors="replace")
    out: dict[str, dict[str, float]] = {}
    for day in re.finditer(r'<Cube\s+time=[\'"](\d{4}-\d{2}-\d{2})[\'"]\s*>'
                           r'(.*?)</Cube>', text, re.S):
        stamp, block = day.group(1), day.group(2)
        rates = {}
        for cell in re.finditer(r'currency=[\'"]([A-Z]{3})[\'"]\s+'
                                r'rate=[\'"]([\d.]+)[\'"]', block):
            rates[cell.group(1)] = float(cell.group(2))
        if rates:
            out[stamp] = rates
    return out
