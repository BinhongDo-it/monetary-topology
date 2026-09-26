"""B121 cell 3: the default part of the crossing cost, read off a published decomposition.

The closed form bounds the narrowing of LIBOR-OIS a new edge can buy by the gap left between LIBOR-OIS and
the edge's own price over OIS, less the crossing cost of a bank that takes the edge's funds and lends them on
at LIBOR. The part of that cost with an independent measurement is the borrower's default risk.

Filipovic and Trolle, "The term structure of interbank risk", Journal of Financial Economics 109(3), 2013,
707-733 (SSRN 1923696, fetched 2026-09-23 to data/raw/b121/lit/ssrn-1923696.pdf), decompose the three-month
USD LIBOR-OIS spread into a default and a non-default component from 2007-08-09 to 2011-01-12. Their Figure 4,
Panel A draws the two as filled areas: the default component in dark gray, the whole spread in light gray. The
figure is vector graphics, so the two outlines are read from the PDF's drawing paths, not from a picture.

The x axis is placed by the caption's own span (the first and last of 895 daily observations); the y axis by
the printed tick labels. Two checks are printed: the ticks must be evenly spaced, and the light-gray outline
(the paper's fitted spread) is set against this station's own LIBOR-OIS; that difference is the floor of this
reading, since it gathers the two sources, the model fit and the digitisation.

    python experiments/b121_ft_default.py
    python experiments/b121_ft_default.py --selftest
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "b121" / "lit" / "ssrn-1923696.pdf"
COVER = ROOT / "results" / "b121_taf_cover.json"
OUT = ROOT / "results" / "b121_ft_default.json"
PAGE = 55  # zero-based: page 56 of the SSRN file, Figure 4
FIRST, LAST = dt.date(2007, 8, 9), dt.date(2011, 1, 12)  # the caption's span
DARK, LIGHT = 0.4, 0.7  # fill gray levels: default component, whole spread
TICKS = ("0", "100", "200", "300", "400")


def outline_top(points: list[tuple[float, float]], x: float, halfwidth: float) -> float | None:
    near = [y for px, y in points if abs(px - x) <= halfwidth]
    return None if not near else min(near)


def read_panel(page) -> dict:
    fills = [f for f in page.get_drawings()
             if f["fill"] and len(f["items"]) > 50 and f["rect"].x0 < 200 and f["rect"].y1 < 240]
    shapes = {}
    for f in fills:
        pts = [(q.x, q.y) for it in f["items"] for q in it[1:] if hasattr(q, "x")]
        shapes[round(f["fill"][0], 1)] = pts
    words = {w[4]: (w[1] + w[3]) / 2 for w in page.get_text("words") if w[0] < 100 and w[1] < 240 and w[4] in TICKS}
    return {"shapes": shapes, "ticks": words}


def calibrate(panel: dict) -> dict:
    t = panel["ticks"]
    ys = [t[k] for k in TICKS]
    steps = [ys[i] - ys[i + 1] for i in range(len(ys) - 1)]
    xs = [x for pts in panel["shapes"].values() for x, _ in pts]
    return {"y0": ys[0], "pt_per_bp": (ys[0] - ys[-1]) / 400.0, "tick_steps": [round(s, 3) for s in steps],
            "x0": min(xs), "x1": max(xs)}


def value_on(panel: dict, cal: dict, gray: float, day: dt.date) -> float | None:
    span = (LAST - FIRST).days
    x = cal["x0"] + (day - FIRST).days / span * (cal["x1"] - cal["x0"])
    top = outline_top(panel["shapes"][gray], x, 1.5 * (cal["x1"] - cal["x0"]) / span)
    return None if top is None else round((cal["y0"] - top) / cal["pt_per_bp"], 1)


def build(rows: list[dict], panel: dict) -> dict:
    cal = calibrate(panel)
    inwin = [r for r in rows if r.get("wedge_day")]
    out = []
    for r in inwin:
        day = dt.date.fromisoformat(r["wedge_day"])
        dflt, total = value_on(panel, cal, DARK, day), value_on(panel, cal, LIGHT, day)
        out.append({"auction": r["auction"], "wedge_bp": r["wedge_bp"], "left_over_bp": r["left_over_bp"],
                    "cds_bp": r.get("cds_bp"), "ft_default_bp": dflt, "ft_total_bp": total,
                    "source_gap_bp": None if total is None else round(total - r["wedge_bp"], 1),
                    "implied_k": None if not dflt or not r.get("cds_bp") else round(dflt / r["cds_bp"], 3),
                    "room_bp": None if dflt is None else round(max(0.0, r["left_over_bp"] - dflt), 1)})
    spread = max(cal["tick_steps"]) - min(cal["tick_steps"]) if cal["tick_steps"] else None
    gaps = [abs(o["source_gap_bp"]) for o in out if o["source_gap_bp"] is not None]
    floor = max(gaps) if gaps else None
    complete = bool(out) and all(o["ft_default_bp"] is not None for o in out)
    crit = [
        {"name": "B121-29", "kind": "instrument",
         "statement": "the figure's y ticks are evenly spaced to within one point and both outlines are read on every auction day in the window",
         # uneven by less than one point, the unit the outline itself is read in (one point is about 2.6 bp)
         "passed": bool(spread is not None and spread < 1.0 and complete
                        and all(o["ft_total_bp"] is not None for o in out)),
         "detail": (f"tick steps {cal['tick_steps']} pt; {len(out)} auction days; "
                    f"largest gap between the paper's fitted spread and this station's LIBOR-OIS: {floor} bp")},
        {"name": "B121-30", "kind": "own_reading",
         "statement": ("print, per auction, the room the closed form leaves for LIBOR-OIS to narrow once the published "
                       "default component is taken out of the gap between LIBOR-OIS and the auction price"),
         "passed": complete,
         "detail": ("room: " + ", ".join(f"{o['auction']} {o['room_bp']}" for o in out)) if complete
                   else "the default outline is missing on some auction day"},
    ]
    return {"stage": "B121", "calibration": cal, "floor_bp": floor, "rows": out, "criteria": crit,
            "source": {"paper": "Filipovic and Trolle (2013), JFE 109(3), Figure 4 Panel A",
                       "file": "data/raw/b121/lit/ssrn-1923696.pdf", "cover": "results/b121_taf_cover.json"}}


def selftest() -> None:
    # a fake panel: y0 = 200, 1 bp = 0.5 pt, flat default of 10 bp and flat total of 60 bp over the span
    ticks = {"0": 200.0, "100": 150.0, "200": 100.0, "300": 50.0, "400": 0.0}
    xs = [100.0 + 0.05 * i for i in range(0, 2001)]  # denser than one day per point, as the real outline is
    panel = {"ticks": ticks, "shapes": {DARK: [(x, 195.0) for x in xs] + [(x, 200.0) for x in xs],
                                        LIGHT: [(x, 170.0) for x in xs] + [(x, 200.0) for x in xs]}}
    rows = [{"auction": "2008-05-05", "wedge_day": "2008-05-05", "wedge_bp": 58.0, "left_over_bp": 40.0, "cds_bp": 50.0}]
    out = build(rows, panel)
    r = out["rows"][0]
    assert r["ft_default_bp"] == 10.0 and r["ft_total_bp"] == 60.0 and r["room_bp"] == 30.0 and r["implied_k"] == 0.2, r
    assert all(c["passed"] for c in out["criteria"]), out["criteria"]
    bent = dict(panel, ticks=dict(ticks, **{"200": 110.0}))  # uneven ticks must fail the instrument check
    assert not build(rows, bent)["criteria"][0]["passed"]
    empty = {"ticks": ticks, "shapes": {DARK: [(100.0, 195.0), (100.0, 200.0), (200.0, 200.0)],
                                        LIGHT: panel["shapes"][LIGHT]}}
    assert not build(rows, empty)["criteria"][1]["passed"]  # no outline on the day: nothing to read
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    import pymupdf
    panel = read_panel(pymupdf.open(PDF)[PAGE])
    rows = json.loads(COVER.read_text(encoding="utf-8"))["rows"]
    out = build(rows, panel)
    print(f"{'auction':<11}{'wedge':>7}{'left':>7}{'FTtot':>7}{'gap':>7}{'FTdef':>7}{'cds':>7}{'k':>7}{'room':>7}")
    for o in out["rows"]:
        f = lambda v: "" if v is None else str(v)
        print(f"{o['auction']:<11}{f(o['wedge_bp']):>7}{f(o['left_over_bp']):>7}{f(o['ft_total_bp']):>7}"
              f"{f(o['source_gap_bp']):>7}{f(o['ft_default_bp']):>7}{f(o['cds_bp']):>7}{f(o['implied_k']):>7}{f(o['room_bp']):>7}")
    print(f"floor (largest |fitted spread - LIBOR-OIS|): {out['floor_bp']} bp")
    for c in out["criteria"]:
        print(f"{c['name']} [{c['kind']}] {'PASS' if c['passed'] else 'FAIL'}: {c['detail']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0 if all(c["passed"] for c in out["criteria"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
