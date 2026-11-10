"""B146: which markets on the mandi panel had both edges cut by a dated document.

A market town has two edges to everywhere else. Goods move on one, and a price
quoted elsewhere arrives on the other. This station looks, on the daily mandi
panel, for (market, event) units where a named document dates a cut of each,
and sorts every unit into one of seven cells.

Three things are kept apart throughout, because the panel cannot tell them apart
on its own:

* a market that stops filing rows. That is the edge carrying the *record* out of
  the market, or the thing that edge carries (a price formed that day). It says
  nothing about whether a price from elsewhere could still arrive;
* a market that was closed (strike, curfew, no means of settlement). The price
  did not form. No edge is described by that;
* an edge that a document says was cut: a highway under water, a blockade, an
  order to carriers to stop a service.

So the dates of an information cut come only from named documents, and a filing
stop is one column of the panel. On a panel that exists only where markets file,
a stop and a reading inside the window exclude each other: a market that stopped
leaves the two filings on either side and nothing between.

The treatment is a set of restrictions with their own start and end dates, so the
index of every reading is the set in force on a day, never one event date.

Usage::

    python experiments/b146_double_cut.py --selftest
    python experiments/b146_double_cut.py
    python experiments/b146_double_cut.py --commodity "Lentil (Masur)" --no-write
"""
from __future__ import annotations

import argparse
import bisect
import collections
import datetime
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b146_stop_census as census  # noqa: E402

ROOT = HERE.parent
RESULTS = ROOT / "results"
D = datetime.date
ONE = datetime.timedelta(1)

SHORT = {"Lentil (Masur)": "lentil", "Cowpea (Lobia-Karamani)": "cowpea", "White Peas": "white"}

# ----------------------------------------------------------------------------- knobs
PRIOR_WINDOW = 30
PRIOR_FLOORS = (5, 10, 15)      # filings in the 30 days before the event's first date
STOP_FLOORS = (8, 15)           # days between two filings that count as a stop
CLUSTER_WINDOWS = (3, 7)        # days within which stops are one cluster
DEFAULT = {"prior_floor": 5, "stop_floor": 8, "cluster_window": 3}
EDGE_DAYS = 7                   # the "at the cut" and "end of window" slices
PRE_DAYS = 60                   # the pre-window for arrivals and dispersion
MIN_MARKETS = 3                 # fewer markets than this is not a dispersion
MIN_SEGMENT = 10                # filings on each side of an arrivals jump
REF_SLACK = 3                   # days either side for the outside reference
SHIFTS = (-40, -20, -10, 10, 20, 40)   # shifted calendars for the closure read-back
REF_MIN_OBS = 500               # a variety is a reference of its own with this many outside rows in the window
FIXED_MIN = 10                  # filings per segment for a series to enter the fixed-composition reference
PLACEBO_STEP = 30               # days between the starts of two placebo windows
PLACEBO_MAX = 36                # placebo windows per event at most
PLACEBO_MIN_LEN = 30            # events shorter than this get no placebo table
READ_MIN_LEN = 30               # a change in h is read only on a window at least this long
CLOSURE_PLACEBO_STEP = 7        # days between two shifted closure windows
CLOSURE_PLACEBO_MIN_UNITS = 10  # a shifted window with fewer active markets is not counted
EARLY_DAYS = 2                  # a last filing more than this many days before a closure's first day came before it
YEAR_BACK = 364                 # the same window a year earlier, on the same weekdays

# ----------------------------------------------------------------------------- cells
CELLS = (
    "unverified", "ordinary", "T_cut_I_open", "T_open_I_cut", "object_absent",
    "both_cut_read_inside", "both_cut_edges_only",
)
#: cell -> (rule in words, what it feeds, whether it can carry a verdict)
MAPPING = {
    "unverified": ("an edge document of the event is not checked against a source",
                   "nothing", None),
    "ordinary": ("neither edge document covers the market", "counted, not read", "counted"),
    "T_cut_I_open": ("transport document covers it; no full information cut does "
                     "(a mobile-data-only order is a thinner edge, not a cut one)",
                     "B146-8", "printed"),
    "T_open_I_cut": ("full information cut covers it; no transport document does",
                     "counted, dispersion printed", "printed"),
    "object_absent": ("a closure, curfew or strike document covers it and it filed nothing "
                      "in its window, or every filing in the window has zero arrivals: what is "
                      "missing is the price itself, and no edge is described", "nothing", None),
    "both_cut_read_inside": ("both documents cover it, it filed inside the window, no closure",
                             "B146-6", "read"),
    "both_cut_edges_only": ("both documents cover it, it filed nothing inside the window, "
                            "no closure", "B146-7", "read"),
}
#: state of a reading -> verdict. ``None`` is "no verdict": the state is printed and
#: is neither a pass nor a fail.
MAPPING_B6 = {"grew": True, "did_not_grow": False, "unread": None}
MAPPING_B6_WORDS = {
    "grew": "dispersion at the end of the window exceeds dispersion at the cut by more than one "
            "grid step: the registered consequent holds",
    "did_not_grow": "it does not: the copies stayed where the cut left them, and the registered "
                    "consequent does not hold on this unit",
    "unread": "fewer than three markets of one variety, or the premise is false, or the count of "
              "both-cut units moves on the knob sweep: no verdict"}
#: B146-7 prints a state per unit and registers no direction, so no state is a fail;
#: its flag is whether every unit of the cell has a row and a state.
MAPPING_B7 = {"unread": None, "did_not_move": "printed", "moved_with_reference": "printed",
              "moved_against_reference": "printed"}
#: an information document counts as a cut of the inbound edge only for these kinds
FULL_CUT_KINDS = ("all",)
#: the wider reading, reported next to the strict one: every data service stopped,
#: voice still up
WIDE_CUT_KINDS = ("all", "all_internet")

# ----------------------------------------------------------------------------- events
#: Each row: where, the transport document, the information document, the closure
#: documents, the source of each, the grade of the source (1 official, 2 research,
#: 3 press and trackers), and whether the dates were checked against that source.
#: ``districts`` None means the whole state. Dates are inclusive.
EVENTS = (
    {
        "id": "MN-2016-blockade", "state": "Manipur", "label": "highway blockade, Manipur",
        "transport": {"start": D(2016, 11, 1), "end": D(2017, 3, 19), "districts": None,
                      "what": "National Highways 2 and 37 blockaded; lifted 19 Mar 2017"},
        "info": {"start": D(2016, 12, 18), "end": D(2016, 12, 30), "kind": "mobile_data",
                 "districts": ("Imphal East", "Imphal West"),
                 "what": "district magistrates' order to disconnect mobile internet"},
        "closures": ({"start": D(2016, 12, 18), "end": D(2016, 12, 18),
                      "districts": ("Imphal East", "Imphal West"), "checked": True,
                      "what": "curfew reported on that day; relaxation dates not found, so "
                              "the documented span is the one day"},),
        "sources": ("https://internetshutdowns.in/india-shutdowns/960/manipur-2016/",
                    "https://www.thequint.com/india/2016/12/20/economic-blockade-to-attack-on-"
                    "civilians-manipur-crisis-with-nagaland-districts-violence-all-you-need-to-know-",
                    "https://english.madhyamam.com/national/2016/dec/18/manipur-22-vehicles-"
                    "torched-near-imphal-violence-spreads-curfew-imposed",
                    "https://swarajyamag.com/amp/story/insta%2F130-day-naga-economic-blockade-"
                    "in-manipur-to-be-lifted-tonight"),
        "grade": 3, "checked": True, "excluded_markets": (),
    },
    {
        "id": "MP-2017-strike", "state": "Madhya Pradesh", "label": "farmers' strike, Madhya Pradesh",
        "transport": None,
        "info": {"start": D(2017, 6, 6), "end": D(2017, 6, 11), "kind": "mobile_data",
                 "districts": ("Mandsaur", "Ratlam", "Ujjain", "Neemuch", "Indore", "Dewas"),
                 "what": "mobile internet suspended; one report gives 5 Jun as the start"},
        "closures": ({"start": D(2017, 6, 1), "end": D(2017, 6, 10), "districts": None,
                      "checked": True,
                      "what": "ten-day strike called by farmers' bodies: no produce brought to market"},
                     {"start": D(2017, 6, 6), "end": D(2017, 6, 10), "districts": ("Mandsaur",),
                      "checked": True, "what": "curfew after the 6 Jun firing; relaxed 10 Jun"}),
        "sources": ("https://internetshutdowns.in/india-shutdowns/737/madhya-pradesh-2017/",
                    "https://www.millenniumpost.in/big-stories/big-stories-245862",
                    "https://www.millenniumpost.in/nation/nation-246460",
                    "https://www.business-standard.com/article/pti-stories/farmers-stir-violence-"
                    "arson-in-western-mp-govt-announces-117060701377_1.html"),
        "grade": 3, "checked": True, "excluded_markets": (),
    },
    {
        "id": "AS-2014-flood", "state": "Assam", "label": "flood, lower Assam",
        "transport": {"start": D(2014, 9, 22), "end": D(2014, 9, 25),
                      "districts": ("Goalpara", "Kamrup"),
                      "what": "National Highway 37 under water, Goalpara cut off from Guwahati; "
                              "25 Sep is the last dated report of the closure, a lower bound"},
        "info": None,
        "closures": (),
        "sources": ("https://assamtribune.com/goalpara-hatsingimari-hit-by-garo-hills-water",
                    "https://indiaenvironmentportal.org.in/news-clippings/state-flood-toll-rises-to-36",
                    "https://www.millenniumpost.in/after-jk-assam-flooded-39565"),
        "grade": 3, "checked": True, "excluded_markets": (),
    },
    {
        "id": "RJ-2015-blockade", "state": "Rajasthan", "label": "rail and road blockade, eastern Rajasthan",
        "transport": {"start": D(2015, 5, 21), "end": D(2015, 5, 28),
                      "districts": ("Bharatpur", "Dausa", "Sawai Madhopur", "Karauli", "Tonk"),
                      "what": "sit-in on the Delhi-Mumbai line from 21 May, highways from 24 May; "
                              "called off 28 May"},
        "info": None,
        "closures": (),
        "sources": ("https://www.tribuneindia.com/news/archive/nation/after-failed-talks-gujjars-"
                    "intensify-stir-in-rajasthan-84980",
                    "https://www.moneylife.in/article/gujjars-call-off-agitation-as-rajasthan-"
                    "agrees-to-quota/42019.html",
                    "https://www.business-standard.com/article/pti-stories/gujjar-stir-wr-losing-"
                    "rs-15-cr-daily-due-to-train-cancellation-115052600410_1.html"),
        "grade": 3, "checked": True, "excluded_markets": (),
    },
    {
        "id": "WB-2017-hills", "state": "West Bengal", "label": "hills shutdown, Darjeeling",
        "transport": {"start": D(2017, 6, 15), "end": D(2017, 6, 22), "districts": ("Darjeeling",),
                      "what": "indefinite general shutdown in the hills (19 Jun reported as its "
                              "fifth day); still on when the panel ends on 22 Jun"},
        "info": {"start": D(2017, 6, 20), "end": D(2017, 6, 22), "kind": "all_internet",
                 "districts": ("Darjeeling",),
                 "what": "mobile internet blocked 18 Jun; on 20 Jun the district magistrate "
                         "ordered providers to stop all internet service in the hills"},
        "closures": (),
        "sources": ("https://internetshutdowns.in/india-shutdowns/902/west-bengal-2017/",
                    "https://sflc.in/darjeeling-internet-ban-completes-two-months/",
                    "https://www.business-standard.com/article/pti-stories/wb-internet-still-"
                    "suspended-gjm-activists-take-out-protest-117061900693_1.html"),
        "grade": 3, "checked": True,
        # the orders name the hills; Siliguri is the plains subdivision of the same district
        "excluded_markets": ("Siliguri",),
    },
    {
        "id": "MP-2016-cash", "state": "Madhya Pradesh",
        "label": "largest cluster of stops on the panel, Madhya Pradesh",
        "transport": None, "info": None,
        "closures": ({"start": D(2016, 11, 9), "end": D(2016, 11, 22), "districts": None,
                      "checked": True,
                      "what": "large notes withdrawn on the evening of 8 Nov 2016; markets "
                              "reported shut for want of cash for five days to a fortnight"},),
        "sources": ("https://newsbits.in/demonetization-crushes-rural-economy-mp-villagers-are-"
                    "cashless-getting-fleeced",
                    "https://culanth.org/fieldsights/trading-notes",
                    "https://www.ideasforindia.in/topics/money-finance/what-did-demonetisation-do-"
                    "to-domestic-agricultural-markets.html"),
        "grade": 3, "checked": True, "excluded_markets": (),
    },
    # Four candidates whose dates were not checked against any source. They are
    # listed so that the count of candidates is the count that was looked at.
    {
        "id": "UK-2013-flood", "state": "Uttrakhand", "label": "flood, Uttarakhand (unchecked)",
        "transport": {"start": D(2013, 6, 16), "end": D(2013, 6, 30), "districts": None,
                      "what": "unchecked"},
        "info": None, "closures": (), "sources": (), "grade": None, "checked": False,
        "excluded_markets": (),
    },
    {
        "id": "GJ-2015-mobile", "state": "Gujarat", "label": "statewide mobile-data stop, Gujarat (unchecked)",
        "transport": None,
        "info": {"start": D(2015, 8, 26), "end": D(2015, 9, 2), "kind": "mobile_data",
                 "districts": None, "what": "unchecked"},
        "closures": (), "sources": (), "grade": None, "checked": False, "excluded_markets": (),
    },
    {
        "id": "HR-2016-blockade", "state": "Haryana", "label": "road blockade, Haryana (unchecked)",
        "transport": {"start": D(2016, 2, 19), "end": D(2016, 2, 23), "districts": None,
                      "what": "unchecked"},
        "info": {"start": D(2016, 2, 19), "end": D(2016, 2, 23), "kind": "mobile_data",
                 "districts": None, "what": "unchecked"},
        "closures": (), "sources": (), "grade": None, "checked": False, "excluded_markets": (),
    },
    {
        "id": "TR-2016-road", "state": "Tripura", "label": "highway failure, Tripura (unchecked)",
        "transport": {"start": D(2016, 6, 15), "end": D(2016, 7, 31), "districts": None,
                      "what": "unchecked"},
        "info": None, "closures": (), "sources": (), "grade": None, "checked": False,
        "excluded_markets": (),
    },
)
#: Dated nationwide events that are no edge document of any row. Where one falls inside
#: a window that is read, it is printed next to the reading.
NATIONWIDE = ({"date": D(2016, 11, 8), "what": "large notes withdrawn nationwide on the evening of 8 Nov 2016"},)

#: Storms and floods that took communication down physically inside the panel's span.
#: Dates are unchecked; the screen only counts markets active before
#: each, at every activity floor, so that the candidate list is not limited to orders.
OUTAGE_SCREEN = (
    {"id": "OR-2013-cyclone", "state": "Orissa", "start": D(2013, 10, 12), "label": "cyclone, Odisha coast"},
    {"id": "AP-2014-cyclone", "state": "Andhra Pradesh", "start": D(2014, 10, 12), "label": "cyclone, north Andhra coast"},
    {"id": "TN-2015-flood", "state": "Tamil Nadu", "start": D(2015, 12, 1), "label": "flood, Chennai and the north coast"},
    {"id": "TN-2016-cyclone", "state": "Tamil Nadu", "start": D(2016, 12, 12), "label": "cyclone, Chennai"},
)
EVENT_FIELDS = ("state", "transport", "info", "closures", "sources", "grade", "checked")


# ----------------------------------------------------------------------------- helpers
def f6(x):
    """Floats go to the record through one explicit format."""
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float("%.6f" % x)


def iso(d):
    return None if d is None else d.isoformat()


def days(a, b):
    return [a + datetime.timedelta(k) for k in range((b - a).days + 1)] if a <= b else []


def covers(doc, district, market, excluded=()):
    if doc is None or market in excluded:
        return False
    return doc["districts"] is None or district in doc["districts"]


def event_start(ev):
    c = [x["start"] for x in (ev["transport"], ev["info"]) if x] + [x["start"] for x in ev["closures"]]
    return min(c)


def event_end(ev):
    c = [x["end"] for x in (ev["transport"], ev["info"]) if x] + [x["end"] for x in ev["closures"]]
    return max(c)


def mad(xs):
    m = statistics.median(xs)
    return statistics.median(abs(x - m) for x in xs)


def quantile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(math.ceil(q * len(xs))) - 1))] if xs else None


class Panel:
    """The rows of one commodity, indexed the ways the station reads them."""

    def __init__(self, rows):
        self.rows = rows
        self.per = census.filing_days(rows)                      # (state, district, market) -> days
        self.sets = {k: set(v) for k, v in self.per.items()}
        self.last_day = max((r[6] for r in rows), default=None)
        ser = collections.defaultdict(dict)
        arr = collections.defaultdict(dict)
        for s, dis, m, v, a, modal, d in rows:
            if modal is not None and modal > 0:
                ser[(s, dis, m, v)][d] = modal
            if a is not None:
                arr[(s, dis, m)][d] = arr[(s, dis, m)].get(d, 0.0) + a
        self.series = dict(ser)
        self.arrivals = dict(arr)
        self.dominant = {}
        for k in self.per:
            cands = [(len(v), kk[3]) for kk, v in self.series.items() if kk[:3] == k]
            self.dominant[k] = max(cands)[1] if cands else None
        nat = collections.defaultdict(list)
        for (s, dis, m, v), dd in self.series.items():
            for d, p in dd.items():
                nat[d].append((s, math.log(p), v))
        self.nat = dict(nat)
        self.first_day = min((r[6] for r in rows), default=None)

    def price(self, key):
        v = self.dominant.get(key)
        return self.series.get(key + (v,), {}) if v is not None else {}

    def reference(self, d, state, variety=None):
        """Median log price on the day over every series outside ``state``; with
        ``variety`` given, over the series of that variety only."""
        def take(day):
            return [x for s, x, v in self.nat.get(day, ()) if s != state and (variety is None or v == variety)]
        today = take(d)
        if len(today) >= MIN_MARKETS:
            return statistics.median(today)
        # a thin day: pool the days either side
        xs = []
        for k in range(-REF_SLACK, REF_SLACK + 1):
            xs += take(d + datetime.timedelta(k))
        return statistics.median(xs) if xs else None

    def reference_varieties(self, state, a, b):
        """Varieties with at least REF_MIN_OBS outside rows in [a, b], and the states
        those rows come from."""
        n = collections.Counter()
        where = collections.defaultdict(collections.Counter)
        for (s, dis, m, v), dd in self.series.items():
            if s == state:
                continue
            k = sum(1 for d in dd if a <= d <= b)
            n[v] += k
            if k:
                where[v][s] += k
        return {v: dict(sorted(where[v].items())) for v in sorted(n) if n[v] >= REF_MIN_OBS}

    def fixed_composition(self, state, a, b, variety=None):
        """The outside move with the set of series held fixed: over the series with at
        least FIXED_MIN filings in each of the three segments, the median of each
        series' own change in median log price."""
        pre0, post1 = a - datetime.timedelta(PRE_DAYS), b + datetime.timedelta(PRE_DAYS)
        d1, d2 = [], []
        for (s, dis, m, v), dd in sorted(self.series.items()):
            if s == state or (variety is not None and v != variety):
                continue
            seg = [[math.log(p) for d, p in dd.items() if lo <= d <= hi]
                   for lo, hi in ((pre0, a - ONE), (a, b), (b + ONE, post1))]
            if min(len(x) for x in seg) < FIXED_MIN:
                continue
            m0, m1, m2 = (statistics.median(x) for x in seg)
            d1.append(m1 - m0)
            d2.append(m2 - m1)
        return {"series": len(d1),
                "before_to_inside": f6(statistics.median(d1)) if d1 else None,
                "inside_to_after": f6(statistics.median(d2)) if d2 else None}

    def rupee_step(self, key):
        """The grain of one market's price in rupees: the median non-zero step."""
        pr = self.price(key)
        ds = sorted(pr)
        st = [abs(pr[b] - pr[a]) for a, b in zip(ds, ds[1:]) if pr[a] != pr[b]]
        return statistics.median(st) if st else None

    def grid(self, keys):
        """The grain of the prices in ``keys``: each series' median and smallest
        non-zero log step, and the median of each across the series."""
        med, small = [], []
        for k in keys:
            pr = self.price(k)
            ds = sorted(pr)
            st = [abs(math.log(pr[b]) - math.log(pr[a])) for a, b in zip(ds, ds[1:]) if pr[a] != pr[b]]
            if st:
                med.append(statistics.median(st))
                small.append(min(st))
        return {"median_step": statistics.median(med) if med else None,
                "smallest_step": statistics.median(small) if small else None,
                "series": len(med)}


def stop_over(panel, key, a, b, stop_floor):
    """The (last, next) filing pair, at least ``stop_floor`` days apart, whose open
    interval holds a day of [a, b]. A stop still open when the panel ends is
    measured to the panel's last day and its ``next`` is None."""
    ds = panel.per[key]
    out = []
    # only the pairs whose open interval can reach [a, b]: the one that starts at
    # or before a, and those that start before b
    i0 = max(bisect.bisect_right(ds, a) - 1, 0)
    i1 = bisect.bisect_left(ds, b)
    for i in range(i0, min(i1 + 1, len(ds))):
        x = ds[i]
        y = ds[i + 1] if i + 1 < len(ds) else None
        hi = y if y is not None else panel.last_day + ONE
        if (hi - x).days < stop_floor:
            continue
        if max(x + ONE, a) <= min(hi - ONE, b):
            out.append((x, y))
    return out


def classify(panel, key, ev, stop_floor, cut_kinds=FULL_CUT_KINDS, ignore_closure=False):
    """One (market, event) unit -> one cell, with the facts that decided it."""
    s, dis, m = key
    excl = ev.get("excluded_markets", ())
    facts = {"T": False, "I": False, "I_thin": False, "closure": False, "window": None,
             "filed_in_window": None, "stopped": False, "zero_arrivals": False}
    if not ev["checked"]:
        return "unverified", facts
    T = covers(ev["transport"], dis, m, excl)
    info_cov = covers(ev["info"], dis, m, excl)
    I = info_cov and ev["info"]["kind"] in cut_kinds
    facts.update(T=T, I=I, I_thin=info_cov and not I)
    if T and I:
        a, b = max(ev["transport"]["start"], ev["info"]["start"]), min(ev["transport"]["end"], ev["info"]["end"])
    elif T:
        a, b = ev["transport"]["start"], ev["transport"]["end"]
    elif I:
        a, b = ev["info"]["start"], ev["info"]["end"]
    else:
        a = b = None
    filed = panel.sets[key]
    absent = False
    for c in ev["closures"]:
        if not c.get("checked", True) or not covers(c, dis, m, excl):
            continue
        ca, cb = (c["start"], c["end"]) if a is None else (max(a, c["start"]), min(b, c["end"]))
        if ca > cb:
            continue
        facts["closure"] = True
        # the closure explains a silence only if the unit is silent over its whole
        # decisive window; a one-day curfew inside a 139-day blockade removes that
        # day from the readings and leaves the unit where its edges put it
        wa, wb = (c["start"], c["end"]) if a is None else (a, b)
        none_filed = not any(d in filed for d in days(wa, wb))
        stopped = bool(stop_over(panel, key, ca, cb, stop_floor))
        if none_filed and stopped:
            absent = True
            facts["stopped"] = True
    if a is not None:
        win = [d for d in days(a, b) if d in filed]
        facts["window"] = (a, b)
        facts["filed_in_window"] = len(win)
        arr = [panel.arrivals.get(key, {}).get(d) for d in win]
        arr = [x for x in arr if x is not None]
        if arr and sum(arr) == 0:
            facts["zero_arrivals"] = True
            absent = True
        if not facts["stopped"]:
            facts["stopped"] = bool(stop_over(panel, key, a, b, stop_floor))
    if absent and not ignore_closure:
        return "object_absent", facts
    if T and I:
        return ("both_cut_read_inside" if facts["filed_in_window"] else "both_cut_edges_only"), facts
    if T:
        return "T_cut_I_open", facts
    if I:
        return "T_open_I_cut", facts
    return "ordinary", facts


def units_for(panel, ev, prior_floor):
    """Markets of the event's state with at least ``prior_floor`` filings in the 30
    days before the event's first date."""
    start = event_start(ev)
    win = set(days(start - datetime.timedelta(PRIOR_WINDOW), start - ONE))
    out = []
    for key in sorted(panel.per):
        if key[0] != ev["state"]:
            continue
        n = len(panel.sets[key] & win)
        if n >= prior_floor:
            out.append((key, n))
    return out


def dosage(ev):
    """Runs of days on which the same set of restrictions is in force: the
    index of a reading is this set, not a date."""
    docs = []
    if ev["transport"]:
        docs.append(("transport", ev["transport"]))
    if ev["info"]:
        docs.append(("info:" + ev["info"]["kind"], ev["info"]))
    for i, c in enumerate(ev["closures"]):
        docs.append(("closure%d" % (i + 1), c))
    runs = []
    for d in days(event_start(ev), event_end(ev)):
        on = tuple(n for n, x in docs if x["start"] <= d <= x["end"])
        if runs and runs[-1][2] == on:
            runs[-1][1] = d
        else:
            runs.append([d, d, on])
    return [{"from": iso(a), "to": iso(b), "days": (b - a).days + 1, "in_force": list(on)}
            for a, b, on in runs], len(docs)


def latest(pr, a, b):
    ds = [d for d in pr if a <= d <= b]
    return pr[max(ds)] if ds else None


def dispersion_change(panel, keys, cut_day, end_day):
    """MAD of log prices across markets, per variety, at the cut and at the end of
    the window; the variety with most markets is the one reported."""
    by_var = collections.defaultdict(list)
    for k in keys:
        if panel.dominant[k] is not None:
            by_var[panel.dominant[k]].append(k)
    best = None
    for v, ks in sorted(by_var.items()):
        pair = []
        for k in ks:
            pr = panel.price(k)
            p0 = latest(pr, cut_day - datetime.timedelta(2 * EDGE_DAYS), cut_day - ONE)
            p1 = latest(pr, end_day - datetime.timedelta(EDGE_DAYS - 1), end_day)
            if p0 and p1:
                pair.append((math.log(p0), math.log(p1)))
        if best is None or len(pair) > best["markets"]:
            best = {"variety": v, "markets": len(pair),
                    "at_cut": mad([p[0] for p in pair]) if pair else None,
                    "at_end": mad([p[1] for p in pair]) if pair else None}
    return best


def read_b6(panel, both_inside, premise, flips):
    """Three states. ``both_inside`` maps event id -> (keys, cut_day, end_day)."""
    out = []
    for eid, (keys, cut_day, end_day) in sorted(both_inside.items()):
        ch = dispersion_change(panel, keys, cut_day, end_day)
        g = panel.grid(keys)["median_step"]
        if not premise or ch is None or ch["markets"] < MIN_MARKETS or g is None or flips:
            state = "unread"
        else:
            state = "grew" if ch["at_end"] - ch["at_cut"] > g else "did_not_grow"
        out.append({"event": eid, "state": state, "grid": f6(g),
                    "variety": ch and ch["variety"], "markets": ch["markets"] if ch else 0,
                    "at_cut": f6(ch and ch["at_cut"]), "at_end": f6(ch and ch["at_end"])})
    return out


def edge_step(panel, key, pair, state_name):
    """The step across a stop and the outside reference over the same two days."""
    a, b = pair
    pr = panel.price(key)
    pa = latest(pr, a - datetime.timedelta(EDGE_DAYS), a)
    after = sorted(d for d in pr if b and b <= d <= b + datetime.timedelta(EDGE_DAYS))
    pb = pr[after[0]] if after else None
    ra = panel.reference(a, state_name)
    rb = panel.reference(b, state_name) if b else None
    step = math.log(pb) - math.log(pa) if pa and pb else None
    ref = rb - ra if ra is not None and rb is not None else None
    return {"last": iso(a), "next": iso(b), "price_last": pa, "price_next": pb,
            "step": f6(step), "reference_move": f6(ref)}


def reference_floor(panel, state, lo, hi, variety=None):
    """The outside reference's own day-to-day move over [lo, hi]. A move of the
    reference between two single days is read against this: the set of series
    behind the daily median changes from one day to the next."""
    prev, ch = None, []
    for d in days(lo, hi):
        r = panel.reference(d, state, variety)
        if r is None:
            continue
        if prev is not None:
            ch.append(abs(r - prev))
        prev = r
    return {"day_pairs": len(ch), "median": f6(statistics.median(ch)) if ch else None,
            "p90": f6(quantile(ch, 0.9)), "max": f6(max(ch)) if ch else None}


def read_b7(panel, edges_only, grid_of, floor_of=None):
    out = []
    for eid, key, pair in edges_only:
        row = edge_step(panel, key, pair, key[0])
        g = grid_of[eid]
        fl = (floor_of or {}).get(eid, {}).get("median") or 0.0
        row.update(event=eid, market=" / ".join(key[1:]), grid=f6(g), reference_daily_move_median=f6(fl))
        # the reference move has to clear the price grid and the reference's own
        # typical move between two days
        if row["step"] is None or row["reference_move"] is None or g is None \
                or abs(row["reference_move"]) < max(g, fl):
            row["state"] = "unread"
        elif row["step"] == 0:
            row["state"] = "did_not_move"
        elif (row["step"] > 0) == (row["reference_move"] > 0):
            row["state"] = "moved_with_reference"
        else:
            row["state"] = "moved_against_reference"
        out.append(row)
    return out


def arrivals_jump(panel, key, a, b):
    """Arrivals per filing before and inside [a, b], and the one split of
    [a - PRE_DAYS, b] into two levels that fits best. The split lives between
    two filings, so it is returned as that pair."""
    arr = panel.arrivals.get(key, {})
    pre = [arr[d] for d in arr if a - datetime.timedelta(PRE_DAYS) <= d < a]
    ins = [arr[d] for d in arr if a <= d <= b]
    ds = sorted(d for d in arr if a - datetime.timedelta(PRE_DAYS) <= d <= b)
    best = None
    for i in range(MIN_SEGMENT, len(ds) - MIN_SEGMENT + 1):
        l = statistics.median(arr[d] for d in ds[:i])
        r = statistics.median(arr[d] for d in ds[i:])
        # the split that leaves the least absolute deviation around the two medians;
        # the difference of medians alone is tied over a whole run of splits
        cost = sum(abs(arr[d] - l) for d in ds[:i]) + sum(abs(arr[d] - r) for d in ds[i:])
        if best is None or cost < best[0]:
            best = (cost, ds[i - 1], ds[i], l, r)
    post = [arr[d] for d in arr if b < d <= b + datetime.timedelta(PRE_DAYS)]
    return {"median_before": f6(statistics.median(pre)) if pre else None,
            "median_inside": f6(statistics.median(ins)) if ins else None,
            "median_after": f6(statistics.median(post)) if post else None,
            "filings_before": len(pre), "filings_inside": len(ins), "filings_after": len(post),
            "jump_between": [iso(best[1]), iso(best[2])] if best else None,
            "jump_day_values": [f6(arr[best[1]]), f6(arr[best[2]])] if best else None,
            "jump_days_after_start": (best[2] - a).days if best else None,
            "jump_left": f6(best[3]) if best else None, "jump_right": f6(best[4]) if best else None}


def weekly(a, b):
    monday = a - datetime.timedelta(a.weekday())
    while monday <= b:
        yield monday, monday + datetime.timedelta(6)
        monday += datetime.timedelta(7)


def h_levels(panel, key, a, b, variety):
    """Weekly local log price less the outside reference, and its mean before,
    inside and after [a, b]."""
    pr = panel.price(key)
    h = []
    for w0, w1 in weekly(a - datetime.timedelta(PRE_DAYS), b + datetime.timedelta(PRE_DAYS)):
        vals = []
        for d in days(w0, w1):
            if d in pr:
                ref = panel.reference(d, key[0], variety)
                if ref is not None:
                    vals.append(math.log(pr[d]) - ref)
        if vals:
            h.append([iso(w0), f6(statistics.fmean(vals)), len(vals)])
    hin = [x[1] for x in h if D.fromisoformat(x[0]) + datetime.timedelta(6) >= a
           and D.fromisoformat(x[0]) <= b]
    hpre = [x[1] for x in h if D.fromisoformat(x[0]) + datetime.timedelta(6) < a]
    hpost = [x[1] for x in h if D.fromisoformat(x[0]) > b]
    return h, hpre, hin, hpost


def ref_levels(panel, state, a, b, variety):
    def lev(lo, hi):
        xs = [x for x in (panel.reference(d, state, variety) for d in days(lo, hi)) if x is not None]
        return statistics.median(xs) if xs else None
    return (lev(a - datetime.timedelta(PRE_DAYS), a - ONE), lev(a, b),
            lev(b + ONE, min(b + datetime.timedelta(PRE_DAYS), panel.last_day)))


def reference_table(panel, ev, keys, a, b, grid):
    """Every reading of B146-8 that leans on the outside reference, once per
    definition of the reference: all varieties pooled, then each variety with
    enough outside rows. A change in h is read only where every definition gives
    the same sign and every one clears the price grid."""
    defs = [("all varieties", None, None)]
    for v, where in panel.reference_varieties(ev["state"], a, b).items():
        defs.append((v, v, where))
    refs = {}
    for name, v, where in defs:
        r0, r1, r2 = ref_levels(panel, ev["state"], a, b, v)
        row = {"before": f6(r0), "inside": f6(r1), "after": f6(r2),
               "move_inside": f6(r1 - r0) if None not in (r0, r1) else None,
               "move_after": f6(r2 - r1) if None not in (r1, r2) else None,
               "fixed_composition": panel.fixed_composition(ev["state"], a, b, v),
               "states": where, "units": {}}
        for key in keys:
            _, hpre, hin, hpost = h_levels(panel, key, a, b, v)
            hb = statistics.fmean(hpre) if hpre else None
            hi = statistics.fmean(hin) if hin else None
            ha = statistics.fmean(hpost) if hpost else None
            row["units"][" / ".join(key[1:])] = {
                "h_before": f6(hb), "h_inside": f6(hi), "h_after": f6(ha),
                "h_change_inside": f6(hi - hb) if None not in (hb, hi) else None}
        refs[name] = row
    verdict = {}
    for key in keys:
        m = " / ".join(key[1:])
        ch = {name: refs[name]["units"][m]["h_change_inside"] for name in refs}
        vals = [x for x in ch.values() if x is not None]
        same_sign = bool(vals) and (all(x > 0 for x in vals) or all(x < 0 for x in vals))
        clear = bool(vals) and grid is not None and all(abs(x) > grid for x in vals)
        # "every definition agrees" says nothing with one definition, and a window
        # of a few days holds a week or two of h: both are printed and not read
        several = len(ch) >= 2
        long_enough = (b - a).days + 1 >= READ_MIN_LEN
        verdict[m] = {"h_change_inside_by_reference": ch, "same_sign": same_sign,
                      "all_clear_the_grid": clear, "definitions": len(ch),
                      "window_days": (b - a).days + 1, "window_long_enough": long_enough,
                      "state": "read" if (same_sign and clear and len(vals) == len(ch)
                                          and several and long_enough) else "unread",
                      "own_variety": panel.dominant[key]}
    return {"references": refs, "h_change_by_unit": verdict}


def placebo_windows(panel, ev, keys, a, b):
    """The same table on windows of the same length that end before the event
    starts: what these markets' prices do against the outside when nothing is cut."""
    length = (b - a).days
    if length + 1 < PLACEBO_MIN_LEN:
        return None
    own = {" / ".join(k[1:]): panel.dominant[k] for k in keys}
    rows = []
    k = 0
    while len(rows) < PLACEBO_MAX:
        k += 1
        s0 = a - datetime.timedelta(PLACEBO_STEP * k)
        s1 = s0 + datetime.timedelta(length)
        if s1 >= a - ONE:
            continue
        if s0 - datetime.timedelta(PRE_DAYS) < panel.first_day:
            break
        r_all = ref_levels(panel, ev["state"], s0, s1, None)
        row = {"window": [iso(s0), iso(s1)],
               "reference_move_all": f6(r_all[1] - r_all[0]) if None not in r_all[:2] else None,
               "reference_move_own_variety": {}, "units": {}}
        for v in sorted(set(own.values()) - {None}):
            rv = ref_levels(panel, ev["state"], s0, s1, v)
            row["reference_move_own_variety"][v] = f6(rv[1] - rv[0]) if None not in rv[:2] else None
        for key in keys:
            pr = panel.price(key)
            pre = [pr[d] for d in pr if s0 - datetime.timedelta(PRE_DAYS) <= d < s0]
            ins = [pr[d] for d in pr if s0 <= d <= s1]
            arr = panel.arrivals.get(key, {})
            apre = [arr[d] for d in arr if s0 - datetime.timedelta(PRE_DAYS) <= d < s0]
            ains = [arr[d] for d in arr if s0 <= d <= s1]
            step = panel.rupee_step(key)
            if len(pre) < MIN_SEGMENT or len(ins) < MIN_SEGMENT:
                row["units"][" / ".join(key[1:])] = None
                continue
            p0, p1 = statistics.median(pre), statistics.median(ins)
            row["units"][" / ".join(key[1:])] = {
                "price_before": f6(p0), "price_inside": f6(p1),
                "steps": f6((p1 - p0) / step) if step else None,
                "arrivals_before": f6(statistics.median(apre)) if apre else None,
                "arrivals_inside": f6(statistics.median(ains)) if ains else None}
        rows.append(row)
    return rows


def placebo_summary(rows, units, grid, event_units):
    """Per market: placebo windows in which the outside reference moved by at least
    one grid step, and in how many of those the market's median price stayed within
    one of its own rupee steps, or did not move at all. The event's own window is
    put next to it."""
    out = {}
    for m in units:
        have = [r for r in rows if r["units"].get(m)]
        moved = [r for r in have if r["reference_move_all"] is not None and grid is not None
                 and abs(r["reference_move_all"]) >= grid]
        st = [abs(r["units"][m]["steps"]) for r in moved if r["units"][m]["steps"] is not None]
        ar = [r["units"][m]["arrivals_inside"] / r["units"][m]["arrivals_before"] for r in have
              if r["units"][m]["arrivals_before"] and r["units"][m]["arrivals_inside"] is not None]
        ev = event_units[m]
        ev_ratio = (ev["arrivals"]["median_inside"] / ev["arrivals"]["median_before"]
                    if ev["arrivals"]["median_before"] and ev["arrivals"]["median_inside"] is not None else None)
        out[m] = {"windows": len(have), "windows_reference_moved_a_grid_step": len(moved),
                  "of_those_price_within_one_step": sum(x <= 1.0 for x in st),
                  "of_those_price_unmoved": sum(x == 0 for x in st),
                  "event_window_steps": ev["price_steps_inside"],
                  "arrivals_ratio_placebo_min": f6(min(ar)) if ar else None,
                  "arrivals_ratio_placebo_median": f6(statistics.median(ar)) if ar else None,
                  "arrivals_ratio_event": f6(ev_ratio),
                  "placebo_windows_with_arrivals_ratio_at_or_below_event":
                      sum(x <= ev_ratio for x in ar) if ev_ratio is not None else None}
    return out


def cross_section(panel, state, a, b, event_ratios):
    """Arrivals over the same calendar window at every market outside the state:
    the ratio of the median inside [a, b] to the median in the PRE_DAYS before,
    for markets with MIN_SEGMENT filings on each side. The placebo windows all
    end before the event, so anything nationwide that falls inside the event's
    own window is seen only here. The same table a year earlier is put next to it."""
    def table(lo, hi):
        rows = []
        for key, arr in sorted(panel.arrivals.items()):
            if key[0] == state:
                continue
            pre = [arr[d] for d in arr if lo - datetime.timedelta(PRE_DAYS) <= d < lo]
            ins = [arr[d] for d in arr if lo <= d <= hi]
            if len(pre) < MIN_SEGMENT or len(ins) < MIN_SEGMENT:
                continue
            m0 = statistics.median(pre)
            if m0:
                rows.append((key[0], statistics.median(ins) / m0))
        return rows

    def summarise(rows):
        rs = [r for _, r in rows]
        below = {}
        for m, er in sorted(event_ratios.items()):
            if er is None:
                continue
            hit = collections.Counter(s for s, r in rows if r <= er)
            below[m] = {"event_ratio": f6(er), "markets": sum(hit.values()),
                        "share": f6(sum(hit.values()) / len(rs)) if rs else None,
                        "by_state": dict(sorted(hit.items()))}
        return {"markets": len(rs), "median_ratio": f6(statistics.median(rs)) if rs else None,
                "markets_by_state": dict(sorted(collections.Counter(s for s, _ in rows).items())),
                "p10_ratio": f6(quantile(rs, 0.1)), "at_or_below_event_ratio": below}
    back = datetime.timedelta(YEAR_BACK)
    return {"same_window": summarise(table(a, b)),
            "same_window_a_year_earlier": summarise(table(a - back, b - back))}


def closure_placebo(panel, ev, knobs, events):
    """For an event with closure documents: the share of its active markets that
    land in object_absent, on its own dates and with every document of the event
    moved back a week at a time. A market that goes silent for a fortnight with
    no document anywhere lands in the cell too, so the count on the event's own
    dates is read against this."""
    if not ev["checked"] or not ev["closures"]:
        return None

    def moved(k):
        dt = datetime.timedelta(CLOSURE_PLACEBO_STEP * k)

        def mv(doc):
            return doc and dict(doc, start=doc["start"] - dt, end=doc["end"] - dt)
        return dict(ev, transport=mv(ev["transport"]), info=mv(ev["info"]),
                    closures=tuple(mv(c) for c in ev["closures"]))

    def share(e):
        us = units_for(panel, e, knobs["prior_floor"])
        n = sum(classify(panel, k, e, knobs["stop_floor"])[0] == "object_absent" for k, _ in us)
        return n, len(us)
    taken = [(c["start"], c["end"]) for e in events if e["checked"] and e["state"] == ev["state"]
             for c in e["closures"]]
    n0, u0 = share(ev)
    rows, skipped, thin, k = [], 0, 0, 0
    while True:
        k += 1
        e = moved(k)
        lo, hi = event_start(e), event_end(e)
        if lo - datetime.timedelta(PRIOR_WINDOW) < panel.first_day:
            break
        if any(lo <= y and x <= hi for x, y in taken):
            skipped += 1
            continue
        n, u = share(e)
        if u < CLOSURE_PLACEBO_MIN_UNITS:
            thin += 1
            continue
        rows.append([iso(lo), n, u])
    sh = [n / u for _, n, u in rows]
    s0 = n0 / u0 if u0 else None
    return {"event": {"object_absent": n0, "units": u0, "share": f6(s0)},
            "windows": len(rows), "skipped_overlapping_a_closure_document": skipped,
            "skipped_fewer_active_markets_than_floor": thin,
            "share_median": f6(statistics.median(sh)) if sh else None,
            "share_p90": f6(quantile(sh, 0.9)), "share_max": f6(max(sh)) if sh else None,
            "windows_at_or_above_event_share": sum(x >= s0 for x in sh) if s0 is not None else None,
            "expected_in_cell_at_median_share": f6(statistics.median(sh) * u0) if sh else None,
            "rows": rows}


def absent_detail(panel, units, ev_by_id):
    """For the units in object_absent under a closure document: the last filing
    before the closure's first day and the next filing. A last filing well before
    the closure began is a silence the closure did not start."""
    out = {}
    for u in units:
        if u["cell"] != "object_absent":
            continue
        ev = ev_by_id[u["event"]]
        s, dis, m = u["key"]
        cov = [c["start"] for c in ev["closures"] if covers(c, dis, m, ev.get("excluded_markets", ()))]
        if not cov:
            continue
        cs = min(cov)
        ds = panel.per[u["key"]]
        i = bisect.bisect_left(ds, cs)
        last = ds[i - 1] if i else None
        nxt = ds[i] if i < len(ds) else None
        row = out.setdefault(u["event"], {"closure_first_day": iso(cs), "units": []})
        row["units"].append([" / ".join(u["key"][1:]), iso(last), iso(nxt)])
    for eid, row in out.items():
        cs = D.fromisoformat(row["closure_first_day"])
        lasts = [D.fromisoformat(x[1]) for x in row["units"] if x[1]]
        early = sum((cs - d).days > EARLY_DAYS for d in lasts)
        row["last_filing_dates"] = dict(sorted(collections.Counter(iso(d) for d in lasts).items()))
        row["last_filing_more_than_%d_days_before_the_closure" % EARLY_DAYS] = early
        row["last_filing_within_%d_days_of_the_closure" % EARLY_DAYS] = len(lasts) - early
        row["never_filed_again"] = sum(x[2] is None for x in row["units"])
    return out


def read_b8(panel, t_open, ev_by_id):
    """T cut, information open. ``t_open`` maps event id -> list of keys."""
    out = {}
    for eid, keys in sorted(t_open.items()):
        ev = ev_by_id[eid]
        a, b = ev["transport"]["start"], ev["transport"]["end"]
        units = {}
        for key in keys:
            pr = panel.price(key)
            h, hpre, hin, hpost = h_levels(panel, key, a, b, None)

            def level(lo, hi):
                xs = [pr[d] for d in pr if lo <= d <= hi]
                return f6(statistics.median(xs)) if xs else None
            units[" / ".join(key[1:])] = {
                "h_weekly": h,
                "h_before": f6(statistics.fmean(hpre)) if hpre else None,
                "h_inside": f6(statistics.fmean(hin)) if hin else None,
                "h_after": f6(statistics.fmean(hpost)) if hpost else None,
                "price_before": level(a - datetime.timedelta(PRE_DAYS), a - ONE),
                "price_inside": level(a, b),
                "price_after": level(b + ONE, b + datetime.timedelta(PRE_DAYS)),
                "rupee_step": f6(panel.rupee_step(key)),
                "filings_inside": len([d for d in panel.sets[key] if a <= d <= b]),
                "arrivals": arrivals_jump(panel, key, a, b)}
            u = units[" / ".join(key[1:])]
            u["price_steps_inside"] = (f6((u["price_inside"] - u["price_before"]) / u["rupee_step"])
                                       if None not in (u["price_inside"], u["price_before"], u["rupee_step"])
                                       else None)
        disp = []
        for w0, w1 in weekly(a - datetime.timedelta(PRE_DAYS), b):
            xs = [math.log(p) for p in (latest(panel.price(k), w0, w1) for k in keys) if p]
            if len(xs) >= MIN_MARKETS:
                disp.append([iso(w0), f6(mad(xs)), len(xs)])
        dpre = [x[1] for x in disp if D.fromisoformat(x[0]) + datetime.timedelta(6) < a]
        din = [x[1] for x in disp if D.fromisoformat(x[0]) + datetime.timedelta(6) >= a]
        def ref_level(lo, hi):
            xs = [x for x in (panel.reference(d, ev["state"]) for d in days(lo, hi)) if x is not None]
            return f6(statistics.median(xs)) if xs else None
        out[eid] = {"window": [iso(a), iso(b)], "units": units,
                    "reference_before": ref_level(a - datetime.timedelta(PRE_DAYS), a - ONE),
                    "reference_inside": ref_level(a, b),
                    "reference_after": ref_level(b + ONE, min(b + datetime.timedelta(PRE_DAYS),
                                                               panel.last_day)),
                    "expected_units":
                    sorted(" / ".join(k[1:]) for k in keys),
                    "dispersion_weekly": disp,
                    "dispersion_before": f6(statistics.median(dpre)) if dpre else None,
                    "dispersion_inside": f6(statistics.median(din)) if din else None,
                    "grid": {k: f6(v) if isinstance(v, float) else v
                             for k, v in panel.grid(keys).items()}}
        g = out[eid]["grid"]["median_step"]
        out[eid]["by_reference"] = reference_table(panel, ev, keys, a, b, g)
        pl = placebo_windows(panel, ev, keys, a, b)
        out[eid]["placebo"] = None if pl is None else {
            "windows": pl, "summary": placebo_summary(pl, sorted(units), g, units)}
        out[eid]["reference_daily_move"] = {
            name: reference_floor(panel, ev["state"], a, b, None if name == "all varieties" else name)
            for name in out[eid]["by_reference"]["references"]}
        ratios = {}
        for m, u in units.items():
            ar = u["arrivals"]
            ratios[m] = (ar["median_inside"] / ar["median_before"]
                         if ar["median_before"] and ar["median_inside"] is not None else None)
        out[eid]["arrivals_cross_section"] = (
            cross_section(panel, ev["state"], a, b, ratios) if (b - a).days + 1 >= PLACEBO_MIN_LEN else None)
        out[eid]["nationwide_events_inside_window"] = [
            {"date": iso(n["date"]), "what": n["what"], "days_after_window_start": (n["date"] - a).days}
            for n in NATIONWIDE if a <= n["date"] <= b]
    return out


def assign(panel, events, knobs, cut_kinds=FULL_CUT_KINDS, ignore_closure=False):
    """Every (market, event) unit at one knob point."""
    out = []
    for ev in events:
        for key, prior in units_for(panel, ev, knobs["prior_floor"]):
            cell, facts = classify(panel, key, ev, knobs["stop_floor"], cut_kinds, ignore_closure)
            out.append({"event": ev["id"], "key": key, "prior": prior, "cell": cell, "facts": facts})
    return out


def stop_cluster(panel, ev, knobs):
    """Markets of the event's state whose stop begins within the cluster window of
    the event's first date: how many stopped together."""
    start = event_start(ev)
    lo, hi = start - datetime.timedelta(knobs["cluster_window"]), start + datetime.timedelta(knobs["cluster_window"])
    n = 0
    for key, _ in units_for(panel, ev, knobs["prior_floor"]):
        ds = panel.per[key]
        for x, y in zip(ds, ds[1:] + [None]):
            hi_d = y if y is not None else panel.last_day + ONE
            if lo <= x <= hi and (hi_d - x).days >= knobs["stop_floor"]:
                n += 1
                break
    return n


def knob_sweep(panel, events):
    base = {(u["event"], u["key"]): u["cell"] for u in assign(panel, events, DEFAULT)}
    rows = []
    for pf in PRIOR_FLOORS:
        for sf in STOP_FLOORS:
            for cw in CLUSTER_WINDOWS:
                kn = {"prior_floor": pf, "stop_floor": sf, "cluster_window": cw}
                cur = {(u["event"], u["key"]): u["cell"] for u in assign(panel, events, kn)}
                changed = sorted("%s: %s  %s -> %s" % (e, " / ".join(k[1:]), base[(e, k)], c)
                                 for (e, k), c in cur.items() if (e, k) in base and base[(e, k)] != c)
                rows.append({"prior_floor": pf, "stop_floor": sf, "cluster_window": cw,
                             "units": len(cur), "dropped_vs_default": len(set(base) - set(cur)),
                             "added_vs_default": len(set(cur) - set(base)),
                             "cells": dict(sorted(collections.Counter(cur.values()).items())),
                             "both_cut_units": sum(c.startswith("both_cut") for c in cur.values()),
                             "changed_cell": changed,
                             "cluster_sizes": {ev["id"]: stop_cluster(panel, ev, kn)
                                               for ev in events if ev["checked"]}})
    return rows


def holiday_ratio(nat, shift=0):
    first, last = min(nat), max(nat)
    day_sum = nb_sum = 0.0
    cells = below = 0
    for mm, dd, _ in census.FIXED_HOLIDAYS:
        for y in range(first.year, last.year + 1):
            d = D(y, mm, dd) + datetime.timedelta(shift)
            if not (first + datetime.timedelta(census.NEIGHBOUR_DAYS) <= d
                    <= last - datetime.timedelta(census.NEIGHBOUR_DAYS)):
                continue
            nb = statistics.median(nat.get(d + datetime.timedelta(k), 0)
                                   for k in range(-census.NEIGHBOUR_DAYS, census.NEIGHBOUR_DAYS + 1) if k)
            day_sum += nat.get(d, 0)
            nb_sum += nb
            cells += 1
            below += nat.get(d, 0) < nb
    return (day_sum / nb_sum if nb_sum else float("nan")), cells, below


# ----------------------------------------------------------------------------- criteria
def crit(name, kind, passed, detail, **extra):
    out = {"name": name, "kind": kind, "passed": passed, "detail": detail}
    out.update(extra)
    return out


def event_row_complete(ev):
    if any(f not in ev for f in EVENT_FIELDS):
        return False
    if ev["checked"] and (not ev["sources"] or ev["grade"] not in (1, 2, 3)):
        return False
    for doc in (ev["transport"], ev["info"]):
        if doc is not None and not (isinstance(doc.get("start"), D) and isinstance(doc.get("end"), D)
                                    and doc["start"] <= doc["end"] and "districts" in doc):
            return False
    if ev["info"] is not None and "kind" not in ev["info"]:
        return False
    return all(isinstance(c.get("start"), D) and isinstance(c.get("end"), D)
               and c["start"] <= c["end"] and "districts" in c for c in ev["closures"])


def run(rows, counts, events=EVENTS, knobs=DEFAULT, sweep=None, shift=0, ignore_closure=False,
        b8_drop=None, b10_swap=False, b8_empty=None):
    """The whole station on one commodity's rows. The keyword arguments after
    ``knobs`` exist for the self-test: each plants one error."""
    rec = {}
    ev_by_id = {e["id"]: e for e in events}
    # B146-1
    ok1 = counts["kept"] > 0 and counts["files"] > 0
    if not ok1:
        return {"criteria": [crit("B146-1", "instrument", False,
                                  "no rows read: files %(files)d, lines %(lines)d" % counts)],
                "parse": counts}
    panel = Panel(rows)
    alld = sorted({r[6] for r in rows})
    rec["parse"] = dict(counts, markets=len(panel.per), states=len({k[0] for k in panel.per}),
                        first_day=iso(alld[0]), last_day=iso(alld[-1]),
                        dated_share=f6(counts["kept"] / max(counts["lines"] - counts["short"], 1)))
    c = [crit("B146-1", "instrument", ok1,
              "files %(files)d, lines %(lines)d, short %(short)d, undated %(undated)d, kept %(kept)d; "
              % counts + "markets %d, states %d, %s to %s"
              % (rec["parse"]["markets"], rec["parse"]["states"], alld[0], alld[-1]))]
    # B146-2
    nat = census.national_counts(panel.per)
    real, cells, below = holiday_ratio(nat, shift)
    sh = {s: holiday_ratio(nat, shift + s) for s in SHIFTS}
    shifted = {s: v[0] for s, v in sh.items()}
    # the calendar handed in must beat every shifted one, in both directions, on
    # the ratio and on the count of cells below their neighbours: a calendar that
    # is itself a shifted one has the true calendar among its comparisons
    # a shifted calendar with no filings at all around its days compares nothing
    usable = {k: v for k, v in sh.items() if v[1] > 0 and not math.isnan(v[0])}
    ok2 = (cells > 0 and any(k < 0 for k in usable) and any(k > 0 for k in usable)
           and all(real < v[0] and below > v[2] for v in usable.values()))
    rec["closure_readback"] = {"ratio": f6(real), "cells": cells, "cells_below_neighbours": below,
                               "shifted_ratios": {str(k): f6(v) for k, v in shifted.items()},
                               "shifted_calendars_compared": sorted(usable),
                               "shifted_cells_below": {str(k): v[2] for k, v in sh.items()},
                               "shifted_cells": {str(k): v[1] for k, v in sh.items()}}
    c.append(crit("B146-2", "known_answer", ok2,
                  "markets filing on three fixed closure days against the median of the 14 "
                  "neighbouring days: pooled ratio %.3f, %d of %d cells below; the same on calendars "
                  "shifted by %s days: %s, cells below %s"
                  % (real, below, cells, "/".join(map(str, SHIFTS)),
                     " / ".join("n/a" if math.isnan(shifted[s]) else "%.3f" % shifted[s] for s in SHIFTS),
                     " / ".join("%d of %d" % (sh[s][2], sh[s][1]) for s in SHIFTS))))
    # B146-3
    table = []
    for ev in events:
        dose, ndocs = dosage(ev)
        table.append({"id": ev["id"], "state": ev["state"], "label": ev["label"],
                      "checked": ev["checked"], "grade": ev["grade"], "sources": list(ev["sources"]),
                      "transport": ev["transport"] and {"start": iso(ev["transport"]["start"]),
                                                        "end": iso(ev["transport"]["end"]),
                                                        "districts": ev["transport"]["districts"],
                                                        "what": ev["transport"]["what"]},
                      "info": ev["info"] and {"start": iso(ev["info"]["start"]), "end": iso(ev["info"]["end"]),
                                              "kind": ev["info"]["kind"],
                                              "districts": ev["info"]["districts"], "what": ev["info"]["what"]},
                      "closures": [{"start": iso(x["start"]), "end": iso(x["end"]),
                                    "districts": x["districts"], "what": x["what"]} for x in ev["closures"]],
                      "excluded_markets": list(ev.get("excluded_markets", ())),
                      "execution_steps": ndocs, "dosage": dose,
                      "complete": event_row_complete(ev)})
    rec["events"] = table
    rec["physical_outage_screen"] = [
        {"id": o["id"], "state": o["state"], "start": iso(o["start"]), "label": o["label"], "checked": False,
         "active_units_by_prior_floor": {
             str(pf): len(units_for(panel, {"state": o["state"], "transport": {"start": o["start"], "end": o["start"]},
                                            "info": None, "closures": ()}, pf)) for pf in (1,) + PRIOR_FLOORS}}
        for o in OUTAGE_SCREEN]
    units = assign(panel, events, knobs, ignore_closure=ignore_closure)
    unchecked_ids = {e["id"] for e in events if not e["checked"]}
    leak = [u for u in units if u["event"] in unchecked_ids and u["cell"] != "unverified"]
    ok3 = all(t["complete"] for t in table) and not leak
    c.append(crit("B146-3", "bookkeeping", ok3,
                  "%d event rows, %d checked against a source, %d not; rows with every field: %d; "
                  "units of an unchecked row sitting in a cell that reads: %d"
                  % (len(table), sum(t["checked"] for t in table), len(unchecked_ids),
                     sum(t["complete"] for t in table), len(leak))))
    # B146-4
    def both(u, kinds):
        ev = ev_by_id[u["event"]]
        s, dis, m = u["key"]
        ex = ev.get("excluded_markets", ())
        return (ev["checked"] and covers(ev["transport"], dis, m, ex) and covers(ev["info"], dis, m, ex)
                and ev["info"]["kind"] in kinds)
    strict = [u for u in units if both(u, FULL_CUT_KINDS)]
    wide = [u for u in units if both(u, WIDE_CUT_KINDS)]
    anykind = [u for u in units if both(u, ("all", "all_internet", "mobile_data"))]
    ok4 = len(strict) > 0
    scope = {}
    for ev in events:
        if not (ev["checked"] and ev["transport"] and ev["info"]):
            continue
        mine = [u["key"] for u in units if u["event"] == ev["id"]]
        scope[ev["id"]] = {
            "information_kind": ev["info"]["kind"], "active_units_in_state": len(mine),
            "in_both_documents_by_district": sum(covers(ev["transport"], k[1], k[2]) and
                                                 covers(ev["info"], k[1], k[2]) for k in mine),
            "after_named_exclusions": sum(covers(ev["transport"], k[1], k[2], ev["excluded_markets"]) and
                                          covers(ev["info"], k[1], k[2], ev["excluded_markets"]) for k in mine),
            "excluded_markets": list(ev["excluded_markets"])}
    rec["premise_by_event"] = scope
    rec["premise"] = {"units_T_and_full_cut": len(strict), "units_T_and_all_data_cut": len(wide),
                      "units_T_and_any_information_order": len(anykind),
                      "any_order_units": sorted("%s: %s" % (u["event"], " / ".join(u["key"][1:]))
                                                for u in anykind)}
    c.append(crit("B146-4", "premise", ok4,
                  "units covered by a checked transport document and a checked full information cut, "
                  "active before the event: %d. With every data service stopped and voice up counted "
                  "as a cut: %d. With any information order at all: %d (%s)"
                  % (len(strict), len(wide), len(anykind),
                     "; ".join(rec["premise"]["any_order_units"]) or "none")
                  + ". Events carrying both documents: " + ("; ".join(
                      "%s (%s): %d active in the state, %d in both documents by district, %d after "
                      "the markets the orders leave out" % (e, v["information_kind"], v["active_units_in_state"],
                                                            v["in_both_documents_by_district"],
                                                            v["after_named_exclusions"])
                      for e, v in scope.items()) or "none")))
    # B146-5
    cells_count = collections.Counter(u["cell"] for u in units)
    by_event = collections.defaultdict(collections.Counter)
    for u in units:
        by_event[u["event"]][u["cell"]] += 1
    rec["mapping"] = {k: {"rule": v[0], "feeds": v[1], "verdict": v[2]} for k, v in MAPPING.items()}
    rec["cells"] = {k: cells_count.get(k, 0) for k in CELLS}
    rec["cells_by_event"] = {e: dict(sorted(v.items())) for e, v in sorted(by_event.items())}
    rec["units"] = [{"event": u["event"], "market": " / ".join(u["key"][1:]), "prior": u["prior"],
                     "cell": u["cell"], "T": u["facts"]["T"], "I": u["facts"]["I"],
                     "I_thin": u["facts"]["I_thin"], "closure": u["facts"]["closure"],
                     "stopped": u["facts"]["stopped"], "filed_in_window": u["facts"]["filed_in_window"],
                     "zero_arrivals": u["facts"]["zero_arrivals"]} for u in units]
    eighteenth = [u for u in units if u["cell"].startswith("both_cut") and u["facts"]["closure"]
                  and u["facts"]["stopped"] and not u["facts"]["filed_in_window"]]
    ok5 = (all(u["cell"] in CELLS for u in units) and set(MAPPING) == set(CELLS)
           and MAPPING["unverified"][2] is None and MAPPING["object_absent"][2] is None
           and not eighteenth)
    rec["object_absent_units"] = absent_detail(panel, units, ev_by_id)
    rec["object_absent_against_shifted_closures"] = {
        ev["id"]: cp for ev in events for cp in [closure_placebo(panel, ev, knobs, events)]
        if cp is not None and cp["event"]["object_absent"]}
    c.append(crit("B146-5", "own_reading", ok5,
                  "%d units, one cell each: %s. Units a closure document covers, that filed nothing, "
                  "and that sit in a both-cut cell: %d"
                  % (len(units), ", ".join("%s %d" % (k, rec["cells"][k]) for k in CELLS), len(eighteenth))
                  + "".join(
                      ". %s: object_absent %d of %d (%.3f); the same documents moved back a week at a "
                      "time, %d windows: median share %.3f, 90th percentile %.3f, highest %.3f, at or "
                      "above the event's share %d; last filing more than %d days before the closure "
                      "began: %d of %d"
                      % (eid, v["event"]["object_absent"], v["event"]["units"], v["event"]["share"],
                         v["windows"], v["share_median"] or 0, v["share_p90"] or 0, v["share_max"] or 0,
                         v["windows_at_or_above_event_share"] or 0, EARLY_DAYS,
                         rec["object_absent_units"].get(eid, {}).get(
                             "last_filing_more_than_%d_days_before_the_closure" % EARLY_DAYS, 0),
                         len(rec["object_absent_units"].get(eid, {}).get("units", ())))
                      for eid, v in rec["object_absent_against_shifted_closures"].items())))
    # sweep (B146-9) comes before B146-6 because the latter reads it
    sw = knob_sweep(panel, events) if sweep is None else sweep
    rec["knob_sweep"] = sw
    expected_points = len(PRIOR_FLOORS) * len(STOP_FLOORS) * len(CLUSTER_WINDOWS)
    ok9 = len(sw) == expected_points and len({(r["prior_floor"], r["stop_floor"], r["cluster_window"])
                                               for r in sw}) == expected_points
    moved = sorted({x for r in sw for x in r["changed_cell"]})
    c9 = crit("B146-9", "instrument", ok9,
              "%d of %d knob points run (prior floor %s, stop floor %s, cluster window %s; the flag "
              "counts the points and checks that they are distinct); units "
              "that change cell somewhere on the sweep: %d; both-cut units at each point: %s"
              % (len(sw), expected_points, "/".join(map(str, PRIOR_FLOORS)),
                 "/".join(map(str, STOP_FLOORS)), "/".join(map(str, CLUSTER_WINDOWS)), len(moved),
                 " ".join(str(r["both_cut_units"]) for r in sw)))
    # B146-6
    inside = collections.defaultdict(list)
    for u in units:
        if u["cell"] == "both_cut_read_inside":
            inside[u["event"]].append(u["key"])
    both_inside = {}
    for eid, keys in inside.items():
        ev = ev_by_id[eid]
        both_inside[eid] = (keys, max(ev["transport"]["start"], ev["info"]["start"]),
                            min(ev["transport"]["end"], ev["info"]["end"]))
    flips = len({r["both_cut_units"] for r in sw}) > 1
    b6 = read_b6(panel, both_inside, ok4, flips)
    rec["B146-6"] = b6
    states6 = sorted({r["state"] for r in b6}) or ["unread"]
    read6 = [r for r in b6 if r["state"] != "unread"]
    rec["mapping_B146-6"] = {k: {"verdict": MAPPING_B6[k], "rule": MAPPING_B6_WORDS[k]} for k in MAPPING_B6}
    rec["mapping_B146-7"] = dict(MAPPING_B7)
    pass6 = None if not read6 else all(MAPPING_B6[r["state"]] for r in read6)
    c.append(crit("B146-6", "own_reading", pass6,
                  "both edges cut and still filing: %d event groups; states %s. %s"
                  % (len(b6), ", ".join(states6),
                     "; ".join("%s %s: %d markets, dispersion %.4f -> %.4f against a grid of %.4f"
                               % (r["event"], r["variety"], r["markets"], r["at_cut"] or 0,
                                  r["at_end"] or 0, r["grid"] or 0) for r in b6 if r["markets"])
                     or "No unit in the cell, so there is nothing to read; the cell is not scored."),
                  state="/".join(states6)))
    # B146-7
    edges = []
    grid_of = {}
    for u in units:
        if u["cell"] == "both_cut_edges_only":
            a, b = u["facts"]["window"]
            pairs = stop_over(panel, u["key"], a, b, 1)
            if pairs:
                edges.append((u["event"], u["key"], pairs[0]))
            grid_of.setdefault(u["event"], panel.grid(
                [x["key"] for x in units if x["event"] == u["event"]])["median_step"])
    floor_of = {ev["id"]: reference_floor(panel, ev["state"], event_start(ev) - datetime.timedelta(PRE_DAYS),
                                          min(event_end(ev), panel.last_day))
                for ev in events if ev["checked"] and (ev["info"] or ev["transport"])}
    rec["reference_daily_move_by_event"] = floor_of
    b7 = read_b7(panel, edges, grid_of, floor_of)
    rec["B146-7"] = b7
    read7 = [r for r in b7 if r["state"] != "unread"]
    n_edges_only = sum(u["cell"] == "both_cut_edges_only" for u in units)
    pass7 = None if not read7 else (len(b7) == n_edges_only and all(r.get("state") in MAPPING_B7 for r in b7))
    c.append(crit("B146-7", "own_reading", pass7,
                  "both edges cut and not filing: %d units, %d with a step that can be read. %s"
                  % (n_edges_only, len(read7),
                     "; ".join("%s %s: %s, step %s, reference %s"
                               % (r["event"], r["market"], r["state"],
                                  "n/a" if r["step"] is None else "%+.4f" % r["step"],
                                  "n/a" if r["reference_move"] is None else "%+.4f" % r["reference_move"])
                               for r in b7) or "No unit in the cell; not scored."),
                  state="/".join(sorted({r["state"] for r in b7}) or ["unread"])))
    # steps across stops that overlap any information order, whatever the cell: printed only
    aside = []
    for u in units:
        ev = ev_by_id[u["event"]]
        if not ev["checked"] or not ev["info"] or not covers(ev["info"], u["key"][1], u["key"][2],
                                                             ev.get("excluded_markets", ())):
            continue
        for pair in stop_over(panel, u["key"], ev["info"]["start"], ev["info"]["end"], 2):
            row = edge_step(panel, u["key"], pair, u["key"][0])
            fl = floor_of.get(u["event"], {}).get("median")
            f9 = floor_of.get(u["event"], {}).get("p90")
            row.update(event=u["event"], market=" / ".join(u["key"][1:]), cell=u["cell"],
                       reference_daily_move_median=fl, reference_daily_move_p90=f9,
                       reference_move_exceeds_it=(None if row["reference_move"] is None or fl is None
                                                  else abs(row["reference_move"]) > fl),
                       reference_move_exceeds_p90=(None if row["reference_move"] is None or f9 is None
                                                   else abs(row["reference_move"]) > f9))
            aside.append(row)
    rec["steps_across_stops_under_information_orders"] = aside
    # B146-8
    t_open = collections.defaultdict(list)
    for u in units:
        if u["cell"] == "T_cut_I_open":
            t_open[u["event"]].append(u["key"])
    b8 = read_b8(panel, t_open, ev_by_id)
    if b8_drop:
        for eid in b8:
            b8[eid]["units"].pop(b8_drop, None)
    if b8_empty:
        for eid in b8:
            if b8_empty in b8[eid]["units"]:
                b8[eid]["units"][b8_empty]["h_weekly"] = []
    rec["B146-8"] = b8
    n8 = sum(len(v["units"]) for v in b8.values())
    ok8 = (n8 > 0 and all(sorted(v["units"]) == v["expected_units"] for v in b8.values())
           and all(x["h_weekly"] for v in b8.values() for x in v["units"].values()))
    c.append(crit("B146-8", "own_reading", ok8 if t_open else None,
                  "transport cut, information open: %d units in %d events. %s"
                  % (n8, len(b8), "; ".join(
                      "%s: %d markets, weekly dispersion %s before and %s inside against a price "
                      "grid of %s" % (eid, len(v["units"]),
                                      "%.4f" % v["dispersion_before"] if v["dispersion_before"] is not None else "n/a",
                                      "%.4f" % v["dispersion_inside"] if v["dispersion_inside"] is not None else "n/a",
                                      "%.4f" % v["grid"]["median_step"] if v["grid"]["median_step"] else "n/a")
                      for eid, v in b8.items()) or "No unit in the cell on this commodity; not scored.")
                  + ("" if not b8 else " Change in h inside the window, by definition of the outside "
                     "reference: " + "; ".join(
                         "%s %s (%s)" % (m, x["state"], ", ".join(
                             "%s %s" % (n, "n/a" if c is None else "%+.3f" % c)
                             for n, c in x["h_change_inside_by_reference"].items()))
                         for v in b8.values() for m, x in v["by_reference"]["h_change_by_unit"].items())
                     + "".join(
                         ". %s, arrivals inside the window over arrivals before, same calendar window at "
                         "markets outside the state: %d markets, median ratio %.3f; at or below each "
                         "unit's own ratio: %s; nationwide events inside the window: %s"
                         % (eid, v["arrivals_cross_section"]["same_window"]["markets"],
                            v["arrivals_cross_section"]["same_window"]["median_ratio"] or 0,
                            ", ".join("%s (%.3f) %d" % (m, x["event_ratio"], x["markets"]) for m, x in
                                      v["arrivals_cross_section"]["same_window"]["at_or_below_event_ratio"].items()),
                            "; ".join("%s, day %d" % (n["date"], n["days_after_window_start"])
                                      for n in v["nationwide_events_inside_window"]) or "none")
                         for eid, v in b8.items() if v["arrivals_cross_section"]))))
    c.append(c9)
    # B146-10
    ev_with_units = sorted(by_event)
    n_events, n_units = len(ev_with_units), len(units)
    if b10_swap:
        n_events = n_units + 1
    rec["independent_units"] = {"events_with_units": n_events, "units": n_units,
                                "per_event": {e: sum(v.values()) for e, v in sorted(by_event.items())}}
    ok10 = n_events <= n_units and n_events == len(rec["independent_units"]["per_event"]) \
        and sum(rec["independent_units"]["per_event"].values()) == n_units
    c.append(crit("B146-10", "bookkeeping", ok10,
                  "events with at least one unit: %d; units: %d; per event: %s"
                  % (n_events, n_units, ", ".join("%s %d" % kv for kv in
                                                  rec["independent_units"]["per_event"].items()) or "none")))
    order = ["B146-%d" % i for i in range(1, 11)]
    rec["criteria"] = sorted(c, key=lambda x: order.index(x["name"]))
    return rec


# ----------------------------------------------------------------------------- self-test
def fixture(diverge=False, markets=4, stopper_closed=True, stopper=True, ref_jump=0.0, flat_arrivals=False,
            ref_noise=0.0):
    """Two states. X has an event from 1 Mar to 20 Mar 2015 (transport) and 5 Mar to
    15 Mar (a full information cut) in districts A and B; B is under a closure
    document and its market stops. In A, ``markets`` markets keep filing; A9 stops
    with no closure. State Y files every day and is the outside reference."""
    rows = []
    start, end = D(2015, 1, 1), D(2015, 4, 30)
    for d in days(start, end):
        yp = 5000.0 * (math.exp(ref_jump) if d >= D(2015, 3, 10) else 1.0)
        if ref_noise and d.toordinal() % 3 == 1:
            yp *= math.exp(ref_noise)      # every third day the whole reference sits higher
        for i in range(4):
            rows.append(("Y", "Q", "Y%d" % i, "Other", 10.0, yp + 100 * i, d))
        for i in range(markets):
            p = 5000.0
            if diverge and d >= D(2015, 3, 8):
                p = 5000.0 + 800.0 * i
            arr = 10.0 if (flat_arrivals or d < D(2015, 3, 10)) else 4.0
            rows.append(("X", "A", "A%d" % i, "Other", arr, p, d))
        if stopper and not (D(2015, 3, 1) <= d <= D(2015, 3, 20)):
            rows.append(("X", "A", "A9", "Other", 10.0, 5000.0 if d < D(2015, 3, 1) else 5600.0, d))
        if not (D(2015, 3, 1) <= d <= D(2015, 3, 20)):
            rows.append(("X", "B", "B0", "Other", 10.0, 5000.0, d))
    # give every A series three small steps well before the event: the price grid
    out = []
    for r in rows:
        if r[0] == "X" and r[1] == "A" and r[2] != "A9" and (
                r[6] < D(2015, 1, 15) or D(2015, 1, 25) <= r[6] < D(2015, 2, 5)):
            r = r[:5] + (4900.0,) + r[6:]
        out.append(r)
    ev = {"id": "FX", "state": "X", "label": "fixture",
          "transport": {"start": D(2015, 3, 1), "end": D(2015, 3, 20), "districts": ("A", "B"), "what": "t"},
          "info": {"start": D(2015, 3, 5), "end": D(2015, 3, 15), "kind": "all",
                   "districts": ("A", "B"), "what": "i"},
          "closures": ({"start": D(2015, 3, 1), "end": D(2015, 3, 20), "districts": ("B",),
                        "checked": True, "what": "c"},) if stopper_closed else (),
          "sources": ("fixture",), "grade": 3, "checked": True, "excluded_markets": ()}
    counts = {"files": 1, "lines": len(out), "short": 0, "undated": 0, "kept": len(out)}
    return out, counts, ev


def by_name(rec):
    return {x["name"]: x for x in rec["criteria"]}


def selftest():
    fails = []

    def expect(cond, msg):
        print("  %s  %s" % ("ok  " if cond else "FAIL", msg))
        if not cond:
            fails.append(msg)

    rows, counts, ev = fixture()
    base = run(rows, counts, events=(ev,))
    cr = by_name(base)
    cell = {u["market"]: u["cell"] for u in base["units"]}
    print("fixture with a known answer")
    expect(cell.get("B / B0") == "object_absent", "closed and silent market is object_absent, got %s" % cell.get("B / B0"))
    expect(cell.get("A / A0") == "both_cut_read_inside", "filing market under both documents reads inside")
    expect(cell.get("A / A9") == "both_cut_edges_only", "silent market with no closure has only its edges")
    expect(all(cr[n]["passed"] is True for n in ("B146-1", "B146-3", "B146-4", "B146-5", "B146-9", "B146-10")),
           "structural criteria pass on the fixture")
    expect(cr["B146-6"]["state"] == "did_not_grow" and cr["B146-6"]["passed"] is False,
           "identical prices every day: dispersion did not grow")
    print("each criterion fed an input that must fail it")
    # B146-1: an empty directory
    with tempfile.TemporaryDirectory() as tmp:
        old = census.DATA
        census.DATA = Path(tmp)
        try:
            r0, c0 = census.read_csv("nothing here")
        finally:
            census.DATA = old
    expect(by_name(run(r0, c0, events=(ev,)))["B146-1"]["passed"] is False, "B146-1 fails on an empty directory")
    # B146-2: closures planted on the fixed days, then the calendar shifted
    hol = [r for r in rows if not any((r[6].month, r[6].day) == (m, d) for m, d, _ in census.FIXED_HOLIDAYS)
           or r[2] == "Y0"]
    # the fixture spans January to April, so add a second year to give neighbours
    hol2 = hol + [r[:6] + (r[6].replace(year=2016),) for r in hol if r[6].month <= 2]
    cnt = dict(counts, kept=len(hol2), lines=len(hol2))
    expect(by_name(run(hol2, cnt, events=(ev,)))["B146-2"]["passed"] is True, "B146-2 reads planted closures back")
    expect(by_name(run(hol2, cnt, events=(ev,), shift=10))["B146-2"]["passed"] is False,
           "B146-2 fails when the calendar it is handed is the shifted one")
    # B146-3: an unchecked row carrying dates
    un = dict(ev, checked=False, id="FXU")
    r3 = run(rows, counts, events=(un,))
    expect(all(u["cell"] == "unverified" for u in r3["units"]) and len(r3["units"]) > 0,
           "units of an unchecked row all sit in unverified")
    bad = dict(ev, sources=())
    expect(by_name(run(rows, counts, events=(bad,)))["B146-3"]["passed"] is False,
           "B146-3 fails on a checked row with no source")
    # B146-4: take the information document away, then make it mobile data only
    expect(by_name(run(rows, counts, events=(dict(ev, info=None),)))["B146-4"]["passed"] is False,
           "B146-4 fails with the information document removed")
    thin = dict(ev, info=dict(ev["info"], kind="mobile_data"))
    r4 = run(rows, counts, events=(thin,))
    expect(by_name(r4)["B146-4"]["passed"] is False and
           {u["market"]: u["cell"] for u in r4["units"]}["A / A0"] == "T_cut_I_open",
           "a mobile-data-only order is not a cut: premise false, unit sits in T_cut_I_open")
    # B146-5: the classifier made blind to closures
    r5 = run(rows, counts, events=(ev,), ignore_closure=True)
    expect(by_name(r5)["B146-5"]["passed"] is False,
           "B146-5 fails when a closed, silent market is put in a both-cut cell")
    # B146-6: diverging prices, and fewer than three markets
    r6 = run(*fixture(diverge=True)[:2], events=(ev,))
    expect(by_name(r6)["B146-6"]["state"] == "grew" and by_name(r6)["B146-6"]["passed"] is True,
           "diverging prices: dispersion grew")
    r6b = run(*fixture(diverge=True, markets=2)[:2], events=(ev,))
    expect(by_name(r6b)["B146-6"]["state"] == "unread" and by_name(r6b)["B146-6"]["passed"] is None,
           "two markets: unread, no verdict")
    r6c = run(*fixture(diverge=True)[:2], events=(thin,))
    expect(by_name(r6c)["B146-6"]["passed"] is None, "premise false: B146-6 carries no verdict")
    # B146-7: reference that does not move, then one that does
    expect(by_name(base)["B146-7"]["state"] == "unread" and by_name(base)["B146-7"]["passed"] is None,
           "reference move smaller than the grid: unread, no verdict")
    r7 = run(*fixture(ref_jump=0.2)[:2], events=(ev,))
    expect(by_name(r7)["B146-7"]["state"] == "moved_with_reference" and by_name(r7)["B146-7"]["passed"] is True,
           "reference moved and the market's step went with it")
    # B146-8: a T-cut-only event, then one active market dropped from the table
    tonly = dict(ev, info=None, closures=())
    r8 = run(rows, counts, events=(tonly,))
    expect(by_name(r8)["B146-8"]["passed"] is True, "B146-8 passes with every active market in the table")
    a0 = r8["B146-8"]["FX"]["units"]["A / A0"]["arrivals"]
    expect(a0["jump_between"] == ["2015-03-09", "2015-03-10"] and a0["jump_days_after_start"] == 9,
           "arrivals jump is found between the two filings where it was planted")
    expect(by_name(run(rows, counts, events=(tonly,), b8_drop="A / A1"))["B146-8"]["passed"] is False,
           "B146-8 fails with one active market missing")
    # B146-9: one point short
    full = knob_sweep(Panel(rows), (ev,))
    expect(by_name(run(rows, counts, events=(ev,), sweep=full[:-1]))["B146-9"]["passed"] is False,
           "B146-9 fails one knob point short")
    expect(by_name(run(rows, counts, events=(ev,), sweep=full[:-1] + full[:1]))["B146-9"]["passed"] is False,
           "B146-9 fails when a point is run twice in place of another")
    # B146-10
    expect(by_name(run(rows, counts, events=(ev,), b10_swap=True))["B146-10"]["passed"] is False,
           "B146-10 fails when the event count exceeds the unit count")
    # stop floor is live: B0's stop is 21 days, so a floor of 30 un-stops it
    c30, _ = classify(Panel(rows), ("X", "B", "B0"), ev, 30)
    expect(c30 != "object_absent", "a stop shorter than the floor is not a stop (floor is live), got %s" % c30)
    # a market the order leaves out, a market too thin before the event, the reference
    ex = dict(ev, excluded_markets=("A0",))
    cx = {u["market"]: u["cell"] for u in run(rows, counts, events=(ex,))["units"]}
    expect(cx["A / A0"] == "ordinary" and cx["A / A1"] == "both_cut_read_inside",
           "a market the order leaves out is ordinary; its neighbour is not")
    thin_rows = rows + [("X", "A", "A7", "Other", 1.0, 5000.0, D(2015, 2, 20)),
                        ("X", "A", "A7", "Other", 1.0, 5000.0, D(2015, 3, 7))]
    names = {u["market"] for u in run(thin_rows, dict(counts, kept=len(thin_rows)), events=(ev,))["units"]}
    expect("A / A7" not in names and "A / A0" in names, "a market with one prior filing is not a unit")
    pj = Panel(fixture(ref_jump=0.2)[0])
    want = statistics.median(math.log(5000.0 * math.exp(0.2) + 100 * i) for i in range(4))
    expect(abs(pj.reference(D(2015, 3, 12), "X") - want) < 1e-12 and
           abs(pj.reference(D(2015, 3, 12), "Y") - want) > 0.05,
           "the reference leaves out the event's own state")
    two = Panel([r for r in fixture(ref_jump=0.2)[0] if r[2] not in ("Y2", "Y3")])
    expect(abs(two.reference(D(2015, 3, 12), "X") - math.log(5000.0 * math.exp(0.2))) < 1e-12,
           "on a thin day the reference widens by days and still leaves out the event's state")
    # the decisive window of a both-cut unit is the overlap of the two documents
    a8 = rows + [("X", "A", "A8") + r[3:] for r in rows
                 if r[2] == "A0" and not D(2015, 3, 5) <= r[6] <= D(2015, 3, 15)]
    c8 = {u["market"]: u["cell"] for u in run(a8, dict(counts, kept=len(a8)), events=(ev,))["units"]}
    expect(c8["A / A8"] == "both_cut_edges_only",
           "silent only where both documents overlap: edges only, got %s" % c8["A / A8"])
    # filings with zero arrivals are rows without a price behind them
    z = [r[:4] + (0.0,) + r[5:] if r[2] == "A1" and D(2015, 3, 1) <= r[6] <= D(2015, 3, 20) else r
         for r in rows]
    cz = {u["market"]: u["cell"] for u in run(z, counts, events=(tonly,))["units"]}
    expect(cz["A / A1"] == "object_absent" and cz["A / A2"] == "T_cut_I_open",
           "every filing in the window at zero arrivals: object_absent")
    # mapping: the two cells without a verdict
    expect(MAPPING["unverified"][2] is None and MAPPING["object_absent"][2] is None,
           "unverified and object_absent map to no verdict")
    # dosage: three documents, runs partition the event
    dose, nd = dosage(ev)
    expect(nd == 3 and sum(x["days"] for x in dose) == 20 and len(dose) == 3,
           "dosage: 3 documents, runs cover the 20 days in 3 runs")
    # B146-2 on the panel itself: the fixture's closures sit on the fixed days by
    # construction, so the flag is also handed a shifted calendar on real rows
    real_rows, real_counts = census.read_csv(census.COMMODITIES[0])
    if real_rows:
        expect(by_name(run(real_rows, real_counts, shift=0, events=()))["B146-2"]["passed"] is True
               and by_name(run(real_rows, real_counts, shift=10, events=()))["B146-2"]["passed"] is False,
               "B146-2 on the panel: passes on the true calendar, fails on the one shifted by 10 days")
    else:
        print("  ....  panel not on disk: the real-rows check of B146-2 was not run")
    # B146-2 compares in both directions: with only forward shifts it has no verdict to give
    global SHIFTS
    keep_shifts = SHIFTS
    try:
        SHIFTS = (10, 20, 40)
        expect(by_name(run(hol2, cnt, events=(ev,)))["B146-2"]["passed"] is False,
               "B146-2 fails when the shifted calendars all lie on one side")
    finally:
        SHIFTS = keep_shifts
    # B146-8: the outside reference, one definition per variety
    global REF_MIN_OBS, PLACEBO_MIN_LEN, PLACEBO_STEP, PRE_DAYS, READ_MIN_LEN, NATIONWIDE, CLOSURE_PLACEBO_MIN_UNITS
    keep = (REF_MIN_OBS, PLACEBO_MIN_LEN, PLACEBO_STEP, PRE_DAYS)
    keep_read, keep_nat, keep_cpu = READ_MIN_LEN, NATIONWIDE, CLOSURE_PLACEBO_MIN_UNITS
    try:
        REF_MIN_OBS = 10
        READ_MIN_LEN = 10
        jrows, jcounts, _ = fixture(ref_jump=0.2)
        flat = [("Z", "Q", "Z%d" % i, "Dal", 10.0, 9000.0 + 100 * i, d)
                for d in days(D(2015, 1, 1), D(2015, 4, 30)) for i in range(4)]
        both_move = [("Z", "Q", "Z%d" % i, "Dal", 10.0,
                      (9000.0 + 100 * i) * (math.exp(0.2) if d >= D(2015, 3, 10) else 1.0), d)
                     for d in days(D(2015, 1, 1), D(2015, 4, 30)) for i in range(4)]
        ra = run(jrows + flat, dict(jcounts, kept=len(jrows) + len(flat)), events=(tonly,))
        byr = ra["B146-8"]["FX"]["by_reference"]
        expect(set(byr["references"]) == {"all varieties", "Other", "Dal"},
               "B146-8 prints one reference per variety next to the pooled one")
        expect(byr["h_change_by_unit"]["A / A0"]["state"] == "unread"
               and abs(byr["references"]["Dal"]["units"]["A / A0"]["h_change_inside"]) < 0.02
               and byr["references"]["Other"]["units"]["A / A0"]["h_change_inside"] < -0.05,
               "a change in h that one variety's reference does not show is unread")
        rb = run(jrows + both_move, dict(jcounts, kept=len(jrows) + len(both_move)), events=(tonly,))
        expect(rb["B146-8"]["FX"]["by_reference"]["h_change_by_unit"]["A / A0"]["state"] == "read",
               "a change in h that every reference shows, above the grid, is read")
        READ_MIN_LEN = 30
        rshort = run(jrows + both_move, dict(jcounts, kept=len(jrows) + len(both_move)), events=(tonly,))
        ush = rshort["B146-8"]["FX"]["by_reference"]["h_change_by_unit"]["A / A0"]
        expect(ush["same_sign"] and ush["all_clear_the_grid"] and ush["state"] == "unread",
               "the same change on a window shorter than the reading floor is unread")
        READ_MIN_LEN = 10
        REF_MIN_OBS = 10 ** 6
        rone = run(jrows, jcounts, events=(tonly,))
        uone = rone["B146-8"]["FX"]["by_reference"]["h_change_by_unit"]["A / A0"]
        expect(uone["definitions"] == 1 and uone["all_clear_the_grid"] and uone["state"] == "unread",
               "a change in h under one definition of the reference only is unread")
        REF_MIN_OBS = 10
        small = [("Z", "Q", "Z%d" % i, "Dal", 10.0,
                  (9000.0 + 100 * i) * (math.exp(0.03) if d >= D(2015, 3, 10) else 1.0), d)
                 for d in days(D(2015, 1, 1), D(2015, 4, 30)) for i in range(4)]
        rs = run(jrows + small, dict(jcounts, kept=len(jrows) + len(small)), events=(tonly,))
        us = rs["B146-8"]["FX"]["by_reference"]["h_change_by_unit"]["A / A0"]
        expect(us["same_sign"] and not us["all_clear_the_grid"] and us["state"] == "unread",
               "a change in h of one sign under every reference, under the grid in one of them, is unread")
        fc = Panel(jrows).fixed_composition("X", D(2015, 3, 1), D(2015, 3, 20))
        expect(fc["series"] == 4 and 0.19 < fc["before_to_inside"] < 0.2001 and abs(fc["inside_to_after"]) < 1e-9,
               "fixed-composition reference: four series, the planted jump and nothing after it")
        fd = Panel(jrows + flat).fixed_composition("X", D(2015, 3, 1), D(2015, 3, 20), "Dal")
        expect(fd["series"] == 4 and abs(fd["before_to_inside"]) < 1e-9,
               "fixed-composition reference keeps to the variety it is asked for")
        # the placebo table: windows of the event's length that end before it starts
        PLACEBO_MIN_LEN, PLACEBO_STEP, PRE_DAYS = 10, 10, 20
        rp = run(rows, counts, events=(tonly,))["B146-8"]["FX"]["placebo"]
        w = rp["windows"]
        expect(len(w) == 1 and w[0]["window"] == ["2015-01-30", "2015-02-18"]
               and w[0]["units"]["A / A0"]["steps"] == 0.5,
               "placebo: one window fits before the event, and its price step is the planted one")
        expect(rp["summary"]["A / A0"]["placebo_windows_with_arrivals_ratio_at_or_below_event"] == 0
               and rp["summary"]["A / A0"]["arrivals_ratio_event"] == 0.4,
               "placebo: no window has arrivals falling as far as the planted fall inside the event")
        # the cross-section: the same calendar window at markets outside the state
        fall = [("W", "Q", "W0", "Other", 10.0 if d < D(2015, 3, 5) else 4.0, 5000.0, d)
                for d in days(D(2015, 1, 1), D(2015, 4, 30))]
        # a market with three filings before the window falls too, and is too thin to count
        fall += [("V", "Q", "V0", "Other", 10.0 if d < D(2015, 3, 1) else 1.0, 5000.0, d)
                 for d in days(D(2015, 2, 26), D(2015, 4, 30))]
        NATIONWIDE = ({"date": D(2015, 3, 4), "what": "planted"},)
        rx = run(rows + fall, dict(counts, kept=len(rows) + len(fall)), events=(tonly,))["B146-8"]["FX"]
        cs = rx["arrivals_cross_section"]["same_window"]
        expect(cs["markets"] == 5 and cs["median_ratio"] == 1.0 and cs["markets_by_state"] == {"W": 1, "Y": 4}
               and cs["at_or_below_event_ratio"]["A / A0"]["markets"] == 1
               and cs["at_or_below_event_ratio"]["A / A0"]["by_state"] == {"W": 1},
               "cross-section: five outside markets, the one planted fall, equal to the event's, is the one counted")
        expect(rx["arrivals_cross_section"]["same_window_a_year_earlier"]["markets"] == 0,
               "cross-section a year earlier: no market has rows there, and none is counted")
        expect(rx["nationwide_events_inside_window"] == [
                   {"date": "2015-03-04", "what": "planted", "days_after_window_start": 3}],
               "a nationwide date inside the window is printed with its day of the window")
        NATIONWIDE = ({"date": D(2015, 3, 25), "what": "planted outside"},)
        expect(run(rows, counts, events=(tonly,))["B146-8"]["FX"]["nationwide_events_inside_window"] == [],
               "a nationwide date outside the window is not printed")
        NATIONWIDE = keep_nat
        ax = rx["units"]["A / A0"]["arrivals"]
        expect(ax["jump_day_values"] == [10.0, 4.0] and ax["median_after"] == 4.0 and ax["filings_after"] == 20,
               "arrivals: the two filings either side of the jump, and the level after the window")
        frows, fcounts, _ = fixture(flat_arrivals=True)
        rf = run(frows, fcounts, events=(tonly,))["B146-8"]["FX"]["placebo"]
        expect(rf["summary"]["A / A0"]["placebo_windows_with_arrivals_ratio_at_or_below_event"] == 1,
               "placebo: with flat arrivals the event's window is no different from the placebo one")
        PLACEBO_MIN_LEN = 30
        expect(run(rows, counts, events=(tonly,))["B146-8"]["FX"]["placebo"] is None,
               "an event shorter than the placebo floor gets no placebo table")
    finally:
        REF_MIN_OBS, PLACEBO_MIN_LEN, PLACEBO_STEP, PRE_DAYS = keep
        READ_MIN_LEN, NATIONWIDE = keep_read, keep_nat
    # third round: the flags and floors added after the second
    expect(by_name(run(rows, counts, events=(tonly,), b8_empty="A / A1"))["B146-8"]["passed"] is False,
           "B146-8 fails when one unit's weekly series is empty")
    back = dict(ev, closures=(dict(ev["closures"][0], start=D(2015, 3, 20), end=D(2015, 3, 1)),))
    expect(by_name(run(rows, counts, events=(back,)))["B146-3"]["passed"] is False,
           "B146-3 fails on a closure document that ends before it starts")
    nodis = dict(ev, closures=({k: v for k, v in ev["closures"][0].items() if k != "districts"},))
    expect(event_row_complete(nodis) is False, "B146-3: a closure document without its districts is incomplete")
    # the reference's own daily move is a floor under a single-day reference move
    fl0 = reference_floor(Panel(rows), "X", D(2015, 1, 10), D(2015, 3, 20))
    nrows, ncounts, _ = fixture(ref_jump=0.2, ref_noise=0.5)
    fl1 = reference_floor(Panel(nrows), "X", D(2015, 1, 10), D(2015, 3, 20))
    expect(fl0["median"] == 0.0 and 0.45 < fl1["median"] < 0.55 and fl1["day_pairs"] == 69,
           "reference floor: zero on a flat reference, the planted swing on a noisy one")
    r7n = run(nrows, ncounts, events=(ev,))
    expect(by_name(r7n)["B146-7"]["state"] == "unread" and by_name(r7n)["B146-7"]["passed"] is None
           and abs(r7n["B146-7"][0]["reference_move"] - 0.2) < 0.01,
           "B146-7: a reference move above the grid and under the reference's own daily move is unread")
    # stop_over reads the same pairs as a walk over every pair of filings
    pz = Panel(rows + [("X", "A", "A7", "Other", 1.0, 5000.0, d) for d in
                       (D(2015, 1, 3), D(2015, 1, 20), D(2015, 2, 1), D(2015, 2, 2), D(2015, 3, 30))])

    def walk(key, a, b, floor):
        ds = pz.per[key]
        got = []
        for x, y in zip(ds, ds[1:] + [None]):
            hi = y if y is not None else pz.last_day + ONE
            if (hi - x).days >= floor and max(x + ONE, a) <= min(hi - ONE, b):
                got.append((x, y))
        return got
    same = all(stop_over(pz, k, a, b, fl) == walk(k, a, b, fl)
               for k in (("X", "A", "A7"), ("X", "A", "A9"), ("X", "B", "B0"), ("X", "A", "A0"))
               for a in days(D(2014, 12, 28), D(2015, 5, 3))[::3] for span in (0, 1, 9, 40)
               for b in [a + datetime.timedelta(span)] for fl in (1, 2, 8, 15))
    expect(same and stop_over(pz, ("X", "A", "A7"), D(2015, 1, 5), D(2015, 1, 6), 8)
           == [(D(2015, 1, 3), D(2015, 1, 20))],
           "stop_over finds the pairs a walk over every pair of filings finds")
    # object_absent against the same documents moved back, and the last filing before the closure
    try:
        CLOSURE_PLACEBO_MIN_UNITS = 1
        cp = closure_placebo(Panel(rows), ev, DEFAULT, (ev,))
        expect(cp["event"] == {"object_absent": 1, "units": 6, "share": 0.166667} and cp["windows"] == 2
               and cp["skipped_overlapping_a_closure_document"] == 2 and cp["share_max"] == 0.0
               and cp["windows_at_or_above_event_share"] == 0,
               "closure placebo: two shifted windows fit, two overlap the closure, none has a unit in the cell")
        quiet = [r for r in rows if not (r[2] == "B0" and D(2015, 2, 8) <= r[6] <= D(2015, 2, 27))]
        cq = closure_placebo(Panel(quiet), ev, DEFAULT, (ev,))
        expect(cq["windows_at_or_above_event_share"] == 1 and cq["share_max"] == 0.166667,
               "closure placebo: a silence with no document, of the event's size, is counted at the event's share")
        CLOSURE_PLACEBO_MIN_UNITS = 7
        expect(closure_placebo(Panel(rows), ev, DEFAULT, (ev,))["windows"] == 0,
               "closure placebo: a shifted window with fewer active markets than the floor is not counted")
    finally:
        CLOSURE_PLACEBO_MIN_UNITS = keep_cpu
    oa = base["object_absent_units"]["FX"]
    expect(oa["units"] == [["B / B0", "2015-02-28", "2015-03-21"]]
           and oa["last_filing_more_than_%d_days_before_the_closure" % EARLY_DAYS] == 0,
           "object_absent: the last filing before the closure and the next one are printed")
    early = [r for r in rows if not (r[2] == "B0" and D(2015, 2, 20) <= r[6] <= D(2015, 2, 28))]
    oe = run(early, dict(counts, kept=len(early)), events=(ev,))["object_absent_units"]["FX"]
    expect(oe["last_filing_more_than_%d_days_before_the_closure" % EARLY_DAYS] == 1
           and oe["last_filing_dates"] == {"2015-02-19": 1},
           "object_absent: a market silent since ten days before the closure is counted as early")
    edge = [r for r in rows if not (r[2] == "B0" and r[6] == D(2015, 2, 28))]
    og = run(edge, dict(counts, kept=len(edge)), events=(ev,))["object_absent_units"]["FX"]
    expect(og["last_filing_dates"] == {"2015-02-27": 1}
           and og["last_filing_more_than_%d_days_before_the_closure" % EARLY_DAYS] == 0,
           "object_absent: a last filing exactly at the early-days bound is not early")
    expect(quantile(list(range(1, 11)), 0.9) == 9 and quantile(list(range(1, 11)), 0.1) == 1
           and quantile([], 0.5) is None, "quantile: the ninth of ten, the first of ten, nothing of nothing")
    # the census record: a cluster under a closure document is marked, and unmarked without the event
    more = rows + [("X", "B", nm) + r[3:] for nm in ("B1", "B2") for r in rows if r[2] == "B0"]
    cw = census_with_documents(more, events=(ev,))["clusters_against_documents"]["state_stop8_prior10"]
    expect(cw["clusters"] == 1 and cw["put_against_a_document"] == 1 and cw["of_those_with_a_closure_document"] == 1,
           "census: the planted cluster is found and marked with the closure document it falls on")
    hit = census_with_documents(more, events=(ev,))["clusters"]["state_stop8_prior10"][0]["events_on_it"][0]
    expect(hit["members"] == 4 and hit["members_in_scope_by_district"] == {
               "transport": 4, "information": 4, "full_information_cut": 4, "closure": 3}
           and cw["of_those_a_closure_document_covers_a_member"] == 1
           and all(x[1:] == [0, 20] for x in hit["members_under_transport_document_filings_in_its_window"]),
           "census: the documents are counted by the districts they name: closure covers 3 of the 4 markets")
    far = dict(ev, transport=dict(ev["transport"], districts=("C",)), info=None,
               closures=(dict(ev["closures"][0], districts=("C",)),))
    cwf = census_with_documents(more, events=(far,))["clusters_against_documents"]["state_stop8_prior10"]
    expect(cwf["put_against_a_document"] == 1 and cwf["of_those_no_document_covers_a_member"] == 1
           and cwf["of_those_a_closure_document_covers_a_member"] == 0,
           "census: a cluster matched by state whose markets no document names is reported as such")
    half = dict(ev, info=None, closures=(dict(ev["closures"][0], districts=("C",)),))
    cwh = census_with_documents(more, events=(half,))["clusters_against_documents"]["state_stop8_prior10"]
    expect(cwh["of_those_no_document_covers_a_member"] == 0 and cwh["of_those_only_edge_documents_cover_a_member"] == 1,
           "census: a cluster whose markets only the transport document names is counted under edge documents")
    cw0 = census_with_documents(more, events=())["clusters_against_documents"]["state_stop8_prior10"]
    expect(cw0["clusters"] == 1 and cw0["put_against_a_document"] == 0 and cw0["largest_not_looked_up"]["markets"] == 4,
           "census: with no event table the same cluster is reported as not looked up")
    # second mutation round: seven places the fixtures above walked past
    dip = [r for r in hol2 if not (r[2] == "Y3" and (r[6].month, r[6].day) == (2, 5))]
    rdip = run(dip, dict(cnt, kept=len(dip), lines=len(dip)), events=(ev,))
    expect(rdip["closure_readback"]["ratio"] < min(
               float(v) for v in rdip["closure_readback"]["shifted_ratios"].values() if v is not None and v == v)
           and by_name(rdip)["B146-2"]["passed"] is False,
           "B146-2 fails when a shifted calendar has as many cells below as the true one, lower ratio or not")
    keep = (REF_MIN_OBS, PRE_DAYS)
    try:
        REF_MIN_OBS = 10
        jrows, jcounts, _ = fixture(ref_jump=0.2)
        against = [("Z", "Q", "Z%d" % i, "Dal", 10.0,
                    (9000.0 + 100 * i) * (math.exp(-0.4) if d >= D(2015, 3, 10) else 1.0), d)
                   for d in days(D(2015, 1, 1), D(2015, 4, 30)) for i in range(4)]
        ro = run(jrows + against, dict(jcounts, kept=len(jrows) + len(against)), events=(tonly,))
        uo = ro["B146-8"]["FX"]["by_reference"]["h_change_by_unit"]["A / A0"]
        expect(uo["all_clear_the_grid"] and not uo["same_sign"] and uo["state"] == "unread",
               "a change in h above the grid under every reference, of opposite signs, is unread")
        REF_MIN_OBS = 10 ** 6
        rn = run(jrows + against, dict(jcounts, kept=len(jrows) + len(against)), events=(tonly,))
        expect(set(rn["B146-8"]["FX"]["by_reference"]["references"]) == {"all varieties"},
               "a variety with fewer outside rows than the floor is not a reference of its own")
        thin = [("Y", "Q", "Y9", "Other", 10.0, 5000.0, d) for d in days(D(2015, 2, 25), D(2015, 4, 30))]
        ft = Panel(jrows + thin).fixed_composition("X", D(2015, 3, 1), D(2015, 3, 20))
        expect(ft["series"] == 4,
               "fixed-composition reference leaves out a series with too few filings in one segment")
    finally:
        REF_MIN_OBS, PRE_DAYS = keep
    prow = lambda move, steps: {"reference_move_all": move, "units": {
        "m": {"steps": steps, "arrivals_before": 1.0, "arrivals_inside": 1.0}}}
    ps = placebo_summary([prow(0.5, 3.0), prow(0.5, 1.0), prow(0.0, 0.0)], ["m"], 0.1,
                         {"m": {"arrivals": {"median_before": 1.0, "median_inside": 0.5}, "price_steps_inside": 0.0}})["m"]
    expect(ps["windows"] == 3 and ps["windows_reference_moved_a_grid_step"] == 2,
           "placebo summary: a window where the outside did not move a grid step is not counted as moved")
    expect(ps["of_those_price_within_one_step"] == 1 and ps["of_those_price_unmoved"] == 0,
           "placebo summary: a price three steps away is not within one step")
    cwu = census_with_documents(more, events=(dict(ev, checked=False),))["clusters_against_documents"]["state_stop8_prior10"]
    expect(cwu["clusters"] == 1 and cwu["put_against_a_document"] == 0,
           "census: an unchecked event marks no cluster")
    # states map to verdicts through the printed tables
    expect(MAPPING_B6 == {"grew": True, "did_not_grow": False, "unread": None}
           and all(by_name(x)["B146-6"]["passed"] is MAPPING_B6[by_name(x)["B146-6"]["state"]] for x in (base, r6, r6b)),
           "B146-6: each state maps to the verdict its table gives")
    print("self-test: %d failed" % len(fails))
    return 1 if fails else 0


# ----------------------------------------------------------------------------- census record
MATCH_LEAD = 7      # a cluster whose first last-filing falls this many days before an event's first date still belongs to it


def census_with_documents(rows, events=EVENTS):
    """The census tables, with each cluster marked by the checked events of its
    state whose documents it falls on, and a count of how many clusters were ever
    put against a document. A cluster with no mark was not looked up anywhere."""
    out = census.census_record(rows)
    filed = {k: set(v) for k, v in census.filing_days(rows).items()}
    summary = {}
    for name, cl in out["clusters"].items():
        for c in cl:
            st = c["where"].split(" / ")[0]
            first = D.fromisoformat(c["first_last_filing"])
            hits = []
            for ev in events:
                if not ev["checked"] or ev["state"] != st:
                    continue
                if event_start(ev) - datetime.timedelta(MATCH_LEAD) <= first <= event_end(ev):
                    kinds = sorted({k for k, x in (("transport", ev["transport"]), ("information", ev["info"])) if x}
                                   | ({"closure"} if ev["closures"] else set()))
                    # the match above is by state and dates; the documents name
                    # districts, so count the cluster's markets each one covers
                    ex = ev.get("excluded_markets", ())
                    mem = c["members"]
                    scope = {
                        "transport": sum(covers(ev["transport"], dis, m, ex) for dis, m, _ in mem),
                        "information": sum(covers(ev["info"], dis, m, ex) for dis, m, _ in mem),
                        "full_information_cut": sum(covers(ev["info"], dis, m, ex) for dis, m, _ in mem)
                        if ev["info"] and ev["info"]["kind"] in FULL_CUT_KINDS else 0,
                        "closure": sum(any(covers(x, dis, m, ex) for x in ev["closures"]) for dis, m, _ in mem)}
                    inside = []
                    if ev["transport"]:
                        win = days(ev["transport"]["start"], ev["transport"]["end"])
                        inside = [[dis + " / " + m, sum(d in filed.get((st, dis, m), ()) for d in win), len(win)]
                                  for dis, m, _ in mem if covers(ev["transport"], dis, m, ex)]
                    hits.append({"event": ev["id"], "documents": kinds, "members": len(mem),
                                 "members_in_scope_by_district": scope,
                                 "members_under_transport_document_filings_in_its_window": inside})
            c["events_on_it"] = hits
        marked = [c for c in cl if c["events_on_it"]]

        def reach(c, what):
            return any(h["members_in_scope_by_district"][what] for h in c["events_on_it"])
        summary[name] = {"clusters": len(cl), "put_against_a_document": len(marked),
                         "match": "state and dates; member counts per document are by district",
                         "ranks_put_against_a_document": [c["rank"] for c in marked],
                         "of_those_with_a_closure_document": sum(
                             any("closure" in h["documents"] for h in c["events_on_it"]) for c in marked),
                         "of_those_with_only_edge_documents": sum(
                             all("closure" not in h["documents"] for h in c["events_on_it"]) for c in marked),
                         "of_those_a_closure_document_covers_a_member": sum(reach(c, "closure") for c in marked),
                         "of_those_only_edge_documents_cover_a_member": sum(
                             not reach(c, "closure") and (reach(c, "transport") or reach(c, "information"))
                             for c in marked),
                         "of_those_no_document_covers_a_member": sum(
                             not any(reach(c, w) for w in ("closure", "transport", "information"))
                             for c in marked),
                         "of_those_a_full_information_cut_covers_a_member": sum(
                             reach(c, "full_information_cut") for c in marked),
                         "largest_not_looked_up": next(
                             ({"rank": c["rank"], "where": c["where"], "markets": c["markets"],
                               "first_last_filing": c["first_last_filing"]} for c in cl if not c["events_on_it"]),
                             None)}
    out["clusters_against_documents"] = summary
    return out


# ----------------------------------------------------------------------------- output
def to_text(rec):
    return json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def write_record(path, text):
    sys.path.insert(0, str(ROOT.parent))
    import safe_write
    if path.exists():
        if path.read_text(encoding="utf-8") == text:
            return "unchanged"
        safe_write.rewrite(str(path), "B146 record", lambda _old: text, session="T6_S30B6")
        return "rewritten"
    safe_write.create(str(path), "B146 record", text, session="T6_S30B6")
    return "created"


def print_record(commodity, rec):
    print("=" * 100)
    print(commodity)
    for x in rec["criteria"]:
        flag = {True: "PASS", False: "FAIL", None: "UNREAD"}[x["passed"]]
        print("  %-8s %-12s %-6s %s" % (x["name"], x["kind"], flag, x["detail"]))
    if "mapping" not in rec:
        return
    print("  cell -> rule -> feeds -> verdict")
    for k in CELLS:
        v = rec["mapping"][k]
        print("     %-22s %s | %s | %s" % (k, v["rule"], v["feeds"], v["verdict"]))
    print("  events (documents, runs of days with one set of restrictions in force)")
    for t in rec["events"]:
        print("     %-18s checked=%s grade=%s steps=%d units=%s"
              % (t["id"], t["checked"], t["grade"], t["execution_steps"],
                 rec["cells_by_event"].get(t["id"], {})))
        if t["checked"]:
            for r in t["dosage"]:
                print("        %s..%s %3d d  %s" % (r["from"], r["to"], r["days"], ", ".join(r["in_force"]) or "-"))
    print("  units not in the ordinary cell")
    for u in rec["units"]:
        if u["cell"] != "ordinary":
            print("     %-18s %-34s prior=%2d %-22s T=%d I=%d thin=%d closure=%d stopped=%d filed=%s"
                  % (u["event"], u["market"], u["prior"], u["cell"], u["T"], u["I"], u["I_thin"],
                     u["closure"], u["stopped"], u["filed_in_window"]))
    for eid, v in rec["B146-8"].items():
        print("  %s  window %s..%s  dispersion weekly median before %s, inside %s; grid %s"
              % (eid, v["window"][0], v["window"][1], v["dispersion_before"], v["dispersion_inside"], v["grid"]))
        print("     outside reference (median log price) before %s, inside %s, after %s"
              % (v["reference_before"], v["reference_inside"], v["reference_after"]))
        for m, x in v["units"].items():
            a = x["arrivals"]
            print("     %-30s price %s / %s / %s  h after %s" % (m, x["price_before"], x["price_inside"],
                                                                x["price_after"], x["h_after"]))
            print("     %-30s filings inside %3d  h before %s inside %s  arrivals %s -> %s  jump %s (+%s d) %s -> %s"
                  % (m, x["filings_inside"], x["h_before"], x["h_inside"], a["median_before"],
                     a["median_inside"], a["jump_between"], a["jump_days_after_start"], a["jump_left"],
                     a["jump_right"]))
        print("     reference, day-to-day move inside the window: %s" % v["reference_daily_move"])
        print("     nationwide events inside the window: %s" % v["nationwide_events_inside_window"])
        if v["arrivals_cross_section"]:
            for nm, t in v["arrivals_cross_section"].items():
                print("     arrivals ratio, %s, markets outside the state: %d, median %s, 10th percentile %s"
                      % (nm, t["markets"], t["median_ratio"], t["p10_ratio"]))
                for m, x in t["at_or_below_event_ratio"].items():
                    print("        at or below %-28s %.3f: %d (%s) %s"
                          % (m, x["event_ratio"], x["markets"], x["share"], x["by_state"]))
        for m, x in v["units"].items():
            a = x["arrivals"]
            print("     %-30s arrivals after the window %s (%d filings); the two filings at the jump %s"
                  % (m, a["median_after"], a["filings_after"], a["jump_day_values"]))
    print("  object_absent against the same documents moved back a week at a time")
    for eid, v in rec["object_absent_against_shifted_closures"].items():
        print("     %-18s event %s; windows %d (skipped %d overlapping, %d thin); median %s p90 %s max %s; "
              "at or above the event %s; expected in the cell at the median share %s"
              % (eid, v["event"], v["windows"], v["skipped_overlapping_a_closure_document"],
                 v["skipped_fewer_active_markets_than_floor"], v["share_median"], v["share_p90"],
                 v["share_max"], v["windows_at_or_above_event_share"], v["expected_in_cell_at_median_share"]))
    for eid, v in rec["object_absent_units"].items():
        print("     %-18s closure from %s; last filings %s; never filed again %d"
              % (eid, v["closure_first_day"], v["last_filing_dates"], v["never_filed_again"]))
    print("  reference, day-to-day move by event: %s" % rec["reference_daily_move_by_event"])
    print("  steps across stops that overlap an information order (printed, no state)")
    for r in rec["steps_across_stops_under_information_orders"]:
        print("     %-18s %-30s %-16s %s -> %s  %s -> %s  step %s  reference %s  exceeds its daily move: %s"
              % (r["event"], r["market"], r["cell"], r["last"], r["next"], r["price_last"],
                 r["price_next"], r["step"], r["reference_move"],
                 "median %s, 90th percentile %s" % (r["reference_move_exceeds_it"], r["reference_move_exceeds_p90"])))
    print("  knob sweep")
    for r in rec["knob_sweep"]:
        print("     prior>=%2d stop>=%2d cluster<=%d  units %3d  both-cut %d  cells %s  clusters %s  changed %d"
              % (r["prior_floor"], r["stop_floor"], r["cluster_window"], r["units"], r["both_cut_units"],
                 r["cells"], r["cluster_sizes"], len(r["changed_cell"])))
        for x in r["changed_cell"][:12]:
            print("          " + x)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--commodity", action="append")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    bad = 0
    for commodity in a.commodity or census.COMMODITIES:
        rows, counts = census.read_csv(commodity)
        rec = run(rows, counts)
        rec["stage"] = "B146"
        rec["commodity"] = commodity
        rec["config"] = {
            "knobs": DEFAULT, "prior_window_days": PRIOR_WINDOW, "edge_days": EDGE_DAYS,
            "pre_days": PRE_DAYS, "min_markets": MIN_MARKETS, "min_segment": MIN_SEGMENT,
            "reference_slack_days": REF_SLACK, "shifts": list(SHIFTS),
            "reference_min_obs": REF_MIN_OBS, "fixed_composition_min_filings": FIXED_MIN,
            "placebo": {"step_days": PLACEBO_STEP, "max_windows": PLACEBO_MAX, "min_length_days": PLACEBO_MIN_LEN},
            "h_read_min_window_days": READ_MIN_LEN, "h_read_min_definitions": 2,
            "h_segments": "whole Monday-to-Sunday weeks; the segment before the window starts on the Monday "
                          "of the week that holds the day pre_days before it",
            "closure_placebo": {"step_days": CLOSURE_PLACEBO_STEP, "min_units": CLOSURE_PLACEBO_MIN_UNITS},
            "early_last_filing_days": EARLY_DAYS, "cross_section_year_back_days": YEAR_BACK,
            "nationwide_events": [{"date": iso(n["date"]), "what": n["what"]} for n in NATIONWIDE],
            "sweep": {"prior_floor": list(PRIOR_FLOORS), "stop_floor": list(STOP_FLOORS),
                      "cluster_window": list(CLUSTER_WINDOWS)},
            "full_cut_kinds": list(FULL_CUT_KINDS), "wide_cut_kinds": list(WIDE_CUT_KINDS),
            "source": "data/agmark/%s/*.csv" % commodity, "events": [e["id"] for e in EVENTS],
            "reference": "median log modal price on the day over series outside the event's state; "
                         "B146-8 repeats it per variety and with the set of series held fixed",
            "price_per_market": "the variety with most filings in that market"}
        print_record(commodity, rec)
        cen = census_with_documents(rows)
        cen["stage"] = "B146"
        cen["commodity"] = commodity
        cen["config"] = {"gap_floors": list(census.GAP_FLOORS), "prior_floors": list(census.PRIOR_FLOORS),
                         "prior_window_days": census.PRIOR_WINDOW_DAYS,
                         "cluster_window_days": census.CLUSTER_WINDOW_DAYS,
                         "cluster_min_markets": census.CLUSTER_MIN_MARKETS,
                         "cluster_settings": [list(x) for x in census.CLUSTER_SETTINGS],
                         "match_lead_days": MATCH_LEAD, "source": "data/agmark/%s/*.csv" % commodity}
        print("  clusters of stops against documents")
        for name, v in cen["clusters_against_documents"].items():
            print("     %-26s clusters %3d  put against a document %d (ranks %s; by state: closure %d, edge only %d; "
                  "by district: closure covers a member %d, only edge documents cover one %d, none covers one %d, "
                  "a full information cut covers one %d)  largest not looked up: %s"
                  % (name, v["clusters"], v["put_against_a_document"], v["ranks_put_against_a_document"],
                     v["of_those_with_a_closure_document"], v["of_those_with_only_edge_documents"],
                     v["of_those_a_closure_document_covers_a_member"],
                     v["of_those_only_edge_documents_cover_a_member"], v["of_those_no_document_covers_a_member"],
                     v["of_those_a_full_information_cut_covers_a_member"], v["largest_not_looked_up"]))
            for c in cen["clusters"][name]:
                for h in c["events_on_it"]:
                    print("          rank %3d %-16s %2d markets  %-18s in scope by district %s  under the "
                          "transport document, filings in its window %s"
                          % (c["rank"], c["where"], h["members"], h["event"], h["members_in_scope_by_district"],
                             h["members_under_transport_document_filings_in_its_window"]))
        if not a.no_write:
            cpath = RESULTS / ("b146_stop_census_%s.json" % SHORT.get(commodity, "other"))
            print("  record %s: %s" % (cpath.name, write_record(cpath, to_text(cen))))
            path = RESULTS / ("b146_double_cut_%s.json" % SHORT.get(commodity, "other"))
            print("  record %s: %s" % (path.name, write_record(path, to_text(rec))))
        bad += sum(1 for x in rec["criteria"] if x["passed"] is False and x["kind"] in ("instrument", "bookkeeping", "known_answer"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
