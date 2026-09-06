# -*- coding: utf-8 -*-
"""R15b: the other half of the treaty condition, and the time path.

The endpoint test moved in the predicted direction and explained little, so the
remaining half of the stated condition is the cargo itself: the exemption is
recorded as covering Swedish bottoms AND Swedish commodities. The register names
the commodity on every line, so the composition of assessed against unassessed
provincial voyages is readable even though the owner is not.

Printed, not thresholded: the assessed rate by year, and the commodities most
over-represented on assessed voyages against unassessed ones in the same group.
"""
import csv, json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
D=json.load((CACHE/"b44_homeport_year.json").open(encoding="utf-8")); CTY=D["__country__"]
PROV={"Riga","Reval","Narva","Nyen","Pernau","Arensburg"}
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
        if nm in PROV: grp[did]=("provinces",y)
        elif CTY.get(nm)=="Sweden": grp[did]=("homeland",y)
st=collections.defaultdict(lambda:[0,0,collections.Counter()])
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,ian,iso=h.index("id_doorvaart"),h.index("aantal"),h.index("soort")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        if did not in grp: continue
        s=st[did]; s[0]+=1
        if row[ian].strip() not in MISS: s[1]+=1
        g=row[iso].strip()
        if g not in MISS: s[2][g]+=1

for label in ("provinces","homeland"):
    ids=[d for d,(g,_) in grp.items() if g==label and st[d][0]>0]
    by=collections.defaultdict(lambda:[0,0])
    for d in ids:
        c=by[grp[d][1]]; c[0]+=1; c[1]+= (st[d][1]>0)
    print("\n=== %s, assessed share by year (n>=40 only) ==="%label)
    ys=[y for y in sorted(by) if by[y][0]>=40]
    print("  "+"  ".join("%d:%.0f%%"%(y,100*by[y][1]/by[y][0]) for y in ys))
    tot=sum(by[y][0] for y in by); ass=sum(by[y][1] for y in by)
    print("  all years %d voyages, assessed %.1f%%"%(tot,100*ass/tot))

    A=collections.Counter(); N=collections.Counter()
    for d in ids:
        (A if st[d][1]>0 else N).update(set(st[d][2]))
    na=sum(1 for d in ids if st[d][1]>0); nn=len(ids)-na
    print("  commodities over-represented on assessed voyages (present on >=15 of them):")
    rows=[]
    for g,c in A.items():
        if c<15: continue
        pa=c/max(na,1); pn=N.get(g,0)/max(nn,1)
        rows.append((pa/max(pn,1e-9), g, c, 100*pa, 100*pn))
    rows.sort(reverse=True)
    for lift,g,c,pa,pn in rows[:8]:
        print("    %-26s on %4d assessed (%.1f%%) vs %.1f%% of unassessed   lift %.1fx"%(g[:26],c,pa,pn,lift))
    print("  most common on unassessed voyages, for contrast:")
    for g,c in N.most_common(6):
        print("    %-26s %.1f%% of unassessed vs %.1f%% of assessed"%(g[:26],100*c/max(nn,1),100*A.get(g,0)/max(na,1)))
