#!/usr/bin/env python3
"""B11's first gate, C11-0: count the issuers that close a loop in corporate credit.

The loop is `investment grade -> downgrade -> distressed exchange -> re-rated`,
the corporate counterpart of B8's `current -> delinquent -> modified -> current`.
**The gate counts issuers that carry it, against a registered threshold of 200.**
If there are only a few dozen, the domain is dead whatever else is available.

--------------------------------------------------------------------------
The rulings this reads, all made before any count
--------------------------------------------------------------------------

1. "Investment grade before the exchange" is **investment grade at any point in
   the rating history before it**, the 2012-06-15 stock records included.
2. The closing edge **does not require a return to investment grade**: any
   re-rating on the scale after the exchange closes the loop.
3. The marker is **the agency's own symbol**: Fitch's `RD` (restricted default).
4. The domain is **Corporate, Financial and Insurance together**, reported per
   class.
5. Short of 200, **S&P is read before the gate is judged**.
6. Still short after S&P, **the station stops** and a domain switch is
   registered separately.
7. The count is **not widened to default of any kind**.

--------------------------------------------------------------------------
What this file fixes that the rulings leave open
--------------------------------------------------------------------------

The series is the issuer's long-term issuer default rating, where `RD` lives.
Every place a choice remains, both readings are printed:

- **series**: the foreign-currency long-term IDR alone, and that series joined
  with the local-currency long-term IDR;
- **identity**: the row key `b11_markers` counts with (LEI, then obligor
  identifier, then issuer identifier, then name), and a union of rows that share
  an LEI, an obligor identifier or a name within one class file;
- **re-rating on the day of the exchange**: a later date only, and the same date
  or later.

The rating scale is enumerated rather than assumed, and any symbol outside it is
reported.

Usage:

    python experiments/b11_c11_0_gate.py
    python experiments/b11_c11_0_gate.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b11_markers as M                                        # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "results" / "b11_c11_0_gate.json"
OUT_MD = ROOT / "results" / "b11_c11_0_gate.md"

THRESHOLD = 200
IG = ("AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-")
SPECULATIVE = ("BB+", "BB", "BB-", "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C")
SCALE = IG + SPECULATIVE
#: Symbols on the series that are not rungs of the scale. `RD` is the marker,
#: `D` is default, `WD` a withdrawal and `NR` not rated.
OFF_SCALE = ("RD", "D", "WD", "NR")
ORDER = SCALE + ("RD", "D")

SERIES = {
    "LT IDR": ("Long Term Issuer Default Rating",),
    "LT IDR + LC LT IDR": ("Long Term Issuer Default Rating",
                           "Local Currency Long Term Issuer Default Rating"),
}


def read_rows(files) -> list[dict]:
    """Every row of the issuer default rating series, with its class and its
    position in the file."""
    wanted = set(SERIES["LT IDR + LC LT IDR"])
    out = []
    for path in files:
        cls = M.VALID_NAME.match(path.name).group(3)
        with open(path, encoding="utf-8", newline="") as f:
            for i, r in enumerate(csv.DictReader(f)):
                if r["rating_type"] in wanted:
                    out.append({"class": cls, "pos": i, "type": r["rating_type"],
                                "date": r["rating_action_date"].strip(),
                                "rating": r["rating"].strip(),
                                "action": r["rating_action_class"].strip(),
                                "lei": r["legal_entity_identifier"].strip(),
                                "obligor_id": r["obligor_identifier"].strip(),
                                "name": r["obligor_name"].strip().strip('"').strip(),
                                "rowkey": M.obligor_key(r)})
    return out


def union_ids(rows: list[dict]) -> list[str]:
    """Connect rows that share an LEI, an obligor identifier or a lower-cased
    name inside one class file, and return each row's component."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first = []
    for r in rows:
        ks = [f"{r['class']}|{c}|{r[c]}" for c in ("lei", "obligor_id") if r[c]]
        if r["name"]:
            ks.append(f"{r['class']}|name|{r['name'].lower()}")
        for k in ks[1:]:
            a, b = find(ks[0]), find(k)
            if a != b:
                parent[a] = b
        first.append(ks[0] if ks else f"{r['class']}|row|{r['pos']}")
    return [find(k) for k in first]


def histories(rows, ids, types) -> dict[str, list[dict]]:
    h = collections.defaultdict(list)
    for r, k in zip(rows, ids):
        if r["type"] in types:
            h[k].append(r)
    for k in h:
        h[k].sort(key=lambda r: (r["date"], r["pos"]))
    return h


def loops(hist: dict[str, list[dict]]) -> dict:
    """Per issuer: its exchanges, whether investment grade preceded one, and
    whether a rung of the scale followed one."""
    per = {}
    for k, h in hist.items():
        rds = sorted({r["date"] for r in h if r["rating"] == "RD"})
        if not rds:
            continue
        ig_before = [d0 for d0 in rds if any(r["rating"] in IG and r["date"] < d0 for r in h)]
        later = [d0 for d0 in rds if any(r["rating"] in SCALE and r["date"] > d0 for r in h)]
        same_or_later = [d0 for d0 in rds
                         if any(r["rating"] in SCALE and r["date"] >= d0 for r in h)]
        strict = [d0 for d0 in ig_before if d0 in later]
        loose = [d0 for d0 in ig_before if d0 in same_or_later]

        def before_withdrawal(d0):
            wd = [r["date"] for r in h if r["rating"] == "WD" and r["date"] > d0]
            stop = min(wd) if wd else "9999-12-31"
            return any(r["rating"] in SCALE and d0 < r["date"] < stop for r in h)

        unbroken = [d0 for d0 in strict if before_withdrawal(d0)]
        best = [ORDER.index(r["rating"]) for r in h if r["rating"] in ORDER and r["date"] < rds[0]]
        per[k] = {"class": h[0]["class"], "name": h[-1]["name"], "rd_dates": rds,
                  "ig_before": bool(ig_before), "rerated": bool(later),
                  "loop": bool(strict), "loop_same_day": bool(loose),
                  "loop_before_withdrawal": bool(unbroken),
                  "loop_dates": strict, "best_before_first_rd":
                      ORDER[min(best)] if best else "none before the first RD",
                  "path": [f"{r['date']} {r['rating']}" for r in h]}
    return per


def window_of(d: str) -> str:
    return M.window_of(d) or "outside"


def analyse(files) -> dict:
    rows = read_rows(files)
    variants = {}
    for sname, types in SERIES.items():
        for iname, ids in (("row key", [f"{r['class']}|{r['rowkey']}" for r in rows]),
                           ("union of identifiers", union_ids(rows))):
            per = loops(histories(rows, ids, types))
            by_class = collections.Counter(v["class"] for v in per.values() if v["loop"])
            windows = collections.Counter(window_of(d) for v in per.values()
                                          for d in v["loop_dates"])
            variants[f"{sname} / {iname}"] = {
                "issuers_with_rd": len(per),
                "ig_before_an_rd": sum(v["ig_before"] for v in per.values()),
                "rerated_after_an_rd": sum(v["rerated"] for v in per.values()),
                "loops": sum(v["loop"] for v in per.values()),
                "loops_same_day": sum(v["loop_same_day"] for v in per.values()),
                "loops_before_withdrawal": sum(v["loop_before_withdrawal"] for v in per.values()),
                "loops_by_class": dict(sorted(by_class.items())),
                "loop_exchanges_by_window": dict(sorted(windows.items())),
                "best_before_first_rd": dict(collections.Counter(
                    v["best_before_first_rd"] for v in per.values())),
                "objects": {k: v for k, v in per.items() if v["ig_before"]},
            }
    symbols = collections.Counter(r["rating"] for r in rows)
    unknown = sorted(s for s in symbols if s not in SCALE + OFF_SCALE)
    spans = {}
    for path in files:
        dates = []
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                d = r["rating_action_date"].strip()
                if d:
                    dates.append(d)
        spans[path.name] = {"earliest": min(dates), "latest": max(dates),
                            "rows": len(dates),
                            "before_rule_start": sum(d < M.RULE_START for d in dates),
                            "on_rule_start": sum(d == M.RULE_START for d in dates)}
    return {"files": [p.name for p in files], "series_rows": len(rows),
            "symbols": dict(symbols.most_common()), "unknown_symbols": unknown,
            "variants": variants, "spans": spans}


def verdict(a: dict) -> dict:
    primary = a["variants"]["LT IDR / row key"]
    counts = {k: (v["loops"], v["loops_same_day"]) for k, v in a["variants"].items()}
    top = max(max(x) for x in counts.values())
    if top >= THRESHOLD:
        state, passed = "the gate passes", True
    else:
        state, passed = ("undecided: short of the threshold on Fitch, and the registered "
                         "exit reads S&P before judging"), None
    needed = THRESHOLD - top
    return {"state": state, "passed": passed, "counts": counts, "largest": top,
            "needed_from_sp": needed,
            "retained_share": primary["ig_before_an_rd"] / max(primary["issuers_with_rd"], 1),
            "share_needed": THRESHOLD / max(primary["issuers_with_rd"], 1),
            "multiple_of_fitch_needed": (needed / top) if top else float("inf")}


def criteria(a: dict, v: dict) -> list[dict]:
    p = a["variants"]["LT IDR / row key"]
    cs = [{
        "name": "B11-C11-0  issuers that close IG -> RD -> re-rated, against 200",
        "kind": "premise", "passed": v["passed"], "undecided": v["passed"] is None,
        "detail": (f"{p['loops']} issuers on the long-term IDR by row key "
                   f"({p['loops_same_day']} with a same-day re-rating); every variant "
                   f"reads {min(x[0] for x in v['counts'].values())} to {v['largest']}. "
                   f"The investment-grade screen keeps {p['ig_before_an_rd']} of the "
                   f"{p['issuers_with_rd']} issuers with an RD, where 200 needs "
                   f"{v['share_needed']:.1%}. State: {v['state']}. For S&P to carry the "
                   f"gate it has to add {v['needed_from_sp']} qualifying issuers Fitch "
                   f"does not have, {v['multiple_of_fitch_needed']:.0f} times Fitch's "
                   "own count. Three states: at least 200 passes; short on Fitch alone "
                   "is undecided until S&P is read (ruling 5); short after S&P stops "
                   "the station (ruling 6)")},
        {"name": "B11-C11-0a  every symbol on the series is a rung of the scale or a named off-scale code",
         "kind": "instrument", "passed": not a["unknown_symbols"],
         "detail": (f"{len(a['symbols'])} distinct symbols over {a['series_rows']:,} rows; "
                    f"outside the scale and {', '.join(OFF_SCALE)}: "
                    f"{a['unknown_symbols'] or 'none'}")},
        {"name": "B11-C11-0b  the count does not depend on how issuers are identified",
         "kind": "instrument",
         "passed": all(v["counts"][f"{s} / row key"] == v["counts"][f"{s} / union of identifiers"]
                       for s in SERIES),
         "detail": "; ".join(f"{k}: {x[0]} (same day {x[1]})" for k, x in v["counts"].items())},
        {"name": "B11-C11-0c  every issuer that was investment grade before an RD is printed with its path",
         "kind": "bookkeeping", "passed": True,
         "detail": (f"{len(p['objects'])} issuers printed, "
                    f"{sum(o['loop'] for o in p['objects'].values())} of them close the loop")},
    ]
    sp = a["spans"]
    reach = all(s["earliest"] <= M.RULE_START for s in sp.values())
    cs.append({"name": "B11-C11-2  the snapshot on disk reaches back to 2012-06-15, so a rolling window does not bind",
               "kind": "premise", "passed": reach,
               "detail": "; ".join(f"{k}: {s['earliest']} to {s['latest']}, "
                                   f"{s['on_rule_start']:,} rows on 2012-06-15"
                                   for k, s in sp.items())})
    return cs


def render(a: dict, v: dict, cs: list[dict]) -> str:
    L = []
    A = L.append
    p = a["variants"]["LT IDR / row key"]
    A("# B11, C11-0: the corporate-credit loop, counted\n")
    A("Generated by `experiments/b11_c11_0_gate.py` from Fitch's rating histories "
      "on disk. The criteria are written in the script that produces this record, "
      "the record carries their text, and every quantity this run produces is "
      "reported.\n")
    A(f"**The reading.** On Fitch's long-term issuer default rating, "
      f"{p['issuers_with_rd']} issuers carry an `RD`. **{p['ig_before_an_rd']} of them "
      f"were investment grade before it, and {p['loops']} of those were re-rated "
      f"afterwards** ({p['loops_same_day']} counting a re-rating on the day of the "
      f"exchange). The threshold is {THRESHOLD}. Every variant below reads "
      f"{min(x[0] for x in v['counts'].values())} to {v['largest']}, and dropping the "
      f"investment-grade condition altogether leaves {p['rerated_after_an_rd']} "
      "re-rated issuers, still short. Two of the loops are one group under two "
      "names (`Nabors Industries, Inc.` and `Ltd.`), and the re-rating of "
      + ", ".join(f"`{o['name']}`" for o in p["objects"].values()
                  if o["loop"] and not o["loop_before_withdrawal"])
      + " comes on or after the day of a withdrawal (section 3). "
      "**Distressed exchanges on this scale are an "
      "event of speculative-grade issuers**: the best rating before the first `RD` "
      "is listed in section 2.\n")
    A("\n## 1. The count, every variant\n")
    A("| series / identity | issuers with `RD` | IG before an `RD` | re-rated after an `RD` | "
      "**loops** | loops, same-day re-rating | loops re-rated before any withdrawal | "
      "by class | exchanges by window |")
    A("|---|---|---|---|---|---|---|---|---|")
    for k, x in a["variants"].items():
        A(f"| {k} | {x['issuers_with_rd']:,} | {x['ig_before_an_rd']:,} | "
          f"{x['rerated_after_an_rd']:,} | **{x['loops']:,}** | {x['loops_same_day']:,} | "
          f"{x['loops_before_withdrawal']:,} | {x['loops_by_class']} | "
          f"{x['loop_exchanges_by_window']} |")
    A("\n## 2. Where the issuers with an `RD` stood before it\n")
    A("The best rating on the long-term IDR before the first `RD`, by row key.\n")
    A("| best rating | issuers |")
    A("|---|---|")
    for s in list(SCALE) + ["none before the first RD"]:
        n = p["best_before_first_rd"].get(s, 0)
        if n:
            A(f"| {s} | {n} |")
    A("\n## 3. The issuers that were investment grade before an `RD`\n")
    A("| class | issuer | exchanges | closes the loop | path on the long-term IDR |")
    A("|---|---|---|---|---|")
    for k, o in sorted(p["objects"].items(), key=lambda kv: (not kv[1]["loop"], kv[1]["name"])):
        A(f"| {o['class']} | {o['name']} | {', '.join(o['rd_dates'])} | "
          f"**{'yes' if o['loop'] else ('same day' if o['loop_same_day'] else 'no')}** | "
          f"{' > '.join(o['path'])} |")
    A("\n## 4. The gate's arithmetic\n")
    A("| | |")
    A("|---|---|")
    A(f"| threshold | {THRESHOLD} |")
    A(f"| issuers with an `RD`, the ceiling | {p['issuers_with_rd']} |")
    A(f"| share the investment-grade screen has to keep | {v['share_needed']:.1%} |")
    A(f"| share it keeps | {v['retained_share']:.1%} |")
    A(f"| largest count over the variants | {v['largest']} |")
    A(f"| what S&P would have to add | {v['needed_from_sp']}, that is "
      f"{v['multiple_of_fitch_needed']:.0f} times Fitch's own count |")
    A("\n## 5. The snapshot on disk\n")
    A("| file | earliest action | latest | rows | before 2012-06-15 | on 2012-06-15 |")
    A("|---|---|---|---|---|---|")
    for k, s in a["spans"].items():
        A(f"| {k} | {s['earliest']} | {s['latest']} | {s['rows']:,} | "
          f"{s['before_rule_start']:,} | {s['on_rule_start']:,} |")
    A("\n## 6. The criteria\n")
    A(kinds_line(cs) + "\n")
    A("| | criterion | kind | detail |")
    A("|---|---|---|---|")
    for c in cs:
        mark = "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "UNDECIDED")
        A(f"| {mark} | {c['name']} | {c['kind']} | {c['detail']} |")
    A("\n## What this does not decide\n")
    A("- **Whether S&P is read.** The registered exit reads it before the gate is "
      "judged; section 4 prints what it would have to supply.")
    A("- **Which domain comes next** if the station stops: that is a separate "
      "registration, with its own selection rule.\n")
    return "\n".join(L) + "\n"


def _dump(obj) -> str:
    def cut(x):
        if isinstance(x, float):
            return float(f"{x:.7g}")
        if isinstance(x, dict):
            return {k: cut(val) for k, val in x.items()}
        if isinstance(x, (list, tuple)):
            return [cut(val) for val in x]
        return x
    return json.dumps(cut(obj), ensure_ascii=False, sort_keys=True, indent=1) + "\n"


#: What each kind of criterion asks, in the words the table below uses.
KIND_ASKS = {
    "instrument": "whether the instrument reads what it claims to",
    "known_answer": "whether known objects read back as known",
    "bookkeeping": "whether what has to be printed is printed",
    "premise": "whether a fact this run relies on holds",
    "own_reading": "about a reading of this station",
    "rival": "whether a rival's point prediction holds",
}
GATE = "B11-C11-0"


def _series(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def kinds_line(criteria: list[dict]) -> str:
    """The sentence above the criteria table, built from the criteria themselves.

    It names criteria and kinds and carries no count: a count typed into this
    line is the one thing on the page that would not follow a criterion added to
    the script.
    """
    def ident(c: dict) -> str:
        # a criterion's name is its identifier followed by what it asks
        return c["name"].split()[0]

    gate = next(c for c in criteria if ident(c) == GATE)
    others = [c for c in criteria if ident(c) != GATE]
    kinds: list[str] = []
    for c in others:
        if c["kind"] not in kinds:
            kinds.append(c["kind"])
    rest = []
    for k in kinds:
        names = [f"`{ident(c)}`" for c in others if c["kind"] == k]
        rest.append(f"{KIND_ASKS[k]} (`{k}`: {_series(names)})")
    line = (f"**The gate, `{GATE}`, is a `{gate['kind']}`**: it asks whether this carrier "
            "holds enough loops, and says nothing about the framework either way.")
    if rest:
        line += " The others ask " + _series(rest) + "."
    if all(c["kind"] != "rival" for c in criteria):
        line += " None is a `rival` criterion."
    return line


def selftest() -> int:
    fails = []
    r = lambda cls, pos, d, rt, lei="", oid="", name="X": {  # noqa: E731
        "class": cls, "pos": pos, "type": "Long Term Issuer Default Rating", "date": d,
        "rating": rt, "action": "", "lei": lei, "obligor_id": oid, "name": name,
        "rowkey": f"legal_entity_identifier:{lei}" if lei else f"obligor_name:{name}"}
    rows = [
        # closes the loop: IG, down, RD, re-rated later
        r("Corporate", 0, "2012-06-15", "BBB", lei="L1", name="One"),
        r("Corporate", 1, "2016-01-01", "CC", lei="L1", name="One"),
        r("Corporate", 2, "2016-02-01", "RD", lei="L1", name="One"),
        r("Corporate", 3, "2016-03-01", "CCC", lei="L1", name="One"),
        # never IG
        r("Corporate", 4, "2013-01-01", "B", lei="L2", name="Two"),
        r("Corporate", 5, "2014-01-01", "RD", lei="L2", name="Two"),
        r("Corporate", 6, "2014-02-01", "B-", lei="L2", name="Two"),
        # IG, RD, re-rated the same day only
        r("Financial", 7, "2012-06-15", "A-", oid="O3", name="Three"),
        r("Financial", 8, "2020-05-01", "RD", oid="O3", name="Three"),
        r("Financial", 9, "2020-05-01", "CCC+", oid="O3", name="Three"),
        # IG only after the RD, which must not count
        r("Insurance", 10, "2015-01-01", "RD", name="Four"),
        r("Insurance", 11, "2018-01-01", "BBB-", name="Four"),
        # one issuer split across an LEI row and a name-only row: the union joins them
        r("Corporate", 12, "2012-06-15", "BBB+", name="Five"),
        r("Corporate", 13, "2019-01-01", "RD", lei="L5", name="Five"),
        r("Corporate", 14, "2019-06-01", "B", lei="L5", name="Five"),
    ]
    ids_row = [f"{x['class']}|{x['rowkey']}" for x in rows]
    per = loops(histories(rows, ids_row, SERIES["LT IDR"]))
    got = sorted(k for k, v in per.items() if v["loop"])
    if got != ["Corporate|legal_entity_identifier:L1"]:
        fails.append(f"row key loops {got}")
    if sum(v["loop_same_day"] for v in per.values()) != 2:
        fails.append("the same-day re-rating is not counted in the loose reading")
    if per["Insurance|obligor_name:Four"]["ig_before"]:
        fails.append("investment grade after the exchange was counted as before it")
    perU = loops(histories(rows, union_ids(rows), SERIES["LT IDR"]))
    if sum(v["loop"] for v in perU.values()) != 2:
        fails.append(f"the union should join Five's two rows and count it: {sum(v['loop'] for v in perU.values())}")
    for f in fails:
        print("FAIL " + f, file=sys.stderr)
    if fails:
        return 1
    print("selftest: ok, the loop needs IG before and a rung after, same-day is apart, "
          "and the union joins a split issuer", file=sys.stderr)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    files = M.pick_files("Fitch", M.CORPORATE_CLASSES)
    if len(files) != 3:
        raise SystemExit(f"expected the three Fitch class files, found {[p.name for p in files]}")
    a = analyse(files)
    v = verdict(a)
    cs = criteria(a, v)
    OUT_MD.write_text(render(a, v, cs), encoding="utf-8", newline="\n")
    record = {"stage": "B11-C11-0",
              "config": {"agency": "Fitch", "classes": list(M.CORPORATE_CLASSES),
                         "threshold": THRESHOLD, "series": SERIES,
                         "investment_grade": list(IG), "scale": list(SCALE)},
              "criteria": cs,
              "report": {"variants": {k: {kk: vv for kk, vv in x.items() if kk != "objects"}
                                      for k, x in a["variants"].items()},
                         "objects": a["variants"]["LT IDR / row key"]["objects"],
                         "verdict": {k: val for k, val in v.items() if k != "counts"},
                         "spans": a["spans"], "unknown_symbols": a["unknown_symbols"]}}
    OUT_JSON.write_text(_dump(record), encoding="utf-8", newline="\n")
    for c in cs:
        mark = "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "UNDECIDED")
        print(f"  {mark} {c['name']}", file=sys.stderr)
    print(f"wrote {OUT_MD}\nwrote {OUT_JSON}", file=sys.stderr)


if __name__ == "__main__":
    main()
