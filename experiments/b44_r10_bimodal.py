# -*- coding: utf-8 -*-
"""R10：波罗的海诸省那个中间读数，是混合还是部分？

跑前登记的假说（出处是文献给的规则，不是这次读数）：
STRO 的方法学文章写明豁免适用于 "Swedish vessels and commodities" —— 船与货都要是瑞典的。
里加、雷瓦尔是转口港，船是瑞典的而货常常是荷兰或吕贝克商人的。
若中间读数（0.30–0.42）是「有的航次免、有的不免」的混合，
则逐航次的 aantal 填充率应当双峰：一堆在 0，一堆在 1，中间少。
若是「每个航次都只免一部分」，则质量应当堆在中间。
两个结局都到得了（D15），判据是印分布不是画线（第 11 条）。
"""
import csv, json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
csv.field_size_limit(10 ** 8)
MISS = {"", "-", "?", "--"}
M = json.load((CACHE / "place_std_map.json").open(encoding="utf-8"))
home, src, std = M["home"], M["src"], M["std"]
GRP = {}
for p, g in [("Riga","波罗的海诸省"),("Reval","波罗的海诸省"),("Narva","波罗的海诸省"),
             ("Nyen","波罗的海诸省"),("Pernau","波罗的海诸省"),
             ("Stockholm","瑞典本土"),("Göteborg","瑞典本土"),("Norrköping","瑞典本土"),
             ("Kalmar","瑞典本土"),("Kungsbacka","瑞典本土"),
             ("Amsterdam","对照 尼德兰"),("Lübeck","对照 从不属瑞典")]:
    GRP[p] = g
id2 = {}
with (RAW / "doorvaarten.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";"); h = next(r)
    iy, iid, isp = h.index("jaar"), h.index("id_doorvaart"), h.index("schipper_plaatsnaam")
    for row in r:
        try: y = int(row[iy]); did = int(row[iid])
        except (ValueError, IndexError): continue
        if not (1660 <= y <= 1709): continue
        p = row[isp].strip(); k = home.get(p) or src.get(p)
        if not k: continue
        g = GRP.get(std[k][0])
        if g: id2[did] = (g, std[k][0])
per = collections.defaultdict(lambda: [0, 0])
with (RAW / "ladingen.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";"); h = next(r)
    iid, ia = h.index("id_doorvaart"), h.index("aantal")
    for row in r:
        try: did = int(row[iid])
        except (ValueError, IndexError): continue
        if did not in id2: continue
        c = per[did]; c[0] += 1
        if row[ia].strip() not in MISS: c[1] += 1
bins = collections.defaultdict(lambda: collections.Counter())
tot = collections.Counter()
for did, (n, k) in per.items():
    if n == 0: continue
    g = id2[did][0]; f_ = k / n
    tot[g] += 1
    if f_ == 0.0: bins[g]["恰好 0"] += 1
    elif f_ == 1.0: bins[g]["恰好 1"] += 1
    elif f_ < 0.5: bins[g]["(0,0.5)"] += 1
    else: bins[g]["[0.5,1)"] += 1
print("【1660-1709，逐航次的 aantal 填充率分布（分母＝该航次的明细行数）】")
K = ["恰好 0", "(0,0.5)", "[0.5,1)", "恰好 1"]
print("%-16s %8s %10s %10s %10s %10s" % ("组", "航次", *K))
for g in ["波罗的海诸省", "瑞典本土", "对照 尼德兰", "对照 从不属瑞典"]:
    n = tot[g]
    if not n: continue
    print("%-16s %8d %10s %10s %10s %10s"
          % (g, n, *["%.1f%%" % (100 * bins[g][k] / n) for k in K]))
print("\n【同表，逐港（n>=100 才印）】")
pb = collections.defaultdict(lambda: collections.Counter()); pt = collections.Counter()
for did, (n, k) in per.items():
    if n == 0: continue
    nm = id2[did][1]; f_ = k / n; pt[nm] += 1
    pb[nm]["恰好 0" if f_ == 0 else ("恰好 1" if f_ == 1 else "中间")] += 1
print("%-14s %8s %10s %10s %10s" % ("籍港", "航次", "恰好 0", "中间", "恰好 1"))
for nm in sorted(pt, key=lambda x: -pt[x]):
    if pt[nm] < 100: continue
    n = pt[nm]
    print("%-14s %8d %10s %10s %10s" % (nm, n,
          *["%.1f%%" % (100 * pb[nm][k] / n) for k in ("恰好 0", "中间", "恰好 1")]))
