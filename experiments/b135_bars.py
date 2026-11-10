"""B135 bars: the daily bars the lock-buy class's volatility needs, into B110's cache.

B135-5 takes ``sigma`` from each lock-buy block's stock over the 60, 120 and
250 trading days before the trade. Every usable lock-buy block asks
for its stock's bars from ``BEFORE_DAYS`` calendar days before the trade to the
trade; a stock's windows are merged, and clipped to its listed dates. Everything else
is B110's: the security list, the per-stock cache under
``data/raw/b110/daily_baostock/stock/`` that fetches only what is not already
on disk, the guarded baostock socket, the refusal breaker and its cool-downs.

Writes nothing under ``results/``; writes ``data/raw/b135/bars_manifest.json``.

    python experiments/b135_bars.py --plan     # offline: stocks, ranges, rows, hours
    python experiments/b135_bars.py            # fetch; Ctrl+C stops after the request in hand

Needs ``pip install baostock`` (B110 installed it into this environment).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pickle
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import b110_fetch as B  # noqa: E402
import b135_readings as R  # noqa: E402

BEFORE_DAYS = 400   # 250 trading days is about 365 calendar days; the rest is margin
MANIFEST = ROOT / "data" / "raw" / "b135" / "bars_manifest.json"


def lock_windows() -> dict[str, list[tuple[str, str]]]:
    blocks = R.load_blocks()
    cache = R.CACHE / "classes_full.pkl"
    if cache.exists():
        cl = pickle.loads(cache.read_bytes())
    else:
        cl = R.classes(blocks, R.load_table("rpt_share_holder_increase", R.HOLDER_FIELDS),
                       R.load_table("rpt_executive_hold_details", R.EXEC_FIELDS), R.load_lift())
    a = R.frame(blocks, cl)
    lock = a[(a["cls"] == "lock") & a["usable"]]
    out = {}
    for code, g in lock.groupby("SECURITY_CODE"):
        merged: list = []
        for d in sorted(set(g["day"])):
            b = (dt.date.fromisoformat(d) - dt.timedelta(days=BEFORE_DAYS)).isoformat()
            merged = B.add_interval(merged, b, d)
        out[str(code)] = [tuple(w) for w in merged]
    return out


def need_by_stock(windows: dict, basic: dict) -> tuple[dict, dict]:
    need, notes = {}, {"not_in_security_list": [], "not_listed_in_window": []}
    for code, ws in windows.items():
        listed = basic.get(code) if basic else None
        if basic and listed is None:
            notes["not_in_security_list"].append(code)
        for b, e in ws:
            c = B.clip(b, e, listed)
            if c is None:
                notes["not_listed_in_window"].append(code)
                continue
            need[code] = B.add_interval(need.get(code, []), *c)
    return need, notes


def write_manifest(obj: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp.expired")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True, default=str),
                   encoding="utf-8", newline="\n")
    tmp.replace(MANIFEST)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--bs-delay", type=float, default=0.0)
    a = ap.parse_args(argv)
    last_final = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    windows = lock_windows()
    B.install_log_lock()
    if a.plan:
        basic, note = B.load_basic(network=False, refresh=False, delay=0.0, day=last_final)
    else:
        guard = B.install_socket_guard()
        print(f"socket guard {guard}", flush=True)
        basic, note = B.load_basic(network=True, refresh=False, delay=a.bs_delay, day=last_final)
    need, notes = need_by_stock(windows, basic)
    jobs = B.bar_jobs(need)
    rows = sum(B.trading_rows(b, e) for _, b, e in jobs)
    spr, how = B.seconds_per_row()
    hours = None if spr is None else rows * spr / 3600
    print(f"lock-buy stocks {len(windows)}; security list: {note}; stocks with a window {len(need)}; "
          f"ranges to ask {len(jobs)}, about {rows:,.0f} rows; "
          + (f"about {hours:.2f} h at {spr * 100:.2f} s per 100 rows ({how})" if hours is not None
             else "hours not reported: seconds per row not measured"), flush=True)
    manifest = {"window_before_days": BEFORE_DAYS, "bars_through": last_final,
                "lock_buy_stocks": len(windows), "stocks_with_window": len(need),
                "ranges": len(jobs), "rows_estimated": round(rows),
                "seconds_per_row": spr, "seconds_per_row_how": how, "notes": notes,
                "security_list": note, "state": "planned" if a.plan else "running"}
    if a.plan:
        return 0
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
        manifest["progress"] = {k: result.get(k) for k in ("jobs", "position")}
    finally:
        B.P.bs_logout()
        write_manifest(manifest)
    print(f"\nwrote {MANIFEST.relative_to(ROOT)}: {manifest['state']}", flush=True)
    return 0 if manifest["state"] == "finished" else 4


if __name__ == "__main__":
    raise SystemExit(main())
