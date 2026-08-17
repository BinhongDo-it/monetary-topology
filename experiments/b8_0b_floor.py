#!/usr/bin/env python3
"""B8-0b: the noise floor for the loop sum.

Pre-registered in ``docs/b8_fannie_slice.md`` §18, **written before this ran and
not revisited** (§8). Read that section first; this file implements it and adds
nothing.

    Z := 2 * Var(omega)   over the loops being compared          §18.1
    N := 2 * Var(omega)   over CLEAN CURES, whose true value      §18.3
                          is zero by construction
    M := 2 * Var(omega)   within (arm, missed months, months to   §18.4
                          cure) cells, size-weighted

**`N` is the zero-calibration arm, not the matched-cell dispersion.** §18.2
settles that and gives three reasons; the load-bearing one is that matched-cell
dispersion is a *subset of the signal*, so using it as the floor drives the
ratio toward one by an amount that depends on how finely the cells are cut.
`M` is still computed and printed, because it says how much of `omega` the
realised path explains, which is B8-4's precondition. **It does not enter the
ratio.**

--------------------------------------------------------------------------
The clean cure's window
--------------------------------------------------------------------------

§18.3's N2: a clean cure has no modification onset, so `t_M` has no meaning
there. It is defined as **the first delinquent month**, which makes the window
`(t_A, t_B]` exactly as §17 defines it and keeps the three-leg split formally
valid. **`N` uses the loop sum only.** Leg 2 on this arm is not a
re-contracting and nothing here reads it.

--------------------------------------------------------------------------
Two computations of Z that must agree
--------------------------------------------------------------------------

`b3_cip_slice.md` B3-1, adopted verbatim: `Z` is computed by enumeration over
ordered pairs **and** as `2 * Var`, and they must agree to a relative error
below 1e-12. That is a gate on the code, not a reading. Enumeration is
quadratic, so it runs on a capped random sample and **the cap is printed**.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_omega as W                                           # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_loop_omega as Z8                                     # noqa: E402
import b8_0a_gate as G                                         # noqa: E402

OUT = K.ROOT / "results" / "b8_0b_floor.md"

#: **The column list `analyse` opens the core table with.** Pit 30.
COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq",
        "mod_flag", "nib_upb", "defer_amt"]

#: §6.4's floor on a cell, adopted by §18.4.
MIN_CELL = 20

#: How many loops the quadratic enumeration of `Z` is drawn from. **The cap is
#: printed**, because a silent truncation reads as full coverage.
ENUM_CAP = 3000

#: B3-1's tolerance on "the two computations of `Z` agree", verbatim.
ENUM_TOL = 1e-12

#: §3.3's coarse grid, reused as the cell edges for `M`. Months.
#: **Path quantities only.** §18.4 forbids any contract-derived key, because
#: `omega` is a function of the contract and cutting on it would drive the
#: within-cell variance to zero and the ratio to infinity. That is C11's
#: criterion B (§6.6.16) in a different costume, and that one was only caught
#: after the run.
EDGES_MISSED = (1, 2, 3, 6, 12)
EDGES_CURE = (0, 1, 2, 3, 6, 12)


def zed(x: np.ndarray) -> float:
    """`Z = 2 * Var(x)`, §18.1. Population variance, not the sample one."""
    x = np.asarray(x, dtype=np.float64)
    return 2.0 * float(np.var(x)) if x.size else float("nan")


def zed_by_enumeration(x: np.ndarray) -> float:
    """`(1/k^2) * sum over ordered pairs of (x_i - x_j)^2`, §18.1 verbatim.

    Quadratic. The caller caps the sample; this does no capping of its own so
    that what it is given is what it measures.
    """
    x = np.asarray(x, dtype=np.float64)
    k = x.size
    if k == 0:
        return float("nan")
    d = x[:, None] - x[None, :]
    return float((d * d).sum()) / (k * k)


def check_enumeration(x: np.ndarray, cap: int = ENUM_CAP,
                      seed: int = 20260817) -> dict:
    """B3-1: the two computations of `Z` must agree to machine precision."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return {"n": 0, "capped": False, "var": float("nan"),
                "enum": float("nan"), "rel": float("nan"), "ok": False}
    take = x
    capped = x.size > cap
    if capped:
        take = x[np.random.default_rng(seed).choice(x.size, cap,
                                                    replace=False)]
    v, e = zed(take), zed_by_enumeration(take)
    rel = abs(v - e) / max(abs(v), 1e-300)
    return {"n": int(take.size), "capped": capped, "var": v, "enum": e,
            "rel": rel, "ok": bool(rel < ENUM_TOL)}


# ---------------------------------------------------------------------------
# the clean-cure arm, through the same machinery
# ---------------------------------------------------------------------------

def clean_cure_loops(c: K.Core) -> dict:
    """Clean-cure windows shaped like `b8_loops.find_loops`' return.

    §18.3 N1: the zero-calibration arm runs through **the same** summation as
    the signal, so this returns the same three indices and nothing else does
    the summing. §18.3 N2: `t_M` is the **first delinquent month**, because a
    clean cure has no modification onset.

    The population is `b8_0a_gate.find_clean_cures`, unmodified, which screens
    field 42, field 63 and field 108 (O28).
    """
    t0, st, en, k, drops = G.find_clean_cures(c, require_no_defer=True)
    # `t0` is the departure vertex and `en` the return vertex, which is exactly
    # §17's `t_A` and `t_B`. The first delinquent month is `t_A + 1` by
    # construction: `find_clean_cures` anchors `t0` at the last current row
    # before the episode, so the row after it is the first delinquent one.
    return {"t_A": t0, "t_M": t0 + 1, "t_B": en,
            "arm": np.full(t0.size, L.ARM_MOD, dtype=np.int8),
            "loan": c.loan_of_row()[t0] if t0.size else np.zeros(0, np.int32),
            "drops": drops}


# ---------------------------------------------------------------------------
# the matched cells
# ---------------------------------------------------------------------------

def cell_of(arm, missed, cure) -> np.ndarray:
    """§18.4's cell id. **Three path keys and no contract key.**"""
    a = np.asarray(arm, dtype=np.int64)
    i = np.searchsorted(np.asarray(EDGES_MISSED), np.asarray(missed),
                        side="right")
    j = np.searchsorted(np.asarray(EDGES_CURE), np.asarray(cure),
                        side="right")
    return (a * 64 + i * 8 + j).astype(np.int64)


def emm(om: np.ndarray, cell: np.ndarray, min_cell: int = MIN_CELL) -> dict:
    """`M`, §18.4: within-cell `2*Var`, weighted by cell size."""
    om = np.asarray(om, dtype=np.float64)
    if om.size == 0:
        return {"M": float("nan"), "cells": 0, "cells_used": 0,
                "loops_used": 0, "loops_dropped_small": 0}
    order = np.argsort(cell, kind="stable")
    cs, os_ = cell[order], om[order]
    starts = np.flatnonzero(np.concatenate(([True], cs[1:] != cs[:-1])))
    counts = np.diff(np.append(starts, cs.size))
    num = den = 0.0
    used = small = 0
    for s, n in zip(starts.tolist(), counts.tolist()):
        if n < min_cell:
            small += n
            continue
        num += n * zed(os_[s:s + n])
        den += n
        used += 1
    return {"M": (num / den) if den else float("nan"),
            "cells": int(starts.size), "cells_used": used,
            "loops_used": int(den), "loops_dropped_small": small}


# ---------------------------------------------------------------------------
# per archive
# ---------------------------------------------------------------------------

def analyse(name: str, cache_root=None, pos=None, tab=None) -> dict:
    if pos is None or tab is None:
        pos, tab = Z8.curve_table()
    c = K.Core(name, cols=COLS, cache_root=cache_root)
    try:
        disc, _dinfo = W.disc_of_row(c, pos, tab)
        r, ok, rinfo = W.row_residuals(c, disc)

        lp = L.find_loops(c)
        sig = Z8.loop_sums(lp, r, ok)
        cc = clean_cure_loops(c)
        flo = Z8.loop_sums(cc, r, ok)

        a = {"name": name, "n_rows": c.n_rows,
             "loans_refused_c13": rinfo["V"]["loans_dropped_c13"],
             "cc_drops": cc["drops"], "arms": {}}

        # ---- N, the zero-calibration arm -----------------------------------
        fm = flo["measurable"]
        n_om = flo["omega"][fm]
        a["N"] = {"loops": int(fm.size), "measurable": int(fm.sum()),
                  "Z": zed(n_om),
                  "absmed": float(np.median(np.abs(n_om))) if n_om.size
                  else float("nan"),
                  "q": (np.percentile(n_om, [10, 50, 90]).tolist()
                        if n_om.size else [float("nan")] * 3),
                  "enum": check_enumeration(n_om),
                  "enough": bool(n_om.size >= MIN_CELL)}

        # ---- Z and M, per arm and pooled ------------------------------------
        meas = sig["measurable"]
        arm = lp["arm"]
        cell = cell_of(arm, sig["n1"] + 1, sig["n3"])
        for tag, sel in (("mod", arm == L.ARM_MOD),
                         ("defer", arm == L.ARM_DEFER),
                         ("pooled", np.ones_like(meas))):
            m = sel & meas
            om = sig["omega"][m]
            d = {"loops": int(sel.sum()), "measurable": int(m.sum()),
                 "Z": zed(om),
                 "q": (np.percentile(om, [10, 50, 90]).tolist() if om.size
                       else [float("nan")] * 3),
                 "enum": check_enumeration(om),
                 "M": emm(om, cell[m])}
            zz, nn = d["Z"], a["N"]["Z"]
            d["ratio"] = (float(np.sqrt(zz) / np.sqrt(nn))
                          if (np.isfinite(zz) and np.isfinite(nn) and nn > 0)
                          else float("nan"))
            d["ratio_M"] = (float(np.sqrt(zz) / np.sqrt(d["M"]["M"]))
                            if (np.isfinite(zz) and np.isfinite(d["M"]["M"])
                                and d["M"]["M"] > 0) else float("nan"))
            a["arms"][tag] = d
    finally:
        c.close()
    return a


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _f(x, k=4):
    return "nan" if not np.isfinite(x) else f"{x:.{k}e}"


def render(rows: list[dict]) -> str:
    Ls: list[str] = []
    A = Ls.append
    A("# B8-0b: the noise floor for the loop sum\n")
    A("Generated by `experiments/b8_0b_floor.py`. **Pre-registered in "
      "`docs/b8_fannie_slice.md` §18, before this ran.** The map from outcome "
      "to disposition is §18.5 and is not revisited here.\n")
    A("```\nZ := 2 * Var(omega)  over the loops compared\n"
      "N := 2 * Var(omega)  over CLEAN CURES, true value zero by construction\n"
      "M := 2 * Var(omega)  within (arm, missed months, months to cure) cells\n"
      "```\n")
    A("**`N` is the floor, `M` is not** (§18.2). Matched-cell dispersion is a "
      "subset of the signal, so using it as the floor drives the ratio toward "
      "one by an amount that depends on how finely the cells are cut. `M` is "
      "printed because it says how much of `omega` the realised path explains, "
      "which is B8-4's precondition.\n")

    A("\n## 1. The gate: two computations of `Z` must agree\n")
    A("`b3_cip_slice.md` B3-1, verbatim. Enumeration over ordered pairs "
      f"against `2*Var`, relative error below `{ENUM_TOL:.0e}`. Enumeration is "
      f"quadratic so it draws at most {ENUM_CAP:,} loops, **and the cap is "
      "printed**.\n")
    A("| archive | arm | n | capped | `2*Var` | enumeration | rel. error | "
      "**agrees** |")
    A("|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("pooled", "mod", "defer"):
            e = a["arms"][tag]["enum"]
            A(f"| {a['name']} | {tag} | {e['n']:,} | "
              f"{'yes' if e['capped'] else 'no'} | {_f(e['var'])} | "
              f"{_f(e['enum'])} | {_f(e['rel'], 2)} | "
              f"**{'yes' if e['ok'] else 'NO'}** |")
        e = a["N"]["enum"]
        A(f"| {a['name']} | N (clean cures) | {e['n']:,} | "
          f"{'yes' if e['capped'] else 'no'} | {_f(e['var'])} | "
          f"{_f(e['enum'])} | {_f(e['rel'], 2)} | "
          f"**{'yes' if e['ok'] else 'NO'}** |")

    A("\n## 2. `N`, the zero calibration\n")
    A("Clean cures from `b8_0a_gate.find_clean_cures` (O28's population: never "
      "field 42 `Y`, never a positive field 63, never a positive field 108), "
      "summed by **the same** `loop_sums` the signal uses (§18.3 N1). `t_M` is "
      "the first delinquent month (§18.3 N2). **The contract genuinely does "
      "not change on this arm, so the true loop sum is zero and what is left "
      "is construction error, reporting noise and freezes.**\n")
    A("| archive | clean cures | **measurable** | `N` | `sqrt(N)` | "
      "median abs | p10 | p50 | p90 | over MIN_CELL |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        n = a["N"]
        A(f"| {a['name']} | {n['loops']:,} | **{n['measurable']:,}** | "
          f"{_f(n['Z'])} | {_f(np.sqrt(n['Z']))} | {_f(n['absmed'])} | "
          + " | ".join(_f(v) for v in n["q"])
          + f" | {'yes' if n['enough'] else '**NO**'} |")

    A("\n## 3. The headline, `sqrt(Z)/sqrt(N)`\n")
    A("§18.5's map: above 3 is B8-1's **necessary** condition, not B8-1. "
      "Between 1 and 3 is a recorded failure. At or below 1 the signal is "
      "under the floor. **None of those changes the floor, the cells or the "
      "statistic.**\n")
    A("| archive | arm | loops | **measurable** | `Z` | `sqrt(Z)` | "
      "**`sqrt(Z)/sqrt(N)`** | omega p10 | p50 | p90 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        for tag in ("pooled", "mod", "defer"):
            d = a["arms"][tag]
            A(f"| {a['name']} | {tag} | {d['loops']:,} | "
              f"**{d['measurable']:,}** | {_f(d['Z'])} | "
              f"{_f(np.sqrt(d['Z']))} | **{_f(d['ratio'], 3)}** | "
              + " | ".join(_f(v, 3) for v in d["q"]) + " |")

    A("\n## 4. `M`, the matched cells, **not the floor**\n")
    A("Cells are `(arm, missed months, months to cure)` on §3.3's coarse grid. "
      "**No contract quantity is a cell key** (§18.4): `omega` is a function "
      "of the contract, so cutting on it would drive the within-cell variance "
      "to zero and the ratio to infinity, which is C11's criterion B in a "
      "different costume. `M < N` would mean the cells are cut too fine or a "
      "contract quantity leaked in, and §18.5 sends that back to the keys "
      "rather than accepting the number.\n")
    A(f"Cells smaller than {MIN_CELL} are dropped and counted.\n")
    A("| archive | arm | cells | used | loops used | dropped, small cell | "
      "`M` | `sqrt(M)` | `sqrt(Z)/sqrt(M)` | `M` vs `N` |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a in rows:
        nn = a["N"]["Z"]
        for tag in ("pooled", "mod", "defer"):
            d = a["arms"][tag]
            m = d["M"]
            rel = ("n/a" if not (np.isfinite(m["M"]) and np.isfinite(nn)
                                 and nn > 0)
                   else ("**M < N**" if m["M"] < nn else f"{m['M'] / nn:.1f}x"))
            A(f"| {a['name']} | {tag} | {m['cells']:,} | {m['cells_used']:,} | "
              f"{m['loops_used']:,} | {m['loops_dropped_small']:,} | "
              f"{_f(m['M'])} | {_f(np.sqrt(m['M']))} | "
              f"{_f(d['ratio_M'], 3)} | {rel} |")

    A("\n## What this does not decide\n")
    A("- **B8-1 is not read here.** This supplies its floor. B8-1 needs both "
      "`q` grids of §3.3 and §6's windows.")
    A("- **`M` does not enter any ratio that B8-1 uses** (§18.2).")
    A("- The per-class floor `sqrt(Z(a))/sqrt(N(a))` of §15.4 is **not** "
      "computed here; it is gated by C9 and belongs to B8-4a.")
    A("- Loans carrying both zero-interest balances are **refused** (C13), "
      "count in section 2's neighbour and in `b8_loop_omega.md` §1.\n")
    return "\n".join(Ls) + "\n"


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails: list[str] = []

    # -- Z, both ways, against hand arithmetic ----------------------------
    x = np.array([1.0, 2.0, 4.0, 8.0])
    # 2*Var: mean 3.75, var = (7.5625+3.0625+0.0625+18.0625)/4 = 7.1875
    if abs(zed(x) - 14.375) > 1e-12:
        fails.append(f"zed = {zed(x)}, hand computation 14.375")
    if abs(zed_by_enumeration(x) - 14.375) > 1e-12:
        fails.append(f"enumeration = {zed_by_enumeration(x)}, hand 14.375")
    # a constant vector has Z = 0 exactly, both ways
    if zed(np.full(9, 2.5)) != 0.0 or zed_by_enumeration(np.full(9, 2.5)) != 0.0:
        fails.append("Z on a constant vector is not exactly zero")
    ck = check_enumeration(x)
    if not ck["ok"]:
        fails.append(f"check_enumeration says the two disagree: {ck}")
    # **And the gate must be able to fire.** Both quantities are the same
    # number mathematically, so no input can distinguish them: a
    # `check_enumeration` that computed `2*Var` twice would agree perfectly and
    # look like a passing gate forever. So the disagreement is injected. Pit
    # 33's rule: after adding a check, make the thing it should catch happen.
    _real = globals()["zed_by_enumeration"]
    try:
        globals()["zed_by_enumeration"] = lambda v: _real(v) * 1.001
        fired = check_enumeration(x)
    finally:
        globals()["zed_by_enumeration"] = _real
    if fired["ok"]:
        fails.append("the enumeration gate passed a 0.1 per cent "
                     "disagreement; it is comparing a number to itself")

    # -- the cells: no contract key can reach `cell_of` -------------------
    # **A signature check, not a comment.** §18.4's ban is the load-bearing
    # part of `M`, and a ban enforced only by prose is enforced by nobody.
    import inspect
    params = list(inspect.signature(cell_of).parameters)
    if params != ["arm", "missed", "cure"]:
        fails.append(f"cell_of takes {params}; §18.4 allows exactly "
                     "['arm', 'missed', 'cure'] and every one of them is a "
                     "path quantity")
    # cells must separate, or `M` is one big cell
    ar = np.array([0, 0, 0, 1])
    ms = np.array([1, 5, 20, 1])
    cu = np.array([0, 4, 20, 0])
    ids = cell_of(ar, ms, cu)
    if len(set(ids.tolist())) != 4:
        fails.append(f"cell_of collapsed four distinct paths to {set(ids.tolist())}")

    # -- M: weighting, and the small-cell drop ----------------------------
    om = np.concatenate([np.zeros(25), np.ones(25) * 3.0, np.array([9.0] * 5)])
    cl = np.concatenate([np.zeros(25, int), np.ones(25, int),
                         np.full(5, 2, int)])
    m = emm(om, cl)
    if m["cells"] != 3 or m["cells_used"] != 2:
        fails.append(f"emm used {m['cells_used']} of {m['cells']} cells, "
                     "expected 2 of 3")
    if m["loops_dropped_small"] != 5:
        fails.append(f"emm dropped {m['loops_dropped_small']} loops in small "
                     "cells, expected 5")
    if abs(m["M"]) > 1e-12:
        fails.append(f"emm on two constant cells read {m['M']}, expected 0")
    # a cell with spread must move it, or the weighting is inert
    om2 = om.copy()
    om2[:25] = np.linspace(0.0, 1.0, 25)
    m2 = emm(om2, cl)
    if not m2["M"] > 0:
        fails.append("emm did not react to a cell with spread")

    # -- end to end on `b8_loops`' fixture --------------------------------
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    cr = root / "cache"
    K.build_archive(zp, force=True, cache_root=cr)
    with K.Core(zp.stem, cols=COLS, cache_root=cr) as c:
        months = np.unique(c.row["period"][:])
        months = months[months != K.U16_NA]
        pos, tab = Z8._flat_curve(months)
        cc = clean_cure_loops(c)
    a = analyse(zp.stem, cache_root=cr, pos=pos, tab=tab)

    # the clean-cure arm must exist and t_M must be the first delinquent month
    if cc["t_A"].size == 0:
        fails.append("the fixture yields no clean cure, so `N` is an empty "
                     "set and every ratio below is nan")
    if cc["t_A"].size and not bool((cc["t_M"] == cc["t_A"] + 1).all()):
        fails.append("t_M on the clean-cure arm is not the first delinquent "
                     "month; §18.3 N2 is not implemented")
    if a["N"]["measurable"] == 0:
        fails.append("no clean cure is measurable on the fixture, so `N` is "
                     "nan and the gate below proves nothing")
    for tag in ("pooled", "mod", "defer"):
        if not a["arms"][tag]["enum"]["ok"]:
            fails.append(f"the two computations of Z disagree on {tag}: "
                         f"{a['arms'][tag]['enum']}")
    if not a["N"]["enum"]["ok"]:
        fails.append(f"the two computations of Z disagree on N: "
                     f"{a['N']['enum']}")
    print(f"  fixture: N over {a['N']['measurable']} clean cures = "
          f"{a['N']['Z']:.4e}; pooled Z = {a['arms']['pooled']['Z']:.4e}; "
          f"ratio {a['arms']['pooled']['ratio']:.3f}", file=sys.stderr)

    txt = render([a])
    for cmpl in K.check_markdown_tables(txt):
        fails.append(f"malformed table: {cmpl}")
    for need in ("## 1. The gate", "## 2. `N`, the zero calibration",
                 "## 4. `M`, the matched cells"):
        if need not in txt:
            fails.append(f"render omits `{need}`")

    for m_ in fails:
        print("FAIL " + m_, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, Z agrees both ways and the floor arm runs end to end",
          file=sys.stderr)
    return 0


def run(names: list[str]) -> int:
    pos, tab = Z8.curve_table()
    rows = []
    for n in names:
        print(f"reading {n}", file=sys.stderr)
        a = analyse(n, pos=pos, tab=tab)
        rows.append(a)
        print(f"  done {n}: N over {a['N']['measurable']:,} clean cures = "
              f"{a['N']['Z']:.4e}, pooled ratio "
              f"{a['arms']['pooled']['ratio']:.3f}", file=sys.stderr)
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
