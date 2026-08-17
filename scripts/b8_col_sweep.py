#!/usr/bin/env python3
"""Mutation sweep over the B8 scripts' core-table column lists.

**Why this exists.** Pit 30 was hit four times in one day. Each time the shape
was identical: a script opens the core table with an explicit ``cols=`` list,
its selftest opens the fixture with **every** column, and so a column missing
from the run-path list is invisible until a real archive is read. The remedy in
each file was to hoist the list to a module constant and have the selftest use
it — but *that* remedy is itself unchecked, because a selftest can name the
constant and still never touch the column.

This sweep is the check. For every constant below it removes one entry at a
time and re-runs that script's selftest. **A selftest that still passes has not
covered that column**, and the reason is one of exactly two:

  * the selftest does not reach the code that reads it, which is a coverage
    gap and the file needs fixing; or
  * nothing in the file reads it at all, which is a **dead entry** in the list.

Both are worth knowing and the sweep does not try to tell them apart: it prints
the file and the column and leaves the reading to a person. The 2026-08-17 run
found one of each — ``b8_c10_4_tier_carrier`` opened its fixture with all
columns (gap), and once fixed, ``delinq`` and ``mod_flag`` turned out to be dead
entries in the same file.

**It mutates files in place and restores them.** It writes the original back in
a ``finally``, so an interrupt leaves the tree clean, but it is still a tool to
run on a clean checkout rather than over uncommitted work.

Usage::

    python scripts/b8_col_sweep.py
    python scripts/b8_col_sweep.py --only b8_loops.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1] / "experiments"

#: ``file -> (constants, selftest argv)``. A script that opens the core table
#: with an explicit list belongs here; one that takes every column does not,
#: because there is nothing to get wrong. ``b8_triangles`` is deliberately
#: absent for that reason.
#:
#: **A file may name more than one list.** ``b8_omega`` has two: ``PROBE_COLS``
#: for the coverage probe and ``V_COLS`` for ``rows_for_V``, which reads field
#: 19 and no delinquency at all. Merging them would make every entry look
#: load-bearing to this sweep and a dead entry would stop being detectable.
TARGETS = {
    "b8_loops.py": (["CENSUS_COLS"], ["selftest"]),
    "b8_omega.py": (["PROBE_COLS", "V_COLS"], ["selftest"]),
    "b8_c10_contract_move.py": (["COLS"], ["selftest"]),
    "b8_c10_4_tier_carrier.py": (["COLS"], ["selftest"]),
    "b8_c11_deferred_balance.py": (["COLS"], ["selftest"]),
    "b8_c12_impact.py": (["COLS"], ["selftest"]),
    "b8_0a_gate.py": (["GATE_COLS"], ["--selftest"]),
    "b8_c13_double_balance.py": (["COLS"], ["selftest"]),
}


def sweep(only: str | None = None) -> int:
    missed, total = [], 0
    for fn, (consts, argv) in TARGETS.items():
        if only and fn != only:
            continue
        path = EXP / fn
        orig = path.read_text(encoding="utf-8")
        for const in consts:
            m = re.search(rf"^{const} = \[(.*?)\]", orig, re.M | re.S)
            if not m:
                print(f"{fn}: constant {const} not found", file=sys.stderr)
                return 2
            items = [x.strip() for x in m.group(1).replace("\n", " ").split(",")
                     if x.strip()]
            try:
                for k in range(len(items)):
                    total += 1
                    kept = items[:k] + items[k + 1:]
                    path.write_text(
                        orig[:m.start()] + f"{const} = ["
                        + ", ".join(kept) + "]" + orig[m.end():],
                        encoding="utf-8")
                    r = subprocess.run([sys.executable, str(path)] + argv,
                                       capture_output=True)
                    if r.returncode == 0:
                        missed.append((fn, const, items[k]))
                        print(f"  MISSED  {fn}  {const}  dropping {items[k]}",
                              file=sys.stderr)
            finally:
                path.write_text(orig, encoding="utf-8")
    n_lists = sum(len(v[0]) for k, v in TARGETS.items()
                  if not only or k == only)
    print(f"\n{total} columns across {n_lists} list(s) in "
          f"{1 if only else len(TARGETS)} script(s), {len(missed)} missed",
          file=sys.stderr)
    if missed:
        print("\nEach line above is either a selftest that does not reach the "
              "column, or a dead entry in the list. **Both need a person.**",
              file=sys.stderr)
    return 1 if missed else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only")
    raise SystemExit(sweep(ap.parse_args().only))


if __name__ == "__main__":
    main()
