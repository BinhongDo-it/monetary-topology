# -*- coding: utf-8 -*-
"""E1: which province administers each institution, from its national code.

**The column the compilation was supposed to carry is empty.** `school_province`
is filled in none of the 2017 to 2021 rows and in a fifth to a quarter of the
2022 to 2024 ones. What is filled, at 98 per cent, is `university_code`, and
the five-digit national code is assigned in blocks by province in
administrative-division order. So the column is derivable from a column that
is there.

**Administering province, not the city the campus stands in**, and the
distinction is load-bearing for what E1 asks. `河北工业大学` stands in Tianjin
and is administered by Hebei, and it is Hebei's candidates who receive its
local preference. The code follows the administrator. A name follows the city
often enough to serve as an anchor and not often enough to serve as the answer.

**The block edges are fitted from anchors and then tested on anchors that were
not used to fit them.** An institution whose name begins with a province or a
provincial capital anchors its code. Half the anchors, taken by whether the
code is even, fit the edges; the other half are predicted and scored. **The
mismatches are printed by name rather than counted**, because the interesting
ones are the institutions whose administrator is not who their name says.

Writes `data/e1_home_province.json`.

    python data/e1_home_province.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "gaokao" / "Gaokao-Compass-11M" / "data"
OUT = ROOT / "data" / "e1_home_province.json"

PROVINCE = ("北京 天津 河北 山西 内蒙古 辽宁 吉林 黑龙江 上海 江苏 浙江 安徽 "
            "福建 江西 山东 河南 湖北 湖南 广东 广西 海南 重庆 四川 贵州 云南 "
            "西藏 陕西 甘肃 青海 宁夏 新疆").split()

CITY = {
    "南京": "江苏", "苏州": "江苏", "徐州": "江苏", "无锡": "江苏",
    "常州": "江苏", "扬州": "江苏", "南通": "江苏", "淮阴": "江苏",
    "杭州": "浙江", "宁波": "浙江", "温州": "浙江", "绍兴": "浙江",
    "嘉兴": "浙江", "湖州": "浙江", "台州": "浙江", "金华": "浙江",
    "武汉": "湖北", "宜昌": "湖北", "襄阳": "湖北", "荆楚": "湖北",
    "西安": "陕西", "咸阳": "陕西", "延安": "陕西", "宝鸡": "陕西",
    "成都": "四川", "绵阳": "四川", "西南石油": None,
    "广州": "广东", "深圳": "广东", "汕头": "广东", "佛山": "广东",
    "暨南": "广东", "华南": "广东", "岭南": "广东", "五邑": "广东",
    "厦门": "福建", "福州": "福建", "泉州": "福建", "集美": "福建",
    "长沙": "湖南", "湘潭": "湖南", "衡阳": "湖南", "吉首": "湖南",
    "哈尔滨": "黑龙江", "齐齐哈尔": "黑龙江", "牡丹江": "黑龙江",
    "长春": "吉林", "延边": "吉林", "北华": "吉林",
    "沈阳": "辽宁", "大连": "辽宁", "鞍山": "辽宁", "渤海": "辽宁",
    "青岛": "山东", "济南": "山东", "烟台": "山东", "潍坊": "山东",
    "曲阜": "山东", "聊城": "山东", "临沂": "山东", "鲁东": "山东",
    "郑州": "河南", "洛阳": "河南", "新乡": "河南", "信阳": "河南",
    "合肥": "安徽", "淮北": "安徽", "安庆": "安徽", "蚌埠": "安徽",
    "南昌": "江西", "赣南": "江西", "井冈山": "江西", "景德镇": "江西",
    "昆明": "云南", "大理": "云南", "曲靖": "云南",
    "南宁": "广西", "桂林": "广西", "柳州": "广西",
    "贵阳": "贵州", "遵义": "贵州", "兰州": "甘肃", "西北师": "甘肃",
    "太原": "山西", "中北": "山西", "石家庄": "河北", "燕山": "河北",
    "华北理工": "河北", "唐山": "河北", "邯郸": "河北",
    "重庆": "重庆", "西南政法": "重庆", "天津": "天津",
    "北京": "北京", "上海": "上海", "海南": "海南", "三亚": "海南",
    "宁夏": "宁夏", "青海": "青海", "新疆": "新疆", "石河子": "新疆",
    "塔里木": "新疆", "拉萨": "西藏", "内蒙古": "内蒙古", "呼伦贝尔": "内蒙古",
}


#: Codes the blocks cannot decide, with the reason. Sichuan's and Chongqing's
#: institutions are interleaved through one range because Chongqing was carved
#: out of Sichuan in 1997 and kept its numbers, so a majority of the nearest
#: anchors there is genuinely split and returns nothing. These three carry no
#: province or city at the front of their names either.
BY_HAND = {10613: "四川", 10614: "四川", 10697: "陕西"}


def anchor_of(name: str):
    for p in sorted(PROVINCE, key=len, reverse=True):
        if name.startswith(p):
            return p
    for c in sorted(CITY, key=len, reverse=True):
        if name.startswith(c):
            return CITY[c]
    # A campus tag names the campus's province, and the tag is where the three
    # Beijing campuses of the mining, petroleum and geosciences universities
    # live: their names begin `中国`, so nothing at the front anchors them, and
    # their codes sit above the range where the blocks mean anything.
    m = re.search(r"[（(]\s*([^）)]{2,6})\s*[）)]", name)
    if m:
        tag = m.group(1)
        for p in sorted(PROVINCE, key=len, reverse=True):
            if tag.startswith(p):
                return p
        for c in sorted(CITY, key=len, reverse=True):
            if tag.startswith(c):
                return CITY[c]
        if tag == "华东":
            return "山东"
    return None


def harvest() -> tuple[dict, dict]:
    """code -> its commonest name, and code -> 985/211 tier, over every file.

    The tier flags are carried on every row of the admission tables and are the
    one field in this compilation that is filled everywhere, so they are read
    here rather than re-walked by each analysis: 71 MB per pass, and the map is
    what every later step joins on anyway.
    """
    seen = collections.defaultdict(collections.Counter)
    tier = {}
    for root, dirs, files in os.walk(SRC):
        for f in files:
            if f != "school-admission.csv":
                continue
            with open(os.path.join(root, f), encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    c = (r.get("university_code") or "").strip()
                    n = re.sub(r"\s+", "", r.get("university_name") or "")
                    if not (re.fullmatch(r"\d{5}", c) and len(n) >= 3):
                        continue
                    seen[int(c)][n] += 1
                    if r.get("is_985") == "1":
                        tier[int(c)] = "985"
                    elif r.get("is_211") == "1":
                        tier.setdefault(int(c), "211")
    return ({c: v.most_common(1)[0][0] for c, v in seen.items()}, tier)


#: The block structure is a property of the low range. Above this the codes run
#: by date of foundation rather than by division, and a neighbour says nothing.
BLOCK_CEILING = 12000
NEIGHBOURS = 9


def fit(anchors: list) -> callable:
    """Majority of the nearest anchors, which one bad anchor cannot flip."""
    a = sorted(x for x in anchors if x[0] < BLOCK_CEILING)

    def predict(code: int):
        if code >= BLOCK_CEILING or not a:
            return None
        near = sorted(a, key=lambda x: (abs(x[0] - code), x[0]))[:NEIGHBOURS]
        tally = collections.Counter(v for _c, v in near)
        top, n = tally.most_common(1)[0]
        return top if n * 2 > len(near) else None
    return predict


def main() -> int:
    names, tier = harvest()
    anchors = [(c, anchor_of(n)) for c, n in names.items() if anchor_of(n)]
    print("institutions with a five-digit code   %d" % len(names))
    print("of those, name anchors its province   %d" % len(anchors))

    # ---- held out: fit on the even codes, score the odd ones --------------
    even = [x for x in anchors if x[0] % 2 == 0]
    odd = [x for x in anchors if x[0] % 2 == 1]
    p = fit(even)
    hit = miss = blank = 0
    wrong = []
    band = collections.defaultdict(lambda: [0, 0, 0])
    for c, want in odd:
        got = p(c)
        key = "under %d" % BLOCK_CEILING if c < BLOCK_CEILING else "at or over"
        if got is None:
            blank += 1
            band[key][2] += 1
        elif got == want:
            hit += 1
            band[key][0] += 1
        else:
            miss += 1
            band[key][1] += 1
            wrong.append((c, names[c], want, got))
    print("\nheld out on the odd codes, fitted on the even")
    print("  scored %d: agree %d, disagree %d, unassigned %d  (%.1f%% of the "
          "assigned agree)" % (len(odd), hit, miss, blank,
                               100 * hit / max(1, hit + miss)))
    for k, (a_, b_, c_) in sorted(band.items()):
        print("    %-12s agree %5d  disagree %4d  unassigned %5d  (%.1f%%)"
              % (k, a_, b_, c_, 100 * a_ / max(1, a_ + b_)))
    print("  the disagreements, by name, most of them institutions whose "
          "administrator is not who their name says:")
    for c, n, want, got in sorted(wrong)[:25]:
        print("    %5d  %-26s name says %-5s block says %s" % (c, n, want, got))
    if len(wrong) > 25:
        print("    ... and %d more, all in the record" % (len(wrong) - 25))

    # ---- the map, fitted on every anchor ---------------------------------
    p = fit(anchors)
    home, unassigned = {}, []
    for c, n in sorted(names.items()):
        # Name first: the code is the administrator of the day it was issued,
        # and two provinces have been created since.
        v = anchor_of(n) or BY_HAND.get(c) or p(c)
        if v:
            home[str(c)] = {
                "name": n, "province": v, "tier": tier.get(c, "other"),
                "by": ("name" if anchor_of(n)
                       else "hand" if c in BY_HAND else "code")}
        else:
            unassigned.append((c, n))
    print("\nassigned %d of %d institutions, %d left unassigned"
          % (len(home), len(names), len(unassigned)))
    print("  first ten unassigned: %s" % [n for _c, n in unassigned[:10]])

    per = collections.Counter(v["province"] for v in home.values())
    print("\ninstitutions per administering province")
    for prov in PROVINCE:
        print("  %-6s %4d" % (prov, per.get(prov, 0)))

    OUT.write_text(json.dumps(
        {"_comment": [
            "code -> administering province, derived from the five-digit "
            "national institution code, whose blocks run by province in "
            "administrative-division order.",
            "Built by data/e1_home_province.py from the school-admission "
            "tables. `by` says whether the institution's own name anchored it "
            "or whether the surrounding block did.",
            "Administering province, not the city the campus stands in: "
            "河北工业大学 stands in Tianjin and is administered by Hebei, and "
            "Hebei's candidates are the ones its local preference reaches.",
            "Held out on the odd codes, fitted on the even: %d agree, %d "
            "disagree, %d unassigned." % (hit, miss, blank)],
         "held_out": {"scored": len(odd), "agree": hit, "disagree": miss,
                      "unassigned": blank,
                      "disagreements": [
                          {"code": c, "name": n, "name_says": w, "block_says": g}
                          for c, n, w, g in sorted(wrong)]},
         "unassigned": [{"code": c, "name": n} for c, n in unassigned],
         "home": home},
        indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print("\nwrote %s  %d bytes" % (OUT, OUT.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
