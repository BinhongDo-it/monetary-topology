#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B17c: the same rank measurement, second country. Cuba, CUP against USD.

WHY
===
B17 read `2 <= r <= b1` on Argentina and killed the rival (one brecha factor
plus legislated wedges, which predicts `r = 1`). Its largest exposure is that
it is one country: B5 section 9.3 says so in as many words. B17 section 7.8
names the fix and says the code runs unchanged on Cuba and Bolivia. This is
that run, and it does not change one line of the arithmetic: `panel`,
`daily_changes`, `structural`, `spectrum` and `centered` are imported from
`b17_rank`, so a second country cannot be read by a second piece of code.

WHAT THIS DOES NOT CLAIM
========================
B17's rival is section 5.1's rival, but B17's framework side is weaker. The
identity `r <= b1` is an identity. `r >= 2` rules out a single driver, which a
pure friction story requires; it does NOT rule out friction being one of the
two or more drivers, and section 5.1 forbids exactly that. So this is a
necessary-condition test of the section 5.1 claim, on a second carrier, and a
pass here must not be written up as support for section 5.1.

GATE ZERO, run before a line of this file was written
=====================================================
Cuba publishes three official rates per currency and two informal ones. Two of
the five are dead on arrival, and the reason is arithmetic, not thinness:

  tasaPublica / tasaOficial = 5.000000 exactly, on all 207 days and all 13
      currencies. It is the same track times a constant, so in log daily
      changes it is the same series, contributing nothing.
  tasaOficial for USD takes ONE value, 24.0000, on all 207 days. A series that
      never moves has zero variance and cannot load on anything.

That is the shape the second B17 carrier died of: several "positions" that are
one position. Here it is caught by arithmetic on the published numbers rather
than by a settlement identifier, and it is caught before any criterion is run.

  LIVE:  tasaEspecial (BCC), USD (eltoque informal), USDT_TRC20 (eltoque)
  DEAD:  tasaOficial (frozen), tasaPublica (5x tasaOficial)

  C = 3,  b1 = C - 1 = 2

Bolivia is not opened. Its tracks are the official TCO and the informal ask,
so `C = 2` and `b1 = 1`, and `r <= 1` is then satisfied by anything. Gate zero
fails and no criterion is written. That is a reading, not a postponement.

THE PRE-REGISTRATION
====================
1  CRITERION.  `r` is the rank of the covariance of the zero-sum projected
   daily log changes across the three live tracks.

     rival      one brecha factor loading differently on each track   r = 1
     framework  r <= b1 = 2

   Three-valued, fixed before the run:
     r = 1        the rival is confirmed. FAIL, written as "the rival won",
                  never as "no effect found"
     r = 2        the rival is dead
     r > 2        structural break, code error, the section is void

   b1 = 2 is the smallest value at which this reads anything, and B17 section 5
   says small is what gives it teeth: it makes "r = 2" a statement about two
   thick cycles rather than a factor count on noise.

2  THE GATE NUMBERS.  The joint window is bounded by BCC at about 207 days.
   `spectrum` reports the Z90 resolution `1.645 * lambda * sqrt(2/T)`, which at
   T = 207 is 16.2% of each eigenvalue against 6.1% at Argentina's T = 1456.
   So the two eigenvalues separate only if they differ by more than roughly a
   sixth. Argentina's C5 full window had `lambda2/lambda1 = 0.495` and would
   separate here; its C4 pre window had `0.86` at T = 233 and did NOT separate,
   and was read as undecidable. Both outcomes are therefore live at this T.

3  REACHABILITY.  r = 1 is reachable: two tracks moving together and a third
   scaled would give it. r = 2 is reachable: Argentina produced it at every
   window. The undecidable cell is reachable and has a registered reading.
   No branch is empty.

4  CARRIER AND CONVENTION.  CUP against USD. The eltoque filename is the
   observation date; the payload's `date` field is the fetch timestamp and is
   the SAME value, 2026-08-19, in all 2,069 files on disk, so using it would
   collapse the panel to one day. It is ignored, and a structural check asserts
   that the values themselves are distinct across files. This is the shape B15
   registered as its hard gate: which column is the clock.
"""

import argparse
import ast
import glob
import json
import os
import re
import sys
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "results", "b17c_cuba.json")

#: One reader of the arithmetic. Selftest 1 asserts this file defines none of
#: these itself, so a second country cannot drift into a second construction.
from b17_rank import (centered, daily_changes, panel,            # noqa: E402
                      spectrum, structural)

TRACKS = ["especial", "informal", "usdt"]
DEAD = {"oficial": "frozen at 24.0000 on all 207 days, zero variance",
        "publica": "exactly 5.000000 x tasaOficial, the same series scaled"}


def load_bcc(field="tasaEspecial", code="usd"):
    p = os.path.join(RAW, "bcc_%s.json" % code)
    rows = json.load(open(p, encoding="utf-8"))
    out = {}
    for r in rows:
        v = r.get(field)
        if v is None or v <= 0:
            continue
        y, m, d = (int(x) for x in r["fecha"].split("-"))
        out[date(y, m, d)] = (float(v),)
    return out


def load_eltoque(key="USD"):
    """The FILENAME is the observation date. See the pre-registration, cell 4."""
    #: Only the plain `trmi_YYYY-MM-DD.json`. Twelve dates also carry a
    #: `_HH-MM-SS` re-fetch; those are B6's sensitivity probes, not second
    #: observations, and taking them would silently give twelve days a
    #: different within-day convention from the other 2,047.
    out, payload_dates, vals, probes = {}, set(), set(), 0
    keep = re.compile(r"^trmi_\d{4}-\d\d-\d\d\.json$")
    for p in sorted(glob.glob(os.path.join(RAW, "eltoque", "trmi_*.json"))):
        if not keep.match(os.path.basename(p)):
            probes += 1
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        t = d.get("tasas") or {}
        v = t.get(key)
        if not v or v <= 0:
            continue
        payload_dates.add(d.get("date"))
        vals.add(json.dumps(t, sort_keys=True))
        stamp = os.path.basename(p).split("trmi_")[1][:10]
        y, m, dd = (int(x) for x in stamp.split("-"))
        out[date(y, m, dd)] = (float(v),)
    return out, {"payload_dates": sorted(payload_dates)[:3],
                 "n_payload_dates": len(payload_dates),
                 "n_distinct_tasas": len(vals), "n_days": len(out),
                 "sensitivity_probes_skipped": probes}


def build():
    series = {"especial": load_bcc()}
    inf, m1 = load_eltoque("USD")
    usdt, m2 = load_eltoque("USDT_TRC20")
    series["informal"], series["usdt"] = inf, usdt
    return series, {"informal": m1, "usdt": m2}


def gate_zero():
    """The two dead tracks, re-derived here rather than asserted."""
    rows = json.load(open(os.path.join(RAW, "bcc_usd.json"), encoding="utf-8"))
    ratio = {round(r["tasaPublica"] / r["tasaOficial"], 9) for r in rows}
    frozen = {r["tasaOficial"] for r in rows}
    esp = {r["tasaEspecial"] for r in rows}
    return {"n_days": len(rows), "publica_over_oficial": sorted(ratio),
            "oficial_distinct": sorted(frozen), "especial_distinct": len(esp)}


def run():
    g = gate_zero()
    print("  GATE ZERO, re-derived, not asserted:")
    print("    BCC usd rows            %d" % g["n_days"])
    print("    publica / oficial       %s   -> one track, not two"
          % g["publica_over_oficial"])
    print("    oficial distinct values %s   -> zero variance"
          % g["oficial_distinct"])
    print("    especial distinct values %d  -> live" % g["especial_distinct"])
    for k, why in sorted(DEAD.items()):
        print("    DEAD  %-9s %s" % (k, why))

    series, meta = build()
    print("\n  eltoque clock, the B15-4 shape:")
    for k, m in sorted(meta.items()):
        print("    %-9s %d day(s), %d distinct tasas objects, "
              "%d distinct payload date(s) %s"
              % (k, m["n_days"], m["n_distinct_tasas"], m["n_payload_dates"],
                 m["payload_dates"]))
    print("    the payload date is one constant across every file, so it is the")
    print("    fetch stamp. The filename is the observation date and is used.")

    dates, logs = panel(series, TRACKS)
    keep, d_logs = daily_changes(dates, logs)
    print("\n  panel: %d joint days %s .. %s, %d daily changes, C = %d, b1 = %d"
          % (len(dates), dates[0], dates[-1], d_logs.shape[0], len(TRACKS),
             len(TRACKS) - 1))
    if d_logs.shape[0] < 30:
        print("  too few changes to read a spectrum.")
        return 1

    st = structural(d_logs, TRACKS)
    print("\n  structural checks (about the code, not the world):")
    for k, v in sorted(st.items()):
        if isinstance(v, (int, float, bool, str)):
            print("    %-34s %s" % (k, v))
        else:
            print("    %-34s %s" % (k, json.dumps(v)[:90]))

    sp = spectrum(d_logs, TRACKS)
    print("\n  spectrum:")
    print(json.dumps(sp, indent=2, sort_keys=True, default=float)[:2600])

    n = len(TRACKS)
    P = np.eye(n) - np.ones((n, n)) / n
    obs = np.sort(np.linalg.eigvalsh(np.cov(d_logs @ P, rowvar=False)))[::-1]
    dg = np.diag(np.cov(d_logs, rowvar=False))
    nul = np.sort(np.linalg.eigvalsh(P @ np.diag(dg) @ P))[::-1]
    b1 = n - 1
    print("\n  independent-noise null, the generous version (each track's whole")
    print("  daily-change variance taken as its own noise):")
    print("    observed eigenvalues %s" % np.array2string(obs[:b1], precision=8))
    print("    null     eigenvalues %s" % np.array2string(nul[:b1], precision=8))
    print("    observed l1/l_b1 %.3f   null l1/l_b1 %.3f"
          % (obs[0] / obs[b1 - 1], nul[0] / nul[b1 - 1]))
    print("    lambda2 / lambda1  observed %.4f   null %.4f"
          % (obs[1] / obs[0], nul[1] / nul[0]))

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump({"tracks": TRACKS, "b1": b1, "gate_zero": g, "meta": meta,
               "n_joint_days": len(dates), "n_changes": int(d_logs.shape[0]),
               "first": str(dates[0]), "last": str(dates[-1]),
               "structural": st, "spectrum": sp,
               "observed_eigenvalues": [float(x) for x in obs],
               "null_eigenvalues": [float(x) for x in nul],
               "diagnostic_only": True,
               "diagnostic_reason": "B17c second-country replication; the "
               "station is not closed until the reading is written up"},
              open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True, default=float)
    print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    top = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    chk("1  this file defines no arithmetic of its own; panel, daily_changes, "
        "structural, spectrum and centered all come from b17_rank",
        not (top & {"panel", "daily_changes", "structural", "spectrum",
                    "centered", "relatives", "all_pairs"})
        and any(isinstance(n, ast.ImportFrom) and n.module == "b17_rank"
                and {a.name for a in n.names} >= {"panel", "daily_changes",
                                                  "structural", "spectrum"}
                for n in ast.walk(tree)))
    g = gate_zero()
    chk("2  publica is exactly 5x oficial on every row, so it is one track "
        "(measured %s)" % g["publica_over_oficial"],
        g["publica_over_oficial"] == [5.0])
    chk("3  oficial takes a single value and therefore has zero variance "
        "(measured %s)" % g["oficial_distinct"],
        len(g["oficial_distinct"]) == 1)
    chk("4  especial moves, so the official side contributes exactly one live "
        "track (%d distinct values)" % g["especial_distinct"],
        g["especial_distinct"] > 20)
    _inf, m = load_eltoque("USD")
    chk("5  the eltoque payload date is one constant across all files, so it "
        "is a fetch stamp; using it would collapse the panel to one day",
        m["n_payload_dates"] == 1)
    chk("6  one file per date after the %d sensitivity probes are skipped, and "
        "every day's tasas object is distinct, so the filename clock is sound "
        "(%d objects over %d days)"
        % (m["sensitivity_probes_skipped"], m["n_distinct_tasas"], m["n_days"]),
        m["n_distinct_tasas"] == m["n_days"] and m["n_days"] > 1500
        and m["sensitivity_probes_skipped"] >= 12)
    chk("7  three live tracks give b1 = 2, the smallest value at which the "
        "reading says anything", len(TRACKS) == 3 and len(TRACKS) - 1 == 2)
    chk("8  the docstring registers the criterion, the gate numbers, "
        "reachability and the convention, and says what a pass does NOT mean",
        all(k in (ast.get_docstring(tree) or "")
            for k in ("PRE-REGISTRATION", "GATE ZERO", "REACHABILITY",
                      "DOES NOT CLAIM", "necessary-condition")))
    chk("9  nothing here deletes",
        not [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "attr", getattr(n.func, "id", "")) in
             ("remove", "rmtree", "unlink", "rmdir")])
    print("\n  %d/9" % (9 - len(fails)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.run:
        return run()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
