"""B42: weekly grain barge tonnage by lock and commodity, and how fast it decorrelates.

This carrier answers a question the daily exchange snapshots cannot answer without
waiting: how many observations a flow variable has to accumulate before it carries
anything. The lock panel is already thirteen years long, so the persistence can be
measured now instead of estimated from a bracket and revisited in a year.

The object is a two-index quantity on positions: tons of one commodity moving past
one lock in one week. A model in which position carries a single scalar has nowhere
to put the commodity index, and the additive residual below is exactly the part of
the panel such a model cannot produce.

Source: USDA AMS open transport data, Socrata dataset n4pw-9ygw, built from the
Army Corps of Engineers Lock Performance Monitoring System. Free, no key, no bot
wall. Seven locks, four commodities, weekly, 2003 or 2013 to present depending on
the lock.

    python experiments/b42_lock_flows.py --fetch        # cache the panel
    python experiments/b42_lock_flows.py --describe     # print the object first
    python experiments/b42_lock_flows.py --persistence  # rho, and what it costs

Nothing is deleted. A cached page that fails to parse is renamed aside with a
timestamp so the day it was fetched stays inspectable.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b42" / "agtransport"
DATASET = "n4pw-9ygw"
BASE = f"https://agtransport.usda.gov/resource/{DATASET}.json"
PAGE = 20000
PAIR = ("Corn", "Soybeans")


def _get(params: dict) -> list:
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(force: bool = False) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    off, page = 0, 0
    while True:
        dest = CACHE / f"{DATASET}_offset{off:06d}.json"
        if dest.exists() and not force:
            rows = json.loads(dest.read_text(encoding="utf-8"))
            print(f"  offset {off:6d}: {len(rows):6d} rows (cached)")
        else:
            rows = _get({"$limit": PAGE, "$offset": off, "$order": "date,lock,commodity"})
            tmp = dest.with_suffix(".json.part")
            tmp.write_text(json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=1),
                           encoding="utf-8", newline="\n")
            tmp.replace(dest)
            print(f"  offset {off:6d}: {len(rows):6d} rows (fetched)")
            time.sleep(1.0)
        if len(rows) < PAGE:
            break
        off += PAGE
        page += 1
        if page > 50:
            print("  refusing to page further; check the query"); break
    print(f"cache: {CACHE}")


def load() -> list:
    out = []
    for f in sorted(CACHE.glob(f"{DATASET}_offset*.json")):
        try:
            out += json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            aside = f.with_suffix(f".corrupt.{ts}.json")
            f.rename(aside)
            print(f"  {f.name} did not parse; kept as {aside.name}")
    for r in out:
        r["week_date"] = (r.get("date") or "")[:10]
        try:
            r["tons"] = float(r.get("tons"))
        except (TypeError, ValueError):
            r["tons"] = float("nan")
    return out


def describe() -> None:
    """Print the object before any statistic touches it."""
    rows = load()
    if not rows:
        print("nothing cached; run --fetch first"); return
    locks = sorted({r["lock"] for r in rows})
    coms = sorted({r["commodity"] for r in rows})
    dates = sorted({r["week_date"] for r in rows})
    print(f"rows {len(rows)}   locks {len(locks)}   commodities {len(coms)}   weeks {len(dates)}")
    print(f"span {dates[0]} .. {dates[-1]}")
    print(f"\n{'lock':16s} {'commodity':12s} {'weeks':>6} {'zeros':>6} {'zero%':>7} "
          f"{'median':>10} {'max':>12}")
    for lk in locks:
        for cm in coms:
            v = sorted(r["tons"] for r in rows if r["lock"] == lk and r["commodity"] == cm
                       and r["tons"] == r["tons"])
            if not v:
                continue
            z = sum(1 for x in v if x == 0)
            print(f"{lk:16s} {cm:12s} {len(v):6d} {z:6d} {100*z/len(v):6.1f}% "
                  f"{v[len(v)//2]:10.0f} {v[-1]:12.0f}")
    print("\nZeros are not missing data. The upper Mississippi and Illinois locks close "
          "for winter, so a structural zero is the river being shut rather than no "
          "grain moving. Any window that reads levels has to carry that; a window that "
          "reads differences across commodities at one lock in one week does not, "
          "because a closed lock zeroes both commodities together.")


def _additive_residual(M: list[list[float]]) -> list[list[float]]:
    """Remove one row effect and one column effect by alternating centering.

    Written out rather than imported so this stage does not become a consumer of
    another stage's machinery. Checked against a least-squares fit below.
    """
    R, C = len(M), len(M[0])
    A = [row[:] for row in M]
    for _ in range(200):
        for i in range(R):
            m = sum(A[i]) / C
            for j in range(C):
                A[i][j] -= m
        worst = 0.0
        for j in range(C):
            m = sum(A[i][j] for i in range(R)) / R
            worst = max(worst, abs(m))
            for i in range(R):
                A[i][j] -= m
        if worst < 1e-13:
            break
    return A


def _check_against_lstsq(M: list[list[float]], res: list[list[float]]) -> float:
    """Same residual from a design matrix, so convergence is demonstrated not promised."""
    try:
        import numpy as np
    except ImportError:
        return float("nan")
    R, C = len(M), len(M[0])
    X, y = [], []
    for i in range(R):
        for j in range(C):
            row = [1.0] + [0.0] * (R - 1) + [0.0] * (C - 1)
            if i: row[i] = 1.0
            if j: row[R - 1 + j] = 1.0
            X.append(row); y.append(M[i][j])
    b, *_ = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)
    fit = (np.array(X) @ b).reshape(R, C)
    return float(np.max(np.abs((np.array(M) - fit) - np.array(res))))


def persistence(max_lag: int = 60) -> None:
    rows = load()
    if not rows:
        print("nothing cached; run --fetch first"); return
    locks = sorted({r["lock"] for r in rows})
    by = {}
    for r in rows:
        if r["commodity"] in PAIR:
            by[(r["week_date"], r["lock"], r["commodity"])] = r["tons"]
    weeks = sorted({k[0] for k in by})
    full = [w for w in weeks
            if all((w, lk, cm) in by and by[(w, lk, cm)] == by[(w, lk, cm)]
                   for lk in locks for cm in PAIR)]
    print(f"complete {len(locks)} x {len(PAIR)} weeks: {len(full)} of {len(weeks)}")
    print(f"D22  b1 = ({len(locks)}-1)({len(PAIR)}-1) = {(len(locks)-1)*(len(PAIR)-1)}")
    if len(full) < 30:
        print("too few complete weeks to say anything about persistence"); return

    # log tons so the residual is a ratio contrast rather than a level contrast;
    # +1 keeps a closed-lock zero finite instead of dropping the week.
    series = []
    lstsq_gap = 0.0
    for w in full:
        M = [[math.log1p(by[(w, lk, cm)]) for cm in PAIR] for lk in locks]
        res = _additive_residual(M)
        if not series:
            lstsq_gap = _check_against_lstsq(M, res)
        series.append(math.sqrt(sum(x * x for r in res for x in r)))
    n = len(series)
    mu = sum(series) / n
    dev = [x - mu for x in series]
    v0 = sum(d * d for d in dev) / n
    acf = [sum(dev[i] * dev[i + k] for i in range(n - k)) / (n - k) / v0
           for k in range(1, max_lag + 1)]
    rho1 = acf[0]
    first_zero = next((k + 1 for k, a in enumerate(acf) if a <= 0), None)
    neff = n * (1 - rho1) / (1 + rho1) if rho1 < 1 else float("nan")
    print(f"\nadditive residual checked against lstsq: max gap {lstsq_gap:.3e}")
    print(f"weeks n            {n}")
    print(f"residual mean      {mu:.4f}   sd {math.sqrt(v0):.4f}")
    print(f"rho_1              {rho1:.4f}")
    print(f"first non-positive acf at lag  {first_zero}")
    print(f"N_eff = n(1-r)/(1+r)  {neff:.1f}")
    print("\nacf by lag: " + "  ".join(f"{k+1}:{a:+.3f}" for k, a in enumerate(acf[:12])))
    print("\nWhat this buys: N_eff is the number of independent weekly observations the "
          "panel already holds. A forward-only daily series has to run until it reaches "
          "the same number, and this figure is what that target is, measured rather "
          "than assumed.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="cache the panel")
    ap.add_argument("--force", action="store_true", help="refetch pages already cached")
    ap.add_argument("--describe", action="store_true", help="print the object")
    ap.add_argument("--persistence", action="store_true", help="rho and N_eff")
    a = ap.parse_args()
    if a.fetch: fetch(a.force)
    if a.describe: describe()
    if a.persistence: persistence()
    if not (a.fetch or a.describe or a.persistence):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
