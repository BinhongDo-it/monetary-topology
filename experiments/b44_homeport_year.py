# -*- coding: utf-8 -*-
"""一次扫描，落一张可复用的表：籍标准港 × 年 -> [航次, 明细行, aantal 非空]。

此后「哪个籍港在哪几年不量货」这一族问题全部是这张表上的算术，不再碰 837 MB 的原件。
籍取 schipper_plaatsnaam，经 places_source.home_port -> soundcoding -> places_standard.Kode 标准化
（口径与 homeport_std.py / sovereignty_test.py 完全一致）。
缺失占位符按 §126.40 第二款那条：'-' 是占位符不是值。
"""
import csv, json, pathlib, array, time
import numpy as np

_H = pathlib.Path(__file__).resolve().parent
RAW = _H.parent / "data/raw/stro/classic"
CACHE = _H.parent / "data/cache/stro_classic"
csv.field_size_limit(10 ** 8)
MISS = {"", "-", "?", "--"}
Y0, Y1 = 1600, 1790

M = json.load((CACHE / "place_std_map.json").open(encoding="utf-8"))
home, src, std = M["home"], M["src"], M["std"]

t0 = time.time()
# ---- 第一遍：doorvaarten，建 id -> (籍港, 年) ----
keys, kidx = [], {}
ids = array.array("q")
kis = array.array("i")
n_pass_tot = n_pass_ok = 0
with (RAW / "doorvaarten.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";")
    h = next(r)
    iy, isp, iid = h.index("jaar"), h.index("schipper_plaatsnaam"), h.index("id_doorvaart")
    for row in r:
        n_pass_tot += 1
        try:
            y = int(row[iy]); did = int(row[iid])
        except (ValueError, IndexError):
            continue
        if not (Y0 <= y <= Y1):
            continue
        p = row[isp].strip()
        if p in MISS:
            continue
        k = home.get(p) or src.get(p)
        if not k:
            continue
        nm = std[k][0]
        key = (nm, y)
        j = kidx.get(key)
        if j is None:
            j = kidx[key] = len(keys); keys.append(key)
        ids.append(did); kis.append(j)
        n_pass_ok += 1
print("第一遍 doorvaarten：%d 行，窗口内可解析籍的航次 %d，(籍港,年) 格 %d，%.1f 秒"
      % (n_pass_tot, n_pass_ok, len(keys), time.time() - t0))

A = np.frombuffer(ids, dtype=np.int64)
B = np.frombuffer(kis, dtype=np.int32)
o = np.argsort(A, kind="stable")
A, B = A[o], B[o]

# ---- 第二遍：ladingen，逐明细行 ----
t1 = time.time()
lid = array.array("q"); lok = array.array("b")
n_line = 0
with (RAW / "ladingen.csv").open(encoding="utf-8", newline="") as f:
    r = csv.reader(f, delimiter=";")
    h = next(r)
    iid, ia = h.index("id_doorvaart"), h.index("aantal")
    for row in r:
        n_line += 1
        try:
            did = int(row[iid])
        except (ValueError, IndexError):
            continue
        lid.append(did)
        lok.append(0 if row[ia].strip() in MISS else 1)
L = np.frombuffer(lid, dtype=np.int64)
OK = np.frombuffer(lok, dtype=np.int8)
pos = np.searchsorted(A, L)
pos[pos >= len(A)] = len(A) - 1
hit = A[pos] == L
kk = B[pos]
print("第二遍 ladingen：%d 行，落在窗口内可解析籍的 %d（%.1f%%），%.1f 秒"
      % (n_line, int(hit.sum()), 100 * hit.sum() / n_line, time.time() - t1))

nk = len(keys)
rows = np.bincount(kk[hit], minlength=nk)
fill = np.bincount(kk[hit], weights=OK[hit].astype(np.float64), minlength=nk).astype(np.int64)
pas = np.bincount(B, minlength=nk)

out = {"%s|%d" % (nm, y): [int(pas[j]), int(rows[j]), int(fill[j])]
       for j, (nm, y) in enumerate(keys)}
cty = {}
for p, k in list(home.items()) + list(src.items()):
    nm, _, co = std[k]
    cty.setdefault(nm, co)
out["__country__"] = cty
out["__meta__"] = {"window": [Y0, Y1], "miss": sorted(MISS),
                   "passages_in_window": int(n_pass_ok), "ladingen_rows": int(n_line),
                   "ladingen_matched": int(hit.sum())}
p = CACHE / "b44_homeport_year.json"
p.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
print("落缓存 %s，%d 格，%.1f KB，总计 %.1f 秒" % (p.name, nk, p.stat().st_size / 1024, time.time() - t0))
