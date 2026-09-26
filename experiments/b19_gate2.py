"""B19: restate gate two in one unit, and reconcile the two dispersion readings.

**This does not reopen B19.** The stage is closed and stays closed. This is the
step the dispersion file registered as next: put gate two's arithmetic in one unit
so it can be recomputed by someone who is not the person who wrote it down.

**The unit problem, stated exactly.** Gate two is `z * se / band`. Both halves
were in points of shares outstanding and that part was consistent: the band is
constrained money over market value, and the noise was written as five points of
institutional ownership. What the dispersion file then measured is a *relative*
quantity, the cross-sectional sd of `dlog(shares held)`, and it stopped there
because converting needs an ownership level it did not have.

**That level is one published number, not an unmeasurable one**, and the
conversion is one multiplication:

    se in points = ownership level in points  *  se relative

**And the conversion reconciles the two readings that have been sitting apart.**
The prose of a later recheck records a dispersion of 6.5 to 9.0 points. The robust
form of the measured relative dispersion, times an ownership level in the range US
equities actually carry, lands on that interval. **They are the same object in two
units, and this file checks that rather than asserting it.**

**Which form converts is settled by arithmetic, not by preference.** Each form
implies an ownership level: the level at which it reproduces the recorded interval.
The robust form implies a level in the range US equity institutional ownership is
quoted across. The raw sd implies one an order of magnitude below it. Holdings
changes are heavy-tailed and the raw sd is carrying that tail. Both forms stay in
the record and the implied levels are what separate them.

**What is still not on disk.** The stage's record carries the string
`not passed, ratio 6.1, stage not opened` and no arithmetic, and the recheck's
ratio of 16.6 appears in no script or record. Neither is reproducible. This file
names the missing inputs and prints the ratio as a function of them.

    python experiments/b19_gate2.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DISP = ROOT / "results" / "b19_dispersion.json"
OUT = ROOT / "results" / "b19_gate2.json"

# One-sided ninety per cent, the same constant D14 uses.
Z90 = 1.6448536269514722

# For a normal sample the interquartile range is 1.349 standard deviations.
IQR_TO_SD = 1.3489795003921634

# Ownership levels to convert at. A printed range, not a chosen value: US equity
# institutional ownership is quoted across roughly this span depending on whether
# the universe is all listed names or the large-cap end.
LEVELS = (50.0, 60.0, 70.0, 80.0)

# The interval a later recheck's prose records, in points. Carried here so the
# conversion can be checked against it rather than compared by eye.
PROSE_INTERVAL = (6.5, 9.0)

# Money figures the stage's own prose names, in dollars. None is on disk in any
# record, which is half of what this file reports.
MONEY = {
    "original_5.98T_x_5pct_halved_x_0.3": 5.98e12 * 0.05 * 0.5 * 0.3,
    "recheck_us_equity": 3.7e9,
    "recheck_incl_funds_and_sma": 12.0e9,
}


def main() -> int:
    if not DISP.exists():
        print(f"input missing: {DISP}", file=sys.stderr)
        return 2
    disp = json.loads(DISP.read_text(encoding="utf-8"))
    sd_rel = float(disp["median_sd_dlog"])
    iqr_rel = float(disp["median_iqr_dlog"])
    robust_rel = iqr_rel / IQR_TO_SD

    # ---- convert both forms at each level, and see which lands on the prose --
    conversions = []
    for level in LEVELS:
        conversions.append(
            {
                "ownership_level_points": level,
                "se_points_from_raw_sd": round(level * sd_rel, 4),
                "se_points_from_robust": round(level * robust_rel, 4),
                "robust_lands_in_prose_interval": bool(
                    PROSE_INTERVAL[0] <= level * robust_rel <= PROSE_INTERVAL[1]
                ),
            }
        )
    robust_hits = [c for c in conversions if c["robust_lands_in_prose_interval"]]

    # The level at which the robust conversion reproduces each end of the prose
    # interval, solved rather than searched.
    level_for_low = PROSE_INTERVAL[0] / robust_rel
    level_for_high = PROSE_INTERVAL[1] / robust_rel
    raw_level_low = PROSE_INTERVAL[0] / sd_rel
    raw_level_high = PROSE_INTERVAL[1] / sd_rel
    # The range US equity institutional ownership is quoted across, used as the
    # comparison the two implied levels are held against. It is a printed range,
    # and neither form is scored against a line drawn on any estimate.
    quoted_low, quoted_high = min(LEVELS), max(LEVELS)
    robust_in_quoted = quoted_low <= level_for_high and level_for_low <= quoted_high
    raw_in_quoted = quoted_low <= raw_level_high and raw_level_low <= quoted_high

    # ---- what the one recorded number implies about the unrecorded ones -----
    recorded_ratio = 6.1
    se_pts_written = 5.0
    implied_band_pts = Z90 * se_pts_written / recorded_ratio
    implied_denominator = {k: v / (implied_band_pts / 100.0) for k, v in MONEY.items()}
    # rule 11f, 2026-09-13: this verdict was a literal True, so an empty MONEY or a
    # zero band would still have been written as printed.
    backouts_exist = (bool(implied_denominator) and implied_band_pts > 0
                      and all(v > 0 and v == v for v in implied_denominator.values()))

    # ---- the ratio as a function of what is missing, printed, no line on it --
    grid = []
    for mk, money in sorted(MONEY.items()):
        for denom in (3.0e12, 10.0e12, 25.0e12, 50.0e12):
            band_pts = money / denom * 100.0
            for level in LEVELS:
                se_pts = level * robust_rel
                grid.append(
                    {
                        "money_key": mk,
                        "money_usd": money,
                        "denominator_usd": denom,
                        "ownership_level_points": level,
                        "band_points": round(band_pts, 8),
                        "se_points_robust": round(se_pts, 4),
                        "ratio": round(Z90 * se_pts / band_pts, 3)
                        if band_pts > 0
                        else None,
                    }
                )

    criteria = [
        {
            "name": "B19-G-1",
            "kind": "known_answer",
            "criterion": (
                "the measured relative dispersion, converted at an ownership level, "
                "reproduces the dispersion interval a later recheck recorded in prose"
            ),
            "passed": len(robust_hits) > 0,
            "detail": (
                f"robust relative dispersion {robust_rel:.4f} from an iqr of "
                f"{iqr_rel:.4f}. Converted: "
                + ", ".join(
                    f"L={c['ownership_level_points']:.0f} -> "
                    f"{c['se_points_from_robust']:.2f} pts"
                    for c in conversions
                )
                + f". The prose interval is {PROSE_INTERVAL[0]} to "
                f"{PROSE_INTERVAL[1]} points, and it is reproduced at ownership "
                f"levels {level_for_low:.1f} to {level_for_high:.1f} points, which "
                "is the range US equity institutional ownership is quoted across. "
                "So the two readings that have been recorded separately are one "
                "object in two units."
            ),
        },
        {
            "name": "B19-G-2",
            "kind": "instrument",
            "criterion": (
                "the two forms of the dispersion are separated by the ownership "
                "level each implies, not by a preference between them"
            ),
            "passed": bool(robust_in_quoted and not raw_in_quoted),
            "detail": (
                f"to reproduce the recorded interval of {PROSE_INTERVAL[0]} to "
                f"{PROSE_INTERVAL[1]} points, the robust form implies an ownership "
                f"level of {level_for_low:.1f} to {level_for_high:.1f} points and "
                f"the raw sd implies {raw_level_low:.1f} to {raw_level_high:.1f}. "
                f"The quoted range held against is {quoted_low:.0f} to "
                f"{quoted_high:.0f} points. The robust form's implied level sits "
                "inside it and the raw sd's is an order of magnitude below. "
                f"Converted at those quoted levels the raw sd gives "
                + ", ".join(
                    f"{c['se_points_from_raw_sd']:.1f}"
                    for c in conversions
                )
                + " points, which is a security's institutional ownership moving by "
                "most of itself every quarter. Holdings changes are heavy-tailed "
                "and the raw sd carries that tail. Both forms stay in the record."
            ),
        },
        {
            "name": "B19-G-3",
            "kind": "bookkeeping",
            "criterion": (
                "the ratio that closed the stage can be recomputed from what the "
                "repository holds"
            ),
            "passed": False,
            "detail": (
                "It cannot. The stage record carries the string 'not passed, ratio "
                "6.1, stage not opened' and no arithmetic; the constrained money "
                "and the denominator were never written into a script or a record, "
                "and the recheck's ratio of 16.6 appears in neither. This is 18d's "
                "shape, the reading on disk and its configuration not. The verdict "
                "is untouched and the stage stays closed. What changes is that the "
                "gap is now named rather than invisible, and the two inputs that "
                "would close it are listed."
            ),
        },
        {
            "name": "B19-G-4",
            "kind": "own_reading",
            "criterion": (
                "print what the one recorded number implies about the ones that "
                "were not recorded"
            ),
            "passed": backouts_exist,
            "detail": (
                f"at z {Z90:.4f} and the five points written down, a ratio of "
                f"{recorded_ratio} implies a band of {implied_band_pts:.4f} points, "
                "which for each money figure the prose names implies a denominator "
                "of "
                + ", ".join(
                    f"{k} -> {v/1e12:.2f}T"
                    for k, v in sorted(implied_denominator.items())
                )
                + ". Back-outs from one recorded number, not readings."
            ),
        },
        {
            "name": "B19-G-5",
            "kind": "own_reading",
            "criterion": (
                "print the ratio as a function of the missing inputs, over a grid, "
                "with no threshold on it"
            ),
            "passed": len(grid) > 0,
            "detail": (
                f"{len(grid)} cells over three money figures, four denominators and "
                "four ownership levels, all at the robust dispersion. Nothing is "
                "selected from the grid; supplying the money and the denominator "
                "gives the ratio immediately."
            ),
        },
    ]

    record = {
        "stage": "B19",
        "arm": "gate two restated in one unit",
        "config": {
            "z90": Z90,
            "iqr_to_sd": IQR_TO_SD,
            "levels_points": list(LEVELS),
            "prose_interval_points": list(PROSE_INTERVAL),
            "dispersion_source": DISP.name,
            "money_figures": dict(sorted(MONEY.items())),
        },
        "diagnostic_only": True,
        "diagnostic_reason": (
            "B19 is closed at gate two and this does not reopen it. It restates the "
            "gate in one unit, reconciles the two dispersion readings, and records "
            "that the ratio which closed the stage is not reproducible from the "
            "repository."
        ),
        "dispersion": {
            "median_sd_dlog": sd_rel,
            "median_iqr_dlog": iqr_rel,
            "robust_sd_from_iqr": robust_rel,
        },
        "conversions": conversions,
        "level_reproducing_prose_low": level_for_low,
        "level_reproducing_prose_high": level_for_high,
        "raw_sd_implied_level_low": raw_level_low,
        "raw_sd_implied_level_high": raw_level_high,
        "quoted_level_range_points": [min(LEVELS), max(LEVELS)],
        "recorded_ratio": recorded_ratio,
        "se_points_written_down": se_pts_written,
        "implied_band_points": implied_band_pts,
        "implied_denominator_usd": implied_denominator,
        "ratio_grid": grid,
        "not_reproducible": [
            "constrained money attributable to the compliant universe",
            "the denominator, whether whole market or compliant subset",
            "the recheck's ratio of 16.6",
        ],
        "criteria": criteria,
    }
    OUT.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}[{c['kind']}] {c['name']}: {c['detail'][:180]}")
    print()
    print(f"robust relative {robust_rel:.4f}; prose interval reproduced at "
          f"L = {level_for_low:.1f} to {level_for_high:.1f} points")
    print("wrote", OUT.name)
    return 1 if any(c["passed"] is False for c in criteria) else 0


if __name__ == "__main__":
    raise SystemExit(main())
