# -*- coding: utf-8 -*-
"""R3：进位基数由它必须复现的那个常数来定，不引外部源。
豁免期 1650-1709 的残差在纯 Daler 样本上是常数 4（R2 第三款，95.1%/91.9%）。
把带 Skilling 的航次也算进来，扫基数 B，看哪一个 B 让残差重新集中在 4。
正确的 B 唯一，错的 B 会把残差打散。"""
import csv, pathlib, collections, re, statistics
_H=pathlib.Path(__file__).resolve().parent; RAW=_H.parent/"data/raw/stro/classic"
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
    return None
BASES=[12,16,24,32,48,64,96]
tot={}
with (RAW/"doorvaarten.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iy,iid=h.index("jaar"),h.index("id_doorvaart")
    i1,j1,i2,j2,i3=(h.index(x) for x in ("totaal_muntsoort1","totaal_bedrag1","totaal_muntsoort2","totaal_bedrag2","totaal_muntsoort3"))
    for row in r:
        try: y=int(row[iy])
        except ValueError: continue
        if not (1650<=y<=1709) or row[i1].strip()!="Daler": continue
        if row[i3].strip() not in MISS: continue          # 有第三位的弃掉
        m2=row[i2].strip()
        if m2 not in MISS and m2!="Skilling": continue
        a=val(row[j1]); b=val(row[j2]) if m2=="Skilling" else 0.0
        if a is None or b is None: continue
        try: tot[int(row[iid])]=(a,b)
        except ValueError: pass
psum=collections.defaultdict(lambda:[0.0,0.0]); dirty=set(); hassk=set()
with (RAW/"ladingen.csv").open(encoding="utf-8",newline="") as f:
    r=csv.reader(f,delimiter=";"); h=next(r)
    iid=h.index("id_doorvaart")
    i1,j1,i2,j2,i3=(h.index(x) for x in ("muntsoort1","bedrag1","muntsoort2","bedrag2","muntsoort3"))
    for row in r:
        try: did=int(row[iid])
        except ValueError: continue
        if did not in tot: continue
        if row[i1].strip()!="Daler" or row[i3].strip() not in MISS: dirty.add(did); continue
        m2=row[i2].strip()
        if m2 not in MISS and m2!="Skilling": dirty.add(did); continue
        a=val(row[j1]); b=val(row[j2]) if m2=="Skilling" else 0.0
        if a is None or b is None: dirty.add(did); continue
        c=psum[did]; c[0]+=a; c[1]+=b
        if b>0: hassk.add(did)
ok=[k for k in tot if k in psum and k not in dirty]
withsk=[k for k in ok if k in hassk or tot[k][1]>0]
print("豁免期合格航次 %d，其中带 Skilling 分量的 %d" % (len(ok),len(withsk)))
print("\n%-6s | %-28s | %-28s" % ("基数 B","全部合格航次","只看带 Skilling 的"))
print("%-6s | %8s %9s %9s | %8s %9s %9s" % ("","＝4 占","中位","不同值","＝4 占","中位","不同值"))
for B in BASES:
    rows=[]
    for k in ok:
        d=(tot[k][0]+tot[k][1]/B)-(psum[k][0]+psum[k][1]/B)
        rows.append((k,round(d,6)))
    def rep(sub):
        v=[d for k,d in rows if k in sub] if sub is not None else [d for _,d in rows]
        if not v: return (0,0,0)
        e4=sum(1 for x in v if abs(x-4)<1e-6)
        return (100*e4/len(v),statistics.median(v),len(set(v)))
    a=rep(None); b=rep(set(withsk))
    print("%-6d | %7.2f%% %9.3f %9d | %7.2f%% %9.3f %9d" % (B,a[0],a[1],a[2],b[0],b[1],b[2]))
