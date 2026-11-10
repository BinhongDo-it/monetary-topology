"""B144 arm K: one country's own regional price levels, by group, as its statistics bureau prints them.

The Statistics Bureau of Japan's regional price difference index for 2025 gives every prefecture
an index (national average 100) for the total and for ten groups of the household budget. Arm A
read, on a crowd-sourced table, that inside one country position rows follow the local wage and
rows one writer sets for the whole country do not. Here the same reading is made on the bureau's
own table: how far apart the prefectures stand in each group.

Two groups are priced for the whole country by one schedule: medical care (the national fee
schedule and drug price list) and transport and communication (national fares and tariffs). One
group is the position: housing, which here is rent of rented dwellings.

  B144-K0  instrument    47 prefectures in twelve columns are read, and every column is the one
                         the summary names: its stated highest and lowest prefectures are the
                         argmax and argmin of the parsed column
  B144-K1  known_answer  the summary's own figures come back: the largest ratio of highest to
                         lowest prefecture is housing's, 1.64, and the smallest medical care's, 1.05
  B144-K2  own_reading   housing stands widest of the ten groups, and both groups priced by one
                         national schedule stand among the three narrowest

Run from the repo root:
    python experiments/b144_japan_regions.py
    python experiments/b144_japan_regions.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "b144" / "weights" / "jp_regional_price_index_2025.pdf"
OUT = ROOT / "results" / "b144_japan_regions.json"

PAGE_A, PAGE_B = 9, 10                   # zero-based pages of the annex table
COLS_A = ("総合", "家賃を除く総合", "食料", "住居", "光熱・水道", "家具・家事用品")
COLS_B = ("被服及び履物", "保健医療", "交通・通信", "教育", "教養娯楽", "諸雑費")
GROUPS = COLS_A[2:] + COLS_B
SCHEDULE = ("保健医療", "交通・通信")
POSITION = "住居"
STATEMENT_PAGES = (5, 6, 7)
KNOWN = {"住居": 1.64, "保健医療": 1.05}
PREF = re.compile(r"(北海道|東京都|京都府|大阪府|[一-龥]{2,3}県)")


def tokens(text: str) -> list:
    return re.findall(r"北海道|東京都|京都府|大阪府|[一-龥]{2,3}県|\d+\.\d|\d+", text)


def read_page(text: str, cols: tuple, after: bool) -> dict:
    tok = tokens(text)
    out = {}
    for i, t in enumerate(tok):
        if PREF.fullmatch(t):
            nums = tok[i + 1:i + 13] if after else tok[i - 12:i] if i >= 12 else []
            if len(nums) == 12 and all(re.fullmatch(r"\d+(\.\d)?", x) for x in nums):
                vals = [float(x) for x in nums[0::2]]
                if all("." in x for x in nums[0::2]):
                    out[t] = dict(zip(cols, vals))
    return out


def statements(text: str) -> dict:
    """group -> (highest prefectures, lowest prefecture) as the summary's figure 4-3 names them."""
    out = {}
    starts = sorted((text.find(g + "〔"), g) for g in GROUPS if g + "〔" in text)   # a row starts with its name
    for k, (start, g) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(text)
        found = re.findall(r"〔(.+?)〕", text[start:end])
        if len(found) >= 2:
            out[g] = (found[:-1], found[-1])
    return out


def load() -> dict:
    import pymupdf
    doc = pymupdf.open(PDF)
    a = read_page(doc[PAGE_A].get_text(), COLS_A, after=True)
    b = read_page(doc[PAGE_B].get_text(), COLS_B, after=False)
    table = {p: {**a[p], **b[p]} for p in a if p in b}
    said = re.sub(r"\s+", "", " ".join(doc[i].get_text() for i in STATEMENT_PAGES))
    return {"table": table, "said": statements(said)}


def spread(table: dict) -> dict:
    out = {}
    for g in GROUPS:
        v = np.array([table[p][g] for p in table])
        out[g] = {"max_over_min": float(v.max() / v.min()), "sd_log": float(np.std(np.log(v))),
                  "highest": max(table, key=lambda p: table[p][g]), "lowest": min(table, key=lambda p: table[p][g])}
    return out


def c_k0(data: dict):
    problems = []
    t = data["table"]
    if len(t) != 47:
        problems.append(f"{len(t)} prefectures read, not 47")
    for g, (hi, lo) in data["said"].items():
        if not t:
            break
        top = max(t[p][g] for p in t)
        bottom = min(t[p][g] for p in t)
        if any(t.get(p, {}).get(g) != top for p in hi) or t.get(lo, {}).get(g) != bottom:
            problems.append(f"the column read as {g} does not have the summary's extremes")
    if len(data["said"]) != len(GROUPS):
        problems.append(f"the summary names extremes for {len(data['said'])} groups, not {len(GROUPS)}")
    if t and max(t, key=lambda p: t[p]["総合"]) != "東京都":
        problems.append("the column read as the total does not put Tokyo highest")
    detail = (f"{len(t)} prefectures, {len(COLS_A) + len(COLS_B)} columns; extremes named by the summary for "
              f"{len(data['said'])} groups; " + ("; ".join(problems) if problems else "every column is the one named"))
    return not problems, detail, {"problems": problems}


def c_k1(sp: dict):
    got = {g: round(sp[g]["max_over_min"], 2) for g in KNOWN}
    widest = max(sp, key=lambda g: sp[g]["max_over_min"])
    narrowest = min(sp, key=lambda g: sp[g]["max_over_min"])
    ok = got == KNOWN and widest == POSITION and narrowest == "保健医療"
    detail = (f"largest ratio {widest} {sp[widest]['max_over_min']:.3f}, smallest {narrowest} "
              f"{sp[narrowest]['max_over_min']:.3f}; the summary prints 1.64 and 1.05")
    return ok, detail, {"computed": got}


def c_k2(sp: dict):
    order = sorted(GROUPS, key=lambda g: sp[g]["sd_log"])
    ok = order[-1] == POSITION and all(g in order[:3] for g in SCHEDULE)
    detail = ("groups from narrowest to widest, spread of the log index across prefectures: "
              + "; ".join(f"{g} {sp[g]['sd_log']:.3f} (max/min {sp[g]['max_over_min']:.2f})" for g in order))
    return ok, detail, {"order": order}


KINDS = {"B144-K0": "instrument", "B144-K1": "known_answer", "B144-K2": "own_reading"}
STATEMENTS = {"B144-K0": "Every column read is the one the summary names.",
              "B144-K1": "The summary's own extreme ratios come back from the parsed table.",
              "B144-K2": "Housing stands widest across prefectures, and the groups priced by one national schedule "
                         "among the narrowest."}


def toy() -> dict:
    prefs = ["北海道", "東京都", "京都府", "大阪府"] + [f"{chr(0x4e00 + k)}{chr(0x4e10 + k)}県" for k in range(43)]
    rng = np.random.default_rng(1)
    spreads = {g: 0.03 for g in GROUPS}
    spreads.update({"住居": 0.12, "保健医療": 0.005, "交通・通信": 0.008})
    table = {}
    for k, p in enumerate(prefs):
        row = {g: round(100 * math.exp(spreads[g] * rng.normal()), 1) for g in GROUPS}
        row["総合"], row["家賃を除く総合"] = (110.0 if p == "東京都" else 99.0), 100.0
        table[p] = row
    said = {g: ([max(table, key=lambda p: table[p][g])], min(table, key=lambda p: table[p][g])) for g in GROUPS}
    return {"table": table, "said": said}


def selftest() -> None:
    d = toy()
    assert c_k0(d)[0] and c_k2(spread(d["table"]))[0]
    swapped = toy()
    for p in swapped["table"]:
        r = swapped["table"][p]
        r["住居"], r["食料"] = r["食料"], r["住居"]
    assert not c_k0(swapped)[0], "a column read under the wrong name fails"
    assert not c_k2(spread(swapped["table"]))[0]
    flat = toy()
    for p in flat["table"]:
        flat["table"][p]["保健医療"] = flat["table"][p]["教育"] * 1.3
    assert not c_k2(spread(flat["table"]))[0]
    few = toy()
    few["table"] = dict(list(few["table"].items())[:40])
    assert not c_k0(few)[0]
    page = "別表 北海道 102.4 3 103.2 1 102.5 6 92.6 24 117.8 1 101.6 12 東京都 104.2 1 102.2 3 102.9 3 129.8 1 93.7 46 101.2 16"
    r = read_page(page, COLS_A, after=True)
    assert r["東京都"]["住居"] == 129.8 and r["北海道"]["総合"] == 102.4
    rb = read_page("107.3 1 100.9 5 101.1 4 96.1 21 98.8 11 103.5 2 北海道", COLS_B, after=False)
    assert rb["北海道"]["諸雑費"] == 103.5
    s = statements("食料〔沖縄県〕「教育」より高い。〔長野県〕低い。住居〔東京都〕高い。〔岡山県〕低い。教育〔大阪府〕高い。〔富山県〕低い。")
    assert s["教育"] == (["大阪府"], "富山県"), "a group named inside another row's sentence does not start a row"
    assert s["食料"] == (["沖縄県"], "長野県") and s["住居"] == (["東京都"], "岡山県")
    print("selftest ok: the readers return what the page says, and every flag fails on its planted input")


def main() -> int:
    data = load()
    sp = spread(data["table"]) if len(data["table"]) == 47 else {}
    res = {"B144-K0": c_k0(data)}
    if sp:
        res["B144-K1"] = c_k1(sp)
        res["B144-K2"] = c_k2(sp)
    for n, (p, d, _) in res.items():
        print(f"{'PASS' if p else 'FAIL'} {n} [{KINDS[n]}]: {d}")
    rec = {"stage": "B144", "diagnostic_only": True,
           "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
           "criteria": [{"name": n, "kind": KINDS[n], "passed": bool(p), "statement": STATEMENTS[n], "detail": d}
                        for n, (p, d, _) in res.items()],
           "objects": {"table": data["table"], "spread": {g: {k: (round(v, 4) if isinstance(v, float) else v)
                                                              for k, v in s.items()} for g, s in sp.items()},
                       "summary_extremes": data["said"]},
           "config": {"pdf": "data/raw/b144/weights/jp_regional_price_index_2025.pdf",
                      "fetched_by": "experiments/b144_fetch.py --only weights", "columns": list(COLS_A + COLS_B),
                      "schedule_groups": list(SCHEDULE), "position_group": POSITION, "known": KNOWN}}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-K0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
    else:
        sys.exit(main())
