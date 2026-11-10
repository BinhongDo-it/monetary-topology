"""B99: fetch the CMS Part D Formulary Reference File (FRF) and unpack it.

The package carries an End User Point Agreement; it was accepted on 2026-10-29 (see the B99
section of SOURCES.md). The download link on the Formulary Guidance page serves the ZIP
directly, with no click-through page in front of it.

Resumable: a partial file is continued with an HTTP Range request. A file whose size does not
match the server's Content-Length, or a ZIP that fails its CRC check, is reported and not
unpacked. Members are unpacked only if their resolved path stays inside the target directory.
Writes manifest.json with URL, bytes and SHA-256 of the package and every unpacked member.

usage: python -I fetch_b99_partd_ref.py OUT_DIR
"""
import hashlib
import json
import os
import sys
import urllib.request
import zipfile

URL = "https://www.cms.gov/files/zip/cy-2026-september-formulary-reference-file.zip-0"
NAME = "cy-2026-september-formulary-reference-file.zip"
UA = {"User-Agent": "Mozilla/5.0 (research fetch; B99)"}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch(url: str, path: str, size: int) -> None:
    have = os.path.getsize(path) if os.path.exists(path) else 0
    if have == size:
        return
    if have > size:
        raise SystemExit(f"{path}: {have} bytes on disk, server says {size}; not touching it")
    headers = dict(UA)
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "ab") as fh:
        if have and r.status != 206:
            raise SystemExit(f"server ignored the Range request (HTTP {r.status}); stop")
        for chunk in iter(lambda: r.read(1 << 20), b""):
            fh.write(chunk)
    got = os.path.getsize(path)
    if got != size:
        raise SystemExit(f"{path}: truncated, {got} of {size} bytes")


def main(argv) -> int:
    out = os.path.abspath(argv[0])
    os.makedirs(out, exist_ok=True)
    size = remote_size(URL)
    pkg = os.path.join(out, NAME)
    fetch(URL, pkg, size)
    with zipfile.ZipFile(pkg) as z:
        bad = z.testzip()
        if bad is not None:
            raise SystemExit(f"CRC failure on member {bad}; not unpacking")
        dest = os.path.join(out, "extracted")
        members = []
        for info in z.infolist():
            target = os.path.abspath(os.path.join(dest, info.filename))
            if not target.startswith(dest + os.sep):
                raise SystemExit(f"member escapes the target directory: {info.filename}")
            members.append((info, target))
        for info, target in members:
            if info.is_dir():
                continue
            if not os.path.exists(target):
                z.extract(info, dest)
    manifest = {
        "url": URL, "file": NAME, "bytes": os.path.getsize(pkg), "sha256": sha256(pkg),
        "content_length": size,
        "license": "End User Point Agreement in the package, accepted 2026-10-29",
        "members": sorted(
            [{"file": os.path.relpath(t, out).replace(os.sep, "/"),
              "bytes": os.path.getsize(t), "sha256": sha256(t)}
             for i, t in members if not i.is_dir()], key=lambda m: m["file"]),
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(json.dumps(manifest, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
