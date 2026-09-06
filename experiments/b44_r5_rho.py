# -*- coding: utf-8 -*-
"""R5：臂 D。四个格直接量，逐航线算 S−S'、−(S+S')、rho。
  S − S'  = [t_b(东) − t_b(西)] − [t_a(东) − t_a(西)]     两类 × 两方向的双重差分
  −(S+S') = t_a(东)+t_a(西)+t_b(东)+t_b(西)
  t = totaal_bedrag1（含固定费与按货征），中位
底按 D24 量出来不声明：逐格自助 2000 次给 S−S' 的抽样散布（在这个尺寸上是毫秒级）。
安慰剂：荷 对 非瑞非荷 —— 两支真实不同的船队、同一张税则，两个窗口都跑。
结构自检：Theorem 6(4) 要求 |S−S'| <= −(S+S')，即 rho <= 1。违反即实现有错。
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
GRP = {"瑞vs非瑞": (["瑞"], [c for c in ALL if c != "瑞"]),
       "荷vs非瑞非荷": (["荷"], [c for c in ALL if c not in ("瑞", "荷")])}
def get(w, pr, cs, d):
    out = []
    for c in cs: out += cell.get((w, pr, c, d), [])
    return out
rng = random.Random(20260903)
def one(w, pr, A, Bc, nmin, reps=2000):
    v = {(g, d): get(w, pr, cs, d) for g, cs in (("a", A), ("b", Bc)) for d in ("东", "西")}
    n = {k: len(x) for k, x in v.items()}
    if min(n.values()) < nmin: return None
    m = {k: statistics.median(x) for k, x in v.items()}
    idx = (m[("b", "东")] - m[("b", "西")]) - (m[("a", "东")] - m[("a", "西")])
    fri = m[("a", "东")] + m[("a", "西")] + m[("b", "东")] + m[("b", "西")]
    bs = []
    for _ in range(reps):
        mm = {k: statistics.median(rng.choices(x, k=len(x))) for k, x in v.items()}
        bs.append((mm[("b", "东")] - mm[("b", "西")]) - (mm[("a", "东")] - mm[("a", "西")]))
    se = statistics.pstdev(bs)
    return dict(route=pr, n=n, m=m, idx=idx, fri=fri,
                rho=abs(idx) / fri if fri > 0 else float("nan"),
                se=se, ratio=abs(idx) / se if se > 0 else float("inf"))

def run(w, gname, nmin):
    A, Bc = GRP[gname]
    routes = sorted({k[1] for k in cell if k[0] == w})
    out = [r for r in (one(w, pr, A, Bc, nmin) for pr in routes) if r]
    out.sort(key=lambda r: -sum(r["n"].values()))
    return out

def show(title, rows):
    print("\n【%s】航线格 %d 个" % (title, len(rows)))
    if not rows: return
    print("%-30s %5s %5s %5s %5s %9s %9s %8s %8s %7s" %
          ("航线", "a东", "a西", "b东", "b西", "S−S'", "−(S+S')", "rho", "se", "|比|"))
    for r in rows[:14]:
        n = r["n"]
        print("%-30s %5d %5d %5d %5d %9.3f %9.3f %8.4f %8.3f %7.2f" %
              ("↔".join(r["route"].split("~"))[:30], n[("a","东")], n[("a","西")],
               n[("b","东")], n[("b","西")], r["idx"], r["fri"], r["rho"], r["se"], r["ratio"]))
    rh = sorted(r["rho"] for r in rows); ix = sorted(abs(r["idx"]) for r in rows)
    rt = sorted(r["ratio"] for r in rows)
    print("  rho     中位 %.4f  四分位 %.4f / %.4f  区间 %.4f – %.4f"
          % (statistics.median(rh), rh[len(rh)//4], rh[3*len(rh)//4], rh[0], rh[-1]))
    print("  |S−S'|  中位 %.3f Daler  区间 %.3f – %.3f" % (statistics.median(ix), ix[0], ix[-1]))
    print("  |S−S'|/se 中位 %.2f  区间 %.2f – %.2f；超过 2 的 %d/%d"
          % (statistics.median(rt), rt[0], rt[-1], sum(1 for x in rt if x > 2), len(rt)))
    bad = [r for r in rows if r["rho"] > 1.0]
    print("  结构自检 Theorem 6(4) rho<=1：%s" % ("全部通过" if not bad else "违反 %d 条！" % len(bad)))

for nmin in (40, 20):
    show("后 1720-79　瑞 对 非瑞　四格 n>=%d" % nmin, run("后", "瑞vs非瑞", nmin))
show("后 1720-79　安慰剂 荷 对 非瑞非荷　n>=40", run("后", "荷vs非瑞非荷", 40))
show("豁免 1650-1709　安慰剂 荷 对 非瑞非荷　n>=40", run("豁免", "荷vs非瑞非荷", 40))

# 归约检查：豁免期瑞典籍的 totaal 合并起来是不是那个常数 4
print("\n【归约检查：豁免期瑞典籍的 totaal 合并（R2 第三款推出它该是常数 4）】")
for w in ("豁免", "后"):
    for c, lab in (("瑞", "瑞典籍"), ("荷", "尼德兰籍")):
        for d in ("东", "西"):
            v = []
            for k, x in cell.items():
                if k[0] == w and k[2] == c and k[3] == d: v += x
            if len(v) < 30: continue
            v.sort()
            print("  %-4s %-6s %s向  n=%-6d 中位 %8.3f  四分位 %7.3f / %7.3f  ＝4 占 %.1f%%"
                  % (w, lab, d, len(v), statistics.median(v), v[len(v)//4], v[3*len(v)//4],
                     100 * sum(1 for x in v if abs(x - 4) < 1e-9) / len(v)))
