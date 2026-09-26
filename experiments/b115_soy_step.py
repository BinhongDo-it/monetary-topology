"""B115: the soybean tariff step of 2018, read as a term moved in place (Corollary 43.6).

Four series, from the files experiments/b115_soy_fetch.py put under data/b115/raw, each file
checked against its manifest by the reader in experiments/b115_soy_describe.py:

  Gulf       the Gulf - Louisiana soybean bid, weekly, US$ per bushel (AgTransport Grain Basis)
  Dalian     the DCE No. 2 soybean settle on the days a contract traded, yuan per tonne
  Paranagua  the CEPEA/ESALQ Paranagua soybean indicator, daily, US$ per 60 kg bag
  yuan       yuan per US dollar, daily (FRED DEXCHUS)

The step. On 2018-07-06 the additional tariff on US yellow soybeans (tariff line 12019010) went
from 0 to 25% over a 3% MFN rate, announced without a date on 2018-04-04 and with one on
2018-06-16. The term of the relation from the US export end to China moved by
Delta = ln(1.28 / 1.03).

The reading. Each relative level is averaged over two plateaus of weeks, one before and one
after, and the weeks between are printed as a path. Four settings of the plateaus are read, and a
state counts only when all four give it. Every move is set against the same move over window
pairs of the same shape, 2016 to 2020, whose span holds no dated soybean tariff document. The
floor is the larger of the quote grid and the median absolute placebo move.

Corollary 43.6 here. With only the term of e = (Gulf -> Dalian) moved, Dalian against the Gulf
moves by h_e Delta, and every potential moves by w_e Delta u, u the potential of a unit current
from the Gulf to Dalian. By Theorem 42 u lies between its values at the two ends, so the
tariff's part of Paranagua against the Gulf is at least 0 and at most h_e Delta, and its part of
Dalian against Paranagua is at least 0. The yuan moved in the same weeks, and a step of its own
moves every pair by at most its size s. With Dalian priced on the yuan side of the Gulf, and
Paranagua nearer China than the Gulf once the tariff binds, the yuan's step lowers both legs, so

  tariff's part of Dalian against the Gulf      in [Dalian at the market rate, at the pre-plateau rate]
  tariff's part of Paranagua against the Gulf   in [read, read + s]
  tariff's part of Dalian against Paranagua     in [at the market rate - s, at the pre-plateau rate]

and a state is read from an interval: its low end above the floor matches, its high end below
minus the floor does not, anything else is not read. The same intervals with no orientation
assumed, each end moved out by s, are printed.

    python experiments/b115_soy_step.py              # print, and write the record
    python experiments/b115_soy_step.py --selftest   # offline, planted faults
"""

from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import math
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import b115_soy_describe as rd  # noqa: E402  the reader that checks each file against its manifest

REPO = HERE.parent
RAW = REPO / "data" / "b115" / "raw"
OUT = REPO / "results" / "b115_soy_step.json"

MFN, ADDED = 0.03, 0.25
DELTA = math.log((1 + MFN + ADDED) / (1 + MFN))
KG_PER_BU = 27.2155        # a soybean bushel is 60 lb
KG_PER_BAG = 60.0          # the Paranagua indicator is quoted per 60 kg bag
GULF = "Gulf - Louisiana"
ASF_CONFIRMED = "2018-08-03"

#: dated documents that move the soybean term, announcements included
TERM_DATES = (
    ("2018-04-04", "Tariff Commission announcement [2018] No. 1: 25% on 106 lines incl. 12019010, date to be announced"),
    ("2018-06-16", "announcement [2018] No. 5: list one, 12019010 in it, from 2018-07-06"),
    ("2018-07-06", "list one takes effect"),
    ("2019-08-23", "announcement [2019] No. 4: 5% more on 12019010 from 2019-09-01 12:01"),
    ("2019-09-01", "the 5% takes effect"),
    ("2019-09-13", "purchases of US soybeans to be excluded from the additional tariffs"),
    ("2019-12-06", "exclusion of soybeans on applications by firms"),
    ("2020-02-06", "announcement [2020] No. 1: 5% becomes 2.5% from 2020-02-14 13:01"),
    ("2020-02-14", "the 2.5% takes effect"),
    ("2020-02-17", "announcement [2020] No. 2: market-based exclusion"),
    ("2020-03-02", "exclusion applications open"),
)

#: plateaus as (first Friday, weeks); every post plateau ends 2018-07-27, before ASF_CONFIRMED
SETTINGS = {
    "A": {"pre": ("2018-01-05", 13), "post": ("2018-07-06", 4)},
    "B": {"pre": ("2018-01-05", 13), "post": ("2018-06-22", 6)},
    "C": {"pre": ("2018-05-04", 6), "post": ("2018-07-06", 4)},
    "D": {"pre": ("2018-05-04", 6), "post": ("2018-06-22", 6)},
}
DEFAULT = "A"

#: against no tariff, late June through late November 2018: the Gulf export price about $0.74/bu
#: lower and the Brazilian price about $0.97/bu higher
KNOWN = {"gulf_usd_bu": -0.74, "brazil_usd_bu": 0.97, "first_friday": "2018-06-29", "last_friday": "2018-11-30",
         "source": "Adjemian, Smith and He (2021), Food Policy 105, 102152"}
ORDER = 10.0   # one order of magnitude either way

KEYS = ("m_PG", "m_DG_usd", "m_DG_fx0", "m_DP_usd", "m_DP_fx0", "d_yuan")
LABELS = {"m_PG": "Paranagua against the Gulf",
          "m_DG_usd": "Dalian against the Gulf, yuan at the market rate",
          "m_DG_fx0": "Dalian against the Gulf, yuan at the pre-plateau rate",
          "m_DP_usd": "Dalian against Paranagua, yuan at the market rate",
          "m_DP_fx0": "Dalian against Paranagua, yuan at the pre-plateau rate",
          "d_yuan": "log yuan per US dollar"}

MATCH, MISS, NOT_READ = "matches", "does not match", "not read"
VERDICT = {MATCH: True, MISS: False, NOT_READ: None}
R_LOW, R_HIGH = "the low end above its floor", "the high end below minus its floor"
R_WITHIN, R_NO_FLOOR = "within the floor", "floor not measured"
R_GAP, R_SPLIT = "a week of either plateau without a quote in a series", "the window settings do not give one state"
MAPPING = (
    ("B115-4", "tariff's part of Paranagua against the Gulf: " + R_LOW, MATCH),
    ("B115-4", "tariff's part of Paranagua against the Gulf: " + R_HIGH, MISS),
    ("B115-5", "tariff's part of Dalian against Paranagua: " + R_LOW, MATCH),
    ("B115-5", "tariff's part of Dalian against Paranagua: " + R_HIGH, MISS),
    ("any", R_WITHIN, NOT_READ),
    ("any", R_NO_FLOOR, NOT_READ),
    ("any", R_GAP, NOT_READ),
    ("any", R_SPLIT, NOT_READ),
)


# ---------------------------------------------------------------- dates and series

def day(s: str) -> date:
    return date.fromisoformat(s[:10])


def nearest_friday(d: date) -> date:
    """AgTransport dates a week by the day its report closed: a Friday, or a day next to it when a holiday moved it."""
    off = (4 - d.weekday()) % 7
    return d + timedelta(days=off - 7 if off > 3 else off)


def fridays(first: str, n: int) -> list[str]:
    f = day(first)
    if f.weekday() != 4:
        raise ValueError(f"{first} is not a Friday")
    return [(f + timedelta(days=7 * k)).isoformat() for k in range(n)]


def first_day(friday: str) -> str:
    """The Saturday that opens the week ending on this Friday."""
    return (day(friday) - timedelta(days=6)).isoformat()


class Daily:
    """Days in order with a running sum of one value per day, for sums and means over closed day ranges."""

    def __init__(self, pairs):
        items = sorted(pairs)
        for (a, _), (b, _) in zip(items, items[1:]):
            if a == b:
                raise ValueError(f"two values on {a}")
        self.days = [d for d, _ in items]
        self.cum = [0.0]
        for _, v in items:
            self.cum.append(self.cum[-1] + v)

    def total(self, lo: str, hi: str) -> tuple[float, int]:
        i, j = bisect.bisect_left(self.days, lo), bisect.bisect_right(self.days, hi)
        return self.cum[j] - self.cum[i], j - i

    def count(self, lo: str, hi: str) -> int:
        return self.total(lo, hi)[1]

    def mean(self, lo: str, hi: str) -> float | None:
        s, n = self.total(lo, hi)
        return s / n if n else None


# ---------------------------------------------------------------- reading the files

def parse_para(cells: list[list]) -> dict:
    head = next((i for i, r in enumerate(cells) if r and rd.cell_text(r[0]) == "Data"), None)
    if head is None or len(cells[head]) < 3 or "US$" not in rd.cell_text(cells[head][2]):
        raise RuntimeError("the Paranagua sheet has no 'Data' row with a US$ column third")
    out = {}
    for r in cells[head + 1:]:
        try:
            d = datetime.strptime(rd.cell_text(r[0]) if r else "", "%d/%m/%Y").date().isoformat()
        except ValueError:
            continue
        v = rd.cell_number(r[2]) if len(r) > 2 else None
        if v:
            if d in out:
                raise RuntimeError(f"two Paranagua rows on {d}")
            out[d] = v
    return out


def parse_fx(text: str) -> dict:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or len(rows[0]) < 2 or rows[0][1].strip() != "DEXCHUS":
        raise RuntimeError("the FRED file's second column is not DEXCHUS")
    return {r[0]: float(r[1]) for r in rows[1:] if r and r[1].strip() not in (".", "")}


def parse_dce(tables, name: str, book: dict) -> None:
    """book: contract -> day -> (volume, settle), every row, so that a row read twice is caught."""
    for label, header, rows in tables:
        ix = rd.column_index(header)
        missing = [k for k in ("contract", "date", "volume", "settle") if k not in ix]
        if missing:
            raise RuntimeError(f"{name} {label}: no column for {missing}")
        for r in rows:
            def get(k):
                return r[ix[k]] if ix[k] < len(r) else None
            c, d8 = rd.cell_text(get("contract")), rd.cell_text(get("date"))
            if not c and not d8:
                continue
            if not (c.startswith("b") and c[1:].isdigit() and len(d8) == 8 and d8.isdigit()):
                raise RuntimeError(f"{name} {label}: row {c!r} {d8!r} is not a No. 2 soybean contract on a date")
            per = book.setdefault(c, {})
            key = rd.iso(d8)
            if key in per:
                raise RuntimeError(f"{name}: {c} on {key} twice")
            per[key] = (rd.cell_number(get("volume")) or 0.0, rd.cell_number(get("settle")))


def load(raw: Path) -> tuple[dict, dict, dict, dict]:
    man = json.loads((raw / rd.MANIFEST_NAME).read_text(encoding="utf-8"))
    gulf = {}
    for k in sorted(k for k in man if k.startswith("agtransport/") and k.endswith(".json")):
        for r in json.loads(rd.load_checked(raw, k, man).decode("utf-8")):
            if r.get("market_name") != GULF:
                continue
            if r.get("commodity") not in (None, "Soybeans"):
                raise RuntimeError(f"a {GULF} row for {r.get('commodity')}")
            f = nearest_friday(rd.parse_week(r["date"])).isoformat()
            if f in gulf:
                raise RuntimeError(f"two {GULF} rows fall in the week ending {f}")
            gulf[f] = float(r["bid"])
    para = parse_para(rd.read_cepea(rd.load_checked(raw, "cepea/soja_paranagua_series.xls", man)))
    fx = parse_fx(rd.load_checked(raw, "fred/DEXCHUS.csv", man).decode("utf-8-sig"))
    book: dict = {}
    for k in sorted(m for m in man if m.startswith("dce/") and "no2_soybeans" in m):
        parse_dce(rd.dce_tables(rd.load_checked(raw, k, man), k), k, book)
    dce = {c: sorted((d, v, s) for d, (v, s) in per.items() if v > 0 and s) for c, per in book.items()}
    return gulf, para, fx, {c: rows for c, rows in dce.items() if rows}


def build(gulf: dict, para: dict, fx: dict, dce: dict) -> dict:
    """gulf: Friday -> US$/bu; para: day -> US$ per bag; fx: day -> yuan per US$;
    dce: contract -> [(day, volume, settle)] on the days it traded."""
    return {
        "gulf": dict(gulf),
        "para": Daily((d, math.log(v)) for d, v in para.items()),
        "para_level": Daily(para.items()),
        "fx": Daily((d, math.log(v)) for d, v in fx.items()),
        "cny": {c: Daily((d, math.log(s)) for d, _, s in rows) for c, rows in dce.items()},
        "usd": {c: Daily((d, math.log(s / fx[d])) for d, _, s in rows if d in fx) for c, rows in dce.items()},
        "vol": {c: Daily((d, v) for d, v, _ in rows) for c, rows in dce.items()},
    }


# ---------------------------------------------------------------- one window pair

def choose(S: dict, pre: tuple, post: tuple) -> str | None:
    """The contract traded in both plateaus, on days with a yuan rate, with the largest volume over the two."""
    best = None
    for c in sorted(S["usd"]):
        if S["usd"][c].count(*pre) == 0 or S["usd"][c].count(*post) == 0:
            continue
        v = S["vol"][c].total(*pre)[0] + S["vol"][c].total(*post)[0]
        if best is None or v > best[0]:
            best = (v, c)
    return best[1] if best else None


def pair(S: dict, pre_w: list[str], post_w: list[str]) -> dict:
    pre, post = (first_day(pre_w[0]), pre_w[-1]), (first_day(post_w[0]), post_w[-1])
    g0 = [math.log(S["gulf"][f]) for f in pre_w if f in S["gulf"]]
    g1 = [math.log(S["gulf"][f]) for f in post_w if f in S["gulf"]]
    out = {"pre": [pre_w[0], pre_w[-1]], "post": [post_w[0], post_w[-1]], "span": [pre[0], post[1]],
           "gulf_weeks": [len(g0), len(g1)]}
    p0, p1, x0, x1 = S["para"].mean(*pre), S["para"].mean(*post), S["fx"].mean(*pre), S["fx"].mean(*post)
    if not g0 or not g1 or None in (p0, p1, x0, x1):
        return out
    dG, dP = sum(g1) / len(g1) - sum(g0) / len(g0), p1 - p0
    out.update({"m_PG": dP - dG, "d_yuan": x1 - x0})
    c = choose(S, pre, post)
    out["contract"] = c
    if c is None:
        return out
    dC = S["cny"][c].mean(*post) - S["cny"][c].mean(*pre)
    dU = S["usd"][c].mean(*post) - S["usd"][c].mean(*pre)
    out.update({"m_DG_usd": dU - dG, "m_DG_fx0": dC - dG, "m_DP_usd": dU - dP, "m_DP_fx0": dC - dP})
    return out


def weekly_gaps(S: dict, weeks: list[str], contract: str | None) -> list[str]:
    out = []
    for f in weeks:
        lo = first_day(f)
        if f not in S["gulf"]:
            out.append(f"{f} Gulf")
        if S["para"].count(lo, f) == 0:
            out.append(f"{f} Paranagua")
        if S["fx"].count(lo, f) == 0:
            out.append(f"{f} yuan")
        if contract is None or S["cny"][contract].count(lo, f) == 0:
            out.append(f"{f} Dalian {contract}")
    return out


def tariff_part(o: dict) -> dict | None:
    """The intervals the tariff's part of each leg lies in, with the orientation named in the docstring and with none."""
    if any(o.get(k) is None for k in KEYS):
        return None
    s = abs(o["d_yuan"])
    return {"PG": [o["m_PG"], o["m_PG"] + s], "DP": [o["m_DP_usd"] - s, o["m_DP_fx0"]],
            "DG": [o["m_DG_usd"], o["m_DG_fx0"]],
            "PG_no_orientation": [o["m_PG"] - s, o["m_PG"] + s],
            "DP_no_orientation": [o["m_DP_usd"] - 2 * s, o["m_DP_usd"] + 2 * s],
            "DG_no_orientation": [o["m_DG_usd"] - s, o["m_DG_usd"] + s]}


def h_interval(o: dict) -> dict | None:
    if any(o.get(k) is None for k in KEYS):
        return None
    s = abs(o["d_yuan"])
    return {"low": max(o["m_PG"], o["m_DG_usd"]) / DELTA, "high": o["m_DG_fx0"] / DELTA,
            "low_no_orientation": (max(o["m_PG"], o["m_DG_usd"]) - s) / DELTA,
            "high_no_orientation": (o["m_DG_usd"] + s) / DELTA}


# ---------------------------------------------------------------- floors and states

def friday_grid(S: dict) -> list[str]:
    fs = sorted(S["gulf"])
    return fridays(fs[0], (day(fs[-1]) - day(fs[0])).days // 7 + 1)


def placebo(S: dict, grid: list[str], n_pre: int, gap: int, n_post: int, term_days: list[str]):
    """Every pair of the same shape on the grid whose span holds no dated step; a pair is kept when each
    plateau has a Gulf week and a day of each daily series."""
    rows, stepped, thin = [], 0, 0
    span = n_pre + gap + n_post
    for k in range(len(grid) - span + 1):
        pre_w, post_w = grid[k:k + n_pre], grid[k + n_pre + gap:k + span]
        lo, hi = first_day(pre_w[0]), post_w[-1]
        if any(lo <= t <= hi for t in term_days):
            stepped += 1
            continue
        p = pair(S, pre_w, post_w)
        if p.get("m_PG") is None:
            thin += 1
            continue
        rows.append(p)
    return rows, stepped, thin


def quote_step(values) -> float | None:
    vs = sorted({round(v, 6) for v in values})
    gaps = [g for g in (round(b - a, 6) for a, b in zip(vs, vs[1:])) if g > 0]
    return min(gaps) if gaps else None


def quote_grids(gulf: dict, para: dict, fx: dict, dce: dict, lo: str, hi: str) -> dict:
    series = {"gulf": list(gulf.values()),
              "para": [v for d, v in para.items() if lo <= d <= hi],
              "yuan": [v for d, v in fx.items() if lo <= d <= hi],
              "dalian": [s for rows in dce.values() for d, _, s in rows if lo <= d <= hi]}
    one = {}
    for k, vs in series.items():
        step = quote_step(vs) if vs else None
        med = statistics.median(vs) if vs else None
        one[k] = {"step": step, "median": med, "relative": step / med if step and med else 0.0}
    r = {k: v["relative"] for k, v in one.items()}
    moves = {"m_PG": r["para"] + r["gulf"], "m_DG_usd": r["dalian"] + r["yuan"] + r["gulf"],
             "m_DG_fx0": r["dalian"] + r["gulf"], "m_DP_usd": r["dalian"] + r["yuan"] + r["para"],
             "m_DP_fx0": r["dalian"] + r["para"], "d_yuan": r["yuan"]}
    return {"series": one, "moves": moves}


def independent(rows: list[dict]) -> int:
    n, last = 0, ""
    for r in sorted(rows, key=lambda r: r["pre"][0]):
        if r["pre"][0] > last:
            n += 1
            last = r["post"][1]
    return n


def floor_of(obs: float | None, rows: list[dict], key: str, grid: float) -> dict:
    have = [r for r in rows if r.get(key) is not None]
    if not have:
        return {"pairs": 0, "floor": None}
    xs = [abs(r[key]) for r in have]
    med = statistics.median(xs)
    return {"pairs": len(xs), "independent": independent(have), "median_abs": med, "max_abs": max(xs), "grid": grid,
            "floor": max(grid, med),
            "placebo_at_least_as_large": None if obs is None else sum(1 for x in xs if x >= abs(obs))}


def read_state(interval: list | None, floor_lo: float | None, floor_hi: float | None) -> tuple[str, str]:
    if interval is None:
        return NOT_READ, R_GAP
    if floor_lo is None or floor_hi is None:
        return NOT_READ, R_NO_FLOOR
    if interval[0] > floor_lo:
        return MATCH, R_LOW
    if interval[1] < -floor_hi:
        return MISS, R_HIGH
    return NOT_READ, R_WITHIN


def one_state(states: dict) -> tuple[str, str]:
    if len({s[0] for s in states.values()}) == 1:
        return tuple(states[DEFAULT] if DEFAULT in states else next(iter(states.values())))
    return NOT_READ, R_SPLIT


def read_setting(S: dict, grid: list[str], st: dict, term_days: list[str], move_grids: dict) -> dict:
    pre_w, post_w = fridays(*st["pre"]), fridays(*st["post"])
    gap = (day(post_w[0]) - day(pre_w[-1])).days // 7 - 1
    obs = pair(S, pre_w, post_w)
    gaps = weekly_gaps(S, pre_w + post_w, obs.get("contract"))
    rows, stepped, thin = placebo(S, grid, len(pre_w), gap, len(post_w), term_days)
    floors = {k: floor_of(obs.get(k), rows, k, move_grids[k]) for k in KEYS}
    part = None if gaps else tariff_part(obs)
    fl = {k: floors[k]["floor"] for k in KEYS}
    states = {
        "B115-4": read_state(part and part["PG"], fl["m_PG"], fl["m_PG"]),
        "B115-5": read_state(part and part["DP"], fl["m_DP_usd"], fl["m_DP_fx0"]),
        "B115-4 no orientation": read_state(part and part["PG_no_orientation"], fl["m_PG"], fl["m_PG"]),
        "B115-5 no orientation": read_state(part and part["DP_no_orientation"], fl["m_DP_usd"], fl["m_DP_usd"]),
    }
    return {"pre": [pre_w[0], pre_w[-1]], "post": [post_w[0], post_w[-1]], "gap_weeks": gap, "observed": obs,
            "coverage_gaps": gaps, "placebo": rows, "placebo_spanning_a_step": stepped,
            "placebo_without_a_quote": thin, "placebo_missing_a_gulf_week": sum(
                1 for r in rows if r["gulf_weeks"] != [len(pre_w), len(post_w)]),
            "floors": floors, "tariff_part": part, "states": {k: list(v) for k, v in states.items()},
            "h": h_interval(obs)}


# ---------------------------------------------------------------- the other objects

def known_answer(S: dict, pre_w: list[str]) -> dict:
    n = (day(KNOWN["last_friday"]) - day(KNOWN["first_friday"])).days // 7 + 1
    window = fridays(KNOWN["first_friday"], n)

    def spread(weeks):
        xs = []
        for f in weeks:
            p = S["para_level"].mean(first_day(f), f)
            if f in S["gulf"] and p is not None:
                xs.append(p * KG_PER_BU / KG_PER_BAG - S["gulf"][f])
        return (sum(xs) / len(xs) if xs else None), len(xs)

    s0, n0 = spread(pre_w)
    s1, n1 = spread(window)
    theirs = KNOWN["brazil_usd_bu"] - KNOWN["gulf_usd_bu"]
    ours = None if s0 is None or s1 is None else s1 - s0
    ratio = None if ours is None else ours / theirs
    return {"pre_weeks": n0, "window_weeks": n1, "spread_pre_usd_bu": s0, "spread_window_usd_bu": s1,
            "ours_usd_bu": ours, "theirs_usd_bu": theirs, "ratio": ratio,
            "passed": ratio is not None and 1 / ORDER < ratio < ORDER}


def path_2018(S: dict, contract: str | None, pre_w: list[str]) -> list[dict]:
    x_pre = S["fx"].mean(first_day(pre_w[0]), pre_w[-1])
    out = []
    for f in fridays("2017-12-29", 40):
        lo = first_day(f)
        g = S["gulf"].get(f)
        lg = None if g is None else math.log(g * 1000 / KG_PER_BU)
        p = S["para"].mean(lo, f)
        lp = None if p is None else p + math.log(1000 / KG_PER_BAG)
        x = S["fx"].mean(lo, f)
        dc = S["cny"][contract].mean(lo, f) if contract in S["cny"] else None
        du = S["usd"][contract].mean(lo, f) if contract in S["usd"] else None

        def diff(a, b):
            return None if a is None or b is None else a - b
        out.append({"friday": f, "gulf_usd_t": None if lg is None else math.exp(lg),
                    "paranagua_usd_t": None if lp is None else math.exp(lp),
                    "dalian_cny_t": None if dc is None else math.exp(dc), "yuan": None if x is None else math.exp(x),
                    "ln_P_over_G": diff(lp, lg), "ln_D_over_G_usd": diff(du, lg),
                    "ln_D_over_G_pre_rate": None if dc is None or lg is None or x_pre is None else dc - x_pre - lg,
                    "ln_D_over_P_usd": diff(du, lp)})
    return out


def volume_2018(S: dict) -> list[dict]:
    out = []
    for f in fridays("2018-01-05", 52):
        lo = first_day(f)
        vols = sorted(((S["vol"][c].total(lo, f)[0], c) for c in S["vol"]), key=lambda x: (-x[0], x[1]))
        vols = [(v, c) for v, c in vols if v > 0]
        out.append({"friday": f, "total": sum(v for v, _ in vols), "top": [[c, v] for v, c in vols[:3]]})
    return out


def run(gulf: dict, para: dict, fx: dict, dce: dict, settings: dict = SETTINGS, term_dates=TERM_DATES,
        move_grids: dict | None = None) -> dict:
    S = build(gulf, para, fx, dce)
    grid = friday_grid(S)
    term_days = [t for t, _ in term_dates]
    qg = quote_grids(gulf, para, fx, dce, first_day(grid[0]), grid[-1])
    mg = move_grids if move_grids is not None else qg["moves"]
    st = {k: read_setting(S, grid, v, term_days, mg) for k, v in settings.items()}
    d = st[DEFAULT] if DEFAULT in st else next(iter(st.values()))
    pre_default = fridays(*(settings[DEFAULT] if DEFAULT in settings else next(iter(settings.values())))["pre"])
    return {"settings": st, "term_days": term_days, "quote_grids": qg, "move_grids_used": mg,
            "friday_grid": [grid[0], grid[-1], len(grid)], "delta": DELTA,
            "known_answer": known_answer(S, pre_default),
            "path_2018": path_2018(S, d["observed"].get("contract"), pre_default),
            "dalian_volume_2018": volume_2018(S)}


# ---------------------------------------------------------------- criteria

def f4(x) -> str:
    return "n/a" if x is None else f"{x:+.4f}"


def criteria_for(o: dict) -> list[dict]:
    st = o["settings"]
    b1 = [f"{k}: {g}" for k, v in st.items() for g in v["coverage_gaps"]]
    b2 = []
    for k, v in st.items():
        for p in v["placebo"]:
            if any(p["span"][0] <= t <= p["span"][1] for t in o["term_days"]):
                b2.append(f"{k}: placebo {p['span'][0]}..{p['span'][1]} spans a dated step")
        for key in ("m_PG", "m_DG_fx0"):
            if not any(p.get(key) is not None for p in v["placebo"]):
                b2.append(f"{k}: no placebo pair reads {LABELS[key]}")
    b3 = [f"{k}: {key}" for k, v in st.items() for key in KEYS
          if v["observed"].get(key) is None or not math.isfinite(v["observed"][key]) or v["floors"][key].get("floor") is None]
    s4 = one_state({k: tuple(v["states"]["B115-4"]) for k, v in st.items()})
    s5 = one_state({k: tuple(v["states"]["B115-5"]) for k, v in st.items()})
    b6 = [k for k, v in st.items() if v["h"] is None or not all(math.isfinite(x) for x in v["h"].values())]
    ka = o["known_answer"]
    d = st[DEFAULT] if DEFAULT in st else next(iter(st.values()))

    def legs(key_pair):
        return "; ".join(f"{k}: [{f4((v['tariff_part'] or {}).get(key_pair, [None, None])[0])}, "
                         f"{f4((v['tariff_part'] or {}).get(key_pair, [None, None])[1])}] -> {v['states'][name_of[key_pair]][0]}"
                         for k, v in st.items())
    name_of = {"PG": "B115-4", "DP": "B115-5"}

    def floors_line(v, key):
        fl = v["floors"][key]
        return (f"{LABELS[key]} {f4(v['observed'].get(key))}, floor {f4(fl.get('floor'))} "
                f"(median of {fl.get('pairs')} placebo pairs, {fl.get('independent')} apart; "
                f"{fl.get('placebo_at_least_as_large')} as large)")
    return [
        {"name": "B115-1", "kind": "instrument", "passed": not b1,
         "statement": "every week of both plateaus, in every setting, has a Gulf bid, a Paranagua day, a yuan day "
                      "and a day the chosen No. 2 soybean contract traded",
         "detail": "; ".join(f"{k}: {v['observed'].get('contract')}, {len(v['coverage_gaps'])} gaps" for k, v in st.items())
                   + (": " + "; ".join(b1[:6]) if b1 else "")},
        {"name": "B115-2", "kind": "instrument", "passed": not b2,
         "statement": "no placebo window pair spans a dated soybean tariff document, and in every setting placebo pairs "
                      "read Paranagua against the Gulf and Dalian against the Gulf",
         "detail": "; ".join(f"{k}: {len(v['placebo'])} pairs kept, {v['placebo_spanning_a_step']} spanning a step, "
                             f"{v['placebo_without_a_quote']} without a quote" for k, v in st.items())
                   + (": " + "; ".join(b2[:6]) if b2 else "")},
        {"name": "B115-3", "kind": "own_reading", "passed": not b3,
         "statement": "the moves of Paranagua and of Dalian against the Gulf, of Dalian against Paranagua, and of the "
                      "yuan, with Dalian at the market rate and at the pre-plateau rate, are printed in every setting "
                      "against their placebo floors",
         "detail": f"setting {DEFAULT}: " + "; ".join(floors_line(d, key) for key in KEYS)
                   + (" | missing: " + "; ".join(b3[:6]) if b3 else "")},
        {"name": "B115-4", "kind": "own_reading", "passed": VERDICT[s4[0]],
         "statement": "the tariff moved Paranagua up against the Gulf: every potential moves by w_e Delta u, and u at "
                      "Paranagua lies between its values at the Gulf and at Dalian (Corollary 43.6, Theorem 42)",
         "detail": f"{s4[0]} ({s4[1]}); " + legs("PG")},
        {"name": "B115-5", "kind": "own_reading", "passed": VERDICT[s5[0]],
         "statement": "Paranagua moved no further against the Gulf than Dalian did, which is the tariff's part of "
                      "Dalian against Paranagua being at least 0 (Corollary 43.6, Theorem 42)",
         "detail": f"{s5[0]} ({s5[1]}); " + legs("DP")},
        {"name": "B115-6", "kind": "own_reading", "passed": not b6,
         "statement": "the share h_e the step passed to Dalian against the Gulf, as an interval over Delta = "
                      "ln(1.28/1.03): from below the larger of Paranagua against the Gulf and Dalian at the market "
                      "rate, from above Dalian at the pre-plateau rate; and with no orientation assumed, each end "
                      "moved out by the yuan's step",
         "detail": "; ".join(f"{k}: [{f4((v['h'] or {}).get('low'))}, {f4((v['h'] or {}).get('high'))}], "
                             f"no orientation [{f4((v['h'] or {}).get('low_no_orientation'))}, "
                             f"{f4((v['h'] or {}).get('high_no_orientation'))}]" for k, v in st.items())},
        {"name": "B115-7", "kind": "known_answer", "passed": bool(ka["passed"]),
         "statement": "Paranagua minus the Gulf in US$/bu, averaged over the weeks ending 2018-06-29 to 2018-11-30 "
                      "against the default pre plateau, has the sign of the $1.71/bu that Adjemian, Smith and He "
                      "(2021) estimate against no tariff and lies within one order of magnitude of it",
         "detail": f"{f4(ka['ours_usd_bu'])} over {ka['window_weeks']} weeks against {ka['pre_weeks']}, theirs "
                   f"{f4(ka['theirs_usd_bu'])}, ratio {f4(ka['ratio'])}"},
    ]


# ---------------------------------------------------------------- output

def public(x):
    if isinstance(x, float):
        return rd.fmt(x, 6) if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): public(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [public(v) for v in x]
    return x


def show(o: dict, criteria: list[dict]) -> None:
    print(f"Delta = ln(1.28/1.03) = {DELTA:.5f}; Friday grid {o['friday_grid'][0]}..{o['friday_grid'][1]} "
          f"({o['friday_grid'][2]} weeks)")
    for k, v in o["settings"].items():
        obs = v["observed"]
        print(f"\nsetting {k}: pre {v['pre'][0]}..{v['pre'][1]}, post {v['post'][0]}..{v['post'][1]}, "
              f"gap {v['gap_weeks']} weeks, contract {obs.get('contract')}")
        print(f"  placebo pairs {len(v['placebo'])} kept, {v['placebo_spanning_a_step']} spanning a step, "
              f"{v['placebo_without_a_quote']} without a quote, {v['placebo_missing_a_gulf_week']} short a Gulf week;"
              f" coverage gaps {v['coverage_gaps'] or 'none'}")
        for key in KEYS:
            fl = v["floors"][key]
            print(f"  {LABELS[key]:55s} {f4(obs.get(key))}  floor {f4(fl.get('floor'))}  max {f4(fl.get('max_abs'))}"
                  f"  pairs {fl.get('pairs')} ({fl.get('independent')} apart), {fl.get('placebo_at_least_as_large')} as large")
        tp = v["tariff_part"] or {}
        for leg in ("PG", "DP", "DG"):
            a, b = tp.get(leg, [None, None]), tp.get(leg + "_no_orientation", [None, None])
            print(f"  tariff's part {leg}: [{f4(a[0])}, {f4(a[1])}]  no orientation [{f4(b[0])}, {f4(b[1])}]")
        h = v["h"] or {}
        print(f"  h in [{f4(h.get('low'))}, {f4(h.get('high'))}], no orientation "
              f"[{f4(h.get('low_no_orientation'))}, {f4(h.get('high_no_orientation'))}]")
        print("  states: " + "; ".join(f"{n} {s[0]} ({s[1]})" for n, s in v["states"].items()))
    ka = o["known_answer"]
    print(f"\nknown answer: ours {f4(ka['ours_usd_bu'])} $/bu over {ka['window_weeks']} weeks, theirs "
          f"{f4(ka['theirs_usd_bu'])}, ratio {f4(ka['ratio'])}")
    print("\nmapping")
    for m in MAPPING:
        print(f"  {m[0]:7s} {m[1]:85s} -> {m[2]} -> {VERDICT[m[2]]}")
    print()
    for c in criteria:
        print(f"{c['name']} [{c['kind']}] {c['passed']}: {c['detail']}")


# ---------------------------------------------------------------- self-test

def synthetic(para_step=0.05, gulf_step=-0.08, fx_step=0.06, cny_step=0.02, start="2018-06-16", stop=None,
              drop_friday=None):
    gulf, para, fx, rows = {}, {}, {}, []
    d = date(2016, 1, 2)
    while d <= date(2020, 12, 31):
        s = d.isoformat()
        on = start <= s and (stop is None or s < stop)
        if d.weekday() < 5:
            para[s] = 23.0 * math.exp(para_step if on else 0.0)
            fx[s] = 6.3 * math.exp(fx_step if on else 0.0)
            rows.append((s, 10.0, 3400.0 * math.exp(cny_step if on else 0.0)))
        if d.weekday() == 4 and s != drop_friday:
            gulf[s] = 10.0 * math.exp(gulf_step if on else 0.0)
        d += timedelta(days=1)
    return gulf, para, fx, {"b9999": rows}


def selftest() -> int:
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    def close(a, b, tol=1e-9):
        return a is not None and b is not None and abs(a - b) <= tol

    zero = {k: 1e-9 for k in KEYS}   # a quote grid is never zero; exact worlds leave rounding at 1e-17
    expect(abs(DELTA - 0.21730) < 5e-6, "Delta is not ln(1.28/1.03)")
    for got, want in (("2018-03-29", "2018-03-30"), ("2017-10-21", "2017-10-20"), ("2016-11-23", "2016-11-25"),
                      ("2018-03-27", "2018-03-30"), ("2018-04-02", "2018-03-30"), ("2018-03-30", "2018-03-30")):
        expect(nearest_friday(day(got)).isoformat() == want, f"{got} is not put in the week ending {want}")
    expect(first_day("2018-07-06") == "2018-06-30", "a week does not open on the Saturday")
    expect(quote_step([9.44, 9.45, 9.47, 9.45]) == 0.01, "the quote step is misread")
    try:
        Daily([("2018-01-02", 1.0), ("2018-01-02", 2.0)])
        expect(False, "two values on one day pass")
    except ValueError:
        pass
    dd = Daily([("2018-01-02", 1.0), ("2018-01-03", 3.0), ("2018-01-05", 5.0)])
    expect(dd.mean("2018-01-03", "2018-01-05") == 4.0 and dd.count("2018-01-04", "2018-01-04") == 0,
           "a mean over a closed day range is misread")

    fxd = {"2018-01-02": 6.3, "2018-01-03": 6.3, "2018-03-01": 6.3, "2018-03-02": 6.3}
    dce = {"b1": [("2018-01-02", 50.0, 3000.0)],
           "b2": [("2018-01-03", 5.0, 3000.0), ("2018-03-01", 5.0, 3100.0)],
           "b3": [("2018-01-03", 5.0, 3000.0), ("2018-03-02", 5.0, 3100.0)],
           "b4": [("2018-01-04", 90.0, 3000.0), ("2018-03-01", 90.0, 3100.0)]}
    Sx = build({}, {}, fxd, dce)
    pre, post = ("2018-01-01", "2018-01-31"), ("2018-02-25", "2018-03-31")
    expect(choose(Sx, pre, post) == "b2", "a tie is not broken by the contract name, or a one-plateau contract is chosen")
    expect(Sx["usd"]["b4"].count("2018-01-01", "2018-03-31") == 1, "a traded day without a yuan rate is read in dollars")
    dce["b3"] = [("2018-01-03", 9.0, 3000.0), ("2018-03-02", 5.0, 3100.0)]
    expect(choose(build({}, {}, fxd, dce), pre, post) == "b3", "the larger volume over both plateaus is not chosen")

    rows = [{"m_PG": 0.1, "pre": ["2016-01-08", "2016-01-15"], "post": ["2016-02-05", "2016-02-12"]},
            {"m_PG": -0.2, "pre": ["2016-01-15", "2016-01-22"], "post": ["2016-02-12", "2016-02-19"]},
            {"m_PG": 0.3, "pre": ["2016-03-04", "2016-03-11"], "post": ["2016-03-25", "2016-04-01"]},
            {"m_PG": 0.05, "pre": ["2016-04-01", "2016-04-08"], "post": ["2016-04-29", "2016-05-06"]}]
    fl = floor_of(0.25, rows, "m_PG", 0.5)
    expect(close(fl["median_abs"], 0.15) and close(fl["max_abs"], 0.3) and fl["floor"] == 0.5
           and fl["placebo_at_least_as_large"] == 1, "the floor is not the larger of the grid and the median placebo move")
    expect(floor_of(0.25, rows, "m_PG", 0.0)["floor"] == fl["median_abs"], "the median placebo move is not the floor")
    expect(independent(rows) == 2, "overlapping placebo pairs are counted as apart")
    expect(read_state([0.2, 0.3], 0.2, 0.2) == (NOT_READ, R_WITHIN), "a low end equal to the floor is read")
    expect(read_state([-0.5, -0.2], 0.2, 0.2) == (NOT_READ, R_WITHIN), "a high end equal to minus the floor is read")
    expect(read_state([-0.5, -0.21], 0.2, 0.2)[0] == MISS and read_state([0.21, 0.5], 0.2, 0.2)[0] == MATCH,
           "an interval clear of the floor is not read")
    expect(read_state([-0.5, 0.5], None, 0.2) == (NOT_READ, R_NO_FLOOR) and read_state(None, 0.1, 0.1) == (NOT_READ, R_GAP),
           "a missing floor or a missing interval is read")
    expect(one_state({"A": (MATCH, R_LOW), "B": (MATCH, R_LOW)}) == (MATCH, R_LOW)
           and one_state({"A": (MATCH, R_LOW), "B": (NOT_READ, R_WITHIN)}) == (NOT_READ, R_SPLIT),
           "settings that disagree give a state")
    for group, how, state in MAPPING:
        if group == "any":
            expect(VERDICT[state] is None, f"the not-read row '{how}' points at a verdict")
        else:
            expect(VERDICT[state] in (True, False), f"the row '{group} {how}' gives no verdict")
    produced = {R_WITHIN, R_NO_FLOOR, R_GAP, R_SPLIT}
    expect({m[1] for m in MAPPING if m[0] == "any"} == produced, "a not-read reason in the mapping is never produced")
    h = h_interval({"m_PG": 0.13, "m_DG_usd": 0.04, "m_DG_fx0": 0.10, "m_DP_usd": -0.09, "m_DP_fx0": -0.03, "d_yuan": 0.06})
    expect(close(h["low"], 0.13 / DELTA) and close(h["high"], 0.10 / DELTA) and close(h["low_no_orientation"], 0.07 / DELTA)
           and close(h["high_no_orientation"], 0.10 / DELTA), "the interval for h is misread")

    try:
        parse_para([["Data", "À vista R$", "À vista R$ 2"], ["04/01/2016", 1.0, 1.0]])
        expect(False, "a Paranagua sheet without a US$ column is read")
    except RuntimeError:
        pass
    try:
        parse_fx("observation_date,DEXJPUS\n2016-01-04,120.0\n")
        expect(False, "a FRED file for another rate is read")
    except RuntimeError:
        pass
    try:
        parse_dce([("t", ["合约", "日期", "成交量", "结算价"], [["m1809", "20180702", "1", "3000"]])], "x", {})
        expect(False, "a meal contract is read as No. 2 soybeans")
    except RuntimeError:
        pass
    book = {}
    parse_dce([("t", ["合约", "日期", "成交量", "结算价"], [["b1809", "20180702", "1", "3000"], ["", "", "", ""]])], "x", book)
    try:
        parse_dce([("u", ["合约", "日期", "成交量", "结算价"], [["b1809", "20180702", "0", "3001"]])], "y", book)
        expect(False, "a contract-day read twice passes")
    except RuntimeError:
        pass

    # the whole reading on a world with exact steps on 2018-06-16 and no noise
    base = run(*synthetic(), move_grids=zero)
    for k, v in base["settings"].items():
        o = v["observed"]
        expect(close(o.get("m_PG"), 0.13) and close(o.get("m_DG_usd"), 0.04) and close(o.get("m_DG_fx0"), 0.10)
               and close(o.get("m_DP_usd"), -0.09) and close(o.get("m_DP_fx0"), -0.03) and close(o.get("d_yuan"), 0.06),
               f"setting {k}: the moves of an exact step are misread")
        expect(v["placebo"] and all(abs(p[key]) < 1e-9 for p in v["placebo"] for key in KEYS if p.get(key) is not None),
               f"setting {k}: a placebo pair on flat series moves, or none is kept")
        expect(not v["coverage_gaps"], f"setting {k}: a full world shows a coverage gap")
    c = {x["name"]: x["passed"] for x in criteria_for(base)}
    expect(c == {"B115-1": True, "B115-2": True, "B115-3": True, "B115-4": True, "B115-5": False, "B115-6": True,
                 "B115-7": True}, f"the criteria of the exact world are misread: {c}")

    tp = base["settings"]["A"]["tariff_part"]
    want_tp = {"PG": [0.13, 0.19], "DP": [-0.15, -0.03], "DG": [0.04, 0.10], "PG_no_orientation": [0.07, 0.19],
               "DP_no_orientation": [-0.21, 0.03], "DG_no_orientation": [-0.02, 0.10]}
    expect(tp is not None and all(close(tp[k][i], want_tp[k][i]) for k in want_tp for i in (0, 1)),
           "the intervals for the tariff's part are misread")
    expect({k: v["gap_weeks"] for k, v in base["settings"].items()} == {"A": 13, "B": 11, "C": 3, "D": 1},
           "the weeks between the plateaus are miscounted")
    per_bu = KG_PER_BU / KG_PER_BAG
    want = (23.0 * math.exp(0.05) * per_bu - 10.0 * math.exp(-0.08)) - (23.0 * per_bu - 10.0)
    expect(close(base["known_answer"]["ours_usd_bu"], want), "the spread in US$/bu is misread")
    c = {x["name"]: x["passed"] for x in criteria_for(run(*synthetic(para_step=-0.03, gulf_step=0.0), move_grids=zero))}
    expect(c["B115-4"] is None, "Paranagua a little down while the yuan's step could cover it gives a verdict")
    g, pa, x, dc = synthetic()
    dc = {"b9999": [r for r in dc["b9999"] if not ("2018-02-24" <= r[0] <= "2018-03-02")]}
    c = {x_["name"]: x_["passed"] for x_ in criteria_for(run(g, pa, x, dc, move_grids=zero))}
    expect(c["B115-1"] is False, "a plateau week in which Dalian did not trade passes")
    c = {x["name"]: x["passed"] for x in criteria_for(run(*synthetic(cny_step=0.25), move_grids=zero))}
    expect(c["B115-5"] is True, "Dalian clear above Paranagua is not read as matching")
    c = {x["name"]: x["passed"] for x in criteria_for(run(*synthetic(cny_step=0.08), move_grids=zero))}
    expect(c["B115-5"] is None, "an interval that straddles zero gives a verdict")
    c = {x["name"]: x["passed"] for x in criteria_for(run(*synthetic(para_step=-0.3, gulf_step=0.0), move_grids=zero))}
    expect(c["B115-4"] is False and c["B115-7"] is False, "Paranagua falling against the Gulf is read as matching")
    c = {x["name"]: x["passed"] for x in criteria_for(run(*synthetic(para_step=3.0), move_grids=zero))}
    expect(c["B115-7"] is False, "a spread two orders of magnitude off the known answer passes")
    split = run(*synthetic(para_step=0.05, gulf_step=0.0, fx_step=0.0, cny_step=0.0, stop="2018-07-02"), move_grids=zero)
    got = {k: v["states"]["B115-4"][0] for k, v in split["settings"].items()}
    expect(got == {"A": NOT_READ, "B": MATCH, "C": NOT_READ, "D": MATCH}, f"the settings are not read one by one: {got}")
    expect({x["name"]: x["passed"] for x in criteria_for(split)}["B115-4"] is None, "settings that disagree give a verdict")
    c = {x["name"]: x["passed"] for x in criteria_for(run(*synthetic(drop_friday="2018-02-02"), move_grids=zero))}
    expect(c["B115-1"] is False and c["B115-4"] is None, "a plateau week without a Gulf bid passes")

    doctored = json.loads(json.dumps(base))
    doctored["settings"]["C"]["placebo"].append(dict(doctored["settings"]["C"]["placebo"][0], span=["2019-08-01", "2019-09-30"]))
    expect({x["name"]: x["passed"] for x in criteria_for(doctored)}["B115-2"] is False, "a placebo pair across a dated step passes")
    doctored = json.loads(json.dumps(base))
    for p in doctored["settings"]["B"]["placebo"]:
        p.pop("m_DG_fx0", None)
    expect({x["name"]: x["passed"] for x in criteria_for(doctored)}["B115-2"] is False, "a setting with no placebo for Dalian passes")
    doctored = json.loads(json.dumps(base))
    doctored["settings"]["C"]["observed"]["m_DG_fx0"] = None
    expect({x["name"]: x["passed"] for x in criteria_for(doctored)}["B115-3"] is False, "a missing move passes as printed")
    doctored = json.loads(json.dumps(base))
    doctored["settings"]["B"]["h"] = None
    expect({x["name"]: x["passed"] for x in criteria_for(doctored)}["B115-6"] is False, "a missing interval for h passes")

    for what in fails:
        print(f"SELFTEST FAIL  {what}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    o = run(*load(RAW))
    criteria = criteria_for(o)
    show(o, criteria)
    record = {
        "stage": "B115",
        "config": {"raw": "data/b115/raw", "manifest": rd.MANIFEST_NAME, "mfn": MFN, "additional": ADDED,
                   "delta": DELTA, "kg_per_bu": KG_PER_BU, "kg_per_bag": KG_PER_BAG, "settings": SETTINGS,
                   "default_setting": DEFAULT, "term_dates": TERM_DATES, "asf_confirmed": ASF_CONFIRMED,
                   "known_answer": KNOWN, "order_of_magnitude": ORDER,
                   "floor": "the larger of the quote grid and the median absolute move over placebo window pairs"},
        "mapping": MAPPING,
        "criteria": criteria,
        "objects": o,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(public(record), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nrecord {OUT.relative_to(REPO)}")
    return 0 if all(c["passed"] is not False for c in criteria if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    raise SystemExit(main())
