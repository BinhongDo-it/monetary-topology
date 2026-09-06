# -*- coding: utf-8 -*-
"""把「窗口内属瑞典」改成机械判定，重排：
1660-1709 这个窗口上，瑞典本土的疆域就是现代瑞典（1658 罗斯基勒之后到 1719 之前没有再变），
所以 Modern_Country == 'Sweden' 等价于窗口内属瑞典，零判断。
另加窗口内属瑞典但不在现代瑞典境内的属地，逐个点名（波美拉尼亚＋维斯马、波罗的海诸省、
芬兰、不来梅-维尔登）。这一步是唯一要人来点的，所以把它单列。"""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
CTY = D.pop("__country__"); D.pop("__meta__")
EXTRA = {  # 窗口内属瑞典而不在现代瑞典境内
 "Stralsund":"波美拉尼亚1648","Stettin":"波美拉尼亚1648","Greifswald":"波美拉尼亚1648",
 "Anklam":"波美拉尼亚1648","Demmin":"波美拉尼亚1648","Wolgast":"波美拉尼亚1648",
 "Barth":"波美拉尼亚1648","Wismar":"维斯马1648",
 "Riga":"利沃尼亚1621","Pernau":"利沃尼亚1617","Reval":"爱沙尼亚1561","Narva":"爱沙尼亚1581",
 "Arensburg":"厄塞尔1645","Nyen":"英格里亚1617",
 "Åbo":"芬兰","Helsingfors":"芬兰","Viborg":"芬兰","Björneborg":"芬兰",
 "Stade":"不来梅-维尔登1648","Buxtehude":"不来梅-维尔登1648"}
def swed(nm): return "本土" if CTY.get(nm)=="Sweden" else EXTRA.get(nm,"")
SEG=[("pre",1630,1644),("ex",1660,1709),("post",1720,1779)]
P=collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0]))
for k,v in D.items():
    nm,y=k.rsplit("|",1); y=int(y)
    for s,a,b in SEG:
        if a<=y<=b:
            c=P[nm][s]; c[0]+=v[1]; c[1]+=v[2]
rows=[]
for nm,d in P.items():
    ex=d["ex"]
    if ex[0]>=150:
        pre,po=d["pre"],d["post"]
        rows.append((ex[1]/ex[0],nm,CTY.get(nm,"?"),ex[0],
                     ("%.3f"%(pre[1]/pre[0])) if pre[0]>=150 else "·",
                     ("%.3f"%(po[1]/po[0])) if po[0]>=150 else "·", swed(nm)))
rows.sort()
NS=[i for i,r in enumerate(rows) if not r[6]]
print("【豁免窗 n>=150 的 %d 个港，按读数升序。前 34 名】" % len(rows))
print("%-3s %-16s %-12s %7s %7s %9s %9s %s" % ("#","籍港","现代国别","豁免","n","前","后","窗口内属瑞"))
for i,(ex,nm,co,nex,pre,po,sw) in enumerate(rows[:34],1):
    print("%-3d %-16s %-12s %7.3f %7d %9s %9s %s" % (i,nm,co,ex,nex,pre,po,sw))
print("\n第一个不属瑞典的港排在第 %d 名：%s（%s），读 %.3f，n=%d"
      % (NS[0]+1, rows[NS[0]][1], rows[NS[0]][2], rows[NS[0]][0], rows[NS[0]][3]))
sw=[r for r in rows if r[6]]
print("属瑞典的共 %d 个，读数区间 %.3f – %.3f" % (len(sw), sw[0][0], sw[-1][0]))
print("  其中 <= 0.15 的 %d 个；0.15–0.50 的 %d 个（%s）；> 0.50 的 %d 个（%s）"
      % (sum(1 for r in sw if r[0]<=0.15),
         sum(1 for r in sw if 0.15<r[0]<=0.50), "、".join(r[1] for r in sw if 0.15<r[0]<=0.50),
         sum(1 for r in sw if r[0]>0.50), "、".join("%s %.3f"%(r[1],r[0]) for r in sw if r[0]>0.50)))
ns=[r for r in rows if not r[6]]
print("不属瑞典的共 %d 个，读数区间 %.3f – %.3f" % (len(ns), ns[0][0], ns[-1][0]))
print("  其中 <= 0.15 的 %d 个；0.15–0.50 的 %d 个（%s）"
      % (sum(1 for r in ns if r[0]<=0.15),
         sum(1 for r in ns if 0.15<r[0]<=0.50), "、".join("%s %.3f %s"%(r[1],r[0],r[2]) for r in ns if 0.15<r[0]<=0.50)))
# 属瑞典那一批里读得最高的几个，与不属瑞典读得最低的几个，两头对着看
print("\n【两头对着看】")
print("属瑞读得最高的 6 个：", "、".join("%s %.3f(n=%d,%s)"%(r[1],r[0],r[3],r[6]) for r in sw[-6:]))
print("不属瑞读得最低的 6 个：", "、".join("%s %.3f(n=%d,%s)"%(r[1],r[0],r[3],r[2]) for r in ns[:6]))
