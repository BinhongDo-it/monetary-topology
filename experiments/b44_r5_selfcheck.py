# -*- coding: utf-8 -*-
"""R5 自查：把写进结果件的承重数字从缓存重算，逐条 assert。写错一个数就在这里炸。"""
import json, pathlib, statistics, random
import os
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_r5_cells2.json").open(encoding="utf-8"))
cell = {}
for k, v in D.items():
    w, pr, c, d = k.split("|"); cell[(w, pr, c, d)] = [x[1] for x in v]
ALL = ["瑞","荷","英","丹","挪","德","余"]
G = {"T": (["瑞"], [c for c in ALL if c != "瑞"]),
     "P": (["荷"], [c for c in ALL if c not in ("瑞","荷")])}
def get(w,pr,cs,d):
    o=[]
    for c in cs: o+=cell.get((w,pr,c,d),[])
    return o
def one(w,pr,A,B,nmin,agg=statistics.median):
    v={(g,d):get(w,pr,cs,d) for g,cs in (("a",A),("b",B)) for d in ("东","西")}
    if min(len(x) for x in v.values())<nmin: return None
    m={k:agg(x) for k,x in v.items()}
    idx=(m[("b","东")]-m[("b","西")])-(m[("a","东")]-m[("a","西")]); fri=sum(m.values())
    return dict(pr=pr,m=m,idx=idx,fri=fri,rho=abs(idx)/fri)
def rows(w,g,nmin,agg=statistics.median):
    A,B=G[g]; return [r for r in (one(w,pr,A,B,nmin,agg) for pr in sorted({k[1] for k in cell if k[0]==w})) if r]
CHK=[]
def eq(lab,got,want,tol=5e-4):
    ok = (abs(got-want)<=tol) if isinstance(want,float) else (got==want)
    CHK.append((ok,lab,got,want))
mean=lambda x: sum(x)/len(x)
T40=rows("后","T",40); T20=rows("后","T",20)
P40=rows("后","P",40); PE=rows("豁免","P",40)
eq("后 主 n>=40 航线数",len(T40),8); eq("后 主 n>=20 航线数",len(T20),16)
eq("后 安慰剂 n>=40 航线数",len(P40),24); eq("豁免 安慰剂 n>=40 航线数",len(PE),6)
eq("后 主 rho 中位",statistics.median([r["rho"] for r in T40]),0.0794)
eq("后 主 n>=20 rho 中位",statistics.median([r["rho"] for r in T20]),0.0794)
eq("后 安慰剂 rho 中位",statistics.median([r["rho"] for r in P40]),0.0858)
eq("豁免 安慰剂 rho 中位",statistics.median([r["rho"] for r in PE]),0.0722)
eq("后 主 均值聚合 rho 中位",statistics.median([r["rho"] for r in rows("后","T",40,mean)]),0.0858)
eq("后 安慰剂 均值聚合 rho 中位",statistics.median([r["rho"] for r in rows("后","P",40,mean)]),0.0617)
eq("后 主 |S−S'| 中位",statistics.median([abs(r["idx"]) for r in T40]),15.3125,1e-3)
eq("后 安慰剂 |S−S'| 中位",statistics.median([abs(r["idx"]) for r in P40]),8.500,1e-3)
eq("豁免 安慰剂 |S−S'| 中位",statistics.median([abs(r["idx"]) for r in PE]),8.3125,1e-3)
by={r["pr"]:r for r in T40}
for nm,(m4,rho,idx) in {
 "Amsterdam~Stockholm":((81.00,75.5625,64.625,39.6875),0.0747,19.500),
 "London~Stockholm":((239.125,93.8125,2.00,108.125),0.5675,-251.438),
 "Goteborg~Stralsund":(None,0.3724,-11.125),
 "Danzig~Goteborg":(None,0.0340,2.750),
 "Amsterdam~Norrkoping":(None,0.0841,-22.375),
 "Amsterdam~Karlskrona":(None,0.0618,-5.750),
 "Goteborg~Wolgast":(None,0.0216,-1.250),
 "Liverpool~Stockholm":(None,0.1359,28.938)}.items():
    cand=[k for k in by if k.replace("ö","o").replace("é","e")==nm or k==nm]
    if not cand:
        cand=[k for k in by if k.replace("ö","o")==nm]
    if not cand: CHK.append((False,"找不到航线 "+nm,None,None)); continue
    r=by[cand[0]]
    eq(cand[0]+" rho",r["rho"],rho); eq(cand[0]+" S−S'",r["idx"],idx,1e-3)
    if m4:
        for (g,d),want in zip((("a","东"),("a","西"),("b","东"),("b","西")),m4):
            eq("%s %s%s 中位"%(cand[0],g,d),r["m"][(g,d)],want,1e-3)
eq("结构自检 rho<=1 全过",all(r["rho"]<=1.0 for r in T40+T20+P40+PE),True)
# 归约检查那张表
for w,c,d,n,med in [("豁免","瑞","东",370,2.104),("豁免","瑞","西",314,5.812),
                    ("豁免","荷","东",23593,4.000),("豁免","荷","西",23977,48.000),
                    ("后","瑞","东",17228,19.875),("后","瑞","西",17946,16.125),
                    ("后","荷","东",48878,2.000),("后","荷","西",51831,39.750)]:
    v=[x for k,xs in cell.items() if k[0]==w and k[2]==c and k[3]==d for x in xs]
    eq("%s %s %s n"%(w,c,d),len(v),n); eq("%s %s %s 中位"%(w,c,d),statistics.median(v),med,1e-3)
# R4 修正
r4=json.load((CACHE/"b44_rho_v2.json").open(encoding="utf-8"))
eq("R4 航线数",len(r4),16)
eq("R4 rho 中位",statistics.median([abs(E-W)/(16+E+W) for _,_,_,_,E,W in r4]),0.2552)
eq("修正后 rho 中位",statistics.median([abs((E-W)-(2.104-5.812))/(2.104+5.812+8+E+W) for _,_,_,_,E,W in r4]),0.2422)
# 格数
for w,nmin,want in [("豁免",40,0),("后",40,8),("后",20,16),("豁免",20,1)]:
    routes={k[1] for k in cell if k[0]==w}
    c=sum(1 for pr in routes if min(len(get(w,pr,["瑞"],d)) for d in ("东","西"))>=nmin
          and min(len(get(w,pr,[x for x in ALL if x!="瑞"],d)) for d in ("东","西"))>=nmin)
    eq("%s 四格>=%d 的航线数"%(w,nmin),c,want)
bad=[c for c in CHK if not c[0]]
for ok,lab,got,want in CHK:
    print("%s %-34s 得 %-14s 应 %s" % ("OK " if ok else "!!!",lab,
          ("%.4f"%got) if isinstance(got,float) else got,
          ("%.4f"%want) if isinstance(want,float) else want))
print("\n%d 条检查，%d 条不过" % (len(CHK),len(bad)))
# write-up cross-check: the numbers this script recomputes must also appear
# in the station's write-up. Path comes from the environment so this file
# names no document of its own.
need=["0.0794","0.0858","0.0722","0.2552","0.0617","0.5675","0.3724",
      "15.312","8.500","0.2422","239.12","21.7%","118.9%","5.1%"]
w=os.environ.get("B44_WRITEUP")
if w:
    t=pathlib.Path(w).read_text(encoding="utf-8")
    m=[s for s in need if s not in t]
    print("write-up missing:",m or "none")
else:
    m=[]; print("write-up check skipped (set B44_WRITEUP to a path to run it)")
raise SystemExit(1 if (bad or m) else 0)
