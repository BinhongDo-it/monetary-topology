"""Fetch the ECB HICP (ICP) series for the carrier and the same reference areas as the rates.

What this is for. The rate station reads a wedge between two positions in one unit of account,
and every instrument it has is a bank rate, so every one of them sits on the cross-border edge
through a bank's funding cost. That is why the lifting moved all six of them and why the
reading cannot separate the edge from a general normalisation: the family shares an assumption
and the assumption is false. The instrument that separates has to be a price that does not sit
on that edge at all, and a consumer price is one: it is set by sellers of goods and services,
not by a bank's cost of funds.

Two goods at two positions also give a square that owes nothing to banking: services are
mostly local, industrial goods are mostly traded, and a single scalar carried by each position
predicts that the gap between them is the same in every area.

Rules this obeys, the same ones as the rate fetcher:
  - enumerates before it chooses: the first run pulls the series keys that exist for each
    reference area and writes them to a cache, and nothing is downloaded until that list has
    been looked at
  - `--pick` writes the cross product of areas and shapes, keeping only what discovery found,
    and reports an area that has not been enumerated separately from a shape an area does not
    publish, because those are opposite instructions to whoever reads the output
  - genuinely resumable: a series already on disk that parses is skipped
  - never deletes: a bad or truncated file is renamed with a suffix, not removed
  - reports before it spends: times the first request and prints the measured per-series cost

Run from the repo root with the venv active:
    .\\.venv\\Scripts\\Activate.ps1
    python scripts/fetch_icp_cy.py --discover
    python scripts/fetch_icp_cy.py --pick
    python scripts/fetch_icp_cy.py --fetch
Re-run any step after a timeout; all three pick up where they stopped.
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
# "icp" alone is ambiguous in this repository: another station reads the World Bank
# International Comparison Program under that name. This one is the ECB consumer
# price dataflow, so the directory says hicp and the keys keep the dataflow id.
RAW = ROOT / "data" / "raw" / "hicp"
RAW.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/ICP"
# the same seven as the rate station, so the two readings sit on one control panel
AREAS = ("CY", "U2", "GR", "SI", "MT", "PT", "IE")
START, END = "2003-01", "2020-12"
TIMEOUT = 120
PAUSE = 1.0
UA = "monetary-topology research fetcher (contact via repository)"

# Candidate shapes. These are candidates rather than a choice: `--pick` keeps the ones
# discovery actually found and names the ones it did not, so the choosing still happens
# against the enumerated list.
#   .4.ANR  annual rate of change      .4.INX  index level
SHAPES = (
    "N.000000.4.ANR",    # all items
    "N.000000.4.INX",    # all items, index
    "N.XEF000.4.ANR",    # all items excluding energy and food
    "N.SERV00.4.ANR",    # services, mostly local
    "N.FOOD00.4.ANR",    # food
    # Two item codes here were guessed on the first run and do not exist: `IGD000` for
    # non-energy industrial goods and `NRG000` for energy. The enumerated list has `IGXE00`
    # and `NRGY00`. Nothing was lost, because the picking step reports an absent shape by
    # name rather than sending it, which is the whole point of choosing from the enumeration
    # instead of from a guess. The wrong codes are written down here rather than quietly
    # replaced, so the next person does not guess them again.
    "N.IGXE00.4.ANR",    # non-energy industrial goods, mostly traded
    "N.NRGY00.4.ANR",    # energy, the shock every area takes at once
    # An annual rate is a twelve-month difference, so it smears a step over twelve months.
    # The index carries the monthly resolution a dated reading needs, and a square of two
    # indices is free of their arbitrary base once it is read as a change.
    "N.SERV00.4.INX",    # services, index
    "N.IGXE00.4.INX",    # non-energy industrial goods, index
)


def get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def series_path(key):
    """The dataflow id is in the URL path already, and enumerated keys carry it too."""
    return key[4:] if key.upper().startswith("ICP.") else key


def parses(text):
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return False, 0
    return (len(rows) >= 2 and len(rows[0]) >= 3), max(0, len(rows) - 1)


def retire(path, why):
    """Never delete. Rename with a suffix and leave it in place."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dead = path.with_name(f"{path.name}.expired_{stamp}_{why}")
    path.rename(dead)
    print(f"    retired {path.name} -> {dead.name}")


def discover():
    out = RAW / "series_keys.json"
    found = {}
    if out.exists():
        found = json.loads(out.read_text(encoding="utf-8"))
        print(f"resuming: {len(found)} area(s) already enumerated in {out.name}")
    for area in AREAS:
        if area in found:
            print(f"  {area}: cached, {len(found[area])} keys")
            continue
        key = f"M.{area}" + "." * 4          # ICP has six dimensions
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
        ok, _n = parses(text)
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
    print("Look at that file, then run --pick.")


def pick(keys_file, picked):
    if not keys_file.exists():
        sys.exit("run --discover first; nothing is picked before the list is looked at")
    found = json.loads(keys_file.read_text(encoding="utf-8"))
    unlisted = [a for a in AREAS if a not in found]
    chosen, absent = [], []
    print(f"{'shape':20s}" + "".join(f"{a:>5s}" for a in AREAS))
    for shape in SHAPES:
        row = []
        for area in AREAS:
            key = f"ICP.M.{area}.{shape}"
            if area in unlisted:
                row.append("?")
            elif key in set(found.get(area, ())):
                chosen.append(key)
                row.append("yes")
            else:
                absent.append(key)
                row.append("-")
        print(f"{shape:20s}" + "".join(f"{c:>5s}" for c in row))
    if unlisted:
        print(f"\n'?' means the area has not been enumerated yet, which is not the same as the"
              f" shape being absent.\nrun --discover before --fetch: {', '.join(unlisted)}")
    old = [k.strip() for k in picked.read_text(encoding="utf-8").split("\n")
           if k.strip()] if picked.exists() else []
    kept = [k for k in old if k not in set(chosen)]
    if kept:
        print(f"\nkeeping {len(kept)} key(s) already picked that the cross product does not "
              f"produce")
        chosen += kept
    picked.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    on_disk = sum(1 for k in chosen if (RAW / (k.replace(".", "_") + ".csv")).exists())
    print(f"\nwrote {picked}: {len(chosen)} keys, {on_disk} already on disk, "
          f"{len(chosen) - on_disk} to fetch")
    if absent:
        print(f"{len(absent)} area-and-shape combinations do not exist and are not picked:")
        for k in absent:
            print(f"    {k}")


def fetch(keys_file, picked):
    if not keys_file.exists():
        sys.exit("run --discover first; nothing is downloaded before the list is looked at")
    chosen = [k.strip() for k in picked.read_text(encoding="utf-8").split("\n") if k.strip()] \
        if picked and picked.exists() else []
    if not chosen:
        sys.exit(f"run --pick first, or write the keys one per line into {picked}")
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
            print(f"[{i}/{len(chosen)}] {name}: {type(e).__name__} {e}, left for the next run")
            continue
        dt = time.time() - t0
        measured = dt if measured is None else measured
        ok, n = parses(text)
        if not ok:
            print(f"[{i}/{len(chosen)}] {name}: response did not parse, {len(text)} chars, "
                  f"not written")
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        manifest[name] = {"key": key, "url": url, "rows": n,
                          "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "seconds": round(dt, 2)}
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True),
                                 encoding="utf-8")
        print(f"[{i}/{len(chosen)}] {name}: {n} rows in {dt:.1f}s")
        time.sleep(PAUSE)
    missing = [k for k in chosen if not (RAW / (k.replace(".", "_") + ".csv")).exists()]
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
        print(f"{len(chosen)} series at that rate is about "
              f"{measured * len(chosen) / 60:.1f} minutes, and that number comes from a "
              f"measurement rather than a guess.")


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
