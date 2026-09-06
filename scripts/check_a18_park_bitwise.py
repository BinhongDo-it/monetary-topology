"""Rule 19 for ``ParkSpec.return_rate``: the new field, left at its default,
must reproduce ``a18_park.json`` byte for byte.

The comparison is against ``results/_baseline/a18_park.json``, a copy taken
before the field existed. That directory is this repository's own place for a
rule 19 baseline and is already in ``.gitignore``; a fresh name would have
been a second convention for one job. Nothing is deleted and nothing is
overwritten by this script; it reads two files and prints whether they agree.

    python experiments/a18_policy_paths.py --park     # rewrites the record
    python scripts/check_a18_park_bitwise.py          # then this
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "results" / "a18_park.json"
BASE = ROOT / "results" / "_baseline" / "a18_park.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    for p in (LIVE, BASE):
        if not p.exists():
            print("missing: %s" % p)
            return 2
    a, b = _sha(LIVE), _sha(BASE)
    print("  live     %s  %d bytes" % (a, LIVE.stat().st_size))
    print("  baseline %s  %d bytes" % (b, BASE.stat().st_size))
    if a == b:
        print("\n  identical. rule 19 holds for ParkSpec.return_rate.")
        return 0

    # Not identical: say where, rather than only that. **The first differing
    # row is worth more than the fact of a difference.**
    la = json.loads(LIVE.read_text(encoding="utf-8"))
    lb = json.loads(BASE.read_text(encoding="utf-8"))
    ka, kb = set(la), set(lb)
    if ka != kb:
        print("\n  top-level keys differ: only live %s | only baseline %s"
              % (sorted(ka - kb), sorted(kb - ka)))
    ra, rb = la.get("runs", []), lb.get("runs", [])
    print("\n  rows: live %d, baseline %d" % (len(ra), len(rb)))
    shown = 0
    for i, (x, y) in enumerate(zip(ra, rb)):
        if x != y:
            diff = {k: (x.get(k), y.get(k)) for k in set(x) | set(y)
                    if x.get(k) != y.get(k)}
            print("  row %d differs: %s" % (i, diff))
            shown += 1
            if shown >= 5:
                print("  ... stopping after five")
                break
    if not shown:
        print("  every row agrees; the difference is outside runs[]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
