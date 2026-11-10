"""B147: the six files of the first round, read again by the current reading script, against a record on disk.

Every number the first round wrote for those six files must come back the same (the keys the
continuation added, the payment-limit reading, the header check, the D22 bound and the reading with
one-dollar gross rows left out, are left out of the comparison).
Prints each difference; exits non-zero when there is one.

    python experiments/b147_regress_six.py results/b147_payer_item_square.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b147_parse as bp  # noqa: E402
import b147_payer_item_square as sq  # noqa: E402

SIX = ["garfield", "mh_tmc", "ohsu", "deaconess", "cvmc", "cheshire"]
ADDED = {"asp", "header_check", "d22", "rows_with_gross_at_most_one_dollar_left_out"}


def diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in ADDED:
                continue
            if k not in a or k not in b:
                out.append(path + "/" + str(k) + " present on one side only")
                continue
            diff(a[k], b[k], path + "/" + str(k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(path + " length %d vs %d" % (len(a), len(b)))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, path + "[%d]" % i, out)
    elif a != b:
        out.append(path + ": %r vs %r" % (a, b))


def main() -> int:
    old = json.loads((sq.REPO / sys.argv[1]).read_text(encoding="utf-8"))
    tables = sq.load_asp_tables()
    out = []
    for hid in SIX:
        h = bp.load(hid)
        cen = bp.census(h)
        rep = sq.read_hospital(h, asp_tables=tables, default_q=sq.DEFAULT_QUARTER[hid])
        new = json.loads(json.dumps({"report": rep, "census": cen}, sort_keys=True, ensure_ascii=False, default=str))
        n0 = len(out)
        diff(old["report"][hid], new["report"], "report/" + hid, out)
        diff(old["census"][hid], new["census"], "census/" + hid, out)
        print("%-10s %s" % (hid, "every number the same" if len(out) == n0 else "%d differences" % (len(out) - n0)),
              flush=True)
        del h
    g_old = old.get("garfield_check")
    h = bp.load("garfield")
    diff(g_old, json.loads(json.dumps(sq.garfield_check(h))), "garfield_check", out)
    diff(old["synthetic"], json.loads(json.dumps({"clean": sq.synthetic(False), "perturbed": sq.synthetic(True)})),
         "synthetic", out)
    for line in out[:40]:
        print("  " + line)
    print("differences: %d" % len(out))
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
