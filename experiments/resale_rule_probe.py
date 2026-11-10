"""The resale draw per unit instead of per holding, on the stages that open with
multi-unit holdings.

``A3Model._offers`` draws once for every positive ``(node, tier)`` holding at
rate ``tau`` and offers one unit when the draw lands. Stage A5 reads the same
under a draw per unit (``experiments/a5b_offer_unit_probe.py``), but A5 opens
with every holding a single unit. The stages below set ``residual_owner`` on,
which hands the unsold stock to the prior owners in whole blocks at the
opening, so the two rules part from the first round: under stage A3b's
construction the largest opening holding is 11 to 17 units.

Each stage's own driver is run three times, its record written to a scratch
directory and never over the stored one:

    registered   the rule as coded
    stream       the rule as coded, the asset random stream shifted by one seed
    per_unit     one draw per unit held, so a holding of k units offers
                 Binomial(k, tau) of them

The two rules consume the asset stream differently, so a difference between
``per_unit`` and ``registered`` mixes the rule with a change of random numbers.
``stream`` changes the random numbers and not the rule, and is the floor: a
number is read as moved by the rule only where the per-unit run moves it by
more than the shifted stream does.

Usage::

    python experiments/resale_rule_probe.py --stage a3b
    python experiments/resale_rule_probe.py --stage all
    python experiments/resale_rule_probe.py --selftest

Writes ``results/resale_rule_probe.json``.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from monetary_topology import asset as asset_module  # noqa: E402
from monetary_topology.asset import A3Model  # noqa: E402

OUT = ROOT / "results" / "resale_rule_probe.json"

#: Stage name -> (module, the module global its driver writes through, the
#: file name under that directory). ``None`` for a driver that only prints.
STAGES: dict[str, tuple[str, str | None, str | None]] = {
    "a3b": ("a3b_construction", "RESULTS", "a3b_construction.json"),
    "a3c": ("a3c_load_bearing", "RESULTS", "a3c_load_bearing.json"),
    "a47_block3": ("a47_block3", "OUT", None),
    "a4a": ("a4a_domain_probe", None, None),
}

ARMS = ("registered", "stream", "per_unit")

_REGISTERED_OFFERS = A3Model._offers
_REGISTERED_INIT = A3Model.__init__


def _per_unit_offers(self: A3Model) -> list[tuple[int, int]]:
    """``A3Model._offers`` with the exogenous draw taken once per unit held.

    The forced arm is kept as coded: a distressed node offers one unit from
    each tier it holds unless the turnover draw already took one of its
    holdings this round.
    """
    spec = self.a3.asset
    held = np.argwhere(self.units > 0)
    if held.size == 0:
        return []
    out: list[tuple[int, int]] = []
    if spec.turnover > 0.0:
        counts = self.units[held[:, 0], held[:, 1]].astype(int)
        taken = self._asset_rng.binomial(counts, spec.turnover)
        for (i, q), k in zip(held, taken, strict=True):
            out.extend([(int(i), int(q))] * int(k))
    if spec.arm == "forced":
        floor = spec.forced_sale_floor * self._claims_0
        distressed = self.holdings < floor
        already = {i for i, _ in out}
        forced = [
            (int(i), int(q))
            for i, q in held
            if distressed[i] and int(i) not in already
        ]
        self.forced_sales.append(len(forced))
        out.extend(forced)
    else:
        self.forced_sales.append(0)
    return out


def _shifted_init(self: A3Model, *args, **kwargs) -> None:
    _REGISTERED_INIT(self, *args, **kwargs)
    self._asset_rng = np.random.default_rng(
        self.a3.network.seed + 517_003 + 1
    )


@contextlib.contextmanager
def rule(arm: str):
    """Swap the resale rule, or the asset stream, on the class for one run."""
    if arm not in ARMS:
        raise ValueError(arm)
    try:
        if arm == "per_unit":
            A3Model._offers = _per_unit_offers
        elif arm == "stream":
            A3Model.__init__ = _shifted_init
        yield
    finally:
        A3Model._offers = _REGISTERED_OFFERS
        A3Model.__init__ = _REGISTERED_INIT


def run_stage(stage: str, arm: str, scratch: Path) -> dict:
    """One stage's driver under one arm, written into ``scratch`` only."""
    modname, attr, fname = STAGES[stage]
    mod = importlib.import_module(modname)
    saved_argv = sys.argv
    saved_attr = getattr(mod, attr) if attr else None
    target = scratch / f"{stage}_{arm}.json"
    if attr:
        setattr(mod, attr, scratch if fname else target)
    sys.argv = [modname]
    buf = io.StringIO()
    try:
        with rule(arm), contextlib.redirect_stdout(buf):
            try:
                code = mod.main()
            except ValueError as err:
                # The drivers print their output path relative to the
                # repository after writing it; a scratch path outside the
                # repository fails only that print.
                if "is not in the subpath" not in str(err) or not (
                    (scratch / fname).exists() if fname else target.exists()
                ):
                    raise
                code = "written"
    finally:
        sys.argv = saved_argv
        if attr:
            setattr(mod, attr, saved_attr)
    if fname:
        (scratch / fname).replace(target)
    record = json.loads(target.read_text(encoding="utf-8")) if attr else {}
    (scratch / f"{stage}_{arm}.stdout.txt").write_text(
        buf.getvalue(), encoding="utf-8", newline="\n"
    )
    return {"exit": code, "record": record, "stdout": buf.getvalue()}


def leaves(obj, prefix: str = "") -> dict[str, float]:
    """Every finite number in a record, keyed by its path."""
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k in sorted(obj):
            out.update(leaves(obj[k], f"{prefix}/{k}"))
    elif isinstance(obj, list):
        for n, v in enumerate(obj):
            key = v.get("name") if isinstance(v, dict) and "name" in v else str(n)
            out.update(leaves(v, f"{prefix}/{key}"))
    elif isinstance(obj, bool):
        out[prefix] = float(obj)
    elif isinstance(obj, (int, float)) and math.isfinite(obj):
        out[prefix] = float(obj)
    return out


def stdout_numbers(text: str) -> dict[str, float]:
    """For a driver that only prints: every number, keyed by line and place."""
    import re

    out: dict[str, float] = {}
    for n, line in enumerate(text.splitlines()):
        for m, tok in enumerate(re.findall(r"[-+]?\d+\.\d+(?:e[-+]?\d+)?", line)):
            out[f"line{n:04d}#{m}"] = float(tok)
    return out


def verdicts(record: dict) -> dict[str, str]:
    out = {}
    for c in record.get("criteria", []):
        if not isinstance(c, dict):
            continue
        name = c.get("name") or c.get("criterion")
        state = (
            "diagnostic" if c.get("diagnostic")
            else "void" if c.get("void")
            else "pass" if c.get("passed") else "fail"
        )
        out[str(name)] = state
    return out


def compare(runs: dict[str, dict]) -> dict:
    """Per-unit against registered, read against the shifted-stream floor."""
    if runs["registered"]["record"]:
        num = {a: leaves(runs[a]["record"]) for a in ARMS}
    else:
        num = {a: stdout_numbers(runs[a]["stdout"]) for a in ARMS}
    # Wall-clock fields differ on every run and say nothing about the rule.
    keys = sorted(
        k for k in set(num["registered"]) & set(num["per_unit"]) & set(num["stream"])
        if "second" not in k and "elapsed" not in k
    )
    moved, rule_beyond_stream = [], []
    for k in keys:
        r, s, u = num["registered"][k], num["stream"][k], num["per_unit"][k]
        du, ds = abs(u - r), abs(s - r)
        if du > 0:
            moved.append(k)
        if du > ds and du > 1e-9 * max(1.0, abs(r)):
            rule_beyond_stream.append(
                {"key": k, "registered": r, "stream": s, "per_unit": u,
                 "rule_move": du, "stream_move": ds}
            )
    rule_beyond_stream.sort(key=lambda e: -e["rule_move"] / max(abs(e["registered"]), 1e-12))
    v = {a: verdicts(runs[a]["record"]) for a in ARMS}
    differ = {
        name: {a: v[a].get(name) for a in ARMS}
        for name in sorted(set(v["registered"]) | set(v["per_unit"]))
        if v["registered"].get(name) != v["per_unit"].get(name)
        or v["registered"].get(name) != v["stream"].get(name)
    }
    return {
        "numbers_compared": len(keys),
        "moved_by_per_unit": len(moved),
        "moved_by_stream": sum(
            1 for k in keys if num["stream"][k] != num["registered"][k]
        ),
        "rule_beyond_stream_count": len(rule_beyond_stream),
        "rule_beyond_stream": rule_beyond_stream,
        "verdicts": v,
        "verdicts_that_differ": differ,
        "exit": {a: runs[a]["exit"] for a in ARMS},
    }


def selftest() -> None:
    """The per-unit rule offers k units' worth; the registered one at most one."""
    from a3b_construction import FIXED, construct

    model = construct(0, 10, **{**FIXED, "turnover": 1.0, "holding_period": 1})
    model.units[:] = 0
    model.units[5, 0] = 60
    model.units[5, 1] = 30
    model.units[5, 2] = 10
    reg = _REGISTERED_OFFERS(model)
    per = _per_unit_offers(model)
    assert len(reg) == 3, reg
    assert len(per) == 100, len(per)
    # The swap is undone even when the run raises.
    with contextlib.suppress(RuntimeError), rule("per_unit"):
        raise RuntimeError
    assert A3Model._offers is _REGISTERED_OFFERS
    with rule("stream"):
        assert A3Model.__init__ is _shifted_init
    assert A3Model.__init__ is _REGISTERED_INIT
    print("selftest: per-holding 3 offers, per-unit 100, swaps restored")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=[*STAGES, "all"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    stages = list(STAGES) if args.stage == "all" else [args.stage]
    record = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    record.setdefault("stage", "resale_rule_probe")
    record.setdefault("arms", {
        "registered": "the rule in src/monetary_topology/asset.py",
        "stream": "the registered rule with the asset stream shifted by one seed",
        "per_unit": "one draw per unit held, Binomial(k, tau) offers from a holding of k",
    })
    record.setdefault("stages", {})
    # Not removed afterwards: the drivers' scratch records stay for inspection.
    scratch = Path(tempfile.mkdtemp(prefix="resale_rule_probe_"))
    print(f"scratch records in {scratch}")
    if True:
        for stage in stages:
            runs = {}
            for arm in ARMS:
                print(f"  {stage}: {arm}", flush=True)
                runs[arm] = run_stage(stage, arm, scratch)
            result = compare(runs)
            record["stages"][stage] = result
            print(
                f"{stage}: {result['numbers_compared']} numbers, "
                f"{result['moved_by_per_unit']} moved by per-unit, "
                f"{result['moved_by_stream']} by the shifted stream, "
                f"{result['rule_beyond_stream_count']} moved by the rule more "
                f"than by the stream; verdicts that differ: "
                f"{result['verdicts_that_differ'] or 'none'}"
            )
            for e in result["rule_beyond_stream"][:15]:
                print(
                    f"    {e['key']}: {e['registered']:.6g} -> {e['per_unit']:.6g} "
                    f"(stream {e['stream']:.6g})"
                )
            OUT.write_text(
                json.dumps(record, indent=1, sort_keys=True, default=str) + "\n",
                encoding="utf-8", newline="\n",
            )
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
