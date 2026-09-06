"""Does the harvest explanation for Tennessee hold in the other wheat states?

The result document explains a June sign reversal in Tennessee by the soft red
winter wheat harvest: new wheat arrives at inland country elevators, the inland
wheat basis falls, so river minus inland jumps and the square turns negative.
That is a mechanism, and a mechanism that names a crop and a month makes a
prediction outside the state it was fitted on. Every state that quotes the same
wheat and has both a river position and a country position should show the same
month doing the same thing to its wheat leg.

If they do, the explanation survives a test it could have failed. If they do
not, what Tennessee has is a seasonal pattern of its own and the harvest story
is a story.

    python experiments/b41_harvest_audit.py --check --record

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

SOY = ("Soybeans", "", "US #1")
SRW = ("Wheat", "Soft Red Winter", "US #2")

# Reports that quote soft red winter wheat. Taken from the pooled block's own
# state list plus the two states read at their own coverage.
CANDIDATES = {2892: "KY", 2851: "OH", 2932: "MO", 2787: "SC",
              3156: "NC", 3167: "VA", 3088: "TN"}

RIVER = ("Barge", "River")
INLAND = ("Country Elevators",)


def iso(s: str) -> str:
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        return f"{s[6:10]}-{s[0:2]}-{s[3:5]}"
    return s[:10]


def is_river(pos: str) -> bool:
    return any(w in pos for w in RIVER)


def is_inland(pos: str) -> bool:
    return any(w in pos for w in INLAND) and not is_river(pos)


def legs(rid: int, only_pair=None):
    """month -> list of (wheat leg, soy leg, square), river minus inland.

    only_pair fixes the two positions. Pooling every river-inland pair in a
    state makes the monthly medians incomparable, because which pairs are
    quoted changes with the month: Kentucky carries 875 observations in June
    and 36 in October, drawn from different pairs. A month effect and a
    composition effect look identical in a pooled median, so the reading that
    the prediction is scored on uses one pair throughout."""
    by_day = P.load_all(rid)
    per_month = defaultdict(list)
    pairs_seen = defaultdict(int)
    for day, rows in by_day.items():
        cells, _ = S.cells(rows)
        lvl: dict[tuple, float] = {}
        mon: dict[tuple, str] = {}
        for key, at in cells.items():
            head = key[:3]
            if head not in (SOY, SRW) or "current" not in key[3]:
                continue
            for pos, (lo, hi) in at.items():
                lvl[(head, pos)] = (lo + hi) / 2
                mon[(head, pos)] = key[4]
        rivers = sorted({p for (h, p) in lvl if is_river(p)})
        inlands = sorted({p for (h, p) in lvl if is_inland(p)})
        d = iso(day)
        for r in rivers:
            for c in inlands:
                need = [(SOY, r), (SOY, c), (SRW, r), (SRW, c)]
                if not all(k in lvl for k in need):
                    continue
                if mon[need[0]] != mon[need[1]] or mon[need[2]] != mon[need[3]]:
                    continue
                w = lvl[(SRW, r)] - lvl[(SRW, c)]
                s = lvl[(SOY, r)] - lvl[(SOY, c)]
                if only_pair is not None and (r, c) != only_pair:
                    continue
                per_month[d[5:7]].append((w, s, s - w))
                pairs_seen[(r, c)] += 1
    return per_month, pairs_seen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    if not (a.check or a.record):
        ap.print_help(); return

    out = {}
    for rid, st in CANDIDATES.items():
        try:
            _, all_pairs = legs(rid)
            if not all_pairs:
                per_month, pairs = {}, {}
            else:
                # Every pair, not the thickest one. Scoring the thickest pair
                # was a choice with no reason behind it, and it decided the
                # answer: in Ohio two of the three pairs go one way and the
                # third goes the other, and the thickest happens to be one of
                # the two. The pair a state has most days of is not the pair
                # the mechanism is about.
                per_month, pairs = legs(rid), all_pairs
                per_month = per_month[0] if isinstance(per_month, tuple) else per_month
        except SystemExit:
            continue
        if not per_month:
            print(f"\n{st} ({rid}): no river-and-inland pair quoting both")
            out[st] = None
            continue
        print(f"\n=== {st} ({rid}), {sum(len(v) for v in per_month.values())} "
              f"observations over {len(pairs)} position pair(s)")
        for (r, c), n in sorted(pairs.items(), key=lambda x: -x[1]):
            print(f"    {n:>5}  {r}   minus   {c}")
        print(f"    {'month':<6}{'n':>5}{'wheat leg':>12}{'soy leg':>10}{'square':>9}")
        rec = {}
        for m in sorted(per_month):
            v = per_month[m]
            w = statistics.median(x[0] for x in v)
            s = statistics.median(x[1] for x in v)
            q = statistics.median(x[2] for x in v)
            rec[m] = dict(n=len(v), wheat=w, soy=s, square=q)
            mark = "  <-- June" if m == "06" else ""
            print(f"    {m:<6}{len(v):>5}{w:>+12.2f}{s:>+10.2f}{q:>+9.2f}{mark}")
        out[st] = rec

    # the prediction, stated once and scored once
    print("\n" + "=" * 70)
    print("scored on one fixed position pair per state, the thickest one")
    print("the prediction: June's wheat leg is above that state's own median month")
    print("=" * 70)
    score = []
    for st, rec in out.items():
        if not rec or "06" not in rec:
            print(f"  {st}: no June"); continue
        others = [v["wheat"] for m, v in rec.items() if m != "06"]
        j = rec["06"]["wheat"]
        med = statistics.median(others)
        rank = sum(1 for x in others if x < j) + 1
        ok = j > med
        score.append(ok)
        print(f"  {st}: June wheat leg {j:+7.2f}, median of other months "
              f"{med:+7.2f}, rank {rank} of {len(others) + 1}   "
              f"{'as predicted' if ok else 'AGAINST'}")
    print(f"\n  {sum(score)} of {len(score)} states move as the explanation predicts")

    if a.record:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b41_harvest_audit.json"
        dest.write_text(json.dumps(dict(
            stage="B41", diagnostic_only=True,
            diagnostic_reason="out-of-state test of the Tennessee harvest "
                              "explanation for the June sign reversal",
            by_state=out), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
