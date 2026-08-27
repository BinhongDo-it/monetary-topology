# -*- coding: utf-8 -*-
"""E1: elite seats per candidate, by province, and where the advantage sits.

**Not a framework reading.** E1 reuses C3's carrier and a second compilation to
ask how a quota system allocates, which the framework does not speak to. It is
kept apart from C3 so that neither is read as the other.

**Seats rather than lines, and E1-2 is why.** A filing line is an equilibrium
quantity: seats set aside for local candidates push it down and local
candidates preferring a nearby campus push it up, and no scaling of the line
separates the two. E1-1 measured the line on three two-campus universities and
returned the opposite sign to the allocation story, at a magnitude E1-3 then
showed was inflated by dividing through the host province's table length. **A
seat count is the allocation itself**, fixed before anybody applies, so nothing
about demand enters it.

**The denominator is the pool with a published score segment**, taken from each
province's score-to-rank table at its deepest batch, and it is not the
registration count that circulating comparisons use. The gap between
registering and sitting the common papers differs most between exactly the
provinces being compared, so a registration denominator moves the answer by
tens of per cent in one province and by almost nothing in another. **The two
numbers are not comparable and nothing here should be read against them.**

Three defects in the compilation's own tables, each caught before it reached a
reading and each printed rather than absorbed:

  category    Some provinces carry the same segment table twice, once under
              `文科` and `理科` and once under an empty label and the literal
              string `<NA>`, with identical cumulative counts. Summing over
              labels doubled Anhui's pool, from 468,873 to 937,746, and halved
              its rate. Only labelled categories are summed where any exist.
  depth       A province that publishes segments only down to its undergraduate
              line has a truncated pool. Shanxi reads 0.94 undergraduate seats
              per candidate, which is close to one seat each and is not
              possible, and the batch labels say why. **Only the provinces
              whose tables reach a 专科 batch are compared.**
  coverage    Shaanxi has no enrolment plan in any year of this compilation,
              Beijing has one in two years, and eight provinces have one in
              2022 alone. A province absent from the plans reads as allocating
              nothing to itself, which is an extreme value pointing the way the
              hypothesis does for some provinces and against it for others.

Reads `data/cache/e1/seats_2022.csv`, `data/e1_home_province.json` and the
score-to-rank tables. Writes `results/e1_seat_rates.json`.

    python data/e1_seats.py --year 2022      # builds the cache first
    python experiments/e1_seat_rates.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "gaokao" / "Gaokao-Compass-11M" / "data"
MAP = ROOT / "data" / "e1_home_province.json"
SEATS = ROOT / "data" / "cache" / "e1" / "seats_%s.csv"
OUT = ROOT / "results" / "e1_seat_rates.json"

YEAR = "2022"

PINYIN = {
    "anhui": "安徽", "beijing": "北京", "chongqing": "重庆", "fujian": "福建",
    "gansu": "甘肃", "guangdong": "广东", "guangxi": "广西", "guizhou": "贵州",
    "hainan": "海南", "hebei": "河北", "heilongjiang": "黑龙江", "henan": "河南",
    "hubei": "湖北", "hunan": "湖南", "jiangsu": "江苏", "jiangxi": "江西",
    "jilin": "吉林", "liaoning": "辽宁", "neimenggu": "内蒙古",
    "ningxia": "宁夏", "qinghai": "青海", "shaanxi": "陕西", "shandong": "山东",
    "shanghai": "上海", "shanxi": "山西", "sichuan": "四川", "tianjin": "天津",
    "xinjiang": "新疆", "xizang": "西藏", "yunnan": "云南", "zhejiang": "浙江",
}

#: A category label that names a real examination stream. Anything else is an
#: unlabelled copy, and where labelled rows exist the unlabelled ones repeat
#: them.
STREAM = ("文科", "理科", "综合", "物理", "历史", "文史", "理工")

#: Seats over pool has to lie inside this for both to mean what they say.
#: Above the upper bound a province seats more undergraduates than it has
#: candidates; near zero its plan is empty. The cuts sit in stretches the data
#: leaves empty, printed by E1-6, so neither is doing work another choice would
#: undo.
BAND = (0.1, 1.0)


def inside(seats: int, pool: int) -> bool:
    return bool(pool) and BAND[0] <= seats / pool <= BAND[1]


#: Kept for what it records rather than for what it excludes: the band below
#: catches Zhejiang on its own, and this is the outside reading that says why
#: the source is wrong there.
EXCLUDED = {
    "浙江": ("the source is wrong here and an outside reading says so: this "
             "compilation gives Zhejiang University 1,355 seats nationally in "
             "2022 and none at all in Zhejiang, while a published compilation "
             "of local-intake shares puts it near half"),
}


def pools(year: str = None) -> tuple[dict, dict]:
    """Province -> candidates with a published segment, and how deep it goes."""
    pool, depth = {}, {}
    ydir = SRC / (year or YEAR)
    for p in sorted(os.listdir(ydir)):
        f = ydir / p / "score-range.csv"
        if not f.is_file():
            continue
        prov = PINYIN.get(p, p)
        best, batches = collections.defaultdict(int), collections.Counter()
        with f.open(encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                cat = (r.get("category") or "").strip()
                b = (r.get("batch") or "").strip()
                if b and b != "<NA>":
                    batches[b] += 1
                c = (r.get("cumulative_count") or "").strip()
                if c.isdigit():
                    best[cat] = max(best[cat], int(c))
        named = {k: v for k, v in best.items()
                 if any(k.startswith(x) for x in STREAM)}
        pool[prov] = sum((named or best).values())
        depth[prov] = {
            "reaches": ("专科" if any("专科" in b for b in batches)
                        else "本科 only" if batches else "no batch labels"),
            "batches": dict(sorted(batches.items())),
            "categories_summed": sorted(named or best),
            "unlabelled_copies_dropped": sorted(set(best) - set(named)) if named
            else [],
        }
    return pool, depth


#: Two defensible readings of "a seat at a 985", and they differ by about a
#: factor of two, so the choice is made here and printed rather than left to
#: whichever entry a dictionary happened to keep.
#:
#:   code   only the unit the compilation flags. A university's cooperative,
#:          directed and targeted-programme channels carry their own codes with
#:          the flag off, and they do not count.
#:   name   any unit admitting under the university's name counts, whichever
#:          channel it is.
#:
#: **324 institutions share a name across codes and 49 of those carry
#: inconsistent flags**, so building a name-keyed table by assignment keeps
#: whichever code came last: `北京航空航天大学` reads `other` that way, and
#: Beijing's 985 seats halve. The strongest flag over the codes sharing a name
#: is taken instead.
RANK = {"985": 2, "211": 1, "other": 0}


def tier_tables(home: dict) -> tuple[dict, dict]:
    by_code, by_name = {}, {}
    for v in home.values():
        n = v["name"]
        if v["tier"] != "other":
            by_code[n] = (v["tier"] if RANK[v["tier"]] > RANK.get(
                by_code.get(n, "other"), 0) else by_code[n])
        if RANK[v["tier"]] > RANK.get(by_name.get(n, "other"), 0):
            by_name[n] = v["tier"]
    return by_code, by_name


def main() -> int:
    home = json.loads(MAP.read_text(encoding="utf-8"))["home"]
    by_code, by_name = tier_tables(home)
    tier = by_name
    admin = {v["name"]: v["province"] for v in home.values()}
    pool, depth = pools()

    seats = collections.defaultdict(collections.Counter)
    at_home = collections.defaultdict(collections.Counter)
    with Path(str(SEATS) % YEAR).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if "本科" not in r["batch"]:
                continue
            n, prov, s = r["institution"], r["province"], int(r["seats"])
            t = tier.get(n, "other")
            seats[prov][t] += s
            seats[prov]["all"] += s
            if admin.get(n) == prov:
                at_home[admin[n]][t] += s
            if n in admin:
                at_home[admin[n]][t + "_total"] += s

    criteria: list[dict] = []
    planned = sorted(seats)
    deep = sorted(p for p in pool
                  if depth[p]["reaches"] == "专科" and p in seats
                  and inside(seats[p]["all"], pool[p]))

    # ---- E1-5. What the two compilations cover ---------------------------
    doubled = sorted(p for p in depth if depth[p]["unlabelled_copies_dropped"])
    criteria.append({
        "name": "E1-5 what the compilation covers and what it repeats",
        "detail": ("%d provinces carry an enrolment plan for %s and %d carry a "
                   "score-to-rank table. **%d of those tables reach a 专科 "
                   "batch**, which is the condition for the pool to mean the "
                   "same thing in two provinces, and the seats-over-pool "
                   "band of E1-6 decides which of those are usable. %d "
                   "province(s) carry "
                   "the same segment table twice, once labelled by stream and "
                   "once unlabelled, and summing over labels would double the "
                   "pool: %s"
                   % (len(planned), YEAR, len(pool),
                      sum(1 for p in depth if depth[p]["reaches"] == "专科"),
                      len(doubled), doubled)),
        "passed": True,
        "provinces_with_a_plan": planned,
        "depth": {p: depth[p] for p in sorted(depth)},
        "outside_reading_on_zhejiang": {k: v[0] for k, v in EXCLUDED.items()},
        "compared": deep,
    })

    # ---- E1-6. A bound the numbers have to obey --------------------------
    every = []
    for y in ("2022", "2023", "2024", "2025"):
        f = Path(str(SEATS) % y)
        if not f.is_file():
            continue
        pl, _dp = pools(y)
        sy = collections.Counter()
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if "本科" in r["batch"]:
                    sy[r["province"]] += int(r["seats"])
        for q in sorted(pl):
            if pl[q] and q in sy:
                every.append({"year": y, "province": q, "pool": pl[q],
                              "undergraduate_seats": sy[q],
                              "seats_per_candidate": round(sy[q] / pl[q], 4)})
    every.sort(key=lambda d: d["seats_per_candidate"])
    low = [d for d in every if d["seats_per_candidate"] < BAND[0]]
    high = [d for d in every if d["seats_per_candidate"] > BAND[1]]
    inband = [d["seats_per_candidate"] for d in every
              if BAND[0] <= d["seats_per_candidate"] <= BAND[1]]
    criteria.append({
        "name": "E1-6 seats over pool, which has to lie between two numbers",
        "detail": ("**Above one a province seats more undergraduates than it "
                   "has candidates, and near zero its plan is empty**, so the "
                   "ratio bounds both tables at once. Over %d province-year "
                   "cells it reads %s for the lowest five and then nothing "
                   "until %s, after which %d cells run to %s, then nothing "
                   "until %s. **The cuts at %s and %s sit in those empty "
                   "stretches**, so no other choice inside them would select a "
                   "different set. Outside: %s below and %s above"
                   % (len(every),
                      [d["seats_per_candidate"] for d in every[:5]],
                      min(inband) if inband else None, len(inband),
                      max(inband) if inband else None,
                      high[0]["seats_per_candidate"] if high else None,
                      BAND[0], BAND[1],
                      [(d["province"], d["year"], d["seats_per_candidate"])
                       for d in low],
                      [(d["province"], d["year"], d["seats_per_candidate"])
                       for d in high])),
        "passed": True,
        "reading": ("%d cell(s) fall outside and are not compared"
                    % (len(low) + len(high))),
        "band": list(BAND),
        "ratios": every,
    })

    # ---- E1-7. Elite seats per candidate ---------------------------------
    rates = sorted(
        ({"province": p, "pool": pool[p],
          "seats_985": seats[p]["985"], "seats_211": seats[p]["211"],
          "undergraduate_seats": seats[p]["all"],
          "per_10k_985": round(10000 * seats[p]["985"] / pool[p], 1),
          "per_10k_211": round(10000 * seats[p]["211"] / pool[p], 1),
          "undergraduate_per_candidate": round(seats[p]["all"] / pool[p], 4)}
         for p in deep), key=lambda d: -d["per_10k_985"])
    hi, lo = rates[0], rates[-1]
    span_985 = hi["per_10k_985"] / lo["per_10k_985"]
    span_all = (hi["undergraduate_per_candidate"]
                / lo["undergraduate_per_candidate"])
    # How much of the elite count rests on a name the compilation flags on one
    # code and not on another. The enrolment plans carry no institution code
    # before 2022 and carry one on 27 per cent of rows in 2022, **so the
    # narrower definition is not computable here at all** and the exposure is
    # reported instead of a second table that would only repeat the first.
    shared = collections.defaultdict(set)
    for v in home.values():
        shared[v["name"]].add(v["tier"])
    ambiguous = {n for n, t in shared.items() if len(t) > 1}
    exposed = collections.Counter()
    with Path(str(SEATS) % YEAR).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if "本科" not in r["batch"] or r["province"] not in deep:
                continue
            if tier.get(r["institution"], "other") in ("985", "211"):
                exposed["counted"] += int(r["seats"])
                if r["institution"] in ambiguous:
                    exposed["on an ambiguous name"] += int(r["seats"])
    frac = exposed["on an ambiguous name"] / max(1, exposed["counted"])
    criteria.append({
        "name": "E1-7b how much of the elite count rests on an ambiguous name",
        "detail": ("**324 institution names are carried by more than one code "
                   "and 49 of those carry inconsistent tier flags**, because a "
                   "university's cooperative, directed and targeted channels "
                   "admit under its name on codes with the flag off. A "
                   "name-keyed table built by assignment keeps whichever code "
                   "came last, which reads `北京航空航天大学` as unflagged and "
                   "halves Beijing's count; the strongest flag over the codes "
                   "sharing a name is taken instead. **The narrower reading, "
                   "counting only the flagged code, is not computable from "
                   "these plans**, which carry no code before %s and carry one "
                   "on about a quarter of rows in it. What is computable is "
                   "the exposure: **%d of %d elite seats in the compared "
                   "provinces, %.1f per cent, sit on a name that is flagged on "
                   "one code and not on another**, and that is the upper bound "
                   "on what the wider reading adds"
                   % (YEAR, exposed["on an ambiguous name"], exposed["counted"],
                      100 * frac)),
        "passed": True,
        "reading": "%.1f per cent of the elite seats sit on an ambiguous name"
                   % (100 * frac),
        "exposure": dict(exposed),
        "ambiguous_names": sorted(ambiguous),
    })

    criteria.append({
        "name": "E1-7 elite seats per candidate, on one pool definition",
        "detail": ("over the %d provinces whose pool reaches the same depth: "
                   "985 seats per ten thousand candidates run %s in %s to %s "
                   "in %s, **a factor of %.1f**. Undergraduate seats of every "
                   "kind over the same pools run a factor of %.1f between the "
                   "same two. **The advantage is not in reaching an "
                   "undergraduate place, it is concentrated in the top tier**"
                   % (len(rates), hi["per_10k_985"], hi["province"],
                      lo["per_10k_985"], lo["province"], span_985, span_all)),
        "passed": True,
        "reading": "%.1f times on the top tier against %.1f overall"
                   % (span_985, span_all),
        "rates": rates,
    })

    # ---- E1-8. Where the advantage sits ----------------------------------
    hosted = collections.Counter()
    for v in home.values():
        if v["tier"] in ("985", "211"):
            hosted[(v["province"], v["tier"])] += 1
    share = []
    for p in sorted({q for q, _t in hosted}):
        row = {"province": p,
               "units_985": hosted[(p, "985")], "units_211": hosted[(p, "211")],
               "units": hosted[(p, "985")] + hosted[(p, "211")]}
        for t in ("985", "211"):
            tot = at_home[p][t + "_total"]
            row["home_share_" + t] = (round(at_home[p][t] / tot, 4) if tot
                                      else None)
            row["seats_" + t] = tot
        share.append(row)
    share.sort(key=lambda d: -d["units"])
    named = [d for d in share
             if d["province"] in deep and d["home_share_985"] is not None]
    criteria.append({
        "name": "E1-8 whether the advantage is local favour or the count of "
                "institutions hosted",
        "detail": ("the administering province of every 985 and 211 admitting "
                   "unit, and the share of that unit's seats it sends home. "
                   "**%s administers %d units and %s administers %d**, while "
                   "the home share among the provinces that can be measured "
                   "runs %s. The ministry capped local intake at 30 per cent "
                   "in 2008 and ordered further reduction in 2015, and the "
                   "provinces with the most units sit furthest under it. "
                   "**Read either number alone and it reads backwards**: the "
                   "low home share alone says the host takes no advantage, and "
                   "the seat rate alone says its universities favour it"
                   % (share[0]["province"], share[0]["units"],
                      share[-1]["province"], share[-1]["units"],
                      sorted((d["home_share_985"], d["province"])
                             for d in named))),
        "passed": True,
        "hosted_units": share,
    })

    # ---- E1-9. The same rate in the other years the source can carry ------
    OTHER = ("2023", "2024", "2025")
    per_year = {YEAR: {d["province"]: d["per_10k_985"] for d in rates}}
    sets = {YEAR: deep}
    for y in OTHER:
        f = Path(str(SEATS) % y)
        if not f.is_file():
            continue
        pl, dp = pools(y)
        sy = collections.defaultdict(collections.Counter)
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if "本科" not in r["batch"]:
                    continue
                sy[r["province"]][tier.get(r["institution"], "other")] += \
                    int(r["seats"])
                sy[r["province"]]["all"] += int(r["seats"])
        dy = sorted(q for q in pl
                    if dp[q]["reaches"] == "专科" and q in sy
                    and inside(sy[q]["all"], pl[q]))
        sets[y] = dy
        per_year[y] = {q: round(10000 * sy[q]["985"] / pl[q], 1) for q in dy}

    both_ends = [y for y in sorted(per_year)
                 if hi["province"] in per_year[y] and lo["province"] in per_year[y]]
    spans = {y: round(per_year[y][hi["province"]] / per_year[y][lo["province"]], 2)
             for y in both_ends}
    # The headline pair survives in one year only, so what replicates is the
    # ordering rather than the pair: where the host province of most of the
    # elite units stands among the provinces each year can compare, and how
    # far the top of each year's set sits above its bottom.
    place, top_over_bottom, series = {}, {}, collections.defaultdict(dict)
    zeroes = {}
    for y, v in sorted(per_year.items()):
        if not v:
            continue
        order = sorted(v, key=lambda q: -v[q])
        if hi["province"] in v:
            place[y] = [order.index(hi["province"]) + 1, len(order)]
        # A province with no 985 seat at all is a real reading and not a
        # defect, and it makes the ratio undefined rather than large, so the
        # bottom of the ratio is the lowest non-zero and the zeroes are named.
        nz = [q for q in order if v[q] > 0]
        zeroes[y] = [q for q in order if v[q] == 0]
        if nz:
            top_over_bottom[y] = round(v[nz[0]] / v[nz[-1]], 2)
        for q, r in v.items():
            series[q][y] = r
    criteria.append({
        "name": "E1-9 the same rate in the other years this source can carry",
        "detail": ("**No province's score-to-rank table carries a batch label "
                   "before %s**, so no pool in 2017 to 2021 can be shown to "
                   "reach the same depth as another and the rate has nothing "
                   "to divide by. That is structural and more retrieval from "
                   "this source does not fix it. Of the years that do carry "
                   "one, the comparable sets are %s. **%s and %s hold both "
                   "ends of the headline and %s do not**, so the pair itself "
                   "is a one-year reading: the %s-to-%s ratio is %s. **What "
                   "replicates instead is the ordering.** The host of most of "
                   "the elite units places %s among the provinces each year "
                   "can compare, and the top of each year's set sits %s times "
                   "its bottom"
                   % (YEAR, {y: len(v) for y, v in sorted(sets.items())},
                      both_ends[0] if both_ends else "none",
                      both_ends[-1] if len(both_ends) > 1 else "none",
                      sorted(set(per_year) - set(both_ends)),
                      hi["province"], lo["province"], spans, place,
                      top_over_bottom)),
        "passed": True,
        "reading": ("the pair survives in %d year(s); the ordering survives in "
                    "%d" % (len(spans), len(place))),
        "comparable_sets": {y: v for y, v in sorted(sets.items())},
        "per_10k_985_by_year": {y: dict(sorted(v.items()))
                                for y, v in sorted(per_year.items())},
        "headline_ratio_by_year": spans,
        "host_place_each_year": place,
        "top_over_bottom_each_year": top_over_bottom,
        "provinces_with_no_985_seat": {y: v for y, v in sorted(zeroes.items()) if v},
        "by_province": {q: dict(sorted(v.items()))
                        for q, v in sorted(series.items())},
    })

    record = {
        "stage": "E1",
        "carrier": "provincial enrolment plans and score-to-rank tables, %s"
                   % YEAR,
        "source": "data/cache/e1/seats_%s.csv, data/e1_home_province.json"
                  % YEAR,
        "not_a_framework_reading": (
            "E1 asks how a quota system allocates, which the framework does "
            "not speak to. It is kept apart from C3 so that neither is read "
            "as the other."),
        "diagnostic_only": True,
        "diagnostic_reason": (
            "One year, eleven provinces on one pool definition. Three of the "
            "thirty-one provinces have no enrolment plan in this compilation "
            "for this year and one more is excluded for a source defect an "
            "outside reading confirms; the rest fail the depth condition, so "
            "their pools do not mean the same thing. The station is held open "
            "until the earlier years have a pool definition of their own, "
            "since their score-to-rank coverage runs nine to twenty-one "
            "provinces against twenty-nine here."),
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
    print("\n  %-6s %9s %7s %10s %10s" % ("prov", "pool", "ug/cand",
                                          "985/10k", "211/10k"))
    for d in rates:
        print("  %-6s %9d %7.2f %10.1f %10.1f"
              % (d["province"], d["pool"], d["undergraduate_per_candidate"],
                 d["per_10k_985"], d["per_10k_211"]))
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
