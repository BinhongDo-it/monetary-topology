"""B14: order-type sensitivity, B14_A19.

Registered in the design file, section 7 supplement 2, B14_A19. The question only
became askable once T7's code table arrived: the primary measure is share
weighted and 45.69% of the share weight comes from order type 22, Away From
Market Orders, which by definition do not participate in the spread prevailing
at their own effective time. The specification says to include them, so the
convention is not wrong. It has simply never been tested.

Three variants, fixed by B14_A19 clause 1 and not extendable:

    X22      drop order type 22   Away From Market
    X16      drop order type 16   Retail Liquidity Providing
    X2216    drop both

Nothing here writes a new verdict rule. It rebuilds the panel cache with the
order types filtered out, points b14_gate0 and b14_gate_exit at that cache, and
runs THEIR adjudication code unchanged. The selftest asserts the verdict
functions are the imported ones rather than copies.

The existing cache is never touched: each variant writes into its own directory.

Usage
    python experiments/b14_ordertype_sens.py --selftest
    python experiments/b14_ordertype_sens.py --build X22
    python experiments/b14_ordertype_sens.py --build X22 X16 X2216
    python experiments/b14_ordertype_sens.py --verdict X22
"""
import argparse
import ast
import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "b14_ordertype_sens.json")

#: B14_A19 clause 1. Exactly these three; clause 1 forbids a fourth.
VARIANTS = {"X22": {"22"}, "X16": {"16"}, "X2216": {"22", "16"}}
#: 0-based, from the field line: D | Date | Trdng_Cntr | Symbol | Test_Group | Order_Type
C_ORDTYPE = 5


def load_mod(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def variant_cache(tag):
    return os.path.join(ROOT, "data", "cache", "b14_" + tag.lower())


def build(tags):
    P = load_mod("b14_tickpilot_panel")
    base_stream = P.stream
    for tag in tags:
        drop = VARIANTS[tag]
        print("\n=== %s: dropping order type(s) %s ===" % (tag, " ".join(sorted(drop))))

        def filtered(path, _drop=drop):
            kept = dropped = 0
            for f in base_stream(path):
                if len(f) > C_ORDTYPE and f[C_ORDTYPE] in _drop:
                    dropped += 1
                    continue
                kept += 1
                yield f
            print("      kept %d rows, dropped %d (%.4f)"
                  % (kept, dropped, dropped / max(kept + dropped, 1)))

        P.stream = filtered
        P.CACHE = variant_cache(tag)
        os.makedirs(P.CACHE, exist_ok=True)
        names = sorted(f for f in os.listdir(P.RAW)
                       if f.endswith(".gzip") and "MKTQUALITYSTATS" in f)
        for fn in names:
            print("  %s" % fn)
            P.build_one(fn)
    P.stream = base_stream
    print("\n  next: python experiments/b14_ordertype_sens.py --verdict %s" % " ".join(tags))
    return 0


def run_verdict(tag):
    """Point the two gate modules at the variant cache and run THEIR own code.

    The entry points are named explicitly rather than probed for. b14_gate0.run()
    takes no arguments; b14_gate_exit.run(which) takes the round key, and both
    rounds are run because B14_A19 clause 2 asks about B14-0's six inequalities and
    about leg A's 3/6 separately. Each module also writes its own record file, so
    OUT is redirected per variant and the real records are not overwritten.
    """
    cache = (os.path.join(ROOT, "data", "cache", "b14") if tag == "FULL"
             else variant_cache(tag))
    if not os.path.isdir(cache) or not [f for f in os.listdir(cache)
                                        if f.startswith("panel_v2_")]:
        print("  %s: no cache at %s; run --build first" % (tag, cache))
        return None
    calls = [("b14_gate0", "B14-0, the 2016 round", lambda m: m.run()),
             ("b14_gate_exit", "leg A, 2016 round", lambda m: m.run("2016")),
             ("b14_gate_exit", "leg A, 2018 round", lambda m: m.run("2018"))]
    out = {}
    for name, label, call in calls:
        m = load_mod(name)
        m.CACHE = cache
        if hasattr(m, "OUT") and isinstance(m.OUT, str):
            m.OUT = m.OUT.replace(".json", ".sens_%s.json" % tag)
        # b14_gate_exit's step one replays the 2016 windows and demands they
        # reproduce b14_gate0's RECORD digit for digit. Under a variant that
        # record must be the variant's own, not the full-sample one: pointing it
        # at the full record makes the check compare two different populations
        # and report a code error that is not there. That is a check biting the
        # wrong object, the sixth time in this station, so it gets redirected
        # with the same care as OUT.
        if tag != "FULL" and hasattr(m, "GATE0") and isinstance(m.GATE0, str):
            m.GATE0 = m.GATE0.replace(".json", ".sens_%s.json" % tag)
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = call(m)
        except SystemExit as e:
            rc = e.code
        except Exception as e:
            rc = "ERROR: %s: %s" % (type(e).__name__, e)
        finally:
            sys.stdout = old
        text = buf.getvalue()
        out["%s | %s" % (name, label)] = {"rc": rc, "text": text}
        print("\n----- %s / %s -----" % (tag, label))
        print(text.rstrip() or "  (no output)")
        if isinstance(rc, str) and rc.startswith("ERROR"):
            print("  %s" % rc)
    return out


def verdict(tags):
    # Merge rather than overwrite. The first version wrote only the tags of the
    # current invocation, so running one variant silently erased the record of the
    # variant run before it, and B14_A19 clause 2's reading needs all three side by
    # side. Nothing is dropped: a tag rerun replaces only its own entry.
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for tag in ["FULL"] + list(tags):
        r = run_verdict(tag)
        if r is not None:
            res[tag] = {k: v["text"] for k, v in r.items()}
    json.dump(res, open(OUT, "w"), indent=2)
    have = [t for t in ("X22", "X16", "X2216") if t in res]
    print("\n  variants on record: %s" % (" ".join(have) or "none"))
    if len(have) < 3:
        print("  B14_A19 clause 1 fixes three variants; the reading is not in force")
        print("  until all three are on record. Missing: %s"
              % " ".join(t for t in ("X22", "X16", "X2216") if t not in res))
    print("\n  written %s" % os.path.relpath(OUT, ROOT))
    print("  B14_A19 clause 2: compare the six inequalities across FULL and each")
    print("  variant. Every measured number is printed; no threshold is set.")
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("exactly the three B14_A19 variants are defined",
        set(VARIANTS) == {"X22", "X16", "X2216"})
    chk("the variants are the two T7 anomalies and their union",
        VARIANTS["X2216"] == VARIANTS["X22"] | VARIANTS["X16"])
    P = load_mod("b14_tickpilot_panel")
    chk("the order type column is where the field line puts it, right after "
        "Test_Group", C_ORDTYPE == P.C_GRP + 1)
    chk("the panel module's own column map is unchanged by this file",
        (P.C_DATE, P.C_CTR, P.C_SYM, P.C_GRP) == (1, 2, 3, 4)
        and (P.C_NBBO, P.C_BBO) == (42, 43))
    chk("each variant writes to its own directory, none of them the real one",
        len({variant_cache(t) for t in VARIANTS}) == 3
        and os.path.join(ROOT, "data", "cache", "b14")
        not in {variant_cache(t) for t in VARIANTS})
    g0 = load_mod("b14_gate0")
    chk("gate zero's measures are its own and are not redefined here",
        hasattr(g0, "MEASURES") and g0.MEASURES[0][0] == "bbo_shr")
    ge = load_mod("b14_gate_exit")
    chk("the entry points are named, not probed for: gate zero's run takes no "
        "argument and gate exit's takes the round",
        g0.run.__code__.co_argcount == 0 and ge.run.__code__.co_argcount == 1)
    chk("both registered rounds exist in gate exit", set(ge.ROUNDS) == {"2016", "2018"})
    chk("the 2016 round predicts G above C and the 2018 round the reverse",
        ge.ROUNDS["2016"]["sign"] == 1 and ge.ROUNDS["2018"]["sign"] == -1)
    chk("each variant redirects the gate modules' own record files, so the real "
        "records are not overwritten", ".sens_" in src)
    chk("the results file is merged, not overwritten, so running one variant "
        "does not erase another", "res = json.load(open(OUT" in src)
    chk("the reproduction check is redirected too, so it compares a variant "
        "against its OWN gate zero record and not the full-sample one",
        "GATE0" in src and hasattr(ge, "GATE0"))
    chk("gate exit really does read a gate zero record, which is the thing that "
        "had to be redirected", os.path.basename(ge.GATE0) == "b14_gate0.json")
    chk("this file defines no verdict of its own: " +
        (", ".join(sorted({n.name for n in ast.walk(
            ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read()))
            if isinstance(n, ast.FunctionDef)} & {"median", "margin", "adjudicate"}))
         or "zero"),
        not ({n.name for n in ast.walk(ast.parse(
            open(os.path.abspath(__file__), encoding="utf-8").read()))
            if isinstance(n, ast.FunctionDef)} & {"median", "margin", "adjudicate"}))
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("shutil", "rmtree")}
    hits = [getattr(n, "lineno", "?") for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and (n.func.value.id, n.func.attr) in banned]
    chk("no deletion call anywhere: " +
        (("lines " + ", ".join(map(str, hits))) if hits else "zero"), not hits)
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--build", nargs="+", metavar="TAG")
    ap.add_argument("--verdict", nargs="+", metavar="TAG")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    for t in (a.build or []) + (a.verdict or []):
        if t not in VARIANTS:
            print("  %s is not one of the three B14_A19 variants; refused" % t)
            return 1
    if a.build:
        return build(a.build)
    if a.verdict:
        return verdict(a.verdict)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
