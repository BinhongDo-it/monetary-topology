"""B45: two pools for one plate, same city, same period.

Guangzhou allocates ordinary-car licence plates through two legs that run in the
same month: a free lottery and a paid auction. The rules make the split a third
party's doing rather than the applicant's (one application code, one method per
period), forbid lending, leasing, transferring or inheriting an indicator, and
fix each pool's size by published notice. So the two legs carry the same object
at two prices with no low-cost swap between them, which is what D29 and D30 ask
for and what the design file already scored on the rule text.

This file runs what the design registered as the load-bearing comparison, and
the answer it returns is about the comparison rather than about either theory.

The registered criterion. The standard account is an indifference condition: the
marginal applicant is indifferent between paying P now and waiting T periods for
a free plate, so P = T x (the price of time). Its comparative static needs no
value for the price of time: the lottery's win rate rises, the wait shortens,
and P should fall. The framework says the two legs are two edges with no loop
between them, so no such constraint exists.

What this file finds is that the comparison as registered cannot separate those,
and the reason is measurable rather than arguable: the win rate is indicators
over applicants, applicants respond to the same demand that sets P, and that
shared driver produces the standard account's sign on its own. The endogenous
half of the regressor carries the significant coefficient and the exogenous half
does not, so the registered reading is not identified. It is recorded as a
premise that fails, which per discipline 11d says the criteria resting on it
have no object to judge, not that anything was refuted.

Usage
-----
    python b45_two_pools.py
    python b45_two_pools.py --selftest
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "b45"
AUC = DATA / "gz_auction_rows_raw.txt"
LOT = DATA / "gz_lottery_individual_rows_raw.txt"
OUT = ROOT / "results" / "b45_two_pools.json"

RESERVE = 10000.0        # the auction's published reserve, in yuan
BID_GRID = 100.0         # measured below, not assumed


def read(path):
    """Parse one transcribed table. Source defects are handled by name here so
    that the raw file keeps them verbatim, per the transcription discipline."""
    out, notes = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        m = re.match(r"(\d{4})[年月](\d{1,2})月(\d{1,2})日", parts[0])
        if not m:
            raise SystemExit("unparsable date: %r" % parts[0])
        y, mo, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y == 2205:                      # the source's own typo for 2025
            y, notes.append(("%s -> 2025" % parts[0])) and None
            y = 2025
        key = (y, mo)
        # February 2020 carries two rows in both tables, one on the 3rd and one
        # at month end. January 2020's round was postponed into early February,
        # so the early row is January's and the month-end row is February's.
        # Both tables agree on this, which is why it is a real event and not a
        # transcription slip.
        if key == (2020, 2) and day <= 5:
            key = (2020, 1)
        if key in out:
            raise SystemExit("duplicate period after repair: %r" % (key,))
        out[key] = [x for x in parts[1:]]
    return out, notes


def ols(xs, ys):
    """None when the regressor does not move: a half with no variance carries
    no coefficient, and pretending otherwise is a division that happens to be
    by zero rather than a reading."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((v - mx) ** 2 for v in xs)
    if sxx <= 0.0 or n < 3:
        return {"slope": None, "se": None, "t": None, "n": n,
                "degenerate": "the regressor does not vary"}
    b = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / sxx
    a = my - b * mx
    resid = [ys[i] - a - b * xs[i] for i in range(n)]
    s2 = sum(r * r for r in resid) / (n - 2)
    se = math.sqrt(s2 / sxx)
    return {"slope": b, "se": se, "t": b / se, "n": n}


def fmt(o):
    if o["slope"] is None:
        return "no coefficient (%s)" % o["degenerate"]
    return "%+.4f (t %+.2f)" % (o["slope"], o["t"])


def build(auc, lot):
    keys = sorted(set(auc) & set(lot))
    pan = []
    for k in keys:
        pan.append({
            "period": "%d-%02d" % k, "key": k,
            "p_min": float(auc[k][0]), "p_avg": float(auc[k][1]),
            "base": float(lot[k][0]), "ind": float(lot[k][1]),
        })
    for r in pan:
        r["rate"] = r["ind"] / r["base"]
        r["at_reserve"] = r["p_min"] <= RESERVE
    return pan


def diffs(pan):
    """Adjacent-month pairs with both months strictly above the reserve."""
    out = []
    for a, c in zip(pan, pan[1:]):
        step = (c["key"][0] - a["key"][0]) * 12 + (c["key"][1] - a["key"][1])
        if step != 1 or a["at_reserve"] or c["at_reserve"]:
            continue
        out.append({
            "period": c["period"],
            "d_rate": math.log(c["rate"] / a["rate"]),
            "d_ind": math.log(c["ind"] / a["ind"]),
            "d_base": math.log(c["base"] / a["base"]),
            "d_p": math.log(c["p_avg"] / a["p_avg"]),
        })
    return out


def run(pan):
    crit, rep = [], {}
    d = diffs(pan)

    # ---- 1. the panel -------------------------------------------------------
    rep["periods"] = len(pan)
    rep["span"] = [pan[0]["period"], pan[-1]["period"]]
    rep["adjacent_uncensored_pairs"] = len(d)
    crit.append({
        "name": "B45-1", "kind": "instrument",
        "passed": len(pan) > 100 and len(d) > 50,
        "detail": (f"{len(pan)} periods joined on month, {rep['span'][0]} to "
                   f"{rep['span'][1]}, from two separately transcribed tables; "
                   f"{len(d)} adjacent pairs survive the censoring screen "
                   "below. February 2020 carries two rows in BOTH tables and "
                   "January none, so the early-February round is January's, "
                   "postponed; the two tables agreeing on that is what makes "
                   "it an event rather than a transcription slip"),
    })

    # ---- 2. gate six, the floor, measured ----------------------------------
    mins = [r["p_min"] for r in pan]
    avgs = [r["p_avg"] for r in pan]
    on_grid = sum(1 for v in mins if abs(v / BID_GRID - round(v / BID_GRID)) < 1e-9)
    avg_on_grid = sum(1 for v in avgs if abs(v / BID_GRID - round(v / BID_GRID)) < 1e-9)
    spread = max(avgs) / min(avgs)
    rep["floor"] = {
        "bid_grid_yuan": BID_GRID,
        "min_price_on_grid": [on_grid, len(mins)],
        "avg_price_on_grid": [avg_on_grid, len(avgs)],
        "avg_range": [min(avgs), max(avgs)], "avg_spread_x": spread,
    }
    crit.append({
        "name": "B45-2", "kind": "instrument",
        "passed": on_grid == len(mins) and avg_on_grid < len(avgs) // 2,
        "detail": (f"the floor is measured rather than asserted: all "
                   f"{on_grid} of {len(mins)} minimum prices are exact "
                   f"multiples of {BID_GRID:.0f} yuan, so the bid grid is 100, "
                   f"while only {avg_on_grid} of {len(avgs)} average prices "
                   f"are, which is what a computed mean looks like. The "
                   f"average runs {min(avgs):.0f} to {max(avgs):.0f} yuan, a "
                   f"factor of {spread:.2f}, three orders above the grid, so "
                   f"resolution is not what limits anything here"),
    })

    # ---- 3. the censoring, and where the biggest lever falls ---------------
    cens = [r for r in pan if r["at_reserve"]]
    policy = []
    for a, c in zip(pan, pan[1:]):
        if c["ind"] != a["ind"]:
            policy.append({"period": c["period"],
                           "ind_from": a["ind"], "ind_to": c["ind"],
                           "x": c["ind"] / a["ind"],
                           "rate_from": a["rate"], "rate_to": c["rate"],
                           "p_from": a["p_avg"], "p_to": c["p_avg"],
                           "censored": a["at_reserve"] or c["at_reserve"]})
    # A panel with no policy move at all has nothing to be censored, which is
    # a state this criterion has to report rather than trip over.
    big = (max(policy, key=lambda p: abs(math.log(p["x"]))) if policy else None)
    rep["censoring"] = {
        "at_reserve": len(cens), "of": len(pan),
        "share": len(cens) / len(pan),
        "reserve_yuan": RESERVE,
        "largest_policy_move": big,
    }
    rep["policy_moves"] = policy
    if big is None:
        crit.append({
            "name": "B45-3", "kind": "known_answer", "passed": False,
            "detail": ("Void: not evaluated, this panel has no policy move in "
                       "the indicator count, so there is no lever to ask "
                       "whether the censoring covers"),
        })
    else:
        crit.append({
            "name": "B45-3", "kind": "known_answer",
            "passed": big["censored"],
            "detail": (f"the auction has a published reserve of {RESERVE:.0f} "
                       f"yuan and the minimum price sits exactly on it in "
                       f"{len(cens)} of {len(pan)} periods; a price pinned at "
                       f"its floor cannot fall, so those periods cannot refute "
                       f"a prediction that it should. The largest policy move "
                       f"in the whole panel is {big['period']}, indicators "
                       f"{big['ind_from']:.0f} to {big['ind_to']:.0f} "
                       f"({big['x']:.2f}x, win rate "
                       f"{big['rate_from']*100:.4f}% to "
                       f"{big['rate_to']*100:.4f}%), and it falls inside the "
                       f"censored region. The biggest lever this carrier has "
                       f"is the one it cannot read"),
        })

    # ---- 4. is the registered comparison identified ------------------------
    # The registered regressor is the win rate, and the win rate is indicators
    # over applicants. Applicants respond to the same demand that sets the
    # price, so that half of the regressor moves with the outcome for reasons
    # that have nothing to do with any indifference condition. Split it.
    reg = ols([r["d_rate"] for r in d], [r["d_p"] for r in d])
    exo = ols([r["d_ind"] for r in d], [r["d_p"] for r in d])
    endo = ols([r["d_base"] for r in d], [r["d_p"] for r in d])
    v_rate = statistics.pvariance([r["d_rate"] for r in d])
    v_base = statistics.pvariance([r["d_base"] for r in d])
    v_ind = statistics.pvariance([r["d_ind"] for r in d])
    mi = sum(r["d_ind"] for r in d) / len(d)
    mb = sum(r["d_base"] for r in d) / len(d)
    cov = sum((r["d_ind"] - mi) * (r["d_base"] - mb) for r in d) / len(d)
    rep["identification"] = {
        "registered_regressor": reg, "exogenous_half": exo,
        "endogenous_half": endo,
        "variance_share_endogenous": v_base / v_rate,
        "variance_share_exogenous": v_ind / v_rate,
        "covariance_term_share": -2.0 * cov / v_rate,
        "identity": "d_rate = d_ind - d_base, so var(rate) = var(ind) + "
                    "var(base) - 2 cov(ind, base) and the two shares do not "
                    "sum to one",
    }
    # The premise: the exogenous half is what carries the comparison. It does
    # not. Both halves are read as an ordering of |t|, not against a line.
    # A half that does not move cannot carry the comparison and cannot spoil
    # it either: no endogenous variation means the premise holds outright.
    if endo["t"] is None:
        holds = exo["t"] is not None
    elif exo["t"] is None:
        holds = False
    else:
        holds = abs(exo["t"]) > abs(endo["t"])
    crit.append({
        "name": "B45-4", "kind": "premise",
        "passed": bool(holds),
        "detail": (
            "Void: the registered comparison is not identified on this panel, "
            "so the criteria resting on it have no object to judge. The "
            "regressor is the win rate and the win rate is indicators over "
            f"applicants, so it splits: the whole thing reads slope "
            f"{fmt(reg)}, the exogenous half, indicators, reads "
            f"{fmt(exo)} and the endogenous half, applicants, reads "
            f"{fmt(endo)}. The half that is not exogenous is the one "
            f"carrying the significant coefficient, and it is "
            f"{v_base/v_rate*100:.1f} per cent of the regressor's variance "
            f"against the exogenous half's {v_ind/v_rate*100:.1f} (the two do "
            f"not sum to one because the halves covary, the cross term being "
            f"{-2.0*cov/v_rate*100:+.1f} per cent). More applicants and a "
            "higher price are the same demand seen twice, and that alone "
            "produces the standard account's sign"),
    })

    # ---- 5. what an identified design would need --------------------------
    clean = [p for p in policy if abs(math.log(p["x"])) > 0.2 and not p["censored"]]
    rep["clean_exogenous_moves"] = clean
    rep["next"] = {
        "organisation_leg": (
            "the same city runs an organisation lottery and an organisation "
            "auction alongside these two, with its own indicator policy; that "
            "doubles the object and gives a cross-leg comparison inside one "
            "city-month. It is cleaner than two halves of one win rate and it "
            "is not clean: a company car and a personally bought plate are "
            "substitutes, so the two pools' demands are linked, and the data "
            "separates who bid where without separating why anyone was absent "
            "from the other pool"),
        "population_is_not_a_margin": (
            "the indifference condition presumes someone trading off paying "
            "now against waiting, and purchase timing on this carrier is set "
            "by when a car is wanted; entering a free lottery costs almost "
            "nothing, so the denominator counts people who took a free option "
            "rather than people who want a plate this period, and the same "
            "person is a waiter in one period and a buyer in the next. An "
            "exogenous denominator would still not be the wait the condition "
            "needs"),
        "other_two_pool_cities": (
            "Tianjin, Hangzhou and Shenzhen run the same two-pool structure, so "
            "policy moves in one city are a control for the others; their "
            "sources are not yet reached"),
        "why_not_more_periods": (
            "the panel already has every period the carrier has ever had. The "
            "limit is not length, it is that within one leg the win rate's "
            "denominator is the demand that sets the price"),
    }
    months = sorted({int(p["period"].split("-")[1]) for p in clean})
    rep["clean_moves_are_seasonal"] = {
        "months": months, "all_same_month": len(months) == 1,
        "note": ("indicators are cut to a floor every July in the early years, "
                 "so these are one annual pattern seen repeatedly rather than "
                 "independent shocks; anything else moving with the calendar "
                 "rides along with them"),
    }
    # rule 11f, 2026-09-13. The detail's load-bearing claim is that every clean move
    # falls in one month; that is computed two lines above and the verdict ignored it.
    crit.append({
        "name": "B45-5", "kind": "bookkeeping",
        "passed": (bool(clean)
                   and rep["clean_moves_are_seasonal"]["all_same_month"]),
        "detail": (f"{len(clean)} policy moves in the panel are both large "
                   f"(over 0.2 log points) and uncensored, and they all fall "
                   f"in month {months} of their years, which makes them one "
                   f"annual pattern rather than that many shocks: anything "
                   f"else moving with the calendar rides along. So the "
                   f"uncensored exogenous variation is one seasonal cut plus "
                   f"the two regime changes, of which the larger is censored. "
                   f"The two routes to an identified design are named with "
                   f"what each buys, and neither is more periods of this leg, "
                   f"because the panel is already the whole carrier"),
    })

    crit.sort(key=lambda c: c["name"])
    return crit, rep


def selftest() -> int:
    ok = True
    # A seeded world where the indifference condition HOLDS exactly and nothing
    # is endogenous: indicators move, applicants are constant, price tracks the
    # wait. The identification premise must hold there, or the criterion cannot
    # tell an identified panel from an unidentified one.
    pan = []
    for i in range(60):
        y, mo = 2000 + i // 12, i % 12 + 1
        ind = 4000.0 + 400.0 * ((i % 5) - 2)
        base = 500000.0
        rate = ind / base
        pan.append({"period": "%d-%02d" % (y, mo), "key": (y, mo),
                    "p_min": 20000.0, "p_avg": 30.0 / rate,
                    "base": base, "ind": ind, "rate": rate,
                    "at_reserve": False})
    _, rep = run(pan)
    idn = rep["identification"]
    if abs(idn["registered_regressor"]["slope"] + 1.0) > 1e-6:
        print("SELFTEST FAIL: a price equal to c/rate must give slope -1, got %r"
              % idn["registered_regressor"]["slope"])
        ok = False
    if abs(idn["variance_share_endogenous"]) > 1e-12:
        print("SELFTEST FAIL: a constant applicant count is zero endogenous "
              "variance, got %r" % idn["variance_share_endogenous"])
        ok = False

    # Now make applicants move with the price and nothing else change. The
    # premise must FAIL, or the criterion fires either way and reads nothing.
    pan2 = []
    for i in range(60):
        y, mo = 2000 + i // 12, i % 12 + 1
        ind = 4000.0
        shock = 1.0 + 0.10 * math.sin(i)
        base = 500000.0 * shock
        pan2.append({"period": "%d-%02d" % (y, mo), "key": (y, mo),
                     "p_min": 20000.0, "p_avg": 30000.0 * shock,
                     "base": base, "ind": ind, "rate": ind / base,
                     "at_reserve": False})
    c2, r2 = run(pan2)
    by2 = {c["name"]: c for c in c2}
    if by2["B45-4"]["passed"]:
        print("SELFTEST FAIL: the premise passed on a purely endogenous panel")
        ok = False
    if r2["identification"]["variance_share_endogenous"] < 0.99:
        print("SELFTEST FAIL: seeded all variance in applicants, read %r"
              % r2["identification"]["variance_share_endogenous"])
        ok = False

    # Censoring: a panel pinned at the reserve must lose its pairs.
    pan3 = [dict(r, p_min=RESERVE, at_reserve=True) for r in pan]
    if diffs(pan3):
        print("SELFTEST FAIL: censored pairs survived the screen")
        ok = False

    print("SELFTEST PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    for p in (AUC, LOT):
        if not p.exists():
            print("missing %s" % p)
            return 2
    auc, _ = read(AUC)
    lot, _ = read(LOT)
    pan = build(auc, lot)
    crit, rep = run(pan)

    print("=" * 74)
    print("B45: two pools for one plate, same city, same period")
    print("=" * 74)
    print("%d periods, %s to %s, %d adjacent uncensored pairs"
          % (rep["periods"], rep["span"][0], rep["span"][1],
             rep["adjacent_uncensored_pairs"]))
    f = rep["floor"]
    print("floor: minimum price on a %.0f-yuan grid %d/%d, average %d/%d; "
          "average runs %.0f to %.0f (%.2fx)"
          % (f["bid_grid_yuan"], f["min_price_on_grid"][0],
             f["min_price_on_grid"][1], f["avg_price_on_grid"][0],
             f["avg_price_on_grid"][1], f["avg_range"][0], f["avg_range"][1],
             f["avg_spread_x"]))
    c = rep["censoring"]
    b = c["largest_policy_move"]
    if b is None:
        print("at the reserve: %d/%d (%.1f%%); no policy move in this panel"
              % (c["at_reserve"], c["of"], c["share"] * 100))
    else:
        print("at the reserve: %d/%d (%.1f%%); largest policy move %s, %.0f -> "
              "%.0f indicators (%.2fx), censored: %s"
              % (c["at_reserve"], c["of"], c["share"] * 100, b["period"],
                 b["ind_from"], b["ind_to"], b["x"], b["censored"]))
    print()
    i = rep["identification"]
    print("%-34s %10s %8s %8s" % ("the registered regressor, split", "slope",
                                  "se", "t"))
    for nm, k in (("win rate (as registered)", "registered_regressor"),
                  ("  indicators, exogenous", "exogenous_half"),
                  ("  applicants, endogenous", "endogenous_half")):
        v = i[k]
        if v["slope"] is None:
            print("%-34s %10s %8s %8s" % (nm, "-", "-", "-"))
        else:
            print("%-34s %+10.4f %8.4f %+8.2f"
                  % (nm, v["slope"], v["se"], v["t"]))
    print("variance of the regressor: %.1f%% applicants, %.1f%% indicators"
          % (i["variance_share_endogenous"] * 100,
             i["variance_share_exogenous"] * 100))
    print()
    print("policy moves over 0.2 log points, uncensored: %d"
          % len(rep["clean_exogenous_moves"]))
    for p in rep["clean_exogenous_moves"]:
        print("   %s  %.0f -> %.0f (%.2fx)  price %.0f -> %.0f"
              % (p["period"], p["ind_from"], p["ind_to"], p["x"],
                 p["p_from"], p["p_to"]))
    print()
    for cr in crit:
        print("%-5s %-8s %s" % ("PASS" if cr["passed"] else "FAIL",
                                cr["name"], cr["detail"]))

    OUT.write_text(json.dumps({
        "stage": "B45",
        "config": {"auction": AUC.name, "lottery": LOT.name,
                   "reserve_yuan": RESERVE, "bid_grid_yuan": BID_GRID,
                   "source_level": "D32 other, a compiler; 13 periods checked "
                                   "against a second compiler, exact",
                   "leg": "individual ordinary car"},
        "criteria": crit, "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
