# -*- coding: utf-8 -*-
"""B19 gate zero: two Shariah debt screens, one whose threshold moves with the
price and one whose threshold does not, counted for how many cells clear.

The gate under test has the shape of A3 section 3's, `claims_i >= gamma * P`:

    market-cap denominator   debt_i <= 0.30   * MarketCap_i
    total-asset denominator  debt_i <= 0.3333 * Assets_i

The first threshold moves with the price, so a fall in the share price raises the
ratio and pushes out a firm that did nothing at all. The second does not move.
Same firm, same period, two rulebooks: the control arm is supplied by the
institutions rather than constructed here, which is the reason to prefer this
carrier over the ones this project has already tried.

This file only runs gate zero. Gate zero is a count, it is free, and it can veto:
what it asks is how many cells clear their own requirement, not how many
observations there are per cell on average.

Three modes, in the order the discipline requires: enumerate the full tag set
first, choose from it second, never guess and then confirm.

    --probe          enumerate every tag in num.txt, classify by name, rank by
                     coverage. Chooses nothing.
    --emit-tickers   write the symbol list the price fetcher needs
    --gate0          run both screens and count the cells

Criterion shape: no threshold is drawn on any estimate anywhere in this file. What
gets printed is the funnel step by step, the members that the two rulebooks judge
differently (with names, not only a count), the price-decline bucket by whether
the breathing gate pushed the firm out, and the three smallest cells.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

RAW = Path("data") / "raw" / "shariah"
OUT = Path("results") / "b19_shariah_gate0.json"

# Published values, fixed before the run. AAOIFI and S&P divide by market cap;
# MSCI and FTSE divide by total assets.
GAMMA_MCAP = 0.30
GAMMA_ASSETS = 1.0 / 3.0

# Name patterns for --probe. These classify, they do not select: the selection is
# made after reading what --probe prints.
# The first version required an uppercase letter or line start immediately before
# `Debt`, which drops the whole `LongTermDebt*` family, since the `D` there follows
# a lowercase `m`. Printing the top of the ranking is what exposed it: an earlier
# scan had `LongTermDebtNoncurrent` at 26 percent and this one did not list it at all.
DEBT_PAT = re.compile(
    r"Debt|Borrowing|NotesPayable|LoansPayable|LineOfCredit|LinesOfCredit|"
    r"CommercialPaper|FinanceLeaseLiability|CapitalLeaseObligation")

# Matched by the pattern above and not a borrowing: securities held as assets,
# gains and losses, conversion and issuance detail, rates and maturities.
DEBT_NOT = re.compile(
    r"DebtSecurit|DebtAndEquity|DebtConversion|GainLoss|Unrealized|Realized|"
    r"InterestRate|WeightedAverage|Maturit|Amortization|Accretion|Fair(?:Value)?|"
    r"Issuance|Extinguish|Covenant|Percentage|Ratio|Term(?:OfDebt)?$|"
    r"AvailableForSale|HeldToMaturity|Investment|Discount|Premium|"
    # Cash-flow items. A screen on a debt balance is a statement about a stock, and
    # `RepaymentsOfLongTermDebt` is a flow. The qtrs filter already drops them where
    # the panel is built; naming them here keeps the probe reading the same universe.
    r"Proceeds|Repayments|Payments|IncreaseDecrease|InterestExpense|CashFlow")

# Leases are interest-bearing in accounting terms, but ijara is a compliant form of
# finance, so a screen written for this purpose should not fold them into debt. Both
# unions are reported and never summed into one column.
LEASE_PAT = re.compile(r"LeaseLiability|LeaseObligation")

SHARES_PAT = re.compile(r"Shares(?:Outstanding|Issued)|SharesOutstanding")

# Working defaults for --gate0. Revise from the --probe ranking; every change here
# changes what "debt" means and must travel with any number this file produces.
# Mutually exclusive groups, not one flat list. Within a group the first tag that
# is present wins; across groups the values are summed. A flat sum double counts,
# because `LongTermDebt` is normally the sum of its own current and noncurrent
# parts, and a filer that reports all three would have its long-term debt counted
# twice. That error is one-directional: it can only inflate the ratio, and the
# ratio is what decides whether a firm is pushed out.
DEBT_GROUPS = [
    ["LongTermDebtNoncurrent", "OtherLongTermDebtNoncurrent"],
    ["LongTermDebtCurrent"],
    ["ShortTermBorrowings", "DebtCurrent"],
    ["NotesPayableCurrent", "LoansPayableCurrent"],
    ["LinesOfCreditCurrent", "LineOfCredit"],
    ["CommercialPaper"],
]
# Used only when the first two groups are both absent: this is the aggregate that
# would have double counted against them.
DEBT_FALLBACK = ["LongTermDebt", "NotesPayable"]
DEBT_TAGS = sorted({t for g in DEBT_GROUPS for t in g} | set(DEBT_FALLBACK))
SHARES_TAGS = [
    "CommonStockSharesOutstanding", "CommonStockSharesIssued",
    "EntityCommonStockSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
]
ASSET_TAG = "Assets"


def _rows(zf: zipfile.ZipFile, name: str):
    with zf.open(name) as fh:
        yield from csv.DictReader((ln.decode("utf-8", "replace") for ln in fh),
                                  delimiter="\t")


def _norm_cik(v: str) -> str:
    v = (v or "").strip()
    try:
        return str(int(v))          # sub.txt pads with zeros, the ticker map does not
    except ValueError:
        return v


def cmd_probe(args) -> None:
    """Enumerate the whole tag set before choosing any of it."""
    zips = sorted(RAW.glob("*.zip"))[: args.quarters]
    if not zips:
        print("no quarterly zip found. run: python -m data.fetch_shariah --stage sec")
        sys.exit(2)
    print(f"scanning {len(zips)} quarter(s) in full; coverage is stable across quarters,\n"
          f"so more than a couple buys nothing here\n")
    for zp in zips:
        filers, by_tag = set(), defaultdict(set)
        with zipfile.ZipFile(zp) as z:
            keep = {}
            for r in _rows(z, "sub.txt"):
                if r.get("form") in ("10-K", "10-Q"):
                    keep[r["adsh"]] = _norm_cik(r.get("cik", ""))
                    filers.add(keep[r["adsh"]])
            for r in _rows(z, "num.txt"):
                a = r.get("adsh")
                # Same filter the panel uses. Without it the probe counts a universe
                # the panel never sees, and its ceiling is not the one gate0 gets.
                if a in keep and r.get("qtrs") in ("0", ""):
                    by_tag[r.get("tag", "")].add(keep[a])
        n = max(len(filers), 1)
        print(f"--- {zp.stem}   {len(filers)} filers, {len(by_tag)} distinct tags")
        def keep_debt(tag: str) -> bool:
            return bool(DEBT_PAT.search(tag)) and not DEBT_NOT.search(tag)

        borrow = {t: s for t, s in by_tag.items() if keep_debt(t) and not LEASE_PAT.search(t)}
        lease = {t: s for t, s in by_tag.items() if keep_debt(t) and LEASE_PAT.search(t)}
        dropped = {t: s for t, s in by_tag.items()
                   if DEBT_PAT.search(t) and DEBT_NOT.search(t)}
        for label, d in (("BORROWINGS (main reading)", borrow),
                         ("LEASES (reported apart, ijara)", lease),
                         ("EXCLUDED as not a borrowing", dropped)):
            hits = sorted(((k, len(v)) for k, v in d.items()), key=lambda x: -x[1])
            print(f"  {label}: {len(hits)} tags; top {min(20, len(hits))} by coverage")
            for tg, c in hits[:20]:
                print(f"    {tg:56s} {c:6d}  {c/n:6.1%}")
            u = set().union(*d.values()) if d else set()
            print(f"    {'UNION':56s} {len(u):6d}  {len(u)/n:6.1%}")
        hits = sorted(((k, len(v)) for k, v in by_tag.items() if SHARES_PAT.search(k)),
                      key=lambda x: -x[1])
        print(f"  SHARES-LIKE: {len(hits)} tags; top 8 by coverage")
        for tg, c in hits[:8]:
            print(f"    {tg:56s} {c:6d}  {c/n:6.1%}")
        a = by_tag.get(ASSET_TAG, set())
        du = set().union(*borrow.values()) if borrow else set()
        dul = du | (set().union(*lease.values()) if lease else set())
        su = set().union(*[s for t, s in by_tag.items() if SHARES_PAT.search(t)] or [set()])
        print(f"  FUNNEL, one step at a time so a zero says which step produced it:")
        print(f"    {'Assets':40s} {len(a):6d}  {len(a)/n:6.1%}")
        sel = set().union(*[by_tag.get(tg, set()) for tg in DEBT_TAGS]) if DEBT_TAGS else set()
        print(f"    {'+ any borrowing (all such tags)':40s} {len(a & du):6d}  {len(a & du)/n:6.1%}")
        print(f"    {'+ the tags DEBT_GROUPS selects':40s} {len(a & sel):6d}  {len(a & sel)/n:6.1%}   <- what gate0 gets")
        print(f"    {'+ any shares-like':40s} {len(a & sel & su):6d}  {len(a & sel & su)/n:6.1%}   <- ceiling, ex leases")
        lease_u = set().union(*lease.values()) if lease else set()
        print(f"    {'ceiling if leases count as debt':40s} {len(a & (sel | lease_u) & su):6d}  "
              f"{len(a & (sel | lease_u) & su)/n:6.1%}")
        print()


def load_quarter(zpath: Path, tags: set[str]):
    subs, vals = {}, {}
    with zipfile.ZipFile(zpath) as z:
        for r in _rows(z, "sub.txt"):
            if r.get("form") not in ("10-K", "10-Q"):
                continue
            subs[r["adsh"]] = {"cik": _norm_cik(r.get("cik", "")), "name": r.get("name", ""),
                               "period": r.get("period", ""), "sic": r.get("sic", "")}
        for r in _rows(z, "num.txt"):
            tag = r.get("tag", "")
            if tag not in tags or r.get("qtrs") not in ("0", ""):
                continue
            # A parent and its wholly owned subsidiaries file one report together, and
            # num.txt carries a row per entity. The subsidiary rows are legal values for
            # a different company: a utility holding company reads 229 million shares
            # and its subsidiary reads 1. Taking whichever arrives last mixes them under
            # one CIK, and every value stays valid while the entity stops being one.
            if r.get("coreg"):
                continue
            if r.get("segments"):        # dimensional slices, not the consolidated line
                continue
            adsh = r.get("adsh", "")
            if adsh not in subs:
                continue
            try:
                x = float(r.get("value", ""))
            except (TypeError, ValueError):
                continue
            d = r.get("ddate", "")
            k = (adsh, tag)
            if k not in vals or d > vals[k][1]:
                vals[k] = (x, d)
    return subs, vals


def build_panel(zips, debt_tags, shares_tags):
    want = set(debt_tags) | set(shares_tags) | {ASSET_TAG}
    panel, funnel = defaultdict(dict), defaultdict(int)
    for zp in zips:
        subs, vals = load_quarter(zp, want)
        for adsh, s in subs.items():
            funnel["filings"] += 1
            a = vals.get((adsh, ASSET_TAG))
            if a is None or a[0] <= 0:
                continue
            funnel["has_assets"] += 1
            debt, got = 0.0, False
            long_term_seen = False
            for gi, grp in enumerate(DEBT_GROUPS):
                for tg in grp:                      # first present tag in the group wins
                    v = vals.get((adsh, tg))
                    if v is not None:
                        debt += v[0]
                        got = True
                        if gi < 2:
                            long_term_seen = True
                        break
            if not long_term_seen:                  # only then is the aggregate safe
                for tg in DEBT_FALLBACK:
                    v = vals.get((adsh, tg))
                    if v is not None:
                        debt += v[0]
                        got = True
                        break
            if not got:
                continue
            funnel["has_debt"] += 1
            sh = None
            for t in shares_tags:            # first hit wins, in the listed order
                v = vals.get((adsh, t))
                if v is not None and v[0] > 0:
                    sh = v[0]
                    break
            if sh is None:
                continue
            funnel["has_shares"] += 1
            key = s["period"] or a[1]
            panel[s["cik"]][key] = {"debt": debt, "assets": a[0], "shares": sh,
                                    "name": s["name"], "sic": s["sic"]}
    return panel, funnel


def _ticker_map():
    tk = RAW / "company_tickers.json"
    if not tk.exists():
        return {}
    try:
        raw = json.loads(tk.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"company_tickers.json does not parse ({type(e).__name__}); "
              f"re-run the fetcher, it now keeps the bad copy aside and re-downloads")
        sys.exit(3)
    out = {}
    for rec in raw.values():
        out.setdefault(str(int(rec["cik_str"])), rec["ticker"].upper())
    return out


def cmd_emit_tickers(args) -> None:
    zips = sorted(RAW.glob("*.zip"))
    panel, funnel = build_panel(zips, DEBT_TAGS, SHARES_TAGS)
    cik2sym = _ticker_map()
    if not cik2sym:
        print("missing company_tickers.json; run the fetcher first")
        sys.exit(2)
    syms = sorted({cik2sym[c] for c in panel if c in cik2sym})
    dest = RAW / "tickers_needed.txt"
    dest.write_text("\n".join(syms) + "\n", encoding="utf-8", newline="\n")
    for k in ("filings", "has_assets", "has_debt", "has_shares"):
        print(f"  {k:14s} {funnel[k]}")
    print(f"  {'firms':14s} {len(panel)}")
    print(f"  {'with a ticker':14s} {len(syms)}  -> {dest}")


def load_prices():
    d = RAW / "prices"
    px = {}
    if not d.is_dir():
        return px
    for f in sorted(d.glob("*.csv")):
        rows = []
        for r in csv.DictReader(f.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                rows.append((r["Date"], float(r["Close"])))
            except (KeyError, ValueError):
                continue
        if rows:
            px[f.stem.upper()] = sorted(rows)
    return px


def cmd_gate0(args) -> None:
    zips = sorted(RAW.glob("*.zip"))
    if not zips:
        print("no quarterly zip found")
        sys.exit(2)
    panel, funnel = build_panel(zips, DEBT_TAGS, SHARES_TAGS)
    px = load_prices()
    cik2sym = _ticker_map()

    rows, disagree = [], []
    for cik, periods in sorted(panel.items()):
        sym = cik2sym.get(cik)
        series = px.get(sym) if sym else None
        for period, rec in sorted(periods.items()):
            mcap = ret = None
            if series and period:
                p = period.replace("-", "")
                on = [(d, c) for d, c in series if d.replace("-", "") <= p]
                if on:
                    mcap = on[-1][1] * rec["shares"]
                    back = [(d, c) for d, c in on if d.replace("-", "") <= str(int(p) - 10000)]
                    if back:
                        ret = on[-1][1] / back[-1][1] - 1.0
            r_assets = rec["debt"] / rec["assets"]
            ok_assets = r_assets <= GAMMA_ASSETS
            ok_mcap = None if not mcap else (rec["debt"] / mcap) <= GAMMA_MCAP
            rows.append({"cik": cik, "sym": sym or "", "period": period, "name": rec["name"],
                         "r_assets": r_assets, "r_mcap": None if not mcap else rec["debt"] / mcap,
                         "ok_assets": ok_assets, "ok_mcap": ok_mcap, "ret_1y": ret})
            if ok_mcap is not None and ok_mcap != ok_assets:
                disagree.append(rows[-1])

    if px and not any(r["ok_mcap"] is not None for r in rows):
        # Print the objects, not the count. Every tally can be right while the
        # identities fail to join, and that is the failure this guards.
        print("!! not one market cap joined, though price files exist. Key samples:")
        print("   panel cik   :", sorted(panel)[:6])
        print("   map cik     :", sorted(cik2sym)[:6])
        print("   price files :", sorted(px)[:6])
        print("   mapped syms :", sorted({cik2sym.get(c, "-") for c in list(panel)[:6]}))
        sys.exit(3)

    priced = [r for r in rows if r["ok_mcap"] is not None]
    withret = [r for r in priced if r["ret_1y"] is not None]
    BUCKETS = [(-1.01, -0.50), (-0.50, -0.30), (-0.30, -0.15),
               (-0.15, 0.0), (0.0, 0.25), (0.25, 10.0)]
    cells = {}
    for lo, hi in BUCKETS:
        grp = [r for r in withret if lo < r["ret_1y"] <= hi]
        cells[f"({lo:+.2f},{hi:+.2f}]"] = {
            "n": len(grp),
            "pushed_out_by_breathing_gate":
                sum(1 for r in grp if r["ok_mcap"] is False and r["ok_assets"] is True),
            "compliant_both":
                sum(1 for r in grp if r["ok_mcap"] is True and r["ok_assets"] is True)}

    def q(vals, ps=(0.01, 0.10, 0.50, 0.90, 0.99)):
        s = sorted(v for v in vals if v is not None)
        if not s:
            return {}
        return {f"p{int(x*100)}": s[min(len(s) - 1, int(x * len(s)))] for x in ps}

    jumps = []
    for cik, periods in panel.items():
        vs = [rec["assets"] for _, rec in sorted(periods.items())]
        for i in range(1, len(vs)):
            if vs[i - 1] > 0 and vs[i] > 0:
                jumps.append(max(vs[i], vs[i - 1]) / min(vs[i], vs[i - 1]))
    shares_all = [rec["shares"] for periods in panel.values() for rec in periods.values()]
    rq = q([r["r_mcap"] for r in rows])
    sq = q(shares_all)
    print("=== dimension check, before any verdict is read ===")
    print("  shares outstanding : " + "  ".join(f"{k}={v:,.4g}" for k, v in sq.items()))
    print("  debt / market cap  : " + "  ".join(f"{k}={v:,.4g}" for k, v in rq.items()))
    absurd = [r for r in rows if r["r_mcap"] is not None and r["r_mcap"] > 100.0]
    tiny = [rec for periods in panel.values() for rec in periods.values()
            if rec["shares"] < 10_000]
    jq = q(jumps)
    print("  consecutive assets ratio : " + "  ".join(f"{k}={v:,.4g}" for k, v in jq.items()))
    big = sum(1 for j in jumps if j > 2.0)
    print(f"  assets moving over 2x q/q: {big} of {len(jumps)}   "
          f"<- an entity-identity check, not a growth statistic")
    print(f"  debt/mcap above 100      : {len(absurd)} of {len([r for r in rows if r['r_mcap'] is not None])}")
    print(f"  share counts below 10,000: {len(tiny)} of {len(shares_all)}")
    if absurd:
        print("  the objects, not the tally, sorted by how absurd:")
        for r in sorted(absurd, key=lambda r: -r["r_mcap"])[:6]:
            rec = panel[r["cik"]][r["period"]]
            print(f"    {r['sym']:6s} {r['period']}  shares={rec['shares']:,.6g}  "
                  f"debt={rec['debt']:,.6g}  assets={rec['assets']:,.6g}  {r['name'][:28]}")

    print("\n=== funnel ===")
    for k in ("filings", "has_assets", "has_debt", "has_shares"):
        print(f"  {k:16s} {funnel[k]}")
    print(f"  {'firms':16s} {len(panel)}")
    print(f"  {'firm-periods':16s} {len(rows)}")
    print(f"  {'with market cap':16s} {len(priced)}")
    print(f"  {'with 1y return':16s} {len(withret)}   <- denominator of the cells")
    print(f"\n=== the two rulebooks disagree on {len(disagree)} firm-periods ===")
    # Show across the distribution, not the top of it. Sorting by the quantity and
    # printing the head guarantees the sample is the extreme, which hides whether the
    # extreme is the rule or the exception.
    ds = sorted(disagree, key=lambda r: r["r_mcap"] or 0)
    picks = ([ds[int(f * (len(ds) - 1))]
              for f in (0.02, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 0.98)] if ds else [])
    for r in picks:
        rr = "n/a" if r["ret_1y"] is None else f"{r['ret_1y']:+.4f}"
        print(f"    {r['sym']:6s} {r['period']:10s} r_assets={r['r_assets']:.4f} "
              f"r_mcap={r['r_mcap']:.4f} 1y={rr}  {r['name'][:34]}")
    print("\n=== cells: decline bucket by whether the breathing gate pushed the firm out ===")
    for k, v in cells.items():
        print(f"  {k:18s} n={v['n']:6d}  pushed_out={v['pushed_out_by_breathing_gate']:5d}  "
              f"compliant_both={v['compliant_both']:5d}")
    print("\n  three smallest cells, because the worst cell decides a design, not the average:")
    for k, v in sorted(cells.items(), key=lambda kv: kv[1]["pushed_out_by_breathing_gate"])[:3]:
        print(f"    {k:18s} pushed_out={v['pushed_out_by_breathing_gate']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"stage": "B19", "diagnostic_only": True,
         "diagnostic_reason": "gate-zero counting only; the stage is not open and no "
                              "number here is a licensed reading of anything",
         "gamma_mcap": GAMMA_MCAP, "gamma_assets": round(GAMMA_ASSETS, 6),
         "debt_groups": DEBT_GROUPS, "debt_fallback": DEBT_FALLBACK, "shares_tags": SHARES_TAGS,
         "quarters": [z.stem for z in zips], "funnel": dict(funnel),
         "n_firms": len(panel), "n_firm_periods": len(rows), "n_priced": len(priced),
         "n_with_return": len(withret), "n_disagree": len(disagree), "cells": cells},
        indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"\n-> {OUT}")


def cmd_inspect(args) -> None:
    """Every intermediate for one symbol, with the raw tag values behind them."""
    sym = args.inspect.upper()
    zips = sorted(RAW.glob("*.zip"))
    cik2sym = _ticker_map()
    want_cik = [c for c, s in cik2sym.items() if s == sym]
    if not want_cik:
        print(f"{sym} is not in company_tickers.json")
        return
    cik = want_cik[0]
    print(f"{sym}  cik={cik}")
    tags = set(DEBT_TAGS) | set(SHARES_TAGS) | {ASSET_TAG}
    for zp in zips:
        subs, vals = load_quarter(zp, tags)
        for adsh, s in subs.items():
            if s["cik"] != cik:
                continue
            print(f"  --- {zp.stem}  adsh={adsh}  period={s['period']}")
            for (a2, tg), (v, d) in sorted(vals.items()):
                if a2 == adsh:
                    print(f"      {tg:48s} {v:>22,.6g}   ddate={d}")
    px = load_prices().get(sym)
    if px:
        print(f"  price series: {len(px)} bars, "
              f"first={px[0]}, last={px[-1]}, "
              f"min={min(c for _, c in px):.6g}, max={max(c for _, c in px):.6g}")
    else:
        print("  no price series on disk")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", action="store_true")
    g.add_argument("--emit-tickers", action="store_true")
    g.add_argument("--gate0", action="store_true")
    g.add_argument("--inspect", metavar="SYM", help="print every intermediate for one symbol")
    ap.add_argument("--quarters", type=int, default=2, help="--probe only: how many to scan")
    a = ap.parse_args()
    if a.probe:
        cmd_probe(a)
    elif a.emit_tickers:
        cmd_emit_tickers(a)
    elif a.inspect:
        cmd_inspect(a)
    else:
        cmd_gate0(a)


if __name__ == "__main__":
    main()
