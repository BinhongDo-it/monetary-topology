"""B140: the reign-title mix of excavated coins records when an edge was open.

A hoard is a sample of the coin stock in circulation at the moment it was sealed. Coins reach a
place only while the edge to their issuer is open, so the mix of issues in a hoard is a time stamp
of that edge. After 1127 the Song-Jin edge was cut from both sides (the Song ban on copper coin
leaving its territory and the iron-coin zone in Huainan, the Jin death penalty for carrying coin
out), while the Southern Song kept casting. So in Jin territory the Southern Song share of a hoard
should fall below the share in a Southern Song hoard of the same date.

**The quantities.** Hoard ``h``, counts per coin type ``N_h(v)``, each type mapped to an issuer and
a first-cast year.

    S_h = Southern Song coins / Northern Song coins
    Q_h(c) = Southern Song coins cast after the cut c / Southern Song coins cast before it
    rho = median_h S_h (destination) / median_h S_h (Southern Song territory), same window
    rho_Q likewise with Q_h

**Dating.** ``T_h`` is a lower bound on burial: the latest first-cast year among the coins present.
In Jin and Xixia territory the latest Southern Song coin cannot be used for it, because the cut is
exactly what keeps late Southern Song coin out; dating by it pins every Jin hoard at 1178 and empties
the window by construction. So a Jin or Xixia hoard is dated by its latest coin of an issuer the cut
does not touch (Jin: Zhenglong 1158, Dading 1178, Taihe 1204, later issues from 1212; Xixia:
Tianqing 1194, Huangjian 1210, Guangding 1211). A Southern Song hoard is dated by its latest coin.
The main window is ``T_h >= 1204``; the second reading is ``1160 <= T_h <= 1189``, read against the
two Song steps of 1166 and 1179 as a dose.

**Back-mark years.** From Chunxi 7 (1180) the reverse carries the casting year, so Chunxi coins
split at the stable Song cut of 1179-01-26: a Chunxi coin without a year mark was cast 1174-1179.

Block one (``--paper``) checks all of this on synthetic hoards with seeded faults, and maps every
coin label that appears in the transcribed tables. It writes nothing.

Run from the repository root with the project's virtual environment:

    python experiments/b140_hoard_vintage.py --paper
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 140
TOL = 1e-12
CUT_STABLE = 1179  # 1179-01-26; a coin cast from 1180 on is after it
CUT_EARLY = 1166   # 1166-08-27, two Huai on iron coin; reopened 1167, closed again by 1173
WINDOW_MAIN = (1204, None)
WINDOW_DOSE = (1160, 1189)
BOOT_N = 2000

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "b140"

FAULTS = ("drops_only", "presence_without_power", "single_coin_fails", "dading_as_song", "date_all_issuers", "window_by_discovery", "coin_bootstrap",
          "chunxi_unmarked_as_post", "rho_by_pooling", "type_basis_takes_chunxi", "count_single_type_step",
          "ignore_placebo", "steps_as_units", "one_reference", "common_takes_every_place", "war_end_year_out")

# --------------------------------------------------------------------------
# the coin table: reign key -> list of (issuer, first cast year, last cast year)

NS, SS, JIN, LIAO, XIA, TANG, WUDAI, QI, PRE, KOREA = (
    "北宋", "南宋", "金", "辽", "西夏", "唐", "五代十国", "伪齐", "先唐", "高丽")

COINS: dict[str, list[tuple[str, int, int]]] = {}


def _add(issuer, rows):
    for key, a, b in rows:
        COINS.setdefault(key, []).append((issuer, a, b))


_add(NS, [("宋元", 960, 975), ("太平", 976, 983), ("淳化", 990, 994), ("至道", 995, 997),
          ("咸平", 998, 1003), ("景德", 1004, 1007), ("祥符", 1008, 1016), ("天禧", 1017, 1021),
          ("天圣", 1023, 1031), ("明道", 1032, 1033), ("景祐", 1034, 1037), ("皇宋", 1039, 1053),
          ("康定", 1040, 1040), ("庆历", 1041, 1048), ("至和", 1054, 1055), ("嘉祐", 1056, 1063),
          ("治平", 1064, 1067), ("熙宁", 1068, 1077), ("元丰", 1078, 1085), ("元祐", 1086, 1093),
          ("绍圣", 1094, 1097), ("元符", 1098, 1100), ("圣宋", 1101, 1101), ("崇宁", 1102, 1106),
          ("大观", 1107, 1110), ("政和", 1111, 1117), ("重和", 1118, 1118), ("宣和", 1119, 1125),
          ("靖康", 1126, 1126)])
_add(SS, [("建炎", 1127, 1130), ("绍兴", 1131, 1162), ("隆兴", 1163, 1164), ("乾道", 1165, 1173),
          ("淳熙", 1174, 1189), ("绍熙", 1190, 1194), ("庆元", 1195, 1200), ("嘉泰", 1201, 1204),
          ("开禧", 1205, 1207), ("嘉定", 1208, 1224), ("宝庆", 1225, 1227), ("大宋", 1225, 1227),
          ("绍定", 1228, 1233), ("端平", 1234, 1236), ("嘉熙", 1237, 1240), ("淳祐", 1241, 1252),
          ("皇宋", 1253, 1258), ("开庆", 1259, 1259), ("景定", 1260, 1264), ("咸淳", 1265, 1274)])
_add(JIN, [("正隆", 1158, 1160), ("大定", 1178, 1189), ("泰和", 1204, 1208), ("崇庆", 1212, 1213),
           ("至宁", 1213, 1213), ("贞祐", 1213, 1216)])
_add(QI, [("阜昌", 1130, 1137)])
_add(LIAO, [("统和", 983, 1011), ("重熙", 1032, 1054), ("清宁", 1055, 1064), ("咸雍", 1065, 1074),
            ("大康", 1075, 1084), ("大安", 1085, 1094), ("寿昌", 1095, 1100), ("乾统", 1101, 1110),
            ("天庆", 1111, 1120)])
_add(XIA, [("大安", 1075, 1085), ("天盛", 1149, 1169), ("乾祐", 1170, 1193), ("天庆", 1194, 1205),
           ("皇建", 1210, 1210), ("光定", 1211, 1222)])
_add(TANG, [("开元", 621, 907), ("乾元", 758, 759), ("会昌开元", 841, 846), ("大历", 766, 779)])
_add(WUDAI, [("通正", 916, 916), ("天汉", 917, 917), ("光天", 918, 918), ("乾德", 919, 924),
             ("咸康", 925, 925), ("天福", 936, 943), ("天福镇宝", 944, 944), ("广政", 938, 965),
             ("汉元", 948, 950), ("周元", 955, 959), ("唐国", 959, 975), ("大唐", 959, 975),
             ("南唐开元", 959, 975), ("五代开元", 907, 960)])
_add(PRE, [("半两", -175, -118), ("四铢半两", -175, -118), ("一化", -300, -222),
           ("五铢", -118, 621), ("前汉五铢", -118, 8), ("汉五铢", -118, 8), ("后汉五铢", 40, 220),
           ("大泉五十", 7, 14), ("货泉", 14, 40), ("西魏五铢", 540, 556), ("永安五铢", 529, 534),
           ("常平五铢", 553, 577), ("隋五铢", 581, 618), ("南北五铢", 420, 589)])
_add(KOREA, [("东国", 1097, 1105), ("海东", 1102, 1105)])

MISGROUPED: set[str] = set()

# single coins whose first cast differs from the reign's first year
COIN_YEAR = {"熙宁重宝": 1071}  # Miyake 2004 table 1

CHAR = str.maketrans({
    "寳": "宝", "寶": "宝", "豊": "丰", "豐": "丰", "聖": "圣", "歴": "历", "暦": "历", "曆": "历",
    "歷": "历", "慶": "庆", "寧": "宁", "徳": "德", "乹": "乾", "観": "观", "觀": "观", "紹": "绍",
    "興": "兴", "熈": "熙", "開": "开", "國": "国", "貨": "货", "銖": "铢", "両": "两", "兩": "两",
    "漢": "汉", "広": "广", "廣": "广", "鎮": "镇", "統": "统", "壽": "寿", "應": "应", "後": "后",
    "東": "东", "海": "海", "禎": "祯", "黄": "黄", "隆": "隆", "嘉": "嘉", "寿": "寿", "遼": "辽",
    "魏": "魏", "會": "会", "會": "会", "昌": "昌", "唐": "唐", "國": "国", "錢": "钱", "銭": "钱",
    "通": "通", "當": "当", "當": "当", "權": "权", "鐵": "铁", "無": "无", "號": "号", "號": "号",
})

HINT = {  # issuer as printed in a transcription -> issuers it allows
    "唐以前": {PRE}, "唐～五代": {TANG, WUDAI}, "北宋": {NS}, "南宋": {SS}, "金": {JIN, QI},
    "遼": {LIAO}, "辽": {LIAO}, "西夏": {XIA}, "その他": {KOREA}, "唐": {TANG},
    "西漢": {PRE}, "新莽": {PRE}, "後周": {WUDAI}, "前蜀": {WUDAI}, "南唐": {WUDAI},
}


def norm(label: str) -> str:
    s = unicodedata.normalize("NFKC", label).translate(CHAR)
    for junk in (" ", "　", "(", ")", "（", "）"):
        s = s.replace(junk, "")
    if s.startswith("开元") and "南唐" in s:
        s = "南唐" + s.replace("南唐", "")
    return s


def hint_set(printed_issuer: str | None):
    if not printed_issuer:
        return None
    if printed_issuer in HINT:
        return HINT[printed_issuer]
    if printed_issuer.startswith("五代十国"):
        return {WUDAI}
    if printed_issuer.startswith("其他"):
        return {PRE}
    return None


def reign_key(s: str) -> str | None:
    best = None
    for key in COINS:
        if s.startswith(key) and (best is None or len(key) > len(best)):
            best = key
    if best is None and s.endswith("五铢"):
        best = "五铢"
    return best


def map_coin(label: str, printed_issuer: str | None = None, fault=None):
    """Return (issuer, first cast year, last cast year) or (None, reason)."""
    s = norm(label)
    key = reign_key(s)
    if key is None:
        return None, f"no reign key in {s!r}"
    cands = COINS[key]
    allowed = hint_set(printed_issuer)
    if allowed is not None:
        cands = [c for c in cands if c[0] in allowed]
    if not cands and len(COINS[key]) == 1:
        cands = COINS[key]  # the table's group disagrees with the only issuer of this reign
        MISGROUPED.add(f"{label} [{printed_issuer}] -> {cands[0][0]}")
    if len(cands) != 1:
        return None, f"{s!r}: {len(cands)} candidates for key {key}" + (
            f" under {printed_issuer}" if printed_issuer else "")
    issuer, a, b = cands[0]
    if fault == "dading_as_song" and key == "大定":
        issuer = SS
    for coin, year in COIN_YEAR.items():
        if s.startswith(coin):
            a = year
    return (issuer, a, b), None


# --------------------------------------------------------------------------
# the quantities


def ss_side(issuer, a, b, back_year, cut, fault=None):
    """'pre', 'post' or 'straddle' for one Southern Song coin against the cut year."""
    if back_year is not None:
        return "post" if back_year > cut else "pre"
    if b <= cut:
        return "pre"
    if a > cut:
        return "post"
    if a == 1174 and cut == CUT_STABLE:  # Chunxi without a year mark: cast 1174-1179
        return "post" if fault == "chunxi_unmarked_as_post" else "pre"
    return "straddle"


def hoard_numbers(rows, place, cut=CUT_STABLE, fault=None) -> dict:
    """rows: dicts with label, count, optional issuer (as printed) and back_year."""
    ns = ss = pre = post = strad = 0.0
    t_all = t_free = None
    unmapped = []
    for r in rows:
        m, why = map_coin(r["label"], r.get("issuer"), fault)
        if m is None:
            unmapped.append(why)
            continue
        issuer, a, b = m
        n = r["count"]
        if n <= 0:
            continue
        t_all = a if t_all is None else max(t_all, a)
        if issuer != SS:
            t_free = a if t_free is None else max(t_free, a)
        if issuer == NS:
            ns += n
        elif issuer == SS:
            ss += n
            side = ss_side(issuer, a, b, r.get("back_year"), cut, fault)
            pre += n if side == "pre" else 0
            post += n if side == "post" else 0
            strad += n if side == "straddle" else 0
    censored = place in ("jin", "xia")
    t_h = t_all if (fault == "date_all_issuers" or not censored) else t_free
    return {"S": ss / ns if ns else float("nan"), "Q": post / pre if pre else float("nan"),
            "NS": ns, "SS": ss, "pre": pre, "post": post, "straddle": strad,
            "T_h": t_h, "T_all": t_all, "unmapped": unmapped}


def in_window(t, window):
    lo, hi = window
    return t is not None and t >= lo and (hi is None or t <= hi)


def rho(hoards, window, key="S", fault=None):
    """hoards: list of (place, numbers dict, discovery year)."""
    def pick(place):
        out = []
        for p, h, found in hoards:
            t = found if fault == "window_by_discovery" else h["T_h"]
            if p == place and in_window(t, window):
                out.append(h)
        return out
    far, home = pick("jin"), pick("song")
    if not far or not home:
        return float("nan"), len(far), len(home)
    if fault == "rho_by_pooling":
        num = sum(h["SS"] for h in far) / sum(h["NS"] for h in far)
        den = sum(h["SS"] for h in home) / sum(h["NS"] for h in home)
        return num / den, len(far), len(home)
    return (np.median([h[key] for h in far]) / np.median([h[key] for h in home]),
            len(far), len(home))


def bootstrap_upper(far_rows, home_rows, seed, n=BOOT_N, fault=None):
    """One-sided: the share of resampled rho at or above 1, and the 95th percentile.

    The unit is the hoard. far_rows/home_rows: lists of per-hoard (NS, SS) arrays of coins by type.
    """
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for i in range(n):
        if fault == "coin_bootstrap":
            f = [rng.multinomial(int(c.sum()), c / c.sum()) for c in far_rows]
            h = [rng.multinomial(int(c.sum()), c / c.sum()) for c in home_rows]
        else:
            f = [far_rows[j] for j in rng.integers(0, len(far_rows), len(far_rows))]
            h = [home_rows[j] for j in rng.integers(0, len(home_rows), len(home_rows))]
        sf = np.median([c[1] / c[0] for c in f])
        sh = np.median([c[1] / c[0] for c in h])
        out[i] = sf / sh
    return float(np.mean(out >= 1.0)), float(np.quantile(out, 0.95))


# --------------------------------------------------------------------------
# the synthetic world


def ss_reigns():
    return [(k, a, b) for k, v in COINS.items() for (i, a, b) in v if i == SS]


def ns_reigns():
    return [(k, a, b) for k, v in COINS.items() for (i, a, b) in v if i == NS]


def jin_reigns():
    return [(k, a, b) for k, v in COINS.items() for (i, a, b) in v if i == JIN]


def world(rng):
    """Casting per year for every Song and Jin reign, and the Northern Song stock (fixed)."""
    ns = {k: float(rng.uniform(50, 3000)) for k, a, b in ns_reigns()}
    ss_rate = {k: float(rng.uniform(1, 40)) for k, a, b in ss_reigns()}
    jin_rate = {k: float(rng.uniform(1, 20)) for k, a, b in jin_reigns()}
    return ns, ss_rate, jin_rate


def cast_to(rate, a, b, T):
    """Coins of one reign cast by the end of year T."""
    return rate * max(0, min(T, b) - a + 1)


def stock_rows(w, T, cut=None, chunxi_split=True, jin=None):
    """Expected hoard of one coin per unit of stock: rows as hoard_numbers takes them.

    Jin coins go into a hoard on the cut side only, unless jin is given.
    """
    jin = (cut is not None) if jin is None else jin
    ns, ss_rate, jin_rate = w
    rows = [{"label": k + "通宝", "issuer": NS, "count": v} for k, v in ns.items()]
    reach = T if cut is None else min(T, cut)
    for k, a, b in ss_reigns():
        if k == "淳熙" and chunxi_split:
            rows.append({"label": "淳熙元宝", "issuer": SS,
                         "count": cast_to(ss_rate[k], a, min(b, 1179), reach)})
            for y in range(1180, min(b, reach) + 1):
                rows.append({"label": "淳熙元宝", "issuer": SS, "count": ss_rate[k],
                             "back_year": y})
            continue
        rows.append({"label": k + "元宝", "issuer": SS, "count": cast_to(ss_rate[k], a, b, reach)})
    for k, a, b in (jin_reigns() if jin else []):
        rows.append({"label": k + "通宝", "issuer": JIN, "count": cast_to(jin_rate[k], a, b, T)})
    return rows


def closed_S(w, T, cut=None):
    ns, ss_rate, _ = w
    reach = T if cut is None else min(T, cut)
    return sum(cast_to(ss_rate[k], a, b, reach) for k, a, b in ss_reigns()) / sum(ns.values())


def closed_Q(w, T, c=CUT_STABLE, cut=None):
    _, ss_rate, _ = w
    reach = T if cut is None else min(T, cut)
    pre = sum(cast_to(ss_rate[k], a, min(b, c), reach) for k, a, b in ss_reigns())
    post = sum(cast_to(ss_rate[k], max(a, c + 1), b, reach) for k, a, b in ss_reigns() if b > c)
    return post / pre


def rel(a, b):
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b))


# --------------------------------------------------------------------------
# B140-1, block one


def check_closed_forms(fault=None) -> dict:
    """Noiseless hoards: every quantity against its closed form."""
    rng = np.random.default_rng(SEED)
    errs, notes = [], []
    for _ in range(40):
        w = world(rng)
        for T in (1165, 1178, 1190, 1204, 1215, 1230):
            home = hoard_numbers(stock_rows(w, T), "song", fault=fault)
            far = hoard_numbers(stock_rows(w, T, cut=CUT_STABLE), "jin", fault=fault)
            errs += [rel(home["S"], closed_S(w, T)), rel(far["S"], closed_S(w, T, CUT_STABLE))]
            if T > CUT_STABLE:
                errs.append(rel(home["Q"], closed_Q(w, T)))
                errs.append(abs(far["Q"] - closed_Q(w, T, cut=CUT_STABLE)))
            # dating: the Jin hoard carries its latest Jin reign cast by T, never a Song year
            want = max(a for k, a, b in jin_reigns() if a <= T) if T >= 1158 else None
            if far["T_h"] != want:
                notes.append(f"Jin hoard at {T} dated {far['T_h']}, want {want}")
            if home["T_h"] != max(a for k, a, b in ss_reigns() if a <= T):
                notes.append(f"Song hoard at {T} dated {home['T_h']}")
        # rho over a window of burial years, odd count, so the median is the middle year
        Ts = [1205, 1210, 1215, 1220, 1225]
        hoards = ([("jin", hoard_numbers(stock_rows(w, T, cut=CUT_STABLE), "jin", fault=fault), 2000)
                   for T in Ts] +
                  [("song", hoard_numbers(stock_rows(w, T), "song", fault=fault), 1950 + T % 7)
                   for T in Ts])
        r, nf, nh = rho(hoards, WINDOW_MAIN, fault=fault)
        errs.append(rel(r, closed_S(w, 1215, CUT_STABLE) / closed_S(w, 1215)))
        if (nf, nh) != (5, 5):
            notes.append(f"window picked {nf} Jin, {nh} Song hoards, want 5 and 5")
    worst = max(errs)
    return {"passed": worst < TOL and not notes, "worst": worst, "notes": notes[:5]}


def check_dating_unit(fault=None) -> dict:
    """One Jin hoard buried 1215 with a Jiading (1208) coin and no Taihe: it dates to 1178."""
    rows = [{"label": "元丰通宝", "count": 500}, {"label": "嘉定通宝", "count": 2},
            {"label": "大定通宝", "count": 30}]
    t = hoard_numbers(rows, "jin", fault=fault)["T_h"]
    return {"passed": t == 1178, "T_h": t}


def hoard_sample(rng, w, T, cut, size, conc):
    """One real-looking hoard: a Dirichlet draw around the stock (between-hoard spread), then coins."""
    base = [r for r in stock_rows(w, T, cut=cut, chunxi_split=False) if r["issuer"] in (NS, SS)]
    p = np.array([r["count"] for r in base], float)
    p = rng.dirichlet(conc * p / p.sum() + 1e-9)
    n = rng.multinomial(size, p)
    is_ss = np.array([r["issuer"] == SS for r in base])
    return np.array([n[~is_ss].sum(), n[is_ss].sum()], float), n, is_ss


def check_bootstrap(fault=None) -> dict:
    """11f: a cut world must pass, a same-stock world must not."""
    out = {}
    for name, cut in (("cut", CUT_STABLE), ("same_stock", None)):
        seed = SEED
        while True:
            rng = np.random.default_rng(seed)
            w = world(rng)
            far = [hoard_sample(rng, w, int(rng.integers(1204, 1234)), cut, 20000, 300.0)
                   for _ in range(9)]
            home = [hoard_sample(rng, w, int(rng.integers(1204, 1234)), None, 20000, 300.0)
                    for _ in range(9)]
            r = np.median([f[0][1] / f[0][0] for f in far]) / np.median([h[0][1] / h[0][0] for h in home])
            # the same-stock world is drawn until chance puts rho below one, the hard case
            if name == "cut" or r < 0.9:
                break
            seed += 1
        fr = [f[0] for f in far]
        hr = [h[0] for h in home]
        p1, q95 = bootstrap_upper(fr, hr, SEED, fault=fault)
        p2, _ = bootstrap_upper(fr, hr, SEED + 1, fault=fault)
        readable = abs(p1 - p2) < abs((p1 + p2) / 2 - 0.05)  # D51
        out[name] = {"rho": float(r), "p": (p1, p2), "q95": q95, "readable": readable,
                     "pass": readable and q95 < 1.0, "seed": seed}
    return {"passed": out["cut"]["pass"] and not out["same_stock"]["pass"], **out}


def check_window_by_discovery(fault=None) -> dict:
    """The window must follow T_h: hoards found in any year, buried in or out of it."""
    rng = np.random.default_rng(SEED)
    w = world(rng)
    hoards = []
    for T, found in ((1210, 1960), (1225, 1990), (1180, 2012), (1150, 1985)):
        hoards.append(("jin", hoard_numbers(stock_rows(w, T, cut=CUT_STABLE), "jin"), found))
        hoards.append(("song", hoard_numbers(stock_rows(w, T), "song"), found))
    _, nf, nh = rho(hoards, WINDOW_MAIN, fault=fault)
    return {"passed": (nf, nh) == (2, 2), "picked": (nf, nh)}


def check_pooling(fault=None) -> dict:
    """rho is a ratio of medians over hoards, not of pooled coins: one big hoard must not carry it."""
    rows_small = [{"label": "元丰通宝", "count": 100}, {"label": "绍兴元宝", "count": 1}]
    rows_big = [{"label": "元丰通宝", "count": 100000}, {"label": "绍兴元宝", "count": 50000}]
    tah = {"label": "泰和重宝", "count": 1}
    jin = [("jin", hoard_numbers(rows_small + [tah], "jin"), 0) for _ in range(3)]
    jin.append(("jin", hoard_numbers(rows_big + [tah], "jin"), 0))
    song_rows = [{"label": "元丰通宝", "count": 100}, {"label": "嘉定通宝", "count": 2}]
    song = [("song", hoard_numbers(song_rows, "song"), 0) for _ in range(4)]
    r, _, _ = rho(jin + song, WINDOW_MAIN, fault=fault)
    return {"passed": abs(r - 0.5) < TOL, "rho": r}


def presence_verdict(home_present, p_min, dest, alpha=0.05, fault=None):
    """B140-3c, read at scale. home_present: for each home hoard, whether coins cast after the border are
    there. dest: (Southern Song coins in the hoard, of them cast after the border) per destination hoard.
    On the rival's premise the late coins reach a destination at their home share p; p_min, the lowest
    home share, is the rival's best case. A cut edge still leaks a few coins, so one late coin decides
    nothing: the criterion fails only where the destination's late share reaches the home share, and
    passes where the rival's chance of a share that low is below alpha."""
    if not home_present or not all(home_present) or not dest:
        return {"passed": None, "prob": None, "share": None}
    n = sum(a for a, _ in dest)
    k = sum(b for _, b in dest)
    share = k / n if n else None
    if fault == "single_coin_fails" and k > 0:
        return {"passed": False, "prob": None, "share": share}
    if share is not None and share >= p_min:
        return {"passed": False, "prob": None, "share": share}
    # rival's probability of k or fewer late coins among n, binomial at p_min
    prob = float(sum(math.comb(int(n), j) * p_min ** j * (1 - p_min) ** (int(n) - j) for j in range(int(k) + 1)))
    if fault == "presence_without_power":
        return {"passed": True, "prob": prob, "share": share}
    return {"passed": True if prob < alpha else None, "prob": prob, "share": share}


def check_presence(fault=None) -> dict:
    """At the home share it fails; one late coin among many passes; too few coins stay unread."""
    got = {"home share at destination": presence_verdict([True] * 3, 0.15, [(30, 6)], fault=fault)["passed"],
           "one coin among many": presence_verdict([True] * 3, 0.15, [(60, 1)], fault=fault)["passed"],
           "few coins": presence_verdict([True] * 3, 0.15, [(5, 0)], fault=fault)["passed"],
           "enough coins": presence_verdict([True] * 3, 0.15, [(10, 0), (25, 0)], fault=fault)["passed"],
           "home lacks them": presence_verdict([True, False], 0.15, [(40, 0)], fault=fault)["passed"]}
    want = {"home share at destination": False, "one coin among many": True, "few coins": None,
            "enough coins": True, "home lacks them": None}
    return {"passed": got == want, "got": got}


# B140-9. Northern Song vintages in Xixia hoards against a reference stock of Northern Song coin, grouped by
# the Song-Xia war and peace periods (the five wars: 1040-44, 1064-67, 1071-82, 1096-99, 1114-19;
# Song shi as quoted in the war histories). The edge state read is the actual one: a closed trading post
# without war kept trade going as smuggling (Chen Xu 2005), a war cut it.
XIA_WARS = [(1040, 1044), (1064, 1067), (1071, 1082), (1096, 1099), (1114, 1119)]

# A segment is a group of reign titles: a coin is dated no finer than its title. The years in a label are the
# casting span of the group's titles, and the kind is the state of the edge over most of those years; segment_scope
# prints the war years inside each title and the share of each group's coin that falls in war years.
XIA_SEGMENTS = [
    ("A peace 1004-1053", ["景德", "祥符", "天禧", "天圣", "明道", "景祐", "皇宋"], "peace"),
    ("B war 1040-1048", ["康定", "庆历"], "war"),
    ("C peace 1054-1063", ["至和", "嘉祐"], "peace"),
    ("D war 1064-1085", ["治平", "熙宁", "元丰"], "war"),
    ("E peace 1086-1097", ["元祐", "绍圣"], "peace"),
    ("F war 1098-1100", ["元符"], "war"),
    ("G peace 1101", ["圣宋"], "peace"),
    ("H late 1102-1126", ["崇宁", "大观", "政和", "重和", "宣和", "靖康"], "late"),
]


# Segment B is one coin, the Qingli ten-cash piece, scarce in the north whatever the border did: the step
# out of it rises in every placebo hoard, so it separates nothing and is not counted (2026-09-30).
SINGLE_TYPE_SEGMENTS = {"B war 1040-1048"}

# The reference stocks the reading is taken against. The common stock is the Northern Song coin of the hoards of
# Jin territory and of Southern Song territory and of no other place.
COMMON_PLACES = ("jin", "song")


def war_years(a, b, fault=None):
    """Calendar years from a to b, both included, that lie inside a Song-Xia war."""
    if fault == "war_end_year_out":
        return sum(1 for y in range(a, b + 1) if any(lo <= y < hi for lo, hi in XIA_WARS))
    return sum(1 for y in range(a, b + 1) if any(lo <= y <= hi for lo, hi in XIA_WARS))


def segment_scope(stock, fault=None):
    """What a segment can and cannot date. For each group: its titles with their casting years and the war years
    among them; the share of the group's coin (counts from `stock`) cast in war years if each title's coin is
    spread evenly over its years; and the lowest and highest share any spread inside the titles allows."""
    out = []
    for lab, keys, kind in XIA_SEGMENTS:
        tot = even = lo = hi = 0.0
        titles = []
        for k in keys:
            a, b = next((a, b) for issuer, a, b in COINS[k] if issuer == NS)
            w, n = war_years(a, b, fault), stock.get(k, 0.0)
            titles.append({"title": k, "cast": [a, b], "years": b - a + 1, "war_years": w})
            tot += n
            even += n * w / (b - a + 1)
            lo += n if w == b - a + 1 else 0.0
            hi += n if w else 0.0
        out.append({"segment": lab, "kind": kind, "titles": titles,
                    "war_share_even": round(even / tot, 4) if tot else None,
                    "war_share_bounds": [round(lo / tot, 4), round(hi / tot, 4)] if tot else None})
    return out


def check_segments(fault=None) -> dict:
    """War years inside the titles the counted steps rest on, and the kind of each counted segment against the
    share of its years at war: above one half for a war group, below for a peace group."""
    flat = {k: 1.0 for _, keys, _ in XIA_SEGMENTS for k in keys}
    scope = {s["segment"][0]: s for s in segment_scope(flat, fault)}
    years = {t["title"]: t["war_years"] for s in scope.values() for t in s["titles"]}
    got = {"war years": {k: years[k] for k in ("治平", "熙宁", "元丰", "元祐", "绍圣", "元符", "圣宋")},
           "kinds agree": all((scope[g]["war_share_even"] > 0.5) == (scope[g]["kind"] == "war") for g in "DEFG")}
    want = {"war years": {"治平": 4, "熙宁": 7, "元丰": 5, "元祐": 0, "绍圣": 2, "元符": 2, "圣宋": 0},
            "kinds agree": True}
    return {"passed": got == want, "got": got}


def segment_ratios(counts, other, segments=XIA_SEGMENTS):
    """Share of each segment's coins in one hoard over its share in a reference stock."""
    T, OT = sum(counts.values()), sum(other.values())
    out = []
    for lab, keys, kind in segments:
        x, o = sum(counts.get(k, 0) for k in keys), sum(other.get(k, 0) for k in keys)
        out.append((lab, kind, (x / T) / (o / OT) if x and o else None, x))
    return out


def vintage_counts(rows):
    """Northern Song coins of one hoard by reign title."""
    c = defaultdict(float)
    for r in rows:
        m, _ = map_coin(r["label"], r.get("issuer"))
        if m and m[0] == NS and r["count"] > 0:
            c[reign_key(norm(r["label"]))] += r["count"]
    return c


def pool(counts):
    p = defaultdict(float)
    for c in counts:
        for k, v in c.items():
            p[k] += v
    return p


def without(stock, c):
    """A stock without one of the hoards pooled in it."""
    return {k: v - c.get(k, 0.0) for k, v in stock.items()}


def vintage_pools(hoards, fault=None):
    """hoards: (name, place, rows, excluded). Northern Song coin by reign title for every hoard not excluded, by
    place, and the common stock. The seeded fault pools every place that is not a destination, which takes in
    hoards sealed under the Northern Song."""
    by = {}
    for name, place, rows, excl in hoards:
        if not excl:
            by.setdefault(place, {})[name] = vintage_counts(rows)
    places = [p for p in by if p not in ("xia", "liao")] if fault == "common_takes_every_place" else COMMON_PLACES
    return by, pool(c for p in places for c in by.get(p, {}).values())


def check_common_scope(fault=None) -> dict:
    """A hoard sealed under the Northern Song, a Liao one, a Xixia one and an excluded one stay out of the stock."""
    def row(n):
        return [{"label": "元丰通宝", "issuer": "北宋", "count": n}]
    hoards = [("a", "jin", row(100), None), ("b", "song", row(10), None), ("c", "ns", row(7), None),
              ("d", "liao", row(5), None), ("e", "xia", row(3), None), ("f", "jin", row(1000), "excluded")]
    _, common = vintage_pools(hoards, fault)
    return {"passed": sum(common.values()) == 110, "got": sum(common.values())}


def hoard_rises(segs, fault=None):
    """(rising, counted) over the counted steps of one hoard. A vintage-by-vintage decline, which a flow that
    simply ended in 1127 would give, never rises; so only the war-to-peace steps are counted, and not the step out
    of a single-type segment. The seeded faults count the peace-to-war drops instead (a steady decline produces
    them too) or count the single-type step."""
    hits = total = 0
    for (la, ka, ra, _), (lb, kb, rb, _) in zip(segs, segs[1:]):
        if ra is None or rb is None:
            continue
        if la in SINGLE_TYPE_SEGMENTS and fault != "count_single_type_step":
            continue
        if fault == "drops_only":
            if ka == "peace" and kb == "war":
                total += 1
                hits += rb < ra
        elif ka == "war" and kb == "peace":
            total += 1
            hits += rb > ra
    return hits, total


def tally_hoards(per_hoard, fault=None):
    """Hoards with a counted step: how many rise at every counted step, how many at none, and the steps."""
    res = [(h, t) for h, t in (hoard_rises(s, fault) for s in per_hoard) if t]
    return {"hoards": len(res), "hoards_rising": sum(1 for h, t in res if h == t),
            "hoards_falling": sum(1 for h, t in res if h == 0),
            "steps": sum(t for _, t in res), "steps_rising": sum(h for h, _ in res),
            "hoards_with_both_steps": sum(1 for _, t in res if t == 2),
            "hoards_with_both_rising": sum(1 for h, t in res if t == 2 and h == 2)}


MAPPING_B140_9 = {"every hoard rises and the probability is below 0.05": True,
                  "every hoard falls and the probability is below 0.05": False,
                  "anything else": None}


def transitions_test(per_hoard, fault=None, placebo=None):
    """Sign test with the hoard as the unit. A hoard counts once: as rising when every counted step of it rises,
    as falling when none does. The steps of one hoard come from one set of counts, so they are not multiplied
    as separate trials (the seeded fault steps_as_units does that). Rival: a hoard rises with probability at
    most one half, or the share of the placebo hoards that rise if that is higher; the mirror bound holds for
    falling. placebo is (share rising, share falling) among hoards where the Song-Xia wars were not on the edge.
    The verdict follows MAPPING_B140_9: three hoards cannot reach 0.05, five can."""
    t = tally_hoards(per_hoard, fault)
    hoards, up, down = t["hoards"], t["hoards_rising"], t["hoards_falling"]
    p_up, p_down = (None, None) if placebo is None or fault == "ignore_placebo" else placebo
    b_up = 0.5 if p_up is None else max(0.5, p_up)
    b_down = 0.5 if p_down is None else max(0.5, p_down)
    n = t["steps"] if fault == "steps_as_units" else hoards
    passed, prob, bound = None, 1.0, b_up
    if hoards and up == hoards:
        prob = b_up ** n
        passed = True if prob < 0.05 else None
    elif hoards and down == hoards:
        bound, prob = b_down, b_down ** n
        passed = False if prob < 0.05 else None
    return {"passed": passed, "rises": t["steps_rising"], "total": t["steps"], "hoards": hoards,
            "hoards_rising": up, "hoards_falling": down, "prob": prob, "bound": bound,
            "hoards_needed": math.ceil(math.log(0.05) / math.log(bound)) if bound < 1 else None}


def claim_9(by_reference, fault=None):
    """The cell is claimed only when every reference stock gives the same verdict; the seeded fault reads the
    first reference alone."""
    v = [r["passed"] for r in by_reference.values()]
    if fault == "one_reference":
        v = v[:1]
    return v[0] if v and all(x == v[0] for x in v) else None


def rank_prob(xs, others, side="high"):
    """Exact chance that len(xs) hoards drawn from all of them rank at least as high (or as low) as xs do:
    the hoard is the unit, nothing is assumed about the spread."""
    vals = list(xs) + list(others)
    sign = 1.0 if side == "high" else -1.0

    def score(idx):
        rest = [vals[i] for i in range(len(vals)) if i not in idx]
        return sum(sum(1.0 if sign * (vals[i] - o) > 0 else 0.5 if vals[i] == o else 0.0 for o in rest) for i in idx)
    obs = score(tuple(range(len(xs))))
    hits = total = 0
    for idx in itertools.combinations(range(len(vals)), len(xs)):
        total += 1
        hits += score(idx) >= obs - 1e-9
    return hits / total


def check_rank_prob(fault=None) -> dict:
    """Three hoards above all of seven others: one arrangement of 120; in the middle: nothing."""
    top = rank_prob([8, 9, 10], [1, 2, 3, 4, 5, 6, 7])
    low = rank_prob([1, 2, 3], [4, 5, 6, 7, 8, 9, 10], side="low")
    mid = rank_prob([4, 5, 6], [1, 2, 3, 7, 8, 9, 10])
    return {"passed": abs(top - 1 / 120) < TOL and abs(low - 1 / 120) < TOL and mid > 0.4,
            "got": (round(top, 6), round(low, 6), round(mid, 4))}


def check_transitions(fault=None) -> dict:
    """Five hoards that all alternate pass and five that all fall fail; three hoards, a mixed set, hoards that
    add only the single-type step, a placebo that rises too and two references that disagree are not decided."""
    def series(vals):
        return [(lab, kind, v, 100) for (lab, _, kind), v in zip(XIA_SEGMENTS, vals)]
    alt = series([1.2, 0.5, 1.5, 0.9, 1.0, 0.8, 1.0, 0.5])
    fall = series([1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.5])
    early = series([1.2, 0.5, 1.5, None, None, None, None, None])  # only the single-type step can be read

    def t(hoards, **kw):
        return transitions_test(hoards, fault, **kw)
    got = {"alternating, five hoards": t([alt] * 5)["passed"],
           # one half to the third power is 0.125: the six steps of three hoards are not six trials
           "alternating, three hoards": t([alt] * 3)["passed"],
           "falling, five hoards": t([fall] * 5)["passed"],
           "three rise and two fall": t([alt] * 3 + [fall] * 2)["passed"],
           "single-type step only": t([alt] * 3 + [early] * 2)["passed"],
           # the same steps rise everywhere at the placebo destinations: nothing is separated
           "placebo rises too": t([alt] * 5, placebo=(1.0, 0.0))["passed"],
           "references disagree": claim_9({"one": t([alt] * 5), "other": t([fall] * 5)}, fault),
           "references agree": claim_9({"one": t([alt] * 5), "other": t([alt] * 5)}, fault)}
    want = {"alternating, five hoards": True, "alternating, three hoards": None, "falling, five hoards": False,
            "three rise and two fall": None, "single-type step only": None, "placebo rises too": None,
            "references disagree": None, "references agree": True}
    return {"passed": got == want and MAPPING_B140_9["anything else"] is None, "got": got}


CHECKS = {"closed forms": check_closed_forms, "dating": check_dating_unit,
          "window": check_window_by_discovery, "bootstrap": check_bootstrap,
          "pooling": check_pooling, "presence": check_presence, "transitions": check_transitions,
          "segments": check_segments, "common stock": check_common_scope, "rank": check_rank_prob}


# --------------------------------------------------------------------------
# the transcribed tables: every label mapped, every table summed


def read_tsv(path: Path):
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))


# Sato 2021 table 3 prints row 7 (Chong'an) as "熙寧元・重87、30": thirty coins with no name, inside the Northern
# Song bracket, after the Xining pair and before Yuanfeng, and the row reaches its printed total of 1,227 only with
# them. The transcription keeps the token as printed (label "3", count 0); it is read here as Northern Song coin in
# the Xining position (page image alt_miyake_sato95_p14_rows7_8.png).
SATO_READ_ON_THE_PAGE = {("7", "3", "30"): ("熙寧", 30.0)}


def tables():
    """(name, rows as hoard_numbers takes them, printed total or None, place)."""
    out = []
    sato = RAW / "alt_miyake"
    head = {r["no"]: r for r in read_tsv(sato / "sato2021_komazawa95_table3_rows.tsv")}
    long = read_tsv(sato / "sato2021_komazawa95_table3_long.tsv")
    by = {}
    for r in long:
        c = r["count"].strip()
        label, count = r["coin_label_as_printed"], (float(c) if c else 0.0)
        label, count = SATO_READ_ON_THE_PAGE.get((r["no"], label, r["token_as_printed"].strip()), (label, count))
        by.setdefault(r["no"], []).append({"label": label, "issuer": r["group_as_printed"], "count": count})
    for no, rows in by.items():
        h = head[no]
        tot = h["total_as_printed"].strip().replace(",", "")
        out.append((f"Sato 2021 t3 #{no} {h['site_as_printed']}", rows,
                    float(tot) if tot else None, h["type_as_printed"]))
    for f, tot in (("user_reports/user_reports_jiutai_kalun_wenwu1985-1.tsv", 26463),
                   ("user_reports/user_reports_quzhou_kaixianyuan_kaogu1983-9.tsv", 3092)):
        rows = []
        for r in read_tsv(RAW / f):
            name = re.sub(r"\([^)]*\+[^)]*\)", "", r["钱文"])  # "(小平+折二)" names sizes, not coins
            for part in name.split("+"):
                rows.append({"label": part, "issuer": r["发行方"], "count": 0.0,
                             "printed_year": r["始铸年"]})
            rows[-1]["count"] = float(r["枚数"])
        out.append((f, rows, tot, None))
    rows = []
    tot = None
    for r in read_tsv(RAW / "jin_hoards/anyang_xiaoxue_shunping_miyake2004_table1.tsv"):
        if r["type_inscription"] == "TOTAL_PRINTED":
            tot = float(r["total"])
        elif not r["type_inscription"].startswith("TOTAL"):
            rows.append({"label": r["type_inscription"].split("・")[-1], "issuer": r["issuer"],
                         "count": float(r["total"]), "printed_year": r["first_cast_ce"]})
    out.append(("anyang_xiaoxue", rows, tot, None))
    rows = [{"label": r["name"], "issuer": r["issuer"], "count": float(r["count_used"]),
             "printed_year": r["first_year"]} for r in read_tsv(RAW / "mashan/mashan_changtun_yu1997_transcribed.tsv")]
    out.append(("mashan (selected sample)", rows, None, None))
    return out


def label_report():
    unmapped, year_diff, sums = [], [], []
    for name, rows, tot, _ in tables():
        s = sum(r["count"] for r in rows)
        if tot is not None and abs(s - tot) > 0:
            sums.append(f"{name}: rows sum {s:g}, printed {tot:g}")
        for r in rows:
            m, why = map_coin(r["label"], r.get("issuer"))
            if m is None:
                unmapped.append(f"{name}: {r['label']} [{r.get('issuer')}] n={r['count']:g}: {why}")
                continue
            py = r.get("printed_year")
            if py and py.lstrip("-").isdigit() and int(py) != m[1] and m[0] in (NS, SS, JIN):
                year_diff.append(f"{r['label']} [{m[0]}]: table {py}, map {m[1]}")
    return unmapped, sorted(set(year_diff)), sums


# --------------------------------------------------------------------------


def paper() -> int:
    ok = True
    print("B140 block one: every check on synthetic hoards, then with each seeded fault\n")
    for name, fn in CHECKS.items():
        res = fn()
        ok &= res["passed"]
        print(f"  {name:13s} {'PASS' if res['passed'] else 'FAIL'}  {short(res)}")
    print()
    for fault in FAULTS:
        caught = [n for n, fn in CHECKS.items() if not fn(fault=fault)["passed"]]
        ok &= bool(caught)
        print(f"  fault {fault:24s} caught by: {', '.join(caught) or 'NOTHING'}")
    print("\nLabels in the transcribed tables")
    unmapped, year_diff, sums = label_report()
    print(f"  unmapped ({len(unmapped)}):")
    for u in unmapped:
        print("    " + u)
    print(f"  mapped although the table's group disagrees ({len(MISGROUPED)}):")
    for u in sorted(MISGROUPED):
        print("    " + u)
    print(f"  first-cast year, table against map, Song and Jin only ({len(year_diff)}):")
    for y in year_diff:
        print("    " + y)
    print(f"  tables whose rows do not sum to the printed total ({len(sums)}):")
    for s in sums:
        print("    " + s)
    print(f"\nblock one {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def short(res):
    keep = {k: v for k, v in res.items() if k != "passed"}
    if "cut" in keep:
        return "; ".join(f"{k}: rho {v['rho']:.3f}, p {v['p'][0]:.4f}/{v['p'][1]:.4f}, "
                         f"q95 {v['q95']:.3f}, pass {v['pass']}" for k, v in keep.items()
                         if isinstance(v, dict))
    return ", ".join(f"{k} {v}" for k, v in keep.items())


# --------------------------------------------------------------------------
# block two: the readings (printed, not written; block three writes the record)

# Sato 2021 table 3 rows by place; region misprints corrected where the site says otherwise
PLACE = {**{str(n): "song" for n in (3, 4, 5, 6, 7, 8, 10)}, "9": "jin",  # 宿州 is Jin after 1142
         **{str(n): "liao" for n in (11, 12, 13)}, **{str(n): "xia" for n in (14, 15, 16)},
         **{str(n): "jin" for n in range(17, 31)}, "1": "ns", "2": "ns"}
EXCLUDE = {"8": "開仙院: temple offering deposit (Miyake 2024 n.7 excludes it)",
           "10": "乐安: Sato's row copies 衢州; the 叙录 entry for the same hoard (乐安公溪镇芜头) replaces it",
           "19": "大鄭村: a collector's hoard, every type near 3% (尹郁山, 考古 1988-2; Miyake, 中国历史文物 2004-3, pp.63, 67)",
           "25": "遷安: row swapped with 遷西",
           "26": "遷西: row swapped with 遷安; the 叙录 entry for the same hoard (迁西长岭峰, p.378) replaces it"}


# per-type tables read in 《钱币考古文献叙录》 (2005): (file, name, printed total or None)
# (file, name, printed total or None, place)
XULU = [("xulu_jurong_chuncheng_p322.tsv", "句容春城 (叙录 p.322)", 6180, "song"),
        ("xulu_lean_wutou_p320.tsv", "乐安公溪镇芜头 (叙录 p.320)", 11688, "song"),
        ("xulu_pingxiang_xiashi_p330.tsv", "萍乡硖石 (叙录 p.330)", None, "song"),
        ("xulu_pingxiang_dawangping_p331.tsv", "萍乡大王坪 (叙录 p.331)", None, "song"),
        ("xulu_jin_penglai_xingwu_p369.tsv", "蓬莱兴无 (叙录 p.369)", 59663, "jin"),
        ("xulu_jin_qianxi_changlingfeng_p378.tsv", "迁西长岭峰 (叙录 p.378)", 8214, "jin"),
        ("xulu_jin_huixian_chengnei_p381.tsv", "辉县城内 (叙录 p.381)", 6452, "jin"),
        ("xulu_jin_kedong_fuan_p384.tsv", "克东福安 (叙录 p.384)", 3436, "jin"),
        ("xulu_jin_kangping_biantaizi_p386.tsv", "康平边台子 (叙录 p.386)", 15404, "jin"),
        ("xulu_jin_donggou_majuanzi_p386.tsv", "东沟马圈子 (叙录 p.386)", 9173, "jin")]


def xulu_rows(fname):
    rows = []
    for r in read_tsv(RAW / "xulu" / fname):
        by = (r.get("back_year") or "").strip()
        rows.append({"label": r["label"], "issuer": r["issuer"], "count": float(r["count"]),
                     **({"back_year": int(by)} if by else {})})
    return rows


def china_hoards():
    """(name, place, rows) for every Chinese hoard with a per-type table; original reports override Sato."""
    out = [(name, place, xulu_rows(f), None) for f, name, _, place in XULU]
    for name, rows, tot, typ in tables():
        if name.startswith("Sato"):
            no = name.split("#")[1].split()[0]
            if no == "21":
                continue  # 十里 is 九台卡伦; the original report replaces the row
            if no == "29":
                continue  # 安陽小学: Miyake 2004 table 1 replaces the row
            out.append((name, PLACE[no], rows, EXCLUDE.get(no)))
        elif "jiutai" in name:
            out.append(("九台卡伦 (谷潜 1985)", "jin", rows, None))
        elif "quzhou" in name:
            out.append(("衢州开仙院 (崔成实 1983)", "song", rows, "temple offering deposit"))
        elif name == "anyang_xiaoxue":
            out.append(("顺平安阳小学 (三宅 2004 表1)", "jin", rows, None))
        elif name.startswith("mashan"):
            rows2 = []
            for r in read_tsv(RAW / "mashan/mashan_changtun_yu1997_transcribed.tsv"):
                marks = r["back_marks"]
                if r["name"] == "淳熙元宝":
                    # back years 7, 8, 9, 10, 11, 12, 15 printed without counts per year: all after the cut
                    rows2.append({"label": r["name"], "issuer": r["issuer"], "count": float(r["count_used"]),
                                  "back_year": 1180})
                else:
                    rows2.append({"label": r["name"], "issuer": r["issuer"], "count": float(r["count_used"])})
            out.append(("马山长屯 (于凤芝 1997)", "song", rows2, "hand-picked sample, biased to new coins"))
    return out


def ss_by_cast(rows, lo, hi):
    """Southern Song coins whose first cast year is in [lo, hi]."""
    n = 0.0
    for r in rows:
        m, _ = map_coin(r["label"], r.get("issuer"))
        if m and m[0] == SS and lo <= (r.get("back_year") or m[1]) <= hi and r["count"] > 0:
            n += r["count"]
    return n


def japan_hoards():
    out = []
    for f, name in (("japan/nakaya_akaiwa_table4_transcribed.tsv", "赤磐 中屋"),
                    ("japan/terakaido_maruko_table4_transcribed.tsv", "丸子 寺開土 (197 of about 3,000 survive)")):
        rows = []
        for r in read_tsv(RAW / f):
            cnt = r.get("枚数", "").replace(",", "")
            if cnt.replace(".", "").isdigit():
                rows.append((r.get("王朝") or r.get("王朝(報告の表記)"), int(r["初鋳年"]) if r["初鋳年"].lstrip("-").isdigit() else None,
                             float(cnt), r.get("銭種") or r.get("銭種(報告の表記)")))
        out.append((name, rows))
    wide = [("japan/gifu_kiyo3_tables3-4_transcribed.tsv", "銭貨名", "国・王朝", "初鋳年"),
            ("japan_verify/shinori_table1-3-1_transcribed.tsv", "coin", "issuer", "first_cast")]
    for f, cn, iss, yr in wide:
        recs = read_tsv(RAW / f)
        cols = [c for c in recs[0] if c not in ("No", "no", cn, iss, yr)]
        for c in cols:
            rows = []
            for r in recs:
                v = (r.get(c) or "").replace(",", "").strip()
                if v.replace(".", "").isdigit() and float(v) > 0:
                    y = r[yr].strip()
                    rows.append((r[iss], int(y) if y.lstrip("-").isdigit() else None, float(v), r[cn]))
            label = f"{'岐阜' if 'gifu' in f else '志海苔'} {c}"
            if rows:
                out.append((label, rows))
    return out


def japan_numbers(rows):
    ns = sum(n for i, y, n, _ in rows if i == "北宋")
    ss = sum(n for i, y, n, _ in rows if i == "南宋")
    ss_post = sum(n for i, y, n, _ in rows if i == "南宋" and y and y >= 1180)
    ss_pre = ss - ss_post
    ming = sum(n for i, y, n, _ in rows if i == "明")
    mochu = sum(n for i, y, n, c in rows if c and ("模鋳" in c or "無文" in c or "私鋳" in c))
    total = sum(n for _, _, n, _ in rows)
    th = max(y for _, y, n, _ in rows if y is not None)
    return {"T_h": th, "S": ss / ns if ns else float("nan"), "Q": ss_post / ss_pre if ss_pre else float("nan"),
            "ming": ming / total, "mochu": mochu, "total": total}


def read() -> int:
    print("B140 block two: the readings, printed. Nothing is written.\n")
    print("Chinese hoards with a per-type table. T_h: Jin, Liao and Xixia by their latest coin of an issuer")
    print("the Song cut does not touch; Song territory by its latest coin. Q: Southern Song cast from 1180 on")
    print("over cast before; post-1162: Southern Song cast 1163-1210 over all Southern Song.\n")
    rows_out = []
    for name, place, rows, excl in china_hoards():
        censored = place in ("jin", "xia", "liao")
        h = hoard_numbers(rows, "jin" if censored else "song")
        ss = h["SS"]
        late = ss_by_cast(rows, 1163, 1210)
        post80 = ss_by_cast(rows, 1180, 1300)
        jin = sum(r["count"] for r in rows if (map_coin(r["label"], r.get("issuer"))[0] or ("",))[0] == JIN)
        tot = sum(r["count"] for r in rows)
        rows_out.append((place, h["T_h"], name, h, late, post80, jin / tot if tot else 0, excl))
    for place in ("song", "jin", "xia", "liao"):
        print(f"  [{place}]")
        for p, th, name, h, late, post80, jshare, excl in sorted(r for r in rows_out if r[0] == place):
            print(f"    T_h {th}  S {h['S']:.5f}  SS {h['SS']:6.0f}  cast 1163-1210 {late:4.0f}  from 1180 {post80:4.0f}"
                  f"  Jin share {jshare:.4f}  {name}{'  [out: ' + excl + ']' if excl else ''}")
    print("\nB140-3a/3b, main window T_h >= 1204:")
    for place in ("song", "jin", "xia"):
        inwin = [r for r in rows_out if r[0] == place and r[1] and r[1] >= 1204 and not r[7]]
        print(f"  {place}: {len(inwin)} hoard(s) in the window, not excluded: "
              + "; ".join(f"{r[2]} (T_h {r[1]}, from 1180 {r[5]:.0f} of {r[3]['SS']:.0f} SS)" for r in inwin))
    print("  Jin: 北京右安门 has Taihe (T_h >= 1204), counts not yet read.")
    print("\nB140-3a, dose window 1160-1189:")
    for place in ("song", "jin"):
        inwin = [r for r in rows_out if r[0] == place and r[1] and 1160 <= r[1] <= 1189 and not r[7]]
        print(f"  {place}: {len(inwin)} hoard(s)")
    print("\nB140-5, Japan by T_h (latest coin of any issuer):")
    for name, rows in sorted(japan_hoards(), key=lambda x: japan_numbers(x[1])["T_h"]):
        j = japan_numbers(rows)
        print(f"  T_h {j['T_h']}  S {j['S']:.4f}  Q {j['Q']:.3f}  Ming share {j['ming']:.3f}  "
              f"mochu/mubun {j['mochu']:.0f}  n {j['total']:.0f}  {name}")
    print("\nB140-2, Japan top twenty (Suzuki 1992 table 4):")
    top = read_tsv(RAW / "japan_verify/suzuki1992_table4_top40_transcribed.tsv")[:20]
    from collections import Counter
    print("  " + ", ".join(f"{k} {v}" for k, v in Counter(r["issuer"] for r in top).items()))
    print("  辽宁 'Northern Song above 85%': no underlying table found; not recomputable.")
    return 0


# --------------------------------------------------------------------------
# block three: the record


# reports opened that list coin types without counts per type (rule 25: the zero reads are printed too)
TYPE_LISTS_ONLY = [
    ("北京右安门 (李维, 中国钱币 2013-6)", "jin", ">= 1204 (泰和)", "river-silt scatter; Dading, Taihe, Daguan counted by collectors; no Southern Song type listed"),
    ("高安相城乡 (肖锦秀, 南方文物 1997-2)", "song", "咸淳", "about 15,000 coins; Southern Song 17 types, back years listed; only 正隆 15 and 天盛 1 counted"),
    ("深圳花果山 (南方文物 1996-4)", "song", "淳祐", "about 2 t; 'Southern Song relatively few'; rubbings, no counts"),
    ("长兴虹星乡 (夏星南, 考古 1990-8)", "song", "咸淳", "2,588 coins, 47 types, types only"),
    ("常宁县招待所 (冯玉辉, 考古 1983-1)", "song", "咸淳", "over 4,000 jin, types only"),
    ("玉屏关家屯 (吴钦湘, 考古 1989-7)", "song", "景定", "about 12,000 coins, 53 types, types only"),
    ("罗定车田乡 (陈大远, 考古 1992-3)", "song", "开庆", "12,764 legible coins; counts for Tang and Jin types only"),
    ("黄石西塞山 (湖北省博物馆, 考古 1973-4)", "song", "淳祐 (1252)", "over 20,000 jin; percentages for the commonest types only; Liao, Xixia and Jin coins present"),
    ("安吉五岭冲 (安吉县博物馆, 考古 1982-1)", "song", "咸淳", "about 850 coins, 54 types; counts for the rarest only"),
    ("东莞大岭山 (王健, 考古 1986-7)", "song", "咸淳", "over 50 kg, types only"),
    ("邵阳石脚 (杨平怀, 考古 1985-11)", "song", "咸淳", "7 kg, types only"),
    ("祁东小坪 (唐郑, 考古 1987-2)", "song", "景定", "over 140 jin, types only"),
    ("南宁白坟岭 (叶浓新, 考古 1987-6)", "song", "咸淳", "49.3 jin, types only; back years listed"),
    ("建宁封头 (叙录 p.330; 东南文化 1994-5)", "song", "咸淳", "3,669 kg, types only"),
    ("贺县兴全 (叙录 p.332; 考古与文物 1985-1)", "song", "绍定", "6,557 coins, 40 types, types only"),
    ("临汝佛山寺 (李献奇、侯鸿钧, 中原文物 1984-3)", "jin", "1178 by 大定", "510 kg, 170 types; Southern Song types include 淳熙 backs 捌 (1181) and 十二 (1185), 绍熙 back 元 (1190); no counts"),
]

# Jin-territory hoards whose type lists name Southern Song types cast after the cut; all are dated by
# their Jin or Xixia coins below the window and give no counts, so they are printed, not counted
JIN_LATE_TYPES = [
    ("临汝佛山寺, Henan (中原文物 1984-3)", "1178 (大定)", "淳熙 backs 1181, 1185; 绍熙 back 1190"),
    ("孝义上栅, Shanxi (考古 1988-4, 叙录 p.315)", "1178 (大定)", "嘉定 (1208-1224); 115,500 coins"),
    ("微山田陈, Shandong (中国钱币 1987-2, 叙录 p.316)", "1178 (大定)", "淳熙 with back years, 'a few of each'"),
    ("三原五泉, Shaanxi (内蒙古金融 1987-4, 叙录 p.323)", "1194 (Xixia 天庆)", "淳熙 back 柒 (1180)"),
    ("定兴小店, Hebei (中原文物 1987-1; 孙斌 2020 p.51)", "1178 (大定)",
     "淳熙 backs 十一, 十二, 十四 (1184-1187); the Sato row counts 9 淳熙 without back years"),
    ("沁阳金冢, Henan (华夏考古 1990-2; 孙斌 2020 p.51)", "1178 (大定)", "淳熙 backs 柒 to 十三 (1180-1186)"),
    ("获鹿张家庄, Hebei (考古 1989-2; 叙录 p.377)", "1178 (大定)",
     "淳熙 22 with backs 捌, 九, 十, 一 as printed (from 1181); the Sato row counts the 22 without back years"),
]

# Jin-territory hoards the dating rule puts in the main window, with no count by Southern Song type
WINDOW_JIN_NO_TABLE = [
    ("北京右安门 (中国钱币 2013-6)", ">= 1204 (泰和)", "no Southern Song type listed"),
    ("甘泉蛇河沟, Shaanxi (陕西金融 1993 增刊钱币专辑 19; 叙录 p.382)", "1210 (Xixia 皇建)",
     "28,104 coins identified; Southern Song 284, types 建炎, 绍兴, 乾道, 淳熙, none later (孙斌 2020 p.51 agrees); "
     "read in 3c on the type basis"),
]

# the same reports read for presence: Southern Song types cast from 1180; Jin coins cast before 1198
# (Zhenglong, Dading); Jin coins cast after 1198 (Taihe). Read from the type lists in each report.
PRESENCE_LISTS = {
    "安吉": {"ss_after_1180": True, "jin_before_1198": ["正隆", "大定"], "jin_after_1198": []},
    "东莞": {"ss_after_1180": True, "jin_before_1198": [], "jin_after_1198": []},
    "邵阳": {"ss_after_1180": True, "jin_before_1198": ["正隆"], "jin_after_1198": []},
    "祁东小坪": {"ss_after_1180": True, "jin_before_1198": ["正隆", "大定"], "jin_after_1198": []},
    "南宁": {"ss_after_1180": True, "jin_before_1198": [], "jin_after_1198": []},
    "高安": {"ss_after_1180": True, "jin_before_1198": ["正隆"], "jin_after_1198": []},
    "深圳": {"ss_after_1180": True, "jin_before_1198": ["正隆", "大定"], "jin_after_1198": []},
    "长兴": {"ss_after_1180": True, "jin_before_1198": ["正隆", "大定"], "jin_after_1198": []},
    "常宁": {"ss_after_1180": True, "jin_before_1198": ["正隆"], "jin_after_1198": []},
    "玉屏": {"ss_after_1180": True, "jin_before_1198": ["正隆"], "jin_after_1198": []},
    "罗定": {"ss_after_1180": True, "jin_before_1198": ["正隆"], "jin_after_1198": []},
    "黄石": {"ss_after_1180": True, "jin_before_1198": ["正隆", "大定"], "jin_after_1198": []},
    "北京右安门": {"ss_after_1180": False, "jin_before_1198": ["正隆", "大定"], "jin_after_1198": ["泰和"]},
}


def late_share(rows):
    """Southern Song coins cast 1180-1210 over those cast to 1179 plus those; reigns running past 1210 left out."""
    pre = post = 0.0
    for r in rows:
        m, _ = map_coin(r["label"], r.get("issuer"))
        if not m or m[0] != SS or r["count"] <= 0:
            continue
        a, b = m[1], m[2]
        by = r.get("back_year")
        if by is not None:
            year_lo = year_hi = by
        elif a == 1174:
            year_lo, year_hi = 1174, 1179  # Chunxi without a year mark
        else:
            year_lo, year_hi = a, b
        if year_hi <= CUT_STABLE:
            pre += r["count"]
        elif year_lo > CUT_STABLE and year_hi <= 1210:
            post += r["count"]
    return post / (pre + post) if pre + post else None


# B140-3c on the reign-type basis (2026-09-30): Southern Song coins of the types first cast 1190-1210
# (Shaoxi, Qingyuan, Jiatai, Kaixi, Jiading) against every Southern Song type first cast to 1210. It reads a
# report that names the types and gives a total but no count by casting year, such as Ganquan Shehegou.
LATE_TYPE_FROM = 1190


def type_counts(rows, fault=None):
    """(Southern Song coins of types first cast to 1210, of them types first cast 1190-1210)."""
    start = 1174 if fault == "type_basis_takes_chunxi" else LATE_TYPE_FROM
    early = late = 0.0
    for r in rows:
        m, _ = map_coin(r["label"], r.get("issuer"))
        if not m or m[0] != SS or r["count"] <= 0 or m[1] > 1210:
            continue
        if m[1] >= start:
            late += r["count"]
        else:
            early += r["count"]
    return early + late, late


def check_type_basis(fault=None) -> dict:
    """Chunxi is before the late types, Chunyou (1241) is past the window, Shaoxi is late."""
    rows = [{"label": "建炎通宝", "issuer": "南宋", "count": 5}, {"label": "淳熙元宝", "issuer": "南宋", "count": 10},
            {"label": "绍熙元宝", "issuer": "南宋", "count": 5}, {"label": "淳祐元宝", "issuer": "南宋", "count": 7}]
    n, k = type_counts(rows, fault)
    return {"passed": (n, k) == (20, 5), "got": (n, k)}


CHECKS["type basis"] = check_type_basis


# destinations read on the type basis that give no count by type: (name, T_h, Southern Song coins,
# of them late types, what the reports say)
TYPE_BASIS_DEST = [
    ("甘泉蛇河沟, Shaanxi, Jin territory", 1210, 284, 0,
     "types Jianyan, Shaoxing, Qiandao, Chunxi 'and others' (叙录 p.382); Sun Bin 2020 p.51 lists it under Chunxi "
     "and under no later type"),
]


def hoard_table():
    out = []
    for name, place, rows, excl in china_hoards():
        censored = place in ("jin", "xia", "liao")
        h = hoard_numbers(rows, "jin" if censored else "song")
        tot = sum(r["count"] for r in rows)
        jin = sum(r["count"] for r in rows if (map_coin(r["label"], r.get("issuer"))[0] or ("",))[0] == JIN)
        out.append({"hoard": name, "place": place, "T_h": h["T_h"], "NS": h["NS"], "SS": h["SS"],
                    "S_h": round(h["S"], 6) if h["NS"] else None,
                    "SS_cast_1163_1210": ss_by_cast(rows, 1163, 1210), "SS_cast_from_1180": ss_by_cast(rows, 1180, 1300),
                    "jin_share": round(jin / tot, 5) if tot else None, "excluded": excl})
    return out


def build_record() -> dict:
    checks = {n: fn()["passed"] for n, fn in CHECKS.items()}
    faults = {f: any(not fn(fault=f)["passed"] for fn in CHECKS.values()) for f in FAULTS}
    unmapped, year_diff, sums = label_report()
    table = hoard_table()
    usable = [h for h in table if not h["excluded"]]
    win = {p: [h for h in usable if h["place"] == p and h["T_h"] and h["T_h"] >= 1204] for p in ("song", "jin", "xia")}
    dose = {p: [h for h in usable if h["place"] == p and h["T_h"] and 1160 <= h["T_h"] <= 1189] for p in ("song", "jin")}
    japan = []
    for name, rows in japan_hoards():
        j = japan_numbers(rows)
        japan.append({"hoard": name, "T_h": j["T_h"], "S_h": None if j["S"] != j["S"] else round(j["S"], 5),
                      "Q_h": None if j["Q"] != j["Q"] else round(j["Q"], 4), "ming_share": round(j["ming"], 4),
                      "n": j["total"]})
    japan.sort(key=lambda r: r["T_h"])
    top = read_tsv(RAW / "japan_verify/suzuki1992_table4_top40_transcribed.tsv")[:20]
    ns_top = sum(1 for r in top if r["issuer"] == "北宋")
    # 蓬莱兴无: the entry says the coins run down to Jin and names no Jin coin, so its Jin share is unknown
    jin_not_itemized = {"蓬莱兴无 (叙录 p.369)"}
    jin_shares = [(h["T_h"], h["jin_share"]) for h in usable if h["place"] == "jin" and h["hoard"] not in jin_not_itemized]
    wuzhou = [float(r["cu"]) for r in read_tsv(RAW / "alloy/guangxi_wenji17_tables7_8_transcribed.tsv")
              if r["table"] == "7" and r["site_or_place"] == "梧州元丰钱监" and r["coin"] != "绍兴元宝" and r["cu"]]

    rows_by = {name: rows for name, place, rows, excl in china_hoards()}
    home_counted = list(win["song"])
    shares = {h["hoard"]: late_share(rows_by[h["hoard"]]) for h in home_counted}
    p_min = min(v for v in shares.values() if v is not None)
    home_list = [k for k in PRESENCE_LISTS if k != "北京右安门"]
    home_present = ([h["SS_cast_from_1180"] > 0 for h in home_counted]
                    + [PRESENCE_LISTS[k]["ss_after_1180"] for k in home_list])
    dest = [(h["SS"], h["SS_cast_from_1180"]) for p in ("jin", "xia") for h in win[p]]
    pv = presence_verdict(home_present, p_min, dest)
    # the verdict is read on the type basis, which takes Ganquan Shehegou in with the Xixia hoards
    shares_t = {}
    for h in home_counted:
        n_t, k_t = type_counts(rows_by[h["hoard"]])
        shares_t[h["hoard"]] = (k_t / n_t) if n_t else None
    p_min_t = min(v for v in shares_t.values() if v is not None)
    home_present_t = [bool(v) for v in shares_t.values()]
    dest_t = ([type_counts(rows_by[h["hoard"]]) for p in ("jin", "xia") for h in win[p]]
              + [(n, k) for _, _, n, k, _ in TYPE_BASIS_DEST])
    pv_t = presence_verdict(home_present_t, p_min_t, dest_t)
    grid3c = {True: "B", None: "unread", False: "C"}[pv_t["passed"]]

    def jin_in(rows, keys):
        return any((map_coin(r["label"], r.get("issuer"))[0] or ("", 0))[0] == JIN
                   and any(norm(r["label"]).startswith(k) for k in keys) and r["count"] > 0 for r in rows)
    jin_pre = ([jin_in(rows_by[h["hoard"]], ("正隆", "大定")) for h in home_counted]
               + [bool(PRESENCE_LISTS[k]["jin_before_1198"]) for k in home_list])
    jin_post = ([jin_in(rows_by[h["hoard"]], ("泰和",)) for h in home_counted]
                + [bool(PRESENCE_LISTS[k]["jin_after_1198"]) for k in home_list])
    prob_txt = (f". Destination late share {pv['share']:.3f} against the lowest home share {p_min:.3f}; on the "
                f"rival's premise a share this low has probability {pv['prob']:.4f}" if pv["prob"] is not None else "")

    by, common = vintage_pools(china_hoards())
    xia_counts, liao_counts, jin_counts, song_counts = (by.get(p, {}) for p in ("xia", "liao", "jin", "song"))
    song_pool = pool(song_counts.values())
    outside = {n: sum(c.values()) for n, c in by.get("ns", {}).items()}
    references = {"common stock": (common, COMMON_PLACES), "Southern Song home stock": (song_pool, ("song",))}

    def against(ref, members, place):
        """Each hoard of a place against a reference stock; a hoard pooled in the stock is taken out of it."""
        return {n: segment_ratios(c, without(ref, c) if place in members else ref)
                for n, c in by.get(place, {}).items()}

    read9 = {}
    for rname, (ref, members) in references.items():
        xs = against(ref, members, "xia")
        oth = {p: tally_hoards(against(ref, members, p).values()) for p in ("jin", "song", "liao")}
        n_oth = sum(o["hoards"] for o in oth.values())
        placebo = ((sum(o["hoards_rising"] for o in oth.values()) / n_oth,
                    sum(o["hoards_falling"] for o in oth.values()) / n_oth) if n_oth else None)
        read9[rname] = {"coins": sum(ref.values()), "per_hoard": xs, "xia": tally_hoards(xs.values()),
                        "others": oth, "placebo": placebo,
                        "test": transitions_test(list(xs.values()), placebo=placebo)}
    passed9 = claim_9({k: v["test"] for k, v in read9.items()})
    per_hoard = read9["common stock"]["per_hoard"]
    pooled_segs = segment_ratios(pool(xia_counts.values()), common)
    big_name, big = max(((n, c) for p in COMMON_PLACES for n, c in by.get(p, {}).items()),
                        key=lambda x: sum(x[1].values()))
    no_big = tally_hoards(segment_ratios(c, without(common, big)) for c in xia_counts.values())
    scope = segment_scope(common)
    seg_keys = {lab[0]: keys for lab, keys, _ in XIA_SEGMENTS}

    def seg_sum(c, g):
        return sum(c.get(k, 0.0) for k in seg_keys[g])
    measures = [("E over D, coin counts", lambda c: seg_sum(c, "E") / seg_sum(c, "D") if seg_sum(c, "E") and seg_sum(c, "D") else None, "high"),
                ("G over F, coin counts", lambda c: seg_sum(c, "G") / seg_sum(c, "F") if seg_sum(c, "G") and seg_sum(c, "F") else None, "high"),
                ("share of group A", lambda c: seg_sum(c, "A") / sum(c.values()), "high"),
                ("share of group C", lambda c: seg_sum(c, "C") / sum(c.values()), "high"),
                ("share of group H", lambda c: seg_sum(c, "H") / sum(c.values()), "low")]
    placement = []
    for mname, fn, side in measures:
        xs = {n: fn(c) for n, c in xia_counts.items()}
        row = {"measure": mname, "side": side, "xia": {n: round(v, 4) for n, v in xs.items()}}
        for p, cs in (("jin", jin_counts), ("song", song_counts)):
            ot = [v for v in (fn(c) for c in cs.values()) if v is not None]
            beyond = [sum(1 for o in ot if (o > v if side == "high" else o < v)) for v in xs.values()]
            row[p] = {"hoards": len(ot), "median": round(float(np.median(ot)), 4), "beyond_each_xia_hoard": beyond,
                      "rank_prob": round(rank_prob(list(xs.values()), ot, side), 4)}
        placement.append(row)
    c_ratio = [r for lab, kind, r, x in pooled_segs if lab.startswith("C ")][0]
    b_ratio, b_coins = [(r, x) for lab, kind, r, x in pooled_segs if lab.startswith("B ")][0]
    jin_segs = [segment_ratios(c, song_pool) for c in jin_counts.values()]
    b_step = [sg[2][2] > sg[1][2] for sg in jin_segs if sg[1][2] is not None and sg[2][2] is not None]

    def tally_txt(t):
        return (f"{t['steps_rising']} of {t['steps']} steps, {t['hoards_rising']} of {t['hoards']} hoards with every "
                f"counted step rising")
    ref_txt = []
    for rname, r in read9.items():
        ref_txt.append(
            f"{rname} ({r['coins']:.0f} coins): Xixia {tally_txt(r['xia'])} ("
            + " | ".join(n + ": " + ", ".join(f"{v:.2f}" if v is not None else "-" for _, _, v, _ in segs)
                         for n, segs in r["per_hoard"].items())
            + "); the same steps in the other hoards against the same stock, a hoard pooled in it taken out: "
            + "; ".join(f"{lab} {tally_txt(r['others'][p])}" for p, lab in (("jin", "Jin territory"),
                                                                              ("song", "Southern Song territory"),
                                                                              ("liao", "Liao")))
            + f"; rival's bound for a hoard {r['test']['bound']:.2f}, probability {r['test']['prob']:.3f}")
    need = read9["common stock"]["test"]["hoards_needed"]
    place_txt = "; ".join(
        f"{row['measure']}: Xixia " + ", ".join(f"{v:.3f}" for v in row["xia"].values())
        + "".join(f"; {lab} median {row[p]['median']:.3f} over {row[p]['hoards']} hoards, "
                  f"{'above' if row['side'] == 'high' else 'below'} each Xixia hoard "
                  + ", ".join(str(b) for b in row[p]["beyond_each_xia_hoard"])
                  + f", chance of ranking this {row['side']} {row[p]['rank_prob']:.3f}"
                  for p, lab in (("jin", "Jin territory"), ("song", "Southern Song territory")))
        for row in placement)
    scope_txt = "; ".join(
        f"{s['segment']} ("
        + ", ".join(f"{t['title']} {t['cast'][0]}-{t['cast'][1]} war years {t['war_years']} of {t['years']}"
                    for t in s["titles"])
        + f") {s['war_share_even']:.2f} [{s['war_share_bounds'][0]:.2f}, {s['war_share_bounds'][1]:.2f}]"
        for s in scope)

    def few(p):
        return len(win[p]) < 3

    rival3 = dict(kind="rival", rival_shape="point",
                  rival_premise="the outflow of Song coin is a property of the issuer: what leaves is an unbiased "
                                "sample of its stock, whichever way it goes and whether the edge is open",
                  rival_entailment="in the same window the Southern-to-Northern Song ratio of any destination equals "
                                   "that inside Southern Song territory, rho = 1")
    obj = "; ".join(f"{h['hoard']} ({h['place']}, T_h {h['T_h']}): SS {h['SS']:.0f}, cast 1163-1210 "
                    f"{h['SS_cast_1163_1210']:.0f}, from 1180 {h['SS_cast_from_1180']:.0f}"
                    for p in ("xia", "song") for h in win[p])
    crit = [
        {"name": "B140-1  the quantities on synthetic hoards, and every coin label mapped", "kind": "instrument",
         "passed": all(checks.values()) and all(faults.values()) and len(unmapped) <= 2,
         "detail": "checks " + ", ".join(f"{k} {v}" for k, v in checks.items()) + "; seeded faults caught: "
                   + ", ".join(f"{k} {v}" for k, v in faults.items()) + f"; unmapped labels {len(unmapped)}: "
                   + " | ".join(unmapped) + f"; rows not summing to the printed total {len(sums)}: " + " | ".join(sums)},
        {"name": "B140-2  the top twenty coins in Japanese hoards, recounted", "kind": "known_answer",
         "passed": ns_top == 17,
         "detail": f"Suzuki 1992 table 4: Northern Song {ns_top} of 20 (the secondary figure 18 does not match the "
                   "table). 'Northern Song above 85% in Liaoning Jin hoards': no underlying table, not recomputed"},
        {"name": "B140-3a  Jin territory, rho in the main window, printed", "kind": "own_reading", "passed": None,
         "detail": f"hoards with T_h >= 1204: Jin {len(win['jin'])}, Southern Song {len(win['song'])}; the one Jin "
                   "candidate, Beijing Youanmen (Li Wei 2013), is a scatter in river silt with Taihe coins (T_h >= 1204); "
                   "collectors counted Dading about 4,000, Taihe about 150, Daguan ten-cash about 70, and the types "
                   "they list include no Southern Song coin; a list, not a per-type table. Not a rival criterion: the "
                   "Northern Song denominator is stock Jin and Xixia held before the border, so rho < 1 follows on the "
                   "rival's premise as well"},
        {"name": "B140-3b  the late Southern Song coins, rho_Q below one", "grid": "unread", "passed": None,
         "detail": f"hoards with a per-type table and T_h >= 1204: Southern Song territory {len(win['song'])}, Jin "
                   f"territory {len(win['jin'])}; rho_Q is Jin against home, and the Jin side is empty (the Xixia hoards "
                   f"are read in 3c). Jin-territory hoards in the window with no count by Southern Song type: "
                   + "; ".join(f"{n}, dated {d}: {w}" for n, d, w in WINDOW_JIN_NO_TABLE)
                   + f". The objects: {obj}", **rival3},
        {"name": "B140-3c  coins cast after the border: their share at the destinations against home",
         "kind": "rival", "rival_shape": "point", "grid": grid3c, "passed": pv_t["passed"],
         "rival_premise": rival3["rival_premise"],
         "rival_entailment": "a type cast after the border reaches a destination at its share p of the issuer's "
                             "circulation: among n Southern Song coins at a destination, k late ones with k/n near p",
         "detail": "Verdict on the type basis (Southern Song types first cast 1190-1210 against every type first "
                   "cast to 1210): home hoards with counts " + ", ".join(f"{k} p {v:.3f}" for k, v in shares_t.items())
                   + f"; destinations " + "; ".join(f"{h['hoard']} T_h {h['T_h']}" for p in ("jin", "xia") for h in win[p])
                   + "; " + "; ".join(f"{n} T_h {t}, {c} Southern Song coins, late types {k} ({w})"
                                      for n, t, c, k, w in TYPE_BASIS_DEST)
                   + f". Destination late-type share {pv_t['share']:.3f} over {sum(a for a, _ in dest_t):.0f} coins "
                   + f"against the lowest home share {p_min_t:.3f}; on the rival's premise probability "
                   + (f"{pv_t['prob']:.2e}" if pv_t["prob"] is not None else "n/a")
                   + f". On the casting-year basis (coins cast from 1180), Xixia hoards only: Home hoards in the window: {sum(home_present)} of "
                   f"{len(home_present)} hold them ({len(home_counted)} counted: "
                   + ", ".join(f"{k} p {v:.3f}" for k, v in shares.items())
                   + f"; {len(home_list)} type lists: " + ", ".join(home_list) + "). Destinations with a per-type "
                   "table and T_h >= 1204: " + "; ".join(f"{h['hoard']} T_h {h['T_h']}, {h['SS']:.0f} Southern Song "
                   f"coins, from 1180 {h['SS_cast_from_1180']:.0f}" for p in ("jin", "xia") for h in win[p])
                   + prob_txt
                   + ". Printed, not counted: Beijing Youanmen (T_h >= 1204), a collectors' list with no Southern "
                     "Song type; Sanyuan, Shaanxi (Jin territory, 1983, over 2,100 kg), coins picked from the part "
                     "that went to private hands, among them a Xixia Tianqing (1194) and a Chunxi with back 7 (1180), "
                     "a Southern Song coin cast after the cut, T_h 1194, below the window and with no table; one coin "
                     "is what a cut edge lets through by trade and carriage, not a share. Jin-territory type lists "
                     "that name Southern Song types cast after the cut (dated below the window, no counts): "
                     + "; ".join(f"{n}, dated {d}: {w}" for n, d, w in JIN_LATE_TYPES) + ". "
                     "Jin to Song, printed: Jin coins cast before 1198 (Zhenglong, Dading) in "
                   f"{sum(jin_pre)} of {len(jin_pre)} home hoards, cast after 1198 (Taihe) in {sum(jin_post)}; Jin "
                   "cast little between the end of Dading and Taihe, and Taihe is a ten-cash coin, so this row "
                   "has little power"},
        {"name": "B140-9  Northern Song vintages in Xixia hoards follow the Song-Xia war and peace periods",
         "kind": "rival", "rival_shape": "point", "grid": {True: "B", None: "unread", False: "C"}[passed9],
         "passed": passed9, "rival_premise": rival3["rival_premise"],
         "rival_entailment": "every Northern Song vintage reaches Xixia at its share of the Song stock: the ratio "
                             "of Xixia share to reference-stock share is 1 for every vintage, or falls steadily with "
                             "vintage if the flow simply ended; it never rises from a group of reign titles cast "
                             "mostly in war years to the group cast mostly in peace years after it",
         "detail": "Mapping: " + "; ".join(f"{k} -> {({True: 'B', False: 'C', None: 'unread'})[v]}"
                                           for k, v in MAPPING_B140_9.items())
                   + "; the cell is claimed only if every reference stock gives the same verdict. Counted "
                     "war-to-peace steps (D to E, F to G), by reference stock. " + ". ".join(ref_txt)
                   + f". The hoard is the unit and the steps of one hoard are not separate trials: three hoards give "
                     f"at best 0.125, and {need} hoards all rising would be needed. The common stock without its "
                     f"largest hoard ({big_name}, {sum(big.values()):.0f} coins, "
                     f"{sum(big.values()) / sum(common.values()):.0%} of it): Xixia {tally_txt(no_big)}. "
                     "Hoard by hoard, among the hoards of each home territory: " + place_txt
                   + ". Pooled ratio by segment against the common stock (Xixia coins): " + "; ".join(
                       f"{lab} {r:.2f} ({x:.0f})" if r is not None else f"{lab} none" for lab, kind, r, x in pooled_segs)
                   + ". A segment is a group of reign titles and a coin is dated no finer than its title; war years "
                     "inside each title, then the share of the group's coin cast in war years if each title's coin is "
                     "spread evenly over its years, with the lowest and highest share any spread allows: " + scope_txt
                   + ". The step out of segment B is not counted: B is one coin, the Qingli ten-cash piece "
                     f"({b_coins:.0f} Xixia coin, about {b_coins / b_ratio:.0f} expected at the common stock's share), "
                     "scarce in the north whatever the border did, and that step "
                     f"rises in {sum(b_step)} of {len(b_step)} Jin-territory hoards against the Southern Song home "
                     "stock. The late group (cast 1102-1126) is low in every Xixia hoard: little open "
                     "time before 1127, and after 1127 the route ran through Jin, whose coin bans cut it. Under the "
                     "Song shi account of the trading posts alone (closed from early Jiayou to 1067), Jiayou coin "
                     f"({c_ratio:.2f}) falls in a closed spell; the war and peace reading is taken because a closed post "
                     "without war moved trade into smuggling (Chen Xu 2005). Northern Song coin in hoards sealed "
                     "under the Northern Song, outside both stocks: "
                   + "; ".join(f"{n} {v:.0f}" for n, v in outside.items())},
        {"name": "B140-4  the Sinan ship against the Southern Song stock", "kind": "own_reading", "passed": None,
         "detail": "the published catalogue gives names and variety counts, no coin counts"},
        {"name": "B140-5  Japanese hoards by T_h", "kind": "own_reading", "passed": len(japan) > 0,
         "detail": "; ".join(f"T_h {r['T_h']} S {r['S_h']} Q {r['Q_h']} Ming {r['ming_share']} n {r['n']:.0f} "
                             f"{r['hoard']}" for r in japan)},
        {"name": "B140-6  the share of Jin's own coins in Jin hoards", "kind": "own_reading",
         "passed": len(jin_shares) > 0,
         "detail": "; ".join(f"T_h {t}: {s}" for t, s in sorted(jin_shares, key=lambda x: (x[0] or 0)))
                   + ". Left out: " + ", ".join(sorted(jin_not_itemized)) + ", whose entry names no Jin coin"},
        {"name": "B140-7  coverage: every hoard with a per-type table, its source and its exclusion",
         "kind": "bookkeeping", "passed": len(table) > 0 and all(h["hoard"] for h in table),
         "detail": "叙录 tables, rows against printed totals: " + "; ".join(
                       f"{name} rows {sum(r['count'] for r in xulu_rows(f)):.0f}"
                       + (f", printed {tot}" if tot else ", no total printed") for f, name, tot, _ in XULU)
                   + ". 句容 prints a Northern Song subtotal of 5,384; its rows give 5,043. 迁西长岭峰 rows exceed the "
                     "printed total by 256, the count printed for both 元祐 and 绍圣; 蓬莱, 辉县, 康平 and 东沟 leave "
                     "types without counts (康平 also 13 coins with no reign). "
                   + f"Chinese with a per-type table {len(table)} (excluded {len(table) - len(usable)}); Japanese "
                   f"{len(japan)}; Sinan 0. Opened, types listed without counts, {len(TYPE_LISTS_ONLY)}: "
                   + " | ".join(f"{n}, {pl}, latest {t}: {w}" for n, pl, t, w in TYPE_LISTS_ONLY)},
        {"name": "B140-8  copper by issuer, and the direction selective melting would push", "kind": "own_reading",
         "passed": len(wuzhou) > 0,
         "detail": "median copper: Zhou 2004, Northern Song 500 coins 65.4%, Southern Song 82 coins 56.3%; Wang et al. "
                   f"2005, 70.0% and 63.0%; Wuzhou mint site, {len(wuzhou)} Northern Song coins, "
                   f"{float(np.median(wuzhou)):.1f}%. Northern Song coin is richer "
                   "in copper, so melting by copper content raises S_h, against the prediction; rho_Q cancels it"},
    ]
    config = {"dating": "Jin, Liao and Xixia hoards by their latest coin of an issuer other than Southern Song; "
                        "Southern Song hoards by their latest coin",
              "window_main": [1204, None], "window_dose": [1160, 1189], "cut_stable": 1179,
              "excluded": {k: v for k, v in EXCLUDE.items()}, "original_reports_replace": ["九台卡伦", "顺平安阳小学"],
              "common_stock_places": list(COMMON_PLACES), "reference_stocks": list(references),
              "song_xia_wars": [list(w) for w in XIA_WARS],
              "sato_rows_read_on_the_page": {"/".join(k): list(v) for k, v in SATO_READ_ON_THE_PAGE.items()}}
    vint = {"mapping": {k: {True: "B", False: "C", None: "unread"}[v] for k, v in MAPPING_B140_9.items()},
            "references": {rname: {"coins": r["coins"],
                                   "xia_per_hoard": {n: [None if v is None else round(v, 4) for _, _, v, _ in segs]
                                                     for n, segs in r["per_hoard"].items()},
                                   "xia": r["xia"], "others": r["others"],
                                   "placebo_share_rising_and_falling": [round(x, 4) for x in r["placebo"]],
                                   "bound": r["test"]["bound"], "prob": round(r["test"]["prob"], 6),
                                   "hoards_needed": r["test"]["hoards_needed"], "verdict": r["test"]["passed"]}
                           for rname, r in read9.items()},
            "claimed": passed9,
            "common_stock_without_its_largest_hoard": {"hoard": big_name, "coins": sum(big.values()),
                                                       "share_of_stock": round(sum(big.values()) / sum(common.values()), 4),
                                                       "xia": no_big},
            "pooled_ratio_by_segment": [{"segment": lab, "ratio": None if r is None else round(r, 4), "xia_coins": x}
                                        for lab, kind, r, x in pooled_segs],
            "placement_among_home_hoards": placement, "segments": scope,
            "sealed_under_northern_song_outside_both_stocks": outside}
    return {"stage": "B140", "config": config, "criteria": crit, "hoards": table, "japan": japan,
            "xixia_vintages": vint}


def run() -> int:
    import json
    rec = build_record()
    path = Path(__file__).resolve().parents[1] / "results" / "b140_hoard_vintage.json"
    path.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for c in rec["criteria"]:
        print(f"  {({True: 'PASS', False: 'FAIL', None: 'UNREAD'})[c['passed']]}  {c['name']}")
    print(f"\nwrote {path.name}")
    return 0 if all(c["passed"] is not False for c in rec["criteria"]) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--read", action="store_true")
    a = ap.parse_args()
    if a.paper:
        sys.exit(paper())
    if a.read:
        sys.exit(read())
    if a.run:
        sys.exit(run())
    ap.print_help()


if __name__ == "__main__":
    main()
