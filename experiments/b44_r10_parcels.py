# -*- coding: utf-8 -*-
"""R10 补两件：
 (1) 为什么逐 parcel 读 0.299 而逐航次只有 10.1% —— 交税的那些航次是不是 parcel 多？
 (2) 把「恰好 0」的比例对着对照组的基线归一化：诸省拿到的是本土那份待遇的几成？
    对照组也有约 15% 的航次恰好 0，那是档案本身的漏，不是豁免。"""
import csv, json, pathlib, collections, statistics
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
csv.field_size_limit(10**8); MISS = {"", "-", "?", "--"}
M = json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home, src, std = M["home"], M["src"], M["std"]
GRP = {**{p:"波罗的海诸省" for p in ("Riga","Reval","Narva","Nyen","Pernau")},
       **{p:"瑞典本土" for p in ("Stockholm","Göteborg","Norrköping","Kalmar","Kungsbacka")},
       "Amsterdam":"对照","Lübeck":"对照"}
id2 = {}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid,isp=h.index("jaar"),h.index("id_doorvaart"),h.index("schipper_plaatsnaam")
    for row in r:
        try: y=int(row[iy]); did=int(row[iid])
        except (ValueError,IndexError): continue
        if not (1660<=y<=1709): continue
        p=row[isp].strip(); k=home.get(p) or src.get(p)
        if not k: continue
        g=GRP.get(std[k][0])
        if g: id2[did]=g
per=collections.defaultdict(lambda:[0,0])
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,ia=h.index("id_doorvaart"),h.index("aantal")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        if did not in id2: continue
        c=per[did]; c[0]+=1
        if row[ia].strip() not in MISS: c[1]+=1
print("【(1) 每航次的 parcel 数：全不量的 对 全量的】")
print("%-14s %10s %10s %10s %10s %8s" % ("组","全不量 航次","中位 parcel","全量 航次","中位 parcel","倍数"))
agg=collections.defaultdict(lambda:[0,0])
for g in ("波罗的海诸省","瑞典本土","对照"):
    z=[n for did,(n,k) in per.items() if id2[did]==g and n>0 and k==0]
    o=[n for did,(n,k) in per.items() if id2[did]==g and n>0 and k==n]
    if not z or not o: continue
    mz,mo=statistics.median(z),statistics.median(o)
    print("%-14s %10d %10.1f %10d %10.1f %8.2f" % (g,len(z),mz,len(o),mo,mo/mz))
    # 逐 parcel 的填充率，用来对上 R6 第七款那个 0.299
    P=sum(n for did,(n,k) in per.items() if id2[did]==g and n>0)
    K=sum(k for did,(n,k) in per.items() if id2[did]==g and n>0)
    V=sum(1 for did,(n,k) in per.items() if id2[did]==g and n>0)
    Vf=sum(1 for did,(n,k) in per.items() if id2[did]==g and n>0 and k==n)
    agg[g]=[P,K,V,Vf]
print("\n【逐 parcel 与逐航次两种读法，并排】")
print("%-14s %12s %12s %12s %12s" % ("组","parcel 总数","逐 parcel 填充","航次数","逐航次 全量占"))
for g in ("波罗的海诸省","瑞典本土","对照"):
    P,K,V,Vf=agg[g]
    print("%-14s %12d %12.4f %12d %12.4f" % (g,P,K/P,V,Vf/V))
print("\n【(2) 对着对照组的基线归一化：诸省拿到的是本土那份待遇的几成】")
b0={}
for g in ("波罗的海诸省","瑞典本土","对照"):
    z=sum(1 for did,(n,k) in per.items() if id2[did]==g and n>0 and k==0)
    V=agg[g][2]; b0[g]=z/V
base=b0["对照"]
print("  对照组「恰好 0」基线 = %.4f（档案本身的漏，不是豁免）" % base)
for g in ("瑞典本土","波罗的海诸省"):
    ex=(b0[g]-base)/(1-base)
    print("  %-8s 恰好 0 = %.4f  =>  超出基线的部分占可能上限的 %.1f%%" % (g,b0[g],100*ex))
m=(b0["瑞典本土"]-base)/(1-base); s=(b0["波罗的海诸省"]-base)/(1-base)
print("  诸省 / 本土 = %.3f  —— 诸省拿到的是本土那份待遇的 %.1f 成" % (s/m,10*s/m))
