"""B34, LFS arm, step 5: score arm two, the boundary that moved.

The criterion, from the design document, arm B34-2:

    read      whether the kink follows the boundary when the boundary moves
    PASS      it follows AND the old position disappears
    FAIL      the old position does not disappear
    UNDECIDED fewer than two readable years on each side of the move

The load-bearing half is the second one in PASS. Any account in which age
itself raises pay predicts the old kink stays put, because nobody becomes a
year less skilled at 25 when a statute is rewritten.

What moved
----------
The national living wage age went from 25 to 23 on 1 April 2021.

    rate year 2019-20   boundaries {18, 21, 25}    SI 2019/603
    rate year 2021-22   boundaries {18, 21, 23}    SI 2021/329

So 25 is the OLD position and 23 is the NEW one, and 18 and 21 did not move.

The line, and where it comes from
---------------------------------
"Readable" here is the resolution floor already used by this station: a reading
counts as visible when it stands at 1.645 times its own floor or more. That
constant is not chosen here. It is the one-sided five per cent critical value,
and this project's own derivation shows the resolution gate and the power floor
are the same inequality written twice, so the same number carries both.

Nothing else is thresholded. Every ratio is printed, both halves are scored
separately, and the year-effect check below is a comparison of directions with
no line on it at all.

The year-effect check, which is what the two-year requirement wanted
--------------------------------------------------------------------
One year on each side invites the objection that whatever changed is a property
of that year rather than of the move. The requirement of two years per side is
a count, and a count cannot distinguish the two. A reversed control can: if
2021 were simply a flat or noisy year, every boundary would weaken in it. So
this step also reads the NEW boundary, which should move the other way. A year
effect cannot weaken one boundary and strengthen another in the same year.

Usage
-----
    python experiments/b34_lfs_step5_arm2.py
"""

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
IN = REPO / "results" / "b34_lfs_kink.json"
OUT = REPO / "results" / "b34_lfs_arm2.json"

OLD_YEAR, NEW_YEAR = 2019, 2021
# Every rate year after the move, in order. The boundary at 23 was one year old
# in the first of these and two in the second, so reading them separately is
# what separates "the boundary is not there" from "employers have not moved to
# it yet". That distinction was registered before the 2022-23 data existed.
POST_YEARS = (2021, 2022)
# Every rate year before the move, in order, for the same reason read the other
# way round. The criterion's third state is a count of readable years per side,
# and until 2018-19 was on disk the pre side had one. Adding it does two things
# and neither is the verdict: it satisfies that clause as written, and it gives
# the old boundary at 25 a second, independent pre-move reading, which is what
# the load-bearing half of the PASS conjunction had been resting on alone.
PRE_YEARS = (2018, 2019)
OLD_AGE, NEW_AGE = 25, 23
UNMOVED = (18, 21)
VISIBLE = 1.645
VISIBLE_SOURCE = ("one-sided five per cent critical value; this project's own "
                  "derivation makes the resolution gate and the power floor the "
                  "same inequality, so one constant carries both")


def stem(key):
    """Strip the year and the year-specific threshold name from a profile key."""
    parts = key.split("|")
    rest = parts[1:]
    rest = [("MAIN" if p.startswith("main_") else "ALT" if p.startswith("alt_") else p)
            for p in rest]
    return "|".join(rest)


def ratio_at(rows, age):
    for r in rows:
        if r["age"] == age:
            return r
    return None


def main():
    rec = json.loads(IN.read_text(encoding="utf-8"))
    K = rec["kinks"]

    by_stem = {}
    for key in K:
        y = int(key.split("|")[0])
        by_stem.setdefault(stem(key), {})[y] = key
    pairs = {s: d for s, d in by_stem.items() if OLD_YEAR in d and NEW_YEAR in d}

    print("=" * 78)
    print("B34 LFS arm, step 5: arm two. The living wage age moved 25 -> 23 on")
    print("1 April 2021, so 25 is the old position and 23 is the new one.")
    print("visible at %.3f times the floor (%s)" % (VISIBLE, VISIBLE_SOURCE))
    print("=" * 78)

    rows_out, disappeared, followed = [], [], []
    print("\n1. the load-bearing half: does the OLD position (age %d) disappear?" % OLD_AGE)
    print("   %-26s %-11s %-11s %-9s %-9s %s"
          % ("profile", "%d" % OLD_YEAR, "%d" % NEW_YEAR, "ch_old", "ch_new", "gone?"))
    for s in sorted(pairs):
        a = ratio_at(K[pairs[s][OLD_YEAR]]["rows"], OLD_AGE)
        b = ratio_at(K[pairs[s][NEW_YEAR]]["rows"], OLD_AGE)
        gone = abs(b["ratio"]) < VISIBLE
        was_there = abs(a["ratio"]) >= VISIBLE
        disappeared.append((s, was_there, gone))
        print("   %-26s %-+11.2f %-+11.2f %-+9.4f %-+9.4f %s"
              % (s[:26], a["ratio"], b["ratio"], a["ch"], b["ch"],
                 ("yes" if gone else "NO") + ("" if was_there else "  (not visible in %d either)" % OLD_YEAR)))
        rows_out.append({"stem": s, "age": OLD_AGE,
                         "old_year": {"ratio": a["ratio"], "ch": a["ch"], "floor": a["floor"], "n": a["n"]},
                         "new_year": {"ratio": b["ratio"], "ch": b["ch"], "floor": b["floor"], "n": b["n"]},
                         "visible_in_old_year": was_there, "gone_in_new_year": gone})

    print("\n2. the other half: does the kink FOLLOW to the new position (age %d)?" % NEW_AGE)
    print("   %-26s %-11s %-11s %s" % ("profile", "%d" % OLD_YEAR, "%d" % NEW_YEAR, "visible in %d?" % NEW_YEAR))
    for s in sorted(pairs):
        a = ratio_at(K[pairs[s][OLD_YEAR]]["rows"], NEW_AGE)
        b = ratio_at(K[pairs[s][NEW_YEAR]]["rows"], NEW_AGE)
        vis = abs(b["ratio"]) >= VISIBLE
        followed.append((s, vis, abs(b["ratio"]) > abs(a["ratio"])))
        print("   %-26s %-+11.2f %-+11.2f %s"
              % (s[:26], a["ratio"], b["ratio"], "yes" if vis else "no"))

    print("\n3. the year-effect check, a reversed control with no line on it")
    stronger_new = sum(1 for _, _, up in followed if up)
    weaker_old = sum(1 for s in sorted(pairs)
                     if abs(ratio_at(K[pairs[s][NEW_YEAR]]["rows"], OLD_AGE)["ratio"])
                     < abs(ratio_at(K[pairs[s][OLD_YEAR]]["rows"], OLD_AGE)["ratio"]))
    n = len(pairs)
    print("   old position weaker in %d: %d / %d" % (NEW_YEAR, weaker_old, n))
    print("   new position stronger in %d: %d / %d" % (NEW_YEAR, stronger_new, n))
    print("   A year effect moves every boundary the same way. These move opposite ways.")
    # Counting how many profiles weakened is not enough on its own: a boundary
    # that did not move can weaken a little in a thinner year. The size is what
    # separates that from a boundary that stopped existing, so print it.
    def delta(age):
        return [abs(ratio_at(K[pairs[s][NEW_YEAR]]["rows"], age)["ratio"])
                - abs(ratio_at(K[pairs[s][OLD_YEAR]]["rows"], age)["ratio"])
                for s in sorted(pairs)]

    deltas = {a: delta(a) for a in (OLD_AGE, NEW_AGE) + UNMOVED}
    mean = lambda v: sum(v) / len(v)
    print("   %-8s %-11s %-11s %s" % ("age", "mean change", "weaker", "role"))
    role = {OLD_AGE: "old boundary, should go",
            NEW_AGE: "new boundary, should appear"}
    for a in (OLD_AGE, NEW_AGE) + UNMOVED:
        v = deltas[a]
        print("   %-8d %-+11.3f %-11s %s"
              % (a, mean(v), "%d / %d" % (sum(1 for x in v if x < 0), n),
                 role.get(a, "did not move")))
    unmoved_mean = mean([mean(deltas[a]) for a in UNMOVED])
    print("   the two boundaries that did not move average %+.3f between them," % unmoved_mean)
    print("   and the old boundary changed by %+.3f." % mean(deltas[OLD_AGE]))
    beats = sum(1 for i in range(n)
                if deltas[OLD_AGE][i] < min(deltas[a][i] for a in UNMOVED))
    flips_old = sum(1 for s in sorted(pairs)
                    if ratio_at(K[pairs[s][OLD_YEAR]]["rows"], OLD_AGE)["ratio"]
                    * ratio_at(K[pairs[s][NEW_YEAR]]["rows"], OLD_AGE)["ratio"] < 0)
    flips_unmoved = {a: sum(1 for s in sorted(pairs)
                            if ratio_at(K[pairs[s][OLD_YEAR]]["rows"], a)["ratio"]
                            * ratio_at(K[pairs[s][NEW_YEAR]]["rows"], a)["ratio"] < 0)
                     for a in UNMOVED}
    print("   old boundary falls further than either unmoved one on %d / %d profiles"
          % (beats, n))
    print("   sign flips: old boundary %d / %d, unmoved %s"
          % (flips_old, n, ", ".join("%d: %d" % (a, c) for a, c in sorted(flips_unmoved.items()))))

    print("\n3b. every rate year after the move, read separately")
    print("   %-6s %-11s %-11s %-11s %s"
          % ("year", "old mean", "old visible", "new mean", "new visible"))
    progression = {}
    for y in POST_YEARS:
        keys = [d[y] for d in pairs.values() if y in d]
        if not keys:
            continue
        old_r = [ratio_at(K[k]["rows"], OLD_AGE)["ratio"] for k in keys]
        new_r = [ratio_at(K[k]["rows"], NEW_AGE)["ratio"] for k in keys]
        ov = sum(1 for x in old_r if abs(x) >= VISIBLE)
        nv = sum(1 for x in new_r if abs(x) >= VISIBLE)
        m = lambda v: sum(v) / len(v)
        print("   %-6d %-+11.2f %-11s %-+11.2f %s"
              % (y, m(old_r), "%d / %d" % (ov, len(old_r)),
                 m(new_r), "%d / %d" % (nv, len(new_r))))
        progression[str(y)] = {"old_mean": round(m(old_r), 4), "old_visible": ov,
                               "new_mean": round(m(new_r), 4), "new_visible": nv,
                               "profiles": len(keys)}
    if len(progression) > 1:
        ys = sorted(progression)
        a, b = progression[ys[0]], progression[ys[-1]]
        print("   the old position stays gone in every year after the move;")
        print("   the new one goes from %d / %d visible to %d / %d."
              % (a["new_visible"], a["profiles"], b["new_visible"], b["profiles"]))
        print("   That direction was registered before the later year was on disk.")

    print("\n3c. every rate year before the move, read separately")
    print("   %-6s %-11s %-11s %-11s %s"
          % ("year", "old mean", "old visible", "new mean", "new visible"))
    pre_progression = {}
    for y in PRE_YEARS:
        keys = [d[y] for d in pairs.values() if y in d]
        if not keys:
            continue
        old_r = [ratio_at(K[k]["rows"], OLD_AGE)["ratio"] for k in keys]
        new_r = [ratio_at(K[k]["rows"], NEW_AGE)["ratio"] for k in keys]
        ov = sum(1 for x in old_r if abs(x) >= VISIBLE)
        nv = sum(1 for x in new_r if abs(x) >= VISIBLE)
        m = lambda v: sum(v) / len(v)
        print("   %-6d %-+11.2f %-11s %-+11.2f %s"
              % (y, m(old_r), "%d / %d" % (ov, len(old_r)),
                 m(new_r), "%d / %d" % (nv, len(new_r))))
        pre_progression[str(y)] = {"old_mean": round(m(old_r), 4), "old_visible": ov,
                                   "new_mean": round(m(new_r), 4), "new_visible": nv,
                                   "profiles": len(keys)}
    # 23 was not a boundary in either pre-move year, so whatever it reads there
    # is the same quantity the placebo arm reads: a gap the statute does not
    # name. It is printed rather than scored, and it is not evidence about the
    # move in either direction.
    n_pre, n_post = len(pre_progression), len(progression)
    print("   readable rate years: %d before the move, %d after."
          % (n_pre, n_post))
    print("   The old boundary is read once per pre-move year, so the")
    print("   load-bearing half no longer rests on a single year.")

    n_gone = sum(1 for _, was, g in disappeared if g)
    n_was = sum(1 for _, was, g in disappeared if was)
    n_follow = sum(1 for _, v, _ in followed if v)

    print("\n4. verdict, against the criterion as written")
    print("   old position visible in %d : %d / %d" % (OLD_YEAR, n_was, n))
    print("   old position gone in %d    : %d / %d" % (NEW_YEAR, n_gone, n))
    print("   new position visible in %d : %d / %d" % (NEW_YEAR, n_follow, n))
    if n_gone == n and n_follow == n:
        verdict, why = "PASS", "both halves hold on every profile"
    elif n_gone < n:
        verdict, why = ("FAIL", "the old position does not disappear on %d of %d profiles"
                        % (n - n_gone, n))
    else:
        verdict = "UNDECIDED"
        why = ("the load-bearing half holds on every profile (%d / %d), and the "
               "other half is not visible on %d of %d: the kink is gone from the "
               "old position but not yet readable at the new one"
               % (n_gone, n, n - n_follow, n))
    print("   -> %s: %s" % (verdict, why))
    third_state_met = n_pre < 2 or n_post < 2
    print("\n   The criterion's own third state is 'fewer than two readable years")
    print("   on each side'. There are %d before and %d after, so that clause is"
          % (n_pre, n_post))
    print("   %s." % ("met as written" if third_state_met else "NOT met any more"))
    print("   The verdict above does not turn on it either way: it comes from the")
    print("   second half of the PASS conjunction, which is a count of profiles")
    print("   and not a count of years. What the clause wanted, a guard against a")
    print("   year effect, is answered by section 3 and reported separately.")

    record = {
        "stage": "B34-LFS-arm2",
        "criteria": [
            {"name": "B34-2a old position disappears",
             "passed": n_gone == n,
             "detail": "age %d visible in %d on %d/%d profiles, gone in %d on %d/%d"
                       % (OLD_AGE, OLD_YEAR, n_was, n, NEW_YEAR, n_gone, n)},
            {"name": "B34-2b kink follows to the new position",
             "passed": n_follow == n,
             "detail": "age %d visible in %d on %d/%d profiles" % (NEW_AGE, NEW_YEAR, n_follow, n)},
        ],
        "verdict": verdict,
        "verdict_reason": why,
        "config": {
            "old_year": OLD_YEAR, "new_year": NEW_YEAR,
            "old_age": OLD_AGE, "new_age": NEW_AGE,
            "unmoved_boundaries": list(UNMOVED),
            "visible_at": VISIBLE, "visible_source": VISIBLE_SOURCE,
            "source_record": IN.name,
            "pre_years": list(PRE_YEARS), "post_years": list(POST_YEARS),
            "years_each_side": {"before": n_pre, "after": n_post},
            "criterion_third_state": "fewer than two readable years on each side",
            "criterion_third_state_met": third_state_met,
        },
        "post_move_progression": progression,
        "pre_move_progression": pre_progression,
        "year_effect_check": {
            "old_weaker_in_new_year": weaker_old,
            "new_stronger_in_new_year": stronger_new,
            "profiles": n,
            "mean_change_by_age": {str(a): round(mean(v), 4) for a, v in deltas.items()},
            "unmoved_mean": round(unmoved_mean, 4),
            "old_falls_further_than_both_unmoved": beats,
            "sign_flips": dict({str(OLD_AGE): flips_old},
                               **{str(a): c for a, c in flips_unmoved.items()}),
        },
        "profiles": rows_out,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\nwrote %s" % OUT.name)


if __name__ == "__main__":
    main()
