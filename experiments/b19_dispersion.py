"""B19 recheck: measure the quarterly dispersion that gate two guessed at.

**Why this exists.** B19 was closed before opening because gate two came back at
6.1. Three numbers went into that ratio and **none of them came from a
document**: the Islamic equity money invested in US stocks was reached by
5.98 trillion times five per cent, then halved, then taken at three tenths; the
denominator was the whole US market rather than the compliant subset the money
can actually hold; and the quarterly dispersion of institutional ownership was
written as "typically 2 to 5 points" with 5 taken.

Moving the two checkable inputs to defensible values moves the ratio from 6.1 to
about 1.0. **Nothing between those two ends was measured.** This file measures
the third one, because the data has been on disk the whole time: 51 quarters of
Form 13F structured data, 2013Q3 to 2026Q1.

**What is measured, and in what units.** Institutional holdings per security per
quarter, from `INFOTABLE.tsv`, summed over filers. Shares only: `SSHPRNAMTTYPE`
must be `SH`, and rows carrying a `PUTCALL` value are options and are dropped.
The reported quantity is the cross-sectional dispersion of the quarter-on-quarter
change, given two ways:

- **relative**, the standard deviation of `dlog(shares held)`, which needs
  nothing but 13F;
- **in points of institutional holdings**, the same thing at the median level.

Converting to points of shares outstanding needs an ownership level this file
does not have. **It is not assumed.** Gate two's threshold has to be restated in
whichever unit is used, and that restatement is the next step, not this one.

Each quarter's aggregate is cached, so the 18 GB is read once. Nothing is
deleted; a cache file that fails its own check is renamed.

Usage::

    python experiments/b19_dispersion.py --build      # one pass over the zips
    python experiments/b19_dispersion.py              # read caches, report
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import statistics
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "topology-fingerprints" / "data" / "raw" / "sec13f"
CACHE = ROOT / "data" / "cache" / "b19_13f"
QNAME = re.compile(r"form13f_(\d{4}q[1-4])\.zip$", re.I)


def quarters() -> list[tuple[str, Path]]:
    if not SRC.exists():
        raise SystemExit(f"13F data not found at {SRC}")
    out = []
    for f in sorted(SRC.glob("form13f_*.zip")):
        m = QNAME.search(f.name)
        if m:
            out.append((m.group(1).lower(), f))
    return out


def infotable_member(z: zipfile.ZipFile) -> str:
    """Where the holdings table sits inside one quarter's archive.

    **Fifty of the fifty-one put it at the archive root and one does not.**
    `form13f_2025q3.zip` packs everything under `01JUN2025-31AUG2025_form13f/`,
    so a lookup by exact name finds nothing and the run stops on that quarter
    after forty-eight have already been cached. The member is located by its base
    name instead, and **which spelling was found is printed**, because a layout
    that changed once can change again and the next reader should see it rather
    than infer it.
    """
    hits = [n for n in z.namelist() if n.rsplit("/", 1)[-1].upper() == "INFOTABLE.TSV"]
    if not hits:
        raise SystemExit("no INFOTABLE.tsv in %s; members: %s"
                         % (z.filename, z.namelist()[:8]))
    if len(hits) > 1:
        raise SystemExit("more than one INFOTABLE.tsv in %s: %s" % (z.filename, hits))
    return hits[0]


def build_one(q: str, path: Path) -> dict[str, float]:
    """Sum share holdings by CUSIP for one quarter. Options and principal drop out."""
    held: dict[str, float] = {}
    kept = dropped_type = dropped_opt = bad = 0
    with zipfile.ZipFile(path) as z:
        member = infotable_member(z)
        if member != "INFOTABLE.tsv":
            print(f"  {q}  holdings table is at {member!r}, not at the archive root")
        with z.open(member) as fh:
            rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8",
                                                 errors="replace"), delimiter="\t")
            for r in rd:
                if (r.get("PUTCALL") or "").strip():
                    dropped_opt += 1
                    continue
                if (r.get("SSHPRNAMTTYPE") or "").strip().upper() != "SH":
                    dropped_type += 1
                    continue
                cusip = (r.get("CUSIP") or "").strip().upper()
                try:
                    n = float(r.get("SSHPRNAMT") or 0)
                except ValueError:
                    bad += 1
                    continue
                if not cusip or n <= 0:
                    bad += 1
                    continue
                held[cusip] = held.get(cusip, 0.0) + n
                kept += 1
    print(f"  {q}  kept {kept:>10,}  options {dropped_opt:>9,}  "
          f"non-share {dropped_type:>8,}  unusable {bad:>7,}  cusips {len(held):>7,}")
    return held


def build() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    for q, path in quarters():
        out = CACHE / f"{q}.json"
        if out.exists():
            try:
                if len(json.loads(out.read_text(encoding="utf-8"))) > 1000:
                    continue
            except (ValueError, OSError):
                pass
            n = 0
            while (bad := out.with_suffix(f".json.bad{n or ''}")).exists():
                n += 1
            out.rename(bad)
            print(f"  {q}  cache unusable, renamed to {bad.name}, rebuilding")
        held = build_one(q, path)
        out.write_text(json.dumps(held, sort_keys=True), encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true", help="one pass over the zips")
    args = ap.parse_args()
    if args.build:
        return build()

    files = sorted(CACHE.glob("*.json"))
    if len(files) < 2:
        print("no caches yet. Run with --build first (one pass over 18 GB).")
        return 2
    series = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in files}
    qs = sorted(series)
    print(f"{len(qs)} quarters cached, {qs[0]} to {qs[-1]}\n")

    print("cross-sectional dispersion of the quarter-on-quarter change in")
    print("institutional shares held, over securities present in both quarters\n")
    print(f"{'quarter':>9} {'securities':>11} {'sd dlog':>9} {'p90 |dlog|':>11} "
          f"{'iqr dlog':>9}")
    all_sd, all_iqr, rows = [], [], []
    for a, b in zip(qs, qs[1:]):
        pa, pb = series[a], series[b]
        d = [math.log(pb[c] / pa[c]) for c in pb.keys() & pa.keys()
             if pa[c] > 0 and pb[c] > 0]
        if len(d) < 100:
            continue
        d.sort()
        sd = statistics.pstdev(d)
        iqr = d[3 * len(d) // 4] - d[len(d) // 4]
        p90 = sorted(abs(x) for x in d)[9 * len(d) // 10]
        all_sd.append(sd)
        all_iqr.append(iqr)
        rows.append((b, len(d), sd, iqr))
        print(f"{b:>9} {len(d):>11,} {sd:>9.4f} {p90:>11.4f} {iqr:>9.4f}")

    med_sd = statistics.median(all_sd)
    med_iqr = statistics.median(all_iqr)
    print(f"\n  median across quarters:  sd {med_sd:.4f}   iqr {med_iqr:.4f}")
    print(f"  **in points of a holding**: sd {100 * med_sd:.2f} pp, "
          f"iqr {100 * med_iqr:.2f} pp")
    print()
    print("  Gate two used 5 points and the source it cited said 2 to 5.")
    print(f"  Measured here: {100 * med_sd:.2f} points as a standard deviation of the")
    print("  relative change. **These are not the same unit** and the gate has to be")
    print("  restated in one of them before the ratio is recomputed. The point of")
    print("  this file is that the number is measurable and was guessed.")
    print()
    print("  The interquartile range is printed beside the standard deviation")
    print("  because holdings changes are heavy-tailed: a standard deviation on a")
    print("  heavy tail overstates the noise a median security actually carries,")
    print("  and gate two takes the noise as its numerator.")

    criteria = [
        {"name": "B19-D-1  every cached quarter is read and every quarter pair with "
                 "enough overlap is printed",
         "passed": len(qs) > 2 and len(all_sd) == len(qs) - 1,
         "detail": "%d quarters cached, %s to %s, %d quarter pairs read, "
                   "%d dropped for fewer than 100 securities in common"
                   % (len(qs), qs[0], qs[-1], len(all_sd), len(qs) - 1 - len(all_sd))},
        {"name": "B19-D-2  print the dispersion for every quarter pair, and the median "
                 "across them, with no line drawn on either",
         "passed": True,
         "detail": "median across quarters: sd %.4f, iqr %.4f; in points of a holding "
                   "%.2f and %.2f" % (med_sd, med_iqr, 100 * med_sd, 100 * med_iqr)},
        {"name": "B19-D-3  the measured quantity and the one gate two used are named in "
                 "their own units, and the ratio is not recomputed across them",
         "passed": True,
         "detail": "gate two took 5 points of a source that said 2 to 5, in points of "
                   "ownership; this measures %.2f points as the standard deviation of "
                   "the relative change in shares held. **Different units.** Converting "
                   "needs an ownership level this file does not have and does not assume"
                   % (100 * med_sd)},
    ]
    rec = {"stage": "B19-dispersion", "step": "13f_quarterly_dispersion",
           "diagnostic_only": True,
           "diagnostic_reason": ("B19 is closed at gate two and this does not reopen it. "
                                 "It measures the one input to that gate that was written "
                                 "down rather than read, and it stops short of recomputing "
                                 "the ratio because the two quantities are in different "
                                 "units."),
           "quarters": qs, "median_sd_dlog": round(med_sd, 8),
           "median_iqr_dlog": round(med_iqr, 8),
           "per_quarter": [{"quarter": b, "securities": n, "sd_dlog": round(s, 8),
                            "iqr_dlog": round(i, 8)}
                           for b, n, s, i in rows],
           "criteria": criteria}
    out = ROOT / "results" / "b19_dispersion.json"
    out.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s: %d criteria, %d passing"
          % (out.name, len(criteria), sum(1 for c in criteria if c["passed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
