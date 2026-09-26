"""B121 arm A2, part four: build the window past the rival's data and print what is in it.

No criteria here. The rival's workbook ends on 2008-08-08, before Lehman. This part builds the
same object for 2008-08-11 to 2009-12-31 from sources that are free and public, checks each
substitute against the rival's own column where the two overlap, and prints the objects.

  LIBOR leg   TEDRATE + DTB3, both FRED. Returns the workbook's US0003M within half a basis point.
  OIS leg     no free series exists. The stand-in is the effective federal funds rate actually
              realised over the next three months (DFF), which is what a three-month OIS pays at
              maturity. It is checked against the workbook's USSOC on the overlap.
  events      rate days from DFEDTAR and DFEDTARU; auction days from the Board's own TAF loan file
              (every winner of one auction borrows on the same day at the same rate); announcement
              days from the list of TAF press releases on the Board's TAF page, each with its title.

    python experiments/b121_a2_extension_panel.py
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b121"
MAIN = ROOT / "results" / "b121_a2_panel.json"
OUT = ROOT / "results" / "b121_a2_extension_panel.json"
FIRST, LAST = "2008-08-11", "2009-12-31"
HORIZON_DAYS = 91      # three calendar months, the tenor of the OIS being stood in for

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def fred(sid: str) -> dict[str, float]:
    rows = list(csv.reader((RAW / f"{sid}.csv").open(encoding="utf-8")))[1:]
    return {r[0]: float(r[1]) for r in rows if len(r) > 1 and r[1] not in ("", ".", "NA")}


def realised_ois(dff: dict[str, float], day: str, horizon: int = HORIZON_DAYS) -> float | None:
    """Mean effective funds rate over the next `horizon` calendar days, the leg an OIS pays."""
    d0 = dt.date.fromisoformat(day)
    vals = [dff.get((d0 + dt.timedelta(days=k)).isoformat()) for k in range(1, horizon + 1)]
    vals = [v for v in vals if v is not None]
    return statistics.fmean(vals) if len(vals) >= horizon * 0.9 else None


def taf_auction_days() -> dict[str, dict]:
    """One row per auction: its day, how many loans, how much, and the single rate all paid."""
    rows = list(csv.reader((RAW / "taf.csv").open(encoding="utf-8-sig")))
    head_i = next(i for i, r in enumerate(rows) if r and r[0].strip().lower() == "loan date")
    head = [c.strip() for c in rows[head_i]]
    i_day, i_amt, i_rate = head.index("Loan date"), head.index("Loan amount"), head.index("Interest rate")
    out: dict[str, dict] = {}
    for r in rows[head_i + 1:]:
        if not r or not r[i_day].strip():
            continue
        day = dt.datetime.strptime(r[i_day].strip(), "%b %d %Y").date().isoformat()
        a = out.setdefault(day, {"loans": 0, "amount_mn": 0.0, "rates": set()})
        a["loans"] += 1
        a["amount_mn"] += float(r[i_amt].replace(",", ""))
        a["rates"].add(r[i_rate].strip())
    return {d: {"loans": v["loans"], "amount_mn": round(v["amount_mn"], 1),
                "rates": sorted(v["rates"])} for d, v in sorted(out.items())}


def taf_announcements() -> list[dict]:
    """The Board's own list of TAF press releases, each with its date and its title."""
    t = (RAW / "taf_results.html").read_text(encoding="utf-8", errors="replace")
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
    start = txt.find("Related Press Releases")
    block = txt[start:txt.find("More Information", start)] if start >= 0 else ""
    items = re.findall(rf"(.+?)\(((?:{MONTHS}) \d{{1,2}}, 20\d\d)\)", block)
    out = []
    for title, date in items:
        title = title.replace("Related Press Releases", "").strip()
        d = dt.datetime.strptime(date, "%B %d, %Y").date().isoformat()
        low = title.lower()
        kind = ("reduction" if any(w in low for w in ("reduced", "reduce")) else
                "not the facility's size" if any(w in low for w in ("interest on", "margins")) else
                "expansion or schedule")
        out.append({"date": d, "title": title, "kind": kind})
    return sorted(out, key=lambda x: x["date"])


def main() -> int:
    ted, tb3, dff = fred("TEDRATE"), fred("DTB3"), fred("DFF")
    tar, taru = fred("DFEDTAR"), fred("DFEDTARU")
    target = {**tar, **taru}

    # The stand-in for OIS, checked where the rival's own OIS exists.
    main_rows = json.loads(MAIN.read_text(encoding="utf-8"))["panel"]
    pairs = [(r["date"], realised_ois(dff, r["date"]), r["ois3m"]) for r in main_rows
             if r["ois3m"] is not None]
    pairs = [p for p in pairs if p[1] is not None]
    gap = [(a - b) * 100 for _, a, b in pairs]
    after = [(a - b) * 100 for d, a, b in pairs if d >= "2007-08-09"]
    print(f"realised three-month DFF against the workbook's USSOC: {len(pairs)} days, "
          f"median gap {statistics.median(gap):+.1f} bp, from 2007-08-09 {statistics.median(after):+.1f} bp, "
          f"largest {max(gap, key=abs):+.1f} bp")
    # How much of the spread's movement survives the stand-in: correlation of daily changes.
    wb_spread = {r["date"]: r["spread"] for r in main_rows if r["spread"] is not None}
    sub = {d: (ted[d] + tb3[d]) - o for d, o, _ in pairs if d in ted and d in tb3}
    common = sorted(set(wb_spread) & set(sub))
    dw = [wb_spread[b] - wb_spread[a] for a, b in zip(common, common[1:])]
    ds = [sub[b] - sub[a] for a, b in zip(common, common[1:])]
    corr_changes = statistics.correlation(dw, ds)
    corr_levels = statistics.correlation([wb_spread[d] for d in common], [sub[d] for d in common])
    print(f"the substitute spread against the workbook's own spread: {len(common)} days, "
          f"levels correlate {corr_levels:.4f}, daily changes correlate {corr_changes:.4f}")

    # Announcements, and the free known-answer check against the rival's own marks.
    ann = taf_announcements()
    wb_ann = sorted(r["date"] for r in main_rows if r["taf_announce_day"])
    page_main = sorted(a["date"] for a in ann if a["date"] <= "2008-08-08")
    print(f"\nthe Board's TAF page lists {len(ann)} releases; {len(page_main)} fall in the main window")
    print(f"  on the page and marked in the workbook: {sorted(set(page_main) & set(wb_ann))}")
    print(f"  on the page only:                       {sorted(set(page_main) - set(wb_ann))}")
    print(f"  marked in the workbook only:            {sorted(set(wb_ann) - set(page_main))}")
    print("\nreleases in the extension window:")
    for a in ann:
        if FIRST <= a["date"] <= LAST:
            print(f"  {a['date']}  [{a['kind']}]  {a['title'][:110]}")

    auctions = taf_auction_days()
    ext_auctions = {d: v for d, v in auctions.items() if FIRST <= d <= LAST}
    one_rate = sum(1 for v in auctions.values() if len(v["rates"]) == 1)
    print(f"\nTAF loan days in the Board's file: {len(auctions)}, "
          f"{one_rate} of them at a single rate for every loan; "
          f"{len(ext_auctions)} in the extension window")

    # The extension panel itself.
    days = sorted(d for d in ted if FIRST <= d <= LAST and d in tb3)
    panel, steps = [], []
    prev_t = None
    for d in days:
        o = realised_ois(dff, d)
        t = target.get(d)
        if prev_t is not None and t is not None and abs(t - prev_t) > 1e-9:
            steps.append({"date": d, "step_pp": round(t - prev_t, 4), "target_after": t})
        prev_t = t if t is not None else prev_t
        panel.append({
            "date": d, "libor3m": round(ted[d] + tb3[d], 6), "ois_realised": None if o is None else round(o, 6),
            "spread": None if o is None else round(ted[d] + tb3[d] - o, 6), "target": t,
            "rate_change_day": bool(steps and steps[-1]["date"] == d),
            "taf_auction_day": d in ext_auctions,
            "taf_announce_day": any(a["date"] == d and a["kind"] == "expansion or schedule" for a in ann),
            "taf_reduce_day": any(a["date"] == d and a["kind"] == "reduction" for a in ann),
        })
    sp = [r["spread"] for r in panel if r["spread"] is not None]
    print(f"\nextension panel: {len(panel)} days, spread on {len(sp)}; "
          f"median {statistics.median(sp) * 100:.1f} bp, highest {max(sp) * 100:.1f} bp on "
          f"{max((r for r in panel if r['spread'] is not None), key=lambda r: r['spread'])['date']}")
    print(f"rate steps in the window: {[(s['date'], s['step_pp']) for s in steps]}")

    record = {
        "stage": "B121",
        "diagnostic_only": True,
        "diagnostic_reason": "Part four of arm A2. It builds the extension window and prints the "
                             "objects in it; no criterion is scored here.",
        "config": {"window": [FIRST, LAST], "ois_horizon_days": HORIZON_DAYS},
        "source": {"libor": "TEDRATE + DTB3 (FRED)", "ois": "realised DFF over the next 91 days (FRED)",
                   "auctions": "Board of Governors, TAF transaction data, taf.csv",
                   "announcements": "Board of Governors, TAF page, list of related press releases"},
        "ois_substitute_check": {"days": len(pairs), "median_gap_bp": round(statistics.median(gap), 3),
                                 "median_gap_from_2007_08_09_bp": round(statistics.median(after), 3),
                                 "largest_gap_bp": round(max(gap, key=abs), 3),
                                 "spread_levels_corr": round(corr_levels, 6),
                                 "spread_changes_corr": round(corr_changes, 6)},
        "announcement_check": {"page_in_main_window": page_main, "workbook_marks": wb_ann,
                               "both": sorted(set(page_main) & set(wb_ann)),
                               "page_only": sorted(set(page_main) - set(wb_ann)),
                               "workbook_only": sorted(set(wb_ann) - set(page_main))},
        "announcements": ann,
        "auctions": auctions,
        "rate_steps": steps,
        "panel": panel,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT.relative_to(ROOT)}  ({len(panel)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
