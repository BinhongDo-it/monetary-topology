"""The printed-format floor under the squares of B122, B123 and B125.

Each of these stations reads squares off published schedules: a tax statute, two card
networks' interchange tables, an airport tariff guide with a statute and published public
service fares. Their squares are decided exactly, in rationals. What exactness does not say is
how large a square is against the format its inputs are printed in. The discipline for that is
the third condition on the resolution floor: when a number is printed in a fixed published format,
the printed digit is the floor. So here each printed input of a square is moved by one tick of its
own format, and the floor of the square is the largest change in its log that one tick produces.
A square stands on the floor when its log is larger than that.

Ticks, as the documents print them:

    B122   tax rates and deduction ratios              one percentage point
    B123   ad valorem rates                             0.01 per cent
           fixed fees, caps and minimums                one cent
    B125   airport charges                              one euro cent
           public service reference fares               one euro
           resident share and social discount           one percentage point

A number printed once and used in several cells is one input: in B125 the inter-island security
and reduced-mobility charges are printed once for every airport, a passenger charge once per
airport group, and a reference fare once per route for both directions. Moving it moves every
cell it sits in.

B123 is read at its reference setting (a $100 ticket, log(1 + r), no fraud cent) and only on the
squares it reads as non-zero on every setting; a square on a row printed with a ticket condition
the reference ticket does not meet is read at the first grid ticket that meets it.

Run:
    python experiments/b122_b125_tick_floor.py
    python experiments/b122_b125_tick_floor.py --selftest
"""

import argparse
import json
import math
import pathlib
import statistics
import sys
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import b122_vat_input_square as b122  # noqa: E402
import b125_resident_square as b125  # noqa: E402

PP = F(1, 100)
CENT = F(1, 100)


def floor_of(value_fn, inputs, ticks):
    """value_fn(inputs) -> product-form square. Floor: the largest |change in log| when one
    input moves one tick either way."""
    base = math.log(value_fn(inputs))
    worst = 0.0
    for key, tick in ticks.items():
        for sgn in (1, -1):
            moved = dict(inputs)
            moved[key] = inputs[key] + sgn * tick
            try:
                q = value_fn(moved)
            except ZeroDivisionError:
                continue
            if q > 0:
                worst = max(worst, abs(math.log(q) - base))
    return base, worst


def summarise(rows):
    ratios = [abs(r["log"]) / r["floor"] for r in rows if r["floor"] > 0]
    above = sum(1 for r in rows if r["floor"] > 0 and abs(r["log"]) > r["floor"])
    return {"squares": len(rows), "above_floor": above,
            "floor_zero": sum(1 for r in rows if r["floor"] == 0),
            "ratio_min": "%.3f" % min(ratios) if ratios else None,
            "ratio_median": "%.3f" % statistics.median(ratios) if ratios else None,
            "ratio_max": "%.3f" % max(ratios) if ratios else None}


# ---------------------------------------------------------------- B122

def b122_rows(tick=PP):
    rows = []
    for name, t in sorted(b122.TABLES.items()):
        ins, cls = t["inputs"], t["classes"]
        for x in range(len(ins)):
            for y in range(x + 1, len(ins)):
                for a in range(len(cls)):
                    for b in range(a + 1, len(cls)):
                        inp = {"v1": ins[x]["v"], "v2": ins[y]["v"], "ra": cls[a]["r"], "rb": cls[b]["r"]}
                        lg, fl = floor_of(lambda d: b122.closed_form(d["v1"], d["v2"], d["ra"], d["rb"]),
                                          inp, {k: tick for k in inp})
                        if lg != 0:
                            rows.append({"carrier": name, "square": [ins[x]["input"], ins[y]["input"],
                                                                     cls[a]["class"], cls[b]["class"]],
                                         "log": lg, "floor": fl})
    return rows


# ---------------------------------------------------------------- B123

def b123_rows(pct_tick=F(1, 10000), cent=CENT):
    import b123_interchange_square as m
    tables, _ = m.load_all()
    t_ref, fr_ref = m.REF["ticket"], m.REF["fraud"]
    rows = []
    for name, t in sorted(tables.items()):
        if t["family"] not in ("regulatory", "product"):
            continue
        used, ncls = t["used"], len(t["classes"])
        for i in range(len(used)):
            for j in range(i + 1, len(used)):
                for a in range(ncls):
                    for b in range(a + 1, ncls):
                        ci, cj = used[i]["cells"], used[j]["cells"]
                        cells = (ci[a], cj[b], ci[b], cj[a])
                        if None in cells:
                            continue
                        lo = max(used[i]["min_ticket"], used[j]["min_ticket"])
                        signs = []
                        for tk in m.TICKETS:
                            if tk < lo:
                                continue
                            for tr in m.TRANSFORMS:
                                for fr in m.FRAUD:
                                    r = [m.fee(c, tk, fr) / tk for c in cells]
                                    if tr == "neglog1m" and any(v >= 1 for v in r):
                                        continue
                                    signs.append(m.sign(m.square_ratio(*r, tr)))
                        if not signs or not all(s != 0 for s in signs):
                            continue
                        # A row printed with a ticket condition is read at the first grid ticket
                        # that meets it when the reference ticket does not.
                        t_at = t_ref if t_ref >= lo else min(tk for tk in m.TICKETS if tk >= lo)
                        inp, ticks = {}, {}
                        for k, c in enumerate(cells):
                            inp["pct%d" % k], ticks["pct%d" % k] = c["pct"], pct_tick
                            inp["fix%d" % k], ticks["fix%d" % k] = c["fixed"], cent
                            if c.get("cap") is not None:
                                inp["cap%d" % k], ticks["cap%d" % k] = c["cap"], cent
                            if c.get("min") is not None:
                                inp["min%d" % k], ticks["min%d" % k] = c["min"], cent

                        def value(d, cells=cells, t_at=t_at):
                            cs = []
                            for k, c in enumerate(cells):
                                c2 = dict(c, pct=d["pct%d" % k], fixed=d["fix%d" % k])
                                if "cap%d" % k in d:
                                    c2["cap"] = d["cap%d" % k]
                                if "min%d" % k in d:
                                    c2["min"] = d["min%d" % k]
                                cs.append(m.fee(c2, t_at, fr_ref) / t_at)
                            return m.square_ratio(*cs, "log1p")
                        lg, fl = floor_of(value, inp, ticks)
                        rows.append({"carrier": name, "network": t["network"], "family": t["family"],
                                     "square": [used[i]["row"], used[j]["row"], t["classes"][a],
                                                t["classes"][b]], "ticket": str(t_at),
                                     "log": lg, "floor": fl})
    return rows


# ---------------------------------------------------------------- B125

GROUP = {"LPA": "G1", "TFS": "G1", "PMI": "G1", "TFN": "G2", "FUE": "G2", "ACE": "G2", "IBZ": "G2",
         "MAH": "G2", "SPC": "G3", "VDE": "G4", "GMZ": "G4"}


def _cell_keys(c):
    dep = c["cell"].split("-")[0]
    route = "-".join(sorted(c["cell"].split("-")))
    return {"fare": ("fare", route), "passenger": ("pax", GROUP[dep]), "security": ("sec",), "pmr": ("pmr",)}


def _inputs_for(cells):
    inp = {}
    for c in cells:
        for field, key in _cell_keys(c).items():
            inp[key] = F(c[field])
    return inp


def _ticks_for(inp, fare_tick=F(1), cent=CENT, pp=PP):
    t = {}
    for key in inp:
        t[key] = fare_tick if key[0] == "fare" else (pp if key[0] in ("alpha", "disc") else cent)
    return t


def _k(c, d, alpha):
    keys = _cell_keys(c)
    f = d[keys["fare"]]
    u = d[keys["passenger"]] + d[keys["security"]] + d[keys["pmr"]]
    return ((1 - alpha) * f + u) / (f + u)


def b125_route_rows(fare_tick=F(1), cent=CENT, pp=PP):
    rows = []
    cells = b125.osp_cells()
    for x in range(len(cells)):
        for y in range(x + 1, len(cells)):
            c1, c2 = cells[x], cells[y]
            inp = _inputs_for([c1, c2])
            inp[("alpha",)] = F(3, 4)
            ticks = _ticks_for(inp, fare_tick, cent, pp)

            def value(d, c1=c1, c2=c2):
                a = d[("alpha",)]
                return _k(c1, d, a) / _k(c2, d, a)
            lg, fl = floor_of(value, inp, ticks)
            if lg != 0:
                rows.append({"carrier": "canarias OSP", "square": [c1["cell"], c2["cell"]], "log": lg,
                             "floor": fl})
    return rows


def b125_class_rows(fare_tick=F(1), cent=CENT, pp=PP):
    rows = []
    sc = b125.social_cells()
    for arch in sorted(sc):
        rule = b125.SOCIAL[arch]
        for c in sc[arch]:
            inp = _inputs_for([c])
            inp[("alpha",)] = F(3, 4)
            inp[("disc", arch)] = rule["discount"]
            ticks = _ticks_for(inp, fare_tick, cent, pp)
            keys = _cell_keys(c)

            def value(d, keys=keys, arch=arch, rule=rule):
                cc = {"fare": d[keys["fare"]], "passenger": d[keys["passenger"]],
                      "security": d[keys["security"]], "pmr": d[keys["pmr"]]}
                return b125.social_class_square(cc, d[("alpha",)],
                                                dict(rule, discount=d[("disc", arch)]))
            lg, fl = floor_of(value, inp, ticks)
            if lg != 0:
                rows.append({"carrier": arch + " social", "square": [c["cell"]], "log": lg, "floor": fl})
    return rows


# ---------------------------------------------------------------- criteria

def _crit(name, kind, verdict, detail):
    return {"name": name, "kind": kind, "detail": detail, "passed": bool(verdict)}


def criteria(rep):
    out = []
    for name, key, what in (("TICK-B122", "b122", "B122's statutory squares"),
                            ("TICK-B123", "b123", "B123's squares read on every setting, at the reference setting"),
                            ("TICK-B125-routes", "b125_routes", "B125's squares at the published OSP reference fares"),
                            ("TICK-B125-class", "b125_class", "B125's age-by-residence class squares")):
        s = rep[key]["summary"]
        out.append(_crit(
            name, "instrument", s["squares"] > 0 and s["floor_zero"] == 0,
            "the printed-format floor is measured on every one of " + what + ": " + str(s["squares"])
            + " squares, none with a zero floor (" + str(s["floor_zero"]) + "); " + str(s["above_floor"])
            + " stand above their floor; square over floor, min " + str(s["ratio_min"]) + ", median "
            + str(s["ratio_median"]) + ", max " + str(s["ratio_max"]) + "."))
    return out


def build(skip_b123=False, **kw):
    rep = {}
    for key, rows in (("b122", b122_rows(**{k: v for k, v in kw.items() if k == "tick"})),
                      ("b125_routes", b125_route_rows(**{k: v for k, v in kw.items() if k in ("fare_tick", "cent", "pp")})),
                      ("b125_class", b125_class_rows(**{k: v for k, v in kw.items() if k in ("fare_tick", "cent", "pp")}))):
        rep[key] = {"summary": summarise(rows), "rows": rows}
    if not skip_b123:
        rows = b123_rows()
        rep["b123"] = {"summary": summarise(rows), "rows": rows,
                       "by_line": {fam + " " + net: summarise([r for r in rows if r["family"] == fam
                                                               and r["network"] == net])
                                   for fam in ("regulatory", "product") for net in ("visa", "mastercard")}}
    return rep


def selftest():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    rep = build(skip_b123=True)
    rep["b123"] = {"summary": {"squares": 1, "floor_zero": 0, "above_floor": 1, "ratio_min": "2",
                               "ratio_median": "2", "ratio_max": "2"}}
    ok("every criterion holds on the three stations' own inputs (B123 stubbed here)",
       all(c["passed"] for c in criteria(rep)))
    flat = build(skip_b123=True, tick=F(0), fare_tick=F(0), cent=F(0), pp=F(0))
    flat["b123"] = rep["b123"]
    v = {c["name"]: c["passed"] for c in criteria(flat)}
    ok("a zero tick leaves a zero floor and flips the three paper criteria",
       v["TICK-B122"] is False and v["TICK-B125-routes"] is False and v["TICK-B125-class"] is False)
    # Hand value: the Balearic class square at zero charges is log(1 - d); a one-point move in d
    # moves it by about 1/0.8 of a point, larger than a cent in any charge.
    one = b125_class_rows()
    bal = [r for r in one if r["carrier"] == "baleares social"]
    ok("the Balearic class squares sit several floors above theirs",
       bal and min(abs(r["log"]) / r["floor"] for r in bal) > 5)
    tk = _ticks_for({("fare", "LPA-TFN"): F(90), ("alpha",): F(3, 4), ("disc", "canarias"): F(1, 10),
                     ("sec",): F(60, 100)})
    ok("each printed number moves by its own format's tick: fare 1 euro, shares 1 point, charges 1 cent",
       tk == {("fare", "LPA-TFN"): F(1), ("alpha",): PP, ("disc", "canarias"): PP, ("sec",): CENT})
    # Shared inputs: the two directions of one route share one fare, so moving it moves both cells.
    cells = b125.osp_cells()[:2]
    ok("both directions of one route read one fare key", len({k for k in _inputs_for(cells) if k[0] == "fare"}) == 1)
    width = max(len(label) for label, _ in checks)
    for label, cond in checks:
        print(("PASS  " if cond else "FAIL  ") + label.ljust(width))
    bad = [label for label, cond in checks if not cond]
    print("")
    print("selftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="results/b122_b125_tick_floor.json")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rep = build()
    assert rep["b123"]["summary"]["squares"] == 7033, rep["b123"]["summary"]["squares"]
    for k in ("b122", "b123", "b125_routes", "b125_class"):
        print(k.ljust(12), rep[k]["summary"])
    for k, s in sorted(rep["b123"]["by_line"].items()):
        print("   b123", k.ljust(22), s)
    crits = criteria(rep)
    failed = []
    for c in crits:
        print(("PASS   " if c["passed"] else "FAILED[" + c["kind"] + "]: ") + c["name"] + "  " + c["detail"])
        if not c["passed"]:
            failed.append(c["name"])
    for k in rep:
        for r in rep[k]["rows"]:
            r["log"] = "%.6f" % r["log"]
            r["floor"] = "%.6f" % r["floor"]
    record = {"stage": "B122-B125 floor", "config": {
        "ticks": {"B122": "1 percentage point", "B123": "0.01 per cent; 1 cent on fixed fees, caps, minimums",
                  "B125": "1 euro cent on charges; 1 euro on reference fares; 1 point on shares and discounts"},
        "b123_setting": "ticket 100, log(1 + r), no fraud cent; squares read on every setting only",
        "shared_inputs": "a number printed once is one input and moves in every cell it sits in"},
        "criteria": crits, "report": rep}
    out = pathlib.Path(a.out)
    out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("wrote " + str(out))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
