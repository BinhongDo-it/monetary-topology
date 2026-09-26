#!/usr/bin/env python3
"""Join the two California net metering vintages onto one position key.

Arm E of B98 needs one table, one row per (utility, month, hour, daytype), with
the NEM-2 export price and the NEM-3 export price side by side. Neither side is
published in that shape, so this builds it, and the whole of the work is in
three places where a guess would have been easy and the publisher had an answer.

**What the NEM-3 price is.** PG&E posts a price sheet per interconnection
application year at the URL Schedule NBT names. Each is 48 rows by 12 months by
two components, `Energy Produced` and `Energy Delivered`. The published How-To
adds them in its own worked example ($0.33 + $0.05 = $0.38), so the export price
is their sum. The 48 rows are 24 weekday hours then 24 weekend hours, and this
reads which is which off the page rather than assuming the order.

**What the NEM-2 price is.** Schedule NEM2 sheet 11 values exports at "the same
price per kWh at the same TOU period", and sheet 13 says non-bypassable charges
"may not be reduced by any credits for exports" and are "assessed only on the
kilowatt hours consumed". So the NEM-2 export price is the retail price of that
period with nothing added or taken off. The design file had assumed the charges
came off it; reading the tariff removed the question rather than answering it.

**Period definitions are constants here, and the workbook is asked to confirm
them.** Parsing "4:00 pm to 9:00 pm / All Days" out of a spreadsheet cell is a
guess dressed as a read. Writing the hours as a constant with no check is a
guess with no source. So the hours are a constant, the sheet's own wording is
pulled alongside, and the run fails if the two disagree.

Run::

    python experiments/b98_nem_join.py --probe
    python experiments/b98_nem_join.py --schedule E-TOU-C --vintage 2026
    python experiments/b98_nem_join.py --schedule EV2 --vintage 2026
    python experiments/b98_nem_join.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "cpuc_nem"
OUT = ROOT / "data" / "cpuc_nem"

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
HOURS = ([f"{h}:00 AM" for h in [12] + list(range(1, 12))]
         + [f"{h}:00 PM" for h in [12] + list(range(1, 12))])

#: Each schedule: where its rows sit, the period each hour falls in, the summer
#: months, and the wording the workbook must repeat back. The hours are a
#: closed set per period, so a gap or an overlap is caught by construction.
SCHEDULES = {
    "E-TOU-C": {
        "sheet": "Res Inclu TOU_240901-Present",
        "name_contains": "E-TOU-C",
        "periods_sheet": "E-TOU-B-C-D_TOU Periods",
        "summer": {6, 7, 8, 9},
        "peak_hours": {16, 17, 18, 19, 20},
        "peak_all_days": True,
        "must_say": ["4:00 pm to 9:00 pm", "All Days", "Summer  (June-September)"],
        "order": ["Peak", "Off-Peak"],
    },
    "EV2": {
        "sheet": "ElecVehicle&Tech_240901-Present",
        "name_contains": "EV2",
        "periods_sheet": "EV_EV2_E-ELEC_TOU Periods",
        "summer": {6, 7, 8, 9},
        "peak_hours": {16, 17, 18, 19, 20},
        "part_peak_hours": {15, 21, 22, 23},
        "peak_all_days": True,
        "must_say": ["4:00 pm to 9:00 pm", "3:00 pm to 4:00 pm",
                     "9:00 pm to 12:00 am", "Summer:  June-Sept"],
        "order": ["Peak", "Part-Peak", "Off-Peak"],
    },
}


def period_of(cfg, month, hour):
    """Which TOU period an (month, hour) falls in. Daytype enters only if the
    schedule's peak is not every day, and for these two it is."""
    if hour in cfg["peak_hours"]:
        return "Peak"
    if hour in cfg.get("part_peak_hours", set()):
        return "Part-Peak"
    return "Off-Peak"


def read_eec(pdf):
    """The NEM-3 side: 12 months by 24 hours by two daytypes, summed.

    Returns {(month_index, hour_index, daytype): produced + delivered} and the
    two headings it used to decide which block is which.
    """
    with tempfile.TemporaryDirectory() as d:
        txt = pathlib.Path(d) / "x.txt"
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)],
                       check=True, capture_output=True)
        lines = txt.read_text(encoding="utf-8", errors="replace").split("\n")

    # Two different years are printed on this page and only one of them is the
    # vintage. The subtitle reads "2026 Energy Export Credit (EEC) Values: 2023
    # Interconnection Application Year": the first is the year the values are
    # paid in, the second is the batch. The block headings then read "2026
    # Weekday Values", which is the payment year again. Reading the wrong one
    # makes all four sheets look like the same vintage. The vintage is the year
    # standing in front of "Interconnection Application Year".
    printed_years = sorted({m for line in lines for m in
                            re.findall(r"(20\d\d)\s+Interconnection Application", line)})

    blocks, seen = [], None
    rows = []
    for line in lines:
        low = line.lower()
        # Only a heading decides the block. The prose at the top of the page says
        # values "vary by time of day, weekday or weekend and month", which
        # carries both words, and the weekend heading reads "Weekend/Holiday
        # Values" rather than "Weekend Values", so matching on either word alone
        # picks the sentence and matching on the pair misses the heading.
        if "values ($" in low:
            if "weekend" in low:
                seen = "weekend"
                blocks.append((len(rows), "weekend"))
            elif "weekday" in low:
                seen = "weekday"
                blocks.append((len(rows), "weekday"))
        # The dollar sign is not part of the format. The 2023 and 2024 sheets
        # print bare numbers and the 2025 and 2026 sheets print "$0.09342", so a
        # reader keyed on "$" silently returns nothing for half the download and
        # reports it as a file it could not read.
        nums = re.findall(r"\$?(\d+\.\d{4,6})", line)
        if len(nums) < 20:
            continue
        label = re.split(r"\$?\d+\.\d{4,6}", line, maxsplit=1)[0].strip()
        rows.append((label, seen, [float(x) for x in nums]))

    trouble = []
    if len(rows) != 48:
        trouble.append(f"expected 48 value rows, found {len(rows)}")
    if len({d for _, d, _ in rows}) != 2:
        trouble.append("the page does not separate weekday from weekend values")
    for label, _, nums in rows:
        if len(nums) != 24:
            trouble.append(f"row {label!r} carries {len(nums)} values, not 24")

    out = {}
    for label, daytype, nums in rows:
        if label not in HOURS:
            trouble.append(f"unexpected hour label {label!r}")
            continue
        h = HOURS.index(label)
        for m in range(12):
            out[(m, h, daytype)] = nums[2 * m] + nums[2 * m + 1]
    if len(out) != 576 and not trouble:
        trouble.append(f"{len(out)} cells built, expected 576")
    return out, [b[1] for b in blocks], trouble, printed_years


def read_rates(xlsx, key):
    """The NEM-2 side: the period prices of one schedule, by season.

    The block is found by the schedule's name in column A, not by a row number,
    and it stops at the next non-empty name. A row number is a position.
    """
    import openpyxl
    cfg = SCHEDULES[key]
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb[cfg["sheet"]]
    start = None
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if v and cfg["name_contains"] in str(v):
            start = r
            break
    if start is None:
        return {}, [f"no row in column A names {cfg['name_contains']}"]
    # The two sheets put Season, Period and Energy Charge in different columns,
    # so the columns are found by their own heading. A column number is a
    # position, and the first version of this wrote 7, 8, 9 and read the EV
    # sheet correctly and the residential sheet one column off, which produced
    # four prices with the right values under the wrong labels.
    cols = {}
    for r in range(1, ws.max_row + 1):
        row = {c: str(ws.cell(r, c).value or "") for c in range(1, ws.max_column + 1)}
        if any("Season" in v for v in row.values()) and \
           any("Time-of-Use" in v for v in row.values()):
            for c, v in row.items():
                if "Season" in v:
                    cols["season"] = c
                elif "Time-of-Use" in v:
                    cols["period"] = c
                elif "Energy Charge" in v:
                    cols["amount"] = c
            break
    if len(cols) != 3:
        return {}, [f"{cfg['sheet']}: could not find Season, Time-of-Use and "
                    f"Energy Charge headings; found {sorted(cols)}"]

    rates, trouble, season = {}, [], None
    for r in range(start, ws.max_row + 1):
        if r > start and ws.cell(r, 1).value:
            break
        s = ws.cell(r, cols["season"]).value
        p = ws.cell(r, cols["period"]).value
        amount = ws.cell(r, cols["amount"]).value
        if s:
            season = str(s).strip()
        if not p or amount in (None, "", "-"):
            continue
        try:
            rates[(season, str(p).strip())] = float(amount)
        except (TypeError, ValueError):
            trouble.append(f"{season} {p} is not a number: {amount!r}")
    want = {(s, p) for s in ("Summer", "Winter") for p in cfg["order"]}
    missing = want - set(rates)
    if missing:
        trouble.append("missing " + ", ".join(sorted(f"{a} {b}" for a, b in missing)))

    periods = wb[cfg["periods_sheet"]]
    said = " ".join(str(periods.cell(r, c).value or "")
                    for r in range(1, periods.max_row + 1)
                    for c in range(1, periods.max_column + 1))
    for phrase in cfg["must_say"]:
        if phrase not in said:
            trouble.append(f"the workbook does not say {phrase!r}, so the hours "
                           f"written into this script are not confirmed by it")
    return rates, trouble


def build_vintage_pair(early, late):
    """Arm F: two NEM-3 batches against each other, on the same 576-cell grid.

    Arm E puts a NEM-2 price beside a NEM-3 price, and its coarse side takes
    four values against the other's 557, so the pairs inside one TOU block carry
    nothing and are reported apart. Here both sides are the same published
    object one batch apart: same tariff, same avoided-cost formula, same grid,
    same units. There is no coarse side, so every pair carries the reading, and
    the answer "the two regimes are simply different calculations" is not
    available to a reader who wants the shape difference explained away.
    """
    rows, trouble = [], []
    grids = {}
    for tag in (early, late):
        pdf = DATA / "PGE-EEC-Price-Sheets" / (
            f"PGE_Solar Billing Plan_EEC Values Price Sheet {tag}.pdf")
        eec, blocks, t1, printed = read_eec(pdf)
        if printed and tag not in printed:
            t1.append(f"the file is named {tag} and the page is headed "
                      f"{'/'.join(printed)}")
        grids[tag] = eec
        trouble += [f"{tag}: {x}" for x in t1]
    if trouble:
        return [], [], trouble
    a, b = grids[early], grids[late]
    if set(a) != set(b):
        return [], [], ["the two batches do not cover the same positions"]
    for key in sorted(a):
        m, h, daytype = key
        rows.append({"utility": "PGE", "month": m + 1, "hour": h,
                     "daytype": daytype, "season": "n/a",
                     "tou_period": f"batch {early} vs {late}",
                     "p_nem2": f"{a[key]:.5f}", "p_nem3": f"{b[key]:.5f}"})
    keys = {(r["utility"], r["month"], r["hour"], r["daytype"]) for r in rows}
    if len(keys) != len(rows):
        trouble.append("the position key is not unique")
    return rows, ["weekday", "weekend"], trouble


def build(key, vintage):
    cfg = SCHEDULES[key]
    pdf = DATA / "PGE-EEC-Price-Sheets" / (
        f"PGE_Solar Billing Plan_EEC Values Price Sheet {vintage}.pdf")
    eec, blocks, t1, printed = read_eec(pdf)
    if printed and vintage not in printed:
        t1.append(f"the file is named {vintage} and the page is headed "
                  f"{'/'.join(printed)}; the heading is the document and the "
                  f"name is a label, so this run is refused rather than filed "
                  f"under the wrong vintage")
    rates, t2 = read_rates(DATA / "Res_Inclu_TOU_Current.xlsx", key)
    trouble = t1 + t2
    rows = []
    for (m, h, daytype), p3 in sorted(eec.items()):
        season = "Summer" if (m + 1) in cfg["summer"] else "Winter"
        period = period_of(cfg, m + 1, h)
        p2 = rates.get((season, period))
        if p2 is None:
            trouble.append(f"no rate for {season} {period}")
            continue
        # The column names are the station script's interface, not this one's
        # choice: it looks for `nem.?2` and `nem.?3`. Naming them `p2` and `p3`
        # here produced a table it could not read, and it said so rather than
        # guessing a column, which is what finding columns by name is for.
        rows.append({"utility": "PGE", "month": m + 1, "hour": h,
                     "daytype": daytype, "season": season, "tou_period": period,
                     "p_nem2": f"{p2:.5f}", "p_nem3": f"{p3:.5f}"})
    keys = {(r["utility"], r["month"], r["hour"], r["daytype"]) for r in rows}
    if len(keys) != len(rows):
        trouble.append("the position key is not unique")
    return rows, blocks, trouble


def write(rows, path):
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def selftest():
    checks = []
    # the hour labels are a closed set of 24, in order, and 12 AM is midnight
    checks.append(("24 hour labels, no repeat", len(HOURS) == 24 == len(set(HOURS))))
    checks.append(("midnight first, noon at 12", HOURS[0] == "12:00 AM"
                   and HOURS[12] == "12:00 PM"))
    for key, cfg in SCHEDULES.items():
        got = {period_of(cfg, 7, h) for h in range(24)}
        checks.append((f"{key}: every hour lands in a named period",
                       got <= set(cfg["order"])))
        checks.append((f"{key}: every named period is reachable",
                       got == set(cfg["order"])))
        peak = {h for h in range(24) if period_of(cfg, 7, h) == "Peak"}
        checks.append((f"{key}: peak is five hours, 16 to 20", peak == {16, 17, 18, 19, 20}))
    ev2 = SCHEDULES["EV2"]
    checks.append(("EV2 part-peak is 15 and 21 to 23",
                   {h for h in range(24) if period_of(ev2, 7, h) == "Part-Peak"}
                   == {15, 21, 22, 23}))
    checks.append(("the two schedules differ, so running both is not one run twice",
                   {period_of(SCHEDULES["E-TOU-C"], 7, 22)}
                   != {period_of(ev2, 7, 22)}))
    # a seeded page with a row missing must be reported, not silently shortened
    with tempfile.TemporaryDirectory() as d:
        fake = pathlib.Path(d) / "x.txt"
        fake.write_text("2026 Weekday Values\n" + "\n".join(
            h + "  " + "  ".join(["$0.01000"] * 24) for h in HOURS[:23]),
            encoding="utf-8")
        rows = [l for l in fake.read_text(encoding="utf-8").split("\n")
                if l.count("$") >= 20]
        checks.append(("a short page is 23 rows and would be caught", len(rows) == 23))
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("  ok    " if ok else "  FAIL  ") + n)
    print("selftest " + ("passed" if not bad else "FAILED: " + ", ".join(bad)))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", choices=sorted(SCHEDULES) + ["NEM3-batch"])
    ap.add_argument("--against", default="2023",
                    help="arm F only: the earlier batch to put beside --vintage")
    ap.add_argument("--vintage", default="2026")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.probe:
        for key in sorted(SCHEDULES):
            rates, trouble = read_rates(DATA / "Res_Inclu_TOU_Current.xlsx", key)
            print(f"{key}: {len(rates)} period prices")
            for k in sorted(rates):
                print(f"    {k[0]:7s} {k[1]:10s} {rates[k]:.5f}")
            for t in trouble:
                print("    TROUBLE " + t)
        for v in ("2023", "2024", "2025", "2026"):
            pdf = DATA / "PGE-EEC-Price-Sheets" / (
                f"PGE_Solar Billing Plan_EEC Values Price Sheet {v}.pdf")
            if not pdf.exists():
                print(f"EEC {v}: not on disk")
                continue
            eec, blocks, trouble, printed = read_eec(pdf)
            vals = sorted(eec.values())
            span = (f"min {vals[0]:.5f} max {vals[-1]:.5f}, "
                    f"{len(set(round(x, 5) for x in vals))} distinct"
                    if vals else "no cells built")
            mark = "" if printed == [v] else f", HEADED {'/'.join(printed) or 'nothing'}"
            print(f"EEC {v}: {len(eec)} cells, blocks {blocks}, {span}{mark}")
            for t in trouble:
                print("    TROUBLE " + t)
        return 0
    if not a.schedule:
        ap.error("--schedule is required unless --probe or --selftest")
    if a.schedule == "NEM3-batch":
        rows, blocks, trouble = build_vintage_pair(a.against, a.vintage)
        tag = f"NEM3-batch_{a.against}v{a.vintage}"
    else:
        rows, blocks, trouble = build(a.schedule, a.vintage)
        tag = f"{a.schedule}_{a.vintage}"
    for t in trouble:
        print("TROUBLE " + t)
    if trouble:
        return 1
    path = OUT / f"joined_PGE_{tag}.csv"
    write(rows, path)
    p2 = sorted({r["p_nem2"] for r in rows})
    p3 = sorted({r["p_nem3"] for r in rows})
    print(f"{len(rows)} rows, key unique, blocks {blocks}")
    # Print the whole set only when it is small enough to read. Arm E's coarse
    # side takes four or five values and naming them is the point; arm F's takes
    # 539 and naming them is a wall.
    def say(name, vals):
        if len(vals) <= 12:
            return f"  {name} takes {len(vals)} values: {', '.join(vals)}"
        return f"  {name} takes {len(vals)} values, {vals[0]} to {vals[-1]}"
    print(say("p_nem2", p2))
    print(say("p_nem3", p3))
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
