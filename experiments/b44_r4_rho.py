# -*- coding: utf-8 -*-
"""R4：用 B=48 把 Skilling 折进来，在豁免期上按 R2 第四款那个式子算 rho。
  E, W = 东向/西向的「按货征」部分 = Σ(bedrag1 + bedrag2/48)
  rho = |E − W| / (16 + E + W)         16 = 两类各自往返的两笔固定费 4
只用非豁免类的读数（豁免类按条约 ω_a 只剩固定费 4）。"""
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
keep=set()
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid,isp=h.index("jaar"),h.index("id_doorvaart"),h.index("schipper_plaatsnaam")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1709): continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        nm=std[k][0] if k else None; co=std[k][2] if k else None
        if nm in SWE or co=="Sweden": continue          # 只留非豁免类
        try: keep.add(int(row[iid]))
        except ValueError: pass
cargo=collections.defaultdict(float); dirty=set(); dirn={}
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina=h.index("id_doorvaart"),h.index("van"),h.index("naar")
    i1,j1,i2,j2,i3=(h.index(x) for x in ("muntsoort1","bedrag1","muntsoort2","bedrag2","muntsoort3"))
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        if did not in keep: continue
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
ok=[k for k in cargo if k not in dirty and k in dirn]
print("豁免期 1650-1709、非豁免类、Daler+Skilling 可折算、穿越海峡：%d 航次" % len(ok))
route=collections.defaultdict(lambda: collections.defaultdict(list))
for k in ok:
    pr,d=dirn[k]; route[pr][d].append(cargo[k])
rows=[]
for pr,d in route.items():
    e,w=d.get("东向",[]),d.get("西向",[])
    if len(e)<40 or len(w)<40: continue
    E,W=statistics.median(e),statistics.median(w)
    rows.append((abs(E-W)/(16+E+W),tuple(sorted(pr)),len(e),len(w),E,W))
rows.sort(key=lambda r:-(r[2]+r[3]))
print("\n【rho = |E−W| / (16+E+W)，E/W 为按货征部分的中位，Daler】")
print("%-32s %6s %6s %9s %9s %8s" % ("航线","东 n","西 n","E 中位","W 中位","rho"))
for rho,pr,ne,nw,E,W in rows[:18]:
    print("%-32s %6d %6d %9.3f %9.3f %8.4f" % (" ↔ ".join(pr)[:32],ne,nw,E,W,rho))
rs=[r[0] for r in rows]
print("\n航线格 %d 个；rho 中位 %.4f，四分位 %.4f / %.4f，最小 %.4f 最大 %.4f"
      % (len(rs),statistics.median(rs),sorted(rs)[len(rs)//4],sorted(rs)[3*len(rs)//4],min(rs),max(rs)))
print("对照 B13 载体实测 rho 中位 0.2000（b4_directed_edges.md §5）")
json.dump([[r[0],list(r[1]),r[2],r[3],r[4],r[5]] for r in rows],
          (CACHE/"b44_rho_v2.json").open("w",encoding="utf-8"),ensure_ascii=False)
