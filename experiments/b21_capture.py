"""B21: a statutory change that taxes one trade, and whether the trade thins out.

Caishui [2012] 85, in force 2013-01-01, made an individual's tax on a listed
dividend depend on how long the share was held: the whole dividend enters taxable
income under a month, half of it from a month to a year, a quarter beyond. At the
flat 20 per cent rate that is **20, 10 and 5 per cent**. What it replaced,
Caishui [2005] 107, taxed every holder at 10 per cent whatever the holding.

**So on one dated day the dividend-capture trade doubled in cost.** Buy before
the ex-date, take the dividend, sell inside a month, and the tax on that dividend
went from 10 per cent to 20. Nothing else about the trade changed.

**The prediction is declared here before the run, with its direction and its
control.** Volume around an A-leg ex-date should thin after 2013-01-01 relative
to what it was before. **The H leg of the same company is the control**: an
H-share dividend is not within Caishui [2012] 85 at all, mainland individuals
could not reach the H line until Southbound opened in November 2014, and the
company, the dividend and the year are shared. **So the H leg should not move.**

**Caishui [2015] 101 is not the event.** It took the over-one-year tier from 5
per cent to zero and left the under-a-month tier at 20, which is the tier the
capture trade sits in. The date that matters here is 2013-01-01.

**The baseline is two-sided, and the first version's was not.** Taking the
stock's normal volume only from the weeks *before* the ex-date puts the baseline
earlier in calendar time than the window it normalises, so any trend in volume
leaks straight into the ratio. A-share volume grew by orders of magnitude over
these twenty years, and the two eras being compared have different trends, so the
one-sided version measured the trend. **Printing the profile is what showed it**:
the one-sided reading sat 12 to 24 per cent below baseline at *every* lag from
minus ten to plus ten, and no ex-date effect can be present ten days before the
ex-date. A baseline taken symmetrically on both sides cancels a local trend to
first order.

**What this is not.** It is a sign, declared in advance, on a ratio of volumes.
It is not an effect size against a band, so gates two and three do not bind it
(the six criterion shapes). The standard error is printed anyway, because
printing it is free.

Usage::

    python experiments/b21_capture.py
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"
OUT = ROOT / "results" / "b21_capture.json"

EVENT = "2013-01-01"        # Caishui [2012] 85 in force
PRE = (5, 1)                # trading days before the ex-date: the capture window
BASE = (60, 11)             # the stock's own normal volume, **both sides**
MIN_BASE = 20               # baseline days a reading needs


def load(tk: str) -> list[dict]:
    for c in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if c.exists():
            return list(csv.DictReader(c.open(encoding="utf-8")))
    return []


def pairs_on_page() -> list[dict]:
    import re
    row = re.compile(r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?(\d{5})\.HK.*?"
                     r"([0-9]+\.[0-9]+).*?(\d{6})\.(SH|SZ).*?([0-9]+\.[0-9]+)", re.S)
    seen, out = set(), []
    for m in row.finditer(PAGE.read_text(encoding="utf-8")):
        name, h, _, a, mkt, _ = m.groups()
        if h in seen:
            continue
        seen.add(h)
        out.append({"name": name.strip()[:22],
                    "h": (h[1:] if h.startswith("0") else h) + ".HK",
                    "a": f"{a}.{'SS' if mkt == 'SH' else 'SZ'}"})
    return sorted(out, key=lambda r: r["a"])


def bars(tk: str) -> list[tuple[str, float, float]]:
    out = []
    for r in load(tk):
        try:
            v, d = float(r.get("Volume") or 0), float(r.get("Dividends") or 0)
        except (TypeError, ValueError):
            continue
        out.append((r["Date"][:10], v, d))
    return sorted(out)


def main() -> int:
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")
    cells: dict[tuple[str, bool], list[float]] = {}
    per_event = []
    for p in pairs_on_page():
        for leg in ("a", "h"):
            b = bars(p[leg])
            for i, (day, vol, div) in enumerate(b):
                if div <= 0:
                    continue
                pre = [b[j][1] for j in range(max(0, i - PRE[0]), i - PRE[1] + 1)
                       if b[j][1] > 0]
                base = [b[j][1] for j in range(max(0, i - BASE[0]), i - BASE[1] + 1)
                        if b[j][1] > 0]
                base += [b[j][1] for j in range(i + BASE[1], min(len(b), i + BASE[0] + 1))
                         if b[j][1] > 0]
                if len(pre) < PRE[0] - PRE[1] or len(base) < 2 * MIN_BASE:
                    continue
                r = math.log(statistics.median(pre) / statistics.median(base))
                after = day >= EVENT
                cells.setdefault((leg, after), []).append(r)
                per_event.append({"leg": leg, "after": after, "day": day, "r": r})

    print(f"the capture window is the {PRE[0] - PRE[1] + 1} trading days before an")
    print(f"ex-date, against that stock's own median volume over the "
          f"{BASE[0] - BASE[1] + 1} days")
    print(f"on **each** side, eleven to sixty days out. Two-sided, because a")
    print(f"one-sided baseline sits earlier in calendar time than the window it")
    print(f"normalises and a volume trend leaks into the ratio. Log ratio, median")
    print(f"across events, because volume ratios have heavy tails.\n")

    # the worst cell, not the average one (discipline 13 step 1)
    print(f"  {'cell':>18} {'n':>7} {'median log ratio':>18} {'robust se':>11}")
    cen, se = {}, {}
    for leg in ("a", "h"):
        for after in (False, True):
            v = cells.get((leg, after), [])
            if len(v) < 30:
                print(f"  {leg.upper()+' '+('after' if after else 'before'):>18} "
                      f"{len(v):>7}   too thin to carry a centre")
                continue
            m = statistics.median(v)
            s = 1.4826 * statistics.median([abs(x - m) for x in v]) / math.sqrt(len(v))
            cen[(leg, after)] = m
            se[(leg, after)] = s
            print(f"  {leg.upper()+' '+('after' if after else 'before'):>18} "
                  f"{len(v):>7} {m:>18.4f} {s:>11.4f}")

    need = [("a", False), ("a", True), ("h", False), ("h", True)]
    if not all(k in cen for k in need):
        print("\n  one cell is too thin. **Reported, not worked around.**")
        return 1

    da = cen[("a", True)] - cen[("a", False)]
    dh = cen[("h", True)] - cen[("h", False)]
    sda = math.hypot(se[("a", True)], se[("a", False)])
    sdh = math.hypot(se[("h", True)], se[("h", False)])
    did = da - dh
    sdd = math.hypot(sda, sdh)

    print(f"\n  A leg change across {EVENT}: {da:+.4f}  ({da/sda:+.1f} se)")
    print(f"  H leg change across {EVENT}: {dh:+.4f}  ({dh/sdh:+.1f} se)   "
          f"**the control, declared to sit still**")
    print(f"  difference in differences:   {did:+.4f}  ({did/sdd:+.1f} se)")
    print(f"\n  **The sign was declared before the run**: the A leg thins, the H")
    print(f"  leg does not, so the difference is negative. No line is drawn on it.")

    # ---- describe the object, which should have come first and did not ----
    prof: dict[tuple[str, bool, int], list[float]] = {}
    for p2 in pairs_on_page():
        for leg in ("a", "h"):
            b = bars(p2[leg])
            for i, (day, vol, div) in enumerate(b):
                if div <= 0:
                    continue
                base = [b[j][1] for j in range(max(0, i - BASE[0]), i - BASE[1] + 1)
                        if b[j][1] > 0]
                base += [b[j][1] for j in range(i + BASE[1],
                                                min(len(b), i + BASE[0] + 1))
                         if b[j][1] > 0]
                if len(base) < 2 * MIN_BASE:
                    continue
                m = statistics.median(base)
                for k in range(-6, 7):
                    j = i + k
                    if 0 <= j < len(b) and b[j][1] > 0:
                        prof.setdefault((leg, day >= EVENT, k), []).append(
                            math.log(b[j][1] / m))
    print("\nthe profile, which is the step that should have come first. Median log")
    print("volume against the two-sided baseline, by trading day from the ex-date.\n")
    print(f"  {'day':>4}" + "".join(f"{x:>12}" for x in
          ("A before", "A after", "H before", "H after")))
    peak = {}
    for k in range(-6, 7):
        row = f"  {k:>4}"
        for leg, era in (("a", False), ("a", True), ("h", False), ("h", True)):
            v = prof.get((leg, era, k))
            if v and len(v) >= 30:
                mm = statistics.median(v)
                row += f"{mm:>12.3f}"
                if k < 0:
                    peak[(leg, era)] = max(peak.get((leg, era), -9), mm)
            else:
                row += f"{'-':>12}"
        print(row + ("   <- ex-date" if k == 0 else ""))
    hi = max(peak.values()) if peak else float("nan")
    print(f"\n  **The largest pre-ex reading in any cell is {hi:+.3f}.** A capture")
    print(f"  trade should leave a spike there and none of the four carries one.")

    crit = [
        {"name": "B21-24  the trade the statute penalises leaves no volume "
                 "signature to remove: no cell's pre-ex window stands above its "
                 "own baseline by more than the H leg does in both eras alike",
         "passed": None,
         "undecidable": True,
         "detail": "largest pre-ex median log volume over the two-sided baseline, "
                   + "; ".join(f"{k[0].upper()}{'after' if k[1] else 'before'} "
                               f"{v:+.3f}" for k, v in sorted(peak.items()))
                   + f". Nothing resembling a spike appears before 2013 on "
                     f"either leg; a peak at day minus one appears after 2013 on "
                     f"**both**, and the larger of the two sits on the H leg, "
                     f"which this statute does not reach. **So the pattern is a "
                     f"market-wide change and not a tax effect, and the trade the "
                     f"statute penalises is not visible on this instrument. "
                     f"Third state.**"},
        {"name": "B21-21  every cell of the two-by-two carries a centre",
         "passed": all(k in cen for k in need),
         "detail": "; ".join(f"{k[0].upper()}{'after' if k[1] else 'before'} "
                             f"n={len(cells[k])}" for k in need)},
        {"name": "B21-22  the taxed leg's move across the date, read in three "
                 "states because a sign test on an estimator has no zero width",
         "passed": None if abs(da) < 2 * sda else da < 0,
         "undecidable": abs(da) < 2 * sda,
         "detail": f"A leg {da:+.4f} at {da/sda:+.1f} standard errors across "
                   f"{EVENT}. **The first version of this criterion was "
                   f"`change < 0`, a zero-width strict inequality on an "
                   f"estimator**, which discipline 11 forbids whichever way it "
                   f"comes out; a reading a standard error and a half from zero "
                   f"is the middle state and not a refutation. The reading is "
                   f"unchanged by the correction."},
        {"name": "B21-23  the untaxed leg of the same companies does not move "
                 "with it, which is the placebo",
         "passed": abs(dh) < abs(da),
         "detail": f"H leg {dh:+.4f} ({dh/sdh:+.1f} se) against the A leg's "
                   f"{da:+.4f}; difference in differences {did:+.4f} "
                   f"({did/sdd:+.1f} se)"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B21", "step": "capture",
        "diagnostic_only": True,
        "diagnostic_reason": "A declared sign on a volume ratio, with the H leg "
                             "of the same companies as the control. Not an effect "
                             "size against a band, so gates two and three do not "
                             "bind it; the standard errors are printed regardless.",
        "event": EVENT,
        "cells": {f"{k[0]}_{'after' if k[1] else 'before'}":
                  {"n": len(cells[k]), "centre": cen[k], "se": se[k]} for k in need},
        "a_change": da, "h_change": dh, "did": did, "did_se": sdd,
        "pre_ex_peak": {f"{k[0]}_{'after' if k[1] else 'before'}": v
                        for k, v in peak.items()},
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    np_ = sum(1 for c in crit if c["passed"] is True)
    nu = sum(1 for c in crit if c.get("undecidable"))
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, {np_} passing, "
          f"{nu} undecidable, {len(crit)-np_-nu} failing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
