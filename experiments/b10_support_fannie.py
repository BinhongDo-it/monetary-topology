"""B10: the same `b1` curve on Fannie, because the Freddie one may not be moved.

Registered in the B10 availability register §16, and §16.9 rule 4 of that
registration is the reason this file exists:

    不得把 Freddie 的 `b₁` 搬到 Fannie。两家的报送实践不同。

That rule was written by the same author as the Freddie run, before it. So the
transfer function `b8_fannie_slice.md` §3.3 needs, for the two `q` grids it
**enforces on its own carrier**, does not exist until this file runs. The
repository's only `b1` figures for Fannie are §2.1's ``3 - 3 + 1 = 1`` and
§14.4's ``5 - 4 + 1 = 2``, and both are assertions about a-priori graphs.

Nothing here touches `omega`
----------------------------
Four columns are read: ``delinq``, ``mod_flag``, the deferral column, and
``period``. No
balance, no rate, no payment, no amortisation. This file cannot move a B8
prediction and does not try to.

Two things are taken from elsewhere rather than re-implemented
---------------------------------------------------------------
* **The graph arithmetic is imported from ``b10_support``**, so ``betti``, the
  grid functions, the support ladder and the ``b1_walkable <= b1_undirected``
  invariant are the *same code* on both carriers. A difference between the two
  runs therefore cannot come from the grids. That is the whole point of a
  transfer function and it would be lost by writing a second copy.
* **The intake is B8's core table** (``b8_core.Core``), whose ``quiet_pairs``
  reproduced the hand-written control filter bit for bit on 170 million rows
  (the B8 inputs register §6.2.6.1). Field positions are the ones C0b
  earned by behaviour.

Where the two carriers necessarily differ, and it is declared
--------------------------------------------------------------
* ``modified``: Freddie field 8 reads ``Y`` in the event month. Fannie field 42
  reads ``Y`` in the event month too and then reverts on three quarters of loans
  (`b8_fannie_slice.md` §13.1). **This file uses the event month on both**, so
  the reversion does not bite.
* ``deferred``: Freddie field 25 flags the month. Fannie has no such flag and
  the repository holds **two** candidate columns, which C8-6 has already ruled
  are different quantities (*108 与 63 不是同一个量，须分别读*). ``b8_omega.py``
  splits segments on a rising edge of positive **field 63**; C8-6 confirms
  **field 108** is what describes deferral. Measured rising edges here: 2012Q1
  **267 on 63 against 4,882 on 108**, 2019Q1 **1,124 against 14,777**, a factor
  of thirteen to eighteen. **This file defaults to 108 and takes the column as a
  parameter**, so the choice is in the output rather than in a constant. Whether
  a field-108 onset moves the payment, and therefore whether ``b8_omega.py``'s
  boundary set is complete, is a question for B8 and is not decided here.
* Fannie's delinquency field has **no ``RA``**. Freddie carries REO Acquisition
  as a value of the status field; Fannie encodes it in the zero-balance code
  (field 44) instead, so Fannie's ``g1`` and ``g2`` have one vertex fewer **by
  the file's design and not by a grid choice**. Declared because a vertex count
  that differs for that reason is not a transfer-function reading.
* The delinquency sentinels differ. ``b8_core.as_delinq`` maps ``XX`` and
  anything unrecognised to 254, blank to 255, and an off-convention digit string
  to 253. **What they are and whether they behave like Freddie's ``XX`` is a
  question for ``--depth``, not an assumption here.**

One thing this file fixes that the Freddie one did not do
----------------------------------------------------------
``b10_support.transitions`` paired **adjacent rows** without checking they are
**adjacent months**. On Freddie that cost 174 pairs out of 72.2 million
(`§18.0`), so nothing moved, but it was still a gap. **This file requires
``period[i+1] == period[i] + 1``** and prints how many pairs that removes.

Usage::

    python experiments/b10_support_fannie.py --depth
    python experiments/b10_support_fannie.py --run

Writes ``results/b10_support_fannie_depth.json`` /
``results/b10_support_fannie.json``, both ``diagnostic_only``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b8_core  # noqa: E402
import b10_support as fr  # noqa: E402

RESULTS = ROOT / "results"

ARCHIVES = ("2002Q1", "2006Q1", "2007Q1", "2012Q1", "2017Q1", "2019Q1")

#: `b8_core.as_delinq`'s sentinels, named rather than left as bare integers.
SENTINEL = {253: "ODD253", 254: "XX254", 255: "BLANK255"}

_Y = ord("Y")


#: Which column marks a deferral onset. **A parameter, not a constant**, because
#: the repository holds two candidates and has already ruled they are different
#: quantities: the B8 inputs register C8-6, *108 与 63 不是同一个量，须分别读*.
#: Field 108 `defer_amt` is what C8-6 confirms describes deferral and is the
#: default here. Field 63 `nib_upb` is what `b8_omega.py` splits segments on.
#: Measured rising edges, this file's own probe: 2012Q1 **267 on 63 against
#: 4,882 on 108**, 2019Q1 **1,124 against 14,777**. `--depth` prints both so the
#: choice is auditable rather than buried.
DEFER_COLS = ("defer_amt", "nib_upb")


def states_of(c, defer_col: str = "defer_amt") -> tuple[np.ndarray, list[str]]:
    """Per-row raw state, as a code array plus the code-to-label table.

    Precedence is `§16.11`'s, unchanged: ``modified`` if the modification flag
    reads ``Y`` this month, else ``deferred`` on a rising edge of a positive
    deferral balance, else the delinquency field.
    """
    delinq = np.asarray(c.row["delinq"])
    mod = np.asarray(c.row["mod_flag"])
    nib = np.asarray(c.row[defer_col])

    # **The sentinel guard, and it is not optional.** `b8_core.as_cents` maps a
    # blank field to `U32_NA`, not to zero, so `nib > 0` is true on every blank
    # row. `b8_core.py` line 548 writes B8's own use of this column as
    # `(nib != U32_NA) & (nib > 0)`; the first version of this file wrote
    # `nib > 0` and fired the deferral edge on 2.94 million rows, about one per
    # loan, against `§6.3.3`'s measured 99.6% of rows being zero or blank.
    # Caught by `--depth`, before any `b1` was computed.
    nib_pos = (nib != b8_core.U32_NA) & (nib > 0)

    first = np.zeros(c.n_rows, dtype=bool)
    first[np.asarray(c.row_start, dtype=np.int64)] = True
    prev_pos = np.zeros(c.n_rows, dtype=bool)
    prev_pos[1:] = nib_pos[:-1]
    prev_pos[first] = False
    defer_edge = nib_pos & ~prev_pos

    labels = [f"{i:02d}" for i in range(99)]          # codes 0..98
    labels += [SENTINEL[253], SENTINEL[254], SENTINEL[255]]   # 99, 100, 101
    labels += ["modified", "deferred"]                        # 102, 103
    code = np.empty(c.n_rows, dtype=np.int16)
    code[:] = delinq
    code[delinq == 253] = 99
    code[delinq == 254] = 100
    code[delinq == 255] = 101
    code[defer_edge] = 103
    code[mod == _Y] = 102
    return code, labels


def pair_counts(archive: str, drops: Counter,
                defer_col: str = "defer_amt") -> Counter:
    """Ordered raw-state pairs over **consecutive months of one loan**."""
    with b8_core.Core(archive,
                      cols=["delinq", "mod_flag", defer_col, "period"]) as c:
        code, labels = states_of(c, defer_col)
        period = np.asarray(c.row["period"]).astype(np.int64)

        last = np.zeros(c.n_rows, dtype=bool)
        ends = np.asarray(c.row_start, dtype=np.int64) + \
            np.asarray(c.n_per_loan, dtype=np.int64) - 1
        last[ends] = True

        same_loan = ~last[:-1]
        adjacent = period[1:] == period[:-1] + 1
        drops[f"{archive}:pairs_same_loan"] += int(same_loan.sum())
        drops[f"{archive}:dropped_month_gap"] += int((same_loan & ~adjacent).sum())

        ok = same_loan & adjacent
        a = code[:-1][ok].astype(np.int64)
        b = code[1:][ok].astype(np.int64)
        n_lab = len(labels)
        flat = np.bincount(a * n_lab + b, minlength=n_lab * n_lab)
        nz = np.flatnonzero(flat)
        return Counter({(labels[i // n_lab], labels[i % n_lab]): int(flat[i])
                        for i in nz})


def cmd_depth(only, defer_col) -> int:
    names = only or list(ARCHIVES)
    print("b10_support_fannie depth. Enumerates. Computes no b1.\n")
    total, drops = Counter(), Counter()
    for a in names:
        try:
            t = pair_counts(a, drops, defer_col)
        except FileNotFoundError as e:
            print(f"  {a}: {e}")
            continue
        total.update(t)
        print(f"  {a}  pairs {sum(t.values()):>12,}  distinct {len(t):>7,}")

    states = sorted({x for e in total for x in e})
    print(f"\n  raw states observed: {len(states)}")
    print("  " + " ".join(states))

    self_n = sum(n for (u, v) in total for n in [total[(u, v)]] if u == v)
    tot = sum(total.values())
    print(f"\n  ordered pairs {tot:,} over {len(total):,} distinct; "
          f"self-loops {self_n:,} ({self_n / tot:.4f})")
    print("\n  month-gap pairs removed, per archive "
          "(the check the Freddie run did not have):")
    for k, v in sorted(drops.items()):
        if k.endswith("dropped_month_gap"):
            same = drops[k.replace("dropped_month_gap", "pairs_same_loan")]
            print(f"    {k.split(':')[0]:<8} {v:>10,} of {same:>13,} "
                  f"({v / same:.6f})")

    print("\n  the two deferral-column candidates, rising edges per archive:")
    print(f"    {'archive':>9}{'defer_amt(108)':>16}{'nib_upb(63)':>14}")
    for a in names:
        try:
            with b8_core.Core(a, cols=list(DEFER_COLS)) as c:
                fst = np.zeros(c.n_rows, dtype=bool)
                fst[np.asarray(c.row_start, dtype=np.int64)] = True
                cnt = []
                for col in DEFER_COLS:
                    v = np.asarray(c.row[col])
                    pos = (v != b8_core.U32_NA) & (v > 0)
                    pv = np.zeros(c.n_rows, dtype=bool)
                    pv[1:] = pos[:-1]
                    pv[fst] = False
                    cnt.append(int((pos & ~pv).sum()))
                print(f"    {a:>9}{cnt[0]:>16,}{cnt[1]:>14,}")
        except FileNotFoundError:
            pass
    print("    C8-6 ruled these are different quantities. This run used "
          f"**{defer_col}**.")

    print("\n  the sentinels, and how they behave:")
    for s in (SENTINEL[253], SENTINEL[254], SENTINEL[255]):
        ins = [(u, n) for (u, v), n in total.items() if v == s and u != s]
        outs = [(v, n) for (u, v), n in total.items() if u == s and v != s]
        print(f"    {s:<9} in-edges {len(ins):>3} ({sum(n for _, n in ins):>9,})"
              f"   out-edges {len(outs):>3} ({sum(n for _, n in outs):>9,})"
              f"   self {total[(s, s)]:>10,}")
    print("    Read: Freddie's XX had zero in-edges, which is what made it a "
          "first-month\n    artefact rather than a state (§16.12.4). Whether "
          "these behave the same way\n    is decided here and not assumed.")

    print("\n  the twenty commonest transitions:")
    for (u, v), n in total.most_common(20):
        print(f"    {u:>9} -> {v:<9} {n:>13,}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_support_fannie_depth.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "support_fannie_depth", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §16. It measures a "
             "cycle-space capacity on B8's carrier and carries no omega or "
             "holonomy claim (§16.0).",
         "archives": names, "raw_states": states, "defer_col": defer_col,
         "total_pairs": tot, "distinct_pairs": len(total),
         "self_loop_pairs": self_n,
         "matrix": {f"{u}->{v}": n for (u, v), n in sorted(total.items())},
         "drops": dict(sorted(drops.items()))},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_run(only, drop_states, defer_col) -> int:
    names = only or list(ARCHIVES)
    print("b10_support_fannie run. Same grids, same ladder, same betti as the "
          "Freddie run.\n")
    total, drops = Counter(), Counter()
    per_archive = {}
    for a in names:
        try:
            t = pair_counts(a, drops, defer_col)
        except FileNotFoundError as e:
            print(f"  {a}: {e}")
            continue
        per_archive[a] = t
        total.update(t)

    out_grids = {}
    for gname, gf in fr.GRIDS:
        # **Both variants, always.** The drop set is a judgement about what is a
        # servicing position and what is a not-available code, and a judgement
        # that changes a number belongs beside the number. This is the same
        # device as the Freddie run's XX correction: the effect is shown, not
        # asserted, and a reader who disagrees with the drop can read the other
        # column instead of re-running.
        keep, dropped = fr.project(total, gf, drop_states=drop_states)
        whole, _ = fr.project(total, gf, drop_states=())
        rows = []
        print(f"\n  grid {gname}   (pairs dropped for {drop_states or '()'}: "
              f"{dropped:,})")
        print(f"    {'cut':>10}{'V':>5}{'E_und':>7}{'c':>4}{'b1_und':>8}"
              f"{'b1_walk':>9}{'SCC':>5}   |{'b1_und all':>12}{'b1_walk all':>13}")
        for cut in fr.SUPPORT_CUTS:
            r, w = fr.betti(keep, cut), fr.betti(whole, cut)
            r["b1_undirected_no_drop"] = w["b1_undirected"]
            r["b1_walkable_no_drop"] = w["b1_walkable"]
            rows.append(r)
            print(f"    {r['cut']:>10,}{r['V']:>5}{r['E_undirected']:>7}"
                  f"{r['c']:>4}{r['b1_undirected']:>8}{r['b1_walkable']:>9}"
                  f"{r['n_scc']:>5}   |{w['b1_undirected']:>12}"
                  f"{w['b1_walkable']:>13}")
        out_grids[gname] = rows

    print("\n  per archive, grid g1, cut 100:")
    print(f"    {'archive':>9}{'V':>5}{'E_und':>7}{'b1_und':>8}{'b1_walk':>9}")
    per_a = {}
    for a, t in sorted(per_archive.items()):
        pr, _ = fr.project(t, fr.g1, drop_states=drop_states)
        r = fr.betti(pr, 100)
        per_a[a] = r
        print(f"    {a:>9}{r['V']:>5}{r['E_undirected']:>7}"
              f"{r['b1_undirected']:>8}{r['b1_walkable']:>9}")

    print("\n  Read against the Freddie run's §17, which is the point of this "
          "file:\n"
          "    the two carriers' g0m -> g1 -> g2 -> g3 chains are the transfer\n"
          "    function discipline 11's third family asks for, one per carrier.\n"
          "    §16.9 rule 4 still forbids quoting one for the other; what is now\n"
          "    possible is quoting both and saying whether they agree.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_support_fannie.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "support_fannie", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §16. It measures a "
             "cycle-space capacity on B8's carrier and carries no omega or "
             "holonomy claim (§16.0).",
         "archives": names, "drop_states": list(drop_states),
         "defer_col": defer_col,
         "support_cuts": list(fr.SUPPORT_CUTS), "grids": out_grids,
         "per_archive_g1_cut100": per_a,
         "drops": dict(sorted(drops.items()))},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--depth", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", action="append")
    ap.add_argument("--defer-col", choices=DEFER_COLS, default="defer_amt",
                    dest="defer_col",
                    help="column whose rising edge marks a deferral onset. "
                         "C8-6 ruled 108 and 63 are different quantities, so "
                         "this is a choice and it is recorded in the output")
    ap.add_argument("--drop", action="append",
                    help="raw state to exclude in --run; decided from --depth, "
                         "not assumed. Repeatable.")
    a = ap.parse_args(argv)
    if a.depth:
        return cmd_depth(a.only, a.defer_col)
    if a.run:
        return cmd_run(a.only, tuple(a.drop or ()), a.defer_col)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
