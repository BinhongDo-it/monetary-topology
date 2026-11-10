"""A1c quotes A1-2's population from A1b's record; the two must agree.

``A1B_A1_2_POPULATION`` is a constant in the A1c driver, written beside this
stage's own count of defaulters. Nothing else ties it to the record it names,
so a rerun of A1b on another configuration would leave A1c printing the old
pair. This reads the record and compares.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _driver():
    path = ROOT / "experiments" / "a1c_household_order.py"
    spec = importlib.util.spec_from_file_location("a1c_household_order", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a1_2_population_matches_a1b_record() -> None:
    record = json.loads(
        (ROOT / "results" / "a1b_default_cascade.json").read_text(encoding="utf-8"))
    households, defaulting = _driver().A1B_A1_2_POPULATION
    assert households == record["households"]
    by_tenure = record["first_default_shares_by_tenure"]
    assert defaulting == sum(row["defaulting_households"]
                             for tenure, row in by_tenure.items()
                             if not tenure.startswith("_"))
    a1_2 = next(c for c in record["criteria"] if c["name"].startswith("A1-2"))
    assert f"{defaulting:,} defaulting households" in a1_2["detail"]
