# -*- coding: utf-8 -*-
"""自查：把 R6 写进结果件的承重数字从缓存重算一遍，逐条 assert。
写错一个数就在这里炸，不靠人眼对。"""
import json, pathlib, collections, re
import os
_H = pathlib.Path(__file__).resolve().parent
CACHE = _H.parent / "data/cache/stro_classic"
D = json.load((CACHE / "b44_homeport_year.json").open(encoding="utf-8"))
CTY = D.pop("__country__"); META = D.pop("__meta__")
SEG = {"pre": (1630, 1644), "ex": (1660, 1709), "post": (1720, 1779)}
P = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for k, v in D.items():
    nm, y = k.rsplit("|", 1); y = int(y)
    for s, (a, b) in SEG.items():
        if a <= y <= b:
            c = P[nm][s]; c[0] += v[1]; c[1] += v[2]
def r(nm, s):
    c = P[nm][s]; return (round(c[1]/c[0], 3) if c[0] else None), c[0]
def grp(names, s):
    c = [0, 0]
    for nm in names:
        x = P[nm][s]; c[0] += x[0]; c[1] += x[1]
    return round(c[1]/c[0], 3), c[0]

CHK = []
def eq(label, got, want):
    ok = got == want
    CHK.append((ok, label, got, want))

eq("缓存格数", len(D), 40559)
eq("窗口内航次", META["passages_in_window"], 916043)
eq("ladingen 匹配", META["ladingen_matched"], 2520464)
for nm, want in [("Stralsund", (0.020, 4343)), ("Wismar", (0.149, 1153)), ("Greifswald", (0.088, 317)),
                 ("Anklam", (0.031, 324)), ("Lübeck", (0.930, 6167)), ("Rostock", (0.913, 3686)),
                 ("Hamburg", (0.915, 2600)), ("Stettin", (0.029, 3531)), ("Kungsbacka", (0.010, 4776)),
                 ("Riga", (0.299, 1076)), ("Narva", (0.306, 278)), ("Nyen", (0.338, 269)),
                 ("Reval", (0.417, 374)), ("Stade", (0.680, 984)), ("Nedenæs", (0.237, 152)),
                 ("Landskrona", (0.353, 224)), ("Stockholm", (0.078, 7338))]:
    eq("%s 豁免窗" % nm, r(nm, "ex"), want)
eq("Demmin 豁免窗 n", P["Demmin"]["ex"][0], 4)
eq("Kiel 豁免窗 n", P["Kiel"]["ex"][0], 32)
WEND = ["Lübeck","Rostock","Hamburg","Kiel","Stralsund","Wismar","Greifswald","Anklam","Demmin"]
FIVE = {"Stralsund","Wismar","Greifswald","Anklam","Demmin"}
THREE = {"Stralsund","Wismar","Greifswald"}
eq("原组 豁免", grp(WEND, "ex"), (0.634, 18626))
eq("剥三个后 豁免", grp([n for n in WEND if n not in THREE], "ex"), (0.899, 12813))
eq("剥五个后 豁免", grp([n for n in WEND if n not in FIVE], "ex"), (0.922, 12485))
eq("被剥五个 豁免", grp(sorted(FIVE), "ex"), (0.049, 6141))
NL = [n for n in P if CTY.get(n) == "The Netherlands"]
eq("尼德兰 豁免", grp(NL, "ex"), (0.921, 215371))
eq("尼德兰 前窗", grp(NL, "pre"), (0.934, 122980))
eq("尼德兰 后窗", grp(NL, "post"), (0.908, 350157))
# 全枚举两版的计数
n94 = [n for n in P if P[n]["pre"][0] >= 150 and P[n]["ex"][0] >= 150]
n171 = [n for n in P if P[n]["ex"][0] >= 150]
eq("两窗门槛合格港数", len(n94), 94)
eq("单窗门槛合格港数", len(n171), 171)
EXTRA = {"Stralsund","Stettin","Greifswald","Anklam","Demmin","Wolgast","Barth","Wismar",
         "Riga","Pernau","Reval","Narva","Arensburg","Nyen","Åbo","Helsingfors","Viborg",
         "Björneborg","Stade","Buxtehude"}
sw = lambda n: CTY.get(n) == "Sweden" or n in EXTRA
eq("171 里属瑞典", sum(1 for n in n171 if sw(n)), 29)
eq("171 里不属瑞典", sum(1 for n in n171 if not sw(n)), 142)
eq("不属瑞典而 <=0.15 的", sum(1 for n in n171 if not sw(n) and P[n]["ex"][1]/P[n]["ex"][0] <= 0.15), 0)
eq("属瑞典而 <=0.15 的", sum(1 for n in n171 if sw(n) and P[n]["ex"][1]/P[n]["ex"][0] <= 0.15), 21)
srt = sorted(n171, key=lambda n: P[n]["ex"][1]/P[n]["ex"][0])
eq("排序第一个不属瑞典的名次", next(i for i, n in enumerate(srt, 1) if not sw(n)), 23)
eq("94 版里塌的（<0.36）全属瑞典", all(sw(n) for n in n94 if P[n]["ex"][1]/P[n]["ex"][0] < 0.36), True)
eq("94 版里塌的个数", sum(1 for n in n94 if P[n]["ex"][1]/P[n]["ex"][0] < 0.36), 11)

bad = [c for c in CHK if not c[0]]
for ok, lab, got, want in CHK:
    print("%s %-28s 得 %-22s 应 %s" % ("OK " if ok else "!!!", lab, got, want))
print("\n%d 条检查，%d 条不过" % (len(CHK), len(bad)))
# 文件里的关键数字是不是真在文件里
# write-up cross-check: the numbers this script recomputes must also appear
# in the station's write-up. Path comes from the environment so this file
# names no document of its own.
need = ["0.634", "0.899", "0.922", "0.049", "0.921", "0.020", "0.029", "0.031", "0.680",
        "0.237", "916,043", "40,559", "171", "142", "第 23 名"]
w=os.environ.get("B44_WRITEUP")
if w:
    t=pathlib.Path(w).read_text(encoding="utf-8")
    m=[s for s in need if s not in t]
    print("write-up missing:",m or "none")
else:
    m=[]; print("write-up check skipped (set B44_WRITEUP to a path to run it)")
raise SystemExit(1 if (bad or m) else 0)
