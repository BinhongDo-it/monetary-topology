# -*- coding: utf-8 -*-
"""R7：D22 —— 派生量的独立数由底层结构封顶。B44 报了 8 个（放宽到 16 个）航线方块，
那些方块里有几个是独立的？纯计数，零数据。

位置图 G：顶点＝港，边＝航线。
双图 Γ：顶点＝(港, 类)，边＝每个类里的位置边 + 每个港上的 agent 边（换旗）。
b₁(Γ) = E(Γ) − V(Γ) + c(Γ)。b₁(G)=0（森林）时按 Theorem 2 全部 obstruction 都是 square。
"""
import json, pathlib, statistics
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_r5_cells2.json").open(encoding="utf-8"))
cell = {}
for k, v in D.items():
    w, pr, c, d = k.split("|"); cell[(w, pr, c, d)] = [x[1] for x in v]
ALL = ["瑞","荷","英","丹","挪","德","余"]
NS = [c for c in ALL if c != "瑞"]
def n(w, pr, cs, d): return sum(len(cell.get((w, pr, c, d), [])) for c in cs)
def comps(V, E):
    par = {v: v for v in V}
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in E: par[f(a)] = f(b)
    return len({f(v) for v in V})
def report(lab, routes):
    V = sorted({p for pr in routes for p in pr.split("~")})
    E = [tuple(pr.split("~")) for pr in routes]
    cG = comps(V, E)
    b1G = len(E) - len(V) + cG
    VG = [(p, c) for p in V for c in ("a", "b")]
    EG = [((a,"a"),(b,"a")) for a,b in E] + [((a,"b"),(b,"b")) for a,b in E] \
       + [((p,"a"),(p,"b")) for p in V]
    cGam = comps(VG, EG)
    b1Gam = len(EG) - len(VG) + cGam
    print("【%s】" % lab)
    print("  位置图 G：港 %d、航线 %d、连通分支 %d  =>  b1(G) = %d %s"
          % (len(V), len(E), cG, b1G, "（森林，Theorem 2 适用：全部 obstruction 都是 square）"
             if b1G == 0 else "（有位置圈，除了 square 还有别的 obstruction）"))
    print("  双图 Γ：顶点 %d、边 %d（位置边 %d + agent 边 %d）、分支 %d  =>  b1(Γ) = %d"
          % (len(VG), len(EG), 2*len(E), len(V), cGam, b1Gam))
    print("  报出的方块 %d 个，独立上限 %d 个  =>  %s"
          % (len(E), b1Gam, "全部独立，零灌水" if len(E) <= b1Gam else "有 %d 个是别的线性组合" % (len(E)-b1Gam)))
    print("  港：%s" % "、".join(V))
    print()
for nmin, lab in ((40, "主读数 n>=40"), (20, "放宽 n>=20")):
    rs = sorted({k[1] for k in cell if k[0] == "后"})
    keep = [pr for pr in rs
            if min(n("后",pr,["瑞"],d) for d in ("东","西")) >= nmin
            and min(n("后",pr,NS,d) for d in ("东","西")) >= nmin]
    report("后 1720-79 " + lab, keep)
# R4 的 16 条豁免期航线
r4 = json.load((CACHE / "b44_rho_v2.json").open(encoding="utf-8"))
report("豁免 1650-1709　R4 的 16 条", ["~".join(sorted(pr)) for _, pr, *_ in r4])
