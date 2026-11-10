"""Fetch the B132 sources: household consumption by purpose in the national accounts, and the HICP.

Five files, each named in FILES with the URL it came from.

  - nama_10_co3_p3.json: Eurostat household final consumption expenditure by purpose (COICOP 1999),
    total, actual rentals (CP041), imputed rentals (CP042), financial services n.e.c. (CP126, where
    household FISIM is recorded), current prices and chain-linked volumes (2020), in million euro and
    in million units of national currency, every country and year published. Current price over
    volume is the implicit deflator.
  - nama_10_cp18.json: the same account by COICOP 2018, which carries the years after 2022: total,
    actual rentals (CP041), imputed rentals (CP042), financial services (CP122, household FISIM
    included), current prices and previous-year prices (PYP), in million euro and in million units
    of national currency. Current over previous-year price is each year's deflator change, and the
    differences add up exactly. A country's own price change is read in national currency: its euro
    series is converted at each year's exchange rate, so its euro deflator carries the exchange
    rate's move as well. Aggregates exist in euro only.
    The COICOP 1999 file above stops in 2022 for most countries and is kept as a cross-check.
  - prc_hicp_aind.json: HICP annual average index (2015 = 100), all items (CP00), actual rentals
    (CP041), financial services n.e.c. (CP126). The HICP has no imputed rentals, and its CP126 holds
    explicitly charged fees only.
  - insee_premiere_2002.html: INSEE Première no 2002, "La consommation des ménages en 2023", read
    as literature: it prints the 2023 consumption deflator with and without FISIM for France.
  - prc_hicp_inw.json: HICP item weights, per mille, same three items.

Rules this obeys:
  - resumable: a file on disk that passes its check is skipped
  - never deletes: a file that fails its check is renamed .bad_<n> and fetched again
  - checks: HTTP 200; a JSON file parses, carries "value" and "dimension", no "error", and
    at least MIN_VALUES values; an HTML file is over 20 KB and holds its marker phrase
  - measured cost only (`D38`): each request prints its seconds and bytes

Run from the repo root:
    python experiments/b132_fetch.py --fetch
    python experiments/b132_fetch.py --check
    python experiments/b132_fetch.py --selftest
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
RAW = ROOT / "data" / "raw" / "b132"
MANIFEST = RAW / "manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 300
PAUSE = 3.0
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

FILES = {
    "nama_10_co3_p3.json": API + "nama_10_co3_p3?coicop=TOTAL&coicop=CP041&coicop=CP042"
                           "&coicop=CP126&unit=CP_MEUR&unit=CLV20_MEUR&unit=CP_MNAC&unit=CLV20_MNAC"
                           "&format=JSON&lang=EN",
    "nama_10_cp18.json": API + "nama_10_cp18?coicop18=TOTAL&coicop18=CP041&coicop18=CP042"
                         "&coicop18=CP122&unit=CP_MEUR&unit=PYP_MEUR&unit=CP_MNAC&unit=PYP_MNAC"
                         "&format=JSON&lang=EN",
    "prc_hicp_aind.json": API + "prc_hicp_aind?coicop=CP00&coicop=CP041&coicop=CP126"
                          "&unit=INX_A_AVG&format=JSON&lang=EN",
    "prc_hicp_inw.json": API + "prc_hicp_inw?coicop=CP00&coicop=CP041&coicop=CP126"
                         "&format=JSON&lang=EN",
    "insee_premiere_2002.html": "https://www.insee.fr/fr/statistiques/8210847",
}
MIN_VALUES = {"nama_10_co3_p3.json": 10000, "nama_10_cp18.json": 6000, "prc_hicp_aind.json": 2000, "prc_hicp_inw.json": 2000}
#: Units a national-accounts file must carry; a reply without the national-currency pair is not whole.
NEED_UNITS = {"nama_10_co3_p3.json": ("CP_MEUR", "CLV20_MEUR", "CP_MNAC", "CLV20_MNAC"),
              "nama_10_cp18.json": ("CP_MEUR", "PYP_MEUR", "CP_MNAC", "PYP_MNAC")}
MIN_ROWS = {}
MARKER = {"insee_premiere_2002.html": "Sifim"}


def check_bytes(name: str, data: bytes) -> str | None:
    """None if the file is whole, else the reason it is not."""
    if name.endswith(".json"):
        try:
            d = json.loads(data.decode("utf-8"))
        except Exception as e:
            return f"not JSON: {e}"
        if "error" in d:
            return f"source error: {d['error']}"
        if "value" not in d or "dimension" not in d:
            return "no value or dimension block"
        if len(d["value"]) < MIN_VALUES[name]:
            return f"{len(d['value'])} values, fewer than {MIN_VALUES[name]}"
        if name in NEED_UNITS:
            have = set(d["dimension"].get("unit", {}).get("category", {}).get("index", {}))
            missing = [u for u in NEED_UNITS[name] if u not in have]
            if missing:
                return f"units missing: {missing}"
        return None
    if name.endswith(".csv"):
        text = data.decode("utf-8", "replace")
        lines = text.strip().splitlines()
        if not lines[0].startswith("KEY") or "OBS_VALUE" not in lines[0]:
            return "no KEY / OBS_VALUE header"
        if len(lines) < MIN_ROWS[name]:
            return f"{len(lines)} rows, fewer than {MIN_ROWS[name]}"
        if len(lines[-1].split(",")) < len(lines[0].split(",")) - 2:
            return "last row cut"
        return None
    if len(data) < 20_000:
        return f"{len(data)} bytes, under 20 KB"
    if MARKER[name].lower() not in data.decode("utf-8", "replace").lower():
        return f"marker {MARKER[name]!r} absent"
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
        if name.endswith(".json"):
            manifest[name]["source_updated"] = json.loads(data.decode("utf-8")).get("updated")
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
    units = {"unit": {"category": {"index": {u: i for i, u in enumerate(NEED_UNITS["nama_10_co3_p3.json"])}}}}
    good = json.dumps({"value": {str(i): 1 for i in range(12000)}, "dimension": units}).encode()
    assert check_bytes("nama_10_co3_p3.json", good) is None
    euro_only = json.dumps({"value": {str(i): 1 for i in range(12000)},
                            "dimension": {"unit": {"category": {"index": {"CP_MEUR": 0, "CLV20_MEUR": 1}}}}}).encode()
    assert check_bytes("nama_10_co3_p3.json", euro_only) is not None, "a reply in euro only must fail"
    assert check_bytes("nama_10_co3_p3.json", good[:-40]) is not None, "a cut JSON must fail"
    assert check_bytes("nama_10_co3_p3.json", json.dumps(
        {"error": {"status": 413}}).encode()) is not None, "a source error must fail"
    assert check_bytes("nama_10_co3_p3.json", json.dumps(
        {"value": {"0": 1}, "dimension": {}}).encode()) is not None, "a thin reply must fail"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.json"
        p.write_bytes(b"1")
        set_aside(p)
        assert (Path(tmp) / "a.json.bad_1").exists() and not p.exists()
    print("selftest ok: cut, error, thin and euro-only files fail; set_aside renames")


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
