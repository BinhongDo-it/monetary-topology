"""Stage B5's cycle machinery: quotes to squares, split into index and friction.

Registered in ``docs/b5_orphan_prereg.md`` §2.3 and §3. The theorems are in
``docs/b4_directed_edges.md``; this module is their arithmetic on one position
edge.

The graph
---------

There is **one position edge**, ``ARS <-> USD``, and that is not a simplification
but the reason this carrier reaches squares and cannot reach slices: a slice
cycle needs a second position edge to walk to, and there is not one
(``b5_orphan_prereg.md`` §2.2).

What varies is the agent factor. Argentina prices the same conversion five ways
on the same day and which price applies to you is fixed by regulation, so every
cycle here is **two agents on one edge**, which is Theorem 1's square.

From a quote to a weight
------------------------

With ``rate`` in pesos per dollar and ``bid < ask``, buying a dollar costs
``ask`` pesos and selling one gets ``bid``::

    omega(ARS -> USD) = -log(ask)
    omega(USD -> ARS) = +log(bid)

Theorem 6 splits each two-way edge into an antisymmetric and a symmetric part,
and both come out as the quantities the availability check named::

    w_hat = (f - b)/2 = -log sqrt(bid*ask)    minus the log geometric mid
    w_bar = (f + b)/2 = (1/2) log(bid/ask)    minus half the log spread, <= 0

so for two classes facing the same conversion::

    S - S' = 2 (w_hat_a - w_hat_b) = 2 log(mid_b / mid_a)      the headline
    S + S' = 2 (w_bar_a + w_bar_b) = log(bid_a/ask_a)
                                     + log(bid_b/ask_b)        the friction

**The headline needs only the two mid quotes**: the spread cancels by
construction, which is what makes the number safe from the objection that it is
a bid-ask artefact. **Reporting a single orientation ``S`` is prohibited**
(``b4_directed_edges.md`` §5.1): in a thin market its largest component is the
spread.

A single-quote series has ``bid = ask``, so its ``w_bar`` is exactly zero and it
carries no friction. That is why MEP and CCL enter the headline and cannot enter
the column beside it, and why a synthetic spread for them is prohibited rather
than merely unavailable (``b5_orphan_prereg.md`` §3.3).

What is deliberately not here
-----------------------------

**No slice-against-square decomposition.** Theorem 2 does not extend to directed
graphs: directed cycles form a cone and a cone has no direct-sum decomposition
(``PROJECT_PLAN.md`` §12.10, ``b4`` §6). There is also no second position edge to
build one from.

**No agent-edge weights invented.** The agent legs are written into the field as
zeros and then **looked up** rather than assumed, because ``b1_theorem.md`` §8 is
about what happens when that assumption fails, and a function that hard-codes an
assumption cannot report its violation.
"""

from __future__ import annotations

import math

import numpy as np

from monetary_topology import directed
from monetary_topology.parallel_rates import SERIES

#: The two positions. Pesos and dollars, in that order, so that
#: ``vertex(agent, position) = agent * N_POSITIONS + position`` matches
#: ``product_graph.vertex`` and ``directed.directed_square``.
ARS, USD = 0, 1
N_POSITIONS = 2


def quote_legs(row: dict, fields: tuple[str, ...]) -> tuple[float, float]:
    """``(bid, ask)`` for one class on one date.

    A single-quote series returns the same number twice. That is the honest
    encoding of "this market publishes no spread": it makes ``w_bar`` exactly
    zero rather than approximately zero, so a friction column built on it is
    visibly empty instead of quietly small.
    """
    if len(fields) == 1:
        one = row[fields[0].lower()]
        return float(one), float(one)
    return float(row["compra"]), float(row["venta"])


def edge_weights(bid: float, ask: float) -> tuple[float, float]:
    """``(omega(ARS->USD), omega(USD->ARS))`` from one two-sided quote."""
    if bid <= 0 or ask <= 0:
        raise ValueError(f"non-positive quote bid={bid} ask={ask}")
    return -math.log(ask), math.log(bid)


def build_field(quotes: dict[str, tuple[float, float]],
                keys: tuple[str, ...]) -> directed.DirectedField:
    """The directed field on ``Gamma`` for one date.

    ``quotes`` maps a class name to ``(bid, ask)``. The agent legs are written in
    **explicitly as zeros in both directions**, because Theorem 1's load-bearing
    assumption is that they carry no weight and ``directed_square`` looks them up
    rather than assuming them. Writing them here is what makes the assumption a
    statement in the data instead of a fact about the code.
    """
    weights: dict[tuple[int, int], float] = {}
    for a, key in enumerate(keys):
        bid, ask = quotes[key]
        fwd, rev = edge_weights(bid, ask)
        weights[(a * N_POSITIONS + ARS, a * N_POSITIONS + USD)] = fwd
        weights[(a * N_POSITIONS + USD, a * N_POSITIONS + ARS)] = rev
    for a in range(len(keys)):
        for b in range(len(keys)):
            if a == b:
                continue
            for pos in (ARS, USD):
                weights[(a * N_POSITIONS + pos, b * N_POSITIONS + pos)] = 0.0
    return directed.DirectedField(weights, len(keys) * N_POSITIONS)


def index_matrix(quotes: dict[str, tuple[float, float]],
                 keys: tuple[str, ...]) -> np.ndarray:
    """``D[a, b] = S - S' = 2 log(mid_b / mid_a)``, the closed form.

    Antisymmetric by construction, and **its diagonal is exactly zero because it
    is a difference and not because of an ``if``**. Criterion B5-2 reads that
    diagonal off this matrix rather than short-circuiting on ``a == b``, which
    would test the short circuit.
    """
    logs = np.array([
        math.log(math.sqrt(quotes[k][0] * quotes[k][1])) for k in keys
    ])
    return 2.0 * (logs[None, :] - logs[:, None])


def friction_matrix(quotes: dict[str, tuple[float, float]],
                    keys: tuple[str, ...]) -> np.ndarray:
    """``F[a, b] = S + S' = log(bid_a/ask_a) + log(bid_b/ask_b)``.

    Symmetric, non-positive, and **exactly zero wherever either class publishes
    a single quote**. No-arbitrage locks the sign: a round trip through one
    dealer cannot pay.
    """
    spreads = np.array([
        math.log(quotes[k][0] / quotes[k][1]) for k in keys
    ])
    return spreads[None, :] + spreads[:, None]


def square_via_machinery(field: directed.DirectedField, a: int, b: int
                         ) -> tuple[float, float]:
    """``(S, S')`` walked through ``directed.directed_square``.

    The independent path that criterion B5-1 checks the closed forms against.
    ``a == b`` is not permitted: with one class the square degenerates to a
    self-loop at the agent legs, and a position is not a move.
    """
    if a == b:
        raise ValueError(
            "a square needs two distinct classes; the trivial case is read off "
            "the diagonal of index_matrix, not walked"
        )
    return directed.directed_square(field, a, b, ARS, USD, N_POSITIONS)


def quotes_for_date(panel: dict, when: str, keys: tuple[str, ...]
                    ) -> dict[str, tuple[float, float]] | None:
    """``{class: (bid, ask)}`` for one date, or ``None`` if any class is missing.

    ``b5_orphan_prereg.md`` §7: a date enters an analysis only if every class the
    criterion needs has a quote on it. Returning ``None`` rather than a partial
    dictionary is what keeps that rule from being negotiable at the call site.
    """
    out = {}
    for key in keys:
        row = panel.get(key, {}).get(when)
        if row is None:
            return None
        out[key] = quote_legs(row, SERIES[key][1])
    return out


def daily_matrices(panel: dict, dates: list[str], keys: tuple[str, ...]
                   ) -> tuple[list[str], np.ndarray, np.ndarray]:
    """``(dates_used, index, friction)`` stacked over dates.

    Both stacks are computed **on the same dates from the same quotes**, which is
    what lets criterion B5-8 read a divergence between them as a finding rather
    than as a difference in coverage. A confound that moves the peso moves both.
    """
    used, index, friction = [], [], []
    for when in dates:
        quotes = quotes_for_date(panel, when, keys)
        if quotes is None:
            continue
        used.append(when)
        index.append(index_matrix(quotes, keys))
        friction.append(friction_matrix(quotes, keys))
    if not used:
        return [], np.empty((0, len(keys), len(keys))), np.empty(
            (0, len(keys), len(keys))
        )
    return used, np.array(index), np.array(friction)


def agent_quotes(classes: dict, keys: tuple[str, ...], dates: list[str]):
    """``(date, {class: (bid, ask)})`` for the dates **every** class in ``keys``
    quotes.

    The same §7 row filter ``quotes_for_date`` applies, expressed over the
    ``{class: {date: (bid, ask)}}`` shape ``load_agent_classes`` returns rather
    than over a raw panel. The ``for``/``else`` is load-bearing: the body runs
    only when no key broke out, so a partial row can never be yielded.
    """
    for when in dates:
        row = {}
        for key in keys:
            got = classes[key].get(when)
            if got is None:
                break
            row[key] = got
        else:
            yield when, row


def pair_index_series(classes: dict, left: str, right: str,
                      dates: list[str]) -> list[tuple[str, float]]:
    """``[(date, S − S')]`` for one pair, on the dates both classes quote.

    **One definition, two callers.** B5-6 through B5-8 and B5-14 all read this
    series, and a second copy of it would be a second truth about what the
    headline quantity is.
    """
    out = []
    for when, quotes in agent_quotes(classes, (left, right), dates):
        out.append((when, float(index_matrix(quotes, (left, right))[0, 1])))
    return out


def rms(values: np.ndarray) -> float:
    """Root mean square, the aggregation the claim is stated in.

    ``b5_orphan_prereg.md`` §3.4: a claim stated in logs is aggregated in logs.
    Returns ``nan`` on an empty sample rather than zero, because an empty arm
    must not look like a quiet one.
    """
    if values.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(np.square(values))))
