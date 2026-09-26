"""B121 arm E: the Call Report panel for 2007Q1 to 2010Q2, read the way B59 reads it.

B59's cache starts in 2009 and was built, for 2009, from the annual subset archive, which carries no
RC-K average. The single-period archives for 2007Q2 to 2008Q3 and for 2009 sat on disk at zero bytes;
they were fetched again on 2026-09-22 and came down whole. They are kept in this station's own folder,
data/raw/b121/callreport/, so that B59's shared archive folder does not hold two archives for one
quarter, which its builder refuses.

Every archive is read with B59's own reader (`b59_call_report.read_any`), so the codes, the parsing
and the refusals are the same bytes of code that B59 and B113 rely on. The cache written here is this
station's and is rebuildable from the archives.

    python experiments/b121_call_panel.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import b59_call_report as b59c  # noqa: E402

DIRS = [ROOT / "data" / "raw" / "b121" / "callreport", ROOT / "data" / "raw" / "CallReport"]
CACHE = ROOT / "data" / "cache" / "b121_call_report.json"
FIRST, LAST = "2007Q1", "2010Q2"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    panel, refused, skipped = {}, [], []
    for d in DIRS:  # this station's folder first, so a fetched archive wins over a zero-byte one
        for path in sorted(d.glob("FFIEC CDR Call Bulk All Schedules *.zip")):
            per = b59c.period_of(path.name)
            if per is None or not (FIRST <= per <= LAST):
                continue
            if per in panel:
                skipped.append((per, path.name, str(d.relative_to(ROOT))))
                continue
            if path.stat().st_size == 0:
                skipped.append((per, path.name, "zero bytes"))
                continue
            got = b59c.read_any(path)
            for p, (values, found, members, sources, mism) in got.items():
                if mism:
                    refused.append({"archive": path.name, "period": p, "mismatches": mism})
                panel[p] = {"archive": path.name, "folder": str(d.relative_to(ROOT)).replace("\\", "/"),
                            "sha256": sha256(path), "columns_used": found, "supplied_by": sources,
                            "filers": {k: {c: v[c] for c in sorted(v)} for k, v in sorted(values.items())}}
                print(f"  {p}  {len(values):>5} filers  {path.name}  ({panel[p]['folder']})")
    want = [f"{y}Q{q}" for y in range(int(FIRST[:4]), int(LAST[:4]) + 1) for q in range(1, 5)]
    want = [w for w in want if FIRST <= w <= LAST]
    missing = [w for w in want if w not in panel]
    print(f"\n{len(panel)} of {len(want)} quarters read; missing: {missing or 'none'}")
    for s in skipped:
        print(f"  not read: {s}")
    for r in refused:
        print(f"  {r['archive']} [{r['period']}]: {len(r['mismatches'])} column(s) refused")
    have_rck = [p for p, v in sorted(panel.items()) if "3353" in v["columns_used"]]
    print(f"quarters carrying the RC-K average (3353): {have_rck}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(panel, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"written: {CACHE.relative_to(ROOT)}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
