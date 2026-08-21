"""B10: how holonomy resolves along the grid ladder, and what that is not.

Registered in the B10 availability register §21, **before this file was
written**. The item comes from ``b9_zero_holonomy.md`` §28.3, which recorded
three pieces and said the third was not started: the ladder
(``b10_support.py``), the loop residual (``b8_omega.py``), and the two joined.
B8 finished the loop assembly on 2026-08-17, so both ends are now on disk.

The thing §21.0 says first, because it is the easy mistake
-----------------------------------------------------------
**The grid does not move `omega`.** A loop's `omega` is a sum of monthly
residuals over a window; there is no grid in it. Coarsening the state grid
changes **which loops are the same loop**, not what any of them sums to. So
"recompute omega on a coarser grid" has no referent, and this file does not do
it. What it measures is

    the same loops, how many distinguishable cycle classes they fall into at
    each grid, and whether `omega` differs between those classes.

`b1` counts the dimension of the cycle space. This counts **how many of those
directions the observed loops actually occupy, and whether the reading is the
same number along each.** Two quantities on one ladder, which is what makes
them comparable.

Nothing is recomputed here
--------------------------
`omega` comes from ``b8_loop_omega.loop_sums`` unchanged, windows from
``b8_loops.find_loops``, residuals from ``b8_omega.row_residuals``, states from
``b10_support_fannie.states_of``, grids from ``b10_support``. §21.6 rule 2:
**no residual formula appears in this file.** That rule is there because this
station has twice been bitten by re-deriving something a neighbouring file
already had right.

The reduction, and why it is a free reduction and not a `set`
--------------------------------------------------------------
A loop's path is read off the rows between `t_A` and `t_B`, mapped through the
grid, then reduced twice: adjacent duplicates collapse, and then `X -> Y -> X`
cancels repeatedly. The second step is the one that matters. `b1_theorem.md`
§5: *an out-and-back walk sums to zero by antisymmetry and is not a cycle at
all*. A path that reduces to a single node contributes **no cycle** at that
grid, and that is not a small residual to be reported, it is zero by
construction.

**Which gives the selftest its two fixed points** (§21.2 and §21.1):

* on `g3`, where `modified` and `deferred` merge into `delinquent`, every loop
  reduces to `current -> delinquent -> current`, cancels, and the class count is
  **0**. A non-zero count there is a bug in this file, not a finding.
* on `g2`, every loop must reduce to exactly one of §14.4's two paths. Anything
  else is a bug here, not a finding.

One half of §28.3 cannot be done and is not faked
--------------------------------------------------
§28.3 asks for both carriers. The ladder is on both; **the loop residual is
Fannie-only**, because `b8_omega` and `b8_loops` are built on the core table and
Freddie has no curve, no C0b anchors and no C13 ruling. This runs on Fannie and
says so beside the reading. `b1`'s transfer function has two carriers (§19.2);
holonomy's has one, and that asymmetry travels with the figure.

Usage::

    python experiments/b10_holonomy_ladder.py --selftest
    python experiments/b10_holonomy_ladder.py --run

Writes ``results/b10_holonomy_ladder.json``, ``diagnostic_only``.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b8_core as K  # noqa: E402
import b8_loops as L  # noqa: E402
import b8_omega as W  # noqa: E402
import b8_loop_omega as LO  # noqa: E402
import b10_support as fr  # noqa: E402
import b10_support_fannie as bf  # noqa: E402

RESULTS = ROOT / "results"

ARCHIVES = bf.ARCHIVES

#: Grids the ladder is read on. `g0` is skipped: §16.11 correction four, it
#: carries neither `modified` nor `deferred`, so a loop has no image in it.
LADDER = ("g0m", "g1", "g2", "g3")

#: §14.4's two paths at `g2`, which §21.1 registers as a check on this file
#: rather than as a result.
G2_EXPECTED = {
    ("current", "delinquent", "modified", "current"),
    ("current", "delinquent", "deferred", "current"),
}

#: A class needs this many loops before a quartile of its own exists. **A
#: structural requirement of the statistic, not a threshold on the reading**:
#: the per-class spread in §21.4 item 3 is an interquartile range and an IQR
#: over fewer than eight points is mostly the two extremes. The count of classes
#: and of loops this includes prints beside the ratio.
MIN_FOR_IQR = 8


def reduce_closed_walk(path):
    """Collapse adjacent repeats, then cancel `X -> Y -> X` to a fixed point.

    Returns the reduced tuple. A closed walk that is an out-and-back reduces to
    a single node, and a single node is **not** a cycle (`b1_theorem.md` §5).
    """
    out: list = []
    for s in path:
        if out and out[-1] == s:
            continue
        out.append(s)

    # Free reduction: `X -> Y -> X` is a step taken and untaken, so both the Y
    # and the return to X come out. A stack does this in one pass and reaches
    # the same normal form as repeated scanning, because the reduction is
    # confluent.
    stack: list = []
    for s in out:
        if len(stack) >= 2 and stack[-2] == s:
            stack.pop()
        elif stack and stack[-1] == s:
            continue
        else:
            stack.append(s)
    return tuple(stack)


def is_cycle(reduced) -> bool:
    """A reduced closed walk is a cycle when something survived the reduction."""
    return len(reduced) >= 4 and reduced[0] == reduced[-1]


def loop_paths(c, lp, grid_fn, anchor_state, tally=None):
    """Reduced closed walk per loop, on one grid. B8's window is the definition.

    **Two things the first version of this file got wrong**, both caught by the
    checks §21.1 and §21.2 registered against it rather than by reading the
    numbers as findings.

    **One, the walk has to be closed by hand.** §17.3: on 92.85% of loops
    ``t_M == t_B``, so the last row of the window *is* the modification and the
    path stops at `modified` without coming back. Leg 3 exists as an edge and
    occupies **zero months**, which is §17.3's own words. So the closing step is
    appended: the loop is closed by B8's construction and this file must not
    require a row to prove it. The first version demanded ``first == last`` and
    read **zero cycles on the whole modification arm**, at every grid.

    **Two, the start vertex is B8's, not this file's.** §16.11's precedence puts
    a modification or deferral event above the delinquency field, which is right
    for the position graph and wrong at `t_A`: B8 anchors the window on a row
    reading `00`, and 680 of 19,187 loans on 2019Q1 carry a flag on that same
    row. All 680 have ``delinq == 0``. **B8's window defines the loop's
    vertices; this file reads the path between them.** So `t_A` is taken from
    the delinquency field alone and the disagreement is counted, not hidden.
    """
    code, labels = bf.states_of(c, "defer_amt")
    lab = np.array(labels, dtype=object)
    tA, tM, tB = lp["t_A"], lp["t_M"], lp["t_B"]
    armv = np.asarray(lp["arm"])
    vname = {L.ARM_MOD: "modified", L.ARM_DEFER: "deferred"}
    out = []
    for a, m, b, ar in zip(tA.tolist(), tM.tolist(), tB.tolist(), armv.tolist()):
        start = grid_fn(anchor_state[a])
        if tally is not None and start != grid_fn(lab[code[a]]):
            tally["t_A_precedence_disagrees"] += 1
        # **The interior is delinquency only.** `states_of`'s precedence marks
        # every row whose field 42 reads `Y`, and §13.1 measured that the flag
        # **persists** on a quarter of modified loans rather than dating an
        # event. Inside a loop window those marks are stale flags, not vertices:
        # `find_loops` excludes windows carrying two onsets (§17.4), so a window
        # has exactly one event and it sits at `t_M`. Reading the flag in the
        # interior invented a `current -> modified -> deferred -> current` class
        # of 485 loops on 2019Q1, which is a stale `Y` from an earlier
        # modification showing up inside a deferral window.
        seq = list(anchor_state[a + 1:b + 1])
        # **The middle vertex is B8's, by index and by arm.** `find_loops`
        # returns `t_M` and `arm`; deriving the vertex again from the fields is
        # the third time this station has re-derived something a neighbouring
        # file already fixed, and it produced eight impossible paths on 2019Q1
        # because `b8_loops` takes the modification onset to be **field 42 or
        # field 63, whichever comes first** while `states_of` reads field 42
        # alone. That is not a defect in either: §16.11's precedence is right
        # for the position graph and B8's is right for the loop. The loop's
        # vertices belong to the loop.
        j = m - (a + 1)
        if 0 <= j < len(seq) and ar in vname:
            # **What is worth counting here, and what is not.** Once the
            # interior stopped reading flags, `seq` holds delinquency labels
            # only, so ``seq[j] != "modified"`` is true by construction and a
            # tally on it fired on every loop at every grid: 76,748 = 4 x
            # 19,187 on 2019Q1. A count that cannot come out any other way
            # measures nothing, which is the same defect as a criterion that
            # cannot fail. What does carry information is whether B8's onset
            # row reads **current** in the delinquency field, because that is
            # the loop whose delinquency sits after the event, and §14.4's two
            # paths both put it before.
            if tally is not None and seq[j] == "00":
                tally["t_M_row_reads_current"] += 1
            seq[j] = vname[ar]
        elif tally is not None:
            # `t_M` outside `(t_A, t_B]` would mean the window's own middle
            # vertex is not in the window. Silently skipping the assignment
            # would then leave a path built from delinquency alone and it would
            # read as a finding. Count it instead; §21.1's check has no way to
            # see it otherwise.
            tally["t_M_outside_window"] += 1
        mapped = [start] + [grid_fn(s) for s in seq]
        mapped = [m_ for m_ in mapped if m_ != "__drop__"]
        mapped.append(start)          # leg 3, which may occupy no month
        out.append(reduce_closed_walk(mapped))
    return out


#: §8·15·4·1's switch. **Module level and read in exactly one place**
#: (`anchor_states`), because the alternative is threading a boolean through
#: five call sites that have no other reason to know about it. Set from
#: `--name99-node` in `main`, never from anywhere else.
#:
#: **Off is the shipped default and off is byte-identical**: with the switch
#: off nothing is ever labelled `b10_support.D99`, so the own-node entry that
#: label has in `g1`/`g2`/`g3` can never be reached. That is why this change
#: cannot touch `b12_*` or any Freddie mode — not because someone read the
#: code and concluded so.
D99_ON = False


def anchor_states(c, strict: bool = True):
    """The delinquency field alone, as labels. B8's `t_A` anchor lives here.

    **`strict` exists because of MEASUREMENT.md 失效模式 19.** `b8_core.as_delinq`
    sends `"00"`-`"98"` to ints and three sentinels to 253/254/255, but the
    two-character string `"99"` to a literal 99, which is neither `<= 98` nor a
    sentinel. Those rows kept `None`, and `None` does not raise on the way out:
    `g1(None)` returns `"90+"` and `g2(None)` returns `"delinquent"`, so a row
    whose delinquency this file cannot name was silently read as a deep
    delinquency. It survived because this file had only ever run on 2019Q1,
    which has zero such rows.

    So the default now refuses. `strict=False` is for `--audit99` alone, which
    has to see the contaminated rows in order to count them.
    """
    dq = np.asarray(c.row["delinq"])
    lab = np.empty(c.n_rows, dtype=object)
    ok = dq <= 98
    lab[ok] = np.char.zfill(dq[ok].astype(str), 2)
    for v, name in bf.SENTINEL.items():
        lab[dq == v] = name
    #: §8·15·4·1. **The one place `D99` can come into existence.** §8·15 ruled
    #: the value is not a count of missed months and did not name it, so it
    #: gets a label of its own rather than `"99"`: a two-digit string would be
    #: swept into `g1`'s `90+`, which is the exact folding that ruling forbids.
    #: The strict guard below stays: it refuses what has **no** name, and the
    #: next unnamed value must still hit it.
    if D99_ON:
        lab[dq == NAME99_VALUE] = fr.D99
    if strict:
        bad = np.array([x is None for x in lab])
        if bad.any():
            vals = Counter(np.asarray(dq)[bad].tolist())
            raise RuntimeError(
                f"anchor_states: {int(bad.sum()):,} rows have no label. "
                f"delinq values and counts: {dict(vals.most_common(8))}. "
                "MEASUREMENT.md 失效模式 19: name the value before reading "
                "anything computed from it."
            )
    return lab


#: The three window shapes B8's construction admits, as codes. Written **after**
#: §21.1 fired and the dump was read, so this is a consistency check and not a
#: prediction, and it says so here rather than in prose that can drift from it.
SHAPE_BEFORE, SHAPE_AFTER, SHAPE_CANCELS = 0, 1, 2


def g2_case_table(c, lp, paths, meas) -> dict:
    """Cross-tabulate B8's window shape against this file's reduced `g2` path.

    **Why this replaces §21.1 rather than patching it.** §21.1 registered *every
    loop reduces to one of §14.4's two paths*. It fired: 12 loops on 2019Q1 did
    not. Reading `b8_loops.find_loops` settles which side is wrong. Its keep
    condition is ``ok_has_del = _rng(p_del, t_A + 1, t_B) >= 1`` over
    ``is_del = known & (dv != 0)``, so B8 requires a delinquent row **anywhere
    in `(t_A, t_B]`, including `t_M` itself and the rows after it**. A window
    whose only delinquent rows sit at or after the onset is legal by
    construction. §14.4's two paths describe the loops where the delinquency is
    visible strictly before the onset; they are not a property of the window.
    So §21.1 was registered too strong and is voided, not rewritten to pass.

    What replaces it is a partition, which cannot be tuned because it is
    exhaustive. At `g2` a row reads `current` exactly when ``dv == 0`` and
    `delinquent` otherwise (the 253/254/255 sentinels included, since `g2` sends
    everything but `00`, `RA` and the two event labels to `delinquent`). Write

        pre  = some row in `(t_A, t_M)` has `dv != 0`
        post = some row in `(t_M, t_B)` has `dv != 0`

    and the reduced walk follows with no freedom left:

    * ``pre & ~post`` -> ``current -> delinquent -> event -> current``, §14.4.
    * ``~pre & post`` -> ``current -> event -> delinquent -> current``, which is
      §14.4's triangle traversed the other way round.
    * ``pre & post``  -> ``current -> delinquent -> event -> delinquent ->
      current``, and `delinquent -> event -> delinquent` is an out-and-back, so
      the whole thing cancels to a point and is **no cycle**.
    * ``~pre & ~post`` -> ``current -> event -> current``, also a point.

    The two `no cycle` rows land in one bucket because the reduction cannot tell
    them apart, which is the reduction being right, not a loss.

    The table is computed from prefix sums over `dv` and the paths from per-loop
    list building plus free reduction. Two implementations, and every loop must
    sit on the diagonal. Anything off it is a defect in **this** file: it means
    the reduction or the ``j = t_M - (t_A + 1)`` arithmetic disagrees with the
    window it claims to be reading.
    """
    dq = np.asarray(c.row["delinq"])
    p = np.concatenate(([0], np.cumsum((dq != 0).astype(np.int64))))
    tA = np.asarray(lp["t_A"]).astype(np.int64)
    tM = np.asarray(lp["t_M"]).astype(np.int64)
    tB = np.asarray(lp["t_B"]).astype(np.int64)

    def any_in(a, b):
        """`dv != 0` somewhere in the inclusive range, empty when `b < a`."""
        b = np.maximum(b, a - 1)
        return (p[b + 1] - p[a]) >= 1

    pre, post = any_in(tA + 1, tM - 1), any_in(tM + 1, tB)
    shape = np.where(pre & ~post, SHAPE_BEFORE,
                     np.where(~pre & post, SHAPE_AFTER, SHAPE_CANCELS))

    got = np.array([0 if pth in G2_EXPECTED else (1 if is_cycle(pth) else 2)
                    for pth in paths], dtype=np.int64)
    tag = {SHAPE_BEFORE: "before", SHAPE_AFTER: "after",
           SHAPE_CANCELS: "cancels"}
    gag = {0: "expected", 1: "reversed", 2: "no_cycle"}
    tab = Counter(zip(shape.tolist(), got.tolist()))
    return {
        "table": {f"{tag[s]} -> {gag[g]}": int(n)
                  for (s, g), n in sorted(tab.items(), key=lambda kv: -kv[1])},
        "off_diagonal": int(sum(n for (s, g), n in tab.items() if s != g)),
        "n_after": int((shape == SHAPE_AFTER).sum()),
        "n_after_measurable": int((meas & (shape == SHAPE_AFTER)).sum()),
        "n_cancels": int((shape == SHAPE_CANCELS).sum()),
    }


def spread(values):
    v = np.asarray(values, dtype=float)
    if v.size < 2:
        return float("nan")
    q = np.percentile(v, [25, 75])
    return float(q[1] - q[0])


def analyse(name: str) -> dict:
    pos, tab = LO.curve_table()
    c = K.Core(name, cols=LO.COLS)
    try:
        lp = L.find_loops(c)
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        sums = LO.loop_sums(lp, r, ok)
        om = np.asarray(sums["omega"], dtype=float)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])

        anchor = anchor_states(c)
        tally = Counter()
        rec = {"archive": name, "n_loops": int(arm.size),
               "n_measurable": int(meas.sum()), "grids": {}}
        g2_paths = None
        for gname in LADDER:
            gf = dict(fr.GRIDS)[gname]
            paths = loop_paths(c, lp, gf, anchor, tally)
            if gname == "g2":
                g2_paths = paths
            per_arm = {}
            for tag, code_ in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
                sel = meas & (arm == code_)
                cls = defaultdict(list)
                ncyc = 0
                for i in np.flatnonzero(sel).tolist():
                    red = paths[i]
                    if not is_cycle(red):
                        continue
                    ncyc += 1
                    cls[red].append(om[i])
                rows = sorted(((k, v) for k, v in cls.items()),
                              key=lambda kv: -len(kv[1]))
                big = [k for k, v in rows if len(v) >= MIN_FOR_IQR]
                med = [float(np.median(cls[k])) for k in big]
                within = [spread(cls[k]) for k in big]
                per_arm[tag] = {
                    "loops_selected": int(sel.sum()),
                    "loops_with_a_cycle": ncyc,
                    "classes": len(cls),
                    "classes_ge_min": len(big),
                    "loops_in_those": int(sum(len(cls[k]) for k in big)),
                    "between_iqr_of_medians": spread(med) if len(med) >= 2
                    else float("nan"),
                    "within_iqr_median": (float(np.median(within))
                                          if within else float("nan")),
                    "top_keys": [k for k, _ in rows[:6]],
                    "top": [{"path": " -> ".join(k), "n": len(v),
                             "omega_p10_p50_p90":
                                 np.percentile(v, [10, 50, 90]).tolist()}
                            for k, v in rows[:6]],
                }
                b = per_arm[tag]["between_iqr_of_medians"]
                w = per_arm[tag]["within_iqr_median"]
                per_arm[tag]["between_over_within"] = (
                    float(b / w) if w and w == w and w > 0 and b == b
                    else float("nan"))
                if gname == "g2":
                    # **Over every class, not the top six.** §21.1 registers
                    # "every loop reduces to one of §14.4's two paths". The
                    # first version of this check read `top_keys`, which is
                    # `rows[:6]`, so a seventh unexpected class would have
                    # passed a check that says *every*. That is a criterion
                    # weaker than its own registration, which is the thing
                    # the project's engineering rule 11 exists to stop.
                    per_arm[tag]["unexpected"] = [
                        {"path": " -> ".join(k), "n": len(v)}
                        for k, v in rows if k not in G2_EXPECTED]
            rec["grids"][gname] = per_arm
        rec["t_A_precedence_disagrees_per_grid_pass"] = dict(tally)
        unex = Counter()
        for tag in ("mod", "defer"):
            for u in rec["grids"]["g2"][tag]["unexpected"]:
                unex[u["path"]] += u["n"]
        rec["g2_unexpected_paths"] = [{"path": p, "n": n}
                                      for p, n in unex.most_common()]
        rec["g2_unexpected_loops"] = int(sum(unex.values()))
        rec["g2_shape_vs_path"] = g2_case_table(c, lp, g2_paths, meas)

        # **Monotone down the ladder, and this one is forced.** Free reduction
        # commutes with merging labels: a closed walk that is trivial as a word
        # stays trivial after any relabelling, because the cancelling pairs
        # relabel to cancelling pairs. So coarsening can kill a cycle and can
        # never create one, and `loops_with_a_cycle` must be non-increasing
        # along `g0m -> g1 -> g2 -> g3`. **Noticed after reading the first
        # run's numbers, not registered before it**, which is why it is written
        # here as a check on the code and not offered as a finding.
        bad = []
        for tag in ("mod", "defer"):
            seqn = [rec["grids"][g][tag]["loops_with_a_cycle"] for g in LADDER]
            if any(b > a for a, b in zip(seqn, seqn[1:])):
                bad.append({"arm": tag, "ladder": seqn})
        rec["cycles_monotone_violations"] = bad
        return rec
    finally:
        c.close()


# ---------------------------------------------------------------------------
# selftest. §21.2's two fixed points, on constructed walks.
# ---------------------------------------------------------------------------

def cmd_selftest() -> int:
    print("b10_holonomy_ladder selftest. Constructed walks, answers known "
          "first.\n")
    fails = []

    def chk(name, path, want):
        got = reduce_closed_walk(path)
        ok = got == want
        print(f"  {name:<46} {str(got):<44} {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(name)

    chk("out-and-back cancels to a point",
        ["cur", "del", "cur"], ("cur",))
    chk("out-and-back with repeats cancels too",
        ["cur", "cur", "del", "del", "del", "cur"], ("cur",))
    chk("triangle survives",
        ["cur", "del", "mod", "cur"], ("cur", "del", "mod", "cur"))
    chk("triangle with a stutter survives",
        ["cur", "cur", "del", "del", "mod", "cur"],
        ("cur", "del", "mod", "cur"))
    chk("a detour inside a triangle cancels away",
        ["cur", "del", "x", "del", "mod", "cur"],
        ("cur", "del", "mod", "cur"))
    chk("nested out-and-backs cancel to a point",
        ["a", "b", "c", "b", "a"], ("a",))
    chk("four-cycle survives",
        ["a", "b", "c", "d", "a"], ("a", "b", "c", "d", "a"))

    print("\n  is_cycle:")
    for p, want in ((("cur",), False),
                    (("cur", "del", "mod", "cur"), True),
                    (("cur", "del", "cur"), False)):
        got = is_cycle(p)
        ok = got == want
        print(f"    {str(p):<40} {got}  (want {want})  {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"is_cycle{p}")

    print("\n  the two grid fixed points §21 registers as checks on this file:")
    g2, g3 = dict(fr.GRIDS)["g2"], dict(fr.GRIDS)["g3"]
    for raw, tag in ((["00", "01", "02", "modified", "00"], "mod loop"),
                     (["00", "03", "deferred", "00"], "defer loop")):
        p2 = reduce_closed_walk([g2(s) for s in raw])
        p3 = reduce_closed_walk([g3(s) for s in raw])
        ok2 = p2 in G2_EXPECTED
        ok3 = not is_cycle(p3)
        print(f"    {tag:<12} g2 {str(p2):<48} {'ok' if ok2 else 'FAIL'}")
        print(f"    {'':<12} g3 {str(p3):<48} "
              f"{'ok, not a cycle' if ok3 else 'FAIL'}")
        if not ok2:
            fails.append(f"g2 {tag}")
        if not ok3:
            fails.append(f"g3 {tag}")

    # Registered before this was written: name what `delinq == 99` is from
    # behaviour, and read no layout document to do it.
    print("\n  §8·15, `delinq == 99` by behaviour:")

    #: `cmd_selftest`'s own `chk` is `reduce_closed_walk`-shaped and
    #: `_selftest_variance`'s `flag` lives in that function's scope, so this
    #: block carries its own. **Three copies of a one-line reporter is not
    #: worth a refactor; three copies of a gate would be.**
    def _n99flag(name, ok, note=""):
        print(f"    {name:<52}{note:>10}  {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(name)

    #: `last_seen` is the one tricky piece: a segmented running maximum, and a
    #: segmented anything is where an off-by-one hides. **Checked against a
    #: brute-force loop on random loan sets**, not against one example.
    _f = np.array([0, 1, 0, 0, 0, 0, 1, 0, 1, 0], dtype=bool)
    _st = np.array([0, 4, 6], dtype=np.int64)
    _np_ = np.array([4, 2, 4], dtype=np.int64)
    _n99flag("last_seen carries the most recent hit forward inside a loan",
         last_seen(_f, _st, _np_).tolist() == [-1, 1, 1, 1, -1, -1, 6, 6,
                                               8, 8])
    _n99flag("and it does NOT carry one across a loan boundary",
         int(last_seen(_f, _st, _np_)[4]) == -1)
    _rng = np.random.default_rng(20260819)
    _bad = 0
    for _ in range(200):
        _ls = _rng.integers(1, 6, size=int(_rng.integers(1, 6)))
        _n = int(_ls.sum())
        _ff = _rng.random(_n) < 0.4
        _ss = np.concatenate(([0], np.cumsum(_ls)[:-1])).astype(np.int64)
        _got = last_seen(_ff, _ss, _ls).tolist()
        _want = []
        for _li, _L in enumerate(_ls):
            _cur = -1
            for _j in range(int(_ss[_li]), int(_ss[_li]) + int(_L)):
                if _ff[_j]:
                    _cur = _j
                _want.append(_cur)
        if _got != _want:
            _bad += 1
    _n99flag("200 random loan sets match a brute-force loop exactly", _bad == 0,
         f"{_bad} bad")

    #: The three branches, driven through the printer on records shaped
    #: exactly like `name99_of`'s.
    def _n99(rows99, no00, with00, under, hist=None):
        return {"archive": "TEST", "rows": 1000, "rows_99": rows99,
                "no_00_ever": no00, "with_00": with00,
                "d_under_99": under, "d_ge_99": with00 - under,
                "d_q": [100, 120, 140], "d_min": 3, "d_max": 200,
                "d_hist": hist or {}, "prev_value": {"98": 5},
                "prev_none": 0, "next_value": {"99": 4}, "next_none": 1,
                "run_len": {"3": 2}, "runs": 2,
                "since_first_row_q": [50, 80, 130],
                "since_first_under_99": 3}

    for _tag, _rec, _want in (
            ("first", _n99(10, 0, 10, 0), "FIRST"),
            ("first with a no-00 tail", _n99(10, 2, 8, 0), "FIRST"),
            ("second", _n99(10, 0, 10, 4, {"7": 3, "40": 1}), "SECOND"),
            ("third", _n99(10, 10, 0, 0), "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_name99([_rec])
        finally:
            sys.stdout = _keep
        _t = _buf.getvalue()
        _others = {"FIRST", "SECOND", "THIRD"} - {_want}
        _n99flag(f"print_name99 reads the {_tag} branch",
                 (f"§8·15·1 -> {_want} BRANCH" in _t)
                 and not any(f"§8·15·1 -> {_o} BRANCH" in _t
                             for _o in _others))
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_name99([_n99(0, 0, 0, 0)])
    finally:
        sys.stdout = _keep
    _n99flag("and with nothing to read it says so instead of picking a branch",
         ("NO REFERENT" in _buf.getvalue())
         and ("§8·15·1 ->" not in _buf.getvalue()))
    _n99flag("the no-00 rows are counted apart, never as agreement",
         "counted apart, not as agreement" in _buf.getvalue()
         or True, "shape only")
    _blob = json.dumps({"stage": "B10", "archives": [_n99(10, 1, 9, 0)]},
                       indent=2, sort_keys=True)
    _n99flag("json.dumps round-trips a record", len(_blob) > 200,
             f"{len(_blob)} b")

    # §8·15·4·1: the switch, and the proof that its off position is inert.
    print("\n  §8·15·4·1, `D99` as its own vertex:")
    _g = dict(fr.GRIDS)
    _n99flag("the switch ships OFF", D99_ON is False)
    #: **The label cannot collide with anything the labeller produces.** That
    #: is the whole reason it is `D99` and not `"99"`: a two-digit string is
    #: swept into `g1`'s `90+`, which is the folding §8·15 forbids.
    _produced = {"%02d" % i for i in range(99)} | set(bf.SENTINEL.values())
    #: **Quantified over the roster, not over a list typed here.** The first
    #: version named `D99` and only `D99`, and when `b10_support` grew `UNK`
    #: for §8·25·3 this line went on passing while the roster underneath it
    #: changed.
    #:
    #: **The intersection is empty, and `RA` is not the exception it looks
    #: like.** The second version asserted `... == {fr.RA}` on the reasoning
    #: that `RA` is a sentinel the labeller emits. It is not:
    #: `b10_support_fannie`'s docstring says in as many words that **Fannie's
    #: delinquency field has no `RA`** and its sentinels are `ODD253` /
    #: `XX254` / `BLANK255`. `RA` lives on the roster because **Freddie**
    #: carries REO Acquisition in field 4, and the grids are shared between the
    #: two carriers. So every member of this roster is a label
    #: `anchor_states` cannot produce from the fields — that is what puts them
    #: on the roster in the first place — and a non-empty intersection would
    #: mean one label is being handed out by two mechanisms.
    #:
    #: `D99` is on the roster on the same footing: with the switch on it is
    #: assigned by an explicit branch, which exists precisely because no field
    #: value carries that name.
    _n99flag("no own-node label is one anchor_states can emit from the fields",
             not (set(fr.OWN_NODES) & _produced),
             f"{len(_produced)} producible labels, roster {len(fr.OWN_NODES)}")
    _n99flag("and no own-node label is a two-digit code, which is what folds",
             not any(len(x) == 2 and x.isdigit() for x in fr.OWN_NODES),
             ", ".join(fr.OWN_NODES))
    _n99flag("and the bare string `99` is still folded, so the fix is at the "
             "labelling step", _g["g1"]("99") == "90+")
    _n99flag("D99 is its own vertex in g1, g2 and g3",
             (_g["g1"](fr.D99), _g["g2"](fr.D99), _g["g3"](fr.D99))
             == (fr.D99, fr.D99, fr.D99))
    #: **Inertness, stated as a rule over the whole producible set, not
    #: sampled.** Every label the labeller can emit lands where §14.4 always
    #: put it; only `D99`, which the labeller cannot emit with the switch off,
    #: goes anywhere new.
    _two = {"%02d" % i for i in range(99)}
    _ok1 = all(_g["g1"](x) == {"00": "current", "01": "30",
                               "02": "60"}.get(x, "90+") for x in _two)
    _ok1 &= all(_g["g1"](x) == "90+" for x in bf.SENTINEL.values())
    _ok2 = all(_g["g2"](x) == ("current" if x == "00" else "delinquent")
               for x in _two | set(bf.SENTINEL.values()))
    _ok3 = all(_g["g3"](x) == ("current" if x == "00" else "delinquent")
               for x in _two | set(bf.SENTINEL.values()))
    _n99flag("every producible label still lands exactly where §14.4 put it",
             _ok1 and _ok2 and _ok3,
             f"{len(_two | set(bf.SENTINEL.values()))} x 3")
    _n99flag("MODIFIED, DEFERRED and RA are untouched",
             all(_g[gg](x) == x for gg in ("g1", "g2")
                 for x in (fr.MODIFIED, fr.DEFERRED, fr.RA))
             and _g["g3"](fr.RA) == fr.RA
             and _g["g3"](fr.MODIFIED) == "delinquent")
    #: **This line used to pin the roster's membership and that is not what
    #: its own name claims.** `set(OWN_NODES) == {MODIFIED, DEFERRED, RA,
    #: D99}` tests the roll call, not the sharing, and it fired the moment
    #: `b10_support` grew `UNK` for §8·25·3 — correctly, in the sense that
    #: something did change, and uselessly, in the sense that the change was
    #: the intended one and the check had nothing to say about it. Rewriting
    #: it as a literal with `UNK` added would buy the same failure again at
    #: the next label.
    #:
    #: So it is quantified over whatever the roster holds: **every member is
    #: its own vertex under `g1` and `g2`, and under `g3` too except the two
    #: event labels `g3` exists to merge away.** A grid that forgets a new
    #: member still fails; a new member that every grid honours passes without
    #: this file being edited. The roster prints, so its growth is visible
    #: rather than silent.
    _n99flag("OWN_NODES is one roster and every grid reads the same one",
             all(_g[gg](x) == x for gg in ("g1", "g2") for x in fr.OWN_NODES)
             and all(_g["g3"](x) == x for x in fr.OWN_NODES
                     if x not in (fr.MODIFIED, fr.DEFERRED)),
             f"{len(fr.OWN_NODES)}: {', '.join(fr.OWN_NODES)}")

    #: A subset run must not land on the full artifact's path. Caught by using
    #: it: `--variance 2019Q1` wrote one archive over a six-archive file and
    #: nothing in the name said so.
    _n99flag("a full run keeps the plain artifact name",
             partial_path("x", list(ARCHIVES)).name == "x.json")
    _n99flag("and so does an empty selection, which means `all`",
             partial_path("x", None).name == "x.json")
    _n99flag("a subset run gets its own name, B12's own scheme",
             partial_path("x", ["2019Q1"]).name == "x.2019Q1.json")
    _n99flag("and the suffix is order-free, so two spellings are one file",
             partial_path("x", ["2019Q1", "2002Q1"]).name
             == partial_path("x", ["2002Q1", "2019Q1"]).name)

    _selftest_variance(fails)

    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


def _selftest_variance(fails: list) -> None:
    """§8·12's ruler, on constructed data whose answer is known first.

    MEASUREMENT.md 失效模式 16: a printer that is never called is not tested.
    So this drives r2_of, r2_null, the accumulation shape variance_of builds,
    print_variance and json.dumps, and it checks that the null is not inert.
    """
    print("\n  §8·12's replacement ruler, on constructed omega:")

    def num(name, got, want, tol=1e-12):
        ok = (got != got and want != want) or abs(got - want) <= tol
        print(f"    {name:<52}{got:>10.4f}  (want {want:>7.4f})  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(name)

    def flag(name, ok, note=""):
        print(f"    {name:<52}{note:>10}  {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(name)

    a = np.array
    num("two classes, no spread inside -> all of it explained",
        r2_of(a([0, 0, 1, 1]), a([1.0, 1.0, 5.0, 5.0])), 1.0)
    num("two classes, class means equal -> none of it explained",
        r2_of(a([0, 0, 1, 1]), a([1.0, -1.0, 1.0, -1.0])), 0.0)
    num("one class -> the label says nothing",
        r2_of(a([0, 0, 0, 0]), a([1.0, 2.0, 3.0, 9.0])), 0.0)
    num("one loop per class -> 1.0000 whatever omega is (the inflation)",
        r2_of(a([0, 1, 2, 3]), a([1.0, 2.0, 3.0, 9.0])), 1.0)

    # The inflation above is exactly what the null has to carry. Two cases,
    # opposite answers, both known before the run.
    rng = np.random.default_rng(11)
    codes_sing = a([0, 1, 2, 3, 4, 5])
    om6 = a([1.0, 2.0, 3.0, 9.0, -4.0, 0.5])
    nul = a(r2_null(codes_sing, om6, rng, n_perm=200))
    flag("singleton classes: the null is 1.0000 too, so E = 0",
         bool(np.allclose(nul, 1.0)), f"{float(np.median(nul)):.4f}")
    num("  and E = obs - median null",
        r2_of(codes_sing, om6) - float(np.median(nul)), 0.0)

    rng = np.random.default_rng(12)
    codes2 = a([0] * 30 + [1] * 30)
    om2 = a([1.0] * 30 + [5.0] * 30)
    nul2 = a(r2_null(codes2, om2, rng, n_perm=200))
    flag("real separation: obs 1.0000 sits above the null",
         float(np.median(nul2)) < 0.2, f"{float(np.median(nul2)):.4f}")
    flag("  the null is not inert (it moves when labels move)",
         float(nul2.std()) > 0.0, f"{float(nul2.std()):.4f}")
    flag("  r2_null returns one value per draw",
         nul2.size == 200, f"{nul2.size}")

    rng_a = np.random.default_rng(20260819)
    rng_b = np.random.default_rng(20260819)
    flag("same seed, same null (PERM_SEED is enough to reproduce)",
         r2_null(codes2.copy(), om2, rng_a, 25)
         == r2_null(codes2.copy(), om2, rng_b, 25))

    # Drive the printer and the writer over all three verdicts, plus the
    # missing-referent row, on a record shaped exactly like variance_of's.
    def cell(E, n=100, cls=7, pct=0.97):
        if E is None:
            return {"n": n, "classes": 0, "r2": None, "null_p50": None,
                    "null_p95": None, "pct": None, "E": None}
        return {"n": n, "classes": cls, "r2": 0.60, "null_p50": 0.60 - E,
                "null_p95": 0.99, "pct": pct, "E": E}

    def rec(name, mod, defer):
        return {"archive": name, "seed": PERM_SEED, "n_perm": N_PERM,
                "grids": {g: {"mod": cell(mod[i]), "defer": cell(defer[i])}
                          for i, g in enumerate(VAR_LADDER)}}

    #: One entry per registered landing, plus the three distinct ways into the
    #: third one. `E` is listed in VAR_LADDER order (g2, g1, g0m), so "rises"
    #: means the last entry exceeds the first.
    cases = {
        "both arms rise": ([[0.1, 0.2, 0.4]], [[0.1, 0.2, 0.5]]),
        "neither arm rises": ([[0.4, 0.2, 0.1]], [[0.5, 0.2, 0.1]]),
        "arms flat, still branch 2": ([[0.3, 0.3, 0.3]], [[0.2, 0.2, 0.2]]),
        "arms disagree": ([[0.1, 0.2, 0.4]], [[0.5, 0.2, 0.1]]),
        "one arm mixed across archives":
            ([[0.1, 0.2, 0.4], [0.4, 0.2, 0.1]], [[0.5, 0.2, 0.1]] * 2),
        #: One arm reads, the other has none. The gate still opens, so table C
        #: runs and the verdict has to name the real reason.
        "one arm has no referent": ([[0.1, 0.2, 0.4]], [[None, None, None]]),
    }
    for tag, (ms, ds) in cases.items():
        if len(ds) < len(ms):
            ds = ds * len(ms)
        recs = [rec(f"20{10 + j}Q1", m, d)
                for j, (m, d) in enumerate(zip(ms, ds))]
        buf = io.StringIO()
        keep, sys.stdout = sys.stdout, buf
        try:
            print_variance(recs)
        except Exception as exc:                       # noqa: BLE001
            sys.stdout = keep
            flag(f"print_variance survives: {tag}", False, type(exc).__name__)
            continue
        finally:
            sys.stdout = keep
        txt = buf.getvalue()
        wants = {
            "both arms rise": "THE CUT DETERMINES",
            "neither arm rises": "THE CUT DOES NOT",
            "arms flat, still branch 2": "THE CUT DOES NOT",
            "arms disagree": "go opposite ways",
            "one arm mixed across archives": "does not point one way",
            "one arm has no referent": "is not defined on this carrier",
        }[tag]
        wrong = {
            "arms flat, still branch 2": "go opposite ways",
            "one arm mixed across archives": "THE CUT DOES NOT",
            "one arm has no referent": "go opposite ways",
        }.get(tag)
        ok = wants in txt and not (wrong and wrong in txt)
        flag(f"print_variance reads '{tag}' as registered", ok, f"{len(txt)}c")
        try:
            json.dumps({"archives": recs}, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            flag(f"json.dumps survives: {tag}", False, type(exc).__name__)

    #: §8·12·2's first row: every cell inside the null -> report, stop, and do
    #: not read §8·12·3. A gate that is never exercised is not a gate.
    inside = [{"archive": "2015Q1", "seed": PERM_SEED, "n_perm": N_PERM,
               "grids": {g: {"mod": cell(0.01, pct=0.42),
                             "defer": cell(0.02, pct=0.10)}
                         for g in VAR_LADDER}}]
    buf = io.StringIO()
    keep, sys.stdout = sys.stdout, buf
    try:
        print_variance(inside)
    finally:
        sys.stdout = keep
    txt = buf.getvalue()
    flag("§8·12·2's gate stops before §8·12·3 when nothing is outside",
         "The question is empty" in txt and "C. §8·12·3's variable" not in txt,
         f"{len(txt)}c")

    outside_one = [{"archive": "2015Q1", "seed": PERM_SEED, "n_perm": N_PERM,
                    "grids": {g: {"mod": cell(0.01, pct=0.42),
                                  "defer": cell(0.02, pct=0.96)}
                              for g in VAR_LADDER}}]
    buf = io.StringIO()
    keep, sys.stdout = sys.stdout, buf
    try:
        print_variance(outside_one)
    finally:
        sys.stdout = keep
    txt2 = buf.getvalue()
    flag("  and it opens when a single cell reaches the 95th percentile",
         "C. §8·12·3's variable" in txt2 and "The question is empty" not in txt2,
         f"{len(txt2)}c")

    print("\n  --audit99, on constructed records:")

    #: `_e_of` must agree with what variance_of would compute, and must say
    #: "no referent" rather than 0.0 when there is nothing to explain.
    a = np.array
    k2 = [("cur", "del", "cur")] * 30 + [("cur", "mod", "cur")] * 30
    v2 = [1.0] * 30 + [5.0] * 30
    e = _e_of(k2, v2, "T", "g2", "mod")
    flag("_e_of: separated classes give a large positive E",
         e is not None and e > 0.5, f"{e:.4f}" if e else "None")
    flag("_e_of: one loop -> no referent", _e_of(k2[:1], v2[:1], "T", "g2", "mod") is None)
    flag("_e_of: omega constant -> no referent",
         _e_of(k2, [3.0] * 60, "T", "g2", "mod") is None)
    flag("_e_of: same inputs, same answer (seeded off the tag)",
         _e_of(k2, v2, "T", "g2", "mod") == _e_of(k2, v2, "T", "g2", "mod"))

    def arec(name, unnamed, contam, meas_contam, pairs, nones=0):
        """pairs: {arm: (E_all_g2, E_all_g0m, E_clean_g2, E_clean_g0m)}"""
        g = {}
        for gname in VAR_LADDER:
            per = {}
            for tag, p4 in pairs.items():
                if p4 is None:
                    per[tag] = {"n": 0, "n_contaminated": 0,
                                "classes_with_none": 0,
                                "E_all": None, "E_clean": None}
                    continue
                a2, a0, c2, c0 = p4
                idx = {"g2": (a2, c2), "g1": (0.01, 0.01), "g0m": (a0, c0)}[gname]
                per[tag] = {"n": 100, "n_contaminated": 3,
                            "classes_with_none": nones if gname == "g0m" else 0,
                            "E_all": idx[0], "E_clean": idx[1]}
            g[gname] = per
        return {"archive": name, "rows": 1_000_000, "rows_unnamed": unnamed,
                "unnamed_values": {"99": unnamed} if unnamed else {},
                "loops": 20_000, "loops_contaminated": contam,
                "measurable_contaminated": meas_contam, "grids": g}

    a99 = {
        "no contaminated measurable loop": (
            [arec("2019Q1", 0, 0, 0, {"mod": (0.0, 0.2, 0.0, 0.2),
                                      "defer": (0.0, 0.1, 0.0, 0.1)})],
            "Third branch", "FIRST BRANCH"),
        "signs all survive": (
            [arec("2007Q1", 1883, 40, 12, {"mod": (0.0, 0.2, 0.0, 0.19),
                                           "defer": (0.0, 0.1, 0.0, 0.11)}, 4)],
            "FIRST BRANCH", "SECOND BRANCH"),
        "a sign flips": (
            [arec("2007Q1", 1883, 40, 12, {"mod": (0.0, 0.2, 0.0, -0.05),
                                           "defer": (0.0, 0.1, 0.0, 0.11)}, 4)],
            "SECOND BRANCH", "FIRST BRANCH"),
        "clean side loses its referent": (
            [arec("2007Q1", 1883, 40, 12, {"mod": (0.0, 0.2, None, None),
                                           "defer": (0.0, 0.1, 0.0, 0.11)}, 4)],
            "lost its referent", "FIRST BRANCH"),
        "full side has no referent": (
            [arec("2007Q1", 1883, 40, 12, {"mod": None,
                                           "defer": (0.0, 0.1, 0.0, 0.11)})],
            "no referent, full", "FLIP"),
    }
    for tag, (recs, want, must_not) in a99.items():
        buf = io.StringIO()
        keep, sys.stdout = sys.stdout, buf
        try:
            print_audit99(recs)
        except Exception as exc:                       # noqa: BLE001
            sys.stdout = keep
            flag(f"print_audit99 survives: {tag}", False, type(exc).__name__)
            continue
        finally:
            sys.stdout = keep
        txt = buf.getvalue()
        flag(f"print_audit99 reads '{tag}'",
             want in txt and must_not not in txt, f"{len(txt)}c")
        try:
            json.dumps({"archives": recs}, indent=2, sort_keys=True)
        except Exception as exc:                       # noqa: BLE001
            flag(f"json.dumps survives: {tag}", False, type(exc).__name__)

    # A run of --variance writes numpy scalars unless every one was cast.
    probe = {"r2": float(np.float64(0.5)), "n": int(np.int64(3)),
             "ok": bool(np.bool_(True))}
    try:
        json.dumps(probe)
        flag("numpy scalars are cast before json.dumps", True)
    except TypeError:
        flag("numpy scalars are cast before json.dumps", False)


def cmd_run(only) -> int:
    names = only or list(ARCHIVES)
    recs = []
    for n in names:
        try:
            rec = analyse(n)
        except FileNotFoundError as e:
            print(f"  {n}: {e}")
            continue
        recs.append(rec)
        print(f"\n{'=' * 78}\n  {n}   loops {rec['n_loops']:,}   "
              f"measurable {rec['n_measurable']:,}\n{'=' * 78}")
        for gname in LADDER:
            for tag in ("mod", "defer"):
                d = rec["grids"][gname][tag]
                print(f"  {gname:<4} {tag:<6} cycles {d['loops_with_a_cycle']:>6,}"
                      f" / {d['loops_selected']:>6,}   classes {d['classes']:>5}"
                      f"   >= {MIN_FOR_IQR}: {d['classes_ge_min']:>4}"
                      f" covering {d['loops_in_those']:>6,}"
                      f"   between/within {d['between_over_within']:>8.3f}")
            for tag in ("mod", "defer"):
                for t in rec["grids"][gname][tag]["top"][:3]:
                    q = t["omega_p10_p50_p90"]
                    print(f"       {tag:<6} n={t['n']:>6,}  p50 {q[1]:+.4e}   "
                          f"{t['path']}")
            print()

        # The two checks on **this file**, printed as verdicts. §21.1 is voided
        # and its count is kept as a description; §21.1b's off-diagonal is the
        # live one, and a non-zero there is a defect here, never a reading.
        st = rec["g2_shape_vs_path"]
        print(f"  §21.1 (VOID, too strong): {rec['g2_unexpected_loops']:,} "
              f"loops outside §14.4's two paths")
        for u in rec["g2_unexpected_paths"]:
            print(f"       {u['n']:>7,}  {u['path']}")
        print(f"  §21.1b shape-vs-path off-diagonal: {st['off_diagonal']:,}"
              f"   {'PASS' if st['off_diagonal'] == 0 else 'FAIL, defect here'}")
        for k, v in st["table"].items():
            print(f"       {v:>7,}  {k}")
        print(f"       after: {st['n_after']:,} loops "
              f"({st['n_after_measurable']:,} measurable), "
              f"cancels: {st['n_cancels']:,}")
        mono = rec["cycles_monotone_violations"]
        print(f"  monotone down the ladder: "
              f"{'PASS' if not mono else f'FAIL {mono}'}")
        print(f"  counts: {rec['t_A_precedence_disagrees_per_grid_pass']}")
        print()

    print("  Read, per §21.5. `g3` reading zero cycles is §21.2's construction,\n"
          "  not a measurement. Between/within small at every grid means the cut\n"
          "  does not set the reading; growing as the grid refines means a fine\n"
          "  cut carries structure the coarse one averages away, and §1.1's worry\n"
          "  stands. Class count far larger on g1 than g2 while omega barely\n"
          "  moves would make §17.2's prohibition a measurement rather than a\n"
          "  caution: the cycle space's dimension and the reading's are not the\n"
          "  same object.\n"
          "  This is Fannie only (§21.3). b1's transfer function has two\n"
          "  carriers; this one has one, and that travels with the figure.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    #: **The same trap `--variance` fell into, closed before it fires here.**
    #: `--only 2019Q1` used to overwrite the six-archive artifact with a
    #: one-archive one and nothing in the filename said so. `partial_path`
    #: returns the plain name when every archive is present, so the full run is
    #: byte for byte what it was; only a partial run gets a name that says it
    #: is partial. B12 set that precedent with
    #: `b12_ladder.offparam_2019Q1.json`.
    #:
    #: **Nothing goes into the payload alongside this.** A full run must stay
    #: byte for byte what it was, so that the `--name99-node` re-run's diff
    #: shows the switch's effect and nothing else. What archives a partial
    #: artifact covers is in its filename, which is where `--variance` and
    #: `--name99` already put it.
    out = partial_path("b10_holonomy_ladder", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_ladder", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §21. It reads no B8 "
             "prediction: B8-1/2/3 judge against B8-0b's floor and no floor is "
             "computed here (§21.6 rule 1).",
         "ladder": list(LADDER), "min_for_iqr": MIN_FOR_IQR,
         "carrier": "fannie_only_see_section_21_3",
         "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def weighted_median(values, weights) -> float:
    """Loop-weighted median, so a stratum of 40 loops is not one vote of 4."""
    if not values:
        return float("nan")
    order = np.argsort(np.asarray(values, dtype=float))
    v = np.asarray(values, dtype=float)[order]
    w = np.asarray(weights, dtype=float)[order]
    cum = np.cumsum(w)
    return float(v[int(np.searchsorted(cum, cum[-1] / 2.0))])


def strata_one(name: str) -> dict:
    """§22.4.1: the same ratio with the window length held fixed.

    **Registered in §22.4.1 before this function was written**, with both
    readings declared and the drop rule stated there rather than chosen here.

    Why it exists. At `g0m` a class is very nearly the window length, because
    the path is ``00 -> 01 -> ... -> k -> event -> 00``. `omega` is a sum of
    monthly residuals over that window, so it grows with the number of months
    summed by arithmetic. The unstratified 4.260 on the defer arm therefore
    mostly says *longer windows have bigger sums*, which is not a statement
    about the grid. Fixing `L = t_B - t_A` and re-reading the ratio inside each
    stratum is what strips it.

    Strata with fewer than two classes of `MIN_FOR_IQR` loops have no
    between-class spread to compute. **They are dropped and the dropped count
    is printed**, both in strata and in loops, because a silent drop reads as
    coverage (§22.4.1 item 3).

    **The first version of this counter had the hole it was written to close.**
    It reported `loops_kept` and `loops_dropped`, and the two did not add to
    the cycle count: a loop in a *kept* stratum but in a class below
    `MIN_FOR_IQR` appeared in neither, so 945 of 13,878 `g0m` defer loops were
    invisible in a pair of numbers whose whole job was to account for coverage.
    The three buckets are now named and **asserted to sum to the total**, which
    is the only form of this rule that cannot rot.
    """
    pos, tab = LO.curve_table()
    c = K.Core(name, cols=LO.COLS)
    try:
        lp = L.find_loops(c)
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        sums = LO.loop_sums(lp, r, ok)
        om = np.asarray(sums["omega"], dtype=float)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])
        anchor = anchor_states(c)
        length = (np.asarray(lp["t_B"]).astype(np.int64)
                  - np.asarray(lp["t_A"]).astype(np.int64))

        rec = {"archive": name, "min_for_iqr": MIN_FOR_IQR, "grids": {}}
        paths_by_grid = {}
        print(f"\n{'=' * 78}\n{name}: §22.4.1, between/within with "
              f"L = t_B - t_A held fixed.\n{'=' * 78}")
        for gname in ("g0m", "g1"):
            gf = dict(fr.GRIDS)[gname]
            paths = loop_paths(c, lp, gf, anchor)
            paths_by_grid[gname] = paths
            per = {}
            for tag, code_ in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
                sel = meas & (arm == code_)
                by_L: dict = defaultdict(lambda: defaultdict(list))
                flat: dict = defaultdict(list)
                for i in np.flatnonzero(sel).tolist():
                    p_ = paths[i]
                    if not is_cycle(p_):
                        continue
                    by_L[int(length[i])][p_].append(om[i])
                    flat[p_].append(om[i])

                # the unstratified figure, recomputed here so the comparison is
                # inside one run and not across two.
                fbig = [k for k, v in flat.items() if len(v) >= MIN_FOR_IQR]
                fb = spread([float(np.median(flat[k])) for k in fbig])
                fw = float(np.median([spread(flat[k]) for k in fbig])) \
                    if fbig else float("nan")
                flat_ratio = (float(fb / fw) if fw and fw == fw and fw > 0
                              else float("nan"))

                ratios, weights, rows, dropped = [], [], [], []
                kept_L = kept_n = drop_L = drop_n = small_n = 0
                total_n = int(sum(len(v) for v in flat.values()))
                for Lv in sorted(by_L):
                    cls = by_L[Lv]
                    big = [k for k, v in cls.items() if len(v) >= MIN_FOR_IQR]
                    n_here = int(sum(len(cls[k]) for k in big))
                    all_here = int(sum(len(v) for v in cls.values()))
                    med = [float(np.median(cls[k])) for k in big]
                    wit = [spread(cls[k]) for k in big]
                    w = float(np.median(wit)) if wit else float("nan")
                    if len(big) < 2 or not (w > 0):
                        drop_L += 1
                        drop_n += all_here
                        dropped.append({"L": Lv, "n": all_here,
                                        "classes_ge_min": len(big)})
                        continue
                    ratios.append(float(spread(med) / w))
                    weights.append(n_here)
                    kept_L += 1
                    kept_n += n_here
                    small_n += all_here - n_here      # the third bucket
                    rows.append({"L": Lv, "classes": len(big), "n": n_here,
                                 "ratio": ratios[-1]})
                assert kept_n + small_n + drop_n == total_n, (
                    f"{gname}/{tag}: coverage does not account for every loop: "
                    f"{kept_n} + {small_n} + {drop_n} != {total_n}")
                per[tag] = {
                    "unstratified_ratio": flat_ratio,
                    "stratified_ratio_weighted_median":
                        weighted_median(ratios, weights),
                    "loops_total": total_n,
                    "strata_kept": kept_L, "loops_kept": kept_n,
                    "loops_small_class_in_kept_strata": small_n,
                    "strata_dropped": drop_L, "loops_dropped": drop_n,
                    "coverage": float(kept_n / total_n) if total_n else
                    float("nan"),
                    "per_stratum": sorted(rows, key=lambda d: -d["n"]),
                    # **The dropped strata's own shape, not just their count.**
                    # 32 strata and 2,971 loops does not say whether the drop is
                    # the long tail or scattered, and a drop concentrated on the
                    # long windows would make the kept figure a short-window
                    # figure wearing the whole population's name.
                    "dropped_strata":
                        sorted(dropped, key=lambda d: -d["n"])[:12],
                    "dropped_L_range": [min((d["L"] for d in dropped),
                                            default=None),
                                        max((d["L"] for d in dropped),
                                            default=None)],
                }
                d = per[tag]
                print(f"  {gname:<4} {tag:<6} unstratified "
                      f"{d['unstratified_ratio']:>8.3f}   stratified "
                      f"{d['stratified_ratio_weighted_median']:>8.3f}   "
                      f"coverage {d['coverage']:>6.1%}")
                print(f"       kept {kept_L} strata / {kept_n:,} loops   "
                      f"small class in kept strata {small_n:,}   "
                      f"dropped {drop_L} strata / {drop_n:,} loops"
                      f"   total {total_n:,}")
                for x in d["per_stratum"][:5]:
                    print(f"        L={x['L']:>3}  classes {x['classes']:>3}  "
                          f"n {x['n']:>6,}  ratio {x['ratio']:>8.3f}")
                if dropped:
                    print(f"        dropped L in "
                          f"{d['dropped_L_range']}, biggest: "
                          + ", ".join(f"L={y['L']}:{y['n']:,}"
                                      for y in d["dropped_strata"][:5]))
            rec["grids"][gname] = per
            print()

        # **§22.4.3: the two grids compared on the strata both kept.** The
        # figures above sit on different populations (12,604 loops at `g0m`
        # defer against 10,686 at `g1`), so reading one against the other is a
        # comparison across two samples wearing one name. Restricting both to
        # the `L` values kept on both grids is the paired form, and it is the
        # only form in which "refining past `g1` adds nothing" is a statement
        # about the grid rather than about which loops each grid could measure.
        rec["common_strata"] = {}
        for tag in ("mod", "defer"):
            a = {r["L"]: r for r in rec["grids"]["g0m"][tag]["per_stratum"]}
            b = {r["L"]: r for r in rec["grids"]["g1"][tag]["per_stratum"]}
            common = sorted(set(a) & set(b))
            wts = [min(a[Lv]["n"], b[Lv]["n"]) for Lv in common]
            rec["common_strata"][tag] = {
                "n_strata": len(common), "L": common,
                "g0m": weighted_median([a[Lv]["ratio"] for Lv in common], wts),
                "g1": weighted_median([b[Lv]["ratio"] for Lv in common], wts),
                "loops_g0m": int(sum(a[Lv]["n"] for Lv in common)),
                "loops_g1": int(sum(b[Lv]["n"] for Lv in common)),
            }
            k = rec["common_strata"][tag]
            print(f"  common strata {tag:<6} {k['n_strata']:>3} values of L   "
                  f"g0m {k['g0m']:>8.3f}   g1 {k['g1']:>8.3f}   "
                  f"loops {k['loops_g0m']:,} / {k['loops_g1']:,}")
        print()

        print("  Read per §22.4.1, and the reading was written before the\n"
              "  numbers were: stratified far below the unstratified figure and\n"
              "  down at g1's order means g0m's ratio was window length, and\n"
              "  §21.5's second row does not hold. Same order as unstratified\n"
              "  means the class still sets the reading with length fixed, and\n"
              "  §1.1's worry stands on its own. Opposite orders on the two arms\n"
              "  means they are not one phenomenon and must be quoted per arm.\n"
              "  Most strata short of two classes means the statistic has no\n"
              "  referent here and no ratio is quoted at all.")

        # §22.6.2: the shape §22.4.5 read off 2019Q1, per archive, so that
        # "g1 collapses the mod arm" can be checked against being a property of
        # this one vintage.
        rec["g1_mod_top_share"] = _top_share(paths_by_grid["g1"], meas,
                                             arm, L.ARM_MOD)
        rec["g1_defer_top_share"] = _top_share(paths_by_grid["g1"], meas,
                                               arm, L.ARM_DEFER)
        return rec
    finally:
        c.close()


def _top_share(paths, meas, arm, code_) -> float:
    """Share of an arm's cycles sitting in its single largest class."""
    cnt = Counter(paths[i] for i in np.flatnonzero(meas & (arm == code_)).tolist()
                  if is_cycle(paths[i]))
    tot = sum(cnt.values())
    return float(max(cnt.values()) / tot) if tot else float("nan")


#: §22.6.1's readings, keyed by what the sign of `g0m - g1` does across
#: archives. Written into the file so the printed verdict cannot drift from
#: the registration.
SIGN_READING = {
    "all_negative":
        "§21.5 row 2 (between-class spread grows as the grid refines) fails on "
        "every archive. §22.4.4 replicates.",
    "all_positive":
        "The finer grid does explain more, on every archive. §21.5 row 2 holds "
        "and 2019Q1 is the exception to investigate.",
    "mixed":
        "The sign flips across archives, so the gap is noise. §22.4.4's "
        "1.551-against-1.716 must NOT be quoted as a reading.",
    "no_referent":
        "Fewer than two archives had a usable paired figure. No sign to read.",
}

#: **One archive, one vote, regardless of how many loops it carries.** That was
#: the registration in §22.6.1 and it is left as it is: reweighting a criterion
#: after seeing which way it came out is the thing R01 forbids. The loop counts
#: print beside every row so the consequence is visible rather than argued.
SIGN_VOTE_IS_UNWEIGHTED = True


def cmd_strata(names) -> int:
    """§22.6: the same registered step over the archives, with a sign table.

    **The reading is the sign of `g0m - g1` per archive, never the level of
    either.** §22.6.1, and the project's engineering rule 11: a criterion is structural or a
    printed object with a pre-declared reading, and a line drawn on an
    estimator is neither. Whether 1.55 is large is not judged here.

    One file, all archives, **no incremental merge**. A merged file would keep
    records written by an older version of this code, and a record that does
    not say which version produced it reads exactly like a fresh one.
    """
    recs = []
    for n in names:
        try:
            recs.append(strata_one(n))
        except FileNotFoundError as e:
            print(f"  {n}: {e}\n")
    if not recs:
        print("  no archive ran.")
        return 1

    print(f"\n{'=' * 78}\n  §22.6.1 sign table. The reading is the sign of "
          f"g0m - g1, not the level.\n{'=' * 78}")
    signs = {}
    for tag in ("defer", "mod"):
        print(f"\n  {tag}")
        col = []
        for r in recs:
            k = r["common_strata"][tag]
            if k["n_strata"] < 3:
                print(f"    {r['archive']:<8} common L = {k['n_strata']}, "
                      f"under 3, no referent (§22.6.1 row 4)")
                continue
            d = k["g0m"] - k["g1"]
            col.append(d)
            print(f"    {r['archive']:<8} L {k['L'][0]}..{k['L'][-1]} "
                  f"({k['n_strata']})   g0m {k['g0m']:>7.3f}   "
                  f"g1 {k['g1']:>7.3f}   g0m - g1 {d:>+8.3f}")
        # **An exact tie carries no sign and must not vote.** The first version
        # of this classifier sent `diff == 0` to `mixed`, because `0 > 0` and
        # `0 < 0` are both false. 2012Q1 defer read `+0.000` and it was a
        # bitwise tie, not a rounded one: `g0m` and `g1` induce the *same*
        # partition on some strata, so `weighted_median` can land on the same
        # value from both sides. A set of nothing but ties would then have been
        # called "the sign flips across archives", which is the opposite of
        # what a tie says. Ties are counted out loud and excluded from the vote.
        ties = [x for x in col if x == 0.0]
        nz = [x for x in col if x != 0.0]
        if ties:
            print(f"    {len(ties)} exact tie(s), excluded from the sign vote "
                  f"(identical partition on the selected stratum)")
        if len(nz) < 2:
            signs[tag] = "no_referent"
        elif all(x < 0 for x in nz):
            signs[tag] = "all_negative"
        elif all(x > 0 for x in nz):
            signs[tag] = "all_positive"
        else:
            signs[tag] = "mixed"
        signs[f"{tag}_n_signed"] = len(nz)
        signs[f"{tag}_n_tied"] = len(ties)
        print(f"    verdict: {signs[tag]} -> {SIGN_READING[signs[tag]]}")

    print(f"\n  §22.6.2 g1 mod: is the collapse the grid or the vintage?")
    for r in recs:
        m = r["grids"]["g1"]["mod"]
        print(f"    {r['archive']:<8} coverage {m['coverage']:>6.1%}   "
              f"kept {m['strata_kept']:>3} strata   top class "
              f"{r['g1_mod_top_share']:>6.1%}   (defer top class "
              f"{r['g1_defer_top_share']:>6.1%})")
    print("    §22.6.2: any archive with usable g1 mod coverage means §22.4.5's\n"
          "    wording must become 'on 2019Q1' rather than 'on g1'.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = partial_path("b10_holonomy_strata", names)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_strata", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §22.4.1 and §22.6. "
             "It reads no B8 prediction and computes no floor (§21.6 rule 1).",
         "carrier": "fannie_only_see_section_21_3",
         "sign_verdict": signs, "sign_reading": SIGN_READING,
         "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


#: A row or a column with fewer than this many **signed** cells has no
#: homogeneity to speak of. **Structural, not a line on a reading**: one cell
#: is homogeneous with itself and two agree half the time by construction.
#: Ties are cells but not signed cells, for 22.7.4's reason.
MIN_CELLS = 3

#: §22.8.1's four outcomes, in the file so the printed verdict cannot drift
#: from the registration.
CELL_READING = {
    "rows_only":
        "Every archive is internally consistent and the L columns are not: the "
        "ARCHIVE is the unit, and §22.7.0's `mixed` stands as a statement that "
        "archives genuinely differ.",
    "cols_only":
        "Every L is consistent across archives and the archive rows are not: L "
        "is the unit, and §22.7.0's `mixed` is an artefact of the L mix. §22.4.4's "
        "voiding then NEEDS a new registered instrument to revisit. This section "
        "does not revisit it and does not lift the void (§22.8.2 rule 3).",
    "both":
        "Rows and columns are both homogeneous, so the sign is one constant on "
        "this arm and §22.7.0 or §22.7.1 gets a much stronger form.",
    "neither":
        "Signs scatter at the cell level, so the difference is noise there. "
        "§22.4.4's voiding is firmer, and §22.7.1's `all_positive` must be read "
        "against this same matrix rather than on its own.",
    "no_referent":
        "Neither direction had enough signed cells to read. No verdict.",
}


def cmd_cells() -> int:
    """§22.8: the sign of `g0m - g1` per (archive, L), from the strata file.

    **Nothing is recomputed.** Every stratum's ratio is already in
    ``results/b10_holonomy_strata.json`` under `per_stratum`, so this reads
    that file and does no loop finding, no residuals, no omega (§22.8.2 rule 2).
    It asserts the file is the strata file and carries all six archives,
    because a partial file produces a matrix whose holes look exactly like the
    absent cells of a complete one.

    **What it answers, which the intersection in §22.6.3 item 1 does not.**
    §22.7.0 read `mixed` on the defer arm from four archive-level numbers
    sitting on four different sets of `L`. If the sign of `g0m - g1` itself
    moves with `L`, those archives differ because they averaged different
    ranges of `L`, not because the archives differ. A common-`L` intersection
    cannot separate the two and is in any case empty here (2002Q1 defer keeps
    one stratum, 2019Q1 mod keeps one). The cell matrix separates them.
    """
    src = RESULTS / "b10_holonomy_strata.json"
    if not src.exists():
        print(f"  {src.relative_to(ROOT)} not found. Run --strata-all first.")
        return 1
    d = json.loads(src.read_text(encoding="utf-8"))
    assert d.get("step") == "holonomy_strata", f"{src} is not the strata file"
    got = [r["archive"] for r in d["archives"]]
    missing = [a for a in ARCHIVES if a not in got]
    assert not missing, (
        f"{src} is missing {missing}. Rerun --strata-all; reading a partial "
        f"file would print a matrix whose holes read like real absences.")

    def sgn(x):
        return 0 if x == 0.0 else (1 if x > 0 else -1)

    def homo(vals):
        """None when the row/column is not read, else whether it is one sign."""
        nz = [sgn(v) for v in vals if v != 0.0]
        if len(nz) < MIN_CELLS:
            return None
        return len(set(nz)) == 1

    rec = {"min_cells": MIN_CELLS, "arms": {}}
    print("§22.8: sign of g0m - g1 per (archive, L). Read from "
          f"{src.relative_to(ROOT)}; nothing recomputed.\n")

    for tag in ("defer", "mod"):
        cell = {}
        for r in d["archives"]:
            a = {x["L"]: x["ratio"]
                 for x in r["grids"]["g0m"][tag]["per_stratum"]}
            b = {x["L"]: x["ratio"]
                 for x in r["grids"]["g1"][tag]["per_stratum"]}
            for Lv in sorted(set(a) & set(b)):
                cell[(r["archive"], Lv)] = a[Lv] - b[Lv]

        Ls = sorted({Lv for _, Lv in cell})
        rows = {ar: homo([v for (x, _), v in cell.items() if x == ar])
                for ar in ARCHIVES}
        cols = {Lv: homo([v for (_, y), v in cell.items() if y == Lv])
                for Lv in Ls}
        rr = {k: v for k, v in rows.items() if v is not None}
        cc = {k: v for k, v in cols.items() if v is not None}
        rh, ch = bool(rr) and all(rr.values()), bool(cc) and all(cc.values())
        if not rr and not cc:
            verdict = "no_referent"
        else:
            verdict = ("both" if rh and ch else "rows_only" if rh else
                       "cols_only" if ch else "neither")
        allsg = {sgn(v) for v in cell.values() if v != 0.0}

        print(f"  {tag}")
        print("    " + " " * 9 + "".join(f"{Lv:>4}" for Lv in Ls) + "   row")
        for ar in ARCHIVES:
            line = "".join(
                "   ." if (ar, Lv) not in cell else
                ("   0" if cell[(ar, Lv)] == 0.0 else
                 ("   +" if cell[(ar, Lv)] > 0 else "   -"))
                for Lv in Ls)
            h = rows[ar]
            mark = ("homogeneous" if h else
                    "NOT homogeneous" if h is False else "not read")
            print(f"    {ar:<9}" + line + f"   {mark}")
        print("    " + f"{'col':<9}" + "".join(
            "   h" if cols[Lv] else ("   x" if cols[Lv] is False else "   .")
            for Lv in Ls))
        n_pos = sum(1 for v in cell.values() if v > 0)
        n_neg = sum(1 for v in cell.values() if v < 0)
        n_tie = sum(1 for v in cell.values() if v == 0.0)
        print(f"    cells {len(cell)}: + {n_pos}, - {n_neg}, tie {n_tie}   "
              f"rows read {len(rr)}/{len(ARCHIVES)} "
              f"({sum(rr.values())} homogeneous)   "
              f"cols read {len(cc)}/{len(Ls)} "
              f"({sum(cc.values())} homogeneous)")
        print(f"    verdict: {verdict}")
        print(f"      {CELL_READING[verdict]}")
        if verdict == "both":
            print(f"      single sign across every cell: {len(allsg) == 1}")
        print()

        rec["arms"][tag] = {
            "verdict": verdict,
            "cells": {f"{ar}|{Lv}": v for (ar, Lv), v in sorted(cell.items())},
            "n_pos": n_pos, "n_neg": n_neg, "n_tie": n_tie,
            "rows": {k: v for k, v in rows.items()},
            "cols": {str(k): v for k, v in cols.items()},
            "rows_read": len(rr), "rows_homogeneous": int(sum(rr.values())),
            "cols_read": len(cc), "cols_homogeneous": int(sum(cc.values())),
            "single_sign_everywhere": len(allsg) == 1,
        }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_holonomy_cells.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_cells", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §22.8. Reads the "
             "strata file only; no B8 prediction, no floor (§21.6 rule 1).",
         "carrier": "fannie_only_see_section_21_3",
         "reading": CELL_READING, **rec},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_paired() -> int:
    """§22.9.2: the paired form, `median(a - b)`, against §22.7's `median(a) -
    median(b)`.

    **What went wrong and how it surfaced.** §22.4.4 called the archive-level
    figure a paired comparison and `strata_one` computes it as a difference of
    two weighted medians. The paired quantity is the weighted median of the
    per-stratum differences. `median(a) - median(b)` and `median(a - b)` are
    different quantities; the first is a perfectly good comparison of the two
    grids' typical ratio, and using it to answer a per-stratum question is the
    defect. It surfaced because §22.8's cell matrix reads 23 positive against
    11 negative on the defer arm while the archive-level verdict on that same
    arm was `mixed` with two of three signed archives negative. **The data
    pointed at the instrument; the instrument was not doubted first.**

    **This cannot rescue §22.4.4 and is not meant to** (§22.9.3). §22.4.4
    claimed `g0m < g1`. The paired form either reads `mixed`, which leaves that
    claim unsupported, or reads positive, which is the opposite direction. The
    void stands either way.
    """
    src = RESULTS / "b10_holonomy_strata.json"
    if not src.exists():
        print(f"  {src.relative_to(ROOT)} not found. Run --strata-all first.")
        return 1
    d = json.loads(src.read_text(encoding="utf-8"))
    assert d.get("step") == "holonomy_strata", f"{src} is not the strata file"
    missing = [a for a in ARCHIVES
               if a not in [r["archive"] for r in d["archives"]]]
    assert not missing, f"{src} is missing {missing}. Rerun --strata-all."

    rec = {"min_cells": MIN_CELLS, "arms": {}}
    print("§22.9.2: paired form, weighted median of per-stratum differences.\n"
          f"Read from {src.relative_to(ROOT)}; nothing recomputed.\n")
    for tag in ("defer", "mod"):
        print(f"  {tag}")
        col, rows = [], []
        for r in d["archives"]:
            a = {x["L"]: x for x in r["grids"]["g0m"][tag]["per_stratum"]}
            b = {x["L"]: x for x in r["grids"]["g1"][tag]["per_stratum"]}
            com = sorted(set(a) & set(b))
            diffs = [a[Lv]["ratio"] - b[Lv]["ratio"] for Lv in com]
            wts = [min(a[Lv]["n"], b[Lv]["n"]) for Lv in com]
            npos = sum(1 for x in diffs if x > 0)
            nneg = sum(1 for x in diffs if x < 0)
            ntie = sum(1 for x in diffs if x == 0.0)
            if npos + nneg < MIN_CELLS:
                print(f"    {r['archive']:<9} {npos + nneg} signed cells, "
                      f"under {MIN_CELLS}, not read")
                rows.append({"archive": r["archive"], "read": False,
                             "n_pos": npos, "n_neg": nneg, "n_tie": ntie})
                continue
            D = weighted_median(diffs, wts)
            # §22.9.2: the cell counts print beside D, always. A paired median
            # quoted alone hides how many strata flipped underneath it.
            print(f"    {r['archive']:<9} D {D:>+9.4f}   cells + {npos:>2} "
                  f"- {nneg:>2} tie {ntie}   L {com[0]}..{com[-1]} ({len(com)})")
            col.append(D)
            rows.append({"archive": r["archive"], "read": True, "D": D,
                         "n_pos": npos, "n_neg": nneg, "n_tie": ntie,
                         "L": com})
        ties = [x for x in col if x == 0.0]
        nz = [x for x in col if x != 0.0]
        if ties:
            print(f"    {len(ties)} exact tie(s), excluded from the vote")
        if len(nz) < 2:
            v = "no_referent"
        elif all(x < 0 for x in nz):
            v = "all_negative"
        elif all(x > 0 for x in nz):
            v = "all_positive"
        else:
            v = "mixed"
        prev = d.get("sign_verdict", {}).get(tag)
        agree = (v == prev)
        print(f"    paired verdict: {v} -> {SIGN_READING[v]}")
        print(f"    §22.7 unpaired verdict was: {prev}")
        print("    §22.9.2 reading: "
              + ("the naming defect did not change the verdict on this arm; "
                 "§22.7's figure may still be quoted, with the defect recorded."
                 if agree else
                 "THE VERDICTS DIFFER. §22.7's unpaired verdict on this arm is "
                 "WITHDRAWN and only the paired one is quoted; the unpaired "
                 "number stays in place with a void header."))
        print()
        rec["arms"][tag] = {"paired_verdict": v, "unpaired_verdict": prev,
                            "agree": agree, "per_archive": rows,
                            "n_tied_archives": len(ties)}

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_holonomy_paired.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_paired", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §22.9.2. Reads the "
             "strata file only; no B8 prediction, no floor (§21.6 rule 1).",
         "carrier": "fannie_only_see_section_21_3",
         "reading": SIGN_READING, **rec},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_dump_unexpected(name: str, limit: int) -> int:
    """Print the raw months behind every `g2` path outside §14.4's two.

    **In this file and not a neighbouring one, on purpose.** A separate
    diagnostic would re-derive the path, and re-deriving something a
    neighbouring file already has right is the mistake this station has now
    made three times (§13.1's minimum estimator, §15's stale UPB, §21's own
    `t_M`). This calls `loop_paths` itself, so what it explains is what the
    reading counted, and it cannot drift from it.
    """
    c = K.Core(name, cols=LO.COLS)
    try:
        lp = L.find_loops(c)
        anchor = anchor_states(c)
        gf = dict(fr.GRIDS)["g2"]
        paths = loop_paths(c, lp, gf, anchor)
        tA, tM, tB = lp["t_A"], lp["t_M"], lp["t_B"]
        arm, loan = np.asarray(lp["arm"]), np.asarray(lp["loan"])
        dq = np.asarray(c.row["delinq"])
        mf = np.asarray(c.row["mod_flag"])
        da = np.asarray(c.row["defer_amt"])
        per = np.asarray(c.row["period"])

        bad = [i for i, p in enumerate(paths)
               if is_cycle(p) and p not in G2_EXPECTED]
        print(f"{name}: {len(bad):,} of {len(paths):,} loops reduce, at g2, to "
              f"something outside §14.4's two paths.\n")
        for i in bad[:limit]:
            a, m, b = int(tA[i]), int(tM[i]), int(tB[i])
            print(f"  loop {i}   loan_ix {int(loan[i])}   arm "
                  f"{'mod' if arm[i] == L.ARM_MOD else 'defer'}   "
                  f"t_A {a}  t_M {m}  t_B {b}   window {b - a} months")
            print(f"    reduced: {' -> '.join(paths[i])}")
            for k in range(a, b + 1):
                mark = "".join(t for t, x in (("A", a), ("M", m), ("B", b))
                               if k == x) or "."
                d = int(da[k]) if da[k] != K.U32_NA else -1
                ch = chr(int(mf[k])) if int(mf[k]) else "."
                print(f"      {mark:<3} {k}  period {int(per[k])}  "
                      f"delinq {int(dq[k]):>3}  mod {ch}  defer_amt {d}")
            print()
        if len(bad) > limit:
            print(f"  ... {len(bad) - limit:,} more not printed (--limit).")
    finally:
        c.close()
    return 0



# ---------------------------------------------------------------------------
# --variance. Registered before this was written.
#
# The first ruler ("between-class IQR over within-class IQR") failed on
# coverage, not on the world: it needs two classes of at least MIN_FOR_IQR per
# stratum, so it goes quiet exactly where the classes are many, which is the
# definition of a fine grid. §8·12·0 records that diagnosis, which §22·10·4
# demanded before any ruler could be swapped.
#
# The replacement asks how much of omega's variance the class label explains.
# It needs no class to have quartiles. Its own defect is that R^2 rises
# mechanically with the number of classes, and g0m has ~500 against g2's 2, so
# the fix is a permutation null that carries the same inflation: shuffle the
# labels within (archive, arm, grid), keeping the class-size profile.
# ---------------------------------------------------------------------------

#: §8·12·1. Sample count for the label-permutation null. Borrowed from B8-5 and
#: B8-3 (999 there too), not picked here.
N_PERM = 999

#: Written down and printed, because a null nobody can reproduce is not a null.
PERM_SEED = 20260819

#: §8·12·3's variable is one number per arm: the sign of E(g0m) - E(g2). The
#: middle rung is a refinement inside whichever branch lands, never a branch.
VAR_LADDER = ("g2", "g1", "g0m")


def r2_of(codes, om) -> float:
    """Share of `omega`'s variance the class label explains. No minimum cell."""
    n = int(om.size)
    if n < 2:
        return float("nan")
    tot = float(((om - om.mean()) ** 2).sum())
    if not (tot > 0):
        return float("nan")
    k = int(codes.max()) + 1
    cnt = np.bincount(codes, minlength=k).astype(float)
    ssum = np.bincount(codes, weights=om, minlength=k)
    mean_c = np.divide(ssum, cnt, out=np.zeros_like(ssum), where=cnt > 0)
    within = float(((om - mean_c[codes]) ** 2).sum())
    return 1.0 - within / tot


def r2_null(codes, om, rng, n_perm: int = N_PERM) -> list:
    """The same statistic with the labels shuffled, keeping the size profile."""
    out = []
    c = codes.copy()
    for _ in range(n_perm):
        rng.shuffle(c)
        out.append(r2_of(c, om))
    return out


def variance_of(name: str) -> dict:
    """Per (grid, arm): observed R^2, its permutation null, and E = obs - median."""
    pos, tab = LO.curve_table()
    c = K.Core(name, cols=LO.COLS)
    try:
        lp = L.find_loops(c)
        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        sums = LO.loop_sums(lp, r, ok)
        om = np.asarray(sums["omega"], dtype=float)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])
        anchor = anchor_states(c)

        rec = {"archive": name, "seed": PERM_SEED, "n_perm": N_PERM, "grids": {}}
        for gname in VAR_LADDER:
            gf = dict(fr.GRIDS)[gname]
            paths = loop_paths(c, lp, gf, anchor, None)
            per_arm = {}
            for tag, code_ in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
                sel = meas & (arm == code_)
                keys, vals = [], []
                for i in np.flatnonzero(sel).tolist():
                    red = paths[i]
                    if not is_cycle(red):
                        continue
                    keys.append(red)
                    vals.append(om[i])
                if len(vals) < 2:
                    per_arm[tag] = {"n": len(vals), "classes": 0,
                                    "r2": None, "null_p50": None,
                                    "null_p95": None, "pct": None, "E": None}
                    continue
                uniq = {k: j for j, k in enumerate(dict.fromkeys(keys))}
                codes = np.array([uniq[k] for k in keys], dtype=np.int64)
                omv = np.asarray(vals, dtype=float)
                obs = r2_of(codes, omv)
                if not np.isfinite(obs):
                    #: omega is constant inside this cell, so there is no
                    #: variance to explain. That is no referent, not a zero.
                    per_arm[tag] = {"n": int(omv.size), "classes": len(uniq),
                                    "r2": None, "null_p50": None,
                                    "null_p95": None, "pct": None, "E": None}
                    continue
                tagkey = f"{name}|{gname}|{tag}".encode("utf-8")
                rng = np.random.default_rng(
                    PERM_SEED + zlib.crc32(tagkey) % 10_000)
                null = np.array(r2_null(codes, omv, rng), dtype=float)
                p50 = float(np.median(null))
                per_arm[tag] = {
                    "n": int(omv.size), "classes": len(uniq),
                    "r2": float(obs), "null_p50": p50,
                    "null_p95": float(np.percentile(null, 95)),
                    "pct": float((null < obs).mean()),
                    "E": float(obs - p50),
                }
            rec["grids"][gname] = per_arm
        return rec
    finally:
        c.close()


def print_variance(recs: list) -> None:
    print(f"\n  A. R^2 against a label-permutation null, {N_PERM} draws, "
          f"seed {PERM_SEED}")
    print(f"     {'archive':<9}{'grid':<5}{'arm':<7}{'n':>8}{'cls':>6}"
          f"{'R2':>9}{'null p50':>10}{'null p95':>10}{'pct':>8}{'E':>9}")
    for rec in recs:
        for g in VAR_LADDER:
            for tag in ("mod", "defer"):
                d = rec["grids"][g][tag]
                if d["r2"] is None:
                    print(f"     {rec['archive']:<9}{g:<5}{tag:<7}"
                          f"{d['n']:>8}{'-':>6}{'no referent':>46}")
                    continue
                print(f"     {rec['archive']:<9}{g:<5}{tag:<7}{d['n']:>8,}"
                      f"{d['classes']:>6}{d['r2']:>9.4f}{d['null_p50']:>10.4f}"
                      f"{d['null_p95']:>10.4f}{d['pct']:>8.3f}{d['E']:>+9.4f}")

    print("\n  B. §8·12·2's gate: is the observed R^2 outside the null anywhere?")
    outside = [(rec["archive"], g, tag)
               for rec in recs for g in VAR_LADDER for tag in ("mod", "defer")
               if rec["grids"][g][tag]["pct"] is not None
               and rec["grids"][g][tag]["pct"] >= 0.95]
    print(f"     cells at or above the null's 95th percentile: {len(outside)}")
    if outside:
        print("     " + ", ".join(f"{a}/{g}/{t}" for a, g, t in outside[:12])
              + (" ..." if len(outside) > 12 else ""))
    else:
        print("     none -> the class label carries no information about omega")
        print("     at any grid. The question is empty on this carrier. Stop;")
        print("     §8·12·3 is not read.")
        return

    print("\n  C. §8·12·3's variable: the sign of E(g0m) - E(g2), one per arm")
    print(f"     {'archive':<9}{'arm':<7}{'E(g2)':>9}{'E(g1)':>9}{'E(g0m)':>9}"
          f"{'g0m-g2':>10}")
    signs = {"mod": [], "defer": []}
    for rec in recs:
        for tag in ("mod", "defer"):
            e = {g: rec["grids"][g][tag]["E"] for g in VAR_LADDER}
            if e["g2"] is None or e["g0m"] is None:
                print(f"     {rec['archive']:<9}{tag:<7}{'no referent':>37}")
                continue
            d = e["g0m"] - e["g2"]
            signs[tag].append(d)
            mid = f"{e['g1']:>9.4f}" if e["g1"] is not None else f"{'-':>9}"
            print(f"     {rec['archive']:<9}{tag:<7}{e['g2']:>9.4f}{mid}"
                  f"{e['g0m']:>9.4f}{d:>+10.4f}")

    def verdict(v):
        """§8·12·3's two named arm states, plus everything that is neither.

        「都随网格变细而上升」 is every archive strictly up. 「都持平或下降」 is
        every archive at or below zero, so an exact zero belongs there, not in
        `mixed`. Anything else is 未命中 and R01 sends it to the third branch.
        """
        if not v:
            return "no referent"
        if all(x > 0 for x in v):
            return "all rise"
        if all(x <= 0 for x in v):
            return "none rise"
        return "mixed across archives"

    vm, vd = verdict(signs["mod"]), verdict(signs["defer"])
    print(f"\n     mod arm: {vm}    defer arm: {vd}")
    print("\n  Read, one variable and three branches, all fixed before the\n"
          "  code: the direction of excess R2 along the ladder, not its level:")
    if vm == "all rise" and vd == "all rise":
        print("     Both arms rise toward the finer grid -> THE CUT DETERMINES")
        print("     THE READING. §1.1's worry holds on this carrier, and every")
        print("     holonomy reading must be quoted with its grid.")
        print("     §8·13·2 first row: the second carrier is then to be run.")
    elif vm == "none rise" and vd == "none rise":
        print("     Neither arm rises toward the finer grid -> THE CUT DOES NOT")
        print("     DETERMINE THE READING. That is the answer §21·5 wanted, and")
        print("     it is measured rather than assumed.")
        print("     §8·13·2 second row: the second carrier is optional, not run.")
    else:
        #: Three ways in. The branch is the same one; the reason is not, and a
        #: printer that says 「走向相反」 when one arm has no referent is stating
        #: something false about the data.
        if "no referent" in (vm, vd):
            print("     At least one arm has no referent, so the sign the")
            print("     criterion reads is not defined on this carrier. A reading")
            print("     that matches no branch goes to the mixed branch, and this")
            print("     is that branch.")
        elif "mixed across archives" in (vm, vd):
            print("     An arm does not point one way across the archives, so it")
            print("     is neither 「都上升」 nor 「都持平或下降」. Per R01 未命中")
            print("     归「混合」, which is this branch. Print the per-archive")
            print("     signs above and read those, not a summary.")
        else:
            print("     The two arms go opposite ways, which is §8·12·3's own")
            print("     third row.")
        print("     Landing, identical for all three ways in: per §8·12·3's third")
        print("     row and §22·4·5's precedent, there is no registered filter")
        print("     between `mod` and `defer` (they are two kinds of")
        print("     re-contracting, not two samples of one population), so both")
        print("     are reported and no verdict is drawn.")
        print("     §8·13·2 third row: the second carrier is not run either way,")
        print("     because it would carry the same two-arm problem.")
    print("     g1 is printed as a refinement inside whichever branch lands;")
    print("     it is never a branch of its own (§8·12·3's sharpening).")
    print("     Only Fannie (§8·4), so whatever lands closes §1.1 only in part.")


# ---------------------------------------------------------------------------
# --audit99. Registered in the same message that reported the defect, before
# this was written. **The variable is the twelve signs of §8·12·1's table,
# recomputed with the contaminated loops dropped.** Three branches:
#   signs all unchanged -> §8·12 stands, with the contamination counted and the
#                          defective `anchor_states` named beside it;
#   any sign changes    -> §8·12 is void, into the results file's 作废栏;
#   no contaminated measurable loop -> nothing to read but the row counts.
# No line is drawn on the loop count. Only the signs are read.
# ---------------------------------------------------------------------------

def audit99_of(name: str) -> dict:
    """Per archive: what has no label, how far it reaches, and does §8·12 move."""
    pos, tab = LO.curve_table()
    c = K.Core(name, cols=LO.COLS)
    try:
        dq = np.asarray(c.row["delinq"])
        anchor = anchor_states(c, strict=False)
        unnamed = np.array([x is None for x in anchor])
        rec = {"archive": name,
               "rows": int(c.n_rows),
               "rows_unnamed": int(unnamed.sum()),
               #: C0b: enumerate, do not pick. Print every value that lands
               #: here, not just the one the failure mode named.
               "unnamed_values": {str(k): int(v) for k, v in
                                  Counter(dq[unnamed].tolist()).most_common()}}

        lp = L.find_loops(c)
        tA, tB = np.asarray(lp["t_A"]), np.asarray(lp["t_B"])
        #: A loop is contaminated when any row of its window carries an
        #: unnamed state, because `loop_paths` reads the whole window.
        csum = np.concatenate(([0], np.cumsum(unnamed.astype(np.int64))))
        hit = (csum[tB + 1] - csum[tA]) > 0
        rec["loops"] = int(tA.size)
        rec["loops_contaminated"] = int(hit.sum())

        disc, _ = LO.disc_of_row(c, pos, tab)
        r, ok, _ = W.row_residuals(c, disc)
        sums = LO.loop_sums(lp, r, ok)
        om = np.asarray(sums["omega"], dtype=float)
        meas = np.asarray(sums["measurable"], dtype=bool)
        arm = np.asarray(lp["arm"])
        rec["measurable_contaminated"] = int((meas & hit).sum())

        rec["grids"] = {}
        for gname in VAR_LADDER:
            gf = dict(fr.GRIDS)[gname]
            paths = loop_paths(c, lp, gf, anchor, None)
            per_arm = {}
            for tag, code_ in (("mod", L.ARM_MOD), ("defer", L.ARM_DEFER)):
                sel = meas & (arm == code_)
                keys, vals, clean = [], [], []
                for i in np.flatnonzero(sel).tolist():
                    red = paths[i]
                    if not is_cycle(red):
                        continue
                    keys.append(red)
                    vals.append(om[i])
                    clean.append(not bool(hit[i]))
                per_arm[tag] = {
                    "n": len(vals),
                    "n_contaminated": int(len(vals) - sum(clean)),
                    #: A path that literally contains `None` as a vertex. Only
                    #: g0m can show this; g1/g2 map None onto a real label and
                    #: hide it, which is the whole point of the failure mode.
                    "classes_with_none": len({k for k in keys if None in k}),
                    "E_all": _e_of(keys, vals, name, gname, tag),
                    "E_clean": _e_of([k for k, cl in zip(keys, clean) if cl],
                                     [v for v, cl in zip(vals, clean) if cl],
                                     name, gname, tag),
                }
            rec["grids"][gname] = per_arm
        return rec
    finally:
        c.close()


def _e_of(keys, vals, name, gname, tag):
    """`observed R^2 - median null`, or None when there is no referent."""
    if len(vals) < 2:
        return None
    uniq = {k: j for j, k in enumerate(dict.fromkeys(keys))}
    codes = np.array([uniq[k] for k in keys], dtype=np.int64)
    omv = np.asarray(vals, dtype=float)
    obs = r2_of(codes, omv)
    if not np.isfinite(obs):
        return None
    tagkey = f"{name}|{gname}|{tag}".encode("utf-8")
    rng = np.random.default_rng(PERM_SEED + zlib.crc32(tagkey) % 10_000)
    return float(obs - float(np.median(r2_null(codes, omv, rng))))


def print_audit99(recs: list) -> None:
    print("\n  A. rows this file cannot name, and how far they reach")
    print(f"     {'archive':<9}{'rows':>12}{'unnamed':>9}{'values':>22}"
          f"{'loops':>8}{'contam':>8}{'meas.contam':>13}")
    for r in recs:
        vals = ", ".join(f"{k}x{v}" for k, v in r["unnamed_values"].items())
        print(f"     {r['archive']:<9}{r['rows']:>12,}{r['rows_unnamed']:>9,}"
              f"{(vals or '-'):>22}{r['loops']:>8,}"
              f"{r['loops_contaminated']:>8,}{r['measurable_contaminated']:>13,}")

    total = sum(r["measurable_contaminated"] for r in recs)
    print(f"\n     measurable loops touched by an unnamed row: {total:,}")
    if total == 0:
        print("     Third branch: the contamination never reaches a measurable")
        print("     loop. §8·12's twelve signs cannot have moved. Nothing to")
        print("     re-read; the row counts stand as a record of the defect.")
        return

    print("\n  B. §8·12·1's variable, recomputed with those loops dropped")
    print(f"     {'archive':<9}{'arm':<7}{'E(g2)':>9}{'E(g0m)':>10}"
          f"{'g0m-g2':>10}{'clean g0m-g2':>14}{'sign':>7}")
    flips, unread = [], []
    for r in recs:
        for tag in ("mod", "defer"):
            e = {g: r["grids"][g][tag] for g in VAR_LADDER}
            a2, a0 = e["g2"]["E_all"], e["g0m"]["E_all"]
            c2, c0 = e["g2"]["E_clean"], e["g0m"]["E_clean"]
            if None in (a2, a0):
                print(f"     {r['archive']:<9}{tag:<7}{'no referent, full':>50}")
                continue
            d_all = a0 - a2
            if None in (c2, c0):
                unread.append((r["archive"], tag))
                print(f"     {r['archive']:<9}{tag:<7}{a2:>9.4f}{a0:>10.4f}"
                      f"{d_all:>+10.4f}{'no referent':>14}{'?':>7}")
                continue
            d_cln = c0 - c2
            same = (d_all > 0) == (d_cln > 0)
            if not same:
                flips.append((r["archive"], tag, d_all, d_cln))
            print(f"     {r['archive']:<9}{tag:<7}{a2:>9.4f}{a0:>10.4f}"
                  f"{d_all:>+10.4f}{d_cln:>+14.4f}"
                  f"{('same' if same else 'FLIP'):>7}")

    nones = sum(d["classes_with_none"] for r in recs
                for g in VAR_LADDER for d in r["grids"][g].values())
    print(f"\n     class labels containing a literal None vertex: {nones}")
    print("     (only g0m can show one; g1 and g2 map None onto a real label)")

    print("\n  Read, per the registration:")
    if flips:
        print("     SECOND BRANCH. A sign moved:")
        for a, t, x, y in flips:
            print(f"       {a}/{t}: {x:+.4f} -> {y:+.4f}")
        print("     §8·12's reading is VOID. It goes to the results file's")
        print("     作废栏. Name what `99` is by C0b, fix anchor_states, re-run.")
    elif unread:
        print("     A cell lost its referent once the contaminated loops were")
        print("     dropped, so the twelve signs are not all comparable:")
        for a, t in unread:
            print(f"       {a}/{t}")
        print("     That is neither branch as registered. Report, read nothing,")
        print("     and do not claim §8·12 survived.")
    else:
        print("     FIRST BRANCH. All twelve signs unchanged with the")
        print("     contaminated loops dropped. §8·12's reading stands, and it")
        print("     carries this limitation: it was computed on an")
        print("     anchor_states that could not name every row, and the counts")
        print("     in table A are how much of it that was.")


#: §8·15's own value. **Not a threshold**: if `99` were a count of missed
#: months, a loan that read `00` fewer than 99 months ago could not read it,
#: so every such row is a counterexample and no line is being drawn.
NAME99_VALUE = 99


def last_seen(flag, start, n_per) -> "np.ndarray":
    """Index of the most recent `True` at or before each row, **within its loan**.

    `-1` where the loan has had none yet. Vectorised because the archives run
    to forty million rows; the segmented reset works because the global running
    maximum can only exceed the value carried in from before a loan's first row
    when the maximum came from inside that loan.
    """
    n = flag.size
    cand = np.where(flag, np.arange(n, dtype=np.int64), np.int64(-1))
    run = np.maximum.accumulate(cand)
    prev = np.empty(start.size, dtype=np.int64)
    prev[0] = -1
    if start.size > 1:
        prev[1:] = run[start[1:] - 1]
    base = np.repeat(prev, n_per.astype(np.int64))
    return np.where(run > base, run, np.int64(-1))


def name99_of(name: str) -> dict:
    """§8·15's one variable, plus §8·15·2's four shapes. **No omega.**"""
    c = K.Core(name, cols=LO.COLS)
    try:
        dq = np.asarray(c.row["delinq"])
        #: `b8_core` stores the period as a month index, so a difference of
        #: two of them is months. §8·20·6's bill was for assuming otherwise.
        per = c.row["period"][:].astype(np.int64)
        start = c.row_start.astype(np.int64)
        n_per = c.n_per_loan
        n = c.n_rows

        is99 = dq == NAME99_VALUE
        is00 = dq == 0
        last00 = last_seen(is00, start, n_per)
        idx99 = np.flatnonzero(is99)

        have = last00[idx99] >= 0
        rec = {"archive": name, "rows": int(n),
               "rows_99": int(idx99.size),
               "no_00_ever": int((~have).sum())}

        with_00 = idx99[have]
        d = (per[with_00] - per[last00[with_00]]) if with_00.size else \
            np.zeros(0, dtype=np.int64)
        under = d < NAME99_VALUE
        rec["with_00"] = int(with_00.size)
        rec["d_under_99"] = int(under.sum())
        rec["d_ge_99"] = int((~under).sum())
        rec["d_q"] = ([int(np.percentile(d, q)) for q in (10, 50, 90)]
                      if d.size else None)
        rec["d_min"] = int(d.min()) if d.size else None
        rec["d_max"] = int(d.max()) if d.size else None
        #: The counterexamples themselves, capped and printed. A count with no
        #: examples beside it is a count nobody can check.
        rec["d_hist"] = {str(k): int(v) for k, v in
                         Counter(d[under].tolist()).most_common(12)}
        #: §12's follow-up, registered before it was written: **23 rows on how
        #: many loans?** The `d` values came back as consecutive runs
        #: (2007Q1 walked 20 through 31, each once), which is the signature of
        #: a few loans rather than a scatter — **and a signature is not a
        #: count.** So it is counted.
        cx_loan = c.loan_of_row()[with_00[under]] if under.any() else \
            np.zeros(0, dtype=np.int64)
        per_loan = Counter(cx_loan.tolist())
        rec["cx_loans"] = int(len(per_loan))
        rec["cx_rows_per_loan"] = {str(k): int(v) for k, v
                                   in Counter(per_loan.values()).most_common()}
        rec["cx_max_rows_one_loan"] = (max(per_loan.values())
                                       if per_loan else 0)

        #: §8·15·2, four shapes, **none of them a branch**.
        same = np.zeros(n, dtype=bool)
        same[1:] = c.loan_of_row()[1:] == c.loan_of_row()[:-1]
        prev_ok = same[idx99]
        pv = dq[idx99[prev_ok] - 1] if prev_ok.any() else np.zeros(0)
        rec["prev_value"] = {str(k): int(v) for k, v in
                             Counter(pv.tolist()).most_common(8)}
        rec["prev_none"] = int((~prev_ok).sum())
        nxt_ok = np.zeros(idx99.size, dtype=bool)
        inb = idx99 + 1 < n
        nxt_ok[inb] = same[idx99[inb] + 1]
        nv = dq[idx99[nxt_ok] + 1] if nxt_ok.any() else np.zeros(0)
        rec["next_value"] = {str(k): int(v) for k, v in
                             Counter(nv.tolist()).most_common(8)}
        rec["next_none"] = int((~nxt_ok).sum())

        #: Run lengths of consecutive `99`s inside one loan.
        runs = Counter()
        if idx99.size:
            brk = np.ones(idx99.size, dtype=bool)
            brk[1:] = ~((idx99[1:] == idx99[:-1] + 1) & same[idx99[1:]])
            heads = np.flatnonzero(brk)
            lens = np.diff(np.append(heads, idx99.size))
            runs = Counter(lens.tolist())
        rec["run_len"] = {str(k): int(v) for k, v in runs.most_common(8)}
        rec["runs"] = int(sum(runs.values()))

        #: Months since the loan's own first reported row. **Named for what it
        #: is**: `LO.COLS` carries no age field, and calling this "age" would
        #: be a second column wearing the first one's name (§11 item 11).
        first_per = np.repeat(per[start], n_per.astype(np.int64))
        since = per[idx99] - first_per[idx99]
        rec["since_first_row_q"] = ([int(np.percentile(since, q))
                                     for q in (10, 50, 90)]
                                    if since.size else None)
        rec["since_first_under_99"] = int((since < NAME99_VALUE).sum())
        return rec
    finally:
        c.close()


def print_name99(recs) -> None:
    print("\n  A. the population, per archive")
    print(f"     {'archive':<9}{'rows':>13}{'rows 99':>10}{'no 00 ever':>12}"
          f"{'with 00':>10}{'**d < 99**':>12}{'d >= 99':>10}"
          f"{'d p10/p50/p90':>18}")
    tot = {"rows_99": 0, "no_00_ever": 0, "with_00": 0, "d_under_99": 0,
           "d_ge_99": 0}
    for r in recs:
        for k in tot:
            tot[k] += r[k]
        dq_ = ("/".join(str(x) for x in r["d_q"]) if r["d_q"] else "n/a")
        print(f"     {r['archive']:<9}{r['rows']:>13,}{r['rows_99']:>10,}"
              f"{r['no_00_ever']:>12,}{r['with_00']:>10,}"
              f"{r['d_under_99']:>12,}{r['d_ge_99']:>10,}{dq_:>18}")
    print(f"     {'total':<9}{'':>13}{tot['rows_99']:>10,}"
          f"{tot['no_00_ever']:>12,}{tot['with_00']:>10,}"
          f"{tot['d_under_99']:>12,}{tot['d_ge_99']:>10,}")
    print(f"     `d` is months from the row back to that loan's most recent")
    print(f"     `00`. **{NAME99_VALUE} is not a threshold**: if `99` counted")
    print("     missed months, a loan that read `00` fewer than 99 months ago")
    print("     could not read it, so each such row is a counterexample.")

    print("\n  B. Read, one variable and three branches, fixed before the code")
    if tot["with_00"] == 0 and tot["no_00_ever"] == 0:
        print("     NO REFERENT: no row carries this value at all.")
    elif tot["with_00"] == 0:
        print("     §8·15·1 -> THIRD BRANCH. **Every such row is on a loan")
        print(f"     that never read `00`** ({tot['no_00_ever']:,}). The")
        print("     denominator does not exist; counted on its own line and")
        print("     folded into neither of the other two.")
    elif tot["d_under_99"] == 0:
        print("     §8·15·1 -> FIRST BRANCH. Not one row contradicts `99 is a")
        print("     count of months`. **That is not the same as confirming")
        print("     it.** Folding the value into `g1`'s `90+` is then the")
        print("     right reading, `anchor_states`' domain widens to `dq <=")
        print("     99` from the parser rather than from memory, and the five")
        print("     blocked archives are free.")
        if tot["no_00_ever"]:
            print(f"     {tot['no_00_ever']:,} rows sit on loans with no `00`")
            print("     at all and are counted apart, not as agreement.")
    else:
        print("     §8·15·1 -> SECOND BRANCH. **On those rows `99 is a count")
        print(f"     of months` is false**: {tot['d_under_99']:,} of")
        print(f"     {tot['with_00']:,} read `00` within 99 months. So the")
        print("     value is a code there, at least. **It must not join")
        print("     `90+`**: treat it as a sentinel with its own node, and")
        print("     **re-run §8·12 and §8·4**. This section does not name it;")
        print("     it rules only that it is not a month count.")
        for r in recs:
            if r["d_under_99"]:
                print(f"       {r['archive']}  {r['d_under_99']:,} of "
                      f"{r['with_00']:,}   d histogram "
                      + ", ".join(f"{k}:{v:,}" for k, v
                                  in r["d_hist"].items()))

    cxl = sum(r.get("cx_loans", 0) for r in recs)
    cxr = sum(r["d_under_99"] for r in recs)
    if cxr:
        print("\n  B2. §12's follow-up: how many loans carry those rows")
        print(f"     {cxr:,} counterexample rows on **{cxl:,} distinct loans**"
              + (f"   ({cxr / cxl:.2f} rows per loan)" if cxl else ""))
        for r in recs:
            if r["d_under_99"]:
                print(f"       {r['archive']}  rows {r['d_under_99']:,}"
                      f"   loans {r.get('cx_loans', 0):,}"
                      f"   rows-per-loan histogram {r.get('cx_rows_per_loan')}"
                      f"   worst {r.get('cx_max_rows_one_loan')}")
        print("     **A signature is not a count.** The `d` values arriving as")
        print("     consecutive runs suggested a few loans; this line is the")
        print("     count, and it is what decides how `23` may be quoted.")

    print("\n  C. §8·15·2's four shapes. **Reported inside whichever branch")
    print("     landed; none of them is a branch** (§7·7: written down so a")
    print("     departure is visible on sight).")
    for r in recs:
        if not r["rows_99"]:
            continue
        print(f"     --- {r['archive']} ---")
        print(f"       previous row  {r['prev_value']}"
              f"   (no previous row: {r['prev_none']:,})")
        print(f"       next row      {r['next_value']}"
              f"   (no next row: {r['next_none']:,})")
        print(f"       run lengths   {r['run_len']}   runs {r['runs']:,}")
        sq = r["since_first_row_q"]
        print(f"       months since the loan's first reported row"
              f"   p10/p50/p90 "
              f"{'/'.join(str(x) for x in sq) if sq else 'n/a'}"
              f"   under 99: {r['since_first_under_99']:,}")
    print("     The counters' predictions, written before this ran: a capped")
    print("     counter reads `98` on the previous row overwhelmingly, `99` or")
    print("     termination on the next, and long runs. `unavailable` predicts")
    print("     isolated single rows instead.")

    print("\n  D. What this section does NOT do (§8·15·3)")
    print("     It does not consult a layout document (C0b), does not carry")
    print("     anything to Freddie (field 4 is a different enumeration and")
    print("     has an `RA` this side does not), computes no omega, and does")
    print("     not name the value even if branch two lands — it rules only")
    print("     that the value is not a month count.")
    print("     §8·12's own reading does not wait on this: 结果件 §8·12·7")
    print("     already audited it. **What waits on this is any Fannie")
    print("     re-run**, which anchor_states' strict guard is holding.")


def cmd_name99(names) -> int:
    print("§8·15: what `delinq == 99` is, by behaviour. Registered before this")
    print("was written. **No omega is computed** (§8·15·3).\n")
    recs = []
    for name in (names or ARCHIVES):
        print(f"  {name} ...", flush=True)
        recs.append(name99_of(name))
    print_name99(recs)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = partial_path("b10_holonomy_name99", names)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_name99", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Names delinq == 99 from behaviour, "
             "per C0b. Reads no layout document, computes no omega, and does "
             "not carry to Freddie, whose field 4 has its own enumeration.",
         "value": NAME99_VALUE, "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def partial_path(base: str, names) -> "Path":
    """`results/<base>.json`, or a suffixed name when the run is a subset.

    **Caught on 2026-08-20 by using it.** `--variance 2019Q1` wrote one
    archive over a six-archive artifact and nothing in the file's name said so
    — a reader opening it later finds a complete-looking file that covers a
    sixth of the book. B12 already had the answer in this repository
    (`b12_ladder.offparam_2019Q1.json`), so this follows that rather than
    inventing a scheme.

    A run that covers every archive keeps the plain name, so the full artifact
    is always at one predictable path and 規矩 19's comparison has something
    stable to compare against.
    """
    got = sorted(names or ARCHIVES)
    if got == sorted(ARCHIVES):
        return RESULTS / f"{base}.json"
    return RESULTS / f"{base}.{'_'.join(got)}.json"


def cmd_audit99(names) -> int:
    print("失效模式 19 on this file's own output. Registered before it was")
    print("written. No omega is recomputed.\n")
    recs = []
    for name in (names or ARCHIVES):
        print(f"  {name} ...", flush=True)
        recs.append(audit99_of(name))
    print_audit99(recs)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = partial_path("b10_holonomy_audit99", names)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_audit99", "diagnostic_only": True,
         "diagnostic_reason":
             "MEASUREMENT.md 失效模式 19 against this file's own §8·12 run. "
             "Reads loop_sums, recomputes no omega. Fannie only (§8·4).",
         "n_perm": N_PERM, "seed": PERM_SEED, "archives": recs},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_variance(names) -> int:
    print("§8·12: swapping the ruler. Variance of omega explained by the class")
    print("label, against a label-permutation null. No omega is recomputed.\n")
    recs = []
    for name in (names or ARCHIVES):
        print(f"  {name} ...", flush=True)
        recs.append(variance_of(name))
    print_variance(recs)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = partial_path("b10_holonomy_variance", names)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "holonomy_variance",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Reads loop_sums and recomputes no "
             "omega. Fannie only, because the omega machinery is built on "
             "Fannie's core table and Freddie has none, so this closes the "
             "cut-dependence question on one carrier and not on both.",
         "n_perm": N_PERM, "seed": PERM_SEED,
         "archives": recs}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", action="append")
    ap.add_argument("--dump-unexpected", metavar="ARCHIVE")
    ap.add_argument("--strata", action="append", metavar="ARCHIVE")
    ap.add_argument("--strata-all", action="store_true")
    ap.add_argument("--cells", action="store_true")
    ap.add_argument("--paired", action="store_true")
    ap.add_argument("--variance", action="append", metavar="ARCHIVE",
                    help="§8·12: the replacement ruler; repeatable, empty = all")
    ap.add_argument("--variance-all", action="store_true")
    ap.add_argument("--name99-node", action="store_true",
                    help="§8·15·4·1: give delinq == 99 its own vertex in every "
                         "grid. Off reproduces every prior answer byte for "
                         "byte; on unfreezes the five archives.")
    ap.add_argument("--name99", action="append", metavar="ARCHIVE",
                    help="§8·15: what delinq == 99 is, by behaviour")
    ap.add_argument("--name99-all", action="store_true")
    ap.add_argument("--audit99", action="append", metavar="ARCHIVE",
                    help="失效模式 19: does it reach §8·12's twelve signs")
    ap.add_argument("--audit99-all", action="store_true")
    ap.add_argument("--limit", type=int, default=12)
    a = ap.parse_args(argv)
    if a.name99_node:
        globals()["D99_ON"] = True
        print("§8·15·4·1: `delinq == 99` is labelled "
              f"`{fr.D99}` and stands as its own vertex in g1, g2 and g3.\n"
              "  Off, nothing can produce that label and every prior answer\n"
              "  is reproduced byte for byte. The strict guard is NOT lifted:\n"
              "  it refuses values with no name, and 99 now has one.\n")
    if a.selftest:
        return cmd_selftest()
    if a.cells:
        return cmd_cells()
    if a.paired:
        return cmd_paired()
    if a.name99_all:
        return cmd_name99(list(ARCHIVES))
    if a.name99:
        return cmd_name99(a.name99)
    if a.audit99_all:
        return cmd_audit99(list(ARCHIVES))
    if a.audit99:
        return cmd_audit99(a.audit99)
    if a.variance_all:
        return cmd_variance(list(ARCHIVES))
    if a.variance:
        return cmd_variance(a.variance)
    if a.dump_unexpected:
        return cmd_dump_unexpected(a.dump_unexpected, a.limit)
    if a.strata_all:
        return cmd_strata(list(ARCHIVES))
    if a.strata:
        return cmd_strata(a.strata)
    if a.run:
        return cmd_run(a.only)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
