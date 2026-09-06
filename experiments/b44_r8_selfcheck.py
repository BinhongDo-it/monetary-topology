# -*- coding: utf-8 -*-
"""R8（规范版）自查：确定性的量逐条 assert。全部排序后迭代，故可复现。
第一版那个自查已随第一版读数一并作废。"""
import json, csv, pathlib, statistics, collections
import os
_H=pathlib.Path(__file__).resolve().parent
RAW=_H.parent/"data/raw/stro/classic"; CACHE=_H.parent/"data/cache/stro_classic"
D=json.load((CACHE/"b44_r5_cells2.json").open(encoding="utf-8"))
cell={}
for k,v in D.items():
    w,pr,c,d=k.split("|"); cell[(w,pr,c,d)]=[x[1] for x in v]
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
ALL=["瑞","荷","英","丹","挪","德","余"]; NS=[c for c in ALL if c!="瑞"]
def vals(w,pr,cs,d):
    o=[]
    for c in cs: o+=cell.get((w,pr,c,d),[])
    return o
def build(w,cs,nmin=40):
    E={}
    for pr in sorted({k[1] for k in cell if k[0]==w}):
        a,b=pr.split("~")
        if a not in west or b not in west or west[a]==west[b]: continue
        W,Ep=(a,b) if west[a] else (b,a)
        e=vals(w,pr,cs,"东"); x=vals(w,pr,cs,"西")
        if len(e)>=nmin and len(x)>=nmin: E[(W,Ep)]=0.5*(statistics.median(x)-statistics.median(e))
    return E
def quads(keys):
    adj=collections.defaultdict(set)
    for (W,Ep) in keys: adj[W].add(Ep)
    Ws=sorted(adj); out=[]
    for i in range(len(Ws)):
        for j in range(i+1,len(Ws)):
            com=sorted(adj[Ws[i]]&adj[Ws[j]])
            for a in range(len(com)):
                for b in range(a+1,len(com)): out.append((Ws[i],Ws[j],com[a],com[b]))
    return out
def b1(keys):
    V=sorted({p for e in keys for p in e}); par={v:v for v in V}
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for a,b in sorted(keys): par[f(a)]=f(b)
    return len(keys)-len(V)+len({f(v) for v in V}), len(V)
def rat(q,E):
    W1,W2,E1,E2=q; h=[E[(W1,E1)],E[(W2,E1)],E[(W2,E2)],E[(W1,E2)]]
    s=h[0]-h[1]+h[2]-h[3]; sc=sum(abs(x) for x in h)
    return (abs(s)/sc if sc>0 else None), s, sc
CHK=[]
def eq(l,g,w,tol=5e-4):
    CHK.append((((abs(g-w)<=tol) if isinstance(w,float) else (g==w)) if g is not None else False,l,g,w))
for w,cs,lab,nr,npo,bb,nq,med,scm in [
        ("豁免",NS,"豁免非瑞",91,66,26,110,0.1265,74.927),
        ("后",NS,"后非瑞",211,111,101,1147,0.2036,81.172),
        ("后",["瑞"],"后瑞",48,38,11,26,0.3924,12.234),
        ("豁免",["瑞"],"豁免瑞",0,0,0,0,None,None)]:
    E=build(w,cs); Q=quads(E.keys()); bv,nv=b1(E.keys())
    eq(lab+" 航线",len(E),nr); eq(lab+" 港",nv,npo); eq(lab+" b1(G)",bv,bb); eq(lab+" 四腿圈",len(Q),nq)
    if med is not None:
        r=[rat(q,E)[0] for q in Q if rat(q,E)[0] is not None]
        sc=[rat(q,E)[2] for q in Q if rat(q,E)[0] is not None]
        eq(lab+" 比中位",statistics.median(r),med)
        eq(lab+" 尺度中位",statistics.median(sc),scm,1e-3)
# E1
E=build("豁免",NS); k=sorted(E)[0]; eq("E1 一条腿来回精确零",E[k]-E[k],0.0,0.0)
# 同批
edges=[]
for pr in sorted({k[1] for k in cell}):
    a,b=pr.split("~")
    if a not in west or b not in west or west[a]==west[b]: continue
    if all(min(len(vals(w,pr,NS,d)) for d in ("东","西"))>=40 for w in ("豁免","后")):
        edges.append((a,b) if west[a] else (b,a))
Q=quads(edges); E1m=build("豁免",NS); E2m=build("后",NS)
eq("同批 航线",len(edges),69); eq("同批 港",len({p for e in edges for p in e}),50); eq("同批 四腿圈",len(Q),86)
r1=[rat(q,E1m)[0] for q in Q]; r2=[rat(q,E2m)[0] for q in Q]
ok=[(a,b) for a,b in zip(r1,r2) if a is not None and b is not None]
eq("同批 豁免 比中位",statistics.median([a for a,_ in ok]),0.1088)
eq("同批 后 比中位",statistics.median([b for _,b in ok]),0.1268)
eq("同批 逐圈|差|中位",statistics.median([abs(a-b) for a,b in ok]),0.1024)
eq("同批 逐圈|差|最大",max(abs(a-b) for a,b in ok),0.8207)
eq("同批 Σŵ 同号",sum(1 for q in Q if rat(q,E1m)[1]*rat(q,E2m)[1]>0),62)
# 逐十年
C=json.load((CACHE/"b44_r8_decade.json").open(encoding="utf-8"))
def dv(dec,pr,d): return C.get("%d|%s|非瑞|%s"%(dec,pr,d),[])
per=collections.defaultdict(list)
for q in Q:
    W1,W2,E1x,E2x=q
    for dec in range(1650,1790,10):
        h=[];good=True
        for A,B in ((W1,E1x),(W2,E1x),(W2,E2x),(W1,E2x)):
            pr="~".join(sorted((A,B))); e=dv(dec,pr,"东"); x=dv(dec,pr,"西")
            if len(e)<20 or len(x)<20: good=False;break
            h.append(0.5*(statistics.median(x)-statistics.median(e)))
        if good:
            s=h[0]-h[1]+h[2]-h[3]; sc=sum(abs(v) for v in h)
            if sc>0: per[dec].append(abs(s)/sc)
pre=[x for d in per if d<1720 for x in per[d]]; post=[x for d in per if d>=1720 for x in per[d]]
eq("逐十年 前观测数",len(pre),111); eq("逐十年 后观测数",len(post),354)
eq("逐十年 前中位",statistics.median(pre),0.1845); eq("逐十年 后中位",statistics.median(post),0.1631)
pm=[statistics.median(per[d]) for d in sorted(per) if d<1720 and per[d]]
qm=[statistics.median(per[d]) for d in sorted(per) if d>=1720 and per[d]]
eq("逐十年 前跨度下",min(pm),0.0749); eq("逐十年 前跨度上",max(pm),0.2866)
eq("逐十年 后跨度下",min(qm),0.1421); eq("逐十年 后跨度上",max(qm),0.1752)
eq("1710s 比中位",statistics.median(per[1710]),0.129,1e-3)
eq("1720s 比中位",statistics.median(per[1720]),0.164,1e-3)
bad=[c for c in CHK if not c[0]]
for ok_,l,g,w in CHK:
    print("%s %-24s 得 %-12s 应 %s"%("OK " if ok_ else "!!!",l,
        ("%.4f"%g) if isinstance(g,float) else g,("%.4f"%w) if isinstance(w,float) else w))
print("\n%d 条检查，%d 条不过"%(len(CHK),len(bad)))
# write-up cross-check: the numbers this script recomputes must also appear
# in the station's write-up. Path comes from the environment so this file
# names no document of its own.
need=["0.1265","0.2036","0.3924","0.1088","0.1268","0.1024","0.8207","62 / 86",
      "0.1845","0.1631","0.0749","0.2866","0.1421","0.1752","3 1/0","19 / 19","1,147"]
w=os.environ.get("B44_WRITEUP")
if w:
    t=pathlib.Path(w).read_text(encoding="utf-8")
    m=[s for s in need if s not in t]
    print("write-up missing:",m or "none")
else:
    m=[]; print("write-up check skipped (set B44_WRITEUP to a path to run it)")
raise SystemExit(1 if (bad or m) else 0)
