# -*- coding: utf-8 -*-
"""§126.42 第七款第 3 件：Riga 那一格读 23%/37%，比本土 5%-11% 高，原因未查。

主权规则给一个可查的、与本土不同的日期：瑞属利沃尼亚／爱沙尼亚 1710 年被俄国占领
（Narva 1704），1721 尼斯塔德条约正式割让。所以这几个港的恢复应当在 1710 前后，
而不是本土那个 1720。跑前登记：若读数在 1710 恢复而不是 1720，那是同一条规则
给出的第二个日期，而它不是全局的制度变动能造出来的。
逐年印读数与 n，不画线（第 11 条）。"""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
D.pop("__country__"); D.pop("__meta__")
Y = collections.defaultdict(lambda: [0, 0])
for k, v in D.items():
    nm, y = k.rsplit("|", 1)
    c = Y[(nm, int(y))]; c[0] += v[1]; c[1] += v[2]
LIV = ["Riga", "Reval", "Pernau", "Narva"]
MAIN = ["Stockholm", "Göteborg", "Norrköping", "Stralsund"]
CTRL = ["Lübeck", "Amsterdam", "Danzig"]
def series(ports, y0, y1, lo=40):
    a, b = [], []
    for y in range(y0, y1 + 1):
        c = [0, 0]
        for nm in ports:
            x = Y[(nm, y)]; c[0] += x[0]; c[1] += x[1]
        a.append(("%6.2f" % (c[1] / c[0])) if c[0] >= lo else "%6s" % "·")
        b.append("%6d" % c[0])
    return "".join(a), "".join(b)

for y0, y1 in [(1690, 1729)]:
    print("【逐年，%d–%d，n<40 印 ·】" % (y0, y1))
    print("%-26s %s" % ("", "".join("%6s" % str(y)[-2:] for y in range(y0, y1 + 1))))
    for nm in LIV:
        a, b = series([nm], y0, y1)
        print("%-26s %s" % (nm, a)); print("%-26s %s" % ("  n", b))
    a, b = series(LIV, y0, y1); print("%-26s %s" % ("四港合并", a)); print("%-26s %s" % ("  n", b))
    a, b = series(MAIN, y0, y1); print("%-26s %s" % ("对照 本土＋波美拉尼亚", a)); print("%-26s %s" % ("  n", b))
    a, b = series(CTRL, y0, y1); print("%-26s %s" % ("对照 从不属瑞典", a)); print("%-26s %s" % ("  n", b))

print("\n【三段合并：1710 那条线两侧】")
SEG = [("豁免·俄占前 1660-1709", 1660, 1709), ("俄占后·1720 前 1710-1719", 1710, 1719),
       ("1720 后 1720-1779", 1720, 1779)]
print("%-26s %26s %26s %26s" % ("", SEG[0][0], SEG[1][0], SEG[2][0]))
for lab, ports in [("利沃尼亚四港", LIV), ("Riga 单港", ["Riga"]),
                   ("对照 本土＋波美拉尼亚", MAIN), ("对照 从不属瑞典", CTRL)]:
    cells = []
    for _, a0, a1 in SEG:
        c = [0, 0]
        for nm in ports:
            for y in range(a0, a1 + 1):
                x = Y[(nm, y)]; c[0] += x[0]; c[1] += x[1]
        cells.append(("%.3f (n=%d)" % (c[1] / c[0], c[0])) if c[0] >= 150 else "· (n=%d)" % c[0])
    print("%-26s %s" % (lab, "".join("%26s" % x for x in cells)))
