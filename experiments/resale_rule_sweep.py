"""The resale-rule contrast of ``resale_rule_probe.py`` on every stage that runs
on the asset model, each driver run inside a copy of the repository.

``resale_rule_probe.py`` runs four drivers in process and points their output
at a scratch directory. That works for a driver whose output path is one module
global. Most drivers here build paths from ``ROOT`` at import, read other
stages' stored records, or only print, so redirecting one global is not safe.
This file copies ``src``, ``experiments`` and ``results`` into a sandbox, runs
each driver there as a subprocess under the three arms of the probe
(``registered``, ``stream``, ``per_unit``), collects every record the run wrote
and its printed output, and puts the sandbox's stored records back after each
run. Nothing under the repository's own ``results`` is written except this
file's record.

Usage::

    python experiments/resale_rule_sweep.py                 # every stage
    python experiments/resale_rule_sweep.py --only a8_coverage a12_mechanisms
    python experiments/resale_rule_sweep.py --workers 4

Writes ``results/resale_rule_sweep.json``.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from resale_rule_probe import ARMS, compare  # noqa: E402

OUT = ROOT / "results" / "resale_rule_sweep.json"

#: Driver -> the arguments of its registered run. Every driver here imports the
#: asset model directly or through a module that does.
STAGES: dict[str, list[str]] = {
    "a3_asset_channel": [],
    "a3d_gate_margin": [],
    "a3f_who_empties_downstairs": [],
    "a3g_widened_population": [],
    "a3h_gate_acts": [],
    "a3j_gate_acts_grid": [],
    "a5a_units_cap_probe": [],
    "a7a_continuous_c": [],
    "a7b_probes": ["--grid"],
    "a8_coverage": [],
    "a12_mechanisms": [],
    "a14_scale": [],
    "a22_exact_field": [],
    "a24_information_wall": ["--all"],
    "a42_catchup_field_split": ["--run"],
    "a47_block1": [],
    "a47_block2": [],
    "a47_block4": [],
    "a47_block5": [],
    "a48_block1": [],
    "a48_grid": [],
    "a49_block1": [],
    "a49_block2": [],
    "a49_block3": [],
    "a49_grid": [],
    "a50_block1": [],
    "a50_block3": [],
    "a50_block4": [],
    "a50_block5": [],
    "a50_block6": [],
    "a50_block7": [],
    "a50_grid": [],
    "a51_block1": [],
    "a51_grid": [],
    "a51_side_market_rent": [],
    # The asset-carrier variants of stages whose registered run is on the plain
    # carrier: the plain run never reaches the resale draw. ``@asset`` names the
    # variant; the module is the part before it.
    "a2d_terminal_selector@asset": ["--asset"],
    "a8_coverage@asset": ["--asset"],
    "a10_writeoff@asset": ["--asset"],
    "a11_subsistence@asset": ["--asset"],
    "a12_mechanisms@asset": ["--asset"],
    "a13_mobility@asset": ["--asset"],
    "a14_scale@asset": ["--asset"],
    "a7_continuous_c": ["--grid"],
    "a10_horizon": [],
    "a26_greedy": ["--gate"],
}

RUNNER = '''
import runpy, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root / "experiments"))
import resale_rule_probe as probe
arm, driver, rest = sys.argv[2], sys.argv[3], sys.argv[4:]
sys.argv = [driver, *rest]
with probe.rule(arm):
    try:
        runpy.run_path(str(root / "experiments" / f"{driver}.py"), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
    else:
        code = 0
print(f"__RUNNER_EXIT__ {code}")
'''


def _skip(path: Path) -> bool:
    return ".expired" in path.name or path.name == "__pycache__"


def make_sandbox() -> Path:
    box = Path(tempfile.mkdtemp(prefix="resale_rule_sweep_box_"))
    ignore = shutil.ignore_patterns("*.expired*", "__pycache__", "_baseline")
    for part in ("src", "experiments", "results"):
        shutil.copytree(ROOT / part, box / part, ignore=ignore)
    (box / "runner.py").write_text(RUNNER, encoding="utf-8")
    return box


def _state(box: Path) -> dict[str, tuple[int, int]]:
    out = {}
    for p in (box / "results").rglob("*"):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(box))] = (st.st_mtime_ns, st.st_size)
    return out


def run_one(box: Path, stage: str, arm: str, dest: Path) -> dict:
    before = _state(box)
    started = time.time()
    env = {**os.environ, "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1",
           "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
           "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(box / "runner.py"), str(box), arm,
         stage.split("@")[0], *STAGES[stage]],
        cwd=box, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env, timeout=4 * 3600,
    )
    elapsed = time.time() - started
    after = _state(box)
    written = sorted(k for k, v in after.items() if before.get(k) != v)
    dest.mkdir(parents=True, exist_ok=True)
    records = {}
    for rel in written:
        src = box / rel
        if src.suffix == ".json":
            try:
                records[Path(rel).name] = json.loads(src.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        shutil.copy2(src, dest / Path(rel).name)
        original = ROOT / rel
        if original.exists():
            shutil.copy2(original, src)
    (dest / "stdout.txt").write_text(proc.stdout, encoding="utf-8", newline="\n")
    (dest / "stderr.txt").write_text(proc.stderr, encoding="utf-8", newline="\n")
    code = None
    for line in proc.stdout.splitlines()[::-1]:
        if line.startswith("__RUNNER_EXIT__"):
            code = line.split(" ", 1)[1]
            break
    return {
        "exit": code if code is not None else f"crashed ({proc.returncode})",
        "record": records,
        "stdout": proc.stdout,
        "seconds": elapsed,
        "written": written,
    }


def worker(stage: str, scratch: Path, box: Path) -> tuple[str, dict]:
    runs = {}
    for arm in ARMS:
        runs[arm] = run_one(box, stage, arm, scratch / stage / arm)
    for arm in ARMS:
        files = runs[arm]["record"]
        criteria = []
        for fname in sorted(files):
            rec = files[fname]
            for c in (rec.get("criteria", []) if isinstance(rec, dict) else []):
                if isinstance(c, dict):
                    name = c.get("name") or c.get("criterion")
                    criteria.append({**c, "name": f"{fname}:{name}"})
        runs[arm]["record"] = {"files": files, "criteria": criteria} if files else {}
    result = compare(runs)
    result["written"] = runs["registered"]["written"]
    result["seconds_registered"] = round(runs["registered"]["seconds"], 1)
    return stage, result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    stages = args.only or list(STAGES)
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        raise SystemExit(f"unknown stages: {unknown}")
    scratch = Path(tempfile.mkdtemp(prefix="resale_rule_sweep_"))
    print(f"scratch records in {scratch}", flush=True)
    boxes = [make_sandbox() for _ in range(min(args.workers, len(stages)))]
    print(f"{len(boxes)} sandboxes", flush=True)
    record = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    record.setdefault("stage", "resale_rule_sweep")
    record.setdefault("stages", {})
    free = list(boxes)
    with cf.ThreadPoolExecutor(max_workers=len(boxes)) as pool:
        futures = {}
        queue = list(stages)

        def submit():
            while queue and free:
                stage = queue.pop(0)
                box = free.pop()
                futures[pool.submit(worker, stage, scratch, box)] = (stage, box)

        submit()
        while futures:
            done, _ = cf.wait(futures, return_when=cf.FIRST_COMPLETED)
            for fut in done:
                stage, box = futures.pop(fut)
                free.append(box)
                try:
                    _, result = fut.result()
                except Exception as exc:  # noqa: BLE001
                    result = {"error": repr(exc)}
                record["stages"][stage] = result
                if "error" in result:
                    print(f"{stage}: ERROR {result['error']}", flush=True)
                else:
                    print(
                        f"{stage}: {result['seconds_registered']}s, "
                        f"{result['numbers_compared']} numbers, "
                        f"{result['moved_by_per_unit']} moved by per-unit, "
                        f"{result['moved_by_stream']} by the stream, "
                        f"{result['rule_beyond_stream_count']} by the rule beyond "
                        f"the stream; exits {result['exit']}; verdicts that "
                        f"differ: {result['verdicts_that_differ'] or 'none'}",
                        flush=True,
                    )
                OUT.write_text(
                    json.dumps(record, indent=1, sort_keys=True, default=str) + "\n",
                    encoding="utf-8", newline="\n",
                )
            submit()
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
