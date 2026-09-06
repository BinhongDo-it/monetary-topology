# -*- coding: utf-8 -*-
"""R8 v2：不取基本圈基底，枚举全部四腿圈。

为什么换：基本圈的基底由生成树决定，而生成树由 set 的迭代顺序决定，
Python 的字符串哈希逐次随机，于是那个中位每跑一次就变一个数。
比不可复现更深的是：那个中位本来就是基底的函数，而基底是任意的。
四腿圈（两个西港 × 两个东港，四条腿都在）是规范的、无基底的族，
每一个都是同一个形状的 2×2 双重差分，彼此可比。独立数另报（D22：b1）。
一切迭代都在排序后的列表上做（写盘纪律第 4 条）。
"""
import json, csv, pathlib, statistics, random, itertools, collections
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
D = json.load((CACHE/"b44_r5_cells2.json").open(encoding="utf-8"))
cell = {}
for k,v in D.items():
    w,pr,c,d = k.split("|"); cell[(w,pr,c,d)] = [x[1] for x in v]
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
ALL=["瑞","荷","英","丹","挪","德","余"]; NS=[c for c in ALL if c!="瑞"]
def vals(w,pr,cs,d):
    o=[]
    for c in cs: o+=cell.get((w,pr,c,d),[])
    return o
def build(w,cs,nmin):
    E={}
    for pr in sorted({k[1] for k in cell if k[0]==w}):          # 排序，固定顺序
        a,b=pr.split("~")
        if a not in west or b not in west or west[a]==west[b]: continue
        W,Ep=(a,b) if west[a] else (b,a)
        e=vals(w,pr,cs,"东"); x=vals(w,pr,cs,"西")
        if len(e)>=nmin and len(x)>=nmin:
            E[(W,Ep)]={"h":0.5*(statistics.median(x)-statistics.median(e)),"东":e,"西":x}
    return E
def quads(E):
    adj=collections.defaultdict(set)
    for (W,Ep) in E: adj[W].add(Ep)
    Ws=sorted(adj)
    out=[]
    for i in range(len(Ws)):
        for j in range(i+1,len(Ws)):
            com=sorted(adj[Ws[i]] & adj[Ws[j]])
            for a in range(len(com)):
                for b in range(a+1,len(com)):
                    out.append((Ws[i],Ws[j],com[a],com[b]))
    return out
def qsum(q,E):
    W1,W2,E1,E2=q
    h=[E[(W1,E1)]["h"],E[(W2,E1)]["h"],E[(W2,E2)]["h"],E[(W1,E2)]["h"]]
    return h[0]-h[1]+h[2]-h[3], sum(abs(x) for x in h)
def qboot(q,E,rng,reps=400):
    W1,W2,E1,E2=q; legs=[(W1,E1,1),(W2,E1,-1),(W2,E2,1),(W1,E2,-1)]
    o=[]
    for _ in range(reps):
        s=0.0
        for a,b,sg in legs:
            d=E[(a,b)]
            s+=sg*0.5*(statistics.median(rng.choices(d["西"],k=len(d["西"])))
                       -statistics.median(rng.choices(d["东"],k=len(d["东"]))))
        o.append(s)
    return statistics.pstdev(o)
def b1(E):
    V=sorted({p for e in E for p in e}); par={v:v for v in V}
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for a,b in sorted(E): par[f(a)]=f(b)
    c=len({f(v) for v in V})
    return len(E)-len(V)+c, len(V), c
NM=40
print("【E1 结构自检：一条腿走过去再走回来，环和必须精确得零】")
E=build("豁免",NS,NM); k=sorted(E)[0]
h=E[k]["h"]; print("  %s→%s→%s：%.17g  %s" % (k[0],k[1],k[0],h-h,"通过" if h-h==0.0 else "失败"))
for w,cs,lab in [("豁免",NS,"豁免 1650-1709　非瑞典类"),("后",NS,"后 1720-1779　非瑞典类"),
                 ("后",["瑞"],"后 1720-1779　瑞典类"),("豁免",["瑞"],"豁免 1650-1709　瑞典类")]:
    E=build(w,cs,NM); Q=quads(E); bb,nv,nc=b1(E)
    print("\n【%s】航线 %d、港 %d、分支 %d  =>  b1(G)=%d（独立数上限）；四腿圈 %d 个"
          %(lab,len(E),nv,nc,bb,len(Q)))
    if not Q: print("  没有四腿圈"); continue
    r=[]; big=[]
    for q in Q:
        s,sc=qsum(q,E)
        if sc>0: r.append(abs(s)/sc); big.append((abs(s),sc,abs(s)/sc,q))
    r.sort()
    print("  归一化比 |Σŵ|/Σ|ŵ|：中位 %.4f  四分位 %.4f / %.4f  区间 %.4f – %.4f  （n=%d）"
          %(statistics.median(r),r[len(r)//4],r[3*len(r)//4],r[0],r[-1],len(r)))
    sc=sorted(x[1] for x in big)
    print("  尺度 Σ|ŵ| 中位 %.3f Daler，四分位 %.3f / %.3f" % (statistics.median(sc),sc[len(sc)//4],sc[3*len(sc)//4]))
    big.sort(key=lambda x:-x[1])
    print("  尺度最大的三个： " + " ; ".join("%s %s↔%s/%s 比%.3f 尺度%.1f"
          %("",q[0][:8],q[2][:8],q[3][:8],ra,s2) for _,s2,ra,q in big[:3]))
    rng=random.Random(20260903)
    samp=[Q[i] for i in sorted(random.Random(11).sample(range(len(Q)),min(30,len(Q))))]
    fl=[]
    for q in samp:
        s,scv=qsum(q,E)
        if scv>0: fl.append(qboot(q,E,rng)/scv)
    print("  噪声底 se/Σ|ŵ|（随机 %d 个四腿圈）中位 %.4f  =>  读数是底的 %.1f 倍"
          %(len(fl),statistics.median(fl),statistics.median(r)/statistics.median(fl)))
