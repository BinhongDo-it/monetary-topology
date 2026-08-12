"""Tests for B5's cycle machinery, criteria B5-1 and B5-2 among them.

These are the guards `docs/b5_orphan_prereg.md` §8 puts before everything else:
if B5-1 or B5-2 fails, the machinery is wrong and nothing else may be read.

The load-bearing test is `test_the_machinery_reproduces_the_closed_form`. It
walks a square through `directed.directed_square`, which looks every leg up in a
`DirectedField`, and compares that against `2 log(mid_b / mid_a)` computed from
the quotes. **Two independent paths to one number**, which is the only kind of
self-consistency check worth writing: a test that recomputes the closed form the
same way the code does tests nothing.

`test_the_spread_cancels_out_of_the_headline` is the one that protects the
paper's main defence. If the index part could be moved by widening a spread, an
objector could say the whole result is a bid-ask artefact, and they would be
right.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from monetary_topology.orphan_squares import (
    ARS,
    N_POSITIONS,
    USD,
    build_field,
    daily_matrices,
    edge_weights,
    friction_matrix,
    index_matrix,
    quote_legs,
    quotes_for_date,
    rms,
    square_via_machinery,
)

KEYS = ("oficial", "informal", "mep")

#: One plausible day: the official window tight, the blue wide, MEP in between
#: and quoted on one side only.
QUOTES = {
    "oficial": (1008.55, 1066.34),
    "informal": (1195.0, 1215.0),
    "mep": (1162.12, 1162.12),
}


def mid(pair):
    return math.sqrt(pair[0] * pair[1])


# ------------------------------------------------------------------ conversion


def test_a_single_quote_series_returns_the_same_number_twice():
    """The honest encoding of "this market publishes no spread".

    It makes ``w_bar`` exactly zero rather than approximately zero, so a friction
    column built on it is visibly empty instead of quietly small.
    """
    assert quote_legs({"referencia": 1162.12}, ("Referencia",)) == (1162.12, 1162.12)


def test_the_directed_weights_recover_theorem_sixs_two_parts():
    """``w_hat`` is minus the log geometric mid, ``w_bar`` minus half the spread.

    Both are read straight off ``(f - b)/2`` and ``(f + b)/2``, which is Theorem
    6's split, so this checks that the quote-to-weight step lands where the
    theorem expects rather than somewhere that merely looks similar.
    """
    bid, ask = 1195.0, 1215.0
    fwd, rev = edge_weights(bid, ask)
    assert (fwd + rev) / 2 == pytest.approx(0.5 * math.log(bid / ask))
    assert (fwd - rev) / 2 == pytest.approx(-math.log(math.sqrt(bid * ask)))


def test_the_friction_part_is_never_positive():
    """No-arbitrage locks the sign: a round trip through one dealer cannot pay.

    A positive value here would mean the machinery had produced free money, which
    is a bug and never a finding.
    """
    f = friction_matrix(QUOTES, KEYS)
    assert (f <= 1e-15).all()


def test_a_non_positive_quote_raises():
    with pytest.raises(ValueError):
        edge_weights(0.0, 1200.0)


# ------------------------------------------------------- B5-1, the closed form


def test_the_machinery_reproduces_the_closed_form():
    """**B5-1.** Two independent paths to one number.

    One walks the four edges of the square through a ``DirectedField``, looking
    every leg up including the agent legs. The other is
    ``2 log(mid_b / mid_a)``. They must agree to machine precision, because the
    closed form is what every later criterion is computed from and the walk is
    what the theorems are stated about.
    """
    field = build_field(QUOTES, KEYS)
    closed = index_matrix(QUOTES, KEYS)
    friction = friction_matrix(QUOTES, KEYS)
    worst = 0.0
    for a in range(len(KEYS)):
        for b in range(len(KEYS)):
            if a == b:
                continue
            s, s_rev = square_via_machinery(field, a, b)
            worst = max(worst, abs(s - s_rev - closed[a, b]))
            worst = max(worst, abs(s + s_rev - friction[a, b]))
    assert worst < 1e-12, worst


def test_the_index_matrix_is_antisymmetric_and_the_friction_symmetric():
    index = index_matrix(QUOTES, KEYS)
    friction = friction_matrix(QUOTES, KEYS)
    assert np.abs(index + index.T).max() < 1e-12
    assert np.abs(friction - friction.T).max() < 1e-12


def test_the_agent_legs_are_present_in_the_field_rather_than_assumed():
    """``directed_square`` looks them up, so they have to be there.

    Hard-coding them as zero inside the walk would make the function unable to
    report a violation of the assumption it depends on, and ``b1_theorem.md`` §8
    is entirely about when that assumption fails.
    """
    field = build_field(QUOTES, KEYS)
    for pos in (ARS, USD):
        assert field.has(0 * N_POSITIONS + pos, 1 * N_POSITIONS + pos)
        assert field.value(0 * N_POSITIONS + pos, 1 * N_POSITIONS + pos) == 0.0


def test_every_position_edge_is_two_way_so_theorem_six_applies():
    """Both classes quote both directions, so the split is defined everywhere.

    ``b4`` §5.2: on a one-way edge the decomposition degenerates rather than
    returning a large number, and that degeneracy is itself the criterion for
    which failure is in front of you.
    """
    field = build_field(QUOTES, KEYS)
    assert field.one_way() == []
    hat, bar = __import__(
        "monetary_topology.directed", fromlist=["split"]
    ).split(field)
    assert len(hat) == len(bar)


# --------------------------------------------------------- B5-2, trivial square


def test_the_trivial_square_is_exactly_zero_off_the_diagonal():
    """**B5-2**, read off the same matrix every other number comes from.

    Not short-circuited on ``a == b``: that would test the ``if``.
    """
    index = index_matrix(QUOTES, KEYS)
    assert np.abs(np.diag(index)).max() == 0.0


def test_walking_a_trivial_square_is_refused_rather_than_faked():
    """With one class the square degenerates to a self-loop at the agent legs.

    Returning zero here would hide that, and the zero would then look like
    evidence rather than like a definition.
    """
    field = build_field(QUOTES, KEYS)
    with pytest.raises(ValueError, match="two distinct classes"):
        square_via_machinery(field, 1, 1)


# ----------------------------------------------- the spread cancels, which is B4


def test_the_spread_cancels_out_of_the_headline():
    """**The defence B4 bought, as a test.**

    Widen one class's spread while holding its geometric mid fixed. The index
    part must not move at all, and the friction part must. If the index part
    moved, an objector could call the whole result a bid-ask artefact, and
    ``b4`` §5.1 says that in a thin market they would be right about the
    single-orientation number ``S``.
    """
    tight = dict(QUOTES)
    wide = dict(QUOTES)
    centre = mid(QUOTES["informal"])
    wide["informal"] = (centre / 1.5, centre * 1.5)

    assert mid(wide["informal"]) == pytest.approx(centre)
    assert np.abs(
        index_matrix(tight, KEYS) - index_matrix(wide, KEYS)
    ).max() < 1e-12
    assert friction_matrix(wide, KEYS)[1, 1] < friction_matrix(tight, KEYS)[1, 1]


def test_a_single_quote_class_carries_no_friction():
    """Which is why MEP and CCL enter the headline and not the column beside it."""
    friction = friction_matrix(QUOTES, KEYS)
    assert friction[2, 2] == pytest.approx(0.0)
    assert friction[0, 2] == pytest.approx(friction_matrix(QUOTES, KEYS)[0, 0] / 2)


# ---------------------------------------------------------------- date handling


def _panel():
    return {
        "oficial": {"2025-01-10": {"compra": 1008.55, "venta": 1066.34},
                    "2025-01-13": {"compra": 1010.0, "venta": 1068.0}},
        "informal": {"2025-01-10": {"compra": 1195.0, "venta": 1215.0}},
        "mep": {"2025-01-10": {"referencia": 1162.12},
                "2025-01-13": {"referencia": 1163.21}},
    }


def test_a_date_missing_any_required_class_is_dropped_entirely():
    """``b5_orphan_prereg.md`` §7, as code rather than as a note.

    Returning a partial dictionary would make the rule negotiable at the call
    site, and the negotiation would happen on the day someone wanted one more
    observation.
    """
    panel = _panel()
    assert quotes_for_date(panel, "2025-01-10", KEYS) is not None
    assert quotes_for_date(panel, "2025-01-13", KEYS) is None


def test_the_two_stacks_are_computed_on_the_same_dates():
    """**What makes B5-8 readable.**

    The index and friction stacks must come from the same days and the same
    quotes, so a divergence between them is a finding and not a difference in
    coverage.
    """
    used, index, friction = daily_matrices(
        _panel(), ["2025-01-10", "2025-01-13"], KEYS
    )
    assert used == ["2025-01-10"]
    assert index.shape == friction.shape == (1, 3, 3)


def test_an_empty_arm_is_nan_and_not_zero():
    """An arm with no observations must not read as a quiet one.

    ``PROJECT_PLAN.md`` §11.11 rule 1: a comparison with an empty side fails and
    says ``vacuous``; it does not pass for lack of a counterexample. A zero here
    would sail through any "did it collapse" threshold.
    """
    assert math.isnan(rms(np.empty(0)))
    assert rms(np.array([3.0, 4.0])) == pytest.approx(math.sqrt(12.5))


# ------------------------------------------------- the friction-leg source audit


def _audit():
    """``experiments/b5_friction.py`` is a script; loaded by path like the rest."""
    import importlib.util
    import sys
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    spec = importlib.util.spec_from_file_location(
        "b5_friction", root / "experiments" / "b5_friction.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dated(*values):
    return [
        {"date": f"2025-01-{i + 1:02d}", "venta": v} for i, v in enumerate(values)
    ]


def test_the_frozen_run_detector_pairs_both_sides_of_the_sequence():
    """**Regression.** ``zip(rows, rows[1:], strict=True)`` raises.

    The two sequences differ in length by one. ``strict=True`` was added to
    satisfy B905 and **is not a formatting detail** — it changes behaviour — so
    adding it without slicing both sides turned a lint fix into a runtime
    failure. That has now happened twice in this stage, which is why it is
    pinned here rather than remembered.
    """
    audit = _audit()
    assert audit.longest_frozen_run(_dated(1.0, 5.0, 5.0, 5.0, 2.0), "venta") == (
        3, "2025-01-04",
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [((), 0), ((1.0,), 1), ((1.0, 2.0, 3.0), 1), ((7.0, 7.0, 7.0, 7.0), 4)],
)
def test_the_frozen_run_detector_handles_the_degenerate_lengths(values, expected):
    """Zero and one row must not raise; a run is not defined without a pair."""
    audit = _audit()
    assert audit.longest_frozen_run(_dated(*values), "venta")[0] == expected


def test_the_audit_thresholds_are_the_ones_the_mayorista_failure_set():
    """The disqualifier is the test that already caught a bad series.

    ``mayorista``'s longest unchanged sell quote was 71 days against 13 for a
    sound series, so 21 sits between them with room on both sides. A threshold
    chosen after seeing the candidate would be choosing to admit it.
    """
    audit = _audit()
    assert audit.MAX_FROZEN_RUN_DAYS == 21
    assert audit.MODAL_SPREAD_SHARE == 0.50
