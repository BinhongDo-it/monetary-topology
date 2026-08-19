"""B14 阶段一：把 Tick Pilot Appendix B.I 逐月文件压成 (日期, 场所, 标的) 面板。

口径由 claude/B14_设计_v1.md §3 钉死，本脚本只执行，不选择。

  D3-2  spd = sum(w * WA_BBO_Spd) / sum(w),  w = Order_Shares_Ct
  D3-3  同一趟并算 w = Order_Count 的第二条
  D3-4  入格要求 spd 非空且 > 0，且 w > 0
  D3-5  不做任何标志位筛选
  §4    旁证 WA_NBBO_Spd 同法一遍，不参与裁定

用法
    python experiments/b14_tickpilot_panel.py --selftest
    python experiments/b14_tickpilot_panel.py --build            # 全部十件
    python experiments/b14_tickpilot_panel.py --build --only NYSE_MKTQUALITYSTATS_201612.gzip

可重入：目标缓存最后一行是 #DONE 则跳过。写 .part 再改名，中断不会留下半张表。
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
CACHE = os.path.join(ROOT, "data", "cache", "b14")

# 0-based 列号，见 B14_设计_v1.md §1 的字段行
C_DATE, C_CTR, C_SYM, C_GRP = 1, 2, 3, 4
C_ORDCNT, C_SHARES = 15, 16
C_NBBO, C_BBO = 42, 43
NFIELDS = 53

SCHEMA = "v2"   # v2 = v1 加四列（设计件 §4·补1，T5 的判法）
HEAD = ("date,ctr,symbol,test_group,"
        "bbo_shr_num,bbo_shr_den,bbo_cnt_num,bbo_cnt_den,"
        "nbbo_shr_num,nbbo_shr_den,"
        "rows,adm_bbo,blank_bbo,zero_bbo,"
        "zero_shr,zero_cnt,blank_shr,blank_cnt,neg_bbo")


def _num(s):
    """空串与非数字返回 None；否则返回 float。"""
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def accumulate(lines):
    """吃一串已按 | 切好的字段列表，吐出 (date, ctr, sym, grp) -> 累加器。"""
    acc = {}
    bad_width = 0
    for f in lines:
        if len(f) != NFIELDS:
            bad_width += 1
            continue
        key = (f[C_DATE], f[C_CTR], f[C_SYM], f[C_GRP])
        a = acc.get(key)
        if a is None:
            a = acc[key] = [0.0] * 6 + [0, 0, 0, 0] + [0.0, 0.0, 0.0, 0.0, 0]
        a[6] += 1                                  # rows
        bbo = _num(f[C_BBO])
        shr = _num(f[C_SHARES])
        cnt = _num(f[C_ORDCNT])
        nbbo = _num(f[C_NBBO])
        if bbo is None:
            a[8] += 1                              # blank
            if shr is not None and shr > 0:
                a[12] += shr                       # blank_shr
            if cnt is not None and cnt > 0:
                a[13] += cnt                       # blank_cnt
        elif bbo <= 0:
            a[9] += 1                              # zero (或负，同样不是价差)
            if bbo < 0:
                a[14] += 1                         # neg_bbo，交叉盘，单独记
            # T5 的对抗口径要它们的真实权重（设计件 §4·补1）
            if shr is not None and shr > 0:
                a[10] += shr                       # zero_shr
            if cnt is not None and cnt > 0:
                a[11] += cnt                       # zero_cnt
        else:
            if shr is not None and shr > 0:
                a[0] += shr * bbo
                a[1] += shr
                a[7] += 1                          # adm_bbo，以主口径的权重为准
            if cnt is not None and cnt > 0:
                a[2] += cnt * bbo
                a[3] += cnt
        if nbbo is not None and nbbo > 0 and shr is not None and shr > 0:
            a[4] += shr * nbbo
            a[5] += shr
    return acc, bad_width


def stream(path):
    """zcat 出来，只留 D 行，切好字段。"""
    p = subprocess.Popen(["zcat", path], stdout=subprocess.PIPE, bufsize=1 << 20)
    try:
        for raw in p.stdout:
            if raw[:2] != b"D|":
                continue
            yield raw.decode("latin-1").rstrip("\r\n").split("|")
    finally:
        p.stdout.close()
        p.wait()


def out_path(fname):
    m = re.match(r"(.+)_MKTQUALITYSTATS_(\d{6})\.gzip$", fname)
    if not m:
        return None
    return os.path.join(CACHE, "panel_%s_%s_%s.csv"
                        % (SCHEMA, m.group(1), m.group(2)))


def is_done(path):
    if not os.path.exists(path):
        return False
    with open(path, "rb") as fh:
        try:
            fh.seek(-4096, os.SEEK_END)
        except OSError:
            fh.seek(0)
        tail = fh.read().splitlines()
    return bool(tail) and tail[-1].startswith(b"#DONE")


def build_one(fname):
    src = os.path.join(RAW, fname)
    dst = out_path(fname)
    if dst is None:
        print("  跳过（文件名不认识）:", fname)
        return
    if is_done(dst):
        print("  已在缓存，跳过:", os.path.basename(dst))
        return
    os.makedirs(CACHE, exist_ok=True)
    acc, bad = accumulate(stream(src))
    tmp = dst + ".part"
    n = 0
    with open(tmp, "w") as fh:
        fh.write(HEAD + "\n")
        for (d, c, s, g) in sorted(acc):
            a = acc[(d, c, s, g)]
            fh.write("%s,%s,%s,%s,%.6f,%.0f,%.6f,%.0f,%.6f,%.0f,"
                     "%d,%d,%d,%d,%.0f,%.0f,%.0f,%.0f,%d\n"
                     % (d, c, s, g, a[0], a[1], a[2], a[3], a[4], a[5],
                        a[6], a[7], a[8], a[9],
                        a[10], a[11], a[12], a[13], a[14]))
            n += 1
        fh.write("#DONE schema=%s keys=%d bad_width=%d src=%s\n"
                 % (SCHEMA, n, bad, fname))
    os.replace(tmp, dst)
    tot = sum(acc[k][6] for k in acc)
    adm = sum(acc[k][7] for k in acc)
    blk = sum(acc[k][8] for k in acc)
    zer = sum(acc[k][9] for k in acc)
    print("  %-40s 标的日 %6d  行 %9d  入格 %.4f  空 %d  零 %d  宽度异常 %d"
          % (fname, n, tot, (adm / tot if tot else 0.0), blk, zer, bad))


def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        print(("  PASS  " if cond else "  FAIL  ") + name)
        ok = ok and cond

    row = ["D"] * NFIELDS
    row[C_DATE], row[C_CTR], row[C_SYM], row[C_GRP] = "20161201", "N", "AAA", "G1"

    a = list(row); a[C_BBO], a[C_SHARES], a[C_ORDCNT], a[C_NBBO] = "0.0500", "100", "1", "0.0500"
    b = list(row); b[C_BBO], b[C_SHARES], b[C_ORDCNT], b[C_NBBO] = "0.0100", "300", "1", "0.0100"
    acc, bad = accumulate([a, b])
    v = acc[("20161201", "N", "AAA", "G1")]
    chk("按股数加权把 0.05@100 与 0.01@300 压成 0.02", abs(v[0] / v[1] - 0.02) < 1e-12)
    chk("按笔数加权把同两格压成 0.03", abs(v[2] / v[3] - 0.03) < 1e-12)
    chk("两个权重口径给出不同的数，所以并列跑不是多余的", abs(v[0] / v[1] - v[2] / v[3]) > 1e-9)

    z = list(row); z[C_BBO], z[C_SHARES], z[C_ORDCNT] = "0.0000", "999999", "9"
    e = list(row); e[C_BBO], e[C_SHARES], e[C_ORDCNT] = "", "999999", "9"
    acc2, _ = accumulate([a, b, z, e])
    v2 = acc2[("20161201", "N", "AAA", "G1")]
    chk("零价差不进加权均值", abs(v2[0] / v2[1] - 0.02) < 1e-12)
    chk("空价差不进加权均值", abs(v2[2] / v2[3] - 0.03) < 1e-12)
    chk("零与空各自记数", v2[8] == 1 and v2[9] == 1)
    chk("rows 记全部四行", v2[6] == 4)
    chk("adm_bbo 只记入格的两行", v2[7] == 2)

    w = list(row); w[C_BBO], w[C_SHARES], w[C_ORDCNT] = "0.0500", "0", "0"
    acc3, _ = accumulate([a, w])
    v3 = acc3[("20161201", "N", "AAA", "G1")]
    chk("零权重的格不改变加权均值", abs(v3[0] / v3[1] - 0.05) < 1e-12)

    acc5, _ = accumulate([a, b, z, e])
    v5 = acc5[("20161201", "N", "AAA", "G1")]
    chk("零价差行的股数权重被记进 zero_shr", abs(v5[10] - 999999) < 1e-9)
    chk("空价差行的股数权重被记进 blank_shr", abs(v5[12] - 999999) < 1e-9)
    chk("对抗口径把 spd 压低：num/(den+zero_shr) < num/den",
        v5[0] / (v5[1] + v5[10]) < v5[0] / v5[1])
    neg = list(row); neg[C_BBO], neg[C_SHARES], neg[C_ORDCNT] = "-0.0100", "50", "1"
    acc6, _ = accumulate([a, neg])
    v6 = acc6[("20161201", "N", "AAA", "G1")]
    chk("负价差（交叉盘）单独计数，且与零一样进 zero_shr",
        v6[14] == 1 and abs(v6[10] - 50) < 1e-9 and v6[9] == 1)
    chk("负价差不进加权均值", abs(v6[0] / v6[1] - 0.05) < 1e-12)

    short = ["D", "20161201", "N"]
    acc4, bad4 = accumulate([short])
    chk("字段数不对的行被计数并丢弃", bad4 == 1 and not acc4)

    chk("列号对得上 B14 设计件 §1（第 44 字段 = WA_BBO_Spd）", C_BBO == 43 and NFIELDS == 53)
    chk("表头列数与写出的列数一致", len(HEAD.split(",")) == 19)
    print("\n  " + ("全部通过" if ok else "有失败"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.build:
        ap.print_help()
        return 2
    if args.only:
        names = [args.only]
    else:
        names = sorted(f for f in os.listdir(RAW)
                       if re.match(r".+_MKTQUALITYSTATS_\d{6}\.gzip$", f))
    print("B14 面板构建，%d 件" % len(names))
    for fn in names:
        build_one(fn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
