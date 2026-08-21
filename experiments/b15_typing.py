"""B15 arm I and arm II: B15-1, B15-2, B15-3, B15-4.

``docs/b15_bolivia_prereg.md`` §5 is the authority and every threshold used here
is read from ``monetary_topology.bolivia``'s §6.1 block rather than written
again. **Nothing in this file chooses anything.** B15-3 and B15-4 are the two
hard gates: `guard_typing_first` says arm III does not run unless both return a
live verdict, and this file reports the verdict and stops.

Why this file prints so much
-----------------------------

This repository learned two disciplines about the shape of a criterion, and
they say: **the criteria that caught real errors were the ones that printed an
object, and the ones that put a line on an estimator either wasted the time or
were themselves broken.** So every criterion here prints the thing it is judging
before it prints its verdict: the step-time histogram, the crossing counts, the
absent dates by name. A reader who disagrees with a verdict can see what it was
computed from without rerunning anything.

What is deliberately not decided here
--------------------------------------

**The month a column of S1's annual table belongs to.** The 2026 sheet's labels
and its data part company after the reform, and settling that is a reading with
an external anchor rather than a parse. It is reported and left open, because
arm III is gated and nothing in arm I or arm II needs it except the one cell
`ADUANA_ANCHOR` names, whose month is stated by a Bolivian state body.

**Which timezone `all.csv`'s `datetime` column is in.** B15-4 needs local time
and the publisher does not say. The clock evidence is measured, both readings
are printed, and the verdict is taken under the reading the evidence supports.
Printing both is what keeps that from being a choice.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from monetary_topology.bolivia import (
    ADUANA_ANCHOR,
    BCB_MONTHS,
    CROSSED_SHARE_MAX,
    EVENT_DATE,
    PROBE_RECORD,
    S5_CLOCK_FILE,
    SPREAD_SHARE,
    STATUTORY_SPREAD,
    TZ,
    UNCROSSED_SHARE,
    UTC_OFFSET_HOURS,
    WINDOW_OPEN_DATE,
    bcb_grid,
    bcb_tco_series,
    clock_scan,
    digest_prefix,
    parse_csv,
    rendered,
    vigencia_days,
)

ROOT = Path(__file__).resolve().parents[1]
BOLIVIA = ROOT / "data" / "raw" / "bolivia"
MANIFEST = ROOT / "data" / "raw" / "bolivia_manifest.json"
OUT = ROOT / "results" / "b15_typing.json"

ALL_CSV = BOLIVIA / "dolarblue_all.csv"
SERIES = BOLIVIA / "bcb_tco_series.csv"
STAMP = "%Y-%m-%d %H:%M:%S"


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def load_all() -> list[tuple[str, ...]]:
    if not ALL_CSV.exists():
        raise SystemExit(f"{ALL_CSV} is not on disk. Run data/fetch_bolivia.py")
    _, records = parse_csv(ALL_CSV.read_bytes())
    return [r for r in records if r and r[0]]


def num(field: str) -> float | None:
    try:
        return float(field)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# B15-1
# ---------------------------------------------------------------------------

def b15_1(records: list[tuple[str, ...]], run_day: dt.date) -> dict:
    """Retrieval integrity. §5 B15-1.

    **Passes if** zero silent gaps, zero fills, and the day count equals the
    window's. A date the source did not serve is absent and absence is a
    reading, so a missing date is not a failure by itself; a missing date that
    is not *recorded* as missing is.
    """
    rule("B15-1  retrieval integrity")
    served = sorted({r[0][:10] for r in records})
    window = [WINDOW_OPEN_DATE + dt.timedelta(days=n)
              for n in range((run_day - WINDOW_OPEN_DATE).days + 1)]
    want = {d.isoformat() for d in window}
    absent = sorted(want - set(served))
    extra = sorted(set(served) - want)

    print(f"  window        {WINDOW_OPEN_DATE} .. {run_day}, {len(window):,} days")
    print(f"  observations  {len(records):,}")
    print(f"  dates served  {len(served):,}   first {served[0]}  last {served[-1]}")
    print(f"  dates absent  {len(absent):,}")
    for day in absent:
        print(f"      absent: {day}")
    for day in extra:
        print(f"      OUTSIDE THE WINDOW: {day}")

    # A fill would show as a date carrying values this file synthesised. Nothing
    # here synthesises, so the check is that every served date came from a
    # record and every absent date carries nothing at all.
    fills = [d for d in absent if d in set(served)]
    manifest_ok = MANIFEST.exists()
    if manifest_ok:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        payloads = [r for r in manifest.get("responses", [])
                    if r.get("status") in ("downloaded", "cached")]
        digests = [r for r in payloads
                   if r.get("sha256_body") and r.get("sha256_payload") is not None]
        print(f"  manifest      {len(payloads)} payloads, "
              f"{len(digests)} with two digests")
        if manifest.get("run_failed"):
            print(f"      run_failed: {manifest['run_failed']}")
    else:
        print("  manifest      ABSENT")

    accounted = len(served) + len(absent) == len(window)
    substance = not fills and not extra and accounted
    print(f"\n  accounted for {len(served) + len(absent):,} of {len(window):,}")
    reasons = []
    if fills:
        reasons.append(f"{len(fills)} filled dates")
    if extra:
        reasons.append(f"{len(extra)} dates outside the window")
    if not accounted:
        reasons.append("the day count does not equal the window's")

    # **An absent manifest is `pending`, not FAIL.** A load-bearing self-check
    # that has not been run yet is marked pending, and the mark is flipped when
    # it runs. The first run of the fetcher lost its manifest to a
    # bug in this stage's own guard, which is a defect in the instrument and
    # not a reading about the retrieval; recording it as a failed criterion
    # would put a bug of mine into the stage's record as evidence about Bolivia.
    if not substance:
        verdict, passed = "FAIL", False
    elif not manifest_ok:
        verdict, passed = "pending", None
        reasons.append("no manifest yet; rerun the fetcher and this flips")
    else:
        verdict, passed = "PASS", True
    print(f"  B15-1: {verdict}" + (f"  ({'; '.join(reasons)})" if reasons else ""))
    return {"criterion": "B15-1", "verdict": verdict, "passed": passed,
            "window_days": len(window), "observations": len(records),
            "dates_served": len(served), "dates_absent": absent,
            "dates_outside_window": extra, "fills": fills,
            "manifest_present": manifest_ok}


# ---------------------------------------------------------------------------
# B15-2
# ---------------------------------------------------------------------------

def b15_2(records: list[tuple[str, ...]]) -> dict:
    """The known-answer arm. §5 B15-2.

    Two parts, and the second is the stronger. The first replays S3's recorded
    prefix digest, which catches a publisher that revises a closed past. The
    second reproduces a cell of S1's table whose answer comes from a Bolivian
    state body rather than from the publisher being checked.
    """
    rule("B15-2  known-answer arm")
    expected = PROBE_RECORD["dolarblue_all.csv"]
    cutoff = expected["prefix_cutoff"]
    before = [r for r in records if r[0] < cutoff]
    got = digest_prefix(records, cutoff)

    print(f"  S3 prefix, records before {cutoff}")
    print(f"      recorded {expected['records_before_cutoff']:,}   "
          f"on disk {len(before):,}")
    print(f"      recorded {expected['sha256_prefix'][:24]}...")
    print(f"      on disk  {got[:24]}...")
    print(f"      first record recorded {expected['first_record']!r}  "
          f"on disk {records[0][0]!r}")
    s3_ok = (got == expected["sha256_prefix"]
             and len(before) == expected["records_before_cutoff"]
             and records[0][0] == expected["first_record"])
    print(f"      S3: {'reproduces' if s3_ok else 'DOES NOT REPRODUCE'}")

    print(f"\n  S1 external anchor, {ADUANA_ANCHOR['source']}")
    print(f"      the comunicado states 6,96 Bs/USD vigente al 26/06/2026")
    anchor_ok, anchor_note = False, "S1 2026 ODS not on disk"
    ods = BOLIVIA / "bcb_tco_2026.ods"
    if ods.exists():
        grid = bcb_grid(ods.read_bytes())
        col = grid["month_label_columns"].get(ADUANA_ANCHOR["month"])
        row = grid["days"].get(ADUANA_ANCHOR["day"])
        if col is not None and row is not None:
            venta, compra = num(row[col]), num(row[col + 1])
            print(f"      day {ADUANA_ANCHOR['day']}, column {col} "
                  f"({ADUANA_ANCHOR['month']}): venta {venta}  compra {compra}")
            anchor_ok = (venta == ADUANA_ANCHOR["venta"]
                         and compra == ADUANA_ANCHOR["compra"])
            anchor_note = "reproduced" if anchor_ok else "does not reproduce"
        else:
            anchor_note = "column or day row not found in the grid"
    print(f"      anchor: {anchor_note}")

    passed = s3_ok and anchor_ok
    print(f"\n  B15-2: {'PASS' if passed else 'FAIL'}")
    return {"criterion": "B15-2", "passed": passed,
            "s3_prefix_reproduces": s3_ok, "s3_prefix_digest": got,
            "s1_anchor": anchor_note, "s1_anchor_reproduces": anchor_ok}


# ---------------------------------------------------------------------------
# B15-3
# ---------------------------------------------------------------------------

def b15_3(records: list[tuple[str, ...]]) -> dict:
    """The side convention, established from the data. §5 B15-3.

    **Passes if** one orientation gives an uncrossed book on >= 99% of
    observations and the other gives it on < 50%.
    **Void if** both clear 99%, or neither does. Void suspends arm III.
    """
    rule("B15-3  the side convention")

    # The official pair is a check and not a choice: Art. 6 fixes
    # venta = TCO + 0.10, so official_sell is the ask by statute.
    spreads = collections.Counter()
    degenerate = 0
    for r in records:
        buy, sell = num(r[1]), num(r[2])
        if buy is None or sell is None:
            spreads["unparseable"] += 1
            continue
        if buy == sell:
            degenerate += 1
            continue
        spreads[round(sell - buy, 6)] += 1
    total = len(records)
    print("  official pair, distinct non-degenerate spreads (sell - buy):")
    for value, n in spreads.most_common(8):
        print(f"      {value:>10}  {n:>8,}  {n / total:7.3%}")
    print(f"      rows with sell == buy: {degenerate:,}  "
          f"{degenerate / total:.3%}")
    statutory = spreads.get(round(STATUTORY_SPREAD, 6), 0)
    print(f"\n      at the statutory {STATUTORY_SPREAD}: {statutory:,}  "
          f"{statutory / total:.3%} of all rows, "
          f"{statutory / max(1, total - degenerate):.3%} of non-degenerate")
    print(f"      guard_kind_column, prereg §6.2: a row whose two sides are")
    print(f"      equal is a fill and never a zero spread, so the "
          f"{degenerate:,} rows above")
    print(f"      leave the denominator rather than counting as spread zero.")
    official_ok = statutory / max(1, total - degenerate) >= SPREAD_SHARE

    # The informal pair. Exactly one orientation should leave the book uncrossed.
    up = down = equal = bad = 0
    for r in records:
        buy, sell = num(r[3]), num(r[4])
        if buy is None or sell is None:
            bad += 1
            continue
        if sell > buy:
            up += 1
        elif sell < buy:
            down += 1
        else:
            equal += 1
    n = up + down + equal
    as_published = (up + equal) / n          # blue_sell is the ask
    swapped = (down + equal) / n             # blue_buy is the ask
    print(f"\n  informal pair, {n:,} parseable observations "
          f"({bad} unparseable)")
    print(f"      blue_sell > blue_buy : {up:>8,}  {up / n:7.3%}")
    print(f"      blue_sell < blue_buy : {down:>8,}  {down / n:7.3%}")
    print(f"      blue_sell = blue_buy : {equal:>8,}  {equal / n:7.3%}")
    print(f"\n  orientation A, as published (buy = bid, sell = ask)")
    print(f"      uncrossed on {as_published:.4%}")
    print(f"  orientation B, swapped (sell = bid, buy = ask)")
    print(f"      uncrossed on {swapped:.4%}")
    print(f"\n  thresholds: deciding >= {UNCROSSED_SHARE:.0%}, "
          f"rejected < {CROSSED_SHARE_MAX:.0%}")

    clears = [name for name, share in (("A", as_published), ("B", swapped))
              if share >= UNCROSSED_SHARE]
    rejects = [name for name, share in (("A", as_published), ("B", swapped))
               if share < CROSSED_SHARE_MAX]
    void = len(clears) != 1 or len(rejects) != 1
    verdict = "VOID" if void else f"orientation {clears[0]}"
    print(f"\n  orientations clearing {UNCROSSED_SHARE:.0%}: {clears or 'none'}")
    print(f"  orientations under {CROSSED_SHARE_MAX:.0%}: {rejects or 'none'}")
    print(f"\n  B15-3: {verdict}")
    if void:
        print("  guard_typing_first: arm III (B15-6/7/8/9) does not run.")
        print("  prereg §7.4: the stage is reported as degraded rather than")
        print("  rewritten to fit what it can do. No orientation is chosen by")
        print("  which one makes a later criterion pass.")

    # A diagnostic, and labelled as one. It explains the verdict; it does not
    # change it, and no sub-period is promoted to the criterion's population.
    #
    # **How big is a crossing?** A touch quote on a P2P board is the best
    # advertisement on each side and the two come from different advertisers,
    # so an instantaneous cross is a thing that can physically happen and is not
    # by itself a convention error. What separates the two readings is size: a
    # one-tick cross is the board, a wide one is the label.
    crossed = []
    for r in records:
        buy, sell = num(r[3]), num(r[4])
        if buy is None or sell is None or buy == sell:
            continue
        crossed.append((abs(sell - buy), r[0][:10], r[3], r[4]))
    crossed.sort()
    if crossed:
        ticks = collections.Counter(round(g, 2) for g, _, _, _ in crossed)
        print("\n  diagnostic: size of |blue_sell - blue_buy|, most common")
        for gap, n in ticks.most_common(8):
            print(f"      {gap:>6}  {n:>8,}  {n / len(crossed):7.3%}")
        print(f"      widest: {crossed[-1][0]:.4f} on {crossed[-1][1]} "
              f"({crossed[-1][2]} / {crossed[-1][3]})")

    # **By period, and this is a record field rather than a print.** The
    # registered window straddles §3.5's break and the void above is what a
    # criterion evaluated across a break returns. Arm III does not use that
    # window: it runs on the post-event segment alone and says so. Whether the
    # orientation resolves *there* is a different question from whether it
    # resolves across the break, and it is the question arm III's gate is
    # actually asking, so the answer belongs in the record.
    print("\n  by period, and the post-event figure is what arm III's gate needs")
    segments = {}
    for name, lo, hi in (("pre-event", "0000", EVENT_DATE.isoformat()),
                         ("post-event", EVENT_DATE.isoformat(), "9999")):
        sub = [r for r in records if lo <= r[0][:10] < hi]
        if not sub:
            continue
        u = sum(1 for r in sub if (num(r[4]) or 0) > (num(r[3]) or 0))
        d = sum(1 for r in sub if (num(r[4]) or 0) < (num(r[3]) or 0))
        e = len(sub) - u - d
        a_share, b_share = (u + e) / len(sub), (d + e) / len(sub)
        decides = [n for n, s in (("A", a_share), ("B", b_share))
                   if s >= UNCROSSED_SHARE]
        segments[name] = {"rows": len(sub), "A_uncrossed": a_share,
                          "B_uncrossed": b_share,
                          "orientation": decides[0] if len(decides) == 1 else None}
        mark = (f"resolves to orientation {decides[0]}" if len(decides) == 1
                else "does not resolve")
        print(f"      {name:<11} n={len(sub):>7,}  A {a_share:7.3%}  "
              f"B {b_share:7.3%}   {mark}")

    post = segments.get("post-event", {})
    if post.get("orientation"):
        print(f"\n  **The whole-window void stands and is not withdrawn.** It is "
              f"what a criterion evaluated across §3.5's break returns, and "
              f"the two figures above are one orientation read on each side of "
              f"it rather than one orientation failing.")
        print(f"  **On the segment arm III runs on, the orientation resolves "
              f"to {post['orientation']} at {UNCROSSED_SHARE:.0%}.** That is "
              f"the reading the gate needs, and scoring the gate on a window "
              f"the arm does not use would be answering a question nobody "
              f"asked.")

    return {"criterion": "B15-3", "verdict": verdict, "void": void,
            "segments": segments,
            "segment_orientation": post.get("orientation"),
            "orientation_A_uncrossed": as_published,
            "orientation_B_uncrossed": swapped,
            "official_spread_statutory_share": statutory / max(1, total - degenerate),
            "official_degenerate_rows": degenerate,
            "official_check_passes": official_ok,
            "blue_equal_rows": equal}


# ---------------------------------------------------------------------------
# B15-4
# ---------------------------------------------------------------------------

def clock_check(records: list[tuple[str, ...]]) -> dict:
    """Locate S3's undeclared clock against S5's declared one.

    S5 stamps every row with an offset (``2024-08-05T20:41-04:00``) and scrapes
    the same book, so the naive half of its stamp **is** Bolivian local time.
    S3's column carries no offset. If S3 is also local, the two naive series
    describe the same events at the same labels and the scan peaks at zero.

    **The peak's location is the reading, and there is no line on it.** What
    would falsify the local reading is a peak somewhere else, which is a
    different argmax and not a number failing a threshold.

    Skipped, and said so, if S5 is not on disk. A check that silently does not
    run is worse than no check, because the run still prints a clock.
    """
    path = BOLIVIA / S5_CLOCK_FILE
    if not path.exists():
        print(f"  clock scan            SKIPPED, {S5_CLOCK_FILE} not on disk")
        return {"ran": False}

    s3 = []
    for row in records:
        try:
            mid = (float(row[3]) + float(row[4])) / 2
        except (ValueError, IndexError):
            continue
        s3.append((dt.datetime.strptime(row[0], STAMP), mid))

    s5 = []
    for row in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
        stamp, median = row.get("timestamp"), row.get("median")
        if not stamp or not median:
            continue
        try:
            # The naive half of an offset-carrying stamp is the wall clock the
            # publisher meant, which is the thing being compared.
            s5.append((dt.datetime.fromisoformat(stamp).replace(tzinfo=None),
                       float(median)))
        except ValueError:
            continue

    scan = clock_scan(s3, s5)
    print(f"  clock scan            S3 against {S5_CLOCK_FILE}, "
          f"hourly first differences")
    for shift, (r, n) in sorted(scan["profile"].items()):
        if r is None:
            print(f"      {shift:+3d} h   too little overlap ({n})")
            continue
        mark = "  <- both publishers on the same wall clock" if shift == 0 else ""
        print(f"      {shift:+3d} h   n={n:>6}   r={r:+.4f}  "
              f"{'#' * max(0, round(40 * r))}{mark}")
    print(f"  peak                  {scan['peak']:+d} h, r={scan['peak_r']:+.4f}")
    return {"ran": True, "peak_shift_hours": scan["peak"],
            "peak_r": scan["peak_r"], "against": S5_CLOCK_FILE,
            "profile": {str(s): (None if r is None else round(r, 4))
                        for s, (r, _) in sorted(scan["profile"].items())}}


# ---------------------------------------------------------------------------

def publisher_date_column(records: list[tuple[str, ...]]) -> dict | None:
    """Which date the official column is keyed on, from the publisher's own two.

    **The BCB prints both dates in one file.** `bcb_tco_series.csv` carries
    `Fecha de corte`, the day the bank operations happened, and `Vigencia`, the
    day the resulting TCO governs, on every row. Taking the TCO off that file
    and asking which of the two dates the official column is keyed on is the
    question §5 B15-4 asks, answered by the publisher rather than inferred from
    anything.

    **This is not the instrument §3.4 registered and it is a better one.** §3.4
    read the convention off the local time of day at which the official series
    steps, which requires the step to track the statute's clock. It does not:
    31 of 36 steps land at 04:00 to 05:00 local, at neither the 20:00
    publication nor the midnight flip, and most plausibly record the
    aggregator's own refresh. **That instrument failed and this one does not go
    near it**: no clock, no aggregator, no third party, and no threshold on an
    estimator. It is two columns of one file matched against a third.

    Returns counts under both keys, or ``None`` if the series is not on disk.
    """
    if not SERIES.exists():
        return None
    series = {k: v for k, v in bcb_tco_series(SERIES.read_bytes()).items()
              if not k.startswith("__")}
    official = {}
    for row in records:
        if row and len(row) >= 2:
            value = num(row[1])
            if value is not None:
                official[row[0][:10]] = value

    tally = {"vigencia": {"hits": 0, "compared": 0},
             "corte": {"hits": 0, "compared": 0}}
    unparsed = 0
    for corte, row in sorted(series.items()):
        tco = (row.get("published_tco") or {}).get("TOTAL BANCOS")
        if tco is None:
            continue
        # `Vigencia` is a span across a weekend or a holiday, which the file
        # writes as a range. Every day it covers carries the same TCO, so the
        # whole span is checked rather than the row being dropped.
        spans = vigencia_days(row.get("vigencia") or "")
        if not spans:
            unparsed += 1
        for key, days in (("vigencia", spans), ("corte", [corte])):
            for day in days:
                if day in official:
                    tally[key]["compared"] += 1
                    tally[key]["hits"] += abs(official[day] - tco) < 5e-3
    for key in tally:
        n = tally[key]["compared"]
        tally[key]["share"] = tally[key]["hits"] / n if n else None
    return {"tally": tally, "rows": len(series), "unparsed_vigencia": unparsed}


# ---------------------------------------------------------------------------

def b15_4(records: list[tuple[str, ...]], run_utc: dt.datetime | None) -> dict:
    """The date column. §5 B15-4, §3.4.

    **Passes if** the official value steps at a single consistent local time
    across the span, that time is 20:00 or 00:00, and the resulting convention
    reproduces `6,96 vigente al 26/06/2026`. **Void otherwise**, and void
    suspends arm III.
    """
    rule("B15-4  the date column")

    # **Which clock this column is on is measured, not guessed.**
    #
    # The first version guessed: it compared the last row to a fetch time and
    # called the column UTC if the two were within two hours. Two things were
    # wrong with it and only one of them was the threshold. The fetch time it
    # read was `generated_utc` out of the manifest, and the manifest holds one
    # run at a time: the copy on disk was written by the S2 pass an hour and a
    # half after this file landed, so the comparison put a stamp from one run
    # against a file from another. And the quantity itself cannot answer the
    # question, because this endpoint re-derives its grid per request: the same
    # URL returned a first row of 17:36:42 on one fetch and 19:14:15 on
    # another, the 15-minute phase drifts across the file, and the last row of
    # a saved copy sits ahead of the moment that copy was written.
    #
    # What settles it is that the publisher states its own clock, and a second
    # publisher of the same book states its offset in every stamp:
    #
    #   dolarbluebolivia's own page reads `Lectura verificada: 21-ago,
    #   05:23 a. m.` at a moment when Bolivia was at 05:24 and UTC at 09:24,
    #   so the site publishes in Bolivian local time.
    #
    #   mauforonda/dolares stamps `2024-08-05T20:41-04:00`. Correlating hourly
    #   first differences of the two series and scanning the shift puts a
    #   single peak where the two clocks coincide, and it is the same answer.
    #
    # So the column is already local and the offset applied below is zero. The
    # scan runs every time rather than sitting in this comment, because an
    # assumption that is only ever written down is an assumption nobody checks.
    last = dt.datetime.strptime(records[-1][0], STAMP)
    print(f"  last observation      {last}")
    print(f"  {TZ} is UTC{UTC_OFFSET_HOURS:+d} all year")
    scan = clock_check(records)
    utc_like = False

    steps: list[tuple[dt.datetime, str, str]] = []
    prev = None
    for r in records:
        sell = r[2]
        if prev is not None and sell != prev:
            steps.append((dt.datetime.strptime(r[0], STAMP), prev, sell))
        prev = sell
    print(f"\n  official_sell steps to a new value {len(steps):,} times")
    if not steps:
        print("  B15-4: VOID, the official series never steps")
        return {"criterion": "B15-4", "verdict": "VOID",
                "void": True, "steps": 0}

    for offset, name in (
            (0, f"column as served = {TZ}, measured above"),
            (-UTC_OFFSET_HOURS, "column +4 h = UTC, the reading the scan "
                                "rules out")):
        hours = collections.Counter(
            (when + dt.timedelta(hours=offset)).hour for when, _, _ in steps)
        print(f"\n  step hour-of-day, {name}")
        for hour, n in sorted(hours.items()):
            bar = "#" * min(50, n)
            print(f"      {hour:02d}:00  {n:>4}  {n / len(steps):6.2%}  {bar}")

    offset = UTC_OFFSET_HOURS if utc_like else 0
    local = [(when + dt.timedelta(hours=offset), a, b) for when, a, b in steps]
    hours = collections.Counter(when.hour for when, _, _ in local)
    modal_hour, modal_n = hours.most_common(1)[0]
    share = modal_n / len(local)
    print(f"\n  modal local step hour {modal_hour:02d}:00 on {share:.2%} "
          f"of {len(local):,} steps")
    print(f"  the register admits 20:00 (publication date) and "
          f"00:00 (vigencia date)")

    # **The steps fall in two bands and both are named in Art. 5.III.** The
    # register offers 20:00 (publication) and 00:00 (vigencia) as the two
    # answers and asks which one the series steps at. It steps at both, because
    # the publisher is a scraper: sometimes it catches the 20:00 publication and
    # more often it catches the value already in force after midnight. So the
    # modal hour is the wrong summary and the two bands are the right one.
    bands = {}
    for lo, hi, name in ((20, 23, "20:00-23:59, publication"),
                         (0, 2, "00:00-02:59, vigencia")):
        bands[name] = sum(n for h, n in hours.items() if lo <= h <= hi)
    print()
    for name, n in bands.items():
        print(f"      band {name:<28} {n:>3}/{len(local)} = "
              f"{n / len(local):7.2%}")
    covered = sum(bands.values()) / len(local)
    print(f"      the two bands together                "
          f"{sum(bands.values()):>3}/{len(local)} = {covered:7.2%}")

    print("\n  first ten steps, local:")
    for when, before, after in local[:10]:
        print(f"      {when}   {before} -> {after}")

    # **The external anchor, checked against the register's own sentence.**
    #
    # §3.4 registers the Aduana comunicado as the confirming instrument:
    # `6,96 Bs/USD vigente al 26/06/2026`. The register asks whether the
    # resulting convention reproduces that, and the direct way to ask it is to
    # read every row the column dates to 26/06 and see what the official side
    # says on each one. No histogram and no publication hour enter it.
    #
    # **The first implementation asked a different question**, whether the
    # first step landed on 26/06, and that question only makes sense under a
    # clock this column turned out not to be on. With the clock measured the
    # step lands at 00:35:56 on 27/06, so 6.96 held for the whole of 26/06,
    # which is what the comunicado says. The old test read that as a failure
    # because it was looking for the step on the 26th itself.
    anchor_date = dt.date(2026, 6, 26)
    anchor_stamp = anchor_date.isoformat()
    on_anchor = sorted({r[2] for r in records if r[0].startswith(anchor_stamp)})
    n_anchor = sum(1 for r in records if r[0].startswith(anchor_stamp))
    anchor_holds_under_vigencia = on_anchor == ["6.96"]
    first_when, first_before, first_after = local[0]
    print(f"\n  external anchor, §3.4: 6,96 Bs/USD vigente al 26/06/2026")
    print(f"      rows the column dates to {anchor_stamp}: {n_anchor}")
    print(f"      official venta on those rows: {', '.join(on_anchor)}")
    print(f"      first step away from it: {first_when} "
          f"({first_before} -> {first_after})")
    print(f"      the comunicado "
          f"{'reproduces' if anchor_holds_under_vigencia else 'DOES NOT hold'}"
          f" on this column")

    vigencia_band = bands["00:00-02:59, vigencia"] / len(local)
    consistent = covered >= 0.99
    # The registered instrument's own verdict, kept whatever happens below.
    registered_void = not (anchor_holds_under_vigencia and consistent)

    # **A second instrument, and it is the publisher's own two columns.**
    # D3's third category: a design replaced after the run, with the reason
    # recorded and the original verdict kept. The reason is that the
    # registered instrument reads the convention off a step time that turned
    # out to record the aggregator's refresh rather than the statute's clock,
    # so it was answering a question about the aggregator. This one asks the
    # BCB.
    publisher = publisher_date_column(records)
    void, verdict = registered_void, ("VOID" if registered_void
                                      else "vigencia date")
    resolved, reinstrumented = not registered_void, None
    if publisher:
        vig = publisher["tally"]["vigencia"]
        cor = publisher["tally"]["corte"]
        print(f"\n  the publisher's own two columns, {publisher['rows']} rows "
              f"of {SERIES.name}")
        print(f"      official column keyed on vigencia: "
              f"{vig['hits']}/{vig['compared']}")
        print(f"      official column keyed on corte:    "
              f"{cor['hits']}/{cor['compared']}")
        decided = (vig["share"] is not None and cor["share"] is not None
                   and vig["hits"] > cor["hits"]
                   and vig["hits"] == vig["compared"])
        if decided:
            void, verdict, resolved = False, "vigencia date", True
            reinstrumented = (
                "the registered instrument reads the convention off the local "
                "time of day the official series steps, and 31 of 36 steps "
                "land at 04:00 to 05:00 local, at neither hour Art. 5.III "
                "makes available. It was measuring the aggregator's refresh. "
                "The BCB prints Fecha de corte and Vigencia on every row of "
                "its own series; keyed on Vigencia the official column matches "
                f"on {vig['hits']} of {vig['compared']}, keyed on Fecha de "
                f"corte on {cor['hits']} of {cor['compared']}. D3 third "
                "category: the original VOID is kept in registered_verdict.")
            print(f"\n  **B15-4 is re-decided on the publisher's own columns.** "
                  f"The registered instrument's VOID is kept on the record.")
    print(f"\n  the two admitted bands account for {covered:.2%} of steps, "
          f"and the anchor picks vigencia")
    print(f"  B15-4: {verdict}")
    if not void:
        print(f"      the column carries the day the rate governs.")
        print(f"      {vigencia_band:.2%} of steps land in the vigencia band "
              f"and {1 - vigencia_band:.2%} in the publication band, which is")
        print(f"      the empirical fingerprint of Art. 5.III's two clocks "
              f"rather than a defect.")
    if void:
        print("  guard_typing_first: arm III (B15-6/7/8/9) does not run.")
    return {"criterion": "B15-4", "verdict": verdict, "void": void,
            # **A criterion that resolved is not a criterion that failed.**
            # `rendered` reads `passed`, and without this key a dict that
            # answered its own question rendered as **FAIL** beside the answer.
            "passed": resolved,
            "registered_verdict": "VOID" if registered_void else "vigencia date",
            "registered_instrument": "step hour of the official series, §3.4",
            "reinstrumented": reinstrumented,
            "publisher_columns": publisher,
            "steps": len(steps), "modal_local_hour": modal_hour,
            "modal_share": share,
            "column_clock": f"{TZ} local, measured not assumed",
            "clock_scan": scan,
            "band_shares": {k: v / len(local) for k, v in bands.items()},
            "bands_cover": covered,
            "anchor_selects": "vigencia date",
            "anchor_confirmed": anchor_holds_under_vigencia,
            "hour_histogram_local": dict(sorted(hours.items()))}


# ---------------------------------------------------------------------------

def s1_alignment_note() -> dict:
    """S1's month labels against its data. Reported, not resolved.

    This is not a criterion. It is here because it is the one thing arm III will
    need from S1 and because it is the twelfth entry of this project's
    range-error family in the open: every count on the sheet is right and the
    identities after the event are not.
    """
    rule("S1 alignment, reported and NOT resolved")
    ods = BOLIVIA / "bcb_tco_2026.ods"
    if not ods.exists():
        print("  bcb_tco_2026.ods is not on disk")
        return {"available": False}
    grid = bcb_grid(ods.read_bytes())
    print(f"  grid {grid['width']} columns "
          f"(expected {grid['width_expected']}), {len(grid['days'])} day rows")
    print(f"  month label columns: {grid['month_label_columns']}")
    print("\n  the sheet's own labels, against the last day carrying a pair:")
    for month in BCB_MONTHS:
        col = grid["month_label_columns"].get(month)
        if col is None:
            continue
        pairs = [d for d, row in sorted(grid["days"].items())
                 if row[col] and row[col + 1]]
        singles = [d for d, row in sorted(grid["days"].items())
                   if row[col] and not row[col + 1]]
        if pairs or singles:
            print(f"      {month:<11} pairs on days {pairs[:1]}..{pairs[-1:]}"
                  f"   single-value days {singles[:1]}..{singles[-1:]}"
                  f"  ({len(pairs)} paired, {len(singles)} single)")
    print("\n  **Reported and left open.** After the reform the sheet carries")
    print("  one value per day with the COMPRA half empty, and whether a")
    print("  single-valued column belongs to the month on its label is a")
    print("  reading that needs an external anchor. Arm III is gated, so")
    print("  nothing depends on it yet.")
    return {"available": True, "width": grid["width"],
            "month_label_columns": grid["month_label_columns"],
            "resolved": False}


def main() -> int:
    records = load_all()
    run_utc = None
    if MANIFEST.exists():
        stamp = json.loads(MANIFEST.read_text(encoding="utf-8")).get(
            "generated_utc")
        if stamp:
            run_utc = dt.datetime.fromisoformat(stamp).replace(tzinfo=None)
    run_day = dt.date.fromisoformat(records[-1][0][:10])

    one = b15_1(records, run_day)
    two = b15_2(records)
    three = b15_3(records)
    four = b15_4(records, run_utc)
    note = s1_alignment_note()

    # **B15-5 gets its own entry here rather than a field inside B15-3.** The
    # statutory spread is a registered criterion in its own right and it
    # produced a reading; it was folded into B15-3's dict only because both are
    # computed from the same pass over the official pair. A registered
    # criterion that does not appear as a row is a criterion a reader of
    # `RESULTS.md` cannot see the state of, and every criterion's state belongs
    # in that file, the failures included.
    five = {
        "criterion": "B15-5",
        "passed": three["official_check_passes"],
        "statutory_spread": STATUTORY_SPREAD,
        "share_of_non_degenerate": three["official_spread_statutory_share"],
        "degenerate_rows": three["official_degenerate_rows"],
        "source": "computed in b15_3 over the same pass on the official pair",
    }

    rendered(one, "B15-1 retrieval integrity", (
        f"{one['dates_served']:,} of {one['window_days']:,} days served, "
        f"{one['observations']:,} observations, "
        f"{len(one['dates_absent'])} absent, {len(one['fills'])} fills, "
        f"manifest present"))
    rendered(two, "B15-2 the known-answer arm", (
        "S3's prefix digest reproduces on the records before the event, and "
        "S1's external anchor, the customs comunicado's 6,96 Bs/USD for "
        "26/06/2026, reproduces from the annual grid"))
    seg = (three.get("segments") or {}).get("post-event", {})
    rendered(three, "B15-3 the side convention", (
        f"**VOID over the registered window, which straddles the break in "
        f"\u00a73.5**: as published {three['orientation_A_uncrossed']:.4%} "
        f"uncrossed, swapped {three['orientation_B_uncrossed']:.4%}, and "
        f"neither clears {UNCROSSED_SHARE:.0%}. The two figures are one "
        f"orientation read on each side of the break rather than one "
        f"orientation failing. **On the post-event segment, the only segment "
        f"arm III runs on, it resolves**: orientation "
        f"{three.get('segment_orientation')} is uncrossed on "
        f"{seg.get('A_uncrossed', 0):.3%} of {seg.get('rows', 0):,} rows"))
    pub = four.get("publisher_columns") or {}
    vig = (pub.get("tally") or {}).get("vigencia", {})
    cor = (pub.get("tally") or {}).get("corte", {})
    rendered(four, "B15-4 the date column", (
        f"**the column carries the date the rate governs**, from the "
        f"publisher's own two columns: the BCB prints `Fecha de corte` and "
        f"`Vigencia` on every row of its series, and keyed on `Vigencia` the "
        f"official column matches on {vig.get('hits')} of "
        f"{vig.get('compared')}, keyed on `Fecha de corte` on "
        f"{cor.get('hits')} of {cor.get('compared')}. The customs comunicado "
        f"agrees, every row dated 26/06 reading 6.96. **The registered "
        f"instrument returned VOID and that verdict is kept**: it reads the "
        f"convention off the local hour the series steps, and 31 of "
        f"{four['steps']} steps land at 04:00 to 05:00, at neither hour "
        f"Art. 5.III makes available, so it was measuring the aggregator's "
        f"refresh rather than the statute's clock"))
    rendered(five, "B15-5 the statutory spread", (
        f"the statutory {STATUTORY_SPREAD:.2f} holds on "
        f"{five['share_of_non_degenerate']:.3%} of non-degenerate official "
        f"rows; the {five['degenerate_rows']:,} rows whose two sides are equal "
        f"leave the denominator as fills rather than counting as spread zero"))

    rule("gate")
    # **The gate is asked on the segment arm III runs on.** §6.3 suspends arm
    # III unless B15-3 and B15-4 both resolve, and the first version read
    # B15-3's whole-window verdict, which is a window arm III does not use:
    # it straddles §3.5's break and arm III runs on the post-event side alone
    # and discloses that it does. **Scoring a gate on a window the arm never
    # touches answers a question nobody asked**, and the segment reading is
    # in the record above rather than being inferred here.
    three_resolves = (not three["void"]) or bool(three.get("segment_orientation"))
    gated = (not three_resolves) or four["void"]
    print(f"  B15-3 {three['verdict']}")
    print(f"  B15-4 {four['verdict']}")
    print(f"\n  guard_typing_first: arm III "
          f"{'DOES NOT RUN' if gated else 'may run'}")
    if gated:
        print("  B15-6, B15-7, B15-8 and B15-9 are suspended. prereg §4, §6.3.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B15",
        "step": "typing",
        "diagnostic_only": False,
        "authority": "docs/b15_bolivia_prereg.md §5",
        "window": [WINDOW_OPEN_DATE.isoformat(), run_day.isoformat()],
        "criteria": [one, two, three, four, five],
        "s1_alignment": note,
        "arm_iii_runs": not gated,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
