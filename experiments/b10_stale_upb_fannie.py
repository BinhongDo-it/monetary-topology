"""B10 §6.2.5.4: how much of B8's below-cluster mass is a balance that did not move.

Registered in the B8 inputs register §6.2.5.4, **before this file was
written**. It answers one question and adds no criterion:

    §6.2.5.3 registered an open third mechanism, 8.84% (2002Q1) and 8.93%
    (2019Q1) of quiet months landing **below** the modal cluster, with the note
    that a level contract payment plus occasional extra principal cannot produce
    an underpayment. On Freddie, 5.208% of quiet month-differences carry a
    balance identical to the month before, and those months read
    ``P(t) = UPB x rate/1200``, interest only, median 0.8086 of the contract
    payment (the B10 availability register §13.1). By construction such a
    month sits below the cluster. **How much of 8.8% is that?**

What this file does not do
--------------------------
It **does not change B8's criteria, its quiet filter, its estimator, or any of
its numbers**. The filter is not re-implemented: ``scan`` is imported from
``b8_c8_1c_contract_payment_b`` and called unmodified, so the 取数口径 is B8's
byte for byte (R01: never move a criterion and an intake rule in one change).
Only the per-month tally is new.

The drift check is a reproduction, not an assertion
---------------------------------------------------
B8 §6.2.5.3 published the three shares. This file recomputes them from its own
tally and prints them beside the published pair. **If the filter had drifted the
reproduction would miss**, and that is a stronger check than an equality assert
because it names which of the three moved.

    2002Q1   at 0.7354   below 0.0884   above 0.1762
    2019Q1   at 0.7540   below 0.0893   above 0.1566

The new object
--------------
A cross-tab, printed whole, per archive::

                    below cluster   in cluster   above cluster
    balance unchanged      .            .             .
    balance moved          .            .             .

plus, for the unchanged row, the distribution of ``implied / cluster mode``,
which should sit at the interest share of the payment if the mechanism is what
Freddie says it is. **No threshold in this file** (engineering rule 11).

Usage::

    python experiments/b10_stale_upb_fannie.py --limit 2000000     # smoke
    python experiments/b10_stale_upb_fannie.py --only 2019Q1
    python experiments/b10_stale_upb_fannie.py

Writes ``results/b10_stale_upb_fannie.json`` with ``diagnostic_only`` set from
this first version.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import b8_c8_1c_contract_payment_b as b8  # noqa: E402

RESULTS = ROOT / "results"

#: B8 ran C8-1c on these two. Using the same pair is what makes the reproduction
#: in §0 of the output a check rather than a coincidence.
ARCHIVES = ("2002Q1", "2019Q1")

#: The shares B8 published in the B8 inputs register §6.2.5.3.
#: Quoted here so the run prints its own numbers beside them.
B8_PUBLISHED = {"2002Q1": {"at": 0.7354, "below": 0.0884, "above": 0.1762},
                "2019Q1": {"at": 0.7540, "below": 0.0893, "above": 0.1566}}


class StaleTally(b8.Tally):
    """B8's tally with one cross-tab added. Nothing of B8's is removed."""

    def __init__(self, name: str):
        super().__init__(name)
        # (balance unchanged?, below / at / above) -> count
        self.cross = Counter()
        # implied / mode, for the unchanged months only, 0.01-wide bins
        self.stale_ratio = Counter()
        self.moved_ratio = Counter()


#: Captured **before** the patch below. Without this the wrapper calls itself:
#: ``b8.close_segment`` is the name ``scan`` looks up, and it is also the name
#: the patch rebinds, so a call through the module attribute recurses. Bound
#: here rather than inline so the ordering is a statement rather than an
#: accident.
_B8_CLOSE_SEGMENT = b8.close_segment


def close_segment(seg, t) -> None:
    """B8's ``close_segment`` with the cross-tab spliced in.

    **The three gates below are copied verbatim from B8's function and are in
    the same order.** They have to be, or the denominators would not be the ones
    §6.2.5.3 reported and the reproduction in §0 would be meaningless. The
    original is then called so every number B8 accounts for is still accounted
    for by B8's own code rather than by this file's copy of it.
    """
    rows = seg.rows
    if len(rows) >= 2:
        i = seg.rate / 1200.0
        implied = [obs + p_upb * i for (obs, p_upb, _) in rows]
        if min(implied) > 0:
            mode, lo, hi, _ = b8.modal_cluster(implied)
            if mode > 0:
                for (obs, _p_upb, _p_rem), pi in zip(rows, implied):
                    where = "below" if pi < lo else ("above" if pi > hi else "at")
                    stale = (obs == 0.0)
                    t.cross[(stale, where)] += 1
                    b = int(round(min(max(pi / mode, 0.0), 2.0) / 0.01))
                    (t.stale_ratio if stale else t.moved_ratio)[b] += 1
    _B8_CLOSE_SEGMENT(seg, t)


# The filter lives in b8.scan and is not touched; only the segment sink is.
b8.close_segment = close_segment


def share(c: Counter, key) -> float:
    n = sum(c.values())
    return c[key] / n if n else float("nan")


def qtl(c: Counter, qs=(0.10, 0.50, 0.90)) -> list[float]:
    n = sum(c.values())
    if not n:
        return [float("nan")] * len(qs)
    keys, out, run, i = sorted(c), [], 0, 0
    for q in qs:
        target = q * n
        while i < len(keys) and run + c[keys[i]] < target:
            run += c[keys[i]]
            i += 1
        out.append(keys[min(i, len(keys) - 1)] * 0.01)
    return out


def run(names, limit) -> int:
    records = []
    for name in names:
        path = b8.RAW / f"{name}.zip"
        if not path.exists():
            print(f"  {name}: archive missing at {path}", file=sys.stderr)
            continue
        t = StaleTally(name)
        b8.scan(path, t, limit)

        n = t.quiet_months
        mine = {"at": t.m_at_mode / n, "below": t.m_below_mode / n,
                "above": t.m_above_mode / n}
        pub = B8_PUBLISHED.get(name)

        print(f"\n{'=' * 70}\n  {name}   quiet months {n:,}   segments {t.segments:,}"
              f"   loans {t.loans:,}\n{'=' * 70}")
        print("  §0 reproduction of B8 §6.2.5.3's three shares"
              + ("" if limit == 0 else "   (LIMITED RUN, will not match)"))
        for k in ("at", "below", "above"):
            p = f"{pub[k]:.4f}" if pub else "  n/a "
            print(f"    {k:<6} this run {mine[k]:.4f}    B8 published {p}")
        if pub and limit == 0:
            worst = max(abs(mine[k] - pub[k]) for k in mine)
            print(f"    worst absolute difference {worst:.4f}. "
                  "A miss here means the filter drifted, and it names which share.")

        stale_n = sum(v for (s, _), v in t.cross.items() if s)
        print(f"\n  the cross-tab, whole:\n"
              f"    {'':<20}{'below':>12}{'at':>12}{'above':>12}{'row total':>12}")
        for stale, label in ((True, "balance unchanged"), (False, "balance moved")):
            row = [t.cross[(stale, w)] for w in ("below", "at", "above")]
            print(f"    {label:<20}" + "".join(f"{v:>12,}" for v in row)
                  + f"{sum(row):>12,}")
        print(f"    {'share unchanged':<20}{stale_n / n:>12.5f} of all quiet months")

        below_n = t.m_below_mode
        stale_below = t.cross[(True, "below")]
        print(f"\n  the question §6.2.5.4 asked:")
        print(f"    below-cluster months                 {below_n:,}")
        print(f"    of those, balance unchanged          {stale_below:,}"
              f"   ({stale_below / below_n:.5f} of below)" if below_n else "")
        print(f"    unchanged months that are below      "
              f"{stale_below / stale_n:.5f} of unchanged" if stale_n else "")

        sq = qtl(t.stale_ratio)
        mq = qtl(t.moved_ratio)
        print(f"\n  implied / cluster mode:")
        print(f"    balance unchanged   p10 {sq[0]:.3f}  p50 {sq[1]:.3f}  p90 {sq[2]:.3f}")
        print(f"    balance moved       p10 {mq[0]:.3f}  p50 {mq[1]:.3f}  p90 {mq[2]:.3f}")
        print("    Read: if the unchanged row sits at the interest share of the "
              "payment,\n    the mechanism is the one Freddie showed. If it sits "
              "at 1.000 it is not.")

        records.append({
            "archive": name, "quiet_months": n, "segments": t.segments,
            "loans": t.loans, "limit_rows": limit,
            "shares_this_run": mine, "shares_b8_published": pub,
            "cross_tab": {f"{'unchanged' if s else 'moved'}_{w}": v
                          for (s, w), v in sorted(t.cross.items(),
                                                  key=lambda kv: (kv[0][0], kv[0][1]))},
            "stale_share_of_quiet": stale_n / n if n else None,
            "stale_share_of_below": stale_below / below_n if below_n else None,
            "ratio_to_mode_unchanged_p10_p50_p90": sq,
            "ratio_to_mode_moved_p10_p50_p90": mq,
        })

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_stale_upb_fannie.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "stale_upb_fannie",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B8 inputs register §6.2.5.4 as a "
             "candidate component of B8's open third mechanism. It changes no "
             "B8 criterion and carries no omega claim.",
         "archives": records},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", action="append",
                    help="restrict to one archive, e.g. 2019Q1, repeatable")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after this many rows per archive; a smoke run, "
                         "and the reproduction in §0 will not match")
    a = ap.parse_args(argv)
    return run(a.only or list(ARCHIVES), a.limit)


if __name__ == "__main__":
    raise SystemExit(main())
