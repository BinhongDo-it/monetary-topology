"""B122: one input, two deduction ratios, and whether the square closes.

A value added tax writes two numbers into every purchase between businesses,
and a statute prints both. One is the rate on the input, and it is written per
input: what is sold decides it, not who buys. The other is the share of that
tax the buyer may take back, and it is written per class of buyer (or, in the
Japanese arm, per class of seller): who the buyer is decides it, not what is
bought. A buyer of class a who pays for input j at price p carries

    cost(j, a) = p_j * (1 + v_j * (1 - r_a))

after the deduction, so

    log cost(j, a) = log p_j + log(1 + v_j * (1 - r_a)).

**The second term is the whole station.** It is a product of an input index and
a class index inside a logarithm, and it does not split into a part that
depends on j alone plus a part that depends on a alone. Two inputs and two
classes make a square, and its sum is

    log[(1 + v1(1 - ra)) (1 + v2(1 - rb))] - log[(1 + v1(1 - rb)) (1 + v2(1 - ra))].

The price p_j sits in both classes' terms and cancels. So does any discount a
seller gives that depends on the class alone. What is left is read off paper.

**The square is a real loop and not only a count.** Both statutes let a buyer
change class, and the change applies to every input at once: a small-scale
taxpayer may register for the general method (VAT Law article 9, second
paragraph), and a Japanese exempt business may register as an invoice issuer.
The cost of crossing that edge is the same at every position, so it cancels
between the two positions and the square is the difference of the statutory
terms, which is what the four-term sum of the directed theorem reduces to when
the class edge is present and position-free.

**Everything here is a rational number, and the test is exact.** Rates and
ratios are printed as percentages, so the square vanishes if and only if a
product of four rationals equals one, which Fraction decides without a
tolerance. The logarithm is printed beside it for reading and never used to
decide anything.

**Two rivals, scored apart, as in B102.**

    bare        cost(j, a) = phi(j)                  no class index at all
    separable   log cost(j, a) = phi(j) + psi(a)      class enters as a factor
                                                      that is the same on every input

The first predicts that two classes pay the same for the same input. The second
is the one that carries weight: it is the class of every symmetric, class-level
friction or markup, and it is exactly the case a published conversion constant
produces. It predicts every square is one.

Run:
    python experiments/b122_vat_input_square.py
    python experiments/b122_vat_input_square.py --selftest
"""

import argparse
import copy
import json
import math
import pathlib
import sys
from fractions import Fraction as F

# ---------------------------------------------------------------------------
# The statutory table. Every value carries the provision that prints it
# (rule 25: each item carries its source, and the record shows which).
# ---------------------------------------------------------------------------

CN_LAW = ("中华人民共和国增值税法（2024-12-25 通过，第三十八条：2026-01-01 施行）；"
          "条文取自国家税务总局税收政策库全文页")

TABLES = {
    "CN-2026": {
        "jurisdiction": "China",
        "class_axis": "buyer",
        "law": CN_LAW,
        "inputs": [
            {"input": "goods", "v": F(13, 100),
             "source": "增值税法 第十条第一项：销售货物……除本条第二项、第四项、第五项规定外，税率为百分之十三"},
            {"input": "transport_construction", "v": F(9, 100),
             "source": "增值税法 第十条第二项：销售交通运输、邮政、基础电信、建筑、不动产租赁服务……税率为百分之九"},
            {"input": "services", "v": F(6, 100),
             "source": "增值税法 第十条第三项：销售服务、无形资产……税率为百分之六"},
        ],
        "classes": [
            {"class": "general", "r": F(1),
             "source": "增值税法 第十四条：应纳税额为当期销项税额抵扣当期进项税额后的余额"},
            {"class": "simplified", "r": F(0),
             "source": "增值税法 第八条第二款（小规模纳税人按销售额和征收率简易计税）；"
                       "第二十二条第一项（适用简易计税方法计税项目对应的进项税额不得抵扣）"},
            {"class": "advanced_manufacturing", "r": F(105, 100),
             "source": "财政部 税务总局公告2023年第43号：先进制造业企业按当期可抵扣进项税额加计5%抵减应纳增值税税额，"
                       "2023-01-01 至 2027-12-31",
             "condition": "加计抵减额只能抵减应纳税额，本行在抵减前应纳税额足以吸收它时成立"},
        ],
        "class_edge": ("增值税法 第九条第二款：小规模纳税人会计核算健全，能够提供准确税务资料的，"
                       "可以向主管税务机关办理登记，按照本法规定的一般计税方法计算缴纳增值税。"
                       "登记对纳税人的全部购进同时生效，与买的是哪一件无关"),
    },
}

JP_SOURCE = ("国税庁「消費税の仕入税額控除制度における適格請求書等保存方式に関するQ&A」"
             "問130【令和８年４月改訂】の（注）の表；改正令附則22①、23①")

JP_PERIODS = [
    ("2023-10-01..2026-09-30", F(80, 100)),
    ("2026-10-01..2028-09-30", F(70, 100)),
    ("2028-10-01..2030-09-30", F(50, 100)),
    ("2030-10-01..2031-09-30", F(30, 100)),
]

for _period, _ratio in JP_PERIODS:
    TABLES["JP-" + _period] = {
        "jurisdiction": "Japan",
        "class_axis": "seller",
        "law": "消費税法の適格請求書等保存方式と、その経過措置",
        "inputs": [
            {"input": "standard", "v": F(10, 100),
             "printed_national": F(78, 1000) / F(110, 100),
             "source": "問130：支払対価の額に110分の7.8（標準税率、国税分）；国税・地方税合計10%"},
            {"input": "reduced", "v": F(8, 100),
             "printed_national": F(624, 10000) / F(108, 100),
             "source": "問130：軽減税率の対象となる場合は108分の6.24（国税分）；合計8%"},
        ],
        "classes": [
            {"class": "invoice_issuer", "r": F(1),
             "source": "問130【答】：適格請求書発行事業者からの課税仕入れは仕入税額控除の対象"},
            {"class": "non_issuer", "r": _ratio,
             "source": JP_SOURCE + "：仕入税額相当額の" + str(int(_ratio * 100)) + "％（" + _period + "）"},
        ],
        "class_edge": ("免税事業者は適格請求書発行事業者の登録を申請できる。登録は"
                       "その事業者の全ての課税売上げに同時に効き、品目を選ばない"),
        "period": _period,
    }

TABLES["JP-2031-10-01.."] = copy.deepcopy(TABLES["JP-" + JP_PERIODS[-1][0]])
TABLES["JP-2031-10-01.."]["period"] = "2031-10-01.."
TABLES["JP-2031-10-01.."]["classes"][1] = {
    "class": "non_issuer", "r": F(0),
    "source": "問130【答】冒頭：適格請求書発行事業者以外の者からの課税仕入れは、原則、仕入税額控除を行うことはできない；"
              "経過措置は制度開始後８年間（表の最終期間は令和13年９月30日まで）"}

# The deduction factor of the Japanese national share: the buyer takes back
# price * v/(1+v) * r in total, of which 78/100 is the national portion. Q130
# prints the national coefficients directly, and the known-answer criterion
# reads them back from this table.
NATIONAL_SHARE = F(78, 100)


# ---------------------------------------------------------------------------
# The object
# ---------------------------------------------------------------------------

def factor(v, r):
    """The statutory multiplier on the pre-tax price: 1 + v(1 - r). Exact."""
    return 1 + v * (1 - r)


def square(v1, v2, ra, rb, cell=factor):
    """Product form of the square: one if and only if the log square is zero."""
    return (cell(v1, ra) * cell(v2, rb)) / (cell(v1, rb) * cell(v2, ra))


def closed_form(v1, v2, ra, rb):
    """The same square written out, on a second path that shares no helper."""
    num = (1 + v1 - v1 * ra) * (1 + v2 - v2 * rb)
    den = (1 + v1 - v1 * rb) * (1 + v2 - v2 * ra)
    return num / den


def logf(q):
    """A printed logarithm, fixed format (derived-file rule 5). Never decides."""
    return "%.6f" % math.log(q)


def fracs(q):
    return "%d/%d" % (q.numerator, q.denominator)


def build(tables, cell=factor):
    report = {}
    for name in sorted(tables):
        t = tables[name]
        ins, cls = t["inputs"], t["classes"]
        cells = {}
        for i in ins:
            for c in cls:
                cells[i["input"] + "|" + c["class"]] = cell(i["v"], c["r"])
        squares = []
        for x in range(len(ins)):
            for y in range(x + 1, len(ins)):
                for a in range(len(cls)):
                    for b in range(a + 1, len(cls)):
                        i1, i2, c1, c2 = ins[x], ins[y], cls[a], cls[b]
                        q = square(i1["v"], i2["v"], c1["r"], c2["r"], cell)
                        q2 = closed_form(i1["v"], i2["v"], c1["r"], c2["r"])
                        squares.append({
                            "inputs": [i1["input"], i2["input"]],
                            "classes": [c1["class"], c2["class"]],
                            "ratio": fracs(q), "log": logf(q),
                            "zero": q == 1, "two_paths_agree": q == q2})
        gaps = []
        base = cls[0]
        for c in cls[1:]:
            for i in ins:
                g = cell(i["v"], c["r"]) / cell(i["v"], base["r"])
                gaps.append({"input": i["input"], "class": c["class"],
                             "against": base["class"], "ratio": fracs(g),
                             "log": logf(g), "zero": g == 1})
        report[name] = {
            "jurisdiction": t["jurisdiction"], "class_axis": t["class_axis"],
            "period": t.get("period", "from 2026-01-01"),
            "cells": {k: fracs(v) for k, v in sorted(cells.items())},
            "squares": squares, "class_gaps": gaps,
            "independent_squares": (len(ins) - 1) * (len(cls) - 1),
            "nonzero_squares": sum(1 for s in squares if not s["zero"]),
        }
    return report


# ---------------------------------------------------------------------------
# Criteria. Each flag is computed from the object (rule 11f), and the rivals
# are scored apart (B102's form).
# ---------------------------------------------------------------------------

def _crit(name, kind, verdict, detail, extra=None):
    crit = {"name": name, "kind": kind, "detail": detail,
            "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        crit["void"] = True
    if extra:
        crit.update(extra)
    return crit


def criteria(report, tables):
    crits = []

    # B122-1 instrument: every value sourced, every square on two paths.
    unsourced = [n + ":" + row.get("input", row.get("class", "?"))
                 for n, t in sorted(tables.items())
                 for row in t["inputs"] + t["classes"]
                 if not str(row.get("source", "")).strip()]
    disagree = [n for n, r in sorted(report.items())
                for s in r["squares"] if not s["two_paths_agree"]]
    n_sq = sum(len(r["squares"]) for r in report.values())
    crits.append(_crit(
        "B122-1", "instrument", not unsourced and not disagree,
        "every statutory value carries its provision, and every square is "
        "computed twice, once as a ratio of the four cell factors and once from "
        "the written-out closed form, which share no helper. Unsourced values: "
        + (", ".join(unsourced) if unsourced else "none") + ". Squares where "
        "the two paths differ: " + (", ".join(disagree) if disagree else "none")
        + " of " + str(n_sq) + "."))

    # B122-2 premise: the statutes write rates per input and ratios per class,
    # separately, and the class edge exists and is position-free.
    mixed = []
    for n, t in sorted(tables.items()):
        for row in t["inputs"]:
            if "class" in row or "r" in row:
                mixed.append(n + ":" + row["input"] + " carries a class term")
        for row in t["classes"]:
            if "input" in row or "v" in row:
                mixed.append(n + ":" + row["class"] + " carries an input term")
        if not str(t.get("class_edge", "")).strip():
            mixed.append(n + ": no class edge on record")
    crits.append(_crit(
        "B122-2", "premise", not mixed,
        "the rate is written per input and the deduction ratio per class, and "
        "neither provision names the other's index; a buyer (in the Japanese "
        "arm, a seller) can cross between classes, and the crossing applies to "
        "every input at once, so its cost cancels between two positions and the "
        "square is a loop. Violations: " + (", ".join(mixed) if mixed else "none")
        + "."))

    # B122-3 known answer: Q130 prints the national coefficients, 7.8/110 and
    # 6.24/108. They must equal v/(1+v) * 78/100 with v from this table.
    ja = [(n, i) for n, t in sorted(tables.items())
          if t["jurisdiction"] == "Japan" for i in t["inputs"]]
    miss = [n + ":" + i["input"] for n, i in ja
            if i["v"] / (1 + i["v"]) * NATIONAL_SHARE != i["printed_national"]]
    crits.append(_crit(
        "B122-3", "known_answer", (not miss) if ja else None,
        ("the coefficients the tax agency prints in Q130 (110 分の 7.8 for the "
         "standard rate, 108 分の 6.24 for the reduced rate) are read back from "
         "this table's rates as v/(1+v) x 78/100, the national share. Checked "
         "on " + str(len(ja)) + " rows; mismatches: "
         + (", ".join(miss) if miss else "none") + ".")
        if ja else "void: this run carries no Japanese arm, so the printed "
                   "coefficients have nothing to be read back against."))

    # B122-4 own reading: the squares, exact, per carrier.
    lines = []
    for n in sorted(report):
        r = report[n]
        vals = sorted({s["log"] for s in r["squares"]})
        lines.append(n + " " + str(r["nonzero_squares"]) + "/"
                     + str(len(r["squares"])) + " non-zero, "
                     + str(r["independent_squares"]) + " independent, logs "
                     + ", ".join(vals))
    any_nonzero = any(r["nonzero_squares"] for r in report.values())
    crits.append(_crit(
        "B122-4", "own_reading", any_nonzero,
        "the registered reading is that the statutory term log(1 + v(1 - r)) "
        "does not separate, so squares with two distinct rates and two distinct "
        "ratios are non-zero, exactly. " + "; ".join(lines) + "."))

    # B122-5 rival, bare: two classes pay the same for the same input.
    gaps = [g for r in report.values() for g in r["class_gaps"]]
    nz_gaps = [g for g in gaps if not g["zero"]]
    crits.append(_crit(
        "B122-5", "rival", len(nz_gaps) > 0,
        "the bare scalar field puts one cost on one input whoever buys it. Read: "
        + str(len(nz_gaps)) + " of " + str(len(gaps)) + " class gaps are non-zero; "
        "largest " + max((g["log"] for g in nz_gaps), key=lambda s: abs(float(s)),
                        default="none") + " in log. A seller who offset the "
        "statutory wedge by charging the disadvantaged class less would restore "
        "one cost only by writing a price that depends on the buyer's class and "
        "the input's rate together, which is itself a two-index schedule.",
        {"rival_premise": "cost(j, a) = phi(j): a price is a scalar on positions, "
                          "one input has one cost whoever buys it",
         "rival_entailment": "phi carries no class index, so the ratio of two "
                             "classes' costs is one on every input",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))

    # B122-6 rival, separable: the class enters as one factor on every input.
    sq = [s for r in report.values() for s in r["squares"]]
    nz_sq = [s for s in sq if not s["zero"]]
    crits.append(_crit(
        "B122-6", "rival", len(nz_sq) > 0,
        "the separable rival lets the class enter the cost as a factor, provided "
        "it is the same factor on every input: every symmetric class-level "
        "friction, every class markup, and every published class-only conversion "
        "constant has this form, and it makes every square exactly one. Read: "
        + str(len(nz_sq)) + " of " + str(len(sq)) + " squares differ from one, "
        "decided in exact rational arithmetic with no tolerance.",
        {"rival_premise": "log cost(j, a) = phi(j) + psi(a): the class changes the "
                          "cost by one proportion on every input",
         "rival_entailment": "the ratio of two classes' costs is exp(psi(a) - "
                             "psi(b)) on every input, so the ratio of that ratio "
                             "across two inputs, which is the square, is one",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))

    # B122-7 bookkeeping: provisions, periods and the coverage table are in
    # the record. The flag reads the record's own fields.
    need = ("law", "inputs", "classes", "class_edge")
    missing = [n + ":" + k for n, t in sorted(tables.items())
               for k in need if not t.get(k)]
    crits.append(_crit(
        "B122-7", "bookkeeping", not missing and bool(tables),
        "each carrier's law, per-input rates, per-class ratios and class edge "
        "are printed into the record with their provisions. Missing: "
        + (", ".join(missing) if missing else "none") + "; carriers: "
        + str(len(tables)) + "."))
    return crits


def config_block(tables):
    """What this run chose (rule 18d)."""
    return {
        "carriers": sorted(tables),
        "arithmetic": "fractions.Fraction, exact; logarithms printed only",
        "cn_classes": [c["class"] + "=" + fracs(c["r"])
                       for c in tables["CN-2026"]["classes"]] if "CN-2026" in tables else [],
        "jp_periods": [p + "=" + fracs(r) for p, r in JP_PERIODS] + ["2031-10-01..=0/1"],
    }


def tables_for_record(tables):
    out = {}
    for n, t in sorted(tables.items()):
        row = {k: v for k, v in t.items() if k not in ("inputs", "classes")}
        row["inputs"] = [{k: (fracs(v) if isinstance(v, F) else v)
                          for k, v in i.items()} for i in t["inputs"]]
        row["classes"] = [{k: (fracs(v) if isinstance(v, F) else v)
                           for k, v in c.items()} for c in t["classes"]]
        out[n] = row
    return out


def verdicts(tables, cell=factor):
    report = build(tables, cell)
    return {c["name"]: c["passed"] for c in criteria(report, tables)}


def selftest():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    base = verdicts(TABLES)
    ok("every criterion holds on the statutory table",
       all(v is True for v in base.values()))

    # 11f: every flag must flip on an input built to make it false.
    t = copy.deepcopy(TABLES)
    t["CN-2026"]["inputs"][0]["source"] = ""
    ok("an unsourced value flips B122-1", verdicts(t)["B122-1"] is False)

    ok("a broken cell builder flips B122-1 (the two paths part)",
       verdicts(TABLES, cell=lambda v, r: 1 + v * r)["B122-1"] is False)

    t = copy.deepcopy(TABLES)
    t["CN-2026"]["classes"][1]["v"] = F(13, 100)
    ok("a ratio that names an input flips B122-2", verdicts(t)["B122-2"] is False)

    t = copy.deepcopy(TABLES)
    t["CN-2026"]["class_edge"] = ""
    ok("a missing class edge flips B122-2", verdicts(t)["B122-2"] is False)

    t = copy.deepcopy(TABLES)
    t["JP-2026-10-01..2028-09-30"]["inputs"][0]["v"] = F(9, 100)
    ok("a mistranscribed Japanese rate flips B122-3", verdicts(t)["B122-3"] is False)

    t = {"CN-2026": copy.deepcopy(TABLES["CN-2026"])}
    ok("a run with no Japanese arm leaves B122-3 undecided, not false",
       verdicts(t)["B122-3"] is None)

    t = copy.deepcopy(TABLES)
    for n in t:
        for c in t[n]["classes"]:
            c["r"] = F(1)
    v = verdicts(t)
    ok("equal ratios flip both rivals and the own reading",
       v["B122-5"] is False and v["B122-6"] is False and v["B122-4"] is False)

    t = copy.deepcopy(TABLES)
    for n in t:
        for i in t[n]["inputs"]:
            i["v"] = F(13, 100)
            if "printed_national" in i:
                i["printed_national"] = i["v"] / (1 + i["v"]) * NATIONAL_SHARE
    v = verdicts(t)
    ok("equal rates keep the bare rival refuted and flip the separable one",
       v["B122-5"] is True and v["B122-6"] is False)

    # The D30 third clause contrast: a class-only conversion constant, the
    # grain procurement shape (one price is 1.5 times the other on every
    # good), closes every square.
    sep = verdicts(TABLES, cell=lambda v, r: (1 + v) * (1 + (1 - r) / 2))
    ok("a class-only factor closes every square (separable rival right)",
       sep["B122-6"] is False and sep["B122-5"] is True)

    t = copy.deepcopy(TABLES)
    del t["CN-2026"]["law"]
    ok("a carrier with no law on record flips B122-7", verdicts(t)["B122-7"] is False)

    ok("closed form matches a hand value, CN goods vs services, general vs simplified",
       closed_form(F(13, 100), F(6, 100), F(1), F(0)) == F(106, 113))

    width = max(len(label) for label, _ in checks)
    for label, cond in checks:
        print(("PASS  " if cond else "FAIL  ") + label.ljust(width))
    bad = [label for label, cond in checks if not cond]
    print("")
    print("selftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", default="results/b122_vat_input_square.json")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    report = build(TABLES)
    crits = criteria(report, TABLES)

    for n in sorted(report):
        r = report[n]
        print("== " + n + "   (" + r["class_axis"] + " classes, "
              + str(r["independent_squares"]) + " independent squares)")
        for s in r["squares"]:
            print("   " + "/".join(s["inputs"]).ljust(34) + " x "
                  + "/".join(s["classes"]).ljust(34) + " ratio "
                  + s["ratio"].ljust(22) + " log " + s["log"])
    print("")
    print("Japanese dose, the one square (standard vs reduced, issuer vs non-issuer):")
    for n in sorted(k for k in report if k.startswith("JP-")):
        s = report[n]["squares"][0]
        print("   " + report[n]["period"].ljust(24) + " log " + s["log"])
    print("")

    failed = []
    for c in crits:
        if c["passed"] is None:
            mark = "VOID   "
        elif c["passed"]:
            mark = "PASS   "
        else:
            mark = "FAILED[" + c["kind"] + "]: "
            failed.append(c["name"])
        print(mark + c["name"] + "  " + c["detail"])

    record = {"stage": "B122", "config": config_block(TABLES),
              "criteria": crits, "report": report,
              "tables": tables_for_record(TABLES)}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("")
    print("wrote " + str(out))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
