"""Retrieve the Du-Keerati-Schreger CIP deviation dataset for stage B3.

Registered in ``docs/b3_cip_slice.md``; sourcing and the decision to use this
dataset at all are in ``docs/b3_slice_availability.md``.

Usage::

    python data/fetch_cip.py
    python data/fetch_cip.py --check          # classify what is cached, fetch nothing
    python data/fetch_cip.py --stamp-legacy   # append the marker to files that parse

**This is not our measurement of the world; it is somebody else's, downloaded.**
The publisher constructs the series from Bloomberg and Datastream and cannot
redistribute the raw inputs. Every headline built on it carries that
qualification, which `b3_slice_availability.md` §4 states and
`b3_cip_slice.md` §9 repeats.

Three things this script does that a plain download would not.

**It never deletes.** A file that fails classification is renamed with an
`.expired.<timestamp>` suffix and left in place. `CLAUDE.md` fixes this after a
recursive delete cost hours of retrieval.

**It writes the completion marker it checks for.** The HMDA script defined a
sentinel, checked for it, and never wrote it, so every finished file would have
been judged truncated and re-fetched. The classification here is three-state —
`complete`, `legacy`, `bad` — and a missing marker is treated as this script's
own omission rather than as evidence about the file.

**It records a content hash, which the other fetchers do not need.** HMDA and
NMDB come from government endpoints with stable, versioned releases. This file
is hosted by a researcher on S3 and **V4 replaced V3 at the same kind of URL**.
A silent republication under an unchanged name would otherwise be invisible: the
file would still parse, still carry the marker, and quietly be different data.
The manifest therefore records the SHA-256, and a re-run against a changed hash
reports it rather than overwriting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

#: Pinned in `b3_cip_slice.md` §7. The publisher archives prior versions, so a
#: re-check against V1-V3 is possible without asking anyone.
VERSION = "v4"
URL = "https://jschreger.s3.us-east-2.amazonaws.com/cip_dataset_v4.csv"
FILENAME = f"cip_dataset_{VERSION}.csv"
MANIFEST = RAW / "cip_manifest.json"

#: Companion documents. Retrieved alongside the data because the construction is
#: only auditable if the ticker list and the appendix are held with the file that
#: they describe, and a URL in a document is not a copy.
COMPANIONS = {
    "cip_tickers_v4.xlsx": (
        "https://jschreger.s3.us-east-2.amazonaws.com/CIP_Data_Tickers_v4.xlsx"
    ),
    "cip_data_appendix_v4.pdf": (
        "https://jschreger.s3.us-east-2.amazonaws.com/Data_Appendix_V4.pdf"
    ),
}

TIMEOUT_SECONDS = 300

#: Written as the final line of a completed CSV. Its absence in a file that
#: otherwise parses means the file predates the marker, not that it is truncated.
SENTINEL = "# complete"

#: Required by the publisher and recorded here so it cannot be forgotten between
#: retrieval and write-up.
CITATION = (
    "Du, Wenxin, Ritt Keerati, and Jesse Schreger (2025). "
    "'Decoupling Dollar and Treasury Privilege.' "
    "Du, Wenxin, Joanne Im, and Jesse Schreger (2018). "
    "'The U.S. Treasury Premium,' Journal of International Economics, 112, "
    "167-181. "
    "Du, Wenxin and Jesse Schreger (2016). 'Local Currency Sovereign Risk,' "
    "Journal of Finance, 71, 1027-1070."
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_status(path: Path) -> tuple[str, str]:
    """Classify a cached CSV as ``complete``, ``legacy`` or ``bad``.

    Deliberately does **not** check the column names. The schema is the
    publisher's and this script has never seen it; asserting an expected header
    here would make a correct file look broken the first time the publisher
    renames a column. The experiment asserts the columns it needs, loudly, at the
    point where it needs them.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except Exception as exc:  # noqa: BLE001
        return "bad", f"unreadable: {exc}"
    if not text.strip():
        return "bad", "empty"
    lines = text.splitlines()
    if len(lines) < 3:
        return "bad", f"only {len(lines)} lines"
    if "," not in lines[0]:
        return "bad", "first line is not a comma-separated header"
    if lines[-1].strip() == SENTINEL:
        return "complete", ""
    return "legacy", "no completion marker"


def download(url: str, timeout: int = TIMEOUT_SECONDS) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "monetary-topology"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def retire(path: Path, why: str) -> Path:
    """Rename, never remove. Returns the new path so it can be reported."""
    spoiled = path.with_suffix(f"{path.suffix}.expired.{int(time.time())}")
    path.rename(spoiled)
    print(f"  {path.name}: {why} -> kept as {spoiled.name}")
    return spoiled


def fetch_csv(force: bool = False) -> dict:
    out = RAW / FILENAME
    record: dict = {"name": FILENAME, "url": URL, "version": VERSION}

    if out.exists() and not force:
        status, why = file_status(out)
        if status == "complete":
            digest = sha256(out.read_bytes())
            print(f"  {FILENAME}: cached and complete, stored sha256 "
                  f"{digest[:12]}")
            return {**record, "status": "cached", "sha256_stored": digest}
        if status == "legacy":
            print(f"  {FILENAME}: cached, {why}; run --stamp-legacy to mark it")
            return {**record, "status": "legacy"}
        retire(out, why)

    started = time.time()
    try:
        raw = download(URL)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        print(f"  {FILENAME}: FAILED {exc}", file=sys.stderr)
        return {**record, "status": "error", "error": str(exc)}

    source_digest = sha256(raw)
    lines = raw.splitlines()
    header = lines[0].decode("utf-8", errors="replace") if lines else ""

    # **Written verbatim.** An earlier version decoded with ``errors="replace"``
    # and re-encoded, which silently rewrites any byte the decoder dislikes. An
    # archive that quietly differs from what arrived is not an archive.
    body = raw if raw.endswith(b"\n") else raw + b"\n"
    stored = body + f"{SENTINEL}\n".encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(stored)

    print(f"  {FILENAME}: {len(lines) - 1:,} data rows, "
          f"source sha256 {source_digest[:12]}")
    return {
        **record,
        "status": "downloaded",
        "seconds": round(time.time() - started, 1),
        "bytes": len(raw),
        "data_rows": len(lines) - 1,
        # Recorded verbatim rather than validated. The schema belongs to the
        # publisher; what this script owes the next reader is what it actually
        # received, not a judgement about it.
        "header": header,
        # **Two hashes, and they answer two different questions.** The first
        # version recorded only the source hash and then had ``--check`` compare
        # it against the file on disk, which by construction carries an extra
        # sentinel line. They never matched, so the guard cried wolf on every
        # run — and a guard that alarms when nothing is wrong is as useless as
        # one that reassures when something is: the next reader assumes it is
        # the sentinel again and misses a real republication.
        "sha256_source": source_digest,
        "sha256_stored": sha256(stored),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def fetch_companions(force: bool = False) -> list[dict]:
    out = []
    for name, url in COMPANIONS.items():
        path = RAW / name
        if path.exists() and not force:
            digest = sha256(path.read_bytes())
            print(f"  {name}: cached, sha256 {digest[:12]}")
            out.append({"name": name, "url": url, "status": "cached",
                        "sha256": digest})
            continue
        try:
            raw = download(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  {name}: FAILED {exc}", file=sys.stderr)
            out.append({"name": name, "url": url, "status": "error",
                        "error": str(exc)})
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        digest = sha256(raw)
        print(f"  {name}: {len(raw):,} bytes, sha256 {digest[:12]}")
        out.append({
            "name": name, "url": url, "status": "downloaded",
            "bytes": len(raw), "sha256": digest,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
        })
    return out


def check() -> int:
    """Classify what is cached and say so. Fetches nothing."""
    if not RAW.exists():
        print(f"  no directory at {RAW.relative_to(ROOT)}")
        return 1
    recorded = None
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        recorded = m.get("dataset", {}).get("sha256_stored")

    seen = bad = 0
    for path in sorted(RAW.glob("cip_dataset_*.csv")):
        status, why = file_status(path)
        digest = sha256(path.read_bytes())
        # Compared against the **stored** hash, which is what was written here,
        # not against the source hash, which cannot match a file carrying a
        # sentinel line that the source did not.
        if recorded is None:
            verdict = "no stored hash in the manifest; refetch with --force"
        elif digest == recorded:
            verdict = "matches the manifest"
        else:
            verdict = "DOES NOT MATCH THE MANIFEST"
            bad += 1
        print(f"  {path.name}: {status}{' -- ' + why if why else ''}, "
              f"sha256 {digest[:12]}, {verdict}")
        seen += 1
    if not seen:
        print("  nothing cached")
    if recorded:
        print(f"  manifest records stored sha256 {recorded[:12]}")
    return 1 if bad else 0


def stamp_legacy() -> int:
    """Append the completion marker to files that parse. Appends only."""
    if not RAW.exists():
        print(f"  no directory at {RAW.relative_to(ROOT)}")
        return 1
    stamped = already = left = 0
    for path in sorted(RAW.glob("cip_dataset_*.csv")):
        status, why = file_status(path)
        if status == "complete":
            already += 1
        elif status == "legacy":
            with path.open("a", encoding="utf-8") as fh:
                fh.write(f"{SENTINEL}\n")
            stamped += 1
        else:
            print(f"  {path.name}: not stamped, {why}")
            left += 1
    print(f"  stamped {stamped}, already complete {already}, left alone {left}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="classify what is cached and exit")
    ap.add_argument("--stamp-legacy", action="store_true",
                    help="append the completion marker to files that parse")
    ap.add_argument("--force", action="store_true",
                    help="refetch even if a complete file is cached")
    args = ap.parse_args()

    if args.check:
        return check()
    if args.stamp_legacy:
        return stamp_legacy()

    print(f"CIP dataset {VERSION}, for stage B3\n")
    dataset = fetch_csv(force=args.force)
    companions = fetch_companions(force=args.force)

    RAW.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "stage": "B3",
                "version": VERSION,
                "source_page": "https://sites.google.com/view/jschreger/CIP",
                "citation": CITATION,
                "note": (
                    "Derived series. The publisher constructs it from Bloomberg "
                    "and Datastream and states that licensing forbids "
                    "republishing the raw inputs. The ticker spreadsheet "
                    "retrieved alongside makes the construction auditable but "
                    "not re-runnable without a terminal."
                ),
                "dataset": dataset,
                "companions": companions,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n  wrote {MANIFEST.relative_to(ROOT)}")

    failed = [
        r for r in [dataset, *companions] if r.get("status") == "error"
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
