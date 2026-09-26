"""A40: two graphs started apart and coupled. Which candidate gap closes.

The question this answers a first slice of: when two graphs are joined, is
catch-up a contest of support sets, as an early guess had it? A single-graph
reading already said the support set is not the level and moves against it
(b101_expansion_algebra, X3: log correlation -0.966, ranges disjoint). That was
one graph. This is two.

**This station describes before it tests.** Rule 13 puts the worst cell and the
description first, and the description has not been made: nobody has started
this pair apart and watched. So it prints every candidate gap's path and reads
which close, rather than registering a story and scoring it.

**What it deliberately does not do.** It does not force the field exact. A22
did that on A3's carrier and found the whole holonomy carries `1.33%` of the
support contraction, the graph carrying the rest, so the split between the two
channels is a real question here too. It is registered and not run: A22's
construction is on a different carrier and joining them is its own piece of
work, not a flag on this one.

    python experiments/a40_two_graph_catchup.py --selftest
    python experiments/a40_two_graph_catchup.py --run
"""
from __future__ import annotations

import argparse
import dataclasses as _dc
import importlib.util
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network, NetworkConfig, NetworkSpec)

OUT = ROOT / "results" / "a40_two_graph_catchup.json"

#: A25's pair machinery, imported rather than rewritten so the two stations
#: settle the boundary the same way and the conservation assertion is the same
#: assertion.
_spec = importlib.util.spec_from_file_location(
    "a25", ROOT / "experiments" / "a25_boundary.py")
A25 = importlib.util.module_from_spec(_spec)
# **Register before executing.** ``dataclass`` looks the defining module up in
# ``sys.modules`` to resolve annotations, and a module built by hand is not in
# there yet, so the decorator on ``BoundarySpec`` dies on a None lookup.
sys.modules["a25"] = A25
_spec.loader.exec_module(A25)

ROUNDS = 80
SEEDS = (0, 1, 2, 3, 4)
WIDTHS = (0.0, 0.02, 0.05, 0.10)
#: The lagging side starts with this share of the leading side's claims. One
#: number, and it is the only thing that makes them different at round zero.
LAG = 0.5
TAIL = 15

#: Every candidate for "the gap", named before anything runs. Each is read on
#: both sides and the gap is the log ratio, so a gap that closes goes to zero
#: whatever the units are.
GAPS = {
    "level": lambda h: np.asarray(h.total_volume, float),
    "support": lambda h: np.asarray(h.effective_support, float),
    "active_nodes": lambda h: np.asarray(h.active_nodes, float),
    "layer2_reached": lambda h: np.asarray(h.layer2_reached, float),
    "layer1_volume": lambda h: np.asarray(h.layer1_volume, float),
}


def cfg(seed: int, claims: float) -> NetworkConfig:
    return NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=ROUNDS,
                         initial_claims=claims,
                         authority=MonetaryAuthority(rule="none"))


def gaps_of(g1, g2) -> dict:
    """log(lead) - log(lag) per round, per candidate. Zero is a closed gap."""
    out = {}
    for name, f in GAPS.items():
        a, b = f(g1._history), f(g2._history)
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
        d = np.full(n, np.nan)
        d[ok] = np.log(a[ok]) - np.log(b[ok])
        out[name] = d
    return out


def one_pair(seed: int, width: float):
    base = 100.0
    c_lead = cfg(seed, base)
    c_lag = cfg(seed, base * LAG)
    g1, g2, hist = A25.run_pair(c_lead, c_lag, A25.BoundarySpec(width=width),
                                rounds=ROUNDS)
    return g1, g2, hist, gaps_of(g1, g2)


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    crit, report = [], {}

    # ---- A40-0: width zero is two runs that never met (rule 19)
    worst, fields = 0.0, 0
    for seed in SEEDS[:3]:
        g1, g2, _, _ = one_pair(seed, 0.0)
        for g, claims in ((g1, 100.0), (g2, 100.0 * LAG)):
            solo = Network(cfg(seed, claims)).run()
            for f in _dc.fields(type(solo)):
                a = getattr(solo, f.name, None)
                b = getattr(g._history, f.name, None)
                if a is None or b is None:
                    continue
                try:
                    a, b = np.asarray(a, float), np.asarray(b, float)
                except (TypeError, ValueError):
                    continue
                if a.shape != b.shape:
                    continue
                fields += 1
                d = np.abs(a - b)
                d = d[np.isfinite(d)]
                if d.size:
                    worst = max(worst, float(d.max()))
    report["default_off"] = {"worst_abs_difference": worst, "fields_compared": fields}
    crit.append(_crit(
        "A40-0  the boundary shut is two graphs that never met",
        "instrument", worst < 1e-12,
        f"three seeds, both sides, {fields} history fields compared against the same "
        f"configuration run alone: worst absolute difference {worst:.3e}. Rule 19, and "
        f"it is run rather than argued."))

    # ---- A40-1: the pair conserves. run_pair asserts it every round; this
    #             records that the assertion was live rather than trusting it.
    seeded = 0
    try:
        bad_cfg = cfg(0, 100.0)
        A25.run_pair(bad_cfg, cfg(0, 50.0), A25.BoundarySpec(width=0.05),
                     rounds=4, network_cls=_LeakyNetwork)
    except AssertionError:
        seeded = 1
    crit.append(_crit(
        "A40-1  pair-level conservation, and the check that would catch its absence",
        "instrument", seeded == 1,
        "the pair machinery asserts every round that the two sides' claims sum to what "
        "they summed to before the transfer. A network that quietly loses a thousandth "
        "of its holdings each round was planted and the assertion "
        + ("fired" if seeded else "DID NOT FIRE") +
        ". A check nobody has seen fail is not known to work."))

    # ---- A40-2: which candidate gap closes
    rows, paths = [], {}
    for width in WIDTHS:
        for seed in SEEDS:
            _, _, _, gp = one_pair(seed, width)
            for name, d in gp.items():
                fin = d[np.isfinite(d)]
                if fin.size < TAIL + 2:
                    continue
                rows.append({"width": width, "seed": seed, "gap": name,
                             "open": float(fin[0]),
                             "close": float(np.median(fin[-TAIL:])),
                             "ratio": float(np.median(fin[-TAIL:]) / fin[0])
                                      if abs(fin[0]) > 1e-12 else float("nan")})
            if width == WIDTHS[-1] and seed == 0:
                paths = {k: [None if not np.isfinite(x) else float(x)
                             for x in v] for k, v in gp.items()}
    report["gap_rows"] = rows
    report["path_at_widest_seed0"] = paths

    summary = {}
    for name in GAPS:
        for width in WIDTHS:
            sel = [r for r in rows if r["gap"] == name and r["width"] == width]
            if not sel:
                continue
            o = np.array([r["open"] for r in sel])
            c = np.array([r["close"] for r in sel])
            summary.setdefault(name, {})[str(width)] = {
                "open_median": float(np.median(o)), "close_median": float(np.median(c)),
                "close_sd": float(np.std(c)), "seeds": len(sel)}
    report["gap_summary"] = summary

    # the floor: how much the closing figure moves across seeds at width zero,
    # where nothing crossed and so nothing should have closed
    floors = {n: summary[n]["0.0"]["close_sd"] for n in summary if "0.0" in summary[n]}
    report["floor_seed_sd_at_width_zero"] = floors

    lines = []
    for name in GAPS:
        if name not in summary:
            continue
        s = summary[name]
        o0 = s["0.0"]["open_median"]
        c0 = s["0.0"]["close_median"]
        cw = s[str(WIDTHS[-1])]["close_median"]
        moved = abs(cw - c0)
        lines.append(f"{name}: opens {o0:+.3f}, shut boundary closes to {c0:+.3f}, "
                     f"widest closes to {cw:+.3f}, moved {moved:.3f} against a "
                     f"seed floor of {floors.get(name, float('nan')):.3f}")
    crit.append(_crit(
        "A40-2  which candidate gap the boundary closes",
        "own_reading", None,
        "Void: printed, not adjudicated. This is the description rule 13 puts before "
        "any test, and no criterion was registered on which gap should close. Each gap "
        "is a log ratio of the leading side to the lagging one, so zero is closed "
        "whatever the units. The lagging side starts with "
        f"{LAG:.0%} of the other's claims and nothing else differs. "
        + " | ".join(lines)
        + f". Floor measured, not declared: the seed spread of the closing figure at a "
          f"shut boundary, where nothing crossed."))

    # ---- A40-4: why two of the candidate gaps read exactly zero
    scale_rows, worst_part, ratios = [], 0.0, {}
    base = Network(cfg(0, 100.0)).run()
    for mult in (0.125, 0.5, 2.0, 4.0):
        g = Network(cfg(0, 100.0 * mult)).run()
        row = {"claims_multiple": mult}
        for f in ("active_nodes", "layer2_reached", "total_volume",
                  "effective_support"):
            a = np.asarray(getattr(base, f), float)
            b = np.asarray(getattr(g, f), float)
            n = min(len(a), len(b)); a, b = a[:n], b[:n]
            row[f] = {"max_abs_diff": float(np.abs(a - b).max()),
                      "tail_ratio": float(np.median(b[-TAIL:] /
                                                    np.maximum(a[-TAIL:], 1e-12)))}
            if f in ("active_nodes", "layer2_reached"):
                worst_part = max(worst_part, row[f]["max_abs_diff"])
            else:
                ratios.setdefault(f, []).append((mult, row[f]["tail_ratio"]))
        scale_rows.append(row)
    report["claim_scale"] = scale_rows
    crit.append(_crit(
        "A40-4  the claim stock does not move who takes part, at all",
        "instrument", worst_part == 0.0,
        f"one seed, initial claims over a sixteenfold range ({', '.join(str(r['claims_multiple']) for r in scale_rows)} "
        f"times the reference). Active nodes and the share of the second layer reached "
        f"are bitwise identical at every stock: worst absolute difference "
        f"{worst_part:.4f}. Over the same range the level is sublinear and the support "
        f"set moves the other way: "
        + "; ".join(f"x{m:g} -> volume x{r:.2f}" for m, r in ratios["total_volume"])
        + " against "
        + "; ".join(f"support x{r:.2f}" for _, r in ratios["effective_support"])
        + ". **So a pure difference in the claim stock is invisible in who takes part, "
          "and the level and the support set are two directions rather than one.** "
          "That is why two of the candidate gaps in A40-2 read exactly zero: they have "
          "no object on this axis, which is a property of the module and not a bug."))

    crit.append(_crit(
        "A40-3  what is registered and not run", "bookkeeping", True,
        "the field-exact arm. A22 forced w = d phi on A3's carrier and read that the "
        "whole holonomy carries 1.33% of the support contraction there, the graph "
        "carrying the rest. Whether catch-up splits the same way between the two "
        "channels is the question this station opens and does not answer: A22's "
        "construction sits on a different carrier and joining the two is its own piece "
        "of work. Registered here so the next session does not re-derive the need."))

    record = {"stage": "A40",
              "config": {"rounds": ROUNDS, "seeds": list(SEEDS), "widths": list(WIDTHS),
                         "lag_share_of_claims": LAG, "tail": TAIL,
                         "authority": "none, so neither side can issue its way across",
                         "gaps": list(GAPS), "pair_machinery": "a25_boundary.run_pair",
                         "boundary_swing": A25.SWING_HISTORICAL},
              "criteria": crit, "report": report}
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:520]}\n")
    print("  gap medians by boundary width (log lead over lag, 0 is closed)")
    print(f"     {'gap':>15}  {'open':>8} " + " ".join(f"{('w=%g' % w):>9}" for w in WIDTHS))
    for name in GAPS:
        if name not in summary:
            continue
        s = summary[name]
        print(f"     {name:>15}  {s['0.0']['open_median']:>8.3f} "
              + " ".join(f"{s[str(w)]['close_median']:>9.3f}" for w in WIDTHS))
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\nrecord -> {OUT.relative_to(ROOT)}")
    return 1 if [c for c in crit if c["passed"] is False] else 0


class _LeakyArray(np.ndarray):
    """Loses a thousandth on every in-place subtraction.

    The transfer in the pair machinery is written as ``g1.holdings -= share``,
    so this is a fault at exactly the layer the assertion guards. A first plant
    shrank the holdings inside each graph's own step instead, and the assertion
    did not fire, correctly: **its window is the transfer, not the round.**
    Neither graph conserves on its own here, so a round-level check is not
    available and was not pretended to be.
    """

    def __isub__(self, other):
        return np.ndarray.__isub__(self, np.asarray(other) * 1.001)


class _LeakyNetwork(Network):
    """Plants the fault A40-1's assertion exists to catch (11f)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.holdings = self.holdings.view(_LeakyArray)


def selftest():
    ok = []
    g1, g2, _, gp = one_pair(0, 0.0)
    d = gp["level"]
    fin = d[np.isfinite(d)]
    ok.append(abs(fin[0] - np.log(1 / LAG)) < 0.5)
    print(f"  the pair really starts apart -> opening level gap {fin[0]:+.3f} "
          f"(log(1/{LAG}) = {np.log(1/LAG):+.3f})")

    # a gap that must NOT close: the boundary shut
    shut = float(np.median(fin[-TAIL:]))
    _, _, _, gw = one_pair(0, WIDTHS[-1])
    fw = gw["level"][np.isfinite(gw["level"])]
    wide = float(np.median(fw[-TAIL:]))
    ok.append(abs(shut - fin[0]) < abs(fin[0]))
    print(f"  shut boundary, level gap  -> {shut:+.3f}   widest -> {wide:+.3f}")
    ok.append(abs(wide) < abs(shut))
    print(f"  opening it closes the level gap: {abs(wide) < abs(shut)}")

    try:
        A25.run_pair(cfg(0, 100.0), cfg(0, 50.0), A25.BoundarySpec(width=0.05),
                     rounds=4, network_cls=_LeakyNetwork)
        fired = False
    except AssertionError:
        fired = True
    ok.append(fired)
    print(f"  planted leak trips the conservation assertion: {fired}")

    print(f"selftest: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(selftest() if a.selftest else run(write=not a.no_write))
