# -*- coding: utf-8 -*-
"""R16: R4 recomputed with the fixed component measured per route and per
direction instead of assumed to be 4 in all four cells.

The selection logic is R4's, copied rather than rewritten, so the two columns
are the same routes and the same voyages. The only additions are that the
total is kept alongside the cargo charge, so the fixed component is
total minus cargo, and that the exempt class is kept rather than dropped, so
its own charge can be read where the route carries enough of it.
"""
import csv, json, pathlib, collections, re, statistics
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8)
B=48.0; MISS={"","-","?","--"}
FR=re.compile(r'^(\d+)\s+(\d+)/(\d+)$'); PF=re.compile(r'^(\d+)/(\d+)$')
def val(s):
    s=s.strip()
    if s in MISS: return None
    if s.isdigit(): return float(s)
    m=FR.match(s)
    if m: return int(m.group(1))+int(m.group(2))/int(m.group(3))
    m=PF.match(s)
    if m: return int(m.group(1))/int(m.group(2))
    return None
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
SWE={"Stockholm","Göteborg","Stralsund","Wismar","Greifswald","Malmö","Riga","Reval",
     "Landskrona","Kalmar","Norrköping","Geffle","Karlshamn","Karlskrona","Visby"}
keep=set(); TOT={}; GRP={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid,isp=h.index("jaar"),h.index("id_doorvaart"),h.index("schipper_plaatsnaam")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1709): continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        nm=std[k][0] if k else None; co=std[k][2] if k else None
        if nm in SWE or co=="Sweden":
            grp="SE"
        else:
            grp="OT"
        try: did=int(row[iid])
        except ValueError: continue
        if row[h.index("totaal_muntsoort1")].strip()!="Daler": continue
        if row[h.index("totaal_muntsoort3")].strip() not in MISS: continue
        m2=row[h.index("totaal_muntsoort2")].strip()
        if m2 not in MISS and m2!="Skilling": continue
        t1=val(row[h.index("totaal_bedrag1")])
        t2=val(row[h.index("totaal_bedrag2")]) if m2=="Skilling" else 0.0
        if t1 is None or t2 is None: continue
        TOT[did]=t1+t2/B; GRP[did]=grp
        if grp=="OT": keep.add(did)
cargo=collections.defaultdict(float); dirty=set(); dirn={}
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina=h.index("id_doorvaart"),h.index("van"),h.index("naar")
    i1,j1,i2,j2,i3=(h.index(x) for x in ("muntsoort1","bedrag1","muntsoort2","bedrag2","muntsoort3"))
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        if did not in TOT: continue
        if did not in dirn:
            a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
            if a in west and b in west and west[a]!=west[b]:
                dirn[did]=(frozenset((a,b)),"东向" if (west[a] and not west[b]) else "西向")
        if row[i1].strip()!="Daler" or row[i3].strip() not in MISS: dirty.add(did); continue
        m2=row[i2].strip()
        if m2 not in MISS and m2!="Skilling": dirty.add(did); continue
        a=val(row[j1]); b=val(row[j2]) if m2=="Skilling" else 0.0
        if a is None or b is None: dirty.add(did); continue
        cargo[did]+=a+b/B

ok=[k for k in cargo if k not in dirty and k in dirn and k in TOT]
route=collections.defaultdict(lambda: collections.defaultdict(list))
for k in ok:
    pr,d=dirn[k]; route[(pr,GRP[k])][d].append((cargo[k],TOT[k]))
rows=[]
for pr in sorted({p for p,g in route}, key=str):
    ot=route.get((pr,"OT"),{}); se=route.get((pr,"SE"),{})
    e,w=ot.get("\u4e1c\u5411",[]),ot.get("\u897f\u5411",[])
    if len(e)<40 or len(w)<40: continue
    E=statistics.median(x[0] for x in e); W=statistics.median(x[0] for x in w)
    fbE=statistics.median(x[1]-x[0] for x in e); fbW=statistics.median(x[1]-x[0] for x in w)
    se_e,se_w=se.get("\u4e1c\u5411",[]),se.get("\u897f\u5411",[])
    if len(se_e)>=5 and len(se_w)>=5:
        faE=statistics.median(x[1] for x in se_e); faW=statistics.median(x[1] for x in se_w); tag="measured"
    else:
        faE=faW=None; tag="4/4"
    rho_r4=abs(E-W)/(16+E+W)
    if faE is None: fa_e,fa_w=4.0,4.0
    else: fa_e,fa_w=faE,faW
    num=abs((fbE+E-fbW-W)-(fa_e-fa_w)); den=fa_e+fa_w+fbE+E+fbW+W
    rows.append((rho_r4,num/den,tuple(sorted(pr)),len(e),len(w),E,W,fbE,fbW,fa_e,fa_w,tag,len(se_e),len(se_w)))
rows.sort(key=lambda r:-(r[3]+r[4]))
print("\n%-30s %6s %6s %8s %8s %7s %7s %7s %7s %8s %8s"
      %("route","n E","n W","E","W","fix_e","fix_w","t_a_e","t_a_w","rho R4","rho meas"))
for r4,rm,pr,ne,nw,E,W,fbE,fbW,fae,faw,tag,se_e,se_w in rows:
    print("%-30s %6d %6d %8.3f %8.3f %7.3f %7.3f %7.3f %7.3f %8.4f %8.4f  %s"
          %(" / ".join(pr)[:30],ne,nw,E,W,fbE,fbW,fae,faw,r4,rm,tag+("" if tag=="4/4" else " (%d,%d)"%(se_e,se_w))))
a=[r[0] for r in rows]; b=[r[1] for r in rows]
print("\n  %d routes"%len(a))
print("  rho as R4 published it   median %.4f  quartiles %.4f / %.4f  range %.4f-%.4f"
      %(statistics.median(a),sorted(a)[len(a)//4],sorted(a)[3*len(a)//4],min(a),max(a)))
print("  rho with the fee measured median %.4f  quartiles %.4f / %.4f  range %.4f-%.4f"
      %(statistics.median(b),sorted(b)[len(b)//4],sorted(b)[3*len(b)//4],min(b),max(b)))
print("  per-route relative change: median %+.1f%%, range %+.1f%% to %+.1f%%"
      %(100*statistics.median((y-x)/x for x,y in zip(a,b)),
        100*min((y-x)/x for x,y in zip(a,b)),100*max((y-x)/x for x,y in zip(a,b))))
print("  fixed component over these routes: eastbound median %.3f, westbound median %.3f"
      %(statistics.median(r[7] for r in rows),statistics.median(r[8] for r in rows)))
