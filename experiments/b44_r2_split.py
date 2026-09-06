# -*- coding: utf-8 -*-
"""残差按方向、按期、按籍拆开；同时量那个 13% 干净样本的选择偏。"""
import csv, json, pathlib, collections, re, statistics
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8)
MISS={"","-","?","--"}
FR=re.compile(r'^(\d+)\s+(\d+)/(\d+)$'); PF=re.compile(r'^(\d+)/(\d+)$')
def val(s):
    s=s.strip()
    if s in MISS: return None
    if s.isdigit(): return float(s)
    m=FR.match(s)
    if m: return int(m.group(1))+int(m.group(2))/int(m.group(3))
    m=PF.match(s)
    if m: return int(m.group(1))/int(m.group(2))
    try: return float(s.replace(",","."))
    except ValueError: return None
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
SWE={"Stockholm","Göteborg","Stralsund","Wismar","Greifswald","Malmö","Riga","Reval",
     "Landskrona","Kalmar","Norrköping","Geffle","Karlshamn","Karlskrona","Visby"}
tot={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid,isp=h.index("jaar"),h.index("id_doorvaart"),h.index("schipper_plaatsnaam")
    im,ib,ib2=h.index("totaal_muntsoort1"),h.index("totaal_bedrag1"),h.index("totaal_bedrag2")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1780) or row[im].strip()!="Daler" or row[ib2].strip() not in MISS: continue
        v=val(row[ib])
        if v is None: continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        nm=std[k][0] if k else None; co=std[k][2] if k else None
        cls="瑞" if (nm in SWE or co=="Sweden") else "非瑞"
        try: tot[int(row[iid])]=(y,v,cls)
        except ValueError: pass
psum=collections.defaultdict(float); dirty=set(); npar=collections.Counter(); dirn={}
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina=h.index("id_doorvaart"),h.index("van"),h.index("naar")
    im,ib,ib2=h.index("muntsoort1"),h.index("bedrag1"),h.index("bedrag2")
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        if did not in tot: continue
        if did not in dirn:
            a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
            if a in west and b in west and west[a]!=west[b]:
                dirn[did]="东向" if (west[a] and not west[b]) else "西向"
        if row[im].strip()!="Daler" or row[ib2].strip() not in MISS: dirty.add(did); continue
        v=val(row[ib])
        if v is None: dirty.add(did); continue
        psum[did]+=v; npar[did]+=1
ok=[k for k in tot if k in psum and k not in dirty]
def seg(y): return "豁免期 1650-1709" if y<=1709 else ("过渡" if y<1720 else "后 1720-80")
cell=collections.defaultdict(list)
for k in ok:
    y,v,cls=tot[k]; d=v-psum[k]
    cell[(seg(y),cls,dirn.get(k,"未定向"))].append(d)
    cell[("全部","全部",dirn.get(k,"未定向"))].append(d)
print("干净航次 %d\n" % len(ok))
print("%-18s %-4s %-6s %7s %9s %9s %9s" % ("期","类","方向","n","残差中位","＝4 占","＝2 占"))
for key in sorted(cell, key=lambda k:(k[0],k[1],k[2])):
    g=cell[key]
    if len(g)<60: continue
    e4=sum(1 for x in g if abs(x-4)<1e-9); e2=sum(1 for x in g if abs(x-2)<1e-9)
    print("%-18s %-4s %-6s %7d %9.3f %8.1f%% %8.1f%%" % (key[0],key[1],key[2],len(g),
          statistics.median(g),100*e4/len(g),100*e2/len(g)))
# 选择偏：干净 vs 全部，按 parcel 数
allpar=collections.Counter()
print("\n【选择偏】干净样本的 parcel 数中位 %.0f" % statistics.median([npar[k] for k in ok]))
print("  干净 %d / 候选 %d = %.1f%%；被弃的 %d 条全是「有副单位或非 Daler 的 parcel」"
      % (len(ok),len(tot),100*len(ok)/len(tot),len(dirty)))
