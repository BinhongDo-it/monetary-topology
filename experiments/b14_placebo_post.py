"""B14: does the in-pilot noise band transfer to windows outside the pilot?

The band in b14_placebo_band.py is measured on eighteen five-month and twenty
one-month blocks, every one of them wholly inside the pilot. The exit round's
windows are not inside the pilot. So the band is measured in one regime and
applied in another, which is the sixth category error: a criterion whose scope
does not meet its object's.

This script builds blocks on the other side of the event, where the true gap is
zero for a different reason. After the close on 2018-09-28 the quoting and trading
requirements ended for every test group and every pilot security opened in the
control condition on October 1, so a G-versus-C gap measured wholly after that date
has nothing generating it.

THE GROUP LABELS DO NOT COME FROM THE PANEL FILE HERE, AND CANNOT

The panel file's test_group column is the live condition, not the assignment: it
reads C for every row from 201810 on (46,668 / 42,283 / 38,144 rows, no other
value). Reading groups from the pre window, which is what both rounds do, would
put every security in the control group and return nothing. The labels therefore
come from the FINRA assignment file through b14_gate0.load_authoritative, the same
external list b14_gate0's authoritative arm already uses.

That substitution is the whole reason this is a separate script rather than a flag
on the band: the band's blocks read their labels from the data and these cannot.

WHAT IS AND IS NOT AVAILABLE

Blocks are discovered from the cache rather than frozen, because the cache is what
limits them. With months through 201812 there is exactly one block. It is a number
and not a distribution, and it is labelled as one below.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import b14_gate0 as G             # noqa: E402  the external assignment list
import b14_gate_exit as X         # noqa: E402  load / deltas / gate, reused not copied
import b14_gate_exit_pre804 as R  # noqa: E402  the 201803 population, imported not copied

OUT = os.path.join(ROOT, "results", "b14_placebo_post.json")
CELLS = ["N/G1", "N/G2", "N/G3", "P/G1", "P/G2", "P/G3"]
CONV = ["bbo_shr", "bbo_cnt", "bbo_shr_adv", "bbo_shr_adv2"]

#: The first month wholly after the pilot ended. September 2018 is excluded because
#: the pilot was live for all but its last trading day.
FIRST_POST = "201810"


def months():
    """Cache months from FIRST_POST on, present for both venues."""
    have = {}
    for f in os.listdir(X.CACHE):
        if f.startswith("panel_v2_") and f.endswith(".csv"):
            v, m = f[len("panel_v2_"):-4].rsplit("_", 1)
            have.setdefault(m, set()).add(v)
    return sorted(m for m, vs in have.items()
                  if m >= FIRST_POST and {"NYSE", "NYSEARCA"} <= vs)


def blocks_1m(ms):
    """Consecutive triples: two months of pre ending on the 28th, one of post."""
    return [tuple(ms[i:i + 3]) for i in range(len(ms) - 2)]


def windows_1m(b):
    import calendar
    last = calendar.monthrange(int(b[2][:4]), int(b[2][4:]))[1]
    return (b[0] + "01", b[1] + "28"), (b[2] + "01", "%s%02d" % (b[2], last))


def one(b, auth, keep):
    pre, post = windows_1m(b)
    rec, files, probe = X.load(pre, post)
    if keep is not None:
        rec = {k: v for k, v in rec.items() if k[1] in keep}
    d, sk = X.deltas(rec, "pre", auth=auth)
    res, ctrs = X.gate(d, -1)   # sign is inert; raw_gap is what is read
    out = {"block": list(b), "pre": pre, "post": post, "skipped": sk, "measures": {}}
    for name in res:
        tab = res[name]["table"]
        out["measures"][name] = {
            "control_delta": {c: tab[c + "/C"]["delta"] for c in ctrs},
            "control_n": {c: tab[c + "/C"]["n"] for c in ctrs},
            "gaps": {"%s/%s" % (x["ctr"], x["grp"]): x["raw_gap"]
                     for x in res[name]["inequalities"]},
        }
    return out


def selftest():
    bad = []

    def chk(msg, ok):
        print("  %-4s %s" % ("ok" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    ms = months()
    chk("cache months after the pilot: %s" % (ms or "none"), bool(ms))
    chk("every one of them starts on or after %s" % FIRST_POST,
        all(m >= FIRST_POST for m in ms))
    bl = blocks_1m(ms)
    chk("%d block(s), each three consecutive months" % len(bl),
        all(len(b) == 3 for b in bl))
    auth = G.load_authoritative()
    chk("the external assignment list loads, %d tickers" % len(auth), len(auth) > 1000)
    chk("it carries all three test groups",
        {"G1", "G2", "G3"} <= set(auth.values()))
    # The claim in the docstring, checked rather than asserted: the panel file's
    # own labels are useless here.
    seen = set()
    p = os.path.join(X.CACHE, "panel_v2_NYSE_%s.csv" % ms[-1]) if ms else None
    if p and os.path.exists(p):
        with open(p) as fh:
            fh.readline()
            for line in fh:
                if not line.startswith("#"):
                    seen.add(line.split(",")[3])
    chk("the panel file's own label column is control-only in %s: %s"
        % (ms[-1] if ms else "-", sorted(seen)), seen == {"C"})
    chk("the machine is imported, not copied",
        X.gate.__module__ == "b14_gate_exit"
        and R.population.__module__ == "b14_gate_exit_pre804")
    print("\nselftest: %s" % ("PASS" if not bad else "FAIL (%d)" % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--pop", choices=("full", "pre804"), default="pre804")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.run:
        ap.print_help()
        return 0
    ms = months()
    bl = blocks_1m(ms)
    auth = G.load_authoritative()
    keep = R.population() if a.pop == "pre804" else None
    print("months after the pilot: %s" % " ".join(ms))
    print("population: %s\n" % ("all" if keep is None else "%d symbols" % len(keep)))
    out = {"stage": "B14", "diagnostic_only": True,
           "diagnostic_reason":
               "the same statistic measured wholly after the pilot ended, where "
               "every security is in the control condition and the gap is zero by "
               "construction, to see whether the in-pilot band transfers to the "
               "regime the exit round's windows sit in. Group labels come from the "
               "external FINRA assignment file because the panel file's own column "
               "is control-only from 201810 on. B14 stage two is locked",
           "population": a.pop, "months": ms, "blocks": []}
    for b in bl:
        r = one(b, auth, keep)
        out["blocks"].append(r)
        m = r["measures"]["bbo_shr"]
        print("  %s..%s -> %s..%s" % (r["pre"][0], r["pre"][1], r["post"][0], r["post"][1]))
        print("    control delta  %s"
              % "  ".join("%s %+0.4f (n=%d)" % (k, v, m["control_n"][k])
                          for k, v in sorted(m["control_delta"].items())))
        for c in CELLS:
            g = [r["measures"][cv]["gaps"][c] for cv in CONV]
            print("    %-6s %s   |max| %.4f"
                  % (c, "  ".join("%+.4f" % v for v in g), max(abs(v) for v in g)))
        allg = [r["measures"][cv]["gaps"][c] for c in CELLS for cv in CONV]
        print("    largest |gap| anywhere in this block: %.4f\n" % max(abs(v) for v in allg))
    out_path = OUT if a.pop == "pre804" else OUT.replace(".json", "_full.json")
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print("  wrote %s (%d block(s))" % (os.path.relpath(out_path, ROOT), len(bl)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
