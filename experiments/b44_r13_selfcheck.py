# -*- coding: utf-8 -*-
"""R13 自查：吨位记录与船籍类共线这件事，换一条路再数一遍；顺带把
「共线」与「窗口效应」分开（若吨位缺失是早期档案的性质，那它该随年份走而不随类走）。
断言不通过就 raise。"""
import csv, json, pathlib, collections, re, statistics
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent/"data/raw/stro/classic"
CACHE = _H.parent/"data/cache/stro_classic"
csv.field_size_limit(10**8); MISS={"","-","?","--"}
LAST=re.compile(r'(\d+(?:\s*\d+/\d+)?)\s*(?:l[æae]ster|lester|læst|lest)\b', re.I)
OK=[]; BAD=[]
def ck(c,m):
    (OK if c else BAD).append(m)
    print(("  OK  " if c else "  ×   ")+m)

M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
CO={"Sweden":"瑞","The Netherlands":"荷","United Kingdom":"英","Denmark":"丹","Norway":"挪","Germany":"德"}
WIN=[("豁免",1650,1709),("后",1720,1779)]

# ---- 第一路：直接扫原件，逐类 / 逐窗 / 逐十年 数「吨位抽得出」的比例
cls_tot=collections.Counter(); cls_ton=collections.Counter()
cw_tot=collections.Counter(); cw_ton=collections.Counter()
dec_tot=collections.Counter(); dec_ton=collections.Counter()
port_tot=collections.Counter(); port_ton=collections.Counter()
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]])
        except (ValueError,IndexError): continue
        w=None
        for lab,a,b in WIN:
            if a<=y<=b: w=lab
        if w is None: continue
        p=row[ix["schipper_plaatsnaam"]].strip(); k=home.get(p) or src.get(p)
        if not k: continue
        c=CO.get(std[k][2],"余"); hit=1 if LAST.search(row[ix["tonnage"]].strip()) else 0
        cls_tot[c]+=1; cls_ton[c]+=hit
        cw_tot[(c,w)]+=1; cw_ton[(c,w)]+=hit
        d=(y//10)*10; dec_tot[d]+=1; dec_ton[d]+=hit
        port_tot[(c,std[k][0])]+=1; port_ton[(c,std[k][0])]+=hit

print("【逐类　吨位抽得出的比例】")
order=sorted(cls_tot,key=lambda c:-cls_tot[c])
for c in order:
    print("  %-3s n=%-8d %5.1f%%   豁免 %5.1f%%  后 %5.1f%%" % (
        c, cls_tot[c], 100*cls_ton[c]/cls_tot[c],
        100*cw_ton[(c,"豁免")]/max(cw_tot[(c,"豁免")],1),
        100*cw_ton[(c,"后")]/max(cw_tot[(c,"后")],1)))
rate={c:cls_ton[c]/cls_tot[c] for c in cls_tot}
ck(rate["荷"]<0.01 and rate["英"]<0.01, "荷与英的吨位记录率都低于 1%%（荷 %.3f%% 英 %.3f%%）"%(100*rate["荷"],100*rate["英"]))
ck(rate["挪"]>0.7 and rate["丹"]>0.6, "挪与丹都高于 60%%（挪 %.1f%% 丹 %.1f%%）"%(100*rate["挪"],100*rate["丹"]))
ck(rate["挪"]/max(rate["荷"],1e-9)>100, "最高类与最低类之比大于 100 倍（%.0f 倍）"%(rate["挪"]/max(rate["荷"],1e-9)))
ck(0.15<rate["瑞"]<0.30, "瑞落在 15%%–30%%（%.1f%%）"%(100*rate["瑞"]))

# 共线 vs 窗口：同一类在两窗口之间动多少，对比类间动多少
within=max(abs(cw_ton[(c,"豁免")]/max(cw_tot[(c,"豁免")],1)-cw_ton[(c,"后")]/max(cw_tot[(c,"后")],1)) for c in cls_tot)
between=max(rate.values())-min(rate.values())
print("\n【类内跨窗最大变动 %.3f　类间最大变动 %.3f】"%(within,between))
ck(between>within, "类间的变动大于任何一类自己跨窗的变动（%.3f > %.3f）"%(between,within))

print("\n【逐十年】", "  ".join("%d %.0f%%"%(d,100*dec_ton[d]/dec_tot[d]) for d in sorted(dec_tot) if dec_tot[d]>2000))
dv=[dec_ton[d]/dec_tot[d] for d in sorted(dec_tot) if dec_tot[d]>2000]
ck(max(dv)-min(dv) < between, "逐十年的极差小于类间极差（%.3f < %.3f）"%(max(dv)-min(dv),between))

print("\n【逐籍港，n>=800，高五低五】")
ps=sorted(((port_ton[k]/port_tot[k],port_tot[k],k) for k in port_tot if port_tot[k]>=800),reverse=True)
for r_,n_,k in ps[:5]: print("  高 %-22s %-3s n=%-6d %5.1f%%"%(k[1][:22],k[0],n_,100*r_))
for r_,n_,k in ps[-5:]: print("  低 %-22s %-3s n=%-6d %5.1f%%"%(k[1][:22],k[0],n_,100*r_))
ck(all(p[2][0] in ("挪","丹","瑞") for p in ps[:5]), "记录率最高的五个籍港全部是斯堪的纳维亚的类")
ck(all(p[2][0] in ("荷","英","德","余") for p in ps[-5:]), "记录率最低的五个籍港一个斯堪的纳维亚的都没有")

# ---- 第二路：从 R13 的缓存重数格，看主对与安慰剂各剩几条航线
cell=json.load((CACHE/"b44_r13_cells.json").open(encoding="utf-8"))
cell={tuple(k.split("|")):v for k,v in cell.items()}
ALL=["瑞","荷","英","丹","挪","德","余"]
def n(w,pr,cs,d): return sum(len(cell.get((w,pr,c,d),[])) for c in cs)
def counts(w,A,Bc):
    routes=sorted({k[1] for k in cell if k[0]==w})
    q=[min([n(w,pr,A,d) for d in ("东","西")]+[n(w,pr,Bc,d) for d in ("东","西")]) for pr in routes]
    return {t:sum(1 for x in q if x>=t) for t in (40,20,10,5)}
print("\n【从缓存重数】")
res={}
for w,_,_ in WIN:
    for lab,A,Bc in [("瑞 对 非瑞",["瑞"],[c for c in ALL if c!="瑞"]),
                     ("荷 对 非瑞非荷",["荷"],[c for c in ALL if c not in("瑞","荷")]),
                     ("瑞 对 丹",["瑞"],["丹"]), ("瑞 对 挪",["瑞"],["挪"]), ("丹 对 挪",["丹"],["挪"])]:
        c_=counts(w,A,Bc); res[(w,lab)]=c_
        print("  %-4s %-12s %s"%(w,lab," ".join(">=%d: %d"%(t,c_[t]) for t in (40,20,10,5))))
ck(res[("豁免","瑞 对 非瑞")][40]==0 and res[("后","瑞 对 非瑞")][40]==0, "主对在两窗口的 n>=40 都是零条航线")
ck(all(res[(w,"荷 对 非瑞非荷")][t]==0 for w,_,_ in WIN for t in (40,20,10,5)), "安慰剂在两窗口、四个门槛上全部是零条航线")
ck(res[("后","丹 对 挪")][40]>=5, "丹对挪在后窗口 n>=40 有 %d 条"%res[("后","丹 对 挪")][40])
ck(res[("后","瑞 对 丹")][40]==0 and res[("后","瑞 对 挪")][40]==0, "凡是含瑞的对，n>=40 一律零条")

r=sorted(x for v in cell.values() for x in v)
med=statistics.median(r)
print("\n【t/吨位】 n=%d 中位 %.4f 四分位 %.4f/%.4f"%(len(r),med,r[len(r)//4],r[3*len(r)//4]))
ck(0.04<med<0.07, "每 læst 的中位通行费落在 0.04–0.07 Daler（%.4f）"%med)

print("\n%d 条通过，%d 条不通过"%(len(OK),len(BAD)))
if BAD: raise SystemExit("自查未过：\n"+"\n".join(BAD))
