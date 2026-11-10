"""B135 readings: block trades, the six-month lock on buyers from large and
specified holders, and the second price of the same stock on the same day.

Reads the three tables ``experiments/b135_fetch.py --full`` froze on disk and
B110's unlock schedule. Nothing is fetched here.

**The classes.** Lock-buy: a block joined to a five-per-cent holder's
reduction whose market field names a block trade (candidate 2b of the probe).
It is a proxy read off the seller's side. From 2017-05-27 the buyer of such a
block may not sell for six months unless the shares sold were ones the large
holder had bought by auction, which the rules exempt (SSE and SZSE, 2017; the
later versions keep the distinction); the holder table carries the seller, the
way of selling, dates, shares and price, and not where the shares came from. So
the class is "blocks matched to a large holder's reduction stated as a block
trade", and how many of its buyers were in fact exempt is not known here.
Unlocked: a block that none of the probe's four candidates names and whose stock
had no pre-IPO or placement shares unlocked in the 365 days up to the trade. The
joins are the probe's, written over arrays so that the full table fits in
memory; on the probe window they name the probe's blocks exactly (B135-7).

**The price limit.** A block pinned at the day's lower limit is left out. The
limit is the board's, and 5 % for a main-board stock under risk warning on that
day: the daily bars on disk carry the day's own ST flag (the block table carries
only today's short name), and a block is joined to it by stock and day. A block
with no bar on disk for its stock and day keeps the board's limit and is counted
as not known. The 5 % is not carried past 2026-07-06, when the exchanges' revised
trading rules took effect.

**The step.** ``delta = 1 - deal / close``. For a date, the median of the
class's ``delta`` over the ``w`` trading days from the date less the median
over the ``w`` before it, blocks pinned at the day's price limit left out.
Its placebo floor is the same statistic on the first trading day of every
month from 2012 to 2025, less six months around each of the three rule dates.

Run from the repository root with the project's virtual environment:

    python experiments/b135_readings.py --selftest
    python experiments/b135_readings.py --run [--no-write]
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

RAW = ROOT / "data" / "raw" / "b135"
CACHE = ROOT / "data" / "cache" / "b135"
RECORD = ROOT / "results" / "b135_blocktrade.json"
CLOSED = True

FULL = "1990-01-01_2026-09-25"
PROBE = ("2016-05-27", "2018-05-26")
RULES = {"2016-01-09": "officer and large-holder limits, no buyer lock",
         "2017-05-27": "exchange rules: buyer locked six months",
         "2024-05-24": "CSRC order 224: buyer lock kept"}
LOCK_DATE = "2017-05-27"
WINDOWS = (20, 60, 120)
PLACEBO_YEARS = (2012, 2025)
PLACEBO_GAP_DAYS = 183
LIFT_LOOKBACK = 180
UNLOCKED_LOOKBACK = 365
TICK = 0.01

BLOCK_FIELDS = ("SECURITY_CODE", "SECURITY_NAME_ABBR", "TRADE_DATE", "DAILY_RANK",
                "DEAL_VOLUME", "DEAL_PRICE", "DEAL_AMT", "BUYER_CODE", "SELLER_CODE",
                "CLOSE_PRICE", "PRE_CLOSE_PRICE", "PREMIUM_RATIO", "TOTAL_SHARES",
                "UNLIMITED_A_SHARES", "TRADE_MARKET_CODE", "SECUCODE")


# --------------------------------------------------------------------------
# loading


def snapshot_dir(table: str, window: str = FULL) -> Path:
    base = RAW / table
    hits = [p for p in base.glob(f"{window}_count_*_ps500") if ".expired" not in p.name]
    if len(hits) != 1:
        raise RuntimeError(f"{table}: {len(hits)} snapshots for {window}")
    return hits[0]


def read_pages(snap: Path, fields=None):
    count = int(snap.name.split("_count_")[1].split("_")[0])
    pages = -(-count // 500)
    rows = 0
    for page in range(1, pages + 1):
        obj = json.loads((snap / f"page_{page:04d}.json").read_text(encoding="utf-8"))
        data = obj["result"]["data"]
        rows += len(data)
        for r in data:
            yield r if fields is None else {k: r.get(k) for k in fields}
    if rows != count:
        raise RuntimeError(f"{snap.name}: read {rows} rows against {count}")


def load_blocks(snap: Path | None = None) -> pd.DataFrame:
    """The block table's needed columns, cached by snapshot name."""
    snap = snapshot_dir("rpt_data_blocktrade") if snap is None else snap
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"blocks_{snap.name}.csv.gz"
    if cache.exists():
        df = pd.read_csv(cache, dtype={"SECURITY_CODE": str, "BUYER_CODE": str,
                                       "SELLER_CODE": str, "TRADE_MARKET_CODE": str})
    else:
        df = pd.DataFrame.from_records(read_pages(snap, BLOCK_FIELDS))
        df.to_csv(cache, index=False, compression="gzip")
        df = pd.read_csv(cache, dtype={"SECURITY_CODE": str, "BUYER_CODE": str,
                                       "SELLER_CODE": str, "TRADE_MARKET_CODE": str})
    df["day"] = df["TRADE_DATE"].str[:10]
    return df


def load_table(table: str, fields) -> pd.DataFrame:
    return pd.DataFrame.from_records(read_pages(snapshot_dir(table), fields))


def load_lift() -> pd.DataFrame:
    import b135_fetch as F
    rows, _ = F.load_lift_stage()
    out = []
    for r in rows:
        kind = F.lift_class(r.get("FREE_SHARES_TYPE"))
        if kind:
            out.append({"code": r["SECURITY_CODE"], "day": (r.get("FREE_DATE") or "")[:10],
                        "shares": float(r.get("CURRENT_FREE_SHARES") or 0) * 1e4,
                        "kind": kind})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# the joins, over arrays; the probe's dict joins are the reference (B135-7)

HOLDER_FIELDS = ("SECURITY_CODE", "START_DATE", "END_DATE", "DIRECTION", "CHANGE_NUM",
                 "MARKET", "HOLDER_NAME")
EXEC_FIELDS = ("SECURITY_CODE", "CHANGE_DATE", "CHANGE_SHARES", "CHANGE_REASON",
               "AVERAGE_PRICE", "PERSON_NAME")


def _day(x) -> str:
    """A date field's day, and "" for a missing one, as the dict joins read it."""
    return x[:10] if isinstance(x, str) else ""


def _num(x) -> float:
    """A number field, and zero for a missing one, as the dict joins read it."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(v) else v


def code_index(blocks: pd.DataFrame) -> dict:
    """code -> (sorted days, volumes, row labels)."""
    out = {}
    order = blocks.sort_values(["SECURITY_CODE", "day"], kind="mergesort")
    for code, g in order.groupby("SECURITY_CODE", sort=False):
        out[code] = (g["day"].to_numpy(dtype="U10"), g["DEAL_VOLUME"].to_numpy(dtype=float),
                     g.index.to_numpy())
    return out


def join_holder(idx: dict, rows: pd.DataFrame) -> tuple[set, dict]:
    """A reduction names one block whose shares equal the change, or all the
    blocks in its period when they add up to it (the probe's rule)."""
    named, counts = set(), {"reductions": 0, "no_block_in_period": 0,
                            "one_block_equals_change": 0, "several_blocks_equal_change": 0,
                            "blocks_in_period_sum_to_change": 0,
                            "blocks_in_period_no_share_match": 0}
    cuts = rows[rows["DIRECTION"].fillna("") == "减持"]
    counts["reductions"] = len(cuts)
    for code, s, e, n in zip(cuts["SECURITY_CODE"], cuts["START_DATE"], cuts["END_DATE"],
                             cuts["CHANGE_NUM"]):
        hi = _day(e)
        lo = _day(s) or hi
        want = abs(_num(n)) * 1e4
        days, vols, labs = idx.get(code, (np.array([], dtype="U10"), np.array([]), np.array([])))
        a, b = np.searchsorted(days, lo, "left"), np.searchsorted(days, hi, "right")
        if b <= a:
            counts["no_block_in_period"] += 1
            continue
        v = vols[a:b]
        exact = np.flatnonzero(np.abs(v - want) < 0.5)
        if exact.size == 1:
            named.add(int(labs[a + exact[0]]))
            counts["one_block_equals_change"] += 1
        elif exact.size > 1:
            counts["several_blocks_equal_change"] += 1
        elif abs(float(v.sum()) - want) < 0.5:
            named.update(int(x) for x in labs[a:b])
            counts["blocks_in_period_sum_to_change"] += 1
        else:
            counts["blocks_in_period_no_share_match"] += 1
    return named, counts


def join_exec(blocks: pd.DataFrame, rows: pd.DataFrame) -> set:
    """An officer's change stated as a block trade names the one block that
    day with the same shares."""
    stated = rows[rows["CHANGE_REASON"].fillna("").str.contains("大宗")].copy()
    stated["day"] = stated["CHANGE_DATE"].map(_day)
    stated["want"] = stated["CHANGE_SHARES"].map(_num).abs()
    stated["rid"] = np.arange(len(stated))
    b = blocks[["SECURITY_CODE", "day", "DEAL_VOLUME"]].reset_index()
    m = stated.merge(b, on=["SECURITY_CODE", "day"], how="inner")
    m = m[(m["DEAL_VOLUME"] - m["want"]).abs() < 0.5]
    per = m.groupby("rid")["index"].agg(list)
    return {int(v[0]) for v in per if len(v) == 1}


def join_lift(blocks: pd.DataFrame, lift: pd.DataFrame, lookback: int,
              size_check: bool = True) -> set:
    """A block on a stock with pre-IPO or placement shares unlocked in the
    ``lookback`` days up to the trade, no larger than that batch."""
    b = blocks[["SECURITY_CODE", "day", "DEAL_VOLUME"]].reset_index()
    b = b[b["SECURITY_CODE"].isin(set(lift["code"]))]
    m = b.merge(lift.rename(columns={"code": "SECURITY_CODE", "day": "free_day"}),
                on="SECURITY_CODE", how="inner")
    t = pd.to_datetime(m["day"])
    lo = (t - pd.to_timedelta(lookback, unit="D")).dt.strftime("%Y-%m-%d")
    keep = (m["free_day"] >= lo) & (m["free_day"] <= m["day"])
    if size_check:
        keep &= m["DEAL_VOLUME"] <= m["shares"] + 0.5
    return set(int(x) for x in m.loc[keep, "index"].unique())


def classes(blocks, holder, execs, lift) -> dict:
    idx = code_index(blocks)
    c2, n2 = join_holder(idx, holder)
    stated = holder[holder["MARKET"].fillna("").str.contains("大宗")]
    c2b, n2b = join_holder(idx, stated)
    c1 = join_exec(blocks, execs)
    c3 = join_lift(blocks, lift, LIFT_LOOKBACK)
    near = join_lift(blocks, lift, UNLOCKED_LOOKBACK, size_check=False)
    return {"c1": c1, "c2": c2, "c2b": c2b, "c3": c3, "unlock_365": near,
            "c2_counts": n2, "c2b_counts": n2b}


# --------------------------------------------------------------------------
# the frame, the limits, the step

A_PREFIXES = ("000", "001", "002", "003", "300", "301", "600", "601", "603", "605",
              "688", "689")
CHINEXT_20 = "2020-08-24"
ST_MAIN_LIMIT = 0.05
ST_RULE_END = "2026-07-06"


def board_limit(code3: pd.Series, day: pd.Series, st=None) -> np.ndarray:
    """The day's price limit by board, and 5 % for a main-board stock that the
    day's own bar flags as under risk warning. ``st`` is 1, 0 or NaN per row (NaN:
    no bar on disk for that stock and day); without it the board's limit alone."""
    star = code3.isin(("688", "689"))
    chinext = code3.isin(("300", "301"))
    lim = np.where(star | (chinext & (day >= CHINEXT_20)), 0.20, 0.10)
    if st is not None:
        main = ~(star | chinext)
        lim = np.where((np.asarray(st) == 1) & main & (day < ST_RULE_END), ST_MAIN_LIMIT, lim)
    return lim


def st_flags() -> tuple[dict, str]:
    """code -> (day ordinals, the bar's isST) from the raw daily bars on disk, cached
    by the store's signature."""
    import b110_placements as BP
    files = BP.store_files()
    sig = BP.signature(files)
    cache = CACHE / "st_flags.npz"
    if cache.exists():
        try:
            with np.load(cache, allow_pickle=False) as z:
                if str(z["signature"]) == sig:
                    codes, starts = z["codes"], z["starts"]
                    return ({str(c): (z["ordinal"][starts[i]:starts[i + 1]], z["st"][starts[i]:starts[i + 1]])
                             for i, c in enumerate(codes)}, f"read {cache.name}")
        except (OSError, ValueError, KeyError):
            pass
    codes, starts, ords, flags = [], [0], [], []
    for f in files:
        obj = json.loads(f.read_bytes())
        fields = obj.get("fields") or []
        if "isST" not in fields or "date" not in fields:
            continue
        i_d, i_s = fields.index("date"), fields.index("isST")
        rows = [r for r in obj.get("rows", []) if r[i_s] in ("0", "1")]
        codes.append(f.stem)
        ords.extend(dt.date.fromisoformat(r[i_d]).toordinal() for r in rows)
        flags.extend(int(r[i_s]) for r in rows)
        starts.append(len(ords))
    CACHE.mkdir(parents=True, exist_ok=True)
    arrays = {"codes": np.array(codes, dtype="U6"), "starts": np.array(starts, dtype=np.int64),
              "ordinal": np.array(ords, dtype=np.int32), "st": np.array(flags, dtype=np.int8)}
    np.savez(cache, signature=np.array(sig), **arrays)
    out = {c: (arrays["ordinal"][arrays["starts"][i]:arrays["starts"][i + 1]],
               arrays["st"][arrays["starts"][i]:arrays["starts"][i + 1]]) for i, c in enumerate(codes)}
    return out, f"built {cache.name} from {len(files)} store files"


def st_of(a: pd.DataFrame, flags: dict | None) -> np.ndarray:
    """Each block's ST flag on its own day: 1, 0, or NaN where no bar is on disk."""
    out = np.full(len(a), np.nan)
    if not flags:
        return out
    ords = pd.to_datetime(a["day"]).map(dt.date.toordinal).to_numpy(dtype=np.int64)
    codes = a["SECURITY_CODE"].to_numpy()
    for code in pd.unique(codes):
        hit = flags.get(str(code))
        if hit is None:
            continue
        days, st = hit
        rows = np.flatnonzero(codes == code)
        pos = np.searchsorted(days, ords[rows])
        ok = (pos < len(days)) & (days[np.minimum(pos, len(days) - 1)] == ords[rows])
        out[rows[ok]] = st[pos[ok]]
    return out


def frame(blocks: pd.DataFrame, cl: dict, flags: dict | None = None) -> pd.DataFrame:
    a = blocks[blocks["SECURITY_CODE"].str[:3].isin(A_PREFIXES)].copy()
    a["st"] = st_of(a, flags)
    a["lim_board"] = board_limit(a["SECURITY_CODE"].str[:3], a["day"])
    a["lim"] = board_limit(a["SECURITY_CODE"].str[:3], a["day"], a["st"])
    a["delta"] = 1.0 - a["DEAL_PRICE"] / a["CLOSE_PRICE"]
    a["ratio_gap"] = (a["PREMIUM_RATIO"] - (a["DEAL_PRICE"] / a["CLOSE_PRICE"] - 1)).abs()
    tick = TICK / a["PRE_CLOSE_PRICE"]
    r = a["DEAL_PRICE"] / a["PRE_CLOSE_PRICE"] - 1
    a["outside_limit"] = (r > a["lim"] + tick + 1e-9) | (r < -a["lim"] - tick - 1e-9)
    close_r = a["CLOSE_PRICE"] / a["PRE_CLOSE_PRICE"] - 1
    a["close_outside_limit"] = close_r.abs() > a["lim"] + tick + 1e-9
    a["pinned"] = ~a["outside_limit"] & (r <= -a["lim"] + tick + 1e-9)
    # the same two flags on the board's limit alone, to count what the ST flag moved
    out_b = (r > a["lim_board"] + tick + 1e-9) | (r < -a["lim_board"] - tick - 1e-9)
    a["pinned_board_only"] = ~out_b & (r <= -a["lim_board"] + tick + 1e-9)
    a["outside_board_only"] = out_b
    lock = a.index.isin(sorted(cl["c2b"]))
    named = set().union(cl["c1"], cl["c2"], cl["c2b"], cl["c3"], cl["unlock_365"])
    unl = ~a.index.isin(sorted(named))
    a["cls"] = np.where(lock, "lock", np.where(unl, "unlocked", "other"))
    a["usable"] = (a["ratio_gap"] <= 1e-9) & ~a["outside_limit"] & ~a["pinned"]
    return a


def calendar(a: pd.DataFrame) -> np.ndarray:
    return np.array(sorted(a["day"].unique()), dtype="U10")


def step(a: pd.DataFrame, cal: np.ndarray, cls: str, date: str, w: int) -> dict:
    pos = int(np.searchsorted(cal, date, "left"))
    if pos - w < 0 or pos + w > cal.size:
        return {"step": float("nan"), "n_before": 0, "n_after": 0}
    before, after = cal[pos - w:pos], cal[pos:pos + w]
    s = a[(a["cls"] == cls) & a["usable"]]
    x = s.loc[s["day"].isin(before), "delta"].to_numpy()
    y = s.loc[s["day"].isin(after), "delta"].to_numpy()
    if x.size == 0 or y.size == 0:
        return {"step": float("nan"), "n_before": int(x.size), "n_after": int(y.size)}
    return {"step": float(np.median(y) - np.median(x)), "median_before": float(np.median(x)),
            "median_after": float(np.median(y)), "n_before": int(x.size),
            "n_after": int(y.size), "first_after": str(after[0])}


def placebo_dates(cal: np.ndarray) -> list[str]:
    out = []
    rules = [dt.date.fromisoformat(d) for d in RULES]
    for y in range(PLACEBO_YEARS[0], PLACEBO_YEARS[1] + 1):
        for mo in range(1, 13):
            first = f"{y:04d}-{mo:02d}-01"
            pos = int(np.searchsorted(cal, first, "left"))
            if pos >= cal.size:
                continue
            d = str(cal[pos])
            dd = dt.date.fromisoformat(d)
            if all(abs((dd - r).days) >= PLACEBO_GAP_DAYS for r in rules):
                out.append(d)
    return out


def steps_with_floor(a, cal, cls: str, date: str, placebos: list[str]) -> dict:
    out = {}
    for w in WINDOWS:
        s = step(a, cal, cls, date, w)
        pl = np.array([step(a, cal, cls, p, w)["step"] for p in placebos])
        pl = pl[np.isfinite(pl)]
        s["placebo_n"] = int(pl.size)
        s["placebo_min"] = float(pl.min()) if pl.size else float("nan")
        s["placebo_max"] = float(pl.max()) if pl.size else float("nan")
        s["above_all"] = bool(pl.size and s["step"] > pl.max())
        s["below_all"] = bool(pl.size and s["step"] < pl.min())
        s["rank_above"] = int((pl < s["step"]).sum()) if np.isfinite(s["step"]) else None
        out[w] = s
    return out


def rival_cell(steps: dict) -> tuple:
    """B135-3's map, cell by cell (11c). PASS means the rival is wrong."""
    vals = [steps[w] for w in WINDOWS]
    if any(not np.isfinite(v["step"]) for v in vals):
        return None, "unread", "a window has no lock-buy block"
    if all(v["step"] > 0 and v["above_all"] for v in vals):
        return True, "B", "positive and above every placebo on every window"
    if all(not v["above_all"] and not v["below_all"] for v in vals):
        return False, "C", "inside the placebo range on every window"
    if all(v["step"] < 0 and v["below_all"] for v in vals):
        return False, "both_unmet", "negative and below every placebo on every window"
    return None, "unread", "the windows disagree on sign or place"


RIVAL_MAP = {"positive and above every placebo on every window": (True, "B"),
             "inside the placebo range on every window": (False, "C"),
             "negative and below every placebo on every window": (False, "both_unmet"),
             "the windows disagree, or a window is empty": (None, "unread")}


# --------------------------------------------------------------------------
# faster steps: each class indexed by calendar position

class Steps:
    """The class's usable blocks as (calendar position, delta), sorted, so a
    window is two binary searches."""

    def __init__(self, a: pd.DataFrame, cal: np.ndarray) -> None:
        self.cal = cal
        pos = {d: i for i, d in enumerate(cal)}
        self.by = {}
        u = a[a["usable"]]
        for cls, g in u.groupby("cls"):
            p = g["day"].map(pos).to_numpy(dtype=np.int64)
            o = np.argsort(p, kind="mergesort")
            self.by[cls] = (p[o], g["delta"].to_numpy(dtype=float)[o])

    def step(self, cls: str, date: str, w: int) -> dict:
        p0 = int(np.searchsorted(self.cal, date, "left"))
        if p0 - w < 0 or p0 + w > self.cal.size or cls not in self.by:
            return {"step": float("nan"), "n_before": 0, "n_after": 0}
        pos, d = self.by[cls]
        a, b, c = (np.searchsorted(pos, p0 - w, "left"), np.searchsorted(pos, p0, "left"),
                   np.searchsorted(pos, p0 + w, "left"))
        x, y = d[a:b], d[b:c]
        if x.size == 0 or y.size == 0:
            return {"step": float("nan"), "n_before": int(x.size), "n_after": int(y.size)}
        return {"step": float(np.median(y) - np.median(x)), "median_before": float(np.median(x)),
                "median_after": float(np.median(y)), "n_before": int(x.size),
                "n_after": int(y.size), "first_after": str(self.cal[p0])}

    def with_floor(self, cls: str, date: str, placebos: list[str]) -> dict:
        out = {}
        for w in WINDOWS:
            s = self.step(cls, date, w)
            pl = np.array([self.step(cls, p, w)["step"] for p in placebos])
            pl = pl[np.isfinite(pl)]
            s.update(placebo_n=int(pl.size),
                     placebo_min=float(pl.min()) if pl.size else float("nan"),
                     placebo_max=float(pl.max()) if pl.size else float("nan"),
                     above_all=bool(pl.size and s["step"] > pl.max()),
                     below_all=bool(pl.size and s["step"] < pl.min()),
                     rank_above=int((pl < s["step"]).sum()) if np.isfinite(s["step"]) else None)
            out[w] = s
        return out


# --------------------------------------------------------------------------
# B135-5: each lock-buy block against Longstaff's bound

SIGMA_WINDOWS = (60, 120, 250)
LOCK_YEARS = 0.5


def bars_for(codes) -> tuple:
    import b110_placements as BP
    files = [BP.STORE_DIR / f"{c}.json" for c in sorted(codes) if (BP.STORE_DIR / f"{c}.json").exists()]
    bars, how = BP.load_bars(files, cache=CACHE / "bars.npz")
    return bars, how, BP


def st_object(a: pd.DataFrame) -> dict:
    """What the day's ST flag moved, printed: coverage, and the blocks it takes out."""
    known = a["st"].notna()
    st1 = a["st"] == 1
    five = st1 & (a["lim"] == ST_MAIN_LIMIT)
    usable_board = (a["ratio_gap"] <= 1e-9) & ~a["outside_board_only"] & ~a["pinned_board_only"]
    moved = usable_board & ~a["usable"]
    back = a["usable"] & ~usable_board
    return {"a_share_blocks": int(len(a)), "with_a_bar_that_day": int(known.sum()),
            "without_a_bar_that_day": int((~known).sum()), "flagged_st": int(st1.sum()),
            "flagged_st_at_5pct": int(five.sum()),
            "flagged_st_not_at_5pct": int((st1 & ~five).sum()),
            "taken_out_by_the_st_limit": {c: int((moved & (a["cls"] == c)).sum())
                                          for c in ("lock", "unlocked", "other")},
            "of_which_pinned_at_the_5pct_limit": int((moved & a["pinned"]).sum()),
            "of_which_outside_the_5pct_limit": int((moved & a["outside_limit"]).sum()),
            "made_usable_by_the_st_limit": int(back.sum())}


def longstaff_rows(a: pd.DataFrame, bars, BP) -> pd.DataFrame:
    lock = a[(a["cls"] == "lock") & a["usable"]]
    rows = []
    for code, g in lock.groupby("SECURITY_CODE"):
        s = bars.series(str(code))
        for idx, day, delta in zip(g.index, g["day"], g["delta"]):
            rec = {"idx": int(idx), "code": str(code), "day": day, "delta": float(delta)}
            if s is not None:
                r = BP.row_of(s, day)
                if r is None:
                    last = BP.last_row_on_or_before(s, day)
                    r = None if last is None else last + 1
                for n in SIGMA_WINDOWS:
                    sig = BP.sigma_before(s, r, n) if r is not None else None
                    rec[f"sigma_{n}"] = sig
                    rec[f"excess_{n}"] = (None if sig is None
                                          else float(delta) - BP.longstaff(sig, LOCK_YEARS))
            rows.append(rec)
    return pd.DataFrame(rows)


def criterion_longstaff(lr: pd.DataFrame, n_lock: int) -> tuple[dict, dict]:
    cols = [f"excess_{n}" for n in SIGMA_WINDOWS]
    have = lr.dropna(subset=cols) if len(lr) and all(c in lr for c in cols) else lr.iloc[0:0]
    over = {n: int((have[f"excess_{n}"] > 0).sum()) for n in SIGMA_WINDOWS} if len(have) else {}
    signs = np.sign(have[cols].to_numpy()) if len(have) else np.zeros((0, 3))
    mixed = int((np.abs(signs.sum(axis=1)) < len(SIGMA_WINDOWS)).sum()) if len(have) else 0
    years = have["day"].str[:4] if len(have) else pd.Series(dtype=str)
    by_year = ({y: {n: int((g[f"excess_{n}"] > 0).sum()) for n in SIGMA_WINDOWS} | {"blocks": len(g)}
                for y, g in have.groupby(years)} if len(have) else {})
    names = (have.loc[(have[cols] > 0).all(axis=1), ["code", "day", "delta"] + cols]
             .sort_values("day").to_dict("records") if len(have) else [])

    def part(mask_all, mask_have) -> dict:
        h = have[mask_have] if len(have) else have
        sg = np.sign(h[cols].to_numpy()) if len(h) else np.zeros((0, 3))
        return {"usable_blocks": int(mask_all.sum()) if len(lr) else 0, "with_sigma_all_windows": int(len(h)),
                "over_bound": {n: int((h[f"excess_{n}"] > 0).sum()) for n in SIGMA_WINDOWS} if len(h) else {},
                "sign_disagrees_across_windows": int((np.abs(sg.sum(axis=1)) < len(SIGMA_WINDOWS)).sum())}

    # the six-month lock exists from LOCK_DATE: the bound is a comparison under the rule only there
    periods = ({"before the rule": part(lr["day"] < LOCK_DATE, have["day"] < LOCK_DATE),
                "from the rule": part(lr["day"] >= LOCK_DATE, have["day"] >= LOCK_DATE)}
               if len(lr) and "day" in lr else {})
    obj = {"lock_blocks": n_lock, "with_sigma_all_windows": int(len(have)),
           "over_bound": over, "sign_disagrees_across_windows": mixed,
           "periods": periods, "rule_date": LOCK_DATE,
           "by_year": by_year, "over_on_every_window": names}
    ok = (len(have) > 0 and n_lock > 0 and bool(periods)
          and sum(p["with_sigma_all_windows"] for p in periods.values()) == len(have)
          and sum(p["usable_blocks"] for p in periods.values()) == len(lr))
    after = periods.get("from the rule", {})
    return ({"name": "B135-5  each block of the lock-buy proxy class: its discount against "
                     "Longstaff's bound for six months, sigma over 60, 120 and 250 trading days, "
                     "before and from the rule date apart",
             "kind": "own_reading", "passed": bool(ok),
             "detail": (f"{len(have)} of {n_lock} usable blocks of the class have sigma on all three "
                        f"windows; above the bound: " + ", ".join(f"{n} days {over.get(n)}"
                                                                  for n in SIGMA_WINDOWS)
                        + f"; the sign moves across windows on {mixed}. From {LOCK_DATE}, where a "
                        f"six-month lock exists: {after.get('with_sigma_all_windows')} blocks, above the "
                        f"bound " + ", ".join(f"{n} days {after.get('over_bound', {}).get(n)}"
                                              for n in SIGMA_WINDOWS))}, obj)


# --------------------------------------------------------------------------
# B135-6: the borrowed amount, from the exchanges' own figures

YEARBOOKS = ROOT / "data" / "processed" / "b135_yearbooks.json"
REMAINING_YEARS = (0.5, 1.0, 3.0)


def borrowed_rows(a: pd.DataFrame, lr: pd.DataFrame, BP) -> tuple[dict, dict]:
    yb = json.loads(YEARBOOKS.read_text(encoding="utf-8"))
    sse = {int(k): v for k, v in yb["sse_market_value"].items()}
    z = yb["szse_ten_year"]
    years_z = z["market_value_total"]["years"] + z["market_value_total_b"]["years"][1:]
    tot = dict(zip(years_z, z["market_value_total"]["values"] + z["market_value_total_b"]["values"][1:]))
    neg = dict(zip(years_z, z["market_value_negotiable"]["values"]
                   + z["market_value_negotiable_b"]["values"][1:]))
    lock = a[(a["cls"] == "lock") & a["usable"]]
    med_disc = lock.groupby(lock["day"].str[:4].astype(int))["delta"].median()
    med_sig = (lr.dropna(subset=["sigma_250"]).groupby(lr["day"].str[:4].astype(int))["sigma_250"]
               .median() if len(lr) and "sigma_250" in lr else pd.Series(dtype=float))
    rows, missing = {}, []
    for y in range(2012, 2026):
        r = {}
        if y in sse and sse[y]["negotiable_100m_yuan"] is not None:
            r["sse_locked_100m_yuan"] = sse[y]["market_value_100m_yuan"] - sse[y]["negotiable_100m_yuan"]
            r["sse_share_of_cap"] = r["sse_locked_100m_yuan"] / sse[y]["market_value_100m_yuan"]
        else:
            missing.append(f"SSE {y}")
        if y in tot:
            # the ten-year pages are in 10 billion yuan: ten of the 100M-yuan unit
            r["szse_locked_100m_yuan"] = (tot[y] - neg[y]) * 10.0
            r["szse_share_of_cap"] = (tot[y] - neg[y]) / tot[y]
        else:
            missing.append(f"SZSE {y}")
        total = sum(r.get(k, 0.0) for k in ("sse_locked_100m_yuan", "szse_locked_100m_yuan"))
        r["locked_both_100m_yuan"] = total if "sse_locked_100m_yuan" in r and "szse_locked_100m_yuan" in r else None
        if y in med_disc.index and r["locked_both_100m_yuan"] is not None:
            r["lock_buy_median_discount"] = float(med_disc[y])
            r["at_median_discount_100m_yuan"] = total * (1 - float(med_disc[y]))
        if y in med_sig.index and r["locked_both_100m_yuan"] is not None:
            sg = float(med_sig[y])
            r["median_sigma_250"] = sg
            for L in REMAINING_YEARS:
                # the bound is on a discount; above one it says only that the block may be
                # worth nothing, so the value floors at zero
                lb = BP.longstaff(sg, L)
                r[f"longstaff_{L}y"] = lb
                r[f"at_longstaff_{L}y_100m_yuan"] = total * max(0.0, 1 - lb)
        rows[y] = r
    ok = all(rows[y].get("locked_both_100m_yuan") is not None for y in range(2012, 2025))
    # the unit against a figure read by hand: Shenzhen 2024, total 33,041 and negotiable
    # 28,124 ten-billion yuan, so 49,170 hundred-million yuan locked
    ok = ok and abs(rows[2024]["szse_locked_100m_yuan"] - 49170.0) < 0.5
    return ({"name": "B135-6  the borrowed amount: locked shares valued at the close, from the "
                     "exchanges' own total and negotiable market values; and the same amount under "
                     "four stated scenarios (the year's median lock-buy discount, or Longstaff's bound "
                     "at the year's median sigma for half a year, one and three years, each applied "
                     "to the whole amount)",
             "kind": "own_reading", "passed": bool(ok),
             "detail": (f"years 2012-2025; both exchanges read in 2012-2024; missing "
                        f"{', '.join(missing) if missing else 'none'}; the four valuations are "
                        f"parameter scenarios, one discount or one sigma for the whole amount: no "
                        f"stock's own locked value, sigma or remaining term enters them")},
            {"rows": rows, "missing": missing,
             "scenario_note": ("a median over traded blocks is no bound on a sum weighted by locked "
                               "value: the model's lower value of the whole is the sum over stocks of "
                               "locked shares x close x max(0, 1 - bound(sigma_i, term_i)), which needs "
                               "each stock's locked value, sigma and remaining term")})


# --------------------------------------------------------------------------
# B135-1, -2, -3, -4, -7 as criteria

SSE_BOARD_B = ("900",)


def criterion_ratio(a: pd.DataFrame) -> tuple[dict, dict]:
    worst = float(a["ratio_gap"].max())
    breaches = a[a["outside_limit"]]
    kinds = {"close also outside the limit": int(breaches["close_outside_limit"].sum()),
             "close inside the limit": int((~breaches["close_outside_limit"]).sum())}
    ok = worst <= 1e-9 and not bool((a["outside_limit"] & a["usable"]).any())
    listing = breaches[["SECURITY_CODE", "day", "DEAL_PRICE", "PRE_CLOSE_PRICE", "CLOSE_PRICE",
                        "close_outside_limit"]].to_dict("records")
    return ({"name": "B135-1  the source's PREMIUM_RATIO is deal over close less one on every "
                     "A-share block; blocks outside their board's price limit are named and left out",
             "kind": "instrument", "passed": bool(ok),
             "detail": (f"{len(a)} A-share blocks, largest ratio gap {worst:.1e}; outside the day's "
                        f"limit {len(breaches)} ({kinds['close also outside the limit']} on days the "
                        f"close itself is outside, {kinds['close inside the limit']} with the close "
                        f"inside)" + (f"; the day's ST flag is on disk for {int(a['st'].notna().sum())} "
                                      f"of them and takes out "
                                      f"{sum(st_object(a)['taken_out_by_the_st_limit'].values())} more"
                                      if "st" in a else ""))},
            {"ratio_gap_max": worst, "outside_limit": listing, "kinds": kinds,
             "pinned_at_lower_limit": int(a["pinned"].sum()),
             "pinned_at_lower_limit_by_class": ({str(k): int(v) for k, v in
                                                 a[a["pinned"]].groupby("cls").size().items()}
                                                if "cls" in a else None),
             "st": st_object(a) if "st" in a else None})


def criterion_exchange(blocks: pd.DataFrame) -> tuple[dict, dict]:
    yb = json.loads(YEARBOOKS.read_text(encoding="utf-8"))
    y = blocks["day"].str[:4].astype(int)
    c3 = blocks["SECURITY_CODE"].str[:3]
    sh_a = c3.isin(("600", "601", "603", "605", "688", "689"))
    sh_b = c3.isin(SSE_BOARD_B)
    rows, off = {}, []
    for yr, v in sorted(yb["sse_block_trades"].items(), key=lambda kv: int(kv[0])):
        yr = int(yr)
        ma, mb = sh_a & (y == yr), sh_b & (y == yr)
        n = int(ma.sum() + mb.sum())
        amt_a = float(blocks.loc[ma, "DEAL_AMT"].sum()) / 1e8
        amt_b = float(blocks.loc[mb, "DEAL_AMT"].sum()) / 1e8
        rows[yr] = {"sse_trades": v["trades"], "ours_trades": n, "sse_amount": v["amount_100m_yuan"],
                    "ours_amount_a": round(amt_a, 4), "ours_amount_b_as_stored": round(amt_b, 4),
                    "page": f"volume {v['volume']} page {v['page']}"}
        if n != v["trades"] or abs(amt_a + amt_b - v["amount_100m_yuan"]) > 0.005:
            off.append(yr)
    ok = bool(rows) and not off
    return ({"name": "B135-2  yearly block trades against the exchange's own yearbook: Shanghai "
                     "stocks, trades and amount; Shenzhen's fact books carry none",
             "kind": "known_answer", "passed": bool(ok),
             "detail": (f"Shanghai {min(rows)}-{max(rows)}, {len(rows)} years; outside the last printed "
                        f"digit in {len(off)} ({off}); trades differ by at most "
                        f"{max(abs(r['ours_trades'] - r['sse_trades']) for r in rows.values())}, amounts "
                        f"by at most "
                        f"{max(abs(r['ours_amount_a'] + r['ours_amount_b_as_stored'] - r['sse_amount']) for r in rows.values()):.2f} "
                        f"(100M yuan); Shenzhen source-missing every year")},
            {"sse": rows, "outside_rounding": off, "szse": "source-missing"})


def criterion_rival(steps: dict) -> dict:
    passed, grid, why = rival_cell(steps)
    c = {"name": "B135-3  the 2017-05-27 step in the lock-buy proxy class's median discount, 20, 60 "
                 "and 120 trading days, against the same statistic on every placebo month start",
         "kind": "rival", "passed": passed, "grid": grid,
         "rival_premise": ("a scalar price on the node: one stock on one day is one position with "
                           "one price, whoever buys"),
         "rival_entailment": ("a rule that changes only the buyer's class, not the stock, leaves "
                              "the node's scalar where it was: no step in deal over close at "
                              "2017-05-27"),
         "rival_shape": "point prediction (zero step)",
         "detail": (why + "; " + "; ".join(
             f"w {w}: {v['step']:+.4f}, above {v['rank_above']} of {v['placebo_n']} placebos"
             for w, v in steps.items()))}
    if grid == "unread":
        c["grid_note"] = {"B": "not claimed: the step is above every placebo on the 120-day "
                               "window only", "C": "not claimed: the step is positive on every window"}
    return c


def criterion_other_dates(tab: dict) -> dict:
    vals = [v["step"] for d in tab.values() for c in d.values() for v in c.values()]
    ok = len(vals) == 3 * 2 * len(WINDOWS) - len(WINDOWS) and all(np.isfinite(vals))
    return {"name": "B135-4  the same step at 2016-01-09 and 2024-05-24 for both classes, and at "
                    "2017-05-27 for the unlocked class",
            "kind": "own_reading", "passed": bool(ok),
            "detail": f"{len(vals)} steps, {'all finite' if ok else 'a cell missing'}"}


def criterion_coverage(blocks: pd.DataFrame, a: pd.DataFrame, cl: dict, probe_same: dict) -> tuple[dict, dict]:
    cov = pd.DataFrame(index=blocks.index)
    cov["a_share"] = blocks.index.isin(a.index)
    cov["cls"] = "not_a_share"
    cov.loc[a.index, "cls"] = a["cls"]
    cov["usable"] = False
    cov.loc[a.index, "usable"] = a["usable"]
    cov["year"] = blocks["day"].str[:4].astype(int)
    tab = cov.groupby(["year", "cls"]).size().unstack(fill_value=0)
    ok = (len(cov) == len(blocks) and cov.index.is_unique and bool(probe_same)
          and all(probe_same.values()))
    return ({"name": "B135-7  every block one row, with its identity source and class; the array "
                     "joins name the probe's blocks exactly on the probe snapshot",
             "kind": "bookkeeping", "passed": bool(ok),
             "detail": (f"{len(cov)} rows, keys unique; probe reproduction "
                        + ", ".join(f"{k} {'same' if v else 'differs'}" for k, v in probe_same.items()))},
            {"by_year_and_class": {int(y): {k: int(v) for k, v in r.items()} for y, r in tab.iterrows()},
             "usable_lock_by_year": {int(y): int(n) for y, n in
                                     cov[(cov.cls == "lock") & cov.usable].groupby("year").size().items()},
             "lock_proxy": {"a_share_blocks": int((cov.cls == "lock").sum()),
                            "from_the_rule_date": int(((cov.cls == "lock")
                                                       & (blocks["day"] >= LOCK_DATE)).sum()),
                            "share_source_confirmed": 0,
                            "share_source": ("not carried by the holder table: which of these blocks sold "
                                             "auction-bought shares, exempt from the buyer's lock, is not "
                                             "read; every block of the class is 'source not confirmed'")}})


def probe_reproduction() -> dict:
    import b135_fetch as F
    W = "2016-05-27_2018-05-26"
    bsnap = snapshot_dir("rpt_data_blocktrade", W)
    blocks = load_blocks(bsnap)
    brows = list(read_pages(bsnap))
    holder = list(read_pages(snapshot_dir("rpt_share_holder_increase", W)))
    execs = list(read_pages(snapshot_dir("rpt_executive_hold_details", W)))
    stage, _ = F.load_lift_stage()
    key = {F.block_key(r): i for i, r in enumerate(brows)}
    ref = {"c1": {key[k] for k in F.join_exec(F.index_blocks(brows), execs)["named"]}}
    r2 = F.join_holder(brows, holder)
    ref["c2"] = {key[k] for k in r2["named_exact"] | r2["named_sum"]}
    r2b = F.join_holder(brows, F.holder_stated_block(holder))
    ref["c2b"] = {key[k] for k in r2b["named_exact"] | r2b["named_sum"]}
    ref["c3"] = {key[k] for k in F.join_lift(brows, stage, LIFT_LOOKBACK)["named"]}
    mine = classes(blocks, pd.DataFrame(holder), pd.DataFrame(execs), load_lift())
    return {k: ref[k] == mine[k] for k in ref}


# --------------------------------------------------------------------------
# run, record, selftest


def _rv(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return float(f"{x:.10g}") if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): _rv(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_rv(v) for v in x]
    return x


def compute(bars_needed: bool = True) -> dict:
    import pickle
    blocks = load_blocks()
    cache = CACHE / "classes_full.pkl"
    if cache.exists():
        cl = pickle.loads(cache.read_bytes())
    else:
        cl = classes(blocks, load_table("rpt_share_holder_increase", HOLDER_FIELDS),
                     load_table("rpt_executive_hold_details", EXEC_FIELDS), load_lift())
        cache.write_bytes(pickle.dumps(cl))
    flags, st_how = st_flags()
    a = frame(blocks, cl, flags)
    cal = calendar(a)
    pl = placebo_dates(cal)
    S = Steps(a, cal)
    steps = {d: {c: S.with_floor(c, d, pl) for c in ("lock", "unlocked")} for d in RULES}
    lock_codes = set(a[(a["cls"] == "lock") & a["usable"]]["SECURITY_CODE"])
    bars, how, BP = bars_for(lock_codes)
    lr = longstaff_rows(a, bars, BP)
    out = {"blocks": blocks, "a": a, "cl": cl, "placebos": pl, "steps": steps, "bars_how": how,
           "bars_stocks": len(bars), "lr": lr, "st_how": st_how, "st_stocks": len(flags)}
    c1, o1 = criterion_ratio(a)
    c2, o2 = criterion_exchange(blocks)
    c3 = criterion_rival(steps[LOCK_DATE]["lock"])
    other = {d: {c: v for c, v in steps[d].items() if not (d == LOCK_DATE and c == "lock")}
             for d in RULES}
    c4 = criterion_other_dates(other)
    c5, o5 = criterion_longstaff(lr, int(((a["cls"] == "lock") & a["usable"]).sum()))
    c6, o6 = borrowed_rows(a, lr, BP)
    c7, o7 = criterion_coverage(blocks, a, cl, probe_reproduction())
    out["criteria"] = [c1, c2, c3, c4, c5, c6, c7]
    out["objects"] = {"B135-1": o1, "B135-2": o2, "B135-3": steps[LOCK_DATE]["lock"],
                      "B135-4": other, "B135-5": o5, "B135-6": o6, "B135-7": o7}
    return out


def build_record(out: dict) -> dict:
    rec = {"stage": "B135",
           "config": {"tables": {t: snapshot_dir(t).relative_to(ROOT).as_posix()
                                 for t in ("rpt_data_blocktrade", "rpt_executive_hold_details",
                                           "rpt_share_holder_increase")},
                      "a_share_prefixes": list(A_PREFIXES), "board_limits":
                          "main 10%, ChiNext 10% then 20% from 2020-08-24, STAR 20%; main-board ST 5% "
                          "on days the daily bar flags the stock, up to 2026-07-06; no bar that day: "
                          "the board's limit",
                      "st_flag_stocks": out["st_stocks"],
                      "lock_class": ("blocks matched to a five-per-cent holder's reduction stated as a "
                                     "block trade: a seller-side proxy. The six-month lock on the buyer "
                                     "also depends on where the shares came from (auction-bought shares "
                                     "are exempt), which the holder table does not carry"),
                      "windows_trading_days": list(WINDOWS), "placebo_years": list(PLACEBO_YEARS),
                      "placebo_gap_days": PLACEBO_GAP_DAYS, "placebo_dates": len(out["placebos"]),
                      "lift_lookback_days": LIFT_LOOKBACK, "unlocked_lookback_days": UNLOCKED_LOOKBACK,
                      "sigma_windows": list(SIGMA_WINDOWS), "lock_years": LOCK_YEARS,
                      "remaining_years": list(REMAINING_YEARS),
                      "bars_stocks": out["bars_stocks"],
                      "yearbooks": YEARBOOKS.relative_to(ROOT).as_posix()},
           "criteria": [_rv(c) for c in out["criteria"]],
           "objects": _rv(out["objects"])}
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = "Station not closed: the readings are not yet in RESULTS.md."
    return rec


def selftest() -> bool:
    """Each criterion's flag fed an input that must fail it (11f)."""
    ok = True
    # the ST limit: a main-board block at 5 % below the previous close is pinned on a day the bar
    # flags the stock, and usable on the board's limit alone
    b0 = pd.DataFrame({"SECURITY_CODE": ["600001", "600001", "600001", "300001"],
                       "day": ["2008-11-17", "2008-11-18", "2008-11-19", "2021-03-01"],
                       "TRADE_DATE": ["x"] * 4, "DEAL_PRICE": [1.86, 1.86, 1.86, 9.50],
                       "CLOSE_PRICE": [1.90, 1.90, 1.90, 9.80], "PRE_CLOSE_PRICE": [1.96, 1.96, 1.96, 10.0],
                       "PREMIUM_RATIO": [1.86 / 1.90 - 1] * 3 + [9.50 / 9.80 - 1]})
    o = dt.date(2008, 11, 17).toordinal()
    fl = {"600001": (np.array([o, o + 1], dtype=np.int32), np.array([1, 0], dtype=np.int8)),
          "300001": (np.array([dt.date(2021, 3, 1).toordinal()], dtype=np.int32), np.array([1], dtype=np.int8))}
    empty = {"c1": set(), "c2": set(), "c2b": set(), "c3": set(), "unlock_365": set()}
    f1 = frame(b0, empty, fl)
    f0 = frame(b0, empty)
    st_ok = (list(f1["pinned"]) == [True, False, False, False] and not f0["pinned"].any()
             and list(f1["st"].isna()) == [False, False, True, False]
             and float(f1["lim"].iloc[3]) == 0.20
             and st_object(f1)["taken_out_by_the_st_limit"]["unlocked"] == 1)
    print(f"  the ST limit pins a flagged main-board block at 5 %, leaves the unflagged day, the day "
          f"with no bar and the ChiNext block alone: {st_ok}")
    ok &= st_ok
    a = pd.DataFrame({"ratio_gap": [0.0, 1e-6], "outside_limit": [False, False],
                      "usable": [True, True], "close_outside_limit": [False, False],
                      "pinned": [False, False], "SECURITY_CODE": ["600000"] * 2,
                      "day": ["2020-01-02"] * 2, "DEAL_PRICE": [1.0] * 2,
                      "PRE_CLOSE_PRICE": [1.0] * 2, "CLOSE_PRICE": [1.0] * 2})
    c, _ = criterion_ratio(a)
    print(f"  B135-1 fails on a ratio gap: {not c['passed']}")
    ok &= not c["passed"]
    a2 = a.copy()
    a2["ratio_gap"] = 0.0
    a2.loc[0, "outside_limit"] = True
    c, _ = criterion_ratio(a2)
    print(f"  B135-1 fails on a breach left usable: {not c['passed']}")
    ok &= not c["passed"]
    fake = {w: {"step": 0.01, "above_all": True, "below_all": False, "rank_above": 9,
                "placebo_n": 9} for w in WINDOWS}
    print(f"  B135-3 map, all above: {rival_cell(fake)[:2]}")
    ok &= rival_cell(fake)[:2] == (True, "B")
    fake[20]["above_all"] = False
    print(f"  B135-3 map, windows disagree: {rival_cell(fake)[:2]}")
    ok &= rival_cell(fake)[:2] == (None, "unread")
    for w in WINDOWS:
        fake[w].update(step=0.001, above_all=False, below_all=False)
    ok &= rival_cell(fake)[:2] == (False, "C")
    for w in WINDOWS:
        fake[w].update(step=-0.01, above_all=False, below_all=True)
    ok &= rival_cell(fake)[:2] == (False, "both_unmet")
    print(f"  B135-3 map, C and both_unmet reached: {ok}")
    c = criterion_other_dates({"x": {"lock": {20: {"step": float('nan')}}}})
    print(f"  B135-4 fails on a missing cell: {not c['passed']}")
    ok &= not c["passed"]
    c, _ = criterion_longstaff(pd.DataFrame(), 5)
    print(f"  B135-5 fails with no sigma: {not c['passed']}")
    ok &= not c["passed"]
    lr = pd.DataFrame({"idx": [0, 1, 2], "code": ["600000"] * 3,
                       "day": ["2016-03-01", "2018-03-01", "2019-03-01"], "delta": [0.1, 0.1, 0.2],
                       "sigma_60": [0.3] * 3, "sigma_120": [0.3] * 3, "sigma_250": [0.3, 0.3, None],
                       "excess_60": [0.05, -0.05, 0.1], "excess_120": [0.05, -0.05, 0.1],
                       "excess_250": [0.05, 0.02, None]})
    c, o = criterion_longstaff(lr, 3)
    split_ok = (c["passed"] and o["periods"]["before the rule"]["with_sigma_all_windows"] == 1
                and o["periods"]["from the rule"]["with_sigma_all_windows"] == 1
                and o["periods"]["from the rule"]["usable_blocks"] == 2
                and o["periods"]["before the rule"]["over_bound"][60] == 1
                and o["periods"]["from the rule"]["sign_disagrees_across_windows"] == 1)
    print(f"  B135-5 splits the blocks at the rule date: {split_ok}")
    ok &= split_ok
    b = pd.DataFrame({"day": ["2020-01-02"]}, index=[0])
    c, _ = criterion_coverage(b, b.iloc[0:0].assign(cls=[], usable=[]), {}, {"c2b": False})
    print(f"  B135-7 fails when the probe differs: {not c['passed']}")
    ok &= not c["passed"]
    return bool(ok)


def print_run(out: dict) -> None:
    for c in out["criteria"]:
        flag = {True: "PASS", False: "FAIL", None: "unread"}[c["passed"]]
        print(f"{c['name']}\n    [{c['kind']}] {flag}: {c['detail']}")
    o5 = out["objects"]["B135-5"]
    print("\nB135-5 by year (blocks with sigma; above the bound at 60/120/250):")
    for y, v in sorted(o5["by_year"].items()):
        print(f"  {y}: {v['blocks']:5d}  " + " ".join(f"{v[n]:5d}" for n in SIGMA_WINDOWS))
    print("\nB135-6 by year (100M yuan):")
    for y, r in sorted(out["objects"]["B135-6"]["rows"].items()):
        lb = " ".join(f"{L}y {r.get(f'at_longstaff_{L}y_100m_yuan', float('nan')):,.0f}"
                      for L in REMAINING_YEARS)
        print(f"  {y}: locked {r.get('locked_both_100m_yuan') or float('nan'):,.0f}; at median "
              f"discount {r.get('at_median_discount_100m_yuan', float('nan')):,.0f} "
              f"(disc {r.get('lock_buy_median_discount', float('nan')):.4f}); at Longstaff {lb}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        ok = selftest()
        print(f"selftest {'passed' if ok else 'FAILED'}")
        return 0 if ok else 1
    if a.run:
        t0 = time.perf_counter()
        out = compute()
        print_run(out)
        st = out["objects"]["B135-1"]["st"]
        print(f"\nST flag: {st['with_a_bar_that_day']} of {st['a_share_blocks']} A-share blocks have a bar "
              f"that day; flagged {st['flagged_st']} ({st['flagged_st_at_5pct']} at 5 %); taken out "
              f"{st['taken_out_by_the_st_limit']}; made usable {st['made_usable_by_the_st_limit']}")
        for name, p in out["objects"]["B135-5"]["periods"].items():
            print(f"B135-5 {name}: usable {p['usable_blocks']}, with sigma {p['with_sigma_all_windows']}, "
                  f"above the bound {p['over_bound']}, sign moves {p['sign_disagrees_across_windows']}")
        print(f"\n{time.perf_counter() - t0:.1f} s; bars: {out['bars_how']}; ST flags: {out['st_how']}")
        if not a.no_write:
            RECORD.write_text(json.dumps(build_record(out), ensure_ascii=False, indent=1,
                                         sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {RECORD.name}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
