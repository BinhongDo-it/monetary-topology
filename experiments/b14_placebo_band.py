"""B14: the noise scale of leg A's statistic, measured where nothing happened.

Leg A read six inequalities on the pilot's termination and three of them came out
negative by margins between 0.002 and 0.065. Nothing in that design says whether
0.002 is small. This script measures that, by running the identical machine on
window pairs that sit wholly inside the pilot, where the treatment does not change
and the true gap is therefore zero by construction.

WHY THE CONTROL GROUP'S OWN DELTA IS THE HEADLINE HERE

Leg A's record carries one number that decides how it should be read: on venue N
the control group's own spread widened by 0.2766 between the two windows. The
control had nothing done to it. A difference-in-differences asked to recover a
0.099 gap out of a 0.277 common move is subtracting noise from noise, and no
amount of care in the inequality fixes that. So this script reports the control
delta for every block alongside the gaps, and the comparison that matters is
where 0.2766 falls in that distribution.

THE BLOCKS

Frozen here rather than generated, so that the list is auditable and cannot drift:
eighteen five-month blocks, each shaped exactly like leg A (two months of pre, one
month dropped, two months of post), every one of them wholly inside the pilot.

The pilot phased in through October 2016 and ended at the close on 2018-09-28, so
the clean in-pilot span is 201611 through 201808 and the eighteen blocks exhaust
it. Block ten is the calendar twin: August-September against November-December,
the same months as leg A with the treatment held fixed throughout.

Each pre window ends on the 28th of its second month, because leg A's pre window
ends on 2018-09-28. A twin that used full months would not be a twin.

WHAT THIS SCRIPT DOES NOT DO

No pass, no fail, no threshold. The eighteen blocks overlap: they are eighteen
windows on one panel, not eighteen samples, and the largest non-overlapping subset
has three members. A count over overlapping windows reports consistency and is not
a sample size. The output is the distribution and the objects behind it.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate0 as G          # noqa: E402  the conventions of record
import b14_gate_exit as X      # noqa: E402  load / deltas / gate, reused not copied
import b14_gate_exit_pre804 as R  # noqa: E402  the 201803 population, imported not copied

OUT = os.path.join(ROOT, "results", "b14_placebo_band.json")

#: (pre_month_1, pre_month_2, dropped, post_month_1, post_month_2)
BLOCKS = [
    ("201611", "201612", "201701", "201702", "201703"),
    ("201612", "201701", "201702", "201703", "201704"),
    ("201701", "201702", "201703", "201704", "201705"),
    ("201702", "201703", "201704", "201705", "201706"),
    ("201703", "201704", "201705", "201706", "201707"),
    ("201704", "201705", "201706", "201707", "201708"),
    ("201705", "201706", "201707", "201708", "201709"),
    ("201706", "201707", "201708", "201709", "201710"),
    ("201707", "201708", "201709", "201710", "201711"),
    ("201708", "201709", "201710", "201711", "201712"),   # the calendar twin
    ("201709", "201710", "201711", "201712", "201801"),
    ("201710", "201711", "201712", "201801", "201802"),
    ("201711", "201712", "201801", "201802", "201803"),
    ("201712", "201801", "201802", "201803", "201804"),
    ("201801", "201802", "201803", "201804", "201805"),
    ("201802", "201803", "201804", "201805", "201806"),
    ("201803", "201804", "201805", "201806", "201807"),
    ("201804", "201805", "201806", "201807", "201808"),
]
TWIN = 9
#: The largest non-overlapping subset, by index. Three, and the twin is one of them.
INDEPENDENT = (4, 9, 14)

#: Leg A's readings, for the comparison this script exists to make. Copied from
#: results/b14_gate_exit.json rather than recomputed, and checked against it in
#: the selftest so the two cannot drift.
LEG_A_CONTROL_DELTA = {"N": 0.276622, "P": -0.031572}


def windows(b):
    """pre ends on the 28th of its second month; post is two whole months.

    The 28th is not a convenience: leg A's pre window ends on 2018-09-28 because
    that is when the pilot ended, and a twin that ran to month end would not be
    one. The post end is the real last day of the month rather than a blanket 31,
    which as an upper bound would behave identically and would also put dates that
    do not exist into a file that is supposed to be frozen and read by people.
    """
    import calendar
    y, m = int(b[4][:4]), int(b[4][4:])
    last = calendar.monthrange(y, m)[1]
    return (b[0] + "01", b[1] + "28"), (b[3] + "01", "%s%02d" % (b[4], last))


def one(b, shape="5m", keep=None):
    """One block. ``keep``, when given, restricts both venues to that symbol set.

    The filter goes in at the same place the exit round's restricted version
    puts it, between load and deltas, so that the two are the same operation on
    the same object and a band measured here transfers to a gap measured there.
    ``keep=None`` leaves the call identical to what it was before the argument
    existed, which is what the default reproduction check in the selftest reads.
    """
    pre, post = windows(b) if shape == "5m" else windows_1m(b)
    rec, files, probe = X.load(pre, post)
    if keep is not None:
        rec = {k: v for k, v in rec.items() if k[1] in keep}
    d, sk = X.deltas(rec, "pre")
    res, ctrs = X.gate(d, +1)          # sign is inert here; raw_gap is what is read
    out = {"block": list(b), "pre": pre, "post": post, "files": len(files),
           "measures": {}}
    for name in res:
        tab = res[name]["table"]
        out["measures"][name] = {
            "desc": res[name]["desc"],
            "control_delta": {c: tab[c + "/C"]["delta"] for c in ctrs},
            "control_n": {c: tab[c + "/C"]["n"] for c in ctrs},
            "gaps": {"%s/%s" % (x["ctr"], x["grp"]): x["raw_gap"]
                     for x in res[name]["inequalities"]},
        }
    return out


# --------------------------------------------------------------------------
# The one-month shape, for reading the October post window.
#
# Leg A dropped October 2018 in order to mirror the 2016 round, which dropped
# October 2016 because the pilot phased in across that month in waves. The 2018
# end has no such property: the quoting and trading requirements ended for every
# test group at one moment, the close on 2018-09-28, and every pilot security
# opened in the control group on October 1. Mirroring the calendar shape carried
# the drop across without carrying its reason.
#
# October is therefore readable, and on the control group's own delta it is the
# only readable post window anchored on this event. But its shape is not the
# five-month shape: two months of pre, no month dropped, one month of post. The
# band above was measured on two-month post windows and does not apply to it; a
# one-month window carries more sampling noise, and reading one against the other
# would put the criterion and the object in different scopes.
#
# So: the same construction again, at the shape the October reading actually has.

BLOCKS_1M = [
    ("201611", "201612", "201701"),
    ("201612", "201701", "201702"),
    ("201701", "201702", "201703"),
    ("201702", "201703", "201704"),
    ("201703", "201704", "201705"),
    ("201704", "201705", "201706"),
    ("201705", "201706", "201707"),
    ("201706", "201707", "201708"),
    ("201707", "201708", "201709"),
    ("201708", "201709", "201710"),
    ("201709", "201710", "201711"),
    ("201710", "201711", "201712"),
    ("201711", "201712", "201801"),
    ("201712", "201801", "201802"),
    ("201801", "201802", "201803"),
    ("201802", "201803", "201804"),
    ("201803", "201804", "201805"),
    ("201804", "201805", "201806"),
    ("201805", "201806", "201807"),
    ("201806", "201807", "201808"),
]
TWIN_1M = 9
INDEPENDENT_1M = (0, 3, 6, 9, 12, 15, 18)


def windows_1m(b):
    """Two months of pre ending on the 28th, then one whole month of post."""
    import calendar
    y, m = int(b[2][:4]), int(b[2][4:])
    last = calendar.monthrange(y, m)[1]
    return (b[0] + "01", b[1] + "28"), (b[2] + "01", "%s%02d" % (b[2], last))


def src_of_module():
    """This file's own source, for the scoped AST check in the selftest."""
    return open(os.path.abspath(__file__), encoding="utf-8").read()


def selftest():
    bad = []

    def chk(msg, ok):
        print("  %-4s %s" % ("ok" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    chk("eighteen blocks, every one five months long",
        len(BLOCKS) == 18 and all(len(b) == 5 for b in BLOCKS))
    months = [m for b in BLOCKS for m in b]
    chk("every month is inside the clean in-pilot span 201611..201808",
        all("201611" <= m <= "201808" for m in months))
    chk("the blocks are consecutive months",
        all(all(b[i] < b[i + 1] for i in range(4)) for b in BLOCKS))
    chk("block ten is the calendar twin of leg A: Aug-Sep, drop Oct, Nov-Dec",
        BLOCKS[TWIN][0][4:] == "08" and BLOCKS[TWIN][2][4:] == "10"
        and BLOCKS[TWIN][4][4:] == "12")
    pre, post = windows(BLOCKS[TWIN])
    chk("the twin's pre window ends on the 28th, as leg A's does",
        pre[1].endswith("28") and X.ROUNDS["2018"]["pre"][1].endswith("28"))
    import datetime
    ends = [e for b in BLOCKS for w in windows(b) for e in w]
    real = []
    for e in ends:
        try:
            datetime.date(int(e[:4]), int(e[4:6]), int(e[6:]))
        except ValueError:
            real.append(e)
    chk("every window endpoint is a date that exists: %s" % (real or "all real"),
        not real)
    chk("the independent subset really does not overlap",
        all(set(BLOCKS[INDEPENDENT[i]]).isdisjoint(BLOCKS[INDEPENDENT[i + 1]])
            for i in range(len(INDEPENDENT) - 1)))
    chk("the machine is imported, not copied: gate and deltas come from gate_exit",
        X.gate.__module__ == "b14_gate_exit" and X.deltas.__module__ == "b14_gate_exit")
    chk("the measures are gate0's, so the placebo and leg A cannot diverge",
        X.MEASURES is G.MEASURES and X.MIN_DAYS == G.MIN_DAYS)
    # Scoped AST walk rather than a substring search. A substring search for the
    # banned names finds the search itself, which is how this check failed the
    # first time it was run: the guard was its own counterexample. The walk skips
    # the subtree of this function so that naming what is banned is not a breach
    # of the ban, and it reads string constants and attribute names rather than
    # source text so that a comment cannot trip it either.
    import ast
    tree = ast.parse(src_of_module())
    banned = {"all_hold", "passed"}
    hits = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "selftest":
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value in banned:
                hits.append(sub.value)
            elif isinstance(sub, ast.Attribute) and sub.attr in banned:
                hits.append(sub.attr)
    chk("outside this function the module names no verdict field (AST walk): %s"
        % (sorted(set(hits)) or "none"), not hits)
    chk("the population is imported from the restricted exit round, not copied",
        R.population.__module__ == "b14_gate_exit_pre804")
    pop = R.population()
    chk("that population is the 201803 venue-N file, %d symbols" % len(pop),
        len(pop) == 618)
    # Rule 19: the new switch off must be the old code. Checked by running one
    # block and comparing against the copy of it already on disk, rather than by
    # reading the source and reasoning about it.
    #
    # The "files" field is excluded, and the exclusion is the finding rather than
    # a convenience. X.load lists the whole cache and filters by date, so that
    # field counts what was in the cache when the block ran, not what the block
    # read. It went 66 to 72 when three more months were built for the October
    # re-read, months that end after every one of these blocks does, and not one
    # reading moved. A per-run number in a checked file is what the write
    # discipline's sixth clause forbids; it is left in place because nothing here
    # is deleted, and it is named here so the next reader does not read it as a
    # property of the block.
    bp = os.path.join(ROOT, "results", "b14_placebo_band.json")
    if os.path.exists(bp):
        prev = json.load(open(bp, encoding="utf-8"))
        have = {b["index"]: b for b in prev.get("blocks", [])}
        i = TWIN if TWIN in have else (sorted(have)[0] if have else None)
        if i is None:
            chk("a block is on disk to reproduce", False)
        else:
            now = one(BLOCKS[i], "5m")
            now["index"] = i
            a = {k: v for k, v in now.items() if k != "files"}
            b = {k: v for k, v in have[i].items() if k != "files"}
            chk("default reproduces block %d on disk to the byte, files aside "
                "(cache %d then, %d now)" % (i, have[i].get("files", -1), now["files"]),
                json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))
    else:
        chk("the full-population band is on disk to reproduce against", False)
    p = os.path.join(ROOT, "results", "b14_gate_exit.json")
    if os.path.exists(p):
        rec = json.load(open(p, encoding="utf-8"))
        tab = rec["sources"]['D3-9" primary, pre-window inference']["measures"]["bbo_shr"]["table"]
        chk("leg A's control deltas match the record they were copied from",
            all(abs(tab[c + "/C"]["delta"] - v) < 5e-7
                for c, v in LEG_A_CONTROL_DELTA.items()))
    else:
        chk("leg A's record is on disk to check against", False)
    print("\nselftest: %s" % ("PASS" if not bad else "FAIL (%d)" % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--blocks", action="store_true", help="print the frozen blocks only")
    ap.add_argument("--shape", choices=("5m", "1m"), default="5m")
    ap.add_argument("--pop", choices=("full", "pre804"), default="full",
                    help="pre804 restricts both venues to the 201803 venue-N "
                         "symbol set, matching b14_gate_exit_pre804")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", type=int, default=None, help="run one block by index")
    ap.add_argument("--from", dest="lo", type=int, default=0)
    ap.add_argument("--to", dest="hi", type=int, default=len(BLOCKS) - 1)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.blocks:
        bl = BLOCKS if a.shape == "5m" else BLOCKS_1M
        tw = TWIN if a.shape == "5m" else TWIN_1M
        iset = INDEPENDENT if a.shape == "5m" else INDEPENDENT_1M
        for i, b in enumerate(bl):
            pre, post = (windows(b) if a.shape == "5m" else windows_1m(b))
            print("  %2d  %s..%s -> %s..%s%s%s"
                  % (i, pre[0], pre[1], post[0], post[1],
                     "   TWIN" if i == tw else "",
                     "   independent" if i in iset else ""))
        return 0
    if a.run:
        blocks = BLOCKS if a.shape == "5m" else BLOCKS_1M
        twin = TWIN if a.shape == "5m" else TWIN_1M
        ind = INDEPENDENT if a.shape == "5m" else INDEPENDENT_1M
        out_path = OUT if a.shape == "5m" else OUT.replace(".json", "_1m.json")
        keep = None
        if a.pop == "pre804":
            keep = R.population()
            out_path = out_path.replace(".json", "_pre804.json")
            print("  population: %d symbols from panel_v2_NYSE_201803.csv\n"
                  % len(keep))
        hi = a.hi if a.hi != len(BLOCKS) - 1 else len(blocks) - 1
        idx = [a.only] if a.only is not None else range(a.lo, hi + 1)
        out = {"stage": "B14", "diagnostic_only": True,
               "diagnostic_reason":
                   "the noise scale for leg A's statistic, measured on window pairs "
                   "wholly inside the pilot where the true gap is zero by "
                   "construction; B14 stage two is still locked, and these blocks "
                   "overlap so their count is consistency and not a sample size"
                   + ("" if a.pop == "full" else
                      ". Both venues are restricted to the 201803 venue-N symbol "
                      "set, so that this band and the restricted exit round stand "
                      "on the same population"),
               "shape": a.shape, "population": a.pop,
               "independent_subset": list(ind), "twin": twin,
               "leg_a_control_delta": LEG_A_CONTROL_DELTA, "blocks": []}
        for i in idx:
            r = one(blocks[i], a.shape, keep)
            r["index"] = i
            out["blocks"].append(r)
            cd = r["measures"]["bbo_shr"]["control_delta"]
            print("  %2d  %s..%s -> %s..%s   control delta  %s"
                  % (i, r["pre"][0], r["pre"][1], r["post"][0], r["post"][1],
                     "  ".join("%s %+0.4f" % (k, v) for k, v in sorted(cd.items()))))
        # Merge on write, keyed by block index, rather than replace. A partial run
        # that replaced the file would erase the blocks it did not run, which is
        # the failure this repository has already paid for once: a verdict writer
        # that overwrote instead of merging silently dropped two arms of a
        # sensitivity sweep. Merging also makes the run resumable, which matters
        # because the whole sweep does not fit in one go here.
        merged = {}
        if os.path.exists(out_path):
            prev = json.load(open(out_path, encoding="utf-8"))
            for b in prev.get("blocks", []):
                merged[b["index"]] = b
        for b in out["blocks"]:
            merged[b["index"]] = b
        out["blocks"] = [merged[k] for k in sorted(merged)]
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=2, sort_keys=True)
        print("\n  wrote %s (%d of %d blocks on disk)"
              % (os.path.relpath(out_path, ROOT), len(out["blocks"]), len(blocks)))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
