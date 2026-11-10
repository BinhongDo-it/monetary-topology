"""B138: the split-share reform. A rule drew a class line inside each listed company, and the
reform that erased it wrote a price on it.

Before 2005 most of a Chinese listed company's shares could not trade on the exchange. They carried
the same cash flows and votes as the tradable shares; a rule kept them off the market. The 2005-2006
reform let them trade, and in each company the holders of non-tradable shares paid the holders of
tradable A shares a published consideration for it.

**The conversion.** One company: tradable A shares ``N_A`` at ``P_A``, non-tradable shares ``N_N``
worth ``r P_A`` each, and possibly B or H shares ``N_B`` that trade elsewhere and are left alone.
``n = N_A / (N_A + N_N)``; the B and H shares are not in it. The consideration ``c`` is stated as
"each tradable A share receives ``c`` shares from the non-tradable holders". If the reform moves
value between the two classes without adding or removing any,
``P_M (N_A + N_N) = P_A N_A + r P_A N_N``, and it leaves the tradable holders whole,
``(1 + c) P_M = P_A``, then

    c = (1 - n)(1 - r) / (n + (1 - n) r)
    r = ((1 - n) - c n) / ((1 - n)(1 + c))

``r = 1`` gives ``c = 0``; ``r = 0`` gives ``c = (1 - n) / n``.

**The market reading.** With the price after the reform ``P_M`` observed, conservation alone gives
``r_m = (P_M (N_A + N_N) - P_A N_A) / (P_A N_N)``. It equals ``r`` exactly when the tradable holders
come out whole, so ``r_m - r`` reads whether they came out ahead. Whole means ``(1 + c) P_M = P_A``
for a plain transfer; for a directed conversion ``P_M`` is the price on the enlarged share count and
the holder has ``1 + t`` shares, so it is ``(1 + t) P_M = P_A``; for a transfer and a conversion
together, ``(1 + x + t) P_M = P_A``.

**What both readings assume about the shares after the reform.** The reform did not make every share
free to trade on its day. The former non-tradable shares became tradable shares under selling
restrictions: none for twelve months, and for the larger holders no more than five and ten per cent of
the company within the next twelve and twenty-four. Both formulas value those restricted shares at the
free float's price ``P_M``. With a restricted share worth ``q P_M``, ``q <= 1``,

    r(q)   = q r                                   (share-only plans)
    r_m(q) = r_m - (1 - q) P_M N_post / (P_A N_N)  (N_post: the former non-tradable holders' shares after)

so ``r`` and ``r_m`` are the readings at ``q = 1`` and the upper ends in ``q``. ``q`` is not read here.

**The forms a consideration takes, and each one's equivalent ``c``** (block zero read them in
sixteen notices). Shares per tradable share ``x``; cash ``d`` per share; ``w`` warrants of value ``W``
per share; a capital-reserve conversion ``t`` to the tradable holders only; an all-holder conversion
``s`` after which the non-tradable holders hand over ``k`` per post-conversion share; a shrink of the
non-tradable stock by the fraction ``z``.

    shares                 c = x
    shares, cash, warrants c = x + (d + w W) / P_M     (P_M: the tradable price after the reform)
    directed conversion    c = t (1 - a) / (1 + a t),  a = N_A / (N_A + N_N + N_B)
    shares and conversion  c = (x + t (1 - a)) / (1 + a t)   (one plan: not the sum of the two alone)
    all-holder conversion  c = k                        (k on the post-conversion base, = k_pre / (1 + s))
    shrink                 c = 1 / (n + (1 - n)(1 - z)) - 1

A directed conversion dilutes B and H holders too, so a company with both is named and kept out of
the reading.

**B138-1** checks the conversion and its inverse against a second path that counts shares and values
holdings directly, on synthetic companies, and each seeded fault must make it fail.

Run from the repository root with the project's virtual environment:

    python experiments/b138_share_split.py --selftest
    python experiments/b138_share_split.py --paper
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

SEED = 138
COMPANIES = 2000
TOL = 1e-12

FAULTS = ("inverse_denominator", "n_nontradable", "n_with_b", "directed_as_t", "pre_base",
          "cash_at_pre_price", "shrink_as_z", "joint_as_sum")


# --------------------------------------------------------------------------
# the conversion: the formula path


def n_of(NA, NN, NB=0.0, fault=None):
    if fault == "n_nontradable":
        return NN / (NA + NN)
    if fault == "n_with_b":
        return NA / (NA + NN + NB)
    return NA / (NA + NN)


def c_from_r(r, n):
    return (1.0 - n) * (1.0 - r) / (n + (1.0 - n) * r)


def r_from_c(c, n, fault=None):
    if fault == "inverse_denominator":
        return ((1.0 - n) - c * n) / ((1.0 - n) * (1.0 - c))
    return ((1.0 - n) - c * n) / ((1.0 - n) * (1.0 + c))


def r_market(PA, PM, NA, NN):
    return (PM * (NA + NN) - PA * NA) / (PA * NN)


def c_equivalent(plan: dict, NA, NN, NB=0.0, PA=None, PM=None, fault=None) -> float:
    """The shares-per-tradable-share equivalent of one plan."""
    kind = plan["kind"]
    if kind == "shares":
        return plan["x"]
    if kind == "value":  # shares plus cash plus warrants
        price = PA if fault == "cash_at_pre_price" else PM
        return plan["x"] + (plan["d"] + plan["w"] * plan["W"]) / price
    if kind == "directed":
        t = plan["t"]
        if fault == "directed_as_t":
            return t
        a = NA / (NA + NN + NB)
        return t * (1.0 - a) / (1.0 + a * t)
    if kind == "shares_directed":
        x, t = plan["x"], plan["t"]
        a = NA / (NA + NN + NB)
        if fault == "joint_as_sum":  # each part's own equivalent, added: what some notices print
            return x + t * (1.0 - a) / (1.0 + a * t)
        return (x + t * (1.0 - a)) / (1.0 + a * t)
    if kind == "all_then_hand":
        return plan["k_pre"] if fault == "pre_base" else plan["k_pre"] / (1.0 + plan["s"])
    if kind == "shrink":
        z = plan["z"]
        if fault == "shrink_as_z":
            return z
        n = n_of(NA, NN)
        return 1.0 / (n + (1.0 - n) * (1.0 - z)) - 1.0
    raise ValueError(kind)


# --------------------------------------------------------------------------
# the second path: count shares, value holdings


def direct_fair_c(NA, NN, PA, r):
    """The consideration that leaves tradable holders whole, from the merged price."""
    PM = (PA * NA + r * PA * NN) / (NA + NN)
    return PA / PM - 1.0, PM


def direct_fraction(plan: dict, NA, NN, NB) -> float:
    """Tradable A holders' fraction of the whole company's shares after a share-only plan."""
    kind = plan["kind"]
    if kind == "shares":
        return NA * (1 + plan["x"]) / (NA + NN + NB)
    if kind == "directed":
        return NA * (1 + plan["t"]) / (NA + NN + NB + plan["t"] * NA)
    if kind == "shares_directed":
        return NA * (1 + plan["x"] + plan["t"]) / (NA + NN + NB + plan["t"] * NA)
    if kind == "all_then_hand":
        s, k = plan["s"], plan["k_pre"] / (1 + plan["s"])
        a_sh = NA * (1 + s)
        return (a_sh + k * a_sh) / ((NA + NN + NB) * (1 + s))
    if kind == "shrink":
        return NA / (NA + NN * (1 - plan["z"]) + NB)
    raise ValueError(kind)


def direct_value_r(plan: dict, NA, NN, PA):
    """A shares-plus-value plan that leaves tradable holders whole: the r it implies, and P_M."""
    # (1 + x) P_M + d + w W = P_A, and conservation P_M (N_A + N_N) = P_A N_A + r P_A N_N
    PM = (PA - plan["d"] - plan["w"] * plan["W"]) / (1 + plan["x"])
    return (PM * (NA + NN) - PA * NA) / (PA * NN), PM


# --------------------------------------------------------------------------
# B138-1


def synthetic(rng, count=COMPANIES):
    out = []
    for _ in range(count):
        NA = rng.uniform(0.1, 1.0) * 1e8
        NN = rng.uniform(0.2, 3.0) * 1e8
        NB = rng.uniform(0.05, 0.5) * 1e8 if rng.random() < 0.3 else 0.0
        PA = rng.uniform(2.0, 30.0)
        r = rng.uniform(0.05, 1.0)
        out.append((NA, NN, NB, PA, r))
    return out


def rel(a, b):
    return abs(a - b) / max(1.0, abs(b))


def criterion_conversion(fault=None, count=COMPANIES) -> dict:
    rng = np.random.default_rng(SEED)
    worst: dict[str, float] = {}

    def note(key, err):
        worst[key] = max(worst.get(key, 0.0), err)

    for NA, NN, NB, PA, r in synthetic(rng, count):
        n = n_of(NA, NN, NB, fault)
        c = c_from_r(r, n)
        note("inverse", rel(r_from_c(c, n, fault), r))
        c_dir, PM = direct_fair_c(NA, NN, PA, r)
        note("merged price", rel(c, c_dir))
        note("market reading", rel(r_market(PA, PM, NA, NN), r))
        # share-only plans against counted shares; B and H holders keep their shares
        x = float(rng.uniform(0.0, 1.0))
        plans = [{"kind": "shares", "x": x},
                 {"kind": "all_then_hand", "s": float(rng.uniform(0.1, 1.0)),
                  "k_pre": float(rng.uniform(0.05, 0.6))},
                 {"kind": "shrink", "z": float(rng.uniform(0.05, 0.6))}]
        if NB == 0.0:
            plans.append({"kind": "directed", "t": float(rng.uniform(0.1, 2.0))})
            plans.append({"kind": "shares_directed", "x": float(rng.uniform(0.02, 0.5)),
                          "t": float(rng.uniform(0.1, 1.0))})
        for plan in plans:
            if plan["kind"] == "shrink" and NB > 0.0:
                continue  # a shrink with B shares outstanding changes B's fraction too
            ce = c_equivalent(plan, NA, NN, NB, fault=fault)
            # a plain transfer of ce shares from the non-tradable holders
            f_equiv = NA * (1 + ce) / (NA + NN + NB)
            note(plan["kind"], rel(f_equiv, direct_fraction(plan, NA, NN, NB)))
        # a directed conversion with B present: the equivalent from the whole company, B paying its part
        if NB > 0.0:
            plan = {"kind": "directed", "t": float(rng.uniform(0.1, 2.0))}
            ce = c_equivalent(plan, NA, NN, NB, fault=fault)
            note("directed with B", rel(NA * (1 + ce) / (NA + NN + NB), direct_fraction(plan, NA, NN, NB)))
        # shares plus cash plus warrants, fair by construction
        plan = {"kind": "value", "x": x * 0.5, "d": float(rng.uniform(0.0, 0.1)) * PA,
                "w": float(rng.uniform(0.0, 1.0)), "W": float(rng.uniform(0.0, 0.1)) * PA}
        r_v, PM_v = direct_value_r(plan, NA, NN, PA)
        if r_v > 0.0:
            ce = c_equivalent(plan, NA, NN, NB, PA=PA, PM=PM_v, fault=fault)
            note("cash and warrants", rel(r_from_c(ce, n_of(NA, NN, NB, fault), fault), r_v))
    # the two ends, on a grid of n
    for n in np.linspace(0.05, 0.95, 19):
        note("r = 1 gives c = 0", abs(c_from_r(1.0, n)))
        note("r = 0 gives c = (1 - n)/n", rel(c_from_r(0.0, n), (1 - n) / n))
    passed = all(v <= TOL for v in worst.values())
    detail = (f"{count} synthetic companies (30% with B or H shares), largest relative gap per check: "
              + "; ".join(f"{k} {v:.1e}" for k, v in worst.items()) + f" (tolerance {TOL:.0e})")
    return {"name": "B138-1  the conversion and its inverse agree with counted shares and valued holdings",
            "kind": "instrument", "passed": bool(passed), "detail": detail}


# --------------------------------------------------------------------------
# block two: the readings that need no price (B138-2 to B138-8)

#: Notices read by eye in block zero (data/raw/b138/probe_printout_*.txt): form and shares per share.
HAND_READ = {"600493": ("shares_cash", 0.25), "600667": ("shares", 0.25), "600157": ("shares", 0.23),
             "600242": ("shares", 0.086), "600225": ("mixed_conversion", None),
             "600728": ("mixed_conversion", None), "600681": ("directed", 0.4), "000002": ("warrant", None),
             "000629": ("all_holder", None), "002010": ("shares", 0.45), "000514": ("other", None),
             "000938": ("shares", 0.5), "000768": ("shares", 0.25), "000886": ("shares", 0.39),
             "000626": ("shares", 0.30), "600705": ("all_holder", None)}
#: Plans that send shares and convert reserves to the tradable holders in one sentence, read by eye: shares
#: per share, conversion per share.
JOINT_READ = {"000545": (0.06, 0.332), "600697": (0.1, 0.2), "600867": (0.1, 0.4), "000520": (0.1, 0.527)}
#: Notices whose tradable total holds B or H shares, read by eye off the pre-reform column: tradable A shares,
#: and B plus H.
CLASS_ROWS = {"000011": (91_391_300, 61_459_312), "000017": (76_752_000, 215_967_811),
              "000018": (20_231_200, 69_421_903), "000028": (54_885_600, 54_885_600),
              "000030": (40_260_000, 39_600_000), "000055": (42_000_000, 145_368_000),
              "000058": (86_626_238, 228_041_727), "000513": (115_672_313, 122_306_984),
              "000541": (147_035_414, 82_500_000), "000666": (203_000_000, 180_800_000),
              "000726": (141_960_000, 162_240_000), "600362": (230_000_000, 1_387_482_000)}
#: The 75 notices that would convert and whose plan summary carries one of the component words, each
#: read by eye (2026-10-06). In the first 57 the company itself receives or gives up something as part
#: of the plan (an asset swap, donated or injected assets or cash, a debt waived, a buy-back, a one-way
#: shrink, a merger): named. In the other 18 the word sits in an undertaking for after the reform or in
#: the clause that adjusts an additional consideration: kept. The words around each are in the record.
COMPONENT_READ = (
    "000020 000544 000558 000628 000668 000686 000688 000697 000705 000716 000728 000736 000783 000801 "
    "000828 000848 000885 000887 000967 000982 600039 600086 600090 600118 600122 600136 600173 600199 "
    "600203 600215 600228 600234 600259 600290 600338 600339 600503 600506 600523 600561 600605 600617 "
    "600637 600643 600691 600721 600746 600751 600755 600765 600766 600800 600820 600839 600853 600861 "
    "600894").split()
COMPONENT_NOT = ("000506 000538 000651 000662 000759 000922 000939 000999 600003 600067 600078 600321 "
                 "600470 600481 600712 600726 600786 600966").split()
#: 000514 (cash injected, then a conversion to every holder) is "other"; 600705's sentence is its conversion to every
#: holder, the donated assets are in another sentence. Both are the block-zero table's "named, not in the reading".
#: SZSE research institute, "股权分置改革的回顾与总结" (report 0147, 2006-12-20), p. 20: 1,125 companies
#: reformed; 954 by shares alone, 1,086 with shares in the plan (96.5%). By kind: count, mean per 10.
SZSE = {"non-tradable holders give shares": (791, 3.156), "company and holders give shares": (15, 3.261),
        "company converts to tradable holders": (119, 2.768), "all holders convert, holders give": (29, 2.755),
        "cash from non-tradable holders": (8, 17.72)}
SZSE_WINDOW_END = "2006-10-31"
CX = {"auction": 0.7793, "private transfer": 0.8559}
STATED_TOL = 0.01
PRICED = ("shares_cash", "cash", "warrant")
#: B138-9 also reads the companies whose statement and listing are this close: a plan whose implementation
#: dragged on for a year or more carries the stock's own path over that year.
SHORT_WINDOW = 70


def reading_rows(parsed: list[dict]) -> list[dict]:
    out = []
    for p in parsed:
        row = {"code": p["code"], "name": p["name"], "id": p["id"], "day": p["day"]}
        if p["parse"] != "read":
            row["why_not"] = "no text"
            out.append(row)
            continue
        c, s = p["consideration"], p["structure"]
        row.update(form=c["form"], sentence=c.get("sentence"), c_nominal=c.get("shares"), cash=c.get("cash"),
                   warrants=c.get("warrants"), stated_equiv=c.get("stated_equiv"),
                   t_nominal=c.get("conversion"), component=c.get("component"),
                   component_src=c.get("component_src"),
                   NA=s["NA"], NN=s["NN"], NB=s["NB"], NH=s["NH"], NA_how=s.get("NA_how"),
                   tradable_total=s.get("tradable_total"),
                   route=s["route"], record_day=p.get("record_day"))
        if c["form"] == "none":
            row["why_not"] = "no consideration sentence"
        elif c.get("component"):
            row["why_not"] = f"plan with a company-level component: {c['component']}"
        elif not s["structure_ok"]:
            row["why_not"] = "share structure not read"
        elif c["form"] in PRICED:
            row["why_not"] = "needs a price (block two, second part)"
        elif c["form"] not in ("shares", "directed", "shares_directed"):
            row["why_not"] = f"form {c['form']}: named, not converted"
        elif not c.get("shares"):
            row["why_not"] = "amount not read from the sentence"
        elif c["form"] in ("directed", "shares_directed") and (s["NB"] or s["NH"]):
            row["why_not"] = "directed conversion with B or H shares: B and H pay part"
        else:
            NA, NN = s["NA"], s["NN"]
            n = n_of(NA, NN)
            if c["form"] == "shares":
                ce = c["shares"]
            elif c["form"] == "shares_directed":
                ce = c_equivalent({"kind": "shares_directed", "x": c["shares"], "t": c["conversion"]},
                                  NA, NN, 0.0)
            else:
                ce = c_equivalent({"kind": "directed", "t": c["shares"]}, NA, NN, 0.0)
            row.update(n=n, c=ce, r=r_from_c(ce, n))
            if s["stated_total"] and c["form"] == "shares":
                ratio = ce * NA / s["stated_total"]
                row["stated_ratio"] = ratio
                if abs(ratio - 1) > STATED_TOL:
                    row["why_not"] = f"stated total disagrees: c N_A / stated = {ratio:.4f}"
                    row.pop("r")
        out.append(row)
    return out


def used(rows):
    return [r for r in rows if "r" in r and "why_not" not in r]


def equivalent_check(rows) -> str:
    """Directed conversions whose notice states its own equivalent transfer: block one's formula against it."""
    d = [r for r in used(rows) if r["form"] == "directed" and r.get("stated_equiv")]
    if not d:
        return "no directed conversion states an equivalent"
    gaps = np.array([r["c"] / r["stated_equiv"] - 1 for r in d])
    within = int(np.sum(np.abs(gaps) <= 0.01))
    return (f"directed conversions stating their own equivalent: {len(d)}, block one's formula within 1% of it "
            f"in {within}; gap quantiles {quantiles(gaps)}")


def criterion_parse(rows, companies, fault=None) -> dict:
    rows = list(rows)
    if fault == "drop_row":
        rows = rows[1:]
    got = {r["code"]: r for r in rows}
    missing = [c["code"] for c in companies if c["code"] not in got]
    bad_known = []
    for code, (form, x) in HAND_READ.items():
        r = got.get(code)
        xr = None if r is None else r.get("c_nominal")
        if fault == "known" and code == "600667":
            xr = 0.35
        if r is None or r.get("form") != form or (x is not None and (xr is None or abs(xr - x) > 1e-9)):
            bad_known.append(code)
    conflicts = [r["code"] for r in used(rows) if abs(r.get("stated_ratio", 1.0) - 1) > STATED_TOL]
    if fault == "conflict_used" and used(rows):
        conflicts.append(used(rows)[0]["code"])
    # the three tables read by eye after the independent audit: joint plans, class rows, plan components
    bad_joint = []
    for code, (x, t) in JOINT_READ.items():
        r = got.get(code, {})
        tr = r.get("t_nominal")
        if fault == "joint" and code == "600697":
            tr = None
        if r.get("form") != "shares_directed" or abs((r.get("c_nominal") or 0) - x) > 1e-9 \
                or tr is None or abs(tr - t) > 1e-9:
            bad_joint.append(code)
    bad_class = []
    for code, (a, f) in CLASS_ROWS.items():
        r = got.get(code, {})
        na, nf = r.get("NA"), (r.get("NB") or 0) + (r.get("NH") or 0)
        if fault == "class" and code == "000541":
            na = r.get("tradable_total")
        if na is None or abs(na - a) > 0.5 or abs(nf - f) > 0.5:
            bad_class.append(code)
    flagged = {r["code"] for r in rows if r.get("component")}
    if fault == "component":
        flagged = flagged - {"600721"}
    bad_comp = [c for c in COMPONENT_READ if c not in flagged] + [c for c in COMPONENT_NOT if c in flagged]
    #: a row that would convert but for a component word must be one of those read by eye
    unread = sorted(r["code"] for r in rows
                    if r.get("component") and r.get("route") and (r.get("c_nominal") or r.get("cash"))
                    and r.get("form") in ("shares", "directed", "shares_directed", "shares_cash", "cash")
                    and r["code"] not in COMPONENT_READ)
    why: dict = {}
    for r in rows:
        if "why_not" in r:
            why[r["why_not"].split(":")[0]] = why.get(r["why_not"].split(":")[0], 0) + 1
    ok = (not missing and not bad_known and not conflicts and not bad_joint and not bad_class
          and not bad_comp and not unread)
    forms: dict = {}
    for r in used(rows):
        forms[r["form"]] = forms.get(r["form"], 0) + 1
    detail = (f"{len(companies)} companies with a main notice, {len(rows)} rows, missing {len(missing)}; "
              f"hand-read notices {len(HAND_READ)}, disagreeing {len(bad_known)} {bad_known}; "
              f"joint plans read by eye {len(JOINT_READ)}, disagreeing {len(bad_joint)} {bad_joint}; "
              f"class rows read by eye {len(CLASS_ROWS)}, disagreeing {len(bad_class)} {bad_class}; "
              f"plan components read by eye {len(COMPONENT_READ)} with and {len(COMPONENT_NOT)} without, "
              f"disagreeing {len(bad_comp)} {bad_comp}; flagged rows not read by eye {len(unread)} {unread}; "
              f"read and converted {len(used(rows))} ("
              + ", ".join(f"{k} {v}" for k, v in sorted(forms.items(), key=lambda kv: -kv[1]))
              + "); not read, by reason: "
              + "; ".join(f"{k} {v}" for k, v in sorted(why.items(), key=lambda kv: -kv[1]))
              + f"; rows used with a stated-total conflict {len(conflicts)}"
              + f"; {equivalent_check(rows)}")
    return {"name": "B138-2  every company's consideration and share structure are read or named",
            "kind": "instrument", "passed": bool(ok), "detail": detail}


def known_answer(rows) -> dict:
    win = [r for r in rows if r.get("form") and r["day"] <= SZSE_WINDOW_END]
    shares = [r["c_nominal"] * 10 for r in win if r.get("form") == "shares" and r.get("c_nominal")]
    directed = [r["c_nominal"] * 10 for r in win if r.get("form") == "directed" and r.get("c_nominal")]
    with_shares = sum(1 for r in win if r.get("form") in ("shares", "shares_cash", "directed", "all_holder")
                      or (r.get("form") == "warrant" and r.get("c_nominal")))
    mean = float(np.mean(shares)) if shares else float("nan")
    share_pct = with_shares / len(win) if win else float("nan")
    ok = abs(mean / 3.156 - 1) <= 0.05 and abs(share_pct - 0.965) <= 0.05
    detail = (f"notices to {SZSE_WINDOW_END}: {len(win)} companies (SZSE: 1,125). Shares from the "
              f"non-tradable holders: {len(shares)}, mean {mean:.3f} per 10 (SZSE 791 + 15, 3.156 and 3.261); "
              f"conversion to tradable holders: {len(directed)}, mean "
              f"{(np.mean(directed) if directed else float('nan')):.3f} (SZSE 119, 2.768); with shares in the plan "
              f"{with_shares} = {share_pct:.1%} (SZSE 1,086 = 96.5%). Reading: agrees if the mean is within 5% of "
              f"3.156 and the share within 5 points of 96.5%")
    return {"name": "B138-3  counts and mean consideration against the exchange's own tally",
            "kind": "known_answer", "passed": bool(ok), "detail": detail}


def rival_discount() -> dict:
    ok = all(v > 0 for v in CX.values())
    return {"name": "B138-4  the non-tradable share's transfer price is not the tradable price",
            "kind": "rival", "passed": bool(ok), "grid": "B", "rival_shape": "point",
            "rival_premise": "one scalar price at each position: a share of one company is one position",
            "rival_entailment": "a non-tradable share of the company trades at the tradable share's price, discount zero",
            "cite": "Chen and Xiong (2001), abstract: average discount 77.93% (auction) and 85.59% (private "
                    "transfer), August 2000 to July 2001, 2,577 auction trades and 242 private transfers",
            "detail": "auction 77.93%, private transfer 85.59%, against the contemporaneous tradable A-share price; "
                      "literature, read word for word in block zero"}


def rival_consideration(rows, fault=None) -> dict:
    u = used(rows)
    cs = [r["c"] for r in u]
    if fault == "zero":
        cs = cs + [0.0]
    zeros = sum(1 for c in cs if c <= 0)
    ok = bool(cs) and zeros == 0
    return {"name": "B138-5  the consideration is not zero", "kind": "rival", "passed": bool(ok),
            "grid": "B" if ok else "unread", "rival_shape": "point",
            "rival_premise": "one scalar price at each position: the two classes of one company are one position",
            "rival_entailment": "the classes have one price, so merging them moves no value and the consideration is zero",
            "detail": f"{len(cs)} companies read and converted: consideration above zero in {len(cs) - zeros}, "
                      f"zero or below in {zeros}; smallest {min(cs):.4f}, median {np.median(cs):.4f} shares per share"}


def quantiles(xs, qs=(0.05, 0.25, 0.5, 0.75, 0.95)):
    return " ".join(f"q{int(q * 100):02d} {np.quantile(xs, q):.3f}" for q in qs)


def reading_r(rows) -> dict:
    rs = np.array([r["r"] for r in used(rows)])
    ok = rs.size > 0 and bool(np.all(np.isfinite(rs)))
    below0 = int(np.sum(rs < 0))
    at = {k: int(np.sum(1 - rs >= v)) for k, v in CX.items()}
    detail = (f"{rs.size} companies: implied r {quantiles(rs)}; implied discount 1 - r median "
              f"{1 - np.median(rs):.3f}; r below zero (consideration above the non-tradable stock at par) {below0}; "
              f"discount at or above Chen and Xiong's auction 77.93% in {at['auction']}, private transfer 85.59% in "
              f"{at['private transfer']}. Chen and Xiong's prices are 2000-2001, four to five years before the reform")
    return {"name": "B138-6  the implied class-value ratio r, company by company", "kind": "own_reading",
            "passed": bool(ok), "detail": detail}


def average_rank(x) -> np.ndarray:
    """Ranks with ties given their mean rank, so the order of the rows does not matter."""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size)
    i = 0
    while i < x.size:
        j = i
        while j + 1 < x.size and x[order[j + 1]] == x[order[i]]:
            j += 1
        ranks[order[i: j + 1]] = 0.5 * (i + j)
        i = j + 1
    return ranks


def reading_gradient(rows) -> dict:
    u = used(rows)
    ns = np.array([r["n"] for r in u])
    cs = np.array([r["c"] for r in u])
    edges = np.quantile(ns, np.linspace(0, 1, 6))
    bins = []
    for i in range(5):
        m = (ns >= edges[i]) & ((ns < edges[i + 1]) if i < 4 else (ns <= edges[i + 1]))
        bins.append((float(np.median(ns[m])), float(np.median((1 - ns[m]) / ns[m])), float(np.median(cs[m])), int(m.sum())))
    mono = all(bins[i][2] >= bins[i + 1][2] for i in range(4))
    # c is printed to a few digits and many companies share one value: ties take their mean rank
    key = np.round(cs, 9)
    rho = float(np.corrcoef(average_rank(key), average_rank(np.round((1 - ns) / ns, 9)))[0, 1])
    tied = int(sum(1 for v in key if np.sum(key == v) > 1))
    detail = ("c by quintile of n (median n, median (1-n)/n, median c, companies): "
              + "; ".join(f"{a:.3f} {b:.3f} {c:.3f} {d}" for a, b, c, d in bins)
              + f". Median c falls as n rises across the quintiles: {mono}. Rank correlation of c with (1-n)/n "
              f"{rho:.3f}, ties at their mean rank ({len(set(key.tolist()))} distinct values of c, {tied} "
              f"companies in ties)")
    return {"name": "B138-7  the consideration against (1 - n)/n", "kind": "own_reading",
            "passed": bool(len(u) > 0 and all(b[3] > 0 for b in bins)), "detail": detail}


def reading_borrowed(rows) -> dict:
    import json
    from pathlib import Path
    yb = json.loads((Path(__file__).resolve().parents[1] / "data" / "processed" / "b135_yearbooks.json")
                    .read_text(encoding="utf-8"))["sse_market_value"]
    r_med = float(np.median([r["r"] for r in used(rows)]))
    lines, amount, share = [], {}, {}
    for y in range(1993, 2006):
        v = yb.get(str(y))
        if not v or v.get("negotiable_100m_yuan") is None:
            continue
        tot, neg, gdp = v["market_value_100m_yuan"], v["negotiable_100m_yuan"], v["gdp_100m_yuan"]
        non = tot - neg
        amount[y], share[y] = non * (1 - r_med), non * (1 - r_med) / gdp
        lines.append(f"{y} total {tot:.0f} non-tradable at the float price {non:.0f} ({non / tot:.0%}); borrowed at "
                     f"r {r_med:.2f}: {non * (1 - r_med):.0f} ({non * (1 - r_med) / gdp:.1%} of GDP), at the auction "
                     f"discount {non * CX['auction']:.0f}")
    peaks = ""
    if amount:
        ya, ys = max(amount, key=amount.get), max(share, key=share.get)
        peaks = (f"Largest amount {ya}: {amount[ya]:.0f} ({share[ya]:.2%} of GDP); largest share of GDP {ys}: "
                 f"{share[ys]:.2%} ({amount[ys]:.0f}). r is the reading with the restricted shares after the "
                 f"reform valued at the float price; it is the upper end in that value. ")
    return {"name": "B138-8  the borrowed price in the Shanghai total market value, 1993-2005", "kind": "own_reading",
            "passed": bool(lines), "detail": "100 million yuan. " + peaks + " | ".join(lines)}


# --------------------------------------------------------------------------
# block two, second part: prices (B138-9, and the cash plans)


def _bars(code: str) -> list[tuple[str, float, str]]:
    from pathlib import Path
    import json
    p = Path(__file__).resolve().parents[1] / "data" / "raw" / "b110" / "daily_baostock" / "stock" / f"{code}.json"
    if not p.exists():
        return []
    obj = json.loads(p.read_text(encoding="utf-8"))
    f = obj["fields"]
    i_d, i_c, i_s = f.index("date"), f.index("close"), f.index("tradestatus")
    return [(r[i_d], float(r[i_c]), r[i_s]) for r in obj["rows"] if r[i_c] not in ("", None)]


def _index(code: str) -> dict[str, float]:
    from pathlib import Path
    import json
    p = Path(__file__).resolve().parents[1] / "data" / "raw" / "b138" / f"index_{code.replace('.', '')}.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    f = obj["fields"]
    return {r[f.index("date")]: float(r[f.index("close")]) for r in obj["rows"] if r[f.index("close")]}


def _before(bars, day):
    xs = [b for b in bars if b[0] < day and b[2] == "1"]
    return xs[-1] if xs else None


def _after(bars, day):
    xs = [b for b in bars if b[0] > day and b[2] == "1"]
    return xs[0] if xs else None


def price_rows(rows: list[dict], stmt: dict[str, str]) -> list[dict]:
    """Adds P_A, P_M, the index ratio, the holders' gain, r_m, and c for the cash plans."""
    idx = {"sh": _index("sh.000001"), "sz": _index("sz.399106")}
    out = []
    for r in rows:
        r = dict(r)
        form = r.get("form")
        cash_plan = form in ("shares_cash", "cash") and r.get("NA") and r.get("NN") \
            and r.get("why_not", "").startswith("needs a price")
        if not ("r" in r and "why_not" not in r) and not cash_plan:
            out.append(r)
            continue
        day0, day1 = stmt.get(r["code"]), r.get("record_day")
        bars = _bars(r["code"])
        a = _before(bars, day0) if day0 else None
        m = _after(bars, day1) if day1 else None
        if a is None or m is None:
            r["price_why_not"] = ("no statement date" if not day0 else "no record day" if not day1
                                  else "no bar before the statement" if a is None else "no bar after the record day")
            out.append(r)
            continue
        ix = idx["sh" if r["code"].startswith("6") else "sz"]
        ia, im = ix.get(a[0]), ix.get(m[0])
        PA, PM = a[1], m[1]
        NA, NN = r["NA"], r["NN"]
        x = r.get("c_nominal") or 0.0
        d = r.get("cash") or 0.0
        if cash_plan:
            r["c"] = x + d / PM
            r["n"] = n_of(NA, NN)
            r["r"] = r_from_c(r["c"], r["n"])
            r.pop("why_not")
            r["priced_plan"] = True
        if form == "directed":
            t = r["c_nominal"]
            wealth, n_post, n_former = (1 + t) * PM, NA * (1 + t) + NN, NN
        elif form == "shares_directed":
            t = r["t_nominal"]
            wealth, n_post, n_former = (1 + x + t) * PM, NA * (1 + t) + NN, NN - x * NA
        else:
            wealth, n_post, n_former = (1 + x) * PM + d, NA + NN, NN - x * NA
        mkt = (im / ia) if (ia and im) else None
        r.update(day_A=a[0], P_A=PA, day_M=m[0], P_M=PM, market=mkt,
                 gain=wealth / PA - 1, r_m=(PM * n_post - PA * NA) / (PA * NN),
                 # d r_m / d q: the former non-tradable holders' shares after, at P_M, over their value before
                 rm_q_slope=PM * n_former / (PA * NN))
        if mkt:
            PMa = PM / mkt
            wa = wealth / mkt
            r.update(gain_adj=wa / PA - 1, r_m_adj=(PMa * n_post - PA * NA) / (PA * NN))
        out.append(r)
    return out


def reading_market(prows) -> dict:
    p = [r for r in prows if "r_m" in r]
    adj = [r for r in p if "r_m_adj" in r]
    g, ga = np.array([r["gain"] for r in p]), np.array([r["gain_adj"] for r in adj])
    rm, rma = np.array([r["r_m"] for r in p]), np.array([r["r_m_adj"] for r in adj])
    rr = np.array([r["r"] for r in adj])
    days = np.array([(np.datetime64(r["day_M"]) - np.datetime64(r["day_A"])).astype(int) for r in p])
    mk = np.array([r["market"] for r in adj])
    why: dict = {}
    for r in prows:
        if "price_why_not" in r:
            why[r["price_why_not"]] = why.get(r["price_why_not"], 0) + 1
    ok = len(adj) > 0 and bool(np.all(np.isfinite(rma)))
    dd = np.array([(np.datetime64(r["day_M"]) - np.datetime64(r["day_A"])).astype(int) for r in adj])
    s = dd <= SHORT_WINDOW
    short = (f" Windows of {SHORT_WINDOW} days or less ({int(s.sum())} companies): gain against the index "
             f"{quantiles(ga[s])}, above zero in {int(np.sum(ga[s] > 0))}; r_m against the index {quantiles(rma[s])}; "
             f"r {quantiles(rr[s])}; r_m - r {quantiles(rma[s] - rr[s])}.")
    sl = np.array([r["rm_q_slope"] for r in adj])
    short += (f" Both readings value the restricted shares after the reform at the float price (q = 1). Per 0.1 "
              f"that a restricted share is worth less than a free one, r_m falls by {quantiles(0.1 * sl)} and r by a "
              f"tenth of itself.")
    detail = (f"{len(p)} companies with both prices ({len(adj)} with the index on both days); not priced: "
              + "; ".join(f"{k} {v}" for k, v in why.items())
              + f". Calendar days from the last close before the statement to the first close after the record day: "
              f"{quantiles(days)}; the index over the same days {quantiles(mk)}. "
              f"Tradable holders' gain, raw {quantiles(g)}; against the index {quantiles(ga)}, above zero in "
              f"{int(np.sum(ga > 0))} of {len(ga)}. r_m raw {quantiles(rm)}; against the index {quantiles(rma)}; "
              f"r from the consideration on the same companies {quantiles(rr)}; r_m - r against the index "
              f"{quantiles(rma - rr)}." + short)
    return {"name": "B138-9  the market reading: r from the prices before and after, and the tradable holders' gain",
            "kind": "own_reading", "passed": bool(ok), "detail": detail}


def read_block_two() -> list[dict]:
    import b138_parse as Q
    parsed = Q.parse_all()
    rows = reading_rows(parsed)
    comps = Q.companies()
    dates = Q.RAW / "statement_dates.json"
    priced = dates.exists() and (Q.RAW / "index_sh000001.json").exists()
    if priced:
        import json
        rows = price_rows(rows, json.loads(dates.read_text(encoding="utf-8")))
    crit = [criterion_parse(rows, comps), known_answer(rows), rival_discount(), rival_consideration(rows),
            reading_r(rows), reading_gradient(rows), reading_borrowed(rows)]
    if priced:
        crit.append(reading_market(rows))
    return rows, comps, crit


# --------------------------------------------------------------------------
# record

CLOSED = True
ROW_KEYS = ("code", "name", "id", "day", "form", "sentence", "c_nominal", "t_nominal", "cash", "warrants",
            "stated_equiv", "component", "component_src",
            "NA", "NN", "NB", "NH", "NA_how", "tradable_total", "route", "record_day", "n", "c", "r",
            "stated_ratio", "priced_plan",
            "why_not", "day_A", "P_A", "day_M", "P_M", "market", "gain", "gain_adj", "r_m", "r_m_adj",
            "rm_q_slope", "price_why_not")


def _rv(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return float(f"{x:.10g}") if np.isfinite(x) else None
    return x


def build_record(crit, rows) -> dict:
    rec = {
        "stage": "B138",
        "config": {
            "seed": SEED, "tolerance": TOL, "synthetic_companies": COMPANIES,
            "stated_total_tolerance": STATED_TOL, "short_window_days": SHORT_WINDOW,
            "szse_window_end": SZSE_WINDOW_END,
            "notices": "cninfo implementation notices, data/raw/b138/pdf_text through b138_parse; one main notice "
                       "a company, the later of two",
            "structure": "accepted only where the parts add to the notice's total, or both classes' percentages "
                         "give one total, or the tradable count follows from the non-tradable percentage with no "
                         "B or H shares in the text",
            "prices": "baostock unadjusted closes: P_A the last close before the first reform statement, P_M the "
                      "first close after the record day; index sh.000001 for Shanghai, sz.399106 for Shenzhen",
            "n_excludes": "B and H shares",
            "restricted_shares": "valued at the float price after the reform (q = 1) in r and r_m; q not read",
            "plan_components": "a plan whose summary names an asset swap, donated or injected assets or cash, a "
                               "debt waived, a buy-back, a one-way shrink or a new issue for assets is named, "
                               "not converted; undertakings for after the reform are not counted",
            "cash_price": "P_M",
            "warrants": "not converted: no warrant price on this source",
            "literature": {"chen_xiong": CX, "szse_tally": {k: list(v) for k, v in SZSE.items()}},
        },
        "criteria": [{k: _rv(v) if not isinstance(v, dict) else v for k, v in c.items()} for c in crit],
        "companies": [{k: _rv(r[k]) for k in ROW_KEYS if k in r and r[k] is not None} for r in rows],
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = "Station not closed: the readings are not yet written into RESULTS.md."
    return rec


def write_record(rec) -> None:
    from pathlib import Path
    import json
    path = Path(__file__).resolve().parents[1] / "results" / "b138_share_split.json"
    path.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {path.name}")


# --------------------------------------------------------------------------


def paper() -> None:
    print("c against n and r (the implied discount is 1 - r):")
    print("   n    " + "  ".join(f"r={r:.2f}" for r in (0.14, 0.22, 0.35, 0.5, 0.65, 0.8)))
    for n in (0.25, 0.35, 0.45):
        print(f"  {n:.2f}  " + "  ".join(f"{c_from_r(r, n):6.3f}" for r in (0.14, 0.22, 0.35, 0.5, 0.65, 0.8)))
    print("\nr implied by a consideration of c per share:")
    print("   n    " + "  ".join(f"c={c:.2f}" for c in (0.2, 0.25, 0.3, 0.35, 0.4)))
    for n in (0.25, 0.35, 0.45):
        print(f"  {n:.2f}  " + "  ".join(f"{r_from_c(c, n):6.3f}" for c in (0.2, 0.25, 0.3, 0.35, 0.4)))
    print("\nChen and Xiong's discounts as considerations (auction 77.93%, private transfer 85.59%):")
    for n in (0.25, 0.35, 0.45):
        print(f"  n {n:.2f}: auction c {c_from_r(1 - 0.7793, n):.3f}, transfer c {c_from_r(1 - 0.8559, n):.3f}")


def selftest() -> bool:
    ok = True
    clean = criterion_conversion()
    print(f"  clean  B138-1 {clean['passed']}  {clean['detail']}")
    ok &= clean["passed"]
    for fault in FAULTS:
        r = criterion_conversion(fault)
        print(f"  fault {fault:19s} B138-1 fails: {not r['passed']}  {r['detail'][:150]}")
        ok &= not r["passed"]
    return bool(ok)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        t0 = time.perf_counter()
        ok = selftest()
        print(f"selftest {'passed' if ok else 'FAILED'} ({time.perf_counter() - t0:.1f} s)")
        return 0 if ok else 1
    if a.paper:
        paper()
        return 0
    if a.run:
        t0 = time.perf_counter()
        rows, comps, crit = read_block_two()
        crit = [criterion_conversion()] + crit
        for cr in crit:
            print(f"{cr['name']} [{cr['kind']}] {'PASS' if cr['passed'] else 'FAIL'}")
        print(f"{time.perf_counter() - t0:.1f} s")
        if not a.no_write:
            write_record(build_record(crit, rows))
        return 0 if all(c["passed"] for c in crit) else 1
    if a.read:
        t0 = time.perf_counter()
        rows, comps, crit = read_block_two()
        for cr in crit:
            print(f"{cr['name']} [{cr['kind']}] {'PASS' if cr['passed'] else 'FAIL'}: {cr['detail']}\n")
        print("seeded faults on the data (each must fail):")
        for f in ("drop_row", "known", "conflict_used", "joint", "class", "component"):
            print(f"  {f:14s} B138-2 fails: {not criterion_parse(rows, comps, f)['passed']}")
        tied = [dict(r) for r in used(rows)]
        a = reading_gradient(tied)["detail"].split("Rank correlation")[1]
        b = reading_gradient(tied[::-1])["detail"].split("Rank correlation")[1]
        print(f"  {'row order':14s} B138-7's rank correlation the same with the rows reversed: {a == b}")
        print(f"  {'zero':14s} B138-5 fails: {not rival_consideration(rows, 'zero')['passed']}")
        print(f"\nnamed, not in the reading ({sum('why_not' in r for r in rows)}):")
        for r in rows:
            if "why_not" in r:
                print(f"  {r['code']} {r['name']} {r['day']} id {r['id']}: {r['why_not']}")
        print(f"\n{time.perf_counter() - t0:.1f} s")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
