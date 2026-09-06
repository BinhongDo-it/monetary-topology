"""Industries as clusters of agents, with a Leontief matrix between them.

Stage A19. This module is the structure only: it builds the industry-by-industry
coefficient matrix and the agent-to-industry assignment. Nothing here runs a
model. ``network.py`` reads it when ``IndustrySpec.count`` is positive and does
not import it otherwise, so ``count = 0`` reproduces every earlier stage to the
last bit.

Two index conventions meet here and they point opposite ways
------------------------------------------------------------
``network.py`` uses ``a[i, j] == 1`` to mean **i can pay j**: the payer is the
row.

Leontief uses ``A[i, j]`` for the amount of industry ``i`` that industry ``j``
needs per unit of its own gross output: the **buyer is the column**, and the
buyer is the one who pays. So a positive ``A[i, j]`` corresponds to a payment
edge from ``j`` to ``i``, and the two matrices are transposes of each other on
the payment direction. Wiring one into the other without transposing is the
category error that produces a model where money flows up the supply chain.

Column sums are the intermediate input share
--------------------------------------------
``A``'s column ``j`` sums to the share of industry ``j``'s gross output spent on
intermediate goods. One minus that is value added. Published input-output tables
put value added between roughly 0.4 and 0.6 of gross output for most industries,
so the default ``column_sum`` of 0.5 sits in the middle of the observed range
rather than being picked for convenience. It is also the Hawkins-Simon condition:
a column summing to one or more describes an industry consuming more than it
produces, ``(I - A)`` is then singular or sign-indefinite, and every quantity
downstream of it is meaningless. The generator normalises columns to hit the
target exactly and ``check_feasible`` asserts it, so the condition is enforced
where the matrix is made rather than discovered halfway through a run.

Why the matrix is built in two steps
------------------------------------
Sampling every cell from a range gives a **dense** matrix in which every industry
buys from every other. Published tables are not like that: this project measured
26% zero cells in the BEA table and 0.00% in the ICIO table, and used the
difference to rule ICIO out on this axis. A dense matrix deletes the very object
Volume One section 8 is about, because a support set that starts full can never
contract. So edges are drawn first, weights second, and the zero cells are a
property of the draw rather than an afterthought.

Why the financial-to-production probability is not zero
-------------------------------------------------------
The manuscript's strong form said displacement out of the financial layer is
*exactly* zero. That form was withdrawn on 2026-08-16 in favour of the weak form,
that the ratio of within-layer circulation to cross-layer net flow is rising,
because the strong form was never measured and F7 supports the weak one
(Z.1 chain length 1.01 to 2.13, z = 7.94 after 1980). Hard-coding ``p_fp = 0``
would reinstate the withdrawn claim through the back door, and it would also
guarantee the support contraction that A2 is supposed to measure. So ``p_fp`` is
a swept small quantity with zero as one endpoint of the sweep, not the default.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Layer codes for ``industry_layers``.
FINANCIAL = 0
PRODUCTION = 1


@dataclass(frozen=True)
class IndustrySpec:
    """Industry structure. ``count = 0`` disables every path in this module."""

    #: Number of industries. Zero is off.
    count: int = 0

    #: How many of them sit in the financial layer; the rest are production.
    #: This is the explicit stratification rule the manuscript has never
    #: written down: Volume One section 3 leans on a two-layer split whose only
    #: operationalisation so far lives inside F7's Z.1 sector division. Here the
    #: rule is one integer and it is in the record.
    financial_count: int = 0

    #: Probability of an edge, by the layers of the buying and selling industry.
    #: Financial industries buy heavily from each other, production industries
    #: buy from each other and from finance, and finance buys thinly downward.
    p_ff: float = 0.60
    p_pp: float = 0.35
    p_pf: float = 0.40
    p_fp: float = 0.05

    #: Target column sum, the intermediate input share of gross output.
    column_sum: float = 0.50

    #: Shape of the gamma draw for edge weights before normalisation. Larger is
    #: more even; 1.0 is exponential and gives a heavy spread across suppliers.
    weight_shape: float = 2.0

    #: Share of nodes per layer that consider switching industry each round,
    #: taken from the bottom of last round's inflow. Zero is off and no
    #: switching code is reached.
    switch_rate: float = 0.0

    #: Price of a switch as a **relative gain threshold**: a node moves when the
    #: best industry's mean inflow exceeds its own industry's by more than this
    #: fraction. Dimensionless, so it has no upper bound. The payment itself is
    #: the same fraction of its own industry's mean inflow, capped at what the
    #: node holds, and it is paid to
    #: the financial layer weighted by in-degree. Training, certification and
    #: intermediation are bought from somewhere, and a cost that vanished
    #: instead of being paid would break the conservation assertion. Zero cost
    #: is one endpoint of the sweep rather than the default, because free
    #: switching and a recovery lag are directly opposed mechanisms: agents that
    #: leave a dying industry at no cost make the absorbing wall unobservable.
    switch_cost: float = 0.0

    #: An industry counts as damaged when its agent count falls below this
    #: share of the mean industry size in its layer. Zero is off. A share
    #: rather than a headcount so the bar moves with the model's scale instead
    #: of being a magic number that silently means something different at
    #: ``layer2_size = 500``.
    #:
    #: This is the stock reading of the sustainable level: how many agents are
    #: left. The flow reading, ``required_output`` against ``(I - A)^-1 f``, is
    #: the other one and is not wired in yet. Stock first because it *is* the
    #: support set, and the support set is Volume One section 8's central
    #: functional.
    min_share: float = 0.0

    #: How much harder it gets to enter a damaged industry, per round it has
    #: been damaged. Zero is off and reproduces the run without it. Infinity is
    #: the irreversible case: the entry threshold never clears, so nobody
    #: rejoins and the industry stays where it fell. One parameter spans the
    #: whole range, so "slow to recover" and "gone for good" are two points on a
    #: line rather than two code paths.
    recovery_friction: float = 0.0

    #: How much the recovery friction differs BETWEEN industries, as the log
    #: half-range of a geometric spread. Zero is off and every industry carries
    #: the same friction, reproducing the run without it.
    #:
    #: This is the one thing Volume Two section 3 actually asserts about
    #: formation lags: that they are heterogeneous, and that the heterogeneity
    #: is what does the work. It lists four bases ordered by lag, steel capacity
    #: at twenty to thirty years down to reputation at a few, so the ratio
    #: between the slowest and the fastest is about eight. ``exp(2 * 1.04) =
    #: 8.0``, which is where that value comes from; it is not a tuning knob
    #: with a free constant in it.
    #:
    #: The spread is laid out WITHIN each layer, not across them, so the
    #: treatment variable is not collinear with the financial/production split.
    #: A spread that ran across the layers would make "long lag" and "in the
    #: production layer" the same variable, and no reading could tell them
    #: apart.
    friction_spread: float = 0.0

    #: Per-period ROW multiplier on the coefficients of PRODUCTION industries
    #: as sellers, minus one. Zero is off and the matrix never moves.
    #:
    #: Rows and columns are separated because the input-output literature
    #: separates them, and because they mean different things. The RAS
    #: decomposition of a coefficient change (Dietzenbacher and Hoekstra) splits
    #: it into a row-specific part, a column-specific part and a cell residual:
    #:
    #:     A' = diag(r) A diag(s) + residual
    #:
    #: The ROW part is substitution: every buyer uses a uniformly smaller (or
    #: larger) amount of seller ``i``'s product per unit of its own output. The
    #: COLUMN part is fabrication: buyer ``j``'s intermediate input intensity
    #: changes without altering the mix it buys.
    #:
    #: TECHNICAL PROGRESS is one directed trend on the row multiplier, and it
    #: is the one this stage was opened for: most of it reduces the units of
    #: logistics and labour needed per unit of output, so the downstream
    #: sellers' rows fall. It is a trend on this parameter and not the parameter
    #: itself, which is why the field is not named after it. Other occupants of
    #: the same slot push other ways: measured substitution over 1975-1985 ran
    #: AWAY from energy, metal products and transport and TOWARD computers, food
    #: and services, so the sign is a property of the sector pair and not of
    #: technology as such.
    row_drift: float = 0.0

    #: The same row multiplier for FINANCIAL industries as sellers. Separate,
    #: and defaulting to zero rather than to ``row_drift``, because the
    #: asymmetry is the thing being read: the claim under test is that a sector
    #: tied to financial infrastructure resists the decline that hits the
    #: downstream sellers.
    row_drift_financial: float = 0.0

    #: Per-period COLUMN multiplier for PRODUCTION industries as buyers, minus
    #: one: the fabrication effect, which moves the intermediate input share of
    #: gross output directly. That share is the column sum of ``A``.
    #:
    #: The empirical sign here is NOT the same as the row story, and assuming it
    #: was would be the mistake this parameter exists to avoid. Measured over
    #: 1975-1985 the overall intermediate input coefficient rose from 0.307 to
    #: 0.353, up 15% in a decade, because outsourcing and vertical
    #: fragmentation put more of the same output through market transactions.
    #: Technical progress pushing the rows down and fragmentation pushing the
    #: columns up are two directed trends on two different multipliers, and the
    #: net movement of any real table is their sum.
    col_drift: float = 0.0

    #: The same column multiplier for FINANCIAL industries as buyers.
    col_drift_financial: float = 0.0

    #: How hard the supply side binds. Zero is off and reproduces the run
    #: without it. One means an industry that has lost half its live members can
    #: deliver half of what is asked of it, and the undelivered half is simply
    #: not spent.
    #:
    #: This is the min in the Leontief production function, which is the one
    #: assumption that makes the matrix a *technology* rather than a set of
    #: shares. Inputs are not substitutable: a buyer that cannot get steel does
    #: not buy more plastic, it does not build. Without this the industry layer
    #: only ever redirects money, never destroys the transaction, and no switch
    #: anywhere in it can reach an aggregate.
    supply_elasticity: float = 0.0

    seed: int = 0

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("count must be non-negative")
        if not 0 <= self.financial_count <= max(self.count, 0):
            raise ValueError("financial_count must lie in [0, count]")
        for name in ("p_ff", "p_pp", "p_pf", "p_fp"):
            p = getattr(self, name)
            if not 0.0 <= p <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1]")
        if not 0.0 < self.column_sum < 1.0:
            raise ValueError("column_sum must lie in (0, 1) by Hawkins-Simon")
        if self.weight_shape <= 0.0:
            raise ValueError("weight_shape must be positive")
        if not 0.0 <= self.switch_rate <= 1.0:
            raise ValueError("switch_rate must lie in [0, 1]")
        if self.switch_cost < 0.0:
            raise ValueError("switch_cost must be non-negative")
        if not 0.0 <= self.min_share:
            raise ValueError("min_share must be non-negative")
        if self.recovery_friction < 0.0:
            raise ValueError("recovery_friction must be non-negative")
        if self.friction_spread < 0.0:
            raise ValueError("friction_spread must be non-negative")
        for name in ("row_drift", "row_drift_financial",
                     "col_drift", "col_drift_financial"):
            v = getattr(self, name)
            if not -1.0 < v:
                raise ValueError(f"{name} must exceed -1; -1 would zero the matrix")
        if not 0.0 <= self.supply_elasticity <= 1.0:
            raise ValueError("supply_elasticity must lie in [0, 1]")

    @property
    def enabled(self) -> bool:
        return self.count > 0

    @property
    def production_count(self) -> int:
        return self.count - self.financial_count

    def replace(self, **changes: object) -> "IndustrySpec":
        fields = {
            "count": self.count,
            "financial_count": self.financial_count,
            "p_ff": self.p_ff,
            "p_pp": self.p_pp,
            "p_pf": self.p_pf,
            "p_fp": self.p_fp,
            "column_sum": self.column_sum,
            "weight_shape": self.weight_shape,
            "switch_rate": self.switch_rate,
            "switch_cost": self.switch_cost,
            "min_share": self.min_share,
            "recovery_friction": self.recovery_friction,
            "friction_spread": self.friction_spread,
            "row_drift": self.row_drift,
            "row_drift_financial": self.row_drift_financial,
            "col_drift": self.col_drift,
            "col_drift_financial": self.col_drift_financial,
            "supply_elasticity": self.supply_elasticity,
            "seed": self.seed,
        }
        fields.update(changes)
        return IndustrySpec(**fields)  # type: ignore[arg-type]


def industry_layers(spec: IndustrySpec) -> np.ndarray:
    """Layer of each industry. The first ``financial_count`` are financial."""
    layers = np.full(spec.count, PRODUCTION, dtype=int)
    layers[: spec.financial_count] = FINANCIAL
    return layers


def edge_probabilities(spec: IndustrySpec) -> np.ndarray:
    """``p[i, j]`` is the chance that industry ``j`` buys from industry ``i``."""
    layers = industry_layers(spec)
    seller = layers[:, None]
    buyer = layers[None, :]
    p = np.empty((spec.count, spec.count))
    p[(seller == FINANCIAL) & (buyer == FINANCIAL)] = spec.p_ff
    p[(seller == PRODUCTION) & (buyer == PRODUCTION)] = spec.p_pp
    p[(seller == PRODUCTION) & (buyer == FINANCIAL)] = spec.p_pf
    p[(seller == FINANCIAL) & (buyer == PRODUCTION)] = spec.p_fp
    return p


def build_io_matrix(spec: IndustrySpec) -> np.ndarray:
    """The Leontief coefficient matrix. ``A[i, j]``: input i per unit output j.

    Step one draws the sparsity pattern from ``edge_probabilities``. Step two
    draws weights on the surviving cells and normalises each column to
    ``column_sum``. A column that drew no edges is left at zero, which describes
    an industry with no intermediate inputs; it is a legitimate state and
    ``check_feasible`` does not object to it.
    """
    if not spec.enabled:
        return np.zeros((0, 0))
    rng = np.random.default_rng(spec.seed)
    n = spec.count
    mask = rng.random((n, n)) < edge_probabilities(spec)
    np.fill_diagonal(mask, False)
    weights = rng.gamma(spec.weight_shape, 1.0, size=(n, n))
    a = np.where(mask, weights, 0.0)
    totals = a.sum(axis=0)
    live = totals > 0.0
    a[:, live] *= spec.column_sum / totals[live]
    return a


def check_feasible(a: np.ndarray, tol: float = 1e-12) -> None:
    """Hawkins-Simon. Raises rather than warning: downstream of a bad column
    every quantity is meaningless, so there is nothing to salvage by continuing.
    """
    if a.size == 0:
        return
    totals = a.sum(axis=0)
    worst = int(np.argmax(totals))
    if totals[worst] >= 1.0 - tol:
        raise ValueError(
            f"column {worst} sums to {totals[worst]:.6f}, Hawkins-Simon needs < 1"
        )


def leontief_inverse(a: np.ndarray) -> np.ndarray:
    """``(I - A)^-1``. Feasibility is checked first, by design."""
    check_feasible(a)
    if a.size == 0:
        return np.zeros((0, 0))
    return np.linalg.inv(np.eye(a.shape[0]) - a)


def required_output(a: np.ndarray, final_demand: np.ndarray) -> np.ndarray:
    """Gross output each industry must produce to meet ``final_demand``.

    This is the sustainable level an industry is measured against. It is derived
    from the matrix rather than set by hand, and it moves with demand: when final
    demand falls the bar falls with it, so an industry can look alive right up
    until demand returns and it cannot supply. That lag is a property of the
    Leontief structure, not an extra mechanism.
    """
    return leontief_inverse(a) @ np.asarray(final_demand, dtype=float)


def zero_share(a: np.ndarray) -> float:
    """Share of off-diagonal cells that are zero. Compare with the 26% measured
    on the BEA table and the 0.00% on ICIO."""
    if a.size == 0:
        return float("nan")
    n = a.shape[0]
    off = n * (n - 1)
    if off == 0:
        return float("nan")
    return float(((a == 0.0).sum() - n) / off)


def layer_ratio(a: np.ndarray, spec: IndustrySpec) -> float:
    """Within-layer coefficient mass divided by cross-layer coefficient mass.

    The model-side counterpart of F7's Z.1 chain length, which read 1.01 in 1980
    and 2.13 now. The test this licenses is whether a parameter range *spans*
    that interval, and it is not a target to tune toward: tuning it would turn a
    structural parameter into a fitted one.
    """
    if a.size == 0:
        return float("nan")
    layers = industry_layers(spec)
    same = layers[:, None] == layers[None, :]
    np.fill_diagonal(same, False)
    within = float(a[same].sum())
    across = float(a[~same].sum())
    if across == 0.0:
        return float("inf")
    return within / across


def assign_industries(
    spec: IndustrySpec,
    financial_nodes: np.ndarray,
    production_nodes: np.ndarray,
) -> np.ndarray:
    """Agent-to-industry assignment, round robin within each layer.

    Deterministic on purpose: which node sits in which industry is then readable
    off the index without consulting a stream, and a diagnostic that looks wrong
    can be checked by hand. Industry sizes come out equal, which does not flatten
    the model's heterogeneity: degree is still drawn per node by preferential
    attachment, so two nodes in one industry are as different as before.

    Returns an array indexed by node. Nodes in neither list get ``-1`` and no
    caller should be routing them.
    """
    n = int(financial_nodes.size + production_nodes.size)
    out = np.full(n, -1, dtype=int)
    if not spec.enabled:
        return out
    fin_ids = np.arange(spec.financial_count)
    prod_ids = np.arange(spec.financial_count, spec.count)
    if fin_ids.size:
        out[financial_nodes] = fin_ids[np.arange(financial_nodes.size) % fin_ids.size]
    if prod_ids.size:
        out[production_nodes] = prod_ids[
            np.arange(production_nodes.size) % prod_ids.size
        ]
    return out


def route_weights(a: np.ndarray, industry_of: np.ndarray) -> np.ndarray:
    """``w[i, j] = A[g(j), g(i)]``: buyer ``i``'s input requirement for seller j.

    The transpose in the indexing is the whole point of this function and it is
    the one place the two conventions of the module docstring meet. ``i`` is the
    payer, so ``i``'s industry is the Leontief **column**; ``j`` is the supplier,
    so ``j``'s industry is the **row**. Getting it backwards builds an economy in
    which payment runs up the supply chain instead of down it, and every
    aggregate still looks fine, which is why it is written out here rather than
    inlined at the call site.

    A zero cell in ``A`` zeroes the route even where the payment graph has an
    edge. That is the intended behaviour: it is a hole in Volume Two's sense, a
    channel that no price can open, sitting on top of the payment graph rather
    than inside it.
    """
    return a[industry_of[None, :], industry_of[:, None]]


def friction_vector(spec: "IndustrySpec") -> np.ndarray:
    """Per-industry recovery friction, laid out within each layer.

    ``friction_spread = 0`` returns a flat vector equal to
    ``recovery_friction``, so every path that reads this reproduces the run
    that had one scalar.

    Infinite friction stays infinite everywhere: the absorbing wall is the
    limit of the spread, not a point on it, and scaling infinity by anything
    is still infinity.
    """
    k = int(spec.count)
    out = np.full(k, float(spec.recovery_friction))
    if k == 0 or spec.friction_spread <= 0.0 or not np.isfinite(spec.recovery_friction):
        return out
    for lo, hi in ((0, spec.financial_count), (spec.financial_count, k)):
        n = hi - lo
        if n <= 0:
            continue
        # z runs over [-1, 1] inside the layer; a single-industry layer sits at
        # the middle rather than at an end, so it is not silently the fastest.
        z = np.zeros(1) if n == 1 else np.linspace(-1.0, 1.0, n)
        out[lo:hi] = float(spec.recovery_friction) * np.exp(spec.friction_spread * z)
    return out


def coefficient_perturbation(spec: "IndustrySpec") -> tuple[np.ndarray, np.ndarray]:
    """The RAS pair ``(r, s)``: one row multiplier and one column multiplier.

    ``A' = diag(r) A diag(s)``. Both default to all-ones, and the caller skips
    the update when every drift is zero, so a run without perturbation reaches
    none of this.

    Rows are sellers here, matching ``build_io_matrix``'s convention that
    ``A[i, j]`` is what buyer ``j`` needs from seller ``i``.
    """
    k = int(spec.count)
    r = np.ones(k)
    c = np.ones(k)
    if k == 0:
        return r, c
    layers = industry_layers(spec)
    fin, prod = layers == FINANCIAL, layers == PRODUCTION
    r[fin] = 1.0 + spec.row_drift_financial
    r[prod] = 1.0 + spec.row_drift
    c[fin] = 1.0 + spec.col_drift_financial
    c[prod] = 1.0 + spec.col_drift
    return r, c


def perturbation_is_off(spec: "IndustrySpec") -> bool:
    """True when every drift is zero, so the caller can return before touching
    anything and reproduce the build that had no perturbation, bit for bit."""
    return (spec.row_drift == 0.0 and spec.row_drift_financial == 0.0
            and spec.col_drift == 0.0 and spec.col_drift_financial == 0.0)
