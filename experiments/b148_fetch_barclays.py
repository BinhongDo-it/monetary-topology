"""Fetch the Barclays core-range customer rate sheet (PDF) that B148 reads as its second designer.

B148 reads one bank's posted mortgage rates by customer class. The HSBC pages are text; Barclays
prints its customer-class rates only in a PDF rate sheet linked from its first-time-buyer and
remortgage pages (B148 result doc, R10). This script fetches that one file. It does not parse.

Rules this obeys:
  - resumable: a file on disk that passes the checks and matches its manifest hash is skipped;
    an interrupted download is kept as <name>.part and continued with an HTTP Range request
    when the server honours it
  - never deletes: a file that fails the checks is renamed with a .bad_<n> suffix
  - detects truncation: HTTP 200/206, body starts with %PDF-, a %%EOF marker in the last 2 KB,
    and the byte count equals Content-Length when the server sends one
  - one file per server version: the name carries the Last-Modified date, so a later sheet
    never overwrites an earlier one
  - the manifest records URL, file, length, SHA-256, Last-Modified, ETag and the fetch time

The PDF is untrusted data. Read it only with pymupdf under ``python -I``; nothing in it is run.

    python -B experiments/b148_fetch_barclays.py --fetch
    python -B experiments/b148_fetch_barclays.py --check      # re-verify what is on disk, no network
    python -B experiments/b148_fetch_barclays.py --selftest   # seeded faults, no network
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "raw" / "b148" / "barclays"
MANIFEST = DEST / "barclays_manifest.json"
URL = "https://www.barclays.co.uk/content/dam/documents/personal/mortgages/CoreRangeCustomerRateSheet.pdf"
STEM = "CoreRangeCustomerRateSheet"
TIMEOUT = 60
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def pdf_ok(body: bytes, content_length: int | None) -> tuple[bool, str]:
    if not body.startswith(b"%PDF-"):
        return False, "does not start with %PDF-"
    if b"%%EOF" not in body[-2048:]:
        return False, "no %%EOF in the last 2 KB (truncated)"
    if content_length is not None and len(body) != content_length:
        return False, f"{len(body)} bytes, Content-Length {content_length}"
    return True, "ok"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"url": URL, "versions": []}


def save_manifest(m: dict) -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DEST, prefix="manifest.", suffix=".tmp.expired")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, sort_keys=True, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, MANIFEST)


def set_aside(path: Path) -> Path:
    n = 1
    while path.with_name(path.name + f".bad_{n}").exists():
        n += 1
    new = path.with_name(path.name + f".bad_{n}")
    path.rename(new)
    return new


def head() -> dict:
    req = urllib.request.Request(URL, method="HEAD", headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return {k.lower(): v for k, v in r.headers.items()}


def version_name(last_modified: str | None) -> str:
    if not last_modified:
        return f"{STEM}_undated.pdf"
    d = parsedate_to_datetime(last_modified).astimezone(timezone.utc)
    return f"{STEM}_{d:%Y%m%dT%H%M%SZ}.pdf"


def fetch() -> int:
    m = load_manifest()
    h = head()
    lm, etag = h.get("last-modified"), h.get("etag")
    name = version_name(lm)
    final, part = DEST / name, DEST / (name + ".part")
    known = {v["file"]: v for v in m["versions"]}
    if final.exists():
        body = final.read_bytes()
        ok, why = pdf_ok(body, None)
        if ok and name in known and known[name]["sha256"] == hashlib.sha256(body).hexdigest():
            print(f"on disk and verified: {name}  {len(body)} B  sha256 {known[name]['sha256']}")
            return 0
        print(f"on disk but fails ({why if not ok else 'hash not in manifest'}), set aside -> {set_aside(final).name}")
    DEST.mkdir(parents=True, exist_ok=True)
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": UA, "Accept-Encoding": "identity"}
    if have:
        headers["Range"] = f"bytes={have}-"
        if etag:
            headers["If-Range"] = etag
    req = urllib.request.Request(URL, headers=headers)
    t0 = time.perf_counter()
    fetched_after = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    try:
        r = urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}; nothing written")
        return 1
    with r:
        status = r.status
        clen = r.headers.get("Content-Length")
        mode = "ab" if status == 206 else "wb"
        if have and status != 206:
            print(f"server ignored Range (status {status}); restarting the part file")
        with open(part, mode) as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
    secs = time.perf_counter() - t0
    fetched_before = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    body = part.read_bytes()
    total = None
    if clen is not None:
        total = int(clen) + (have if status == 206 else 0)
    ok, why = pdf_ok(body, total)
    print(f"{secs:6.2f} s  status {status}  {len(body)} B  {'ok' if ok else 'BAD: ' + why}")
    if not ok:
        print(f"kept as {part.name} for a resumed run")
        return 1
    sha = hashlib.sha256(body).hexdigest()
    same = [v for v in m["versions"] if v["sha256"] == sha]
    if same:
        # The server's front ends report different Last-Modified stamps for one file
        # (00:43:53 and 00:07:45 GMT on 2026-10-16 for 584,117 identical bytes), so a new
        # name with an old hash is the same version. Keep the bytes, mark them, add a sighting.
        keep = part.with_name(name + f".same_as_{same[0]['file']}.expired")
        part.rename(keep)
        same[0].setdefault("seen_again", []).append({"last_modified": lm, "etag": etag, "at": fetched_before})
        save_manifest(m)
        print(f"same bytes as {same[0]['file']}; kept as {keep.name}")
        return 0
    part.rename(final)
    m["versions"].append({"file": name, "bytes": len(body), "sha256": sha, "last_modified": lm, "etag": etag,
                          "content_type": r.headers.get("Content-Type"), "fetched_after": fetched_after,
                          "fetched_before": fetched_before, "seconds": round(secs, 3)})
    save_manifest(m)
    print(f"written {name}  sha256 {sha}")
    return 0


def check() -> int:
    m = load_manifest()
    bad = 0
    for v in m["versions"]:
        p = DEST / v["file"]
        if not p.exists():
            print(f"MISSING {v['file']}")
            bad += 1
            continue
        body = p.read_bytes()
        ok, why = pdf_ok(body, v["bytes"])
        sha_ok = hashlib.sha256(body).hexdigest() == v["sha256"]
        print(f"{'ok ' if ok and sha_ok else 'BAD'} {v['file']}  {len(body)} B  {why}  sha256 {'match' if sha_ok else 'MISMATCH'}")
        bad += 0 if ok and sha_ok else 1
    return 1 if bad else 0


def selftest() -> int:
    fails = []
    good = b"%PDF-1.7\n" + b"x" * 5000 + b"\n%%EOF\n"
    if not pdf_ok(good, len(good))[0]:
        fails.append("clean PDF rejected")
    if pdf_ok(good[:3000], None)[0]:
        fails.append("seeded truncation (no %%EOF) passed")
    if pdf_ok(b"<html>" + good, None)[0]:
        fails.append("seeded HTML body passed")
    if pdf_ok(good, len(good) + 10)[0]:
        fails.append("seeded Content-Length mismatch passed")
    if version_name("Fri, 16 Oct 2026 00:43:53 GMT") != f"{STEM}_20261016T004353Z.pdf":
        fails.append("version name from Last-Modified")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.pdf"
        p.write_bytes(good)
        moved = set_aside(p)
        if p.exists() or not moved.exists() or not moved.name.endswith(".bad_1"):
            fails.append("set_aside did not rename to .bad_1")
    for f in fails:
        print("SELFTEST FAIL:", f)
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.check:
        return check()
    if a.fetch:
        return fetch()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
