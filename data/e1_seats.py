# -*- coding: utf-8 -*-
"""E1: reduce the enrolment plans to seats by year, province and administrator.

**Seats rather than lines.** E1-2 established that a filing line is an
equilibrium quantity: seats set aside for local candidates push it down and
local candidates preferring a nearby campus push it up, and no scaling of the
line separates the two. A seat count is the allocation itself. It is what the
plan says before anybody applies, so nothing about demand enters it.

**Written as a cache because the source is 725 MB in 227 files** and a full
pass does not fit in one call. One year is processed per invocation and its
result is appended, so the table can be built in pieces and rebuilt from any
point. Nothing is deleted: a year already present is skipped unless `--redo`.

The reduction is to `(year, province, category, batch, institution)` with the
seats summed, which is small enough to keep and general enough that the later
questions do not need the 725 MB again.

    python data/e1_seats.py --year 2017
    python data/e1_seats.py --all          # one year at a time, resumable
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "gaokao" / "Gaokao-Compass-11M" / "data"
MAP = ROOT / "data" / "e1_home_province.json"
CACHE = ROOT / "data" / "cache" / "e1"
OUT = CACHE / "seats_%s.csv"

#: The province directory names the compilation uses, to the Chinese name.
PINYIN = {
    "anhui": "安徽", "beijing": "北京", "chongqing": "重庆", "fujian": "福建",
    "gansu": "甘肃", "guangdong": "广东", "guangxi": "广西", "guizhou": "贵州",
    "hainan": "海南", "hebei": "河北", "heilongjiang": "黑龙江", "henan": "河南",
    "hubei": "湖北", "hunan": "湖南", "jiangsu": "江苏", "jiangxi": "江西",
    "jilin": "吉林", "liaoning": "辽宁", "neimenggu": "内蒙古",
    "ningxia": "宁夏", "qinghai": "青海", "shaanxi": "陕西", "shandong": "山东",
    "shanghai": "上海", "shanxi": "山西", "sichuan": "四川", "tianjin": "天津",
    "xinjiang": "新疆", "xizang": "西藏", "yunnan": "云南", "zhejiang": "浙江",
    "xianggang": "香港", "aomen": "澳门", "taiwan": "台湾",
}


def home_by_name() -> tuple[dict, dict]:
    """name -> administering province, and name -> 985/211 flag, from the map.

    The enrolment plans carry no institution code before 2022, so the join runs
    on the name. Both tables come from one compiler, so the strings match; a
    name the map does not hold is counted rather than guessed at.
    """
    m = json.loads(MAP.read_text(encoding="utf-8"))["home"]
    return ({v["name"]: v["province"] for v in m.values()},
            {v["name"]: code for code, v in m.items()})


def one_year(year: str, home: dict, redo: bool) -> str:
    out = Path(str(OUT) % year)
    if out.exists() and not redo:
        return "%s already built, %d bytes" % (out.name, out.stat().st_size)
    ydir = SRC / year
    if not ydir.is_dir():
        return "%s has no directory" % year
    agg = collections.Counter()
    seen_names, missing = set(), collections.Counter()
    for pdir in sorted(os.listdir(ydir)):
        f = ydir / pdir / "enrollment-plan.csv"
        if not f.is_file():
            continue
        prov = PINYIN.get(pdir, pdir)
        with f.open(encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                n = (r.get("university_name") or "").strip()
                c = (r.get("plan_count") or "").strip()
                if not n or not c.isdigit():
                    continue
                seen_names.add(n)
                if n not in home:
                    missing[n] += int(c)
                agg[(prov, (r.get("category") or "").strip(),
                     (r.get("batch") or "").strip(), n)] += int(c)
    CACHE.mkdir(parents=True, exist_ok=True)
    lines = ["year,province,category,batch,institution,home,seats"]
    for (prov, cat, batch, n), seats in sorted(agg.items()):
        lines.append("%s,%s,%s,%s,%s,%s,%d"
                     % (year, prov, cat, batch, n.replace(",", "，"),
                        home.get(n, ""), seats))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    total = sum(agg.values())
    unknown = sum(missing.values())
    return ("%s: %d rows, %d seats, %d institutions, %d seats at %d "
            "institutions with no administering province (%.1f%%)"
            % (year, len(agg), total, len(seen_names), unknown, len(missing),
               100 * unknown / max(1, total)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    years = a.year or (sorted(x for x in os.listdir(SRC) if x.isdigit())
                       if a.all else [])
    if not years:
        print("give --year YYYY or --all")
        return 2
    home, _flag = home_by_name()
    print("map holds %d institution names" % len(home))
    for y in years:
        print("  " + one_year(y, home, a.redo))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
