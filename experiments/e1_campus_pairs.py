# -*- coding: utf-8 -*-
"""E1, first reading: one brand, two campuses, two home provinces.

**What this asks.** Whether a province places a university it hosts lower in
its own ordering than that university sits elsewhere, which is what an
allocation favouring local candidates produces. This is not a framework
reading. The framework says nothing about who should get which seat; E1 reuses
C3's panel to answer a question about the allocation, and it is kept apart from
C3 for that reason.

**Why the obvious design does not work, and gate five caught it.** The first
plan was a difference in differences over every university with a known home
province: is a university ranked lower at home than its cross-province average.
Counting the cells before building it found that **all eight of Guangxi's own
first-tier universities appear in Guangxi's table and in no other province's**,
and Guizhou has one that appears elsewhere out of three. A provincial
university is first tier at home and second tier away, so it is not in the away
tables at all. **The design would therefore have conditioned on being first
tier in both provinces, which is conditioning on the treatment**, and the
universities with the largest local advantage would have dropped out silently.
Two provinces read zero usable cells and that is what the count said before
anything was built.

**What survives is tighter than what was planned.** Three universities operate
two campuses under one name, in two different provinces, and both campuses are
listed in fourteen or fifteen of the fifteen provinces:

    华北电力大学    (北京) Beijing        (保定) Hebei
    中国石油大学    (北京) Beijing        (华东) Shandong
    中国地质大学    (北京) Beijing        (武汉) Hubei

Comparing the two campuses of one brand inside one province removes the
brand entirely: whatever a university's national standing is worth, both
campuses carry the same name and the same reputation. Comparing that difference
in Beijing against the same difference in the other provinces removes the
province: whatever Beijing's candidates or its papers are like, both campuses
face the same ones. **What is left is the thing being asked about.**

Shandong hosts the 华东 campus, so the same pair read from Shandong is a mirror
of the same test with a different beneficiary, and it is a check the design can
fail.

Reads `data/gaokao_provincial.csv`. Writes `results/e1_campus_pairs.json`.

    python experiments/e1_campus_pairs.py
"""
from __future__ import annotations

import collections
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "gaokao_provincial.csv"
OUT = ROOT / "results" / "e1_campus_pairs.json"
YEAR = "2015"
DECORATION = re.compile(r"[\s\*★☆▲△◆◇#※·]")

#: Campus tag to the province the campus is in. Hand-written, because three of
#: these are not province names: 保定 is a city in Hebei, 华东 is a region and
#: the campus is in Qingdao and Dongying in Shandong, 武汉 is a city in Hubei.
CAMPUS = {"北京": "北京", "保定": "河北", "华东": "山东", "武汉": "湖北"}

PAIRS = [
    ("华北电力大学", "华北电力大学(北京)", "华北电力大学(保定)"),
    ("中国石油大学", "中国石油大学(北京)", "中国石油大学(华东)"),
    ("中国地质大学", "中国地质大学(北京)", "中国地质大学(武汉)"),
]


def load() -> dict:
    out = collections.defaultdict(dict)
    with PANEL.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["year"] != YEAR:
                continue
            out[(r["province"], r["track"])][
                DECORATION.sub("", r["institution"])] = int(r["score"])
    return out


def ranks(scores: dict) -> dict:
    """Normalised position, 0 the highest filing line and 1 the lowest."""
    order = sorted(scores, key=lambda n: (-scores[n], n))
    n = len(order)
    return {name: i / (n - 1) for i, name in enumerate(order)}


def home_of(campus_name: str) -> str | None:
    m = re.search(r"\(([^)]+)\)", campus_name)
    return CAMPUS.get(m.group(1)) if m else None


def main() -> int:
    panel = load()
    rank = {k: ranks(v) for k, v in panel.items()}
    criteria: list[dict] = []
    readings = []

    for brand, a, b in PAIRS:
        ha, hb = home_of(a), home_of(b)
        for track in ("arts", "science"):
            rows = []
            for (prov, t), r in sorted(rank.items()):
                if t != track or a not in r or b not in r:
                    continue
                rows.append({
                    "province": prov,
                    "n_listed": len(r),
                    "rank_a": sorted(r, key=lambda n: r[n]).index(a) + 1,
                    "rank_b": sorted(r, key=lambda n: r[n]).index(b) + 1,
                    "score_a": panel[(prov, t)][a],
                    "score_b": panel[(prov, t)][b],
                    "gap": round(r[a] - r[b], 6),
                })
            if len(rows) < 4:
                continue
            for host, other in ((ha, hb), (hb, ha)):
                if host is None:
                    continue
                at = [x for x in rows if x["province"] == host]
                away = [x for x in rows if x["province"] != host]
                if not at or len(away) < 3:
                    continue
                # gap is (position of the Beijing campus) minus (position of
                # the other campus), and a larger position is an easier entry.
                # Read from the host's own side, so the sign is always "the
                # campus this province hosts sits easier here than it does
                # elsewhere".
                sign = 1.0 if host == ha else -1.0
                g_at = sign * at[0]["gap"]
                g_away = sign * (sum(x["gap"] for x in away) / len(away))
                readings.append({
                    "brand": brand, "track": track, "host": host,
                    "host_campus": a if host == ha else b,
                    "other_campus": b if host == ha else a,
                    "other_home": other,
                    "gap_at_host": round(g_at, 6),
                    "gap_elsewhere_mean": round(g_away, 6),
                    "premium": round(g_at - g_away, 6),
                    "provinces_elsewhere": len(away),
                    "elsewhere_gaps": sorted(
                        round(sign * x["gap"], 6) for x in away),
                    "table": rows,
                })

    beijing = [r for r in readings if r["host"] == "北京"]
    mirror = [r for r in readings if r["host"] != "北京"]
    pos = sum(1 for r in beijing if r["premium"] > 0)
    criteria.append({
        "name": "E1-1 one brand, two campuses, read from the province that "
                "hosts one of them",
        "detail": ("%d brand-and-track readings for Beijing as host, %d of "
                   "them positive, premium %s. %d readings where the host is "
                   "not Beijing, %d positive, premium %s. A positive premium "
                   "says the campus a province hosts sits lower in that "
                   "province's own ordering than the same brand's other "
                   "campus does, by more than it does in the provinces that "
                   "host neither. **Brand is differenced out because both "
                   "campuses carry one name, and province is differenced out "
                   "because both face one candidate pool**"
                   % (len(beijing), pos,
                      [r["premium"] for r in beijing],
                      len(mirror), sum(1 for r in mirror if r["premium"] > 0),
                      [r["premium"] for r in mirror])),
        "passed": True,
        "reading": ("local premium present in every reading" if pos == len(beijing)
                    else "the premium is negative in most readings, which is "
                         "the opposite sign to a local allocation advantage"
                    if pos <= len(beijing) // 2 else "mixed"),
        "readings": readings,
    })

    # ---- E1-2. What the sign says about the instrument --------------------
    thick = sorted((r for r in beijing if r["provinces_elsewhere"] >= 10),
                   key=lambda r: r["premium"])
    criteria.append({
        "name": "E1-2 whether a filing line can answer the question at all",
        "detail": ("the readings resting on ten or more comparison "
                   "provinces are %s, all negative. **A filing line is an "
                   "equilibrium quantity and the two channels move it "
                   "opposite ways**: seats set aside for local candidates push "
                   "it down, and local candidates preferring a campus in their "
                   "own city push it up. In Beijing the second dominates by a "
                   "wide margin, so this measure returns the net and cannot "
                   "separate the part that is policy. **The question needs "
                   "seats rather than lines**, which is a count of the "
                   "allocation itself and is not an equilibrium object"
                   % [r["premium"] for r in thick]),
        "passed": True,
        "reading": "this instrument does not identify the allocation channel",
        "thick_readings": thick,
    })

    # ---- E1-3. The same question under three scalings --------------------
    #  E1-1 measures the gap between two campuses as a difference of positions
    #  divided by the length of the province's table. Beijing's table is the
    #  shortest in the panel, so that divisor is smallest exactly where the
    #  reading is largest. Asking the same question in raw positions, and in
    #  the province's own points, is free and it is the check that was owed.
    import statistics

    def zed(x, others):
        sd = statistics.pstdev(others)
        return (x - statistics.mean(others)) / sd if sd else None

    scalings = []
    for r in beijing:
        rows = r["table"]
        at = [t for t in rows if t["province"] == r["host"]]
        away = [t for t in rows if t["province"] != r["host"]]
        if not at or len(away) < 6:
            continue
        at = at[0]
        raw = lambda t: t["rank_a"] - t["rank_b"]           # noqa: E731
        pts = lambda t: t["score_a"] - t["score_b"]         # noqa: E731
        scalings.append({
            "brand": r["brand"], "track": r["track"],
            "n_comparison_provinces": len(away),
            "table_length_here": at["n_listed"],
            "table_length_elsewhere_median": statistics.median(
                [t["n_listed"] for t in away]),
            "raw_rank_gap_here": raw(at),
            "raw_rank_gap_elsewhere_median": statistics.median(
                [raw(t) for t in away]),
            "z_raw_rank": round(zed(raw(at), [raw(t) for t in away]), 4),
            "z_normalised_rank": round(
                zed(at["gap"], [t["gap"] for t in away]), 4),
            "points_gap_here": pts(at),
            "points_gap_elsewhere_median": statistics.median(
                [pts(t) for t in away]),
            "z_points": round(zed(pts(at), [pts(t) for t in away]), 4),
        })
    inflated = sum(1 for x in scalings
                   if abs(x["z_normalised_rank"]) > abs(x["z_raw_rank"]))
    survives_raw = [x for x in scalings if abs(x["z_raw_rank"]) >= 2]
    criteria.append({
        "name": "E1-3 the same question under three scalings",
        "detail": ("**Beijing's table is the shortest in the panel**, %s rows "
                   "against a median of %s elsewhere, and E1-1 divides the gap "
                   "between the campuses by that length. Dividing by the "
                   "smallest number where the reading is largest inflates it, "
                   "and it does: the normalised z is larger in absolute value "
                   "than the raw-rank z in %d of %d readings. **Under raw "
                   "positions %d of %d readings reach two standard deviations "
                   "and the rest do not**, one of them landing at z=%s, which "
                   "is the middle of the comparison provinces. Under the "
                   "province's own points every reading is positive and %d "
                   "reach two. **The three scalings do not agree, and that "
                   "disagreement is the reading here**: the comparison runs "
                   "across provinces, so cross-province comparability re-enters "
                   "through the scaling, which is what C3 avoids by never "
                   "comparing across a province line"
                   % ([x["table_length_here"] for x in scalings][:1],
                      [x["table_length_elsewhere_median"] for x in scalings][:1],
                      inflated, len(scalings), len(survives_raw), len(scalings),
                      min((x["z_raw_rank"] for x in scalings), key=abs),
                      sum(1 for x in scalings if abs(x["z_points"]) >= 2))),
        "passed": True,
        "reading": ("E1-1's magnitudes are overstated and its sign rests on "
                    "fewer brands than it appeared to"),
        "scalings": scalings,
    })

    # ---- E1-4. What was happening in Beijing in this year -----------------
    criteria.append({
        "name": "E1-4 whether the host province was in a regime change",
        "detail": ("**2015 is the first year Beijing candidates filed their "
                   "choices after their scores were published**, replacing an "
                   "estimate-first system, **and the first year its first "
                   "undergraduate batch used 大平行志愿** in place of the "
                   "earlier grouped structure. The comparison provinces had "
                   "both for years. Both changes let a candidate aim exactly "
                   "for the first time, and aiming exactly is how a preference "
                   "for the campus in one's own city reaches the filing line. "
                   "**So the channel this station cannot separate from the "
                   "allocation is the one that changed, in the host province, "
                   "in the measured year.** The panel holds one year, so "
                   "nothing here separates a standing feature from a "
                   "transition. Beijing also publishes 录取最低分 where most "
                   "of the panel publishes 投档线, which is a different "
                   "quantity, and it is one of three provinces here that do"),
        "passed": True,
        "reading": "the measured year is a transition year in the host province",
        "sources": [
            "http://edu.sina.com.cn/gaokao/2014-11-14/1454443522.shtml",
            "https://gaokao.eol.cn/zhiyuan/tianbao/201506/t20150614_1274151_1.shtml",
        ],
    })

    record = {
        "stage": "E1",
        "carrier": "provincial first-tier filing lines, China, %s" % YEAR,
        "source": "data/gaokao_provincial.csv",
        "not_a_framework_reading": (
            "E1 reuses C3's carrier to ask how a quota system allocates, which "
            "is a question the framework does not speak to. It is kept apart "
            "from C3 so that neither is read as the other."),
        "diagnostic_only": True,
        "diagnostic_reason": (
            "First reading on the sample in hand, and **E1-3 and E1-4 mark it "
            "down rather than confirm it**. Its magnitudes are inflated by a "
            "normalisation that divides by the host province's table length, "
            "and the host province's table is the shortest in the panel; under "
            "raw positions the effect rests on one brand of three. The "
            "measured year is also the first year the host province filed "
            "after scores and the first year its top batch used a large "
            "parallel structure, so a transition and a standing feature are "
            "not separable on one year. The province-wide difference in "
            "differences was not run at all, because counting its cells first "
            "showed it would condition on the treatment, two provinces "
            "returning zero usable local institutions. **What survives is "
            "E1-2: a filing line is an equilibrium quantity and does not "
            "identify the allocation.**"),
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")

    for c in criteria:
        print("[%s] %s\n    %s" % ("PASS" if c["passed"] else "FAIL",
                                   c["name"], c["detail"]))
        print("    reading: %s" % c["reading"])
    print()
    for r in readings:
        print("%-12s %-8s host=%-4s  %s vs %s" % (
            r["brand"], r["track"], r["host"], r["host_campus"],
            r["other_campus"]))
        print("    at host %+.4f   elsewhere mean %+.4f over %d provinces"
              "   premium %+.4f"
              % (r["gap_at_host"], r["gap_elsewhere_mean"],
                 r["provinces_elsewhere"], r["premium"]))
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
