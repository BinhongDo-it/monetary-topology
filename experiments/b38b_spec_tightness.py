"""B38b: is the residual an obstruction, or is it the same name meaning different things?

B38 measured the residual of the city-by-item log price field against the best
scalar potential, and found it large and high-dimensional. The reading is that
the obstruction is not low-dimensional. **The confound that reading has to
survive is not agent error, it is item non-comparability**: a cappuccino in Oslo
and a cappuccino in Lagos are not the same object, and a residual made of that
is a mis-specified edge rather than a non-closing field.

Agent error does not sit in the same place. Independent error averages out and
carries a known spectral signature, which B38-2 already checked against
synthetic data. Correlated error -- everyone in a city using one shared rule --
does not average out, but it is not a confound either: a field that fails to
close because of a shared heuristic is a field that fails to close, and this
framework never assumed anyone was optimising. So the whole weight falls on
non-comparability, and that is what this station tests.

**The discriminant needs two axes, because one will not do.** Tightly specified
items also tend to be tradeable, and arbitrage in tradeables predicts a small
residual for the same rows that quality bias does. Crossed:

    quality bias predicts the residual tracks LOOSE
    arbitrage     predicts the residual tracks TRADEABLE
    a structural obstruction predicts it tracks neither strongly

**The assignment below is made from each item's own description**, on the two
questions "is the physical object pinned by the name" and "can the good itself
move between cities", and is written out in full so any row can be re-argued.

Run:
    python experiments\\b38b_spec_tightness.py
"""

import csv
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "b30_5" / "column_map.json"
OUT = ROOT / "results" / "b38b_spec_tightness.json"

# TIGHT: the name pins a physical object a buyer could not substitute.
# TRADED: the good itself can move between cities and be resold.
SPEC = {
    # tight and traded
    "Volkswagen Golf 1.5": ("TIGHT", "TRADED"),
    "Toyota Corolla Sedan 1.6": ("TIGHT", "TRADED"),
    "Jeans (Levi's 501": ("TIGHT", "TRADED"),
    "Nike Running Shoes": ("TIGHT", "TRADED"),
    "Cigarettes (Pack of 20, Marlboro)": ("TIGHT", "TRADED"),
    "Milk (Regular, 1 Liter)": ("TIGHT", "TRADED"),
    "Eggs (12, Large Size)": ("TIGHT", "TRADED"),
    "White Rice (1 lb)": ("TIGHT", "TRADED"),
    "Apples (1 lb)": ("TIGHT", "TRADED"),
    "Bananas (1 lb)": ("TIGHT", "TRADED"),
    "Oranges (1 lb)": ("TIGHT", "TRADED"),
    "Potatoes (1 lb)": ("TIGHT", "TRADED"),
    "Onions (1 lb)": ("TIGHT", "TRADED"),
    "Tomatoes (1 lb)": ("TIGHT", "TRADED"),
    # tight and not traded: the specification pins the object, but the object
    # cannot be carried to another city and sold there
    "Gasoline (1 Liter)": ("TIGHT", "LOCAL"),
    "One-Way Ticket (Local Transport)": ("TIGHT", "LOCAL"),
    "Monthly Public Transport Pass": ("TIGHT", "LOCAL"),
    "Taxi Start (Standard Tariff)": ("TIGHT", "LOCAL"),
    "Taxi 1 mile (Standard Tariff)": ("TIGHT", "LOCAL"),
    "Taxi 1 Hour Waiting": ("TIGHT", "LOCAL"),
    "Combo Meal at McDonald's": ("TIGHT", "LOCAL"),
    "Soft Drink (Coca-Cola or Pepsi": ("TIGHT", "LOCAL"),
    "Bottled Water (12 oz)": ("TIGHT", "LOCAL"),
    "Bottled Water (50 oz)": ("TIGHT", "LOCAL"),
    "Domestic Beer (16.9 oz Bottle)": ("TIGHT", "LOCAL"),
    "Broadband Internet": ("TIGHT", "LOCAL"),
    # loose and traded
    "Men's Leather Business Shoes": ("LOOSE", "TRADED"),
    "Summer Dress in a Chain Store": ("LOOSE", "TRADED"),
    "Bottle of Wine (Mid-Range)": ("LOOSE", "TRADED"),
    "Local Cheese (1 lb)": ("LOOSE", "TRADED"),
    "Chicken Fillets (1 lb)": ("LOOSE", "TRADED"),
    "Beef Round or Equivalent": ("LOOSE", "TRADED"),
    "Fresh White Bread": ("LOOSE", "TRADED"),
    "Lettuce (1 Head)": ("LOOSE", "TRADED"),
    "Imported Beer (12 oz Small Bottle)": ("LOOSE", "TRADED"),
    # loose and not traded
    "Meal at an Inexpensive Restaurant": ("LOOSE", "LOCAL"),
    "Meal for Two at a Mid-Range Restaurant": ("LOOSE", "LOCAL"),
    "Domestic Draft Beer (1 Pint)": ("LOOSE", "LOCAL"),
    "Cappuccino (Regular Size)": ("LOOSE", "LOCAL"),
    "Monthly Fitness Club Membership": ("LOOSE", "LOCAL"),
    "Tennis Court Rental": ("LOOSE", "LOCAL"),
    "Cinema Ticket (International Release)": ("LOOSE", "LOCAL"),
    "Private Full-Day Preschool": ("LOOSE", "LOCAL"),
    "International Primary School": ("LOOSE", "LOCAL"),
    "1 Bedroom Apartment in City Centre": ("LOOSE", "LOCAL"),
    "1 Bedroom Apartment Outside": ("LOOSE", "LOCAL"),
    "3 Bedroom Apartment in City Centre": ("LOOSE", "LOCAL"),
    "3 Bedroom Apartment Outside": ("LOOSE", "LOCAL"),
    "Price per Square Feet to Buy Apartment in City": ("LOOSE", "LOCAL"),
    "Price per Square Feet to Buy Apartment Outside": ("LOOSE", "LOCAL"),
    "Basic Utilities for 915 Square Feet": ("LOOSE", "LOCAL"),
    "Average Monthly Net Salary": ("LOOSE", "LOCAL"),
}


def value(raw):
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def classify(item):
    tail = item.split(" :: ")[-1]
    for k, v in SPEC.items():
        if tail.startswith(k) or k in tail:
            return v
    return (None, None)


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    cols = [c for c, m in spec["mapping"].items()
            if m.get("agrees") and "in %" not in m["item"].lower()]
    items = [spec["mapping"][c]["item"] for c in cols]
    rows = list(csv.DictReader(
        (ROOT / spec["source_file"]).open(encoding="utf-8-sig", newline="")))
    full = [r for r in rows if all(value(r[c]) for c in cols)]
    M = np.log(np.array([[value(r[c]) for c in cols] for r in full],
                        dtype=float)).T
    a = M.mean(axis=1, keepdims=True)
    b = (M - a).mean(axis=0, keepdims=True)
    R = M - a - b

    print("=" * 78)
    print("B38b: does the residual track loose specification, or tradeability,")
    print("      or neither")
    print("=" * 78)
    print("  %d items on %d complete cities" % M.shape[::1])

    recs, unclassified = [], []
    for k, it in enumerate(items):
        tight, traded = classify(it)
        if tight is None:
            unclassified.append(it)
            continue
        recs.append({"item": it, "spec": tight, "trade": traded,
                     "resid_sd": float(R[k].std())})
    if unclassified:
        print("\n  items with no assignment, named rather than dropped:")
        for it in unclassified:
            print("    %s" % it.split(" :: ")[-1][:60])

    print("\n  every item's residual sd, printed so any row can be re-argued")
    print("  %-52s %-6s %-7s %s" % ("item", "spec", "trade", "resid sd"))
    for r in sorted(recs, key=lambda r: -r["resid_sd"]):
        print("  %-52s %-6s %-7s %8.4f"
              % (r["item"].split(" :: ")[-1][:52], r["spec"], r["trade"],
                 r["resid_sd"]))

    print("\n" + "=" * 78)
    print("the 2x2, medians of the per-item residual sd")
    print("=" * 78)
    cells = {}
    for s in ("TIGHT", "LOOSE"):
        for t in ("TRADED", "LOCAL"):
            v = [r["resid_sd"] for r in recs
                 if r["spec"] == s and r["trade"] == t]
            cells[(s, t)] = (st.median(v) if v else None, len(v))
    print("  %-8s %18s %18s" % ("", "TRADED", "LOCAL"))
    for s in ("TIGHT", "LOOSE"):
        row = []
        for t in ("TRADED", "LOCAL"):
            m, n = cells[(s, t)]
            row.append("%8.4f  (n %2d)" % (m, n) if m else "      -")
        print("  %-8s %18s %18s" % (s, row[0], row[1]))

    def med(f):
        v = [r["resid_sd"] for r in recs if f(r)]
        return st.median(v), len(v)
    mt, nt = med(lambda r: r["spec"] == "TIGHT")
    ml, nl = med(lambda r: r["spec"] == "LOOSE")
    mtr, ntr = med(lambda r: r["trade"] == "TRADED")
    mlo, nlo = med(lambda r: r["trade"] == "LOCAL")
    print("\n  margins")
    print("    TIGHT  %.4f (n %d)   LOOSE %.4f (n %d)   ratio LOOSE/TIGHT %.2f"
          % (mt, nt, ml, nl, ml / mt))
    print("    TRADED %.4f (n %d)   LOCAL %.4f (n %d)   ratio LOCAL/TRADED %.2f"
          % (mtr, ntr, mlo, nlo, mlo / mtr))
    print("\n  the reading, and no threshold is registered on either ratio:")
    print("    quality bias predicts the residual tracks LOOSE")
    print("    arbitrage    predicts it tracks TRADED")
    print("    a structural obstruction predicts neither carries it")
    print("\n  the cell that separates them is TIGHT and LOCAL: pinned to an")
    print("  object, and not arbitrageable. Quality bias predicts it small,")
    print("  arbitrage predicts it large.")
    tl, ntl = cells[("TIGHT", "LOCAL")]
    tt, _ = cells[("TIGHT", "TRADED")]
    ll, _ = cells[("LOOSE", "LOCAL")]
    print("    TIGHT+LOCAL  %.4f    TIGHT+TRADED %.4f    LOOSE+LOCAL %.4f"
          % (tl, tt, ll))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"items": recs, "unclassified": unclassified,
         "cells": {"%s_%s" % k: {"median": v[0], "n": v[1]}
                   for k, v in cells.items()},
         "margins": {"tight": mt, "loose": ml, "traded": mtr, "local": mlo}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
