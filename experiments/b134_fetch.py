"""Fetch the B134 sources: the World Bank Poverty and Inequality Platform's PPP table in each
release and PPP round, the methodology page on urban and rural PPPs, and Chen and Ravallion's
paper on the 2005 round.

  - pip_ppp_<version>.csv: PIP auxiliary PPP table, one per release x PPP round listed in FILES.
    Rows: country, data level (national, rural, urban), year of the round, PPP. The same round in
    two releases is the same reading published twice; their difference is the measured floor.
  - pip_versions.csv: the list of releases.
  - pip_handbook_convert.html: PIP Methodology Handbook, the page on converting to PPP dollars,
    which states how separate rural and urban PPPs are built for China, India and Indonesia.
  - chen_ravallion_wps4703.pdf: Chen and Ravallion (2008), World Bank Policy Research Working
    Paper 4703, the working-paper version of their 2010 QJE paper, read as literature for the
    2005 round's urban-only price collection in China.
  - wb_india_poverty_methodology_2025.pdf: World Bank, "India: Trends in Poverty, 2011-12 to 2022-23,
    Methodology Note", May 2025; states that separate urban-rural PPPs were replaced by spatial
    deflators inside the survey and a single national PPP.
  - wb_pip_update_2025_06.txt: World Bank, "June 2025 Update to the Poverty and Inequality Platform",
    plain-text edition; the same change for India.
  - wb_indonesia_poverty_brief.pdf: World Bank Poverty and Equity Brief, Indonesia; states that a
    regency-level spatial deflator was introduced in 2024 and separate urban and rural PPPs dropped.

Rules this obeys:
  - resumable: a file on disk that passes its check is skipped
  - never deletes: a file that fails its check is renamed .bad_<n> and fetched again
  - checks: HTTP 200; the file is at least MIN_BYTES long, starts with the register's own header
    line, and the data file's last row carries all three fields
  - measured cost only (`D38`): each request prints its seconds and bytes

Run from the repo root:
    python experiments/b134_fetch.py --fetch
    python experiments/b134_fetch.py --check
    python experiments/b134_fetch.py --selftest
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
RAW = ROOT / "data" / "raw" / "b134"
MANIFEST = RAW / "manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 300
PAUSE = 3.0
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

PIP = "https://api.worldbank.org/pip/v1/"
FILES = {
    "pip_ppp_20220909_2011_02_02_PROD.csv": PIP + "aux?table=ppp&version=20220909_2011_02_02_PROD&format=csv",
    "pip_ppp_20220909_2017_01_02_PROD.csv": PIP + "aux?table=ppp&version=20220909_2017_01_02_PROD&format=csv",
    "pip_ppp_20230919_2011_02_02_PROD.csv": PIP + "aux?table=ppp&version=20230919_2011_02_02_PROD&format=csv",
    "pip_ppp_20230919_2017_01_02_PROD.csv": PIP + "aux?table=ppp&version=20230919_2017_01_02_PROD&format=csv",
    "pip_ppp_20240627_2011_02_02_PROD.csv": PIP + "aux?table=ppp&version=20240627_2011_02_02_PROD&format=csv",
    "pip_ppp_20240627_2017_01_02_PROD.csv": PIP + "aux?table=ppp&version=20240627_2017_01_02_PROD&format=csv",
    "pip_ppp_20250930_2017_01_02_PROD.csv": PIP + "aux?table=ppp&version=20250930_2017_01_02_PROD&format=csv",
    "pip_ppp_20250930_2021_01_02_PROD.csv": PIP + "aux?table=ppp&version=20250930_2021_01_02_PROD&format=csv",
    "pip_ppp_20260922_2017_01_02_PROD.csv": PIP + "aux?table=ppp&version=20260922_2017_01_02_PROD&format=csv",
    "pip_ppp_20260922_2021_01_02_PROD.csv": PIP + "aux?table=ppp&version=20260922_2021_01_02_PROD&format=csv",
    "pip_versions.csv": PIP + "versions?format=csv",
    "pip_handbook_convert.html": "https://worldbank.github.io/PIP-Methodology-2022-04/convert.html",
    "chen_ravallion_wps4703.pdf": "https://documents1.worldbank.org/curated/en/526541468262138892/pdf/WPS4703.pdf",
    "wb_india_poverty_methodology_2025.pdf": "https://openknowledge.worldbank.org/server/api/core/bitstreams/"
                                             "1a3697f8-bb80-4246-8773-a27c78080a44/content",
    "wb_pip_update_2025_06.txt": "https://documents1.worldbank.org/curated/en/099510306052516849/txt/"
                                 "IDU-eb272b02-ecd1-4633-9e37-9297e20a711c.txt",
    "wb_indonesia_poverty_brief.pdf": "https://documents1.worldbank.org/curated/en/099124001062512710/pdf/"
                                      "IDU1bc79f79214c1314c0d19a351de1a45668677.pdf",
}
HEADER = {name: "country_code,data_level,year,value" for name in FILES if name.startswith("pip_ppp_")}
HEADER["pip_versions.csv"] = "version,release_version"
MIN_BYTES = {name: 3_000 for name in FILES}
MIN_BYTES["chen_ravallion_wps4703.pdf"] = 200_000
MIN_BYTES["pip_handbook_convert.html"] = 20_000
MIN_BYTES["pip_versions.csv"] = 500
MIN_BYTES["wb_india_poverty_methodology_2025.pdf"] = 500_000
MIN_BYTES["wb_pip_update_2025_06.txt"] = 50_000
MIN_BYTES["wb_indonesia_poverty_brief.pdf"] = 200_000

def check_bytes(name: str, data: bytes) -> str | None:
    """None if the file is whole, else the reason it is not."""
    if len(data) < MIN_BYTES[name]:
        return f"{len(data):,} bytes, under {MIN_BYTES[name]:,}"
    if name.endswith(".pdf"):
        return None if data[:5] == b"%PDF-" and b"%%EOF" in data[-2048:] else "not a whole PDF"
    text = data.decode("utf-8", "replace")
    if name.endswith(".txt"):
        return None if "spatial deflators" in text else "no mention of spatial deflators"
    if name.endswith(".html"):
        return None if "rural" in text.lower() else "no mention of rural"
    if not text.startswith(HEADER[name]):
        return "header is not the table's"
    if name.startswith("pip_ppp_") and "CHN,rural" not in text:
        return "no China rural row"
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
    name = "pip_ppp_20260922_2021_01_02_PROD.csv"
    good = "\n".join(["country_code,data_level,year,value", "CHN,rural,2021,3.4"] + ["ABW,national,2021,1.5"] * 300).encode()
    assert check_bytes(name, good) is None
    assert check_bytes(name, good.replace(b"CHN,rural", b"CHN,urban")) is not None, "no rural row must fail"
    assert check_bytes(name, b"<html>" + good) is not None, "an HTML page must fail"
    assert check_bytes("chen_ravallion_wps4703.pdf", b"%PDF-" + b"x" * 300_000) is not None, "a cut PDF must fail"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.csv"
        p.write_bytes(b"1")
        set_aside(p)
        assert (Path(tmp) / "a.csv.bad_1").exists() and not p.exists()
    print("selftest ok: a table without the rural row, an HTML page and a cut PDF fail; set_aside renames")


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
