"""B14-0, the gate: does the friction half widen on treated relative to control.

Criteria fixed before the run in the design file, section 4:

    Delta(sym, ctr) = log( median daily spd in the post window
                           / median daily spd in the pre window )
    group statistic = median of Delta over symbols within the group
    PASS            = G1>C and G2>C and G3>C, on both venue N and venue P (six)

Primary convention = WA_BBO_Spd weighted by Order_Shares_Ct.
Run alongside: the same quantity weighted by Order_Count (the weighting-convention
check, D3-3), and WA_NBBO_Spd share weighted (a cross-check, excluded from the
verdict).

Usage
    python experiments/b14_gate0.py --selftest
    python experiments/b14_gate0.py --run
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "data", "cache", "b14")
OUT = os.path.join(ROOT, "results", "b14_gate0.json")

PRE = ("20160801", "20160930")
POST = ("20161101", "20161231")
MIN_DAYS = 10
GRP_FROM = "post"   # D3-9', design file section 3 supplement 1: read the group
                    # assignment from the post window only
#: T8 (design file section 3 supplement 2): the authoritative group list published
#: by FINRA. When supplied it replaces the post-window inference.
AUTH = os.path.join(ROOT, "data", "raw", "Tick_Pilot_Test_Group_Assignments.txt")
GROUPS = ["C", "G1", "G2", "G3"]
# (name, numerator column, set of denominator columns, description).
# The v2 column numbers are the HEAD line of b14_tickpilot_panel.py.
MEASURES = [
    ("bbo_shr", 4, (5,), "primary: WA_BBO_Spd, share weighted"),
    ("bbo_cnt", 6, (7,), "weighting-convention check: WA_BBO_Spd, order-count weighted"),
    ("bbo_shr_adv", 4, (5, 14),
     "T5 adverse convention: zero-spread rows admitted at their true share weight\n      (design file section 4 supplement 1)"),
    ("bbo_shr_adv2", 4, (5, 14, 16),
     "T6 arithmetic sensitivity: blanks and zeros both admitted at their true share\n      weight (design file section 4 supplement 2)"),
    ("nbbo_shr", 8, (9,), "cross-check: WA_NBBO_Spd share weighted, excluded from the verdict"),
]
T5_MEASURE = "bbo_shr_adv"
T6_MEASURE = "bbo_shr_adv2"


def canon(sym):
    """The ticker as a key.

    The venues do not spell class shares the same way, and do not spell them the
    same way over time. Arca writes "AMSW A" through 2018-11 and "AMSWA" from
    2018-12; NYSE writes "AMSWA" throughout; the FINRA list writes "AMSWA".
    Keying on the raw string therefore splits one security into two records whose
    windows do not overlap, and the ten-day rule then drops both.

    Measured 2026-08-19: 27 Arca symbols change spelling inside the 2018 round and
    0 inside 2016, so this repairs the leg A round and leaves B14-0 untouched,
    which the reproduction check is there to confirm rather than assume. A further
    25 symbols could not be matched against the authoritative list for the same
    reason. Despacing merges no two distinct tickers: checked over every spelling
    in every cached panel, 0 collisions.
    """
    return sym.replace(" ", "")


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def load_authoritative():
    """FINRA Tick_Pilot_Test_Group_Assignments.txt -> {ticker: group}."""
    out = {}
    with open(AUTH, encoding="latin-1") as fh:
        head = fh.readline().rstrip("\n").split("|")
        i_sym = head.index("Ticker_Symbol")
        i_grp = head.index("Tick_Size_Pilot_Program_Group")
        for line in fh:
            f = line.rstrip("\n").split("|")
            if len(f) <= max(i_sym, i_grp):
                continue
            g = f[i_grp].strip()
            if g in GROUPS:
                out[canon(f[i_sym].strip())] = g
    return out


def load():
    """(ctr, sym) -> {"grp": set, "pre": {name: [spd]}, "post": {...}}"""
    import math
    rec = {}
    files = sorted(f for f in os.listdir(CACHE)
                   if f.startswith("panel_v2_") and f.endswith(".csv"))
    assert files, "no v2 cache; run b14_tickpilot_panel.py --build first"
    for fn in files:
        with open(os.path.join(CACHE, fn)) as fh:
            head = fh.readline()
            assert head.startswith("date,ctr,symbol,test_group,"), fn
            for line in fh:
                if line.startswith("#"):
                    continue
                p = line.rstrip("\n").split(",")
                date, ctr, sym, grp = p[0], p[1], canon(p[2]), p[3]
                if PRE[0] <= date <= PRE[1]:
                    win = "pre"
                elif POST[0] <= date <= POST[1]:
                    win = "post"
                else:
                    continue
                r = rec.get((ctr, sym))
                if r is None:
                    r = rec[(ctr, sym)] = {
                        "grp": set(),
                        "pre": {m[0]: [] for m in MEASURES},
                        "post": {m[0]: [] for m in MEASURES},
                    }
                # D3-9' (design file section 3 supplement 1): read the group
                # assignment from the post window only. The field records the
                # state a security was in on that day, so in the pre window every
                # treated security is also labelled C.
                if win == GRP_FROM:
                    r["grp"].add(grp)
                for name, inum, idens, _ in MEASURES:
                    den = sum(float(p[i]) for i in idens)
                    if den > 0:
                        v = float(p[inum]) / den
                        if v > 0:
                            r[win][name].append(math.log(v))
    return rec, files


def deltas(rec, auth=None):
    """One Delta per (ctr, sym), separately per measure.

    Medians are taken on the log, so Delta is a difference of two medians.
    """
    out = {m[0]: {} for m in MEASURES}
    skipped = {"group not unique": 0, "too few days": 0, "no post-window label": 0}
    for (ctr, sym), r in rec.items():
        if auth is not None:
            grp = auth.get(sym)
            if grp is None:
                skipped["not on the authoritative list"] = skipped.get(
                    "not on the authoritative list", 0) + 1
                continue
        else:
            if not r["grp"]:
                skipped["no post-window label"] += 1
                continue
            if len(r["grp"]) != 1:
                skipped["group not unique"] += 1
                continue
            grp = next(iter(r["grp"]))
        if grp not in GROUPS:
            continue
        for name in out:
            a, b = r["pre"][name], r["post"][name]
            if len(a) < MIN_DAYS or len(b) < MIN_DAYS:
                if name == MEASURES[0][0]:
                    skipped["too few days"] += 1
                continue
            out[name].setdefault((ctr, grp), []).append(median(b) - median(a))
    return out, skipped


args_authoritative = [False]


def run():
    rec, files = load()
    print("read %d cache files, %d (venue, symbol) pairs" % (len(files), len(rec)))
    auth = load_authoritative() if args_authoritative[0] else None
    if auth is not None:
        print("T8: groups from the FINRA authoritative list, %d symbols "
              "(design file section 3 supplement 2)" % len(auth))
    d, skipped = deltas(rec, auth)
    print("dropped: " + ", ".join("%s %d" % (k, v) for k, v in skipped.items()
                              if v) + "\n")

    ctrs = sorted({c for name in d for (c, g) in d[name]})
    res = {"pre": PRE, "post": POST, "min_days": MIN_DAYS, "measures": {}}
    verdict = {}

    prev = None
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT))
        except Exception:
            prev = None

    for name, _, _, desc in MEASURES:
        print("== %s (%s) ==" % (name, desc))
        print("  %-6s %-4s %8s %11s %12s"
              % ("venue", "grp", "symbols", "med Delta", "vs C"))
        tab = {}
        for ctr in ctrs:
            base = median(d[name].get((ctr, "C"), []))
            for grp in GROUPS:
                xs = d[name].get((ctr, grp), [])
                m = median(xs)
                tab[ctr + "/" + grp] = {"n": len(xs), "delta": m}
                rel = "" if (m is None or base is None) else "%+.6f" % (m - base)
                print("  %-6s %-4s %8d %11s %12s"
                      % (ctr, grp, len(xs),
                         "None" if m is None else "%+.6f" % m, rel))
        res["measures"][name] = {"desc": desc, "table": tab}
        ineq = []
        for ctr in ctrs:
            base = median(d[name].get((ctr, "C"), []))
            for grp in ["G1", "G2", "G3"]:
                m = median(d[name].get((ctr, grp), []))
                ok = (m is not None and base is not None and m > base)
                ineq.append({"ctr": ctr, "grp": grp, "holds": ok,
                             "margin": None if (m is None or base is None) else m - base})
        res["measures"][name]["inequalities"] = ineq
        v = all(x["holds"] for x in ineq) and len(ineq) == 6
        verdict[name] = v
        print("  six inequalities: %d/%d hold  ->  %s\n"
              % (sum(1 for x in ineq if x["holds"]), len(ineq), "PASS" if v else "FAIL"))

    primary = MEASURES[0][0]
    weight_chk = MEASURES[1][0]
    res["verdict"] = {
        "primary": primary,
        "B14-0": "PASS" if verdict[primary] else "FAIL",
        "weight_agrees": verdict[primary] == verdict[weight_chk],
        "per_measure": verdict,
    }

    t6 = res["measures"][T6_MEASURE]["inequalities"]
    t6_all = all(x["holds"] for x in t6) and len(t6) == 6
    res["t6"] = {
        "measure": T6_MEASURE,
        "all_hold": bool(t6_all),
        "failing": [x["ctr"] + "/" + x["grp"] for x in t6 if not x["holds"]],
        "note": ("blanks are states with no quote, i.e. the widest kind; "
                 "imputing them at zero is a bound on the arithmetic and not "
                 "on the world, so a failure here is not a threat to B14-0 "
                 "(design file section 4 supplement 2)"),
    }

    t5 = res["measures"][T5_MEASURE]["inequalities"]
    t5_all = all(x["holds"] for x in t5) and len(t5) == 6
    res["t5"] = {
        "measure": T5_MEASURE,
        "settled": bool(t5_all),
        "failing": [x["ctr"] + "/" + x["grp"] for x in t5 if not x["holds"]],
    }

    # The reproduction check required by design file section 4 supplement 1:
    # adding columns must not move existing ones, so re-running the primary
    # convention on the v2 cache has to reproduce the six registered margins
    # digit for digit. Failure to reproduce is a code error and voids every
    # reading of this run.
    repro = None
    if prev and "measures" in prev and primary in prev["measures"]:
        old = {(x["ctr"], x["grp"]): x["margin"]
               for x in prev["measures"][primary]["inequalities"]}
        new = {(x["ctr"], x["grp"]): x["margin"]
               for x in res["measures"][primary]["inequalities"]}
        diffs = [(k, old[k], new[k]) for k in new
                 if k in old and old[k] is not None and new[k] is not None
                 and abs(old[k] - new[k]) > 0]
        repro = {"checked": len([k for k in new if k in old]),
                 "identical": not diffs,
                 "diffs": [{"cell": k[0] + "/" + k[1], "was": a, "now": b}
                           for k, a, b in diffs]}
    res["reproduction_check"] = repro

    # This repository's record shape: stage plus
    # criteria[{name, passed, detail}]. One entry per inequality, one for the
    # weighting-convention check, and the NBBO cross-check marked diagnostic so
    # it does not count.
    crit = []
    for x in res["measures"][primary]["inequalities"]:
        c, g = x["ctr"], x["grp"]
        t = res["measures"][primary]["table"]
        crit.append({
            "name": "B14-0  %s on venue %s: median delta exceeds control" % (g, c),
            "passed": bool(x["holds"]),
            "detail": ("%s %+.6f over %d symbols, C %+.6f over %d, margin %+.6f"
                       % (g, t[c + "/" + g]["delta"], t[c + "/" + g]["n"],
                          t[c + "/C"]["delta"], t[c + "/C"]["n"], x["margin"])),
        })
    crit.append({
        "name": "B14-0  the verdict does not turn on the weighting convention",
        "passed": bool(res["verdict"]["weight_agrees"]),
        "detail": ("share-weighted verdict %s, order-count-weighted verdict %s "
                   "(design file D3-3: disagreement makes the gate unadjudicable)"
                   % ("PASS" if verdict[primary] else "FAIL",
                      "PASS" if verdict[weight_chk] else "FAIL")),
    })
    for x in res["measures"]["nbbo_shr"]["inequalities"]:
        c, g = x["ctr"], x["grp"]
        crit.append({
            "name": "B14-0  cross-check on the consolidated spread: %s on %s" % (g, c),
            "passed": bool(x["holds"]),
            "diagnostic": True,
            "detail": "margin %+.6f; design file section 4 excludes this from the verdict"
                      % x["margin"],
        })
    for x in t5:
        crit.append({
            "name": "B14-0/T5  adverse convention, %s on venue %s"
                    % (x["grp"], x["ctr"]),
            "passed": bool(x["holds"]),
            "detail": ("margin %+.6f with zero-spread rows admitted at their true "
                       "share weight; design file section 4 supplement 1"
                       % x["margin"]),
        })
    for x in t6:
        crit.append({
            "name": "B14-0/T6  blanks and zeros both forced to zero, %s on venue %s"
                    % (x["grp"], x["ctr"]),
            "passed": bool(x["holds"]),
            "diagnostic": True,
            "detail": ("margin %+.6f; a blank is a no-quote state, so this "
                       "convention is a bound on the arithmetic and not on the "
                       "world (design file section 4 supplement 2)" % x["margin"]),
        })
    crit.append({
        "name": "B14-0  the six registered margins reproduce on the v2 cache",
        "passed": bool(repro is None or repro["identical"]),
        "detail": ("no prior record to compare" if repro is None else
                   "%d margins compared, %d differ"
                   % (repro["checked"], len(repro["diffs"]))),
    })
    res["stage"] = "B14"
    res["criteria"] = crit
    res["window"] = [PRE[0], POST[1]]
    res["symbols_by_venue"] = {
        c: sum(res["measures"][primary]["table"][c + "/" + g]["n"] for g in GROUPS)
        for c in ctrs
    }
    res["derived"] = {
        ("median_delta_%s_%s" % (c, g)): res["measures"][primary]["table"][c + "/" + g]["delta"]
        for c in ctrs for g in GROUPS
        if res["measures"][primary]["table"][c + "/" + g]["delta"] is not None
    }
    print("verdict (design file section 4)")
    print("  B14-0 = %s (primary convention %s)"
          % (res["verdict"]["B14-0"], primary))
    print("  weighting conventions agree: %s"
          % ("yes" if res["verdict"]["weight_agrees"]
             else "no -> the gate is unadjudicable"))
    print("  NBBO cross-check: %s (excluded from the verdict)"
          % ("PASS" if verdict["nbbo_shr"] else "FAIL"))
    print("\nT5 (design file section 4 supplement 1)")
    print("  adverse convention: %d/6 hold  ->  T5 %s"
          % (sum(1 for x in t5 if x["holds"]),
             "settled, killed" if t5_all else
             "open: " + ", ".join(res["t5"]["failing"])))
    print("\nT6 (design file section 4 supplement 2; arithmetic sensitivity, "
          "excluded from the verdict)")
    print("  blanks and zeros both forced to zero: %d/6 hold%s"
          % (sum(1 for x in t6 if x["holds"]),
             "" if t6_all else "  failing: " + ", ".join(res["t6"]["failing"])))
    print("  A blank means the venue had no quote at that moment, which is the\n"
          "  widest kind of state, so imputing zero runs against its meaning.\n"
          "  A failure here is therefore not a threat to B14-0.")

    if repro is None:
        print("  reproduction check: no prior record to compare, skipped")
    elif repro["identical"]:
        print("  reproduction check: %d primary margins identical digit for digit"
              % repro["checked"])
    else:
        print("  reproduction check: **DIFFERS**, %d margins moved -> by design\n"
              "  file section 4 supplement 1 every reading of this run is void"
              % len(repro["diffs"]))
        for d in repro["diffs"]:
            print("    %s  %r -> %r" % (d["cell"], d["was"], d["now"]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("canon strips the space that splits a class share into two records",
        canon("AMSW A") == "AMSWA" == canon("AMSWA"))
    chk("canon keeps two genuinely different class shares apart",
        canon("BELF A") != canon("BELF B"))
    chk("canon is idempotent", canon(canon("CRD A")) == canon("CRD A"))
    chk("the authoritative list is keyed through canon",
        all(" " not in k for k in load_authoritative()))
    chk("median, odd count", median([3, 1, 2]) == 2)
    chk("median, even count averages the middle two", median([1, 2, 3, 4]) == 2.5)
    chk("empty list returns None", median([]) is None)
    chk("group assignment read from the post window only (D3-9')",
        GRP_FROM == "post")
    chk("the authoritative list is on disk", os.path.exists(AUTH))
    _a = load_authoritative()
    chk("the authoritative list yields four groups and only four",
        set(_a.values()) == {"C", "G1", "G2", "G3"} and len(_a) > 2000)
    chk("the two windows do not overlap and neither contains 2016-10",
        PRE[1] < "20161001" and POST[0] > "20161031")
    chk("the windows match design file section 3, D3-6",
        PRE == ("20160801", "20160930") and POST == ("20161101", "20161231"))
    chk("the primary column numbers point at bbo over shares",
        MEASURES[0][0] == "bbo_shr" and MEASURES[0][1] == 4
        and MEASURES[0][2] == (5,))
    chk("the cross-check is excluded: it sorts last in MEASURES",
        MEASURES[-1][0] == "nbbo_shr")
    chk("the T5 denominator is den + zero_shr",
        dict((m[0], m[2]) for m in MEASURES)[T5_MEASURE] == (5, 14))
    chk("T5 shares the numerator with the primary convention",
        dict((m[0], m[1]) for m in MEASURES)[T5_MEASURE] == MEASURES[0][1])
    chk("the T6 denominator is den + zero_shr + blank_shr",
        dict((m[0], m[2]) for m in MEASURES)[T6_MEASURE] == (5, 14, 16))
    chk("the T6 denominator contains the T5 one, so T6 can only be stricter",
        set(dict((m[0], m[2]) for m in MEASURES)[T5_MEASURE])
        < set(dict((m[0], m[2]) for m in MEASURES)[T6_MEASURE]))

    r = {("N", "AAA"): {"grp": {"G1"}, "pre": {}, "post": {}},
         ("N", "BBB"): {"grp": {"C", "G1"}, "pre": {}, "post": {}},
         ("N", "CCC"): {"grp": set(), "pre": {}, "post": {}}}
    for k in r:
        for w in ("pre", "post"):
            r[k][w] = {m[0]: [0.0] * 20 for m in MEASURES}
    d, sk = deltas(r)
    chk("a symbol with a non-unique post-window label is dropped and counted",
        sk["group not unique"] == 1)
    chk("a symbol with no post-window label at all is dropped and counted",
        sk["no post-window label"] == 1)
    chk("the surviving symbol lands in (N, G1)",
        list(d["bbo_shr"]) == [("N", "G1")])

    r2 = {("N", "AAA"): {"grp": {"G1"},
                         "pre": {m[0]: [0.0] * 9 for m in MEASURES},
                         "post": {m[0]: [0.0] * 20 for m in MEASURES}}}
    d2, sk2 = deltas(r2)
    chk("a symbol with only 9 pre-window days is dropped",
        sk2["too few days"] == 1 and not d2["bbo_shr"])

    import math
    r3 = {("N", "AAA"): {"grp": {"G1"},
                         "pre": {m[0]: [math.log(0.01)] * 12 for m in MEASURES},
                         "post": {m[0]: [math.log(0.05)] * 12 for m in MEASURES}}}
    d3, _ = deltas(r3)
    chk("a penny grid becoming a nickel grid gives a Delta of log 5",
        abs(d3["bbo_shr"][("N", "G1")][0] - math.log(5)) < 1e-12)

    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--authoritative", action="store_true",
                    help="T8: groups from the FINRA authoritative list instead of the "
                         "post-window inference (design file section 3 supplement 2)")
    a = ap.parse_args()
    args_authoritative[0] = a.authoritative
    if a.authoritative:
        global OUT
        OUT = OUT.replace(".json", ".authoritative.json")
    if a.selftest:
        return selftest()
    if a.run:
        return run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
