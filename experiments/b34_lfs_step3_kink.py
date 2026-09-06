"""B34, LFS arm, step 3: locate the kinks in the profile. Report positions only.

Design section 5.3 gives this step no pass condition. It reports where the
profile bends; arms one and four are scored later, in step 4.

What is carried over from the fifth instrument in B30-22, and what is not
------------------------------------------------------------------------
Carried over, the shape:

  - second difference as the kink statistic, computed everywhere, no pruning
  - the named-position comparison, which is the part that does the work:
        unexplained        a kink where no named position sits
        named_with_no_kink a named position with no kink on it
    Those two are exactly the two FAIL directions of arm one. A kink off the
    statutory boundaries means a finer partition than the statute writes; a
    statutory boundary with no kink means a coarser one.
  - no pruning. That instrument's fourth version pruned an interval whose two
    end sixths had equal slope, which is what happens when the interval holds
    an even number of kinks, and it missed both kinks in two of six runs. Here
    every interior age is reported whether or not anything is on it.

NOT carried over: `TOL = 0.02`, `W = 1.0`, and the 20,000 to 200,000 range.
Those are the units of a student loan simulation. Nothing in them transfers,
and a threshold with no derivation would be an arbitrary calibration.

The floor here is derived rather than declared
----------------------------------------------
The profile is a binomial share per single year of age, and the age cells hold
disjoint people: the collision table in the step 1 record measured 0 of 8 entry
cohorts appearing in more than one quarter, because the income questions are
asked in waves 1 and 5 only and those are exactly four quarters apart. So for

    ch(a) = p(a+1) - 2 p(a) + p(a-1)

the three terms are independent and

    se(ch(a)) = sqrt( se(a+1)^2 + 4 se(a)^2 + se(a-1)^2 )

with se(a) the binomial standard error already in the step 2 record. That is an
analytic floor, zero sampling, and its provenance is the binomial variance plus
a measured independence rather than a chosen constant.

No line is drawn on it. Every interior age is printed with its ch, its floor,
and the ratio, which is a printed object with a stated reading and not a
threshold test.

Sign convention, stated before the numbers
------------------------------------------
ch(a) = slope(a to a+1) - slope(a-1 to a). The profile falls with age, so both
slopes are usually negative. ch(a) > 0 means the fall is flattening at a, which
is what a step down in the share at age a looks like from the right. ch(a) < 0
means the fall is steepening at a.

Named positions: the statutory age boundaries for rate year 2021-22, {18, 21,
23}, from SI 2021/329 as recorded in the results document. Under the statute a
worker's floor rises on reaching 18, 21 and 23, and nowhere else.

Usage
-----
    python experiments/b34_lfs_step3_kink.py
"""

import argparse
import json
import math
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
IN = REPO / "results" / "b34_lfs_profile.json"
OUT = REPO / "results" / "b34_lfs_kink.json"

# Statutory age boundaries, per rate year. The living wage age is the treatment:
# 25 under SI 2019/603 and 23 under SI 2021/329, moved on 1 April 2021. The
# other two boundaries do not move. Arm two reads exactly this: a kink at 25
# in the first year and none there in the second.
NAMED = {2018: (18, 21, 25), 2019: (18, 21, 25),
         2021: (18, 21, 23), 2022: (18, 21, 23)}
NAMED_SOURCE = {2018: "SI 2018/455 with SI 2015/621 reg 4A, age boundaries for rate year 2018-19",
                2019: "SI 2019/603, age boundaries for rate year 2019-20",
                2021: "SI 2021/329, age boundaries for rate year 2021-22",
                2022: "SI 2022/382, age boundaries for rate year 2022-23"}

# Which profiles this step runs on. Unweighted only: the binomial floor above
# is exact for an unweighted share and only approximate for a weighted one, and
# the weighted profiles are already in the step 2 record as a robustness pair.
# Selected by pattern rather than listed, so a new rate year needs no edit here.
KEY_SUFFIX = "|unweighted"


def year_of(key):
    """The rate year a profile key belongs to. Keys are year|pay|threshold|..."""
    head = key.split("|")[0]
    return int(head) if head.isdigit() else None


def second_differences(points, named):
    """ch(a) and its analytic floor, for every interior age. No pruning."""
    by_age = {r["age"]: r for r in points if r.get("p") is not None}
    ages = sorted(by_age)
    out = []
    for a in ages:
        if (a - 1) not in by_age or (a + 1) not in by_age:
            continue
        lo, mid, hi = by_age[a - 1], by_age[a], by_age[a + 1]
        ch = hi["p"] - 2.0 * mid["p"] + lo["p"]
        floor = math.sqrt(hi["se_binom"] ** 2
                          + 4.0 * mid["se_binom"] ** 2
                          + lo["se_binom"] ** 2)
        out.append({
            "age": a,
            "ch": round(ch, 6),
            "floor": round(floor, 6),
            "ratio": round(ch / floor, 4) if floor > 0 else None,
            "slope_left": round(mid["p"] - lo["p"], 6),
            "slope_right": round(hi["p"] - mid["p"], 6),
            "n": mid["n"],
            "named": a in named,
        })
    return out


def report(label, rows, named):
    print("\n--- %s ---" % label)
    print("   %-5s %-8s %-10s %-10s %-8s %-10s %-10s %s"
          % ("age", "n", "slope_L", "slope_R", "named", "ch", "floor", "ch/floor"))
    for r in rows:
        print("   %-5d %-8d %-+10.4f %-+10.4f %-8s %-+10.4f %-10.4f %s"
              % (r["age"], r["n"], r["slope_left"], r["slope_right"],
                 "YES" if r["named"] else "", r["ch"], r["floor"],
                 ("%+.2f" % r["ratio"]) if r["ratio"] is not None else "n/a"))
    # rank by absolute ratio, print the ordering, draw no line
    order = sorted(rows, key=lambda r: -abs(r["ratio"] or 0.0))
    print("   ranked by |ch| / floor, largest first, no line drawn:")
    print("      " + "  ".join("%d%s(%+.2f)" % (r["age"], "*" if r["named"] else "",
                                                r["ratio"] or 0.0)
                               for r in order))
    print("      * marks a statutory boundary (%s)" % ", ".join(map(str, named)))
    named_rows = [r for r in rows if r["named"]]
    other_rows = [r for r in rows if not r["named"]]
    if named_rows and other_rows:
        best_named = max(abs(r["ratio"] or 0.0) for r in named_rows)
        n_bigger = [r["age"] for r in other_rows
                    if abs(r["ratio"] or 0.0) > best_named]
        print("   non-statutory ages whose |ch|/floor exceeds every statutory one: %s"
              % (n_bigger if n_bigger else "none"))
    return {"rows": rows,
            "ranked": [r["age"] for r in order],
            "named": list(named)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=pathlib.Path, default=IN)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    args = ap.parse_args()

    rec = json.loads(args.profile.read_text(encoding="utf-8"))
    prof = rec["profile"]
    appr = rec.get("apprentice_two_cells", {})

    print("=" * 78)
    print("B34 LFS arm, step 3: kink positions. No pass condition (design 5.3).")
    for _y in sorted(NAMED):
        print("named positions %s for rate year %d, from %s"
              % (list(NAMED[_y]), _y, NAMED_SOURCE[_y]))
    print("floor is analytic: se(ch) = sqrt(se(a+1)^2 + 4 se(a)^2 + se(a-1)^2),")
    print("valid because the age cells hold disjoint people (measured, 0 of 8).")
    print("ch(a) > 0 means the fall flattens at a; ch(a) < 0 means it steepens.")
    print("=" * 78)

    out = {}
    for key in sorted(prof):
        if not key.endswith(KEY_SUFFIX):
            continue
        y = year_of(key)
        if y not in NAMED:
            continue
        out[key] = report(key, second_differences(prof[key], NAMED[y]), NAMED[y])

    # the same statistic on the apprentice-free profile, where step 2 built it
    for key, rows in sorted(appr.items()):
        pts = [{"age": r["age"], "p": r["p_no_appr"], "n": r["n_all"] - r["n_appr"],
                "se_binom": math.sqrt(max(r["p_no_appr"] * (1.0 - r["p_no_appr"]), 0.0)
                                      / max(r["n_all"] - r["n_appr"], 1))}
               for r in rows]
        y = year_of(key)
        if y not in NAMED:
            continue
        out[key + "|no_apprentices"] = report(
            key + " (apprentices held out)",
            second_differences(pts, NAMED[y]), NAMED[y])

    record = {
        "stage": "B34-LFS-step3",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "Step 3 of the LFS arm reports kink positions and judges nothing. "
            "Design section 5.3 gives this step no pass condition. Arms one "
            "and four are scored in step 4."
        ),
        "config": {
            "named_positions": {str(k): list(v) for k, v in NAMED.items()},
            "named_source": {str(k): v for k, v in NAMED_SOURCE.items()},
            "profile_key_suffix": KEY_SUFFIX,
            "floor": "analytic binomial, se(ch)=sqrt(se_hi^2+4 se_mid^2+se_lo^2)",
            "pruning": "none",
            "line_drawn": False,
            "source_record": args.profile.name,
        },
        "kinks": out,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print("\nwrote %s" % args.out.name)
    print("Positions reported. Nothing judged. Arm one is scored in step 4.")


if __name__ == "__main__":
    main()
