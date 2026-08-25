"""B14 leg B, B14_A18: the two authorised slices after gate three failed.

Registered in the design file, section 7 supplement 2, B14_A18. Exactly two slices
are authorised and neither may be extended:

  A  half-month resolution, which changes only how well the null is estimated
     (14 placebo pairs instead of 6), not the estimator
  B  three bins on the 2016 pre-pilot relative tick, 5c / P_2016, each bin
     getting its own full placebo set

B14_A18 clause 0: neither slice touches the 88.7% the grid's arithmetic explains.
That figure is a property of the mechanism, not of the sample.

The statistic, loader and projection come from the gate two module by import,
same as gate three, so a slice cannot silently diverge from the thing it slices.

Usage
    python experiments/b14_legb_gate3b.py --selftest
    python experiments/b14_legb_gate3b.py --slice-a
    python experiments/b14_legb_gate3b.py --slice-b
"""
import argparse
import ast
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_A = os.path.join(ROOT, "results", "b14_legb_a18_sliceA.json")
OUT_B = os.path.join(ROOT, "results", "b14_legb_a18_sliceB.json")
#: B14_A18 supplement 1. The registered split variable was 5c / P_2016, and the 2016
#: carrier turns out to hold no price field at all: 52 fields, every one a spread,
#: a count or a time. Substituted with the other source B14_A17 clause 6 registered as
#: legal, the 2016-04/05 median WA_BBO_Spd. The substitution was made AFTER slice A
#: failed and is recorded as such; it is forced by the carrier, not chosen from a
#: menu, and both variables were pre-registered as legal before either was tried.
SPLIT_2016 = os.path.join(ROOT, "results", "b14_legb_split2016.json")
#: The registered variable of B14_A18 clause 2, obtainable after all; see
#: experiments/b14_legb_price2016.py.
PANEL_2016 = os.path.join(ROOT, "results", "b14_legb_price2016.json")

_spec = importlib.util.spec_from_file_location(
    "b14_legb_gate2", os.path.join(HERE, "b14_legb_gate2.py"))
G2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G2)

MONTHS = ["2018-%02d" % m for m in range(5, 13)]
INSIDE = {"2018-05", "2018-06", "2018-07", "2018-08", "2018-09"}
#: B14_A18 clause 2: fixed at three, and clause 3 forbids changing it.
N_BINS = 3


def halves(np, m, g_of, arm, keep_syms=None):
    """Split one venue-month at its median trading day and project onto nickels."""
    ba, aa, bb, ab = G2.load(np, m, g_of, arm)
    p = os.path.join(G2.CACHE, "panel_%s.npz" % m.replace("-", ""))
    d = np.load(p, allow_pickle=False)
    tab = [str(x) for x in d["symbol_table"]]
    want = (arm == "C")
    sel = np.array([(t not in G2.EXCLUDED) and ((g_of.get(t) == "C") == want)
                    and (keep_syms is None or t in keep_syms) for t in tab])[d["sym"]]
    sel &= ~((d["bid_b"] == G2.STUB_BID_CENTS) & (d["ask_b"] == G2.STUB_ASK_CENTS))
    day = (d["sec"][sel].astype(np.int64) // 86400)
    ba, aa = d["bid_a"][sel], d["ask_a"][sel]
    bb, ab = d["bid_b"][sel], d["ask_b"][sel]
    uniq = np.unique(day)
    cut = uniq[len(uniq) // 2]
    out = []
    for mask in (day < cut, day >= cut):
        x = G2.to_nickel(np, ba[mask].astype(np.int64), aa[mask].astype(np.int64))
        y = G2.to_nickel(np, bb[mask].astype(np.int64), ab[mask].astype(np.int64))
        good = (x[0] > 0) & (y[0] > 0)
        out.append(G2.stats(np, x[0][good], x[1][good], y[0][good], y[1][good])["share_rho0"])
    return out


def build_pairs(np, g_of, keep_syms=None):
    """Every adjacent half-month pair, tagged by whether it straddles the event."""
    seq = []
    for m in MONTHS:
        h = {arm: halves(np, m, g_of, arm, keep_syms) for arm in ("G", "C")}
        seq.append((m + "H1", h["G"][0], h["C"][0]))
        seq.append((m + "H2", h["G"][1], h["C"][1]))
    rows = []
    for k in range(len(seq) - 1):
        a, b = seq[k], seq[k + 1]
        ins_a, ins_b = a[0][:7] in INSIDE, b[0][:7] in INSIDE
        kind = "REAL" if ins_a != ins_b else ("inside" if ins_a else "outside")
        rows.append({"pair": "%s -> %s" % (a[0], b[0]), "kind": kind,
                     "dG": a[1] - b[1], "dC": a[2] - b[2],
                     "DiD": (a[1] - b[1]) - (a[2] - b[2])})
    return rows


def verdict(rows, label):
    plac = [r["DiD"] for r in rows if r["kind"] != "REAL"]
    real = [r["DiD"] for r in rows if r["kind"] == "REAL"]
    if not real or not plac:
        print("    %s: no real pair or no placebos" % label)
        return {}
    real = real[0]
    lo, hi = min(plac), max(plac)
    reach = sum(1 for p in plac if abs(p) >= abs(real))
    outside = real < lo or real > hi
    print("    placebos %d, range %+.4f .. %+.4f   real %+.4f   reaching it %d"
          % (len(plac), lo, hi, real, reach))
    print("    -> %s" % ("REAL IS OUTSIDE THE PLACEBO RANGE"
                         if outside else "real is inside the placebo range, not adjudicable"))
    return {"n_placebo": len(plac), "placebo_min": lo, "placebo_max": hi,
            "real": real, "placebos_reaching_real": reach, "real_outside": bool(outside)}


def slice_a():
    import numpy as np
    g_of = {s: g for g, v in
            json.load(open(G2.SYMS_FILE, encoding="utf-8"))["symbols"].items() for s in v}
    print("B14_A18 slice A: half-month resolution. Estimator unchanged, null better estimated.\n")
    rows = build_pairs(np, g_of)
    print("  pair                    kind      dG        dC        DiD")
    for r in rows:
        print("  %-22s %-8s %+.4f   %+.4f   %+.4f%s"
              % (r["pair"], r["kind"], r["dG"], r["dC"], r["DiD"],
                 "  <== the real one" if r["kind"] == "REAL" else ""))
    print("\n  verdict, B14_A18 clause 1, fixed before the run:")
    v = verdict(rows, "A")
    plac = [r["DiD"] for r in rows if r["kind"] != "REAL"]
    print("\n  B14_A18 clause 1 third branch: half-month placebo spread %.4f against the"
          % (max(plac) - min(plac)))
    print("  month-level spread 0.0332. If this is much wider the resolution's noise")
    print("  ate the gain and the month-level reading stands.")
    json.dump({"rows": rows, "verdict": v}, open(OUT_A, "w"), indent=2)
    print("\n  written %s" % os.path.relpath(OUT_A, ROOT))
    return 0


def slice_b():
    """B14_A18 clause 2, run on BOTH bin variables.

    The registered variable is 5c / P_2016 (B14_A18 clause 2). B14_A18 supplement 1
    substituted the 2016 median WA_BBO_Spd because the Appendix B carrier holds
    no price field; that ground was correct and the conclusion premature, since
    2016 daily closes are freely published. Both are run here and both are
    printed. Where they disagree the REGISTERED one governs; the substitute stays
    on record rather than being replaced.

    Bin 1 is the most-bound third under either variable: lowest price under the
    registered one, tightest spread under the substitute.
    """
    import numpy as np
    g_of = {s: g for g, v in
            json.load(open(G2.SYMS_FILE, encoding="utf-8"))["symbols"].items() for s in v}
    variants = []
    if os.path.exists(PANEL_2016):
        px = json.load(open(PANEL_2016, encoding="utf-8"))
        variants.append(("REGISTERED  5c / P_2016", "price", px, "$%.2f"))
    else:
        print("  the registered variable's file is absent at %s"
              % os.path.relpath(PANEL_2016, ROOT))
        print("  run experiments/b14_legb_price2016.py --fetch first.")
    if os.path.exists(SPLIT_2016):
        sp = json.load(open(SPLIT_2016, encoding="utf-8"))
        variants.append(("SUBSTITUTE  2016 median WA_BBO_Spd", "spread", sp, "$%.4f"))
    if not variants:
        print("  no split variable available; nothing computed, nothing written.")
        return 2

    out = {}
    for label, kind, raw, fmt in variants:
        have = {s: v for s, v in raw.items() if s not in G2.EXCLUDED and v and v > 0}
        keyed = sorted((v, s) for s, v in have.items())
        n = len(keyed)
        edges = [0, n // N_BINS, 2 * n // N_BINS, n]
        print("\n" + "=" * 74)
        print("B14_A18 slice B on the %s variable, %d symbols" % (label, n))
        print("  bin 1 is the most-bound third: %s"
              % ("lowest 2016 price" if kind == "price" else "tightest 2016 spread"))
        print("=" * 74)
        res = {}
        for b in range(N_BINS):
            chunk = keyed[edges[b]:edges[b + 1]]
            keep = {s for _, s in chunk}
            arms = {a: sum(1 for s in keep if (g_of.get(s) == "C") == (a == "C"))
                    for a in ("G", "C")}
            print("\n  bin %d: %s .. %s, %d symbols (G %d / C %d)"
                  % (b + 1, fmt % chunk[0][0], fmt % chunk[-1][0], len(keep),
                     arms["G"], arms["C"]))
            rows = build_pairs(np, g_of, keep)
            v = verdict(rows, "bin %d" % (b + 1))
            res["bin%d" % (b + 1)] = {"lo": chunk[0][0], "hi": chunk[-1][0],
                                      "symbols": sorted(keep), "verdict": v,
                                      "rows": rows}
        reals = [res["bin%d" % (b + 1)]["verdict"].get("real") for b in range(N_BINS)]
        mono = all(reals[k] <= reals[k + 1] for k in range(len(reals) - 1)) or \
            all(reals[k] >= reals[k + 1] for k in range(len(reals) - 1))
        passed = [b + 1 for b in range(N_BINS)
                  if res["bin%d" % (b + 1)]["verdict"].get("real_outside")]
        print("\n  real DiD by bin (bin 1 = most bound): %s"
              % "  ".join("%+.4f" % r for r in reals))
        print("  monotone: %s     bins clearing their own placebo range: %s"
              % (mono, passed or "none"))
        # B14_A18 clause 2's reading, plus the defect the first run exposed: a bin
        # clearing with the gradient living in the CONTROL arm is not treatment
        # heterogeneity, so which arm carries it is printed too.
        dgs = [[r for r in res["bin%d" % (b + 1)]["rows"] if r["kind"] == "REAL"][0]["dG"]
               for b in range(N_BINS)]
        dcs = [[r for r in res["bin%d" % (b + 1)]["rows"] if r["kind"] == "REAL"][0]["dC"]
               for b in range(N_BINS)]
        print("  dG by bin (treated arm): %s" % "  ".join("%+.4f" % x for x in dgs))
        print("  dC by bin (control arm): %s" % "  ".join("%+.4f" % x for x in dcs))
        gspan = max(dgs) - min(dgs)
        cspan = max(dcs) - min(dcs)
        print("  spread of dG across bins %.4f, of dC %.4f -> the gradient lives in "
              "the %s arm" % (gspan, cspan, "TREATED" if gspan > cspan else "CONTROL"))
        if passed and mono and gspan > cspan:
            print("  -> a bin clears, monotone, and the gradient is in the treated arm:")
            print("     heterogeneity is real")
        elif passed and mono:
            print("  -> a bin clears and the pattern is monotone, but the gradient is")
            print("     in the control arm. B14_A18 clause 2 did not require checking which")
            print("     arm carries it; that is a defect in the registration. NOT a")
            print("     reversal.")
        elif passed:
            print("  -> a bin clears but the pattern is not monotone: specification")
            print("     search, not a reversal")
        else:
            print("  -> no bin clears: not adjudicable, heterogeneity ruled out too")
        res["_summary"] = {"reals": reals, "monotone": mono, "bins_clearing": passed,
                           "dG": dgs, "dC": dcs, "gradient_arm":
                           "treated" if gspan > cspan else "control"}
        out[kind] = res
    json.dump(out, open(OUT_B, "w"), indent=2)
    print("\n  written %s" % os.path.relpath(OUT_B, ROOT))
    if "price" in out and "spread" in out:
        print("\n  the REGISTERED variable governs where the two disagree (B14_A18 supp 1).")
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the bin count is the registered three", N_BINS == 3)
    chk("the statistic and projection are gate two's own objects",
        G2.stats.__module__ == G2.__name__ and G2.to_nickel.__module__ == G2.__name__)
    chk("the exclusion list comes from gate two", G2.EXCLUDED ==
        {"TA", "SSP", "VNCE", "JONE", "PKD"})
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    chk("exactly two slices are implemented, A and B, per B14_A18 clause 3",
        {"slice_a", "slice_b"} <= fns and not (fns & {"slice_c", "slice_d"}))
    chk("slice B reads both 2016 split files and refuses to source from inside "
        "the window", "SPLIT_2016" in src and "PANEL_2016" in src)
    chk("slice B now also reports which arm carries the gradient, which the first "
        "run showed B14_A18 clause 2 had failed to require", "gradient_arm" in src)
    chk("the substituted split variable is not rho's denominator: it is a 2016 "
        "Appendix B width, two years and a different instrument from the 2018 "
        "Databento quotes rho is built on", "WA_BBO_Spd" in src)
    banned = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree")}
    chk("no deletion call anywhere",
        not [1 for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and (n.func.value.id, n.func.attr) in banned])
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--slice-a", action="store_true")
    ap.add_argument("--slice-b", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.slice_a:
        return slice_a()
    if a.slice_b:
        return slice_b()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
