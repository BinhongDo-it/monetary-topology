"""A1d: the cascade on a measured cushion. Evaluates, designs nothing.

Registered in ``docs/a1d_prereg.md``, fixed 2026-08-16 before a value of ``LIQ``
was read. Two things change from A1b and the criteria are arranged so the two
can be told apart afterwards:

* **the cushion**, from one month of a household's own bills to its measured
  liquid assets with no floor (§3);
* **the window**, from "ever missed over sixty periods" to "sixty days behind
  inside a twelve-month window" (§4).

Usage::

    python experiments/a1d_measured_cushion.py
    python experiments/a1d_measured_cushion.py --households 20000
    python experiments/a1d_measured_cushion.py --cushion-report   # and stop

Writes ``results/a1d_measured_cushion.json``.

What this file inherits and why by import
-------------------------------------------
`docs/a1d_prereg.md` §6.1 says five of A1b's criteria are inherited **unchanged
in statement**. They are therefore inherited as the same code rather than
restated here, because a restatement drifts and a criterion that drifted would
be a different criterion wearing A1b's name. What this file writes for itself is
what the registration writes for itself: the window quantity, the resolution
rule, A1d-1, A1d-2 and the parameter count.

A1b's own record is untouched by any of this. Its cushion is
``Cushion.SCHEDULED``, which is still the default, and it never reads the
``liquid`` field its records now carry.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from monetary_topology.cascade import (  # noqa: E402
    CascadeModel,
    CostRule,
    Cushion,
    HouseholdRecord,
    Obligation,
    baseline_stress,
    build_from_records,
    distinct_records,
    literature_parameters,
    record_of_each,
)
from monetary_topology.income_path import (  # noqa: E402
    PathSpec,
    describe,
    retention_path,
)
from monetary_topology.scf import GROUPS  # noqa: E402
from monetary_topology.scf_joint import (  # noqa: E402
    JointSelection,
    Respondent,
    rank_groups,
    read_respondents,
)

from experiments.a1b_default_cascade import (  # noqa: E402
    ARCHIVE,
    BASELINE_PERIODS,
    FREE_PARAMETER_BOUND,
    LOAN_CLASSES,
    PATH_SEED,
    RENTER_FLOOR,
    SCORED_PERIODS,
    SELECTION,
    SWEEP_MONTHS_PER_ROUND,
    SWEEP_SEEDS,
    ZERO_PERIODS,
    Criterion,
    InputProblem,
    _monotone,
    a1_2,
    a1_3,
    a1_6,
    a1_9,
    a1_10,
    a1b_0,
    basket_by_decile,
    default_jobs,
    first_default_shares,
    flat_path,
    late60_by_group,
    ordering,
    relieved,
    to_records,
)

RESULTS = ROOT / "results"

#: A1-10's licence again: households do not interact, so the size is an
#: estimation setting. Same default as A1b so the two stages' populations are
#: the same population.
DEFAULT_HOUSEHOLDS = 100_000

#: ``docs/a1d_prereg.md`` §5. The sweep's size is **forced** by the model-side
#: resolution floor rather than chosen: at 20,000 the ``next9`` group holds about
#: 1,895 households and the target's own rate would put 4.2 events in it, under
#: the floor of five. At 50,000 the same group gives about 10.4.
DEFAULT_SWEEP_HOUSEHOLDS = 50_000

#: §5, model side. A group producing fewer than this many expected events under
#: the target's own rate has produced a rounding rather than a rate.
EXPECTED_EVENT_FLOOR = 5.0

#: §5, target side. Two standard errors of the adjacent difference, the standard
#: error naive binomial on the family count. Naive is the conservative direction
#: here: it ignores the SCF's design effect, so it admits **more** pairs than a
#: design-corrected rule would and is therefore harder on the model.
PAIR_SIGMA = 2.0

#: The extract carries five implicates of each family, so a count of rows is
#: five times a count of families and a standard error taken on rows would be
#: the sampling error of an imputation rather than of a survey.
IMPLICATES = 5

#: §4. The scored window is the run's last twelve periods.
WINDOW_MONTHS = 12


# ---------------------------------------------------------------------------
# §4. The window quantity
# ---------------------------------------------------------------------------
def behind_in_window(households: list, classes, n_groups: int,
                     start: int | None, end: int | None = None) -> list[float]:
    """Share of each group sixty days behind on any of ``classes`` in a window.

    ``docs/a1d_prereg.md`` §4. Sixty days is two consecutive missed due dates on
    ``CascadeSpec``'s one-month-per-period convention, and the model records the
    first and the last period at which each class stood there.

    ``start=None`` reads the whole run, which is the A1b-comparable reading.
    A window ``[start, end]`` is answered by the two integers alone: the class
    was there inside the window when ``last_sixty >= start`` and
    ``first_sixty <= end``. No trace is stored and none is needed.

    The group count is passed rather than inferred, for the reason
    ``a1b_default_cascade.ever_behind_by_group`` records: a population too small
    to give a group a member would return fewer numbers than the target has, and
    the two would be compared as orderings of different lengths.
    """
    behind = [0] * n_groups
    total = [0] * n_groups

    def hit(house, kind: Obligation) -> bool:
        first = house.first_sixty.get(kind)
        if first is None:
            return False
        if start is None:
            return True
        if end is not None and first > end:
            return False
        return house.last_sixty.get(kind, first) >= start

    for house in households:
        total[house.stratum] += 1
        if any(hit(house, k) for k in classes):
            behind[house.stratum] += 1
    return [b / t if t else 0.0 for b, t in zip(behind, total, strict=True)]


def ever_missed_by_group(households: list, classes,
                         n_groups: int) -> list[float]:
    """A1b-1's exact quantity, any missed payment over the whole run.

    Carried so the two stations are comparable at all. It is what A1b published
    and it is the reading §4 registers as reported and never scored.
    """
    behind = [0] * n_groups
    total = [0] * n_groups
    for house in households:
        total[house.stratum] += 1
        if any(house.ever_missed.get(k, False) for k in classes):
            behind[house.stratum] += 1
    return [b / t if t else 0.0 for b, t in zip(behind, total, strict=True)]


# ---------------------------------------------------------------------------
# §5. The resolution rule
# ---------------------------------------------------------------------------
def target_with_counts(respondents: list[Respondent]) -> dict[str, list]:
    """``LATE60`` by net-worth group, with the sample behind each figure.

    The rate alone cannot say whether an adjacent pair is resolvable, and A1b-1
    failed on a pair separated by four basis points and eleven households
    against five. The counts travel with the rates from here on.
    """
    groups = rank_groups(respondents, "networth")
    weight = [0.0] * len(GROUPS)
    behind = [0.0] * len(GROUPS)
    rows = [0] * len(GROUPS)
    reporting = [0] * len(GROUPS)
    for person, group in zip(respondents, groups, strict=True):
        weight[group] += person.weight
        behind[group] += person.weight * person.extra.get("LATE60", 0.0)
        rows[group] += 1
        if person.extra.get("LATE60", 0.0) > 0.0:
            reporting[group] += 1
    rate = [b / w if w else 0.0 for b, w in zip(behind, weight, strict=True)]
    families = [n / IMPLICATES for n in rows]
    return {
        "rate": rate,
        "families": families,
        "rows": rows,
        "reporting_rows": reporting,
        "standard_error": [
            math.sqrt(p * (1.0 - p) / f) if f > 0 else float("inf")
            for p, f in zip(rate, families, strict=True)
        ],
    }


def scorable_pairs(target: dict[str, list],
                   sizes: list[int]) -> tuple[list[int], list[dict]]:
    """Which adjacent pairs both sides can resolve. ``docs/a1d_prereg.md`` §5.

    Returns the indices of the admitted pairs and a row per pair saying why it
    was admitted or not. A pair the source cannot resolve is not evidence about
    the model, and gating on one is `MEASUREMENT.md` checklist item 8: a guard
    that would say the same thing if the thing it guards were broken.
    """
    admitted: list[int] = []
    rows: list[dict] = []
    n = len(target["rate"])
    for i in range(n - 1):
        gap = target["rate"][i] - target["rate"][i + 1]
        sigma = math.hypot(target["standard_error"][i],
                           target["standard_error"][i + 1])
        sigmas = abs(gap) / sigma if sigma > 0 else 0.0
        expected = [sizes[j] * target["rate"][j] for j in (i, i + 1)]
        source_ok = sigmas >= PAIR_SIGMA
        model_ok = min(expected) >= EXPECTED_EVENT_FLOOR
        if source_ok and model_ok:
            admitted.append(i)
        rows.append({
            "pair": f"{GROUPS[i]}/{GROUPS[i + 1]}",
            "gap": gap,
            "sigmas": sigmas,
            "expected_events": expected,
            "source_resolves": source_ok,
            "model_resolves": model_ok,
            "scored": source_ok and model_ok,
        })
    return admitted, rows


def a1d_1(respondents: list[Respondent], sweep: list[dict],
          households: int) -> tuple[Criterion, dict]:
    """The delinquency gradient on a matched window, on resolvable pairs only.

    ``docs/a1d_prereg.md`` §6.3. Ordinal, the direction 卷一·十八's, required in
    every cell of A1b's registered sweep. **Still not a level**, and §6.3 refuses
    that reading in advance: the model runs a shock scenario over sixty months
    and the survey asks about the twelve months before a 2022 interview. Matching
    the window makes the two the same kind of quantity and not the same year.
    """
    target = target_with_counts(respondents)
    sizes = sweep[0]["sizes"]
    empty = [GROUPS[g] for g, n in enumerate(sizes) if n == 0]
    if empty:
        return Criterion(
            "A1d-1 the delinquency gradient, matched window", False,
            f"{households:,} households leaves {', '.join(empty)} with no "
            f"member. Run at a size that fills every group",
            True,
        ), {"target": target, "cells": [], "pairs": [], "group_sizes": sizes}

    admitted, pair_rows = scorable_pairs(target, sizes)
    if not admitted:
        return Criterion(
            "A1d-1 the delinquency gradient, matched window", False,
            "no adjacent pair is resolvable on both sides, so there is no "
            "ordinal statement left to make. "
            + "; ".join(f"{r['pair']} {r['sigmas']:.2f}sigma, expected "
                        f"{min(r['expected_events']):.1f}" for r in pair_rows),
            True,
        ), {"target": target, "cells": [], "pairs": pair_rows,
            "group_sizes": sizes}

    def holds(model: list[float]) -> bool:
        return all(model[i] > model[i + 1] for i in admitted)

    def matches(model: list[float]) -> bool:
        want = ordering([target["rate"][i] for i in _touched(admitted)])
        got = ordering([model[i] for i in _touched(admitted)])
        return want == got

    cells = [
        {
            "seed": cell["seed"],
            "months_per_round": cell["months_per_round"],
            "window": cell["window"],
            "first_window": cell["first_window"],
            "whole_run": cell["whole_run"],
            "ever_missed": cell["ever_missed"],
            "window_with_rent": cell["window_with_rent"],
            "decreasing": holds(cell["window"]),
            "matches": matches(cell["window"]),
        }
        for cell in sweep
    ]
    decreasing = all(c["decreasing"] for c in cells)
    matched = all(c["matches"] for c in cells)

    detail = (
        "LATE60 by net worth: "
        + ", ".join(
            f"{GROUPS[g]} {target['rate'][g]:.4f} "
            f"({target['reporting_rows'][g]} of {target['families'][g]:,.0f} "
            f"families)"
            for g in range(len(GROUPS))
        )
        + ". Scored pairs: "
        + ", ".join(pair_rows[i]["pair"] for i in admitted)
        + ". Reported and not scored: "
        + (", ".join(f"{r['pair']} ({r['sigmas']:.2f} sigma, expected events "
                     f"{min(r['expected_events']):.1f})"
                     for i, r in enumerate(pair_rows) if i not in admitted)
           or "none")
        + f". Model on the last {WINDOW_MONTHS} periods over {len(cells)} "
          f"sweep cells: "
        + "; ".join(
            f"seed {c['seed']}x{c['months_per_round']} "
            + "/".join(f"{v:.3f}" for v in c["window"])
            + ("" if c["decreasing"] and c["matches"] else "  <-")
            for c in cells
        )
        + f". Decreasing on every scored pair in every cell: {decreasing}. "
          f"Ordering matches the survey on those groups in every cell: "
          f"{matched}"
        + f". Group sizes at {households:,}: {sizes}"
        + ". Reported and never scored, the other three windows on cell one: "
        + f"first {WINDOW_MONTHS} periods "
        + "/".join(f"{v:.3f}" for v in cells[0]["first_window"])
        + "; whole run at sixty days "
        + "/".join(f"{v:.3f}" for v in cells[0]["whole_run"])
        + "; whole run on A1b-1's any-miss rule "
        + "/".join(f"{v:.3f}" for v in cells[0]["ever_missed"])
        + "; last window including rent "
        + "/".join(f"{v:.3f}" for v in cells[0]["window_with_rent"])
    )
    return Criterion("A1d-1 the delinquency gradient, matched window",
                     decreasing and matched, detail), {
        "target": target, "cells": cells, "pairs": pair_rows,
        "group_sizes": sizes, "scored_pairs": admitted,
    }


def _touched(admitted: list[int]) -> list[int]:
    """The groups the admitted pairs speak about, in order and without repeats."""
    out: list[int] = []
    for i in admitted:
        for g in (i, i + 1):
            if g not in out:
                out.append(g)
    return out


# ---------------------------------------------------------------------------
# §6.4. A1d-2. The rent gradient, on net worth alone
# ---------------------------------------------------------------------------
def renter_gradient_by(households: list, by: str) -> tuple[list, list[str]]:
    """Renter arrears by group on one ranking, thin groups named and excluded.

    A1b's function, restated here only because A1d reads the sixty-day event
    rather than any missed payment, and the two would otherwise be two different
    quantities under one name.
    """
    rates: list[tuple[int, float, int]] = []
    excluded: list[str] = []
    for group in range(len(GROUPS)):
        renters = [h for h in households
                   if h.started_renting
                   and (h.stratum if by == "wealth" else h.income_group) == group]
        if len(renters) < RENTER_FLOOR:
            excluded.append(f"{GROUPS[group]} ({len(renters)} renters)")
            continue
        behind = sum(1 for h in renters
                     if h.first_sixty.get(Obligation.RENT) is not None)
        rates.append((group, behind / len(renters), len(renters)))
    return rates, excluded


def renter_families(records: list[HouseholdRecord], households: int,
                    built: list) -> list[dict]:
    """How many distinct SCF **families** stand behind each renter cell.

    ``docs/a1d_prereg.md`` §10, 2026-08-16, ruling 丙. Reported and never
    scored. ``RENTER_FLOOR`` counts model households, which are copies twice
    over: the extract carries five implicates of each family, and the allocation
    then hands weight-proportional copies to each implicate. A cell of 37 model
    renters can be seven families, and a floor that cannot see the difference is
    not doing the job a floor is for.

    A family is the implicate block a record sits in, which is its index over
    :data:`IMPLICATES`, the same divisor the standard errors in §5 use.
    """
    owner = record_of_each(records, households)
    families: dict[int, set[int]] = {}
    rows: dict[int, int] = {}
    counts: dict[int, int] = {}
    behind: dict[int, int] = {}
    for house, index in zip(built, owner, strict=True):
        if not house.started_renting:
            continue
        group = house.stratum
        families.setdefault(group, set()).add(index // IMPLICATES)
        rows[group] = rows.get(group, 0) + 1
        counts[group] = counts.get(group, 0) + 1
        if house.first_sixty.get(Obligation.RENT) is not None:
            behind[group] = behind.get(group, 0) + 1
    return [
        {
            "group": GROUPS[g],
            "model_renters": counts.get(g, 0),
            "families": len(families.get(g, ())),
            "behind": behind.get(g, 0),
            "clears_a_family_floor": len(families.get(g, ())) >= RENTER_FLOOR,
        }
        for g in range(len(GROUPS))
        if counts.get(g, 0)
    ]


def print_families(rows: list[dict], by_wealth) -> None:
    """The counterfactual verdict, printed and taken by nothing.

    A1d-2 is scored as it is registered, on model renters. This says what the
    same criterion would have said under a floor counting families, because a
    verdict that turns on which of two counts a floor uses should not be
    invisible in the output.
    """
    print("\nthe renter cells by distinct SCF family. docs/a1d_prereg.md "
          "section 10, ruling 丙: reported, scored on nothing")
    print(f"    {'group':<10}{'model renters':>15}{'families':>11}"
          f"{'behind':>9}{'clears floor':>14}")
    for row in rows:
        print(f"    {row['group']:<10}{row['model_renters']:>15,}"
              f"{row['families']:>11,}{row['behind']:>9,}"
              f"{'yes' if row['clears_a_family_floor'] else 'no':>14}")
    kept = {row["group"] for row in rows if row["clears_a_family_floor"]}
    survivors = [(g, rate) for g, rate, _ in by_wealth if GROUPS[g] in kept]
    verdict = (
        "monotone" if len(survivors) >= 2 and all(
            a >= b for (_, a), (_, b) in zip(survivors, survivors[1:])
        ) and survivors[0][1] > survivors[-1][1] else "NOT monotone"
    )
    print(f"    on the groups clearing a floor of {RENTER_FLOOR} families, "
          f"A1d-2 would read {verdict}. **It is not scored that way.** The "
          f"criterion stands on its registered count, and this line exists so "
          f"that the difference between the two is on the record rather than "
          f"in a decision nobody can see")


def a1d_2(by_wealth, dropped_wealth, by_income, dropped_income) -> Criterion:
    """Monotone decreasing in **net worth**, and that ranking alone.

    ``docs/a1d_prereg.md`` §6.4. A1-7 named two rankings, they disagreed, and
    naming two was the defect; the diagnosis of why they disagreed is
    ``docs/a1b_prereg.md`` §8 under 2026-08-16. Net worth is the ranking this
    thesis is about and §3's measured cushion is what gives it a channel into
    behaviour at all.

    **This criterion is the test of §3.** A pass says a measured cushion
    produced the monotonicity a label could not. A failure says the
    non-monotonicity belongs to the data rather than to the missing channel.

    The income ranking is printed and scored on nothing.
    """
    if len(by_wealth) < 2:
        return Criterion(
            "A1d-2 the rent gradient, on net worth", False,
            f"fewer than two net-worth groups clear {RENTER_FLOOR} renters, so "
            f"the gradient is undefined rather than refuted", True)

    holds = _monotone(by_wealth)

    def show(rates, dropped) -> str:
        body = ", ".join(f"{GROUPS[g]} {rate:.4f} ({n:,})"
                         for g, rate, n in rates)
        if dropped:
            body += f"; excluded below {RENTER_FLOOR}: " + ", ".join(dropped)
        return body

    detail = (
        f"by net worth, sixty days: {show(by_wealth, dropped_wealth)} "
        f"[{'monotone' if holds else 'NOT monotone'}]. Reported and not scored, "
        f"by income: {show(by_income, dropped_income)}"
    )
    if not holds:
        detail += (
            ". A measured cushion did not produce the monotonicity a label "
            "could not, so the non-monotonicity is a property of the data. "
            "docs/a1b_prereg.md section 8 has what the cells are made of"
        )
    return Criterion("A1d-2 the rent gradient, on net worth", holds, detail)


# ---------------------------------------------------------------------------
# §6.5. A1d-3. The free-parameter bound, one shorter than A1b's
# ---------------------------------------------------------------------------
def free_list(cost: CostRule) -> list[tuple[str, float]]:
    """Four. ``population.buffer_months`` is gone, replaced by a measurement."""
    return [
        ("cost.commute_dependency", cost.commute_dependency),
        ("cost.access_penalty", cost.access_penalty),
        ("cost.grace_basket", float(cost.grace_basket)),
        ("cost.grace_rent", float(cost.grace_rent)),
    ]


def a1d_3(cost: CostRule) -> Criterion:
    free = free_list(cost)
    return Criterion(
        "A1d-3 free parameters within the registered bound",
        len(free) <= FREE_PARAMETER_BOUND,
        f"{len(free)} free against {FREE_PARAMETER_BOUND}: "
        + ", ".join(f"{n}={v:g}" for n, v in free)
        + ". A1b counted five; population.buffer_months left the list when the "
          "cushion became a measurement rather than a choice",
    )


# ---------------------------------------------------------------------------
# The runs
# ---------------------------------------------------------------------------
def _task(job: dict) -> dict:
    """One whole run in one process, on a measured cushion.

    The answer does not depend on the worker count, for the reason
    ``a1b_default_cascade._task`` records at length: each task builds its own
    population by the same deterministic allocation and runs it whole.
    """
    records = job["records"]
    cost = CostRule()
    households = build_from_records(records, job["households"], cost,
                                    cushion=Cushion.MEASURED)
    if job["kind"] == "relieved":
        households = relieved(households, cost)
    result = CascadeModel(households, cost).run(job["path"])

    out: dict = {"kind": job["kind"], "result": result}
    if job["kind"] == "scored":
        out["renter_families"] = renter_families(records, job["households"],
                                                 households)
        short = [sum(h.due.values()) > h.income for h in households]
        clear = [h for h, s in zip(households, short, strict=True) if not s]
        defaulting = [h for h in clear if h.first_default is not None]
        if defaulting:
            n = len(defaulting)
            counts = {k: sum(1 for h in defaulting if h.first_default is k)
                      for k in Obligation}
            out["unstressed"] = {
                "n": n,
                "card": counts[Obligation.CARD] / n,
                "auto": counts[Obligation.AUTO] / n,
                "shelter": (counts[Obligation.RENT]
                            + counts[Obligation.MORTGAGE]) / n,
            }
            out["unstressed"]["holds"] = (
                out["unstressed"]["card"] > out["unstressed"]["auto"]
                > out["unstressed"]["shelter"]
            )
        out["by_wealth"] = renter_gradient_by(households, "wealth")
        out["by_income"] = renter_gradient_by(households, "income")
    elif job["kind"] == "sweep":
        n = len(GROUPS)
        start = job["periods"] - WINDOW_MONTHS
        out["seed"] = job["seed"]
        out["months_per_round"] = job["months_per_round"]
        out["window"] = behind_in_window(households, LOAN_CLASSES, n, start)
        out["first_window"] = behind_in_window(households, LOAN_CLASSES, n, 0,
                                               WINDOW_MONTHS - 1)
        out["whole_run"] = behind_in_window(households, LOAN_CLASSES, n, None)
        out["ever_missed"] = ever_missed_by_group(households, LOAN_CLASSES, n)
        out["window_with_rent"] = behind_in_window(
            households, (*LOAN_CLASSES, Obligation.RENT), n, start
        )
        out["sizes"] = [sum(1 for h in households if h.stratum == g)
                        for g in range(n)]
    return out


def run_tasks(jobs: list[dict], workers: int) -> list[dict]:
    """In order, whichever way they are run, so the caller cannot tell."""
    if workers <= 1 or len(jobs) == 1:
        return [_task(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_task, jobs))


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------
def print_cushion(records: list[HouseholdRecord], built: list) -> dict:
    """What §3 removed, by group. Reported and never scored.

    The share of households whose measured cushion is zero is the size of the
    thing A1b was handing out for free, and it is the quantity that makes A1d-1
    harder to pass rather than easier.
    """
    n_groups = len(GROUPS)
    zero = [0] * n_groups
    total = [0] * n_groups
    cushion = [0.0] * n_groups
    scheduled = [0.0] * n_groups
    for house in built:
        g = house.stratum
        total[g] += 1
        cushion[g] += house.buffer
        scheduled[g] += sum(house.due.values())
        if house.buffer <= 0.0:
            zero[g] += 1
    print("\nthe cushion, measured. docs/a1d_prereg.md section 3: no floor")
    print(f"    {'group':<10}{'n':>9}{'zero':>9}{'zero share':>12}"
          f"{'mean cushion':>15}{'months of bills':>17}")
    rows = []
    for g in range(n_groups):
        if not total[g]:
            continue
        mean = cushion[g] / total[g]
        months = cushion[g] / scheduled[g] if scheduled[g] else 0.0
        print(f"    {GROUPS[g]:<10}{total[g]:>9,}{zero[g]:>9,}"
              f"{zero[g] / total[g]:>12.3%}{mean:>15,.0f}{months:>17.2f}")
        rows.append({"group": GROUPS[g], "households": total[g],
                     "zero": zero[g], "zero_share": zero[g] / total[g],
                     "mean_cushion": mean, "months_of_bills": months})
    print("    'months of bills' is the cushion against one month of scheduled "
          "obligations, which is exactly what A1b handed every household")
    return {"by_group": rows}


def print_stress(built: list) -> dict[str, object]:
    stress = baseline_stress(built)
    print(f"\nbaseline stress, before any shock: {stress['stressed']:,} of "
          f"{stress['households']:,} households ({stress['share']:.3%}) owe "
          f"more each month than they take in")
    print("    unchanged by the cushion: this compares a monthly flow against "
          "a monthly flow and a stock enters neither side")
    return stress


NOT_YET_WRITTEN = ()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--households", type=int, default=DEFAULT_HOUSEHOLDS)
    ap.add_argument("--jobs", type=int, default=None,
                    help="worker processes; the answer does not depend on it")
    ap.add_argument("--sweep-households", type=int,
                    default=DEFAULT_SWEEP_HOUSEHOLDS,
                    help="population for A1d-1's sweep. docs/a1d_prereg.md "
                         "section 5 forces this rather than choosing it")
    ap.add_argument("--cushion-report", action="store_true",
                    help="print the population and the cushion, then stop")
    args = ap.parse_args()

    print("A1d: the cascade on a measured cushion")
    if not ARCHIVE.exists():
        print(f"  {ARCHIVE.name} is absent; run data/fetch_scf.py",
              file=sys.stderr)
        return 1
    try:
        selection = JointSelection.load(SELECTION)
        if not selection.liquid_column:
            raise InputProblem(
                "the selection names no liquid_column, so there is no measured "
                "cushion to read. docs/a1d_prereg.md section 3 registers LIQ"
            )
        respondents = read_respondents(ARCHIVE, selection)
        records = to_records(respondents, basket_by_decile())
    except (InputProblem, ValueError) as exc:
        print(f"  FAILED {exc}", file=sys.stderr)
        return 1

    cost = CostRule()
    built = build_from_records(records, args.households, cost,
                               cushion=Cushion.MEASURED)
    print(f"\npopulation, {args.households:,} households from "
          f"{len(records):,} records, "
          f"{distinct_records(records, args.households):,} of which got at "
          f"least one copy")
    cushion_report = print_cushion(records, built)
    stress = print_stress(built)
    if args.cushion_report:
        return 0

    scored_path = retention_path(PathSpec(periods=SCORED_PERIODS,
                                          seed=PATH_SEED))
    jobs = [
        {"kind": "relieved", "records": records,
         "households": args.households, "periods": ZERO_PERIODS,
         "path": flat_path(ZERO_PERIODS, len(GROUPS))},
        {"kind": "baseline", "records": records,
         "households": args.households, "periods": BASELINE_PERIODS,
         "path": flat_path(BASELINE_PERIODS, len(GROUPS))},
        {"kind": "scored", "records": records, "households": args.households,
         "periods": SCORED_PERIODS, "path": scored_path},
    ]
    for seed in SWEEP_SEEDS:
        for months in SWEEP_MONTHS_PER_ROUND:
            jobs.append({
                "kind": "sweep", "records": records,
                "households": args.sweep_households, "seed": seed,
                "months_per_round": months, "periods": SCORED_PERIODS,
                "path": retention_path(PathSpec(periods=SCORED_PERIODS,
                                                seed=seed,
                                                months_per_round=months)),
            })
    workers = args.jobs if args.jobs is not None else default_jobs()
    print(f"\n  {len(jobs)} independent runs on {workers} worker(s); the "
          f"answer does not depend on that number")
    done = run_tasks(jobs, workers)
    by_kind = {job["kind"]: out for job, out in zip(jobs, done, strict=True)
               if job["kind"] != "sweep"}
    sweep = [out for out in done if out["kind"] == "sweep"]

    zero, reference = a1b_0(by_kind["relieved"]["result"],
                            by_kind["baseline"]["result"])
    zero.name = "A1d-0 zero calibration, by removing the cause"
    scored = by_kind["scored"]["result"]

    by_wealth, dropped_wealth = by_kind["scored"]["by_wealth"]
    by_income, dropped_income = by_kind["scored"]["by_income"]
    family_rows = by_kind["scored"]["renter_families"]
    print_families(family_rows, by_wealth)
    gradient, gradient_detail = a1d_1(respondents, sweep,
                                      args.sweep_households)
    criteria = [
        zero,
        a1_2(scored, by_kind["scored"].get("unstressed")),
        a1_3(scored, cost, reference["final"]),
        a1_6(scored),
        a1_9(records, cost, scored_path, cushion=Cushion.MEASURED),
        a1_10(cost),
        gradient,
        a1d_2(by_wealth, dropped_wealth, by_income, dropped_income),
        a1d_3(cost),
    ]

    print(f"\nbaseline with no shock, {reference['periods']} periods: "
          + ", ".join(f"{k} {v:.4f}"
                      for k, v in reference["final"].items() if v > 0.0))
    print(f"    {reference['displaced']:,} of {reference['renters']:,} renters "
          f"displaced with no shock at all")

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "a1d_measured_cushion.json"
    out.write_text(
        json.dumps(
            {
                "stage": "A1d",
                "complete": True,
                "not_yet_written": list(NOT_YET_WRITTEN),
                "cushion": {
                    "rule": "LIQ, measured, no floor",
                    "source": selection.liquid_column,
                    **cushion_report,
                },
                "delinquency_gradient": {**gradient_detail,
                                         "households": args.sweep_households,
                                         "window_months": WINDOW_MONTHS},
                "wave": selection.wave,
                "households": args.households,
                "records": len(records),
                "records_covered": distinct_records(records, args.households),
                "seeds": "none; the population is a deterministic allocation",
                "baseline_stress": stress,
                "baseline_no_shock": reference,
                "workers": workers,
                "path": {
                    "source": "A0 retention, terminating claims by stratum",
                    "seed": PATH_SEED, "periods": SCORED_PERIODS,
                    "months_per_round": 1,
                },
                "renter_families": {
                    "why": ("docs/a1d_prereg.md section 10, ruling 丙: "
                            "RENTER_FLOOR counts model households, which are "
                            "copies of implicates of families. Reported and "
                            "scored on nothing"),
                    "implicates": IMPLICATES,
                    "floor": RENTER_FLOOR,
                    "by_group": family_rows,
                },
                "first_default_shares": first_default_shares(scored),
                "scored_final": {
                    k.value: scored.delinquent_share[k.value][-1]
                    for k in Obligation
                },
                "free_parameters": [
                    {"name": n, "value": v} for n, v in free_list(cost)
                ],
                "literature_parameters": [
                    {"name": n, "value": v, "why": why}
                    for n, v, why in literature_parameters(cost)
                ],
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "void": bool(c.void), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
