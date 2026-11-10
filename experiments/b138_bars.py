"""B138 block two, second part: the dates and daily bars the market reading needs.

Two inputs for each company. The day its reform statement was first published, from the
statement listing on cninfo (`b138_probe.listing`, pages cached under `data/raw/b138/cninfo/`):
the tradable price before the reform is the last close before that day. The bars around the
reform, from ``STATEMENT_BEFORE`` calendar days before the statement to ``AFTER`` days after the
record day, into B110's per-stock cache (`data/raw/b110/daily_baostock/stock/`), unadjusted
(`adjustflag=3`): the day the consideration lists carries no ex-rights reference price, so the
raw close is the price. The Shanghai composite (sh.000001) and the Shenzhen composite (sz.399106)
over the whole span go to `data/raw/b138/index_<code>.json`, fetched directly: B110's cache is
keyed by stock code and would read 000001 as a Shenzhen stock.

Writes nothing under ``results/``; writes ``data/raw/b138/bars_manifest.json`` and
``data/raw/b138/statement_dates.json``.

    python experiments/b138_bars.py --plan     # the statement listing (network), then ranges and hours
    python experiments/b138_bars.py            # fetch; Ctrl+C stops after the request in hand
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import b110_fetch as B  # noqa: E402
import b138_parse as Q  # noqa: E402
import b138_probe as PR  # noqa: E402

STATEMENT_BEFORE = 45
AFTER = 45
NO_STATEMENT_BEFORE = 150
INDEXES = ("sh.000001", "sz.399106")
INDEX_SPAN = ("2005-01-01", "2015-12-31")
MANIFEST = PR.RAW / "bars_manifest.json"
DATES = PR.RAW / "statement_dates.json"


COVERAGE = PR.RAW / "statement_listing_coverage.json"


def statement_dates() -> dict[str, str]:
    """Code -> the first day any reform statement (full text, summary or revision) was published.

    The listing's coverage (each window's total, rows, distinct ids, repeated pages) is written beside the
    dates; a window that is not whole is printed."""
    coverage: list = []
    rows = PR.listing(PR.KEYWORDS[1], coverage)
    problems = PR.coverage_problems(coverage)
    PR.atomic_write_bytes(COVERAGE, json.dumps(
        {"keyword": PR.KEYWORDS[1], "windows": coverage, "rows_distinct": len(rows), "problems": problems},
        ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))
    print(f"statement listing: {len(coverage)} windows, {len(rows)} distinct announcements; "
          f"{len(problems)} coverage problems" + ("".join("\n  " + p for p in problems[:12])), flush=True)
    out: dict[str, str] = {}
    for r in rows:
        if "说明书" not in PR.clean_title(r.get("announcementTitle")):
            continue
        code, day = str(r["secCode"]), PR.day_of(r["announcementTime"])
        if code not in out or day < out[code]:
            out[code] = day
    PR.atomic_write_bytes(DATES, json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True).encode("utf-8"))
    return out


def shift(day: str, days: int) -> str:
    return (dt.date.fromisoformat(day) + dt.timedelta(days=days)).isoformat()


def windows(stmt: dict[str, str]) -> tuple[dict, dict]:
    out, notes = {}, {"no_statement": [], "no_record_day": []}
    for p in Q.parse_all():
        code = p["code"]
        end_day = p.get("record_day") or p["day"]
        if not p.get("record_day"):
            notes["no_record_day"].append(code)
        if code in stmt and stmt[code] <= end_day:
            beg = shift(stmt[code], -STATEMENT_BEFORE)
        else:
            notes["no_statement"].append(code)
            beg = shift(end_day, -NO_STATEMENT_BEFORE)
        out[code] = [(beg, shift(end_day, AFTER))]
    return out, notes


def index_path(code: str) -> Path:
    return PR.RAW / f"index_{code.replace('.', '')}.json"


def fetch_indexes() -> None:
    fields = "date,code,open,high,low,close,preclose,volume,amount,pctChg"
    for code in INDEXES:
        path = index_path(code)
        if path.exists():
            print(f"  {code}: on disk", flush=True)
            continue
        bs = B.P.bs_session()
        rs = bs.query_history_k_data_plus(code, fields, start_date=INDEX_SPAN[0], end_date=INDEX_SPAN[1],
                                          frequency="d", adjustflag="3")
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        if rs.error_code != "0" or not rows:
            print(f"  {code}: baostock {rs.error_code} {rs.error_msg}, {len(rows)} rows; not written", flush=True)
            continue
        PR.atomic_write_bytes(path, json.dumps({"source": "baostock", "code": code, "fields": fields.split(","),
                                                "rows": rows}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        print(f"  {code}: {len(rows)} rows, {rows[0][0]}..{rows[-1][0]}", flush=True)


def write_manifest(obj: dict) -> None:
    PR.atomic_write_bytes(MANIFEST, json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True,
                                               default=str).encode("utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--bs-delay", type=float, default=0.0)
    a = ap.parse_args(argv)
    stmt = statement_dates()
    wins, notes = windows(stmt)
    print(f"statement dates for {len(stmt)} companies; windows for {len(wins)}; without a statement date "
          f"{len(notes['no_statement'])}; without a record day {len(notes['no_record_day'])}", flush=True)
    last_final = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    B.install_log_lock()
    if a.plan:
        basic, note = B.load_basic(network=False, refresh=False, delay=0.0, day=last_final)
    else:
        print(f"socket guard {B.install_socket_guard()}", flush=True)
        basic, note = B.load_basic(network=True, refresh=False, delay=a.bs_delay, day=last_final)
    need, clipped = {}, []
    for code, ws in wins.items():
        listed = basic.get(code) if basic else None
        for b, e in ws:
            c = B.clip(b, e, listed) if listed else (b, e)
            if c is None:
                clipped.append(code)
                continue
            need[code] = B.add_interval(need.get(code, []), *c)
    jobs = B.bar_jobs(need)
    rows = sum(B.trading_rows(b, e) for _, b, e in jobs)
    spr, how = B.seconds_per_row()
    hours = None if spr is None else rows * spr / 3600
    print(f"security list: {note}; ranges to ask {len(jobs)}, about {rows:,.0f} rows; "
          + (f"about {hours:.2f} h ({how})" if hours is not None else "hours not reported: seconds per row not measured"),
          flush=True)
    manifest = {"statement_before_days": STATEMENT_BEFORE, "after_days": AFTER,
                "no_statement_before_days": NO_STATEMENT_BEFORE, "companies": len(wins),
                "statement_dates": len(stmt), "notes": notes, "not_listed_in_window": clipped,
                "ranges": len(jobs), "rows_estimated": round(rows), "seconds_per_row": spr,
                "state": "planned" if a.plan else "running"}
    if a.plan:
        write_manifest(manifest)
        return 0
    fetch_indexes()
    stop = threading.Event()
    result: dict = {}

    def do(job):
        code, b, e = job
        how_, detail, _ = B.fetch_gap(code, b, e, a.bs_delay, listed=code in basic)
        return how_, detail

    write_manifest(manifest)
    try:
        counts, named, ended = B.run_jobs("bars", jobs, do, stop, B.BREAKER, B.COOLDOWN["bars"],
                                          B.MAX_COOLDOWNS, 25, relogin=B.P.bs_logout, live=result)
        manifest.update(B.outcome_block(counts, named, ended))
        manifest["state"] = "finished" if ended == "finished" else ended
    except KeyboardInterrupt:
        stop.set()
        manifest["state"] = "stopped on request"
    finally:
        B.P.bs_logout()
        write_manifest(manifest)
    print(f"wrote {MANIFEST.relative_to(ROOT)}: {manifest['state']}", flush=True)
    return 0 if manifest["state"] == "finished" else 4


if __name__ == "__main__":
    raise SystemExit(main())
