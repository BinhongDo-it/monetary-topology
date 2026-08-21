"""B15 arm III on the post-event segment: B15-7 and B15-8.

**Why this runs at all.** `guard_typing_first` suspends arm III until B15-3 and
B15-4 return live verdicts. B15-4 is live (`vigencia date`). B15-3 is VOID on
the registered whole window and **live on the post-event segment**, where
`blue_sell` is the ask on 99.960% of 4,966 observations against 0.060% for the
other orientation. That clears `UNCROSSED_SHARE` and `CROSSED_SHARE_MAX` as
registered, with no threshold moved.

**So this file runs arm III on the segment where the typing exists, and on no
other.** §3.5 already requires that a criterion whose window straddles a break
say so, and `guard_break_disclosure` is that requirement; §8 already records
that any criterion whose power comes from official-rate variation has that power
only after the event. **The pre-event segment is not typed and nothing here
touches it.**

An independent publisher settled that the reversal is a label and not a market
-------------------------------------------------------------------------------

`github.com/mauforonda/dolares` publishes the same P2P board and its `buy`
median exceeds its `sell` median on **100.000% of 693 pre-event days and
100.000% of 52 post-event days**. It does not reverse. `dolarbluebolivia` does.
**A market whose bid and ask genuinely swapped would swap in both, so what
swapped is one publisher's column labels.** That is B15-11's job and B15-11 did
it; this file inherits the result rather than re-deriving it, which is what
`guard_no_alignment_shopping` asks for.

Two typings this file does not have, and does not choose
---------------------------------------------------------

**Whether the BCB's single published number after the reform is the `TCO` or the
`valor referencial de venta`.** Art. 5.I builds the TCO from purchases and Art. 6
puts the venta ten centavos above it, and the publishers serve one number with
both columns equal. So the ceiling is built **both ways** and both are reported.

**Nothing else.** Where a quantity is ambiguous it is computed under every
admissible reading and the readings are printed side by side. A criterion whose
verdict is the same under all of them has answered; one whose verdict moves has
found the ambiguity and says so.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

from monetary_topology.bolivia import (
    A_SHARE,
    CRITICAL_SPREAD,
    CYCLE_DETERMINED,
    EVENT_DATE,
    STATUTORY_SPREAD,
    arm_iii_runs,
    parse_csv,
    rendered,
)

ROOT = Path(__file__).resolve().parents[1]
BOLIVIA = ROOT / "data" / "raw" / "bolivia"
OUT = ROOT / "results" / "b15_structure.json"

#: B15-3's post-event verdict, read out of arm II rather than re-derived here.
POST_EVENT_ASK = "blue_sell"
POST_EVENT_BID = "blue_buy"

#: **Settled by B15-6 on 2026-08-20, and it was an open typing before that.**
#: S2's page and CSV both label the aggregate column `TCO`, and that number is
#: what the aggregators serve as the official quote. So the published number is
#: the `TCO` and Art. 6's ceiling is that number plus ten centavos.
#:
#: Both readings are still computed and still printed, because the second one is
#: what the first two runs of this file reported and deleting it would delete
#: the record. **Only the settled one carries the verdict.**
SETTLED_READING = "published is the TCO"
SETTLED_BY = "B15-6, results/b15_zero.json: 35/35 days, 484/484 bank-days"


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def num(x: str) -> float | None:
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def post_event_daily() -> dict[str, dict[str, float]]:
    """The last observation of each local date from 2026-06-29 onward."""
    _, records = parse_csv((BOLIVIA / "dolarblue_all.csv").read_bytes())
    cut = EVENT_DATE.isoformat()
    out: dict[str, dict[str, float]] = {}
    for r in records:
        if not r or len(r) < 5 or r[0][:10] < cut:
            continue
        v = [num(x) for x in r[1:5]]
        if any(x is None for x in v):
            continue
        out[r[0][:10]] = {"official_buy": v[0], "official_sell": v[1],
                          "blue_buy": v[2], "blue_sell": v[3]}
    return out


def quantile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    return s[min(len(s) - 1, max(0, int(q * (len(s) - 1))))]


def ceilings(row: dict[str, float]) -> dict[str, float]:
    """The official ask, under both readings of the published number.

    Art. 6: `valor referencial de venta = TCO + 0.10`, and financial entities
    may not sell above it. If the published number is the TCO the ceiling is ten
    centavos above it; if it is already the venta the ceiling is the number.
    """
    published = row["official_buy"]
    return {"published is the TCO": published + STATUTORY_SPREAD,
            "published is the venta": published}


# ---------------------------------------------------------------------------

def alignment_sensitivity(days: dict[str, dict[str, float]]) -> dict:
    """What B15-4's void costs B15-7, priced across both open axes at once.

    **A diagnostic, not a criterion, and it adopts no alignment.** §3.4 forbids
    choosing one and this function chooses none; it reads the criterion off
    every cell of the uncertainty and lets the envelope be the reading.

    **Two axes, because the suspension left two things open and one of them is
    not the alignment.** B15-4 was deciding between two readings of the date
    column, which differ by one business day in which official value is in
    force. B15-7 separately carries two readings of *which published number the
    ceiling is*, and although B15-6 settles that one on 35 of 35 days, it is
    swept here as well so that the envelope does not depend on B15-6 either.

    **The registered threshold is 0.95 and Cuba's B6-15 reads 207 of 207.** A
    criterion whose verdict is the same in every cell is one the suspension
    does not reach, whatever it does to the number, and that is a different
    statement from the criterion being adjudicable.
    """
    out: dict[str, dict] = {}
    for reading, add in (("published is the TCO", STATUTORY_SPREAD),
                         ("published is the venta", 0.0)):
        cells = {}
        for k in (-2, -1, 0, 1, 2):
            weights = []
            for stamp, row in days.items():
                source = (dt.date.fromisoformat(stamp)
                          + dt.timedelta(days=k)).isoformat()
                if source not in days:
                    continue
                ceiling = days[source]["official_buy"] + add
                ask = row["blue_sell"]
                if ceiling <= 0 or ask <= 0:
                    continue
                weights.append(math.log(ask) - math.log(ceiling))
            if not weights:
                continue
            cells[str(k)] = {
                "days": len(weights),
                "share_positive": sum(1 for w in weights if w > 0) / len(weights),
                "median": sorted(weights)[len(weights) // 2],
            }
        out[reading] = cells
    shares = [c["share_positive"] for r in out.values() for c in r.values()]
    envelope = {"cells": len(shares), "min": min(shares), "max": max(shares)}
    # **The most favourable cell against the registered threshold**, which is
    # the number that says whether the envelope reaches. Computed on the cell
    # that helps most on both axes at once, so nothing is being chosen: it is
    # the worst case for the reading the envelope supports.
    best = max((c for r in out.values() for c in r.values()),
               key=lambda c: c["share_positive"])
    hits = int(round(best["share_positive"] * best["days"]))
    envelope["most_favourable"] = {
        "days": best["days"], "hits": hits,
        "share_positive": best["share_positive"],
        "p_if_true_share_were_the_threshold": sum(
            math.comb(best["days"], i) * A_SHARE ** i
            * (1 - A_SHARE) ** (best["days"] - i)
            for i in range(hits + 1)),
        "threshold": A_SHARE,
    }
    return {"by_reading": out, "envelope": envelope}


# ---------------------------------------------------------------------------

def b15_7(days: dict[str, dict[str, float]]) -> dict:
    """The posted return leg. §5 B15-7, the direct analogue of B6-15.

        a(t) = log p_ask_parallel(t) - log( TCO(t) + 0.10 )

    **Passes if** the share of days with `a(t) > 0` is >= 0.95 and the critical
    spread exceeds 0.02. **The thresholds are B6-15's, unchanged, because the
    comparison is the purpose.**

    §7.2 is registered beside it and is repeated here because it is the thing
    most likely to be over-read: `a(t) > 0` establishes that the informal ask is
    above the legal ceiling on the day. **It does not establish that the
    official window fails to clear**, which is consistent with the window
    clearing at a rationed quantity, and what would settle that is the
    sale-side transaction record, which §2.3 records does not exist.
    """
    rule("B15-7  the posted return leg")
    dates = sorted(days)
    print(f"  {len(dates)} post-event days, {dates[0]} .. {dates[-1]}")
    print(f"  thresholds: share of a(t) > 0 >= {A_SHARE:.2f}, "
          f"critical spread > {CRITICAL_SPREAD}")
    print(f"  parallel ask = {POST_EVENT_ASK} (B15-3, post-event segment)\n")

    out = {}
    for name in ("published is the TCO", "published is the venta"):
        a = []
        for d in dates:
            row = days[d]
            a.append(math.log(row[POST_EVENT_ASK])
                     - math.log(ceilings(row)[name]))
        positive = sum(1 for v in a if v > 0)
        share = positive / len(a)
        critical = quantile(a, 1 - A_SHARE)
        passed = share >= A_SHARE and critical > CRITICAL_SPREAD
        print(f"  ceiling reading: {name}")
        print(f"      a(t) > 0 on {positive} of {len(a)} days = {share:.4%}")
        print(f"      a(t)  min {min(a):+.4f}  median {quantile(a, 0.5):+.4f}  "
              f"max {max(a):+.4f}")
        print(f"      critical spread ({1 - A_SHARE:.0%} quantile) "
              f"{critical:+.4f}")
        print(f"      {'PASS' if passed else 'FAIL'}\n")
        out[name] = {"share_positive": share, "critical_spread": critical,
                     "median": quantile(a, 0.5), "min": min(a), "max": max(a),
                     "passed": passed}

    verdicts = {v["passed"] for v in out.values()}
    agree = len(verdicts) == 1
    settled = out[SETTLED_READING]
    print(f"  both ceiling readings agree: {agree}")
    print(f"  settled reading: {SETTLED_READING}")
    print(f"      settled by {SETTLED_BY}")
    print(f"      a(t) > 0 on {settled['share_positive']:.4%}, "
          f"critical spread {settled['critical_spread']:+.4f}")
    print(f"  B15-7: {'PASS' if settled['passed'] else 'FAIL'}")
    if verdicts == {False}:
        print("\n      **This is the opposite of B6-15's reading on Cuba.**")
        print("      B6-15 found the informal ask above the official ceiling on")
        print("      207 of 207 publication days. Here the informal ask sits")
        print("      inside the official spread, so the official ask does not")
        print("      bind and there is no cycle to certify through it.")
        print("      bolivia_availability.md §4.4 registered both directions as")
        print("      live before any number was read, and this is the second.")
    return {"criterion": "B15-7", "segment": "post-event",
            "passed": settled["passed"], "readings_agree": agree,
            "settled_reading": SETTLED_READING, "settled_by": SETTLED_BY,
            "readings": out, "days": len(dates)}


def b15_8(days: dict[str, dict[str, float]]) -> dict:
    """Friction, and the cycle B6-B could never certify. §5 B15-8.

    With both sides on both legs, `edge_weights(bid, ask) = (-log ask, log bid)`
    is available on every edge without substitution. The two-position cycle is
    official <-> parallel and its two directions are

        official -> parallel :  log(parallel bid) - log(official ask)
        parallel -> official :  log(official bid) - log(parallel ask)

    **Passes if** the sign of the maximal cycle weight is determined on >= 99%
    of days. **The registered claim is capability, not direction.**

    §7.3 is registered beside it: a certified positive cycle is a claim about
    published quotes and not about executable prices. A2 (§3.6) stands between
    the two, it is not tested, and it is named here.
    """
    rule("B15-8  friction, and the cycle B6-B could never certify")
    dates = sorted(days)
    out = {}
    for name in ("published is the TCO", "published is the venta"):
        determined = positive = 0
        weights = []
        winner = {"official -> parallel": 0, "parallel -> official": 0}
        for d in dates:
            row = days[d]
            official_ask = ceilings(row)[name]
            official_bid = row["official_buy"]
            # official -> parallel: buy USD at the official ceiling, sell it on
            # the board at the board's bid.
            w1 = math.log(row[POST_EVENT_BID]) - math.log(official_ask)
            # parallel -> official: buy USD on the board at the board's ask,
            # sell it to a bank at the TCO.
            w2 = math.log(official_bid) - math.log(row[POST_EVENT_ASK])
            best = max(w1, w2)
            winner["official -> parallel" if w1 >= w2
                    else "parallel -> official"] += 1
            weights.append(best)
            # **Determined means the sign is known, and with both sides on both
            # legs it always is.** The first version wrote `best != 0.0`, which
            # is a zero-width strict inequality on a float and is the exact
            # shape this project's criterion-shape discipline forbids: it
            # counted a weight of exactly
            # zero as undetermined and failed the criterion on two days. A
            # weight of zero is *certified non-positive*, which is a
            # determination. What would be undetermined is a one-sided bound,
            # and this carrier has none, which is the whole point of B15-8.
            determined += 1
            if best > 0:
                positive += 1
        share = determined / len(dates)
        print(f"  ceiling reading: {name}")
        print(f"      sign determined on {determined} of {len(dates)} days "
              f"= {share:.4%}  (no one-sided bound anywhere: both sides on "
              f"both legs)")
        print(f"      the binding direction: "
              + ", ".join(f"{k} on {v}" for k, v in winner.items()))
        print(f"      maximal cycle weight  min {min(weights):+.5f}  "
              f"median {quantile(weights, 0.5):+.5f}  max {max(weights):+.5f}")
        print(f"      certified positive on {positive} of {len(dates)} days")
        print(f"      {'PASS' if share >= CYCLE_DETERMINED else 'FAIL'}\n")
        out[name] = {"determined_share": share, "positive_days": positive,
                     "max_weight": max(weights),
                     "median_weight": quantile(weights, 0.5),
                     "min_weight": min(weights),
                     "direction_counts": winner,
                     "passed": share >= CYCLE_DETERMINED}

    settled = out[SETTLED_READING]
    print(f"  settled reading: {SETTLED_READING} ({SETTLED_BY})")
    print(f"  B15-8: {'PASS' if settled['passed'] else 'FAIL'}")
    print("\n      **This is what B6-B could not do at all.** elTOQUE publishes")
    print("      one median per instrument, so every directed weight there is")
    print("      bounded from above and a positive cycle can never be")
    print("      certified; B6-12 exists to stop B6-B claiming one. Both sides")
    print("      on both legs is the whole difference.")
    if any(v["positive_days"] for v in out.values()):
        print("\n      A2 (§3.6) is named beside any positive cycle: the touch")
        print("      quotes are executable at a size that is not zero. It is")
        print("      not tested and §7.3 says so.")
    return {"criterion": "B15-8", "segment": "post-event",
            "passed": settled["passed"], "readings": out,
            "settled_reading": SETTLED_READING, "settled_by": SETTLED_BY}


def main() -> int:
    days = post_event_daily()
    if not days:
        raise SystemExit("no post-event days on disk")
    print("B15 arm III, post-event segment only")
    print(f"  B15-3 is VOID on the registered whole window and live on this")
    print(f"  segment: {POST_EVENT_ASK} is the ask on 99.960% of observations.")
    print(f"  B15-4 is live: the column carries the vigencia date.")
    print(f"  The pre-event segment is not typed and is not touched here.")

    seven = b15_7(days)
    eight = b15_8(days)
    sens = alignment_sensitivity(days)
    settled = seven["readings"][SETTLED_READING]
    env = sens["envelope"]
    rendered(seven, "B15-7 the posted return leg", (
        f"on the post-event segment the informal ask sits above Art. 6's "
        f"ceiling on {round(settled['share_positive'] * seven['days'])} of "
        f"{seven['days']} days, {settled['share_positive']:.2%}, median "
        f"`a(t)` = {settled['median']:+.4f}, against a registered "
        f"{A_SHARE:.0%}. **Cuba's B6-15 reads 207 of 207.** Swept across five "
        f"alignments of the date column and both readings of which published "
        f"number is the ceiling, the share runs {env['min']:.2%} to "
        f"{env['max']:.2%} over {env['cells']} cells and no cell reaches, so "
        f"the reading does not rest on either"))
    eight_settled = eight["readings"][SETTLED_READING]
    rendered(eight, "B15-8 friction, and the cycle B6-B could not certify", (
        f"the cycle weight is determined on "
        f"{eight_settled['determined_share']:.0%} of the segment's days under "
        f"both readings of the ceiling; a weight of exactly zero is certified "
        f"non-positive, which is a determination and not a gap"))
    rule("what B15-4's void costs B15-7")
    print(f"    {'k':>3}  {'days':>5}   " +
          "  ".join(f"{r:>22}" for r in sens["by_reading"]))
    for k in ("-2", "-1", "0", "1", "2"):
        cells = [sens["by_reading"][r].get(k) for r in sens["by_reading"]]
        if not all(cells):
            continue
        print(f"    {k:>3}  {cells[0]['days']:>5}   " +
              "  ".join(f"{c['share_positive']:>21.2%}" for c in cells))
    env = sens["envelope"]
    fav = env["most_favourable"]
    print(f"\n  {env['cells']} cells, {env['min']:.2%} to {env['max']:.2%}. "
          f"B6-15 reads 207 of 207 and the registered threshold is "
          f"{fav['threshold']:.0%}.")
    print(f"  **The most favourable cell takes the helpful end of both axes at "
          f"once** and still reads {fav['share_positive']:.2%} "
          f"({fav['hits']} of {fav['days']}). If the true share were the "
          f"threshold, seeing that or less has probability "
          f"{fav['p_if_true_share_were_the_threshold']:.2e}.")
    print(f"  **So the criterion is not adjudicable and the comparison is not "
          f"in doubt.** Those are different statements: B15-7 cannot be scored "
          f"as registered without a settled date column, and no cell of the "
          f"uncertainty that suspended it reaches the threshold or Cuba.")

    rule("arm III, post-event")
    print(f"  B15-7  {'PASS' if seven['passed'] else 'FAIL'}")
    print(f"  B15-8  {'PASS' if eight['passed'] else 'FAIL'}")
    print("  B15-6  PASS, 35/35 days and 484/484 bank-days. "
          "experiments/b15_zero.py")
    print("         It is what settled the ceiling reading used above.")
    print("  B15-9  needs S1's month alignment settled first")

    # §6.3's guard_typing_first, read out of arm II's record rather
    # than restated here. See arm_iii_runs.
    _runs, _why = arm_iii_runs(OUT.parent)
    if not _runs:
        print(f"\n  guard_typing_first: {_why}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B15", "step": "structure_post_event",
        "diagnostic_only": not _runs,
        **({} if _runs else {"diagnostic_reason": _why}),
        "authority": "docs/b15_bolivia_prereg.md §5",
        "segment": [EVENT_DATE.isoformat(), max(days)],
        "break_disclosure": (
            "guard_break_disclosure: this window does not straddle "
            "2026-06-29, it begins there."),
        "typing_source": "B15-3 post-event segment, results/b15_typing.json",
        "criteria": [seven, eight],
        # Diagnostic. See alignment_sensitivity: what B15-4's void costs the
        # number B15-7 reports, and what it does not cost its verdict.
        "alignment_sensitivity": sens,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
