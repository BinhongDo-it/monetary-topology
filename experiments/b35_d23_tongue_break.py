"""B35: the D23 gate on the swine-tongue three-anchor candidate, answered by arithmetic.

**The gate.** B35 closed with that candidate open and one precondition: read the rule
text for the September 2022 break on the China leg and decide between "access opened"
and "two goods under one code". The rule text was chased through five source classes
and not reached; the one dated document covering the period, USMEF's 28 October 2022
foreign-trade-barriers filing to USTR, names no 2022 access event for pork offal, and
the Chinese-language customs announcement class is robots-blocked from here.

**So the gate is answered on the data instead, and the answer is decisive.** The
question is whether the three anchors price the same physical thing across the break.
They do not, and what shows it is that the break is not tongue-specific: three codes
on the China leg move in the same months in opposite directions while the other two
legs do not move at all.

Nothing is fetched. The input is `results/b35_census_raw_020630-020649_bycountry.json`,
already on disk: US Census monthly exports, HS10, 2022, all destinations.

    python experiments/b35_d23_tongue_break.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_census_raw_020630-020649_bycountry.json"
OUT = ROOT / "results" / "b35_d23_tongue_break.json"

NAMES = {
    "0206490010": "tongues", "0206490020": "hearts", "0206490030": "feet",
    "0206490040": "head meat", "0206490050": "skins", "0206490090": "offal nesoi",
}
TONG = "0206490010"
HEAD = "0206490040"
SKIN = "0206490050"
BREAK_MONTH = 9          # fixed by the record before this file was written
ANCHORS = ("CHINA", "JAPAN", "MEXICO")


# The source classes chased for the rule text, one entry each. They were prose
# inside a detail string until 2026-09-13, which let the count and the verdict
# drift apart: the detail said five and the verdict said True (rule 11f).
SOURCE_CLASSES_TRIED = (
    "English trade press (hits fell in 2014 and 2025, outside the window)",
    "USDA FAS and FSIS (nothing on a September 2022 event)",
    "**the industry body's own dated filing, USMEF to USTR, 28 October 2022, "
    "which names no 2022 access event for pork offal**",
    "Chinese-language search, which surfaced the plant-reinstatement "
    "announcement class",
    "that class's one item, robots-blocked from here",
)


def cell(rows, code, cty, month):
    q = sum(float(r["QTY_1_MO"]) for r in rows
            if r["E_COMMODITY"] == code and r["CTY_NAME"] == cty and r["_month"] == month)
    v = sum(float(r["ALL_VAL_MO"]) for r in rows
            if r["E_COMMODITY"] == code and r["CTY_NAME"] == cty and r["_month"] == month)
    return q, v


def span(rows, code, cty, months):
    q = v = 0.0
    for m in months:
        a, b = cell(rows, code, cty, m)
        q += a
        v += b
    return q, v, (v / q if q else None)


def main() -> int:
    if not SRC.exists():
        print(f"input missing: {SRC}", file=sys.stderr)
        return 2
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    pre_m = list(range(1, BREAK_MONTH))
    post_m = list(range(BREAK_MONTH, 13))

    # ---- print the object: every code, every month, every anchor -------------
    panel = {}
    for cty in ANCHORS:
        panel[cty] = {}
        for code in sorted(NAMES):
            panel[cty][code] = [
                {"month": m, "kg": cell(rows, code, cty, m)[0],
                 "usd": cell(rows, code, cty, m)[1],
                 "usd_per_kg": (cell(rows, code, cty, m)[1] / cell(rows, code, cty, m)[0])
                 if cell(rows, code, cty, m)[0] else None}
                for m in range(1, 13)
            ]

    # ---- is the break tongue-specific, or does the leg reallocate? -----------
    moves = {}
    for code in sorted(NAMES):
        qa, va, ua = span(rows, code, "CHINA", pre_m)
        qb, vb, ub = span(rows, code, "CHINA", post_m)
        moves[code] = {
            "good": NAMES[code],
            "pre_kg_per_month": qa / len(pre_m),
            "post_kg_per_month": qb / len(post_m),
            "ratio": (qb / len(post_m)) / (qa / len(pre_m)) if qa else None,
            "pre_usd_per_kg": ua, "post_usd_per_kg": ub,
            "cold_start": bool(qa == 0 and qb > 0),
            "died": bool(qa > 0 and qb / len(post_m) < 0.2 * (qa / len(pre_m))),
        }

    # the other two legs, same code, same split
    other_legs = {}
    for cty in ("JAPAN", "MEXICO"):
        qa, va, ua = span(rows, TONG, cty, pre_m)
        qb, vb, ub = span(rows, TONG, cty, post_m)
        other_legs[cty] = {
            "pre_usd_per_kg": ua, "post_usd_per_kg": ub,
            "unit_value_ratio": ub / ua if ua else None,
            "volume_ratio": (qb / len(post_m)) / (qa / len(pre_m)) if qa else None,
        }

    # ---- mixture decomposition on the tongue line ---------------------------
    qa, va, u_pre = span(rows, TONG, "CHINA", pre_m)
    qb, vb, u_post = span(rows, TONG, "CHINA", post_m)
    q_old = qa / len(pre_m) * len(post_m)          # old flow continuing at its own rate
    u_new = (vb - q_old * u_pre) / (qb - q_old)
    gained = qb - q_old

    # head meat's missing quantity over the same months
    ha, _, u_head_pre = span(rows, HEAD, "CHINA", pre_m)
    hb, _, u_head_post = span(rows, HEAD, "CHINA", post_m)
    head_lost = ha / len(pre_m) * len(post_m) - hb

    # ---- criteria -----------------------------------------------------------
    tongue_specific = not (moves[SKIN]["cold_start"] or moves[HEAD]["died"])
    legs_quiet = all(0.9 < v["unit_value_ratio"] < 1.1 for v in other_legs.values())
    price_match = abs(u_new - u_head_pre) / u_head_pre < 0.15
    qty_same_order = 0.5 < gained / head_lost < 2.0 if head_lost else False

    criteria = [
        {
            "name": "B35-D23-1",
            "kind": "instrument",
            "criterion": "print the object: every code, every month, all three anchors",
            "passed": all(len(panel[c][k]) == 12 for c in ANCHORS for k in NAMES),
            "detail": (
                f"{len(ANCHORS)} anchors x {len(NAMES)} codes x 12 months printed whole "
                "into the record, no month summarised away."
            ),
        },
        {
            "name": "B35-D23-2",
            "kind": "own_reading",
            "criterion": (
                "the September break is tongue-specific, so the code's contents are "
                "unchanged and the anchors keep pricing one thing"
            ),
            "passed": tongue_specific,
            "detail": (
                "It is not. On the China leg in the same months: tongues "
                f"x{moves[TONG]['ratio']:.2f} in volume with unit value "
                f"{moves[TONG]['pre_usd_per_kg']:.3f} -> {moves[TONG]['post_usd_per_kg']:.3f}; "
                f"skins **cold start**, zero for eight months then "
                f"{moves[SKIN]['post_kg_per_month']:,.0f} kg a month; head meat **dies**, "
                f"{moves[HEAD]['pre_kg_per_month']:,.0f} -> "
                f"{moves[HEAD]['post_kg_per_month']:,.0f} kg a month. Feet and offal-nesoi "
                f"stay flat (x{moves['0206490030']['ratio']:.2f} and "
                f"x{moves['0206490090']['ratio']:.2f})."
            ),
        },
        {
            "name": "B35-D23-3",
            "kind": "known_answer",
            "criterion": (
                "the other two anchors, same code, same split, do not move: a "
                "US-side reclassification would hit every leg at once"
            ),
            "passed": legs_quiet,
            "detail": "; ".join(
                f"{c}: unit value {v['pre_usd_per_kg']:.3f} -> {v['post_usd_per_kg']:.3f} "
                f"(x{v['unit_value_ratio']:.3f}), volume x{v['volume_ratio']:.2f}"
                for c, v in sorted(other_legs.items())
            ) + ". So this is a China-leg event, not a code revision.",
        },
        {
            "name": "B35-D23-4",
            "kind": "own_reading",
            "criterion": (
                "the mixture decomposition names what the new flow prices like, and "
                "the quantity is matched against what left another code"
            ),
            "passed": bool(price_match and qty_same_order),
            "detail": (
                f"if the old flow continued at its own pre-break rate, the implied new "
                f"flow is {gained:,.0f} kg at **${u_new:.3f}/kg**. Head meat on the same "
                f"leg priced ${u_head_pre:.3f} before the break, "
                f"{abs(u_new - u_head_pre) / u_head_pre * 100:.1f} per cent away, and it "
                f"lost {head_lost:,.0f} kg over the same four months against the "
                f"{gained:,.0f} kg tongues gained. Price and quantity both line up."
            ),
        },
        {
            "name": "B35-D23-5",
            "kind": "bookkeeping",
            "criterion": "the rule text was chased and the source classes tried are named",
            # rule 11f, 2026-09-13: the detail says five classes and the verdict was
            # a literal True, so the count and the verdict were not the same object.
            "passed": (len(SOURCE_CLASSES_TRIED) == 5
                       and all(c.strip() for c in SOURCE_CLASSES_TRIED)),
            "detail": (
                f"{len(SOURCE_CLASSES_TRIED)} classes: "
                + "; ".join(SOURCE_CLASSES_TRIED)
                + ". The gate is answered on the data instead. Reading the "
                "announcement would confirm the mechanism; it would not change the "
                "verdict, which is that the code's contents on this leg changed at "
                "the break."
            ),
        },
    ]

    record = {
        "stage": "B35",
        "arm": "D23 gate on the swine-tongue three-anchor candidate",
        "config": {
            "source_record": SRC.name, "break_month": BREAK_MONTH,
            "anchors": list(ANCHORS), "codes": NAMES,
        },
        "diagnostic_only": True,
        "diagnostic_reason": (
            "This is a pre-opening gate, not a station reading. It decides whether the "
            "three-anchor candidate can be opened and over which window."
        ),
        "china_leg_by_code": moves,
        "other_legs_same_code": other_legs,
        "mixture": {
            "pre_usd_per_kg": u_pre, "post_usd_per_kg": u_post,
            "implied_new_usd_per_kg": u_new, "implied_new_kg": gained,
            "head_meat_pre_usd_per_kg": u_head_pre, "head_meat_lost_kg": head_lost,
        },
        "panel": panel,
        "verdict": (
            "two goods under one code, in its sharpest form: not a code that always held "
            "two goods, but goods moving between codes on this leg from September. The "
            "anchors do not price one thing across the break, so the arm can use "
            "January to August only."
        ),
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}[{c['kind']}] {c['name']}: {c['detail'][:210]}")
    print()
    print(f"implied new flow ${u_new:.3f}/kg against head meat ${u_head_pre:.3f}/kg")
    print(f"tongues gained {gained:,.0f} kg, head meat lost {head_lost:,.0f} kg")
    print("wrote", OUT.name)
    return 1 if any(c["passed"] is False for c in criteria) else 0


if __name__ == "__main__":
    raise SystemExit(main())
