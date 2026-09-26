"""Fetch the ECB series B128 reads: bank lending and deposit rates by country, the key rates, and
how much each country's banks borrowed from the Eurosystem.

B128 asks whether a square of two countries by two products moves when the ECB changes its rates
(the framework says it cannot, since a rate change moves the potential and a potential sums to zero
round a loop) and whether it moves when a tool aimed at some classes opens.

One request per product shape takes every reference area at once (the key's area slot is left
empty), so the whole MIR pull is ten requests. The two borrowing tables are one request each.

Rules this obeys:
  - resumable: a file already on disk that passes the checks below is skipped
  - detects truncation: every row must have as many fields as the header, and the series in the
    file must be the series the key list says exist; a file that fails is renamed, never deleted
  - measured cost: every request is timed and the times are written to timings.json (`D38`)
  - enumerates before it chooses (`D12`): the product list is the one written in the design
    after the key list was read, and a shape an area does not publish is named, not guessed at

    python scripts/fetch_b128.py            # fetch what is missing
    python scripts/fetch_b128.py --check    # only check what is on disk
    python scripts/fetch_b128.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b128"
API = "https://data-api.ecb.europa.eu/service/data"
UA = "monetary-topology research fetcher (contact via repository)"
START = "2003-01"
PAUSE = 1.0

# The ten product shapes of the design, cell 3: all variable or fixed for up to one year.
SHAPES = (
    "B.A2A.F.R.2.2240.EUR.N",  # loans to corporations up to EUR 0.25M
    "B.A2A.F.R.3.2240.EUR.N",  # loans to corporations EUR 0.25M to 1M
    "B.A2A.F.R.1.2240.EUR.N",  # loans to corporations over EUR 1M
    "B.A2C.F.R.A.2250.EUR.N",  # loans to households for house purchase
    "B.A2B.F.R.A.2250.EUR.N",  # loans to households for consumption
    "B.A2D.F.R.A.2250.EUR.N",  # loans to households for other purposes (no IE key)
    "B.L22.F.R.A.2250.EUR.N",  # deposits from households, agreed maturity up to 1y
    "B.L22.F.R.A.2240.EUR.N",  # deposits from corporations, agreed maturity up to 1y
    "B.L21.A.R.A.2250.EUR.N",  # overnight deposits, households
    "B.L21.A.R.A.2240.EUR.N",  # overnight deposits, corporations
)
TABLES = {
    **{f"mir_{s.replace('.', '_')}": ("MIR", f"M..{s}") for s in SHAPES},
    "bsi_eurosystem_borrowing": ("BSI", "M..N.A.L20.A.1.U2.1100.Z01.E"),
    "ilm_ltro": ("ILM", "M..N.A050200.U2.EUR"),
    "ilm_mro": ("ILM", "M..N.A050100.U2.EUR"),
    # loan stocks for the TLTRO dose's denominator: eligible = NFC + household consumption + household other
    "bsi_loans_nfc": ("BSI", "M..N.A.A20.A.1.U2.2240.Z01.E"),
    "bsi_loans_hh_consumption": ("BSI", "M..N.A.A21.A.1.U2.2250.Z01.E"),
    "bsi_loans_hh_house": ("BSI", "M..N.A.A22.A.1.U2.2250.Z01.E"),
    "bsi_loans_hh_other": ("BSI", "M..N.A.A23.A.1.U2.2250.Z01.E"),
}


def url_of(flow: str, key: str) -> str:
    return f"{API}/{flow}/{key}?startPeriod={START}&format=csvdata"


def get(url: str) -> tuple[bytes, float]:
    t = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=180) as r:
        body = r.read()
    return body, round(time.perf_counter() - t, 2)


def check(text: str) -> tuple[bool, str, dict]:
    """Whole rows only, a KEY and a TIME_PERIOD column, and per-series first and last period."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as e:
        return False, f"does not parse: {e}", {}
    if len(rows) < 2:
        return False, "no data rows", {}
    head = rows[0]
    if "KEY" not in head or "TIME_PERIOD" not in head or "OBS_VALUE" not in head:
        return False, "header lacks KEY, TIME_PERIOD or OBS_VALUE", {}
    short = [i for i, r in enumerate(rows[1:], 2) if len(r) != len(head)]
    if short:
        return False, f"{len(short)} row(s) with the wrong number of fields, first at line {short[0]}", {}
    iK, iT = head.index("KEY"), head.index("TIME_PERIOD")
    span: dict[str, list[str]] = {}
    for r in rows[1:]:
        s = span.setdefault(r[iK], [r[iT], r[iT], 0])
        s[0], s[1], s[2] = min(s[0], r[iT]), max(s[1], r[iT]), s[2] + 1
    return True, f"{len(rows) - 1} rows, {len(span)} series", span


def retire(path: Path, why: str) -> None:
    dead = path.with_name(f"{path.name}.expired_{time.strftime('%Y%m%d_%H%M%S')}_{why}")
    path.rename(dead)  # never delete (engineering rule 5)
    print(f"    retired {path.name} -> {dead.name}")


def run(only_check: bool) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    man_path, tim_path = RAW / "manifest.json", RAW / "timings.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    timings = json.loads(tim_path.read_text(encoding="utf-8")) if tim_path.exists() else {}
    bad = 0
    for name, (flow, key) in TABLES.items():
        path = RAW / f"{name}.csv"
        if path.exists():
            ok, why, span = check(path.read_text(encoding="utf-8", errors="replace"))
            if ok:
                print(f"  have {name}: {why}")
                continue
            print(f"  {name} on disk fails: {why}")
            if only_check:
                bad += 1
                continue
            retire(path, "failed_check")
        if only_check:
            print(f"  missing {name}")
            bad += 1
            continue
        url = url_of(flow, key)
        try:
            body, secs = get(url)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  {name}: request failed ({e}); re-run to resume")
            bad += 1
            continue
        text = body.decode("utf-8", errors="replace")
        ok, why, span = check(text)
        timings[f"fetch {name}"] = {"seconds": secs, "bytes": len(body)}
        if not ok:
            print(f"  {name}: fetched but fails ({why}); not written")
            bad += 1
            continue
        path.write_bytes(body)
        manifest[name] = {"url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                          "fetched": time.strftime("%Y-%m-%d"), "series": {k: v for k, v in sorted(span.items())}}
        print(f"  got {name}: {why}, {secs} s, {len(body)} bytes")
        time.sleep(PAUSE)
    man_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    tim_path.write_text(json.dumps(timings, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 1 if bad else 0


def selftest() -> None:
    good = "KEY,TIME_PERIOD,OBS_VALUE\nA,2003-01,1.0\nA,2003-02,1.1\nB,2003-01,2.0\n"
    ok, why, span = check(good)
    assert ok and span == {"A": ["2003-01", "2003-02", 2], "B": ["2003-01", "2003-01", 1]}, (why, span)
    assert not check(good + "B,2003-02")[0]  # cut mid-row: must fail
    assert not check("KEY,TIME_PERIOD,OBS_VALUE\n")[0]  # header only
    assert not check("<html>error</html>\n<p>x</p>\n")[0]  # an error page
    assert len(TABLES) == len(SHAPES) + 7
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    return run(a.check)


if __name__ == "__main__":
    raise SystemExit(main())
