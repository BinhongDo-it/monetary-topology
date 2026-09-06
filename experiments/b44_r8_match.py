# -*- coding: utf-8 -*-
"""R8 补：E3 要同一批圈才算数（101 个对 26 个不是 like-for-like）。
取两个窗口都够厚的航线交集建图，逐圈对比；并把归一化比的噪声底 se/Σ|ŵ| 一起印出来。"""
import json, csv, pathlib, statistics, random
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_r5_cells2.json").open(encoding="utf-8"))
cell = {}
for k, v in D.items():
    w, pr, c, d = k.split("|"); cell[(w, pr, c, d)] = [x[1] for x in v]
west = {}
with (RAW / "places_standard.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f, delimiter=";"):
        west[row["Stednavn"].strip()] = row["west_of_Helsingør"].strip().lower() == "true"
ALL = ["瑞","荷","英","丹","挪","德","余"]; NS = [c for c in ALL if c != "瑞"]
rng = random.Random(20260903)
def vals(w,pr,cs,d):
    o=[]
    for c in cs: o+=cell.get((w,pr,c,d),[])
    return o
def ok(w,pr,cs,nmin): return min(len(vals(w,pr,cs,d)) for d in ("东","西"))>=nmin
def cycles(edges):
    par={}
    def f(x):
        par.setdefault(x,x)
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    adj={}; extra=[]
    for (a,b) in edges:
        if f(a)!=f(b):
            par[f(a)]=f(b); adj.setdefault(a,[]).append(b); adj.setdefault(b,[]).append(a)
        else: extra.append((a,b))
    def path(u,v):
        st=[(u,[u])]; seen={u}
        while st:
            x,p=st.pop()
            if x==v: return p
            for y in adj.get(x,[]):
                if y not in seen: seen.add(y); st.append((y,p+[y]))
    return [path(b,a)+[b] for (a,b) in extra if path(b,a)]
def wh(w,pr,cs): return 0.5*(statistics.median(vals(w,pr,cs,"西"))-statistics.median(vals(w,pr,cs,"东")))
def loop(cyc,w,cs):
    s=sc=0.0
    for x,y in zip(cyc,cyc[1:]):
        pr="~".join(sorted((x,y))); v=wh(w,pr,cs)
        s+=(1.0 if (west.get(x) and not west.get(y)) else -1.0)*v; sc+=abs(v)
    return s,sc
def boot(cyc,w,cs,reps=1200):
    out=[]
    for _ in range(reps):
        s=0.0
        for x,y in zip(cyc,cyc[1:]):
            pr="~".join(sorted((x,y)))
            v=0.5*(statistics.median(rng.choices(vals(w,pr,cs,"西"),k=len(vals(w,pr,cs,"西"))))
                   -statistics.median(rng.choices(vals(w,pr,cs,"东"),k=len(vals(w,pr,cs,"东")))))
            s+=(1.0 if (west.get(x) and not west.get(y)) else -1.0)*v
        out.append(s)
    return statistics.pstdev(out)
NM=40
both=[]
for pr in {k[1] for k in cell}:
    a,b=pr.split("~")
    if a not in west or b not in west or west[a]==west[b]: continue
    if ok("豁免",pr,NS,NM) and ok("后",pr,NS,NM): both.append((a,b))
cyc=cycles(both)
print("【E3 同一批圈：两个窗口都两向 n>=%d 的航线 %d 条，港 %d 个，基本圈 %d 个】"
      % (NM,len(both),len({p for e in both for p in e}),len(cyc)))
print("%-46s %9s %9s %8s %9s %9s %8s" % ("圈","豁免 Σŵ","后 Σŵ","豁免比","后比","豁免底","后底"))
r1=[];r2=[];rows=[]
for c in sorted(cyc,key=len):
    s1,c1=loop(c,"豁免",NS); s2,c2=loop(c,"后",NS)
    e1=boot(c,"豁免",NS); e2=boot(c,"后",NS)
    r1.append(abs(s1)/c1); r2.append(abs(s2)/c2); rows.append((c,s1,s2,abs(s1)/c1,abs(s2)/c2,e1/c1,e2/c2))
for c,s1,s2,a1,a2,f1,f2 in rows[:12]:
    print("%-46s %9.3f %9.3f %8.4f %8.4f %9.4f %8.4f" % ("→".join(c)[:46],s1,s2,a1,a2,f1,f2))
print("  归一化比中位：豁免 %.4f  后 %.4f" % (statistics.median(r1),statistics.median(r2)))
print("  噪声底 se/Σ|ŵ| 中位：豁免 %.4f  后 %.4f"
      % (statistics.median([x[5] for x in rows]),statistics.median([x[6] for x in rows])))
d=[abs(a2-a1) for _,_,_,a1,a2,_,_ in rows]
print("  逐圈 |后比 − 豁免比| 中位 %.4f，最大 %.4f" % (statistics.median(d),max(d)))
sg=sum(1 for _,s1,s2,*_ in rows if s1*s2>0)
print("  逐圈 Σŵ 两个窗口同号：%d / %d" % (sg,len(rows)))
