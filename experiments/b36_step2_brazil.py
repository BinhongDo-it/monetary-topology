"""B36-6: Brazilian beef exports to China, from Comex Stat.

The arm. B36-5 varies the destination and rules out a United States supply
contraction. This one varies the source country and rules out China cutting
every source at once. Neither reads on its own; the joint table of the two is
the identification, and all four of its cells were given a reading before any
number here was looked at.

    ratio >= 0.75   Brazil held up
    ratio <= 0.444  Brazil fell too
    between         this axis is undecided

Ratio means the 2025 quantity against the mean of 2021 to 2024, the same
window and the same band convention as the United States side.

The door. api-comexstat.mdic.gov.br, the trade ministry's own API. Free and
open at the time of writing; whether it opens is itself a reading about this
carrier, so the probe prints what it finds rather than assuming.

Two codelists are enumerated before anything is selected, never typed from
memory. A commodity code written from memory is what killed the first version
of B35: HS 0206 was assigned to bovine offal and turned out to be 99.8 percent
swine by value.

Run:
    python b36_step2_brazil.py --probe
    python b36_step2_brazil.py
"""

import argparse
import io
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE = "https://api-comexstat.mdic.gov.br"
HS_HEADS = ("0201", "0202")
BASE_YEARS = (2021, 2024)
TEST_YEAR = 2025
PASS_AT = 0.75
FAIL_AT = 0.444
UA = "monetary-topology research script"
BACKOFF = 12  # the door itself asks for ten seconds


def get(url, cache: Path, force=False):
    """GET with a cache that refuses to read a truncated file silently."""
    if cache.exists() and not force:
        raw = cache.read_text(encoding="utf-8")
        try:
            return json.loads(raw), True
        except json.JSONDecodeError:
            print("  cached %s does not parse, %d bytes. Refetching rather "
                  "than reading it." % (cache.name, len(raw)))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = BACKOFF * (2 ** attempt)
            print("  rate limited on a lookup table, waiting %d seconds" % wait)
            time.sleep(wait)
    if raw is None:
        raise SystemExit("the lookup table is still rate limited after four "
                         "attempts. Nothing selected, nothing judged.")
    obj = json.loads(raw)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(raw, encoding="utf-8")
    return obj, False


def post(body, cache: Path, force=False):
    if cache.exists() and not force:
        raw = cache.read_text(encoding="utf-8")
        try:
            return json.loads(raw), True
        except json.JSONDecodeError:
            print("  cached %s does not parse, %d bytes. Refetching."
                  % (cache.name, len(raw)))
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/general?language=en", data=data,
        headers={"Content-Type": "application/json", "User-Agent": UA})
    # The door rate-limits and says so in Portuguese: "tente novamente em 10
    # segundos". A 429 is a wait, not a refusal, so it is waited out rather
    # than recorded as the year being unavailable. Anything else is re-raised
    # and handled by the caller, which names the year and keeps the run.
    raw = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = BACKOFF * (2 ** attempt)
            print("    rate limited, waiting %d seconds (attempt %d of 4)"
                  % (wait, attempt + 1))
            time.sleep(wait)
    if raw is None:
        raise urllib.error.HTTPError(BASE, 429, "rate limited after four "
                                     "attempts", None, None)
    obj = json.loads(raw)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(raw, encoding="utf-8")
    return obj, False


def walk_rows(obj):
    """Find the list of records wherever the payload keeps it.

    The shape is not documented in the part of the spec I read, so it is
    discovered and printed rather than assumed. A wrapper that returns a
    subset without saying so is failure mode 117.
    """
    if isinstance(obj, list):
        return obj, "top level"
    if isinstance(obj, dict):
        for k in ("data", "list", "result", "results", "rows", "items"):
            v = obj.get(k)
            if isinstance(v, list):
                return v, k
            if isinstance(v, dict):
                for k2 in ("list", "data", "rows"):
                    if isinstance(v.get(k2), list):
                        return v[k2], "%s.%s" % (k, k2)
    return [], "not found"


def pick_countries(cache_dir, force=False):
    obj, cached = get(BASE + "/tables/countries?language=en",
                      cache_dir / "countries.json", force)
    rows, where = walk_rows(obj)
    print("countries table: %d rows, list found at %r, %s"
          % (len(rows), where, "from cache" if cached else "fetched"))
    if not rows:
        print("  top level keys: %s" % (list(obj)[:20] if isinstance(obj, dict)
                                        else type(obj).__name__))
        raise SystemExit("could not find the country list. Nothing selected.")
    print("  fields on one row: %s" % sorted(rows[0]))
    hits = []
    for r in rows:
        blob = " ".join(str(v).upper() for v in r.values())
        if any(k in blob for k in ("CHINA", "HONG KONG", "MACAU", "MACAO",
                                   "TAIWAN")):
            hits.append(r)
    print("\n  every row whose text mentions China or a neighbouring customs "
          "area, printed in full so the choice is visible:")
    for r in hits:
        print("    %s" % json.dumps(r, ensure_ascii=False))
    return rows, hits


def pick_ncm(cache_dir, force=False):
    obj, cached = get(BASE + "/tables/ncm?language=en",
                      cache_dir / "ncm.json", force)
    rows, where = walk_rows(obj)
    print("\nNCM table: %d rows, list found at %r, %s"
          % (len(rows), where, "from cache" if cached else "fetched"))
    if not rows:
        raise SystemExit("could not find the NCM list. Nothing selected.")
    print("  fields on one row: %s" % sorted(rows[0]))
    keys = [k for k in rows[0] if "ncm" in k.lower() or "co" == k.lower()[:2]]
    sel = []
    for r in rows:
        for k in keys:
            v = str(r.get(k) or "")
            if v[:4] in HS_HEADS and len(v) >= 6:
                sel.append(r)
                break
    print("\n  codes under %s, printed in full. This is the selection, and it "
          "is a codelist read, not a code typed from memory:" % (HS_HEADS,))
    for r in sel:
        print("    %s" % json.dumps(r, ensure_ascii=False)[:220])
    return rows, sel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true",
                    help="enumerate the codelists and pull one month only")
    ap.add_argument("--years", nargs=2, type=int, default=[2016, 2026])
    ap.add_argument("--country", default="CHINA",
                    help="destination name as it appears in the codelist")
    ap.add_argument("--force", action="store_true", help="ignore the cache")
    ap.add_argument("--pause", type=float, default=12.0,
                    help="seconds between year queries; the door rate-limits below about this")
    a = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    cache = root / "data" / "b36"
    out = root / "results"

    print("=" * 74)
    print("B36-6, Brazilian beef to %s. Door: %s" % (a.country, BASE))
    print("=" * 74)

    countries, hits = pick_countries(cache, a.force)
    # Match against the WHOLE codelist, not against the shortlist that is
    # printed above. The shortlist is only the rows naming China and its
    # neighbouring customs areas, and it exists so that choosing China is
    # visible. Searching it instead of the full table made --country unable to
    # reach any destination outside that family however it was spelled, while
    # the flag's own help text says "destination name as it appears in the
    # codelist". Gate first and filter second, which is the same shape as the
    # --only trap in run_all.py (legacy, and the trap outlives it).
    exact = [r for r in countries
             if any(str(v).strip().upper() == a.country.upper()
                    for v in r.values())]
    if len(exact) != 1:
        near = [r for r in countries
                if a.country.upper() in " ".join(str(v).upper()
                                                 for v in r.values())]
        print("\n  %d rows in the full codelist match %r exactly."
              % (len(exact), a.country))
        if near:
            print("  rows containing it, so the exact name can be read off:")
            for r in near[:15]:
                print("    %s" % json.dumps(r, ensure_ascii=False))
        raise SystemExit("\npass --country with one of the names above. The "
                         "codelist is cached at %s and can be read directly."
                         % (cache / "countries.json"))
    crow = exact[0]
    cid = None
    for k, v in crow.items():
        if isinstance(v, (int, str)) and str(v).isdigit() and 2 <= len(str(v)) <= 5:
            cid = int(v)
            break
    print("\n  chose: %s  ->  numeric code %s" % (json.dumps(crow, ensure_ascii=False), cid))
    if cid is None:
        raise SystemExit("no numeric code on that row. Nothing queried.")

    ncms, sel = pick_ncm(cache, a.force)
    codes = []
    for r in sel:
        for k, v in r.items():
            s = str(v)
            if s.isdigit() and s[:4] in HS_HEADS and len(s) >= 6:
                codes.append(s)
                break
    codes = sorted(set(codes))
    print("\n  %d codes selected: %s" % (len(codes), codes))
    if not codes:
        raise SystemExit("no NCM code selected. Nothing queried.")

    y0, y1 = a.years
    years = [y0] if a.probe else list(range(y0, y1 + 1))
    per_year = defaultdict(float)
    per_ncm = defaultdict(float)
    failed = []
    months_seen = defaultdict(set)
    shape_printed = False
    for y in years:
        body = {
            "flow": "export",
            "monthDetail": True,
            "period": {"from": "%d-01" % y,
                       "to": "%d-01" % y if a.probe else "%d-12" % y},
            "filters": [{"filter": "country", "values": [cid]},
                        {"filter": "ncm", "values": codes}],
            "details": ["ncm", "country"],
            "metrics": ["metricFOB", "metricKG"],
        }
        cp = cache / ("general_%s_%d%s.json"
                      % (a.country.lower().replace(" ", "_"), y,
                         "_probe" if a.probe else ""))
        try:
            obj, cached = post(body, cp, a.force)
        except urllib.error.HTTPError as e:
            print("  %d: HTTP %s. Body of the error, verbatim:" % (y, e.code))
            print("    %s" % e.read().decode("utf-8", "replace")[:800])
            failed.append(y)
            if not per_year:
                print("  The first year already fails, so this is the door and "
                      "not the year. Stopping. That is a reading about the "
                      "carrier and it is recorded as one.")
                return
            print("  Earlier years are already in hand, so this one year is "
                  "skipped and named at the end rather than losing the run.")
            continue
        rows, where = walk_rows(obj)
        if not shape_printed:
            print("\n" + "=" * 74)
            print("the response, printed before anything is added up")
            print("=" * 74)
            print("  top level: %s" % (list(obj) if isinstance(obj, dict)
                                       else type(obj).__name__))
            print("  rows at %r, %d of them" % (where, len(rows)))
            if rows:
                print("  one row, verbatim: %s"
                      % json.dumps(rows[0], ensure_ascii=False)[:500])
            shape_printed = True
        if a.probe:
            print("\nprobe done. Read the row above, then run without --probe.")
            return
        for r in rows:
            kgk = [k for k in r if k.lower() in ("metrickg", "kg", "metric_kg")]
            mk = [k for k in r if k.lower() in ("month", "comonth", "co_mes",
                                                "monthnumber")]
            if not kgk:
                print("  no kilogram field on a row. Fields: %s" % sorted(r))
                raise SystemExit("stopping rather than adding up the wrong "
                                 "column.")
            q = float(str(r[kgk[0]]).replace(",", "") or 0)
            per_year[y] += q
            if BASE_YEARS[0] <= y <= TEST_YEAR:
                per_ncm[(str(r.get("coNcm") or "?"), y)] += q
            if mk:
                months_seen[y].add(str(r[mk[0]]))
        print("  %d: %d rows, %.0f tonnes, %s"
              % (y, len(rows), per_year[y] / 1e3,
                 "cache" if cached else "fetched"))
        if not cached and y != years[-1]:
            time.sleep(a.pause)

    print("\n" + "=" * 74)
    print("Brazilian beef, NCM under %s, to %s, tonnes" % (HS_HEADS, a.country))
    print("=" * 74)
    for y in sorted(per_year):
        print("  %d  %14.0f   months seen %d" % (y, per_year[y] / 1e3,
                                                 len(months_seen[y]) or 0))

    if failed:
        print("\n  years that did not come back: %s. They are named rather "
              "than passed over." % failed)

    # A mix shift between bone-in and boneless moves no kilogram total, but it
    # is printed anyway: the object, not a count.
    codes_seen = sorted({c for c, _ in per_ncm})
    if codes_seen:
        print("\n" + "=" * 74)
        print("composition by NCM, share of the year in kilograms")
        print("=" * 74)
        yrs = [yy for yy in range(BASE_YEARS[0], TEST_YEAR + 1) if yy in per_year]
        print("  %-10s %s" % ("code", " ".join("%7d" % yy for yy in yrs)))
        for c in codes_seen:
            row = [per_ncm.get((c, yy), 0.0) / max(per_year[yy], 1.0) for yy in yrs]
            if max(row) < 0.005:
                continue
            print("  %-10s %s" % (c, " ".join("%6.1f%%" % (v * 100) for v in row)))

    have = [y for y in range(BASE_YEARS[0], BASE_YEARS[1] + 1) if y in per_year]
    if len(have) != 4 or TEST_YEAR not in per_year:
        print("\nthe base window or the test year is missing. Nothing judged.")
        return
    mean = sum(per_year[y] for y in have) / len(have)
    ratio = per_year[TEST_YEAR] / mean

    print("\n" + "=" * 74)
    print("B36-6, the number first")
    print("=" * 74)
    print("  window judged : %d against the mean of %d to %d"
          % (TEST_YEAR, *BASE_YEARS))
    print("  ratio         : %.4f" % ratio)
    print("  bands pinned before looking: held up >= %.3f, fell too <= %.3f"
          % (PASS_AT, FAIL_AT))
    if ratio >= PASS_AT:
        v = "HELD UP. China did not cut every source."
    elif ratio <= FAIL_AT:
        v = "FELL TOO. China cut sources other than the United States as well."
    else:
        v = "UNDECIDED on this axis, between the two bands."
    print("  verdict       : %s" % v)

    # The four year mean is not neutral on a trending series. The registered
    # band is not moved for that; a second number is printed instead, and it
    # carries no verdict. Registered in section 9.7 before this was run.
    print("\n  diagnostic, no verdict attached:")
    print("    the series is %s over the base window"
          % ("rising" if per_year[BASE_YEARS[1]] > per_year[BASE_YEARS[0]]
             else "flat or falling"))
    print("    %d against %d alone : %.4f"
          % (TEST_YEAR, BASE_YEARS[1],
             per_year[TEST_YEAR] / max(per_year[BASE_YEARS[1]], 1.0)))
    print("    If that number and the one above fall on opposite sides of the "
          "bands, the criterion still rules and this axis is written up as "
          "undecided, per section 9.7.")

    if 2026 in per_year and months_seen[2026]:
        m = len(months_seen[2026])
        print("\n  2026 so far: %d months, %.0f tonnes, annualised %.0f t. "
              "Not judged, the arm is registered on %d."
              % (m, per_year[2026] / 1e3, per_year[2026] * 12.0 / m / 1e3,
                 TEST_YEAR))

    print("\n  This is one axis. The joint reading needs B36-5 as well; the "
          "four cells are in the B36 design file, section one.")

    rec = {"stage": "B36", "criterion": "B36-6 Brazil to China",
           "door": BASE, "country": crow, "ncm_codes": codes,
           "window": {"base": list(BASE_YEARS), "test": TEST_YEAR},
           "bands": {"held_up_at": PASS_AT, "fell_too_at": FAIL_AT},
           "tonnes": {str(y): per_year[y] / 1e3 for y in sorted(per_year)},
           "ratio": ratio, "verdict": v,
           "ratio_vs_last_base_year": per_year[TEST_YEAR] / max(
               per_year[BASE_YEARS[1]], 1.0),
           "years_that_failed": failed,
           "months_seen": {str(y): len(months_seen[y]) for y in sorted(per_year)}}
    out.mkdir(parents=True, exist_ok=True)
    io.open(out / "b36_brazil_china.json", "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % (out / "b36_brazil_china.json"))


if __name__ == "__main__":
    main()
