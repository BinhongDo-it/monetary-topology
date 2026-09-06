# -*- coding: utf-8 -*-
"""R5 补三件：
 (1) 把四个格的中位印出来，不只印 S−S'（第 11 条：打印对象）
 (2) 安慰剂限到与主读数同一批航线，做同口径比 —— 23 条对 8 条不是 like-for-like
 (3) 豁免期上直接量法在薄格（n>=5 / n>=10）是什么样，以及用中位数代替中位数之外的均值敏感性
"""
import json, pathlib, statistics, random
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_r5_cells2.json").open(encoding="utf-8"))
cell = {}
for k, v in D.items():
    w, pr, c, d = k.split("|")
    cell[(w, pr, c, d)] = [x[1] for x in v]
ALL = ["瑞", "荷", "英", "丹", "挪", "德", "余"]
G = {"瑞vs非瑞": (["瑞"], [c for c in ALL if c != "瑞"]),
     "荷vs非瑞非荷": (["荷"], [c for c in ALL if c not in ("瑞", "荷")])}
def get(w, pr, cs, d):
    out = []
    for c in cs: out += cell.get((w, pr, c, d), [])
    return out
rng = random.Random(20260903)
def one(w, pr, A, Bc, nmin, agg=statistics.median, reps=1500):
    v = {(g, d): get(w, pr, cs, d) for g, cs in (("a", A), ("b", Bc)) for d in ("东", "西")}
    n = {k: len(x) for k, x in v.items()}
    if min(n.values()) < nmin: return None
    m = {k: agg(x) for k, x in v.items()}
    idx = (m[("b","东")] - m[("b","西")]) - (m[("a","东")] - m[("a","西")])
    fri = sum(m.values())
    bs = [((lambda mm: (mm[("b","东")]-mm[("b","西")])-(mm[("a","东")]-mm[("a","西")]))
           ({k: agg(rng.choices(x, k=len(x))) for k, x in v.items()})) for _ in range(reps)]
    se = statistics.pstdev(bs)
    return dict(route=pr, n=n, m=m, idx=idx, fri=fri, rho=abs(idx)/fri if fri > 0 else float("nan"),
                se=se, ratio=abs(idx)/se if se > 0 else float("inf"))
def rows(w, g, nmin, agg=statistics.median, only=None):
    A, Bc = G[g]
    rs = sorted({k[1] for k in cell if k[0] == w}) if only is None else only
    return [r for r in (one(w, pr, A, Bc, nmin, agg) for pr in rs) if r]

print("【(1) 主读数：后 1720-79 瑞对非瑞，四个格的中位都印出来】")
main = rows("后", "瑞vs非瑞", 40)
main.sort(key=lambda r: -sum(r["n"].values()))
print("%-28s %8s %8s %8s %8s %9s %8s %7s" % ("航线","瑞东","瑞西","非瑞东","非瑞西","S−S'","rho","|比|"))
for r in main:
    m = r["m"]
    print("%-28s %8.2f %8.2f %8.2f %8.2f %9.3f %8.4f %7.2f"
          % ("↔".join(r["route"].split("~"))[:28], m[("a","东")], m[("a","西")],
             m[("b","东")], m[("b","西")], r["idx"], r["rho"], r["ratio"]))
TR = [r["route"] for r in main]

print("\n【(2) 安慰剂限到同一批航线（%d 条里，荷/非瑞非荷 四格也够厚的）】" % len(TR))
pl = rows("后", "荷vs非瑞非荷", 40, only=TR)
if pl:
    print("%-28s %8s %8s %8s %8s %9s %8s %7s" % ("航线","荷东","荷西","其余东","其余西","S−S'","rho","|比|"))
    for r in pl:
        m = r["m"]
        print("%-28s %8.2f %8.2f %8.2f %8.2f %9.3f %8.4f %7.2f"
              % ("↔".join(r["route"].split("~"))[:28], m[("a","东")], m[("a","西")],
                 m[("b","东")], m[("b","西")], r["idx"], r["rho"], r["ratio"]))
for nm, s in (("主 8 条", main), ("安慰剂 同批", pl)):
    if not s: continue
    rh = sorted(r["rho"] for r in s)
    print("  %-12s n=%-3d rho 中位 %.4f  区间 %.4f – %.4f" % (nm, len(rh), statistics.median(rh), rh[0], rh[-1]))
pl20 = rows("后", "荷vs非瑞非荷", 20, only=TR)
if pl20:
    rh = sorted(r["rho"] for r in pl20)
    print("  %-12s n=%-3d rho 中位 %.4f  区间 %.4f – %.4f" % ("安慰剂 同批 n>=20", len(rh), statistics.median(rh), rh[0], rh[-1]))

print("\n【(3a) 豁免期 瑞对非瑞 直接量法，薄格】")
for nmin in (10, 5):
    s = rows("豁免", "瑞vs非瑞", nmin)
    if not s: print("  n>=%d：一条航线都没有" % nmin); continue
    s.sort(key=lambda r: -sum(r["n"].values()))
    print("  n>=%d：%d 条" % (nmin, len(s)))
    for r in s:
        m = r["m"]
        print("   %-26s 瑞东%5.2f 瑞西%6.2f 非瑞东%6.2f 非瑞西%7.2f  S−S'%9.3f  rho %.4f  |比| %5.2f  n=%s"
              % ("↔".join(r["route"].split("~"))[:26], m[("a","东")], m[("a","西")],
                 m[("b","东")], m[("b","西")], r["idx"], r["rho"], r["ratio"],
                 [r["n"][k] for k in (("a","东"),("a","西"),("b","东"),("b","西"))]))

print("\n【(3b) 均值代替中位的敏感性，后 1720-79】")
mean = lambda x: sum(x)/len(x)
for g, lab in (("瑞vs非瑞","主 瑞对非瑞"), ("荷vs非瑞非荷","安慰剂 荷对非瑞非荷")):
    for agg, an in ((statistics.median,"中位"), (mean,"均值")):
        s = rows("后", g, 40, agg)
        rh = sorted(r["rho"] for r in s)
        print("  %-20s %s：n=%-3d rho 中位 %.4f  区间 %.4f – %.4f"
              % (lab, an, len(rh), statistics.median(rh), rh[0], rh[-1]))
