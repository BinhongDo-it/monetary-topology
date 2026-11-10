"""Stage A2c: cycle structure of the realized circulation graph.

Measures the object Volume II's non-integrability argument is about: cycle
structure. The seven criteria read runs stage A2 already produces, and no price
field is invented. The one thing run beyond them is two of the same arms
continued past the registered length, recorded and not scored. See
``topology.py`` for what this can and cannot license.

Usage::

    python experiments/a2c_cycle_structure.py
    python experiments/a2c_cycle_structure.py --rounds 800 --seeds 6

Writes ``figures/a2c_fig9..10_*.png`` and ``results/a2c_cycle_structure.json``.
Exits non-zero if any criterion fails.

These readings are recorded after the criteria and are not scored:

* ``cutoff``. The realized graph is the edges whose flow exceeds a cutoff, so
  the record carries, for every run, the rank at that cutoff, the rank over
  every strictly positive flow, and how many decades of cutoff read the same
  graph.
* ``continuation`` and ``continuation_one_edge``. The zero-edge and one-edge
  arms of every seed run on to ``CONTINUE_ROUNDS``, each reproducing its
  registered run at every snapshot the two share, to see what the strictly
  positive count does once the decaying flows leave the floating-point range.
* ``hodge_choice``. Both splits, with every triangle filled and with no face
  filled, on the same snapshots; which criteria read the choice, worked out
  from the columns each one reads; and the growth of three measures of flow on
  the same run.
* ``potential_graph``. The potential graph compared with a copy taken before
  round 0, after every round of every run. A2c-4 requires it of the six runs it
  reads.
* ``series`` and ``cross_seed``. Every series the criteria read, of which the
  details quote the ends.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from monetary_topology.config import MonetaryAuthority, WageChannel
from monetary_topology.network import Network, NetworkConfig, NetworkSpec
from monetary_topology.plotting import (
    COLOR_ACCENT,
    COLOR_INSTRUMENT,
    COLOR_LAYER1,
    COLOR_LAYER2,
    annotate,
    apply_style,
    save,
)
from monetary_topology.topology import (
    cycle_rank,
    hodge_decomposition,
    incidence_matrix,
    net_flow_vector,
    realized_adjacency,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

SNAPSHOT_EVERY = 50
AUTONOMOUS_EDGES = (0, 1, 2, 5, 12, 30)

#: Rounds for the continuation of the zero-edge and one-edge arms. Not a tuned
#: number. The flows that leave the realized graph fall by about a quarter of a
#: decade a round, and a double reaches 324 decades below one, so three thousand
#: rounds is twice what the slowest of them needs to leave the floating-point
#: range.
CONTINUE_ROUNDS = 3000

#: One row per model run this script makes. See ``run_checked``.
GRAPH_CHECKS: list[dict] = []


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def run_checked(net: Network):
    """Run ``net`` and compare its potential graph with the opening copy each round.

    The history carries the live adjacency array, so comparing that array with
    itself after the run says nothing, and comparing only the closing state
    misses an edge taken out and put back. The copy is taken before round 0 and
    the comparison is made as each round closes.
    """
    opening = net.adjacency.copy()
    ran = same = 0
    for _ in net._run_steps():
        ran += 1
        same += int(np.array_equal(net.adjacency, opening))
    history = net._history
    assert history is not None
    return history, {
        "rounds": ran,
        "rounds_graph_equal_to_opening": same,
        "potential_directed_edges": int((opening > 0).sum()),
    }


def go(spec: NetworkSpec, *, rule="endogenous", rounds: int, seed: int, network=Network):
    history, check = run_checked(
        network(
            NetworkConfig(
                spec=spec,
                rounds=rounds,
                seed=seed,
                snapshot_every=SNAPSHOT_EVERY,
                authority=MonetaryAuthority(rule=rule),
                wages=WageChannel(bill=8.0, elasticity=0.0),
            )
        )
    )
    GRAPH_CHECKS.append(
        {
            "layers": 3 if spec.intermediate_size else 2,
            "seed": seed,
            "autonomous_edges": spec.financial_to_intermediate_edges,
            **check,
        }
    )
    return history


def graph_unchanged(checks: list[dict]) -> bool:
    """Every round of every run in ``checks`` closed on the graph it opened on."""
    return bool(checks) and all(
        c["rounds"] > 0 and c["rounds_graph_equal_to_opening"] == c["rounds"]
        for c in checks
    )


def three_layer(seed: int, edges: int = 0) -> NetworkSpec:
    return NetworkSpec(
        seed=seed,
        intermediate_size=30,
        layer2_size=150,
        financial_to_intermediate_edges=edges,
    )


def sig(x: float) -> float:
    """Six significant figures, so a last-digit difference between BLAS builds
    is not a difference between two records."""
    return float(f"{float(x):.6g}")


def decades(x: float) -> float | None:
    """``log10`` to one decimal, or ``None`` for nothing at all.

    Magnitudes far below one are recorded as an exponent. Written out in full
    they would be mantissas at ``1e-140``, which say nothing an exponent does
    not and differ between machines in digits nobody reads.
    """
    return None if not x > 0.0 else round(math.log10(x), 1)


def cutoff_reading(flow: np.ndarray, potential: np.ndarray, epsilon: float) -> dict:
    """What the cutoff does to the graph one flow matrix is read as.

    The realized graph keeps a directed edge when its flow exceeds ``epsilon``.
    Three ranks are set side by side: the potential graph's, the realized
    graph's, and the rank counting every flow that is a positive number at all.
    Between the largest flow at or below the cutoff and the smallest flow above
    it there is no flow, so every cutoff in that band reads the same graph; its
    width in decades says how much the choice of cutoff decides, and
    ``same_graph_at_zero_cutoff`` says the two counts are one count. The
    smallest positive flow says how near the fastest of the decaying flows is
    to leaving the floating-point range, which ends about 324 decades below one.
    """
    on = potential > 0
    above = flow > epsilon
    positive = flow > 0
    below = positive & ~above
    upper = decades(float(flow[above].min())) if above.any() else None
    lower = decades(float(flow[below].max())) if below.any() else None
    smallest = decades(float(flow[positive].min())) if positive.any() else None
    total = float(flow.sum())
    return {
        "potential_rank": cycle_rank(potential),
        "cutoff_rank": cycle_rank(above.astype(float)),
        "positive_rank": cycle_rank(positive.astype(float)),
        "directed_edges_above_cutoff": int(above.sum()),
        "directed_edges_positive_at_or_below_cutoff": int(below.sum()),
        "directed_edges_exactly_zero": int((on & ~positive).sum()),
        "directed_edges_carrying_flow_outside_the_potential_graph": int(
            (positive & ~on).sum()
        ),
        "same_graph_at_zero_cutoff": not bool(below.any()),
        "log10_cutoff": decades(epsilon),
        "log10_smallest_flow_above_cutoff": upper,
        "log10_largest_flow_at_or_below_cutoff": lower,
        "log10_smallest_positive_flow": smallest,
        "decades_of_cutoff_reading_this_graph": (
            None if upper is None or lower is None else round(upper - lower, 1)
        ),
        "log10_share_of_volume_at_or_below_cutoff": (
            decades(float(flow[below].sum()) / total)
            if below.any() and total > 0
            else None
        ),
    }


def last_reading(history) -> dict:
    last = max(history.snapshots)
    return cutoff_reading(
        history.snapshots[last], history.adjacency, history.epsilon_absolute
    )


def continued(
    seed: int, short, *, edges: int = 0, rounds: int | None = None, network=Network
) -> dict:
    """The arm of ``seed`` with ``edges`` autonomous edges run on, everything else
    as registered.

    ``short`` is the registered-length run of the same arm. The longer run must
    reproduce it at every snapshot the two share, which is what makes this the
    same run continued and not another run.
    """
    rounds = CONTINUE_ROUNDS if rounds is None else rounds
    long = go(three_layer(seed, edges), rounds=rounds, seed=seed, network=network)
    eps = long.epsilon_absolute
    potential = cycle_rank(long.adjacency)
    rows = [
        (
            int(t),
            cycle_rank(realized_adjacency(long.snapshots[t], eps)),
            cycle_rank((long.snapshots[t] > 0).astype(float)),
        )
        for t in sorted(long.snapshots)
    ]
    shared = [t for t in sorted(short.snapshots) if t in long.snapshots]
    later = [r for r in rows if r[0] > 0]
    unequal = [t for t, at_cutoff, positive in later if positive != at_cutoff]
    settled = [t for t, _, _ in later if not unequal or t > max(unequal)]
    return {
        "seed": seed,
        "autonomous_edges": edges,
        "rounds": rounds,
        "snapshots": len(rows),
        "reproduces_the_registered_run_at_shared_snapshots": bool(shared)
        and eps == short.epsilon_absolute
        and all(
            np.array_equal(long.snapshots[t], short.snapshots[t]) for t in shared
        ),
        "shared_snapshots": len(shared),
        "cutoff_rank_values_after_round_0": sorted({a for _, a, _ in later}),
        "positive_rank_values_after_round_0": sorted(
            {b for _, _, b in later}, reverse=True
        ),
        "last_snapshot_with_positive_rank_above_cutoff_rank": (
            max(unequal) if unequal else None
        ),
        "positive_rank_equals_cutoff_rank_from_snapshot": (
            min(settled) if settled else None
        ),
        "cutoff_rank_at_last_snapshot": rows[-1][1],
        "positive_rank_at_last_snapshot": rows[-1][2],
        "potential_rank": potential,
        "positive_rank_over_potential_at_last_snapshot": sig(rows[-1][2] / potential),
    }


def measure_ranks(history) -> dict[str, list]:
    """Cycle rank only. Exact integer combinatorics, cheap.

    Kept separate from the Hodge measurement because the decomposition costs
    orders of magnitude more and figure 10 does not need it.
    """
    rows: dict[str, list] = {"round": [], "realized_rank": []}
    for t in sorted(history.snapshots):
        realized = realized_adjacency(history.snapshots[t], history.epsilon_absolute)
        rows["round"].append(int(t))
        rows["realized_rank"].append(cycle_rank(realized))
    return rows


def measure(history) -> dict[str, list]:
    """Cycle rank and Hodge magnitudes at every snapshot.

    Magnitudes are recorded alongside shares throughout. A share can fall
    because its own component shrank or because everything else grew, and in
    this model it is usually the second, so reporting shares alone would
    misdescribe what happened.

    Both splits are run. With no face filled the part outside the gradient is
    one component and is reported as ``harmonic_norm_bare``; with every triangle
    filled it is ``curl_norm`` and ``harmonic_norm``. ``splits_agree`` checks,
    at each snapshot, that the gradient is the same vector in both and that the
    bare component is the sum of the other two. Every column the criteria read
    has its counterpart under the bare split, so ``hodge_choice`` can tell
    which criteria the choice reaches by comparing them.
    """
    rows: dict[str, list] = {
        "round": [],
        "realized_rank": [],
        "gradient_norm": [],
        "curl_norm": [],
        "harmonic_norm": [],
        "flow_norm": [],
        "gradient_share": [],
        "harmonic_share": [],
        "divergence_norm": [],
        "gradient_norm_bare": [],
        "harmonic_norm_bare": [],
        "harmonic_share_bare": [],
        "splits_agree": [],
        "gross_volume": [],
        "net_flow_l1": [],
    }
    for t in sorted(history.snapshots):
        flow = history.snapshots[t]
        realized = realized_adjacency(flow, history.epsilon_absolute)
        split = hodge_decomposition(flow, realized)
        bare = hodge_decomposition(flow, realized, fill_triangles=False)
        w = net_flow_vector(flow, realized)
        div = incidence_matrix(realized).T @ w
        g, c, h = split.energies()
        gs, _, hs = split.shares()
        scale = max(float(np.linalg.norm(w)), 1e-30)

        rows["round"].append(int(t))
        rows["realized_rank"].append(cycle_rank(realized))
        rows["gradient_norm"].append(float(np.sqrt(g)))
        rows["curl_norm"].append(float(np.sqrt(c)))
        rows["harmonic_norm"].append(float(np.sqrt(h)))
        rows["flow_norm"].append(float(np.linalg.norm(w)))
        rows["gradient_share"].append(float(gs))
        rows["harmonic_share"].append(float(hs))
        rows["divergence_norm"].append(float(np.linalg.norm(div)))
        # The same arithmetic as the three columns above, on the other split.
        gb, _, hb = bare.energies()
        rows["gradient_norm_bare"].append(float(np.sqrt(gb)))
        rows["harmonic_norm_bare"].append(float(np.sqrt(hb)))
        rows["harmonic_share_bare"].append(float(bare.shares()[2]))
        rows["splits_agree"].append(
            bare.filled_triangles == 0
            and float(np.abs(bare.curl).max(initial=0.0)) == 0.0
            and float(np.abs(bare.gradient - split.gradient).max(initial=0.0))
            <= 1e-9 * scale
            and float(
                np.abs(bare.harmonic - (split.curl + split.harmonic)).max(initial=0.0)
            )
            <= 1e-9 * scale
        )
        rows["gross_volume"].append(float(flow.sum()))
        rows["net_flow_l1"].append(float(np.abs(w).sum()))
    return rows


#: The split-dependent columns each criterion reads, paired with the same column
#: under the split with no face filled. A2c-1 and A2c-2 also read ``flow_norm``,
#: the norm of net flow itself, which no split touches; A2c-4 to A2c-7 read
#: cycle ranks and no Hodge column.
HODGE_COLUMNS_READ = {
    "A2c-1": (("gradient_norm", "gradient_norm_bare"),),
    "A2c-2": (("gradient_norm", "gradient_norm_bare"),),
    "A2c-3": (
        ("harmonic_norm", "harmonic_norm_bare"),
        ("harmonic_share", "harmonic_share_bare"),
    ),
}


def criteria_that_read_the_choice(m: dict[str, list]) -> list[str]:
    """The criteria whose columns take other values under the other split."""

    def differs(a: str, b: str) -> bool:
        return any(
            abs(x - y) > 1e-9 * max(abs(x), abs(y), 1e-30)
            for x, y in zip(m[a], m[b], strict=True)
        )

    return [
        name
        for name, pairs in HODGE_COLUMNS_READ.items()
        if any(differs(a, b) for a, b in pairs)
    ]


def hodge_choice(m: dict[str, list]) -> dict:
    """What the choice of faces does to each number the criteria read."""

    def spread(key: str) -> float:
        return sig(max(m[key]) / min(m[key]))

    def ends(key: str) -> list[float]:
        return [sig(m[key][0]), sig(m[key][-1])]

    def growth(key: str) -> float:
        return sig(m[key][-1] / m[key][0])

    def growth_over_gradient(key: str) -> float:
        g = m["gradient_norm"]
        return sig((m[key][-1] / g[-1]) / (m[key][0] / g[0]))

    return {
        "splits_agree_at_every_snapshot": all(m["splits_agree"]),
        "criteria_that_read_the_choice": criteria_that_read_the_choice(m),
        "no_face_filled": {
            "outside_the_gradient_norm_first_last": ends("harmonic_norm_bare"),
            "outside_the_gradient_norm_max_over_min": spread("harmonic_norm_bare"),
            "outside_the_gradient_share_first_last": ends("harmonic_share_bare"),
        },
        "every_triangle_filled": {
            "curl_norm_first_last": ends("curl_norm"),
            "curl_norm_last_over_first": sig(m["curl_norm"][-1] / m["curl_norm"][0]),
            "harmonic_norm_first_last": ends("harmonic_norm"),
            "harmonic_norm_max_over_min": spread("harmonic_norm"),
            "harmonic_share_first_last": ends("harmonic_share"),
        },
        "growth_on_the_same_run": {
            "gross_volume": growth("gross_volume"),
            "net_flow_per_edge_summed": growth("net_flow_l1"),
            "net_flow_per_edge_norm": growth("flow_norm"),
        },
        "growth_of_the_ratio_to_the_gradient_norm_on_the_same_run": {
            "gross_volume": growth_over_gradient("gross_volume"),
            "net_flow_per_edge_summed": growth_over_gradient("net_flow_l1"),
            "net_flow_per_edge_norm": growth_over_gradient("flow_norm"),
        },
    }


# ---------------------------------------------------------------------------
# figure 9: churn grows, net displacement does not
# ---------------------------------------------------------------------------


def figure_9(rounds: int, seed: int) -> tuple[Path, dict]:
    h = go(NetworkSpec(seed=seed), rounds=rounds, seed=seed)
    m = measure(h)
    t = m["round"]

    fig, (ax_n, ax_s) = plt.subplots(1, 2, figsize=(10.6, 4.6))

    ax_n.plot(
        t,
        m["flow_norm"],
        color=COLOR_LAYER1,
        marker="o",
        markersize=3.5,
        label="net flow, all components",
    )
    ax_n.plot(
        t,
        m["gradient_norm"],
        color=COLOR_LAYER2,
        marker="s",
        markersize=3.5,
        label="gradient component",
    )
    ax_n.plot(
        t,
        m["harmonic_norm"],
        color=COLOR_ACCENT,
        marker="^",
        markersize=3.5,
        label="harmonic component",
    )
    ax_n.set_yscale("log")
    ax_n.set_xlabel("round")
    ax_n.set_ylabel("magnitude, log scale")
    ax_n.set_title("Magnitudes: only one of them grows")
    ax_n.legend(loc="center right")
    annotate(
        ax_n,
        "The gradient component is the part of circulation that actually moves\n"
        "claims from one place to another. It is flat. What grows is the part\n"
        "that returns to where it came from.",
        loc="lower left",
    )

    ratio = np.array(m["flow_norm"]) / np.maximum(np.array(m["gradient_norm"]), 1e-30)
    ax_s.plot(t, ratio, color=COLOR_INSTRUMENT, marker="o", markersize=4)
    ax_s.set_yscale("log")
    ax_s.set_xlabel("round")
    ax_s.set_ylabel("circulation / net displacement")
    ax_s.set_title("Book velocity against topological displacement")
    annotate(
        ax_s,
        f"Rises from {ratio[0]:.1f} to {ratio[-1]:.0f} over the run.\n"
        "This is the framework's claim that intra-layer spending has non-zero\n"
        "book velocity and zero topological displacement, stated for the whole\n"
        "economy as one number rather than asserted about one stratum.",
        loc="lower right",
    )

    fig.tight_layout()
    path = save(fig, FIGURES / "a2c_fig9_churn_versus_displacement.png")
    return path, {
        "two_layer": m,
        "ratio_start": float(ratio[0]),
        "ratio_end": float(ratio[-1]),
    }


# ---------------------------------------------------------------------------
# figure 10: cycle rank collapses with nothing deleted
# ---------------------------------------------------------------------------


def figure_10(rounds: int, seed: int) -> tuple[Path, dict]:
    series: dict[int, dict] = {}
    potentials: dict[int, int] = {}
    readings: dict[int, dict] = {}
    zero_arm: dict = {}
    first_check = len(GRAPH_CHECKS)
    for k in AUTONOMOUS_EDGES:
        spec = three_layer(seed, k)
        h = go(spec, rounds=rounds, seed=seed)
        potentials[k] = cycle_rank(h.adjacency)
        series[k] = measure_ranks(h)
        readings[k] = last_reading(h)
        if k == 0:
            zero_arm = {
                "round": [int(t) for t in sorted(h.snapshots)],
                "by_snapshot": [
                    cutoff_reading(h.snapshots[t], h.adjacency, h.epsilon_absolute)
                    for t in sorted(h.snapshots)
                ],
            }
    checks = GRAPH_CHECKS[first_check:]

    fig, (ax_t, ax_k) = plt.subplots(1, 2, figsize=(10.6, 4.6))

    for k, colour in ((0, COLOR_LAYER1), (1, COLOR_ACCENT), (30, COLOR_LAYER2)):
        m = series[k]
        ax_t.plot(
            m["round"],
            np.array(m["realized_rank"]) / potentials[k],
            color=colour,
            marker="o",
            markersize=3.5,
            label=f"{k} autonomous edge" + ("" if k == 1 else "s"),
        )
    ax_t.axhline(1.0, color=COLOR_INSTRUMENT, linestyle=":", linewidth=1.0)
    ax_t.set_xlabel("round")
    ax_t.set_ylabel("realized cycle rank / potential")
    ax_t.set_ylim(0, 1.08)
    ax_t.set_title("Independent loops surviving in circulation")
    ax_t.legend(loc="center right")
    left = readings[0]["log10_share_of_volume_at_or_below_cutoff"]
    annotate(
        ax_t,
        "The potential graph is unchanged throughout: no edge is deleted, no\n"
        "transaction is forbidden, no price is refused. Loops disappear only\n"
        "because the flow across them decays to nothing"
        + ("." if left is None else f" (10^{left:.0f} of volume)."),
        loc="lower left",
    )

    finals = [series[k]["realized_rank"][-1] / potentials[k] for k in AUTONOMOUS_EDGES]
    ax_k.plot(AUTONOMOUS_EDGES, finals, color=COLOR_ACCENT, marker="o", markersize=5)
    ax_k.set_xlabel("edges from the financial layer into the intermediary")
    ax_k.set_ylabel("surviving fraction of cycle rank")
    ax_k.set_ylim(0, 1.0)
    ax_k.set_title("The same discontinuity, in topological terms")
    annotate(
        ax_k,
        f"Zero edges leaves {finals[0]:.1%} of the loop structure. One edge leaves\n"
        f"{finals[1]:.0%}. This is the stage A2 result restated: what the economy\n"
        "loses when the intermediary is cut off is not volume, it is the\n"
        "independent paths circulation could take.",
        loc="lower right",
    )

    fig.suptitle(
        "Potential cycle rank "
        f"{potentials[0]}, realized {series[0]['realized_rank'][-1]}, "
        "with nothing deleted.",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    path = save(fig, FIGURES / "a2c_fig10_cycle_rank_collapse.png")
    return path, {
        "potential_rank": potentials,
        "final_fraction": dict(
            zip([str(k) for k in AUTONOMOUS_EDGES], finals, strict=True)
        ),
        "series": {str(k): v for k, v in series.items()},
        "cutoff": {str(k): v for k, v in readings.items()},
        "cutoff_zero_edges_by_snapshot": zero_arm,
        "graph_unchanged": graph_unchanged(checks),
    }


# ---------------------------------------------------------------------------


def evaluate(
    rounds: int, seeds: int, f9: dict, f10: dict, extras: dict | None = None
) -> list[Criterion]:
    out: list[Criterion] = []
    m = f9["two_layer"]

    out.append(
        Criterion(
            "A2c-1  net displacement is flat while circulation grows",
            max(m["gradient_norm"]) / min(m["gradient_norm"]) < 3.0
            and m["flow_norm"][-1] / m["flow_norm"][0] > 10.0,
            f"gradient magnitude stays within a factor of "
            f"{max(m['gradient_norm']) / min(m['gradient_norm']):.2f}; total flow "
            f"grows x{m['flow_norm'][-1] / m['flow_norm'][0]:.1f}",
        )
    )
    out.append(
        Criterion(
            "A2c-2  the churn ratio rises by an order of magnitude",
            f9["ratio_end"] / f9["ratio_start"] > 10.0,
            f"circulation over net displacement rises "
            f"{f9['ratio_start']:.1f} -> {f9['ratio_end']:.0f}",
        )
    )
    out.append(
        Criterion(
            "A2c-3  the harmonic component is diluted, not removed",
            max(m["harmonic_norm"]) / min(m["harmonic_norm"]) < 3.0
            and m["harmonic_share"][-1] < 0.1 * m["harmonic_share"][0],
            f"magnitude within a factor of "
            f"{max(m['harmonic_norm']) / min(m['harmonic_norm']):.2f} while its "
            f"share falls {m['harmonic_share'][0]:.2e} -> "
            f"{m['harmonic_share'][-1]:.2e}. Reporting the share alone would have "
            "said it vanished",
        )
    )

    frac = f10["final_fraction"]
    out.append(
        Criterion(
            "A2c-4  cycle rank collapses with no edge deleted",
            # The second half of the name is read off the round-by-round
            # comparison and not asserted in the detail alone.
            frac["0"] < 0.10 and bool(f10.get("graph_unchanged", False)),
            f"potential rank {f10['potential_rank'][0]}, realized fraction "
            f"{frac['0']:.3f}, and the potential graph is identical throughout",
        )
    )
    out.append(
        Criterion(
            "A2c-5  one autonomous edge restores most of the loop structure",
            frac["1"] > 0.5,
            f"0 edges {frac['0']:.3f}, 1 edge {frac['1']:.3f}, "
            f"30 edges {frac['30']:.3f}",
        )
    )

    # cross-seed
    collapsed, rescued = [], []
    by_seed: list[dict] = []
    continuation: list[dict] = []
    continuation_one_edge: list[dict] = []
    for gs in range(seeds):
        a = go(three_layer(gs, 0), rounds=rounds, seed=gs)
        b = go(three_layer(gs, 1), rounds=rounds, seed=gs)
        collapsed.append(
            cycle_rank(
                realized_adjacency(a.snapshots[max(a.snapshots)], a.epsilon_absolute)
            )
            / cycle_rank(a.adjacency)
        )
        rescued.append(
            cycle_rank(
                realized_adjacency(b.snapshots[max(b.snapshots)], b.epsilon_absolute)
            )
            / cycle_rank(b.adjacency)
        )
        if extras is not None:
            by_seed.append(
                {"seed": gs, "zero_edges": last_reading(a), "one_edge": last_reading(b)}
            )
            continuation.append(continued(gs, a))
            continuation_one_edge.append(continued(gs, b, edges=1))
    out.append(
        Criterion(
            "A2c-6  the collapse and the rescue hold across graph seeds",
            max(collapsed) < 0.10 and min(rescued) > 0.5,
            f"{seeds} seeds: collapsed {min(collapsed):.3f}-{max(collapsed):.3f}, "
            f"rescued {min(rescued):.3f}-{max(rescued):.3f}",
        )
    )

    # the honest limitation
    two = go(NetworkSpec(seed=0), rounds=rounds, seed=0)
    ranks = [
        cycle_rank(realized_adjacency(two.snapshots[t], two.epsilon_absolute))
        for t in sorted(two.snapshots)
    ]
    out.append(
        Criterion(
            "A2c-7  limitation recorded: cycle rank saturates when nothing dies",
            max(ranks[1:]) - min(ranks[1:]) <= 1,
            f"in the two-layer model the realized rank is flat at {ranks[-1]} after "
            f"the transient, against a potential {cycle_rank(two.adjacency)}. Cycle "
            "rank is a binary count, so it moves only where edges drop out of the "
            "realized graph. It is informative in the three-layer economy and "
            "inert in the two-layer one, and this criterion exists to keep that "
            "on the record",
        )
    )
    if extras is not None:
        extras["cross_seed"] = {
            "collapsed": [sig(x) for x in collapsed],
            "rescued": [sig(x) for x in rescued],
            "by_seed": by_seed,
        }
        extras["continuation"] = continuation
        extras["continuation_one_edge"] = continuation_one_edge
        extras["two_layer"] = {
            "round": [int(t) for t in sorted(two.snapshots)],
            "realized_rank": ranks,
            "potential_rank": cycle_rank(two.adjacency),
            "by_snapshot": [
                cutoff_reading(two.snapshots[t], two.adjacency, two.epsilon_absolute)
                for t in sorted(two.snapshots)
            ],
        }
    return out


DEFINITIONS = {
    "realized graph": (
        "a directed edge is in it when the flow across it in that round exceeds "
        "the cutoff; cycle rank is taken on the underlying undirected graph"
    ),
    "cutoff": (
        "1e-4 of the mean flow per potential edge at round 0, fixed for the run "
        "(NetworkHistory.epsilon_absolute)"
    ),
    "positive_rank": (
        "cycle rank counting every edge whose flow is a positive floating-point "
        "number, however small"
    ),
    "decades_of_cutoff_reading_this_graph": (
        "log10 of the smallest flow above the cutoff minus log10 of the largest "
        "flow at or below it; no flow lies between, so every cutoff in that band "
        "reads the same realized graph"
    ),
    "flow_norm, 'total flow', 'circulation'": (
        "the Euclidean norm of net flow per undirected edge of the realized "
        "graph, flow[i, j] - flow[j, i]; it is not gross volume, which is "
        "recorded beside it"
    ),
    "harmonic, every triangle filled": (
        "the part of net flow orthogonal to the gradient and to every triangle's "
        "boundary; A2c-3 is read on this"
    ),
    "harmonic, no face filled": (
        "everything orthogonal to the gradient, which is the curl part and the "
        "harmonic part of the other split added together"
    ),
    "continuation": (
        "the same arm, seed and configuration run to CONTINUE_ROUNDS instead of "
        "the registered length; it reproduces the registered run at every "
        "snapshot the two share"
    ),
    "growth_of_the_ratio_to_the_gradient_norm_on_the_same_run": (
        "a measure of flow over the gradient norm at the last snapshot, divided "
        "by the same at the first; on net_flow_per_edge_norm this is A2c-2's "
        "ratio_end over ratio_start"
    ),
    "round": "a unit of trend, not a calendar period",
}


def unscored_lines(f9: dict, f10: dict, extras: dict, checks: list[dict]) -> list[str]:
    zero = f10["cutoff"]["0"]
    choice = hodge_choice(f9["two_layer"])
    bare, filled = choice["no_face_filled"], choice["every_triangle_filled"]
    cont = extras["continuation"]
    settle = [
        c["positive_rank_equals_cutoff_rank_from_snapshot"]
        for c in cont
        if c["positive_rank_equals_cutoff_rank_from_snapshot"] is not None
    ]
    span = f"{min(settle)}-{max(settle)}" if len(settle) == len(cont) and cont else "none"
    lines = [
        f"  cutoff     zero edges, last round: rank {zero['cutoff_rank']} above the "
        f"cutoff, {zero['positive_rank']} over every positive flow, potential "
        f"{zero['potential_rank']}",
        f"             the {zero['directed_edges_positive_at_or_below_cutoff']} "
        f"directed edges between the two carry 10^"
        f"{zero['log10_share_of_volume_at_or_below_cutoff']} of the volume; the "
        f"same graph is read at every cutoff across "
        f"{zero['decades_of_cutoff_reading_this_graph']} decades",
    ]
    if cont:
        lines.append(
            f"  continued  {len(cont)} seeds to {cont[0]['rounds']} rounds: "
            f"positive rank equals cutoff rank from snapshot {span} on; "
            f"cutoff rank one value per seed after round 0: "
            f"{all(len(c['cutoff_rank_values_after_round_0']) == 1 for c in cont)}"
        )
    one = extras.get("continuation_one_edge", [])
    if one:
        fractions = [c["positive_rank_over_potential_at_last_snapshot"] for c in one]
        lines.append(
            f"             one edge, at the last snapshot: positive rank equals "
            f"cutoff rank in "
            f"{sum(c['positive_rank_at_last_snapshot'] == c['cutoff_rank_at_last_snapshot'] for c in one)}"
            f" of {len(one)} seeds, {min(fractions):.3f}-{max(fractions):.3f} of "
            f"potential"
        )
    lines += [
        f"  splits     gradient the same in both: "
        f"{choice['splits_agree_at_every_snapshot']}; no face filled, the part "
        f"outside the gradient moves x"
        f"{bare['outside_the_gradient_norm_max_over_min']:.2f}; every triangle "
        f"filled, curl x{filled['curl_norm_last_over_first']:.2f} and harmonic "
        f"within x{filled['harmonic_norm_max_over_min']:.2f}; read by "
        f"{', '.join(choice['criteria_that_read_the_choice']) or 'none'}",
        f"  flow       gross volume x{choice['growth_on_the_same_run']['gross_volume']}, "
        f"net flow summed x{choice['growth_on_the_same_run']['net_flow_per_edge_summed']}, "
        f"its norm x{choice['growth_on_the_same_run']['net_flow_per_edge_norm']}",
        f"  graph      {len(checks)} runs, "
        f"{sum(c['rounds'] for c in checks)} rounds, "
        f"{sum(c['rounds_graph_equal_to_opening'] for c in checks)} closing on "
        f"the opening graph",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=600)
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    apply_style()
    GRAPH_CHECKS.clear()
    print("stage A2c: cycle structure")
    print(f"  rounds={args.rounds} seeds={args.seeds}\n")

    p9, f9 = figure_9(args.rounds, args.seed)
    p10, f10 = figure_10(args.rounds, args.seed)
    for p in (p9, p10):
        print(f"  wrote {p.relative_to(ROOT)}")
    print()

    extras: dict = {}
    criteria = evaluate(args.rounds, args.seeds, f9, f10, extras)
    print("criteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    checks = list(GRAPH_CHECKS)
    print("\nrecorded, not scored")
    for line in unscored_lines(f9, f10, extras, checks):
        print(line)

    m = f9["two_layer"]
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "a2c_cycle_structure.json"
    path.write_text(
        json.dumps(
            {
                "stage": "A2c",
                "rounds": args.rounds,
                "seed": args.seed,
                "seeds_tested": args.seeds,
                "churn": {k: v for k, v in f9.items() if k != "two_layer"},
                "cycle_rank": {
                    "potential_rank": {
                        str(k): v for k, v in f10["potential_rank"].items()
                    },
                    "final_fraction": f10["final_fraction"],
                },
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in criteria
                ],
                "definitions": DEFINITIONS,
                "series": {
                    "two_layer": {
                        k: (v if k in ("round", "realized_rank", "splits_agree")
                            else [sig(x) for x in v])
                        for k, v in m.items()
                    },
                    "three_layer_realized_rank": f10["series"],
                },
                "hodge_choice": hodge_choice(m),
                "cutoff": {
                    "by_autonomous_edges": f10["cutoff"],
                    "zero_edges_by_snapshot": f10["cutoff_zero_edges_by_snapshot"],
                    "by_seed": extras["cross_seed"]["by_seed"],
                    "two_layer_by_snapshot": extras["two_layer"],
                },
                "cross_seed": {
                    "collapsed": extras["cross_seed"]["collapsed"],
                    "rescued": extras["cross_seed"]["rescued"],
                },
                "continuation": extras["continuation"],
                "continuation_one_edge": extras["continuation_one_edge"],
                "potential_graph": {
                    "runs": len(checks),
                    "rounds": sum(c["rounds"] for c in checks),
                    "rounds_closing_on_the_opening_graph": sum(
                        c["rounds_graph_equal_to_opening"] for c in checks
                    ),
                    "unchanged_in_every_run": graph_unchanged(checks),
                    "by_run": checks,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
