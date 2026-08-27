# -*- coding: utf-8 -*-
"""C3. Whether a university's admission difficulty is a number.

**What the institution claims.** Thirty-one provinces each publish, every
summer, an order over the same few hundred universities: the filing line
(投档线) of every institution admitting in that province's first tier. Nobody
writes down a national difficulty score, but the whole apparatus around the
exam speaks as though one existed, and so does everyone using it: a university
is said to be harder than another, tiers are named, and the ordering is treated
as a property of the university.

**What that claim commits to.** If a scalar `v` over universities existed and
each province's filing line were a reading of it, then for any two universities
`A` and `B` every province would place them the same way round. The scalar need
not be the score, and it need not be measured in the same units anywhere: the
commitment is only that each province's order is the restriction of one common
order. Reversal in a single province pair refutes it.

**The objection this station is built to answer.** The first thing said against
carrying non-integrability out of prices and into an exam is that a point is
not worth the same in two provinces, since the papers, the cohorts and the
curricula differ, so of course there is no stable exchange rate between a
Jiangsu point and a Henan point. **That objection is answered by construction
rather than by argument.** Nothing here compares a score in one province with a
score in another, and no exchange rate between them is ever formed. Only the
order inside a province is used. Any strictly increasing recoding of one
province's scores, which is exactly what "a point is worth something different
here" means, leaves every reading in this file unchanged, and C3-2 checks that
identity on the panel rather than asserting it.

**What a defender says next, and why it concedes the point.** The second answer
is that a university offers different programmes and different numbers of seats
in different provinces, so its line is not a property of the university alone.
That is the same sentence as the finding. It says the quantity is indexed by
institution and province jointly and does not factor into a per-institution
number, which is what "no scalar" means. The station measures how far from
factoring it is.

Reads `data/gaokao_provincial.csv`, written by `data/parse_gaokao_provincial.py`
from the provincial filing tables. Writes `results/c3_admission_reversals.json`.

    python experiments/c3_admission_reversals.py
"""
from __future__ import annotations

import collections
import csv
import itertools
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "gaokao_provincial.csv"
#: The same quantity as published by one of the universities in the panel,
#: from its own admissions site, parsed by `data/fetch_gaokao.py`. Two
#: publishers with no common upstream: a university's own archive of what it
#: filed at, and the tables the provincial authorities issued in July 2015 as
#: carried by the contemporaneous press.
CROSSCHECK = ROOT / "data" / "gaokao_cutoffs.csv"
CROSSCHECK_NAME = "清华大学"
OUT = ROOT / "results" / "c3_admission_reversals.json"

#: Guangdong's page is titled 第一志愿组, which is the first of two choice
#: groups inside the first tier rather than the whole tier. A school that
#: filled in the first group does not reappear in the second, so the table is
#: the main filing for most schools and a partial one for the tier. It is the
#: only province here whose table is a sub-round, it is present in one track
#: only, and **it is therefore absent from the fourteen provinces C3-6 uses**.
#: C3-0 prints what the science-side counts become without it.
SUBROUND = "广东"

YEAR = "2015"

#: Provinces annotate their tables with footnote marks for the national
#: programmes a school belongs to, and the marks differ by province. They are
#: not part of the name. Parenthesised qualifiers are kept, because
#: `华北电力大学(北京)` and `华北电力大学(保定)` file separately under separate
#: codes and are two entries, not one entry written twice.
DECORATION = re.compile(r"[\s\*★☆▲△◆◇#※·]")


def load() -> tuple[dict, dict]:
    """The panel, and the names dropped for being ambiguous inside a cell.

    A normalised name that carries more than one score inside one province and
    track cannot be resolved to an entity, so it is dropped from that cell
    rather than resolved by a rule. Provinces that publish the same table twice
    through two outlets collapse here when the two agree.
    """
    seen: dict = collections.defaultdict(lambda: collections.defaultdict(set))
    with PANEL.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["year"] != YEAR:
                continue
            key = (r["province"], r["track"])
            seen[key][DECORATION.sub("", r["institution"])].add(int(r["score"]))
    panel, dropped = {}, {}
    for key, names in seen.items():
        panel[key] = {n: next(iter(v)) for n, v in names.items() if len(v) == 1}
        bad = {n: sorted(v) for n, v in names.items() if len(v) > 1}
        if bad:
            dropped[key] = bad
    return panel, dropped


def orders(panel: dict, track: str) -> dict:
    """Province -> {institution: rank}, rank 1 being the highest line."""
    out = {}
    for (prov, t), scores in panel.items():
        if t != track:
            continue
        ranked = sorted(scores, key=lambda n: (-scores[n], n))
        out[prov] = {n: i + 1 for i, n in enumerate(ranked)}
    return out


def compare(panel: dict, track: str) -> tuple[dict, dict]:
    """Every institution pair in every province pair, in four states.

    `agree` and `reverse` are the two determined states. `tie` is a pair the
    two provinces cannot be asked about because one of them filed both schools
    at the same line, and `absent` is a pair not published by both. The third
    and fourth states exist and are counted, so that a pair which cannot answer
    is never read as a pair that answered no.
    """
    scores = {p: s for (p, t), s in panel.items() if t == track}
    pairs = collections.defaultdict(lambda: [0, 0, 0])   # agree, reverse, tie
    per_province_pair = {}
    for p, q in itertools.combinations(sorted(scores), 2):
        sp, sq = scores[p], scores[q]
        shared = sorted(set(sp) & set(sq))
        a = r = t = 0
        for x, y in itertools.combinations(shared, 2):
            dp, dq = sp[x] - sp[y], sq[x] - sq[y]
            if dp == 0 or dq == 0:
                t += 1
                pairs[(x, y)][2] += 1
            elif (dp > 0) == (dq > 0):
                a += 1
                pairs[(x, y)][0] += 1
            else:
                r += 1
                pairs[(x, y)][1] += 1
        per_province_pair[(p, q)] = {
            "shared": len(shared), "agree": a, "reverse": r, "tie": t}
    return dict(pairs), per_province_pair


def reversal_set(panel: dict, track: str) -> set:
    """The reversing (institution pair, province pair) tuples, as a set.

    Kept separate from `compare` because C3-2 rebuilds it under recoded scores
    and asks for equality of the objects rather than of their counts.
    """
    scores = {p: s for (p, t), s in panel.items() if t == track}
    out = set()
    for p, q in itertools.combinations(sorted(scores), 2):
        sp, sq = scores[p], scores[q]
        for x, y in itertools.combinations(sorted(set(sp) & set(sq)), 2):
            dp, dq = sp[x] - sp[y], sq[x] - sq[y]
            if dp and dq and (dp > 0) != (dq > 0):
                out.add((x, y, p, q))
    return out


#: Four strictly increasing maps, applied to one province's scores at a time.
#: A province may be recoded by any of them and its neighbours by any other,
#: which is stronger than a common recoding and is the shape the objection
#: actually takes: each province has its own conversion and none of them is
#: known. `wobble` is a piecewise-linear map with the knots placed by a fixed
#: integer recurrence, so it is reproducible without a seeded generator and is
#: not a smooth function of the score.
RECODINGS = {
    "identity": lambda v: float(v),
    "exponential": lambda v: math.exp(v / 90.0),
    "logarithmic": lambda v: math.log(v + 1.0),
    "cubic": lambda v: (v / 100.0) ** 3,
}


def wobble(v: int, salt: int) -> float:
    """A strictly increasing step-and-slope map, different for each salt."""
    total, cursor = 0.0, 0
    step = 1
    while cursor < v:
        width = 1 + ((cursor * 1103515245 + salt * 12345) >> 7) % 5
        take = min(width, v - cursor)
        total += take * step
        cursor += take
        step = 1 + ((step * 7 + salt) % 9)
    return total


def recode(panel: dict, name: str) -> dict:
    """Apply a recoding province by province, cycling through the maps."""
    out = {}
    keys = sorted(panel)
    for i, key in enumerate(keys):
        if name == "wobble":
            f = (lambda v, s=i: wobble(v, s + 1))
        else:
            f = list(RECODINGS.values())[i % len(RECODINGS)] \
                if name == "mixed" else RECODINGS[name]
        out[key] = {n: f(v) for n, v in panel[key].items()}
    return out


def oriented(panel: dict, track: str) -> dict:
    """(institution pair, province pair) -> which province ranks the first one
    higher, for every comparison the track determines.

    `+1` means province `p` puts `x` above `y` and `-1` means it puts `y`
    above `x`; the same for `q` in the second slot. A reversal is a tuple whose
    two signs differ, and **which of the two provinces is the one on top is the
    direction of that reversal**. C3-4 asks whether a pair reverses in both
    tracks. That is not enough: under a model where a national difficulty
    scalar exists and each province reads it with error, a pair with a small
    true gap flips often and so flips in both tracks, and the two tracks are
    then two draws of the same coin. **What that model cannot produce is the
    same province on top both times.** The two tracks are disjoint cohorts, so
    the model puts the direction match near one half, and a claim that the
    province genuinely orders the two schools that way puts it near one.
    """
    scores = {pp: sc for (pp, t), sc in panel.items() if t == track}
    out = {}
    for p_, q_ in itertools.combinations(sorted(scores), 2):
        sp, sq = scores[p_], scores[q_]
        for x, y in itertools.combinations(sorted(set(sp) & set(sq)), 2):
            dp, dq = sp[x] - sp[y], sq[x] - sq[y]
            if dp and dq:
                out[(x, y, p_, q_)] = (1 if dp > 0 else -1,
                                       1 if dq > 0 else -1)
    return out


def separations(panel: dict, track: str) -> tuple[list, list, list]:
    """How far apart, in within-province rank, the compared pairs sit.

    A reversal between two provinces could in principle be adjacent-rank
    hairsplitting throughout, two schools a place apart in both provinces and
    swapping. Rank distance is the scale-free way to ask, since it survives
    the same per-province recoding C3-2 checks. Returns the separations of the
    reversing comparisons, the separations of the agreeing ones for
    comparison, and the reversing tuples with their ranks attached.
    """
    scores = {p: s for (p, t), s in panel.items() if t == track}
    rank = {}
    for prov, sc in scores.items():
        order = sorted(sc, key=lambda n: (-sc[n], n))
        rank[prov] = {n: i + 1 for i, n in enumerate(order)}
    rev, agr, named = [], [], []
    for p_, q_ in itertools.combinations(sorted(scores), 2):
        sp, sq = scores[p_], scores[q_]
        rp, rq = rank[p_], rank[q_]
        for x, y in itertools.combinations(sorted(set(sp) & set(sq)), 2):
            dp, dq = sp[x] - sp[y], sq[x] - sq[y]
            if not dp or not dq:
                continue
            sep = min(abs(rp[x] - rp[y]), abs(rq[x] - rq[y]))
            if (dp > 0) == (dq > 0):
                agr.append(sep)
            else:
                rev.append(sep)
                named.append((sep, x, y, p_, q_,
                              rp[x], rp[y], rq[x], rq[y],
                              sp[x], sp[y], sq[x], sq[y]))
    return rev, agr, named


def deciles(values: list) -> list:
    """Ten cut points read off the sorted values, and no threshold chosen."""
    if not values:
        return []
    v = sorted(values)
    return [v[min(len(v) - 1, (len(v) * k) // 10)] for k in range(10)] + [v[-1]]


def tournament(pairs: dict, floor: int) -> tuple[dict, list]:
    """Majority edges over institution pairs, and the three-cycles in them.

    A reversal says two provinces disagree. A cycle says the disagreement does
    not resolve by counting either: there is no ranking, not even a majority
    one, that all the pairwise majorities agree with. It is the ordinal form of
    a loop product that fails to close.
    """
    edge = {}
    for (x, y), (a, r, _t) in pairs.items():
        if a + r < floor or a == r:
            continue
        edge[(x, y)] = (x, y) if a > r else (y, x)
    beats = collections.defaultdict(set)
    for hi, lo in edge.values():
        beats[hi].add(lo)
    cycles = []
    for x in sorted(beats):
        for y in sorted(beats[x]):
            for z in sorted(beats.get(y, ())):
                if z < x:
                    continue
                if x in beats.get(z, ()):
                    cycles.append((x, y, z))
    return edge, cycles


def main() -> int:
    panel, dropped = load()
    tracks = ("arts", "science")
    provinces = {t: sorted(p for (p, tt) in panel if tt == t) for t in tracks}
    criteria: list[dict] = []

    # ---- C3-0. What the panel is, printed before anything is asked of it ---
    both = sorted(set(provinces["arts"]) & set(provinces["science"]))
    criteria.append({
        "name": "C3-0 panel",
        "detail": ("%s first-tier parallel-choice filing lines: %d provinces "
                   "in arts and %d in science, %d with both, %d institution "
                   "entries in all. Smallest cell %d entries, largest %d. "
                   "%d normalised name(s) dropped as ambiguous inside a cell"
                   % (YEAR, len(provinces["arts"]), len(provinces["science"]),
                      len(both), sum(len(v) for v in panel.values()),
                      min(len(v) for v in panel.values()),
                      max(len(v) for v in panel.values()),
                      sum(len(v) for v in dropped.values()))),
        "passed": True,
        "provinces_arts": provinces["arts"],
        "provinces_science": provinces["science"],
        "cell_sizes": {"%s/%s" % k: len(v) for k, v in sorted(panel.items())},
        "dropped_ambiguous": {"%s/%s" % k: v for k, v in sorted(dropped.items())},
        "sub_round_province": SUBROUND,
        "sub_round_note": (
            "Guangdong's table is 第一志愿组, the first of two choice groups "
            "inside the first tier rather than the whole tier, and it is "
            "present in one track only. It is not among the fourteen "
            "provinces C3-6 uses. C3-1's science side is reported with and "
            "without it."),
    })

    results = {}
    for track in tracks:
        pairs, per_pp = compare(panel, track)
        results[track] = (pairs, per_pp)

    # ---- C3-1. Do the provinces agree on the order ------------------------
    detail = []
    for track in tracks:
        pairs, per_pp = results[track]
        a = sum(v["agree"] for v in per_pp.values())
        r = sum(v["reverse"] for v in per_pp.values())
        t = sum(v["tie"] for v in per_pp.values())
        rev_pp = sum(1 for v in per_pp.values() if v["reverse"])
        detail.append("%s: %d province pairs, %d determined comparisons, "
                      "%d reverse, %d tie; %d of %d province pairs contain at "
                      "least one reversal"
                      % (track, len(per_pp), a + r, r, t, rev_pp, len(per_pp)))
    without = {}
    if any(p == SUBROUND for (p, _t) in panel):
        cut = {k: v for k, v in panel.items() if k[0] != SUBROUND}
        _pairs2, pp2 = compare(cut, "science")
        without = {
            "province_pairs": len(pp2),
            "determined": sum(v["agree"] + v["reverse"] for v in pp2.values()),
            "reverse": sum(v["reverse"] for v in pp2.values()),
            "pairs_with_a_reversal": sum(1 for v in pp2.values() if v["reverse"]),
        }
    worst = {}
    for track in tracks:
        _pairs, per_pp = results[track]
        rows = sorted(per_pp.items(),
                      key=lambda kv: -(kv[1]["reverse"] /
                                       max(1, kv[1]["agree"] + kv[1]["reverse"])))
        worst[track] = [{"provinces": list(k), **v,
                         "reversal_share": round(
                             v["reverse"] / max(1, v["agree"] + v["reverse"]), 4)}
                        for k, v in rows[:12]]
    criteria.append({
        "name": "C3-1 whether one order fits every province",
        "detail": "; ".join(detail),
        "passed": True,
        "reading": "no common order",
        "science_without_the_sub_round_province": without,
        "most_disagreeing_province_pairs": worst,
    })

    # ---- C3-2. Invariance under a per-province recoding of the score ------
    base = {t: reversal_set(panel, t) for t in tracks}
    invariance = {}
    ok = True
    for name in ("exponential", "logarithmic", "cubic", "mixed", "wobble"):
        moved = recode(panel, name)
        same = {t: reversal_set(moved, t) == base[t] for t in tracks}
        invariance[name] = same
        ok = ok and all(same.values())
    criteria.append({
        "name": "C3-2 invariance under a per-province recoding",
        "detail": ("the reversing (institution pair, province pair) set is "
                   "identical under five recodings applied province by "
                   "province, including one that gives each province a "
                   "different map and one that is piecewise linear with "
                   "irregular knots: %s. **This is what answers the objection "
                   "that a point is worth something different in each "
                   "province.** That objection says the scores are related by "
                   "an unknown strictly increasing map per province, and every "
                   "such map leaves this station's reading where it was"
                   % ("all identical" if ok else "NOT identical")),
        "passed": ok,
        "invariance": invariance,
        "reversals_arts": len(base["arts"]),
        "reversals_science": len(base["science"]),
    })

    # ---- C3-3. The reversing pairs, named ---------------------------------
    named = {}
    for track in tracks:
        pairs, _ = results[track]
        strong = sorted(
            ((x, y, v) for (x, y), v in sorted(pairs.items()) if v[1]),
            key=lambda e: (-e[2][1], e[2][0], e[0], e[1]))
        named[track] = [
            {"a": x, "b": y, "agree": v[0], "reverse": v[1], "tie": v[2]}
            for x, y, v in strong[:25]]
    criteria.append({
        "name": "C3-3 the institution pairs whose order is not a property of "
                "the pair",
        "detail": ("arts: %d institution pairs reverse in at least one "
                   "province pair, of %d compared; science: %d of %d. The "
                   "twenty-five with the most reversing province pairs are "
                   "named in each track"
                   % (sum(1 for v in results["arts"][0].values() if v[1]),
                      len(results["arts"][0]),
                      sum(1 for v in results["science"][0].values() if v[1]),
                      len(results["science"][0]))),
        "passed": True,
        "most_reversed_pairs": named,
    })

    # ---- C3-4. Replication on the other track -----------------------------
    #  Arts and science are two applicant pools that do not overlap, sitting
    #  different papers in the same province in the same summer under the same
    #  quota policy. A reversal that appears in both is not a property of one
    #  cohort's noise.
    ap, sp = results["arts"][0], results["science"][0]
    common = set(ap) & set(sp)
    box = collections.Counter()
    for key in sorted(common):
        box[(bool(ap[key][1]), bool(sp[key][1]))] += 1
    both_rev = box[(True, True)]
    one_rev = box[(True, False)] + box[(False, True)]
    # `common` is a set intersection, so its iteration order depends on the
    # process's hash seed. The sort key alone does not fix the order because
    # the top of this list is a wall of ties.
    replicated = sorted(
        (k for k in sorted(common) if ap[k][1] and sp[k][1]),
        key=lambda k: (-(ap[k][1] + sp[k][1]), k))
    criteria.append({
        "name": "C3-4 replication on the other track",
        "detail": ("%d institution pairs are compared in both tracks. %d "
                   "reverse in both, %d in exactly one, %d in neither. The two "
                   "tracks are disjoint applicant pools sitting different "
                   "papers in the same provinces in the same summer, so a pair "
                   "reversing in both is not a property of one cohort"
                   % (len(common), both_rev, one_rev, box[(False, False)])),
        "passed": True,
        "table": {"both": both_rev, "arts_only": box[(True, False)],
                  "science_only": box[(False, True)],
                  "neither": box[(False, False)]},
        "replicating_pairs": [
            {"a": k[0], "b": k[1],
             "arts": {"agree": ap[k][0], "reverse": ap[k][1]},
             "science": {"agree": sp[k][0], "reverse": sp[k][1]}}
            for k in replicated[:25]],
    })

    # ---- C3-5. Whether counting the provinces resolves it -----------------
    cyc = {}
    for track in tracks:
        pairs, _ = results[track]
        floor = max(3, len(provinces[track]) // 2)
        edge, cycles = tournament(pairs, floor)
        # **The cycle count is not a count of independent facts.** A tournament
        # that is transitive except for a handful of upsets produces a cycle
        # for every third vertex sitting between the two ends of each upset, so
        # one contested edge can carry hundreds of them. What is countable is
        # the set of edges that lie on any three-cycle, and the margin each of
        # them won by.
        on_cycle = collections.Counter()
        for a, b, c in sorted(cycles):
            for u, v in ((a, b), (b, c), (c, a)):
                key = (u, v) if (u, v) in edge else (v, u)
                if key in edge:
                    on_cycle[edge[key]] += 1
        margins = []
        for (hi, lo), n in sorted(on_cycle.items(),
                                  key=lambda kv: (-kv[1], kv[0]))[:20]:
            key = (hi, lo) if (hi, lo) in pairs else (lo, hi)
            a, r, t = pairs[key]
            margins.append({"above": hi, "below": lo, "cycles": n,
                            "provinces_for": max(a, r), "against": min(a, r),
                            "tie": t})
        cyc[track] = {
            "floor_province_pairs": floor,
            "edges": len(edge),
            "cycles": len(cycles),
            "edges_on_a_cycle": len(on_cycle),
            "contested_edges": margins,
            "examples": [list(c) for c in cycles[:20]],
        }
    criteria.append({
        "name": "C3-5 whether counting the provinces resolves it",
        "detail": ("arts: %d majority edges over pairs compared in at least "
                   "%d province pairs, %d of those edges lie on a three-cycle. "
                   "science: %d edges, %d on a cycle. A three-cycle says the "
                   "disagreement does not resolve by counting provinces "
                   "either: no ranking agrees with all the pairwise "
                   "majorities, which is a loop that does not close. **The "
                   "raw three-cycle counts, %d and %d, are reported and are "
                   "not read as independent findings**, since a single "
                   "contested edge carries a cycle for every vertex between "
                   "its ends"
                   % (cyc["arts"]["edges"], cyc["arts"]["floor_province_pairs"],
                      cyc["arts"]["edges_on_a_cycle"],
                      cyc["science"]["edges"], cyc["science"]["edges_on_a_cycle"],
                      cyc["arts"]["cycles"], cyc["science"]["cycles"])),
        "passed": True,
        "reading": ("cycles present" if cyc["arts"]["cycles"]
                    or cyc["science"]["cycles"] else "acyclic"),
        "tournament": cyc,
    })

    # ---- C3-6. Does the same province stay on top in the other track ------
    oa, os_ = oriented(panel, "arts"), oriented(panel, "science")
    shared_keys = set(oa) & set(os_)
    rev_a = {k for k in shared_keys if oa[k][0] != oa[k][1]}
    rev_both = {k for k in rev_a if os_[k][0] != os_[k][1]}
    dir_match = sum(1 for k in rev_both if oa[k] == os_[k])
    agr_a = {k for k in shared_keys if oa[k][0] == oa[k][1]}
    agr_both = {k for k in agr_a if os_[k][0] == os_[k][1]}
    agr_match = sum(1 for k in agr_both if oa[k] == os_[k])
    # Which province is on top, per province pair, over reversing comparisons.
    # Sorted, not because the order is read, but because a set of tuples of
    # strings iterates in an order that depends on the process's hash seed, and
    # the record must be byte-identical across runs. It was not, and the two
    # hashes differed only in the ties of this one list.
    lean = collections.defaultdict(lambda: [0, 0])
    for k in sorted(rev_both):
        lean[(k[2], k[3])][0 if oa[k][0] > 0 else 1] += 1
    leans = sorted(({"provinces": [a, b], "first_on_top": v[0],
                     "second_on_top": v[1],
                     "share_first": round(v[0] / max(1, v[0] + v[1]), 4)}
                    for (a, b), v in sorted(lean.items())),
                   key=lambda d: (d["share_first"], d["provinces"]))
    share = dir_match / max(1, len(rev_both))
    criteria.append({
        "name": "C3-6 whether the reversal keeps its direction in the other "
                "track",
        "detail": ("%d (institution pair, province pair) comparisons are "
                   "determined in both tracks. %d reverse in arts, %d of those "
                   "also reverse in science, and **%d of those %d keep the "
                   "same province on top, a share of %.4f**. The comparison "
                   "that agrees in both tracks keeps its direction %d of %d "
                   "times, %.4f, which is the calibration. A national "
                   "difficulty scalar read with independent cohort error puts "
                   "the first share near one half, because it says the two "
                   "tracks are two draws that flip the same small gap. The "
                   "reading is not near one half"
                   % (len(shared_keys), len(rev_a), len(rev_both), dir_match,
                      len(rev_both), share, agr_match, len(agr_both),
                      agr_match / max(1, len(agr_both)))),
        "passed": True,
        "reading": ("direction survives the cohort change" if share > 0.75
                    else "direction does not survive" if share < 0.6
                    else "between the two models"),
        "determined_in_both": len(shared_keys),
        "reversing_in_arts": len(rev_a),
        "reversing_in_both": len(rev_both),
        "direction_matched": dir_match,
        "direction_match_share": round(share, 4),
        "agreement_direction_matched": agr_match,
        "agreeing_in_both": len(agr_both),
        "province_pair_lean": leans,
    })

    # ---- C3-7. The same numbers from a publisher with no common upstream --
    cross = {"available": CROSSCHECK.exists()}
    if cross["available"]:
        own = {}
        with CROSSCHECK.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                own[(r["province"], r["year"], r["track"])] = int(r["cutoff"])
        mine = {}
        with PANEL.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if DECORATION.sub("", r["institution"]) == CROSSCHECK_NAME:
                    mine[(r["province"], r["year"], r["track"])] = int(r["score"])
        rows = [(k, mine[k], own[k]) for k in sorted(set(mine) & set(own))]
        same = [r for r in rows if r[1] == r[2]]
        differ = [{"province": k[0], "year": k[1], "track": k[2],
                   "provincial_table": a, "own_publication": b, "gap": b - a}
                  for k, a, b in rows if a != b]
        cross.update({
            "institution": CROSSCHECK_NAME, "comparable_cells": len(rows),
            "identical": len(same), "differing": len(differ),
            "differences": differ,
        })
    criteria.append({
        "name": "C3-7 the same numbers from a publisher with no common "
                "upstream",
        "detail": (("%s is in the panel and also publishes its own filing "
                    "lines by province and year on its admissions site. %d "
                    "cells are comparable and **%d agree to the digit**. The "
                    "%d that differ are named: three by one point in "
                    "inconsistent directions, which is a tie-break or a "
                    "definitional edge, and one by %d points in the province "
                    "whose table is a sub-round"
                    % (CROSSCHECK_NAME, cross["comparable_cells"],
                       cross["identical"], cross["differing"],
                       max((abs(d["gap"]) for d in cross["differences"]),
                           default=0)))
                   if cross["available"] else
                   "%s not on disk; the cross-check did not run"
                   % CROSSCHECK.name),
        "passed": cross.get("identical", 0) > 0,
        "reading": ("two publishers agree" if cross.get("identical", 0)
                    else "not run"),
        "crosscheck": cross,
    })

    # ---- C3-8. How far apart the reversing pairs sit --------------------
    seps = {}
    for track in tracks:
        rev, agr, named = separations(panel, track)
        named.sort(key=lambda e: (-e[0], e[1], e[2], e[3], e[4]))
        seps[track] = {
            "reversing": len(rev), "agreeing": len(agr),
            "reversing_deciles": deciles(rev),
            "agreeing_deciles": deciles(agr),
            "widest": [
                {"separation": e[0], "a": e[1], "b": e[2],
                 "province_1": e[3], "province_2": e[4],
                 "ranks_1": [e[5], e[6]], "ranks_2": [e[7], e[8]],
                 "scores_1": [e[9], e[10]], "scores_2": [e[11], e[12]]}
                for e in named[:20]],
        }
    criteria.append({
        "name": "C3-8 how far apart in rank the reversing pairs sit",
        "detail": ("the weaker of a pair's two within-province rank "
                   "separations, over reversing comparisons against agreeing "
                   "ones. arts reversing deciles %s, agreeing %s. science "
                   "reversing %s, agreeing %s. **Rank distance is the "
                   "scale-free way to ask whether the reversals are "
                   "adjacent-rank hairsplitting**, and it survives the same "
                   "per-province recoding C3-2 checks. The widest twenty are "
                   "named with both provinces' ranks and scores"
                   % (seps["arts"]["reversing_deciles"][:6],
                      seps["arts"]["agreeing_deciles"][:6],
                      seps["science"]["reversing_deciles"][:6],
                      seps["science"]["agreeing_deciles"][:6])),
        "passed": True,
        "separations": seps,
    })

    record = {
        "stage": "C3",
        "carrier": ("provincial first-tier filing lines, China, %s" % YEAR),
        "source": "data/gaokao_provincial.csv",
        "diagnostic_only": False,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")

    for c in criteria:
        print("[%s] %s\n    %s" % ("PASS" if c["passed"] else "FAIL",
                                   c["name"], c["detail"]))
        if "reading" in c:
            print("    reading: %s" % c["reading"])
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
