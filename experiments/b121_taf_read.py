"""B121 arm E, part two: inside one quarter, what the banks on the TAF edge paid for overnight funds
against the banks off it, and whether that difference arrived with the edge.

  price     B59's RC-K reading: the quarter's expense on fed funds purchased and repo over the RC-K
            quarterly average, where repo is absent at both quarter ends (b59_size_spread.arm_rc_k)
  line      the quarter's mean effective federal funds rate (DFF)
  class     Call Report filers matched to a TAF borrower (results/b121_taf_class.json); two writings:
            ever (borrowed at any time), active (the quarter lies between its first and last loan)
  cells     size bands below $10 billion, each band and quarter cut in two by asset rank as in B113;
            in each piece the share paying above the line, outside minus inside, weighted by
            1/(1/n_out + 1/n_in), pooled over pieces and quarters of a span
  spans     before  2007Q2-2007Q3, the TAF not yet announced (2007-12-12)
            during  2008Q1-2009Q4
  floor     filers resampled whole, 2000 draws, two seeds

The rival is one price at the position: sound banks borrowing overnight pay one rate, so no split of
them carries a difference. The framework reads the edge as carrying one, so the difference between
the banks on it and off it changes when the edge opens.

    python experiments/b121_taf_read.py
    python experiments/b121_taf_read.py --selftest
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import b59_size_spread as b59  # noqa: E402

PANEL = ROOT / "data" / "cache" / "b121_call_report.json"
CLASS = ROOT / "results" / "b121_taf_class.json"
DFF = ROOT / "data" / "raw" / "b121" / "DFF.csv"
OUT = ROOT / "results" / "b121_taf_read.json"
SMALL = ("1bn to 10bn", "250m to 1bn", "under 250m")
SPANS = {"before": ("2007Q2", "2007Q3"), "before_wide": ("2007Q2", "2007Q4"), "during": ("2008Q1", "2009Q4")}
DRAWS, SEEDS, LINE, CUTS = 2000, (11, 23), 2.0, 2


def quarter_of(day: str) -> str:
    return f"{day[:4]}Q{(int(day[5:7]) - 1) // 3 + 1}"


def load():
    panel = {p: v["filers"] for p, v in json.loads(PANEL.read_text(encoding="utf-8")).items()}
    rows = b59.arm_rc_k(b59.quarter_rows(panel, "2007Q1", "2010Q2"))
    effr = collections.defaultdict(list)
    for r in csv.reader(DFF.open(encoding="utf-8")):
        if r and r[0][:2] == "20" and r[1] not in ("", "."):
            effr[quarter_of(r[0])].append(float(r[1]))
    effr = {q: statistics.fmean(v) for q, v in effr.items()}
    cls = json.loads(CLASS.read_text(encoding="utf-8"))
    ever = set(cls["class_rssd"])
    active = collections.defaultdict(set)
    for b in cls["borrowers"].values():
        if "rssd" in b:
            q0, q1 = quarter_of(b["first"]), quarter_of(b["last"])
            for q in {r.period for r, _ in rows}:
                if q0 <= q <= q1:
                    active[q].add(b["rssd"])
    obs = [{"q": r.period, "rssd": r.rssd, "band": b59.band_of(r.assets), "assets": r.assets,
            "gap_bp": (c - effr[r.period]) * 100.0} for r, c in rows if r.period in effr]
    return obs, ever, active


def member(o, ever, active, writing):
    return o["rssd"] in ever if writing == "ever" else o["rssd"] in active.get(o["q"], set())


def span_difference(obs, ever, active, span, writing, stat):
    """Outside minus inside, pooled over the pieces of every small band and quarter in the span."""
    lo, hi = SPANS[span]
    cells = collections.defaultdict(list)
    for o in obs:
        if lo <= o["q"] <= hi and o["band"] in SMALL:
            cells[(o["q"], o["band"])].append(o)
    num = den = 0.0
    for key, cell in cells.items():
        cell.sort(key=lambda o: o["assets"])
        for piece in np.array_split(np.arange(len(cell)), CUTS):
            ps = [cell[i] for i in piece]
            ins = [o["gap_bp"] for o in ps if member(o, ever, active, writing)]
            out = [o["gap_bp"] for o in ps if not member(o, ever, active, writing)]
            if not ins or not out:
                continue
            ko, ki = int(np.sum(np.array(out) > 0)), int(np.sum(np.array(ins) > 0))
            if stat == "share above the line":
                d = ko / len(out) - ki / len(ins)
            else:  # log odds, each count moved by a half, as B113 reads it (Haldane 1956; Anscombe 1956)
                d = (np.log((ko + 0.5) / (len(out) - ko + 0.5)) - np.log((ki + 0.5) / (len(ins) - ki + 0.5)))
            w = 1.0 / (1.0 / len(out) + 1.0 / len(ins))
            num += w * d
            den += w
    return num / den if den else None


def boot(obs, ever, active, writing, stat, seed, draws):
    """Resample filers whole, so a bank's quarters travel together."""
    by = collections.defaultdict(list)
    for o in obs:
        by[o["rssd"]].append(o)
    ids = sorted(by)
    rng = np.random.default_rng(seed)
    out = {"before": [], "during": [], "change": []}
    for _ in range(draws):
        pick = rng.choice(len(ids), len(ids), replace=True)
        sample = []
        for k, i in enumerate(pick):
            for o in by[ids[i]]:
                sample.append(dict(o, rssd=f"{ids[i]}#{k}"))
        ev = {f"{ids[i]}#{k}" for k, i in enumerate(pick) if ids[i] in ever}
        ac = collections.defaultdict(set)
        for k, i in enumerate(pick):
            for q, s in active.items():
                if ids[i] in s:
                    ac[q].add(f"{ids[i]}#{k}")
        b = span_difference(sample, ev, ac, "before", "ever", stat)
        d = span_difference(sample, ev, ac, "during", writing, stat)
        if b is not None and d is not None:
            out["before"].append(b)
            out["during"].append(d)
            out["change"].append(d - b)
    return {k: float(np.std(v, ddof=1)) for k, v in out.items()}


def reading(obs, ever, active, writing, stat, seed, draws, before="before"):
    # No bank was borrowing from a facility that did not exist yet, so the span before it is always
    # read on the ever writing; the active writing changes only the span during.
    b = span_difference(obs, ever, active, before, "ever", stat)
    d = span_difference(obs, ever, active, "during", writing, stat)
    se = boot(obs, ever, active, writing, stat, seed, draws)
    return {"before": b, "during": d, "change": d - b,
            "se": se, "during_se": d / se["during"] if se["during"] else None,
            "change_se": (d - b) / se["change"] if se["change"] else None, "seed": seed, "draws": draws}


def sign_state(cells, key):
    vals = [(c["name"], c[key]) for c in cells if c[key] is not None]
    first = vals[0][1] > 0
    off = [n for n, v in vals if (v > 0) != first]
    if off:
        return "turns over", off
    if not any(abs(c[key + "_se"] or 0) >= LINE for c in cells):
        return "nothing clears the floor", []
    return "steady", []


def build_criteria(counts, main, cells, seeds_ok):
    c = {}
    c["B121-20"] = {
        "kind": "instrument",
        "statement": "the class is joined and priced: in every quarter read, some banks in each small band "
                     "are on the edge and some are off it",
        "passed": bool(counts["min_members"] >= 1 and counts["class"] >= 200),
        "detail": f"{counts['class']} filers in the class; members priced per band and quarter "
                  f"{counts['min_members']} to {counts['max_members']}",
    }
    st, off = sign_state(cells, "during")
    if st != "steady":
        v, g, s = None, "unread", f"sign {st}"
    elif abs(main["during_se"]) >= LINE:
        v, g, s = True, "B", "past two se, sign steady"
    else:
        v, g, s = False, "C", "inside two se, sign steady"
    c["B121-21"] = {
        "kind": "rival",
        "statement": "while the TAF ran, the banks off the edge and the banks on it paid differently for "
                     "overnight funds, past two of its own standard errors",
        "passed": v, "state": s, "grid": g,
        "state_map": {"sign turns over": "no verdict, grid unread",
                      "sign nothing clears the floor": "no verdict, grid unread",
                      "past two se, sign steady": "pass, grid B", "inside two se, sign steady": "fail, grid C"},
        "detail": f"outside minus inside {main['during']:+.4f} ({main['during_se']:+.2f} se)"
                  + (f"; the sign turns over on {off}" if off else ""),
        "rival_shape": "point prediction of zero",
        "rival_premise": "sound banks borrowing overnight pay one price at that position",
        "rival_entailment": "a split of sound banks into any two groups carries no difference in that price",
    }
    st2, off2 = sign_state(cells, "change")
    if st2 != "steady":
        v2, s2 = None, f"sign {st2}"
    elif abs(main["change_se"]) >= LINE:
        v2, s2 = True, "past two se, sign steady"
    else:
        v2, s2 = False, "inside two se, sign steady"
    c["B121-22"] = {
        "kind": "own_reading",
        "statement": "the difference arrived with the edge: during the TAF minus before its announcement, "
                     "past two of its own standard errors",
        "passed": v2, "state": s2,
        "state_map": {"sign turns over": "no verdict", "sign nothing clears the floor": "no verdict",
                      "past two se, sign steady": "pass", "inside two se, sign steady": "fail"},
        "detail": f"before {main['before']:+.4f}, during {main['during']:+.4f}, change {main['change']:+.4f} "
                  f"({main['change_se']:+.2f} se)" + (f"; the sign turns over on {off2}" if off2 else ""),
    }
    c["B121-23"] = {
        "kind": "instrument",
        "statement": "two seeds leave both readings in one state, and each moves less than its distance to the line",
        "passed": bool(seeds_ok["ok"]), "detail": seeds_ok["detail"],
    }
    return c


def selftest(obs, ever, active) -> int:
    bad = 0
    counts = {"class": 266, "min_members": 3, "max_members": 20}
    main = {"before": 0.0, "during": 0.2, "change": 0.2, "during_se": 3.0, "change_se": 3.0}
    steady = [{"name": "a", "during": 0.2, "during_se": 3.0, "change": 0.2, "change_se": 3.0}]
    ok = {"ok": True, "detail": "seeded"}
    if build_criteria(dict(counts, min_members=0), main, steady, ok)["B121-20"]["passed"]:
        print("  B121-20 did not fail with an empty cell"); bad += 1
    if build_criteria(counts, dict(main, during_se=0.5), steady, ok)["B121-21"]["passed"] is not False:
        print("  B121-21 did not fail inside two se"); bad += 1
    flip = steady + [{"name": "b", "during": -0.1, "during_se": -1.0, "change": -0.1, "change_se": -1.0}]
    cr = build_criteria(counts, main, flip, ok)
    if cr["B121-21"]["passed"] is not None or cr["B121-21"]["grid"] != "unread" or cr["B121-22"]["passed"] is not None:
        print("  B121-21 or 22 gave a verdict when a setting turned the sign over"); bad += 1
    if build_criteria(counts, dict(main, change_se=0.4), steady, ok)["B121-22"]["passed"] is not False:
        print("  B121-22 did not fail inside two se"); bad += 1
    if build_criteria(counts, main, steady, {"ok": False, "detail": "x"})["B121-23"]["passed"]:
        print("  B121-23 did not fail when the seeds disagreed"); bad += 1
    # The instrument must hear a planted difference and must not invent one where the class is random.
    planted = [dict(o, gap_bp=o["gap_bp"] - (60.0 if o["rssd"] in ever and o["q"] >= "2008Q1" else 0.0))
               for o in obs]
    r = reading(planted, ever, active, "ever", "share above the line", SEEDS[0], 200)
    if r["change_se"] is None or r["change_se"] < LINE:
        print(f"  a planted 60 bp cut for members from 2008 was not heard ({r['change_se']})"); bad += 1
    rng = np.random.default_rng(3)
    ids = sorted({o["rssd"] for o in obs})
    fake = set(rng.choice(ids, len(ever & set(ids)), replace=False))
    r2 = reading(obs, fake, collections.defaultdict(set), "ever", "share above the line", SEEDS[0], 200)
    if r2["change_se"] is not None and abs(r2["change_se"]) >= 3.0:
        print(f"  a class drawn at random read a change of {r2['change_se']:+.2f} se"); bad += 1
    print("selftest: every criterion failed on its planted input, the instrument heard the planted cut, "
          "and a random class read nothing" if not bad else f"selftest: {bad} checks did not behave")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args()
    obs, ever, active = load()
    if args.selftest:
        return 1 if selftest(obs, ever, active) else 0

    per = collections.Counter((o["q"], o["band"]) for o in obs if o["rssd"] in ever and o["band"] in SMALL)
    qs = [q for q in sorted({o["q"] for o in obs}) if "2007Q2" <= q <= "2009Q4"]
    mem = [per.get((q, b), 0) for q in qs for b in SMALL]
    counts = {"class": len(ever), "min_members": min(mem), "max_members": max(mem)}
    print(f"{len(obs):,} priced filer-quarters; class {len(ever)}; members per small band and quarter "
          f"{min(mem)} to {max(mem)}")

    by_seed = {s: reading(obs, ever, active, "ever", "share above the line", s, args.draws) for s in SEEDS}
    for s, r in by_seed.items():
        print(f"  seed {s}: before {r['before']:+.4f}  during {r['during']:+.4f} ({r['during_se']:+.2f} se)  "
              f"change {r['change']:+.4f} ({r['change_se']:+.2f} se)")
    main_read = by_seed[SEEDS[0]]
    parts, ok = [], True
    for k in ("during_se", "change_se"):
        a, b = (by_seed[s][k] for s in SEEDS)
        gap, dist = abs(a - b), abs(abs((a + b) / 2) - LINE)
        ok = ok and ((abs(a) >= LINE) == (abs(b) >= LINE)) and gap < dist
        parts.append(f"{k}: {a:+.2f} and {b:+.2f}, moved {gap:.3f}, stands {dist:.3f} from the line")
    seeds_ok = {"ok": bool(ok), "detail": "; ".join(parts)}

    cells = []
    for writing in ("ever", "active"):
        for stat in ("share above the line", "log odds"):
            for before in ("before", "before_wide"):
                r = reading(obs, ever, active, writing, stat, SEEDS[0], max(400, args.draws // 4), before)
                cells.append({"name": f"{writing}|{stat}|{before}", "before": r["before"], "during": r["during"],
                              "during_se": r["during_se"], "change": r["change"], "change_se": r["change_se"]})
                print(f"  {writing:<6} {stat:<20} {before:<11} before {r['before']:+.4f}  during {r['during']:+.4f} "
                      f"({r['during_se']:+.2f} se)  change {r['change']:+.4f} ({r['change_se']:+.2f} se)")
    criteria = build_criteria(counts, main_read, cells, seeds_ok)
    print()
    for n, cr in criteria.items():
        flag = {True: "PASS", False: "FAIL", None: "no verdict"}[cr["passed"]]
        print(f"{flag:<10} {n} [{cr['kind']}] {cr['detail']}")
    record = {"stage": "B121",
              "config": {"draws": args.draws, "seeds": list(SEEDS), "spans": SPANS, "bands": list(SMALL),
                         "cuts": CUTS, "statistic": "share above the line", "class_writing": "ever"},
              "source": {"price": "Call Report RC-K and RI 4180, read by b59_size_spread.arm_rc_k",
                         "class": "results/b121_taf_class.json", "line": "FRED DFF, quarter mean"},
              "readings": {"by_seed": by_seed, "knobs": cells, "seeds": seeds_ok, "counts": counts},
              "criteria": [dict(v, name=k) for k, v in criteria.items()],
              "diagnostic_only": True,
              "diagnostic_reason": "Arm E of B121; the station has other arms open."}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0 if all(v["passed"] is not False for v in criteria.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
