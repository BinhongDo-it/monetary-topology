"""B121 cell 3: was the TAF edge big enough to reach the marginal unsecured borrower?

The framework's bound on what a new edge does is a closed form, with no estimate in it: an edge caps
the funding cost of the class that can take it at the edge's price plus that class's crossing cost,
and it does so only for the volume the edge carries. When an auction was oversubscribed, demand at
the edge's price was left off the edge, so the marginal term borrower was still paying the off-edge
price and the edge's price bounds nothing at the margin. When an auction was undersubscribed, every
eligible bank that wanted funds at the stop-out got them, and the wedge that is left over the edge's
price is a lower bound on the crossing cost of the banks that set LIBOR.

The Board printed one results release per auction: the offering amount (in the title), the stop-out
rate, total propositions submitted and accepted, the bid/cover ratio and the number of bidders. The
pages are cached in data/raw/b121/tafres/ (fetched 2026-09-23 from the yearly TAF archive pages).
The wedge is the rival's own LIBOR-OIS from results/b121_a2_panel.json, which ends on 2008-08-08.

The OIS is three-month and the TAF loans are 28 or 84 days, so `edge over OIS` compares a 28-day
fixed rate with a three-month expected overnight path; it is printed, not graded.

    python experiments/b121_taf_cover.py
    python experiments/b121_taf_cover.py --selftest
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "data" / "raw" / "b121" / "tafres"
PANEL = ROOT / "results" / "b121_a2_panel.json"
OUT = ROOT / "results" / "b121_taf_cover.json"
CAPACITY_CHANGE = ("2007-12-12", "2008-01-04", "2008-03-07", "2008-05-02", "2008-07-30")

TITLE = re.compile(r"results of (?:the )?auction of \$\s*([\d.]+) billion in (\d+)-day (?:term )?credit"
                   r" held on ([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)
FIELDS = {
    "stop_out": r"Stop-out rate:\s*([\d.]+)\s*percent",
    "submitted_bn": r"Total propositions submitted:\s*\$\s*([\d.,]+)",
    "accepted_bn": r"Total propositions accepted:\s*\$\s*([\d.,]+)",  # 2008-08-25 prints "$75.000" with no unit
    "bid_cover": r"Bid/cover ratio:\s*([\d.]+)",
    "bidders": r"Number of bidders:\s*(\d+)",
}


def text_of(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def parse(raw: str) -> dict | None:
    s = text_of(raw)
    m = TITLE.search(s)
    if not m:
        return None  # an announcement or a schedule, not a results release
    row = {"offered_bn": float(m.group(1)), "term_days": int(m.group(2)),
           "auction": dt.datetime.strptime(m.group(3), "%B %d, %Y").date().isoformat()}
    for k, rx in FIELDS.items():
        f = re.search(rx, s, re.I)
        if f is None:
            raise ValueError(f"results release for {row['auction']} does not print {k}")
        v = f.group(1).replace(",", "")
        row[k] = int(v) if k == "bidders" else float(v)
    row["unfilled_bn"] = round(row["submitted_bn"] - row["accepted_bn"], 3)
    row["full"] = row["submitted_bn"] > row["offered_bn"]
    return row


ANN_DATE = re.compile(r"Bid Submission Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})")
ANN_MAX = re.compile(r"Maximum Award:?\s*\$\s*([\d.,]+)\s*(billion|million)", re.I)
ANN_MIN = re.compile(r"Minimum Bid Rate:?\s*([\d.]+)\s*percent", re.I)
TAF_CSV = ROOT / "data" / "raw" / "b121" / "taf.csv"


def parse_announcement(raw: str) -> dict | None:
    """Bid day, the per-institution maximum award and the minimum bid rate, from an announcement."""
    s = text_of(raw)
    d, mx, mn = ANN_DATE.search(s), ANN_MAX.search(s), ANN_MIN.search(s)
    if not (d and mx):
        return None
    cap = float(mx.group(1).replace(",", "")) * (1000.0 if mx.group(2).lower() == "billion" else 1.0)
    return {"auction": dt.datetime.strptime(d.group(1), "%B %d, %Y").date().isoformat(),
            "max_award_mn": cap, "min_bid_rate": None if mn is None else float(mn.group(1))}


def loans_by_rate() -> dict[tuple[float, int], list[float]]:
    """Loan amounts (millions) keyed by (stop-out rate, term): one auction's winners share both."""
    import csv
    rows = list(csv.reader(TAF_CSV.open(encoding="utf-8-sig")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip().lower() == "loan date")
    h = [c.strip() for c in rows[hi]]
    iT, iR, iA, iD = h.index("Term"), h.index("Interest rate"), h.index("Loan amount"), h.index("Loan date")
    out: dict[tuple[str, float, int], list[float]] = {}
    for r in rows[hi + 1:]:
        if not r or not r[iD].strip():
            continue
        k = (r[iD].strip(), round(float(r[iR]), 3), int(r[iT]))
        out.setdefault(k, []).append(float(r[iA].replace(",", "")))
    return out


def at_cap(row: dict, loans: dict, caps: dict) -> None:
    """How many winners took the per-institution maximum award, and what share of the award they hold."""
    cap = caps.get(row["auction"])
    row["max_award_mn"] = None if cap is None else cap["max_award_mn"]
    row["min_bid_rate"] = None if cap is None else cap["min_bid_rate"]
    settle_after = dt.date.fromisoformat(row["auction"])
    cands = [(k, v) for k, v in loans.items() if k[1] == round(row["stop_out"], 3)
             and 0 <= (dt.datetime.strptime(k[0], "%b %d %Y").date() - settle_after).days <= 6
             and abs(k[2] - row["term_days"]) <= 3]
    if cap is None or len(cands) != 1:
        row["winners"] = row["winners_at_cap"] = row["share_at_cap"] = None
        return
    amounts = cands[0][1]
    hit = [a for a in amounts if a >= cap["max_award_mn"] - 0.5]
    row["winners"], row["winners_at_cap"] = len(amounts), len(hit)
    row["share_at_cap"] = round(sum(hit) / sum(amounts), 4)


def load_panel() -> dict[str, dict]:
    d = json.loads(PANEL.read_text(encoding="utf-8"))
    return {r["date"]: r for r in d["panel"]}


def wedge_on(panel: dict, day: str) -> tuple[str | None, float | None, float | None]:
    """LIBOR-OIS and OIS on the auction day, or the last day before it that prints both."""
    d = dt.date.fromisoformat(day)
    for back in range(0, 6):
        k = (d - dt.timedelta(days=back)).isoformat()
        r = panel.get(k)
        if r and r.get("libor3m") is not None and r.get("ois3m") is not None:
            return k, round(100 * (r["libor3m"] - r["ois3m"]), 1), r["ois3m"]
    return None, None, None


RIVAL_K_WINDOWS = (("2007-01-01", "2008-08-08"), ("2007-08-09", "2008-08-08"), ("2007-12-12", "2008-08-08"))


def rival_k(panel: dict) -> list[dict]:
    """The rival's own tenor scaling: OLS of LIBOR-OIS (bp) on the previous day's CDS median and the TAF
    dummy, the shape of the rival's `wucds2_libor` equation, on three windows. Printed, not graded."""
    import numpy as np
    days = sorted(panel)
    out = []
    for lo, hi in RIVAL_K_WINDOWS:
        X, y, prev = [], [], None
        for k in days:
            r = panel[k]
            if (lo <= k <= hi and r.get("libor3m") is not None and r.get("ois3m") is not None
                    and prev is not None and prev.get("cds_median") is not None):
                X.append([1.0, prev["cds_median"], 1.0 if k >= "2007-12-12" else 0.0])
                y.append(100 * (r["libor3m"] - r["ois3m"]))
            if r.get("cds_median") is not None:
                prev = r
        b = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)[0]
        out.append({"window": [lo, hi], "n": len(y), "k": round(float(b[1]), 3), "taf_dummy_bp": round(float(b[2]), 1)})
    return out


def build(rows: list[dict], panel: dict) -> dict:
    for r in rows:
        day, w, ois = wedge_on(panel, r["auction"])
        r["wedge_day"], r["wedge_bp"] = day, w
        r["edge_over_ois_bp"] = None if ois is None else round(100 * (r["stop_out"] - ois), 1)
        r["left_over_bp"] = None if w is None else round(w - r["edge_over_ois_bp"], 1)
    # the crossing cost from a printed number: a bank that takes the auction's funds and lends them on at LIBOR
    # carries the borrower's default risk, and the rival's own workbook prices that risk as the median CDS of
    # fifteen LIBOR banks (column CDSMEDIAN2; the package does not print its tenor). The closed form then gives
    # the narrowing of LIBOR-OIS the edge can buy as max(0, left over - k * CDS), and k is the tenor scaling,
    # which no source prints; so the reading is the k at which that narrowing first turns positive.
    for r in rows:
        q = panel.get(r["wedge_day"]) if r["wedge_day"] else None
        r["cds_bp"] = None if not q or q.get("cds_median") is None else round(q["cds_median"], 1)
        r["narrowing_at_k1_bp"] = None if r["cds_bp"] is None else round(max(0.0, r["left_over_bp"] - r["cds_bp"]), 1)
        r["k_flip"] = (None if r["cds_bp"] in (None, 0) or r["left_over_bp"] is None
                       else round(max(0.0, r["left_over_bp"]) / r["cds_bp"], 3))
    # instrument: the printed bid/cover must be submitted over offered, to the page's two decimals
    bad = [r["auction"] for r in rows if abs(r["submitted_bn"] / r["offered_bn"] - r["bid_cover"]) > 0.0051]
    inwin = [r for r in rows if r["wedge_bp"] is not None]
    before = {}
    for c in CAPACITY_CHANGE:
        prior = [r for r in rows if r["auction"] < c]
        before[c] = None if not prior else {k: prior[-1][k] for k in ("auction", "bid_cover", "unfilled_bn", "full")}
    crit = [
        {"name": "B121-26", "kind": "instrument",
         "statement": "every results release parses, and its printed bid/cover equals submitted over offered",
         "passed": bool(rows) and not bad,
         "detail": f"{len(rows)} releases parsed; bid/cover disagreeing with submitted/offered: {bad or 'none'}"},
        {"name": "B121-27", "kind": "own_reading",
         "statement": "print, for each auction in the rival's window, whether the edge was full and the wedge left over its price",
         "passed": bool(inwin) and all(r["left_over_bp"] is not None for r in inwin),
         "detail": (f"{sum(r['full'] for r in inwin)} of {len(inwin)} auctions to 2008-08-08 were oversubscribed; "
                    f"all {len(rows)}: {sum(r['full'] for r in rows)} oversubscribed")},
        {"name": "B121-28", "kind": "own_reading",
         "statement": ("print, for each auction in the rival's window, the narrowing of LIBOR-OIS the closed form allows "
                       "with the rival's CDS as the crossing cost, and the tenor scaling k at which it first turns positive"),
         "passed": bool(inwin) and all(r["k_flip"] is not None for r in inwin),
         "detail": (("narrowing at k = 1: " + ", ".join(f"{r['narrowing_at_k1_bp']:.1f}" for r in inwin)
                     + f"; largest k at which any auction allows a narrowing: {max(r['k_flip'] for r in inwin):.3f}")
                    if inwin and all(r["k_flip"] is not None for r in inwin) else "no CDS on some auction day")},
    ]
    rk = rival_k(panel) if len(panel) > 30 else []
    return {"stage": "B121", "rows": rows, "before_capacity_change": before, "criteria": crit, "rival_k": rk,
            "source": {"pages": "data/raw/b121/tafres", "panel": "results/b121_a2_panel.json"}}


def selftest() -> None:
    page = ("<title>x</title><p>Federal Reserve announces results of auction of $20 billion in 28-day credit "
            "held on December 17, 2007</p><p>Stop-out rate: 4.650 percent Total propositions submitted: "
            "$61.553 billion Total propositions accepted: $20.000 billion Bid/cover ratio: 3.08 "
            "Number of bidders: 93</p>")
    r = parse(page)
    assert r and r["full"] and r["unfilled_bn"] == 41.553 and r["auction"] == "2007-12-17", r
    assert parse("<p>Federal Reserve announces auction of $20 billion</p>") is None
    slack = parse(page.replace("$61.553", "$15.000").replace("3.08", "0.75"))
    assert slack and not slack["full"]
    panel = {"2007-12-17": {"date": "2007-12-17", "libor3m": 4.95, "ois3m": 4.30}}
    out = build([dict(r)], panel)
    assert out["rows"][0]["left_over_bp"] == 65.0 - 35.0, out["rows"][0]
    assert out["criteria"][0]["passed"]
    broken = dict(r, bid_cover=2.00)  # a page whose bid/cover does not match its own totals must fail
    assert not build([broken], panel)["criteria"][0]["passed"]
    assert not build([], panel)["criteria"][1]["passed"]
    assert not build([dict(r)], panel)["criteria"][2]["passed"]  # no CDS on the day: the reading has no object
    withcds = build([dict(r)], {"2007-12-17": dict(panel["2007-12-17"], cds_median=20.0)})["rows"][0]
    assert withcds["narrowing_at_k1_bp"] == 10.0 and withcds["k_flip"] == 1.5, withcds
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
        return 0
    rows = [p for p in (parse(f.read_text(encoding="utf-8", errors="ignore"))
                        for f in sorted(PAGES.glob("2*.html"))) if p]
    rows.sort(key=lambda r: (r["auction"], r["term_days"]))
    caps = {a["auction"]: a for a in (parse_announcement(f.read_text(encoding="utf-8", errors="ignore"))
                                      for f in sorted(PAGES.glob("2*.html"))) if a}
    loans = loans_by_rate()
    for r in rows:
        at_cap(r, loans, caps)
    out = build(rows, load_panel())
    print(f"{'auction':<11}{'term':>5}{'offer':>7}{'bids':>9}{'b/c':>6}{'stop':>7}{'wedge':>7}{'edge-OIS':>9}{'left':>7}")
    for r in rows:
        f = lambda v: "" if v is None else f"{v:.1f}"
        print(f"{r['auction']:<11}{r['term_days']:>5}{r['offered_bn']:>7.0f}{r['submitted_bn']:>9.3f}{r['bid_cover']:>6.2f}"
              f"{r['stop_out']:>7.3f}{f(r['wedge_bp']):>7}{f(r['edge_over_ois_bp']):>9}{f(r['left_over_bp']):>7}  cap {r['winners_at_cap']}/{r['winners']} ({r['share_at_cap']})  min {r['min_bid_rate']}  cds {r.get('cds_bp')}  k* {r.get('k_flip')}")
    for w in out["rival_k"]:
        print(f"rival's own k on {w['window'][0]}..{w['window'][1]}: {w['k']} (n {w['n']}, TAF dummy {w['taf_dummy_bp']} bp)")
    print("\nlast auction before each capacity change:")
    for c, b in out["before_capacity_change"].items():
        print(f"  {c}: {b}")
    for c in out["criteria"]:
        print(f"{c['name']} [{c['kind']}] {'PASS' if c['passed'] else 'FAIL'}: {c['detail']}")
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return 0 if all(c["passed"] for c in out["criteria"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
