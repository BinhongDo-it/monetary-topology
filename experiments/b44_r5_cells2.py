# -*- coding: utf-8 -*-
"""R5 第一步之二：把类切细到国别再建一次格，为的是三个安慰剂：
  (1) 非瑞典类按航次号奇偶劈两半 —— 纯抽样噪声底
  (2) 尼德兰 对 不列颠 —— 两支真实不同的船队、同一张税则，含组成差的底
  (3) 同一对在豁免期上再跑一次 —— 在瑞荷读到 0.25 的那个窗口里，荷英应当读到底
口径与 b44_r5_cells.py 完全一致，只换了类的粒度。"""
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
CO = {"Sweden": "瑞", "The Netherlands": "荷", "United Kingdom": "英",
      "Denmark": "丹", "Norway": "挪", "Germany": "德"}
WIN = [("豁免", 1650, 1709), ("后", 1720, 1779)]
info = {}
with (RAW / "doorvaarten.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";"); h = next(r)
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
        cls = CO.get(std[k][2], "余")
        if row[im1].strip() != "Daler" or row[im3].strip() not in MISS: continue
        m2 = row[im2].strip()
        if m2 not in MISS and m2 != "Skilling": continue
        a1 = val(row[ib1]); a2 = val(row[ib2]) if m2 == "Skilling" else 0.0
        if a1 is None or a2 is None: continue
        info[did] = (w, cls, a1 + a2 / B)
cell = collections.defaultdict(list); seen = set()
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
            cell[(w, "~".join(sorted((a, b))), cls, d)].append((did, t))
print("穿越海峡且计价干净的航次 %d，格 %d" % (len(seen), len(cell)))
# 2026-09-03 自查抓到：原来这里过滤 len>=3，于是散在小国别里的航次被丢掉，
# n>=20 那一档的航线数从 16 掉到 14。类是要合并的，所以一格都不许先丢。
out = {"|".join(k): v for k, v in cell.items()}
json.dump(out, (CACHE / "b44_r5_cells2.json").open("w", encoding="utf-8"), ensure_ascii=False)
print("落缓存 b44_r5_cells2.json：n>=3 的格 %d 个，%.1f MB"
      % (len(out), (CACHE / "b44_r5_cells2.json").stat().st_size / 1e6))
for lab, _, _ in WIN:
    for pair in [("瑞", "荷"), ("荷", "英")]:
        routes = {k[1] for k in cell if k[0] == lab}
        q = []
        for pr in routes:
            n = [len(cell.get((lab, pr, c, d), [])) for c in pair for d in ("东", "西")]
            q.append((min(n), tuple(pr.split("~")), n))
        q.sort(reverse=True)
        print("%-4s %s对%s：四格 >=40 的航线 %d 条，>=20 的 %d 条；最厚三条 %s"
              % (lab, pair[0], pair[1], sum(1 for x in q if x[0] >= 40),
                 sum(1 for x in q if x[0] >= 20),
                 "; ".join("%s %s" % ("↔".join(x[1])[:26], x[2]) for x in q[:3])))
