"""B155. Two capital prices for one corporate bond, written on one rating axis by two legislators.

A bank under the Capital Requirements Regulation (Article 122, standardised approach, banking
book) and an insurer under the Solvency II standard formula (Delegated Regulation 2015/35,
Article 176, spread risk on bonds and loans) each hold the same corporate bond. Both charges are
keyed to the same external rating, through two mapping standards (Implementing Regulations
2016/1799 and 2016/1800). The bank's charge per euro is 8% x risk weight; it does not depend on
the bond's duration. The insurer's charge per euro is a stress factor that is piecewise linear in
modified duration, with a separate column per credit quality step.

Positions are (letter grade, modified duration). Classes are the two licences. The object read
here is the log square

    ln [ (s(g1, d1) / RW(g1)) / (s(g2, d2) / RW(g2)) ]  over two classes and two positions,

decided exactly in rationals. The constant multipliers (8% on the bank side, the market value on
the insurer side) cancel. A square is zero exactly when the two ratios are equal.

Three families are printed:
    GP   grade pair at one duration point
    GPD  grade pair x duration pair (the GP square at d1 minus the GP square at d2)
    CD   one grade, two durations (class x duration pair)

Floor: each printed input of a square is moved one tick of its own printed format (risk weights
1 percentage point, stress coefficients a and b 0.1 percentage point; the one cell printed as
"11 %" is also read with a 1 point tick), and the floor is the largest change in the log that one
tick produces. A square stands above the floor when its log is larger than that, compared
exactly. Equal is "on the floor" and is not counted.

Four versions of the two tables enter:
    bank  2013 text (Table 6)                         applied until 31 December 2024
    bank  Regulation 2024/1623 point (51) (Table 1)   applies from 1 January 2025
    ins   2015/35 as published in OJ L 12, 2015
    ins   as corrected by 2016/467 (paragraphs 3, 4)  in force from 2 April 2016
    ins   as amended by 2026/269 (paragraph 1 only)   applies from 30 January 2027

Every number is transcribed below as a constant and checked against the page text stored in
data/raw/b155/b155_text_snapshot.json.

Run:
    python experiments/b155_capital_square.py
    python experiments/b155_capital_square.py --selftest
"""

import argparse
import copy
import difflib
import functools
import json
import math
import pathlib
import re
import sys
import time
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO.parent))

from b122_b125_tick_floor import floor_of  # noqa: E402

SESSION = "T15_EUCAP"
SNAP = REPO / "data" / "raw" / "b155" / "b155_text_snapshot.json"
OUT = REPO / "results" / "b155_capital_square.json"

GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
UNR = "unrated"
POSITIONS = GRADES + [UNR]
DURATIONS = [F(1), F(15, 2), F(10), F(25, 2), F(15), F(35, 2), F(20), F(25), F(30)]
SHORT = [F(1, 2), F(1), F(2), F(3), F(4), F(5)]
MULTIPLIERS = [F(8), F(21, 2), F(13)]
TICK_RW = F(1)
TICK_AB = F(1, 10)
TICK_ALT = F(1)

# ------------------------------------------------------------------ position axis
# Credit quality step by letter grade, as the two mapping standards print it for
# Fitch, Moody's and S&P (letter categories; modifiers inherit the letter).
BANK_STEP = {"AAA": 1, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5, "CCC": 6}
INS_STEP = {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5, "CCC": 6}
# Article 176(3) prints one column for steps 5 and 6.
INS_COLUMN = {0: "0", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5&6", 6: "5&6"}
INS_COLS = ["0", "1", "2", "3", "4", "5&6"]
MOODYS = {"Aaa": "AAA", "Aa": "AA", "A": "A", "Baa": "BBB", "Ba": "BB", "B": "B", "Caa": "CCC", "Ca": "CCC",
          "C": "CCC"}
BELOW_CCC = {"CCC", "CC", "C", "R", "SD/D", "RD", "D"}

# ------------------------------------------------------------------ transcribed tables (percent)
BANK = {
    "crr_2013": {
        "rw": {1: F(20), 2: F(50), 3: F(100), 4: F(100), 5: F(150), 6: F(150)},
        "unrated": F(100),
        "unrated_rule": "100 % or the risk weight of the central government of incorporation, whichever is higher; "
                        "read on the branch where that sovereign weight is at most 100 %",
        "src": ["crr_122_2013_oj", "crr_122_consol_20240709"],
        "applies": "until 2024-12-31"},
    "crr3": {
        "rw": {1: F(20), 2: F(50), 3: F(75), 4: F(100), 5: F(150), 6: F(150)},
        "unrated": F(100),
        "unrated_rule": "100 %",
        "src": ["crr3_point51", "crr3_application"],
        "applies": "from 2025-01-01"},
}

# Rated table: column -> five segments (a, b); segment 0 has no a.
# Segments: up to 5 | more than 5 up to 10 | 10-15 | 15-20 | more than 20 (capped at 100 %).
SEG_RATED = [(F(5), F(0)), (F(10), F(5)), (F(15), F(10)), (F(20), F(15)), (None, F(20))]
SEG_UNR = [(F(5), F(0)), (F(10), F(5)), (F(20), F(10)), (None, F(20))]


def _p(s):
    return F(s.replace(",", "."))


RATED_2016 = {
    "0": [(None, _p("0,9")), (_p("4,5"), _p("0,5")), (_p("7,0"), _p("0,5")), (_p("9,5"), _p("0,5")),
          (_p("12,0"), _p("0,5"))],
    "1": [(None, _p("1,1")), (_p("5,5"), _p("0,6")), (_p("8,5"), _p("0,5")), (_p("11"), _p("0,5")),
          (_p("13,5"), _p("0,5"))],
    "2": [(None, _p("1,4")), (_p("7,0"), _p("0,7")), (_p("10,5"), _p("0,5")), (_p("13,0"), _p("0,5")),
          (_p("15,5"), _p("0,5"))],
    "3": [(None, _p("2,5")), (_p("12,5"), _p("1,5")), (_p("20,0"), _p("1,0")), (_p("25,0"), _p("1,0")),
          (_p("30,0"), _p("0,5"))],
    "4": [(None, _p("4,5")), (_p("22,5"), _p("2,5")), (_p("35,0"), _p("1,8")), (_p("44,0"), _p("0,5")),
          (_p("46,6"), _p("0,5"))],
    "5&6": [(None, _p("7,5")), (_p("37,5"), _p("4,2")), (_p("58,5"), _p("0,5")), (_p("61,0"), _p("0,5")),
            (_p("63,5"), _p("0,5"))],
}
RATED_2015 = copy.deepcopy(RATED_2016)
RATED_2015["1"][2] = (_p("8,4"), _p("0,5"))
RATED_2015["1"][3] = (_p("10,9"), _p("0,5"))
RATED_2015["1"][4] = (_p("13,4"), _p("0,5"))
RATED_2015["4"][4] = (_p("46,5"), _p("0,5"))
UNRATED_2016 = [(None, _p("3")), (_p("15"), _p("1,7")), (_p("23,5"), _p("1,2")), (_p("35,5"), _p("0,5"))]

INS = {
    "sii_2015": {"rated": RATED_2015, "unrated": None, "src": ["sii_176_2015_oj"],
                 "unrated_missing": "paragraph 4 of the 2015 Official Journal text is not in the stored page text",
                 "applies": "text of OJ L 12, 17.1.2015, until 2016-04-01"},
    "sii_2016": {"rated": RATED_2016, "unrated": UNRATED_2016,
                 "src": ["sii_176_2016_467", "sii_176_consol_20241114"],
                 "applies": "from 2016-04-02 (2016/467, Article 3)"},
    "sii_2027": {"rated": copy.deepcopy(RATED_2016), "unrated": copy.deepcopy(UNRATED_2016),
                 "src": ["sii_2026_269_point53", "sii_amendments_list", "sii_176_consol_20241114"],
                 "applies": "from 2027-01-30 (2026/269, Article 2)"},
}
ALT_CELL = ("sii_2016", "1", 3, "a")   # the cell printed "11 %"

COMBOS = {
    "pre_2016": ("crr_2013", "sii_2015"),
    "pre_crr3": ("crr_2013", "sii_2016"),
    "current": ("crr3", "sii_2016"),
    "post_2027": ("crr3", "sii_2027"),
}

RIVAL = {
    "rival_premise": "the capital price of a bond per euro is a scalar on the position (letter grade x modified "
                     "duration); the holder's licence carries only a constant multiple (different confidence "
                     "levels and horizons, the bank's buffers)",
    "rival_entailment": "ln P(class, position) = c(class) + phi(position), so every log square is zero",
    "rival_shape": "point prediction (exactly zero)",
}

# Registered in the design before the script was written (exact hand computation on the quoted text).
REGISTERED_BB_B_ROOT = F(140, 11)
REGISTERED_BB_B_BANK_RATIO = F(2, 3)
BB_B_SEGMENT = (F(10), F(15))

MAPPING_11C = [
    {"state": "above_floor", "called": "non-zero and larger than one tick", "maps_to": "counted", "verdict": "read"},
    {"state": "on_floor", "called": "non-zero, not larger than one tick", "maps_to": "printed, not counted",
     "verdict": None},
    {"state": "zero", "called": "exactly zero", "maps_to": "structural-zero families", "verdict": None},
]


# ------------------------------------------------------------------ model
class Model:
    """Values of every printed input, keyed by a string; prices read off them."""

    def __init__(self, bank=None, ins=None, bank_step=None, ins_step=None, ins_col=None,
                 bank_dur=None, short_offset=F(0), notch_letter_fn=None):
        self.bank = bank if bank is not None else BANK
        self.notch_letter_fn = notch_letter_fn
        self.ins = ins if ins is not None else INS
        self.bank_step = bank_step or BANK_STEP
        self.ins_step = ins_step or INS_STEP
        self.ins_col = ins_col or INS_COLUMN
        self.bank_dur = bank_dur
        self.short_offset = short_offset
        self.vals = {}
        for bv, t in self.bank.items():
            for st, v in t["rw"].items():
                self.vals["bank|%s|%d" % (bv, st)] = v
            self.vals["bank|%s|U" % bv] = t["unrated"]
        for iv, t in self.ins.items():
            for col, segs in t["rated"].items():
                for i, (a, b) in enumerate(segs):
                    if a is not None:
                        self.vals["ins|%s|%s|%d|a" % (iv, col, i)] = a
                    self.vals["ins|%s|%s|%d|b" % (iv, col, i)] = b
            if t["unrated"] is not None:
                for i, (a, b) in enumerate(t["unrated"]):
                    if a is not None:
                        self.vals["ins|%s|U|%d|a" % (iv, i)] = a
                    self.vals["ins|%s|U|%d|b" % (iv, i)] = b

    # ---- keys
    def bank_key(self, bv, pos):
        if pos == UNR:
            return "bank|%s|U" % bv
        return "bank|%s|%d" % (bv, self.bank_step[pos])

    def ins_col_of(self, pos):
        return "U" if pos == UNR else self.ins_col[self.ins_step[pos]]

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def seg_of(col, dur):
        segs = SEG_UNR if col == "U" else SEG_RATED
        d = max(dur, F(1))
        for i, (up, _start) in enumerate(segs):
            if up is None or d <= up:
                return i
        raise ValueError

    def ins_keys(self, iv, pos, dur):
        col = self.ins_col_of(pos)
        i = self.seg_of(col, dur)
        ks = ["ins|%s|%s|%d|b" % (iv, col, i)]
        if i > 0:
            ks.append("ins|%s|%s|%d|a" % (iv, col, i))
        return ks

    def has(self, iv, pos):
        return not (pos == UNR and self.ins[iv]["unrated"] is None)

    # ---- prices
    def rw(self, vals, bv, pos, dur):
        v = vals[self.bank_key(bv, pos)]
        if self.bank_dur is not None:
            v = v + self.bank_dur(pos, dur)
        return v

    def stress(self, vals, iv, pos, dur):
        col = self.ins_col_of(pos)
        segs = SEG_UNR if col == "U" else SEG_RATED
        d = max(dur, F(1))
        i = self.seg_of(col, dur)
        up, start = segs[i]
        b = vals["ins|%s|%s|%d|b" % (iv, col, i)]
        a = vals["ins|%s|%s|%d|a" % (iv, col, i)] if i > 0 else F(0)
        x = a + b * (d - start)
        if i == 0:
            x = x + self.short_offset
        if up is None:
            x = min(x, F(100))
        return x

    def w(self, vals, combo, pos, dur):
        bv, iv = COMBOS[combo]
        return self.stress(vals, iv, pos, dur) / self.rw(vals, bv, pos, dur)


class Overlay:
    """Read-only view of the base values with a few inputs moved."""

    __slots__ = ("base", "moved")

    def __init__(self, base, moved):
        self.base = base
        self.moved = moved

    def __getitem__(self, k):
        m = self.moved
        return m[k] if k in m else self.base[k]


def u(x):
    return x if x >= 1 else 1 / x


def ticks_for(keys, alt=False):
    out = {}
    for k in keys:
        if k.startswith("bank"):
            out[k] = TICK_RW
        else:
            out[k] = TICK_AB
        parts = k.split("|")
        if alt and len(parts) == 5 and (parts[1], parts[2], int(parts[3]), parts[4]) == ALT_CELL:
            out[k] = TICK_ALT
    return out


def judge(m, ratio_fn, keys, tick_override=None, alt=False):
    """Exact state of a square plus its floor; ratio_fn(vals) -> Fraction."""
    base = m.vals
    r = ratio_fn(base)
    ticks = ticks_for(keys, alt)
    if tick_override is not None:
        ticks = {k: tick_override for k in ticks}
    sub = {k: base[k] for k in keys}

    def vf(d):
        return ratio_fn(Overlay(base, d))

    lg, fl_float = floor_of(vf, sub, ticks)
    fu = F(1)
    for k, t in ticks.items():
        for sgn in (1, -1):
            try:
                q = ratio_fn(Overlay(base, {k: base[k] + sgn * t}))
            except ZeroDivisionError:
                continue
            if q > 0:
                fu = max(fu, u(q / r))
    assert abs(math.log(fu) - fl_float) < 1e-12, (keys, fl_float, fu)
    if r == 1:
        state = "zero"
    elif u(r) > fu:
        state = "above_floor"
    else:
        state = "on_floor"
    mult = (math.log(u(r)) / math.log(fu)) if fu > 1 else (math.inf if r != 1 else 0.0)
    return {"ratio": r, "log": lg, "floor": fl_float, "floor_u": fu, "multiple": mult, "state": state}


def pairs(seq):
    return [(seq[i], seq[j]) for i in range(len(seq)) for j in range(i + 1, len(seq))]


def gp_square(m, combo, g1, g2, d, alt=False, tick_override=None):
    bv, iv = COMBOS[combo]
    keys = sorted(set([m.bank_key(bv, g1), m.bank_key(bv, g2)] + m.ins_keys(iv, g1, d) + m.ins_keys(iv, g2, d)))
    return judge(m, lambda v: m.w(v, combo, g1, d) / m.w(v, combo, g2, d), keys, tick_override, alt)


def gpd_square(m, combo, g1, g2, d1, d2, alt=False):
    bv, iv = COMBOS[combo]
    keys = sorted(set([m.bank_key(bv, g1), m.bank_key(bv, g2)] + m.ins_keys(iv, g1, d1) + m.ins_keys(iv, g2, d1)
                      + m.ins_keys(iv, g1, d2) + m.ins_keys(iv, g2, d2)))
    return judge(m, lambda v: (m.w(v, combo, g1, d1) * m.w(v, combo, g2, d2))
                 / (m.w(v, combo, g2, d1) * m.w(v, combo, g1, d2)), keys, None, alt)


def cd_square(m, combo, g, d1, d2, alt=False):
    bv, iv = COMBOS[combo]
    keys = sorted(set([m.bank_key(bv, g)] + m.ins_keys(iv, g, d1) + m.ins_keys(iv, g, d2)))
    return judge(m, lambda v: m.w(v, combo, g, d1) / m.w(v, combo, g, d2), keys, None, alt)


def positions_for(m, combo):
    _bv, iv = COMBOS[combo]
    return [p for p in POSITIONS if m.has(iv, p)]


def families(m, combo, durations=None, alt=False, tick_override=None):
    durations = DURATIONS if durations is None else durations
    pos = positions_for(m, combo)
    gp, gpd, cd = [], [], []
    for g1, g2 in pairs(pos):
        for d in durations:
            gp.append(dict(g1=g1, g2=g2, d=d, **gp_square(m, combo, g1, g2, d, alt, tick_override)))
        for d1, d2 in pairs(durations):
            gpd.append(dict(g1=g1, g2=g2, d1=d1, d2=d2, **gpd_square(m, combo, g1, g2, d1, d2, alt)))
    for g in pos:
        for d1, d2 in pairs(durations):
            cd.append(dict(g=g, d1=d1, d2=d2, **cd_square(m, combo, g, d1, d2, alt)))
    return {"GP": gp, "GPD": gpd, "CD": cd}


def adjacent(row):
    if UNR in (row["g1"], row["g2"]):
        return False
    return GRADES.index(row["g2"]) - GRADES.index(row["g1"]) == 1


def counts(rows):
    c = {"above_floor": 0, "on_floor": 0, "zero": 0}
    for r in rows:
        c[r["state"]] += 1
    c["total"] = len(rows)
    return c


# ------------------------------------------------------------------ snapshot parsing
def load_snapshot(path=SNAP):
    d = json.loads(path.read_text(encoding="utf-8"))
    return {e["id"]: e for e in d["entries"]}


ROW_RATED = re.compile(r"More than 5 and up to 10|More than 10 and up to 15|More than 15 and up to 20|"
                       r"More than 20|up to 5(?!\d)")
ROW_UNR = re.compile(r"More than 5 and up to 10|More than 10 and up to 20|More than 20|up to 5(?!\d)")
TOK = re.compile(r"—|\d+(?:,\d+)?\s?%")
ORDER_RATED = ["up to 5", "More than 5 and up to 10", "More than 10 and up to 15", "More than 15 and up to 20",
               "More than 20"]
ORDER_UNR = ["up to 5", "More than 5 and up to 10", "More than 10 and up to 20", "More than 20"]


def _num(tok):
    return None if tok == "—" else _p(tok.replace("%", "").strip())


def parse_rated(text):
    ms = list(ROW_RATED.finditer(text))
    rows = {}
    for i, mm in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        toks = [_num(t) for t in TOK.findall(text[mm.end():end])][:12]
        rows[mm.group(0)] = toks
    out = {}
    for ci, col in enumerate(INS_COLS):
        segs = []
        for si, lab in enumerate(ORDER_RATED):
            toks = rows.get(lab, [])
            a = toks[2 * ci] if len(toks) > 2 * ci else "missing"
            b = toks[2 * ci + 1] if len(toks) > 2 * ci + 1 else "missing"
            segs.append((a, b))
        out[col] = segs
    return out


def parse_unrated(text):
    ms = list(ROW_UNR.finditer(text))
    rows = {}
    for i, mm in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        rows[mm.group(0)] = [_num(t) for t in re.findall(r"\d+(?:,\d+)?\s?%", text[mm.end():end])]
    segs = []
    for lab in ORDER_UNR:
        toks = rows.get(lab, [])
        if lab == "up to 5":
            segs.append((None, toks[0] if toks else "missing"))
        else:
            segs.append((toks[0] if toks else "missing", toks[1] if len(toks) > 1 else "missing"))
    return segs


def parse_bank(text):
    seg = text.split("Risk weight", 1)[1]
    rws = [_num(t) for t in re.findall(r"\d+ %", seg)[:6]]
    return {i + 1: v for i, v in enumerate(rws)}


def sources_of_rated(snap):
    t15 = snap["sii_176_2015_oj"]["text"]
    t15 = t15[t15.index("3. ..."):]
    t16 = snap["sii_176_2016_467"]["text"]
    t16_rated, t16_unr = t16.split("(b) paragraph 4", 1)
    return {
        "sii_2015": [("sii_176_2015_oj", parse_rated(t15))],
        "sii_2016": [("sii_176_2016_467", parse_rated(t16_rated)),
                     ("sii_176_consol_20241114", parse_rated(snap["sii_176_consol_20241114"]["text"]))],
    }, {"sii_2016": [("sii_176_2016_467", parse_unrated(t16_unr))]}


def check_transcription(snap, bank=None, ins=None):
    bank = bank or BANK
    ins = ins or INS
    rows, bad = [], []
    for bv, t in bank.items():
        for sid in t["src"]:
            if "Risk weight" not in snap[sid]["text"]:
                continue
            parsed = parse_bank(snap[sid]["text"])
            for st in range(1, 7):
                ok = parsed.get(st) == t["rw"][st]
                rows.append({"table": "bank " + bv, "cell": "CQS%d" % st, "constant": str(t["rw"][st]),
                             "quoted": str(parsed.get(st)), "source": sid, "match": ok})
                if not ok:
                    bad.append(rows[-1])
        txt = " ".join(snap[s]["text"] for s in t["src"])
        unr_ok = ("risk weight of 100 %" in txt) if bv == "crr3" else ("100 % risk weight or the risk weight" in txt)
        rows.append({"table": "bank " + bv, "cell": "unrated", "constant": str(t["unrated"]), "quoted": unr_ok,
                     "source": (t["src"] or ["none"])[0], "match": unr_ok})
        if not unr_ok:
            bad.append(rows[-1])
    rated_src, unr_src = sources_of_rated(snap)
    for iv, srcs in rated_src.items():
        for sid, parsed in srcs:
            for col in INS_COLS:
                for i in range(5):
                    for k, idx in (("a", 0), ("b", 1)):
                        cv = ins[iv]["rated"][col][i][idx]
                        qv = parsed[col][i][idx]
                        if cv is None and qv is None:
                            continue
                        ok = cv == qv
                        rows.append({"table": "ins " + iv, "cell": "CQS%s seg%d %s" % (col, i, k),
                                     "constant": str(cv), "quoted": str(qv), "source": sid, "match": ok})
                        if not ok:
                            bad.append(rows[-1])
    for iv, srcs in unr_src.items():
        if ins[iv]["unrated"] is None:
            rows.append({"table": "ins " + iv, "cell": "unrated", "constant": "None", "quoted": "printed",
                         "source": srcs[0][0], "match": False})
            bad.append(rows[-1])
            continue
        for sid, parsed in srcs:
            for i in range(4):
                for k, idx in (("a", 0), ("b", 1)):
                    cv = ins[iv]["unrated"][i][idx]
                    qv = parsed[i][idx]
                    if cv is None and qv is None:
                        continue
                    ok = cv == qv
                    rows.append({"table": "ins " + iv, "cell": "unrated seg%d %s" % (i, k), "constant": str(cv),
                                 "quoted": str(qv), "source": sid, "match": ok})
                    if not ok:
                        bad.append(rows[-1])
    return rows, bad


def breakpoints(table):
    out = []
    for col, segs in table["rated"].items():
        for i in range(1, 5):
            up, start = SEG_RATED[i - 1]
            a_prev, b_prev = segs[i - 1]
            end_prev = (a_prev or F(0)) + b_prev * (up - start)
            if end_prev != segs[i][0]:
                out.append({"column": col, "at": str(up), "end_of_lower": str(end_prev), "start_of_upper": str(segs[i][0])})
    if table["unrated"] is not None:
        segs = table["unrated"]
        for i in range(1, 4):
            up, start = SEG_UNR[i - 1]
            a_prev, b_prev = segs[i - 1]
            end_prev = (a_prev or F(0)) + b_prev * (up - start)
            if end_prev != segs[i][0]:
                out.append({"column": "U", "at": str(up), "end_of_lower": str(end_prev),
                            "start_of_upper": str(segs[i][0])})
    return out


EXPECTED_BREAKS = {
    "sii_2015": [("1", "10")],
    "sii_2016": [("4", "20")],
}


def parse_mapping(text, n_steps, first_step):
    """Return {(agency, scale): {letter: step}} for Fitch, Moody's, S&P."""
    out = {}
    for row in text.split("||"):
        cells = [c.strip() for c in row.split(" | ")]
        agency = None
        for c in cells:
            if c.startswith("Fitch"):
                agency = "Fitch"
            elif c.startswith("Moody"):
                agency = "Moody's"
            elif c.startswith("S&P"):
                agency = "S&P"
            elif c.startswith("A.M. Best"):
                agency = "A.M. Best"
        if agency is None:
            continue
        for j, c in enumerate(cells):
            if "scale" in c:
                steps = cells[j + 1:j + 1 + n_steps]
                mp = {}
                for k, cell in enumerate(steps):
                    for lab in [x.strip() for x in cell.split(",")]:
                        mp[lab] = first_step + k
                out[(agency, c.replace(agency, "").strip() or c)] = mp
    return out


def letter_of(agency, lab):
    if agency == "Moody's":
        return MOODYS.get(lab)
    if lab in BELOW_CCC:
        return "CCC"
    return lab if lab in GRADES else None


def check_mapping(snap, bank_step=None, ins_step=None):
    bank_step = bank_step or BANK_STEP
    ins_step = ins_step or INS_STEP
    res = {"bank": parse_mapping(snap["its_2016_1799_consol_20240725"]["text"], 6, 1),
           "ins": parse_mapping(snap["its_2016_1800_consol_20240722"]["text"], 7, 0)}
    rows, bad = [], []
    for side, mp, want in (("bank", res["bank"], bank_step), ("ins", res["ins"], ins_step)):
        for (agency, scale), m in sorted(mp.items()):
            if agency == "A.M. Best":
                continue
            per_letter = {}
            for lab, st in m.items():
                L = letter_of(agency, lab)
                if L is None:
                    continue
                per_letter.setdefault(L, set()).add(st)
            for L in GRADES:
                got = per_letter.get(L, set())
                ok = got == {want[L]}
                rows.append({"side": side, "agency": agency, "scale": scale, "letter": L,
                             "steps": sorted(got), "expected": want[L], "match": ok})
                if not ok:
                    bad.append(rows[-1])
    col56 = "5 and 6" in snap["sii_176_2016_467"]["text"]
    best = {}
    for side in ("bank", "ins"):
        for (agency, scale), m in res[side].items():
            if agency == "A.M. Best":
                best[side] = m
    oddity = {"aa+ in bank table": "aa+" in best.get("bank", {}), "aa+ in insurer table": "aa+" in best.get("ins", {})}
    return rows, bad, col56, best, oddity


NOTCHES = ["AAA"] + [L + s for L in ("AA", "A", "BBB", "BB", "B") for s in ("+", "", "-")] + \
          ["CCC+", "CCC", "CCC-", "CC", "C"]


def notch_letter(n):
    if n in ("CC", "C") or n.startswith("CCC"):
        return "CCC"
    return n.rstrip("+-")


def notch_family(m, combo, letter_fn=notch_letter, durations=None):
    """Squares between two notches of one letter class, positions resolved through the letter mapping."""
    durations = DURATIONS if durations is None else durations
    out = []
    for n1, n2 in pairs(NOTCHES):
        if notch_letter(n1) != notch_letter(n2):
            continue
        for d in durations:
            r = m.w(m.vals, combo, letter_fn(n1), d) / m.w(m.vals, combo, letter_fn(n2), d)
            out.append({"n1": n1, "n2": n2, "d": d, "ratio": r})
    return out


# ------------------------------------------------------------------ readings
def gp_index(rows):
    return {(r["g1"], r["g2"], r["d"]): r for r in rows}


def crr3_step(m):
    before = gp_index(families(m, "pre_crr3")["GP"])
    after = gp_index(families(m, "current")["GP"])
    moved, flips = [], []
    for k, b in sorted(before.items(), key=lambda kv: (POSITIONS.index(kv[0][0]), POSITIONS.index(kv[0][1]), kv[0][2])):
        a = after[k]
        if a["ratio"] != b["ratio"]:
            moved.append(k)
    for d in DURATIONS:
        b, a = before[("A", "BBB", d)], after[("A", "BBB", d)]
        readable = b["state"] == "above_floor" and a["state"] == "above_floor"
        flips.append({"d": d, "before": b, "after": a, "readable": readable,
                      "flipped": readable and ((b["ratio"] > 1) != (a["ratio"] > 1))})
    return before, after, moved, flips


def bb_b_roots(m, combo):
    """Exact roots of the BB/B log square in duration on [1, 30], segment by segment, plus jump crossings."""
    bv, iv = COMBOS[combo]
    c = m.rw(m.vals, bv, "BB", F(1)) / m.rw(m.vals, bv, "B", F(1))
    col1, col2 = m.ins_col_of("BB"), m.ins_col_of("B")
    roots = []
    for i, (up, start) in enumerate(SEG_RATED):
        lo = F(1) if i == 0 else SEG_RATED[i - 1][0]
        hi = F(30) if up is None else up
        a1, b1 = m.ins[iv]["rated"][col1][i]
        a2, b2 = m.ins[iv]["rated"][col2][i]
        a1, a2 = a1 or F(0), a2 or F(0)
        # a1 + b1 (d - start) = c (a2 + b2 (d - start))
        den = b1 - c * b2
        num = c * a2 - a1
        if den == 0:
            if num == 0:
                roots.append(("whole segment", lo, hi))
            continue
        t = num / den
        d = start + t
        if lo < d <= hi or (i == 0 and d == lo):
            roots.append(("root", d))
    return c, roots


def level_signs(m, combo):
    bv, iv = COMBOS[combo]
    out = []
    for g1, g2 in pairs(positions_for(m, combo)):
        for d in DURATIONS:
            s1, s2 = m.stress(m.vals, iv, g1, d), m.stress(m.vals, iv, g2, d)
            r1, r2 = m.rw(m.vals, bv, g1, d), m.rw(m.vals, bv, g2, d)
            signs = []
            for k in MULTIPLIERS:
                lv = (s1 - k * r1 / 100) - (s2 - k * r2 / 100)
                signs.append(0 if lv == 0 else (1 if lv > 0 else -1))
            out.append({"g1": g1, "g2": g2, "d": d, "signs": signs, "stable": len(set(signs)) == 1})
    return out


def d22(m, combo):
    pos = positions_for(m, combo)
    ws = {}
    for p in pos:
        for d in DURATIONS:
            ws.setdefault(m.w(m.vals, combo, p, d), []).append((p, d))
    merged = [v for v in ws.values() if len(v) > 1]
    n = len(pos) * len(DURATIONS)
    return {"positions": n, "independent_squares": n - 1, "distinct_ratios": len(ws),
            "independent_after_exact_merges": len(ws) - 1,
            "merged": [[(p, str(d)) for p, d in v] for v in merged]}


def step_2016(m):
    """Change of every square across the 2016/467 correction against the square's own floor (after side)."""
    fb = families(m, "pre_2016")
    fa = families(m, "pre_crr3")
    out = {}
    for fam in ("GP", "GPD", "CD"):
        keyf = (lambda r: (r["g1"], r["g2"], r["d"])) if fam == "GP" else \
               (lambda r: (r["g1"], r["g2"], r["d1"], r["d2"])) if fam == "GPD" else \
               (lambda r: (r["g"], r["d1"], r["d2"]))
        ib = {keyf(r): r for r in fb[fam]}
        rows = []
        for r in fa[fam]:
            k = keyf(r)
            if k not in ib:
                continue
            ch = r["ratio"] / ib[k]["ratio"]
            rows.append({"key": k, "changed": ch != 1, "change_u": ch, "floor_u": r["floor_u"],
                         "within": u(ch) <= r["floor_u"],
                         "change_log": abs(math.log(u(ch))), "floor": r["floor"]})
        out[fam] = rows
    return out


def para1_diff(snap):
    old = snap["sii_176_2015_oj"]["text"]
    old = old[old.index("1. The capital"):old.index("| 2.")].strip()
    new = snap["sii_2026_269_point53"]["text"]
    new = new[new.index("'1. The capital") + 1:].rstrip("'").strip()
    sm = difflib.SequenceMatcher(None, old.split(), new.split())
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            ops.append({"op": tag, "old": " ".join(old.split()[i1:i2]), "new": " ".join(new.split()[j1:j2])})
    return ops


def step_2027(snap, ins=None):
    ins = ins or INS
    replaced = sorted(set(int(x) for x in re.findall(r"paragraph (\d+) is replaced", snap["sii_2026_269_point53"]["text"])))
    lst = snap["sii_amendments_list"]["text"]
    rows176 = re.findall(r"32026R0269 Replacement article 176 paragraph (\d+)", lst)
    diffs = []
    for col in INS_COLS:
        for i in range(5):
            if ins["sii_2027"]["rated"][col][i] != ins["sii_2016"]["rated"][col][i]:
                diffs.append(("CQS" + col, i))
    u27, u16 = ins["sii_2027"]["unrated"], ins["sii_2016"]["unrated"]
    if u27 is None or u16 is None:
        if u27 != u16:
            diffs.append(("unrated", "column missing on one side"))
    else:
        for i in range(4):
            if u27[i] != u16[i]:
                diffs.append(("unrated", i))
    return replaced, rows176, diffs


def provenance(snap, bank=None, ins=None):
    bank = bank or BANK
    ins = ins or INS
    rows, missing = [], []
    for side, tabs in (("bank", bank), ("ins", ins)):
        for v, t in tabs.items():
            srcs = t.get("src") or []
            if not srcs:
                missing.append((side, v, "no source id"))
            if not t.get("applies"):
                missing.append((side, v, "no application date"))
            for sid in srcs:
                e = snap.get(sid)
                if e is None:
                    missing.append((side, v, "source id %s not in snapshot" % sid))
                    continue
                for fld in ("url", "accessed", "version", "text"):
                    if not e.get(fld):
                        missing.append((side, v, "%s lacks %s" % (sid, fld)))
                rows.append({"side": side, "version": v, "source": sid, "url": e.get("url"),
                             "accessed": e.get("accessed"), "version_text": e.get("version"),
                             "applies": t.get("applies")})
    return rows, missing


# ------------------------------------------------------------------ criteria
def _crit(name, kind, verdict, detail, extra=None):
    c = {"name": name, "kind": kind, "detail": detail, "passed": None if verdict is None else bool(verdict)}
    if extra:
        c.update(extra)
    return c


def fmtF(x):
    return str(x)


def fmt(x):
    if x == math.inf:
        return "inf"
    return "%.6f" % x


def fm2(x):
    # Multiples in detail strings are rounded to two decimals, not cut from the six-decimal string.
    if x == math.inf:
        return "inf"
    return "%.2f" % x


def build(m=None, snap=None, durations=None):
    m = m or Model()
    snap = snap or load_snapshot()
    rep = {"model": m, "snap": snap}
    rep["fam"] = {c: families(m, c, durations) for c in COMBOS}
    rep["fam_alt"] = families(m, "current", durations, alt=True)
    rep["short"] = families(m, "current", SHORT)
    rep["notch"] = notch_family(m, "current", letter_fn=m.notch_letter_fn or notch_letter)
    rep["transcription"] = check_transcription(snap, m.bank, m.ins)
    rep["breaks"] = {iv: breakpoints(t) for iv, t in m.ins.items()}
    rep["mapping"] = check_mapping(snap, m.bank_step, m.ins_step)
    rep["crr3"] = crr3_step(m)
    rep["roots"] = {c: bb_b_roots(m, c) for c in ("pre_crr3", "current")}
    rep["levels"] = level_signs(m, "current")
    rep["d22"] = d22(m, "current")
    rep["s2016"] = step_2016(m)
    rep["s2027"] = step_2027(snap, m.ins)
    rep["para1"] = para1_diff(snap)
    rep["prov"] = provenance(snap, m.bank, m.ins)
    rep["grid"] = list(durations or DURATIONS)
    return rep


def criteria(rep):
    m = rep["model"]
    cr = []
    # MATH1-1
    rows, bad = rep["transcription"]
    br = rep["breaks"]
    got = {iv: sorted((b["column"], b["at"]) for b in br[iv]) for iv in ("sii_2015", "sii_2016")}
    br_ok = all(got[iv] == sorted(EXPECTED_BREAKS[iv]) for iv in got) and br["sii_2016"] == br["sii_2027"]
    unr_breaks = [b for iv in br for b in br[iv] if b["column"] == "U"]
    cov = {}
    for r in rows:
        cov[(r["table"], r["source"])] = cov.get((r["table"], r["source"]), 0) + 1
    cr.append(_crit("MATH1-1", "instrument", not bad and br_ok and not unr_breaks,
                    "%d transcribed cells checked against the stored page text, %d mismatches%s. Coverage: %s. "
                    "Segment-boundary breaks: 2015 text %s; 2016/467 text %s; 2027 text %s; unrated column %s. "
                    "Paragraph 4 of the 2015 text is not in the stored page text, so the unrated column is "
                    "transcribed for 2016/467 only." % (
                        len(rows), len(bad), (": " + "; ".join("%s %s const %s quoted %s (%s)" % (
                            b["table"], b["cell"], b["constant"], b["quoted"], b["source"]) for b in bad)) if bad else "",
                        ", ".join("%s via %s: %d" % (k[0], k[1], v) for k, v in sorted(cov.items())),
                        br["sii_2015"], br["sii_2016"], br["sii_2027"], unr_breaks or "none")))
    # MATH1-2
    mrows, mbad, col56, best, odd = rep["mapping"]
    cr.append(_crit("MATH1-2", "premise", not mbad and col56,
                    "%d (agency, scale, letter) placements read from the two mapping standards for Fitch, Moody's "
                    "and S&P (issuer and issue scales), %d off the position axis%s. Bank: AAA and AA in step 1, then "
                    "A, BBB, BB, B one step each, CCC and below in step 6. Insurer: AAA step 0, AA step 1, then one "
                    "step each, CCC and below step 6; Article 176(3) prints steps 5 and 6 as one column: %s. The "
                    "class line is set by licence (standardised approach banking book against the standard "
                    "formula). A.M. Best is off the axis; its insurer-side long-term issuer row prints no 'aa+' "
                    "(%s)." % (len(mrows), len(mbad), (": " + "; ".join(
                        "%s %s %s %s -> %s" % (b["side"], b["agency"], b["scale"], b["letter"], b["steps"])
                        for b in mbad)) if mbad else "", col56, odd)))
    # MATH1-3
    cur = rep["fam"]["current"]
    a_rows = [r for c in COMBOS for r in rep["fam"][c]["GP"] if {r["g1"], r["g2"]} == {"B", "CCC"}]
    a_bad = [r for r in a_rows if r["ratio"] != 1]
    b_bad = [r for r in rep["notch"] if r["ratio"] != 1]
    c_rows = [r for r in rep["short"]["GPD"]]
    c_bad = [r for r in c_rows if r["ratio"] != 1]
    d_bad = []
    for c in COMBOS:
        _bv, iv = COMBOS[c]
        for r in rep["fam"][c]["CD"]:
            want = m.stress(m.vals, iv, r["g"], r["d1"]) / m.stress(m.vals, iv, r["g"], r["d2"])
            if r["ratio"] != want:
                d_bad.append(r)
    best_rows = rep["notch_best"] = amb_best_notches(best)
    cr.append(_crit("MATH1-3", "known_answer", not (a_bad or b_bad or c_bad or d_bad) and not best_rows["bad"],
                    "(a) B/CCC: %d squares over four version pairs and the grid, %d non-zero. (b) within-letter "
                    "notch squares, positions routed through the code's notch-to-letter map (a check on that routing; "
                    "both mapping standards list letter classes): %d, %d non-zero; A.M. Best explicit notches in both tables: %d same-letter "
                    "pairs, %d in different steps, notches absent from one table: %s. (c) grade pair x duration "
                    "pair with both durations at most 5 years (grid %s, 1/2 floors to 1): %d squares, %d non-zero. "
                    "(d) class x duration pair equals ln(stress(d1)/stress(d2)): %d squares over four version "
                    "pairs, %d off.%s" % (
                        len(a_rows), len(a_bad), len(rep["notch"]), len(b_bad), best_rows["pairs"],
                        len(best_rows["bad"]), best_rows["absent"], [str(x) for x in SHORT], len(c_rows), len(c_bad),
                        sum(len(rep["fam"][c]["CD"]) for c in COMBOS), len(d_bad),
                        (" Names: " + "; ".join(str((r.get("g1"), r.get("g2"), r.get("g"), str(r.get("d")),
                                                    str(r.get("d1")), str(r.get("d2"))))
                                                for r in (a_bad + c_bad + d_bad)[:12])) if (a_bad or c_bad or d_bad) else "")))
    # MATH1-4
    gp = cur["GP"]
    grid_ok = len(rep["grid"]) == len(DURATIONS) and all(d in rep["grid"] for d in DURATIONS)
    cg, cgd, ccd = counts(gp), counts(cur["GPD"]), counts(cur["CD"])
    adj = [r for r in gp if adjacent(r)]
    cadj = counts(adj)
    alt = rep["fam_alt"]
    unstable = sum(1 for r in rep["levels"] if not r["stable"])
    bbu = [r for r in gp if {r["g1"], r["g2"]} == {"BB", UNR}]
    above_any = cg["above_floor"] > 0
    nonstruct = nonstructural_zeros(cur)
    cr.append(_crit("MATH1-4", "own_reading", above_any and grid_ok,
                    "Current pair (bank 2024/1623, insurer 2016/467). GP family (%d grade pairs incl. unrated x %d "
                    "duration points): %d above the floor, %d on the floor, %d exactly zero. Adjacent letter "
                    "pairs: %d above, %d on, %d zero of %d. BB/unrated: %s. GPD family: %d above, %d on, %d zero of %d. "
                    "CD family: %d above, %d on, %d zero of %d. With the '11 %%' cell read at a 1 point tick: GP %s, "
                    "GPD %s, CD %s. Level squares at bank multipliers 8, 10.5, 13 %%: %d of %d change sign across "
                    "the multipliers; printed, not read. Grid complete: %s. Exact zeros outside the B/CCC family: "
                    "GP %s; GPD %s. Rival point prediction: %s; it entails "
                    "zero on every square, and every square above the floor is a cell where it fails." % (
                        len(pairs(positions_for(m, "current"))), len(rep["grid"]),
                        cg["above_floor"], cg["on_floor"], cg["zero"],
                        cadj["above_floor"], cadj["on_floor"], cadj["zero"], cadj["total"],
                        ", ".join("%s %+.4f (%s)" % (str(r["d"]), r["log"], fm2(r["multiple"])) for r in bbu),
                        cgd["above_floor"], cgd["on_floor"], cgd["zero"], cgd["total"],
                        ccd["above_floor"], ccd["on_floor"], ccd["zero"], ccd["total"],
                        counts(alt["GP"]), counts(alt["GPD"]), counts(alt["CD"]),
                        unstable, len(rep["levels"]), grid_ok, nonstruct["GP"], nonstruct["GPD"],
                        json.dumps(RIVAL, sort_keys=True)),
                    {"grid_note": "no rival criterion; the point prediction is carried in the detail"}))
    # MATH1-5
    before, after, moved, flips = rep["crr3"]
    nflip = sum(1 for f in flips if f["flipped"])
    nread = sum(1 for f in flips if f["readable"])
    moved_bbb = all("BBB" in k[:2] for k in moved)
    ok5 = bool(moved) and nread > 0 and nflip == nread
    on_before = [str(f["d"]) for f in flips if f["before"]["state"] == "on_floor"]
    on_after = [str(f["d"]) for f in flips if f["after"]["state"] == "on_floor"]
    cr.append(_crit("MATH1-5", "own_reading", ok5,
                    ("this step moved no square. " if not moved else "") +
                    "Regulation 2024/1623 point (51), applied 2025-01-01, bank class only (step 3 from 100 to 75 %%; "
                    "unrated from max(100 %%, sovereign) to 100 %%, read on the branch where the sovereign weight is at "
                    "most 100 %%). GP squares moved: %d of %d, all involving BBB: %s. A/BBB sign changes at %d of the "
                    "%d duration points where both sides stand above the floor (of %d points); a point with a side on "
                    "the floor is printed and not counted. Before: %s; after: %s. On the floor before: %s; after: %s. "
                    "BBB/BB before %+.4f to %+.4f, after %+.4f to %+.4f." % (
                        len(moved), len(before), moved_bbb, nflip, nread, len(DURATIONS),
                        ", ".join("%s %+.4f (%s)" % (str(f["d"]), f["before"]["log"], fm2(f["before"]["multiple"])) for f in flips),
                        ", ".join("%s %+.4f (%s)" % (str(f["d"]), f["after"]["log"], fm2(f["after"]["multiple"])) for f in flips),
                        on_before or "none", on_after or "none",
                        min(before[("BBB", "BB", d)]["log"] for d in DURATIONS), max(before[("BBB", "BB", d)]["log"] for d in DURATIONS),
                        min(after[("BBB", "BB", d)]["log"] for d in DURATIONS), max(after[("BBB", "BB", d)]["log"] for d in DURATIONS))))
    # MATH1-6
    c_pre, roots_pre = rep["roots"]["pre_crr3"]
    c_cur, roots_cur = rep["roots"]["current"]
    one = len(roots_cur) == 1 and roots_cur[0][0] == "root" and roots_cur == roots_pre and c_pre == c_cur
    reg = (one and roots_cur[0][1] == REGISTERED_BB_B_ROOT and c_cur == REGISTERED_BB_B_BANK_RATIO
           and BB_B_SEGMENT[0] < roots_cur[0][1] <= BB_B_SEGMENT[1])
    pts = [r for r in gp if (r["g1"], r["g2"]) == ("BB", "B")]
    cr.append(_crit("MATH1-6", "own_reading", reg,
                    "BB/B along duration: bank ratio %s before and after the 2025 step; exact sign changes on [1, 30]: "
                    "%s (%.4f years). Registered: one crossing at %s inside the insurer's 10 to 15 year segment, bank "
                    "ratio %s; reproduced: %s. The crossing is set by the insurer's step 4 and step 5-6 coefficients "
                    "against the bank's unchanged 100/150. Grid points: %s." % (
                        c_cur, [(r[0], str(r[1])) for r in roots_cur],
                        float(roots_cur[0][1]) if roots_cur and roots_cur[0][0] == "root" else float("nan"),
                        REGISTERED_BB_B_ROOT, REGISTERED_BB_B_BANK_RATIO, reg,
                        ", ".join("%s %+.4f %s (%s)" % (str(r["d"]), r["log"], r["state"], fm2(r["multiple"])) for r in pts))))
    # MATH1-7
    prow, pmiss = rep["prov"]
    cr.append(_crit("MATH1-7", "bookkeeping", not pmiss,
                    "%d (table version, source) rows carry url, access date, version and quoted text; missing: %s. "
                    "Uncovered table: insurer unrated column of the 2015 text (paragraph 4 not in the stored page "
                    "text)." % (len(prow), pmiss or "none")))
    # MATH1-8
    s = rep["s2016"]
    over = {f: [r for r in s[f] if not r["within"]] for f in s}
    nchg = {f: sum(1 for r in s[f] if r["changed"]) for f in s}
    cr.append(_crit("MATH1-8", "known_answer", not any(over.values()),
                    "Delegated Regulation 2016/467 (2016-04-02, insurer class only; four cells each one 0.1 point "
                    "tick). Squares changed / squares whose change exceeds their own floor: GP %d / %d, GPD %d / %d, "
                    "CD %d / %d (unrated positions left out: the 2015 paragraph 4 is not transcribed). The step "
                    "lands on the floor. Each of the four cells moves by one tick, so this holds almost by "
                    "construction; as a check on the transcription it catches a 2016 cell typed three ticks or more "
                    "off its printed value (planted on the step 1 cell 8,5: one or two ticks either way pass, three "
                    "fail). Smaller slips are caught by MATH1-1.%s" % (
                        nchg["GP"], len(over["GP"]), nchg["GPD"], len(over["GPD"]), nchg["CD"], len(over["CD"]),
                        (" Over: " + "; ".join(str(r["key"]) for f in over for r in over[f][:5])) if any(over.values()) else "")))
    # MATH1-9
    replaced, rows176, diffs = rep["s2027"]
    ok9 = replaced == [1] and rows176 == ["1"] and not diffs
    cr.append(_crit("MATH1-9", "known_answer", ok9,
                    "Delegated Regulation 2026/269 point (53), applying from 2027-01-30: paragraphs replaced %s; "
                    "amendment rows on Article 176 from this act: paragraph %s. Table cells differing between the "
                    "2027 and the 2016/467 versions: %s. Paragraph 1 changes: %s." % (
                        replaced, rows176, diffs or "none",
                        "; ".join("%s '%s' -> '%s'" % (o["op"], o["old"], o["new"]) for o in rep["para1"]))))
    return cr


def nonstructural_zeros(fam):
    """Exact zeros not set by the B/CCC column merge."""
    gp = [(r["g1"], r["g2"], str(r["d"])) for r in fam["GP"]
          if r["state"] == "zero" and {r["g1"], r["g2"]} != {"B", "CCC"}]
    gpd = [(r["g1"], r["g2"], str(r["d1"]), str(r["d2"])) for r in fam["GPD"]
           if r["state"] == "zero" and {r["g1"], r["g2"]} != {"B", "CCC"}]
    return {"GP": gp, "GPD": gpd}


def amb_best_notches(best):
    out = {"pairs": 0, "bad": [], "absent": []}
    bank, ins = best.get("bank", {}), best.get("ins", {})
    allk = sorted(set(bank) | set(ins))
    for n in allk:
        if n not in bank or n not in ins:
            out["absent"].append(n)

    def let(n):
        x = n.rstrip("+-")
        return "ccc" if x in ("ccc", "cc", "c", "d", "e", "f", "s") else x
    both = [n for n in allk if n in bank and n in ins]
    for n1, n2 in pairs(both):
        if let(n1) != let(n2):
            continue
        out["pairs"] += 1
        if bank[n1] != bank[n2] or ins[n1] != ins[n2]:
            out["bad"].append((n1, n2))
    return out


# ------------------------------------------------------------------ record
def row_out(r, keys):
    o = {k: (str(r[k]) if isinstance(r[k], F) else r[k]) for k in keys}
    o.update({"log": "%+.6f" % r["log"], "floor": fmt(r["floor"]), "multiple": fmt(r["multiple"]),
              "state": r["state"], "ratio": str(r["ratio"])})
    return o


def record(rep, crits):
    m = rep["model"]
    cur = rep["fam"]["current"]
    before, after, moved, flips = rep["crr3"]
    tables = {}
    for bv, t in m.bank.items():
        tables["bank " + bv] = {"rw": {str(k): str(v) for k, v in t["rw"].items()}, "unrated": str(t["unrated"]),
                               "unrated_rule": t["unrated_rule"], "src": t["src"], "applies": t["applies"]}
    for iv, t in m.ins.items():
        tables["ins " + iv] = {"rated": {c: [[None if a is None else str(a), str(b)] for a, b in segs]
                                         for c, segs in t["rated"].items()},
                               "unrated": None if t["unrated"] is None else
                               [[None if a is None else str(a), str(b)] for a, b in t["unrated"]],
                               "src": t["src"], "applies": t["applies"],
                               "unrated_missing": t.get("unrated_missing")}
    trows, _ = rep["transcription"]
    mrows, _, col56, best, odd = rep["mapping"]
    return {
        "stage": "B155",
        "config": {
            "grid_durations": [str(d) for d in DURATIONS],
            "short_grid_for_family_c": [str(d) for d in SHORT],
            "positions": POSITIONS,
            "ticks": {"risk_weight": "1 percentage point", "stress_a_b": "0.1 percentage point",
                      "alt_cell": "the 2016/467 step 1, 15-20 year 'a' printed as '11 %', also read at 1 point"},
            "bank_multipliers_for_level_squares": [str(k) for k in MULTIPLIERS],
            "combos": {k: list(v) for k, v in COMBOS.items()},
            "bank_step": BANK_STEP, "insurer_step": INS_STEP, "insurer_column": {str(k): v for k, v in INS_COLUMN.items()},
            "snapshot": "data/raw/b155/b155_text_snapshot.json",
        },
        "criteria": crits,
        "mapping_11c": MAPPING_11C,
        "rival": RIVAL,
        "tables": tables,
        "transcription": trows,
        "breakpoints": rep["breaks"],
        "position_mapping": mrows,
        "column_5_and_6_printed": col56,
        "am_best_rows": {k: v for k, v in best.items()},
        "am_best_oddity": odd,
        "provenance": rep["prov"][0],
        "counts": {c: {f: counts(rep["fam"][c][f]) for f in ("GP", "GPD", "CD")} for c in COMBOS},
        "counts_alt_tick_current": {f: counts(rep["fam_alt"][f]) for f in ("GP", "GPD", "CD")},
        "counts_adjacent_current": counts([r for r in cur["GP"] if adjacent(r)]),
        "exact_zeros_outside_b_ccc_current": nonstructural_zeros(cur),
        "squares_current_GP": [row_out(r, ["g1", "g2", "d"]) for r in cur["GP"]],
        "squares_current_CD": [row_out(r, ["g", "d1", "d2"]) for r in cur["CD"]],
        "squares_current_GPD": [row_out(r, ["g1", "g2", "d1", "d2"]) for r in cur["GPD"]],
        "squares_by_combo_GP": {c: [row_out(r, ["g1", "g2", "d"]) for r in rep["fam"][c]["GP"]] for c in COMBOS},
        "crr3_step": {"moved": [[k[0], k[1], str(k[2])] for k in moved],
                      "a_bbb": [{"d": str(f["d"]), "before": "%+.6f" % f["before"]["log"],
                                 "before_state": f["before"]["state"], "before_multiple": fmt(f["before"]["multiple"]),
                                 "after": "%+.6f" % f["after"]["log"], "after_state": f["after"]["state"],
                                 "after_multiple": fmt(f["after"]["multiple"]), "flipped": f["flipped"],
                                 "both_above_floor": f["readable"]} for f in flips]},
        "bb_b_crossing": {c: {"bank_ratio": str(v[0]), "roots": [[x[0]] + [str(y) for y in x[1:]] for x in v[1]]}
                          for c, v in rep["roots"].items()},
        "bb_b_crossing_sensitivity": rep.get("sens", []),
        "level_square_signs": [{"g1": r["g1"], "g2": r["g2"], "d": str(r["d"]), "signs": r["signs"],
                                "stable": r["stable"]} for r in rep["levels"]],
        "level_squares_read": False,
        "independent_squares_d22": rep["d22"],
        "step_2016_467": {f: {"changed": sum(1 for r in v if r["changed"]),
                              "over_floor": sum(1 for r in v if not r["within"]),
                              "rows_changed": [{"key": [str(x) for x in r["key"]], "change": "%.6f" % r["change_log"],
                                                "floor": fmt(r["floor"])} for r in v if r["changed"]]}
                          for f, v in rep["s2016"].items()},
        "step_2026_269": {"paragraphs_replaced": rep["s2027"][0], "amendment_rows": rep["s2027"][1],
                          "table_diffs": rep["s2027"][2], "paragraph_1_changes": rep["para1"]},
        "notch_family": {"squares": len(rep["notch"]), "nonzero": sum(1 for r in rep["notch"] if r["ratio"] != 1),
                         "am_best": rep["notch_best"]},
        "page_text": [{k: e[k] for k in ("id", "url", "accessed", "version", "text") if k in e}
                      for _i, e in sorted(rep["snap"].items())],
    }


def sensitivity(m):
    out = []
    for key in ("ins|sii_2016|4|2|a", "ins|sii_2016|4|2|b", "ins|sii_2016|5&6|2|a", "ins|sii_2016|5&6|2|b",
                "bank|crr3|4", "bank|crr3|5"):
        tick = TICK_RW if key.startswith("bank") else TICK_AB
        for sgn in (1, -1):
            mm = copy.deepcopy(m)
            parts = key.split("|")
            if parts[0] == "ins":
                col, i, ab = parts[2], int(parts[3]), parts[4]
                a, b = mm.ins["sii_2016"]["rated"][col][i]
                mm.ins["sii_2016"]["rated"][col][i] = (a + sgn * tick, b) if ab == "a" else (a, b + sgn * tick)
            else:
                mm.bank["crr3"]["rw"][int(parts[2])] += sgn * tick
            mm = Model(mm.bank, mm.ins)
            _c, roots = bb_b_roots(mm, "current")
            r0 = roots[0][1] if roots and roots[0][0] == "root" else None
            out.append({"input": key, "move": ("+" if sgn > 0 else "-") + str(tick),
                        "root": str(r0), "shift_years": None if r0 is None else "%+.4f" % float(r0 - F(140, 11))})
    return out


# ------------------------------------------------------------------ selftest
def mutated(bank=None, ins=None, **kw):
    return Model(bank or copy.deepcopy(BANK), ins or copy.deepcopy(INS), **kw)


def known_answers(rep):
    """Registered values, computed before the script was written; returns failures."""
    bad = []
    gp = gp_index(rep["fam"]["current"]["GP"])

    def chk(label, cond):
        if not cond:
            bad.append(label)
    r = gp[("AA", "A", F(1))]
    chk("AA/A at 1: +0.675, 7.08", abs(r["log"] - 0.675) < 5e-4 and abs(r["multiple"] - 7.08) < 5e-3)
    r = gp[("AAA", "AA", F(1))]
    chk("AAA/AA at 1: -0.201, 1.70", abs(r["log"] + 0.201) < 5e-4 and abs(r["multiple"] - 1.70) < 5e-3)
    r = gp[("BB", "B", F(25, 2))]
    chk("BB/B at 12.5: -0.008, 0.84 on floor", abs(r["log"] + 0.008) < 5e-4 and abs(r["multiple"] - 0.84) < 5e-3
        and r["state"] == "on_floor")
    r = gp[("BBB", "BB", F(1))]
    chk("BBB/BB at 1: -0.300, 7.35", abs(r["log"] + 0.300) < 5e-4 and abs(r["multiple"] - 7.35) < 5e-3)
    r = gp[("AA", "A", F(30))]
    chk("AA/A at 30: +0.814, 14.64", abs(r["log"] - 0.814) < 5e-4 and abs(r["multiple"] - 14.64) < 5e-3)
    adj = counts([x for x in rep["fam"]["current"]["GP"] if adjacent(x)])
    chk("adjacent: 54 squares, 9 zero, 44 above, 1 on", adj == {"above_floor": 44, "on_floor": 1, "zero": 9, "total": 54})
    _b, _a, _m, flips = rep["crr3"]
    chk("A/BBB flips at the six points above the floor on both sides, none counted at the ties",
        [str(f["d"]) for f in flips if f["flipped"]] == ["1", "15/2", "25/2", "35/2", "25", "30"]
        and [str(f["d"]) for f in flips if not f["readable"]] == ["10", "15", "20"])
    chk("A/BBB before on floor at 10, 15, 20",
        [str(f["d"]) for f in flips if f["before"]["state"] == "on_floor"] == ["10", "15", "20"])
    bb = gp_index(rep["fam"]["pre_crr3"]["GP"])[("A", "BBB", F(1))]
    chk("A/BBB before at 1: +0.113, 1.53", abs(bb["log"] - 0.113) < 5e-4 and abs(bb["multiple"] - 1.53) < 5e-3)
    _c, roots = rep["roots"]["current"]
    chk("BB/B root 140/11", roots == [("root", F(140, 11))])
    chk("2015 breaks", sorted((b["column"], b["at"]) for b in rep["breaks"]["sii_2015"]) == [("1", "10")])
    chk("2016 breaks", sorted((b["column"], b["at"]) for b in rep["breaks"]["sii_2016"]) == [("4", "20")])
    half = [x for x in rep["short"]["CD"] if x["g"] == "AA" and x["d1"] == F(1, 2) and x["d2"] == F(1)]
    chk("duration floor: AA at 1/2 and at 1 carry one price", len(half) == 1 and half[0]["ratio"] == 1)
    old = gp_index(rep["fam"]["pre_2016"]["GP"])[("AAA", "AA", F(25, 2))]
    # The bank prints step 1 (AAA and AA) once, so its tick cancels in AAA/AA; the floor is the
    # insurer's step 0 b moving one tick: 8.25 -> 8.00, ln(33/32).
    chk("2015 AAA/AA at 12.5: ln(8.25/9.65), floor ln(33/32)",
        old["ratio"] == F(825, 965) and old["floor_u"] == F(33, 32))
    now = gp_index(rep["fam"]["current"]["GP"])[("AAA", "AA", F(25, 2))]
    chk("current AAA/AA at 12.5: ln(8.25/9.75), floor ln(33/32)",
        now["ratio"] == F(825, 975) and now["floor_u"] == F(33, 32))
    return bad


def crit_of(crits, name):
    return [c for c in crits if c["name"] == name][0]


def selftest():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))
        print(("ok    " if cond else "FAIL  ") + label)

    snap = load_snapshot()
    rep = build(Model(), snap)
    crits = criteria(rep)
    ka = known_answers(rep)
    ok("known answers on the clean tables (%s)" % (ka or "all"), not ka)
    for c in crits:
        ok("clean run: %s passes" % c["name"], c["passed"] is True)
    for row in MAPPING_11C:
        if row["state"] in ("on_floor", "zero"):
            ok("11c: %s carries no verdict" % row["state"], row["verdict"] is None)

    def run(m=None, s=None, durations=None):
        r = build(m or Model(), s or snap, durations)
        return r, criteria(r)

    # MATH1-1
    ins = copy.deepcopy(INS)
    ins["sii_2016"]["rated"]["4"][4] = (_p("46,5"), _p("0,5"))
    ins["sii_2027"]["rated"]["4"][4] = (_p("46,5"), _p("0,5"))
    r1, c1 = run(mutated(ins=ins))
    ok("MATH1-1: 46,6 -> 46,5 empties the 2016 break set", r1["breaks"]["sii_2016"] == [])
    ok("MATH1-1: and the flag fails", crit_of(c1, "MATH1-1")["passed"] is False)
    ins = copy.deepcopy(INS)
    ins["sii_2016"]["rated"]["3"][1] = (_p("12,6"), _p("1,5"))
    r1, c1 = run(mutated(ins=ins))
    bad = r1["transcription"][1]
    ok("MATH1-1: a mistyped a is named", any(b["cell"] == "CQS3 seg1 a" for b in bad)
       and crit_of(c1, "MATH1-1")["passed"] is False)
    # MATH1-2
    st = dict(INS_STEP)
    st["AA"] = 0
    r2, c2 = run(Model(ins_step=st))
    ok("MATH1-2: insurer AA in step 0 fails", crit_of(c2, "MATH1-2")["passed"] is False)
    st = dict(BANK_STEP)
    st["A"] = 1
    r2, c2 = run(Model(bank_step=st))
    ok("MATH1-2: bank A in step 1 fails", crit_of(c2, "MATH1-2")["passed"] is False)
    # MATH1-3
    ins = copy.deepcopy(INS)
    for iv in ins:
        ins[iv]["rated"]["6only"] = [(a if a is None else a + 1, b) for a, b in ins[iv]["rated"]["5&6"]]
    col = dict(INS_COLUMN)
    col[6] = "6only"
    r3, c3 = run(mutated(ins=ins, ins_col=col))
    ok("MATH1-3 (a): B and CCC split on the insurer side fails", crit_of(c3, "MATH1-3")["passed"] is False)
    r3, c3 = run(Model(short_offset=TICK_AB))
    ok("MATH1-3 (c): b*dur + 0.1 fails", crit_of(c3, "MATH1-3")["passed"] is False
       and any(x["ratio"] != 1 for x in r3["short"]["GPD"]))
    r3, c3 = run(Model(bank_dur=lambda pos, dur: F(1) if (pos == "A" and dur > 10) else F(0)))
    ok("MATH1-3 (d): bank weight moving with duration fails", crit_of(c3, "MATH1-3")["passed"] is False)
    r3, c3 = run(Model(notch_letter_fn=lambda n: "BBB" if n == "A-" else notch_letter(n)))
    ok("MATH1-3 (b): a notch placed in the next letter fails the flag",
       any(x["ratio"] != 1 for x in r3["notch"]) and crit_of(c3, "MATH1-3")["passed"] is False)
    # MATH1-4
    ins = copy.deepcopy(INS)
    bank = copy.deepcopy(BANK)
    for iv in ins:
        for c in INS_COLS:
            ins[iv]["rated"][c] = copy.deepcopy(ins[iv]["rated"]["0"])
        ins[iv]["unrated"] = None
    for bv in bank:
        for k in bank[bv]["rw"]:
            bank[bv]["rw"][k] = F(20)
    r4, c4 = run(mutated(bank=bank, ins=ins))
    ok("MATH1-4: rank-one tables read all zero and the flag fails",
       counts(r4["fam"]["current"]["GP"])["zero"] == len(r4["fam"]["current"]["GP"])
       and crit_of(c4, "MATH1-4")["passed"] is False)
    m4 = Model()
    rows0 = [dict(g1=g1, g2=g2, d=d, **gp_square(m4, "current", g1, g2, d, tick_override=F(0)))
             for g1, g2 in pairs(GRADES) for d in DURATIONS]
    ok("MATH1-4: a zero floor counts every non-zero square as above",
       counts(rows0)["above_floor"] == sum(1 for r in rows0 if r["ratio"] != 1))
    r4, c4 = run(durations=[d for d in DURATIONS if d != F(15)])
    ok("MATH1-4: a grid missing a point is reported", crit_of(c4, "MATH1-4")["passed"] is False)
    # MATH1-5
    bank = copy.deepcopy(BANK)
    bank["crr_2013"]["rw"][3] = F(75)
    r5, c5 = run(mutated(bank=bank))
    c = crit_of(c5, "MATH1-5")
    ok("MATH1-5: prior step 3 at 75 moves nothing and fails", c["passed"] is False
       and c["detail"].startswith("this step moved no square"))
    flips = rep["crr3"][3]
    ok("11c: on the clean tables no point with a side on the floor counts as a flip",
       not any(f["flipped"] for f in flips if not f["readable"]) and any(not f["readable"] for f in flips))
    bank = copy.deepcopy(BANK)
    bank["crr_2013"]["rw"][3] = F(95)
    r5, c5 = run(mutated(bank=bank))
    fl = r5["crr3"][3]
    ok("11c: prior step 3 at 95, points on the floor exist and none counts as a flip",
       any(not f["readable"] for f in fl) and not any(f["flipped"] for f in fl if not f["readable"]))
    # MATH1-6
    m6 = Model()
    sens = sensitivity(m6)
    moved_roots = [s for s in sens if s["input"].startswith("ins|sii_2016|5&6|2|a")]
    ok("MATH1-6: moving the step 5-6 a one tick moves the crossing",
       all(s["root"] != str(F(140, 11)) for s in moved_roots))
    bank = copy.deepcopy(BANK)
    for bv in bank:
        bank[bv]["rw"][5] = F(1000)
    r6, c6 = run(mutated(bank=bank))
    ok("MATH1-6: no crossing fails", crit_of(c6, "MATH1-6")["passed"] is False)
    bank = copy.deepcopy(BANK)
    for bv in bank:
        bank[bv]["rw"][5] = F(151)
    r6, c6 = run(mutated(bank=bank))
    ok("MATH1-6: bank B at 151 in both versions moves the crossing off 140/11 and fails",
       r6["roots"]["current"][1][0][1] != REGISTERED_BB_B_ROOT and crit_of(c6, "MATH1-6")["passed"] is False)
    # MATH1-7
    bank = copy.deepcopy(BANK)
    bank["crr3"]["src"] = []
    r7, c7 = run(mutated(bank=bank))
    ok("MATH1-7: a dropped source is reported", crit_of(c7, "MATH1-7")["passed"] is False)
    # MATH1-8
    ins = copy.deepcopy(INS)
    ins["sii_2016"]["rated"]["1"][2] = (_p("9,5"), _p("0,5"))
    r8, c8 = run(mutated(ins=ins))
    ok("MATH1-8: 8,5 typed as 9,5 fails", crit_of(c8, "MATH1-8")["passed"] is False)
    # MATH1-9
    ins = copy.deepcopy(INS)
    ins["sii_2027"]["rated"]["2"][3] = (_p("13,1"), _p("0,5"))
    r9, c9 = run(mutated(ins=ins))
    ok("MATH1-9: a changed 2027 cell fails", crit_of(c9, "MATH1-9")["passed"] is False)

    # mutation test: break the implementation, the known-answer battery must catch each
    mutants = []
    orig_seg = Model.seg_of

    def seg_strict(col, dur):
        segs = SEG_UNR if col == "U" else SEG_RATED
        d = max(dur, F(1))
        for i, (up, _s) in enumerate(segs):
            if up is None or d < up:
                return i
    mutants.append(("segment upper bound exclusive", lambda: setattr(Model, "seg_of", staticmethod(seg_strict)),
                    lambda: setattr(Model, "seg_of", staticmethod(orig_seg))))
    orig_stress = Model.stress

    def stress_noclamp(self, vals, iv, pos, dur):
        if dur < 1:
            return vals["ins|%s|%s|0|b" % (iv, self.ins_col_of(pos))] * dur
        return orig_stress(self, vals, iv, pos, dur)
    mutants.append(("duration floor of 1 dropped", lambda: setattr(Model, "stress", stress_noclamp),
                    lambda: setattr(Model, "stress", orig_stress)))
    orig_w = Model.w

    def w_flip(self, vals, combo, pos, dur):
        return 1 / orig_w(self, vals, combo, pos, dur)
    mutants.append(("orientation flipped", lambda: setattr(Model, "w", w_flip),
                    lambda: setattr(Model, "w", orig_w)))
    orig_ticks = ticks_for

    def ticks_bank_only(keys, alt=False):
        return {k: (TICK_RW if k.startswith("bank") else F(0)) for k in keys}
    mutants.append(("floor from bank ticks only", lambda: globals().__setitem__("ticks_for", ticks_bank_only),
                    lambda: globals().__setitem__("ticks_for", orig_ticks)))
    orig_step = dict(INS_COLUMN)
    mutants.append(("CCC read from step 4 column", lambda: INS_COLUMN.__setitem__(6, "4"),
                    lambda: INS_COLUMN.__setitem__(6, orig_step[6])))
    orig_roots = bb_b_roots

    def roots_lt(m, combo):
        c, rr = orig_roots(m, combo)
        return c, [r for r in rr if r[0] != "root" or r[1] < 12]
    mutants.append(("crossing search drops a segment", lambda: globals().__setitem__("bb_b_roots", roots_lt),
                    lambda: globals().__setitem__("bb_b_roots", orig_roots)))
    orig_judge_mult = judge

    def judge_le(m, ratio_fn, keys, tick_override=None, alt=False):
        r = orig_judge_mult(m, ratio_fn, keys, tick_override, alt)
        if r["state"] == "on_floor":
            r["state"] = "above_floor"
        return r
    mutants.append(("ties counted as above", lambda: globals().__setitem__("judge", judge_le),
                    lambda: globals().__setitem__("judge", orig_judge_mult)))
    for label, apply, undo in mutants:
        apply()
        try:
            rr = build(Model(), snap)
            caught = bool(known_answers(rr))
        except Exception as e:  # noqa: BLE001
            caught = True
            label = label + " (raised %s)" % type(e).__name__
        finally:
            undo()
        ok("mutation caught: " + label, caught)
    rr = build(Model(), snap)
    ok("mutations undone: known answers clean again", not known_answers(rr))

    bad = [c for c in checks if not c[1]]
    print("\nselftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    t0 = time.perf_counter()
    rep = build()
    crits = criteria(rep)
    secs = time.perf_counter() - t0
    rep["sens"] = sensitivity(rep["model"])
    ka = known_answers(rep)
    print("known answers:", ka or "all hold")
    cur = rep["fam"]["current"]
    for r in cur["GP"]:
        if adjacent(r) or UNR in (r["g1"], r["g2"]):
            print("%-8s %-8s %5s  %+.4f  %-11s %s" % (r["g1"], r["g2"], str(r["d"]), r["log"], r["state"],
                                                     fmt(r["multiple"])[:6]))
    for c in COMBOS:
        print(c, {f: counts(rep["fam"][c][f]) for f in ("GP", "GPD", "CD")})
    for s in rep["sens"]:
        print("sensitivity", s)
    print("d22", rep["d22"]["positions"], rep["d22"]["independent_squares"], rep["d22"]["independent_after_exact_merges"])
    for mrow in MAPPING_11C:
        print("11c  %-12s -> %-22s verdict %s" % (mrow["state"], mrow["maps_to"], mrow["verdict"]))
    failed = []
    for c in crits:
        print(("PASS   " if c["passed"] else ("VOID   " if c["passed"] is None else "FAILED[" + c["kind"] + "]: "))
              + c["name"] + "  " + c["detail"][:600])
        if c["passed"] is False:
            failed.append(c["name"])
    print("single run %.2f s (printed only; kept out of the record)" % secs)
    rec = record(rep, crits)
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if not a.no_write:
        import safe_write  # noqa: E402
        out = pathlib.Path(a.out)
        if out.exists():
            safe_write.rewrite(out, "B155 record", lambda _old: text, session=SESSION)
        else:
            safe_write.create(out, "B155 record", text, session=SESSION)
        print("wrote " + str(out) + " (%d bytes)" % len(text.encode("utf-8")))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
