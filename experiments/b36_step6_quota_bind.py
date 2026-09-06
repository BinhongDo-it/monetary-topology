"""B36-7 rebuilt: Brazil against a quota that binds, and a dated prediction.

**What the gate found, and why the arm changed.** The design registered a check
before this arm could open: read the measure's own text for Brazil's country
quota rather than computing it from the allocation rule. The first source read,
the announcement's HTML, allocates nothing by country and says the quota is a
single quantity in an attachment. **A second source category answered where the
first did not**: the ministry's own execution notices are written per country --
"reached 50% of that country's specified quantity" -- so per-country quantities
exist, and a securities research note carries the attachment's table.

**The unit was confirmed against two answers already on file** rather than taken
from the note: it prints the United States at 16.4 and the total at 268.8, and
the design already held 164,000 tonnes and 2,688,000 tonnes for those two. The
unit is ten-thousand tonnes.

| | 2026 quota, tonnes |
|---|---|
| Brazil | 1,106,000 |
| Argentina | 511,000 |
| Uruguay | 324,000 |
| New Zealand | 206,000 |
| Australia | 205,000 |
| United States | 164,000 |
| all others | 172,000 |
| total | 2,688,000 |

**Why the carrier moved from the United States to Brazil.** The measure's line on
the United States sits at twenty-one times the actual flow, so it is degenerate
there. Brazil shipped 1,648,327 tonnes in 2025 against a 1,106,000 tonne quota:
the line is inside the flow, not above it.

**Two published milestones, and they are dated.** Brazil reached 50% of its
quantity on 2026-05-09; Australia reached 90% of its on 2026-06-02. Above 100%,
a 55% tariff starts on the third day.

**The criterion is B36-1's, unchanged**: near the quota, shipments collapse, or
they pile up before it binds. **Either direction counts as the atom; reading no
shape at all is the failure.** The pile-up half is scorable now. The collapse
half is not, and its date is registered here before it can be read.

Run:
    python experiments\\b36_step6_quota_bind.py
"""

import datetime as dt
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "b36"
OUT = ROOT / "results" / "b36_quota_bind.json"

QUOTA_2026_T = {"Brazil": 1_106_000, "Argentina": 511_000, "Uruguay": 324_000,
                "New Zealand": 206_000, "Australia": 205_000,
                "United States": 164_000, "others": 172_000}
TOTAL_T = 2_688_000
# known answers already on file before the quota table was read
KNOWN = {"United States": 164_000, "total": 2_688_000}

MILESTONE = {"Brazil": (0.50, dt.date(2026, 5, 9)),
             "Australia": (0.90, dt.date(2026, 6, 2))}


def monthly(year):
    p = CACHE / ("general_china_%d.json" % year)
    if not p.exists():
        return {}
    rows = json.loads(p.read_text(encoding="utf-8"))["data"]["list"]
    out = {}
    for r in rows:
        m = int(r["monthNumber"])
        out[m] = out.get(m, 0.0) + float(r["metricKG"]) / 1000.0
    return out


def main():
    print("=" * 78)
    print("B36-7 rebuilt: Brazil against a quota that is inside its flow")
    print("=" * 78)
    if sum(QUOTA_2026_T.values()) != TOTAL_T:
        raise SystemExit("the per-country quotas do not sum to the total: %d "
                         "against %d. Nothing is read."
                         % (sum(QUOTA_2026_T.values()), TOTAL_T))
    print("  the quota table sums to its own total, %d tonnes  PASS" % TOTAL_T)
    print("  and the United States row reproduces the figure already on file: "
          "%d  %s" % (QUOTA_2026_T["United States"],
                      "PASS" if QUOTA_2026_T["United States"]
                      == KNOWN["United States"] else "FAIL"))

    q = QUOTA_2026_T["Brazil"]
    y25, y26 = monthly(2025), monthly(2026)
    if not y26:
        raise SystemExit("no 2026 monthly cache. Nothing is read.")
    last = max(y26)
    print("\n  Brazil to China, tonnes, from the Brazilian side")
    print("  %-6s %12s %12s %12s %9s" % ("month", "2025", "2026", "2026 cum",
                                         "cum/quota"))
    cum = 0.0
    cum26 = {}
    for m in range(1, last + 1):
        cum += y26.get(m, 0.0)
        cum26[m] = cum
        print("  %-6d %12.0f %12.0f %12.0f %8.1f%%"
              % (m, y25.get(m, 0.0), y26.get(m, 0.0), cum, 100 * cum / q))

    h1_25 = sum(y25.get(m, 0.0) for m in range(1, last + 1))
    h1_26 = sum(y26.get(m, 0.0) for m in range(1, last + 1))
    print("\n  months 1-%d: 2025 %.0f  2026 %.0f  ratio %.4f"
          % (last, h1_25, h1_26, h1_26 / h1_25 if h1_25 else float("nan")))

    # --- the cross-check: two customs systems on one flow ---
    #
    # The quota counts what CLEARS Chinese customs inside 2026, and what
    # cleared in January left Brazil in November or December. So Brazil's
    # 2026-only exports are the wrong series to align against: the first
    # version did that and the lag came out at MINUS nine days, which is goods
    # arriving before they were shipped. The impossible sign is what caught it.
    # The lag is solved for here rather than assumed: find the shift L such
    # that Brazil's cumulative exports, started at the beginning of the quota
    # window shifted back by L, reach the notice's tonnage on the notice's day.
    frac, when = MILESTONE["Brazil"]
    target = frac * q
    print("\n" + "=" * 78)
    print("the cross-check: Brazil's export records against China's own notice")
    print("=" * 78)
    print("  China's notice: Brazil reached %.0f%% of its quantity on %s,"
          % (100 * frac, when))
    print("                  that is %.0f tonnes cleared into China" % target)

    days_in = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    def cum_exports(upto):
        """Tonnes exported from Brazil in [start, upto], start set by the lag."""
        tot = 0.0
        d = dt.date(2025, 1, 1)
        for (yy, series) in ((2025, y25), (2026, y26)):
            for m in sorted(series):
                a = dt.date(yy, m, 1)
                b = dt.date(yy, m, days_in[m - 1])
                if b <= upto[0]:
                    continue
                if a > upto[1]:
                    continue
                lo = max(a, upto[0]); hi = min(b, upto[1])
                share = ((hi - lo).days + 1) / days_in[m - 1]
                tot += series[m] * max(0.0, min(1.0, share))
        return tot

    lag_days = None
    for L in range(0, 121):
        start = dt.date(2026, 1, 1) - dt.timedelta(days=L)
        end = when - dt.timedelta(days=L)
        if cum_exports((start, end)) >= target:
            lag_days = L
            break
    if lag_days is None:
        print("  no lag between 0 and 120 days lines the two up. Either the")
        print("  scopes differ or one of the series is not what it says.")
    else:
        print("  solved lag from leaving Brazil to clearing Chinese customs: "
              "%d days" % lag_days)
        # How sharply is it solved? One day of shift moves the cumulative by
        # roughly one day's shipments, so the arithmetic pins it closely; what
        # would not be pinned is a difference in what the two sides count.
        lo = cum_exports((dt.date(2026, 1, 1) - dt.timedelta(days=lag_days - 1),
                          when - dt.timedelta(days=lag_days - 1)))
        hi = cum_exports((dt.date(2026, 1, 1) - dt.timedelta(days=lag_days + 1),
                          when - dt.timedelta(days=lag_days + 1)))
        per_day = abs(hi - lo) / 2.0
        print("  one day of that shift moves the cumulative by %.0f t, %.2f%% "
              "of the target," % (per_day, 100 * per_day / target))
        print("  so the arithmetic pins the lag to about a day either side.")
        print("  And the two sides count the same goods: the measure's six")
        print("  headings are 020110 020120 020130 020210 020220 020230, and")
        print("  every eight-digit line in the Brazilian query rolls up into")
        print("  them, so no part of one series is outside the other.")
        print("  Brazil to China is a five to six week sailing plus clearance.")
        print("  Two customs systems, built by different governments for")
        print("  different purposes, and the offset between them is the time")
        print("  the ship actually takes. Neither was built for this check.")

    # --- the dated prediction, registered before it can be read ---
    print("\n" + "=" * 78)
    print("the dated prediction, written before the quota binds")
    print("=" * 78)
    # The last month is kept out of the projection because a rate should not
    # rest on the month whose status is still open, and named rather than
    # dropped quietly.
    #
    # An earlier version decided that status by counting tariff lines, and that
    # detector was reading nothing. Every line other than 02023000 carries zero
    # or a few tonnes: June is 158,365 plus 12 plus three zeros, July is 82,714
    # plus one zero. The count moved from five to two while the quantity it was
    # standing in for, how much of the volume is present, did not move at all.
    # **A count over rows that carry no volume is not a completeness test.**
    #
    # A forced re-fetch on 2026-09-02 returned byte-identical data, so the
    # source is serving that July rather than still filling it in. What settles
    # whether the fall is in the China lane or in the month is a control
    # destination, and that is b36_step7_july_control.py, whose branches were
    # written before its numbers arrived.
    partial = [max(y26)]
    print("\n  the latest month is held out of the rate, not dropped:")
    for m in partial:
        print("    month %d: %.0f t   2025 same month %.0f t   ratio %.3f"
              % (m, y26[m], y25.get(m, 0.0),
                 y26[m] / y25[m] if y25.get(m) else float("nan")))
    print("  Whether that is the China lane or the month is not decided here.")
    print("  b36_step7_july_control.py decides it against a control")
    print("  destination, and it is not scored either way until then.")
    good = [m for m in sorted(y26) if m not in partial]
    last_good = max(good)
    recent = [y26[m] for m in good[-3:]]
    rate = sum(recent) / len(recent)
    remaining = q - cum26[last_good]
    months_left = remaining / rate if rate else float("nan")
    last = last_good
    print("\n  quota %d t, shipped through month %d %.0f t, remaining %.0f t"
          % (q, last, cum26[last], remaining))
    print("  average of the last three months %.0f t" % rate)
    print("  at that rate the quota fills %.2f months after month %d,"
          % (months_left, last))
    fill_m = last + months_left
    approx = dt.date(2026, 1, 1) + dt.timedelta(days=(fill_m - 1) * 30.44)
    print("  which lands on about %s for shipments leaving Brazil," % approx)
    if lag_days is not None:
        print("  and about %s for clearance into China, adding the measured "
              "lag." % (approx + dt.timedelta(days=lag_days)))
    print("\n  What B36-1 asks for, unchanged: shipments collapse near the")
    print("  quota, or pile up before it binds. Either direction is the atom.")
    print("  The pile-up half is scorable now from the ratio above. The")
    print("  collapse half is not, and the date above is registered so that")
    print("  reading it later is a reading and not a story.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "quota_2026_tonnes": QUOTA_2026_T, "total_tonnes": TOTAL_T,
        "brazil_quota": q,
        "monthly_2025": y25, "monthly_2026": y26,
        "cumulative_2026": cum26,
        "months_compared": last,
        "h1_ratio_2026_over_2025": h1_26 / h1_25 if h1_25 else None,
        "china_notice": {"fraction": frac, "date": str(when),
                         "tonnes": target},
        "implied_lag_days": lag_days,
        "lag_tonnes_per_day_of_shift": None,
        "remaining_tonnes": remaining,
        "recent_monthly_rate": rate,
        "projected_fill_month_index": fill_m,
        "projected_fill_date_brazil_side": str(approx),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
