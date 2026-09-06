# -*- coding: utf-8 -*-
"""R10 自查：把写进结果件的数从原件重算，逐条 assert。"""
import csv, json, pathlib, collections, statistics
import os
_H=pathlib.Path(__file__).resolve().parent
RAW=_H.parent/"data/raw/stro/classic"; CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
BALT={"Riga","Reval","Narva","Nyen","Pernau"}; MAIN={"Stockholm","Göteborg","Norrköping","Kalmar","Kungsbacka"}
CTRL={"Amsterdam","Lübeck"}
id2={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid,isp=h.index("jaar"),h.index("id_doorvaart"),h.index("schipper_plaatsnaam")
    for row in r:
        try: y=int(row[iy]); did=int(row[iid])
        except (ValueError,IndexError): continue
        if not (1660<=y<=1709): continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        if not k: continue
        nm=std[k][0]
        if nm in BALT or nm in MAIN or nm in CTRL: id2[did]=nm
per=collections.defaultdict(lambda:[0,0])
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,ia=h.index("id_doorvaart"),h.index("aantal")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        if did not in id2: continue
        c=per[did]; c[0]+=1
        if row[ia].strip() not in MISS: c[1]+=1
CHK=[]
def eq(l,g,w,tol=5e-4): CHK.append((((abs(g-w)<=tol) if isinstance(w,float) else (g==w)),l,g,w))
def sel(pred): return [(n,k) for did,(n,k) in per.items() if n>0 and pred(id2[did])]
for lab,pred,nv,z,one in [("诸省",lambda x:x in BALT,1515,0.883,0.107),
                          ("本土",lambda x:x in MAIN,14109,0.979,0.019),
                          ("对照 Amsterdam",lambda x:x=="Amsterdam",3954,0.184,0.776),
                          ("对照 Lübeck",lambda x:x=="Lübeck",2163,0.134,0.808)]:
    v=sel(pred); eq(lab+" 航次数",len(v),nv)
    eq(lab+" 恰好0",sum(1 for n,k in v if k==0)/len(v),z,5e-4)
    eq(lab+" 恰好1",sum(1 for n,k in v if k==n)/len(v),one,5e-4)
    eq(lab+" 中间两档合计<6%",sum(1 for n,k in v if 0<k<n)/len(v)<0.06,True)
for nm,nv,z in [("Riga",838,0.884),("Reval",246,0.882),("Narva",217,0.885),("Nyen",200,0.880),
                ("Stockholm",6915,0.975),("Kungsbacka",4750,0.995),("Göteborg",1339,0.957)]:
    v=sel(lambda x,t=nm:x==t); eq(nm+" 航次",len(v),nv)
    eq(nm+" 恰好0",sum(1 for n,k in v if k==0)/len(v),z,5e-4)
b=[z for nm,nv,z in [("Riga",0,0.884),("Reval",0,0.882),("Narva",0,0.885),("Nyen",0,0.880)]]
eq("四个诸省港 恰好0 跨度<0.006",max(b)-min(b)<0.006,True)
for lab,pred,nz,mz,no,mo in [("诸省",lambda x:x in BALT,1337,1.0,162,3.0),
                             ("本土",lambda x:x in MAIN,13819,1.0,265,2.0)]:
    v=sel(pred); Z=[n for n,k in v if k==0]; O=[n for n,k in v if k==n]
    eq(lab+" 全不量航次",len(Z),nz); eq(lab+" 全不量中位parcel",statistics.median(Z),mz)
    eq(lab+" 全量航次",len(O),no); eq(lab+" 全量中位parcel",statistics.median(O),mo)
for lab,pred,pf,vf in [("诸省",lambda x:x in BALT,0.3300,0.1069),("本土",lambda x:x in MAIN,0.0583,0.0188)]:
    v=sel(pred); eq(lab+" 逐parcel填充",sum(k for n,k in v)/sum(n for n,k in v),pf)
    eq(lab+" 逐航次全量占",sum(1 for n,k in v if k==n)/len(v),vf)
c=sel(lambda x:x in CTRL); base=sum(1 for n,k in c if k==0)/len(c)
eq("对照基线",base,0.1661)
m=sel(lambda x:x in MAIN); s=sel(lambda x:x in BALT)
mz=sum(1 for n,k in m if k==0)/len(m); sz=sum(1 for n,k in s if k==0)/len(s)
eq("本土 归一化",(mz-base)/(1-base),0.975,1e-3); eq("诸省 归一化",(sz-base)/(1-base),0.859,1e-3)
eq("诸省/本土",((sz-base)/(1-base))/((mz-base)/(1-base)),0.881,1e-3)
bad=[x for x in CHK if not x[0]]
for ok,l,g,w in CHK:
    print("%s %-26s 得 %-10s 应 %s"%("OK " if ok else "!!!",l,("%.4f"%g) if isinstance(g,float) else g,
          ("%.4f"%w) if isinstance(w,float) else w))
print("\n%d 条检查，%d 条不过"%(len(CHK),len(bad)))
# write-up cross-check: the numbers this script recomputes must also appear
# in the station's write-up. Path comes from the environment so this file
# names no document of its own.
need=["88.3%","10.7%","97.9%","88.4%","88.2%","88.5%","88.0%","0.3300","0.1069","0.1661","0.881","3.00"]
w=os.environ.get("B44_WRITEUP")
if w:
    t=pathlib.Path(w).read_text(encoding="utf-8")
    m=[s for s in need if s not in t]
    print("write-up missing:",m or "none")
else:
    m=[]; print("write-up check skipped (set B44_WRITEUP to a path to run it)")
raise SystemExit(1 if (bad or m) else 0)
