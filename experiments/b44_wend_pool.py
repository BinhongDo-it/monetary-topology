# -*- coding: utf-8 -*-
"""文德汉萨拆解的第二步：把三个窗口各自合并，让最薄那几个港也可判（第 13 条第 1 步）。
并做「剥三个」对「剥五个」的稳健性 —— Anklam / Demmin 是跑前登记的外推，
它们进不进那个集合不该改变结论，本节把两种都印出来。"""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
CTY = D.pop("__country__"); D.pop("__meta__")

WEND = ["Lübeck", "Rostock", "Hamburg", "Kiel", "Stralsund", "Wismar", "Greifswald", "Anklam", "Demmin"]
SEG = [("前 1630-44", 1630, 1644), ("豁免 1660-1709", 1660, 1709), ("后 1720-79", 1720, 1779)]
P = collections.defaultdict(lambda: [0, 0])
for k, v in D.items():
    nm, y = k.rsplit("|", 1); y = int(y)
    for s, a, b in SEG:
        if a <= y <= b:
            c = P[(nm, s)]; c[0] += v[1]; c[1] += v[2]
def f(c, lo=150):
    return "%.3f" % (c[1] / c[0]) if c[0] >= lo else "·"

print("【九个成员，三段各自合并】  n<150 印 ·")
print("%-12s %s   %s" % ("籍港", "".join("%22s" % s[0] for s in SEG), "当时归属"))
OWN = {"Lübeck": "帝国自由市，从不属瑞典", "Rostock": "梅克伦堡，从不属瑞典",
       "Hamburg": "帝国自由市，从不属瑞典", "Kiel": "荷尔斯泰因，从不属瑞典",
       "Stralsund": "瑞属波美拉尼亚 1648-1815", "Wismar": "瑞典 1648-1803",
       "Greifswald": "瑞属波美拉尼亚 1648-1815", "Anklam": "瑞属波美拉尼亚 1648-1720",
       "Demmin": "瑞属波美拉尼亚 1648-1720"}
for nm in WEND:
    cells = []
    for s, _, _ in SEG:
        c = P[(nm, s)]
        cells.append("%s (n=%d)" % (f(c), c[0]))
    print("%-12s %s   %s" % (nm, "".join("%22s" % x for x in cells), OWN[nm]))

THREE = {"Stralsund", "Wismar", "Greifswald"}
FIVE = THREE | {"Anklam", "Demmin"}
print("\n【稳健性：剥三个 对 剥五个】")
print("%-22s %22s %22s %22s" % ("", "前 1630-44", "豁免 1660-1709", "后 1720-79"))
for lab, drop in [("原组（九个全在）", set()), ("剥三个后剩下的", THREE), ("剥五个后剩下的", FIVE),
                  ("被剥掉的三个", None), ("被剥掉的五个", "F")]:
    cells = []
    for s, _, _ in SEG:
        c = [0, 0]
        for nm in WEND:
            if drop is None:
                keep = nm in THREE
            elif drop == "F":
                keep = nm in FIVE
            else:
                keep = nm not in drop
            if keep:
                x = P[(nm, s)]; c[0] += x[0]; c[1] += x[1]
        cells.append("%s (n=%d)" % (f(c), c[0]))
    print("%-22s %s" % (lab, "".join("%22s" % x for x in cells)))
# 对照：尼德兰与瑞典本土，同三段
for lab, sel in [("对照 尼德兰籍", lambda n: CTY.get(n) == "The Netherlands"),
                 ("对照 瑞典籍(现代)", lambda n: CTY.get(n) == "Sweden")]:
    cells = []
    for s, a, b in SEG:
        c = [0, 0]
        for k, v in D.items():
            nm, y = k.rsplit("|", 1); y = int(y)
            if a <= y <= b and sel(nm):
                c[0] += v[1]; c[1] += v[2]
        cells.append("%s (n=%d)" % (f(c), c[0]))
    print("%-22s %s" % (lab, "".join("%22s" % x for x in cells)))
