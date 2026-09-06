"""B34, LFS arm, step 6: score arm three, the placebo, and arm four, the
structural check. Design section 5.3 step 6.

Arm three
---------
The registered form is: read the ages the statute does not name and see whether
a break sits there. Step 4 re-indexed the statistic from age to gap, because a
boundary lives between two ages and a second difference at an age straddles two
gaps; the same re-indexing applies here, so the placebo set is the gaps the
statute does not touch rather than the ages it does not name. Nothing in the
step 2 record changes.

Two readings are printed, both on numbers step 4 already computed:

  three-a  no placebo gap reads a break at the visibility multiple in a
           majority of that year's eight profiles
  three-b  in each rate year the largest mean excess sits on a statutory gap

three-b is the same comparison as B34-1b seen from the placebo side. It is
reported separately because the two arms are registered separately and `D31`
forbids collapsing two registered states into one sentence.

The flat side is printed too. A gap that reads flatter than its neighbours is
not a break and does not score, but it is an object, and discipline 11 says to
print the object.

Arm four
--------
Registered form: the boundary set taken from the statute for each year equals,
word for word, the set the code uses. The statute side is written out here from
the instruments directly rather than imported from the other steps, because a
check that imports the thing it is checking checks nothing. The code side is
read out of the config blocks the other steps wrote into their records.

Two exclusions are part of the statute side and are checked as such:

  the lower bound of the youngest band is not an age. Entitlement begins on
  ceasing to be of compulsory school age, National Minimum Wage Act 1998
  s.1(2)(c), which is fixed by school year and not by a birthday. So 16 and 17
  must not appear as boundaries.

  the apprentice rate is not a fifth age band. National Minimum Wage
  Regulations 2015 reg 5(1) applies it to a worker under an apprenticeship who
  is either within twelve months of starting or under nineteen; the two limbs
  are disjunctive, so it crosses the age bands and 19 must not appear as a
  boundary.

Usage
-----
    python experiments/b34_lfs_step6_placebo_struct.py
"""

import argparse
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
ARM1 = REPO / "results" / "b34_lfs_arm1.json"
PROFILE = REPO / "results" / "b34_lfs_profile.json"
KINK = REPO / "results" / "b34_lfs_kink.json"
OUT = REPO / "results" / "b34_lfs_arm3_arm4.json"

# ---------------------------------------------------------------------------
# The statute side of arm four, written out from the instruments.
# Boundaries are the ages at which the floor rises, as half-open left endpoints.
STATUTE_BOUNDARIES = {
    2018: [18, 21, 25],
    2019: [18, 21, 25],
    2021: [18, 21, 23],
    2022: [18, 21, 23],
}
STATUTE_RATES = {
    # living wage, second adult band, third band, youngest band, apprentice
    2018: [7.83, 7.38, 5.90, 4.20, 3.70],
    2019: [8.21, 7.70, 6.15, 4.35, 3.90],
    2021: [8.91, 8.36, 6.56, 4.62, 4.30],
    2022: [9.50, 9.18, 6.83, 4.81, 4.81],
}
STATUTE_CITE = {
    2018: ("SI 2018/455 reg 2(2) and reg 2(3)(a)-(d), in force 1 April 2018; the age wording is in SI 2015/621 reg 4A as in force that day, because 2018/455 substitutes figures only"),
    2019: "SI 2019/603 reg 2(2) and reg 2(3), in force 1 April 2019",
    2021: "SI 2021/329 reg 2(2) and reg 2(3)(a), in force 1 April 2021",
    2022: "SI 2022/382 reg 2, in force 1 April 2022",
}
# Ages that must not be read as boundaries, with the provision that excludes them.
EXCLUDED_AGES = {
    16: "lower bound is compulsory school age, not a birthday; NMWA 1998 s.1(2)(c)",
    17: "lower bound is compulsory school age, not a birthday; NMWA 1998 s.1(2)(c)",
    19: "apprentice rate crosses the age bands; NMWR 2015 reg 5(1), limbs disjunctive",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm1", type=pathlib.Path, default=ARM1)
    ap.add_argument("--profile", type=pathlib.Path, default=PROFILE)
    ap.add_argument("--kink", type=pathlib.Path, default=KINK)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    args = ap.parse_args()

    a1 = json.loads(args.arm1.read_text(encoding="utf-8"))
    pr = json.loads(args.profile.read_text(encoding="utf-8"))
    kk = json.loads(args.kink.read_text(encoding="utf-8"))
    pooled = a1["pooled"]
    order = a1["order"]
    visible = a1["config"]["visible_multiple"]

    print("=" * 78)
    print("B34 LFS arm, step 6: arm three, the placebo, and arm four, structure.")
    print("=" * 78)

    # ---------------- arm three ---------------------------------------------
    print("\nPLACEBO GAPS, the gaps no statutory floor rises in")
    print("   %-6s %-7s %-10s %-10s %-10s"
          % ("year", "gap", "break/N", "flat/N", "mean excess/se"))
    placebo, statutory = {}, {}
    for k in sorted(pooled, key=lambda s: (int(s.split("|")[0]),
                                           int(s.split("|")[1].split("-")[0]))):
        y, g = k.split("|")
        y = int(y)
        blk = pooled[k]
        (statutory if blk["named"] else placebo).setdefault(y, {})[g] = blk
        if not blk["named"]:
            print("   %-6d %-7s %-10s %-10s %+.2f"
                  % (y, g, "%d/%d" % (blk["break"], blk["n"]),
                     "%d/%d" % (blk["flat"], blk["n"]), blk["mean_excess_mult"]))

    loud = {}
    for y in sorted(placebo):
        hits = [g for g, b in placebo[y].items() if b["break"] * 2 >= b["n"]]
        if hits:
            loud[y] = sorted(hits, key=lambda g: int(g.split("-")[0]))
    print("\n   placebo gaps reading a break at >= %.3f se in a majority of the"
          " eight profiles: %s" % (visible, loud or "none, in any rate year"))

    top_not_statutory = {}
    for y in sorted(order):
        b = order[y]
        if not b["top_is_statutory"]:
            top_not_statutory[int(y)] = b["top_gap"]
    print("   rate years whose largest mean excess sits off the statute: %s"
          % (top_not_statutory or "none"))

    print("\n   the flat side, printed because it is an object and not a verdict:")
    for y in sorted(placebo):
        flat = sorted(placebo[y].items(), key=lambda kv: kv[1]["mean_excess_mult"])
        print("      %d flattest gaps: %s" % (y, "  ".join(
            "%s(%+.2f, flat in %d of %d)"
            % (g, b["mean_excess_mult"], b["flat"], b["n"]) for g, b in flat[:3])))

    # ---------------- arm four ----------------------------------------------
    print("\n" + "=" * 78)
    print("ARM FOUR: statute against code, per rate year")
    print("=" * 78)
    code_named_kink = {int(k): list(v)
                       for k, v in kk["config"]["named_positions"].items()}
    code_named_arm1 = {int(k): list(v)
                       for k, v in a1["config"]["named_positions"].items()}
    code_rates = {int(k): list(v)
                  for k, v in pr["config"]["statutory_rates"].items()}
    code_thresholds = {int(k): v for k, v in pr["config"]["thresholds"].items()}

    mismatch = []
    for y in sorted(STATUTE_BOUNDARIES):
        s = list(STATUTE_BOUNDARIES[y])
        for name, got in (("step 3", code_named_kink.get(y)),
                          ("step 4", code_named_arm1.get(y))):
            ok = got == s
            print("   %d boundaries  statute %s  %s %s  %s"
                  % (y, s, name, got, "equal" if ok else "NOT EQUAL"))
            if not ok:
                mismatch.append("%d boundaries %s: %s against %s" % (y, name, got, s))
        r_s, r_c = STATUTE_RATES[y], code_rates.get(y)
        ok = r_c == r_s
        print("   %d rates       statute %s  step 2 %s  %s"
              % (y, r_s, r_c, "equal" if ok else "NOT EQUAL"))
        if not ok:
            mismatch.append("%d rates: %s against %s" % (y, r_c, r_s))
        # the two thresholds actually used must be the two adult bands
        want = sorted([r_s[0], r_s[1]])
        got = sorted(code_thresholds.get(y, {}).values())
        ok = got == want
        print("   %d thresholds  the two adult bands %s  step 2 used %s  %s"
              % (y, want, got, "equal" if ok else "NOT EQUAL"))
        if not ok:
            mismatch.append("%d thresholds: %s against %s" % (y, got, want))
        print("       cite: %s" % STATUTE_CITE[y])

    excluded_hit = []
    for y in sorted(STATUTE_BOUNDARIES):
        for a, why in sorted(EXCLUDED_AGES.items()):
            for name, got in (("step 3", code_named_kink.get(y, [])),
                              ("step 4", code_named_arm1.get(y, []))):
                if a in got:
                    excluded_hit.append("%d %s reads %d as a boundary: %s"
                                        % (y, name, a, why))
    print("\n   ages the statute excludes from the boundary set:")
    for a, why in sorted(EXCLUDED_AGES.items()):
        print("      %d  %s" % (a, why))
    print("   any of them used as a boundary: %s" % (excluded_hit or "none"))

    crit = [
        {"name": "B34-3a no placebo gap carries a break",
         # The number of rate years is counted, never written in. It was
         # written in when there were three, and adding 2018 made the sentence
         # false while every number beside it stayed right.
         "detail": ("no gap outside the statute reads >= %.3f se in a majority of"
                    " that year's profiles, in any of the %d rate years"
                    % (visible, len(order))
                    if not loud else
                    "; ".join("%d: %s" % (y, v) for y, v in sorted(loud.items()))),
         "passed": not loud},
        {"name": "B34-3b the largest excess of each year sits on the statute",
         "detail": ("; ".join("%s top gap %s%s"
                              % (y, order[y]["top_gap"],
                                 "" if order[y]["top_is_statutory"] else " (off statute)")
                              for y in sorted(order))),
         "passed": not top_not_statutory},
        {"name": "B34-4a boundary set, statute equals code",
         "detail": ("all %d rate years equal in both steps that carry the set"
                    % len(STATUTE_BOUNDARIES)
                    if not mismatch else "; ".join(mismatch)),
         "passed": not mismatch},
        {"name": "B34-4b excluded ages never used as boundaries",
         "detail": ("16, 17 and 19 absent from every boundary set"
                    if not excluded_hit else "; ".join(excluded_hit)),
         "passed": not excluded_hit},
    ]
    print("\n" + "=" * 78)
    for c in crit:
        print("   [%s] %s" % ("PASS" if c["passed"] else "FAIL", c["name"]))
        print("          %s" % c["detail"])
    print("=" * 78)

    record = {
        "stage": "B34-LFS-step6",
        "criteria": crit,
        "config": {
            "statute_boundaries": {str(k): v for k, v in STATUTE_BOUNDARIES.items()},
            "statute_rates": {str(k): v for k, v in STATUTE_RATES.items()},
            "statute_cite": {str(k): v for k, v in STATUTE_CITE.items()},
            "excluded_ages": {str(k): v for k, v in EXCLUDED_AGES.items()},
            "visible_multiple": visible,
            "source_records": [args.arm1.name, args.profile.name, args.kink.name],
            "statute_side_written_here": True,
        },
        "placebo": {str(y): placebo[y] for y in placebo},
        "statutory": {str(y): statutory[y] for y in statutory},
        "placebo_break": {str(y): v for y, v in loud.items()},
        "top_gap_off_statute": {str(y): v for y, v in top_not_statutory.items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print("\nwrote %s" % args.out.name)


if __name__ == "__main__":
    main()
