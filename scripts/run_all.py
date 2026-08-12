#!/usr/bin/env python3
"""Run everything and print a digest short enough to paste.

Usage::

    python scripts/run_all.py              # lint, tests, every experiment
    python scripts/run_all.py --quick      # lint and tests only
    python scripts/run_all.py --b2         # include B2, which needs fetched data

Each experiment already prints its own criteria in full. This runs them with
output suppressed and reports only the pass counts, the exit codes, and any
criterion that failed, so the result of a full verification is a dozen lines
rather than two hundred.

Written because the expensive part of this workflow is not computation but the
volume of text that has to be read afterwards.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

EXPERIMENTS = [
    (
        "A0   retention and allocation",
        "experiments/a0_retention.py",
        "a0_retention.json",
    ),
    ("A0b  derived demand", "experiments/a0_derived_wages.py", "a0_derived_wages.json"),
    (
        "A2   support contraction",
        "experiments/a2_support_contraction.py",
        "a2_support_contraction.json",
    ),
    (
        "A2c  cycle structure",
        "experiments/a2c_cycle_structure.py",
        "a2c_cycle_structure.json",
    ),
]
#: Stages needing the retrieved HMDA sample, run only under ``--b2``. B1 is here
#: rather than above because its seventh criterion checks Theorem 3 against the
#: real cells; ``--no-data`` runs its other six without any download.
DATA_STAGES = [
    ("B2A  effective price loop A", "experiments/b2_loop_a.py", "b2_loop_a.json"),
    (
        "B2A  graded placebo FHA/VA",
        "experiments/b2_placebo_products.py",
        "b2_placebo_products.json",
    ),
    ("B1   enlarged graph", "experiments/b1_theorem.py", "b1_theorem.json"),
    ("B2B  vintage separation", "experiments/b2_loop_b.py", "b2_loop_b.json"),
    # Needs the retrieved Ámbito and BCRA archives, so it belongs here rather
    # than with the synthetic stages. Its two criteria gate everything else in
    # B5: `b5_orphan_prereg.md` §8 says no headline without a calibration.
    (
        "B5   zero calibration",
        "experiments/b5_zero_calibration.py",
        "b5_zero_calibration.json",
    ),
    # Must run after the calibration: it reads that stage's result file for its
    # noise floor and refuses to start if the arm did not pass, which is
    # `b5_orphan_prereg.md` §8 expressed as an import rather than as a note.
    ("B5   squares", "experiments/b5_squares.py", "b5_squares.json"),
    # Must run after the squares: B5-14's denominator is B5-8's collapse and it
    # reads that record rather than recomputing it, refusing to start if B5-8
    # did not pass. `b5_orphan_prereg.md` §6A.6, the same gate shape again.
    (
        "B5   pre-window guards",
        "experiments/b5_parallel_trends.py",
        "b5_parallel_trends.json",
    ),
]

#: B1 without its real-data criterion, so a checkout with no download still
#: verifies the theorems.
B1_SYNTHETIC = (
    "B1   enlarged graph (synthetic)",
    "experiments/b1_theorem.py --no-data",
    "b1_theorem.json",
)


def run(cmd: list[str]) -> tuple[int, str]:
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, f"{time.time() - started:.1f}s"


def criteria_from(path: Path) -> tuple[int, int, list[str]]:
    """Pass count, total, and the names of any that failed."""
    if not path.exists():
        return 0, 0, ["no result file"]
    record = json.loads(path.read_text())
    blocks = []
    if "criteria" in record:
        blocks.append(record["criteria"])
    else:
        blocks.extend(
            v["criteria"]
            for v in record.values()
            if isinstance(v, dict) and "criteria" in v
        )
    passed = sum(c["passed"] for b in blocks for c in b)
    total = sum(len(b) for b in blocks)
    failed = [c["name"] for b in blocks for c in b if not c["passed"]]
    return passed, total, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="lint and tests only")
    ap.add_argument("--b2", action="store_true", help="include B2, needs fetched data")
    args = ap.parse_args()

    lines: list[str] = []
    ok = True

    code, secs = run([sys.executable, "-m", "ruff", "check", "."])
    lines.append(f"  lint     {'clean' if code == 0 else 'FAILED'}   {secs}")
    ok &= code == 0

    code, secs = run([sys.executable, "-m", "pytest", "-q"])
    lines.append(f"  tests    {'pass' if code == 0 else 'FAILED'}    {secs}")
    ok &= code == 0

    if not args.quick:
        jobs = list(EXPERIMENTS) + (DATA_STAGES if args.b2 else [B1_SYNTHETIC])
        total_p = total_n = 0
        for label, script, result_file in jobs:
            code, secs = run([sys.executable, *script.split()])
            p, n, failed = criteria_from(RESULTS / result_file)
            total_p += p
            total_n += n
            mark = f"{p}/{n}" if n else "no result"
            lines.append(f"  {label:<32} {mark:>8}   exit {code}   {secs}")
            for name in failed:
                lines.append(f"       FAILED: {name}")
            ok &= code == 0
        lines.append(f"  {'TOTAL':<32} {f'{total_p}/{total_n}':>8}")

    print("\n".join(lines))
    print(f"\n  {'ALL GREEN' if ok else 'SOMETHING FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
