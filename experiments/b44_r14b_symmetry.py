# -*- coding: utf-8 -*-
"""R14b: the safety check the class-dependent fixed fee forces.

The fixed component turns out to differ by class, about 4 Daler for the western
fleets and about one skilling per laest for the Scandinavian ones. A class-level
LEVEL difference still cancels from the double difference, but only if the fee is
symmetric in direction. If it is not, it enters S - S' directly and every reading
that treats it as cancelling is wrong by that amount. So: print the residual by
class and direction, and print what it is a function of.
"""
import csv, json, pathlib, collections, statistics, re
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); B=48.0; MISS={"","-","?","--"}
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
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
CO={"Sweden":"SE","The Netherlands":"NL","United Kingdom":"GB","Denmark":"DK","Norway":"NO","Germany":"DE"}
WIN=[("exemption",1650,1709),("post",1720,1779)]
info={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]]); did=int(row[ix["id_doorvaart"]])
        except (ValueError,IndexError): continue
        w=None
        for lab,a,b in WIN:
            if a<=y<=b: w=lab
        if w is None: continue
        if row[ix["totaal_muntsoort1"]].strip()!="Daler": continue
        if row[ix["totaal_muntsoort3"]].strip() not in MISS: continue
        m2=row[ix["totaal_muntsoort2"]].strip()
        if m2 not in MISS and m2!="Skilling": continue
        a1=val(row[ix["totaal_bedrag1"]]); a2=val(row[ix["totaal_bedrag2"]]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: continue
        p=row[ix["schipper_plaatsnaam"]].strip(); k=home.get(p) or src.get(p)
        info[did]=[w, CO.get(std[k][2],"XX") if k else "XX", a1+a2/B, 0.0, 0, True, None]
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid=h.index("id_doorvaart"); im1=h.index("muntsoort1"); ib1=h.index("bedrag1")
    im2=h.index("muntsoort2"); ib2=h.index("bedrag2"); im3=h.index("muntsoort3")
    iv,ina=h.index("van"),h.index("naar")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        rec=info.get(did)
        if rec is None: continue
        if rec[6] is None:
            a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
            if a in west and b in west and west[a]!=west[b]:
                rec[6]="east" if (west[a] and not west[b]) else "west"
        if row[im1].strip() in MISS: continue
        if row[im1].strip()!="Daler" or row[im3].strip() not in MISS: rec[5]=False; continue
        m2=row[im2].strip()
        if m2 not in MISS and m2!="Skilling": rec[5]=False; continue
        a1=val(row[ib1]); a2=val(row[ib2]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: rec[5]=False; continue
        rec[3]+=a1+a2/B; rec[4]+=1
rows=[(w,c,tot-cg,cg,np_,d) for w,c,tot,cg,np_,ok,d in info.values() if ok and d]
print("crossing voyages with a Daler total and every line parsable: %d"%len(rows))
print("\n=== residual by class and direction: does it cancel from the double difference? ===")
print("  %-10s %-4s %8s %10s %10s %12s"%("window","cls","n east","med east","med west","east-west"))
for wlab,_,_ in WIN:
    for c in ("SE","NL","GB","DK","NO","DE"):
        e=[r_ for w,cc,r_,_,_,d in rows if w==wlab and cc==c and d=="east"]
        wv=[r_ for w,cc,r_,_,_,d in rows if w==wlab and cc==c and d=="west"]
        if len(e)<80 or len(wv)<80: continue
        me,mw=statistics.median(e),statistics.median(wv)
        print("  %-10s %-4s %8d %10.3f %10.3f %12.3f"%(wlab,c,len(e),me,mw,me-mw))
print("\n=== what is the residual a function of? exemption window, non-Swedish ===")
sub=[(r_,cg,np_) for w,c,r_,cg,np_,d in rows if w=="exemption" and c in ("NL","GB")]
print("  by parcel count:")
for n in range(1,7):
    g=[r_ for r_,cg,np_ in sub if np_==n]
    if len(g)>=100: print("    %d parcel(s)  n=%-6d median residual %6.3f"%(n,len(g),statistics.median(g)))
print("  by cargo charge decile:")
s2=sorted(sub,key=lambda x:x[1]); k=len(s2)//10
for i in range(0,10,2):
    g=s2[i*k:(i+1)*k]
    if g: print("    decile %d  cargo %7.2f-%8.2f  median residual %6.3f"
                %(i+1,g[0][1],g[-1][1],statistics.median(x[0] for x in g)))
