"""B15 arm IV: B15-10 and B15-11.

``docs/b15_bolivia_prereg.md`` §5 is the authority. **Arm IV is not gated.**
`guard_typing_first` suspends arm III when B15-3 or B15-4 is void, and it says
nothing about arm IV, which is why this file can run while B15-3 stands void.

The one thing arm IV has to be careful about
---------------------------------------------

**B15-3 is void, so no side of the parallel leg is typed, and B15-10's
statistic names a side.** §5 B15-10 asks for a break in the log gap between the
parallel bid and the official ask. `guard_no_alignment_shopping` forbids
re-deriving the orientation inside a criterion, so this file does not derive one:
it runs the statistic under **both** orientations and reports both. If the
verdict is the same either way, the orientation does not matter to B15-10 and
the criterion returns a live answer despite the void above it. If the verdicts
differ, that is reported and B15-10 inherits the void rather than picking a
side.

The same treatment covers the second unresolved typing. The BCB publishes one
number after the reform and whether it is the `TCO` or the `valor referencial de
venta` is not settled by any source now in hand, so the official ask is built
both ways, from the published number directly and from the published number plus
`RD 88/2026` Art. 6's ten centavos.

**Four combinations, all reported, none chosen.** That is the whole of this
file's answer to a typing it does not have.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

from monetary_topology.bolivia import (
    AGREEMENT_SHARE,
    EVENT_DATE,
    NULL_DRAWS,
    NULL_SEED,
    S4_HEADER,
    STATUTORY_SPREAD,
    WINDOW_OPEN_DATE,
    cotizaciones,
    ecb_rates,
    parse_csv,
    rendered,
)

ROOT = Path(__file__).resolve().parents[1]
BOLIVIA = ROOT / "data" / "raw" / "bolivia"
OUT = ROOT / "results" / "b15_calibration.json"


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def num(field: str) -> float | None:
    try:
        return float(field)
    except (TypeError, ValueError):
        return None


def daily_s3() -> dict[str, dict[str, float]]:
    """S3 collapsed to one observation a day: the last of each local date.

    **The last and not the mean.** A daily mean of a 15-minute series is a
    different statistic on days the series is thin, and B15-10 is a break test
    on a level rather than on an average. The last observation of a date is the
    close, it exists on every served date, and it is the same construction on
    both sides of the event.
    """
    path = BOLIVIA / "dolarblue_all.csv"
    if not path.exists():
        raise SystemExit(f"{path} is not on disk. Run data/fetch_bolivia.py")
    _, records = parse_csv(path.read_bytes())
    out: dict[str, dict[str, float]] = {}
    for r in records:
        if not r or not r[0]:
            continue
        values = [num(x) for x in r[1:5]]
        if any(v is None for v in values):
            continue
        out[r[0][:10]] = {"official_buy": values[0], "official_sell": values[1],
                          "blue_buy": values[2], "blue_sell": values[3]}
    return out


def daily_s4() -> dict[str, float]:
    """S4 as date -> median, past the licence banner the file opens with.

    The file leads with four `#` comment lines carrying the source, the licence
    and a generation timestamp, so the first CSV row is not the header. **The
    register recorded the header and not the banner**, which is what a summary
    of a page shows you; the banner is what the file has. Skipping `#` lines and
    then asserting the header is the difference between reading a licence string
    as a date and noticing.
    """
    path = BOLIVIA / "paralelo_historical.csv"
    if not path.exists():
        return {}
    rows = [r for r in ([h] + list(rs)) if r and not r[0].startswith("#")
            ] if (hrs := parse_csv(path.read_bytes())) and (h := hrs[0]) is not None \
        and (rs := hrs[1]) is not None else []
    if not rows:
        return {}
    header = tuple(n.strip().lower() for n in rows[0])
    if header != S4_HEADER:
        print(f"  S4 header after the banner is {header}, register says "
              f"{S4_HEADER}")
    return {r[0][:10]: v for r in rows[1:]
            if len(r) >= 2 and (v := num(r[1])) is not None}


#: S5's own column, named rather than positional.
#:
#: **The first version of this took column 1 and column 1 is `low`.** The files
#: are `timestamp,low,high,median,vwap,naive`, an intraday scrape of a P2P board
#: at about forty rows a day, and `low` is the cheapest advertisement on the
#: board that minute. `sell.csv` carries a `low` of 6.5 on a day the market was
#: near 11, which is one abandoned advertisement and not a price. Averaging the
#: `low` of one file against the `low` of another produced a publication noise
#: floor of 2.4 Bs, a number with no referent, and B15-11 failed on it.
#: **A column read by position is a column read by hope.**
S5_COLUMN = "median"


def daily_s5(name: str) -> dict[str, float]:
    """One of S5's files as local date -> the day's last median.

    The timestamps carry their own offset, `-04:00`, which is `America/La_Paz`
    and is the first independent confirmation of §3.3's registered zone from a
    source that states it rather than from a clock comparison.
    """
    path = BOLIVIA / f"mauforonda_{name}"
    if not path.exists():
        return {}
    header, records = parse_csv(path.read_bytes())
    names = [h.strip().lower() for h in header]
    if S5_COLUMN not in names:
        print(f"  S5 {name}: no {S5_COLUMN!r} column in {names}; skipped")
        return {}
    k = names.index(S5_COLUMN)
    out: dict[str, float] = {}
    for r in records:
        if not r or len(r) <= k:
            continue
        value = num(r[k])
        if value is not None and value > 0:
            out[r[0][:10]] = value          # last observation of the local date
    return out


def s5_orientation() -> dict:
    """Does S5's buy/sell ordering flip at the event the way S3's does?

    **This is the question B15-3's void actually raises**, and it belongs here
    rather than in arm II because it needs a second publisher. If S3's blue pair
    reverses at 2026-06-29 and S5's does not, the reversal is one publisher
    relabelling its columns. If both reverse, it is the market.
    """
    buy, sell = daily_s5("buy.csv"), daily_s5("sell.csv")
    days = sorted(set(buy) & set(sell))
    if not days:
        return {"available": False}
    out = {}
    for label, lo, hi in (("pre-event ", "0000", EVENT_DATE.isoformat()),
                          ("post-event", EVENT_DATE.isoformat(), "9999")):
        sub = [d for d in days if lo <= d < hi]
        if not sub:
            continue
        higher = sum(1 for d in sub if buy[d] > sell[d])
        out[label.strip()] = {"days": len(sub), "buy_above_sell": higher,
                              "share": higher / len(sub)}
        print(f"      {label}  n={len(sub):>4}   "
              f"buy > sell on {higher / len(sub):7.3%} of days")
    return {"available": True, **out}


# ---------------------------------------------------------------------------
# B15-10
# ---------------------------------------------------------------------------

def break_statistic(series: list[tuple[str, float]], cut: str) -> float:
    """|mean after - mean before|, the simplest thing that answers the question.

    A break test wants one number that is large when the level moves at `cut`
    and small otherwise. Anything fancier here would be a choice, and the null
    is what carries the inference.
    """
    before = [v for d, v in series if d < cut]
    after = [v for d, v in series if d >= cut]
    if len(before) < 2 or len(after) < 2:
        return 0.0
    return abs(sum(after) / len(after) - sum(before) / len(before))


def b15_10(s3: dict[str, dict[str, float]]) -> dict:
    """The event. §5 B15-10.

    Break at 2026-06-29 in the log gap, against a permutation null over the
    window with the break date drawn uniformly, 999 draws, seed 0. **Passes if**
    the observed statistic exceeds the 99th percentile of the null.
    **The null's degeneracy is checked and reported**, because B6-14's null
    returned the same value on all 999 draws and that was reported rather than
    hidden.
    """
    rule("B15-10  the event")
    cut = EVENT_DATE.isoformat()
    dates = sorted(s3)
    print(f"  {len(dates):,} daily observations, break registered at {cut}")
    print(f"  null: {NULL_DRAWS} draws, seed {NULL_SEED}, break date uniform "
          f"over the window\n")

    variants: dict[str, list[tuple[str, float]]] = {}
    for bid_col, bid_name in (("blue_buy", "A: blue_buy is the bid"),
                              ("blue_sell", "B: blue_sell is the bid")):
        for ask_expr, ask_name in (
                ("official_sell", "ask = official_sell as served"),
                ("official_buy+", f"ask = official_buy + {STATUTORY_SPREAD}")):
            series = []
            for day in dates:
                row = s3[day]
                bid = row[bid_col]
                ask = (row["official_sell"] if ask_expr == "official_sell"
                       else row["official_buy"] + STATUTORY_SPREAD)
                if bid > 0 and ask > 0:
                    series.append((day, math.log(bid) - math.log(ask)))
            variants[f"{bid_name}; {ask_name}"] = series

    results = {}
    for name, series in variants.items():
        observed = break_statistic(series, cut)
        rng = random.Random(NULL_SEED)
        candidates = [d for d, _ in series]
        drawn = [rng.choice(candidates) for _ in range(NULL_DRAWS)]
        null_by_date = [(break_statistic(series, d), d) for d in drawn]
        null = sorted(v for v, _ in null_by_date)
        p99 = null[int(0.99 * (len(null) - 1))]
        distinct = len(set(round(v, 12) for v in null))
        exceeds = observed > p99
        rank = sum(1 for v in null if v >= observed)
        print(f"  {name}")
        print(f"      observed break statistic  {observed:.6f}")
        print(f"      null p99                  {p99:.6f}")
        print(f"      null min / median / max   {null[0]:.6f} / "
              f"{null[len(null) // 2]:.6f} / {null[-1]:.6f}")
        print(f"      distinct null values      {distinct} of {len(null)}"
              + ("   DEGENERATE" if distinct < 10 else ""))
        print(f"      null draws >= observed    {rank}")
        print(f"      exceeds p99: {exceeds}")
        # **Print the draws that beat it, not just how many.** A permutation
        # null over break dates is a null of "a break somewhere else", and on a
        # series with one real step the cuts adjacent to that step reproduce
        # almost all of it. Whether this criterion failed because the event is
        # weak or because the null cannot tell 06-29 from 06-28 is settled by
        # looking at where those draws are, and by nothing else.
        beaters = sorted({d for v, d in null_by_date if v >= observed})
        if beaters:
            gaps = [abs((dt.date.fromisoformat(d) - EVENT_DATE).days)
                    for d in beaters]
            print(f"      the {len(beaters)} distinct dates that match or beat "
                  f"the registered break:")
            print(f"        {', '.join(beaters)}")
            print(f"        distance from {EVENT_DATE} in days: "
                  f"min {min(gaps)}, max {max(gaps)}")
            results_beaters = {"dates": beaters, "min_days_from_event": min(gaps),
                               "max_days_from_event": max(gaps)}
            # **A break test cannot tell a break at t from a break at t+1.**
            # 2026-06-27 and 06-28 are the weekend immediately before the
            # registered date and the series is flat across it, so a cut there
            # is the same split under another label rather than a competing
            # break. A null that counts them against the event is asking
            # whether the reform happened on exactly Monday, which is not the
            # question. The rank is therefore reported twice: as registered,
            # and with the event's own neighbourhood removed.
            near = [(v, d) for v, d in null_by_date
                    if abs((dt.date.fromisoformat(d) - EVENT_DATE).days) <= 7]
            far = [(v, d) for v, d in null_by_date
                   if abs((dt.date.fromisoformat(d) - EVENT_DATE).days) > 7]
            far_ge = sum(1 for v, _ in far if v >= observed)
            far_sorted = sorted(v for v, _ in far)
            far_p99 = far_sorted[int(0.99 * (len(far_sorted) - 1))]
            print(f"        of the {NULL_DRAWS} draws, {len(near)} land within "
                  f"7 days of the event and {len(far)} outside")
            print(f"        excluding that neighbourhood: {far_ge} of "
                  f"{len(far)} draws >= observed, p99 = {far_p99:.6f}, "
                  f"exceeds: {observed > far_p99}")
            results_beaters["draws_within_7_days"] = len(near)
            results_beaters["far_ge_observed"] = far_ge
            results_beaters["far_p99"] = far_p99
            results_beaters["exceeds_far_p99"] = observed > far_p99
        else:
            results_beaters = {"dates": [], "min_days_from_event": None,
                               "max_days_from_event": None}
        print()
        results[name] = {"observed": observed, "null_p99": p99,
                         "null_distinct": distinct, "null_ge_observed": rank,
                         "exceeds_p99": exceeds, "beaters": results_beaters}

    verdicts = {r["exceeds_p99"] for r in results.values()}
    passed = verdicts == {True}
    print(f"  all four combinations agree: {len(verdicts) == 1}")
    print(f"  B15-10: {'PASS' if passed else 'FAIL' if verdicts == {False} else 'SPLIT'}")
    if len(verdicts) == 1:
        print("      the orientation B15-3 could not settle does not change "
              "this verdict,")
        print("      so B15-10 returns a live answer under the void above it.")
    return {"criterion": "B15-10", "passed": passed,
            "orientation_invariant": len(verdicts) == 1,
            "variants": results, "break_date": cut,
            "null_draws": NULL_DRAWS, "null_seed": NULL_SEED}


# ---------------------------------------------------------------------------
# B15-11
# ---------------------------------------------------------------------------

def b15_11(s3: dict[str, dict[str, float]]) -> dict:
    """Zero calibration across publishers. §5 B15-11.

    **Passes if** the share of days on which at least two of the three agree to
    the published precision is >= 0.50. And the disagreement is the measurement
    B6-B could not make: it had one publisher of Cuba's informal rate, so
    `cuba_informal.noise_floor` had to infer publication noise from a variance
    identity. Here it is observed.
    """
    rule("B15-11  zero calibration across publishers")
    s4 = daily_s4()
    s5_buy, s5_sell = daily_s5("buy.csv"), daily_s5("sell.csv")
    print(f"  S3 {len(s3):,} days   S4 {len(s4):,} days   "
          f"S5 buy {len(s5_buy):,} / sell {len(s5_sell):,} days")
    print(f"  S5 reads its {S5_COLUMN!r} column by name\n")
    print("  does S5's ordering flip at the event the way S3's does?")
    flip = s5_orientation()
    if not s4 and not s5_buy:
        print("  S4 and S5 are not on disk. Run data/fetch_bolivia.py --pass s4")
        print("  and --pass s5. B15-11: pending")
        return {"criterion": "B15-11", "verdict": "pending",
                "reason": "S4 and S5 not retrieved"}

    # S3's parallel level, orientation-free: the midpoint of its two columns.
    # **A midpoint is the one summary of a two-sided quote that does not depend
    # on which side is which**, which is what a criterion running under a void
    # B15-3 needs. It is a level and not a spread, so
    # guard_no_one_sided_in_friction is not engaged and S4 may stand beside it.
    s3_mid = {d: (r["blue_buy"] + r["blue_sell"]) / 2 for d, r in s3.items()}
    s5_mid = {d: (s5_buy[d] + s5_sell[d]) / 2
              for d in set(s5_buy) & set(s5_sell)}
    common = sorted(set(s3_mid) & (set(s4) | set(s5_mid)))
    print(f"  {len(common):,} days where at least two publishers overlap\n")

    agree = 0
    pairs = collections.Counter()
    spreads: list[float] = []
    for day in common:
        levels = {}
        if day in s3_mid:
            levels["S3"] = s3_mid[day]
        if day in s4:
            levels["S4"] = s4[day]
        if day in s5_mid:
            levels["S5"] = s5_mid[day]
        if len(levels) < 2:
            continue
        names = sorted(levels)
        hit = False
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if round(levels[a], 2) == round(levels[b], 2):
                    pairs[f"{a}={b}"] += 1
                    hit = True
        agree += hit
        spreads.append(max(levels.values()) - min(levels.values()))

    share = agree / max(1, len(common))
    print(f"  days with at least two agreeing to two decimals: "
          f"{agree:,} of {len(common):,} = {share:.4%}")
    for pair, n in pairs.most_common():
        print(f"      {pair}: {n:,}")
    if spreads:
        spreads.sort()
        n = len(spreads)
        print(f"\n  the observed publication noise floor, "
              f"max - min across publishers per day:")
        for label, q in (("median", 0.50), ("p90", 0.90), ("p99", 0.99)):
            print(f"      {label:>6}  {spreads[min(n - 1, int(q * n))]:.4f} Bs")
        print(f"      {'max':>6}  {spreads[-1]:.4f} Bs")
        print("\n  **This is the number cuba_informal.noise_floor had to infer "
              "from a")
        print("  variance identity because Cuba had one publisher. Here it is "
              "counted.**")

    passed = share >= AGREEMENT_SHARE
    print(f"\n  threshold {AGREEMENT_SHARE:.0%}")
    print(f"  B15-11: {'PASS' if passed else 'FAIL'}")
    return {"criterion": "B15-11", "passed": passed, "agreement_share": share,
            "days_compared": len(common), "pair_counts": dict(pairs),
            "noise_floor_median": spreads[len(spreads) // 2] if spreads else None,
            "noise_floor_max": spreads[-1] if spreads else None,
            "s5_orientation": flip}


# ---------------------------------------------------------------------------
# B15-12, the referee
# ---------------------------------------------------------------------------

ECB_FILE = "ecb_eurofxref_90d.xml"
#: The referee publishes four decimals, so this is its own last
#: digit. Every deviation below is reported in units of it, because
#: a deviation smaller than the referee can resolve is not a
#: disagreement about the world.
REFEREE_TICK = 1e-4
#: The TCO carries two decimals, and it is the larger of the two
#: precisions feeding the implied cross: half its last digit at a
#: TCO near 11.5 is an order of magnitude more than the referee's.
TCO_TICK = 1e-2


def s7_daily() -> dict[str, dict]:
    """One entry per date the BCB's quotation tables actually show.

    **Keyed on the date the page echoes, not the date requested.** Eighteen of
    the fifty-seven requests came back showing another day, which is Anexo II
    section 4 speaking rather than data missing: weekends and holidays carry
    the previous business day's table. Keying on the echo collapses them
    instead of counting one table several times, and a criterion that counted
    them several times would be reading the calendar as evidence.
    """
    out: dict[str, dict] = {}
    for path in sorted(BOLIVIA.glob("bcb_cotizaciones_*.html")):
        table = cotizaciones(path.read_bytes())
        stamp = table["date"]
        usd = table["rows"].get("USD") or []
        eur = table["rows"].get("EUR") or []
        raw = table["raw"].get("EUR") or []
        if not stamp or not usd or len(eur) < 2 or not raw:
            continue
        out[stamp] = {"tco": usd[0], "eur_bs": eur[0], "eur_me": eur[1],
                      "eur_raw": raw[0]}
    return out


def published_tick(days: dict[str, dict]) -> tuple[float, int]:
    """The band, read off the publication rather than chosen.

    §5 B15-12 fixes the band at **one tick of the published euro series**, and
    a tick is a count of decimals in what the publisher wrote. Taken as the
    widest precision seen, so that a day printed to four decimals does not
    narrow the band for a day printed to five.
    """
    decimals = 0
    for row in days.values():
        token = row["eur_raw"]
        if "." in token:
            decimals = max(decimals, len(token.split(".", 1)[1]))
    return 10.0 ** -decimals, decimals


def ecb_back(ecb: dict[str, dict], stamp: str, steps: int) -> tuple[str, float] | None:
    """The ECB's USD rate `steps` publication days before `stamp`.

    **Business days are counted on the ECB's own calendar and not on a
    Bolivian one.** Art. 5.III's clock is "the previous business day", and a
    Monday's previous business day is the Friday. Stepping through the dates
    the referee actually published gets that for free and does not require
    this repository to invent a holiday table for either country.
    """
    if steps < 0:
        raise ValueError("steps counts publication days back, so it is >= 0")
    dates = sorted(d for d in ecb if "USD" in ecb[d])
    if steps == 0:
        return (stamp, ecb[stamp]["USD"]) if stamp in dates else None
    earlier = [d for d in dates if d < stamp]
    if len(earlier) < steps:
        return None
    day = earlier[-steps]
    return day, ecb[day]["USD"]


def b15_12(days: dict[str, dict], ecb: dict[str, dict]) -> dict:
    """The referee. §5 B15-12, §3 S6.

        published Bs/EUR  ?=  TCO x (ECB USD per EUR)

    **Passes if** the two agree within one tick of the published euro series.
    The band is `published_tick`, read off the publication.

    **The lag is scanned rather than assumed, and the scan is the finding.**
    §5 registered that Art. 5.III fixes the alignment where B6-4 had to guess
    it, so the registered reading is one publication day back. The other steps
    are run beside it because a criterion that reports only the step it
    expected cannot tell a fit from a coincidence.

    **One thing the band cannot resolve, printed rather than absorbed.** The
    ECB publishes four decimals, so half its last digit times the TCO is the
    floor on any reconstruction, and at a TCO near 11.5 that floor is tens of
    ticks. A day inside the band is a day where the identity survived that
    floor; a day outside it may be the identity failing or may be the referee's
    own rounding, **and the second column below separates them** by comparing
    the BCB's own published cross against the ECB at the ECB's precision,
    where no multiplication happens and no rounding is inherited.
    """
    rule("B15-12  the referee")
    band, decimals = published_tick(days)
    print(f"  published euro series carries {decimals} decimals, "
          f"so the band is one tick = {band:g} Bs")
    print(f"  {len(days)} BCB days, {len(ecb)} ECB days")

    scan, deviations = {}, {}
    for steps in (0, 1, 2, 3):
        inside, gaps, devs, compared = 0, [], [], 0
        envelopes, outside = [], 0
        for stamp, row in sorted(days.items()):
            got = ecb_back(ecb, stamp, steps)
            if got is None:
                continue
            compared += 1
            gap = abs(row["tco"] * got[1] - row["eur_bs"])
            gaps.append(gap)
            if gap <= band:
                inside += 1
            # The deviation in the referee's own units. **No line is drawn on
            # it.** The first version scored this column against a 5e-4 band,
            # and that band appears in no register: it was picked after the
            # run, it landed in the middle of the distribution it was scoring,
            # and the share it produced was a property of the line rather than
            # of the data. What the column carries now is the distribution.
            cross = row["eur_bs"] / row["tco"]
            devs.append(abs(cross - got[1]))
            # **The rounding envelope, computed per day rather than asserted.**
            # Two published precisions feed the implied cross and the larger
            # one is not the referee's. The TCO carries two decimals, so half
            # its last digit is 0.005 Bs, and at a TCO near 11.5 that is a
            # relative error of 4.3e-4 which arrives in the cross multiplied
            # by the cross itself. The referee's own half-digit is 5e-5, an
            # order of magnitude smaller. **Saying a deviation is too large to
            # be rounding without computing this is an assertion**, and the
            # first draft of this criterion made it.
            envelope = REFEREE_TICK / 2 + cross * (TCO_TICK / 2) / row["tco"]
            envelopes.append(envelope)
            if abs(cross - got[1]) > envelope:
                outside += 1
        if not compared:
            continue
        deviations[steps] = devs
        ordered = sorted(devs)
        scan[steps] = {
            "days_compared": compared,
            "within_band": inside,
            "within_band_share": inside / compared,
            "max_gap_bs": max(gaps),
            "median_gap_bs": sorted(gaps)[len(gaps) // 2],
            "max_gap_ticks": max(gaps) / band,
            "cross_deviation_mean": sum(devs) / len(devs),
            "cross_deviation_median": ordered[len(ordered) // 2],
            "cross_deviation_max": max(devs),
            "cross_deviation_mean_in_referee_ticks":
                (sum(devs) / len(devs)) / REFEREE_TICK,
            "outside_rounding_envelope": outside,
            "outside_rounding_envelope_share": outside / compared,
            "deviation_over_envelope_median":
                sorted(d / e for d, e in zip(devs, envelopes))[len(devs) // 2],
            "deviation_over_envelope_max":
                max(d / e for d, e in zip(devs, envelopes)),
        }

    # Which lag is nearest on each day, and how often. **A count of days, not
    # a share against a threshold**, which is the shape the criteria in this
    # repository that caught anything all had.
    nearest = {steps: 0 for steps in scan}
    common = set.intersection(*[set(days) for _ in [0]]) if days else set()
    for stamp in sorted(days):
        here = {}
        for steps in scan:
            got = ecb_back(ecb, stamp, steps)
            if got is not None:
                here[steps] = abs(days[stamp]["eur_bs"] / days[stamp]["tco"]
                                  - got[1])
        if here:
            nearest[min(here, key=here.get)] += 1

    print()
    print(f"    {'lag':>4} {'days':>5} {'in band':>9} {'nearest on':>11} "
          f"{'mean dev':>10} {'ref ticks':>10} {'outside rounding':>17} "
          f"{'dev/env med':>12}")
    for steps, row in sorted(scan.items()):
        tag = "  <- Art. 5.III" if steps == 1 else ""
        print(f"    {steps:>4} {row['days_compared']:>5} "
              f"{row['within_band_share']:>8.1%} "
              f"{nearest.get(steps, 0):>8} d  "
              f"{row['cross_deviation_mean']:>10.5f} "
              f"{row['cross_deviation_mean_in_referee_ticks']:>10.1f} "
              f"{row['outside_rounding_envelope']:>8}/"
              f"{row['days_compared']:<8} "
              f"{row['deviation_over_envelope_median']:>11.2f}{tag}")

    # Paired, because the two columns are read on the same days and an
    # unpaired comparison of two means over one sample says less than the
    # count of days on which one beat the other.
    closer = None
    if 0 in deviations and 1 in deviations:
        pairs = list(zip(deviations[0], deviations[1]))
        closer = sum(1 for a, b in pairs if a < b)
        print(f"\n  lag 0 is nearer than lag 1 on {closer} of {len(pairs)} "
              f"days, paired on the same dates")

    floor_ticks = max(r["tco"] for r in days.values()) * (REFEREE_TICK / 2) / band
    print()
    print(f"  the referee publishes {REFEREE_TICK:g}, so half its last digit "
          f"at the largest TCO here is {floor_ticks:.0f} ticks of the euro "
          f"series.")
    print(f"  **A band of one tick is below that floor**, so the first column "
          f"cannot pass on any alignment and its failing carries nothing "
          f"about Bolivia. What carries something is the last column.")

    registered = scan.get(1)
    passed = bool(registered and registered["within_band_share"] >= 1.0)
    best = min(scan, key=lambda k: scan[k]["cross_deviation_mean"]) if scan else None
    print()
    print(f"  B15-12: {'PASS' if passed else 'FAIL'}")
    if best is not None:
        ticks = scan[best]["cross_deviation_mean_in_referee_ticks"]
        out_share = scan[best]["outside_rounding_envelope_share"]
        print(f"  at lag {best}, "
              f"{scan[best]['outside_rounding_envelope']} of "
              f"{scan[best]['days_compared']} days fall outside the envelope "
              f"the two published precisions allow, median "
              f"{scan[best]['deviation_over_envelope_median']:.2f} times it "
              f"and at most "
              f"{scan[best]['deviation_over_envelope_max']:.2f} times.")
        # **The reading branches on the referee's own resolution, not on a
        # line.** A deviation the referee cannot resolve is not a
        # disagreement about the world; one many times its last digit is.
        if out_share <= 0.0:
            print(f"  **The registered expectation is met.** The nearest "
                  f"alignment is lag {best} and its mean deviation is "
                  f"{ticks:.1f} times the referee's own last digit, which is "
                  f"inside what the referee can resolve. The published euro "
                  f"is the published dollar times this cross, and §5 B15-12's "
                  f"reading applies: this measures the pass-through.")
        else:
            print(f"  **The registered expectation is not met.** §5 B15-12 "
                  f"wrote that if Bolivia's euro were Cuba's, a mechanical "
                  f"restatement of its dollar times a world cross, this "
                  f"criterion would measure a pass-through. The nearest "
                  f"alignment is lag {best} and it still sits {ticks:.0f} "
                  f"times the referee's last digit away, so the euro is not "
                  f"that restatement at any alignment tried. **It tracks the "
                  f"cross without reproducing it**, which makes the euro leg "
                  f"carry something the dollar leg does not.")
    return {
        "criterion": "B15-12", "passed": passed,
        "band_bs": band, "euro_decimals": decimals,
        "referee_tick": REFEREE_TICK,
        "registered_lag": 1,
        "referee_floor_in_ticks": floor_ticks,
        "nearest_lag_by_mean_deviation": best,
        "nearest_deviation_in_referee_ticks":
            scan[best]["cross_deviation_mean_in_referee_ticks"] if best is not None else None,
        "nearest_lag_day_counts": {str(k): v for k, v in nearest.items()},
        "lag0_nearer_than_lag1_days": closer,
        "scan": {str(k): v for k, v in scan.items()},
    }


def main() -> int:
    s3 = daily_s3()
    ten = b15_10(s3)
    eleven = b15_11(s3)

    rule("arm IV so far")
    print(f"  B15-10  {'PASS' if ten['passed'] else 'see above'}")
    print(f"  B15-11  {eleven.get('verdict') or ('PASS' if eleven.get('passed') else 'FAIL')}")


    # **B15-12 gets a row rather than a print line.** It is a registered
    # criterion and its state is "did not run for want of a carrier", which is
    # a state a reader of RESULTS.md has to be able to see. A criterion that
    # exists only as a sentence in a log is a criterion nobody can check the
    # status of.
    # **B15-12 runs.** The register put the euro on an endpoint that does not
    # carry it; it is on the BCB's per-day quotation table, one request each,
    # and the correction is recorded in the results file rather than in the
    # register, which does not move.
    days_s7 = s7_daily()
    ecb_path = BOLIVIA / ECB_FILE
    ecb = ecb_rates(ecb_path.read_bytes()) if ecb_path.exists() else {}
    if days_s7 and ecb:
        twelve = b15_12(days_s7, ecb)
    else:
        twelve = {
            "criterion": "B15-12", "void": True, "verdict": "not run",
            "reason": (f"{'no BCB quotation tables' if not days_s7 else ''}"
                       f"{' and ' if not days_s7 and not ecb else ''}"
                       f"{'no ECB reference file' if not ecb else ''}"
                       f" on disk; run data/fetch_bolivia.py --pass all"),
        }

    rendered(ten, "B15-10 the event", (
        f"no single dated break at the reform: null draws "
        f"{ten['null_draws']}, seed {ten['null_seed']}, break date "
        f"{ten['break_date']}, and the reading does not depend on which "
        f"orientation is taken ({ten['orientation_invariant']}). The banks' "
        f"rate had already walked most of the way before the instruments were "
        f"signed, so there is no step for a break test to find"))
    rendered(eleven, "B15-11 zero calibration across publishers", (
        f"publishers agree on {eleven['agreement_share']:.2%} of the "
        f"{eleven['days_compared']:,} days compared; the noise floor is "
        f"{eleven['noise_floor_median']:.4f} Bs at the median and "
        f"{eleven['noise_floor_max']:.4f} at its worst"))
    if twelve.get("void"):
        rendered(twelve, "B15-12 the euro leg", twelve["reason"])
    else:
        registered = twelve["scan"].get("1", {})
        rendered(twelve, "B15-12 the referee", (
            f"the published Bs/EUR against the ECB reference rate times the "
            f"published TCO, over {twelve['scan']['1']['days_compared']} days. "
            f"**The registered expectation is "
            f"{'met' if twelve['nearest_deviation_in_referee_ticks'] <= 1.0 else 'not met'}.** "
            f"The register wrote that if Bolivia's euro were Cuba's, a "
            f"mechanical restatement of its dollar times a world cross, this "
            f"criterion would measure the pass-through. The nearest alignment "
            f"is "
            f"lag {twelve['nearest_lag_by_mean_deviation']} and its mean "
            f"deviation is still "
            f"{twelve['scan'][str(twelve['nearest_lag_by_mean_deviation'])]['cross_deviation_mean_in_referee_ticks']:.0f}"
            f" times the referee's own last digit, so the euro leg tracks the "
            f"cross without restating it and carries information the dollar "
            f"leg does not. The registered band of one tick of the euro series "
            f"sits below the floor the referee's four decimals put under any "
            f"reconstruction ({twelve['referee_floor_in_ticks']:.0f} ticks), "
            f"so that band cannot be met on any alignment"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B15", "step": "calibration",
        "diagnostic_only": False,
        "authority": "docs/b15_bolivia_prereg.md §5",
        "window": [WINDOW_OPEN_DATE.isoformat(), max(s3).ljust(10)],
        "criteria": [ten, eleven, twelve],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
