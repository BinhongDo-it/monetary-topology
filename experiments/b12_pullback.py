"""B12: is a holonomy reading an artefact of how the states were cut.

The question this station answers, and why it needs a different instrument
---------------------------------------------------------------------------
Every holonomy reading in this repository carries one caveat, written at the
top of the ETF station's own register: *a non-zero reading elsewhere cannot be
distinguished from an artefact of how states were cut*. That station is immune
to it because its three positions are institutional objects with no grid to
choose, and that immunity is the same fact as its inability to supply a
calibration. So the caveat can only be answered on a carrier that has a grid to
choose, which means this family.

It was attacked once with a between-class-over-within-class spread and the
verdict was that the ruler cannot measure it: not "the cut does not set the
reading", not "the cut sets the reading", but that the statistic has no zero it
is obliged to predict, so a sign flip between vintages is unreadable.

**This file changes the ruler to one that predicts an exact zero.**

Coarsening is a graph map ``f : G_fine -> G_coarse``. If ``omega`` is pulled
back from the coarse grid, that is, if there is an ``omega_coarse`` with
``omega = f*(omega_coarse)``, then

    every fine cycle whose image under ``f`` is trivial must sum to exactly
    zero,

because a pullback preserves loop sums and a trivial loop sums to zero. That is
a prohibition, not a fit: the framework is made to say *there shall be nothing
here* before anything is measured, and then the there is inspected. Both
outcomes are reachable and both are written down before the run.

What is in this file today
--------------------------
**The two gates only.** Nothing is estimated here. The gates are

* ``B12-0a`` the layers of ``f`` against the window length ``L = t_B - t_A``,
  because on the finest grid a cycle class is very nearly the window length and
  ``omega`` is a sum over that window, so a batch confined to one ``L`` band is
  reporting arithmetic and not the cut;
* ``B12-0b`` recomputing the cycle class counts on the vintage the ladder was
  read on, which must reproduce ``503 / 41 / 2 / 0`` on the deferral arm and
  ``431 / 25 / 2 / 0`` on the modification arm, exactly. **One cycle off and
  this station does not open.**

``B12-0b`` is this station's only construction check and it is one that can
really fail, which is the property the ``-x + x`` self-tests of a neighbouring
station lacked. Three things can break it. The shared modules underneath
(``b8_core``, ``b8_loops``, ``b8_omega``, ``b8_loop_omega``, ``b10_support``)
have all been edited since the archived record was written. The walk here is
assembled once in raw labels and pushed down the ladder by relabelling, where
the archived run re-mapped the raw row sequence separately at every grid. And
the two agree only if free reduction commutes with merging labels, which is the
premise the pullback test rests on and is therefore checked on the data rather
than asserted.

The limit that must travel with ``B12-0b``: those two count vectors are from a
**single vintage**, while the ladder's ``b1`` row is six vintages unioned at a
support threshold of 100. On this vintage alone the middle grid's ``b1`` reads
7, not 9. **This gate compares class counts, not ``b1``.**

Three numbers are fixed before the run and none of them is this file's
------------------------------------------------------------------------
``N``      the instrument floor, the median absolute deviation of
           ``omega - closed`` measured by the floor station, per vintage.
``SIGNAL_OVER_NOISE``  4.0, the value the previous grid station used on itself.
``MIN_CYCLES``  the project-wide small-cell floor, imported rather than copied
           so that it is the same object and not a number that can drift.

None of the three is used by the gates. They are declared here because the
verdict thresholds must exist before the estimate does, and ``--gate`` prints
their provenance so a transcription error surfaces now rather than later.

Usage::

    python experiments/b12_pullback.py --gate

**The gate writes no file.** It only prints, and it is meant to be read before
anything else is run. ``--run`` and ``--placebo`` are the estimation steps and
are not built yet.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b8_core as K            # noqa: E402
import b8_loops as L           # noqa: E402
import b8_omega as W           # noqa: E402
import b8_loop_omega as LO     # noqa: E402
import b10_support as fr       # noqa: E402
import b10_support_fannie as bf  # noqa: E402

#: **The free reduction machine is imported, not rewritten.** It is the one
#: piece of the neighbouring ladder this station reuses verbatim, because a
#: second implementation of a normal form is a second thing that can be wrong
#: while agreeing with itself.
from b10_holonomy_ladder import is_cycle, reduce_closed_walk  # noqa: E402

#: The floor station itself, imported rather than reimplemented, because `N`
#: is explicitly not this station's number. `--floor` uses its clean-cure
#: population, its column list and its scale estimator unchanged.
import b8_0b_floor as FL     # noqa: E402
import b8_0a_gate as G       # noqa: E402

#: The project-wide floor on how many observations a cell needs. Imported from
#: the module that defines it so that this file cannot hold a stale copy. It is
#: used here as the floor on how many cycles a pair of grids needs before its
#: reading is reported at all.
from monetary_topology.effective_price import (  # noqa: E402
    MIN_CELL_SIZE as MIN_CYCLES,
)

RESULTS = ROOT / "results"

#: The rungs, and the adjacent pairs that give the coarsening maps. `g0` is not
#: on the ladder: it carries neither `modified` nor `deferred`, so a loop has no
#: image in it.
LADDER = ("g0m", "g1", "g2", "g3")
PAIRS = tuple(zip(LADDER, LADDER[1:]))

#: The vintage the archived ladder was read on, and the counts it returned.
#: Reproducing these is `B12-0b`. **Exact equality, no tolerance.**
GATE_ARCHIVE = "2019Q1"
TARGET_CLASSES = {"defer": (503, 41, 2, 0), "mod": (431, 25, 2, 0)}

#: The instrument floor, per vintage: the median absolute deviation of
#: `omega - closed`, from the floor station's own table. **Measured elsewhere,
#: transcribed here.** `--gate` re-reads that table and prints the comparison,
#: so a typo in this dict is caught by the run and not by a reader.
FLOOR_SOURCE = RESULTS / "b8_0b_floor.md"
FLOOR = {
    "2002Q1": 5.2162e-08,
    "2006Q1": 3.5436e-08,
    "2007Q1": 3.3663e-08,
    "2012Q1": 3.2822e-08,
    "2017Q1": 2.6950e-08,
    "2019Q1": 2.6803e-08,
}

#: The ratio at which a batch is called separated from the floor. Taken from the
#: previous grid station, which used it on itself. Not chosen here.
SIGNAL_OVER_NOISE = 4.0

#: Printed caps. Every cap in this file prints what it dropped, because a silent
#: truncation reads as coverage.
MAX_CLASS_ROWS = 12
MAX_L_ROWS = 20


# ---------------------------------------------------------------------------
# provenance of the three fixed numbers
# ---------------------------------------------------------------------------

def floor_from_source() -> dict:
    """Re-read the floor table rather than trust the dict above.

    The row shape is nine cells with the correlation column carrying a sign, and
    the sixth cell bolded. Anything else is not that row and is skipped.
    """
    if not FLOOR_SOURCE.exists():
        return {}
    got = {}
    for line in FLOOR_SOURCE.read_text(encoding="utf-8").splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) != 9:
            continue
        if cells[0] not in FLOOR or not cells[4].startswith(("+", "-")):
            continue
        m = re.fullmatch(r"\*\*([0-9.]+e-[0-9]+)\*\*", cells[5])
        if m:
            got[cells[0]] = float(m.group(1))
    return got


def print_constants() -> int:
    print("  the three numbers, and where each came from")
    print(f"    MIN_CYCLES        {MIN_CYCLES:<12}  imported from "
          "effective_price.MIN_CELL_SIZE, the project-wide small-cell floor")
    print(f"    SIGNAL_OVER_NOISE {SIGNAL_OVER_NOISE:<12}  the ratio the "
          "previous grid station used on itself")
    src = floor_from_source()
    bad = 0
    print("    N, the instrument floor, per vintage: transcribed here, "
          f"re-read from {FLOOR_SOURCE.name}")
    for a in sorted(FLOOR):
        s = src.get(a)
        if s is None:
            mark = "source row not found"
            bad += 1
        elif s == FLOOR[a]:
            mark = "matches source"
        else:
            mark = f"DISAGREES with source {s:.4e}"
            bad += 1
        print(f"      {a}  {FLOOR[a]:.4e}   {mark}")
    if bad:
        print(f"    {bad} vintage(s) not confirmed against the source table. "
              "The gates do not use N, so this does not stop the gate, but it "
              "must be settled before --run.")
    print()
    return bad


# ---------------------------------------------------------------------------
# the walk, assembled once, in raw labels
# ---------------------------------------------------------------------------

def anchor_states(c):
    """The delinquency field alone, as labels.

    The window's start vertex is the loop construction's, not the position
    graph's: the position graph gives a modification or deferral flag
    precedence over the delinquency field, which is right there and wrong at
    `t_A`, where the loop is anchored on a row reading `00` while a few hundred
    loans carry a stale flag on that same row. This is a restatement of a
    definition, not an independent derivation, and it is here rather than
    imported so that the walk assembly below is this file's from end to end.
    """
    dq = np.asarray(c.row["delinq"])
    lab = np.empty(c.n_rows, dtype=object)
    #: **The numeric range is every code below the sentinels, not the first
    #: ninety-nine.** The parser sends `00` to `98` to their integer, three
    #: named sentinels to 253, 254 and 255, and a two-digit `99` to a literal
    #: 99. A range that stops at 98 therefore leaves every literal `99` row
    #: unlabelled, which on this vintage set is 647, 2,199, 1,883, 90 and 1 rows
    #: on five archives and **zero on the sixth**. The sixth is the one the
    #: class-count reproduction is pinned to, which is why nothing caught this
    #: until a second archive was read, and why widening the range **cannot**
    #: move that reproduction: the count it changes there is zero, and the run
    #: prints it.
    lo = int(min(bf.SENTINEL))
    ok = dq < lo
    lab[ok] = np.char.zfill(dq[ok].astype(str), 2)
    for v, name in bf.SENTINEL.items():
        lab[dq == v] = name
    n_extra = int(((dq >= 99) & (dq < lo)).sum())
    missing = int(sum(1 for x in lab if x is None))
    if missing:
        raise RuntimeError(
            f"{missing} rows carry no state label. The label table and the "
            "parser's range disagree; fix the range, do not coerce.")
    anchor_states.last_beyond_98 = n_extra
    return lab


anchor_states.last_beyond_98 = 0


def raw_walks(c, lp):
    """One closed walk per loop, in raw state labels, before any grid.

    Three things the loop's own construction fixes and this file must not
    re-derive. The walk is **closed by hand**, because on almost every loop the
    event month is the last month of the window and leg three occupies no month
    at all. The **middle vertex is the loop's**, taken by index and arm from the
    loop finder, because the finder takes the onset to be the earlier of two
    fields while the state labeller reads one of them alone, and re-deriving it
    produces impossible paths. The **interior is delinquency only**, because
    the modification flag persists rather than dating an event, so reading it
    inside the window invents a class out of stale flags.
    """
    anchor = anchor_states(c)
    tA, tM, tB = lp["t_A"], lp["t_M"], lp["t_B"]
    armv = np.asarray(lp["arm"])
    vname = {L.ARM_MOD: fr.MODIFIED, L.ARM_DEFER: fr.DEFERRED}
    tally = Counter()
    out = []
    for a, m, b, ar in zip(tA.tolist(), tM.tolist(), tB.tolist(),
                           armv.tolist()):
        start = anchor[a]
        seq = list(anchor[a + 1:b + 1])
        j = m - (a + 1)
        if 0 <= j < len(seq) and ar in vname:
            seq[j] = vname[ar]
        else:
            tally["t_M_outside_window"] += 1
        out.append(tuple([start] + seq + [start]))
    return out, tally


def reduce_on_one(walk, gf):
    """One walk through one grid, reduced. Same path as `reduce_on`."""
    mapped = [gf(x) for x in walk]
    return reduce_closed_walk([x for x in mapped if x != "__drop__"])


def reduce_on(walks, gf):
    """Map every raw walk through one grid and reduce. Counts dropped states."""
    dropped = 0
    out = []
    for w in walks:
        mapped = [gf(s) for s in w]
        d = [x for x in mapped if x != "__drop__"]
        dropped += len(mapped) - len(d)
        out.append(reduce_closed_walk(d))
    return out, dropped


def vertex_map(fine_gf, coarse_gf, raw_labels):
    """`f` on vertices, derived from the two grids, plus its well-definedness.

    Both grids are functions of the raw label, so `f` is forced: it must send
    `fine(s)` to `coarse(s)` for every raw `s`. If two raw labels share a fine
    image and differ in their coarse image, `f` is not a map at all and every
    reading downstream is meaningless. The clashes are named, not counted.
    """
    f: dict = {}
    clash = []
    for s in sorted(raw_labels):
        a, b = fine_gf(s), coarse_gf(s)
        if a in f and f[a] != b:
            clash.append((s, a, f[a], b))
        else:
            f[a] = b
    return f, clash


# ---------------------------------------------------------------------------
# B12-0b
# ---------------------------------------------------------------------------

def gate_0b(red, meas, arm, walks):
    """Recompute the class counts and compare, exactly.

    Prints the whole count vector per grid per arm, not a verdict. The verdict
    line at the end is derived from the printed objects.
    """
    print(f"{'=' * 78}\n  B12-0b   cycle class counts on {GATE_ARCHIVE}, "
          "recomputed here\n" + "=" * 78)
    got = {}
    per_grid = {}
    for tag, code_ in (("defer", L.ARM_DEFER), ("mod", L.ARM_MOD)):
        sel = np.flatnonzero(meas & (arm == code_)).tolist()
        counts, cyc, cls_by_grid = [], [], {}
        for g in LADDER:
            cls = defaultdict(int)
            n = 0
            for i in sel:
                p = red[g][i]
                if not is_cycle(p):
                    continue
                n += 1
                cls[p] += 1
            counts.append(len(cls))
            cyc.append(n)
            cls_by_grid[g] = cls
        got[tag] = tuple(counts)
        per_grid[tag] = cls_by_grid
        want = TARGET_CLASSES[tag]
        ok = got[tag] == want
        print(f"  {tag:<6} loops selected {len(sel):>6,}")
        print(f"         classes  got  {' / '.join(f'{x:>5}' for x in counts)}")
        print(f"                  want {' / '.join(f'{x:>5}' for x in want)}"
              f"    {'exact' if ok else 'DIFFERS'}")
        print(f"         cycles        {' / '.join(f'{x:>5,}' for x in cyc)}")
        if not ok:
            for gi, g in enumerate(LADDER):
                if counts[gi] == want[gi]:
                    continue
                rows = sorted(cls_by_grid[g].items(), key=lambda kv: -kv[1])
                print(f"         {g}: {counts[gi]} classes, want {want[gi]}. "
                      f"top {min(MAX_CLASS_ROWS, len(rows))} of {len(rows)}, "
                      "by loops:")
                for k, v in rows[:MAX_CLASS_ROWS]:
                    print(f"           {v:>7,}  {' -> '.join(k)}")
                if len(rows) > MAX_CLASS_ROWS:
                    print(f"           ... {len(rows) - MAX_CLASS_ROWS} "
                          "further classes not printed")
        print()

    passed = all(got[t] == TARGET_CLASSES[t] for t in got)
    print("  B12-0b: " + ("reproduces, both arms, exactly. The station may "
                          "open."
                          if passed else
                          "DOES NOT reproduce. The station does not open. "
                          "Stop here."))
    print()
    return passed, per_grid


# ---------------------------------------------------------------------------
# the commutation the pullback test rests on
# ---------------------------------------------------------------------------

def gate_commutes(red, walks, maps):
    """Does relabelling a reduced word give the same thing as reducing again.

    The pullback test asks for the image of a fine cycle under `f`. That object
    is only well defined if reducing then relabelling agrees with relabelling
    then reducing. It is forced on paper, because a cancelling pair relabels to
    a cancelling pair, and it is checked here on every loop because the whole
    station is downstream of it.
    """
    print(f"{'=' * 78}\n  the premise: reduce then relabel == relabel then "
          "reduce\n" + "=" * 78)
    all_ok = True
    for fine, coarse in PAIRS:
        f = maps[(fine, coarse)]
        bad = []
        for i, w in enumerate(red[fine]):
            staged = reduce_closed_walk([f[x] for x in w])
            if staged != red[coarse][i]:
                bad.append(i)
        print(f"  {fine} -> {coarse}: {len(bad):,} of {len(red[fine]):,} "
              f"disagree   {'ok' if not bad else 'FAIL, defect here'}")
        for i in bad[:3]:
            staged = reduce_closed_walk([f[x] for x in red[fine][i]])
            print(f"      loop {i}")
            print(f"        staged {staged}")
            print(f"        direct {red[coarse][i]}")
        if bad:
            all_ok = False
    print()
    return all_ok


# ---------------------------------------------------------------------------
# B12-0a
# ---------------------------------------------------------------------------

def describe_L(vals):
    if not vals:
        return "no loops"
    v = np.asarray(vals, dtype=float)
    q = np.percentile(v, [10, 50, 90])
    modal, n_modal = Counter(vals).most_common(1)[0]
    return (f"L {int(v.min()):>3}..{int(v.max()):<3} "
            f"p10/p50/p90 {q[0]:>5.1f} {q[1]:>5.1f} {q[2]:>5.1f}  "
            f"modal L={modal} holds {n_modal / len(vals):6.1%}")


def gate_0a(red, meas, arm, length, maps):
    """The layers against the window length.

    Two tables. The first is the finest grid's classes against `L`, which is
    where a class was found to be very nearly the window length. The second is
    the one that matters here: the batch whose image is trivial, against `L`,
    per pair of grids. If that batch is one `L` band, then whatever the sums do
    is arithmetic on window length and not a statement about the cut, and those
    loops are reported apart.
    """
    print(f"{'=' * 78}\n  B12-0a   layers against the window length "
          "L = t_B - t_A\n" + "=" * 78)

    print("  part one: the finest grid's classes against L\n")
    for tag, code_ in (("defer", L.ARM_DEFER), ("mod", L.ARM_MOD)):
        sel = np.flatnonzero(meas & (arm == code_)).tolist()
        cls = defaultdict(list)
        for i in sel:
            p = red["g0m"][i]
            if is_cycle(p):
                cls[p].append(int(length[i]))
        rows = sorted(cls.items(), key=lambda kv: -len(kv[1]))
        big = [(k, v) for k, v in rows if len(v) >= MIN_CYCLES]
        single = [(k, v) for k, v in big if len(set(v)) == 1]
        print(f"  {tag:<6} {len(rows):,} classes, {len(big):,} at or above "
              f"MIN_CYCLES={MIN_CYCLES}, covering "
              f"{sum(len(v) for _, v in big):,} loops")
        print(f"         {len(single):,} of those {len(big):,} sit at a "
              "single L exactly")
        for k, v in big[:MAX_CLASS_ROWS]:
            flag = "  <- single L" if len(set(v)) == 1 else ""
            print(f"           n={len(v):>6,}  {describe_L(v)}{flag}")
            print(f"                    {' -> '.join(k)}")
        if len(big) > MAX_CLASS_ROWS:
            print(f"           ... {len(big) - MAX_CLASS_ROWS} further classes "
                  "at or above the floor, not printed")
        print()

    print("  part two: the trivial-image batch against L, per pair\n")
    for fine, coarse in PAIRS:
        f = maps[(fine, coarse)]
        for tag, code_ in (("defer", L.ARM_DEFER), ("mod", L.ARM_MOD)):
            sel = np.flatnonzero(meas & (arm == code_)).tolist()
            triv, live = [], []
            for i in sel:
                p = red[fine][i]
                if not is_cycle(p):
                    continue
                img = reduce_closed_walk([f[x] for x in p])
                (triv if not is_cycle(img) else live).append(int(length[i]))
            n_cyc = len(triv) + len(live)
            print(f"  {fine} -> {coarse}   {tag:<6} "
                  f"fine cycles {n_cyc:>6,}   trivial image {len(triv):>6,}   "
                  f"survives {len(live):>6,}")
            print(f"      trivial   {describe_L(triv)}")
            print(f"      survives  {describe_L(live)}")
            if len(triv) < MIN_CYCLES:
                print(f"      -> under MIN_CYCLES={MIN_CYCLES}. This pair is "
                      "not readable on this arm. Count printed, no reading.")
            if n_cyc and len(triv) == n_cyc:
                print("      -> every fine cycle has a trivial image. The "
                      "outcome of this pair is fixed by the construction "
                      "before any sum is taken, so both outcomes are NOT "
                      "reachable and this pair is not an arm.")
            if triv:
                cnt = Counter(triv)
                share = max(cnt.values()) / len(triv)
                if share >= 0.90:
                    print(f"      -> {share:.1%} of the trivial batch sits at "
                          f"L={cnt.most_common(1)[0][0]}. Confounded with "
                          "window length; report apart.")
                rows = sorted(cnt.items())
                shown = rows[:MAX_L_ROWS]
                print("      by L: " + "  ".join(f"{k}:{v}" for k, v in shown)
                      + (f"   ... {len(rows) - len(shown)} further L values "
                         "not printed" if len(rows) > len(shown) else ""))
            print()


# ---------------------------------------------------------------------------
# --floor: does the instrument floor depend on the window length
# ---------------------------------------------------------------------------

def buckets_by(vals, floor):
    """Greedy left-to-right merge of a sorted key until each block holds
    `floor` observations, with the short tail merged back into its neighbour.

    **No free parameter.** The key order is the key's own order, the block
    closes at the imported small-cell floor, and the tail rule is the only way
    to close the last block without inventing a second threshold.
    """
    order = sorted(set(vals))
    n = Counter(vals)
    out, cur, tot = [], [], 0
    for k in order:
        cur.append(k)
        tot += n[k]
        if tot >= floor:
            out.append(cur)
            cur, tot = [], 0
    if cur:
        if out:
            out[-1].extend(cur)
        else:
            out.append(cur)
    return out


def floor_population(archive):
    """The clean-cure arm's `omega - closed`, per loop, with its window length.

    This is the population the floor station measured `N` on. Nothing is
    recomputed differently here: the window finder, the column list, the
    residual and the scale estimator are all that station's.
    """
    pos, tab = LO.curve_table()
    c = K.Core(archive, cols=FL.COLS)
    try:
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        cc = FL.clean_cure_loops(c)
        flo = LO.loop_sums(cc, r, ok)
        q0 = K.quiet_pairs(c)
        pid0 = W.contract_periods(c, fill=True)
        pay0, _k0, _p0 = W.contract_payments(c, pid0, q0)
        es = G.episode_sums(c, pay0, cc["t_A"], cc["t_B"], cc["k"])
        closed, ideal = es[1], es[2]
        fm = np.asarray(flo["measurable"], dtype=bool) & np.asarray(ideal,
                                                                   dtype=bool)
        resid = (np.asarray(flo["omega"], dtype=float) - np.asarray(
            closed, dtype=float))[fm]
        Lf = (np.asarray(cc["t_B"]).astype(np.int64)
              - np.asarray(cc["t_A"]).astype(np.int64))[fm]
        return resid, Lf
    finally:
        c.close()


def cmd_floor(archives) -> int:
    """Is `N` flat in `L`, or does it grow with the number of months summed.

    The gate found that on the one live pair of grids the trivial-image batch
    has systematically longer windows than the batch that survives. The
    prohibition being tested is an exact zero and does not care, but the ratio
    the verdict is read on divides by `N`, and `N` is one scalar per vintage
    that does not move with `L`. **So measure whether it should.** This asks
    the question of the population the floor was drawn on, rather than assuming
    an answer either way.

    Writes nothing.
    """
    print("\n  Does the instrument floor move with the window length.\n"
          "  Population, estimator and window finder are the floor station's, "
          "unchanged.\n")
    for a in archives:
        resid, Lf = floor_population(a)
        pooled = FL.mad_scale(resid)
        want = FLOOR[a]
        rel = abs(pooled - want) / want if want else float("nan")
        print("=" * 78)
        print(f"  {a}   floor-arm loops {resid.size:,}")
        print(f"    pooled MAD(omega - closed)  {pooled:.4e}   "
              f"published N {want:.4e}   relative gap {rel:.2e}"
              f"   {'reproduces' if rel < 1e-3 else 'DIFFERS'}")
        if not resid.size:
            print()
            continue
        blocks = buckets_by(Lf.tolist(), MIN_CYCLES)
        print(f"    by L, greedy blocks of at least MIN_CYCLES={MIN_CYCLES} "
              f"({len(blocks)} blocks, no other parameter):")
        rows = []
        for blk in blocks:
            m = np.isin(Lf, blk)
            v = resid[m]
            s = FL.mad_scale(v)
            rows.append((blk[0], blk[-1], int(v.size), s,
                         float(np.median(np.abs(v)))))
        shown = rows[:MAX_L_ROWS]
        print(f"      {'L range':<12} {'n':>7}  {'MAD':>12}  {'median|.|':>12}"
              f"  {'MAD / pooled':>13}")
        for lo, hi, n, s, med in shown:
            rng = f"{lo}..{hi}" if lo != hi else f"{lo}"
            print(f"      {rng:<12} {n:>7,}  {s:>12.4e}  {med:>12.4e}"
                  f"  {s / pooled:>13.3f}")
        if len(rows) > len(shown):
            print(f"      ... {len(rows) - len(shown)} further blocks not "
                  "printed")
        ratios = [s / pooled for _, _, _, s, _ in rows if s == s and s > 0]
        if len(ratios) >= 2:
            print(f"    spread of MAD across blocks: "
                  f"{min(ratios):.3f} to {max(ratios):.3f} times pooled, "
                  f"a factor of {max(ratios) / min(ratios):.2f}")
        lo_half = [s for _, hi, _, s, _ in rows
                   if hi <= np.median(Lf)]
        hi_half = [s for lo, _, _, s, _ in rows
                   if lo > np.median(Lf)]
        if lo_half and hi_half:
            print(f"    short windows vs long, MAD "
                  f"{np.median(lo_half):.4e} vs {np.median(hi_half):.4e}"
                  f"   long/short {np.median(hi_half) / np.median(lo_half):.3f}")
        print()
    print("  Read: a ratio near 1 across every block means one scalar N is the "
          "right\n  denominator and the window-length skew of the "
          "trivial-image batch does not\n  reach the verdict. A ratio that "
          "climbs with L means it does, and the run\n  must divide by the "
          "block's own MAD.\n")
    return 0


# ---------------------------------------------------------------------------
# --run: the pullback test, on the one pair of grids the gate left alive
# ---------------------------------------------------------------------------

#: The gate killed two of the three adjacent pairs on the registered vintage:
#: the finest pair leaves 5 and 2 cycles with a trivial image, under the floor,
#: and the coarsest pair leaves **every** cycle with a trivial image and none
#: surviving, so its outcome is fixed by the construction before any sum is
#: taken and it is not an arm. This is what is left.
LIVE_PAIR = ("g1", "g2")

#: Resamples for the instrument null. Same count the placebo ladder is
#: registered at, so no second number enters the file.
N_NULL = 999


def block_index(blocks):
    """L value -> block position, from the greedy blocking."""
    return {v: i for i, blk in enumerate(blocks) for v in blk}


def stat_median_ratio(absom, denom):
    """The L-corrected headline: median over loops of |omega| / N(that loop's L).

    The uncorrected form divides one median by one scalar. That scalar is the
    floor arm's pooled MAD, which is 87 per cent an `L = 2` measurement, while
    the batch being read sits at `L` around 13 to 20. Dividing each loop by the
    floor at **its own** window length is the same estimator conditioned, not a
    different estimator, and it uses every loop rather than a subset.
    """
    v = np.asarray(absom, dtype=float) / np.asarray(denom, dtype=float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float("nan")


def run_one(archive: str) -> dict:
    """One vintage, one pass over the residuals, both sides.

    The signal side and the floor side share `row_residuals`, which is the
    expensive step, so they are computed together rather than in two runs.
    """
    pos, tab = LO.curve_table()
    cols = sorted(set(LO.COLS) | set(FL.COLS))
    c = K.Core(archive, cols=cols)
    try:
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)

        # ---- floor side ------------------------------------------------
        cc = FL.clean_cure_loops(c)
        flo = LO.loop_sums(cc, r, ok)
        q0 = K.quiet_pairs(c)
        pid0 = W.contract_periods(c, fill=True)
        pay0, _k0, _p0 = W.contract_payments(c, pid0, q0)
        es = G.episode_sums(c, pay0, cc["t_A"], cc["t_B"], cc["k"])
        fm = (np.asarray(flo["measurable"], dtype=bool)
              & np.asarray(es[2], dtype=bool))
        fres = (np.asarray(flo["omega"], dtype=float)
                - np.asarray(es[1], dtype=float))[fm]
        fL = (np.asarray(cc["t_B"]).astype(np.int64)
              - np.asarray(cc["t_A"]).astype(np.int64))[fm]
        pooled_N = FL.mad_scale(fres)

        #: Blocks come from the **floor** arm, so every block holds at least
        #: MIN_CYCLES floor loops by construction and `N(L)` is never estimated
        #: on fewer. Whether the signal side reaches the floor in a block is a
        #: separate question and is printed per block.
        blocks = buckets_by(fL.tolist(), MIN_CYCLES)
        bidx = block_index(blocks)
        last = len(blocks) - 1
        bN, bn_floor, bres = [], [], []
        for blk in blocks:
            m = np.isin(fL, blk)
            bN.append(FL.mad_scale(fres[m]))
            bn_floor.append(int(m.sum()))
            bres.append(fres[m])

        # ---- signal side -----------------------------------------------
        lp = L.find_loops(c)
        sums = LO.loop_sums(lp, r, ok)
        om = np.asarray(sums["omega"], dtype=float)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])
        sL = (np.asarray(lp["t_B"]).astype(np.int64)
              - np.asarray(lp["t_A"]).astype(np.int64))
        walks, _t = raw_walks(c, lp)
        fine, coarse = LIVE_PAIR
        red_f, _d1 = reduce_on(walks, dict(fr.GRIDS)[fine])
        red_c, _d2 = reduce_on(walks, dict(fr.GRIDS)[coarse])
        raw_labels = set()
        for w in walks:
            raw_labels.update(w)
        f, clash = vertex_map(dict(fr.GRIDS)[fine], dict(fr.GRIDS)[coarse],
                              raw_labels)

        rec = {"archive": archive, "pair": list(LIVE_PAIR),
               "pooled_N": pooled_N, "published_N": FLOOR.get(archive),
               "floor_loops": int(fres.size),
               "vertex_map_clashes": len(clash),
               "blocks": [{"L_lo": b[0], "L_hi": b[-1], "n_floor": n,
                           "N": v}
                          for b, n, v in zip(blocks, bn_floor, bN)],
               "arms": {}}

        for tag, code_ in (("defer", L.ARM_DEFER), ("mod", L.ARM_MOD)):
            sel = np.flatnonzero(meas & (arm == code_)).tolist()
            triv_i, live_n = [], 0
            for i in sel:
                if not is_cycle(red_f[i]):
                    continue
                if is_cycle(reduce_closed_walk([f[x] for x in red_f[i]])):
                    live_n += 1
                else:
                    triv_i.append(i)
            absom = np.abs(om[triv_i])
            Ls = sL[triv_i].astype(int)
            #: Loops whose L is past the floor arm's range fall in the last
            #: block. Counted and printed; a silent assignment would read as
            #: coverage.
            beyond = int(sum(1 for v in Ls.tolist() if v not in bidx))
            pos_b = np.array([bidx.get(int(v), last) for v in Ls.tolist()],
                             dtype=int)
            denom = np.array([bN[j] for j in pos_b.tolist()], dtype=float)

            per_block = []
            for j, blk in enumerate(blocks):
                m = pos_b == j
                if not m.any():
                    continue
                per_block.append({
                    "L_lo": blk[0], "L_hi": blk[-1],
                    "n_signal": int(m.sum()), "n_floor": bn_floor[j],
                    "N": bN[j],
                    "median_abs_omega": float(np.median(absom[m])),
                    "ratio_local": float(np.median(absom[m]) / bN[j])
                    if bN[j] else float("nan"),
                    "ratio_pooled": float(np.median(absom[m]) / pooled_N)
                    if pooled_N else float("nan"),
                    "readable": bool(m.sum() >= MIN_CYCLES)})

            corrected = stat_median_ratio(absom, denom)
            uncorrected = (float(np.median(absom) / pooled_N)
                           if absom.size and pooled_N else float("nan"))

            #: The instrument null, empirical. Draw the same block composition
            #: from the floor arm and form the same statistic. No distribution
            #: is assumed and no constant is introduced: the population, the
            #: blocks and the count are all already fixed above.
            rng = np.random.default_rng(0)
            null = []
            for _ in range(N_NULL if absom.size else 0):
                draw = np.empty(absom.size)
                for j in range(len(blocks)):
                    m = pos_b == j
                    k = int(m.sum())
                    if not k:
                        continue
                    src = bres[j]
                    draw[m] = np.abs(rng.choice(src, size=k, replace=True))
                null.append(stat_median_ratio(draw, denom))
            null = np.asarray(null, dtype=float)

            verdict = "no_reading"
            if absom.size < MIN_CYCLES:
                verdict = "under_min_cycles"
            elif corrected <= 1.0:
                verdict = "pullback_holds"
            elif corrected >= SIGNAL_OVER_NOISE:
                verdict = "pullback_fails"
            else:
                verdict = "indeterminate"

            a = {"loops_selected": len(sel), "fine_cycles": len(triv_i) + live_n,
                 "trivial_image": len(triv_i), "survives": live_n,
                 "L_beyond_floor_range": beyond,
                 "median_abs_omega": float(np.median(absom))
                 if absom.size else float("nan"),
                 "ratio_L_corrected": corrected,
                 "ratio_pooled_floor": uncorrected,
                 "verdict": verdict, "per_block": per_block}
            if null.size:
                a["null"] = {"n": int(null.size), "mean": float(null.mean()),
                             "sd": float(null.std(ddof=1)),
                             "p90": float(np.percentile(null, 90)),
                             "p99": float(np.percentile(null, 99)),
                             "quantile_of_observed":
                                 float((null <= corrected).mean())}
                if verdict == "pullback_fails":
                    z95, z80 = 1.6449, 0.8416
                    a["MDE"] = float(null.mean() + (z95 + z80) * null.std(ddof=1))
            #: **The control the prohibition needs, and the reason it needs
            #: one.** `omega` is a sum of monthly residuals, and a monthly
            #: residual depends on balance, rate and the curve, not only on
            #: which state the loan is in. So `omega` is not automatically a
            #: one-form on the state graph, and if it is not one on the
            #: **finest** grid then it cannot be a pullback from any coarser
            #: one either, for a reason that has nothing to do with the cut.
            #: The loops whose word is already trivial at the finest grid are
            #: exactly the ones that test this: under any one-form hypothesis
            #: they must sum to zero, and no coarsening is involved. **If they
            #: read the same as the batch above, the batch above is not about
            #: the cut.**
            ctrl_i = [i for i in sel
                      if not is_cycle(reduce_on_one(walks[i],
                                                    dict(fr.GRIDS)["g0m"]))]
            cabs = np.abs(om[ctrl_i])
            cL = sL[ctrl_i].astype(int)
            cpos = np.array([bidx.get(int(v), last) for v in cL.tolist()],
                            dtype=int)
            cden = np.array([bN[j] for j in cpos.tolist()], dtype=float)
            a["control_trivial_at_finest_grid"] = {
                "n": len(ctrl_i),
                "median_abs_omega": float(np.median(cabs))
                if cabs.size else float("nan"),
                "ratio_L_corrected": stat_median_ratio(cabs, cden)
                if cabs.size else float("nan"),
                "readable": bool(len(ctrl_i) >= MIN_CYCLES)}
            rec["arms"][tag] = a
        return rec
    finally:
        c.close()


def cmd_run(archives) -> int:
    recs = []
    print(f"\n  B12-A, the pullback test, on {LIVE_PAIR[0]} -> "
          f"{LIVE_PAIR[1]} only.\n"
          "  The other two adjacent pairs were closed by the gate, one for "
          "sample and one\n  because its outcome is fixed by the "
          "construction. Verdicts run on the floor at\n  each loop's own "
          "window length; the pooled-floor figure prints beside it so the\n"
          "  correction is visible rather than asserted.\n")
    for a in archives:
        rec = run_one(a)
        recs.append(rec)
        print("=" * 78)
        print(f"  {rec['archive']}   floor arm {rec['floor_loops']:,} loops   "
              f"pooled N {rec['pooled_N']:.4e}   published "
              f"{rec['published_N']:.4e}   blocks {len(rec['blocks'])}")
        if rec["vertex_map_clashes"]:
            print(f"  f IS NOT A MAP on this vintage: "
                  f"{rec['vertex_map_clashes']} clashes. Reading void.")
        for tag in ("defer", "mod"):
            d = rec["arms"][tag]
            print(f"  {tag:<6} fine cycles {d['fine_cycles']:>6,}   "
                  f"trivial image {d['trivial_image']:>5,}   survives "
                  f"{d['survives']:>6,}   past floor L range "
                  f"{d['L_beyond_floor_range']}")
            print(f"         median |omega| {d['median_abs_omega']:.4e}")
            print(f"         ratio, floor at each loop's own L  "
                  f"{d['ratio_L_corrected']:>8.3f}   <- the verdict runs here")
            print(f"         ratio, one pooled floor            "
                  f"{d['ratio_pooled_floor']:>8.3f}   <- what the pooled "
                  "floor would have said")
            if "null" in d:
                n_ = d["null"]
                print(f"         instrument null: mean {n_['mean']:.3f}  "
                      f"sd {n_['sd']:.3f}  p90 {n_['p90']:.3f}  "
                      f"p99 {n_['p99']:.3f}  observed sits at quantile "
                      f"{n_['quantile_of_observed']:.4f}")
            if "MDE" in d:
                print(f"         MDE at alpha 0.05, power 0.80: {d['MDE']:.3f}"
                      f"   observed {d['ratio_L_corrected']:.3f}")
            ct = d.get("control_trivial_at_finest_grid")
            if ct:
                print(f"         CONTROL, already trivial at the finest grid, "
                      f"no coarsening involved: n={ct['n']}")
                print(f"           median |omega| {ct['median_abs_omega']:.4e}"
                      f"   ratio {ct['ratio_L_corrected']:>12.3f}"
                      f"   {'' if ct['readable'] else '(under MIN_CYCLES)'}")
                if ct["readable"] and ct["ratio_L_corrected"] == ct[
                        "ratio_L_corrected"]:
                    print("           -> compare with the line above. A "
                          "control of the same size means the reading is not "
                          "about the cut.")
            print(f"         VERDICT  {d['verdict']}")
            rows = d["per_block"]
            shown = rows[:MAX_L_ROWS]
            print(f"         {'L':<10} {'n_sig':>6} {'n_flr':>6} "
                  f"{'N':>12} {'med|w|':>12} {'local':>8} {'pooled':>8}")
            for b in shown:
                rng_ = (f"{b['L_lo']}..{b['L_hi']}" if b['L_lo'] != b['L_hi']
                        else f"{b['L_lo']}")
                mark = "" if b["readable"] else "  under floor, no reading"
                print(f"         {rng_:<10} {b['n_signal']:>6,} "
                      f"{b['n_floor']:>6,} {b['N']:>12.4e} "
                      f"{b['median_abs_omega']:>12.4e} "
                      f"{b['ratio_local']:>8.3f} {b['ratio_pooled']:>8.3f}"
                      f"{mark}")
            if len(rows) > len(shown):
                print(f"         ... {len(rows) - len(shown)} further blocks "
                      "not printed")
            print()

    print("=" * 78)
    print("  across vintages, the verdict per arm (consistency is itself a "
          "reading,\n  not something to average):")
    for tag in ("defer", "mod"):
        line = "   ".join(f"{r['archive']} {r['arms'][tag]['verdict']}"
                          for r in recs)
        print(f"    {tag:<6} {line}")
    print()

    RESULTS.mkdir(parents=True, exist_ok=True)
    #: A run on fewer than the registered six vintages is an off-parameter run
    #: and must not land on the registered record's name. The renderer skips
    #: `.offparam` by filename, so this cannot become a section of the results
    #: page either.
    full = sorted(FLOOR)
    out = (RESULTS / "b12_pullback.json" if sorted(archives) == full
           else RESULTS / ("b12_pullback.offparam_"
                           + "_".join(sorted(archives)) + ".json"))
    out.write_text(json.dumps(
        {"stage": "B12", "step": "pullback", "diagnostic_only": True,
         "diagnostic_reason":
             "The placebo ladder registered beside this test has not run, and "
             "until it does a separation from the floor cannot be told from "
             "one a size-preserving relabel of the grid would also produce. "
             "The station is not closed and this record is not a licensed "
             "reading.",
         "pair": list(LIVE_PAIR), "min_cycles": MIN_CYCLES,
         "signal_over_noise": SIGNAL_OVER_NOISE, "n_null": N_NULL,
         "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.relative_to(ROOT)}   (diagnostic_only, so the "
          "renderer skips it)\n")
    return 0


# ---------------------------------------------------------------------------
# --perm: the permutation criterion. Registered as a post-run redesign.
# ---------------------------------------------------------------------------

#: The pair the permutation runs on. **Not** the pair the pullback test ran on,
#: and the reason is pure counting done before any run: the coarser pair has six
#: vertices in a `(1, 3, 1, 1)` fibre shape, so a size-preserving relabelling
#: has only `C(6,3) = 20` distinct draws, the smallest attainable `p` is
#: `1/21` and the verdict line is at `0.05`. This pair has 66 vertices in a
#: `(1, 63, 1, 1)` shape and `C(66,3) = 45,760` distinct draws. It is also the
#: cut that is actually used, raw states straight to the reported grid.
PERM_PAIR = ("g0m", "g2")

#: Draws. The count the placebo ladder was registered at, so no new number.
N_PERM = 999

#: Fixed seed. The draw must not depend on when the run happened.
PERM_SEED = 0


def word_split(words, singles, left=None):
    """Reduce every distinct word under one relabelling, and say if it survives.

    `singles` stay alone. Everything else merges into one label, or into two
    when `left` is given, which is the two-way-split class. Only the partition
    matters to free reduction, so image names are placeholders and no
    economically meaningful name is invented for a random block.
    """
    out = {}
    for w in words:
        if left is None:
            img = [x if x in singles else "__M__" for x in w]
        else:
            img = [x if x in singles else ("__L__" if x in left else "__R__")
                   for x in w]
        out[w] = is_cycle(reduce_closed_walk(img))
    return out


def t_statistic(absom, Lb, alive, blocks_idx, nblocks):
    """`T`: median over the dead batch of |omega| divided by the live batch's
    median |omega| at the same window length.

    Returns `(T, n_dead, n_unmatched)`. A dead loop whose block holds no live
    loop cannot be matched; it is counted and excluded, never dropped quietly.
    """
    med = np.full(nblocks, np.nan)
    for j in range(nblocks):
        m = (blocks_idx == j) & alive
        if m.any():
            med[j] = np.median(absom[m])
    dead = ~alive
    if not dead.any():
        return float("nan"), 0, 0
    d_idx = blocks_idx[dead]
    ref = med[d_idx]
    good = np.isfinite(ref) & (ref > 0)
    if not good.any():
        return float("nan"), int(dead.sum()), int(dead.sum())
    r = absom[dead][good] / ref[good]
    return float(np.median(r)), int(dead.sum()), int((~good).sum())


#: The three comparison classes, and why there is more than one.
#:
#: `shape` is the class the redesign registered: any three of the vertices
#: stand alone, the rest merge, matching the real fibre shape. **A 49-draw
#: smoke run found it degenerate**: the real cut leaves 13,710 of 13,878 cycles
#: alive while a random cut of that shape leaves essentially none, so four
#: draws in five produce no live batch at all and the null for the ratio is
#: estimated on a self-selected fifth. The reason is structural and countable:
#: a cycle survives a coarsening only if at least two interior states stay
#: distinct, and the real grid gets that from `modified` and `deferred` being
#: their own states. **Those two are not a cut anyone chose. They are two
#: fields in the file.**
#:
#: So the other two classes hold the event vertices fixed and permute the thing
#: the station's question is actually about, which is where the delinquency
#: ladder gets cut.
#:
#: `alone`  one delinquency code stands alone, the rest merge. Same shape as
#:          the real cut, which puts `00` alone. **Exhaustive at 64 draws**,
#:          which is the whole class, so the count is not a sampling choice.
#: `split`  any two-way split of the delinquency codes. Spans the plausible
#:          alternatives rather than the shape-matched ones. Sampled.
NULL_CLASSES = ("shape", "alone", "split")


def draw_singletons(kind, vocab, real_singles, rng, i):
    """One draw from a comparison class. Returns the set of vertices that stay
    alone, or None when the class is exhausted at index `i`.
    """
    events = [v for v in vocab if v in (fr.MODIFIED, fr.DEFERRED)]
    codes = [v for v in vocab if v not in (fr.MODIFIED, fr.DEFERRED)]
    if kind == "shape":
        pick = rng.choice(len(vocab), size=len(real_singles), replace=False)
        return frozenset(vocab[j] for j in pick.tolist()), None
    if kind == "alone":
        if i >= len(codes):
            return None, None
        return frozenset(events + [codes[i]]), None
    if kind == "split":
        #: A two-way split of the codes. The merged label is shared by one
        #: side; the other side gets its own, so `singles` is not the right
        #: shape here and the split is returned explicitly.
        side = rng.integers(0, 2, size=len(codes)).astype(bool)
        if side.all() or (~side).all():
            return None, "degenerate"
        left = frozenset(c for c, b in zip(codes, side.tolist()) if b)
        return frozenset(events), left
    raise ValueError(kind)


def perm_one(archive: str, n_draws: int, kind: str = "shape") -> dict:
    pos, tab = LO.curve_table()
    c = K.Core(archive, cols=LO.COLS)
    try:
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        lp = L.find_loops(c)
        sums = LO.loop_sums(lp, r, ok)
        om = np.asarray(sums["omega"], dtype=float)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])
        sL = (np.asarray(lp["t_B"]).astype(np.int64)
              - np.asarray(lp["t_A"]).astype(np.int64))
        walks, _t = raw_walks(c, lp)
        fine, coarse = PERM_PAIR
        red_f, _d = reduce_on(walks, dict(fr.GRIDS)[fine])

        rec = {"archive": archive, "pair": list(PERM_PAIR),
               "null_class": kind,
               "n_draws": n_draws, "seed": PERM_SEED, "arms": {}}

        vocab = sorted({x for w in red_f for x in w})
        real_gf = dict(fr.GRIDS)[coarse]
        #: The real partition's singletons are the vertices whose coarse image
        #: nothing else shares. Derived, not typed in.
        img = Counter(real_gf(v) for v in vocab)
        real_singles = frozenset(v for v in vocab if img[real_gf(v)] == 1)
        shape = sorted(Counter(real_gf(v) for v in vocab).values(),
                       reverse=True)
        rec["vertices"] = len(vocab)
        rec["fibre_shape"] = shape
        rec["real_singletons"] = sorted(real_singles)
        rec["distinct_partitions"] = math.comb(len(vocab),
                                               len(real_singles))

        for tag, code_ in (("defer", L.ARM_DEFER), ("mod", L.ARM_MOD)):
            sel = [i for i in np.flatnonzero(meas & (arm == code_)).tolist()
                   if is_cycle(red_f[i])]
            if not sel:
                rec["arms"][tag] = {"cycles": 0, "note": "no cycles"}
                continue
            words = [red_f[i] for i in sel]
            uniq = sorted(set(words))
            widx = {w: k for k, w in enumerate(uniq)}
            wof = np.array([widx[w] for w in words], dtype=int)
            absom = np.abs(om[sel])
            Ls = sL[sel].astype(int)

            #: Blocks are fixed once, from **every** cycle's L, so they do not
            #: move between the real grid and a draw.
            blocks = buckets_by(Ls.tolist(), MIN_CYCLES)
            bmap = block_index(blocks)
            bidx = np.array([bmap.get(int(v), len(blocks) - 1)
                             for v in Ls.tolist()], dtype=int)

            def alive_for(singles, left=None):
                keep = word_split(uniq, singles, left)
                flags = np.array([keep[w] for w in uniq], dtype=bool)
                return flags[wof]

            alive = alive_for(real_singles)
            T, n_dead, n_unmatched = t_statistic(absom, Ls, alive, bidx,
                                                 len(blocks))

            rng = np.random.default_rng(PERM_SEED)
            Ts, Bs, degenerate = [], [], 0
            for di in range(n_draws):
                singles, left = draw_singletons(kind, vocab, real_singles,
                                                rng, di)
                if singles is None:
                    if left == "degenerate":
                        degenerate += 1
                        Bs.append(0)
                        Ts.append(float("nan"))
                        continue
                    break
                al = alive_for(singles, left)
                if al.all():
                    degenerate += 1
                    Bs.append(0)
                    Ts.append(float("nan"))
                    continue
                t_, nd_, _u = t_statistic(absom, Ls, al, bidx, len(blocks))
                Ts.append(t_)
                Bs.append(nd_)
            Ta = np.asarray(Ts, dtype=float)
            Ba = np.asarray(Bs, dtype=float)
            fin = np.isfinite(Ta)

            a = {"cycles": len(sel), "distinct_words": len(uniq),
                 "blocks": len(blocks), "n_dead_real": n_dead,
                 "n_unmatched_real": n_unmatched, "T": T,
                 "degenerate_draws": degenerate,
                 "usable_draws": int(fin.sum())}
            if fin.sum() >= 2 and T == T:
                below = float((Ta[fin] <= T).mean())
                a["quantile_of_T"] = below
                a["p_two_sided"] = float(min(1.0, 2 * min(below, 1 - below)))
                a["null_T"] = {"mean": float(np.nanmean(Ta[fin])),
                               "sd": float(np.nanstd(Ta[fin], ddof=1)),
                               "p05": float(np.percentile(Ta[fin], 5)),
                               "p50": float(np.percentile(Ta[fin], 50)),
                               "p95": float(np.percentile(Ta[fin], 95))}
                z95, z80 = 1.6449, 0.8416
                a["MDE"] = float(a["null_T"]["mean"]
                                 + (z95 + z80) * a["null_T"]["sd"])
                a["null_B"] = {"p05": float(np.percentile(Ba, 5)),
                               "p50": float(np.percentile(Ba, 50)),
                               "p95": float(np.percentile(Ba, 95)),
                               "quantile_of_real":
                                   float((Ba <= n_dead).mean())}
                a["verdict"] = ("indistinguishable_from_random_cut"
                                if a["p_two_sided"] >= 0.05
                                else "real_cut_is_special")
                if n_dead < MIN_CYCLES:
                    a["verdict"] = "under_min_cycles"
            else:
                a["verdict"] = "no_reading"
            rec["arms"][tag] = a
        return rec
    finally:
        c.close()


def cmd_perm(archives, n_draws, kinds) -> int:
    recs = []
    print(f"\n  B12-C, the permutation criterion, on {PERM_PAIR[0]} -> "
          f"{PERM_PAIR[1]}.\n"
          "  The zero is exchangeability, not a prohibition, so nothing here "
          "needs omega to\n  be a one-form. Two readings, reported apart: "
          "where T sits in the null, and\n  where the real cut's kill count "
          "sits in its null.\n")
    for a in archives:
      for kind in kinds:
        nd = 64 if kind == "alone" else n_draws
        rec = perm_one(a, nd, kind)
        recs.append(rec)
        print("=" * 78)
        print(f"  {rec['archive']}   null class '{kind}'   "
              f"{rec['vertices']} vertices   fibre shape "
              f"{rec['fibre_shape']}   singletons "
              f"{rec['real_singletons']}")
        for tag in ("defer", "mod"):
            d = rec["arms"][tag]
            if d.get("cycles", 0) == 0:
                print(f"  {tag:<6} no cycles")
                continue
            print(f"  {tag:<6} cycles {d['cycles']:,}   distinct words "
                  f"{d['distinct_words']}   L blocks {d['blocks']}   "
                  f"usable draws {d['usable_draws']}/{nd}   degenerate "
                  f"{d['degenerate_draws']}")
            print(f"         real cut kills {d['n_dead_real']:,}   "
                  f"unmatched {d['n_unmatched_real']}")
            print(f"         T = {d['T']:.4f}")
            if "null_T" in d:
                n_ = d["null_T"]
                print(f"         null T: p05 {n_['p05']:.4f}  p50 "
                      f"{n_['p50']:.4f}  p95 {n_['p95']:.4f}   "
                      f"mean {n_['mean']:.4f} sd {n_['sd']:.4f}")
                print(f"         T sits at quantile {d['quantile_of_T']:.4f}"
                      f"   two-sided p {d['p_two_sided']:.4f}")
                print(f"         MDE (alpha .05, power .80) {d['MDE']:.4f}"
                      f"   -> B's |omega| must reach {d['MDE']:.2f}x C's "
                      "before this design sees it")
                b_ = d["null_B"]
                print(f"         SECOND READING, reported apart: kill count."
                      f" null p05/p50/p95 {b_['p05']:.0f}/{b_['p50']:.0f}/"
                      f"{b_['p95']:.0f}, real {d['n_dead_real']} at quantile "
                      f"{b_['quantile_of_real']:.4f}")
                if b_["quantile_of_real"] <= 0.05 or b_[
                        "quantile_of_real"] >= 0.95:
                    print("           -> the real cut's kill count is extreme "
                          "in its own null. Per the registration, T's "
                          "unconditional quantile is NOT read as a statement "
                          "about omega.")
            print(f"         VERDICT  {d['verdict']}")
            print()
    print("=" * 78)
    for tag in ("defer", "mod"):
        line = "   ".join(
            f"{r['archive']}/{r['null_class']} "
            f"{r['arms'][tag].get('verdict', 'none')}"
            for r in recs)
        print(f"    {tag:<6} {line}")
    print()
    RESULTS.mkdir(parents=True, exist_ok=True)
    full = sorted(FLOOR)
    offparam = (sorted(archives) != full or n_draws != N_PERM
                or sorted(kinds) != sorted(NULL_CLASSES))
    name = ("b12_perm.json" if not offparam
            else "b12_perm.offparam_" + "_".join(sorted(archives))
                 + "_" + "".join(k[0] for k in kinds)
                 + f"_draws{n_draws}.json")
    out = RESULTS / name
    out.write_text(json.dumps(
        {"stage": "B12", "step": "permutation", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered as a post-run redesign on 2026-08-19 after the "
             "pullback prohibition was found to fail at the finest grid, where "
             "no coarsening is involved. The station is not closed, the "
             "companion pullback reading is withdrawn as an answer to the "
             "station's question, and this record is not a licensed reading.",
         "pair": list(PERM_PAIR), "n_draws": n_draws, "seed": PERM_SEED,
         "null_classes": list(kinds),
         "min_cycles": MIN_CYCLES, "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.relative_to(ROOT)}"
          + ("   (off-parameter name)" if offparam else "") + "\n")
    return 0


# ---------------------------------------------------------------------------
# --ladder: enumerate the cuts a person could have made, and read the spread
# ---------------------------------------------------------------------------

#: **Why this replaces the permutation.** A permutation asks whether the real
#: cut is special among arbitrary cuts. That question has an answer forced by
#: the loop construction: every loop is anchored at `00` and leaves it, so any
#: cut that puts `00` with the states it passes through flattens the loop, and
#: the real cut is the only one in a shape-matched class that isolates `00`.
#: The real cut is therefore an end point of any such class, and an end point
#: cannot sit inside a null.
#:
#: **The station's question was never "is the real cut special".** It is
#: whether a different cut would have given a different reading. That is
#: answered by enumeration: recompute the reading under every cut in the class
#: a person could plausibly have chosen, and print the spread. No null, no
#: p-value, no threshold on an estimate, and no end-point problem, because
#: nothing is being ranked.
#:
#: **The class.** The delinquency codes are ordered, they are months
#: delinquent, so a cut anyone would make is a set of thresholds on that
#: ladder. Holding fixed the three layers that are not choices (the anchor
#: `00`, and `modified` and `deferred`, which are fields in the file), a
#: three-bin cut of the 63 remaining codes is two breakpoints among 62 gaps:
#: **C(62, 2) = 1,891 cuts, enumerated whole.** The real grid is one of them,
#: with breakpoints after `01` and after `02`, which is the 30-day and 60-day
#: convention.
LADDER_BINS = 3


def ladder_cuts(codes):
    """Every way to cut an ordered ladder into `LADDER_BINS` contiguous bins.

    Yields `(i, j)` breakpoints and the resulting bin id per code. Enumerated
    whole, so the count is a fact about the ladder and not a sampling choice.
    """
    n = len(codes)
    for i in range(1, n):
        for j in range(i + 1, n):
            yield (i, j)


def cmd_ladder(archives) -> int:
    print("\n  B12-D: the reading under every cut a person could have made.\n"
          "  Enumerated whole, so there is no null and nothing is ranked. The "
          "question is\n  how far the reading moves across cuts, and the "
          "scale it is read against is the\n  instrument floor, which is "
          "measured elsewhere.\n")
    recs = []
    for archive in archives:
        pos, tab = LO.curve_table()
        c = K.Core(archive, cols=LO.COLS)
        try:
            disc, _ = LO.disc_of_row(c, pos, tab)
            r, ok, _ = W.row_residuals(c, disc)
            lp = L.find_loops(c)
            sums = LO.loop_sums(lp, r, ok)
            om = np.asarray(sums["omega"], dtype=float)
            meas = np.asarray(sums["measurable"], dtype=bool)
            arm = np.asarray(lp["arm"])
            walks, _t = raw_walks(c, lp)
            red0, _d = reduce_on(walks, dict(fr.GRIDS)["g0m"])

            vocab = sorted({x for w in red0 for x in w})
            events = [v for v in vocab if v in (fr.MODIFIED, fr.DEFERRED)]
            codes = sorted(v for v in vocab if v not in events)
            #: `00` is the anchor and is held alone; the ladder that gets cut
            #: is what is left.
            anchor, rung = codes[0], codes[1:]
            rec = {"archive": archive, "codes": len(codes),
                   "anchor": anchor, "rungs": len(rung),
                   "cuts": len(list(ladder_cuts(rung))), "arms": {}}
            rec["rows_above_98"] = anchor_states.last_beyond_98
            print("=" * 78)
            print(f"  {archive}   ladder {anchor} + {len(rung)} rungs "
                  f"({rung[0]}..{rung[-1]})   cuts enumerated "
                  f"{rec['cuts']:,}   rows with a code above 98: "
                  f"{anchor_states.last_beyond_98:,}")

            for tag, code_ in (("defer", L.ARM_DEFER), ("mod", L.ARM_MOD)):
                sel = [i for i in np.flatnonzero(meas & (arm == code_)).tolist()
                       if is_cycle(red0[i])]
                if not sel:
                    continue
                words = [red0[i] for i in sel]
                uniq = sorted(set(words))
                widx = {w: k for k, w in enumerate(uniq)}
                wof = np.array([widx[w] for w in words], dtype=int)
                absom = np.abs(om[sel])
                #: per-word loop membership, built once
                members = [np.flatnonzero(wof == k) for k in range(len(uniq))]

                def read_cut(i, j):
                    lab = {anchor: "A"}
                    for t, cd in enumerate(rung):
                        lab[cd] = "B0" if t < i else ("B1" if t < j else "B2")
                    for e in events:
                        lab[e] = e
                    img = {}
                    for k, w in enumerate(uniq):
                        red = reduce_closed_walk([lab[x] for x in w])
                        if is_cycle(red):
                            img.setdefault(red, []).append(k)
                    alive = sum(len(members[k]) for ks in img.values()
                                for k in ks)
                    meds = []
                    for ks in img.values():
                        idx = np.concatenate([members[k] for k in ks])
                        if idx.size >= MIN_CYCLES:
                            meds.append(float(np.median(absom[idx])))
                    sp = spread_iqr(meds) if len(meds) >= 2 else float("nan")
                    return len(img), alive, sp, len(meds)

                real = read_cut(1, 2)
                cls, alv, spr, big = [], [], [], []
                for (i, j) in ladder_cuts(rung):
                    a_, b_, c_, d_ = read_cut(i, j)
                    cls.append(a_)
                    alv.append(b_)
                    spr.append(c_)
                    big.append(d_)
                cls = np.asarray(cls, float)
                alv = np.asarray(alv, float)
                spr = np.asarray(spr, float)
                fin = np.isfinite(spr)

                def place(v, arr):
                    return float((np.asarray(arr) <= v).mean())

                a = {"real": {"classes": real[0], "alive": real[1],
                              "spread": real[2], "classes_ge_min": real[3]},
                     "classes": {"min": float(cls.min()),
                                 "p50": float(np.percentile(cls, 50)),
                                 "max": float(cls.max()),
                                 "real_at": place(real[0], cls)},
                     "alive": {"min": float(alv.min()),
                               "p50": float(np.percentile(alv, 50)),
                               "max": float(alv.max()),
                               "real_at": place(real[1], alv)},
                     "spread": {"finite": int(fin.sum()),
                                "min": float(spr[fin].min()) if fin.any()
                                else float("nan"),
                                "p50": float(np.percentile(spr[fin], 50))
                                if fin.any() else float("nan"),
                                "max": float(spr[fin].max()) if fin.any()
                                else float("nan"),
                                "real_at": place(real[2], spr[fin])
                                if fin.any() else float("nan")}}
                floor = FLOOR.get(archive, float("nan"))
                a["spread_over_floor"] = {
                    "min": a["spread"]["min"] / floor,
                    "p50": a["spread"]["p50"] / floor,
                    "max": a["spread"]["max"] / floor,
                    "real": real[2] / floor}
                rec["arms"][tag] = a

                print(f"  {tag:<6} cycles {len(sel):,}   distinct words "
                      f"{len(uniq)}")
                print(f"         real grid (cut after {rung[0]}, after "
                      f"{rung[1]}): classes {real[0]}   alive {real[1]:,}   "
                      f"classes at or above the floor {real[3]}")
                print(f"         classes across all cuts: "
                      f"{cls.min():.0f} / {np.percentile(cls, 50):.0f} / "
                      f"{cls.max():.0f}   real sits at "
                      f"{a['classes']['real_at']:.4f}")
                print(f"         alive   across all cuts: "
                      f"{alv.min():,.0f} / {np.percentile(alv, 50):,.0f} / "
                      f"{alv.max():,.0f}   real sits at "
                      f"{a['alive']['real_at']:.4f}")
                s_ = a["spread_over_floor"]
                print(f"         between-class spread of median |omega|, "
                      f"in floor units:")
                print(f"           across cuts  min {s_['min']:,.0f}   "
                      f"p50 {s_['p50']:,.0f}   max {s_['max']:,.0f}")
                print(f"           real grid    {s_['real']:,.0f}   sits at "
                      f"{a['spread']['real_at']:.4f}   "
                      f"({a['spread']['finite']:,} of {len(spr):,} cuts give a "
                      "finite spread)")
                if a["spread"]["min"] > 0:
                    print(f"           max / min across cuts = "
                          f"{a['spread']['max'] / a['spread']['min']:.2f}x"
                          "   <- this is the answer: how far the reading moves "
                          "when the cut moves")
                print()
            recs.append(rec)
        finally:
            c.close()
    RESULTS.mkdir(parents=True, exist_ok=True)
    full = sorted(FLOOR)
    name = ("b12_ladder.json" if sorted(archives) == full
            else "b12_ladder.offparam_" + "_".join(sorted(archives)) + ".json")
    out = RESULTS / name
    out.write_text(json.dumps(
        {"stage": "B12", "step": "ladder_enumeration", "diagnostic_only": True,
         "diagnostic_reason":
             "Enumeration over threshold cuts of the delinquency ladder, "
             "opened after the permutation route was found capped by the "
             "construction. The station is not closed and no criterion has "
             "been pinned on the spread yet.",
         "bins": LADDER_BINS, "min_cycles": MIN_CYCLES, "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.relative_to(ROOT)}\n")
    return 0


def spread_iqr(values):
    v = np.asarray(values, dtype=float)
    if v.size < 2:
        return float("nan")
    q = np.percentile(v, [25, 75])
    return float(q[1] - q[0])


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------"""

def cmd_gate(archive: str) -> int:
    print(f"\n  B12 gates on {archive}. Nothing is estimated here and no file "
          "is written.\n")
    bad_const = print_constants()

    pos, tab = LO.curve_table()
    c = K.Core(archive, cols=LO.COLS)
    try:
        lp = L.find_loops(c)
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        sums = LO.loop_sums(lp, r, ok)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])
        length = (np.asarray(lp["t_B"]).astype(np.int64)
                  - np.asarray(lp["t_A"]).astype(np.int64))

        walks, tally = raw_walks(c, lp)
        print(f"  loops {arm.size:,}   measurable {int(meas.sum()):,}   "
              f"walk assembly counts {dict(tally) or '{}'}")
        print(f"  rows carrying a delinquency code above 98 and below the "
              f"sentinels: {anchor_states.last_beyond_98:,}"
              "   (zero on the vintage the class counts are pinned to)\n")

        raw_labels = set()
        for w in walks:
            raw_labels.update(w)
        print(f"  {len(raw_labels)} distinct raw labels appear in the walks\n")

        red, drops = {}, {}
        for g in LADDER:
            gf = dict(fr.GRIDS)[g]
            red[g], drops[g] = reduce_on(walks, gf)
        print("  states dropped by each grid (a dropped state is a lost edge, "
              "and a lost edge raises H1 rather than lowering it):")
        for g in LADDER:
            print(f"    {g:<4} {drops[g]:,}")
        odd = [(g, i, red[g][i]) for g in LADDER
               for i in range(len(walks))
               if len(red[g][i]) not in (1,) and len(red[g][i]) < 4]
        print(f"  reduced words of forbidden length: {len(odd)}   "
              f"{'ok' if not odd else 'FAIL, defect here'}\n")

        maps = {}
        for fine, coarse in PAIRS:
            gf_f, gf_c = dict(fr.GRIDS)[fine], dict(fr.GRIDS)[coarse]
            f, clash = vertex_map(gf_f, gf_c, raw_labels)
            maps[(fine, coarse)] = f
            print(f"  f : {fine} -> {coarse}   {len(f)} vertices  "
                  f"{'well defined' if not clash else 'NOT A MAP'}")
            for s, a, b1, b2 in clash:
                print(f"      raw {s!r}: {fine} gives {a!r}, coarse gives both "
                      f"{b1!r} and {b2!r}")
            print("      " + ", ".join(f"{k}->{v}" for k, v in sorted(f.items())))
        print()

        commutes = gate_commutes(red, walks, maps)
        passed, _ = gate_0b(red, meas, arm, walks)
        gate_0a(red, meas, arm, length, maps)

        print("=" * 78)
        print("  gate summary")
        print(f"    constants confirmed against source   "
              f"{'yes' if not bad_const else 'no, ' + str(bad_const) + ' off'}")
        print(f"    relabel/reduce commute               "
              f"{'yes' if commutes else 'NO'}")
        print(f"    B12-0b exact reproduction            "
              f"{'yes' if passed else 'NO'}")
        print("    B12-0a is descriptive: read the two tables above, they "
              "decide which pairs get reported apart.")
        print("=" * 78 + "\n")
        return 0 if (passed and commutes) else 1
    finally:
        c.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true",
                    help="B12-0a and B12-0b. Prints, writes nothing.")
    ap.add_argument("--archive", default=GATE_ARCHIVE,
                    help="vintage for the gates. The registered one is "
                         f"{GATE_ARCHIVE}; the target counts are its.")
    ap.add_argument("--floor", action="store_true",
                    help="does N depend on the window length. Prints, writes "
                         "nothing.")
    ap.add_argument("--only", nargs="*", default=None,
                    help="vintages for --floor. Default: all six.")
    ap.add_argument("--run", action="store_true",
                    help="B12-A on the one live pair. Writes "
                         "results/b12_pullback.json, diagnostic_only.")
    ap.add_argument("--ladder", action="store_true",
                    help="B12-D: enumerate every threshold cut of the "
                         "delinquency ladder and print the spread.")
    ap.add_argument("--perm", action="store_true",
                    help="B12-C: the permutation criterion on g0m -> g2.")
    ap.add_argument("--null", nargs="*", default=list(NULL_CLASSES),
                    choices=list(NULL_CLASSES),
                    help="comparison classes for --perm.")
    ap.add_argument("--draws", type=int, default=N_PERM,
                    help=f"draws for --perm. Registered value {N_PERM}; "
                         "anything else writes an off-parameter record.")
    ap.add_argument("--placebo", action="store_true",
                    help="superseded by --perm, which is the same construction "
                         "promoted to the main criterion.")
    a = ap.parse_args(argv)
    if a.placebo:
        print("  superseded. The size-preserving relabel is now the main "
              "criterion; use --perm.")
        return 2
    if a.ladder:
        return cmd_ladder(a.only or sorted(FLOOR))
    if a.perm:
        return cmd_perm(a.only or sorted(FLOOR), a.draws, a.null)
    if a.run:
        return cmd_run(a.only or sorted(FLOOR))
    if a.floor:
        return cmd_floor(a.only or sorted(FLOOR))
    if not a.gate:
        ap.print_help()
        return 2
    return cmd_gate(a.archive)


if __name__ == "__main__":
    raise SystemExit(main())
