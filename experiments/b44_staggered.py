# -*- coding: utf-8 -*-
"""塌的那 11 个港不是同时塌的：它们各自的主权是分三批换的（1645 哈兰德、1648 波美拉尼亚、
1658 斯科讷与布胡斯）。逐年印，看每个港的断点落不落在它自己那纸条约上。
不画线：印读数与 n，不设阈值（第 11 条）。"""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
D.pop("__country__"); D.pop("__meta__")
Y = collections.defaultdict(lambda: [0, 0])
for k, v in D.items():
    nm, y = k.rsplit("|", 1)
    c = Y[(nm, int(y))]; c[0] += v[1]; c[1] += v[2]

BATCH = [
    ("瑞典本土（1645 布罗姆瑟布鲁起免）", ["Stockholm", "Göteborg", "Norrköping"]),
    ("哈兰德 1645 质押给瑞典 30 年", ["Varberg", "Halmstad"]),
    ("瑞属波美拉尼亚 1648 西发里亚", ["Stralsund", "Stettin", "Greifswald", "Anklam", "Wismar"]),
    ("斯科讷／布胡斯 1658 罗斯基勒", ["Malmö", "Landskrona", "Kungelf", "Marstrand"]),
    ("对照：从不属瑞典", ["Lübeck", "Rostock", "København", "Amsterdam", "Danzig"]),
]
YRS = list(range(1640, 1671))
print("【逐年 aantal 填充率，n<40 印 ·（n 在下一行）】")
hdr = "".join("%6s" % str(y)[-2:] for y in YRS)
print("%-14s %s" % ("", hdr))
for lab, ports in BATCH:
    print("-- %s" % lab)
    for nm in ports:
        a = "".join(("%6.2f" % (Y[(nm, y)][1] / Y[(nm, y)][0])) if Y[(nm, y)][0] >= 40 else "%6s" % "·"
                    for y in YRS)
        b = "".join("%6d" % Y[(nm, y)][0] for y in YRS)
        print("%-14s %s" % (nm, a))
        print("%-14s %s" % ("  n", b))

print("\n【每批合并后逐年，n 更厚】")
print("%-30s %s" % ("", hdr))
for lab, ports in BATCH:
    a, b = [], []
    for y in YRS:
        c = [0, 0]
        for nm in ports:
            x = Y[(nm, y)]; c[0] += x[0]; c[1] += x[1]
        a.append(("%6.2f" % (c[1] / c[0])) if c[0] >= 40 else "%6s" % "·")
        b.append("%6d" % c[0])
    print("%-30s %s" % (lab, "".join(a)))
    print("%-30s %s" % ("  n", "".join(b)))
