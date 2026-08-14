"""Availability check for a continuous `C`: is the continuum constructible.

**Status: availability check, not a stage and not a pre-registration.** It scores
nothing, registers nothing, writes no file, and no number in `RESULTS.md` comes
from it. It answers one question, which is whether the object a continuous-`C`
stage would need can be built at all, in the same place in the order that
`b5_orphan_availability.md` and `b6_cuba_availability.md` occupy for their
stages: the check comes before the pre-registration, not after.

Why the question is live
------------------------

`docs/a4_causal_primitive.md` §11 closes A4 with `A(X)` void. The reason is not
a threshold and not the choice of summary: `A(X)` is a ratio across two arms and
no competitor is readable in both, because the two arms are two economies with
different state and a ratio between them measures the state difference as much
as the mechanism difference. A continuous `C` replaces that ratio with a slope
along a path, which does not need both endpoints live at once.

And §10 asserts `C = 0 ⇒ H¹ ≡ 0` from a measured fact, that the centrality
spread under `uniform_access` is exactly zero. A continuum turns `H¹` from a
switch into a regressor, which is the form the framework's own chain
`C → H¹ → D` is stated in and has never been measured in.

What `uniform_access` actually is, and why this is not one switch
-----------------------------------------------------------------

Reading `network.py`, the flag collapses **five** things, each with its own
comment saying the collapse follows from a complete graph having no layers:

1. the adjacency, to a complete graph with no seed entering it;
2. the payroll incidence, from a quarter of the financial layer paying half the
   households to everyone paying everyone;
3. the discretionary routing, which stops subtracting the payroll mask;
4. the spending propensities, from two layer values to one claim-weighted value;
5. the opening holdings, to a flat split or to §9.3's permuted marginal.

Four of the five interpolate. **The third does not, and the reason matters.**
The subtraction is skipped only because at the endpoint the payroll mask is the
whole matrix, so subtracting would empty the discretionary graph and the null
arm would be a dead economy reporting clean numbers, which is what that comment
in `network.py` says. At any interior `c` the mask is partial and the
subtraction is well defined. So a continuum that always subtracts is coherent
everywhere **and its endpoint is not A4's `C = 0` arm**. That has to be
registered before anything runs rather than discovered from a discontinuity in
the output, and it is the main thing this file exists to say.

What is measured here
---------------------

Only constructibility, and only on the graph. Interpolation is by edge
addition: `A(c)` is the stratified adjacency with every remaining ordered pair
present independently with probability `c`, so `c = 0` is the stratified graph
exactly and `c = 1` is the complete graph exactly, and edges are monotone in
`c` by construction.

The question is whether a continuum in the construction parameter is a
continuum in the quantity that carries the mechanism. Centrality is normalised
in-degree and `terms = base (1 + kappa (1 - c_i))`, so the terms dispersion the
loop sum is built from is proportional to the centrality dispersion. If that
dispersion sits flat and then falls off a cliff, the sweep would be a two-point
comparison wearing a grid, and the stage should not be written that way.

Not measured here, and named so the gap is visible: `H¹` itself. The loop sum
is defined on the `terms` matrix, which lives on `A3Model`. `A4Model` subclasses
`Network` and has no edge field at all, so there is no holonomy to compute on
it. A continuous-`C` stage that wants `C → H¹ → D` is therefore an A3-side
measurement with no competitors in it, and a continuous-`C` stage that wants the
four competitors is a separate A4-side one. Those are two stages and this file
does not choose between them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import centrality  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    NetworkSpec,
    build_graph,
)

#: A fresh stream, so the added edges cannot correlate with the stratified
#: graph's own draw (`spec.seed`), the payroll receiver order (`seed + 4241`) or
#: the opening permutation (`seed + 9301`).
_SHORTCUT_OFFSET = 20_749

#: The grid. Dense near zero because that is where a threshold would sit if the
#: framework's account is right, and the endpoints are exact by construction
#: rather than by a limit.
GRID: tuple[float, ...] = (
    0.0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4,
    0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0,
)


def blend(spec: NetworkSpec, c: float) -> np.ndarray:
    """The stratified adjacency with each remaining pair added at rate `c`.

    `c = 0` returns the stratified graph bit for bit and `c = 1` returns the
    complete graph, both exactly rather than in a limit, so the sweep's ends are
    the two objects A4 already ran rather than approximations of them.
    """
    base = build_graph(spec)
    if c <= 0.0:
        return base
    n = spec.size
    if c >= 1.0:
        return 1.0 - np.eye(n)
    rng = np.random.default_rng(spec.seed + _SHORTCUT_OFFSET)
    extra = (rng.random((n, n)) < c).astype(float)
    np.fill_diagonal(extra, 0.0)
    return np.clip(base + extra, 0.0, 1.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()

    print(
        "\nAVAILABILITY  does the construction parameter carry a continuum\n"
        "\n  Interpolation is edge addition. `terms = base (1 + k (1 - c_i))`,"
        " so the\n  dispersion the loop sum is built from is proportional to the"
        " centrality\n  dispersion below. Five seeds, means.\n"
    )
    print(
        "     c      edges     mean deg   centrality spread   centrality sd"
        "   layer gap"
    )
    for c in GRID:
        rows = []
        for seed in range(args.seeds):
            spec = NetworkSpec(seed=seed)
            a = blend(spec, c)
            cen = centrality(a)
            k = spec.layer1_size
            rows.append(
                (
                    float(a.sum()),
                    float(a.sum(axis=1).mean()),
                    float(cen.max() - cen.min()),
                    float(cen.std()),
                    # The thing the stratification is: how far the financial
                    # layer's mean position sits above the production layer's.
                    # A spread that survives while this closes would be a
                    # continuum in dispersion and not in structure.
                    float(cen[:k].mean() - cen[k:].mean()),
                )
            )
        m = np.array(rows).mean(axis=0)
        print(
            f"  {c:5.2f}  {m[0]:9.0f}  {m[1]:10.2f}  {m[2]:17.6f}"
            f"  {m[3]:14.6f}  {m[4]:10.6f}"
        )

    print(
        "\n  Endpoints are exact: c = 0 is `build_graph(spec)` bit for bit and"
        "\n  c = 1 is `1 - eye(n)`, which is what `uniform_access` returns."
    )
    for seed in range(args.seeds):
        spec = NetworkSpec(seed=seed)
        lo = np.array_equal(blend(spec, 0.0), build_graph(spec))
        hi = np.array_equal(
            blend(spec, 1.0),
            build_graph(spec.replace(uniform_access=True)),
        )
        print(f"    seed {seed}: c=0 matches stratified {lo}, "
              f"c=1 matches uniform {hi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
