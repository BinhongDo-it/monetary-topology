"""B37-3 and B37-4: during a freeze, did the world move, and how did it end.

B37-2 found five series whose quote goes flat for far longer than the seven day
floor. A flat quote has two possible causes and they are opposite: the pipe to
the source went stale, or the thing being quoted genuinely did not move. This
stage separates them, and the separation needs a referee that is not one of the
publishers under test.

The referee is BCRA Comunicación A 3500, the central bank's own reference rate,
already on disk from B5's retrieval. It is not a publisher of someone else's
number; it is the number. Where a series has no A 3500 analogue an Ámbito series
stands in, and that is labelled a proxy rather than a referee.

The yardstick, and it invents no constant. For a freeze of n published days,
the referee's move over those same dates is compared against the distribution of
its move over every n-day window in the sample. A freeze that landed on a
genuinely quiet stretch sits in the low tail; a freeze whose world was moving
normally sits near the middle. The percentile is printed and read, rather than a
line being drawn on it.

B37-4 then asks how the freeze ended. If the first move after it is about the
size of the whole gap the referee opened, the copy was frozen and then resynced
in one step. If it is much smaller, the copy had partial information all along
and was drifting rather than frozen. Those are different mechanisms and the
registered criterion forbids merging them.

Criteria: registered for this arm, and the result file section R2.

Run:
    python b37_step1_freeze.py
"""

import argparse
import io
import json
import math
import statistics
from pathlib import Path

from monetary_topology.parallel_rates import (
    ALL_AMBITO,
    WINDOW_END,
    WINDOW_START,
    load_bcra_reference,
    load_series,
    mid_of,
    parse_argentinadatos_rows,
)

FLOOR_DAYS = 7          # B37-1, measured, not chosen
MIN_FREEZE = 8          # anything at or below the floor is not a freeze

#: Which referee judges which series, and whether it is a referee or a proxy.
REFEREE = {
    "oficial":   ("bcra", "A 3500, the central bank's own reference"),
    "mayorista": ("bcra", "A 3500; mayorista is the interbank rate beside it"),
    "blue":      ("ambito:informal", "the other publisher of the same market"),
    "cripto":    ("ambito:ccl", "PROXY, not the same instrument"),
    "tarjeta":   ("bcra", "PROXY, tarjeta is oficial times a tax"),
}


def ambito_daily(raw: Path, key: str):
    _, fields = ALL_AMBITO[key]
    return {r["date"]: mid_of(r, fields) for r in load_series(raw, key)}


def argdatos_daily(raw: Path, casa: str):
    p = raw / ("argentinadatos_%s.json" % casa)
    if not p.exists():
        return None
    out = {}
    for r in parse_argentinadatos_rows(json.loads(p.read_text(encoding="utf-8")),
                                       casa):
        c, v = r.get("compra"), r.get("venta")
        if c and v and c > 0 and v > 0:
            out[r["date"]] = (c * v) ** 0.5
        elif v and v > 0:
            out[r["date"]] = float(v)
    return out


def in_window(d):
    a, b = WINDOW_START.isoformat(), WINDOW_END.isoformat()
    return {k: v for k, v in d.items() if a <= k <= b}


def freezes(daily):
    dates = sorted(daily)
    out = []
    i = 0
    while i < len(dates):
        j = i
        while j + 1 < len(dates) and daily[dates[j + 1]] == daily[dates[i]]:
            j += 1
        n = j - i + 1
        if n >= MIN_FREEZE:
            out.append({"days": n, "first": dates[i], "last": dates[j],
                        "value": daily[dates[i]],
                        "next": dates[j + 1] if j + 1 < len(dates) else None})
        i = j + 1
    return out


def move(ref, a, b):
    """log ref(b) / ref(a), on the nearest available dates at or inside [a, b]."""
    ks = sorted(k for k in ref if a <= k <= b)
    if len(ks) < 2:
        return None, None, None
    return math.log(ref[ks[-1]] / ref[ks[0]]), ks[0], ks[-1]


def window_moves(ref, n):
    """|log move| over every n-row window of the referee. The yardstick."""
    ks = sorted(ref)
    out = []
    for i in range(len(ks) - n):
        try:
            out.append(abs(math.log(ref[ks[i + n]] / ref[ks[i]])))
        except (ValueError, ZeroDivisionError):
            pass
    return sorted(out)


def own_daily_step(daily):
    """Median absolute daily log move on the days this series is not frozen.

    This is the registered floor. The design file asks whether the referee's
    move over a freeze is small against this, and the first version of the
    script asked a different question instead: where the freeze sat in the
    referee's own distribution of same-length moves. Those read differently.
    A percentile asks whether the window was unusual for the referee; the
    registered criterion asks whether the referee moved enough that a flat
    quote is a fault. On the seventy-one day freeze the referee moved 4.6 per
    cent, which is unremarkable for that length and still far more than a live
    quote could sit through. The percentile is kept and printed, with no
    verdict on it.
    """
    ks = sorted(daily)
    steps = []
    for i in range(1, len(ks)):
        a, b = daily[ks[i - 1]], daily[ks[i]]
        if a > 0 and b > 0 and a != b:
            steps.append(abs(math.log(b / a)))
    return statistics.median(steps) if steps else None


def pct(sorted_vals, x):
    lo = sum(1 for v in sorted_vals if v < x)
    return lo / len(sorted_vals) if sorted_vals else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    raw = root / "data" / "raw"

    bcra = in_window(load_bcra_reference(raw))
    amb = {k: in_window(ambito_daily(raw, k)) for k in ALL_AMBITO}
    print("=" * 78)
    print("B37-3 and B37-4. Referee: BCRA A 3500, %d dates on disk in window"
          % len(bcra))
    print("floor from B37-1: %d days. A freeze is %d days or more."
          % (FLOOR_DAYS, MIN_FREEZE))
    print("=" * 78)

    rec = {"floor_days": FLOOR_DAYS, "min_freeze": MIN_FREEZE, "series": {}}
    for casa, (ref_key, note) in REFEREE.items():
        daily = argdatos_daily(raw, casa)
        if daily is None:
            print("\nargentinadatos %s: not on disk, named not skipped" % casa)
            continue
        daily = in_window(daily)
        ref = bcra if ref_key == "bcra" else amb.get(ref_key.split(":", 1)[1], {})
        fz = freezes(daily)
        print("\n" + "-" * 78)
        print("argentinadatos %s   referee %s" % (casa, ref_key))
        print("  %s" % note)
        if not fz:
            print("  no freeze at or above %d days. Nothing to judge here."
                  % MIN_FREEZE)
            rec["series"][casa] = {"freezes": 0, "referee": ref_key}
            continue
        rows = []
        for f in sorted(fz, key=lambda x: -x["days"])[:4]:
            m, k0, k1 = move(ref, f["first"], f["last"])
            if m is None:
                print("  %4d days %s to %s: the referee has under two dates "
                      "inside. Not judged." % (f["days"], f["first"], f["last"]))
                continue
            yard = window_moves(ref, f["days"])
            p = pct(yard, abs(m))
            # B37-4: the first move after the freeze, against the gap opened
            step = None
            if f["next"] and f["next"] in daily:
                step = math.log(daily[f["next"]] / f["value"])
            print("\n  %4d days  %s to %s  frozen at %.4f"
                  % (f["days"], f["first"], f["last"], f["value"]))
            print("      referee moved %+.4f over %s to %s"
                  % (m, k0, k1))
            print("      that is the %.0fth percentile of its own %d-day moves "
                  "(median %.4f)" % (p * 100, f["days"],
                                     statistics.median(yard) if yard else float("nan")))
            # The registered reading: the referee's move against this series'
            # own daily step. A quote that cannot sit through one day's move
            # cannot sit through many of them.
            step0 = own_daily_step(daily)
            ratio = abs(m) / step0 if step0 else float("inf")
            print("      this series' own median daily move %.5f, so the "
                  "referee moved %.0f of them" % (step0 or float("nan"), ratio))
            print("      REGISTERED READING: %s"
                  % ("the world moved far more than this quote's own step, so "
                     "the pipe was frozen" if ratio >= 3.0 else
                     "the world moved no more than this quote's own step, so "
                     "the world was quiet too and this one does not carry"))
            if step is not None:
                # The ratio is unstable when the gap is near zero: tarjeta's
                # nine and eleven day freezes gave 6.55 and -0.80 off gaps of
                # 0.002 and 0.004, which carry nothing. So it is reported only
                # where the gap is itself above this series' daily step.
                if step0 and abs(m) < 3.0 * step0:
                    print("      B37-4: not read. The gap the referee opened "
                          "(%+.4f) is inside this series' own daily step, so "
                          "the ratio would divide by noise." % m)
                else:
                    print("      B37-4: first move after it %+.4f, which is "
                          "%.2f of the gap the referee opened"
                          % (step, step / m if m else float("nan")))
                    print("             %s"
                          % ("one step, so it was frozen and then resynced"
                             if m and abs(step / m) > 0.6 else
                             "a fraction, so it was drifting rather than frozen"))
            rows.append({"days": f["days"], "first": f["first"],
                         "last": f["last"], "value": f["value"],
                         "referee_move": m, "percentile": p,
                         "yard_median": statistics.median(yard) if yard else None,
                         "own_daily_step": step0,
                         "referee_over_own_step": ratio,
                         "first_move_after": step,
                         "step_over_gap": (step / m) if (step is not None and m) else None})
        rec["series"][casa] = {"freezes": len(fz), "referee": ref_key,
                               "note": note, "longest": rows}

    print("\n" + "=" * 78)
    print("Both readings are per freeze. The percentile is printed rather than")
    print("cut at a line: a freeze low in the referee's own distribution is a")
    print("quiet world, one near the middle is a stale pipe, and the numbers")
    print("above say which each one is.")
    out = Path(a.out) if a.out else root / "results" / "b37_freeze.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
