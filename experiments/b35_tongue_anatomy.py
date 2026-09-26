"""B35: what happened to swine tongues in September 2022, read at the atom level.

The D23 gate (b35_d23_tongue_break.py) already ruled that 0206490010 does not
price one good across September 2022 on the China leg, so the three anchor arm
may use January to August only. This file asks the next question, which the gate
did not: WHERE did the tongues come from, and is the move a boundary move or a
demand move.

Three things are computed here and nothing else:

  1. The individual country aggregate, which is not what the feed hands back by
     default. CTY_CODE=* returns the dimension's index table, and that table
     holds continents (5XXX), trade blocs (00xx) and one world total ("-")
     alongside the countries. Adding those to the countries double counts, and
     the doubling is not visible in any name: ASIA and ARUBA look alike. The
     atom filter and its sum check are criterion 1 and 2.

  2. The mass balance across the break. Tongues gain and head meat loses on the
     same leg in the same month; if one code's contents moved into another
     code, the tonnage lost by one should turn up in the other, and the unit
     value of the INCREMENT should look like the source's unit value rather
     than like the destination's old one.

  3. The anatomical control. One tongue, one heart and four feet come off every
     hog, so at the animal those three quantities are locked to each other. Any
     movement in a ratio between them is a statement about the export mix or
     about the code boundary, never about the hog. Hearts and feet are both
     inside 0206.49 and neither is alleged to have moved, so heart over foot is
     the control and tongue over foot is the treated ratio. The reading is an
     ORDERING, not a threshold: the treated ratio must move further in log
     terms than the control does.

What this file does NOT do: decide step against spike. One year cannot separate
a code or registration change (a step that persists into 2023 and is absent in
2021) from a demand episode (a spike present in neither). Criterion 6 registers
that test and maps both of its outcomes before it is run, so that whichever way
it lands there is already a reading waiting for it.

Usage
-----
    python b35_tongue_anatomy.py
    python b35_tongue_anatomy.py --selftest
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b35_census_raw_020630-020649_bycountry.json"
OUT = ROOT / "results" / "b35_tongue_anatomy.json"

TONG, HEART, FOOT, HEAD = ("0206490010", "0206490020",
                           "0206490030", "0206490040")
NAMES = {TONG: "tongues", HEART: "hearts", FOOT: "feet", HEAD: "head meat",
         "0206490050": "skins", "0206490090": "offal nesoi"}
BREAK_MONTH = 9        # fixed by the D23 gate before this file was written
CHINA = "CHINA"

# Per hog: one tongue, one heart, four feet. Used only to say WHICH ratios are
# anatomically locked, never as a yield assumption: no step below divides by
# these numbers or asserts that every tongue and foot is exported.
PER_HOG = {TONG: 1, HEART: 1, FOOT: 4}


def is_atom(code: str) -> bool:
    """True for one country, False for every aggregate in the index table.

    The three aggregate shapes in this feed, all observed on this file:
        "-"      the world total
        "00dd"   trade blocs: EUROPEAN UNION, APEC, OECD, ASEAN, USMCA, ...
        "dXXX"   continents: 1XXX NORTH AMERICA ... 7XXX AFRICA
    A country code is four digits and does not begin with 00.
    """
    return code.isdigit() and len(code) == 4 and not code.startswith("00")


def totals(rows, code, month, leg=None, atoms_only=True):
    """Quantity and value for one commodity-month, optionally on one leg."""
    q = v = 0.0
    for r in rows:
        if r["E_COMMODITY"] != code or r["_month"] != month:
            continue
        if atoms_only and not is_atom(r["CTY_CODE"]):
            continue
        if leg is not None and r["CTY_NAME"] != leg:
            continue
        if leg is None and not atoms_only:
            pass
        q += float(r["QTY_1_MO"])
        v += float(r["ALL_VAL_MO"])
    return q, v


def span(rows, code, months, leg=None, atoms_only=True):
    q = v = 0.0
    for m in months:
        a, b = totals(rows, code, m, leg, atoms_only)
        q += a
        v += b
    return q / len(months), v / len(months), (v / q if q else None)


def non_china(rows, code, month):
    q = v = 0.0
    for r in rows:
        if (r["E_COMMODITY"] == code and r["_month"] == month
                and is_atom(r["CTY_CODE"]) and r["CTY_NAME"] != CHINA):
            q += float(r["QTY_1_MO"])
            v += float(r["ALL_VAL_MO"])
    return q, v


def logmult(a, b):
    """|log(b/a)|, the size of a move with direction removed."""
    if not a or not b:
        return None
    return abs(math.log(b / a))


def run(rows):
    pre = list(range(1, BREAK_MONTH))
    post = list(range(BREAK_MONTH, 13))
    crit = []
    rep = {}

    # ---- 1. the filter, and the sum check the pitfall ledger asks for -------
    agg_rows = [r for r in rows if not is_atom(r["CTY_CODE"])]
    atom_rows = [r for r in rows if is_atom(r["CTY_CODE"])]
    cells = sorted({(r["E_COMMODITY"], r["_month"]) for r in rows
                    if r["CTY_CODE"] == "-"})
    worst = 0.0
    for code, m in cells:
        aq, av = totals(rows, code, m)
        tq = sum(float(r["QTY_1_MO"]) for r in rows
                 if r["E_COMMODITY"] == code and r["_month"] == m
                 and r["CTY_CODE"] == "-")
        tv = sum(float(r["ALL_VAL_MO"]) for r in rows
                 if r["E_COMMODITY"] == code and r["_month"] == m
                 and r["CTY_CODE"] == "-")
        for got, want in ((aq, tq), (av, tv)):
            if want:
                worst = max(worst, abs(got - want) / want)
    rep["rows_total"] = len(rows)
    rep["rows_aggregate"] = len(agg_rows)
    rep["rows_atom"] = len(atom_rows)
    rep["aggregate_labels"] = sorted({(r["CTY_CODE"], r["CTY_NAME"])
                                      for r in agg_rows})
    rep["sumcheck_cells"] = len(cells)
    rep["sumcheck_worst_rel_diff"] = worst
    crit.append({
        "name": "B35-TA-1",
        "kind": "instrument",
        "passed": bool(cells) and worst < 1e-9,
        "detail": (f"atoms sum to the world total row on all {len(cells)} "
                   f"commodity-months, worst relative difference {worst:.3e}; "
                   f"{len(agg_rows)} of {len(rows)} rows are aggregates "
                   f"({len(rep['aggregate_labels'])} distinct labels)"),
    })

    # ---- 2. the trap is live on this very file -----------------------------
    naive_q, _, _ = span(rows, TONG, pre + post, atoms_only=False)
    real_q, _, _ = span(rows, TONG, pre + post)
    infl = naive_q / real_q if real_q else None
    rep["tongue_naive_over_atom"] = infl
    crit.append({
        "name": "B35-TA-2",
        "kind": "known_answer",
        "passed": infl is not None and infl > 1.5,
        "detail": (f"summing every returned row inflates the tongue tonnage by "
                   f"{infl:.3f}x over the atom sum, so this file is one where "
                   f"the wildcard trap changes the answer rather than one "
                   f"where the filter is decoration"),
    })

    # ---- 3. is the rise confined to the China leg --------------------------
    legs = {}
    for code in (TONG, HEAD):
        cn_pre = span(rows, code, pre, leg=CHINA)
        cn_post = span(rows, code, post, leg=CHINA)
        nc_pre = [non_china(rows, code, m)[0] for m in pre]
        nc_post = [non_china(rows, code, m)[0] for m in post]
        all_pre = span(rows, code, pre)
        all_post = span(rows, code, post)
        legs[NAMES[code]] = {
            "atoms_pre_t": all_pre[0] / 1000.0,
            "atoms_post_t": all_post[0] / 1000.0,
            "atoms_mult": (all_post[0] / all_pre[0]) if all_pre[0] else None,
            "atoms_uv_pre": all_pre[2], "atoms_uv_post": all_post[2],
            "china_pre_t": cn_pre[0] / 1000.0,
            "china_post_t": cn_post[0] / 1000.0,
            "china_mult": (cn_post[0] / cn_pre[0]) if cn_pre[0] else None,
            "nonchina_monthly_t": [round(x / 1000.0, 1)
                                   for x in nc_pre + nc_post],
            "nonchina_pre_t": sum(nc_pre) / len(nc_pre) / 1000.0,
            "nonchina_post_t": sum(nc_post) / len(nc_post) / 1000.0,
        }
    rep["legs"] = legs
    t = legs["tongues"]
    share_cn = ((t["china_post_t"] - t["china_pre_t"])
                / (t["atoms_post_t"] - t["atoms_pre_t"])
                if t["atoms_post_t"] != t["atoms_pre_t"] else None)
    nc_mult = (t["nonchina_post_t"] / t["nonchina_pre_t"]
               if t["nonchina_pre_t"] else None)
    rep["tongue_rise_share_on_china"] = share_cn
    rep["tongue_nonchina_mult"] = nc_mult
    crit.append({
        "name": "B35-TA-3",
        "kind": "own_reading",
        "passed": (share_cn is not None and nc_mult is not None
                   and share_cn > 1.0 - abs(nc_mult - 1.0)
                   and abs(math.log(nc_mult)) < abs(math.log(t["atoms_mult"]))),
        "detail": (f"tongues {t['atoms_pre_t']:.0f} -> {t['atoms_post_t']:.0f} "
                   f"t/mo across all countries ({t['atoms_mult']:.2f}x), while "
                   f"the non China leg goes {t['nonchina_pre_t']:.0f} -> "
                   f"{t['nonchina_post_t']:.0f} t/mo ({nc_mult:.2f}x); the "
                   f"China leg carries {share_cn:.3f} of the increment"),
    })

    # ---- 4. mass balance, and the unit value of the increment --------------
    h = legs["head meat"]
    dq_t = (t["atoms_post_t"] - t["atoms_pre_t"]) * 1000.0
    dq_h = (h["atoms_post_t"] - h["atoms_pre_t"]) * 1000.0
    _, tv_pre, _ = span(rows, TONG, pre)
    _, tv_post, _ = span(rows, TONG, post)
    inc_uv = ((tv_post - tv_pre) / dq_t) if dq_t else None
    rep["tongue_gain_kg_per_mo"] = dq_t
    rep["headmeat_loss_kg_per_mo"] = dq_h
    rep["mass_balance_ratio"] = (-dq_h / dq_t) if dq_t else None
    rep["increment_unit_value"] = inc_uv
    rep["headmeat_uv_pre"] = h["atoms_uv_pre"]
    rep["tongue_uv_pre"] = t["atoms_uv_pre"]
    d_head = logmult(h["atoms_uv_pre"], inc_uv)
    d_tong = logmult(t["atoms_uv_pre"], inc_uv)
    rep["increment_closer_to"] = ("head meat" if (d_head is not None
                                                 and d_tong is not None
                                                 and d_head < d_tong)
                                  else "old tongues")
    crit.append({
        "name": "B35-TA-4",
        "kind": "own_reading",
        "passed": (dq_t > 0 and dq_h < 0 and d_head is not None
                   and d_tong is not None and d_head < d_tong),
        "detail": (f"tongues gain {dq_t/1000.0:.1f} t/mo while head meat loses "
                   f"{-dq_h/1000.0:.1f} t/mo ({rep['mass_balance_ratio']:.2f} "
                   f"of the gain); the increment prices at "
                   f"${inc_uv:.3f}/kg against head meat's "
                   f"${h['atoms_uv_pre']:.3f} and old tongue's "
                   f"${t['atoms_uv_pre']:.3f}, so it looks like the source and "
                   f"not like the destination"),
    })

    # ---- 5. the anatomical control -----------------------------------------
    ratios = {}
    for scope, leg in (("atoms", None), ("china", CHINA),
                       ("nonchina", "__NONCHINA__")):
        got = {}
        for code in (TONG, HEART, FOOT):
            if leg == "__NONCHINA__":
                a = sum(non_china(rows, code, m)[0] for m in pre) / len(pre)
                b = sum(non_china(rows, code, m)[0] for m in post) / len(post)
            else:
                a = span(rows, code, pre, leg=leg)[0]
                b = span(rows, code, post, leg=leg)[0]
            got[code] = (a, b)
        def rat(n, d):
            a = got[n][0] / got[d][0] if got[d][0] else None
            b = got[n][1] / got[d][1] if got[d][1] else None
            return {"pre": a, "post": b,
                    "mult": (b / a) if (a and b) else None,
                    "logmove": logmult(a, b)}
        ratios[scope] = {"tongue_per_foot": rat(TONG, FOOT),
                         "heart_per_foot": rat(HEART, FOOT),
                         "tongue_per_heart": rat(TONG, HEART)}
    rep["anatomical_ratios"] = ratios
    rep["per_hog"] = {NAMES[k]: v for k, v in PER_HOG.items()}
    a = ratios["atoms"]
    ok5 = (a["tongue_per_foot"]["logmove"] is not None
           and a["heart_per_foot"]["logmove"] is not None
           and a["tongue_per_foot"]["logmove"] > a["heart_per_foot"]["logmove"])
    crit.append({
        "name": "B35-TA-5",
        "kind": "known_answer",
        "passed": bool(ok5),
        "detail": (f"one tongue, one heart and four feet per hog, so these "
                   f"ratios are locked at the animal; tongue over foot moves "
                   f"{a['tongue_per_foot']['mult']:.2f}x while the heart over "
                   f"foot control moves {a['heart_per_foot']['mult']:.2f}x "
                   f"(log sizes {a['tongue_per_foot']['logmove']:.3f} against "
                   f"{a['heart_per_foot']['logmove']:.3f}); on the China leg "
                   f"tongue over heart goes "
                   f"{ratios['china']['tongue_per_heart']['pre']:.2f} -> "
                   f"{ratios['china']['tongue_per_heart']['post']:.2f}"),
    })

    # ---- 7. the union of the two codes is continuous, each part is not ------
    # If a boundary moved between exactly two codes and nothing else happened,
    # then the two codes TOGETHER are invariant: same tonnage, same unit value.
    # This is an identity style check and it needs no yield assumption, no
    # anatomy and no outside data. It is also the sharpest object here, because
    # a demand episode inside one good cannot produce it: a demand episode does
    # not leave the pair invariant while breaking one member.
    def monthly_uv(codes, months, leg):
        out = []
        for m in months:
            q = v = 0.0
            for r in rows:
                if (r["E_COMMODITY"] in codes and r["_month"] == m
                        and is_atom(r["CTY_CODE"])
                        and (leg is None or r["CTY_NAME"] == leg)):
                    q += float(r["QTY_1_MO"])
                    v += float(r["ALL_VAL_MO"])
            out.append((q, v / q if q else None))
        return out

    def overlap(a, b):
        return min(a) <= max(b) and min(b) <= max(a)

    series = {}
    for label, codes in (("tongues", {TONG}), ("head_meat", {HEAD}),
                         ("union", {TONG, HEAD})):
        for legname, leg in (("china", CHINA), ("nonchina_note", None)):
            if legname == "nonchina_note" and label != "union":
                continue
            got = monthly_uv(codes, range(1, 13), leg)
            uv = [u for _, u in got if u is not None]
            series[f"{label}_{legname}"] = {
                "monthly_t": [round(q / 1000.0, 1) for q, _ in got],
                "monthly_uv": [round(u, 4) if u else None for _, u in got],
                "uv_pre_range": [min(uv[:BREAK_MONTH - 1]),
                                 max(uv[:BREAK_MONTH - 1])],
                "uv_post_range": [min(uv[BREAK_MONTH - 1:]),
                                  max(uv[BREAK_MONTH - 1:])],
                "uv_overlap": overlap(uv[:BREAK_MONTH - 1], uv[BREAK_MONTH - 1:]),
            }
    rep["continuity"] = series
    ok7 = (series["tongues_china"]["uv_overlap"] is False
           and series["head_meat_china"]["uv_overlap"] is True
           and series["union_china"]["uv_overlap"] is True)
    crit.append({
        "name": "B35-TA-7",
        "kind": "known_answer",
        "passed": bool(ok7),
        "detail": (
            "on the China leg the tongue unit value ranges do not overlap "
            f"({series['tongues_china']['uv_pre_range'][0]:.3f}-"
            f"{series['tongues_china']['uv_pre_range'][1]:.3f} against "
            f"{series['tongues_china']['uv_post_range'][0]:.3f}-"
            f"{series['tongues_china']['uv_post_range'][1]:.3f}), while head "
            "meat's own price ranges do overlap and so do the ranges of the "
            "two codes taken together "
            f"({series['union_china']['uv_pre_range'][0]:.3f}-"
            f"{series['union_china']['uv_pre_range'][1]:.3f} against "
            f"{series['union_china']['uv_post_range'][0]:.3f}-"
            f"{series['union_china']['uv_post_range'][1]:.3f}); the pair is "
            "continuous where each member is not"),
    })

    # ---- 8. how much of the post break tongue line is not tongue ------------
    # Two endpoints, both measured on this same leg before the break: the old
    # tongue price and the head meat price. Every post break month is written
    # as a mixture of those two. The pre break months are run through the same
    # arithmetic as a control, where the answer has to come back near zero.
    def endpoints():
        q1 = v1 = q2 = v2 = 0.0
        for m in pre:
            a, b = totals(rows, TONG, m, CHINA)
            q1 += a
            v1 += b
            a, b = totals(rows, HEAD, m, CHINA)
            q2 += a
            v2 += b
        return v1 / q1, v2 / q2

    p_tong, p_head = endpoints()

    def decompose(m, ph):
        q, v = totals(rows, TONG, m, CHINA)
        if not q or p_tong == ph:
            return None
        q_old = (v - ph * q) / (p_tong - ph)
        return {"month": m, "t": q / 1000.0, "uv": v / q,
                "implied_tongue_t": q_old / 1000.0,
                "implied_other_t": (q - q_old) / 1000.0,
                "other_share": (q - q_old) / q}

    dec_pre = [decompose(m, p_head) for m in pre]
    dec_post = [decompose(m, p_head) for m in post]
    share_pre = [d["other_share"] for d in dec_pre]
    share_post = [d["other_share"] for d in dec_post]
    impl_post = [d["implied_tongue_t"] for d in dec_post]
    obs_pre_t = [totals(rows, TONG, m, CHINA)[0] / 1000.0 for m in pre]
    head_loss = (sum(totals(rows, HEAD, m, CHINA)[0] for m in pre) / len(pre)
                 - sum(totals(rows, HEAD, m, CHINA)[0] for m in post) / len(post))
    mixed_in = sum(d["implied_other_t"] for d in dec_post) / len(dec_post)
    rep["mixture"] = {
        "p_tongue_pre_china": p_tong, "p_headmeat_pre_china": p_head,
        "pre": dec_pre, "post": dec_post,
        "other_share_pre_range": [min(share_pre), max(share_pre)],
        "other_share_post_range": [min(share_post), max(share_post)],
        "implied_tongue_post_range_t": [min(impl_post), max(impl_post)],
        "observed_tongue_pre_range_t": [min(obs_pre_t), max(obs_pre_t)],
        "mixed_in_t_per_mo": mixed_in,
        "headmeat_loss_t_per_mo": head_loss / 1000.0,
        "mixed_over_loss": mixed_in / (head_loss / 1000.0) if head_loss else None,
    }
    # The slack here is float noise, not a judgement: the seeded selftest puts
    # the implied flow exactly on the boundary of the observed range, and an
    # exact comparison there turns on the last bit of a division.
    mean_impl = sum(impl_post) / len(impl_post)
    _eps = 1e-9 * max(1.0, max(obs_pre_t))
    inside = (min(obs_pre_t) - _eps <= mean_impl <= max(obs_pre_t) + _eps)
    ok8 = (min(share_post) > max(share_pre) and inside)
    crit.append({
        "name": "B35-TA-8",
        "kind": "own_reading",
        "passed": bool(ok8),
        "detail": (
            f"with the two pre break China leg prices as endpoints "
            f"(${p_tong:.4f} and ${p_head:.4f}), the share of the tongue line "
            f"that prices like head meat runs "
            f"{min(share_pre):+.3f} to {max(share_pre):+.3f} before the break "
            f"and {min(share_post):.3f} to {max(share_post):.3f} after; the "
            f"implied real tongue flow after the break is "
            f"{min(impl_post):.0f}-{max(impl_post):.0f} t/mo, inside the "
            f"observed pre break range {min(obs_pre_t):.0f}-"
            f"{max(obs_pre_t):.0f}, so the tongue flow itself never moved"),
    })

    # ---- 9. does that reading survive the choice of the second endpoint -----
    # The decomposition names one price it did not measure on the moved goods
    # themselves. Sweep it across a band that covers every plausible value and
    # print what the answer does, rather than defending one number.
    sweep = []
    for ph in [0.9 + 0.1 * i for i in range(8)]:
        ds = [decompose(m, ph) for m in post]
        sweep.append({"p_head": ph,
                      "other_share_min": min(d["other_share"] for d in ds),
                      "other_share_mean": sum(d["other_share"] for d in ds) / len(ds)})
    rep["mixture_sweep"] = sweep
    worst_mean = min(s["other_share_mean"] for s in sweep)
    ok9 = worst_mean > 0.5
    crit.append({
        "name": "B35-TA-9",
        "kind": "instrument",
        "passed": bool(ok9),
        "detail": (
            f"sweeping the second endpoint from ${sweep[0]['p_head']:.2f} to "
            f"${sweep[-1]['p_head']:.2f}/kg, the mean share of the post break "
            f"tongue line that is not tongue stays between "
            f"{worst_mean:.3f} and "
            f"{max(s['other_share_mean'] for s in sweep):.3f}, so the majority "
            "reading does not depend on which value inside that band is used"),
    })

    # ---- 6. the test that decides step against spike, mapped before it runs -
    branches = {
        "step": {
            "pattern": ("2021 looks like 2022 January to August, and 2023 "
                        "looks like 2022 September to December"),
            "reading": ("a boundary move: the contents of 0206490010 changed "
                        "in September 2022 and stayed changed, which is what "
                        "the D23 gate already ruled on the China leg and "
                        "which confines the three anchor arm to Jan-Aug for "
                        "2022 and to whole years elsewhere"),
        },
        "spike": {
            "pattern": ("2021 and 2023 both look like 2022 January to August"),
            "reading": ("a demand episode inside one good: the code kept "
                        "carrying the same thing and the arm may use the "
                        "whole of 2022 with the episode named"),
        },
        "neither": {
            "pattern": ("2021 and 2023 differ from each other and from both "
                        "halves of 2022"),
            "reading": ("undecided at this resolution: the series has more "
                        "moving parts than one break, and the arm waits"),
        },
    }
    rep["step_vs_spike"] = {
        "status": "registered, not run",
        "needs": ("US Census intltrade exports, HS10 0206490010 and "
                  "0206490040, CTY_CODE=*, months 2021-01..2021-12 and "
                  "2023-01..2023-12"),
        "why_not_run_here": ("api.census.gov is outside the egress allowlist "
                            "of both shells available to this session; the "
                            "2022 cache was fetched on the machine that owns "
                            "data/b35/ and the same fetcher resumes there"),
        "branches": branches,
    }
    reach = len({json.dumps(b["reading"]) for b in branches.values()})
    crit.append({
        "name": "B35-TA-6",
        "kind": "bookkeeping",
        "passed": reach == len(branches),
        "detail": (f"the step against spike test is named and all "
                   f"{len(branches)} of its outcomes carry distinct readings "
                   f"written before it runs, so no branch can arrive without "
                   f"one; the test itself is not run in this record"),
    })

    # ---- 10. the break is in the composition, not in the volume ------------
    # The question "what is the break" has two candidate answers that look
    # alike in a pre/post mean: the whole leg stepped up in September, or the
    # leg was already climbing all year and only the mix broke. One month on
    # month series each, and the reading is a RANK inside each series rather
    # than a line drawn across both.
    ALL6 = {TONG, HEART, FOOT, HEAD, "0206490050", "0206490090"}
    leg_t = [monthly_uv(ALL6, [m], CHINA)[0][0] for m in range(1, 13)]
    tong_uv = [monthly_uv({TONG}, [m], CHINA)[0][1] for m in range(1, 13)]
    def mom(s):
        return [math.log(s[i + 1] / s[i]) for i in range(len(s) - 1)
                if s[i] and s[i + 1]]
    leg_mom, uv_mom = mom(leg_t), mom(tong_uv)
    br = BREAK_MONTH - 2          # index of the August to September step
    uv_rank = sorted(range(len(uv_mom)), key=lambda i: -abs(uv_mom[i])).index(br)
    leg_rank = sorted(range(len(leg_mom)), key=lambda i: -abs(leg_mom[i])).index(br)
    rep["break_location"] = {
        "leg_total_t_per_mo": [round(x / 1000.0, 1) for x in leg_t],
        "tongue_uv_china": [round(x, 4) for x in tong_uv],
        "leg_month_on_month_log": [round(x, 4) for x in leg_mom],
        "tongue_uv_month_on_month_log": [round(x, 4) for x in uv_mom],
        "aug_to_sep_rank_in_tongue_uv": uv_rank,
        "aug_to_sep_rank_in_leg_total": leg_rank,
        "n_steps": len(uv_mom),
    }
    crit.append({
        "name": "B35-TA-10",
        "kind": "own_reading",
        "passed": uv_rank == 0 and leg_rank > 0,
        "detail": (
            f"among the {len(uv_mom)} month on month steps of 2022, August to "
            f"September is rank {uv_rank + 1} in the China leg tongue unit "
            f"value (log step {uv_mom[br]:+.3f} against a next largest of "
            f"{max(abs(x) for i, x in enumerate(uv_mom) if i != br):.3f}) and "
            f"rank {leg_rank + 1} in the whole leg's tonnage (log step "
            f"{leg_mom[br]:+.3f}, while the leg's largest step is "
            f"{max(leg_mom, key=abs):+.3f}); the leg climbs all year with no "
            "September event, and what breaks in September is the mix"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    """Two seeded checks. Both must fire, or the guard is decoration."""
    ok = True

    # (a) is_atom must separate the three aggregate shapes from countries.
    for c, want in (("5700", True), ("2010", True), ("0026", False),
                    ("0003", False), ("5XXX", False), ("1XXX", False),
                    ("-", False), ("", False)):
        if is_atom(c) != want:
            print("SELFTEST FAIL: is_atom(%r) = %s" % (c, is_atom(c)))
            ok = False

    # (b) a seeded file where the whole story is known: aggregates double the
    #     atoms, and from BREAK_MONTH a fixed tonnage of head meat is declared
    #     under the tongue code at head meat's own price. Every criterion that
    #     claims to see a boundary move must fire here, and the mixture must
    #     recover the tonnage that was moved. A guard that cannot find a move
    #     it was handed is not a guard.
    P_TONG, P_HEART, P_FOOT, P_HEAD = 3.30, 1.40, 2.30, 1.20
    MOVED = 2000.0        # kg per month, head meat declared as tongue
    seed = []
    def row(code, cty, ctyname, month, q, v):
        return {"E_COMMODITY": code, "CTY_CODE": cty, "CTY_NAME": ctyname,
                "_month": month, "QTY_1_MO": str(q), "ALL_VAL_MO": str(v)}
    for m in range(1, 13):
        moved = MOVED if m >= BREAK_MONTH else 0.0
        base = {TONG: (400.0, P_TONG), HEART: (150.0, P_HEART),
                FOOT: (16000.0, P_FOOT), HEAD: (3000.0, P_HEAD)}
        for code, (q, price) in base.items():
            if code == TONG:
                q_cn, v_cn = q + moved, q * price + moved * P_HEAD
            elif code == HEAD:
                q_cn, v_cn = q - moved, (q - moved) * price
            else:
                q_cn, v_cn = q, q * price
            q_jp, v_jp = q * 0.25, q * 0.25 * price
            seed.append(row(code, "5700", CHINA, m, q_cn, v_cn))
            seed.append(row(code, "5880", "JAPAN", m, q_jp, v_jp))
            seed.append(row(code, "5XXX", "ASIA", m, q_cn + q_jp, v_cn + v_jp))
            seed.append(row(code, "-", "TOTAL FOR ALL COUNTRIES", m,
                            q_cn + q_jp, v_cn + v_jp))
    crit, rep = run(seed)
    by = {c["name"]: c for c in crit}
    if not by["B35-TA-1"]["passed"]:
        print("SELFTEST FAIL: sum check should pass on the seeded file")
        ok = False
    if abs(rep["tongue_naive_over_atom"] - 3.0) > 1e-9:
        print("SELFTEST FAIL: seeded inflation should be exactly 3.0, got %r"
              % rep["tongue_naive_over_atom"])
        ok = False
    for name in ("B35-TA-2", "B35-TA-5", "B35-TA-7", "B35-TA-8", "B35-TA-9"):
        if not by[name]["passed"]:
            print("SELFTEST FAIL: %s did not fire on a seeded boundary move"
                  % name)
            ok = False
    got = rep["mixture"]["mixed_in_t_per_mo"] * 1000.0
    if abs(got - MOVED) > 1.0:
        print("SELFTEST FAIL: mixture recovered %.1f kg/mo, seeded %.1f"
              % (got, MOVED))
        ok = False
    pre_share = max(abs(x) for x in rep["mixture"]["other_share_pre_range"])
    if pre_share > 1e-9:
        print("SELFTEST FAIL: the pre break control should read zero, read %r"
              % pre_share)
        ok = False

    # (c) the anatomical control must NOT fire when nothing moved but scale.
    flat = []
    for m in range(1, 13):
        for code, mult, price in ((TONG, 1.0, P_TONG), (HEART, 1.0, P_HEART),
                                  (FOOT, 4.0, P_FOOT), (HEAD, 2.0, P_HEAD)):
            q = (100 if m < BREAK_MONTH else 400) * mult
            flat.append(row(code, "5700", CHINA, m, q * 0.8, q * 0.8 * price))
            flat.append(row(code, "5880", "JAPAN", m, q * 0.2, q * 0.2 * price))
            flat.append(row(code, "-", "TOTAL FOR ALL COUNTRIES", m, q,
                            q * price))
    _, frep = run(flat)
    fa = frep["anatomical_ratios"]["atoms"]
    if abs(fa["tongue_per_foot"]["logmove"]) > 1e-12 or \
       abs(fa["heart_per_foot"]["logmove"]) > 1e-12:
        print("SELFTEST FAIL: ratios moved on a file where only scale changed")
        ok = False

    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    if not SRC.exists():
        print("missing %s" % SRC)
        return 2
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    crit, rep = run(rows)

    print("=" * 74)
    print("B35 tongue anatomy: where the September 2022 tonnage came from")
    print("=" * 74)
    print("rows %d, of which %d aggregate and %d country"
          % (rep["rows_total"], rep["rows_aggregate"], rep["rows_atom"]))
    print("aggregate labels: %s"
          % ", ".join("%s %s" % (c, n) for c, n in rep["aggregate_labels"]))
    print("sum check over %d commodity-months, worst relative diff %.3e"
          % (rep["sumcheck_cells"], rep["sumcheck_worst_rel_diff"]))
    print()
    print("%-12s %9s %9s %7s %9s %9s" % ("", "pre t/mo", "post t/mo", "x",
                                         "uv pre", "uv post"))
    for k, v in rep["legs"].items():
        print("%-12s %9.1f %9.1f %7.2f %9.3f %9.3f"
              % (k, v["atoms_pre_t"], v["atoms_post_t"], v["atoms_mult"],
                 v["atoms_uv_pre"], v["atoms_uv_post"]))
        print("%-12s %9.1f %9.1f %7.2f   (China leg)"
              % ("  of which", v["china_pre_t"], v["china_post_t"],
                 v["china_mult"]))
        print("%-12s %9.1f %9.1f          (non China)"
              % ("  rest", v["nonchina_pre_t"], v["nonchina_post_t"]))
    print()
    print("tongue gain %.1f t/mo, head meat loss %.1f t/mo, ratio %.2f"
          % (rep["tongue_gain_kg_per_mo"] / 1000.0,
             -rep["headmeat_loss_kg_per_mo"] / 1000.0,
             rep["mass_balance_ratio"]))
    print("increment unit value $%.3f/kg, head meat $%.3f, old tongue $%.3f "
          "-> closer to %s"
          % (rep["increment_unit_value"], rep["headmeat_uv_pre"],
             rep["tongue_uv_pre"], rep["increment_closer_to"]))
    print()
    print("anatomical ratios (1 tongue, 1 heart, 4 feet per hog)")
    for scope, d in rep["anatomical_ratios"].items():
        print("  %-9s %-18s %8s %8s %7s"
              % (scope, "", "pre", "post", "x"))
        for rname, r in d.items():
            if r["pre"] is None or r["post"] is None:
                continue
            print("  %-9s %-18s %8.4f %8.4f %7.2f"
                  % ("", rname, r["pre"], r["post"], r["mult"]))
    print()
    for c in crit:
        print("%-5s %-12s %s" % ("PASS" if c["passed"] else "FAIL",
                                 c["name"], c["detail"]))

    rec = {
        "stage": "B35-TA",
        "config": {"break_month": BREAK_MONTH, "source": SRC.name,
                   "atom_rule": "four digits, all numeric, not starting 00",
                   "per_hog": {NAMES[k]: v for k, v in PER_HOG.items()}},
        "criteria": crit,
        "report": rep,
    }
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
