"""B1: the hole taxonomy, executed.

``docs/b1_setup.md`` section 5 rules that deleting an edge has two distinct
consequences, a **puncture** and a **disconnection**, and quotes measured numbers
for both. Those numbers came from a script that was never committed, so the one
claim in this repository that depends on the square complex had no source. This
is the source.

Usage::

    python experiments/b1_holes.py

Writes ``results/b1_holes.json``. No data is retrieved and no seed is used: every
graph here is constructed and every number is exact integer linear algebra.

What this is not
----------------
It cannot move a figure stage B2 reports. ``docs/b1_theorem.md`` section 12.2:
Theorem 3's quantity is a sum around a closed walk in the 1-skeleton and is
invariant under every choice of `C_2`. The square complex is load-bearing in
exactly one place in this repository, and this file is that place.

What it found that was not asked for
------------------------------------
**B1H-7.** Section 5 registers "the test is whether `Gamma` is still connected
after the deletion". That test separates a disconnection from everything else. It
does **not** separate a puncture from a no-event: a boundary edge of the same
filled grid leaves the graph connected and leaves `dim H^1` at zero, because it
lies in one 2-cell rather than two, so `rank d_2` falls exactly as fast as `b_1`
does. The connectivity test is necessary and is not sufficient.

**B1H-8.** The sufficient condition depends on `b_1(G)`, and the accreditation row
survives on the carrier it actually lives on. On a **star** `G`, which is what
``tier_positions`` is and what most of section 5's transitions are, barring a
class from one position raises `dim H^1`. On a `G` carrying a cycle the identical
operation raises nothing, because the 2-cells that die are dependent on the ones
that survive. Section 5's verdict is right and the reason it gives is not the
reason it is right.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from monetary_topology.product_graph import (  # noqa: E402
    box_product,
    complete_agent_graph,
    complex_ranks,
    delete_edge,
    hole_kind,
    path_graph,
    product_squares,
    squares,
    tier_positions,
    vertex,
)

RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def filled_grid(rows: int, cols: int) -> tuple[np.ndarray, list[list[int]]]:
    """`P_rows box P_cols` with every unit square filled.

    Section 5's demonstration carrier. A grid is a Cartesian product of two
    paths, so its unit squares are exactly the Cartesian squares of the product
    and no cell is chosen by hand.
    """
    g, h = path_graph(cols), path_graph(rows)
    return box_product(g, h), product_squares(g, h)


def dumbbell() -> np.ndarray:
    """Two triangles joined by a bridge. `b_1 = 2` and the bridge is a cut edge."""
    adj = np.zeros((6, 6), dtype=int)
    for u, v in [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3), (2, 3)]:
        adj[u, v] = adj[v, u] = 1
    return adj


def bar_class_from_position(
    adj_g: np.ndarray, m: int, position: int, n_barred: int
) -> tuple[str, int, int]:
    """Delete the edge `cash -> position` for the first ``n_barred`` classes.

    Section 5's accreditation row: below the threshold the edge is absent at any
    price, for a whole set of classes rather than for one. Returns the verdict on
    the last deletion and the `dim H^1` before and after the whole set.
    """
    n = np.asarray(adj_g).shape[0]
    adj = box_product(adj_g, complete_agent_graph(m))
    cells = squares(adj_g, m)
    before = complex_ranks(adj, cells).dim_h1
    verdict = "neither"
    for a in range(n_barred):
        u, v = vertex(a, 0, n), vertex(a, position, n)
        verdict, _, _ = hole_kind(adj, cells, u, v)
        adj, cells = delete_edge(adj, u, v, cells)
    return verdict, before, complex_ranks(adj, cells).dim_h1


def criteria() -> tuple[list[Criterion], dict]:
    out: list[Criterion] = []
    record: dict = {}

    # ---- B1H-1: the filled grid is contractible -------------------------
    adj, cells = filled_grid(5, 6)
    base = complex_ranks(adj, cells)
    record["grid_5x6"] = base.__dict__ | {"cells": len(cells)}
    out.append(
        Criterion(
            "B1H-1  the filled 5x6 grid has no first cohomology",
            (base.vertices, base.edges, base.components, base.b1, base.rank_d2,
             base.dim_h1) == (30, 49, 1, 20, 20, 0),
            f"{base.line()}   cells={len(cells)}   "
            "(b1_setup section 5 quotes b1=20, rank d2=20, dim H1=0)",
        )
    )

    # ---- B1H-2: an interior edge is a puncture --------------------------
    i, j = vertex(2, 2, 6), vertex(2, 3, 6)
    kind, before, after = hole_kind(adj, cells, i, j)
    record["grid_interior_edge"] = {"kind": kind, "after": after.__dict__}
    out.append(
        Criterion(
            "B1H-2  deleting an interior grid edge is a puncture",
            kind == "puncture"
            and (before.b1, after.b1) == (20, 19)
            and (before.rank_d2, after.rank_d2) == (20, 18)
            and (before.components, after.components) == (1, 1)
            and (before.dim_h1, after.dim_h1) == (0, 1),
            f"b1 {before.b1}->{after.b1}, rank d2 {before.rank_d2}->{after.rank_d2}, "
            f"c {before.components}->{after.components}, "
            f"dim H1 {before.dim_h1}->{after.dim_h1}   verdict={kind}   "
            "(section 5 quotes 20->19, 20->18, c fixed, 0->1)",
        )
    )

    # ---- B1H-3: a bridge is a disconnection -----------------------------
    d = dumbbell()
    kind_d, before_d, after_d = hole_kind(d, [], 2, 3)
    record["dumbbell_bridge"] = {"kind": kind_d, "after": after_d.__dict__}
    out.append(
        Criterion(
            "B1H-3  deleting a dumbbell bridge is a disconnection",
            kind_d == "disconnection"
            and (before_d.components, after_d.components) == (1, 2)
            and (before_d.b1, after_d.b1) == (2, 2),
            f"c {before_d.components}->{after_d.components}, "
            f"b1 {before_d.b1}->{after_d.b1}   verdict={kind_d}   "
            "(section 5 quotes c 1->2 with b1 fixed at 2)",
        )
    )

    # ---- B1H-4: the bare graph is the other reading ---------------------
    bare = complex_ranks(adj, [])
    out.append(
        Criterion(
            "B1H-4  with no 2-cells, dim H1 = b1",
            bare.dim_h1 == bare.b1 == 20 and bare.rank_d2 == 0,
            f"{bare.line()}   "
            "(b1_theorem section 12.2 first row: no d1, so every 1-cochain is "
            "closed and dim H1 = b1)",
        )
    )

    # ---- B1H-5: Kunneth, numerically ------------------------------------
    # dim H1(Gamma) = b1(G) + b1(H). Asserted in b1_theorem section 12 from
    # Kunneth and never checked against a rank until now.
    cycle_g = path_graph(4)
    cycle_g[0, 3] = cycle_g[3, 0] = 1
    rows = []
    ok = True
    for label, g in [("star(4 tiers)", tier_positions(4)), ("cycle(4)", cycle_g)]:
        b1_g = len(np.transpose(np.nonzero(np.triu(g, 1)))) - g.shape[0] + 1
        for m in (3, 5, 8):
            h = complete_agent_graph(m)
            b1_h = m * (m - 1) // 2 - m + 1
            got = complex_ranks(box_product(g, h), squares(g, m)).dim_h1
            ok = ok and got == b1_g + b1_h
            rows.append(f"{label} x K{m}: {got} vs {b1_g}+{b1_h}")
    record["kunneth"] = rows
    out.append(
        Criterion(
            "B1H-5  dim H1(Gamma) = b1(G) + b1(H) on six shapes",
            ok,
            "; ".join(rows),
        )
    )

    # ---- B1H-6: the generalisation reproduces the special case ----------
    same = all(
        squares(g, m) == product_squares(g, complete_agent_graph(m))
        for g in (tier_positions(3), cycle_g)
        for m in (2, 3, 5)
    )
    out.append(
        Criterion(
            "B1H-6  product_squares reproduces squares element for element",
            same,
            "six shapes, walks compared as lists rather than as sets, so an "
            "ordering change would fail here rather than pass quietly",
        )
    )

    # ---- B1H-7: the connectivity test is not sufficient -----------------
    kind_b, before_b, after_b = hole_kind(adj, cells, vertex(0, 2, 6), vertex(0, 3, 6))
    record["grid_boundary_edge"] = {"kind": kind_b, "after": after_b.__dict__}
    out.append(
        Criterion(
            "B1H-7  a connected deletion need not be a puncture",
            kind_b == "neither"
            and after_b.components == 1
            and (before_b.dim_h1, after_b.dim_h1) == (0, 0)
            and (before_b.rank_d2, after_b.rank_d2) == (20, 19),
            f"grid boundary edge: c stays {after_b.components}, "
            f"b1 {before_b.b1}->{after_b.b1}, rank d2 {before_b.rank_d2}->"
            f"{after_b.rank_d2}, dim H1 {before_b.dim_h1}->{after_b.dim_h1}, "
            f"verdict={kind_b}.  Section 5's connectivity test separates a "
            "disconnection from the rest and does NOT separate a puncture from "
            "a no-event",
        )
    )

    # ---- B1H-8: the accreditation row, on both kinds of G ---------------
    star_rows, cycle_rows = [], []
    star_ok = cycle_ok = True
    for m in (3, 5, 8):
        for k in (1, 2):
            if k >= m:
                continue
            v_s, b_s, a_s = bar_class_from_position(tier_positions(4), m, 1, k)
            star_rows.append(f"star m={m} k={k}: {b_s}->{a_s} ({v_s})")
            star_ok = star_ok and a_s > b_s
            v_c, b_c, a_c = bar_class_from_position(cycle_g, m, 1, k)
            cycle_rows.append(f"cycle m={m} k={k}: {b_c}->{a_c} ({v_c})")
            cycle_ok = cycle_ok and a_c == b_c
    record["accreditation_star"] = star_rows
    record["accreditation_cycle_g"] = cycle_rows
    out.append(
        Criterion(
            "B1H-8  the accreditation row is a puncture on a star G and not on "
            "a G with a cycle",
            star_ok and cycle_ok,
            "STAR (tier_positions, the carrier section 5's rows live on): "
            + "; ".join(star_rows)
            + ".  CYCLE G: "
            + "; ".join(cycle_rows)
            + ".  Section 5's verdict on the accreditation row holds on the "
            "star. The reason it gives, that nothing disconnects, holds in "
            "both columns and therefore is not the reason",
        )
    )

    return out, record


def main() -> int:
    print("B1: the hole taxonomy, and the source for b1_setup section 5\n")
    cs, record = criteria()
    for c in cs:
        print(c.line())
    n_pass = sum(c.passed for c in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b1_holes.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B1H",
                **record,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in cs
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
