"""B7 step 3: the design audit. B7-9, before any rank is read.

Pre-registered in ``docs/b7_interaction_rank.md``. Section 9 orders the work and
this is step 3, which §6 registers as **reported and not gated**:

    B7-9. Before any rank is read, report the share of the within-cell variance
    that the labelled class index accounts for, and the number of distinct DTI
    levels present in the median cell.

**This file computes no rank and imports no estimator.** That is the point of it
being a separate file: §6 says the stage has to know how much of stage B2's
within term it is talking about *before* it starts talking, and a file that could
print a rank would make the ordering a matter of discipline rather than of what
the code can do.

Usage::

    python experiments/b7_design.py

Writes ``results/b7_design.json``. It reads every retrieved HMDA file, so it
takes as long as stage B2's own loader and no longer.

Why the fill is the number to watch
-----------------------------------
Section 3.5 records that the estimator recovers a constructed rank exactly at a
fill of `0.60` and above and fails below `0.35`, in both directions. So the fill
this file reports **predicts whether B7-0 can pass**, and B7-0 is the gate on the
whole of §5's trichotomy. If the fill comes back near `0.15`, the stage is over
before the expensive part: only the zero-versus-non-zero split would be readable,
and `b1_theorem.md` Corollary 4 already settled that.

A third specification point, fixed here before the run
------------------------------------------------------
§2.2 registers "one level per distinct published value" for the DTI class index.
Taken literally that makes ``Exempt`` a level. **It is not one.** ``Exempt``
records that the filer is relieved of the reporting obligation, so it is a
property of the lender's reporting status and not of the borrower, in exactly the
way §2.1 rules ``applicant_credit_score_type`` out. It is dropped with the blanks
and its count is reported separately from theirs, because a filer-driven absence
and a missing field are different things and the drop table should not merge
them.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from b2_loop_a import RAW, VALID_NAME, VALID_YEARS  # noqa: E402
from monetary_topology.effective_price import (  # noqa: E402
    CELL_KEYS,
    MIN_CELL_SIZE,
    SPREAD_BOUND,
    as_codes,
    average_ranks,
    make_cell_ids,
    plausible_mask,
)

RESULTS = ROOT / "results"

#: The class field. Fixed in §2.2 of the pre-registration and not chosen here.
CLASS_FIELD = "debt_to_income_ratio"

#: Values that are not classes. Blanks are missing data; ``Exempt`` is a
#: property of the filer. Counted separately, never merged.
BLANK = {"", "NA", "na", "None", "none"}
FILER_EXEMPT = {"Exempt", "exempt", "EXEMPT"}

#: The fill at and above which §3.5's sweep recovered a constructed rank exactly.
#: **Read off a sweep of constructed designs, not registered against these data**,
#: and used only to print a prediction that B7-0 will later decide for real.
FILL_RECOVERED = 0.60


@dataclass(frozen=True)
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def load_with_class() -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray, dict]:
    """Stage B2's sample, plus the class column, in one pass.

    Deliberately **not** a change to ``b2_loop_a.load``. That function produces
    the sample stage B2's published figures rest on, and widening it so another
    stage can borrow it would put B2's numbers downstream of B7's needs. The file
    list, the name convention and the marker-row handling are imported rather
    than restated, so the two loaders cannot drift on which files they read.

    The class column is accumulated as integer codes rather than as twenty
    million Python strings.
    """
    files = [
        p
        for p in sorted(RAW.glob("*.csv"))
        if (m := VALID_NAME.match(p.name)) and int(m.group(1)) in VALID_YEARS
    ]
    if not files:
        raise SystemExit(
            f"no usable data in {RAW.relative_to(ROOT)}.\n"
            "Run:  python data/fetch_hmda.py"
        )

    spreads: list[float] = []
    cols: dict[str, list[str]] = {k: [] for k in CELL_KEYS}
    codes: list[int] = []
    lookup: dict[str, int] = {}
    drops = {"blank": 0, "filer_exempt": 0}

    for path in files:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("activity_year", "").startswith("#"):
                    continue
                try:
                    spread = float(row["rate_spread"])
                except (KeyError, TypeError, ValueError):
                    continue

                raw = (row.get(CLASS_FIELD) or "").strip()
                if raw in FILER_EXEMPT:
                    drops["filer_exempt"] += 1
                    code = -1
                elif raw in BLANK:
                    drops["blank"] += 1
                    code = -1
                else:
                    code = lookup.setdefault(raw, len(lookup))

                spreads.append(spread)
                codes.append(code)
                for key in CELL_KEYS:
                    cols[key].append(row.get(key, ""))

    print(f"  loaded {len(files)} files, {len(spreads):,} loans")
    return (
        np.array(spreads),
        {k: np.array(v) for k, v in cols.items()},
        np.array(codes, dtype=np.int64),
        {"levels": lookup, "drops": drops, "n_files": len(files)},
    )


#: Where the parsed sample is kept between runs. ``data/processed/*`` is already
#: in ``.gitignore``, so this never enters the repository.
PARSE_CACHE = ROOT / "data" / "processed" / "b7_parse_cache.npz"

#: Bumped whenever the **meaning** of what is cached changes. A stale cache that
#: still matches its fingerprint is the failure this number exists to prevent, so
#: it moves for a changed field list, a changed drop rule, a changed dtype, and
#: not for a comment.
PARSE_CACHE_VERSION = 1


def parse_fingerprint() -> str:
    """Everything that could change the parse, hashed into one string.

    The file list with each file's **size and modification time in
    nanoseconds**, the cell keys, the class field, the two drop sets, and the
    format version. A cache whose fingerprint does not match is not used and not
    repaired; it is rebuilt, loudly.

    Deliberately not a hash of the file **contents**: reading four hundred CSV
    files to decide whether to avoid reading four hundred CSV files saves
    nothing. Size and mtime miss the case of a file edited in place within the
    same nanosecond and to the same length, which no retrieval this project runs
    can produce.
    """
    files = sorted(
        p for p in RAW.glob("*.csv")
        if (m := VALID_NAME.match(p.name)) and int(m.group(1)) in VALID_YEARS
    )
    payload = json.dumps(
        {
            "version": PARSE_CACHE_VERSION,
            "files": [[p.name, p.stat().st_size, p.stat().st_mtime_ns] for p in files],
            "cell_keys": list(CELL_KEYS),
            "class_field": CLASS_FIELD,
            "blank": sorted(BLANK),
            "filer_exempt": sorted(FILER_EXEMPT),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_cached(rebuild: bool = False) -> tuple[tuple, np.ndarray]:
    """``load_with_class`` with the parse kept on disk. Returns ``(loaded, cell_ids)``.

    The parse is twenty million rows through ``csv.DictReader`` and takes about
    twenty minutes; every script in this stage paid it separately. What is kept
    is four integer and float arrays, about `560 MB`, and what is discarded is the
    seven fixed-width string columns, which are `6.3 GB`, and their join, which is
    another `6.7 GB`.

    **The cell codes are cached, not the cell key strings, and the downstream
    numbering is identical either way.** ``as_codes`` assigns codes by
    ``np.unique``, so a code's order is its string's order; taking
    ``np.unique`` of a subset of the codes therefore renumbers exactly as taking
    ``np.unique`` of the same subset of the strings does. So a cached run
    reproduces an uncached one **bit for bit**, including the null draws, which
    depend on the cell ordering. That is the property that makes this a cache and
    not a second implementation.

    ``rebuild=True`` ignores any existing cache and writes a fresh one.
    """
    want = parse_fingerprint()
    if not rebuild and PARSE_CACHE.exists():
        with np.load(PARSE_CACHE, allow_pickle=False) as z:
            got = str(z["fingerprint"])
            if got == want:
                meta = json.loads(str(z["meta"]))
                print(f"  parse cache hit ({PARSE_CACHE.name})")
                return (
                    (z["spreads"], {"activity_year": z["years"]},
                     z["class_codes"], meta),
                    z["cell_codes"],
                )
        print("  parse cache STALE, rebuilding")
        print(f"    on disk  {got[:16]}")
        print(f"    wanted   {want[:16]}")

    spreads, cols, class_codes, meta = load_with_class()
    cell_codes, _n = as_codes(make_cell_ids(cols))
    years = cols["activity_year"].astype(np.int32)

    PARSE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        PARSE_CACHE,
        fingerprint=np.array(want),
        meta=np.array(json.dumps(meta)),
        spreads=spreads,
        class_codes=class_codes,
        cell_codes=cell_codes,
        years=years,
    )
    print(f"  wrote parse cache ({PARSE_CACHE.stat().st_size / 1e6:.0f} MB)")
    return (spreads, {"activity_year": years}, class_codes, meta), cell_codes


def levels_by_code(levels: dict[str, int] | list[str]) -> list[str]:
    """The class levels **in code order**, which is the only order a partition may use.

    **This function exists because of a bug it is named after.** ``load_with_class``
    assigns each class a code by first appearance in the CSV files, and the design
    record stored ``sorted(meta["levels"])``, which is the same strings in
    **alphabetical** order. ``coarse_classes`` and ``complement_classes`` then read
    that list **positionally**, as `levels[i]` is the level of code `i`. It is not.

    On the retrieved sample the two orders differ, so every partition this stage
    built merged the wrong classes: the "regulator's bucket scheme" grid put
    ``<20%`` in the same group as ``49``. Nothing about the fill, the group count
    or any criterion could see it, because a scrambled partition of nineteen
    levels into six groups is still six groups.

    A list is accepted and returned unchanged, for the caller that already has the
    ordered list. A dict is sorted by its value, which is the code.
    """
    if isinstance(levels, dict):
        return [k for k, _ in sorted(levels.items(), key=lambda kv: kv[1])]
    return list(levels)


def design_from_loaded(
    loaded: tuple,
    bound: float | None = SPREAD_BOUND,
    rank_transform: bool = False,
    cell_ids: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """The filtered, coded design, from an already-read sample.

    **Split out from ``build_design`` on 2026-08-16, no operation and no order
    changed at the default arguments**, so B7-7 can rebuild the design at six
    spread bands without reading four hundred CSV files six times.
    ``build_design`` now calls this and returns exactly what it always did;
    ``results/b7_design.json`` reproduces.

    ``bound = None`` applies **no** band. ``rank_transform`` replaces the spreads
    by tie-averaged ranks over the whole class-usable sample before the cell-size
    filter, which is what ``effective_price.rank_decomposition`` does and which is
    deliberately computed with no band at all: a rank is bounded by the sample
    size however large the value, so the placeholder rows move it by at most
    `115 / 20,071,900`. The two options are therefore normally used together.

    ``cell_ids`` may be supplied by a caller sweeping bands: the cell key is a
    property of the row and no band changes it, so joining sixteen million
    strings once instead of once per band is an optimisation and never a result.

    Returns the years as well, which ``build_design`` drops. B7-8 needs them and
    nothing before it did.
    """
    spreads, cols, class_codes, meta = loaded
    n_loaded = spreads.size

    usable = class_codes >= 0
    values = np.asarray(spreads, dtype=np.float64)
    if rank_transform:
        values = np.zeros_like(values)
        values[usable] = average_ranks(spreads[usable])
    keep = usable if bound is None else plausible_mask(spreads, bound) & usable

    values = values[keep]
    cols = {k: np.asarray(v)[keep] for k, v in cols.items()}
    class_codes = class_codes[keep]
    if cell_ids is None:
        missing = [k for k in CELL_KEYS if k not in cols]
        if missing:
            raise ValueError(
                "cols is missing "
                + ", ".join(missing)
                + " and no cell_ids were supplied. A sample from load_cached "
                "carries only activity_year; pass the cell codes it returns "
                "beside it."
            )
    keys = (make_cell_ids(cols) if cell_ids is None else np.asarray(cell_ids)[keep])

    cell_codes, n_cells_all = as_codes(keys)
    sizes = np.bincount(cell_codes, minlength=n_cells_all)
    in_big = (sizes >= MIN_CELL_SIZE)[cell_codes]

    values, class_codes = values[in_big], class_codes[in_big]
    surviving_keys = keys[in_big]
    years = cols["activity_year"][in_big]
    cell_codes = np.unique(cell_codes[in_big], return_inverse=True)[1]
    n_cells = int(cell_codes.max()) + 1 if cell_codes.size else 0
    n_classes = int(class_codes.max()) + 1 if class_codes.size else 0

    present = np.bincount(
        cell_codes * n_classes + class_codes, minlength=n_cells * n_classes
    ) > 0
    design = {
        "n_files": meta["n_files"],
        "n_loaded": int(n_loaded),
        "drops": meta["drops"],
        "n_after_filters": int(values.size),
        "n_cells": n_cells,
        "n_classes": n_classes,
        "class_levels": levels_by_code(meta["levels"]),
        "fill": float(present.mean()),
        "bound": bound,
        "rank_transform": bool(rank_transform),
        "n_present_entries": int(present.sum()),
        "cell_keys": surviving_keys,
    }
    return cell_codes, class_codes, values, years, design


def build_design() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """The filtered, coded sample: cell codes, class codes, spreads, description.

    **Extracted from ``audit`` on 2026-08-15, without changing a single
    operation or its order**, so that ``b7_gate.py`` builds the identical design
    rather than restating the filters and drifting from them. ``audit`` now calls
    this and its output is unchanged; ``results/b7_design.json`` reproduces.

    **Delegates to :func:`design_from_loaded` since 2026-08-16.** It drops the
    years and the cell keys so its four-tuple signature is what it always was and
    every existing caller is untouched.

    **Reads through :func:`load_cached` since 2026-08-16**, so `b7_gate.py`,
    `b7_rank.py` and `audit` all stop paying the twenty-minute parse on every
    run. The cached path reproduces the uncached one bit for bit, cell numbering
    included; ``load_cached``'s docstring says why.
    """
    loaded, cell_ids = load_cached()
    cells, classes, values, _years, design = design_from_loaded(
        loaded, cell_ids=cell_ids
    )
    design = {k: v for k, v in design.items() if k != "cell_keys"}
    return cells, classes, values, design


def _unused_original_build_design() -> tuple:
    """The pre-2026-08-16 body, kept because nothing in this repository is
    deleted. It is not called; :func:`design_from_loaded` is the live path and
    reproduces it exactly at the default arguments."""
    spreads, cols, class_codes, meta = load_with_class()
    n_loaded = spreads.size

    keep = plausible_mask(spreads, SPREAD_BOUND) & (class_codes >= 0)
    spreads = spreads[keep]
    cols = {k: v[keep] for k, v in cols.items()}
    class_codes = class_codes[keep]

    cell_codes, n_cells_all = as_codes(make_cell_ids(cols))
    sizes = np.bincount(cell_codes, minlength=n_cells_all)
    big = sizes >= MIN_CELL_SIZE
    in_big = big[cell_codes]

    spreads, class_codes = spreads[in_big], class_codes[in_big]
    cell_codes = np.unique(cell_codes[in_big], return_inverse=True)[1]
    n_cells = int(cell_codes.max()) + 1 if cell_codes.size else 0
    n_classes = int(class_codes.max()) + 1 if class_codes.size else 0

    present = np.bincount(
        cell_codes * n_classes + class_codes, minlength=n_cells * n_classes
    ) > 0
    design = {
        "n_files": meta["n_files"],
        "n_loaded": int(n_loaded),
        "drops": meta["drops"],
        "n_after_filters": int(spreads.size),
        "n_cells": n_cells,
        "n_classes": n_classes,
        "class_levels": levels_by_code(meta["levels"]),
        "fill": float(present.mean()),
    }
    return cell_codes, class_codes, spreads, design


def coarse_classes(class_codes: np.ndarray, levels: list[str]) -> np.ndarray:
    # ``levels`` is read POSITIONALLY: levels[i] must be the level of code i.
    # Pass design["class_levels"], which :func:`levels_by_code` puts in code
    # order. Passing an alphabetically sorted list silently scrambles the
    # partition and nothing downstream can detect it.
    """§3.8's second class grid: the regulator's own buckets, integers collapsed.

    The published field buckets everything below `36` and above `49` and reports
    `36` through `49` as bare integers. Collapsing those integers into one level
    reconstructs the range the regulator's own bucket scheme leaves open, so the
    coarse grid is `<20%`, `20%-<30%`, `30%-<36%`, `36-49`, `50%-60%`, `>60%`.

    **Both boundaries are the regulator's**, `36` and `50`, at exactly the points
    where its buckets stop and resume. This project chooses neither.

    **Moved here from ``b7_rank.py`` on 2026-08-15**, unchanged, because
    ``b7_gate.py`` has to gate this grid too and two copies of a class mapping is
    two chances for them to stop agreeing. ``b7_rank.py`` now delegates.
    """
    n = int(class_codes.max()) + 1 if class_codes.size else 0
    if len(levels) != n:
        raise ValueError(
            f"levels has {len(levels)} entries against {n} class codes; it is "
            "read positionally and a length mismatch means it is the wrong list"
        )
    order: dict[str, int] = {}
    out = np.empty_like(class_codes)
    for i in range(len(levels)):
        key = "INT" if levels[i].strip().isdigit() else levels[i]
        if key not in order:
            order[key] = len(order)
        out[class_codes == i] = order[key]
    return out


def complement_classes(class_codes: np.ndarray, levels: list[str]) -> np.ndarray:
    # Read POSITIONALLY, exactly as :func:`coarse_classes`. Same warning.
    """§3.11's third class grid: the exact complement of :func:`coarse_classes`.

    The coarse grid keeps the five published buckets apart and merges the
    fourteen integers `36` through `49` into one level. This one does the
    opposite: it keeps the fourteen integers apart and merges the five buckets
    into one. Fifteen levels.

    **It uses the same two boundaries, `36` and `50`, and they are the
    regulator's.** No boundary is chosen by this project here either, which is
    what makes it runnable without the external transcription §2.3 waits on.

    It exists to test the deduction in §3.10: the fine grid sees a second
    direction and the coarse grid does not, so that direction must distinguish
    levels the coarse grid merges. This grid is the one that keeps exactly those
    distinctions and discards the others.
    """
    n = int(class_codes.max()) + 1 if class_codes.size else 0
    if len(levels) != n:
        raise ValueError(
            f"levels has {len(levels)} entries against {n} class codes; it is "
            "read positionally and a length mismatch means it is the wrong list"
        )
    out = np.empty_like(class_codes)
    order: dict[str, int] = {}
    for i in range(len(levels)):
        key = levels[i] if levels[i].strip().isdigit() else "BUCKET"
        if key not in order:
            order[key] = len(order)
        out[class_codes == i] = order[key]
    return out


def describe_partition(
    class_codes: np.ndarray, group_ids: np.ndarray, levels: list[str]
) -> dict[int, list[str]]:
    """Which level names ended up in which group. **Print this before computing.**

    §3.21's guard, and the only thing that would have caught §3.21's bug on the
    day it was written. A partition's name is not its membership: for the whole of
    stage B7 before 2026-08-16 the grid called "the regulator's own bucket scheme"
    put ``<20%`` in the same group as ``49``, and the group count, the fill, the
    loan counts and every criterion in the pre-registration were satisfied
    throughout. **A scrambled partition is invisible in a count and obvious in a
    list.**

    One copy here rather than one per script, for the same reason
    ``coarse_classes`` moved here: two copies of a class mapping is two chances
    for them to stop agreeing.
    """
    groups: dict[int, list[str]] = {}
    for code in range(len(levels)):
        hit = group_ids[class_codes == code]
        if hit.size:
            groups.setdefault(int(hit[0]), []).append(levels[code])
    return groups


def audit() -> tuple[list[Criterion], dict]:
    cell_codes, class_codes, spreads, design = build_design()
    # design["class_levels"] is already in code order; levels_by_code passes a
    # list through unchanged, so re-wrapping it here cannot re-sort it.
    n_loaded, meta = design["n_loaded"], {"levels": design["class_levels"],
                                          "drops": design["drops"],
                                          "n_files": design["n_files"]}
    n_cells, n_classes = design["n_cells"], design["n_classes"]
    n = spreads.size

    # ---- the cell-by-class design -------------------------------------
    flat = cell_codes * n_classes + class_codes
    size = n_cells * n_classes
    counts = np.bincount(flat, minlength=size).astype(np.float64)
    totals = np.bincount(flat, weights=spreads, minlength=size)
    sqtot = np.bincount(flat, weights=spreads**2, minlength=size)
    present = counts > 0

    per_cell_classes = present.reshape(n_cells, n_classes).sum(axis=1)
    fill = float(present.mean())
    quart = np.percentile(per_cell_classes, [0, 25, 50, 75, 100]).tolist()

    # ---- B7-9: how much of the within term the class index touches -----
    # Var_c = between-class-within-cell + mean within-class variance, exactly.
    cell_n = np.bincount(cell_codes, minlength=n_cells).astype(np.float64)
    cell_sum = np.bincount(cell_codes, weights=spreads, minlength=n_cells)
    cell_sq = np.bincount(cell_codes, weights=spreads**2, minlength=n_cells)
    cell_mean = cell_sum / cell_n
    var_c = cell_sq / cell_n - cell_mean**2

    entry_mean = np.divide(totals, counts, out=np.zeros_like(totals), where=present)
    dev = (entry_mean - np.repeat(cell_mean, n_classes)) ** 2
    between_c = np.bincount(
        np.repeat(np.arange(n_cells), n_classes), weights=counts * dev,
        minlength=n_cells,
    ) / cell_n

    w = cell_n / cell_n.sum()
    within_term = float((w * var_c).sum())
    between_class_term = float((w * between_c).sum())
    share = between_class_term / within_term if within_term > 0 else 0.0

    # Exactness check on the decomposition, not a claim about the world.
    within_class_term = float(
        (w * (np.bincount(np.repeat(np.arange(n_cells), n_classes),
                          weights=sqtot - counts * entry_mean**2,
                          minlength=n_cells) / cell_n)).sum()
    )
    residual = abs(within_term - between_class_term - within_class_term)

    record = {
        "n_files": meta["n_files"],
        "n_loaded": int(n_loaded),
        "drops": meta["drops"],
        "n_after_filters": int(n),
        "n_cells": n_cells,
        "n_classes": n_classes,
        "class_levels": levels_by_code(meta["levels"]),
        "fill": fill,
        "classes_per_cell_min_q1_median_q3_max": quart,
        "within_term": within_term,
        "between_class_term": between_class_term,
        "b7_9_share": share,
        "decomposition_residual": residual,
        "fill_recovered_boundary": FILL_RECOVERED,
        "gate_prediction": "may pass" if fill >= FILL_RECOVERED else "expected to fail",
    }

    out = [
        Criterion(
            "B7-9a  the decomposition is exact",
            residual < 1e-9 * max(within_term, 1.0),
            f"within {within_term:.6f} = between-class {between_class_term:.6f} + "
            f"within-class {within_class_term:.6f}, residual {residual:.3e}. "
            "An identity, so a failure here is the code and nothing else",
        ),
        Criterion(
            "B7-9b  every retained loan lands in exactly one class",
            int(counts.sum()) == n,
            f"{int(counts.sum()):,} of {n:,} retained loans placed; "
            f"dropped before the design: {meta['drops']['blank']:,} blank and "
            f"{meta['drops']['filer_exempt']:,} filer-exempt, counted separately "
            "because they are different absences",
        ),
        Criterion(
            "B7-9  reported, not gated: what this class index touches",
            True,
            f"**share of stage B2's within term carried by the class index: "
            f"{share:.4f}**.  {n_classes} classes over {n_cells:,} cells, "
            f"{n:,} loans.  distinct classes per cell "
            f"min/q1/median/q3/max = {'/'.join(f'{v:.0f}' for v in quart)}.  "
            f"**fill = {fill:.4f}**, against the {FILL_RECOVERED:.2f} at which "
            "§3.5's sweep still recovered a constructed rank exactly, so B7-0 is "
            f"{record['gate_prediction']}",
        ),
    ]
    return out, record


def main() -> int:
    print("B7 step 3: the design audit. No rank is computed in this file.\n")
    cs, record = audit()
    for c in cs:
        print(c.line())
    n_pass = sum(c.passed for c in cs)
    print(f"\n  {n_pass}/{len(cs)} criteria passed")

    if record["fill"] < FILL_RECOVERED:
        print(
            "\n  READ THIS BEFORE SPENDING ANYTHING ELSE ON B7.\n"
            f"  The fill is {record['fill']:.4f}, below the {FILL_RECOVERED:.2f} at\n"
            "  which the estimator still recovered a constructed rank. §3.5 says\n"
            "  the trichotomy is then unavailable and only the zero-versus-non-zero\n"
            "  split may be reported, and Corollary 4 already settled that split.\n"
            "  B7-0 on the real design is the decision and it has not been run."
        )

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b7_design.json"
    out.write_text(
        json.dumps({"stage": "B7", "step": "design_audit", **record,
                    "criteria": [{"name": c.name, "passed": bool(c.passed),
                                  "detail": c.detail} for c in cs]}, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
