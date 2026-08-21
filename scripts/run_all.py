#!/usr/bin/env python3
"""Run everything and print a digest short enough to paste.

Usage::

    python scripts/run_all.py              # lint, tests, every experiment
    python scripts/run_all.py --quick      # lint and tests only
    python scripts/run_all.py --b2         # include B2, which needs fetched data
    python scripts/run_all.py --skip-done  # read the records already on disk
    python scripts/run_all.py --only A4 B1 # these stages only

**`--skip-done` reads instead of running.** A stage whose record is already in
``results/`` is not re-run; its criteria are read off that record and appear in
the digest exactly as if it had been. The digest marks them, so a read is never
mistaken for a run. Without it this script re-derives, every time, results that
were derived once and written down, and the expensive part of that is not the
computation.

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
    # About ninety seconds, which is an order more than everything above it and
    # two orders less than `SLOW_STAGES`. It sits here because A4 is a stage
    # whose verdicts belong in the default digest, and because most of the cost
    # is A4-5's three alternative orderings, which are a criterion rather than a
    # robustness extra: a criterion evaluated only behind a flag is not
    # evaluated.
    (
        "A4   the causal primitive",
        "experiments/a4_causal_primitive.py --json",
        "a4_causal_primitive.json",
    ),
    # About fifteen seconds, and it was outside this list until 2026-08-15.
    #
    # **What being outside it cost.** A5 runs entirely on A3's machinery. The
    # commit that restated A3 added `rent_rate = 0.05` as a default-on
    # mechanism and carried A5's existing record forward without re-running the
    # stage, so `results/a5_reachability.json` described an economy in which
    # being outside the asset market costs nothing while the repository
    # described one in which it costs five percent of the low tier's price a
    # round. Record and code entered the repository in the same commit and
    # disagreed for four days across five further commits. Nothing caught it,
    # because the restatement preserved the opening construction: every
    # construction-time number in the file still reproduced bitwise, only the
    # ones that run rounds had moved, and a file half of whose numbers are
    # exactly right does not look like a wrong file. There was no guard to
    # fail, and no number looked wrong. It was found by re-running the stage on
    # unchanged code and comparing.
    #
    # `docs/MEASUREMENT.md` failure mode 9 is the general form and this entry
    # is its durable half: enumerating the dependent stages by hand every time
    # a shared default moves depends on somebody remembering to enumerate, and
    # running them does not.
    (
        "A5   the reachability threshold",
        "experiments/a5_reachability.py",
        "a5_reachability.json",
    ),
    # Belongs with the synthetic stages and not beside B1 proper: it retrieves
    # nothing, uses no seed, and every graph in it is constructed. It is here
    # because `b1_setup.md` section 5's puncture-versus-disconnection ruling is
    # the one claim in this repository that depends on the square complex, and
    # until this ran in CI the numbers that ruling quotes had no committed
    # source.
    (
        "B1H  the hole taxonomy",
        "experiments/b1_holes.py",
        "b1_holes.json",
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
    # Needs the retrieved elTOQUE series, so it belongs here for the same reason
    # B6-A does. It reads B6-A's own BCC archive as well, for the official leg
    # of B6-13 and B6-15, but it does not read B6-A's record and does not gate
    # on it: the two halves answer different questions and B6-B's own header
    # says what it may not conclude, which is anything about a positive cycle
    # through an edge that publishes one number.
    (
        "B6-B informal leg",
        "experiments/b6b_informal.py",
        "b6b_informal.json",
    ),
    # B15 is B6's control carrier and sits next to it for that reason. Its five
    # jobs need the retrieved BCB and dolarbluebolivia archives, so they belong
    # here rather than with the synthetic stages.
    #
    # **No job reads another's record**, so the order below is for reading and
    # not for correctness. It is the order the arms were registered in: typing
    # first because B15-3 and B15-4 gate arm III, then the zero calibration that
    # settles which published number the ceiling is measured against, then arm
    # III itself, then the customs edge, then arm IV.
    #
    # **B15-3 is VOID on the registered whole window and live after the break**,
    # so the structure job runs on the post-event segment and says so in its own
    # record. That is a reported degradation rather than a rerun on a segment
    # picked to make a criterion pass.
    (
        "B15  typing and the known-answer arm",
        "experiments/b15_typing.py",
        "b15_typing.json",
    ),
    (
        "B15  zero calibration: the published TCO against the statute",
        "experiments/b15_zero.py",
        "b15_zero.json",
    ),
    (
        "B15  posted return leg and friction, post-event segment",
        "experiments/b15_structure.py",
        "b15_structure.json",
    ),
    (
        "B15  the customs edge",
        "experiments/b15_customs.py",
        "b15_customs.json",
    ),
    (
        "B15  the event and cross-publisher zero calibration",
        "experiments/b15_calibration.py",
        "b15_calibration.json",
    ),
    # A1 and A1b need retrieved files, so they belong here rather than with the
    # synthetic stages: A1 reads the HHDC workbook, the DFA archive, the Z.1
    # series, the SCF extract and the CEX table; A1b reads the SCF extract and
    # the CEX basket. Both are added the moment they first wrote a record,
    # rather than after somebody noticed, which is what
    # `tests/test_runner_covers_every_record.py` exists to force.
    #
    # **Neither is a complete stage yet.** Both records carry `complete: false`
    # and name the criteria not yet written. They are in the runner anyway,
    # because a record that renders has to be reproducible whatever else is true
    # of it, and because a stage added to the runner only once it is finished is
    # a stage nobody re-runs while it is being written.
    (
        "A1   the default cascade",
        "experiments/a1_default_cascade.py",
        "a1_default_cascade.json",
    ),
    # Cost unmeasured: it needs `data/processed/cex_necessities_by_decile.csv`,
    # which arrives with the next `data/fetch_cex.py` run. If it turns out to
    # belong in SLOW_STAGES, it moves there with the timing in the comment
    # rather than silently.
    (
        "A1b  the cascade on a measured population",
        "experiments/a1b_default_cascade.py",
        "a1b_default_cascade.json",
    ),
    # `docs/a1c_prereg.md` §5 says the job arrives with the first record rather
    # than afterwards, which is this file's own rule read forwards instead of
    # backwards.
    (
        "A1c  the order inside a household",
        "experiments/a1c_household_order.py",
        "a1c_household_order.json",
    ),
    # `docs/a1d_prereg.md` §9, same rule. This one is the heaviest of the four:
    # its sweep runs at 50,000 rather than 20,000, and the size is forced by §5's
    # model-side resolution floor rather than chosen. If it turns out to belong
    # in SLOW_STAGES it moves there with a timing in the comment.
    (
        "A1d  the cascade on a measured cushion",
        "experiments/a1d_measured_cushion.py",
        "a1d_measured_cushion.json",
    ),
    # Needs the processed loan-performance core, which is built locally and is
    # not in the repository, so it sits here with the other stages whose input
    # has to be on the machine already. It is not slow: the expensive step is
    # one pass of row residuals per vintage and the enumeration itself runs on
    # 934 distinct reduced words rather than on the loans.
    (
        "B12  grid invariance: every cut of the delinquency ladder",
        "experiments/b12_pullback.py --ladder",
        "b12_ladder.json",
    ),
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
#:
#: **Semantics narrowed 2026-08-16.** Membership means *adjudicated not to be
#: repaired*, and no longer merely *registered as failing*. The project-wide ban
#: on repairing a failed criterion was lifted on that date: a criterion whose
#: design is wrong may be rewritten, provided the stage is re-run and both
#: numbers are kept, and provided the criterion and the retrieval convention do
#: not move in the same commit. What this list holds is the other kind, the
#: failures that were looked at and left alone on purpose. Each entry's string
#: says which one it is, so adding an entry now requires stating the reason it
#: is not being repaired rather than the reason it fails.
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
    "A4-3 no competitor is a strawman": (
        "all four competitors fail the 0.02 floor on the C=0 arm, the largest "
        "being education at +0.00932. The floor is in absolute Gini units "
        "against a C=0 control that sits at 0.00711, so it asks each "
        "competitor for 2.8 times the control's whole value; education clears "
        "35.6 control-cell sd and still misses it. The threshold is registered "
        "and is not moved on that account, and MechanismParams keeps every "
        "value, including the claim in its own docstring that they were set to "
        "clear this floor, which stands as falsified rather than repaired. "
        "docs/a4_causal_primitive.md 11.2, 11.7"
    ),
    # A5's four, registered failing in docs/a5_reachability.md 8.1, which says
    # of the first two in its own words that they "fail in a way that is a
    # result rather than a defect". None is repaired and no threshold moves.
    "A5-1  participation falls with reachability": (
        "entry participation is not monotone in reachability: it rises from "
        "22.2% at rho=0.25 to 29.6% at rho=1.0 before collapsing. At the "
        "cheapest prices the whole stock sells at the opening and it sells to "
        "the richest, because no cap limits how much one node may hold, so "
        "making the asset cheaper does not put it in ordinary hands. "
        "max_units therefore interacts with rho and the two cannot be swept "
        "independently; that is an open defect in the design, registered as a "
        "diagnostic probe rather than repaired. "
        "docs/a5_reachability.md 8.1, 8.5"
    ),
    "A5-2  the threshold sits where the definition puts it": (
        "the threshold is not at the definitional point: 26.2% at rho=0.5 "
        "against a floor of 50%. Section 5's registered consequence is that "
        "it is reported at the location it is actually at, which is what 8.1 "
        "does. Same open defect as A5-1. docs/a5_reachability.md 8.1"
    ),
    "A5-3  the sign of the production layer's trend flips": (
        "no sign flip: the production layer's share falls at both ends of the "
        "grid. Section 5's registered consequence applies in full, and 8.1 "
        "withdraws section 1's claim that the source's retention tilting "
        "point transfers to the price. docs/a5_reachability.md 8.1"
    ),
    "A5-6  freeze the price and the drift disappears": (
        "**this failure is the stage's finding.** Reachability has a "
        "numerator and a denominator and the registered criterion named only "
        "the numerator: with the price frozen exactly, rho still moves, "
        "because the median production-layer agent's claims fall out from "
        "under it. The zero calibration did what a zero calibration is for. "
        "A5-7 and A5-8 are registered forward to score what it caught, and "
        "this criterion is not backfilled. docs/a5_reachability.md 8.1, 8.4"
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
    """Run one child, time it, and say why it failed if it did.

    **The encoding is explicit, and it is not a style preference.** ``text=True``
    alone decodes with ``locale.getpreferredencoding()``, which on a Chinese
    Windows install is GBK. ``ruff`` renders its diagnostics with box-drawing
    characters, so the first byte of a ``U+2500`` is ``0x80`` in UTF-8 and the
    reader thread dies with ``UnicodeDecodeError`` before ``run`` ever returns.
    **The bug only fires when there is something to report**: a clean ruff prints
    ``All checks passed!``, which is ASCII, so this harness looked correct for as
    long as it had nothing to say. Observed 2026-08-18.

    **The output goes to stderr on failure only.** The digest this file prints is
    meant to be pasted whole, and ``announce`` above already establishes stderr
    as the channel for anything that must not disturb it, so redirecting stdout
    still gives exactly what it gave before, to the byte. Before this, a failing
    lint printed ``FAILED`` and the name of no rule, so the next step was always
    to run the same command again by hand.
    """
    started = time.time()
    proc = subprocess.run(
        cmd, capture_output=True, text=True, cwd=ROOT,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        detail = (proc.stdout or "") + (proc.stderr or "")
        if detail.strip():
            print(f"  --- {' '.join(cmd[-3:])} said:", file=sys.stderr)
            for line in detail.rstrip().splitlines():
                print(f"  {line}", file=sys.stderr)
            print("  ---", file=sys.stderr, flush=True)
    return proc.returncode, f"{time.time() - started:.1f}s"


def criteria_from(path: Path) -> tuple[int, int, list[str], list[str]]:
    """Pass count, total, the names that failed, and every name seen.

    The fourth element exists so that a criterion on ``EXPECTED_FAILURES``
    which has started passing can be told apart from one that was not run at
    all. Those are different events and only one of them is a finding.

    **Voids and diagnostics are excluded from all four, corrected 2026-08-13.**
    A criterion the run could not evaluate is not a criterion the run failed,
    and one demoted to a diagnostic decides nothing by construction. Counting
    them here reported every void as an unexpected failure and put it in the
    denominator, so a stage with four live passes and two voids printed as
    ``4/6`` with two ``FAILED:`` lines under it. `render_results.py`'s
    ``mark_of`` and ``render_block`` already draw exactly this distinction and
    say so in their own docstrings; this file was the half that had not been
    brought over, so the digest and `RESULTS.md` disagreed about the same
    record. A3 and A6 both move as a result, in the direction of reporting
    fewer failures than before, and no verdict changes.
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
    live = [
        c
        for b in blocks
        for c in b
        if not (c.get("void") or c.get("diagnostic"))
    ]
    passed = sum(c["passed"] for c in live)
    failed = [c["name"] for c in live if not c["passed"]]
    seen = [c["name"] for c in live]
    return passed, len(live), failed, seen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="lint and tests only")
    ap.add_argument("--b2", action="store_true", help="include B2, needs fetched data")
    ap.add_argument(
        "--slow", action="store_true", help="include A6r, about fifteen minutes"
    )
    ap.add_argument(
        "--skip-done", action="store_true",
        help="do not re-run a stage whose record is already in results/; "
             "read that record instead"
    )
    ap.add_argument(
        "--only", nargs="+", metavar="NAME", default=None,
        help="run only the stages whose label starts with one of these"
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
        if args.only:
            want = tuple(args.only)
            dropped = [lb for lb, _, _ in jobs if not lb.startswith(want)]
            jobs = [j for j in jobs if j[0].startswith(want)]
            # Named, not silently dropped, for the reason every other skip in
            # this file is named.
            if dropped:
                print(f"  --only: not selected: "
                      f"{', '.join(d.split()[0] for d in dropped)}",
                      file=sys.stderr)
        total_p = total_n = 0
        n_expected = 0
        n_read = 0
        for label, script, result_file in jobs:
            record = RESULTS / result_file
            # **Read, not run.** The record on disk is the same object the run
            # would write, so the digest is the same digest; what changes is
            # that a result derived once is not derived again. A missing record
            # still runs, because there is nothing to read.
            reading = args.skip_done and record.exists()
            if reading:
                n_read += 1
                code, secs = 0, "read"
            else:
                announce(label)
                code, secs = run([sys.executable, *script.split()])
            p, n, failed, seen = criteria_from(record)
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
            how = "READ " if reading else f"exit {code}"
            lines.append(f"  {label:<32} {mark:>8}   {how}   {secs}")
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
            # A read has no exit code of its own, so the record's own criteria
            # are the whole of what it can say.
            ok &= reading or code == 0 or bool(failed)
        lines.append(
            f"  {'TOTAL':<32} {f'{total_p}/{total_n}':>8}"
            + (f"   {n_expected} expected failures" if n_expected else "")
        )
        if n_read:
            lines.append(
                f"  {n_read} stage(s) marked READ: their record was already on "
                f"disk and --skip-done was given, so they were not re-run"
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
