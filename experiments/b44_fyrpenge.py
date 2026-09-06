# -*- coding: utf-8 -*-
"""那笔 2 Daler 是不是 fyrpenge。判别式：豁免期里有金额的瑞典籍航次，金额堆不堆在 2。
堆 => ω_a 不是 0，是那笔固定费，B44 的代入要改。"""
import csv, json, pathlib, collections
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8)
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
SWE={"Stockholm","Göteborg","Stralsund","Wismar","Greifswald","Malmö","Riga","Reval",
     "Landskrona","Kalmar","Norrköping","Geffle","Karlshamn","Karlskrona","Visby"}
def num(s):
    s=s.strip().replace(",",".")
    try: return float(s)
    except ValueError:
        p=s.split()
        try: return float(p[0])
        except Exception: return None
per=collections.defaultdict(collections.Counter)
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,isp,im,ib=h.index("jaar"),h.index("schipper_plaatsnaam"),h.index("totaal_muntsoort1"),h.index("totaal_bedrag1")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1780) or row[im].strip()!="Daler": continue
        a=num(row[ib])
        if a is None or a<=0: continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        nm=std[k][0] if k else None; co=std[k][2] if k else None
        cls="瑞" if (nm in SWE or co=="Sweden") else "非瑞"
        seg="豁免期 1650-1709" if y<=1709 else ("过渡 1710-19" if y<1720 else "后 1720-80")
        per[(seg,cls)][a]+=1
for seg in ("豁免期 1650-1709","过渡 1710-19","后 1720-80"):
    for cls in ("瑞","非瑞"):
        c=per.get((seg,cls))
        if not c: continue
        n=sum(c.values())
        eq2=c.get(2.0,0); le3=sum(v for k,v in c.items() if k<=3.0)
        print("\n%-18s %-4s n=%6d  ＝2.00 占 %5.1f%%   <=3.00 占 %5.1f%%   不同取值 %d"
              % (seg,cls,n,100*eq2/n,100*le3/n,len(c)))
        print("   前 8：", "  ".join("%.10g:%d(%.1f%%)"%(v,ct,100*ct/n) for v,ct in c.most_common(8)))
