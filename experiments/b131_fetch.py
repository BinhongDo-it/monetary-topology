"""Fetch the B131 sources: interest before and after FISIM allocation by sector, deposit and
loan stocks by sector, the ESA 2010 chapter that defines FISIM, and one ECB box.

Ten files, each named in FILES with the URL it came from.

  - nasa_10_nf_tr_d41.json: Eurostat annual non-financial sector accounts, items D41
    (interest) and D41G (total interest before FISIM allocation), sectors S14_S15 and S11,
    paid and received, current prices, million euro, every country and year the source has.
    FISIM by user sector is read off the difference of the two items (ESA 2010 14.11).
  - nasa_10_f_bs_dep_loans.json: Eurostat annual financial balance sheets, items F22
    (transferable deposits), F29 (other deposits) and F4 (loans), sectors S14_S15 and S11,
    assets and liabilities, non-consolidated, million euro.
  - nasa_10_nf_tr_b6g_p3.json: household disposable income (B6G) and final consumption
    expenditure (P3), S14_S15, current prices, million euro; the denominators for the ECB box.
  - nasa_10_nf_tr_s1.json: total economy (S1) GDP (B1GQ), current prices, million euro. The
    request also names exports (P62F) and imports (P72F) of FISIM; the source lists both items
    and carries no value for either under S1.
  - nasa_10_nf_tr_fisim_trade.json: exports (P62F) and imports (P72F) of FISIM, rest of the
    world (S2), paid and received, current prices, million euro. Exports sit under S2 paid,
    imports under S2 received.
  - mir_outstanding.csv: ECB MIR, outstanding amounts, monthly, every reference area: loans (A20) and
    deposits with agreed maturity (L22), all maturities, to non-financial corporations (2240) and
    households (2250), percent per annum. Overnight deposit rates are the same series for new
    business and outstanding amounts and are on disk from B128.
  - mir_notice.csv: ECB MIR, deposits redeemable at notice from households, all notice periods;
    like overnight deposits, the same series serves new business and outstanding amounts.
  - bsi_stocks.csv: ECB BSI, month-end stocks of overnight (L21), agreed-maturity (L22) and
    notice (L23) deposits and of loans (A20), households (2250) and corporations (2240), euro
    area counterparts, EUR millions. Twelve month-ends averaged per year stand in for the
    four-quarter average stock of ESA 14.07, and weight the deposit rates by type.
  - esa2010_ch14.html: ESA 2010 chapter 14, the FISIM rules as the source prints them.
  - ecb_eb_2023_8_box5.html: ECB Economic Bulletin 8/2023, box "A primer on measuring
    household income", read as literature.

Rules this obeys:
  - resumable: a file on disk that passes its check is skipped
  - never deletes: a file that fails its check is renamed .bad_<n> and fetched again
  - checks: HTTP 200; a JSON file parses, carries "value" and "dimension", no "error", at
    least MIN_VALUES values, and at least MIN_ITEM values for each item named there (a reply
    can list an item in its dimensions and carry nothing for it); an HTML file is over 20 KB
    and holds its marker phrase
  - measured cost only (`D38`): each request prints its seconds and bytes

Run from the repo root:
    python experiments/b131_fetch.py --fetch
    python experiments/b131_fetch.py --check
    python experiments/b131_fetch.py --selftest
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
RAW = ROOT / "data" / "raw" / "b131"
MANIFEST = RAW / "manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 300
PAUSE = 3.0
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

FILES = {
    "nasa_10_nf_tr_d41.json": API + "nasa_10_nf_tr?na_item=D41&na_item=D41G&sector=S14_S15"
                              "&sector=S11&unit=CP_MEUR&format=JSON&lang=EN",
    "nasa_10_f_bs_dep_loans.json": API + "nasa_10_f_bs?na_item=F22&na_item=F29&na_item=F4"
                                   "&sector=S14_S15&sector=S11&co_nco=NCO&unit=MIO_EUR"
                                   "&format=JSON&lang=EN",
    "nasa_10_nf_tr_b6g_p3.json": API + "nasa_10_nf_tr?na_item=B6G&na_item=P3&sector=S14_S15"
                                 "&unit=CP_MEUR&format=JSON&lang=EN",
    "nasa_10_nf_tr_s1.json": API + "nasa_10_nf_tr?na_item=B1GQ&na_item=P62F&na_item=P72F"
                             "&sector=S1&unit=CP_MEUR&format=JSON&lang=EN",
    "nasa_10_nf_tr_fisim_trade.json": API + "nasa_10_nf_tr?na_item=P62F&na_item=P72F"
                                      "&sector=S2&unit=CP_MEUR&format=JSON&lang=EN",
    "mir_outstanding.csv": "https://data-api.ecb.europa.eu/service/data/MIR/"
                           "M..B.A20+L22.A.R.A.2240+2250.EUR.O?format=csvdata",
    "mir_notice.csv": "https://data-api.ecb.europa.eu/service/data/MIR/"
                      "M..B.L23.A.R.A.2250.EUR.N?format=csvdata",
    "bsi_stocks.csv": "https://data-api.ecb.europa.eu/service/data/BSI/"
                      "M..N.A.L21+L22+L23+A20.A.1.U2.2240+2250.Z01.E?format=csvdata",
    "esa2010_ch14.html": "https://ec.europa.eu/eurostat/esa2010/chapter/view/14/",
    "ecb_eb_2023_8_box5.html": "https://www.ecb.europa.eu/press/economic-bulletin/focus/2024/html/"
                               "ecb.ebbox202308_05~68f551afd4.en.html",
}
MIN_VALUES = {"nasa_10_nf_tr_d41.json": 5000, "nasa_10_f_bs_dep_loans.json": 5000,
              "nasa_10_nf_tr_b6g_p3.json": 1000, "nasa_10_nf_tr_s1.json": 1500,
              "nasa_10_nf_tr_fisim_trade.json": 400}
# values per na_item, for the files whose items are read one by one
MIN_ITEM = {"nasa_10_nf_tr_s1.json": {"B1GQ": 1500},
            "nasa_10_nf_tr_fisim_trade.json": {"P62F": 200, "P72F": 200}}
MIN_ROWS = {"mir_outstanding.csv": 5000, "mir_notice.csv": 2000, "bsi_stocks.csv": 20000}
MARKER = {"esa2010_ch14.html": "reference rate", "ecb_eb_2023_8_box5.html": "FISIM"}


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
        counts = item_counts(d)
        thin = {it: counts.get(it, 0) for it, least in MIN_ITEM.get(name, {}).items() if counts.get(it, 0) < least}
        if thin:
            return "items with too few values: " + ", ".join(f"{it} {n}" for it, n in thin.items())
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


def item_counts(d: dict) -> dict:
    """Values per na_item in a JSON-stat reply, read off the flat index."""
    ids, size = d.get("id", []), d.get("size", [])
    if "na_item" not in ids:
        return {}
    k = ids.index("na_item")
    stride = 1
    for s in size[k + 1:]:
        stride *= s
    code = {i: c for c, i in d["dimension"]["na_item"]["category"]["index"].items()}
    out = {}
    for flat in d["value"]:
        it = code[(int(flat) // stride) % size[k]]
        out[it] = out.get(it, 0) + 1
    return out


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
    good = json.dumps({"value": {str(i): 1 for i in range(6000)}, "dimension": {}}).encode()
    assert check_bytes("nasa_10_nf_tr_d41.json", good) is None
    assert check_bytes("nasa_10_nf_tr_d41.json", good[:-40]) is not None, "a cut JSON must fail"
    assert check_bytes("nasa_10_nf_tr_d41.json", json.dumps(
        {"error": {"status": 413}}).encode()) is not None, "a source error must fail"
    assert check_bytes("nasa_10_nf_tr_d41.json", json.dumps(
        {"value": {"0": 1}, "dimension": {}}).encode()) is not None, "a thin reply must fail"
    # a reply that lists an item and carries nothing for it: GDP alone must not pass for GDP and trade
    def stat(per_item):
        items = list(per_item)
        n = max(per_item.values()) or 1
        value = {str(i * n + j): 1.0 for i, it in enumerate(items) for j in range(per_item[it])}
        return json.dumps({"id": ["na_item", "time"], "size": [len(items), n], "value": value,
                           "dimension": {"na_item": {"category": {"index": {it: i for i, it in enumerate(items)}}},
                                         "time": {"category": {"index": {str(j): j for j in range(n)}}}}}).encode()
    assert item_counts(json.loads(stat({"B1GQ": 3, "P62F": 0, "P72F": 2}))) == {"B1GQ": 3, "P72F": 2}
    assert check_bytes("nasa_10_nf_tr_s1.json", stat({"B1GQ": 2000, "P62F": 0, "P72F": 0})) is None
    assert check_bytes("nasa_10_nf_tr_s1.json", stat({"B1GQ": 1400, "P62F": 300, "P72F": 300})) is not None, \
        "GDP too thin must fail even when the file has enough values in all"
    assert check_bytes("nasa_10_nf_tr_fisim_trade.json", stat({"P62F": 600, "P72F": 0})) is not None, \
        "a trade file with no imports must fail"
    assert check_bytes("nasa_10_nf_tr_fisim_trade.json", stat({"P62F": 600, "P72F": 600})) is None
    csv = "\n".join(["KEY,OBS_VALUE"] + ["k,1"] * 6000).encode()
    assert check_bytes("mir_outstanding.csv", csv) is None
    assert check_bytes("mir_outstanding.csv", b"KEY,OBS_VALUE\nk,1\n") is not None, "thin CSV must fail"
    assert check_bytes("mir_outstanding.csv", b"<html>" + b"x" * 90_000) is not None, "HTML must fail"
    page = ("x" * 30_000 + " the reference rate ").encode()
    assert check_bytes("esa2010_ch14.html", page) is None
    assert check_bytes("esa2010_ch14.html", b"x" * 30_000) is not None, "no marker must fail"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.json"
        p.write_bytes(b"1")
        set_aside(p)
        assert (Path(tmp) / "a.json.bad_1").exists() and not p.exists()
    print("selftest ok: cut, error, thin, item-empty and marker-less files fail; set_aside renames")


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
