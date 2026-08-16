"""The income path A1 and A1b run on, taken from A0 rather than invented.

``docs/a1_prereg.md`` §2 and `cascade.py`'s own list of what it refuses to
invent: **the income path is A0's retention mechanism**. A cascade stage that
wrote its own shock would answer a different question from the one A0 already
measured, and the answer would be about the shock.

What is taken
---------------
``History.terminating[t, s]`` is the claims **landing** on stratum ``s`` in round
``t``. That is the quantity the manuscript's 卷一·十八 is about: what reaches a
household, against what it owes. The multiplier this module hands the cascade is

    multiplier[t][s] = terminating[t, s] / terminating[0, s]

so period zero is exactly one for every stratum by construction, and the
cascade's baseline is A0's opening round rather than a level this file chose.

Three identifications, each registered rather than assumed
------------------------------------------------------------
**The population is the same population.** A0's DFA-calibrated preset uses
counts ``(50, 40, 9, 1)`` and net worth shares ``(0.025, 0.296, 0.363, 0.316)``,
which are the cascade's, so the mapping is by construction and not by
approximation. The source-faithful preset uses ``(49, 40, 10, 1)`` and would
need one, so it is refused here rather than silently rescaled.

**One A0 round is one model month.** Nothing publishes A0's round length; it is
a circulation period. The cascade's period is a month because the delinquency
target is defined in days. The identification is therefore a declaration, and
what it sets is how fast the path's transition plays out against the cost rule's
grace periods. ``months_per_round`` holds each round for longer, which is the
robustness arm: a verdict that moves when the same path is stretched is a
verdict about the identification.

**The seed is A0's.** A1b draws nothing and has no seed of its own, so the only
randomness reaching it is A0's propensity draw. A run reports which seed it used
and a sweep varies it, exactly as A0's own stages do.

What this module will not do
------------------------------
It will not return a path whose opening round is not one, and it will not return
a flat path. A flat path is the zero-shock arm, and that arm is built by the
caller as an explicit vector of ones rather than by asking this file for a shock
and getting none: a retention mechanism that turned out to move nothing would
otherwise be indistinguishable from the control.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .calibration import DFA_COUNTS, DFA_NET_WORTH_SHARES, dfa_calibrated
from .economy import run


class PathProblem(ValueError):
    """The path is not the shape a cascade stage can run on."""


#: How far the opening multiplier may sit from one before the normalisation is
#: judged not to have happened. It is a division of a number by itself, so this
#: is floating point and nothing else.
OPENING_TOLERANCE = 1e-12

#: A path in which no stratum moves by more than this is the control arm wearing
#: a shock's name, and it is refused. A0's own measured path takes the bottom
#: half to about 0.58 of its opening within twenty rounds, so this is loose by
#: two orders and catches only a mechanism that did nothing.
MINIMUM_MOVEMENT = 5e-3


@dataclass(frozen=True)
class PathSpec:
    """Everything that decides the path, and nothing else."""

    periods: int
    seed: int = 7
    #: The identification, swept rather than pinned. One means a round is a
    #: month; three holds each round for a quarter and stretches the transition
    #: against the cost rule's clocks without changing its shape.
    months_per_round: int = 1

    def rounds(self) -> int:
        return math.ceil(self.periods / self.months_per_round)


def retention_path(spec: PathSpec) -> list[tuple[float, ...]]:
    """``path[t][stratum]``, multiplying that stratum's income in month ``t``."""
    if spec.periods < 1:
        raise PathProblem("a path needs at least one period")
    if spec.months_per_round < 1:
        raise PathProblem("months_per_round must be at least one")

    config = dfa_calibrated(rounds=spec.rounds(), seed=spec.seed)
    if tuple(config.strata.counts) != tuple(DFA_COUNTS):
        raise PathProblem(
            f"the preset carries counts {tuple(config.strata.counts)} against "
            f"the cascade's {tuple(DFA_COUNTS)}; the two populations are not "
            f"the same population and the mapping would be an approximation "
            f"nobody registered"
        )
    if tuple(config.strata.wealth_share) != tuple(DFA_NET_WORTH_SHARES):
        raise PathProblem("the preset's wealth shares are not the DFA's")

    landing = np.asarray(run(config).terminating, dtype=float)
    opening = landing[0]
    if np.any(opening <= 0.0):
        raise PathProblem(
            "a stratum receives nothing in the opening round, so there is no "
            "level to normalise against"
        )

    multipliers = landing / opening
    if np.max(np.abs(multipliers[0] - 1.0)) > OPENING_TOLERANCE:
        raise PathProblem("the opening round did not normalise to one")

    moved = float(np.max(np.abs(multipliers - 1.0)))
    if moved < MINIMUM_MOVEMENT:
        raise PathProblem(
            f"no stratum moves by more than {moved:.2e} over "
            f"{spec.rounds()} rounds. A retention mechanism that moves nothing "
            f"is the control arm, and the control arm is built explicitly"
        )

    return [
        tuple(float(x) for x in multipliers[t // spec.months_per_round])
        for t in range(spec.periods)
    ]


def flat_path(periods: int, n_strata: int) -> list[tuple[float, ...]]:
    """The control. Built here rather than asked of the mechanism above."""
    return [tuple([1.0] * n_strata) for _ in range(periods)]


def describe(path: list[tuple[float, ...]]) -> list[tuple[int, tuple[float, ...]]]:
    """A few rows of the path, for a run to print what it is running on."""
    if not path:
        return []
    marks = sorted({0, 1, 5, 11, 23, len(path) - 1} & set(range(len(path))))
    return [(t, path[t]) for t in marks]
