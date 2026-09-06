# -*- coding: utf-8 -*-
"""E3 的作用域修正：原判据比的是相隔七十年的两个窗口，却把变动归给 1720 那一年，分不开。
按十年重建格，在同一批圈上逐十年读归一化比 |Σŵ|/Σ|ŵ|，看它是在 1720 有台阶还是一路在漂。
口径与 b44_r5_cells2.py 完全一致，只把窗口换成十年。"""
import csv, json, pathlib, collections, re, statistics
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
csv.field_size_limit(10**8)
B=48.0; MISS={"","-","?","--"}
FR=re.compile(r'^(\d+)\s+(\d+)/(\d+)$'); PF=re.compile(r'^(\d+)/(\d+)$')
BAD=[]
def val(s):
    s=s.strip()
    if s in MISS: return None
    if s.isdigit(): return float(s)
    m=FR.match(s)
    if m:
        if int(m.group(3))==0: BAD.append(s); return None   # 原件里有分母为零的分数
        return int(m.group(1))+int(m.group(2))/int(m.group(3))
    m=PF.match(s)
    if m:
        if int(m.group(2))==0: BAD.append(s); return None
        return int(m.group(1))/int(m.group(2))
    return None
M=json.load((CACHE/"place_std_map.json").open(encoding="utf-8"))
home,src,std=M["home"],M["src"],M["std"]
v2s=json.load((CACHE/"van2std.json").open(encoding="utf-8"))
west={}
with (RAW/"places_standard.csv").open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f,delimiter=";"):
        west[row["Stednavn"].strip()]=row["west_of_Helsingør"].strip().lower()=="true"
P=CACHE/"b44_r8_decade.json"
if not P.exists():
    info={}
    with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
        r=csv.reader(f,delimiter=";"); h=next(r)
        iy,iid,isp=h.index("jaar"),h.index("id_doorvaart"),h.index("schipper_plaatsnaam")
        im1,ib1=h.index("totaal_muntsoort1"),h.index("totaal_bedrag1")
        im2,ib2=h.index("totaal_muntsoort2"),h.index("totaal_bedrag2"); im3=h.index("totaal_muntsoort3")
        for row in r:
            try: y=int(row[iy]); did=int(row[iid])
            except (ValueError,IndexError): continue
            if not (1620<=y<=1789): continue
            p=row[isp].strip(); k=home.get(p) or src.get(p)
            if not k: continue
            swe = std[k][2]=="Sweden"
            if row[im1].strip()!="Daler" or row[im3].strip() not in MISS: continue
            m2=row[im2].strip()
            if m2 not in MISS and m2!="Skilling": continue
            a1=val(row[ib1]); a2=val(row[ib2]) if m2=="Skilling" else 0.0
            if a1 is None or a2 is None: continue
            info[did]=(y//10*10, "瑞" if swe else "非瑞", a1+a2/B)
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
                seen.add(did); dec,cls,t=info[did]
                cell["%d|%s|%s|%s"%(dec,"~".join(sorted((a,b))),cls,"东" if (west[a] and not west[b]) else "西")].append(t)
    P.write_text(json.dumps(cell,ensure_ascii=False),encoding="utf-8")
    print("分母为零的分数记录 %d 条：%s" % (len(BAD), sorted(set(BAD))[:8]))
    print("落缓存 b44_r8_decade.json：%d 个格，%.1f MB"%(len(cell),P.stat().st_size/1e6))
C=json.load(P.open(encoding="utf-8"))
def v(dec,pr,d): return C.get("%d|%s|非瑞|%s"%(dec,pr,d),[])
CYC=[["Königsberg","Bremen","Danzig","Amsterdam","Königsberg"],
     ["København","Amsterdam","Danzig","Bordeaux","København"],
     ["Libau","Bremen","Danzig","Amsterdam","Libau"],
     ["Riga","Bremen","Danzig","Amsterdam","Riga"],
     ["Hull","Riga","Bremen","Danzig","Hull"],
     ["Riga","Bremen","Königsberg","London","Riga"],
     ["London","Königsberg","Bremen","Danzig","London"],
     ["Newcastle","Königsberg","Bremen","Danzig","Newcastle"]]
NM=20
print("\n【同一批圈，逐十年的归一化比 |Σŵ|/Σ|ŵ|（每条腿每方向 n>=%d 才算，n 不足印 ·）】"%NM)
decs=list(range(1620,1790,10))
print("%-46s %s"%("圈","".join("%8s"%("%ds"%d) for d in decs)))
allr=collections.defaultdict(list)
for cyc in CYC:
    out=[]
    for dec in decs:
        s=sc=0.0; okc=True
        for x,y in zip(cyc,cyc[1:]):
            pr="~".join(sorted((x,y))); e,w=v(dec,pr,"东"),v(dec,pr,"西")
            if len(e)<NM or len(w)<NM: okc=False; break
            h=0.5*(statistics.median(w)-statistics.median(e))
            s+=(1.0 if (west.get(x) and not west.get(y)) else -1.0)*h; sc+=abs(h)
        if okc and sc>0:
            out.append("%8.3f"%(abs(s)/sc)); allr[dec].append(abs(s)/sc)
        else: out.append("%8s"%"·")
    print("%-46s %s"%("→".join(cyc[:-1])[:46],"".join(out)))
print("%-46s %s"%("逐十年中位（可算的圈数在下一行）",
      "".join("%8s"%("%.3f"%statistics.median(allr[d]) if allr[d] else "·") for d in decs)))
print("%-46s %s"%("  可算圈数","".join("%8d"%len(allr[d]) for d in decs)))
pre=[x for d in decs if d<1720 for x in allr[d]]; post=[x for d in decs if d>=1720 for x in allr[d]]
print("\n1720 之前逐圈-十年 %d 个，中位 %.4f；1720 之后 %d 个，中位 %.4f"
      %(len(pre),statistics.median(pre),len(post),statistics.median(post)))
