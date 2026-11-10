"""B160: fetch the Reserve Bank of India press releases and circulars read by this station, as text.

Each source is fetched once, the body text is cut out of the page (between the size marker and the
archive month list), and the snapshot keeps the URL, the fetch time (UTC), the SHA-256 of the raw
response bytes and the SHA-256 of the body text. The raw page carries live parts (the site's
"last updated" line, current rates), so its hash differs between fetches; the body hash does not.

The scan index (titles of every press release from prid 38520 to 39259 and every circular from
Id 10670 to 10779, read 2026-10-29 to find which releases carry the exchange/deposit split) is
written next to it, so the record shows which pages were opened, including those with nothing.

usage:
  python -B experiments/b160_fetch.py            fetch and write data/raw/b160/b160_text_snapshot.json
  python -B experiments/b160_fetch.py --index DIR   also build b160_scan_index.json from saved scan pages
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b160"
SNAPSHOT = RAW / "b160_text_snapshot.json"
INDEX = RAW / "b160_scan_index.json"
SESSION = "B156_1029"

PR = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid={}"
CIRC = "https://rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id={}"

SOURCES = [
    ("pr38520", PR.format(38520), "2016-11-08 notice: exchange up to 4,000 per person; deposit without limit"),
    ("pr38560", PR.format(38560), "2016-11-11 statement: exchange window to 2016-12-30"),
    ("pr38568", PR.format(38568), "2016-11-12 statement: about 10 crore exchange transactions on 2016-11-10"),
    ("pr38643", PR.format(38643), "2016-11-21 activity at banks, 2016-11-10 to 11-18: exchange and deposits split"),
    ("pr38662", PR.format(38662), "2016-11-22 caution: exchange on behalf of others; deposit in unlimited amounts"),
    ("pr38695", PR.format(38695), "2016-11-25 exchange at Reserve Bank counters continues at the current limit"),
    ("pr38727", PR.format(38727), "2016-11-28 activity at banks, 2016-11-10 to 11-27: exchange and deposits split"),
    ("pr38839", PR.format(38839), "2016-12-08 activity at banks, 2016-11-10 to 12-07: issuance only"),
    ("pr38886", PR.format(38886), "2016-12-13 deputy governors' briefing: notes returned to RBI and chests"),
    ("pr38980", PR.format(38980), "2016-12-21 distribution of banknotes: issuance only"),
    ("pr39163", PR.format(39163), "2017-01-05 clarification: periodic SBN figures are chest accounting entries"),
    ("c10684", CIRC.format(10684), "DCM 1226, 2016-11-08: scheme, 4,000 exchange limit, deposit terms, reporting"),
    ("c10698", CIRC.format(10698), "DCM 1264, 2016-11-11: daily report rows 'Exchanged in Cash' and 'Deposits into Account'"),
    ("c10705", CIRC.format(10705), "DCM 1268, 2016-11-12: revised Annex 6A adds cash paid over counters and ATMs"),
    ("c10706", CIRC.format(10706), "DCM 1272, 2016-11-13: exchange limit 4,000 to 4,500, immediate effect; separate queues"),
    ("c10713", CIRC.format(10713), "DCM 1280, 2016-11-15: indelible ink SOP, metro cities first"),
    ("c10719", CIRC.format(10719), "DCM 1302, 2016-11-17: exchange limit 2,000 from 2016-11-18, once per person"),
    ("c10740", CIRC.format(10740), "DCM 1391, 2016-11-24: no over-the-counter exchange after midnight of 2016-11-24"),
]


def body_text(raw: str) -> str:
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", raw)
    s = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    m = re.search(r"\(\s*[\d.]+ kb \)", s)
    i = m.end() if m else 0
    j = s.find("2026 All Months", i)
    return s[i:j if j > 0 else len(s)].strip()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3)
    raise RuntimeError("unreachable")


def build_snapshot() -> dict:
    out = []
    for key, url, note in SOURCES:
        b = fetch(url)
        txt = body_text(b.decode("utf-8", "replace"))
        if len(txt) < 200 or "Date :" not in txt and "RBI/2016-17" not in txt:
            raise SystemExit(f"{key}: body text not found or truncated ({len(txt)} chars)")
        out.append({"key": key, "url": url, "note": note,
                    "fetched_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "raw_bytes": len(b), "raw_sha256": hashlib.sha256(b).hexdigest(),
                    "text_sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest(), "text": txt})
        print(f"{key}: {len(b)} bytes, body {len(txt)} chars")
    return {"station": "B160", "sources": out}


def build_index(scan_dir: Path) -> dict:
    rows = []
    for f in sorted(scan_dir.glob("*.html")):
        kind = "press_release" if f.name.startswith("p") else "circular"
        num = int(re.sub(r"\D", "", f.stem))
        txt = body_text(f.read_text(encoding="utf-8", errors="replace"))
        low = txt.lower()
        rows.append({"kind": kind, "id": num, "head": txt[:240],
                     "split_phrase": "exchange amounted to" in low and "deposits amounted to" in low,
                     "sbn_related": any(k in low for k in ("specified bank note", "legal tender", "sbn"))})
    rows.sort(key=lambda r: (r["kind"], r["id"]))
    return {"station": "B160", "read": "2026-10-29",
            "ranges": {"press_release": [38520, 39259], "circular": [10670, 10779]},
            "note": "Title and first words of every page in the two ranges, with two flags read from the full body: "
                    "split_phrase (both 'exchange amounted to' and 'deposits amounted to') and sbn_related. "
                    "Pages are not kept, only these heads.",
            "rows": rows}


def write(path: Path, text: str, label: str) -> None:
    sys.path.insert(0, str(ROOT.parent))
    from safe_write import create, rewrite
    if path.exists():
        rewrite(path, label, lambda _t: text, session=SESSION)
    else:
        create(path, label, text, session=SESSION)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, default=None)
    a = ap.parse_args(argv)
    RAW.mkdir(parents=True, exist_ok=True)
    snap = build_snapshot()
    write(SNAPSHOT, json.dumps(snap, indent=1, sort_keys=True, ensure_ascii=False) + "\n", "B160 text snapshot")
    if a.index:
        idx = build_index(a.index)
        write(INDEX, json.dumps(idx, indent=1, sort_keys=True, ensure_ascii=False) + "\n", "B160 scan index")
        print(f"index: {len(idx['rows'])} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
