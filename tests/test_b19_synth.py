# -*- coding: utf-8 -*-
"""Synthetic check on the B19 gate-zero script.

A run whose only possible outcome is "the code is wrong" is a unit test, and it
belongs on a synthetic example that takes seconds, not on the full sample.

Three firms, of which two fall by exactly the same amount and only one is pushed
out by the gate whose threshold moves with the price. That is the shape the whole
design rests on, so its answer is worked out by hand, and it is also the one place
the objection "being pushed out is mechanically collinear with falling" would bite.

It also pins a real defect: sub.txt pads CIK with leading zeros while
company_tickers.json carries integers. Without normalising both sides, the
"with market cap" column silently reads zero while every funnel step and every
firm count stays correct.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "experiments" / "b19_shariah_gate0.py"

# cik (zero padded, as sub.txt writes it), name, debt, symbol, price t0, price t1
FIRMS = [
    ("0000000001", "A Corp", 30.0, "AAA", 10.0, 5.0),   # .30 vs .60 -> the two disagree
    ("0000000002", "B Corp", 10.0, "BBB", 10.0, 5.0),   # same fall, both rulebooks pass
    ("0000000003", "C Corp", 50.0, "CCC", 10.0, 10.0),  # both fail
]


def _build(root: Path, shares_tag: str = "CommonStockSharesOutstanding") -> None:
    R = root / "data" / "raw" / "shariah"
    (R / "prices").mkdir(parents=True, exist_ok=True)
    sub = "adsh\tcik\tname\tsic\tform\tperiod\n"
    num = "adsh\ttag\tversion\tddate\tqtrs\tuom\tvalue\n"
    for i, (cik, name, debt, sym, p0, p1) in enumerate(FIRMS, 1):
        adsh = f"0001-24-00000{i}"
        sub += f"{adsh}\t{cik}\t{name}\t1234\t10-K\t20241231\n"
        num += f"{adsh}\tDebtCurrent\tus-gaap/2024\t20241231\t0\tUSD\t{debt}\n"
        num += f"{adsh}\tAssets\tus-gaap/2024\t20241231\t0\tUSD\t100.0\n"
        num += f"{adsh}\t{shares_tag}\tus-gaap/2024\t20241231\t0\tshares\t10.0\n"
        (R / "prices" / f"{sym}.csv").write_text(
            "Date,Open,High,Low,Close,Volume\n"
            f"2023-12-29,{p0},{p0},{p0},{p0},1000\n"
            f"2024-12-31,{p1},{p1},{p1},{p1},1000\n",
            encoding="utf-8", newline="\n")
    with zipfile.ZipFile(R / "2024q4.zip", "w") as z:
        z.writestr("sub.txt", sub)
        z.writestr("num.txt", num)
    (R / "company_tickers.json").write_text(json.dumps({
        str(i): {"cik_str": int(c.lstrip("0")), "ticker": s, "title": n}
        for i, (c, n, _d, s, _a, _b) in enumerate(FIRMS)}), encoding="utf-8")


def _run(root: Path) -> dict:
    r = subprocess.run([sys.executable, str(SCRIPT), "--gate0"], cwd=root,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((root / "results" / "b19_shariah_gate0.json").read_text(encoding="utf-8"))


def test_gate0_on_synthetic(tmp_path: Path) -> None:
    _build(tmp_path)
    rec = _run(tmp_path)
    assert rec["n_firms"] == 3
    assert rec["n_firm_periods"] == 3
    # these two read zero if the CIK sides are not normalised, while the two above pass
    assert rec["n_priced"] == 3, "market caps did not join: CIK formats differ across sides"
    assert rec["n_with_return"] == 3
    assert rec["n_disagree"] == 1, "only A Corp is judged differently by the two rulebooks"

    cell = rec["cells"]["(-1.01,-0.50]"]
    assert cell["n"] == 2, "A and B fall by the same amount and must land in one bucket"
    assert cell["pushed_out_by_breathing_gate"] == 1
    assert cell["compliant_both"] == 1
    assert cell["pushed_out_by_breathing_gate"] + cell["compliant_both"] == cell["n"]


def test_shares_tag_fallback_order(tmp_path: Path) -> None:
    """Any tag in the list works, and the reading does not depend on which one."""
    _build(tmp_path, shares_tag="WeightedAverageNumberOfSharesOutstandingBasic")
    rec = _run(tmp_path)
    assert rec["n_priced"] == 3
    assert rec["n_disagree"] == 1


def test_record_states_it_is_not_a_licensed_reading(tmp_path: Path) -> None:
    _build(tmp_path)
    rec = _run(tmp_path)
    assert rec.get("diagnostic_only") is True
    assert isinstance(rec.get("diagnostic_reason"), str) and len(rec["diagnostic_reason"]) > 10

def test_debt_groups_do_not_double_count(tmp_path: Path) -> None:
    """A filer reporting the aggregate and both of its parts must be counted once.

    A flat sum over the tag list gives 200 where the balance sheet says 100, and the
    error only ever inflates the ratio, which is the quantity that decides whether a
    firm is pushed out by the moving gate.
    """
    R = tmp_path / "data" / "raw" / "shariah"
    (R / "prices").mkdir(parents=True, exist_ok=True)
    sub = "adsh\tcik\tname\tsic\tform\tperiod\n"
    num = "adsh\ttag\tversion\tddate\tqtrs\tuom\tvalue\n"
    rows = [
        # cik, name, sym, tags: reports aggregate AND both parts -> must read 100
        ("1", "Split Co", "SPL", [("LongTermDebt", 100.0),
                                  ("LongTermDebtNoncurrent", 80.0),
                                  ("LongTermDebtCurrent", 20.0)]),
        # reports only the aggregate -> fallback must fire, also 100
        ("2", "Agg Co", "AGG", [("LongTermDebt", 100.0)]),
    ]
    for i, (cik, name, sym, tags) in enumerate(rows, 1):
        adsh = f"0001-24-00000{i}"
        sub += f"{adsh}\t{cik}\t{name}\t1234\t10-K\t20241231\n"
        for tg, v in tags:
            num += f"{adsh}\t{tg}\tus-gaap/2024\t20241231\t0\tUSD\t{v}\n"
        num += f"{adsh}\tAssets\tus-gaap/2024\t20241231\t0\tUSD\t1000.0\n"
        num += f"{adsh}\tCommonStockSharesOutstanding\tus-gaap/2024\t20241231\t0\tshares\t10.0\n"
        # cash-flow flow item with qtrs=4: must never enter the balance
        num += f"{adsh}\tRepaymentsOfLongTermDebt\tus-gaap/2024\t20241231\t4\tUSD\t999999.0\n"
        (R / "prices" / f"{sym}.csv").write_text(
            "Date,Open,High,Low,Close,Volume\n2023-12-29,10,10,10,10,1000\n"
            "2024-12-31,10,10,10,10,1000\n", encoding="utf-8", newline="\n")
    with zipfile.ZipFile(R / "2024q4.zip", "w") as z:
        z.writestr("sub.txt", sub)
        z.writestr("num.txt", num)
    (R / "company_tickers.json").write_text(json.dumps({
        "0": {"cik_str": 1, "ticker": "SPL", "title": "Split Co"},
        "1": {"cik_str": 2, "ticker": "AGG", "title": "Agg Co"}}), encoding="utf-8")

    # Read the number, not the verdict. Double counting gives 200 where the balance
    # sheet says 100, and both land outside the 0.30 screen, so any assertion on the
    # verdict passes either way. The quantity has to be read directly.
    import importlib.util
    spec = importlib.util.spec_from_file_location("b19", SCRIPT)
    b19 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b19)
    import os
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        panel, funnel = b19.build_panel(sorted((R).glob("*.zip")),
                                        b19.DEBT_TAGS, b19.SHARES_TAGS)
    finally:
        os.chdir(cwd)
    assert panel["1"]["20241231"]["debt"] == 100.0, (
        f"aggregate plus both parts must count once, got {panel['1']['20241231']['debt']}")
    assert panel["2"]["20241231"]["debt"] == 100.0, (
        f"aggregate alone must fire the fallback, got {panel['2']['20241231']['debt']}")
    # and the cash-flow row with qtrs=4 must never have entered
    assert panel["1"]["20241231"]["debt"] < 1000.0

def test_co_registrant_rows_are_not_mixed_into_the_parent(tmp_path: Path) -> None:
    """A parent and its wholly owned subsidiary file together; only the parent counts.

    Taken from a real reading: a utility holding company's own share count is 229
    million and its subsidiary's is 1, both carried under one CIK in one filing, and
    both are legal values. Whichever the loop happens to see last decides the answer,
    so the total assets series jumps between 9.5 and 31 billion across quarters while
    every individual number stays valid. Counts cannot catch this; the entity has to
    be pinned.
    """
    R = tmp_path / "data" / "raw" / "shariah"
    (R / "prices").mkdir(parents=True, exist_ok=True)
    sub = "adsh\tcik\tname\tsic\tform\tperiod\n0001-24-000001\t1\tParent Co\t4911\t10-K\t20241231\n"
    num = "adsh\ttag\tversion\tcoreg\tddate\tqtrs\tuom\tvalue\n"
    parent = [("Assets", 3.0e10), ("LongTermDebtNoncurrent", 4.0e9),
              ("CommonStockSharesOutstanding", 2.29e8)]
    subsid = [("Assets", 1.3e10), ("LongTermDebtNoncurrent", 2.0e9),
              ("CommonStockSharesOutstanding", 1.0)]
    for tg, v in parent:      # consolidated rows carry an empty coreg
        num += f"0001-24-000001\t{tg}\tus-gaap/2024\t\t20241231\t0\tUSD\t{v}\n"
    for tg, v in subsid:      # the subsidiary's own rows, named in coreg
        num += f"0001-24-000001\t{tg}\tus-gaap/2024\tSUBCO\t20241231\t0\tUSD\t{v}\n"
    with zipfile.ZipFile(R / "2024q4.zip", "w") as z:
        z.writestr("sub.txt", sub)
        z.writestr("num.txt", num)
    (R / "company_tickers.json").write_text(json.dumps(
        {"0": {"cik_str": 1, "ticker": "PAR", "title": "Parent Co"}}), encoding="utf-8")
    (R / "prices" / "PAR.csv").write_text(
        "Date,Open,High,Low,Close,Volume\n2023-12-29,50,50,50,50,0\n"
        "2024-12-31,50,50,50,50,0\n", encoding="utf-8", newline="\n")

    import importlib.util, os
    spec = importlib.util.spec_from_file_location("b19", SCRIPT)
    b19 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b19)
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        panel, _ = b19.build_panel(sorted(R.glob("*.zip")), b19.DEBT_TAGS, b19.SHARES_TAGS)
    finally:
        os.chdir(cwd)
    rec = panel["1"]["20241231"]
    assert rec["shares"] == 2.29e8, f"subsidiary share count leaked in: {rec['shares']}"
    assert rec["assets"] == 3.0e10, f"subsidiary assets leaked in: {rec['assets']}"
    assert rec["debt"] == 4.0e9, f"subsidiary debt leaked in: {rec['debt']}"
