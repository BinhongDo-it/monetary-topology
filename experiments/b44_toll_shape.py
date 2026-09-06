# -*- coding: utf-8 -*-
"""东向那个 2.00 是不是一个固定下限费。印分布，不印统计量。"""
import csv, json, pathlib, collections
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8)
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
def num(s):
    s=s.strip().replace(",",".")
    try: return float(s)
    except ValueError:
        p=s.split()
        try: return float(p[0])
        except Exception: return None
amt={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,im,ib,iid=h.index("jaar"),h.index("totaal_muntsoort1"),h.index("totaal_bedrag1"),h.index("id_doorvaart")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1720<=y<=1780) or row[im].strip()!="Daler": continue
        a=num(row[ib])
        if a is None or a<=0: continue
        try: amt[int(row[iid])]=a
        except ValueError: pass
TARGET={frozenset(("Amsterdam","Danzig")),frozenset(("Amsterdam","Riga")),
        frozenset(("London","St. Petersborg"))}
dist=collections.defaultdict(collections.Counter); seen=set()
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina=h.index("id_doorvaart"),h.index("van"),h.index("naar")
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        if did not in amt or did in seen: continue
        a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
        if not a or not b or a==b: continue
        pr=frozenset((a,b))
        if pr not in TARGET: continue
        if a not in west or b not in west or west[a]==west[b]: continue
        seen.add(did)
        d="东向" if (west[a] and not west[b]) else "西向"
        dist[(tuple(sorted(pr)),d)][amt[did]]+=1
for k in sorted(dist,key=lambda k:(k[0],k[1])):
    c=dist[k]; n=sum(c.values())
    top=c.most_common(8)
    print("\n%-30s %-4s n=%5d  前 8 个取值（值:次数，占比）" % (" ↔ ".join(k[0]),k[1],n))
    print("   "+"  ".join("%.10g:%d(%.1f%%)"%(v,ct,100*ct/n) for v,ct in top))
    lo=sum(ct for v,ct in c.items() if v<=3.0)
    print("   <=3.00 Daler 的占 %.1f%%；不同取值 %d 个" % (100*lo/n,len(c)))
