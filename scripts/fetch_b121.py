"""B121: fetch the daily and weekly series the station reads, and time every request.

Run it on the machine that has the network. It is resumable: a series is fetched once,
checked, and written next to a completion marker; a later run skips it. Nothing is ever
deleted. A file that fails its check keeps its name with `.bad_<n>` appended and is left
on disk, so a truncated body is never read as data.

    python scripts/fetch_b121.py              # fetch the wanted series, then probe the unknown ids
    python scripts/fetch_b121.py --probe      # probe only, no fetching
    python scripts/fetch_b121.py --only DED3 SWPT

Per-request seconds go to `data/raw/b121/timings.json` (discipline 38: the cost of one
request is measured at every size that exists, never written into the code as a constant).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "b121"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
UA = "Mozilla/5.0 (research fetch; one request per series)"

# The series the station reads. The note is what the publisher calls it, kept here so a
# column is never read under a name this project invented for it (discipline 54).
WANTED = {
    "DED3": "3-Month Eurodollar Deposit Rate (London), H.15, ends 2016-10-11",
    "DFEDTAR": "Federal funds target rate, to 2008-12-15",
    "DFEDTARU": "Federal funds target range, upper limit, from 2008-12-16",
    "DFF": "Effective federal funds rate, daily",
    "SWPT": "Central bank liquidity swaps, H.4.1, weekly",
    "TERMAUC": "Term auction credit, monthly",
    "WCPFF": "Net portfolio holdings of Commercial Paper Funding Facility LLC, weekly",
    "COMPOUT": "Commercial paper outstanding, weekly",
    "ABCOMP": "Asset-backed commercial paper outstanding, weekly",
    "DCPF3M": "3-Month AA Financial Commercial Paper Rate",
    "DCPN3M": "3-Month AA Nonfinancial Commercial Paper Rate",
    "DTB3": "3-Month Treasury Bill Secondary Market Rate",
    "TEDRATE": "TED Spread, 3-month LIBOR minus 3-month T-bill, ends 2022-01-21",
    "WTERAUC": "Reserve Bank Credit: Term Auction Credit, weekly, discontinued",
    "WABCMMF": "Reserve Bank Credit: AMLF, weekly, 2008-09-24 to 2010-12-08",
    "H0RESPPALDDNWW": "Loans: Primary Dealer and Other Broker-Dealer Credit, Wednesday level",
    "WLCFLPCL": "Loans: Primary Credit, Wednesday level",
    "TERAUC1690": "Term auction credit maturing in 16 to 90 days, discontinued",
}

# Ids this project has not confirmed exist. A probe that 404s is a reading, not a failure:
# it says this id is not the publisher's name for that object, and the search goes on.
PROBE = [
    "H0RESPPALDFNWW",                              # AMLF, Wednesday level, the long H.4.1 name
    "RESPPALTXAWNWW",                              # Term auction credit, week average
    "WLCFLL",                                      # Loans, all liquidity and credit facilities
    "USD3MTD156N",                                 # removed from FRED in 2022, kept to record that
]
# The first probe list was a guess at the naming and every id in it answered 404. The ids above
# were looked up instead of guessed, and the ones that are wanted moved into WANTED.

# The Board's transaction-level disclosures for the crisis facilities (the pages under
# /newsevents/reform_*.htm link them). Each comes with a definitions file, and every column is
# read under the name that file gives it (discipline 54).
FEDFILES = {
    "taf.csv": "https://www.federalreserve.gov/newsevents/files/taf.csv",
    "taf_definitions.csv": "https://www.federalreserve.gov/newsevents/files/taf_definitions.csv",
    "amlf.csv": "https://www.federalreserve.gov/newsevents/files/amlf.csv",
    "amlf_definitions.csv": "https://www.federalreserve.gov/newsevents/files/amlf_definitions.csv",
    "cpff.csv": "https://www.federalreserve.gov/newsevents/files/cpff.csv",
    "cpff_definitions.csv": "https://www.federalreserve.gov/newsevents/files/cpff_definitions.csv",
    "cbls.csv": "https://www.federalreserve.gov/newsevents/files/cbls.csv",
    "cbls_definitions.csv": "https://www.federalreserve.gov/newsevents/files/cbls_definitions.csv",
}


def check_plain_csv(body: bytes) -> tuple[bool, str, dict]:
    """A disclosure file is data only if it is text, ends whole, and every row has the header's width."""
    if not body:
        return False, "empty body", {}
    text = body.decode("utf-8-sig", "replace")
    if "<html" in text[:400].lower():
        return False, "html, not csv", {}
    if not text.endswith(("\n", "\r")):
        return False, "does not end in a newline, so it may be cut short", {}
    import csv, io
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    width = len(rows[0])
    ragged = sum(1 for r in rows[1:] if len(r) != width)
    return True, "", {"rows": len(rows) - 1, "columns": rows[0], "ragged_rows": ragged}


PAGES = {
    "taf_results.html": "https://www.federalreserve.gov/monetarypolicy/taf.htm",
    "reform_taf.html": "https://www.federalreserve.gov/newsevents/reform_taf.htm",
    "reform_amlf.html": "https://www.federalreserve.gov/newsevents/reform_amlf.htm",
    "reform_cpff.html": "https://www.federalreserve.gov/newsevents/reform_cpff.htm",
    "reform_swaps.html": "https://www.federalreserve.gov/newsevents/reform_swaplines.htm",
}


def fetch(url: str, tries: int = 4) -> tuple[int, bytes, float]:
    """One request. Returns (status, body, seconds). A refusal is returned, not raised."""
    wait = 5.0
    for attempt in range(tries):
        started = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), time.time() - started
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == tries - 1:
                return e.code, b"", time.time() - started
        except Exception:
            if attempt == tries - 1:
                return 0, b"", time.time() - started
        time.sleep(wait)
        wait *= 2
    return 0, b"", 0.0


def check_csv(body: bytes) -> tuple[bool, str, dict]:
    """A body is data only if it parses whole. Anything else is named and refused."""
    if not body:
        return False, "empty body", {}
    text = body.decode("utf-8", "replace")
    if "<html" in text[:400].lower():
        return False, "html, not csv", {}
    if not text.endswith("\n"):
        return False, "does not end in a newline, so it may be cut short", {}
    lines = text.strip("\n").split("\n")
    header = lines[0].split(",")
    if len(header) < 2 or not header[0].lower().startswith(("date", "observation")):
        return False, f"unexpected header {lines[0][:40]!r}", {}
    dates = [ln.split(",")[0] for ln in lines[1:]]
    bad = [d for d in dates if len(d) != 10 or d[4] != "-" or d[7] != "-"]
    if bad:
        return False, f"{len(bad)} rows do not carry a date, first {bad[0][:20]!r}", {}
    return True, "", {
        "rows": len(dates),
        "first": dates[0],
        "last": dates[-1],
        "rows_2007_2009": sum(1 for d in dates if "2007" <= d[:4] <= "2009"),
        "columns": header[1:],
    }


def keep(path: Path, body: bytes) -> None:
    path.write_bytes(body)


def park(path: Path, body: bytes, why: str) -> Path:
    """A body that failed its check stays on disk under a name that says so."""
    n = 1
    while (bad := path.with_suffix(path.suffix + f".bad_{n}")).exists():
        n += 1
    bad.write_bytes(body)
    bad.with_suffix(bad.suffix + ".why").write_text(why + "\n", encoding="utf-8")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="probe the unknown ids only")
    ap.add_argument("--only", nargs="*", default=None, help="fetch these ids only")
    ap.add_argument("--pages", action="store_true", help="also save the facility pages")
    ap.add_argument("--press", action="store_true",
                    help="save every press release the saved TAF page lists, one file per release")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    timings_path = OUT / "timings.json"
    timings = json.loads(timings_path.read_text(encoding="utf-8")) if timings_path.exists() else []
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    todo = {} if args.probe else dict(WANTED)
    if args.only:
        todo = {k: WANTED.get(k, "not in the wanted list") for k in args.only}

    for sid, note in todo.items():
        csv_path, done_path = OUT / f"{sid}.csv", OUT / f"{sid}.done"
        if done_path.exists() and csv_path.exists():
            print(f"{sid:<12} already on disk, skipped")
            continue
        status, body, secs = fetch(FRED.format(sid))
        timings.append({"what": f"fred:{sid}", "status": status, "bytes": len(body),
                        "seconds": round(secs, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        if status != 200:
            print(f"{sid:<12} HTTP {status} after retries, nothing written")
            manifest[sid] = {"note": note, "status": status}
            continue
        ok, why, facts = check_csv(body)
        if not ok:
            bad = park(csv_path, body, why)
            print(f"{sid:<12} refused: {why}  ({bad.name})")
            manifest[sid] = {"note": note, "status": status, "refused": why}
            continue
        keep(csv_path, body)
        entry = {"note": note, "url": FRED.format(sid), "bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest(), "seconds": round(secs, 3), **facts}
        done_path.write_text(json.dumps(entry, indent=2, sort_keys=True), encoding="utf-8")
        manifest[sid] = entry
        print(f"{sid:<12} {facts['rows']:>6} rows  {facts['first']} to {facts['last']}  "
              f"2007-09: {facts['rows_2007_2009']:>4}  {len(body):>8}B  {secs:5.1f}s")

    if args.probe or not args.only:
        print("\nprobing ids this project has not confirmed:")
        for sid in PROBE:
            if sid in manifest and manifest[sid].get("probe_status") == 200:
                print(f"  {sid:<12} already answered 200, skipped")
                continue
            status, body, secs = fetch(FRED.format(sid), tries=1)
            timings.append({"what": f"probe:{sid}", "status": status, "bytes": len(body),
                            "seconds": round(secs, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            ok, why, facts = check_csv(body) if status == 200 else (False, f"HTTP {status}", {})
            manifest.setdefault(sid, {})["probe_status"] = status
            if ok:
                keep(OUT / f"{sid}.csv", body)
                (OUT / f"{sid}.done").write_text(json.dumps(facts, indent=2, sort_keys=True), encoding="utf-8")
                manifest[sid].update(facts)
                print(f"  {sid:<12} exists: {facts['rows']} rows {facts['first']} to {facts['last']}, "
                      f"2007-09: {facts['rows_2007_2009']}")
            else:
                print(f"  {sid:<12} no: {why}")
            time.sleep(2)

    if not args.probe and not args.only:
        print("\nthe Board's transaction-level files:")
        for name, url in FEDFILES.items():
            path, done = OUT / name, OUT / (name + ".done")
            if path.exists() and done.exists():
                print(f"  {name:<22} already on disk, skipped")
                continue
            status, body, secs = fetch(url, tries=3)
            timings.append({"what": f"fed:{name}", "status": status, "bytes": len(body),
                            "seconds": round(secs, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            if status != 200:
                print(f"  {name:<22} HTTP {status}, nothing written")
                manifest[name] = {"url": url, "status": status}
                continue
            ok, why, facts = check_plain_csv(body)
            if not ok:
                bad = park(path, body, why)
                print(f"  {name:<22} refused: {why} ({bad.name})")
                manifest[name] = {"url": url, "status": status, "refused": why}
                continue
            keep(path, body)
            entry = {"url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                     "seconds": round(secs, 3), **facts}
            done.write_text(json.dumps(entry, indent=2, sort_keys=True), encoding="utf-8")
            manifest[name] = entry
            print(f"  {name:<22} {facts['rows']:>6} rows  {len(facts['columns'])} columns  "
                  f"ragged {facts['ragged_rows']}  {len(body):>8}B  {secs:5.1f}s")

    if args.pages:
        print("\nfacility pages:")
        for name, url in PAGES.items():
            path = OUT / name
            if path.exists():
                print(f"  {name:<22} already on disk, skipped")
                continue
            status, body, secs = fetch(url, tries=2)
            timings.append({"what": f"page:{name}", "status": status, "bytes": len(body),
                            "seconds": round(secs, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            if status == 200 and body:
                keep(path, body)
                print(f"  {name:<22} {len(body):>8}B  {secs:5.1f}s")
            else:
                print(f"  {name:<22} HTTP {status}, nothing written")

    if args.press:
        import re
        page = (OUT / "taf_results.html").read_text(encoding="utf-8", errors="replace")
        start = page.find("Related Press Releases")
        block = page[start:page.find("More Information", start)]
        links = re.findall(r'href="(https://www\.federalreserve\.gov/newsevents/press/monetary/(\d{8}[a-z])\.htm)"', block)
        (OUT / "press").mkdir(exist_ok=True)
        print(f"\npress releases listed on the TAF page: {len(links)}")
        for url, stem in links:
            path = OUT / "press" / f"{stem}.html"
            if path.exists():
                print(f"  {stem} already on disk, skipped")
                continue
            status, body, secs = fetch(url, tries=2)
            timings.append({"what": f"press:{stem}", "status": status, "bytes": len(body),
                            "seconds": round(secs, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            if status == 200 and b"</html>" in body.lower():
                keep(path, body)
                print(f"  {stem} {len(body):>7}B {secs:4.1f}s")
            else:
                print(f"  {stem} HTTP {status} or cut short, nothing written")
            time.sleep(1)

    timings_path.write_text(json.dumps(timings, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    by_size = sorted((t for t in timings if t["status"] == 200), key=lambda t: t["bytes"])
    if by_size:
        print("\nwhat one request cost, smallest to largest (discipline 38):")
        for t in (by_size[0], by_size[len(by_size) // 2], by_size[-1]):
            print(f"  {t['bytes']:>9}B  {t['seconds']:>6.1f}s  {t['what']}")
    print(f"\nmanifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
