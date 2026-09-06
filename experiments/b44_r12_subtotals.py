# -*- coding: utf-8 -*-
"""R12：原件里有 tonnage、subtotaal1、subtotaal2、korting 四组字段，而 R2 去算了残差。
先只做诊断：填充率、单位、subtotaal1+subtotaal2 是不是等于 totaal、以及那个 4 是谁。
一次扫描，只读 doorvaarten。"""
import csv, pathlib, collections, re, statistics
_H=pathlib.Path(__file__).resolve().parent
RAW=_H.parent/"data/raw/stro/classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
FR=re.compile(r'^(\d+)\s+(\d+)/(\d+)$'); PF=re.compile(r'^(\d+)/(\d+)$')
def val(s):
    s=s.strip()
    if s in MISS: return None
    if s.isdigit(): return float(s)
    m=FR.match(s)
    if m and int(m.group(3)): return int(m.group(1))+int(m.group(2))/int(m.group(3))
    m=PF.match(s)
    if m and int(m.group(2)): return int(m.group(1))/int(m.group(2))
    return None
WIN=[("豁免 1650-1709",1650,1709),("后 1720-1779",1720,1779)]
fill=collections.defaultdict(collections.Counter)
cur=collections.defaultdict(collections.Counter)
ton=collections.defaultdict(list)
s2=collections.defaultdict(collections.Counter)
resid=collections.defaultdict(list)
n=collections.Counter()
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]])
        except (ValueError,IndexError): continue
        w=None
        for lab,a,b in WIN:
            if a<=y<=b: w=lab
        if w is None: continue
        n[w]+=1
        for c in ("tonnage","soort_korting","korting_bedrag1",
                  "subtotaal1_bedrag1","subtotaal2_bedrag1","totaal_bedrag1"):
            if row[ix[c]].strip() not in MISS: fill[w][c]+=1
        for c in ("subtotaal1_muntsoort1","subtotaal2_muntsoort1","totaal_muntsoort1"):
            v=row[ix[c]].strip()
            if v not in MISS: cur[w][c+"="+v]+=1
        t=val(row[ix["tonnage"]])
        if t: ton[w].append(t)
        # 三个都是 Daler 且无副单位时，看 s1+s2 与 totaal 的关系
        if (row[ix["subtotaal1_muntsoort1"]].strip()=="Daler"
            and row[ix["subtotaal2_muntsoort1"]].strip()=="Daler"
            and row[ix["totaal_muntsoort1"]].strip()=="Daler"
            and all(row[ix[c]].strip() in MISS for c in
                    ("subtotaal1_muntsoort2","subtotaal2_muntsoort2","totaal_muntsoort2"))):
            a,b,c2=val(row[ix["subtotaal1_bedrag1"]]),val(row[ix["subtotaal2_bedrag1"]]),val(row[ix["totaal_bedrag1"]])
            if None not in (a,b,c2):
                resid[w].append((a,b,c2,t))
                s2[w][round(b,2)]+=1
for w,_,_ in WIN:
    N=n[w]
    print("【%s】航次 %d" % (w,N))
    print("  填充率：", "  ".join("%s %.1f%%"%(c,100*fill[w][c]/N) for c in
        ("tonnage","soort_korting","korting_bedrag1","subtotaal1_bedrag1","subtotaal2_bedrag1","totaal_bedrag1")))
    print("  币种前三：", "; ".join("%s %d"%(k,v) for k,v in cur[w].most_common(6)))
    if ton[w]:
        t=sorted(ton[w]); print("  tonnage n=%d 中位 %.1f 四分位 %.1f / %.1f 区间 %.1f–%.1f"
              %(len(t),statistics.median(t),t[len(t)//4],t[3*len(t)//4],t[0],t[-1]))
    R=resid[w]
    print("  三项皆纯 Daler 的航次 %d" % len(R))
    if R:
        ok=sum(1 for a,b,c2,_ in R if abs(a+b-c2)<1e-9)
        print("  subtotaal1 + subtotaal2 == totaal 的占 %.2f%%" % (100*ok/len(R)))
        print("  subtotaal2 取值前八：", "; ".join("%s×%d"%(k,v) for k,v in s2[w].most_common(8)))
        b2=[b for a,b,c2,_ in R]; print("  subtotaal2 中位 %.3f" % statistics.median(b2))
        wt=[(b,t) for a,b,c2,t in R if t]
        if len(wt)>200:
            print("  subtotaal2 对 tonnage：", end="")
            for lo,hi in ((0,30),(30,60),(60,100),(100,200),(200,10000)):
                s=[b for b,t in wt if lo<=t<hi]
                if len(s)>=30: print(" [%d,%d) n=%d 中位 %.2f"%(lo,hi,len(s),statistics.median(s)), end="")
            print()
    print()
