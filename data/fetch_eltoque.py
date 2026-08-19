"""elTOQUE's informal exchange rate, one day per request, for stage B6-B.

`b6b_eltoque_prereg.md` §10 is the authority. Written after
``data/fetch_bcc.py`` and deliberately close to it, so that the four places it
has to differ stand out instead of hiding in a rewrite.

The four differences, and why each is forced
---------------------------------------------

**One request buys one day.** A window longer than twenty-four hours is refused
outright with HTTP 400 and the body ``El intervalo de tiempo debe ser menor a 24
horas``. ``fetch_bcc`` asks once per currency and gets a window back; this asks
once per day, 2055 times, and there is no bulk form to ask for instead.

**The same day refetched produces different bytes.** The response carries the
server clock and no echo of the day it describes, so ``sha256`` of the body is
not an equality test. Every comparison that means anything in this file runs
through ``digest_tasas``, which hashes the measurement and not the envelope.
``sha256_body`` is still recorded, for the narrower claim that the file on disk
is the file that arrived.

**Absence is a value and is stored.** A day the instrument cannot serve comes
back with an empty ``tasas`` object. That is the source's own statement, it is
what makes a silent fallback detectable, and it is written to disk like any other
day. ``b6_cuba_prereg.md`` §10 rule 1 asked the fetcher to compare the returned
span against the requested one; there is no span in the response, and this is
what replaced it.

**Pacing is read, not assumed.** Every response carries ``X-RateLimit-Limit``,
``X-RateLimit-Remaining`` and ``X-RateLimit-Reset``, and the documented ceiling
is 60 per minute with a 10 per second burst cap, per key. Sixty per minute is one
per second, which is the sustained rate here, but the headers decide when to wait
longer and a ``429`` is handled through ``Retry-After`` rather than by guessing.

What this file will not do
---------------------------

**It does not delete.** A response that fails to parse is renamed with an
``.expired`` suffix and left in place, ``retire`` below.

**It does not fill.** An empty day stays empty in both directions. B6-A's guard 2
admitted a back-fill as a forward-fill once and the retraction is in
``b6_cuba_prereg.md`` §11; the lesson cost several hours and costs four lines
here.

**It does not print the key.** The token is read from ``.env``, which
``.gitignore`` line 10 excludes, and elTOQUE's terms forbid passing it to a third
party. Only its length and last six characters are ever shown, which is enough to
tell "loaded the wrong file" from "loaded nothing".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from monetary_topology.cuba_informal import (
    ENDPOINT,
    POLITE_DELAY_SECONDS,
    PROBE_RECORD,
    PROBE_TAKEN_LIVE,
    TRMI_START,
    day_window,
    digest_tasas,
    guard_membership,
    guard_no_fill,
    guard_row_key,
    guard_verbatim,
    is_absent,
    local_span_seconds,
    probe_is_comparable,
    request_count,
    sensitivity_days,
    served,
    tasas_of,
    trmi_url,
    window_days,
    window_is_shortened,
)
from monetary_topology.cuba_segments import GuardFailed

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TRMI_DIR = RAW / "eltoque"
MANIFEST = RAW / "eltoque_manifest.json"
TOKEN_FILE = ROOT / ".env"
TOKEN_KEY = "ELTOQUE_TOKEN"

TIMEOUT_SECONDS = 60
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0


#: How a 429 is answered when the source's own advice is unusable.
#:
#: Observed 2026-08-19: a request came back 429 with ``Retry-After: -11``. **A
#: negative wait is not a wait**, and clamping it to a second is an immediate
#: retry wearing a delay's clothes. The floor below is used when both
#: ``Retry-After`` and ``X-RateLimit-Reset`` point into the past, and it doubles
#: per attempt.
THROTTLE_FLOOR_SECONDS = 30.0
THROTTLE_ATTEMPTS = 4

#: A wait longer than this is reported rather than slept through. The run
#: resumes from disk, so coming back later costs nothing, and an unannounced
#: hour-long sleep is indistinguishable from a hang.
MAX_THROTTLE_WAIT_SECONDS = 300.0

#: Progress every this many requests, on a long pass. At the measured pacing
#: that is roughly every seven minutes, which is what makes a ten-hour run
#: distinguishable from a stuck one without reading this file.
#:
#: **A pass shorter than this prints nothing until it ends**, which is how the
#: twelve-window sensitivity pass spent three and a half minutes looking stuck.
#: ``progress_step`` gives a short pass a step of its own.
PROGRESS_EVERY = 25


def progress_step(total: int) -> int:
    """How often to print, for a pass of this length. At least four lines."""
    return max(1, min(PROGRESS_EVERY, total // 4))


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


class RateLimited(Exception):
    """A 429 that came back after waiting out its own ``Retry-After``."""


class Unparseable(Exception):
    """A response that is not the shape this stage understands."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_token() -> str:
    """Read the key from ``.env`` and say nothing about its value.

    An absent file and an absent line are different mistakes and get different
    messages, because "you have no .env" and "your .env has the wrong key name"
    lead to different next actions.
    """
    if not TOKEN_FILE.exists():
        raise SystemExit(
            f"no {TOKEN_FILE.name} at {TOKEN_FILE.parent}. It holds one line, "
            f"{TOKEN_KEY}=<key>, and .gitignore excludes it. Request a key at "
            f"https://tasas-token.eltoque.com/"
        )
    for line in TOKEN_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{TOKEN_KEY}="):
            token = line.split("=", 1)[1].strip()
            if not token:
                raise SystemExit(f"{TOKEN_KEY} in {TOKEN_FILE.name} is empty")
            return token
    raise SystemExit(f"no {TOKEN_KEY}= line in {TOKEN_FILE.name}")


def describe_token(token: str) -> str:
    """Enough to diagnose, not enough to use."""
    return f"{len(token)} chars, ends {token[-6:]}"


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
            f"reset={reset} ({gap}) "
            f"retry-after={get('Retry-After')}")


def throttle_wait(headers, attempt: int) -> float:
    """How long to wait after a 429: the source, then the clock, then a floor.

    **Both headers have been seen pointing into the past**, so neither is trusted
    without a sign check. When they do, the wait comes from a schedule of this
    file's own rather than from a clamp, because a clamp on a negative number is
    an immediate retry wearing a delay's clothes.
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


def wait_for(headers: dict[str, str]) -> float:
    """How long to sleep after one response. **Not from the remaining count.**

    ``X-RateLimit-Remaining`` reported ``10`` on all fifteen requests of the rate
    probe on 2026-08-19, including on the three that came back 429. **The header
    does not decrement**, so a pacer that slowed down when it approached zero
    would never slow down at all. The first version of this function did exactly
    that, which is why the first real run walked into the limit at full speed.

    What is left is the sustained delay, which is a measured constant rather than
    a header, and ``X-RateLimit-Reset``, which does move and is used by
    ``throttle_wait`` after a refusal. Passing the headers in is kept so that the
    manifest records what the limiter claimed at the time even though nothing
    here believes the count.
    """
    del headers
    return POLITE_DELAY_SECONDS


def download(url: str, token: str) -> tuple[bytes, dict[str, str]]:
    """Fetch one window. Retry server errors, never retry client errors.

    The one exception is 429, which is a client error the server asked us to
    retry and which carries the wait in ``Retry-After``. It is waited out once.
    A second 429 stops the run, because pressing against a published limit after
    being told twice is how a key gets withdrawn, and this project has one key.
    """
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "monetary-topology",
        },
    )
    throttled = 0
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310, E501
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.read(), headers
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                throttled += 1
                delay = throttle_wait(exc.headers, throttled)
                print(f"      429 #{throttled}: {limits(exc.headers)}")
                if delay > MAX_THROTTLE_WAIT_SECONDS:
                    raise RateLimited(
                        f"the limiter asks for {delay:.0f}s, which is longer "
                        f"than this file will sleep without saying so. The run "
                        f"resumes from disk, so stopping now costs one command "
                        f"later. Headers: {limits(exc.headers)}"
                    ) from exc
                if throttled > THROTTLE_ATTEMPTS:
                    raise RateLimited(
                        f"{throttled} consecutive 429s with backoff. This is "
                        f"the limiter saying no, not a burst. Headers: "
                        f"{limits(exc.headers)}"
                    ) from exc
                print(f"      waiting {delay:.0f}s")
                time.sleep(delay)
                continue
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


def write_atomic(path: Path, data: bytes) -> None:
    """Temporary file, then rename, so a response is whole or absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def slug(date_from: str) -> str:
    """A filename from a window's opening timestamp.

    The sub-day windows need the hour in the name or the sensitivity pass would
    overwrite the main pass on the twelve dates they share.
    """
    day, clock = date_from.split(" ")
    if clock == "00:00:00":
        return day
    return f"{day}_{clock.replace(':', '-')}"


def trmi_path(date_from: str) -> Path:
    return TRMI_DIR / f"trmi_{slug(date_from)}.json"


def parse(raw: bytes, path: Path) -> dict[str, float]:
    """The stored bytes, read back as a measurement, or retired.

    A file that does not parse is renamed rather than skipped, so a rerun fetches
    it again and the broken one stays on disk to be looked at.
    """
    try:
        payload = json.loads(raw.decode("utf-8"))
        return tasas_of(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        if path.exists():
            retire(path, f"unparseable: {exc}")
        raise Unparseable(f"{path.name}: {exc}") from exc


def span_note(date_from: str, date_to: str) -> dict:
    """What the window covers in elapsed time, for the manifest.

    Only meaningful on a whole-day window; the sensitivity hour and the recorded
    sub-day probe are not days and are marked as such rather than given a
    number that would read like one.
    """
    day = date.fromisoformat(date_from.split(" ")[0])
    whole = date_to.endswith(("23:59:59", "22:59:59"))
    if not whole:
        return {"day_span_seconds": None, "window_shortened": False}
    return {
        "day_span_seconds": local_span_seconds(day),
        "window_shortened": window_is_shortened(day),
    }


def fetch_window(date_from: str, date_to: str, token: str, *,
                 force: bool) -> dict:
    """One window, cached or fetched. **This is the whole of the resume logic.**

    A day already on disk is a day already paid for, and the file's existence is
    the resume point. There is no separate state to keep in step with the
    directory, which is the failure this shape avoids rather than the
    convenience it offers.
    """
    path = trmi_path(date_from)
    if path.exists() and not force:
        raw = path.read_bytes()
        tasas = parse(raw, path)
        return {
            **span_note(date_from, date_to),
            "date_from": date_from,
            "date_to": date_to,
            "status": "cached",
            "file": path.name,
            "sha256_body": sha256(raw),
            "sha256_tasas": digest_tasas(tasas),
            "served": list(served(tasas)),
            "absent": is_absent(tasas),
            "wait": 0.0,
        }
    body, headers = download(trmi_url(date_from, date_to), token)
    write_atomic(path, body)
    guard_verbatim(body, path.read_bytes())
    tasas = parse(body, path)
    return {
        **span_note(date_from, date_to),
        "date_from": date_from,
        "date_to": date_to,
        "status": "downloaded",
        "file": path.name,
        "sha256_body": sha256(body),
        "sha256_tasas": digest_tasas(tasas),
        "served": list(served(tasas)),
        "absent": is_absent(tasas),
        "wait": wait_for(headers),
        "rate_limit": {
            k: headers.get(k)
            for k in ("x-ratelimit-limit", "x-ratelimit-remaining",
                      "x-ratelimit-reset")
        },
    }


def run_pass(windows: list[tuple[str, str]], token: str, label: str, *,
             force: bool) -> list[dict]:
    """One pass over a list of windows, with progress and header-driven pacing."""
    out: list[dict] = []
    fetched = 0
    step = progress_step(len(windows))
    started = time.time()
    for index, (date_from, date_to) in enumerate(windows, start=1):
        record = fetch_window(date_from, date_to, token, force=force)
        out.append(record)
        if record["status"] == "downloaded":
            fetched += 1
            time.sleep(record["wait"])
        if index % step == 0 or index == len(windows):
            elapsed = time.time() - started
            left = len(windows) - index
            eta = left * (elapsed / index) / 60.0
            print(f"    {label}: {index}/{len(windows)}, {fetched} fetched, "
                  f"{elapsed / 60:.0f} min in, about {eta:.0f} min left")
    return out


def replay(token: str, *, force: bool) -> tuple[list[dict], list[str]]:
    """B6-9's known-answer arm: the twelve recorded probe windows.

    Eight of the twelve fall inside the main pass's span, so this reads the file
    the main pass wrote rather than making a fresh request, **and that is the
    stronger check of the two**. The question is not whether the endpoint still
    answers the same way; it is whether the day the main pass filed under
    2026-08-11 is the day the probe recorded for 2026-08-11. An off-by-one
    anywhere in the date handling puts some other day's numbers in that file, and
    the response body cannot report the error because it carries no date of its
    own. The four windows outside the span are fetched.

    A disagreement is a failure of the instrument or of this file, and it is
    reported rather than repaired.
    """
    records: list[dict] = []
    disagreements: list[str] = []
    for window, expected in sorted(PROBE_RECORD.items()):
        date_from, date_to = window
        record = fetch_window(date_from, date_to, token, force=force)
        agrees = record["sha256_tasas"] == digest_tasas(expected)
        record["replay_expected"] = digest_tasas(expected)
        record["replay_agrees"] = agrees
        record["replay_comparable"] = probe_is_comparable(window)
        records.append(record)
        if not agrees:
            if probe_is_comparable(window):
                disagreements.append(date_from)
                print(f"    REPLAY DISAGREES: {date_from}")
            else:
                stored = parse(trmi_path(date_from).read_bytes(),
                               trmi_path(date_from))
                deltas = {
                    code: round(math.log(stored[code] / expected[code]), 4)
                    for code in sorted(set(stored) & set(expected))
                    if stored[code] > 0 and expected[code] > 0
                }
                record["live_probe_deltas"] = deltas
                print(f"    {date_from}: differs as registered, probe taken "
                      f"while the day was live. deltas {deltas}")
        if record["status"] == "downloaded":
            time.sleep(record["wait"])
    return records, disagreements


def collect(records: list[dict]) -> tuple[dict, dict, set[str]]:
    """Split a pass's records into what the guards need."""
    values: dict[str, dict[str, float]] = {}
    membership: dict[str, tuple[str, ...]] = {}
    absent: set[str] = set()
    for record in records:
        when = record["date_from"].split(" ")[0]
        tasas = parse(trmi_path(record["date_from"]).read_bytes(),
                      trmi_path(record["date_from"]))
        values[when] = tasas
        membership[when] = tuple(record["served"])
        if record["absent"]:
            absent.add(when)
    return values, membership, absent


def probe_limits(token: str) -> int:
    """One request, every header printed, nothing written.

    Exists because ``X-RateLimit-Limit: 10`` does not say ten of what. Ten per
    second and ten per minute differ by a factor of six in the run's length and
    by everything in whether the run is possible at all, and the only way to
    tell them apart is to ask and read what comes back.
    """
    date_from, date_to = day_window(date(2026, 8, 11))
    url = trmi_url(date_from, date_to)
    print(f"  one request: {date_from} .. {date_to}")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "monetary-topology",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310, E501
            body = resp.read()
            print(f"  HTTP {resp.status}")
            for key, value in sorted(resp.headers.items()):
                print(f"    {key}: {value}")
            print(f"  body: {body.decode('utf-8', 'replace')[:200]}")
            print(f"  clock now: {time.time():.0f}")
            return 0
    except urllib.error.HTTPError as exc:
        print(f"  HTTP {exc.code}")
        for key, value in sorted(exc.headers.items()):
            print(f"    {key}: {value}")
        print(f"  body: {exc.read().decode('utf-8', 'replace')[:200]}")
        print(f"  clock now: {time.time():.0f}")
        return 1


def probe_rate(token: str) -> int:
    """Fifteen requests at the rate this file intends to run at, and a table.

    ``X-RateLimit-Limit: 10`` does not say ten of what, and the three readings
    that fit the specification differ by a factor of thirty in how long the main
    pass takes. Yesterday's four probes reported ``remaining`` going 9, 10, 10,
    10 with ``reset`` unchanged across eight seconds, which fits none of them, so
    this measures instead of inferring.

    **The window is one already recorded in ``PROBE_RECORD``**, so nothing new is
    seen and nothing is written. Fifteen requests at one second is exactly the
    cadence the main pass would use, which makes this the smallest honest test of
    the plan rather than a burst aimed at the limiter.
    """
    date_from, date_to = day_window(date(2026, 8, 11))
    url = trmi_url(date_from, date_to)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "monetary-topology",
        },
    )
    print(f"  fifteen requests at {POLITE_DELAY_SECONDS:.1f}s on a window "
          f"already recorded: {date_from}")
    print(f"  {'#':>3} {'t':>6} {'code':>5} {'limit':>6} {'left':>5} "
          f"{'reset':>12} {'reset-now':>10}")
    started = time.time()
    refused = 0
    for seq in range(1, 16):
        now = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310, E501
                resp.read()
                code, headers = resp.status, resp.headers
        except urllib.error.HTTPError as exc:
            exc.read()
            code, headers = exc.code, exc.headers
            refused += 1
        reset = headers.get("X-RateLimit-Reset", "-")
        try:
            gap = f"{float(reset) - now:+.0f}s"
        except ValueError:
            gap = "-"
        print(f"  {seq:>3} {now - started:>5.1f}s {code:>5} "
              f"{headers.get('X-RateLimit-Limit', '-'):>6} "
              f"{headers.get('X-RateLimit-Remaining', '-'):>5} "
              f"{reset:>12} {gap:>10}")
        if refused >= 3:
            print("  three refusals, stopping. That is the answer.")
            break
        time.sleep(POLITE_DELAY_SECONDS)
    print(f"  {refused} of {seq} refused")
    return 0


def probe_window(token: str) -> int:
    """Wait out any live window, then one request, and read the window's length.

    The rate probe established that the limit is ten per window and that the
    window is at least 155 seconds. What it could not separate is whether that
    155 was the whole window or the tail of one started by earlier refusals,
    since a refused request still counts against most limiters.

    **A request made after a quiet period longer than any candidate window is
    necessarily the first of its own window**, so ``X-RateLimit-Reset`` minus the
    moment it was sent is the window length and nothing else. One request, a
    seven minute wait, and the number that decides whether the main pass is nine
    hours or seventeen.
    """
    quiet = 420
    print(f"  waiting {quiet}s so the next request is certainly the first of a "
          f"new window")
    for left in range(quiet, 0, -30):
        print(f"    {left}s", end="\r", flush=True)
        time.sleep(min(30, left))
    print("    0s      ")
    date_from, date_to = day_window(date(2026, 8, 11))
    req = urllib.request.Request(
        trmi_url(date_from, date_to),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "monetary-topology",
        },
    )
    sent = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310, E501
            resp.read()
            headers, code = resp.headers, resp.status
    except urllib.error.HTTPError as exc:
        exc.read()
        headers, code = exc.headers, exc.code
    reset = headers.get("X-RateLimit-Reset", "-")
    print(f"  HTTP {code}   limit={headers.get('X-RateLimit-Limit', '-')}   "
          f"reset={reset}")
    try:
        window = float(reset) - sent
    except ValueError:
        print("  reset is unreadable; nothing measured")
        return 1
    if code != 200:
        print("  refused after seven quiet seconds' worth of waiting, so the "
              "window is longer than the wait or the quota is not per-window")
        return 1
    print(f"\n  WINDOW = {window:.0f}s, LIMIT = 10")
    per_request = window / 10.0
    print(f"  sustained rate: one request every {per_request:.1f}s")
    total = request_count(TRMI_START, date.today())
    print(f"  {total:,} requests would take {total * per_request / 3600:.1f} h")
    print(f"  the B6-A window alone, about 245 days, would take "
          f"{245 * per_request / 3600:.1f} h")
    return 0


def check() -> int:
    """Classify what is cached against the manifest, and fetch nothing."""
    if not MANIFEST.exists():
        print(f"no manifest at {MANIFEST.relative_to(ROOT)}; nothing to check")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded = {
        row["file"]: row["sha256_tasas"]
        for row in manifest.get("responses", [])
        if "file" in row and "sha256_tasas" in row
    }
    files = sorted(TRMI_DIR.glob("trmi_*.json")) if TRMI_DIR.exists() else []
    print(f"  {len(files)} files on disk, {len(recorded)} in the manifest")
    bad = 0
    for path in files:
        try:
            digest = digest_tasas(parse(path.read_bytes(), path))
        except Unparseable:
            bad += 1
            continue
        if path.name not in recorded:
            print(f"  {path.name}: not in the manifest")
            bad += 1
        elif recorded[path.name] != digest:
            print(f"  {path.name}: tasas digest differs from the manifest")
            bad += 1
    missing = sorted(set(recorded) - {p.name for p in files})
    for name in missing:
        print(f"  {name}: in the manifest and not on disk")
    print(f"  {bad} mismatched, {len(missing)} missing")
    return 0 if bad == 0 and not missing else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached against the manifest and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and its cost, fetch nothing")
    ap.add_argument("--probe-limits", action="store_true",
                    help="one request, print every header, write nothing")
    ap.add_argument("--probe-rate", action="store_true",
                    help="fifteen requests at the run's cadence, write nothing")
    ap.add_argument("--probe-window", action="store_true",
                    help="wait out the limiter, then one request, to measure "
                         "the window length")
    ap.add_argument("--force", action="store_true",
                    help="refetch even if cached")
    ap.add_argument("--pass", dest="which", default="all",
                    choices=("main", "sensitivity", "replay", "all"),
                    help="which pass to run")
    args = ap.parse_args()

    if args.check:
        return check()

    if args.probe_limits:
        return probe_limits(load_token())

    if args.probe_rate:
        return probe_rate(load_token())

    if args.probe_window:
        return probe_window(load_token())

    # The last complete day, not today. A window that ends at 23:59:59 of the
    # current day is a partial day's offers, and the estimator is a median over
    # whatever is inside the window, so today's answer is a different statistic
    # from every other row. It is fetched on the next run, when it is whole.
    last_complete = datetime.now(timezone.utc).date() - timedelta(days=1)
    days = window_days(TRMI_START, last_complete)
    sens = sensitivity_days(last_complete)
    cached = sum(1 for d in days
                 if trmi_path(day_window(d)[0]).exists())

    print("elTOQUE, informal representative rate, for stage B6-B")
    print(f"  endpoint {ENDPOINT}")
    print(f"  main pass {TRMI_START} to {last_complete}, {len(days):,} days")
    print(f"  sensitivity pass {len(sens)} dates, one hour each")
    print(f"  replay pass {len(PROBE_RECORD)} recorded probe windows")
    print(f"  {cached:,} of the main pass already on disk")
    outstanding = request_count(TRMI_START, last_complete) - cached
    print(f"  {outstanding:,} requests outstanding, about "
          f"{outstanding * POLITE_DELAY_SECONDS / 60:.0f} min at "
          f"{POLITE_DELAY_SECONDS:.0f}s each\n")

    if args.dry_run:
        print("  dry run, nothing fetched")
        return 0

    token = load_token()
    print(f"  key loaded from {TOKEN_FILE.name}, {describe_token(token)}\n")

    responses: list[dict] = []
    disagreements: list[str] = []
    if args.which in ("main", "all"):
        responses += run_pass([day_window(d) for d in days], token, "main",
                              force=args.force)
    if args.which in ("sensitivity", "all"):
        responses += run_pass(
            [day_window(d, sensitivity=True) for d in sens], token,
            "sensitivity", force=args.force,
        )
    if args.which in ("replay", "all"):
        replayed, disagreements = replay(token, force=args.force)
        responses += replayed

    main_records = [r for r in responses
                    if r["date_from"].endswith("00:00:00")
                    and r["date_from"].split(" ")[0]
                    in {d.isoformat() for d in days}]
    values, membership, absent = collect(main_records)
    try:
        for record in main_records:
            when = record["date_from"].split(" ")[0]
            payload = json.loads(
                trmi_path(record["date_from"]).read_text(encoding="utf-8")
            )
            guard_row_key(date.fromisoformat(when), payload, when)
        guard_no_fill(values, absent)
        guard_membership(values, membership)
    except GuardFailed as exc:
        print(f"\n  GUARD FAILED: {exc}", file=sys.stderr)
        print("  Nothing downstream may run. prereg §6.2.", file=sys.stderr)
        return 1

    RAW.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "B6-B",
                "endpoint": ENDPOINT,
                "endpoint_verified": "2026-08-18",
                "window": [TRMI_START.isoformat(), last_complete.isoformat()],
                "provenance": (
                    "elTOQUE, Tasa Representativa del Mercado Informal. One "
                    "median per instrument per requested window, formed from "
                    "buy and sell offers scraped from Telegram, WhatsApp and "
                    "classified sites and pooled by the publisher, so there is "
                    "no bid and no ask on this leg. The construction is "
                    "peer-reviewed: Vidal, Muniz Cuza and Calas Torres, Using "
                    "AI in the Informal Currency Market: Evidence from Cuba, "
                    "Applied Economics, October 2024, "
                    "doi:10.1080/00036846.2024.2416091. elTOQUE's terms "
                    "require attribution and forbid resale, redistribution and "
                    "sharing the key, so the series itself is not committed: "
                    "data/raw/ is excluded and only this manifest is tracked."
                ),
                "absent_days": sorted(absent),
                "shortened_windows": sorted(
                    r["date_from"].split(" ")[0] for r in responses
                    if r.get("window_shortened")
                ),
                "short_span_days": sorted(
                    r["date_from"].split(" ")[0] for r in responses
                    if r.get("day_span_seconds") not in (None, 86_399)
                ),
                "replay_disagreements": disagreements,
                "replay_not_compared": sorted(
                    f"{a} .. {b}" for a, b in PROBE_TAKEN_LIVE
                ),
                "responses": responses,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")
    print(f"  {len(values):,} days, {len(absent):,} of them empty")
    if disagreements:
        print(f"  REPLAY DISAGREEMENTS: {len(disagreements)}, B6-9 fails")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
