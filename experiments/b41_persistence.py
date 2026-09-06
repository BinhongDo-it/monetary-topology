"""How much of a B41 panel is new information: autocorrelation of the square.

The square is built from basis quotes, and basis is a persistent quantity. A
panel of 1,620 trading days is not 1,620 independent readings of anything, so
this measures how far apart two days have to be before they carry separate
information, and turns that into an effective sample size.

Reads only what b41_ams_probe.py has cached. No network, no key.

    python experiments/b41_persistence.py --report 3186
    python experiments/b41_persistence.py --report 3186 --max-lag 30

A series here is one position pair and one commodity pairing, followed through
time on the current delivery. Windows other than the current one are skipped
because their labels move with the calendar and would fragment the series.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_square_smoke as S  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b41" / "cache"
OUT = REPO / "data" / "b41"


def load_all(rid: int) -> dict[str, list[dict]]:
    """Every cached Report Detail row for this report, grouped by report_date."""
    by_day: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple] = set()
    files = sorted(CACHE.glob(f"reports_{rid}_Report_Detail__*.json"))
    if not files:
        raise SystemExit(f"no cached Report Detail for {rid}. Run the probe with "
                         f"--history {rid} first.")
    for f in files:
        payload = json.loads(f.read_text(encoding="utf-8"))
        for r in payload.get("results") or []:
            ident = (r.get("report_date"), S.position(r), r.get("commodity"),
                     r.get("class"), r.get("grade"), r.get("delivery_start"),
                     r.get("basis Min"), r.get("basis Max"),
                     r.get("basis Min Futures Month"))
            if ident in seen:
                continue
            seen.add(ident)
            if r.get("report_date"):
                by_day[r["report_date"]].append(r)
    print(f"{len(files)} cached file(s), {len(seen)} distinct rows, "
          f"{len(by_day)} report days")
    return by_day


def series_of(by_day: dict, ca: str, cb: str) -> dict[tuple, dict[str, float]]:
    """(pos_i, pos_j, identity of a, identity of b) -> {date: midpoint}."""
    out: dict[tuple, dict[str, float]] = defaultdict(dict)
    rolls: dict[tuple, set] = defaultdict(set)
    for day, rows in by_day.items():
        by_key, _ = S.cells(rows)
        for s in S.squares(by_key, ca, cb):
            if s["gap"] != 0 or not s["same_facility"]:
                continue
            if not s["key_a"][3].startswith("current"):
                continue
            ident = (s["pos_i"], s["pos_j"],
                     s["key_a"][0], s["key_a"][1], s["key_a"][2],
                     s["key_b"][0], s["key_b"][1], s["key_b"][2])
            out[ident][day] = s["mid"]
            rolls[ident].add((s["key_a"][4], s["key_b"][4]))
    return out, rolls


def acf(values: list[float], max_lag: int) -> list[float]:
    n = len(values)
    m = mean(values)
    dev = [v - m for v in values]
    c0 = sum(d * d for d in dev)
    if c0 == 0:
        return [float("nan")] * max_lag
    out = []
    for k in range(1, max_lag + 1):
        if n - k < 3:
            out.append(float("nan"))
            continue
        ck = sum(dev[i] * dev[i + k] for i in range(n - k))
        out.append(ck / c0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=int, required=True)
    ap.add_argument("--pair", nargs=2, default=["Soybeans", "Wheat"])
    ap.add_argument("--max-lag", type=int, default=20)
    ap.add_argument("--min-obs", type=int, default=60)
    a = ap.parse_args()

    by_day = load_all(a.report)
    ser, rolls = series_of(by_day, *a.pair)
    lengths = sorted((len(v) for v in ser.values()), reverse=True)
    print(f"{len(ser)} square series; lengths {lengths[:10]}"
          f"{' ...' if len(lengths) > 10 else ''}")
    keep = {k: v for k, v in ser.items() if len(v) >= a.min_obs}
    print(f"{len(keep)} series with at least {a.min_obs} observations\n")
    if not keep:
        print("Nothing long enough yet. Pull more history and run again.")
        return

    order = lambda d: date(int(d[6:]), int(d[:2]), int(d[3:5]))
    all_acf, rows_out = [], []
    for ident, obs in sorted(keep.items(), key=lambda kv: -len(kv[1])):
        days = sorted(obs, key=order)
        vals = [obs[d] for d in days]
        a_k = acf(vals, a.max_lag)
        all_acf.append(a_k)
        rho1 = a_k[0]
        neff_ar1 = len(vals) * (1 - rho1) / (1 + rho1) if rho1 < 1 else float("nan")
        # The truncated sum of a slowly decaying autocorrelation is itself a
        # noisy quantity and can come out at or below zero, at which point the
        # effective length is undefined rather than large. Say so instead of
        # printing a number, and do not retry at a shorter truncation to make
        # it positive: that would be choosing the answer.
        finite = [x for x in a_k if x == x]
        denom = 1 + 2 * sum(finite)
        neff_sum = len(vals) / denom if denom > 1 else float("nan")
        rows_out.append(dict(pos_i=ident[0], pos_j=ident[1],
                             a=f"{ident[2]} {ident[3]}".strip(),
                             b=f"{ident[5]} {ident[6]}".strip(),
                             n=len(vals), rho1=rho1,
                             neff_ar1=neff_ar1, neff_sum=neff_sum,
                             rolls=len(rolls[ident])))
    hdr = (f"{'i':<22}{'j':<22}{'n':>5}{'rho1':>8}{'N_eff AR1':>11}"
           f"{'N_eff sum':>11}{'rolls':>6}")
    print(hdr); print("-" * len(hdr))
    for r in rows_out:
        print(f'{r["pos_i"].split("|")[0].strip():<22}'
              f'{r["pos_j"].split("|")[0].strip():<22}{r["n"]:>5}'
              f'{r["rho1"]:>8.3f}{r["neff_ar1"]:>11.1f}{r["neff_sum"]:>11.1f}'
              f'{r["rolls"]:>6}')

    print(f"\nmean autocorrelation across {len(all_acf)} series, by lag in trading days:")
    for k in range(a.max_lag):
        vals = [s[k] for s in all_acf if s[k] == s[k]]
        if vals:
            print(f"  lag {k+1:>3}: {mean(vals):+.3f}")

    r1 = mean(r["rho1"] for r in rows_out)
    n_bar = mean(r["n"] for r in rows_out)
    print(f"\nmean lag-1 autocorrelation {r1:+.3f}")
    print(f"mean series length {n_bar:.0f} days, mean effective length "
          f"{mean(r['neff_ar1'] for r in rows_out):.1f} (AR1) / "
          f"{mean(r['neff_sum'] for r in rows_out):.1f} (sum of the ACF)")
    print("Effective length is what may be multiplied by the number of "
          "independent cycles, not the raw day count.")

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"persistence_{a.report}.json"
    dest.write_text(json.dumps(dict(report=a.report, pair=a.pair, series=rows_out),
                               ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
