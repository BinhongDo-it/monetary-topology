"""Fetch the B133 sources: the BEA NIPA annual flat file and its two registers.

Three files, each named in FILES with the URL it came from. No key or registration is needed.

  - NipaDataA.txt: every published annual NIPA series, one row per series and year
    (SeriesCode, Period, Value). Read here: the PCE price index (DPCERG) and its percent change
    (DPCERV), the contributions to the PCE price change of imputed rental of owner-occupied nonfarm
    housing (CE001228) and of financial services furnished without payment (CE001209), the price
    indexes for gross value added of the nonfarm business sector (B358RG), the business sector
    (B195RG) and GDP (A191RG), and the current-dollar values that weight them.
  - SeriesRegister.txt: series code, label, metric, and the table lines each series sits on.
  - TablesRegister.txt: table ids and titles.

Rules this obeys:
  - resumable: a file on disk that passes its check is skipped
  - never deletes: a file that fails its check is renamed .bad_<n> and fetched again
  - checks: HTTP 200; the file is at least MIN_BYTES long, starts with the register's own header
    line, and the data file's last row carries all three fields
  - measured cost only (`D38`): each request prints its seconds and bytes

Run from the repo root:
    python experiments/b133_fetch.py --fetch
    python experiments/b133_fetch.py --check
    python experiments/b133_fetch.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b133"
MANIFEST = RAW / "manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 300
PAUSE = 3.0
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

BEA = "https://apps.bea.gov/national/Release/TXT/"
FILES = {
    "NipaDataA.txt": BEA + "NipaDataA.txt",
    "SeriesRegister.txt": BEA + "SeriesRegister.txt",
    "TablesRegister.txt": BEA + "TablesRegister.txt",
}
MIN_BYTES = {"NipaDataA.txt": 5_000_000, "SeriesRegister.txt": 500_000, "TablesRegister.txt": 20_000}
HEADER = {"NipaDataA.txt": "%SeriesCode,Period,Value", "SeriesRegister.txt": "%SeriesCode,SeriesLabel",
          "TablesRegister.txt": "TableId,TableTitle"}


def check_bytes(name: str, data: bytes) -> str | None:
    """None if the file is whole, else the reason it is not."""
    if len(data) < MIN_BYTES[name]:
        return f"{len(data):,} bytes, under {MIN_BYTES[name]:,}"
    text = data.decode("utf-8", "replace")
    if not text.startswith(HEADER[name]):
        return "header is not the register's"
    last = text.rstrip().splitlines()[-1]
    if name == "NipaDataA.txt" and len(last.split(",")) < 3:
        return "last row cut"
    return None


def set_aside(path: Path) -> None:
    n = 1
    while path.with_name(f"{path.name}.bad_{n}").exists():
        n += 1
    path.rename(path.with_name(f"{path.name}.bad_{n}"))


def fetch() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    bad = 0
    for name, url in FILES.items():
        path = RAW / name
        if path.exists():
            why = check_bytes(name, path.read_bytes())
            if why is None:
                print(f"skip {name}: on disk and whole")
                continue
            print(f"{name} on disk fails ({why}); set aside")
            set_aside(path)
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            status, data = r.status, r.read()
        secs = time.perf_counter() - t0
        why = None if status == 200 else f"HTTP {status}"
        why = why or check_bytes(name, data)
        print(f"{name}: {secs:.1f} s, {len(data):,} bytes, {'ok' if why is None else why}")
        if why is not None:
            bad += 1
            continue
        path.write_bytes(data)
        manifest[name] = {"url": url, "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()}
        time.sleep(PAUSE)
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    return 1 if bad else 0


def check() -> int:
    bad = 0
    for name in FILES:
        path = RAW / name
        why = "missing" if not path.exists() else check_bytes(name, path.read_bytes())
        print(f"{name}: {'ok' if why is None else why}")
        bad += why is not None
    return 1 if bad else 0


def selftest() -> None:
    good = "\n".join(["%SeriesCode,Period,Value"] + ['A,1999,"1.0"'] * 400_000).encode()
    assert check_bytes("NipaDataA.txt", good) is None
    assert check_bytes("NipaDataA.txt", good[:4_000_000]) is not None, "a short file must fail"
    assert check_bytes("NipaDataA.txt", good + b"\nA,19") is not None, "a cut last row must fail"
    assert check_bytes("NipaDataA.txt", b"<html>" + good) is not None, "an HTML page must fail"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.txt"
        p.write_bytes(b"1")
        set_aside(p)
        assert (Path(tmp) / "a.txt.bad_1").exists() and not p.exists()
    print("selftest ok: short, cut and HTML files fail; set_aside renames")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(fetch() if a.fetch else check())
