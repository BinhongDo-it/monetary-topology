"""B41 and B35 shared gate probe against USDA AMS Market News (MARS API).

Four modes, each small enough to read the output of before running the next.
Nothing here pulls a full history: `--full` refuses until the fifth gate item
is on disk, because that is what the station's design requires.

    python experiments/b41_ams_probe.py --fields 2851
    python experiments/b41_ams_probe.py --structure
    python experiments/b41_ams_probe.py --earliest 2851
    python experiments/b41_ams_probe.py --full          # refuses, on purpose

Key resolution, in order: MARS_API_KEY in the environment, then
`../.mars_api_key` beside the repository, then `data/.mars_api_key`.
The key is never written into this file and never printed.

Every response is cached under data/b41/cache/ and validated before it is
trusted. A cache file that fails validation is renamed aside rather than
removed, and refetched. Nothing on disk is ever deleted.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

BASE = "https://marsapi.ams.usda.gov/services/v1.2"
REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b41" / "cache"
OUT = REPO / "data" / "b41"

# Report ids taken from the AMS state grain report index. Weekly ones are
# marked so a daily-only run can skip them without editing the table.
REPORTS = {
    2960: ("AR", "Arkansas Daily Grain Bids", "daily"),
    3146: ("CA", "California Weekly Grain Bids", "weekly"),
    2912: ("CO", "Colorado Daily Grain Bids", "daily"),
    3192: ("IL", "Illinois Daily Grain Bids", "daily"),
    3463: ("IN", "Indiana Weekly Grain Bids", "weekly"),
    2850: ("IA", "Iowa Daily Grain Bids", "daily"),
    3043: ("IA-MN", "Iowa - Southern Minnesota Barge Terminal", "daily"),
    2886: ("KS", "Kansas Daily Grain Bids", "daily"),
    2892: ("KY", "Kentucky Daily Grain Bids", "daily"),
    3147: ("LA-TX", "Louisiana and Texas Gulf Export Bids and Basis", "daily"),
    2714: ("MD", "Maryland Weekly Grain Bids", "weekly"),
    3046: ("MN", "Minneapolis Daily Grain", "daily"),
    3045: ("MN", "Minneapolis Daily Basis Report", "daily"),
    3049: ("MN", "Southern Minnesota Daily Grain Bids", "daily"),
    2928: ("MS", "Mississippi Daily Grain Bids", "daily"),
    3223: ("MO", "Kansas City Daily Grain Bids", "daily"),
    2932: ("MO", "Missouri Daily Grain Bids", "daily"),
    2771: ("MT", "Montana Daily Elevator Grain Bids", "daily"),
    3225: ("NE", "Nebraska Daily Grain Bids", "daily"),
    3156: ("NC", "North Carolina Daily Grain Bids", "daily"),
    3878: ("ND", "North Dakota Daily Grain Bids", "daily"),
    2851: ("OH", "Ohio Daily Grain Bids", "daily"),
    3100: ("OK", "Oklahoma Daily Grain Bids", "daily"),
    3148: ("OR", "Portland Daily Grain Bids", "daily"),
    3091: ("PA", "Pennsylvania Weekly Grain Bids", "weekly"),
    2787: ("SC", "South Carolina Daily Grain Bids", "daily"),
    3186: ("SD", "South Dakota Daily Grain Bids", "daily"),
    3088: ("TN", "Tennessee Daily Grain Bids", "daily"),
    2711: ("TX", "Texas Daily Grain Bids", "daily"),
    3167: ("VA", "Virginia Daily Grain Bids", "daily"),
    3239: ("WY", "Wyoming Daily Grain Bids", "daily"),
}


# ---------------------------------------------------------------- key & http

def api_key() -> str:
    env = os.environ.get("MARS_API_KEY")
    if env:
        return env.strip()
    for candidate in (REPO.parent / ".mars_api_key", REPO / "data" / ".mars_api_key"):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    sys.exit(
        "No API key. Set MARS_API_KEY, or put the key in a file named "
        ".mars_api_key beside the repository. The key never goes in a tracked file."
    )


def slug(text: str) -> str:
    keep = "".join(c if c.isalnum() else "_" for c in text)
    return keep[:120]


def get(path: str, query: str | None, key: str, pause: float = 0.4,
        all_sections: bool = False) -> dict | list:
    """One GET, cached on disk, validated before it is trusted.

    A bare reports/<id> call returns the Report Header section only, which is
    report-level metadata and carries no bids. The bids live in the Report
    Detail section, reached either by putting the section in the path or by
    asking for allSections."""
    CACHE.mkdir(parents=True, exist_ok=True)
    tag = (query or "latest") + ("__all" if all_sections else "")
    name = f"{slug(path)}__{slug(tag)}.json"
    hit = CACHE / name
    if hit.exists():
        try:
            payload = json.loads(hit.read_text(encoding="utf-8"))
            if payload not in ({}, []) or query:
                return payload
        except (json.JSONDecodeError, UnicodeDecodeError):
            aside = hit.with_suffix(f".corrupt.{int(time.time())}.json")
            hit.rename(aside)          # renamed, never removed
            print(f"    cache entry did not parse, set aside as {aside.name}")

    url = f"{BASE}/{urllib.parse.quote(path, safe='/')}"
    parts = []
    if query:
        parts.append("q=" + urllib.parse.quote(query, safe="=:;/,"))
    if all_sections:
        parts.append("allSections=true")
    if parts:
        url += "?" + "&".join(parts)
    token = base64.b64encode(f"{key}:".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})

    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            payload = json.loads(raw)          # truncation shows up here
            tmp = hit.with_suffix(".part")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, hit)
            time.sleep(pause)
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                sys.exit(f"HTTP {exc.code}: the key was rejected. Check it and retry.")
            if exc.code == 404:
                return {}
            last = exc
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url} failed four times: {last}")


def rows_of(payload) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for k in ("results", "data", "report"):
            v = payload.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        return [payload]
    return []


# ---------------------------------------------------------------- mode: fields

def mode_fields(report_id: int, key: str, section: str | None = None,
                day: str | None = None) -> None:
    """Print the key set before selecting anything from it."""
    path = f"reports/{report_id}" + (f"/{section}" if section else "")
    payload = get(path, f"report_begin_date={day}" if day else None, key)
    rows = rows_of(payload)
    if isinstance(payload, dict):
        print(f"  sections available: {payload.get('reportSections')}")
        print(f"  stats: {payload.get('stats')}")
    print(f"report {report_id}  {REPORTS.get(report_id, ('?', '?', '?'))[1]}")
    print(f"  top-level type: {type(payload).__name__}")
    if isinstance(payload, dict):
        print(f"  top-level keys: {sorted(payload)[:40]}")
    print(f"  rows: {len(rows)}")
    if not rows:
        print("  no rows returned")
        return
    seen = defaultdict(int)
    for r in rows:
        for k in r:
            seen[k] += 1
    print(f"  fields present, with the count of rows carrying each:")
    for k in sorted(seen):
        example = next((r[k] for r in rows if r.get(k) not in (None, "")), "")
        print(f"    {k:<34} {seen[k]:>5}   e.g. {str(example)[:56]}")
    print("\n  first row verbatim:")
    print("   ", json.dumps(rows[0], ensure_ascii=False)[:1400])


# ------------------------------------------------------------- mode: structure

CITYISH = ("city", "location", "market", "office", "region", "area")


def guess(fields: set[str], *wants: str) -> str | None:
    for w in wants:
        for f in fields:
            if f.lower() == w:
                return f
    for w in wants:
        for f in sorted(fields):
            if w in f.lower():
                return f
    return None


def mode_structure(key: str, daily_only: bool, limit: int | None) -> None:
    """One latest-report pull per state; tabulate cells; find same-city pairs."""
    picked = [i for i, m in REPORTS.items() if not daily_only or m[2] == "daily"]
    if limit:
        picked = picked[:limit]
    table, failures = [], []
    for rid in picked:
        st, name, freq = REPORTS[rid]
        try:
            head = rows_of(get(f"reports/{rid}", None, key))
            days = sorted({r.get("report_date") for r in head if r.get("report_date")},
                          key=lambda s: (s[6:], s[:2], s[3:5]))
            if not days:
                failures.append((rid, "header carried no report_date"))
                print(f"{rid:>5} {st:<6} header has no dates")
                continue
            latest = days[-1]
            rows = rows_of(get(f"reports/{rid}/Report Detail",
                               f"report_begin_date={latest}", key))
        except RuntimeError as exc:
            failures.append((rid, str(exc)))
            print(f"{rid:>5} {st:<6} FETCH FAILED")
            continue
        if not rows:
            failures.append((rid, "no rows"))
            print(f"{rid:>5} {st:<6} no rows")
            continue
        fields = set().union(*(set(r) for r in rows))
        # Names below were read off a Report Detail response on 2026-09-02
        # rather than guessed. guess() stays as the fallback so that a report
        # with a different shape degrades instead of throwing.
        f_loc = "trade_loc" if "trade_loc" in fields else guess(
            fields, "trade_loc", "market_location_name", "region", "location")
        f_fac = "delivery_point" if "delivery_point" in fields else guess(
            fields, "delivery_point", "facility")
        f_com = "commodity" if "commodity" in fields else guess(fields, "commodity")
        f_cls = "class" if "class" in fields else guess(fields, "class", "grade")
        f_del = ("delivery_start" if "delivery_start" in fields
                 else guess(fields, "delivery_period", "delivery"))
        f_mon = ("basis Min Futures Month" if "basis Min Futures Month" in fields
                 else guess(fields, "futures_month", "basis_month", "month"))
        # A position label of the form "Toledo - On River" carries its city in
        # front of the dash. That is where arm B lives, so the city is taken
        # from the label rather than from market_location_city, which is the
        # office city and identical for every row.
        cells = set()
        for r in rows:
            loc = str(r.get(f_loc) or "")
            city = loc.split(" - ")[0].strip() if " - " in loc else loc
            cells.add((
                loc, city,
                f'{r.get(f_com) or ""}|{r.get(f_cls) or ""}',
                str(r.get(f_del) or ""), str(r.get(f_mon) or ""),
                str(r.get(f_fac) or ""),
            ))
        locs = {c[0] for c in cells if c[0]}
        coms = {c[2] for c in cells}
        by_city = defaultdict(set)
        for loc, city, *_ in cells:
            if city:
                by_city[city].add(loc)
        multi = {c: v for c, v in by_city.items() if len(v) > 1}
        table.append(dict(report=rid, state=st, rows=len(rows), locations=len(locs),
                          commodities=len(coms), cells=len(cells),
                          same_city_pairs={c: sorted(v) for c, v in multi.items()},
                          field_map=dict(location=f_loc, facility=f_fac,
                                         commodity=f_com, klass=f_cls,
                                         delivery=f_del, month=f_mon)))
        print(f"{rid:>5} {st:<6} rows={len(rows):>5} loc={len(locs):>3} "
              f"com={len(coms):>3} cells={len(cells):>4} "
              f"same-city={len(multi)}")

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "structure.json"
    dest.write_text(json.dumps(
        dict(generated_for="B41 arm-B enumeration", reports=table, failures=failures),
        ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {dest.relative_to(REPO)}")
    print("\nsame-city position pairs, which is what arm B needs:")
    any_pair = False
    for row in table:
        for city, locs in sorted(row["same_city_pairs"].items()):
            any_pair = True
            print(f"  {row['state']:<6} {city:<26} {locs}")
    if not any_pair:
        print("  none found under the guessed city field; check field_map in the json")


# ------------------------------------------------------------- mode: earliest

def has_rows(rid: int, y0: int, y1: int, key: str) -> int:
    q = f"report_begin_date={date(y0,1,1):%m/%d/%Y}:{date(y1,12,31):%m/%d/%Y}"
    try:
        return len(rows_of(get(f"reports/{rid}", q, key)))
    except RuntimeError:
        return -1


def mode_earliest(rid: int, key: str) -> None:
    """Walk back by decade, then bisect by year. Both ends of a range are
    required by the API, so there is no open-ended query to ask instead."""
    this_year = date.today().year
    print(f"report {rid}  {REPORTS.get(rid, ('?', '?', '?'))[1]}")
    lo = None
    for y in range(this_year, 1979, -5):
        n = has_rows(rid, max(y - 4, 1980), y, key)
        print(f"  {max(y-4,1980)}-{y}: {n:>6} rows")
        if n <= 0:
            break
        lo = max(y - 4, 1980)
    if lo is None:
        print("  no window returned rows; the report id or the date filter is wrong")
        return
    hi = lo + 4
    while lo < hi:
        mid = (lo + hi) // 2
        n = has_rows(rid, mid, mid, key)
        print(f"  {mid}: {n:>6} rows")
        if n > 0:
            hi = mid
        else:
            lo = mid + 1
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "earliest.json"
    known = {}
    if dest.exists():
        known = json.loads(dest.read_text(encoding="utf-8"))
    known[str(rid)] = dict(earliest_year=lo, checked_on=str(date.today()),
                           report=REPORTS.get(rid, ("?", "?", "?"))[1])
    dest.write_text(json.dumps(known, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    print(f"\n  earliest year with rows: {lo}")
    print(f"  wrote {dest.relative_to(REPO)}")


# --------------------------------------------------------------- mode: history

def mode_history(rid: int, key: str, y0: int, y1: int) -> None:
    """Pull one report's Report Detail in yearly chunks.

    A year of one state is a few thousand rows, well inside the 100,000 cap, so
    the chunking is for resumability rather than for the cap: a run that stops
    halfway leaves whole years on disk and the next run skips them.

    The gate has to be closed before this is allowed to run, which is what the
    earliest.json check is doing here."""
    gate = OUT / "earliest.json"
    if not gate.exists():
        sys.exit(f"Refusing to pull: {gate.relative_to(REPO)} is not on disk. "
                 f"Run --earliest first.")
    st, name, _ = REPORTS.get(rid, ("?", "?", "?"))
    print(f"report {rid}  {st}  {name}")
    total = 0
    for y in range(y0, y1 + 1):
        q = f"report_begin_date=01/01/{y}:12/31/{y}"
        rows = rows_of(get(f"reports/{rid}/Report Detail", q, key))
        days = len({r.get("report_date") for r in rows if r.get("report_date")})
        total += len(rows)
        flag = ""
        payload_cap = 100000
        if len(rows) >= payload_cap:
            flag = "  AT THE ROW CAP, this year needs splitting"
        print(f"  {y}: {len(rows):>7} rows over {days:>4} days{flag}")
    print(f"  {total} rows in all for {rid}")


# ------------------------------------------------------------------ mode: full

def mode_full() -> None:
    dest = OUT / "earliest.json"
    if not dest.exists():
        sys.exit(
            "Refusing to pull. The fifth gate item, the start of history, is not on "
            f"disk yet. Run --earliest for the carrier reports first; it writes "
            f"{dest.relative_to(REPO)}."
        )
    print("Gate item five is on disk:")
    print(dest.read_text(encoding="utf-8"))
    print("The bulk pull itself is deliberately not implemented in this file. "
          "Write it once the carrier and the date span are settled, so that the "
          "span is a decision on record rather than a default.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fields", type=int, metavar="ID")
    ap.add_argument("--section", default=None,
                    help='report section, e.g. "Report Detail"')
    ap.add_argument("--day", default=None, metavar="MM/DD/YYYY")
    ap.add_argument("--structure", action="store_true")
    ap.add_argument("--earliest", type=int, metavar="ID")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--history", type=int, metavar="ID",
                    help="pull one report's Report Detail, year by year")
    ap.add_argument("--years", type=int, nargs=2, default=[2020, 2026],
                    metavar=("FROM", "TO"))
    ap.add_argument("--daily-only", action="store_true", default=True)
    ap.add_argument("--limit", type=int, default=None,
                    help="only the first N reports, for a small auditable slice")
    a = ap.parse_args()
    if a.full:
        return mode_full()
    key = api_key()
    if a.fields:
        return mode_fields(a.fields, key, a.section, a.day)
    if a.history:
        return mode_history(a.history, key, a.years[0], a.years[1])
    if a.earliest:
        return mode_earliest(a.earliest, key)
    if a.structure:
        return mode_structure(key, a.daily_only, a.limit)
    ap.print_help()


if __name__ == "__main__":
    main()
