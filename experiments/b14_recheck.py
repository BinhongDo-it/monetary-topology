"""B14 recheck: the three things clause 5 and the outside review left directly testable.

All three run on caches already on disk. Nothing is fetched, nothing is bought.

  A  (design file section 7 supplement 2, B14_A2)  Split the treated groups by whether
     the nickel grid could bind at all, using each symbol's own pre-window spread
     from BEFORE the pilot took effect. The grid mechanism predicts the effect sits
     in the binding half and is absent in the slack half. A competing explanation
     (common time trend, volatility shock, composition drift) gets the slack half
     wrong. This is the discriminating power B14-0 itself does not have.

  B  (B14_A3)  T10: split the 2018 post window into November and December. December is
     the deepest month of that quarter's volatility event.

  C  (B14_A4)  The outside review's fourth point: inside the pilot the grid forces every
     venue, so BBO and NBBO are both pinned at a nickel; outside it the grid only
     permits, and NBBO is a market-wide min. So BBO minus NBBO should sit near zero
     inside the pilot and open up outside it.

Usage
    python experiments/b14_recheck.py --selftest
    python experiments/b14_recheck.py --census      # B14_A2 reachability count first
    python experiments/b14_recheck.py --run
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate0 as G          # noqa: E402
import b14_gate_exit as E      # noqa: E402

OUT = os.path.join(ROOT, "results", "b14_recheck.json")
GROUPS = G.GROUPS
median = G.median

#: The tick the pilot itself specifies. Not a calibration this study chose (D5).
NICKEL = 0.05
#: Single months carry 21 and 19 trading days, so the ten-day rule is scaled down
#: for test B only, and said so in the design file before the run.
MIN_DAYS_MONTHLY = 5


def load_raw(pre, post, extra_windows=()):
    """(ctr, sym) -> per-window lists of the raw (not logged) spd, plus labels.

    Kept separate from b14_gate_exit.load because B14_A2 needs the level of the
    pre-window spread, which the log-space loader throws away.
    """
    import math
    wins = [("pre", pre), ("post", post)] + list(extra_windows)
    rec = {}
    files = sorted(f for f in os.listdir(E.CACHE)
                   if f.startswith("panel_v2_") and f.endswith(".csv"))
    assert files, "no v2 cache"
    for fn in files:
        with open(os.path.join(E.CACHE, fn)) as fh:
            fh.readline()
            for line in fh:
                if line.startswith("#"):
                    continue
                p = line.rstrip("\n").split(",")
                date, ctr, sym, grp = p[0], p[1], G.canon(p[2]), p[3]
                for wname, (a, b) in wins:
                    if not (a <= date <= b):
                        continue
                    r = rec.get((ctr, sym))
                    if r is None:
                        r = rec[(ctr, sym)] = {"tag": {w: set() for w, _ in wins}}
                        for w, _ in wins:
                            r[w] = {"bbo": [], "nbbo": [], "lbbo": [], "lnbbo": []}
                    r["tag"][wname].add(grp)
                    den = float(p[5])
                    if den > 0:
                        v = float(p[4]) / den
                        if v > 0:
                            r[wname]["bbo"].append(v)
                            r[wname]["lbbo"].append(math.log(v))
                    den2 = float(p[9])
                    if den2 > 0:
                        v2 = float(p[8]) / den2
                        if v2 > 0:
                            r[wname]["nbbo"].append(v2)
                            r[wname]["lnbbo"].append(math.log(v2))
    return rec


def group_of(r, grp_from):
    t = r["tag"][grp_from]
    if len(t) != 1:
        return None
    g = next(iter(t))
    return g if g in GROUPS else None


def six(tab, sign):
    """Six inequalities from a {ctr/grp: value} table. sign=+1 wants G>C."""
    out = []
    for ctr in ("N", "P"):
        base = tab.get(ctr + "/C")
        for grp in ("G1", "G2", "G3"):
            m = tab.get(ctr + "/" + grp)
            gap = None if (m is None or base is None) else m - base
            out.append({"ctr": ctr, "grp": grp, "raw_gap": gap,
                        "holds": bool(gap is not None and sign * gap > 0)})
    return out


def deltas_by(rec, grp_from, pre, post, key="lbbo", min_days=None, pick=None):
    """(ctr, grp) -> list of Delta, optionally restricted by pick(ctr, sym, r)."""
    md = G.MIN_DAYS if min_days is None else min_days
    out = {}
    for (ctr, sym), r in rec.items():
        g = group_of(r, grp_from)
        if g is None:
            continue
        if pick is not None and not pick(ctr, sym, r):
            continue
        a, b = r[pre][key], r[post][key]
        if len(a) < md or len(b) < md:
            continue
        out.setdefault((ctr, g), []).append(median(b) - median(a))
    return out


def tabulate(d):
    return {c + "/" + g: median(v) for (c, g), v in d.items()}, \
           {c + "/" + g: len(v) for (c, g), v in d.items()}


# ------------------------------------------------------------------ test A

SPLIT_SOURCE = "2016 pre window, before the pilot took effect"


def binder(rec2016):
    """Which symbols the nickel grid could bind at all, from BEFORE the pilot.

    The split window has to sit before treatment for BOTH rounds. Using each
    round's own pre window is wrong for 2018, whose pre window is INSIDE the
    pilot: there every treated symbol is pinned at a nickel by construction, so
    "median pre spread < 0.05" is unreachable for the treated groups and the
    split degenerates. The reachability count required by D15 caught exactly
    that on the first pass (2018 binding held 0 treated symbols), and this was
    fixed before any reading was taken. The 2016 pre window is 2016-08 and
    2016-09, and the pilot took effect in 2016-10.
    """
    b = {}
    for (ctr, sym), r in rec2016.items():
        m = median(r["pre"]["bbo"])
        if m is not None:
            b[(ctr, sym)] = (m < NICKEL)
    return b


def test_a(rec2016, rec2018):
    """Split the treated groups by whether the nickel grid could bind."""
    bind = binder(rec2016)
    res = {"split_source": SPLIT_SOURCE,
           "split_symbols": len(bind),
           "split_binding": sum(1 for v in bind.values() if v)}
    for label, rc, cfg, gf in (
            ("2016", rec2016, E.ROUNDS["2016"], "post"),
            ("2018", rec2018, E.ROUNDS["2018"], "pre")):
        blk = {"unsplittable": sum(1 for k in rc if k not in bind)}
        for half, want in (("binding", True), ("slack", False)):
            d = deltas_by(rc, gf, "pre", "post",
                          pick=lambda c, s, r, w=want: bind.get((c, s)) is w)
            tab, n = tabulate(d)
            ineq = six(tab, cfg["sign"])
            blk[half] = {"table": tab, "n": n, "inequalities": ineq,
                         "holds": sum(1 for x in ineq if x["holds"])}
        res[label] = blk
    return res


# ------------------------------------------------------------------ test B

def test_b(rec2018m):
    cfg = E.ROUNDS["2018"]
    out = {}
    for m in ("nov", "dec"):
        d = deltas_by(rec2018m, "pre", "pre", m, min_days=MIN_DAYS_MONTHLY)
        tab, n = tabulate(d)
        ineq = six(tab, cfg["sign"])
        out[m] = {"table": tab, "n": n, "inequalities": ineq,
                  "holds": sum(1 for x in ineq if x["holds"])}
    return out


# ------------------------------------------------------------------ test C

def test_c(rec2016, rec2018):
    out = {}
    for label, rc, gf in (("2016", rec2016, "post"), ("2018", rec2018, "pre")):
        blk = {}
        for w in ("pre", "post"):
            per = {}
            for (ctr, sym), r in rc.items():
                g = group_of(r, gf)
                if g is None:
                    continue
                a, b = median(r[w]["bbo"]), median(r[w]["nbbo"])
                if a is None or b is None:
                    continue
                per.setdefault((ctr, g), []).append(a - b)
            blk[w] = {c + "/" + g: median(v) for (c, g), v in per.items()}
            blk[w + "_n"] = {c + "/" + g: len(v) for (c, g), v in per.items()}
        out[label] = blk
    return out


def pure_slack(rec2016):
    """Symbols whose pre-window spread was never under a nickel, not once.

    Design file B14_A5 clause 1. The B14_A2 split uses the median, so its slack half still
    contains days the grid could bind. This is the half with no such days at all.
    """
    out = {}
    for (ctr, sym), r in rec2016.items():
        v = r["pre"]["bbo"]
        if v:
            out[(ctr, sym)] = not any(x < NICKEL for x in v)
    return out


def gradient_bins(rec2016):
    """(ctr, sym) -> bin index 0..5.

    A nickel is the only fixed cut, and it has a source: it is the increment the
    pilot specifies. Each side of it is split into thirds by its OWN quantiles, so
    no other cut point is invented (design file B14_A5 clause 2). Bin 2 sits just under
    the nickel and bin 3 just over it, so the step between them is the one the grid
    mechanism predicts and a smooth story does not.
    """
    lev = {}
    for (ctr, sym), r in rec2016.items():
        m = median(r["pre"]["bbo"])
        if m is not None:
            lev[(ctr, sym)] = m
    below = sorted(v for v in lev.values() if v < NICKEL)
    above = sorted(v for v in lev.values() if v >= NICKEL)

    def q(xs, f):
        return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None

    cuts = [q(below, 1 / 3.0), q(below, 2 / 3.0), NICKEL,
            q(above, 1 / 3.0), q(above, 2 / 3.0)]
    out = {}
    for k, v in lev.items():
        i = 0
        for c in cuts:
            if c is not None and v >= c:
                i += 1
        out[k] = i
    return out, cuts


def test_candidates(rec2016, rec2018):
    ps = pure_slack(rec2016)
    bins, cuts = gradient_bins(rec2016)
    res = {"cuts": cuts, "n_pure_slack": sum(1 for v in ps.values() if v)}
    for label, rc, cfg, gf in (("2016", rec2016, E.ROUNDS["2016"], "post"),
                               ("2018", rec2018, E.ROUNDS["2018"], "pre")):
        blk = {}
        d = deltas_by(rc, gf, "pre", "post",
                      pick=lambda c, s, r: ps.get((c, s)) is True)
        tab, n = tabulate(d)
        ineq = six(tab, cfg["sign"])
        blk["pure_slack"] = {"table": tab, "n": n, "inequalities": ineq,
                             "holds": sum(1 for x in ineq if x["holds"])}
        grad = {}
        for i in range(6):
            di = deltas_by(rc, gf, "pre", "post",
                           pick=lambda c, s, r, j=i: bins.get((c, s)) == j)
            ti, ni = tabulate(di)
            gi = six(ti, cfg["sign"])
            grad[i] = {"table": ti, "n": ni, "inequalities": gi,
                       "holds": sum(1 for x in gi if x["holds"])}
        blk["gradient"] = grad
        res[label] = blk
    return res


#: Bandwidths for the narrow-band discontinuity test (design file B14_A6). Every one
#: is a multiple or half of the ORIGINAL one-cent grid, so none is a number this
#: study picked (D5).
BANDWIDTHS = [0.005, 0.01, 0.02, 0.03]
#: Placebo cut points with no institutional meaning, for B14_A6 clause 3. The second
#: one is supplied by the data, not chosen here.
PLACEBO_ROUND = 0.10


def levels(rec2016):
    out = {}
    for k, r in rec2016.items():
        m = median(r["pre"]["bbo"])
        if m is not None:
            out[k] = m
    return out


def test_rd(rec2016, rec2018):
    """Narrow bands either side of a cut, at four bandwidths, plus two placebos."""
    lev = levels(rec2016)
    slack_vals = sorted(v for v in lev.values() if v >= NICKEL)
    placebo_med = slack_vals[len(slack_vals) // 2] if slack_vals else None
    cuts = [("nickel", NICKEL), ("placebo_dime", PLACEBO_ROUND),
            ("placebo_slack_median", placebo_med)]
    res = {"cuts": {n: c for n, c in cuts}}
    for label, rc, cfg, gf in (("2016", rec2016, E.ROUNDS["2016"], "post"),
                               ("2018", rec2018, E.ROUNDS["2018"], "pre")):
        blk = {}
        for cname, c in cuts:
            if c is None:
                continue
            per_h = {}
            for h in BANDWIDTHS:
                side = {}
                for sname, lo, hi in (("left", c - h, c), ("right", c, c + h)):
                    d = deltas_by(rc, gf, "pre", "post",
                                  pick=lambda ct, sy, r, a=lo, b=hi:
                                  (lev.get((ct, sy)) is not None
                                   and a <= lev[(ct, sy)] < b))
                    tab, n = tabulate(d)
                    ineq = six(tab, cfg["sign"])
                    side[sname] = {"table": tab, "n": n, "inequalities": ineq,
                                   "holds": sum(1 for x in ineq if x["holds"])}
                per_h["%.3f" % h] = side
            blk[cname] = per_h
        res[label] = blk
    return res


def show_rd(res, label, sign):
    print("\n-- %s round, sign %+d" % (label, sign))
    print("   %-22s %-6s %-4s %-24s %-4s %-24s"
          % ("cut", "h", "nL", "left gaps (N then P)", "nR", "right gaps (N then P)"))
    for cname in ("nickel", "placebo_dime", "placebo_slack_median"):
        if cname not in res[label]:
            continue
        cval = res["cuts"][cname]
        for h, side in sorted(res[label][cname].items()):
            row = []
            for sname in ("left", "right"):
                b = side[sname]
                n = sum(b["n"].values())
                g = " ".join("%+.3f" % x["raw_gap"] if x["raw_gap"] is not None
                             else " None " for x in b["inequalities"])
                row.append((n, g))
            print("   %-22s %-6s %-4d %-24s %-4d %-24s"
                  % ("%s %.4f" % (cname, cval), h, row[0][0], row[0][1],
                     row[1][0], row[1][1]))


#: Split-sample windows (design file B14_A8). Aug and Sep 2016 are both before the
#: pilot took effect in Oct 2016, so either can define the split while the other
#: serves as the denominator, and the two never share an observation.
SPLIT_A = ("20160801", "20160831")
SPLIT_B = ("20160901", "20160930")
MIN_DAYS_SPLIT = 5


def test_split_sample(rec2016):
    """Break the shared denominator: split on one month, divide by the other."""
    out = {}
    for vname, cutwin, denwin in (("A", "aug", "sep"), ("B", "sep", "aug")):
        lev = {}
        for k, r in rec2016.items():
            m = median(r[cutwin]["bbo"])
            if m is not None:
                lev[k] = m
        below = sorted(v for v in lev.values() if v < NICKEL)
        above = sorted(v for v in lev.values() if v >= NICKEL)

        def q(xs, f):
            return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None

        cuts = [q(below, 1 / 3.0), q(below, 2 / 3.0), NICKEL,
                q(above, 1 / 3.0), q(above, 2 / 3.0)]
        bins = {}
        for k, v in lev.items():
            i = 0
            for c in cuts:
                if c is not None and v >= c:
                    i += 1
            bins[k] = i

        grad = {}
        for i in range(6):
            d = deltas_by(rec2016, "post", denwin, "post", min_days=MIN_DAYS_SPLIT,
                          pick=lambda c, sy, r, j=i: bins.get((c, sy)) == j)
            tab, n = tabulate(d)
            grad[i] = {"table": tab, "n": n, "inequalities": six(tab, +1)}

        band = {}
        for h in BANDWIDTHS:
            side = {}
            for sname, lo, hi in (("left", NICKEL - h, NICKEL),
                                  ("right", NICKEL, NICKEL + h)):
                d = deltas_by(rec2016, "post", denwin, "post",
                              min_days=MIN_DAYS_SPLIT,
                              pick=lambda c, sy, r, a=lo, b=hi:
                              (lev.get((c, sy)) is not None and a <= lev[(c, sy)] < b))
                tab, n = tabulate(d)
                side[sname] = {"table": tab, "n": n, "inequalities": six(tab, +1)}
            band["%.3f" % h] = side
        out[vname] = {"cut_window": cutwin, "denominator_window": denwin,
                      "cuts": cuts, "gradient": grad, "band": band}
    return out


def cross_levels(rec2016, mode):
    """Split levels that share nothing with the outcome denominator (B14_A9).

    mode "venue": a symbol on NYSE is split by its OWN pre-window spread ON ARCA,
    and vice versa. Different order flow, different book, different sampling
    instants, so the measurement errors are independent, while "can the nickel
    grid bind this name" is a property of the security and should agree across
    venues.

    mode "measure": split on WA_NBBO_Spd, outcome on WA_BBO_Spd. Same venue and
    same instants, so this is weaker; it runs as a cross-check only.
    """
    own = {}
    for k, r in rec2016.items():
        key = "nbbo" if mode == "measure" else "bbo"
        m = median(r["pre"][key])
        if m is not None:
            own[k] = m
    if mode == "measure":
        return own
    other = {"N": "P", "P": "N"}
    out = {}
    for (ctr, sym) in rec2016:
        v = own.get((other[ctr], sym))
        if v is not None:
            out[(ctr, sym)] = v
    return out


def bins_from(lev):
    below = sorted(v for v in lev.values() if v < NICKEL)
    above = sorted(v for v in lev.values() if v >= NICKEL)

    def q(xs, f):
        return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None

    cuts = [q(below, 1 / 3.0), q(below, 2 / 3.0), NICKEL,
            q(above, 1 / 3.0), q(above, 2 / 3.0)]
    out = {}
    for k, v in lev.items():
        i = 0
        for c in cuts:
            if c is not None and v >= c:
                i += 1
        out[k] = i
    return out, cuts


def test_cross(rec2016):
    res = {}
    for mode in ("venue", "measure"):
        lev = cross_levels(rec2016, mode)
        bins, cuts = bins_from(lev)
        grad = {}
        for i in range(6):
            d = deltas_by(rec2016, "post", "pre", "post",
                          pick=lambda c, s, r, j=i: bins.get((c, s)) == j)
            tab, n = tabulate(d)
            grad[i] = {"table": tab, "n": n, "inequalities": six(tab, +1)}
        band = {}
        for h in BANDWIDTHS:
            side = {}
            for sname, lo, hi in (("left", NICKEL - h, NICKEL),
                                  ("right", NICKEL, NICKEL + h)):
                d = deltas_by(rec2016, "post", "pre", "post",
                              pick=lambda c, s, r, a=lo, b=hi:
                              (lev.get((c, s)) is not None and a <= lev[(c, s)] < b))
                tab, n = tabulate(d)
                side[sname] = {"table": tab, "n": n, "inequalities": six(tab, +1)}
            band["%.3f" % h] = side
        res[mode] = {"n_splittable": len(lev), "cuts": cuts,
                     "gradient": grad, "band": band}
    return res


#: Design file B14_A10. The pilot took effect 2016-10-03, so every window here is
#: before treatment. The split window shares no observation with any other.
W_APR = ("20160401", "20160430")
W_MAY = ("20160501", "20160531")
W_PLACEBO_PRE = ("20160601", "20160731")
#: The placebo post window is 2016-08/09, which is the real test's PRE window,
#: already loaded as "pre".


def far_binder(rec):
    """Split on 2016-04 and 2016-05, keeping only names both months agree on.

    Design file B14_A10 clause 2. Screening out the names whose side flips between
    the two months removes split noise instead of correcting for it.
    """
    out, unstable, nodata = {}, 0, 0
    for k, r in rec.items():
        a, b = median(r["apr"]["bbo"]), median(r["may"]["bbo"])
        if a is None or b is None:
            nodata += 1
            continue
        if (a < NICKEL) != (b < NICKEL):
            unstable += 1
            continue
        both = r["apr"]["bbo"] + r["may"]["bbo"]
        out[k] = median(both)
    return out, {"unstable": unstable, "no split data": nodata, "kept": len(out)}


def test_placebo_did(rec):
    lev, stats = far_binder(rec)
    bins, cuts = bins_from(lev)
    res = {"split_stats": stats, "cuts": cuts}
    for name, prewin, postwin in (("placebo", "pre_pl", "pre"),
                                  ("real", "pre", "post")):
        grad = {}
        for i in range(6):
            d = deltas_by(rec, "post", prewin, postwin,
                          pick=lambda c, sy, r, j=i: bins.get((c, sy)) == j)
            tab, n = tabulate(d)
            grad[i] = {"table": tab, "n": n, "inequalities": six(tab, +1)}
        band = {}
        for h in BANDWIDTHS:
            side = {}
            for sname, lo, hi in (("left", NICKEL - h, NICKEL),
                                  ("right", NICKEL, NICKEL + h)):
                d = deltas_by(rec, "post", prewin, postwin,
                              pick=lambda c, sy, r, a=lo, b=hi:
                              (lev.get((c, sy)) is not None and a <= lev[(c, sy)] < b))
                tab, n = tabulate(d)
                side[sname] = {"table": tab, "n": n, "inequalities": six(tab, +1)}
            band["%.3f" % h] = side
        res[name] = {"pre": prewin, "post": postwin, "gradient": grad, "band": band}
    return res


#: Design file B14_A11. Aug and Sep 2018 both sit INSIDE the pilot, so nothing
#: happens between them: that pair is the 2018 placebo.
W_AUG18 = ("20180801", "20180831")
W_SEP18 = ("20180901", "20180928")


def test_slack_placebo(rec16, rec18):
    """B14_A11: is the pure-slack residue there before the pilot too, and does the
    2018 gradient survive a placebo inside the pilot."""
    # pure slack defined on the SPLIT window, sharing nothing with either test
    pure, flip = {}, 0
    for k, r in rec16.items():
        v = r["apr"]["bbo"] + r["may"]["bbo"]
        if v:
            pure[k] = not any(x < NICKEL for x in v)
    res = {"n_pure_slack": sum(1 for x in pure.values() if x)}

    for name, prewin, postwin in (("placebo", "pre_pl", "pre"),
                                  ("real", "pre", "post")):
        d = deltas_by(rec16, "post", prewin, postwin,
                      pick=lambda c, s, r: pure.get((c, s)) is True)
        tab, n = tabulate(d)
        res[name] = {"table": tab, "n": n, "inequalities": six(tab, +1),
                     "holds": sum(1 for x in six(tab, +1) if x["holds"])}

    # 2018 placebo: Aug -> Sep, both inside the pilot, split from 2016-04/05
    lev, _ = far_binder(rec16)
    bins, cuts = bins_from(lev)
    g18 = {}
    for i in range(6):
        d = deltas_by(rec18, "pre", "aug18", "sep18", min_days=MIN_DAYS_SPLIT,
                      pick=lambda c, s, r, j=i: bins.get((c, s)) == j)
        tab, n = tabulate(d)
        g18[i] = {"table": tab, "n": n, "inequalities": six(tab, -1)}
    res["placebo_2018"] = {"cuts": cuts, "gradient": g18}
    return res


def show_six(name, blk, sign):
    want = "G above C" if sign > 0 else "G below C"
    print("  %-9s  %d/6 hold (wants %s)" % (name, blk["holds"], want))
    for ctr in ("N", "P"):
        cn = blk["n"].get(ctr + "/C", 0)
        cv = blk["table"].get(ctr + "/C")
        print("     %s  C n=%-5d Delta %s" % (ctr, cn, "None" if cv is None else "%+.6f" % cv))
        for x in [y for y in blk["inequalities"] if y["ctr"] == ctr]:
            k = ctr + "/" + x["grp"]
            print("        %-3s n=%-5d Delta %-11s gap %-11s %s"
                  % (x["grp"], blk["n"].get(k, 0),
                     "None" if blk["table"].get(k) is None else "%+.6f" % blk["table"][k],
                     "None" if x["raw_gap"] is None else "%+.6f" % x["raw_gap"],
                     "hold" if x["holds"] else "----"))


def run(census_only=False):
    r16 = load_raw(E.ROUNDS["2016"]["pre"], E.ROUNDS["2016"]["post"],
                   extra_windows=[("aug", SPLIT_A), ("sep", SPLIT_B),
                                  ("apr", W_APR), ("may", W_MAY),
                                  ("pre_pl", W_PLACEBO_PRE)])
    r18 = load_raw(E.ROUNDS["2018"]["pre"], E.ROUNDS["2018"]["post"],
                   extra_windows=[("nov", ("20181101", "20181130")),
                                  ("dec", ("20181201", "20181231")),
                                  ("aug18", W_AUG18), ("sep18", W_SEP18)])
    print("loaded: 2016 %d pairs, 2018 %d pairs" % (len(r16), len(r18)))

    a = test_a(r16, r18)
    print("\n" + "=" * 74)
    print("A  reachability count first (design file B14_A2 clause 3, D15)")
    print("=" * 74)
    print("  split from: %s" % a["split_source"])
    print("  %d symbols splittable, %d of them binding"
          % (a["split_symbols"], a["split_binding"]))
    for label in ("2016", "2018"):
        print("  %s: %d pairs in this round have no 2016 pre window and are dropped"
              % (label, a[label]["unsplittable"]))
        for half in ("binding", "slack"):
            n = a[label][half]["n"]
            print("    %s %-8s  %s" % (label, half,
                  "  ".join("%s %d" % (k, n[k]) for k in sorted(n))))
    if census_only:
        return 0

    print("\n" + "=" * 74)
    print("A  the grid split (design file section 7 supplement 2, B14_A2)")
    print("=" * 74)
    for label in ("2016", "2018"):
        print("\n-- %s round, sign %+d" % (label, E.ROUNDS[label]["sign"]))
        for half in ("binding", "slack"):
            show_six(half, a[label][half], E.ROUNDS[label]["sign"])

    b = test_b(r18)
    print("\n" + "=" * 74)
    print("B  T10: the 2018 post window split by month (design file B14_A3)")
    print("=" * 74)
    for m in ("nov", "dec"):
        show_six(m, b[m], -1)

    c = test_c(r16, r18)
    print("\n" + "=" * 74)
    print("C  BBO minus NBBO, in dollars (design file B14_A4)")
    print("=" * 74)
    for label in ("2016", "2018"):
        inside = "post" if label == "2016" else "pre"
        print("\n-- %s round; the window INSIDE the pilot is '%s'" % (label, inside))
        for w in ("pre", "post"):
            row = c[label][w]
            mark = "  <- inside the pilot" if w == inside else ""
            print("   %-5s %s%s" % (w,
                  "  ".join("%s %.5f" % (k, row[k]) for k in sorted(row)), mark))

    cand = test_candidates(r16, r18)
    print("\n" + "=" * 74)
    print("D  candidates for the slack residue (design file B14_A5)")
    print("=" * 74)
    print("  bin cuts (a nickel is the only fixed one): %s"
          % ", ".join("%.4f" % c if c is not None else "None" for c in cand["cuts"]))
    print("  symbols never under a nickel in the pre window: %d" % cand["n_pure_slack"])
    for label in ("2016", "2018"):
        sign = E.ROUNDS[label]["sign"]
        print("\n-- %s round, sign %+d" % (label, sign))
        show_six("pure slack", cand[label]["pure_slack"], sign)
        print("  gradient, bin 2 is just under a nickel and bin 3 just over:")
        print("     %-4s %-7s %-7s %-32s %s" % ("bin", "n(N)", "n(P)", "N gaps", "P gaps"))
        for i in range(6):
            g = cand[label]["gradient"][i]
            nN = sum(g["n"].get("N/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            nP = sum(g["n"].get("P/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            gn = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "N")
            gp = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "P")
            print("     %-4d %-7d %-7d %-32s %s" % (i, nN, nP, gn, gp))

    rd = test_rd(r16, r18)
    print("\n" + "=" * 74)
    print("E  narrow-band discontinuity at a nickel, with two placebo cuts (B14_A6)")
    print("=" * 74)
    print("  six gaps per cell, ordered N/G1 N/G2 N/G3 P/G1 P/G2 P/G3")
    for label in ("2016", "2018"):
        show_rd(rd, label, E.ROUNDS[label]["sign"])

    sp = test_split_sample(r16)
    print("\n" + "=" * 74)
    print("F  split sample: the split variable is NOT the denominator (B14_A8)")
    print("=" * 74)
    for v in ("A", "B"):
        b = sp[v]
        print("\n-- %s: split on %s, denominator %s" %
              (v, b["cut_window"], b["denominator_window"]))
        print("   gradient (2016, wants G above C), bin 2 under a nickel, 3 over:")
        for i in range(6):
            g = b["gradient"][i]
            nN = sum(g["n"].get("N/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            nP = sum(g["n"].get("P/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            gn = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "N")
            gp = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "P")
            print("     bin %d  n %-5d %-5d  N %-26s P %s" % (i, nN, nP, gn, gp))
        print("   narrow band at a nickel:")
        for h in sorted(b["band"]):
            row = []
            for sname in ("left", "right"):
                x = b["band"][h][sname]
                row.append((sum(x["n"].values()),
                            " ".join("%+.3f" % y["raw_gap"] if y["raw_gap"] is not None
                                     else " None " for y in x["inequalities"])))
            print("     h %-6s nL %-4d %-26s nR %-4d %s"
                  % (h, row[0][0], row[0][1], row[1][0], row[1][1]))

    cx = test_cross(r16)
    print("\n" + "=" * 74)
    print("G  cross-venue and cross-measure splits: nothing shared at all (B14_A9)")
    print("=" * 74)
    for mode in ("venue", "measure"):
        b = cx[mode]
        print("\n-- split by %s; %d symbols splittable" % (mode, b["n_splittable"]))
        for i in range(6):
            g = b["gradient"][i]
            nN = sum(g["n"].get("N/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            nP = sum(g["n"].get("P/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            gn = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "N")
            gp = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "P")
            print("     bin %d  n %-5d %-5d  N %-26s P %s" % (i, nN, nP, gn, gp))
        print("   narrow band, N-side median of the six gaps:")
        for h in sorted(b["band"]):
            out = []
            for sname in ("left", "right"):
                x = b["band"][h][sname]
                gs = [y["raw_gap"] for y in x["inequalities"]
                      if y["ctr"] == "N" and y["raw_gap"] is not None]
                out.append((sum(x["n"].values()), median(gs) if gs else None))
            l, rr = out
            ratio = (l[1] / rr[1]) if (l[1] and rr[1] and rr[1] != 0) else None
            print("     h %-6s nL %-4d medL %-9s nR %-4d medR %-9s L/R %s"
                  % (h, l[0], "%+.4f" % l[1] if l[1] is not None else "None",
                     rr[0], "%+.4f" % rr[1] if rr[1] is not None else "None",
                     "%.2f" % ratio if ratio else "n/a"))

    pl = test_placebo_did(r16)
    print("\n" + "=" * 74)
    print("H  placebo DiD before the pilot, split on 2016-04/05 (B14_A10)")
    print("=" * 74)
    print("  split screen: %s" % pl["split_stats"])
    print("  cuts: %s" % ", ".join("%.4f" % c if c is not None else "None"
                                   for c in pl["cuts"]))
    for name in ("placebo", "real"):
        b = pl[name]
        tag = "  <- BOTH windows before the pilot" if name == "placebo" else ""
        print("\n-- %s: %s -> %s%s" % (name, b["pre"], b["post"], tag))
        for i in range(6):
            g = b["gradient"][i]
            nN = sum(g["n"].get("N/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            nP = sum(g["n"].get("P/" + x, 0) for x in ("C", "G1", "G2", "G3"))
            gn = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "N")
            gp = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                          for x in g["inequalities"] if x["ctr"] == "P")
            print("     bin %d  n %-5d %-5d  N %-26s P %s" % (i, nN, nP, gn, gp))
        print("   narrow band, N-side median of the six gaps:")
        for h in sorted(b["band"]):
            out = []
            for sname in ("left", "right"):
                x = b["band"][h][sname]
                gs = [y["raw_gap"] for y in x["inequalities"]
                      if y["ctr"] == "N" and y["raw_gap"] is not None]
                out.append((sum(x["n"].values()), median(gs) if gs else None))
            l, rr = out
            ratio = (l[1] / rr[1]) if (l[1] and rr[1] and rr[1] != 0) else None
            print("     h %-6s nL %-4d medL %-9s nR %-4d medR %-9s L/R %s"
                  % (h, l[0], "%+.4f" % l[1] if l[1] is not None else "None",
                     rr[0], "%+.4f" % rr[1] if rr[1] is not None else "None",
                     "%.2f" % ratio if ratio else "n/a"))

    sl = test_slack_placebo(r16, r18)
    print("\n" + "=" * 74)
    print("I  pure-slack residue and the 2018 placebo (B14_A11)")
    print("=" * 74)
    print("  pure slack on the 2016-04/05 split window: %d symbols" % sl["n_pure_slack"])
    for name in ("placebo", "real"):
        b = sl[name]
        tag = "  <- both windows before the pilot" if name == "placebo" else ""
        print("\n-- pure slack, %s%s   %d/6 hold" % (name, tag, b["holds"]))
        for ctr in ("N", "P"):
            row = [x for x in b["inequalities"] if x["ctr"] == ctr]
            print("     %s  C n=%-5d Delta %-11s  gaps %s"
                  % (ctr, b["n"].get(ctr + "/C", 0),
                     "None" if b["table"].get(ctr + "/C") is None
                     else "%+.6f" % b["table"][ctr + "/C"],
                     " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None
                              else " None " for x in row)))
    print("\n-- 2018 placebo: Aug -> Sep, BOTH inside the pilot, wants G below C")
    for i in range(6):
        g = sl["placebo_2018"]["gradient"][i]
        nN = sum(g["n"].get("N/" + x, 0) for x in ("C", "G1", "G2", "G3"))
        nP = sum(g["n"].get("P/" + x, 0) for x in ("C", "G1", "G2", "G3"))
        gn = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                      for x in g["inequalities"] if x["ctr"] == "N")
        gp = " ".join("%+.4f" % x["raw_gap"] if x["raw_gap"] is not None else "  None "
                      for x in g["inequalities"] if x["ctr"] == "P")
        print("     bin %d  n %-5d %-5d  N %-26s P %s" % (i, nN, nP, gn, gp))

    res = {"stage": "B14", "diagnostic_only": True,
           "diagnostic_reason": ("recheck registered in design file section 7 "
                                 "supplement 2 clauses B14_A2, B14_A3 and B14_A4; the station "
                                 "is not closed"),
           "nickel": NICKEL, "min_days_monthly": MIN_DAYS_MONTHLY,
           "A_grid_split": a, "B_month_split": b, "C_bbo_minus_nbbo": c, "D_candidates": cand, "E_narrow_band": rd, "F_split_sample": sp, "G_cross_split": cx, "H_placebo_did": pl, "I_slack_placebo": sl}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, sort_keys=True, default=list)
        fh.write("\n")
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the split threshold is the pilot's own quoting increment, not a chosen "
        "calibration", NICKEL == 0.05)
    chk("the split is computed on the pre window, which is before treatment",
        E.ROUNDS["2016"]["pre"][1] < "20161001")
    chk("canon is shared with the other two scripts", G.canon is E.canon)
    t = {"N/C": 0.10, "N/G1": 0.50, "N/G2": 0.05, "N/G3": 0.40,
         "P/C": 0.10, "P/G1": 0.50, "P/G2": 0.50, "P/G3": 0.50}
    up = six(t, +1)
    chk("six() reads direction: sign=+1 gives 5/6 on this table",
        sum(1 for x in up if x["holds"]) == 5)
    dn = six(t, -1)
    chk("and sign=-1 gives 1/6 on the same table, the one cell whose gap is "
        "negative", sum(1 for x in dn if x["holds"]) == 1)
    chk("no cell holds under both signs, since a gap cannot be both positive and "
        "negative", not any(x["holds"] and y["holds"] for x, y in zip(up, dn)))
    chk("the two counts are complementary once the zero-gap cells are excluded",
        sum(1 for x in up if x["holds"]) + sum(1 for x in dn if x["holds"])
        == sum(1 for x in up if x["raw_gap"] not in (None, 0)))
    chk("a missing cell yields holds=False, not a crash",
        six({"N/C": 0.1}, +1)[0]["holds"] is False)
    r = {"tag": {"pre": {"G1"}, "post": {"C"}}}
    chk("group_of reads the window it is told to", group_of(r, "pre") == "G1"
        and group_of(r, "post") == "C")
    chk("a non-unique label yields None",
        group_of({"tag": {"pre": {"C", "G1"}}}, "pre") is None)
    fake = {("N", "A"): {"pre": {"bbo": [0.01, 0.20]}},
            ("N", "B"): {"pre": {"bbo": [0.20, 0.30]}}}
    ps = pure_slack(fake)
    chk("pure slack excludes a symbol that was under a nickel even once",
        ps[("N", "A")] is False and ps[("N", "B")] is True)
    bn, cu = gradient_bins({("N", str(i)): {"pre": {"bbo": [0.01 * (i + 1)]}}
                            for i in range(12)})
    chk("a nickel is the third cut and it is exactly 0.05", cu[2] == NICKEL)
    chk("the gradient yields six bins", len(set(bn.values())) <= 6 and max(bn.values()) <= 5)
    chk("everything under a nickel lands in bins 0 to 2 and everything over in 3 to 5",
        all((v < 3) == (0.01 * (int(k[1]) + 1) < NICKEL) for k, v in bn.items()))
    chk("the B14_A10 split window shares no observation with any other window",
        W_MAY[1] < W_PLACEBO_PRE[0] and W_PLACEBO_PRE[1] < "20160801")
    chk("every B14_A10 window sits before the pilot took effect on 2016-10-03",
        W_PLACEBO_PRE[1] < "20161003")
    fb, st = far_binder({("N", "A"): {"apr": {"bbo": [0.01]}, "may": {"bbo": [0.02]}},
                         ("N", "B"): {"apr": {"bbo": [0.01]}, "may": {"bbo": [0.20]}},
                         ("N", "C"): {"apr": {"bbo": []}, "may": {"bbo": [0.20]}}})
    chk("a name both months agree on is kept", ("N", "A") in fb)
    chk("a name that flips side between the two months is screened out and counted",
        ("N", "B") not in fb and st["unstable"] == 1)
    chk("a name missing a split month is counted separately, not called unstable",
        st["no split data"] == 1)
    chk("the two split-sample months do not overlap",
        SPLIT_A[1] < SPLIT_B[0])
    chk("both split-sample months sit before the pilot took effect in 2016-10",
        SPLIT_A[1] < "20161001" and SPLIT_B[1] < "20161001")
    chk("every bandwidth is a multiple or half of the original one-cent grid",
        all(abs(h / 0.005 - round(h / 0.005)) < 1e-12 for h in BANDWIDTHS))
    chk("the placebo cut is not any grid width", PLACEBO_ROUND not in (0.01, 0.05))
    chk("the split source is a window before the pilot, stated in the record",
        "before the pilot" in SPLIT_SOURCE)
    fake16 = {("N", "A"): {"pre": {"bbo": [0.01]}}, ("N", "B"): {"pre": {"bbo": [0.20]}},
              ("N", "C"): {"pre": {"bbo": []}}}
    bb = binder(fake16)
    chk("binder marks a penny-wide name binding and a twenty-cent name slack",
        bb[("N", "A")] is True and bb[("N", "B")] is False)
    chk("a symbol with no pre-window spread is left out of the split entirely, "
        "not silently called slack", ("N", "C") not in bb)
    chk("monthly MIN_DAYS is scaled down and said so before the run",
        MIN_DAYS_MONTHLY == 5 and MIN_DAYS_MONTHLY < G.MIN_DAYS)
    import re
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    # Code points, not literal characters: a literal class here would fail on
    # itself, the same self-reference that broke two earlier checks in this station.
    cjk = re.compile("[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
    hits = sorted({c for c in src if cjk.match(c)})
    chk("no CJK or fullwidth punctuation in this file: " +
        ("".join(hits) if hits else "zero"), not hits)
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.census:
        return run(census_only=True)
    if a.run:
        return run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
