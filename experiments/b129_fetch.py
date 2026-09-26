"""Fetch the B129 sources: the Berlin rent index, the 2019 rent table, the statute, one paper.

Seven files, each named in FILES with the URL it came from. Nothing here is scraped: every
file is a published document at a fixed address.

Rules this obeys:
  - resumable: a file on disk that passes its check is skipped
  - never deletes: a file that fails its check is renamed .bad_<n> and fetched again
  - checks: HTTP 200; a PDF starts with %PDF and carries %%EOF in its last 2 KB; an XLSX is a
    zip archive that opens and holds xl/workbook.xml
  - measured cost only (`D38`): each request prints its seconds and bytes

Run from the repo root:
    python experiments/b129_fetch.py --fetch
    python experiments/b129_fetch.py --check
    python experiments/b129_fetch.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b129" / "raw"
MANIFEST = RAW / "manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 120
PAUSE = 10.0   # berlin.de answered 429 to two requests 0.6 s apart on 2026-09-23
LIB = "https://www.statistischebibliothek.de/mir/servlets/MCRFileNodeServlet"

FILES = {
    "vpi_berlin_2020m12.xlsx": LIB + "/BBHeft_derivate_00023460/SB_M01-02-00_2020m12_BE.xlsx",
    "vpi_berlin_2022m09.xlsx": LIB + "/BBHeft_derivate_00027867/SB_M01-02-00_2022m09_BE.xlsx",
    "vpi_berlin_2022m09.pdf": LIB + "/BBHeft_derivate_00027866/SB_M01-02-00_2022m09_BE.pdf",
    "mietspiegeltabelle2019.pdf":
        "https://www.berlin.de/sen/wohnen/_assets/archiv/mietspiegeltabelle2019.pdf",
    "mietspiegel2019_ergebnisbericht.pdf":
        "https://www.berlin.de/sen/wohnen/_assets/service/mietspiegel2019_berlin_ergebnisbericht_pdf.pdf",
    "gvbl_2020_nr6_mietenwog.pdf":
        "https://www.berlin.de/sen/justiz/service/gesetze-und-verordnungen/2020/"
        "ausgabe-nr-6-vom-22-2-2020-s-49-56.pdf",
    # berlin.de answers the GVBl address with 429 plus a challenge cookie (2026-09-23, three
    # tries over ten minutes). Not worked around. The committee's recommendation carries the
    # text as adopted, and Hahn et al. Table 1 reprints the §6 table: two routes to one table.
    # 18/2437 amends §6 only in Abs. 4 and 5, so Abs. 1-3 (the table and both surcharges) are
    # the draft's text, 18/2347.
    "abgh_d18_2437.pdf": "https://www.parlament-berlin.de/ados/18/IIIPlen/vorgang/d18-2437.pdf",
    "abgh_d18_2347.pdf": "https://www.parlament-berlin.de/ados/18/iiiplen/vorgang/d18-2347.pdf",
    "bgb_556f.html": "https://www.gesetze-im-internet.de/bgb/__556f.html",
    "hahn_2023_rent_freeze.pdf":
        "https://www.repository.cam.ac.uk/bitstreams/245e4319-8a6c-427d-abb1-188faa57c5a7/download",
}


def check(name: str, body: bytes) -> str | None:
    """None if the body is a whole file of its kind, else why not."""
    if name.endswith(".pdf"):
        if not body.startswith(b"%PDF"):
            return "not a PDF (no %PDF header)"
        if b"%%EOF" not in body[-2048:]:
            return "truncated PDF (no %%EOF in the last 2 KB)"
        return None
    if name.endswith(".xlsx"):
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                if "xl/workbook.xml" not in z.namelist():
                    return "zip without xl/workbook.xml"
                bad = z.testzip()
                if bad is not None:
                    return f"corrupt member {bad}"
        except zipfile.BadZipFile:
            return "not a zip archive"
        return None
    if name.endswith(".html"):
        if b"</html>" not in body[-4096:].lower():
            return "truncated HTML (no closing </html>)"
        if b"556f" not in body:
            return "page does not carry the section it was fetched for"
        return None
    return "unknown kind"


def set_aside(path: Path) -> None:
    n = 1
    while path.with_name(f"{path.name}.bad_{n}").exists():
        n += 1
    path.rename(path.with_name(f"{path.name}.bad_{n}"))


def fetch(raw: Path = RAW) -> int:
    raw.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    failures = 0
    for name, url in FILES.items():
        path = raw / name
        if path.exists():
            why = check(name, path.read_bytes())
            if why is None:
                print(f"skip  {name}")
                continue
            print(f"bad   {name}: {why}; set aside")
            set_aside(path)
        time.sleep(PAUSE)
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                status, body = r.status, r.read()
        except Exception as e:  # noqa: BLE001 - reported, not swallowed
            print(f"FAIL  {name}: {e}")
            failures += 1
            continue
        secs = time.perf_counter() - t0
        why = check(name, body) if status == 200 else f"HTTP {status}"
        if why is not None:
            print(f"FAIL  {name}: {why} ({secs:.1f} s)")
            failures += 1
            continue
        path.write_bytes(body)
        manifest[name] = {"url": url, "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest()}
        print(f"ok    {name}: {len(body):,} bytes in {secs:.1f} s")
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    return failures


def check_all(raw: Path = RAW) -> int:
    bad = 0
    for name in FILES:
        path = raw / name
        why = "missing" if not path.exists() else check(name, path.read_bytes())
        print(f"{'ok  ' if why is None else 'BAD '} {name}{'' if why is None else ': ' + why}")
        bad += why is not None
    return bad


def selftest() -> None:
    good_pdf = b"%PDF-1.4\n" + b"x" * 5000 + b"\n%%EOF\n"
    assert check("a.pdf", good_pdf) is None
    assert check("a.pdf", good_pdf[:3000]) is not None, "a truncated PDF must fail"
    assert check("a.pdf", b"<html>403</html>") is not None, "an HTML error page must fail"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", "<workbook/>")
    assert check("a.xlsx", buf.getvalue()) is None
    assert check("a.xlsx", buf.getvalue()[:40]) is not None, "a cut zip must fail"
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as z:
        z.writestr("other.xml", "<x/>")
    assert check("a.xlsx", buf2.getvalue()) is not None, "a zip that is not a workbook must fail"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "f.pdf"
        p.write_bytes(b"junk")
        set_aside(p)
        assert not p.exists() and (Path(d) / "f.pdf.bad_1").exists(), "set_aside renames"
    print("selftest ok: 6 checks and set_aside")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.fetch:
        sys.exit(1 if fetch() else 0)
    else:
        sys.exit(1 if check_all() else 0)
