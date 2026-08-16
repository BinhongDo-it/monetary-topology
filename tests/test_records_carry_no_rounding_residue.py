"""A regenerated record must not print a reduction's rounding residue.

`CLAUDE.md`'s rule 5 for files under `git diff --exit-code` says to fix the
float formatting so that a difference in the last digit between BLAS builds
does not surface as a text diff. This file is that rule as a guard for the one
class it keeps being violated by: **a quantity the theory says is exactly zero,
written out as whatever the arithmetic left behind.**

`2.220446049250313e-16` is not a measurement of anything. It is `2^-52`, and a
record carrying it says the identity held, in a form that changes with SIMD
width, thread count and BLAS backend on one pinned version of numpy. Pinning
the dependency does not reach it: pinning fixes which library runs, and this
digit is decided by the order a reduction happened to accumulate in.

**The fix, and it is what `results/a3_asset_channel.json` and
`results/a3c_load_bearing.json` already did on 2026-08-16**: write the bound
instead of the residue.

    "largest holonomy shift under unrelated prices 4.44e-16"
    "the largest holonomy shift under unrelated prices is at machine
     precision, below `1e-10`"

The second says everything the first said and says it the same way on every
machine.

Scope
-----
**Records some job in `scripts/run_all.py` regenerates**, taken from the runner
itself rather than listed here. A record nothing re-runs is never compared
against a fresh one, so it cannot turn a byte-diff red; the exposure begins the
day the stage gets a job, and scoping this way means the guard picks that up on
its own instead of waiting for somebody to remember.

What counts as a residue
------------------------
A mantissa **with more than one significant digit** at an exponent of `-12` or
smaller. `1e-16` is a registered tolerance and passes; `2.220446049250313e-16`
is a residue and does not.

**The line is drawn where it is because of what a tighter one would cost.** A
single-digit mantissa like `4e-16` may well be a rounded residue that still
flips between builds, and this guard lets it through, because catching it would
also flag every `1e-10` and `5e-13` a criterion registers as its own tolerance
and the allowlist would become the whole repository. The residues that actually
turn CI red are full-precision, and those are what this catches.

Ratchet, not a clean sheet
--------------------------
Six records are outside today and `KNOWN_RESIDUES` names each with the JSON keys
the residue sits under, because a count nobody can see is not an exposure
anybody will fix. Checked in both directions, the same discipline
`test_runner_covers_every_record.py` applies: an entry that has been cleaned
fails as loudly as a new offender, so the list cannot outlive its reasons.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
_RUNNER = ROOT / "scripts" / "run_all.py"

#: A mantissa carrying more than one significant digit at 1e-12 or below. The
#: decimal point is the test: a number the code chose is round, and a number the
#: arithmetic produced is not.
RESIDUE = re.compile(r"\d\.\d+[eE]-(?:1[2-9]|[2-9]\d|\d{3,})")

#: Records with a runner job that still print full-precision residues, with
#: where each one sits. Every entry here is a quantity the stage's own theory
#: says is zero, which is why the fix is a bound and never a rounder repr.
KNOWN_RESIDUES: dict[str, str] = {
    "a0_derived_wages.json": (
        "18, under `dfa.sweeps.level_by_elasticity`, `.level_by_floor`, the "
        "same two on `source`, and inside `criteria[].detail`. A level that "
        "has collapsed to zero at one end of a sweep, printed as what is left "
        "of it; one pair is `1.0238861633133766e-85` beside its own rounded "
        "`1.024e-85`, so the writer already rounds in one place and not the "
        "other"
    ),
    "a2_support_contraction.json": (
        "9, under `autonomous_edges.wage_funding_ratio`, `.household_inflow`, "
        "`intermediate.three_layer_funding_ratio_tail` and "
        "`.three_layer_level_at_zero_elasticity`. Same shape: a level at zero "
        "elasticity is zero, and the residue is the sweep's arithmetic"
    ),
    "a6_ratchet.json": (
        "8, under `fixed_point.rows[].relative_error` and "
        "`lambda_curve.cells.*.final_leak_factor`. A relative error at a "
        "converged fixed point, which is a convergence residue and not a "
        "reading of the economy"
    ),
    "b1_theorem.json": (
        "2, under `theorem_3_on_real_data.aggregate_relative_error` and "
        "`.worst_relative_error_per_cell`. Theorem 3 holding exactly, written "
        "as how exactly"
    ),
    "b5_squares.json": (
        "2, under `B5-1.worst_friction_discrepancy` and "
        "`.worst_index_discrepancy`. Two identities holding, one of them at "
        "`8.881784197001252e-16`, which is `4 * 2^-52`"
    ),
    "b6_segments.json": (
        "3, under `B6-1.worst_friction_discrepancy`, `.worst_index_discrepancy` "
        "and `B6-5.worst_cross_segment_spread`. Same as B5's, and "
        "`2.220446049250313e-16` is machine epsilon itself"
    ),
}


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runner_jobs() -> set[str]:
    """Every result file some job in `run_all.py` regenerates."""
    runner = _load(_RUNNER)
    jobs = [
        *runner.EXPERIMENTS,
        *runner.SLOW_STAGES,
        *runner.DATA_STAGES,
        runner.B1_SYNTHETIC,
    ]
    return {result_file for _, _, result_file in jobs}


def residues() -> dict[str, int]:
    """Regenerated records carrying a residue, and how many each carries."""
    out: dict[str, int] = {}
    for name in sorted(runner_jobs()):
        path = RESULTS / name
        if not path.exists():
            continue
        hits = RESIDUE.findall(path.read_text(encoding="utf-8"))
        if hits:
            out[name] = len(hits)
    return out


def test_no_regenerated_record_carries_a_new_residue() -> None:
    found = residues()
    new = sorted(set(found) - set(KNOWN_RESIDUES))
    assert not new, (
        "these records have a runner job and print a full-precision residue, "
        "so a different BLAS build regenerates them into a different file: "
        + ", ".join(f"{n} ({found[n]})" for n in new)
        + ". Write the bound rather than the digits, the way "
        "results/a3_asset_channel.json does: 'at machine precision, below "
        "`1e-10`'. If the value is a registered tolerance rather than a "
        "residue, add it to KNOWN_RESIDUES with that reason."
    )


def test_the_allowlist_has_no_stale_entry() -> None:
    """Both directions, so a cleaned record does not keep its exemption."""
    found = residues()
    cleaned = sorted(set(KNOWN_RESIDUES) - set(found))
    assert not cleaned, (
        "listed as carrying a residue and no longer does, so the entry is "
        "stale and should come out of KNOWN_RESIDUES: " + ", ".join(cleaned)
    )


def test_the_exposure_is_counted() -> None:
    """The number is asserted so that it can only move deliberately.

    Not a threshold and not a target. It is the count as of 2026-08-16, six
    records and forty-two occurrences, written down so that a change shows up
    as an edit to this line.
    """
    found = residues()
    assert len(KNOWN_RESIDUES) == 6
    assert sum(found.values()) == 42, found


# ---------------------------------------------------------------------------
# The detector itself. MEASUREMENT.md checklist item 8: would this guard say
# the same thing if the thing it guards were broken?
# ---------------------------------------------------------------------------
def test_a_registered_tolerance_is_not_a_residue() -> None:
    """The false positive that would make the allowlist the whole repository."""
    for tolerance in ("1e-10", "1e-12", "5e-13", "1e-16", "-1e-15"):
        assert not RESIDUE.search(tolerance), tolerance


def test_machine_epsilon_and_its_multiples_are_residues() -> None:
    for residue in ("2.220446049250313e-16", "8.881784197001252e-16",
                    "4.44e-16", "1.44e-15", "1.0238861633133766e-85"):
        assert RESIDUE.search(residue), residue


def test_an_ordinary_small_number_is_not_a_residue() -> None:
    """The exponent floor, so a real reading near 1e-11 is left alone."""
    for ordinary in ("1.234e-9", "9.87654321e-11", "0.05", "3.14e-3"):
        assert not RESIDUE.search(ordinary), ordinary


def test_a_residue_inside_a_detail_string_is_caught() -> None:
    """Where three of the six actually sit. Reading the file as text rather
    than as parsed floats is what makes those visible at all."""
    assert RESIDUE.search('"detail": "Mean-cost drift 1.86e-16."')
    assert not RESIDUE.search(
        '"detail": "Mean-cost drift at machine precision, below `1e-10`."'
    )
