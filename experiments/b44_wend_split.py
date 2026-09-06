# -*- coding: utf-8 -*-
"""§126.42 第七款第 2 件：文德汉萨那一组被瑞属波美拉尼亚污染，剥掉再读。

跑前登记（同一条主权规则的样本外外推，规则写在 §126.42 第四款）：
  1648 西发里亚把前波美拉尼亚整块给瑞典，1720 斯德哥尔摩条约割予普鲁士。
  于是九个成员里应当塌的不止三个，Anklam 与 Demmin 同批入瑞典，也该塌；
  Lübeck / Rostock / Hamburg / Kiel 从不属瑞典，不该塌。
  剥掉塌的那几个之后，组读数的 1690s 应当从 41% 回到对照组那一档。
全部是 b44_homeport_year.json 上的算术，零扫描。
"""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
CTY = D.pop("__country__"); META = D.pop("__meta__")

WEND = ["Lübeck", "Rostock", "Hamburg", "Kiel", "Stralsund", "Wismar", "Greifswald", "Anklam", "Demmin"]
PRED_SWED = {"Stralsund", "Wismar", "Greifswald", "Anklam", "Demmin"}   # 跑前登记
def grp(nm):
    if nm in WEND: return "文德汉萨"
    return {"Sweden": "瑞典", "Denmark": "丹麦", "Norway": "挪威",
            "The Netherlands": "尼德兰", "United Kingdom": "不列颠"}.get(CTY.get(nm, ""), "其余")

dec = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))   # 十年->组->[行,非空]
port = collections.defaultdict(lambda: [0, 0])                                   # (港,十年)->[行,非空]
for k, v in D.items():
    nm, y = k.rsplit("|", 1); y = int(y)
    if not (1600 <= y <= 1789): continue
    d = y // 10 * 10
    c = dec[d][grp(nm)]; c[0] += v[1]; c[1] += v[2]
    if nm in WEND:
        c = port[(nm, d)]; c[0] += v[1]; c[1] += v[2]

def pct(c, lo=200):
    return "%.0f%% (%d)" % (100 * c[1] / c[0], c[0]) if c[0] >= lo else "-(%d)" % c[0]

G = ["瑞典", "文德汉萨", "丹麦", "挪威", "尼德兰", "不列颠", "其余"]
DECS = [d for d in sorted(dec) if 1600 <= d <= 1780]
print("【核对：§126.42 第三款那张表，从缓存重算】")
print("%-7s %s" % ("十年", "".join("%14s" % g for g in G)))
for d in DECS:
    print("%-7s %s" % ("%ds" % d, "".join("%14s" % pct(dec[d].get(g, [0, 0])) for g in G)))

print("\n【九个成员逐港，aantal 填充率（n<150 印 · ）】  跑前登记该塌的：%s" % "、".join(sorted(PRED_SWED)))
SHOW = [d for d in DECS if 1620 <= d <= 1770]
print("%-12s %s" % ("籍港", "".join("%8s" % ("%ds" % d) for d in SHOW)))
for nm in WEND:
    row = []
    for d in SHOW:
        c = port.get((nm, d), [0, 0])
        row.append("%.0f%%" % (100 * c[1] / c[0]) if c[0] >= 150 else "·")
    print("%-12s %s   %s" % (nm, "".join("%8s" % x for x in row),
                             "← 登记该塌" if nm in PRED_SWED else ""))
print("\n同格样本量（明细行）")
print("%-12s %s" % ("籍港", "".join("%8s" % ("%ds" % d) for d in SHOW)))
for nm in WEND:
    print("%-12s %s" % (nm, "".join("%8d" % port.get((nm, d), [0, 0])[0] for d in SHOW)))

# 剥掉登记该塌的那几个，重读组读数
print("\n【剥掉登记该塌的 %d 个之后，文德汉萨组重读】" % len(PRED_SWED))
print("%-7s %14s %14s %14s %14s" % ("十年", "原组读数", "剥后（从不属瑞典）", "被剥掉的那几个", "尼德兰对照"))
for d in DECS:
    a = b = None
    A = [0, 0]; B = [0, 0]
    for nm in WEND:
        c = port.get((nm, d), [0, 0])
        t = B if nm in PRED_SWED else A
        t[0] += c[0]; t[1] += c[1]
    print("%-7s %14s %14s %14s %14s" % ("%ds" % d, pct(dec[d].get("文德汉萨", [0, 0])),
                                        pct(A), pct(B), pct(dec[d].get("尼德兰", [0, 0]))))
