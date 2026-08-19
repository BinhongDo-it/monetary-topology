"""B14-0 闸零：处理组的摩擦半有没有相对对照组变宽。

判据由 claude/B14_设计_v1.md §4 钉死：

    Δ(sym, ctr) = log( 后窗逐日 spd 的中位数 / 前窗逐日 spd 的中位数 )
    组统计量    = 组内对标的取 Δ 的中位数
    PASS        = G1>C 且 G2>C 且 G3>C，在 N 与 P 两个场所上都成立（六条）

主口径 = WA_BBO_Spd 按 Order_Shares_Ct 加权。
并列跑：同量按 Order_Count 加权（权重口径核，D3-3），WA_NBBO_Spd 按股数加权（旁证，不裁定）。

用法
    python experiments/b14_gate0.py --selftest
    python experiments/b14_gate0.py --run
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "data", "cache", "b14")
OUT = os.path.join(ROOT, "results", "b14_gate0.json")

PRE = ("20160801", "20160930")
POST = ("20161101", "20161231")
MIN_DAYS = 10
GRP_FROM = "post"   # D3-9'，设计件 §3·补1：分组归属只从后窗读
#: T8（设计件 §3·补2）：FINRA 发布的权威分组名单。给了它就用它，不用后窗推。
AUTH = os.path.join(ROOT, "data", "raw", "Tick_Pilot_Test_Group_Assignments.txt")
GROUPS = ["C", "G1", "G2", "G3"]
# (名字, 分子列, 分母列的集合, 说明)。v2 列号见 b14_tickpilot_panel.py 的 HEAD。
MEASURES = [
    ("bbo_shr", 4, (5,), "主口径：WA_BBO_Spd 按股数加权"),
    ("bbo_cnt", 6, (7,), "权重口径核：WA_BBO_Spd 按笔数加权"),
    ("bbo_shr_adv", 4, (5, 14),
     "T5 对抗口径：零价差行按真实股数权重当作价差为零收进来（设计件 §4·补1）"),
    ("bbo_shr_adv2", 4, (5, 14, 16),
     "T6 算术敏感度：零与空都按真实股数权重当作价差为零收进来（设计件 §4·补2）"),
    ("nbbo_shr", 8, (9,), "旁证：WA_NBBO_Spd 按股数加权，不参与裁定"),
]
T5_MEASURE = "bbo_shr_adv"
T6_MEASURE = "bbo_shr_adv2"


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def load_authoritative():
    """FINRA 的 Tick_Pilot_Test_Group_Assignments.txt -> {ticker: group}。"""
    out = {}
    with open(AUTH, encoding="latin-1") as fh:
        head = fh.readline().rstrip("\n").split("|")
        i_sym = head.index("Ticker_Symbol")
        i_grp = head.index("Tick_Size_Pilot_Program_Group")
        for line in fh:
            f = line.rstrip("\n").split("|")
            if len(f) <= max(i_sym, i_grp):
                continue
            g = f[i_grp].strip()
            if g in GROUPS:
                out[f[i_sym].strip()] = g
    return out


def load():
    """(ctr, sym) -> {"grp": set, "pre": {name: [spd]}, "post": {...}}"""
    import math
    rec = {}
    files = sorted(f for f in os.listdir(CACHE)
                   if f.startswith("panel_v2_") and f.endswith(".csv"))
    assert files, "没有 v2 缓存，先跑 b14_tickpilot_panel.py --build"
    for fn in files:
        with open(os.path.join(CACHE, fn)) as fh:
            head = fh.readline()
            assert head.startswith("date,ctr,symbol,test_group,"), fn
            for line in fh:
                if line.startswith("#"):
                    continue
                p = line.rstrip("\n").split(",")
                date, ctr, sym, grp = p[0], p[1], p[2], p[3]
                if PRE[0] <= date <= PRE[1]:
                    win = "pre"
                elif POST[0] <= date <= POST[1]:
                    win = "post"
                else:
                    continue
                r = rec.get((ctr, sym))
                if r is None:
                    r = rec[(ctr, sym)] = {
                        "grp": set(),
                        "pre": {m[0]: [] for m in MEASURES},
                        "post": {m[0]: [] for m in MEASURES},
                    }
                # D3-9'（设计件 §3·补1）：分组归属只从后窗读。
                # 该字段记的是「该证券在该日处于什么状态」，前窗里受处理的证券也全标 C。
                if win == GRP_FROM:
                    r["grp"].add(grp)
                for name, inum, idens, _ in MEASURES:
                    den = sum(float(p[i]) for i in idens)
                    if den > 0:
                        v = float(p[inum]) / den
                        if v > 0:
                            r[win][name].append(math.log(v))
    return rec, files


def deltas(rec, auth=None):
    """每个 (ctr, sym) 一个 Δ，按 measure 分开。中位数取在 log 上，所以 Δ 是两个中位数之差。"""
    out = {m[0]: {} for m in MEASURES}
    skipped = {"组不唯一": 0, "天数不够": 0, "后窗无标签": 0}
    for (ctr, sym), r in rec.items():
        if auth is not None:
            grp = auth.get(sym)
            if grp is None:
                skipped["权威名单查无此标的"] = skipped.get("权威名单查无此标的", 0) + 1
                continue
        else:
            if not r["grp"]:
                skipped["后窗无标签"] += 1
                continue
            if len(r["grp"]) != 1:
                skipped["组不唯一"] += 1
                continue
            grp = next(iter(r["grp"]))
        if grp not in GROUPS:
            continue
        for name in out:
            a, b = r["pre"][name], r["post"][name]
            if len(a) < MIN_DAYS or len(b) < MIN_DAYS:
                if name == MEASURES[0][0]:
                    skipped["天数不够"] += 1
                continue
            out[name].setdefault((ctr, grp), []).append(median(b) - median(a))
    return out, skipped


args_authoritative = [False]


def run():
    rec, files = load()
    print("读入 %d 件缓存，%d 个 (场所, 标的)" % (len(files), len(rec)))
    auth = load_authoritative() if args_authoritative[0] else None
    if auth is not None:
        print("T8：用 FINRA 权威分组名单，%d 只（设计件 §3·补2）" % len(auth))
    d, skipped = deltas(rec, auth)
    print("剔除：" + "，".join("%s %d" % (k, v) for k, v in skipped.items()
                              if v) + "\n")

    ctrs = sorted({c for name in d for (c, g) in d[name]})
    res = {"pre": PRE, "post": POST, "min_days": MIN_DAYS, "measures": {}}
    verdict = {}

    prev = None
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT))
        except Exception:
            prev = None

    for name, _, _, desc in MEASURES:
        print("== %s (%s) ==" % (name, desc))
        print("  %-4s %-4s %6s %10s %12s" % ("场所", "组", "标的数", "Δ中位数", "相对C"))
        tab = {}
        for ctr in ctrs:
            base = median(d[name].get((ctr, "C"), []))
            for grp in GROUPS:
                xs = d[name].get((ctr, grp), [])
                m = median(xs)
                tab[ctr + "/" + grp] = {"n": len(xs), "delta": m}
                rel = "" if (m is None or base is None) else "%+.6f" % (m - base)
                print("  %-4s %-4s %6d %10s %12s"
                      % (ctr, grp, len(xs),
                         "None" if m is None else "%+.6f" % m, rel))
        res["measures"][name] = {"desc": desc, "table": tab}
        ineq = []
        for ctr in ctrs:
            base = median(d[name].get((ctr, "C"), []))
            for grp in ["G1", "G2", "G3"]:
                m = median(d[name].get((ctr, grp), []))
                ok = (m is not None and base is not None and m > base)
                ineq.append({"ctr": ctr, "grp": grp, "holds": ok,
                             "margin": None if (m is None or base is None) else m - base})
        res["measures"][name]["inequalities"] = ineq
        v = all(x["holds"] for x in ineq) and len(ineq) == 6
        verdict[name] = v
        print("  六条不等式：%d/%d 成立  ->  %s\n"
              % (sum(1 for x in ineq if x["holds"]), len(ineq), "PASS" if v else "FAIL"))

    primary = MEASURES[0][0]
    weight_chk = MEASURES[1][0]
    res["verdict"] = {
        "primary": primary,
        "B14-0": "PASS" if verdict[primary] else "FAIL",
        "weight_agrees": verdict[primary] == verdict[weight_chk],
        "per_measure": verdict,
    }

    t6 = res["measures"][T6_MEASURE]["inequalities"]
    t6_all = all(x["holds"] for x in t6) and len(t6) == 6
    res["t6"] = {
        "measure": T6_MEASURE,
        "all_hold": bool(t6_all),
        "failing": [x["ctr"] + "/" + x["grp"] for x in t6 if not x["holds"]],
        "note": ("blanks are states with no quote, i.e. the widest kind; "
                 "imputing them at zero is a bound on the arithmetic and not "
                 "on the world, so a failure here is not a threat to B14-0 "
                 "(design file section 4 supplement 2)"),
    }

    t5 = res["measures"][T5_MEASURE]["inequalities"]
    t5_all = all(x["holds"] for x in t5) and len(t5) == 6
    res["t5"] = {
        "measure": T5_MEASURE,
        "settled": bool(t5_all),
        "failing": [x["ctr"] + "/" + x["grp"] for x in t5 if not x["holds"]],
    }

    # 设计件 §4·补1 要求的复现核：加列不改原有列，v2 上重跑主口径必须逐位复现
    # 已登记的六个边距。不复现即为代码错，本次一切读数作废。
    repro = None
    if prev and "measures" in prev and primary in prev["measures"]:
        old = {(x["ctr"], x["grp"]): x["margin"]
               for x in prev["measures"][primary]["inequalities"]}
        new = {(x["ctr"], x["grp"]): x["margin"]
               for x in res["measures"][primary]["inequalities"]}
        diffs = [(k, old[k], new[k]) for k in new
                 if k in old and old[k] is not None and new[k] is not None
                 and abs(old[k] - new[k]) > 0]
        repro = {"checked": len([k for k in new if k in old]),
                 "identical": not diffs,
                 "diffs": [{"cell": k[0] + "/" + k[1], "was": a, "now": b}
                           for k, a, b in diffs]}
    res["reproduction_check"] = repro

    # scripts/render_results.py 的记录形状：stage + criteria[{name, passed, detail}]。
    # 六条不等式各自一条，权重口径核一条，旁证 NBBO 记为 diagnostic 不参与计数。
    crit = []
    for x in res["measures"][primary]["inequalities"]:
        c, g = x["ctr"], x["grp"]
        t = res["measures"][primary]["table"]
        crit.append({
            "name": "B14-0  %s on venue %s: median delta exceeds control" % (g, c),
            "passed": bool(x["holds"]),
            "detail": ("%s %+.6f over %d symbols, C %+.6f over %d, margin %+.6f"
                       % (g, t[c + "/" + g]["delta"], t[c + "/" + g]["n"],
                          t[c + "/C"]["delta"], t[c + "/C"]["n"], x["margin"])),
        })
    crit.append({
        "name": "B14-0  the verdict does not turn on the weighting convention",
        "passed": bool(res["verdict"]["weight_agrees"]),
        "detail": ("share-weighted verdict %s, order-count-weighted verdict %s "
                   "(design file D3-3: disagreement makes the gate unadjudicable)"
                   % ("PASS" if verdict[primary] else "FAIL",
                      "PASS" if verdict[weight_chk] else "FAIL")),
    })
    for x in res["measures"]["nbbo_shr"]["inequalities"]:
        c, g = x["ctr"], x["grp"]
        crit.append({
            "name": "B14-0  cross-check on the consolidated spread: %s on %s" % (g, c),
            "passed": bool(x["holds"]),
            "diagnostic": True,
            "detail": "margin %+.6f; design file section 4 excludes this from the verdict"
                      % x["margin"],
        })
    for x in t5:
        crit.append({
            "name": "B14-0/T5  adverse convention, %s on venue %s"
                    % (x["grp"], x["ctr"]),
            "passed": bool(x["holds"]),
            "detail": ("margin %+.6f with zero-spread rows admitted at their true "
                       "share weight; design file section 4 supplement 1"
                       % x["margin"]),
        })
    for x in t6:
        crit.append({
            "name": "B14-0/T6  blanks and zeros both forced to zero, %s on venue %s"
                    % (x["grp"], x["ctr"]),
            "passed": bool(x["holds"]),
            "diagnostic": True,
            "detail": ("margin %+.6f; a blank is a no-quote state, so this "
                       "convention is a bound on the arithmetic and not on the "
                       "world (design file section 4 supplement 2)" % x["margin"]),
        })
    crit.append({
        "name": "B14-0  the six registered margins reproduce on the v2 cache",
        "passed": bool(repro is None or repro["identical"]),
        "detail": ("no prior record to compare" if repro is None else
                   "%d margins compared, %d differ"
                   % (repro["checked"], len(repro["diffs"]))),
    })
    res["stage"] = "B14"
    res["criteria"] = crit
    res["window"] = [PRE[0], POST[1]]
    res["symbols_by_venue"] = {
        c: sum(res["measures"][primary]["table"][c + "/" + g]["n"] for g in GROUPS)
        for c in ctrs
    }
    res["derived"] = {
        ("median_delta_%s_%s" % (c, g)): res["measures"][primary]["table"][c + "/" + g]["delta"]
        for c in ctrs for g in GROUPS
        if res["measures"][primary]["table"][c + "/" + g]["delta"] is not None
    }
    print("裁定（依设计件 §4）")
    print("  B14-0 = %s（主口径 %s）" % (res["verdict"]["B14-0"], primary))
    print("  权重口径同号：%s" % ("是" if res["verdict"]["weight_agrees"] else "否 -> 闸零不可裁"))
    print("  旁证 NBBO：%s（不参与裁定）" % ("PASS" if verdict["nbbo_shr"] else "FAIL"))
    print("\nT5（依设计件 §4·补1）")
    print("  对抗口径六条：%d/6 成立  ->  T5 %s"
          % (sum(1 for x in t5 if x["holds"]),
             "结清，判死" if t5_all else "未结：" + ", ".join(res["t5"]["failing"])))
    print("\nT6（依设计件 §4·补2，算术敏感度，不参与裁定）")
    print("  零与空都按真实权重当作零：%d/6 成立%s"
          % (sum(1 for x in t6 if x["holds"]),
             "" if t6_all else "  翻掉的是 " + ", ".join(res["t6"]["failing"])))
    print("  空的含义是该场所当时没有报价，是最宽的一类状态；把它算成零"
          "在方向上与其含义相反，故此处的翻掉不构成对 B14-0 的威胁。")

    if repro is None:
        print("  复现核：没有可比的前一份记录，跳过")
    elif repro["identical"]:
        print("  复现核：主口径 %d 个边距与已登记记录逐位相同" % repro["checked"])
    else:
        print("  复现核：**不相同**，%d 个边距变了 -> 依设计件 §4·补1，本次一切读数作废"
              % len(repro["diffs"]))
        for d in repro["diffs"]:
            print("    %s  %r -> %r" % (d["cell"], d["was"], d["now"]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("\n写出 %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("中位数，奇数个", median([3, 1, 2]) == 2)
    chk("中位数，偶数个取中间两个的平均", median([1, 2, 3, 4]) == 2.5)
    chk("空表返回 None", median([]) is None)
    chk("分组归属只从后窗读（§3·补1 D3-9'）", GRP_FROM == "post")
    chk("权威名单文件在盘", os.path.exists(AUTH))
    _a = load_authoritative()
    chk("权威名单读得出四个组且只有四个组",
        set(_a.values()) == {"C", "G1", "G2", "G3"} and len(_a) > 2000)
    chk("前窗后窗不重叠且都不含 2016-10",
        PRE[1] < "20161001" and POST[0] > "20161031")
    chk("窗口与设计件 §3 D3-6 一致",
        PRE == ("20160801", "20160930") and POST == ("20161101", "20161231"))
    chk("主口径列号指向 bbo/股数",
        MEASURES[0][0] == "bbo_shr" and MEASURES[0][1] == 4
        and MEASURES[0][2] == (5,))
    chk("旁证不参与裁定：MEASURES 里它排在最后",
        MEASURES[-1][0] == "nbbo_shr")
    chk("T5 对抗口径的分母是 den + zero_shr",
        dict((m[0], m[2]) for m in MEASURES)[T5_MEASURE] == (5, 14))
    chk("T5 对抗口径与主口径共用同一个分子",
        dict((m[0], m[1]) for m in MEASURES)[T5_MEASURE] == MEASURES[0][1])
    chk("T6 口径的分母是 den + zero_shr + blank_shr",
        dict((m[0], m[2]) for m in MEASURES)[T6_MEASURE] == (5, 14, 16))
    chk("T6 的分母包含 T5 的分母，故 T6 只会更严",
        set(dict((m[0], m[2]) for m in MEASURES)[T5_MEASURE])
        < set(dict((m[0], m[2]) for m in MEASURES)[T6_MEASURE]))

    r = {("N", "AAA"): {"grp": {"G1"}, "pre": {}, "post": {}},
         ("N", "BBB"): {"grp": {"C", "G1"}, "pre": {}, "post": {}},
         ("N", "CCC"): {"grp": set(), "pre": {}, "post": {}}}
    for k in r:
        for w in ("pre", "post"):
            r[k][w] = {m[0]: [0.0] * 20 for m in MEASURES}
    d, sk = deltas(r)
    chk("后窗标签不唯一的标的被剔除并计数", sk["组不唯一"] == 1)
    chk("后窗完全没有标签的标的被剔除并计数", sk["后窗无标签"] == 1)
    chk("剩下的标的进了 (N, G1)", list(d["bbo_shr"]) == [("N", "G1")])

    r2 = {("N", "AAA"): {"grp": {"G1"},
                         "pre": {m[0]: [0.0] * 9 for m in MEASURES},
                         "post": {m[0]: [0.0] * 20 for m in MEASURES}}}
    d2, sk2 = deltas(r2)
    chk("前窗只有 9 天的标的被剔除", sk2["天数不够"] == 1 and not d2["bbo_shr"])

    import math
    r3 = {("N", "AAA"): {"grp": {"G1"},
                         "pre": {m[0]: [math.log(0.01)] * 12 for m in MEASURES},
                         "post": {m[0]: [math.log(0.05)] * 12 for m in MEASURES}}}
    d3, _ = deltas(r3)
    chk("1 分变 5 分给出 log5 的 Δ",
        abs(d3["bbo_shr"][("N", "G1")][0] - math.log(5)) < 1e-12)

    print("\n  " + ("全部通过" if ok else "有失败"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--authoritative", action="store_true",
                    help="T8：分组用 FINRA 权威名单，不用后窗推（设计件 §3·补2）")
    a = ap.parse_args()
    args_authoritative[0] = a.authoritative
    if a.authoritative:
        global OUT
        OUT = OUT.replace(".json", ".authoritative.json")
    if a.selftest:
        return selftest()
    if a.run:
        return run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
