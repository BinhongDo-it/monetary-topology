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

**It is a ratchet, not a clean sheet.** `OUTSIDE_THE_RUNNER` names every
record that is outside the runner together with the reason it is there, because
a count nobody can see is not an exposure anybody will fix. The point of the
list is that the next one cannot be added silently.

**The count lives in one place, and it is an assertion rather than prose.** An
earlier version of this docstring said "eight records", the list grew past it,
and the sentence stayed wrong: a number in prose beside a list that is the truth
is a second source that only ever drifts. `test_the_exposure_is_counted` carries
the number instead, because an assertion fires and a sentence does not.

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
    "b8_verdicts.json": (
        "B8's verdict sheet. The stage writes markdown, so none of its "
        "thirty-one products reaches RESULTS.md through the renderer's glob "
        "and the strongest carrier in the programme was absent from that file "
        "entirely. This sheet is assembled by experiments/b8_verdicts.py from "
        "products that must already be on disk, and it re-measures nothing, so "
        "a runner job would run a transcription rather than a stage. The "
        "close-out task is for B8's writers to emit JSON beside each markdown "
        "product; this entry goes away when they do"
    ),
    "a7_continuous_c.json": (
        "A7-A's measurement record. Its diagnostic_only flag was cleared on "
        "2026-08-18 (M-46) so the stage's own readings are visible in RESULTS.md "
        "and not only its verdict sheet. It is listed here rather than given a "
        "runner job because the run is about forty minutes and nothing about it "
        "has changed; re-running it on every CI pass buys nothing. THE CAVEAT THE "
        "CLEARED FLAG USED TO CARRY, which must travel with any citation: D_fixed, "
        "the estimator section 4.2 registers as scored, is not computed in this "
        "file. Every gap here is D_reach, which the same section registers as "
        "reported and never scored."
    ),
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
    # --- B9, all sixteen, added 2026-08-18 ---------------------------------
    # **Ruled 2026-08-18: B9 is a historical stage and is not maintained.** The stage
    # closed on 2026-08-17 and its two authority documents are
    # B9's design and result files (outside this repository) (D19, eleven
    # files merged). No runner path was built and none will be: the retrieval
    # side needs `DATABENTO_API_KEY` and the cached venue captures under
    # `data/raw/b9/`, and the `--nbbo-*` jobs are the expensive ones.
    #
    # **What that costs, stated rather than implied.** These sixteen are the
    # records a reader sees under the B9 headings in `RESULTS.md`, and nothing
    # regenerates them, so failure mode 9 is live on every one. It is a
    # decision, not an oversight, and the thing that makes it survivable is
    # that the stage is closed and its readings were re-verified against these
    # files on 2026-08-18, every one of them, digit for digit.
    "b9_floor_measurement.json": (
        "SS24, **flipped out of diagnostic_only by a ruling on 2026-08-18**. It carries the two readings this stage is hardest on: "
        "`off-grid = 0.000` across sixteen funds and 6,464 reconstructed "
        "closes, which is what identifies the disclosed price as the closing "
        "NBBO midpoint, and the tick comparison, `15.83x` against `1.42x`, "
        "which rejects the quantisation account. The field had said \"reads no "
        "prediction\", which is true and is not that field's test. Needs only "
        "the cached SSGA workbooks, so `--grid` is the cheapest B9 job to wire "
        "back in if anyone ever does. Historical stage, not maintained"
    ),
    "b9_gate.json": (
        "B9-0. **Relabelled from a test to a construction check** "
        "(docs/b9_zero_holonomy.md SS49.1): the reversed edge is "
        "`-omega(v, u, st)` on the same state dict, so the sum is `-x + x` and "
        "cannot be non-zero. The record now carries that in `gate_asserts` and "
        "the `worst_note` says an exact `0.0` in the agreement column is a "
        "branch artefact. Historical stage, not maintained"
    ),
    "b9_a1.json": (
        "B9-A-1 against the published spread, which SS24 established is the "
        "**cost** floor and not the measurement floor. The verdict labels are "
        "readings about arbitrageability. Superseded as the headline by "
        "b9_measured.json. Historical stage, not maintained"
    ),
    "b9_a2.json": (
        "B9-A-2, the calm-to-stress gradient, and **the home of SS18.1's "
        "headline `1.027 / 0.562 / 1.683`**, which SS18 mis-cites to "
        "b9_a1.json. Historical stage, not maintained"
    ),
    "b9_measured.json": (
        "B9-A-1 and A-2 against the measurement floor `F_m = 0.005 / NAV`. "
        "**This is the station's headline record**: the index part reads "
        "`1.050` to `5.083`, eleven of eleven above one. Historical stage, "
        "not maintained"
    ),
    "b9_disc.json": (
        "D1, D1b and D2, the three discriminators with a point prediction "
        "under the noise null. Historical stage, not maintained"
    ),
    "b9_disc_control.json": (
        "the same three on the B9-A-7 control sample, which exists so that a "
        "restricted run is not compared against a full one. Historical stage, "
        "not maintained"
    ),
    "b9_disc_recon.json": (
        "the same three on the reconstructed price. **The pair with "
        "b9_disc_control.json is the whole of B9-A-7 on D2.** Historical "
        "stage, not maintained"
    ),
    "b9_decomp.json": (
        "SS31's variance decomposition: `rho_c`, `V_c`, `V_e`, `w`, the "
        "four-cell verdict, and SS33's circular-shift null. **Re-run "
        "2026-08-18** to land the corrected `se_d_rho_c` (the difference's own "
        "standard error, not one end's) and the divergence guard on "
        "`pairs_per_regime_for_2se`. Historical stage, not maintained"
    ),
    "b9_decomp_control.json": (
        "the same decomposition on the B9-A-7 control sample. Note its market-"
        "stress split is `193/404` where the main run's is `194/404`, so its "
        "`d_rho_c` is `0.069422` and not `0.069132`. Historical stage, not "
        "maintained"
    ),
    "b9_decomp_recon.json": (
        "the same on the reconstructed price. **This is the record that failed "
        "B9-A-7**: `d_rho_c` collapses from `+0.0694` to `+0.0001` and the "
        "`V_e` stress-over-calm ratio reverses. Historical stage, not "
        "maintained"
    ),
    "b9_gate_speed.json": (
        "SS26, **the only prediction anywhere in B9 registered with opposed "
        "signs**. It ran and landed on the flow account's side: the zero-"
        "change share falls in ten of eleven. Historical stage, not maintained"
    ),
    "b9_nbbo_overlap.json": (
        "B9-A-6 on `XNAS.ITCH`, exact-match `0.5256`. Needs the cached venue "
        "captures under `data/raw/b9/_nbbo` and a vendor key. **Also written "
        "by an older version of the writer**: it carries neither `dataset` nor "
        "`offset_s`, which the current code emits. Historical stage, not "
        "maintained"
    ),
    "b9_nbbo_overlap_ARCX_PILLAR.json": (
        "B9-A-6 on the listing venue, `0.8975`, the best candidate and still a "
        "failure against the registered `0.90`. Written by an intermediate "
        "version: no `min_size`, `registered_fund_days`, `never_compared` or "
        "`header_only_captures`. Historical stage, not maintained"
    ),
    "b9_nbbo_overlap_ARCX_PILLAR_sz100.json": (
        "the round-lot filter on the same venue. **The test it was built for "
        "is void, not negative** (SS43): `bbo-1s` carries no deeper level, so a "
        "record failing the size filter is dropped rather than corrected and "
        "the comparison falls back to a staler snapshot. Historical stage, not "
        "maintained"
    ),
    "b9_nbbo_combined.json": (
        "the four-venue best, `0.5564`, **worse than the listing venue alone**, "
        "which is what fired SS39.3's stopping rule. Its `halfcent_steps` "
        "carries the vendor's undefined-price sentinel in the tail; see "
        "B9's result file (outside this repository), section 8.5. Historical stage, not maintained"
    ),
    "b9_nbbo_combined_sz100.json": (
        "the four-venue best under the round-lot filter, `0.5456`. Same void-"
        "not-negative standing as the other `sz100` record. Historical stage, "
        "not maintained"
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
    "b14_t1_order_type.json": (
        "B14's T1. Same standing as b14_gate0.json and the same download, plus "
        "its own 136 MB order-type panel under data/cache/b14/, which "
        "`.gitignore` excludes for the same reason it excludes data/raw"
    ),
    "b13_zero_domain.json": (
        "B13. The gate reads CME MDP 3.0 packet captures, 6.8 GB compressed for "
        "one ten-minute window, which are not in the repository and are not "
        "redistributable. **The products are**: `b13_verdicts.py` copies the "
        "station's ten console outputs into `results/` on every run, so the "
        "evidence a criterion cites is present even though the capture that "
        "produced it is not. Wiring it back in costs the download and nothing "
        "else, and until someone does, the number check inside that sheet is "
        "what stands between the criteria and the products going out of step"
    ),
    "b14_gate0.json": (
        "B14-0. Needs the ten Tick Pilot Appendix B.I monthly files, 1.07 GB "
        "compressed, hand-downloaded from ftp.nyxdata.com and not in the "
        "repository, plus the 30 MB derived panel under data/cache/b14/. The "
        "gate itself runs in seconds off that cache, so wiring it back in "
        "costs only the download. **What this costs is stated rather than "
        "implied**: nothing regenerates this record, so it goes stale "
        "invisibly, and the thing that limits the damage is that the record "
        "carries its own reproduction check (the six registered margins are "
        "recomputed and compared on every run)"
    ),
    "b14_gate0.authoritative.json": (
        "B14-0 re-run against the published group list rather than the "
        "Test_Group field. Same cost as b14_gate0.json above: the ten "
        "Appendix B.I monthly files are hand-downloaded and not in the "
        "repository. It carries the same six-margin reproduction check, "
        "which is what limits the damage of nothing regenerating it"
    ),
    "b14_gate0.sens_FULL.json": (
        "B14-0's order-type sensitivity arm, the unrestricted variant. Same "
        "download as b14_gate0.json. The four sens_* records are one sweep "
        "and share a reason: each re-runs the gate with a set of order types "
        "dropped, so they cost the same 1.07 GB and nothing else"
    ),
    "b14_gate0.sens_X16.json": (
        "B14-0's order-type sensitivity arm, type 16 dropped. See "
        "b14_gate0.sens_FULL.json for the shared reason"
    ),
    "b14_gate0.sens_X22.json": (
        "B14-0's order-type sensitivity arm, type 22 dropped. See "
        "b14_gate0.sens_FULL.json for the shared reason. This is the arm the "
        "caveat hangs on: T6's six of six depends on type 22 entirely"
    ),
    "b14_gate0.sens_X2216.json": (
        "B14-0's order-type sensitivity arm, types 22 and 16 dropped "
        "together. See b14_gate0.sens_FULL.json for the shared reason"
    ),
    "b14_stage_two.json": (
        "B14's verdict sheet, the same shape as b8_verdicts.json above. It is "
        "assembled by experiments/b14_verdicts.py from records that must "
        "already be on disk and it re-measures nothing, so a runner job would "
        "run a transcription rather than a stage. It carries a check of its "
        "own instead: every number in a criterion must appear in one of that "
        "criterion's own sources, and a number that is not a reading has to "
        "be listed as exempt with a reason"
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

    **And it had drifted, found 2026-08-18.** `main` filters on three things and
    this function called two of them, so a file with no `stage` key counted as
    rendered here and was skipped there. `b9_datasets.json` is the file that
    exercised it: this test demanded a runner job for a record that never
    reaches `RESULTS.md`. The third filter is now `renderer.is_record` and both
    callers use it, which is what this docstring was asking for all along.
    """
    renderer = _load(_RENDERER)
    out = set()
    for path in sorted(RESULTS.glob("*.json")):
        if not renderer.is_registered(path):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if not renderer.is_record(record):
            continue
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
    how it was found. `18` was the count including those two.

    **It drifted again, and by one this time.** On 2026-08-18 the list held
    **19** against an assertion of `18`, so a nineteenth had gone in without
    this line being touched and the test had been red for however long that
    was. Which entry it was is not recoverable from the file, and that is the
    point: **a count checked only when somebody happens to run the check tells
    you an exposure moved without telling you which.** It stays a number
    anyway, because the alternative is no signal at all, but the honest reading
    of this line is "something changed", never "nothing changed".

    **`40`, 2026-08-19.** Two B14 records went in, `b14_gate0.json` and
    `b14_t1_order_type.json`, sixteen lines in one edit, and this line was not
    touched. Found by running the suite rather than by anyone noticing, which is
    the same way the last three drifts were found. **This time the entries are
    identifiable**, because the edit was still uncommitted when the check ran, so
    for once the honest reading of this line is not merely "something changed".

    `36` is the count after B9's went in on 2026-08-18 (ruled 2026-08-18, the stage
    historical and unmaintained), which is the largest single addition this
    list has taken. Sixteen arrived with that ruling and a seventeenth,
    `b9_floor_measurement.json`, arrived an hour later when its
    `diagnostic_only` was flipped, which is the shape this list is for: the
    exposure grew because a record stopped being a diagnostic, not because
    anybody wrote new code.

    **`41` was on disk against an assertion of `40` on 2026-08-21**, before
    anything in this round was added. Which entry drifted is not recoverable
    from the file, which is the fourth time that sentence has had to be written
    here. It is recorded rather than absorbed, because 40 moving to 47 in one
    edit would otherwise read as six additions when it is seven.

    **`47`, 2026-08-21.** B14's close-out: `b14_gate0.authoritative.json`, the
    four `b14_gate0.sens_*.json` arms, and `b14_stage_two.json`. The five gate
    records share `b14_gate0.json`'s reason, a hand-downloaded 1.07 GB that is
    not in the repository. The verdict sheet is here for the other reason on
    this list, the one `b8_verdicts.json` gives: it transcribes rather than
    measures, so a runner job would regenerate nothing.
    """
    assert len(OUTSIDE_THE_RUNNER) == 47
