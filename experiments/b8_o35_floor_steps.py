#!/usr/bin/env python3
"""O35: contract moves that carry no flag, on B8-0b's floor arm, named one by one.

--------------------------------------------------------------------------
Where this comes from
--------------------------------------------------------------------------

`results/b8_2_curve.md` section 4 recomputed the clean-cure arm under a second
curve construction and printed `max floor shift`. Five archives read 1.8e-12 to
1.5e-11. **2017Q1 read 3.102e-06, which is 115 times that archive's floor of
2.695e-08.** The argument printed above that table says the shift has to be
zero: the annuity factor cancels where field 17 steps down by one month, and a
clean cure re-contracts nothing. So at least one loop on the arm B8-0b draws its
floor from does not cancel. It went into the project's objection cache as O35
on 2026-08-17, with two notes: `MAD` absorbed it where a variance-type floor
would not, and the task is to count how many loops and find which batch.

--------------------------------------------------------------------------
The identity this file reads everything through
--------------------------------------------------------------------------

A clean cure carries no zero-interest balance, so `V(b, i, n, d)` is the level
payment on `b` times the annuity at `d`, and the level payment times the
annuity at the note rate is `b` itself. Hence `V(b, i, n, d) = b * V(1, i, n, d)`
and every month of a loop sum splits exactly:

    r(t) = log( B(t) / B_hat(t) )  +  C(t)
    C(t) = log V(1, i(t), n(t), d(t))  -  log V(1, i(t-1), n(t-1) - 1, d(t))

`i` is field 9, `n` is field 17 and `d` is the curve at the row's own month and
horizon. **`C(t)` is zero whenever the term steps down by one and the note rate
holds**, whatever `d` is, and then the loop sum is the ideal closed form plus the
cent. Two ways for it not to be zero:

- **a term step** (field 17 does not step down by one, rate unchanged). `C`
  depends on `d`, so a change of curve construction moves it. This is what
  section 4 of `b8_2_curve.md` could see.
- **a rate step** (field 9 moves, term steps normally). `C(t)` reduces to
  `log A(i(t-1), n) - log A(i(t), n)` and `d` drops out. **A change of curve
  construction cannot move it**, so the test that found O35 is blind to this
  half by construction.

So the object is every floor loop whose window holds a month in which the term or
the note rate did not do what an unchanged contract does. On such a loop
`omega - closed = sum of C + the cent`, and each term of that is computed here.

--------------------------------------------------------------------------
What it reads and what it does not rebuild
--------------------------------------------------------------------------

The loop cache (`b8_cache`) and the core table, read only. **The cache's stored
tag differs from the current one**, and `b8_cache.load` refuses such an entry.
This file does not retag and does not rebuild. It finds the commit whose sources
produce the stored tag and compares every source module with the working tree on
the syntax tree with docstrings stripped, which is the rule the B8 design set for
cache tags and which `b8_cache.tag` itself does not implement. **Prose-only
differences are read through; any code difference stops the run.**

Usage:

    python experiments/b8_o35_floor_steps.py selftest
    python experiments/b8_o35_floor_steps.py scan --only 2017Q1
    python experiments/b8_o35_floor_steps.py scan
    python experiments/b8_o35_floor_steps.py render
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_omega as W                                           # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_loop_omega as Z8                                     # noqa: E402
import b8_cache as C                                           # noqa: E402
import b8_0a_gate as G                                         # noqa: E402
import b8_0b_floor as F                                        # noqa: E402
import b8_2_curve as P2C                                       # noqa: E402

OUT_MD = K.ROOT / "results" / "b8_o35_floor_steps.md"
OUT_JSON = K.ROOT / "results" / "b8_o35_floor_steps.json"
SCAN_DIR = K.ROOT / "data" / "processed" / "b8_o35"
ARCHIVES = ("2002Q1", "2006Q1", "2007Q1", "2012Q1", "2017Q1", "2019Q1")
CORE_COLS = ["period", "rate", "upb", "rem_legal", "mat_date", "delinq",
             "mod_flag", "loan_age", "nib_upb", "defer_amt"]

#: The two constructions `b8_2_curve` compared. Imported, not retyped.
RULE_A, RULE_B = P2C.RULE_A, P2C.RULE_B

#: Months printed on each side of a named loop's window.
PAD = 1

#: Rows drawn for the identity check, on top of every named loop's rows.
IDENTITY_SAMPLE = 20000
SEED = 20260915

#: **The identity check's tolerance, derived and not chosen.** `b8_2_curve`
#: bounds the rounding of one `r` difference at `4 * |log V| * eps` with
#: `|log V| = 14`, which is two logs a side. The identity here compares
#: `r - log(B/B_hat)` against `C`: six logarithms, so the same derivation
#: gives six.
IDENTITY_TOL = 6.0 * 14.0 * np.finfo(np.float64).eps

#: The archive the curve lookup is checked on, bit for bit, against
#: `b8_omega.disc_of_row` over every row. The smallest, because the
#: production function allocates four full-length arrays.
DISC_CHECK_ARCHIVE = "2019Q1"

#: Rows per chunk wherever a full-length integer copy would otherwise be made.
CHUNK = 5_000_000


# ---------------------------------------------------------------------------
# provenance of the loop cache
# ---------------------------------------------------------------------------

def _strip_docstrings(src: str) -> str:
    """The syntax tree with every docstring removed, dumped without positions.

    Comments are not in the tree at all. A bare string in the middle of a body
    is kept, so a change there counts as code, which errs toward stopping.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def _tag_of(texts: list[str]) -> str:
    """`b8_cache.tag`'s arithmetic on a given list of module texts."""
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
    h.update(repr((Z8.RULE, W.MAX_H, K.SCHEMA_VERSION)).encode("utf-8"))
    return h.hexdigest()[:16]


def _git(args: list[str]) -> bytes:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    r = subprocess.run(["git", "-c", "safe.directory=*"] + args, cwd=K.ROOT,
                       capture_output=True, env=env)
    if r.returncode:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip())
    return r.stdout


def provenance(stored: str, git=_git) -> dict:
    """Is the cache entry the one the current code would build?

    `current` when the stored tag is today's. Otherwise the commit whose module
    texts reproduce the stored tag is found, and each module is compared with
    the working tree twice: as text, and as a docstring-free syntax tree.
    `prose-only` means every difference is in comments or docstrings.
    """
    cur = C.tag()
    out = {"stored": stored, "current": cur}
    if stored == cur:
        out["status"] = "current"
        return out
    paths = [Path(inspect.getsourcefile(m)).resolve() for m in C.SOURCE_MODULES]
    rel = [p.relative_to(K.ROOT).as_posix() for p in paths]
    work = [inspect.getsource(m) for m in C.SOURCE_MODULES]
    if _tag_of(work) != cur:
        out["status"] = "tag-arithmetic-mismatch"
        return out
    try:
        commits = git(["log", "--format=%H", "--"] + rel).decode("utf-8").split()
    except (OSError, RuntimeError) as e:
        out.update(status="unverifiable", reason=str(e)[:200])
        return out
    for h in commits:
        try:
            old = [git(["show", f"{h}:{r}"]).decode("utf-8").replace("\r\n", "\n")
                   for r in rel]
        except RuntimeError:
            continue
        if _tag_of(old) != stored:
            continue
        text = [r for r, a, b in zip(rel, old, work) if a != b]
        tree = [r for r, a, b in zip(rel, old, work)
                if _strip_docstrings(a) != _strip_docstrings(b)]
        out.update(commit=h[:12], text_differs=text, code_differs=tree,
                   status="prose-only" if not tree else "code-changed")
        return out
    out["status"] = "no-commit-matches"
    return out


def load_cache(name: str) -> tuple[dict, dict, dict]:
    """The cached loops, read directly. The caller has checked provenance."""
    with np.load(C._path(name), allow_pickle=False) as z:
        meta = json.loads(bytes(z["meta__json"]).decode("utf-8"))
        sig = {k[5:]: z[k] for k in z.files if k.startswith("sig__")}
        flo = {k[7:]: z[k] for k in z.files if k.startswith("floor__")}
    return sig, flo, meta


# ---------------------------------------------------------------------------
# the pieces of the identity
# ---------------------------------------------------------------------------

def disc_at(pos: dict, tab: np.ndarray, period, rem) -> np.ndarray:
    """`b8_omega.disc_of_row` on a subset of rows. Checked bit for bit against
    the production function in the run, on every row of one archive."""
    period = np.asarray(period).astype(np.int64)
    rem = np.asarray(rem).astype(np.int64)
    mrow = np.full(period.size, -1, dtype=np.int64)
    known = period != K.U16_NA
    if known.any():
        keys = np.unique(period[known])
        lut = np.full(int(keys.max()) + 1, -1, dtype=np.int64)
        for mi in keys.tolist():
            lut[mi] = pos.get(int(mi), -1)
        mrow[known] = lut[period[known]]
    good = (mrow >= 0) & (rem >= 1) & (rem <= W.MAX_H)
    out = np.full(period.size, np.nan)
    gi = np.flatnonzero(good)
    if gi.size:
        out[gi] = tab[mrow[gi], rem[gi]]
    return out


def contract_term(rate_now, rate_prev, n_now, n_prev_raw, d) -> np.ndarray:
    """`C(t)`. Rates as stored (thousandths of a per cent), `n_prev_raw` is
    the previous row's field 17 before the one-month step."""
    i_now = np.asarray(rate_now, dtype=np.float64) / 1000.0
    i_prev = np.asarray(rate_prev, dtype=np.float64) / 1000.0
    n = np.asarray(n_now, dtype=np.float64)
    n1 = np.asarray(n_prev_raw, dtype=np.float64) - 1.0
    one = np.ones(n.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(W.V(one, i_now, n, d)) - np.log(W.V(one, i_prev, n1, d))


def window_index(t_A, t_B) -> tuple[np.ndarray, np.ndarray]:
    """Rows `[t_A + 1, t_B]` of every loop, flattened, with each row's loop."""
    t_A = np.asarray(t_A, dtype=np.int64)
    t_B = np.asarray(t_B, dtype=np.int64)
    ln = t_B - t_A
    if ln.size and ln.min() < 1:
        raise ValueError("a loop window with no months")
    owner = np.repeat(np.arange(t_A.size, dtype=np.int64), ln)
    off = np.arange(int(ln.sum()), dtype=np.int64) - np.repeat(np.cumsum(ln) - ln, ln)
    return np.repeat(t_A + 1, ln) + off, owner


def step_masks(per, rate, rem, mat, mod, nib, dfr, first) -> dict:
    """Per row `t`, what the pair `(t-1, t)` did. Every mask is False on a
    loan's first row and wherever either row lacks the field it tests.

    `flagged` is a flag on either row of the pair: field 42 `Y`, a positive
    field 63 or a positive field 108, which is exactly the population screen
    `b8_0a_gate.find_clean_cures` applies. `at_maturity` marks pairs whose
    earlier row already reads field 17 at one month or less, where a step of
    minus one is no longer possible.
    """
    n = per.size
    elig = np.zeros(n, dtype=bool)
    elig[1:] = ((per[1:].astype(np.int32) - per[:-1].astype(np.int32)) == 1)
    for a in (per, rem, rate):
        known = a != K.U16_NA
        elig[1:] &= known[1:] & known[:-1]
    elig &= ~first
    term = np.zeros(n, dtype=bool)
    term[1:] = (rem[1:].astype(np.int32) - rem[:-1].astype(np.int32)) != -1
    term &= elig
    rstep = np.zeros(n, dtype=bool)
    rstep[1:] = rate[1:] != rate[:-1]
    rstep &= elig
    mknown = mat != K.U16_NA
    mmove = np.zeros(n, dtype=bool)
    mmove[1:] = (mat[1:] != mat[:-1]) & mknown[1:] & mknown[:-1]
    mmove &= elig
    fl = ((mod == ord("Y")) | ((nib != K.U32_NA) & (nib > 0))
          | ((dfr != K.U32_NA) & (dfr > 0)))
    flagged = fl.copy()
    flagged[1:] |= fl[:-1]
    at_mat = np.zeros(n, dtype=bool)
    at_mat[1:] = rem[:-1] <= 1
    return {"eligible": elig, "term": term, "rate": rstep, "mat": mmove,
            "flagged": flagged, "at_maturity": at_mat}


def bal_at(c, idx) -> np.ndarray:
    """`b8_core.zero_interest_split`'s interest-bearing balance on given rows,
    in currency units. The shared function builds five full-length arrays;
    this reads only the rows asked for, and the run checks the two agree bit
    for bit on every row of one archive."""
    idx = np.asarray(idx, dtype=np.int64)
    upb = c.row["upb"][idx].astype(np.int64)
    nib = c.row["nib_upb"][idx].astype(np.int64)
    dfr = c.row["defer_amt"][idx].astype(np.int64)
    z63 = np.where((nib != K.U32_NA) & (nib > 0), nib, 0)
    z108 = np.where((dfr != K.U32_NA) & (dfr > 0), dfr, 0)
    return (upb - z63 - z108).astype(np.float64) / 100.0


def month_label(mi: int) -> str:
    mi = int(mi)
    if mi == K.U16_NA:
        return "blank"
    return f"{K.EPOCH_YEAR + mi // 12}-{mi % 12 + 1:02d}"


def implied_payment(b0: float, b_end: float, note_pct: float, m: int) -> float:
    """The payment that takes `b0` to `b_end` in `m` scheduled months.

    On the ideal path `b_end = f^m(b0)` to within the cent, so this recovers the
    contract payment the closed form used, to a fraction of a cent. It only
    feeds the rounding bound's minimum balance.
    """
    i = note_pct / 1200.0
    g = (1.0 + i) ** m
    return (b0 * g - b_end) * i / (g - 1.0)


def _top(values: np.ndarray, k: int = 8) -> list[list[int]]:
    if values.size == 0:
        return []
    v, c = np.unique(values, return_counts=True)
    o = np.lexsort((v, -c))[:k]
    return [[int(v[j]), int(c[j])] for j in o]


# ---------------------------------------------------------------------------
# the scan, one archive at a time, cached to disk
# ---------------------------------------------------------------------------

#: Functions whose source decides what `scan_archive` writes. The per-archive
#: files carry a hash of their docstring-free syntax trees and `render` refuses
#: a file whose hash is not today's.
_SCAN_FUNCS = ("disc_at", "contract_term", "window_index", "step_masks",
               "implied_payment", "_top", "scan_archive", "_named_loop",
               "bal_at", "provenance", "_strip_docstrings", "_tag_of")


def scan_tag() -> str:
    h = hashlib.sha256()
    for f in _SCAN_FUNCS:
        h.update(_strip_docstrings(inspect.getsource(globals()[f])).encode())
    h.update(repr((RULE_A, RULE_B, PAD, IDENTITY_SAMPLE, SEED)).encode())
    return h.hexdigest()[:16]


def _named_loop(e, fl, arr, ids, cA, cB, rows, owner, res, lo_row, hi_row):
    a, b = int(fl["t_A"][e]), int(fl["t_B"][e])
    k = int(fl["k"][e])
    note = arr["rate"][a] / 1000.0
    lo, hi = max(lo_row, a - PAD), min(hi_row, b + PAD)
    span = np.arange(lo, hi + 1, dtype=np.int64)
    bal = dict(zip(span.tolist(), arr["bal"](span).tolist()))
    m = k + 1
    p_hat = implied_payment(bal[a], bal[b], note, m)
    b_hat = [bal[t - 1] * (1.0 + arr["rate"][t - 1] / 1000.0 / 1200.0) - p_hat
             for t in range(a + 1, b + 1)]
    b_min = float(min(min(bal[t] for t in range(a, b + 1)), min(b_hat)))
    bound = float(G.rounding_bound(b_min, note, k))
    sel = owner == e
    rr = rows[sel]
    steps = []
    for t, ca, cb in zip(rr.tolist(), cA[sel].tolist(), cB[sel].tolist()):
        d17 = int(arr["rem"][t]) - int(arr["rem"][t - 1])
        d9 = int(arr["rate"][t]) - int(arr["rate"][t - 1])
        if d17 != -1 or d9 != 0:
            steps.append({
                "month": month_label(arr["per"][t]),
                "field17": [int(arr["rem"][t - 1]), int(arr["rem"][t])],
                "field19": [month_label(arr["mat"][t - 1]),
                            month_label(arr["mat"][t])],
                "field9": [int(arr["rate"][t - 1]) / 1000.0,
                           int(arr["rate"][t]) / 1000.0],
                "C_A": float(ca), "C_B": float(cb)})
    path = []
    for t in range(lo, hi + 1):
        path.append({
            "row": "A" if t == a else ("B" if t == b else ""),
            "month": month_label(arr["per"][t]),
            "f9": int(arr["rate"][t]) / 1000.0 if arr["rate"][t] != K.U16_NA else None,
            "f12": float(bal[t]),
            "f16": int(arr["age"][t]) if arr["age"][t] != K.U16_NA else None,
            "f17": int(arr["rem"][t]) if arr["rem"][t] != K.U16_NA else None,
            "f19": month_label(arr["mat"][t]),
            "f40": int(arr["dq"][t]),
            "f42": chr(int(arr["mod"][t])) if int(arr["mod"][t]) != K.U8_NA else ""})
    loan = int(fl["loan"][e])
    return {"loop": int(e), "loan_id": ids[loan] if loan < len(ids) else str(loan),
            "t_A": month_label(arr["per"][a]), "t_B": month_label(arr["per"][b]),
            "k": k, "n_win": int(fl["n_win"][e]),
            "omega": float(fl["omega"][e]), "closed": float(fl["closed"][e]),
            "residual": float(res[e]), "C_A": float(cA[sel].sum()),
            "C_B": float(cB[sel].sum()),
            "remainder": float(res[e] - cA[sel].sum()),
            "payment_implied": float(p_hat), "b_min": b_min, "bound": bound,
            "steps": steps, "path": path}


def scan_archive(name: str, posA, tabA, posB, tabB) -> dict:
    sig, fl, meta = load_cache(name)
    prov = provenance(meta.get("tag"))
    if prov["status"] not in ("current", "prose-only"):
        raise SystemExit(f"{name}: the loop cache is not readable as today's "
                         f"code ({prov}). Rebuild it: python "
                         f"experiments/b8_cache.py build --only {name}")
    c = K.Core(name, cols=CORE_COLS)
    try:
        n = c.n_rows
        n_loans = int(c.n_loans)
        first = c.first_row_of_loan_mask()
        per = np.asarray(c.row["period"][:])
        rate = np.asarray(c.row["rate"][:])
        rem = np.asarray(c.row["rem_legal"][:])
        mat = np.asarray(c.row["mat_date"][:])
        mod = np.asarray(c.row["mod_flag"][:])
        nib = np.asarray(c.row["nib_upb"][:])
        dfr = np.asarray(c.row["defer_amt"][:])
        mk = step_masks(per, rate, rem, mat, mod, nib, dfr, first)

        # field 17 against field 19 minus the reporting month, in chunks so no
        # full-length integer copy is ever held
        agree = seen = 0
        for s0 in range(0, n, CHUNK):
            s1 = min(n, s0 + CHUNK)
            r_, m_, p_ = (rem[s0:s1].astype(np.int32), mat[s0:s1].astype(np.int32),
                          per[s0:s1].astype(np.int32))
            kn = (r_ != K.U16_NA) & (m_ != K.U16_NA) & (p_ != K.U16_NA)
            agree += int(((r_ == m_ - p_) & kn).sum())
            seen += int(kn.sum())
        derived = agree / max(seen, 1)

        size = int(per[per != K.U16_NA].max()) + 1
        unf = mk["eligible"] & ~mk["flagged"]
        masks = {
            "eligible_unflagged": unf,
            "term_unflagged": unf & mk["term"] & ~mk["at_maturity"],
            "term_unflagged_at_maturity": unf & mk["term"] & mk["at_maturity"],
            "rate_unflagged": unf & mk["rate"],
            "mat_unflagged": unf & mk["mat"],
            "term_flagged": mk["eligible"] & mk["flagged"] & mk["term"],
            "rate_flagged": mk["eligible"] & mk["flagged"] & mk["rate"]}
        periods = {}
        totals = {}
        for key, m in masks.items():
            cnt = np.bincount(per[m].astype(np.int64), minlength=size)[:size]
            totals[key] = int(cnt.sum())
            for mi in np.flatnonzero(cnt).tolist():
                periods.setdefault(month_label(mi), {})[key] = int(cnt[mi])
        it = np.flatnonzero(masks["term_unflagged"])
        ir = np.flatnonzero(masks["rate_unflagged"])

        def dlt(a, idx):
            return a[idx].astype(np.int64) - a[idx - 1].astype(np.int64)

        deltas = {"term_unflagged_d17": _top(dlt(rem, it)),
                  "term_unflagged_d19": _top(dlt(mat, it)),
                  "rate_unflagged_d9": _top(dlt(rate, ir))}

        # ---- the floor arm ----------------------------------------------------
        nl = int(np.asarray(fl["t_A"]).size)
        rows, owner = window_index(fl["t_A"], fl["t_B"])
        term_r = mk["term"][rows]
        rate_r = mk["rate"][rows]
        mat_r = mk["mat"][rows]
        dA = disc_at(posA, tabA, per[rows], rem[rows])
        dB = disc_at(posB, tabB, per[rows], rem[rows])
        cA = contract_term(rate[rows], rate[rows - 1], rem[rows], rem[rows - 1], dA)
        cB = contract_term(rate[rows], rate[rows - 1], rem[rows], rem[rows - 1], dB)

        def per_loop(x):
            return np.bincount(owner, weights=np.asarray(x, dtype=np.float64),
                               minlength=nl)

        n_term = per_loop(term_r).astype(np.int64)
        n_rate = per_loop(rate_r).astype(np.int64)
        n_mat = per_loop(mat_r).astype(np.int64)
        finA = per_loop(~np.isfinite(cA)) == 0
        finB = per_loop(~np.isfinite(cB)) == 0
        CA = per_loop(np.where(np.isfinite(cA), cA, 0.0))
        CB = per_loop(np.where(np.isfinite(cB), cB, 0.0))

        meas = np.asarray(fl["measurable"]).astype(bool)
        ideal = np.asarray(fl["ideal"]).astype(bool)
        P = meas & ideal
        stepped = (n_term > 0) | (n_rate > 0)
        Fset = P & stepped
        res = np.asarray(fl["omega"], dtype=np.float64) - np.asarray(fl["closed"], dtype=np.float64)

        def pops(x):
            return {"all": int(x.sum()), "measurable": int((x & meas).sum()),
                    "ideal": int((x & ideal).sum()), "P": int((x & P).sum())}

        floor = {"loops": nl, "measurable": int(meas.sum()),
                 "ideal": int(ideal.sum()), "P": int(P.sum()),
                 "with_term_step": pops(n_term > 0),
                 "with_rate_step": pops(n_rate > 0),
                 "with_field19_move": pops(n_mat > 0),
                 "named": int(Fset.sum()),
                 "C_A_nonfinite_in_P": int((P & ~finA).sum()),
                 "C_B_nonfinite_in_P": int((P & ~finB).sum())}

        # the shift, on the same population `b8_2_curve` read
        sp = P & finB
        sh = np.abs(CB - CA)
        floor["shift_max_over_P"] = float(sh[sp].max()) if sp.any() else float("nan")
        floor["shift_max_unnamed"] = (float(sh[sp & ~stepped].max())
                                      if (sp & ~stepped).any() else float("nan"))
        floor["C_A_max_unnamed"] = (float(np.abs(CA[P & ~stepped]).max())
                                    if (P & ~stepped).any() else float("nan"))

        # ---- the identity, on real rows ----------------------------------------
        def bal_of(idx):
            return bal_at(c, idx)

        rng = np.random.default_rng(SEED)
        in_P = P[owner]
        cand = np.flatnonzero(in_P)
        pick = (rng.choice(cand, size=min(IDENTITY_SAMPLE, cand.size), replace=False)
                if cand.size else cand)
        pick = np.union1d(pick, np.flatnonzero(Fset[owner]))
        t = rows[pick]
        b_now = bal_of(t)
        b_prev = bal_of(t - 1)
        i_now = rate[t].astype(np.float64) / 1000.0
        i_prev = rate[t - 1].astype(np.float64) / 1000.0
        n_now = rem[t].astype(np.float64)
        n_prv = rem[t - 1].astype(np.float64)
        pay = K.level_payment(b_prev, i_prev, n_prv)
        bhat = b_prev * (1.0 + i_prev / 1200.0) - pay
        # the rows `b8_omega.row_residuals` admits: a horizon of at least one month
        # now and of more than one month on the previous row, and a positive
        # counterfactual balance
        okr = (np.isfinite(pay) & (bhat > 0) & (b_now > 0) & np.isfinite(dA[pick])
               & (n_now >= 1) & (n_now != K.U16_NA) & (n_prv > 1) & (n_prv != K.U16_NA))
        with np.errstate(divide="ignore", invalid="ignore"):
            lhs = W.r_month(b_now[okr], b_prev[okr], i_now[okr], pay[okr],
                            n_now[okr], dA[pick][okr], note_prev=i_prev[okr],
                            n_prev=n_prv[okr] - 1.0) \
                - (np.log(b_now[okr]) - np.log(bhat[okr]))
        gap = np.abs(lhs - cA[pick][okr])
        identity = {"rows": int(okr.sum()), "named_rows": int(Fset[owner].sum()),
                    "max_gap": float(gap.max()) if gap.size else float("nan"),
                    "tol": IDENTITY_TOL}

        disc_check = None
        if name == DISC_CHECK_ARCHIVE:
            full = W.disc_of_row(c, posA, tabA)[0]
            mine = disc_at(posA, tabA, per, rem)
            disc_check = {"rows": int(n), "equal": bool(np.array_equal(full, mine, equal_nan=True))}
            del full, mine
            zfull = K.zero_interest_split(c)[0].astype(np.float64) / 100.0
            zmine = bal_at(c, np.arange(n, dtype=np.int64))
            disc_check["balance_equal"] = bool(np.array_equal(zfull, zmine))
            del zfull, zmine

        # ---- the named loops ---------------------------------------------------
        arr = {"per": per, "rate": rate, "rem": rem, "mat": mat, "mod": mod,
               "dq": np.asarray(c.row["delinq"][:]),
               "age": np.asarray(c.row["loan_age"][:]),
               "bal": bal_of}
        ids_path = c.root / "loan_ids.txt"
        ids = ids_path.read_text(encoding="utf-8").split("\n") if ids_path.exists() else []
        starts = c.row_start.astype(np.int64)
        ends = starts + c.n_per_loan.astype(np.int64) - 1
        named = []
        for e in np.flatnonzero(Fset).tolist():
            lo = int(fl["loan"][e])
            named.append(_named_loop(e, fl, arr, ids, cA, cB, rows, owner, res,
                                     int(starts[lo]), int(ends[lo])))

        # ---- what the floor feeds: published arithmetic, then screened ------------
        def floor_stats(x, conv=True):
            x = np.asarray(x, dtype=np.float64)
            d = {"n": int(x.size), "mad": F.mad_scale(x), "zed": F.zed(x)}
            if conv:
                d["conv"] = F.scale_convergence(x)
            return d

        corrected = res.copy()
        corrected[Fset] = res[Fset] - CA[Fset]
        N = {"published_population": floor_stats(res[P]),
             "screened": floor_stats(res[P & ~Fset]),
             "corrected": floor_stats(corrected[P], conv=False)}

        arm = np.asarray(sig["arm"])
        smeas = np.asarray(sig["measurable"]).astype(bool)
        som = np.asarray(sig["omega"], dtype=np.float64)
        arms = {}
        for tag, sel in (("mod", arm == L.ARM_MOD), ("defer", arm == L.ARM_DEFER),
                         ("pooled", np.ones(arm.size, dtype=bool))):
            m = sel & smeas
            arms[tag] = {"loops": int(sel.sum()), "measurable": int(m.sum()),
                         "Z": F.zed(som[m]), "mad": F.mad_scale(som[m])}
            if tag == "mod":
                arms[tag]["conv"] = F.scale_convergence(som[m])

        # ---- the signal arm, descriptive -------------------------------------------
        srows, sown = window_index(sig["t_A"], sig["t_B"])
        tM = np.asarray(sig["t_M"], dtype=np.int64)
        off_onset = srows != tM[sown]
        ns = int(np.asarray(sig["t_A"]).size)
        s_step = np.bincount(sown, weights=((mk["term"][srows] | mk["rate"][srows])
                                            & off_onset).astype(np.float64),
                             minlength=ns) > 0
        signal = {tag: {"measurable": int((sel & smeas).sum()),
                        "with_step_off_onset": int((sel & smeas & s_step).sum())}
                  for tag, sel in (("mod", arm == L.ARM_MOD),
                                   ("defer", arm == L.ARM_DEFER))}
    finally:
        c.close()

    return {"name": name, "scan_tag": scan_tag(), "cache_tag": meta.get("tag"),
            "provenance": prov, "rows": int(n), "loans": n_loans,
            "prefix_scale": float(meta.get("prefix_scale", float("nan"))),
            "field17_is_field19_minus_period": derived,
            "totals": totals, "periods": periods, "deltas": deltas,
            "floor": floor, "identity": identity, "disc_check": disc_check,
            "named": named, "N": N, "arms": arms, "signal": signal}


def _scan_path(name: str) -> Path:
    return SCAN_DIR / f"{name}.json"


def _dump(obj, cut_floats: bool = True) -> str:
    """JSON with floats cut to seven significant figures, so the last BLAS
    digit never reaches a checked-in file. **The per-archive scan files keep
    full precision** (`cut_floats=False`): they live under `data/`, never enter
    the repository, and the published figures they are compared against run to
    eight significant figures, so a cut there manufactures mismatches."""
    def cut(x):
        if isinstance(x, float):
            if not np.isfinite(x):
                return None
            return float(f"{x:.7g}") if cut_floats else x
        if isinstance(x, dict):
            return {k: cut(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [cut(v) for v in x]
        return x
    return json.dumps(cut(obj), ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def cmd_scan(names: list[str]) -> int:
    posA, tabA = Z8.curve_table(RULE_A)
    posB, tabB = Z8.curve_table(RULE_B)
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    for name in names:
        print(f"scanning {name}", file=sys.stderr)
        d = scan_archive(name, posA, tabA, posB, tabB)
        _scan_path(name).write_text(_dump(d, cut_floats=False), encoding="utf-8",
                                    newline="\n")
        fl = d["floor"]
        print(f"  {name}: provenance {d['provenance']['status']}, floor P "
              f"{fl['P']:,}, named {fl['named']}, shift max "
              f"{fl['shift_max_over_P']:.4g}, identity gap "
              f"{d['identity']['max_gap']:.3g} on {d['identity']['rows']:,} rows",
              file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# reading the published products this file compares against
# ---------------------------------------------------------------------------

PRODUCTS = {
    "floor": K.ROOT / "results" / "b8_0b_floor.md",
    "curve": K.ROOT / "results" / "b8_2_curve.md",
    "paths": K.ROOT / "results" / "b8_3_paths.md",
    "verdicts": K.ROOT / "results" / "b8_verdicts.json",
}


def published_table(text: str, header_prefix: str) -> list[list[str]]:
    """Data rows of the first markdown table whose header starts with the
    prefix, as lists of cells with emphasis and code marks removed."""
    lines = text.splitlines()
    for j, line in enumerate(lines):
        if line.startswith(header_prefix):
            rows = []
            for row in lines[j + 2:]:
                if not row.startswith("|"):
                    break
                rows.append([cell.strip().strip("*").strip("`").strip()
                             for cell in row.strip().strip("|").split("|")])
            return rows
    raise SystemExit(f"no table whose header starts {header_prefix!r}")


_SCI = re.compile(r"^[+-]?\d\.(\d+)e[+-]\d+$")
_FIX = re.compile(r"^[+-]?[\d,]+\.(\d+)$")
_INT = re.compile(r"^[+-]?[\d,]+$")


def at_printed(x: float, s: str) -> bool | None:
    """Does `x`, formatted the way `s` is printed, read `s`? `None` when `s`
    is not a number. **The comparison is at the printed precision and nothing
    else**: no tolerance is introduced."""
    s = s.strip()
    plus = s.startswith("+")
    m = _SCI.match(s)
    if m:
        k = len(m.group(1))
        return (f"{x:+.{k}e}" if plus else f"{x:.{k}e}") == s
    m = _FIX.match(s)
    if m:
        k = len(m.group(1))
        return (f"{x:+,.{k}f}" if plus else f"{x:,.{k}f}") == s
    if _INT.match(s):
        return f"{int(round(x)):,}" == s.lstrip("+")
    return None


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _e(x, k=4):
    return "nan" if x is None or not np.isfinite(x) else f"{x:.{k}e}"


def _load_scans() -> list[dict]:
    rows, missing, stale = [], [], []
    cur = scan_tag()
    for n in ARCHIVES:
        p = _scan_path(n)
        if not p.exists():
            missing.append(n)
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("scan_tag") != cur:
            stale.append(n)
            continue
        rows.append(d)
    if missing or stale:
        raise SystemExit(f"scan files missing {missing} or stale {stale}. Run: "
                         "python experiments/b8_o35_floor_steps.py scan")
    return rows


def evaluate(rows: list[dict], texts: dict) -> dict:
    """Every comparison and every criterion. Returns what render prints."""
    by = {d["name"]: d for d in rows}
    out = {"repro": [], "repro_sub": [0, 0], "shift": [], "remainder": [],
           "digits": [], "criteria": []}

    def rep(where, arch, what, mine, printed):
        ok = at_printed(mine, printed)
        out["repro"].append({"where": where, "archive": arch, "what": what,
                             "mine": mine, "printed": printed, "ok": ok})

    # -- b8_0b_floor.md -------------------------------------------------------
    for r in published_table(texts["floor"], "| archive | legacy `MAD` |"):
        d = by.get(r[0])
        if d:
            rep("b8_0b_floor 2.4", r[0], "N's MAD", d["N"]["published_population"]["mad"], r[5])
    for r in published_table(texts["floor"], "| archive | arm | n | `2*Var` p10 |"):
        d = by.get(r[0])
        if not d:
            continue
        conv = (d["N"]["published_population"]["conv"] if r[1].startswith("N")
                else d["arms"]["mod"]["conv"] if r[1] == "mod" else None)
        if conv is None:
            continue
        n = int(r[2].replace(",", ""))
        hit = [c for c in conv if c["n"] == n]
        if not hit:
            continue
        c = hit[0]
        full = n == conv[-1]["n"]
        pairs = [(c["var_lo"], r[3]), (c["var_med"], r[4]), (c["var_hi"], r[5]),
                 (c["mad_lo"], r[7]), (c["mad_med"], r[8]), (c["mad_hi"], r[9])]
        if full:
            rep("b8_0b_floor 2.3", r[0], f"{r[1]} full population 2*Var", c["var_med"], r[4])
            rep("b8_0b_floor 2.3", r[0], f"{r[1]} full population MAD", c["mad_med"], r[8])
        else:
            for mine, printed in pairs:
                out["repro_sub"][0] += 1
                out["repro_sub"][1] += bool(at_printed(mine, printed))
    for r in published_table(texts["floor"], "| archive | arm | loops | **measurable** |"):
        d = by.get(r[0])
        if not d or r[1] not in d["arms"]:
            continue
        a = d["arms"][r[1]]
        rep("b8_0b_floor 3", r[0], f"{r[1]} loops", a["loops"], r[2])
        rep("b8_0b_floor 3", r[0], f"{r[1]} measurable", a["measurable"], r[3])
        rep("b8_0b_floor 3", r[0], f"{r[1]} Z", a["Z"], r[4])
        nz = d["N"]["published_population"]["zed"]
        rep("b8_0b_floor 3", r[0], f"{r[1]} sqrt(Z)/sqrt(N)",
            float(np.sqrt(a["Z"]) / np.sqrt(nz)), r[6])
    # -- b8_2_curve.md --------------------------------------------------------
    shift_printed = {}
    for r in published_table(texts["curve"], "| archive | MAD signal A |"):
        d = by.get(r[0])
        if not d:
            continue
        nm = d["N"]["published_population"]["mad"]
        rep("b8_2_curve 4", r[0], "MAD signal A", d["arms"]["mod"]["mad"], r[1])
        rep("b8_2_curve 4", r[0], "MAD floor A", nm, r[3])
        rep("b8_2_curve 4", r[0], "ratio A", d["arms"]["mod"]["mad"] / nm, r[6])
        shift_printed[r[0]] = r[5]
    # -- b8_3_paths.md --------------------------------------------------------
    paths_rows = {r[0]: r for r in published_table(
        texts["paths"], "| archive | arm | loops | measurable | rate |") if r[1] == "mod"}
    for a, r in paths_rows.items():
        d = by.get(a)
        if d:
            rep("b8_3_paths 1", a, "floor", d["N"]["published_population"]["mad"], r[9])

    repro_ok = all(x["ok"] for x in out["repro"])
    bad = [f"{x['where']} {x['archive']} {x['what']}: {x['mine']!r} against {x['printed']}"
           for x in out["repro"] if not x["ok"]]

    # -- the shift ------------------------------------------------------------
    eps = float(np.finfo(np.float64).eps)
    shift_ok = True
    for d in rows:
        fl = d["floor"]
        printed = shift_printed.get(d["name"], "")
        term_named = fl["with_term_step"]["P"]
        mine = fl["shift_max_over_P"]
        if term_named:
            ok = bool(at_printed(mine, printed))
            how = "reproduces the printed figure"
        else:
            bound = Z8.REPLAY_SLACK * eps * d["prefix_scale"]
            ok = (mine <= IDENTITY_TOL) and (float(printed) <= bound)
            how = (f"no term step in the population: analytic {_e(mine, 2)} at "
                   f"rounding, printed {printed} under the prefix-sum bound {_e(bound, 2)}")
        shift_ok &= ok
        out["shift"].append({"archive": d["name"], "term_named": term_named,
                             "mine": mine, "printed": printed, "ok": ok, "how": how})

    # -- the remainder --------------------------------------------------------
    rem_ok = True
    for d in rows:
        for e in d["named"]:
            ok = abs(e["remainder"]) <= e["bound"]
            rem_ok &= ok
            out["remainder"].append((d["name"], e, ok))

    # -- identity and lookup --------------------------------------------------
    id_ok = all(d["identity"]["rows"] > 0 and d["identity"]["max_gap"] <= IDENTITY_TOL
                for d in rows)
    dc = [d["disc_check"] for d in rows if d.get("disc_check")]
    look_ok = bool(dc) and all(x["equal"] and x.get("balance_equal") for x in dc)
    prov = {d["name"]: d["provenance"] for d in rows}
    prov_ok = all(p["status"] in ("current", "prose-only") for p in prov.values())

    # -- what moves on the screened floor ---------------------------------------
    verdicts = json.loads(texts["verdicts"])
    det = {c["name"]: c["detail"] for c in verdicts["criteria"]}
    scr = {d["name"]: d["N"]["screened"] for d in rows}
    pub = {d["name"]: d["N"]["published_population"] for d in rows}

    def quoted_range(detail, pattern):
        m = re.search(pattern, detail)
        return (m.group(1), m.group(2)) if m else (None, None)

    digits = []
    lo_s, hi_s = quoted_range(det.get("B8-0b", ""), r"(\d\.\d+e-\d+) to (\d\.\d+e-\d+)")
    vals = [scr[a]["mad"] for a in ARCHIVES]
    digits.append({"verdict": "B8-0b", "what": "floor range",
                   "quoted": f"{lo_s} to {hi_s}",
                   "screened": f"{min(vals):.2e} to {max(vals):.2e}",
                   "digits_hold": (lo_s is not None and at_printed(min(vals), lo_s)
                                   and at_printed(max(vals), hi_s)),
                   "condition": "none beyond the figures", "condition_holds": True})
    lo_r, hi_r = quoted_range(det.get("B8-1", ""), r"Ratio ([\d,]+) to ([\d,]+)")
    rat = [by[a]["arms"]["mod"]["mad"] / scr[a]["mad"] for a in ARCHIVES]
    heads = [float(np.sqrt(by[a]["arms"][arm]["Z"]) / np.sqrt(scr[a]["zed"]))
             for a in ARCHIVES for arm in ("pooled", "mod", "defer")]
    digits.append({"verdict": "B8-1", "what": "MAD ratio range, modification arm",
                   "quoted": f"{lo_r} to {hi_r}",
                   "screened": f"{min(rat):,.0f} to {max(rat):,.0f}",
                   "digits_hold": (lo_r is not None and at_printed(min(rat), lo_r)
                                   and at_printed(max(rat), hi_r)),
                   "condition": "sqrt(Z)/sqrt(N) above 3 on every arm and archive (map of section 18.5)",
                   "condition_holds": min(heads) > 3.0})
    moved3 = []
    for a, r in paths_rows.items():
        dl = float(r[10])
        mine = abs(dl) / scr[a]["mad"]
        if not at_printed(mine, r[11]):
            moved3.append(f"{a}: {r[11]} reads {mine:.3e}")
    digits.append({"verdict": "B8-3", "what": "delta / floor per archive (b8_3_paths section 1)",
                   "quoted": "six cells", "screened": "; ".join(moved3) or "all six unchanged",
                   "digits_hold": not moved3,
                   "condition": "the verdict rests on per-cell signs and permutation, which the floor does not enter",
                   "condition_holds": True})
    out["digits"] = digits
    verdict_ok = all(x["condition_holds"] for x in digits)

    named_total = sum(d["floor"]["named"] for d in rows)
    printed_total = sum(len(d["named"]) for d in rows)
    books_ok = (len(rows) == len(ARCHIVES) and named_total == printed_total
                and all(e["path"] and e["steps"] for d in rows for e in d["named"])
                and all(d["periods"] for d in rows))

    def crit(name, passed, kind, detail):
        out["criteria"].append({"name": name, "passed": bool(passed), "kind": kind,
                                "detail": detail})

    crit("B8-O35-1", prov_ok, "instrument",
         "the loop cache is read as the current code would build it: "
         + "; ".join(f"{a} {p['status']}" + (f" (commit {p.get('commit')}, text differs in "
                                            f"{', '.join(p.get('text_differs', [])) or 'nothing'})"
                                            if p["status"] == "prose-only" else "")
                     for a, p in prov.items()))
    crit("B8-O35-2", id_ok and look_ok, "instrument",
         "r(t) - log(B/B_hat) equals the contract term on real rows to "
         f"{IDENTITY_TOL:.2e} (largest gap "
         f"{max(d['identity']['max_gap'] for d in rows):.2e} over "
         f"{sum(d['identity']['rows'] for d in rows):,} rows), and the row-subset "
         "curve lookup and balance agree bit for bit with the production functions "
         f"on every row of {DISC_CHECK_ARCHIVE}: "
         + ("yes" if look_ok else "NO"))
    crit("B8-O35-3", repro_ok, "known_answer",
         f"the cache reproduces {sum(1 for x in out['repro'] if x['ok'])} of "
         f"{len(out['repro'])} published figures at their printed precision"
         + (": " + "; ".join(bad[:6]) if bad else "")
         + f". Subsample cells, not part of this criterion: {out['repro_sub'][1]} of "
         f"{out['repro_sub'][0]}")
    crit("B8-O35-4", shift_ok, "known_answer",
         "the published max floor shift is read back from the named loops: "
         + "; ".join(f"{s['archive']} {s['how'] if not s['term_named'] else s['printed'] + ' reproduced as ' + _e(s['mine'], 3)}"
                     if s["ok"] else f"{s['archive']} NOT: mine {_e(s['mine'], 3)}, printed {s['printed']}"
                     for s in out["shift"]))
    crit("B8-O35-5", rem_ok, "known_answer",
         f"every one of the {named_total} named loops is back inside B8-0a's own rounding "
         "bound once its contract term is removed: "
         + "; ".join(f"{a} loan {e['loan_id']} {abs(e['remainder']):.2e} against {e['bound']:.2e}"
                     for a, e, ok in out["remainder"]))
    crit("B8-O35-6", books_ok, "bookkeeping",
         f"{printed_total} named loops printed with their window paths and steps, against "
         f"{named_total} counted; step tables by reporting month for all "
         f"{len(rows)} archives")
    crit("B8-O35-7", verdict_ok, "own_reading",
         "no B8 verdict moves on the floor screened of the named loops: "
         + "; ".join(f"{x['verdict']} {x['what']}: quoted {x['quoted']}, screened "
                     f"{x['screened']}, digits {'unchanged' if x['digits_hold'] else 'move'}, "
                     f"condition {'holds' if x['condition_holds'] else 'FAILS'}"
                     for x in digits))
    return out


def _reading(rows: list[dict]) -> str:
    """The paragraph that says what the tables below add up to. Every figure in
    it is computed from the scans, none is typed."""
    named = [(d["name"], e) for d in rows for e in d["named"]]
    n_rate = sum(1 for _, e in named
                 if any(s["field9"][0] != s["field9"][1] for s in e["steps"]))
    n_term = sum(1 for _, e in named
                 if any(s["field17"][1] - s["field17"][0] != -1 for s in e["steps"]))
    pop = sum(d["floor"]["P"] for d in rows)
    c_other = max(d["floor"]["C_A_max_unnamed"] for d in rows)
    term_loop = [(a, e) for a, e in named
                 if any(s["field17"][1] - s["field17"][0] != -1 for s in e["steps"])]
    shift = {d["name"]: d["floor"]["shift_max_over_P"] for d in rows}
    heads_pub, heads_scr, moved = [], [], []
    for d in rows:
        pz, sz = d["N"]["published_population"]["zed"], d["N"]["screened"]["zed"]
        for arm in ("pooled", "mod", "defer"):
            Z = d["arms"][arm]["Z"]
            heads_pub.append(np.sqrt(Z) / np.sqrt(pz))
            heads_scr.append(np.sqrt(Z) / np.sqrt(sz))
        if d["floor"]["named"]:
            moved.append(f"{d['name']} from {np.sqrt(d['arms']['pooled']['Z']) / np.sqrt(pz):.2e} "
                         f"to {np.sqrt(d['arms']['pooled']['Z']) / np.sqrt(sz):.2e} pooled")
    spreads = []
    for d in rows:
        conv = d["N"]["screened"]["conv"]
        inner = [c for c in conv if c["n"] < conv[-1]["n"]]
        if inner and inner[-1]["var_lo"] > 0:
            spreads.append((inner[-1]["var_hi"] / inner[-1]["var_lo"], d["name"], inner[-1]["n"]))
    worst = max(spreads) if spreads else (float("nan"), "", 0)
    tops = {}
    for d in rows:
        ranked = sorted(((v.get("term_unflagged", 0), m) for m, v in d["periods"].items()
                         if v.get("term_unflagged", 0)), key=lambda z: (-z[0], z[1]))
        if ranked:
            tops[d["name"]] = ranked[0][1]
    common = max(set(tops.values()), key=lambda m: list(tops.values()).count(m)) if tops else ""
    k_common = list(tops.values()).count(common)
    mad_moves = [f"{d['name']}: {d['N']['published_population']['mad']:.4e} to "
                 f"{d['N']['screened']['mad']:.4e}" for d in rows
                 if not at_printed(d["N"]["screened"]["mad"],
                                   f"{d['N']['published_population']['mad']:.4e}")]
    # the verdict quotes the range, so the range is what is compared
    pub_m = [d["N"]["published_population"]["mad"] for d in rows]
    scr_m = [d["N"]["screened"]["mad"] for d in rows]
    mad_quoted = (f"{min(pub_m):.2e}" == f"{min(scr_m):.2e}"
                  and f"{max(pub_m):.2e}" == f"{max(scr_m):.2e}")
    s = (f"\n**The reading.** Of {pop:,} loops in B8-0b's population over {len(rows)} archives, "
         f"**{len(named)} hold a step**: {n_rate} a change of note rate and {n_term} a change of "
         "term, and none carries a flag in field 42, 63 or 108. Removing each one's contract "
         "term leaves it inside B8-0a's own rounding bound, and the contract term on every "
         + ("other loop in the population is exactly zero. " if c_other == 0.0 else
            f"other loop in the population is at most {c_other:.1e}. "))
    if term_loop:
        a, e = term_loop[0]
        s += (f"**O35's figure is the term-step loop** ({a}, loan {e['loan_id']}), read back as "
              f"{shift[a]:.3e}. ")
    s += ("The floor's `MAD` "
          + (f"moves in its fifth significant figure only ({'; '.join(mad_moves)})"
             if mad_moves else "does not move at its printed precision on any archive")
          + (", and the range B8-0b's verdict quotes at three figures reads the same. "
             if mad_quoted else ", and the range B8-0b's verdict quotes moves. ")
          + "**The variance-type readings move by orders of magnitude**: with the named "
          f"loops out, `sqrt(Z)/sqrt(N)` reads "
          f"{min(heads_scr):.1e} to {max(heads_scr):.1e} on every arm of every archive "
          f"({'; '.join(moved)}), and `2*Var` on the floor settles with the sample size, the "
          f"widest spread at the largest proper subsample being {worst[0]:.1f}x ({worst[1]}, "
          f"n = {worst[2]:,}). Across whole archives, the term steps with no flag are "
          f"concentrated in **{common}** on {k_common} of {len(rows)} archives.\n")
    return s


#: What each kind of criterion asks, in the words the table below uses.
KIND_ASKS = {
    "instrument": "whether the instrument reads what it claims to",
    "known_answer": "whether the named objects account for the published figures",
    "bookkeeping": "whether what has to be printed is printed",
    "premise": "whether a fact this run relies on holds",
    "rival": "whether a rival's point prediction holds",
}


def _series(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def kinds_line(criteria: list[dict]) -> str:
    """The sentence above the criteria table, built from the criteria themselves.

    It names criteria and kinds and carries no count: a count typed into this
    line is the one thing on the page that would not follow a criterion added to
    the script.
    """
    kinds: list[str] = []
    for c in criteria:
        if c["kind"] not in kinds:
            kinds.append(c["kind"])
    own = [f"`{c['name']}`" for c in criteria if c["kind"] == "own_reading"]
    rest = [f"{KIND_ASKS[k]} (`{k}`)" for k in kinds if k != "own_reading"]
    parts = []
    if own:
        parts.append(f"**{_series(own)} {'asks' if len(own) == 1 else 'ask'} about a "
                     f"reading of B8 itself** (`own_reading`)")
    if rest:
        parts.append(("the others ask " if own else "the criteria ask ") + _series(rest))
    line = "; ".join(parts) + "."
    if "rival" not in kinds:
        line += " None is a `rival` criterion."
    return line[0].upper() + line[1:] if not line.startswith("**") else line


def render(rows: list[dict], ev: dict) -> str:
    Ls: list[str] = []
    A = Ls.append
    by = {d["name"]: d for d in rows}
    A("# O35: contract moves with no flag on B8-0b's floor arm\n")
    A("Generated by `experiments/b8_o35_floor_steps.py`. Disposition of O35 in the "
      "project's objection cache. The criteria are written in the script that "
      "produces this record, the record carries their text, and every quantity this "
      "run produces is reported.\n")
    A("**What O35 was.** `b8_2_curve.md` section 4 recomputed the clean-cure arm under "
      f"the far-corner curve construction. Five archives moved by 1.8e-12 to 1.5e-11. "
      "**2017Q1 moved by 3.102e-06, 115 times its floor**, on an arm where the "
      "argument printed above that table says the annuity factor cancels whatever the "
      "curve is.\n")
    A("**The identity.** With no zero-interest balance `V(b, i, n, d) = b * V(1, i, n, d)`, "
      "so each month of a loop sum splits exactly into the ideal part and a contract term:\n")
    A("```\nr(t) = log( B(t) / B_hat(t) )  +  C(t)\n"
      "C(t) = log V(1, i(t), n(t), d(t))  -  log V(1, i(t-1), n(t-1) - 1, d(t))\n```\n")
    A("`i` is field 9, `n` field 17, `d` the curve at the row's month and horizon. "
      "**`C(t)` is zero when the term steps down by one month and the note rate holds.** "
      "A term step makes it depend on `d`, which is what a change of curve can see. "
      "**A rate step leaves `d` out of it entirely**, so the test that found O35 cannot "
      "see that half, and this file looks for both.\n")
    A(_reading(rows))

    A("\n## 1. The cache, and whether it is the one today's code would build\n")
    A("The stored tag is not today's, so `b8_cache.load` refuses it. It is read here "
      "only if the commit whose sources reproduce the stored tag differs from the "
      "working tree in comments and docstrings alone, compared on the syntax tree.\n")
    A("| archive | stored tag | current tag | status | commit | text differs in | code differs in |")
    A("|---|---|---|---|---|---|---|")
    for d in rows:
        p = d["provenance"]
        A(f"| {d['name']} | `{p['stored']}` | `{p['current']}` | **{p['status']}** | "
          f"{p.get('commit', '')} | {', '.join(p.get('text_differs', [])) or '-'} | "
          f"{', '.join(p.get('code_differs', [])) or '-'} |")

    A("\n## 2. The identity on real rows, and the two lookups\n")
    A(f"Every named loop's rows plus up to {IDENTITY_SAMPLE:,} drawn from the population, "
      "pushed through `b8_omega.r_month` with a positive payment. The tolerance is six "
      "logarithms at `|log V| = 14`, the derivation `b8_2_curve` uses for two.\n")
    A("| archive | rows | of them named | largest gap | tolerance |")
    A("|---|---|---|---|---|")
    for d in rows:
        i = d["identity"]
        A(f"| {d['name']} | {i['rows']:,} | {i['named_rows']:,} | {_e(i['max_gap'], 2)} | "
          f"{_e(i['tol'], 2)} |")
    for d in rows:
        if d.get("disc_check"):
            x = d["disc_check"]
            A(f"\nOn {d['name']}, all {x['rows']:,} rows: the curve lookup equals "
              f"`b8_omega.disc_of_row` bit for bit: **{'yes' if x['equal'] else 'NO'}**; "
              "the interest-bearing balance equals `b8_core.zero_interest_split`: "
              f"**{'yes' if x.get('balance_equal') else 'NO'}**.\n")

    A("\n## 3. The published figures this file leans on, read back from the cache\n")
    A("At the printed precision, no tolerance.\n")
    A("| product | archive | figure | printed | from the cache | **same** |")
    A("|---|---|---|---|---|---|")
    for x in ev["repro"]:
        A(f"| {x['where']} | {x['archive']} | {x['what']} | {x['printed']} | "
          f"{x['mine']:.6g} | **{'yes' if x['ok'] else 'NO'}** |")
    A(f"\nSubsample cells of `b8_0b_floor.md` section 2.3 (21 draws per size, same "
      f"seed): **{ev['repro_sub'][1]} of {ev['repro_sub'][0]}** read the same.\n")

    A("\n## 4. The floor arm, by what its windows hold\n")
    A("`P` is B8-0b's population: measurable and on the ideal path. A step is a "
      "month whose field 17 did not step down by one (term) or whose field 9 moved "
      "(rate). Field 19 moves are counted beside them because field 17 is computed "
      "from it.\n")
    A("| archive | clean cures | measurable | ideal | **`P`** | term step: all | in `P` | "
      "rate step: all | in `P` | field 19 moved: all | in `P` | **named** |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for d in rows:
        f = d["floor"]
        A(f"| {d['name']} | {f['loops']:,} | {f['measurable']:,} | {f['ideal']:,} | "
          f"**{f['P']:,}** | {f['with_term_step']['all']:,} | {f['with_term_step']['P']:,} | "
          f"{f['with_rate_step']['all']:,} | {f['with_rate_step']['P']:,} | "
          f"{f['with_field19_move']['all']:,} | {f['with_field19_move']['P']:,} | "
          f"**{f['named']:,}** |")
    A("\n| archive | field 17 = field 19 minus the reporting month | largest `\\|C\\|` on an unnamed loop in `P` |")
    A("|---|---|---|")
    for d in rows:
        A(f"| {d['name']} | {d['field17_is_field19_minus_period']:.6f} | "
          f"{_e(d['floor']['C_A_max_unnamed'], 2)} |")

    A("\n## 5. The named loops\n")
    A("Every loop in `P` with a step, with its window and one month either side. "
      "`residual` is `omega - closed` as B8-0b computes it, `C` is the contract term "
      "summed over the window under the registered curve, and `remainder` is what is "
      "left. `bound` is `b8_0a_gate.rounding_bound` on the loop's smallest balance, "
      "the bound B8-0a's gate holds the ideal path to.\n")
    for d in rows:
        for e in d["named"]:
            A(f"\n### {d['name']}, loan {e['loan_id']}, window {e['t_A']} to {e['t_B']}, "
              f"`k` = {e['k']}\n")
            A("| residual | `C`, registered curve | `C`, far corner | **remainder** | "
              "bound | **inside** |")
            A("|---|---|---|---|---|---|")
            A(f"| {e['residual']:+.4e} | {e['C_A']:+.4e} | {e['C_B']:+.4e} | "
              f"**{e['remainder']:+.3e}** | {e['bound']:.3e} | "
              f"**{'yes' if abs(e['remainder']) <= e['bound'] else 'NO'}** |")
            A("\n| month | field 17 | field 19 | field 9 | `C`, registered | `C`, far corner |")
            A("|---|---|---|---|---|---|")
            for s in e["steps"]:
                A(f"| {s['month']} | {s['field17'][0]} to {s['field17'][1]} | "
                  f"{s['field19'][0]} to {s['field19'][1]} | "
                  f"{s['field9'][0]:.3f} to {s['field9'][1]:.3f} | {s['C_A']:+.4e} | "
                  f"{s['C_B']:+.4e} |")
            A("\n| vertex | month | 9 | 12 | 16 | 17 | 19 | 40 | 42 |")
            A("|---|---|---|---|---|---|---|---|---|")
            for p in e["path"]:
                f9 = "" if p["f9"] is None else f"{p['f9']:.3f}"
                A(f"| {p['row']} | {p['month']} | {f9} | {p['f12']:,.2f} | "
                  f"{'' if p['f16'] is None else p['f16']} | "
                  f"{'' if p['f17'] is None else p['f17']} | {p['f19']} | {p['f40']} | "
                  f"{p['f42']} |")

    A("\n## 6. O35's number, read back from those loops\n")
    A("| archive | term steps in `P` | largest `\\|C_far - C_registered\\|` over `P` | "
      "printed `max floor shift` | **read back** |")
    A("|---|---|---|---|---|")
    for s in ev["shift"]:
        A(f"| {s['archive']} | {s['term_named']} | {_e(s['mine'], 3)} | {s['printed']} | "
          f"**{'yes' if s['ok'] else 'NO'}** |")

    A("\n## 7. The batch: steps with no flag, by reporting month\n")
    A("Across every row of each archive, pairs of consecutive months in one loan with "
      "neither row carrying field 42 `Y`, a positive field 63 or a positive field 108, "
      "which is the screen the clean-cure arm applies. Term steps where field 17 had "
      "already reached one month are counted apart, since a step of minus one is no "
      "longer available there.\n")
    A("| archive | pairs with no flag | term steps | at maturity | rate steps | field 19 moves | "
      "term steps with a flag | rate steps with a flag |")
    A("|---|---|---|---|---|---|---|---|")
    for d in rows:
        t = d["totals"]
        A(f"| {d['name']} | {t['eligible_unflagged']:,} | {t['term_unflagged']:,} | "
          f"{t['term_unflagged_at_maturity']:,} | {t['rate_unflagged']:,} | "
          f"{t['mat_unflagged']:,} | {t['term_flagged']:,} | {t['rate_flagged']:,} |")
    for key, label in (("term_unflagged", "term steps with no flag"),
                       ("rate_unflagged", "rate steps with no flag")):
        A(f"\n**Months carrying the most {label}**, with the month's share of its own "
          "unflagged pairs.\n")
        A("| archive | month 1 | month 2 | month 3 | month 4 | month 5 | month 6 |")
        A("|---|---|---|---|---|---|---|")
        for d in rows:
            per = d["periods"]
            ranked = sorted(((v.get(key, 0), m) for m, v in per.items() if v.get(key, 0)),
                            key=lambda z: (-z[0], z[1]))[:TOP_PERIODS]
            cells = [f"{m}: {n:,} ({n / max(per[m].get('eligible_unflagged', 1), 1):.1e})"
                     for n, m in ranked]
            cells += [""] * (TOP_PERIODS - len(cells))
            A(f"| {d['name']} | " + " | ".join(cells) + " |")
    A("\n**The size of the steps**, most frequent first, as `(change, count)`.\n")
    A("| archive | field 17 on term steps | field 19 on term steps | field 9 on rate steps, thousandths of a per cent |")
    A("|---|---|---|---|")
    for d in rows:
        x = d["deltas"]
        A(f"| {d['name']} | {x['term_unflagged_d17']} | {x['term_unflagged_d19']} | "
          f"{x['rate_unflagged_d9']} |")

    A("\n## 8. The signal arm, described and not judged\n")
    A("Measurable loops holding a term or rate step in some month other than the "
      "onset. On this arm contract moves are the object, flags persist after an "
      "onset, and scheduled rate changes are contract terms, so this count is a size "
      "and not a contamination.\n")
    A("| archive | modification loops | with a step off the onset | deferral loops | with a step off the onset |")
    A("|---|---|---|---|---|")
    for d in rows:
        s = d["signal"]
        A(f"| {d['name']} | {s['mod']['measurable']:,} | {s['mod']['with_step_off_onset']:,} | "
          f"{s['defer']['measurable']:,} | {s['defer']['with_step_off_onset']:,} |")

    A("\n## 9. What the named loops do to what the floor feeds\n")
    A("`screened` drops the named loops from `P`; `corrected` keeps them with their "
      "contract term removed.\n")
    A("| archive | `N`'s `MAD`: published population | screened | corrected | "
      "`2*Var`: published population | screened | corrected |")
    A("|---|---|---|---|---|---|---|")
    for d in rows:
        N = d["N"]
        A(f"| {d['name']} | {_e(N['published_population']['mad'])} | {_e(N['screened']['mad'])} | "
          f"{_e(N['corrected']['mad'])} | {_e(N['published_population']['zed'])} | "
          f"{_e(N['screened']['zed'])} | {_e(N['corrected']['zed'])} |")
    A("\n**`sqrt(Z)/sqrt(N)`, the registered headline of `b8_0b_floor.md` section 3**, "
      "on the published population and on the screened one.\n")
    A("| archive | pooled | screened | modification | screened | deferral | screened |")
    A("|---|---|---|---|---|---|---|")
    for d in rows:
        pz, sz = d["N"]["published_population"]["zed"], d["N"]["screened"]["zed"]
        cells = []
        for arm in ("pooled", "mod", "defer"):
            Z = d["arms"][arm]["Z"]
            cells += [f"{np.sqrt(Z) / np.sqrt(pz):.3e}", f"**{np.sqrt(Z) / np.sqrt(sz):.3e}**"]
        A(f"| {d['name']} | " + " | ".join(cells) + " |")
    A("\n**Does `2*Var` on the floor settle as the sample grows, once the named loops "
      "are out.** The same draw `b8_0b_floor.md` section 2.3 used (21 per size, same "
      "seed), p10, median and p90, then the spread p90/p10.\n")
    A("| archive | population | n | `2*Var` p10 | median | p90 | spread | `MAD` median |")
    A("|---|---|---|---|---|---|---|---|")
    for d in rows:
        for tag in ("published_population", "screened"):
            for c in d["N"][tag]["conv"]:
                spread = c["var_hi"] / c["var_lo"] if c["var_lo"] > 0 else float("nan")
                A(f"| {d['name']} | {tag.replace('_', ' ')} | {c['n']:,} | {_e(c['var_lo'])} | "
                  f"{_e(c['var_med'])} | {_e(c['var_hi'])} | {spread:,.1f}x | {_e(c['mad_med'])} |")

    A("\n## 10. The criteria\n")
    A(kinds_line(ev["criteria"]) + "\n")
    A("| | criterion | kind | detail |")
    A("|---|---|---|---|")
    for c in ev["criteria"]:
        A(f"| {'PASS' if c['passed'] else 'FAIL'} | {c['name']} | {c['kind']} | "
          f"{c['detail'].replace('|', '/')} |")
    A("\n**B8-O35-7 has three states per verdict and they map as follows**: the quoted "
      "figures read the same on the screened floor (holds); a quoted figure moves and "
      "the verdict's condition still holds (holds, and the moved figure is printed so "
      "the verdict text can point here); the condition fails (does not hold).\n")
    A("| verdict | figure | quoted | screened | figures | condition | condition holds |")
    A("|---|---|---|---|---|---|---|")
    for x in ev["digits"]:
        A(f"| {x['verdict']} | {x['what']} | {x['quoted']} | {x['screened']} | "
          f"{'same' if x['digits_hold'] else 'move'} | {x['condition']} | "
          f"**{'yes' if x['condition_holds'] else 'NO'}** |")

    A("\n## What this does not decide\n")
    A("- **Whether the clean-cure screen should also read fields 9 and 19.** That "
      "changes the registered population of B8-0a and B8-0b and every figure printed "
      "from it; this file prints both populations and changes neither.")
    A("- **What the signal arm's off-onset steps are.** Section 8 is a size.")
    A("- **What the months in section 7 were.** A batch of maturity dates moving by a "
      "month with no flag is a fact about the file; the programme or servicer practice "
      "behind it is not read here.")
    A("- **The loop cache's tag.** `b8_cache.tag` hashes source text, so the two "
      "comment edits in section 1 leave every B8 station that calls `b8_cache.get` "
      "rebuilding. The syntax-tree comparison applied here is not what that function "
      "computes, and this file neither retags nor rebuilds.\n")
    return "\n".join(Ls) + "\n"


TOP_PERIODS = 6


def cmd_render() -> int:
    rows = _load_scans()
    texts = {k: p.read_text(encoding="utf-8") for k, p in PRODUCTS.items()}
    ev = evaluate(rows, texts)
    txt = render(rows, ev)
    bad = K.check_markdown_tables(txt)
    if bad:
        for b in bad:
            print("MALFORMED " + b, file=sys.stderr)
        return 1
    OUT_MD.write_text(txt, encoding="utf-8", newline="\n")
    record = {
        "stage": "B8-O35",
        "config": {"rule_registered": list(RULE_A), "rule_far_corner": list(RULE_B),
                   "population": "measurable and ideal-path clean cures (B8-0b's N)",
                   "identity_sample": IDENTITY_SAMPLE, "seed": SEED, "pad": PAD,
                   "archives": list(ARCHIVES)},
        "criteria": ev["criteria"],
        "report": {
            "named": [{"archive": d["name"], "loan": e["loan_id"], "window": [e["t_A"], e["t_B"]],
                       "k": e["k"], "residual": e["residual"], "contract_term": e["C_A"],
                       "remainder": e["remainder"], "bound": e["bound"],
                       "steps": [{"month": s["month"], "field17": s["field17"],
                                  "field19": s["field19"], "field9": s["field9"]}
                                 for s in e["steps"]]}
                      for d in rows for e in d["named"]],
            "floor": {d["name"]: d["floor"] for d in rows},
            "unflagged_step_totals": {d["name"]: d["totals"] for d in rows},
            "N_mad": {d["name"]: {k: d["N"][k]["mad"] for k in d["N"]} for d in rows},
            "N_2var": {d["name"]: {k: d["N"][k]["zed"] for k in d["N"]} for d in rows},
            "verdict_figures": ev["digits"],
        },
    }
    OUT_JSON.write_text(_dump(record), encoding="utf-8", newline="\n")
    print(f"wrote {OUT_MD}\nwrote {OUT_JSON}", file=sys.stderr)
    for c in ev["criteria"]:
        print(f"  {'PASS' if c['passed'] else 'FAIL'} {c['name']} [{c['kind']}]",
              file=sys.stderr)
    return 0 if all(c["passed"] for c in ev["criteria"]) else 1


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

class _Fake:
    pass


def selftest() -> int:
    fails: list[str] = []
    rng = np.random.default_rng(17)

    # -- 1. the identity, on the production `r_month`, in four cases ---------
    m = 4000
    b_prev = rng.uniform(2e3, 9e5, m)
    i_prev = rng.uniform(2.0, 9.0, m)
    n_raw = rng.integers(4, 400, m).astype(np.float64)
    d = rng.uniform(0.3, 7.5, m)
    pay = K.level_payment(b_prev, i_prev, n_raw)
    bhat = b_prev * (1.0 + i_prev / 1200.0) - pay
    b_now = bhat * (1.0 + rng.normal(0.0, 1e-6, m))
    cases = {
        "none": (i_prev, n_raw - 1.0),
        "term": (i_prev, n_raw - 1.0 + rng.choice([1.0, -1.0, 2.0], m)),
        "rate": (i_prev + rng.choice([-1.0, 1.0, 0.125], m), n_raw - 1.0),
        "both": (i_prev + 0.5, n_raw),
    }
    for name, (i_now, n_now) in cases.items():
        lhs = W.r_month(b_now, b_prev, i_now, pay, n_now, d, note_prev=i_prev,
                        n_prev=n_raw - 1.0) - (np.log(b_now) - np.log(bhat))
        c1 = contract_term(i_now * 1000.0, i_prev * 1000.0, n_now, n_raw, d)
        gap = float(np.abs(lhs - c1).max())
        if not gap <= IDENTITY_TOL:
            fails.append(f"{name}: r - log(B/B_hat) differs from the contract term "
                         f"by {gap:.3e}, past {IDENTITY_TOL:.3e}")
        c2 = contract_term(i_now * 1000.0, i_prev * 1000.0, n_now, n_raw, d + 1.0)
        if name == "none" and np.any(c1 != 0.0):
            fails.append("with no step the contract term must be exactly zero")
        if name == "rate" and float(np.abs(c1 - c2).max()) > IDENTITY_TOL:
            fails.append("a pure rate step moved with the curve; it must not")
        if name == "term" and not float(np.abs(c1 - c2).min()) > IDENTITY_TOL:
            fails.append("a term step did not move with the curve on some row")
    # the check can fire: a contract term that assumes the horizon stepped
    # normally must disagree with `r_month` on the term-step rows
    i_now, n_now = cases["term"]
    lhs = W.r_month(b_now, b_prev, i_now, pay, n_now, d, note_prev=i_prev,
                    n_prev=n_raw - 1.0) - (np.log(b_now) - np.log(bhat))
    wrong = contract_term(i_now * 1000.0, i_prev * 1000.0, n_now, n_now + 1.0, d)
    if not float(np.abs(lhs - wrong).max()) > 1e-6:
        fails.append("the identity check cannot tell a term step from none")

    # -- 2. the lookups against the production functions ---------------------
    months = sorted(rng.choice(np.arange(100, 400), 60, replace=False).tolist())
    pos = {int(mi): j for j, mi in enumerate(months)}
    tab = rng.uniform(0.1, 6.0, (len(months), W.MAX_H + 1))
    tab[rng.random(tab.shape) < 0.01] = np.nan
    nf = 5000
    fk = _Fake()
    fk.n_rows = nf
    per = rng.choice(np.array(months + [5, 7, K.U16_NA]), nf).astype(np.uint16)
    rem = rng.integers(0, W.MAX_H + 5, nf).astype(np.uint16)
    rem[rng.random(nf) < 0.02] = K.U16_NA
    upb = rng.integers(0, 50_000_000, nf).astype(np.uint32)
    nib = np.where(rng.random(nf) < 0.1, rng.integers(0, 900_000, nf), 0).astype(np.uint32)
    nib[rng.random(nf) < 0.05] = K.U32_NA
    dfr = np.where(rng.random(nf) < 0.1, rng.integers(0, 900_000, nf), 0).astype(np.uint32)
    dfr[rng.random(nf) < 0.05] = K.U32_NA
    fk.row = {"period": per, "rem_legal": rem, "upb": upb, "nib_upb": nib,
              "defer_amt": dfr}
    if not np.array_equal(W.disc_of_row(fk, pos, tab)[0], disc_at(pos, tab, per, rem),
                          equal_nan=True):
        fails.append("disc_at disagrees with b8_omega.disc_of_row on the fixture")
    zfull = K.zero_interest_split(fk)[0].astype(np.float64) / 100.0
    if not np.array_equal(zfull, bal_at(fk, np.arange(nf))):
        fails.append("bal_at disagrees with b8_core.zero_interest_split on the fixture")

    # -- 3. windows and steps ----------------------------------------------------
    rows, owner = window_index([0, 5, 9], [2, 6, 12])
    if rows.tolist() != [1, 2, 6, 10, 11, 12] or owner.tolist() != [0, 0, 1, 2, 2, 2]:
        fails.append(f"window_index returned {rows.tolist()} / {owner.tolist()}")
    try:
        window_index([3], [3])
        fails.append("a window with no months was accepted")
    except ValueError:
        pass
    Y, N_ = ord("Y"), ord("N")
    # loan 2 opens the month after loan 1 closes, so only the first-row cut keeps
    # the pair across the boundary out; its third row skips a month
    per = np.array([100, 101, 102, 103, 104, 105, 106, 107, 109, 110], np.uint16)
    rem = np.array([300, 299, 298, 298, 297, 296, 3, 2, 1, 1], np.uint16)
    rate = np.array([5000] * 5 + [5125] + [4000] * 4, np.uint16)
    mat = np.array([400] * 3 + [401] * 3 + [55] * 4, np.uint16)
    mod = np.array([N_] * 7 + [Y] + [N_] * 2, np.uint8)
    na32 = np.full(10, K.U32_NA, np.uint32)
    first = np.zeros(10, bool)
    first[[0, 6]] = True
    mk = step_masks(per, rate, rem, mat, mod, na32, na32, first)
    want = {"eligible": [1, 2, 3, 4, 5, 7, 9], "term": [3, 9], "rate": [5],
            "mat": [3], "flagged": [7, 8]}
    for k_, v in want.items():
        if np.flatnonzero(mk[k_]).tolist() != v:
            fails.append(f"step_masks {k_}: {np.flatnonzero(mk[k_]).tolist()}, want {v}")
    if not (mk["at_maturity"][9] and not mk["at_maturity"][3]):
        fails.append("the maturity split does not mark the pair after a one-month horizon")

    # -- 4. provenance -------------------------------------------------------------
    rel = [Path(inspect.getsourcefile(mm)).resolve().relative_to(K.ROOT).as_posix()
           for mm in C.SOURCE_MODULES]
    work = [inspect.getsource(mm) for mm in C.SOURCE_MODULES]

    def fake_git(old):
        def g(args):
            if args[0] == "log":
                return b"aaaaaaaaaaaaaaaa\n"
            path = args[1].split(":", 1)[1]
            return old[rel.index(path)].encode("utf-8")
        return g

    if provenance(C.tag())["status"] != "current":
        fails.append("provenance does not read today's tag as current")
    if _tag_of(work) != C.tag():
        fails.append("the tag arithmetic here does not reproduce b8_cache.tag")
    prose = list(work)
    prose[0] = prose[0] + "\n# a comment added by the selftest\n"
    q = provenance(_tag_of(prose), git=fake_git(prose))
    if q["status"] != "prose-only" or q.get("text_differs") != [rel[0]]:
        fails.append(f"a comment-only difference read as {q}")
    doc = list(work)
    doc[-1] = doc[-1].replace('"""', '"""Selftest. ', 1)
    q = provenance(_tag_of(doc), git=fake_git(doc))
    if doc[-1] == work[-1] or q["status"] != "prose-only":
        fails.append(f"a docstring-only difference read as {q}")
    code = list(work)
    code[1] = code[1] + "\nO35_SELFTEST_CONSTANT = 1\n"
    q = provenance(_tag_of(code), git=fake_git(code))
    if q["status"] != "code-changed" or q.get("code_differs") != [rel[1]]:
        fails.append(f"a code difference read as {q}")
    if provenance("0000000000000000", git=fake_git(work))["status"] != "no-commit-matches":
        fails.append("an unknown tag was matched to a commit")

    # -- 5. reading printed figures ------------------------------------------------
    for x, s, want_ in ((3.1019e-06, "3.102e-06", True), (3.1026e-06, "3.102e-06", False),
                        (2773329.74, "2,773,329.7", True), (5139, "5,139", True),
                        (0.0010743, "+1.0743e-03", True), (1.0, "yes", None)):
        if at_printed(x, s) is not want_:
            fails.append(f"at_printed({x}, {s!r}) is {at_printed(x, s)}, want {want_}")
    txt = "x\n| archive | a | b |\n|---|---|---|\n| 2017Q1 | **1.0e+00** | `2` |\n\ny\n"
    if published_table(txt, "| archive | a |") != [["2017Q1", "1.0e+00", "2"]]:
        fails.append("published_table misread a two-cell row")
    p_ = float(K.level_payment(np.array([200000.0]), np.array([5.0]), np.array([300.0]))[0])
    b_ = 200000.0
    for _ in range(3):
        b_ = b_ * (1.0 + 5.0 / 1200.0) - p_
    if abs(implied_payment(200000.0, b_, 5.0, 3) - p_) > 1e-6:
        fails.append("implied_payment does not recover the payment of a scheduled path")

    for f_ in fails:
        print("FAIL " + f_, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the identity holds on r_month in four cases and can fire, the "
          "lookups match the production functions, and provenance separates prose "
          "from code", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["scan", "render", "selftest"])
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args()
    if args.command == "selftest":
        raise SystemExit(selftest())
    if args.command == "render":
        raise SystemExit(cmd_render())
    keep = set(args.only or ARCHIVES)
    raise SystemExit(cmd_scan([n for n in ARCHIVES if n in keep]))


if __name__ == "__main__":
    main()
