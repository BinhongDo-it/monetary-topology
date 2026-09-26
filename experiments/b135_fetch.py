"""B135 fetch, probe stage: who sold each block trade, three ways, and what a full pull costs.

**What the station reads.** From 2017-05-27 the exchange rules on share reductions lock for six
months any buyer who takes a block from a large holder or from a holder of pre-IPO or privately
placed shares. The same stock on the same day then carries two classes of buyer: the one who is
locked and the one on the open market. The station reads the step in the block discount at that
date. To do that each block has to be put in a class, and the block table only names brokerage
branches, not sellers.

**What this probe does.** It pulls the block table for a window around the rule date and joins it
three ways to a seller:

    1  director and officer holding changes whose stated method is a block trade (named person,
       day, shares, average price);
    2  changes by holders of five per cent or more, which carry a period, a share count and an
       average price; 2b is the same join restricted to rows whose market field names a block
       trade, the one place that table states a method;
    3  the unlock schedule already on disk for B110: a block on a stock that had pre-IPO or
       placement shares unlocked in the days before it.

It prints how many blocks each join names, by month and on each side of the rule date, and how
the three sets overlap. **It prints no discount by class.** The class key is chosen from the
counts, before any discount is read against it.

It also asks the source what its ratio column is (`D54`): the premium column against price over
close, and the discount column against price over close and over the previous close.

**Cost.** Three pages of the whole block table at three depths are timed and written to
`data/raw/b135/cost.json`; the full-pull hours are printed from that file and from nothing else.

**What it writes.** Nothing under `results/`. Pages land under `data/raw/b135/`, keyed by table,
filter window and the server's row count, and are reused on the next run. A cached page that
fails its checks is renamed with an `.expired` suffix and fetched again. Nothing is deleted.

    python experiments/b135_fetch.py --probe                          # window 2016-05-27 to 2018-05-26
    python experiments/b135_fetch.py --probe --window 2023-05-24:2025-05-23
    python experiments/b135_fetch.py --full                           # all three tables up to yesterday
    python experiments/b135_fetch.py --selftest                       # offline checks of every join here

A run that stops partway is resumed by running it again with the same `--full-hi`: pages on disk
are checked and kept, and only the missing ones are fetched.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import io
import json
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
RAW = ROOT / "data" / "raw" / "b135"
LIFT_STAGE_DIR = ROOT / "data" / "raw" / "b110" / "rpt_lift_stage"

sys.path.insert(0, str(HERE.parent))
import b110_probe as P  # noqa: E402  request, cache and cost helpers; their log and cache follow RAW

P.RAW = RAW

RULE_DATE = "2017-05-27"
DEFAULT_WINDOW = ("2016-05-27", "2018-05-26")
PAGE_SIZE = 500

BLOCK = ("RPT_DATA_BLOCKTRADE", "TRADE_DATE", ("TRADE_DATE", "SECURITY_CODE", "DAILY_RANK", "DEAL_VOLUME"))
EXEC = ("RPT_EXECUTIVE_HOLD_DETAILS", "CHANGE_DATE", ("CHANGE_DATE", "SECURITY_CODE", "PERSON_NAME", "CHANGE_SHARES"))
HOLDER = ("RPT_SHARE_HOLDER_INCREASE", "END_DATE", ("END_DATE", "SECURITY_CODE", "HOLDER_NAME", "CHANGE_NUM"))

# Unlock share types that make the holder a "specified shareholder" under the 2017 rules:
# shares issued before the IPO, and shares from a non-public offering. The probe prints every
# type string on the table, so this list is checked against the table rather than trusted.
PRE_IPO_MARKERS = ("首发原股东", "首发前")
PLACEMENT_MARKERS = P.PLACEMENT_MARKERS
LIFT_LOOKBACK_DAYS = (90, 180, 365)
LIFT_DEFAULT_DAYS = 180
PRICE_TOL = 0.005  # half a tick: an average price and a deal price that agree to the tick


# ---------------------------------------------------------------------------
# Fetching one filtered table
# ---------------------------------------------------------------------------

def window_filter(date_field: str, lo: str, hi: str) -> str:
    return f"({date_field}>='{lo}')({date_field}<='{hi}')"


def fetch_window(report: str, date_field: str, sort_cols: tuple[str, ...], lo: str, hi: str,
                 delay: float, keep_rows: bool = True, on_row=None) -> dict:
    """Every row of `report` whose `date_field` falls in [lo, hi], paged and cached.

    The server has to have applied the filter: every row is checked to fall in the window.
    With `keep_rows=False` the rows are handed one at a time to `on_row` and not held, so a
    whole-table pull stays at one page in memory.
    """
    params = {"reportName": report, "columns": "ALL", "sortColumns": ",".join(sort_cols),
              "sortTypes": ",".join("1" for _ in sort_cols), "pageSize": str(PAGE_SIZE),
              "pageNumber": "1", "source": "WEB", "client": "WEB",
              "filter": window_filter(date_field, lo, hi)}
    body = P.http_get(P.DATACENTER, params, report, delay)
    ok, why, obj = P.datacenter_page_ok(body, 1, PAGE_SIZE)
    if not ok:
        raise RuntimeError(f"{report} page 1: {why}")
    pages, count = obj["result"]["pages"], obj["result"]["count"]
    snap = RAW / report.lower() / f"{lo}_{hi}_count_{count}_ps{PAGE_SIZE}"
    rows, fetched = [], 0
    for page in range(1, pages + 1):
        path = snap / f"page_{page:04d}.json"
        if path.exists():
            ok, why, obj = P.datacenter_page_ok(path.read_bytes(), page, PAGE_SIZE, pages, count)
            if not ok:
                P.retire(path, why)
        if not path.exists():
            if page > 1:
                params["pageNumber"] = str(page)
                body = P.http_get(P.DATACENTER, params, report, delay)
            ok, why, obj = P.datacenter_page_ok(body, page, PAGE_SIZE, pages, count)
            if not ok:
                raise RuntimeError(f"{report} page {page}: {why}. The table moved during the run or "
                                   f"the page came back short; rerun to start a new snapshot.")
            P.atomic_write_bytes(path, body)
            fetched += 1
        for r in obj["result"]["data"]:
            d = (r.get(date_field) or "")[:10]
            if not lo <= d <= hi:
                raise RuntimeError(f"{report}: row dated {d!r} outside {lo}..{hi}; the filter was not applied")
            if on_row is not None:
                on_row(r)
        if keep_rows:
            rows.extend(obj["result"]["data"])
        obj = body = None
    return {"report": report, "window": [lo, hi], "count": count, "pages": pages, "rows": rows,
            "snapshot": snap.relative_to(ROOT).as_posix(), "pages_fetched_this_run": fetched}


def table_count(report: str, sort_col: str, delay: float, page: int = 1) -> tuple[int, int, bytes]:
    """(count, pages, body) of one unfiltered page; used for the cost section."""
    params = {"reportName": report, "columns": "ALL", "sortColumns": sort_col, "sortTypes": "-1",
              "pageSize": str(PAGE_SIZE), "pageNumber": str(page), "source": "WEB", "client": "WEB"}
    body = P.http_get(P.DATACENTER, params, report + "/unfiltered", delay)
    ok, why, obj = P.datacenter_page_ok(body, page, PAGE_SIZE)
    if not ok:
        raise RuntimeError(f"{report} unfiltered page {page}: {why}")
    return obj["result"]["count"], obj["result"]["pages"], body


def load_lift_stage() -> tuple[list[dict], str]:
    """The newest complete snapshot of B110's unlock schedule. Pages are checked, not trusted."""
    best = None
    for snap in sorted(LIFT_STAGE_DIR.glob("count_*_ps500")):
        if ".expired" in snap.name:
            continue
        count = int(snap.name.split("_")[1])
        pages = -(-count // 500)
        rows, good = [], True
        for page in range(1, pages + 1):
            path = snap / f"page_{page:04d}.json"
            if not path.exists():
                good = False
                break
            ok, _, obj = P.datacenter_page_ok(path.read_bytes(), page, 500, pages, count)
            if not ok:
                good = False
                break
            rows.extend(obj["result"]["data"])
        if good and (best is None or count > best[0]):
            best = (count, rows, snap.relative_to(ROOT).as_posix())
    if best is None:
        raise RuntimeError(f"no complete unlock snapshot under {LIFT_STAGE_DIR}")
    return best[1], best[2]


# ---------------------------------------------------------------------------
# The joins
# ---------------------------------------------------------------------------

def day(value) -> str:
    return (value or "")[:10]


def block_key(b: dict) -> tuple:
    return (b["SECURITY_CODE"], day(b["TRADE_DATE"]), b.get("DAILY_RANK"), b.get("DEAL_VOLUME"),
            b.get("DEAL_PRICE"), b.get("BUYER_CODE"), b.get("SELLER_CODE"))


def index_blocks(blocks: list[dict]) -> dict:
    """(code, day) -> list of blocks."""
    out = collections.defaultdict(list)
    for b in blocks:
        out[(b["SECURITY_CODE"], day(b["TRADE_DATE"]))].append(b)
    return out


def shares_equal(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 0.5
    except (TypeError, ValueError):
        return False


def price_agrees(avg, deal) -> bool | None:
    try:
        return abs(float(avg) - float(deal)) <= PRICE_TOL
    except (TypeError, ValueError):
        return None


def join_exec(blocks_by_day: dict, exec_rows: list[dict]) -> dict:
    """Candidate 1: an officer's change stated as a block trade, joined on code, day and shares."""
    stated = [r for r in exec_rows if "大宗" in (r.get("CHANGE_REASON") or "")]
    named, ambiguous, day_only, none = set(), 0, 0, 0
    price = collections.Counter()
    for r in stated:
        cands = blocks_by_day.get((r["SECURITY_CODE"], day(r["CHANGE_DATE"])), [])
        exact = [b for b in cands if shares_equal(b.get("DEAL_VOLUME"), abs(float(r.get("CHANGE_SHARES") or 0)))]
        if len(exact) == 1:
            named.add(block_key(exact[0]))
            price[str(price_agrees(r.get("AVERAGE_PRICE"), exact[0].get("DEAL_PRICE")))] += 1
        elif len(exact) > 1:
            ambiguous += 1
        elif cands:
            day_only += 1
        else:
            none += 1
    return {"records_stated_block": len(stated), "named": named, "records_ambiguous": ambiguous,
            "records_day_but_no_share_match": day_only, "records_no_block_that_day": none,
            "price_agrees_on_named": dict(price)}


def join_holder(blocks: list[dict], holder_rows: list[dict]) -> dict:
    """Candidate 2: a five-per-cent holder's reduction, joined on code and period.

    A block inside the period is named when its shares equal the reported change, or when the
    blocks inside the period add up to the reported change.
    """
    by_code = collections.defaultdict(list)
    for b in blocks:
        by_code[b["SECURITY_CODE"]].append(b)
    cuts = [r for r in holder_rows if (r.get("DIRECTION") or "") == "减持"]
    named_exact, named_sum = set(), set()
    counts = collections.Counter()
    for r in cuts:
        hi = day(r.get("END_DATE"))
        lo = day(r.get("START_DATE")) or hi
        want = abs(float(r.get("CHANGE_NUM") or 0)) * 1e4
        inside = [b for b in by_code.get(r["SECURITY_CODE"], []) if lo <= day(b["TRADE_DATE"]) <= hi]
        if not inside:
            counts["no_block_in_period"] += 1
            continue
        exact = [b for b in inside if shares_equal(b.get("DEAL_VOLUME"), want)]
        if len(exact) == 1:
            named_exact.add(block_key(exact[0]))
            counts["one_block_equals_change"] += 1
        elif len(exact) > 1:
            counts["several_blocks_equal_change"] += 1
        elif shares_equal(sum(float(b.get("DEAL_VOLUME") or 0) for b in inside), want):
            named_sum.update(block_key(b) for b in inside)
            counts["blocks_in_period_sum_to_change"] += 1
        else:
            counts["blocks_in_period_no_share_match"] += 1
    return {"reductions": len(cuts), "named_exact": named_exact, "named_sum": named_sum,
            "records": dict(counts)}


def holder_stated_block(rows: list[dict]) -> list[dict]:
    """Five-per-cent holder changes whose market field names a block trade. The field is the
    only place that table states a method; the first probe run found it there (2,748 of 8,583
    reductions in the 2016-05-27 to 2018-05-26 window)."""
    return [r for r in rows if "大宗" in (r.get("MARKET") or "")]


def lift_class(share_type: str) -> str | None:
    t = share_type or ""
    if any(m in t for m in PRE_IPO_MARKERS):
        return "pre_ipo"
    if any(m in t for m in PLACEMENT_MARKERS):
        return "placement"
    return None


def join_lift(blocks: list[dict], stage_rows: list[dict], lookback: int) -> dict:
    """Candidate 3: a block on a stock that had pre-IPO or placement shares unlocked in the
    `lookback` days up to the trade day, with the block no larger than that batch."""
    batches = collections.defaultdict(list)
    for r in stage_rows:
        kind = lift_class(r.get("FREE_SHARES_TYPE"))
        if kind:
            batches[r["SECURITY_CODE"]].append((day(r["FREE_DATE"]), float(r.get("CURRENT_FREE_SHARES") or 0) * 1e4, kind))
    named, kinds = set(), collections.Counter()
    for b in blocks:
        t = dt.date.fromisoformat(day(b["TRADE_DATE"]))
        lo = (t - dt.timedelta(days=lookback)).isoformat()
        vol = float(b.get("DEAL_VOLUME") or 0)
        hits = [k for (fd, sh, k) in batches.get(b["SECURITY_CODE"], []) if lo <= fd <= t.isoformat() and vol <= sh + 0.5]
        if hits:
            named.add(block_key(b))
            kinds["+".join(sorted(set(hits)))] += 1
    return {"lookback_days": lookback, "named": named, "by_share_type": dict(kinds)}


# ---------------------------------------------------------------------------
# What the source calls its ratio columns (D54)
# ---------------------------------------------------------------------------

def ratio_columns(blocks: list[dict]) -> dict:
    out = collections.Counter()
    worst = 0.0
    for b in blocks:
        try:
            p, c = float(b["DEAL_PRICE"]), float(b["CLOSE_PRICE"])
        except (TypeError, ValueError, KeyError):
            out["premium: price or close missing"] += 1
            continue
        pr = b.get("PREMIUM_RATIO")
        if pr is None:
            out["premium: column empty"] += 1
        else:
            diff = abs(float(pr) - (p / c - 1))
            worst = max(worst, diff)
            out["premium == price/close - 1" if diff < 1e-6 else "premium != price/close - 1"] += 1
        dr = b.get("DISCOUNT_RATIO")
        if dr is None:
            out["discount column: empty"] += 1
        else:
            c0 = b.get("PRE_CLOSE_PRICE")
            if abs(float(dr) - (p / c - 1)) < 1e-6:
                out["discount column == price/close - 1"] += 1
            elif c0 and abs(float(dr) - (p / float(c0) - 1)) < 1e-6:
                out["discount column == price/previous close - 1"] += 1
            else:
                out["discount column: neither"] += 1
    return {"counts": dict(sorted(out.items())), "premium_worst_abs_diff": f"{worst:.3e}"}


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def month_side(keys: set, rule: str) -> dict:
    months, side = collections.Counter(), collections.Counter()
    for k in keys:
        months[k[1][:7]] += 1
        side["before" if k[1] < rule else "from"] += 1
    return {"by_month": dict(sorted(months.items())), "before_rule": side["before"], "from_rule": side["from"]}


def overlap(sets: dict[str, set]) -> dict:
    names = sorted(sets)
    out = {}
    for mask in range(1, 2 ** len(names)):
        inside = [n for i, n in enumerate(names) if mask >> i & 1]
        outside = [n for i, n in enumerate(names) if not mask >> i & 1]
        s = set.intersection(*(sets[n] for n in inside))
        for n in outside:
            s = s - sets[n]
        out[" & ".join(inside) + (" only" if outside else "")] = len(s)
    return out


def run(lo: str, hi: str, delay: float) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"B135 probe, window {lo} .. {hi}, rule date {RULE_DATE}\n")

    tables = {}
    for report, field, sort in (BLOCK, EXEC, HOLDER):
        print(f"fetching {report} on {field} ...", flush=True)
        tables[report] = fetch_window(report, field, sort, lo, hi, delay)
        t = tables[report]
        print(f"  {t['count']} rows, {t['pages']} pages, {t['pages_fetched_this_run']} fetched now, {t['snapshot']}")
    blocks = tables[BLOCK[0]]["rows"]
    keys = [block_key(b) for b in blocks]
    dup = len(keys) - len(set(keys))
    print(f"\nblocks in window: {len(blocks)}; rows sharing a full key with another: {dup}")

    ratio = ratio_columns(blocks)
    print("\nwhat the ratio columns are (D54):")
    for k, v in ratio["counts"].items():
        print(f"  {v:7d}  {k}")
    print(f"  largest |premium - (price/close - 1)|: {ratio['premium_worst_abs_diff']}")

    reasons = collections.Counter(r.get("CHANGE_REASON") for r in tables[EXEC[0]]["rows"])
    markets = collections.Counter((r.get("DIRECTION"), r.get("MARKET")) for r in tables[HOLDER[0]]["rows"])
    print("\nofficer changes by stated method:")
    for k, v in reasons.most_common():
        print(f"  {v:7d}  {k}")
    print("five-per-cent holder changes by direction and market field:")
    for k, v in markets.most_common():
        print(f"  {v:7d}  {k}")

    stage, stage_snap = load_lift_stage()
    types = collections.Counter(r.get("FREE_SHARES_TYPE") for r in stage)
    print(f"\nunlock schedule {stage_snap}: {len(stage)} batches; share types and the class this probe gives them:")
    for k, v in types.most_common():
        print(f"  {v:7d}  {lift_class(k) or '-':9s}  {k}")

    by_day = index_blocks(blocks)
    c1 = join_exec(by_day, tables[EXEC[0]]["rows"])
    c2 = join_holder(blocks, tables[HOLDER[0]]["rows"])
    c2b = join_holder(blocks, holder_stated_block(tables[HOLDER[0]]["rows"]))
    c3 = {d: join_lift(blocks, stage, d) for d in LIFT_LOOKBACK_DAYS}

    print("\ncandidate 1, officer changes stated as block trades:")
    print(f"  records {c1['records_stated_block']}: named one block {len(c1['named'])}, "
          f"several equal blocks {c1['records_ambiguous']}, block that day but no share match "
          f"{c1['records_day_but_no_share_match']}, no block that day {c1['records_no_block_that_day']}")
    print(f"  average price agrees with the deal price to half a tick: {c1['price_agrees_on_named']}")
    print("candidate 2, five-per-cent holder reductions:")
    print(f"  reductions {c2['reductions']}: {c2['records']}")
    print(f"  blocks named: one block equals the change {len(c2['named_exact'])}, "
          f"blocks summing to the change {len(c2['named_sum'])}")
    print("candidate 2b, the same reductions restricted to a market field that names a block trade:")
    print(f"  reductions {c2b['reductions']}: {c2b['records']}")
    print(f"  blocks named: one block equals the change {len(c2b['named_exact'])}, "
          f"blocks summing to the change {len(c2b['named_sum'])}")
    print("candidate 3, a pre-IPO or placement unlock in the days before the block:")
    for d, r in c3.items():
        print(f"  lookback {d:3d} days: {len(r['named'])} blocks, by share type {r['by_share_type']}")

    sets = {"1_officer": c1["named"], "2_holder": c2["named_exact"] | c2["named_sum"],
            "2b_holder_block": c2b["named_exact"] | c2b["named_sum"],
            "3_unlock180": c3[LIFT_DEFAULT_DAYS]["named"]}
    ov = overlap(sets)
    print(f"\noverlap of the three named sets (candidate 3 at {LIFT_DEFAULT_DAYS} days):")
    for k, v in ov.items():
        print(f"  {v:7d}  {k}")
    sides = {n: month_side(s, RULE_DATE) for n, s in sets.items()}
    print("\nnamed blocks on each side of the rule date, and all blocks:")
    all_side = month_side(set(keys), RULE_DATE)
    print(f"  {'all blocks':12s} before {all_side['before_rule']:6d}  from {all_side['from_rule']:6d}")
    for n, s in sides.items():
        print(f"  {n:12s} before {s['before_rule']:6d}  from {s['from_rule']:6d}")
    months = sorted(all_side["by_month"])
    print("\nby month:  all  " + "  ".join(f"{n:>11s}" for n in sides))
    for m in months:
        print(f"  {m}  {all_side['by_month'][m]:5d}  " + "  ".join(f"{sides[n]['by_month'].get(m, 0):11d}" for n in sides))

    print("\ncost of a full pull (D38): timing three depths of the whole block table ...", flush=True)
    counts = {}
    for report, field, sort in (BLOCK, EXEC, HOLDER):
        n, pages, _ = table_count(report, field, delay)
        counts[report] = {"count": n, "pages": pages}
    bp = counts[BLOCK[0]]["pages"]
    for page in (bp // 2, bp):
        table_count(BLOCK[0], BLOCK[1], delay, page)
    timing = P.timing_table(P.read_request_log())
    cost = {"page_size": PAGE_SIZE, "tables": counts, "timing": timing}
    P.atomic_write_bytes(RAW / "cost.json", json.dumps(cost, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))
    for report in counts:
        row = timing.get(report + "/unfiltered") or timing.get(report)
        print(P.cost_line(f"{report} full", counts[report]["pages"], row, delay))

    summary = {
        "window": [lo, hi], "rule_date": RULE_DATE,
        "tables": {k: {kk: v[kk] for kk in ("count", "pages", "snapshot")} for k, v in tables.items()},
        "blocks": len(blocks), "blocks_sharing_full_key": dup, "ratio_columns": ratio,
        "officer_methods": {str(k): v for k, v in reasons.items()},
        "holder_direction_market": {f"{k[0]}|{k[1]}": v for k, v in markets.items()},
        "lift_snapshot": stage_snap, "lift_types": {str(k): v for k, v in types.items()},
        "candidate_1": {k: (len(v) if isinstance(v, set) else v) for k, v in c1.items()},
        "candidate_2": {k: (len(v) if isinstance(v, set) else v) for k, v in c2.items()},
        "candidate_2b": {k: (len(v) if isinstance(v, set) else v) for k, v in c2b.items()},
        "candidate_3": {str(d): {"named": len(r["named"]), "by_share_type": r["by_share_type"]} for d, r in c3.items()},
        "overlap": ov, "sides": sides, "all_blocks_side": all_side, "full_tables": counts,
    }
    P.atomic_write_bytes(RAW / f"probe_summary_{lo}_{hi}.json",
                         json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))
    print(f"\nwrote {(RAW / f'probe_summary_{lo}_{hi}.json').relative_to(ROOT).as_posix()} and data/raw/b135/cost.json")
    return 0


# ---------------------------------------------------------------------------
# Selftest: every join is fed an input that must fail it, and it has to fail (11f)
# ---------------------------------------------------------------------------

def selftest() -> int:
    def blk(code, d, vol, price=10.0, close=10.5, rank=1, prem=None, disc=None, pre=10.4):
        return {"SECURITY_CODE": code, "TRADE_DATE": d + " 00:00:00", "DEAL_VOLUME": vol, "DEAL_PRICE": price,
                "CLOSE_PRICE": close, "PRE_CLOSE_PRICE": pre, "DAILY_RANK": rank, "BUYER_CODE": "b", "SELLER_CODE": "s",
                "PREMIUM_RATIO": price / close - 1 if prem is None else prem,
                "DISCOUNT_RATIO": price / close - 1 if disc is None else disc}

    blocks = [blk("000001", "2017-06-01", 100000), blk("000001", "2017-06-01", 50000, rank=2),
              blk("000002", "2017-06-02", 70000), blk("000003", "2016-06-03", 30000)]
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    by_day = index_blocks(blocks)
    ex = [{"SECURITY_CODE": "000001", "CHANGE_DATE": "2017-06-01 00:00:00", "CHANGE_SHARES": -100000,
           "CHANGE_REASON": "大宗交易", "AVERAGE_PRICE": 10.0},
          {"SECURITY_CODE": "000002", "CHANGE_DATE": "2017-06-02 00:00:00", "CHANGE_SHARES": -70000,
           "CHANGE_REASON": "集中竞价", "AVERAGE_PRICE": 10.0},
          {"SECURITY_CODE": "000001", "CHANGE_DATE": "2017-06-01 00:00:00", "CHANGE_SHARES": -99999,
           "CHANGE_REASON": "大宗交易", "AVERAGE_PRICE": 10.0}]
    r1 = join_exec(by_day, ex)
    check("candidate 1 names the block with the stated shares", len(r1["named"]) == 1)
    check("candidate 1 ignores a change whose stated method is not a block", r1["records_stated_block"] == 2)
    check("candidate 1 does not name a block whose shares differ by one", r1["records_day_but_no_share_match"] == 1)
    check("candidate 1 price check reads the average price", r1["price_agrees_on_named"] == {"True": 1})
    ex_bad = [dict(ex[0], SECURITY_CODE="000009")]
    check("candidate 1 names nothing on another stock", len(join_exec(by_day, ex_bad)["named"]) == 0)

    hold = [{"SECURITY_CODE": "000001", "DIRECTION": "减持", "START_DATE": "2017-05-30 00:00:00",
             "END_DATE": "2017-06-05 00:00:00", "CHANGE_NUM": 15.0},
            {"SECURITY_CODE": "000002", "DIRECTION": "减持", "START_DATE": None,
             "END_DATE": "2017-06-02 00:00:00", "CHANGE_NUM": 7.0},
            {"SECURITY_CODE": "000003", "DIRECTION": "增持", "START_DATE": None,
             "END_DATE": "2016-06-03 00:00:00", "CHANGE_NUM": 3.0}]
    r2 = join_holder(blocks, hold)
    check("candidate 2 names blocks that sum to the change", len(r2["named_sum"]) == 2)
    check("candidate 2 names a single-day exact match", len(r2["named_exact"]) == 1)
    check("candidate 2 skips an increase", r2["reductions"] == 2)
    marked = [dict(hold[0], MARKET="二级市场"), dict(hold[1], MARKET="大宗交易"),
              dict(hold[1], MARKET="二级市场以及大宗交易"), dict(hold[1], MARKET=None)]
    check("candidate 2b keeps only a market field that names a block", len(holder_stated_block(marked)) == 2)
    moved = [dict(hold[1], END_DATE="2017-06-01 00:00:00")]
    check("candidate 2 names nothing outside the period", len(join_holder(blocks, moved)["named_exact"]) == 0)

    stage = [{"SECURITY_CODE": "000001", "FREE_DATE": "2017-03-01 00:00:00", "CURRENT_FREE_SHARES": 20.0,
              "FREE_SHARES_TYPE": "首发原股东限售股份"},
             {"SECURITY_CODE": "000002", "FREE_DATE": "2017-05-01 00:00:00", "CURRENT_FREE_SHARES": 5.0,
              "FREE_SHARES_TYPE": "定向增发机构配售股份"},
             {"SECURITY_CODE": "000003", "FREE_DATE": "2016-06-01 00:00:00", "CURRENT_FREE_SHARES": 50.0,
              "FREE_SHARES_TYPE": "股权激励限售股份"}]
    r3 = join_lift(blocks, stage, 180)
    check("candidate 3 names both blocks after a pre-IPO unlock", {k[0] for k in r3["named"]} == {"000001"})
    check("candidate 3 skips a block larger than the batch", not any(k[0] == "000002" for k in r3["named"]))
    check("candidate 3 skips an incentive-share unlock", not any(k[0] == "000003" for k in r3["named"]))
    check("candidate 3 skips an unlock outside the lookback", len(join_lift(blocks, stage, 60)["named"]) == 0)

    ratio = ratio_columns(blocks + [blk("000004", "2017-06-05", 1, prem=0.5, disc=10.0 / 10.4 - 1)])
    check("ratio check flags a premium that is not price over close",
          ratio["counts"].get("premium != price/close - 1") == 1)
    check("ratio check reads a discount column taken against the previous close",
          ratio["counts"].get("discount column == price/previous close - 1") == 1)

    ov = overlap({"a": {1, 2, 3}, "b": {2, 3, 4}, "c": {3}})
    check("overlap counts each region once", sum(ov.values()) == 4 and ov["a & b & c"] == 1 and ov["a & b only"] == 1)
    check("month_side splits at the rule date", month_side({("x", "2017-05-26"), ("x", "2017-05-27")}, RULE_DATE)
          ["before_rule"] == 1)
    check("window filter names both bounds", window_filter("TRADE_DATE", "a", "b") == "(TRADE_DATE>='a')(TRADE_DATE<='b')")

    print(f"\n{len(fails)} failed" if fails else "\nall checks pass")
    return 1 if fails else 0


FULL_LO = "1990-01-01"


def full(hi: str, delay: float) -> int:
    """All three tables from FULL_LO to `hi`, paged and cached like the probe window.

    `hi` freezes the pull: rows dated after it do not enter, so a table that grows while the pull
    runs does not move the pages already on disk. After the pull every table is checked for rows
    that share a full key (a sort that ties can move a row across a page boundary between two
    requests, which shows up as one row twice and another missing).
    """
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"B135 full pull, {FULL_LO} .. {hi}\n")
    keyers = {BLOCK[0]: block_key,
              EXEC[0]: lambda r: (r.get("SECURITY_CODE"), day(r.get("CHANGE_DATE")), r.get("PERSON_NAME"),
                                  r.get("CHANGE_SHARES"), r.get("AVERAGE_PRICE"), r.get("CHANGE_REASON"),
                                  r.get("POSITION_NAME"), r.get("DSE_PERSON_NAME")),
              HOLDER[0]: lambda r: (r.get("SECURITY_CODE"), day(r.get("END_DATE")), day(r.get("START_DATE")),
                                    r.get("HOLDER_NAME"), r.get("CHANGE_NUM_SYMBOL"), r.get("MARKET"),
                                    day(r.get("NOTICE_DATE")), r.get("TRADE_AVERAGE_PRICE"))}
    out = {}
    for report, field, sort in (BLOCK, EXEC, HOLDER):
        print(f"fetching {report} on {field} ...", flush=True)
        seen, tally = set(), {"rows": 0, "dup": 0, "first": "9999"}

        def on_row(r, keyer=keyers[report], field=field):
            k = hash(keyer(r))
            tally["rows"] += 1
            if k in seen:
                tally["dup"] += 1
            seen.add(k)
            tally["first"] = min(tally["first"], day(r.get(field)))

        t = fetch_window(report, field, sort, FULL_LO, hi, delay, keep_rows=False, on_row=on_row)
        seen.clear()
        print(f"  {t['count']} rows, {t['pages']} pages, {t['pages_fetched_this_run']} fetched now, "
              f"earliest {tally['first']}, rows sharing a full key {tally['dup']}, {t['snapshot']}", flush=True)
        out[report] = {"count": t["count"], "pages": t["pages"], "rows_read": tally["rows"],
                       "earliest": tally["first"], "rows_sharing_full_key": tally["dup"], "snapshot": t["snapshot"]}
    P.atomic_write_bytes(RAW / f"full_manifest_{FULL_LO}_{hi}.json",
                         json.dumps({"window": [FULL_LO, hi], "tables": out}, ensure_ascii=False, indent=1,
                                    sort_keys=True).encode("utf-8"))
    print(f"\nwrote data/raw/b135/full_manifest_{FULL_LO}_{hi}.json")
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--full-hi", default=(dt.date.today() - dt.timedelta(days=1)).isoformat())
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--window", default=":".join(DEFAULT_WINDOW))
    ap.add_argument("--delay", type=float, default=1.0)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.probe:
        lo, hi = a.window.split(":")
        return run(lo, hi, a.delay)
    if a.full:
        return full(a.full_hi, a.delay)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
