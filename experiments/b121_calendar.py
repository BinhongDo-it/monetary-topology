"""B121: how clean is each event window? A calendar of everything else that happened.

Every reading in this station attributes a move to one action on one day, and in 2007-09 many things
moved together. This builds a calendar from the New York Fed's own crisis timelines, one entry per
dated item, and prints, for each event day the station reads, every other entry within a few trading
days. It scores nothing: it lists what else was in each window so the attribution can be judged.

  sources  data/raw/b121/nyfed_Crisis_Timeline.pdf   (US: Fed actions, market events, other policy)
           data/raw/b121/nyfed_IRCTimelinePublic.pdf (other countries' central banks and governments)
           both from newyorkfed.org/research/global_economy/policyresponses.html

    python experiments/b121_calendar.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b121"
OUT = ROOT / "results" / "b121_calendar.json"
PDFS = {"US": RAW / "nyfed_Crisis_Timeline.pdf", "International": RAW / "nyfed_IRCTimelinePublic.pdf"}
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                                   "Oct", "Nov", "Dec"], start=1)}
DATE = re.compile(r"(?m)^\s*(\d{1,2})-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b")
TITLE = re.compile(r"\(\s*([A-Z][a-z]+)\.?\s*(\d{4})?\s*(?:-|–|thru)\s*([A-Z][a-z]+)\.?\s*(\d{4})\s*\)")


def month_years(title: str) -> dict[int, int]:
    """Map each month on a page to its year, from the page title's range."""
    m = TITLE.search(title)
    if not m:
        return {}
    m1, y1, m2, y2 = m.group(1)[:3], m.group(2), m.group(3)[:3], int(m.group(4))
    a, b = MON[m1], MON[m2]
    y1 = int(y1) if y1 else (y2 if a <= b else y2 - 1)
    out, y, mo = {}, y1, a
    for _ in range(14):
        out[mo] = y
        if mo == b and y == y2:
            break
        mo += 1
        if mo == 13:
            mo, y = 1, y + 1
    return out


def rows_of(page) -> list[tuple[float, str]]:
    """Row labels on the left edge, with their vertical position."""
    labels = []
    for b in page.get_text("blocks"):
        text = b[4].strip()
        if b[0] < 120 and text and not DATE.match(text) and len(text) < 60 and "Timeline" not in text:
            labels.append((b[1], " ".join(text.split())))
    return sorted(labels)


def parse(source: str, path: Path) -> list[dict]:
    doc = pymupdf.open(path)
    out = []
    for pno in range(doc.page_count):
        page = doc[pno]
        blocks = page.get_text("blocks")
        title = next((b[4] for b in blocks if "Timeline" in b[4]), "")
        years = month_years(" ".join(title.split()))
        labels = rows_of(page)
        for b in blocks:
            text = b[4]
            hits = list(DATE.finditer(text))
            for k, h in enumerate(hits):
                end = hits[k + 1].start() if k + 1 < len(hits) else len(text)
                body = " ".join(text[h.end():end].split())
                mo = MON[h.group(2)[:3]]
                if mo not in years or not body:
                    continue
                try:
                    day = dt.date(years[mo], mo, int(h.group(1))).isoformat()
                except ValueError:
                    continue
                above = [lab for y, lab in labels if y <= b[1] + 5]
                out.append({"date": day, "source": source, "row": above[-1] if above else "",
                            "text": body.replace("ﬁ", "fi").replace("ﬀ", "ff"),
                            "page": pno + 1})
    return out


# The event days the station reads, with the words that mark an entry as the same action.
EVENT_SETS = {
    "A2 capacity (TAF)": (["2007-12-12", "2008-01-04", "2008-03-07", "2008-05-02", "2008-07-30"],
                          r"TAF|Term Auction|swap"),
    "A1 supply (swap lines)": (["2007-12-12", "2008-05-02", "2008-07-30", "2008-09-18", "2008-09-24",
                                "2008-10-13", "2008-10-14"], r"swap|currency arrangement|TAF|Term Auction"),
    "rate changes": (["2007-09-18", "2007-10-31", "2007-12-11", "2008-01-22", "2008-01-30",
                      "2008-03-18", "2008-04-30", "2008-10-08", "2008-10-29", "2008-12-16"],
                     r"target|fed funds|rate lowered|lowers|cut"),
}


def main() -> int:
    cal = []
    for source, path in PDFS.items():
        entries = parse(source, path)
        print(f"{source}: {len(entries)} dated entries, {min(e['date'] for e in entries)} to "
              f"{max(e['date'] for e in entries)}")
        cal += entries
    cal.sort(key=lambda e: (e["date"], e["source"]))

    audit = {}
    for name, (days, same) in EVENT_SETS.items():
        print(f"\n===== {name}")
        audit[name] = {}
        for d in days:
            d0 = dt.date.fromisoformat(d)
            near = [e for e in cal if abs((dt.date.fromisoformat(e["date"]) - d0).days) <= 3]
            own = [e for e in near if e["date"] == d and re.search(same, e["text"], re.I)]
            other = [e for e in near if e not in own]
            audit[name][d] = {"same_action": own, "other_within_3_days": other}
            print(f"  {d}: {len(own)} entries for this action, {len(other)} other entries within 3 calendar days")
            for e in other:
                print(f"      {e['date']} [{e['source']}/{e['row'][:22]}] {e['text'][:110]}")

    record = {"stage": "B121", "diagnostic_only": True,
              "diagnostic_reason": "A calendar for judging each event window; it scores nothing.",
              "config": {"window_calendar_days": 3},
              "source": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in PDFS.items()},
              "calendar": cal, "audit": audit}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8",
                   newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}  ({len(cal)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
