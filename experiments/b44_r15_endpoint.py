# -*- coding: utf-8 -*-
"""R15: why 11 per cent of Baltic-province voyages were assessed.

Hypothesis, taken from the literature before this was run: the exemption was not
granted on the flag alone. One account states it covered Swedish bottoms carrying
cargo "to and from Sweden", which makes the voyage's endpoints part of the
condition. An entrepot in the Baltic provinces sends most of its traffic between
two non-Swedish places, so on that reading a provincial voyage qualifies only
when one end is in Sweden.

Two definitions of "in Sweden" are printed side by side, because the whole
question is whether the possessions counted:
  A  Sweden proper, the modern country
  B  the whole realm, Sweden proper plus the named possessions

Three outcomes reachable: assessed voyages are disproportionately those with no
Swedish endpoint (the condition explains it); the endpoint mix is the same for
both (it does not); or assessed voyages are disproportionately Swedish-endpoint
(something else). Criterion is the printed table, no threshold.
"""
import csv, json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
D=json.load((CACHE/"b44_homeport_year.json").open(encoding="utf-8"))
CTY=D["__country__"]
EXTRA={"Stralsund":"Pomerania","Stettin":"Pomerania","Greifswald":"Pomerania",
 "Anklam":"Pomerania","Demmin":"Pomerania","Wolgast":"Pomerania","Barth":"Pomerania",
 "Wismar":"Wismar","Riga":"Livonia","Pernau":"Livonia","Reval":"Estonia","Narva":"Estonia",
 "Arensburg":"Osel","Nyen":"Ingria","Åbo":"Finland","Helsingfors":"Finland",
 "Viborg":"Finland","Björneborg":"Finland","Stade":"Bremen-Verden","Buxtehude":"Bremen-Verden"}
PROV={"Riga","Reval","Narva","Nyen","Pernau","Arensburg"}
def proper(nm): return CTY.get(nm)=="Sweden"
def realm(nm):  return proper(nm) or nm in EXTRA

# home port class of each voyage in the window
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
        if nm in PROV: grp[did]=("provinces",nm)
        elif proper(nm): grp[did]=("homeland",nm)
        elif nm in ("Amsterdam","Lübeck"): grp[did]=("control",nm)
print("voyages in scope 1660-1709: %d"%len(grp))

# per voyage: was anything measured, and where did it come from and go to
st=collections.defaultdict(lambda:[0,0,set(),set()])   # lines, filled, vans, naars
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina,ian=h.index("id_doorvaart"),h.index("van"),h.index("naar"),h.index("aantal")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        if did not in grp: continue
        s=st[did]; s[0]+=1
        if row[ian].strip() not in MISS: s[1]+=1
        a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
        if a: s[2].add(a)
        if b: s[3].add(b)

def endpoint(s,test):
    return any(test(x) for x in s[2]) or any(test(x) for x in s[3])

for label in ("provinces","homeland","control"):
    ids=[d for d,(g,_) in grp.items() if g==label and st[d][0]>0]
    print("\n=== %s, %d voyages with at least one cargo line ==="%(label,len(ids)))
    for tname,test in (("A  an endpoint in Sweden proper",proper),
                       ("B  an endpoint anywhere in the realm",realm)):
        tab=collections.Counter()
        for d in ids:
            s=st[d]
            assessed = s[1]>0                      # anything measured at all
            tab[(endpoint(s,test),assessed)]+=1
        print("  %s"%tname)
        print("     %-22s %10s %10s %10s"%("","not assessed","assessed","assessed %"))
        for has in (True,False):
            n0,n1=tab[(has,False)],tab[(has,True)]
            if n0+n1==0: continue
            print("     %-22s %10d %10d %9.1f%%"
                  %("yes" if has else "no",n0,n1,100*n1/(n0+n1)))
