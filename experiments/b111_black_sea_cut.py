"""B111: the 2026 Black Sea cuts on both sides, printed week by week against Theorem 43.

In July and August 2026 Ukraine lost its sea corridor and Russia lost first its Azov loadings
and then most of its Novorossiysk loadings. On each side three positions sit on one loop with
the world price W (Euronext milling wheat, September 2026 contract): the interior, the port
whose sea route was cut, and the route that stayed open (the western border for Ukraine, the
Baltic for Russia). The station prints the prices at those positions from hand-read weekly
quotes, aligns them to the dated steps of each cut, and puts one reading next to each object.
A position quoted by two sources is printed as two families, each with its own floor.

  a  the port against W. The path from the June mean is printed in full. Two readings: the
     relative move over one and two weeks from the Friday before each step week, and the
     relative move from the last June Friday to every later Friday (Corollary 43.1: a cut moves
     the pair away from its term, on the side where it already stood; Corollary 43.5 gives the
     opposite sign when a route partly reopens).
  b  the premium of the open route over the cut port, same week, same grade, same source, over
     one and two weeks from the Friday before each step week: a cut widens it, a partial
     reopening narrows it.
  c  Ukraine only: the port against W at the end of the weakening segment, against the weeks
     of the full cut (Corollary 43.5: the rewrite grows with the weakening).
  d  the interior's weekly change in the week of each dated step and the week after, next to
     the same weeks of 2025 (Theorem 43 (2): a cut lowers the interior).
  e  whether each position carries a quote each week: a clean quote, one its source calls
     nominal, one at or below the minimum export price, or none, and for none whether the
     source's issue for that week was read, read only as a rewrite, not found, or did not show
     that week. Printed next to the dated steps and the same weeks of 2025, without a reading:
     a position whose relations lose their weight has no price, and a relation that gains
     weight brings a comparison with it, and neither has a floor or a threshold to read against.

Each reading takes one of three states: matches, does not match, not read. A reading is not
read when an end cell is missing, when its source quotes it as nominal, approximate or as a
zone, when the Ukrainian port price is at or below that month's minimum allowable export
price, when no dated step lies inside the window, or when the move does not clear the floor.
The floor is the larger of the quote grid, counted only for quotes with a fixed format, and the
median absolute move of the same quantity over windows of the same length whose ends both lie
in June 2026, or both in the same weeks of 2025, in the same column, both ends readable. When
no such window exists the floor is not measured, and the reading is not read. No minimum export
price for 2025 is on disk, so a 2025 end is readable when it is present and not flagged.

Structural checks, each with a failure planted in the selftest:
  B111-1  every cell carries a source URL, a price date, a published date, a basis and a grade
  B111-2  one column holds one unit, one basis and one grade, and W one futures contract
  B111-3  every difference is taken within one week across columns, or within one column
          across weeks
  B111-4  every week in each source's window has a coverage row, weeks that read zero included,
          and a row that counts its cells counts the cells on disk from that page

Data: data/b111_black_sea_prices.json, transcribed by hand, one source URL per cell.

Run:
    python experiments/b111_black_sea_cut.py
    python experiments/b111_black_sea_cut.py --selftest
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "b111_black_sea_prices.json"
OUT = ROOT / "results" / "b111_black_sea_cut.json"

STUDY = ("2026-05-22", "2026-09-11")
JUNE = ("2026-06-05", "2026-06-12", "2026-06-19", "2026-06-26")
SAME_WEEKS_2025 = ("2025-05-30", "2025-09-12")
JUNE_2025 = ("2025-06-06", "2025-06-13", "2025-06-20", "2025-06-27")
#: the last Friday before either side's first dated step; the long windows of a start here
PRE_CUT = "2026-06-26"
WINDOWS = (1, 2)
W_COL = ("W.wheat.euronext", "2026-09")
W25_COL = ("REF2025.W.wheat.euronext", "2025-09")
W_CONTRACTS = ("2026-09", "2026-12", "2025-09", "2025-12")
#: fixed quote formats: Euronext ticks in quarters, the broker's CPT and FCA index in whole
#: dollars, the exchange's purchase price page in whole dollars and whole hryvnias, the weekly
#: domestic average in steps of 25 roubles. IKAR prints half dollars in some weeks and the
#: Ukrainian interior page prints steps of 50 and 250, so they carry none.
GRID = {"W.wheat.euronext": 0.25, "U1.wheat115.cpt_odesa": 1.0, "U1.corn.cpt_odesa": 1.0,
        "U2.corn.fca_chop": 1.0, "R0.wheat3.exw_european_russia.sovecon": 25.0,
        "U1.wheat2.cpt_terminal.graintrade": 1.0, "U1.corn.cpt_terminal.graintrade": 1.0,
        "U2.corn.daf.graintrade": 1.0, "U0.wheat2.exw_elevator.graintrade": 1.0}

COLUMNS = {
    "U1.corn.cpt_odesa": ("USD/t", "CPT Odesa", "corn"),
    "U1.wheat115.cpt_odesa": ("USD/t", "CPT Odesa", "wheat 11.5% protein"),
    "U1.wheatfeed.cpt_odesa": ("USD/t", "CPT Odesa", "feed wheat"),
    "U2.corn.fca_chop": ("USD/t", "FCA Chop", "corn"),
    "U2.corn_newcrop.fca_chop": ("EUR/t", "FCA Chop", "corn, new crop"),
    "U1.corn_newcrop.cpt_port": ("USD/t", "CPT port", "corn, new crop"),
    "U2.wheat.fca_chop": ("EUR/t", "FCA Chop", "wheat"),
    "W.wheat.euronext": ("EUR/t", "Euronext futures", "milling wheat"),
    "U0.wheat.exw": ("UAH/t", "EXW Ukraine", "wheat"),
    "U0.corn.exw": ("UAH/t", "EXW Ukraine", "corn"),
    "FLOOR.wheat.cpt": ("USD/t", "CPT", "wheat, minimum allowable export price"),
    "FLOOR.wheat.fob": ("USD/t", "FOB", "wheat, minimum allowable export price"),
    "FLOOR.corn.cpt": ("USD/t", "CPT", "corn, minimum allowable export price"),
    "FLOOR.corn.fob": ("USD/t", "FOB", "corn, minimum allowable export price"),
    "FLOOR.corn.dap": ("USD/t", "DAP", "corn, minimum allowable export price"),
    "U1.corn.dap_odesa": ("USD/t", "DAP Odesa", "corn"),
    "U2.corn.fca_border": ("EUR/t", "FCA border", "corn"),
    "U1.wheat115.dap_odesa": ("USD/t", "DAP Odesa", "wheat 11.5% protein"),
    "U1.wheatfeed.dap_odesa": ("USD/t", "DAP Odesa", "feed wheat"),
    "U2.wheat110.fca_border": ("EUR/t", "FCA border", "wheat 11% protein"),
    "U0.corn.exw_elevator.graintrade": ("UAH/t", "EXW elevators", "corn"),
    "U0.wheat2.exw_elevator.graintrade": ("UAH/t", "EXW elevators", "wheat grade II"),
    "U0.wheat3.exw_elevator.graintrade": ("UAH/t", "EXW elevators", "wheat grade III"),
    "U0.wheat4.exw_elevator.graintrade": ("UAH/t", "EXW elevators", "wheat grade IV"),
    "U1.corn.cpt_terminal_uah.graintrade": ("UAH/t", "CPT terminal", "corn"),
    "U1.wheat2.cpt_terminal_uah.graintrade": ("UAH/t", "CPT terminal", "wheat grade II"),
    "U1.wheat3.cpt_terminal_uah.graintrade": ("UAH/t", "CPT terminal", "wheat grade III"),
    "U1.wheat4.cpt_terminal_uah.graintrade": ("UAH/t", "CPT terminal", "wheat grade IV"),
    "U1.corn.cpt_terminal.graintrade": ("USD/t", "CPT terminal", "corn"),
    "U1.wheat2.cpt_terminal.graintrade": ("USD/t", "CPT terminal", "wheat grade II"),
    "U1.wheat3.cpt_terminal.graintrade": ("USD/t", "CPT terminal", "wheat grade III"),
    "U1.wheat4.cpt_terminal.graintrade": ("USD/t", "CPT terminal", "wheat grade IV"),
    "U2.corn.daf.graintrade": ("USD/t", "DAF", "corn"),
    "U2.wheat3.daf.graintrade": ("USD/t", "DAF", "wheat grade III"),
    "R1.wheat125.fob_novo.ikar": ("USD/t", "FOB Novorossiysk", "wheat 12.5% protein, new crop"),
    "R1.wheat125.fob_novo.ikar_oldcrop": ("USD/t", "FOB Novorossiysk", "wheat 12.5% protein, old crop"),
    "R1.wheat125.fob_deepwater.sovecon": ("USD/t", "FOB deep water", "wheat 12.5% protein"),
    "R1.wheat125.fob_deepwater.sovecon_oldcrop": ("USD/t", "FOB deep water", "wheat 12.5% protein"),
    "R2.wheat125.fob_baltic.ikar": ("USD/t", "FOB Baltic", "wheat 12.5% protein"),
    "R1.wheat125.fob_novo.rusagrotrans": ("USD/t", "FOB Novorossiysk", "wheat 12.5% protein"),
    "R2.wheat125.fob_baltic.rusagrotrans": ("USD/t", "FOB Baltic", "wheat 12.5% protein"),
    "R1.wheat4_125.cpt_deepwater_truck.rusagrotrans": ("RUB/t", "CPT deep-water port, by truck", "wheat class 4, 12.5% protein"),
    "R0.wheat3.exw_european_russia.sovecon": ("RUB/t", "EXW European Russia", "wheat class 3"),
    "R0.wheat4.exw_european_russia.sovecon": ("RUB/t", "EXW European Russia", "wheat class 4"),
    "R0.wheat4_125.exw_south.rusagrotrans": ("RUB/t", "EXW elevator, South", "wheat class 4, 12.5% protein"),
    "R0.wheat4_125.exw_central.rusagrotrans": ("RUB/t", "EXW elevator, Central Russia", "wheat class 4, 12.5% protein"),
    "R0.wheat4_125.exw_volga.rusagrotrans": ("RUB/t", "EXW elevator, Volga", "wheat class 4, 12.5% protein"),
    "DUTY.wheat.ru": ("RUB/t", "export duty", "wheat"),
    "FREIGHT.ru_sovecon": ("USD/t", "freight", "average"),
}
#: friday: a daily page, read on the Friday of each week
KINDS = ("weekly", "friday", "daily", "monthly", "implied", "stated_prev")
WEEKLY_KINDS = ("weekly", "friday", "implied", "stated_prev")
REQUIRED = ("series", "date", "unit", "source", "published", "basis", "grade", "kind")
DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?(/\d{4}-\d{2}(-\d{2})?)?$")

#: The dated steps read by a, b, c and d, taken from the step table in the data file by side and
#: date. dose "up" means the side lost capacity at that step, "down" that a route partly came back.
READ_STEPS = (("UA", "2026-07-22", "up"), ("UA", "2026-08-01/12", "down"),
              ("RU", "2026-07-10", "up"), ("RU", "2026-07-27/2026-07-31", "up"),
              ("RU", "2026-08-10/2026-08-14", "up"))
#: One family per source for each position. The second Ukrainian port family, and the interior
#: family of the same source, take the grade whose CPT dollar price sits closest to the broker's
#: 11.5% protein index over the four June 2026 Fridays: a mean gap of 1.75 dollars for grade II,
#: 8.25 for grade III, 10.5 for grade IV.
SIDES = {
    "UA": {
        "ports": (
            {"source": "broker weekly report", "port": "U1.wheat115.cpt_odesa", "twin": None, "commodity": "wheat",
             "twin_note": "the broker's 2025 weekly reports quote DAP Odesa ranges, another column; its CPT index starts 2025-09-02"},
            {"source": "exchange purchase price page", "port": "U1.wheat2.cpt_terminal.graintrade",
             "twin": "REF2025.U1.wheat2.cpt_terminal.graintrade", "commodity": "wheat", "twin_note": None}),
        "interiors": (
            {"source": "exchange purchase price page", "column": "U0.wheat2.exw_elevator.graintrade",
             "twin": "REF2025.U0.wheat2.exw_elevator.graintrade", "twin_note": None},
            {"source": "interior price page", "column": "U0.wheat.exw", "twin": None,
             "twin_note": "the interior price page shows no 2025 weeks and one June 2026 week"}),
        "open_pairs": (
            {"source": "broker weekly report", "open": "U2.corn.fca_chop", "cut": "U1.corn.cpt_odesa",
             "open_twin": None, "cut_twin": None, "commodity": "corn",
             "twin_note": "the FCA Chop dollar index starts 2026-07-17, so neither June 2026 nor 2025 has a window"},
            {"source": "exchange purchase price page", "open": "U2.corn.daf.graintrade", "cut": "U1.corn.cpt_terminal.graintrade",
             "open_twin": "REF2025.U2.corn.daf.graintrade", "cut_twin": "REF2025.U1.corn.cpt_terminal.graintrade",
             "commodity": "corn", "twin_note": None}),
    },
    "RU": {
        "ports": (
            {"source": "weekly grain report", "port": "R1.wheat125.fob_novo.ikar", "twin": "REF2025.R1.wheat125.fob_novo.ikar",
             "commodity": None, "twin_note": None},),
        "interiors": (
            {"source": "weekly grain report", "column": "R0.wheat3.exw_european_russia.sovecon",
             "twin": "REF2025.R0.wheat3.exw_european_russia.sovecon", "twin_note": None},),
        "open_pairs": (
            {"source": "Rusagrotrans via Interfax", "open": "R2.wheat125.fob_baltic.rusagrotrans",
             "cut": "R1.wheat125.fob_novo.rusagrotrans", "open_twin": None, "cut_twin": None, "commodity": None,
             "twin_note": "no Baltic quote before the cut or in 2025 in these sources"},
            {"source": "weekly grain report", "open": "R2.wheat125.fob_baltic.ikar", "cut": "R1.wheat125.fob_novo.ikar",
             "open_twin": None, "cut_twin": None, "commodity": None,
             "twin_note": "the Baltic line first appears 2026-08-21; no Baltic quote before the cut or in 2025 in these sources"}),
    },
}
#: Coverage families: the weeks each one must account for, weeks with nothing read included.
FAMILIES = (("UA", "broker weekly report 2026", "2026-05-29", "2026-09-11"),
            ("UA", "interior price page 2026", "2026-05-29", "2026-09-11"),
            ("UA", "broker weekly report 2025", "2025-06-06", "2025-08-29"),
            ("UA", "exchange purchase price page 2026", "2026-05-29", "2026-09-11"),
            ("UA", "exchange purchase price page 2025", "2025-05-30", "2025-09-12"),
            ("W", "futures history 2025", "2025-05-30", "2025-09-12"),
            ("RU", "weekly grain report 2026", "2026-05-22", "2026-09-11"),
            ("RU", "weekly grain report 2025", "2025-05-30", "2025-08-29"))

MATCH, MISS, NOT_READ = "matches", "does not match", "not read"
MAPPING = (("a, c, d: dose up", "move below minus the floor", MATCH),
           ("a, c, d: dose up", "move above the floor", MISS),
           ("a, c, d: dose down", "move above the floor", MATCH),
           ("a, c, d: dose down", "move below minus the floor", MISS),
           ("b: dose up", "move above the floor", MATCH),
           ("b: dose up", "move below minus the floor", MISS),
           ("b: dose down", "move below minus the floor", MATCH),
           ("b: dose down", "move above the floor", MISS),
           ("any", "move within the floor", NOT_READ),
           ("any", "floor not measured", NOT_READ),
           ("any", "an end cell missing, flagged, or at or below the minimum export price", NOT_READ),
           ("a, long windows", "no dated step inside the window", NOT_READ),
           ("d only", "the same week of 2025 not on disk", NOT_READ))


def day(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def fridays(a: str, b: str) -> list[str]:
    d, end = day(a), day(b)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    out = []
    while d <= end:
        out.append(d.isoformat())
        d += dt.timedelta(days=7)
    return out


def friday_on_or_before(s: str) -> str:
    d = day(s)
    return (d - dt.timedelta(days=(d.weekday() - 4) % 7)).isoformat()


def plus_weeks(s: str, k: int) -> str:
    return (day(s) + dt.timedelta(days=7 * k)).isoformat()


def weeks_between(a: str, b: str) -> int:
    return (day(b) - day(a)).days // 7


def same_week_2025(s: str) -> str:
    return dt.date.fromisocalendar(2025, day(s).isocalendar()[1], 5).isoformat()


def base_series(series: str) -> str:
    return series[len("REF2025."):] if series.startswith("REF2025.") else series


def column_key(c: dict) -> tuple:
    return (c["series"], c.get("contract") if base_series(c["series"]).startswith("W.") else None)


def col(series: str) -> tuple:
    return (series, None)


def val(c: dict) -> float:
    if "value" not in c:
        raise ValueError(f"range cell used as a point: {c['series']} {c['date']}")
    return float(c["value"])


def flags(c: dict | None) -> list[str]:
    if c is None:
        return ["missing"]
    return [k for k in ("nominal", "approx", "zone") if c.get(k)]


def f4(x):
    return None if x is None else float(f"{x:.4f}")


def public(x):
    """The record without the unrounded working values (keys that start with an underscore)."""
    if isinstance(x, dict):
        return {k: public(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, list):
        return [public(v) for v in x]
    return x


class Ledger:
    """Every difference the objects take goes through here, and is logged."""

    def __init__(self):
        self.pairs = []

    def across(self, a: dict, b: dict) -> float:
        self.pairs.append(("across", column_key(a), a["date"], column_key(b), b["date"]))
        if a["date"] != b["date"]:
            raise ValueError(f"across columns in different weeks: {a['date']} and {b['date']}")
        return val(a) - val(b)

    def over(self, a: dict, b: dict) -> float:
        self.pairs.append(("over", column_key(a), a["date"], column_key(b), b["date"]))
        if column_key(a) != column_key(b):
            raise ValueError(f"over weeks in different columns: {column_key(a)} and {column_key(b)}")
        return val(b) - val(a)


# ---------------------------------------------------------------- structural checks

def check_cells(cells: list[dict]) -> list[str]:
    bad = []
    for i, c in enumerate(cells):
        miss = [k for k in REQUIRED if c.get(k) in (None, "")]
        if miss:
            bad.append(f"cell {i} {c.get('series')} {c.get('date')}: missing {', '.join(miss)}")
            continue
        if not str(c["source"]).startswith("http"):
            bad.append(f"cell {i} {c['series']} {c['date']}: source is not a URL")
        if not DATE_RE.match(c["date"]) or not DATE_RE.match(str(c["published"])):
            bad.append(f"cell {i} {c['series']} {c['date']}: date or published date malformed")
        if "value" not in c and not ("low" in c and "high" in c):
            bad.append(f"cell {i} {c['series']} {c['date']}: no value")
        if c["kind"] not in KINDS:
            bad.append(f"cell {i} {c['series']} {c['date']}: kind {c['kind']}")
    return bad


def check_columns(cells: list[dict]) -> list[str]:
    bad = []
    for i, c in enumerate(cells):
        base = base_series(c.get("series", ""))
        decl = COLUMNS.get(base)
        if decl is None:
            bad.append(f"cell {i} {c.get('series')}: column not declared")
            continue
        got = (c.get("unit"), c.get("basis"), c.get("grade"))
        if got != decl:
            bad.append(f"cell {i} {c['series']} {c.get('date')}: holds {got}, column is {decl}")
        if base.startswith("W.") and c.get("contract") not in W_CONTRACTS:
            bad.append(f"cell {i} {c['series']} {c.get('date')}: contract {c.get('contract')}")
    return bad


def check_arithmetic(pairs: list[tuple]) -> list[str]:
    bad = []
    for p in pairs:
        if p[0] == "across" and p[2] != p[4]:
            bad.append(f"across {p[1][0]} {p[2]} and {p[3][0]} {p[4]}")
        if p[0] == "over" and p[1] != p[3]:
            bad.append(f"over {p[1]} and {p[3]}")
    return bad


def coverage_rows(data: dict) -> dict:
    """The weeks each family has a row for, read from the coverage the transcription recorded."""
    rows = {f: set() for f in FAMILIES}
    ua = data["sides"]["UA"]["coverage"]
    fam = {f[1]: f for f in FAMILIES}
    rows[fam["broker weekly report 2026"]] |= {friday_on_or_before(d) for d in ua["spike_weekly_2026"]["opened"]}
    rows[fam["interior price page 2026"]] |= {friday_on_or_before(d) for d in ua["ukragroconsult_exw"]["opened"]}
    rows[fam["interior price page 2026"]] |= set(ua["ukragroconsult_exw"].get("not_on_page", []))
    rows[fam["broker weekly report 2025"]] |= {friday_on_or_before(d) for d in ua["spike_weekly_2025"]["opened"]}
    rows[fam["futures history 2025"]] |= {friday_on_or_before(d) for d in ua["euronext_2025"]["opened"]}
    for r in ua["graintrade"]:
        rows[fam["exchange purchase price page " + r["price_date"][:4]]].add(friday_on_or_before(r["price_date"]))
    for r in data["sides"]["RU"]["coverage"]:
        rows[fam["weekly grain report " + r["price_date"][:4]]].add(friday_on_or_before(r["price_date"]))
    return rows


def check_page_counts(data: dict) -> tuple[list[str], int]:
    """A coverage row that counts its cells must count the cells on disk with that source and published date."""
    rows = list(data["sides"]["RU"]["coverage"]) + list(data["sides"]["UA"]["coverage"]["graintrade"])
    on_disk = {}
    for c in data["cells"]:
        k = (c.get("source"), c.get("published"))
        on_disk[k] = on_disk.get(k, 0) + 1
    bad = []
    for r in rows:
        n = on_disk.get((r["source"], r["published"]), 0)
        if n != r["cells_read"]:
            bad.append(f"{r['source']} {r['published']}: row counts {r['cells_read']}, disk holds {n}")
    return bad, len(rows)


def check_coverage(data: dict) -> tuple[list[str], dict, int]:
    rows = coverage_rows(data)
    bad, table = [], {}
    for f in FAMILIES:
        need = fridays(f[2], f[3])
        missing = [w for w in need if w not in rows[f]]
        table[f"{f[0]} {f[1]}"] = {"weeks": len(need), "rows": len([w for w in need if w in rows[f]])}
        bad += [f"{f[0]} {f[1]}: week {w} has no coverage row" for w in missing]
    count_bad, n_rows = check_page_counts(data)
    return bad + count_bad, table, n_rows


# ---------------------------------------------------------------- readings

def read_state(move, floor, dose, cut_sign=-1):
    """cut_sign is the sign a cut gives the move: -1 for the port against W and for the interior,
    +1 for the premium of the open route. A partial reopening expects the other sign."""
    if floor is None:
        return NOT_READ, "floor not measured"
    if abs(move) <= floor:
        return NOT_READ, "move within the floor"
    expected = cut_sign if dose == "up" else -cut_sign
    went = "down" if move < 0 else "up"
    return (MATCH if (move < 0) == (expected < 0) else MISS), f"moved {went} past the floor"


def weekly(cells, key, kinds=WEEKLY_KINDS):
    out = {}
    for c in cells:
        if column_key(c) == key and c["kind"] in kinds:
            out[c["date"]] = c
    return out


def by_friday(cells, key):
    out = {}
    for c in cells:
        if column_key(c) == key and c["kind"] in WEEKLY_KINDS:
            out[friday_on_or_before(c["date"])] = c
    return out


def unchanged_weeks(M, t):
    """How many Fridays in a row before t the column printed the same value as at t."""
    k = 0
    if M.get(t) is None:
        return None
    while M.get(plus_weeks(t, -k - 1)) is not None and val(M[plus_weeks(t, -k - 1)]) == val(M[t]):
        k += 1
    return k


def min_price(cells, commodity, date):
    if commodity is None:
        return None
    for c in cells:
        if c["series"] == f"FLOOR.{commodity}.cpt" and c["date"] == date[:7]:
            return c
    return None


def median_abs(xs):
    xs = [abs(x) for x in xs]
    return statistics.median(xs) if xs else None


def floor_of(grid, noise):
    if noise is None:
        return None
    return max(grid or 0.0, noise)


def floor_record(june_moves, moves_2025, grid, why_no_2025=None):
    moves = list(june_moves) + list(moves_2025)
    noise = median_abs(moves)
    fl = floor_of(grid, noise)
    return {"noise": f4(noise), "windows_june_2026": len(june_moves), "windows_2025": len(moves_2025),
            "zero_moves": sum(1 for m in moves if m == 0), "grid": f4(grid), "floor": f4(fl), "_floor": fl,
            "why_no_2025": why_no_2025 if not moves_2025 else None}


def steps_of(data, side):
    table = [s for s in data["steps"] if s["side"] == side]
    out = []
    for sd, date, dose in READ_STEPS:
        if sd != side:
            continue
        hits = [s for s in table if s["date"] == date]
        if not hits:
            raise ValueError(f"step {side} {date} is not in the step table")
        out.append({"side": side, "date": date, "start": date[:10], "dose": dose,
                    "events": [h["event"] for h in hits], "sources": [h["source"] for h in hits]})
    return out


def step_week(st):
    """The first Friday strictly after the step starts: the first weekly quote that can carry it."""
    return [f for f in fridays(*STUDY) if f > st["start"]][0]


def step_end(st):
    d = st["date"]
    if "/" not in d:
        return d
    tail = d.split("/")[1]
    return d[:8] + tail if len(tail) == 2 else tail


def rel_path(cells, port_key, w_key, base_weeks, commodity, weeks, led):
    """Port and W against their means over base_weeks, in percentage points, on every Friday in weeks."""
    P, W = weekly(cells, port_key), weekly(cells, w_key)

    def usable(d):
        p, w = P.get(d), W.get(d)
        if p is None or w is None or flags(p) or flags(w):
            return False
        mp = min_price(cells, commodity, d)
        return not (mp is not None and val(p) <= val(mp))

    base = [d for d in base_weeks if usable(d)]
    if not base:
        return {"rows": {}, "P": P, "W": W, "baseline": {"base_weeks": [], "port_mean": None, "W_mean": None,
                                                         "grid_pp": None, "_grid": 0.0, "grid_legs": []}}
    pbar = statistics.mean(val(P[d]) for d in base)
    wbar = statistics.mean(val(W[d]) for d in base)
    rows, run, prev = {}, 0, None
    for t in weeks:
        p, w = P.get(t), W.get(t)
        run = run + 1 if (p is not None and prev is not None and val(p) == val(prev)) else 0
        prev = p
        row = {"date": t, "port": None if p is None else val(p), "W": None if w is None else val(w),
               "port_flags": flags(p), "W_flags": flags(w), "port_unchanged_weeks": run}
        if p is not None and p.get("delivery"):
            row["delivery"] = p["delivery"]
        mp = None if p is None else min_price(cells, commodity, t)
        row["minimum_export_price"] = None if mp is None else val(mp)
        if p is not None and w is not None:
            led.across(p, w)
            row["_rel"] = 100 * (val(p) / pbar - val(w) / wbar)
            row["port_move_pct"] = f4(100 * (val(p) / pbar - 1))
            row["W_move_pct"] = f4(100 * (val(w) / wbar - 1))
            row["relative_pp"] = f4(row["_rel"])
        row["readable"] = usable(t)
        rows[t] = row
    legs = [k for k in (base_series(port_key[0]), W_COL[0]) if k in GRID]
    grid = 100 * (GRID.get(base_series(port_key[0]), 0.0) / pbar + GRID[W_COL[0]] / wbar)
    return {"rows": rows, "P": P, "W": W,
            "baseline": {"base_weeks": base, "port_mean": f4(pbar), "W_mean": f4(wbar), "grid_pp": f4(grid),
                         "_grid": grid, "grid_legs": legs}}


def path_move(path, t0, t1, led):
    rows = path["rows"]
    r0, r1 = rows.get(t0), rows.get(t1)
    if r0 is None or r1 is None or "_rel" not in r0 or "_rel" not in r1:
        return None, "an end cell missing"
    led.over(path["P"][t0], path["P"][t1])
    led.over(path["W"][t0], path["W"][t1])
    move = r1["_rel"] - r0["_rel"]
    if not (r0["readable"] and r1["readable"]):
        why = []
        for r in (r0, r1):
            if r["port_flags"] or r["W_flags"]:
                why.append(f"{r['date']} flagged {'+'.join(r['port_flags'] + r['W_flags'])}")
            elif r["minimum_export_price"] is not None and r["port"] <= r["minimum_export_price"]:
                why.append(f"{r['date']} at or below the minimum export price")
        return move, "; ".join(why) or "an end cell not readable"
    return move, None


def window_moves(path, L, weeks, led, move_of=None):
    move_of = move_of or path_move
    moves = []
    for s in weeks:
        e = plus_weeks(s, L)
        if e in weeks:
            mv, why = move_of(path, s, e, led)
            if mv is not None and why is None:
                moves.append(mv)
    return moves


def object_a(data, led):
    cells, out, inner = data["cells"], {}, {}
    same_2025 = fridays(*SAME_WEEKS_2025)
    for side in ("UA", "RU"):
        steps = steps_of(data, side)
        fams, inner[side] = [], []
        for spec in SIDES[side]["ports"]:
            path = rel_path(cells, col(spec["port"]), W_COL, JUNE, spec["commodity"], fridays(*STUDY), led)
            twin = None if spec["twin"] is None else rel_path(cells, col(spec["twin"]), W25_COL, JUNE_2025,
                                                              spec["commodity"], same_2025, led)
            floors = {}

            def floor(L, path=path, twin=twin, floors=floors, note=spec["twin_note"]):
                if L not in floors:
                    m25 = [] if twin is None else window_moves(twin, L, same_2025, led)
                    floors[L] = floor_record(window_moves(path, L, JUNE, led), m25, path["baseline"]["_grid"], note)
                return floors[L]

            readings = []
            for st in steps:
                t0 = plus_weeks(step_week(st), -1)
                for L in WINDOWS:
                    t1 = plus_weeks(t0, L)
                    move, why = path_move(path, t0, t1, led)
                    fl = floor(L)
                    if why is not None:
                        state, reason = NOT_READ, why
                    else:
                        state, reason = read_state(move, fl["_floor"], st["dose"])
                    readings.append({"step": st["date"], "dose": st["dose"], "from": t0, "to": t1, "weeks": L,
                                     "move_pp": f4(move), "floor_pp": fl["floor"], "state": state, "reason": reason})
            long_windows = []
            for t1 in [f for f in fridays(*STUDY) if f > PRE_CUT]:
                L = weeks_between(PRE_CUT, t1)
                inside = [s for s in steps if step_week(s) <= t1]
                move, why = path_move(path, PRE_CUT, t1, led)
                fl = floor(L)
                if not inside:
                    state, reason = NOT_READ, "no dated step inside the window"
                elif why is not None:
                    state, reason = NOT_READ, why
                else:
                    dose = "up" if any(s["dose"] == "up" for s in inside) else "down"
                    state, reason = read_state(move, fl["_floor"], dose)
                long_windows.append({"from": PRE_CUT, "to": t1, "weeks": L, "steps_inside": [s["date"] for s in inside],
                                     "move_pp": f4(move), "floor_pp": fl["floor"], "state": state, "reason": reason})
            fams.append({"source": spec["source"], "port": spec["port"], "twin": spec["twin"], "commodity": spec["commodity"],
                         "baseline": path["baseline"], "baseline_2025": None if twin is None else twin["baseline"],
                         "floors": floors, "path": [path["rows"][t] for t in sorted(path["rows"])],
                         "path_2025": None if twin is None else [twin["rows"][t] for t in sorted(twin["rows"])],
                         "readings": readings, "long_windows": long_windows})
            inner[side].append({"path": path, "floor": floor})
        out[side] = fams
    return out, inner


def premium_path(cells, open_key, cut_key, commodity, led):
    O, C = weekly(cells, open_key), weekly(cells, cut_key)
    rows, prev = {}, None
    for d in sorted(set(O) & set(C)):
        o, c = O[d], C[d]
        prem = led.across(o, c)
        mp = min_price(cells, commodity, d)
        why = flags(o) + flags(c)
        if mp is not None and val(c) <= val(mp):
            why.append("cut port at or below the minimum export price")
        row = {"date": d, "open": val(o), "cut": val(c), "premium": f4(prem), "_prem": prem,
               "flags": why, "minimum_export_price": None if mp is None else val(mp),
               "open_unchanged_weeks": 0, "cut_unchanged_weeks": 0}
        if prev is not None:
            row["open_unchanged_weeks"] = prev["open_unchanged_weeks"] + 1 if prev["open"] == row["open"] else 0
            row["cut_unchanged_weeks"] = prev["cut_unchanged_weeks"] + 1 if prev["cut"] == row["cut"] else 0
        rows[d] = prev = row
    return {"rows": rows, "O": O, "C": C}


def premium_move(path, t0, t1, led):
    r0, r1 = path["rows"].get(t0), path["rows"].get(t1)
    if r0 is None or r1 is None:
        return None, "an end cell missing"
    led.over(path["O"][t0], path["O"][t1])
    led.over(path["C"][t0], path["C"][t1])
    move = r1["_prem"] - r0["_prem"]
    why = [f"{r['date']} {'; '.join(r['flags'])}" for r in (r0, r1) if r["flags"]]
    return move, (("flagged: " + "; ".join(why)) if why else None)


def object_b(data, led):
    cells, out = data["cells"], {}
    same_2025 = fridays(*SAME_WEEKS_2025)
    for side in ("UA", "RU"):
        steps = steps_of(data, side)
        fams = []
        for spec in SIDES[side]["open_pairs"]:
            path = premium_path(cells, col(spec["open"]), col(spec["cut"]), spec["commodity"], led)
            twin = None if spec["open_twin"] is None else premium_path(cells, col(spec["open_twin"]), col(spec["cut_twin"]),
                                                                       spec["commodity"], led)
            grid = GRID.get(spec["open"], 0.0) + GRID.get(spec["cut"], 0.0)
            floors = {}
            for L in WINDOWS:
                m25 = [] if twin is None else window_moves(twin, L, same_2025, led, premium_move)
                floors[L] = floor_record(window_moves(path, L, JUNE, led, premium_move), m25, grid, spec["twin_note"])
            readings = []
            for st in steps:
                t0 = plus_weeks(step_week(st), -1)
                for L in WINDOWS:
                    t1 = plus_weeks(t0, L)
                    move, why = premium_move(path, t0, t1, led)
                    if why is not None:
                        state, reason = NOT_READ, why
                    else:
                        state, reason = read_state(move, floors[L]["_floor"], st["dose"], cut_sign=+1)
                    readings.append({"step": st["date"], "dose": st["dose"], "from": t0, "to": t1, "weeks": L,
                                     "change": f4(move), "floor": floors[L]["floor"], "state": state, "reason": reason})
            dates = sorted(path["rows"])
            changes = []
            for a, b in zip(dates, dates[1:]):
                led.over(path["O"][a], path["O"][b])
                led.over(path["C"][a], path["C"][b])
                changes.append({"from": a, "to": b, "change": f4(path["rows"][b]["_prem"] - path["rows"][a]["_prem"]),
                                "steps_inside": [s["date"] for s in steps if s["start"] <= b and step_end(s) > a]})
            fams.append({"source": spec["source"], "open": spec["open"], "cut": spec["cut"], "commodity": spec["commodity"],
                         "floors": floors, "path": [path["rows"][d] for d in dates],
                         "path_2025": None if twin is None else [twin["rows"][d] for d in sorted(twin["rows"])],
                         "readings": readings, "adjacent_changes": changes})
        out[side] = fams
    return out


def object_c(data, a_inner, led):
    ua = steps_of(data, "UA")
    up = [s for s in ua if s["dose"] == "up"][0]
    back = [s for s in ua if s["dose"] == "down"][0]["start"]
    end_weak = plus_weeks(step_week(up), -1)
    cut_weeks = [f for f in fridays(*STUDY) if up["start"] <= f < back]
    fams = []
    for spec, inner in zip(SIDES["UA"]["ports"], a_inner["UA"]):
        readings = []
        for t in cut_weeks:
            L = weeks_between(end_weak, t)
            move, why = path_move(inner["path"], end_weak, t, led)
            fl = inner["floor"](L)
            if why is not None:
                state, reason = NOT_READ, why
            else:
                state, reason = read_state(move, fl["_floor"], "up")
            readings.append({"weakening_segment_end": end_weak, "cut_week": t, "weeks": L, "move_pp": f4(move),
                             "floor_pp": fl["floor"], "state": state, "reason": reason})
        fams.append({"source": spec["source"], "port": spec["port"], "readings": readings})
    return {"weakening_segment_end": end_weak, "cut_segment_weeks": cut_weeks, "families": fams}


def object_d(data, led):
    cells, out = data["cells"], {}
    W = weekly(cells, W_COL)
    same_2025 = fridays(*SAME_WEEKS_2025)
    for side in ("UA", "RU"):
        steps = steps_of(data, side)
        fams = []
        for spec in SIDES[side]["interiors"]:
            X = by_friday(cells, col(spec["column"]))
            R = {} if spec["twin"] is None else by_friday(cells, col(spec["twin"]))

            def change(M, t):
                a, b = M.get(plus_weeks(t, -1)), M.get(t)
                if a is None or b is None:
                    return None, "an end cell missing"
                mv = led.over(a, b)
                fl = flags(a) + flags(b)
                return mv, (("flagged: " + "+".join(fl)) if fl else None)

            june = [m for m, why in (change(X, t) for t in JUNE if plus_weeks(t, -1) in JUNE) if m is not None and why is None]
            m25 = [m for m, why in (change(R, t) for t in same_2025 if plus_weeks(t, -1) >= SAME_WEEKS_2025[0])
                   if m is not None and why is None]
            grid = GRID.get(spec["column"])
            fl = floor_record(june, m25, grid, spec["twin_note"])
            readings = []
            for st in steps:
                t1 = step_week(st)
                for t in (t1, plus_weeks(t1, 1)):
                    mv, why = change(X, t)
                    t25 = same_week_2025(t)
                    mv25, _ = change(R, t25)
                    wmv, _ = change(W, t)
                    if why is not None:
                        state, reason = NOT_READ, why
                    elif mv25 is None:
                        state, reason = NOT_READ, "the same week of 2025 not on disk"
                    else:
                        state, reason = read_state(mv, fl["_floor"], st["dose"])
                    readings.append({"step": st["date"], "dose": st["dose"], "week": t, "change": f4(mv),
                                     "unchanged_weeks": unchanged_weeks(X, t),
                                     "same_week_2025": t25, "change_2025": f4(mv25), "W_change": f4(wmv),
                                     "floor": fl["floor"], "state": state, "reason": reason})
            fams.append({"source": spec["source"], "column": spec["column"], "twin": spec["twin"],
                         "unit": COLUMNS[spec["column"]][0], "floor": fl, "readings": readings})
        out[side] = fams
    return out


# ---------------------------------------------------------------- e: whether each position carries a quote each week

#: Three kinds of week. Priced: the source gives the position a price, loosely for approx and zone.
#: Unpriced: the source was read and gives no price a trade can clear at, because it says nominal, the
#: quote sits at or below the minimum export price below which exports are prohibited, or it carries
#: no line. Unread: nothing can be said about the market that week, because only a rewrite without the
#: line was read, no issue was found, the page did not show the week, no issue was opened, or the
#: futures column rolled to another contract.
PRICED = ("quoted", "quoted as a range", "implied from the next issue", "approx", "zone")
UNPRICED = ("nominal", "at or below the minimum export price", "not quoted")
UNREAD = ("not in the rewrite read", "no issue found", "not on the page", "issue not read", "rolled to another contract")
PRESENCE_CODES = {"quoted": "Q", "quoted as a range": "R", "implied from the next issue": "I", "nominal": "N",
                  "approx": "A", "zone": "Z", "at or below the minimum export price": "F", "not quoted": "-",
                  "not in the rewrite read": "W", "no issue found": "0", "not on the page": "P",
                  "issue not read": ".", "rolled to another contract": "C"}
#: One row per position and source. issues names whose issues are read for the weeks with no cell;
#: commodity names the minimum export price that applies to a Ukrainian port column.
PRESENCE = (
    {"side": "UA", "role": "port", "source": "broker weekly report", "column": "U1.wheat115.cpt_odesa",
     "contract": None, "issues": "broker weekly", "twin": None, "commodity": "wheat"},
    {"side": "UA", "role": "port", "source": "broker weekly report", "column": "U1.corn.cpt_odesa",
     "contract": None, "issues": "broker weekly", "twin": None, "commodity": "corn"},
    {"side": "UA", "role": "open route", "source": "broker weekly report", "column": "U2.corn.fca_chop",
     "contract": None, "issues": "broker weekly", "twin": None, "commodity": None},
    {"side": "UA", "role": "port", "source": "exchange purchase price page", "column": "U1.wheat2.cpt_terminal.graintrade",
     "contract": None, "issues": "exchange page", "twin": "REF2025.U1.wheat2.cpt_terminal.graintrade", "commodity": "wheat"},
    {"side": "UA", "role": "port", "source": "exchange purchase price page", "column": "U1.corn.cpt_terminal.graintrade",
     "contract": None, "issues": "exchange page", "twin": "REF2025.U1.corn.cpt_terminal.graintrade", "commodity": "corn"},
    {"side": "UA", "role": "open route", "source": "exchange purchase price page", "column": "U2.corn.daf.graintrade",
     "contract": None, "issues": "exchange page", "twin": "REF2025.U2.corn.daf.graintrade", "commodity": None},
    {"side": "UA", "role": "interior", "source": "exchange purchase price page", "column": "U0.wheat2.exw_elevator.graintrade",
     "contract": None, "issues": "exchange page", "twin": "REF2025.U0.wheat2.exw_elevator.graintrade", "commodity": None},
    {"side": "UA", "role": "interior", "source": "interior price page", "column": "U0.wheat.exw",
     "contract": None, "issues": "interior page", "twin": None, "commodity": None},
    {"side": "RU", "role": "port", "source": "weekly grain report", "column": "R1.wheat125.fob_novo.ikar",
     "contract": None, "issues": "weekly report", "twin": "REF2025.R1.wheat125.fob_novo.ikar", "commodity": None},
    {"side": "RU", "role": "open route", "source": "weekly grain report", "column": "R2.wheat125.fob_baltic.ikar",
     "contract": None, "issues": "weekly report", "twin": None, "commodity": None},
    {"side": "RU", "role": "interior", "source": "weekly grain report", "column": "R0.wheat3.exw_european_russia.sovecon",
     "contract": None, "issues": "weekly report", "twin": "REF2025.R0.wheat3.exw_european_russia.sovecon", "commodity": None},
    {"side": "RU", "role": "port", "source": "Rusagrotrans via Interfax", "column": "R1.wheat125.fob_novo.rusagrotrans",
     "contract": None, "issues": "Rusagrotrans note", "twin": None, "commodity": None},
    {"side": "RU", "role": "open route", "source": "Rusagrotrans via Interfax", "column": "R2.wheat125.fob_baltic.rusagrotrans",
     "contract": None, "issues": "Rusagrotrans note", "twin": None, "commodity": None},
    {"side": "W", "role": "world", "source": "broker weekly report", "column": "W.wheat.euronext",
     "contract": "2026-09", "issues": "broker weekly", "twin": "REF2025.W.wheat.euronext", "twin_contract": "2025-09",
     "twin_issues": "futures history", "commodity": None},
)
#: The weeks each issue family accounts for, taken from the coverage families of B111-4.
PRESENCE_WINDOWS = {("broker weekly", "2026"): "broker weekly report 2026",
                    ("exchange page", "2026"): "exchange purchase price page 2026",
                    ("exchange page", "2025"): "exchange purchase price page 2025",
                    ("interior page", "2026"): "interior price page 2026",
                    ("weekly report", "2026"): "weekly grain report 2026",
                    ("weekly report", "2025"): "weekly grain report 2025",
                    ("Rusagrotrans note", "2026"): "weekly grain report 2026",
                    ("futures history", "2025"): "futures history 2025"}


def presence_weeks(issue_name, year):
    label = PRESENCE_WINDOWS[(issue_name, year)]
    f = [x for x in FAMILIES if x[1] == label][0]
    return fridays(f[2], f[3])


def issues_read(data, name, year):
    """For each Friday, how the source's issue for that week was read: read, rewrite, none, not on the page."""
    ua, ru = data["sides"]["UA"]["coverage"], data["sides"]["RU"]["coverage"]
    out = {}
    if name == "broker weekly":
        for d in ua.get("spike_weekly_" + year, {}).get("opened", []):
            out[friday_on_or_before(d)] = "read"
    elif name == "exchange page":
        for r in ua["graintrade"]:
            if r["price_date"].startswith(year):
                out[friday_on_or_before(r["price_date"])] = "read"
    elif name == "interior page":
        page = ua["ukragroconsult_exw"]
        for d in page["opened"]:
            if d.startswith(year):
                out[friday_on_or_before(d)] = "read"
        for w in page.get("not_on_page", []):
            if w.startswith(year):
                out[w] = "not on the page"
    elif name == "futures history":
        for d in ua.get("euronext_" + year, {}).get("opened", []):
            out[friday_on_or_before(d)] = "read"
    elif name in ("weekly report", "Rusagrotrans note"):
        for r in ru:
            if not r["price_date"].startswith(year) or (name == "Rusagrotrans note") != ("interfax" in r["source"]):
                continue
            how = {"browser": "read", "fetch": "rewrite", "none": "none"}[r["via"]]
            w = friday_on_or_before(r["price_date"])
            if out.get(w) != "read":
                out[w] = how
    else:
        raise ValueError(f"unknown issue family {name}")
    return out


def presence_path(data, column, contract, issue_name, year, commodity):
    cells = data["cells"]
    mine, others = {}, set()
    for c in cells:
        if c["series"] != column or c["kind"] not in WEEKLY_KINDS:
            continue
        w = friday_on_or_before(c["date"])
        if column_key(c) == (column, contract):
            mine[w] = c
        else:
            others.add(w)
    read = issues_read(data, issue_name, year)
    rows = []
    for w in presence_weeks(issue_name, year):
        c = mine.get(w)
        if c is not None:
            fl = flags(c)
            mp = min_price(cells, commodity, c["date"]) if "value" in c else None
            if fl:
                state = fl[0]
            elif mp is not None and val(c) <= val(mp):
                state = "at or below the minimum export price"
            elif c["kind"] in ("implied", "stated_prev"):
                state = "implied from the next issue"
            elif "value" not in c:
                state = "quoted as a range"
            else:
                state = "quoted"
        elif w in others:
            state = "rolled to another contract"
        else:
            state = {"read": "not quoted", "rewrite": "not in the rewrite read", "none": "no issue found",
                     "not on the page": "not on the page", None: "issue not read"}[read.get(w)]
        rows.append({"week": w, "state": state, "code": PRESENCE_CODES[state],
                     "cell_date": None if c is None else c["date"], "source": None if c is None else c["source"]})
    return rows


def presence_kind(state):
    for name, group in (("priced", PRICED), ("unpriced", UNPRICED), ("unread", UNREAD)):
        if state in group:
            return name
    raise ValueError(f"state {state} is in no kind")


def presence_summary(rows, step):
    before = [r for r in rows if step is not None and r["week"] < step]
    after = [r for r in rows if step is None or r["week"] >= step]

    def kinds(rs):
        t = {"priced": 0, "unpriced": 0, "unread": 0}
        for r in rs:
            t[presence_kind(r["state"])] += 1
        return t

    def tally(rs):
        t = {}
        for r in rs:
            t[r["state"]] = t.get(r["state"], 0) + 1
        return dict(sorted(t.items()))

    return {"step_week": step, "weeks_before": len(before), "weeks_from_step_week": len(after),
            "before": kinds(before), "from_step_week": kinds(after),
            "states_before": tally(before), "states_from_step_week": tally(after),
            "first_priced_week": next((r["week"] for r in rows if presence_kind(r["state"]) == "priced"), None),
            "first_unpriced_week_from_step_week": next((r["week"] for r in after if presence_kind(r["state"]) == "unpriced"), None)}


def object_e(data):
    first_up = {side: min(step_week(s) for s in steps_of(data, side) if s["dose"] == "up") for side in ("UA", "RU")}
    fams = []
    for spec in PRESENCE:
        step = first_up.get(spec["side"])
        rows = presence_path(data, spec["column"], spec["contract"], spec["issues"], "2026", spec["commodity"])
        fam = {"side": spec["side"], "role": spec["role"], "source": spec["source"], "column": spec["column"],
               "contract": spec["contract"], "path": rows, "summary": presence_summary(rows, step), "path_2025": None}
        if spec["twin"] is not None:
            twin_rows = presence_path(data, spec["twin"], spec.get("twin_contract"), spec.get("twin_issues", spec["issues"]),
                                      "2025", spec["commodity"])
            fam["path_2025"] = twin_rows
            fam["summary_2025"] = presence_summary(twin_rows, None)
        fams.append(fam)
    return {"codes": PRESENCE_CODES, "kinds": {"priced": list(PRICED), "unpriced": list(UNPRICED), "unread": list(UNREAD)},
            "first_cut_step_week": first_up, "families": fams}


def context(data):
    cells = data["cells"]
    duty = sorted(({"period": c["date"], "rub_per_t": c["value"], "source": c["source"]}
                   for c in cells if c["series"] == "DUTY.wheat.ru"), key=lambda r: r["period"])
    floors = sorted(({"month": c["date"], "term": c["series"][6:], "usd_per_t": c["value"]}
                     for c in cells if c["series"].startswith("FLOOR.")), key=lambda r: (r["month"], r["term"]))
    return {"export_duty_ru": duty, "minimum_export_price_ua": floors, "steps": data["steps"]}


def run(data):
    led = Ledger()
    a, inner = object_a(data, led)
    objects = {"a": a, "b": object_b(data, led), "c": object_c(data, inner, led), "d": object_d(data, led),
               "e": object_e(data)}
    return public(objects), led


def counts(objects):
    def tally(rs):
        t = {MATCH: 0, MISS: 0, NOT_READ: 0}
        for r in rs:
            t[r["state"]] += 1
        return t

    out = {"a": {}, "a_long_windows": {}, "b": {}, "c": {}, "d": {}}
    for side in ("UA", "RU"):
        for fam in objects["a"][side]:
            out["a"][f"{side} {fam['source']}"] = tally(fam["readings"])
            out["a_long_windows"][f"{side} {fam['source']}"] = tally(fam["long_windows"])
        for fam in objects["b"][side]:
            out["b"][f"{side} {fam['source']}"] = tally(fam["readings"])
        for fam in objects["d"][side]:
            out["d"][f"{side} {fam['source']}"] = tally(fam["readings"])
    for fam in objects["c"]["families"]:
        out["c"][f"UA {fam['source']}"] = tally(fam["readings"])
    return out


def criteria_for(data, led):
    b1, b2, b3 = check_cells(data["cells"]), check_columns(data["cells"]), check_arithmetic(led.pairs)
    b4, table, n_rows = check_coverage(data)
    return [
        {"name": "B111-1", "kind": "bookkeeping", "passed": not b1,
         "statement": "every cell carries a source URL, a price date, a published date, a basis and a grade",
         "detail": f"{len(data['cells'])} cells, {len(b1)} incomplete" + (": " + "; ".join(b1[:5]) if b1 else "")},
        {"name": "B111-2", "kind": "instrument", "passed": not b2,
         "statement": "one column holds one unit, one basis and one grade, and W one futures contract per column",
         "detail": f"{len(COLUMNS)} declared columns, {len(b2)} cells off their column" + (": " + "; ".join(b2[:5]) if b2 else "")},
        {"name": "B111-3", "kind": "instrument", "passed": not b3,
         "statement": "every difference is taken within one week across columns, or within one column across weeks",
         "detail": f"{len(led.pairs)} differences logged, {len(b3)} off" + (": " + "; ".join(b3[:5]) if b3 else "")},
        {"name": "B111-4", "kind": "bookkeeping", "passed": not b4,
         "statement": "every week in each source's window has a coverage row, weeks that read zero included, "
                      "and a row that counts its cells counts the cells on disk from that page",
         "detail": "; ".join(f"{k}: {v['rows']} of {v['weeks']} weeks" for k, v in table.items())
                   + f"; {n_rows} page rows counted against the cells on disk"
                   + (": " + "; ".join(b4[:5]) if b4 else "")},
    ]


# ---------------------------------------------------------------- selftest

def fixture() -> dict:
    """A small file of the same shape: two sides, June and the cut weeks of 2026, the same weeks of 2025."""
    cells = []

    def add(series, date, unit, basis, grade, value, kind="weekly", page=None, **kw):
        src = "https://example.org/" + (page if page else series) + "/" + date
        c = {"series": series, "date": date, "unit": unit, "basis": basis, "grade": grade, "value": value,
             "kind": kind, "source": src, "published": date}
        c.update(kw)
        cells.append(c)

    weeks = ("2026-06-05", "2026-06-12", "2026-06-19", "2026-06-26", "2026-07-03", "2026-07-10",
             "2026-07-17", "2026-07-24", "2026-07-31", "2026-08-07", "2026-08-14", "2026-08-21")
    port = (220, 218, 217, 213, 207, 208, 204, 196, 195, 195, 195, 195)
    wv = (203, 200.75, 201.25, 202.75, 201.5, 216.25, 234, 232.75, 222.75, 223, 228, 223.5)
    prem = (0, 1, 1, 1, 2, 2, 3, 10, 16, 12, 15, 10)
    for i, (d, p, w) in enumerate(zip(weeks, port, wv)):
        add("U1.wheat115.cpt_odesa", d, "USD/t", "CPT Odesa", "wheat 11.5% protein", p, nominal=False)
        add("W.wheat.euronext", d, "EUR/t", "Euronext futures", "milling wheat", w, contract="2026-09", zone=False)
        add("U1.corn.cpt_odesa", d, "USD/t", "CPT Odesa", "corn", p - 5, nominal=False)
        add("R1.wheat125.fob_novo.ikar", d, "USD/t", "FOB Novorossiysk", "wheat 12.5% protein, new crop", p + 15,
            page="RU", nominal=False)
        add("R0.wheat3.exw_european_russia.sovecon", d, "RUB/t", "EXW European Russia", "wheat class 3", 14000 - 100 * i, page="RU")
        add("U0.wheat.exw", d, "UAH/t", "EXW Ukraine", "wheat", 7000)
        add("U1.wheat2.cpt_terminal.graintrade", d, "USD/t", "CPT terminal", "wheat grade II", p - 2, kind="friday", page="GT")
        add("U1.corn.cpt_terminal.graintrade", d, "USD/t", "CPT terminal", "corn", p - 7, kind="friday", page="GT")
        add("U2.corn.daf.graintrade", d, "USD/t", "DAF", "corn", p - 7 + prem[i], kind="friday", page="GT")
        add("U0.wheat2.exw_elevator.graintrade", d, "UAH/t", "EXW elevators", "wheat grade II", 9000 - 50 * i,
            kind="friday", page="GT")
    for d in weeks[6:]:
        add("U2.corn.fca_chop", d, "USD/t", "FCA Chop", "corn", 230, nominal=False)
        add("R1.wheat125.fob_novo.rusagrotrans", d, "USD/t", "FOB Novorossiysk", "wheat 12.5% protein", 215, page="RU")
        add("R2.wheat125.fob_baltic.rusagrotrans", d, "USD/t", "FOB Baltic", "wheat 12.5% protein", 240, page="RU")
        add("R2.wheat125.fob_baltic.ikar", d, "USD/t", "FOB Baltic", "wheat 12.5% protein", 250, page="RU")
    wiggle = (0, 1, -1, 2, 0, -2, 1, 0, -1, 1, 2, 0, -1, 0, 1, 0)
    for i, d in enumerate(fridays("2025-05-30", "2025-09-12")):
        if d < "2025-09-12":
            add("REF2025.W.wheat.euronext", d, "EUR/t", "Euronext futures", "milling wheat", 200 + wiggle[i], contract="2025-09", zone=False)
        else:
            add("REF2025.W.wheat.euronext", d, "EUR/t", "Euronext futures", "milling wheat", 190, contract="2025-12", zone=False)
        add("REF2025.U1.wheat2.cpt_terminal.graintrade", d, "USD/t", "CPT terminal", "wheat grade II", 220 + wiggle[i],
            kind="friday", page="GT")
        add("REF2025.U1.corn.cpt_terminal.graintrade", d, "USD/t", "CPT terminal", "corn", 210, kind="friday", page="GT")
        add("REF2025.U2.corn.daf.graintrade", d, "USD/t", "DAF", "corn", 210 + i % 2, kind="friday", page="GT")
        add("REF2025.U0.wheat2.exw_elevator.graintrade", d, "UAH/t", "EXW elevators", "wheat grade II", 9500 + 20 * (i % 2),
            kind="friday", page="GT")
        if d <= "2025-08-29":
            add("REF2025.R1.wheat125.fob_novo.ikar", d, "USD/t", "FOB Novorossiysk", "wheat 12.5% protein, new crop",
                230 + wiggle[i], page="RU", nominal=False)
            add("REF2025.R0.wheat3.exw_european_russia.sovecon", d, "RUB/t", "EXW European Russia", "wheat class 3", 14500, page="RU")
    for m in ("2026-06", "2026-07", "2026-08"):
        add("FLOOR.wheat.cpt", m, "USD/t", "CPT", "wheat, minimum allowable export price", 180, kind="monthly")
        add("FLOOR.corn.cpt", m, "USD/t", "CPT", "corn, minimum allowable export price", 150, kind="monthly")
    steps = [{"side": "UA", "date": "2026-07-22", "event": "corridor", "source": "https://example.org/s1"},
             {"side": "UA", "date": "2026-08-01/12", "event": "partial", "source": "https://example.org/s2"},
             {"side": "RU", "date": "2026-07-10", "event": "azov", "source": "https://example.org/s3"},
             {"side": "RU", "date": "2026-07-27/2026-07-31", "event": "taman", "source": "https://example.org/s4"},
             {"side": "RU", "date": "2026-08-10/2026-08-14", "event": "novorossiysk", "source": "https://example.org/s5"}]

    def page_rows(page, dates):
        rows = []
        for d in dates:
            src = f"https://example.org/{page}/{d}"
            rows.append({"source": src, "published": d, "price_date": d, "via": "browser",
                         "cells_read": sum(1 for c in cells if c["source"] == src and c["published"] == d)})
        return rows

    ru_cov = page_rows("RU", fridays("2026-05-22", "2026-09-11") + fridays("2025-05-30", "2025-08-29"))
    ua_cov = {"spike_weekly_2026": {"opened": fridays("2026-05-29", "2026-09-11")},
              "ukragroconsult_exw": {"opened": ["2026-06-27", "2026-08-03"],
                                     "not_on_page": [w for w in fridays("2026-05-29", "2026-09-11") if w not in ("2026-06-26", "2026-07-31")]},
              "spike_weekly_2025": {"opened": fridays("2025-06-06", "2025-08-29")},
              "euronext_2025": {"opened": fridays("2025-05-30", "2025-09-12")},
              "graintrade": page_rows("GT", fridays("2026-05-29", "2026-09-11") + fridays("2025-05-30", "2025-09-12"))}
    return {"cells": cells, "steps": steps, "sides": {"UA": {"coverage": ua_cov}, "RU": {"coverage": ru_cov}}}


def fam_of(families, source):
    return [f for f in families if f["source"] == source][0]


def selftest() -> int:
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    GT = "exchange purchase price page"
    clean = fixture()
    objects, led = run(clean)
    crit = {c["name"]: c["passed"] for c in criteria_for(clean, led)}
    expect(all(crit.values()), f"clean fixture fails a structural check: {crit}")

    # B111-1: a cell without a source, a cell without a basis, a malformed published date
    bad = copy.deepcopy(clean); bad["cells"][3]["source"] = ""
    expect(check_cells(bad["cells"]), "B111-1 does not report a missing source")
    bad = copy.deepcopy(clean); del bad["cells"][5]["basis"]
    expect(check_cells(bad["cells"]), "B111-1 does not report a missing basis")
    bad = copy.deepcopy(clean); bad["cells"][0]["published"] = "last Monday"
    expect(check_cells(bad["cells"]), "B111-1 does not report a malformed published date")

    # B111-2: an FCA value filed under the CPT column; a third contract in W; a 2025 twin of another grade
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "U2.corn.fca_chop"][0]["series"] = "U1.corn.cpt_odesa"
    expect(check_columns(bad["cells"]), "B111-2 does not report an FCA value in the CPT column")
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "W.wheat.euronext"][0]["contract"] = "2027-03"
    expect(check_columns(bad["cells"]), "B111-2 does not report an unknown W contract")
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "REF2025.U1.wheat2.cpt_terminal.graintrade"][4]["grade"] = "wheat grade III"
    expect(check_columns(bad["cells"]), "B111-2 does not report a 2025 cell of another grade in the twin column")

    # B111-3: a premium across a week, a change across two columns
    expect(not check_arithmetic(led.pairs), "B111-3 flags the clean run")
    u2 = [c for c in clean["cells"] if c["series"] == "U2.corn.fca_chop"]
    u1 = {c["date"]: c for c in clean["cells"] if c["series"] == "U1.corn.cpt_odesa"}
    probe = Ledger()
    try:
        probe.across(u2[1], u1[u2[0]["date"]])
        expect(False, "B111-3 lets a premium be taken across two weeks")
    except ValueError:
        pass
    expect(check_arithmetic(probe.pairs), "B111-3 does not report the logged cross-week premium")
    probe = Ledger()
    try:
        probe.over(u2[0], u1[u2[1]["date"]])
        expect(False, "B111-3 lets a change be taken across two columns")
    except ValueError:
        pass
    expect(check_arithmetic(probe.pairs), "B111-3 does not report the logged cross-column change")

    # B111-4: a dropped zero week, a dropped week of the interior page, a dropped 2025 page, a dropped W week,
    # a page row that counts one cell too many
    bad = copy.deepcopy(clean)
    zero = [r for r in bad["sides"]["RU"]["coverage"] if r["cells_read"] == 0][0]
    bad["sides"]["RU"]["coverage"].remove(zero)
    expect(check_coverage(bad)[0], "B111-4 does not report a dropped zero week")
    bad = copy.deepcopy(clean)
    bad["sides"]["UA"]["coverage"]["ukragroconsult_exw"]["not_on_page"].pop()
    expect(check_coverage(bad)[0], "B111-4 does not report a dropped week of the interior page")
    bad = copy.deepcopy(clean)
    bad["sides"]["UA"]["coverage"]["graintrade"] = [r for r in bad["sides"]["UA"]["coverage"]["graintrade"]
                                                    if r["price_date"] != "2025-07-18"]
    expect(check_coverage(bad)[0], "B111-4 does not report a dropped 2025 page of the exchange")
    bad = copy.deepcopy(clean)
    bad["sides"]["UA"]["coverage"]["euronext_2025"]["opened"].remove("2025-08-08")
    expect(check_coverage(bad)[0], "B111-4 does not report a dropped week of the 2025 futures history")
    bad = copy.deepcopy(clean)
    [r for r in bad["sides"]["UA"]["coverage"]["graintrade"] if r["price_date"] == "2026-07-24"][0]["cells_read"] += 1
    expect(check_coverage(bad)[0], "B111-4 does not report a page row that counts a cell the disk does not hold")

    # the mapping from a move to a state, every verdict row of MAPPING, then every not-read row
    for group, how, state in MAPPING[:8]:
        sign = +1 if group.startswith("b") else -1
        dose = "up" if "dose up" in group else "down"
        move = -5 if "below" in how else 5
        expect(read_state(move, 1, dose, cut_sign=sign)[0] == state, f"mapping row {group} / {how} does not give {state}")
    expect(read_state(0.5, 1, "up")[0] == NOT_READ and read_state(-0.5, 1, "down", cut_sign=+1)[0] == NOT_READ,
           "a move within the floor is read")
    expect(read_state(-50, None, "up")[0] == NOT_READ, "a reading without a measured floor is read")
    expect({m[2] for m in MAPPING[8:]} == {NOT_READ}, "a not-read row of the mapping points at a verdict")

    # the floor: median of absolute moves, raised to the grid
    expect(median_abs([-1.0, 3.0]) == 2.0 and floor_of(2.5, 2.0) == 2.5 and floor_of(0.1, 2.0) == 2.0
           and floor_of(1.0, None) is None, "the floor is not max(grid, median |move|)")

    # the floor takes its 2025 windows from the twin column, and none across the contract roll of W
    gt_a = fam_of(objects["a"]["UA"], GT)
    expect(gt_a["floors"][1]["windows_2025"] == 14, f"a: 2025 one-week windows {gt_a['floors'][1]['windows_2025']}, not 14")
    expect(fam_of(objects["a"]["UA"], "broker weekly report")["floors"][1]["windows_2025"] == 0,
           "a: a family without a 2025 column counts 2025 windows")
    expect(gt_a["floors"][1]["windows_june_2026"] == 3 and gt_a["floors"][2]["windows_june_2026"] == 2,
           f"a: June windows {gt_a['floors'][1]['windows_june_2026']} and {gt_a['floors'][2]['windows_june_2026']}, "
           "not 3 and 2: a window ends outside June")
    bad = copy.deepcopy(clean)
    bad["cells"] = [c for c in bad["cells"] if c["series"] != "REF2025.U1.wheat2.cpt_terminal.graintrade"]
    ob, _ = run(bad)
    expect(fam_of(ob["a"]["UA"], GT)["floors"][1]["windows_2025"] == 0, "a: 2025 windows counted without the twin column")

    # flags reach the reading: a nominal port cell, and a port at the minimum export price
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "U1.wheat115.cpt_odesa" and c["date"] == "2026-07-31"][0]["nominal"] = True
    ob, _ = run(bad)
    r = [x for x in fam_of(ob["a"]["UA"], "broker weekly report")["readings"] if x["to"] == "2026-07-31"]
    expect(r and all(x["state"] == NOT_READ and "nominal" in x["reason"] for x in r), "a nominal end cell is read")
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "FLOOR.wheat.cpt" and c["date"] == "2026-07"][0]["value"] = 195
    ob, _ = run(bad)
    r = [x for x in fam_of(ob["a"]["UA"], "broker weekly report")["readings"] if x["to"] == "2026-07-31"]
    expect(r and all(x["state"] == NOT_READ and "minimum export price" in x["reason"] for x in r),
           "a port at the minimum export price is read")

    # a, long windows: a window with no dated step inside is not read
    for fam in objects["a"]["UA"]:
        r = [x for x in fam["long_windows"] if x["to"] == "2026-07-17"][0]
        expect(r["state"] == NOT_READ and r["reason"] == "no dated step inside the window",
               f"a long window before the first Ukrainian step is read ({fam['source']})")
    r = [x for x in objects["a"]["RU"][0]["long_windows"] if x["to"] == "2026-07-17"][0]
    expect(r["steps_inside"] == ["2026-07-10"], "a long window after the first Russian step does not hold it")

    # b: with a floor, a cut that widens the premium matches, one that narrows it does not; a reopening that narrows it matches
    gt_b = fam_of(objects["b"]["UA"], GT)
    r = {(x["step"], x["weeks"]): x for x in gt_b["readings"]}
    expect(r[("2026-07-22", 1)]["state"] == MATCH, f"b: a widening premium at a cut is {r[('2026-07-22', 1)]['state']}")
    expect(r[("2026-08-01/12", 1)]["state"] == MATCH, f"b: a narrowing premium at a reopening is {r[('2026-08-01/12', 1)]['state']}")
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "U2.corn.daf.graintrade" and c["date"] == "2026-07-24"][0]["value"] -= 14
    ob, _ = run(bad)
    r = [x for x in fam_of(ob["b"]["UA"], GT)["readings"] if x["step"] == "2026-07-22" and x["weeks"] == 1][0]
    expect(r["state"] == MISS, f"b: a narrowing premium at a cut is {r['state']}")
    expect(all(w["state"] == NOT_READ for fam in objects["b"]["RU"] for w in fam["readings"]), "b reads without a floor")

    # d: the 2025 week missing turns a reading off; with the twin floor a cut matches and a reopening does not
    bad = copy.deepcopy(clean)
    bad["cells"] = [c for c in bad["cells"] if not (c["series"].startswith("REF2025.R0") and c["date"] == "2025-07-18")]
    ob, _ = run(bad)
    r = [x for x in ob["d"]["RU"][0]["readings"] if x["week"] == "2026-07-17"]
    expect(r and r[0]["state"] == NOT_READ and "2025" in r[0]["reason"], "d reads a week whose 2025 twin is missing")
    expect(objects["d"]["RU"][0]["floor"]["floor"] is not None, "d has no floor on the clean fixture")
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "U0.wheat2.exw_elevator.graintrade" and c["date"] == "2026-07-24"][0]["approx"] = True
    ob, _ = run(bad)
    r = [x for x in fam_of(ob["d"]["UA"], GT)["readings"] if x["week"] == "2026-07-24"][0]
    expect(r["state"] == NOT_READ and "flagged" in r["reason"], "d reads a flagged interior end")
    gt_d = {x["week"]: x for x in fam_of(objects["d"]["UA"], GT)["readings"]}
    expect(gt_d["2026-07-24"]["state"] == MATCH, f"d: a falling interior at a cut is {gt_d['2026-07-24']['state']}")
    expect(gt_d["2026-08-07"]["state"] == MISS, f"d: a falling interior at a reopening is {gt_d['2026-08-07']['state']}")

    # the 2025 windows of b and d come from the twin columns
    expect(gt_b["floors"][1]["windows_2025"] == 15, f"b: 2025 one-week windows {gt_b['floors'][1]['windows_2025']}, not 15")
    expect(fam_of(objects["d"]["UA"], GT)["floor"]["windows_2025"] == 15, "d: the 2025 weekly changes are not all in the floor")

    # unchanged runs are counted from the column itself
    r = [x for x in fam_of(objects["a"]["UA"], "broker weekly report")["path"] if x["date"] == "2026-08-21"][0]
    expect(r["port_unchanged_weeks"] == 3, f"a: a port unchanged for three weeks prints {r['port_unchanged_weeks']}")
    r = [x for x in gt_b["path_2025"] if x["date"] == "2025-06-13"][0]
    expect(r["cut_unchanged_weeks"] == 2 and r["open_unchanged_weeks"] == 0,
           f"b: unchanged runs print {r['cut_unchanged_weeks']} and {r['open_unchanged_weeks']}")
    r = [x for x in fam_of(objects["d"]["UA"], "interior price page")["readings"] if x["week"] == "2026-07-31"][0]
    expect(r["unchanged_weeks"] == 8, f"d: an interior unchanged for eight weeks prints {r['unchanged_weeks']}")

    # e: each week's state comes from the cells and the coverage rows, one planted case per state
    def e_state(ob, side, column, week, twin=False):
        fam = [f for f in ob["e"]["families"] if f["side"] == side and f["column"] == column][0]
        return [r for r in fam["path_2025" if twin else "path"] if r["week"] == week][0]["state"]

    expect(e_state(objects, "UA", "U1.wheat115.cpt_odesa", "2026-07-24") == "quoted", "e: a clean port cell is not quoted")
    expect(e_state(objects, "UA", "U1.wheat115.cpt_odesa", "2026-05-29") == "not quoted", "e: a read issue without the cell is not 'not quoted'")
    bad = copy.deepcopy(clean)
    [c for c in bad["cells"] if c["series"] == "U1.wheat115.cpt_odesa" and c["date"] == "2026-07-31"][0]["nominal"] = True
    [c for c in bad["cells"] if c["series"] == "FLOOR.wheat.cpt" and c["date"] == "2026-08"][0]["value"] = 195
    bad["cells"] = [c for c in bad["cells"] if not (c["series"] == "U1.wheat2.cpt_terminal.graintrade" and c["date"] == "2026-08-07")]
    ob, _ = run(bad)
    expect(e_state(ob, "UA", "U1.wheat115.cpt_odesa", "2026-07-31") == "nominal", "e: a nominal cell is not reported as nominal")
    expect(e_state(ob, "UA", "U1.wheat115.cpt_odesa", "2026-08-07") == "at or below the minimum export price",
           "e: a port at the minimum export price is not reported")
    expect(e_state(ob, "UA", "U1.wheat2.cpt_terminal.graintrade", "2026-08-07") == "not quoted",
           "e: a page read without the cell is not 'not quoted'")
    sm_bad = [f for f in ob["e"]["families"] if f["column"] == "U1.wheat115.cpt_odesa"][0]["summary"]
    expect(sm_bad["from_step_week"] == {"priced": 1, "unpriced": 7, "unread": 0}
           and sm_bad["first_unpriced_week_from_step_week"] == "2026-07-31",
           f"e: a nominal week or a week at the minimum export price is counted as priced: {sm_bad}")
    expect(e_state(objects, "UA", "U0.wheat.exw", "2026-09-04") == "not on the page", "e: a week off the page is not reported")
    bad = copy.deepcopy(clean)
    bad["cells"].append({"series": "W.wheat.euronext", "date": "2026-08-28", "unit": "EUR/t", "basis": "Euronext futures",
                         "grade": "milling wheat", "value": 240, "kind": "weekly", "contract": "2026-12", "zone": False,
                         "source": "https://example.org/W/2026-08-28", "published": "2026-08-28"})
    ob, _ = run(bad)
    expect(e_state(ob, "W", "W.wheat.euronext", "2026-08-28") == "rolled to another contract", "e: a contract roll is not reported")
    expect(e_state(ob, "W", "W.wheat.euronext", "2026-09-04") == "not quoted", "e: a read week without any contract is not 'not quoted'")
    bad = copy.deepcopy(clean)
    for r in bad["sides"]["RU"]["coverage"]:
        if r["price_date"] == "2026-07-03":
            r["via"] = "none"
        if r["price_date"] == "2026-06-26":
            r["via"] = "fetch"
    [c for c in bad["cells"] if c["series"] == "R0.wheat3.exw_european_russia.sovecon" and c["date"] == "2026-07-03"][0]["kind"] = "implied"
    bad["cells"] = [c for c in bad["cells"] if not (c["series"] == "R0.wheat3.exw_european_russia.sovecon" and c["date"] == "2026-06-26")]
    bad["sides"]["UA"]["coverage"]["graintrade"] = [r for r in bad["sides"]["UA"]["coverage"]["graintrade"] if r["price_date"] != "2026-06-12"]
    bad["cells"] = [c for c in bad["cells"] if not (c["series"] == "U0.wheat2.exw_elevator.graintrade" and c["date"] == "2026-06-12")]
    ob, _ = run(bad)
    expect(e_state(ob, "RU", "R0.wheat3.exw_european_russia.sovecon", "2026-07-03") == "implied from the next issue",
           "e: an implied cell is not reported as implied")
    expect(e_state(ob, "RU", "R2.wheat125.fob_baltic.ikar", "2026-07-03") == "no issue found", "e: a week with no issue found is not reported")
    expect(e_state(ob, "RU", "R0.wheat3.exw_european_russia.sovecon", "2026-06-26") == "not in the rewrite read",
           "e: a line missing from a rewrite is read as not quoted")
    expect(e_state(ob, "UA", "U0.wheat2.exw_elevator.graintrade", "2026-06-12") == "issue not read", "e: a page never opened is not reported")
    expect(e_state(objects, "RU", "R1.wheat125.fob_novo.rusagrotrans", "2026-07-10") == "issue not read",
           "e: a note that was not opened is read as a week without a quote")
    fam = [f for f in objects["e"]["families"] if f["column"] == "U1.wheat115.cpt_odesa"][0]
    sm = fam["summary"]
    expect(sm["step_week"] == "2026-07-24" and sm["weeks_before"] == 8 and sm["before"] == {"priced": 7, "unpriced": 1, "unread": 0}
           and sm["from_step_week"] == {"priced": 5, "unpriced": 3, "unread": 0}
           and sm["first_unpriced_week_from_step_week"] == "2026-08-28", f"e: the summary around the first cut step is off: {sm}")
    fam = [f for f in objects["e"]["families"] if f["column"] == "U0.wheat.exw"][0]
    expect(fam["summary"]["from_step_week"]["unread"] == 3 and fam["summary"]["first_unpriced_week_from_step_week"] is None,
           f"e: weeks off the page are counted as weeks without a price: {fam['summary']}")
    expect({presence_kind(k) for k in PRESENCE_CODES} == {"priced", "unpriced", "unread"}
           and len(PRICED) + len(UNPRICED) + len(UNREAD) == len(PRESENCE_CODES), "e: a state sits in no kind or in two")
    expect(e_state(objects, "UA", "U2.corn.daf.graintrade", "2025-07-18", twin=True) == "quoted", "e: the 2025 column is not read")

    # the step table is read from the file: a missing step stops the run
    bad = copy.deepcopy(clean)
    bad["steps"] = [s for s in bad["steps"] if s["date"] != "2026-07-10"]
    try:
        run(bad)
        expect(False, "a reading step missing from the step table does not stop the run")
    except ValueError:
        pass

    print(f"selftest: {checks - len(fails)} of {checks} checks pass")
    for f in fails:
        print("  FAIL", f)
    return 1 if fails else 0


# ---------------------------------------------------------------- main

def show_state(r, key, unit):
    mv = "" if r[key] is None else f"{r[key]:+.2f}{unit}"
    return f"{mv}  {r['state']} ({r['reason']})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    objects, led = run(data)
    criteria = criteria_for(data, led)
    tally = counts(objects)

    for side in ("UA", "RU"):
        for fam in objects["a"][side]:
            base = fam["baseline"]
            print(f"a {side} [{fam['source']}] {fam['port']}: June mean over {', '.join(base['base_weeks'])}: "
                  f"port {base['port_mean']}, W {base['W_mean']}; grid {base['grid_pp']} pp")
            for k, v in sorted(fam["floors"].items(), key=lambda kv: int(kv[0])):
                print(f"   floor {k} wk: {v['floor']} pp (noise {v['noise']}, June windows {v['windows_june_2026']}, "
                      f"2025 windows {v['windows_2025']}, zero moves {v['zero_moves']})")
            for r in fam["path"]:
                if r.get("relative_pp") is not None:
                    print(f"   {r['date']}  port {r['port']:>7}  W {r['W']:>7}  rel {r['relative_pp']:>8.2f} pp  "
                          f"{'+'.join(r['port_flags'] + r['W_flags'])}{'' if r['readable'] else ' (not readable)'}"
                          f"{'  unchanged ' + str(r['port_unchanged_weeks']) + ' wk' if r['port_unchanged_weeks'] else ''}")
            for r in fam["readings"]:
                print(f"   step {r['step']} ({r['dose']}) {r['from']} -> {r['to']}: {show_state(r, 'move_pp', ' pp')}  floor {r['floor_pp']}")
            for r in fam["long_windows"]:
                print(f"   long {r['from']} -> {r['to']} ({r['weeks']} wk): {show_state(r, 'move_pp', ' pp')}  floor {r['floor_pp']}")
    for side in ("UA", "RU"):
        for fam in objects["b"][side]:
            print(f"b {side} [{fam['source']}] {fam['open']} over {fam['cut']}: floors "
                  + "; ".join(f"{k} wk {v['floor']} ({v['windows_june_2026']} June, {v['windows_2025']} 2025)" for k, v in fam["floors"].items()))
            for p in fam["path"]:
                print(f"   {p['date']}  open {p['open']}  cut {p['cut']}  premium {p['premium']}  {'; '.join(p['flags'])}"
                      f"{'  open unchanged ' + str(p['open_unchanged_weeks']) + ' wk' if p['open_unchanged_weeks'] else ''}"
                      f"{'  cut unchanged ' + str(p['cut_unchanged_weeks']) + ' wk' if p['cut_unchanged_weeks'] else ''}")
            for r in fam["readings"]:
                print(f"   step {r['step']} ({r['dose']}) {r['from']} -> {r['to']}: {show_state(r, 'change', '')}  floor {r['floor']}")
    for fam in objects["c"]["families"]:
        for r in fam["readings"]:
            print(f"c UA [{fam['source']}]: {r['weakening_segment_end']} -> {r['cut_week']}: {show_state(r, 'move_pp', ' pp')}  floor {r['floor_pp']}")
    for side in ("UA", "RU"):
        for fam in objects["d"][side]:
            fl = fam["floor"]
            print(f"d {side} [{fam['source']}] {fam['column']}: floor {fl['floor']} (noise {fl['noise']}, June windows "
                  f"{fl['windows_june_2026']}, 2025 windows {fl['windows_2025']}, zero moves {fl['zero_moves']}, grid {fl['grid']})")
            for r in fam["readings"]:
                print(f"   step {r['step']} week {r['week']}: {r['change']} (2025 {r['same_week_2025']}: {r['change_2025']}; "
                      f"W {r['W_change']}; unchanged {r['unchanged_weeks']} wk)  {r['state']} ({r['reason']})")
    e = objects["e"]
    print("e: " + ", ".join(f"{v} {k}" for k, v in e["codes"].items()))
    for label, key in (("2026", "path"), ("2025", "path_2025")):
        fams = [f for f in e["families"] if f[key] is not None]
        weeks = sorted({r["week"] for f in fams for r in f[key]})
        print(f"e {label}: weeks " + " ".join(w[5:] for w in weeks))
        for f in fams:
            codes = {r["week"]: r["code"] for r in f[key]}
            line = "".join(f"{codes.get(w, ' '):>6}" for w in weeks)
            print(f"   {f['side']:2} {f['role']:10} {f['source'][:28]:28} {f['column'][:40]:40}{line}")
    for f in e["families"]:
        sm = f["summary"]
        print(f"   e {f['side']} {f['column']}: step week {sm['step_week']}; before {sm['before']}; from it {sm['from_step_week']}; "
              f"first priced {sm['first_priced_week']}; first unpriced from the step week {sm['first_unpriced_week_from_step_week']}")
    print("states:", json.dumps(tally))
    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['detail'][:300]}")

    rec = {"stage": "B111",
           "config": {"data": "data/b111_black_sea_prices.json", "study": list(STUDY), "june": list(JUNE),
                      "same_weeks_2025": list(SAME_WEEKS_2025), "june_2025": list(JUNE_2025), "pre_cut": PRE_CUT,
                      "windows_weeks": list(WINDOWS), "W_column": list(W_COL), "W_column_2025": list(W25_COL),
                      "grid": GRID, "read_steps": [list(s) for s in READ_STEPS], "families": SIDES,
                      "presence": PRESENCE, "presence_windows": {f"{k[0]} {k[1]}": v for k, v in PRESENCE_WINDOWS.items()},
                      "coverage_families": [list(f) for f in FAMILIES]},
           "criteria": criteria, "mapping": [list(m) for m in MAPPING], "states": tally,
           "objects": objects, "context": context(data)}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
