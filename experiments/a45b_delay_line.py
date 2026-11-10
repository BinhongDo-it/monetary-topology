"""A45b: A45's wage bill read L rounds late, as a delay line on the spending state.

Ruled 2026-09-28. A45's map pays the wage bill out of the spending state, which
carries the second layer's spending of the round before: the bill follows its
signal one round late. This station stretches that one round into L. The
spending state becomes a line of L cells, the newest cell takes the round's
spending, each round shifts the line by one, and the bill reads the oldest
cell. No cell carries mass: A45's mass functional is zero on the spending
state, and it is zero on every cell of the line. At L = 1 the block is A45's
own, bit for bit.

Readings, on A45's five default carriers (A44's control runs, no wall), for
L in {1, 2, 3, 6, 20}:

    the stationary split     each home class's stationary share, against L = 1
    the entry term K         A45's: a class's deviation term when the claims
                             enter it, less the median of its term when they
                             enter each of the other two home classes
    the extra term           each class's deviation term for claims entering
                             each home class, less the same term at L = 1; its
                             slope in the added rounds L - 1, and how far it is
                             from a line and from one entry class to another

A lag that carries no mass moves no stationary share and no entry term: the
extra term is linear in the added rounds and the same for every entry class, so
it cancels out of K's comparison. It is what the claims still in the line are
worth to each class for each added round, per unit injected, and it leaves when
the injection stops.

Criteria (written here, carried in the record):

    A45b-0 instrument   at L = 1 the delay-line block is A45's block bitwise;
                        at L > 1 the bill column sits on the oldest cell, the
                        newest cell holds the spending row, and the line shifts
                        by one, on every carrier
    A45b-1 instrument   on every carrier and every L the stationary vector
                        solves the map, the mass functional is conserved by
                        every column, and the stationary mass adds to one,
                        each within A45's chain tolerance 1e-12
    A45b-2 own_reading  the stationary split and the entry terms do not move
                        with L: every class, every carrier, every L, within
                        1e-12 of L = 1
    A45b-3 own_reading  the extra term is linear in the added rounds and the
                        same for every entry class, within 1e-12

    python experiments/a45b_delay_line.py --selftest   # seeded faults, one per clause
    python experiments/a45b_delay_line.py --run        # criteria, readings, the record
    python experiments/a45b_delay_line.py --run --no-write

Only ``--run`` without ``--no-write`` writes, to results/a45b_delay_line.json.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import a45_duration_levers as a45  # noqa: E402
from a44_occupation_operator import HOME_CLASSES, RESULTS, SEEDS, record_path  # noqa: E402

RECORD = RESULTS / "a45b_delay_line.json"

#: Whether the readings are written into RESULTS.md. While they are not, the
#: record carries ``diagnostic_only`` and a reason.
CLOSED = True

LAGS = (1, 2, 3, 6, 20)
WALL = 0.0

#: A45's chain tolerance (TOL_CHAIN), inherited: every clause here is an
#: identity of the same kind as A45-2's.
TOL = a45.TOL_CHAIN

#: Fixed decimal places for the record: shares, entry terms and slopes are
#: solved directly, as A45's are.
DECIMALS = a45.DECIMALS


# --------------------------------------------------------------------------
# the delay line


class DelayLine:
    """A45's block with its spending state stretched into L cells.

    Three one-line hooks, so that a seeded fault replaces a line rather than a
    copy of the assembly."""

    def _bill_cell(self, m_nodes: int, L: int) -> int:
        return m_nodes + L - 1                      # the bill reads the oldest cell

    def _shift(self) -> float:
        return 1.0                                  # the line keeps what it carries

    def _mass(self, m_nodes: int, m: int) -> np.ndarray:
        ell = np.zeros(m)
        ell[:m_nodes] = 1.0                         # no cell of the line carries mass
        return ell

    def block(self, parts: a45.Parts, L: int) -> tuple[np.ndarray, np.ndarray, int]:
        A = a45.FieldBuilder().matrix(parts)
        n = parts.n
        nodes = parts.live[:-1]
        if parts.live[-1] != n:
            raise AssertionError("A45's block does not end on the spending state")
        m_nodes = nodes.size
        m = m_nodes + L
        B = np.zeros((m, m))
        bill = self._bill_cell(m_nodes, L)
        B[:m_nodes, :m_nodes] = A[np.ix_(nodes, nodes)]
        B[:m_nodes, bill] = A[nodes, n]             # the bill, paid to the nodes
        B[m_nodes, :m_nodes] = A[n, nodes]          # the round's spending, into the newest cell
        B[m_nodes, bill] += A[n, n]                 # the bill's own spending, into the newest cell
        for k in range(1, L):
            B[m_nodes + k, m_nodes + k - 1] = self._shift()
        return B, self._mass(m_nodes, m), m_nodes


def layout_ok(parts: a45.Parts, line: DelayLine) -> dict:
    """A45b-0 on one carrier."""
    ref = a45.FieldBuilder().block(parts)
    B1, _, _ = line.block(parts, 1)
    equal = bool(B1.shape == ref.shape and np.array_equal(B1, ref))
    A = a45.FieldBuilder().matrix(parts)
    nodes = parts.live[:-1]
    n = parts.n
    placed = True
    for L in LAGS:
        if L == 1:
            continue
        B, _, m0 = line.block(parts, L)
        oldest = m0 + L - 1
        others = [m0 + k for k in range(L - 1)]
        placed &= bool(np.array_equal(B[:m0, oldest], A[nodes, n]))
        placed &= bool(not np.any(B[:m0, others]))
        placed &= bool(np.array_equal(B[m0, :m0], A[n, nodes]))
        placed &= bool(all(B[m0 + k, m0 + k - 1] == 1.0 for k in range(1, L)))
    return {"seed": parts.seed, "equal_at_1": equal, "placed": placed}


def readings(parts: a45.Parts, L: int, line: DelayLine) -> dict:
    B, ell, m_nodes = line.block(parts, L)
    pi = a45.stationary(B, ell)
    dev = a45.deviation_matrix(B, pi, ell)
    pos = a45.block_positions(parts)
    columns = {}
    for t in HOME_CLASSES:
        v = np.zeros(B.shape[0])
        v[pos[t]] = 1.0 / pos[t].size
        d = dev @ v
        columns[t] = {c: float(d[pos[c]].sum()) for c in HOME_CLASSES}
    split = {c: float(a45.floored(pi)[pos[c]].sum()) for c in HOME_CLASSES}
    return {"columns": columns, "split": split, "K": a45.entry_terms(columns),
            "stationary_err": float(np.abs(B @ pi - pi).max()),
            "conserve_err": float(np.abs(ell @ B - ell).max()),
            "mass_err": abs(float(ell @ pi) - 1.0),
            "line_mass": float(np.sum(pi[m_nodes:]))}


def carrier_row(parts: a45.Parts, line: DelayLine) -> dict:
    res = {L: readings(parts, L, line) for L in LAGS}
    base = res[1]
    d_split = max(abs(res[L]["split"][c] - base["split"][c]) for L in LAGS for c in HOME_CLASSES)
    d_K = max(abs(res[L]["K"][c] - base["K"][c]) for L in LAGS for c in HOME_CLASSES)
    xs = np.array([L - 1 for L in LAGS], dtype=float)
    slope, per_entry, nonlin, spread = {}, {}, 0.0, 0.0
    for c in HOME_CLASSES:
        per_t = {}
        for t in HOME_CLASSES:
            ys = np.array([res[L]["columns"][t][c] - base["columns"][t][c] for L in LAGS])
            b = float(ys[-1] / xs[-1])
            nonlin = max(nonlin, float(np.max(np.abs(ys - b * xs))))
            per_t[t] = b
        per_entry[c] = per_t
        spread = max(spread, max(per_t.values()) - min(per_t.values()))
        slope[c] = statistics.median(per_t.values())
    return {
        "seed": parts.seed, "wall": parts.wall,
        "K": base["K"], "split": base["split"], "slope": slope, "slope_by_entry": per_entry,
        "slope_sum": sum(slope.values()),
        "d_split": d_split, "d_K": d_K, "nonlinearity": nonlin, "entry_spread": spread,
        "stationary_err": max(r["stationary_err"] for r in res.values()),
        "conserve_err": max(r["conserve_err"] for r in res.values()),
        "mass_err": max(r["mass_err"] for r in res.values()),
        "line_mass": {L: res[L]["line_mass"] for L in LAGS},
    }


# --------------------------------------------------------------------------
# criteria


def criteria(layout: list[dict], rows: list[dict]) -> list[dict]:
    out = []
    bad0 = [r for r in layout if not (r["equal_at_1"] and r["placed"])]
    out.append(dict(
        name="A45b-0  the delay line at L = 1 is A45's block, and at L > 1 the bill reads the oldest cell",
        kind="instrument", passed=bool(layout) and not bad0,
        detail=("Void: no carriers, nothing was evaluated" if not layout else
                f"On {len(layout)} carriers the L = 1 block equals A45's bitwise; at L in "
                f"{list(LAGS[1:])} the bill column sits on the oldest cell, the newest cell holds "
                f"the spending row and the line shifts by one." if not bad0 else
                "Fails on " + "; ".join(f"seed {r['seed']} equal {r['equal_at_1']} placed {r['placed']}"
                                        for r in bad0))))
    bad1 = [r for r in rows if not (r["stationary_err"] <= TOL and r["conserve_err"] <= TOL
                                    and r["mass_err"] <= TOL)]
    out.append(dict(
        name="A45b-1  the stationary vector solves each delay-line map, which conserves the mass functional",
        kind="instrument", passed=bool(rows) and not bad1,
        detail=("Void: no carriers, nothing was evaluated" if not rows else
                f"On {len(rows)} carriers and L in {list(LAGS)}: the stationary vector solves the "
                f"map, every column conserves the mass functional and the stationary mass adds to "
                f"one, each within {TOL:.0e}." if not bad1 else
                "Fails on " + "; ".join(f"seed {r['seed']} stationary {r['stationary_err']:.1e} "
                                        f"conserve {r['conserve_err']:.1e} mass {r['mass_err']:.1e}"
                                        for r in bad1))))
    bad2 = [r for r in rows if not (r["d_split"] <= TOL and r["d_K"] <= TOL)]
    out.append(dict(
        name="A45b-2  the lag moves no stationary share and no entry term",
        kind="own_reading", passed=bool(rows) and not bad2,
        detail=("Void: no carriers, nothing was evaluated" if not rows else
                f"On {len(rows)} carriers and L in {list(LAGS)}: every class's stationary share and "
                f"entry term is within {TOL:.0e} of its value at L = 1." if not bad2 else
                "Fails on " + "; ".join(f"seed {r['seed']} split {r['d_split']:.1e} K {r['d_K']:.1e}"
                                        for r in bad2))))
    bad3 = [r for r in rows if not (r["nonlinearity"] <= TOL and r["entry_spread"] <= TOL)]
    out.append(dict(
        name="A45b-3  the extra term is linear in the added rounds and the same for every entry class",
        kind="own_reading", passed=bool(rows) and not bad3,
        detail=("Void: no carriers, nothing was evaluated" if not rows else
                f"On {len(rows)} carriers: the extra term is within {TOL:.0e} of a line in L - 1 "
                f"and of the same value for every entry class. Slopes per round "
                f"of lag and unit injected, medians over carriers: "
                + ", ".join(f"{c} {statistics.median(r['slope'][c] for r in rows):+.4f}"
                            for c in HOME_CLASSES) + "." if not bad3 else
                "Fails on " + "; ".join(f"seed {r['seed']} nonlinearity {r['nonlinearity']:.1e} "
                                        f"spread {r['entry_spread']:.1e}" for r in bad3))))
    return out


# --------------------------------------------------------------------------
# runs


def run_all(line: DelayLine | None = None, seeds=SEEDS) -> dict:
    line = DelayLine() if line is None else line
    parts = [a45.parts_of(record_path(s, WALL)) for s in seeds]
    layout = [layout_ok(p, line) for p in parts]
    rows = [carrier_row(p, line) for p in parts]
    return {"layout": layout, "rows": rows, "criteria": criteria(layout, rows)}


def medians(rows: list[dict]) -> dict:
    med = {c: statistics.median(r["slope"][c] for r in rows) for c in HOME_CLASSES}
    payer_gain = {
        "from_financial_ratio_of_medians": -med["l1"] / med["mid"],
        "from_earners_ratio_of_medians": -med["earners"] / med["mid"],
        "from_financial_median_of_ratios": statistics.median(-r["slope"]["l1"] / r["slope"]["mid"]
                                                             for r in rows),
        "from_earners_median_of_ratios": statistics.median(-r["slope"]["earners"] / r["slope"]["mid"]
                                                           for r in rows),
    }
    return {"slope": med, "payers_gain": payer_gain,
            "K": {c: statistics.median(r["K"][c] for r in rows) for c in HOME_CLASSES},
            "split": {c: statistics.median(r["split"][c] for r in rows) for c in HOME_CLASSES}}


def report(out: dict) -> None:
    rows = out["rows"]
    print("# A45b: A45's wage bill read L rounds late\n")
    print(f"lags {list(LAGS)}; carriers seeds {[r['seed'] for r in rows]}, wall {WALL}")
    print("| seed | K l1 | K mid | K earners | share l1 | share mid | share earners "
          "| slope l1 | slope mid | slope earners | slope sum | max dK | max dsplit | nonlin | spread |")
    print("|" + "---|" * 15)
    for r in rows:
        print(f"| {r['seed']} | " + " | ".join(f"{r['K'][c]:.4f}" for c in HOME_CLASSES) + " | "
              + " | ".join(f"{r['split'][c]:.5f}" for c in HOME_CLASSES) + " | "
              + " | ".join(f"{r['slope'][c]:+.5f}" for c in HOME_CLASSES)
              + f" | {r['slope_sum']:+.1e} | {r['d_K']:.1e} | {r['d_split']:.1e} "
                f"| {r['nonlinearity']:.1e} | {r['entry_spread']:.1e} |")
    med = medians(rows)
    print("\nmedians over carriers: slope " + ", ".join(f"{c} {v:+.4f}" for c, v in med["slope"].items()))
    pg = med["payers_gain"]
    print(f"payers' gain per round of lag: from the financial layer {pg['from_financial_ratio_of_medians']:.3f} "
          f"and from the wage earners {pg['from_earners_ratio_of_medians']:.3f} (ratio of medians); "
          f"{pg['from_financial_median_of_ratios']:.3f} and {pg['from_earners_median_of_ratios']:.3f} "
          f"(median of ratios)")
    print("stationary mass on the line (not counted), seed 0: "
          + ", ".join(f"L={L} {v:.4f}" for L, v in rows[0]["line_mass"].items()))
    print(f"largest residues (printed, not recorded): stationary "
          f"{max(r['stationary_err'] for r in rows):.1e}, conservation "
          f"{max(r['conserve_err'] for r in rows):.1e}, mass {max(r['mass_err'] for r in rows):.1e}, "
          f"split {max(r['d_split'] for r in rows):.1e}, K {max(r['d_K'] for r in rows):.1e}, "
          f"distance from a line {max(r['nonlinearity'] for r in rows):.1e}, entry spread "
          f"{max(r['entry_spread'] for r in rows):.1e}")
    print("\n## Criteria")
    for c in out["criteria"]:
        print(f"- {c['name']} ({c['kind']}): {'PASS' if c['passed'] else 'FAIL'}. {c['detail']}")


# --------------------------------------------------------------------------
# the record


def _clip(x, decimals: int = DECIMALS):
    if x is None or isinstance(x, str):
        return x
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    x = float(x)
    if not math.isfinite(x):
        return None
    y = round(x, decimals)
    return 0.0 if y == 0.0 else y


def _deep(x):
    if isinstance(x, dict):
        return {str(k): _deep(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_deep(v) for v in x]
    return _clip(x)


def _within(value: float) -> dict:
    """A residue within the tolerance is written as the tolerance it was held to."""
    return {"at_most": TOL} if value <= TOL else {"value": float(f"{value:.3e}")}


def build_record(out: dict) -> dict:
    rows = []
    for r in out["rows"]:
        rows.append({
            "seed": r["seed"], "wall": _clip(r["wall"]),
            "K": _deep(r["K"]), "split": _deep(r["split"]), "slope": _deep(r["slope"]),
            "slope_by_entry": _deep(r["slope_by_entry"]),
            "slope_sum": _within(abs(r["slope_sum"])),
            "d_split": _within(r["d_split"]), "d_K": _within(r["d_K"]),
            "nonlinearity": _within(r["nonlinearity"]), "entry_spread": _within(r["entry_spread"]),
            "stationary_err": _within(r["stationary_err"]),
            "conserve_err": _within(r["conserve_err"]), "mass_err": _within(r["mass_err"]),
            "line_mass": _deep(r["line_mass"]),
        })
    rec = {
        "stage": "A45b",
        "config": {
            "carrier": "A45's rebuilt mean field on A44's control runs (a17_edge_cut.base_config)",
            "seeds": list(SEEDS), "wall": WALL, "lags": list(LAGS),
            "delay_line": ("the spending state stretched into L cells: the newest cell takes the "
                           "round's spending row and the bill's own spending, the line shifts by "
                           "one each round, the bill column reads the oldest cell"),
            "mass_functional": "one on trading nodes, zero on every cell of the line",
            "entry_term": "A45's entry_terms on the deviation matrix D = (B - P) Z",
            "extra_term": ("class c's deviation term for claims entering t at L, less the same at "
                           "L = 1; slope = its value at the largest L over L - 1"),
            "tolerance": TOL, "decimals": DECIMALS,
        },
        "criteria": out["criteria"],
        "layout": out["layout"],
        "carriers": rows,
        "medians": _deep(medians(out["rows"])),
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = "Station not closed: the readings are not yet written into RESULTS.md."
    return rec


def serialize(rec: dict) -> str:
    return json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# seeded faults


class _NoBillSpending(DelayLine):
    """Seeded fault: the bill's own spending left out of the newest cell."""

    def block(self, parts, L):
        B, ell, m0 = super().block(parts, L)
        B[m0, self._bill_cell(m0, L)] = 0.0
        return B, ell, m0


class _BillReadsNewest(DelayLine):
    """Seeded fault: the bill reads the newest cell, so no lag is applied."""

    def _bill_cell(self, m_nodes, L):
        return m_nodes


class _LineCarriesMass(DelayLine):
    """Seeded fault: the cells of the line counted as mass."""

    def _mass(self, m_nodes, m):
        return np.ones(m)


class _LeakyLine(DelayLine):
    """Seeded fault: the line loses a tenth of what it carries each round."""

    def _shift(self):
        return 0.9


def selftest() -> int:
    seeds = SEEDS[:2]
    good = run_all(seeds=seeds)
    flags = {c["name"].split()[0]: c["passed"] for c in good["criteria"]}
    checks = [("the default passes every criterion", all(flags.values()))]
    cases = (
        ("bill's own spending dropped", _NoBillSpending(), ("A45b-0",)),
        ("bill reads the newest cell", _BillReadsNewest(), ("A45b-0",)),
        ("line counted as mass", _LineCarriesMass(), ("A45b-1", "A45b-2")),
        ("leaky line", _LeakyLine(), ("A45b-0", "A45b-2", "A45b-3")),
    )
    for label, line, must_fail in cases:
        res = run_all(line=line, seeds=seeds)
        got = {c["name"].split()[0]: c["passed"] for c in res["criteria"]}
        for name in must_fail:
            checks.append((f"{label}: {name} fails", got[name] is False))
    empty = criteria([], [])
    checks.append(("no carriers: every flag fails", all(c["passed"] is False for c in empty)))
    rec = serialize(build_record(good))
    checks.append(("the record serializes the same twice", rec == serialize(build_record(run_all(seeds=seeds)))))
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    n_ok = sum(ok for _, ok in checks)
    print(f"\n{n_ok} of {len(checks)} checks pass")
    return 0 if n_ok == len(checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.run:
        print(__doc__)
        return 2
    out = run_all()
    report(out)
    text = serialize(build_record(out))
    again = serialize(build_record(run_all()))
    if text != again:
        print("the record differs between two computations")
        return 3
    if not args.no_write:
        RECORD.write_text(text, encoding="utf-8", newline="\n")
        same = RECORD.read_bytes() == text.encode("utf-8")
        print(f"\nwrote {RECORD.name} ({len(text.encode('utf-8'))} bytes); read back byte-identical: {same}")
        if not same:
            return 3
    return 0 if all(c["passed"] for c in out["criteria"]) else 1


if __name__ == "__main__":
    sys.exit(main())
