"""B126 readings: how far a price moves at each sale, against how often the object sells.

Reads data/b126/parsed/ (written by experiments/b126_parse.py) and writes
results/b126_auction_jump.json.

Objects, before any number is read:
  unit    a wine and a vintage. Three wines on the pages are outside the carrier (dry whites and
          a merchant's own label) and are named in EXCLUDE; the record prints the list.
  event   one house on one day. Its price is the median log price per 750 ml of that house's
          lots of the unit that day. Several lots of one unit sold by one house on one day are
          the same object at the same moment with no news in between: their spread is the
          floor (B126-3), and the jump is read between events.
  jump    |Δlog p| between adjacent events of a unit, in date order.
  unit statistic   the median jump over the unit's pairs. Units are the independent observations
          (B126-5); pairs are not.
  density site lots / years in the unit's window. Site lots is the summary's lot_count, not the
          table's rows: the table is truncated to its most recent part on 72 of 376 pages.
          The window runs from the later of the site's first recorded sale (2011-10-04) and
          vintage + LAG to the fetch date. LAG is a knob.

Knobs, each scanned (`11f`): FORMATS (750 ml only, or every size), LAG (2, 3, 4 years),
MIN_PAIRS (3, 5), CLEAN (off, 3x, 2x; see SCAN). A reading is read only where its sign does not
move across the scan. A bin of a control is read only where its own sign does not move.

Criteria (kinds per `11d`):
  B126-1  instrument   parser checks: no own-vs-site unit price gap, every HTML/JSON
                       disagreement is a tagged size conflict
  B126-2  own_reading  rank correlation of density with the unit median jump. The registered
                       reading is negative (thinner units jump further). Three states:
                       negative at every scan point / positive at every point / sign moves
  B126-3  instrument   floor: median same-day same-house spread; the main reading is read only
                       if the median jump clears it
  B126-4  own_reading  inside interval bins, three cut schemes, the sign of B126-2 holds
  B126-6  own_reading  inside age bins, three cut schemes, the sign of B126-2 holds
  B126-5  bookkeeping  units and pairs per unit printed
  B126-7  own_reading  the B126-2 reading on cross-house pairs only, each event price net of its
                       house's level (house_levels). Added 2026-09-23 after B126-2 read flat:
                       adjacent events are half the time two houses, and a house pair carries a
                       level gap (premium, currency, clientele) that no density moves
  B126-7a/7b           B126-7 inside interval bins and inside age bins, as B126-4 and B126-6
  B126-8  own_reading  the B126-2 reading on same-house pairs only (one house's consecutive sales)

Run from the repo root:
    python experiments/b126_readings.py
    python experiments/b126_readings.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics as st
import sys
from datetime import date
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
PARSED = ROOT / "data" / "b126" / "parsed"
OUT = ROOT / "results" / "b126_auction_jump.json"

EXCLUDE = {
    "chateau-dyquem-y-bordeaux": "dry white, Bordeaux appellation",
    "chateau-doisy-daene-bordeaux-sec": "dry white, Bordeaux appellation",
    "bordeaux-index-sauternes": "a merchant's own label",
}
# closed 2026-09-24: no record carries this any more; kept as the last reason the station stood open
DIAGNOSTIC_REASON = ("station open: both arms are run (results/b126_auction_jump.json, results/b126_retail.json); "
                     "the retail arm reads 42 to 58 stale units per setting and is undecided at that count, and "
                     "on the seven wines added last its stale units do not lean to the interpolation")
SITE_START = date(2011, 10, 4)   # earliest sale date on any page, read off the parsed rows
FETCHED = date(2026, 9, 22)

DEFAULT = {"formats": "750", "lag": 3, "min_pairs": 5, "clean": 3.0}
SCAN = {"formats": ["750", "all"], "lag": [2, 3, 4], "min_pairs": [3, 5], "clean": [0.0, 3.0, 2.0]}
# clean: drop a lot whose price per 750 ml is more than c times, or under 1/c times, the median
# of the other houses' lots of the same unit and size within a year either side (three or more
# of them); 0 keeps all.
# Why it exists, read off the rows 2026-09-23: quantity recorded as 1 on multi-bottle lots
# (Dreweatts, 20 of 65 comparable lots at 4.5x to 13.4x; some HDH and K&L singles at 5x to 25x),
# and one Acker sale (2026-07-25) labelled USD at 5x to 7.6x, near the HKD rate. None of these
# is detectable from the row itself; each is a jump of log 5 to log 25 on the pair it touches.
INTERVAL_CUTS = {"tercile": None, "30/180 days": (30, 180), "90/365 days": (90, 365)}
AGE_CUTS = {"tercile": None, "10/20 years": (10, 20), "15/25 years": (15, 25)}


def d(s: str) -> date:
    return date.fromisoformat(s[:10])


def events(rows: list[dict]) -> tuple[list[tuple[date, str, float]], list[float]]:
    """Events of one unit in date order, and the within-event spreads that make the floor."""
    by: dict[tuple, list[float]] = {}
    for r in rows:
        by.setdefault((r["date"], r["house"]), []).append(math.log(r["own_750_usd"]))
    ev, floor = [], []
    for (day, house), ps in sorted(by.items()):
        ev.append((d(day), house, st.median(ps)))
        if len(ps) > 1:
            m = st.median(ps)
            floor.append(st.median(abs(p - m) for p in ps) * 2)   # a typical pairwise gap
    return ev, floor


def house_levels(evs: dict, min_obs: int = 5, iters: int = 200) -> dict:
    """A house's price level: the house effect in log price = cell + house, fitted by alternating
    means, a cell being one unit in one calendar year (so drift does not enter). Only cells
    holding two or more houses identify anything, so only those are used. Houses with fewer
    than min_obs events in such cells get no level. Levels are centred on their event-weighted mean.

    A first version took each house's median deviation from its cell's median. The self-test
    killed it: when a house meets different partners on different units (h1 against h3 on thin
    units, against h2 on thick ones), its deviation depends on the partner, and the median
    lands between the two gaps."""
    obs = []
    for key, ev in evs.items():
        by_year: dict[int, list] = {}
        for e in ev:
            by_year.setdefault(e[0].year, []).append(e)
        for y, es in by_year.items():
            if len({e[1] for e in es}) >= 2:
                obs += [((key, y), e[1], e[2]) for e in es]
    n_h: dict[str, int] = {}
    for _, h, _ in obs:
        n_h[h] = n_h.get(h, 0) + 1
    obs = [o for o in obs if n_h[o[1]] >= min_obs]
    lv = {h: 0.0 for _, h, _ in obs}
    for _ in range(iters):
        cell: dict = {}
        for c, h, p in obs:
            cell.setdefault(c, []).append(p - lv[h])
        cm = {c: sum(v) / len(v) for c, v in cell.items()}
        acc: dict[str, list[float]] = {}
        for c, h, p in obs:
            acc.setdefault(h, []).append(p - cm[c])
        lv = {h: sum(v) / len(v) for h, v in acc.items()}
        m = sum(lv[h] for _, h, _ in obs) / max(1, len(obs))
        lv = {h: v - m for h, v in lv.items()}
    return lv


def units_from(lots: list[dict], cov: list[dict], cfg: dict, pair_kind: str = "all") -> list[dict]:
    """pair_kind: "all" (B126-2 as registered), "same" (adjacent events of one house),
    "cross" (adjacent events of two houses, each price net of its house's level)."""
    us = _units_from(lots, cov, cfg)
    if pair_kind == "all":
        return us
    lv = house_levels({(u["slug"], u["vintage"]): u["events"] for u in us})
    out = []
    for u in us:
        ev = u["events"]
        if pair_kind == "same":
            ph: dict[str, list] = {}
            for e in ev:
                ph.setdefault(e[1], []).append(e)
            pairs = [(abs(b[2] - a[2]), (b[0] - a[0]).days) for h in ph.values() for a, b in zip(h, h[1:])]
        else:
            pairs = [(abs((b[2] - lv[b[1]]) - (a[2] - lv[a[1]])), (b[0] - a[0]).days)
                     for a, b in zip(ev, ev[1:]) if a[1] != b[1] and a[1] in lv and b[1] in lv]
        out.append(dict(u, pairs=pairs))
    return out


_CLEAN_CACHE: dict = {}


def clean_lots(lots: list[dict], c: float) -> list[dict]:
    """Lots kept under the clean knob; see SCAN. Cached per (lots, c)."""
    key = (id(lots), c)
    if key in _CLEAN_CACHE:
        return _CLEAN_CACHE[key]
    if not c:
        _CLEAN_CACHE[key] = lots
        return lots
    by: dict[tuple, list[dict]] = {}
    for l in lots:
        if l.get("own_750_usd"):
            by.setdefault((l["slug"], l["vintage"], l["format_ml"]), []).append(l)
    keep = []
    for ls in by.values():
        for l in ls:
            # peers within a year either side only. A first version took every other-house lot
            # of the unit; on a thin unit that window spans a decade, so ordinary drift read as
            # a bad lot: at 2x it dropped 10.0 % of thin units' lots (median 3.7 years old)
            # against 7.4 % of thick units' (0.8 years), cutting into the jumps being measured.
            t = d(l["date"])
            o = [x["own_750_usd"] for x in ls if x["house"] != l["house"] and abs((d(x["date"]) - t).days) <= 365]
            if len(o) >= 3:
                r = l["own_750_usd"] / st.median(o)
                if r > c or r < 1 / c:
                    continue
            keep.append(l)
    _CLEAN_CACHE[key] = keep
    return keep


def _units_from(lots: list[dict], cov: list[dict], cfg: dict) -> list[dict]:
    site = {(c["slug"], c["vintage"]): c for c in cov}
    by: dict[tuple, list[dict]] = {}
    for l in clean_lots(lots, cfg.get("clean", 0.0)):
        if l["slug"] in EXCLUDE or l["format_conflict"] or not l["own_750_usd"]:
            continue
        if cfg["formats"] == "750" and l["format_ml"] != 750:
            continue
        by.setdefault((l["slug"], l["vintage"]), []).append(l)
    out = []
    for (slug, vint), rows in sorted(by.items()):
        ev, floor = events(rows)
        pairs = [(abs(b[2] - a[2]), (b[0] - a[0]).days) for a, b in zip(ev, ev[1:])]
        start = max(SITE_START, date(vint + cfg["lag"], 1, 1))
        years = max((FETCHED - start).days / 365.25, 0.5)
        n_site = site[(slug, vint)]["site_lots"] or len(rows)
        out.append({"slug": slug, "vintage": vint, "age": FETCHED.year - vint, "site_lots": n_site,
                    "years": years, "density": n_site / years, "pairs": pairs, "floor": floor,
                    "n_events": len(ev), "events": ev})
    return out


def corr(us: list[dict], key=lambda u: st.median(p[0] for p in u["pairs"])) -> tuple[float | None, int]:
    xs = [(u["density"], key(u)) for u in us if u["pairs"]]
    xs = [(a, b) for a, b in xs if b is not None]
    if len(xs) < 5:
        return None, len(xs)
    r = spearmanr([a for a, _ in xs], [b for _, b in xs]).statistic
    return (None if math.isnan(r) else float(r)), len(xs)


def cuts_of(values: list[float], fixed) -> tuple[float, float] | None:
    if fixed:
        return fixed
    if len(values) < 2:
        return None
    q = st.quantiles(values, n=3)
    return q[0], q[1]


def binned(us: list[dict], what: str, fixed, min_pairs: int) -> list[dict]:
    """Inside each bin, the B126-2 correlation again, units as observations."""
    names = ("short", "mid", "long") if what == "interval" else ("young", "mid", "old")
    vals = [g for u in us for _, g in u["pairs"]] if what == "interval" else [u["age"] for u in us]
    if cuts_of(vals, fixed) is None:
        return [{"bin": n, "cut": None, "rho": None, "units": 0} for n in names]
    if what == "interval":
        lo, hi = cuts_of(vals, fixed)
        out = []
        for name, test in (("short", lambda g: g < lo), ("mid", lambda g: lo <= g < hi), ("long", lambda g: g >= hi)):
            sub = []
            for u in us:
                ps = [p for p in u["pairs"] if test(p[1])]
                if len(ps) >= max(1, min_pairs // 2):
                    sub.append(dict(u, pairs=ps))
            r, n = corr(sub)
            out.append({"bin": name, "cut": [round(lo, 1), round(hi, 1)], "rho": r, "units": n})
        return out
    lo, hi = cuts_of(vals, fixed)
    out = []
    for name, test in (("young", lambda a: a < lo), ("mid", lambda a: lo <= a < hi), ("old", lambda a: a >= hi)):
        sub = [u for u in us if test(u["age"])]
        r, n = corr(sub)
        out.append({"bin": name, "cut": [round(lo, 1), round(hi, 1)], "rho": r, "units": n})
    return out


def sign(x):
    return None if x is None else (1 if x > 0 else -1 if x < 0 else 0)


def state_of(rhos: list[float | None]) -> str:
    """Three states, and a fourth for no object. Mapping printed with the verdict (`11c`)."""
    s = {sign(r) for r in rhos}
    if not rhos or s == {None}:
        return "no object"
    if s == {-1}:
        return "thinner units jump further at every scan point"
    if s == {1}:
        return "thinner units jump less at every scan point"
    return "sign moves across the scan"


VERDICT = {"thinner units jump further at every scan point": True,
           "thinner units jump less at every scan point": False,
           "sign moves across the scan": None,
           "no object": None}


def scan_of(lots, cov, kind: str) -> list[dict]:
    out = []
    for fm, lag, mp, cl in itertools.product(SCAN["formats"], SCAN["lag"], SCAN["min_pairs"], SCAN["clean"]):
        cfg = {"formats": fm, "lag": lag, "min_pairs": mp, "clean": cl}
        us = [u for u in units_from(lots, cov, cfg, kind) if len(u["pairs"]) >= mp]
        r, n = corr(us)
        jumps = [st.median(p[0] for p in u["pairs"]) for u in us]
        floors = [f for u in us for f in u["floor"]]
        out.append({"cfg": cfg, "rho": r, "units": n,
                    "median_jump": st.median(jumps) if jumps else None,
                    "floor": st.median(floors) if floors else None,
                    "zero_jump_share": (sum(1 for u in us for p in u["pairs"] if p[0] == 0)
                                        / max(1, sum(len(u["pairs"]) for u in us)))})
    return out


def bins_of(lots, cov, kind: str) -> tuple[dict, dict]:
    inter, age = {}, {}
    for fm, lag, mp, cl in itertools.product(SCAN["formats"], SCAN["lag"], SCAN["min_pairs"], SCAN["clean"]):
        cfg = {"formats": fm, "lag": lag, "min_pairs": mp, "clean": cl}
        us = [u for u in units_from(lots, cov, cfg, kind) if len(u["pairs"]) >= mp]
        for cn, fixed in INTERVAL_CUTS.items():
            inter[f"{fm}|{lag}|{mp}|{cl}|{cn}"] = binned(us, "interval", fixed, mp)
        for cn, fixed in AGE_CUTS.items():
            age[f"{fm}|{lag}|{mp}|{cl}|{cn}"] = binned(us, "age", fixed, mp)
    return inter, age


def bin_states(table: dict) -> dict:
    """One bin is (cut scheme, bin name). Its sign is read across the whole knob scan (`11f`):
    the same sign at every scan point where it has units, or it moves."""
    by: dict[tuple, list] = {}
    for k, bins in table.items():
        cn = k.split("|")[-1]
        for b in bins:
            by.setdefault(f"{cn}/{b['bin']}", []).append(b["rho"])
    out = {}
    for key, rs in by.items():
        s = {sign(r) for r in rs if r is not None}
        out[key] = {"rhos": rs, "state": "no units" if not s else ("moves" if len(s) > 1 else ("negative" if s == {-1} else "positive" if s == {1} else "zero"))}
    return out


def held(table: dict, main_sign) -> tuple:
    """Three states (`11c`), with the mapping:
      some bin holds the sign against the main one at every scan point  -> False
      every bin with a steady sign carries the main sign, at least one  -> True
      no bin has a steady sign, or there is no main sign                -> None
    A bin whose sign moves across the scan is not read (`11f`); it is counted and printed.
    A first version took any single bin at any single scan point against the sign as False;
    that read a bin of twenty units at one knob setting as a verdict on the whole reading.
    Returns (verdict, per-bin states)."""
    bs = bin_states(table)
    if main_sign is None:
        return None, bs
    want = "negative" if main_sign == -1 else "positive"
    steady = {k: v["state"] for k, v in bs.items() if v["state"] in ("negative", "positive", "zero")}
    if any(s != want for s in steady.values()):
        return False, bs
    return (True if steady else None), bs


SIGN_OF_STATE = {"thinner units jump further at every scan point": -1,
                 "thinner units jump less at every scan point": 1}


def scan_detail(scan) -> str:
    return "rho over the scan: " + ", ".join(
        f"{s['cfg']['formats']}/lag{s['cfg']['lag']}/k{s['cfg']['min_pairs']}/c{s['cfg']['clean']:g} {s['rho']:+.3f} (n={s['units']})"
        for s in scan if s["rho"] is not None)


def read(lots, cov, parse_checks) -> dict:
    blocks = {}
    for kind in ("all", "same", "cross"):
        scan = scan_of(lots, cov, kind)
        inter, age = bins_of(lots, cov, kind)
        state = state_of([s["rho"] for s in scan])
        blocks[kind] = {"scan": scan, "interval_bins": inter, "age_bins": age, "state": state,
                        "interval_held": held(inter, SIGN_OF_STATE.get(state)),
                        "age_held": held(age, SIGN_OF_STATE.get(state))}
    base = [u for u in units_from(lots, cov, dict(DEFAULT)) if len(u["pairs"]) >= DEFAULT["min_pairs"]]
    dens = sorted(u["density"] for u in base)
    t1, t2 = st.quantiles(dens, n=3)
    terc = []
    for name, test in (("thin", lambda x: x < t1), ("mid", lambda x: t1 <= x < t2), ("thick", lambda x: x >= t2)):
        sub = [u for u in base if test(u["density"])]
        terc.append({"tercile": name, "units": len(sub),
                     "density_range": [min(u["density"] for u in sub), max(u["density"] for u in sub)],
                     "median_unit_jump": st.median(st.median(p[0] for p in u["pairs"]) for u in sub),
                     "median_gap_days": st.median(g for u in sub for _, g in u["pairs"])})
    levels = house_levels({(u["slug"], u["vintage"]): u["events"] for u in _units_from(lots, cov, dict(DEFAULT))})

    a, s, c = blocks["all"], blocks["same"], blocks["cross"]
    floor_ratio = {k: [x["median_jump"] / x["floor"] if x["floor"] and x["median_jump"] is not None else None
                       for x in b["scan"]] for k, b in blocks.items()}
    unit_check = parse_checks["unit_check"]
    size_only = all(all(w.startswith("format ") for w in x["why"]) for x in parse_checks["html_json_mismatch"])

    def ctrl(b, what):
        v, bs = b[f"{what}_held"]
        parts = [f"{k}: {x['state']}" for k, x in sorted(bs.items())]
        return v, "per bin across the scan: " + "; ".join(parts)

    ih, idet = ctrl(a, "interval")
    ah, adet = ctrl(a, "age")
    cih, cidet = ctrl(c, "interval")
    cah, cadet = ctrl(c, "age")
    crit = [
        {"name": "B126-1", "kind": "instrument",
         "statement": "own 750 ml price agrees with the site's to $1 on every row, and every HTML/JSON disagreement is a tagged size conflict",
         "passed": (not unit_check) and size_only,
         "detail": f"unit gaps {len(unit_check)}; disagreements {len(parse_checks['html_json_mismatch'])}, all size conflicts: {size_only}"},
        {"name": "B126-2", "kind": "own_reading",
         "statement": "thinner units jump further: density and the unit median jump, all adjacent events, rank-correlate negatively",
         "passed": VERDICT[a["state"]], "state": a["state"], "state_map": VERDICT, "detail": scan_detail(a["scan"])},
        {"name": "B126-3", "kind": "instrument",
         "statement": "the median unit jump clears the same-day same-house floor at every scan point, for each pair kind that has pairs",
         "passed": (all(r > 1 for v in floor_ratio.values() for r in v if r is not None)
                    if any(r is not None for v in floor_ratio.values() for r in v) else None),
         "detail": "; ".join(f"{k}: " + ", ".join(f"{r:.2f}" for r in v if r is not None) for k, v in floor_ratio.items())},
        {"name": "B126-4", "kind": "own_reading",
         "statement": "inside interval bins, three cut schemes, whole scan, the B126-2 sign holds",
         "passed": ih, "detail": idet},
        {"name": "B126-6", "kind": "own_reading",
         "statement": "inside age bins, three cut schemes, whole scan, the B126-2 sign holds",
         "passed": ah, "detail": adet},
        {"name": "B126-7", "kind": "own_reading",
         "statement": "cross-house pairs, each price net of its house's level: thinner units jump further",
         "passed": VERDICT[c["state"]], "state": c["state"], "state_map": VERDICT, "detail": scan_detail(c["scan"])},
        {"name": "B126-7a", "kind": "own_reading",
         "statement": "B126-7 inside interval bins, three cut schemes, whole scan: the sign holds",
         "passed": cih, "detail": cidet},
        {"name": "B126-7b", "kind": "own_reading",
         "statement": "B126-7 inside age bins, three cut schemes, whole scan: the sign holds",
         "passed": cah, "detail": cadet},
        {"name": "B126-8", "kind": "own_reading",
         "statement": "same-house pairs (one house's consecutive sales of a unit): thinner units jump further",
         "passed": VERDICT[s["state"]], "state": s["state"], "state_map": VERDICT, "detail": scan_detail(s["scan"])},
        {"name": "B126-5", "kind": "bookkeeping",
         "statement": "units, not pairs, are the observations; units and pairs per unit printed",
         "passed": bool(base) and all(len(u["pairs"]) >= DEFAULT["min_pairs"] for u in base),
         "detail": f"default: {len(base)} units, pairs per unit median {st.median(len(u['pairs']) for u in base) if base else None}"},
    ]
    return {"blocks": blocks, "terciles": terc, "house_levels": levels, "criteria": crit,
            "units_default": [{"slug": u["slug"], "vintage": u["vintage"], "age": u["age"],
                               "site_lots": u["site_lots"], "density": u["density"], "pairs": len(u["pairs"]),
                               "median_jump": st.median(p[0] for p in u["pairs"]),
                               "median_gap_days": st.median(g for _, g in u["pairs"])} for u in base]}


def rnd(o):
    if isinstance(o, float):
        return float(f"{o:.6g}")
    if isinstance(o, dict):
        return {k: rnd(v) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v) for v in o]
    return o


def report(r: dict) -> None:
    for kind, b in r["blocks"].items():
        print(f"\n=== pairs: {kind}  ({b['state']})")
        print("scan (formats, lag, min pairs): rho, units, median unit jump, floor, share of zero jumps")
        for s in b["scan"]:
            c = s["cfg"]
            rho = f"{s['rho']:+.3f}" if s["rho"] is not None else "  n/a "
            fl = f"{s['floor']:.4f}" if s["floor"] is not None else "n/a"
            mj = f"{s['median_jump']:.4f}" if s["median_jump"] is not None else "n/a"
            print(f"  {c['formats']:>3} lag{c['lag']} k{c['min_pairs']} c{c['clean']:g}  rho {rho}  n {s['units']:>3}"
                  f"  jump {mj}  floor {fl}  zero {s['zero_jump_share']:.3f}")
        for title, tab in (("interval bins", b["interval_bins"]), ("age bins", b["age_bins"])):
            print(f"  {title}, default formats/lag/k, three cut schemes")
            for k, bins in tab.items():
                fm, lag, mp, cl, cn = k.split("|")
                if (fm, int(lag), int(mp), float(cl)) != (DEFAULT["formats"], DEFAULT["lag"], DEFAULT["min_pairs"], DEFAULT["clean"]):
                    continue
                print(f"    {cn:>12}: " + "  ".join(
                    f"{x['bin']} {('%+.3f' % x['rho']) if x['rho'] is not None else '  n/a '} (n={x['units']})" for x in bins))
    print("\ndensity terciles, all pairs, default config")
    for t in r["terciles"]:
        print(f"  {t['tercile']:>5}  units {t['units']:>3}  density {t['density_range'][0]:.2f}-{t['density_range'][1]:.2f}/yr"
              f"  median unit jump {t['median_unit_jump']:.4f}  median gap {t['median_gap_days']:.0f} d")
    print("\nhouse levels (log, default config): " + ", ".join(f"{h} {v:+.3f}" for h, v in sorted(r["house_levels"].items(), key=lambda x: x[1])))
    print("\ncriteria")
    for c in r["criteria"]:
        print(f"  {c['name']:7} {c['kind']:12} {c['passed']!s:5}  {c.get('state', '')}")
        print(f"          {c['detail'][:300]}")
    print(f"\nstate map for B126-2 (`11c`): {r['criteria'][1]['state_map']}")
    print(f"excluded wines: {EXCLUDE}")


def run() -> int:
    lots = json.loads((PARSED / "lots.json").read_text(encoding="utf-8"))
    cov = json.loads((PARSED / "coverage.json").read_text(encoding="utf-8"))
    checks = json.loads((PARSED / "checks.json").read_text(encoding="utf-8"))
    r = read(lots, cov, checks)
    report(r)
    rec = {"stage": "B126",
           "config": {"exclude": EXCLUDE, "site_start": str(SITE_START), "fetched": str(FETCHED),
                                      "default": DEFAULT, "scan": SCAN, "interval_cuts": {k: v for k, v in INTERVAL_CUTS.items()},
                                      "age_cuts": {k: v for k, v in AGE_CUTS.items()},
                                      "source": "data/b126/parsed/ via experiments/b126_parse.py"},
           **rnd(r)}
    OUT.write_text(json.dumps(rec, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT}")
    return 0


def selftest() -> int:
    """Seeded worlds. Each flag is fed a world where it has to turn (`11f`)."""
    import random

    def world(jump_of, age_of=lambda i: 10 + i % 30, n_units=60, sold=None):
        rnd_ = random.Random(1)
        lots, cov = [], []
        for i in range(n_units):
            dens_lots = 5 + i * 3 if sold is None else sold(i)
            cov.append({"slug": "w", "vintage": 2026 - age_of(i), "site_lots": dens_lots})
            p = 100.0
            for k in range(8):
                p *= math.exp(rnd_.choice([-1, 1]) * jump_of(i))
                lots.append({"slug": "w", "vintage": 2026 - age_of(i), "date": f"20{15 + k}-0{1 + i % 9}-1{k % 9}",
                             "house": "h", "own_750_usd": p, "format_ml": 750, "format_conflict": False})
                lots.append({"slug": "w", "vintage": 2026 - age_of(i), "date": f"20{15 + k}-0{1 + i % 9}-1{k % 9}",
                             "house": "h", "own_750_usd": p * 1.001, "format_ml": 750, "format_conflict": False})
        return lots, cov

    ok = {"unit_check": [], "html_json_mismatch": []}
    checks = []
    # thinner units jump further: unit i has site lots 5 + 3i, jump 0.5 / (1 + i)
    r = read(*world(lambda i: 0.5 / (1 + i)), ok)
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("thin-jumps-far world reads negative, B126-2 True", c["B126-2"]["passed"] is True))
    checks.append(("its jumps clear the 0.1 % floor, B126-3 True", c["B126-3"]["passed"] is True))
    r = read(*world(lambda i: 0.01 * (1 + i)), ok)
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("thin-jumps-less world reads positive, B126-2 False", c["B126-2"]["passed"] is False))
    r = read(*world(lambda i: 0.2), ok)
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("a world with no density effect does not read True", c["B126-2"]["passed"] is not True))
    # age drives both: old units are thin and jump far, but inside an age bin density does nothing
    age_of = lambda i: 5 + 10 * (i % 3)
    r = read(*world(lambda i: 0.05 * (1 + (i % 3)) * (1 + 0.001 * (i % 7)), age_of=age_of,
                    sold=lambda i: 300 // (1 + (i % 3)) + (i % 7)), ok)
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("an age-driven world does not pass B126-6 as a density effect", c["B126-6"]["passed"] is not True))
    bad = {"unit_check": [{"row": 0}], "html_json_mismatch": []}
    r = read(*world(lambda i: 0.5 / (1 + i)), bad)
    checks.append(("a unit price gap turns B126-1", r["criteria"][0]["passed"] is False))
    bad = {"unit_check": [], "html_json_mismatch": [{"why": ["quantity 6 vs '12'"]}]}
    r = read(*world(lambda i: 0.5 / (1 + i)), bad)
    checks.append(("a non-size disagreement turns B126-1", r["criteria"][0]["passed"] is False))
    def two_houses(true_jump, house_of, level):
        """Units whose events alternate between two houses inside one year; each house prints
        the true price times exp(level[house])."""
        rnd_ = random.Random(2)
        lots, cov = [], []
        for i in range(60):
            cov.append({"slug": "w", "vintage": 1990 + i % 30, "site_lots": 5 + 3 * i})
            p = 100.0
            for k in range(10):
                p *= math.exp(rnd_.choice([-1, 1]) * true_jump(i))
                h = house_of(i)[k % 2]
                lots.append({"slug": "w", "vintage": 1990 + i % 30, "date": f"2020-{1 + k:02d}-15", "house": h,
                             "own_750_usd": p * math.exp(level[h]), "format_ml": 750, "format_conflict": False})
        return lots, cov

    lv = {"h1": 0.0, "h2": 0.1, "h3": 0.6}
    r = read(*two_houses(lambda i: 0.5 / (1 + i), lambda i: ("h1", "h2"), lv), ok)
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("two-house world, true jumps larger when thin: B126-7 True", c["B126-7"]["passed"] is True))
    # thin units trade between h1 and h3 (level gap 0.6), thick between h1 and h2 (gap 0.1),
    # the true jump is the same everywhere: raw cross-house jumps fall with density, net of level they do not
    r = read(*two_houses(lambda i: 0.05, lambda i: ("h1", "h3") if i < 30 else ("h1", "h2"), lv), ok)
    c = {x["name"]: x for x in r["criteria"]}
    raw_cross = [x for x in r["blocks"]["cross"]["scan"]]
    checks.append(("a house-composition world does not pass B126-7 once levels are netted out",
                   c["B126-7"]["passed"] is not True))
    def lot(day, house, price):
        return {"slug": "w", "vintage": 2000, "format_ml": 750, "date": day, "house": house, "own_750_usd": price}
    drift = [lot("2014-01-01", "a", 100), lot("2014-02-01", "b", 100), lot("2014-03-01", "c", 100),
             lot("2014-04-01", "d", 100), lot("2024-01-01", "e", 250)]
    _CLEAN_CACHE.clear()
    checks.append(("cleaning keeps a price 2.5x its peers when the peers are ten years away",
                   len(clean_lots(drift, 2.0)) == 5))
    bad = drift + [lot("2014-02-15", "f", 800)]
    _CLEAN_CACHE.clear()
    kept = clean_lots(bad, 3.0)
    checks.append(("cleaning drops an 8x lot among same-year peers, and only it",
                   len(kept) == 5 and all(x["own_750_usd"] != 800 for x in kept)))
    _CLEAN_CACHE.clear()
    tab = {"750|2|3|0|t": [{"bin": "a", "rho": -0.3}, {"bin": "b", "rho": 0.2}],
           "all|2|3|0|t": [{"bin": "a", "rho": -0.2}, {"bin": "b", "rho": -0.1}]}
    checks.append(("a bin moving across the scan is unread, a steady bin with the sign reads True",
                   held(tab, -1)[0] is True))
    tab["all|2|3|0|t"][1]["rho"] = 0.1
    checks.append(("a bin steady against the sign at every scan point reads False", held(tab, -1)[0] is False))
    tab = {"750|2|3|0|t": [{"bin": "a", "rho": -0.3}], "all|2|3|0|t": [{"bin": "a", "rho": 0.3}]}
    checks.append(("only moving bins: no verdict", held(tab, -1)[0] is None))
    checks.append(("the state map sends the moving sign to no verdict",
                   VERDICT["sign moves across the scan"] is None and VERDICT["no object"] is None))
    for name, good in checks:
        print(f"{'PASS' if good else 'FAIL'}  {name}")
    return 0 if all(g for _, g in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    return selftest() if ap.parse_args().selftest else run()


if __name__ == "__main__":
    sys.exit(main())
