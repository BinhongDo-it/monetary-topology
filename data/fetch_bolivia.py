"""Bolivia's official and parallel rates, for stage B15.

``docs/b15_bolivia_prereg.md`` §10 is the authority. Written to
``data/fetch_eltoque.py``'s contract and deliberately close to it, so that the
places it has to differ stand out instead of hiding in a rewrite.

The differences, and why each is forced
----------------------------------------

**One request buys a range, not a day.** elTOQUE caps a window at twenty-four
hours, so B6-B cost 2,056 requests and nine hours. Here S1 serves a year per
request and S3 serves its whole archive in one file. **The registered request
count for the entire stage is in the low tens**, which is the difference between
a publisher who serves ranges and one who serves a day.

**So the resume unit is a file, not a day.** ``fetch_eltoque`` resumes by the
existence of one file per day, which is the same idea at a different grain. A
file already on disk is a file already retrieved and there is no separate state
to keep in step with the directory.

**The payload is not JSON and its format is not known in advance.**
``xls.php`` is a filename, not a promise. ``bolivia.sniff`` reports what
arrived, ``bolivia.guard_truncation`` applies the check that belongs to that
format, and the ODS export of the same year is fetched beside the XLS because
the standard library reads a zip of XML and does not read BIFF.

**The stable digest is over a prefix, not over the payload.** elTOQUE's body
carried a server clock, so ``sha256`` of the body was not an equality test and
``digest_tasas`` hashed the measurement instead. Here the reason is different
and the answer is the same shape: ``all.csv`` is a growing archive, so its body
digest moves whenever the publisher appends a quarter of an hour.
``digest_prefix`` hashes the records that describe a past that has already
closed, and **that is the thing that must not move.** If it does, the publisher
revised history, which is B15-2's whole purpose.

**Pacing is a floor plus the headers, and the headers are measured first.**
``--probe-headers`` makes one request per source, prints every header, and
writes nothing. It exists because elTOQUE's published limit was 60 a minute and
the key carried ten per 156 seconds, and the gap between those two is ten hours
against thirty-five minutes. ``b6b_eltoque_prereg.md`` §12.

**S3's bulk history will not be pulled without a flag.** The publisher's terms
permit reuse with attribution and in the same breath say bulk history wants
registration for a beta API, while serving this file with no key at all.
``b15_bolivia_prereg.md`` §10 registers the tension and registers the
resolution as **register, or fall back to S4 plus S5, rather than pull
quietly.** I resolve that explicitly and ``--s3-bulk-acknowledged`` is where
that is recorded.

What this file will not do
---------------------------

**It does not delete.** ``retire`` renames with ``.expired`` and leaves the file
in place. **Nothing in this repository deletes.**

**It does not fill.** A date the source does not serve is absent in both
directions, at every resolution.

**It does not print a Bolivian rate.** Counts, spans, formats, digests and
guard verdicts. B15's claim is that its register closed before its data existed
and that B15-3 and B15-4 are decided from the archive rather than from a look at
it; a silent retrieval layer costs nothing and removes the one way that could
quietly stop being true.

**It does not touch git.** Committing is done by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from monetary_topology.bolivia import (
    BCB_FORMATS,
    BCB_YEARS,
    EVENT_DATE,
    GuardFailed,
    POLITE_FLOOR_SECONDS,
    S2_CSV_URL,
    S2_DETAIL_URL,
    S3_ALL_HEADER,
    S3_ALL_URL,
    S3_ATTRIBUTION,
    S3_OFICIAL_URL,
    S3_TERMS,
    S4_CITATION,
    S4_HEADER,
    S4_URL,
    S5_BRANCHES,
    S5_FILES,
    S5_RAW,
    S5_REPO,
    S6_ECB_90D_URL,
    S6_INDEX_URL,
    S7_COTIZACIONES_URL,
    SIGNING_DATE,
    WINDOW_OPEN_DATE,
    bcb_tco_detail,
    bcb_url,
    cotizaciones,
    datetime_span,
    decode,
    decoding_used,
    describe_form,
    digest_prefix,
    digest_rows,
    ecb_rates,
    echoed_date,
    guard_header,
    guard_press_free,
    guard_span,
    guard_truncation,
    parse_csv,
    registered_constants,
    rows_of,
    sha256,
    sniff,
    utc_stamp,
    window_days,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BOLIVIA_DIR = RAW / "bolivia"
MANIFEST = RAW / "bolivia_manifest.json"

TIMEOUT_SECONDS = 120
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

#: How a 429 is answered when the source's own advice is unusable.
#:
#: elTOQUE returned ``Retry-After: -11`` on 2026-08-19. **A negative wait is not
#: a wait**, and clamping it to a second is an immediate retry wearing a delay's
#: clothes. This floor is used when both ``Retry-After`` and
#: ``X-RateLimit-Reset`` point into the past, and it doubles per attempt.
THROTTLE_FLOOR_SECONDS = 30.0
THROTTLE_ATTEMPTS = 4

#: A wait longer than this is reported rather than slept through. The run
#: resumes from disk, so coming back later costs nothing, and an unannounced
#: long sleep is indistinguishable from a hang.
MAX_THROTTLE_WAIT_SECONDS = 300.0

#: The cut-off for ``digest_prefix``. Records strictly older than this describe
#: a past that has closed, so their digest must reproduce on any later fetch.
#: Fixed to the event date rather than to the run date **on purpose**: a cut-off
#: that moved with the clock would compare a different prefix every time and
#: could never detect anything.
PREFIX_CUTOFF = EVENT_DATE.isoformat()

USER_AGENT = f"monetary-topology (stage B15; {S3_ATTRIBUTION})"


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


class RateLimited(Exception):
    """A 429 that came back after waiting out its own advice."""


class Refused(Exception):
    """A 4xx that is the source's answer and not a transport failure."""


def limits(headers) -> str:
    """The limiter's own account of itself, for a message a human will read."""
    def get(name: str) -> str:
        try:
            return str(headers.get(name, "-"))
        except AttributeError:
            return "-"
    now = time.time()
    reset = get("X-RateLimit-Reset")
    try:
        gap = f"{float(reset) - now:+.0f}s"
    except ValueError:
        gap = "unparseable"
    return (f"limit={get('X-RateLimit-Limit')} "
            f"remaining={get('X-RateLimit-Remaining')} "
            f"reset={reset} ({gap}) retry-after={get('Retry-After')}")


def throttle_wait(headers, attempt: int) -> float:
    """How long to wait after a 429: the source, then the clock, then a floor.

    **Both headers have been seen pointing into the past** on the other carrier,
    so neither is trusted without a sign check, and when both fail the wait
    comes from a schedule of this file's own rather than from a clamp.
    """
    try:
        advised = float(headers.get("Retry-After"))
    except (TypeError, ValueError):
        advised = -1.0
    if advised > 0:
        return advised
    try:
        gap = float(headers.get("X-RateLimit-Reset")) - time.time()
    except (TypeError, ValueError):
        gap = -1.0
    if gap > 0:
        return gap
    return THROTTLE_FLOOR_SECONDS * (2 ** (attempt - 1))


def wait_for(headers: dict[str, str], source: str) -> float:
    """How long to sleep after one response. A floor, raised by the headers.

    **Not lowered by them.** ``X-RateLimit-Remaining`` reported ``10`` on all
    fifteen requests of elTOQUE's rate probe including the three that were
    refused, so a pacer that speeds up when a header says there is room speeds
    up on a header that does not move. The floor is the publisher's own stated
    politeness where there is one, and a header asking for longer wins.
    """
    floor = POLITE_FLOOR_SECONDS.get(source, 5.0)
    try:
        gap = float(headers.get("x-ratelimit-reset", "")) - time.time()
    except (TypeError, ValueError):
        gap = -1.0
    return max(floor, gap) if gap > 0 else floor


def download(url: str) -> tuple[bytes, dict[str, str], int | None]:
    """Fetch one payload. Retry server errors, never retry client errors.

    The one exception is 429, which is a client error the server asked us to
    retry. It is waited out on its own advice where that advice is usable and on
    a backoff of this file's own where it is not, and it gives up rather than
    pressing against a published limit.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    throttled = 0
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310, E501
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read()
                declared = headers.get("content-length")
                length = int(declared) if declared and declared.isdigit() else None
                return body, headers, length
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                throttled += 1
                delay = throttle_wait(exc.headers, throttled)
                print(f"      429 #{throttled}: {limits(exc.headers)}")
                if delay > MAX_THROTTLE_WAIT_SECONDS:
                    raise RateLimited(
                        f"the limiter asks for {delay:.0f}s, longer than this "
                        f"file will sleep without saying so. The run resumes "
                        f"from disk. Headers: {limits(exc.headers)}"
                    ) from exc
                if throttled > THROTTLE_ATTEMPTS:
                    raise RateLimited(
                        f"{throttled} consecutive 429s with backoff. That is "
                        f"the limiter saying no, not a burst."
                    ) from exc
                print(f"      waiting {delay:.0f}s")
                time.sleep(delay)
                continue
            if exc.code < 500:
                raise Refused(f"HTTP {exc.code} {exc.reason}") from exc
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


def write_atomic(path: Path, data: bytes) -> None:
    """Temporary file, then rename, so a payload is whole or absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def describe(body: bytes, label: str, declared: int | None) -> dict:
    """Everything about a payload except what it says the rate is.

    Format, size, encoding, truncation verdict, row count, timestamp span, and
    the two digests. **No level and no value**, for the reason in the module
    docstring.
    """
    fmt = sniff(body)
    record: dict[str, object] = {
        "sha256_body": sha256(body),
        "encoding": decoding_used(body) if fmt in ("csv", "html") else None,
        "truncation": guard_truncation(body, fmt, declared, label),
    }
    try:
        rows = rows_of(body, fmt)
    except NotImplementedError as exc:
        record["rows"] = None
        record["parse"] = f"not attempted: {exc}"
        record["sha256_payload"] = None
        return record
    record["parse"] = "ok"
    record["rows"] = len(rows)
    record["sha256_payload"] = digest_rows(rows)
    record["sha256_prefix"] = digest_prefix(rows, PREFIX_CUTOFF)
    record["prefix_cutoff"] = PREFIX_CUTOFF
    if rows:
        record["header"] = list(rows[0])
        record["span"] = datetime_span(rows[1:])
    return record


def fetch_one(url: str, path: Path, source: str, label: str, *,
              force: bool) -> dict:
    """One payload, cached or fetched. **This is the whole of the resume logic.**

    A file already on disk is a file already retrieved and its existence is the
    resume point. There is no separate state to keep in step with the directory,
    which is the failure this shape avoids rather than the convenience it
    offers.
    """
    if path.exists() and not force:
        body = path.read_bytes()
        return {
            "url": url, "file": path.name, "status": "cached",
            "wait": 0.0, **describe(body, label, None),
        }
    body, headers, declared = download(url)
    # The wholeness check runs **before** the write, on purpose. A payload that
    # fails its own format's check is never stored under the name of a good one,
    # so the next run asks again instead of resuming onto a file that looks
    # complete. This ordering is the whole of guard_truncation's teeth.
    record = describe(body, label, declared)
    write_atomic(path, body)
    stored = path.read_bytes()
    if sha256(stored) != record["sha256_body"]:
        retire(path, "the stored bytes differ from what arrived")
        raise GuardFailed(
            f"{label}: what was written back is not what arrived. Every digest "
            f"in the manifest rests on this check."
        )
    return {
        "url": url, "file": path.name, "status": "downloaded",
        "wait": wait_for(headers, source),
        "rate_limit": {k: headers.get(k) for k in
                       ("x-ratelimit-limit", "x-ratelimit-remaining",
                        "x-ratelimit-reset", "retry-after")},
        "content_type": headers.get("content-type"),
        "last_modified": headers.get("last-modified"),
        **record,
    }


# ---------------------------------------------------------------------------
# The passes.
# ---------------------------------------------------------------------------

def pass_s1(*, force: bool) -> list[dict]:
    """S1. Three years, two serialisations each, six requests.

    The XLS is the source of record named in the register's §3.1. The ODS is
    retrieval machinery under §10 and it earns its three requests twice over:
    it is parseable from the standard library whatever ``xls.php`` turns out to
    serve, **and it makes B15-2 an independent-format check rather than a
    replay of our own bytes.** Two exports of one year by one publisher through
    two serialisers have to agree row for row.
    """
    out: list[dict] = []
    for year in BCB_YEARS:
        for fmt in BCB_FORMATS:
            path = BOLIVIA_DIR / f"bcb_tco_{year}.{fmt}"
            label = f"S1 {year}.{fmt}"
            print(f"  {label}")
            record = fetch_one(bcb_url(year, fmt), path, "bcb", label,
                               force=force)
            record["source"] = "S1"
            record["year"] = year
            record["requested_format"] = fmt
            out.append(record)
            print(f"    {record['status']}, {record['truncation']['format']}, "
                  f"{record['truncation']['bytes']:,} bytes, "
                  f"rows={record.get('rows')}")
            if record["status"] == "downloaded":
                time.sleep(record["wait"])
    return out


def pass_s3(*, force: bool, acknowledged: bool) -> list[dict]:
    """S3. The whole archive in one file, and the ``kind`` column if it exists.

    The bulk file is gated behind ``acknowledged`` for the reason registered in
    §10: the publisher's terms permit reuse with attribution and in the same
    breath say bulk history wants registration, while serving this file with no
    key. I resolve that tension explicitly and this flag is the record of it.
    """
    out: list[dict] = []
    if not acknowledged:
        print("  S3 all.csv NOT fetched. Terms position, prereg §10:")
        print(f"    {S3_TERMS}")
        print("    Pass --s3-bulk-acknowledged to pull it on the reading that")
        print("    an unkeyed public endpoint is public, or fall back to S4+S5.")
        return out
    label = "S3 all.csv"
    print(f"  {label}")
    record = fetch_one(S3_ALL_URL, BOLIVIA_DIR / "dolarblue_all.csv",
                       "dolarblue", label, force=force)
    record["source"] = "S3"
    record["terms"] = S3_TERMS
    record["attribution"] = S3_ATTRIBUTION
    out.append(record)
    print(f"    {record['status']}, {record['truncation']['bytes']:,} bytes, "
          f"{record.get('rows')} rows")
    span = record.get("span") or {}
    print(f"    span {span.get('first')} .. {span.get('last')}, "
          f"monotonic={span.get('monotonic')}, "
          f"duplicate stamps={span.get('duplicates')}")
    if record["status"] == "downloaded":
        time.sleep(record["wait"])

    # The `kind` column. `guard_kind_column` is registered against a file this
    # project has never seen and whose URL is a guess, so a refusal here is
    # recorded as a fact rather than raised. The manifest then says honestly
    # whether that guard was exercised at all, which is better than a guard
    # that reports success because it never ran.
    label = "S3 oficial.csv"
    print(f"  {label} (URL is a guess; a refusal is recorded, not raised)")
    try:
        extra = fetch_one(S3_OFICIAL_URL, BOLIVIA_DIR / "dolarblue_oficial.csv",
                          "dolarblue", label, force=force)
    except (Refused, ServerUnavailable, urllib.error.URLError) as exc:
        print(f"    not available: {exc}")
        out.append({"source": "S3", "url": S3_OFICIAL_URL,
                    "status": "unavailable", "reason": str(exc),
                    "guard_kind_column": "not exercised"})
        return out
    extra["source"] = "S3"
    header = [name.lower() for name in extra.get("header", [])]
    extra["guard_kind_column"] = (
        "exercised" if "kind" in header else
        "not exercised: the file has no kind column"
    )
    out.append(extra)
    print(f"    {extra['status']}, {extra.get('rows')} rows, "
          f"kind column: {'kind' in header}")
    if extra["status"] == "downloaded":
        time.sleep(extra["wait"])
    return out


def pass_s4(*, force: bool) -> list[dict]:
    """S4. One file, CC-BY 4.0, cited wherever it is reported.

    Median only in history, so it enters as an index series and as an
    independent check on the level. §2.2's guard keeps it out of everything
    else, and that guard lives in the criteria rather than here.
    """
    label = "S4 historical.csv"
    print(f"  {label}")
    record = fetch_one(S4_URL, BOLIVIA_DIR / "paralelo_historical.csv",
                       "paralelo", label, force=force)
    record["source"] = "S4"
    record["citation"] = S4_CITATION
    header = tuple(n.lower() for n in record.get("header", []))
    record["header_matches_register"] = header == S4_HEADER
    print(f"    {record['status']}, {record.get('rows')} rows, "
          f"header {header}")
    span = record.get("span") or {}
    print(f"    span {span.get('first')} .. {span.get('last')}")
    if record["status"] == "downloaded":
        time.sleep(record["wait"])
    return [record]


def pass_s6(*, force: bool) -> list[dict]:
    """S6. The outside cross, ninety days in one request.

    Register §3 names the ECB daily reference rate as the referee for B15-12.
    The ninety-day file covers 2026-05-25 onward, which contains the whole
    post-event window with a month of run-up, in one request. **The full
    history is a second file and is not fetched here**, because the pre-event
    era also costs seven hundred requests on the other leg and that is a
    decision rather than a step.

    Rates are units of the currency per one euro. The inversion belongs where
    the comparison is made, and is done there in the open.
    """
    label = "S6 ECB 90-day reference rates"
    print(f"  {label}")
    record = fetch_one(S6_ECB_90D_URL, BOLIVIA_DIR / "ecb_eurofxref_90d.xml",
                       "ecb", label, force=force)
    record["source"] = "S6"
    record["role"] = "the outside euro cross, B15-12's referee"
    try:
        rates = ecb_rates(BOLIVIA_DIR.joinpath("ecb_eurofxref_90d.xml")
                          .read_bytes())
    except (OSError, ValueError) as exc:
        rates = {}
        record["parse_failed"] = str(exc)
    record["days"] = len(rates)
    if rates:
        stamps = sorted(rates)
        record["span"] = {"first": stamps[0], "last": stamps[-1]}
        record["usd_present"] = sum(1 for d in rates if "USD" in rates[d])
        print(f"    {record['status']}, {len(rates)} days "
              f"{stamps[0]} .. {stamps[-1]}, "
              f"USD on {record['usd_present']}")
    else:
        print(f"    {record['status']}, no days parsed")
    if record["status"] == "downloaded":
        time.sleep(record["wait"])
    return [record]


def pass_s7(*, force: bool) -> list[dict]:
    """S7. The BCB's whole quotation table, one calendar day per request.

    **Register §3.3 put the euro on the rate index and it is not there.** That
    endpoint takes `?anio=` and its own heading says it is the dollar; the euro
    is on this one, which takes a day, a month and a year. The correction is
    recorded in the results file rather than in the register, which does not
    move.

    **The same window as S2**, from the signing date, so that the two BCB legs
    are read over one span. Every calendar day is asked for, weekends
    included, and a day that answers with another day's table is recorded as a
    fallback rather than skipped: Anexo II §4 says weekends carry the previous
    business day's value, so a repeated table is the statute speaking.

    **`?qdd=` is guilty until it echoes the date.** S2's day endpoint answered
    200 with somebody else's grid twenty-one times before anyone read the
    page's own statement of what it was showing, and this endpoint is the same
    shape from the same institution.
    """
    out: list[dict] = []
    today = date.today()
    days = window_days(SIGNING_DATE, today)
    print(f"  S7 cotizaciones, {len(days)} calendar days "
          f"{SIGNING_DATE} .. {today}, one request each")
    for day in days:
        iso = day.isoformat()
        path = BOLIVIA_DIR / f"bcb_cotizaciones_{iso}.html"
        url = (f"{S7_COTIZACIONES_URL}?qdd={day.day}"
               f"&qmm={day.month}&qaa={day.year}")
        try:
            record = fetch_one(url, path, "bcb", f"S7 {iso}", force=force)
        except (Refused, ServerUnavailable, GuardFailed) as exc:
            print(f"    {iso}: {exc}")
            out.append({"source": "S7", "date": iso, "status": "unavailable",
                        "reason": str(exc)})
            continue
        record["source"] = "S7"
        record["date"] = iso
        try:
            table = cotizaciones(path.read_bytes())
        except GuardFailed as exc:
            record["parse_failed"] = str(exc)
            print(f"    {iso}: {exc}")
            out.append(record)
            continue
        echoed = table["date"]
        record["echoed_date"] = echoed
        record["is_fallback"] = bool(echoed and echoed != iso)
        record["codes"] = len(table["rows"])
        record["repeated_codes"] = table["repeated_codes"]
        # Codes whose row carried a token this file will not decide. Recorded
        # per day rather than counted, because which currency it was is the
        # thing a reader needs and a count of them is not.
        record["ambiguous_codes"] = sorted(table["ambiguous_codes"])
        for code in ("USD", "EUR"):
            if code in table["rows"]:
                record[f"{code.lower()}_row"] = table["rows"][code]
        usd = record.get("usd_row") or []
        eur = record.get("eur_row") or []
        # **The two rows B15-12 reads, printed on every day.** Section 13 step
        # two of the engineering rules: run the description before the test,
        # and print the object rather than a count of it. Fifty-seven lines is
        # the object.
        mark = "  <- another day" if record["is_fallback"] else ""
        print(f"    {iso}  echo {str(echoed):10}  "
              f"USD {usd[0] if usd else '-':>9}  "
              f"EUR {' '.join(f'{v:g}' for v in eur) if eur else '-':>18}"
              f"{'  ambiguous: ' + ','.join(record['ambiguous_codes']) if record['ambiguous_codes'] else ''}"
              f"{mark}")
        out.append(record)
        if record["status"] == "downloaded":
            time.sleep(record["wait"])
    served = [r for r in out if r.get("echoed_date") and not r.get("is_fallback")]
    fallback = [r for r in out if r.get("is_fallback")]
    noecho = [r for r in out if r.get("status") not in ("unavailable",)
              and not r.get("echoed_date")]
    print(f"    {len(served)} days served their own table, "
          f"{len(fallback)} echoed another day, "
          f"{len(noecho)} echoed no date at all")
    if noecho:
        print(f"    no date echoed on: "
              f"{', '.join(r['date'] for r in noecho[:8])}"
              f"{' ...' if len(noecho) > 8 else ''}")
    both = [r for r in out if r.get("usd_row") and r.get("eur_row")]
    print(f"    {len(both)} days carry both a USD row and a EUR row")
    amb = sorted({c for r in out for c in r.get("ambiguous_codes", [])})
    if amb:
        print(f"    codes with an undecidable token somewhere: "
              f"{', '.join(amb)}")
        print(f"    USD ambiguous on "
              f"{sum(1 for r in out if 'USD' in r.get('ambiguous_codes', []))}"
              f" days, EUR on "
              f"{sum(1 for r in out if 'EUR' in r.get('ambiguous_codes', []))}")
    return out


def pass_s5(*, force: bool) -> list[dict]:
    """S5. The auditable mirror, by raw file rather than by clone.

    A clone would drop a nested `.git` inside `data/raw/`, which this project's
    own rules would then have to reason about, and B15-11 needs the current
    snapshot rather than the history. **The 25,627 commits remain the argument
    for this source's auditability**; they are cited, not downloaded.

    The branch is discovered rather than assumed. A raw URL on the wrong branch
    returns a 404 that is indistinguishable from a deleted file, so the first
    file is used to settle the branch and the rest follow it.
    """
    out: list[dict] = []
    branch: str | None = None
    for name in S5_FILES:
        for candidate in (S5_BRANCHES if branch is None else (branch,)):
            url = S5_RAW.format(repo=S5_REPO, branch=candidate, name=name)
            label = f"S5 {candidate}/{name}"
            try:
                record = fetch_one(url, BOLIVIA_DIR / f"mauforonda_{name}",
                                   "github", label, force=force)
            except Refused as exc:
                print(f"  {label}: {exc}")
                continue
            branch = candidate
            record["source"] = "S5"
            record["repo"] = S5_REPO
            record["branch"] = candidate
            record["citation"] = (
                f"github.com/{S5_REPO}, every observation fixed by a commit")
            out.append(record)
            span = record.get("span") or {}
            print(f"  {label}: {record['status']}, {record.get('rows')} rows, "
                  f"{span.get('first')} .. {span.get('last')}")
            if record["status"] == "downloaded":
                time.sleep(record["wait"])
            break
        else:
            print(f"  S5 {name}: not on either branch, recorded as absent")
            out.append({"source": "S5", "file": name, "status": "unavailable",
                        "reason": "404 on every candidate branch"})
    return out


def pass_s2(*, force: bool) -> list[dict]:
    """S2. The daily series in one request, then one request per day of grid.

    **This is the one pass whose request count the register could not have
    budgeted.** §10 put the whole stage in the low tens, on the reading that
    every source here serves ranges. S2 serves a range for the *series* and one
    day at a time for the *microdata*, and the microdata is what B15-6 needs, so
    the post-event window costs one request per calendar day. That is a
    retrieval fact and it is disclosed rather than trimmed: **B15-6 is the
    criterion §7.1 calls the most interesting single result this stage could
    return if it failed**, and it cannot be run on a sample.

    Every calendar day is asked for, weekends included. Anexo II §4 says
    Saturdays, Sundays and holidays carry the previous business day's TCO, so a
    day with no grid is the statute speaking and is recorded as such rather than
    skipped by a holiday calendar this project would otherwise have to invent.
    """
    out: list[dict] = []
    today = date.today()

    label = "S2 daily series CSV"
    url = (f"{S2_CSV_URL}?desde={SIGNING_DATE.isoformat()}"
           f"&hasta={today.isoformat()}")
    print(f"  {label}")
    try:
        record = fetch_one(url, BOLIVIA_DIR / "bcb_tco_series.csv", "bcb",
                           label, force=force)
        record["source"] = "S2"
        record["role"] = "the published TCO series, B15-6's comparison target"
        out.append(record)
        print(f"    {record['status']}, {record.get('rows')} rows, "
              f"{record['truncation']['bytes']:,} bytes")
        if record["status"] == "downloaded":
            time.sleep(record["wait"])
    except (Refused, ServerUnavailable) as exc:
        print(f"    not available: {exc}")
        out.append({"source": "S2", "url": url, "status": "unavailable",
                    "reason": str(exc)})

    days = window_days(SIGNING_DATE, today)
    print(f"  S2 microdata, {len(days)} calendar days "
          f"{SIGNING_DATE} .. {today}, one request each")
    for index, day in enumerate(days, start=1):
        iso = day.isoformat()
        path = BOLIVIA_DIR / f"bcb_tco_detail_{iso}.html"
        try:
            record = fetch_one(f"{S2_DETAIL_URL}?fecha={iso}", path, "bcb",
                               f"S2 {iso}", force=force)
        except (Refused, ServerUnavailable, GuardFailed) as exc:
            print(f"    {iso}: {exc}")
            out.append({"source": "S2", "date": iso, "status": "unavailable",
                        "reason": str(exc)})
            continue
        record["source"] = "S2"
        record["date"] = iso
        # **`has_grid` is not the check and the first version thought it was.**
        # `?fecha=` on a day with no operations returns 200 and the endpoint's
        # default grid, so twenty-one requested days came back byte-identical to
        # 2026-08-18 and every one of them had a grid. The page states the day
        # it is showing in its date input; that is what decides.
        body = path.read_bytes()
        echoed = echoed_date(body)
        record["echoed_date"] = echoed
        record["is_fallback"] = bool(echoed and echoed != iso)
        try:
            detail = bcb_tco_detail(body)
            record["banks"] = len(detail["banks"])
            record["tiers"] = len(detail["tiers"])
            record["has_grid"] = bool(detail["tiers"])
        except GuardFailed as exc:
            record["has_grid"] = False
            record["no_grid_reason"] = str(exc)
        record["own_grid"] = bool(record.get("has_grid")
                                  and not record["is_fallback"])
        out.append(record)
        if index % 10 == 0 or index == len(days):
            own = sum(1 for r in out if r.get("own_grid"))
            back = sum(1 for r in out if r.get("is_fallback"))
            print(f"    {index}/{len(days)}, {own} days with their own grid, "
                  f"{back} showing another day")
        if record["status"] == "downloaded":
            time.sleep(record["wait"])
    return out


def replay(*, acknowledged: bool) -> int:
    """B15-2's known-answer arm on S3: fetch again and compare the closed past.

    **The probe of 2026-08-19 is why this is a mode rather than a note.** The
    response carried ``last-modified`` equal to ``Date`` to the second, so the
    origin builds the file when it is asked, and the archive's first row read
    ``2024-07-21 19:14:15``, whose second-of-minute equals the request's.
    **Either the grid is anchored to the clock or it is anchored to the moment
    of generation**, and those two are a different instrument. One extra request
    separates them and nothing else does.

    The two failures are separated on purpose, because they mean different
    things:

    - **the timestamps move**: the publisher re-derives its grid per request, so
      a row is not addressable and ``digest_prefix`` cannot be an equality test
      on this source at all;
    - **the timestamps hold and a value moves**: the publisher revised a closed
      past, which is the silent revision B15-2 exists to catch.

    Written to a second file. Nothing is overwritten and nothing is deleted.
    """
    archived = BOLIVIA_DIR / "dolarblue_all.csv"
    if not archived.exists():
        print(f"  no {archived.name} on disk; fetch first")
        return 1
    if not acknowledged:
        print("  replay needs --s3-bulk-acknowledged, same terms as the pull")
        return 1

    old_header, old_rows = parse_csv(archived.read_bytes())
    label = "S3 all.csv replay"
    print(f"  {label}")
    record = fetch_one(S3_ALL_URL, BOLIVIA_DIR / "dolarblue_all.replay.csv",
                       "dolarblue", label, force=True)
    new_header, new_rows = parse_csv(
        (BOLIVIA_DIR / "dolarblue_all.replay.csv").read_bytes())

    guard_header(new_header, S3_ALL_HEADER, label)
    old_before = [r for r in old_rows if r and r[0] < PREFIX_CUTOFF]
    new_before = [r for r in new_rows if r and r[0] < PREFIX_CUTOFF]
    old_stamps = [r[0] for r in old_before]
    new_stamps = [r[0] for r in new_before]

    print(f"    archived {len(old_rows):,} rows, replay {len(new_rows):,}")
    print(f"    before {PREFIX_CUTOFF}: {len(old_before):,} and "
          f"{len(new_before):,}")

    if old_stamps == new_stamps:
        print("    timestamps: identical on the closed past")
    else:
        first = next((a for a, b in zip(old_stamps, new_stamps) if a != b),
                     None)
        print(f"    TIMESTAMPS MOVED. first disagreement at {first!r} against "
              f"{new_stamps[old_stamps.index(first)] if first else '-'!r}")
        print("    The grid is re-derived per request. A row on this source is "
              "not addressable by its timestamp, so digest_prefix cannot be an "
              "equality test here and B15-2 needs a different key.")
        return 1

    old_digest = digest_prefix(old_before, PREFIX_CUTOFF)
    new_digest = digest_prefix(new_before, PREFIX_CUTOFF)
    if old_digest == new_digest:
        print(f"    prefix digest reproduces: {old_digest[:16]}...")
        print("    B15-2 passes on S3: the closed past did not move")
        return 0
    changed = [(a[0], a, b) for a, b in zip(old_before, new_before) if a != b]
    print(f"    PREFIX DIGEST MOVED on {len(changed)} row(s). "
          f"The timestamps held, so this is a revision of a closed past.")
    for when, a, b in changed[:10]:
        print(f"      {when}: {a[1:]} -> {b[1:]}")
    return 1


def probe_s2() -> int:
    """Fetch S2's page, store it, and print its form so the parameters are read.

    **B15-6 is the one criterion whose failure §7.1 calls the most interesting
    result this stage could return**, and it needs the BCB's own per-bank
    microdata. The endpoint is known and its query parameters are not. Guessing
    them produces a 200 with an empty table, which is the failure mode that
    looks like a finding, so the form is read instead.
    """
    label = "S2 tco_reporte_detalle_historico.php"
    print(f"  {label}\n  {S2_DETAIL_URL}")
    try:
        body, headers, declared = download(S2_DETAIL_URL)
    except (Refused, ServerUnavailable, urllib.error.URLError) as exc:
        print(f"    not available: {exc}")
        return 1
    path = BOLIVIA_DIR / "bcb_tco_reporte_page.html"
    write_atomic(path, body)
    fmt = sniff(body)
    print(f"    HTTP 200, {len(body):,} bytes, sniffed {fmt}, "
          f"content-type {headers.get('content-type')}")
    print(f"    stored as {path.name}")

    from html.parser import HTMLParser

    class Forms(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.found: list[str] = []
            self._select: str | None = None

        def handle_starttag(self, tag: str, attrs) -> None:
            a = dict(attrs)
            if tag == "form":
                self.found.append(
                    f"form action={a.get('action')!r} method={a.get('method')!r}")
            elif tag == "input":
                self.found.append(
                    f"  input name={a.get('name')!r} type={a.get('type')!r} "
                    f"value={a.get('value')!r}")
            elif tag == "select":
                self._select = a.get("name")
                self.found.append(f"  select name={a.get('name')!r}")
            elif tag == "option" and self._select:
                self.found.append(f"    option value={a.get('value')!r}")
            elif tag == "a" and any(
                    ext in a.get("href", "").lower()
                    for ext in (".csv", ".xls", ".xlsx")):
                # The extension test runs on the whole href, not on its tail.
                # `export.csv?d=1` ends in `?d=1`, and an endswith test on the
                # tail misses exactly the links worth finding.
                self.found.append(f"  link href={a.get('href')!r}")

        def handle_endtag(self, tag: str) -> None:
            if tag == "select":
                self._select = None

    parser = Forms()
    parser.feed(decode(body))
    if parser.found:
        print("\n    the page's own form, verbatim:")
        for line in parser.found[:60]:
            print(f"    {line}")
        if len(parser.found) > 60:
            print(f"    ... {len(parser.found) - 60} more")
    else:
        print("\n    no form found; the table is probably built by script.")
        print("    Grep the stored file for the endpoint it calls.")
    for needle in ("csv", "export", "descargar", "ajax", "fetch("):
        n = decode(body).lower().count(needle)
        if n:
            print(f"    the page mentions {needle!r} {n} time(s)")
    return 0


def probe_euro() -> int:
    """B15-12's source: find how the BCB's rate index selects a currency.

    §5 B15-12 wants the BCB's `Bs / Euro` against the ECB daily reference rate
    times the BCB's `Bs / Dólar`. The dollar side is S1 and S2 and is in hand;
    the euro side is an endpoint nobody here has seen. **Its parameter is read
    off the index page's own form**, because a guessed parameter on a BCB
    endpoint has already been observed returning 200 and a different table.
    """
    label = "S6 index"
    print(f"  {label}\n  {S6_INDEX_URL}")
    try:
        body, headers, declared = download(S6_INDEX_URL)
    except (Refused, ServerUnavailable, urllib.error.URLError) as exc:
        print(f"    not available: {exc}")
        return 1
    path = BOLIVIA_DIR / "bcb_tipos_index.html"
    write_atomic(path, body)
    print(f"    HTTP 200, {len(body):,} bytes, sniffed {sniff(body)}, "
          f"content-type {headers.get('content-type')}")
    print(f"    stored as {path.name}")
    found = describe_form(body)
    if found:
        print("\n    the page's own form and data links, verbatim:")
        for line in found:
            print(f"    {line}")
    else:
        print("\n    no form and no data links found.")
    text = decode(body)
    print()
    for needle in ("euro", "eur", "deg", "moneda", "divisa", "dolar", "dólar"):
        n = text.lower().count(needle)
        if n:
            print(f"    the page mentions {needle!r} {n} time(s)")
    import re as _re
    currencies = sorted(set(_re.findall(
        r'(?:moneda|currency|divisa)[=:\s"\']{0,4}([A-Za-z]{2,12})',
        text, _re.I)))[:20]
    if currencies:
        print(f"    tokens following a currency-looking key: {currencies}")
    return 0


def probe_headers() -> int:
    """One request per source, every header printed, nothing written.

    **This is the step that stops a documented rate limit being believed.**
    elTOQUE's specification said 60 a minute; the key carried ten per 156
    seconds, and the difference was a ten-hour run against a thirty-five minute
    one. It also settles what ``xls.php`` actually serves before any parser is
    committed to, which is the other thing this stage cannot look up.
    """
    targets = [
        ("S1 2026 xls", bcb_url(2026, "xls")),
        ("S1 2026 ods", bcb_url(2026, "ods")),
        ("S3 all.csv", S3_ALL_URL),
        ("S3 oficial.csv", S3_OFICIAL_URL),
    ]
    for label, url in targets:
        print(f"\n  {label}: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310, E501
                body = resp.read()
                print(f"    HTTP {resp.status}")
                for key, value in sorted(resp.headers.items()):
                    print(f"      {key}: {value}")
        except urllib.error.HTTPError as exc:
            body = exc.read()
            print(f"    HTTP {exc.code} {exc.reason}")
            for key, value in sorted(exc.headers.items()):
                print(f"      {key}: {value}")
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"    unreachable: {exc}")
            continue
        fmt = sniff(body)
        print(f"    {len(body):,} bytes, sniffed as {fmt}")
        if fmt in ("csv", "html"):
            # Every control character escaped, not just the newline. The first
            # version escaped `\n` alone and the file turned out to use CRLF,
            # so the bare `\r` returned the terminal's cursor and the header was
            # overwritten by the row after it. **A carriage return in a debug
            # print is a silent truncation of the thing being debugged.**
            text = body[:400].decode("utf-8", "replace")
            text = text.replace("\\", "\\\\").replace("\r", "\\r")
            text = text.replace("\n", "\\n").replace("\t", "\\t")
            print(f"    first 400 bytes: {text}")
        print(f"    clock now: {time.time():.0f}")
        time.sleep(5.0)
    print("\n  nothing written")
    return 0


def check() -> int:
    """Classify what is on disk against the manifest, and fetch nothing."""
    if not MANIFEST.exists():
        print(f"no manifest at {MANIFEST.relative_to(ROOT)}; nothing to check")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded = {row["file"]: row for row in manifest.get("responses", [])
                if "file" in row}
    files = sorted(BOLIVIA_DIR.glob("*")) if BOLIVIA_DIR.exists() else []
    files = [p for p in files if p.is_file() and ".expired" not in p.name]
    print(f"  {len(files)} files on disk, {len(recorded)} in the manifest")
    bad = 0
    for path in files:
        if path.name not in recorded:
            print(f"  {path.name}: not in the manifest")
            continue
        body = path.read_bytes()
        if sha256(body) != recorded[path.name].get("sha256_body"):
            print(f"  {path.name}: body digest differs from the manifest")
            bad += 1
    missing = sorted(set(recorded) - {p.name for p in files})
    for name in missing:
        print(f"  {name}: in the manifest and not on disk")
    print(f"  {bad} mismatched, {len(missing)} missing")
    return 0 if bad == 0 and not missing else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is on disk against the manifest, exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and its cost, fetch nothing")
    ap.add_argument("--probe-headers", action="store_true",
                    help="one request per source, print every header, write "
                         "nothing")
    ap.add_argument("--force", action="store_true",
                    help="refetch even if a file is on disk")
    ap.add_argument("--s3-bulk-acknowledged", action="store_true",
                    dest="s3_ok",
                    help="pull S3's bulk history. prereg §10 registers the "
                         "terms tension; this flag is the record of the "
                         "author's resolution of it")
    ap.add_argument("--probe-euro", action="store_true", dest="probe_euro",
                    help="fetch the BCB's rate index and print its form, so "
                         "B15-12's currency parameter is read not guessed")
    ap.add_argument("--probe-s2", action="store_true", dest="probe_s2",
                    help="fetch S2's page and print its form, so B15-6's query "
                         "parameters are read rather than guessed")
    ap.add_argument("--replay", action="store_true",
                    help="B15-2 on S3: fetch again to a second file and check "
                         "that the closed past did not move")
    ap.add_argument("--pass", dest="which", default="all",
                    choices=("s1", "s2", "s3", "s4", "s5", "s6", "s7", "all"),
                    help="which pass to run")
    args = ap.parse_args()

    if args.check:
        return check()

    days = window_days(WINDOW_OPEN_DATE, date.today())
    print("Bolivia, official and parallel rates, for stage B15")
    print(f"  window {WINDOW_OPEN_DATE} to {date.today()}, {len(days):,} days")
    print(f"  event  {EVENT_DATE}, prefix digest cut at {PREFIX_CUTOFF}")
    print(f"  S1     {len(BCB_YEARS)} years x {len(BCB_FORMATS)} formats = "
          f"{len(BCB_YEARS) * len(BCB_FORMATS)} requests")
    s2_days = len(window_days(SIGNING_DATE, date.today()))
    print(f"  S2     1 series CSV + {s2_days} daily microdata requests, "
          f"from {SIGNING_DATE}")
    print("  S3     1 bulk file, plus 1 attempt at oficial.csv")
    print("  S4     1 file, CC-BY 4.0")
    print(f"  S5     {len(S5_FILES)} raw files from github.com/{S5_REPO}")
    print("  S6     1 file, the ECB's 90-day reference rates")
    print(f"  S7     {s2_days} daily quotation tables, from {SIGNING_DATE}")
    total = (len(BCB_YEARS) * len(BCB_FORMATS) + 1 + s2_days + 2 + 1
             + len(S5_FILES) + 1 + s2_days)
    print(f"  total  {total} requests")
    print("  **S7 costs one request per day for the same reason S2 does.**")
    print("    The euro is not on the endpoint the register named; it is on a")
    print("    per-day quotation table, so B15-12's referee costs a second")
    print("    daily leg over the same window. The pre-event era would cost")
    print(f"    {len(days) - s2_days:,} more on S7 plus the ECB's full history,")
    print("    and is not fetched.")
    print(f"  **S2's daily microdata is why this is not the low tens §10")
    print(f"    budgeted.** That section costed the stage on the reading that")
    print(f"    every source serves ranges; S2 serves the series as a range and")
    print(f"    the microdata one day at a time, and B15-6 needs the microdata.")
    print(f"    Disclosed rather than sampled.\n")

    try:
        guard_span(days)
        guard_press_free(registered_constants())
    except GuardFailed as exc:
        print(f"  GUARD FAILED before any request: {exc}", file=sys.stderr)
        return 1
    print("  guard_span: every day 86,399s, La Paz has no DST")
    print("  guard_press_free: no registered constant is a press or summary "
          "number\n")

    if args.probe_headers:
        return probe_headers()

    if args.probe_s2:
        BOLIVIA_DIR.mkdir(parents=True, exist_ok=True)
        return probe_s2()

    if args.probe_euro:
        BOLIVIA_DIR.mkdir(parents=True, exist_ok=True)
        return probe_euro()

    if args.replay:
        try:
            return replay(acknowledged=args.s3_ok)
        except GuardFailed as exc:
            print(f"\n  GUARD FAILED: {exc}", file=sys.stderr)
            return 1

    if args.dry_run:
        print("  dry run, nothing fetched")
        if not args.s3_ok:
            print(f"\n  S3 terms, prereg §10:\n    {S3_TERMS}")
        return 0

    BOLIVIA_DIR.mkdir(parents=True, exist_ok=True)
    responses: list[dict] = []
    failure: str | None = None
    # **The manifest is written whatever happens below.** The first run of this
    # file fetched all seven registered payloads and then died on a guard while
    # probing an eighth that gates nothing, and because the manifest was written
    # after the passes, B15-1's entire record went with it. Downloaded data is
    # irreproducible and its provenance is part of the data; a later error must
    # not be able to discard the account of an earlier success.
    try:
        if args.which in ("s1", "all"):
            responses += pass_s1(force=args.force)
        if args.which in ("s2", "all"):
            responses += pass_s2(force=args.force)
        if args.which in ("s3", "all"):
            responses += pass_s3(force=args.force, acknowledged=args.s3_ok)
        if args.which in ("s4", "all"):
            responses += pass_s4(force=args.force)
        if args.which in ("s5", "all"):
            responses += pass_s5(force=args.force)
        if args.which in ("s6", "all"):
            responses += pass_s6(force=args.force)
        if args.which in ("s7", "all"):
            responses += pass_s7(force=args.force)
    except GuardFailed as exc:
        failure = f"GuardFailed: {exc}"
        print(f"\n  GUARD FAILED: {exc}", file=sys.stderr)
        print("  Nothing downstream may run. prereg §6.2.", file=sys.stderr)
    except (Refused, RateLimited, ServerUnavailable) as exc:
        failure = f"{type(exc).__name__}: {exc}"
        print(f"\n  {type(exc).__name__}: {exc}", file=sys.stderr)
        print("  The run resumes from disk; nothing was lost.", file=sys.stderr)

    # S3's header is checked once, here, rather than inside `describe`, so that
    # the bytes are on disk before the check can stop the run. A header that has
    # moved is a finding to read, not a download to throw away.
    for record in responses:
        if record.get("file") == "dolarblue_all.csv" and record.get("header"):
            try:
                guard_header(tuple(record["header"]), S3_ALL_HEADER,
                             "S3 all.csv")
                print("  guard_header: S3's columns are the registered five")
            except GuardFailed as exc:
                failure = failure or f"GuardFailed: {exc}"
                print(f"\n  GUARD FAILED: {exc}", file=sys.stderr)

    # **A pass records its own payloads and keeps everybody else's.**
    #
    # ``responses`` starts empty on every run and this file is written whole, so
    # a run of ``--pass s2`` used to replace the manifest with S2's rows alone
    # and take the account of S1, S3, S4 and S5 with it. **That is the same
    # failure the comment above the passes describes**, one hundred lines up:
    # a later step must not be able to discard the account of an earlier
    # success. It was repaired for the error path and not for the partial-pass
    # path, so the hole stayed open on the one axis nobody had been bitten on
    # yet.
    #
    # It bit later. `experiments/b15_typing.py` read `generated_utc` off this
    # file as the moment S3 was fetched, and by then the copy on disk had been
    # written by an S2 pass an hour and a half after `dolarblue_all.csv`
    # landed. The clock that comparison produced set B15-4's answer.
    #
    # **Merged on `file`, newest wins.** A payload this run did not touch keeps
    # the row it had; a payload it did fetch overwrites the older row, because
    # the fresh digest describes the bytes now on disk. `generated_utc` is this
    # run's stamp and says so, which is why the merge cannot make it a fetch
    # time for anything: `run_covers` names the passes that ran.
    previous: list[dict] = []
    if MANIFEST.exists():
        try:
            previous = json.loads(
                MANIFEST.read_text(encoding="utf-8")).get("responses", [])
        except (OSError, json.JSONDecodeError) as exc:
            # Named rather than swallowed. A manifest that cannot be read is a
            # thing to know about; it is not a reason to refuse to write the
            # rows this run just earned.
            print(f"  previous manifest unreadable, not merged: {exc}",
                  file=sys.stderr)
    merged = {row.get("file"): row for row in previous if row.get("file")}
    merged.update({row.get("file"): row for row in responses if row.get("file")})
    unkeyed = [row for row in responses if not row.get("file")]
    all_responses = sorted(merged.values(),
                           key=lambda r: str(r.get("file"))) + unkeyed
    kept = len(all_responses) - len(responses)

    RAW.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": utc_stamp(),
                "stage": "B15",
                "authority": "docs/b15_bolivia_prereg.md",
                "window": [WINDOW_OPEN_DATE.isoformat(),
                           date.today().isoformat()],
                "event_date": EVENT_DATE.isoformat(),
                "prefix_cutoff": PREFIX_CUTOFF,
                "provenance": (
                    "S1: Banco Central de Bolivia, Tipo de Cambio Oficial, "
                    "annual table, compra and venta as separate columns, one "
                    "file per year, fetched in two serialisations because the "
                    "payload format of xls.php is not documented and the "
                    "standard library does not read BIFF. S3: "
                    "dolarbluebolivia.click, best available offer on each side "
                    "of one venue's Binance P2P book at 15-minute resolution, "
                    f"reused under terms requiring the attribution "
                    f"'{S3_ATTRIBUTION}'. The parallel leg of this stage is "
                    "one venue's book and not 'the Bolivian parallel market'; "
                    "b15_bolivia_prereg.md §3.6 A3 and §8. data/raw/ is "
                    "excluded from the repository and only this manifest is "
                    "tracked."
                ),
                "s3_terms": S3_TERMS,
                "s3_bulk_acknowledged": bool(args.s3_ok),
                "guards_run": {
                    "guard_span": "pass",
                    "guard_press_free": "pass",
                    "guard_truncation": "per payload, see responses",
                    "guard_header": "S3 all.csv only",
                },
                "run_failed": failure,
                "run_covers": args.which,
                "responses": all_responses,
            },
            indent=2, sort_keys=True,
        ) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")
    print(f"  {len(responses)} payloads recorded this run, "
          f"{max(0, kept)} carried over from earlier runs, "
          f"{len(all_responses)} in the manifest")
    if failure:
        print(f"  the run did not complete: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
