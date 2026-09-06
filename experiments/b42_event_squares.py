"""B42-4 first read: does the square move when registration moves at one of its ends.

This does not render a verdict. It prints the object, in the sense the B41 stage
settled on after a day spent on statistics that turned out to answer nothing: the
first pass over a new pairing is instrument calibration, and the numbers below are
there to be looked at rather than thresholded.

The square is the one B41 measured, and the code that builds it is imported from
that stage rather than rewritten here, so that a change to what a square means
propagates instead of silently forking. That direction of coupling is the safe
one: this stage reads the definition, it does not own it.

    [ basis(a,i) - basis(b,i) ] - [ basis(a,j) - basis(b,j) ]

Treatment is a change in certificates registered at one end of the square, in one
of the two commodities the square is built from. The opponent, a scalar price
potential on positions, predicts the square is identically zero and therefore
predicts no response to anything. The framework says the position term carries a
commodity index, so a commodity-specific change in a published position quantity
should show up in it.

Two controls come free and use the same code on the same days:

  pairs away from the event   a square between two positions neither of which was
                              treated, on the same dates
  off-pair commodities        a registration change in a commodity that is not one
                              of the square's two. A change in the congestion of a
                              position is common to both commodities and cancels
                              in the square, so this arm is predicted to read zero
                              whichever way the treated arm reads.

    python experiments/b42_event_squares.py --describe
    python experiments/b42_event_squares.py --series
    python experiments/b42_event_squares.py --events
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_square_smoke as sm          # the square's definition lives there

CACHE = REPO / "data" / "b41" / "cache"

# The AMS basis cache starts here, so an earlier change has nothing to read against.
AMS_START = "2020-02-01"

# The spot window is the only one quoted on nearly every day; the forward windows
# come and go with the crop calendar. Restricting to it leaves one cell per day per
# position per commodity, which --describe checks rather than assumes.
SPOT = "current~current"

# One entry per state. `zones` maps a delivery district published in the
# registration file to the position it sits at. A district whose position cannot
# be settled from a document maps to a tuple of the candidates: an event there
# still moves the square between them, so the size of the move is readable while
# the sign is not. A district that maps to None is off every position here and
# supplies a control.
#
# The commodity pair has to share a statutory test weight, or a per-ton cost
# leaves a per-bushel residue in the square. Wheat and soybeans are both 60,
# corn is 56, so Ohio pairs wheat with soybeans rather than with corn.
# The registration file names a futures contract; the price report names a
# commodity. Contracts with no counterpart in the price reports map to None and
# their changes can only ever be controls.
CONTRACT_TO_COMMODITY = {
    "CORN FUTURES": "Corn",
    "SOYBEAN FUTURES": "Soybeans",
    "WHEAT FUTURES": "Wheat",
    "KC WHEAT FUTURES": "Wheat",
    "HARD RED SPRING WHEAT FUT": "Wheat",
    "OATS FUTURES": "Oats",
    "ROUGH RICE FUTURES": None,
    "SOYBEAN OIL FUTURES": None,
    "SOYBEAN MEAL FUTURES": None,
}

STATES = {
    "IL": dict(
        report=3192,
        pair=("Corn", "Soybeans"),
        positions=["Chicago | Terminal Elevators",
                   "Mississippi River | Barge Loading Elevators",
                   "North Illinois River | Barge Loading Elevators",
                   "South Illinois River | Barge Loading Elevators"],
        # Zone 4 is the Peoria reach, the one stretch whose side of the AMS
        # north/south split cannot be settled without the area definitions, and
        # no change in the record falls in it, so the unsettled entry never binds.
        zones={"ZONE 1": "Chicago | Terminal Elevators",
               "ZONE 2": "North Illinois River | Barge Loading Elevators",
               "ZONE 3": "North Illinois River | Barge Loading Elevators",
               "ZONE 4": None,
               "ZONE 5": "South Illinois River | Barge Loading Elevators",
               "ZONE 6": "Mississippi River | Barge Loading Elevators",
               "CHICAGO": "Chicago | Terminal Elevators",
               "MISSISSIPPI RIVER": "Mississippi River | Barge Loading Elevators"},
        towns=(", IL",),
    ),
    "MO": dict(
        report=2932,
        pair=("Corn", "Soybeans"),
        positions=["St. Louis MS River | Terminals/Mills/Processors",
                   "Northeast Missouri MS River | Barge Loading Elevators",
                   "Southeast Missouri MS River | Barge Loading Elevators",
                   "Kansas City | Terminals/Mills/Processors"],
        zones={"MISSISSIPPI RIVER": None, "ST. LOUIS": None},
        towns=(", MO",),
    ),
    "OH": dict(
        report=2851,
        pair=("Wheat", "Soybeans"),
        positions=["Toledo - On River | Terminal Elevators",
                   "Toledo - Off River | Terminal Elevators",
                   "Ohio River | Barge Loading Elevators",
                   "East | Country Elevators"],
        # The six facilities in the exchange's Toledo district sit in one city and
        # the report prices that city as two positions, one with water access and
        # one without. Which of the two a given facility belongs to is a single
        # bit that no document to hand settles, so the district maps to both: an
        # event there moves the square between them either way, and only the sign
        # of the move depends on the bit.
        zones={"TOLEDO": ("Toledo - On River | Terminal Elevators",
                          "Toledo - Off River | Terminal Elevators"),
               "OHIO RIVER": "Ohio River | Barge Loading Elevators",
               "NORTHWEST OHIO": None},
        towns=(", OH", ", MI"),
    ),
}


def to_iso(s: str) -> str:
    """report_date arrives as MM/DD/YYYY. Sorting or comparing it as text puts
    December before February and silently mis-orders every window, so it is
    converted once here and never handled in the source format again."""
    s = (s or "").strip()
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        return f"{s[6:10]}-{s[0:2]}-{s[3:5]}"
    return s[:10]


def load_state(state: str) -> list[dict]:
    cfg = STATES[state]
    rows = []
    for f in sorted(CACHE.glob(f"reports_{cfg['report']}_Report_Detail*")):
        d = json.loads(f.read_text(encoding="utf-8"))
        r = d.get("results") if isinstance(d, dict) else d
        if isinstance(r, list):
            rows += r
    return rows


def daily_cells(rows: list[dict], cfg: dict) -> dict:
    """(day, commodity) -> {position: (lo, hi, futures_month)} on the spot window."""
    out: dict[tuple, dict] = defaultdict(dict)
    skipped = defaultdict(int)
    for r in rows:
        if r.get("commodity") not in cfg["pair"]:
            continue
        pos = sm.position(r)
        if pos not in cfg["positions"]:
            continue
        if r.get("quote_type") != "Basis" or r.get("sale Type") != "Bid":
            skipped["not a basis bid"] += 1; continue
        window = f'{r.get("delivery_start") or "current"}~{r.get("delivery_end") or "current"}'
        if window != SPOT:
            skipped["not the spot window"] += 1; continue
        lo, hi = r.get("basis Min"), r.get("basis Max")
        m_lo, m_hi = r.get("basis Min Futures Month"), r.get("basis Max Futures Month")
        if lo is None or hi is None or not m_lo:
            skipped["no basis"] += 1; continue
        if m_lo != m_hi:
            skipped["range straddles two months"] += 1; continue
        day = to_iso(r.get("report_date"))
        key = (day, r.get("commodity"))
        if pos in out[key]:
            skipped["more than one spot cell"] += 1; continue
        out[key][pos] = (float(lo), float(hi), m_lo)
    return out, skipped


def square_series(cells: dict, cfg: dict) -> dict:
    """(i, j) -> {day: (mid, lo, hi)}, enforcing one futures month per commodity."""
    days = sorted({k[0] for k in cells})
    series: dict[tuple, dict] = defaultdict(dict)
    dropped = defaultdict(int)
    a, b = cfg["pair"]
    for day in days:
        ca, cb = cells.get((day, a), {}), cells.get((day, b), {})
        shared = sorted(set(ca) & set(cb))
        for i, j in combinations(shared, 2):
            if ca[i][2] != ca[j][2] or cb[i][2] != cb[j][2]:
                dropped["futures month differs across the two positions"] += 1
                continue
            ai, aj, bi, bj = ca[i][:2], ca[j][:2], cb[i][:2], cb[j][:2]
            mid = (sum(ai) / 2 - sum(bi) / 2) - (sum(aj) / 2 - sum(bj) / 2)
            vals = [(x - y) - (z - w) for x in ai for y in aj for z in bi for w in bj]
            series[(i, j)][day] = (mid, min(vals), max(vals))
    return series, dropped


def parse_dates(s: str) -> date:
    return date.fromisoformat(s if "-" in s else
                              f"{s[6:10]}-{s[0:2]}-{s[3:5]}")


def describe(state: str) -> None:
    cfg = STATES[state]
    rows = load_state(state)
    cells, skipped = daily_cells(rows, cfg)
    days = sorted({k[0] for k in cells})
    print(f"{state}  report {cfg['report']}  pair {cfg['pair']}")
    print(f"rows {len(rows)}   spot cells kept on {len(days)} days")
    for k, v in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print(f"   {v:7d}  set aside: {k}")
    have = defaultdict(int)
    for (day, com), d in cells.items():
        have[(com, len(d))] += 1
    print("\ndays by how many positions carry a spot cell:")
    for com in cfg["pair"]:
        print(f"   {com:10s} "
              f"{ {n: have[(com, n)] for n in range(len(cfg['positions'])+1) if have[(com,n)]} }")
    series, dropped = square_series(cells, cfg)
    for k, v in dropped.items():
        print(f"   {v:7d}  square dropped: {k}")
    print(f"\n{'pair':56s} {'days':>6} {'mean':>9} {'sd':>8}")
    for (i, j), d in sorted(series.items()):
        v = [x[0] for x in d.values()]
        print(f"{i.split('|')[0].strip():26s} vs {j.split('|')[0].strip():26s} "
              f"{len(v):6d} {statistics.fmean(v):9.2f} {statistics.pstdev(v):8.2f}")


def events_for_state(state: str) -> list[dict]:
    """Changes carried by the registration snapshot, restricted to this state."""
    import importlib.util
    cfg = STATES[state]
    spec = importlib.util.spec_from_file_location(
        "b42panel", Path(__file__).resolve().parent / "b42_registration_panel.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    ev = m.events(m.parse(), quiet=True)
    out = []
    for e in ev:
        if not e["town"].endswith(cfg["towns"]):
            continue
        if e["effective"] < AMS_START:
            continue
        if e["district"] not in cfg["zones"]:
            continue
        pos = cfg["zones"][e["district"]]
        com = CONTRACT_TO_COMMODITY.get(e["commodity"])
        out.append({**e, "position": pos, "off_position": pos is None,
                    "ams_commodity": com, "in_pair": com in cfg["pair"]})
    return out


def window_mean(d: dict, days: list[str], end: str, n: int, after: bool) -> tuple:
    idx = [k for k in days if (k >= end if after else k <= end)]
    idx = idx[:n] if after else idx[-n:]
    v = [d[k][0] for k in idx if k in d]
    return (statistics.fmean(v) if v else float("nan"), len(v))


def touched(e: dict, i: str, j: str) -> str:
    """Whether this square has the changed facility at one of its ends.

    Returns "yes", "no", or "unsettled". A district that maps to a tuple is one
    whose position is a single unknown bit: a square spanning both candidates has
    the facility at one end whichever way the bit falls, so it reads "yes", while
    a square with exactly one candidate at an end reads "unsettled" rather than
    "no". Calling those "no" would put possibly-treated squares into the control
    arm, which is the one error this classification must not make."""
    pos = e["position"]
    if pos is None:
        return "no"
    if isinstance(pos, tuple):
        n = len({i, j} & set(pos))
        return "yes" if n == 2 else ("unsettled" if n == 1 else "no")
    return "yes" if pos in (i, j) else "no"


def events(state: str, span: int = 10, placebo: int = 5) -> None:
    import random
    cfg = STATES[state]
    rows = load_state(state)
    cells, _ = daily_cells(rows, cfg)
    series, _ = square_series(cells, cfg)
    days = sorted({k[0] for k in cells})
    ev = events_for_state(state)
    print(f"{state}: {len(ev)} changes in the record fall in a district this state "
          f"knows about, over {len(days)} report days")
    print(f"window {span} report days each side\n")
    print(f"{'effective':11s} {'w':>4} {'district':16s} {'com':9s} {'square':50s} "
          f"{'pre':>8} {'post':>8} {'delta':>8} {'n':>7} {'arm':7s}")
    summary = defaultdict(list)
    for e in sorted(ev, key=lambda x: x["effective"]):
        for (i, j), d in sorted(series.items()):
            pre, npre = window_mean(d, days, e["previous_effective"], span, False)
            post, npost = window_mean(d, days, e["effective"], span, True)
            if npre < 3 or npost < 3:
                continue
            t = touched(e, i, j)
            if not e["in_pair"]:
                arm = {"yes": "offcom", "unsettled": "offcom?", "no": "neither"}[t]
            else:
                arm = {"yes": "treat", "unsettled": "unsettl", "no": "away"}[t]
            summary[arm].append(abs(post - pre))
            lab = f"{i.split('|')[0].strip()} vs {j.split('|')[0].strip()}"
            print(f"{e['effective']:11s} {e['window_days']:4d} {e['district']:16s} "
                  f"{str(e['ams_commodity']):9s} {lab:50s} {pre:8.2f} {post:8.2f} "
                  f"{post-pre:8.2f} {npre:3d}/{npost:<3d} {arm:7s}")
    print(f"\n{'arm':9s} {'n':>5} {'median |delta|':>15} {'mean |delta|':>14}")
    for arm in ("treat", "unsettl", "away", "offcom", "offcom?", "neither"):
        v = summary[arm]
        if v:
            print(f"{arm:9s} {len(v):5d} {statistics.median(v):15.2f} "
                  f"{statistics.fmean(v):14.2f}")

    # The floor for this statistic is what the same code reads on dates chosen at
    # random, holding the position and the window width fixed. Without it the
    # median above is a number with nothing to be large or small against.
    treat_ev = [e for e in ev if e["in_pair"] and e["position"] is not None]
    if treat_ev and placebo:
        random.seed(20260903)
        print(f"\nplacebo: same positions and window widths, dates drawn at random, "
              f"{placebo} rounds")
        for rep in range(placebo):
            v = []
            for e in treat_ev:
                k = random.randrange(20, max(21, len(days) - 20))
                d_eff = days[k]
                d_prev = days[max(0, k - max(1, e["window_days"]))]
                for (i, j), d in series.items():
                    if touched(e, i, j) != "yes":
                        continue
                    pre, npre = window_mean(d, days, d_prev, span, False)
                    post, npost = window_mean(d, days, d_eff, span, True)
                    if npre >= 3 and npost >= 3:
                        v.append(abs(post - pre))
            if v:
                print(f"   rep {rep}: {len(v):4d} pairs  median {statistics.median(v):7.2f}"
                      f"  mean {statistics.fmean(v):7.2f}")
    print("\nNo verdict is taken from this table. It is here to show what the arms "
          "look like before any statistic is chosen.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", default="IL", choices=sorted(STATES))
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--events", action="store_true")
    ap.add_argument("--span", type=int, default=10)
    ap.add_argument("--placebo", type=int, default=5)
    a = ap.parse_args()
    if a.describe: describe(a.state)
    if a.events: events(a.state, a.span, a.placebo)
    if not (a.describe or a.events): ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
