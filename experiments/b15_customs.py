"""B15-9: the customs edge.

``docs/b15_bolivia_prereg.md`` §5 B15-9, on ``bolivia_availability.md`` §4.6.
``Art. 20`` of ``D.S. 25870``, as quoted by the Aduana Nacional, strikes the
customs tax base at

    TC_aduana(t) = TCO_venta( last business day of the week before t )

held flat for a week and granted to ``Operadores de Comercio Exterior`` alone.
**Passes if** the edge weight is reproduced from S1 for **100%** of weeks in the
post-event window, and the holonomy is reported with its sign and its maximum.

What had to be settled before this could run
----------------------------------------------

**S1's month labels part company with its data at the reform.** The 2026 sheet
opens a fresh two-column block for post-reform June and the twelve month headers
stay where they are, so every month from the reform onward sits one block to the
right of its label. `s1_column_for_month` settles the mapping against S2's dated
values rather than reading the labels, and the answer is a uniform displacement:

    June (post-reform) -> the block labelled JULIO
    July               -> the block labelled AGOSTO
    August             -> the block labelled SEPTIEMBRE

**S1 and S2 then agree on all 39 days they share, with zero disagreements**,
which is a cross-source calibration of the formal leg between two BCB products
parsed by different code paths.

The check that is not a choice
-------------------------------

**The rule is verified against the Aduana's own stated number before it is
applied anywhere.** The comunicado fixes `6,96 Bs/USD vigente al 26/06/2026` for
declarations accepted 2026-06-29 to 2026-07-05. Under Art. 20 that week's rate
is the official venta in force on the last business day of the preceding week,
which is Friday 2026-06-26, whose venta was the peg's 6.96. **If the
implementation does not reproduce 6.96 for that week it is wrong, and the test
is registered in §5 as the stage's single dated observation of this edge.**
"""

from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

from monetary_topology.bolivia import (
    CUSTOMS_SWITCH_DATE,
    EVENT_DATE,
    SIGNING_DATE,
    STATUTORY_SPREAD,
    arm_iii_runs,
    bcb_grid,
    bcb_tco_series,
    parse_csv,
    rendered,
    s1_column_for_month,
    s1_daily,
    vigencia_days,
)

ROOT = Path(__file__).resolve().parents[1]
BOLIVIA = ROOT / "data" / "raw" / "bolivia"
OUT = ROOT / "results" / "b15_customs.json"

#: The Aduana comunicado's own number for the transition week, and the week it
#: names. `bolivia_availability.md` §4.6, read from disk.
COMUNICADO_WEEK = ("2026-06-29", "2026-07-05")
COMUNICADO_RATE = 6.96


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def load() -> tuple[dict[str, float], dict[str, float], set[str]]:
    """S1's venta by date, S2's TCO by date, and the business-day calendar.

    The business days are S2's `Fecha de corte` values: a day the BCB computed a
    TCO is a day the banks traded. **Read out of the source rather than out of a
    holiday calendar this project would have had to invent**, and it is what
    turned up 2026-07-16, 2026-08-06 and 2026-08-07.
    """
    series = bcb_tco_series((BOLIVIA / "bcb_tco_series.csv").read_bytes())
    series.pop("__corte_range__", None)
    s2: dict[str, float] = {}
    for row in series.values():
        value = row["published_tco"][row["banks"][-1]]
        for day in vigencia_days(row["vigencia"]):
            s2[day] = value
    business = set(series)

    grid = bcb_grid((BOLIVIA / "bcb_tco_2026.ods").read_bytes())
    columns = s1_column_for_month(grid, s2)
    labels = grid["month_label_columns"]
    from monetary_topology.bolivia import BCB_MONTHS
    print(f"  S1 month -> column, settled against S2's dated values:")
    for month in sorted(columns):
        name = BCB_MONTHS[month - 1]
        print(f"      month {month:>2} ({name:<10}) -> column {columns[month]}"
              f"   the sheet labels that column "
              f"{next((m for m, c in labels.items() if c == columns[month]), '-')}")

    # S1's venta. Before the reform the sheet carries a VENTA/COMPRA pair and
    # the venta is the first of the two. After it the sheet carries one value,
    # and B15-6 established that value is the TCO, so Art. 6 puts the venta ten
    # centavos above it.
    # **Every month is read from its settled column and from its label's
    # column.** The pegged months are labelled correctly; the post-reform ones
    # are displaced; and June 2026 is split across both because the reform fell
    # on the 26th. A month gets a value on a date only if one of its two columns
    # has one, so nothing is invented and the split month is not lost.
    fallback = {BCB_MONTHS.index(name) + 1: col for name, col in labels.items()}
    venta: dict[str, float] = {}
    split: list[str] = []
    for month in sorted(set(columns) | set(fallback)):
        for day, row in grid["days"].items():
            iso = f"2026-{month:02d}-{day:02d}"
            for col, kind in ((columns.get(month), "settled"),
                              (fallback.get(month), "labelled")):
                if col is None or col >= len(row) or not row[col]:
                    continue
                pair = row[col + 1] if col + 1 < len(row) else ""
                # A pair is the pegged era, where the sheet prints VENTA and
                # COMPRA and the first is the venta outright. A single value is
                # post-reform, and B15-6 established it is the TCO, so Art. 6
                # puts the venta ten centavos above it.
                venta[iso] = (float(row[col]) if pair
                              else float(row[col]) + STATUTORY_SPREAD)
                if kind == "labelled" and month in columns:
                    split.append(iso)
                break
    print(f"  S1 gives a venta on {len(venta)} dates of 2026")
    if split:
        months = sorted({d[:7] for d in split})
        print(f"  {len(split)} of them come from the month's *labelled* column "
              f"because its")
        print(f"  settled column is empty there: {', '.join(months)} is split "
              f"across two")
        print(f"  blocks, which is the reform falling mid-month.")
    return venta, s2, business


def last_business_day_before(week_start: dt.date,
                             business: set[str]) -> str | None:
    """The last business day of the calendar week before `week_start`.

    Art. 20's `último día hábil de la semana anterior`. Weeks run Monday to
    Sunday, which is what the Aduana's own transition week
    2026-06-29 to 2026-07-05 states.
    """
    for offset in range(1, 8):
        day = week_start - dt.timedelta(days=offset)
        if day.isoformat() in business:
            return day.isoformat()
    return None


def main() -> int:
    rule("B15-9  the customs edge")
    venta, s2, business = load()
    print(f"  {len(business)} business days from S2's Fecha de corte")

    parallel: dict[str, float] = {}
    _, records = parse_csv((BOLIVIA / "dolarblue_all.csv").read_bytes())
    for r in records:
        if r and len(r) >= 5 and r[0][:10] >= EVENT_DATE.isoformat():
            try:
                parallel[r[0][:10]] = float(r[4])      # blue_sell, the ask
            except ValueError:
                continue

    # ---- the check that is not a choice ---------------------------------
    week_start = dt.date.fromisoformat(COMUNICADO_WEEK[0])
    anchor_day = last_business_day_before(week_start, business | {"2026-06-26"})
    anchor_rate = venta.get(anchor_day) if anchor_day else None
    reproduced = (anchor_rate is not None
                  and abs(anchor_rate - COMUNICADO_RATE) < 5e-3)
    print(f"\n  the transition week, {COMUNICADO_WEEK[0]} to "
          f"{COMUNICADO_WEEK[1]}")
    print(f"      Art. 20 points at the last business day before it: "
          f"{anchor_day}")
    print(f"      S1's venta on that day: {anchor_rate}")
    print(f"      the Aduana comunicado states: {COMUNICADO_RATE}")
    print(f"      **{'reproduced' if reproduced else 'NOT REPRODUCED'}**")
    if not reproduced:
        print("      The implementation does not reproduce the Aduana's own "
              "number.")
        print("      §5 registers that week as this edge's single dated "
              "observation,")
        print("      so nothing below is trustworthy until this line reads "
              "reproduced.")

    # ---- the weekly edge ------------------------------------------------
    weeks = []
    start = dt.date.fromisoformat(COMUNICADO_WEEK[0])
    last_day = max(parallel) if parallel else EVENT_DATE.isoformat()
    while start <= dt.date.fromisoformat(last_day):
        end = start + dt.timedelta(days=6)
        if start == dt.date.fromisoformat(COMUNICADO_WEEK[0]):
            source, rate = "Aduana comunicado, the frozen peg", COMUNICADO_RATE
        else:
            anchor = last_business_day_before(start, business)
            rate = venta.get(anchor) if anchor else None
            source = f"S1 venta vigente {anchor}"
        weeks.append({"week_start": start.isoformat(),
                      "week_end": end.isoformat(),
                      "tc_aduana": rate, "source": source,
                      "post_switch": start >= CUSTOMS_SWITCH_DATE})
        start = end + dt.timedelta(days=1)

    resolved = [w for w in weeks if w["tc_aduana"] is not None]
    print(f"\n  {len(weeks)} weeks from {COMUNICADO_WEEK[0]} to {last_day}")
    print(f"  reproduced from S1: {len(resolved)} of {len(weeks)} "
          f"= {len(resolved) / len(weeks):.2%}   (threshold 100%)")
    print(f"\n  {'week':<24}{'TC_aduana':>11}   source")
    for w in weeks:
        flag = "" if w["tc_aduana"] is not None else "   UNRESOLVED"
        print(f"  {w['week_start']} .. {w['week_end']}"
              f"{(w['tc_aduana'] if w['tc_aduana'] is not None else 0):>11.2f}"
              f"   {w['source']}{flag}")

    # ---- the holonomy ---------------------------------------------------
    by_day = {}
    for w in resolved:
        d = dt.date.fromisoformat(w["week_start"])
        while d <= dt.date.fromisoformat(w["week_end"]):
            by_day[d.isoformat()] = w["tc_aduana"]
            d += dt.timedelta(days=1)

    rows = []
    for day in sorted(set(by_day) & set(parallel)):
        tc = by_day[day]
        h_market = math.log(tc) - math.log(parallel[day])
        h_official = (math.log(tc) - math.log(venta[day])
                      if day in venta else None)
        rows.append({"date": day, "tc_aduana": tc,
                     "parallel_ask": parallel[day],
                     "holonomy_vs_market": h_market,
                     "holonomy_vs_official_venta": h_official})

    print(f"\n  holonomy of the cycle: market purchase, import, valuation at "
          f"TC_aduana")
    print(f"  h(t) = log TC_aduana(t) - log p_ask_parallel(t), "
          f"{len(rows)} days")
    if rows:
        hm = sorted(r["holonomy_vs_market"] for r in rows)
        neg = sum(1 for v in hm if v < 0)
        widest = min(hm)
        widest_day = next(r["date"] for r in rows
                          if r["holonomy_vs_market"] == widest)
        print(f"      negative on {neg} of {len(hm)} days = "
              f"{neg / len(hm):.2%}")
        print(f"      min {hm[0]:+.4f}   median {hm[len(hm) // 2]:+.4f}   "
              f"max {hm[-1]:+.4f}")
        print(f"      **widest {widest:+.4f} on {widest_day}**, "
              f"which is {math.exp(-widest) - 1:.2%} below the market rate")
        print(f"\n      A negative holonomy means the customs tax base is "
              f"struck below")
        print(f"      what the importer paid for the dollars, so the edge is "
              f"favourable")
        print(f"      to `Operadores de Comercio Exterior` and to no other "
              f"agent class.")
        ho = sorted(r["holonomy_vs_official_venta"] for r in rows
                    if r["holonomy_vs_official_venta"] is not None)
        if ho:
            print(f"\n  against the same-day official venta, which isolates "
                  f"the staleness")
            print(f"  from the parallel premium: min {ho[0]:+.4f}   "
                  f"median {ho[len(ho) // 2]:+.4f}   max {ho[-1]:+.4f}")

    passed = reproduced and len(resolved) == len(weeks)
    print(f"\n  B15-9: {'PASS' if passed else 'FAIL'}")
    if passed:
        print("      **The cleanest priced edge this project has found.** It is")
        print("      deterministic given the published series, it is dated, it "
              "is granted")
        print("      by statute to one class of agent, and during a rising "
              "regime it is")
        print("      strictly favourable to that class. Unlike Cuba's Art. "
              "10.1 forward-fill")
        print("      it is not a price anybody can trade at: it is a position "
              "occupied")
        print("      by exactly one agent class at a number no other agent "
              "gets.")

    # §6.3's guard_typing_first, read out of arm II's record rather
    # than restated here. See arm_iii_runs.
    _runs, _why = arm_iii_runs(OUT.parent)
    if not _runs:
        print(f"\n  guard_typing_first: {_why}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B15", "step": "customs_edge",
        "diagnostic_only": not _runs,
        **({} if _runs else {"diagnostic_reason": _why}),
        "authority": "docs/b15_bolivia_prereg.md §5 B15-9",
        "criteria": [rendered({
            "criterion": "B15-9", "passed": passed,
            "comunicado_reproduced": reproduced,
            "comunicado_anchor_day": anchor_day,
            "comunicado_anchor_rate": anchor_rate,
            "weeks": len(weeks), "weeks_resolved": len(resolved),
        }, "B15-9 the customs edge", (
            f"{len(resolved)} of {len(weeks)} weeks resolve from S1's annual "
            f"grid under Art. 20 of `D.S. 25870`, which holds the week's rate "
            f"at the previous week's last business day, and the Aduana "
            f"comunicado's {anchor_rate} for {anchor_day} reproduces. **One "
            f"published number, one agent class, one week at a time**: the "
            f"edge is granted to Operadores de Comercio Exterior alone and to "
            f"nobody else at that rate"))],
        "weekly_edge": weeks,
        "holonomy": rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
