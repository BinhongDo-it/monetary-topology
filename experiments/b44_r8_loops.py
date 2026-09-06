# -*- coding: utf-8 -*-
"""R8 臂 E：纯位置环。ŵ(u,v) = ½[t(v→u) − t(u→v)]，沿港的圈求和。
位置图按构造二部（只有穿海峡的港对是边），最短圈四条腿，展开是两个西港 × 两个东港的双重差分。
E1 结构自检：树上路径来回走一遍必须精确得零。
E2 印读数与归一化比 |Σŵ| / Σ|ŵ|，不画线。
E3 非瑞典类的环和跨 1720 动不动 —— 那一年对这个类什么也没改，所以它不该动。
底按 D24 逐圈自助量出来。"""
import json, csv, pathlib, statistics, random, itertools
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_r5_cells2.json").open(encoding="utf-8"))
cell = {}
for k, v in D.items():
    w, pr, c, d = k.split("|"); cell[(w, pr, c, d)] = [x[1] for x in v]
west = {}
with (RAW / "places_standard.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f, delimiter=";"):
        west[row["Stednavn"].strip()] = row["west_of_Helsingør"].strip().lower() == "true"
ALL = ["瑞","荷","英","丹","挪","德","余"]
NS = [c for c in ALL if c != "瑞"]
def vals(w, pr, cs, d):
    o = []
    for c in cs: o += cell.get((w, pr, c, d), [])
    return o
rng = random.Random(20260903)

def build(w, cs, nmin):
    """留下两个方向都够厚的航线，返回 边 -> {东:[...], 西:[...]}"""
    E = {}
    for pr in {k[1] for k in cell if k[0] == w}:
        a, b = pr.split("~")
        if a not in west or b not in west or west[a] == west[b]: continue
        e = vals(w, pr, cs, "东"); x = vals(w, pr, cs, "西")
        if len(e) >= nmin and len(x) >= nmin: E[(a, b)] = {"东": e, "西": x}
    return E

def cycles(E):
    """生成树 + 非树边 = 基本圈"""
    par = {}
    def f(x):
        par.setdefault(x, x)
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    adj = {}; tree = []; extra = []
    for (a, b) in E:
        if f(a) != f(b):
            par[f(a)] = f(b); tree.append((a, b))
            adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
        else: extra.append((a, b))
    def path(u, v):
        st = [(u, [u])]; seen = {u}
        while st:
            x, p = st.pop()
            if x == v: return p
            for y in adj.get(x, []):
                if y not in seen: seen.add(y); st.append((y, p + [y]))
        return None
    out = []
    for (a, b) in extra:
        p = path(b, a)
        if p: out.append(p + [b])          # b -> ... -> a -> b
    return out, tree

def wh(cells4, agg=statistics.median):
    return 0.5 * (agg(cells4["西"]) - agg(cells4["东"]))   # 定向为 西港 -> 东港

def loopsum(cyc, E, agg=statistics.median):
    s = 0.0; scale = 0.0
    for x, y in zip(cyc, cyc[1:]):
        d = E.get((x, y)) or E.get((y, x))
        v = wh(d, agg)
        sg = 1.0 if (west.get(x) and not west.get(y)) else -1.0
        s += sg * v; scale += abs(v)
    return s, scale

def boot(cyc, E, reps=1500):
    out = []
    for _ in range(reps):
        s = 0.0
        for x, y in zip(cyc, cyc[1:]):
            d = E.get((x, y)) or E.get((y, x))
            v = 0.5 * (statistics.median(rng.choices(d["西"], k=len(d["西"])))
                       - statistics.median(rng.choices(d["东"], k=len(d["东"]))))
            s += (1.0 if (west.get(x) and not west.get(y)) else -1.0) * v
        out.append(s)
    return statistics.pstdev(out)

NM = 40
print("【E1 结构自检：树上路径来回走一遍，环和必须精确得零】")
E = build("豁免", NS, NM); cyc, tree = cycles(E)
if tree:
    a, b = tree[0]
    s, _ = loopsum([a, b, a], E)
    print("  %s → %s → %s ：环和 = %.17g  %s" % (a, b, a, s, "通过" if s == 0.0 else "失败"))
    if len(tree) > 1:
        c, d2 = tree[1]
        s2, _ = loopsum([c, d2, c], E)
        print("  %s → %s → %s ：环和 = %.17g  %s" % (c, d2, c, s2, "通过" if s2 == 0.0 else "失败"))

for w, cs, lab in [("豁免", NS, "豁免 1650-1709　非瑞典类"),
                   ("后",  NS, "后 1720-1779　非瑞典类"),
                   ("后",  ["瑞"], "后 1720-1779　瑞典类"),
                   ("豁免", ["瑞"], "豁免 1650-1709　瑞典类")]:
    E = build(w, cs, NM); cyc, tree = cycles(E)
    V = {p for e in E for p in e}
    print("\n【%s】两向都 n>=%d 的航线 %d 条，港 %d 个，基本圈 %d 个"
          % (lab, NM, len(E), len(V), len(cyc)))
    if not cyc: print("  没有圈，读不出位置全息量"); continue
    print("  %-52s %10s %10s %8s %9s %7s" % ("圈", "Σŵ", "Σ|ŵ|", "比", "se", "|Σŵ|/se"))
    for c in sorted(cyc, key=len)[:10]:
        s, sc = loopsum(c, E); se = boot(c, E)
        print("  %-52s %10.3f %10.3f %8.4f %9.3f %7.2f"
              % ("→".join(c)[:52], s, sc, abs(s)/sc if sc else float("nan"), se,
                 abs(s)/se if se else float("inf")))
    rs = [abs(loopsum(c, E)[0]) / loopsum(c, E)[1] for c in cyc]
    print("  归一化比 |Σŵ|/Σ|ŵ| 中位 %.4f，区间 %.4f – %.4f" % (statistics.median(rs), min(rs), max(rs)))
