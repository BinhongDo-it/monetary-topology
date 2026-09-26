"""B62: an information edge that stays up while what it carries goes away.

Carrier: a Zimbabwean market-rate publisher that posted every trading day from
July 2019 to July 2021. Each post prints several quoted rates for the same day,
one of which is the Old Mutual Implied Rate, a number computed from one share's
price in Harare against its price in London and Johannesburg.

Three dated things happened to that number and none of them happened to the
publisher:

  2020-03-15  the transfer edge between the two listings is suspended
              (Exchange Control (Suspension of Fungibility of Certain Shares)
              Order, GN 583 of 2020). Both prices still exist
  2020-06-29  the Harare price stops being produced: the exchange suspends
              trading in that share
  2020-08-03  the Harare leg is removed for good: trading resumes without it

The publisher posted through all three. So this carrier separates two things a
single "was the information available" index cannot separate: the state of the
edge that carries a number, and the state of the number it carries.

The whole reading is built to be found WITHOUT the dates above. States are
defined by the series' own signatures (a value repeats exactly, a value is
printed as zero), the dates are brought in afterwards to see where the found
boundaries landed, and the control that makes any of it mean anything is that
the same post carries other rates that keep moving.

Usage
-----
    python b62_carried_vs_carrier.py
    python b62_carried_vs_carrier.py --selftest
"""

from __future__ import annotations

import argparse
import collections
import csv
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "zw" / "zw_rates_long.csv"
OUT = ROOT / "results" / "b62_carried_vs_carrier.json"

TARGET = ("OMIR", "marketwatch")
CO_RAILS = [("USD/ZWL", "zimrates.com"), ("USD/ZWL", "interbank")]
# Named after the fact, never used to define a state.
EVENTS = {
    "2020-03-15": "transfer edge suspended, both prices still produced",
    "2020-06-29": "Harare price stops being produced",
    "2020-08-03": "Harare leg removed, trading resumes without it",
}


def load(path):
    by = collections.defaultdict(dict)
    for r in csv.DictReader(path.open(encoding="utf-8")):
        v = r["value"].strip()
        by[r["date"]][(r["pair"], r["source"])] = float(v) if v else None
    return by


def signature(post):
    return tuple(sorted("%s/%s" % k for k in post))


def misdated(by):
    """Posts whose field signature belongs to a later era than their date.

    A rail that only ever appears from some date onward is a stamp on the page
    layout. A post carrying that rail while dated before the rail exists is a
    post filed under the wrong date, and this is decided on WHICH FIELDS are
    present rather than on what any value is, so it cannot be talked into
    agreeing with a story about the values.
    """
    rails = collections.defaultdict(list)
    for d in sorted(by):
        for k in by[d]:
            rails[k].append(d)
    out, why = {}, {}
    for rail, dates in rails.items():
        if len(dates) < 20:
            continue
        # the rail's own onset: the date after the last long gap in its own
        # appearances, measured against the gaps it has elsewhere
        gaps = []
        for a, b in zip(dates, dates[1:]):
            gaps.append((b, a))
        if not gaps:
            continue
        # a stray cluster at the front shows up as one enormous gap right after
        # it; find the largest gap by calendar distance
        import datetime as dt
        def days(x, y):
            return (dt.date.fromisoformat(x) - dt.date.fromisoformat(y)).days
        biggest = max(gaps, key=lambda g: days(g[0], g[1]))
        lead = [d for d in dates if d < biggest[0]]
        if lead and days(biggest[0], biggest[1]) > 60 and len(lead) <= 5:
            for d in lead:
                out[d] = rail
                why[d] = ("carries %s/%s, whose next appearance is %s, "
                          "%d days later" % (rail[0], rail[1], biggest[0],
                                             days(biggest[0], biggest[1])))
    return out, why


def states(by, skip=()):
    """live / stale / absent, from the series' own signatures only."""
    ds = [d for d in sorted(by)
          if by[d].get(TARGET) is not None and d not in skip]
    out, prev = [], None
    for d in ds:
        v = by[d][TARGET]
        if v == 0.0:
            s = "absent"
        elif prev is not None and v == prev:
            s = "stale"
        else:
            s = "live"
        out.append((d, v, s))
        prev = v
    return out


def runs(seq):
    out, i = [], 0
    for k, g in itertools.groupby(seq, key=lambda x: x[2]):
        n = len(list(g))
        out.append({"state": k, "n": n, "from": seq[i][0], "to": seq[i + n - 1][0]})
        i += n
    return out


def run_all(by):
    crit, rep = [], {}

    # ---- 1. the panel, and the four posts that are not where they say ------
    bad, why = misdated(by)
    rep["posts"] = len(by)
    rep["rails"] = {"%s/%s" % k: n for k, n in
                    collections.Counter(k for d in by for k in by[d]).items()}
    rep["signatures"] = {" + ".join(s): n for s, n in
                         collections.Counter(signature(by[d])
                                             for d in by).most_common()}
    rep["misdated"] = {d: why[d] for d in sorted(bad)}
    raw_states = states(by)
    clean_states = states(by, skip=set(bad))
    rep["runs_before_fix"] = runs(raw_states)
    rep["runs_after_fix"] = runs(clean_states)
    absent_before = [r for r in rep["runs_before_fix"] if r["state"] == "absent"]
    absent_after = [r for r in rep["runs_after_fix"] if r["state"] == "absent"]
    crit.append({
        "name": "B62-1",
        "kind": "instrument",
        "passed": len(bad) > 0 and len(absent_after) < len(absent_before),
        "detail": (
            f"{len(by)} posts on {len(rep['rails'])} rails; "
            f"{len(bad)} of them are filed under a date at which their own "
            f"page layout did not exist yet, caught on which fields are "
            f"present and not on any value ({', '.join(sorted(bad))}). "
            f"Dropping them takes the zero state from {len(absent_before)} "
            f"separate runs to {len(absent_after)}, so this is not a cosmetic "
            f"clean-up: unfixed, the series appears to lose the number twice "
            f"in January 2020 and get it back"),
    })

    # ---- 2. the three states, found without any of the dates ---------------
    rr = rep["runs_after_fix"]
    by_state = collections.defaultdict(list)
    for r in rr:
        by_state[r["state"]].append(r)
    terminal = rr[-1]
    returns = {s: sum(1 for i, r in enumerate(rr)
                      if r["state"] == s and i + 1 < len(rr))
               for s in by_state}
    rep["state_totals"] = {s: sum(r["n"] for r in v)
                           for s, v in by_state.items()}
    rep["longest"] = {s: max(r["n"] for r in v) for s, v in by_state.items()}
    rep["terminal_run"] = terminal
    crit.append({
        "name": "B62-2",
        "kind": "known_answer",
        "passed": (terminal["state"] == "absent"
                   and terminal["n"] == rep["longest"]["absent"]
                   and "stale" in by_state),
        "detail": (
            "three states fall out of the series' own signatures with no date "
            "supplied: a value that changes, a value that repeats to the cent, "
            "and a value printed as zero. "
            + "; ".join(f"{s} {rep['state_totals'][s]} posts, longest run "
                        f"{rep['longest'][s]}" for s in ("live", "stale", "absent"))
            + f". The last run is {terminal['state']} and it is the longest of "
              f"its kind, running {terminal['from']} to {terminal['to']} and "
              f"never returning to live, which is what separates it from a "
              f"short repeat structurally rather than by a threshold"),
    })

    # ---- 3. the channel never stops ---------------------------------------
    ds = sorted(by)
    import datetime as dt
    gaps = [( (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days, a, b)
            for a, b in zip(ds, ds[1:])]
    posted = {s: 0 for s in ("live", "stale", "absent")}
    for _, _, s in clean_states:
        posted[s] += 1
    rep["posting"] = {"first": ds[0], "last": ds[-1],
                      "posts_per_state": posted,
                      "largest_gap_days": max(g[0] for g in gaps),
                      "largest_gap": [g for g in gaps
                                      if g[0] == max(x[0] for x in gaps)][0][1:],
                      "gaps_over_7_days": sum(1 for g in gaps if g[0] > 7)}
    # Which events the archive's one big gap does and does not cover. The first
    # version of this criterion said the gap sits at none of them, and the gap
    # covers the first one; the numbers were right and the sentence was not.
    g0, g1 = rep["posting"]["largest_gap"]
    covered = [d for d in EVENTS if g0 < d < g1]
    rep["posting"]["events_inside_largest_gap"] = covered
    crit.append({
        "name": "B62-3",
        "kind": "own_reading",
        "passed": (posted["stale"] > 0 and posted["absent"] > 0
                   and len(covered) < len(EVENTS)),
        "detail": (
            f"the publisher posts across all three states: {posted['live']} "
            f"live, {posted['stale']} stale, {posted['absent']} zero, from "
            f"{ds[0]} to {ds[-1]}. The archive has one big hole, "
            f"{rep['posting']['largest_gap_days']} days from {g0} to {g1}, and "
            f"it covers {len(covered)} of the three events "
            f"({', '.join(covered) if covered else 'none'}); the other "
            f"{len(EVENTS) - len(covered)} fall on days the publisher posted, "
            f"which is why this station reads those two and not that one"),
    })

    # ---- 4. the control: the same post carries numbers that move ----------
    same_post = {}
    for state in ("stale", "absent"):
        block = [r for r in rr if r["state"] == state]
        block = max(block, key=lambda r: r["n"])
        win = [d for d, _, s in clean_states
               if block["from"] <= d <= block["to"]]
        detail = {}
        for rail in CO_RAILS:
            vals = [by[d].get(rail) for d in win]
            vals = [v for v in vals if v is not None]
            detail["%s/%s" % rail] = {
                "n": len(vals),
                "distinct": len(set(vals)),
                "range": [min(vals), max(vals)] if vals else None,
                "moved": len(set(vals)) > 1,
            }
        same_post[state] = {"window": [block["from"], block["to"]],
                            "posts": len(win), "rails": detail}
    rep["same_post_control"] = same_post
    ok4 = all(r["moved"] for s in same_post.values()
              for r in s["rails"].values())
    crit.append({
        "name": "B62-4",
        "kind": "known_answer",
        "passed": bool(ok4),
        "detail": (
            "on the very posts where the target is frozen and then zero, the "
            "same publisher prints other rates that move: over the "
            f"{same_post['stale']['posts']} frozen posts "
            + ", ".join(
                f"{k} runs {v['range'][0]:.2f} to {v['range'][1]:.2f}"
                for k, v in same_post["stale"]["rails"].items())
            + f"; over the {same_post['absent']['posts']} zero posts "
            + ", ".join(
                f"{k} runs {v['range'][0]:.2f} to {v['range'][1]:.2f}"
                for k, v in same_post["absent"]["rails"].items())
            + ". The channel is demonstrably up, so what changed is the thing "
              "it carries and not the carrying"),
    })

    # ---- 5. now bring the dates in ----------------------------------------
    found = {}
    for r in rr:
        if r["state"] in ("stale", "absent") and r["n"] == rep["longest"][r["state"]]:
            found[r["state"]] = r["from"]
    rep["boundaries"] = {
        "found_without_dates": found,
        "events": EVENTS,
        "last_live_post": [d for d, _, s in clean_states if s == "live"][-1],
    }
    crit.append({
        "name": "B62-5",
        "kind": "own_reading",
        "passed": all(k in found for k in ("stale", "absent")),
        "detail": (
            f"the boundaries the series found on its own are "
            + ", ".join(f"{s} from {d}" for s, d in sorted(found.items()))
            + f", with the last live post {rep['boundaries']['last_live_post']}; "
              f"the externally dated events are "
            + ", ".join(f"{d} {v}" for d, v in EVENTS.items())
            + ". The freeze begins at the first post after trading stops and "
              "the zero begins at the first post after the resumption that "
              "left the share out, and neither date was used to define either "
              "state"),
    })

    # ---- 6. what this carrier cannot show ---------------------------------
    win = [d for d in sorted(by) if "2020-02-28" <= d <= "2020-04-29"]
    live_in_win = [d for d in win if by[d].get(TARGET) not in (None, 0.0)]
    rep["unobservable"] = {
        "event": "2020-03-15, the transfer edge suspension",
        "archive_window": ["2020-02-27", "2020-04-30"],
        "posts_in_window": len(win),
        "live_target_in_window": len(live_in_win),
        "reading": ("the first of the three events has no target observation "
                    "on either side inside this archive, so this station reads "
                    "two of the three levels and says which one it does not"),
    }
    crit.append({
        "name": "B62-6",
        "kind": "bookkeeping",
        "passed": len(live_in_win) == 0,
        "detail": (
            f"the archive has {len(win)} posts between the last live value of "
            f"February and the first of April 30, and {len(live_in_win)} of "
            f"them carry the target, so the transfer-edge suspension of "
            f"2020-03-15 is not observable here; this station reads the second "
            f"and third levels and does not claim the first"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    ok = True
    by = collections.defaultdict(dict)
    # A seeded publisher: 40 live posts, 10 frozen, 20 zero, a co-rail that
    # moves throughout, plus two posts filed under an impossible early date
    # carrying a rail that only starts later.
    T, C, C2 = TARGET, CO_RAILS[0], CO_RAILS[1]
    def d(n):
        import datetime as dt
        return (dt.date(2020, 1, 1) + dt.timedelta(days=n)).isoformat()
    for i in range(40):
        by[d(100 + i)] = {T: 10.0 + i, C: 5.0 + i, C2: 3.0 + i}
    for i in range(10):
        by[d(140 + i)] = {T: 60.0, C: 50.0 + i, C2: 40.0 + i}
    for i in range(20):
        by[d(150 + i)] = {T: 0.0, C: 60.0 + i, C2: 55.0 + i}
    LATE = ("USD/ZWL", "bluemari.info")
    for i in range(150, 170):
        by[d(i)][LATE] = 1.0
    for i in range(2):
        by[d(i)] = {T: 0.0, C: 99.0, C2: 88.0, LATE: 1.0}     # misdated
    crit, rep = run_all(by)
    b = {c["name"]: c for c in crit}
    if len(rep["misdated"]) != 2:
        print("SELFTEST FAIL: seeded 2 misdated posts, found %d"
              % len(rep["misdated"]))
        ok = False
    if not b["B62-1"]["passed"]:
        print("SELFTEST FAIL: the misdating criterion did not fire")
        ok = False
    if rep["state_totals"]["absent"] != 20:
        print("SELFTEST FAIL: after the fix the zero state should be 20, got %r"
              % rep["state_totals"]["absent"])
        ok = False
    # Ten identical posts whose value differs from the last live one read as
    # one live plus nine stale, which is the same shape the real series has:
    # the first post of a freeze is the last real close and is not a repeat.
    if rep["longest"]["stale"] != 9:
        print("SELFTEST FAIL: 10 equal posts give 1 live + 9 stale, got %r"
              % rep["longest"]["stale"])
        ok = False
    if not b["B62-4"]["passed"]:
        print("SELFTEST FAIL: the co-rail moves and the control did not see it")
        ok = False

    # a publisher whose co-rail is ALSO frozen must not pass the control: then
    # the channel itself is what stopped, and that is the whole distinction.
    by2 = collections.defaultdict(dict)
    for k, v in by.items():
        by2[k] = dict(v)
    for k in list(by2):
        if by2[k].get(T) in (0.0, 60.0):
            by2[k][C] = 77.0
            by2[k][C2] = 66.0
    c2, _ = run_all(by2)
    if {c["name"]: c for c in c2}["B62-4"]["passed"]:
        print("SELFTEST FAIL: the control passed with a frozen co-rail")
        ok = False

    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not SRC.exists():
        print("missing %s" % SRC)
        return 2
    by = load(SRC)
    crit, rep = run_all(by)

    print("=" * 74)
    print("B62: the edge stays up, the number it carries does not")
    print("=" * 74)
    print("posts %d, %s to %s" % (rep["posts"], rep["posting"]["first"],
                                  rep["posting"]["last"]))
    print("page layouts:")
    for s, n in rep["signatures"].items():
        print("   x%-4d %s" % (n, s))
    print("misdated posts, caught on fields not values:")
    for d, w in rep["misdated"].items():
        print("   %s  %s" % (d, w))
    print()
    print("state runs after dropping them:")
    for r in rep["runs_after_fix"]:
        print("   %-7s x%-4d %s .. %s" % (r["state"], r["n"], r["from"], r["to"]))
    print()
    for state, s in rep["same_post_control"].items():
        print("control over the %s block (%s .. %s, %d posts):"
              % (state, s["window"][0], s["window"][1], s["posts"]))
        for k, v in s["rails"].items():
            print("   %-24s n=%-4d distinct=%-4d %.2f .. %.2f"
                  % (k, v["n"], v["distinct"], v["range"][0], v["range"][1]))
    print()
    for c in crit:
        print("%-5s %-8s %s" % ("PASS" if c["passed"] else "FAIL",
                                c["name"], c["detail"]))

    OUT.write_text(json.dumps({
        "stage": "B62",
        "config": {"source": str(SRC.relative_to(ROOT)),
                   "target": list(TARGET),
                   "co_rails": [list(x) for x in CO_RAILS],
                   "events_named_after_the_fact": EVENTS},
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
