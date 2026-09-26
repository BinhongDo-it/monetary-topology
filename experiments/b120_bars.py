"""B120 bars: the daily bars over each locked-price plan's window, added to the B110 bar store.

**What this is for.** `B120-1` sets each plan's price against the average before its pricing base date,
and `B120-3` to `B120-5` read the price on the day each plan ended against its locked price. Both need
a stock's daily bars from before the plan's first document to its end. The B110 store under
`data/raw/b110/daily_baostock/stock/` already holds most of them, one file per stock with the date
ranges it covers; this script asks baostock for the ranges the plans need and that store lacks, with
B110's fetcher, so there is one store of A-share bars.

**A plan's window** runs from 60 calendar days before its first date (twenty trading days before a
base date, with the longest holiday inside) to 10 days after its end, or after its issue when the plan
moved to first-day pricing and then issued; a pending plan's runs to the last finished trading day.
A plan's first date is the earliest of its first locked document, the plan documents assigned to it
and the calendar base dates its documents read: 40 of the 929 plans of 2026-09-17 have a plan document
before their first agreement, 9 of them by 61 to 120 days, and the base date is that document's board
date. Windows of one stock are merged and cut to its listed dates. Codes baostock does not carry
(Beijing) are named and skipped.

**What it writes.** Bars into the B110 store and its request and bar logs, as `b110_fetch.py` does;
`data/raw/b120/bars_manifest.json` with the counts and every named gap; the printout at
`data/raw/b120/bars_printout_<time>.txt`. No criterion and nothing under `results/`.

    python experiments/b120_bars.py --selftest
    python experiments/b120_bars.py --plan      # offline: stocks, ranges not on disk, rows, hours
    python experiments/b120_bars.py             # fetch the missing ranges

The network part runs where baostock answers (its server takes a raw socket, not HTTP).
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import datetime as dt
import io
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b110_fetch as F110  # noqa: E402
import b110_probe as P110  # noqa: E402
import b120_fetch as F  # noqa: E402
import b120_plans as B  # noqa: E402
import b120_probe as P  # noqa: E402

BEFORE_DAYS = 60
AFTER_DAYS = 10
MANIFEST = "bars_manifest.json"


def document_days(events: dict) -> dict:
    """plan document id -> its day, from the plans script's events."""
    return {det["id"]: d for evs in events.values() for d, k, det in evs if k == "plan document"}


def first_day(p: dict, doc_day: dict) -> dt.date:
    """The earliest of the plan's first locked document, the plan documents assigned to it and the calendar base dates read."""
    return min([p["b"]] + [doc_day[i] for i in p.get("documents", []) if i in doc_day] + list(p.get("base_days", [])))


def plan_window(p: dict, last_final: dt.date, doc_day: dict | None = None) -> tuple[str, str] | None:
    end = max(p["t"], p["then"][0]) if p.get("then") else p["t"]
    beg = first_day(p, doc_day or {}) - dt.timedelta(days=BEFORE_DAYS)
    end = min(end + dt.timedelta(days=AFTER_DAYS), last_final)
    return (beg.isoformat(), end.isoformat()) if beg <= end else None


def needed(plans: list[dict], basic: dict, last_final: dt.date, doc_day: dict | None = None) -> tuple[dict, dict]:
    """code -> merged ranges its plans need, cut to its listed dates; and the plans that need nothing, by reason."""
    need: dict[str, list] = {}
    notes: dict = {"not carried by baostock": set(), "not in the security list": set(), "not listed in the window": [],
                   "no window": []}
    for p in sorted(plans, key=lambda p: (p["code"], p["b"])):
        code = p["code"]
        w = plan_window(p, last_final, doc_day)
        if w is None:
            notes["no window"].append(f"{code} {p['b']}")
            continue
        if P110.bs_code(code) is None:
            notes["not carried by baostock"].add(code)
            continue
        listed = basic.get(code) if basic else None
        if basic and listed is None:
            notes["not in the security list"].add(code)
        c = F110.clip(w[0], w[1], listed)
        if c is None:
            notes["not listed in the window"].append(f"{code} {p['b']}")
            continue
        need[code] = F110.add_interval(need.get(code, []), *c)
    return need, notes


def ranges_to_ask(need: dict, offline: bool) -> list[tuple[str, str, str]]:
    """The parts of the needed ranges the B110 store does not cover. Offline, the probe's cached windows count as
    covered, as in `b110_fetch.py --plan`; online they have been folded into the store before this is asked."""
    if offline:
        return F110.bar_jobs(need, repair=False, probe=F110.probe_windows())
    return F110.bar_jobs(need)


def rows_in(ranges) -> float:
    return sum(F110.trading_rows(b, e) for b, e in ranges)


def write_manifest(root: Path, obj: dict) -> Path:
    path = root / MANIFEST
    P.atomic_write_bytes(path, (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8"))
    return path


def run(plan_only: bool, bs_delay: float, refresh_basic: bool) -> int:
    today = P.TODAY()
    last_final = today - dt.timedelta(days=1)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        built = B.build(write=False)
    plans = built["plans"]
    print(f"== plans read from the census cache: {len(plans)}, {len({p['code'] for p in plans})} companies; by outcome "
          f"{dict(collections.Counter(p['outcome'] for p in plans))}")
    doc_day = document_days(built["events"])
    guard = "not installed: offline"
    if not plan_only:
        F110.install_log_lock()
        guard = F110.install_socket_guard()
        print(f"== socket guard {guard}", flush=True)
    basic, note = F110.load_basic(network=not plan_only, refresh=refresh_basic, delay=bs_delay, day=last_final.isoformat(),
                                  repair=not plan_only)
    print(f"== security list: {note}; {len(basic)} stocks")
    need, notes = needed(plans, basic, last_final, doc_day)
    moved = sum(1 for p in plans if first_day(p, doc_day) < p["b"])
    print(f"== plans whose first date is before their first locked document: {moved}")
    if not plan_only:
        print(f"== probe windows folded into the store: {F110.import_probe_windows()}")
    jobs = ranges_to_ask(need, offline=plan_only)
    need_rows = sum(rows_in(spans) for spans in need.values())
    left_rows = rows_in([(b, e) for _, b, e in jobs])
    print(f"== bars through {last_final}: {len(need)} stocks, about {need_rows:,.0f} rows needed; {len(jobs)} ranges and about "
          f"{left_rows:,.0f} rows not in the B110 store, over {len({c for c, _, _ in jobs})} stocks")
    for k, v in notes.items():
        print(f"   plans without bars, {k}: {len(v)} {sorted(v)[:12]}")
    rate, how = F110.seconds_per_row()
    if rate is None:
        print("   hours: not measured, no hours printed")
    else:
        print(f"   hours: {(left_rows * rate + len(jobs) * bs_delay) / 3600:.2f} at {rate * 100:.3f} s per 100 rows ({how}) "
              f"plus {bs_delay}s per range")
    if plan_only:
        return 0
    conflicts = [0]
    live: dict = {}

    def do(job):
        code, b, e = job
        how, detail, c = F110.fetch_gap(code, b, e, bs_delay, listed=code in basic)
        conflicts[0] += c
        return how, detail

    stop = threading.Event()
    try:
        counts, named, ended = F110.run_jobs("bars", jobs, do, stop, F110.BREAKER, F110.COOLDOWN["bars"], F110.MAX_COOLDOWNS, 25,
                                             relogin=P110.bs_logout, live=live)
    except KeyboardInterrupt:
        counts, named, ended = live.get("counts", {}), live.get("named", {}), f"stopped on request at {live.get('position', 0)} of {len(jobs)}"
    finally:
        P110.bs_logout()
    left = F110.bar_jobs(need, repair=False)
    manifest = {"bars_through": last_final.isoformat(),
                "window": {"before_days": BEFORE_DAYS, "after_days": AFTER_DAYS, "plans_starting_before_their_first_agreement": moved},
                "plans": len(plans), "stocks": len(need), "ranges_asked": len(jobs), "ended": ended,
                "counts": dict(counts), "named": {k: v for k, v in named.items()}, "row_conflicts": conflicts[0],
                "ranges_still_missing": len(left), "missing": [list(j) for j in left[:500]],
                "plans_without_bars": {k: sorted(v) for k, v in notes.items()}, "security_list": note, "socket_guard": guard}
    path = write_manifest(P.RAW, manifest)
    print(f"== {ended}; {dict(counts)}; row conflicts {conflicts[0]}; ranges still missing {len(left)}; wrote data/raw/b120/{path.name}")
    for how, items in sorted(named.items()):
        print(f"   {how}: {len(items)}, first {items[:3]}")
    return 0 if ended == "finished" else 1


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    d = dt.date
    last = d(2026, 9, 16)

    def plan(code, b, t, then=None, outcome="issued"):
        return {"code": code, "b": b, "t": t, "then": then, "outcome": outcome}

    early = dict(plan("600004", d(2021, 7, 27), d(2021, 9, 1)), documents=["9", "10", "11"], base_days=[d(2021, 7, 20)])
    doc_day = document_days({"600004": [(d(2021, 3, 29), "plan document", {"id": "9"}), (d(2021, 3, 29), "issued", {"id": "x"}),
                                        (d(2021, 8, 2), "plan document", {"id": "10"})], "600005": [(d(2020, 1, 2), "plan document", {"id": "12"})]})
    firsts = [first_day(early, doc_day), first_day(dict(early, documents=["10"]), doc_day), first_day(dict(early, documents=[]), doc_day),
              first_day(plan("600006", d(2022, 1, 1), d(2022, 2, 1)), doc_day)]
    check(f"a plan's first date is the earliest of its first locked document, its plan documents and its calendar base dates; a "
          f"document of another plan or an unknown id does not move it ({firsts}, {plan_window(early, last, doc_day)})",
          firsts == [d(2021, 3, 29), d(2021, 7, 20), d(2021, 7, 20), d(2022, 1, 1)] and doc_day == {"9": d(2021, 3, 29), "10": d(2021, 8, 2), "12": d(2020, 1, 2)}
          and plan_window(early, last, doc_day) == ("2021-01-28", "2021-09-11"))
    w = [plan_window(plan("600001", d(2021, 3, 1), d(2021, 9, 1)), last),
         plan_window(plan("600001", d(2025, 5, 8), d(2026, 6, 16), then=(d(2026, 7, 27), "issued", {})), last),
         plan_window(plan("600002", d(2026, 2, 7), d(2026, 9, 16), outcome="pending"), last),
         plan_window(plan("600003", d(2026, 9, 1), d(2026, 9, 16)), d(2026, 7, 1))]
    check(f"a window runs 60 days before the plan's first date to 10 days after the end or the issue after a move, cut at the last "
          f"finished day ({w})",
          w == [("2020-12-31", "2021-09-11"), ("2025-03-09", "2026-08-06"), ("2025-12-09", "2026-09-16"), None])
    plans = [plan("600001", d(2021, 3, 1), d(2021, 9, 1)), plan("600001", d(2021, 6, 1), d(2022, 1, 1)),
             plan("920001", d(2022, 3, 1), d(2022, 9, 1)), plan("000001", d(2019, 1, 1), d(2019, 6, 1)),
             plan("300001", d(2022, 3, 1), d(2022, 9, 1)), plan("600009", d(2026, 9, 10), d(2026, 9, 16)),
             dict(plan("600009", d(2025, 1, 10), d(2025, 3, 1)), documents=["20"])]
    basic = {"600001": ("2000-01-01", ""), "000001": ("2020-01-01", ""), "600009": ("2000-01-01", "")}
    need, notes = needed(plans, basic, last, {"20": d(2024, 11, 1)})
    check(f"windows of one stock merge, a Beijing code is skipped, a window before listing is named, a code missing from the "
          f"security list is named and kept ({need}, {({k: sorted(v) for k, v in notes.items()})})",
          need == {"600001": [["2020-12-31", "2022-01-11"]], "300001": [["2021-12-31", "2022-09-11"]],
                   "600009": [["2024-09-02", "2025-03-11"], ["2026-07-12", "2026-09-16"]]}
          and notes["not carried by baostock"] == {"920001"} and notes["not listed in the window"] == ["000001 2019-01-01"]
          and notes["not in the security list"] == {"300001"} and notes["no window"] == [])
    import tempfile
    saved = P110.RAW
    with tempfile.TemporaryDirectory() as tmp:
        P110.RAW = Path(tmp)
        try:
            store = F110.empty_store("600001")
            store.update(covered=[["2021-01-01", "2021-06-30"]],
                         rows=[["2021-01-04", "sh.600001", "1", "1", "1", "1", "1", "100", "100", "1", "0.1", "1.0", "0"]])
            store["rows"] = [r[:len(P110.BS_FIELDS)] + [""] * (len(P110.BS_FIELDS) - len(r)) for r in store["rows"]]
            store["rows"][0][9] = "1"
            F110.write_store("600001", store)
            jobs = ranges_to_ask({"600001": [["2020-12-31", "2022-01-11"]], "300001": [["2021-12-31", "2022-09-11"]]}, offline=True)
        finally:
            P110.RAW = saved
    check(f"the ranges asked are the parts of each window the store does not cover ({jobs})",
          jobs == [("300001", "2021-12-31", "2022-09-11"), ("600001", "2020-12-31", "2020-12-31"), ("600001", "2021-07-01", "2022-01-11")])
    with tempfile.TemporaryDirectory() as tmp:
        a = write_manifest(Path(tmp), {"b": 1, "a": {"z": 1, "y": [1, 2]}}).read_bytes()
        b = write_manifest(Path(tmp), {"a": {"y": [1, 2], "z": 1}, "b": 1}).read_bytes()
    check("the manifest is written with sorted keys, so two runs with the same counts write the same bytes", a == b)
    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="offline: stocks, ranges not on disk, rows, hours")
    ap.add_argument("--bs-delay", type=float, default=0.2, help="seconds to wait after each baostock answer")
    ap.add_argument("--refresh-basic", action="store_true", help="ask baostock for a new security list")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    out = P.RAW / f"bars_printout_{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}{'_plan' if args.plan else ''}.txt"
    tee = F.Tee(sys.stdout, out)
    sys.stdout = tee
    try:
        print(f"printout also written to data/raw/b120/{out.name}")
        return run(args.plan, args.bs_delay, args.refresh_basic)
    finally:
        sys.stdout = tee.stream
        tee.fh.close()


if __name__ == "__main__":
    sys.exit(main())
