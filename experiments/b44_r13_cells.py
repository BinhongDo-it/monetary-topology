# -*- coding: utf-8 -*-
"""R13 第一步：吨位归一化之后还剩几个格（第 13 条第 1 步：先量最坏那一格）。
只数，不算 rho。t/吨位 的单位是 Daler per læst。
tonnage 是自由文本（船名与吨位混在一起），用 \\d+ læster 的正则抽。"""
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
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
CO={"Sweden":"瑞","The Netherlands":"荷","United Kingdom":"英","Denmark":"丹","Norway":"挪","Germany":"德"}
WIN=[("豁免",1650,1709),("后",1720,1779)]
info={}; drop=collections.Counter()
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r); ix={c:i for i,c in enumerate(h)}
    for row in r:
        try: y=int(row[ix["jaar"]]); did=int(row[ix["id_doorvaart"]])
        except (ValueError,IndexError): continue
        w=None
        for lab,a,b in WIN:
            if a<=y<=b: w=lab
        if w is None: continue
        drop[w+" 窗口内"]+=1
        p=row[ix["schipper_plaatsnaam"]].strip(); k=home.get(p) or src.get(p)
        if not k: drop[w+" 籍不可解析"]+=1; continue
        m=LAST.search(row[ix["tonnage"]].strip())
        if not m: drop[w+" 吨位抽不出"]+=1; continue
        ton=val(m.group(1))
        if not ton or not (1<=ton<=1000): drop[w+" 吨位不合理"]+=1; continue
        if row[ix["totaal_muntsoort1"]].strip()!="Daler" or row[ix["totaal_muntsoort3"]].strip() not in MISS:
            drop[w+" 币种不合"]+=1; continue
        m2=row[ix["totaal_muntsoort2"]].strip()
        if m2 not in MISS and m2!="Skilling": drop[w+" 币种不合"]+=1; continue
        a1=val(row[ix["totaal_bedrag1"]]); a2=val(row[ix["totaal_bedrag2"]]) if m2=="Skilling" else 0.0
        if a1 is None or a2 is None: drop[w+" 金额不可解析"]+=1; continue
        info[did]=(w, CO.get(std[k][2],"余"), (a1+a2/B)/ton, ton)
        drop[w+" 留下"]+=1
for w,_,_ in WIN:
    print("【%s】" % w, "  ".join("%s %d"%(k.split(" ",1)[1],v) for k,v in drop.items() if k.startswith(w)))
cell=collections.defaultdict(list); seen=set()
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid,iv,ina=h.index("id_doorvaart"),h.index("van"),h.index("naar")
    for row in r:
        try: did=int(row[iid])
        except (ValueError,IndexError): continue
        if did in seen or did not in info: continue
        a=v2s.get(row[iv].strip()); b=v2s.get(row[ina].strip())
        if a in west and b in west and west[a]!=west[b]:
            seen.add(did); w,cls,rate,ton=info[did]
            cell[(w,"~".join(sorted((a,b))),cls,"东" if (west[a] and not west[b]) else "西")].append(rate)
print("\n穿海峡且四项都合格的航次 %d，格 %d" % (len(seen),len(cell)))
json.dump({"|".join(k):v for k,v in cell.items()},
          (CACHE/"b44_r13_cells.json").open("w",encoding="utf-8"),ensure_ascii=False)
ALL=["瑞","荷","英","丹","挪","德","余"]
def n(w,pr,cs,d): return sum(len(cell.get((w,pr,c,d),[])) for c in cs)
for w,_,_ in WIN:
    routes=sorted({k[1] for k in cell if k[0]==w})
    for lab,A,Bc in [("瑞 对 非瑞",["瑞"],[c for c in ALL if c!="瑞"]),
                     ("荷 对 非瑞非荷",["荷"],[c for c in ALL if c not in("瑞","荷")])]:
        q=[]
        for pr in routes:
            v=[n(w,pr,A,d) for d in ("东","西")]+[n(w,pr,Bc,d) for d in ("东","西")]
            q.append((min(v),tuple(pr.split("~")),v))
        q.sort(reverse=True)
        line=" ".join("四格>=%d: %d"%(t,sum(1 for x in q if x[0]>=t)) for t in (40,20,10,5))
        print("  %-4s %-12s %s" % (w,lab,line))
        for mn,pr,v in q[:4]:
            print("        最薄 %-4d %-30s %s" % (mn,"↔".join(pr)[:30],v))
r=[x for v in cell.values() for x in v]
r.sort(); print("\nt/吨位（Daler per læst）中位 %.4f 四分位 %.4f / %.4f 区间 %.4f–%.2f"
      %(statistics.median(r),r[len(r)//4],r[3*len(r)//4],r[0],r[-1]))
