"""Fetch the free files B99 reads: two NADAC annual reference files, the NADAC week-to-week
comparison file, and FDA's NSDE. DailyMed SPL is not fetched here (it is the GB-scale step the
design keeps for after the pair count, `D21`).

    nadac/       NADAC (National Average Drug Acquisition Cost) 2026 and 2025, data.medicaid.gov
    comparison/  NADAC Comparison, data.medicaid.gov (one cumulative file)
    nsde/        Comprehensive NDC SPL Data Elements File, the zip FDA's NSDE page links

Rules this obeys:
  - resumable: bytes go to `<name>.part`; a rerun asks for the rest with a Range request and
    checks that the server's Content-Range starts where the part ends. A server that answers
    with the whole file instead makes the old part retire (renamed, never deleted, rule 5)
  - detects truncation: the finished file must be exactly the size the server announced; a CSV
    must carry the source's own header (`D54`), end in a newline, and have as many fields on
    every row as its header; a zip must open and pass `testzip`. A file that fails is renamed
  - a file already on disk is skipped only when it is the file the manifest recorded (bytes and
    SHA-256)
  - the zip is untrusted: `--extract` writes its members into a new, empty directory, by base
    name only, and refuses any member whose name carries a path
  - measured cost: every transfer is timed into the manifest (`D38`)

Run with `python -I` (the downloads are untrusted data):

    python -I scripts/fetch_b99.py --probe      # sizes only, nothing written
    python -I scripts/fetch_b99.py              # fetch what is missing or partial
    python -I scripts/fetch_b99.py --extract    # unpack the NSDE zip into a new directory
    python -I scripts/fetch_b99.py --check      # check what is on disk, write nothing
    python -I scripts/fetch_b99.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b99"
UA = "Mozilla/5.0 (monetary-topology research fetcher)"
CHUNK = 1 << 20

NADAC_HEADER = ["NDC Description", "NDC", "NADAC Per Unit", "Effective Date", "Pricing Unit",
                "Pharmacy Type Indicator", "OTC", "Explanation Code",
                "Classification for Rate Setting", "Corresponding Generic Drug NADAC Per Unit",
                "Corresponding Generic Drug Effective Date", "As of Date"]
COMP_HEADER = ["NDC Description", "NDC", "Old NADAC Per Unit", "New NADAC Per Unit",
               "Classification for Rate Setting", "Percent Change", "Primary Reason",
               "Start Date", "End Date", "Effective Date"]

#: name -> (subdirectory, URL, kind, expected header or None). The URLs are the downloadURL
#: fields of the data.medicaid.gov metastore entries and the link on FDA's NSDE page, read
#: 2026-10-29.
SOURCES = {
    "nadac_2026": ("nadac", "https://download.medicaid.gov/data/"
                   "nadac-national-average-drug-acquisition-cost-10-28-2026.csv", "csv",
                   NADAC_HEADER),
    "nadac_2025": ("nadac", "https://download.medicaid.gov/data/"
                   "nadac-national-average-drug-acquisition-cost-12-31-2025.csv", "csv",
                   NADAC_HEADER),
    "comparison": ("comparison", "https://download.medicaid.gov/data/"
                   "nadac-comparison-10-28-2026.csv", "csv", COMP_HEADER),
    "nsde": ("nsde", "https://download.open.fda.gov/"
             "Comprehensive_NDC_SPL_Data_Elements_File.zip", "zip", None),
}


def target(name: str) -> Path:
    sub, url, _k, _h = SOURCES[name]
    return RAW / sub / url.rsplit("/", 1)[1]


def stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def retire(path: Path, why: str) -> Path:
    dead = path.with_name(f"{path.name}.expired_{stamp()}_{why}")
    path.rename(dead)  # never delete (engineering rule 5)
    print(f"    retired {path.name} -> {dead.name}")
    return dead


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def probe(url: str) -> dict:
    """Total size from a one-byte Range request (the CSV host sends no Content-Length on HEAD)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        cr = r.headers.get("Content-Range", "")
        total = int(cr.rsplit("/", 1)[1]) if "/" in cr else int(r.headers.get("Content-Length"))
        return {"bytes": total, "last_modified": r.headers.get("Last-Modified"),
                "etag": r.headers.get("ETag"), "status": r.status}


# ---------------------------------------------------------------------------- checks

def check_csv(path: Path, header: list[str]) -> tuple[bool, str, dict]:
    """The size check against the server's announcement is the truncation guard; this one
    checks the rows. A file that does not end in a newline is accepted only when its last row
    still has the header's field count and its last field has the shape of the column's first
    data row (the NADAC 2025 file is published that way, 2026-10-29): a row cut inside its
    last field would keep the field count, so the shape check is what catches it."""
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        trailing_nl = f.read(1) == b"\n"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        head = next(rd, [])
        if head != header:
            return False, f"header {head} is not the source's {header}", {"header": head}
        n, short = 0, 0
        first_short = None
        shapes, last = set(), None
        for r in rd:
            n += 1
            if len(r) != len(head):
                short += 1
                first_short = first_short or n + 1
            elif last is not None:
                shapes.add(_shape(last[-1]))
            last = r
    if short:
        return False, f"{short} rows with the wrong field count, first at line {first_short}", {}
    if n == 0:
        return False, "no data rows", {}
    note = ""
    if not trailing_nl:
        if _shape(last[-1]) not in shapes:
            return False, (f"no trailing newline and the last field {last[-1]!r} has a shape no "
                           "earlier row has (cut mid-field)"), {}
        note = "; no trailing newline as published, last row whole"
    return True, f"{n} rows, header as the source prints it{note}", {"rows": n, "header": head,
                                                                      "trailing_newline": trailing_nl}


def _shape(s: str) -> str:
    return "".join("9" if c.isdigit() else "A" if c.isalpha() else c for c in s)


def check_zip(path: Path) -> tuple[bool, str, dict]:
    if not zipfile.is_zipfile(path):
        return False, "not a zip", {}
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad is not None:
            return False, f"member {bad} fails its CRC", {}
        members = [{"name": i.filename, "bytes": i.file_size} for i in z.infolist()]
    return True, f"{len(members)} members, CRCs pass", {"members": members}


def check_file(name: str, path: Path) -> tuple[bool, str, dict]:
    _s, _u, kind, header = SOURCES[name]
    return check_csv(path, header) if kind == "csv" else check_zip(path)


# ---------------------------------------------------------------------------- fetch

def transfer(url: str, part: Path, total: int) -> float:
    """Append to `part` until it holds `total` bytes. Returns seconds spent."""
    have = part.stat().st_size if part.exists() else 0
    if have > total:
        retire(part, "longer_than_announced")
        have = 0
    if have == total:
        return 0.0
    t = time.perf_counter()
    hdr = {"User-Agent": UA}
    if have:
        hdr["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=300) as r:
        if have:
            cr = r.headers.get("Content-Range", "")
            if r.status != 206 or not cr.startswith(f"bytes {have}-"):
                print(f"    server ignored the Range (status {r.status}, {cr!r}); restarting")
                retire(part, "range_ignored")
                return transfer(url, part, total)
        with open(part, "ab") as f:
            done = have
            last = time.perf_counter()
            while True:
                b = r.read(CHUNK)
                if not b:
                    break
                f.write(b)
                done += len(b)
                if time.perf_counter() - last > 15:
                    print(f"    {done / 1e6:.1f} / {total / 1e6:.1f} MB")
                    last = time.perf_counter()
    return round(time.perf_counter() - t, 1)


def run(only_check: bool) -> int:
    man_path = RAW / "b99_manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    bad = 0
    for name, (sub, url, _kind, _h) in SOURCES.items():
        path = target(name)
        if path.exists():
            entry = manifest.get(name, {})
            ok = (entry.get("bytes") == path.stat().st_size
                  and entry.get("sha256") == sha256_of(path))
            if ok:
                print(f"  have {name}: {entry['bytes']} bytes, SHA-256 as recorded")
                continue
            print(f"  {name} on disk is not the file the manifest recorded")
            if only_check:
                bad += 1
                continue
            retire(path, "not_in_manifest")
        if only_check:
            print(f"  missing {name}")
            bad += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        try:
            meta = probe(url)
            secs = transfer(url, part, meta["bytes"])
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  {name}: transfer stopped ({e}); rerun to resume from the part file")
            bad += 1
            continue
        size = part.stat().st_size
        if size != meta["bytes"]:
            print(f"  {name}: {size} bytes against the announced {meta['bytes']}; rerun to resume")
            bad += 1
            continue
        ok, why, info = check_file(name, part)
        if not ok:
            print(f"  {name}: whole by size but fails: {why}")
            retire(part, "failed_check")
            bad += 1
            continue
        os.replace(part, path)
        manifest[name] = {"url": url, "file": f"{sub}/{path.name}", "bytes": size,
                          "sha256": sha256_of(path), "last_modified": meta["last_modified"],
                          "etag": meta["etag"], "fetched": time.strftime("%Y-%m-%d"),
                          "seconds": secs, "check": why, **info}
        man_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")
        print(f"  got {name}: {size} bytes in {secs} s; {why}")
    return 1 if bad else 0


def extract() -> int:
    """NSDE members into a new, empty directory named after the zip's hash."""
    man_path = RAW / "b99_manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    entry = manifest["nsde"]
    zpath = target("nsde")
    if sha256_of(zpath) != entry["sha256"]:
        print("  the zip on disk is not the recorded one; refusing to extract")
        return 1
    out = RAW / "nsde" / f"extracted_{entry['sha256'][:12]}"
    if out.exists() and any(out.iterdir()):
        print(f"  {out.name} already holds files; leaving it")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with zipfile.ZipFile(zpath) as z:
        for i in z.infolist():
            if i.is_dir():
                continue
            nm = i.filename
            if "/" in nm or "\\" in nm or nm.startswith(".") or ".." in nm or ":" in nm:
                print(f"  refused member with a path in its name: {nm!r}")
                continue
            body = z.read(i)
            (out / nm).write_bytes(body)
            written.append({"name": nm, "bytes": len(body),
                            "sha256": hashlib.sha256(body).hexdigest()})
    entry["extracted_into"] = f"nsde/{out.name}"
    entry["extracted"] = written
    man_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"  extracted {len(written)} members into {out}")
    return 0


def do_probe() -> int:
    total = 0
    for name, (_s, url, _k, _h) in SOURCES.items():
        m = probe(url)
        total += m["bytes"]
        print(f"  {name:11s} {m['bytes'] / 1e6:8.1f} MB  {m['last_modified']}  {url}")
    print(f"  total {total / 1e6:.1f} MB")
    return 0


def selftest() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        hdr = ["A", "B", "C"]
        good = d / "g.csv"
        good.write_bytes(b"A,B,C\n1,2,3\n4,5,6\n")
        assert check_csv(good, hdr)[0]
        cut = d / "c.csv"
        cut.write_bytes(b"A,B,C\n1,2,3\n4,5")
        assert not check_csv(cut, hdr)[0]                    # cut mid-row
        dates = b"A,B,C\nx,1,12/30/2025\ny,2,\nz,3,12/31/2025"
        whole = d / "w.csv"
        whole.write_bytes(dates)                             # published without a final newline
        assert check_csv(whole, hdr)[0]
        mid = d / "m.csv"
        mid.write_bytes(dates[:-2])                          # cut inside the last field
        assert not check_csv(mid, hdr)[0]
        short = d / "s.csv"
        short.write_bytes(b"A,B,C\n1,2,3\n4,5\n")
        assert not check_csv(short, hdr)[0]                  # a whole row with a field missing
        renamed = d / "r.csv"
        renamed.write_bytes(b"A,B,D\n1,2,3\n")
        ok, why, info = check_csv(renamed, hdr)
        assert not ok and info["header"] == ["A", "B", "D"]  # header printed back (D54)
        page = d / "p.csv"
        page.write_bytes(b"<html>error</html>\n")
        assert not check_csv(page, hdr)[0]
        z = d / "z.zip"
        with zipfile.ZipFile(z, "w") as zz:
            zz.writestr("x.csv", "a,b\n1,2\n")
        assert check_zip(z)[0]
        zb = bytearray(z.read_bytes())
        k = zb.find(b"1,2")
        zb[k] = ord("9")                                     # one byte of a member changed
        zbad = d / "zb.zip"
        zbad.write_bytes(bytes(zb))
        assert not check_zip(zbad)[0]
        assert not check_zip(good)[0]
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if a.probe:
        return do_probe()
    if a.extract:
        return extract()
    return run(a.check)


if __name__ == "__main__":
    raise SystemExit(main())
