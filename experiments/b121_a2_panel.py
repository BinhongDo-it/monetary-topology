"""B121 arm A2, part one: build the main window's panel and print the objects in it.

No criteria here. This part joins the three sources, prints what is in each column, and
writes the panel so the reading script in part two reads one file instead of three.

Sources, main window (2007-01-01 to 2008-08-08):
  data/raw/114040-V1.zip   the rival's own data (openICPSR 114040, Taylor and Williams),
                           sheet "Data for Figures & Regressions"
  data/raw/b121/*.csv      FRED, for the reconstruction check and the extension window

    python experiments/b121_a2_panel.py
"""

from __future__ import annotations

import csv
import datetime
import json
import statistics
import zipfile
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data" / "raw" / "114040-V1.zip"
FREDDIR = ROOT / "data" / "raw" / "b121"
OUT = ROOT / "results" / "b121_a2_panel.json"
SHEET = "Data for Figures & Regressions"
FIRST, LAST = "2007-01-01", "2008-08-08"

# What the publisher calls each column, copied from the workbook's own Notes sheet, so no
# column is read under a name this project invented for it (discipline 54).
COLS = {
    "FFT": "Target Federal Funds Rate",
    "FFE": "Effective Federal Funds Rate",
    "US0003M": "Three-Month US LIBOR",
    "USSOC": "Three-Month US OIS",
    "CD_3M": "Three-Month CD",
    "CDSMEDIAN2": "CDS Median (15 Banks)",
    "TAFBAL_FRB": "TAF Outstanding Balance - US",
    "TAFBAL_TOT": "TAF Outstanding Balance - Total",
    "RPGT03M": "Three-Month Repo",
    "GFED03M": "Three-Month Term Fed Funds",
    "TAFDUMMY": "TAF Dummy = 1 starting on 12/12/2007",
    "USTAFD": "TAF Dummy = 1 on TAF bid dates",
    "TAFSETTLE": "TAF Settlement Dummy",
    "TAFANNOUNCEFRBNY": "TAF Announcements Dummy",
}


def read_fred(sid: str) -> dict[str, float]:
    path = FREDDIR / f"{sid}.csv"
    if not path.exists():
        return {}
    rows = list(csv.reader(path.open(encoding="utf-8")))[1:]
    return {r[0]: float(r[1]) for r in rows if len(r) > 1 and r[1] not in ("", ".", "NA")}


def read_workbook() -> tuple[list[str], dict[str, dict[str, float]], dict]:
    book = xlrd.open_workbook(file_contents=zipfile.ZipFile(ZIP).read("TaylorWilliamsData.xls"))
    sheet = book.sheet_by_name(SHEET)
    head = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
    missing = [c for c in COLS if c not in head]
    if missing:
        raise SystemExit(f"the workbook does not carry {missing}; its columns are {head}")
    by_col: dict[str, dict[str, float]] = {c: {} for c in COLS}
    dates, unreadable = [], 0
    for r in range(1, sheet.nrows):
        try:
            day = datetime.datetime(*xlrd.xldate_as_tuple(sheet.cell_value(r, 0), book.datemode))
        except Exception:
            unreadable += 1
            continue
        d = day.date().isoformat()
        if not (FIRST <= d <= LAST):
            continue
        dates.append(d)
        for c in COLS:
            v = sheet.cell_value(r, head.index(c))
            if isinstance(v, float):
                by_col[c][d] = v
    return dates, by_col, {"rows_in_sheet": sheet.nrows - 1, "rows_without_a_date": unreadable}


def main() -> int:
    dates, col, sheet_facts = read_workbook()
    print(f"workbook: {sheet_facts['rows_in_sheet']} rows, "
          f"{sheet_facts['rows_without_a_date']} without a readable date, "
          f"{len(dates)} in {FIRST} to {LAST}, duplicates {len(dates) - len(set(dates))}")

    print("\nwhat each column carries in the window (the name is the publisher's own):")
    coverage = {}
    for c, name in COLS.items():
        v = [col[c][d] for d in dates if d in col[c]]
        coverage[c] = len(v)
        span = f"{min(v):9.4f} to {max(v):9.4f}" if v else "empty"
        print(f"  {c:<18} {len(v):>4}/{len(dates)}  {span}   {name}")

    # The spread, both timings. Taylor and Williams regress on libor(t) - ois(t-1), which their
    # own program writes as `newlibor3ois3`; the plain difference is kept beside it.
    both = [d for d in dates if d in col["US0003M"] and d in col["USSOC"]]
    spread = {d: col["US0003M"][d] - col["USSOC"][d] for d in both}
    lagged = {}
    for i, d in enumerate(dates):
        if i and d in col["US0003M"] and dates[i - 1] in col["USSOC"]:
            lagged[d] = col["US0003M"][d] - col["USSOC"][dates[i - 1]]
    pre = [v for d, v in spread.items() if d < "2007-08-09"]
    post = [v for d, v in spread.items() if d >= "2007-08-09"]
    print(f"\nLIBOR minus OIS, in basis points: {len(spread)} days, "
          f"before 2007-08-09 median {statistics.median(pre) * 100:.1f} over {len(pre)} days, "
          f"from 2007-08-09 median {statistics.median(post) * 100:.1f} over {len(post)} days, "
          f"highest {max(spread.values()) * 100:.1f} on {max(spread, key=spread.get)}")

    # Dose one: how much of the target rate has been taken away since the window's own peak.
    peak = max(col["FFT"].values())
    cuts = []
    for i, d in enumerate(dates):
        if i and d in col["FFT"] and dates[i - 1] in col["FFT"]:
            step = col["FFT"][d] - col["FFT"][dates[i - 1]]
            if abs(step) > 1e-9:
                cuts.append({"date": d, "step_pp": round(step, 4),
                             "target_after": round(col["FFT"][d], 4),
                             "spread_bp": round(spread[d] * 100, 1) if d in spread else None})
    print(f"\nrate steps in the window, from a peak of {peak:.2f} percent: {len(cuts)}")
    for c in cuts:
        print(f"  {c['date']}  {c['step_pp']:+.2f} to {c['target_after']:.2f}   "
              f"spread {c['spread_bp']} bp")

    # Dose two: the facility's own size, and the days its own dummies name.
    taf = col["TAFBAL_FRB"]
    live = {d: v for d, v in taf.items() if v > 0}
    bids = [d for d in dates if col["USTAFD"].get(d, 0) > 0]
    print(f"\nTAF balance (US): first positive {min(live) if live else 'never'}, "
          f"highest {max(taf.values()):.0f} on {max(taf, key=taf.get)}, "
          f"{len(live)} days above zero of {len(taf)}")
    print(f"TAF bid days named by the workbook's own dummy: {len(bids)}"
          + (f", first {bids[0]}, last {bids[-1]}" if bids else ""))

    # The reconstruction the extension window rests on, checked where both exist.
    ted, tb3 = read_fred("TEDRATE"), read_fred("DTB3")
    pairs = [(d, ted[d] + tb3[d], col["US0003M"][d])
             for d in dates if d in ted and d in tb3 and d in col["US0003M"]]
    if pairs:
        err = [abs(a - b) * 100 for _, a, b in pairs]
        print(f"\nTEDRATE + DTB3 against the workbook's US0003M: {len(pairs)} days, "
              f"median gap {statistics.median(err):.2f} bp, largest {max(err):.2f} bp")

    panel = []
    for d in dates:
        panel.append({
            "date": d,
            "fft": col["FFT"].get(d), "ffe": col["FFE"].get(d),
            "libor3m": col["US0003M"].get(d), "ois3m": col["USSOC"].get(d),
            "spread": round(spread[d], 6) if d in spread else None,
            "spread_lagged_ois": round(lagged[d], 6) if d in lagged else None,
            "taf_frb": col["TAFBAL_FRB"].get(d), "taf_tot": col["TAFBAL_TOT"].get(d),
            "cds_median": col["CDSMEDIAN2"].get(d), "repo3m": col["RPGT03M"].get(d),
            "term_ff3m": col["GFED03M"].get(d),
            "taf_bid_day": bool(col["USTAFD"].get(d, 0) > 0),
            "taf_settle_day": bool(col["TAFSETTLE"].get(d, 0) > 0),
            "taf_announce_day": bool(col["TAFANNOUNCEFRBNY"].get(d, 0) > 0),
        })

    record = {
        "stage": "B121",
        "diagnostic_only": True,
        "diagnostic_reason": "Part one of arm A2. It builds the panel and prints the objects in "
                             "it; no criterion is scored here and the station is not closed.",
        "config": {"window_first": FIRST, "window_last": LAST, "sheet": SHEET,
                   "source_zip": "data/raw/114040-V1.zip", "fred_dir": "data/raw/b121"},
        "source": {"main_window": "openICPSR 114040, replication data for Taylor and Williams, "
                                  "A Black Swan in the Money Market, AEJ: Macroeconomics 1(1)",
                   "column_names": COLS, "fred": ["TEDRATE", "DTB3"]},
        "coverage": coverage,
        "sheet_facts": sheet_facts,
        "spread_bp": {"days": len(spread),
                      "median_before_2007_08_09": round(statistics.median(pre) * 100, 2),
                      "median_from_2007_08_09": round(statistics.median(post) * 100, 2),
                      "highest": round(max(spread.values()) * 100, 2),
                      "highest_on": max(spread, key=spread.get)},
        "rate_steps": cuts,
        "taf": {"first_positive": min(live) if live else None,
                "highest": round(max(taf.values()), 3),
                "highest_on": max(taf, key=taf.get),
                "days_above_zero": len(live), "bid_days": len(bids), "bid_day_list": bids},
        "libor_reconstruction_check": {
            "days": len(pairs),
            "median_gap_bp": round(statistics.median(err), 4) if pairs else None,
            "largest_gap_bp": round(max(err), 4) if pairs else None},
        "panel": panel,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}  ({len(panel)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
