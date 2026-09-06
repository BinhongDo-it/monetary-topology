"""Does the Chicago selection story survive the check it implies?

The result document explains a large second difference at Chicago by pointing
at a fill rate: corn is quoted there on 39 percent of the days that soybeans
are, while the three river positions quote both commodities on the same days.
That is a real asymmetry and it was printed. What was not done is the check the
explanation implies. If a selected subset of days is what produces a large and
noisy reading, then putting a pair that reads small and quiet on the same days
should move it. If that pair does not move, the selection is not what makes
Chicago large, and the explanation has to be something else.

The heading of that section also says Chicago is the only position whose two
commodities are not quoted on the same days. That was read off a table of four
positions in one state. This file states the scope by counting the asymmetry
everywhere the carrier reaches.

    python experiments/b41_chicago_audit.py --check --record

Reads only what is cached. No network, no key.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_persistence as P     # noqa: E402
import b41_square_smoke as S    # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results"

IL = 3192
CORN = "Corn"
SOY = "Soybeans"


def iso(s: str) -> str:
    """MM/DD/YYYY to ISO. Never order these dates in their native form."""
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        return f"{s[6:10]}-{s[0:2]}-{s[3:5]}"
    return s[:10]


def panel(rid: int, ca: str, cb: str):
    """day -> {(commodity, position): midpoint}, current window, months matched."""
    by_day = P.load_all(rid)
    out: dict[str, dict] = {}
    for day, rows in by_day.items():
        cells, _ = S.cells(rows)
        got: dict[tuple, float] = {}
        month: dict[tuple, str] = {}
        for key, at in cells.items():
            com, klass, grade, window, m_lo = key[0], key[1], key[2], key[3], key[4]
            if com not in (ca, cb):
                continue
            if "current" not in window:
                continue
            for pos, (lo, hi) in at.items():
                got[(com, pos, klass, grade)] = (lo + hi) / 2
                # the month is kept per cell, not per commodity. Requiring one
                # month across every position in the state would drop days on
                # which a position outside the pair happened to roll, which is
                # a filter about places the square never touches.
                month[(com, pos, klass, grade)] = m_lo
        if not got:
            continue
        out[iso(day)] = dict(cells=got, month=month)
    return out


def series(pan, ca, cb, key_a, key_b, i, j, days=None):
    vals, used = [], []
    for d in sorted(pan):
        if days is not None and d not in days:
            continue
        c = pan[d]["cells"]
        need = [(ca,) + (i,) + key_a, (ca,) + (j,) + key_a,
                (cb,) + (i,) + key_b, (cb,) + (j,) + key_b]
        if not all(k in c for k in need):
            continue
        m = pan[d]["month"]
        if m[need[0]] != m[need[1]] or m[need[2]] != m[need[3]]:
            continue
        ai, aj, bi, bj = (c[k] for k in need)
        vals.append((ai - aj) - (bi - bj))
        used.append(d)
    return vals, used


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    if not (a.check or a.record):
        ap.print_help(); return

    pan = panel(IL, CORN, SOY)
    print(f"\nIllinois, {len(pan)} days with a current-window quote")

    KA = ("Yellow", "US #2")      # corn class, grade
    KB = ("", "US #1")            # soybean class, grade
    positions = sorted({p for d in pan.values() for (_, p, _, _) in d["cells"]})

    # fill rate per position per commodity, on the identities the panel uses
    fill = {}
    for pos in positions:
        for com, k in ((CORN, KA), (SOY, KB)):
            n = sum(1 for d in pan.values() if (com, pos) + k in d["cells"])
            fill[(pos, com)] = n / len(pan)
    used_pos = [p for p in positions
                if fill[(p, CORN)] > 0.2 and fill[(p, SOY)] > 0.2]
    print("\nfill rate on the identities this panel uses:")
    for p in sorted(positions, key=lambda p: min(fill[(p, CORN)], fill[(p, SOY)])):
        if max(fill[(p, CORN)], fill[(p, SOY)]) < 0.2:
            continue
        print(f"   corn {fill[(p, CORN)]:.3f}   soy {fill[(p, SOY)]:.3f}   "
              f"ratio {min(fill[(p, CORN)], fill[(p, SOY)]) / max(fill[(p, CORN)], fill[(p, SOY)]):.2f}   {p}")

    chi = [p for p in used_pos if p.startswith("Chicago")]
    print(f"\nChicago positions in the panel: {chi}")

    # the days Chicago corn exists
    chi_pos = chi[0] if chi else None
    chi_days = {d for d, v in pan.items() if chi_pos and (CORN, chi_pos) + KA in v["cells"]}
    print(f"days Chicago corn is quoted: {len(chi_days)}")

    rows = []
    pairs = [(i, j) for n, i in enumerate(used_pos) for j in used_pos[n + 1:]]
    print(f"\n{'mean':>8}{'sd':>8}{'n':>7}   pair   (full sample)")
    full = {}
    for i, j in pairs:
        v, _ = series(pan, CORN, SOY, KA, KB, i, j)
        if len(v) < 30:
            continue
        full[(i, j)] = v
        print(f"{statistics.mean(v):>8.2f}{statistics.stdev(v):>8.2f}{len(v):>7}   "
              f"{i}  vs  {j}")

    print(f"\n{'mean':>8}{'sd':>8}{'n':>7}   pair   "
          f"(restricted to the {len(chi_days)} days Chicago quotes corn)")
    for (i, j) in full:
        v, _ = series(pan, CORN, SOY, KA, KB, i, j, days=chi_days)
        if len(v) < 20:
            print(f"{'-':>8}{'-':>8}{len(v):>7}   {i}  vs  {j}")
            continue
        rows.append(dict(i=i, j=j, n_full=len(full[(i, j)]),
                         mean_full=statistics.mean(full[(i, j)]),
                         sd_full=statistics.stdev(full[(i, j)]),
                         n_sub=len(v), mean_sub=statistics.mean(v),
                         sd_sub=statistics.stdev(v)))
        print(f"{statistics.mean(v):>8.2f}{statistics.stdev(v):>8.2f}{len(v):>7}   "
              f"{i}  vs  {j}")

    if a.record:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b41_chicago_audit.json"
        dest.write_text(json.dumps(dict(
            stage="B41", diagnostic_only=True,
            diagnostic_reason="recheck of the Chicago selection explanation: "
                              "does a quiet pair move when put on the same days",
            report=IL, days=len(pan), chicago_corn_days=len(chi_days),
            fill={f"{p}|{c}": v for (p, c), v in fill.items() if v > 0.05},
            pairs=rows), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
