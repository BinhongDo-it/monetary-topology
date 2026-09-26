"""B120 readings, part one: each locked-price plan's price and base date, and the stock's price where the plan ended.

**What this reads.** The plans `b120_plans.py` builds from the census cache, and the daily bars `b120_bars.py` added to
the B110 store. A compact copy of the bars the plans need sits in `data/cache/b120_bars.npz`, rebuilt when one of
those store files changes name, size or modification second. This part prints the objects; it reads no criterion and
writes nothing under `results/`.

**The frame, per plan.**

- *The base date B and the price P.* From 2020-02-14 a locked price may not be below 80% of VWAP20 on the base date:
  the amount over the volume of the 20 days the stock traded before B, a day before an adjustment taken at its
  adjusted price (B110's `vwap_before`, in the price basis of the last market day before B). The candidates for B are
  the plan's first locked document's day, each calendar base date its documents read, and each plan document assigned
  to it that does not read first-day pricing; the candidates for P are the prices per share its documents read. The
  pair read is the candidate price nearest the floor at a candidate base date, as a gap in ticks of 0.01 yuan; a tie
  goes to the first locked document, then the earlier day, then the lower price. The gap at the first locked document
  alone is kept beside it.
- *The price carried to a later day*, by the agreements' formula: on a day whose adjustment factor (the close before
  over the day's reference price) is below 1.05 the cash per share, the close before less the reference price, comes
  off the price; on a day with a larger factor, a split, the price is divided by the factor. To an earlier day the same
  steps are undone.
- *The end t* (for a plan moved to first-day pricing, the announcement of the move). The close of the last day the
  stock traded before t and of the first day it traded on or after t, each with the calendar days between it and t,
  and M before and M on or after t: each close over the price carried to its day. A close more than 10 days before t
  is named as stale.
- *For an issued plan*, the B110 table's issue price against the price carried to the issue day, in ticks.

A plan whose documents read no price is given the rule's price, 80% of VWAP20 on its first locked document's day
rounded up to the tick, and named apart; its gap is zero by construction, so it stays out of the price-against-floor
count. A plan with no bars (the Beijing exchange), or with no price read and no VWAP20 on that day, or with fewer than
20 traded days before every candidate base date, is named with its reason and read no further. A close on or after the
end more than 10 days after it is named as late, and the security list's delisting date is kept beside each plan.

**Part two** reads two things off that frame and prints them, still without a verdict.

- *Where each price comes from*, in this order: within a tick of the floor at the base date read; above the floor with
  a document of the plan naming 每股净资产, the net assets a bank or an insurer may not price below; within a tick of
  the B110 table's issue price carried to the issue day; within a tick of the floor of some other market day of the
  plan's life, that day named; a price another plan of the same company reads at its own floor; or not confirmed.
- *Where each plan ended*, with one end the plans script cannot see: a plan still pending whose stock the security
  list shows delisted ended when the stock last traded. The ends are grouped into issued at the locked price, the lock
  given up (bids or first-day pricing), ended, ended in review, re-locked or replaced, the stock delisted, and pending.

M is then binned and the groups counted in each bin, over the plans whose price is confirmed, again over those at the
floor alone, and again with the close on or after the end. The days from the first document to the end are printed by
bin beside them, since a plan that ran longer had more time for the price to move either way.

**Part three** cuts the same table three ways. A plan whose documents' titles name a related party (关联交易, 控股股东,
实际控制人) is set against the rest: the rules name three classes a locked price may be sold to, and only the
related-party marker is readable here, so that is what is cut. Then the plans are grouped by how long they ran and by
the year they started, since a plan that ran longer had more time for the price to move. Last, the plans moved to
first-day pricing in the summer of 2026 are printed one by one, and M is taken for them and for the locked plans still
live beside them on one day before the first of those moves.

**Part four** puts a number on what walking away was worth. A plan that did not issue would have handed the new holder
`n N (Pm - P) / (N + n)` on the day it ended, the same transfer B110 reads on the issues that did happen. `n` is read
from the plan's own documents, the cap on the shares or the cap on the money over the price; `N` is not in any table
for a plan that never issued, so the transfer is printed as a band: the rules cap the shares at 30% of the shares
before the issue, so `n N / (N + n)` lies between `n / 1.3` and `n`. The issues that did happen are counted with the
table's own `n` and `N`, and B110-4's locked-cash column is recomputed here from the offering table and the full bar
store and set against the number in B110's record.

**Part five** reads the criteria off all of that and writes the record. B120-1 asks whether the rule pins the price,
B120-2 whether each plan holds one end and each completed locked placement finds its plan, B120-3 whether the share
that issued rises with M by more than a shuffle of the labels reaches, B120-4 what the plans that did not issue would
have handed over, B120-5 the batch moved to first-day pricing, B120-6 the coverage table, and B120-7 B110-4's own
column recomputed here. Every flag is read off the objects, and the selftest seeds each one with an input that has to
make it fail.

    python experiments/b120_readings.py --selftest
    python experiments/b120_readings.py --frame
    python experiments/b120_readings.py --tables
    python experiments/b120_readings.py --splits
    python experiments/b120_readings.py --money
    python experiments/b120_readings.py --criteria
    python experiments/b120_readings.py --record
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import datetime as dt
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b110_placements as B110  # noqa: E402
import b120_fetch as F  # noqa: E402
import b120_plans as B  # noqa: E402
import b120_probe as P  # noqa: E402

FLOOR = 0.8
TICK = 0.01
STALE_DAYS = 10
BARS_CACHE = P.ROOT / "data" / "cache" / "b120_bars.npz"
STATES = ("read", "price from the rule", "no bars", "no price read", "no VWAP20 at any candidate base date")
MEASURED = ("read", "price from the rule")
GAP_BINS = ((-math.inf, -100.0, "100 ticks or more below"), (-100.0, -10.0, "10 to 100 below"), (-10.0, -1.0, "1 to 10 below"),
            (-1.0, 1.0, "within a tick"), (1.0, 10.0, "1 to 10 above"), (10.0, 100.0, "10 to 100 above"),
            (100.0, math.inf, "100 ticks or more above"))
NET_ASSET = "每股净资产"
SCAN_DAYS = 250
PRICE_STATES = ("at the floor", "the floor with net assets named", "the issue price agrees", "the floor of another day",
                "a price of another plan of this company", "not confirmed", "from the rule")
M_BINS = ((0.0, 0.70), (0.70, 0.85), (0.85, 1.00), (1.00, 1.20), (1.20, 1.50), (1.50, 2.00), (2.00, math.inf))
GROUPS = {"issued": "issued at the locked price", "issued by bids": "the lock given up", "moved to first day": "the lock given up",
          "plan ended": "ended", "plan lapsed": "ended", "application withdrawn": "ended", "subscribers exited": "ended",
          "review ended": "ended in review", "review refused": "ended in review", "re-locked on a new base date": "re-locked or replaced",
          "new locked plan": "re-locked or replaced", "new plan": "re-locked or replaced", "stock delisted": "the stock delisted",
          "pending": "pending", "review ended, offering not named": "ended in review", "voted down": "ended"}
GROUP_ORDER = ("issued at the locked price", "the lock given up", "ended", "ended in review", "re-locked or replaced",
               "the stock delisted", "pending")
WALKED = ("ended", "ended in review", "the stock delisted")
YI = 1e8
SHARE_CAP_RULE = 0.30  # 《上市公司证券发行注册管理办法》第五十五条: the shares issued may not pass 30% of the shares before the issue
B110_RECORD = P.ROOT / "results" / "b110_placements.json"
NUM_CN = r"([0-9][0-9,，]*(?:\.[0-9]+)?)"
UNITS = {"": 1.0, "万": 1e4, "亿": 1e8}
SHARES_CAP = re.compile(r"(?:发行|认购)(?:的)?(?:股票|股份|A股)?(?:的)?(?:数量|股数)[^。；]{0,30}?不超过" + NUM_CN + r"([万亿]?)股")
MONEY_CAP = re.compile(r"(?:募集|认购)(?:资金)?(?:总额|金额|总金额|规模)[^。；]{0,30}?不超过(?:人民币)?" + NUM_CN + r"([万亿]?)元")
RATIO_CAP = re.compile(r"不超过[^。；]{0,20}?(?:本次)?发行前(?:公司)?(?:股份)?总股本的" + NUM_CN + r"%")
RELATED_WORDS = ("关联交易", "控股股东", "实际控制人")
DURATIONS = ((0, 180), (181, 365), (366, 730), (731, math.inf))


def gap_bin(g: float) -> str:
    for lo, hi, label in GAP_BINS:
        if (lo < g < hi) if label == "within a tick" else (lo < g <= hi if hi < 0 else lo <= g < hi):
            return label
    return GAP_BINS[-1][2]


def row_before(series: dict, day: dt.date) -> int:
    """Index of the first row on or after `day`: the rows before it are the market days before `day`."""
    return int(np.searchsorted(series["ordinal"], day.toordinal(), side="left"))


def vwap20(series: dict, day: dt.date) -> float | None:
    r = row_before(series, day)
    if r == 0:
        return None
    return B110.vwap_before(series, r, B110.VWAP_DAYS, r - 1)


def carry(series: dict, price: float, r0: int, r1: int, split: float = B110.SPLIT_FACTOR) -> float:
    """`price`, stated in the basis of row r0, carried through the adjustment days r0+1..r1; back through r1+1..r0
    when r1 is the earlier row."""
    f = series["factor"]
    rows = range(r0 + 1, r1 + 1) if r1 >= r0 else range(r0, r1, -1)
    sign = 1 if r1 >= r0 else -1
    for r in rows:
        if f[r] == 1.0:
            continue
        if f[r] < split:
            price -= sign * float(series["close"][r - 1] - series["preclose"][r])
        else:
            price = price / float(f[r]) if sign > 0 else price * float(f[r])
    return price


def candidates(p: dict, doc_day: dict, doc_state: dict) -> list[tuple[dt.date, str]]:
    out = {p["b"]: "first locked document"}
    for d in p.get("base_days", []):
        out.setdefault(d, "calendar base date read")
    for i in p.get("documents", []):
        if i in doc_day and doc_state.get(i) != "first day":
            out.setdefault(doc_day[i], "plan document")
    return sorted(out.items())


def pin(series: dict, p: dict, cands: list[tuple[dt.date, str]]) -> dict | None:
    """The candidate (base date, price) nearest the floor, with the gap at the first locked document alone."""
    best, at_b = None, None
    for day, label in cands:
        v = vwap20(series, day)
        if v is None:
            continue
        for x in p["prices"]:
            gap = (x - FLOOR * v) / TICK
            key = (abs(gap), day != p["b"], day, x)
            if best is None or key < best["key"]:
                best = {"key": key, "B": day, "label": label, "P": x, "vwap20": v, "gap": gap}
            if day == p["b"] and (at_b is None or abs(gap) < abs(at_b)):
                at_b = gap
    if best is None:
        return None
    best.pop("key")
    best["gap_at_b"] = at_b
    return best


def around(series: dict, day: dt.date) -> tuple[int | None, int | None]:
    """The last traded row before `day` and the first traded row on or after it."""
    traded = series["traded"]
    i = int(np.searchsorted(series["ordinal"][traded], day.toordinal(), side="left"))
    return (int(traded[i - 1]) if i > 0 else None), (int(traded[i]) if i < len(traded) else None)


def side(series: dict, row: int | None, day: dt.date, price: float, r0: int) -> dict:
    if row is None:
        return {"day": None, "close": None, "days": None, "carried": None, "M": None}
    d = dt.date.fromordinal(int(series["ordinal"][row]))
    carried = carry(series, price, r0, row)
    close = float(series["close"][row])
    return {"day": d, "close": close, "days": abs((d - day).days), "carried": carried,
            "M": close / carried if carried else None}


def rule_price(v: float) -> float:
    return math.ceil(round(FLOOR * v / TICK, 6)) * TICK


def read_plan(p: dict, bars, doc_day: dict, doc_state: dict, out_date: str | None = None) -> dict:
    o = {"id": f"{p['code']}:{p['b'].isoformat()}", "code": p["code"], "name": p["name"], "outcome": p["outcome"], "b": p["b"],
         "t": p["t"], "then": p["then"][0] if p.get("then") else None, "prices": list(p["prices"]), "state": "read",
         "out_date": out_date or None}
    series = bars.series(p["code"])
    if series is None:
        o["state"] = "no bars"
        return o
    if not p["prices"]:
        v = vwap20(series, p["b"])
        if v is None:
            o["state"] = "no price read"
            return o
        x = rule_price(v)
        o.update(state="price from the rule", candidates=1, B=p["b"], label="first locked document", P=round(x, 2), vwap20=v,
                 gap=(x - FLOOR * v) / TICK)
        o["gap_at_b"] = o["gap"]
    else:
        cands = candidates(p, doc_day, doc_state)
        o["candidates"] = len(cands)
        got = pin(series, p, cands)
        if got is None:
            o["state"] = "no VWAP20 at any candidate base date"
            return o
        o.update(got)
    r0 = row_before(series, o["B"]) - 1
    before, on = around(series, p["t"])
    o["before"] = side(series, before, p["t"], o["P"], r0)
    o["on"] = side(series, on, p["t"], o["P"], r0)
    o["stale"] = o["before"]["days"] is not None and o["before"]["days"] > STALE_DAYS
    o["late"] = o["on"]["days"] is not None and o["on"]["days"] > STALE_DAYS
    if p["outcome"] == "issued":
        try:
            table = float(p["detail"]["P"])
        except (KeyError, TypeError, ValueError):
            table = None
        rT = int(np.searchsorted(series["ordinal"], p["t"].toordinal(), side="right")) - 1
        c = carry(series, o["P"], r0, rT) if table is not None and rT >= r0 else None
        o["issue"] = {"table": table, "carried": c, "gap": (table - c) / TICK if c is not None else None}
    return o


def frame(plans: list[dict], bars, doc_day: dict, doc_state: dict, basic: dict | None = None) -> list[dict]:
    basic = basic or {}
    return [read_plan(p, bars, doc_day, doc_state, (basic.get(p["code"]) or (None, None))[1])
            for p in sorted(plans, key=lambda p: (p["code"], p["b"]))]


def load(rebuild: bool = False) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        built = B.build(write=False)
    plans = built["plans"]
    doc_day = {det["id"]: d for evs in built["events"].values() for d, k, det in evs if k == "plan document"}
    doc_state = {a["id"]: a["state"] for a in built["read"] if a["cls"] == "plan document"}
    codes = sorted({p["code"] for p in plans})
    files = [f for f in B110.store_files() if f.stem in set(codes)]
    bars, note = B110.load_bars(files, cache=BARS_CACHE, rebuild=rebuild)
    basic, basic_note = B110.F.load_basic(network=False, refresh=False, delay=0.0, day="", repair=False)
    texts = built["texts"]
    fr = frame(plans, bars, doc_day, doc_state, basic)
    title = {a["id"]: a["title"] for a in built["read"]}
    day_of = {a["id"]: a["day"] for a in built["read"]}
    net, titles = {}, {}
    for p in plans:
        ids = list(p["agreements"]) + list(p["documents"])
        key = f"{p['code']}:{p['b'].isoformat()}"
        net[key] = any(NET_ASSET in (texts.get(i) or "") for i in ids)
        titles[key] = [title.get(i, "") for i in ids]
    sizes = {}
    for p in plans:
        key = f"{p['code']}:{p['b'].isoformat()}"
        ids = sorted(set(list(p["agreements"]) + list(p["documents"])), key=lambda i: (day_of.get(i) or dt.date.max, i))
        got = {"shares": None, "money": None, "ratio": None}
        for i in ids:
            t = texts.get(i)
            if not t:
                continue
            one = deal_size(B.flat(t))
            for k in got:
                if got[k] is None:
                    got[k] = one[k]
        sizes[key] = got
    for o in fr:
        o["net_asset"] = net.get(o["id"], False)
        o["titles"] = titles.get(o["id"], [])
    return {"plans": plans, "bars": bars, "bars_note": note, "files": files, "codes": codes, "basic_note": basic_note, "frame": fr,
            "sizes": sizes, "seo_rows": (B110.F.snapshot_on_disk("RPT_SEO_DETAIL") or {"rows": []})["rows"], "built": built}


def quantiles(xs: list[float], qs=(0.1, 0.5, 0.9)) -> str:
    if not xs:
        return "none"
    a = np.sort(np.array(xs, dtype=float))
    return ", ".join(f"{int(q * 100)}th {float(np.quantile(a, q)):.4f}" for q in qs)


def show(o: dict) -> str:
    base = f"{o['code']} {o['name']} b {o['b']} {o['outcome']}"
    if o["state"] != "read":
        return f"{base}: {o['state']}"
    return (f"{base}; B {o['B']} ({o['label']}) P {o['P']} of {o['prices'][:4]}, VWAP20 {o['vwap20']:.4f}, floor {FLOOR * o['vwap20']:.4f}, "
            f"gap {o['gap']:+.2f} ticks (at the first locked document {o['gap_at_b']:+.2f})" if o["gap_at_b"] is not None else
            f"{base}; B {o['B']} ({o['label']}) P {o['P']} of {o['prices'][:4]}, VWAP20 {o['vwap20']:.4f}, floor {FLOOR * o['vwap20']:.4f}, "
            f"gap {o['gap']:+.2f} ticks (no VWAP20 at the first locked document)")


def report(data: dict) -> int:
    fr, plans = data["frame"], data["plans"]
    print(f"== 0. inputs: {len(plans)} plans, {len(data['codes'])} stocks; bars: {data['bars_note']}; store files for them {len(data['files'])}; "
          f"security list: {data['basic_note']}")
    states = collections.Counter(o["state"] for o in fr)
    print(f"   by state: {dict(sorted(states.items()))}")
    for s in STATES[2:]:
        named = [o for o in fr if o["state"] == s]
        if named:
            print(f"   {s}: " + "; ".join(f"{o['code']} {o['name']} b {o['b']} {o['outcome']}" for o in named[:12]))
    rd = [o for o in fr if o["state"] == "read"]

    print(f"\n== 1. the price against the floor, 80% of VWAP20 on the base date: {len(rd)} plans read (a preview of B120-1, no verdict)")
    bins = collections.Counter(gap_bin(o["gap"]) for o in rd)
    print("   gap at the pair read: " + ", ".join(f"{label} {bins.get(label, 0)}" for _, _, label in GAP_BINS))
    at_b = [o for o in rd if o["gap_at_b"] is not None]
    bins_b = collections.Counter(gap_bin(o["gap_at_b"]) for o in at_b)
    print(f"   gap at the first locked document alone ({len(at_b)} with a VWAP20 there): "
          + ", ".join(f"{label} {bins_b.get(label, 0)}" for _, _, label in GAP_BINS))
    print(f"   base date of the pair read: {dict(collections.Counter(o['label'] for o in rd))}; plans with more than one price read "
          f"{sum(1 for o in rd if len(o['prices']) > 1)}; with more than one candidate base date {sum(1 for o in rd if o['candidates'] > 1)}")
    by_year = collections.defaultdict(collections.Counter)
    for o in rd:
        by_year[o["B"].year][gap_bin(o["gap"])] += 1
    for y in sorted(by_year):
        c = by_year[y]
        print(f"     {y}: within a tick {c.get('within a tick', 0)}, above {sum(v for k, v in c.items() if 'above' in k)}, "
              f"below {sum(v for k, v in c.items() if 'below' in k)}")
    below = sorted([o for o in rd if o["gap"] <= -1.0], key=lambda o: o["gap"])
    above = sorted([o for o in rd if o["gap"] >= 1.0], key=lambda o: -o["gap"])
    print(f"   below the floor by a tick or more, {len(below)}; the furthest 10:")
    for o in below[:10]:
        print(f"      {show(o)}")
    print(f"   above the floor by a tick or more, {len(above)}; the furthest 10:")
    for o in above[:10]:
        print(f"      {show(o)}")
    moved_b = [o for o in rd if o["B"] != o["b"]]
    print(f"   pairs read at a base date other than the first locked document, {len(moved_b)}; a spread of 8:")
    for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in moved_b], 8):
        print(f"      {show(o)}")

    iss = [o for o in rd if o.get("issue") and o["issue"]["gap"] is not None]
    print(f"\n== 2. issued plans: the B110 table's issue price against the plan's price carried to the issue day, {len(iss)} "
          f"of {sum(1 for o in rd if o['outcome'] == 'issued')} read")
    ib = collections.Counter(gap_bin(o["issue"]["gap"]) for o in iss)
    print("   gap: " + ", ".join(f"{label} {ib.get(label, 0)}" for _, _, label in GAP_BINS))
    far = sorted([o for o in iss if abs(o["issue"]["gap"]) >= 1.0], key=lambda o: -abs(o["issue"]["gap"]))
    print(f"   a tick or more apart, {len(far)}; the furthest 12:")
    for o in far[:12]:
        print(f"      {o['code']} {o['name']} B {o['B']} P {o['P']} carried {o['issue']['carried']:.4f} table {o['issue']['table']} "
              f"gap {o['issue']['gap']:+.2f} (floor gap {o['gap']:+.2f})")

    rule = [o for o in fr if o["state"] == "price from the rule"]
    print(f"\n   no price read, the rule's price used: {len(rule)}; by outcome {dict(collections.Counter(o['outcome'] for o in rule))}")
    for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in rule], 6):
        print(f"      {o['code']} {o['name']} b {o['b']} {o['outcome']}: VWAP20 {o['vwap20']:.4f}, rule price {o['P']}")
    rule_iss = [o for o in rule if o.get("issue") and o["issue"]["gap"] is not None]
    rb = collections.Counter(gap_bin(o["issue"]["gap"]) for o in rule_iss)
    print(f"   of them issued, the table's price against the rule's price carried to the issue day, {len(rule_iss)}: "
          + ", ".join(f"{label} {rb.get(label, 0)}" for _, _, label in GAP_BINS))

    ms = [o for o in fr if o["state"] in MEASURED]
    print(f"\n== 3. the stock's price where each plan ended, M = close over the price carried to that day: {len(ms)} plans "
          f"({len(rd)} with a price read, {len(rule)} with the rule's price)")
    for oc in B.OUTCOMES:
        xs = [o for o in ms if o["outcome"] == oc]
        if not xs:
            continue
        mb = [o["before"]["M"] for o in xs if o["before"]["M"] is not None]
        mo = [o["on"]["M"] for o in xs if o["on"]["M"] is not None]
        print(f"   {oc}: {len(xs)}; M before t {quantiles(mb)}, below 1 {sum(1 for m in mb if m < 1)}; "
              f"M on or after t {quantiles(mo)}; stale closes {sum(1 for o in xs if o['stale'])}; late closes {sum(1 for o in xs if o['late'])}; "
              f"no close on or after t in the bars {sum(1 for o in xs if o['on']['day'] is None)}")
    stale = sorted([o for o in ms if o["stale"]], key=lambda o: -o["before"]["days"])
    print(f"   stale: the last close more than {STALE_DAYS} days before t, {len(stale)}:")
    for o in stale:
        print(f"      {o['code']} {o['name']} {o['outcome']} t {o['t']} last traded {o['before']['day']} ({o['before']['days']} days); "
              f"delisted in the security list {o['out_date']}")
    late = sorted([o for o in ms if o["late"]], key=lambda o: -o["on"]["days"])
    print(f"   late: the first close on or after t more than {STALE_DAYS} days after it, {len(late)}:")
    for o in late:
        print(f"      {o['code']} {o['name']} {o['outcome']} t {o['t']} next traded {o['on']['day']} ({o['on']['days']} days)")
    gone = [o for o in fr if o["outcome"] == "pending" and o["out_date"]]
    print(f"   pending plans whose stock the security list shows delisted, {len(gone)}: "
          + "; ".join(f"{o['code']} {o['name']} {o['out_date']}" for o in gone))

    print("\n== 4. a spread of plans in each outcome")
    for oc in B.OUTCOMES:
        xs = [o for o in ms if o["outcome"] == oc]
        for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in xs], 5):
            bf, on = o["before"], o["on"]
            print(f"   {oc}: {o['code']} {o['name']} B {o['B']} P {o['P']} gap {o['gap']:+.1f}; t {o['t']}: before {bf['day']} close "
                  f"{bf['close']} carried {bf['carried'] if bf['carried'] is None else round(bf['carried'], 4)} M "
                  f"{bf['M'] if bf['M'] is None else round(bf['M'], 4)}; on {on['day']} M {on['M'] if on['M'] is None else round(on['M'], 4)}")
    return 0


# ---------------------------------------------------------------------------
# Part two: where each price comes from, where each plan ended, and M by bin
# ---------------------------------------------------------------------------

def m_bin(m: float | None) -> str | None:
    if m is None:
        return None
    for lo, hi in M_BINS:
        if lo <= m < hi:
            return f"{lo:.2f} to {hi:.2f}" if hi < math.inf else f"{lo:.2f} and above"
    return f"below {M_BINS[0][0]:.2f}"


def floor_day(series: dict, price: float, r_lo: int, r_hi: int) -> tuple[dt.date | None, int]:
    """The first market day in rows r_lo..r_hi whose floor is within a tick of `price`, and how many days are."""
    first, n = None, 0
    for r in range(max(r_lo, B110.VWAP_DAYS), min(r_hi, len(series["ordinal"]) - 1) + 1):
        v = B110.vwap_before(series, r, B110.VWAP_DAYS, r - 1)
        if v is not None and abs(price - FLOOR * v) < TICK:
            n += 1
            if first is None:
                first = dt.date.fromordinal(int(series["ordinal"][r]))
    return first, n


def price_state(o: dict, net_asset: bool, others: list[dict], series: dict | None = None) -> tuple[str, str]:
    """Where the price read comes from, and what says so. The tests run in this order."""
    if o["state"] == "price from the rule":
        return "from the rule", f"80% of VWAP20 on {o['B']} rounded up"
    if abs(o["gap"]) < 1.0:
        return "at the floor", f"{o['gap']:+.2f} ticks at {o['B']}"
    if net_asset and o["gap"] >= 1.0:
        return "the floor with net assets named", f"{NET_ASSET} in a document of the plan, {o['gap']:+.2f} ticks over the floor"
    if o.get("issue") and o["issue"]["gap"] is not None and abs(o["issue"]["gap"]) < 1.0:
        return "the issue price agrees", f"the table's {o['issue']['table']} against {o['issue']['carried']:.4f} carried"
    if series is not None:
        r_hi = int(np.searchsorted(series["ordinal"], o["t"].toordinal(), side="right")) - 1
        day, n = floor_day(series, o["P"], row_before(series, o["b"]) - SCAN_DAYS, r_hi)
        if day is not None:
            return "the floor of another day", f"the floor on {day} ({n} days in the plan's life), {(day - o['b']).days:+d} days from the first document"
    same = [q for q in others if q["id"] != o["id"] and o["P"] in q["prices"] and q.get("gap") is not None and abs(q["gap"]) < 1.0]
    if same:
        return "a price of another plan of this company", f"the price of the plan starting {same[0]['b']}, at its own floor"
    return "not confirmed", f"{o['gap']:+.2f} ticks at {o['B']}, price over the close on the base date {o.get('P_over_close')}"


def end_of(o: dict) -> str:
    """The end read: a plan still pending whose stock is off the security list ended when the stock last traded."""
    return "stock delisted" if o["outcome"] == "pending" and o["out_date"] else o["outcome"]


def read_more(fr: list[dict], bars) -> None:
    """Adds the price state, the end read and the M bins to each plan of the frame."""
    by_code = collections.defaultdict(list)
    for o in fr:
        by_code[o["code"]].append(o)
    for o in fr:
        o["end"] = end_of(o)
        o["related"] = related_party(o.get("titles", []))
        if o["state"] not in MEASURED:
            continue
        series = bars.series(o["code"])
        row = row_before(series, o["B"])
        o["P_over_close"] = round(o["P"] / float(series["close"][row - 1]), 4) if row else None
        o["price_state"], o["price_why"] = price_state(o, o.get("net_asset", False), by_code[o["code"]], series)
        o["M"], o["M_on"] = o["before"]["M"], o["on"]["M"]
        o["bin"], o["bin_on"] = m_bin(o["M"]), m_bin(o["M_on"])
        o["days"] = (o["t"] - o["b"]).days


def bin_table(rows: list[dict], key: str = "bin") -> list[tuple[str, int, dict, float | None]]:
    """Per M bin: the plans in it, the count by group, and the median days from the first document to the end."""
    out = []
    for lo, hi in M_BINS:
        label = f"{lo:.2f} to {hi:.2f}" if hi < math.inf else f"{lo:.2f} and above"
        xs = [o for o in rows if o.get(key) == label]
        days = sorted(o["days"] for o in xs)
        out.append((label, len(xs), collections.Counter(GROUPS[o["end"]] for o in xs), days[len(days) // 2] if days else None))
    return out


def print_bins(title: str, rows: list[dict], key: str = "bin") -> None:
    print(f"   {title}: {len(rows)} plans")
    head = "      bin          n   " + "  ".join(f"{g[:22]:>22}" for g in GROUP_ORDER) + "      days"
    print(head)
    for label, n, c, days in bin_table(rows, key):
        cells = "  ".join(f"{(str(c.get(g, 0)) + ' ' + (f'{c.get(g, 0) / n * 100:.0f}%' if n else '')):>22}" for g in GROUP_ORDER)
        print(f"      {label:<12} {n:>3}   {cells}   {days if days is not None else '':>7}")


def tables(data: dict) -> int:
    fr = data["frame"]
    read_more(fr, data["bars"])
    ms = [o for o in fr if o["state"] in MEASURED]
    print(f"== 5. where each price comes from: {len(ms)} plans read")
    st = collections.Counter(o["price_state"] for o in ms)
    for s in PRICE_STATES:
        print(f"   {s}: {st.get(s, 0)}")
    for s in ("the floor with net assets named", "the issue price agrees", "the floor of another day",
              "a price of another plan of this company", "not confirmed"):
        xs = [o for o in ms if o["price_state"] == s]
        for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in xs], 8 if s != "not confirmed" else 20):
            print(f"      {s}: {o['code']} {o['name']} b {o['b']} {o['outcome']} P {o['P']} of {o['prices'][:3]}; {o['price_why']}")

    print("\n== 6. where each plan ended, the ends the plans script reads plus the delistings")
    ends = collections.Counter(o["end"] for o in fr)
    print(f"   ends: {dict(sorted(ends.items(), key=lambda kv: -kv[1]))}")
    print(f"   groups: {dict(collections.Counter(GROUPS[o['end']] for o in fr))}")
    gone = [o for o in fr if o["end"] == "stock delisted"]
    print(f"   pending plans whose stock is off the security list, read as ended when the stock last traded: {len(gone)}")
    for o in sorted(gone, key=lambda o: o["out_date"]):
        last = o["before"]["day"] if o["state"] in MEASURED else None
        print(f"      {o['code']} {o['name']} b {o['b']} delisted {o['out_date']}, last traded {last}, "
              f"M {round(o['M'], 4) if o.get('M') else None}")

    ok = [o for o in ms if o["price_state"] != "not confirmed" and o.get("bin")]
    print("\n== 7. M by bin and the end group, plans whose price is confirmed")
    print_bins("M from the close before the end", ok)
    print_bins("M from the close on or after the end", [o for o in ok if o.get("bin_on")], "bin_on")
    print_bins("only the plans whose price sits at the floor", [o for o in ok if o["price_state"] == "at the floor"])
    print_bins("only the plans whose price comes from the rule", [o for o in ok if o["price_state"] == "from the rule"])
    left = [o for o in ms if o["price_state"] == "not confirmed" and o.get("bin")]
    print_bins("the plans left out, whose price is not confirmed", left)
    print(f"   plans read with no M: {sum(1 for o in ms if not o.get('bin'))}")
    return 0


# ---------------------------------------------------------------------------
# Part three: the subscriber side, how long the plan ran, and the 2026 batch
# ---------------------------------------------------------------------------

def related_party(titles: list[str]) -> bool:
    """A placement to the controlling shareholder or one of its affiliates is a related-party transaction, and the
    announcement's title says so."""
    return any(w in (t or "") for t in titles for w in RELATED_WORDS)


def duration_bucket(days: int) -> str:
    for lo, hi in DURATIONS:
        if lo <= days <= hi:
            return f"{lo} to {hi} days" if hi < math.inf else f"{lo} days and more"
    return "no days"


def issued_share(xs: list[dict]) -> tuple[int, int, float | None]:
    """How many of these plans issued at the locked price, how many walked away, and the first over the two."""
    done = sum(1 for o in xs if GROUPS[o["end"]] == "issued at the locked price")
    walked = sum(1 for o in xs if GROUPS[o["end"]] in WALKED)
    return done, walked, (done / (done + walked) if done + walked else None)


def m_at(o: dict, series: dict, day: dt.date) -> float | None:
    """M on one day: the close of the last day the stock traded before it over the price carried to that day."""
    before, _ = around(series, day)
    return side(series, before, day, o["P"], row_before(series, o["B"]) - 1)["M"]


def share_row(label: str, xs: list[dict]) -> str:
    cells = []
    for lo, hi in M_BINS:
        b = f"{lo:.2f} to {hi:.2f}" if hi < math.inf else f"{lo:.2f} and above"
        d, w, r = issued_share([o for o in xs if o.get("bin") == b])
        cells.append(f"{d:>3}/{w:<3}{'' if r is None else f'{r * 100:>4.0f}%'}".ljust(13))
    d, w, r = issued_share(xs)
    return f"      {label:<22} {len(xs):>4}  " + " ".join(cells) + f"   {d:>3}/{w:<3}{'' if r is None else f'{r * 100:>4.0f}%'}"


def share_head() -> str:
    names = [f"{lo:.2f}-{hi:.2f}" if hi < math.inf else f"{lo:.2f}+" for lo, hi in M_BINS]
    return "      " + "M bin".ljust(22) + "     n  " + " ".join(n.ljust(13) for n in names) + "   all"


def splits(data: dict) -> int:
    fr = data["frame"]
    read_more(fr, data["bars"])
    ok = [o for o in fr if o["state"] in MEASURED and o["price_state"] != "not confirmed" and o.get("bin")]
    print(f"\n== 8. the subscriber side: {len(ok)} plans whose price is confirmed, split by whether a title names a related party")
    print("   the rules let three classes take a locked price (the controlling shareholder and its affiliates, an investor "
          "taking control, a strategic investor). Only the related-party marker is readable from the titles here, so the "
          "other two are not told apart; the subscribers' names are in the offering table for the issued plans alone.")
    rel = [o for o in ok if o["related"]]
    oth = [o for o in ok if not o["related"]]
    for label, xs in (("a related party named", rel), ("no related party named", oth)):
        print(f"   {label}: {len(xs)}; ends {dict(collections.Counter(GROUPS[o['end']] for o in xs))}")
    print("   the count that issued at the locked price over the count that walked away, by M bin:")
    print(share_head())
    print(share_row("a related party named", rel))
    print(share_row("no related party named", oth))

    print("\n== 9. how long the plan ran and the year it started")
    print(share_head())
    for lo, hi in DURATIONS:
        label = f"{lo} to {hi} days" if hi < math.inf else f"{lo} days and more"
        print(share_row(label, [o for o in ok if duration_bucket(o["days"]) == label]))
    print("   by the year of the first locked document:")
    print(share_head())
    for y in sorted({o["b"].year for o in ok}):
        print(share_row(str(y), [o for o in ok if o["b"].year == y]))

    moved = sorted([o for o in ok if o["outcome"] == "moved to first day"], key=lambda o: o["t"])
    print(f"\n== 10. the plans moved to first-day pricing: {len(moved)}")
    for o in moved:
        print(f"      {o['code']} {o['name']} b {o['b']} P {o['P']} moved {o['t']}: close before {o['before']['close']} "
              f"carried {o['before']['carried']:.4f} M {o['M']:.4f}, {o['days']} days")
    if moved:
        day = moved[0]["t"] - dt.timedelta(days=1)
        live = [o for o in ok if o["b"] <= day and o["t"] > day and o["outcome"] != "moved to first day"]
        mm = [(o, m_at(o, data["bars"].series(o["code"]), day)) for o in moved]
        ml = [(o, m_at(o, data["bars"].series(o["code"]), day)) for o in live]
        mm = [(o, m) for o, m in mm if m is not None]
        ml = [(o, m) for o, m in ml if m is not None]
        print(f"   M on {day}, the day before the first of those moves:")
        print(f"      the plans that moved, {len(mm)}: {quantiles([m for _, m in mm])}; below 1 {sum(1 for _, m in mm if m < 1)}")
        print(f"      the locked plans still live that day and did not move, {len(ml)}: {quantiles([m for _, m in ml])}; "
              f"below 1 {sum(1 for _, m in ml if m < 1)}")
        print(f"      what became of those, {dict(collections.Counter(GROUPS[o['end']] for o, _ in ml))}")
        for o, m in sorted(ml, key=lambda x: -x[1])[:10]:
            print(f"      still locked and highest that day: {o['code']} {o['name']} b {o['b']} P {o['P']} M {m:.4f} -> {o['end']} {o['t']}")
    return 0


# ---------------------------------------------------------------------------
# Part four: what walking away was worth
# ---------------------------------------------------------------------------

def cn_number(digits: str, unit: str) -> float:
    return float(digits.replace(",", "").replace("，", "")) * UNITS[unit]


def deal_size(text: str) -> dict:
    """The caps a plan's own document prints: the shares, the money, and the shares as a share of the shares before."""
    out = {"shares": None, "money": None, "ratio": None}
    m = SHARES_CAP.search(text)
    if m:
        out["shares"] = cn_number(*m.groups())
    m = MONEY_CAP.search(text)
    if m:
        out["money"] = cn_number(*m.groups())
    m = RATIO_CAP.search(text)
    if m:
        out["ratio"] = float(m.group(1).replace(",", "")) / 100.0
    return out


def size_of(o: dict, size: dict) -> tuple[float | None, str]:
    """The shares the plan would have issued, and where that count comes from. A plan's documents print a cap on the money
    it raises and often a cap on the shares; the money cap over the price is the plan's own size, while the share cap is
    usually the ceiling the rules put at 30% of the shares before, so the money cap is taken where both are read and the
    share cap is named beside it when the two are more than half apart. That gap is where a misread shows: 和而泰's share
    cap reads 46,695,402万股 where its money cap over its price is 46,695,402 shares, and 华谊兄弟's share cap reads
    35,971,223 shares against a money cap of 2.29 billion yuan at 2.78 a share."""
    by_money = size["money"] / o["P"] if size.get("money") and o.get("P") else None
    by_shares = size.get("shares")
    if by_money and by_shares:
        lo, hi = sorted((by_money, by_shares))
        return by_money, ("the money cap over the price, the share cap agrees" if hi <= 1.5 * lo
                          else "the money cap over the price, the share cap more than half apart")
    if by_money:
        return by_money, "the money cap over the price"
    if by_shares:
        return by_shares, "the share cap in the documents"
    return None, "no cap read"


def transfer(n: float, pm: float, price: float, ratio: float | None = None) -> tuple[float, float]:
    """n N (Pm - P) / (N + n) in 100 million yuan, as a band because N is not in any table for a plan that never issued:
    the rules cap n at 30% of N, so the factor N / (N + n) = 1 / (1 + n/N) lies between 1/1.3 and 1, and a plan that
    prints its own n/N gets that factor alone."""
    factors = [1 / (1 + ratio)] if ratio else [1 / (1 + SHARE_CAP_RULE), 1.0]
    got = [n * (pm - price) / YI * f for f in factors]
    return min(got), max(got)


def issued_transfer(row: dict, pm: float) -> float | None:
    """The same transfer on an issue that happened, with the table's own shares before and shares issued."""
    n, N, price = B110.num(row.get("ISSUE_NUM")), B110.num(row.get("ISSUE_SHARE_BEFORE")), B110.num(row.get("ISSUE_PRICE"))
    if not n or not N or price is None or pm is None:
        return None
    return n * N * (pm - price) / (N + n) / YI


def b110_column(bars, rows: list[dict], since: str = B110.SCOPE_START) -> dict:
    """B110-4's locked-cash column recomputed here: the cash placements priced in advance, by the year of T."""
    out: dict = collections.defaultdict(lambda: [0, 0.0])
    left: collections.Counter = collections.Counter()
    for r in rows:
        T = str(r.get("ISSUE_DATE") or "")[:10]
        if str(r.get("SEO_TYPE")) != "1" or T < since or r.get("ISSUE_WAY") != B110.PRICED_WAY:
            continue
        o = {"principle": r.get("PRICE_PRINCIPLE") or "", "gross": B110.num(r.get("TOTAL_RAISE_FUNDS")),
             "net": B110.num(r.get("NET_RAISE_FUNDS"))}
        if B110.priced_state(o) != "cash":
            continue
        series = bars.series(str(r.get("SECURITY_CODE")))
        row = B110.row_of(series, T) if series is not None else None
        if row is None or int(series["status"][row]) != 1:
            left["no bars" if series is None else "T is not a row" if row is None else "suspended on T"] += 1
            continue
        v = issued_transfer(r, float(series["close"][row]))
        if v is None:
            left["the table is missing a number"] += 1
            continue
        out[T[:4]][0] += 1
        out[T[:4]][1] += v
    return {"by_year": {y: (n, round(v, 2)) for y, (n, v) in sorted(out.items())}, "left": dict(left)}


def b110_record_column(path: Path = B110_RECORD) -> dict:
    """The same column as B110's own record prints it: year -> (offerings, transfer on the close of T)."""
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    detail = next((c["detail"] for c in obj.get("criteria", []) if c.get("name") == "B110-4"), "")
    return {m.group(1): (int(m.group(2)), float(m.group(3).replace(",", "")))
            for m in re.finditer(r"网下定价发行 (\d{4}): (\d+) offerings, (-?[\d,]+\.\d\d) /", detail)}


def money(data: dict) -> int:
    ms = prepare(data)
    print(f"\n== 11. the size each plan would have issued: {len(ms)} plans whose price is confirmed")
    print(f"   where the count comes from: {dict(collections.Counter(o['n_from'] for o in ms))}; "
          f"plans printing their own share of the shares before: {sum(1 for o in ms if o['ratio'])}")
    apart = [o for o in ms if o["n_from"].endswith("more than half apart")]
    for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in apart], 8):
        sz = data["sizes"][o["id"]]
        print(f"      caps apart: {o['code']} {o['name']} b {o['b']}: share cap {sz['shares']:,.0f}, money cap over the price "
              f"{sz['money'] / o['P']:,.0f}, carried as a band")
    for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in ms if o["n"]], 8):
        print(f"      {o['code']} {o['name']} b {o['b']} {o['end']}: n {o['n']:,.0f} shares ({o['n_from']}), "
              f"P {o['P']}, n P {o['n'] * o['P'] / YI:,.2f} in 100 million yuan, ratio {o['ratio']}")
    for o in P.pick_spread([{**o, "announcementTime": 0, "announcementId": o["id"]} for o in ms if not o["n"]], 6):
        print(f"      no cap read: {o['code']} {o['name']} b {o['b']} {o['end']}")

    walked = [o for o in ms if GROUPS[o["end"]] in WALKED + ("the lock given up", "re-locked or replaced") and o["n"] and o["M"]]
    print(f"\n== 12. what the plans that did not issue would have handed over on the day they ended: {len(walked)} plans")
    print("   n N (Pm - P) / (N + n) in 100 million yuan, as a band because N is not in any table for a plan that never issued")
    rows: dict = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for o in walked:
        lo, hi = o["walk_lo"], o["walk_hi"]
        for key in (str(o["t"].year), GROUPS[o["end"]]):
            rows[key][0] += 1
            rows[key][1] += lo
            rows[key][2] += hi
    for key in sorted(rows):
        n, lo, hi = rows[key]
        print(f"      {key:<26} {n:>4} plans, {lo:>10,.2f} to {hi:>10,.2f}")
    for o in sorted(walked, key=lambda o: -abs(o["walk_hi"]))[:10]:
        print(f"      the largest: {o['code']} {o['name']} b {o['b']} {o['end']} {o['t']}, M {o['M']:.3f}, "
              f"{o['walk_lo']:,.2f} to {o['walk_hi']:,.2f}")

    priced, _ = B.offering_rows()
    by_deal = collections.defaultdict(list)
    for r in priced:
        by_deal[(str(r["SECURITY_CODE"]), str(r["ISSUE_DATE"])[:10])].append(r)
    done = [o for o in ms if o["end"] == "issued" and o.get("issue")]
    got: dict = collections.defaultdict(lambda: [0, 0.0])
    for o in done:
        rs = by_deal.get((o["code"], o["t"].isoformat()), [])
        r = rs[0] if len(rs) == 1 else None
        if r is None:
            continue
        v = issued_transfer(r, o["on"]["close"] if o["on"]["day"] == o["t"] else o["before"]["close"])
        if v is not None:
            got[str(o["t"].year)][0] += 1
            got[str(o["t"].year)][1] += v
    print("   the issues that did happen, with the table's own shares issued and shares before, by the year of the issue:")
    for y in sorted(got):
        n, v = got[y]
        print(f"      {y:<26} {n:>4} plans, {v:>10,.2f}")

    print("\n== 13. B110-4's locked-cash column recomputed here against B110's record")
    full, note = B110.load_bars()
    print(f"   bars: {note}")
    mine = b110_column(full, data["seo_rows"])
    theirs = b110_record_column()
    print(f"   offerings left out of the recomputation: {mine['left']}")
    bad = []
    for y in sorted(set(mine["by_year"]) | set(theirs)):
        a, b = mine["by_year"].get(y), theirs.get(y)
        same = a is not None and b is not None and a[0] == b[0] and abs(a[1] - b[1]) <= 0.02
        print(f"      {y}: here {a}, in the record {b}{'' if same else '   <- apart'}")
        if not same:
            bad.append(y)
    print(f"   years apart: {bad if bad else 'none'}")
    return 0


# ---------------------------------------------------------------------------
# Part five: the criteria and the record
# ---------------------------------------------------------------------------

RECORD = P.ROOT / "results" / "b120_readings.json"
DRAWS = 2000
SEEDS = (20260917, 20260918)
MATCHING_ON_FILE = {"300909": "the pricing text names no matching funds, and B110's own reading takes this placement for the cash raised beside an asset deal of the same company"}

PRICE_MAP = {"at the floor": True, "the floor with net assets named": True, "the issue price agrees": True,
             "the floor of another day": True, "a price of another plan of this company": True, "not confirmed": False}
LINK_MAP = {"linked to a plan": True, "no announcement of this company in the census": None, "no plan found": False}
SHAPE_MAP = {"one end, after the first document and not after the data end": True,
             "an end before the first document": False, "an end after the data end": False,
             "an end the groups do not name": False}
GRADIENT_MAP = {"rises above the floor": True, "inside the floor": None, "falls below the floor": False}
MONEY_MAP = {"a band": True, "named without a size": True, "named without a close before the end": True,
             "a band the wrong way round": False, "unaccounted": False}
MOVED_MAP = {"read on the pivot day and on its own": True, "named without a confirmed price": True,
             "a confirmed price with no M read": False}
COVER_FIELDS = ("code and name", "base date", "locked price", "end", "end date", "M", "size", "related-party marker")
NEEDED = ("code and name", "base date", "locked price", "end", "end date", "M")


def _raises(fn) -> bool:
    """Used by the selftest: a state the mapping does not hold has to raise and not pass."""
    try:
        fn()
    except Exception:
        return True
    return False


def verdict_of(states, mapping: dict):
    """False when any state maps to False, None when any maps to None and none to False, else True. A state the mapping
    does not hold raises, since an unmapped cell is an error and not a pass: every cell is mapped, and the undetermined
    cell carries no verdict."""
    got = [mapping[s] for s in states]
    if any(v is False for v in got):
        return False
    return None if any(v is None for v in got) else True


def both(a, b):
    return False if False in (a, b) else (None if None in (a, b) else True)


def walk_band(o: dict) -> tuple[float, float]:
    return transfer(o["n"], o["before"]["close"], o["before"]["carried"], o["ratio"])


def prepare(data: dict) -> list[dict]:
    """The frame with part two's states, part three's marks and part four's size and band on it, and the plans whose
    price is confirmed. Running the steps again lands on the same values."""
    fr = data["frame"]
    read_more(fr, data["bars"])
    for o in fr:
        if o["state"] not in MEASURED:
            continue
        sz = data["sizes"].get(o["id"], {})
        o["n"], o["n_from"] = size_of(o, sz)
        o["ratio"] = sz.get("ratio")
        o["walk_lo"], o["walk_hi"] = walk_band(o) if o["n"] and o["before"]["carried"] else (None, None)
    return [o for o in fr if o["state"] in MEASURED and o["price_state"] != "not confirmed"]


def criterion_price(fr: list[dict]) -> dict:
    """B120-1. The rule pins the locked price at the floor, so every price read is at it or in a named class."""
    rd = [o for o in fr if o["state"] == "read"]
    states = collections.Counter(o["price_state"] for o in rd)
    named = collections.defaultdict(list)
    for o in rd:
        named[o["price_state"]].append(f"{o['code']} {o['name']} b {o['b']} ({o['price_why']})")
    passed = verdict_of([o["price_state"] for o in rd], PRICE_MAP)
    rule = [o for o in fr if o["state"] == "price from the rule"]
    out = [o for o in fr if o["state"] not in MEASURED]
    detail = (f"{len(rd)} plans whose documents read a price: " + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))
              + f". Not objects here: {len(rule)} plans given the rule's price, whose gap is zero by construction, and "
              + f"{len(out)} read no further ({dict(collections.Counter(o['state'] for o in out))}). The "
              + f"{states.get('not confirmed', 0)} not confirmed are named below and stay out of every later table. This "
              + "criterion asks the instrument, so a fail here hands over a list to check and says nothing about the framework.")
    return {"name": "B120-1", "kind": "known_answer",
            "criterion": "every locked price read sits within a tick of 80% of VWAP20 on a base date of its plan, or falls in a named class that says why not",
            "passed": passed, "detail": detail,
            "payload": {"states": dict(sorted(states.items())), "named": {k: v for k, v in sorted(named.items())},
                        "mapping": PRICE_MAP, "floor": FLOOR, "tick": TICK, "vwap_days": B110.VWAP_DAYS,
                        "given the rule's price": len(rule),
                        "read no further": dict(collections.Counter(o["state"] for o in out))}}


def link_state(s: dict, linked: set, in_census: set) -> str:
    if B.issue_key(s) in linked:
        return "linked to a plan"
    if str(s["SECURITY_CODE"]) not in in_census:
        return "no announcement of this company in the census"
    return "no plan found"


def plan_shape(p: dict, data_end: dt.date) -> str:
    if p["t"] < p["b"]:
        return "an end before the first document"
    if p["t"] > data_end:
        return "an end after the data end"
    if p["outcome"] not in GROUPS:
        return "an end the groups do not name"
    return "one end, after the first document and not after the data end"


def criterion_join(plans: list[dict], known: list[dict], in_census: set, data_end: dt.date) -> dict:
    """B120-2. One end to a plan, no announcement in two plans, and every completed locked placement back to a plan."""
    shapes = collections.Counter(plan_shape(p, data_end) for p in plans)
    bad_shape = [f"{p['code']} {p['name']} b {p['b']} -> {p['outcome']} {p['t']}" for p in plans
                 if plan_shape(p, data_end) != "one end, after the first document and not after the data end"]
    seen: dict = {}
    twice, doubled = [], 0
    for p in plans:
        key = f"{p['code']}:{p['b']}"
        ids = list(p["agreements"]) + list(p["documents"])
        doubled += len(ids) - len(set(ids))
        for i in set(ids):
            if i in seen:
                twice.append(f"{i} in {seen[i]} and in {key}")
            seen[i] = key
    linked = {p["detail"]["key"] for p in plans if p["outcome"] == "issued" and p["detail"].get("key")}
    linked |= {p["then"][2]["key"] for p in plans if p.get("then") and p["then"][2].get("key")}
    by_text = collections.Counter(B.known_state(s) for s in known)
    mine = [s for s in known if B.known_state(s) == "a locked cash placement"
            and str(s["SECURITY_CODE"]) not in MATCHING_ON_FILE]
    states = collections.Counter(link_state(s, linked, in_census) for s in mine)
    missed = [f"{s['SECURITY_CODE']} {s['SECURITY_NAME_ABBR']} T {str(s['ISSUE_DATE'])[:10]} P {s['ISSUE_PRICE']} "
              f"({link_state(s, linked, in_census)})" for s in mine if link_state(s, linked, in_census) != "linked to a plan"]
    shape_v = verdict_of([plan_shape(p, data_end) for p in plans], SHAPE_MAP)
    if twice:
        shape_v = False
    passed = both(shape_v, verdict_of([link_state(s, linked, in_census) for s in mine], LINK_MAP))
    detail = (f"{len(plans)} plans: " + ", ".join(f"{k} {v}" for k, v in sorted(shapes.items()))
              + f"; announcements in two plans {len(twice)}" + (f": {twice[:6]}" if twice else "")
              + f", announcements a plan holds both as an agreement and as a plan document {doubled}"
              + ". Completed placements the offering table reads as priced in advance and paid in cash from "
              + f"{F.RECALL_FROM}: {len(known)}, by what their own pricing text prices: "
              + ", ".join(f"{k} {v}" for k, v in sorted(by_text.items()))
              + f". The {len(mine)} whose text reads a locked cash placement, less the {len(MATCHING_ON_FILE)} a record on "
              + "file reads otherwise, are the objects here: " + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))
              + ". A placement of a company the census never returned an announcement for carries no verdict, its exchange "
              + "being outside the carrier; one of a company the census did return carries a verdict.")
    return {"name": "B120-2", "kind": "instrument",
            "criterion": "every plan holds one end dated after its first document and not after the data end, no announcement sits in two plans, and every completed locked cash placement finds the plan it came from",
            "passed": passed, "detail": detail,
            "payload": {"shapes": dict(sorted(shapes.items())), "shapes_named": bad_shape, "in_two_plans": twice,
                        "held twice by one plan": doubled,
                        "completed_by_text": dict(sorted(by_text.items())), "link_states": dict(sorted(states.items())),
                        "not_linked": missed, "mapping": {**SHAPE_MAP, **LINK_MAP},
                        "on_file_as_matching": MATCHING_ON_FILE, "recall_from": F.RECALL_FROM,
                        "data_end": data_end.isoformat()}}


def rank_of(a) -> np.ndarray:
    """Average ranks, ties sharing their mean rank."""
    x = np.asarray(a, dtype=float)
    order = np.argsort(x, kind="mergesort")
    s = x[order]
    r = np.empty(len(s), dtype=float)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return r


def spearman(m, y) -> float:
    a, b = rank_of(m), rank_of(y)
    a, b = a - a.mean(), b - b.mean()
    d = math.sqrt(float(a @ a) * float(b @ b))
    return float(a @ b) / d if d else 0.0


def shuffle_floor(mc: np.ndarray, yr: np.ndarray, strata, draws: int, seed: int, denom: float) -> dict:
    """The largest correlation a shuffle of the labels reaches. With strata the labels move inside one stratum alone, so
    a gradient that is nothing but the strata does not pass it."""
    rng = np.random.default_rng(seed)
    blocks = [np.arange(len(yr))] if strata is None else [np.flatnonzero(strata == s) for s in np.unique(strata)]
    mean, z, got = float(yr.mean()), yr.copy(), np.empty(draws, dtype=float)
    for k in range(draws):
        for ix in blocks:
            z[ix] = rng.permutation(yr[ix])
        got[k] = float(mc @ (z - mean)) / denom
    return {"largest": float(np.abs(got).max()), "sd": float(got.std(ddof=1)), "draws": draws, "seed": int(seed)}


def gradient(xs: list[dict], draws: int = DRAWS, seeds: tuple = SEEDS) -> dict:
    """The rank correlation between M and issuing at the locked price, against two shuffle floors."""
    m = np.array([o["M"] for o in xs], dtype=float)
    y = np.array([1.0 if GROUPS[o["end"]] == "issued at the locked price" else 0.0 for o in xs])
    strata = np.array([f"{o['b'].year}|{duration_bucket(o['days'])}" for o in xs])
    mr, yr = rank_of(m), rank_of(y)
    mc, yc = mr - mr.mean(), yr - yr.mean()
    denom = math.sqrt(float(mc @ mc) * float(yc @ yc))
    rho = float(mc @ yc) / denom if denom else 0.0
    nulls = {}
    for label, st in (("labels shuffled", None), ("labels shuffled inside the start year and the length", strata)):
        per = [shuffle_floor(mc, yr, st, draws, s, denom) for s in seeds]
        floor = max(p["largest"] for p in per)
        nulls[label] = {"floor": floor, "over the floor": abs(rho) / floor if floor else None, "by_seed": per,
                        "seeds apart": abs(per[0]["largest"] - per[1]["largest"])}
    floor = max(v["floor"] for v in nulls.values())
    state = "rises above the floor" if rho > floor else "falls below the floor" if rho < -floor else "inside the floor"
    return {"plans": len(xs), "issued": int(y.sum()), "walked": int(len(y) - y.sum()), "rho": rho, "floor": floor,
            "over the floor": abs(rho) / floor if floor else None, "state": state, "nulls": nulls,
            "strata": len(set(strata.tolist()))}


def cut_row(sub: list[dict]) -> dict:
    d, w, r = issued_share(sub)
    rho = spearman([o["M"] for o in sub], [1.0 if GROUPS[o["end"]] == "issued at the locked price" else 0.0 for o in sub]) \
        if len(sub) > 2 else None
    return {"plans": len(sub), "issued": d, "walked": w, "share": r, "rho": rho}


def criterion_gradient(ok: list[dict], draws: int = DRAWS, seeds: tuple = SEEDS) -> dict:
    """B120-3. The share that issued rises with M, by more than a shuffle of the labels reaches."""
    xs = [o for o in ok if o.get("M") and GROUPS[o["end"]] in ("issued at the locked price",) + WALKED]
    g = gradient(xs, draws, seeds)
    bins = [{"bin": label, "plans": n, "by group": {k: v for k, v in sorted(c.items())}, "median days": d}
            for label, n, c, d in bin_table(ok)]
    shares = []
    for label, _, _, _ in bin_table(ok):
        d, w, r = issued_share([o for o in ok if o.get("bin") == label])
        shares.append({"bin": label, "issued": d, "walked": w, "share": r})
    cuts = {"a related party named": cut_row([o for o in xs if o["related"]]),
            "no related party named": cut_row([o for o in xs if not o["related"]])}
    for b in sorted({duration_bucket(o["days"]) for o in xs}):
        cuts[b] = cut_row([o for o in xs if duration_bucket(o["days"]) == b])
    for y in sorted({o["b"].year for o in xs}):
        cuts[f"started {y}"] = cut_row([o for o in xs if o["b"].year == y])
    passed = verdict_of([g["state"]], GRADIENT_MAP)
    detail = (f"{g['plans']} plans whose price is confirmed and which either issued at the locked price ({g['issued']}) or "
              f"walked away ({g['walked']}). The share that issued, by M bin: "
              + ", ".join(f"{s['bin']} {s['share']:.3f}" if s["share"] is not None else f"{s['bin']} none" for s in shares)
              + f". The rank correlation between M and issuing is {g['rho']:+.4f} against a floor of {g['floor']:.4f}, the "
              + f"largest any of {draws} label shuffles reached on either seed, taking the stricter of a plain shuffle and "
              + f"one that moves labels inside a start year and length bucket alone ({g['strata']} buckets): "
              + f"{g['over the floor']:.1f} times the floor, and {abs(g['rho']) - g['floor']:.4f} above it against "
              + f"{max(v['seeds apart'] for v in g['nulls'].values()):.4f} between what the two seeds give for that floor. "
              + "The reading the design registers against this one, that the "
              + "conditional agreement binds both sides and the end is independent of the price path after signing, calls "
              + "for a flat share across the bins; it is settled here and carries no criterion of its own. Two of the three "
              + "splits the design registers are read, the related-party marker and the length and start year. The stage a "
              + "plan had reached is not read, the acceptance and registration announcements never having been fetched, so "
              + "nothing here speaks to the split before and after registration, and the other two subscriber classes are "
              + "not told apart from each other.")
    return {"name": "B120-3", "kind": "own_reading",
            "criterion": "the share of plans that issued at the locked price, among those that issued or walked away, rises with M by more than the shuffle floor",
            "passed": passed, "detail": detail,
            "payload": {"gradient": g, "bins": bins, "shares": shares, "cuts": cuts, "mapping": GRADIENT_MAP,
                        "m_bins": [[lo, None if hi == math.inf else hi] for lo, hi in M_BINS],
                        "not read": {"the stage at the end": "the acceptance and registration announcements were not fetched",
                                     "the three subscriber classes": "only the related-party marker is readable from the titles"}}}


def money_state(o: dict) -> str:
    if o["walk_lo"] is not None and o["walk_hi"] is not None:
        return "a band the wrong way round" if o["walk_lo"] > o["walk_hi"] else "a band"
    if o["before"]["close"] is None or o["before"]["carried"] is None:
        return "named without a close before the end"
    return "named without a size" if not o["n"] else "unaccounted"


def criterion_money(ok: list[dict]) -> dict:
    """B120-4. What a plan that did not issue would have handed over on the day it ended."""
    xs = [o for o in ok if GROUPS[o["end"]] in WALKED + ("the lock given up", "re-locked or replaced")]
    states = collections.Counter(money_state(o) for o in xs)
    passed = verdict_of([money_state(o) for o in xs], MONEY_MAP)
    banded = [o for o in xs if money_state(o) == "a band"]
    by_group: dict = collections.defaultdict(lambda: [0, 0.0, 0.0])
    by_year: dict = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for o in banded:
        for tab, key in ((by_group, GROUPS[o["end"]]), (by_year, str(o["t"].year))):
            tab[key][0] += 1
            tab[key][1] += o["walk_lo"]
            tab[key][2] += o["walk_hi"]
    lo = sum(o["walk_lo"] for o in banded)
    hi = sum(o["walk_hi"] for o in banded)
    sizes = collections.Counter(o["n_from"] for o in xs)
    detail = (f"{len(xs)} plans whose price is confirmed and which did not issue at the locked price: "
              + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))
              + ". Where the share count comes from: " + ", ".join(f"{k} {v}" for k, v in sorted(sizes.items()))
              + f". The {len(banded)} carrying a band would have handed over {lo:,.2f} to {hi:,.2f} in 100 million yuan on "
              + "the day they ended, n N (Pm - P) / (N + n) with N in no table and the shares capped at 30% of the shares "
              + "before, so N / (N + n) lies between 1/1.3 and 1 and a plan printing its own ratio gets that factor alone. "
              + f"The {states.get('named without a size', 0)} with no cap read are named and left out, so the total is a "
              + "floor over the plans that print a cap and not a total over all of them. A negative band is a plan whose "
              + "price stood above the market where it ended, the amount the subscriber did not take.")
    return {"name": "B120-4", "kind": "own_reading",
            "criterion": "every plan that did not issue at the locked price carries a band for what it would have handed over, or is named with what it lacks",
            "passed": passed, "detail": detail,
            "payload": {"states": dict(sorted(states.items())), "size_states": dict(sorted(sizes.items())),
                        "by_group": {k: {"plans": v[0], "low": v[1], "high": v[2]} for k, v in sorted(by_group.items())},
                        "by_year": {k: {"plans": v[0], "low": v[1], "high": v[2]} for k, v in sorted(by_year.items())},
                        "total": {"plans": len(banded), "low": lo, "high": hi},
                        "named without a size": [f"{o['code']} {o['name']} b {o['b']} {o['end']}" for o in xs
                                                 if money_state(o) == "named without a size"],
                        "largest": [f"{o['code']} {o['name']} b {o['b']} {o['end']} {o['t']} M {o['M']:.3f}: "
                                    f"{o['walk_lo']:,.2f} to {o['walk_hi']:,.2f}"
                                    for o in sorted(banded, key=lambda o: -abs(o["walk_hi"]))[:12]],
                        "mapping": MONEY_MAP, "share_cap_rule": SHARE_CAP_RULE}}


def criterion_moved(fr: list[dict], ok: list[dict], bars) -> dict:
    """B120-5. The plans moved to first-day pricing, against the locked plans still live beside them."""
    moved = [o for o in fr if o["end"] == "moved to first day"]
    if not moved:
        return {"name": "B120-5", "kind": "own_reading", "criterion": "the plans moved to first-day pricing are read",
                "passed": False, "detail": "no plan read as moved to first-day pricing", "payload": {"moved": []}}
    pivot = min(o["t"] for o in moved) - dt.timedelta(days=1)
    rows, states = [], []
    for o in sorted(moved, key=lambda o: (o["t"], o["code"])):
        series = bars.series(o["code"])
        usable = series is not None and o["state"] in MEASURED and o.get("price_state") != "not confirmed"
        at = m_at(o, series, pivot) if usable else None
        st = ("named without a confirmed price" if not usable
              else "read on the pivot day and on its own" if at is not None and o.get("M") is not None
              else "a confirmed price with no M read")
        states.append(st)
        rows.append({"code": o["code"], "name": o["name"], "b": o["b"].isoformat(), "announced": o["t"].isoformat(),
                     "P": o.get("P"), "M on the pivot day": at, "M on its own day": o.get("M"),
                     "price": o.get("price_state", o["state"]), "state": st})
    still = []
    for o in ok:
        if not (o["b"] <= pivot < o["t"]) or o["end"] == "moved to first day":
            continue
        series = bars.series(o["code"])
        v = m_at(o, series, pivot) if series is not None else None
        if v is not None:
            still.append({"code": o["code"], "name": o["name"], "b": o["b"].isoformat(), "M on the pivot day": v,
                          "later": o["end"]})
    passed = verdict_of(states, MOVED_MAP)
    if not still:
        passed = False
    a = sorted(r["M on the pivot day"] for r in rows if r["M on the pivot day"] is not None)
    b = sorted(r["M on the pivot day"] for r in still)
    detail = (f"{len(moved)} plans read as moved to first-day pricing, announced {min(o['t'] for o in moved)} to "
              f"{max(o['t'] for o in moved)}: "
              + ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(states).items()))
              + f". M on {pivot}, the day before the first of the moves: the movers "
              + (f"{np.quantile(a, 0.1):.3f} / {np.quantile(a, 0.5):.3f} / {np.quantile(a, 0.9):.3f} at the tenth, the "
                 f"median and the ninetieth, {sum(1 for x in a if x < 1)} of {len(a)} below 1" if a else "none read")
              + f"; the {len(b)} locked plans still live that day and not moved "
              + (f"{np.quantile(b, 0.1):.3f} / {np.quantile(b, 0.5):.3f} / {np.quantile(b, 0.9):.3f}, "
                 f"{sum(1 for x in b if x < 1)} of {len(b)} below 1" if b else "none read")
              + ". Every plan is printed and no line is drawn on either distribution.")
    return {"name": "B120-5", "kind": "own_reading",
            "criterion": "every plan moved to first-day pricing is read with M on its own announcement and on the day before the first of the moves, or named without a confirmed price, and the locked plans still live that day stand beside them",
            "passed": passed, "detail": detail,
            "payload": {"pivot": pivot.isoformat(), "moved": rows, "still locked": still, "mapping": MOVED_MAP,
                        "states": dict(sorted(collections.Counter(states).items())),
                        "later of the still locked": dict(sorted(collections.Counter(r["later"] for r in still).items()))}}


def cover_row(o: dict) -> dict:
    """Where each field of one plan comes from, the fields it has none for left as None."""
    src = {"code and name": "the census announcement", "base date": None, "locked price": None, "end": None,
           "end date": None, "M": None, "size": None, "related-party marker": None}
    src["end"] = ("the security list's delisting date" if o["end"] == "stock delisted"
                  else "the offering table" if o["outcome"] in ("issued", "issued by bids")
                  else "the data end, no closing announcement" if o["outcome"] == "pending"
                  else "a census announcement")
    src["end date"] = src["end"]
    src["related-party marker"] = "the documents' titles" if o.get("titles") else None
    if o["state"] in MEASURED:
        src["base date"] = o.get("label")
        src["locked price"] = o.get("price_state")
        src["M"] = f"the close of {o['before']['day']}" if o["before"]["day"] is not None else None
        src["size"] = None if o.get("n_from") in (None, "no cap read") else o["n_from"]
    return {"plan": o["id"], "code": o["code"], "name": o["name"], "state": o["state"], "sources": src}


def criterion_coverage(fr: list[dict], inputs: dict) -> dict:
    """B120-6. One row a plan, each field with where it came from, the empty ones counted too."""
    rows = [cover_row(o) for o in fr]
    twice = [k for k, v in collections.Counter(r["plan"] for r in rows).items() if v > 1]
    have = {f: sum(1 for r in rows if r["sources"][f]) for f in COVER_FIELDS}
    by_field = {f: dict(sorted(collections.Counter(r["sources"][f] or "none" for r in rows).items())) for f in COVER_FIELDS}
    confirmed = {o["id"] for o in fr if o["state"] in MEASURED and o.get("price_state") != "not confirmed"}
    short = [f"{r['plan']} has no {f}" for r in rows if r["plan"] in confirmed for f in NEEDED if not r["sources"][f]]
    passed = len(rows) == len(fr) and not twice and not short
    detail = (f"{len(rows)} rows for {len(fr)} plans, one each, {len(twice)} repeated. Fields present: "
              + ", ".join(f"{f} {have[f]}" for f in COVER_FIELDS)
              + f". Of the {len(confirmed)} plans whose price is confirmed, {len(short)} field slots the readings use are "
              + "empty. A field with no source is printed as none and counted, and so are the inputs that returned nothing: "
              + ", ".join(f"{k} {v}" for k, v in sorted(inputs.items()))
              + f", plans read no further {dict(collections.Counter(o['state'] for o in fr if o['state'] not in MEASURED))}.")
    return {"name": "B120-6", "kind": "bookkeeping",
            "criterion": "every plan holds one coverage row naming where each field came from, and no plan whose price is confirmed is short a field the readings use",
            "passed": passed, "detail": detail,
            "payload": {"fields present": have, "by_field": by_field, "repeated": twice, "short": short,
                        "inputs": dict(sorted(inputs.items())), "rows": rows}}


def criterion_recompute(mine: dict, theirs: dict, note: str) -> dict:
    """B120-7. B110-4's locked-cash column, recomputed here from the offering table and the full bar store."""
    years = sorted(set(mine["by_year"]) | set(theirs))
    apart = []
    for y in years:
        a, b = mine["by_year"].get(y), theirs.get(y)
        if a is None or b is None or a[0] != b[0] or abs(a[1] - b[1]) > 0.02:
            apart.append(f"{y}: here {a}, in the record {b}")
    passed = bool(years) and bool(theirs) and not apart
    detail = (f"{len(years)} years of the column: " + ", ".join(f"{y} {mine['by_year'].get(y)}" for y in years)
              + f". Offerings left out of the recomputation: {mine['left']}, for the reasons B110's own record gives. "
              + f"Years apart from the record: {len(apart)}" + (f": {apart}" if apart else "")
              + f". Bars: {note}. This says the transfer B120-4 prints is the arithmetic B110 already closed and not a "
              + "second one.")
    return {"name": "B120-7", "kind": "known_answer",
            "criterion": "B110-4's locked-cash column recomputed here from the offering table and the bar store agrees with B110's record in every year, on the count and on the transfer",
            "passed": passed, "detail": detail,
            "payload": {"here": {y: list(v) for y, v in mine["by_year"].items()},
                        "in the record": {y: list(v) for y, v in theirs.items()},
                        "left out": mine["left"], "apart": apart, "record": B110_RECORD.name}}


def config_block(data: dict) -> dict:
    fr = data["frame"]
    return {"scope": {"data end": B.DATA_END.isoformat(), "rule from": B.ISSUED_FROM,
                      "completed placements from": F.RECALL_FROM, "plan documents near a plan": list(F.PLAN_DOC_NEAR)},
            "rules": {"floor": FLOOR, "tick": TICK, "vwap days": B110.VWAP_DAYS, "share cap": SHARE_CAP_RULE,
                      "net asset word": NET_ASSET, "related words": list(RELATED_WORDS),
                      "m bins": [[lo, None if hi == math.inf else hi] for lo, hi in M_BINS],
                      "durations": [[lo, None if hi == math.inf else hi] for lo, hi in DURATIONS], "groups": GROUPS},
            "knobs": {"stale days": STALE_DAYS, "scan days": SCAN_DAYS, "split factor": B110.SPLIT_FACTOR,
                      "shuffle draws": DRAWS, "shuffle seeds": list(SEEDS)},
            "inputs": {"plans": len(data["plans"]), "stocks": len(data["codes"]), "store files": len(data["files"]),
                       "bars": data["bars_note"], "security list": data["basic_note"],
                       "offering rows": len(data["seo_rows"]),
                       "frame states": dict(sorted(collections.Counter(o["state"] for o in fr).items())),
                       "pdf texts": dict(sorted(data["built"]["counts"].items()))}}


def criteria_report(data: dict, write: bool = False) -> int:
    fr = data["frame"]
    ok = prepare(data)
    built = data["built"]
    full, note = B110.load_bars()
    inputs = {"PDF texts by how they read": dict(sorted(built["counts"].items())),
              "census announcements": len(built["rows"]), "census windows not in the cache": len(built["gaps"])}
    out = [criterion_price(fr),
           criterion_join(data["plans"], F.completed_locked_cash(since=F.RECALL_FROM),
                          {str(r["secCode"]) for r in built["rows"].values()}, B.DATA_END),
           criterion_gradient(ok), criterion_money(ok), criterion_moved(fr, ok, data["bars"]),
           criterion_coverage(fr, inputs),
           criterion_recompute(b110_column(full, data["seo_rows"]), b110_record_column(), note)]
    print("\n== 14. the criteria")
    for c in out:
        mark = {True: "PASS", False: "FAIL", None: "NO VERDICT"}[c["passed"]]
        print(f"\n[{mark}] {c['name']} ({c['kind']}) {c['criterion']}")
        print(f"  {c['detail']}")
        if "mapping" in c["payload"]:
            print("  state -> verdict: " + ", ".join(f"{k} -> {v}" for k, v in c["payload"]["mapping"].items()))
    for k, v in sorted(out[0]["payload"]["named"].items()):
        print(f"  B120-1 {k}: {len(v)}: {v[:5]}{' ...' if len(v) > 5 else ''}")
    print(f"  B120-2 not linked: {out[1]['payload']['not_linked']}")
    g = out[2]["payload"]["gradient"]
    for label, v in g["nulls"].items():
        print(f"  B120-3 floor, {label}: {v['floor']:.4f}, {abs(g['rho']) / v['floor']:.1f} times, "
              f"seeds apart {v['seeds apart']:.4f}, sd {v['by_seed'][0]['sd']:.4f}")
    print("  B120-3 the share that issued, by cut:")
    for k, v in out[2]["payload"]["cuts"].items():
        share = "none" if v["share"] is None else f"{v['share'] * 100:.0f}%"
        rho = "none" if v["rho"] is None else f"{v['rho']:+.4f}"
        print(f"    {k:<28} {v['plans']:>4} plans, {v['issued']:>3}/{v['walked']:<3} {share:>5}, rho {rho}")
    print("  B120-4 by group: " + "; ".join(f"{k} {v['plans']} plans {v['low']:,.2f} to {v['high']:,.2f}"
                                            for k, v in out[3]["payload"]["by_group"].items()))
    print(f"  B120-6 short: {out[5]['payload']['short'][:8]}")
    if write:
        record = B110.clean({"stage": "B120", "config": config_block(data), "criteria": out})
        body = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
        P.atomic_write_bytes(RECORD, body)
        print(f"\n  record -> results/{RECORD.name}, {len(body):,} bytes, sha256 {hashlib.sha256(body).hexdigest()[:16]}")
    return 0


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _series(closes: list[float], precloses: list[float], status: list[int] | None = None, start: dt.date = dt.date(2021, 1, 4)) -> dict:
    """Weekday rows from `start`: volume 100 and amount close times volume on traded rows, zero on the others."""
    n = len(closes)
    days = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    st = status or [1] * n
    out = {"ordinal": np.array([x.toordinal() for x in days], dtype=np.int32), "status": np.array(st, dtype=np.int8),
           "close": np.array(closes, dtype=float), "preclose": np.array(precloses, dtype=float)}
    out["volume"] = np.array([100.0 if s else 0.0 for s in st])
    out["amount"] = out["close"] * out["volume"]
    for k in ("open", "high", "low"):
        out[k] = out["close"].copy()
    return B110.finish_series(out)


def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    d = dt.date
    # rows 0-9 close 10; row 10 a 0.2 dividend; row 22 closes at 12; row 25 a two-for-one split; row 5 suspended
    closes = [10.0] * 10 + [9.8] * 12 + [12.0] + [9.8] * 2 + [4.9] * 5
    pre = [10.0] * 10 + [9.8] * 12 + [9.8] + [12.0] + [9.8] + [4.9] * 5
    status = [1] * 30
    status[5] = 0
    s = _series(closes, pre, status)
    day = lambda r: d.fromordinal(int(s["ordinal"][r]))  # noqa: E731
    v22, v25, vsat = vwap20(s, day(22)), vwap20(s, day(25)), vwap20(s, d(2021, 2, 6))  # v25 is used again by the floor scan below
    expect25 = (5 * 1000 + 12 * 980 + 1200 + 2 * 980) / (5 * 100 * 10 / 9.8 + 15 * 100)
    check(f"VWAP20 counts the 20 traded days before the base date in the basis of the day before it, a dividend inside taken at "
          f"its adjusted price, a split on the base date left out, a Saturday read as the Monday after ({v22}, {v25}, {vsat}, "
          f"{day(22)}, {day(25)})", day(22) == d(2021, 2, 3) and abs(v22 - 9.8) < 1e-9 and abs(v25 - expect25) < 1e-9 and vsat == v25)
    short = _series([10.0] * 12, [10.0] * 12)
    check(f"fewer than 20 traded days before the base date give no VWAP20 ({vwap20(short, d(2021, 1, 20))})", vwap20(short, d(2021, 1, 20)) is None)
    c1, c2, c3 = carry(s, 7.84, 21, 29), carry(s, 7.84, 5, 12), carry(s, 7.84, 11, 20)
    b1, b2 = carry(s, 3.92, 29, 21), carry(s, 7.64, 12, 5)
    check(f"a price carries through a dividend day by the cash off and through a split day by the factor, and back the same way "
          f"({c1}, {c2}, {c3}, {b1}, {b2})",
          abs(c1 - 3.92) < 1e-12 and abs(c2 - 7.64) < 1e-12 and c3 == 7.84 and abs(b1 - 7.84) < 1e-12 and abs(b2 - 7.84) < 1e-12)
    bars = type("Bars", (), {"series": lambda self, code: {"600001": s, "600002": short}.get(code)})()
    doc_day = {"dA": d(2021, 2, 3), "dF": d(2021, 2, 3), "dL": d(2021, 1, 20)}
    doc_state = {"dF": "first day"}

    def plan(code, b, t, prices, documents=(), base_days=(), outcome="plan ended", P_table=None):
        return {"code": code, "name": "测试", "b": b, "t": t, "outcome": outcome, "prices": list(prices), "documents": list(documents),
                "base_days": list(base_days), "then": None, "detail": {"P": P_table} if P_table is not None else {}}

    x = read_plan(plan("600001", d(2021, 2, 8), d(2021, 2, 6), [7.84, 9.0], documents=["dA"]), bars, doc_day, doc_state)
    y = read_plan(plan("600001", d(2021, 2, 8), d(2021, 2, 6), [7.84, 7.93], documents=["dF"]), bars, doc_day, doc_state)
    z = read_plan(plan("600001", d(2021, 2, 8), d(2021, 2, 6), [7.84], base_days=[d(2021, 2, 3)]), bars, doc_day, doc_state)
    tie = read_plan(plan("600001", d(2021, 2, 3), d(2021, 2, 6), [7.84], base_days=[d(2021, 2, 2)]), bars, doc_day, doc_state)
    floor_b = FLOOR * expect25
    check(f"the pair read is the candidate price nearest the floor at a candidate base date: a plan document not read as "
          f"first-day pricing and a calendar base date are candidates, a first-day plan document is not; the gap at the first "
          f"locked document is kept, and a tie goes to the first locked document ({[(o['B'], o['label'], o['P'], round(o['gap'], 3), round(o['gap_at_b'], 3)) for o in (x, y, z, tie)] if all(o.get('gap_at_b') is not None for o in (x, y, z, tie)) else 'a gap at the first locked document missing'})",
          (x["B"], x["label"], x["P"]) == (d(2021, 2, 3), "plan document", 7.84) and abs(x["gap"]) < 1e-6
          and x["gap_at_b"] is not None and abs(x["gap_at_b"] - (7.84 - floor_b) / TICK) < 1e-6
          and (y["B"], y["label"], y["P"]) == (d(2021, 2, 8), "first locked document", 7.93) and abs(y["gap"] - (7.93 - floor_b) / TICK) < 1e-6
          and (z["B"], z["label"]) == (d(2021, 2, 3), "calendar base date read") and x["candidates"] == 2 and y["candidates"] == 1
          and (tie["B"], tie["label"], tie["candidates"]) == (d(2021, 2, 3), "first locked document", 2))
    bf, on = x["before"], x["on"]
    check(f"at an end on a Saturday the close before is Friday's and the close on or after is Monday's, each over the price carried "
          f"to its day, so M stays whole across the split ({bf}, {on})",
          bf["day"] == d(2021, 2, 5) and bf["days"] == 1 and abs(bf["carried"] - 7.84) < 1e-12 and abs(bf["M"] - 1.25) < 1e-12
          and on["day"] == d(2021, 2, 8) and on["days"] == 2 and abs(on["carried"] - 3.92) < 1e-12 and abs(on["M"] - 1.25) < 1e-12)
    w = read_plan(plan("600001", d(2021, 2, 3), d(2021, 2, 3), [7.84]), bars, doc_day, doc_state)
    check(f"at an end on a market day the close before is the day before, and the close on or after is the day itself "
          f"({w['before']['day']}, {w['on']['day']})", w["before"]["day"] == d(2021, 2, 2) and w["on"]["day"] == d(2021, 2, 3))
    iss = read_plan(plan("600001", d(2021, 2, 3), d(2021, 2, 9), [7.84], outcome="issued", P_table=3.92), bars, doc_day, doc_state)
    check(f"an issued plan's table price is set against its price carried to the issue day ({iss['issue']})",
          iss["issue"]["table"] == 3.92 and abs(iss["issue"]["gap"]) < 1e-6)
    s2 = _series([10.0] * 40, [10.0] * 40, [1] * 21 + [0] * 12 + [1] * 7)
    s2b = _series([10.0] * 40, [10.0] * 40)
    bars2 = type("Bars", (), {"series": lambda self, code: {"600003": s2}.get(code)})()
    st = read_plan(plan("600003", d(2021, 2, 8), d(2021, 2, 15), [8.0]), bars2, {}, {})
    fresh = read_plan(plan("600003", d(2021, 2, 8), d(2021, 2, 2), [8.0]), bars2, {}, {})
    check(f"a last close more than 10 days before the end is named stale and a first close more than 10 days after it late, and a "
          f"close from before the base date is read against the price taken back to its day ({st['before']}, {st['on']}, {st['stale']}, "
          f"{st['late']}, {fresh['before']['days']}, {fresh['stale']}, {fresh['late']})",
          st["before"]["day"] == d(2021, 2, 1) and st["before"]["days"] == 14 and abs(st["before"]["M"] - 1.25) < 1e-12 and st["stale"]
          and st["on"]["day"] == d(2021, 2, 18) and st["on"]["days"] == 3 and not st["late"] and fresh["before"]["days"] == 1
          and not fresh["stale"] and fresh["late"] and fresh["on"]["days"] == 16)
    states = [read_plan(plan("920001", d(2021, 2, 3), d(2021, 3, 1), [7.0]), bars, {}, {})["state"],
              read_plan(plan("600002", d(2021, 1, 20), d(2021, 3, 1), []), bars, {}, {})["state"],
              read_plan(plan("600002", d(2021, 1, 20), d(2021, 3, 1), [7.0]), bars, {}, {})["state"]]
    check(f"no bars, no price read with no VWAP20 on the first locked document's day, and no VWAP20 at any candidate base date "
          f"are named and read no further ({states})",
          states == ["no bars", "no price read", "no VWAP20 at any candidate base date"])
    r1 = read_plan(plan("600001", d(2021, 2, 8), d(2021, 2, 6), []), bars, doc_day, doc_state, "2024-05-10")
    r2 = read_plan(plan("600001", d(2021, 2, 3), d(2021, 2, 9), [], outcome="issued", P_table=3.92), bars, doc_day, doc_state)
    check(f"a plan with no price read takes 80% of VWAP20 on its first locked document's day rounded up to the tick, is named "
          f"apart and read on; the delisting date is kept ({r1['state']}, {r1.get('P')}, {r1.get('gap')}, {r1.get('before')}, "
          f"{r1['out_date']}, {r2.get('P')}, {r2.get('issue')})",
          r1["state"] == "price from the rule" and r1.get("P") == 7.93 and 0 <= r1["gap"] < 1 and abs(r1["before"]["M"] - 9.8 / 7.93) < 1e-12
          and r1["out_date"] == "2024-05-10" and r2.get("P") == 7.84 and abs(r2["issue"]["gap"]) < 1e-6)
    check(f"every outcome the plans script reads has a group ({sorted(set(B.OUTCOMES) - set(GROUPS))})",
          not set(B.OUTCOMES) - set(GROUPS) and set(GROUPS.values()) == set(GROUP_ORDER))
    check(f"the M bins cover the line once, from below to above ({[m_bin(m) for m in (0.0, 0.6999, 0.70, 0.85, 0.999, 1.0, 1.1999, 1.2, 1.4999, 1.5, 1.9999, 2.0, 12.0)]})",
          [m_bin(m) for m in (0.0, 0.6999, 0.70, 0.85, 0.999, 1.0, 1.1999, 1.2, 1.4999, 1.5, 1.9999, 2.0, 12.0)]
          == ["0.00 to 0.70", "0.00 to 0.70", "0.70 to 0.85", "0.85 to 1.00", "0.85 to 1.00", "1.00 to 1.20", "1.00 to 1.20",
              "1.20 to 1.50", "1.20 to 1.50", "1.50 to 2.00", "1.50 to 2.00", "2.00 and above", "2.00 and above"] and m_bin(None) is None)
    fd_hit, fd_n = floor_day(s2b, 8.0, 0, 39)
    fd_miss = floor_day(s2b, 5.0, 0, 39)
    fd_basis = floor_day(s, FLOOR * v25 / 2, 25, 25)
    check(f"the floor of another day is found by scanning the market days in the basis of the day before each, and missed when no "
          f"day pins the price ({fd_hit}, {fd_n}, {fd_miss}, {fd_basis}, {floor_day(s, FLOOR * v25, 25, 25)})",
          fd_hit == d(2021, 2, 1) and fd_n == 20 and fd_miss == (None, 0) and fd_basis == (None, 0)
          and floor_day(s, FLOOR * v25, 25, 25) == (d(2021, 2, 8), 1))
    ends = [end_of({"outcome": "pending", "out_date": "2024-01-05"}), end_of({"outcome": "pending", "out_date": None}),
            end_of({"outcome": "plan ended", "out_date": "2024-01-05"})]
    check(f"a pending plan whose stock is off the security list is read as delisted, and no other end is touched ({ends})",
          ends == ["stock delisted", "pending", "plan ended"])
    at = {"id": "a", "state": "read", "gap": 0.4, "B": d(2021, 2, 3), "P": 7.84, "prices": [7.84], "b": d(2021, 2, 3), "t": d(2021, 3, 1)}
    na = dict(at, id="b", gap=300.0)
    issue = dict(at, id="c", gap=300.0, issue={"gap": 0.2, "table": 9.0, "carried": 8.99})
    other = dict(at, id="d", gap=300.0)
    none = dict(at, id="e", gap=300.0, P=99.0, prices=[99.0], P_over_close=11.1)
    rule = dict(at, id="f", state="price from the rule")
    far = dict(at, id="g", gap=300.0)
    got = [price_state(at, False, [], None)[0], price_state(na, True, [], None)[0], price_state(issue, False, [], None)[0],
           price_state(dict(none, P=7.84, prices=[7.84]), False, [], s)[0], price_state(other, False, [at], None)[0],
           price_state(none, False, [], None)[0], price_state(rule, True, [], None)[0], price_state(other, False, [far], None)[0]]
    check(f"the price states run in their order: at the floor, net assets named, the issue price, the floor of another day, "
          f"another plan's price, not confirmed, and the rule's price apart ({got})",
          got == ["at the floor", "the floor with net assets named", "the issue price agrees", "the floor of another day",
                  "a price of another plan of this company", "not confirmed", "from the rule", "not confirmed"])
    rows = [{"bin": "0.00 to 0.70", "end": "plan ended", "days": 100}, {"bin": "0.00 to 0.70", "end": "issued", "days": 200},
            {"bin": "0.00 to 0.70", "end": "pending", "days": 300}, {"bin": "2.00 and above", "end": "issued", "days": 50},
            {"bin": "2.00 and above", "end": "moved to first day", "days": 70}]
    tab = {label: (n, dict(c), days) for label, n, c, days in bin_table(rows)}
    check(f"a bin table counts the groups in each bin and gives the median days ({tab['0.00 to 0.70']}, {tab['2.00 and above']}, "
          f"{tab['1.00 to 1.20']})",
          tab["0.00 to 0.70"] == (3, {"ended": 1, "issued at the locked price": 1, "pending": 1}, 200)
          and tab["2.00 and above"] == (2, {"issued at the locked price": 1, "the lock given up": 1}, 70)
          and tab["1.00 to 1.20"] == (0, {}, None))
    check(f"a title naming a related party marks the subscriber side, and the others do not "
          f"({[related_party(t) for t in (['关于与控股股东签署认购协议的公告'], ['关于签署认购协议暨关联交易的公告'], ['关于与特定对象签署认购协议的公告'], [], [None])]})",
          [related_party(t) for t in (["关于与控股股东签署认购协议的公告"], ["关于签署认购协议暨关联交易的公告"],
                                      ["关于与特定对象签署认购协议的公告"], [], [None])] == [True, True, False, False, False])
    check(f"the day buckets cover the line once ({[duration_bucket(x) for x in (0, 180, 181, 365, 366, 730, 731, 5000)]})",
          [duration_bucket(x) for x in (0, 180, 181, 365, 366, 730, 731, 5000)]
          == ["0 to 180 days", "0 to 180 days", "181 to 365 days", "181 to 365 days", "366 to 730 days", "366 to 730 days",
              "731 days and more", "731 days and more"])
    sh = [issued_share([{"end": e} for e in ("issued", "plan ended", "stock delisted", "pending", "moved to first day")]),
          issued_share([{"end": "pending"}]), issued_share([])]
    check(f"the issued share counts the plans that issued at the locked price over those and the ones that walked away, and is "
          f"none when neither is there ({sh})", sh == [(1, 2, 1 / 3), (0, 0, None), (0, 0, None)])
    mfix = [m_at({"P": 7.84, "B": d(2021, 2, 3)}, s, x) for x in (d(2021, 2, 6), d(2021, 2, 3))]
    check(f"M on a day of one's choosing takes the last close before it, not the close on it, over the price carried to that "
          f"day ({mfix})", all(abs(m - 9.8 / 7.84) < 1e-12 for m in mfix))
    sizes = [deal_size("发行股票的数量不超过150,501,672股，募集资金总额不超过45,000.00万元"),
             deal_size("本次发行数量不超过发行前总股本的30%，即不超过263,309,266股，募集资金总额为不超过1,053,237,064.00元"),
             deal_size("认购金额不超过人民币1.5亿元"), deal_size("本次发行的股票在深圳证券交易所上市")]
    check(f"the caps are read from a document: the shares, the money with its unit and its commas, and the share of the shares "
          f"before ({sizes})",
          sizes[0] == {"shares": 150501672.0, "money": 450000000.0, "ratio": None}
          and sizes[1] == {"shares": 263309266.0, "money": 1053237064.0, "ratio": 0.30}
          and sizes[2] == {"shares": None, "money": 150000000.0, "ratio": None}
          and sizes[3] == {"shares": None, "money": None, "ratio": None})
    sz = [size_of({"P": 5.0}, {"shares": 1800.0, "money": 10000.0}), size_of({"P": 5.0}, {"shares": 100.0, "money": 10000.0}),
          size_of({"P": 5.0}, {"money": 10000.0}), size_of({"P": 5.0}, {"shares": 1000.0}),
          size_of({"P": None}, {"money": 10000.0}), size_of({"P": 5.0}, {})]
    check(f"the money cap over the price is the count where both caps are read, with the share cap named when the two are more "
          f"than half apart; one cap alone is taken as it is; with neither there is no count ({sz})",
          sz == [(2000.0, "the money cap over the price, the share cap agrees"),
                 (2000.0, "the money cap over the price, the share cap more than half apart"),
                 (2000.0, "the money cap over the price"), (1000.0, "the share cap in the documents"),
                 (None, "no cap read"), (None, "no cap read")])
    tr = [transfer(1e8, 12.0, 10.0), transfer(1e8, 12.0, 10.0, 0.30), transfer(1e8, 12.0, 10.0, 0.10), transfer(1e8, 8.0, 10.0)]
    check(f"the transfer is n (Pm - P) over 100 million with the factor N/(N+n): a band from the 30% cap, one number when the "
          f"plan prints its own ratio, and the band the other way round when the stock sits below the price "
          f"({[(round(a, 4), round(b, 4)) for a, b in tr]})",
          abs(tr[0][0] - 2.0 / 1.3) < 1e-9 and abs(tr[0][1] - 2.0) < 1e-9 and abs(tr[1][0] - 2.0 / 1.3) < 1e-9
          and tr[1][0] == tr[1][1] and abs(tr[2][0] - 2.0 / 1.1) < 1e-9
          and abs(tr[3][0] + 2.0) < 1e-9 and abs(tr[3][1] + 2.0 / 1.3) < 1e-9)
    it = issued_transfer({"ISSUE_NUM": "100000000", "ISSUE_SHARE_BEFORE": "900000000", "ISSUE_PRICE": "10"}, 12.0)
    check(f"the transfer on an issue that happened uses the table's shares issued and shares before ({it})",
          abs(it - (1e8 * 9e8 * 2.0 / 1e9) / YI) < 1e-9
          and issued_transfer({"ISSUE_NUM": "100000000", "ISSUE_SHARE_BEFORE": None, "ISSUE_PRICE": "10"}, 12.0) is None)
    rec = b110_record_column(Path("no such file"))
    import tempfile as _tmp
    with _tmp.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.json"
        f.write_text(json.dumps({"criteria": [{"name": "B110-4", "detail": "Transfer: 网下定价发行 2018: 26 offerings, -98.38 / -84.82 / -; "
                                                                          "网下定价发行 2021: 95 offerings, 885.06 / 869.93 / -; "
                                                                          "网下询价配售 2021: 362 offerings, 899.38 / 931.89 / 758.11."}]}), encoding="utf-8")
        parsed = b110_record_column(f)
    check(f"B110's own column is read out of its record, the close on T and not the day before, and a missing record reads empty "
          f"({parsed}, {rec})", parsed == {"2018": (26, -98.38), "2021": (95, 885.06)} and rec == {})
    rows = [{"SEO_TYPE": "1", "ISSUE_DATE": "2021-02-03 00:00:00", "ISSUE_WAY": B110.PRICED_WAY, "SECURITY_CODE": "600001",
             "PRICE_PRINCIPLE": "定价基准日为董事会决议公告日", "TOTAL_RAISE_FUNDS": "1000", "NET_RAISE_FUNDS": "900",
             "ISSUE_NUM": "100000000", "ISSUE_SHARE_BEFORE": "900000000", "ISSUE_PRICE": "10"},
            {"SEO_TYPE": "1", "ISSUE_DATE": "2021-01-11 00:00:00", "ISSUE_WAY": B110.PRICED_WAY, "SECURITY_CODE": "600001",
             "PRICE_PRINCIPLE": "定价基准日为董事会决议公告日", "TOTAL_RAISE_FUNDS": "1000", "NET_RAISE_FUNDS": "900",
             "ISSUE_NUM": "100000000", "ISSUE_SHARE_BEFORE": "900000000", "ISSUE_PRICE": "10"},
            {"SEO_TYPE": "1", "ISSUE_DATE": "2021-02-03 00:00:00", "ISSUE_WAY": B110.PRICED_WAY, "SECURITY_CODE": "900999",
             "PRICE_PRINCIPLE": "定价基准日为董事会决议公告日", "TOTAL_RAISE_FUNDS": "1000", "NET_RAISE_FUNDS": "900",
             "ISSUE_NUM": "100000000", "ISSUE_SHARE_BEFORE": "900000000", "ISSUE_PRICE": "10"}]
    col = b110_column(bars, rows, since="2017-02-15")
    check(f"the recomputed column counts a cash placement priced in advance on the close of T, skips a suspended T and a stock "
          f"with no bars, and names each ({col})",
          col["by_year"] == {"2021": (1, round(1e8 * 9e8 * 2.0 / 1e9 / YI, 2))} and col["left"] == {"suspended on T": 1, "no bars": 1})
    check(f"the gap bins cover every gap once and put a gap of exactly one tick outside 'within a tick' "
          f"({[gap_bin(g) for g in (-150, -100, -10, -1, -0.99, 0, 0.99, 1, 10, 100, 150)]})",
          [gap_bin(g) for g in (-150, -100, -10, -1, -0.99, 0, 0.99, 1, 10, 100, 150)]
          == ["100 ticks or more below", "100 ticks or more below", "10 to 100 below", "1 to 10 below", "within a tick", "within a tick",
              "within a tick", "1 to 10 above", "10 to 100 above", "100 ticks or more above", "100 ticks or more above"])

    # --- part five: each criterion is seeded with an input that must make it fail (discipline 11f) ---
    def po(code="600001", b=d(2021, 3, 1), t=d(2021, 9, 1), end="plan ended", state="read", price_state="at the floor",
           close=12.0, carried=10.0, n=1e7, ratio=None, related=False, P=10.0, label="first locked document"):
        m = close / carried if carried else None
        side_b = {"day": t - dt.timedelta(days=1), "close": close, "days": 1, "carried": carried, "M": m}
        return {"id": f"{code}:{b.isoformat()}", "code": code, "name": "测试", "b": b, "t": t, "outcome": end, "end": end,
                "state": state, "price_state": price_state, "price_why": "seeded", "M": m, "M_on": m, "bin": m_bin(m),
                "days": (t - b).days, "related": related, "titles": ["关联交易"] if related else ["发行预案"], "n": n,
                "n_from": "the money cap over the price" if n else "no cap read", "ratio": ratio, "P": P, "prices": [P],
                "label": label, "gap": 0.0, "gap_at_b": 0.0, "B": b, "before": side_b, "on": dict(side_b, day=t, days=0),
                "walk_lo": None, "walk_hi": None, "out_date": None, "agreements": [f"a{code}{b}"], "documents": [],
                "detail": {}, "then": None, "net_asset": False}

    def band(o):
        o["walk_lo"], o["walk_hi"] = walk_band(o)
        return o

    good = [po(), po(code="600002")]
    c1 = criterion_price(good)
    c1_bad = criterion_price(good + [po(code="600003", price_state="not confirmed")])
    c1_rule = criterion_price(good + [po(code="600004", state="price from the rule", price_state="from the rule")])
    rule_n = c1_rule["payload"]["given the rule's price"]
    check(f"B120-1 passes when every price read falls in a named class, fails on one not confirmed, and is not moved by a plan "
          f"given the rule's price ({c1['passed']}, {c1_bad['passed']}, {c1_rule['passed']}, {rule_n})",
          c1["passed"] is True and c1_bad["passed"] is False and c1_rule["passed"] is True
          and rule_n == 1 and "from the rule" not in c1_rule["payload"]["states"]
          and len(c1_bad["payload"]["named"]["not confirmed"]) == 1)

    def deal(code="600001", day="2021-09-01", num="100000000", text="定价基准日为董事会决议公告日"):
        return {"SECURITY_CODE": code, "SECURITY_NAME_ABBR": "测试", "ISSUE_DATE": f"{day} 00:00:00", "ISSUE_NUM": num,
                "ISSUE_PRICE": "10", "PRICE_PRINCIPLE": text}

    issued = po(end="issued")
    issued["detail"] = {"key": B.issue_key(deal())}
    plans_ok = [issued, po(code="600002")]
    census = {"600001", "600002", "600003"}
    j_ok = criterion_join(plans_ok, [deal()], census, d(2026, 9, 16))
    j_late = criterion_join([dict(issued, t=d(2026, 9, 17))], [deal()], census, d(2026, 9, 16))
    j_back = criterion_join([dict(issued, t=d(2020, 1, 1))], [deal()], census, d(2026, 9, 16))
    twin = dict(po(code="600002"), agreements=list(issued["agreements"]))
    j_twin = criterion_join([issued, twin], [deal()], census, d(2026, 9, 16))
    j_miss = criterion_join(plans_ok, [deal(), deal(code="600003", num="7")], census, d(2026, 9, 16))
    j_off = criterion_join(plans_ok, [deal(), deal(code="830001", num="7")], census, d(2026, 9, 16))
    j_skip = criterion_join(plans_ok, [deal(), deal(code="300909", num="7")], census | {"300909"}, d(2026, 9, 16))
    held = dict(issued, documents=list(issued["agreements"]))
    j_held = criterion_join([held, po(code="600002")], [deal()], census, d(2026, 9, 16))
    check(f"B120-2 passes on one end a plan and every placement linked, and fails on an end after the data end, an end before "
          f"the first document, an announcement in two plans, and a placement of a company in the census with no plan; a "
          f"placement of a company the census never returned carries no verdict, and the one on file as matching funds is not "
          f"an object; a plan holding one announcement both as an agreement and as a plan document is counted and not failed "
          f"({[x['passed'] for x in (j_ok, j_late, j_back, j_twin, j_miss, j_off, j_skip, j_held)]}, "
          f"{j_held['payload']['held twice by one plan']})",
          [x["passed"] for x in (j_ok, j_late, j_back, j_twin, j_miss, j_off, j_skip, j_held)]
          == [True, False, False, False, False, None, True, True] and len(j_miss["payload"]["not_linked"]) == 1
          and j_held["payload"]["held twice by one plan"] == 1 and not j_held["payload"]["in_two_plans"])

    rng0 = np.random.default_rng(7)
    rise = [po(code=f"6{i:05d}", end="issued" if rng0.random() < min(0.95, 0.05 + i / 120) else "plan ended",
               close=10.0 + i / 12, b=d(2021 + i % 4, 3, 1), t=d(2022 + i % 4, 3, 1) + dt.timedelta(days=i))
            for i in range(120)]
    fall = [dict(o, end="plan ended" if o["end"] == "issued" else "issued") for o in rise]
    flat = [dict(o, end="issued" if rng0.random() < 0.5 else "plan ended") for o in rise]
    g_up = criterion_gradient(rise, draws=300)
    g_dn = criterion_gradient(fall, draws=300)
    g_flat = criterion_gradient(flat, draws=300)
    check(f"B120-3 reads a rise above the shuffle floor, the same table turned over as a fall, and no relation as inside the "
          f"floor ({g_up['passed']}, {g_dn['passed']}, {g_flat['passed']}; rho {g_up['payload']['gradient']['rho']:+.3f}, "
          f"{g_dn['payload']['gradient']['rho']:+.3f}, {g_flat['payload']['gradient']['rho']:+.3f}; floor "
          f"{g_up['payload']['gradient']['floor']:.3f})",
          g_up["passed"] is True and g_dn["passed"] is False and g_flat["passed"] is None
          and len(g_up["payload"]["cuts"]) > 6)
    check(f"a rank is the mean of the places tied values share, counted from the bottom, and the correlation follows the labels "
          f"({list(rank_of([3.0, 1.0, 2.0, 1.0]))}, {spearman([1.0, 2.0, 3.0, 4.0], [0.0, 0.0, 1.0, 1.0]):+.6f})",
          list(rank_of([3.0, 1.0, 2.0, 1.0])) == [3.0, 0.5, 2.0, 0.5]
          and abs(spearman([1.0, 2.0, 3.0, 4.0], [0.0, 0.0, 1.0, 1.0]) - 0.8944271909999159) < 1e-9
          and abs(spearman([1.0, 2.0, 3.0, 4.0], [1.0, 1.0, 0.0, 0.0]) + 0.8944271909999159) < 1e-9)
    conf = ([po(code=f"70{i:04d}", end="issued" if i < 10 else "plan ended", close=10.0, b=d(2021, 3, 1), t=d(2022, 3, 1))
             for i in range(30)]
            + [po(code=f"71{i:04d}", end="issued" if i < 25 else "plan ended", close=20.0, b=d(2024, 3, 1), t=d(2025, 3, 1))
               for i in range(30)])
    g_conf = criterion_gradient(conf, draws=300)
    gc = g_conf["payload"]["gradient"]
    check(f"B120-3 reads a gradient that lies wholly between the start years as inside the floor, since a shuffle inside a year "
          f"and length bucket leaves it where it stands, and the stricter of the two floors is the one the state is read "
          f"against ({g_conf['passed']}, rho {gc['rho']:+.4f}, floors "
          f"{[round(v['floor'], 4) for v in gc['nulls'].values()]}, taken {gc['floor']:.4f})",
          g_conf["passed"] is None and gc["state"] == "inside the floor" and gc["rho"] > 0.2
          and gc["nulls"]["labels shuffled inside the start year and the length"]["floor"]
          > gc["nulls"]["labels shuffled"]["floor"]
          and gc["floor"] == max(v["floor"] for v in gc["nulls"].values())
          and g_up["payload"]["gradient"]["state"] == "rises above the floor")

    walked = [band(po(code="600001")), band(po(code="600002", close=8.0))]
    m_ok = criterion_money(walked)
    m_none = criterion_money(walked + [po(code="600003", n=None)])
    m_open = criterion_money(walked + [po(code="600004")])
    m_flip = criterion_money(walked + [dict(po(code="600005"), walk_lo=5.0, walk_hi=1.0)])
    m_shut = criterion_money(walked + [band(po(code="600006", end="issued"))])
    check(f"B120-4 bands every plan that did not issue, names one with no cap read, fails on one with a size and no band and "
          f"on a band the wrong way round, and leaves an issued plan out "
          f"({m_ok['passed']}, {m_none['passed']}, {m_open['passed']}, {m_flip['passed']}, {m_ok['payload']['total']}, "
          f"{m_shut['payload']['total']['plans']})",
          m_ok["passed"] is True and m_none["passed"] is True and m_open["passed"] is False and m_flip["passed"] is False
          and m_ok["payload"]["total"]["plans"] == 2 and m_shut["payload"]["total"]["plans"] == 2
          and m_ok["payload"]["total"]["low"] < m_ok["payload"]["total"]["high"]
          and len(m_none["payload"]["named without a size"]) == 1)

    dead = _series([10.0] * 5, [10.0] * 5, [0] * 5)
    mv_bars = type("Bars", (), {"series": lambda self, code: dead if code == "600009" else s})()
    mv = [po(code="600001", end="moved to first day", b=day(2), t=day(26)),
          po(code="600002", end="moved to first day", b=day(2), t=day(28))]
    live = [po(code="600003", b=day(2), t=day(29)), po(code="600004", b=day(2), t=day(29)),
            po(code="600001", b=day(3), t=day(29), end="issued")]
    v_ok = criterion_moved(mv + live, live, mv_bars)
    v_none = criterion_moved(mv, [], mv_bars)
    v_named = criterion_moved(mv + [po(code="600005", end="moved to first day", b=day(2), t=day(27),
                                       price_state="not confirmed")] + live, live, mv_bars)
    v_bad = criterion_moved(mv + [po(code="600009", end="moved to first day", b=day(2), t=day(27))] + live, live, mv_bars)
    check(f"B120-5 reads every mover on the day before the first move, fails with no locked plan left to stand beside them and "
          f"on a mover whose price is confirmed and whose M does not read, and names a mover whose price is not confirmed "
          f"({v_ok['passed']}, {v_none['passed']}, {v_named['passed']}, {v_bad['passed']}, pivot {v_ok['payload']['pivot']})",
          v_ok["passed"] is True and v_none["passed"] is False and v_named["passed"] is True and v_bad["passed"] is False
          and v_ok["payload"]["pivot"] == (day(26) - dt.timedelta(days=1)).isoformat()
          and len(v_ok["payload"]["still locked"]) == 3
          and "issued" in v_ok["payload"]["later of the still locked"])

    ins = {"PDF texts by how they read": {"read": 2}, "census announcements": 9, "census windows not in the cache": 0}
    cv_ok = criterion_coverage(good, ins)
    thin = dict(po(code="600003"))
    thin["before"] = dict(thin["before"], day=None)
    cv_thin = criterion_coverage(good + [thin], ins)
    cv_twin = criterion_coverage(good + [po()], ins)
    cv_out = criterion_coverage(good + [po(code="600004", state="no bars")], ins)
    check(f"B120-6 gives one row a plan with a source for each field, fails on a plan whose price is confirmed and whose M has "
          f"no day and on the same plan twice, and lets a plan read no further through named "
          f"({cv_ok['passed']}, {cv_thin['passed']}, {cv_twin['passed']}, {cv_out['passed']}, {cv_ok['payload']['fields present']})",
          cv_ok["passed"] is True and cv_thin["passed"] is False and cv_twin["passed"] is False and cv_out["passed"] is True
          and cv_ok["payload"]["fields present"]["M"] == 2 and cv_ok["payload"]["fields present"]["size"] == 2
          and cv_out["payload"]["by_field"]["M"]["none"] == 1)

    same = {"2021": (95, 885.06), "2022": (80, 519.27)}
    r_ok = criterion_recompute({"by_year": dict(same), "left": {}}, dict(same), "seeded")
    r_off = criterion_recompute({"by_year": {**same, "2022": (80, 519.30)}, "left": {}}, dict(same), "seeded")
    r_cnt = criterion_recompute({"by_year": {**same, "2022": (79, 519.27)}, "left": {}}, dict(same), "seeded")
    r_gap = criterion_recompute({"by_year": {"2021": (95, 885.06)}, "left": {}}, dict(same), "seeded")
    r_bare = criterion_recompute({"by_year": dict(same), "left": {}}, {}, "seeded")
    r_none = criterion_recompute({"by_year": {}, "left": {}}, {}, "seeded")
    check(f"B120-7 passes when every year agrees on the count and the transfer, and fails on a year apart by more than a cent, "
          f"on a count apart, on a year missing on one side, on an empty record and on two empty columns "
          f"({[x['passed'] for x in (r_ok, r_off, r_cnt, r_gap, r_bare, r_none)]})",
          [x["passed"] for x in (r_ok, r_off, r_cnt, r_gap, r_bare, r_none)] == [True, False, False, False, False, False])

    pdata = {"frame": [po(code="600001", b=day(2), t=day(26)), po(code="600002", b=day(2), t=day(26))], "bars": bars,
             "sizes": {f"600001:{day(2).isoformat()}": {"money": 1e8, "shares": None, "ratio": None},
                       f"600002:{day(2).isoformat()}": {"money": None, "shares": None, "ratio": None}}}
    pok = prepare(pdata)
    p1, p2 = pdata["frame"]
    check(f"the frame prepared for the criteria carries the size read from the plan's own caps and the band that follows, and "
          f"leaves both empty where no cap is read ({p1['n']}, {p1['n_from']}, {p1['walk_lo']}, {p1['walk_hi']}, {p2['n']}, "
          f"{p2['walk_lo']}, {len(pok)})",
          abs(p1["n"] - 1e7) < 1e-6 and p1["n_from"] == "the money cap over the price" and p1["walk_lo"] is not None
          and p1["walk_lo"] < p1["walk_hi"] and p2["n"] is None and p2["walk_lo"] is None and len(pok) == 2
          and (p1["walk_lo"], p1["walk_hi"]) == walk_band(p1))

    check(f"a state the mapping does not hold raises rather than passing ({SHAPE_MAP})",
          verdict_of(["one end, after the first document and not after the data end"], SHAPE_MAP) is True
          and _raises(lambda: verdict_of(["a state no one mapped"], SHAPE_MAP)))
    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--frame", action="store_true", help="build the frame and print its objects")
    ap.add_argument("--tables", action="store_true", help="part two: where each price comes from, where each plan ended, M by bin")
    ap.add_argument("--splits", action="store_true", help="part three: the subscriber side, how long the plan ran, the 2026 batch")
    ap.add_argument("--money", action="store_true", help="part four: what walking away was worth, and B110-4 recomputed")
    ap.add_argument("--criteria", action="store_true", help="part five: the criteria, each with the states it maps")
    ap.add_argument("--record", action="store_true", help="part five, and write results/b120_readings.json")
    ap.add_argument("--rebuild-bars", action="store_true", help="rebuild data/cache/b120_bars.npz")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest or not (args.frame or args.tables or args.splits or args.money or args.criteria or args.record):
        return selftest()
    tail = ("" if args.frame else "_tables" if args.tables else "_splits" if args.splits
            else "_money" if args.money else "_criteria")
    out = P.RAW / f"readings_printout_{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}{tail}.txt"
    tee = F.Tee(sys.stdout, out)
    sys.stdout = tee
    try:
        print(f"printout also written to data/raw/b120/{out.name}")
        data = load(args.rebuild_bars)
        rc = report(data) if args.frame else 0
        rc = rc or (tables(data) if args.tables else 0)
        rc = rc or (splits(data) if args.splits else 0)
        rc = rc or (money(data) if args.money else 0)
        return rc or (criteria_report(data, args.record) if args.criteria or args.record else 0)
    finally:
        sys.stdout = tee.stream
        tee.fh.close()


if __name__ == "__main__":
    sys.exit(main())
