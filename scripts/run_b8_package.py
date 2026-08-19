#!/usr/bin/env python3
"""Run the whole B8 backlog in one pass, so it is one round and not eleven.

`claude/全项目总账_v1.md` seven.2.2 carries B8's leftovers and says, at the
bottom of the same table, **package them into one round rather than opening a
round per item**. This is that package. It is a runner, not a station: it
decides nothing, it invents no parameter, and every number it produces comes
from the scripts it calls.

**Why a runner rather than a shell loop.** Three reasons, each of which has
already cost this project something:

1. **Seventeen products on disk carry a "Registered in `docs/b8_inputs_availability.md`"
   line pointing at a file that moved.** The writers were corrected; the outputs
   on disk are from before the correction. Nothing regenerates them on its own,
   so the stale pointer survives every partial re-run. A pass that re-runs the
   writers clears all seventeen at once, and `--check-pointers` says whether it
   did.
2. **Order matters and is not obvious.** The core table feeds the loop cache,
   the loop cache feeds four stations, and `b8_verdicts.py` reads the products
   of nine. Run out of order and a station reads a stale upstream without
   saying so.
3. **The verdict sheet must be regenerated last, and `RESULTS.md` after it.**
   `b8_verdicts.py` now refuses to write when a number in a verdict is printed
   by none of that verdict's own products, which is exactly the check that a
   re-run is meant to exercise. Running it first would check the old products.

**Is the whole round necessary? No, and this file says so rather than implying
otherwise by existing.** Asked directly on 2026-08-19 and the answer is on the
merits:

- **No number changed.** The three code edits of 2026-08-19 were a prose and
  column-name correction in one writer (O34), a new `--max-lag` flag whose
  registered default is untouched, and a check added to the verdict sheet. **No
  verdict moves and no measurement is stale.**
- **Exactly one product's content is out of date**, `results/b8_cmt_sensitivity2.md`,
  because its writer's section 2 was rewritten. That is `--minimal`, and it reads
  the core table rather than the archives.
- **The other seventeen products are stale in a header line only**: they name
  `docs/b8_inputs_availability.md`, which moved. Clearing that costs a full
  re-run of seventeen stations, several of which rescan the 2.9 GB of archives.
  **That trade is bad, and this project has already ruled the other way once**:
  the thirty references inside `HANDOFF_B8.md` were handled on 2026-08-18 by
  annotating the replacement file rather than by editing thirty places
  (ledger seven.2.3). The same treatment fits here.

So the full pass is for **after something upstream actually changes** — the core
table, the loop cache's source hash, or a station's arithmetic. It is written
down now because that is when it is cheap to write and expensive to reconstruct.

Usage::

    python scripts/run_b8_package.py --plan          # print the plan, run nothing
    python scripts/run_b8_package.py --minimal       # only what 2026-08-19 made necessary
    python scripts/run_b8_package.py                 # the whole package
    python scripts/run_b8_package.py --from b8_1_signal
    python scripts/run_b8_package.py --only b8_cmt_sensitivity2 --only b8_residue
    python scripts/run_b8_package.py --offparam      # also the off-parameter sweeps

**It does not commit anything and it does not touch git.**

Logs land in `results/_b8_package_log/<step>.log`, one per step, overwritten on
re-run. A step that fails does not stop the pass: the digest at the end lists
every non-zero exit, because a runner that halts on the first failure turns one
broken station into an unrun package.
"""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
LOGS = RESULTS / "_b8_package_log"

#: The moved file the seventeen stale products still point at.
STALE_POINTER = "b8_inputs_availability.md"

#: (step name, argv after the interpreter, why it is here / what it produces).
#: Order is dependency order and is not alphabetical.
STEPS: list[tuple[str, list[str], str]] = [
    ("core_status", ["experiments/b8_core.py", "status"],
     "does the core table exist for all six vintages. Reads only"),
    ("cache_status", ["experiments/b8_cache.py", "status"],
     "does the loop cache exist and is its source hash current. Reads only"),
    # **Measured 2026-08-19: all six vintages read STALE**, because the cache is
    # keyed on a hash of the source of every function that fed it and that
    # source has moved since the cache was written. A stale entry is refused
    # rather than served, so leaving this out does not read wrong numbers, it
    # makes every station downstream pay the rebuild separately. This is the
    # expensive step of the package and the reason it is a package.
    ("cache_build", ["experiments/b8_cache.py", "build"],
     "rebuilds data/processed/b8_loops for all six vintages. **The long one.** "
     "Everything after it reads the cache instead of rescanning 170 million rows"),

    # --- probes and audits, cheap, and three of the seventeen ---
    ("layout_probe", ["experiments/b8_layout_probe.py"], "b8_layout_probe.md"),
    ("layout_probe_b", ["experiments/b8_layout_probe_b.py"], "b8_layout_probe_b.md"),
    ("field_audit", ["experiments/b8_field_audit.py"], "b8_field_audit.md"),

    # --- the instrument ---
    ("omega", ["experiments/b8_omega.py"], "b8_omega_payment_coverage.md"),
    ("loops", ["experiments/b8_loops.py"], "b8_loops_census.md"),
    ("triangles", ["experiments/b8_triangles.py"], "b8_triangles.md"),
    ("loop_omega", ["experiments/b8_loop_omega.py"], "b8_loop_omega.md"),
    ("quiet_delta", ["experiments/b8_quiet_delta.py"], "b8_quiet_delta.md"),

    # --- the gates and the eight criteria ---
    ("0a_gate", ["experiments/b8_0a_gate.py"], "b8_0a_gate.md, backs B8-0a"),
    ("0b_floor", ["experiments/b8_0b_floor.py"], "b8_0b_floor.md, backs B8-0b"),
    ("1_signal", ["experiments/b8_1_signal.py"], "b8_1_signal.md, backs B8-1"),
    ("residue", ["experiments/b8_residue.py"],
     "b8_residue.md, backs B8-1's section 21.6 reading"),
    ("2_windows", ["experiments/b8_2_windows.py"], "b8_2_windows.md, backs B8-2 and B8-6"),
    ("2_curve", ["experiments/b8_2_curve.py"], "b8_2_curve.md, backs B8-2"),
    ("3_paths", ["experiments/b8_3_paths.py"], "b8_3_paths.md, backs B8-3"),
    ("3_curve", ["experiments/b8_3_curve.py"], "b8_3_curve.md, backs B8-3"),
    ("4_class", ["experiments/b8_4_class.py"], "b8_4_class.md, backs B8-4a"),
    ("c9_cells", ["experiments/b8_c9_cells.py"], "b8_c9_cells.md, backs B8-4a and B8-4b"),
    ("5_hole", ["experiments/b8_5_hole.py"], "b8_5_hole.md, backs B8-5 and B8-6"),

    # --- the C-series checks ---
    ("c8_1c", ["experiments/b8_c8_1c_contract_payment.py"], "b8_c8_1c_contract_payment.md"),
    ("c8_1c_b", ["experiments/b8_c8_1c_contract_payment_b.py"], "b8_c8_1c_contract_payment_b.md"),
    ("c8_1e", ["experiments/b8_c8_1e_undermode.py"], "b8_c8_1e_undermode.md"),
    ("c8_1f", ["experiments/b8_c8_1f_freeze_recovery.py"],
     "b8_c8_1f_freeze_recovery.md at the registered MAX_LAG of 6"),
    ("c8_arithmetic", ["experiments/b8_c8_arithmetic.py"], "b8_c8_arithmetic.md"),
    ("c10_contract_move", ["experiments/b8_c10_contract_move.py"], "b8_c10_contract_move.md"),
    ("c10_4_tier", ["experiments/b8_c10_4_tier_carrier.py"], "b8_c10_4_tier_carrier.md"),
    ("c11_deferred", ["experiments/b8_c11_deferred_balance.py"], "b8_c11_deferred_balance.md"),
    ("c12_impact", ["experiments/b8_c12_impact.py"], "b8_c12_impact.md"),
    ("c13_double", ["experiments/b8_c13_double_balance.py"], "b8_c13_double_balance.md"),

    # --- the curve sensitivity, which carries O34's correction ---
    ("cmt_sensitivity", ["experiments/b8_cmt_sensitivity.py"], "b8_cmt_sensitivity.md"),
    ("cmt_sensitivity2", ["experiments/b8_cmt_sensitivity2.py"],
     "b8_cmt_sensitivity2.md. **This run is what clears O34**: the stale "
     "paragraph and the two mislabelled columns were fixed in the writer on "
     "2026-08-19 and the file on disk is from before that"),

    # --- last, and in this order ---
    ("verdicts", ["experiments/b8_verdicts.py"],
     "results/b8_verdicts.json. **Refuses to write** if a number in a verdict "
     "is printed by none of that verdict's own products"),
    ("render", ["scripts/render_results.py"], "RESULTS.md"),
]

#: What the 2026-08-19 edits actually make necessary. Everything outside this
#: list would be re-run to correct a header line, which is not worth an archive
#: scan; see the note at the top of this file.
MINIMAL = ("cmt_sensitivity2", "verdicts", "render")

#: Runs at a parameter other than the registered one. They write `.offparam_`
#: files, which `render_results.py` keeps out of `RESULTS.md` by filename. Off
#: by default because an off-parameter run is not a claim.
OFFPARAM: list[tuple[str, list[str], str]] = [
    ("c8_1f_lag12", ["experiments/b8_c8_1f_freeze_recovery.py", "--max-lag", "12"],
     "seven.2.2's 'C8-1f's MAX_LAG raised and re-run'. Writes "
     "b8_c8_1f_freeze_recovery.offparam_lag12.md. The short-lag columns cannot "
     "move: the loop takes the first matching lag, so a higher ceiling only "
     "adds later chances. What moves is lag_hist's tail and the split between "
     "lag_none_room and lag_censored"),
]


def stale_pointer_files() -> list[str]:
    return sorted(p.name for p in RESULTS.glob("b8_*.md")
                  if STALE_POINTER in p.read_text(encoding="utf-8", errors="replace"))


def run(steps: list[tuple[str, list[str], str]]) -> list[tuple[str, int, float]]:
    LOGS.mkdir(parents=True, exist_ok=True)
    out = []
    for i, (name, argv, _why) in enumerate(steps, 1):
        log = LOGS / f"{name}.log"
        print(f"[{i}/{len(steps)}] {name} ... ", end="", flush=True)
        t0 = time.time()
        with open(log, "w", encoding="utf-8") as fh:
            rc = subprocess.call([sys.executable, "-u"] + argv, cwd=ROOT,
                                 stdout=fh, stderr=subprocess.STDOUT)
        dt = time.time() - t0
        print(f"{'ok' if rc == 0 else 'EXIT %d' % rc} in {dt:.0f}s")
        out.append((name, rc, dt))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print the plan, run nothing")
    ap.add_argument("--from", dest="start", default=None, help="resume at this step")
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--minimal", action="store_true",
                    help="only the steps the 2026-08-19 edits make necessary")
    ap.add_argument("--offparam", action="store_true",
                    help="also the off-parameter sweeps, which write .offparam_ files")
    ap.add_argument("--check-pointers", action="store_true",
                    help="list the products still naming the moved register, run nothing")
    a = ap.parse_args()

    if a.check_pointers:
        bad = stale_pointer_files()
        print(f"{len(bad)} product(s) still name `docs/{STALE_POINTER}`:")
        for n in bad:
            print("   ", n)
        return 0

    # The off-parameter runs go before `verdicts` and `render`, not after: they
    # write nothing those two read (the `.offparam_` filename keeps them out),
    # but a plan that ends on `render` is the one a reader can trust to be the
    # last thing that touched RESULTS.md.
    steps = STEPS[:-2] + (list(OFFPARAM) if a.offparam else []) + STEPS[-2:]
    if a.minimal:
        steps = [s for s in steps if s[0] in MINIMAL]
    if a.only:
        keep = set(a.only)
        steps = [s for s in steps if s[0] in keep or s[1][0].split("/")[-1][:-3] in keep]
    if a.start:
        names = [s[0] for s in steps]
        if a.start not in names:
            ap.error(f"--from {a.start} is not a step; steps are {', '.join(names)}")
        steps = steps[names.index(a.start):]
    if not steps:
        ap.error("nothing selected")

    if a.plan:
        print(f"{len(steps)} step(s), in this order:\n")
        for i, (name, argv, why) in enumerate(steps, 1):
            print(f"{i:2d}. {name:22s} {' '.join(argv)}")
            print(f"    -> {why}")
        return 0

    before = stale_pointer_files()
    print(f"before: {len(before)} product(s) name the moved register\n")
    results = run(steps)
    after = stale_pointer_files()

    print("\n" + "=" * 62)
    bad = [(n, rc) for n, rc, _ in results if rc]
    print(f"{len(results) - len(bad)}/{len(results)} steps exited 0"
          + ("" if not bad else "; non-zero: "
             + ", ".join(f"{n} ({rc})" for n, rc in bad)))
    print(f"stale pointer: {len(before)} before, {len(after)} after"
          + ("" if not after else "; still stale: " + ", ".join(after)))
    slow = sorted(results, key=lambda r: -r[2])[:5]
    print("slowest: " + ", ".join(f"{n} {dt:.0f}s" for n, _, dt in slow))
    print(f"logs in {LOGS.relative_to(ROOT)}")
    print("\nnot done by this package, and why:")
    print("  - the 46.65 per cent of underpaid months that are still unnamed: "
          "an investigation, not a run")
    print("  - O35, the 2017Q1 cure whose offset fails on 115 floors: unread")
    print("  - the 1,065 unattributed loop displacement in section 5.1: unread")
    print("  - the full-year download: needs gate five (D21) first")
    print("  - pit 50's uncovered path: **not a leftover.** The pit table's own "
          "last sentence registers it as a known untested path and refuses to "
          "grow the fixture for it. Address: experiments/b8_4_class.py "
          "analyse() lines 375-396. Re-filed 2026-08-19")
    print("  - three scripts still rebuild instead of reading the core table: "
          "a speed change with the numbers unchanged, not attempted here")
    return 1 if bad else 0


if __name__ == "__main__":
    # `--plan | head` should not end in a traceback.
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
