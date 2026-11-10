"""A57: when the three concentration measures go three ways, and what produces it.

A15 found the 1929 shape (the top percentile falling while the top decile and
the Gini rise, from the state after round one to the close) on the arm with no
mechanism at all, at A15's shallow cell (``f2i = 30``, ``e = 0.5``), on one
seed of five. This stage asks how often, and on what.

    rate        the same arm and cell on 1,000 seeds.
    condition   the edge-by-elasticity grid on 200 seeds a cell, and the
                financial-to-intermediate edge count taken past A12's grid to
                where the build rule saturates. That rule gives edge ``i`` to
                the financial node ranked ``i mod 20`` by in-degree and to the
                intermediate node ``i mod 30`` of a permutation, so the pairs
                repeat with period 60 and nothing changes past it.
    mechanism   the top two nodes' share change, split exactly by
                counterparty layer and issuance, round by round; and the same
                for the top decile at the counts where it stops rising.
    cuts        issuance moved off the top node (``injection_target =
                "uniform"``) or switched off (``authority.rule = "none"``),
                both fields the model already has; and the outlet to the
                intermediate block wired by hand to the hubs only, to the
                other eighteen only, or to all twenty, on a graph built at a
                count of zero.

``network.py`` is not changed. The hand-wired outlets patch ``build_graph``
for the one construction and put it back.

    python experiments/a57_shape_conditions.py --gate
    python experiments/a57_shape_conditions.py --selftest
    python experiments/a57_shape_conditions.py --run [--workers N]
    python experiments/a57_shape_conditions.py --tables
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

RECORD = RESULTS / "a57_shape_conditions.json"
A15_SCRIPT = ROOT / "experiments" / "a15_transcribed_vs_implied.py"
A15_RECORD = RESULTS / "a15_transcribed_vs_implied.json"
A54_SCRIPT = ROOT / "experiments" / "a54_penalty.py"
STAGE = "A57"


def _load(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_A15 = _load(A15_SCRIPT, "a15_for_a57")
_A12 = _A15._A12
_A54 = _load(A54_SCRIPT, "a54_for_a57")
r = _A12.r
gini = _A12.gini
top_share = _A12.top_share

ROUNDS = _A15.ROUNDS
CARRIER = _A15.BASE_CARRIER
CELL = (_A15.SHALLOW_F2I, _A15.SHALLOW_ELASTICITY)
EDGES = tuple(_A12.EDGES)
ELASTICITIES = tuple(_A12.ELASTICITIES)
ARM = "off"
SHAPE = (-1, 1, 1)                    # top1, top10, Gini, opening to close
AXIS = tuple(range(20, 62, 2)) + (61, 80)
SATURATION = 60
FLOW_COUNTS = (2, 20, 40, 60)
CUT_COUNTS = {2: 200, 20: 1000, 30: 1000, 40: 200}
CUTS = ("uniform", "noissue")
OUTLETS = {"none": (), "hubs": (0, 1), "rest": tuple(range(2, 20)),
           "all": tuple(range(20))}
OUTLET_SEED_OFFSET = 9001             # buyers for the hand-wired outlets
AMPLIFIER_COUNTS = (22, 26, 30, 40)
AMPLIFIER_EDGES = 4                   # the opening top two hold four outlet edges
TOP10_COUNTS = (30, 40, 50, 60)
SEEDS_CELL, SEEDS_GRID, SEEDS_AXIS, SEEDS_OUTLET, SEEDS_TOP10 = 1000, 200, 200, 1000, 500
LEGS = ("fin", "mid", "hh", "issuance")
VARIANTS = ("base",) + CUTS + tuple("outlet:" + a for a in OUTLETS)


@dataclass
class Criterion:
    name: str
    kind: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "passed": self.passed,
                "detail": self.detail}


# -- the model ---------------------------------------------------------------

def build(f2i: int, e: float, seed: int, variant: str = "base"):
    """A12's ``off`` arm as A15's shallow batch builds it, plus one cut."""
    floor_spec, write_spec, transfer = _A15.shallow_arms()[ARM]
    assert transfer == 0.0
    base = _A12.base_config(f2i, e, ROUNDS, seed, CARRIER)
    cfg = dataclasses.replace(base, subsistence=floor_spec, writeoff=write_spec)
    if variant == "uniform":
        cfg = dataclasses.replace(cfg, injection_target="uniform")
    elif variant == "noissue":
        cfg = dataclasses.replace(
            cfg, authority=dataclasses.replace(cfg.authority, rule="none"))
    elif variant.startswith("outlet:"):
        if f2i != 0:
            raise ValueError("outlet arms are wired on a count of zero")
        return _with_outlets(cfg, OUTLETS[variant.split(":", 1)[1]])
    elif variant != "base":
        raise ValueError(variant)
    return _A12.Network(cfg)


def _with_outlets(cfg, ranks: tuple):
    """One edge into the intermediate block from each financial node at the
    given in-degree ranks, read off the same in-degree the build rule reads
    (payroll points from the intermediate block to households and does not
    touch it)."""
    import monetary_topology.network as net
    orig = net.build_graph

    def patched(spec, wage_edges=None):
        a = orig(spec, wage_edges=wage_edges)
        if spec.uniform_access or not ranks:
            return a
        fin = spec.financial_nodes
        payers = fin[np.argsort(-a.sum(axis=0)[fin], kind="stable")]
        buyers = np.random.default_rng(spec.seed + OUTLET_SEED_OFFSET).permutation(
            spec.intermediate_nodes)
        for j, rk in enumerate(ranks):
            a[payers[rk], buyers[j % buyers.size]] = 1.0
        return a

    net.build_graph = patched
    try:
        return _A12.Network(cfg)
    finally:
        net.build_graph = orig


def measures(H: np.ndarray) -> dict:
    """The six numbers A15 scores, with A12's rounding, on the same instants."""
    n = H.shape[1]
    k1, k10 = max(1, n // 100), max(1, n // 10)
    return {"t1o": r(top_share(H[0], k1)), "t1c": r(top_share(H[-1], k1)),
            "t10o": r(top_share(H[0], k10)), "t10c": r(top_share(H[-1], k10)),
            "go": r(gini(H[0])), "gc": r(gini(H[-1]))}


def _sign(a: float, b: float) -> int:
    return (a > b) - (a < b)


def signs(m: dict) -> tuple:
    return (_sign(m["t1c"], m["t1o"]), _sign(m["t10c"], m["t10o"]),
            _sign(m["gc"], m["go"]))


def _layers(m) -> np.ndarray:
    n = m.holdings.size
    lay = np.zeros(n, dtype=int)              # 0 financial, 1 intermediate, 2 households
    lay[np.asarray(m._mid)] = 1
    lay[np.asarray(m._hh)] = 2
    return lay


def _recording(m, S_holder: list, lay: np.ndarray, acc: dict):
    """Wrap the two flow steps so each round's flows into and out of the set
    in ``S_holder[0]`` are added up by counterparty layer. The set is fixed
    from round one on; round zero is before the opening reading."""
    od, ow = m._discretionary_flow, m._wage_flow
    rnd = [0]

    def add(mat):
        S = S_holder[0]
        if S is None:
            return
        mat = np.asarray(mat, dtype=float)
        for L, name in enumerate(("fin", "mid", "hh")):
            other = (~S) & (lay == L)
            acc[name] += float(mat[np.ix_(other, S)].sum()) - float(mat[np.ix_(S, other)].sum())

    def d():
        mat = od()
        if rnd[0] > 0:
            add(mat)
        rnd[0] += 1
        return mat

    def w():
        mat, bill = ow()
        if rnd[0] > 0:
            add(mat)
        return mat, bill

    m._discretionary_flow, m._wage_flow = d, w


def _split(H: np.ndarray, S: np.ndarray, acc: dict, on_set: float) -> dict:
    """The exact split of the set's share change, opening to close:
    d(share) = [net flows + issuance landing on the set - s0 * issuance] / M."""
    landed = float(H[-1].sum() - H[0].sum())
    s0 = float(H[0, S].sum() / H[0].sum())
    Mc = float(H[-1].sum())
    c = {k: acc[k] / Mc for k in ("fin", "mid", "hh")}
    c["issuance"] = (on_set - s0 * landed) / Mc
    observed = float(H[-1, S].sum() / Mc) - s0
    c["resid"] = abs(sum(c[k] for k in LEGS) - observed) * Mc
    c["issued"] = landed
    return c


def run_one(job: tuple) -> dict:
    """One run. ``what`` is "signs" (the grid and the axis), "top2" (the
    split for the top two) or "top10" (two passes: the first fixes the set)."""
    section, f2i, e, seed, variant, what = job
    m = build(f2i, e, seed, variant)
    lay = _layers(m)
    n = lay.size
    fin, mid = np.asarray(m._l1), np.asarray(m._mid)
    out_mid = m.adjacency[np.ix_(fin, mid)].sum(axis=1)
    row = {"section": section, "f2i": int(f2i), "e": float(e), "seed": int(seed),
           "variant": variant}
    if what == "signs":
        m.run()
        H = np.asarray(m._history.holdings, dtype=float)
        row["s"] = "".join("-0+"[x + 1] for x in signs(measures(H)))
        if f2i >= SATURATION:
            row["digest"] = hashlib.sha1(H.tobytes()).hexdigest()
        return row
    if what == "top10":
        m0 = build(f2i, e, seed, variant)
        m0.run()
        H0 = np.asarray(m0._history.holdings, dtype=float)
        S = np.zeros(n, dtype=bool)
        S[np.argsort(-H0[0], kind="stable")[:max(1, n // 10)]] = True
        holder = [S]
    else:
        holder = [None]
    acc = {"fin": 0.0, "mid": 0.0, "hh": 0.0}
    _recording(m, holder, lay, acc)
    if what == "top2":
        # The top two at the opening reading are known only after round zero
        # closes, so the set is fixed there, before round one's flows.
        steps = m._run_steps()
        for t in steps:
            if t == 0:
                S = np.zeros(n, dtype=bool)
                S[np.argsort(-m.holdings, kind="stable")[:max(1, n // 100)]] = True
                holder[0] = S
        H = np.asarray(m._history.holdings, dtype=float)
        if set(np.argsort(-H[0], kind="stable")[:max(1, n // 100)].tolist()) != set(
                np.flatnonzero(S).tolist()):
            raise AssertionError("the top-two set fixed at round zero is not the opening one")
    else:
        m.run()
        H = np.asarray(m._history.holdings, dtype=float)
        if not np.array_equal(H, H0):
            raise AssertionError("the second pass is not the first")
    S = holder[0]
    landed = float(H[-1].sum() - H[0].sum())
    if m.config.injection_target == "uniform":
        on_set = landed * float(S.sum()) / n
    else:
        on_set = landed if S[m.injection_node] else 0.0
    row.update(measures(H))
    row["s"] = "".join("-0+"[x + 1] for x in signs(row))
    row["set_fin"] = int((S & (lay == 0)).sum())
    pos = {int(f): i for i, f in enumerate(fin)}
    row["set_outlets"] = int(sum(out_mid[pos[int(i)]] for i in np.flatnonzero(S) if int(i) in pos))
    row.update({"c_" + k: v for k, v in _split(H, S, acc, on_set).items()})
    return row


def _jobs() -> list:
    J = []
    for s in range(SEEDS_CELL):
        J.append(("cell", CELL[0], CELL[1], s, "base", "top2"))
    for f in FLOW_COUNTS:
        for s in range(SEEDS_CELL):
            J.append(("flows", f, CELL[1], s, "base", "top2"))
    for f in EDGES:
        for e in ELASTICITIES:
            for s in range(SEEDS_GRID):
                J.append(("grid", f, e, s, "base", "signs"))
    for f in AXIS:
        for s in range(SEEDS_AXIS):
            J.append(("axis", f, CELL[1], s, "base", "signs"))
    for f, ns in CUT_COUNTS.items():
        for v in CUTS:
            for s in range(ns):
                J.append(("cuts", f, CELL[1], s, v, "top2"))
    for a in OUTLETS:
        for s in range(SEEDS_OUTLET):
            J.append(("outlet", 0, CELL[1], s, "outlet:" + a, "top2"))
    for f in AMPLIFIER_COUNTS:
        if f in FLOW_COUNTS or f == CELL[0]:
            continue
        for s in range(SEEDS_CELL):
            J.append(("amplifier", f, CELL[1], s, "base", "top2"))
    for f in TOP10_COUNTS:
        for s in range(SEEDS_TOP10):
            J.append(("top10", f, CELL[1], s, "base", "top10"))
    return J


def run_jobs(jobs: list, workers: int) -> list:
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(run_one, jobs, chunksize=8))


# -- the gate (rule 19) ------------------------------------------------------

GATE_COUNTS = (0, 20, 30, 60)
GATE_SEEDS = (0, 1, 2, 3)
GATE_BITWISE_SEEDS = tuple(range(10))
SIX = ("t1o", "t1c", "t10o", "t10c", "go", "gc")
A12_FIELDS = {"t1o": "top1_open", "t1c": "top1_wealth", "t10o": "top10_open",
              "t10c": "top10_wealth", "go": "gini_open", "gc": "gini_close"}


def _holdings(f2i, e, seed, variant):
    m = build(f2i, e, seed, variant)
    m.run()
    return np.asarray(m._history.holdings, dtype=float), float(
        np.asarray(m._history.issuance, dtype=float).sum())


def _gate_one(job):
    kind, f2i, seed = job
    if kind == "a12":
        row = _A12.one_run(ARM, f2i, CELL[1], ROUNDS, seed, _A15.shallow_arms(), clocks=True)
        H, _ = _holdings(f2i, CELL[1], seed, "base")
        mine = measures(H)
        return {"kind": kind, "f2i": f2i, "seed": seed,
                "same": all(mine[k] == row[A12_FIELDS[k]] for k in SIX)}
    if kind == "outlet":
        a, _ = _holdings(0, CELL[1], seed, "base")
        b, _ = _holdings(0, CELL[1], seed, "outlet:none")
        return {"kind": kind, "f2i": 0, "seed": seed, "same": bool(np.array_equal(a, b))}
    a, issued = _holdings(f2i, CELL[1], seed, "base")
    same = all(np.array_equal(a, _holdings(f2i, CELL[1], seed, v)[0]) for v in CUTS)
    return {"kind": kind, "f2i": f2i, "seed": seed, "same": bool(same),
            "base_issued": issued}


def gate_jobs() -> list:
    J = [("a12", f, s) for f in GATE_COUNTS for s in GATE_SEEDS]
    J += [("outlet", 0, s) for s in GATE_BITWISE_SEEDS]
    J += [("cuts", 40, s) for s in GATE_BITWISE_SEEDS]
    return J


def gate_verdict(rows: list) -> tuple:
    bad = [x for x in rows if not x["same"]]
    issuing = [x for x in rows if x["kind"] == "cuts" and x["base_issued"] != 0.0]
    ok = not bad and not issuing
    detail = ("%d checks: this script's six numbers against A12's own run of the arm "
              "at counts %s, seeds %s; the outlet patch with no edges against the "
              "unpatched graph, bit for bit, seeds 0-%d; both issuance cuts against the "
              "base run at count 40, where the base run issues nothing, bit for bit, "
              "seeds 0-%d. Differing: %d. Base runs at count 40 that issue: %d"
              % (len(rows), list(GATE_COUNTS), list(GATE_SEEDS), GATE_BITWISE_SEEDS[-1],
                 GATE_BITWISE_SEEDS[-1], len(bad), len(issuing)))
    return ok, detail


# -- the criteria -------------------------------------------------------------

def criterion_0(gate: dict | None, rows: list) -> Criterion:
    resid = max((x["c_resid"] / max(1.0, abs(x["c_issued"]) + 100.0)
                 for x in rows if "c_resid" in x), default=None)
    ok = bool(gate and gate.get("verdict") == "pass" and resid is not None and resid < 1e-9)
    return Criterion(
        "A57-0 the arm is A12's, the cuts are clean, and the split closes", "instrument", ok,
        "%s. The share split closes on every decomposed run: largest residual %.2e of the "
        "claim stock" % (gate["detail"] if gate else "no gate section", resid if resid is not None else float("nan")))


def a15_rows() -> list:
    doc = json.loads(A15_RECORD.read_text(encoding="utf-8"))
    return sorted((x for x in doc["runs"] if x.get("batch") == "shallow" and x["arm"] == ARM),
                  key=lambda x: x["seed"])


def criterion_1(cell_rows: list, recorded: list) -> Criterion:
    """A15's five seeds at its cell: the six numbers, and which seeds hit."""
    mine = {x["seed"]: x for x in cell_rows}
    same = sum(all(mine[x["seed"]][k] == x[A12_FIELDS[k]] for k in SIX)
               for x in recorded if x["seed"] in mine)
    rec_hits = [x["seed"] for x in recorded
                if (_sign(x["top1_wealth"], x["top1_open"]), _sign(x["top10_wealth"], x["top10_open"]),
                    _sign(x["gini_close"], x["gini_open"])) == SHAPE]
    my_hits = [s for s in sorted(mine) if s in {x["seed"] for x in recorded} and mine[s]["s"] == "-++"]
    ok = bool(recorded) and same == len(recorded) and my_hits == rec_hits
    return Criterion(
        "A57-1 A15's five seeds at its cell are reproduced", "known_answer", ok,
        "%d of %d recorded rows equal on all six numbers; hits here %s, in A15's record %s"
        % (same, len(recorded), my_hits, rec_hits))


def criterion_2(axis_rows: list) -> Criterion:
    """The build rule repeats its pairs with period 60: counts past it are the run at 60."""
    at = {(x["f2i"], x["seed"]): x["digest"] for x in axis_rows if "digest" in x}
    seeds = sorted({s for f, s in at if f == SATURATION})
    past = sorted({f for f, _ in at if f > SATURATION})
    differ = [(f, s) for f in past for s in seeds if at.get((f, s)) != at[(SATURATION, s)]]
    ok = bool(seeds) and bool(past) and not differ
    return Criterion(
        "A57-2 past 60 edges nothing changes", "instrument", ok,
        "counts %s against %d, %d seeds each, the whole holdings path hashed: %d differ"
        % (past, SATURATION, len(seeds), len(differ)))


def grid_counts(rows: list) -> dict:
    out = {}
    for x in rows:
        k = (x["f2i"], x["e"])
        n, h = out.get(k, (0, 0))
        out[k] = (n + 1, h + (x["s"] == "-++"))
    return out


def criterion_3(grid: dict) -> Criterion:
    """The shape needs the edges into the intermediate block."""
    low = {k: v for k, v in grid.items() if k[0] <= 3}
    top = {k: v for k, v in grid.items() if k[0] == max(EDGES)}
    ok = bool(low) and bool(top) and all(h == 0 for _, h in low.values()) and all(h > 0 for _, h in top.values())
    return Criterion(
        "A57-3 the shape needs edges into the intermediate block", "own_reading", ok,
        "at counts 0 to 3, hits %d in %d runs over %d cells; at %d, hits in every one of "
        "%d cells: %s" % (sum(h for _, h in low.values()), sum(n for n, _ in low.values()),
                          len(low), max(EDGES), len(top),
                          ", ".join("e=%g %d/%d" % (k[1], h, n) for k, (n, h) in sorted(top.items()))))


def falls(rows: list) -> tuple:
    return sum(x["s"][0] == "-" for x in rows), len(rows)


def criterion_4(cut_rows: list, base_rows: list) -> Criterion:
    """Issuance landing on the top node is not what holds the top share up:
    at the smallest count, with it moved or switched off, the top two still
    never lose share."""
    parts, ok = [], bool(cut_rows)
    for v in CUTS:
        d, n = falls([x for x in cut_rows if x["variant"] == v and x["f2i"] == 2])
        ok = ok and n > 0 and d == 0
        parts.append("%s %d/%d" % (v, d, n))
    bd, bn = falls([x for x in base_rows if x["f2i"] == 2 and x["seed"] < CUT_COUNTS[2]])
    ok = ok and bn > 0 and bd == 0
    return Criterion(
        "A57-4 moving or stopping issuance does not produce the fall", "own_reading", ok,
        "top-two share falls at count 2: base %d/%d, %s" % (bd, bn, ", ".join(parts)))


def criterion_5(outlet_rows: list) -> Criterion:
    """Neither the hubs' outlet nor the others' alone produces the fall."""
    c = {a: falls([x for x in outlet_rows if x["variant"] == "outlet:" + a]) for a in OUTLETS}
    ok = all(c[a][1] > 0 for a in OUTLETS) and c["hubs"][0] < c["all"][0] and c["rest"][0] < c["all"][0]
    return Criterion(
        "A57-5 neither outlet alone produces the fall", "own_reading", ok,
        "top-two share falls: " + ", ".join("%s %d/%d" % (a, d, n) for a, (d, n) in c.items()))


def amplifier_rates(rows: list) -> dict:
    out = {}
    for f in AMPLIFIER_COUNTS:
        xs = [x for x in rows if x["f2i"] == f and x["set_outlets"] == AMPLIFIER_EDGES]
        out[f] = falls(xs)
    return out


def criterion_6(rates: dict) -> Criterion:
    """With the top two's own outlet held, the others' outlets amplify."""
    seq = [rates[f][0] / rates[f][1] if rates[f][1] else None for f in AMPLIFIER_COUNTS]
    ok = all(v is not None for v in seq) and all(a < b for a, b in zip(seq, seq[1:]))
    return Criterion(
        "A57-6 with the top two holding %d outlet edges, the fall rises with the others' outlets"
        % AMPLIFIER_EDGES, "own_reading", ok,
        ", ".join("count %d: %d/%d" % (f, *rates[f]) for f in AMPLIFIER_COUNTS))


def variance_shares(rows: list) -> dict:
    C = np.array([[x["c_" + k] for k in LEGS] for x in rows])
    d = C.sum(axis=1)
    if d.size < 2 or d.var() == 0:
        return {}
    return {k: float(np.cov(C[:, i], d)[0, 1] / d.var()) for i, k in enumerate(LEGS)}


def criterion_7(top2: dict, top10: dict) -> Criterion:
    """The leg that moves the share across seeds is the one into the intermediate block."""
    lead = {}
    for tag, shares in (("top two", top2), ("top decile", top10)):
        for f, sh in sorted(shares.items()):
            lead[(tag, f)] = max(sh, key=sh.get) if sh else None
    ok = bool(lead) and all(v == "mid" for v in lead.values())
    return Criterion(
        "A57-7 the intermediate-block leg carries the cross-seed variance of the share change",
        "own_reading", ok,
        "; ".join("%s at %d: largest share %s" % (t, f, v) for (t, f), v in sorted(lead.items())))


EXPECTED = None   # filled in by expected_counts()


def expected_counts() -> dict:
    out = {}
    for j in _jobs():
        out[j[0]] = out.get(j[0], 0) + 1
    return out


def criterion_8(rows: list, expected: dict) -> Criterion:
    got = {}
    for x in rows:
        got[x["section"]] = got.get(x["section"], 0) + 1
    ok = bool(expected) and got == expected
    return Criterion(
        "A57-8 every section is in the record with every run it was planned with", "bookkeeping", ok,
        "rows by section %s, planned %s" % (dict(sorted(got.items())), dict(sorted(expected.items()))))


def analyse(rows: list, gate: dict | None) -> tuple:
    by = {}
    for x in rows:
        by.setdefault(x["section"], []).append(x)
    base_top2 = by.get("cell", []) + by.get("flows", []) + by.get("amplifier", [])
    top2_shares = {f: variance_shares([x for x in base_top2 if x["f2i"] == f])
                   for f in (30, 40, 60)}
    top10_shares = {f: variance_shares([x for x in by.get("top10", []) if x["f2i"] == f])
                    for f in TOP10_COUNTS}
    crits = [
        criterion_0(gate, rows),
        criterion_1(by.get("cell", []), a15_rows()),
        criterion_2(by.get("axis", [])),
        criterion_3(grid_counts(by.get("grid", []))),
        criterion_4(by.get("cuts", []), by.get("flows", [])),
        criterion_5(by.get("outlet", [])),
        criterion_6(amplifier_rates(base_top2)),
        criterion_7(top2_shares, top10_shares),
        criterion_8(rows, expected_counts()),
    ]
    return crits, {"variance_shares": {"top2": top2_shares, "top10": top10_shares}}


# -- the selftest (11f) ------------------------------------------------------

def _fake(section, f2i, s, seed=0, variant="base", **kw):
    row = {"section": section, "f2i": f2i, "e": 0.5, "seed": seed, "variant": variant, "s": s}
    row.update(kw)
    return row


def selftest() -> dict:
    """Each criterion once on an input it must pass, then on one it must fail."""
    out = []

    def check(name, good, bad):
        g, b = good(), bad()
        out.append({"criterion": name, "passes_on_good": g.passed, "fails_on_bad": not b.passed})
        print("   %-6s good %s, seeded fault %s" % (name, "PASS" if g.passed else "FAIL",
                                                   "caught" if not b.passed else "MISSED"))

    rec = [{"seed": s, "top1_open": 0.15, "top1_wealth": 0.14 if s == 3 else 0.16,
            "top10_open": 0.78, "top10_wealth": 0.80, "gini_open": 0.88, "gini_close": 0.89}
           for s in range(5)]
    mine = [{"seed": x["seed"], "t1o": x["top1_open"], "t1c": x["top1_wealth"], "t10o": x["top10_open"],
             "t10c": x["top10_wealth"], "go": x["gini_open"], "gc": x["gini_close"],
             "s": "-++" if x["seed"] == 3 else "+++"} for x in rec]
    bad1 = [dict(x) for x in mine]
    bad1[0]["t1c"] = 0.1600001
    check("A57-1", lambda: criterion_1(mine, rec), lambda: criterion_1(bad1, rec))

    ax = [dict(_fake("axis", f, "+++", s), digest="h%d" % s) for f in (60, 61, 80) for s in range(3)]
    bad2 = [dict(x) for x in ax]
    bad2[4]["digest"] = "other"
    check("A57-2", lambda: criterion_2(ax), lambda: criterion_2(bad2))

    gr = {(f, e): (200, 0 if f <= 3 else 40) for f in EDGES for e in ELASTICITIES}
    bad3 = dict(gr)
    bad3[(1, 0.5)] = (200, 1)
    check("A57-3", lambda: criterion_3(gr), lambda: criterion_3(bad3))

    cuts = [_fake("cuts", 2, "+++", s, v) for v in CUTS for s in range(4)]
    base = [_fake("flows", 2, "+++", s) for s in range(4)]
    bad4 = [dict(x) for x in cuts]
    bad4[-1]["s"] = "-++"
    check("A57-4", lambda: criterion_4(cuts, base), lambda: criterion_4(bad4, base))

    def outl(n_rest):
        rows = []
        for a, d in (("none", 0), ("hubs", 1), ("rest", n_rest), ("all", 5)):
            rows += [_fake("outlet", 0, "-++" if i < d else "+++", i, "outlet:" + a) for i in range(20)]
        return rows
    check("A57-5", lambda: criterion_5(outl(2)), lambda: criterion_5(outl(5)))

    good6 = {22: (6, 100), 26: (11, 100), 30: (19, 100), 40: (31, 100)}     # (falls, runs)
    bad6 = dict(good6)
    bad6[30] = (9, 100)
    check("A57-6", lambda: criterion_6(good6), lambda: criterion_6(bad6))

    sh = {"fin": -5.0, "mid": 30.0, "hh": -24.0, "issuance": 0.0}
    good7 = ({30: sh}, {30: sh})
    bad7 = ({30: sh}, {30: dict(sh, hh=40.0)})
    check("A57-7", lambda: criterion_7(*good7), lambda: criterion_7(*bad7))

    exp = {"cell": 2, "grid": 3}
    rows8 = [_fake("cell", 30, "+++", 0), _fake("cell", 30, "+++", 1)] + [_fake("grid", 0, "+++", s) for s in range(3)]
    check("A57-8", lambda: criterion_8(rows8, exp), lambda: criterion_8(rows8[:-1], exp))

    g0 = {"verdict": "pass", "detail": "fixture"}
    split_ok = [_fake("cell", 30, "+++", 0, c_resid=1e-11, c_issued=0.0)]
    split_bad = [_fake("cell", 30, "+++", 0, c_resid=1e-3, c_issued=0.0)]
    check("A57-0", lambda: criterion_0(g0, split_ok), lambda: criterion_0(g0, split_bad))

    gate_ok = [{"kind": "a12", "same": True}, {"kind": "cuts", "same": True, "base_issued": 0.0}]
    gate_bad = [{"kind": "a12", "same": True}, {"kind": "cuts", "same": True, "base_issued": 0.25}]
    g, b = gate_verdict(gate_ok)[0], gate_verdict(gate_bad)[0]
    out.append({"criterion": "gate", "passes_on_good": g, "fails_on_bad": not b})
    print("   %-6s good %s, seeded fault %s" % ("gate", "PASS" if g else "FAIL", "caught" if not b else "MISSED"))

    held = sum(x["passes_on_good"] and x["fails_on_bad"] for x in out)
    return {"checks": out, "held": held, "of": len(out),
            "verdict": "pass" if held == len(out) else "fail"}


# -- the record ----------------------------------------------------------------

ROW_FIELDS = ("section", "variant", "f2i", "e", "seed", "s", "t1o", "t1c", "t10o", "t10c",
              "go", "gc", "set_fin", "set_outlets", "c_fin", "c_mid", "c_hh", "c_issuance",
              "c_resid", "c_issued", "digest")


def table(rows: list) -> dict:
    return {"fields": list(ROW_FIELDS),
            "rows": [[x.get(k) for k in ROW_FIELDS] for x in rows]}


def untable(t: dict) -> list:
    return [{k: v for k, v in zip(t["fields"], row) if v is not None} for row in t["rows"]]


def station_config() -> dict:
    return {
        "carrier": dataclasses.asdict(CARRIER), "rounds": ROUNDS, "arm": ARM,
        "arm_spec": "A12's arm with every mechanism off, as A15's shallow batch builds it",
        "cell": {"f2i": CELL[0], "elasticity": CELL[1]},
        "shape": "top1 down, top10 up, Gini up, holdings[0] to holdings[-1], on A12's rounding",
        "seeds": {"cell": SEEDS_CELL, "grid": SEEDS_GRID, "axis": SEEDS_AXIS,
                  "cuts": CUT_COUNTS, "outlet": SEEDS_OUTLET, "top10": SEEDS_TOP10},
        "edges": list(EDGES), "elasticities": list(ELASTICITIES), "axis": list(AXIS),
        "flow_counts": list(FLOW_COUNTS), "amplifier_counts": list(AMPLIFIER_COUNTS),
        "top10_counts": list(TOP10_COUNTS), "outlets": {k: list(v) for k, v in OUTLETS.items()},
        "outlet_buyer_seed_offset": OUTLET_SEED_OFFSET,
        "cuts": {"uniform": "injection_target = 'uniform'", "noissue": "authority.rule = 'none'"},
    }


def write_record(section: str, payload: dict) -> None:
    doc = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    doc["stage"] = STAGE
    doc["config"] = _A54._fmt(station_config())
    doc.setdefault("sections", {})[section] = _A54._fmt(payload)
    RECORD.write_text(_A54._dump(doc), encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


def _print(crits: list) -> None:
    for c in crits:
        print("  [%s] %s (%s)\n         %s" % ("PASS" if c.passed else "FAIL", c.name, c.kind, c.detail))


def tables() -> int:
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    run = doc["sections"]["run"]
    rows = untable(run["rows"])
    by = {}
    for x in rows:
        by.setdefault(x["section"], []).append(x)
    print("criteria: " + ", ".join("%s %s" % (c["name"].split()[0], "PASS" if c["passed"] else "FAIL")
                                    for c in run["criteria"]))
    cell = by["cell"]
    print("\n### the cell, %d seeds\nhits %d; sign triples (top1, top10, Gini): %s" % (
        len(cell), sum(x["s"] == "-++" for x in cell), _count(x["s"] for x in cell)))
    print("opening top two all financial: %d of %d" % (sum(x["set_fin"] == 2 for x in cell), len(cell)))
    print("\n### hit rate, edges by elasticity, %d seeds a cell" % SEEDS_GRID)
    g = grid_counts(by["grid"])
    print("f2i   " + "  ".join("%6g" % e for e in ELASTICITIES))
    for f in EDGES:
        print("%-5d " % f + "  ".join("%6.3f" % (g[(f, e)][1] / g[(f, e)][0]) for e in ELASTICITIES))
    print("\n### the axis, e = %g, %d seeds a count" % (CELL[1], SEEDS_AXIS))
    print("f2i  hit    top1 down  top10 up  Gini up")
    for f in AXIS:
        xs = [x for x in by["axis"] if x["f2i"] == f]
        print("%-4d %.3f  %.3f      %.3f     %.3f" % (f, sum(x["s"] == "-++" for x in xs) / len(xs),
              sum(x["s"][0] == "-" for x in xs) / len(xs), sum(x["s"][1] == "+" for x in xs) / len(xs),
              sum(x["s"][2] == "+" for x in xs) / len(xs)))
    base_top2 = by["cell"] + by["flows"] + by["amplifier"]
    print("\n### the top two's share change, split by leg (share units over the run), base arm")
    print("f2i  seeds  top1 down  " + "  ".join("%-9s" % k for k in LEGS) + "  issuing runs")
    for f in sorted({x["f2i"] for x in base_top2}):
        xs = [x for x in base_top2 if x["f2i"] == f]
        print("%-4d %5d  %.3f      " % (f, len(xs), sum(x["s"][0] == "-" for x in xs) / len(xs)) +
              "  ".join("%+.4f  " % np.mean([x["c_" + k] for x in xs]) for k in LEGS) +
              "  %d" % sum(x["c_issued"] > 0 for x in xs))
    print("\n### variance of the share change carried by each leg")
    for tag, shares in run["analysis"]["variance_shares"].items():
        for f, sh in sorted(shares.items(), key=lambda kv: int(kv[0])):
            print("%-5s at %s: %s" % (tag, f, "  ".join("%s %+.2f" % (k, sh[k]) for k in LEGS)))
    print("\n### issuance cuts, same seeds as the base rows")
    print("f2i  variant   seeds  hit    top1 down  issuing runs")
    for f, ns in CUT_COUNTS.items():
        src = by["cell"] if f == CELL[0] else by["flows"]
        for v, xs in [("base", [x for x in src if x["f2i"] == f and x["seed"] < ns])] + [
                (v, [x for x in by["cuts"] if x["f2i"] == f and x["variant"] == v]) for v in CUTS]:
            print("%-4d %-9s %5d  %.3f  %.3f      %d" % (f, v, len(xs), sum(x["s"] == "-++" for x in xs) / len(xs),
                  sum(x["s"][0] == "-" for x in xs) / len(xs), sum(x["c_issued"] > 0 for x in xs)))
    print("\n### hand-wired outlets, graph built at count 0, %d seeds an arm" % SEEDS_OUTLET)
    print("arm   ranks with an outlet  hit    top1 down  " + "  ".join("%-9s" % k for k in LEGS))
    for a, ranks in OUTLETS.items():
        xs = [x for x in by["outlet"] if x["variant"] == "outlet:" + a]
        print("%-5s %-21s %.3f  %.3f      " % (a, "%d-%d" % (ranks[0], ranks[-1]) if ranks else "-",
              sum(x["s"] == "-++" for x in xs) / len(xs), sum(x["s"][0] == "-" for x in xs) / len(xs)) +
              "  ".join("%+.4f  " % np.mean([x["c_" + k] for x in xs]) for k in LEGS))
    print("\n### the top two's own outlet edges, against the fall")
    print("edges held  f2i  seeds  top1 down")
    for k in sorted({x["set_outlets"] for x in base_top2 if x["f2i"] >= 20}):
        for f in sorted({x["f2i"] for x in base_top2 if x["f2i"] >= 20}):
            xs = [x for x in base_top2 if x["f2i"] == f and x["set_outlets"] == k]
            if xs:
                print("%-10d  %-4d %5d  %.3f" % (k, f, len(xs), sum(x["s"][0] == "-" for x in xs) / len(xs)))
    print("\n### the top decile's share change, split by leg")
    print("f2i  seeds  top10 up  same set up  " + "  ".join("%-9s" % k for k in LEGS))
    for f in TOP10_COUNTS:
        xs = [x for x in by["top10"] if x["f2i"] == f]
        print("%-4d %5d  %.3f     %.3f        " % (f, len(xs), sum(x["s"][1] == "+" for x in xs) / len(xs),
              sum(sum(x["c_" + k] for k in LEGS) > 0 for x in xs) / len(xs)) +
              "  ".join("%+.4f  " % np.mean([x["c_" + k] for x in xs]) for k in LEGS))
    return 0


def _count(it) -> dict:
    out = {}
    for v in it:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--gate", "--selftest", "--run", "--tables"):
        mode.add_argument(flag, action="store_true")
    ap.add_argument("--workers", type=int, default=_A54._default_workers())
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    if args.tables:
        return tables()
    if args.selftest:
        print("stage %s, seeded faults\n" % STAGE)
        s = selftest()
        print("\n   %d of %d held, verdict: %s" % (s["held"], s["of"], s["verdict"]))
        if not args.no_write:
            write_record("selftest", s)
        return 0 if s["verdict"] == "pass" else 1
    if args.gate:
        print("stage %s, rule 19\n" % STAGE)
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            rows = list(ex.map(_gate_one, gate_jobs()))
        ok, detail = gate_verdict(rows)
        print("   " + detail + "\n   verdict: %s" % ("pass" if ok else "fail"))
        if not args.no_write:
            write_record("gate", {"verdict": "pass" if ok else "fail", "detail": detail, "rows": rows})
        return 0 if ok else 1
    doc = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    gate = doc.get("sections", {}).get("gate")
    if not gate or gate.get("verdict") != "pass":
        print("stage %s: not starting, the gate has not passed (run --gate)" % STAGE)
        return 2
    jobs = _jobs()
    print("stage %s: %d runs, %d workers" % (STAGE, len(jobs), args.workers))
    t0 = time.perf_counter()
    rows = run_jobs(jobs, args.workers)
    print("   ran %d runs in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, analysis = analyse(rows, gate)
    _print(crits)
    if not args.no_write:
        write_record("run", {"criteria": [c.as_dict() for c in crits], "analysis": analysis,
                             "rows": table(rows)})
    return 0 if all(c.passed for c in crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
