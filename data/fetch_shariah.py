# -*- coding: utf-8 -*-
"""B19 fetcher: SEC Financial Statement Data Sets, the CIK-to-ticker map, stooq daily bars.

Each quarterly zip runs 110 to 125 MB, so two years is about 1 GB and the full
history from 2009Q2 is around 5 GB. Run this on the machine that has the network:
neither the bridged Linux VM nor the cloud container can reach sec.gov.

Resumable at file granularity: a quarter that is already on disk and verifies is
skipped. Downloaded data is treated as irreplaceable and nothing here deletes.
A file that fails verification is renamed with an `.expired_bad_*` suffix and left
in place rather than overwritten.

SEC requires a User-Agent carrying a contact address, and asks for rate limiting.

No `Accept-Encoding` header is sent. urllib does not transparently decompress, so
asking for gzip yields a gzip byte stream written straight to disk, which then
fails to parse as UTF-8 at position 1 with byte 0x8b. Zips were unaffected because
the server does not re-compress them; the JSON map was.

Two stages, run separately, because the second one's list is the first one's output:
    python -m data.fetch_shariah --stage sec --start 2023q1 --end 2024q4
    python -m data.fetch_shariah --stage prices

Two years first rather than the full history: the gate this feeds asks how many
cells clear their own requirement, and that is answerable on two years. Buying
more before knowing that is buying before measuring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

FSDS = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
STOOQ = "https://stooq.com/q/d/l/?s={sym}.us&i=d"
YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         "?range=5y&interval=1d")

# SEC requires a contact address in the User-Agent and that requirement is theirs.
UA = "monetary-topology research binhongd@outlook.com"
# Price hosts are ordinary web servers and refuse or throttle non-browser agents.
UA_WEB = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

RAW = Path("data") / "raw" / "shariah"
MANIFEST = RAW / "_manifest.json"
MIN_ZIP_BYTES = 5_000_000
# A bar file is judged by shape, not by size. A byte floor silently drops the
# shortest series, and the shortest series belong to names that listed late or
# stopped trading, which are exactly the ones a screen keyed on price declines
# needs most.
MIN_CSV_LINES = 2          # header plus at least one bar


def _get(url: str, timeout: int = 180, ua: str = UA, referer: str = "") -> bytes:
    h = {"User-Agent": ua}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _yahoo_csv(sym: str) -> bytes:
    """Return the same Date,Close shape the rest of this file expects."""
    blob = _get(YAHOO.format(sym=sym.upper()), timeout=30, ua=UA_WEB)
    d = json.loads(blob.decode("utf-8", "replace"))
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        return b""
    r0 = res[0]
    ts = r0.get("timestamp") or []
    q = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
    closes = q.get("close") or []
    lines = ["Date,Open,High,Low,Close,Volume"]
    for i, epoch in enumerate(ts):
        c = closes[i] if i < len(closes) else None
        if c is None:
            continue
        day = time.strftime("%Y-%m-%d", time.gmtime(epoch))
        lines.append(f"{day},{c},{c},{c},{c},0")
    if len(lines) == 1:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def _keep_aside(p: Path, why: str) -> Path:
    """Rename rather than overwrite or delete. Downloaded bytes are never discarded."""
    tag = why.split(":")[0].strip().replace(" ", "_")
    keep = Path(str(p) + f".expired_bad_{tag}")
    n = 1
    while keep.exists():
        keep = Path(str(p) + f".expired_bad_{tag}_{n}")
        n += 1
    p.rename(keep)
    return keep


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def _save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False),
                        encoding="utf-8", newline="\n")


def _verify_zip(p: Path) -> tuple[bool, str]:
    """A truncated or corrupt archive must be recognised, never read silently."""
    if not p.exists():
        return False, "missing"
    if p.stat().st_size < MIN_ZIP_BYTES:
        return False, f"too small: {p.stat().st_size}B"
    try:
        with zipfile.ZipFile(p) as z:
            bad = z.testzip()
            if bad is not None:
                return False, f"corrupt member: {bad}"
            need = {"num.txt", "sub.txt"}
            missing = need - set(z.namelist())
            if missing:
                return False, f"missing members: {sorted(missing)}"
    except zipfile.BadZipFile as e:
        return False, f"bad zip: {e}"
    return True, "ok"


def _fetch_ticker_map() -> None:
    dest = RAW / "company_tickers.json"
    if dest.exists():
        try:
            json.loads(dest.read_text(encoding="utf-8"))
            print(f"company_tickers.json  {dest.stat().st_size}B  (verified)")
            return
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            keep = _keep_aside(dest, type(e).__name__)
            print(f"company_tickers.json on disk does not parse -> kept as {keep.name}")
    blob = _get(TICKERS_URL, timeout=60)
    dest.write_bytes(blob)
    try:
        json.loads(dest.read_text(encoding="utf-8"))
    except Exception as e:
        keep = _keep_aside(dest, type(e).__name__)
        print(f"downloaded map still does not parse ({e}); kept as {keep.name}")
        sys.exit(3)
    print(f"company_tickers.json  {len(blob)}B  ok")
    time.sleep(1.0)


def quarters(start: str, end: str):
    y, q = int(start[:4]), int(start[5])
    ey, eq = int(end[:4]), int(end[5])
    while (y, q) <= (ey, eq):
        yield y, q
        q += 1
        if q > 4:
            y, q = y + 1, 1


def fetch_sec(start: str, end: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    _fetch_ticker_map()
    man = _load_manifest()
    for y, q in quarters(start, end):
        key = f"{y}q{q}"
        dest = RAW / f"{key}.zip"
        ok, why = _verify_zip(dest)
        if ok and man.get(key, {}).get("sha256"):
            print(f"{key}  SKIP (verified)")
            continue
        if dest.exists() and not ok:
            keep = _keep_aside(dest, why)
            print(f"{key}  invalid on disk ({why}) -> kept as {keep.name}")
        try:
            blob = _get(FSDS + f"{key}.zip")
        except urllib.error.HTTPError as e:
            print(f"{key}  HTTP {e.code}  (quarter may not be published yet)")
            continue
        except Exception as e:
            print(f"{key}  FAILED {type(e).__name__}: {e}")
            continue
        dest.write_bytes(blob)
        ok, why = _verify_zip(dest)
        if not ok:
            print(f"{key}  downloaded but INVALID: {why}")
            continue
        man[key] = {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
        _save_manifest(man)
        print(f"{key}  {len(blob)}B  ok")
        time.sleep(1.0)


def fetch_prices(tickers_file: str, source: str = "stooq") -> None:
    """Only the symbols the gate actually needs, not the whole market."""
    src_p = Path(tickers_file)
    if not src_p.exists():
        print(f"list not found: {src_p}\nrun: python experiments/b19_shariah_gate0.py --emit-tickers")
        sys.exit(2)
    syms = [s.strip() for s in src_p.read_text(encoding="utf-8").split() if s.strip()]
    out = RAW / "prices"
    out.mkdir(parents=True, exist_ok=True)
    man = _load_manifest()
    done = man.setdefault("_prices", {})
    bad = 0
    missing: list[str] = []
    print(f"{len(syms)} symbols, source={source}")
    for i, sym in enumerate(syms, 1):
        f = out / f"{sym}.csv"
        # Resume on what is on disk. The manifest is flushed every hundred symbols,
        # so gating on it as well makes an interrupted run re-fetch what it already has.
        if f.exists() and f.read_bytes().count(b"\n") >= MIN_CSV_LINES:
            done.setdefault(sym, f.stat().st_size)
            continue
        try:
            if source == "yahoo":
                blob = _yahoo_csv(sym)
            else:
                blob = _get(STOOQ.format(sym=sym.lower()), timeout=30,
                            ua=UA_WEB, referer="https://stooq.com/")
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                # The symbol has no series here. That is a gap in the sample, not a
                # sick source, and it must not stop the run.
                missing.append(sym)
                continue
            print(f"  {sym}  HTTP {e.code}")
            bad += 1
            if bad > 5:
                print(f"  six consecutive server refusals; stopping rather than "
                      f"walking the remaining list")
                break
            continue
        except Exception as e:
            print(f"  {sym}  FAILED {type(e).__name__}: {e}")
            bad += 1
            if bad > 5:
                print(f"  six consecutive transport failures; stopping")
                break
            continue
        if len(blob) == 0:
            missing.append(sym)          # empty series is a gap, not a refusal
            continue
        if b"Date" not in blob[:200] or blob.count(b"\n") < MIN_CSV_LINES:
            bad += 1
            # Print what came back. A count of failures says nothing about why.
            if bad <= 3:
                head = blob[:240].decode("utf-8", "replace").replace("\n", " | ")
                print(f"  {sym}  not a bar file ({len(blob)}B). Server returned:")
                print(f"      {head}")
            if bad >= 8 and len(done) == 0:
                print(f"\n  eight refusals and nothing on disk: this source is not serving us.")
                print(f"  try the other one:  --stage prices --source "
                      f"{'stooq' if source == 'yahoo' else 'yahoo'}")
                break
            continue
        bad = 0
        f.write_bytes(blob)
        done[sym] = len(blob)
        if i % 100 == 0:
            _save_manifest(man)
            print(f"  ... {i}/{len(syms)}")
        time.sleep(0.35)
    _save_manifest(man)
    if missing:
        # These are part of the sample gap and belong on record, not in the console
        # scrollback. Delisted names land here, and they are the ones that fell.
        mp = RAW / "symbols_without_series.txt"
        prior = set(mp.read_text(encoding="utf-8").split()) if mp.exists() else set()
        mp.write_text("\n".join(sorted(prior | set(missing))) + "\n",
                      encoding="utf-8", newline="\n")
        print(f"{len(missing)} symbols had no series -> {mp}")
    print(f"done: {len(done)} symbols on disk, {len(syms) - len(done)} still to go")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["sec", "prices"], required=True)
    ap.add_argument("--start", default="2023q1")
    ap.add_argument("--end", default="2024q4")
    ap.add_argument("--tickers", default=str(RAW / "tickers_needed.txt"))
    ap.add_argument("--source", choices=["stooq", "yahoo"], default="stooq")
    a = ap.parse_args()
    if a.stage == "sec":
        fetch_sec(a.start, a.end)
    else:
        fetch_prices(a.tickers, a.source)


if __name__ == "__main__":
    main()
