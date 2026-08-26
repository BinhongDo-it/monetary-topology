"""Rule 19 for a newly added switch: off must reproduce the committed records.

**What this checks and why it is a re-run rather than an argument.** A new
field on ``NetworkConfig`` reaches eleven stations through four objects:
``Network`` itself, and the three subclasses ``A6Model``, ``A3Model`` and
``A4Model``. Reasoning that a guard returns early is not the check. The check
is that the recorded numbers come back, field for field, out of the code as it
stands now.

**The criterion is structural and carries no threshold.** Every re-run row must
equal its recorded row on every field. A mismatch is printed as the row, both
values side by side, because a count of mismatches says nothing about which
object changed.

The records this reads were written before the switch existed, which is what
makes them the baseline. Reading them is the whole point: they are not a
convenience, they are the pre-change state of the world.

**The cheap mode is the default and the re-run mode is the fallback.** Rule 19
asks whether a new switch at its default reproduces the recorded numbers, and
the stations get re-run anyway in the ordinary course of work. So the ordinary
flow is: snapshot the records before touching a shared module, do the work, run
the stations, then diff the records against the snapshot. That costs a copy and
a comparison rather than eighteen hundred simulations, and it is **strictly
stronger** in the place that has actually broken: a JSON diff has no
reconstruction step, while the re-run mode rebuilds each row from its fields
and therefore has to be edited every time a row grows one. That reconstruction
missed `funding` once and `retain` once, in a single afternoon.

    python scripts/check_default_off.py --snapshot     # before the work
    ...                                                # do the work, run stages
    python scripts/check_default_off.py --diff         # after

**A record that did not move is not the same as a record that reproduced.** It
can also be a record nothing re-ran. So `--diff` reports both, and names the
records whose file is older than the snapshot rather than counting them as
clean. That distinction is failure mode 47 and it is the one thing the cheap
mode could get wrong.

**A record is checked against the machine that wrote it.** Two of A18's B-arm
cells sit on a boundary where a difference of order 1e-10, which is what
separates one BLAS build's summation order from another's, moves the count
below the subsistence line by twenty-one nodes. The code reproduces itself to
the bit on either machine; the reading does not survive the crossing. There is
no exemption list here for that and there should not be one: the stage
measures its own boundary cells and records them, see A18_B6 and
docs/MEASUREMENT.md failure mode 48. Run this where the record was made.

Run from the repository root::

    python scripts/check_default_off.py
    python scripts/check_default_off.py --quick   # one cell per arm

Nothing is written. This script has no output file by design: it answers a
yes/no about the code in front of it and the answer is not a reading of the
world, so it does not belong in ``results/``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

RESULTS = ROOT / "results"


BASELINE = RESULTS / "_baseline"


def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def snapshot() -> int:
    """Copy every record aside, so a later diff has something to diff against.

    **Nothing is deleted.** An existing baseline is renamed with an `.expired_`
    suffix and the next free number, which is this repository's convention for
    anything that is finished with but must not vanish.
    """
    import shutil
    if BASELINE.exists():
        n = 1
        while (RESULTS / f"_baseline.expired_{n}").exists():
            n += 1
        BASELINE.rename(RESULTS / f"_baseline.expired_{n}")
        print(f"  previous baseline kept as results/_baseline.expired_{n}")
    BASELINE.mkdir(parents=True)
    files = sorted(RESULTS.glob("*.json"))
    stamps = {}
    for f in files:
        shutil.copy2(f, BASELINE / f.name)
        stamps[f.name] = f.stat().st_mtime
    (BASELINE / "_mtimes.txt").write_text(
        "\n".join(f"{k}\t{v!r}" for k, v in sorted(stamps.items())) + "\n",
        encoding="utf-8", newline="\n")
    print(f"  snapshot: {len(files)} record(s) copied to results/_baseline")
    return 0


_ABSENT = object()


def _same(a, b) -> bool:
    """Equality that treats two NaNs as the same value.

    **Bought immediately.** The first run of this diff reported four records as
    changed on twelve fields whose old and new values were both `nan`, because
    `nan != nan`. A record carrying a NaN is carrying a real reading here (a
    ratio with no denominator, reported rather than filled in), so the fix is
    in the comparison and not in the records.
    """
    if a is _ABSENT or b is _ABSENT:
        return a is b
    if isinstance(a, float) and isinstance(b, float):
        if a != a and b != b:          # both NaN
            return True
    return a == b


def _fields(obj, prefix=""):
    """Flatten a record to (path, value) so a diff can name what moved."""
    if isinstance(obj, dict):
        for k in sorted(obj):
            yield from _fields(obj[k], f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _fields(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def diff_records() -> int:
    """Compare every record against the snapshot, field by field."""
    if not BASELINE.exists():
        print("  no baseline. Run --snapshot before the work, not after")
        return 1
    stamp_file = BASELINE / "_mtimes.txt"
    stamps = {}
    if stamp_file.exists():
        for line in stamp_file.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                k, v = line.split("\t", 1)
                stamps[k] = float(v)

    changed, clean, stale, new, gone = [], [], [], [], []
    for base in sorted(BASELINE.glob("*.json")):
        cur = RESULTS / base.name
        if not cur.exists():
            gone.append(base.name)
            continue
        a = json.loads(base.read_text(encoding="utf-8"))
        b = json.loads(cur.read_text(encoding="utf-8"))
        fa, fb = dict(_fields(a)), dict(_fields(b))
        moved = [k for k in sorted(set(fa) | set(fb))
                 if not _same(fa.get(k, _ABSENT), fb.get(k, _ABSENT))]
        if moved:
            changed.append((base.name, moved, fa, fb))
        elif cur.stat().st_mtime <= stamps.get(base.name, 0.0):
            # Byte-identical and never rewritten. That is not evidence of
            # anything: nothing ran it.
            stale.append(base.name)
        else:
            clean.append(base.name)
    for cur in sorted(RESULTS.glob("*.json")):
        if not (BASELINE / cur.name).exists():
            new.append(cur.name)

    print(f"  {len(clean)} record(s) re-run and identical")
    print(f"  {len(changed)} record(s) differ")
    print(f"  {len(stale)} record(s) NOT RE-RUN, so untested by this diff")
    if new:
        print(f"  {len(new)} record(s) new since the snapshot: {new}")
    if gone:
        print(f"  {len(gone)} record(s) missing now: {gone}")
    for name, moved, fa, fb in changed:
        print(f"\n  [DIFF] {name}: {len(moved)} field(s)")
        for k in moved[:20]:
            print(f"    {k}: was {fa.get(k, '<absent>')!r}  now "
                  f"{fb.get(k, '<absent>')!r}")
        if len(moved) > 20:
            print(f"    ... and {len(moved) - 20} more")
    if stale:
        print("\n  NOT RE-RUN, named rather than counted as clean:")
        for name in stale:
            print(f"    {name}")
    return 0 if not changed else 1


#: Set by ``main`` from ``--slice``. Every path narrows its rows through this,
#: so a full check can be run in pieces on a machine that will not hold a long
#: process. ``(0, 1)`` is every row.
SLICE = (0, 1)


def take(rows: list) -> list:
    """The rows this invocation is responsible for."""
    i, n = SLICE
    return rows[i::n] if n > 1 else rows


def compare(tag: str, recorded: dict, rerun: dict, keys) -> list[str]:
    """Field-for-field. Returns the differing fields, named, with both values."""
    bad = []
    for k in keys:
        a, b = recorded.get(k), rerun.get(k)
        if isinstance(a, float) and isinstance(b, float):
            same = a == b
        else:
            same = a == b
        if not same:
            bad.append(f"    {tag}  {k}: recorded {a!r}  rerun {b!r}")
    return bad


def report(name: str, checked: int, bad: list[str]) -> bool:
    mark = "OK  " if not bad else "DIFF"
    print(f"  [{mark}] {name}: {checked} row(s) re-run, {len(bad)} field(s) differ")
    for line in bad[:40]:
        print(line)
    if len(bad) > 40:
        print(f"    ... and {len(bad) - 40} more differing fields")
    return not bad


def check_a12(quick: bool) -> bool:
    """Network and A6Model. The transfer arms route through A6Model."""
    a12 = importlib.import_module("a12_mechanisms")
    ok = True
    for record_name, asset in (("a12_mechanisms", False),
                               ("a12_mechanisms_asset", True)):
        rec = load(record_name)
        carrier = a12.carrier_at(a12._A8.BASE_NODES, asset=asset)
        arms = a12.arms_for(a12.need_for(carrier))
        for k in [k for k, (_f, _w, rate) in arms.items()
                  if rate > 0.0 and carrier.asset]:
            del arms[k]
        rows = take(rec["runs"])
        if quick:
            seen, keep = set(), []
            for row in rows:
                if row["arm"] not in seen:
                    seen.add(row["arm"])
                    keep.append(row)
            rows = keep
        bad = []
        for row in rows:
            fresh = a12.one_run(
                row["arm"], row["f2i"], row["elasticity"],
                rec["rounds"], rec["seed"], arms, carrier,
            )
            tag = f"{row['arm']} f2i={row['f2i']} e={row['elasticity']}"
            bad += compare(tag, row, fresh,
                           [k for k in row if k != "surfaces"])
            if row.get("surfaces") != fresh.get("surfaces"):
                bad.append(f"    {tag}  surfaces: recorded "
                           f"{row.get('surfaces')!r}  rerun {fresh.get('surfaces')!r}")
        which = "A3Model, asset carrier" if asset else "Network + A6Model"
        ok &= report(f"{record_name} ({which})", len(rows), bad)
    return ok


def check_a11(quick: bool) -> bool:
    """The floor itself, in both exit rules. This is the state resupply reads."""
    a11 = importlib.import_module("a11_subsistence")
    ok = True
    for record_name, mode, asset in (
        ("a11_subsistence", "exit", False),
        ("a11_subsistence_drawdown", "drawdown", False),
        ("a11_subsistence_asset", "exit", True),
    ):
        rec = load(record_name)
        rows = take(rec["runs"])
        if quick:
            rows = rows[::9]
        bad = []
        for row in rows:
            fresh = a11.one_run(
                row["need_multiple"], row["grace"], row["seed"],
                rec["rounds"], row["graph"] == "complete",
                asset=asset, mode=mode,
            )
            tag = (f"need={row['need_multiple']} grace={row['grace']} "
                   f"seed={row['seed']} {row['graph']}")
            bad += compare(tag, row, fresh, list(row))
        ok &= report(f"{record_name} (floor, {mode})", len(rows), bad)
    return ok


def check_a16(quick: bool) -> bool:
    """The hub obligation, added the day before. Its record is the newest one."""
    a16 = importlib.import_module("a16_hub_debt")
    rec = load("a16_hub_debt")
    rows = take(rec["runs"])
    if quick:
        seen, keep = set(), []
        for row in rows:
            k = (row["orientation"], row["rate"])
            if k not in seen:
                seen.add(k)
                keep.append(row)
        rows = keep
    bad = []
    for row in rows:
        orientation = None if row["orientation"] == "off" else row["orientation"]
        fresh = a16.one_run(orientation, row["rate"], row["hubs"],
                            row["need_multiple"], row["seed"])
        tag = (f"{row['orientation']} rate={row['rate']} hubs={row['hubs']} "
               f"need={row['need_multiple']} seed={row['seed']}")
        bad += compare(tag, row, fresh,
                       [k for k in row if k != "hub_nodes"])
        if list(row.get("hub_nodes", [])) != list(fresh.get("hub_nodes", [])):
            bad.append(f"    {tag}  hub_nodes differ")
    return report("a16_hub_debt (hub obligation)", len(rows), bad)


def check_a18(quick: bool) -> bool:
    """A18's A arm. Added 2026-08-26, and it was added because it was missing.

    ``a18_policy_paths.json`` was written on the day two other switches went
    into ``network.py``, and the rule 19 pass for those switches read the
    records that existed when it was written rather than the ones that existed
    when it finished. So A18 was never checked, and fifty-one of its fields had
    drifted before anybody looked.

    They had all drifted the same way and it was worth knowing: see
    ``_largest_jump`` in the stage, which now reports no jump at all on a series
    that never moves by more than one unit in the last place.
    """
    a18 = importlib.import_module("a18_policy_paths")
    rec = load("a18_policy_paths")
    rows = take(rec["runs"])
    if quick:
        rows = rows[::8]
    specs = {label: (mode, wspec, auth)
             for (label, mode, wspec, auth) in a18.policies()}
    bad = []
    for row in rows:
        mode, wspec, auth = specs[row["policy"]]
        fresh = a18.one_run(row["policy"], mode, wspec, auth,
                            row["need_multiple"], row["seed"])
        tag = f"{row['policy']} floor={row['need_multiple']} seed={row['seed']}"
        bad += compare(tag, row, fresh, list(row))
    return report("a18_policy_paths (policy paths)", len(rows), bad)


def check_a18b(quick: bool) -> bool:
    """A18's B arm, the one that carries the switch being extended.

    It is checked like any other record and not treated as trusted for being
    new. A new field on the spec that carries the mechanism is exactly where a
    default would fail to be a default.
    """
    a18 = importlib.import_module("a18_policy_paths")
    rec = load("a18_resupply")
    rows = take(rec["runs"])
    if quick:
        rows = rows[::8]
    bad = []
    by_control = {}
    for row in rows:
        key = (row["mode"], row["need_multiple"], row["seed"])
        if key not in by_control:
            cfg = a18.config_for(row["mode"], a18.WriteOffSpec(), "endogenous",
                                 row["need_multiple"], row["seed"])
            net = a18.Network(cfg)
            h = net.run()
            import numpy as _np
            by_control[key] = {
                "_below": a18._below_set(net, row["mode"]),
                "_holdings": _np.asarray(h.holdings, dtype=float)[-1],
                "_adjacency": net.adjacency,
            }
        # Every axis the record carries has to be handed back, or the re-run is
        # a different cell wearing the same label. This has now cost two
        # rounds: once when `funding` was added and once when `retain` was.
        # **A checker that reconstructs a row from its fields has to be edited
        # every time a row grows a field**, and nothing enforces that but the
        # diff it produces.
        fresh = a18.resupply_run(row["mode"], row["need_multiple"],
                                 row["rate"], row["seed"], by_control[key],
                                 row.get("funding", "creditors"),
                                 retain=row.get("retain", 0.0))
        tag = (f"{row['mode']} floor={row['need_multiple']} "
               f"rate={row['rate']} route={row.get('funding')} "
               f"retain={row.get('retain')} seed={row['seed']}")
        bad += compare(tag, row, fresh, list(row))
    return report("a18_resupply (the resupply arm)", len(rows), bad)


def check_a18c(quick: bool) -> bool:
    """A18's C arm. Added the same round the arm was, per failure mode 47."""
    a18 = importlib.import_module("a18_policy_paths")
    rec = load("a18_landing")
    rows = take(rec["runs"])
    if quick:
        rows = rows[::8]
    bad = []
    for row in rows:
        fresh = a18.landing_run(row["need_multiple"], row["rate"], row["seed"],
                                row["target"], row["elasticity"],
                                retain=row.get("retain", 0.0))
        tag = (f"floor={row['need_multiple']} rate={row['rate']} "
               f"e={row['elasticity']} target={row['target']} "
               f"retain={row.get('retain')} seed={row['seed']}")
        bad += compare(tag, row, fresh, list(row))
    return report("a18_landing (the landing arm)", len(rows), bad)


def check_a18d(quick: bool) -> bool:
    """A18's D arm. Added the same round the arm was, per failure mode 47."""
    a18 = importlib.import_module("a18_policy_paths")
    rec = load("a18_repay")
    rows = take(rec["runs"])
    if quick:
        rows = rows[::8]
    bad = []
    for row in rows:
        fresh = a18.repay_run(row["mode"], row["need_multiple"], row["rate"],
                              row["seed"], row["repay"], row["funding"],
                              row["retain"])
        tag = (f"{row['mode']} floor={row['need_multiple']} "
               f"rate={row['rate']} repay={row['repay']} "
               f"route={row['funding']} seed={row['seed']}")
        bad += compare(tag, row, fresh, list(row))
    return report("a18_repay (the loan arm)", len(rows), bad)


def check_a18e(quick: bool) -> bool:
    """A18's E arm. Added the same round the arm was, per failure mode 47."""
    a18 = importlib.import_module("a18_policy_paths")
    rec = load("a18_park")
    rows = take(rec["runs"])
    if quick:
        rows = rows[::8]
    bad = []
    for row in rows:
        fresh = a18.park_run(row["need_multiple"], row["rate"], row["seed"],
                             row["park"], row["retain"], row["target"])
        tag = (f"floor={row['need_multiple']} rate={row['rate']} "
               f"park={row['park']} retain={row['retain']} "
               f"target={row['target']} seed={row['seed']}")
        bad += compare(tag, row, fresh, list(row))
    return report("a18_park (the parking arm)", len(rows), bad)


def check_a18f(quick: bool) -> bool:
    """A18's F arm. Added the same round the arm was, per failure mode 47."""
    a18 = importlib.import_module("a18_policy_paths")
    rec = load("a18_carry")
    rows = take(rec["runs"])
    if quick:
        rows = rows[::8]
    bad = []
    for row in rows:
        fresh = a18.carry_run(row["need_multiple"], row["rate"], row["seed"],
                              row["park"], row["funding"])
        tag = (f"floor={row['need_multiple']} park={row['park']} "
               f"route={row['funding']} seed={row['seed']}")
        bad += compare(tag, row, fresh, list(row))
    return report("a18_carry (the carrying arm)", len(rows), bad)


def check_a4(quick: bool) -> bool:
    """A4Model, through the stage's own A4Model-against-Network check and cells."""
    a4 = importlib.import_module("a4_causal_primitive")
    rec = load("a4_causal_primitive")
    seeds, rounds = rec["seeds"], rec["rounds"]

    pairs = a4.reproduction_check(seeds, rounds)
    failing = [s for s, good in pairs if not good]
    print(f"  [{'OK  ' if not failing else 'DIFF'}] a4 A4Model vs Network: "
          f"bitwise identical at {sum(g for _, g in pairs)} of {len(pairs)} seeds"
          + ("" if not failing else f"   FAILING SEEDS: {failing}"))

    base = a4.base_config(rule=rec["parameters"]["issuance_rule"], amount=10.0,
                          target=rec["parameters"]["injection_target"],
                          rounds=rounds,
                          opening=rec["parameters"]["uniform_opening"])
    cells = a4.main_effect_cells()
    if quick:
        cells = dict(list(cells.items())[:4])
    rows = a4.measure(cells, base=base, seeds=seeds,
                      channel_order=rec["parameters"]["channel_order"],
                      event_order=rec["parameters"]["event_order"],
                      pooling=rec["parameters"]["pooling"])
    bad = []
    for name, r in rows.items():
        if name not in rec["cells"]:
            bad.append(f"    {name}: not in the record")
            continue
        fresh = {k: a4._round(float(r[k].mean())) for k, _ in a4.SCORED_MEASURES}
        bad += compare(name, rec["cells"][name], fresh, list(fresh))
    return report("a4_causal_primitive (A4Model cells)", len(rows), bad) and not failing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="one cell per arm rather than every recorded cell")
    ap.add_argument("--only", default="",
                    help="comma separated: a12, a11, a16, a18, a18b, a18c, a18d, a18e, a18f, a4. Default all")
    ap.add_argument("--snapshot", action="store_true",
                    help="copy the records aside, before the work")
    ap.add_argument("--diff", action="store_true",
                    help="compare the records to the snapshot, after the work. "
                         "No simulation is re-run")
    ap.add_argument("--slice", default="0/1",
                    help="i/n, this invocation takes every nth row from i. "
                         "For machines that will not hold a long process")
    args = ap.parse_args()
    if args.snapshot:
        return snapshot()
    if args.diff:
        return diff_records()
    global SLICE
    i, n = args.slice.split("/")
    SLICE = (int(i), int(n))

    from monetary_topology.network import NetworkConfig
    cfg = NetworkConfig()
    print("the switch under test, at its default:")
    print(f"  resupply.rate    = {cfg.resupply.rate!r}")
    print(f"  resupply.funding = {cfg.resupply.funding!r}")
    print(f"  resupply.active  = {cfg.resupply.active!r}")
    if cfg.resupply.active:
        print("  the default is ON. Nothing below is a rule 19 check.")
        return 1
    print()

    started = time.time()
    wanted = [x.strip() for x in args.only.split(",") if x.strip()]
    available = {"a12": check_a12, "a11": check_a11,
                 "a16": check_a16, "a18": check_a18,
                 "a18b": check_a18b, "a18c": check_a18c,
                 "a18d": check_a18d, "a18e": check_a18e,
                 "a18f": check_a18f, "a4": check_a4}
    for name in wanted:
        if name not in available:
            print(f"  unknown path {name!r}; known: {sorted(available)}")
            return 1
    running = wanted or list(available)
    print(f"  running {running}, slice {SLICE[0]}/{SLICE[1]}")
    checks = [available[name](args.quick) for name in running]
    print()
    print(f"  {sum(checks)} of {len(checks)} paths reproduce their records "
          f"({time.time() - started:.0f} s)")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
