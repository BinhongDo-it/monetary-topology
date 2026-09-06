# -*- coding: utf-8 -*-
"""R17: the measured per-laest rate printed in both skilling, against the
published figure.

R14 read the fixed component at about one skilling per laest above 20 laester
and recorded a discrepancy against a published schedule that gives two. The
conversion base this station identified is 48 to the Daler, and R9's external
chain says why: the accounts are kept in Lubeck skilling, one of which is two
Danish. So a rate the station reads as one is two in the other unit, and the
question is only which unit the published figure is quoted in.

Nothing is decided here. Both columns are printed so a reader can see that the
gap is exactly the factor the two units differ by, rather than a residual to be
explained by something else.
"""
import csv, json, pathlib, re, statistics
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
LYBSK_PER_DALER = 48.0        # identified in R3, confirmed by an external chain in R9
DANISH_PER_LYBSK = 2.0        # 1 daler = 96 Danish = 48 Lubeck
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
info={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]]); did=int(row[ix["id_doorvaart"]])
        except (ValueError,IndexError): continue
        if not (1650<=y<=1779): continue
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
        info[did]=[a1+a2/LYBSK_PER_DALER, ton, 0.0, True]
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid=h.index("id_doorvaart"); i1=h.index("muntsoort1"); j1=h.index("bedrag1")
    i2=h.index("muntsoort2"); j2=h.index("bedrag2"); i3=h.index("muntsoort3")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        rec=info.get(did)
        if rec is None: continue
        if row[i1].strip() in MISS: continue
        if row[i1].strip()!="Daler" or row[i3].strip() not in MISS: rec[3]=False; continue
        m2=row[i2].strip()
        if m2 not in MISS and m2!="Skilling": rec[3]=False; continue
        a=val(row[j1]); b=val(row[j2]) if m2=="Skilling" else 0.0
        if a is None or b is None: rec[3]=False; continue
        rec[2]+=a+b/LYBSK_PER_DALER
rows=[(tot-cg,ton) for tot,ton,cg,ok in info.values() if ok]
print("voyages with a burden and a fully parsable Daler total: %d\n"%len(rows))
print("  %-11s %6s %9s %11s %14s %16s"
      %("burden","n","median t","median res","Lubeck sk/laest","Danish sk/laest"))
for lo,hi in [(20,29),(30,49),(50,99),(100,1000)]:
    g=[(r_,t_) for r_,t_ in rows if lo<=t_<=hi]
    if len(g)<100: continue
    mr=statistics.median(x for x,_ in g); mt=statistics.median(t for _,t in g)
    lyb=LYBSK_PER_DALER*mr/mt
    print("  %-11s %6d %9.1f %11.3f %14.2f %16.2f"
          %("%d-%d"%(lo,hi),len(g),mt,mr,lyb,lyb*DANISH_PER_LYBSK))
big=[(r_,t_) for r_,t_ in rows if t_>=20]
mr=statistics.median(x for x,_ in big); mt=statistics.median(t for _,t in big)
lyb=LYBSK_PER_DALER*mr/mt
print("\n  pooled at 20 laester and above: n=%d, %.2f Lubeck skilling per laest, "
      "%.2f Danish"%(len(big),lyb,lyb*DANISH_PER_LYBSK))
print("  the published schedule gives 2 skilling per laest for a laden ship.")
print("  Danish column against that figure: %+.1f per cent."%(100*(lyb*DANISH_PER_LYBSK-2)/2))
