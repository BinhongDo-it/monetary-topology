# -*- coding: utf-8 -*-
"""Discipline 19 for the v2 dump: the new columns must not have moved the old ones.

v1 ch386 was a full pass over the capture and v1 ch382 stopped at 6,000,000
packets, which is what the `_6M` twin next to it records. So the invariant is
not equal length. It is:

    v1's four columns are a PREFIX of v2's first four columns, row for row.

A prefix is the right shape because the dump walks the capture in order and a
packet limit only truncates. If a group set or a book rule had changed, the
prefix would break at the first differing row and this prints where.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAIRS = (("two_classes_ch386_v3.tsv", "two_classes_ch386.tsv"),
         ("two_classes_ch382_v3.tsv", "two_classes_ch382.tsv"))


def rows(path, n=None):
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            out.append(line.rstrip("\n").split("\t"))
    return out


def main():
    ok = True
    for newn, oldn in PAIRS:
        a = os.path.join(ROOT, "data", "cache", "b13", newn)
        b = os.path.join(ROOT, "data", "cache", "b13", oldn)
        if not (os.path.exists(a) and os.path.exists(b)):
            print("%-28s missing" % newn)
            ok = False
            continue
        new = [r[:4] for r in rows(a)]
        old = rows(b)
        if len(new) < len(old):
            print("%-28s v2 %7d < v1 %7d, not a prefix" % (newn, len(new), len(old)))
            ok = False
            continue
        first = None
        for i, (x, y) in enumerate(zip(new, old)):
            if x != y:
                first = i
                break
        # the identity the two new columns must satisfy on every row
        bad = 0
        for r in rows(a):
            if int(r[2]) != -(int(r[4]) + int(r[5])):
                bad += 1
            if len(r) >= 8 and int(r[3]) != (2 * int(r[7]) + int(r[5])) - \
                    (2 * int(r[6]) + int(r[4])):
                bad += 1
        print("%-28s v2 %7d  v1 %7d  prefix %s  friction=-(s_e+s_d) 违反 %d"
              % (newn, len(new), len(old),
                 "identical" if first is None else "BREAKS at row %d" % first, bad))
        if first is not None:
            print("     v2 %s" % new[first])
            print("     v1 %s" % old[first])
        ok = ok and first is None and bad == 0
    print("")
    print("第 19 条：%s" % ("通过，新列没有动旧列" if ok else "未通过"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
