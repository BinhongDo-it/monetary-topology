"""B2 placebo validation: is the VA borrower pool actually wide?

Pre-registered in ``docs/b2_placebo_pool_width.md``. Uses the samples already
retrieved for the graded placebo::

    python experiments/b2_placebo_pool_width.py
    python experiments/b2_placebo_pool_width.py --states CA TX   # quick subset

Writes ``results/b2_placebo_pool_width.json``. No figure: the output is a handful
of numbers per programme and a chart of a handful of numbers is decoration.

What is being validated
-----------------------
``docs/b2_measurement.md`` section 8 argues from programme rule that the VA pool
spans a range comparable to conventional and wider than FHA, and the whole graded
placebo rests on it. The argument was never measured. If the VA pool is in fact
narrow, the pool-width account reclaims the conventional-VA gap and the placebo
stops identifying anything.

Credit score is redacted in public HMDA and FHFA's NMDB aggregates pool FHA with
VA and USDA into one ``Government / Non-Conventional`` market, so neither source
can test the premise in the variable it is stated in. What is tested instead is
borrower **capacity**, on the same loans, using fields the retrieval kept.

The statistic is the within-cell dispersion, absolute
---------------------------------------------------
Loop A reports a within *share* because its question is whether a position-only
potential can reproduce a price field, and that question is inherently a ratio.
Pool width is not that question. "How spread out are the borrowers transacting at
this position" is the within-cell dispersion in the units of the attribute, and
dividing it by a total that also contains between-cell variance would let a
programme whose borrowers sort strongly across tracts look narrow at fixed
position when it is not. Shares are reported alongside and are not what the
criteria read.

Two dispersion measures, because one of them has a known weakness
----------------------------------------------------------------
Log income in this sample is right-tailed and conventional lending here includes
jumbo while FHA has the lowest county loan limits, so a variance in log income
gives conventional a tail no government programme is allowed to have. That runs
against the premise being confirmed, which is the right direction for a nuisance,
but it is large enough to be worth removing rather than signing.

So the same dispersion is computed a second time on the **within-programme rank**
of income, the device loop A already uses for its ranked analogue. Ranks are
bounded, so no tail can dominate, and each programme is ranked against its own
distribution so a level difference cannot enter. The criteria require the
conclusion on both.

Memory and passes
-----------------
A cell is keyed on year and census tract and a tract lies inside one state, so
every cell closes at the end of its state-year file and can be folded away. Three
passes: tract-years reached, then the income distribution over the common
tract-years, then the fold. Nothing holds the sample in memory.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.effective_price import (  # noqa: E402
    CELL_KEYS,
    MIN_CELL_SIZE,
    SPREAD_BOUND,
)
from monetary_topology.pool_width import (  # noqa: E402
    BoundFold,
    BucketAccumulator,
    MomentAccumulator,
    SplitFold,
    dti_bucket,
)

RESULTS = ROOT / "results"

PRODUCT_DIRS = {
    "conventional": "hmda",
    "fha": "hmda_fha",
    "va": "hmda_va",
}

#: Same convention as the loop A and placebo loaders. Files not matching are
#: skipped and reported rather than silently included, and nothing is deleted.
VALID_NAME = re.compile(r"^hmda_([A-Z]{2})_(20\d\d)\.csv$")
VALID_YEARS = range(2018, 2031)

#: Pre-registered in section 4 of the design document.
MIN_POOL_RATIO = 0.80
MAX_MISSING_SPREAD = 0.10

#: Plausibility bands, added after the first national run and recorded here
#: rather than presented as if they had always been there. Section 6 of the
#: design document is the changelog entry.
#:
#: What went wrong. The first national run reported a within-cell dispersion of
#: loan-to-value of 91,970,479 for conventional against 11,412 for VA. A ratio of
#: loan to value has no such number in it. The published columns carry rows at
#: 89,759 and 993,446, against a 99.99th percentile of about 130, so a handful of
#: rows in units that are not a percentage were carrying a headline. Income
#: carries the same shape: a maximum of 2,302,773, which in HMDA's thousands is
#: an annual income of 2.3 billion dollars.
#:
#: This is the same failure the project already hit once, on a rate spread of
#: -9999997 (`docs/b2_measurement.md` section 10), and the same remedy: state a
#: band, count what it removes, and sweep it so that no result rests on where
#: exactly it was put. The ranked measure was already immune, which is why it is
#: the one the discriminating criterion reads.
INCOME_BOUNDS: tuple[float, ...] = (1000.0, 10000.0, math.inf)
LTV_BOUNDS: tuple[float, ...] = (110.0, 150.0, math.inf)

#: The band the criteria read. The others are folded in the same pass so that
#: PW-8 can say whether the choice carries the verdict.
INCOME_BOUND = 10000.0
LTV_BOUND = 150.0


def income_field(bound: float) -> str:
    return f"log_income@{bound:g}"


def ltv_field(bound: float) -> str:
    return f"ltv@{bound:g}"


#: Fields folded. ``rate_spread`` is recomputed here rather than taken from the
#: placebo because the placebo's headline is unrestricted and every figure in a
#: comparison has to come off one sample.
CONTINUOUS: tuple[str, ...] = (
    "rate_spread",
    "rank_income",
    *(income_field(b) for b in INCOME_BOUNDS),
    *(ltv_field(b) for b in LTV_BOUNDS),
)

#: Minimum cell sizes folded in the same pass. The headline is
#: ``MIN_CELL_SIZE``; the others are folded because the threshold selects
#: **different** cells for each programme and the direction of that selection is
#: not obvious in advance.
#:
#: A programme's surviving cells are the ones where that programme is dense. VA
#: lending concentrates near installations, where pay scales compress the income
#: distribution, so the threshold plausibly narrows VA's measured pool. The sweep
#: is what turns "plausibly" into a measurement.
MIN_SIZES: tuple[int, ...] = (5, MIN_CELL_SIZE, 50)


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


@dataclass
class Level:
    """One minimum-cell-size threshold's worth of folds."""

    splits: dict[str, SplitFold] = field(
        default_factory=lambda: {k: SplitFold() for k in CONTINUOUS}
    )
    dti: BoundFold = field(default_factory=BoundFold)

    def within(self, key: str) -> float:
        """Within-cell dispersion, in the units of the field. The pool measure."""
        return self.splits[key].split().within

    def share(self, key: str) -> float:
        """Within share. Reported for continuity with loop A, not read by criteria."""
        return self.splits[key].split().within_share


@dataclass
class ProgrammeFold:
    """Everything accumulated for one programme, at every threshold."""

    product: str
    levels: dict[int, Level] = field(
        default_factory=lambda: {m: Level() for m in MIN_SIZES}
    )
    rows_in_common: int = 0
    missing: dict[str, int] = field(
        default_factory=lambda: {"income": 0, "dti": 0, "ltv": 0}
    )
    #: Rows carrying a positive number that is not a plausible value of the
    #: field, at the headline band. Counted separately from ``missing`` because
    #: an absent value and an impossible one are different defects.
    out_of_band: dict[str, int] = field(
        default_factory=lambda: {"income": 0, "ltv": 0}
    )
    files: int = 0

    def missing_rate(self, key: str) -> float:
        return self.missing[key] / self.rows_in_common if self.rows_in_common else 0.0

    def out_of_band_rate(self, key: str) -> float:
        share = self.out_of_band[key] / self.rows_in_common
        return share if self.rows_in_common else 0.0


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def files_for(product: str, states: tuple[str, ...] | None) -> list[Path]:
    directory = ROOT / "data" / "raw" / PRODUCT_DIRS[product]
    if not directory.exists():
        raise SystemExit(
            f"no data directory at {directory.relative_to(ROOT)}.\n"
            f"Run:  python data/fetch_hmda.py --product {product}"
        )
    keep, skipped = [], 0
    for path in sorted(directory.glob("*.csv")):
        match = VALID_NAME.match(path.name)
        if not match or int(match.group(2)) not in VALID_YEARS:
            skipped += 1
            continue
        if states and match.group(1) not in states:
            continue
        keep.append(path)
    if skipped:
        print(f"  {product}: skipped {skipped} file(s) off-convention")
    if not keep:
        raise SystemExit(f"no usable data for {product}")
    return keep


def rows(path: Path):
    """Rows of one slim HMDA file, with the completion marker skipped.

    The marker parses as a short row, which is why every loader in this
    repository guards on it rather than trusting the row count.
    """
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("activity_year", "").startswith("#"):
                continue
            yield row


def spread_of(row: dict) -> float | None:
    """The reported spread, or ``None`` if it is not an interest-rate difference.

    The plausibility band is ``effective_price.SPREAD_BOUND``, applied here so
    this sample is the placebo's sample and not a neighbouring one.
    """
    try:
        value = float(row["rate_spread"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(value) or abs(value) > SPREAD_BOUND:
        return None
    return value


def positive_float(text: str) -> float | None:
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0.0 else None


def in_common(row: dict, common: set[tuple[str, str]]) -> bool:
    return (row.get("census_tract", ""), row.get("activity_year", "")) in common


# ---------------------------------------------------------------------------
# Passes
# ---------------------------------------------------------------------------


def tract_years(paths: list[Path]) -> set[tuple[str, str]]:
    """Pass one: which tract-years this programme reaches at all."""
    seen: set[tuple[str, str]] = set()
    for path in paths:
        for row in rows(path):
            if spread_of(row) is None:
                continue
            seen.add((row.get("census_tract", ""), row.get("activity_year", "")))
    return seen


def income_histogram(paths: list[Path], common: set[tuple[str, str]]) -> Counter:
    """Pass two: the programme's own income distribution over the kept rows.

    Income is published in thousands and rounded, so the distinct values number
    in the thousands and a histogram is exact rather than an approximation of the
    empirical distribution.
    """
    hist: Counter = Counter()
    for path in paths:
        for row in rows(path):
            if spread_of(row) is None or not in_common(row, common):
                continue
            income = positive_float(row.get("income", ""))
            if income is not None and income <= INCOME_BOUND:
                hist[int(income)] += 1
    return hist


def rank_table(hist: Counter) -> tuple[list[int], list[float]]:
    """Tie-averaged rank in `(0, 1)` for each observed income value.

    Same convention as ``effective_price.average_ranks``: every member of a tie
    group takes the group's mean rank, so a value held by many borrowers cannot
    be spread across an interval it does not occupy.
    """
    values = sorted(hist)
    total = sum(hist.values())
    ranks: list[float] = []
    seen = 0
    for value in values:
        count = hist[value]
        ranks.append((seen + (count + 1) / 2.0) / total)
        seen += count
    return values, ranks


def accumulate(
    paths: list[Path],
    common: set[tuple[str, str]],
    values: list[int],
    ranks: list[float],
    product: str,
) -> ProgrammeFold:
    """Pass three: fold each file's cells into running totals and discard them."""
    out = ProgrammeFold(product=product)
    for path in paths:
        out.files += 1
        moments = {k: MomentAccumulator() for k in CONTINUOUS}
        buckets = BucketAccumulator()

        for row in rows(path):
            spread = spread_of(row)
            if spread is None or not in_common(row, common):
                continue
            out.rows_in_common += 1
            cell = "|".join(row.get(k, "") for k in CELL_KEYS)

            moments["rate_spread"].add(cell, spread)

            income = positive_float(row.get("income", ""))
            if income is None:
                out.missing["income"] += 1
            else:
                for bound in INCOME_BOUNDS:
                    if income <= bound:
                        moments[income_field(bound)].add(cell, math.log(income))
                if income <= INCOME_BOUND:
                    index = bisect.bisect_left(values, int(income))
                    moments["rank_income"].add(cell, ranks[index])
                else:
                    out.out_of_band["income"] += 1

            ltv = positive_float(row.get("loan_to_value_ratio", ""))
            if ltv is None:
                out.missing["ltv"] += 1
            else:
                for bound in LTV_BOUNDS:
                    if ltv <= bound:
                        moments[ltv_field(bound)].add(cell, ltv)
                if ltv > LTV_BOUND:
                    out.out_of_band["ltv"] += 1

            bucket = dti_bucket(row.get("debt_to_income_ratio", ""))
            if bucket < 0:
                out.missing["dti"] += 1
            else:
                buckets.add(cell, bucket)

        for min_size, level in out.levels.items():
            for key in CONTINUOUS:
                level.splits[key].absorb(moments[key], min_size)
            level.dti.absorb(buckets, min_size)

    return out


def report(fold: ProgrammeFold) -> dict:
    record: dict = {
        "files": fold.files,
        "rows_in_common_tract_years": fold.rows_in_common,
        "missing_rate": {k: fold.missing_rate(k) for k in fold.missing},
        "out_of_band_rate": {k: fold.out_of_band_rate(k) for k in fold.out_of_band},
        "out_of_band_rows": dict(fold.out_of_band),
        "by_min_cell_size": {},
    }
    for min_size, level in fold.levels.items():
        block: dict = {}
        for key in CONTINUOUS:
            split = level.splits[key].split()
            block[key] = {
                "within": split.within,
                "between": split.between,
                "within_share": split.within_share,
                "n_cells": split.n_cells,
                "n_loans": split.n_loans,
            }
        block["dti_within_cell_bound"] = {
            "bound": level.dti.bound,
            "n_cells": level.dti.n_cells,
            "n_loans": level.dti.n,
        }
        record["by_min_cell_size"][str(min_size)] = block
    return record


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------


def pool_holds(folds: dict[str, ProgrammeFold], key: str, min_size: int) -> bool:
    """PW-1 and PW-2's content at one threshold on one measure."""
    d = {p: folds[p].levels[min_size].within(key) for p in folds}
    if d["conventional"] <= 0:
        return False
    return d["va"] > d["fha"] and d["va"] / d["conventional"] >= MIN_POOL_RATIO


def evaluate(folds: dict[str, ProgrammeFold], headline: int) -> list[Criterion]:
    """The criteria of section 4, in the order they are registered."""

    def w(key: str) -> dict[str, float]:
        return {p: folds[p].levels[headline].within(key) for p in folds}

    log_inc = w(income_field(INCOME_BOUND))
    rank_inc = w("rank_income")
    ltv = w(ltv_field(LTV_BOUND))
    rate = w("rate_spread")
    dti = {p: folds[p].levels[headline].dti.bound for p in folds}

    out: list[Criterion] = []

    # A programme with no surviving cell reports a dispersion of exactly zero,
    # which reads as "this pool has no width" when it means "there is nothing
    # here to measure". Those are opposite conclusions and the difference is
    # invisible in the number, so it is checked rather than left to the reader.
    populated = {
        p: folds[p].levels[headline].splits["rank_income"].split().n_loans
        for p in folds
    }
    out.append(
        Criterion(
            "PW-0  every programme has cells at the headline threshold",
            all(v > 0 for v in populated.values()),
            "loans in cells of at least "
            + f"{headline}: "
            + ", ".join(f"{p} {v:,}" for p, v in populated.items())
            + ". A programme with none reports zero dispersion, which is an "
            "absence and not a narrow pool, and every criterion below would "
            "read it as the second",
        )
    )

    out.append(
        Criterion(
            "PW-1  the VA pool is wider than the FHA pool",
            log_inc["va"] > log_inc["fha"] and rank_inc["va"] > rank_inc["fha"],
            f"within-cell dispersion, log income: VA {log_inc['va']:.5f} against "
            f"FHA {log_inc['fha']:.5f}, conventional {log_inc['conventional']:.5f}; "
            f"ranked income: VA {rank_inc['va']:.5f} against FHA "
            f"{rank_inc['fha']:.5f}, conventional {rank_inc['conventional']:.5f}",
        )
    )

    ratios = {
        "log income": log_inc["va"] / log_inc["conventional"]
        if log_inc["conventional"] > 0
        else 0.0,
        "ranked income": rank_inc["va"] / rank_inc["conventional"]
        if rank_inc["conventional"] > 0
        else 0.0,
    }
    out.append(
        Criterion(
            "PW-2  the VA pool is comparable to the conventional pool",
            all(v >= MIN_POOL_RATIO for v in ratios.values()),
            "VA over conventional: "
            + ", ".join(f"{k} {v:.4f}" for k, v in ratios.items())
            + f", against the registered floor {MIN_POOL_RATIO:.2f}. Loan-limit "
            "truncation biases the log-income ratio down and cannot touch the "
            "ranked one",
        )
    )

    r = {
        p: (rate[p] / rank_inc[p] if rank_inc[p] > 0 else float("inf")) for p in folds
    }
    out.append(
        Criterion(
            "PW-3  the graded grid converts pool width into rate dispersion",
            r["conventional"] > r["va"] and r["conventional"] > r["fha"],
            f"rate dispersion per unit of ranked-income dispersion: conventional "
            f"{r['conventional']:.3f}, VA {r['va']:.3f}, FHA {r['fha']:.3f}. A "
            f"pure pool-width account makes this ratio constant across programmes",
        )
    )

    out.append(
        Criterion(
            "PW-4  debt-to-income does not contradict the premise",
            dti["va"] >= dti["fha"],
            f"within-cell variance lower bound: VA {dti['va']:.4f}, FHA "
            f"{dti['fha']:.4f}, conventional {dti['conventional']:.4f}. FHA and "
            f"VA underwrite to higher ceilings, which inflates both, so a pass "
            f"here is weak and only a failure would be strong",
        )
    )

    worst_key, worst_gap = "income", 0.0
    for key in ("income", "dti"):
        rates = [folds[p].missing_rate(key) for p in folds]
        mean = sum(rates) / len(rates)
        gap = max(abs(x - mean) for x in rates)
        if gap > worst_gap:
            worst_key, worst_gap = key, gap
    out.append(
        Criterion(
            "PW-5  the three samples are comparable at all",
            worst_gap <= MAX_MISSING_SPREAD,
            f"largest deviation from the mean missing rate is {worst_gap:.4f} on "
            f"{worst_key} against {MAX_MISSING_SPREAD:.2f}; income "
            + ", ".join(f"{p} {folds[p].missing_rate('income'):.4f}" for p in folds)
            + "; dti "
            + ", ".join(f"{p} {folds[p].missing_rate('dti'):.4f}" for p in folds),
        )
    )

    out.append(
        Criterion(
            "PW-6  negative control: the down-payment rules pin loan-to-value",
            ltv["conventional"] > ltv["va"] and ltv["conventional"] > ltv["fha"],
            f"within-cell dispersion of LTV: conventional {ltv['conventional']:.3f}, "
            f"VA {ltv['va']:.3f}, FHA {ltv['fha']:.3f}. A check on the instrument "
            f"and not on the pool: the rules pin LTV for both government "
            f"programmes and a method that cannot see that is not measuring "
            f"dispersion. A failure voids the rest",
        )
    )

    verdicts = {
        (m, key): pool_holds(folds, key, m)
        for m in MIN_SIZES
        for key in (income_field(INCOME_BOUND), "rank_income")
    }
    out.append(
        Criterion(
            "PW-7  the minimum-size threshold is not carrying the verdict",
            len(set(verdicts.values())) == 1,
            "PW-1 and PW-2 together, evaluated at every folded threshold: "
            + "; ".join(
                f"{key} at {m} {'holds' if v else 'fails'}"
                for (m, key), v in verdicts.items()
            ),
        )
    )

    banded = {b: pool_holds(folds, income_field(b), headline) for b in INCOME_BOUNDS}
    ltv_range = {
        b: {p: folds[p].levels[headline].within(ltv_field(b)) for p in folds}
        for b in LTV_BOUNDS
    }
    out.append(
        Criterion(
            "PW-8  the plausibility band is not carrying the verdict",
            len(set(banded.values())) == 1,
            "PW-1 and PW-2 on log income at each income band: "
            + "; ".join(f"{b:g} {'holds' if v else 'fails'}" for b, v in banded.items())
            + ". Rows removed at the headline band: "
            + ", ".join(
                f"{p} income {folds[p].out_of_band_rate('income'):.6f}, "
                f"ltv {folds[p].out_of_band_rate('ltv'):.6f}"
                for p in folds
            )
            + ". LTV dispersion by band, conventional: "
            + ", ".join(
                f"{b:g} {ltv_range[b]['conventional']:.3f}" for b in LTV_BOUNDS
            ),
        )
    )
    return out


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--headline",
        type=int,
        default=MIN_CELL_SIZE,
        choices=MIN_SIZES,
        help="which folded threshold the criteria read; the others are reported",
    )
    parser.add_argument(
        "--states",
        nargs="*",
        default=None,
        help="two-letter codes; a subset for a quick run, never for a reported figure",
    )
    args = parser.parse_args()
    states = tuple(args.states) if args.states else None

    print("B2 placebo validation: pool width at fixed position")
    print(
        f"  min cell sizes {MIN_SIZES}, headline {args.headline}, "
        f"spread band +/-{SPREAD_BOUND}"
    )
    if states:
        print(f"  SUBSET RUN, states {' '.join(states)}: not a reportable figure")
    print()

    paths = {p: files_for(p, states) for p in PRODUCT_DIRS}

    print("pass 1: tract-years reached by each programme")
    reached = {p: tract_years(g) for p, g in paths.items()}
    for product, seen in reached.items():
        print(f"  {product:<13} {len(seen):>9,} tract-years")
    common = set.intersection(*reached.values())
    print(f"  common to all three {len(common):>9,}\n")

    print("pass 2 and 3: income ranks, then the fold")
    folds = {}
    for product, group in paths.items():
        values, ranks = rank_table(income_histogram(group, common))
        folds[product] = accumulate(group, common, values, ranks, product)
        f = folds[product]
        print(
            f"  {product:<13} {f.files:>3} files, "
            f"{f.rows_in_common:>10,} loans in common tract-years, "
            f"{len(values):>5,} distinct incomes"
        )
    print()

    criteria = evaluate(folds, args.headline)
    print("criteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    # A subset run goes to ``results/subset/``, which ``render_results.py`` does
    # not reach because its glob is not recursive. A state subset is a smoke test
    # and letting one render into RESULTS.md beside the national figure would put
    # two numbers with the same stage name in front of a reader.
    directory = RESULTS / "subset" if states else RESULTS
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / "b2_placebo_pool_width.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B2A-poolwidth",
                "min_cell_size": args.headline,
                "min_cell_sizes_folded": list(MIN_SIZES),
                "spread_bound": SPREAD_BOUND,
                "registered_min_pool_ratio": MIN_POOL_RATIO,
                "income_bound": INCOME_BOUND,
                "income_bounds_folded": [
                    None if math.isinf(b) else b for b in INCOME_BOUNDS
                ],
                "ltv_bound": LTV_BOUND,
                "ltv_bounds_folded": [None if math.isinf(b) else b for b in LTV_BOUNDS],
                "states_subset": list(states) if states else None,
                "common_tract_years": len(common),
                "programmes": {p: report(f) for p, f in folds.items()},
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
