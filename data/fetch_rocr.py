"""Retrieve the NRSRO rating-history (ROCR) files that B11 counts loops on.

Registered before the run, and unchanged since. It carries two gates:
**C11-1**, whether the corporate files actually populate ``CR``/``PV``/``MD``,
and **C11-2**, whether the archive is cumulative or rolling. Both are answered
by reading bytes this file retrieves, and both are answered **before** any bulk
download, which is the whole reason the probe modes exist separately from the
pull mode.

Usage::

    python data/fetch_rocr.py --discover     # what the page looks like, decide nothing
    python data/fetch_rocr.py --index        # parse the listing, download no CSV
    python data/fetch_rocr.py --peek         # range-read head+tail of a few files
    python data/fetch_rocr.py --check        # classify what is on disk, fetch nothing
    python data/fetch_rocr.py --pull Corporate --yes   # the bulk download

**Run them in that order.** ``--pull`` is written here because a resumable
downloader belongs next to the index it reads, not because this round runs it.
C11-2 is read off ``--index`` and ``--peek``; if the archive turns out to be
rolling, the window shrinks and the pull is a different pull.

Endpoint, verified 2026-08-17 as serving a static listing::

    https://ratingshistory.info/

Files hang off ``https://ratingshistory.info/api/public/<name>.csv`` where the
name is ``YYYYMMDD <agency> <asset class>.csv``, spaces and all. The listing's
anchor text carries a line count per file, e.g.::

    20260810 Egan-Jones Ratings Company Corporate.csv (578778 lines)

That count is free measurement and this file keeps it for two uses. It sizes the
download before anything is downloaded, and after a pull it is an independent
check on the bytes that arrived, which is the cheapest truncation detector
available here: a short file that still parses as CSV is exactly the failure
the project's engineering rule 6 says must not be read silently.

Who is not here
---------------
**S&P Global Ratings is not on this site.** The seven agencies published are
Egan-Jones, Fitch, Japan Credit Rating Agency, Demotech, Kroll, Moody's and
DBRS. S&P posts its own 17g-7(b) files behind ``disclosure.spglobal.com``,
which 302s to a login. The B11 ruling of 2026-08-17 is to try that free
registration, because S&P names the distressed exchanges in its default study
and a same-agency join costs no name matching. Until that lands, the rating path
comes from the agencies above and the match rate is a measured quantity that
gets reported with C11-0 rather than assumed.

Why there is a discovery mode
-----------------------------
The listing's markup was read once, through a converter, and a converter is not
the page. ``--discover`` dumps the raw bytes' shape and the first raw ``href``
values so a human confirms the parse target before any mode trusts it. Same
accommodation ``data/fetch_cex.py`` makes, same reason: a parser that guesses a
layout returns rows rather than an error.

What the filename parse refuses to guess
----------------------------------------
The asset class is the filename's tail, and four of the classes are two words
(``US Public``, ``INT Public``, ``Other ABS``, ``Other SFP``). Splitting on
whitespace would silently file ``US Public`` under ``Public`` and hand the
agency an extra token. So the parse matches against a known suffix list,
longest first, and a name matching nothing is recorded as unparsed and counted
in the report. **It is never bucketed by a fallback rule**, because a fallback
here produces a plausible agency name for a file nobody looked at.

Nothing in this file deletes
----------------------------
``--force`` renames the superseded file to ``<name>.expired_<tag>`` and leaves
it in place, per the project's engineering rule 5. Partial downloads live at ``<name>.part``
and are resumed, never truncated and never removed; a ``.part`` that fails its
size check stays a ``.part`` so the next run sees it as unfinished rather than
finding a short CSV that reads fine.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ROCR = RAW / "rocr"
PEEK = ROCR / "peek"
INDEX = RAW / "rocr_index.json"
MANIFEST = RAW / "rocr_manifest.json"

LISTING_URL = "https://ratingshistory.info/"
FILE_PREFIX = "https://ratingshistory.info/api/public/"

TIMEOUT_SECONDS = 300
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

#: Two-word classes first, so ``US Public`` is not read as ``Public``.
ASSET_CLASSES = (
    "INT Public",
    "Other ABS",
    "Other SFP",
    "US Public",
    "ABCP",
    "CDO",
    "CLO",
    "CMBS",
    "Corporate",
    "Financial",
    "Insurance",
    "RMBS",
    "Sovereign",
)

#: The listing was rejected by no publisher so far, but BLS rejected a bare
#: agent with a 403 on this project once already (``data/fetch_cex.py``), and a
#: browser-shaped default costs nothing.
#: This repository identifies itself to every publisher it reads. That is the
#: convention across the other fetchers here and it is the convention because
#: a publisher who wants to refuse an automated reader is entitled to, and a
#: header that hides the reader takes that decision away from them. If a
#: publisher filters on the header, ``--user-agent`` overrides it for one run
#: on the machine doing the reading; the default that ships stays honest.
DEFAULT_USER_AGENT = "monetary-topology/1.0 (academic replication; contact via repo)"

#: Tokens the ROCR schema uses for the fields C11-1 is about. The peek report
#: flags a column whose name contains one of these, and then prints the raw
#: header anyway. **The flag is a hint, not the ruling**: which column is the
#: rating action date is decided by a human reading the values, because the
#: header names are the publisher's and were never verified here.
FIELD_HINTS = ("RAD", "RAC", "CR", "PV", "MD", "LEI", "CIK", "CUSIP", "ISIN")


class Forbidden(Exception):
    """The publisher refused the request, which is a header problem here."""


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utcstamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


#: Sub-delimiters and the characters these filenames actually carry, kept
#: literal so the encoded path stays readable. Only the genuinely unsafe ones,
#: spaces above all, get percent-encoded.
PATH_SAFE = "/:@&=+$,;~()'!*"


def encode_path(url: str) -> str:
    """Percent-encode a URL's path so ``http.client`` will send it.

    The listing writes filenames into ``href`` with literal spaces
    (``.../20241028 DBRS Corporate.csv``). ``http.client`` refuses a request
    line containing a space, so every mode died on the first fetch. Normalising
    here rather than at each call site means one place decides, and the index
    keeps the human-readable form.

    ``unquote`` first, so a listing that starts percent-encoding tomorrow does
    not get double-encoded. That inverse is exact for these names because none
    of them contains a literal ``%``; a filename that did would round-trip
    wrong, and that is the one assumption this function makes.
    """
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe=PATH_SAFE)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def request(url: str, agent: str, headers: dict[str, str] | None = None):
    """Open ``url``, retrying 5xx only. A 4xx is a decision, not a hiccup."""
    url = encode_path(url)
    merged = {"User-Agent": agent, "Accept": "*/*"}
    merged.update(headers or {})
    last: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        req = urllib.request.Request(url, headers=merged)
        try:
            return urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise Forbidden(
                    f"HTTP 403 for {url}\n"
                    "The publisher refused this client. That is their decision to "
                    "make and this file does not work around it: fetch the file in "
                    "a browser yourself and drop it in "
                    f"{ROCR} under the same name; every later mode reads the cache."
                ) from exc
            if 500 <= exc.code < 600:
                last = exc
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as exc:
            last = exc
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise ServerUnavailable(f"{url} failed {RETRY_ATTEMPTS} times: {last}")


# --------------------------------------------------------------------------
# the listing
# --------------------------------------------------------------------------


class LinkHarvest(HTMLParser):
    """Collect ``(href, anchor text)`` for every link on the listing.

    Deliberately dumb: it filters nothing. Filtering happens downstream where
    the report can say how many links were dropped and why.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text).strip()))
            self._href = None
            self._text = []


LINE_COUNT_RE = re.compile(r"\((\d[\d,]*)\s+lines?\)")
NAME_RE = re.compile(r"^(\d{8})\s+(.+?)\.csv$", re.IGNORECASE)


def split_class(stem: str) -> tuple[str, str] | None:
    """``"Moody's Investors Service US Public"`` -> agency, class.

    Returns ``None`` when the tail matches no known class, which the caller
    records rather than repairs.
    """
    for cls in ASSET_CLASSES:
        if stem.endswith(" " + cls):
            return stem[: -(len(cls) + 1)].strip(), cls
    return None


def parse_listing(html: str) -> dict:
    harvest = LinkHarvest()
    harvest.feed(html)

    entries: list[dict] = []
    unparsed: list[dict] = []
    skipped = 0

    for href, text in harvest.links:
        absolute = urllib.parse.urljoin(LISTING_URL, href)
        if not absolute.startswith(FILE_PREFIX):
            skipped += 1
            continue
        name = urllib.parse.unquote(absolute[len(FILE_PREFIX):])
        match = NAME_RE.match(name)
        lines_match = LINE_COUNT_RE.search(text)
        lines = int(lines_match.group(1).replace(",", "")) if lines_match else None
        if not match:
            unparsed.append({"name": name, "url": absolute, "reason": "filename"})
            continue
        stamp, stem = match.group(1), match.group(2)
        split = split_class(stem)
        if split is None:
            unparsed.append({"name": name, "url": absolute, "reason": "asset class"})
            continue
        agency, asset_class = split
        entries.append(
            {
                "name": name,
                "url": absolute,
                "snapshot": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}",
                "agency": agency,
                "asset_class": asset_class,
                "listed_lines": lines,
            }
        )

    entries.sort(key=lambda e: (e["agency"], e["asset_class"], e["snapshot"]))
    return {"entries": entries, "unparsed": unparsed, "non_file_links": skipped}


def newest_per_pair(entries: list[dict]) -> dict[tuple[str, str], dict]:
    newest: dict[tuple[str, str], dict] = {}
    for entry in entries:
        key = (entry["agency"], entry["asset_class"])
        if key not in newest or entry["snapshot"] > newest[key]["snapshot"]:
            newest[key] = entry
    return newest


def cmd_discover(args) -> int:
    with request(LISTING_URL, args.user_agent) as response:
        body = response.read()
    text = body.decode("utf-8", errors="replace")
    print(f"listing bytes      : {len(body)}")
    print(f"content-type       : {response.headers.get('Content-Type')}")
    print(f"sha256             : {hashlib.sha256(body).hexdigest()}")
    print()
    print("--- first 1200 characters, verbatim ---")
    print(text[:1200])
    print("--- end ---")
    print()
    harvest = LinkHarvest()
    harvest.feed(text)
    print(f"anchors found      : {len(harvest.links)}")
    print()
    print("--- first 12 hrefs, raw, before any unquoting ---")
    for href, label in harvest.links[:12]:
        print(f"  href={href!r}")
        print(f"  text={label!r}")
    print("--- end ---")
    print()
    print("Nothing was written. If the hrefs above are not what --index should")
    print("parse, the parser is wrong and no later mode should be run.")
    return 0


def cmd_index(args) -> int:
    with request(LISTING_URL, args.user_agent) as response:
        body = response.read()
    parsed = parse_listing(body.decode("utf-8", errors="replace"))
    entries = parsed["entries"]

    if not entries:
        print("No file links parsed. Run --discover; the layout moved.")
        return 2

    ROCR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": LISTING_URL,
        "retrieved_utc": utcstamp(),
        "listing_sha256": hashlib.sha256(body).hexdigest(),
        "entry_count": len(entries),
        "entries": entries,
        "unparsed": parsed["unparsed"],
        "non_file_links": parsed["non_file_links"],
    }
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    snapshots = sorted({e["snapshot"] for e in entries})
    print(f"file links parsed  : {len(entries)}")
    print(f"unparsed names     : {len(parsed['unparsed'])}")
    print(f"non-file anchors   : {parsed['non_file_links']}")
    print(f"snapshot range     : {snapshots[0]} .. {snapshots[-1]}")
    print(f"distinct snapshots : {len(snapshots)}")
    print(f"written            : {INDEX}")
    print()

    print("--- C11-2, part one: how far back do the SNAPSHOTS go ---")
    print("A rolling archive shows a short snapshot range. That is not yet the")
    print("gate: one snapshot may still carry the whole history. --peek settles it.")
    print()
    by_agency: dict[str, list[str]] = {}
    for entry in entries:
        by_agency.setdefault(entry["agency"], []).append(entry["snapshot"])
    for agency in sorted(by_agency):
        stamps = sorted(set(by_agency[agency]))
        print(f"  {agency:<40s} {len(stamps):>4d} snapshots  {stamps[0]} .. {stamps[-1]}")
    print()

    print("--- newest snapshot per agency x asset class, with listed line counts ---")
    newest = newest_per_pair(entries)
    total_lines = 0
    for (agency, asset_class), entry in sorted(newest.items()):
        lines = entry["listed_lines"]
        total_lines += lines or 0
        shown = f"{lines:,}" if lines is not None else "unlisted"
        print(f"  {agency:<40s} {asset_class:<12s} {entry['snapshot']}  {shown:>14s} lines")
    print()
    print(f"total lines across newest of every pair : {total_lines:,}")
    corporate = {k: v for k, v in newest.items() if k[1] in ("Corporate", "Financial", "Insurance")}
    corp_lines = sum(v["listed_lines"] or 0 for v in corporate.values())
    print(f"of which Corporate + Financial + Insurance : {corp_lines:,}")
    print()
    print("A line count in the hundreds of thousands on a single snapshot is the")
    print("first evidence that a file is a full history rather than one month of")
    print("actions. --peek reads the dates and settles it.")
    return 0


# --------------------------------------------------------------------------
# the peek: bytes, not files
# --------------------------------------------------------------------------


def range_read(url: str, agent: str, spec: str, cap: int) -> tuple[bytes, bool]:
    """Read at most ``cap`` bytes of ``url`` under Range ``spec``.

    Returns ``(payload, range_honored)``. A server that ignores Range answers
    200 with the whole body; this reads ``cap`` bytes and closes, so an ignored
    Range costs one buffer rather than the whole file. That guard is the reason
    this is not written as a plain ``urlopen().read(cap)``.
    """
    with request(url, agent, {"Range": f"bytes={spec}"}) as response:
        honored = response.status == 206
        payload = response.read(cap)
    return payload, honored


def whole_lines(payload: bytes, drop_first: bool, drop_last: bool) -> list[str]:
    """Decode a byte window into lines that are certainly complete.

    A window cut mid-line yields a partial record at whichever end was cut, and
    a partial CSV record parses without complaint into a row with the wrong
    number of fields. Both suspect ends are dropped by construction.
    """
    text = payload.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if drop_first and lines:
        lines = lines[1:]
    if drop_last and lines:
        lines = lines[:-1]
    return lines


DATE_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})")


def scan_dates(rows: list[list[str]], column: int) -> tuple[str, str] | None:
    seen = [m.group(0).strip() for m in (DATE_RE.match(r[column]) for r in rows if column < len(r)) if m]
    if not seen:
        return None
    return min(seen), max(seen)


def cmd_peek(args) -> int:
    if not INDEX.exists():
        print(f"No index at {INDEX}. Run --index first.")
        return 2
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    newest = newest_per_pair(payload["entries"])
    targets = [e for (a, c), e in sorted(newest.items()) if c == args.peek_class]
    if args.agency:
        needle = args.agency.lower()
        targets = [e for e in targets if needle in e["agency"].lower()]
    if not targets:
        print(f"No {args.peek_class} files in the index for that filter.")
        return 2
    # Biggest first. The C11-2 question is whether one snapshot carries the
    # whole history, and the file with the most rows is the one whose answer
    # is least likely to be an artefact of a thin publisher. Alphabetical order
    # put DBRS at 9,536 rows ahead of Egan-Jones at 578,778.
    targets.sort(key=lambda e: (-(e["listed_lines"] or 0), e["agency"]))
    targets = targets[: args.limit]

    PEEK.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []

    for entry in targets:
        print("=" * 78)
        print(f"{entry['agency']} / {entry['asset_class']} / snapshot {entry['snapshot']}")
        listed = entry["listed_lines"]
        print(f"listed lines: {listed:,}" if listed else "listed lines: unlisted")
        record: dict = {
            "agency": entry["agency"],
            "asset_class": entry["asset_class"],
            "snapshot": entry["snapshot"],
            "url": entry["url"],
            "listed_lines": listed,
        }

        head, honored = range_read(entry["url"], args.user_agent, f"0-{args.peek_bytes - 1}", args.peek_bytes)
        record["range_honored"] = honored
        record["head_bytes"] = len(head)
        stem = re.sub(r"[^A-Za-z0-9]+", "_", f"{entry['agency']}_{entry['asset_class']}_{entry['snapshot']}")
        (PEEK / f"{stem}.head").write_bytes(head)

        if not honored:
            print("  Range NOT honored (server answered 200). Head sample kept,")
            print("  tail sample skipped so the whole file is not pulled by accident.")

        head_lines = whole_lines(head, drop_first=False, drop_last=True)
        if not head_lines:
            print("  Head window held no complete line. Raise --peek-bytes.")
            record["error"] = "no complete line in head window"
            report.append(record)
            continue

        reader = csv.reader(io.StringIO("\n".join(head_lines)))
        rows = [r for r in reader if r]
        header = rows[0]
        body_rows = rows[1:]
        record["header"] = header
        record["head_rows_sampled"] = len(body_rows)

        print(f"  columns ({len(header)}):")
        for i, name in enumerate(header):
            flag = ""
            upper = re.sub(r"[^A-Z]", "", name.upper())
            for hint in FIELD_HINTS:
                if hint in upper:
                    flag = f"   <-- contains {hint}"
                    break
            samples = [r[i] for r in body_rows[:60] if i < len(r) and r[i].strip()][:3]
            print(f"    [{i:>2d}] {name!r:<34s} e.g. {samples}{flag}")

        filled: dict[str, float] = {}
        for i, name in enumerate(header):
            if not body_rows:
                break
            nonempty = sum(1 for r in body_rows if i < len(r) and r[i].strip())
            filled[name] = round(nonempty / len(body_rows), 4)
        record["head_fill_rate"] = filled

        date_cols = [i for i, r in enumerate(body_rows[0]) if DATE_RE.match(r)] if body_rows else []
        record["date_like_columns"] = date_cols
        for column in date_cols:
            span = scan_dates(body_rows, column)
            if span:
                print(f"  column [{column}] {header[column]!r} dates in head sample: {span[0]} .. {span[1]}")
                record.setdefault("head_date_spans", {})[header[column]] = list(span)

        if honored:
            tail, tail_ok = range_read(entry["url"], args.user_agent, f"-{args.peek_bytes}", args.peek_bytes)
            record["tail_bytes"] = len(tail)
            (PEEK / f"{stem}.tail").write_bytes(tail)
            if tail_ok:
                tail_lines = whole_lines(tail, drop_first=True, drop_last=False)
                tail_rows = [r for r in csv.reader(io.StringIO("\n".join(tail_lines))) if r]
                record["tail_rows_sampled"] = len(tail_rows)
                for column in date_cols:
                    span = scan_dates(tail_rows, column)
                    if span:
                        print(f"  column [{column}] {header[column]!r} dates in TAIL sample: {span[0]} .. {span[1]}")
                        record.setdefault("tail_date_spans", {})[header[column]] = list(span)
            else:
                print("  Tail range not honored; tail sample not interpreted.")

        report.append(record)

    out = PEEK / "rocr_peek_report.json"
    out.write_text(
        json.dumps(
            {"retrieved_utc": utcstamp(), "peek_bytes": args.peek_bytes, "files": report},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("=" * 78)
    print(f"written: {out}")
    print()
    print("--- how to read this for the two gates ---")
    print("C11-2 (cumulative or rolling): compare the earliest date in the head")
    print("  sample against the tail sample. A single snapshot whose dates reach")
    print("  back to 2012-06-15 is cumulative and the rolling snapshot window on")
    print("  the listing does not bind. If the earliest date is recent, it is")
    print("  rolling and the B11 window shrinks to whatever is actually there.")
    print("C11-1 (contract terms): find the coupon / par value / maturity columns")
    print("  in the header dump above and read their head_fill_rate. The prereg")
    print("  threshold is 0.90. The ROCR schema makes all three OPTIONAL, so a")
    print("  low rate here is the expected outcome, not a bug in this script.")
    return 0


# --------------------------------------------------------------------------
# the pull: resumable, verified, never destructive
# --------------------------------------------------------------------------


def count_lines(path: Path) -> int:
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            total += chunk.count(b"\n")
    return total


def pull_one(entry: dict, agent: str, force: bool) -> dict:
    ROCR.mkdir(parents=True, exist_ok=True)
    target = ROCR / entry["name"]
    part = target.with_suffix(target.suffix + ".part")
    record = {"name": entry["name"], "url": entry["url"], "listed_lines": entry["listed_lines"]}

    if target.exists() and not force:
        record["status"] = "cached"
        record["bytes"] = target.stat().st_size
        record["sha256"] = sha256_file(target)
        record["lines"] = count_lines(target)
        record["lines_match_listing"] = (
            None if entry["listed_lines"] is None else abs(record["lines"] - entry["listed_lines"]) <= 1
        )
        return record

    if target.exists() and force:
        retired = target.with_suffix(target.suffix + f".expired_{utcstamp()[:10].replace('-', '')}_pre_refetch")
        if not retired.exists():
            target.rename(retired)
        record["retired_to"] = retired.name

    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with request(entry["url"], agent, headers) as response:
        resumed = have > 0 and response.status == 206
        if have and not resumed:
            # The server ignored the resume. Starting over is the only honest
            # option: appending a full body onto a partial one produces a file
            # that is longer than the source and parses fine.
            have = 0
            part.write_bytes(b"")
            record["resume_refused"] = True
        declared = response.headers.get("Content-Length")
        expected = have + int(declared) if declared is not None else None
        mode = "ab" if have else "wb"
        with part.open(mode) as handle:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)

    got = part.stat().st_size
    record["bytes"] = got
    record["expected_bytes"] = expected
    if expected is not None and got != expected:
        record["status"] = "truncated"
        record["note"] = f"{got} bytes on disk, {expected} promised. Left as .part; rerun to resume."
        return record

    lines = count_lines(part)
    record["lines"] = lines
    if entry["listed_lines"] is not None and abs(lines - entry["listed_lines"]) > 1:
        record["status"] = "line_count_mismatch"
        record["note"] = (
            f"{lines} lines on disk, listing advertised {entry['listed_lines']}. "
            "Left as .part so nothing downstream reads it. The listing may have "
            "been refreshed mid-pull; rerun --index and compare."
        )
        return record

    part.replace(target)
    record["status"] = "fetched"
    record["sha256"] = sha256_file(target)
    record["lines_match_listing"] = True
    return record


def cmd_pull(args) -> int:
    if not INDEX.exists():
        print(f"No index at {INDEX}. Run --index first.")
        return 2
    if not args.yes:
        print("--pull needs --yes. Read the --peek report before spending the bytes:")
        print("if the archive is rolling, this is a different pull.")
        return 2
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    newest = newest_per_pair(payload["entries"])
    targets = [e for (a, c), e in sorted(newest.items()) if c == args.pull]
    if args.agency:
        needle = args.agency.lower()
        targets = [e for e in targets if needle in e["agency"].lower()]
    if not targets:
        print(f"Nothing in the index for asset class {args.pull!r}.")
        return 2

    records = []
    for entry in targets:
        print(f"-- {entry['name']}")
        record = pull_one(entry, args.user_agent, args.force)
        print(f"   {record['status']}  {record.get('bytes', 0):,} bytes")
        if record.get("note"):
            print(f"   {record['note']}")
        records.append(record)

    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    previous.setdefault("runs", []).append(
        {
            "retrieved_utc": utcstamp(),
            "asset_class": args.pull,
            "listing_sha256": payload["listing_sha256"],
            "files": records,
        }
    )
    MANIFEST.write_text(
        json.dumps(previous, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print()
    print(f"manifest: {MANIFEST}")
    bad = [r for r in records if r["status"] not in ("fetched", "cached")]
    if bad:
        print(f"{len(bad)} file(s) did not complete. They remain .part and are not readable downstream.")
        return 1
    return 0


def cmd_check(args) -> int:
    print(f"index    : {INDEX}  {'present' if INDEX.exists() else 'absent'}")
    print(f"manifest : {MANIFEST}  {'present' if MANIFEST.exists() else 'absent'}")
    if not ROCR.exists():
        print(f"cache    : {ROCR} does not exist yet")
        return 0
    complete = sorted(p for p in ROCR.glob("*.csv") if p.is_file())
    partial = sorted(ROCR.glob("*.part"))
    expired = sorted(ROCR.glob("*.expired_*"))
    print(f"cache    : {ROCR}")
    print(f"  complete .csv : {len(complete)}")
    for path in complete:
        print(f"    {path.name}  {path.stat().st_size:,} bytes")
    print(f"  unfinished .part : {len(partial)}")
    for path in partial:
        print(f"    {path.name}  {path.stat().st_size:,} bytes  (rerun --pull to resume)")
    print(f"  retired .expired_* : {len(expired)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discover", action="store_true", help="dump the listing's shape, decide nothing")
    mode.add_argument("--index", action="store_true", help="parse the listing, download no CSV")
    mode.add_argument("--peek", action="store_true", help="range-read head and tail of a few files")
    mode.add_argument("--check", action="store_true", help="classify what is on disk, fetch nothing")
    mode.add_argument("--pull", metavar="CLASS", help="download the newest file of this asset class")
    parser.add_argument("--agency", help="substring filter on the agency name")
    parser.add_argument("--peek-class", default="Corporate", help="asset class to peek at (default Corporate)")
    parser.add_argument("--peek-bytes", type=int, default=400_000, help="bytes per window (default 400000)")
    parser.add_argument("--limit", type=int, default=4, help="how many files to peek (default 4)")
    parser.add_argument("--force", action="store_true", help="refetch, retiring the current file by rename")
    parser.add_argument("--yes", action="store_true", help="required by --pull")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args(argv)

    try:
        if args.discover:
            return cmd_discover(args)
        if args.index:
            return cmd_index(args)
        if args.peek:
            return cmd_peek(args)
        if args.check:
            return cmd_check(args)
        return cmd_pull(args)
    except Forbidden as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except ServerUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
