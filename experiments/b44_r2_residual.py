# -*- coding: utf-8 -*-
"""B44 R2：把固定费与按货征的部分分开。
残差 = totaal_bedrag1 − Σ ladingen.bedrag1，只在两侧都是纯 Daler、无副单位的航次上算，
于是不需要任何 Skilling↔Daler 换算率（第 18c 条）。分数按 a b/c 正确解析。"""
import csv, json, pathlib, collections, re
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

# 一 收合格航次：totaal 纯 Daler、无 totaal_bedrag2
tot={}; bad=collections.Counter()
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid=h.index("jaar"),h.index("id_doorvaart")
    im,ib,ib2=h.index("totaal_muntsoort1"),h.index("totaal_bedrag1"),h.index("totaal_bedrag2")
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1780): continue
        if row[im].strip()!="Daler": bad["币种非 Daler"]+=1; continue
        if row[ib2].strip() not in MISS: bad["有副单位"]+=1; continue
        v=val(row[ib])
        if v is None: bad["金额解析不了"]+=1; continue
        try: tot[int(row[iid])]=(y,v)
        except ValueError: pass
print("1650-1780 合格航次（纯 Daler 无副单位、金额可解析）：%d" % len(tot))
print("  被挡下的：", bad.most_common())

# 二 逐航次加 parcel；只要有一条 parcel 不合格，整个航次弃掉
psum=collections.defaultdict(float); dirty=set(); nrow=0
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid=h.index("id_doorvaart"); im,ib,ib2=h.index("muntsoort1"),h.index("bedrag1"),h.index("bedrag2")
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        if did not in tot: continue
        nrow+=1
        if row[im].strip()!="Daler" or row[ib2].strip() not in MISS: dirty.add(did); continue
        v=val(row[ib])
        if v is None: dirty.add(did); continue
        psum[did]+=v
ok=[k for k in tot if k in psum and k not in dirty]
print("  这些航次下的 parcel 行 %d；有脏行被弃的航次 %d；干净且有 parcel 的 %d" % (nrow,len(dirty),len(ok)))

res=collections.Counter(); neg=0
for k in ok:
    d=round(tot[k][1]-psum[k],4)
    res[d]+=1
    if d<-1e-9: neg+=1
n=len(ok)
print("\n【残差 ＝ totaal − Σparcel 的分布，n=%d】" % n)
print("  前 14 个取值：")
for v,c in res.most_common(14): print("     %10.4f : %7d (%.2f%%)" % (v,c,100*c/n))
print("  ＝0 的占 %.2f%%；|残差|<=0.01 的占 %.2f%%；负的 %d = %.2f%%"
      % (100*res.get(0.0,0)/n, 100*sum(c for v,c in res.items() if abs(v)<=0.01)/n, neg, 100*neg/n))
big=sum(c for v,c in res.items() if v>3.0)
print("  残差 >3 Daler 的占 %.2f%%；不同残差值 %d 个" % (100*big/n,len(res)))
json.dump({str(k):v for k,v in res.most_common(200)},(CACHE/"b44_residual.json").open("w",encoding="utf-8"))
