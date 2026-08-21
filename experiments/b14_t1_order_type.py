"""B14 T1: dispose of the composition-drift threat.

The threat (design file section 6, T1): WA_BBO_Spd is sampled at the moment an
order arrives, so a change in the mix of order types moves the aggregate even if
the quoting process itself does not move at all.

Two readings; every other convention is word for word the same as sections 3
and 4:

  T1-a  fixed composition: lock each symbol's weights to its own pre-window
        order-type shares, so day to day only the spread moves and the weights
        do not. Composition drift is switched off in this column.
  T1-b  run the gate once per order type and see where the six inequalities hold.

Usage
    python experiments/b14_t1_order_type.py --selftest
    python experiments/b14_t1_order_type.py --build --only NYSE_MKTQUALITYSTATS_201612.gzip
    python experiments/b14_t1_order_type.py --run
"""
import argparse
import collections
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
CACHE = os.path.join(ROOT, "data", "cache", "b14")
OUT = os.path.join(ROOT, "results", "b14_t1_order_type.json")

C_DATE, C_CTR, C_SYM, C_GRP, C_OT = 1, 2, 3, 4, 5
C_SHARES, C_BBO = 16, 43
NFIELDS = 53
PRE = ("20160801", "20160930")
POST = ("20161101", "20161231")
MIN_DAYS = 10
GROUPS = ["C", "G1", "G2", "G3"]
HEAD = "date,ctr,symbol,test_group,order_type,num,den"


def median(xs):
    s = sorted(xs)
    n = len(s)
    return None if n == 0 else (s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2]))


def accumulate(rows):
    acc = {}
    for f in rows:
        if len(f) != NFIELDS:
            continue
        try:
            bbo = float(f[C_BBO]) if f[C_BBO] else None
            shr = float(f[C_SHARES]) if f[C_SHARES] else None
        except ValueError:
            continue
        if bbo is None or bbo <= 0 or shr is None or shr <= 0:
            continue
        k = (f[C_DATE], f[C_CTR], f[C_SYM], f[C_GRP], f[C_OT])
        a = acc.get(k)
        if a is None:
            a = acc[k] = [0.0, 0.0]
        a[0] += shr * bbo
        a[1] += shr
    return acc


def stream(path):
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
    return None if not m else os.path.join(
        CACHE, "panel_ot_%s_%s.csv" % (m.group(1), m.group(2)))


def is_done(path):
    if not os.path.exists(path):
        return False
    with open(path, "rb") as fh:
        try:
            fh.seek(-4096, os.SEEK_END)
        except OSError:
            fh.seek(0)
        t = fh.read().splitlines()
    return bool(t) and t[-1].startswith(b"#DONE")


def build_one(fname):
    dst = out_path(fname)
    if dst is None or is_done(dst):
        print("  skipped:", fname)
        return
    os.makedirs(CACHE, exist_ok=True)
    acc = accumulate(stream(os.path.join(RAW, fname)))
    tmp = dst + ".part"
    with open(tmp, "w") as fh:
        fh.write(HEAD + "\n")
        for k in sorted(acc):
            a = acc[k]
            fh.write("%s,%s,%s,%s,%s,%.6f,%.0f\n" % (k + (a[0], a[1])))
        fh.write("#DONE keys=%d src=%s\n" % (len(acc), fname))
    os.replace(tmp, dst)
    print("  %-40s cells %8d" % (fname, len(acc)))


def load():
    """(ctr, sym) -> {grp, pre: {(date, ot): (num, den)}, post: {...}}"""
    rec = {}
    files = sorted(f for f in os.listdir(CACHE)
                   if f.startswith("panel_ot_") and f.endswith(".csv"))
    assert files, "no panel_ot cache; run --build first"
    for fn in files:
        with open(os.path.join(CACHE, fn)) as fh:
            assert fh.readline().startswith("date,ctr,symbol"), fn
            for line in fh:
                if line.startswith("#"):
                    continue
                d, c, sym, g, ot, num, den = line.rstrip("\n").split(",")
                win = "pre" if PRE[0] <= d <= PRE[1] else (
                    "post" if POST[0] <= d <= POST[1] else None)
                if win is None:
                    continue
                r = rec.get((c, sym))
                if r is None:
                    r = rec[(c, sym)] = {"grp": set(), "pre": {}, "post": {}}
                if win == "post":
                    r["grp"].add(g)                      # D3-9'
                r[win][(d, ot)] = (float(num), float(den))
    return rec, files


def series(cell, fixed=None):
    """One number per day. With fixed weights when given, otherwise that day's own
    weights, which is the primary convention.
    """
    byday = collections.defaultdict(dict)
    for (d, ot), (num, den) in cell.items():
        byday[d][ot] = (num, den)
    out = []
    for d in sorted(byday):
        n = w = 0.0
        for ot, (num, den) in byday[d].items():
            if den <= 0:
                continue
            wt = den if fixed is None else fixed.get(ot, 0.0)
            if wt <= 0:
                continue
            n += wt * (num / den)
            w += wt
        if w > 0 and n / w > 0:
            out.append(math.log(n / w))
    return out


def pre_mix(cell):
    mix = collections.Counter()
    for (_, ot), (_, den) in cell.items():
        mix[ot] += den
    return dict(mix)


def gate(deltas, label):
    ctrs = sorted({c for c, _ in deltas})
    rows, ineq = [], []
    for c in ctrs:
        base = median(deltas.get((c, "C"), []))
        for g in GROUPS:
            m = median(deltas.get((c, g), []))
            rows.append((c, g, len(deltas.get((c, g), [])), m,
                         None if (m is None or base is None) else m - base))
            if g != "C":
                ineq.append({"ctr": c, "grp": g,
                             "holds": bool(m is not None and base is not None and m > base),
                             "margin": None if (m is None or base is None) else m - base})
    print("== %s ==" % label)
    print("  %-6s %-4s %8s %11s %12s"
          % ("venue", "grp", "symbols", "med Delta", "vs C"))
    for c, g, n, m, rel in rows:
        print("  %-4s %-4s %6d %10s %12s"
              % (c, g, n, "None" if m is None else "%+.6f" % m,
                 "" if rel is None else "%+.6f" % rel))
    ok = all(x["holds"] for x in ineq) and len(ineq) == 6
    print("  six: %d/%d hold  ->  %s\n"
          % (sum(1 for x in ineq if x["holds"]), len(ineq), "PASS" if ok else "FAIL"))
    return ok, ineq


def run():
    import json
    rec, files = load()
    print("read %d panel_ot cache files, %d (venue, symbol) pairs\n"
          % (len(files), len(rec)))

    d_var, d_fix = {}, {}
    per_ot = collections.defaultdict(dict)
    ots = collections.Counter()
    for (c, sym), r in rec.items():
        if len(r["grp"]) != 1:
            continue
        g = next(iter(r["grp"]))
        if g not in GROUPS:
            continue
        mix = pre_mix(r["pre"])
        for tgt, fixed in ((d_var, None), (d_fix, mix)):
            a, b = series(r["pre"], fixed), series(r["post"], fixed)
            if len(a) >= MIN_DAYS and len(b) >= MIN_DAYS:
                tgt.setdefault((c, g), []).append(median(b) - median(a))
        for ot in mix:
            ots[ot] += mix[ot]
            ca = {k: v for k, v in r["pre"].items() if k[1] == ot}
            cb = {k: v for k, v in r["post"].items() if k[1] == ot}
            a, b = series(ca), series(cb)
            if len(a) >= MIN_DAYS and len(b) >= MIN_DAYS:
                per_ot[ot].setdefault((c, g), []).append(median(b) - median(a))

    res = {"stage": "B14", "window": [PRE[0], POST[1]], "criteria": []}
    ok_v, iv = gate(d_var, "control: that day's own weights "
                    "(must reproduce the registered primary convention)")
    ok_f, ifx = gate(d_fix, "T1-a fixed composition: weights locked to the "
                    "symbol's own pre-window order-type shares")
    res["criteria"].append({
        "name": "B14-0/T1a  the gate survives holding the order-type mix fixed",
        "passed": bool(ok_f),
        "detail": "; ".join("%s/%s %+.6f" % (x["ctr"], x["grp"], x["margin"])
                            for x in ifx),
    })

    print("T1-b, one run per order type, by descending pre-window share\n")
    tot = sum(ots.values()) or 1
    for ot, mass in sorted(ots.items(), key=lambda kv: -kv[1]):
        share = mass / tot
        if share < 0.01:
            continue
        ok, ii = gate(per_ot[ot],
                      "Order_Type %s (pre-window share weight %.4f)" % (ot, share))
        res["criteria"].append({
            "name": "B14-0/T1b  order type %s alone, share %.4f" % (ot, share),
            "passed": bool(ok),
            "diagnostic": True,
            "detail": "; ".join(
                "%s/%s %s" % (x["ctr"], x["grp"],
                              "-" if x["margin"] is None else "%+.6f" % x["margin"])
                for x in ii),
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    cell = {("20160801", "10"): (0.05 * 100, 100.0),
            ("20160801", "11"): (0.01 * 300, 300.0)}
    chk("that day's own weights reproduce the primary convention 0.02",
        abs(math.exp(series(cell)[0]) - 0.02) < 1e-12)
    chk("fixed 50/50 weights give 0.03",
        abs(math.exp(series(cell, {"10": 1.0, "11": 1.0})[0]) - 0.03) < 1e-12)
    chk("when the pre-window share equals the day's own weight, fixed and free "
        "agree",
        abs(series(cell, pre_mix(cell))[0] - series(cell)[0]) < 1e-12)
    chk("an order type absent from the fixed weights is dropped",
        abs(math.exp(series(cell, {"10": 1.0})[0]) - 0.05) < 1e-12)
    chk("pre_mix accumulates by shares",
        pre_mix(cell) == {"10": 100.0, "11": 300.0})
    chk("the windows match design file section 3, D3-6",
        PRE == ("20160801", "20160930") and POST == ("20161101", "20161231"))
    chk("the column numbers point at WA_BBO_Spd and Order_Shares_Ct",
        C_BBO == 43 and C_SHARES == 16 and C_OT == 5)
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.build:
        names = [a.only] if a.only else sorted(
            f for f in os.listdir(RAW)
            if re.match(r".+_MKTQUALITYSTATS_\d{6}\.gzip$", f))
        for fn in names:
            build_one(fn)
        return 0
    if a.run:
        return run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
