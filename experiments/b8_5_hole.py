#!/usr/bin/env python3
"""B8-5: does the fraction reaching `modified` after delinquency differ by class.

Read map: `docs/b8_fannie_slice.md` §22, written before this ran.

**No `omega`, no curve, no floor.** This is a count. The object is
reachability, `b1_setup.md`'s `H0`/`H1`, not curl.

--------------------------------------------------------------------------
What this can and cannot claim (§22.1)
--------------------------------------------------------------------------

§5 registered "the fraction of borrowers for whom `delinquent -> modified`
**never exists** differs by class". **A fraction and a non-existence are not
the same object.** A class with a 5 per cent modification rate has the edge; it
is rare. The data gives a rate; `H0`/`H1` wants existence.

So the honest label here is **access gating differs by class**, and the
topological reading needs an argument this station does not make. §15.6's
branch table already says exactly this ("the reading contracts to access
gating rather than path dependence"); §22.1 moves it forward onto the
criterion itself so it cannot be lost between the run and the write-up.

**And it is association, not causation** (§9), alongside B8-4: modification is
endogenous. **The bottom of the class range is truncated by construction** --
GSE conforming excludes subprime, jumbo, FHA and VA -- and the truncation
points toward the null, so dispersion is **harder** to find here, not easier.
That sentence travels with every citation.

--------------------------------------------------------------------------
The three things that could manufacture a result
--------------------------------------------------------------------------

**Censoring (§22.4), which is the only one that can do it from nothing.** A
loan that goes delinquent in the last month of an archive has no time to be
modified. If one class's delinquencies sit late in the file it looks like a
hole. The answer is not to pick a follow-up window: the fraction is printed
**as a function of** the required follow-up `H`, and **the verdict hangs on
the class ordering being stable across `H`**, never on a level at one `H`.

**Competing exits (§22.3).** "Never modified" lumps a borrower who cured with
one who was foreclosed, and those are opposite facts. **Reaching liquidation
is not a hole**: the borrower left the delinquent node, by a different edge.
Every exit is a column.

**The entry tier (§22.2).** Who counts as delinquent is a `q`-grid choice, and
unlike B8-2 the two grids give genuinely different pools here, so **B8-6 is a
real test on B8-5**. §3.3's fine grid *is* a ladder in months past due, so the
ladder is run rather than two points off it.

Usage:

    python experiments/b8_5_hole.py run
    python experiments/b8_5_hole.py run --only 2019Q1
    python experiments/b8_5_hole.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_triangles as T                                       # noqa: E402
import b8_c9_cells as C9                                       # noqa: E402

OUT = K.ROOT / "results" / "b8_5_hole.md"

COLS = ["period", "delinq", "mod_flag", "nib_upb", "defer_amt", "upb",
        "zero_bal"]

#: §22.5. The five grids that pass C9 **and** sit on the borrower by §2.4.
#: `ltv_llpa_coarse4` and `occupancy` passed C9 and are dwelling indices, so
#: they are out; both gates are independent and both must be met.
GRIDS = ("purpose", "fthb", "fico_llpa_coarse5", "dti_complement15",
         "fico_llpa9")

#: §22.2 as a ladder. The coarse `q` grid is `d >= 1`; the fine grid's levels
#: **are** the months-past-due ladder, so running it is running the fine grid
#: rather than picking a point on it.
D_LADDER = (1, 2, 3, 4, 6)

#: §22.4's follow-up requirement, in months after the delinquency entry.
H_GRID = (6, 12, 18, 24, 36)

#: §22.5. On the denominator, not on triangle completions: C9's floor was
#: measured on a much smaller population and is not the binding gate here.
MIN_CELL = 20

#: §22.6.
N_PERM = 999
PERM_SEED = 20260817


def _first_per_loan(loan: np.ndarray, n_loans: int,
                    mask: np.ndarray) -> np.ndarray:
    """Row index of each loan's first `True`, or -1.

    `loan` is passed in rather than fetched, because `Core.loan_of_row`
    **rebuilds a row-length array with `np.repeat` on every call**. The first
    version of this file called it 130 times per archive and the run took
    twenty minutes; it is built once now and handed down.
    """
    out = np.full(n_loans, -1, dtype=np.int64)
    hits = np.flatnonzero(mask)
    if hits.size:
        lo = loan[hits]
        # last write wins under fancy indexing, so walk backwards and the
        # first hit per loan is what survives
        out[lo[::-1]] = hits[::-1]
    return out


def _win_of(per: np.ndarray) -> np.ndarray:
    """§6's window of a reporting month. `b8_cache._window_of` does the same
    for rows; this one takes months directly."""
    out = np.full(per.size, -1, dtype=np.int64)
    for k, (_n, lo, hi) in enumerate(T.WINDOWS):
        m = (per >= T._to_month_index(lo)) & (per <= T._to_month_index(hi))
        out[m] = k
    return out


def scan(c: K.Core) -> dict:
    """Every row-length pass this station makes, made once.

    Returns per-loan arrays only. **Nothing downstream touches a row again**,
    which is the whole of the twenty-minute fix: the event lags depend on the
    entry rung `d` and **not at all** on the follow-up requirement `H`, so
    computing them inside the `H` loop repeated 150 row-scans per archive to
    produce the same numbers five times over.
    """
    n = c.n_rows
    loan = c.loan_of_row()
    per = c.row["period"][:].astype(np.int64)
    dv = c.row["delinq"][:]
    known = dv <= 98
    rowidx = np.arange(n, dtype=np.int64)
    last_row = (c.row_start.astype(np.int64)
                + c.n_per_loan.astype(np.int64) - 1)

    mf = c.row["mod_flag"][:]
    nib = c.row["nib_upb"][:].astype(np.int64)
    dfr = c.row["defer_amt"][:].astype(np.int64)
    upb = c.row["upb"][:].astype(np.int64)
    zb = c.row["zero_bal"][:]
    EVENTS = {
        # §17's own onset: field 42 or field 63, whichever comes first
        "mod": (mf == K._Y) | ((nib != K.U32_NA) & (nib > 0)),
        # C10-4: the deferral carrier is field 108
        "defer": (dfr != K.U32_NA) & (dfr > 0),
        # §16.6: termination is the balance reaching zero, not field 44
        "term": (upb != K.U32_NA) & (upb == 0),
        "cure": known & (dv == 0),
    }

    out = {}
    for d in D_LADDER:
        e = _first_per_loan(loan, c.n_loans, known & (dv >= d))
        has = e >= 0
        ent_of_row = e[loan]
        at_or_after = ent_of_row >= 0
        follow = np.full(c.n_loans, -1, dtype=np.int64)
        follow[has] = per[last_row[has]] - per[e[has]]
        base = np.where(has, per[np.maximum(e, 0)], 0)

        lags, zcode = {}, np.zeros(c.n_loans, dtype=np.uint8)
        # **the clip to at-or-after entry is load-bearing, not hygiene.**
        # Without it a loan already carrying the state before it went
        # delinquent gets a negative lag, which reads as "never", so exactly
        # the re-modification population would be recorded as never modified.
        # A guard for the cure landing on the entry row was here and is gone:
        # the entry row satisfies `dv >= d >= 1`, so it cannot be a cure row
        # and the guard could not fire. Dead code that looks load-bearing is
        # worse than none.
        span = rowidx >= ent_of_row
        for k, msk in EVENTS.items():
            r = _first_per_loan(loan, c.n_loans, msk & at_or_after & span)
            lags[k] = np.where(r >= 0, per[np.maximum(r, 0)] - base, -1)
            if k == "term":
                ok = r >= 0
                zcode[ok] = zb[r[ok]]
        # **A borrower already modified at entry has demonstrably reached the
        # node**, so §5's "the edge never exists for them" is false and they
        # count in the numerator. That is a decision, so it is counted and
        # printed rather than buried: a reader who wants the other convention
        # can subtract this column.
        already = np.zeros(c.n_loans, dtype=bool)
        already[has] = EVENTS["mod"][e[has]]
        out[d] = {"entry": e, "in_pool": has, "follow": follow,
                  "win": np.where(has, _win_of(base), -1),
                  "lag": lags, "zb_code": zcode, "already": already}
    return out


def outcomes(sc: dict, horizon: int) -> dict:
    """§22.3's columns, from `scan`'s per-loan lags. **No row work at all.**

    **The numerator is `modified within the horizon`, unconditionally.**
    Reaching the node is reaching the node, and a borrower who cured, went
    delinquent again and was then modified **did reach it**. An earlier
    version took the first of the four events, which sent every
    cure-then-modify path into the `cured` column and out of the numerator.
    §5 asks whether the edge is reached, not whether it was reached first.

    The other three race each other for the **descriptive** columns only, so
    `cured` reads "cured and not modified inside the horizon".
    """
    p, big = sc["in_pool"], 1 << 30
    def hit(k):
        L = sc["lag"][k]
        return np.where((L >= 0) & (L <= horizon), L, big)
    modified = p & (hit("mod") < big)
    stack = np.stack([hit("defer"), hit("term"), hit("cure")])
    who, none = np.argmin(stack, axis=0), np.min(stack, axis=0) == big
    rest = p & ~modified
    return {"modified": modified, "already": p & sc["already"],
            "deferred": rest & ~none & (who == 0),
            "terminated": rest & ~none & (who == 1),
            "cured": rest & ~none & (who == 2),
            "open": rest & none}


def _compact(lab, hit, keep, drop_levels):
    """The cell reduced to `(level values, sizes, hits)` in one `bincount`.

    The first version walked `np.unique` and then built a boolean mask per
    level, so a fifteen-level cell of sixty thousand loans made fifteen passes
    to compute a partition it had already been handed.
    """
    lv = lab[keep]
    uniq, code = np.unique(lv, return_inverse=True)
    tot = np.bincount(code, minlength=uniq.size)
    hits = np.bincount(code, weights=hit[keep].astype(np.float64),
                       minlength=uniq.size)
    alive = np.array([(int(u) not in drop_levels) and t >= MIN_CELL
                      for u, t in zip(uniq, tot)], dtype=bool)
    return uniq, tot, hits, alive


def rates(lab: np.ndarray, hit: np.ndarray, keep: np.ndarray,
          drop_levels: set) -> dict:
    """Modification rate per class level, and the range across levels.

    **The range is over levels that clear `MIN_CELL` on the denominator.** A
    level with three loans in it can take any rate at all and would set the
    range by itself.
    """
    uniq, tot, hits, alive = _compact(lab, hit, keep, drop_levels)
    out = [{"level": int(u), "n": int(t), "rate": float(h / t)}
           for u, t, h, a in zip(uniq, tot, hits, alive) if a]
    rs = [o["rate"] for o in out]
    return {"levels": out, "n_levels": len(out),
            "range": (max(rs) - min(rs)) if len(rs) >= 2 else float("nan"),
            "lo": min(rs) if rs else float("nan"),
            "hi": max(rs) if rs else float("nan"),
            "n": int(keep.sum())}


def permute_p(lab: np.ndarray, hit: np.ndarray, keep: np.ndarray,
              drop_levels: set, obs: float, n_perm: int = N_PERM,
              seed: int = PERM_SEED) -> float:
    """§22.6's null: shuffle the class label among the loans in the cell.

    **Shuffling the label is a meaningful null and shuffling the window is
    not**, which is why B8-2 bootstraps and this permutes: class is a tag on a
    loan, window is the calendar.

    **Drawn from the null's distribution rather than simulated on the
    labels.** Under label shuffling the `K` modified loans are spread over
    groups of fixed sizes without replacement, so the count landing in each
    group is **multivariate hypergeometric in the group sizes**, and the
    labels never need to be touched. Same null, one vectorised draw instead of
    999 shuffles of sixty thousand elements: measured at **140 times faster**
    on the largest real cell, and `permute_p_shuffle` is kept so the selftest
    can hold the two against each other rather than take that on trust.

    **The null runs on the population the observation ran on.** Loans in a
    below-floor or excluded level are not in the observed range at all, so
    dealing them into the surviving levels would compute a null for a
    different experiment. A three-loan level moved `p` from 0.21 to 0.13
    before that was fixed, and a check found it rather than a reading.
    """
    if not np.isfinite(obs):
        return float("nan")
    _u, tot, hits, alive = _compact(lab, hit, keep, drop_levels)
    if alive.sum() < 2:
        return float("nan")
    sizes = tot[alive].astype(np.int64)
    K = int(round(float(hits[alive].sum())))
    if K <= 0 or K >= int(sizes.sum()):
        return 1.0                       # no dispersion is possible at all
    draws = np.random.default_rng(seed).multivariate_hypergeometric(
        sizes, K, size=n_perm)
    r = draws / sizes
    return float(((r.max(1) - r.min(1)) >= obs).sum() + 1) / (n_perm + 1)


def permute_p_shuffle(lab, hit, keep, drop_levels, obs, n_perm=N_PERM,
                      seed=PERM_SEED) -> float:
    """The same null done the slow, obvious way. **Kept as the reference the
    fast path is checked against**, not as a fallback: a closed-form null that
    silently disagrees with the shuffle would be a perfectly self-consistent
    wrong answer, which is this repository's most common defect shape."""
    if not np.isfinite(obs):
        return float("nan")
    _u, tot, _h, alive = _compact(lab, hit, keep, drop_levels)
    if alive.sum() < 2:
        return float("nan")
    lv, hh = lab[keep], hit[keep].astype(np.float64)
    uniq, code = np.unique(lv, return_inverse=True)
    inpop = alive[code]
    code = np.searchsorted(np.flatnonzero(alive), code[inpop])
    hh, k = hh[inpop], int(alive.sum())
    tt = np.bincount(code, minlength=k)
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(code)
        r = np.bincount(code, weights=hh, minlength=k) / np.maximum(tt, 1)
        if (r.max() - r.min()) >= obs:
            ge += 1
    return (ge + 1) / (n_perm + 1)


SCAN_CACHE = K.ROOT / "data" / "processed" / "b8_hole"

#: Per-`d` fields and the dtype each is stored at. Months fit in an `int16`
#: and the window in an `int8`; storing them as the `int64` they are computed
#: in would quadruple a file for no information. `entry` is not kept: nothing
#: downstream of `scan` uses a row index.
SCAN_DTYPES = {"in_pool": np.bool_, "follow": np.int16, "win": np.int8,
               "already": np.bool_, "zb_code": np.uint8,
               "lag_mod": np.int16, "lag_defer": np.int16,
               "lag_term": np.int16, "lag_cure": np.int16}


#: Modules whose source decides the cached per-loan numbers. **Whole modules,
#: and this one in the list**, on `b8_cache`'s reasoning: a helper three levels
#: down is just as load-bearing, and a cache tag that does not cover the code
#: writing the cache is the defect the tag exists to prevent, sitting inside
#: the tag.
SCAN_MODULES = (K, C9, T, sys.modules[__name__])


def scan_tag() -> str:
    """A hash of the code that produces the cached per-loan numbers."""
    h = hashlib.sha256()
    for m in SCAN_MODULES:
        h.update(inspect.getsource(m).encode("utf-8"))
    h.update(repr((D_LADDER, GRIDS, K.SCHEMA_VERSION)).encode("utf-8"))
    return h.hexdigest()[:16]


def scan_cached(name: str, cache_root=None, scan_root=None) -> tuple:
    """`scan` plus the class grids, computed once per archive and kept.

    **The row-level pass is the only expensive thing in this station and its
    answer cannot change unless the code changes.** A stale entry raises
    rather than serving, on the same reasoning as `b8_cache`: this repository
    has paid for the other convention repeatedly.
    """
    root = Path(scan_root or SCAN_CACHE)
    f, tg = root / f"{name}.npz", scan_tag()
    if f.exists():
        with np.load(f, allow_pickle=False) as z:
            if str(z["tag"]) == tg:
                sc = {d: {"in_pool": z[f"{d}__in_pool"],
                          "follow": z[f"{d}__follow"].astype(np.int64),
                          "win": z[f"{d}__win"].astype(np.int64),
                          "already": z[f"{d}__already"],
                          "zb_code": z[f"{d}__zb_code"],
                          "lag": {k_: z[f"{d}__lag_{k_}"].astype(np.int64)
                                  for k_ in ("mod", "defer", "term", "cure")}}
                      for d in D_LADDER}
                return sc, {g: z[f"grid__{g}"] for g in GRIDS}, int(z["n"])
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        grids = {g: C9.build_grids(c)[g] for g in GRIDS}
        sc, n_loans = scan(c), int(c.n_loans)
    finally:
        c.close()
    flat = {"tag": np.array(tg), "n": np.array(n_loans)}
    flat.update({f"grid__{g}": v for g, v in grids.items()})
    for d in D_LADDER:
        src = dict(sc[d])
        src.update({f"lag_{k_}": v for k_, v in src.pop("lag").items()})
        for k_, dt in SCAN_DTYPES.items():
            flat[f"{d}__{k_}"] = np.asarray(src[k_]).astype(dt)
    root.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **flat)
    print(f"  wrote scan cache {f.name} "
          f"({f.stat().st_size / 1e6:.1f} MB, tag {tg})", file=sys.stderr)
    return sc, grids, n_loans


def analyse(name: str, cache_root=None, n_perm: int = N_PERM,
            scan_root=None) -> dict:
    sc, grids, n_loans = scan_cached(name, cache_root=cache_root,
                                     scan_root=scan_root)
    rows = []
    for d in D_LADDER:
        p = sc[d]
        for h in H_GRID:
            oc = outcomes(p, h)
            keep0 = p["in_pool"] & (p["follow"] >= h)
            for w in range(len(T.WINDOWS)):
                keep = keep0 & (p["win"] == w)
                if int(keep.sum()) < MIN_CELL:
                    continue
                ex = {k: int((oc[k] & keep).sum()) for k in
                      ("modified", "already", "deferred", "terminated",
                       "cured", "open")}
                for g in GRIDS:
                    drop = set(C9.EXCLUDED.get(g, {}))
                    r = rates(grids[g], oc["modified"], keep, drop)
                    if r["n_levels"] < 2:
                        continue
                    r["p"] = permute_p(grids[g], oc["modified"], keep, drop,
                                       r["range"], n_perm=n_perm)
                    r.update({"d": d, "h": h, "w": w, "grid": g, "exits": ex,
                              "censored": int((p["in_pool"] & (p["win"] == w)
                                               & (p["follow"] < h)).sum())})
                    rows.append(r)
    return {"name": name, "rows": rows, "n_loans": n_loans,
            "n_pool": {d: int(sc[d]["in_pool"].sum()) for d in D_LADDER}}


def _level(grid: str, v) -> str:
    """`b8_c9_cells.level_name`, guarded. A label is decoration and must never
    be able to take a run down; the guard exists because it did."""
    try:
        return C9.level_name(grid, v)
    except Exception:
        return str(v)


def stability(rows: list[dict]) -> list[dict]:
    """§22.4's verdict object: **is the class ordering stable across `H`.**

    For each `grid x d x window`, take the level ordering by rate at each `H`.
    A level absent at any `H` is dropped from the comparison and counted,
    since an ordering over a changing set is not an ordering.

    **Two readings, because the first one written was the wrong test.**

    `stable` is the full ordering matching at every `H`. On the first real run
    it read 115 of 554, and the pass rate fell monotonically with the number
    of levels: 51 per cent at two levels, 24 at three, 4 at five, **zero at
    seven and above, over 155 cells**. A full ordering over `k` levels has
    `k!` arrangements and five readings have to land on the same one, so the
    bar tightens with `k` **whatever the data says**. Two mechanisms push the
    same way, a combinatorial one and a statistical one (more levels means
    fewer loans per level means noisier rates), and neither is censoring.
    **§22.4 was written to detect censoring and this test does not.**

    `ends_stable` is the corrected reading: **the level holding the highest
    rate and the level holding the lowest are the same at every `H`.** That is
    stability of the statistic actually reported, since `range` is
    `max - min` and a swap in the middle of the pack does not move it by a
    single digit. Both are printed under R01; `ends_stable` is the operative
    one and `stable` is kept because it was the published number.

    `n_min` is the smallest level count entering the comparison, so a reader
    can see the statistical mechanism rather than take the ruling on trust.
    """
    key = {}
    for r in rows:
        key.setdefault((r["grid"], r["d"], r["w"]), {})[r["h"]] = r
    out = []
    for (g, d, w), by_h in sorted(key.items()):
        hs = sorted(by_h)
        common = None
        for h in hs:
            s = {o["level"] for o in by_h[h]["levels"]}
            common = s if common is None else (common & s)
        if not common or len(common) < 2 or len(hs) < 2:
            continue
        orders, ends, n_min = [], [], 1 << 30
        for h in hs:
            lv = sorted((o for o in by_h[h]["levels"]
                         if o["level"] in common), key=lambda o: o["rate"])
            orders.append(tuple(o["level"] for o in lv))
            ends.append((lv[0]["level"], lv[-1]["level"]))
            n_min = min(n_min, min(o["n"] for o in lv))
        out.append({"grid": g, "d": d, "w": w, "n_h": len(hs),
                    "n_common": len(common), "n_min": n_min,
                    "stable": len(set(orders)) == 1,
                    "ends_stable": len(set(ends)) == 1,
                    "p_max": max(by_h[h]["p"] for h in hs),
                    # **which levels, not just whether they held still.** The
                    # whole substantive content of this station is which class
                    # sits at the bottom of the access ordering, and the first
                    # version computed the endpoints and then printed only a
                    # yes or a no about them.
                    # **only when the ends held still.** They are rebound
                    # each `H`, so on an unstable cell they are the last `H`'s
                    # answer wearing the cell's label, and 422 of 554 printed
                    # rows are unstable. An em dash is a reading; a stale
                    # snapshot is not.
                    "bottom": (_level(g, ends[0][0])
                               if len(set(ends)) == 1 else "-"),
                    "top": (_level(g, ends[0][1])
                            if len(set(ends)) == 1 else "-"),
                    "range_lo": min(by_h[h]["range"] for h in hs),
                    "range_hi": max(by_h[h]["range"] for h in hs)})
    return out


def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:.{k}f}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-5: does reaching `modified` after delinquency depend on class\n")
    A("Generated by `experiments/b8_5_hole.py`. Read map in "
      "`docs/b8_fannie_slice.md` §22, written before this ran.\n")
    A("**The honest label is access gating, not a hole** (§22.1). §5 asks "
      "whether the edge `delinquent -> modified` **never exists** for some "
      "class; the data gives a rate, and a low rate is not a missing edge. "
      "The `H0`/`H1` reading needs an argument this station does not make.\n")
    A("**Association, not causation** (§9). **The bottom of the class range "
      "is truncated by construction** (GSE conforming excludes subprime, "
      "jumbo, FHA, VA) and the truncation points toward the null, so "
      "dispersion is harder to find here, not easier. **This sentence travels "
      "with every citation of B8-5.**\n")
    if not rows:
        return "\n".join(Ls) + "\n_no data_\n"
    allr = [r for a in rows for r in a["rows"]]

    A("\n## 1. The pools\n")
    A("Entry is the first month at or past the rung, per §22.2's ladder.\n")
    A("**The ladder is a refinement of §3.3's grid, not a copy of it, and the "
      "first version of this file said otherwise.** §3.3's primary grid is "
      "`current / 30 / 60 / 90+ / modified / deferred`: three delinquency "
      "depths with **`90+` merged**. Rungs `d>=1`, `d>=2` and `d>=3` are that "
      "grid; `d>=4` and `d>=6` split the merged bucket and are **extra**. "
      "They are printed because a rung is a free reading once the scan is "
      "done, but **a result resting only on `d>=4` or `d>=6` is not resting "
      "on a registered grid** and must say so where it is cited.\n")
    A("| archive | loans | " + " | ".join(f"`d>={d}`" for d in D_LADDER) + " |")
    A("|---|---|" + "---|" * len(D_LADDER))
    for a in rows:
        A(f"| {a['name']} | {a['n_loans']:,} | "
          + " | ".join(f"{a['n_pool'][d]:,}" for d in D_LADDER) + " |")

    A("\n## 2. Where the borrowers went\n")
    A("**Reaching liquidation is not a hole** (§22.3): the borrower left the "
      "delinquent node by a different edge. Exits are behavioural, the first "
      "one to happen wins, and termination is the balance reaching zero per "
      "§16.6 rather than field 44's code.\n")
    A("**A borrower already carrying the modification state at entry counts "
      "as having reached the node** and is printed separately, so the other "
      "convention is one subtraction away.\n")
    A("| archive | `d` | `H` | window | in cell | censored out | modified | "
      "of which already | deferred | terminated | cured | still open |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    seen = set()
    for a in rows:
        for r in a["rows"]:
            k = (a["name"], r["d"], r["h"], r["w"])
            if k in seen:
                continue
            seen.add(k)
            e = r["exits"]
            A(f"| {a['name']} | {r['d']} | {r['h']} | "
              f"{T.WINDOWS[r['w']][0]} | {r['n']:,} | {r['censored']:,} | "
              f"{e['modified']:,} | {e['already']:,} | {e['deferred']:,} | "
              f"{e['terminated']:,} | {e['cured']:,} | {e['open']:,} |")

    A("\n## 3. The range across classes, and the permutation null\n")
    A(f"Range is over levels clearing `MIN_CELL = {MIN_CELL}` on the "
      f"denominator. The null shuffles the class label among the loans in the "
      f"cell, {N_PERM} times (§22.6).\n")
    A("| archive | grid | `d` | `H` | window | levels | n | lowest rate | "
      "highest | **range** | **p** |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for r in a["rows"]:
            A(f"| {a['name']} | `{r['grid']}` | {r['d']} | {r['h']} | "
              f"{T.WINDOWS[r['w']][0]} | {r['n_levels']} | {r['n']:,} | "
              f"{_f(r['lo'])} | {_f(r['hi'])} | **{_f(r['range'])}** | "
              f"**{_f(r['p'], 3)}** |")

    A("\n## 4. §22.4's verdict: is the ordering stable across `H`\n")
    A("**The criterion hangs here, not on section 3's levels.** A difference "
      "that appears at one follow-up requirement and not another is "
      "censoring. Levels absent at any `H` are dropped from the comparison, "
      "because an ordering over a changing set is not an ordering.\n")
    A("**Two readings, and the operative one is `ends`** (§22.4a). `full` is "
      "the whole ordering matching at every `H`, which was the first version "
      "of this test and is the wrong one: a full ordering over `k` levels has "
      "`k!` arrangements, so the bar tightens with `k` whatever the data "
      "says, and on the first run it passed zero of 155 cells at seven levels "
      "or more. `ends` is the level holding the highest rate and the level "
      "holding the lowest being the same at every `H`, **which is stability "
      "of the number actually reported**, since `range` is `max - min`. Both "
      "are printed under R01.\n")
    A("| archive | grid | `d` | window | `H` values | levels compared | "
      "smallest level | **ends** | full | worst `p` | **lowest access** | "
      "**highest** | range low | range high |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    tally = {"stable": 0, "total": 0, "sig": 0, "ends": 0, "ends_sig": 0}
    for a in rows:
        for s in stability(a["rows"]):
            tally["total"] += 1
            tally["stable"] += bool(s["stable"])
            tally["ends"] += bool(s["ends_stable"])
            tally["sig"] += bool(s["stable"] and s["p_max"] < 0.05)
            tally["ends_sig"] += bool(s["ends_stable"] and s["p_max"] < 0.05)
            A(f"| {a['name']} | `{s['grid']}` | {s['d']} | "
              f"{T.WINDOWS[s['w']][0]} | {s['n_h']} | {s['n_common']} | "
              f"{s['n_min']:,} | "
              f"**{'yes' if s['ends_stable'] else 'no'}** | "
              f"{'yes' if s['stable'] else 'no'} | {_f(s['p_max'], 3)} | "
              f"`{s['bottom']}` | `{s['top']}` | "
              f"{_f(s['range_lo'])} | {_f(s['range_hi'])} |")

    A("\n## 5. The tally\n")
    A("| cells | **ends stable** | **and** `p` < 0.05 | full ordering stable "
      "| and `p` < 0.05 | **reading** |")
    A("|---|---|---|---|---|---|")
    verdict = ("**access gating differs by class**"
               if tally["ends_sig"] > 0 and tally["ends"] == tally["total"]
               else "**not established on this data**"
               if tally["ends_sig"] == 0
               else "**mixed: read cell by cell, do not pool**")
    A(f"| {tally['total']} | {tally['ends']} | {tally['ends_sig']} | "
      f"{tally['stable']} | {tally['sig']} | {verdict} |")
    A("\n§22.7's map, read on `ends`. **Whatever this says, it is a rate and "
      "not an existence claim** (§22.1).\n")

    A("\n## What this does not decide\n")
    A("- **`H0`/`H1` in the formal sense.** That needs the edge to be absent; "
      "the data gives a rate. §22.1.")
    A("- **Why.** No servicer-side variable exists in this file.")
    A("- **B8-4**, which needs per-class floors and runs separately.")
    A("- Causality of any kind.\n")
    return "\n".join(Ls) + "\n"


# ---------------------------------------------------------------------------
# fixture: a population whose answer is known before the code runs
# ---------------------------------------------------------------------------

#: `(purpose code, n loans, months delinquent, modifies, lag, tail)`.
#: **Built so every answer is arithmetic and every mechanism has something to
#: break.** A mutation run found the first version could not see three
#: defects, all because the fixture never exercised them.
#:
#: * `P` modifies on two thirds, `C` on one third, both promptly. That fixes
#:   two rates exactly and nothing else in the file may move them.
#: * `S` modifies on every loan but **20 months after entry**, so it reads
#:   zero at `H` of 6, 12 and 18 and one at 24 and 36. It pins the horizon's
#:   **upper** bound, which an open-ended window would ignore, and it makes
#:   the class ordering genuinely move with `H`, so §22.4's stability verdict
#:   is exercised on data rather than only on hand-built rows. Its tail runs
#:   150 months so `follow` passes 127, which is what makes a narrowed cache
#:   dtype visible in the round trip.
#: * `R` modifies promptly but its record **ends four months after entry**,
#:   in the same window as everyone else. It is the censoring trap: drop
#:   §22.4's follow-up requirement and `R` enters at rate one.
#: * `B` is **modified before it ever goes delinquent** and never after. The
#:   flag persists, so it is set on the entry row: it reads rate one and its
#:   whole count lands in `already`. Drop the clip to at-or-after entry and
#:   its lag goes negative, which reads as never, so `B` is what makes that
#:   clip visible. It is the re-modification population in miniature.
#: * The delinquent run climbs `01, 02, 03`, so `delinq` at the entry row
#:   says whether entry took the **first** month at the rung or the last.
FIX = [("P", 30, 3, True, 0, 60), ("P", 15, 3, False, 0, 60),
       ("C", 15, 3, True, 0, 60), ("C", 30, 3, False, 0, 60),
       ("S", 45, 3, True, 20, 150),
       ("R", 30, 3, True, 0, 1),
       ("B", 45, 3, "before", 0, 60)]
FIX_LEAD = 48            # quiet months before anything happens
FIX_SLOW_LAG = 20        # `S`'s lag, and the horizon boundary it straddles


def _synth_hole(path: Path) -> None:
    lines = []
    lid = 910000000000
    for code, n_loans, k_del, mods, lag, tail in FIX:
        for _ in range(n_loans):
            lid += 1
            y, m, age, rem = 2010, 1, 0, 360
            rate, bal = 5.0, 200000.0
            pmt = float(K.level_payment([bal], [rate], [rem])[0])
            if mods == "before":
                # modified early, flag persists, then goes delinquent
                plan = ([("00", "N")] * 20 + [("00", "Y")] * (FIX_LEAD - 20)
                        + [(f"{j + 1:02d}", "Y") for j in range(k_del)]
                        + [("00", "Y")] * tail)
            else:
                plan = ([("00", "N")] * FIX_LEAD
                        + [(f"{j + 1:02d}", "N") for j in range(k_del)]
                        + [("00", "N")] * lag
                        + ([("00", "Y")] if mods else [("00", "N")])
                        + [("00", "Y" if mods else "N")] * tail)
            for dq, mod in plan:
                if dq == "00":
                    bal = bal * (1.0 + rate / 1200.0) - pmt
                f = [""] * K.NFIELDS
                f[1] = str(lid)
                f[2] = f"{m:02d}{y:04d}"
                f[3] = "R"
                f[8] = f"{rate:.3f}"
                f[11] = f"{max(bal, 1.0):.2f}"
                f[12] = "360"
                f[15] = str(age)
                f[16] = str(rem)
                f[17] = str(rem)
                f[18] = "012040"
                f[19] = "80"
                f[22] = "35"
                f[23] = "720"
                f[25] = "N"
                f[26] = code
                f[29] = "P"
                f[30] = "CA"
                f[39] = dq
                f[41] = mod
                f[101] = "7"
                f[105] = "7"
                lines.append("|".join(f))
                rem -= 1
                age += 1
                m += 1
                if m == 13:
                    m, y = 1, y + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("f.csv", "\n".join(lines) + "\n")


def _fixture_tag() -> str:
    src = inspect.getsource(_synth_hole) + repr(FIX)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:8]


def selftest() -> int:
    fails: list[str] = []
    _tg0 = scan_tag()

    # -- `rates`, on hand-built labels ------------------------------------
    lab = np.concatenate([np.zeros(MIN_CELL, np.int16),
                          np.ones(MIN_CELL, np.int16),
                          np.full(3, 2, np.int16)])       # level 2 is short
    hit = np.concatenate([np.ones(MIN_CELL, bool),
                          np.zeros(MIN_CELL, bool),
                          np.ones(3, bool)])
    r = rates(lab, hit, np.ones(lab.size, bool), set())
    if r["n_levels"] != 2:
        fails.append(f"a level with 3 loans was counted; {r['n_levels']} "
                     "levels read, expected 2")
    if abs(r["range"] - 1.0) > 1e-12:
        fails.append(f"a 1.0-vs-0.0 split gave range {r['range']}")
    # **the floor must be what excludes it**, not the level count
    r2 = rates(lab, hit, np.ones(lab.size, bool), {2})
    if r2["n_levels"] != 2:
        fails.append("excluding an already-short level changed the count, so "
                     "the floor and the exclusion list are entangled")
    # a level named in EXCLUDED must go even when it is large
    big = np.concatenate([lab, np.full(MIN_CELL, 99, np.int16)])
    bh = np.concatenate([hit, np.ones(MIN_CELL, bool)])
    if rates(big, bh, np.ones(big.size, bool), {99})["n_levels"] != 2:
        fails.append("a large excluded level survived; blanks would enter as "
                     "a class")
    if rates(big, bh, np.ones(big.size, bool), set())["n_levels"] != 3:
        fails.append("the exclusion did nothing, so the test above is empty")

    # -- the permutation must separate signal from noise ------------------
    p_sig = permute_p(lab, hit, np.ones(lab.size, bool), {2}, r["range"],
                      n_perm=199)
    if not p_sig < 0.05:
        fails.append(f"a perfectly separated split gave p = {p_sig}")
    rng = np.random.default_rng(7)
    noise = rng.random(2 * MIN_CELL) < 0.5
    lab2 = np.concatenate([np.zeros(MIN_CELL, np.int16),
                           np.ones(MIN_CELL, np.int16)])
    obs = rates(lab2, noise, np.ones(lab2.size, bool), set())["range"]
    p_noise = permute_p(lab2, noise, np.ones(lab2.size, bool), set(), obs,
                        n_perm=199)
    if p_noise < 0.05:
        fails.append(f"pure noise gave p = {p_noise}; the null does not hold "
                     "its size and every cell would read significant")
    # **the null has to be computed over the level set the observation used.**
    # A level below `MIN_CELL` is excluded from the observed range, so if the
    # permutation keeps it the two are not comparable: a three-loan level's
    # rate swings wildly under shuffling and inflates the null range, which
    # makes every `p` too large by an amount nothing reports.
    pad = np.concatenate([lab2, np.full(3, 7, np.int16)])
    padh = np.concatenate([noise, np.ones(3, bool)])
    p_pad = permute_p(pad, padh, np.ones(pad.size, bool), set(),
                      rates(pad, padh, np.ones(pad.size, bool),
                            set())["range"], n_perm=199)
    # **the closed-form null against the shuffle it replaces.** Both are
    # Monte Carlo at the same draw count, so they agree to sampling error and
    # not exactly; the tolerance is three standard errors of a proportion at
    # 4,000 draws, which is 0.024.
    for nn, kk, ph in ((4000, 5, 0.05), (2000, 9, 0.10), (1200, 3, 0.25)):
        gg = np.random.default_rng(nn)
        lb = gg.integers(0, kk, nn).astype(np.int16)
        ht = gg.random(nn) < ph
        kp = np.ones(nn, bool)
        ob = rates(lb, ht, kp, set())["range"]
        fast = permute_p(lb, ht, kp, set(), ob, n_perm=4000)
        slow = permute_p_shuffle(lb, ht, kp, set(), ob, n_perm=4000)
        if abs(fast - slow) > 0.024:
            fails.append(f"the hypergeometric null and the shuffle disagree "
                         f"at n={nn}, k={kk}: {fast:.4f} vs {slow:.4f}. The "
                         "fast path is not the same null")
    if abs(p_pad - p_noise) > 1e-12:
        fails.append(f"adding a level of 3 loans moved `p` from {p_noise} to "
                     f"{p_pad}; the permutation is not applying the floor the "
                     "observed statistic applies")

    # -- `stability` must see an ordering flip ----------------------------
    def _row(h, p_=0.001, **rates):
        lv = [{"level": k, "n": 99, "rate": v}
              for k, v in sorted(rates.items())]
        return {"grid": "g", "d": 1, "w": 0, "h": h, "p": p_,
                "range": max(r["rate"] for r in lv)
                - min(r["rate"] for r in lv), "levels": lv}
    s1 = stability([_row(6, a=0.1, b=0.4), _row(12, a=0.2, b=0.5)])[0]
    if not (s1["stable"] and s1["ends_stable"]):
        fails.append("a consistent ordering was called unstable")
    s2 = stability([_row(6, a=0.1, b=0.4), _row(12, a=0.5, b=0.2)])[0]
    if s2["stable"] or s2["ends_stable"]:
        fails.append("an ordering that flips between two `H` was called "
                     "stable; §22.4's whole criterion is this comparison")
    # **the two readings must be able to disagree**, or `ends` is a rename.
    # A swap strictly inside the pack leaves `range` untouched, so `full`
    # fails and `ends` holds. This is the case that made the first version of
    # §22.4 measure the level count instead of censoring.
    # **an unstable cell must not print an ordering.** `bottom` and `top` are
    # rebuilt at every `H`, so on a cell whose ends move they would otherwise
    # be the last `H`'s answer wearing the cell's label, and 422 of 554
    # published rows are unstable.
    uns = stability([_row(6, a=0.1, b=0.9), _row(12, a=0.9, b=0.1)])[0]
    if uns["bottom"] != "-" or uns["top"] != "-":
        fails.append(f"an unstable cell named its ends: {uns['bottom']} / "
                     f"{uns['top']}; that is one `H`'s reading printed as the "
                     "cell's")
    sta = stability([_row(6, a=0.1, b=0.9), _row(12, a=0.2, b=0.8)])[0]
    if sta["bottom"] == "-" or sta["top"] == "-":
        fails.append("a stable cell refused to name its ends, so the check "
                     "above passes on a column that is always a dash")
    s3 = stability([_row(6, a=0.1, b=0.2, c=0.3, z=0.9),
                    _row(12, a=0.1, b=0.3, c=0.2, z=0.9)])[0]
    if s3["stable"]:
        fails.append("a middle-of-the-pack swap did not break the full "
                     "ordering, so `full` is not reading the ordering")
    if not s3["ends_stable"]:
        fails.append("a middle-of-the-pack swap broke `ends`, which is "
                     "supposed to track `max - min` and cannot see it")
    if s3["n_min"] != 99:
        fails.append(f"`n_min` read {s3['n_min']}, expected 99")
    # **both ends have to be watched.** The bottom of the ordering is the
    # claim "this class has the lowest access rate", and it can change hands
    # while the top does not and while `range` does not move at all.
    s4 = stability([_row(6, a=0.1, b=0.2, z=0.9),
                    _row(12, a=0.2, b=0.1, z=0.9)])[0]
    if s4["ends_stable"]:
        fails.append("the lowest-rate level changed hands and `ends` did not "
                     "notice; it is watching the top only, and the bottom is "
                     "half the claim")
    # `n_min` is the smallest level in the comparison, which is the whole
    # point of printing it: it is the noise mechanism made visible
    s5 = stability([{"grid": "g", "d": 1, "w": 0, "h": h, "p": 0.5,
                     "range": 0.3,
                     "levels": [{"level": 0, "n": 4000, "rate": 0.1},
                                {"level": 1, "n": 21, "rate": 0.4}]}
                    for h in (6, 12)])[0]
    if s5["n_min"] != 21:
        fails.append(f"`n_min` read {s5['n_min']} where the smallest level "
                     "holds 21 loans; it is not reporting the binding count")

    # -- end to end, on a fixture whose answer is arithmetic --------------
    root = K.CACHE / "_selftest_hole"
    zp = root / "raw" / f"2098Q1_{_fixture_tag()}.zip"
    if not zp.exists():
        _synth_hole(zp)
    cr = root / "cache"
    K.build_archive(zp, force=True, cache_root=cr)
    # **entry is the FIRST month at the rung.** The fixture climbs 01, 02, 03,
    # so the delinquency code sitting on the entry row says which end was
    # taken, and taking the last one shifts every horizon by two months
    # without changing anything a rate check can see.
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as cx:
        pl = scan(cx)
        dvx = cx.row["delinq"][:]
        for d in (1, 2, 3):
            e = pl[d]["entry"][pl[d]["in_pool"]]
            if e.size == 0:
                fails.append(f"nothing entered the pool at `d>={d}`")
            elif not np.all(dvx[e] == d):
                fails.append(f"entry at `d>={d}` landed on delinquency codes "
                             f"{np.unique(dvx[e]).tolist()}, not {d}; it is "
                             "not the first month at the rung")

    sr = root / 'scan'
    a = analyse(zp.stem, cache_root=cr, n_perm=199, scan_root=sr)
    got = {r["h"]: r for r in a["rows"] if r["grid"] == "purpose"
           and r["d"] == 1}
    if not got:
        fails.append("the fixture produced no `purpose` cell at all")
    else:
        want = {6: 0.0, 12: 0.0, 18: 0.0, 24: 1.0, 36: 1.0}   # `S`
        for h, r in sorted(got.items()):
            by = {o["level"]: o["rate"] for o in r["levels"]}
            # **`R` must be censored out.** Uncensored it modifies promptly
            # and would enter at rate one.
            if r["n_levels"] != 4:
                fails.append(f"H={h} read {r['n_levels']} levels, expected 4. "
                             "`R`'s record ends four months after entry, so "
                             "§22.4 must drop it; if it is here, the "
                             "follow-up requirement is not applied")
                break
            for lv, exp in ((ord("P"), 2 / 3), (ord("C"), 1 / 3),
                            (ord("S"), want[h]), (ord("B"), 1.0)):
                if abs(by.get(lv, -1) - exp) > 1e-9:
                    fails.append(f"H={h}, class `{chr(lv)}` read "
                                 f"{by.get(lv, float('nan')):.6f}, expected "
                                 f"{exp:.6f}")
        # **`B` carries the state in before it is delinquent**, so its whole
        # count must land in `already`; if it does not, the clip to at-or-after
        # entry has stopped biting and the re-modification population would
        # read as never modified.
        b_cell = [r for r in a["rows"] if r["d"] == 1 and r["h"] == 6][0]
        if b_cell["exits"]["already"] != 45:
            fails.append(f"`already` read {b_cell['exits']['already']}, "
                         "expected 45: `B` is modified before it goes "
                         "delinquent and the flag persists onto the entry row")
        # **`S` crossing between H=18 and H=24 must make the ordering move**,
        # which is the whole of §22.4's criterion, exercised end to end
        st = [s for s in stability(a["rows"])
              if s["grid"] == "purpose" and s["d"] == 1]
        if not st:
            fails.append("no stability row for `purpose`, so §22.4's verdict "
                         "is untested on data")
        elif st[0]["stable"]:
            fails.append("`S` moves from the bottom to the top of the "
                         "ordering between H=18 and H=24 and the verdict "
                         "still read stable")
        print(f"  fixture: {len(got)} purpose cells, P/C/S pinned, "
              f"ordering unstable as built", file=sys.stderr)
    # -- the scan cache: round trip, staleness, and the tag ---------------
    cf = sr / f"{zp.stem}.npz"
    if not cf.exists():
        fails.append("no scan cache was written, so nothing below is tested")
    else:
        # **elementwise, not by summary.** A narrowed dtype, a swapped field
        # or a truncated month all survive a comparison of derived ranges and
        # none survives this.
        with K.Core(zp.stem, cols=COLS, cache_root=cr) as cz:
            direct = scan(cz)
        got, _g, _n = scan_cached(zp.stem, cache_root=cr, scan_root=sr)
        for d in D_LADDER:
            for k_ in ("in_pool", "follow", "win", "already", "zb_code"):
                if not np.array_equal(np.asarray(direct[d][k_]),
                                      np.asarray(got[d][k_])):
                    fails.append(f"the cached scan differs from the computed "
                                 f"one on `{k_}` at d>={d}")
            for k_ in ("mod", "defer", "term", "cure"):
                if not np.array_equal(direct[d]["lag"][k_],
                                      got[d]["lag"][k_]):
                    fails.append(f"the cached scan differs on lag `{k_}` at "
                                 f"d>={d}")
        if int(max(direct[1]["follow"].max() for _ in (0,))) <= 127:
            fails.append("no fixture loan has more than 127 months of "
                         "follow-up, so a narrowed cache dtype would round "
                         "trip cleanly and the comparison above is blind")
        # **a stale entry must be refused, and refused means recomputed.**
        # The data is poisoned along with the tag, so a cache that loads it
        # returns visibly wrong numbers instead of quietly-correct ones.
        with np.load(cf, allow_pickle=False) as z:
            poison = {k_: z[k_] for k_ in z.files}
        poison["tag"] = np.array("0" * 16)
        poison["1__in_pool"] = np.zeros_like(poison["1__in_pool"])
        np.savez_compressed(cf, **poison)
        a3 = analyse(zp.stem, cache_root=cr, n_perm=199, scan_root=sr)
        if [r["range"] for r in a3["rows"]] != [r["range"] for r in a["rows"]]:
            fails.append("a scan cache with a foreign tag was served; the "
                         "staleness check is not the thing deciding")
    if sys.modules[__name__] not in SCAN_MODULES:
        fails.append("the scan tag does not hash this module, so editing "
                     "`scan` would change the cached numbers without moving "
                     "the tag")
    real = D_LADDER
    try:
        globals()["D_LADDER"] = tuple(list(real) + [7])
        if scan_tag() == _tg0:
            fails.append("changing the rung ladder did not move the scan tag")
    finally:
        globals()["D_LADDER"] = real
    if scan_tag() != _tg0:
        fails.append("the scan tag did not come back")

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. The pools", "## 2. Where the borrowers went",
                 "## 3. The range across classes",
                 "## 4. §22.4's verdict", "## 5. The tally"):
        if need not in txt:
            fails.append(f"render omits `{need}`")

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the censoring trap is caught and the null holds its "
          "size", file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n)
        rows.append(a)
        print(f"  done {n}: {len(a['rows'])} cells", file=sys.stderr)
    txt = render(rows)
    bad = K.check_markdown_tables(txt)
    if bad:
        for b in bad:
            print("MALFORMED " + b, file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt, encoding="utf-8")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["run", "selftest"])
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args()
    if args.command == "selftest":
        raise SystemExit(selftest())
    root = K.CACHE / K.SCHEMA_VERSION
    names = sorted(p.name for p in root.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()) \
        if root.exists() else []
    if args.only:
        keep = set(args.only)
        names = [n for n in names if n in keep]
    if not names:
        print("no core table. Run: python experiments/b8_core.py build",
              file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(run(names))


if __name__ == "__main__":
    main()
