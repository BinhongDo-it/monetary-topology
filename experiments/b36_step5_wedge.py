"""B36-11: one shock, two graphs, and the discriminator is duration.

What the framework says. A tariff is rate limiting: it acts on the weight of an
edge. A withdrawn registration is quantity limiting with the bound at zero: it
deletes the edge and leaves the weight untouched. If that split is real then one
shock leaves two marks, and each mark should trace the duration of its own
cause, not the other's. Both durations come from documents:

    tariff, plus ten per cent      2025-03-10 to 2025-11-10    8 months
    registration withdrawn         2025-03    to 2026-05-15   14 months

They differ by six months and the difference sits at the end, which makes the
test clean. Between 2025-11 and 2026-05 the tariff is gone and the registration
is still gone. The quantity floor is known to persist through that stretch. The
question is whether the price wedge does.

The wedge, per ten digit line so that a change in the mix cannot pose as a
change in price:

    w(line, month) = log[ unit value to China / unit value to everywhere else ]
    unit value     = ALL_VAL_MO / QTY_1_MO
    everywhere else = the all countries record minus the China record

Criteria are in the B36 result file, section R19, with the windows fixed in
R20.5, both written before this ran.

Run:
    python b36_step5_wedge.py
"""

import argparse
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

FLOOR_SHARE = 0.05      # a line-month is read only above this share of its own
BASE_YEAR = 2024        # 2024 monthly mean, so the floor is relative per line
WINDOWS = [
    ("pre, nothing on", "2024-01", "2025-02"),
    ("tariff on, registration off", "2025-04", "2025-10"),
    ("TARIFF OFF, registration off", "2025-11", "2026-04"),
    ("both off", "2026-06", "2026-06"),
]


def months(a, b):
    ya, ma = int(a[:4]), int(a[5:])
    yb, mb = int(b[:4]), int(b[5:])
    out = []
    while (ya, ma) <= (yb, mb):
        out.append("%04d-%02d" % (ya, ma))
        ma += 1
        if ma == 13:
            ma, ya = 1, ya + 1
    return out


def load(src: Path, label):
    if not src.exists():
        raise SystemExit("not on disk: %s" % src)
    recs = json.loads(io.open(src, encoding="utf-8").read())
    names = sorted({(r.get("CTY_NAME") or "").strip() for r in recs})
    if len(names) != 1:
        raise SystemExit("%s holds %d destination buckets, expected one"
                         % (src.name, len(names)))
    v = defaultdict(float)
    q = defaultdict(float)
    for r in recs:
        k = (str(r.get("E_COMMODITY") or "?"),
             "%04d-%02d" % (int(r["_year"]), int(r["_month"])))
        try:
            v[k] += float(str(r.get("ALL_VAL_MO") or 0).replace(",", ""))
            q[k] += float(str(r.get("QTY_1_MO") or 0).replace(",", ""))
        except ValueError:
            pass
    print("%s: %d rows, bucket %r, %d line-months" % (label, len(recs),
                                                      names[0], len(v)))
    return v, q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--hs", nargs="*", default=["0201", "0202"],
                    help="HS heads, must match an existing pair of records")
    ap.add_argument("--reopening", action="store_true",
                    help="also print the wedge and the tonnage by month since "
                         "each reopening of this lane, for B36-13")
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    res = root / "results"

    tag = "-".join(a.hs)
    print("=" * 74)
    print("the price wedge, per ten digit line, heads %s" % tag)
    print("=" * 74)
    vt, qt = load(res / ("b35_census_raw_%s_total.json" % tag), "all countries")
    vc, qc = load(res / ("b35_census_raw_%s_5700.json" % tag), "China      ")

    lines = sorted({k[0] for k in vt})
    allm = months("2016-01", "2026-06")

    # The floor is relative to each line's own 2024 level, so a big line and a
    # small line are held to the same standard rather than to the same tonnage.
    base = {}
    for ln in lines:
        ms = [qc.get((ln, m), 0.0) for m in months("%d-01" % BASE_YEAR,
                                                   "%d-12" % BASE_YEAR)]
        base[ln] = sum(ms) / 12.0

    kept = defaultdict(list)     # month -> [(line, w, kg)]
    dropped_kg = defaultdict(float)
    kept_kg = defaultdict(float)
    for ln in lines:
        for m in allm:
            cq, cv = qc.get((ln, m), 0.0), vc.get((ln, m), 0.0)
            oq = qt.get((ln, m), 0.0) - cq
            ov = vt.get((ln, m), 0.0) - cv
            if cq <= 0 or oq <= 0 or cv <= 0 or ov <= 0:
                dropped_kg[m] += max(cq, 0.0)
                continue
            if base[ln] > 0 and cq < FLOOR_SHARE * base[ln]:
                dropped_kg[m] += cq
                continue
            kept[m].append((ln, math.log((cv / cq) / (ov / oq)), cq))
            kept_kg[m] += cq

    print("\nthe floor drops line-months below %.0f%% of that line's own %d "
          "monthly mean. Dropped quantity is named, not passed over."
          % (FLOOR_SHARE * 100, BASE_YEAR))
    tot_k = sum(kept_kg.values())
    tot_d = sum(dropped_kg.values())
    print("  kept %.0f t, dropped %.0f t, dropped share %.4f"
          % (tot_k / 1e3, tot_d / 1e3, tot_d / (tot_k + tot_d)))

    def wbar(m):
        rows = kept.get(m, [])
        wq = sum(kg for _, _, kg in rows)
        if not rows or wq <= 0:
            return None, 0
        return sum(w * kg for _, w, kg in rows) / wq, len(rows)

    print("\n" + "=" * 74)
    print("monthly wedge, quantity weighted across lines")
    print("=" * 74)
    print("  %-9s %10s %6s %14s" % ("month", "w", "lines", "China kg kept"))
    for m in months("2024-01", "2026-06"):
        w, n = wbar(m)
        print("  %-9s %10s %6d %14.1f"
              % (m, "%.4f" % w if w is not None else "     -", n,
                 kept_kg.get(m, 0.0) / 1e3))

    print("\n" + "=" * 74)
    print("by window. The pre window also gives the dispersion the rest is read")
    print("against, and it is a log dispersion (failure mode 118)")
    print("=" * 74)
    rec = {"floor_share": FLOOR_SHARE, "windows": {}}
    pre_sd = None
    for label, a0, b0 in WINDOWS:
        ws = [wbar(m)[0] for m in months(a0, b0)]
        ws = [x for x in ws if x is not None]
        if not ws:
            print("  %-30s no readable month" % label)
            rec["windows"][label] = None
            continue
        mu = statistics.mean(ws)
        sd = statistics.pstdev(ws) if len(ws) > 1 else 0.0
        if pre_sd is None:
            pre_sd = sd
        z = (mu - rec["windows"].get("pre, nothing on", {}).get("mean", mu)) / \
            pre_sd if (pre_sd and rec["windows"].get("pre, nothing on")) else 0.0
        print("  %-30s n %2d  mean w %+.4f  sd %.4f  %s"
              % (label, len(ws), mu, sd,
                 "" if not rec["windows"].get("pre, nothing on")
                 else "%+.2f pre-sd from the pre window" % z))
        rec["windows"][label] = {"n": len(ws), "mean": mu, "sd": sd,
                                 "z_vs_pre": z}

    print("\n" + "=" * 74)
    print("the reading")
    print("=" * 74)
    pre = rec["windows"].get("pre, nothing on")
    off = rec["windows"].get("TARIFF OFF, registration off")
    on = rec["windows"].get("tariff on, registration off")
    if not (pre and off and on):
        v = "UNDECIDED, a window has no readable month"
    elif abs(off["z_vs_pre"]) <= 1.0 and abs(on["z_vs_pre"]) > 1.0:
        v = ("TWO GRAPHS SEPARATE. The wedge moves while the tariff is on and "
             "is back within the pre window's own spread once it is off, while "
             "the quantity floor runs six months longer.")
    elif abs(off["z_vs_pre"]) > 1.0:
        v = ("NOT SEPARATE on this carrier. The wedge is still away from the "
             "pre window after the tariff came off, so the withdrawn "
             "registration moved the weight as well as the edge.")
    else:
        v = ("UNDECIDED. The wedge does not move even while the tariff is on, "
             "so this instrument does not see the rate channel at all.")
    print("  " + v)
    print("\n  Quantity, for contrast, is read in R13 and R20: the floor lasts")
    print("  fourteen months and tracks the registration, not the tariff.")

    if a.reopening:
        # B36-13. Deleting an edge does not delete what past traffic built on
        # it, and the information graph never closed at all, so the speed of a
        # reopening reads that stock. This lane has reopened twice, after a
        # fourteen year closure and after a fourteen month one.
        print("\n" + "=" * 74)
        print("B36-13: two reopenings of the same lane")
        print("=" * 74)
        for label, first, shut in (("2017-06, after 14 years", "2017-06", "14 y"),
                                   ("2026-06, after 14 months", "2026-06", "14 mo")):
            print("\n  %s (closed %s)" % (label, shut))
            print("    %-6s %-9s %12s %10s" % ("k", "month", "tonnes", "w"))
            ms = [m for m in months(first, "2026-06")][:15]
            for k, m in enumerate(ms, 1):
                w, _ = wbar(m)
                kg = sum(qc.get((ln, m), 0.0) for ln in lines)
                print("    %-6d %-9s %12.1f %10s"
                      % (k, m, kg / 1e3, "%+.4f" % w if w is not None else "-"))
        pre = rec["windows"].get("pre, nothing on")
        if pre:
            print("\n  the plateau to converge to is the pre window mean, "
                  "%+.4f" % pre["mean"])
            print("  A reopening that lands on it in one month is a stock that")
            print("  survived; one that takes many months is a stock that did not.")

    rec["verdict"] = v
    rec["heads"] = a.hs
    out = Path(a.out) if a.out else res / ("b36_wedge_%s.json" % tag)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
