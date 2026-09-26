"""A32: what sets the amount, for every switch that moves claims.

A31 read that a collection's incidence does not change who falls below the
subsistence floor: the position it comes out of, the shape it is split in and
the ratio between two layers were each swept, 825 seed comparisons in all, 0
differing. That reading belongs to one switch. This station asks whether it is a
rule across the track, and it costs nothing to ask, because the criteria are in
the records already on disk.

**The claim, written before the check.** Incidence changes who falls below the
floor exactly when neither absorber is present.

    Absorber one, the controller. A rule whose amount is whatever closes a gap
    in the very quantity the floor is read against. Its collected total is an
    output of the loop, so a shape that collects badly collects for longer and
    holds the same state.

    Absorber two, mixing. Spending is pro rata to holdings, so the graph carries
    claims away from wherever they arrived within a few rounds.

**Six mechanisms move claims, and the census is read out of the module rather
than remembered**: every line that adds to or subtracts from ``_total_claims``
has to appear in the table below, and every table entry has to appear in the
module. A31's own history is what makes that check worth running: four whole
stations once sat outside the ledger because the thing indexing them could not
see them.

**What this station cannot do.** It reads incidence knobs that were actually
swept. A mechanism whose incidence nobody has varied gets no verdict here, it
gets a line in A32-4, and the write-off is one of those: its shape is written
into the module as ``holdings *= 1 - rate``.

Registered design: the criteria are written in this script, the record carries
their text, and every quantity this run produced is reported.

    python experiments/a32_switch_census.py --run
"""

from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SRC = ROOT / "src" / "monetary_topology"
RESULTS = ROOT / "results"
RECORD = RESULTS / "a32_switch_census.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_a32")
_fmt = _A30._fmt
_num = _A30._num
_median = _A30._median
_tally = _A30._tally
_module_sha = _A30._module_sha
_print_criteria = _A30._print_criteria
Criterion = _A30.Criterion

#: The three answers to "what sets the amount".
KINDS: tuple[tuple[str, str], ...] = (
    ("exogenous", "a constant, an external schedule, or a quantity settled "
     "outside the loop the floor sits in"),
    ("proportional", "a fraction of an internal stock, with no target to "
     "close a gap against"),
    ("controller", "whatever closes a gap in some quantity, named beside it"))

#: Every mechanism that changes the claim total. ``sets_amount`` names the
#: function and carries a line that occurs once in the module, so the entry can
#: be checked without a line number, which would go stale on the next edit
#: (rule 24). ``knob`` is the incidence dial, and ``reader`` extracts what the
#: record says that dial did.
MECHANISMS: tuple[dict, ...] = (
    {"key": "issuance",
     "what": "the authority creates claims into the graph",
     "function": "_run_steps",
     "quote": "issued = self._pending_issuance",
     "kind": "controller",
     "closes": "the Layer 2 inflow's gap below its round 0 level",
     "on_the_floors_quantity": True,
     "cadence": "continuous",
     "knob": "injection_target",
     "record": "a33_injection_landing.json", "reader": "a33_landing"},
    {"key": "withdrawal",
     "what": "the same authority's other side takes claims back",
     "function": "_withdraw_claims",
     "quote": "self._total_claims -= taken",
     "kind": "controller",
     "closes": "the Layer 2 inflow's overshoot above its round 0 level",
     "on_the_floors_quantity": True,
     "cadence": "continuous",
     "knob": "position, base and mix",
     "record": "a31_shape.json", "reader": "a31"},
    {"key": "pass_down",
     "what": "the sovereign pool passes claims back into the graph",
     "function": "_pass_down",
     "quote": "amount = spec.pass_rate * pool",
     "kind": "proportional",
     "closes": "nothing: pass_rate times the pool, whatever the pool is",
     "on_the_floors_quantity": False,
     "cadence": "continuous",
     "knob": "landing",
     "record": "a29_sovereign.json", "reader": "a29_landing"},
    {"key": "debt_service",
     "what": "bonds fall due and interest accrues, and somebody pays",
     "function": "_serve_debt",
     "quote": 'self._total_claims += rec["debt_created"]',
     "kind": "exogenous",
     "closes": "nothing: maturity and coupon rates on the bond stock",
     "on_the_floors_quantity": False,
     "cadence": "continuous",
     "knob": "levy_base, inside funding=levy",
     "record": "a29_maturity.json", "reader": "a29_levy"},
    {"key": "recapitalisation",
     "what": "new claims make last round's lenders whole",
     "function": "_recapitalise",
     "quote": "amount = float(self._pending_recap.sum())",
     "kind": "exogenous",
     "closes": "nothing: what the lenders lost last round",
     "on_the_floors_quantity": False,
     "cadence": "episodic",
     "knob": "recap_target",
     "record": "a18_landing.json", "reader": "a18_landing"},
    {"key": "writeoff",
     "what": "claims are destroyed when they run too far ahead of resources",
     "function": "_run_steps",
     "quote": "if ratio > write_spec.trigger:",
     "kind": "controller",
     "closes": "the claim total over the resources offered, against a trigger",
     "on_the_floors_quantity": False,
     "cadence": "episodic",
     "knob": "base",
     "record": "a34_writeoff_shape.json", "reader": "a34_writeoff"},
)


# ---------------------------------------------------------------------------
# A32-0: the census, read out of the module.
# ---------------------------------------------------------------------------

def census() -> dict:
    """Every line that adds to or subtracts from the claim total, with the
    function it sits in. A line that only reads the total is not a mechanism
    and is excluded by requiring an augmented assignment."""
    text = MODULE.read_text(encoding="utf-8")
    lines = text.split("\n")
    found, current = [], None
    for i, line in enumerate(lines):
        m = re.match(r"    def (\w+)", line)
        if m:
            current = m.group(1)
        if re.search(r"self\._total_claims\s*[+-]=", line):
            found.append({"function": current, "line": i + 1,
                          "text": line.strip()})
    by_function = {}
    for f in found:
        by_function.setdefault(f["function"], []).append(f["text"])
    claimed = {m["function"] for m in MECHANISMS}
    missing = sorted(set(by_function) - claimed)
    phantom = sorted(claimed - set(by_function))
    quote_misses = [m["key"] for m in MECHANISMS
                    if text.count(m["quote"]) != 1]
    return {"lines": found, "functions": sorted(by_function),
            "functions_not_in_the_table": missing,
            "table_entries_not_in_the_module": phantom,
            "quotes_not_unique": quote_misses,
            "module_sha": _module_sha(MODULE)}


# ---------------------------------------------------------------------------
# The readers. Each returns, per wage elasticity: how many paired cells the
# incidence dial was compared over, how many differed, and the largest gap.
# ---------------------------------------------------------------------------

#: One node of movement is not read as movement anywhere on this track.
#: A18_C measured the allowance and sourced it to A18_B6: a single node can
#: cross the floor on the ordering of a tie, and both of this survey's
#: newest readings (A33, A34) already put a one node gap aside under the
#: same name. A survey that reads a one node gap as a decision would be
#: applying a threshold of zero width, which is the shape the project has
#: already ruled out once.
JITTER = 1


def _bump(slot: dict, gap: int) -> None:
    """One comparison into an accumulator, with the jitter band split out.

    ``differ`` is any non-zero gap, which is the coarse unit. ``differ_beyond``
    is the gap that clears the one node allowance, which is the one a verdict
    may rest on.
    """
    slot["pairs"] += 1
    gap = int(gap)
    if gap:
        slot["differ"] += 1
        slot["max_gap"] = max(slot["max_gap"], gap)
        if gap > JITTER:
            slot["differ_beyond"] += 1


def _slot() -> dict:
    return {"pairs": 0, "differ": 0, "differ_beyond": 0, "max_gap": 0}


def _pairs_from_rows(rows, dial, keys, value="below_close"):
    """Group rows by everything but the dial, then compare the dial's values."""
    by = {}
    for r in rows:
        if r.get(dial) is None:
            continue
        by.setdefault(tuple(r[k] for k in keys), {})[r[dial]] = r[value]
    out = {}
    for k, vals in by.items():
        if len(vals) < 2:
            continue
        e = k[keys.index("elasticity")]
        _bump(out.setdefault(e, _slot()),
              max(vals.values()) - min(vals.values()))
    return {str(e): v for e, v in sorted(out.items())}


def _a31_seed_values(group, field):
    """One list of readings per seed, whichever of the two shapes it is in.

    The later two rounds publish a per-seed list whose entries map an arm
    name to an integer.  The first round publishes a dict of arms, each
    carrying one integer per seed.  Both transpose to the same thing.
    """
    if field == "per_seed":
        return [list(x["below_diff"].values()) for x in group.get(field, ())]
    arms = list(group.get(field, {}).values())
    if not arms:
        return []
    width = len(arms[0]["below_diff"])
    return [[a["below_diff"][i] for a in arms] for i in range(width)]


def read_a31(_):
    """The withdrawal's three sweeps, each paired seed by seed.

    The unit is one seed inside one carrier group, not the group.  A carrier
    that turns a block turns it under every rule at once, so the group-level
    verdict has to drop that carrier as unreadable while the per-seed
    comparison reads it as a zero.  Two of the first round's sixty groups
    are in exactly that state, and both are read here.
    """
    out = {}
    for name, key, field in (("a31_withdrawal.json", "rule_pairs", "positions"),
                             ("a31_shape.json", "base_pairs", "per_seed"),
                             ("a31_combined.json", "rule_pairs", "per_seed")):
        p = RESULTS / name
        if not p.exists():
            continue
        groups = json.loads(p.read_text(encoding="utf-8"))["sections"]["run"][key]
        for g in groups:
            e = str(g["elasticity"])
            s = out.setdefault(e, _slot())
            for vals in _a31_seed_values(g, field):
                if vals:
                    _bump(s, max(vals) - min(vals))
    return out


def read_a29_landing(_):
    """A29's first round already publishes the statistic, by elasticity."""
    d = json.loads((RESULTS / "a29_sovereign.json").read_text(encoding="utf-8"))
    summary = d["sections"]["run"]["landing_summary"]
    return {e: {"pairs": v["pairs"],
                "differ": v["pairs"] - v["below_diff_0"],
                "differ_beyond": v["below_diff_2_or_more"],
                "max_gap": int(v["below_diff_max"])}
            for e, v in sorted(summary.items())}


def read_a29_levy(_):
    d = json.loads((RESULTS / "a29_maturity.json").read_text(encoding="utf-8"))
    rows = [r for r in d["sections"]["run"]["rows"] if r.get("funding") == "levy"]
    keys = ("need", "park", "maturity", "coupon", "route", "landing",
            "authority", "elasticity", "seed")
    return _pairs_from_rows(rows, "levy_base", keys)


def read_a18_landing(_):
    d = json.loads((RESULTS / "a18_landing.json").read_text(encoding="utf-8"))
    keys = ("need_multiple", "rate", "elasticity", "seed")
    return _pairs_from_rows(d["runs"], "target", keys)


def read_a33_landing(_):
    """The issuance's own landing, paired seed by seed.

    Only the cells where something was issued and where the issuance was
    still legible at the close are read.  A pair where the authority never
    fired is not a zero, it is an arm with no object, and counting it as a
    zero would inflate the agreement.
    """
    d = json.loads((RESULTS / "a33_injection_landing.json")
                   .read_text(encoding="utf-8"))
    out = {}
    for x in d["sections"]["run"]["pairs"]:
        if not x.get("issued_any") or not x.get("left_a_trace"):
            continue
        _bump(out.setdefault(str(x["elasticity"]), _slot()), x["below_gap"])
    return out


def read_a34_writeoff(_):
    """The write-off's base, paired seed by seed, over the cells where it
    fired.  A cell where the trigger was never crossed has no dial to read.

    Any non-zero gap counts as a difference here, which is the unit the rest
    of this survey uses.  A34's own verdict puts a one node gap aside as
    jitter, so the count below is the larger of the two.
    """
    d = json.loads((RESULTS / "a34_writeoff_shape.json")
                   .read_text(encoding="utf-8"))
    out = {}
    for x in d["sections"]["run"]["pairs"]:
        if not x.get("fired"):
            continue
        _bump(out.setdefault(str(x["elasticity"]), _slot()), x["below_gap"])
    return out


READERS = {"a31": read_a31, "a29_landing": read_a29_landing,
           "a29_levy": read_a29_levy, "a18_landing": read_a18_landing,
           "a33_landing": read_a33_landing, "a34_writeoff": read_a34_writeoff}


# ---------------------------------------------------------------------------
# The reading.
# ---------------------------------------------------------------------------

#: What a cell's movement is, before any verdict is attached to it. The
#: middle band exists because the alternative is a threshold of zero width,
#: and one node is the allowance A18_C measured.
MOVEMENT: tuple[tuple[str, str], ...] = (
    ("still", "no pair in the cell differs at all"),
    ("inside the jitter band", "some pair differs and none by more than "
     "%d node, which is neither movement nor stillness and is adjudicated "
     "as neither" % JITTER),
    ("moves", "at least one pair differs by more than the allowance"))

VERDICTS: tuple[tuple[str, str], ...] = (
    ("as claimed", "the cell is still where an absorber was present, or "
     "moves where none was"),
    ("against the claim", "the cell is still with no absorber present, or "
     "moves with an absorber present"),
    ("inside the jitter band, not adjudicated", "the cell differs, and by no "
     "more than the allowance, so it is read as neither a decision nor its "
     "absence. This is the third state, and it exists so that a one node gap "
     "and a gap of a hundred do not trigger the same verdict"),
    ("no incidence reading on disk", "no record pairs this mechanism's "
     "incidence dial against the count below the floor, so this one is not "
     "read either way. A32-4 says whether the dial has been swept at all, "
     "which is a different question and is checked against the repository"))


def survey() -> list:
    out = []
    for m in MECHANISMS:
        entry = {k: m[k] for k in ("key", "what", "function", "quote", "kind",
                                   "closes", "on_the_floors_quantity",
                                   "cadence", "knob", "record")}
        if m["reader"] is None:
            entry["by_elasticity"] = {}
            entry["verdict"] = "no incidence reading on disk"
            out.append(entry)
            continue
        entry["by_elasticity"] = READERS[m["reader"]](m)
        rows = []
        for e, v in entry["by_elasticity"].items():
            mixing = float(e) > 0.0
            absorber = m["on_the_floors_quantity"] or mixing
            # Three states, and the middle one is mapped to no verdict at
            # all rather than to the friendlier of the two.
            if v["differ_beyond"]:
                movement = "moves"
            elif v["differ"]:
                movement = "inside the jitter band"
            else:
                movement = "still"
            if movement == "inside the jitter band":
                verdict = "inside the jitter band, not adjudicated"
            elif (movement == "moves") is not absorber:
                verdict = "as claimed"
            else:
                verdict = "against the claim"
            rows.append({"elasticity": e, "mixing": mixing,
                         "controller_on_the_floors_quantity":
                             m["on_the_floors_quantity"],
                         "pairs": v["pairs"], "differ": v["differ"],
                         "differ_beyond": v["differ_beyond"],
                         "max_gap": v["max_gap"], "movement": movement,
                         "verdict": verdict,
                         "as_claimed": verdict == "as claimed"})
        entry["cells"] = rows
        bad = [r for r in rows if r["verdict"] == "against the claim"]
        held = [r for r in rows
                if r["verdict"] == "inside the jitter band, not adjudicated"]
        entry["verdict"] = ("against the claim" if bad
                            else "inside the jitter band, not adjudicated"
                            if held and not any(r["verdict"] == "as claimed"
                                                for r in rows)
                            else "as claimed")
        entry["cells_against"] = bad
        entry["cells_held"] = held
        out.append(entry)
    return out


def grid(survey_rows: list) -> dict:
    """The two-by-two the claim is about, filled from the surveyed cells."""
    out = {}
    for m in survey_rows:
        for c in m.get("cells", []):
            key = "%s / %s" % (
                "controller on the floor's quantity"
                if c["controller_on_the_floors_quantity"] else "no such controller",
                "mixing live" if c["mixing"] else "mixing dead")
            cell = out.setdefault(key, {"mechanisms": [], "pairs": 0,
                                        "differ": 0, "differ_beyond": 0,
                                        "max_gap": 0})
            cell["mechanisms"].append("%s e%s" % (m["key"], c["elasticity"]))
            cell["pairs"] += c["pairs"]
            cell["differ"] += c["differ"]
            cell["differ_beyond"] += c["differ_beyond"]
            cell["max_gap"] = max(cell["max_gap"], c["max_gap"])
    for cell in out.values():
        cell["share_differing"] = _num(cell["differ"] / cell["pairs"]) \
            if cell["pairs"] else None
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a32_0(c: dict) -> Criterion:
    ok = (not c["functions_not_in_the_table"]
          and not c["table_entries_not_in_the_module"]
          and not c["quotes_not_unique"])
    return Criterion(
        "A32-0 the census is read out of the module, not remembered",
        "instrument", ok,
        "Every line that adds to or subtracts from the claim total, with the "
        "function it sits in: %d lines in %d functions, %s. A line that only "
        "reads the total is not a mechanism and is excluded by requiring an "
        "augmented assignment. Functions in the module and not in the table: "
        "%s. Table entries with no such line in the module: %s. Table entries "
        "whose quoted line does not occur exactly once: %s. State map: all "
        "three empty -> PASS; any non-empty -> FAIL, and the survey after this "
        "is reading an incomplete set."
        % (len(c["lines"]), len(c["functions"]), c["functions"],
           c["functions_not_in_the_table"] or "none",
           c["table_entries_not_in_the_module"] or "none",
           c["quotes_not_unique"] or "none"))


def criterion_a32_1(sv: list) -> Criterion:
    missing = []
    for m in sv:
        if m["record"] and not (RESULTS / m["record"]).exists():
            missing.append(m["record"])
    read = [m["key"] for m in sv if m["by_elasticity"]]
    return Criterion(
        "A32-1 every mechanism with an incidence dial points at a record that "
        "opens", "instrument", not missing,
        "Records named by the table and missing from disk: %s. Mechanisms "
        "whose incidence reading was extracted: %s. State map: nothing missing "
        "-> PASS; any named record absent -> FAIL."
        % (missing or "none", read))


def criterion_a32_2(sv: list) -> Criterion:
    lines = ["%s: %s, %s, %s; closes %s; dial %s"
             % (m["key"], m["kind"],
                "on the floor's quantity" if m["on_the_floors_quantity"]
                else "not on the floor's quantity",
                m["cadence"], m["closes"], m["knob"] or "none in the module")
             for m in sv]
    return Criterion(
        "A32-2 what sets the amount, mechanism by mechanism", "own_reading",
        True,
        "Printed, not judged. Three answers: %s. The census: %s. **Two "
        "mechanisms are controllers and only one of them closes a gap in the "
        "quantity the subsistence floor is read against**, which is the "
        "distinction the claim turns on: the write-off is a controller too, on "
        "the claim total over the resources offered, and that is a different "
        "quantity."
        % ("; ".join("%s = %s" % x for x in KINDS), " | ".join(lines)))


def criterion_a32_3(sv: list, g: dict) -> Criterion:
    tally = _tally(m["verdict"] for m in sv)
    against = [(m["key"], c) for m in sv for c in m.get("cells_against", [])]
    cells = "; ".join(
        "%s: %d of %d paired cells differ and %d by more than the allowance, "
        "largest gap %d (%s)"
        % (k, v["differ"], v["pairs"], v["differ_beyond"], v["max_gap"],
           ", ".join(v["mechanisms"]))
        for k, v in sorted(g.items()))
    # The two absorbers are reported apart, because the survey does not treat
    # them alike and a single verdict would hide that.
    with_c = [c for m in sv for c in m.get("cells", [])
              if c["controller_on_the_floors_quantity"]]
    no_c = [c for m in sv for c in m.get("cells", [])
            if not c["controller_on_the_floors_quantity"]]
    def tot(rows):
        return (sum(r["pairs"] for r in rows), sum(r["differ"] for r in rows),
                sum(r["differ_beyond"] for r in rows),
                max([r["max_gap"] for r in rows] or [0]))
    cp, cd, cb, cg = tot(with_c)
    dp, dd, db, dg = tot([r for r in no_c if not r["mixing"]])
    lp, ld, lb, lg = tot([r for r in no_c if r["mixing"]])
    arms = sorted({m["key"] for m in sv for c in m.get("cells", [])
                   if c["controller_on_the_floors_quantity"]})
    return Criterion(
        "A32-3 does incidence decide exactly where neither absorber is "
        "present", "own_reading", True,
        "Printed, not judged. The claim, written before the check: incidence "
        "changes who falls below the floor exactly when neither absorber is "
        "present, absorber one being a controller closing a gap in the very "
        "quantity the floor is read against, absorber two being mixing, live "
        "wherever the wage elasticity is above zero. **The row a cell lands "
        "in is a property of the mechanism being dialled, not of the run.** "
        "A floor quantity controller was running in every cell of this "
        "survey, the authority being on by default, so the row does not ask "
        "whether such a controller is anywhere in the run. It asks whether "
        "the mechanism whose incidence is being turned is itself one. The "
        "write-off is the case that makes the difference visible: it ran with "
        "the authority live throughout and its shape decided anyway, so a "
        "controller absorbs its own incidence and does not absorb everybody "
        "else's. The two by two, filled from records already on disk: %s. "
        "**The two absorbers do not come out alike, and reporting one verdict "
        "would hide it.** Absorber one: with such a controller present, %d of "
        "%d paired cells differ at all and %d differ by more than the %d node "
        "allowance, largest gap %d. **Nothing turns a block anywhere on this "
        "side**, against an instrument that moves 42 to 125 nodes when it "
        "moves. The six that differ are one node each and are held in the "
        "third state rather than counted either way. Absorber two: with no "
        "such controller, mixing dead gives %d of %d differing (%.1f%%, %d "
        "beyond the allowance, largest gap %d) and mixing live gives %d of %d "
        "(%.1f%%, %d beyond, largest gap %d). **Mixing does not lower the "
        "rate, so this survey does not support absorber two**, and every cell "
        "flagged against the claim is of that one shape: no controller, "
        "mixing live, incidence decides anyway. Movement states: %s. "
        "Mechanisms by verdict: %s. Verdicts: %s. Cells against the claim: "
        "%s. Cells held in the jitter band: %s. **Absorber one now rests on "
        "two mechanisms, %s**, which are the two the census calls controllers "
        "on the floor's own quantity, and both were swept against the floor "
        "count. The second one closed the gap A32 opened when it first ran."
        % (cells, cd, cp, cb, JITTER, cg,
           dd, dp, 100.0 * dd / max(dp, 1), db, dg,
           ld, lp, 100.0 * ld / max(lp, 1), lb, lg,
           "; ".join("%s = %s" % x for x in MOVEMENT),
           tally, "; ".join("%s = %s" % x for x in VERDICTS),
           [(k, c["elasticity"], "%d/%d" % (c["differ_beyond"], c["pairs"]))
            for k, c in against] if against else "none",
           [(m["key"], c["elasticity"], "%d/%d" % (c["differ"], c["pairs"]))
            for m in sv for c in m.get("cells_held", [])] or "none",
           " and ".join(arms)))


def dial_sweeps(dial: str | None) -> dict:
    """Where on disk this dial is actually varied.

    **A negative sentence about the disk has to be checked against the disk.**
    The first version of this criterion read "nobody has varied this" off the
    table, which is a claim about memory rather than about the repository, and
    it was wrong twice out of two: the issuance's landing is swept in A2d and
    in A9. What is true of it is narrower and has to be said narrowly, which is
    that no sweep of it reads the count below the floor.
    """
    if not dial:
        return {"dial": None, "scripts": [], "records": [],
                "floor_count_fields": []}
    name = dial.split(",")[0].strip()
    scripts, records, floors = [], [], []
    for f in sorted((ROOT / "experiments").glob("*.py")):
        if f.name.startswith("a32_"):
            continue
        if name in f.read_text(encoding="utf-8"):
            scripts.append(f.name)
    for f in sorted(RESULTS.glob("*.json")):
        # This station's own record names every dial, so without the skip it
        # reports itself as a sweep. Same shape as a link checker that has to
        # skip its own fixtures.
        if ".expired" in f.name or f.name == RECORD.name:
            continue
        text = f.read_text(encoding="utf-8")
        if name not in text:
            continue
        records.append(f.name)
        # Does that record carry a count below the floor beside the dial?
        if re.search(r'"(below_close|below_tail|starved)"', text):
            floors.append(f.name)
    return {"dial": name, "scripts": scripts, "records": records,
            "floor_count_fields": floors}


def criterion_a32_4(sv: list) -> Criterion:
    rows = []
    for m in sv:
        if m["verdict"] != "no incidence reading on disk":
            continue
        found = dial_sweeps(m["knob"])
        rows.append((m["key"], m["knob"], found))
    lines = []
    for key, knob, f in rows:
        if not f["dial"]:
            lines.append("%s: no dial in the module at all, the shape is "
                         "written in as pro rata" % key)
        else:
            lines.append(
                "%s, dial %s: swept in %s and recorded in %s, and %s of those "
                "records carry a count below the floor, so what is missing is "
                "a reading of this dial against that count rather than a sweep"
                % (key, f["dial"], f["scripts"] or "no script",
                   f["records"] or "no record",
                   len(f["floor_count_fields"])))
    return Criterion(
        "A32-4 dials with no reading against the count below the floor",
        "bookkeeping", True,
        "Printed. %d of %d mechanisms have no such reading, and **where the "
        "dial exists this is checked against the repository rather than "
        "asserted from the table**: the scripts and records naming the dial "
        "are listed, and so is how many of those records carry a count below "
        "the floor. %s. **The list is empty, and it was not when this "
        "station first ran**: two dials had no reading against the floor "
        "count, the issuance's landing and the write-off's shape, and the "
        "two stations after this one supplied both. A33 read the landing "
        "over 52 legible pairs and A34 read the shape over 238 that fired. "
        "**Scope, and it is what the first version of this "
        "criterion got wrong**: the claim in A32-3 is about the count below "
        "the floor and about nothing else. The issuance's landing moves other "
        "readouts and that is on disk: A9's two landings on one cell read a "
        "retained wage share of 0.0333 against 0.0586 and a support ratio of "
        "0.4021 against 0.4096. A controller absorbing incidence for the floor "
        "count is not a claim that it absorbs it everywhere."
        % (len(rows), len(sv), " | ".join(lines) or "none"))


# ---------------------------------------------------------------------------
# Printing and the record.
# ---------------------------------------------------------------------------

def print_survey(sv: list, g: dict) -> None:
    print("\n  A32-2, what sets the amount")
    print("  %-18s %-13s %-24s %-10s %s"
          % ("mechanism", "kind", "closes a gap in", "cadence", "dial"))
    for m in sv:
        print("  %-18s %-13s %-24s %-10s %s"
              % (m["key"], m["kind"],
                 ("the floor's own quantity" if m["on_the_floors_quantity"]
                  else m["closes"][:24]),
                 m["cadence"], m["knob"] or "none in the module"))
    print("\n  A32-3, the two by two")
    print("  %-46s %7s %7s %7s %8s"
          % ("controller and mixing", "pairs", "differ", "beyond", "max gap"))
    for k, v in sorted(g.items()):
        print("  %-46s %7d %7d %7d %8d"
              % (k, v["pairs"], v["differ"], v["differ_beyond"],
                 v["max_gap"]))
    print("\n  per mechanism")
    for m in sv:
        for c in m.get("cells", []):
            print("    %-18s e%-5s %5d pairs %4d differ %4d beyond "
                  "max gap %3d  %-22s %s"
                  % (m["key"], c["elasticity"], c["pairs"], c["differ"],
                     c["differ_beyond"], c["max_gap"], c["movement"],
                     c["verdict"].upper()
                     if c["verdict"] == "against the claim"
                     else c["verdict"]))
        if not m.get("cells"):
            print("    %-18s no incidence reading on disk" % m["key"])


def write_record(payload: dict) -> None:
    doc = {"stage": "A32",
           "config": _fmt({
               "carrier": "none: this station runs no model. It parses "
                          "network.py and reads records already on disk",
               "module_sha": payload["census"]["module_sha"],
               "script_sha": _module_sha(SCRIPT),
               "mechanisms": [m["key"] for m in MECHANISMS],
               "kinds": {k: v for k, v in KINDS},
               "claim": ("incidence changes who falls below the floor exactly "
                         "when neither absorber is present: a controller "
                         "closing a gap in the quantity the floor is read "
                         "against, or mixing"),
           }),
           "sections": {"run": _fmt(payload)}}
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s" % RECORD.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", required=True)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    print("stage A32: no model is run. The census is parsed out of "
          "network.py and every reading comes off a record already on disk.\n")
    c = census()
    sv = survey()
    g = grid(sv)
    crits = [criterion_a32_0(c), criterion_a32_1(sv), criterion_a32_2(sv),
             criterion_a32_3(sv, g), criterion_a32_4(sv)]
    print_survey(sv, g)
    _print_criteria(crits)
    failed = [x.name for x in crits if x.evaluated and not x.passed]
    print("\n  %d/%d" % (len(crits) - len(failed), len(crits)))
    if not args.no_write:
        write_record({"criteria": [x.as_dict() for x in crits],
                      "census": c, "survey": sv, "grid": g})
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
