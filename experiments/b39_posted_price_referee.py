"""B39: an independently collected posted price, as a referee for the archive.

B38c closed by naming what it could not reach: a bias that is persistent,
structured, and unrelated to how tightly an item is specified. Two vintages of
one source cannot reach it, because they share their underlying entries. **Only
a source with no contact with the first one can.**

This is that source. The Big Mac index is a posted menu price, collected by The
Economist, published as a series since 2000, and it has no connection to the
crowdsourced archive. The archive carries a McDonald's combo meal for every
city. So the same brand's posted price exists in two datasets that were built by
different people for different reasons, and they can be put against each other.

**This is also the LADDER arm.** The class predicts a nationally posted number
rather than a locally set one, and until now that was read from contributors'
recollections of such a number. Here the number itself is the object.

**Two things are read, and they are different questions.**

    B39-1  the level: does the archive's country figure track the posted price
    B39-2  the residual sd of that fit, which is an independent bound on the
           archive's country-level error for a tightly specified branded item

**The item is not identical on the two sides**: a combo meal is not a single
sandwich. A fixed ratio between them is absorbed by the intercept and changes
neither the slope nor the residual, which is the whole reason the reading is on
those two and not on the level.

Run:
    python experiments\\b39_posted_price_referee.py
"""

import csv
import json
import math
import statistics as st
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "b30_5" / "column_map.json"
BIGMAC = ROOT / "data" / "raw" / "big-mac-full-index.csv"
OUT = ROOT / "results" / "b39_posted_price_referee.json"

MCMEAL = "Combo Meal at McDonald's"
DATES = ["2022-07-01", "2023-01-01"]

# The two sources spell some countries differently. Only the differences are
# listed; everything else matches on the name as printed.
ALIAS = {
    "United States": "United States", "Britain": "United Kingdom",
    "South Korea": "South Korea", "Czech Republic": "Czech Republic",
    "UAE": "United Arab Emirates", "Russia": "Russia",
    "Vietnam": "Vietnam", "Hong Kong": "Hong Kong (China)",
    "Taiwan": "Taiwan", "Moldova": "Moldova", "Turkey": "Turkey",
    "Azerbaijan": "Azerbaijan", "Saudi Arabia": "Saudi Arabia",
}


def value(raw):
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def ols(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    b = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / sxx
    a = my - b * mx
    res = [y[i] - (a + b * x[i]) for i in range(n)]
    return a, b, st.pstdev(res), res


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    dx = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy = math.sqrt(sum((v - my) ** 2 for v in y))
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (dx * dy)


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    col = next(c for c, m in spec["mapping"].items()
               if MCMEAL in m["item"] and m.get("agrees"))
    rows = list(csv.DictReader(
        (ROOT / spec["source_file"]).open(encoding="utf-8-sig", newline="")))
    citycol, ctrycol = spec["city_column"], spec["country_column"]

    per_country = {}
    for r in rows:
        v = value(r[col])
        if v:
            per_country.setdefault(r[ctrycol].strip(), []).append(v)

    bm = list(csv.DictReader(BIGMAC.open(encoding="utf-8-sig", newline="")))
    posted, by_date = {}, {}
    for r in bm:
        if r["date"] in DATES:
            v = value(r["dollar_price"])
            if v:
                nm = ALIAS.get(r["name"].strip(), r["name"].strip())
                posted.setdefault(nm, []).append(v)
                by_date.setdefault(nm, {})[r["date"]] = v

    print("=" * 78)
    print("B39: the archive against an independently collected posted price")
    print("=" * 78)
    print("  archive item    %s" % spec["mapping"][col]["item"])
    print("  referee         Big Mac index, %s, dollar price" % " and ".join(DATES))
    print("  countries       archive %d, referee %d"
          % (len(per_country), len(posted)))

    pairs, missing = [], []
    for c, v in sorted(posted.items()):
        a = per_country.get(c)
        if not a:
            missing.append(c)
            continue
        pairs.append((c, st.median(v), st.median(a), len(a)))
    if missing:
        print("\n  referee countries with no archive cities, named rather than "
              "dropped quietly (%d):" % len(missing))
        print("    %s" % ", ".join(missing))

    print("\n  %-24s %10s %10s %8s %8s"
          % ("country", "posted", "archive", "ratio", "cities"))
    for c, p, a, n in sorted(pairs, key=lambda t: -t[2] / t[1]):
        print("  %-24s %10.2f %10.2f %8.3f %8d" % (c, p, a, a / p, n))

    x = [math.log(p) for _, p, _, _ in pairs]
    y = [math.log(a) for _, _, a, _ in pairs]
    a0, b0, sd, res = ols(x, y)
    r = pearson(x, y)
    print("\n" + "=" * 78)
    print("B39-1  does the archive track the posted price")
    print("=" * 78)
    print("  n countries        %d" % len(pairs))
    print("  slope              %+.4f    (1 means it tracks one for one)" % b0)
    print("  Pearson on logs    %+.4f    r^2 %.4f" % (r, r * r))
    print("  implied level      a combo meal is %.2f times a single sandwich"
          % math.exp(a0 + (b0 - 1) * st.mean(x)))

    print("\n" + "=" * 78)
    print("B39-2  the residual, which is the independent bound B38c lacked")
    print("=" * 78)
    print("  residual sd in logs  %.4f" % sd)
    print("  the archive's own two-vintage cell sd was 0.0373, and arm A's")
    print("  gasoline measurement was 0.0293. This number is measured against")
    print("  a source with no contact with the archive at all, so it is the")
    print("  one that carries a persistent bias if there is one.")
    print("\n  the countries furthest from the fitted line, printed as objects")
    order = sorted(range(len(pairs)), key=lambda i: -abs(res[i]))
    for i in order[:8]:
        print("    %-24s %+.4f   archive is %+.1f%% off the line"
              % (pairs[i][0], res[i], (math.exp(res[i]) - 1) * 100))

    # --- B39-3: how much of that residual is the two sources being dated
    # differently, rather than the archive being wrong ---
    print("\n" + "=" * 78)
    print("B39-3  how much of that is a date mismatch rather than an error")
    print("=" * 78)
    print("  The referee publishes two dates six months apart and the archive")
    print("  sits between them. A country whose posted price barely moved")
    print("  between those dates cannot have a large date-driven residual; a")
    print("  country whose price moved a lot can have nothing else. The split")
    print("  is on the referee alone and never on the residual.")
    move = {}
    for c, dd in by_date.items():
        if len(dd) == 2:
            a1, a2 = dd[DATES[0]], dd[DATES[1]]
            move[c] = abs(math.log(a2 / a1))
    have = [(i, move.get(pairs[i][0])) for i in range(len(pairs))]
    have = [(i, m) for i, m in have if m is not None]
    print("\n  countries with both referee dates: %d" % len(have))
    cut = st.median([m for _, m in have])
    print("  median move between the two dates: %.4f in logs (%.1f%%)"
          % (cut, 100 * (math.exp(cut) - 1)))
    stable = [i for i, m in have if m <= cut]
    moved = [i for i, m in have if m > cut]
    for label, idx in (("stable half", stable), ("moving half", moved)):
        xs = [x[i] for i in idx]; ys = [y[i] for i in idx]
        _, bb, ss, _ = ols(xs, ys)
        rr = pearson(xs, ys)
        print("  %-14s n %2d   slope %+.4f   Pearson %+.4f   residual sd %.4f"
              % (label, len(idx), bb, rr, ss))
    print("\n  the movers, and by how much the referee itself moved:")
    for i in sorted(moved, key=lambda i: -move[pairs[i][0]])[:8]:
        print("    %-24s referee moved %+.1f%%, archive is %+.1f%% off the line"
              % (pairs[i][0], 100 * (math.exp(move[pairs[i][0]]) - 1),
                 (math.exp(res[i]) - 1) * 100))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "archive_item": spec["mapping"][col]["item"],
        "referee": "Big Mac index dollar price, %s" % ", ".join(DATES),
        "n_countries": len(pairs), "slope": b0, "pearson": r,
        "residual_sd": sd,
        "pairs": [{"country": c, "posted": p, "archive": a, "cities": n,
                   "residual": res[i]}
                  for i, (c, p, a, n) in enumerate(pairs)],
        "referee_countries_without_archive": missing,
        "b39_3_date_split": {
            "median_move_log": st.median([m for _, m in have]),
            "stable": {"n": len(stable),
                       "residual_sd": ols([x[i] for i in stable],
                                          [y[i] for i in stable])[2]},
            "moving": {"n": len(moved),
                       "residual_sd": ols([x[i] for i in moved],
                                          [y[i] for i in moved])[2]}},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
