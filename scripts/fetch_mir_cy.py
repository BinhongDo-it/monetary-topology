"""Fetch the ECB MFI interest rate (MIR) series for Cyprus, Greece and the euro area.

What this is for. B97 asks whether a price that sits on one class of edge moves when that
class is restored and not when another is. Cyprus cut two classes, the island's own
bank-to-bank edge and the cross-border edge, and restored them eleven months apart
(2014-05-05 and 2014-06-01 against 2015-04-06). The MIR series is one currency priced at two
positions, so it is the price that sits on the cross-border edge.

Rules this obeys:
  - enumerates before it chooses (`D12`): the first run pulls the list of series keys that
    actually exist for each reference area and writes it to a cache, and nothing is downloaded
    until that list has been looked at
  - genuinely resumable: a series already on disk that parses and covers its window is skipped,
    so re-running after a timeout costs only what is missing
  - never deletes: a bad or stale file is renamed with a suffix, not removed
  - reports before it spends (`D38`): times the first request and prints the measured per-series
    cost, and refuses to quote a total without one
  - detects truncation: a CSV that does not parse, or that ends mid-row, is renamed and
    re-fetched rather than read

Run from the repo root with the venv active:
    .\\.venv\\Scripts\\Activate.ps1
    python scripts/fetch_mir_cy.py --discover
    python scripts/fetch_mir_cy.py --pick
    python scripts/fetch_mir_cy.py --fetch
Re-run any step after a timeout; all three pick up where they stopped. `--pick` writes the
cross product of the reference areas and the instrument shapes into the picked list, keeping
only the keys discovery actually found and naming the ones it did not.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mir"
RAW.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/MIR"
# CY is the carrier. U2 is the other position the same unit sits at, so it is the second
# leg of every wedge, not a control. The rest are controls, and they are here for one
# reason each: GR sat in the same periphery credit stress and never cut its domestic edge,
# though it cut its own external edge on 2015-06-29, which is inside a three-month window
# at the 2015-04 date; SI had a bank crisis and a bail-in at the end of 2013 and cut no
# edge at all; MT is the other small island banking system in the same currency; PT and IE
# are the other two programme countries of the period.
AREAS = ("CY", "U2", "GR", "SI", "MT", "PT", "IE")
START, END = "2003-01", "2020-12"   # opens before the carrier and closes after Greece's lift
TIMEOUT = 120
PAUSE = 1.0                          # be polite; the measured cost is printed either way
UA = "monetary-topology research fetcher (contact via repository)"


def get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def series_path(key):
    """The dataflow id is already in the URL path, and the enumerated keys carry it too.

    `--discover` returns keys of the form `MIR.M.CY.B...`, and pasting one of those after
    `/service/data/MIR/` asks the API for `MIR/MIR.M.CY...`, which is the 400 this hit on the
    first run of `--fetch`. The key that goes in the path is the one without the dataflow.
    """
    return key[4:] if key.upper().startswith("MIR.") else key


def parses(text):
    """A CSV that does not parse, or that has one row, is treated as truncated."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return False, 0
    return (len(rows) >= 2 and len(rows[0]) >= 3), max(0, len(rows) - 1)


def retire(path, why):
    """Never delete. Rename with a suffix and leave it in place (工程第 5 条)."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dead = path.with_name(f"{path.name}.expired_{stamp}_{why}")
    path.rename(dead)
    print(f"    retired {path.name} -> {dead.name}")


def discover():
    """`D12`: pull the series keys that exist, write them out, choose afterwards."""
    out = RAW / "series_keys.json"
    found = {}
    if out.exists():
        found = json.loads(out.read_text(encoding="utf-8"))
        print(f"resuming: {len(found)} area(s) already enumerated in {out.name}")
    for area in AREAS:
        if area in found:
            print(f"  {area}: cached, {len(found[area])} keys")
            continue
        # one wildcard per remaining dimension; the API reports the count if this is wrong
        key = f"M.{area}" + "." * 8
        url = f"{API}/{key}?detail=serieskeysonly&format=csvdata"
        t0 = time.time()
        try:
            text = get(url)
        except urllib.error.HTTPError as e:
            print(f"  {area}: HTTP {e.code}. The wildcard shape may be wrong for this dataflow.")
            print(f"    tried {url}")
            print(f"    server said: {e.read()[:400].decode('utf-8', errors='replace')}")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  {area}: {type(e).__name__} {e}, left for the next run")
            continue
        dt = time.time() - t0
        ok, n = parses(text)
        if not ok:
            print(f"  {area}: response did not parse as CSV, {len(text)} chars, not cached")
            continue
        rows = list(csv.DictReader(io.StringIO(text)))
        keys = sorted({r.get("KEY") or r.get("SERIES_KEY") or "" for r in rows} - {""})
        found[area] = keys
        print(f"  {area}: {len(keys)} series keys in {dt:.1f}s")
        out.write_text(json.dumps(found, indent=1, sort_keys=True), encoding="utf-8")
        time.sleep(PAUSE)
    print(f"\nwrote {out}")
    print("Look at that file and pick the series before running --fetch.")
    print("The ones B97 wants are deposits and loans to households and to non-financial")
    print("corporations, new business, annualised agreed rate, for CY and U2 on the same key")
    print("shape, so that the two are the same instrument at two positions.")


def fetch(keys_file, picked):
    """Download the chosen series, skipping what is already complete."""
    if not keys_file.exists():
        sys.exit("run --discover first; nothing is downloaded before the list is looked at")
    chosen = [k.strip() for k in picked.read_text(encoding="utf-8").split("\n") if k.strip()] \
        if picked and picked.exists() else []
    if not chosen:
        sys.exit(f"write the keys to fetch, one per line, into {picked}")
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}
    measured = None
    for i, key in enumerate(chosen, 1):
        name = key.replace(".", "_") + ".csv"
        path = RAW / name
        if path.exists():
            ok, n = parses(path.read_text(encoding="utf-8"))
            if ok:
                print(f"[{i}/{len(chosen)}] {name}: on disk, {n} rows, skipped")
                continue
            retire(path, "truncated")
        url = f"{API}/{series_path(key)}?startPeriod={START}&endPeriod={END}&format=csvdata"
        t0 = time.time()
        try:
            text = get(url)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", errors="replace").replace("\n", " ")
            print(f"[{i}/{len(chosen)}] {name}: HTTP {e.code}, left for the next run")
            print(f"    {url}")
            print(f"    server said: {body}")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # A read that times out is the ordinary case on a long run, and it has to cost the
            # same as an HTTP error: one series, left for the next run. Letting it propagate
            # ends the whole run, which is what happened on 2026-09-13 at series 24 of 24.
            print(f"[{i}/{len(chosen)}] {name}: {type(e).__name__} {e}, left for the next run")
            continue
        dt = time.time() - t0
        measured = dt if measured is None else measured
        ok, n = parses(text)
        if not ok:
            print(f"[{i}/{len(chosen)}] {name}: response did not parse, {len(text)} chars, not written")
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        manifest[name] = {"key": key, "url": url, "rows": n,
                          "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "seconds": round(dt, 2)}
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        print(f"[{i}/{len(chosen)}] {name}: {n} rows in {dt:.1f}s")
        time.sleep(PAUSE)
    missing = [k for k in chosen
               if not (RAW / (k.replace(".", "_") + ".csv")).exists()]
    if missing:
        print(f"\n{len(missing)} of {len(chosen)} series are still missing; re-run --fetch:")
        for k in missing:
            print(f"    {k}")
    else:
        print(f"\nall {len(chosen)} series are on disk")
    if measured is None:
        print("nothing was downloaded this run, so there is no measured cost to report")
    else:
        print(f"\nmeasured cost: {measured:.1f}s for the first series actually fetched.")
        print(f"{len(chosen)} series at that rate is about {measured * len(chosen) / 60:.1f} minutes,")
        print("and that number comes from a measurement rather than a guess (`D38`).")


# The instruments, each a key shape shared by every reference area. Deposits are the thing
# that could not move while the edge was cut; loans are the placebo, since a loan is not a
# deposit that wants to cross. The two volume shapes are there to read how much business each
# rate is an average over, which is what says whether a rate moved or its mix did.
SHAPES = (
    "B.L21.A.R.A.2250.EUR.N",    # overnight deposits, households
    "B.L21.A.R.A.2240.EUR.N",    # overnight deposits, non-financial corporations
    "B.L22.F.R.A.2250.EUR.N",    # deposits with agreed maturity up to 1y, households, rate
    "B.L22.F.R.A.2240.EUR.N",    # deposits with agreed maturity up to 1y, firms, rate
    "B.A2C.F.R.A.2250.EUR.N",    # loans for house purchase, variable or up to 1y fixation
    "B.A2A.F.R.A.2240.EUR.N",    # loans to firms, variable or up to 1y fixation
    "B.L22.A.B.A.2250.EUR.N",    # deposits with agreed maturity, households, volume
    "B.L22.A.B.A.2240.EUR.N",    # deposits with agreed maturity, firms, volume
)


def pick(keys_file, picked):
    """Write the picked list as areas by shapes, keeping only what discovery found.

    This is the choosing step `D12` asks for, and it chooses from the enumerated list rather
    than from a guess about what the API will accept. A shape an area does not publish is
    named here rather than left to come back as an HTTP error in the middle of a long run.
    """
    if not keys_file.exists():
        sys.exit("run --discover first; nothing is picked before the list is looked at")
    found = json.loads(keys_file.read_text(encoding="utf-8"))
    # An area that was never enumerated and an area that does not publish a shape look the
    # same in the output of this loop, and they are opposite instructions to whoever reads it:
    # the first says run --discover again, the second says stop looking (`D37`, `D45`).
    unlisted = [a for a in AREAS if a not in found]
    chosen, absent = [], []
    print(f"{'shape':28s}" + "".join(f"{a:>5s}" for a in AREAS))
    for shape in SHAPES:
        row = []
        for area in AREAS:
            key = f"MIR.M.{area}.{shape}"
            if area in unlisted:
                row.append("?")
            elif key in set(found.get(area, ())):
                chosen.append(key)
                row.append("yes")
            else:
                absent.append(key)
                row.append("-")
        print(f"{shape:28s}" + "".join(f"{c:>5s}" for c in row))
    if unlisted:
        print(f"\n'?' means the area has not been enumerated yet, which is not the same as the"
              f" shape being absent.\nrun --discover before --fetch: {', '.join(unlisted)}")
    old = [k.strip() for k in picked.read_text(encoding="utf-8").split("\n")
           if k.strip()] if picked.exists() else []
    kept = [k for k in old if k not in set(chosen)]
    if kept:
        # never drop a key that was already picked: it may already be on disk and read by a
        # station. Anything the cross product does not regenerate is appended back.
        print(f"\nkeeping {len(kept)} key(s) already in the picked list that the cross "
              f"product does not produce")
        chosen += kept
    picked.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    on_disk = sum(1 for k in chosen if (RAW / (k.replace(".", "_") + ".csv")).exists())
    print(f"\nwrote {picked}: {len(chosen)} keys, {on_disk} already on disk, "
          f"{len(chosen) - on_disk} to fetch")
    if absent:
        print(f"{len(absent)} area-and-shape combinations do not exist and are not picked:")
        for k in absent:
            print(f"    {k}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--pick", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--picked", default=str(RAW / "picked_keys.txt"))
    a = ap.parse_args()
    if a.discover:
        discover()
    elif a.pick:
        pick(RAW / "series_keys.json", Path(a.picked))
    elif a.fetch:
        fetch(RAW / "series_keys.json", Path(a.picked))
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
