"""`a3c_load_bearing.build` routes a keyword by which dataclass declares it.

`docs/a7_continuous_c.md` section 3.1 names this as the second thing A7 needs.
`shortcut_rate` lives on `NetworkSpec`, every keyword used to go to `AssetSpec`,
and a sweep cell therefore could not reach the parameter A7 sweeps.

Four claims.

**The two name sets must stay disjoint.** The split is well defined only while
they are, and a name in both would reach one constructor and silently not reach
the other. This repository has already paid for that defect with a different
parameter: it reached one of two call sites, the default path was the correct
one, so nothing fired until a sweep took the other branch. The module raises at
import rather than letting a grid cell discover it.

**Both sides must actually be routed.** A test that only checks the new side
would pass on an implementation that sent everything to `NetworkSpec`.

**A typo must still fail.** The old signature got that for free, since an
unknown name reached `AssetSpec` and raised. Splitting the dictionary is exactly
the kind of change that turns a `TypeError` into a silently dropped cell.

**And `seed` must stay unreachable.** It is a named parameter, so a cell that
sets it collides before the body runs. The implementation carries a comment
saying so rather than a check that can never be true, and this is where that
claim is held: if a later signature change makes `seed` reachable through
`**kw`, this test fails and the comment gets fixed with it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from monetary_topology.network import build_graph

ROOT = Path(__file__).resolve().parents[1]

#: Short runs. Nothing here reads a result, only where a keyword landed.
ROUNDS = 5


def _a3c():
    path = ROOT / "experiments" / "a3c_load_bearing.py"
    spec = importlib.util.spec_from_file_location("a3c_load_bearing", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cell(module, **extra) -> dict:
    return {**module.FIXED, **module.CELLS["both"], **extra}


def test_the_two_field_sets_are_disjoint() -> None:
    module = _a3c()
    assert module._NETWORK_FIELDS & module._ASSET_FIELDS == frozenset()
    assert "shortcut_rate" in module._NETWORK_FIELDS
    assert "terms_spread" in module._ASSET_FIELDS


def test_a_network_keyword_reaches_the_spec() -> None:
    module = _a3c()
    model = module.build(0, ROUNDS, **_cell(module, shortcut_rate=0.5))
    assert model.a3.network.spec.shortcut_rate == pytest.approx(0.5)


def test_an_asset_keyword_still_reaches_the_asset_spec() -> None:
    module = _a3c()
    model = module.build(0, ROUNDS, **_cell(module))
    assert model.a3.asset.terms_spread == pytest.approx(module.KAPPA)
    assert model.a3.network.spec.shortcut_rate == 0.0


def test_the_routed_value_reaches_the_graph_and_not_only_the_spec() -> None:
    """The spec carrying the value is not the claim. The claim is that the
    adjacency the model runs on is the one that value produces."""
    module = _a3c()
    model = module.build(0, ROUNDS, **_cell(module, shortcut_rate=0.5))
    spec = model.a3.network.spec
    dense = build_graph(spec)
    sparse = build_graph(spec.replace(shortcut_rate=0.0))
    assert dense.sum() > 10 * sparse.sum()
    # The model folds the payroll mask in on top, so it is a superset of the
    # bare graph rather than equal to it.
    assert np.all(model.adjacency >= dense)
    assert model.adjacency.sum() - dense.sum() < 0.05 * dense.sum()


def test_a_typo_is_refused_rather_than_dropped() -> None:
    module = _a3c()
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        module.build(0, ROUNDS, **_cell(module, no_such_parameter=1))


def test_seed_cannot_be_set_by_a_cell() -> None:
    """Refused by Python's own argument binding, which is why the
    implementation carries a comment instead of a check."""
    module = _a3c()
    with pytest.raises(TypeError, match="seed"):
        module.build(0, ROUNDS, **_cell(module, seed=3))
