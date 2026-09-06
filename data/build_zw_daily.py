"""Turn the raw long table of quoted rates into a business-day panel.

The raw table is one row per (post date, rail); posts appear on trading days
only and the archive missed some of them. This builds a Monday-to-Friday panel
per rail and marks every cell with how it got there, so no downstream reader
can mistake a filled cell for an observed one.

    obs      printed on that day
    interp   linear in log between the two nearest observed days
    frozen   observed, but identical to the previous observed value
    dead     the rail printed 0.00 or had stopped by then

Never fills across a gap longer than MAX_GAP days, and never fills after a
rail's last positive print.
"""

from __future__ import annotations

import csv
import datetime as dt
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "zw" / "zw_rates_long.csv"
OUT = HERE / "processed" / "zw" / "zw_rates_daily.csv"
MAX_GAP = 14


def main() -> None:
    rails: dict[str, dict[dt.date, float]] = defaultdict(dict)
    zeros: dict[str, set[dt.date]] = defaultdict(set)
    with RAW.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            v = r["value"].strip()
            if not v:
                continue
            d = dt.date.fromisoformat(r["date"])
            k = f"{r['pair']}|{r['source']}"
            x = float(v)
            if x > 0:
                rails[k][d] = x
            else:
                zeros[k].add(d)

    lo = min(min(v) for v in rails.values())
    hi = max(max(v) for v in rails.values())
    days = [lo + dt.timedelta(days=i) for i in range((hi - lo).days + 1)]
    days = [d for d in days if d.weekday() < 5]

    out: list[tuple[str, str, str, str, str]] = []
    for k in sorted(rails):
        obs = rails[k]
        ks = sorted(obs)
        last_live = ks[-1]
        prev_val = None
        for d in days:
            if d in obs:
                x = obs[d]
                tag = "frozen" if prev_val is not None and x == prev_val else "obs"
                prev_val = x
                out.append((d.isoformat(), *k.split("|"), f"{x:.4f}", tag))
                continue
            if d in zeros[k] or d > last_live:
                out.append((d.isoformat(), *k.split("|"), "", "dead"))
                continue
            before = [t for t in ks if t < d]
            after = [t for t in ks if t > d]
            if not before or not after:
                out.append((d.isoformat(), *k.split("|"), "", "none"))
                continue
            a, b = before[-1], after[0]
            if (b - a).days > MAX_GAP:
                out.append((d.isoformat(), *k.split("|"), "", "none"))
                continue
            w = (d - a).days / (b - a).days
            x = math.exp(math.log(obs[a]) * (1 - w) + math.log(obs[b]) * w)
            out.append((d.isoformat(), *k.split("|"), f"{x:.4f}", "interp"))

    out.sort()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "date,pair,source,value,how\n" + "".join(",".join(r) + "\n" for r in out),
        encoding="utf-8", newline="\n")

    tally: dict[tuple[str, str], int] = defaultdict(int)
    for _d, pair, src, _v, how in out:
        tally[(f"{pair}|{src}", how)] += 1
    kinds = ["obs", "frozen", "interp", "dead", "none"]
    print(f"{len(out)} rows over {len(days)} business days -> {OUT}")
    print(f"{'rail':24s} " + " ".join(f"{k:>7s}" for k in kinds))
    for k in sorted(rails):
        print(f"{k:24s} " + " ".join(f"{tally[(k, x)]:7d}" for x in kinds))


if __name__ == "__main__":
    main()
