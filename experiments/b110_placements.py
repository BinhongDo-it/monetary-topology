"""B110: the entry edge an A-share placement opens to one class only, read from the cache that
experiments/b110_fetch.py built.

Part one builds the per-offering frame and prints its objects. Part two reads B110-1 to B110-3 off
the frame: the price floor, the lock months, and the join of the two tables. Part three reads B110-4 to
B110-7: what the edge hands over and to whom, the discount against the most a lock can be worth, the
price against the day's high, and the coverage table; `--write` puts all seven in
results/b110_placements.json.

An offering enters B110-4 to B110-6 only when it traded on T, its price and shares are in the table,
and B110-1 found nothing wrong with its T; a bid offering is split by class only when B110-3 found its
shares add up. Every offering that stays out is named with the reason.

**Scope.** Offerings of SEO_TYPE 1 whose ISSUE_DATE falls on or after 2017-02-15. ISSUE_DATE is
the day bids are taken, T; the offering period opens two trading days earlier. An offering sits in
the rules of its ISSUE_DATE: from 2020-02-14 the price floor is 80% of the base-date VWAP20 and the
locks are 6 and 18 months; from 2017-02-15 to 2020-02-13 the floor is 90% and the locks are 12 and
36 months. ISSUE_WAY 网下询价配售 is an offering priced by bids, 网下定价发行 one priced in advance.

**The frame**, per offering:

- from the offering table: price P, shares issued n, shares before N, listing date, way, the lock
  text and the pricing text;
- from the stock's own daily bars on T: close Pm, high H, the close of the traded day before T, and
  VWAP20 as of T-k for k = 0..10: the amount over the volume of the 20 days the stock traded before
  row T-k. A row is a market day and a suspended day is a row with tradestatus 0, so T-k counts
  market days and VWAP20 counts traded days only. The rules price a day before a split or a dividend
  at its adjusted price, and adjust the issue price for one between the base date and the issue, so
  every average is taken in the price basis of T: a day's volume is scaled by the exchange's
  adjustment factors between that day and T, from close over the next day's preclose. The
  one-day average before T-k is kept beside it;
- realised volatility over the 250 traded days before T, from ln(close / preclose), which carries
  splits and dividends through the exchange's reference price;
- the unlock groups joined to it. A group is the holder rows of one stock, one unlock date and one
  lock month, placement shares only. It joins the offering of that stock whose listing date plus the
  lock month lands from 3 days before to 20 days after the unlock date. Two offerings that fit
  equally are not guessed between, and a group no offering fits is named with the latest offering
  before its unlock beside it.

A compact copy of the bars sits in data/cache/b110_bars.npz, rebuilt when a store file changes
name, size or modification second.

**The join, second and third passes.** An offering in scope holding more shares than it issued, with
no split between T and its unlock dates, lets go of the groups whose removal, one to three of them,
leaves exactly the shares issued, when only one such set exists. Failing that, when the excess equals
exactly the shares of another offering of the same stock that has no group at all, the holder rows
adding up to it (one to four of them) move to that offering: one unlock batch can carry two offerings'
holders. Then an offering still short of its
shares takes the unjoined groups of its stock (a tie, a lock month that lands nowhere, no lock month,
a group just let go) whose shares, alone or with one or two others, equal exactly what it is missing.
Only where no split falls between T and those unlock dates, so the sums are exact; a group two
offerings could take joins neither.

    python experiments/b110_placements.py --frame
    python experiments/b110_placements.py --criteria
    python experiments/b110_placements.py --criteria --write
    python experiments/b110_placements.py --selftest
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import io
import itertools
import json
import math
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b110_fetch as F  # noqa: E402
import b110_probe as P  # noqa: E402

ROOT = P.ROOT
SCOPE_START = F.SCOPE_START
RULE_2020 = "2020-02-14"
FLOOR = {"2017": 0.9, "2020": 0.8}
CLASS_MONTHS = {"2017": (12, 36), "2020": (6, 18)}
K_MAX = 10
VWAP_DAYS = 20
SIGMA_DAYS = 250
TRADING_DAYS_PER_YEAR = F.TRADING_DAYS_PER_YEAR
JOIN_LAG = (-3, 20)
TICK = 0.01
BID_WAY = "网下询价配售"
PRICED_WAY = "网下定价发行"
STORE_DIR = P.RAW / "daily_baostock" / "stock"
MANIFEST = P.RAW / "fetch_manifest.json"
BARS_CACHE = ROOT / "data" / "cache" / "b110_bars.npz"
NUMERIC = ("open", "high", "low", "close", "preclose", "volume", "amount")
# What a 网下定价发行 row sells its shares for. An issue paid in assets prices them under the reorganisation rule
# (a market reference price, a counterparty, the assets bought); matching funds are raised in cash. Each list turns
# up in the other's text, so the word that comes first decides, and a text that names the asset part first and the
# matching funds after prices both parts of one deal without saying which part the row is.
ASSET_WORDS = ("购买资产", "资产购买", "市场参考价", "重组", "对价股份", "交易对方", "标的资产", "换股", "交易各方", "交易双方",
               "协议各方")
MATCHING_WORDS = ("募集配套资金", "配套融资", "配套募集")
PRICED_STATES = ("cash", "for assets", "both parts", "cash by its text, net equal to gross", "cash by its text, net above gross",
                 "cash by its text, proceeds not printed")
# A factor this large on an adjustment day is a split (ten for ten-point-five at least), not a dividend alone.
SPLIT_FACTOR = 1.05
# A cash dividend paid on a split day makes the day's factor overstate the share multiplier by that dividend's
# share of the price, and the reference price is printed to the tick. Two calibration values, not findings;
# B110-3 prints their sweep.
DIVIDEND_ROOM = 0.06
FACTOR_BAND = 0.005
MIN_MONTHS = {"2017": 12, "2020": 6}
CATEGORIES = ("公募", "私募", "保险", "合格境外投资者", "证券公司", "自然人", "其他")
QFII_WORDS = ("QFII", "UBS", "瑞银", "瑞士银行", "摩根士丹利", "MORGAN", "摩根大通", "高盛", "GOLDMAN",
              "巴克莱", "BARCLAYS", "野村", "NOMURA", "美林", "MERRILL", "花旗", "汇丰", "HSBC", "德意志银行",
              "DEUTSCHE", "法国巴黎银行", "BNP", "新加坡政府投资", "阿布达比投资局", "科威特政府投资局",
              "挪威中央银行", "NORGES", "瑞穗", "MIZUHO", "麦格理", "MACQUARIE", "淡马锡", "TEMASEK",
              "施罗德", "SCHRODER", "富达", "FIDELITY", "贝莱德", "BLACKROCK", "瑞士信贷", "CREDIT SUISSE",
              "卡塔尔投资局", "澳门金融管理局", "香港金融管理局", "东方汇理", "AMUNDI")
# Insurers' asset managers carry no word that says insurance, so they are named by the start of the name.
INSURER_AM = ("大家", "华泰资产", "泰康", "国寿", "中国人寿", "平安资产", "太平洋资产", "新华资产", "阳光资产",
              "太平资产", "中再", "华夏久盈", "光大永明", "英大", "合众", "民生通惠", "百年", "工银安盛",
              "招商信诺", "中英益利", "中意资产", "人保", "长城财富", "建信保险", "交银康联", "中邮资产",
              "国华", "富德", "前海人寿", "君康", "弘康", "恒安标准", "信泰", "利安", "珠江", "长江养老")
# A securities firm whose legal name carries no word for one, and the state's bad-debt asset managers,
# whose names read like a private manager's.
SECURITIES_NAMES = ("中国国际金融股份有限公司",)
STATE_AMC = ("中国华融资产管理", "中国长城资产管理", "中国东方资产管理", "中国信达资产管理", "中国银河资产管理",
             "中央汇金资产管理")


# ---------------------------------------------------------------------------
# Small pieces
# ---------------------------------------------------------------------------

def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def era_of(day: str) -> str:
    return "2020" if day >= RULE_2020 else ("2017" if day >= SCOPE_START else "before 2017")


def deal_id(s: dict) -> str:
    return f"{s.get('SECURITY_CODE')}:{(s.get('ISSUE_DATE') or '')[:10]}:{s.get('ISSUE_NUM')}"


def is_placement(share_type) -> bool:
    return isinstance(share_type, str) and any(m in share_type for m in F.PLACEMENT_TYPE_MARKERS)


def lock_month(x) -> int | None:
    v = num(x)
    return int(v) if v is not None and v == int(v) else None


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def longstaff(sigma: float, years: float) -> float:
    """Longstaff (1995): the most a perfectly timed seller gains from being free to sell for `years`,
    the expected maximum of a driftless geometric Brownian motion over the interval, minus one."""
    v = sigma * sigma * years
    s = math.sqrt(v)
    return (2.0 + v / 2.0) * norm_cdf(s / 2.0) + math.sqrt(v / (2.0 * math.pi)) * math.exp(-v / 8.0) - 1.0


def category(name: str) -> str:
    """One of CATEGORIES for a holder name. The order of the tests is the rule: a private product run
    by a fund company is private, a securities firm's asset manager is a securities firm."""
    n = (name or "").strip()
    head = re.split(r"[-－]", n, maxsplit=1)[0]
    if "私募" in n or re.search(r"(股权投资|创业投资|产业投资|创投)基金管理", n):
        return "私募"
    if re.search(r"基金管理(\(中国\)|（中国）)?(股份)?有限(责任)?公司", head) or (head != n and head.endswith("基金")):
        return "公募"
    if (re.search(r"证券(股份)?有限(责任)?公司|证券资产管理", head) or (head != n and head.endswith("证券"))
            or head.startswith(SECURITIES_NAMES)):
        return "证券公司"
    letters = sum(ch.isascii() and ch.isalpha() for ch in n)
    if ((letters >= 4 and letters >= 0.4 * len(n.replace(" ", ""))) or any(w in n.upper() for w in QFII_WORDS)
            or re.search(r"[(（](亚洲|香港|新加坡|国际)[)）]", head)):
        return "合格境外投资者"
    if head.startswith(STATE_AMC):
        return "其他"
    if any(w in n for w in ("保险", "人寿", "养老")) or (
            re.search(r"资产管理(股份)?有限(责任)?公司", head) and head.startswith(INSURER_AM)):
        return "保险"
    person = r"[一-鿿]{2,4}" if "·" not in n else r"[一-鿿·]{3,16}"
    if re.fullmatch(person, n):
        return "自然人"
    if re.search(r"有限合伙|合伙企业|投资中心|投资管理|资产管理", n):
        return "私募"
    return "其他"


# ---------------------------------------------------------------------------
# The bars: one compact copy of every store file
# ---------------------------------------------------------------------------

def store_files(store_dir: Path = STORE_DIR) -> list[Path]:
    return sorted(p for p in store_dir.glob("*.json") if re.fullmatch(r"\d{6}\.json", p.name))


def signature(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        st = f.stat()
        h.update(f"{f.name}\t{st.st_size}\t{int(st.st_mtime)}\n".encode("utf-8"))
    return h.hexdigest()


def build_bars(files: list[Path]) -> tuple[dict, dict]:
    col = {name: i for i, name in enumerate(P.BS_FIELDS)}
    codes, starts, ords, status, skipped = [], [0], [], [], {}
    nums: dict = {k: [] for k in NUMERIC}
    for f in files:
        obj = json.loads(f.read_bytes())
        ok, why = F.store_ok(obj)
        if not ok:
            skipped[f.stem] = why
            continue
        rows = obj["rows"]
        codes.append(f.stem)
        ords.extend(dt.date.fromisoformat(r[0]).toordinal() for r in rows)
        status.extend(int(r[col["tradestatus"]]) for r in rows)
        for k in NUMERIC:
            i = col[k]
            nums[k].extend(float(r[i]) if r[i] else math.nan for r in rows)
        starts.append(len(ords))
    arrays = {"codes": np.array(codes, dtype="U6"), "starts": np.array(starts, dtype=np.int64),
              "ordinal": np.array(ords, dtype=np.int32), "status": np.array(status, dtype=np.int8)}
    arrays.update({k: np.array(v, dtype=np.float64) for k, v in nums.items()})
    return arrays, skipped


class Bars:
    def __init__(self, arrays: dict):
        self.a = arrays
        self.pos = {str(c): i for i, c in enumerate(arrays["codes"])}

    def __len__(self) -> int:
        return len(self.pos)

    def rows(self) -> int:
        return int(self.a["starts"][-1])

    def last_day(self) -> str:
        return dt.date.fromordinal(int(self.a["ordinal"].max())).isoformat() if self.rows() else ""

    def series(self, code: str) -> dict | None:
        i = self.pos.get(code)
        if i is None:
            return None
        s, e = int(self.a["starts"][i]), int(self.a["starts"][i + 1])
        return finish_series({k: self.a[k][s:e] for k in ("ordinal", "status") + NUMERIC})


def finish_series(out: dict) -> dict:
    """Adds the traded rows, each row's adjustment factor (the close before it over its preclose, one
    where they agree) and their running product."""
    out["traded"] = np.flatnonzero(out["status"] == 1)
    close, pre = out["close"], out["preclose"]
    f = np.ones(len(close))
    if len(close) > 1:
        prev, cur = close[:-1], pre[1:]
        moved = (prev > 0) & (cur > 0) & (np.abs(prev - cur) > 1e-9)
        f[1:][moved] = prev[moved] / cur[moved]
    out["factor"], out["g"] = f, np.cumprod(f)
    return out


def load_bars(files: list[Path] | None = None, cache: Path = BARS_CACHE, rebuild: bool = False) -> tuple[Bars, str]:
    files = store_files() if files is None else files
    sig = signature(files)
    why = "no cache on disk"
    if cache.exists() and not rebuild:
        try:
            with np.load(cache, allow_pickle=False) as z:
                if str(z["signature"]) == sig:
                    return Bars({k: z[k] for k in z.files if k != "signature"}), f"read {cache.name}"
            why = "a store file changed since the cache was built"
        except (OSError, ValueError, KeyError) as exc:
            why = f"cache unreadable ({exc.__class__.__name__})"
    elif rebuild:
        why = "rebuild asked for"
    arrays, skipped = build_bars(files)
    buf = io.BytesIO()
    np.savez(buf, signature=np.array(sig), **arrays)
    P.atomic_write_bytes(cache, buf.getvalue())
    how = f"built {cache.name} from {len(files)} store files ({why})"
    if skipped:
        how += f"; skipped {len(skipped)} that failed their checks: {sorted(skipped.items())[:5]}"
    return Bars(arrays), how


def row_of(series: dict, day: str) -> int | None:
    o = dt.date.fromisoformat(day).toordinal()
    i = int(np.searchsorted(series["ordinal"], o))
    return i if i < len(series["ordinal"]) and int(series["ordinal"][i]) == o else None


def last_row_on_or_before(series: dict, day: str) -> int | None:
    i = int(np.searchsorted(series["ordinal"], dt.date.fromisoformat(day).toordinal(), side="right")) - 1
    return i if i >= 0 else None


def vwap_before(series: dict, row: int, days: int = VWAP_DAYS, basis: int | None = None) -> float | None:
    """Amount over volume of the last `days` traded rows before `row`, in the price basis of row `basis`
    (default `row`): each day's volume is scaled by the adjustment factors between it and `basis`."""
    if row < 0:
        return None
    traded = series["traded"]
    cut = int(np.searchsorted(traded, row))
    if cut < days:
        return None
    idx = traded[cut - days:cut]
    g = series["g"]
    scale = g[row if basis is None else basis] / g[idx]
    vol, amt = float((series["volume"][idx] * scale).sum()), float(series["amount"][idx].sum())
    return amt / vol if vol > 0 and math.isfinite(amt) else None


def sigma_of(series: dict, idx: np.ndarray, min_days: int) -> float | None:
    c, p = series["close"][idx], series["preclose"][idx]
    good = (c > 0) & (p > 0)
    r = np.log(c[good] / p[good])
    if r.size < max(min_days, 2):
        return None
    return float(np.std(r, ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))


def sigma_before(series: dict, row: int, days: int = SIGMA_DAYS) -> float | None:
    """The last `days` traded rows before `row`."""
    traded = series["traded"]
    cut = int(np.searchsorted(traded, row))
    return sigma_of(series, traded[cut - days:cut], days) if cut >= days else None


def sigma_after(series: dict, row: int, end_row: int, min_days: int = 20) -> float | None:
    """Traded rows after `row` through `end_row`."""
    traded = series["traded"]
    return sigma_of(series, traded[(traded > row) & (traded <= end_row)], min_days)


# ---------------------------------------------------------------------------
# The frame
# ---------------------------------------------------------------------------

def bar_readings(series: dict | None, T: str, price: float | None, floor: float | None) -> dict:
    out = {"bars": "no bars", "row_T": None, "Pm": None, "H": None, "low": None, "prev_close": None,
           "vwap": [None] * (K_MAX + 1), "vwap1": [None] * (K_MAX + 1), "min_k": None, "d": None,
           "ticks_over_high": None, "sigma_pre": None, "traded_before": 0}
    if series is None:
        return out
    i = row_of(series, T)
    if i is None:
        out["bars"] = "T is not a row"
        return out
    traded = series["traded"]
    cut = int(np.searchsorted(traded, i))
    out.update(row_T=i, traded_before=cut, bars="ok" if int(series["status"][i]) == 1 else "suspended on T",
               Pm=float(series["close"][i]), H=float(series["high"][i]), low=float(series["low"][i]))
    if cut:
        out["prev_close"] = float(series["close"][traded[cut - 1]])
    out["vwap"] = [vwap_before(series, i - k, VWAP_DAYS, i) for k in range(K_MAX + 1)]
    out["vwap1"] = [vwap_before(series, i - k, 1, i) for k in range(K_MAX + 1)]
    if price is not None and floor is not None:
        out["min_k"] = next((k for k, v in enumerate(out["vwap"]) if v is not None and price >= floor * v - TICK), None)
    if price is not None and out["bars"] == "ok" and out["Pm"]:
        out["d"] = 1.0 - price / out["Pm"]
        out["ticks_over_high"] = int(round((price - out["H"]) / TICK))
    out["sigma_pre"] = sigma_before(series, i)
    return out


def offering_frame(seo_rows: list[dict], bars: Bars) -> list[dict]:
    frame = []
    for s in seo_rows:
        T = (s.get("ISSUE_DATE") or "")[:10]
        if s.get("SEO_TYPE") != "1" or not T or T < SCOPE_START:
            continue
        code, era, principle = str(s.get("SECURITY_CODE")), era_of(T), s.get("PRICE_PRINCIPLE") or ""
        o = {"id": deal_id(s), "code": code, "name": s.get("SECURITY_NAME_ABBR"), "T": T, "era": era,
             "way": s.get("ISSUE_WAY") or "", "P": num(s.get("ISSUE_PRICE")), "n": num(s.get("ISSUE_NUM")),
             "N": num(s.get("ISSUE_SHARE_BEFORE")), "listing": (s.get("ISSUE_LISTING_DATE") or "")[:10],
             "lock_text": s.get("LOCKIN_PERIOD") or "", "gross": num(s.get("TOTAL_RAISE_FUNDS")),
             "net": num(s.get("NET_RAISE_FUNDS")), "first_day": "首日" in principle, "principle": principle, "groups": []}
        o.update(bar_readings(bars.series(code), T, o["P"], FLOOR.get(era)))
        frame.append(o)
    return frame


def unlock_groups(stage_rows: list[dict], start: str = SCOPE_START) -> tuple[list[dict], list[str], collections.Counter]:
    """Holder rows of every placement unlock batch from `start`, grouped by lock month."""
    groups, absent, excluded = [], [], collections.Counter()
    for code, free_date in F.holder_batches(stage_rows, start):
        path = P.RAW / "rpt_lift_gd" / f"{code}_{free_date}.json"
        if not path.exists():
            absent.append(f"{code} {free_date}")
            continue
        ok, why, obj = P.lift_gd_ok(path.read_bytes())
        if not ok:
            absent.append(f"{code} {free_date}: {why}")
            continue
        by_month: dict = collections.defaultdict(list)
        for r in obj["result"]["data"]:
            if not is_placement(r.get("FREE_SHARES_TYPE")):
                excluded[str(r.get("FREE_SHARES_TYPE"))] += 1
                continue
            by_month[lock_month(r.get("LOCK_MONTH"))].append(r)
        for month in sorted(by_month, key=lambda m: (m is None, m or 0)):
            rs = by_month[month]
            holders = [(str(r.get("LIMITED_HOLDER_NAME") or ""), num(r.get("ADD_LISTING_SHARES")) or 0.0) for r in rs]
            groups.append({"code": code, "free_date": free_date, "lock_month": month,
                           "holders": [(nm, sh, category(nm)) for nm, sh in holders],
                           "shares": sum(sh for _, sh in holders),
                           "types": sorted({str(r.get("FREE_SHARES_TYPE")) for r in rs})})
    return groups, absent, excluded


def join_group(offerings: list[dict], free_date: str, months) -> tuple[dict | None, str, int | None]:
    if months is None:
        return None, "no lock month", None
    fd = dt.date.fromisoformat(free_date)
    fits = []
    for s in offerings:
        listing = (s.get("ISSUE_LISTING_DATE") or "")[:10]
        if not listing:
            continue
        lag = (fd - P.add_months(dt.date.fromisoformat(listing), months)).days
        if JOIN_LAG[0] <= lag <= JOIN_LAG[1]:
            fits.append((abs(lag), deal_id(s), lag, s))
    if not fits:
        return None, "no offering fits", None
    fits.sort(key=lambda x: (x[0], x[1]))
    if len(fits) > 1 and fits[0][0] == fits[1][0]:
        return None, "two offerings fit equally", None
    return fits[0][3], "fits", fits[0][2]


def latest_before(offerings: list[dict], free_date: str) -> dict | None:
    prior = [s for s in offerings if "" < (s.get("ISSUE_DATE") or "")[:10] <= free_date]
    return max(prior, key=lambda s: ((s.get("ISSUE_DATE") or "")[:10], deal_id(s))) if prior else None


def join_all(groups: list[dict], seo_rows: list[dict], frame: list[dict], bars: Bars, bars_through: str):
    by_stock: dict = collections.defaultdict(list)
    for s in seo_rows:
        if s.get("SEO_TYPE") == "1":
            by_stock[str(s.get("SECURITY_CODE"))].append(s)
    index = {o["id"]: o for o in frame}
    outcomes: collections.Counter = collections.Counter()
    for g in groups:
        s, how, lag = join_group(by_stock.get(g["code"], []), g["free_date"], g["lock_month"])
        g.update(how=how, lag=lag, deal=deal_id(s) if s else None)
        if s is None:
            prior = latest_before(by_stock.get(g["code"], []), g["free_date"])
            g["latest_before"] = deal_id(prior) if prior else None
            outcomes[how] += 1
        elif g["deal"] in index:
            outcomes["fits an offering in scope"] += 1
            index[g["deal"]]["groups"].append(g)
        else:
            outcomes["fits an offering before the scope"] += 1
    outcomes.update(trim_excess(frame, bars, by_stock, {g["deal"] for g in groups if g.get("deal")}))
    outcomes.update(fill_gaps(frame, groups, bars))
    for o in frame:
        series = bars.series(o["code"])
        for g in o["groups"]:
            g["years"] = (dt.date.fromisoformat(g["free_date"]) - dt.date.fromisoformat(o["T"])).days / 365.25
            end = last_row_on_or_before(series, g["free_date"]) if series is not None else None
            g["sigma_lock"] = (sigma_after(series, o["row_T"], end)
                               if series is not None and o["row_T"] is not None and end is not None
                               and g["free_date"] <= bars_through else None)
        o["shares_joined"] = sum(g["shares"] for g in o["groups"])
        o["ratio"] = o["shares_joined"] / o["n"] if o["n"] else None
    return outcomes


def split_between(series: dict | None, row_T: int | None, last_day: str) -> bool:
    if series is None or row_T is None:
        return True
    end = last_row_on_or_before(series, last_day)
    return end is not None and end > row_T and bool(np.any(series["factor"][row_T + 1:end + 1] >= SPLIT_FACTOR))


def trim_excess(frame: list[dict], bars, by_stock: dict, joined: set) -> collections.Counter:
    """The second pass of the join; see the module text."""
    out: collections.Counter = collections.Counter()
    for o in frame:
        if o["n"] is None or not o["groups"]:
            continue
        excess = sum(g["shares"] for g in o["groups"]) - o["n"]
        if excess < 1:
            continue
        if split_between(bars.series(o["code"]), o["row_T"], max(g["free_date"] for g in o["groups"])):
            out["excess with a split between T and the unlocks, left for B110-3"] += 1
            continue
        hits = [c for r in (1, 2, 3) if r < len(o["groups"]) for c in itertools.combinations(o["groups"], r)
                if abs(sum(g["shares"] for g in c) - excess) < 0.5]
        if len(hits) == 1:
            for g in hits[0]:
                o["groups"].remove(g)
                g.update(deal=None, how_first=g["how"], how="let go: the offering adds up without it")
            out["excess let go"] += 1
            continue
        homes = [s for s in by_stock.get(o["code"], []) if deal_id(s) != o["id"] and deal_id(s) not in joined
                 and num(s.get("ISSUE_NUM")) is not None and abs(num(s.get("ISSUE_NUM")) - excess) < 0.5]
        rows = [(g, h) for g in o["groups"] for h in g["holders"]]
        moves = [c for r in (1, 2, 3, 4) for c in itertools.combinations(rows, r)
                 if abs(sum(h[1] for _, h in c) - excess) < 0.5] if len(homes) == 1 and len(rows) <= 40 else []
        if len(moves) != 1:
            out["excess left: " + ("no set of groups or rows adds up to it" if not hits and not moves
                                   else "more than one set adds up to it")] += 1
            continue
        for g, h in moves[0]:
            g["holders"].remove(h)
            g["shares"] -= h[1]
        out["excess rows moved to another offering of the stock"] += 1
    return out


def fill_gaps(frame: list[dict], groups: list[dict], bars) -> collections.Counter:
    """The second pass of the join; see the module text."""
    loose: dict = collections.defaultdict(list)
    for g in groups:
        if g.get("deal") is None:
            loose[g["code"]].append(g)
    plans, claims = {}, collections.defaultdict(set)
    out: collections.Counter = collections.Counter()
    for o in frame:
        cands = [g for g in loose.get(o["code"], []) if g["free_date"] > o["T"]]
        if not cands or o["n"] is None or o["row_T"] is None:
            continue
        gap = o["n"] - sum(g["shares"] for g in o["groups"])
        if gap < 1:
            continue
        if split_between(bars.series(o["code"]), o["row_T"], max(g["free_date"] for g in cands)):
            out["share gap left: a split between T and the loose groups"] += 1
            continue
        hits = [c for r in (1, 2, 3) for c in itertools.combinations(cands, r)
                if abs(sum(g["shares"] for g in c) - gap) < 0.5]
        if len(hits) == 1:
            plans[o["id"]] = hits[0]
            for g in hits[0]:
                claims[id(g)].add(o["id"])
        elif hits:
            out["share gap left: more than one set of groups fits"] += 1
    index = {o["id"]: o for o in frame}
    for oid in sorted(plans):
        combo = plans[oid]
        if any(len(claims[id(g)]) > 1 for g in combo):
            out["share gap left: a group two offerings could take"] += 1
            continue
        for g in combo:
            g.update(deal=oid, how_first=g.get("how_first", g["how"]), how="fills the offering's share gap exactly")
            index[oid]["groups"].append(g)
        out["share gap filled"] += 1
    return out


def load_all(rebuild_bars: bool = False) -> dict:
    tables = F.load_tables(network=False, delay=0.0)
    seo, stage = tables["RPT_SEO_DETAIL"], tables["RPT_LIFT_STAGE"]
    bars, bars_note = load_bars(rebuild=rebuild_bars)
    try:
        bars_through = json.loads(MANIFEST.read_text(encoding="utf-8"))["scope"]["bars_through"]
        through_note = "the fetch manifest"
    except (OSError, ValueError, KeyError):
        bars_through, through_note = bars.last_day(), "the last day in the bars"
    frame = offering_frame(seo["rows"], bars)
    groups, absent, excluded = unlock_groups(stage["rows"])
    outcomes = join_all(groups, seo["rows"], frame, bars, bars_through)
    return {"tables": tables, "bars": bars, "bars_note": bars_note, "bars_through": bars_through,
            "through_note": through_note, "frame": frame, "groups": groups, "absent": absent,
            "excluded": excluded, "outcomes": outcomes}


# ---------------------------------------------------------------------------
# B110-1 to B110-3
# ---------------------------------------------------------------------------

YUAN = re.compile(r"(\d+(?:\.\d+)?)\s*元\s*/\s*股")
BASE_DATE = re.compile(r"(?:定价基准日|发行期首日)[^。；;]{0,40}?(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
FIRST_DAY_BASE = re.compile(r"定价基准日为[^。；;]{0,30}?发行期的?首日|发行期的?首日为[^。；;]{0,10}?定价基准日")
ONE_DAY = re.compile(r"前\s*[1一]\s*个?\s*交易日[^。；;]{0,30}?均价|创业板上市公司证券发行管理暂行办法|创业板发行管理(暂行)?办法")
RATIO_80 = re.compile(r"80\s*%|百分之八十|八折")
RATIO_90 = re.compile(r"90\s*%|百分之九十|九折")
MISSING = "price or volume missing"
UNCLASSIFIED = "unclassified"
# Each state an offering or a group can take, and the verdict it carries: True is consistent with the rule,
# False is a case the rule does not allow and nothing on file explains, None is no verdict.
FLOOR_MAP = {"at T-k": True, "adjusted after T": True, "base date written": True, "one-day average": True,
             "text price": True, "text price less dividends": True, MISSING: None, UNCLASSIFIED: False}
LOCK_MAP = {"a class month": True, "longer than the class months": True,
            "month count below the minimum, the unlock after T plus the minimum": True,
            "no lock month": None, "shorter than the minimum": False}
SHARES_MAP = {"equal": True, "splits between T and the unlock": True, "fewer shares than issued": None,
              "no shares issued in the table": None, "more shares than issued, no split explains them": False}


def parse_date(y: str, m: str, d: str) -> str | None:
    try:
        return dt.date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def dividends_before(series: dict, row: int, days: int = 250) -> float:
    """Cash per share taken off the reference price on adjustment days that are not splits, in the `days`
    rows up to `row`."""
    idx = np.arange(max(1, row - days), row + 1)
    f = series["factor"][idx]
    sel = idx[(f != 1.0) & (f < SPLIT_FACTOR)]
    return float((series["close"][sel - 1] - series["preclose"][sel]).sum())


def floor_state(o: dict, series: dict | None, k_max: int = K_MAX) -> tuple[str, str]:
    """B110-1 for one bid offering: its state, and what decided it. The tests run in this order."""
    text, floor, price = o["principle"], FLOOR[o["era"]], o["P"]
    vw = o["vwap"][:k_max + 1]
    k = next((k for k, v in enumerate(vw) if v is not None and price is not None and price >= floor * v - TICK), None)
    if k is not None:
        return "at T-k", f"k={k}"
    if series is None or o["row_T"] is None or price is None:
        return MISSING, o["bars"]
    end = last_row_on_or_before(series, o["listing"]) if o["listing"] else None
    fa = float(np.prod(series["factor"][o["row_T"] + 1:end + 1])) if end is not None and end > o["row_T"] else 1.0
    pu = price * fa
    if fa > 1.0:
        k = next((k for k, v in enumerate(vw) if v is not None and pu >= floor * v - TICK), None)
        if k is not None:
            return "adjusted after T", f"factor {fa:.4f} between T and listing, then k={k}"
    m = BASE_DATE.search(text)
    bd = parse_date(*m.groups()) if m else None
    if bd:
        b = last_row_on_or_before(series, bd)
        ratio = 0.8 if RATIO_80.search(text) else 0.9 if RATIO_90.search(text) else floor
        v = vwap_before(series, b, VWAP_DAYS, o["row_T"]) if b is not None and b <= o["row_T"] else None
        if v is not None and pu >= ratio * v - TICK:
            return "base date written", f"base date {bd} in the text, P/VWAP20 {pu / v:.4f} against {ratio}"
    if ONE_DAY.search(text):
        k = next((k for k, v in enumerate(o["vwap1"][:k_max + 1]) if v is not None and pu >= 0.9 * v - TICK), None)
        if k is not None:
            return "one-day average", f"90% of the day's average before T-{k}"
    prices = [float(x) for x in YUAN.findall(text)]
    if prices and not FIRST_DAY_BASE.search(text):
        if price >= prices[-1] - TICK:
            return "text price", f"floor printed in the text {prices[-1]}"
        cash = dividends_before(series, o["row_T"])
        if price >= prices[-1] - cash - TICK:
            return "text price less dividends", f"floor printed in the text {prices[-1]}, cash {cash:.4f} off in the year before T"
    best = max((price / v for v in vw if v), default=None)
    # not a classification: the latest day in the year before T on which the floor would have held
    held = next((dt.date.fromordinal(int(series["ordinal"][j])).isoformat() for j in range(o["row_T"] - k_max - 1, max(o["row_T"] - 250, 0), -1)
                 if (v := vwap_before(series, j, VWAP_DAYS, o["row_T"])) is not None and pu >= floor * v - TICK), None)
    return UNCLASSIFIED, ((f"highest P/VWAP20 over T-0..T-{k_max} is {best:.4f} against {floor}" if best else "no VWAP20")
                          + (f"; the floor would last have held as of {held}" if held else "; the floor holds on no day in the year before T"))


def lock_text_months(text: str) -> set[int]:
    return {round(float(x) * 12) for x in re.findall(r"\d+(?:\.\d+)?", text or "")}


def lock_state(o: dict, g: dict) -> tuple[str, str]:
    """B110-2 for one unlock group of a bid offering. The rules set the time a holder may not sell as a
    minimum, counted from the end of the issue: six months, eighteen for the named investors (twelve and
    thirty-six before 2020-02-14). The issue ends on or after T, so an unlock before T plus the minimum
    breaks the rule whatever day the issue ended, and a month count taken from the listing date can read
    one short without breaking it."""
    m = g["lock_month"]
    if m is None:
        return "no lock month", ""
    earliest = P.add_months(dt.date.fromisoformat(o["T"]), MIN_MONTHS[o["era"]]).isoformat()
    if g["free_date"] < earliest:
        return "shorter than the minimum", f"unlock {g['free_date']} before T plus {MIN_MONTHS[o['era']]} months, {earliest}"
    if m in CLASS_MONTHS[o["era"]]:
        return "a class month", f"{m} months"
    if m < MIN_MONTHS[o["era"]]:
        return "month count below the minimum, the unlock after T plus the minimum", f"{m} months; unlock {g['free_date']}, T plus the minimum {earliest}"
    marks = [label for label, hit in (("in the offering's lock text", m in lock_text_months(o["lock_text"])),
                                      ("restructuring", "配套" in o["principle"] or "购买资产" in o["principle"]),
                                      ("bank", "银行" in (o["name"] or "")),
                                      ("securities firm", "证券" in (o["name"] or ""))) if hit]
    return "longer than the class months", f"{m} months; " + (", ".join(marks) or "no other mark")


def shares_state(o: dict, series: dict | None, room: float = DIVIDEND_ROOM, band: float = FACTOR_BAND) -> tuple[str, str]:
    """B110-3 for one offering: the shares in its joined groups against the shares it issued. Each group's
    shares are taken back to the issue through the split days between T and its unlock: a split day's
    factor, give or take `band`, is the most the shares can have multiplied, and that over (1 + `room`)
    the least. Fewer shares than issued is a group the tables do not carry or the join left out, and it
    carries no verdict; more shares than any split explains is a group joined to the wrong offering."""
    if o["n"] is None:
        return "no shares issued in the table", ""
    total = sum(g["shares"] for g in o["groups"])
    if not o["groups"]:
        return "fewer shares than issued", "no unlock group joined"
    if abs(total - o["n"]) < 0.5:
        return "equal", ""
    low = high = 0.0
    splits = 0
    for g in o["groups"]:
        big = np.array([])
        if series is not None and o["row_T"] is not None:
            end = last_row_on_or_before(series, g["free_date"])
            if end is not None and end > o["row_T"]:
                f = series["factor"][o["row_T"] + 1:end + 1]
                big = f[f >= SPLIT_FACTOR]
        s = float(np.prod(big)) if big.size else 1.0
        splits += int(big.size)
        low += g["shares"] / (s * (1.0 + band) ** int(big.size))
        high += g["shares"] / (s * ((1.0 - band) / (1.0 + room)) ** int(big.size))
    ratio = f"joined {total:,.0f} against {o['n']:,.0f} issued, {total / o['n']:.4f}, {splits} split days"
    if splits and low - 0.5 <= o["n"] <= high + 0.5:
        return "splits between T and the unlock", ratio
    if high + 0.5 < o["n"]:
        return "fewer shares than issued", ratio
    return "more shares than issued, no split explains them", ratio


def verdict_of(states: list[str], mapping: dict) -> bool:
    """False when any state maps to False; a state missing from the mapping is an error, not a pass."""
    return not any(mapping[s] is False for s in states)


def bid_rows(frame: list[dict]) -> list[dict]:
    return [o for o in frame if o["way"] == BID_WAY]


def criterion_floor(frame: list[dict], bars, seo_rows: list[dict], k_max: int = K_MAX) -> dict:
    rows = [(o, *floor_state(o, bars.series(o["code"]), k_max)) for o in bid_rows(frame)]
    counts = collections.Counter((o["era"], st) for o, st, _ in rows)
    passed = verdict_of([st for _, st, _ in rows], FLOOR_MAP)
    named = {st: [f"{o['code']} {o['T']} P={o['P']} ({why})" for o, s2, why in rows if s2 == st]
             for st in FLOOR_MAP if st != "at T-k"}
    pre = [s for s in seo_rows if s.get("SEO_TYPE") == "1" and s.get("ISSUE_WAY") == BID_WAY
           and "" < (s.get("ISSUE_DATE") or "")[:10] < SCOPE_START]
    pre_states = collections.Counter()
    pre_below = []
    for s in pre:
        prices = [float(x) for x in YUAN.findall(s.get("PRICE_PRINCIPLE") or "")]
        price = num(s.get("ISSUE_PRICE"))
        if not prices or price is None:
            pre_states["no price in the text"] += 1
        elif price >= prices[-1] - TICK:
            pre_states["at or above the text price"] += 1
        else:
            pre_states["below the text price"] += 1
            pre_below.append(f"{s.get('SECURITY_CODE')} {(s.get('ISSUE_DATE') or '')[:10]} P={price} text {prices[-1]}")
    bad = named[UNCLASSIFIED]
    detail = (f"{len(rows)} bid offerings from {SCOPE_START}: "
              + "; ".join(f"{era} {st} {c}" for (era, st), c in sorted(counts.items()))
              + f". Unclassified: {len(bad)}" + (f": {bad}" if bad else "")
              + f". Before {SCOPE_START}, table only, P against the last yuan price in the pricing text: "
              + ", ".join(f"{k} {v}" for k, v in sorted(pre_states.items()))
              + "; the ones below it carry no verdict here, since without bars a split or a revised floor cannot be told from an error.")
    return {"name": "B110-1", "kind": "known_answer",
            "criterion": "every bid offering clears its price floor at some T-k, or a record on file says why not",
            "passed": passed, "detail": detail,
            "payload": {"counts": {f"{era} {st}": c for (era, st), c in sorted(counts.items())}, "named": named,
                        "before_scope": dict(sorted(pre_states.items())), "before_scope_below": pre_below,
                        "mapping": FLOOR_MAP, "k_max": k_max}}


def criterion_locks(frame: list[dict]) -> dict:
    rows = [(o, g, *lock_state(o, g)) for o in bid_rows(frame) for g in o["groups"]]
    counts = collections.Counter((o["era"], st) for o, _, st, _ in rows)
    holders = collections.Counter((o["era"], g["lock_month"]) for o, g, _, _ in rows for _ in g["holders"])
    passed = verdict_of([st for _, _, st, _ in rows], LOCK_MAP)
    longer = collections.defaultdict(list)
    for o, g, st, why in rows:
        if st != "a class month":
            longer[f"{o['era']} {st}: {why.split('; ', 1)[-1] if '; ' in why else why}"].append(
                f"{o['code']} {o['name']} {o['T']} lock {g['lock_month']} unlock {g['free_date']} holders {len(g['holders'])}")
    share = {}
    for era in ("2017", "2020"):
        tot = sum(c for (e, _), c in holders.items() if e == era)
        cls = sum(c for (e, m), c in holders.items() if e == era and m in CLASS_MONTHS[era])
        share[era] = f"{cls}/{tot}"
    detail = (f"{len(rows)} unlock groups of bid offerings: " + "; ".join(f"{e} {s} {c}" for (e, s), c in sorted(counts.items()))
              + ". Holder rows in the two class months: " + ", ".join(f"{e} {v}" for e, v in share.items())
              + ". Every other lock month is named below with what marks it; a lock shorter than the rules' minimum would fail this.")
    return {"name": "B110-2", "kind": "known_answer",
            "criterion": "no holder of a bid offering is locked for less than the rules' minimum, and every lock month other than the two class months is named",
            "passed": passed, "detail": detail,
            "payload": {"counts": {f"{e} {s}": c for (e, s), c in sorted(counts.items())},
                        "holder_rows_by_month": {f"{e} {m}": c for (e, m), c in sorted(holders.items(), key=lambda kv: (kv[0][0], kv[0][1] is None, kv[0][1] or 0))},
                        "named": dict(sorted(longer.items())), "mapping": LOCK_MAP}}


def criterion_join(frame: list[dict], bars, outcomes: collections.Counter, room: float = DIVIDEND_ROOM,
                   band: float = FACTOR_BAND) -> dict:
    rows = [(o, *shares_state(o, bars.series(o["code"]), room, band)) for o in frame]
    bid = [(o, st, why) for o, st, why in rows if o["way"] == BID_WAY]
    counts = collections.Counter((o["way"], o["era"], st) for o, st, _ in rows)
    passed = verdict_of([st for _, st, _ in bid], SHARES_MAP)
    bad = [f"{o['code']} {o['T']} ({why})" for o, st, why in bid if SHARES_MAP[st] is False]
    short = [f"{o['code']} {o['T']} ({why})" for o, st, why in bid if st == "fewer shares than issued"]
    detail = (f"join: {dict(sorted(outcomes.items()))}. Bid offerings: "
              + "; ".join(f"{e} {s} {c}" for (w, e, s), c in sorted(counts.items()) if w == BID_WAY)
              + f". More shares than issued with no split to explain them: {len(bad)}" + (f": {bad}" if bad else "")
              + f". Fewer shares than issued, no verdict, and the readings leave them out: {len(short)}: {short}"
              + ". Priced offerings and mergers are printed, not judged: no reading here splits them by class. "
              + "; ".join(f"{w} {e} {s} {c}" for (w, e, s), c in sorted(counts.items()) if w != BID_WAY))
    return {"name": "B110-3", "kind": "instrument",
            "criterion": "the unlock groups joined to each bid offering add up to the shares it issued, or to them times the splits between",
            "passed": passed, "detail": detail,
            "payload": {"join": dict(sorted(outcomes.items())), "counts": {f"{w} {e} {s}": c for (w, e, s), c in sorted(counts.items())},
                        "more_than_issued_bid": bad, "fewer_than_issued_bid": short, "mapping": SHARES_MAP,
                        "dividend_room": room, "factor_band": band}}



# ---------------------------------------------------------------------------
# B110-4 to B110-7
# ---------------------------------------------------------------------------

RECORD = ROOT / "results" / "b110_placements.json"
SIGMA_SWEEP = (60, 120, SIGMA_DAYS)
K_SWEEP = (5, 10, 20)
EDGE_MAP = {"d above the bound under every volatility": True, "d within the bound under every volatility": False,
            "the sign moves with the volatility": None, "a volatility is missing": None}
HIGH_MAP = {"price above the day's high": True, "price at or below the day's high": False, "no price record on T": None}
PM_COLUMNS = ("close on T", "close the traded day before", "base VWAP20 at T-2")


def t_deal(n: float, N: float, pm: float, price: float) -> float:
    """What the old holders hand the new ones at one issue: n shares bought at P into a firm whose N
    shares trade at Pm, so a share afterwards is worth (N Pm + n P) / (N + n)."""
    return n * N * (pm - price) / (N + n)


def issue_shares(o: dict, g: dict, series: dict | None) -> float:
    """A group's shares taken back to the issue through the split days between T and its unlock."""
    if series is None or o["row_T"] is None:
        return g["shares"]
    end = last_row_on_or_before(series, g["free_date"])
    if end is None or end <= o["row_T"]:
        return g["shares"]
    f = series["factor"][o["row_T"] + 1:end + 1]
    big = f[f >= SPLIT_FACTOR]
    return g["shares"] / (float(np.prod(big)) if big.size else 1.0)


def class_label(o: dict, months: int | None) -> str:
    short, long_ = CLASS_MONTHS[o["era"]]
    if months in (short, long_):
        return f"{months} months"
    return "no lock month" if months is None else "other lock months"


def text_kind(principle: str) -> str:
    """What a 网下定价发行 row's pricing text prices: cash, assets, or both parts of one deal."""
    a = [principle.find(w) for w in ASSET_WORDS if w in principle]
    m = [principle.find(w) for w in MATCHING_WORDS if w in principle]
    if not a or (m and min(m) < min(a)):
        return "cash"
    return "both parts" if m else "for assets"


def proceeds_state(o: dict) -> str:
    if o["gross"] is None or o["net"] is None:
        return "proceeds not printed"
    if o["net"] < o["gross"]:
        return "net below gross"
    return "net equal to gross" if o["net"] == o["gross"] else "net above gross"


def priced_state(o: dict) -> str:
    """A 网下定价发行 offering is a cash placement when its text reads cash and the source nets an issuance cost
    from its proceeds, the footprint a cash placement carries (the record prints how many bid offerings carry it)."""
    kind = text_kind(o["principle"])
    if kind != "cash":
        return kind
    state = proceeds_state(o)
    return "cash" if state == "net below gross" else f"cash by its text, {state}"


def priced_reason(state: str) -> str | None:
    """Why a 网下定价发行 offering in this state stays out of the transfer table, or None."""
    if state == "cash":
        return None
    if state == "for assets":
        return f"{PRICED_WAY} for assets: the new holders pay with assets priced in the same deal, so n N (Pm - P) / (N + n) is not a transfer"
    if state == "both parts":
        return f"{PRICED_WAY}, one text pricing the asset part and the matching funds of a deal: which part this row is is not said"
    return f"{PRICED_WAY}, {state}: not told apart from an issue paid in assets"


def gate(o: dict, floor_states: dict) -> str | None:
    """Why an offering stays out of B110-4 to B110-6, or None."""
    if o["way"] not in (BID_WAY, PRICED_WAY):
        return f"{o['way'] or 'no way'}: not a cash placement"
    if o["P"] is None or o["n"] is None or o["N"] is None:
        return "price or shares missing in the offering table"
    if o["bars"] != "ok":
        return o["bars"]
    if o["way"] == BID_WAY and FLOOR_MAP[floor_states[o["id"]]] is False:
        return "B110-1: T does not fit the price floor"
    if o["way"] == PRICED_WAY:
        return priced_reason(priced_state(o))
    return None


def fold(verdicts: list) -> bool | None:
    """One verdict from many: any True is True; otherwise any False is False; otherwise no verdict."""
    if any(v is True for v in verdicts):
        return True
    return False if any(v is False for v in verdicts) else None


def transfer_breaches(all_ids: list[str], in_table: list[str], named: list[str], split: dict, by_class: dict) -> list[str]:
    """What B110-4's flag asserts, each breach named: every offering once, in the table or named and never
    both or neither; a table that is not empty; and the class split adding back, under each Pm, to the
    transfer of the offerings it splits."""
    out = []
    twice = sorted(i for i, c in collections.Counter(all_ids).items() if c > 1)
    if twice:
        out.append(f"offerings twice in scope: {twice[:5]}")
    both = sorted(set(in_table) & set(named))
    if both:
        out.append(f"offerings in the table and named: {both[:5]}")
    if sorted(all_ids) != sorted(in_table + named):
        out.append("the table and the named do not add up to the offerings in scope")
    if not in_table:
        out.append("the table is empty")
    for col, want in sorted(split.items()):
        got = sum(v.get(col, 0.0) for v in by_class.values())
        if abs(got - want) > 1e-9 * max(1.0, abs(want)):
            out.append(f"{col}: the classes add up to {got:.6g}, the offerings they split to {want:.6g}")
    return out


def yi(x: float) -> str:
    return f"{x / 1e8:,.2f}"


def criterion_transfers(frame: list[dict], bars, floor_states: dict, shares_states: dict) -> dict:
    by_year: dict = collections.defaultdict(lambda: collections.defaultdict(float))
    by_class: dict = collections.defaultdict(lambda: collections.defaultdict(float))
    in_table, named, unsplit = [], collections.defaultdict(list), collections.defaultdict(list)
    split = collections.defaultdict(float)
    priced_rows = collections.defaultdict(list)
    for o in frame:
        why = gate(o, floor_states)
        if why:
            named[why].append(o["id"])
            continue
        pms = {"close on T": o["Pm"], "close the traded day before": o["prev_close"],
               "base VWAP20 at T-2": o["vwap"][2] if o["way"] == BID_WAY else None}
        values = {k: t_deal(o["n"], o["N"], v, o["P"]) for k, v in pms.items() if v is not None}
        key = f"{o['way']} {o['T'][:4]}"
        by_year[key]["offerings"] += 1
        for k, v in values.items():
            by_year[key][k] += v
        in_table.append(o["id"])
        if o["way"] == PRICED_WAY and "close on T" in values:
            priced_rows[o["T"][:4]].append({"offering": o["id"], "code": o["code"], "name": o["name"], "T": o["T"], "P": o["P"],
                                            "Pm": o["Pm"], "n": o["n"], "N": o["N"], "close on T": values["close on T"]})
        if o["way"] != BID_WAY:
            continue
        if SHARES_MAP[shares_states[o["id"]]] is not True:
            unsplit[f"B110-3 {shares_states[o['id']]}"].append(o["id"])
            continue
        for k, v in values.items():
            split[k] += v
        series = bars.series(o["code"])
        parts = []
        for g in o["groups"]:
            base, held = issue_shares(o, g, series), sum(h[1] for h in g["holders"]) or 1.0
            label = class_label(o, g["lock_month"])
            for _, sh, cat in g["holders"]:
                short = label == f"{CLASS_MONTHS[o['era']][0]} months"
                parts.append((f"{o['T'][:4]} {label}" + (f" {cat}" if short else ""), base * sh / held))
        total = sum(sh for _, sh in parts) or 1.0
        for label, sh in parts:
            by_class[label]["shares issued"] += sh
            for k, v in values.items():
                by_class[label][k] += v * sh / total
    all_ids = [o["id"] for o in frame]
    named_ids = [i for ids in named.values() for i in ids]
    breaches = transfer_breaches(all_ids, in_table, named_ids, dict(split), by_class)
    priced = [o for o in frame if o["way"] == PRICED_WAY]
    priced_split = {s: {"offerings": 0, "issue value n P": 0.0} for s in PRICED_STATES}
    for o in priced:
        cell = priced_split[priced_state(o)]
        cell["offerings"] += 1
        if o["n"] is not None and o["P"] is not None:
            cell["issue value n P"] += o["n"] * o["P"]
    text_by_proceeds = collections.Counter(f"{text_kind(o['principle'])}, {proceeds_state(o)}" for o in priced)
    bid_proceeds = collections.Counter(proceeds_state(o) for o in frame if o["way"] == BID_WAY)
    passed = not breaches
    years = sorted(by_year)
    detail = (f"Breaches of the table's shape: {'; '.join(breaches) if breaches else 'none'}. "
              f"{len(in_table)} of {len(frame)} offerings in the year table, {len(named_ids)} named with the reason they are "
              f"not: " + "; ".join(f"{k} {len(v)}" for k, v in sorted(named.items()))
              + ". Transfer to the new holders, n N (Pm - P) / (N + n), in 100 million yuan, Pm the close on T / the close "
              "the day before / the base VWAP20 at T-2: "
              + "; ".join(f"{k}: {int(by_year[k]['offerings'])} offerings, " + " / ".join(yi(by_year[k][c]) if c in by_year[k] else "-" for c in PM_COLUMNS)
                          for k in years)
              + f". Bid offerings in the year table but not split by class: " + "; ".join(f"{k} {len(v)}" for k, v in sorted(unsplit.items()))
              + f". The {len(priced)} {PRICED_WAY} offerings in scope by what the pricing text prices and whether net proceeds "
              "sit below gross, with the issue value n P in 100 million yuan: "
              + "; ".join(f"{s} {v['offerings']} ({yi(v['issue value n P'])})" for s, v in priced_split.items())
              + "; bid offerings by the same proceeds reading: " + "; ".join(f"{k} {v}" for k, v in sorted(bid_proceeds.items()))
              + ".")
    return {"name": "B110-4", "kind": "own_reading",
            "criterion": "what the edge hands over and to which class, year by year, with every offering once in the table or named and the class split adding back to the offerings it splits",
            "passed": passed, "detail": detail,
            "payload": {"by_year": {k: dict(v) for k, v in sorted(by_year.items())},
                        "by_class": {k: dict(v) for k, v in sorted(by_class.items())},
                        "named": {k: sorted(v) for k, v in sorted(named.items())},
                        "not_split_by_class": {k: sorted(v) for k, v in sorted(unsplit.items())},
                        "breaches": breaches, "split_offerings_total": dict(split),
                        "priced": {"states": priced_split, "mapping": {s: priced_reason(s) or "in the table" for s in PRICED_STATES},
                                   "text_by_proceeds": dict(sorted(text_by_proceeds.items())),
                                   "extremes_by_year": {y: {"lowest": sorted(r, key=lambda x: (x["close on T"], x["offering"]))[:3],
                                                            "highest": sorted(r, key=lambda x: (-x["close on T"], x["offering"]))[:3]}
                                                        for y, r in sorted(priced_rows.items())},
                                   "bid_proceeds": dict(sorted(bid_proceeds.items()))}}}


def edge_state(xs: dict) -> str:
    if any(v is None for v in xs.values()):
        return "a volatility is missing"
    if all(v > 0 for v in xs.values()):
        return "d above the bound under every volatility"
    if all(v <= 0 for v in xs.values()):
        return "d within the bound under every volatility"
    return "the sign moves with the volatility"


def edge_cells(o: dict, series: dict, bars_through: str) -> list[dict]:
    cells = []
    for g in o["groups"]:
        years = (dt.date.fromisoformat(g["free_date"]) - dt.date.fromisoformat(o["T"])).days / 365.25
        sig = {f"{n} traded days before T": sigma_before(series, o["row_T"], n) for n in SIGMA_SWEEP}
        end = last_row_on_or_before(series, g["free_date"])
        sig["over the lock"] = (sigma_after(series, o["row_T"], end)
                                if end is not None and g["free_date"] <= bars_through else None)
        bounds = {k: (longstaff(v, years) if v is not None else None) for k, v in sig.items()}
        xs = {k: (o["d"] - b if b is not None else None) for k, b in bounds.items()}
        cats = collections.Counter(h[2] for h in g["holders"])
        cells.append({"offering": o["id"], "era": o["era"], "class": class_label(o, g["lock_month"]), "months": g["lock_month"],
                      "unlock": g["free_date"], "years": years, "d": o["d"], "sigma": sig, "bound": bounds, "state": edge_state(xs),
                      "holders": dict(cats.most_common())})
    return cells


def criterion_edge(frame: list[dict], bars, floor_states: dict, shares_states: dict, bars_through: str) -> dict:
    cells, named = [], collections.defaultdict(list)
    for o in frame:
        if o["way"] != BID_WAY:
            continue
        why = gate(o, floor_states)
        if why is None and SHARES_MAP[shares_states[o["id"]]] is not True:
            why = f"B110-3 {shares_states[o['id']]}"
        if why:
            named[why].append(o["id"])
            continue
        cells.extend(edge_cells(o, bars.series(o["code"]), bars_through))
    verdicts = [EDGE_MAP[c["state"]] for c in cells]
    passed = fold(verdicts)
    counts = collections.Counter((c["era"], c["class"], c["state"]) for c in cells)
    above = [c for c in cells if EDGE_MAP[c["state"]] is True]
    spread = {}
    for era in ("2017", "2020"):
        for cl in sorted({c["class"] for c in cells if c["era"] == era}):
            xs = [c["d"] - c["bound"][f"{SIGMA_DAYS} traded days before T"] for c in cells
                  if c["era"] == era and c["class"] == cl and c["bound"][f"{SIGMA_DAYS} traded days before T"] is not None]
            spread[f"{era} {cl}"] = q(xs)
    detail = (f"{len(cells)} class cells of bid offerings (an offering, a lock month): "
              + "; ".join(f"{e} {cl} {st} {c}" for (e, cl, st), c in sorted(counts.items()))
              + f". Above the bound under every volatility: {len(above)}"
              + (": " + "; ".join(f"{c['offering']} {c['class']} ({c['months']} months, unlock {c['unlock']}) d {c['d']:.4f}, bound "
                                  + "/".join(f"{b:.4f}" for b in c["bound"].values()) + f", holders {c['holders']}" for c in above) if above else "")
              + ". d minus the bound with the 250-day volatility, by rules period and class: "
              + "; ".join(f"{k} {v}" for k, v in spread.items())
              + ". Offerings out of this reading: " + "; ".join(f"{k} {len(v)}" for k, v in sorted(named.items())) + ".")
    return {"name": "B110-5", "kind": "own_reading",
            "criterion": "a bid offering whose discount d exceeds Longstaff's bound on what its lock can be worth, under the volatility of 60, 120 and 250 traded days before T and over the lock itself",
            "passed": passed, "detail": detail,
            "payload": {"counts": {f"{e} {cl} {st}": c for (e, cl, st), c in sorted(counts.items())},
                        "above": above, "spread_250": spread, "named": {k: sorted(v) for k, v in sorted(named.items())},
                        "mapping": EDGE_MAP, "sigma_sweep": list(SIGMA_SWEEP)}}


def high_state(o: dict) -> str:
    if o["bars"] != "ok" or o["P"] is None or o["H"] is None or o["ticks_over_high"] is None:
        return "no price record on T"
    return "price above the day's high" if o["ticks_over_high"] > 0 else "price at or below the day's high"


def adv20(series: dict, row: int) -> float | None:
    """Average daily volume of the 20 traded days before `row`, in the share count of `row`."""
    traded = series["traded"]
    cut = int(np.searchsorted(traded, row))
    if cut < VWAP_DAYS:
        return None
    idx = traded[cut - VWAP_DAYS:cut]
    return float((series["volume"][idx] * (series["g"][row] / series["g"][idx])).mean())


def criterion_high(frame: list[dict], bars, floor_states: dict, shares_states: dict) -> dict:
    rows, named = [], collections.defaultdict(list)
    for o in frame:
        if o["way"] != BID_WAY:
            continue
        why = gate(o, floor_states)
        if why:
            named[why].append(o["id"])
            continue
        series = bars.series(o["code"])
        rows.append((o, high_state(o), adv20(series, o["row_T"])))
    verdicts = [HIGH_MAP[st] for _, st, _ in rows]
    passed = fold(verdicts)
    above = []
    for o, st, adv in rows:
        if HIGH_MAP[st] is not True:
            continue
        if SHARES_MAP[shares_states[o["id"]]] is True:
            classes = collections.Counter()
            for g in o["groups"]:
                for _, sh, cat in g["holders"]:
                    classes[f"{class_label(o, g['lock_month'])} {cat}"] += 1
            cls = dict(classes.most_common())
        else:
            cls = f"not split: B110-3 {shares_states[o['id']]}"
        above.append({"offering": o["id"], "name": o["name"], "ticks_over_high": o["ticks_over_high"], "P": o["P"], "H": o["H"],
                      "issue_over_adv20": (o["n"] / adv) if adv else None, "classes": cls})
    ratio = sorted(((o["n"] / adv), HIGH_MAP[st] is True) for o, st, adv in rows if adv and HIGH_MAP[st] is not None)
    curve = []
    for i in range(10):
        chunk = ratio[i * len(ratio) // 10:(i + 1) * len(ratio) // 10]
        if chunk:
            curve.append({"from": chunk[0][0], "to": chunk[-1][0], "offerings": len(chunk), "above the high": sum(a for _, a in chunk)})
    big = []
    for o, st, adv in rows:
        if SHARES_MAP[shares_states[o["id"]]] is not True:
            continue
        series = bars.series(o["code"])
        for g in o["groups"]:
            base, held = issue_shares(o, g, series), sum(h[1] for h in g["holders"]) or 1.0
            for nm, sh, cat in g["holders"]:
                if base * sh / held > 0.3 * (o["N"] + o["n"]):
                    big.append(f"{o['id']} {nm} {base * sh / held / (o['N'] + o['n']):.3f} of the shares after the issue")
    counts = collections.Counter((o["era"], st) for o, st, _ in rows)
    detail = (f"{len(rows)} bid offerings with a price record on T: " + "; ".join(f"{e} {s} {c}" for (e, s), c in sorted(counts.items()))
              + f". Above the day's high: {len(above)}: " + "; ".join(f"{a['offering']} {a['name']} {a['ticks_over_high']} ticks, classes {a['classes']}" for a in above)
              + ". Share of offerings above the high by tenth of issue size over the 20-day average volume before T: "
              + "; ".join(f"{c['from']:.2f}-{c['to']:.2f}: {c['above the high']}/{c['offerings']}" for c in curve)
              + f". Holders whose allocation alone passes 30% of the shares after the issue (their holdings before it are not in the cache): {len(big)}"
              + (f": {big}" if big else "") + ". Offerings out of this reading: " + "; ".join(f"{k} {len(v)}" for k, v in sorted(named.items())) + ".")
    return {"name": "B110-6", "kind": "own_reading",
            "criterion": "a class that paid more for restricted shares than the free share cost at any moment of T",
            "passed": passed, "detail": detail,
            "payload": {"counts": {f"{e} {s}": c for (e, s), c in sorted(counts.items())}, "above": above, "curve": curve,
                        "allocation_over_30_percent": big, "named": {k: sorted(v) for k, v in sorted(named.items())},
                        "mapping": HIGH_MAP}}


COVER_FIELDS = (("price P", "offering table"), ("shares issued n", "offering table"), ("shares before N", "offering table"),
                ("listing date", "offering table"), ("pricing text", "offering table"), ("lock text", "offering table"),
                ("a traded row on T", "baostock bars"), ("close the traded day before T", "baostock bars"),
                ("VWAP20 at T-2", "baostock bars"), ("volatility over 250 traded days before T", "baostock bars"),
                ("an unlock group joined", "unlock batches and holder rows"), ("shares add up (B110-3)", "the join"))


def coverage_rows(frame: list[dict], shares_states: dict) -> list[dict]:
    rows = []
    for o in frame:
        have = [o["P"] is not None, o["n"] is not None, o["N"] is not None, bool(o["listing"]), bool(o["principle"]),
                bool(o["lock_text"]), o["bars"] == "ok", o["prev_close"] is not None, o["vwap"][2] is not None,
                o["sigma_pre"] is not None, bool(o["groups"]), SHARES_MAP[shares_states[o["id"]]] is True]
        rows.append({"offering": o["id"], "way": o["way"], "have": dict(zip((f for f, _ in COVER_FIELDS), have))})
    return rows


def coverage_breaches(frame: list[dict], rows: list[dict]) -> list[str]:
    """What B110-7's flag asserts, each breach named: one row for each offering in scope and none for
    anything else, every field in every row, and a table that is not empty."""
    out = []
    got, want = collections.Counter(r["offering"] for r in rows), collections.Counter(o["id"] for o in frame)
    extra, missing = sorted((got - want).elements()), sorted((want - got).elements())
    if extra:
        out.append(f"a second row, or a row for no offering in scope: {extra[:5]}")
    if missing:
        out.append(f"offerings in scope with no row: {missing[:5]}")
    fields = [f for f, _ in COVER_FIELDS]
    short = sorted(r["offering"] for r in rows if list(r["have"]) != fields)
    if short:
        out.append(f"rows without every field: {short[:5]}")
    if not rows:
        out.append("the table is empty")
    return out


def criterion_coverage(frame: list[dict], rows: list[dict]) -> dict:
    breaches = coverage_breaches(frame, rows)
    passed = not breaches
    ways = sorted({r["way"] or "no way" for r in rows})
    counts = {field: {f"{w} {s}": 0 for w in ways for s in ("present", "absent")} for field, _ in COVER_FIELDS}
    absent = {field: [] for field, _ in COVER_FIELDS}
    for r in rows:
        for field, have in r["have"].items():
            if field in counts:
                counts[field][f"{r['way'] or 'no way'} {'present' if have else 'absent'}"] += 1
                if not have:
                    absent[field].append(r["offering"])
    detail = (f"{len(rows)} rows for {len(frame)} offerings in scope. Breaches of the table's shape: "
              f"{'; '.join(breaches) if breaches else 'none'}. Per field, where it comes from and how many "
              "offerings have it, zero counts included: "
              + "; ".join(f"{field} ({src}): " + ", ".join(f"{k} {v}" for k, v in counts[field].items()) for field, src in COVER_FIELDS) + ".")
    return {"name": "B110-7", "kind": "bookkeeping",
            "criterion": "a coverage table with one row per offering in scope and every field's source, empty fields included",
            "passed": passed, "detail": detail,
            "payload": {"fields": {f: s for f, s in COVER_FIELDS}, "counts": {k: dict(v) for k, v in sorted(counts.items())},
                        "absent": {k: sorted(v) for k, v in sorted(absent.items())}, "breaches": breaches}}


def clean(x):
    """The record's numbers through one format, so two machines write the same bytes."""
    if isinstance(x, bool) or x is None or isinstance(x, (str, int)):
        return x
    if isinstance(x, (float, np.floating)):
        return float(format(float(x), ".6g")) if math.isfinite(float(x)) else None
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return str(x)


def config_block(d: dict) -> dict:
    t = d["tables"]
    return {"scope": {"from": SCOPE_START, "seo_type": "1", "bid_way": BID_WAY, "priced_way": PRICED_WAY},
            "rules": {"floor": FLOOR, "class_months": CLASS_MONTHS, "minimum_months": MIN_MONTHS, "second_rules_from": RULE_2020,
                      "priced_text": {"asset_words": list(ASSET_WORDS), "matching_words": list(MATCHING_WORDS)}},
            "knobs": {"k_max": K_MAX, "k_sweep": list(K_SWEEP), "vwap_days": VWAP_DAYS, "sigma_days": SIGMA_DAYS,
                      "sigma_sweep": list(SIGMA_SWEEP), "join_lag_days": list(JOIN_LAG), "split_factor": SPLIT_FACTOR,
                      "dividend_room": DIVIDEND_ROOM, "factor_band": FACTOR_BAND, "tick": TICK,
                      "trading_days_per_year": TRADING_DAYS_PER_YEAR},
            "inputs": {"offerings": t["RPT_SEO_DETAIL"]["snapshot"], "unlock_batches": t["RPT_LIFT_STAGE"]["snapshot"],
                       "holder_files": len({(g["code"], g["free_date"]) for g in d["groups"]}), "bars_through": d["bars_through"],
                       "bars_stocks": len(d["bars"]), "bars_rows": d["bars"].rows()}}


def criteria_report(write: bool = False) -> int:
    d = load_all()
    frame, bars, seo_rows = d["frame"], d["bars"], d["tables"]["RPT_SEO_DETAIL"]["rows"]
    floor_states = {o["id"]: floor_state(o, bars.series(o["code"]))[0] for o in frame if o["way"] == BID_WAY}
    shares_states = {o["id"]: shares_state(o, bars.series(o["code"]))[0] for o in frame}
    out = [criterion_floor(frame, bars, seo_rows), criterion_locks(frame), criterion_join(frame, bars, d["outcomes"]),
           criterion_transfers(frame, bars, floor_states, shares_states),
           criterion_edge(frame, bars, floor_states, shares_states, d["bars_through"]),
           criterion_high(frame, bars, floor_states, shares_states),
           criterion_coverage(frame, coverage_rows(frame, shares_states))]
    for c in out:
        mark = {True: "PASS", False: "FAIL", None: "NO VERDICT"}[c["passed"]]
        print(f"\n[{mark}] {c['name']} ({c['kind']}) {c['criterion']}")
        print(f"  {c['detail']}")
        if "mapping" in c["payload"]:
            print("  state -> verdict: " + ", ".join(f"{k} -> {v}" for k, v in c["payload"]["mapping"].items()))
    b1 = out[0]["payload"]["named"]
    for st in ("adjusted after T", "base date written", "one-day average", "text price", "text price less dividends", MISSING):
        print(f"  B110-1 {st}: {len(b1[st])}: {b1[st][:8]}{' ...' if len(b1[st]) > 8 else ''}")
    print(f"  B110-1 before the scope, below the text price: {len(out[0]['payload']['before_scope_below'])}: {out[0]['payload']['before_scope_below'][:10]} ...")
    print("  B110-1 sweep of the k window (the station's own knob):")
    for k_max in (5, 10, 20):
        c = criterion_floor(frame, bars, seo_rows, k_max)
        print(f"    k up to {k_max}: {'PASS' if c['passed'] else 'FAIL'}, unclassified {len(c['payload']['named'][UNCLASSIFIED])}")
    for key, items in out[1]["payload"]["named"].items():
        print(f"  B110-2 {key}: {len(items)}: {items[:6]}{' ...' if len(items) > 6 else ''}")
    print("  B110-3 sweep of the two calibration values:")
    for room, band in ((0.03, 0.001), (0.06, 0.005), (0.10, 0.01)):
        c = criterion_join(frame, bars, d["outcomes"], room, band)
        print(f"    dividend room {room}, factor band {band}: {'PASS' if c['passed'] else 'FAIL'}, "
              f"more than issued {len(c['payload']['more_than_issued_bid'])}, fewer {len(c['payload']['fewer_than_issued_bid'])}")
    print("  B110-4 by class, 100 million yuan at the close on T:")
    for k, v in out[3]["payload"]["by_class"].items():
        print(f"    {k}: {yi(v.get('close on T', 0.0))} ({v.get('shares issued', 0.0) / 1e8:,.2f} hundred million shares)")
    if write:
        record = clean({"stage": "B110", "config": config_block(d), "criteria": out})
        body = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
        P.atomic_write_bytes(RECORD, body)
        print(f"\nrecord -> {RECORD.relative_to(ROOT)}, {len(body):,} bytes, sha256 {hashlib.sha256(body).hexdigest()[:16]}")
    return 0


# ---------------------------------------------------------------------------
# The printout
# ---------------------------------------------------------------------------

def q(values, qs=(0.0, 0.1, 0.5, 0.9, 1.0), fmt="{:.4f}") -> str:
    v = sorted(x for x in values if x is not None and math.isfinite(x))
    if not v:
        return "none"
    return " ".join(f"q{int(p * 100)}=" + fmt.format(v[int(round(p * (len(v) - 1)))]) for p in qs) + f"  n={len(v)}"


def frame_report(rebuild_bars: bool = False) -> int:
    d = load_all(rebuild_bars)
    frame, groups, bars, through = d["frame"], d["groups"], d["bars"], d["bars_through"]
    t = d["tables"]
    print(f"tables: offerings {t['RPT_SEO_DETAIL']['snapshot']}, unlock batches {t['RPT_LIFT_STAGE']['snapshot']}")
    print(f"bars: {d['bars_note']}; {len(bars)} stocks, {bars.rows():,} rows; bars through {through} ({d['through_note']})")

    print(f"\n== offerings: SEO_TYPE 1, ISSUE_DATE from {SCOPE_START}: {len(frame)}")
    cells = collections.defaultdict(collections.Counter)
    for o in frame:
        cells[(o["era"], o["way"])][o["bars"]] += 1
    for (era, way), c in sorted(cells.items()):
        print(f"  {era} {way:8s} {sum(c.values()):5d}  " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    for label in ("no bars", "T is not a row", "suspended on T"):
        names = [f"{o['code']} {o['T']} {o['way']}" for o in frame if o["bars"] == label]
        if names:
            print(f"  {label}: {len(names)}: {names[:12]}{' ...' if len(names) > 12 else ''}")

    bid = [o for o in frame if o["way"] == BID_WAY]
    print(f"\n== bid offerings ({BID_WAY}): {len(bid)}")
    for era in ("2017", "2020"):
        rows = [o for o in bid if o["era"] == era]
        ks = collections.Counter(o["min_k"] for o in rows)
        print(f"  {era}: floor {FLOOR[era]}: smallest k with P >= floor x VWAP20(T-k) - 0.01: "
              + ", ".join(f"k={k} {v}" for k, v in sorted(ks.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))))
        none = [o for o in rows if o["min_k"] is None]
        for o in none[:10]:
            ratios = " ".join(f"{(o['P'] / v):.3f}" if v else "-" for v in o["vwap"])
            s = bars.series(o["code"])
            moves = []
            if s is not None and o["row_T"] is not None and o["listing"]:
                end = last_row_on_or_before(s, o["listing"])
                for j in range(max(1, o["row_T"] - 30), (end or 0) + 1):
                    if s["factor"][j] != 1.0:
                        moves.append((dt.date.fromordinal(int(s["ordinal"][j])).isoformat(), round(float(s["factor"][j]), 4)))
            print(f"      no k: {o['code']} {o['T']} P={o['P']} bars={o['bars']} P/VWAP20(T-0..T-10)= {ratios}; "
                  f"adjustments from T-30 to listing {o['listing']}: {moves}")
        if len(none) > 10:
            print(f"      ... {len(none) - 10} more")

    print(f"\n== unlock groups: {len(groups)} from {len(groups and {(g['code'], g['free_date']) for g in groups})} batch files; "
          f"batches with no holder file: {len(d['absent'])} {d['absent'][:5]}")
    print(f"  holder rows left out as not placement shares, by type: {dict(d['excluded'].most_common(8))}")
    print(f"  join: {dict(sorted(d['outcomes'].items()))}")
    lags = collections.Counter(g["lag"] for g in groups if g.get("lag") is not None)
    print(f"  lag of the fits, days after listing plus lock months: {dict(sorted(lags.items()))}")
    for how in ("two offerings fit equally", "no offering fits", "no lock month"):
        rows = [g for g in groups if g["how"] == how]
        if rows:
            print(f"  {how}: {len(rows)}")
            months = collections.Counter(g["lock_month"] for g in rows)
            print(f"      lock months: {dict(months.most_common(12))}")
            for g in rows[:8]:
                print(f"      {g['code']} {g['free_date']} lock {g['lock_month']} shares {g['shares']:,.0f} "
                      f"holders {len(g['holders'])}; latest offering before: {g.get('latest_before')}")

    print("\n== lock months of the groups joined to offerings in scope, by rules period and way")
    lm = collections.defaultdict(collections.Counter)
    for o in frame:
        for g in o["groups"]:
            lm[(o["era"], o["way"])][g["lock_month"]] += 1
    for key, c in sorted(lm.items()):
        print(f"  {key[0]} {key[1]:8s} " + ", ".join(f"{m}m {v}" for m, v in sorted(c.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))))

    print("\n== bid offerings, each class month: offerings with a group joined / offerings whose listing plus that month is on or before bars_through")
    for era in ("2017", "2020"):
        rows = [o for o in bid if o["era"] == era and o["listing"]]
        parts = []
        for m in CLASS_MONTHS[era]:
            due = [o for o in rows if P.add_months(dt.date.fromisoformat(o["listing"]), m).isoformat() <= through]
            hit = [o for o in due if any(g["lock_month"] == m for g in o["groups"])]
            future = sum(1 for o in rows if o not in due and any(g["lock_month"] == m for g in o["groups"]))
            parts.append(f"{m} months {len(hit)}/{len(due)} (and {future} joined ahead of the date)")
        other = collections.Counter(g["lock_month"] for o in rows for g in o["groups"] if g["lock_month"] not in CLASS_MONTHS[era])
        print(f"  {era}: " + "; ".join(parts) + f"; other months joined: {dict(other.most_common())}")

    print("\n== bid offerings: shares in the joined groups over shares issued")
    for era in ("2017", "2020"):
        rows = [o for o in bid if o["era"] == era]
        buckets = collections.Counter()
        for o in rows:
            r = o["ratio"]
            buckets["none joined" if not o["groups"] else "equal" if r is not None and abs(r - 1) < 1e-9
                    else "above one" if r is not None and r > 1 else "below one"] += 1
        print(f"  {era}: {dict(sorted(buckets.items()))}")
        above = sorted({round(o["ratio"], 4) for o in rows if o["groups"] and o["ratio"] and o["ratio"] > 1 + 1e-9})
        print(f"      ratios above one: {above[:30]}{' ...' if len(above) > 30 else ''}")
        below = sorted((o for o in rows if o["groups"] and o["ratio"] is not None and o["ratio"] < 1 - 1e-9), key=lambda o: o["ratio"])
        for o in below[:6]:
            print(f"      below: {o['code']} {o['T']} ratio {o['ratio']:.4f} months {[g['lock_month'] for g in o['groups']]} listing {o['listing']}")

    print("\n== holders of bid offerings by category (joined groups)")
    cat = collections.defaultdict(lambda: [0, 0.0])
    names = collections.defaultdict(collections.Counter)
    for o in bid:
        for g in o["groups"]:
            for nm, sh, c in g["holders"]:
                cat[c][0] += 1
                cat[c][1] += sh
                names[c][nm] += sh
    total = sum(v[1] for v in cat.values()) or 1.0
    for c in CATEGORIES:
        rows, shares = cat[c]
        print(f"  {c}: {rows} rows, {shares / total:.1%} of shares; largest: {[nm for nm, _ in names[c].most_common(6)]}")
    print(f"  其他, the next 20 by shares: {[nm for nm, _ in names['其他'].most_common(26)[6:]]}")

    print("\n== the reading's inputs, bid offerings with bars on T")
    for era in ("2017", "2020"):
        rows = [o for o in bid if o["era"] == era and o["bars"] == "ok"]
        print(f"  {era}: sigma before T  {q([o['sigma_pre'] for o in rows])}")
        print(f"  {era}: d = 1 - P/Pm    {q([o['d'] for o in rows])}")
        over = [o for o in rows if o["ticks_over_high"] is not None and o["ticks_over_high"] > 0]
        print(f"  {era}: P above the high of T: {len(over)}: {[(o['code'], o['T'], o['ticks_over_high']) for o in over[:10]]}")
        short = sum(1 for o in rows if o["sigma_pre"] is None)
        print(f"  {era}: fewer than {SIGMA_DAYS} traded days before T: {short}")
    priced = [o for o in frame if o["way"] == PRICED_WAY and o["bars"] == "ok"]
    for state, count in sorted(collections.Counter(priced_state(o) for o in priced).items()):
        print(f"  priced offerings, {state}: {count}, d at T: {q([o['d'] for o in priced if priced_state(o) == state])}")
    return 0


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    table = {(0.20, 6): 11.8, (0.20, 12): 17.0, (0.25, 18): 26.9, (0.30, 36): 48.7, (0.50, 36): 90.0,
             (0.40, 6): 24.6}
    worst = max(abs(longstaff(s, m / 12) * 100 - v) for (s, m), v in table.items())
    check(f"Longstaff's bound reproduces the design table to its printed digit (worst {worst:.3f} points)", worst <= 0.05)
    check("the bound is 20% at sigma 32.97% over six months and at 19.03% over eighteen, 10% at 12.07% over a year",
          abs(longstaff(0.3297, 0.5) - 0.20) < 5e-4 and abs(longstaff(0.1903, 1.5) - 0.20) < 5e-4
          and abs(longstaff(0.1207, 1.0) - 0.10) < 5e-4)
    wrong = (2.0 + 0.02 / 2) * norm_cdf(math.sqrt(0.02) / 2) - 1.0
    check("a bound missing its second term misses the table", abs(wrong * 100 - 11.8) > 0.05)

    # a stock with a suspended stretch inside the VWAP window
    days = [dt.date(2021, 3, 1) + dt.timedelta(days=i) for i in range(40)]
    status = np.array([0 if 20 <= i <= 22 else 1 for i in range(40)], dtype=np.int8)
    vol = np.array([0.0 if s == 0 else 1000.0 + 10 * i for i, s in enumerate(status)])
    price = np.array([10.0 + 0.1 * i for i in range(40)])
    series = {"ordinal": np.array([d.toordinal() for d in days], dtype=np.int32), "status": status,
              "close": price, "preclose": np.r_[price[0], price[:-1]], "high": price + 0.2, "low": price - 0.2,
              "open": price, "volume": vol, "amount": vol * price}
    finish_series(series)
    row = 35
    idx = [i for i in range(row) if status[i] == 1][-20:]
    hand = float(sum(vol[i] * price[i] for i in idx) / sum(vol[i] for i in idx))
    check("VWAP20 counts the 20 traded days before the row and skips suspended ones",
          abs(vwap_before(series, row) - hand) < 1e-12)
    rows_only = list(range(row - 20, row))
    naive = float(sum(vol[i] * price[i] for i in rows_only) / sum(vol[i] for i in rows_only))
    check("counting 20 rows instead gives a different number here, so the check above can fail", abs(naive - hand) > 1e-6)
    check("VWAP20 is None with fewer than 20 traded days", vwap_before(series, 15) is None)
    check("a row is found by its date, and a date with no row is None",
          row_of(series, days[7].isoformat()) == 7 and row_of(series, "2020-01-01") is None)

    # T-k counts rows: floor crossed at k = 2
    fl = {"ordinal": series["ordinal"], "status": np.ones(40, dtype=np.int8), "close": np.full(40, 10.0),
          "preclose": np.full(40, 10.0), "high": np.full(40, 10.0), "low": np.full(40, 10.0),
          "open": np.full(40, 10.0), "volume": np.full(40, 100.0), "amount": np.full(40, 1000.0)}
    fl["amount"][33:] = 1300.0   # the last days run up: VWAP20 before rows 34.. is higher
    finish_series(fl)
    r = bar_readings(fl, days[38].isoformat(), 8.08, 0.8)
    ks = [round(v, 4) for v in r["vwap"][:5]]
    # by hand: VWAP20 at T-0..T-5 is 10.75, 10.60, 10.45, 10.30, 10.15, 10.00, and 8.08 clears 0.8 x v - 0.01 only
    # from v <= 10.1125, so the smallest k is 5
    check(f"the smallest k is the first T-k whose VWAP20 the price clears (VWAP20 at T-0..T-4: {ks})",
          ks == [10.75, 10.6, 10.45, 10.3, 10.15] and r["min_k"] == 5)

    # VWAP20 across a two-for-one split, in the price basis after it
    sp = {"ordinal": fl["ordinal"], "status": np.ones(40, dtype=np.int8), "open": np.full(40, 10.0),
          "high": np.full(40, 10.0), "low": np.full(40, 10.0), "volume": np.full(40, 100.0), "amount": np.full(40, 1000.0),
          "close": np.full(40, 10.0), "preclose": np.full(40, 10.0)}
    sp["close"][30:], sp["preclose"][31:] = 5.0, 5.0
    sp["preclose"][30] = 5.0                  # the split day: the reference price is half the close before it
    sp["volume"][30:] = 200.0                 # the same turnover in twice the shares at half the price
    finish_series(sp)
    check("VWAP20 across a two-for-one split is taken at the price after it, 5.00 here",
          abs(vwap_before(sp, 38) - 5.0) < 1e-12 and float(sp["factor"][30]) == 2.0)
    plain = float(sp["amount"][18:38].sum() / sp["volume"][18:38].sum())
    check(f"and the unadjusted average is not ({plain:.4f})", abs(plain - 5.0) > 0.1)
    check("an average as of a day before the split, taken in the basis of a day after, is halved",
          abs(vwap_before(sp, 25, VWAP_DAYS, 38) - 5.0) < 1e-12 and abs(vwap_before(sp, 25) - 10.0) < 1e-12)

    # volatility across a two-for-one split
    rng = np.random.default_rng(3)
    ret = rng.normal(0, 0.02, 300)
    close = 20 * np.exp(np.cumsum(ret))
    pre = np.r_[20.0, close[:-1]]
    split = close.copy()
    split[150:] = close[150:] / 2
    pre_split = np.r_[20.0, split[:-1]]
    pre_split[150] = split[149] / 2        # the exchange's reference price on the split day
    base = {"close": close, "preclose": pre}
    halved = {"close": split, "preclose": pre_split}
    s1 = sigma_of(base, np.arange(300), 250)
    s2 = sigma_of(halved, np.arange(300), 250)
    naive_pre = np.r_[20.0, split[:-1]]
    s3 = sigma_of({"close": split, "preclose": naive_pre}, np.arange(300), 250)
    check("volatility from close over preclose is the same across a split", abs(s1 - s2) < 1e-12)
    check("and close over the previous close is not", abs(s3 - s1) > 0.01)

    # the join
    offers = [{"SECURITY_CODE": "600001", "ISSUE_DATE": "2021-01-05 00:00:00", "ISSUE_NUM": 1,
               "ISSUE_LISTING_DATE": "2021-01-20 00:00:00"},
              {"SECURITY_CODE": "600001", "ISSUE_DATE": "2021-07-01 00:00:00", "ISSUE_NUM": 2,
               "ISSUE_LISTING_DATE": "2021-07-20 00:00:00"}]
    s, how, lag = join_group(offers, "2021-07-20", 6)
    check("a group joins the offering whose listing plus the lock lands on the unlock", how == "fits" and lag == 0 and s["ISSUE_NUM"] == 1)
    check("three days early fits, four does not; twenty days late fits, twenty-one does not",
          join_group(offers, "2021-07-17", 6)[1] == "fits" and join_group(offers, "2021-07-16", 6)[1] == "no offering fits"
          and join_group(offers, "2021-08-09", 6)[1] == "fits" and join_group(offers, "2021-08-10", 6)[1] == "no offering fits")
    twins = offers + [dict(offers[0], ISSUE_NUM=3)]
    check("two offerings that fit equally are not guessed between", join_group(twins, "2021-07-20", 6)[1] == "two offerings fit equally")
    check("a group with no lock month joins nothing", join_group(offers, "2021-07-20", None)[1] == "no lock month")
    check("a month is added from the end of a month to the end of a shorter one",
          P.add_months(dt.date(2020, 8, 31), 6) == dt.date(2021, 2, 28))
    check("the latest offering before an unlock is the one issued last on or before it",
          latest_before(offers, "2021-12-31")["ISSUE_NUM"] == 2 and latest_before(offers, "2020-12-31") is None)

    names = {"财通基金管理有限公司": "公募", "诺德基金管理有限公司": "公募", "财通基金-光大银行-财通基金玉泉1号单一资产管理计划": "公募",
             "深圳市共同基金管理有限公司-共同定增私募证券投资基金": "私募", "济南瀚祥投资管理合伙企业(有限合伙)": "私募",
             "国投集新(北京)股权投资基金(有限合伙)": "私募", "广发证券股份有限公司": "证券公司", "华安证券资产管理有限公司": "证券公司",
             "UBS AG": "合格境外投资者", "摩根士丹利国际股份有限公司": "合格境外投资者", "J.P. Morgan Securities plc": "合格境外投资者",
             "大家资产管理有限责任公司": "保险", "中国人寿保险股份有限公司": "保险", "薛小华": "自然人",
             "湖北省铁路发展基金有限责任公司": "其他", "思格新能源股份有限公司": "其他", "兴银理财有限责任公司": "其他",
             "建信基金管理有限责任公司": "公募", "中国国际金融股份有限公司": "证券公司",
             "中国华融资产管理股份有限公司": "其他", "国泰君安资产管理(亚洲)有限公司": "合格境外投资者",
             "中国国有企业结构调整基金股份有限公司": "其他"}
    got = {nm: category(nm) for nm in names}
    check("holder names fall in their categories: " + ", ".join(f"{nm} {got[nm]}" for nm in names if got[nm] != names[nm]),
          got == names)

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        rows = [["2021-03-01", "sh.600001", "10.0000", "10.5000", "9.8000", "10.2000", "10.0000", "1000", "10200.0000", "1", "2.0", "0"],
                ["2021-03-02", "sh.600001", "10.2000", "10.2000", "10.2000", "10.2000", "10.2000", "0", "0.0000", "0", "0.0", "0"]]
        store = {"source": "baostock", "code": "sh.600001", "fields": list(P.BS_FIELDS),
                 "covered": [["2021-03-01", "2021-03-02"]], "rows": rows}
        (d / "600001.json").write_text(json.dumps(store), encoding="utf-8")
        cache = d / "bars.npz"
        b1, how1 = load_bars(store_files(d), cache)
        b2, how2 = load_bars(store_files(d), cache)
        check("the bars cache is built once and then read", how1.startswith("built") and how2.startswith("read"))
        sr = b2.series("600001")
        check("the cache holds the rows: two days, one traded, the suspended day's volume zero",
              sr is not None and len(sr["ordinal"]) == 2 and list(sr["traded"]) == [0] and float(sr["volume"][1]) == 0.0
              and float(sr["close"][0]) == 10.2)
        store["rows"].append(["2021-03-03", "sh.600001", "10.2000", "10.9000", "10.1000", "10.8000", "10.2000", "1500",
                              "16000.0000", "1", "5.9", "0"])
        store["covered"] = [["2021-03-01", "2021-03-03"]]
        (d / "600001.json").write_text(json.dumps(store), encoding="utf-8")
        b3, how3 = load_bars(store_files(d), cache)
        check("a changed store file rebuilds the cache", how3.startswith("built") and len(b3.series("600001")["ordinal"]) == 3)


    # ---- B110-1 to B110-3: the failures each check exists for, seeded, and the state maps
    days60 = [(dt.date(2021, 1, 4) + dt.timedelta(days=i)).isoformat() for i in range(60)]
    flat = finish_series({"ordinal": np.array([dt.date.fromisoformat(x).toordinal() for x in days60], dtype=np.int32),
                          "status": np.ones(60, dtype=np.int8), "open": np.full(60, 10.0), "high": np.full(60, 10.2),
                          "low": np.full(60, 9.8), "close": np.full(60, 10.0), "preclose": np.full(60, 10.0),
                          "volume": np.full(60, 100.0), "amount": np.full(60, 1000.0)})
    first_day = "本次发行的定价基准日为发行期首日，发行价格不低于定价基准日前20个交易日股票交易均价的80%。"

    def offer(price, text=first_day, code="600001", n=1000.0, era="2020", series=flat):
        o = {"id": f"{code}:{days60[50]}:{n}", "code": code, "name": "测试", "T": days60[50], "era": era, "way": BID_WAY,
             "P": price, "n": n, "N": 10000.0, "listing": days60[55], "lock_text": "0.5年", "principle": text, "groups": [],
             "gross": None, "net": None}
        o.update(bar_readings(series, o["T"], price, FLOOR[era]))
        return o

    class Stub:
        def __init__(self, table):
            self.table = table

        def series(self, code):
            return self.table.get(code)

    stub = Stub({"600001": flat})
    ok_o, low_o = offer(8.0), offer(7.0)
    miss_o = offer(7.0, code="600002")
    board = "本次非公开发行的定价基准日为董事会决议公告日，发行价格不低于定价基准日前20个交易日股票交易均价的90%，即不低于7.00元/股。如在定价基准日至发行期首日期间除权，发行价格相应调整。"
    states = {"ok": floor_state(ok_o, flat)[0], "low": floor_state(low_o, flat)[0], "missing": floor_state(miss_o, None)[0],
              "board": floor_state(offer(7.0, board), flat)[0],
              "first day with a printed price": floor_state(offer(7.0, first_day + "即不低于7.00元/股。"), flat)[0]}
    check(f"B110-1 states: {states}",
          states == {"ok": "at T-k", "low": UNCLASSIFIED, "missing": MISSING, "board": "text price",
                     "first day with a printed price": UNCLASSIFIED})
    check("B110-1 maps a missing price to no verdict, a clear floor to consistent, an unexplained miss to a violation",
          FLOOR_MAP[MISSING] is None and FLOOR_MAP["at T-k"] is True and FLOOR_MAP[UNCLASSIFIED] is False)
    check("B110-1 fails on a seeded miss and passes with the miss replaced by a missing price",
          criterion_floor([ok_o, low_o], stub, [])["passed"] is False and criterion_floor([ok_o, miss_o], stub, [])["passed"] is True)
    try:
        verdict_of(["no such state"], FLOOR_MAP)
        raised = None
    except KeyError as err:
        raised = err
    check("a state no map names is an error, not a pass", isinstance(raised, KeyError))

    def grp(free, months, shares, deal=None, code="600001"):
        return {"code": code, "free_date": free, "lock_month": months, "holders": [("某基金管理有限公司", float(shares), "公募")],
                "shares": float(shares), "how": "fits", "deal": deal}

    lk = {"class": lock_state(ok_o, grp("2021-08-23", 6, 1)), "early": lock_state(ok_o, grp("2021-08-20", 5, 1)),
          "short count": lock_state(ok_o, grp("2021-08-25", 5, 1)), "none": lock_state(ok_o, grp("2021-08-25", None, 1)),
          "long": lock_state(ok_o, grp("2023-02-23", 24, 1))}
    check("B110-2 states: " + ", ".join(f"{k} {v[0]}" for k, v in lk.items()),
          [v[0] for v in lk.values()] == ["a class month", "shorter than the minimum",
                                          "month count below the minimum, the unlock after T plus the minimum",
                                          "no lock month", "longer than the class months"])
    locked = dict(ok_o, groups=[grp("2021-08-23", 6, 1000)])
    early = dict(ok_o, groups=[grp("2021-08-20", 6, 1000)])
    check("B110-2 fails on an unlock before T plus the minimum and passes without it",
          criterion_locks([early])["passed"] is False and criterion_locks([locked])["passed"] is True
          and LOCK_MAP["no lock month"] is None)

    split = finish_series({k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in flat.items()
                           if k in ("ordinal", "status", "open", "high", "low", "close", "preclose", "volume", "amount")})
    split["close"][53:] = 10.0 / 1.48
    split["preclose"][54:] = 10.0 / 1.48
    split["preclose"][53] = round(10.0 / 1.4797, 4)
    finish_series(split)
    sh = {"equal": shares_state(dict(ok_o, groups=[grp("2021-08-23", 6, 1000)]), flat)[0],
          "fewer": shares_state(dict(ok_o, groups=[grp("2021-08-23", 6, 500)]), flat)[0],
          "more": shares_state(dict(ok_o, groups=[grp("2021-08-23", 6, 1480)]), flat)[0],
          # 688535 in the data: 9,618,852 issued, 14,235,902 at the unlock, a split day whose factor prints 1.4797
          "split": shares_state(dict(ok_o, n=9618852.0, groups=[grp("2021-03-01", 6, 14235902)]), split)[0],
          "split, too many": shares_state(dict(ok_o, n=9618852.0, groups=[grp("2021-03-01", 6, 19237704)]), split)[0]}
    check(f"B110-3 states: {sh}",
          sh == {"equal": "equal", "fewer": "fewer shares than issued", "more": "more shares than issued, no split explains them",
                 "split": "splits between T and the unlock", "split, too many": "more shares than issued, no split explains them"})
    check("B110-3 fails on more shares than issued and gives fewer no verdict",
          criterion_join([dict(ok_o, groups=[grp("2021-08-23", 6, 1480)])], stub, collections.Counter())["passed"] is False
          and criterion_join([dict(ok_o, groups=[grp("2021-08-23", 6, 500)])], stub, collections.Counter())["passed"] is True)

    # the join's second and third passes
    a = dict(ok_o, id="600001:A", n=100.0, groups=[])
    a["groups"] = [grp("2021-08-23", 6, 60, "600001:A"), grp("2021-08-24", 7, 40, "600001:A"), grp("2021-09-01", 8, 30, "600001:A")]
    out = trim_excess([a], stub, {}, set())
    check("an offering thirty shares over lets go of the one group of thirty",
          out["excess let go"] == 1 and sum(g["shares"] for g in a["groups"]) == 100)
    b = dict(ok_o, id="600001:B", n=50.0, groups=[grp("2021-08-23", 6, 20, "600001:B")])
    loose = [grp("2021-08-25", 9, 30), grp("2021-08-26", 10, 11)]
    fill_gaps([b], loose, stub)
    check("an offering thirty short takes the one loose group of thirty", sum(g["shares"] for g in b["groups"]) == 50
          and loose[0]["deal"] == "600001:B" and loose[1]["deal"] is None)
    b2 = dict(ok_o, id="600001:B2", n=50.0, groups=[grp("2021-08-23", 6, 20, "600001:B2")])
    twins = [grp("2021-08-25", 9, 30), grp("2021-08-26", 10, 30)]
    out = fill_gaps([b2], twins, stub)
    check("and takes neither of two that fit", all(g["deal"] is None for g in twins) and out["share gap filled"] == 0)
    b3 = dict(ok_o, id="600001:B3", n=50.0, groups=[grp("2021-08-23", 6, 20, "600001:B3")])
    moved = [grp("2021-03-02", 9, 30)]
    out = fill_gaps([b3], moved, Stub({"600001": split}))
    check("and takes nothing across a split", moved[0]["deal"] is None and out["share gap left: a split between T and the loose groups"] == 1)
    c = dict(ok_o, id="600001:C", n=18.0, groups=[])
    mixed = grp("2021-08-23", 6, 0, "600001:C")
    mixed["holders"] = [("资产出售方有限公司", 93.0, "其他"), ("某基金管理有限公司", 12.0, "公募")]
    mixed["shares"] = 105.0
    c["groups"] = [mixed, grp("2023-02-23", 24, 6, "600001:C")]
    home = {"600001": [{"SECURITY_CODE": "600001", "ISSUE_DATE": "2021-01-05", "ISSUE_NUM": 93}]}
    trim_excess([c], stub, home, set())
    check("an excess equal to another offering's shares moves the rows that add up to it",
          sum(g["shares"] for g in c["groups"]) == 18 and [h[0] for h in c["groups"][0]["holders"]] == ["某基金管理有限公司"])
    c2 = dict(ok_o, id="600001:C2", n=18.0, groups=[])
    mixed2 = grp("2021-08-23", 6, 0, "600001:C2")
    mixed2["holders"] = [("资产出售方有限公司", 93.0, "其他"), ("某基金管理有限公司", 12.0, "公募")]
    mixed2["shares"] = 105.0
    c2["groups"] = [mixed2, grp("2023-02-23", 24, 6, "600001:C2")]
    trim_excess([c2], stub, {}, set())
    check("and moves nothing when no offering has that many shares", sum(g["shares"] for g in c2["groups"]) == 111)

    # ---- B110-4 to B110-7: the failures each check exists for, seeded, and the state maps
    post = (10000.0 * 10.0 + 1000.0 * 8.0) / 11000.0
    want4 = t_deal(1000.0, 10000.0, 10.0, 8.0)
    check(f"T_deal is what the old holders lose and the new ones gain at the price after the issue ({want4:.4f})",
          abs(want4 - 10000.0 * (10.0 - post)) < 1e-9 and abs(want4 - 1000.0 * (post - 8.0)) < 1e-9
          and t_deal(1000.0, 10000.0, 10.0, 10.0) == 0.0)
    tb = {"clean": transfer_breaches(["a", "b"], ["a"], ["b"], {"close on T": 5.0}, {"x": {"close on T": 2.0}, "y": {"close on T": 3.0}}),
          "twice": transfer_breaches(["a", "a"], ["a", "a"], [], {}, {}),
          "both": transfer_breaches(["a", "b"], ["a", "b"], ["b"], {}, {}),
          "neither": transfer_breaches(["a", "b"], ["a"], [], {}, {}),
          "empty": transfer_breaches(["a"], [], ["a"], {}, {}),
          "split": transfer_breaches(["a"], ["a"], [], {"close on T": 5.0}, {"x": {"close on T": 4.0}})}
    check(f"B110-4 names each breach of the table's shape: {tb}",
          tb["clean"] == [] and tb["twice"] == ["offerings twice in scope: ['a']"]
          and tb["both"][0] == "offerings in the table and named: ['b']"
          and tb["neither"] == ["the table and the named do not add up to the offerings in scope"]
          and tb["empty"] == ["the table is empty"] and len(tb["split"]) == 1 and tb["split"][0].startswith("close on T"))
    t_ok = dict(ok_o, groups=[grp("2021-08-23", 6, 1000)])
    nob = offer(7.0, code="600002", series=None)
    fs4 = {t_ok["id"]: floor_state(t_ok, flat)[0]}
    ss4 = {t_ok["id"]: shares_state(t_ok, flat)[0]}
    c4 = criterion_transfers([t_ok, nob], stub, fs4, ss4)
    check(f"B110-4 puts an offering's transfer in its year and its class and names the one with no bars: "
          f"{c4['payload']['by_class']} {c4['payload']['named']}",
          c4["passed"] is True and abs(c4["payload"]["by_year"][f"{BID_WAY} 2021"]["close on T"] - want4) < 1e-9
          and abs(c4["payload"]["by_class"]["2021 6 months 公募"]["close on T"] - want4) < 1e-9
          and c4["payload"]["named"] == {"no bars": [nob["id"]]})
    bare = dict(t_ok, groups=[dict(grp("2021-08-23", 6, 1000), holders=[])])
    c4_bare = criterion_transfers([bare], stub, fs4, {bare["id"]: shares_state(bare, flat)[0]})
    check(f"B110-4 fails when a split offering's groups carry no holder rows, so its transfer lands in no class: {c4_bare['payload']['breaches']}",
          c4_bare["passed"] is False)
    asset_text = "根据《重组管理办法》相关规定，上市公司发行股份的价格不得低于市场参考价的90%。本次发行股份购买资产的发行价格为9.20元/股。"
    matching_text = "本次非公开发行股份募集配套资金选择董事会决议公告日前20个交易日的上市公司股票交易均价为市场参考价，发行价格为16.80元/股。"
    both_text = "本次发行股份购买资产和发行股份募集配套资金的定价基准日为董事会决议公告日，发行价格不低于定价基准日前20个交易日股票交易均价的90%。"
    tk = {"asset": text_kind(asset_text), "matching first": text_kind(matching_text), "both": text_kind(both_text), "board": text_kind(board)}
    check(f"a 网下定价发行 text is read by the word that comes first: {tk}",
          tk == {"asset": "for assets", "matching first": "cash", "both": "both parts", "board": "cash"})

    def priced_offer(text, n, gross=8000.0, net=7900.0):
        return dict(offer(8.0, text, n=n), way=PRICED_WAY, id=f"600001:priced:{n}", gross=gross, net=net)

    p_cash, p_asset, p_both = priced_offer(board, 1001.0), priced_offer(asset_text, 1002.0, net=8000.0), priced_offer(both_text, 1003.0)
    p_even, p_none = priced_offer(board, 1004.0, net=8000.0), priced_offer(board, 1005.0, gross=None)
    ps = {k: priced_state(o) for k, o in (("cash", p_cash), ("asset", p_asset), ("both", p_both), ("even", p_even), ("none", p_none))}
    check(f"B110-4 priced states: {ps}", ps == {"cash": "cash", "asset": "for assets", "both": "both parts",
                                                "even": "cash by its text, net equal to gross",
                                                "none": "cash by its text, proceeds not printed"})
    c4p = criterion_transfers([t_ok, p_cash, p_asset, p_both, p_even, p_none], stub, fs4, ss4)
    named4 = c4p["payload"]["named"]
    row4 = c4p["payload"]["by_year"].get(f"{PRICED_WAY} 2021", {})
    check(f"B110-4 keeps a cash 网下定价发行 in the table and names the four it cannot read as cash: {sorted(named4)}",
          c4p["passed"] is True and row4.get("offerings") == 1
          and abs(row4.get("close on T", 0.0) - t_deal(1001.0, 10000.0, 10.0, 8.0)) < 1e-9
          and sorted(i for ids in named4.values() for i in ids) == sorted([p_asset["id"], p_both["id"], p_even["id"], p_none["id"]])
          and named4.get(priced_reason("for assets")) == [p_asset["id"]]
          and [s for s, r in c4p["payload"]["priced"]["mapping"].items() if r == "in the table"] == ["cash"]
          and sum(v["offerings"] for v in c4p["payload"]["priced"]["states"].values()) == 5
          and [r["offering"] for r in c4p["payload"]["priced"]["extremes_by_year"]["2021"]["lowest"]] == [p_cash["id"]])

    es = {"above": edge_state({"a": 0.1, "b": 0.2}), "within": edge_state({"a": -0.1, "b": 0.0}),
          "at the bound": edge_state({"a": 0.0, "b": 0.1}), "missing": edge_state({"a": None, "b": 0.1})}
    check(f"B110-5 states: {es}", es == {"above": "d above the bound under every volatility",
                                         "within": "d within the bound under every volatility",
                                         "at the bound": "the sign moves with the volatility",
                                         "missing": "a volatility is missing"})
    check("B110-5 maps a sign that moves with the volatility, and a missing volatility, to no verdict",
          EDGE_MAP == {"d above the bound under every volatility": True, "d within the bound under every volatility": False,
                       "the sign moves with the volatility": None, "a volatility is missing": None})
    check("one verdict from many: any True, else any False, else none",
          fold([None, True, False]) is True and fold([None, False]) is False and fold([None, None]) is None and fold([]) is None)
    rng5 = np.random.default_rng(5)
    days500 = [dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(500)]
    c5 = 10.0 * np.exp(np.cumsum(rng5.normal(0, 0.02, 500)))
    vol_s = finish_series({"ordinal": np.array([x.toordinal() for x in days500], dtype=np.int32),
                           "status": np.ones(500, dtype=np.int8), "open": c5, "high": c5 * 1.01, "low": c5 * 0.99,
                           "close": c5, "preclose": np.r_[10.0, c5[:-1]], "volume": np.full(500, 1000.0), "amount": c5 * 1000.0})

    def edge_offer(price, row, months=6):
        T = days500[row].isoformat()
        o = {"id": f"600003:{T}:{price}", "code": "600003", "name": "测试", "T": T, "era": "2020", "way": BID_WAY,
             "P": price, "n": 1000.0, "N": 10000.0, "listing": (days500[row] + dt.timedelta(days=10)).isoformat(),
             "lock_text": "0.5年", "principle": first_day, "groups": []}
        o.update(bar_readings(vol_s, T, price, FLOOR["2020"]))
        o["groups"] = [grp(P.add_months(days500[row], months).isoformat(), months, 1000, o["id"], code="600003")]
        return o

    stub5, through5 = Stub({"600003": vol_s}), days500[-1].isoformat()

    def run5(o):
        return criterion_edge([o], stub5, {o["id"]: "at T-k"}, {o["id"]: "equal"}, through5)

    e_far, e_near, e_short = (run5(edge_offer(round(float(c5[300]) * 0.5, 2), 300)),
                              run5(edge_offer(round(float(c5[300]) * 0.98, 2), 300)),
                              run5(edge_offer(round(float(c5[100]) * 0.5, 2), 100)))
    check(f"B110-5 passes on a discount far past the bound, fails on one within it, and gives no verdict without 250 "
          f"traded days before T: {e_far['passed']} {e_near['passed']} {e_short['passed']}",
          e_far["passed"] is True and e_near["passed"] is False and e_short["passed"] is None)
    cell = e_far["payload"]["above"][0]
    years5 = (P.add_months(days500[300], 6) - days500[300]).days / 365.25
    check(f"the bound runs over the calendar years from T to the unlock, under each volatility printed ({cell['years']:.6f} years)",
          abs(cell["years"] - years5) < 1e-12 and set(cell["sigma"]) == {f"{n} traded days before T" for n in SIGMA_SWEEP} | {"over the lock"}
          and all(cell["sigma"][k] is not None and abs(cell["bound"][k] - longstaff(cell["sigma"][k], years5)) < 1e-12 for k in cell["sigma"]))

    at_h, over_h = offer(10.2, n=1000.0), offer(10.21, n=1001.0)
    check(f"one tick over the day's high is above it and the high itself is not ({over_h['ticks_over_high']} and {at_h['ticks_over_high']} ticks)",
          high_state(over_h) == "price above the day's high" and high_state(at_h) == "price at or below the day's high"
          and high_state(nob) == "no price record on T")

    def run6(frame):
        return criterion_high(frame, stub, {o["id"]: "at T-k" for o in frame}, {o["id"]: "equal" for o in frame})["passed"]

    check("B110-6 passes on one offering over the high, fails with only one at it, and gives no verdict with no price record",
          run6([at_h, over_h]) is True and run6([at_h]) is False and run6([nob]) is None
          and HIGH_MAP == {"price above the day's high": True, "price at or below the day's high": False, "no price record on T": None})

    cov_frame = [t_ok, nob]
    rows7 = coverage_rows(cov_frame, {t_ok["id"]: "equal", nob["id"]: "fewer shares than issued"})
    whole, dropped, again = (criterion_coverage(cov_frame, rows7), criterion_coverage(cov_frame, rows7[:1]),
                             criterion_coverage(cov_frame, rows7 + rows7[:1]))
    thin = criterion_coverage(cov_frame, [dict(rows7[0], have=dict(list(rows7[0]["have"].items())[:-1])), rows7[1]])
    check(f"B110-7 passes on one full row per offering and fails on a missing row, a second row and a missing field: "
          f"{whole['passed']} {dropped['passed']} {again['passed']} {thin['passed']}",
          whole["passed"] is True and dropped["passed"] is False and again["passed"] is False and thin["passed"] is False
          and criterion_coverage([], [])["passed"] is False)
    check(f"the coverage counts print a zero where no offering lacks a field: {whole['payload']['counts']['price P']}",
          whole["payload"]["counts"]["price P"] == {f"{BID_WAY} present": 2, f"{BID_WAY} absent": 0})

    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--frame", action="store_true", help="print the frame's objects; writes nothing but the bars cache")
    ap.add_argument("--criteria", action="store_true", help="read B110-1 to B110-7 off the frame")
    ap.add_argument("--write", action="store_true", help="with --criteria: write results/b110_placements.json")
    ap.add_argument("--rebuild-bars", action="store_true", help="build the bars cache again")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.frame:
        return frame_report(args.rebuild_bars)
    if args.criteria:
        return criteria_report(args.write)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
