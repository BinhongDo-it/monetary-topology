# -*- coding: utf-8 -*-
"""完整性自查：R6 第四款的 n 门槛要求「前窗与豁免窗都有 n>=150」，
那道门槛会不会藏起一个反例？把它放宽到「只要豁免窗 n>=150」，重排一遍，印全。
两个方向都要看：(a) 有没有多出来的低读数港是从不属瑞典的；
(b) 有没有当时属瑞典而读得高的港（那才是真正的假阴性）。"""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
CTY = D.pop("__country__"); D.pop("__meta__")
SEG = [("pre", 1630, 1644), ("ex", 1660, 1709), ("post", 1720, 1779)]
P = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for k, v in D.items():
    nm, y = k.rsplit("|", 1); y = int(y)
    for s, a, b in SEG:
        if a <= y <= b:
            c = P[nm][s]; c[0] += v[1]; c[1] += v[2]
# 窗口内属瑞典的港，逐个点名（本土＋1645/1648/1658 三批＋芬兰、波罗的海诸省、不来梅-维尔登）
SWED = {"Stockholm","Göteborg","Norrköping","Kalmar","Nyköping","Gävle","Söderhamn","Hudiksvall",
        "Sundsvall","Härnösand","Uppsala","Västervik","Visby","Karlskrona","Karlshamn","Karlstad",
        "Halmstad","Varberg","Falkenberg","Kungelf","Marstrand","Uddevalla","Strömstad",
        "Malmö","Landskrona","Helsingborg","Ystad","Simrishamn","Kristianstad","Åhus",
        "Stralsund","Stettin","Greifswald","Anklam","Demmin","Wolgast","Wismar","Barth","Damm","Gollnow",
        "Riga","Reval","Pernau","Narva","Arensburg","Nyen","Åbo","Helsingfors","Viborg","Björneborg",
        "Stade","Buxtehude"}
rows = []
for nm, d in P.items():
    ex = d["ex"]
    if ex[0] >= 150:
        pre, po = d["pre"], d["post"]
        rows.append((ex[1]/ex[0], nm, CTY.get(nm,"?"), ex[0],
                     ("%.3f"%(pre[1]/pre[0])) if pre[0]>=150 else "·", pre[0],
                     ("%.3f"%(po[1]/po[0])) if po[0]>=150 else "·", po[0]))
rows.sort()
print("【放宽后：豁免窗 n>=150 的籍港共 %d 个（原 94 个）。前 20 名】" % len(rows))
print("%-3s %-16s %-16s %8s %8s %10s %10s %9s" % ("#","籍港","现代国别","豁免","n豁免","前1630-44","后1720-79","窗口内属瑞"))
for i,(ex,nm,co,nex,pre,npre,po,npo) in enumerate(rows[:20],1):
    print("%-3d %-16s %-16s %8.3f %8d %10s %10s %9s" % (i,nm,co,ex,nex,pre,po,"是" if nm in SWED else ""))
print("\n【方向 (b)：窗口内属瑞典、且豁免窗 n>=150 的港，一个不漏】")
print("%-16s %-16s %8s %8s %10s %10s" % ("籍港","现代国别","豁免","n豁免","前1630-44","后1720-79"))
sw=[r for r in rows if r[1] in SWED]
for ex,nm,co,nex,pre,npre,po,npo in sw:
    print("%-16s %-16s %8.3f %8d %10s %10s" % (nm,co,ex,nex,pre,po))
print("共 %d 个，其中豁免窗读数最高的是 %s = %.3f" % (len(sw), sw[-1][1], sw[-1][0]))
print("\n【方向 (a)：读数低于最高的那个属瑞港、而不属瑞典的港】")
cut=sw[-1][0]
bad=[r for r in rows if r[0]<=cut and r[1] not in SWED]
print("共 %d 个：%s" % (len(bad), "、".join("%s(%.3f,%s)"%(r[1],r[0],r[2]) for r in bad) or "无"))
