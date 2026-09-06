# -*- coding: utf-8 -*-
"""臂 C 的全枚举版：不挑港。凡在前窗与豁免窗都有 n>=150 明细行的籍港，一个不漏地印出来，
按豁免窗读数排序。不画线（第 11 条），让那张表自己说话：
如果塌的那一批恰好是当时归瑞典的那一批，而没有一个非瑞典港塌，那就是识别本身。
D12: enumerate before selecting. Report every quantity this run produces, not the ones that fit."""
import json, pathlib, collections
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
CTY = D.pop("__country__"); D.pop("__meta__")
SEG = [("pre", 1630, 1644), ("exempt", 1660, 1709), ("post", 1720, 1779)]
P = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for k, v in D.items():
    nm, y = k.rsplit("|", 1); y = int(y)
    for s, a, b in SEG:
        if a <= y <= b:
            c = P[nm][s]; c[0] += v[1]; c[1] += v[2]
rows = []
for nm, d in P.items():
    pre, ex, po = d["pre"], d["exempt"], d["post"]
    if pre[0] >= 150 and ex[0] >= 150:
        rows.append((ex[1] / ex[0], pre[1] / pre[0], po[1] / po[0] if po[0] >= 150 else None,
                     pre[0], ex[0], po[0], nm, CTY.get(nm, "?")))
rows.sort()
print("【全枚举：前窗与豁免窗都有 n>=150 明细行的籍港，共 %d 个，按豁免窗读数升序】" % len(rows))
print("%-3s %-16s %-18s %9s %9s %9s %8s %8s %8s" %
      ("#", "籍港", "现代国别", "前1630-44", "豁免", "后1720-79", "n前", "n豁免", "n后"))
for i, (ex, pre, po, npre, nex, npo, nm, co) in enumerate(rows, 1):
    print("%-3d %-16s %-18s %9.3f %9.3f %9s %8d %8d %8d" %
          (i, nm, co, pre, ex, ("%.3f" % po) if po is not None else "·", npre, nex, npo))
gaps = [(rows[i + 1][0] - rows[i][0], i) for i in range(len(rows) - 1)]
gaps.sort(reverse=True)
print("\n排序后最大的三个间隙：")
for g, i in gaps[:3]:
    print("  第 %d 与第 %d 之间：%.3f -> %.3f，间隙 %.3f （%s | %s）"
          % (i + 1, i + 2, rows[i][0], rows[i + 1][0], g, rows[i][6], rows[i + 1][6]))
