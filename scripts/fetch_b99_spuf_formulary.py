"""B99: fetch one member of the CMS Part D quarterly SPUF ZIP by byte range.

The SPUF package (SPUF_2026_20261007.zip, 2,485,007,192 bytes, data.cms.gov, free) holds
fifteen inner ZIPs. Only the "basic drugs formulary file" is needed here (it carries the
proxy NDC next to each RXCUI on every plan formulary), and it is the first member, so this
script fetches the package's central directory, finds that member, fetches its bytes with an
HTTP Range request, inflates it, and checks the CRC-32 and size against the central directory.

Resumable: the range file is continued from its current length. A range file longer than the
member, a short read, or a CRC mismatch stops the script without writing the inner ZIP.
Writes manifest.json with URL, member offsets, bytes and SHA-256.

usage: python -I fetch_b99_spuf_formulary.py OUT_DIR
"""
import hashlib
import json
import os
import struct
import sys
import urllib.request
import zipfile
import zlib

URL = ("https://data.cms.gov/sites/default/files/2026-10/"
       "062e9434-ed9d-4e83-abbd-4d64eb375949/SPUF_2026_20261007.zip")
MEMBER = "basic drugs formulary file  PPUF_2026Q3.zip"
UA = {"User-Agent": "Mozilla/5.0 (research fetch; B99)"}
TAIL = 65536


def get_range(start: int, end: int) -> bytes:
    req = urllib.request.Request(URL, headers={**UA, "Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status != 206:
            raise SystemExit(f"server ignored the Range request (HTTP {r.status})")
        return r.read()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def central_directory(total: int) -> dict:
    tail = get_range(total - TAIL, total - 1)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise SystemExit("no end-of-central-directory record in the last 64 KiB")
    n, cd_size, cd_off = struct.unpack("<HII", tail[i + 10:i + 20])
    base = total - len(tail)
    p, out = cd_off - base, {}
    for _ in range(n):
        if tail[p:p + 4] != b"PK\x01\x02":
            raise SystemExit("central directory entry signature mismatch")
        method, = struct.unpack("<H", tail[p + 10:p + 12])
        crc, csz, usz = struct.unpack("<III", tail[p + 16:p + 28])
        fl, el, cl = struct.unpack("<HHH", tail[p + 28:p + 34])
        off, = struct.unpack("<I", tail[p + 42:p + 46])
        name = tail[p + 46:p + 46 + fl].decode("cp437")
        out[name] = {"method": method, "crc": crc, "csize": csz, "usize": usz, "offset": off}
        p += 46 + fl + el + cl
    names = sorted(out, key=lambda k: out[k]["offset"])
    for a, b in zip(names, names[1:]):
        out[a]["next_offset"] = out[b]["offset"]
    out[names[-1]]["next_offset"] = cd_off
    return out


def main(argv) -> int:
    out = os.path.abspath(argv[0])
    os.makedirs(out, exist_ok=True)
    req = urllib.request.Request(URL, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers["Content-Length"])
    cd = central_directory(total)
    m = cd[MEMBER]
    span = m["next_offset"] - m["offset"]
    part = os.path.join(out, "member.range")
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if have > span:
        raise SystemExit(f"{part}: {have} bytes, member span is {span}; not touching it")
    if have < span:
        chunk = get_range(m["offset"] + have, m["offset"] + span - 1)
        with open(part, "ab") as fh:
            fh.write(chunk)
    raw = open(part, "rb").read()
    if len(raw) != span:
        raise SystemExit(f"{part}: truncated, {len(raw)} of {span} bytes")
    if raw[:4] != b"PK\x03\x04":
        raise SystemExit("local header signature mismatch")
    fl, el = struct.unpack("<HH", raw[26:30])
    data = raw[30 + fl + el:30 + fl + el + m["csize"]]
    if len(data) != m["csize"]:
        raise SystemExit("compressed data shorter than the central directory says")
    body = zlib.decompress(data, -15) if m["method"] == 8 else data
    if len(body) != m["usize"] or (zlib.crc32(body) & 0xFFFFFFFF) != m["crc"]:
        raise SystemExit("inflated member fails its size or CRC-32 check")
    inner = os.path.join(out, "basic_drugs_formulary_PPUF_2026Q3.zip")
    with open(inner, "wb") as fh:
        fh.write(body)
    dest = os.path.join(out, "extracted")
    members = []
    with zipfile.ZipFile(inner) as z:
        if z.testzip() is not None:
            raise SystemExit("inner ZIP fails its CRC check")
        for info in z.infolist():
            target = os.path.abspath(os.path.join(dest, info.filename))
            if not target.startswith(dest + os.sep):
                raise SystemExit(f"member escapes the target directory: {info.filename}")
            if not info.is_dir() and not os.path.exists(target):
                z.extract(info, dest)
            if not info.is_dir():
                members.append(target)
    manifest = {
        "url": URL, "package_bytes": total, "member": MEMBER,
        "member_offset": m["offset"], "member_span": span,
        "member_csize": m["csize"], "member_usize": m["usize"], "member_crc32": m["crc"],
        "range_file_sha256": sha256(raw), "inner_zip_sha256": sha256(body),
        "extracted": sorted(
            [{"file": os.path.relpath(t, out).replace(os.sep, "/"),
              "bytes": os.path.getsize(t), "sha256": sha256(open(t, "rb").read())}
             for t in members], key=lambda x: x["file"]),
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(json.dumps(manifest, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
