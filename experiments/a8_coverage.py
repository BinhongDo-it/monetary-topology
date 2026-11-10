"""A8: the coverage test. Four surfaces read off one parameter curve.

Volume One section 13 asks whether demand collapse, SMB death, the wage
paradox and the consuming-power leak reduce to one topological fact rather
than to four separate villains. Operationally: does a single parameter vector
put all four surfaces on the table at once, and does widening one edge take
all four off it.

The grid is not chosen here. Every number below is imported from
``a2_support_contraction`` so the curve is reported over a grid that was fixed
before this stage existed, which is the form ``docs/a3_restated.md`` requires:
report the curve and ask whether any single setting satisfies several mutually
independent surfaces. Selecting a setting because it lands where one wants it
is what that document forbids.

Usage::

    python experiments/a8_coverage.py
    python experiments/a8_coverage.py --rounds 600 --seeds 5

Writes ``results/a8_coverage.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import A3Config, A3Model, AssetSpec
from monetary_topology.config import WageChannel
from monetary_topology.mechanisms import gini
from monetary_topology.network import (
    Network,
    NetworkConfig,
    NetworkSpec,
    scaled_carrier,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

#: Claims are conserved exactly up to floating point. Same constant and same
#: meaning as ``economy.py``'s ``SFC_TOLERANCE``.
#:
#: The graph model does assert inside its own loop, at ``network.py``'s
#: ``raise AssertionError`` on the flow stage, but that assertion spans the
#: payroll and discretionary transfers only: issuance lands before it and the
#: ``_post_round`` hook runs after it, which is where A3's asset settlement
#: sits. The identity checked here is read on every recorded row, which covers
#: issuance in every round and every settlement but the last, because a round's
#: row is written before its hook runs; and it is read once more on the state
#: the run is left in, which covers the last (``read_run``).
SFC_TOLERANCE = 1e-9

#: Decimal places every reported float is rounded to before it is written.
#: Fixed here rather than left to ``repr`` so two BLAS builds cannot differ in
#: the last digit and surface as a text diff.
#:
#: **It is also the resolution the surfaces are read at**, because they are read
#: off the rounded row. A positive ratio under ``5e-7`` of its opening value
#: reads zero. ``rounding_report`` lists every flag that decides.
DIGITS = 6


def _a2_grid() -> tuple[dict, str]:
    """Load A2's registered grid from its own file, or fall back to a copy.

    Reported either way. A failure here does not stop the run: the constants
    this reads feed criterion A8-1 and nothing else, so a missing file is
    something to print, not something to halt on.
    """
    path = ROOT / "experiments" / "a2_support_contraction.py"
    try:
        spec = importlib.util.spec_from_file_location("_a2", path)
        if spec is None or spec.loader is None:
            raise ImportError("no loader")
        mod = importlib.util.module_from_spec(spec)
        # Register before executing. ``dataclass`` looks the defining module up
        # in ``sys.modules`` while it processes annotations, and a module built
        # by hand is not there yet, so a file holding a dataclass fails to
        # execute with an AttributeError that names neither.
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return (
            {
                "AUTONOMOUS_EDGES": tuple(mod.AUTONOMOUS_EDGES),
                "ELASTICITIES": tuple(mod.ELASTICITIES),
                "INTERMEDIATE_SIZE": int(mod.INTERMEDIATE_SIZE),
                "TAIL": int(mod.TAIL),
            },
            "imported from experiments/a2_support_contraction.py",
        )
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return (
            {
                "AUTONOMOUS_EDGES": (0, 1, 2, 3, 5, 8, 12, 20, 30),
                "ELASTICITIES": (0.0, 0.5, 0.9, 0.99, 1.0),
                "INTERMEDIATE_SIZE": 30,
                "TAIL": 25,
            },
            f"fallback copy, import failed: {type(exc).__name__}",
        )


GRID, GRID_SOURCE = _a2_grid()
AUTONOMOUS_EDGES = GRID["AUTONOMOUS_EDGES"]
ELASTICITIES = GRID["ELASTICITIES"]
INTERMEDIATE_SIZE = GRID["INTERMEDIATE_SIZE"]
TAIL = GRID["TAIL"]

#: Production side held at 180 nodes with the intermediate carved out of it,
#: exactly as A2's ``three_layer`` does. The block is inside Layer 2, not a
#: fourth category, which is what ``NetworkSpec.layer2`` already states.
PRODUCTION_SIZE = 180

#: Layer 1's size, restated here rather than left to ``NetworkSpec``'s default.
#: Scaling the carrier needs a base to scale from, and a default resolved at
#: call time is not one.
LAYER1_SIZE = 20

#: The node count A2's grid was registered at.
BASE_NODES = LAYER1_SIZE + PRODUCTION_SIZE


@dataclass(frozen=True)
class Carrier:
    """Three block sizes and the autonomous-edge grid, at one node count.

    **The grid is not the same list of numbers at every size, and that is not
    a choice made here.** ``financial_to_intermediate_edges`` is a *count*,
    while the quantity it stands for is a *share*: how much of the intermediate
    block's opening inflow arrives from the layer above. That share is A2's
    counterpart of A0b's object, the autonomous term ``W0 (1 - e)`` of the
    two-layer wage rule: each is the part of the payer's funding that does not
    depend on the households its payroll pays (``network.autonomous_share``
    gives the full correspondence). The share is not
    linear in the count, so carrying the same counts to a larger carrier would
    carry a different curve. Each count is therefore solved, one bisection per
    grid point, to land on the share that grid point had at ``BASE_NODES``.

    At ``BASE_NODES`` the solve is skipped and the registered numbers are
    returned as they stand, so a run that does not ask for a size is running
    the code path this stage always ran.
    """

    nodes: int
    layer1_size: int
    intermediate_size: int
    layer2_size: int
    edges: tuple[int, ...]
    #: Whether A3's asset layer rides on top. Off is the carrier this stage
    #: was registered on and the one every downstream stage inherited.
    #:
    #: **It is a carrier and not a config field**, because the asset layer is
    #: a subclass rather than a switch: ``A3Model`` wraps the same
    #: ``NetworkConfig`` and settles an asset market inside ``_post_round``.
    #: So it travels here, beside the block sizes, rather than in ``ARMS``.
    #:
    #: **Why it exists.** Every reading this stage and its dependants make
    #: about concentration is made on a carrier with no asset revaluation,
    #: and revaluation is the channel the empirical literature puts the
    #: weight on: Montecino and Epstein (version of 24 April 2017, Table 2)
    #: find rising equity returns contribute +6.3 percentage points to the
    #: change in the 95/10 ratio of household net income against -0.4 from
    #: the employment channel, and +4.1 against -0.5 on the 90/10 ratio.
    #: Their ratio is of net income and the readings here are of claim
    #: balances, so the paper ranks the channels and supplies no number to
    #: match. Measured here, the subsistence arm's closing Gini
    #: moves -0.3086 without the asset layer and +0.0772 with it, and the
    #: top one percent share -0.1329 against +0.0436. **Six readings change
    #: sign.** A stage that reports only one of the two carriers is
    #: reporting one channel and calling it the world.
    asset: bool = False

    @property
    def resized(self) -> bool:
        """The block sizes moved, so the edge grid was solved."""
        return self.nodes != BASE_NODES

    @property
    def rescaled(self) -> bool:
        """Not the registered carrier, for any reason.

        Two reasons and they are not the same reason, which is why
        ``resized`` exists beside this: a run with the asset layer on at two
        hundred nodes solved nothing, and a line saying its counts were
        solved would be false. Written after that line printed.
        """
        return self.resized or self.asset

    @property
    def tag(self) -> str:
        """Filename suffix. Empty for the registered carrier."""
        bits = []
        if self.nodes != BASE_NODES:
            bits.append(f"n{self.nodes}")
        if self.asset:
            bits.append("asset")
        return ("_" + "_".join(bits)) if bits else ""


def carrier_at(nodes: int, asset: bool = False) -> Carrier:
    """The carrier at ``nodes``. ``BASE_NODES`` and no asset layer is the
    registered one, and returns the registered numbers untouched.
    """
    sizes, edges = scaled_carrier(
        nodes,
        base_nodes=BASE_NODES,
        base_layer1=LAYER1_SIZE,
        base_intermediate=INTERMEDIATE_SIZE,
        base_edges=AUTONOMOUS_EDGES,
    )
    return Carrier(nodes=nodes, edges=edges, asset=asset, **sizes)


#: The registered carrier. Every function below takes it as the default, so a
#: caller that never mentions a size cannot reach the scaling code at all.
BASE = carrier_at(BASE_NODES)


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def r(x: float) -> float:
    return round(float(x), DIGITS)


def tail_mean(x: np.ndarray) -> float:
    return float(np.asarray(x, dtype=float)[-TAIL:].mean())


def build_model(
    f2i: int,
    elasticity: float,
    rounds: int,
    seed: int,
    carrier: Carrier = BASE,
):
    """The model for one configuration, constructed and not run.

    ``Network(cfg)`` is exactly what ``run_network`` constructs, so the
    registered carrier takes the path it always took. The model is kept, where
    ``run_network`` handed back only the history, because the state a run is
    left in after its last round is in no history row (``read_run``).
    """
    spec = NetworkSpec(
        seed=seed,
        layer1_size=carrier.layer1_size,
        intermediate_size=carrier.intermediate_size,
        layer2_size=carrier.layer2_size,
        financial_to_intermediate_edges=f2i,
    )
    cfg = NetworkConfig(
        spec=spec,
        rounds=rounds,
        seed=seed,
        wages=WageChannel(elasticity=elasticity),
    )
    return (
        A3Model(A3Config(asset=AssetSpec(), network=cfg))
        if carrier.asset
        else Network(cfg)
    )


def order(x: float) -> int | None:
    """``floor(log10(x))`` for a positive ``x``, and ``None`` for zero or below.

    Written only for values that read zero at ``DIGITS`` places. Their digits
    are decided by accumulation order and differ between BLAS builds; their
    order of magnitude does not.
    """
    return int(math.floor(math.log10(x))) if x > 0.0 else None


def one_run(
    f2i: int,
    elasticity: float,
    rounds: int,
    seed: int,
    carrier: Carrier = BASE,
) -> dict:
    """One configuration, read on the four surfaces.

    Every reading is a ratio against the same run's own opening value, so no
    cross-configuration normalisation enters and nothing is scaled by a number
    chosen here.
    """
    model = build_model(f2i, elasticity, rounds, seed, carrier)
    return read_run(model, model.run(), f2i, elasticity, seed)


def read_run(model, h, f2i: int, elasticity: float, seed: int) -> dict:
    """The row for one run, from the history it wrote and the state it left."""
    m = h.total_claims
    expected = h.total_claims[0] + np.cumsum(h.issuance)
    conserved = float(np.abs(m - expected).max())
    # A round's row is written before that round's ``_post_round`` hook, which
    # is where A3's asset settlement sits. A settlement that made or lost
    # claims would show in the next round's row, and the last round has no next
    # row. The state the model is left in is read for that one.
    closed = abs(
        float(np.asarray(model.holdings, dtype=float).sum()) - float(expected[-1])
    )
    owed0 = float(h.wage_owed[0])

    # Unrounded first. The surfaces are read off the rounded values, as
    # registered, and once more off these, so that the record says where the
    # rounding decides a flag (``rounding_report``).
    raw = {
        "mr_ratio": float(h.total_ratio[-1] / h.total_ratio[0]),
        "mara_ratio": float(tail_mean(h.active_ratio) / h.active_ratio[0]),
        "m_ratio": float(m[-1] / m[0]),
        "gini_open": float(gini(h.holdings[0])),
        "gini_close": float(gini(h.holdings[-1])),
        "resource_levels": int(np.unique(h.total_resources).size),
        "support_ratio": float(
            tail_mean(h.effective_support) / h.effective_support[0]
        ),
        "wage_funding": float(tail_mean(h.wage_funding_ratio)),
        "wage_owed_ratio": float(
            tail_mean(h.wage_owed) / owed0 if owed0 > 0 else 0.0
        ),
    }

    return {
        "f2i": int(f2i),
        "elasticity": float(elasticity),
        "seed": int(seed),
        # surface two: the claim-to-resource ratio a price index reads against
        # the one nobody targets
        "mr_ratio": r(raw["mr_ratio"]),
        "mara_ratio": r(raw["mara_ratio"]),
        # surface three: money and concentration against the real side
        "m_ratio": r(raw["m_ratio"]),
        "gini_open": r(raw["gini_open"]),
        "gini_close": r(raw["gini_close"]),
        "resource_levels": raw["resource_levels"],
        # surface four a: the reach of circulation
        "support_ratio": r(raw["support_ratio"]),
        "support_l2_ratio": r(
            tail_mean(h.effective_support_l2) / h.effective_support_l2[0]
        ),
        # surface four b: the payroll squeeze, read as a pair
        "wage_funding": r(raw["wage_funding"]),
        "wage_owed_ratio": r(raw["wage_owed_ratio"]),
        "smb_ratio": r(
            tail_mean(h.intermediate_holdings) / h.intermediate_holdings[0]
        ),
        # The two quantities the surfaces ask to be positive, where they are
        # positive and read zero at ``DIGITS`` places: the order of magnitude
        # they sit at. Empty for every row the rounding does not touch.
        "below_resolution": {
            name: order(raw[name])
            for name in ("mara_ratio", "wage_owed_ratio")
            if raw[name] > 0.0 and r(raw[name]) == 0.0
        },
        # The same four flags read off the unrounded values. ``surfaces``, set
        # by the callers from the rounded row, is the registered reading.
        "surfaces_unrounded": surface_flags(raw),
        # structure
        "onsets": onset_rounds(h),
        "layer2_reached_close": int(h.layer2_reached[-1]),
        "potential_support": int(h.potential_support),
        # The bound, not the digits. The gap is a quantity the accounting says
        # is exactly zero, so whatever the reduction left behind is decided by
        # accumulation order and differs between BLAS builds. Writing the
        # residue would put a number in the record that changes when nothing
        # about the economy did; writing whether it cleared the tolerance says
        # the same thing identically on every machine.
        "claims_conserved": bool(conserved < SFC_TOLERANCE),
        # The same bound on the state the run is left in, after the last
        # round's settlement, which no row above carries.
        "claims_conserved_at_close": bool(closed < SFC_TOLERANCE),
    }


#: Reporting order and one-character marks for the four surfaces. Fixed here
#: rather than taken from dictionary order, so the printed string reads in the
#: order Volume One section 13 lists them in.
SURFACE_ORDER = ("two", "three", "four_a", "four_b")
SURFACE_MARKS = {"two": "2", "three": "3", "four_a": "a", "four_b": "b"}


def onset_rounds(h) -> dict:
    """The round each surface first holds, or ``None`` if it never does.

    Printed, not adjudicated. Volume One section 12 states a causal chain, and
    the order surfaces appear in would be the executable form of it, but two of
    the links here are forced by construction and cannot carry information: the
    intermediate block *is* the payroll payer, so payroll fails when the block
    is drained by definition of ``min(per_payer, holdings[payers])``; and the
    payroll edge is the only downward one, so household inflow follows it. Only
    the order *between* surfaces driven by different machinery is informative,
    which is why this is reported rather than scored.
    """
    m = np.asarray(h.holdings, dtype=float).sum(axis=1)
    mr = np.asarray(h.total_ratio, dtype=float)
    mara = np.asarray(h.active_ratio, dtype=float)
    support = np.asarray(h.effective_support, dtype=float)
    funding = np.asarray(h.wage_funding_ratio, dtype=float)
    owed = np.asarray(h.wage_owed, dtype=float)
    g = np.array([gini(h.holdings[t]) for t in range(len(m))])

    def first(mask: np.ndarray) -> int | None:
        idx = np.where(mask)[0]
        return int(idx[0]) if idx.size else None

    return {
        "two": first((mr > mr[0]) & (mara > 0.0)),
        "three": first((m > m[0]) & (g > g[0])),
        "four_a": first(support < support[0]),
        "four_b": first((funding < 1.0) & (owed > 0.0)),
    }


def surface_flags(v: dict) -> dict:
    """The four surfaces, from the nine quantities they are read off.

    Directions only. Each entry is the sign of a movement, so there is no
    threshold anywhere in this function and nothing to tune.
    """
    return {
        # M/R rises while the ratio a price index reads does not fall with it
        "two": bool(v["mr_ratio"] > 1.0 and v["mara_ratio"] > 0.0),
        # money and concentration rise together while the real side is fixed
        "three": bool(
            v["m_ratio"] > 1.0
            and v["gini_close"] > v["gini_open"]
            and v["resource_levels"] == 1
        ),
        # circulation reaches fewer nodes than it started with
        "four_a": bool(v["support_ratio"] < 1.0),
        # payroll goes unfunded while the bill it is measured against survives
        "four_b": bool(v["wage_funding"] < 1.0 and v["wage_owed_ratio"] > 0.0),
    }


def surfaces_present(row: dict) -> dict:
    """Which surfaces are on the table for this configuration.

    The registered reading. The magnitudes live in the row itself and are
    reported beside these flags.

    **Read at the record's resolution.** ``row`` holds values rounded to
    ``DIGITS`` places, so a comparison here is a comparison at that many
    places: the two conditions that ask for a positive value read zero for
    anything under half a unit in the last place. That is the one finite
    resolution in the adjudication. ``rounding_report`` prints every flag it
    decides and the order of magnitude the decided values sit at.
    """
    return surface_flags(row)


def rounding_report(rows: list[dict], across_seeds: list[dict]) -> dict:
    """Where rounding to ``DIGITS`` places decides a flag.

    A flag is decided by the rounding when the registered reading, off the
    rounded row, and the reading off the unrounded values disagree. Each such
    flag is listed with the order of magnitude of the value that read zero and
    with how many production-layer nodes circulation still reached at the
    close, which is the reading that says what the zero is.
    """
    decided = []
    for arm, group in (("grid", rows), ("seeds", across_seeds)):
        for row in group:
            for name in SURFACE_ORDER:
                if row["surfaces"][name] == row["surfaces_unrounded"][name]:
                    continue
                decided.append(
                    {
                        "arm": arm,
                        "f2i": row["f2i"],
                        "elasticity": row["elasticity"],
                        "seed": row["seed"],
                        "surface": name,
                        "at_record_resolution": row["surfaces"][name],
                        "unrounded": row["surfaces_unrounded"][name],
                        "below_resolution": row["below_resolution"],
                        "layer2_reached_close": row["layer2_reached_close"],
                    }
                )
    runs = rows + across_seeds
    orders = [o for row in runs for o in row["below_resolution"].values()]
    positive = {
        name: [row[name] for row in runs if row[name] > 0.0]
        for name in ("mara_ratio", "wage_owed_ratio")
    }
    return {
        "digits": DIGITS,
        "reads_zero_below": 0.5 * 10.0**-DIGITS,
        "flags_decided": decided,
        "edges_where_it_decides": sorted({d["f2i"] for d in decided}),
        "orders_reading_zero": (
            {"smallest": min(orders), "largest": max(orders)} if orders else None
        ),
        "smallest_value_reading_positive": {
            name: (min(values) if values else None)
            for name, values in positive.items()
        },
    }


def rounding_lines(report: dict) -> list[str]:
    """``rounding_report`` as printed lines."""
    decided = report["flags_decided"]
    lines = [
        f"  flags read at {report['digits']} decimal places; a positive value "
        f"under {report['reads_zero_below']:.0e} reads zero"
    ]
    if not decided:
        lines.append("  no flag is decided by the rounding on this carrier")
        return lines
    span = report["orders_reading_zero"]
    reached = sorted({d["layer2_reached_close"] for d in decided})
    lines.append(
        f"  {len(decided)} flags are decided by it, all at edges "
        f"{report['edges_where_it_decides']}"
        + (
            # A flag can also be decided by a value within half a unit of the
            # line it is compared with, and then no positive value read zero.
            ""
            if span is None
            else f": the values that read zero there are positive at "
            f"1e{span['smallest']} to 1e{span['largest']} of their opening "
            f"value, and circulation reaches {reached} production-layer nodes "
            f"at the close"
        )
    )
    small = report["smallest_value_reading_positive"]
    lines.append(
        "  smallest value read as positive anywhere on the grid: active ratio "
        f"{small['mara_ratio']}, wage bill ratio {small['wage_owed_ratio']}"
    )
    by_surface: dict[str, int] = {}
    for d in decided:
        by_surface[d["surface"]] = by_surface.get(d["surface"], 0) + 1
    tally = ", ".join(f"{name} {by_surface[name]}" for name in sorted(by_surface))
    one_way = all(not d["at_record_resolution"] and d["unrounded"] for d in decided)
    lines.append(
        f"  by surface: {tally}"
        + (
            "; in each the registered reading is absent and the unrounded "
            "sign is positive"
            if one_way
            else "; the two readings disagree in both directions"
        )
    )
    return lines


def run_grid(rounds: int, seed: int, carrier: Carrier = BASE) -> list[dict]:
    rows = []
    for f2i in carrier.edges:
        for e in ELASTICITIES:
            row = one_run(f2i, e, rounds, seed, carrier)
            row["surfaces"] = surfaces_present(row)
            row["all_four"] = bool(all(row["surfaces"].values()))
            rows.append(row)
    return rows


def run_seeds(
    rounds: int, seeds: int, elasticity: float, carrier: Carrier = BASE
) -> list[dict]:
    rows = []
    for f2i in carrier.edges:
        for s in range(seeds):
            row = one_run(f2i, elasticity, rounds, s, carrier)
            row["surfaces"] = surfaces_present(row)
            row["all_four"] = bool(all(row["surfaces"].values()))
            rows.append(row)
    return rows


def evaluate(
    rows: list[dict], across_seeds: list[dict], carrier: Carrier = BASE
) -> list[Criterion]:
    out: list[Criterion] = []

    out.append(
        Criterion(
            "A8-1  the grid comes from A2, not from this stage",
            GRID_SOURCE.startswith("imported"),
            f"{GRID_SOURCE}; edges={list(carrier.edges)}, "
            f"elasticities={list(ELASTICITIES)}, "
            f"intermediate={carrier.intermediate_size}, tail={TAIL}"
            + (
                f"; carrier at {carrier.nodes} nodes, so the counts are solved "
                f"from A2's {list(AUTONOMOUS_EDGES)} at {BASE_NODES} by holding "
                f"each point's autonomous share. The transform is fixed and "
                f"the grid is still A2's"
                if carrier.resized
                else ""
            )
            + (
                "; A3's asset layer is on this carrier, which the registered "
                "one does not have"
                if carrier.asset
                else ""
            ),
        )
    )

    levels = {row["resource_levels"] for row in rows + across_seeds}
    out.append(
        Criterion(
            "A8-2  the real side is a level, not state",
            levels == {1},
            f"distinct resource values per run across "
            f"{len(rows) + len(across_seeds)} runs: {sorted(levels)}",
        )
    )

    runs = rows + across_seeds
    conserved = sum(
        1
        for row in runs
        if row["claims_conserved"] and row["claims_conserved_at_close"]
    )
    out.append(
        Criterion(
            "A8-3  claims are conserved across the grid",
            conserved == len(runs),
            f"{conserved}/{len(runs)} runs hold the identity between holdings "
            f"and opening-plus-issuance at machine precision, below "
            f"{SFC_TOLERANCE:.0e}, on every recorded row and on the settled "
            f"state the run is left in",
        )
    )

    hits = sorted({row["f2i"] for row in rows if row["all_four"]})
    misses = sorted({row["f2i"] for row in rows} - set(hits))
    never = [
        name
        for name in ("two", "three", "four_a", "four_b")
        if not any(row["surfaces"][name] for row in rows)
    ]
    detail = (
        f"all four surfaces present at edges {hits}; absent at {misses}; "
        f"surfaces never present anywhere on the grid: {never or 'none'}"
    )
    # The registered design has two halves and this criterion tests one of
    # them. Section 13 asks whether a single setting puts the four on the
    # table **and** whether widening one edge takes them off it, and an
    # empty miss list means this grid answers the first and not the second.
    # Measured on the asset carrier, where the market stays contracted at
    # the widest edge tried, so nothing on the grid removes the surfaces.
    if not misses:
        detail += (
            ". NO CONTRAST: no edge on this grid takes the four off the table,"
            " so this run answers whether a setting exists and not whether"
            " widening the edge removes it, which is the other half of the"
            " registered design"
        )
    out.append(
        Criterion(
            "A8-4  one setting puts all four surfaces on the table",
            bool(hits) and not never,
            detail,
        )
    )

    # A8-5. A8-4 reads the grid arm, which is one seed. The seed arm in this
    # same record carries five at one elasticity, and the two halves of A8-4 do
    # not survive it equally: that some setting shows all four is stable, and
    # which surface drops at an end is not. The support ratio at the far edge
    # straddles one across seeds, so a criterion placed on it would be a
    # zero-width strict inequality on a quantity whose seed spread exceeds its
    # margin, which is the shape rule 11 forbids. This prints the tally instead
    # and places no line on it. Its own pass condition is structural: the seed
    # arm exists and every point in it carries more than one seed.
    seed_tally: dict[int, dict[str, int]] = {}
    for row in across_seeds:
        entry = seed_tally.setdefault(row["f2i"], {"seeds": 0, "all_four": 0})
        entry["seeds"] += 1
        entry["all_four"] += int(bool(row["all_four"]))
        for name in ("two", "three", "four_a", "four_b"):
            entry[name] = entry.get(name, 0) + int(bool(row["surfaces"][name]))
    tally_lines = []
    for f2i in sorted(seed_tally):
        entry = seed_tally[f2i]
        n = entry["seeds"]
        tally_lines.append(
            f"f2i={f2i}: all_four {entry['all_four']}/{n}, "
            + " ".join(
                f"{name} {entry[name]}/{n}"
                for name in ("two", "three", "four_a", "four_b")
            )
        )
    out.append(
        Criterion(
            "A8-5  the seed arm is tallied surface by surface, no line on it",
            bool(seed_tally) and all(e["seeds"] > 1 for e in seed_tally.values()),
            "; ".join(tally_lines) if tally_lines else "no seed arm on this run",
        )
    )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=600)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--nodes",
        type=int,
        default=BASE_NODES,
        help="carrier size. The default is the registered one and runs the "
        "code path this stage always ran; any other value scales the three "
        "blocks by the node ratio and solves the edge grid for the same "
        "autonomous shares.",
    )
    parser.add_argument(
        "--asset",
        action="store_true",
        help="put A3's asset layer on the carrier. Off is the registered "
        "carrier. On adds the revaluation channel, which is the one the "
        "empirical literature weights most heavily and the one every "
        "concentration reading downstream of this stage is missing.",
    )
    args = parser.parse_args()

    carrier = carrier_at(args.nodes, asset=args.asset)

    print("stage A8: the coverage test")
    print(f"  rounds={args.rounds} seeds={args.seeds} grid={GRID_SOURCE}")
    print(
        f"  carrier {carrier.nodes} nodes "
        f"({carrier.layer1_size}/{carrier.intermediate_size}/"
        f"{carrier.layer2_size}), edges {list(carrier.edges)}, "
        f"asset layer {'on' if carrier.asset else 'off'}"
    )
    if carrier.resized:
        print(
            f"  solved from A2's {list(AUTONOMOUS_EDGES)} at {BASE_NODES} "
            f"nodes by holding each point's autonomous share"
        )
    print()

    rows = run_grid(args.rounds, args.seed, carrier)
    mid_elasticity = ELASTICITIES[len(ELASTICITIES) // 2]
    across = run_seeds(args.rounds, args.seeds, mid_elasticity, carrier)

    print(
        f"{'edges':>6s} {'elast':>6s} {'M/R':>8s} {'MaRa':>7s} {'gini':>15s} "
        f"{'support':>8s} {'wfund':>7s} {'owed':>7s}  surfaces"
    )
    for row in rows:
        flags = "".join(
            SURFACE_MARKS[k] if row["surfaces"][k] else "." for k in SURFACE_ORDER
        )
        print(
            f"{row['f2i']:6d} {row['elasticity']:6.2f} {row['mr_ratio']:8.2f} "
            f"{row['mara_ratio']:7.3f} {row['gini_open']:6.4f}->{row['gini_close']:<8.4f} "
            f"{row['support_ratio']:8.3f} {row['wage_funding']:7.3f} "
            f"{row['wage_owed_ratio']:7.3f}  {flags}"
        )

    criteria = evaluate(rows, across, carrier)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    rounding = rounding_report(rows, across)
    print("\nresolution (printed, not scored)")
    for line in rounding_lines(rounding):
        print(line)

    # Printed objects that are not criteria. Nothing here can pass or fail; the
    # point is that a reader sees the objects rather than a verdict computed
    # from them.
    by_elasticity = {}
    for name in ("mr_ratio", "gini_close", "support_ratio", "wage_funding"):
        lo = [row[name] for row in rows if row["elasticity"] == min(ELASTICITIES)]
        hi = [row[name] for row in rows if row["elasticity"] == max(ELASTICITIES)]
        by_elasticity[name] = {
            "at_lowest_elasticity": [r(v) for v in lo],
            "at_highest_elasticity": [r(v) for v in hi],
        }

    # Every onset observed anywhere on the grid. The spread is the object: if
    # every surface opens inside the first few rounds then the ordering is
    # reading the opening transient rather than any chain of causation, and no
    # criterion should be written on it at this resolution.
    onset_spread = {}
    for name in SURFACE_ORDER:
        seen = [row["onsets"][name] for row in rows if row["onsets"][name] is not None]
        never = sum(1 for row in rows if row["onsets"][name] is None)
        onset_spread[name] = {
            "earliest": min(seen) if seen else None,
            "latest": max(seen) if seen else None,
            "never_opens": never,
        }

    unfunded_pairs = [
        {
            "f2i": row["f2i"],
            "elasticity": row["elasticity"],
            "wage_funding": row["wage_funding"],
            "wage_owed_ratio": row["wage_owed_ratio"],
        }
        for row in rows
        if row["wage_owed_ratio"] <= 0.0
    ]

    RESULTS.mkdir(parents=True, exist_ok=True)
    # A rescaled run writes its own file rather than overwriting this
    # stage's record. The two carry the same fields on different carriers,
    # and the project's own rule is that two readings on different
    # definitions do not share a column.
    path = RESULTS / f"a8_coverage{carrier.tag}.json"
    path.write_text(
        json.dumps(
            {
                "stage": "A8",
                "rounds": args.rounds,
                "seed": args.seed,
                "seeds_tested": args.seeds,
                "grid_source": GRID_SOURCE,
                "grid": {
                    "autonomous_edges": list(carrier.edges),
                    "elasticities": list(ELASTICITIES),
                    "intermediate_size": carrier.intermediate_size,
                    "production_size": carrier.intermediate_size
                    + carrier.layer2_size,
                    "tail": TAIL,
                },
                "carrier": {
                    "nodes": carrier.nodes,
                    "layer1_size": carrier.layer1_size,
                    "intermediate_size": carrier.intermediate_size,
                    "layer2_size": carrier.layer2_size,
                    "edges": list(carrier.edges),
                    "rescaled": carrier.rescaled,
                    "asset_layer": carrier.asset,
                    "registered_edges_at_base": list(AUTONOMOUS_EDGES),
                    "base_nodes": BASE_NODES,
                },
                **(
                    {
                        "diagnostic_only": True,
                        "diagnostic_reason": (
                            (
                                ""
                                if carrier.nodes == BASE_NODES
                                else f"Carrier at {carrier.nodes} nodes, not "
                                f"the {BASE_NODES} this stage is registered "
                                f"at; the edge grid is solved for equal "
                                f"autonomous share, so the curve is "
                                f"comparable in shape and not in level. "
                            )
                            + (
                                ""
                                if not carrier.asset
                                else "A3's asset layer is on this carrier "
                                "and the registered one has no asset "
                                "layer, so the two are two channels and "
                                "not two settings of one. Reported beside "
                                "the registered run, never in place of "
                                "it."
                            )
                            + " No number here is a closed reading of A8."
                        ),
                    }
                    if carrier.rescaled
                    else {}
                ),
                "grid_runs": rows,
                "seed_runs": across,
                "seed_run_elasticity": mid_elasticity,
                "diagnostics": {
                    "onset_rounds_by_surface": onset_spread,
                    "response_across_elasticity": by_elasticity,
                    "bill_collapsed_to_zero": unfunded_pairs,
                    "rounding": rounding,
                },
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
