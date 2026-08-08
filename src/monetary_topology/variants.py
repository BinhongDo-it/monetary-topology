"""One place to copy a config with named overrides.

Shared by the experiments and the tests so a sweep cannot accidentally re-default
a parameter it did not mean to change. Every field is listed explicitly rather
than reconstructed by reflection, so adding a field to ``EconomyConfig`` without
adding it here fails loudly at the next sweep.
"""

from __future__ import annotations

from .config import EconomyConfig

_FIELDS = (
    "strata",
    "spend",
    "adjacency",
    "wages",
    "authority",
    "initial_claims",
    "total_resources",
    "resource_withholding",
    "rounds",
    "seed",
)


def variant(base: EconomyConfig, **overrides: object) -> EconomyConfig:
    """Return a copy of ``base`` with ``overrides`` applied."""
    unknown = set(overrides) - set(_FIELDS)
    if unknown:
        raise ValueError(f"unknown config fields: {sorted(unknown)}")
    fields: dict[str, object] = {name: getattr(base, name) for name in _FIELDS}
    fields.update(overrides)
    return EconomyConfig(**fields)  # type: ignore[arg-type]
