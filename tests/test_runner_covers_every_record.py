"""Every record that reaches `RESULTS.md` must have a job in the runner.

`docs/MEASUREMENT.md` failure mode 9 records what happens when it does not.
Stage A5's stored record was produced before `rent_rate` existed, the commit
that added that mechanism carried the record forward without re-running the
stage, and record and code entered the repository together and disagreed for
four days. No guard failed, because there was none, and no number looked wrong,
because half of them still reproduced bitwise. The rule that came out of it is
that **a stage nothing re-runs does not have a record, it has a memory.**

This file is that rule as a guard rather than as a paragraph.

**The invariant is stated on the renderer's own selection.** `render_results.py`
globs `results/*.json`, drops the off-parameter and smoke runs by filename and
the writer-declared diagnostics by field, and turns every survivor into a
heading. That survivor set is exactly the set of records a reader sees, and it
is therefore exactly the set that has to be reproducible on demand. Asking the
question of experiment files instead would miss a record whose writer was
renamed and catch a diagnostic that prints and never writes.

**It is a ratchet, not a clean sheet.** Eight records are outside the runner
today, and `OUTSIDE_THE_RUNNER` names each of them with the reason it is there,
because a count nobody can see is not an exposure anybody will fix. The point of
the list is that the ninth cannot be added silently.

**Checked in both directions**, the same discipline `run_all.py` applies to
`EXPECTED_FAILURES`. An entry that is not a rendered record, or that has since
been given a runner job, fails as loudly as a new omission: an allowlist nobody
prunes stops being a list of exceptions and becomes a place things go to be
forgotten.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

#: Records that render into `RESULTS.md` and that no job in `run_all.py`
#: regenerates. Each reason says what is actually known, and "no reason found"
#: is written where that is the truth: three A-track stages are here because
#: nobody added them, not because anybody decided they cost too much.
OUTSIDE_THE_RUNNER: dict[str, str] = {
    "a7_verdicts.json": (
        "A7's verdict sheet. The stage's own measurements are six runs across "
        "two arms, two estimators and three round counts, about forty minutes, "
        "and every one of them is diagnostic_only because section 4.2's scored "
        "estimator runs under a flag rather than by default. This sheet is "
        "assembled from those records by `--verdicts` and exists so that a "
        "stage with eleven verdicts is not invisible in RESULTS.md. Adding a "
        "runner job is the close-out task and is deliberately not done while "
        "another line of work is editing run_all.py"
    ),
    "a3_asset_channel.json": (
        "A3 itself, the stage every A-track claim about compounding rests on, "
        "and the stage whose own restatement produced failure mode 9's "
        "instance. No reason found: it was never added. The registered sweep "
        "takes about four and a half minutes, which would put it between A4 "
        "and the slow stages rather than out of reach"
    ),
    "a3b_construction.json": (
        "A3b, the opening construction as a registered axis. No reason found"
    ),
    "a3c_load_bearing.json": (
        "A3c, the divergence instrument A3-8 is scored on. No reason found"
    ),
    "b7_crossfold.json": (
        "B7-16, the cross-fold second moment, pre-registered and run after the "
        "stage closed. Needs the fetched HMDA sample, so it belongs in "
        "DATA_STAGES. **Deliberately outside the runner for the same reason as "
        "the rest of B7**: the stage's headline is withdrawn and no runner path "
        "was rebuilt. That decision is now weaker than it was, because SS11 "
        "reads something the withdrawal does not cover, and it is left standing "
        "here so the next person weighs it rather than inherits it"
    ),
    "b7_crossfold_depth.json": (
        "B7-16's gate: entries holding two or more loans, class by class. Same "
        "reason as b7_crossfold.json. It estimates nothing and is the cheapest "
        "record in the stage, so it is the first thing worth wiring back in if "
        "a B7 runner path is ever rebuilt"
    ),
    "b7_design.json": (
        "B7's design audit and B7-9's share of stage B2's within term. Needs "
        "the fetched HMDA sample, so it belongs in DATA_STAGES. **B7 is closed "
        "and no B7 job was added**: the stage's reading was withdrawn "
        "(docs/b7_interaction_rank.md SS3.25 to SS3.29) and rebuilding a runner "
        "path for a withdrawn stage was judged not worth it. That is a "
        "decision, not an oversight, and it is recorded here as one"
    ),
    "b7_interaction_rank.json": (
        "B7-1, B7-2 and B7-3, the estimator's synthetic checks. Pure "
        "construction, no download, runs in minutes. Same decision as "
        "b7_design.json"
    ),
    "b7_gate_draws50_reps20.json": (
        "B7-0a/b/c on the fine class grid under SS3.15's rate criterion. Needs "
        "the fetched HMDA sample. Same decision"
    ),
    "b7_gate_coarse_draws50_reps20.json": (
        "the same three arms on the coarse grid. Same decision"
    ),
    "b7_carry.json": (
        "B7-11, what a coarsening can carry. **The one result in that stage "
        "that survived the withdrawal**, because it measures what a coarsening "
        "does to a direction and holds whether the direction is signal or "
        "noise. Cited by b8_fannie_slice.md SS3.3 and b9_zero_holonomy.md SS3. "
        "Needs the fetched HMDA sample. Same decision"
    ),
    "b7_hetero.json": (
        "B7-12b and B7-14, the off-diagonal structure of S and the "
        "seventeen-class design against its own null. **This is the record "
        "that withdrew B7-4.** Needs the fetched HMDA sample. Same decision"
    ),
    "b7_class_noise_draws50_reps20.json": (
        "B7-13: a constructed field with zero interaction and class-specific "
        "noise reads back the stage's headline rank in 40 of 40 repetitions. "
        "Needs the fetched HMDA sample. Same decision"
    ),
    "b7_class_noise_drop2_draws50_reps5.json": (
        "B7-15, the same arm on the seventeen-class design. Five repetitions, "
        "per MEASUREMENT.md 11c. Needs the fetched HMDA sample. Same decision"
    ),
    "b2_placebo_pool_width.json": (
        "needs the fetched HMDA sample, so it belongs in DATA_STAGES and is "
        "not in it"
    ),
    "b3_cip_slice.json": (
        "needs the fetched CIP sample, so it belongs in DATA_STAGES and is "
        "not in it"
    ),
    "b4_directed_edges.json": (
        "pure theory, no download, and it runs in seconds. No reason found"
    ),
    "b5_friction.json": (
        "a source audit whose verdict is REJECT and which records that a "
        "source does not exist. Whether an audit of an absent source needs a "
        "runner job is a question this list does not settle"
    ),
    "b5_p2p.json": (
        "the second source audit, same standing as b5_friction.json"
    ),
}

#: `render_results.py`'s own filename filter, kept in step by importing it below
#: rather than restated here. This constant exists only to fail loudly if the
#: import stops finding it.
_RENDERER = ROOT / "scripts" / "render_results.py"
_RUNNER = ROOT / "scripts" / "run_all.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rendered_records() -> set[str]:
    """The set the renderer turns into headings, computed by its own functions.

    Reimplementing the filter here would let the two drift, and a guard that
    drifts from the thing it guards is `centrality_bins` with a different name.
    """
    renderer = _load(_RENDERER)
    out = set()
    for path in sorted(RESULTS.glob("*.json")):
        if not renderer.is_registered(path):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if renderer.is_diagnostic(record):
            continue
        out.add(path.name)
    return out


def runner_jobs() -> set[str]:
    """Every result file some job in `run_all.py` regenerates, flags included."""
    runner = _load(_RUNNER)
    jobs = [
        *runner.EXPERIMENTS,
        *runner.SLOW_STAGES,
        *runner.DATA_STAGES,
        runner.B1_SYNTHETIC,
    ]
    return {result_file for _, _, result_file in jobs}


def test_every_rendered_record_has_a_runner_job() -> None:
    missing = sorted(rendered_records() - runner_jobs() - set(OUTSIDE_THE_RUNNER))
    assert not missing, (
        "these records render into RESULTS.md and nothing regenerates them: "
        + ", ".join(missing)
        + ". Either give each a job in run_all.py, or add it to "
        "OUTSIDE_THE_RUNNER with the reason. See docs/MEASUREMENT.md failure "
        "mode 9 for what the second option costs."
    )


def test_the_allowlist_has_no_stale_entry() -> None:
    """Both directions, so the list cannot quietly outlive its reasons."""
    rendered, jobs = rendered_records(), runner_jobs()
    not_a_record = sorted(set(OUTSIDE_THE_RUNNER) - rendered)
    assert not not_a_record, (
        "listed as outside the runner but not a rendered record: "
        + ", ".join(not_a_record)
    )
    now_covered = sorted(set(OUTSIDE_THE_RUNNER) & jobs)
    assert not now_covered, (
        "listed as outside the runner and now has a job, so the entry is "
        "stale and the exposure it described is gone: " + ", ".join(now_covered)
    )


def test_the_exposure_is_counted() -> None:
    """The number is asserted so that it can only move deliberately.

    Not a threshold and not a target. It is the count, written down so that a
    change to it shows up as an edit to this line rather than as a silently
    longer list.

    **This line failed to do its job once, and the miss is recorded here rather
    than quietly corrected.** It read `8` from 2026-08-15. On 2026-08-16 the B7
    withdrawal added **eight** entries in one commit without touching it, so the
    count sat at 16 against an assertion of 8 and that commit went in red. The
    docstring at the top of this file says the point of the list is that the
    ninth cannot be added silently, and eight were. **What failed was not the
    assertion**, which fires the moment anyone runs it. It is that nobody ran it,
    and a guard nobody runs is not a guard. B7-16 then brought two more, which is
    how it was found. `18` is the count including those two.
    """
    assert len(OUTSIDE_THE_RUNNER) == 18
