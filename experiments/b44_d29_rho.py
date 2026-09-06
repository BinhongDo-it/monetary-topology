# -*- coding: utf-8 -*-
"""B44 开工第一件：D29，分母那一半取不取得到。
定义代入（b4_directed_edges.md §5.1）：豁免类 ω_a ≡ 0，非豁免类 ω_b 两向各带一次税。
  S − S'  = 东向税 − 西向税        指标部分
  −(S+S') = 东向税 + 西向税        摩擦部分
  rho     = |差| / 和              落在 [0,1]，Theorem 6(4) 自动满足
只取 Daler 计价的航次（第 18c 条：不同口径不混列）。"""
import csv, json, pathlib, collections, statistics
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8)
MISS={"","-","?","--"}
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
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

SWE={"Stockholm","Göteborg","Stralsund","Wismar","Greifswald","Malmö","Riga","Reval",
     "Landskrona","Kalmar","Norrköping","Geffle","Karlshamn","Karlskrona","Visby"}
info={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,isp,iid=h.index("jaar"),h.index("schipper_plaatsnaam"),h.index("id_doorvaart")
    im,ib=h.index("totaal_muntsoort1"),h.index("totaal_bedrag1")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1780): continue
        if row[im].strip()!="Daler": continue
        amt=num(row[ib])
        if amt is None or amt<=0: continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        nm=std[k][0] if k else None
        co=std[k][2] if k else None
        cls="瑞" if (nm in SWE or co=="Sweden") else "非瑞"
        try: info[int(row[iid])]=(y,cls,amt)
        except ValueError: pass
print("1650-1780 且 Daler 计价、金额为正的过海峡：%d" % len(info))

# 航线方向：用 van/naar 标准化后的 west_of_Helsingør
route=collections.defaultdict(lambda: collections.defaultdict(list))  # (无序对) -> (方向,类,期) -> [税]
seen=set()
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina=h.index("id_doorvaart"),h.index("van"),h.index("naar")
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        m=info.get(did)
        if not m or did in seen: continue
        a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
        if not a or not b or a==b: continue
        if a not in west or b not in west: continue
        if west[a]==west[b]: continue          # 只留真正穿越海峡的
        seen.add(did)
        y,cls,amt=m
        d="东向" if (west[a] and not west[b]) else "西向"
        per="豁免期" if y<=1709 else ("过渡" if y<1720 else "后 1720-80")
        route[frozenset((a,b))][(d,cls,per)].append(amt)
print("穿越海峡且两端可解析的过海峡 %d，无序航线对 %d" % (len(seen),len(route)))

rows=[]
for pr,d in route.items():
    for per in ("豁免期","后 1720-80"):
        e=d.get(("东向","非瑞",per),[]); w=d.get(("西向","非瑞",per),[])
        if len(e)<40 or len(w)<40: continue
        me,mw=statistics.median(e),statistics.median(w)
        rho=abs(me-mw)/(me+mw)
        rows.append((rho,tuple(sorted(pr)),per,len(e),len(w),me,mw))
rows.sort(key=lambda r:-(r[3]+r[4]))
print("\n【非豁免类的 rho ＝ |东−西| / (东+西)，中位税，Daler】")
print("%-34s %-11s %6s %6s %9s %9s %8s" % ("航线（无序对）","期","东 n","西 n","东中位","西中位","rho"))
for rho,pr,per,ne,nw,me,mw in rows[:22]:
    print("%-34s %-11s %6d %6d %9.2f %9.2f %8.4f" % (" ↔ ".join(pr)[:34],per,ne,nw,me,mw,rho))
if rows:
    rs=[r[0] for r in rows]
    print("\n合计 %d 个（航线 × 期）格，rho 中位 %.4f，四分位 %.4f / %.4f，最大 %.4f"
          % (len(rs),statistics.median(rs),sorted(rs)[len(rs)//4],sorted(rs)[3*len(rs)//4],max(rs)))
    for per in ("豁免期","后 1720-80"):
        g=[r[0] for r in rows if r[2]==per]
        if g: print("  %-11s %3d 格，rho 中位 %.4f" % (per,len(g),statistics.median(g)))
json.dump([[r[0],list(r[1]),r[2],r[3],r[4],r[5],r[6]] for r in rows],
          (CACHE/"b44_rho.json").open("w",encoding="utf-8"),ensure_ascii=False)
print("落缓存 b44_rho.json")
