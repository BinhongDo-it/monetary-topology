"""Pull the eighteen state grain reports that are still one day deep.

Eight of the twenty-six carrier reports have their full Report Detail on disk and
eighteen have only the latest issue. That gap is the same gap for two stages: the
basis stage needs the extra states to widen a reading that currently rests on
seven, and this stage needs four of them because its registration changes sit in
towns those reports price.

Nothing here is new machinery. It loops the history mode already written for the
first of those two stages, so the caching, the corrupt-file handling and the
yearly chunking are the ones already in use rather than a second implementation
that could drift from them.

Resumable by construction: a report whose years are already cached is skipped, and
a run that stops halfway leaves whole years on disk for the next run to keep.

    python experiments/b42_pull_state_histories.py --plan     # cost, fetch nothing
    python experiments/b42_pull_state_histories.py --pull
    python experiments/b42_pull_state_histories.py --pull --only 2850 2892
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_ams_probe as probe

REPO = Path(__file__).resolve().parents[1]
STRUCT = REPO / "data" / "b41" / "structure.json"
CACHE = REPO / "data" / "b41" / "cache"
YEARS = (2020, 2026)

# Reports whose towns carry a registration change, so they buy something for this
# stage as well as for the basis stage. They go first, so that a run cut short
# has still done the part with two uses.
PRIORITY = [2850, 3043, 2892, 2960, 3049]


def cached_years(rid: int) -> int:
    return len([f for f in CACHE.glob(f"reports_{rid}_Report_Detail*")])


def targets() -> list[dict]:
    struct = json.loads(STRUCT.read_text(encoding="utf-8"))
    rows = [r for r in struct["reports"] if cached_years(r["report"]) < 7]
    rows.sort(key=lambda r: (PRIORITY.index(r["report"])
                             if r["report"] in PRIORITY else 99, r["state"]))
    return rows


def plan() -> None:
    rows = targets()
    n_years = YEARS[1] - YEARS[0] + 1
    print(f"{'':2s} {'state':8s} {'report':>7} {'loc':>4} {'com':>4} {'cached':>7} "
          f"{'requests':>9}")
    for i, r in enumerate(rows, 1):
        mark = "*" if r["report"] in PRIORITY else " "
        print(f"{mark} {r['state']:8s} {r['report']:7d} {r['locations']:4d} "
              f"{r['commodities']:4d} {cached_years(r['report']):7d} {n_years:9d}")
    print(f"\n{len(rows)} reports x {n_years} years = {len(rows)*n_years} requests")
    print(f"at the probe's own pacing that is roughly "
          f"{len(rows)*n_years*0.4/60:.1f} minutes of waiting plus transfer")
    print("* marks a report whose towns carry a registration change, so it buys "
          "something for two stages rather than one. Those run first.")


def pull(only: list[int] | None) -> int:
    key = probe.api_key()
    rows = targets()
    if only:
        rows = [r for r in rows if r["report"] in only]
    if not rows:
        print("nothing to pull; every target already has its years on disk")
        return 0
    failed = []
    for i, r in enumerate(rows, 1):
        rid = r["report"]
        print(f"\n[{i}/{len(rows)}] {r['state']}  report {rid}")
        try:
            probe.mode_history(rid, key, YEARS[0], YEARS[1])
        except SystemExit as exc:
            print(f"   stopped: {exc}")
            failed.append((rid, str(exc)))
            break
        except Exception as exc:
            print(f"   failed: {type(exc).__name__} {exc}")
            failed.append((rid, f"{type(exc).__name__}: {exc}"))
            continue
        time.sleep(1.0)
    print(f"\ndone. {len(rows) - len(failed)} of {len(rows)} pulled")
    for rid, why in failed:
        print(f"   {rid}: {why}")
    left = [r["report"] for r in targets()]
    print(f"reports still short of a full history: {len(left)}  {left}")
    return 1 if failed else 0


def iso(s: str) -> str:
    s = (s or "").strip()
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        return f"{s[6:10]}-{s[0:2]}-{s[3:5]}"
    return s[:10]


def verify() -> None:
    """What is on disk now, per report, so the pull can be audited without rerunning."""
    struct = json.loads(STRUCT.read_text(encoding="utf-8"))
    print(f"{'state':8s} {'report':>7} {'files':>6} {'rows':>9} {'days':>6} {'span':>25}")
    for r in sorted(struct["reports"], key=lambda x: x["state"]):
        rid = r["report"]
        rows = []
        for f in sorted(CACHE.glob(f"reports_{rid}_Report_Detail*")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"{r['state']:8s} {rid:7d}  {f.name} does not parse"); continue
            x = d.get("results") if isinstance(d, dict) else d
            if isinstance(x, list):
                rows += x
        # report_date is MM/DD/YYYY. Sorting it as text puts December before
        # February, which is how the first version of this printed a span that
        # ended before it began. It is converted before it is ordered, the same
        # way the square stage handles it, because the trap is the same trap.
        days = sorted({iso(z.get("report_date")) for z in rows if z.get("report_date")})
        span = f"{days[0]}..{days[-1]}" if days else "-"
        if any(len(x) != 10 or x[4] != "-" for x in days):
            span += "  (unparsed dates present)"
        print(f"{r['state']:8s} {rid:7d} {cached_years(rid):6d} {len(rows):9d} "
              f"{len(days):6d} {span:>25}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true", help="print the cost, fetch nothing")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--only", type=int, nargs="+", metavar="ID")
    a = ap.parse_args()
    if a.plan: plan()
    if a.verify: verify()
    if a.pull: return pull(a.only)
    if not (a.plan or a.pull or a.verify): ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
