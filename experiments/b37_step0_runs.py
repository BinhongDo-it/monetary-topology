"""B37-1 and B37-2: how long a published quote goes without changing.

The object, and where it came from. B5's calibration arm tried to pair Ámbito's
wholesale rate against argentinadatos' and found the premise false: on the
December 2023 devaluation Ámbito and the central bank both jump from about 365
to about 800 while argentinadatos sits at 365.45 for weeks, its longest run of
an unchanged sell quote being seventy-one days against thirteen for its own card
series. B5 changed arms and moved on. This stage takes that failure as its
subject.

A publisher whose link to its source has gone stale does not fall silent. It
keeps emitting a number, at full amplitude, and the number is simply no longer
about anything. So the length of a run of an unchanged quote reads how long a
copy has been unanchored, and it reads it on one series at a time without
needing a second publisher to agree with.

Order, and it is the registered one. B37-1 measures the floor on a series that
has been shown independently to track its source, and nothing else is read until
that floor exists. B37-2 then reads every other series against it. B37-3 and
B37-4 need a freeze to exist before they have an object, so they are not here.

Criteria are registered for this arm.

Run:
    python b37_step0_runs.py
"""

import argparse
import io
import json
import statistics
from pathlib import Path

from monetary_topology.parallel_rates import (
    ALL_AMBITO,
    WINDOW_END,
    WINDOW_START,
    load_series,
    mid_of,
    parse_argentinadatos_rows,
)

# The floor series: B5 showed this one follows BCRA Comunicación A 3500, so a
# long run here would be the market and not the plumbing.
FLOOR = ("ambito", "mayorista")
AMBITO_KEYS = ("mayorista", "oficial", "informal", "mep", "ccl")
ARGDATOS_CASAS = ("mayorista", "oficial", "tarjeta", "cripto", "blue")


def ambito_daily(raw: Path, key: str):
    _, fields = ALL_AMBITO[key]
    return [(r["date"], mid_of(r, fields)) for r in load_series(raw, key)]


def argdatos_daily(raw: Path, casa: str):
    # load_argentinadatos refuses a casa outside B5's table, and blue is not in
    # it on purpose: that table says which series are agent classes for B5, and
    # B37 has no business editing it. The parser is shared, the table is not.
    p = raw / ("argentinadatos_%s.json" % casa)
    if not p.exists():
        return None
    rows = parse_argentinadatos_rows(json.loads(p.read_text(encoding="utf-8")),
                                     casa)
    out = []
    for r in rows:
        c, v = r.get("compra"), r.get("venta")
        if c and v and c > 0 and v > 0:
            out.append((r["date"], (c * v) ** 0.5))
        elif v and v > 0:
            out.append((r["date"], float(v)))
    return out


def runs_with_end(series):
    """Maximal stretches of consecutive rows carrying an identical quote.

    Rows are trading days, so a weekend is not a break: it simply is not a row.
    A run of n rows is n published days on which the number did not move. Each
    run carries its own first and last date so a freeze can be located rather
    than only counted.
    """
    out = []
    if not series:
        return out
    series = sorted(series)
    start = prev = series[0][0]
    val = series[0][1]
    n = 1
    for d, v in series[1:]:
        if v == val:
            n += 1
            prev = d
        else:
            out.append({"days": n, "first": start, "last": prev, "value": val})
            start = prev = d
            val = v
            n = 1
    out.append({"days": n, "first": start, "last": prev, "value": val})
    return out


def in_win(series):
    a, b = WINDOW_START.isoformat(), WINDOW_END.isoformat()
    return [(d, v) for d, v in series if a <= d <= b]


def report(label, series, floor=None):
    rs = runs_with_end(in_win(series))
    if not rs:
        print("  %-26s no row inside the window" % label)
        return None
    lens = sorted(r["days"] for r in rs)
    n = len(lens)
    q = lambda p: lens[min(n - 1, int(p * n))]
    top = sorted(rs, key=lambda r: -r["days"])[:3]
    mark = ""
    if floor is not None:
        mark = "   <-- %.1f x the floor" % (lens[-1] / floor) if lens[-1] > floor else ""
    print("  %-26s rows %5d  runs %5d  median %2d  p95 %3d  p99 %4d  MAX %4d%s"
          % (label, len(in_win(series)), n, statistics.median(lens),
             q(0.95), q(0.99), lens[-1], mark))
    for r in top:
        print("        %4d days  %s to %s  at %.4f"
              % (r["days"], r["first"], r["last"], r["value"]))
    return {"rows": len(in_win(series)), "runs": n,
            "median": statistics.median(lens), "p95": q(0.95), "p99": q(0.99),
            "max": lens[-1], "longest": top}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    raw = root / "data" / "raw"

    print("=" * 78)
    print("B37: how long a published quote goes without changing")
    print("window %s to %s, trading days only" % (WINDOW_START, WINDOW_END))
    print("=" * 78)

    rec = {"window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
            "floor_series": "%s %s" % FLOOR, "series": {}}

    print("\nB37-1, the floor. Ambito mayorista, which B5 showed follows BCRA")
    print("Comunicacion A 3500, so a long run here is the market not the pipe.")
    print("-" * 78)
    f = report("ambito mayorista", ambito_daily(raw, "mayorista"))
    if f is None:
        raise SystemExit("the floor series is empty. Nothing is judged.")
    rec["series"]["ambito mayorista"] = f
    floor = f["max"]
    print("\n  floor taken as this series' longest run: %d days" % floor)
    print("  Everything below is read against it, and the gate is that a")
    print("  candidate has to beat it by more than the ratio printed.")

    print("\nB37-2, every other series")
    print("-" * 78)
    for k in AMBITO_KEYS:
        if k == "mayorista":
            continue
        rec["series"]["ambito " + k] = report("ambito " + k,
                                              ambito_daily(raw, k), floor)
    for c in ARGDATOS_CASAS:
        s = argdatos_daily(raw, c)
        if s is None:
            print("  %-26s not on disk, named rather than skipped silently"
                  % ("argentinadatos " + c))
            continue
        rec["series"]["argentinadatos " + c] = report("argentinadatos " + c,
                                                      s, floor)

    print("\n" + "=" * 78)
    print("the reading")
    print("=" * 78)
    frozen = [(k, v) for k, v in rec["series"].items()
              if v and k != "ambito mayorista" and v["max"] > floor]
    if not frozen:
        print("  Not one series beats the floor. Inside this window no edge to a")
        print("  source went stale, and the seventy-one days B5 found is an")
        print("  exception rather than a family. That is a reading, not a null.")
    else:
        for k, v in sorted(frozen, key=lambda kv: -kv[1]["max"]):
            print("  %-26s max %4d days, %.1f x the floor, longest %s to %s"
                  % (k, v["max"], v["max"] / floor, v["longest"][0]["first"],
                     v["longest"][0]["last"]))
        print("\n  Each of these has a candidate freeze. B37-3 asks whether the")
        print("  true value moved during it, and B37-4 asks whether the gap")
        print("  closed in one step. Neither is read here.")
    rec["floor_days"] = floor
    out = Path(a.out) if a.out else root / "results" / "b37_runs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=1))
    print("\nwritten: %s" % out)


if __name__ == "__main__":
    main()
