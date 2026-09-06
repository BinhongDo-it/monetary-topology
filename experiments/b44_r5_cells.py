# -*- coding: utf-8 -*-
"""R5 第一步：只数格，不算 rho（第 13 条第 1 步：先量最坏那一格，不是平均那一格）。
臂 D 要四个格：两类（瑞典籍/非瑞典籍）× 两方向（东/西），逐航线。
先看 1720-79 上有几条航线四个格都够厚，再决定算不算得下去。
口径与 R4 同：totaal_muntsoort1 必须是 Daler，副位只许 Skilling，B=48；
分数按 'a b/c' 与 'b/c' 正确解析（R1 第三处错）；'-' 是占位符不是值。
"""
import csv, json, pathlib, collections, re
_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
csv.field_size_limit(10 ** 8)
B = 48.0
MISS = {"", "-", "?", "--"}
FR = re.compile(r'^(\d+)\s+(\d+)/(\d+)$'); PF = re.compile(r'^(\d+)/(\d+)$')
def val(s):
    s = s.strip()
    if s in MISS: return None
    if s.isdigit(): return float(s)
    m = FR.match(s)
    if m: return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    m = PF.match(s)
    if m: return int(m.group(1)) / int(m.group(2))
    return None

M = json.load((CACHE / "place_std_map.json").open(encoding="utf-8"))
home, src, std = M["home"], M["src"], M["std"]
v2s = json.load((CACHE / "van2std.json").open(encoding="utf-8"))
west = {}
with (RAW / "places_standard.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f, delimiter=";"):
        west[row["Stednavn"].strip()] = row["west_of_Helsingør"].strip().lower() == "true"

WIN = [("豁免 1650-1709", 1650, 1709), ("后 1720-1779", 1720, 1779)]
# 类：机械规则，Modern_Country == Sweden，零判断（R6 第九款那条）
info = {}
hdr = None
with (RAW / "doorvaarten.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";"); h = next(r); hdr = h
    iy, iid, isp = h.index("jaar"), h.index("id_doorvaart"), h.index("schipper_plaatsnaam")
    im1, ib1 = h.index("totaal_muntsoort1"), h.index("totaal_bedrag1")
    im2, ib2 = h.index("totaal_muntsoort2"), h.index("totaal_bedrag2")
    im3 = h.index("totaal_muntsoort3")
    for row in r:
        try: y = int(row[iy]); did = int(row[iid])
        except (ValueError, IndexError): continue
        w = None
        for lab, a, b in WIN:
            if a <= y <= b: w = lab
        if w is None: continue
        p = row[isp].strip(); k = home.get(p) or src.get(p)
        if not k: continue
        co = std[k][2]
        cls = "瑞" if co == "Sweden" else "非瑞"
        if row[im1].strip() != "Daler" or row[im3].strip() not in MISS: continue
        m2 = row[im2].strip()
        if m2 not in MISS and m2 != "Skilling": continue
        a1 = val(row[ib1]); a2 = val(row[ib2]) if m2 == "Skilling" else 0.0
        if a1 is None or a2 is None: continue
        info[did] = (w, cls, a1 + a2 / B)
print("doorvaarten 字段：", [c for c in hdr if "totaal" in c or c in ("jaar","id_doorvaart","schipper_plaatsnaam")])
print("两个窗口内、籍可解析、纯 Daler(+Skilling) 计价的航次：%d" % len(info))

cell = collections.defaultdict(list)     # (win, route, cls, dir) -> tolls
seen = set()
with (RAW / "ladingen.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";"); h = next(r)
    iid, iv, ina = h.index("id_doorvaart"), h.index("van"), h.index("naar")
    for row in r:
        try: did = int(row[iid])
        except (ValueError, IndexError): continue
        if did in seen or did not in info: continue
        a = v2s.get(row[iv].strip()); b = v2s.get(row[ina].strip())
        if a in west and b in west and west[a] != west[b]:
            seen.add(did)
            w, cls, t = info[did]
            d = "东" if (west[a] and not west[b]) else "西"
            cell[(w, frozenset((a, b)), cls, d)].append(t)
print("其中两端可解析且真正穿越海峡的：%d" % len(seen))

for lab, _, _ in WIN:
    routes = {k[1] for k in cell if k[0] == lab}
    quad = []
    for pr in routes:
        n = [len(cell.get((lab, pr, c, d), [])) for c in ("瑞", "非瑞") for d in ("东", "西")]
        quad.append((min(n), sum(n), tuple(sorted(pr)), n))
    quad.sort(reverse=True)
    for thr in (40, 20, 10, 5, 1):
        print("%-16s 四个格都 >= %-3d 的航线：%d" % (lab, thr, sum(1 for q in quad if q[0] >= thr)))
    print("%-16s 按最薄格排前 12（n 顺序：瑞东 瑞西 非瑞东 非瑞西）" % lab)
    for mn, tot, pr, n in quad[:12]:
        print("   最薄 %-5d 合计 %-6d %-34s %s" % (mn, tot, " ↔ ".join(pr)[:34], n))
    print()
json.dump({"|".join([k[0], "~".join(sorted(k[1])), k[2], k[3]]): v for k, v in cell.items()},
          (CACHE / "b44_r5_cells.json").open("w", encoding="utf-8"), ensure_ascii=False)
print("落缓存 b44_r5_cells.json（%d 个格）" % len(cell))
