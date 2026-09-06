# -*- coding: utf-8 -*-
"""R14 first half: does the fixed component scale with burden?

R12 recorded a published fee schedule in which a laden ship's lighthouse due is
2 skilling per laest rather than a flat sum, and left one question open: whether
the fixed residual this station measured (a constant 4 in the exemption window)
is that due. It is a data question, not a literature one: the residual is
total minus the sum of parcel charges, and the burden is recoverable from the
free-text tonnage field for part of the corpus. Join them and look.

Criterion is to print the object, not to draw a line (rule 11): the residual's
median in each burden band, and the implied skilling per laest.
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
WIN=[("exemption",1650,1709),("post",1720,1779)]

# --- pass 1: voyages with a total in Daler, a burden, and a window
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
        m=LAST.search(row[ix["tonnage"]].strip())
        if not m: continue
        ton=val(m.group(1))
        if not ton or not (1<=ton<=1000): continue
        if row[ix["totaal_muntsoort1"]].strip()!="Daler": continue
        if row[ix["totaal_muntsoort3"]].strip() not in MISS: continue
        m2=row[ix["totaal_muntsoort2"]].strip()
        if m2 not in MISS and m2!="Skilling": continue
        a1=val(row[ix["totaal_bedrag1"]]); a2=val(row[ix["totaal_bedrag2"]]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: continue
        p=row[ix["schipper_plaatsnaam"]].strip(); k=home.get(p) or src.get(p)
        cls=CO.get(std[k][2],"XX") if k else "XX"
        info[did]=[w, cls, a1+a2/B, ton, 0.0, True]   # ..., cargo sum, all-parcels-parsable

# --- pass 2: sum the parcel charges
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid=h.index("id_doorvaart"); im1=h.index("muntsoort1"); ib1=h.index("bedrag1")
    im2=h.index("muntsoort2"); ib2=h.index("bedrag2"); im3=h.index("muntsoort3")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        rec=info.get(did)
        if rec is None: continue
        if row[im1].strip() in MISS: continue          # a line with no charge is fine
        if row[im1].strip()!="Daler" or row[im3].strip() not in MISS:
            rec[5]=False; continue
        m2=row[im2].strip()
        if m2 not in MISS and m2!="Skilling": rec[5]=False; continue
        a1=val(row[ib1]); a2=val(row[ib2]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: rec[5]=False; continue
        rec[4]+=a1+a2/B

rows=[(w,cls,tot-cargo,ton) for w,cls,tot,ton,cargo,ok in info.values() if ok]
print("voyages with a burden, a Daler total and every parcel line parsable: %d"%len(rows))

BANDS=[(1,9),(10,14),(15,19),(20,29),(30,49),(50,99),(100,1000)]
for wlab,_,_ in WIN:
    sub=[(res,ton) for w,cls,res,ton in rows if w==wlab]
    if not sub: continue
    print("\n=== %s window, n=%d ==="%(wlab,len(sub)))
    print("  %-12s %6s %10s %10s %12s %14s"%("burden","n","median t","median res","res/laest","skilling/laest"))
    for lo,hi in BANDS:
        g=[(r_,t_) for r_,t_ in sub if lo<=t_<=hi]
        if len(g)<30: continue
        mr=statistics.median(x for x,_ in g); mt=statistics.median(t for _,t in g)
        print("  %-12s %6d %10.1f %10.3f %12.4f %14.2f"
              %("%d-%d"%(lo,hi),len(g),mt,mr,mr/mt,48*mr/mt))
    # rank correlation between burden and residual, Spearman on ranks
    import math
    n=len(sub)
    rs=sorted(range(n),key=lambda i:sub[i][0]); rt=sorted(range(n),key=lambda i:sub[i][1])
    a=[0]*n; b=[0]*n
    for k,i in enumerate(rs): a[i]=k
    for k,i in enumerate(rt): b[i]=k
    ma=sum(a)/n; mb=sum(b)/n
    num=sum((a[i]-ma)*(b[i]-mb) for i in range(n))
    den=math.sqrt(sum((a[i]-ma)**2 for i in range(n))*sum((b[i]-mb)**2 for i in range(n)))
    print("  Spearman(residual, burden) = %+.4f"%(num/den))
    # what a flat fee would predict versus what 2 skilling per laest would
    flat=statistics.median(x for x,_ in sub)
    print("  median residual overall %.3f Daler; 2 skilling/laest on the median ship "
          "would be %.4f Daler"%(flat, 2*statistics.median(t for _,t in sub)/B))
