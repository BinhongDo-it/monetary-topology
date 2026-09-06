# -*- coding: utf-8 -*-
"""B44 设计件第 ② 格：闸门数。四个数，全是乘除法。
承重臂是 DiD：aantal 填充率，瑞典籍对尼德兰籍，三段（前 / 豁免 / 后）。"""
import csv, json, pathlib, collections, math
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
CACHE=_H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8)
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
MISS={"","-","?","--"}
SWE_TERR={"Stockholm","Göteborg","Stralsund","Wismar","Greifswald","Malmö","Riga","Reval",
          "Landskrona","Kalmar","Norrköping","Gefle","Geffle","Karlshamn","Karlskrona","Visby"}
def g(nm,co):
    if nm in SWE_TERR or co=="Sweden": return "瑞"
    if co=="The Netherlands": return "荷"
    return None
def seg(y):
    if 1630<=y<=1644: return "前 1630-44"
    if 1660<=y<=1709: return "豁免 1660-1709"
    if 1720<=y<=1779: return "后 1720-79"
    return None
id2={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,isp,iid=h.index("jaar"),h.index("schipper_plaatsnaam"),h.index("id_doorvaart")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        s=seg(y)
        if not s: continue
        p=row[isp].strip()
        if p in MISS: continue
        k=home.get(p) or src.get(p)
        if not k: continue
        nm,_,co=std[k]; a=g(nm,co)
        if not a: continue
        try: id2[int(row[iid])]=(s,a)
        except ValueError: pass
cell=collections.defaultdict(lambda:[0,0])
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,ia=h.index("id_doorvaart"),h.index("aantal")
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        m=id2.get(did)
        if not m: continue
        c=cell[m]; c[0]+=1
        if row[ia].strip() not in MISS: c[1]+=1
print("%-16s %-4s %10s %10s %8s %10s" % ("段","组","明细行 n","aantal","填充率","se"))
P={}
for s in ("前 1630-44","豁免 1660-1709","后 1720-79"):
    for a in ("瑞","荷"):
        n,k=cell[(s,a)]; p=k/n; se=math.sqrt(p*(1-p)/n)
        P[(s,a)]=(p,se,n)
        print("%-16s %-4s %10d %10d %8.4f %10.6f" % (s,a,n,k,p,se))
def did(s0,s1):
    (a0,e0,_),(b0,f0,_)=P[(s0,"瑞")],P[(s0,"荷")]
    (a1,e1,_),(b1,f1,_)=P[(s1,"瑞")],P[(s1,"荷")]
    d=(a1-b1)-(a0-b0); se=math.sqrt(e0**2+f0**2+e1**2+f1**2)
    return d,se
for lab,s0,s1 in (("进入豁免（前 → 豁免）","前 1630-44","豁免 1660-1709"),
                  ("退出豁免（豁免 → 后）","豁免 1660-1709","后 1720-79")):
    d,se=did(s0,s1)
    print("\n%s  DiD = %+.4f  se = %.6f  |t| = %.1f" % (lab,d,se,abs(d)/se))
    Z=1.645
    print("  闸二：Z90×se = %.6f；效应 |d| = %.4f => 效应 / (Z90×se) = %.0f 倍"
          % (Z*se,abs(d),abs(d)/(Z*se)))
    print("  闸三：功效 = Phi(|d|/se - Z90) = %.4f"
          % (0.5*(1+math.erf((abs(d)/se-Z)/math.sqrt(2)))))
print("\n闸六 分辨率底：单组 se 最大 %.6f，效应 %.4f，比 %.0f 倍"
      % (max(v[1] for v in P.values()), abs(did("前 1630-44","豁免 1660-1709")[0]),
         abs(did("前 1630-44","豁免 1660-1709")[0])/max(v[1] for v in P.values())))
print("n - k = %d - 4 = %d" % (sum(v[2] for v in P.values()), sum(v[2] for v in P.values())-4))
