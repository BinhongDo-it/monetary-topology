"""Tests for what the B5 retriever still owns: chunking and bisection.

Parsing, the collapse rule and the anomaly scan **moved into
``monetary_topology.parallel_rates``** and are tested in
``test_b5_parallel_rates.py``. They moved because the loader needs the same
rules and the same registered constants, and a pre-registered threshold that
exists in two files has two truths. The earlier version of this file, which
tested them here, is kept as ``test_b5_fetch.py.expired1``.

What is left is the part that talks to the network: how the window is divided,
and what happens when the endpoint refuses a span. Nothing here makes a request.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

#: Loaded by path because ``data/`` is a directory of scripts and not a package,
#: which is how the other fetchers in this repository are arranged.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
_SPEC = importlib.util.spec_from_file_location(
    "fetch_ambito", _ROOT / "data" / "fetch_ambito.py"
)
assert _SPEC and _SPEC.loader
fetch_ambito = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fetch_ambito)

ONE_SIDED = ("Referencia",)


# --------------------------------------------------------------------- chunking


def test_the_window_is_covered_exactly_once_and_clipped_at_both_ends():
    chunks = fetch_ambito.chunk_halves()
    assert chunks[0][2] == fetch_ambito.WINDOW_START
    assert chunks[-1][3] == fetch_ambito.WINDOW_END
    for (*_, end), (*_, start, _) in zip(chunks[:-1], chunks[1:], strict=True):
        assert (start - end).days == 1


def test_the_first_and_last_chunks_are_the_clipped_halves():
    """2019 has no first half inside the window and 2026 has no second."""
    chunks = fetch_ambito.chunk_halves()
    assert (chunks[0][0], chunks[0][1]) == (2019, 2)
    assert (chunks[-1][0], chunks[-1][1]) == (2026, 1)


def test_the_registered_window_comes_from_the_package():
    """The fetcher must not carry its own copy of a pre-registered constant."""
    from monetary_topology import parallel_rates

    assert fetch_ambito.WINDOW_START is parallel_rates.WINDOW_START
    assert fetch_ambito.WINDOW_END is parallel_rates.WINDOW_END
    assert fetch_ambito.JUMP_THRESHOLD == parallel_rates.JUMP_THRESHOLD


# ------------------------------------------------------------------- bisection


class _Server:
    """A stand-in for the endpoint, poisoned exactly the way the real one is.

    Any range spanning the 13-to-14 August 2025 boundary raises; both halves of
    it answer. That is the observed behaviour, bisected against ``dolarrava/cl``
    on 2026-08-11 and reproduced identically on ``dolarrava/mep``, which shares
    the backend. It is a deterministic server fault and not throttling:
    throttling answers 429, does not reproduce on exactly the same range, and
    would not let the two halves through while refusing their union.
    """

    BAD_LEFT = "2025-08-13"
    BAD_RIGHT = "2025-08-14"

    def __init__(self):
        self.asked = []

    def __call__(self, url, timeout=None):
        start, end = url.rsplit("/", 2)[-2:]
        self.asked.append((start, end))
        if start <= self.BAD_LEFT and end >= self.BAD_RIGHT:
            raise fetch_ambito.ServerUnavailable("HTTP 500 after 3 attempts")
        return b'[["Fecha","Referencia"],["01/08/2025","1366,90"]]'


def _with_fake_server(server, tmp_path, start, end):
    """Run one ``fetch_range`` against a stand-in endpoint.

    ``download`` is replaced wholesale, so the retry sleeps inside it never
    happen and the test does not have to reach into the ``time`` module.
    """
    real_download, real_raw = fetch_ambito.download, fetch_ambito.RAW
    try:
        fetch_ambito.download = server
        fetch_ambito.RAW = tmp_path
        return fetch_ambito.fetch_range(
            "ccl", "dolarrava/cl", ONE_SIDED,
            date.fromisoformat(start), date.fromisoformat(end),
            "ambito_ccl_probe.json", force=True,
        )
    finally:
        fetch_ambito.download = real_download
        fetch_ambito.RAW = real_raw


def test_a_poisoned_range_is_bisected_until_both_sides_answer(tmp_path):
    """**No fixed chunk size is safe, so the size adapts.**

    A window wider than a day can straddle a boundary the endpoint refuses. The
    fetcher must not respond by giving up on the window, and must not respond by
    inventing what is inside it.
    """
    got = _with_fake_server(_Server(), tmp_path, "2025-08-10", "2025-08-17")

    # The bisected nodes are notes about the endpoint, not chunks; the leaves
    # are what must cover the range.
    leaves = [r for r in got if r["status"] != "bisected"]
    assert all(r["status"] in ("downloaded", "empty") for r in leaves), leaves
    covered = [r["range"] for r in leaves]
    assert covered[0][0] == "2025-08-10"
    assert covered[-1][1] == "2025-08-17"
    for (_, left_end), (right_start, _) in zip(
        covered[:-1], covered[1:], strict=True
    ):
        gap = date.fromisoformat(right_start) - date.fromisoformat(left_end)
        assert gap.days == 1, f"bisection left a hole at {left_end}"


def test_bisection_writes_one_verbatim_response_per_file(tmp_path):
    """Pieces are stored separately rather than stitched into one archive.

    Concatenating two responses would produce a file that no request would ever
    return, and the manifest's two hashes would then describe something the
    endpoint never sent.
    """
    got = _with_fake_server(_Server(), tmp_path, "2025-08-10", "2025-08-17")
    leaves = [r for r in got if r["status"] != "bisected"]
    written = sorted(p.name for p in tmp_path.glob("*.json"))
    assert len(written) == len(leaves)
    assert all(name.startswith("ambito_ccl_2025-08-") for name in written)


def test_the_bisection_tree_is_remembered_and_not_rediscovered(tmp_path):
    """**The memo caches the shape of the failure, not the data.**

    A range the endpoint refuses is never written, so without a memo every run
    re-asks for it, waits out three retries with backoff at each internal node,
    and rediscovers a tree it already knew. Measured on the real endpoint that is
    about seventy seconds per run across the two ``dolarrava`` series.

    Second run must ask for nothing: the memo splits, the leaves are cached.
    """
    server = _Server()
    first = _with_fake_server(server, tmp_path, "2025-08-10", "2025-08-17")
    memo = {
        (c["series"], c["range"][0], c["range"][1])
        for c in first if c.get("status") == "bisected"
    }
    assert memo, "the bisected node was not recorded"

    second_server = _Server()
    real_download, real_raw = fetch_ambito.download, fetch_ambito.RAW
    try:
        fetch_ambito.download = second_server
        fetch_ambito.RAW = tmp_path
        again = fetch_ambito.fetch_range(
            "ccl", "dolarrava/cl", ONE_SIDED,
            date(2025, 8, 10), date(2025, 8, 17),
            "ambito_ccl_probe.json", force=False, known_bad=memo,
        )
    finally:
        fetch_ambito.download = real_download
        fetch_ambito.RAW = real_raw

    assert second_server.asked == [], second_server.asked
    assert {c["status"] for c in again} <= {"bisected", "cached-complete",
                                            "cached-empty"}


def test_force_re_probes_a_range_the_memo_calls_bad(tmp_path):
    """The endpoint may be fixed, and a memo that could never expire would hide it.

    ``--force`` clears the memo at the call site in ``main``; here the same
    intent is expressed by passing ``force=True``, which must reach the network
    rather than trusting the note.
    """
    server = _Server()
    memo = {("ccl", "2025-08-10", "2025-08-17")}
    real_download, real_raw = fetch_ambito.download, fetch_ambito.RAW
    try:
        fetch_ambito.download = server
        fetch_ambito.RAW = tmp_path
        fetch_ambito.fetch_range(
            "ccl", "dolarrava/cl", ONE_SIDED,
            date(2025, 8, 10), date(2025, 8, 17),
            "ambito_ccl_probe.json", force=True, known_bad=memo,
        )
    finally:
        fetch_ambito.download = real_download
        fetch_ambito.RAW = real_raw

    assert ("2025-08-10", "2025-08-17") in server.asked


def test_a_bisected_node_carries_no_data_and_no_hash(tmp_path):
    """It is a note about the endpoint, not a chunk.

    ``main`` counts it separately for the same reason: folding it into the held
    count would inflate the number of chunks and deflate rows per chunk, and
    both are read by eye.
    """
    got = _with_fake_server(_Server(), tmp_path, "2025-08-10", "2025-08-17")
    node = next(c for c in got if c["status"] == "bisected")
    assert "sha256_stored" not in node
    assert "rows" not in node
    assert node["split_at"] == "2025-08-13"


def test_a_single_day_that_still_fails_is_recorded_and_left_absent(tmp_path):
    """**There is no substitute for it that would not be an invention.**

    **This repository forbids repair**, and a missing day filled from a
    neighbour, a different agent class, or an interpolation is repair wearing a
    different hat. For MEP and CCL specifically, a filled gap would be filled with the
    quantity in dispute (``b4_directed_edges.md`` §5.2).
    """
    class AlwaysDown:
        def __call__(self, url, timeout=None):
            raise fetch_ambito.ServerUnavailable("HTTP 500 after 3 attempts")

    real_download, real_raw = fetch_ambito.download, fetch_ambito.RAW
    try:
        fetch_ambito.download = AlwaysDown()
        fetch_ambito.RAW = tmp_path
        got = fetch_ambito.fetch_range(
            "ccl", "dolarrava/cl", ONE_SIDED,
            date(2025, 8, 13), date(2025, 8, 13),
            "ambito_ccl_probe.json", force=True,
        )
    finally:
        fetch_ambito.download = real_download
        fetch_ambito.RAW = real_raw

    assert len(got) == 1
    assert got[0]["status"] == "unretrievable"
    assert list(tmp_path.glob("*.json")) == []


def test_a_client_error_is_not_retried_and_not_bisected(tmp_path):
    """A 404 is the server answering, not failing.

    The CCL path was wrong for a whole run and answered 404 fourteen times per
    series. Retrying or bisecting that would have turned one wrong path into
    hundreds of requests asking the same question.
    """
    calls = []

    class NotFound:
        def __call__(self, url, timeout=None):
            calls.append(url)
            raise OSError("HTTP Error 404: Not Found")

    real_download, real_raw = fetch_ambito.download, fetch_ambito.RAW
    try:
        fetch_ambito.download = NotFound()
        fetch_ambito.RAW = tmp_path
        got = fetch_ambito.fetch_range(
            "ccl", "dolarrava/ccl", ONE_SIDED,
            date(2025, 7, 1), date(2025, 12, 31),
            "ambito_ccl_probe.json", force=True,
        )
    finally:
        fetch_ambito.download = real_download
        fetch_ambito.RAW = real_raw

    assert len(calls) == 1
    assert got[0]["status"] == "error"
    assert list(tmp_path.glob("*.json")) == []


def test_a_response_that_does_not_parse_is_not_archived(tmp_path):
    """An unparseable response is reported, and the chunk stays absent.

    Archiving it would make the next run treat it as cached, and the failure
    would become permanent and silent.
    """
    class Garbage:
        def __call__(self, url, timeout=None):
            return b"<html>maintenance</html>"

    real_download, real_raw = fetch_ambito.download, fetch_ambito.RAW
    try:
        fetch_ambito.download = Garbage()
        fetch_ambito.RAW = tmp_path
        got = fetch_ambito.fetch_range(
            "ccl", "dolarrava/cl", ONE_SIDED,
            date(2025, 7, 1), date(2025, 7, 2),
            "ambito_ccl_probe.json", force=True,
        )
    finally:
        fetch_ambito.download = real_download
        fetch_ambito.RAW = real_raw

    assert got[0]["status"] == "error"
    assert list(tmp_path.glob("*.json")) == []


def test_an_atomic_write_leaves_no_partial_file(tmp_path):
    fetch_ambito.write_atomic(tmp_path / "x.json", b"[]")
    assert (tmp_path / "x.json").read_bytes() == b"[]"
    assert list(tmp_path.glob("*.partial")) == []


@pytest.mark.parametrize("status", ["complete", "empty", "bad"])
def test_chunk_status_classifies_the_three_cases(tmp_path, status):
    payloads = {
        "complete": '[["Fecha","Referencia"],["01/07/2025","1233,08"]]',
        "empty": '[["Fecha","Referencia"]]',
        "bad": "{not json",
    }
    path = tmp_path / "chunk.json"
    path.write_text(payloads[status], encoding="utf-8")
    assert fetch_ambito.chunk_status(path, ONE_SIDED)[0] == status
