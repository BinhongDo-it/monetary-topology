"""Fetch NYISO locational prices with their published components.

What this is for. The station reads a field whose answer is already published: the tariff
(Section 17.1.1) defines the price at a bus as

    gamma_i = lambda_R + gamma_i^L + gamma_i^C

where lambda_R is the system marginal price at the reference bus and is one number for the
whole network in a given interval. So the residual

    r(i, t) = LBMP(i, t) - losses(i, t) - congestion(i, t)

has to be the same at every node in an interval, which makes it a constant field, which makes
every cycle sum of it exactly zero. That is a zero calibration on real data, and what it
adds to the ones this repository already has is that the true value is fixed by an algebraic
identity inside the publisher's own pricing rule rather than by an argument of ours about what
must cancel, and that the network it runs on is three orders of magnitude larger. It is not the
first such calibration here and must not be described as one.

Rules this obeys:
  - probes before it chooses: `--probe` fetches one day under each candidate URL shape and
    prints what came back, with the headers, before anything is downloaded in bulk
  - reports before it spends: the probe prints measured seconds and bytes per file, and the
    bulk step refuses to quote a total without one
  - genuinely resumable: a file already on disk that parses is skipped
  - never deletes: a truncated file is renamed with a suffix, not removed
  - the sign convention is not guessed here; the station identifies it by which choice makes
    the residual constant across nodes

Run from the repo root with the venv active:
    .\\.venv\\Scripts\\Activate.ps1
    python scripts/fetch_nyiso_lbmp.py --probe
    python scripts/fetch_nyiso_lbmp.py --fetch
"""
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
RAW = ROOT / "data" / "raw" / "nyiso"
RAW.mkdir(parents=True, exist_ok=True)

BASE = "http://mis.nyiso.com/public/csv"
# Candidate shapes, probed rather than assumed. The zone file is the small one and the
# generator file is the wide one; both carry the same three columns.
SHAPES = (
    ("damlbmp_zone", "damlbmp/{d}damlbmp_zone.csv"),
    ("damlbmp_gen", "damlbmp/{d}damlbmp_gen.csv"),
    ("rtlbmp_zone", "realtime/{d}realtime_zone.csv"),
    ("rtlbmp_gen", "realtime/{d}realtime_gen.csv"),
)
#: The monthly archives, dated to the first of the month. A publisher that keeps individual
#: days for a recent window and older ones only inside these is the ordinary arrangement, and
#: it is the first thing to check when a dated file comes back missing.
ZIP_SHAPES = (
    ("damlbmp_zone_zip", "damlbmp/{m}01damlbmp_zone_csv.zip"),
    ("damlbmp_gen_zip", "damlbmp/{m}01damlbmp_gen_csv.zip"),
    ("rtlbmp_zone_zip", "realtime/{m}01realtime_zone_csv.zip"),
)
PROBE_DAY = "20150415"          # a quiet spring weekday
PROBE_RECENT = "20250415"       # and a recent one, to tell retention from a wrong path
# One month is enough for the calibration: the reading is an identity that has to hold in
# every interval, so more intervals buy repetitions of a test that cannot be noisy.
DAYS = [f"2015{m:02d}{d:02d}" for m in (4,) for d in range(1, 31)]
TIMEOUT = 120
PAUSE = 1.0
UA = "monetary-topology research fetcher (contact via repository)"


def get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parses(text):
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return False, 0, []
    ok = len(rows) >= 2 and len(rows[0]) >= 3
    return ok, max(0, len(rows) - 1), (rows[0] if rows else [])


def retire(path, why):
    """Never delete. Rename with a suffix and leave it in place."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path.rename(path.with_name(f"{path.name}.expired_{stamp}_{why}"))


def attempt(name, url):
    """One request, and **the outcome is recorded whether or not it worked**.

    The first version of this probe wrote only the shapes that succeeded, so when every one of
    them failed it left an empty file and nothing on disk said why. A probe's failures are the
    thing it is for: they say whether the host is unreachable, whether the path is wrong, or
    whether the file simply is not kept for that date, and those are three different next steps.
    """
    row = {"url": url}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            row["status"] = r.status
            row["content_type"] = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode("utf-8", errors="replace").replace("\n", " ")
        row.update({"outcome": "http_error", "status": e.code, "body": body,
                    "seconds": round(time.time() - t0, 2)})
        print(f"  {name:18s} HTTP {e.code}   {url}")
        return row
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        row.update({"outcome": type(e).__name__, "error": str(e)[:200],
                    "seconds": round(time.time() - t0, 2)})
        print(f"  {name:18s} {type(e).__name__}: {str(e)[:90]}")
        print(f"  {'':18s} {url}")
        return row
    row["seconds"] = round(time.time() - t0, 2)
    row["bytes"] = len(raw)
    if raw[:2] == b"PK":
        row["outcome"] = "zip"
        (RAW / f"probe_{name}.zip").write_bytes(raw)
        print(f"  {name:18s} zip, {len(raw) / 1024:.0f} KiB, {row['seconds']}s   {url}")
        return row
    text = raw.decode("utf-8", errors="replace")
    ok, n, header = parses(text)
    row.update({"outcome": "csv" if ok else "did_not_parse", "rows": n, "header": header})
    # saved either way: a body that is not CSV is usually an error page, and reading it is
    # how the next run stops guessing
    (RAW / f"probe_{name}.txt").write_text(text[:200_000], encoding="utf-8", newline="\n")
    print(f"  {name:18s} {'csv' if ok else 'not csv'}, {n} rows, "
          f"{len(raw) / 1024:.0f} KiB, {row['seconds']}s   {url}")
    if ok:
        print(f"  {'':18s} header: {header}")
    return row


def probe():
    """Every candidate shape, on an old date and a recent one, with all outcomes recorded."""
    out = {}
    print(f"daily files, old date {PROBE_DAY}:")
    for name, shape in SHAPES:
        out[f"{name}@{PROBE_DAY}"] = attempt(name, f"{BASE}/{shape.format(d=PROBE_DAY)}")
        time.sleep(PAUSE)
    print(f"\ndaily files, recent date {PROBE_RECENT}. **A recent day that works while an old "
          f"one does not is retention, not a wrong path**:")
    for name, shape in SHAPES[:2]:
        out[f"{name}@{PROBE_RECENT}"] = attempt(name, f"{BASE}/{shape.format(d=PROBE_RECENT)}")
        time.sleep(PAUSE)
    print(f"\nmonthly archives for {PROBE_DAY[:6]}:")
    for name, shape in ZIP_SHAPES:
        out[name] = attempt(name, f"{BASE}/{shape.format(m=PROBE_DAY[:6])}")
        time.sleep(PAUSE)
    print("\nreachability control, the host's own index. **This separates 'the site is not "
          "reachable from here' from 'that path is wrong'**:")
    out["host_root"] = attempt("host_root", "http://mis.nyiso.com/public/P-24Alist.htm")
    (RAW / "probe.json").write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    good = [k for k, v in out.items() if v.get("outcome") in ("csv", "zip")]
    print(f"\nwrote {RAW / 'probe.json'} with every attempt, {len(good)} of {len(out)} usable.")
    if not good:
        print("Nothing came back usable. The file above now says which of the three it was: "
              "host unreachable, path wrong, or that date not kept.")
        return
    per = max(out[k].get("seconds", 0.0) for k in good)
    print(f"measured cost: {per:.1f}s for the slowest usable shape, so {len(DAYS)} days is "
          f"about {per * len(DAYS) / 60:.1f} minutes, from a measurement rather than a guess.")


def fetch(shape_name):
    shape = dict(SHAPES)[shape_name]
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {}
    measured = None
    for i, d in enumerate(DAYS, 1):
        name = f"{d}_{shape_name}.csv"
        path = RAW / name
        if path.exists():
            ok, n, _h = parses(path.read_text(encoding="utf-8"))
            if ok:
                print(f"[{i}/{len(DAYS)}] {name}: on disk, {n} rows, skipped")
                continue
            retire(path, "truncated")
        url = f"{BASE}/{shape.format(d=d)}"
        t0 = time.time()
        try:
            text = get(url)
        except urllib.error.HTTPError as e:
            print(f"[{i}/{len(DAYS)}] {name}: HTTP {e.code}, left for the next run")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"[{i}/{len(DAYS)}] {name}: {type(e).__name__} {e}, left for the next run")
            continue
        dt = time.time() - t0
        measured = dt if measured is None else measured
        ok, n, _h = parses(text)
        if not ok:
            print(f"[{i}/{len(DAYS)}] {name}: did not parse, {len(text)} chars, not written")
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        manifest[name] = {"url": url, "rows": n,
                          "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "seconds": round(dt, 2)}
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True),
                                 encoding="utf-8")
        print(f"[{i}/{len(DAYS)}] {name}: {n} rows in {dt:.1f}s")
        time.sleep(PAUSE)
    missing = [d for d in DAYS if not (RAW / f"{d}_{shape_name}.csv").exists()]
    print(f"\n{len(DAYS) - len(missing)} of {len(DAYS)} days on disk"
          + (f"; re-run --fetch for the rest" if missing else ""))
    if measured is not None:
        print(f"measured cost: {measured:.1f}s for the first file actually fetched.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--shape", default="damlbmp_gen",
                    help="which shape to fetch in bulk, after the probe has been looked at")
    a = ap.parse_args()
    if a.probe:
        probe()
    elif a.fetch:
        fetch(a.shape)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
