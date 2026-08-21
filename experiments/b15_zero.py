"""B15-6: the formal leg's zero calibration.

``docs/b15_bolivia_prereg.md`` §5 B15-6. Recompute

    TCO_t = sum(TC_it * M_it) / sum(M_it)

from S2's microdata and compare against the published value. **Passes if** the
recomputation equals the published value to the published precision on **>= 99%**
of the days S2 covers.

**Anexo II §4 fixes the precision and the statute is what fixes it**: `el valor
será redondeado al segundo decimal para su publicación`. §7.1 registered "the
published value being rounded to a coarser precision than the recomputation" as
one of three things to rule out before a disagreement could be called a finding.
It is not a hypothesis any more; the comparison is at two decimals because the
instrument says so.

**Fifteen comparisons a day, not one.** The BCB's page prints each bank's own
weighted average beside the aggregate, so each day yields fourteen per-bank
checks and one aggregate check. A per-bank match with an aggregate mismatch and
a uniform mismatch are different failures and this file separates them.

Why a failure here would be the stage's best result
-----------------------------------------------------

§7.1: *if the published TCO is not what Anexo II says it is, that is the most
interesting single result this stage could return.* And `RD 88/2026` Art. 7
names the mechanism by which that could happen and attaches a penalty to it:
`el suministro de información falsa o la omisión selectiva de operaciones será
sancionado`. **The statute polices selective omission, which is exactly what a
recomputation from the same microdata cannot detect and what a recomputation
against a differently-sourced total can.**

So the three exclusions §7.1 registers are checked before any disagreement is
reported as a finding: tier buckets rounding differently from the underlying
operations, the 17:00 cutoff excluding operations the page still lists, and the
publication precision.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from monetary_topology.bolivia import (
    GuardFailed,
    SIGNING_DATE,
    TCO_RECOMPUTE_SHARE,
    anexo_ii,
    arm_iii_runs,
    bcb_tco_series,
    echoed_date,
    rendered,
)

ROOT = Path(__file__).resolve().parents[1]
BOLIVIA = ROOT / "data" / "raw" / "bolivia"
OUT = ROOT / "results" / "b15_zero.json"

TOTAL_MARKER = "TOTAL"


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def html_fallbacks() -> dict[str, str]:
    """Which stored detail pages are showing a day other than the one asked for.

    **Reported because it already cost a wrong result.** The first run of B15-6
    read the 55 stored pages, saw a grid on every one, and returned 55 of 55.
    Twenty-one of those pages were byte-identical to the endpoint's default:
    `?fecha=` on a day with no operations returns HTTP 200 and **another day's
    grid**, not an empty one. The page states which day it is showing in its
    date input and that was not read.
    """
    out: dict[str, str] = {}
    for path in sorted(BOLIVIA.glob("bcb_tco_detail_*.html")):
        day = path.stem.replace("bcb_tco_detail_", "")
        echoed = echoed_date(path.read_bytes())
        if echoed and echoed != day:
            out[day] = echoed
    return out


def main() -> int:
    path = BOLIVIA / "bcb_tco_series.csv"
    if not path.exists():
        raise SystemExit(
            f"no {path.name} under {BOLIVIA}. "
            f"Run data/fetch_bolivia.py --pass s2")
    series = bcb_tco_series(path.read_bytes())
    corte_range = series.pop("__corte_range__", None)

    rule("B15-6  the published TCO is the statute's weighted average")
    print(f"  source: {path.name}, one request, the whole range")
    print(f"  {len(series)} cutoff dates, {min(series)} .. {max(series)}")
    if corte_range:
        print(f"  the file states its own range: fecha de corte "
              f"{corte_range[0]} .. {corte_range[1]}")
    print(f"  the file states both dates per row: `Fecha de corte` is the day")
    print(f"  the operations happened, `Vigencia` is the day the TCO governs.")

    fallbacks = html_fallbacks()
    if fallbacks:
        print(f"\n  **{len(fallbacks)} of the stored daily HTML pages show a "
              f"different day.**")
        print(f"  `?fecha=` on a day with no operations returns 200 and the")
        print(f"  endpoint's default grid, not an empty one. Those pages are not")
        print(f"  observations of the day requested and B15-6 does not read")
        print(f"  them. Listed by requested date -> date the page actually "
              f"shows:")
        for day in sorted(fallbacks):
            weekday = dt.date.fromisoformat(day).strftime("%a")
            print(f"      {day} {weekday} -> {fallbacks[day]}")
        # **A weekday that falls back is not automatically a holiday.** The
        # source states its own last cutoff date, and a request past it asks
        # for a day whose 20:00 publication has not happened yet. Counting
        # that as a holiday would invent one.
        last_corte = corte_range[1] if corte_range else max(series)
        weekdays = sorted(d for d in fallbacks
                          if dt.date.fromisoformat(d).weekday() < 5)
        holidays = [d for d in weekdays if d <= last_corte]
        unpublished = [d for d in weekdays if d > last_corte]
        print(f"\n  of those, {len(weekdays)} fall on a weekday, and the two "
              f"reasons are different:")
        if holidays:
            print(f"      {len(holidays)} inside the source's range, so the "
                  f"BCB computed no TCO: {', '.join(holidays)}")
            print(f"      **The holiday calendar is read out of the endpoint "
                  f"rather than out of")
            print(f"      one this project would otherwise have had to "
                  f"invent.**")
        if unpublished:
            print(f"      {len(unpublished)} past the source's last cutoff "
                  f"({last_corte}), so not")
            print(f"      a holiday at all: {', '.join(unpublished)}. Art. "
                  f"5.III publishes at 20:00,")
            print(f"      and the fetch ran before that day's publication. "
                  f"**Absence here is")
            print(f"      the clock and not the calendar.**")

    without = sorted(fallbacks)
    rows = []
    agg_hits = bank_hits = bank_total = 0
    for day in sorted(series):
        detail = series[day]
        banks = [b for b in detail["banks"] if TOTAL_MARKER not in b.upper()]
        recomputed = anexo_ii(detail["tiers"], banks)
        published = detail["published_tco"].get(detail["banks"][-1])
        if recomputed is None or published is None:
            continue
        agg_ok = round(recomputed, 2) == published
        agg_hits += agg_ok
        per_bank = []
        for b in banks:
            tiers_b = [(r, {b: c[b]}) for r, c in detail["tiers"] if b in c]
            got = anexo_ii(tiers_b, [b])
            want = detail["published_tco"].get(b)
            if got is None or want is None:
                continue
            ok = round(got, 2) == want
            bank_hits += ok
            bank_total += 1
            if not ok:
                per_bank.append((b, round(got, 4), want))
        rows.append({"date": day, "vigencia": detail.get("vigencia"),
                     "recomputed": recomputed,
                     "published": published, "aggregate_ok": agg_ok,
                     "bank_mismatches": per_bank,
                     "banks": len(banks), "tiers": len(detail["tiers"])})
        if not agg_ok or per_bank:
            print(f"\n  {day}  recomputed {recomputed:.4f} -> "
                  f"{round(recomputed, 2)}   published {published}"
                  f"   {'aggregate ok' if agg_ok else 'AGGREGATE DIFFERS'}")
            for b, got, want in per_bank:
                print(f"      {b}: recomputed {got} published {want}")

    n = len(rows)
    if not n:
        print("\n  no day carried both a recomputation and a published value")
        return 1
    share = agg_hits / n
    bank_share = bank_hits / max(1, bank_total)
    print(f"\n  aggregate: {agg_hits} of {n} days match at two decimals "
          f"= {share:.4%}")
    print(f"  per bank:  {bank_hits} of {bank_total} bank-days "
          f"= {bank_share:.4%}")
    print(f"  threshold {TCO_RECOMPUTE_SHARE:.0%}")

    worst = max((abs(r["recomputed"] - r["published"]) for r in rows),
                default=0.0)
    print(f"  worst |recomputed - published| = {worst:.4f} Bs")
    print(f"  the published value is rounded to two decimals by Anexo II §4, "
          f"so a gap under 0.005 is the rounding and not a disagreement")

    passed = share >= TCO_RECOMPUTE_SHARE
    print(f"\n  B15-6: {'PASS' if passed else 'FAIL'}")
    if passed:
        print("      **The published TCO is the statute's own formula applied "
              "to the")
        print("      statute's own microdata.** This is the formal leg's zero "
              "calibration:")
        print("      the instrument reports zero when zero is the truth, which "
              "is what")
        print("      B6-18 established for Cuba's informal leg on 909 of 1,321 "
              "days.")
        print("\n      **And it settles a typing arm III had to carry twice.** "
              "The page")
        print("      labels the aggregate `TCO`, so the single number the BCB "
              "publishes")
        print("      after the reform is the TCO and not the valor referencial "
              "de venta.")
        print("      B15-7's ceiling is that number plus Art. 6's ten centavos, "
              "and the")
        print("      second reading both B15-7 and B15-8 were run under is "
              "retired.")
    else:
        print("      §7.1: three things are ruled out before this is a finding.")
        print("      Tier buckets rounding differently from the underlying")
        print("      operations; the 17:00 cutoff excluding operations the page")
        print("      still lists; the publication precision, which Anexo II §4")
        print("      fixes at two decimals. **Only after all three fail do the")
        print("      statute and the practice disagree.**")

    # §6.3's guard_typing_first, read out of arm II's record rather
    # than restated here. See arm_iii_runs.
    _runs, _why = arm_iii_runs(OUT.parent)
    if not _runs:
        print(f"\n  guard_typing_first: {_why}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B15", "step": "zero_calibration",
        "diagnostic_only": not _runs,
        **({} if _runs else {"diagnostic_reason": _why}),
        "authority": "docs/b15_bolivia_prereg.md §5 B15-6, §7.1",
        "window": [SIGNING_DATE.isoformat(),
                   max(series) if series else None],
        "vigencia_mapping": {d: series[d].get("vigencia") for d in series},
        "html_fallback_dates": fallbacks,
        "source_corte_range": corte_range,
        # A list under `criteria`, which is the shape every other record in
        # this repository uses and the shape the results table reads. A
        # singular `criterion` rendered as a heading with nothing under it.
        "criteria": [rendered({
            "criterion": "B15-6", "passed": passed,
            "aggregate_share": share, "aggregate_matches": agg_hits,
            "days": n, "bank_day_share": bank_share,
            "bank_days": bank_total,
            "worst_absolute_gap": worst,
            "days_without_own_grid": without,
        }, "B15-6 the published TCO is the statute's weighted average", (
            f"recomputed from the per-bank microdata by Anexo II's formula and "
            f"matched on {agg_hits} of {n} days and "
            f"{round(bank_share * bank_total)} of {bank_total} bank-days, at "
            f"the two decimals Anexo II section 4 fixes. Worst absolute gap "
            f"{worst:.4f} Bs. **This settles which published number Art. 6's "
            f"ceiling is measured against**, which arm III would otherwise "
            f"have had to carry as two readings"))],
        "rows": rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
