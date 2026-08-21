"""B14 stage one: collapse the Tick Pilot Appendix B.I monthly files into a
(date, venue, symbol) panel.

The conventions are fixed before the run in the design file, section 3. This
script executes them; it does not choose any of them.

  D3-2  spd = sum(w * WA_BBO_Spd) / sum(w),  w = Order_Shares_Ct
  D3-3  the same pass also computes the w = Order_Count variant
  D3-4  a cell is admitted only if spd is non-blank and > 0, and w > 0
  D3-5  no flag-based subsetting of any kind
  sec4  WA_NBBO_Spd gets the same treatment as a cross-check, excluded from the
        verdict

Usage
    python experiments/b14_tickpilot_panel.py --selftest
    python experiments/b14_tickpilot_panel.py --build            # everything on disk
    python experiments/b14_tickpilot_panel.py --build --only NYSE_MKTQUALITYSTATS_201612.gzip

Re-entrant: a target cache whose last line is #DONE is skipped. Bytes go to .part
and are renamed on completion, so an interrupted run never leaves half a table.
"""
import argparse
import gzip
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
CACHE = os.path.join(ROOT, "data", "cache", "b14")

# 0-based column numbers; see the field line quoted in design file section 1
C_DATE, C_CTR, C_SYM, C_GRP = 1, 2, 3, 4
C_ORDCNT, C_SHARES = 15, 16
C_NBBO, C_BBO = 42, 43
NFIELDS = 53

SCHEMA = "v2"   # v2 = v1 plus four columns (design file section 4 supplement 1,
                # the way T5 is adjudicated)
HEAD = ("date,ctr,symbol,test_group,"
        "bbo_shr_num,bbo_shr_den,bbo_cnt_num,bbo_cnt_den,"
        "nbbo_shr_num,nbbo_shr_den,"
        "rows,adm_bbo,blank_bbo,zero_bbo,"
        "zero_shr,zero_cnt,blank_shr,blank_cnt,neg_bbo")


def _num(s):
    """Blank and non-numeric return None; otherwise a float."""
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def accumulate(lines):
    """Take pipe-split field lists, return (date, ctr, sym, grp) -> accumulator."""
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
            a[9] += 1                              # zero (or negative: also not a spread)
            if bbo < 0:
                a[14] += 1                         # neg_bbo: crossed book, counted apart
            # The T5 adverse convention needs their true weights
            # (design file section 4 supplement 1)
            if shr is not None and shr > 0:
                a[10] += shr                       # zero_shr
            if cnt is not None and cnt > 0:
                a[11] += cnt                       # zero_cnt
        else:
            if shr is not None and shr > 0:
                a[0] += shr * bbo
                a[1] += shr
                a[7] += 1                          # adm_bbo, on the primary weight
            if cnt is not None and cnt > 0:
                a[2] += cnt * bbo
                a[3] += cnt
        if nbbo is not None and nbbo > 0 and shr is not None and shr > 0:
            a[4] += shr * nbbo
            a[5] += shr
    return acc, bad_width


def stream(path):
    """Decompress, keep only D rows, split the fields.

    Python's gzip and not an external zcat: zcat does not exist on Windows, which
    is where this repository runs, and the first version died there with WinError 2
    after the 2016 caches had already been built elsewhere through zcat. That makes
    the reader a place two rounds could silently diverge, so --verify-reader
    rebuilds a cached file through this reader and compares byte for byte against
    what zcat produced. Read in blocks rather than iterating lines, because per-line
    iteration over a GzipFile is several times slower on a gigabyte of input.
    """
    tail = b""
    with gzip.open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            rows = (tail + chunk).split(b"\n")
            tail = rows.pop()
            for raw in rows:
                if raw[:2] != b"D|":
                    continue
                yield raw.decode("latin-1").rstrip("\r\n").split("|")
    if tail[:2] == b"D|":
        yield tail.decode("latin-1").rstrip("\r\n").split("|")


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
        print("  skipped (filename not recognised):", fname)
        return
    if is_done(dst):
        print("  already cached, skipped:", os.path.basename(dst))
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
    print("  %-40s symbol-days %6d  rows %9d  admitted %.4f  blank %d  zero %d"
          "  bad width %d"
          % (fname, n, tot, (adm / tot if tot else 0.0), blk, zer, bad))


def verify_reader(names):
    """Project rules item 19: a reader swap must reproduce existing output, and the
    comparison must actually be run.

    Rebuilds each named source through the current reader into a .reread file and
    compares it byte for byte with the cache already on disk, which was produced by
    the zcat reader. Writes nothing over the cache and deletes nothing.
    """
    ok = True
    for fname in names:
        src = os.path.join(RAW, fname)
        dst = out_path(fname)
        if dst is None or not os.path.exists(src):
            print("  %-40s source not on disk, skipped" % fname)
            continue
        if not os.path.exists(dst):
            print("  %-40s no existing cache to compare against, skipped" % fname)
            continue
        acc, bad = accumulate(stream(src))
        re_path = dst + ".reread"
        n = 0
        with open(re_path, "w") as fh:
            fh.write(HEAD + "\n")
            for (d, c, sy, g) in sorted(acc):
                a = acc[(d, c, sy, g)]
                fh.write("%s,%s,%s,%s,%.6f,%.0f,%.6f,%.0f,%.6f,%.0f,"
                         "%d,%d,%d,%d,%.0f,%.0f,%.0f,%.0f,%d\n"
                         % (d, c, sy, g, a[0], a[1], a[2], a[3], a[4], a[5],
                            a[6], a[7], a[8], a[9],
                            a[10], a[11], a[12], a[13], a[14]))
                n += 1
            fh.write("#DONE schema=%s keys=%d bad_width=%d src=%s\n"
                     % (SCHEMA, n, bad, fname))
        old_b = open(dst, "rb").read()
        new_b = open(re_path, "rb").read()
        same = old_b == new_b
        ok = ok and same
        print("  %-40s %s  (%d keys, %d bytes)"
              % (fname,
                 "byte-identical to the zcat-built cache" if same
                 else "**DIFFERS from the zcat-built cache**", n, len(new_b)))
        if not same:
            a_lines, b_lines = old_b.split(b"\n"), new_b.split(b"\n")
            print("       cached %d lines, reread %d lines" % (len(a_lines), len(b_lines)))
            for i, (x, y) in enumerate(zip(a_lines, b_lines)):
                if x != y:
                    print("       first difference at line %d:" % (i + 1))
                    print("         cached: %r" % x[:160])
                    print("         reread: %r" % y[:160])
                    break
        print("       kept at %s" % os.path.relpath(re_path, ROOT))
    print("\n  " + ("reader reproduces the existing caches" if ok
                    else "**reader does not reproduce; do not build 2018 on it**"))
    return 0 if ok else 1


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
    chk("share weighting collapses 0.05@100 and 0.01@300 to 0.02",
        abs(v[0] / v[1] - 0.02) < 1e-12)
    chk("count weighting collapses the same two cells to 0.03",
        abs(v[2] / v[3] - 0.03) < 1e-12)
    chk("the two weighting conventions give different numbers, so running both "
        "is not redundant", abs(v[0] / v[1] - v[2] / v[3]) > 1e-9)

    z = list(row); z[C_BBO], z[C_SHARES], z[C_ORDCNT] = "0.0000", "999999", "9"
    e = list(row); e[C_BBO], e[C_SHARES], e[C_ORDCNT] = "", "999999", "9"
    acc2, _ = accumulate([a, b, z, e])
    v2 = acc2[("20161201", "N", "AAA", "G1")]
    chk("a zero spread does not enter the weighted mean",
        abs(v2[0] / v2[1] - 0.02) < 1e-12)
    chk("a blank spread does not enter the weighted mean",
        abs(v2[2] / v2[3] - 0.03) < 1e-12)
    chk("blanks and zeros are counted separately", v2[8] == 1 and v2[9] == 1)
    chk("rows counts all four rows", v2[6] == 4)
    chk("adm_bbo counts only the two admitted rows", v2[7] == 2)

    w = list(row); w[C_BBO], w[C_SHARES], w[C_ORDCNT] = "0.0500", "0", "0"
    acc3, _ = accumulate([a, w])
    v3 = acc3[("20161201", "N", "AAA", "G1")]
    chk("a zero-weight cell does not move the weighted mean",
        abs(v3[0] / v3[1] - 0.05) < 1e-12)

    acc5, _ = accumulate([a, b, z, e])
    v5 = acc5[("20161201", "N", "AAA", "G1")]
    chk("the share weight of a zero-spread row lands in zero_shr",
        abs(v5[10] - 999999) < 1e-9)
    chk("the share weight of a blank-spread row lands in blank_shr",
        abs(v5[12] - 999999) < 1e-9)
    chk("the adverse convention lowers spd: num/(den+zero_shr) < num/den",
        v5[0] / (v5[1] + v5[10]) < v5[0] / v5[1])
    neg = list(row); neg[C_BBO], neg[C_SHARES], neg[C_ORDCNT] = "-0.0100", "50", "1"
    acc6, _ = accumulate([a, neg])
    v6 = acc6[("20161201", "N", "AAA", "G1")]
    chk("a negative spread (crossed book) is counted apart and, like a zero, "
        "enters zero_shr",
        v6[14] == 1 and abs(v6[10] - 50) < 1e-9 and v6[9] == 1)
    chk("a negative spread does not enter the weighted mean",
        abs(v6[0] / v6[1] - 0.05) < 1e-12)

    short = ["D", "20161201", "N"]
    acc4, bad4 = accumulate([short])
    chk("a row with the wrong field count is counted and discarded",
        bad4 == 1 and not acc4)

    chk("column numbers match design file section 1 (field 44 = WA_BBO_Spd)",
        C_BBO == 43 and NFIELDS == 53)
    chk("the header column count matches what is written",
        len(HEAD.split(",")) == 19)

    import tempfile
    rowa = "D|20161201|N|AAA|G1|" + "|" * (NFIELDS - 6) + "x"
    body = ("H|4|BI|201612|20180425\n" + rowa + "\n" + rowa).encode("latin-1")
    tmp = os.path.join(tempfile.gettempdir(), "_b14_reader_probe.gz")
    with gzip.open(tmp, "wb") as fh:
        fh.write(body)
    got = list(stream(tmp))
    chk("the block reader drops the H row and keeps both D rows, including a "
        "final row with no trailing newline", len(got) == 2)
    chk("and splits them into the full field count",
        all(len(g) == NFIELDS for g in got))
    with gzip.open(tmp, "wb") as fh:
        fh.write(b"")
    chk("an empty member yields nothing rather than raising", list(stream(tmp)) == [])
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--only", nargs="*", default=None,
                    metavar="FILE", help="build only these sources")
    ap.add_argument("--verify-reader", nargs="*", default=None,
                    metavar="FILE",
                    help="rebuild cached months through the current reader and "
                         "compare byte for byte; defaults to one file per venue")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.verify_reader is not None:
        names = args.verify_reader or ["NYSE_MKTQUALITYSTATS_201612.gzip",
                                       "NYSEARCA_MKTQUALITYSTATS_201612.gzip"]
        print("reader reproduction check, %d file(s)" % len(names))
        return verify_reader(names)
    if not args.build:
        ap.print_help()
        return 2
    if args.only:
        names = list(args.only)
    else:
        names = sorted(f for f in os.listdir(RAW)
                       if re.match(r".+_MKTQUALITYSTATS_\d{6}\.gzip$", f))
    print("B14 panel build, %d files" % len(names))
    for fn in names:
        build_one(fn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
