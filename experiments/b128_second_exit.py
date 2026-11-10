"""B128: the second exit from zero, read against a threshold and a lag fixed by the first round.

The registration (design, "第二轮离开零") first compared the level at which a country's household overnight deposit
rate leaves zero the second time with L_up, the deposit facility rate in the month it left the first time. That level
is not the threshold: with a repricing lag the rate keeps rising while the deposit rate waits to follow, so the first
exit is read at a policy rate above the one that set it off. A model whose threshold and lag never move (the rate is
off the zero line in month t exactly when DFR(t - L) > T) leaves zero the first time at 3.75 and the second time at
2.50 on the path the ECB actually took and a pause at 2.50, and L_up would read that as a threshold moving down by
1.25 when it moved by nothing (independent audit, 2026-09-28).

So the two branches are read against the fixed model itself:

  first round   for each country that went off the line in the 2022-23 hikes and back on it in the 2024-26 cuts,
                and for each lag L of 0 to 12 months, the thresholds T that agree with every month's state from
                2022-06 to 2026-05 (off when above the line, on when at or below it). The pairs (L, T) that agree
                everywhere are the fixed model's feasible set; a country with none is printed as not fitted. MIR
                sits on a 0.01 grid and the design takes the tick as the floor, so a month within one tick of the
                line is unread: the countries that went back sit on the line and step by one tick (BE, FR at 0.05
                and 0.06), and counted as on or off by a single tick they leave few or no fixed pairs (NL none).
                The lags that fit with only the months exactly on the line left out are printed beside them
  second round  for every pair in the set, the month the fixed model says the rate leaves the line again, from the
                policy path as published by the read date; an exit is a month more than one tick above the line.
                Earlier than every such month: the threshold moved down.
                Later than every one, or still on the line when every pair has it off: moved up. Inside the range:
                consistent with a fixed threshold. Before the earliest month has come: not yet readable

The registration run reads rates up to 2026-05 only: the months after are the second round and are not read until the
read dates in the design. Lines 0.05 and 0.10 as in R6.

    python experiments/b128_second_exit.py              # register: the feasible sets, rates read to 2026-05
    python experiments/b128_second_exit.py --read       # read the second round (from 2027-03-15)
    python experiments/b128_second_exit.py --selftest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import b128_a_rate_dose as base
import b128_floor_return as fr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b128_second_exit.json"
FIT = ("2022-06", "2026-05")            # the first round: off in the hikes, back on in the cuts
LAGS = range(0, 13)
TICK = 0.01                             # MIR sits on a 0.01 grid (B97); a month within one tick of the line is unread
LINES = fr.LINES

STATE_MAP = {"observed exit before every pair's month": "threshold moved down",
             "observed exit after every pair's month, or on the line when every pair is off": "threshold moved up",
             "observed exit inside the pairs' months": "consistent with a fixed threshold and lag",
             "no exit yet and some pair not yet due": "not yet readable",
             "no feasible pair in the first round": "the fixed model does not fit this country's first round"}


def dfr_levels(until: str) -> dict[str, float]:
    """Month-end deposit facility rate from its dated levels, the rule B128-10 uses, to `until` (past 2026 at the read)."""
    import csv
    lev = {}
    with open(ROOT / "data" / "raw" / "b128" / "fm_keyrates.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["KEY"] == "FM.B.U2.EUR.4F.KR.DFR.LEV" and r["OBS_VALUE"]:
                lev[r["TIME_PERIOD"]] = float(r["OBS_VALUE"])
    days, out, cur, i = sorted(lev), {}, None, 0
    for m in base.months("1999-01", until):
        while i < len(days) and days[i][:7] <= m:
            cur, i = lev[days[i]], i + 1
        out[m] = cur
    return out


def shift(m: str, k: int) -> str:
    y, mo = int(m[:4]), int(m[5:7]) - k
    while mo < 1:
        y, mo = y - 1, mo + 12
    return f"{y:04d}-{mo:02d}"


def feasible(series: dict[str, float], dfr: dict[str, float], line: float, span=FIT, band: float = TICK) -> list[dict]:
    """(L, [T_low, T_high)) such that DFR(t - L) > T exactly in the months where the rate is above the line, over the
    months more than `band` from the line (the design's floor is the grid tick, not the printed digits)."""
    out = []
    months = [m for m in base.months(*span) if m in series and abs(series[m] - line) > band + 1e-9]
    for L in LAGS:
        on = [dfr[shift(m, L)] for m in months if series[m] <= line]
        off = [dfr[shift(m, L)] for m in months if series[m] > line]
        lo = max(on) if on else float("-inf")
        hi = min(off) if off else float("inf")
        if lo < hi:
            out.append({"lag": L, "t_low": lo, "t_high": hi})
    return out


def exit_month(dfr: dict[str, float], lag: int, t: float, after: str, until: str) -> str | None:
    """The first month after `after` in which the fixed model is off the line: DFR(month - lag) > t."""
    for m in base.months(shift(after, -1), until):
        if dfr.get(shift(m, lag)) is not None and dfr[shift(m, lag)] > t:
            return m
    return None


def predict(pairs: list[dict], dfr: dict[str, float], after: str, until: str) -> list[dict]:
    """Earliest and latest predicted second exit per pair (T at the low end, T just under the high end)."""
    rows = []
    for p in pairs:
        early = exit_month(dfr, p["lag"], p["t_low"], after, until)
        late = exit_month(dfr, p["lag"], p["t_high"] - 1e-9, after, until)
        rows.append({**p, "earliest": early, "latest": late})
    return rows


def classify(observed: str | None, preds: list[dict], until: str) -> str:
    if not preds:
        return "the fixed model does not fit this country's first round"
    earliest = min((p["earliest"] for p in preds if p["earliest"]), default=None)
    if observed is not None:
        if earliest is None or observed < earliest:
            return "threshold moved down"
        if all(p["latest"] is not None and observed > p["latest"] for p in preds):
            return "threshold moved up"
        return "consistent with a fixed threshold and lag"
    if all(p["latest"] is not None and p["latest"] <= until for p in preds):
        return "threshold moved up"
    return "not yet readable"


def second_exit(series: dict[str, float], line: float, after: str, until: str, band: float = TICK) -> str | None:
    """The first month after `after` more than one tick above the line."""
    return next((m for m in base.months(shift(after, -1), until) if m in series and series[m] > line + band + 1e-9), None)


def build(series_all, dfr, read: bool, until: str) -> dict:
    reads, crit_rows = [], []
    for line in LINES:
        r6 = fr.classify({a: {m: v for m, v in s.items() if m <= FIT[1]} for a, s in series_all.items()}, dfr, line)
        returners = [x["country"] for x in r6["rows"] if x["returns"]]
        rows = []
        for a in returners:
            s = series_all[a]
            first = {m: v for m, v in s.items() if m <= FIT[1]}
            pairs = feasible(first, dfr, line)
            row = {"country": a, "line": line, "left_zero": next(x for x in r6["rows"] if x["country"] == a)["left_zero"],
                   "returned": next(x for x in r6["rows"] if x["country"] == a)["returned"], "pairs": pairs,
                   "lags": [p["lag"] for p in pairs],
                   "months_read": sum(abs(v - line) > TICK + 1e-9 for m, v in first.items() if FIT[0] <= m <= FIT[1]),
                   "lags_only_on_line_months_out": [p["lag"] for p in feasible(first, dfr, line, band=0.0)]}
            if read:
                preds = predict(pairs, dfr, FIT[1], until)
                obs = second_exit(s, line, FIT[1], until)
                row.update({"predicted": preds, "observed_exit": obs, "state": classify(obs, preds, until)})
            rows.append(row)
        reads.append({"line": line, "rows": rows})
        crit_rows += rows
    fitted = sum(bool(r["pairs"]) for r in crit_rows)
    crit = [{"name": "B128-16", "kind": "own_reading",
             "statement": "the second exit from zero of each country that went back to zero in the 2024-26 cuts, read against "
                          "the dates a threshold and a lag fixed by its first round give for the policy path as published",
             "passed": None, "state": "registered, second round not read" if not read else "read", "state_map": STATE_MAP,
             "detail": "; ".join(f"line {r['line']} {r['country']}: lags {r['lags'] or 'none'}"
                                 + (f", {r['state']}" if read else "") for r in crit_rows)
                       + f"; {fitted} of {len(crit_rows)} fitted by the fixed model"}]
    rec = {"stage": "B128", "reading": "second exit from zero against a fixed threshold and lag", "reads": reads,
           "criteria": crit,
           "config": {"product": fr.PRODUCT, "fit": FIT, "lags": [LAGS.start, LAGS.stop - 1], "lines": LINES, "tick": TICK,
                      "rates_read_to": until, "dfr": "month-end level, FM.B.U2.EUR.4F.KR.DFR.LEV"},
           "source": {"rates": "data/raw/b128/mir_B_L21_A_R_A_2250_EUR_N.csv", "dfr": "data/raw/b128/fm_keyrates.csv"}}
    if not read:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = "Registration: the second round is read from 2027-03-15 (design, read dates)."
    return rec


def selftest() -> None:
    real = dfr_levels("2026-09")
    assert real == {m: v for m, v in fr.dfr_by_month().items() if m <= "2026-09"}, "the month-end rule must be B128-10's"
    path = dict(real)
    for m in base.months("2026-10", "2028-06"):          # an instrument scenario, not a forecast: a pause at 2.50,
        path[m] = 2.50 if m < "2027-06" else 3.00 if m < "2027-09" else 3.50   # then two hikes
    ms = base.months("2021-01", "2028-06")
    until = "2028-06"

    def model(t_before: float, t_after: float, switch: str, lag: int = 6, k: float = 0.25) -> dict[str, float]:
        return {m: max(0.0, k * (path[shift(m, lag)] - (t_before if m < switch else t_after))) for m in ms}

    # the audit's fixed model: threshold 2.25, pass-through 0.25, six months' lag, never moving
    fixed = model(2.25, 2.25, "2099-01")
    first_off = next(m for m in base.months("2022-06", "2023-12") if fixed[m] > 0.05)
    back_on = next(m for m in base.months("2024-06", "2026-05") if fixed[m] <= 0.05)
    assert (first_off, path[first_off], back_on) == ("2023-08", 3.75, "2025-10"), (first_off, path[first_off], back_on)
    pairs = feasible(fixed, path, 0.05)
    assert 6 in [p["lag"] for p in pairs], pairs
    obs = second_exit(fixed, 0.05, FIT[1], until)
    assert obs == "2027-03" and path[obs] == 2.50, obs
    assert classify(obs, predict(pairs, path, FIT[1], until), until) == "consistent with a fixed threshold and lag"
    # the level rule it replaces reads the same fixed model as a threshold moved down by 1.25
    assert path[obs] < path[first_off]

    # a rate that sits on the line and moves by one tick after its return: those months are unread, the fit stands;
    # read to the printed digit, the same series has no fixed pair
    hover = dict(fixed)
    for m in ("2025-11", "2026-01", "2026-03"):
        hover[m] = 0.06
    assert 6 in [p["lag"] for p in feasible(hover, path, 0.05)]
    assert feasible(hover, path, 0.05, band=0.0) == []
    # a threshold that does move once the first round is over: down, and up
    down = model(2.25, 1.25, "2026-06")
    assert classify(second_exit(down, 0.05, FIT[1], until), predict(feasible(down, path, 0.05), path, FIT[1], until),
                    until) == "threshold moved down"
    up = model(2.25, 4.00, "2026-06")
    assert second_exit(up, 0.05, FIT[1], until) is None
    assert classify(None, predict(feasible(up, path, 0.05), path, FIT[1], until), until) == "threshold moved up"
    # the mapping, cell by cell, on a range of predicted months that has width
    wide = [{"lag": 3, "t_low": 2.0, "t_high": 2.5, "earliest": "2027-01", "latest": "2027-04"},
            {"lag": 6, "t_low": 2.0, "t_high": 2.5, "earliest": "2027-03", "latest": "2027-06"}]
    for seen, want in (("2026-12", "threshold moved down"), ("2027-01", "consistent with a fixed threshold and lag"),
                       ("2027-05", "consistent with a fixed threshold and lag"), ("2027-06", "consistent with a fixed threshold and lag"),
                       ("2027-07", "threshold moved up"), (None, "threshold moved up")):
        assert classify(seen, wide, "2027-12") == want, (seen, classify(seen, wide, "2027-12"))
    assert classify(None, wide, "2027-05") == "not yet readable"
    # before the fixed model's months have come, nothing is read
    assert classify(None, predict(pairs, path, FIT[1], "2026-12"), "2026-12") == "not yet readable"
    # a first round no fixed pair fits: off, on, off again with the policy rate only rising
    flicker = {m: (0.1 if m in ("2022-10", "2023-04") else 0.0) for m in ms}
    assert feasible(flicker, path, 0.05) == []
    assert classify(None, [], until) == "the fixed model does not fit this country's first round"
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--read", action="store_true", help="read the second round (from 2027-03-15)")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    data = base.load_rates()
    series = {k: s for (k, p), s in data.items() if p == fr.PRODUCT and k in base.JOINED and k not in fr.OUT_OF_TEST}
    if not a.read:
        series = {k: {m: v for m, v in s.items() if m <= FIT[1]} for k, s in series.items()}   # second round unread
    until = max(max(s) for s in series.values())
    out = build(series, dfr_levels(until), a.read, until)
    for r in out["reads"]:
        print(f"== line {r['line']}")
        for x in r["rows"]:
            spans = ", ".join(f"L={p['lag']} T in [{p['t_low']:.2f}, {p['t_high']:.2f})" for p in x["pairs"]) or "none"
            print(f"   {x['country']}: left {x['left_zero']}, back {x['returned']}; {x['months_read']} months more than a tick from "
                  f"the line; fixed pairs: {spans}; with only the months exactly on the line left out: lags {x['lags_only_on_line_months_out'] or 'none'}"
                  + (f"; observed {x['observed_exit']} -> {x['state']}" if a.read else ""))
    c = out["criteria"][0]
    print(f"{c['name']} [{c['kind']}] {c['state']}: {c['detail']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
