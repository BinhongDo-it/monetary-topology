"""B14 leg A: run the gate again on the END of the pilot; all six inequalities
are predicted to reverse.

Criteria fixed before the run in the design file, section 7 supplement 2 clause A
and its expansion B14_A1:

    the 2016 round (B14-0): pre window before the nickel grid, post window after
                            -> predicts G > C
    the 2018 round (leg A): pre window inside the nickel grid, post window back on
                            the penny grid -> predicts G < C

The phrase "word for word the same conventions as sections 3 and 4" is implemented
here by importing MEASURES and median from b14_gate0 rather than copying them. The
five parallel quantities, the numerator and denominator column numbers, and the way
medians are taken therefore cannot drift between the two rounds.

This script carries a gate that can bite: --run first replays the 2016 windows under
D3-9' and must reproduce, digit for digit, the six margins registered in
results/b14_gate0.json. If it does not, the script stops and never touches 2018.
(Project rules, engineering part item 19: a new switch must reproduce existing
results at its default, and the comparison must actually be run.)

Usage
    python experiments/b14_gate_exit.py --selftest
    python experiments/b14_gate_exit.py --census   # B14_A1 clause 3, the step-zero census
    python experiments/b14_gate_exit.py --repro    # reproduction check only
    python experiments/b14_gate_exit.py --run      # reproduction check, then leg A
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate0 as G   # noqa: E402  the conventions of record, reused not copied

CACHE = os.path.join(ROOT, "data", "cache", "b14")
OUT = os.path.join(ROOT, "results", "b14_gate_exit.json")
GATE0 = os.path.join(ROOT, "results", "b14_gate0.json")
CHANGES = os.path.join(ROOT, "data", "raw", "TSPilotChanges20181001.txt")

GROUPS = G.GROUPS
MEASURES = G.MEASURES
median = G.median
canon = G.canon

ROUNDS = {
    # sign = the predicted direction: +1 means G above C, -1 means G below C
    "2016": {
        "pre": ("20160801", "20160930"), "post": ("20161101", "20161231"),
        "grp_from": "post", "sign": +1, "asof": None,
        "why": "the B14-0 round (design file section 3 D3-6, supplement 1 D3-9'); "
               "this script's reproduction check",
    },
    "2018": {
        "pre": ("20180801", "20180928"), "post": ("20181101", "20181231"),
        "grp_from": "pre", "sign": -1, "asof": "20180928",
        "why": "leg A; the pilot ended at the close on 2018-09-28 "
               "(design file section 7 supplement 2, B14_A1)",
    },
}
MIN_DAYS = G.MIN_DAYS
#: The check B14_A1 clause 1 puts in place: 09-29 and 09-30 are a weekend, so the row
#: count on those two dates must be zero.
WEEKEND_PROBE = ("20180929", "20180930")


# ------------------------------------------------------------ group assignment

def grp_replay(asof):
    """Check 2: replay TSPilotChanges to the as-of date (design file B14_A1 clause 2
    and its addendum).

    The file is SCD-2 shaped: each record carries a validity interval
    [Effective_Date, Deleted_Date). It records only the securities that changed
    (1,682 rows against a universe of 2,396), so a baseline is required.

      baseline = the universe snapshot in Tick_Pilot_Test_Group_Assignments.txt
      override = the change-history row still valid on the as-of date, taking the
                 largest Effective_Date
      exited   = the security has a row with Effective_Date <= as-of but not one
                 still valid on that date (all deleted) -> drop it from the list

    Returns (grp_map, stats).
    """
    base = dict(G.load_authoritative())
    live, seen = {}, {}
    with open(CHANGES, encoding="latin-1") as fh:
        head = fh.readline().rstrip("\n").split("|")
        i_sym = head.index("Ticker_Symbol")
        i_eff = head.index("Effective_Date")
        i_del = head.index("Deleted_Date")
        i_grp = head.index("Tick_Size_Pilot_Program_Group")
        i_post = head.index("Posting_Date")
        for line in fh:
            f = line.rstrip("\n").split("|")
            if len(f) <= max(i_sym, i_eff, i_del, i_grp, i_post):
                continue
            sym, eff, dele = (canon(f[i_sym].strip()), f[i_eff].strip(),
                              f[i_del].strip())
            grp, post = f[i_grp].strip(), f[i_post].strip()
            if not eff or eff > asof:
                continue
            seen[sym] = True
            if dele and dele <= asof:
                continue                      # this row expired before the as-of
            if grp not in GROUPS:
                continue
            key = (eff, post)
            if sym not in live or key > live[sym][0]:
                live[sym] = (key, grp)
    exited = sorted(s for s in seen if s not in live)
    out = {k: v for k, v in base.items() if k not in set(exited)}
    changed = 0
    for sym, (_, grp) in live.items():
        if out.get(sym) != grp:
            changed += 1
        out[sym] = grp
    return out, {"baseline": len(base), "mentioned in history": len(seen),
                 "valid at as-of": len(live), "exited": len(exited),
                 "group differs from baseline": changed, "after replay": len(out)}


# ------------------------------------------------------------------------ load

def load(pre, post):
    """(ctr, sym) -> {"pre_grp": set, "post_grp": set, "pre": {...}, "post": {...}}

    The same shape as b14_gate0.load, with the windows parameterised and the
    pre-window labels kept as well: the 2018 round reads its groups from the pre
    window (design file B14_A1 clause 2, D3-9").
    """
    rec, probe = {}, 0
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
                if WEEKEND_PROBE[0] <= date <= WEEKEND_PROBE[1]:
                    probe += 1
                if pre[0] <= date <= pre[1]:
                    win = "pre"
                elif post[0] <= date <= post[1]:
                    win = "post"
                else:
                    continue
                r = rec.get((ctr, sym))
                if r is None:
                    r = rec[(ctr, sym)] = {
                        "pre_grp": set(), "post_grp": set(),
                        "pre": {m[0]: [] for m in MEASURES},
                        "post": {m[0]: [] for m in MEASURES},
                    }
                r[win + "_grp"].add(grp)
                for name, inum, idens, _ in MEASURES:
                    den = sum(float(p[i]) for i in idens)
                    if den > 0:
                        v = float(p[inum]) / den
                        if v > 0:
                            r[win][name].append(math.log(v))
    return rec, files, probe


def deltas(rec, grp_from, auth=None):
    """One Delta per (ctr, sym). grp_from picks the window the label is read from."""
    out = {m[0]: {} for m in MEASURES}
    skipped = {}

    def bump(k):
        skipped[k] = skipped.get(k, 0) + 1

    for (ctr, sym), r in rec.items():
        if auth is not None:
            grp = auth.get(sym)
            if grp is None:
                bump("not on the external list")
                continue
        else:
            tags = r[grp_from + "_grp"]
            if not tags:
                bump("no %s-window label" % ("pre" if grp_from == "pre" else "post"))
                continue
            if len(tags) != 1:
                bump("group not unique")
                continue
            grp = next(iter(tags))
        if grp not in GROUPS:
            continue
        for name in out:
            a, b = r["pre"][name], r["post"][name]
            if len(a) < MIN_DAYS or len(b) < MIN_DAYS:
                if name == MEASURES[0][0]:
                    bump("too few days")
                continue
            out[name].setdefault((ctr, grp), []).append(median(b) - median(a))
    return out, skipped


# ------------------------------------------------------------------------ gate

def gate(d, sign):
    """The six inequalities. sign=+1 wants G>C, sign=-1 wants G<C."""
    ctrs = sorted({c for name in d for (c, g) in d[name]})
    res = {}
    for name, _, _, desc in MEASURES:
        tab, ineq = {}, []
        for ctr in ctrs:
            base = median(d[name].get((ctr, "C"), []))
            for grp in GROUPS:
                xs = d[name].get((ctr, grp), [])
                tab[ctr + "/" + grp] = {"n": len(xs), "delta": median(xs)}
            for grp in ["G1", "G2", "G3"]:
                m = median(d[name].get((ctr, grp), []))
                margin = None if (m is None or base is None) else sign * (m - base)
                ineq.append({"ctr": ctr, "grp": grp,
                             "holds": bool(margin is not None and margin > 0),
                             "margin": margin,
                             "raw_gap": None if (m is None or base is None) else m - base})
        res[name] = {"desc": desc, "table": tab, "inequalities": ineq,
                     "all_hold": all(x["holds"] for x in ineq) and len(ineq) == 6}
    return res, ctrs


def show(res, ctrs, sign):
    want = "G above C" if sign > 0 else "G below C"
    for name, _, _, desc in MEASURES:
        r = res[name]
        print("== %s (%s) ==" % (name, desc))
        print("  %-6s %-4s %8s %11s %13s"
              % ("venue", "grp", "symbols", "med Delta", "vs C"))
        for ctr in ctrs:
            for grp in GROUPS:
                c = r["table"][ctr + "/" + grp]
                gap = None
                if grp != "C":
                    base = r["table"][ctr + "/C"]["delta"]
                    if c["delta"] is not None and base is not None:
                        gap = c["delta"] - base
                print("  %-6s %-4s %8d %11s %13s"
                      % (ctr, grp, c["n"],
                         "None" if c["delta"] is None else "%+.6f" % c["delta"],
                         "" if gap is None else "%+.6f" % gap))
        n = sum(1 for x in r["inequalities"] if x["holds"])
        print("  six (wants %s): %d/6 hold  ->  %s\n"
              % (want, n, "PASS" if r["all_hold"] else "FAIL"))


def reproduction_check(res):
    """The six primary margins from the 2016 windows must reproduce the record."""
    if not os.path.exists(GATE0):
        return {"checked": 0, "identical": False,
                "why": "results/b14_gate0.json is not on disk"}
    prev = json.load(open(GATE0))
    old = {(x["ctr"], x["grp"]): x["margin"]
           for x in prev["measures"]["bbo_shr"]["inequalities"]}
    new = {(x["ctr"], x["grp"]): x["margin"]
           for x in res["bbo_shr"]["inequalities"]}
    both = [k for k in new if k in old and old[k] is not None and new[k] is not None]
    diffs = [{"cell": k[0] + "/" + k[1], "was": old[k], "now": new[k]}
             for k in both if abs(old[k] - new[k]) > 0]
    return {"checked": len(both), "identical": (not diffs and len(both) == 6),
            "diffs": diffs}


def census():
    """B14_A1 clause 3, step zero: symbol counts per month per group.

    Structure only; not one spread is compared here.
    """
    tab, dates = {}, {}
    files = sorted(f for f in os.listdir(CACHE)
                   if f.startswith("panel_v2_") and f.endswith(".csv"))
    for fn in files:
        with open(os.path.join(CACHE, fn)) as fh:
            fh.readline()
            for line in fh:
                if line.startswith("#"):
                    continue
                p = line.split(",", 4)
                ym, ctr, sym, grp = p[0][:6], p[1], canon(p[2]), p[3]
                tab.setdefault((ym, ctr), {}).setdefault(grp, set()).add(sym)
                dates.setdefault((ym, ctr), set()).add(p[0])
    print("symbol counts per month per group (design file B14_A1 clause 3, step 2)")
    print("  %-7s %-5s %6s %7s %7s %7s %7s"
          % ("month", "venue", "days", "C", "G1", "G2", "G3"))
    for key in sorted(tab):
        ym, ctr = key
        row = tab[key]
        print("  %-7s %-5s %6d %7s %7s %7s %7s"
              % (ym, ctr, len(dates[key]),
                 *[(len(row[g]) if g in row else "—") for g in GROUPS]))
    print("\nHow to read this, fixed before the run:")
    print("In the 2016 pre window and the 2018 post window the treated groups must\n"
          "be empty; in the 2016 post window and the 2018 pre window all four groups\n"
          "must be present. That is the premise of D3-9' and D3-9\".")
    print("If the treated groups are NOT empty in the 2018 post window, the premise\n"
          "of D3-9\" fails: stop, rewrite the clause, and do not run the gate.")
    return 0


def need_months(cfg):
    """Which cache files this round needs: every month the two windows touch,
    times the two venues.
    """
    ym = set()
    for a, b in (cfg["pre"], cfg["post"]):
        y, m = int(a[:4]), int(a[4:6])
        while "%04d%02d" % (y, m) <= b[:6]:
            ym.add("%04d%02d" % (y, m))
            m += 1
            if m > 12:
                y, m = y + 1, 1
    return {"panel_v2_%s_%s.csv" % (v, s) for v in ("NYSE", "NYSEARCA") for s in ym}


def run(which):
    print("=" * 74)
    print("step one: reproduction check (replay the 2016 windows under D3-9';\n"
          "must reproduce b14_gate0.json digit for digit)")
    print("=" * 74)
    cfg = ROUNDS["2016"]
    rec, files, probe = load(cfg["pre"], cfg["post"])
    print("read %d cache files, %d (venue, symbol) pairs" % (len(files), len(rec)))
    d, sk = deltas(rec, cfg["grp_from"])
    res16, ctrs16 = gate(d, cfg["sign"])
    rep = reproduction_check(res16)
    for x in res16["bbo_shr"]["inequalities"]:
        print("  %s/%-3s  margin %+.6f" % (x["ctr"], x["grp"], x["margin"]))
    if rep["identical"]:
        print("\n  reproduction check passed: 6 primary margins identical to the "
              "record, digit for digit.\n")
    else:
        print("\n  **reproduction check FAILED** (%d compared, %d differ)"
              % (rep["checked"], len(rep.get("diffs", []))))
        for x in rep.get("diffs", []):
            print("    %s  %r -> %r" % (x["cell"], x["was"], x["now"]))
        print("  By design file B14_A1 clause 8 this is a code error and every leg A\n"
              "  reading is void. Stopping here.")
        return 1

    print("=" * 74)
    print("step two: the leg A gate (%s)" % ROUNDS[which]["why"])
    print("=" * 74)
    cfg = ROUNDS[which]

    # A gate in front: if this round's cache is not on disk, stop and write nothing.
    # What it prevents is reading "the data has not arrived" as a FAIL. The last row
    # of the outcome map (B14_A1 clause 5) already rules that an empty treated group is a
    # defect in how groups were taken and not a reading; this moves that ruling to
    # before the run instead of after it.
    need = need_months(cfg)
    have = {f for f in os.listdir(CACHE)
            if f.startswith("panel_v2_") and f.endswith(".csv")}
    miss = sorted(n for n in need if n not in have)
    if miss:
        print("\n  **%d cache files for this round are missing; stopping, "
              "writing nothing.**" % len(miss))
        for n in miss:
            print("    " + n)
        print("\n  fetch: python experiments/b14_fetch_2018.py --fetch")
        print("  build: python experiments/b14_tickpilot_panel.py --build")
        return 2
    rec, files, probe = load(cfg["pre"], cfg["post"])
    print("read %d cache files, %d (venue, symbol) pairs" % (len(files), len(rec)))
    if cfg["asof"]:
        print("B14_A1 clause 1 weekend check: %d rows dated 2018-09-29/30 (must be 0)"
              % probe)
        if probe:
            print("  **Not zero. Either the calendar is wrong or the pre-window bound\n"
                  "  is wrong. Stopping here.**")
            return 1

    out = {"round": which, "pre": cfg["pre"], "post": cfg["post"],
           "grp_from": cfg["grp_from"], "sign": cfg["sign"],
           "min_days": MIN_DAYS, "reproduction_check": rep,
           "weekend_probe_rows": probe, "sources": {}}

    srcs = [("D3-9\" primary, pre-window inference", None, cfg["grp_from"])]
    if cfg["asof"]:
        srcs.append(("check 1, FINRA authoritative list",
                     G.load_authoritative(), None))
        rp, stats = grp_replay(cfg["asof"])
        print("\ncheck 2: change history replayed to %s -> %s"
              % (cfg["asof"], ", ".join("%s %d" % kv for kv in stats.items())))
        srcs.append(("check 2, change-history replay", rp, None))
        out["replay_stats"] = stats

    verdicts = {}
    for label, auth, gf in srcs:
        print("\n" + "-" * 74)
        print("group assignment from: %s" % label)
        print("-" * 74)
        d, sk = deltas(rec, gf or cfg["grp_from"], auth)
        print("dropped: " + ", ".join("%s %d" % kv for kv in sorted(sk.items())
                                      if kv[1]) + "\n")
        res, ctrs = gate(d, cfg["sign"])
        show(res, ctrs, cfg["sign"])
        verdicts[label] = {m: res[m]["all_hold"] for m in res}
        out["sources"][label] = {"skipped": sk, "measures": res}

    primary = MEASURES[0][0]
    main = out["sources"][srcs[0][0]]["measures"]
    ok = main[primary]["all_hold"]
    out["verdict"] = {
        "gate": "leg A",
        "primary": primary,
        "result": "PASS" if ok else "FAIL",
        "per_measure": {m: main[m]["all_hold"] for m in main},
        "per_source": verdicts,
        "sources_agree": len({tuple(sorted(v.items())) for v in verdicts.values()}) == 1,
        "failing": [x["ctr"] + "/" + x["grp"]
                    for x in main[primary]["inequalities"] if not x["holds"]],
    }
    print("=" * 74)
    print("verdict (design file section 7 supplement 2, B14_A1 clause 4)")
    print("  leg A gate = %s (primary convention %s, direction %s)"
          % (out["verdict"]["result"], primary,
             "G > C" if cfg["sign"] > 0 else "G < C"))
    if out["verdict"]["failing"]:
        print("  did not reverse: " + ", ".join(out["verdict"]["failing"]))
        print("  The reading for this cell is in the outcome map, B14_A1 clause 5,\n"
              "  fixed before the run row by row.")
    print("  the three group sources agree: %s"
          % ("yes" if out["verdict"]["sources_agree"] else "no"))
    print("  five parallel quantities: " + ", ".join(
        "%s %s" % (m, "PASS" if main[m]["all_hold"] else "FAIL") for m in main))

    out["stage"] = "B14"
    out["diagnostic_only"] = True
    out["diagnostic_reason"] = (
        "B14 stage two remains locked (design file section 7); this out-of-sample "
        "leg is registered in section 7 supplement 2 clause A and its reading is "
        "fixed in supplement 2 B14_A1 clause 5, so the record is evidence and not a "
        "licensed reading until the station closes")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, sort_keys=True, default=list)
        fh.write("\n")
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("the conventions are not copied: MEASURES is the same object as in "
        "b14_gate0", MEASURES is G.MEASURES)
    chk("canon is the same function as in b14_gate0, so the two rounds key "
        "tickers identically", canon is G.canon)
    chk("median is the same function as in b14_gate0", median is G.median)
    chk("MIN_DAYS matches b14_gate0", MIN_DAYS == G.MIN_DAYS == 10)
    chk("the 2016 windows are identical to b14_gate0",
        ROUNDS["2016"]["pre"] == G.PRE and ROUNDS["2016"]["post"] == G.POST)
    chk("the 2016 group source matches b14_gate0 GRP_FROM",
        ROUNDS["2016"]["grp_from"] == G.GRP_FROM == "post")
    chk("the 2018 round reads groups from the pre window (D3-9\", the mirror of "
        "D3-9')",
        ROUNDS["2018"]["grp_from"] == "pre")
    chk("the two rounds predict opposite directions",
        ROUNDS["2016"]["sign"] * ROUNDS["2018"]["sign"] == -1)
    chk("the 2018 pre window ends on the pilot termination date, 09-28",
        ROUNDS["2018"]["pre"] == ("20180801", "20180928"))
    chk("the 2018 post window starts 11-01, all of October dropped",
        ROUNDS["2018"]["post"] == ("20181101", "20181231")
        and ROUNDS["2018"]["pre"][1] < "20181001")

    # Gate direction: on one and the same set of numbers, flipping sign must flip
    # the conclusion.
    d = {m[0]: {("N", "C"): [0.10] * 5, ("N", "G1"): [0.50] * 5,
                ("N", "G2"): [0.40] * 5, ("N", "G3"): [0.45] * 5} for m in MEASURES}
    up, _ = gate(d, +1)
    dn, _ = gate(d, -1)
    chk("numbers with G above C: sign=+1 gives three holds", sum(
        1 for x in up[MEASURES[0][0]]["inequalities"] if x["holds"]) == 3)
    chk("the same numbers with sign=-1 give zero holds, so the gate really does "
        "read direction", sum(
        1 for x in dn[MEASURES[0][0]]["inequalities"] if x["holds"]) == 0)
    chk("raw_gap is independent of sign and margin is not",
        up[MEASURES[0][0]]["inequalities"][0]["raw_gap"]
        == dn[MEASURES[0][0]]["inequalities"][0]["raw_gap"]
        and up[MEASURES[0][0]]["inequalities"][0]["margin"]
        == -dn[MEASURES[0][0]]["inequalities"][0]["margin"])
    chk("all_hold is false when the six are not complete (one venue only)",
        up[MEASURES[0][0]]["all_hold"] is False)

    # Group source in deltas
    def mk(pre_tags, post_tags, n=20):
        return {"pre_grp": set(pre_tags), "post_grp": set(post_tags),
                "pre": {m[0]: [0.0] * n for m in MEASURES},
                "post": {m[0]: [0.0] * n for m in MEASURES}}

    rec = {("N", "AAA"): mk(["G1"], ["C"]), ("N", "BBB"): mk(["C"], ["C"])}
    dp, _ = deltas(rec, "pre")
    chk("pre-window inference reads AAA as G1, since by the post window it is "
        "back on C",
        set(dp[MEASURES[0][0]]) == {("N", "G1"), ("N", "C")})
    dq, _ = deltas(rec, "post")
    chk("post-window inference reads both as C on the same input, which is exactly "
        "the trap that carrying D3-9' over to 2018 would fall into",
        set(dq[MEASURES[0][0]]) == {("N", "C")})
    rec2 = {("N", "AAA"): mk(["C", "G1"], ["C"])}
    _, sk2 = deltas(rec2, "pre")
    chk("a symbol with a non-unique pre-window label is dropped and counted",
        sk2.get("group not unique") == 1)
    _, sk3 = deltas({("N", "AAA"): mk([], ["C"])}, "pre")
    chk("a symbol with no pre-window label is dropped and counted",
        sk3.get("no pre-window label") == 1)

    chk("the weekend probe watches 09-29 to 09-30",
        WEEKEND_PROBE == ("20180929", "20180930"))
    n16, n18 = need_months(ROUNDS["2016"]), need_months(ROUNDS["2018"])
    chk("the 2016 round needs eight cache files (two pre months plus two post "
        "months, times two venues)", len(n16) == 8)
    chk("the 2018 round needs eight cache files", len(n18) == 8)
    chk("the two rounds share no cache file", not (n16 & n18))
    chk("neither 2016-10 nor 2018-10 is needed (both phase months dropped whole)",
        not any("201610" in x or "201810" in x for x in n16 | n18))
    chk("the eight months the 2018 round reads are the four non-phase months",
        {x.split("_")[-1][:6] for x in n18} == {"201808", "201809", "201811", "201812"})
    chk("and the fetch takes a superset of them, October included, because a month "
        "the windows drop still belongs on disk",
        {x.split("_")[-1][:6] for x in n18}
        < {"201808", "201809", "201810", "201811", "201812"})
    chk("the change-history file is on disk", os.path.exists(CHANGES))
    if os.path.exists(CHANGES):
        rp, st = grp_replay("20180928")
        chk("the replay yields four groups and only four",
            set(rp.values()) == set(GROUPS))
        chk("the replayed list is no larger than the baseline; it can only shrink",
            st["after replay"] <= st["baseline"] + st["valid at as-of"])
        chk("the replay actually uses the change history",
            st["valid at as-of"] > 0)
        r0, _ = grp_replay("20160901")
        chk("replaying to before and after the pilot start gives different lists, "
            "so the replay is not a no-op", r0 != rp)
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--repro", action="store_true",
                    help="reproduction check only, on the 2016 cache already on disk; "
                         "does not touch 2018 and writes no record")
    ap.add_argument("--round", default="2018", choices=sorted(ROUNDS))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.census:
        return census()
    if a.repro:
        cfg = ROUNDS["2016"]
        rec, files, _ = load(cfg["pre"], cfg["post"])
        print("read %d cache files, %d (venue, symbol) pairs" % (len(files), len(rec)))
        d, sk = deltas(rec, cfg["grp_from"])
        print("dropped: " + ", ".join("%s %d" % kv for kv in sorted(sk.items())
                                      if kv[1]))
        res, ctrs = gate(d, cfg["sign"])
        show(res, ctrs, cfg["sign"])
        rep = reproduction_check(res)
        for x in res["bbo_shr"]["inequalities"]:
            print("  %s/%-3s  margin %+.6f" % (x["ctr"], x["grp"], x["margin"]))
        print("\nreproduction check: %d compared, %s"
              % (rep["checked"],
                 "identical digit for digit" if rep["identical"]
                 else "**%d differ**" % len(rep.get("diffs", []))))
        for x in rep.get("diffs", []):
            print("  %s  %r -> %r" % (x["cell"], x["was"], x["now"]))
        return 0 if rep["identical"] else 1
    if a.run:
        return run(a.round)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
