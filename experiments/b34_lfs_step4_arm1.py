"""B34, LFS arm, step 4: score arm one, the position of the break.

Design section 5.3 step 4: report the two numbers of section 5.1 at every band
boundary and judge arm one.

Why this step re-indexes the statistic, and why that is a shape fix and not a
new degree of freedom
---------------------------------------------------------------------------
Step 3 reported ch(a) = p(a+1) - 2 p(a) + p(a-1), indexed by age. Arm one asks
which *boundary* the break sits on, and a statutory boundary is not an age, it
is the gap between two ages: the floor rises on reaching 21, so the pay jump
lies between age 20 and age 21 and shows up in both ch(20) and ch(21) with
opposite signs. A single step between a and a+1 produces ch(a) = -d and
ch(a+1) = +d for a step of size d, and nothing anywhere else. So an age index
cannot say which side of it the boundary is on. That is a scope mismatch
between the criterion and the object, provable on a pure step function with no
data at all.

The fix is to index by gap. For the gap a -> a+1 write

    D(a)      = p(a) - p(a+1)                       the fall across this gap
    excess(a) = D(a) - ( D(a-1) + D(a+1) ) / 2      the fall net of its neighbours

excess is gap-indexed, and it is still a second difference: excess(a) equals
( ch(a+1) - ch(a) ) / 2 exactly. No number in the step 2 record changes, only
which combination of them the criterion reads. Discipline 5, item 2a.

Why the level difference and the survival ratio alone cannot score arm one
-------------------------------------------------------------------------
Section 5.1 fixes the scale by printing both the level difference
delta = p(a+1) - p(a) and the survival ratio r = p(a+1) / p(a), judging on the
ratio. Both are printed here at every gap, statutory and not, because the
profile falls at nearly every year of age: r < 1 almost everywhere, so
"the boundary is visible in r" is true at gaps that no statute touches, and the
FAIL branch of arm one would not be reachable. `D15` requires every branch to be
reachable before the run. The comparison the design intends is between the
statutory gaps and the rest, which is the same comparison arm three makes, and
excess is the statistic that makes it.

Floors
------
Independent age cells (step 1 measured 0 of 8 entry cohorts appearing twice),
so with p and its binomial se from the step 2 record:

    excess(a) = -0.5 p(a-1) + 1.5 p(a) - 1.5 p(a+1) + 0.5 p(a+2)
    se        = sqrt( 0.25 se(a-1)^2 + 2.25 se(a)^2
                      + 2.25 se(a+1)^2 + 0.25 se(a+2)^2 )

    log r     = log p(a+1) - log p(a)
    se(log r) = sqrt( (se(a+1)/p(a+1))^2 + (se(a)/p(a))^2 )

The visibility multiple is 1.645, the same constant the arm two step uses, from
the single-sided critical value that makes `D14` and `D17` the same inequality.
It is a resolution floor in the sense of `D24`, not a band around a rival's
point prediction.

Sign convention, stated before the numbers
------------------------------------------
excess(a) > 0 means the profile falls faster across this gap than across its
neighbours, which is what a statutory floor rising in this gap looks like.
excess(a) < 0 means this gap is flatter than its neighbours.

Usage
-----
    python experiments/b34_lfs_step4_arm1.py
"""

import argparse
import json
import math
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
IN = REPO / "results" / "b34_lfs_profile.json"
OUT = REPO / "results" / "b34_lfs_arm1.json"

# Ages at which the statutory floor rises, per rate year. Same table as step 3,
# from the statutory instruments recorded in the results document. A boundary
# at age b sits in the gap b-1 -> b.
NAMED = {2018: (18, 21, 25), 2019: (18, 21, 25),
         2021: (18, 21, 23), 2022: (18, 21, 23)}
NAMED_SOURCE = {2018: "SI 2018/455 with SI 2015/621 reg 4A, age boundaries for rate year 2018-19",
                2019: "SI 2019/603, age boundaries for rate year 2019-20",
                2021: "SI 2021/329, age boundaries for rate year 2021-22",
                2022: "SI 2022/382, age boundaries for rate year 2022-23"}

KEY_SUFFIX = "|unweighted"
VISIBLE = 1.645
VISIBLE_SOURCE = ("single-sided critical value; the multiple at which `D14` and "
                  "`D17` are the same inequality")

# The gap range scored. The profile runs 16 to 30; excess needs four consecutive
# ages, so the scorable gaps run 17->18 to 28->29. Both ends are reported.
GAP_LO, GAP_HI = 16, 29


def year_of(key):
    head = key.split("|")[0]
    return int(head) if head.isdigit() else None


def gaps(points, named):
    """delta, survival ratio and excess for every gap a -> a+1."""
    by_age = {r["age"]: r for r in points if r.get("p") is not None}
    out = []
    for a in sorted(by_age):
        if (a + 1) not in by_age:
            continue
        if a < GAP_LO or a + 1 > GAP_HI:
            continue
        lo, hi = by_age[a], by_age[a + 1]
        delta = hi["p"] - lo["p"]
        se_delta = math.sqrt(lo["se_binom"] ** 2 + hi["se_binom"] ** 2)
        r = hi["p"] / lo["p"] if lo["p"] > 0 else None
        if r is not None and r > 0 and lo["p"] > 0 and hi["p"] > 0:
            se_logr = math.sqrt((hi["se_binom"] / hi["p"]) ** 2
                                + (lo["se_binom"] / lo["p"]) ** 2)
            logr_mult = abs(math.log(r)) / se_logr if se_logr > 0 else None
        else:
            se_logr = logr_mult = None
        row = {
            "gap": "%d-%d" % (a, a + 1),
            "a": a,
            "boundary_age": a + 1,
            "named": (a + 1) in named,
            "n_lo": lo["n"], "n_hi": hi["n"],
            "p_lo": round(lo["p"], 6), "p_hi": round(hi["p"], 6),
            "delta": round(delta, 6),
            "se_delta": round(se_delta, 6),
            "r": round(r, 6) if r is not None else None,
            "se_logr": round(se_logr, 6) if se_logr is not None else None,
            "logr_mult": round(logr_mult, 4) if logr_mult is not None else None,
        }
        # excess needs a-1 and a+2 as well
        if (a - 1) in by_age and (a + 2) in by_age:
            q = by_age[a - 1], by_age[a], by_age[a + 1], by_age[a + 2]
            excess = (-0.5 * q[0]["p"] + 1.5 * q[1]["p"]
                      - 1.5 * q[2]["p"] + 0.5 * q[3]["p"])
            se = math.sqrt(0.25 * q[0]["se_binom"] ** 2
                           + 2.25 * q[1]["se_binom"] ** 2
                           + 2.25 * q[2]["se_binom"] ** 2
                           + 0.25 * q[3]["se_binom"] ** 2)
            row["excess"] = round(excess, 6)
            row["se_excess"] = round(se, 6)
            row["excess_mult"] = round(excess / se, 4) if se > 0 else None
        else:
            row["excess"] = row["se_excess"] = row["excess_mult"] = None
        out.append(row)
    return out


def report(label, rows, named):
    print("\n--- %s ---" % label)
    print("   %-7s %-6s %-9s %-9s %-9s %-9s %-9s %-9s"
          % ("gap", "named", "p_lo", "p_hi", "delta", "r", "|log r|/se", "excess/se"))
    for r in rows:
        print("   %-7s %-6s %-9.4f %-9.4f %-+9.4f %-9.4f %-9s %-9s"
              % (r["gap"], "YES" if r["named"] else "",
                 r["p_lo"], r["p_hi"], r["delta"],
                 r["r"] if r["r"] is not None else float("nan"),
                 ("%.2f" % r["logr_mult"]) if r["logr_mult"] is not None else "n/a",
                 ("%+.2f" % r["excess_mult"]) if r["excess_mult"] is not None else "n/a"))
    scored = [r for r in rows if r["excess_mult"] is not None]
    named_rows = [r for r in scored if r["named"]]
    other_rows = [r for r in scored if not r["named"]]
    seen = [r for r in named_rows if r["excess_mult"] >= VISIBLE]
    extra = [r for r in other_rows if r["excess_mult"] >= VISIBLE]
    flat = [r for r in named_rows if r["excess_mult"] <= -VISIBLE]
    print("   statutory gaps read as a break (excess >= %.3f se): %s of %s  %s"
          % (VISIBLE, len(seen), len(named_rows), [r["gap"] for r in seen]))
    print("   statutory gaps read as flatter than neighbours: %s"
          % ([r["gap"] for r in flat] or "none"))
    print("   non-statutory gaps read as a break: %s of %s  %s"
          % (len(extra), len(other_rows), [r["gap"] for r in extra] or "none"))
    order = sorted(scored, key=lambda r: -(r["excess_mult"]))
    print("   ranked by excess/se, largest first, no line drawn:")
    print("      " + "  ".join("%s%s(%+.2f)" % (r["gap"], "*" if r["named"] else "",
                                                r["excess_mult"]) for r in order))
    return {"rows": rows,
            "named_boundaries": list(named),
            "named_gaps_total": len(named_rows),
            "named_gaps_break": [r["gap"] for r in seen],
            "named_gaps_flat": [r["gap"] for r in flat],
            "other_gaps_total": len(other_rows),
            "other_gaps_break": [r["gap"] for r in extra],
            "ranked": [r["gap"] for r in order]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=pathlib.Path, default=IN)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    args = ap.parse_args()

    rec = json.loads(args.profile.read_text(encoding="utf-8"))
    prof = rec["profile"]
    appr = rec.get("apprentice_two_cells", {})

    print("=" * 78)
    print("B34 LFS arm, step 4: arm one, the position of the break.")
    for _y in sorted(NAMED):
        print("  floor rises at %s in rate year %d, from %s"
              % (list(NAMED[_y]), _y, NAMED_SOURCE[_y]))
    print("  a boundary at age b sits in the gap b-1 -> b, so the gap is the index")
    print("  excess(a) = D(a) - (D(a-1)+D(a+1))/2 with D(a) = p(a) - p(a+1)")
    print("  excess(a) = ( ch(a+1) - ch(a) ) / 2, the step 3 statistic re-indexed")
    print("  visible at %.3f se, %s" % (VISIBLE, VISIBLE_SOURCE))
    print("=" * 78)

    out = {}
    for key in sorted(prof):
        if not key.endswith(KEY_SUFFIX):
            continue
        y = year_of(key)
        if y not in NAMED:
            continue
        out[key] = report(key, gaps(prof[key], NAMED[y]), NAMED[y])

    for key, rows in sorted(appr.items()):
        y = year_of(key)
        if y not in NAMED:
            continue
        pts = [{"age": r["age"], "p": r["p_no_appr"], "n": r["n_all"] - r["n_appr"],
                "se_binom": math.sqrt(max(r["p_no_appr"] * (1.0 - r["p_no_appr"]), 0.0)
                                      / max(r["n_all"] - r["n_appr"], 1))}
               for r in rows]
        out[key + "|no_apprentices"] = report(
            key + " (apprentices held out)", gaps(pts, NAMED[y]), NAMED[y])

    # ---- pooled tallies, printed per gap across all profiles -----------------
    print("\n" + "=" * 78)
    print("POOLED: how often each gap reads as a break, over all %d profiles" % len(out))
    print("=" * 78)
    tally = {}
    for key, blk in out.items():
        y = year_of(key)
        for r in blk["rows"]:
            if r["excess_mult"] is None:
                continue
            t = tally.setdefault((y, r["gap"]), {"named": r["named"], "n": 0,
                                                 "break": 0, "flat": 0, "mults": []})
            t["n"] += 1
            t["mults"].append(r["excess_mult"])
            if r["excess_mult"] >= VISIBLE:
                t["break"] += 1
            if r["excess_mult"] <= -VISIBLE:
                t["flat"] += 1
    print("   %-6s %-7s %-6s %-10s %-10s %-10s"
          % ("year", "gap", "named", "break/N", "flat/N", "mean excess/se"))
    for (y, g) in sorted(tally, key=lambda k: (k[0], int(k[1].split("-")[0]))):
        t = tally[(y, g)]
        print("   %-6d %-7s %-6s %-10s %-10s %+.2f"
              % (y, g, "YES" if t["named"] else "",
                 "%d/%d" % (t["break"], t["n"]), "%d/%d" % (t["flat"], t["n"]),
                 sum(t["mults"]) / len(t["mults"])))

    # ---- criteria -----------------------------------------------------------
    # Arm one asks where the break falls, which is an ordering question, so it is
    # scored on the ordering. Counting how many of the eight profiles clear a
    # multiple would treat eight readings of the same quantity off overlapping
    # data as eight independent votes, and discipline 11 bans the all-of-N shape
    # for exactly that reason. The count is printed above and judges nothing.
    #
    # The null is enumerated, not sampled and not assumed: with G scorable gaps
    # of which K are statutory, every one of the C(G, K) placements is written
    # out and the rank sum of the statutory gaps is read off. No constant enters.
    import itertools

    def rank_block(y):
        rows = [(g, t2["mean"], t2["named"]) for (yy, g), t2 in means.items() if yy == y]
        rows.sort(key=lambda z: -z[1])
        ranks = {g: i + 1 for i, (g, _m, _n) in enumerate(rows)}
        named = [g for (g, _m, nm) in rows if nm]
        other = [g for (g, _m, nm) in rows if not nm]
        obs = sum(ranks[g] for g in named)
        G, K = len(rows), len(named)
        dist = [sum(c) for c in itertools.combinations(range(1, G + 1), K)]
        le = sum(1 for d in dist if d <= obs)
        return {"gaps_scored": G, "statutory": K,
                "ranks": {g: ranks[g] for g in named},
                "rank_sum": obs,
                "rank_sum_min": K * (K + 1) // 2,
                "rank_sum_expected": round(K * (G + 1) / 2.0, 2),
                "exact_p_le": round(le / len(dist), 4),
                "top_gap": rows[0][0], "top_is_statutory": rows[0][2],
                "best_named_mean": max(m for (_g, m, nm) in rows if nm),
                "best_other_mean": max(m for (_g, m, nm) in rows if not nm),
                "other_above_all_named": [g for g in other
                                          if ranks[g] < min(ranks[x] for x in named)],
                "order": [g + ("*" if nm else "") for (g, _m, nm) in rows]}

    means = {(y, g): {"mean": sum(t2["mults"]) / len(t2["mults"]),
                      "named": t2["named"]} for (y, g), t2 in tally.items()}
    blocks = {y: rank_block(y) for y in sorted({y for (y, _g) in tally})}

    print("\n" + "=" * 78)
    print("ORDER: gaps ranked by mean excess/se within each rate year, * statutory")
    print("=" * 78)
    for y in sorted(blocks):
        b = blocks[y]
        print("   %d  %s" % (y, "  ".join(b["order"])))
        print("      statutory ranks %s of %d, rank sum %d (min %d, chance %.2f),"
              " exact p(rank sum this low or lower) = %.4f"
              % (list(b["ranks"].values()), b["gaps_scored"], b["rank_sum"],
                 b["rank_sum_min"], b["rank_sum_expected"], b["exact_p_le"]))
        print("      non-statutory gaps ranking above every statutory one: %s"
              % (b["other_above_all_named"] or "none"))

    pooled_obs = sum(b["rank_sum"] for b in blocks.values())
    pooled_exp = sum(b["rank_sum_expected"] for b in blocks.values())
    # exact pooled null: convolve the three per-year distributions
    conv = {0: 1}
    for y in sorted(blocks):
        G, K = blocks[y]["gaps_scored"], blocks[y]["statutory"]
        d = {}
        for c in itertools.combinations(range(1, G + 1), K):
            d[sum(c)] = d.get(sum(c), 0) + 1
        nxt = {}
        for a in conv:
            for b2 in d:
                nxt[a + b2] = nxt.get(a + b2, 0) + conv[a] * d[b2]
        conv = nxt  # exact convolution; a dict comprehension here would
                    # overwrite colliding sums instead of adding them
    tot = sum(conv.values())
    pooled_p = sum(v for k2, v in conv.items() if k2 <= pooled_obs) / tot
    print("   pooled rank sum %d against chance %.2f, exact p = %.5f"
          % (pooled_obs, pooled_exp, pooled_p))

    # Alpha is not a new constant. Section 8.1 fixes the visibility multiple at
    # 1.645, which is the single-sided 5 per cent critical value; `D17` shows that
    # multiple is what makes the power gate and the readability gate the same
    # inequality. So this station already carries a single-sided 0.05, and the
    # ordering criterion is read against it.
    ALPHA = 0.05
    chance_rank = None

    # branch one: does the order beat chance, pooled. One statistic, one exact null.
    c1a_pass = pooled_p <= ALPHA
    # branch two, registered as the finer-partition FAIL of arm one: a gap the
    # statute does not touch, ranked above every gap it does.
    c1b_bad = {y: blocks[y]["other_above_all_named"] for y in blocks
               if blocks[y]["other_above_all_named"]}
    # branch three, registered as the coarser-partition FAIL: a statutory gap
    # ranked worse than the rank chance alone would give it, (G+1)/2. That number
    # is the null's own centre, not a chosen line.
    c1c_bad = {}
    for y in sorted(blocks):
        b = blocks[y]
        mid = (b["gaps_scored"] + 1) / 2.0
        chance_rank = mid
        worse = [g for g, r in b["ranks"].items() if r > mid]
        if worse:
            c1c_bad[y] = worse

    crit = [
        {"name": "B34-1a the break sits on the statutory gaps, by order",
         "detail": "; ".join(
             "%d rank sum %d against chance %.1f, exact p %.4f, ranks %s"
             % (y, blocks[y]["rank_sum"], blocks[y]["rank_sum_expected"],
                blocks[y]["exact_p_le"], list(blocks[y]["ranks"].values()))
             for y in sorted(blocks))
         + "; pooled rank sum %d against %.1f, exact p %.5f, single-sided alpha %.2f"
         % (pooled_obs, pooled_exp, pooled_p, ALPHA),
         "passed": bool(c1a_pass)},
        {"name": "B34-1b no gap outside the statute outranks every gap inside it",
         "detail": ("clean in all three rate years" if not c1b_bad else
                    "; ".join("%d: %s" % (y, v) for y, v in sorted(c1b_bad.items()))
                    + "; clean in %s"
                    % ([y for y in sorted(blocks) if y not in c1b_bad] or "none")),
         "passed": not c1b_bad},
        {"name": "B34-1c no statutory gap ranks worse than chance would give it",
         "detail": ("every statutory gap ranks better than %.1f of %d"
                    % (chance_rank, blocks[max(blocks)]["gaps_scored"])
                    if not c1c_bad else
                    "; ".join("%d: %s ranked %s, chance rank %.1f"
                              % (y, v, [blocks[y]["ranks"][g] for g in v],
                                 (blocks[y]["gaps_scored"] + 1) / 2.0)
                              for y, v in sorted(c1c_bad.items()))
                    + "; clean in %s"
                    % ([y for y in sorted(blocks) if y not in c1c_bad] or "none")),
         "passed": not c1c_bad},
    ]
    print("\n" + "=" * 78)
    for c in crit:
        print("   [%s] %s" % ("PASS" if c["passed"] else "FAIL", c["name"]))
        print("          %s" % c["detail"])
    print("   1a is the position question and it is scored on the order alone.")
    print("   1b and 1c are the two FAIL directions registered for arm one:")
    print("   a break the statute does not write, and a boundary with no break.")
    print("=" * 78)

    record = {
        "stage": "B34-LFS-step4",
        "criteria": crit,
        "config": {
            "named_positions": {str(k): list(v) for k, v in NAMED.items()},
            "named_source": {str(k): v for k, v in NAMED_SOURCE.items()},
            "profile_key_suffix": KEY_SUFFIX,
            "visible_multiple": VISIBLE,
            "visible_multiple_source": VISIBLE_SOURCE,
            "gap_range": [GAP_LO, GAP_HI],
            "index": "gap a -> a+1; a statutory boundary at age b sits in gap b-1 -> b",
            "excess": "excess(a) = D(a) - (D(a-1)+D(a+1))/2 = (ch(a+1) - ch(a))/2",
            "line_drawn_on_delta_or_r": False,
            "source_record": args.profile.name,
        },
        "order": {str(y): blocks[y] for y in blocks},
        "pooled_rank_sum": {"observed": pooled_obs,
                            "expected_by_chance": pooled_exp,
                            "exact_p_le": round(pooled_p, 6)},
        "pooled": {"%d|%s" % (y, g): {"named": t["named"], "n": t["n"],
                                      "break": t["break"], "flat": t["flat"],
                                      "mean_excess_mult": round(
                                          sum(t["mults"]) / len(t["mults"]), 4)}
                   for (y, g), t in tally.items()},
        "gaps": out,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print("\nwrote %s" % args.out.name)


if __name__ == "__main__":
    main()
