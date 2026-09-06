# -*- coding: utf-8 -*-
"""R15c: the assessed share of provincial voyages against the year each port
was lost, and a check on whether the commodity field is readable at all.

The year series showed provincial voyages assessed at 4 to 9 per cent through
the 1690s and 17 to 19 per cent in 1703 to 1705. Sweden lost these places to
Russia in that order: Nyen and its district in 1703, Narva 1704, Riga and Reval
1710. If the assessed share is a port losing its status, each port should turn
on its own date rather than on a common one, and the ports lost in 1710 should
still be quiet in 1705. Printed per port per year, no threshold.

Also settles whether the alternative half of the treaty condition is readable:
if an unassessed voyage has no commodity recorded either, the cargo cannot be
compared between the two groups on this carrier at all.
"""
import csv, json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
D=json.load((CACHE/"b44_homeport_year.json").open(encoding="utf-8")); CTY=D["__country__"]
LOST={"Nyen":1703,"Narva":1704,"Reval":1710,"Riga":1710,"Pernau":1710,"Arensburg":1710}
grp={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]]); did=int(row[ix["id_doorvaart"]])
        except (ValueError,IndexError): continue
        if not (1660<=y<=1709): continue
        p=row[ix["schipper_plaatsnaam"]].strip(); k=home.get(p) or src.get(p)
        if not k: continue
        nm=std[k][0]
        if nm in LOST: grp[did]=(nm,y)
        elif CTY.get(nm)=="Sweden": grp[did]=("__homeland",y)
st=collections.defaultdict(lambda:[0,0,0])       # lines, aantal filled, soort filled
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,ian,iso=h.index("id_doorvaart"),h.index("aantal"),h.index("soort")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        if did not in grp: continue
        s=st[did]; s[0]+=1
        if row[ian].strip() not in MISS: s[1]+=1
        if row[iso].strip() not in MISS: s[2]+=1

print("=== is the commodity readable on an unassessed voyage? ===")
prov=[d for d,(n,_) in grp.items() if n in LOST and st[d][0]>0]
for lab,sel in (("assessed",lambda s:s[1]>0),("unassessed",lambda s:s[1]==0)):
    g=[st[d] for d in prov if sel(st[d])]
    if not g: continue
    print("  %-12s %5d voyages, %5.1f%% have any commodity named, %5.1f%% have any quantity"
          %(lab,len(g),100*sum(1 for s in g if s[2]>0)/len(g),100*sum(1 for s in g if s[1]>0)/len(g)))

print("\n=== assessed share per port per year (n printed, '.' when n<12) ===")
per=collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0]))
for d,(nm,y) in grp.items():
    if st[d][0]==0: continue
    c=per[nm][y]; c[0]+=1; c[1]+=(st[d][1]>0)
ys=list(range(1690,1710))
print("  %-12s %s"%("port"," ".join("%4d"%y for y in ys)))
for nm in ["Nyen","Narva","Riga","Reval","Pernau","__homeland"]:
    d=per.get(nm,{})
    cells=[]
    for y in ys:
        c=d.get(y)
        cells.append("%4s"%("."if not c or c[0]<12 else "%d%%"%round(100*c[1]/c[0])))
    print("  %-12s %s"%(nm," ".join(cells)))
print("\n  n per port per year, same grid")
for nm in ["Nyen","Narva","Riga","Reval","Pernau","__homeland"]:
    d=per.get(nm,{})
    print("  %-12s %s"%(nm," ".join("%4d"%(d.get(y,[0,0])[0]) for y in ys)))

print("\n=== how much of the provincial 11 per cent sits in the war years ===")
for lo,hi in [(1660,1689),(1690,1699),(1700,1702),(1703,1709)]:
    g=[d for d,(nm,y) in grp.items() if nm in LOST and lo<=y<=hi and st[d][0]>0]
    if not g: continue
    a=sum(1 for d in g if st[d][1]>0)
    print("  %d-%d  n=%-5d assessed %5.1f%%"%(lo,hi,len(g),100*a/len(g)))
