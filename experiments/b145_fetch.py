"""B145 arm A, retrieval: the Berkes-Nencka replication packages on Harvard Dataverse.

Two files of doi:10.7910/DVN/TYVVY2 (CC0, no login), each into its own directory:

  data_pkg/  ~data_restat_upload.7z                   datafile 9659456, 491,062,786 bytes
  code_pkg/  ~2023.10_conditional_accept_upload.7z    datafile 9659455,   4,588,918 bytes

Resumable: bytes arrive in <name>.partial and the request asks for the rest with a Range
header, so a run that stops resumes where it stopped. A file is renamed to its final name
only when its length equals the length the repository lists and it opens with the 7z
signature; anything else stays .partial and is reported. Nothing reads a .partial file.
SHA-256 and length of every finished file go to data/raw/b145/b145_manifest.json.

Run from the repo root:
    python experiments/b145_fetch.py           fetch what is missing
    python experiments/b145_fetch.py --plan    what is on disk and what is missing
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b145"
MANIFEST = RAW / "b145_manifest.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research replication reader"
SEVENZ = b"7z\xbc\xaf\x27\x1c"
FILES = {
    "data_pkg": ("~data_restat_upload.7z", "https://dataverse.harvard.edu/api/access/datafile/9659456",
                 491062786),
    "code_pkg": ("~2023.10_conditional_accept_upload.7z", "https://dataverse.harvard.edu/api/access/datafile/9659455",
                 4588918),
}
CHUNK = 1 << 20


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def fetch_one(key: str) -> dict:
    name, url, size = FILES[key]
    folder = RAW / key
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / name
    part = folder / (name + ".partial")
    if final.exists():
        print(f"{key}: on disk, {final.stat().st_size:,} bytes")
    else:
        for attempt in range(1, 9):
            have = part.stat().st_size if part.exists() else 0
            if have == size:
                break
            if have > size:
                print(f"{key}: .partial is {have:,} bytes, longer than the listed {size:,}; left as is")
                return {"key": key, "status": "too_long", "bytes": have}
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": f"bytes={have}-"})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    code = r.status
                    if have and code != 206:
                        print(f"{key}: server ignored the range (status {code}); this pass appends nothing")
                        return {"key": key, "status": "no_range", "bytes": have}
                    got = 0
                    with part.open("ab") as f:
                        for block in iter(lambda: r.read(CHUNK), b""):
                            f.write(block)
                            got += len(block)
                print(f"{key}: attempt {attempt}, +{got:,} bytes in {time.time() - t0:.1f} s")
            except Exception as exc:  # noqa: BLE001 - every failure resumes on the next attempt
                print(f"{key}: attempt {attempt} stopped: {exc!r}; resuming")
                time.sleep(5)
        have = part.stat().st_size if part.exists() else 0
        if have != size:
            print(f"{key}: {have:,} of {size:,} bytes; stays .partial")
            return {"key": key, "status": "incomplete", "bytes": have}
        with part.open("rb") as f:
            head = f.read(6)
        if head != SEVENZ:
            print(f"{key}: length right but no 7z signature ({head!r}); stays .partial")
            return {"key": key, "status": "bad_signature", "bytes": have}
        part.rename(final)
    n = final.stat().st_size
    if n != size:
        print(f"{key}: final file is {n:,} bytes, listed {size:,}")
        return {"key": key, "status": "size_mismatch", "bytes": n}
    return {"key": key, "status": "ok", "file": f"{key}/{name}", "url": url, "bytes": n,
            "listed_bytes": size, "sha256": sha256(final)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args()
    if args.plan:
        for key, (name, _url, size) in FILES.items():
            final = RAW / key / name
            part = RAW / key / (name + ".partial")
            state = (f"done {final.stat().st_size:,}" if final.exists()
                     else f"partial {part.stat().st_size:,}" if part.exists() else "missing")
            print(f"{key}: {state} / {size:,}")
        return 0
    rows = [fetch_one(k) for k in FILES]
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    files = {r["key"]: r for r in old.get("files", [])}
    for r in rows:
        if r["status"] == "ok":
            files[r["key"]] = r
    MANIFEST.write_text(json.dumps({"dataset": "doi:10.7910/DVN/TYVVY2", "licence": "CC0",
                                    "files": [files[k] for k in sorted(files)]},
                                   indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for r in rows:
        print(r)
    return 0 if all(r["status"] == "ok" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
