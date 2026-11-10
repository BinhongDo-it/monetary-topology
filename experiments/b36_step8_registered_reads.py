"""B36: the two registered predictions that were waiting on their sources.

Both were written before the months they speak about were published, and both say where
the number will come from. This script reads whatever of those months is on disk, and for
each clause says one of three things: decided true, decided false, or not readable yet,
with the missing months named. It fetches nothing; the existing fetchers do that.

**Prediction one, section R26 of the result file, registered 2026-09-02.** Brazilian beef to
China, Comex Stat, NCM under 0201 and 0202:

    R26-1a  August 2026 <= July's 82,714 t (the July figure as registered)
    R26-1b  August 2026 below 72,417 t, the low edge of the lane's own seasonal band
            (August/July 0.876 to 1.237 since 2020, applied to July)
    R26-2   the controls (Chile, Egypt) do not fall with it. Read on the lane's own
            August/July ratio: a control at or above the seasonal floor 0.876 holds; a
            control at or below China's own ratio fell with it; between is not read
    R26-3   September lower than August. Lower -> PASS. Higher and back inside the seasonal
            band (>= 72,417 t) -> FAIL. Higher but under the band: the clause "or close to
            the floor" has no registered number, so no verdict

**Prediction two, section R15.5, US beef to China, Census API, HS 0201 and 0202 to
CTY_CODE 5700:**

    R15-a   the July-December 2026 monthly mean is above June 2026's 1,152 t
    R15-b   and above the July-December 2025 monthly mean

Exports are not negative, so the published months already bound the mean from below:
sum(published) / 6. A clause is decided true as soon as that bound clears its line, and
decided false only when all six months are published. A month counts as published when the
world total for that month and heading is on disk and not empty; an empty China cell in a
published month is a zero, an absent or unpublished one is not.

    python experiments/b36_step8_registered_reads.py --selftest
    python experiments/b36_step8_registered_reads.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
BR = ROOT / "data" / "b36"
US = ROOT / "data" / "b35"
OUT = ROOT / "results" / "b36_registered_reads.json"

JULY_REGISTERED = 82_714.0          # R26 prediction 1, as written on 2026-09-02
SEASON_LOW_T = 72_417.0             # R26: 0.876 x July, the lane's own seasonal low edge
SEASON_LOW_RATIO = 0.876            # August/July 2024, the lowest since 2020 (R26)
JUNE_US_T = 1_152.0                 # R15.5, June 2026, tonnes
HEADS = ("0201", "0202")
CONTROLS = ("chile", "egypt")


# ---------------------------------------------------------------- loaders

def comex_months(slug, year, root=BR):
    """{month: tonnes}, or None if the year file is not on disk."""
    p = root / ("general_%s_%d.json" % (slug, year))
    if not p.exists():
        return None
    out = {}
    for r in json.loads(p.read_text(encoding="utf-8"))["data"]["list"]:
        m = int(r["monthNumber"])
        out[m] = out.get(m, 0.0) + float(r["metricKG"]) / 1000.0
    return out


def _cells(p):
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if d == [["_empty"]]:
        return []
    h = d[0]
    return [dict(zip(h, r)) for r in d[1:]]


def us_month(year, month, root=US):
    """(tonnes to China, published?) for one month, both headings."""
    tonnes, published = 0.0, True
    for hs in HEADS:
        world = _cells(root / ("%s_%d_%02d_total_HS10.json" % (hs, year, month)))
        if not world:                       # absent or empty: not published, not zero
            published = False
            continue
        china = _cells(root / ("%s_%d_%02d_5700_HS10.json" % (hs, year, month)))
        if china is None:
            published = False
            continue
        tonnes += sum(float(r["QTY_1_MO"] or 0) for r in china) / 1000.0
    return tonnes, published


# ---------------------------------------------------------------- criteria

def r26(china, controls):
    """china, controls[slug]: {month: tonnes} for 2026, or None."""
    crit = []
    aug = china.get(8) if china else None
    jul = china.get(7) if china else None
    sep = china.get(9) if china else None

    if aug is None:
        p1a = p1b = None
        d1 = "August 2026 not on disk for the China lane"
    else:
        p1a, p1b = aug <= JULY_REGISTERED, aug < SEASON_LOW_T
        d1 = (f"August {aug:,.0f} t against July as registered {JULY_REGISTERED:,.0f} t "
              f"(July as now served {jul:,.0f} t); seasonal band low edge "
              f"{SEASON_LOW_T:,.0f} t")
    crit.append({"name": "B36-R26-1a", "kind": "own_reading", "passed": p1a,
                 "statement": "August 2026 Brazil-to-China beef at or below July's 82,714 t.",
                 "detail": d1})
    crit.append({"name": "B36-R26-1b", "kind": "own_reading", "passed": p1b,
                 "statement": "August 2026 below 72,417 t, the low edge of the lane's own "
                              "August/July band applied to July.", "detail": d1})

    ratio_cn = (aug / jul) if (aug is not None and jul) else None
    states, parts = [], []
    for s in CONTROLS:
        c = controls.get(s)
        if ratio_cn is None or not c or c.get(8) is None or not c.get(7):
            states.append(None)
            parts.append(f"{s}: August or July not on disk")
            continue
        r = c[8] / c[7]
        st = True if r >= SEASON_LOW_RATIO else (False if r <= ratio_cn else None)
        states.append(st)
        parts.append(f"{s} Aug/Jul {r:.3f}")
    if ratio_cn is None or any(s is None for s in states):
        p2 = False if any(s is False for s in states) else None
    else:
        p2 = all(states)
    crit.append({"name": "B36-R26-2", "kind": "own_reading", "passed": p2,
                 "statement": "The control destinations do not fall with the China lane in "
                              "August: each holds at or above 0.876 August/July.",
                 "detail": (f"China Aug/Jul {ratio_cn:.3f}; " if ratio_cn else "") +
                           "; ".join(parts)})

    if sep is None or aug is None:
        p3, d3 = None, "September or August 2026 not on disk for the China lane"
    elif sep < aug:
        p3, d3 = True, f"September {sep:,.0f} t below August {aug:,.0f} t"
    elif sep >= SEASON_LOW_T:
        p3, d3 = False, f"September {sep:,.0f} t above August {aug:,.0f} t and inside the band"
    else:
        p3, d3 = None, (f"September {sep:,.0f} t above August {aug:,.0f} t but under the "
                        f"band; 'close to the floor' has no registered number")
    crit.append({"name": "B36-R26-3", "kind": "own_reading", "passed": p3,
                 "statement": "September 2026 lower than August.", "detail": d3})
    return crit


def r15(h2_2026, h2_2025):
    """h2_*: list of six (tonnes, published) for July..December."""
    pub = [t for t, ok in h2_2026 if ok]
    names = [m for m, (t, ok) in zip(range(7, 13), h2_2026) if not ok]
    lower = sum(pub) / 6.0
    full = len(pub) == 6
    base25 = sum(t for t, _ok in h2_2025) / 6.0 if all(ok for _t, ok in h2_2025) else None
    crit = []
    for name, line, label in (("B36-R15-a", JUNE_US_T, "the June 2026 month"),
                              ("B36-R15-b", base25, "the July-December 2025 mean")):
        if line is None:
            p, d = None, "July-December 2025 not complete on disk"
        elif lower > line:
            p = True
            d = (f"{len(pub)} of 6 months published ({', '.join(f'{t:,.0f}' for t in pub)} t); "
                 f"the mean is at least {lower:,.1f} t whatever the rest are, above "
                 f"{label} {line:,.1f} t")
        elif full:
            p, d = False, f"mean {lower:,.1f} t, not above {label} {line:,.1f} t"
        else:
            need = 6.0 * line - sum(pub)
            p = None
            d = (f"{len(pub)} of 6 months published, months {names} not yet; the mean is "
                 f"at least {lower:,.1f} t; it clears {label} {line:,.1f} t if the remaining "
                 f"months sum to more than {need:,.0f} t")
        crit.append({"name": name, "kind": "own_reading", "passed": p,
                     "statement": f"The July-December 2026 monthly mean of US beef to China "
                                  f"is above {label}.", "detail": d})
    return crit


# ---------------------------------------------------------------- selftest

def _write_comex(root, slug, months):
    rows = [{"monthNumber": "%02d" % m, "metricKG": str(t * 1000.0), "coNcm": "02023000"}
            for m, t in months.items()]
    (root / ("general_%s_2026.json" % slug)).write_text(
        json.dumps({"data": {"list": rows}}), encoding="utf-8")


def _write_us(root, y, m, tonnes, published=True):
    for hs in HEADS:
        h = ["CTY_NAME", "QTY_1_MO"]
        world = [h, ["TOTAL", "0"]] if published else [["_empty"]]
        (root / ("%s_%d_%02d_total_HS10.json" % (hs, y, m))).write_text(
            json.dumps(world), encoding="utf-8")
        if published:
            q = tonnes * 1000.0 / 2 if tonnes else 0
            cell = [h, ["CHINA", str(q)]] if tonnes else [["_empty"]]
            (root / ("%s_%d_%02d_5700_HS10.json" % (hs, y, m))).write_text(
                json.dumps(cell), encoding="utf-8")


def selftest():
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        _write_comex(root, "china", {7: 82_714, 8: 40_000, 9: 20_000})
        _write_comex(root, "chile", {7: 19_112, 8: 19_000})
        _write_comex(root, "egypt", {7: 5_543, 8: 5_400})
        cn = comex_months("china", 2026, root)
        ctl = {s: comex_months(s, 2026, root) for s in CONTROLS}
        c = {x["name"]: x for x in r26(cn, ctl)}
        checks.append(("a collapse reads true on all four R26 clauses",
                       all(c[k]["passed"] is True for k in c)))
        _write_comex(root, "china", {7: 82_714, 8: 140_000, 9: 150_000})
        c = {x["name"]: x for x in r26(comex_months("china", 2026, root), ctl)}
        checks.append(("a rebound to 140,000 t fails 1a, 1b and 3",
                       c["B36-R26-1a"]["passed"] is False and c["B36-R26-1b"]["passed"] is False
                       and c["B36-R26-3"]["passed"] is False))
        _write_comex(root, "china", {7: 82_714, 8: 40_000})
        _write_comex(root, "chile", {7: 19_112, 8: 9_000})
        c = {x["name"]: x for x in r26(comex_months("china", 2026, root),
                                       {s: comex_months(s, 2026, root) for s in CONTROLS})}
        checks.append(("a control falling as far as China fails R26-2",
                       c["B36-R26-2"]["passed"] is False))
        checks.append(("September absent leaves R26-3 without a verdict",
                       c["B36-R26-3"]["passed"] is None))
        c = {x["name"]: x for x in r26(None, {})}
        checks.append(("no file leaves every R26 clause without a verdict",
                       all(x["passed"] is None for x in c.values())))

        for m, t in zip(range(7, 13), (934.6, 745.1, 486.5, 559.8, 589.2, 942.5)):
            _write_us(root, 2025, m, t)
        _write_us(root, 2026, 7, 2025.9)
        _write_us(root, 2026, 8, 2272.8)
        for m in range(9, 13):
            _write_us(root, 2026, m, 0, published=False)
        h26 = [us_month(2026, m, root) for m in range(7, 13)]
        h25 = [us_month(2025, m, root) for m in range(7, 13)]
        c = {x["name"]: x for x in r15(h26, h25)}
        checks.append(("two months published: b decided true by the bound, a not yet",
                       c["B36-R15-b"]["passed"] is True and c["B36-R15-a"]["passed"] is None))
        _write_us(root, 2026, 9, 0)              # published, nothing to China: a real zero
        for m in range(10, 13):
            _write_us(root, 2026, m, 10.0)
        h26 = [us_month(2026, m, root) for m in range(7, 13)]
        c = {x["name"]: x for x in r15(h26, h25)}
        checks.append(("all six in and low: a fails",
                       c["B36-R15-a"]["passed"] is False))
        checks.append(("a published month with no China rows counts as zero",
                       us_month(2026, 9, root) == (0.0, True)))
        _write_us(root, 2026, 7, 9000.0)
        h26 = [us_month(2026, m, root) for m in range(7, 13)]
        c = {x["name"]: x for x in r15(h26, h25)}
        checks.append(("a large July decides a true", c["B36-R15-a"]["passed"] is True))
    print("B36 registered reads, selftest")
    for n, ok in checks:
        print(f"  {'ok ' if ok else 'BAD'} {n}")
    bad = [n for n, ok in checks if not ok]
    if bad:
        raise SystemExit(f"selftest failed: {bad}")
    print(f"selftest passed: {len(checks)} checks")


# ---------------------------------------------------------------- run

def run():
    cn = comex_months("china", 2026)
    ctl = {s: comex_months(s, 2026) for s in CONTROLS}
    crit = r26(cn, ctl)
    h26 = [us_month(2026, m) for m in range(7, 13)]
    h25 = [us_month(2025, m) for m in range(7, 13)]
    crit += r15(h26, h25)
    rec = {"stage": "B36",
           "config": {"july_registered_t": JULY_REGISTERED, "season_low_t": SEASON_LOW_T,
                      "season_low_ratio": SEASON_LOW_RATIO, "june_us_t": JUNE_US_T,
                      "controls": list(CONTROLS), "us_headings": list(HEADS),
                      "us_destination": "5700",
                      "published_rule": "world total for the month and heading on disk "
                                        "and not empty"},
           "criteria": crit,
           "report": {"brazil_china_2026": {str(k): round(v, 3) for k, v in (cn or {}).items()},
                      "controls_2026": {s: {str(k): round(v, 3) for k, v in (c or {}).items()}
                                        for s, c in ctl.items()},
                      "us_china_h2_2026": [{"month": m, "tonnes": round(t, 1),
                                            "published": ok}
                                           for m, (t, ok) in zip(range(7, 13), h26)],
                      "us_china_h2_2025": [{"month": m, "tonnes": round(t, 1),
                                            "published": ok}
                                           for m, (t, ok) in zip(range(7, 13), h25)]}}
    if all(c["passed"] is None for c in crit[:4]):
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("the R26 clauses are unread: the Comex Stat 2026 file is "
                                    "not on disk at this run; R15 is read as far as the "
                                    "published months bound it")
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    for c in crit:
        v = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"  {c['name']:11s} {v:10s} {c['detail']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest()
    if not a.selftest:
        run()


if __name__ == "__main__":
    sys.exit(main())
