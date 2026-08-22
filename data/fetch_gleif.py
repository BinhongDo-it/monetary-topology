"""Retrieve GLEIF's Level 2 relationship records, which say who owns whom.

B11's cross-agency join collapsed at the entity level: of 186 Fitch obligors
carrying an ``RD`` and an LEI, only 32 had that same LEI anywhere in Moody's
(``results/b11_coverage_fitch_moody.json``). The cause is not a bad key. Fitch
and Moody's often rate different legal entities of the same corporate family,
typically the parent on one side and the issuing subsidiary on the other, and
those are two LEIs by construction.

GLEIF publishes the parent-child map itself, free and without registration, as
the Level 2 relationship records of the Golden Copy. Rolling both sides up to a
common parent is therefore an **exact published mapping**, not a name match, and
it addresses the diagnosed cause rather than working around it.

Usage::

    python data/fetch_gleif.py --discover   # what the API offers, decide nothing
    python data/fetch_gleif.py --columns    # the CSV header inside the zip
    python data/fetch_gleif.py --pull       # the newest full relationship file
    python data/fetch_gleif.py --check      # what is on disk, fetch nothing

Why the URL is not written down here
------------------------------------
The Golden Copy path carries the publish timestamp
(``.../2026/08/17/1264925/20260817-0800-gleif-goldencopy-rr-golden-copy.csv.zip``),
so a hardcoded URL rots within a day. This asks the publishes API for the newest
one instead, and records in the manifest exactly which publish was taken, so a
result stays traceable to a file even after that file stops being the newest.

The known limit, recorded before any number is read
---------------------------------------------------
**Level 2 coverage is partial by design.** An entity may report a
"reporting exception" instead of a parent (its parent is not consolidated, or
there is no parent, or the parent's LEI is unknown), and those entities simply
have no edge here. So the rollup can only ever raise the match count, and the
share it fails to raise is not evidence that the two agencies rated unrelated
companies. That asymmetry has to be stated wherever the improved count is
quoted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
GLEIF = RAW / "gleif"
MANIFEST = RAW / "gleif_manifest.json"

PUBLISHES_API = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes?format=json"

TIMEOUT_SECONDS = 600
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

PATH_SAFE = "/:@&=+$,;~()'!*"


class ServerUnavailable(Exception):
    """A 5xx that survived every retry."""


class Ambiguous(Exception):
    """More than one candidate file, so this refuses to pick one."""


def encode_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe=PATH_SAFE)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def utcstamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def request(url: str, agent: str, headers: dict[str, str] | None = None):
    merged = {"User-Agent": agent, "Accept": "*/*"}
    merged.update(headers or {})
    last: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        req = urllib.request.Request(encode_path(url), headers=merged)
        try:
            return urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            if 500 <= exc.code < 600:
                last = exc
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as exc:
            last = exc
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise ServerUnavailable(f"{url} failed {RETRY_ATTEMPTS} times: {last}")


def walk_urls(node, trail=()) -> list[dict]:
    """Every ``url`` anywhere under ``node``, with the path that reached it.

    The API's nesting is not pinned here on purpose. A recursive collector keeps
    working when the publisher adds a level, and ``--discover`` prints what it
    found so a human confirms the pick before ``--pull`` acts on it.
    """
    found = []
    if isinstance(node, dict):
        if isinstance(node.get("url"), str):
            found.append(
                {
                    "path": "/".join(trail),
                    "url": node["url"],
                    "size": node.get("size"),
                    "format": node.get("format"),
                }
            )
        for key, value in node.items():
            found.extend(walk_urls(value, trail + (str(key),)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(walk_urls(value, trail + (str(index),)))
    return found


def newest_publish(agent: str) -> dict:
    with request(PUBLISHES_API, agent) as response:
        payload = json.loads(response.read().decode("utf-8"))
    entries = payload.get("data") or []
    if not entries:
        raise ServerUnavailable("The publishes API returned no entries.")
    return max(entries, key=lambda e: str(e.get("publish_date", "")))


def rr_candidates(publish: dict) -> list[dict]:
    rr = publish.get("rr")
    if rr is None:
        raise ServerUnavailable("No 'rr' object in the newest publish; the API moved.")
    return [c for c in walk_urls(rr) if c["url"].lower().endswith(".csv.zip")]


def pick_full(candidates: list[dict]) -> dict:
    full = [c for c in candidates if "full" in c["path"].lower() or "golden-copy.csv.zip" in c["url"].lower()]
    exact = [c for c in full if "delta" not in c["path"].lower() and "delta" not in c["url"].lower()]
    if len(exact) != 1:
        raise Ambiguous(
            "Expected exactly one full relationship file, found "
            f"{len(exact)}:\n" + "\n".join(f"  {c['path']}  {c['url']}" for c in exact or full)
        )
    return exact[0]


def cmd_discover(args) -> int:
    publish = newest_publish(args.user_agent)
    print(f"newest publish_date : {publish.get('publish_date')}")
    print(f"top-level keys      : {sorted(k for k in publish if not k.startswith('_'))}")
    print()
    candidates = rr_candidates(publish)
    print(f"relationship-record .csv.zip entries: {len(candidates)}")
    for candidate in candidates:
        size = candidate["size"]
        pretty = f"{size / 1e6:.1f} MB" if isinstance(size, int) else "size unstated"
        print(f"  path={candidate['path']}")
        print(f"    {pretty}   {candidate['url']}")
    print()
    try:
        chosen = pick_full(candidates)
    except Ambiguous as exc:
        print(str(exc))
        print("\n--pull would refuse. Nothing was written.")
        return 1
    print(f"--pull would take: {chosen['path']}")
    print(f"  {chosen['url']}")
    print("\nNothing was written.")
    return 0


def target_for(chosen: dict, publish: dict) -> Path:
    name = Path(urllib.parse.urlsplit(chosen["url"]).path).name
    return GLEIF / name


def cmd_pull(args) -> int:
    publish = newest_publish(args.user_agent)
    chosen = pick_full(rr_candidates(publish))
    GLEIF.mkdir(parents=True, exist_ok=True)
    target = target_for(chosen, publish)
    part = target.with_suffix(target.suffix + ".part")

    if target.exists() and not args.force:
        print(f"cached: {target.name}  {target.stat().st_size:,} bytes")
        print(f"sha256: {sha256_file(target)}")
        return 0

    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with request(chosen["url"], args.user_agent, headers) as response:
        resumed = have > 0 and response.status == 206
        if have and not resumed:
            have = 0
            part.write_bytes(b"")
            print("server refused the resume; starting over")
        declared = response.headers.get("Content-Length")
        expected = have + int(declared) if declared is not None else None
        with part.open("ab" if have else "wb") as handle:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)

    got = part.stat().st_size
    if expected is not None and got != expected:
        print(f"truncated: {got:,} bytes on disk, {expected:,} promised.")
        print(f"Left as {part.name}; rerun to resume. Nothing downstream can read it.")
        return 1
    if not zipfile.is_zipfile(part):
        print(f"{part.name} is not a readable zip. Left in place; rerun to resume.")
        return 1

    part.replace(target)
    record = {
        "retrieved_utc": utcstamp(),
        "publish_date": publish.get("publish_date"),
        "url": chosen["url"],
        "api": PUBLISHES_API,
        "bytes": got,
        "sha256": sha256_file(target),
        "file": target.name,
    }
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    previous.setdefault("runs", []).append(record)
    MANIFEST.write_text(
        json.dumps(previous, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"fetched: {target.name}  {got:,} bytes")
    print(f"publish: {publish.get('publish_date')}")
    print(f"sha256 : {record['sha256']}")
    print(f"manifest: {MANIFEST}")
    return 0


def newest_local() -> Path | None:
    if not GLEIF.exists():
        return None
    files = sorted(GLEIF.glob("*rr-golden-copy.csv.zip"))
    return files[-1] if files else None


def cmd_columns(args) -> int:
    archive = newest_local()
    if archive is None:
        print(f"No relationship file in {GLEIF}. Run --pull first.")
        return 2
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.namelist()
        print(f"{archive.name}")
        for member in members:
            info = bundle.getinfo(member)
            print(f"  member {member}  {info.file_size:,} bytes uncompressed")
        csvs = [m for m in members if m.lower().endswith(".csv")]
        if len(csvs) != 1:
            print(f"Expected one CSV inside, found {len(csvs)}. Refusing to guess.")
            return 1
        with bundle.open(csvs[0]) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8", errors="replace", newline="")
            reader = csv.reader(text)
            header = next(reader)
            print(f"\ncolumns ({len(header)}):")
            samples = [next(reader) for _ in range(3)]
            for index, name in enumerate(header):
                values = [row[index] for row in samples if index < len(row)]
                print(f"  [{index:>2d}] {name!r:<52s} e.g. {values}")
    print("\nNothing was written. The coverage step matches these names and refuses")
    print("to run if it cannot find the two node columns and the relationship type.")
    return 0


def cmd_check(args) -> int:
    print(f"manifest : {MANIFEST}  {'present' if MANIFEST.exists() else 'absent'}")
    if not GLEIF.exists():
        print(f"cache    : {GLEIF} does not exist yet")
        return 0
    for path in sorted(GLEIF.iterdir()):
        print(f"  {path.name}  {path.stat().st_size:,} bytes")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discover", action="store_true", help="what the API offers, decide nothing")
    mode.add_argument("--columns", action="store_true", help="the CSV header inside the local zip")
    mode.add_argument("--pull", action="store_true", help="download the newest full relationship file")
    mode.add_argument("--check", action="store_true", help="what is on disk, fetch nothing")
    parser.add_argument("--force", action="store_true", help="refetch even if cached")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args(argv)

    try:
        if args.discover:
            return cmd_discover(args)
        if args.columns:
            return cmd_columns(args)
        if args.pull:
            return cmd_pull(args)
        return cmd_check(args)
    except (ServerUnavailable, Ambiguous) as exc:
        print(str(exc), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
