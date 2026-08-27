# -*- coding: utf-8 -*-
"""E1 gate five: run the statistic on the sample in hand before buying more.

E1 asks how much of a province's admission advantage comes from hosting the
universities rather than from being allocated seats at other people's. Its main
criterion is a difference in differences over within-province ranks, and it
needs one column the C3 panel does not carry: **where each university is**.

Two sources for that column, both already on disk, and neither of them costs
anything:

  code   Guangdong's and Guangxi's tables print the five-digit national
         institution code. Those codes are assigned in blocks by province, in
         administrative-division order, which is checkable rather than assumed:
         151 of the 240 institutions carrying a code have their own province or
         city at the front of their name, and those 151 pin the block edges.
  name   An institution whose name begins with a province or a provincial
         capital is in it. `北京大学`, `厦门大学`, `郑州大学`.

**A code with anchors of two different provinces on either side of it is left
unassigned rather than resolved by a rule**, and the count of those is printed.
The point of this script is the counts, not a reading: what it has to establish
before anything is bought is how many (institution, province) cells the design
actually gets, and how thin the worst province is.

    python data/e1_probe.py
"""
from __future__ import annotations

import collections
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
from parse_gaokao_provincial import (  # noqa: E402
    TABLE, TR, cells, decode_page, sources)

PANEL = ROOT / "data" / "gaokao_provincial.csv"
YEAR = "2015"
DECORATION = re.compile(r"[\s\*★☆▲△◆◇#※·]")

PROVINCE = ("北京 天津 河北 山西 内蒙古 辽宁 吉林 黑龙江 上海 江苏 浙江 安徽 "
            "福建 江西 山东 河南 湖北 湖南 广东 广西 海南 重庆 四川 贵州 云南 "
            "西藏 陕西 甘肃 青海 宁夏 新疆").split()

#: A provincial capital or a city large enough to name a university after, and
#: the province it is in. Only used at the front of a name.
CITY = {
    "南京": "江苏", "苏州": "江苏", "徐州": "江苏", "无锡": "江苏",
    "杭州": "浙江", "宁波": "浙江", "温州": "浙江",
    "武汉": "湖北", "西安": "陕西", "成都": "四川", "广州": "广东",
    "深圳": "广东", "汕头": "广东", "厦门": "福建", "福州": "福建",
    "长沙": "湖南", "湘潭": "湖南", "哈尔滨": "黑龙江", "长春": "吉林",
    "沈阳": "辽宁", "大连": "辽宁", "青岛": "山东", "济南": "山东",
    "烟台": "山东", "郑州": "河南", "合肥": "安徽", "南昌": "江西",
    "昆明": "云南", "南宁": "广西", "桂林": "广西", "贵阳": "贵州",
    "兰州": "甘肃", "太原": "山西", "石家庄": "河北", "燕山": "河北",
    "重庆": "重庆", "天津": "天津", "北京": "北京", "上海": "上海",
    "苏北": "江苏", "西南": None, "西北": None, "东北": None, "华东": None,
    "华中": None, "华南": None, "华北": None, "中南": None,
}


def harvest_codes() -> dict:
    """name -> five-digit national code, from whichever tables print one."""
    out = {}
    for f in sources()[0]:
        page = decode_page(f.read_bytes())
        for tbl in TABLE.findall(page):
            rows = [c for c in (cells(tr) for tr in TR.findall(tbl)) if c]
            if len(rows) < 5:
                continue
            for r in rows:
                for i, c in enumerate(r):
                    m = re.fullmatch(r"\s*(\d{5})\s*", c)
                    if m and i + 1 < len(r):
                        nm = DECORATION.sub("", r[i + 1])
                        if re.search(r"[一-鿿]{3,}", nm) and "分" not in nm:
                            out.setdefault(nm, int(m.group(1)))
            break
    return out


def by_name(nm: str):
    """The province a name states, or None. Regional prefixes state nothing."""
    for p in sorted(PROVINCE, key=len, reverse=True):
        if nm.startswith(p):
            return p
    for c in sorted(CITY, key=len, reverse=True):
        if nm.startswith(c):
            return CITY[c]
    return None


def block_map(code: dict):
    """Assign a province to each code from the anchors around it.

    A code whose nearest anchor below and nearest anchor above name different
    provinces is left out, because the block edge is somewhere inside that gap
    and nothing here says where.
    """
    anchors = sorted((c, by_name(n)) for n, c in code.items() if by_name(n))
    out, ambiguous = {}, []
    for nm, c in sorted(code.items(), key=lambda kv: kv[1]):
        below = [a for a in anchors if a[0] <= c]
        above = [a for a in anchors if a[0] >= c]
        if not below or not above:
            ambiguous.append((nm, c, "outside the anchored range"))
            continue
        lo, hi = below[-1][1], above[0][1]
        if lo == hi:
            out[nm] = lo
        else:
            ambiguous.append((nm, c, "%s below, %s above" % (lo, hi)))
    return out, anchors, ambiguous


def main() -> int:
    code = harvest_codes()
    from_block, anchors, ambiguous = block_map(code)

    rows = [r for r in csv.DictReader(PANEL.open(encoding="utf-8"))
            if r["year"] == YEAR]
    names = {DECORATION.sub("", r["institution"]) for r in rows}

    home, source = {}, collections.Counter()
    for n in sorted(names):
        n_name, n_code = by_name(n), from_block.get(n)
        if n_code and n_name and n_code != n_name:
            source["code and name disagree"] += 1
            continue
        pick = n_name or n_code
        if pick:
            home[n] = pick
            source["name" if n_name else "code"] += 1
        else:
            source["unassigned"] += 1

    print("codes harvested            %d" % len(code))
    print("anchors pinning the blocks %d" % len(anchors))
    print("codes left ambiguous       %d" % len(ambiguous))
    print("institutions in the panel  %d" % len(names))
    print("home province assigned     %d  (%s)"
          % (len(home), dict(source)))

    # ---- the cells the design actually gets -------------------------------
    panel = collections.defaultdict(dict)
    for r in rows:
        panel[(r["province"], r["track"])][
            DECORATION.sub("", r["institution"])] = int(r["score"])
    provinces = sorted({p for p, _t in panel})

    print("\nper province, the cells the difference in differences gets")
    print("  %-6s %-6s %6s %6s %8s %8s"
          % ("prov", "track", "listed", "local", "local also", "away"))
    print("  %-6s %-6s %6s %6s %8s %8s"
          % ("", "", "", "", "elsewhere", "in prov"))
    thin = []
    for p in provinces:
        for t in ("arts", "science"):
            if (p, t) not in panel:
                continue
            here = set(panel[(p, t)])
            local = {n for n in here if home.get(n) == p}
            elsewhere = collections.Counter()
            for q in provinces:
                if q == p or (q, t) not in panel:
                    continue
                for n in local & set(panel[(q, t)]):
                    elsewhere[n] += 1
            usable = sum(1 for n in local if elsewhere[n] >= 1)
            away = sum(1 for n in here if home.get(n) not in (None, p))
            print("  %-6s %-6s %6d %6d %8d %8d"
                  % (p, t, len(here), len(local), usable, away))
            thin.append((usable, p, t))
    thin.sort()
    print("\nthe three thinnest cells: %s" % thin[:3])
    print("provinces with fewer than 3 usable local institutions in a track: %d"
          % sum(1 for u, _p, _t in thin if u < 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
