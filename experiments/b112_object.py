"""B112, first look: print the objects before any criterion is written.

Reads what `experiments/b112_fetch.py` wrote under `data/b112/raw` and prints six blocks.
Nothing here is a criterion. Each block prints an object and says in one line what to look at.

  0  coverage: first and last period of each series family per country, and the thinnest cells
  1  where reserves sit: each country's share of the euro area total, around each dated rule
  2  what moved them: the month's change in reserves beside refinancing, own purchases, the
     TARGET balance, banknotes and deposits of other residents, around the same dates
  3  refinancing doses: the months when longer-term refinancing moved most, per country, and the
     change in reserves and in the TARGET balance that month and the three after
  4  purchases against TARGET: over each purchase window, what each central bank bought beside
     the change in its TARGET balance and in its banks' reserves
  5  how much of each banking system's payments cross a border: TARGET payments sent inside the
     national component and to other components against average reserves, per year, and the
     cross-border share of interbank loans and deposits
  6  the same-month share of a refinancing dose that stays in the borrowing country, by the rate
     rule in force, with each country's month-to-month noise beside it

The class is the national component: minimum reserves are held "with the relevant NCBs in each
euro area Member State in which they are established" (Regulation (EU) 2021/378, Article
3(1)(b)).

    python experiments/b112_object.py            # all blocks
    python experiments/b112_object.py --block 1  # one block
    python experiments/b112_object.py --write    # the four criteria, and results/b112_object.json
    python experiments/b112_object.py --selftest # seeded fixture and seeded criteria, no data needed
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b112" / "raw"

COUNTRIES = ("AT", "BE", "BG", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR",
             "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK")
BIG = ("DE", "FR", "NL", "IT", "ES", "BE", "LU", "FI", "AT", "IE", "PT", "GR")

# Dated rules that change what it costs or pays to hold reserves, each with the month of effect.
# Every date is copied from the ECB text named beside it.
RULES = (
    ("2019-10", "two-tier system applies from 2019-10-30, exempt tier 6 x minimum reserves at 0%"
                " (press release 2019-09-12)"),
    ("2022-07", "deposit facility rate raised to 0% from 2022-07-27, which makes the exempt tier "
                "redundant (two-tier system page)"),
    ("2022-09", "multiplier set to 0 from the maintenance period starting 2022-09-14 "
                "(two-tier system page)"),
    ("2022-11", "TLTRO III rate indexed to the average key rates from 2022-11-23, with added "
                "voluntary repayment dates (press release 2022-10-27)"),
    ("2022-12", "minimum reserves remunerated at the deposit facility rate from 2022-12-21 "
                "(press release 2022-10-27)"),
    ("2023-09", "minimum reserves remunerated at 0% from 2023-09-20 (press release 2023-07-27)"),
    ("2024-09", "spread between the MRO rate and the deposit facility rate cut from 50 to 15 "
                "basis points from 2024-09-18 (press release 2024-03-13)"),
)

# Windows over which the Eurosystem's securities holdings for monetary policy grew or shrank.
# The central bank balance sheets start in 2016-06, so the first window opens there.
WINDOWS = (
    ("2016-06", "2018-12", "APP net purchases, from the first month on the balance sheets"),
    ("2019-10", "2022-06", "APP restart and PEPP"),
    ("2022-06", "2026-12", "reinvestments reduced and then stopped"),
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _read(path: Path) -> list[dict]:
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


class Store:
    """Every series under `root`, in euro billions where the metadata gives euro."""

    def __init__(self, root: Path):
        self.series: dict[str, dict[str, float]] = {}
        self.meta: dict[str, dict] = {}
        for meta_path in sorted(root.glob("*.meta.csv")):
            data_path = meta_path.with_name(meta_path.name.replace(".meta.csv", ".csv"))
            if not data_path.exists():
                continue
            for row in _read(meta_path):
                self.meta[row["KEY"]] = row
            for row in _read(data_path):
                if row["OBS_VALUE"] == "":
                    continue
                key = row["KEY"]
                m = self.meta.get(key, {})
                scale = 1.0
                if m.get("UNIT") == "EUR" and m.get("UNIT_MULT", "") != "":
                    scale = 10.0 ** (int(m["UNIT_MULT"]) - 9)
                self.series.setdefault(key, {})[row["TIME_PERIOD"]] = float(row["OBS_VALUE"]) * scale

    def find(self, **parts) -> dict[str, dict[str, float]]:
        """Series whose key has the given value at the given position (0 is the flow)."""
        out = {}
        for key, s in self.series.items():
            p = key.split(".")
            if all(int(i) < len(p) and p[int(i)] == v for i, v in parts.items()):
                out[key] = s
        return out

    def one(self, key: str) -> dict[str, float]:
        return self.series.get(key, {})


def ilm(st: Store, c: str, item: str) -> dict[str, float]:
    got = [s for k, s in st.find(**{"0": "ILM", "1": "M", "2": c, "4": item}).items()]
    return got[0] if len(got) == 1 else {}


def reserves(st: Store, c: str) -> dict[str, float]:
    """Liabilities to credit institutions related to monetary policy operations (L020000)."""
    return ilm(st, c, "L020000")


def tgb(st: Store, c: str) -> dict[str, float]:
    sector = "E" if c == "4F" else "N"
    return st.one(f"TGB.M.{c}.{sector}.A094T.U2.EUR.E")


def bsi(st: Store, c: str, item: str, area: str, sector: str) -> dict[str, float]:
    return st.one(f"BSI.M.{c}.N.A.{item}.A.1.{area}.{sector}.Z01.E")


def months(a: str, b: str) -> list[str]:
    y, m = int(a[:4]), int(a[5:7])
    out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def shift(month: str, k: int) -> str:
    y, m = int(month[:4]), int(month[5:7]) - 1 + k
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def delta(s: dict[str, float], month: str) -> float | None:
    prev = shift(month, -1)
    if month in s and prev in s:
        return s[month] - s[prev]
    return None


def fmt(x: float | None, width: int = 8, digits: int = 1) -> str:
    return f"{'.':>{width}s}" if x is None else f"{x:{width}.{digits}f}"


def members(st: Store, cols: list[str]) -> tuple[str, ...]:
    """Countries with a reserve figure in every one of these months.

    Croatia's balance sheet starts in 2023-01 and Bulgaria's in 2025-12, so a share taken over
    all twenty-one countries would change its denominator at each accession. Over a window the
    denominator is the countries present throughout it.
    """
    return tuple(c for c in COUNTRIES if all(m in reserves(st, c) for m in cols))


def shares(st: Store, month: str, among: tuple[str, ...] | None = None) -> dict[str, float]:
    among = COUNTRIES if among is None else among
    held = {c: reserves(st, c).get(month) for c in among}
    total = sum(v for v in held.values() if v is not None)
    if total <= 0 or any(v is None for v in held.values()):
        return {}
    return {c: v / total for c, v in held.items()}


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def block0(st: Store) -> None:
    print("\n== 0. coverage. Look at: the first period of each family, and the thinnest cells")
    fams = (("reserves L020000", lambda c: reserves(st, c)),
            ("refinancing A050200", lambda c: ilm(st, c, "A050200")),
            ("securities A070100", lambda c: ilm(st, c, "A070100")),
            ("TARGET balance", lambda c: tgb(st, c)),
            ("MFI claims on own NCB", lambda c: bsi(st, c, "A20", "U6", "1100")),
            ("MFI loans to other euro area MFIs", lambda c: bsi(st, c, "A20", "U5", "1200")))
    print(f"{'':6s}" + "".join(f"{name[:26]:>28s}" for name, _ in fams))
    for c in COUNTRIES:
        cells = []
        for _, get in fams:
            s = get(c)
            cells.append(f"{min(s)}..{max(s)} n={len(s)}" if s else "none")
        print(f"{c:6s}" + "".join(f"{x:>28s}" for x in cells))
    last = max((m for c in COUNTRIES for m in reserves(st, c)), default=None)
    if last:
        held = sorted((reserves(st, c).get(last, float("nan")), c) for c in COUNTRIES)
        print(f"\nsmallest reserve holdings at {last}, euro billions: "
              + ", ".join(f"{c} {v:.2f}" for v, c in held[:5]))


def block1(st: Store) -> None:
    print("\n== 1. share of euro area reserves, percent. Look at: whether a row moves at the rule"
          " month and stays, or moves and comes back")
    for month, text in RULES:
        cols = [shift(month, k) for k in (-1, 0, 1, 2, 3)]
        among = members(st, cols)
        got = {m: shares(st, m, among) for m in cols}
        print(f"\n{month}  {text}  [{len(among)} countries in the denominator]")
        print(f"{'':4s}" + "".join(f"{m:>9s}" for m in cols))
        for c in BIG:
            print(f"{c:4s}" + "".join(fmt(100 * got[m][c], 9, 2) if got[m] else fmt(None, 9)
                                       for m in cols))


def block2(st: Store) -> None:
    print("\n== 2. the month's change, euro billions: reserves against what moved them. Look at:"
          " which column carries the change in reserves")
    head = ("dR", "refin", "secur", "TARGET", "notes", "res.dep", "rest")
    for month, text in RULES:
        print(f"\n{month}  {text}")
        print(f"{'':4s}" + "".join(f"{h:>9s}" for h in head))
        for c in BIG:
            dR = delta(reserves(st, c), month)
            parts = [delta(ilm(st, c, "A050000"), month), delta(ilm(st, c, "A070100"), month),
                     delta(tgb(st, c), month), delta(ilm(st, c, "L010000"), month),
                     delta(ilm(st, c, "L050000"), month)]
            rest = None
            if dR is not None and all(p is not None for p in parts):
                rest = dR - (parts[0] + parts[1] + parts[2] - parts[3] - parts[4])
            print(f"{c:4s}" + "".join(fmt(x, 9) for x in [dR] + parts + [rest]))


def block3(st: Store, top: int = 8) -> None:
    print("\n== 3. refinancing doses, euro billions. Look at: whether reserves keep the dose in the"
          " borrowing country in the months after, or the TARGET balance gives it away")
    allm = sorted({m for c in COUNTRIES for m in ilm(st, c, "A050200")})
    net = []
    for m in allm[1:]:
        # countries whose balance sheet covers both months; accessions drop out of that month
        d = [x for x in (delta(ilm(st, c, "A050200"), m) for c in COUNTRIES) if x is not None]
        if d:
            net.append((abs(sum(d)), m, sum(d)))
    for _, m, total in sorted(net, reverse=True)[:top]:
        print(f"\n{m}: euro area net change in longer-term refinancing {total:+.1f}")
        print(f"{'':4s}{'dose':>9s}" + "".join(f"{'dR+' + str(k):>9s}" for k in range(4))
              + "".join(f"{'dT+' + str(k):>9s}" for k in range(4)))
        rows = []
        for c in COUNTRIES:
            dose = delta(ilm(st, c, "A050200"), m)
            if dose is None or abs(dose) < 5:
                continue
            dR = [delta(reserves(st, c), shift(m, k)) for k in range(4)]
            dT = [delta(tgb(st, c), shift(m, k)) for k in range(4)]
            rows.append((-abs(dose), c, dose, dR, dT))
        for _, c, dose, dR, dT in sorted(rows):
            print(f"{c:4s}{fmt(dose, 9)}" + "".join(fmt(x, 9) for x in dR)
                  + "".join(fmt(x, 9) for x in dT))


def block4(st: Store) -> None:
    print("\n== 4. purchases against TARGET, euro billions over each window. Look at: which"
          " countries' banks end up holding what other central banks bought")
    for a, b, text in WINDOWS:
        print(f"\n{a} to {b}: {text}")
        print(f"{'':4s}{'bought':>9s}{'dTARGET':>9s}{'dR':>9s}{'drefin':>9s}")
        for c in COUNTRIES + ("4F",):
            sec, T = ilm(st, c, "A070100"), tgb(st, c)
            R, L = reserves(st, c), ilm(st, c, "A050200")
            first = max(a, min(sec)) if sec else None
            last = min(b, max(sec)) if sec else None

            def chg(s):
                return (s[last] - s[first]) if first and last and first in s and last in s else None
            print(f"{c:4s}" + "".join(fmt(chg(s), 9) for s in (sec, T, R, L)))


def pss_values(st: Store, c: str) -> tuple[dict[str, float], dict[str, float]]:
    """TARGET payments sent inside the national component (31) and to other components (32)."""
    for inst in ("I39", "I31"):
        inside = st.one(f"PSS.A.{c}.F000.{inst}.P101.VT.X0.31.EUR.E")
        across = st.one(f"PSS.A.{c}.F000.{inst}.P101.VT.X0.32.EUR.E")
        if inside and across:
            return inside, across
    return {}, {}


def block5(st: Store) -> None:
    print("\n== 5. how much of each banking system's payments cross a border. Look at: days a unit"
          " of reserves sits before it is paid to another country, against days before it is paid"
          " at home")
    years = sorted({y for c in COUNTRIES for y in pss_values(st, c)[0]})
    for y in years[-3:]:
        print(f"\n{y}: inside and across are euro billions sent in the year; avg R from month-end"
              f" reserves, or MFI claims on own NCB where the balance sheet does not reach")
        print(f"{'':4s}{'inside':>11s}{'across':>11s}{'across%':>9s}{'avg R':>9s}{'days@home':>10s}"
              f"{'days@abroad':>12s}{'loans x-b%':>11s}{'dep x-b%':>9s}")
        for c in COUNTRIES:
            inside, across = pss_values(st, c)
            vi, va = inside.get(y), across.get(y)
            R = reserves(st, c)
            vals = [v for m, v in R.items() if m.startswith(y)]
            src = "R"
            if len(vals) < 12:
                vals = [v for m, v in bsi(st, c, "A20", "U6", "1100").items() if m.startswith(y)]
                src = "B"
            avg = statistics.fmean(vals) if len(vals) == 12 else None
            share = 100 * va / (vi + va) if vi is not None and va is not None and vi + va > 0 else None
            d_home = 365 * avg / vi if avg and vi else None
            d_abroad = 365 * avg / va if avg and va else None

            def xb(item):
                u5, u2 = bsi(st, c, item, "U5", "1200"), bsi(st, c, item, "U2", "1200")
                pairs = [(u5[m], u2[m]) for m in u5 if m.startswith(y) and m in u2 and u2[m] > 0]
                return 100 * sum(p for p, _ in pairs) / sum(q for _, q in pairs) if pairs else None
            print(f"{c:4s}{fmt(vi, 11)}{fmt(va, 11)}{fmt(share, 9)}{fmt(avg, 8)}{src}"
                  f"{fmt(d_home, 10, 2)}{fmt(d_abroad, 12, 2)}{fmt(xb('A20'), 11)}{fmt(xb('L20'), 9)}")


# The rate on longer-term refinancing against the rate on holding reserves, by date. Each boundary
# is copied from the ECB text named beside it; the regime a month falls in is the one in force at
# the end of that month, because the balance sheets are end-of-month.
REGIMES = (
    ("2016-06", "TLTRO II: the MRO rate at allotment, as low as the deposit facility rate at allotment"
                " for banks that meet the lending benchmark", "press release 2016-03-10"),
    ("2019-09", "TLTRO III as first set: 10 bp above the average MRO rate over the life, as low as the"
                " average deposit facility rate plus 10 bp; from 2020-03-17 also bridge LTROs at the"
                " average deposit facility rate", "press releases 2019-06-06 and 2020-03-12"),
    ("2020-06", "special rate period from 2020-06-24: as low as 50 bp below the average deposit"
                " facility rate, extended to 2022-06-23", "press releases 2020-04-30 and 2020-12-10"),
    ("2022-11", "rate indexed to the average key rates from 2022-11-23, repayments",
     "press release 2022-10-27"),
)


def regime_of(month: str) -> str:
    name = "before the first TLTRO II allotment"
    for start, text, _ in REGIMES:
        if month >= start:
            name = text
    return name


def quiet_sd(st: Store, c: str, net: dict[str, float]) -> float | None:
    """Month-to-month noise of one country's reserves: months with little net refinancing,
    December and January left out because the year-end moves shares by more (block 1)."""
    ch = [delta(reserves(st, c), m) for m, n in net.items()
          if abs(n) < 20 and not m.endswith(("-12", "-01"))]
    ch = [x for x in ch if x is not None]
    return statistics.pstdev(ch) if len(ch) > 10 else None


def block6(st: Store) -> None:
    print("\n== 6. same-month retention of a refinancing dose, by the rate rule in force. Look at: the"
          " median retention in each regime, and which cells clear three times their noise")
    allm = sorted({m for c in COUNTRIES for m in ilm(st, c, "A050200")})
    net = {}
    for m in allm[1:]:
        d = [x for x in (delta(ilm(st, c, "A050200"), m) for c in COUNTRIES) if x is not None]
        net[m] = sum(d)
    sd = {c: quiet_sd(st, c, net) for c in COUNTRIES}
    print("noise, euro bn (sd of the monthly change in reserves in quiet months): "
          + ", ".join(f"{c} {sd[c]:.1f}" for c in COUNTRIES if sd[c] is not None))
    for start, text, source in REGIMES:
        cells = []
        for m in allm[1:]:
            if regime_of(m) != text:
                continue
            for c in COUNTRIES:
                dose = delta(ilm(st, c, "A050200"), m)
                dR, dT = delta(reserves(st, c), m), delta(tgb(st, c), m)
                if None in (dose, dR, dT) or sd[c] is None or abs(dose) < 3 * sd[c]:
                    continue
                cells.append((m, c, dose, dR / dose, -dT / dose, dose / sd[c]))
        print(f"\nfrom {start}: {text} ({source})")
        if not cells:
            print("  no cell clears three times its noise")
            continue
        print(f"  {len(cells)} cells; median retention {statistics.median(r[3] for r in cells):.2f},"
              f" median leak through TARGET {statistics.median(r[4] for r in cells):.2f}")
        for m, c, dose, ret, leak, z in cells:
            print(f"    {m} {c}  dose {dose:+7.1f} ({z:+5.1f} sd)  retention {ret:5.2f}  leak {leak:5.2f}")


BLOCKS = {0: block0, 1: block1, 2: block2, 3: block3, 4: block4, 5: block5, 6: block6}


# ---------------------------------------------------------------------------
# Criteria and record
# ---------------------------------------------------------------------------

RECORD = ROOT / "results" / "b112_object.json"
NOISE_MULTIPLE = 3          # a dose is read when it is this many times its country's monthly noise
QUIET_CUT = 20.0            # euro bn of net refinancing below which a month counts as quiet
SCAN_MULTIPLES = (2, 3, 4)  # the two knobs above, swept for the retention reading (11f)
SCAN_CUTS = (10.0, 20.0, 40.0)
CLOCK_YEARS = ("2019", "2020", "2021")
KNOWN_MONTHS = ("2019-09", "2019-11")  # end of the last month before, and of the first full month after

# ECB Occasional Paper 302 (September 2022), page 15, the two statements checked here. Each names
# countries and a direction; the check reads the same direction in the balance sheets.
KNOWN = (
    ("reserve share", "At the start of the TTS, banks in Italy, Greece, Portugal and Slovakia held"
                      " less EL than the allowances", ("IT", "GR", "PT", "SK"), +1),
    ("TARGET balance", "The TARGET2 claims of Germany, France, the Netherlands and Belgium declined"
                       " during the first weeks of the TTS", ("DE", "FR", "NL", "BE"), -1),
)
SOURCE_PATTERN = re.compile(r"press releases? \d{4}-\d{2}-\d{2}|two-tier system page")


def r4(x: float | None) -> float | None:
    return None if x is None else round(x, 4)


def net_refinancing(st: Store) -> dict[str, float]:
    allm = sorted({m for c in COUNTRIES for m in ilm(st, c, "A050200")})
    net = {}
    for m in allm[1:]:
        d = [x for x in (delta(ilm(st, c, "A050200"), m) for c in COUNTRIES) if x is not None]
        net[m] = sum(d)
    return net


def monthly_sd(series: dict[str, float], net: dict[str, float], cut: float) -> float | None:
    ch = [delta(series, m) for m, n in net.items() if abs(n) < cut and not m.endswith(("-12", "-01"))]
    ch = [x for x in ch if x is not None]
    return statistics.pstdev(ch) if len(ch) > 10 else None


def share_sd(st: Store, c: str, net: dict[str, float], cut: float) -> float | None:
    ch = []
    for m, n in net.items():
        if abs(n) >= cut or m.endswith(("-12", "-01")):
            continue
        prev = shift(m, -1)
        among = members(st, [prev, m])
        if c not in among:
            continue
        s1, s0 = shares(st, m, among), shares(st, prev, among)
        if s1 and s0:
            ch.append(s1[c] - s0[c])
    return statistics.pstdev(ch) if len(ch) > 10 else None


def retention_cells(st: Store, net: dict[str, float], k: float, cut: float) -> list[dict]:
    sd = {c: monthly_sd(reserves(st, c), net, cut) for c in COUNTRIES}
    cells = []
    for m in sorted(net):
        for c in COUNTRIES:
            dose = delta(ilm(st, c, "A050200"), m)
            dR, dT = delta(reserves(st, c), m), delta(tgb(st, c), m)
            if None in (dose, dR, dT) or sd[c] is None or abs(dose) < k * sd[c]:
                continue
            cells.append({"regime": regime_of(m), "month": m, "country": c, "dose": r4(dose),
                          "dR": r4(dR), "dT": r4(dT), "sd": r4(sd[c]),
                          "retention": r4(dR / dose), "leak": r4(-dT / dose)})
    return cells


def regime_medians(cells: list[dict]) -> dict[str, dict]:
    out = {}
    for _, text, _ in REGIMES:
        rets = [x["retention"] for x in cells if x["regime"] == text]
        out[text] = {"n": len(rets), "median_retention": r4(statistics.median(rets)) if rets else None}
    return out


SPECIAL, FIRST = REGIMES[2][1], REGIMES[1][1]


def criterion_data(checked: list[tuple[str, list[str]]]) -> dict:
    bad = [(n, p) for n, p in checked if p]
    return {"name": "B112-1", "kind": "instrument", "passed": not bad and bool(checked),
            "statement": "every request is on disk, passes the fetch checks, and has the series"
                         " count its enumeration found",
            "detail": f"{len(checked)} requests, {len(checked) - len(bad)} pass"
                      + ("" if not bad else "; failing: " + "; ".join(f"{n}: {p[0]}" for n, p in bad))}


def state_of(z: float | None, sign: int) -> str:
    """One country's reading of a stated direction: the four states KNOWN_MAPPING maps."""
    if z is None:
        return "no object"
    if abs(z) < NOISE_MULTIPLE:
        return "within noise"
    return "as stated" if z * sign > 0 else "opposite"


def known_rows(st: Store, net: dict[str, float]) -> list[dict]:
    a, b = KNOWN_MONTHS
    among = members(st, [a, b])
    s0, s1 = shares(st, a, among), shares(st, b, among)
    rows = []
    for what, quote, countries, sign in KNOWN:
        for c in countries:
            if what == "reserve share":
                change = (s1[c] - s0[c]) * 100 if c in s0 and c in s1 else None
                sd = share_sd(st, c, net, QUIET_CUT)
                sd = None if sd is None else sd * 100
            else:
                # the paper compares maintenance period averages, so the period average is read
                avg = st.one(f"TGB.M.{c}.N.A094T.U2.EUR.A")
                change = avg[b] - avg[a] if a in avg and b in avg else None
                sd = monthly_sd(avg, net, QUIET_CUT)
            z = None if change is None or not sd else change / (sd * 2 ** 0.5)
            state = state_of(z, sign)
            rows.append({"object": what, "quote": quote, "country": c, "change": r4(change),
                         "sd_two_months": r4(None if sd is None else sd * 2 ** 0.5), "z": r4(z),
                         "state": state})
    return rows


KNOWN_MAPPING = {"as stated": "counts toward PASS", "within noise": "no verdict",
                 "no object": "no verdict", "opposite": "FAIL"}


def criterion_known(rows: list[dict]) -> dict:
    states = [x["state"] for x in rows]
    if "opposite" in states:
        passed = False
    elif all(any(x["state"] == "as stated" for x in rows if x["object"] == what)
             for what, *_ in KNOWN):
        passed = True
    else:
        passed = None
    return {"name": "B112-2", "kind": "known_answer", "passed": passed,
            "statement": "the directions ECB Occasional Paper 302 (p. 15) states for the start of the"
                         " two-tier system read the same way on the balance sheets, Sep to Nov 2019",
            "detail": "; ".join(f"{x['object']} {x['country']} {x['change']:+.2f} (z {x['z']:+.1f})"
                                f" {x['state']}" if x["z"] is not None
                                else f"{x['object']} {x['country']} {x['state']}" for x in rows)}


RETENTION_MAPPING = {"special rate period above first terms at every scan point": "PASS",
                     "special rate period below first terms at every scan point": "FAIL",
                     "mixed, or a regime without a cell at some scan point": "no verdict"}


def retention_scan(st: Store, net: dict[str, float]) -> list[dict]:
    out = []
    for k in SCAN_MULTIPLES:
        for cut in SCAN_CUTS:
            med = regime_medians(retention_cells(st, net, k, cut))
            out.append({"noise_multiple": k, "quiet_cut": cut, "medians": med})
    return out


def criterion_retention(scan: list[dict]) -> dict:
    signs = []
    for point in scan:
        sp, fi = point["medians"][SPECIAL]["median_retention"], point["medians"][FIRST]["median_retention"]
        signs.append(None if sp is None or fi is None else (sp > fi) - (sp < fi))
    if signs and all(s == 1 for s in signs):
        passed, state = True, "special rate period above first terms at every scan point"
    elif signs and all(s == -1 for s in signs):
        passed, state = False, "special rate period below first terms at every scan point"
    else:
        passed, state = None, "mixed, or a regime without a cell at some scan point"
    base = next(p for p in scan if p["noise_multiple"] == NOISE_MULTIPLE and p["quiet_cut"] == QUIET_CUT)
    return {"name": "B112-3", "kind": "own_reading", "passed": passed,
            "statement": "the same-month share of a refinancing dose that stays in the borrowing country"
                         " is higher while holding it pays (TLTRO III special rate period, from"
                         " 2020-06-24) than under the first TLTRO III terms",
            "detail": f"{state}; at {NOISE_MULTIPLE} sd and quiet below {QUIET_CUT:.0f} bn: special"
                      f" {base['medians'][SPECIAL]['median_retention']} over"
                      f" {base['medians'][SPECIAL]['n']} cells, first terms"
                      f" {base['medians'][FIRST]['median_retention']} over"
                      f" {base['medians'][FIRST]['n']} cells"}


def criterion_sources(rules=None, regimes=None) -> dict:
    rules = RULES if rules is None else rules
    regimes = REGIMES if regimes is None else regimes
    unsourced = [m for m, text in rules if not SOURCE_PATTERN.search(text)]
    unsourced += [m for m, _, src in regimes if not SOURCE_PATTERN.search(src)]
    return {"name": "B112-4", "kind": "bookkeeping", "passed": not unsourced,
            "statement": "every rule date and every regime boundary names the dated ECB text it was"
                         " copied from",
            "detail": f"{len(rules) + len(regimes)} dates, "
                      + ("all sourced" if not unsourced else "unsourced: " + ", ".join(unsourced))}


def clock_rows(st: Store) -> list[dict]:
    rows = []
    for y in CLOCK_YEARS:
        for c in COUNTRIES:
            inside, across = pss_values(st, c)
            vi, va = inside.get(y), across.get(y)
            vals = [v for m, v in reserves(st, c).items() if m.startswith(y)]
            source = "reserves"
            if len(vals) < 12:
                vals = [v for m, v in bsi(st, c, "A20", "U6", "1100").items() if m.startswith(y)]
                source = "MFI claims on own NCB"
            avg = statistics.fmean(vals) if len(vals) == 12 else None
            if vi is None and va is None:
                continue
            rows.append({"year": y, "country": c, "inside": r4(vi), "across": r4(va), "avg_reserves": r4(avg),
                         "reserves_source": source,
                         "days_home": None if not (avg and vi) else round(365 * avg / vi, 2),
                         "days_abroad": None if not (avg and va) else round(365 * avg / va, 2)})
    return rows


def build_record(st: Store, checked: list[tuple[str, list[str]]]) -> dict:
    net = net_refinancing(st)
    cells = retention_cells(st, net, NOISE_MULTIPLE, QUIET_CUT)
    scan = retention_scan(st, net)
    known = known_rows(st, net)
    shares_at = {}
    for month, _ in RULES:
        cols = [shift(month, k) for k in (-1, 0, 1, 2, 3)]
        among = members(st, cols)
        shares_at[month] = {m: {c: r4(100 * v) for c, v in shares(st, m, among).items()} for m in cols}
    criteria = [criterion_data(checked), criterion_known(known), criterion_retention(scan),
                criterion_sources()]
    return {
        "stage": "B112",
        "config": {"noise_multiple": NOISE_MULTIPLE, "quiet_cut_bn": QUIET_CUT,
                   "quiet_months_exclude": ["-12", "-01"], "scan_noise_multiples": list(SCAN_MULTIPLES),
                   "scan_quiet_cuts_bn": list(SCAN_CUTS), "clock_years": list(CLOCK_YEARS),
                   "known_answer_months": list(KNOWN_MONTHS), "reserves_item": "L020000",
                   "refinancing_item": "A050200", "target_collection_for_known_answer": "A"},
        "rules": [{"month": m, "text": text} for m, text in RULES],
        "regimes": [{"from": m, "text": text, "source": src} for m, text, src in REGIMES],
        "mapping": {"B112-2": KNOWN_MAPPING, "B112-3": RETENTION_MAPPING},
        "objects": {"retention_cells": cells, "retention_by_regime": regime_medians(cells),
                    "retention_scan": scan, "known_answer_rows": known, "shares_at_rules": shares_at,
                    "clocks": clock_rows(st),
                    "noise_sd_bn": {c: r4(monthly_sd(reserves(st, c), net, QUIET_CUT)) for c in COUNTRIES}},
        "criteria": criteria,
    }


def fetch_checks() -> list[tuple[str, list[str]]]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import b112_fetch as F
    out = []
    for req in F.requests():
        problems, _ = F.verify_pair(req, F.RAW / f"{req['name']}.csv", F.RAW / f"{req['name']}.meta.csv")
        out.append((req["name"], problems))
    return out


def write_record(record: dict, path: Path) -> None:
    path.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def print_criteria(record: dict) -> None:
    print("\n== criteria")
    for name, mapping in record["mapping"].items():
        print(f"  {name} mapping: " + "; ".join(f"{k} -> {v}" for k, v in mapping.items()))
    for c in record["criteria"]:
        verdict = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        print(f"  {c['name']} [{c['kind']}] {verdict}: {c['statement']}\n      {c['detail']}")


# ---------------------------------------------------------------------------
# Self-test: a two-country fixture whose every printed number can be worked by hand
# ---------------------------------------------------------------------------

def _write(root: Path, name: str, rows: list[tuple[str, str, float]], meta: dict[str, tuple]) -> None:
    lines = ["KEY,TIME_PERIOD,OBS_VALUE"] + [f"{k},{t},{v}" for k, t, v in rows]
    (root / f"{name}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    mlines = ["KEY,TITLE,UNIT,UNIT_MULT"] + [f"{k},x,{u},{m}" for k, (u, m) in meta.items()]
    (root / f"{name}.meta.csv").write_text("\n".join(mlines) + "\n", encoding="utf-8")


def cmd_selftest() -> int:
    global COUNTRIES
    saved = COUNTRIES
    ok = True
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # reserves in millions: DE 300 then 330, IT 100 then 70; so shares 75/25 then 82.5/17.5
        rows = [("ILM.M.DE.N.L020000.U2.EUR", "2019-09", 300e3), ("ILM.M.DE.N.L020000.U2.EUR", "2019-10", 330e3),
                ("ILM.M.IT.N.L020000.U2.EUR", "2019-09", 100e3), ("ILM.M.IT.N.L020000.U2.EUR", "2019-10", 70e3)]
        _write(root, "ilm", rows, {"ILM.M.DE.N.L020000.U2.EUR": ("EUR", 6),
                                   "ILM.M.IT.N.L020000.U2.EUR": ("EUR", 6)})
        _write(root, "tgb", [("TGB.M.DE.N.A094T.U2.EUR.E", "2019-09", 800e3),
                             ("TGB.M.DE.N.A094T.U2.EUR.E", "2019-10", 830e3)],
               {"TGB.M.DE.N.A094T.U2.EUR.E": ("EUR", 6)})
        COUNTRIES = ("DE", "IT")
        try:
            st = Store(root)
            s9, s10 = shares(st, "2019-09"), shares(st, "2019-10")
            checks = {
                "units: 300e3 millions is 300 billions": reserves(st, "DE")["2019-09"] == 300.0,
                "shares 75 / 25": abs(s9["DE"] - 0.75) < 1e-12 and abs(s9["IT"] - 0.25) < 1e-12,
                "shares 82.5 / 17.5": abs(s10["DE"] - 0.825) < 1e-12,
                "month-on-month change 30": delta(reserves(st, "DE"), "2019-10") == 30.0,
                "change needs both months": delta(reserves(st, "DE"), "2019-09") is None,
                "TARGET change 30": delta(tgb(st, "DE"), "2019-10") == 30.0,
                "a missing country blanks the shares": shares(st, "2019-08") == {},
                "the denominator keeps only countries present in every month":
                    members(st, ["2019-08", "2019-09"]) == () and members(st, ["2019-09", "2019-10"]) == ("DE", "IT"),
                "month arithmetic across a year": shift("2019-11", 3) == "2020-02"
                and shift("2020-01", -1) == "2019-12" and months("2019-11", "2020-02")
                == ["2019-11", "2019-12", "2020-01", "2020-02"],
            }
        finally:
            COUNTRIES = saved
    # each criterion is fed an input that must make it fail, or fall to no verdict (11f)
    good_scan = [{"noise_multiple": 3, "quiet_cut": 20.0,
                  "medians": {SPECIAL: {"n": 5, "median_retention": 1.0},
                              FIRST: {"n": 3, "median_retention": 0.4}}}]
    swapped = [{"noise_multiple": 3, "quiet_cut": 20.0,
                "medians": {SPECIAL: {"n": 5, "median_retention": 0.4},
                            FIRST: {"n": 3, "median_retention": 1.0}}}]
    mixed = good_scan + [{"noise_multiple": 2, "quiet_cut": 20.0,
                          "medians": {SPECIAL: {"n": 5, "median_retention": 1.0},
                                      FIRST: {"n": 0, "median_retention": None}}}]
    row = {"object": "reserve share", "quote": "q", "country": "IT", "change": 2.0, "sd_two_months": 0.5,
           "z": 4.0, "state": "as stated"}
    row_t = dict(row, object="TARGET balance", country="DE", change=-40.0, z=-4.0)
    checks.update({
        "B112-1 fails when one request has a problem":
            criterion_data([("a", []), ("b", ["cut mid-row"])])["passed"] is False,
        "B112-1 fails on an empty request list": criterion_data([])["passed"] is False,
        "B112-2 passes with one as-stated row per statement": criterion_known([row, row_t])["passed"] is True,
        "B112-2 fails on an opposite row": criterion_known([row, dict(row_t, state="opposite")])["passed"] is False,
        "B112-2 gives no verdict when a statement is all noise":
            criterion_known([row, dict(row_t, state="within noise")])["passed"] is None,
        "B112-3 passes on the good scan": criterion_retention(good_scan)["passed"] is True,
        "B112-3 fails when the regimes swap": criterion_retention(swapped)["passed"] is False,
        "B112-3 gives no verdict when a scan point has no cell": criterion_retention(mixed)["passed"] is None,
        "B112-4 fails on a rule without a source":
            criterion_sources(rules=RULES + (("2030-01", "a rule with no source"),))["passed"] is False,
        "B112-4 passes on the table as written": criterion_sources()["passed"] is True,
        "a stated rise read at +4 sd is as stated": state_of(4.0, +1) == "as stated",
        "a stated fall read at +4 sd is opposite": state_of(4.0, -1) == "opposite",
        "a reading under the noise multiple is within noise": state_of(-1.0, -1) == "within noise",
        "no reading is no object": state_of(None, +1) == "no object",
    })
    # the known-answer path end to end: quiet noise for two years, then a jump that must read
    # as stated for a stated rise, and as opposite once the stated direction is reversed
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        span = months("2017-10", "2019-11")
        ilm_rows, tgb_rows = [], []
        for i, m in enumerate(span):
            wiggle = 1e3 if i % 2 else -1e3
            it = {"2019-10": 150e3, "2019-11": 160e3}.get(m, 100e3 + wiggle / 2)
            tg = {"2019-10": 450e3, "2019-11": 400e3}.get(m, 500e3 + wiggle)
            ilm_rows += [("ILM.M.DE.N.L020000.U2.EUR", m, 1000e3 + wiggle), ("ILM.M.IT.N.L020000.U2.EUR", m, it),
                         ("ILM.M.DE.N.A050200.U2.EUR", m, 10e3), ("ILM.M.IT.N.A050200.U2.EUR", m, 10e3)]
            tgb_rows.append(("TGB.M.DE.N.A094T.U2.EUR.A", m, tg))
        units = ("EUR", 6)
        _write(root, "ilm", ilm_rows, {k: units for k, _, _ in ilm_rows})
        _write(root, "tgb", tgb_rows, {"TGB.M.DE.N.A094T.U2.EUR.A": units})
        COUNTRIES = ("DE", "IT")
        try:
            st = Store(root)
            rows = {(x["object"], x["country"]): x for x in known_rows(st, net_refinancing(st))}
            it_row, de_row = rows[("reserve share", "IT")], rows[("TARGET balance", "DE")]
            checks["known answer: a jump in the Italian share reads as stated"] = it_row["state"] == "as stated"
            checks["known answer: a fall in the German TARGET average reads as stated"] = de_row["state"] == "as stated"
            checks["known answer: the absent countries read as no object"] = rows[("reserve share", "GR")]["state"] == "no object"
        finally:
            COUNTRIES = saved
    for name, good in checks.items():
        ok &= good
        print(f"  {'ok' if good else 'WRONG'}  {name}")
    print(f"\nselftest: {sum(checks.values())} of {len(checks)}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--block", type=int, choices=sorted(BLOCKS))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--write", action="store_true", help="criteria and results/b112_object.json")
    ap.add_argument("--raw", default=str(RAW))
    a = ap.parse_args()
    if a.selftest:
        return cmd_selftest()
    root = Path(a.raw)
    if not any(root.glob("*.meta.csv")):
        print(f"nothing under {root}; run experiments/b112_fetch.py --fetch first")
        return 1
    st = Store(root)
    if a.write:
        record = build_record(st, fetch_checks())
        print_criteria(record)
        write_record(record, RECORD)
        print(f"\nwrote {RECORD}")
        return 0 if all(c["passed"] is not False for c in record["criteria"]) else 1
    for k, fn in BLOCKS.items():
        if a.block is None or a.block == k:
            fn(st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
