#!/usr/bin/env python3
"""B8 C9: observations per `(class x window)` cell, and the minimum over classes.

Registered in ``docs/b8_fannie_slice.md`` §15.3. Reads the core table and
``b8_triangles.triangles``, which reproduces C3/C4 window for window.

**What C9 decides.** C7 reported the class fields' *fill rate* and §15.3's N3
says that statistic does not bound the reading: present is not the same as
enough. C9 is the gate that licenses B8-4. **If C9's minimum cannot be met on a
class grid, B8-4 does not run on that grid, and that is not a failure of B8.**

**The floor is `min_size = 20` and the source is this repository**, not this
file: ``b2_measurement.md`` §10 adopted 20 as the per-cell minimum after the
``0.975`` artefact and the graded placebo ran at it.

**Where the band edges come from, since §5 says "band" and does not say where.**

  * **FICO and LTV: the issuer's own published pricing partition**, Fannie Mae's
    LLPA Matrix Table 1, effective 2026-01-28. Same principle as §3.3's primary
    `q` grid, which is the delinquency status field's own partition. **No
    boundary here is chosen by this project.**
  * **DTI: there is no issuer partition.** Every DTI-based LLPA was **removed on
    2023-05-17** and the current matrix carries none, so the issuer's pricing
    grid gives no cut on DTI. The grid used is therefore the regulator's, the
    HMDA published buckets `<20 / 20-29 / 30-35 / 36-49 / 50-60 / >60` with
    `36`-`49` reported as bare integers, which is the grid
    ``b7_interaction_rank.md`` §3.3 already measured rank-sensitivity on and
    whose three variants (fine 19, coarse 6, complement 15) are reproduced here.
    **Cite this asymmetry wherever a DTI band is quoted: FICO and LTV come from
    the issuer, DTI comes from the regulator, and they are not the same kind of
    source.**
  * **Every coarse grid merges levels of its own fine grid and introduces no new
    boundary.** That is the form §3.3's coarse DTI grid takes and the reason it
    is licensed: the reading is a function of *which* levels are merged, so a
    coarse grid that invents an edge is a different object, not a coarser one.

**Nothing is excluded here.** ``b7_interaction_rank.md`` §2.4 requires a class
index to move with the borrower and not with the dwelling or the tract, and
`state`, `ltv` and `occupancy` fail that test. **They are counted anyway and the
verdict is printed as a column.** C9 is a census; the exclusion is B8-4's
decision and making it here would let a counting step rule on a design question.

**Missing values are a level**, printed and counted, never dropped, per §7.

**No prediction is read here and no outcome terminates the stage.**

Usage::

    python experiments/b8_c9_cells.py --selftest
    python experiments/b8_c9_cells.py
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b8_core as K  # noqa: E402
import b8_triangles as T  # noqa: E402

OUT = K.ROOT / "results" / "b8_c9_cells.md"

#: `b2_measurement.md` §10. Not chosen here.
MIN_SIZE = 20

#: `b8_fannie_slice.md` §6. B8-4a reads across these four. `post-2022` exists in
#: the data and is reported beside them, marked as outside §6.
WINDOWS_SEC6 = ["pre-crisis", "HAMP", "Flex", "COVID"]

#: Fannie Mae LLPA Matrix Table 1, effective 2026-01-28. Lower edge of each
#: band, ascending. A score below the first edge is the bottom band.
FICO_LLPA = [640, 660, 680, 700, 720, 740, 760, 780]
#: LTV column bands of the same table. **These are UPPER edges, not lower
#: ones.** The published columns run `<30.00`, `30.01-60.00`, ... `>95.00`, and
#: the file reports LTV as a whole per cent, so an LTV of exactly 60 belongs to
#: the `30.01-60.00` column and 61 to the next. Banding it with lower edges the
#: way FICO is banded puts every round LTV one column too high, which is what
#: the selftest caught on its first run.
LTV_LLPA_UPPER = [30, 60, 70, 75, 80, 85, 90, 95]

#: HMDA's published DTI buckets. `36`-`49` arrive as bare integers, everything
#: else as a bucket. `b7_interaction_rank.md` §3.3's three grids.
DTI_LOW = [20, 30, 36]
DTI_HIGH = [50, 61]


def _band(v, edges, na_level: int) -> np.ndarray:
    """Bucket ``v`` by lower edges, sending the missing sentinel to its own
    level. Returns int16 labels, with ``na_level`` reserved for missing."""
    lab = np.searchsorted(np.asarray(edges), v, side="right").astype(np.int16)
    return np.where(v == K.U16_NA, np.int16(na_level), lab)


def _band_upper(v, upper, na_level: int) -> np.ndarray:
    """Bucket ``v`` by **upper** edges: the band whose upper edge first reaches
    the value. Used where the published partition is written as closed ranges
    ending on a round number."""
    lab = np.searchsorted(np.asarray(upper), v, side="left").astype(np.int16)
    return np.where(v == K.U16_NA, np.int16(na_level), lab)


def _fico_grids(v):
    fine = _band(v, FICO_LLPA, 99)
    # coarse merges LLPA bands in pairs. Every edge below is an LLPA edge.
    coarse = _band(v, [640, 680, 720, 760], 99)
    return {"fico_llpa9": fine, "fico_llpa_coarse5": coarse}


def _ltv_grids(v):
    fine = _band_upper(v, LTV_LLPA_UPPER, 99)
    coarse = _band_upper(v, [60, 80, 95], 99)
    return {"ltv_llpa9": fine, "ltv_llpa_coarse4": coarse}


def _dti_grids(v):
    """The three grids of §3.3, reproduced.

    fine        19 levels: five buckets plus the fourteen integers 36-49
    coarse       6 levels: the fourteen integers merged, the buckets kept
    complement  15 levels: the buckets merged, the fourteen integers kept
    """
    na = v == K.U16_NA
    x = v.astype(np.int32)
    inner = (~na) & (x >= 36) & (x <= 49)

    fine = np.full(v.size, 99, dtype=np.int16)
    fine = np.where((~na) & (x < 20), 0, fine)
    fine = np.where((~na) & (x >= 20) & (x < 30), 1, fine)
    fine = np.where((~na) & (x >= 30) & (x < 36), 2, fine)
    fine = np.where(inner, (x - 36 + 3).astype(np.int16), fine)
    fine = np.where((~na) & (x >= 50) & (x <= 60), 17, fine)
    fine = np.where((~na) & (x > 60), 18, fine)

    coarse = np.where(inner, np.int16(3), fine)
    coarse = np.where((~na) & (x >= 50) & (x <= 60), np.int16(4), coarse)
    coarse = np.where((~na) & (x > 60), np.int16(5), coarse)

    # complement: the five buckets become one level, the integers stay apart
    complement = np.where(inner, (x - 36).astype(np.int16), np.int16(14))
    complement = np.where(na, np.int16(99), complement)
    return {"dti_fine19": fine, "dti_coarse6": coarse,
            "dti_complement15": complement}


def build_grids(c: K.Core) -> dict:
    """label array per class grid, one entry per loan, plus the §2.4 verdict."""
    g = {}
    g.update(_fico_grids(c.loan["fico"]))
    g.update(_ltv_grids(c.loan["ltv"]))
    g.update(_dti_grids(c.loan["dti"]))
    for name, col in (("fthb", "fthb"), ("occupancy", "occupancy"),
                      ("purpose", "purpose"), ("state", "state")):
        g[name] = c.loan[col].astype(np.int16)
    return g


#: `b7_interaction_rank.md` §2.4: a class index must move with the borrower and
#: not with the dwelling or the tract. Recorded, not enforced.
SEC24 = {
    "fico_llpa9": "borrower", "fico_llpa_coarse5": "borrower",
    "dti_fine19": "borrower", "dti_coarse6": "borrower",
    "dti_complement15": "borrower",
    "fthb": "borrower", "purpose": "borrower",
    "ltv_llpa9": "**dwelling**", "ltv_llpa_coarse4": "**dwelling**",
    "occupancy": "**dwelling**", "state": "**tract**",
}


#: The label each grid uses for "the field was blank". Banded fields get 99
#: from ``_band``; ``as_code`` fields get ``U8_NA``; ``state`` is packed in a
#: uint16 and its ``U16_NA`` wraps to -1 in the int16 the labels are held in.
#: **Not the same thing as a field whose value is a reported "unknown" code**,
#: which is a level the file asserts and stays a level here.
MISSING_LABEL = {
    "fico_llpa9": 99, "fico_llpa_coarse5": 99,
    "ltv_llpa9": 99, "ltv_llpa_coarse4": 99,
    "dti_fine19": 99, "dti_coarse6": 99, "dti_complement15": 99,
    "fthb": int(K.U8_NA), "occupancy": int(K.U8_NA), "purpose": int(K.U8_NA),
    "state": -1,
}

#: Levels excluded from the floor test, per the author's ruling of 2026-08-16: a
#: blank class field and a self-reported unknown code are both measurement
#: gaps rather than agent classes, and each is excluded **carrying its count**,
#: which is §7's form.
#:
#: **The `purpose` entry is on a weaker footing than the rest and it is marked
#: so.** Blanks are identified behaviourally: the field is absent. `U` is
#: identified as "unspecified" from the layout document, and C0b forbids
#: identifying a field by the look of its values or by the layout document.
#: It is excluded per the ruling, its count is printed, and **nothing
#: downstream may treat `U` as identified**. Its total across all six archives
#: and all four windows is small enough that no reading can turn on it.
EXCLUDED = {
    "fico_llpa9": {99: "blank"}, "fico_llpa_coarse5": {99: "blank"},
    "ltv_llpa9": {99: "blank"}, "ltv_llpa_coarse4": {99: "blank"},
    "dti_fine19": {99: "blank"}, "dti_coarse6": {99: "blank"},
    "dti_complement15": {99: "blank"},
    "fthb": {int(K.U8_NA): "blank"},
    "occupancy": {int(K.U8_NA): "blank"},
    "purpose": {int(K.U8_NA): "blank",
                ord("U"): "unknown code, **documentary basis only**"},
    "state": {-1: "blank"},
}

#: Band edges again, as text, so a level number in the report is readable.
_FICO_NAMES = ["<=639", "640-659", "660-679", "680-699", "700-719",
               "720-739", "740-759", "760-779", ">=780"]
_FICO_C_NAMES = ["<=639", "640-679", "680-719", "720-759", ">=760"]
_LTV_NAMES = ["<=30", "30-60", "60-70", "70-75", "75-80", "80-85", "85-90",
              "90-95", ">95"]
_LTV_C_NAMES = ["<=60", "60-80", "80-95", ">95"]
_DTI_F_NAMES = (["<20", "20-29", "30-35"] + [str(k) for k in range(36, 50)]
                + ["50-60", ">60"])
_DTI_C_NAMES = ["<20", "20-29", "30-35", "36-49", "50-60", ">60"]
_DTI_X_NAMES = [str(k) for k in range(36, 50)] + ["outside 36-49"]


def level_name(grid: str, v: int) -> str:
    """A level label as something a reader can check against the source grid.

    **The report printed a minimum without saying which level it was on**, and
    that cannot distinguish "the borrower indices are too thin" from "the
    indices are fine and the blank level is thin". Those two call for different
    decisions, so the level is named.
    """
    if v == MISSING_LABEL.get(grid):
        return "*blank*"
    tab = {"fico_llpa9": _FICO_NAMES, "fico_llpa_coarse5": _FICO_C_NAMES,
           "ltv_llpa9": _LTV_NAMES, "ltv_llpa_coarse4": _LTV_C_NAMES,
           "dti_fine19": _DTI_F_NAMES, "dti_coarse6": _DTI_C_NAMES,
           "dti_complement15": _DTI_X_NAMES}.get(grid)
    if tab is not None:
        return tab[v] if 0 <= v < len(tab) else f"?{v}"
    if grid == "state":
        return K.unpack_state(int(v) & 0xFFFF) or "*blank*"
    return chr(v) if 32 <= v < 127 else f"?{v}"


@dataclass
class GridResult:
    name: str
    n_levels: int = 0
    cells: int = 0
    n_ok: int = 0
    n_short: int = 0
    n_empty: int = 0
    loans_in_short: int = 0
    min_cell: int = 0
    per_window_min: dict = field(default_factory=dict)
    quant: list = field(default_factory=list)
    na_level_n: int = 0
    argmin: str = ""
    min_ex_blank: int = 0
    argmin_ex_blank: str = ""
    blank_loans: int = 0
    excluded_detail: dict = field(default_factory=dict)


def score(lab: np.ndarray, win: np.ndarray, tri: np.ndarray,
          windows: list[str], name: str) -> GridResult:
    r = GridResult(name)
    sel = tri
    lv = np.unique(lab[sel])
    r.n_levels = int(lv.size)
    r.na_level_n = int(((lab == 99) & sel).sum())
    counts, cellv, cellw = [], [], []
    for wi, wname in enumerate(windows):
        m = sel & (win == T.WINDOWS_INDEX[wname])
        col = [int((m & (lab == v)).sum()) for v in lv]
        counts.extend(col)
        cellv.extend(int(v) for v in lv)
        cellw.extend([wname] * len(col))
        r.per_window_min[wname] = min(col) if col else 0
    a = np.asarray(counts, dtype=np.int64)
    cellv = np.asarray(cellv)
    cellw = np.asarray(cellw)
    r.cells = int(a.size)
    r.n_ok = int((a >= MIN_SIZE).sum())
    r.n_short = int(((a > 0) & (a < MIN_SIZE)).sum())
    r.n_empty = int((a == 0).sum())
    r.loans_in_short = int(a[(a > 0) & (a < MIN_SIZE)].sum())
    r.min_cell = int(a.min()) if a.size else 0
    if a.size:
        r.quant = [int(x) for x in np.quantile(a, [0, .1, .25, .5, .75, .9, 1])]
        j = int(a.argmin())
        r.argmin = f"`{level_name(name, int(cellv[j]))}` in {cellw[j]}"
        # **The same minimum with the blank level dropped.** Reported beside
        # the primary one, never instead of it: §7 requires an exclusion to
        # carry its count, and "the field was not reported" is a measurement
        # gap rather than an agent class, so which of the two is the right
        # object is a ruling and not this file's to make.
        drop = np.isin(cellv, list(EXCLUDED.get(name, {})))
        keep = ~drop
        r.blank_loans = int(a[drop].sum())
        r.excluded_detail = {int(v): int(a[cellv == v].sum())
                             for v in EXCLUDED.get(name, {})}
        if keep.any():
            b = a[keep]
            r.min_ex_blank = int(b.min())
            jj = int(b.argmin())
            r.argmin_ex_blank = (f"`{level_name(name, int(cellv[keep][jj]))}`"
                                 f" in {cellw[keep][jj]}")
    return r


# ---------------------------------------------------------------------------


def collect(names: list[str]):
    """Per archive, the triangle mask, window index and class labels.

    Archives are origination cohorts, which is B8-4b's axis, so the cohort
    identity is kept rather than pooled away.
    """
    per_cohort = {}
    pooled_lab, pooled_win, pooled_tri = {}, [], []
    q_same = True
    for n in names:
        with K.Core(n) as c:
            t = T.triangles(c)
            g = build_grids(c)
            # The triangle population does not depend on the `q` grid: the test
            # asks for *some* delinquent row, not a depth, and both registered
            # grids agree on which rows are delinquent. Asserted rather than
            # argued, since §3.3 forbids reading anything off one grid.
            dv = c.row["delinq"]
            primary_del = (dv <= 98) & (dv != 0)      # current/30/60/90+/mod
            secondary_del = (dv <= 98) & (dv != 0)    # current/delinquent/mod
            if not np.array_equal(primary_del, secondary_del):
                q_same = False
            per_cohort[n] = (t["triangle"], t["window"], g)
            pooled_tri.append(t["triangle"])
            pooled_win.append(t["window"])
            for k, v in g.items():
                pooled_lab.setdefault(k, []).append(v)
        print(f"  {n}: {int(t['triangle'].sum()):,} triangles", file=sys.stderr)
    tri = np.concatenate(pooled_tri)
    win = np.concatenate(pooled_win)
    lab = {k: np.concatenate(v) for k, v in pooled_lab.items()}
    return per_cohort, lab, win, tri, q_same


def report(res, res_flex_cohort, q_same, names) -> str:
    L = []
    A = L.append
    A("# B8 C9: observations per cell, and whether B8-4 has a grid to run on\n")
    A("Generated by `experiments/b8_c9_cells.py` from the core table and "
      "`b8_triangles.triangles`, which reproduces C3/C4 window for window "
      "(+0 on all five). Registered in `docs/b8_fannie_slice.md` §15.3.\n")
    A(f"**Floor `min_size = {MIN_SIZE}`, source `b2_measurement.md` §10.** "
      "Not chosen here.\n")
    A("**Reads no prediction. No outcome here terminates the stage.**\n")

    A("\n## 0. The `q` grid does not enter\n")
    A("§15.3 asks for each class grid **and each `q` grid**. The triangle "
      "population is the same on both: the test asks for *some* delinquent "
      "row, not for a depth, and the primary grid "
      "`current/30/60/90+/modified` and the secondary "
      "`current/delinquent/modified` agree row for row on which rows are "
      "delinquent. " +
      ("**Checked as arrays on every archive, not argued.** The `q` grid "
       "changes the walk's state space and therefore `omega`; it does not "
       "change who completes a triangle, so one table per class grid is the "
       "whole answer rather than two identical ones.\n"
       if q_same else
       "**The check FAILED: the two grids disagree on which rows are "
       "delinquent. Everything below is on the primary grid only and is not "
       "a result.**\n"))

    A("\n## 1. Class grids, their sources, and §2.4\n")
    A("**FICO and LTV are the issuer's own partition** (Fannie Mae LLPA Matrix "
      "Table 1, effective 2026-01-28). **DTI has no issuer partition**: every "
      "DTI-based LLPA was removed on 2023-05-17, so its grid is the "
      "regulator's, the HMDA buckets `b7_interaction_rank.md` §3.3 already "
      "measured. **The two are not the same kind of source and the asymmetry "
      "travels with every DTI band quoted.** Every coarse grid merges levels "
      "of its own fine grid and introduces no new boundary.\n")
    A("`b7_interaction_rank.md` §2.4 requires a class index to move with the "
      "borrower. **Nothing is excluded here; C9 is a census and the exclusion "
      "is B8-4's decision.**\n")
    A("| grid | levels seen | §2.4 moves with | missing as a level |")
    A("|---|---|---|---|")
    for r in res:
        A(f"| `{r.name}` | {r.n_levels} | {SEC24[r.name]} | "
          f"{r.na_level_n:,} |")

    A("\n## 2. The gate: cells at or above the floor\n")
    A("Cells are `(level x window)` over §6's four windows, pooled across the "
      "six archives. **`min cell` is the statistic §15.3 asks for.** Loans "
      "sitting in short cells are counted because §7 requires every exclusion "
      "to carry its count.\n")
    A("**Every level counted, nothing excluded.** The verdict is in §2.1, "
      "which applies the ruling; this table is the raw census it rests on.\n")
    A(f"| grid | cells | at or above {MIN_SIZE} | short | empty | loans lost "
      f"to short cells | min cell, all levels | on which level |")
    A("|---|---|---|---|---|---|---|---|")
    for r in res:
        A(f"| `{r.name}` | {r.cells} | {r.n_ok} | {r.n_short} | {r.n_empty} | "
          f"{r.loans_in_short:,} | **{r.min_cell:,}** | {r.argmin} |")

    A("\n### 2.1 The verdict, on the ruling of 2026-08-16\n")
    A("**the author ruled that a blank class field and a self-reported unknown code "
      "are both excluded, each carrying its count.** Neither is an agent "
      "class; both are measurement gaps, and §7's form for a measurement gap "
      "is exclusion with the count printed. **The all-levels-kept column is "
      "retained beside it as the double report**, so the effect of the ruling "
      "is visible rather than absorbed.\n")
    A(f"| grid | min, all levels kept | on which level | "
      f"**min, ruling applied** | **on which level** | loans excluded | "
      f"**B8-4 runs?** | **the ruling decided it?** |")
    A("|---|---|---|---|---|---|---|---|")
    for r in res:
        a_ok = r.min_cell >= MIN_SIZE
        b_ok = r.min_ex_blank >= MIN_SIZE
        A(f"| `{r.name}` | {r.min_cell:,} | {r.argmin} | "
          f"**{r.min_ex_blank:,}** | {r.argmin_ex_blank} | "
          f"{r.blank_loans:,} | **{'yes' if b_ok else 'no'}** | "
          f"**{'YES' if a_ok != b_ok else 'no'}** |")
    A("\n**What was excluded, and on what basis.** C0b identifies a field by "
      "behaviour, never by the look of its values or by the layout document. "
      "A blank meets that standard: the field is absent. **`purpose`'s `U` "
      "does not** and is marked, excluded per the ruling with its count "
      "printed. **Nothing downstream may treat `U` as identified.**\n")
    A("| grid | level | basis | loans |")
    A("|---|---|---|---|")
    for r in res:
        for lab_v, why in EXCLUDED.get(r.name, {}).items():
            A(f"| `{r.name}` | `{level_name(r.name, lab_v)}` | {why} | "
              f"{r.excluded_detail.get(lab_v, 0):,} |")
    A("\n**A `no` is not a failure of B8** (§15.3). It says B8-4 does not run "
      "on that grid, and it must not be written as a failure.\n")
    A("**Read the §2.4 column of §1 beside this one.** A grid that passes the "
      "floor and fails §2.4 is not a grid B8-4 may use; the two tests are "
      "independent and both bind.\n")

    A("\n## 3. The whole distribution, not the mean\n")
    A("| grid | min | p10 | p25 | p50 | p75 | p90 | max |")
    A("|---|---|---|---|---|---|---|---|")
    for r in res:
        if r.quant:
            A(f"| `{r.name}` | " + " | ".join(f"{x:,}" for x in r.quant) + " |")

    A("\nPer-window minimum over levels, which is where a grid dies.\n")
    A("| grid | " + " | ".join(WINDOWS_SEC6) + " |")
    A("|---|" + "---|" * len(WINDOWS_SEC6))
    for r in res:
        A(f"| `{r.name}` | " +
          " | ".join(f"{r.per_window_min.get(w, 0):,}" for w in WINDOWS_SEC6)
          + " |")

    A("\n## 4. B8-4b's axis: class by origination cohort, inside Flex\n")
    A("§15.5's B8-4b is the discriminating arm and its axis is the origination "
      "cohort **inside the Flex window**. The archives are origination "
      "quarters, so the axis is the six of them. Cells are "
      "`(level x cohort)` on Flex-window triangles only.\n")
    A(f"| grid | cells | at or above {MIN_SIZE} | short | empty | "
      f"**min cell** | on which level | **min, blank dropped** | "
      f"on which level | **B8-4b runs?** |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in res_flex_cohort:
        ok = r.min_ex_blank >= MIN_SIZE
        A(f"| `{r.name}` | {r.cells} | {r.n_ok} | {r.n_short} | {r.n_empty} | "
          f"**{r.min_cell:,}** | {r.argmin} | **{r.min_ex_blank:,}** | "
          f"{r.argmin_ex_blank} | "
          f"**{'yes' if ok else 'no'}** |")
    A("\n**The verdict column here is on the blank-dropped minimum**, which is "
      "the more permissive of the two. A `no` under the permissive reading is "
      "a `no` under either.\n")

    A("\n## What this does not decide\n")
    A("- **It does not license B8-4 on a grid it passes.** C9 is a count. "
      "§15.5's two further requirements, equal `n` after subsampling and "
      "printing the loading, are not counts and are not checked here.")
    A("- **It does not exclude any class index.** §2.4's verdict is printed in "
      "§1 and acted on in B8-4, not here.")
    A("- **It does not settle whether a passing grid is the right grid.** "
      "§3.3's finding is that the reading depends on *which* levels are "
      "merged, so a grid passing C9 is a grid on which the reading can be "
      "attempted, not one on which it is trustworthy.")
    A("- It reads no prediction, so no result here is quotable as a finding "
      "about the economy.\n")
    return "\n".join(L) + "\n"


def selftest() -> int:
    """The banders, on values chosen so each lands on a named edge."""
    fails = []
    NA = K.U16_NA

    f = np.array([600, 639, 640, 659, 660, 700, 759, 760, 779, 780, 850, NA],
                 dtype=np.uint16)
    got = _fico_grids(f)["fico_llpa9"]
    want = [0, 0, 1, 1, 2, 4, 6, 7, 7, 8, 8, 99]
    if list(got) != want:
        fails.append(f"fico_llpa9 {list(got)} != {want}")

    v = np.array([29, 30, 31, 60, 61, 80, 81, 95, 96, NA], dtype=np.uint16)
    got = _ltv_grids(v)["ltv_llpa9"]
    want = [0, 0, 1, 1, 2, 4, 5, 7, 8, 99]
    if list(got) != want:
        fails.append(f"ltv_llpa9 {list(got)} != {want}")

    d = np.array([19, 20, 29, 30, 35, 36, 37, 49, 50, 60, 61, NA],
                 dtype=np.uint16)
    g = _dti_grids(d)
    if list(g["dti_fine19"]) != [0, 1, 1, 2, 2, 3, 4, 16, 17, 17, 18, 99]:
        fails.append(f"dti_fine19 {list(g['dti_fine19'])}")
    if list(g["dti_coarse6"]) != [0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 5, 99]:
        fails.append(f"dti_coarse6 {list(g['dti_coarse6'])}")
    if list(g["dti_complement15"]) != [14, 14, 14, 14, 14, 0, 1, 13, 14, 14,
                                       14, 99]:
        fails.append(f"dti_complement15 {list(g['dti_complement15'])}")

    # the three DTI grids must be exactly §3.3's 19 / 6 / 15 on full support
    full = np.arange(0, 101, dtype=np.uint16)
    g = _dti_grids(full)
    for nm, want_n in (("dti_fine19", 19), ("dti_coarse6", 6),
                       ("dti_complement15", 15)):
        n = int(np.unique(g[nm]).size)
        if n != want_n:
            fails.append(f"{nm} has {n} levels on full support, §3.3 says "
                         f"{want_n}")

    # a coarse grid must be a merge of its fine grid: two values in the same
    # fine level can never fall in different coarse levels.
    for fine_n, coarse_n, mk in (("fico_llpa9", "fico_llpa_coarse5",
                                  lambda x: _fico_grids(x)),
                                 ("ltv_llpa9", "ltv_llpa_coarse4",
                                  lambda x: _ltv_grids(x)),
                                 ("dti_fine19", "dti_coarse6",
                                  lambda x: _dti_grids(x))):
        x = np.arange(0, 101, dtype=np.uint16)
        gg = mk(x)
        fi, co = gg[fine_n], gg[coarse_n]
        for lv in np.unique(fi):
            if np.unique(co[fi == lv]).size != 1:
                fails.append(f"{coarse_n} splits a level of {fine_n}, so it "
                             f"introduces a boundary {fine_n} does not have")
                break

    for f_ in fails:
        print("FAIL " + f_, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, banders on their edges and every coarse grid is a "
          "merge of its fine grid", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())

    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()
                   and not p.name.startswith("209")) if root.exists() else []
    if args.only:
        names = [n for n in names if n in set(args.only)]
    if not names:
        print("no core table. Run: python experiments/b8_core.py build",
              file=sys.stderr)
        raise SystemExit(1)

    per_cohort, lab, win, tri, q_same = collect(names)
    res = [score(lab[g], win, tri, WINDOWS_SEC6, g) for g in lab]

    # B8-4b: (level x cohort) inside Flex only
    flex = T.WINDOWS_INDEX["Flex"]
    res_fc = []
    for g in lab:
        counts, cellv, cellw = [], [], []
        lv = np.unique(lab[g][tri & (win == flex)])
        for n in names:
            t_, w_, g_ = per_cohort[n]
            m = t_ & (w_ == flex)
            counts.extend(int((m & (g_[g] == v)).sum()) for v in lv)
            cellv.extend(int(v) for v in lv)
            cellw.extend([n] * int(lv.size))
        a = np.asarray(counts, dtype=np.int64)
        cv = np.asarray(cellv)
        cw = np.asarray(cellw)
        r = GridResult(g, n_levels=int(lv.size), cells=int(a.size))
        r.n_ok = int((a >= MIN_SIZE).sum())
        r.n_short = int(((a > 0) & (a < MIN_SIZE)).sum())
        r.n_empty = int((a == 0).sum())
        r.min_cell = int(a.min()) if a.size else 0
        if a.size:
            j = int(a.argmin())
            r.argmin = f"`{level_name(g, int(cv[j]))}` in {cw[j]}"
            keep = ~np.isin(cv, list(EXCLUDED.get(g, {})))
            r.blank_loans = int(a[~keep].sum())
            if keep.any():
                b = a[keep]
                r.min_ex_blank = int(b.min())
                jj = int(b.argmin())
                r.argmin_ex_blank = (
                    f"`{level_name(g, int(cv[keep][jj]))}` in {cw[keep][jj]}")
        res_fc.append(r)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report(res, res_fc, q_same, names), encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT}", file=sys.stderr)
    worst = min((r.min_cell for r in res), default=0)
    best = max((r.min_cell for r in res), default=0)
    print(f"  min cell across grids: worst {worst:,}, best {best:,}, "
          f"floor {MIN_SIZE}", file=sys.stderr)


if __name__ == "__main__":
    main()
