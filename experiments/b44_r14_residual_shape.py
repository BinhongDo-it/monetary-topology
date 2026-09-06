# -*- coding: utf-8 -*-
"""R14 second half: print the residual itself, by burden band and by class.

The banded medians look like a step function rather than a linear rate, and two
subsamples of this corpus disagree about the level, so the thing to do is print
the values (rule 11) instead of another summary.
"""
import csv, json, pathlib, collections, re, statistics
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); B=48.0; MISS={"","-","?","--"}
FR=re.compile(r'^(\d+)\s+(\d+)/(\d+)$'); PF=re.compile(r'^(\d+)/(\d+)$')
LAST=re.compile(r'(\d+(?:\s*\d+/\d+)?)\s*(?:l[æae]ster|lester|læst|lest)\b', re.I)
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
CO={"Sweden":"SE","The Netherlands":"NL","United Kingdom":"GB","Denmark":"DK",
    "Norway":"NO","Germany":"DE"}
info={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]]); did=int(row[ix["id_doorvaart"]])
        except (ValueError,IndexError): continue
        if not (1650<=y<=1709): continue
        if row[ix["totaal_muntsoort1"]].strip()!="Daler": continue
        if row[ix["totaal_muntsoort3"]].strip() not in MISS: continue
        m2=row[ix["totaal_muntsoort2"]].strip()
        if m2 not in MISS and m2!="Skilling": continue
        a1=val(row[ix["totaal_bedrag1"]]); a2=val(row[ix["totaal_bedrag2"]]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: continue
        m=LAST.search(row[ix["tonnage"]].strip())
        ton=val(m.group(1)) if m else None
        if ton is not None and not (1<=ton<=1000): ton=None
        p=row[ix["schipper_plaatsnaam"]].strip(); k=home.get(p) or src.get(p)
        cls=CO.get(std[k][2],"XX") if k else "XX"
        info[did]=[cls, a1+a2/B, ton, 0.0, True]
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid=h.index("id_doorvaart"); im1=h.index("muntsoort1"); ib1=h.index("bedrag1")
    im2=h.index("muntsoort2"); ib2=h.index("bedrag2"); im3=h.index("muntsoort3")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        rec=info.get(did)
        if rec is None: continue
        if row[im1].strip() in MISS: continue
        if row[im1].strip()!="Daler" or row[im3].strip() not in MISS: rec[4]=False; continue
        m2=row[im2].strip()
        if m2 not in MISS and m2!="Skilling": rec[4]=False; continue
        a1=val(row[ib1]); a2=val(row[ib2]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: rec[4]=False; continue
        rec[3]+=a1+a2/B
rows=[(c,tot-cg,ton) for c,tot,ton,cg,ok in info.values() if ok]
print("exemption window 1650-1709, every parcel line parsable: %d voyages, "
      "of which %d carry a burden"%(len(rows),sum(1 for _,_,t in rows if t)))

def top(vals,k=8):
    c=collections.Counter(round(v,4) for v in vals)
    n=len(vals)
    return "  ".join("%.4f:%.1f%%"%(v,100*m/n) for v,m in c.most_common(k))

print("\n=== the residual's own values, by burden band (with a burden) ===")
for lo,hi in [(1,9),(10,14),(15,19),(20,29),(30,49),(50,99),(100,1000)]:
    g=[r_ for _,r_,t in rows if t and lo<=t<=hi]
    if len(g)<30: continue
    print("  %-9s n=%-6d median %7.3f | %s"%("%d-%d"%(lo,hi),len(g),statistics.median(g),top(g)))

print("\n=== the residual's own values, by class ===")
by=collections.defaultdict(list)
for c,r_,t in rows: by[c].append(r_)
for c,g in sorted(by.items(),key=lambda kv:-len(kv[1])):
    if len(g)<200: continue
    print("  %-3s n=%-7d median %7.3f | %s"%(c,len(g),statistics.median(g),top(g,6)))

print("\n=== with a burden vs without, same window ===")
for lab,g in (("with a burden",[r_ for _,r_,t in rows if t]),
              ("without",     [r_ for _,r_,t in rows if not t])):
    print("  %-15s n=%-7d median %7.3f | %s"%(lab,len(g),statistics.median(g),top(g,6)))
