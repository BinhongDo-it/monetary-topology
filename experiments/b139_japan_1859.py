"""B139: Japan 1859. A treaty wrote one conversion by holder, and opening the ports gave a ring its edge.

A coin's value has a metal part, which every node can weigh and which closes by construction, and a
redemption part, which lives on an edge and need not close. The 1858 treaties made foreign coin pass
"same kind, same weight", so on the edge dollar <-> ichibu the ichibu kept only its metal, while the
edge ichibu <-> koban still ran at face value (four bu to the ryo).

**The ring.** ``s_d`` fine silver in one dollar, ``s_i`` fine silver in one ichibu, ``g_k`` fine gold
in one koban (one ryo = four bu), ``R_w`` the world silver-gold ratio by weight, ``e`` the ichibu a
rule gives for one dollar. Dollar -> ichibu -> koban -> gold sold abroad for silver -> dollars:

    L(e) = e * (1/4) * g_k * R_w / s_d

    by weight (treaty)     e = s_d / s_i              L_w = R_w / R_t,  R_t = 4 s_i / g_k
    by bullion (domestic)  e = 4 s_d / (g_k R_b)      L_b = R_w / R_b
                                                      L_w / L_b = R_b / R_t

``R_t`` is the silver-gold ratio the ichibu carries at face value, ``R_b`` the one on the domestic
bullion market. The scalar price field says ``ln L = 0`` on every ring for every holder.

**B139-1** (block one, ``--paper``) walks the ring coin by coin on synthetic specifications and
checks the walk against the three closed forms; each seeded fault must make it fail. It also carries
the published specifications as two groups, the 1874 Mint table and Koga's assays, and prints how far
apart they put ``ln L_w``: that spread, not the printed digits, is the floor. Writes nothing.

**B139-11 to B139-13** (``--dated``) read the dated statements in ``data/b139_dated_statements.json``:
what a dollar fetched in ichibu at the custom house and from everyone else, month by month and port by
port; the rate at which the custom house took dollars for duties; and the ring at each month's prices,
by holder. The scalar price field says one price for every holder in every month.

Run from the repository root with the project's virtual environment:

    python experiments/b139_japan_1859.py --paper
    python experiments/b139_japan_1859.py --dated [--image-only]
    python experiments/b139_japan_1859.py --run
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

import numpy as np

SEED = 139
TOL = 1e-12
BU_PER_RYO = 4
TROY_OZ_G = 31.1034768
MOMME_G = 3.75

FAULTS = ("gross_weight", "ten_bu_to_ryo", "inverted_world_ratio", "bullion_by_face")


# --------------------------------------------------------------------------
# the closed forms


def closed(c) -> dict:
    s_d, s_i, g_k, R_w, R_b = (c[k] for k in ("s_d", "s_i", "g_k", "R_w", "R_b"))
    R_t = BU_PER_RYO * s_i / g_k
    return {"L_w": R_w / R_t, "L_b": R_w / R_b, "ratio": R_b / R_t, "R_t": R_t}


# --------------------------------------------------------------------------
# the walk: move one lot of metal around the ring, coin by coin


def fine(weight, fineness, fault=None):
    return weight if fault == "gross_weight" else weight * fineness


def walk(c, rule, dollars=1000.0, fault=None) -> float:
    """Dollars back per dollar in, after one trip round the ring under a rule for the first edge."""
    s_d = fine(c["w_d"], c["f_d"], fault)
    s_i = fine(c["w_i"], c["f_i"], fault)
    g_k = fine(c["w_k"], c["f_k"], fault)
    bu = 10 if fault == "ten_bu_to_ryo" else BU_PER_RYO
    R_w = 1.0 / c["R_w"] if fault == "inverted_world_ratio" else c["R_w"]
    if rule == "weight":            # the treaty: silver for silver by weight
        ichibu = dollars * s_d / s_i
    elif rule == "bullion":         # melt the dollar, sell silver for gold at home, take koban at face
        if fault == "bullion_by_face":
            ichibu = dollars * s_d / s_i
        else:
            gold = dollars * s_d / c["R_b"]
            ichibu = gold / g_k * bu
    else:
        raise ValueError(rule)
    koban = ichibu / bu             # one koban is one ryo
    silver_abroad = koban * g_k * R_w
    return silver_abroad / s_d / dollars


def synthetic(rng):
    return {"w_d": rng.uniform(20, 30), "f_d": rng.uniform(0.85, 0.95),
            "w_i": rng.uniform(5, 12), "f_i": rng.uniform(0.80, 0.99),
            "w_k": rng.uniform(2, 15), "f_k": rng.uniform(0.40, 0.90),
            "R_w": rng.uniform(10, 20), "R_b": rng.uniform(5, 16)}


def with_fine(c):
    d = dict(c)
    d.update(s_d=c["w_d"] * c["f_d"], s_i=c["w_i"] * c["f_i"], g_k=c["w_k"] * c["f_k"])
    return d


def rel(a, b):
    return abs(a - b) / max(abs(a), abs(b))


def criterion_ring(fault=None, n=5000) -> dict:
    rng = np.random.default_rng(SEED)
    worst = {"L_w": 0.0, "L_b": 0.0, "ratio": 0.0}
    for _ in range(n):
        c = synthetic(rng)
        cf = closed(with_fine(c))
        Lw, Lb = walk(c, "weight", fault=fault), walk(c, "bullion", fault=fault)
        worst["L_w"] = max(worst["L_w"], rel(Lw, cf["L_w"]))
        worst["L_b"] = max(worst["L_b"], rel(Lb, cf["L_b"]))
        worst["ratio"] = max(worst["ratio"], rel(Lw / Lb, cf["ratio"]))
    # the rival's field: every coin has one price phi; any ring of phi differences sums to zero
    phi = rng.normal(size=4)
    ring = (phi[1] - phi[0]) + (phi[2] - phi[1]) + (phi[3] - phi[2]) + (phi[0] - phi[3])
    return {"passed": max(worst.values()) < TOL and abs(ring) < TOL, "worst": worst,
            "rival_ring": ring}


# --------------------------------------------------------------------------
# the published specifications, two groups (result file R1.1)

# Mint 1874 table (Meiji 7 Dajokan notice, NDL 800341): troy oz per ten ryo, fineness
MINT_1874 = {
    "tenpo_koban": (3.61214 / 10, 0.5675), "ansei_koban": (2.89010 / 10, 0.5697),
    "manen_koban": (1.06894 / 10, 0.5736), "tenpo_ichibu": (11.15435 / 40, 0.9914),
    "ansei_ichibu": (11.12504 / 40, 0.8930), "ansei_nishu": (35.10250 / 80, 0.8446),
}
# Koga, assays of Meiji 22-37: momme per coin, fineness. No own assay of the Ansei koban.
KOGA = {"ansei_ichibu": (2.307 * MOMME_G / TROY_OZ_G, 0.8947),
        "ansei_nishu": (3.628 * MOMME_G / TROY_OZ_G, 0.8476)}
# Dillon 1874, Osaka assays: troy oz per coin, fineness
DILLON = {"ansei_koban": (0.289, 0.5550), "manen_koban": (0.107, 0.5747)}
# Mexican dollar: legal 418 grains at 903 per thousand (Eckfeldt & Du Bois 1842); US Mint 1859 table
DOLLAR = {"legal": (418 / 480, 0.903), "mint_1859": (0.866, 0.901)}
R_W_1859 = 15.19  # Soetbeer 1879 p.131, US Mint 1903 table XVII, MeasuringWorth


def spec_groups():
    """Every combination the sources allow for the opening ring (Ansei koban, Ansei ichibu)."""
    koban = {"Mint 1874": MINT_1874["ansei_koban"], "Dillon": DILLON["ansei_koban"]}
    ichibu = {"Mint 1874": MINT_1874["ansei_ichibu"], "Koga": KOGA["ansei_ichibu"]}
    out = {}
    for kn, (wk, fk) in koban.items():
        for iname, (wi, fi) in ichibu.items():
            for dn, (wd, fd) in DOLLAR.items():
                out[f"koban {kn}, ichibu {iname}, dollar {dn}"] = {
                    "s_d": wd * fd, "s_i": wi * fi, "g_k": wk * fk, "R_w": R_W_1859, "R_b": float("nan")}
    return out


def floor_report():
    rows = {k: math.log(closed(c)["L_w"]) for k, c in spec_groups().items()}
    spread = max(rows.values()) - min(rows.values())
    koban_only = abs(math.log(DILLON["ansei_koban"][0] * DILLON["ansei_koban"][1]
                              / (MINT_1874["ansei_koban"][0] * MINT_1874["ansei_koban"][1])))
    ichibu_only = abs(math.log(KOGA["ansei_ichibu"][0] * KOGA["ansei_ichibu"][1]
                               / (MINT_1874["ansei_ichibu"][0] * MINT_1874["ansei_ichibu"][1])))
    printed = 0.5e-5 / (2.89010 / 10) + 0.05 / 569.7 + 0.5e-5 / (11.12504 / 40) + 0.05 / 893.0
    return rows, spread, koban_only, ichibu_only, printed


# --------------------------------------------------------------------------


def paper() -> int:
    ok = True
    res = criterion_ring()
    ok &= res["passed"]
    w = res["worst"]
    print("B139-1, block one: the ring walked coin by coin against the closed forms, 5000 synthetic sets")
    print(f"  {'PASS' if res['passed'] else 'FAIL'}  worst relative gap L_w {w['L_w']:.1e}, "
          f"L_b {w['L_b']:.1e}, L_w/L_b {w['ratio']:.1e}; rival ring of phi {res['rival_ring']:.1e}")
    for fault in FAULTS:
        r = criterion_ring(fault=fault, n=200)
        ok &= not r["passed"]
        print(f"  fault {fault:22s} {'caught' if not r['passed'] else 'NOT CAUGHT'}  "
              f"worst L_w {r['worst']['L_w']:.2e}, L_b {r['worst']['L_b']:.2e}")
    rows, spread, ko, io, printed = floor_report()
    print("\nThe floor: ln L_w at the opening, every source combination (block two reads the level)")
    for k, v in rows.items():
        print(f"  {v:.5f}  {k}")
    print(f"  spread {spread:.4f}; koban source alone {ko:.4f}, ichibu source alone {io:.4f}; "
          f"printed digits of the 1874 table {printed:.1e}")
    print(f"\nblock one {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------
# block two: the readings (printed, not written; block three writes the record)

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "b139"


def fine_oz(spec):
    w, f = spec
    return w * f


# every source for each coin the rings use: (troy oz per coin, fineness)
SOURCES = {
    "tenpo_koban": {"Mint 1874": MINT_1874["tenpo_koban"]},
    "ansei_koban": {"Mint 1874": MINT_1874["ansei_koban"], "Dillon": DILLON["ansei_koban"]},
    "manen_koban": {"Mint 1874": MINT_1874["manen_koban"], "Dillon": DILLON["manen_koban"]},
    "tenpo_ichibu": {"Mint 1874": MINT_1874["tenpo_ichibu"]},
    "ansei_ichibu": {"Mint 1874": MINT_1874["ansei_ichibu"], "Koga": KOGA["ansei_ichibu"]},
}
R_W = {1859: 15.19, 1860: 15.29}


def ring_logs(ryo_per_dollar, koban_rates, year):
    """ln L over every source combination.

    L = (ryo of face a dollar buys) * (gold per ryo of face) * R_w / s_d. The ichibu holder buys the
    koban that gives most gold per ryo, so each combination takes the best koban on offer.
    """
    vals = []
    for d in DOLLAR.values():
        s_d = fine_oz(d)
        for choice in _combos(koban_rates):
            g = max(fine_oz(spec) / ryo for spec, ryo in choice)
            for r in ryo_per_dollar(s_d):
                vals.append(math.log(r * g * R_W[year] / s_d))
    return min(vals), max(vals)


def _combos(koban_rates):
    out = [[]]
    for coin, ryo in koban_rates.items():
        out = [c + [(spec, ryo)] for c in out for spec in SOURCES[coin].values()]
    return out


def fixed(ryo):
    return lambda s_d: [ryo]


def weight_less(fee, ichibu):
    return lambda s_d: [(1 - fee) * s_d / fine_oz(spec) / BU_PER_RYO for spec in SOURCES[ichibu].values()]


# 3 ryo 1 bu 2 shu, at four bu and sixteen shu to the ryo
TENPO_ZOMASHI = 3 + 1 / 4 + 2 / 16

# the dose path of the ring (result file R1.3); each row governs from its day on
SEGMENTS = [
    ("1859-07-01", "custom house 1 dollar = 2 nishu = 1 bu; tenpo koban 1 ryo 1 bu, ansei koban 1 ryo",
     fixed(0.25), {"tenpo_koban": 1.25, "ansei_koban": 1.0}, 1859),
    ("1859-07-21", "1 dollar = 3 ichibu; koban as above",
     fixed(0.75), {"tenpo_koban": 1.25, "ansei_koban": 1.0}, 1859),
    ("1860-02-22", "zomashi: tenpo koban 3 ryo 1 bu 2 shu, ansei koban 2 ryo 2 bu 3 shu",
     fixed(0.75), {"tenpo_koban": TENPO_ZOMASHI, "ansei_koban": 2.6875}, 1860),
    ("1860-05-30", "Man'en koban at 1 ryo",
     fixed(0.75), {"manen_koban": 1.0, "tenpo_koban": TENPO_ZOMASHI, "ansei_koban": 2.6875}, 1860),
    ("1860-07-01", "official class: by weight less 4% (ansei ichibu)",
     weight_less(0.04, "ansei_ichibu"), {"manen_koban": 1.0}, 1860),
    ("1860-07-01", "everyone else: market; autumn 1860 point 1 dollar = 2 ichibu",
     fixed(0.5), {"manen_koban": 1.0}, 1860),
]

# market prices on one day, mid-December 1859 (Ansei 6.11.20), by holder: the Roju Wakisaka and Harris,
# Bakumatsu gaikoku kankei monjo 30, doc. 39, pp.91-95. The koban leg is the Kanagawa market price, 8 ichibu
# (2 ryo); the dollar leg is the custom-house rate for holders with an exchange quota and the money changers'
# rate for everyone else. The world side comes from the specifications, not from Harris's 12 ichibu in China.
MARKET_1859 = [
    ("custom-house quota: 1 dollar = 3 ichibu; koban at 8 ichibu", fixed(0.75), 2.0),
    ("money changers: 1 dollar = 2 bu to 2 bu 2 shu; koban at 8 ichibu", lambda s_d: [0.5, 0.625], 2.0),
]


def market_logs(rule, koban_ryo, year=1859):
    """ln L with either koban bought at the market price; min and max over both coins and every source."""
    vals = [v for coin in ("tenpo_koban", "ansei_koban") for v in ring_logs(rule, {coin: koban_ryo}, year)]
    return min(vals), max(vals)


# the edge dollar <-> ichibu: every written rule, who it binds, what it writes (R1.2, R1.3)
EDGE_RULES = [
    ("1858 treaty art. 5", "foreigners with Japanese", "same kind, same weight"),
    ("1859-07-01 custom house", "foreigners at the custom house", "1 dollar = 2 nishu = 1 bu"),
    ("1859-07-21 Roju letter", "foreigners at the custom house", "1 dollar = 3 ichibu"),
    ("before 1859-08-26 domestic notice", "Japanese among themselves", "silver of 7.2 momme = 3 ichibu"),
    ("1859-08-26 order", "Japanese among themselves", "by weight"),
    ("1859-12-02 notice", "Japanese among themselves; land tax", "by weight"),
    ("1860-01-20 sanbu-sadame", "every holder, stamped dollars >= 7 momme", "1 dollar = 3 ichibu"),
    ("1860-07-01 letter", "official class", "by weight less 4%"),
    ("1860-07-01 letter", "everyone else", "market price"),
]


def outflow_rows():
    rows = []
    for name, key in (("outflow.json", "records"), ("outflow_verify.json", "new_records")):
        d = json.loads((RAW / "_blockzero" / name).read_text(encoding="utf-8"))
        rows += [r for r in d[key] if r.get("group") == "外流估计"]
    return rows


def read() -> int:
    print("B139 block two: the readings, printed. Nothing is written.\n")
    print("B139-2  the literature chain: 4 dollars -> 12 ichibu -> 3 koban -> dollars")
    for k in ("tenpo_koban", "ansei_koban"):
        for src, spec in SOURCES[k].items():
            for dn, d in DOLLAR.items():
                back = 3 * fine_oz(spec) * R_W[1859] / fine_oz(d)
                print(f"  {k} {src}, dollar {dn}: multiple {back / 4:.3f}")
    print("\nB139-3 / B139-6  ln L by segment, min and max over every source combination")
    for day, what, e, koban, yr in SEGMENTS:
        lo, hi = ring_logs(e, koban, yr)
        print(f"  {day}  ln L {lo:+.4f} .. {hi:+.4f}  width {hi - lo:.4f}  L {math.exp(lo):.3f} .. "
              f"{math.exp(hi):.3f}  {what}")
    print("\nB139-4  the silver-gold ratio, one per edge")
    for k in ("tenpo_ichibu", "ansei_ichibu"):
        for src, spec in SOURCES[k].items():
            for kk, ryo in (("tenpo_koban", 1.0), ("tenpo_koban", 1.25), ("ansei_koban", 1.0)):
                for ks, kspec in SOURCES[kk].items():
                    R_t = BU_PER_RYO * fine_oz(spec) * ryo / fine_oz(kspec)
                    print(f"  R_t {R_t:6.3f}  {k} {src}, {kk} {ks} at {ryo:g} ryo")
    tk = MINT_1874["tenpo_koban"]
    gold_momme = tk[0] * TROY_OZ_G / MOMME_G * tk[1]
    R_b = {"Kaseikoyo 1887": 10.59652, "Ikebe 1896 after Kaheishi, Ansei 2": 10.14,
           "Mikami 1989, 37 momme": 12.33, "Mikami after Inoue 2012, 37.5 momme": 12.5,
           "fold 1858 low: 71.03 momme x hoji chogin 26.05% / tenpo koban gold": 71.03 * 0.2605 / gold_momme,
           "fold 1858 high: 74.24 momme x hoji chogin 26.05% / tenpo koban gold": 74.24 * 0.2605 / gold_momme}
    for k, v in R_b.items():
        print(f"  R_b {v:6.3f}  ln L_b {math.log(R_W[1859] / v):+.4f}  {k}")
    print("\nB139-5  the edge dollar <-> ichibu, written rules by holder")
    for when, who, what in EDGE_RULES:
        print(f"  {when:34s} {who:44s} {what}")
    rows = outflow_rows()
    print(f"\nB139-8  outflow estimates, not combined ({len(rows)})")
    for r in rows:
        print(f"  {r['label'][:120]}")
    return 0


# --------------------------------------------------------------------------
# B139-9: after the edge was cut, the ring opens again, 1601 to 1859

# gold in one ryo of koban, momme (金位并金吹方手續書, 金銀位ノ記); fineness of chogin (田谷 1973, 甲賀)
KOBAN_GOLD = {"慶長": 4.01226, "元禄": 2.730639, "乾字": 2.1073, "正徳": 4.0122, "享保": 4.130966,
              "元文": 2.30, "文政": 1.97443, "保字": 1.70320}
CHOGIN = {"慶長": 0.80, "元禄": 0.64, "宝永": 0.50, "永字": 0.40, "三ツ宝": 0.32, "四ツ宝": 0.20,
          "享保": 0.80, "元文": 0.46, "文政": 0.36, "保字": 0.26}

# the 三貨図彙 rows, with the coin pair each row names; (year, koban, chogin fineness low, high, momme low, high)
SANKA_PAIRS = {"慶長銀": ("慶長", "慶長"), "元字銀": (None, "元禄"), "宝字銀": (None, "宝永"),
               "新銀": (None, "享保"), "新銀(享保銀)": (None, "享保"), "文銀": (None, "元文"),
               "文銀(元文銀)": (None, "元文")}
SANKA_GOLD = {"元禄金": "元禄", "慶長金": "慶長", "慶長元禄金": ("慶長", "元禄"), "慶長金新金": ("慶長", "享保"),
              "元ノ字金・乾金": ("元禄", "乾字"), "文金(元文金)": "元文", "金(元文金)": "元文",
              "金(享保金)": "享保", "金": None, "金壹兩": None, "金一兩": None, "金壹兩(小判)": None,
              "小判一両": None}

# the steps that cut the edge (result file R1.6), for the axis
CUT_STEPS = [(1609, "foreign payments in chogin only"), (1639, "Portuguese ships barred"),
             (1664, "koban exchange licensed, 68 momme"), (1668, "silver to Dutch and Chinese stopped"),
             (1671, "Chinese back to silver"), (1685, "trade ceilings in silver"),
             (1695, "copper substitution"), (1715, "Shotoku new regulation"),
             (1763, "Chinese ships bring gold and silver in"), (1859, "ports open")]


def world_ratio():
    out = {}
    for lo, hi, v in ((1601, 1620, 12.25), (1621, 1640, 14.0), (1641, 1660, 14.5), (1661, 1680, 15.0)):
        for y in range(lo, hi + 1):
            out[y] = v  # Soetbeer 1879, twenty-year European estimates
    lines = (RAW / "ratios" / "measuringworth_goldsilver_1687_1900_export_ratioonly.csv").read_text(
        encoding="utf-8").splitlines()
    for line in lines[2:]:
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[0].isdigit():
            out[int(parts[0])] = float(parts[1])
    return out


def regime(year):
    """(koban, chogin) the Osaka market quoted, by year; transition years flagged."""
    if year < 1820:
        return ("元文", "元文"), year in (1819,)
    if year < 1838:
        return ("文政", "文政"), year in (1820,)
    return ("保字", "保字"), year in (1837, 1838)


def kobe_annual():
    import openpyxl
    wb = openpyxl.load_workbook(RAW / "arm9" / "kobe_kinseidb_data_180301.xlsx", read_only=True)
    by = {}
    for row in wb.worksheets[0].iter_rows(min_row=3, values_only=True):
        y, md, lo, hi = row[1], row[2], row[7], row[8]
        if not y or lo is None:
            continue
        year = int(str(y).rstrip("年"))
        if year == 1859 and md and int(str(md).split("月")[0]) >= 6:
            continue  # from 1859-06-30 the quote is 有合建, and the edge is open
        lo, hi = _num(lo), _num(hi)
        if lo is None:
            continue
        mid = (lo + hi) / 2 if hi is not None else lo
        by.setdefault(year, []).append(mid)
    return {y: (float(np.mean(v)), len(v)) for y, v in by.items() if year_ok(y)}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def year_ok(y):
    return y <= 1859


def sanka_rows():
    import csv
    rows = []
    path = RAW / "sanka" / "sankazui_gold_by_year.tsv"
    for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines(), delimiter="\t"):
        if not r["low_momme"] or "大判" in r["gold_coin"] or "枚" in r["gold_coin"]:
            continue
        y = r["year_ad"][:4]
        if not y.isdigit() or int(y) < 1601 or int(y) > 1786:
            continue
        rows.append((int(y), r["gold_coin"], r["silver_unit"], float(r["low_momme"]), float(r["high_momme"])))
    return rows


def sanka_regime(year, gold, silver):
    """Every (koban, chogin) the row can mean: named coins first, else the coins current that year."""
    silver_key = {"銀": ["慶長"] if year == 1601 else None, "慶長銀": ["慶長"], "元字銀": ["元禄"], "宝字銀": ["宝永"], "新銀": ["享保"],
                  "新銀(享保銀)": ["享保"], "文銀": ["元文"], "文銀(元文銀)": ["元文"],
                  "慶長銀元禄銀": ["慶長", "元禄"], "元禄銀(推定)": ["元禄"],
                  "通用銀(永中・三ツ宝・四ツ宝)": ["永字", "三ツ宝", "四ツ宝"],
                  "通用銀": ["永字", "三ツ宝", "四ツ宝"], "未写明(宝字銀/通用銀期)": ["宝永", "永字", "三ツ宝", "四ツ宝"]
                  }.get(silver)
    g = SANKA_GOLD.get(gold, "?")
    if (g is None or g == "?") and silver_key:
        # gold not named: the koban of the same recoinage as the named chogin
        match = {"慶長": ["慶長"], "元禄": ["元禄"], "宝永": ["元禄", "乾字"], "永字": ["元禄", "乾字"],
                 "三ツ宝": ["元禄", "乾字"], "四ツ宝": ["元禄", "乾字"], "享保": ["正徳", "享保"],
                 "元文": ["元文"]}
        golds = sorted({k for sv in silver_key for k in match[sv]})
        return golds, silver_key
    golds = list(g) if isinstance(g, tuple) else [g]
    return golds, silver_key


def arm9() -> int:
    Rw = world_ratio()
    print("B139-9: ln(R_w / R_b) by year. R_b = gold rate (momme of chogin per ryo) x chogin fineness /")
    print("gold in a ryo. Endo 1931 p.33: the rate is a money rate of chogin, not a weight; every fold row")
    print("stands on reading it as a weight. The unfolded points are printed after.\n")
    print("Official rates:")
    for y, m, k, c in ((1609, 50, "慶長", "慶長"), (1700, 60, "元禄", "元禄")):
        Rb = m * CHOGIN[c] / KOBAN_GOLD[k]
        print(f"  {y}  {m} momme, {k} koban and chogin: R_b {Rb:.2f}, R_w {Rw.get(y, float('nan')):.2f}, "
              f"ln {math.log(Rw[y] / Rb):+.3f}")
    print("\n三貨図彙 rows (1601-1786), every coin pair the row allows:")
    for y, gold, silver, lo, hi in sanka_rows():
        golds, silvers = sanka_regime(y, gold, silver)
        if silvers is None or y not in Rw:
            print(f"  {y}  {lo:g}-{hi:g} momme  {gold} / {silver}: pair or R_w missing")
            continue
        vals = [math.log(Rw[y] / (m * CHOGIN[s] / KOBAN_GOLD[g])) for g in golds for s in silvers for m in (lo, hi)]
        print(f"  {y}  {lo:g}-{hi:g} momme  {gold} / {silver}:  ln {min(vals):+.3f} .. {max(vals):+.3f}")
    print("\nOsaka, 三井 daily book (近世経済データベース), annual mean of the daily mid, to 1859-06-29:")
    kobe = kobe_annual()
    for y in sorted(kobe):
        (k, c), flag = regime(y)
        m, n = kobe[y]
        Rb = m * CHOGIN[c] / KOBAN_GOLD[k]
        print(f"  {y}  {m:6.2f} momme (n {n:3d})  {k}/{c}{' [transition]' if flag else ''}  R_b {Rb:5.2f}  "
              f"R_w {Rw[y]:5.2f}  ln {math.log(Rw[y] / Rb):+.3f}")
    print("\nUnfolded points (a ratio by weight given directly):")
    for y, lo, hi, what in ((1717, 9, 10, "Newton's Mint report: China and Japan, a pound of gold for 9 to 10 of silver"),
                            (1715, 10, 20, "Chinese traders importing gold, 正徳 or so: 1 momme gold for 10-20 silver"),
                            (1855, 10.14, 10.14, "Ikebe 1896 after 貨幣史, Ansei 2"),
                            (1859, 10.59652, 10.59652, "貨政考要 1887, from two-bu and ichibu weights"),
                            (1859, 12.33, 12.5, "幕末外国関係文書: gold 3 momme for silver 37 (or 37.5)")):
        print(f"  {y}  R {lo:g}-{hi:g}  ln {math.log(Rw[y] / hi):+.3f} .. {math.log(Rw[y] / lo):+.3f}  {what}")
    print("\nCut steps on the same axis: " + "; ".join(f"{y} {w}" for y, w in CUT_STEPS))
    return 0


# --------------------------------------------------------------------------
# block three: the record


def fold_series():
    """(year, source, ln low, ln high) for every year B139-9 reads."""
    Rw, out = world_ratio(), []
    for y, m, k, c in ((1609, 50, "慶長", "慶長"), (1700, 60, "元禄", "元禄")):
        v = math.log(Rw[y] / (m * CHOGIN[c] / KOBAN_GOLD[k]))
        out.append((y, "official rate", v, v))
    for y, gold, silver, lo, hi in sanka_rows():
        golds, silvers = sanka_regime(y, gold, silver)
        if silvers is None or y not in Rw:
            continue
        vals = [math.log(Rw[y] / (m * CHOGIN[s] / KOBAN_GOLD[g])) for g in golds for s in silvers for m in (lo, hi)]
        out.append((y, "Sanka zui", min(vals), max(vals)))
    for y, (m, n) in sorted(kobe_annual().items()):
        (k, c), _ = regime(y)
        v = math.log(Rw[y] / (m * CHOGIN[c] / KOBAN_GOLD[k]))
        out.append((y, "Osaka daily", v, v))
    return out


# --------------------------------------------------------------------------
# B139-10. The Osaka gold quote day by day, 1859-1860, against each decree (the Mitsui ledger in the
# Kinsei Keizai Database; dates are those of the ledger, in the Japanese calendar). From Ansei 6.6.1 the
# quote is for "gold on hand", koban and ichibu-ban no longer quoted, so the series after that day is the
# price of the gold unit of account in silver of account, and the koban ring cannot be folded from it.

# (ledger year, month, day, Gregorian date, what, the edge it writes)
DECREES = [
    (1859, "5", 24, "1859-06-24", "two-shu decree; Tenpo koban raised to 1 ryo 1 bu (the later window runs into the switch of 06-30)", "both"),
    (1859, "6", 1, "1859-06-30", "the quote moves from koban to gold on hand", "quote"),
    (1859, "6", 22, "1859-07-21", "1 dollar = 3 ichibu", "dollar-ichibu"),
    (1859, "7", 28, "1859-08-26", "by weight among Japanese", "dollar-ichibu"),
    (1859, "8", 13, "1859-09-09", "Ansei ichibu at the dollar's fineness", "dollar-ichibu"),
    (1859, "11", 9, "1859-12-02", "by weight among Japanese; dollars taken for land tax", "dollar-ichibu"),
    (1859, "12", 28, "1860-01-20", "three-bu stamp on dollars of 7 momme and over", "dollar-ichibu"),
    (1860, "1", 20, "1860-02-11", "zomashi announced", "ichibu-koban"),
    (1860, "2", 1, "1860-02-22", "zomashi in force", "ichibu-koban"),
    (1860, "4", 10, "1860-05-30", "Man'en koban", "ichibu-koban"),
    (1860, "5", 13, "1860-07-01", "market rate for all but the official class", "dollar-ichibu"),
]

# dated prices in the notes of the same ledger (金相場メモ / 備考, quoting the 御買上金控)
LEDGER_PRICES = [
    ("Ansei 6.8.21 (1859-09-17)", "ichibu silver bought by tender, 10,000 ryo", "bids 71.36, 71.38, 71.40 momme per ryo; the day's quote 71.42"),
    ("Ansei 6.9.15", "ichibu silver bought by tender, 15,000 ryo", "bids 71.400, 71.430, 71.435; the day's quote 71.450"),
    ("Ansei 6.10.5 (1859-10-30)", "five oban bought", "30 ryo 2 bu each, paid in ichibu silver"),
    ("Ansei 7.1.9 (1860-01-31)", "five oban bought", "55 ryo 2 bu each, paid in ichibu silver"),
]
OBAN_RYO = (30.5, 55.5)  # the two purchases above

# who could change how much: Bakumatsu gaikoku kankei monjo 30 (Ansei 6.11, December 1859), by document
QUOTAS = [
    ("doc. 91, pp.220-221, Roju and Harris, 11.24 (1859-12-17)", "Kanagawa", "10,000 ichibu a day for all nations together, divided "
     "among them; the mint strikes 15,000 to 16,000 a day, 20,000 at most, for three ports"),
    ("doc. 52, p.132 and doc. 39, p.93", "Nagasaki", "nine ichibu a day per American before the Kanrin-maru brought "
     "200,000 ichibu, four a day after"),
    ("doc. 67, p.164, the Russian commander at Hakodate, 11.22", "Hakodate", "five dollars a day per man by agreement: "
     "500 dollars for a crew of 100"),
    ("doc. 5, pp.10-14, the Hakodate magistrates, 11.16", "Hakodate", "the town does not take dollars; foreign merchants "
     "who drew ichibu at the office change them at a premium for Japanese holding dollars; the office reckons 78,000 "
     "ryo a year for foreigners and 70,000 for townsmen, asks 70,000 and is granted 30,000"),
    ("doc. 91, p.222, Harris, 11.24", "treaty", "same kind, same weight binds the exchange at the port offices; trade "
     "between merchants lies outside it"),
    ("doc. 91, pp.209 and 222, Harris, 11.24", "Kanagawa", "on each koban the Japanese seller and the foreign buyer gain "
     "four ichibu apiece (a koban is worth twelve ichibu abroad)"),
    ("doc. 91, p.213, Harris, 11.24", "by weight", "100 dollars weigh 311 ichibu"),
]


def osaka_days(years=(1859, 1860)):
    """Trading days of the ledger for the given years: (year, month label, day, quote)."""
    import re

    import openpyxl
    wb = openpyxl.load_workbook(RAW / "arm9" / "kobe_kinseidb_data_180301.xlsx", read_only=True)
    days = []
    for row in wb.worksheets[0].iter_rows(min_row=3, values_only=True):
        if not row[1] or int(str(row[1])[:4]) not in years:
            continue
        m = re.match(r"(閏?)(\d+)月(\d+)日", str(row[2]))
        lo, hi = _num(row[7]), _num(row[8])
        if not m or lo is None:
            continue
        days.append((int(str(row[1])[:4]), m.group(1) + m.group(2), int(m.group(3)),
                     (lo + hi) / 2 if hi is not None else lo))
    return days


def first_day_from(days, year, month, day):
    """Index of the first trading day on or after a ledger date; None if the series ends before it."""
    seen = False
    for i, (y, mo, d, _) in enumerate(days):
        if y == year and mo == month:
            seen = True
            if d >= day:
                return i
        elif seen:
            return i
    return None


def quote_steps(days, window):
    """For each decree: mean quote over `window` trading days before and from the day, and the log step.
    A decree whose window is not complete on both sides carries no step."""
    out = []
    for y, mo, d, greg, what, edge in DECREES:
        i = first_day_from(days, y, mo, d)
        if i is None or i < window or i + window > len(days):
            out.append({"decree": greg, "what": what, "edge": edge, "step": None})
            continue
        b = float(np.mean([q for *_, q in days[i - window:i]]))
        a = float(np.mean([q for *_, q in days[i:i + window]]))
        out.append({"decree": greg, "what": what, "edge": edge, "before": round(b, 2), "after": round(a, 2),
                    "step": round(math.log(a / b), 4)})
    return out


def step_noise(days, window):
    """Absolute log step between adjacent windows at every trading day: median, 90th and 95th percentile."""
    v = sorted(abs(math.log(np.mean([q for *_, q in days[i:i + window]]) / np.mean([q for *_, q in days[i - window:i]])))
               for i in range(window, len(days) - window + 1))
    if not v:
        return None
    return {"median": round(v[len(v) // 2], 4), "p90": round(v[int(len(v) * 0.9)], 4), "p95": round(v[int(len(v) * 0.95)], 4),
            "n": len(v)}


def daily_reading(days):
    """The object B139-10 prints, and whether it is complete: every decree with a step at every window."""
    by_w = {w: {"steps": quote_steps(days, w), "noise": step_noise(days, w)} for w in (5, 10, 20)}
    complete = all(st["step"] is not None for w in by_w.values() for st in w["steps"]) and all(
        w["noise"] is not None for w in by_w.values())
    return by_w, complete


def daily() -> int:
    days = osaka_days()
    by_w, complete = daily_reading(days)
    print(f"B139-10  Osaka gold quote, {len(days)} trading days of 1859-1860, range "
          f"{min(q for *_, q in days):.2f} to {max(q for *_, q in days):.2f} momme per ryo\n")
    for w, obj in by_w.items():
        print(f"window {w} trading days; noise {obj['noise']}")
        for st in obj["steps"]:
            print(f"  {st['decree']}  {st.get('before')} -> {st.get('after')}  ln {st['step']}  [{st['edge']}] {st['what']}")
    print("\ncomplete:", complete, "; a series cut to 60 days:", daily_reading(days[:60])[1])
    return 0



# --------------------------------------------------------------------------
# B139-11 to B139-13. Dated statements of what a dollar fetched in ichibu, by holder and by month, July 1859
# to 1861: data/b139_dated_statements.json, one row per statement with its source and the way its figure was
# read. A month is sorted when one side's whole interval lies above the other's, unsorted when the two overlap.
# Two rules date a month, and both are read. "Both sides dated": each side has a statement dated to within two
# months. "Rule in force": everyone else has such a statement, and the custom house's side is whatever written
# rate covers the month, however long it stayed in force. A cell is claimed only where the two rules give the
# same verdict. Later compilations (level = "later compilation", whichever way their figure was read) stay in
# the table and enter no reading.

DATED = Path(__file__).resolve().parents[1] / "data" / "b139_dated_statements.json"
TIGHT_DAYS = 62  # a statement spanning two months or less can date a month; a longer one only widens intervals
TAEL_DAYS = 14   # a koban price in taels is turned at the dollar's Shanghai rates dated within two weeks of it
SOVEREIGN_FINE_OZ = 113.0016 / 480  # troy ounces of fine gold in a sovereign
OTHERS = ("street", "posted", "treasury_jp")
DATED_PORTS = (("Y", "Yokohama"), ("N", "Nagasaki"))
BY_WEIGHT = 311.0  # ichibu per 100 dollars by weight (Harris, doc. 91 p.213, in QUOTAS)
# the revaluation in force 1860-02-22, in ichibu: Ansei koban 2 ryo 2 bu 3 shu, Tenpo koban 3 ryo 1 bu 2 shu
REVALUED = (("new", "ansei_koban", 10.75), ("old", "tenpo_koban", 13.5))


def later(r) -> bool:
    """A later compilation or a modern study: by the kind of source, not by how its figure was read."""
    return r["how"] == "study" or bool(r.get("level"))


def dated_rows(image_only=False, with_study=False):
    rows = []
    for r in json.loads(DATED.read_text(encoding="utf-8"))["statements"]:
        if (later(r) and not with_study) or (image_only and r["how"] == "text"):
            continue
        rows.append(dict(r, low=float(r["low"]), high=float(r["high"])))
    return rows


def _day(d):
    """Days on the calendar, so that a span is the days it covers."""
    return datetime.date(int(d[:4]), int(d[5:7]), int(d[8:10])).toordinal()


def _months(d0, d1):
    y, m, out = int(d0[:4]), int(d0[5:7]), []
    while (y, m) <= (int(d1[:4]), int(d1[5:7])):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def by_month(rows, kinds, port, coin=None):
    """month -> [low, high, statements, statements dated to within two months]."""
    out = {}
    for r in rows:
        if r["kind"] not in kinds or r["port"] != port or (coin is not None and r["coin"] != coin):
            continue
        tight = _day(r["date_to"]) - _day(r["date_from"]) <= TIGHT_DAYS
        for m in _months(r["date_from"], r["date_to"]):
            a = out.setdefault(m, [r["low"], r["high"], 0, 0])
            a[0], a[1], a[2], a[3] = min(a[0], r["low"]), max(a[1], r["high"]), a[2] + 1, a[3] + (1 if tight else 0)
    return out


def _sign(lo, hi):
    return 1 if lo > 0 else (-1 if hi < 0 else None)


def class_gap(rows, port, others=OTHERS, swap=False, both_dated=False):
    """Per month in which the other holders have a dated statement: ln(custom house / others), low and high,
    and the month's sign: +1 when the whole custom-house interval lies above the others', -1 when below, None
    when the two overlap. With ``both_dated`` the custom house's side must have a statement dated to within
    two months as well; without it, a written rate covering the month is enough."""
    cus, oth = by_month(rows, ("custom",), port), by_month(rows, others, port)
    out = []
    for m in sorted(set(cus) & set(oth)):
        if oth[m][3] == 0 or (both_dated and cus[m][3] == 0):
            continue
        a, b = (oth[m], cus[m]) if swap else (cus[m], oth[m])
        lo, hi = math.log(a[0] / b[1]), math.log(a[1] / b[0])
        out.append({"month": m, "custom": cus[m][:2], "others": oth[m][:2], "statements": oth[m][2],
                    "ln_low": lo, "ln_high": hi, "sign": _sign(lo, hi)})
    return out


def duty_gap(rows, port, both_dated=False):
    """The same for the rate at which the custom house took dollars paid in for duties. A month with a
    statement that duties were asked at the market rate, without a figure, carries no sign."""
    oth = by_month(rows, OTHERS, port)
    fig = by_month([r for r in rows if r["low"] > 0], ("duty",), port)
    nofig = by_month([r for r in rows if r["low"] == 0], ("duty",), port)
    out = []
    for m in sorted(set(fig) & set(oth)):
        if oth[m][3] == 0 or (both_dated and fig[m][3] == 0):
            continue
        lo, hi = math.log(fig[m][0] / oth[m][1]), math.log(fig[m][1] / oth[m][0])
        out.append({"month": m, "duty": fig[m][:2], "others": oth[m][:2], "statements": oth[m][2],
                    "ln_low": lo, "ln_high": hi, "sign": None if m in nofig else _sign(lo, hi),
                    "market_rate_asked": m in nofig})
    return out


def by_quarter(gaps):
    """One sign per quarter: None with no sorted month, -1 with any month below, else +1."""
    q = {}
    for g in gaps:
        q.setdefault(f"{g['month'][:4]}Q{(int(g['month'][5:7]) - 1) // 3 + 1}", []).append(g["sign"])
    out = []
    for k in sorted(q):
        s = [x for x in q[k] if x is not None]
        out.append(None if not s else (-1 if min(s) < 0 else 1))
    return out


def sorted_verdict(signs):
    """signs: one entry per dated month, +1 (the holders the rule names fetched more than the others), -1
    (less) or None (not sorted). One price for every holder gives a month no reason to sort either way, so it
    is read as refuted at scale when one side holds more than half of all the dated months, and as standing
    when neither side does. Returns the counts, the verdict (None when no month is dated), the cell, and the
    chance of a split at least that one-sided among the sorted months if each were a coin toss."""
    n, pos, neg = len(signs), sum(1 for s in signs if s == 1), sum(1 for s in signs if s == -1)
    out = {"months": n, "above": pos, "below": neg, "unsorted": n - pos - neg, "prob": None}
    if n == 0:
        return dict(out, passed=None, grid="unread")
    k, m = max(pos, neg), pos + neg
    if m:
        out["prob"] = float(f"{sum(math.comb(m, j) for j in range(k, m + 1)) / 2 ** m:.6g}")
    if 2 * k <= n:
        return dict(out, passed=False, grid="C")
    if neg == 0:
        return dict(out, passed=True, grid="B")
    if pos == 0:
        return dict(out, passed=True, grid="both_unmet")
    return dict(out, passed=True, grid="mixed", grid_split={"B": pos, "both_unmet": neg})


#: What stands in for Shanghai's cash price of the Mexican dollar in taels. No cash quotation dated to a day
#: is on these pages, so every rate of the dollar is used and each is named: a month's extreme quotation, the
#: discount on bank bills payable in Hongkong, and the rates at which accounts turned sums.
PROXIES = ("cash quotation", "bill on Hongkong", "booked in an account")


def tael_rows(rows, day, basis=PROXIES):
    q = [r for r in rows if r["kind"] == "dollar_tael" and r.get("basis", "cash quotation") in basis]
    return [r for r in q if (_day(r["date_to"]) - _day(r["date_from"]) <= 7
                             and min(abs(_day(r["date_from"]) - _day(day)), abs(_day(r["date_to"]) - _day(day))) <= TAEL_DAYS)
            or (_day(r["date_to"]) - _day(r["date_from"]) > 7 and r["date_from"] <= day <= r["date_to"])]


def tael_rate(rows, day, basis=PROXIES):
    """Shanghai taels per dollar around a day: low and high over the quotations dated to a week or less that
    lie within TAEL_DAYS of it, and over any quotation whose span covers the day (a month's extreme whose day
    the source does not give)."""
    q = [r for r in rows if r["kind"] == "dollar_tael" and r.get("basis", "cash quotation") in basis]
    near = [r for r in q if (_day(r["date_to"]) - _day(r["date_from"]) <= 7
                             and min(abs(_day(r["date_from"]) - _day(day)), abs(_day(r["date_to"]) - _day(day))) <= TAEL_DAYS)
            or (_day(r["date_to"]) - _day(r["date_from"]) > 7 and r["date_from"] <= day <= r["date_to"])]
    if not near:
        raise ValueError("no Shanghai dollar rate near " + day)
    return min(r["low"] for r in near), max(r["high"] for r in near), len(near)


def shanghai_dollars(rows, coin=None, basis=PROXIES):
    """Shanghai sale prices of the koban in dollars by month: dollar rows as printed, tael rows at the dollar's
    rate of the same weeks."""
    out = {}
    for r in rows:
        if coin is not None and r["coin"] != coin:
            continue
        if r["kind"] == "abroad":
            lo, hi = r["low"], r["high"]
        elif r["kind"] == "abroad_tael":
            if basis != PROXIES and not tael_rows(rows, r["date_from"], basis):
                continue  # under a narrower basis a tael price with no rate near it is left unturned
            t = tael_rate(rows, r["date_from"], basis)
            lo, hi = r["low"] / t[1], r["high"] / t[0]
        else:
            continue
        for m in _months(r["date_from"], r["date_to"]):
            a = out.setdefault(m, [lo, hi])
            a[0], a[1] = min(a[0], lo), max(a[1], hi)
    return out


def month_rings(rows, port="Y", basis=PROXIES):
    """ln L by month for the holder changing at the custom house and for a holder who gets the others' rate:
    dollars -> ichibu -> koban at the port -> dollars at Shanghai. Port prices that do not name the coin are
    set against every Shanghai price of the month; low and high over the month's statements."""
    cus, oth = by_month(rows, ("custom",), port), by_month(rows, OTHERS, port)
    kb, cost = by_month(rows, ("koban",), port, coin=""), by_month(rows, ("cost",), port, coin="")
    ab, out = shanghai_dollars(rows, basis=basis), []
    for m in sorted(set(kb) | set(cost)):
        if m not in ab:
            continue
        r = {"month": m, "abroad": ab[m]}
        costs = []
        if m in kb and m in cus:
            costs += [kb[m][0] / (cus[m][1] / 100), kb[m][1] / (cus[m][0] / 100)]
        if m in cost:
            costs += cost[m][:2]
        if costs:
            r["custom"] = (math.log(ab[m][0] / max(costs)), math.log(ab[m][1] / min(costs)))
        if m in kb and m in oth:
            c2 = [kb[m][0] / (oth[m][1] / 100), kb[m][1] / (oth[m][0] / 100)]
            r["other"] = (math.log(ab[m][0] / max(c2)), math.log(ab[m][1] / min(c2)))
        out.append(r)
    return out


def coin_rings(rows, port="Y", basis=PROXIES):
    """Where both the port price and the Shanghai price name the coin: ln(Shanghai / port), in dollars."""
    out = []
    for coin in ("new", "old"):
        cost, ab = by_month(rows, ("cost",), port, coin=coin), shanghai_dollars(rows, coin=coin, basis=basis)
        for m in sorted(set(cost) & set(ab)):
            out.append({"month": m, "coin": coin, "port": cost[m][:2], "abroad": ab[m],
                        "ln": (math.log(ab[m][0] / cost[m][1]), math.log(ab[m][1] / cost[m][0]))})
    return out


def metal_in_taels(rows, coin, day):
    """A koban's metal at Shanghai's own prices: its gold at the price of the sovereign, the rest of its weight
    as silver at the price of the dollar. Low and high over the specification sources and the dollar's rates
    near the day."""
    t = tael_rate(rows, day)
    out = []
    for w, f in SOURCES[coin].values():
        for sov in (r for r in rows if r["kind"] == "sovereign_tael"):
            for sv in (sov["low"], sov["high"]):
                for tt in t[:2]:
                    for d in DOLLAR.values():
                        out.append(w * f * sv / SOVEREIGN_FINE_OZ + w * (1 - f) * tt / fine_oz(d))
    return min(out), max(out)


def london_value(coin, year=1859):
    """A koban's gold at the London ratio, in Mexican dollars, over every specification source: low, high."""
    v = [fine_oz(k) * R_W[year] / fine_oz(d) for k in SOURCES[coin].values() for d in DOLLAR.values()]
    return min(v), max(v)


def _r4(v):
    return [round(v[0], 4), round(v[1], 4)]


def _rounded(x):
    """A copy for the record with every float at four decimals; the readings themselves are kept unrounded."""
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _rounded(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_rounded(v) for v in x]
    return x


def holder_reading(rows, basis=PROXIES):
    """The object B139-13 prints: the ring at each month's prices by holder, the ring where the coin is named,
    lots and shipments, the multiple as observers state it, the Shanghai leg, and the ring walked backwards
    after the revaluation. ``basis``: which rates of the dollar in taels turn a koban price in taels into
    dollars."""
    rings = [{"month": r["month"], "shanghai_dollars": list(r["abroad"]),
              "custom_house_holder": list(r["custom"]) if "custom" in r else None,
              "holder_at_the_others_rate": list(r["other"]) if "other" in r else None}
             for r in month_rings(rows, basis=basis)]
    named = [{"month": r["month"], "coin": r["coin"], "ln": list(r["ln"])} for r in coin_rings(rows, basis=basis)]
    lots = [{"date": r["date_from"], "port": r["port"], "multiple": r["high"] / r["low"], "note": r["note"]}
            for r in rows if r["kind"] in ("ship", "lot")]
    stated = [{"from": r["date_from"], "to": r["date_to"], "multiple": r["low"], "holder": r["holder"]}
              for r in rows if r["kind"] == "stated"]
    london, own, after, rates = [], [], [], []
    for coin, key, bu in REVALUED:
        a = shanghai_dollars(rows, coin=coin, basis=basis).get(SHANGHAI_MONTH)
        if not a:
            continue
        lo, hi = london_value(key)
        london.append({"coin": coin, "ln": [math.log(a[0] / hi), math.log(a[1] / lo)]})
        v = bu / (BY_WEIGHT / 100)  # dollars a koban is taken for at its new value, at the weight rate
        lo, hi = london_value(key, 1860)
        # the Shanghai price is the one on these pages, of November 1859; the rule is the one in force from
        # 22 February 1860. No Shanghai price of the koban after that day is on these pages.
        after.append({"coin": coin, "ichibu": bu,
                      "shanghai_price_of": SHANGHAI_MONTH, "rule_in_force_from": ZOMASHI_DAY,
                      "against_shanghai": [math.log(v / a[1]), math.log(v / a[0])],
                      "against_london_value": [math.log(v / hi), math.log(v / lo)]})
    keys = {c: k for c, k, _ in REVALUED}
    sov = [r for r in rows if r["kind"] == "sovereign_tael"]
    for r in rows:
        if r["kind"] == "abroad_tael" and r["coin"]:
            lo, hi = metal_in_taels(rows, keys[r["coin"]], r["date_from"])
            own.append({"date": r["date_from"], "coin": r["coin"],
                        "ln": [math.log(r["low"] / hi), math.log(r["high"] / lo)],
                        "sovereign_rate": [{"holder": s["holder"], "basis": s.get("basis", ""),
                                            "dated": s["date_from"],
                                            "days_from_the_koban_price": abs(_day(s["date_from"]) - _day(r["date_from"]))}
                                           for s in sov]})
    for day in sorted({r["date_from"] for r in rows if r["kind"] == "abroad_tael"}):
        used = tael_rows(rows, day)
        rates.append({"date": day,
                      "rates_used": [{"holder": u["holder"], "basis": u.get("basis", ""), "from": u["date_from"],
                                      "to": u["date_to"], "low": u["low"], "high": u["high"]} for u in used],
                      **{name: (list(tael_rate(rows, day, b)[:2]) if tael_rows(rows, day, b) else None)
                         for name, b in (("every_rate", PROXIES),
                                         ("without_bills_on_hongkong", ("cash quotation", "booked in an account")),
                                         ("cash_quotations_only", ("cash quotation",)))}})
    return {"ring_by_month": rings, "ring_coin_named": named, "lots_and_shipments": lots,
            "multiple_as_stated": stated, "shanghai_against_london_value": london,
            "shanghai_in_its_own_prices": own, "after_the_revaluation": after,
            "shanghai_dollar_in_taels": rates}


def holder_verdict(obj):
    """B139-13 as a flag: every part of the object is there; the ring is open, its whole interval above zero,
    in more than half of the months read for the holder who changes at the custom house; and it sits astride
    zero in more than half of the months read for a holder who gets the others' rate."""
    cus = [r["custom_house_holder"] for r in obj["ring_by_month"] if r["custom_house_holder"]]
    oth = [r["holder_at_the_others_rate"] for r in obj["ring_by_month"] if r["holder_at_the_others_rate"]]
    opened = sum(1 for lo, hi in cus if lo > 0)
    astride = sum(1 for lo, hi in oth if lo <= 0 <= hi)
    whole = all(len(v) > 0 for v in obj.values())
    return {"months_custom_house": len(cus), "open": opened, "months_others": len(oth), "astride_zero": astride,
            "parts_present": whole, "passed": whole and 2 * opened > len(cus) and 2 * astride > len(oth)}


def pooled_gap(rows, **kw):
    return sorted_verdict([g["sign"] for p, _ in DATED_PORTS for g in class_gap(rows, p, **kw)])


def pooled_duty(rows, **kw):
    return sorted_verdict([g["sign"] for p, _ in DATED_PORTS for g in duty_gap(rows, p, **kw)])


def settled(by_rule: dict) -> dict:
    """One verdict from the two dating rules: theirs where they agree, no cell where they differ. A cell whose
    verdict turns on which of the station's own two rules dates a month is not read."""
    cells = {(v["passed"], v["grid"]) for v in by_rule.values()}
    if len(cells) == 1:
        v = next(iter(by_rule.values()))
        return {k: v[k] for k in ("passed", "grid", "grid_split") if k in v}
    return {"passed": None, "grid": "unread"}


SHANGHAI_MONTH = "1859-11"   # the one month with a Shanghai price of the koban by coin
ZOMASHI_DAY = "1860-02-22"
RULES = (("rule in force", False), ("both sides dated", True))


def dated_faults(rows):
    """Inputs that must move each of the three readings. True means the fault was caught."""
    def ours(v):
        return v["passed"] is True and v["grid"] == "B"

    base = pooled_gap(rows)
    gaps = [g for p, _ in DATED_PORTS for g in class_gap(rows, p)]
    over = [g for g in gaps if g["ln_low"] <= 0 <= g["ln_high"]]
    statements = sum(1 for r in rows if r["kind"] in OTHERS and r["port"] in dict(DATED_PORTS))
    # one row at each port read: a planted row at one port alone leaves the other port's months to carry the count
    poison = rows + [dict(rows[0], kind="street", port=p, low=400.0, high=400.0, how="study", coin="",
                          date_from="1859-07-01", date_to="1861-12-31") for p, _ in DATED_PORTS]
    in_table = sum(1 for r in dated_rows(with_study=True) if r["how"] == "study")
    # a compilation whose figure was read on its page image is still a compilation
    seen = [dict(rows[0], kind="street", port=p, low=400.0, high=400.0, how="image", level="later compilation",
                 coin="", date_from="1859-07-01", date_to="1861-12-31") for p, _ in DATED_PORTS]
    table = dated_rows(with_study=True)
    on_image = [r for r in table if r.get("level") and r["how"] != "study"]
    custom_wide = [dict(r, date_from="1859-07-01", date_to="1861-12-31") if r["kind"] == "custom" else r for r in rows]
    wide = [dict(r, date_from="1859-07-01", date_to="1861-12-31") if r["kind"] in OTHERS else r for r in rows]
    asked = rows + [dict(r, low=0.0, high=0.0) for r in rows if r["kind"] == "duty" and r["low"] > 0]
    return {
        "the two classes exchanged": not ours(pooled_gap(rows, swap=True)),
        "the custom house set to the street's 200": not ours(pooled_gap(
            [dict(r, low=200.0, high=200.0) if r["kind"] == "custom" else r for r in rows])),
        "units are months and an overlapping month has no sign": (
            base["months"] == len(gaps) < statements and len(over) > 0 and all(g["sign"] is None for g in over)),
        "a later compilation counted": (not ours(pooled_gap(poison))
                                        and pooled_gap([r for r in poison if r["how"] != "study"]) == base
                                        and in_table > 0 and not any(r["how"] == "study" for r in rows)),
        "a later compilation read on its page image counted": (
            not ours(pooled_gap(rows + seen)) and pooled_gap([r for r in rows + seen if not later(r)]) == base
            and len(on_image) > 0 and not any(later(r) for r in rows)),
        "no dated statement on the custom house's side": (
            pooled_gap(custom_wide, both_dated=True)["months"] == 0
            and pooled_gap(custom_wide, both_dated=True)["passed"] is None
            and pooled_gap(custom_wide)["months"] > 0),
        "a span counted in days of the calendar": _day("1859-03-03") - _day("1859-01-01") == 61,
        "the two dating rules disagreeing leave no cell": settled(
            {"a": {"passed": True, "grid": "B"}, "b": {"passed": False, "grid": "C"}}) == {"passed": None, "grid": "unread"},
        "no dated statement on the others' side": pooled_gap(wide)["months"] == 0 and pooled_gap(wide)["passed"] is None,
        "the duty counter set to the street's 200": not ours(pooled_duty(
            [dict(r, low=200.0, high=200.0) if r["kind"] == "duty" and r["low"] > 0 else r for r in rows])),
        "duties asked at the market rate in every month": pooled_duty(asked)["above"] == 0 and not ours(pooled_duty(asked)),
        "no koban price at the port": not holder_verdict(holder_reading(
            [r for r in rows if r["kind"] not in ("koban", "cost")]))["passed"],
        "everyone handed the custom-house rate": not holder_verdict(holder_reading(
            [dict(r, low=BY_WEIGHT, high=BY_WEIGHT) if r["kind"] in OTHERS else r for r in rows]))["passed"],
    }


def _tally(v):
    s = f"{v['above']} of {v['months']} above, {v['unsorted']} unsorted, {v['below']} below"
    return s + (f" (sign test {v['prob']:.1e})" if v["prob"] is not None else "")


def dated(image_only=False) -> int:
    rows = dated_rows(image_only)
    table = dated_rows(with_study=True)
    print(f"B139-11 to B139-13: {len(table)} dated statements in the table, {len(rows)} read "
          f"({'transcription-only rows and ' if image_only else ''}later compilations left out)")
    for p, name in DATED_PORTS:
        g = class_gap(rows, p)
        print(f"\nB139-11  the dollar in ichibu per 100 dollars, {name}: the custom house against everyone else")
        for x in g:
            print(f"  {x['month']}  custom {x['custom'][0]:5.0f}-{x['custom'][1]:<5.0f} others {x['others'][0]:5.0f}-"
                  f"{x['others'][1]:<5.0f} (n={x['statements']})  ln {x['ln_low']:+.3f} .. {x['ln_high']:+.3f}  "
                  f"{ {1: '+', -1: '-', None: 'overlap'}[x['sign']] }")
        print("  by month:  ", _tally(sorted_verdict([x["sign"] for x in g])))
        print("  by quarter:", _tally(sorted_verdict(by_quarter(g))))
        b = class_gap(rows, p, both_dated=True)
        print("  both sides dated to within two months:", _tally(sorted_verdict([x["sign"] for x in b])),
              "; months", ", ".join(x["month"] for x in b) or "none")
    print("  both ports, rule in force:", pooled_gap(rows))
    print("  both ports, both sides dated:", pooled_gap(rows, both_dated=True))
    print("\nthe government's own counter, Yokohama: what it gave foreigners against what it gave Japanese holders")
    for x in class_gap(rows, "Y", others=("treasury_jp",)):
        print(f"  {x['month']}  foreigners {x['custom'][0]:5.0f}-{x['custom'][1]:<5.0f} Japanese {x['others'][0]:5.0f}-"
              f"{x['others'][1]:<5.0f}  ln {x['ln_low']:+.3f} .. {x['ln_high']:+.3f}")
    for p, name in DATED_PORTS:
        g = duty_gap(rows, p)
        print(f"\nB139-12  the custom house taking dollars in for duties, {name}, against everyone else")
        for x in g:
            print(f"  {x['month']}  duty {x['duty'][0]:5.0f}-{x['duty'][1]:<5.0f} others {x['others'][0]:5.0f}-"
                  f"{x['others'][1]:<5.0f}  ln {x['ln_low']:+.3f} .. {x['ln_high']:+.3f}  "
                  f"{ {1: '+', -1: '-', None: 'no sign'}[x['sign']] }"
                  f"{'  (duties asked at the market rate)' if x['market_rate_asked'] else ''}")
        print("  by month:  ", _tally(sorted_verdict([x["sign"] for x in g])))
        print("  by quarter:", _tally(sorted_verdict(by_quarter(g))))
        b = duty_gap(rows, p, both_dated=True)
        print("  both sides dated to within two months:", _tally(sorted_verdict([x["sign"] for x in b])),
              "; months", ", ".join(x["month"] for x in b) or "none")
    print("  both ports, rule in force:", pooled_duty(rows))
    print("  both ports, both sides dated:", pooled_duty(rows, both_dated=True))
    print("  cells claimed: B139-11", settled({r: pooled_gap(rows, both_dated=b) for r, b in RULES}),
          " B139-12", settled({r: pooled_duty(rows, both_dated=b) for r, b in RULES}))
    obj = holder_reading(rows)
    flag, obj = holder_verdict(obj), _rounded(obj)
    print("\nB139-13  the ring at the prices of each month, Yokohama, coin not named (ln L low .. high)")
    for r in obj["ring_by_month"]:
        print(f"  {r['month']}  Shanghai ${r['shanghai_dollars'][0]:.2f}-{r['shanghai_dollars'][1]:.2f}  "
              f"custom-house holder {r['custom_house_holder']}  holder at the others' rate {r['holder_at_the_others_rate']}")
    for key in ("ring_coin_named", "lots_and_shipments", "multiple_as_stated", "shanghai_against_london_value",
                "shanghai_in_its_own_prices", "after_the_revaluation", "shanghai_dollar_in_taels"):
        print(f"  {key.replace('_', ' ')}:")
        for r in obj[key]:
            print("    ", r)
    print("  flag:", flag)
    print("\nseeded faults:")
    faults = dated_faults(rows)
    for k, v in faults.items():
        print(f"  {'caught' if v else 'NOT CAUGHT'}  {k}")
    return 0 if all(faults.values()) else 1


def build_record() -> dict:
    ring = criterion_ring()
    faults = {f: not criterion_ring(fault=f, n=200)["passed"] for f in FAULTS}
    b1 = ring["passed"] and all(faults.values())

    chain = {f"{k} {src}, dollar {dn}": 3 * fine_oz(spec) * R_W[1859] / fine_oz(d) / 4
             for k in ("tenpo_koban",) for src, spec in SOURCES[k].items() for dn, d in DOLLAR.items()}
    b2 = all(round(v) == 3 for v in chain.values())
    realized = [ring_logs(e, kb, yr) for day, what, e, kb, yr in SEGMENTS if day == "1859-07-21"][0]

    segs = []
    for day, what, e, kb, yr in SEGMENTS:
        lo, hi = ring_logs(e, kb, yr)
        segs.append({"from": day, "rule": what, "ln_L_min": round(lo, 4), "ln_L_max": round(hi, 4),
                     "floor_width": round(hi - lo, 4)})
    b3 = all((s["ln_L_min"] > s["floor_width"]) or (s["ln_L_max"] < -s["floor_width"]) for s in segs)
    market = []
    for what, rule, kr in MARKET_1859:
        lo, hi = market_logs(rule, kr)
        market.append({"holder": what, "ln_L_min": round(lo, 4), "ln_L_max": round(hi, 4)})

    tk = MINT_1874["tenpo_koban"]
    gold_momme = tk[0] * TROY_OZ_G / MOMME_G * tk[1]
    R_b = {"Kaseikoyo 1887": 10.59652, "Ikebe 1896": 10.14, "Mikami 1989, 37 momme": 12.33,
           "Inoue 2012, 37.5 momme": 12.5, "fold, Osaka 1858 low": 71.03 * 0.2605 / gold_momme,
           "fold, Osaka 1858 high": 74.24 * 0.2605 / gold_momme}
    ln_Lb = {k: round(math.log(R_W[1859] / v), 4) for k, v in R_b.items()}
    R_t = {"ansei ichibu, ansei koban at 1 ryo": BU_PER_RYO * fine_oz(MINT_1874["ansei_ichibu"]) / fine_oz(MINT_1874["ansei_koban"]),
           "tenpo ichibu, tenpo koban at 1.25 ryo": BU_PER_RYO * fine_oz(MINT_1874["tenpo_ichibu"]) * 1.25 / fine_oz(MINT_1874["tenpo_koban"])}
    b3 = b3 and all(v > 0.03 for v in ln_Lb.values())

    after_1860 = [r for r in EDGE_RULES if r[0].startswith("1860-07-01")]
    days = osaka_days()
    by_w, daily_ok = daily_reading(days)
    cut_fails = not daily_reading(days[:60])[1]  # a series that stops before the later decrees must not pass
    dollar_steps = {w: max(abs(st["step"]) for st in obj["steps"] if st["edge"] == "dollar-ichibu" and st["step"] is not None)
                    for w, obj in by_w.items()} if daily_ok else {}
    last_koban = [q for y, mo, d, q in days if (y, mo) == (1859, "5")][-1]
    first_onhand = [q for y, mo, d, q in days if (y, mo) == (1859, "6")][0]
    apr = [q for y, mo, d, q in days if (y, mo) == (1860, "4")]
    oban_ln = math.log(OBAN_RYO[1] / OBAN_RYO[0])
    zomashi_ln = math.log(TENPO_ZOMASHI / 1.25)
    series = fold_series()
    pos = sum(1 for _, _, lo, hi in series if lo > 0)
    rows = outflow_rows()

    # B139-11 to B139-13: the dated statements. A seeded fault that is not caught leaves all three unread.
    stm, stm_image = dated_rows(), dated_rows(image_only=True)
    seeds = dated_faults(stm)
    seeds_ok = all(seeds.values())
    gap_by = {rule: {name: class_gap(stm, p, both_dated=b) for p, name in DATED_PORTS} for rule, b in RULES}
    duty_by = {rule: {name: duty_gap(stm, p, both_dated=b) for p, name in DATED_PORTS} for rule, b in RULES}
    v11_by = {rule: pooled_gap(stm, both_dated=b) for rule, b in RULES}
    v12_by = {rule: pooled_duty(stm, both_dated=b) for rule, b in RULES}
    gap, duty = gap_by["rule in force"], duty_by["rule in force"]
    v11, v12 = v11_by["rule in force"], v12_by["rule in force"]
    counter = class_gap(stm, "Y", others=("treasury_jp",))
    obj13 = holder_reading(stm)
    v13 = holder_verdict(obj13)
    # the flag must not turn on taking a bank bill's discount for the cash price of the dollar
    v13_no_bills = holder_verdict(holder_reading(stm, basis=("cash quotation", "booked in an account")))

    def cell(by_rule):
        if not seeds_ok:
            return {"passed": None, "grid": "unread"}
        return settled(by_rule)

    def per_port(gaps, rows_image, fn, both=False):
        return "; ".join(
            f"{name}: {_tally(sorted_verdict([g['sign'] for g in gaps[name]]))}, by quarter "
            f"{_tally(sorted_verdict(by_quarter(gaps[name])))}, on the rows read from page images and ledgers "
            f"{_tally(sorted_verdict([g['sign'] for g in fn(rows_image, p, both_dated=both)]))}"
            for p, name in DATED_PORTS)

    def months_of(gaps):
        return ", ".join(f"{name} {g['month']}" for _, name in DATED_PORTS for g in gaps[name]) or "none"

    def two_rules(v_by):
        a, b = v_by["rule in force"], v_by["both sides dated"]
        same = (a["passed"], a["grid"]) == (b["passed"], b["grid"])
        return ("the two dating rules give one verdict" if same else
                f"the two dating rules differ (rule in force: {a['grid']}; both sides dated: {b['grid']}), "
                "so no cell is claimed")

    r13 = obj13["shanghai_dollar_in_taels"]
    apart13 = _day(ZOMASHI_DAY) - min(_day(r["date_from"]) for r in stm
                                      if r["kind"] == "abroad_tael" and r["date_from"].startswith(SHANGHAI_MONTH))
    sov13 = obj13["shanghai_in_its_own_prices"][0]["sovereign_rate"][0] if obj13["shanghai_in_its_own_prices"] else None

    def unsorted(gaps):
        return ", ".join(f"{name} {g['month']}" for _, name in DATED_PORTS for g in gaps[name] if g["sign"] is None)

    def span(gaps):
        s = [g for name in gaps for g in gaps[name] if g["sign"] is not None]
        return f"{min(g['ln_low'] for g in s):+.3f} to {max(g['ln_high'] for g in s):+.3f}" if s else "none"

    seeds_line = "Seeded faults: " + "; ".join(f"{k}, {'caught' if v else 'NOT CAUGHT'}" for k, v in seeds.items())
    rings13 = obj13["ring_by_month"]

    crit = [
        {"name": "B139-1  the ring walked coin by coin agrees with the three closed forms", "kind": "instrument",
         "passed": b1, "detail": f"5000 synthetic specifications, largest relative gap L_w {ring['worst']['L_w']:.1e}, "
                                 f"L_b {ring['worst']['L_b']:.1e}, L_w/L_b {ring['worst']['ratio']:.1e}; seeded faults caught: "
                                 + ", ".join(f"{k} {v}" for k, v in faults.items())},
        {"name": "B139-2  the literature's chain, 4 dollars to 12 ichibu to 3 koban, returns three times",
         "kind": "known_answer", "passed": b2,
         "detail": "multiple with the Tenpo koban taken at 4 ichibu: " + ", ".join(f"{k} {v:.3f}" for k, v in chain.items())
                   + f". The Tenpo koban had been raised to 1 ryo 1 bu on 1859-06-24; the ring open from 1859-07-21 "
                     f"returns {math.exp(realized[0]):.3f} to {math.exp(realized[1]):.3f}"},
        {"name": "B139-3  every ring of the opening, and the bullion ring, has ln L away from zero",
         "kind": "rival", "grid": "B", "rival_shape": "point", "passed": b3,
         "rival_premise": "each coin has one price phi in a common unit of account, the same for every holder",
         "rival_entailment": "every exchange term is phi(j) - phi(i) in logs, so the ring dollar -> ichibu -> koban -> "
                             "dollar sums to zero whoever writes the rate and for whom",
         "detail": "; ".join(f"{s['from']} {s['ln_L_min']:+.4f}..{s['ln_L_max']:+.4f} (floor {s['floor_width']:.4f})"
                             for s in segs) + "; ln L_b " + ", ".join(f"{k} {v:+.4f}" for k, v in ln_Lb.items())},
        {"name": "B139-4  the silver-gold ratio, one per edge", "kind": "own_reading",
         "passed": bool(R_t) and bool(R_b) and all(v > 0 for v in list(R_t.values()) + list(R_b.values())),
         "detail": "R_t " + ", ".join(f"{k} {v:.3f}" for k, v in R_t.items()) + "; R_b "
                   + ", ".join(f"{k} {v:.3f}" for k, v in R_b.items())
                   + "; the two fold rows read the Osaka quote as a weight of chogin, which Endo 1931 p.33 disputes"},
        {"name": "B139-5  the edge dollar <-> ichibu: written rules by holder", "kind": "own_reading",
         "passed": len(EDGE_RULES) > 0 and len(after_1860) == 2,
         "detail": " | ".join(f"{w}: {who}: {what}" for w, who, what in EDGE_RULES)
                   + f". From 1860-07-01 the edge carries {len(after_1860)} written values by holder. Who could change "
                     "how much in December 1859 (Bakumatsu gaikoku kankei monjo 30): "
                   + " | ".join(f"{where}: {what} ({src})" for src, where, what in QUOTAS)},
        {"name": "B139-6  the dose path of the ring", "kind": "own_reading",
         "passed": len(segs) == len(SEGMENTS) and len(market) == len(MARKET_1859),
         "detail": "; ".join(f"from {s['from']}: {s['rule']}" for s in segs)
                   + ". At market prices on one day, mid-December 1859 (Roju Wakisaka and Harris, Bakumatsu gaikoku "
                     "kankei monjo 30, doc. 39): "
                   + "; ".join(f"{m['holder']}: ln L {m['ln_L_min']:+.3f}..{m['ln_L_max']:+.3f}" for m in market)
                   + ". The written rates of the same date open the ring at "
                   + f"{segs[1]['ln_L_min']:+.3f}..{segs[1]['ln_L_max']:+.3f}"
                   + ". The gold leg at market prices, in logs of ryo per unit of gold from the opening: Kanagawa koban "
                     f"at 2 ryo by 1859-12-13, {math.log(2.0 / 1.25):+.2f}; the oban bought in Osaka, 30 ryo 2 bu on "
                     f"1859-10-30 and 55 ryo 2 bu on 1860-01-31, {oban_ln:+.2f} between the two; the zomashi in force "
                     f"1860-02-22 wrote {zomashi_ln:+.2f} for the Tenpo koban. The market had moved "
                     f"{oban_ln / zomashi_ln:.0%} of that distance on the oban before the zomashi was announced"},
        {"name": "B139-7  the two closings: the silver side on opening day, the gold side from 1860",
         "kind": "own_reading", "passed": segs[0]["ln_L_max"] < 0 and segs[3]["ln_L_max"] < 0,
         "detail": f"silver side (Ansei two-shu): {segs[0]['ln_L_min']:+.3f}..{segs[0]['ln_L_max']:+.3f} on 1859-07-01, "
                   f"withdrawn 1859-07-21 ({segs[1]['ln_L_min']:+.3f}..{segs[1]['ln_L_max']:+.3f}); gold side "
                   f"(zomashi, then Man'en koban): {segs[2]['ln_L_min']:+.3f}..{segs[2]['ln_L_max']:+.3f}, residual "
                   f"after Man'en {segs[3]['ln_L_min']:+.3f}..{segs[3]['ln_L_max']:+.3f}"},
        {"name": "B139-8  outflow estimates, each with its source, not combined", "kind": "bookkeeping",
         "passed": len(rows) > 0 and all(r.get("source") for r in rows),
         "detail": f"{len(rows)} named estimates or statements: " + " | ".join(r["label"] for r in rows)},
        {"name": "B139-9  after the edge was cut the ring stays open, 1601-1859", "kind": "own_reading",
         "passed": len(series) > 0,
         "detail": f"{len(series)} readings of ln(R_w/R_b), {pos} with the whole interval above zero. "
                   + "; ".join(f"{y} {src} {lo:+.3f}..{hi:+.3f}" for y, src, lo, hi in series)
                   + ". The fold reads the Osaka quote as a weight of chogin (Endo 1931 p.33 disputes it); four "
                     "unfolded points, 1717, 1855, 1859 twice: ln +0.20 to +0.52"},
        {"name": "B139-10  the Osaka gold quote day by day across the decrees, 1859-1860", "kind": "own_reading",
         "passed": daily_ok and cut_fails and len(LEDGER_PRICES) > 0,
         "detail": f"{len(days)} trading days, quote {min(q for *_, q in days):.2f} to {max(q for *_, q in days):.2f} "
                   "momme per ryo. Largest step at a decree on the dollar-ichibu edge, in logs: "
                   + ", ".join(f"window {w} days {v:.4f} (median step of the series {by_w[w]['noise']['median']:.4f}, "
                               f"90th percentile {by_w[w]['noise']['p90']:.4f})" for w, v in dollar_steps.items())
                   + ". Steps at ten days: " + "; ".join(f"{st['decree']} {st['step']:+.4f} ({st['what']})"
                                                          for st in by_w[10]["steps"])
                   + f". On 1859-06-30 the quote left the koban for gold on hand: {last_koban:.2f} the day before, "
                     f"{first_onhand:.2f} that day, {math.log(first_onhand / last_koban):+.3f}. In the fourth month of "
                     f"1860, {max(apr):.2f} to {min(apr):.2f} within the month the Man'en koban was issued, "
                     f"{math.log(min(apr) / max(apr)):+.3f}; the ledger's editors put it down to large shipments of "
                     "silver to Edo and the new koban. Prices dated in the same ledger: "
                   + " | ".join(f"{when}: {what}, {how}" for when, what, how in LEDGER_PRICES)
                   + ". The tenders put four ichibu of silver at the day's quote for a ryo of gold on hand to within "
                     "0.1%: the ichibu passed at its face. A series cut to sixty days does not pass: "
                   + str(cut_fails)},
        {"name": "B139-11  what a dollar fetched in ichibu, month by month: the custom house against everyone else",
         "kind": "rival", "rival_shape": "point", **cell(v11_by),
         "rival_premise": "at a port in a month the dollar has one price in ichibu, the same for every holder",
         "rival_entailment": "the rate the custom house gave the holders it changed for and the rate everyone else "
                             "got are one number, so in a month where both are dated the two ranges overlap, and "
                             "where the scatter of the statements sorts a month it sorts it as often one way as "
                             "the other",
         "grid_note": "a month whose two ranges overlap occupies no cell: " + (unsorted(gap) or "none")
                      + "; " + two_rules(v11_by),
         "detail": f"{len(stm)} dated statements read, in ichibu per 100 dollars; later compilations left out by "
                   "the kind of source, however their figures were read. Two rules date a month. Rule in force "
                   "(everyone else has a statement dated to within two months; the custom house's side is the "
                   "written rate covering the month): " + per_port(gap, stm_image, class_gap)
                   + f". Both ports: {_tally(v11)}. Both sides dated to within two months: "
                   + per_port(gap_by["both sides dated"], stm_image, class_gap, True)
                   + f". Both ports: {_tally(v11_by['both sides dated'])}; months "
                   + months_of(gap_by["both sides dated"])
                   + ". Where a month is sorted under the first rule, ln(custom house / others) runs "
                   + span(gap) + ". The government's own counter at Yokohama, what it gave foreigners against what "
                   "it gave Japanese holders: "
                   + ", ".join(f"{g['month']} {g['ln_low']:+.3f}..{g['ln_high']:+.3f}" for g in counter)
                   + ". " + seeds_line},
        {"name": "B139-12  the rate at which the custom house took dollars for duties, against everyone else",
         "kind": "rival", "rival_shape": "point", **cell(v12_by),
         "rival_premise": "at a port in a month the dollar has one price in ichibu, whatever it is tendered for",
         "rival_entailment": "a dollar paid in for duties discharges as many ichibu as a dollar fetches from "
                             "everyone else, so in a month where both are dated the duty rate lies inside the "
                             "others' range, or is sorted as often below it as above",
         "grid_note": "a month with no sign occupies no cell: " + (unsorted(duty) or "none")
                      + "; in the months where a statement says duties were asked at the market rate the sign "
                        "is withheld; " + two_rules(v12_by),
         "detail": "Rule in force (the duty rate is the written rule covering the month, everyone else dated to "
                   "within two months): " + per_port(duty, stm_image, duty_gap)
                   + f". Both ports: {_tally(v12)}. Both sides dated to within two months: "
                   + per_port(duty_by["both sides dated"], stm_image, duty_gap, True)
                   + f". Both ports: {_tally(v12_by['both sides dated'])}; months "
                   + months_of(duty_by["both sides dated"])
                   + ". Where a month is sorted under the first rule, "
                   "ln(duty rate / others) runs " + span(duty) + ". Every statement of the duty rate: "
                   + " | ".join(f"{r['date_from']}..{r['date_to']} {r['port']} "
                                f"{('%g' % r['low']) if r['low'] else 'market rate asked, no figure'} ({r['holder']})"
                                for r in stm if r["kind"] == "duty") + ". " + seeds_line},
        {"name": "B139-13  the ring at each month's prices, by holder", "kind": "own_reading",
         "passed": (v13["passed"] if v13["passed"] == v13_no_bills["passed"] else None) if seeds_ok else None,
         "detail": "dollars to ichibu to koban at Yokohama to dollars at Shanghai, ln L low..high by month. Holder "
                   "changing at the custom house: "
                   + ", ".join(f"{r['month']} {r['custom_house_holder'][0]:+.3f}..{r['custom_house_holder'][1]:+.3f}"
                               for r in rings13 if r["custom_house_holder"])
                   + f" ({v13['open']} of {v13['months_custom_house']} months with the whole range above zero). "
                     "Holder at the others' rate: "
                   + ", ".join(f"{r['month']} {r['holder_at_the_others_rate'][0]:+.3f}..{r['holder_at_the_others_rate'][1]:+.3f}"
                               for r in rings13 if r["holder_at_the_others_rate"])
                   + f" ({v13['astride_zero']} of {v13['months_others']} months astride zero). Where the coin is "
                     "named: " + ", ".join(f"{r['month']} {r['coin']} koban {r['ln'][0]:+.3f}..{r['ln'][1]:+.3f}"
                                           for r in obj13["ring_coin_named"])
                   + ". Lots and shipments, proceeds over cost: "
                   + ", ".join(f"{r['date']} {r['multiple']:.3f}" for r in obj13["lots_and_shipments"])
                   + ". The multiple as stated: "
                   + ", ".join(f"{r['multiple']:g} ({r['holder']})" for r in obj13["multiple_as_stated"])
                   + ". Shanghai's price of the koban against its London value: "
                   + ", ".join(f"{r['coin']} {r['ln'][0]:+.3f}..{r['ln'][1]:+.3f}" for r in obj13["shanghai_against_london_value"])
                   + "; against its metal with gold at the rate an account booked the sovereign at and silver at "
                     "the dollar's rates ("
                   + (f"{sov13['holder']}, dated {sov13['dated']}, {sov13['days_from_the_koban_price']} days from "
                      "the koban's price, the day of the conversion not stated; no market quotation of the "
                      "sovereign is on these pages" if sov13 else "no sovereign rate") + "): "
                   + ", ".join(f"{r['coin']} {r['ln'][0]:+.3f}..{r['ln'][1]:+.3f}" for r in obj13["shanghai_in_its_own_prices"])
                   + ". The dollar in taels that turns the koban's tael price into dollars: "
                   + "; ".join(f"{r['date']} every rate {r['every_rate'][0]:g}..{r['every_rate'][1]:g} ("
                               + ", ".join(f"{u['basis']} {u['low']:g}" + (f"-{u['high']:g}" if u['high'] != u['low'] else "")
                                           for u in r["rates_used"])
                               + "), without the bills on Hongkong "
                               + (f"{r['without_bills_on_hongkong'][0]:g}..{r['without_bills_on_hongkong'][1]:g}"
                                  if r["without_bills_on_hongkong"] else "none")
                               + ", cash quotations only "
                               + (f"{r['cash_quotations_only'][0]:g}..{r['cash_quotations_only'][1]:g}"
                                  if r["cash_quotations_only"] else "none") for r in r13)
                   + f". The flag is the same with the bills left out: {v13['passed'] == v13_no_bills['passed']}"
                   + f". A koban carried in and paid at its new value under the rule in force from {ZOMASHI_DAY}, "
                     f"against its Shanghai price of {SHANGHAI_MONTH}, the one on these pages (the two are {apart13} days "
                     "apart; no Shanghai price after the revaluation is on them): "
                   + ", ".join(f"{r['coin']} {r['against_shanghai'][0]:+.3f}..{r['against_shanghai'][1]:+.3f}"
                               for r in obj13["after_the_revaluation"]) + ". " + seeds_line},
    ]
    config = {"R_w": {"1859": 15.19, "1860": 15.29, "before 1687": "Soetbeer 1879 twenty-year European estimates",
                      "from 1687": "MeasuringWorth"},
              "specifications": "every source kept: koban Mint 1874 or Dillon, ichibu Mint 1874 or Koga, dollar "
                                "legal or US Mint 1859; the floor is the spread between them",
              "koban_gold_momme": KOBAN_GOLD, "chogin_fineness": CHOGIN,
              "osaka_quote": "annual mean of the daily mid, to 1859-06-29",
              "dated_statements": {"table": "data/b139_dated_statements.json", "others": list(OTHERS),
                                   "ports_read": [name for _, name in DATED_PORTS],
                                   "a_statement_dates_a_month_if_it_spans_at_most_days": TIGHT_DAYS,
                                   "tael_rate_within_days": TAEL_DAYS, "ichibu_per_100_dollars_by_weight": BY_WEIGHT,
                                   "revalued_koban_in_ichibu": {c: bu for c, _, bu in REVALUED},
                                   "later_compilations": "in the table, left out of every reading: by the kind of "
                                                         "source (level), however the figure was read (how)",
                                   "dating_rules": {
                                       "rule in force": "everyone else has a statement dated to within the span; "
                                                        "the custom house's side is the written rate covering "
                                                        "the month",
                                       "both sides dated": "each side has a statement dated to within the span",
                                       "cell": "claimed only where the two rules give one verdict"},
                                   "days": "spans counted on the calendar",
                                   "shanghai_dollar_in_taels": "every rate near the day, each named by its basis: "
                                                               "cash quotation, bill on Hongkong, booked in an "
                                                               "account",
                                   "tenpo_koban_zomashi_ryo": TENPO_ZOMASHI}}

    def month_rows(gaps, key):
        return [{"month": g["month"], key: g[key], "others": g["others"], "statements": g["statements"],
                 "ln": _r4((g["ln_low"], g["ln_high"])), "sign": {1: "+", -1: "-", None: "none"}[g["sign"]]}
                | ({"market_rate_asked": True} if g.get("market_rate_asked") else {}) for g in gaps]

    table = dated_rows(with_study=True)
    dated_block = {
        "statements_in_table": len(table), "statements_read": len(stm),
        "statements_read_from_images_and_ledgers": len(stm_image),
        "custom_house_against_others": {name: month_rows(gap[name], "custom") for _, name in DATED_PORTS},
        "custom_house_counts": {**{name: sorted_verdict([g["sign"] for g in gap[name]]) for _, name in DATED_PORTS},
                                "both ports": v11},
        "government_counter_foreigners_against_japanese": month_rows(counter, "custom"),
        "duty_rate_against_others": {name: month_rows(duty[name], "duty") for _, name in DATED_PORTS},
        "duty_counts": {**{name: sorted_verdict([g["sign"] for g in duty[name]]) for _, name in DATED_PORTS},
                        "both ports": v12},
        "both_sides_dated": {
            "custom_house_against_others": {name: month_rows(gap_by["both sides dated"][name], "custom")
                                            for _, name in DATED_PORTS},
            "custom_house_counts": {**{name: sorted_verdict([g["sign"] for g in gap_by["both sides dated"][name]])
                                       for _, name in DATED_PORTS}, "both ports": v11_by["both sides dated"]},
            "duty_rate_against_others": {name: month_rows(duty_by["both sides dated"][name], "duty")
                                         for _, name in DATED_PORTS},
            "duty_counts": {**{name: sorted_verdict([g["sign"] for g in duty_by["both sides dated"][name]])
                               for _, name in DATED_PORTS}, "both ports": v12_by["both sides dated"]}},
        "cells_claimed": {"B139-11": cell(v11_by), "B139-12": cell(v12_by)},
        "later_compilations_read_on_a_page_image": [
            {"ref": r["ref"], "kind": r["kind"], "from": r["date_from"], "to": r["date_to"]}
            for r in table if r.get("level") and r["how"] != "study"],
        "ring_by_holder_flag_without_bills_on_hongkong": v13_no_bills,
        "ring_by_holder": _rounded(obj13), "ring_by_holder_flag": v13, "seeded_faults": seeds}
    return {"stage": "B139", "config": config, "criteria": crit, "segments": segs, "market_1859": market,
            "dated_statements": dated_block,
            "osaka_1859_1860": {str(w): obj for w, obj in by_w.items()},
            "ledger_prices": [{"when": a, "what": b, "price": c} for a, b, c in LEDGER_PRICES],
            "quotas_1859_12": [{"source": a, "where": b, "what": c} for a, b, c in QUOTAS],
            "arm9": [{"year": y, "source": s, "ln_low": round(lo, 4), "ln_high": round(hi, 4)} for y, s, lo, hi in series]}


def run() -> int:
    rec = build_record()
    path = Path(__file__).resolve().parents[1] / "results" / "b139_japan_1859.json"
    path.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for c in rec["criteria"]:
        print(f"  { {True: 'PASS', False: 'FAIL', None: 'UNREAD'}[c['passed']] }  {c['name']}")
    print(f"\nwrote {path.name}")
    return 0 if all(c["passed"] for c in rec["criteria"]) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--arm9", action="store_true")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--dated", action="store_true")
    ap.add_argument("--image-only", action="store_true",
                    help="with --dated: leave out the rows read in transcription only")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.paper:
        sys.exit(paper())
    if a.read:
        sys.exit(read())
    if a.arm9:
        sys.exit(arm9())
    if a.daily:
        sys.exit(daily())
    if a.dated:
        sys.exit(dated(a.image_only))
    if a.run:
        sys.exit(run())
    ap.print_help()


if __name__ == "__main__":
    main()
