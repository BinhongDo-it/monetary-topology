# -*- coding: utf-8 -*-
"""R8 v2 的 E3：同一批四腿圈跨窗口比，以及逐十年。全部排序后迭代，无基底。"""
import json, csv, pathlib, statistics, random, collections
_H = pathlib.Path(__file__).resolve().parent
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
NM=40
edges=[]
for pr in sorted({k[1] for k in cell}):
    a,b=pr.split("~")
    if a not in west or b not in west or west[a]==west[b]: continue
    if all(min(len(vals(w,pr,NS,d)) for d in ("东","西"))>=NM for w in ("豁免","后")):
        edges.append((a,b) if west[a] else (b,a))
def H(w,W,E): 
    pr="~".join(sorted((W,E)))
    return 0.5*(statistics.median(vals(w,pr,NS,"西"))-statistics.median(vals(w,pr,NS,"东")))
adj=collections.defaultdict(set)
for (W,E) in edges: adj[W].add(E)
Q=[]
Ws=sorted(adj)
for i in range(len(Ws)):
    for j in range(i+1,len(Ws)):
        com=sorted(adj[Ws[i]]&adj[Ws[j]])
        for a in range(len(com)):
            for b in range(a+1,len(com)): Q.append((Ws[i],Ws[j],com[a],com[b]))
def ratio(w,q):
    W1,W2,E1,E2=q
    h=[H(w,W1,E1),H(w,W2,E1),H(w,W2,E2),H(w,W1,E2)]
    s=h[0]-h[1]+h[2]-h[3]; sc=sum(abs(x) for x in h)
    return (abs(s)/sc if sc>0 else None), s, sc
V={p for e in edges for p in e}
print("【E3 同批：两个窗口都两向 n>=%d 的航线 %d 条、港 %d 个，四腿圈 %d 个】"%(NM,len(edges),len(V),len(Q)))
r1=[];r2=[];sg=0;dd=[]
for q in Q:
    a,s1,_=ratio("豁免",q); b,s2,_=ratio("后",q)
    if a is None or b is None: continue
    r1.append(a); r2.append(b); dd.append(abs(a-b))
    if s1*s2>0: sg+=1
print("  归一化比中位：豁免 %.4f（四分位 %.4f/%.4f）  后 %.4f（%.4f/%.4f）"
      %(statistics.median(r1),sorted(r1)[len(r1)//4],sorted(r1)[3*len(r1)//4],
        statistics.median(r2),sorted(r2)[len(r2)//4],sorted(r2)[3*len(r2)//4]))
print("  逐圈 |后比 − 豁免比| 中位 %.4f，四分位 %.4f / %.4f，最大 %.4f"
      %(statistics.median(dd),sorted(dd)[len(dd)//4],sorted(dd)[3*len(dd)//4],max(dd)))
print("  逐圈 Σŵ 两窗同号 %d / %d"%(sg,len(r1)))
rng=random.Random(20260903)
def boot(w,q,reps=400):
    W1,W2,E1,E2=q; legs=[(W1,E1,1),(W2,E1,-1),(W2,E2,1),(W1,E2,-1)]; o=[]
    for _ in range(reps):
        s=0.0
        for A,B,g in legs:
            pr="~".join(sorted((A,B))); e=vals(w,pr,NS,"东"); x=vals(w,pr,NS,"西")
            s+=g*0.5*(statistics.median(rng.choices(x,k=len(x)))-statistics.median(rng.choices(e,k=len(e))))
        o.append(s)
    return statistics.pstdev(o)
samp=[Q[i] for i in sorted(random.Random(11).sample(range(len(Q)),min(30,len(Q))))]
for w in ("豁免","后"):
    fl=[boot(w,q)/ratio(w,q)[2] for q in samp if ratio(w,q)[2]>0]
    med=statistics.median(r1 if w=="豁免" else r2)
    print("  %s 噪声底中位 %.4f  =>  读数是底的 %.1f 倍"%(w,statistics.median(fl),med/statistics.median(fl)))

C=json.load((CACHE/"b44_r8_decade.json").open(encoding="utf-8"))
def dv(dec,pr,d): return C.get("%d|%s|非瑞|%s"%(dec,pr,d),[])
print("\n【逐十年，同一批四腿圈（每条腿每方向 n>=20），看 1720 有没有台阶】")
decs=list(range(1650,1790,10)); per=collections.defaultdict(list)
for q in Q:
    W1,W2,E1,E2=q
    for dec in decs:
        h=[];good=True
        for A,B in ((W1,E1),(W2,E1),(W2,E2),(W1,E2)):
            pr="~".join(sorted((A,B))); e=dv(dec,pr,"东"); x=dv(dec,pr,"西")
            if len(e)<20 or len(x)<20: good=False;break
            h.append(0.5*(statistics.median(x)-statistics.median(e)))
        if good:
            s=h[0]-h[1]+h[2]-h[3]; sc=sum(abs(v) for v in h)
            if sc>0: per[dec].append(abs(s)/sc)
print("  %-8s %s"%("十年","".join("%9s"%("%ds"%d) for d in decs)))
print("  %-8s %s"%("比中位","".join("%9s"%("%.3f"%statistics.median(per[d]) if per[d] else "·") for d in decs)))
print("  %-8s %s"%("四腿圈数","".join("%9d"%len(per[d]) for d in decs)))
pre=[x for d in decs if d<1720 for x in per[d]]; post=[x for d in decs if d>=1720 for x in per[d]]
if pre and post:
    print("  1720 前 %d 个圈-十年，中位 %.4f，十年中位跨度 %.4f–%.4f"
          %(len(pre),statistics.median(pre),
            min(statistics.median(per[d]) for d in decs if d<1720 and per[d]),
            max(statistics.median(per[d]) for d in decs if d<1720 and per[d])))
    print("  1720 后 %d 个圈-十年，中位 %.4f，十年中位跨度 %.4f–%.4f"
          %(len(post),statistics.median(post),
            min(statistics.median(per[d]) for d in decs if d>=1720 and per[d]),
            max(statistics.median(per[d]) for d in decs if d>=1720 and per[d])))
