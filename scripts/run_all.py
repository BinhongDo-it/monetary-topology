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
    (
        "A6   the siphon in tax points",
        "experiments/a6_siphon_cost.py",
        "a6_siphon_cost.json",
    ),
]

#: Stages slow enough that putting them in the default run would change what
#: this script is for. ``a6_ratchet.py`` sweeps a lambda grid at two thousand
#: rounds, rescans the rate grid at two thousand, and runs six long-horizon
#: cells at sixty thousand with one carrying a registered multiple of three,
#: and since A6-20 to A6-23 it also runs a four-cell rebate factorial at twenty
#: thousand, a ratio scan whose horizon scales as 10/lambda, and a five-column
#: re-measurement of the curve. That is about twenty-five minutes on the
#: author's machine against seconds for everything above.
#:
#: **It prints nothing while it runs**, because every job here is run with its
#: output captured. `announce` exists so that silence is legible: a stage this
#: long is otherwise indistinguishable from a hang.
#:
#: **Skipping it is announced rather than silent.** A digest that omits a stage
#: without saying so reads as "everything passed", which is the kind of object
#: this repository exists to argue against.
SLOW_STAGES = [
    (
        "A6r  the ratchet and the levy base",
        "experiments/a6_ratchet.py",
        "a6_ratchet.json",
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
    # Needs the retrieved BCC archive, so it belongs here rather than with the
    # synthetic stages. It has no dependency on any other stage: every class it
    # reads comes from one publisher, which is what removes B5's reporter
    # confound and removes B5's zero calibration with it
    # (`b6_cuba_prereg.md` §4.3).
    ("B6-A segment typing", "experiments/b6_segments.py", "b6_segments.json"),
]

#: Criteria that are registered as failing and are expected to keep failing.
#: Each is a finding rather than a defect, so a digest that reports them as
#: breakage says the same thing every run and stops carrying information.
#:
#: **This list is checked in both directions.** An entry that fails is
#: expected and does not spoil the verdict. An entry that *passes* is reported
#: as loudly as an unexpected failure, because a criterion registered as
#: failing and then passing is a finding, and an allowlist that swallowed it
#: would be exactly the mechanism this file exists to avoid. Anything not on
#: the list that fails counts as breakage, as before.
EXPECTED_FAILURES = {
    "A6-1": (
        "scope defect visible on paper: it quantifies over all eight cells "
        "while A6-3 requires the flat four not to contract. Not rewritten "
        "after the fact. docs/a6_siphon_cost.md 9.2"
    ),
    "A6-5": (
        "a real negative result, and the one that generated A6-7 to A6-23. "
        "Diagnosed in docs/a6_siphon_cost.md 16, not repaired"
    ),
    "A6-10": (
        "R* is proportional to lambda in this arm, so it falls off any grid "
        "fixed in advance. Asking for it as a level is the wrong question. "
        "**The right question is now written and it passes**: A6-21 scans "
        "R = rho*lambda and finds R* = lambda at every lambda, which is why "
        "this criterion's grid reported the floor. A6-10 keeps its failure "
        "and is not repaired. docs/a6_siphon_cost.md 14.5, 19"
    ),
    "A6-11": (
        "the same split as A6-10, on the same two cells, and the same "
        "resolution: A6-21 asks the answerable form of it"
    ),
}

#: B1 without its real-data criterion, so a checkout with no download still
#: verifies the theorems.
B1_SYNTHETIC = (
    "B1   enlarged graph (synthetic)",
    "experiments/b1_theorem.py --no-data",
    "b1_theorem.json",
)


def announce(label: str) -> None:
    """Say what is starting, on **stderr**.

    The digest goes to stdout and is accumulated and printed once at the end,
    which is what makes it a dozen pasteable lines rather than two hundred. It
    also makes a long stage indistinguishable from a hang: nothing prints for
    the whole run, and ``a6_ratchet`` is both last and about twenty-five
    minutes. Somebody watching that terminal has no way to tell a working run
    from a stuck one, and the honest answer to "is it stuck" should not require
    reading this file.

    On stderr so the pasteable digest is unchanged to the byte: redirecting
    stdout still gives exactly what it gave before.
    """
    print(f"  ... {label}", file=sys.stderr, flush=True)


def run(cmd: list[str]) -> tuple[int, str]:
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return proc.returncode, f"{time.time() - started:.1f}s"


def criteria_from(path: Path) -> tuple[int, int, list[str], list[str]]:
    """Pass count, total, the names that failed, and every name seen.

    The fourth element exists so that a criterion on ``EXPECTED_FAILURES``
    which has started passing can be told apart from one that was not run at
    all. Those are different events and only one of them is a finding.
    """
    if not path.exists():
        return 0, 0, ["no result file"], []
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
    seen = [c["name"] for b in blocks for c in b]
    return passed, total, failed, seen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="lint and tests only")
    ap.add_argument("--b2", action="store_true", help="include B2, needs fetched data")
    ap.add_argument(
        "--slow", action="store_true", help="include A6r, about fifteen minutes"
    )
    args = ap.parse_args()

    lines: list[str] = []
    ok = True

    announce("lint")
    code, secs = run([sys.executable, "-m", "ruff", "check", "."])
    lines.append(f"  lint     {'clean' if code == 0 else 'FAILED'}   {secs}")
    ok &= code == 0

    announce("tests")
    code, secs = run([sys.executable, "-m", "pytest", "-q"])
    lines.append(f"  tests    {'pass' if code == 0 else 'FAILED'}    {secs}")
    ok &= code == 0

    if not args.quick:
        jobs = list(EXPERIMENTS) + (DATA_STAGES if args.b2 else [B1_SYNTHETIC])
        jobs += SLOW_STAGES if args.slow else []
        total_p = total_n = 0
        n_expected = 0
        for label, script, result_file in jobs:
            announce(label)
            code, secs = run([sys.executable, *script.split()])
            p, n, failed, seen = criteria_from(RESULTS / result_file)
            total_p += p
            total_n += n
            expected = [f for f in failed if f in EXPECTED_FAILURES]
            unexpected = [f for f in failed if f not in EXPECTED_FAILURES]
            # Registered as failing, present in this run, and it passed.
            surprises = [
                s for s in seen if s in EXPECTED_FAILURES and s not in failed
            ]
            n_expected += len(expected)
            mark = f"{p}/{n}" if n else "no result"
            lines.append(f"  {label:<32} {mark:>8}   exit {code}   {secs}")
            for name in unexpected:
                lines.append(f"       FAILED: {name}")
            for name in expected:
                lines.append(
                    f"       expected FAIL: {name} -- {EXPECTED_FAILURES[name]}"
                )
            for name in surprises:
                lines.append(
                    f"       ** {name} is registered as failing and it PASSED. "
                    f"That is a finding, not a fix: read it before touching "
                    f"anything"
                )
            # A non-zero exit is what an experiment returns when any criterion
            # fails, so it cannot be read on its own once some failures are
            # expected. It still matters when nothing failed, which is what a
            # crash before the result file was written looks like.
            ok &= not unexpected and not surprises
            ok &= code == 0 or bool(failed)
        lines.append(
            f"  {'TOTAL':<32} {f'{total_p}/{total_n}':>8}"
            + (f"   {n_expected} expected failures" if n_expected else "")
        )
        if not args.slow:
            names = ", ".join(label.split()[0] for label, _, _ in SLOW_STAGES)
            lines.append(f"  NOT RUN: {names}. Add --slow to include them")
        if not args.b2:
            lines.append(
                "  NOT RUN: the B2 and B5 and B6 data stages, and B1's "
                "real-data criterion. Add --b2 to include them"
            )

    print("\n".join(lines))
    print(f"\n  {'ALL GREEN' if ok else 'SOMETHING FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
