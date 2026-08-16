"""A three-function stand-in for pytest, for the sandbox only.

The sandbox this repository is edited from has no package index reachable, so
``import pytest`` fails there while the tests themselves are fine. This module
provides ``approx``, ``raises`` and ``fixture`` so the suite can be executed as
a smoke check before it is handed to a machine that has the real thing.

**It is not the test runner.** It does not collect, it does not report, it does
not implement parametrisation, and a suite passing under it has not been run.
``scripts/run_all.py`` and CI both use pytest.
"""
from __future__ import annotations

import math
from contextlib import contextmanager


class _Approx:
    def __init__(self, expected, rel=None, abs=None):
        self.expected = expected
        self.rel = rel
        self.abs = abs

    def _close(self, got, want) -> bool:
        rel = 1e-6 if self.rel is None else self.rel
        abs_ = 1e-12 if self.abs is None else self.abs
        return math.isclose(got, want, rel_tol=rel, abs_tol=abs_)

    def __eq__(self, other) -> bool:
        if isinstance(self.expected, (list, tuple)):
            if len(other) != len(self.expected):
                return False
            return all(self._close(a, b)
                       for a, b in zip(other, self.expected, strict=True))
        return self._close(other, self.expected)

    def __repr__(self) -> str:
        return f"approx({self.expected!r})"


def approx(expected, rel=None, abs=None):
    return _Approx(expected, rel=rel, abs=abs)


class Failed(AssertionError):
    pass


class _Caught:
    """What ``with raises(X) as exc`` binds. ``exc.value`` is the exception."""

    value: BaseException | None = None


@contextmanager
def raises(expected, match=None):
    caught = _Caught()
    try:
        yield caught
    except expected as exc:
        caught.value = exc
        if match is not None:
            import re
            if not re.search(match, str(exc)):
                raise Failed(f"{exc!r} does not match {match!r}") from exc
        return
    except Exception as exc:  # noqa: BLE001
        raise Failed(f"raised {type(exc).__name__}, wanted {expected}") from exc
    raise Failed(f"nothing raised, wanted {expected}")


def fixture(*args, **kwargs):
    def wrap(fn):
        return fn
    return wrap(args[0]) if args and callable(args[0]) else wrap
