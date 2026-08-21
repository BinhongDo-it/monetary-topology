"""A4: connectivity as a covariate or as the space the covariates act in.

`docs/a4_causal_primitive.md` is the pre-registration and this file implements
it. Every switch, threshold and reading rule below is fixed there; where the
implementation had to decide something the document did not specify, the
decision is recorded in §9, §10.4 or §11 of that document rather than here.

**The measurement layer was written and run before this scoring layer existed**,
so every quantity was looked at before the line it is judged against was drawn
rather than after. §11 of the pre-registration is the record of that ordering:
it states the two repairs, the reading rule and both falsification conditions,
and it was committed before this file computed any of them.

What this stage runs, and why it is eighteen cells rather than thirty-two
------------------------------------------------------------------------

`docs/a4_causal_primitive.md` §2 describes a `2 x 2^4` factorial. §5's five
predictions are all defined on **main effects**, and §11.5 adds one based
contrast per transmitting mechanism per generating mechanism. That is `C`
crossed with `{none, I, E, K, M, E+I, E+M, K+I, K+M}`, eighteen cells. The
remaining fourteen carry interactions no registered prediction reads, so they
are available under `--full` and are not run by default.

Two repairs registered in §11 before this file computed them
------------------------------------------------------------

**§11.5, and it repairs the denominator.** §9.2 classifies `I` and `M` as
transmitting and sorting dispersion while creating none, and §11.3 measures the
`C = 0` arm to be an attractor at a Gini of `0.0071` reached in five rounds from
any opening. So against the bare null a transmitting mechanism's denominator is
a reading of the graph draw. `A(X | G)` takes both terms with a generating
mechanism on, in both arms. **Both generators are used and both are reported**,
because registering only the stronger one would be choosing a base after seeing
which base is stronger.

**§11.6, and it repairs the numerator.** The registered pair of measures is
computed a second time on the production layer alone and reported beside the
aggregate pair. The reason predates this stage's first run: §6's external
anchors are household income Ginis over a whole population, while the aggregate
measure is taken over a population containing a twenty-node financial layer
holding about `99.7%` of the stock. Checklist item 2.

Neither repair moves a parameter. §11.7 has the list of what stays fixed,
including the four `MechanismParams` values this stage has shown do not clear
A4-3's floor.

Three things this configuration fixes, each of them a decision taken elsewhere
------------------------------------------------------------------------------

**The `C = 0` arm opens at the same marginal distribution as `C = 1`.**
`NetworkSpec(uniform_opening="same_marginal")`. §9.3 records that
`uniform_access` also collapses the opening holdings to an equal split, that the
argument licensing the switch does not license that collapse, and that the
collapse pins the denominator of every transmitting mechanism near zero by
construction. §9.3a records that this was a task rather than a ruling. The field
is read only under `uniform_access`, so setting it here is a bitwise no-op in the
`C = 1` arm, which `tests/test_a4_uniform_opening.py` asserts rather than claims.

**`A(X)` is reported per seed as well as pooled, and both arms' final Gini is
reported beside it.** §4 averages the two differences over seeds before taking
the ratio. §10.4 adds two obligations that come from measurement rather than
from design. A ratio of small differences on five seeds can straddle one without
anyone seeing it, so A3c's rule is imported: no point value is quoted for a
competitor whose sign moves across seeds. And the Gini is bounded with the
control cell already at `0.935`, so with both arms now opening at the same
distribution the arm nearer the ceiling is `C = 1` and the compression falls on
the numerator. `A(X)` is biased **downward**, a pass at `A(X) > 1` is
conservative, and a failure cannot be read without the headroom beside it.

**Injection is a separate axis from the registered point, and it moves one thing
at a time.** `PROJECT_PLAN` §16.2 makes `A(X)` a function of the injection
amount. `NetworkConfig.authority` already defaults to `rule="endogenous"`, so
the registered point is not "no injection", and sweeping an amount would mean
changing the rule and the amount together, which is `MEASUREMENT.md` rule 4. So
the sweep runs at `rule="fixed"` with `fixed_amount` starting at zero, the
`endogenous` point is reported as its own row rather than folded into the curve,
and `--target` selects which of `INJECTION_TARGETS` the credit goes to. The
default run is the registered point and nothing else.

What the injection axis is now expected to show
-----------------------------------------------

`experiments/a4a_domain_probe.py --probe injection` measured the `top_node` arm
before this file existed. Over three hundred rounds the endogenous rule issues
about `3213` against an opening stock of `100`, and the production layer's whole
holdings history is `array_equal` to the same run with issuance off, at every
seed, with derived demand on and off. So on that arm the injection amount is
expected to move `A(X)` by nothing at all, and §16.2's registered deliverable,
the amount at which `A(X)` crosses one, is expected not to exist. This chunk
runs one amount at a time through `--rule`, `--amount` and `--target`; the swept
curve is chunk 2's, and the prediction is written down here before it runs.

Cost
----

Ninety runs at three hundred rounds for the registered point, two hundred and
seventy more for A4-5's three alternative orderings, and five for §2's bitwise
check. About ninety seconds.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.mechanisms import (  # noqa: E402
    A4Config,
    MechanismParams,
    Switches,
    gini,
    run_a4,
)
from monetary_topology.network import (  # noqa: E402
    INJECTION_TARGETS,
    OPENING_HOLDINGS,
    Network,
    NetworkConfig,
    NetworkSpec,
)

RESULTS = ROOT / "results"

REGISTERED_SEEDS = 5
REGISTERED_ROUNDS = 300

#: The four competing explanations, in the order §5's table lists them. Each
#: name is the field on :class:`Switches` that turns it on, so the mapping from
#: a criterion's prose to a cell is a lookup and not a translation.
COMPETITORS: tuple[str, ...] = (
    "inheritance",
    "education",
    "capital",
    "mating",
)

#: Short labels for the printed tables, matching `Switches.label`'s letters.
LETTER = {
    "inheritance": "I",
    "education": "E",
    "capital": "K",
    "mating": "M",
}

#: §9.2's classification, and it was written before any of this stage's
#: measurements existed. A **generating** mechanism draws its own dispersion
#: from a fixed distribution that never consults the graph. A **transmitting**
#: mechanism moves and sorts dispersion that is already there and creates none.
#:
#: §11.5 turns the classification into arithmetic: a transmitting mechanism's
#: `A(X)` is taken with a generating mechanism on in both terms and both arms,
#: because §11.3 measures the `C = 0` arm to be an attractor at a Gini of
#: `0.0071` reached in five rounds from any opening, so a transmitting
#: mechanism's denominator against the bare null is a reading of the graph draw.
GENERATING: tuple[str, ...] = ("education", "capital")
TRANSMITTING: tuple[str, ...] = ("inheritance", "mating")


def main_effect_cells() -> dict[str, Switches]:
    """`C` crossed with the singles and with §11.5's based pairs. Eighteen.

    Nine settings per arm: the null, each competitor alone, and each
    transmitting mechanism on top of each generating one. Insertion order is
    fixed by module constants rather than by a set or by dataclass field order,
    which the project's determinism rule requires.

    **Both generators are used as bases and both are reported.** Registering
    only the stronger one would be choosing a base after seeing which base is
    stronger, which is the move §5.1's demotions, §10.3's second refusal and
    `PROJECT_PLAN` §13.4 all exist to prevent. The two disagreeing is a result.
    """
    cells: dict[str, Switches] = {}
    for connectivity in (True, False):
        c = 1 if connectivity else 0
        cells[f"C{c}_none"] = Switches(connectivity=connectivity)
        for name in COMPETITORS:
            cells[f"C{c}_{LETTER[name]}"] = Switches(
                connectivity=connectivity, **{name: True}
            )
        for g in GENERATING:
            for x in TRANSMITTING:
                cells[f"C{c}_{LETTER[g]}+{LETTER[x]}"] = Switches(
                    connectivity=connectivity, **{g: True, x: True}
                )
    return cells


def base_cell(c: int, base: str | None) -> str:
    """The cell a competitor's effect is differenced against."""
    return f"C{c}_none" if base is None else f"C{c}_{LETTER[base]}"


def treated_cell(c: int, base: str | None, name: str) -> str:
    """The cell with the competitor on, over the same base."""
    if base is None:
        return f"C{c}_{LETTER[name]}"
    return f"C{c}_{LETTER[base]}+{LETTER[name]}"


#: One pairing per competitor per base, in the order the tables print them.
#: Generating mechanisms take §4's original form against the bare null;
#: transmitting mechanisms take §11.5's form once per generator.
def contrasts() -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = [(g, None) for g in GENERATING]
    out += [(x, None) for x in TRANSMITTING]
    for x in TRANSMITTING:
        for g in GENERATING:
            out.append((x, g))
    return out


def full_factorial_cells() -> dict[str, Switches]:
    """All thirty-two. Available, unread by any registered prediction."""
    cells: dict[str, Switches] = {}
    for connectivity in (True, False):
        for mask in range(16):
            flags = {
                name: bool(mask & (1 << i))
                for i, name in enumerate(COMPETITORS)
            }
            sw = Switches(connectivity=connectivity, **flags)
            cells[f"C{1 if connectivity else 0}_{sw.label[1:]}"] = sw
    return cells


def base_config(
    *,
    rule: str,
    amount: float,
    target: str,
    rounds: int,
    opening: str = "same_marginal",
) -> NetworkConfig:
    """The registered A4 network configuration.

    `uniform_opening` is set on the spec rather than passed at the `C = 0` arm,
    because `A4Config.resolved_network` rebuilds the spec with
    `dataclasses.replace` and would carry whatever it is handed. Setting it once
    here means the two arms cannot drift apart through a call site that forgot
    it, and the field reaches no code under `uniform_access = False`.

    `opening` exists so that §9.3's registered check is a flag rather than an
    edit. That section requires the `C = 0` arm be re-run at the same opening
    marginal as `C = 1` and `A(X)` recomputed **before A4 is run at all**, with
    A4-4's threshold reset if `A(X)` falls materially. `flat` is the arm every
    pre-2026-08-13 number was produced under and is kept reachable for exactly
    that comparison.
    """
    return NetworkConfig(
        spec=NetworkSpec(uniform_opening=opening),
        authority=MonetaryAuthority(rule=rule, fixed_amount=amount),
        injection_target=target,
        rounds=rounds,
    )


def run_cell(
    switches: Switches,
    *,
    base: NetworkConfig,
    seeds: int,
    channel_order: str,
    event_order: str,
    pooling: str,
) -> list:
    """One cell at every seed. The graph seed and the run seed move together.

    Copied from `cell_configs`'s reason rather than calling it: holding the
    graph fixed across replications would make the reported spread a statement
    about one graph.
    """
    out = []
    for s in range(seeds):
        net = replace(base, seed=s, spec=replace(base.spec, seed=s))
        out.append(
            run_a4(
                A4Config(
                    switches=switches,
                    params=MechanismParams(),
                    network=net,
                    channel_order=channel_order,
                    event_order=event_order,
                    pooling=pooling,
                )
            )
        )
    return out


def amplification(
    rows: dict[str, dict], key: str, name: str, base: str | None
) -> dict[str, object]:
    """`A(X)` or `A(X | G)` for one competitor on one measure, per seed and pooled.

    Two numbers and they answer different questions. The pooled ratio is §4's
    registered form, which averages the two differences over seeds before
    dividing. The per-seed vector is what says whether that ratio is a summary
    or an artefact, and its **sign agreement** is the gate §10.4 imports from
    A3c: a competitor whose per-seed ratios do not share a sign gets no point
    value quoted, whatever the pooled number comes to.

    `numerator` and `denominator` are carried out rather than divided away
    because `A4-3`'s strawman floor is a statement about the denominator alone,
    and a reader checking that should not have to reconstruct it.

    `base` is `None` for a generating mechanism, which keeps §4's form, and a
    generator's name for a transmitting one, which takes §11.5's.
    """
    num_by_seed = (
        rows[treated_cell(1, base, name)][key] - rows[base_cell(1, base)][key]
    )
    den_by_seed = (
        rows[treated_cell(0, base, name)][key] - rows[base_cell(0, base)][key]
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        by_seed = np.where(den_by_seed != 0.0, num_by_seed / den_by_seed, np.nan)
    finite = by_seed[np.isfinite(by_seed)]
    signs = {float(np.sign(v)) for v in finite if v != 0.0}

    num, den = float(num_by_seed.mean()), float(den_by_seed.mean())
    return {
        "competitor": name,
        "base": "null" if base is None else LETTER[base],
        "numerator": num,
        "denominator": den,
        "pooled": float(num / den) if den != 0.0 else float("nan"),
        "by_seed": by_seed,
        "quotable": len(signs) <= 1 and finite.size == by_seed.size,
    }


def reproduction_check(seeds: int, rounds: int) -> list[tuple[int, bool]]:
    """§2's strict generalisation, checked rather than asserted in prose.

    With `C` on and every competitor off, `A4Model` must reproduce the plain
    `Network` bitwise. This runs at the **registered** authority rather than at
    the sweep's, because that is the configuration the existing A0 and A2
    numbers were produced under, and a generalisation that reproduces its own
    special case only at a setting nobody used has reproduced nothing.
    """
    rows = []
    for s in range(seeds):
        net = NetworkConfig(
            spec=NetworkSpec(seed=s, uniform_opening="same_marginal"),
            seed=s,
            rounds=rounds,
        )
        a4 = run_a4(A4Config(switches=Switches(), network=net))
        plain = Network(net).run()
        rows.append(
            (
                s,
                np.array_equal(
                    np.asarray(a4.history.holdings),
                    np.asarray(plain.holdings),
                ),
            )
        )
    return rows


def measure(
    cells: dict[str, Switches],
    *,
    base: NetworkConfig,
    seeds: int,
    channel_order: str,
    event_order: str,
    pooling: str,
) -> dict[str, dict]:
    """Every cell at every seed, keyed by cell name in the dict's fixed order."""
    out: dict[str, dict] = {}
    for name, switches in cells.items():
        results = run_cell(
            switches,
            base=base,
            seeds=seeds,
            channel_order=channel_order,
            event_order=event_order,
            pooling=pooling,
        )
        finals = [
            np.asarray(r.history.holdings, dtype=float)[-1] for r in results
        ]
        k = base.spec.layer1_size
        out[name] = {
            "gini": np.array([r.gini_final for r in results], dtype=float),
            "holders": np.array(
                [r.effective_holders_final for r in results], dtype=float
            ),
            # §11.6. The same two measures on the production layer alone. The
            # aggregate pair is taken over a population containing a twenty-node
            # financial layer holding about 99.7% of the stock, while §6's
            # external anchors are household income Ginis over a whole
            # population. Both pairs are reported; neither replaces the other.
            "gini_prod": np.array(
                [gini(f[k:]) for f in finals], dtype=float
            ),
            "holders_prod": np.array(
                [_effective_holders(f[k:]) for f in finals], dtype=float
            ),
            "cross_layer": np.array(
                [r.cross_layer_rate for r in results], dtype=float
            ),
            "cross_layer_baseline": np.array(
                [r.cross_layer_baseline for r in results], dtype=float
            ),
            "events": np.array(
                [r.generational_events for r in results], dtype=float
            ),
            # The final holdings vector per seed, as shares. Kept so that
            # `resolution` can ask whether the vector moved at all, which is a
            # different question from whether either scalar summary of it moved,
            # and the two have to be separable before a criterion built on a
            # summary can be read.
            "shares": np.array([_shares(f) for f in finals], dtype=float),
        }
    return out


def _shares(final: np.ndarray) -> np.ndarray:
    total = float(final.sum())
    return final / total if total > 0.0 else np.zeros_like(final)


def _effective_holders(final: np.ndarray) -> float:
    """`1/HHI` over whatever slice it is handed. Same formula as `run_a4`'s."""
    total = float(final.sum())
    if total <= 0.0:
        return 0.0
    return float(1.0 / np.square(final / total).sum())


#: The measures a table is read on. The first two are §3's registered pair. The
#: second two are §11.6's production-layer pair, reported beside them and not in
#: place of them.
SCORED_MEASURES: tuple[tuple[str, str], ...] = (
    ("gini", "Gini agg"),
    ("holders", "1/HHI agg"),
    ("gini_prod", "Gini prod"),
    ("holders_prod", "1/HHI prod"),
)


def resolution(rows: dict[str, dict]) -> list[dict]:
    """Does each registered measure have anything to see, in each arm.

    **The reading rule, stated before the table is looked at.** A measure has
    *resolution* for a treatment in an arm when the paired effect is sign-stable
    across seeds **and** large against that same measure's own seed-to-seed
    spread in the control cell of that arm. Where it does not, a criterion built
    on that measure in that arm is **unreadable**: not a pass and not a failure.

    This is checklist item 7 turned on the instrument rather than on the
    carrier. Within a seed the model is deterministic, so a paired difference
    has no sampling noise; all the variation is across graph draws. The control
    cell's spread across seeds is therefore exactly an arm whose value under no
    treatment is the whole of what the measure does when nothing is being done
    to it, and an effect inside it is a reading of the draw.

    **`tv` is a diagnostic and is fenced off as one here, before it is
    computed.** It is the total-variation distance between the normalised final
    holdings vectors with the competitor on and off, paired by seed, and it
    reads as the share of the stock sitting on different nodes. It exists to
    separate two situations no scalar summary can tell apart: a treatment that
    moves nothing, and a treatment that moves a great deal in a way neither the
    Gini nor `1/HHI` is shaped to register. Promoting it to a criterion after
    seeing which competitors it favours is the move §13.4 and §10.3 refuse, so
    it is fenced in advance rather than after.
    """
    out: list[dict] = []
    for c in (1, 0):
        for name, base in contrasts():
            lo, hi = base_cell(c, base), treated_cell(c, base, name)
            row: dict = {
                "arm": f"C={c}",
                "competitor": name,
                "base": "null" if base is None else LETTER[base],
                "tv": float(
                    (
                        0.5
                        * np.abs(rows[hi]["shares"] - rows[lo]["shares"]).sum(
                            axis=1
                        )
                    ).mean()
                ),
            }
            for key, label in SCORED_MEASURES:
                control = rows[lo][key]
                floor = float(control.std())
                effect = rows[hi][key] - control
                signs = {float(np.sign(v)) for v in effect if v != 0.0}
                row[key] = {
                    "label": label,
                    "control": float(control.mean()),
                    "effect": float(effect.mean()),
                    "floor": floor,
                    "ratio": (
                        abs(float(effect.mean())) / floor
                        if floor > 0.0
                        else float("inf")
                    ),
                    "sign_stable": len(signs) <= 1,
                }
            out.append(row)
    return out


def print_resolution(table: list[dict]) -> None:
    print(
        "\n  Instrument resolution, sect. 11.2's rule. The base cell's spread"
        " across seeds is\n  the floor; an effect inside it reads the graph draw"
        " rather than the treatment.\n  Where a measure has no resolution, a"
        " criterion resting on it is unreadable:\n  not a pass and not a failure."
        "  `*` marks a sign that is stable across seeds."
    )
    print(
        "\n  arm   base  competitor      Gini agg   1/HHI agg"
        "  Gini prod  1/HHI prod    stock"
    )
    print(
        "                                eff/sd      eff/sd"
        "     eff/sd      eff/sd      moved"
    )
    for r in table:
        cols = "".join(
            f"  {r[k]['ratio']:9.2f}{'*' if r[k]['sign_stable'] else ' '}"
            for k, _ in SCORED_MEASURES
        )
        print(
            f"  {r['arm']:4s}  {r['base']:4s}  {r['competitor']:12s}"
            + cols
            + f"  {r['tv']:8.2%}"
        )
    print(
        "\n  `stock moved` is the total-variation distance between the two final"
        " holdings\n  vectors, paired by seed: the share of the stock ending on"
        " different nodes. It\n  is a diagnostic, fenced off as one before it was"
        " computed (sect. 11.4)."
    )


def print_levels(table: list[dict]) -> None:
    """The same contrasts in levels, so a reader can check the ratios."""
    print(
        "\n  The same rows in levels. `control` is the base cell's mean,"
        " `effect` the paired\n  difference, `floor` the base cell's spread"
        " across seeds."
    )
    for key, label in SCORED_MEASURES:
        print(f"\n  {label}")
        print(
            "    arm   base  competitor        control       effect"
            "       floor"
        )
        for r in table:
            m = r[key]
            print(
                f"    {r['arm']:4s}  {r['base']:4s}  {r['competitor']:12s}"
                f"  {m['control']:12.5f}  {m['effect']:+11.5f}"
                f"  {m['floor']:10.5f}"
            )


def print_cells(rows: dict[str, dict]) -> None:
    print(
        "\n  cell        Gini agg   1/HHI agg  Gini prod  1/HHI prod"
        "  cross-layer  baseline"
    )
    for name, r in rows.items():
        cl = r["cross_layer"]
        cl_txt = "     --  " if np.isnan(cl).all() else f"{np.nanmean(cl):8.4f}"
        base = r["cross_layer_baseline"]
        base_txt = (
            "    --  " if np.isnan(base).all() else f"{np.nanmean(base):7.4f}"
        )
        print(
            f"  {name:10s}  {r['gini'].mean():8.5f}  {r['holders'].mean():10.2f}"
            f"  {r['gini_prod'].mean():9.5f}"
            f"  {r['holders_prod'].mean():10.2f}"
            f"  {cl_txt}  {base_txt}"
        )


def print_amplification(rows: dict[str, dict], seeds: int) -> None:
    """`A(X)` on every measure, for every registered contrast."""
    for key, label in SCORED_MEASURES:
        print(f"\n  A(X) on {label}")
        print(
            "    base  competitor      num (C=1)    den (C=0)      pooled"
            "  quote   by seed"
        )
        for name, base in contrasts():
            a = amplification(rows, key, name, base)
            per = " ".join(
                "    nan" if not np.isfinite(v) else f"{v:7.2f}"
                for v in a["by_seed"]
            )
            print(
                f"    {a['base']:4s}  {name:12s}  {a['numerator']:+10.5f}"
                f"  {a['denominator']:+11.5f}  {a['pooled']:10.3f}"
                f"  {'yes' if a['quotable'] else 'no':>5s}   {per}"
            )
    print(
        "\n  `quote` is A3c's rule through sect. 10.4: a point value is quoted"
        " only where the\n  per-seed ratios share a sign. Levels of both arms,"
        " which sect. 10.4 requires\n  beside every ratio, because A(X) is"
        " biased downward by the ceiling:"
    )
    for arm in ("C1_none", "C0_none"):
        r = rows[arm]
        print(
            f"     {arm:8s} Gini agg {r['gini'].mean():.5f}"
            f"  (headroom {1.0 - r['gini'].mean():.5f})"
            f"   Gini prod {r['gini_prod'].mean():.5f}"
            f"  (headroom {1.0 - r['gini_prod'].mean():.5f})"
        )
    print(f"\n  seeds = {seeds}")


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

#: An effect is **readable** when its sign is stable across seeds and its size
#: is at least one control-cell standard deviation. This is the weakest bar the
#: floor admits, deliberately: the floor is the whole of what the measure does
#: when nothing is being done to it, so an effect below it is a reading of the
#: graph draw and one above it is merely not that. A cell that fails this bar is
#: failing generously.
READABLE_SD = 1.0


@dataclass
class Criterion:
    """One registered prediction. Same four states the rest of the repository
    uses, and the same field names, so nothing downstream needs a case."""

    name: str
    passed: bool
    detail: str
    void: bool = False
    diagnostic: bool = False

    def line(self) -> str:
        if self.diagnostic:
            mark = "diag"
        elif self.void:
            mark = "VOID"
        else:
            mark = "pass" if self.passed else "FAIL"
        return f"  {mark}  {self.name}\n        {self.detail}"


def stable_verdicts(rows: dict[str, dict]) -> tuple[bool, bool, bool]:
    """A4-1, A4-2 and A4-6's verdicts, computed from one run's cells.

    Pulled out so that A4-5's claim about them is **checked** rather than
    written into a detail string. An earlier draft of this file asserted in
    prose that the three do not move across orderings without evaluating them
    on the alternative runs, which is the shape `MEASUREMENT.md` §7 collects.
    """
    g = {k: v["gini"] for k, v in rows.items()}
    a1 = float(g["C0_none"].mean()) < 0.02
    diff = g["C1_none"] - g["C0_none"]
    a2 = float(diff.mean()) >= 0.05 and bool((diff > 0.0).all())
    a6 = bool((rows["C1_M"]["cross_layer"] < rows["C0_M"]["cross_layer"]).all())
    return a1, a2, a6


def _sd_units(effect: float, control: np.ndarray) -> str:
    """Effect in floor units, or `undefined` where the floor is exactly zero.

    A control cell with no spread across seeds gives no floor to measure
    against, and printing an infinity there would read as an enormous effect
    when it is an absent denominator.
    """
    sd = float(control.std())
    return "undefined" if sd == 0.0 else f"{effect / sd:.1f}"


def _readable(entry: dict) -> bool:
    return bool(entry["sign_stable"]) and entry["ratio"] >= READABLE_SD


def readable_set(table: list[dict]) -> set[tuple[str, str, str, str]]:
    """Which cells clear the floor. The object A4-5 asks about stability of."""
    return {
        (r["arm"], r["base"], r["competitor"], key)
        for r in table
        for key, _ in SCORED_MEASURES
        if _readable(r[key])
    }


def evaluate(
    rows: dict[str, dict],
    table: list[dict],
    order_runs: dict[str, tuple[dict, list[dict]]],
) -> list[Criterion]:
    """A4-1 to A4-6, scored on §3's registered measure.

    **The aggregate Gini is what scores.** §11.6 adds the production-layer pair
    beside it and explicitly does not replace it, so every threshold below is
    read on `gini` and the production-layer figure travels in the detail. A
    stage that scored on the measure added after the registered one failed would
    be choosing its instrument by its answer.
    """
    g = {k: v["gini"] for k, v in rows.items()}
    gp = {k: v["gini_prod"] for k, v in rows.items()}
    out: list[Criterion] = []

    # -- A4-1 -----------------------------------------------------------
    null0 = float(g["C0_none"].mean())
    out.append(
        Criterion(
            "A4-1 null calibration: identical agents on a complete graph do not"
            " stratify",
            null0 < 0.02,
            f"C=0 all competitors off, Gini {null0:.5f} against a ceiling of"
            f" 0.02. Production layer {float(gp['C0_none'].mean()):.5f}."
            f" Spread across seeds {float(g['C0_none'].std()):.5f}.",
        )
    )

    # -- A4-2 -----------------------------------------------------------
    gap = float(g["C1_none"].mean()) - null0
    per_seed = g["C1_none"] - g["C0_none"]
    out.append(
        Criterion(
            "A4-2 connectivity alone is sufficient",
            gap >= 0.05 and bool((per_seed > 0.0).all()),
            f"Gini {float(g['C1_none'].mean()):.5f} against {null0:.5f}, gap"
            f" {gap:+.5f} against a floor of 0.05, and the sign holds at"
            f" {int((per_seed > 0.0).sum())} of {per_seed.size} seeds."
            f" Production layer {float(gp['C1_none'].mean()):.5f} against"
            f" {float(gp['C0_none'].mean()):.5f}.",
        )
    )

    # -- A4-3 -----------------------------------------------------------
    floors: dict[str, float] = {}
    bits = []
    for name in COMPETITORS:
        d = float((g[f"C0_{LETTER[name]}"] - g["C0_none"]).mean())
        floors[name] = d
        bits.append(f"{LETTER[name]} {d:+.5f}")
    strawmen = [n for n, d in floors.items() if d < 0.02]
    out.append(
        Criterion(
            "A4-3 no competitor is a strawman",
            not strawmen,
            f"Each competitor alone with C off, Gini rise over the null against"
            f" a floor of 0.02: {', '.join(bits)}. Below the floor:"
            f" {', '.join(LETTER[n] for n in strawmen) or 'none'}."
            f" The floor is in absolute Gini units and the C=0 control sits at"
            f" {null0:.5f}, so it asks each competitor for"
            f" {0.02 / null0:.1f} times the control's whole value; the"
            f" threshold is registered and is not moved on that account."
            f" Education's rise is {_sd_units(floors['education'], g['C0_none'])}"
            f" control-cell sd and still below it.",
        )
    )

    # -- A4-4 -----------------------------------------------------------
    live_cells = sorted(
        f"{arm}/{base}/{LETTER[comp]}"
        for arm, base, comp, key in readable_set(table)
        if key == "gini"
    )
    quotable = []
    for name, base in contrasts():
        a = amplification(rows, "gini", name, base)
        if a["quotable"]:
            quotable.append(
                f"{LETTER[name]}|{a['base']} = {a['pooled']:.1f}"
                f" (denominator {a['denominator']:+.5f})"
            )
    out.append(
        Criterion(
            "A4-4 connectivity is upstream",
            False,
            f"**Void on two independent grounds and not evaluated.** §7's"
            f" table: A4-3 fails for {len(strawmen)} of four competitors, and a"
            f" failed strawman floor makes that competitor's comparison void"
            f" rather than favourable. §11.8's rule: A(X) is a ratio across the"
            f" two arms and no competitor is readable in both, so one of its"
            f" two terms is a reading of the graph draw in every case. Readable"
            f" Gini cells: {', '.join(live_cells) or 'none'}. Ratios whose"
            f" per-seed sign happens to agree: {'; '.join(quotable) or 'none'},"
            f" and each rests on a denominator inside two control-cell sd, so"
            f" the agreement is five draws landing the same way rather than a"
            f" quantity.",
            void=True,
        )
    )

    # -- A4-5 -----------------------------------------------------------
    base_set = readable_set(table)
    here = stable_verdicts(rows)
    moved, flipped = [], []
    for label, (alt_rows, other) in sorted(order_runs.items()):
        other_set = readable_set(other)
        if other_set != base_set:
            moved.append(f"{label} ({len(base_set ^ other_set)} cells differ)")
        there = stable_verdicts(alt_rows)
        if there != here:
            names = [
                n
                # `strict=True` rather than to satisfy the linter: the three
                # tuples come from `stable_verdicts`, and if one of them ever
                # grows a fourth verdict while this list does not, the silent
                # behaviour is to drop it from the comparison.
                for n, a, b in zip(
                    ("A4-1", "A4-2", "A4-6"), here, there, strict=True
                )
                if a != b
            ]
            flipped.append(f"{label} ({', '.join(names)})")
    out.append(
        Criterion(
            "A4-5 the update order does not decide it",
            False,
            f"**Void: A4-4 has no result for an ordering to preserve or"
            f" overturn.** What was run in its place, on all four combinations"
            f" of channel order and event order, and is reported: the set of"
            f" cells clearing §11.2's floor, and the three verdicts that do not"
            f" pass through A(X). Registered set has {len(base_set)} cells;"
            f" orderings whose set differs: {', '.join(moved) or 'none'}."
            f" A4-1, A4-2 and A4-6 evaluated on every alternative run;"
            f" orderings where any of the three flips:"
            f" {', '.join(flipped) or 'none'}.",
            void=True,
        )
    )

    # -- A4-6 -----------------------------------------------------------
    on1, on0 = rows["C1_M"]["cross_layer"], rows["C0_M"]["cross_layer"]
    ref = float(rows["C1_M"]["cross_layer_baseline"].mean())
    lower = on1 < on0
    out.append(
        Criterion(
            "A4-6 caste is derived from holdings, not read off the layer",
            bool(lower.all()),
            f"Matching reads holdings and never the layer label. Cross-layer"
            f" pairing rate with M on: C=1 {float(on1.mean()):.4f} against C=0"
            f" {float(on0.mean()):.4f}, uniform-random reference {ref:.4f}, and"
            f" C=1 is lower at {int(lower.sum())} of {lower.size} seeds."
            f" On §11.5's based cells the same direction holds and wider:"
            f" E+M {float(rows['C1_E+M']['cross_layer'].mean()):.4f} against"
            f" {float(rows['C0_E+M']['cross_layer'].mean()):.4f}, K+M"
            f" {float(rows['C1_K+M']['cross_layer'].mean()):.4f} against"
            f" {float(rows['C0_K+M']['cross_layer'].mean()):.4f}."
            f" This criterion reads a rate directly and takes no ratio across"
            f" arms, which is why §11's collapse does not reach it.",
        )
    )
    return out


def _round(value: float, places: int = 6) -> float:
    """Floats into the record through `round`, never through `repr`.

    The project's determinism rule, and the third instance of it: a float
    written at full precision differs in its last digits between platforms and
    the CI step that diffs `RESULTS.md` fails on content that is identical.
    """
    return float(f"{value:.{places}f}")


def record(
    rows: dict[str, dict],
    table: list[dict],
    criteria: list[Criterion],
    args,
) -> dict:
    return {
        "stage": "A4",
        "seeds": args.seeds,
        "rounds": args.rounds,
        "parameters": {
            "issuance_rule": args.rule,
            "injection_target": args.target,
            "uniform_opening": args.opening,
            "pooling": args.pooling,
            "channel_order": args.channel_order,
            "event_order": args.event_order,
            "readable_sd": READABLE_SD,
        },
        "cells": {
            name: {
                key: _round(float(r[key].mean()))
                for key, _ in SCORED_MEASURES
            }
            | {"cross_layer": _round(float(np.nanmean(r["cross_layer"])))
               if not np.isnan(r["cross_layer"]).all() else None}
            for name, r in rows.items()
        },
        "resolution": [
            {
                "arm": r["arm"],
                "base": r["base"],
                "competitor": r["competitor"],
                "stock_moved": _round(r["tv"]),
            }
            | {
                key: {
                    "effect": _round(r[key]["effect"]),
                    "floor": _round(r[key]["floor"]),
                    "sd": _round(r[key]["ratio"], 2),
                    "sign_stable": bool(r[key]["sign_stable"]),
                }
                for key, _ in SCORED_MEASURES
            }
            for r in table
        ],
        "criteria": [
            {
                "name": c.name,
                "passed": bool(c.passed),
                "void": bool(c.void),
                "diagnostic": bool(c.diagnostic),
                "detail": c.detail,
            }
            for c in criteria
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    ap.add_argument(
        "--full",
        action="store_true",
        help="all thirty-two cells; no registered prediction reads them",
    )
    ap.add_argument(
        "--rule",
        default="endogenous",
        choices=("endogenous", "fixed", "none"),
        help="issuance rule; the registered point is endogenous",
    )
    ap.add_argument("--amount", type=float, default=10.0)
    ap.add_argument("--target", default="top_node", choices=INJECTION_TARGETS)
    ap.add_argument(
        "--opening",
        default="same_marginal",
        choices=OPENING_HOLDINGS,
        help="section 9.3's check: `flat` is the pre-repair C=0 arm",
    )
    ap.add_argument("--channel-order", default="capital_first")
    ap.add_argument("--event-order", default="inherit_first")
    ap.add_argument("--pooling", default="round")
    ap.add_argument(
        "--levels",
        action="store_true",
        help="print the resolution rows in levels as well as in floor units",
    )
    ap.add_argument(
        "--json",
        nargs="?",
        const="a4_causal_primitive.json",
        default=None,
        help="write the record; pass a name to write beside the registered one",
    )
    ap.add_argument(
        "--no-reproduction",
        action="store_true",
        help="skip section 2's bitwise check",
    )
    args = ap.parse_args()

    cells = full_factorial_cells() if args.full else main_effect_cells()
    base = base_config(
        rule=args.rule,
        amount=args.amount,
        target=args.target,
        rounds=args.rounds,
        opening=args.opening,
    )

    print(
        f"\nA4 measurement  seeds={args.seeds}  rounds={args.rounds}"
        f"  rule={args.rule}  amount={args.amount:g}"
        f"  target={args.target}  opening={args.opening}"
        f"\n                channel_order={args.channel_order}"
        f"  event_order={args.event_order}  pooling={args.pooling}"
        f"  cells={len(cells)}"
    )

    if not args.no_reproduction:
        rows = reproduction_check(args.seeds, args.rounds)
        bad = [s for s, ok in rows if not ok]
        print(
            "\n  section 2 strict generalisation, C on and all competitors off,"
            " A4Model against Network:"
        )
        print(
            f"    bitwise identical at {sum(ok for _, ok in rows)}"
            f" of {len(rows)} seeds"
            + ("" if not bad else f"   FAILING SEEDS: {bad}")
        )

    rows = measure(
        cells,
        base=base,
        seeds=args.seeds,
        channel_order=args.channel_order,
        event_order=args.event_order,
        pooling=args.pooling,
    )
    print_cells(rows)
    if args.full:
        return 0

    table = resolution(rows)
    print_resolution(table)
    if args.levels:
        print_levels(table)
    print_amplification(rows, args.seeds)

    # A4-5's alternatives. Three more eighteen-cell passes, which is about a
    # minute; run by default because a criterion that is only evaluated behind
    # a flag is not evaluated.
    order_runs: dict[str, tuple[dict, list[dict]]] = {}
    for channel, event in (
        ("pooling_first", args.event_order),
        (args.channel_order, "match_first"),
        ("pooling_first", "match_first"),
    ):
        label = f"{channel}/{event}"
        alt = measure(
            cells,
            base=base,
            seeds=args.seeds,
            channel_order=channel,
            event_order=event,
            pooling=args.pooling,
        )
        order_runs[label] = (alt, resolution(alt))

    criteria = evaluate(rows, table, order_runs)
    live = [c for c in criteria if not (c.void or c.diagnostic)]
    n_pass = sum(c.passed for c in live)
    print("\n  Criteria\n")
    for c in criteria:
        print(c.line())
    n_void = sum(c.void for c in criteria)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, {n_void} void")

    if args.json:
        RESULTS.mkdir(exist_ok=True)
        out = RESULTS / args.json
        out.write_text(
            json.dumps(record(rows, table, criteria, args), indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
