#!/usr/bin/env python3
"""The loop cache: `omega` computed once per archive, read by every station.

**Why.** `b8_loop_omega`, `b8_0b_floor`, `b8_3_paths` and `b8_2_windows` each
rebuilt the whole pipeline from the core table: `disc_of_row`,
`row_residuals`, `find_loops`, `loop_sums`. That is four full scans of 170
million rows per pass, and the expensive part inside it is
`contract_payments`, a Python loop over several million contract periods.
Every re-run of any station paid it again. The instruction to cache reusable
intermediates has been standing since the start of this project and was not
followed.

What is cached is small: 85,308 loops across the six archives, a couple of
dozen fields, a few megabytes. What it replaces is an archive scan.

--------------------------------------------------------------------------
The tag, which is the only thing that makes this safe
--------------------------------------------------------------------------

**A stale cache is worse than no cache.** This repository's pit table is
largely a list of things that were true once and were still being read later,
so a cache keyed on the archive name alone would be a machine for
manufacturing that defect.

So the key is a **hash of the source of every function that produced the
numbers** -- `b8_core`, `b8_omega`, `b8_loops`, `b8_loop_omega` -- together
with the curve rule and the archive's own manifest. Edit any of them and the
tag changes and the cache is rebuilt. Nothing has to remember to invalidate
it. `b8_core._fixture_tag` already uses this trick for the selftest fixtures,
so it is the house pattern rather than a new idea.

The tag is stored beside the data and checked on load. `load` on a stale or
missing entry raises; it never returns the old numbers.

--------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------

    python experiments/b8_cache.py build            # all archives
    python experiments/b8_cache.py build --only 2019Q1
    python experiments/b8_cache.py status
    python experiments/b8_cache.py verify           # recompute and compare
    python experiments/b8_cache.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b8_core as K                                            # noqa: E402
import b8_omega as W                                           # noqa: E402
import b8_loops as L                                           # noqa: E402
import b8_loop_omega as Z8                                     # noqa: E402
import b8_0a_gate as G                                         # noqa: E402
import b8_triangles as T                                       # noqa: E402

CACHE = K.ROOT / "data" / "processed" / "b8_loops"

#: Modules whose source decides the numbers. **Whole modules, not the
#: functions this file happens to call**: a helper three levels down is just as
#: load-bearing, and naming functions individually is a list that goes stale.
#:
#: **This module is in the list too.** The first version left it out, and then
#: adding `leg2_split` -- a function whose output goes straight into the cached
#: fields -- left the tag unchanged. A cache tag that does not cover the code
#: writing the cache is the exact defect the tag exists to prevent, sitting
#: inside the tag.
SOURCE_MODULES = (K, W, L, Z8, G, sys.modules[__name__])

#: Fields kept per signal loop. Everything a downstream station has needed so
#: far, and nothing that belongs to one station's own diagnostics.
SIGNAL_FIELDS = ("t_A", "t_M", "t_B", "arm", "loan", "omega", "leg1", "leg2",
                 "n_win", "n_have", "measurable", "miss_before", "miss_after",
                 "n1", "n3", "window", "rem_A", "n_onsets",
                 "l2_balance", "l2_repricing", "l2_rate", "l2_term",
                 "l2_balloon", "l2_ok",
                 "l1_closed", "bal_A", "rate_A", "pay_A")

#: Fields kept per clean-cure loop, which is B8-0b's floor arm.
FLOOR_FIELDS = ("t_A", "t_M", "t_B", "k", "loan", "omega", "n_win",
                "measurable", "ideal", "closed", "rem_A")


def tag() -> str:
    """A hash of the code and the rules that produce the cached numbers."""
    h = hashlib.sha256()
    for m in SOURCE_MODULES:
        h.update(inspect.getsource(m).encode("utf-8"))
    h.update(repr((Z8.RULE, W.MAX_H, K.SCHEMA_VERSION)).encode("utf-8"))
    return h.hexdigest()[:16]


def _path(name: str, cache_root=None) -> Path:
    return (cache_root or CACHE) / f"{name}.npz"


def build(name: str, cache_root=None, pos=None, tab=None,
          core_root=None) -> dict:
    """Compute everything once and write it. Returns the same dict `load` does."""
    if pos is None or tab is None:
        pos, tab = Z8.curve_table()
    c = K.Core(name, cols=Z8.COLS + ["zero_bal"], cache_root=core_root)
    try:
        disc, dinfo = W.disc_of_row(c, pos, tab)
        r, ok, rinfo = W.row_residuals(c, disc)

        lp = L.find_loops(c)
        sig = Z8.loop_sums(lp, r, ok)
        rem = c.row["rem_legal"][:].astype(np.int64)
        win = _window_of(c, lp["t_M"])

        # the floor arm, through the same summation (§18.3 N1)
        t0, _st, en, kk, cdrops = G.find_clean_cures(c, require_no_defer=True)
        cc = {"t_A": t0, "t_M": t0 + 1, "t_B": en, "k": kk,
              "arm": np.full(t0.size, L.ARM_MOD, dtype=np.int8),
              "loan": c.loan_of_row()[t0] if t0.size else np.zeros(0, np.int32)}
        flo = Z8.loop_sums(cc, r, ok)
        q0 = K.quiet_pairs(c)
        pid0 = W.contract_periods(c, fill=True)
        pay0, _kn, _pp = W.contract_payments(c, pid0, q0)
        es = G.episode_sums(c, pay0, cc["t_A"], cc["t_B"], cc["k"])
        spl = leg2_split(c, lp, disc, pay0, sig["leg2"], ok)
        spl.update(leg1_closed(c, lp, pay0, sig["n1"]))

        out = {
            "sig": {
                "t_A": lp["t_A"], "t_M": lp["t_M"], "t_B": lp["t_B"],
                "arm": lp["arm"], "loan": lp["loan"],
                "omega": sig["omega"], "leg1": sig["leg1"],
                "leg2": sig["leg2"], "n_win": sig["n_win"],
                "n_have": sig["n_have"], "measurable": sig["measurable"],
                "miss_before": sig["miss_before"],
                "miss_after": sig["miss_after"],
                "n1": sig["n1"], "n3": sig["n3"],
                "window": win, "rem_A": rem[lp["t_A"]],
                "n_onsets": lp["n_onsets"],
                **spl,
            },
            "floor": {
                "t_A": cc["t_A"], "t_M": cc["t_M"], "t_B": cc["t_B"],
                "k": cc["k"], "loan": cc["loan"], "omega": flo["omega"],
                "n_win": flo["n_win"], "measurable": flo["measurable"],
                "ideal": es[2], "closed": es[1],
                "rem_A": rem[cc["t_A"]],
            },
            "meta": {
                "name": name, "tag": tag(),
                "n_rows": int(c.n_rows), "n_loans": int(c.n_loans),
                "identity_max": sig["identity_max"],
                "prefix_scale": sig["prefix_scale"],
                "excluded_two_arms": int(lp["excluded_two_arms"]["t_A"].size),
                "loop_counts": lp["counts"],
                "curve": dinfo,
                "rows": {k_: v for k_, v in rinfo.items()
                         if k_ not in ("V",)},
                "carrier": rinfo["V"]["carrier"],
                "V": {k_: v for k_, v in rinfo["V"].items()
                      if k_ not in ("bad", "carrier", "horizon")},
                "horizon": rinfo["V"]["horizon"],
                "clean_cure_drops": cdrops,
            },
        }
    finally:
        c.close()

    p = _path(name, cache_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    flat = {f"sig__{k_}": v for k_, v in out["sig"].items()}
    flat.update({f"floor__{k_}": v for k_, v in out["floor"].items()})
    flat["meta__json"] = np.frombuffer(
        json.dumps(out["meta"], default=_jsonable).encode("utf-8"),
        dtype=np.uint8)
    np.savez_compressed(p, **flat)
    return out


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    raise TypeError(type(x))


def _window_of(c: K.Core, rows: np.ndarray) -> np.ndarray:
    """§6's windows by reporting month. One copy, here, rather than one per
    station: it was written twice already."""
    per = c.row["period"][:].astype(np.int64)[rows]
    out = np.full(rows.size, -1, dtype=np.int64)
    for k, (_n, lo, hi) in enumerate(T.WINDOWS):
        m = (per >= T._to_month_index(lo)) & (per <= T._to_month_index(hi))
        out[m] = k
    return out


def logk(i, d, n):
    """`log k(i, d, n)` with `k = LP(1, i, n) * A(d, n)`, so `V = B * k`.

    At `d == i` this is exactly zero. Below the note rate it is positive and
    **rises with `n`**; above it, negative and falling. That pair of facts is
    what §2.1 reads a positive `term` column as meaning, so both are asserted
    in the selftest rather than left as prose.
    """
    n = np.asarray(n, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (np.log(W.level_payment(np.ones_like(n), i, n))
                + np.log(W.annuity(d, n)))


def leg2_terms(i_now, i_prev, n_now, n_hat, d, b_now, b_hat, leg2) -> dict:
    """The arithmetic of :func:`leg2_split`, with no core table in sight.

    **Split out so the sub-channels can be pinned.** The first version did the
    reading and the arithmetic in one function, and a mutation run found that
    the closure test caught every error in `balance` and `repricing` while
    `rate` and `term` were not pinned at all: both are differences from the
    same base and `cross` is the residual, so a `rate` that silently computed
    the whole repricing, or one that computed identically zero, still added
    up. `rate` and `term` are the two columns §2.1's reading turns on, so
    that is the worst place in the file to have an unpinned number.

    Every argument is an array over loops. Returns the five terms with NaN
    wherever the inputs do not admit a reading.
    """
    i_now, i_prev = np.asarray(i_now, float), np.asarray(i_prev, float)
    n_now, n_hat = np.asarray(n_now, float), np.asarray(n_hat, float)
    d = np.asarray(d, float)
    b_now, b_hat = np.asarray(b_now, float), np.asarray(b_hat, float)
    ok = (np.isfinite(b_now) & (b_now > 0) & np.isfinite(b_hat) & (b_hat > 0)
          & (n_now > 0) & (n_hat > 0) & np.isfinite(d) & (i_now > 0)
          & (i_prev > 0))
    out = {k_: np.full(ok.shape, np.nan) for k_ in
           ("l2_balance", "l2_repricing", "l2_rate", "l2_term", "l2_balloon")}
    s = np.flatnonzero(ok)
    if s.size:
        kb = logk(i_prev[s], d[s], n_hat[s])
        out["l2_balance"][s] = np.log(b_now[s]) - np.log(b_hat[s])
        out["l2_repricing"][s] = logk(i_now[s], d[s], n_now[s]) - kb
        out["l2_rate"][s] = logk(i_now[s], d[s], n_hat[s]) - kb
        out["l2_term"][s] = logk(i_prev[s], d[s], n_now[s]) - kb
        out["l2_balloon"][s] = (np.asarray(leg2, float)[s]
                                - out["l2_balance"][s]
                                - out["l2_repricing"][s])
    out["l2_ok"] = ok
    return out


def leg1_closed(c: K.Core, lp: dict, pay_row, n1) -> dict:
    """Leg 1's closed form on the **modification** arm, and its three inputs.

    **Why this is the same object B8-0b found on the floor arm.**
    `loop_residual_ideal` is a sum over the loop, and it factors by leg. On a
    flat delinquent run the balance holds at `B_A`, the note rate does not
    move, and field 17 runs down by one a month, so `k(i, d, n)` cancels
    between `V` and `V-hat` and each month contributes the same

        r(t) = log B_A - log( B_A * (1 + i/1200) - P )

    with `n1` such months in leg 1. That expression is the first term of
    `loop_residual_ideal`; the rest of it is the cure month, which the
    modification arm does not have because the contract moves instead.

    **Nothing before `t_M` knows a modification is coming**, so leg 1 on the
    modification arm is exactly the artifact B8-0b measured, and it can be
    subtracted rather than assumed small. O32 left that as an inference:
    "if the modification arm carries the same deterministic component and it
    is of the same order, it is a ten-thousandth of the signal, **but that is
    an inference and not a measurement**." This makes it a measurement.

    Returns `l1_closed` and the three per-loop inputs, so a later station can
    re-derive it without re-opening an archive.
    """
    tA = lp["t_A"]
    bal_c, _z = K.zero_interest_split(c)
    bal_A = bal_c[tA].astype(np.float64) / 100.0
    rate_A = c.row["rate"][:].astype(np.float64)[tA] / 1000.0
    pay_A = np.asarray(pay_row, dtype=np.float64)[tA]
    n1 = np.asarray(n1, dtype=np.float64)

    b_next = bal_A * (1.0 + rate_A / 1200.0) - pay_A
    with np.errstate(divide="ignore", invalid="ignore"):
        per_month = np.log(bal_A) - np.log(b_next)
    ok = (bal_A > 0) & (b_next > 0) & (rate_A > 0) & np.isfinite(pay_A) \
        & (pay_A > 0) & (n1 >= 0)
    return {"l1_closed": np.where(ok, n1 * per_month, np.nan),
            "bal_A": bal_A, "rate_A": rate_A, "pay_A": pay_A}


def leg2_split(c: K.Core, lp: dict, disc, pay_row, leg2, ok_row) -> dict:
    """Leg 2 at `t_M`, decomposed exactly. **Additive, not an approximation.**

    `V = B * k(i, d, n) + Z * q` with `k(i, d, n) = LP(1, i, n) * A(d, n)`, so

        r(t_M) = log(B_now / B_hat)      the arrears capitalised
               + log(k_now / k_hat)      the repricing
               + a remainder             the balloon, and field 64, which is
                                         identically zero on these archives

    **Why it is needed.** B8-2 came back with leg 2 positive in all 29 readable
    cells while §14.3 predicted negative, so the modification raises the
    present value of the obligation. Before that is read as a fact about
    modifications it has to be separated from a property of the construction:
    when `d < i` the factor `k` exceeds one and **grows with `n`**, so a term
    extension raises `V` mechanically, and Treasury yields sat far below
    mortgage note rates through most of the sample. At `d = i` the repricing
    term is exactly zero.

    The repricing term is split again by holding one contract term fixed:

        rate  = log k(i_now,  d, n_hat) - log k(i_prev, d, n_hat)
        term  = log k(i_prev, d, n_now) - log k(i_prev, d, n_hat)
        cross = repricing - rate - term        the interaction, printed

    Returns arrays over loops, NaN where `t_M`'s residual was not computable.

    **The balloon term is the residual, so it is only meaningful where `leg2`
    is.** `loop_sums` writes `0.0` into `leg2` on a month it could not read,
    and subtracting two finite terms from that zero would print a large
    spurious balloon on exactly the loops that were dropped for being
    unreadable. Every station that renders this filters on `measurable` first,
    but a field that is a lie when read without a filter is the shape of half
    this project's pit table, so the mask is applied here instead of trusted
    to the caller.
    """
    tM = lp["t_M"]
    rate = c.row["rate"][:].astype(np.float64) / 1000.0
    rem = c.row["rem_legal"][:].astype(np.float64)
    bal_c, zib_c = K.zero_interest_split(c)
    bal = bal_c.astype(np.float64) / 100.0

    i_now, i_prev = rate[tM], rate[tM - 1]
    n_now, n_hat = rem[tM], rem[tM - 1] - 1.0
    d = np.asarray(disc)[tM]
    b_now = bal[tM]
    b_hat = bal[tM - 1] * (1.0 + i_prev / 1200.0) - pay_row[tM - 1]

    out = leg2_terms(i_now, i_prev, n_now, n_hat, d, b_now, b_hat, leg2)
    out["l2_ok"] = out["l2_ok"] & np.asarray(ok_row)[tM]
    for k_ in [f for f in out if f != "l2_ok"]:
        out[k_] = np.where(out["l2_ok"], out[k_], np.nan)
    return out


def load(name: str, cache_root=None) -> dict:
    """Read a cached archive. **Raises on a missing or stale entry**; it never
    returns numbers produced by code that has since changed."""
    p = _path(name, cache_root)
    if not p.exists():
        raise FileNotFoundError(
            f"no loop cache for {name}. Run: python experiments/b8_cache.py "
            f"build --only {name}")
    with np.load(p, allow_pickle=False) as z:
        meta = json.loads(bytes(z["meta__json"]).decode("utf-8"))
        if meta.get("tag") != tag():
            raise ValueError(
                f"the loop cache for {name} was built by different code "
                f"(tag {meta.get('tag')}, current {tag()}). Run: python "
                f"experiments/b8_cache.py build --only {name}")
        sig = {k_[5:]: z[k_] for k_ in z.files if k_.startswith("sig__")}
        flo = {k_[7:]: z[k_] for k_ in z.files if k_.startswith("floor__")}
    return {"sig": sig, "floor": flo, "meta": meta}


def get(name: str, cache_root=None, **kw) -> dict:
    """`load`, falling back to `build` when missing or stale."""
    try:
        return load(name, cache_root)
    except (FileNotFoundError, ValueError) as e:
        print(f"  {name}: {type(e).__name__}, rebuilding", file=sys.stderr)
        return build(name, cache_root=cache_root, **kw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_status(names, cache_root=None) -> int:
    cur = tag()
    print(f"current code tag: {cur}", file=sys.stderr)
    for n in names:
        p = _path(n, cache_root)
        if not p.exists():
            print(f"  {n:12} absent", file=sys.stderr)
            continue
        try:
            m = load(n, cache_root)["meta"]
            print(f"  {n:12} ok    {m['tag']}  "
                  f"{p.stat().st_size / 1e6:.1f} MB  "
                  f"{m['sig'] if 'sig' in m else ''}"
                  f"{len(load(n, cache_root)['sig']['omega']):,} loops",
                  file=sys.stderr)
        except ValueError as e:
            print(f"  {n:12} STALE {str(e)[-40:]}", file=sys.stderr)
    return 0


def cmd_verify(names, cache_root=None) -> int:
    """Recompute from the core table and compare, field by field."""
    pos, tab = Z8.curve_table()
    bad = 0
    for n in names:
        cached = load(n, cache_root)
        fresh = build(n, cache_root=cache_root / "_verify" if cache_root
                      else CACHE / "_verify", pos=pos, tab=tab)
        for grp in ("sig", "floor"):
            for f in cached[grp]:
                a, b = cached[grp][f], fresh[grp][f]
                if not np.array_equal(np.asarray(a), np.asarray(b),
                                      equal_nan=True):
                    print(f"  {n} {grp}.{f} DIFFERS", file=sys.stderr)
                    bad += 1
        print(f"  {n}: {'ok' if not bad else 'MISMATCH'}", file=sys.stderr)
    return 1 if bad else 0


def selftest() -> int:
    fails: list[str] = []

    # -- the tag must move when the code moves ----------------------------
    # **This is the whole safety property.** A cache keyed on the archive name
    # would hand back numbers produced by code that has since changed, which is
    # the defect half this repository's pit table is made of.
    t0 = tag()
    if len(t0) != 16:
        fails.append(f"tag is {t0!r}, expected 16 hex characters")
    real = W.MAX_H
    try:
        W.MAX_H = real + 1
        if tag() == t0:
            fails.append("changing a rule that feeds the numbers did not move "
                         "the tag; a stale cache would be served silently")
    finally:
        W.MAX_H = real
    if tag() != t0:
        fails.append("the tag did not come back after the rule was restored")
    # and a source change must move it too, which is the case a constant
    # cannot reach: the tag hashes whole modules
    src = inspect.getsource(SOURCE_MODULES[0])
    if "def quiet_pairs" not in src:
        fails.append("the tag is not hashing whole module sources, so an edit "
                     "to a helper it does not name would not invalidate")
    # **and this module must be in its own hash.** It was not, and adding
    # `leg2_split` -- whose output is a cached field -- then left the tag
    # unchanged.
    if sys.modules[__name__] not in SOURCE_MODULES:
        fails.append("b8_cache does not hash its own source; editing `build` "
                     "or `leg2_split` would change the cached numbers without "
                     "moving the tag")
    if "def leg2_split" not in inspect.getsource(sys.modules[__name__]):
        fails.append("the self-hash does not reach this module's functions")

    # -- build, load, and compare against the direct computation ----------
    root = K.CACHE / "_selftest_loops"
    zp = root / "raw" / f"2099Q1_{L._fixture_tag()}.zip"
    if not zp.exists():
        L._synth_loops(zp)
    cr = root / "cache"
    K.build_archive(zp, force=True, cache_root=cr)
    with K.Core(zp.stem, cols=Z8.COLS, cache_root=cr) as c:
        months = np.unique(c.row["period"][:])
        months = months[months != K.U16_NA]
        pos, tab = Z8._flat_curve(months)

    cache_root = root / "loopcache"
    built = build(zp.stem, cache_root=cache_root, pos=pos, tab=tab,
                  core_root=cr)
    got = load(zp.stem, cache_root=cache_root)

    # **the cached numbers must equal the direct ones bit for bit**, computed
    # here without touching the cache at all
    with K.Core(zp.stem, cols=Z8.COLS + ["zero_bal"], cache_root=cr) as c2:
        disc, _ = W.disc_of_row(c2, pos, tab)
        r2, ok2, _ = W.row_residuals(c2, disc)
        lp2 = L.find_loops(c2)
        sig2 = Z8.loop_sums(lp2, r2, ok2)
    for f, direct in (("omega", sig2["omega"]), ("leg1", sig2["leg1"]),
                      ("leg2", sig2["leg2"]), ("n_win", sig2["n_win"]),
                      ("measurable", sig2["measurable"]),
                      ("t_A", lp2["t_A"]), ("t_M", lp2["t_M"]),
                      ("t_B", lp2["t_B"]), ("arm", lp2["arm"])):
        if not np.array_equal(np.asarray(got["sig"][f]),
                              np.asarray(direct), equal_nan=True):
            fails.append(f"cached sig.{f} differs from the direct computation")
    if got["sig"]["omega"].size == 0:
        fails.append("the fixture cached no loop, so nothing above is tested")

    # -- `k`, the factor §2.1's whole reading rests on --------------------
    # **This is an analytic claim being used to interpret a measurement**, so
    # it is asserted rather than written in prose and believed. `V = B * k`
    # with `k(i, d, n) = LP(1, i, n) * A(d, n)`.
    def _k(i, dd, n):
        return W.level_payment(1.0, i, n) * W.annuity(dd, n)

    for i_ in (4.0, 6.5, 9.0):
        for n_ in (60.0, 180.0, 360.0):
            if abs(_k(i_, i_, n_) - 1.0) > 1e-12:
                fails.append(f"k({i_}, {i_}, {n_}) = {_k(i_, i_, n_)}, not 1; "
                             "at d = i the repricing term is supposed to "
                             "vanish exactly and §2.1 reads it that way")
    # d < i: above one, and **rising in n**, which is the term-extension
    # channel the whole section exists to separate out
    ks = [_k(6.5, 3.0, n_) for n_ in (60.0, 120.0, 240.0, 360.0)]
    if not all(x > 1.0 for x in ks):
        fails.append(f"k at d < i came back {ks}, not above one; §2.1's "
                     "mechanical channel does not exist as described")
    if not all(b > a for a, b in zip(ks, ks[1:])):
        fails.append(f"k at d < i is not increasing in n: {ks}. §2.1 reads a "
                     "positive `term` column as the discount rate sitting "
                     "below the note rate, and that reading needs this")
    # and the sign must reverse above the note rate, or the column is not
    # measuring what it is named after
    ks_hi = [_k(3.0, 6.5, n_) for n_ in (60.0, 240.0)]
    if not all(x < 1.0 for x in ks_hi) or ks_hi[1] >= ks_hi[0]:
        fails.append(f"k at d > i came back {ks_hi}; it should fall below one "
                     "and keep falling, so `term` carries a sign rather than "
                     "always pointing the same way")

    # -- the sub-channels, on hand-built numbers -------------------------
    # **`rate` and `term` cannot be pinned on the fixture.** Both are
    # differences from the same base and `cross` is whatever is left, so a
    # `rate` that computed the entire repricing, and a `rate` that computed
    # identically zero, both still add up. A mutation run confirmed it: three
    # errors in this sub-split survived every check that went through a core
    # table. They are the two columns §2.1's reading turns on, so they are
    # driven here directly with the answer known in advance.
    one = np.ones(1)

    def _t(i_n, i_p, n_n, n_h, dd, leg2=0.0):
        return leg2_terms(one * i_n, one * i_p, one * n_n, one * n_h,
                          one * dd, one * 100.0, one * 100.0, one * leg2)

    # (a) nothing moves: every repricing term is exactly zero
    z = _t(6.0, 6.0, 240.0, 240.0, 6.0)
    for f_ in ("l2_repricing", "l2_rate", "l2_term"):
        if abs(float(z[f_][0])) > 1e-12:
            fails.append(f"{f_} = {float(z[f_][0]):.3e} with the contract "
                         "unchanged and d = i; it must be exactly zero")
    # (b) the rate moves alone: `term` is zero and `rate` IS the repricing
    a = _t(4.0, 6.0, 240.0, 240.0, 3.0)
    if abs(float(a["l2_term"][0])) > 1e-12:
        fails.append(f"`term` = {float(a['l2_term'][0]):.3e} on a loop whose "
                     "remaining term did not move; it is reading the rate")
    if abs(float(a["l2_rate"][0] - a["l2_repricing"][0])) > 1e-12:
        fails.append("with only the rate moving, `rate` does not equal the "
                     f"repricing ({float(a['l2_rate'][0]):.4e} vs "
                     f"{float(a['l2_repricing'][0]):.4e})")
    if abs(float(a["l2_rate"][0])) < 1e-6:
        fails.append("`rate` came back ~zero while the note rate moved two "
                     "points; the channel is dead")
    # (c) the term moves alone: `rate` is zero and `term` IS the repricing
    b = _t(6.0, 6.0, 360.0, 240.0, 3.0)
    if abs(float(b["l2_rate"][0])) > 1e-12:
        fails.append(f"`rate` = {float(b['l2_rate'][0]):.3e} on a loop whose "
                     "note rate did not move; it is reading the term")
    if abs(float(b["l2_term"][0] - b["l2_repricing"][0])) > 1e-12:
        fails.append("with only the term moving, `term` does not equal the "
                     f"repricing ({float(b['l2_term'][0]):.4e} vs "
                     f"{float(b['l2_repricing'][0]):.4e})")
    # **and its sign is the claim §2.1 makes.** d below the note rate, term
    # extended: positive. Above the note rate: negative. If this does not
    # reverse, the column is not measuring the channel it is named after.
    if not float(b["l2_term"][0]) > 0:
        fails.append(f"extending the term at d < i gave `term` = "
                     f"{float(b['l2_term'][0]):.4e}; §2.1 reads a positive "
                     "`term` as exactly this and the sign does not appear")
    b_hi = _t(3.0, 3.0, 360.0, 240.0, 6.0)
    if not float(b_hi["l2_term"][0]) < 0:
        fails.append(f"extending the term at d > i gave `term` = "
                     f"{float(b_hi['l2_term'][0]):.4e}; the column does not "
                     "carry a sign, so a positive reading means nothing")
    # (d) both move: neither channel is zero, and the three still close
    ab = _t(4.0, 6.0, 360.0, 240.0, 3.0)
    cross = float(ab["l2_repricing"][0] - ab["l2_rate"][0]
                  - ab["l2_term"][0])
    if abs(float(ab["l2_rate"][0])) < 1e-6 or abs(float(ab["l2_term"][0])) < 1e-6:
        fails.append("a loan with both terms moving reported a dead channel: "
                     f"rate {float(ab['l2_rate'][0]):.4e}, term "
                     f"{float(ab['l2_term'][0]):.4e}")
    if not abs(cross) > 1e-9:
        fails.append("the interaction is zero to floating point on a loan "
                     "where both terms moved; `cross` is then decoration and "
                     "printing it says nothing")
    # (e) the balance term is the whole of leg 2 when nothing else moves
    bb = leg2_terms(one * 6.0, one * 6.0, one * 240.0, one * 240.0, one * 6.0,
                    one * 110.0, one * 100.0, one * np.log(1.1))
    if abs(float(bb["l2_balance"][0] - np.log(1.1))) > 1e-12:
        fails.append("`balance` is not log(B_now / B_hat)")
    if abs(float(bb["l2_balloon"][0])) > 1e-12:
        fails.append(f"the remainder is {float(bb['l2_balloon'][0]):.3e} on a "
                     "loop whose leg 2 is exactly the balance term")
    # **and the remainder must be able to be non-zero, at a known value.**
    # With `d = i` and no term move the repricing is exactly zero and the
    # balance is `log(1.1)`, so anything else in leg 2 lands in the balloon
    # and nowhere else. Without this a balloon hardcoded to zero passes every
    # other check in this file, which is what a mutation run found.
    bl = leg2_terms(one * 6.0, one * 6.0, one * 240.0, one * 240.0, one * 6.0,
                    one * 110.0, one * 100.0, one * (np.log(1.1) + 0.25))
    if abs(float(bl["l2_balloon"][0]) - 0.25) > 1e-12:
        fails.append(f"the remainder came back {float(bl['l2_balloon'][0]):.6f}"
                     " where the two named terms leave exactly 0.25 of leg 2 "
                     "unexplained; it is not `leg2 - balance - repricing`")

    # -- leg 1's closed form, against `loop_residual_ideal` ---------------
    # **Anchored to the function B8-0a already gates on**, not written twice
    # from the same derivation. `loop_residual_ideal` factors into `k` flat
    # delinquent months plus one cure month, so subtracting the per-month
    # expression `k` times must leave exactly the cure month.
    for B0, i_, P_, k_n in ((200000.0, 6.0, 1200.0, 1),
                            (200000.0, 6.0, 1200.0, 5),
                            (43000.0, 9.5, 410.0, 3),
                            (990000.0, 3.25, 4300.0, 11)):
        f0 = B0 * (1.0 + i_ / 1200.0) - P_
        per = np.log(B0) - np.log(f0)
        b = B0
        for _ in range(k_n + 1):
            b = b * (1.0 + i_ / 1200.0) - P_
        cure = np.log(b) - np.log(f0)
        whole = float(W.loop_residual_ideal(B0, i_, P_, k_n))
        if abs(whole - (k_n * per + cure)) > 1e-12:
            fails.append(f"leg 1's per-month expression does not add up to "
                         f"`loop_residual_ideal` at k={k_n}: {whole:.12e} vs "
                         f"{k_n * per + cure:.12e}")
    # k = 0 is no missed month, so no loop and no residual. Both halves of the
    # split have to vanish there, and they do so for different reasons: leg 1
    # because it has no months, the cure month because `f^1 == f`.
    if abs(float(W.loop_residual_ideal(200000.0, 6.0, 1200.0, 0))) > 1e-15:
        fails.append("`loop_residual_ideal` is non-zero with no missed month, "
                     "so the split into leg 1 and a cure month is anchored to "
                     "something that does not reduce")

    # **and on the fixture's modification arm the measured leg 1 must equal
    # it**, because the fixture builds flat delinquent runs on purpose. This
    # is the check that fails if the derivation is right and the wiring is
    # wrong, which is the pairing pit 39 asks for.
    l1c = np.asarray(got["sig"]["l1_closed"])
    l1m = np.asarray(got["sig"]["leg1"])
    n1v = np.asarray(got["sig"]["n1"])
    sel = (np.asarray(got["sig"]["arm"]) == L.ARM_MOD) \
        & np.asarray(got["sig"]["measurable"]) & np.isfinite(l1c) & (n1v > 0)
    if int(sel.sum()) == 0:
        fails.append("no measurable modification loop on the fixture has a "
                     "non-empty leg 1, so the closed form is untested")
    else:
        gap = float(np.max(np.abs(l1m[sel] - l1c[sel])))
        if gap > 1e-9:
            fails.append(f"leg 1 differs from its closed form by {gap:.3e} on "
                         "the fixture, whose delinquent runs are flat by "
                         "construction; either the derivation or the wiring "
                         "is wrong")
        if float(np.max(np.abs(l1c[sel]))) < 1e-12:
            fails.append("every fixture leg 1 closed form is zero, so the "
                         "comparison above passes on nothing")

    # -- the decomposition closes ----------------------------------------
    # **The only non-tautological check on it.** `l2_balloon` is defined as
    # the residual, so `balance + repricing + balloon == leg2` proves nothing.
    # What can fail is the residual being large where the model says it must
    # be zero: on a loop carrying no zero-interest balance at `t_M` or the
    # month before, `V = B * k` exactly and the remainder has nothing left in
    # it. Field 64 is identically zero on these archives.
    with K.Core(zp.stem, cols=Z8.COLS + ["zero_bal"], cache_root=cr) as c3:
        _bal_c, zib_c = K.zero_interest_split(c3)
        q3 = K.quiet_pairs(c3)
        pid3 = W.contract_periods(c3, fill=True)
        pay3, _k3, _p3 = W.contract_payments(c3, pid3, q3)
        disc3, _ = W.disc_of_row(c3, pos, tab)
        r3, ok3, _ = W.row_residuals(c3, disc3)
        lp3 = L.find_loops(c3)
        sig3 = Z8.loop_sums(lp3, r3, ok3)
        sp3 = leg2_split(c3, lp3, disc3, pay3, sig3["leg2"], ok3)
        tM3 = lp3["t_M"]
        flat = (zib_c[tM3] == 0) & (zib_c[tM3 - 1] == 0)
    closes = flat & sp3["l2_ok"] & sig3["measurable"]
    if int(closes.sum()) == 0:
        fails.append("no fixture loop is free of a zero-interest balance at "
                     "`t_M`, so the decomposition's closure is untested")
    else:
        worst = float(np.max(np.abs(sp3["l2_balloon"][closes])))
        if worst > 1e-9:
            fails.append(f"on a loop with no balloon the remainder is {worst:.3e}"
                         ", not zero. `V = B * k` does not hold there and the "
                         "split into balance and repricing is wrong")
    # **and the masking, forced rather than hoped for.** `loop_sums` writes
    # `0.0` into `leg2` on a month it could not read, so subtracting two
    # finite terms from that zero prints a large invented balloon on exactly
    # the loops that were dropped. Whether the fixture happens to contain such
    # a month is not something to depend on, so one is made.
    if tM3.size:
        with K.Core(zp.stem, cols=Z8.COLS + ["zero_bal"], cache_root=cr) as c5:
            ok_x = np.asarray(ok3).copy()
            ok_x[tM3[0]] = False
            sig_x = Z8.loop_sums(lp3, r3, ok_x)
            sp_x = leg2_split(c5, lp3, disc3, pay3, sig_x["leg2"], ok_x)
        if np.isfinite(sp_x["l2_balloon"][0]) or sp_x["l2_ok"][0]:
            fails.append("a loop whose `t_M` residual was made unreadable "
                         "still reported a balloon; `leg2` is 0.0 there and "
                         "the subtraction invents a number")
        if not np.isfinite(sp3["l2_balloon"][0]):
            fails.append("that loop had no readable balloon to begin with, so "
                         "the mask test above cannot tell masking from a "
                         "missing value")

    # -- `rate` and `term` are individually pinned ------------------------
    # Both are differences from the same base, so a copy-paste that made them
    # identical would still add up. Each must vanish when its own contract
    # term does not move.
    n_l = tM3.size
    with K.Core(zp.stem, cols=Z8.COLS + ["zero_bal"], cache_root=cr) as c4:
        rr = c4.row["rate"][:].astype(np.float64) / 1000.0
        nn = c4.row["rem_legal"][:].astype(np.float64)
        same_rate = (rr[tM3] == rr[tM3 - 1]) & sp3["l2_ok"]
        same_term = (nn[tM3] == nn[tM3 - 1] - 1.0) & sp3["l2_ok"]
    if int(same_rate.sum()) and np.nanmax(
            np.abs(sp3["l2_rate"][same_rate])) > 1e-12:
        fails.append("`rate` is non-zero on a loop whose note rate did not "
                     "move; it is not the rate channel")
    if int(same_term.sum()) and np.nanmax(
            np.abs(sp3["l2_term"][same_term])) > 1e-12:
        fails.append("`term` is non-zero on a loop whose remaining term ran "
                     "down by exactly one month; it is not the term channel")
    if int(same_rate.sum()) == 0 and int(same_term.sum()) == 0:
        fails.append("no fixture loop holds either contract term fixed across "
                     f"`t_M` ({n_l} loops), so neither channel is pinned")

    # a stale tag must raise rather than serve
    p = _path(zp.stem, cache_root)
    with np.load(p, allow_pickle=False) as z:
        flat = {k_: z[k_] for k_ in z.files}
    meta = json.loads(bytes(flat["meta__json"]).decode("utf-8"))
    meta["tag"] = "0" * 16
    flat["meta__json"] = np.frombuffer(json.dumps(meta).encode("utf-8"),
                                       dtype=np.uint8)
    np.savez_compressed(p, **flat)
    try:
        load(zp.stem, cache_root=cache_root)
    except ValueError:
        pass
    else:
        fails.append("a cache entry with a foreign tag loaded without "
                     "complaint; staleness is not checked")
    # `get` must rebuild rather than fail
    again = get(zp.stem, cache_root=cache_root, pos=pos, tab=tab,
                core_root=cr)
    if not np.array_equal(np.asarray(again["sig"]["omega"]),
                          np.asarray(built["sig"]["omega"]), equal_nan=True):
        fails.append("`get` rebuilt to different numbers than `build`")

    print(f"  cache: {got['sig']['omega'].size} loops, "
          f"{p.stat().st_size / 1e3:.1f} kB, tag {t0}", file=sys.stderr)

    for m in fails:
        print("FAIL " + m, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the cache reproduces the direct computation and a "
          "foreign tag refuses to load", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command",
                    choices=["build", "status", "verify", "selftest"])
    ap.add_argument("--only", action="append", default=None)
    ap.add_argument("--force", action="store_true")
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

    if args.command == "status":
        raise SystemExit(cmd_status(names))
    if args.command == "verify":
        raise SystemExit(cmd_verify(names))

    pos, tab = Z8.curve_table()
    for n in names:
        if not args.force:
            try:
                load(n)
                print(f"  {n}: cached, skipping", file=sys.stderr)
                continue
            except (FileNotFoundError, ValueError):
                pass
        print(f"building {n}", file=sys.stderr)
        o = build(n, pos=pos, tab=tab)
        print(f"  {n}: {o['sig']['omega'].size:,} loops, "
              f"{o['floor']['omega'].size:,} clean cures, "
              f"{_path(n).stat().st_size / 1e6:.1f} MB", file=sys.stderr)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
