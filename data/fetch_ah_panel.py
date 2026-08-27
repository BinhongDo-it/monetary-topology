"""B21 daily panel: two prices per pair and two exchange rates, resumable.

One file per ticker under ``data/raw/b21/px/``. **Nothing is ever deleted.** A
file that is short, unparseable or out of order is renamed with a ``.partial``
suffix and refetched on the next run, so a truncated download can never be read
as though it were whole.

Two decisions taken here rather than left open, both reversible by editing the
two constants they live in.

**All 203 pairs are pulled, not the 149 in the premium index.** The 54 outside it
are the ones the Connect channel does not reach, and the ease of moving a
position between the two classes is the parameter this stage turns on. Dropping
them would remove the only variation in it. They are pulled and labelled later,
once the eligibility list is in hand; the grouping is not decided before the list
is read.

**Unadjusted closes on both legs.** An adjusted series folds dividends back into
the price, and the two legs of an A+H pair pay on different dates and are taxed
differently, so adjusting one leg on a schedule the other does not share invents
a premium move on the ex-date. Raw closes leave that wedge visible instead of
smoothing it into the series. **Splits are the opposite case and are handled**:
they are simultaneous by charter, so an unhandled split shows up as a step of
several hundred per cent in one leg. The integrity check below looks for exactly
that and refuses the file.

Usage::

    python data/fetch_ah_panel.py                 # six-ticker probe, then stops
    python data/fetch_ah_panel.py --all           # the whole list, resumable
    python data/fetch_ah_panel.py --all --report  # no fetching, audit what is on disk

The probe runs first on purpose. It covers Shanghai, Shenzhen, Hong Kong and both
exchange rates, prints what came back, and stops. **Look at those six before
spending an hour on four hundred.**
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "b21"
PAGE = CACHE / "aastocks_ah.html"
PX = CACHE / "px"
NODATA = CACHE / "tickers_without_data.txt"
TRUNC = CACHE / "truncations.txt"

START = "2006-01-01"          # the premium index is backdated to 2006-01-03
MIN_ROWS = 5                  # only a file with almost nothing in it
STALE_DAYS = 21               # how far behind the newest series a file may end
MAX_STEP = 3.0                # a one-day ratio above this is a listing event, not a split
SPLIT_NEAR = 3                # days either side of a split event a step may sit

# The two exchange rates are two different objects and never share a column.
# USD legs, crossed to HKD in the panel build rather than here, so the raw series
# stay as the sources publish them.
FX = {
    "CNY=X": "onshore USD/CNY, the rate the mainland class faces",
    "CNH=X": "offshore USD/CNH, the rate the Hong Kong class faces",
    "HKD=X": "USD/HKD, the leg both classes share",
}

# The offshore rate is load-bearing: it is the leg that differs between the two
# classes, and the whole measurement is the difference between the classes. If
# CNH=X returns nothing, one of these is tried in order rather than the offshore
# leg being quietly replaced by the onshore one. **They must never share a
# column and one must never stand in for the other.**
CNH_ALTERNATES = ["CNH=X", "USDCNH=X", "CNH=F", "CNHUSD=X", "USDCNH"]


def to_yahoo(code: str) -> str:
    """The page's suffixes are not the ones a price source uses.

    Shanghai is written ``.SH`` on the page and ``.SS`` by the source. A mapping
    that keeps the page's own suffix silently drops every Shanghai name, and
    Shanghai is the larger half. Hong Kong codes are five digits on the page and
    four at the source.
    """
    if code.endswith(".SH"):
        return code[:-3] + ".SS"
    if code.endswith(".SZ"):
        return code
    if code.endswith(".HK"):
        num = code[:-3]
        return (num[1:] if len(num) == 5 and num.startswith("0") else num) + ".HK"
    return code


def px_path(ticker: str) -> Path:
    """The one place a ticker becomes a filename.

    **There were two spellings and they disagreed.** The main fetch wrote
    `CNY=X.csv` and the rate probe wrote `CNH_F.csv`, so a reader that assumed
    either one found half the files and reported the other half missing. The `=`
    is legal on both platforms, so nothing failed loudly; it just went looking in
    the wrong place.

    Going forward `=` becomes `_`. An existing file under the old spelling is
    still found and is **not renamed**, because it is data.
    """
    safe = PX / f"{ticker.replace('=', '_')}.csv"
    if safe.exists():
        return safe
    legacy = PX / f"{ticker}.csv"
    return legacy if legacy.exists() else safe


def read_pairs() -> list[dict]:
    if not PAGE.exists():
        print(f"no pair list at {PAGE}")
        print("run  python experiments/b21_probe.py  first")
        sys.exit(2)
    html = PAGE.read_text(encoding="utf-8")
    row = re.compile(
        r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?(\d{5})\.HK.*?"
        r"([0-9]+\.[0-9]+).*?(\d{6})\.(SH|SZ).*?([0-9]+\.[0-9]+)", re.S)
    seen, out = set(), []
    for m in row.finditer(html):
        name, h, _, a, mkt, _ = m.groups()
        if h in seen:
            continue
        seen.add(h)
        out.append({"name": name.strip()[:24], "h": f"{h}.HK", "a": f"{a}.{mkt}"})
    return sorted(out, key=lambda r: r["h"])


def quarantine(path: Path, reason: str) -> None:
    n = 0
    while True:
        dest = path.with_suffix(f"{path.suffix}.partial{'' if n == 0 else n}")
        if not dest.exists():
            break
        n += 1
    path.rename(dest)
    print(f"    !! {reason}; renamed to {dest.name}, not deleted")


def newest_end() -> str:
    """The latest last-date across every cached file. The yardstick for staleness."""
    best = ""
    for f in PX.glob("*.csv"):
        try:
            rows = list(csv.DictReader(f.open(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        if rows and rows[-1].get("Date", "") > best:
            best = rows[-1]["Date"]
    return best


def check(path: Path, latest: str = "") -> tuple[bool, str]:
    """Refuse a file that stops early, is out of order, or carries a price step.

    **Row count is not a refusal and must not be.** A short series here is a
    recent listing, not a truncated download, and the recent listings are the
    population the tick-size dates fall inside. An earlier version refused
    anything under 200 rows and threw out 42 of 203 Hong Kong legs, every one of
    them current to the day it was fetched. That is a fixed absolute threshold
    laid across a heterogeneous distribution -- the ninth category error -- and
    it is the second time this project has bought it, after the byte floor in
    B19 that dropped the shortest series for the same reason.

    **The signal for truncation is that the series stops early**, which is read
    against where the other series stop rather than against a constant.
    """
    try:
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return False, f"unreadable ({type(e).__name__})"
    if len(rows) < MIN_ROWS:
        return False, f"{len(rows)} rows, effectively empty"
    if "Close" not in rows[0] or "Date" not in rows[0]:
        return False, f"columns are {list(rows[0])[:5]}"
    if "Stock Splits" not in rows[0]:
        # Written before the split column was kept. Not corrupt, but unusable:
        # nothing in it distinguishes a split from a price move, and the scan
        # found candidate splits sitting under the step threshold.
        return False, "saved without the Stock Splits column, refetch"
    dates, prev, step = [], None, None
    for r in rows:
        dates.append(r["Date"])
        try:
            c = float(r["Close"])
        except (TypeError, ValueError):
            continue
        if c <= 0:
            return False, "a close at or below zero"
        if prev and (c / prev > MAX_STEP or prev / c > MAX_STEP):
            step = f"{prev:g} to {c:g} on {r['Date']}"
        prev = c
    if dates != sorted(dates):
        return False, "dates are not in order"
    if latest and dates[-1] < latest:
        gap = (dt.date.fromisoformat(latest) - dt.date.fromisoformat(dates[-1])).days
        if gap > STALE_DAYS:
            return False, (f"ends {dates[-1]}, {gap} days before the newest series "
                           f"({latest}); this one stopped early")
    if step:
        return False, f"a one-day step of more than {MAX_STEP}x ({step}), likely an unhandled split"
    tag = "  SHORT, a recent listing" if len(rows) < 250 else ""
    return True, f"{len(rows)} rows, {dates[0]} to {dates[-1]}{tag}"


def fetch_one(ticker: str, path: Path) -> str:
    import yfinance as yf
    df = yf.Ticker(ticker).history(start=START, interval="1d", auto_adjust=False)
    if df is None or df.empty:
        return "no data"
    # Splits and dividends are kept as columns rather than folded into the price.
    # **They must be treated differently and a single adjusted column cannot do
    # both.** A split is simultaneous on the two legs by charter, so it has to be
    # applied or the ratio jumps on the split date; a dividend is not, so
    # applying it invents a premium move on each leg's own ex-date. Keeping the
    # events beside the raw close is the only shape that allows one and refuses
    # the other.
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume",
                        "Dividends", "Stock Splits") if c in df.columns]
    df = df[keep].copy()
    df.index.name = "Date"
    df.index = df.index.strftime("%Y-%m-%d")
    tmp = path.with_suffix(".csv.writing")
    df.to_csv(tmp, encoding="utf-8", lineterminator="\n", float_format="%.6f")
    tmp.replace(path)          # atomic, so an interrupted run leaves no half file
    return "ok"


def rescue() -> int:
    """Rename quarantined files back when the corrected check accepts them.

    They were refused by a threshold that was wrong, not by anything wrong with
    them. Renaming rather than refetching is the point of never deleting.
    """
    latest = newest_end()
    print(f"newest series on disk ends {latest}\n")
    back = left = 0
    for f in sorted(PX.glob("*.csv.partial*")):
        dest = PX / f.name.split(".csv.partial")[0] + ".csv" if False else \
            PX / (f.name.split(".csv.partial")[0] + ".csv")
        if dest.exists():
            print(f"  {f.name:>30}  a good copy already exists, left in place")
            left += 1
            continue
        ok, why = check(f, latest)
        if ok:
            f.rename(dest)
            print(f"  {dest.name:>30}  recovered: {why}")
            back += 1
        else:
            print(f"  {f.name:>30}  still refused: {why}")
            left += 1
    print(f"\n  recovered {back}, still quarantined {left}. Nothing was deleted.")
    return 0


def repair() -> int:
    """Cut a quarantined series at its last price step and keep what follows.

    **Every one of the five files this was written for is the same thing**: the
    series carries rows from before the security existed in its present form. A
    Hong Kong code reused by a new issuer, a mainland shell that became a broker
    by reverse merger, a run of 0.01 placeholders before a listing day. The step
    is real and the check was right to refuse the file; what is wrong is throwing
    away the part after the step along with the part before it.

    **The decision is recorded, not taken silently.** The original file is left
    in quarantine untouched, the cut is written as a fresh `.csv`, and both sides
    of the cut go into ``truncations.txt`` so the call can be checked by someone
    who knows the corporate history. A step that is a genuine split, where the
    pre-step rows should have been rescaled rather than dropped, looks the same
    to this function and different to a person. **Read that file.**
    """
    lines = []
    fixed = 0
    for f in sorted(PX.glob("*.csv.partial")):
        dest = PX / (f.name.split(".csv.partial")[0] + ".csv")
        if dest.exists():
            continue
        rows = list(csv.DictReader(f.open(encoding="utf-8")))
        cut = None
        prev = None
        for i, r in enumerate(rows):
            try:
                c = float(r["Close"])
            except (TypeError, ValueError):
                continue
            if c > 0 and prev and (c / prev > MAX_STEP or prev / c > MAX_STEP):
                cut = (i, r["Date"], prev, c)
            if c > 0:
                prev = c
        if cut is None:
            continue
        i, date, before, after = cut
        kept = rows[i:]
        if len(kept) < MIN_ROWS:
            print(f"  {f.name:>30}  step at {date} leaves only {len(kept)} rows, left alone")
            continue
        with dest.open("w", encoding="utf-8", newline="\n") as out:
            w = csv.DictWriter(out, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(kept)
        lines.append(f"{dest.stem}\tcut at {date}\t{before:g} -> {after:g}"
                     f"\tratio {max(after / before, before / after):.1f}"
                     f"\tdropped {i}\tkept {len(kept)}\tnow starts {kept[0]['Date']}")
        print(f"  {dest.name:>30}  cut at {date}: {before:g} -> {after:g}, "
              f"dropped {i}, kept {len(kept)}")
        fixed += 1
    if lines:
        head = "" if TRUNC.exists() else (
            "# Series cut at a price step. The rows before the step are not this\n"
            "# security. Each line: ticker, date, prices either side, ratio, rows\n"
            "# dropped and kept. The uncut original is still in quarantine.\n")
        with TRUNC.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(head + "\n".join(lines) + "\n")
        print(f"\n  {fixed} cut. **Recorded in {TRUNC.name}. Read it before using them.**")
    else:
        print("  nothing to cut")
    return 0


def fx_probe() -> int:
    """Try every candidate for the offshore rate and print what each returns.

    **No substitution happens here and none may happen anywhere.** The offshore
    rate is the leg on which the two classes differ, so filling it with the
    onshore rate would erase the quantity being measured. If none of these works
    the answer is that this source cannot supply the leg, not that the leg can be
    approximated.
    """
    PX.mkdir(parents=True, exist_ok=True)
    print(f"{'candidate':>14} {'rows':>7}  {'range':>26}")
    live = []
    for tk in CNH_ALTERNATES:
        path = px_path(tk)
        try:
            res = fetch_one(tk, path)
        except Exception as e:                        # noqa: BLE001
            print(f"{tk:>14} {'-':>7}  {type(e).__name__}: {str(e)[:40]}")
            continue
        if res == "no data":
            print(f"{tk:>14} {'-':>7}  no data")
            continue
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        rng = f"{rows[0]['Date']} to {rows[-1]['Date']}" if rows else ""
        print(f"{tk:>14} {len(rows):>7}  {rng:>26}")
        if len(rows) >= MIN_ROWS:
            live.append((tk, len(rows), rng))
    print()
    if live:
        print("  usable candidates, longest first:")
        for tk, n, rng in sorted(live, key=lambda x: -x[1]):
            print(f"    {tk:>14} {n:>7} rows  {rng}")
        print("\n  **Pick one and name it in SOURCES.md.** Do not let the onshore\n"
              "  rate stand in for it: the difference between the two rates is the\n"
              "  difference between the two classes, and that difference is the\n"
              "  measurement.")
    else:
        print("  **None of them returns a series.** This source cannot supply the\n"
              "  offshore leg. The index half cannot be computed without it, so the\n"
              "  next step is a different rate source, not an approximation.")
    return 0


def adjust_check(ticker: str = "0168.HK") -> int:
    """Find out what adjustment the Close column already carries. Two minutes.

    **This is checked because the panel columns cannot answer it.** The saved
    files keep Open, High, Low, Close and Volume and drop Adj Close, so nothing
    on disk distinguishes a raw close from a split-adjusted one. The scan gives
    the reason to ask: 404 series over twenty years produced exactly five price
    steps above 3x, and all five were listing events. Mainland A shares issue
    bonus shares constantly, so twenty years with no split step at all means the
    source is back-adjusting splits before it hands them over.

    **That is fine and it is not the risk.** Both legs come from the same source
    by the same method, so a split adjustment applied to both cancels in the
    ratio. **The risk is dividends**, because the two legs of an A+H pair pay on
    different dates, and a dividend adjustment applied on each leg's own schedule
    invents a premium move on each ex-date that no one traded.

    Prints every column the source returns, plus its dividend and split events,
    so the question is settled by looking rather than by assuming.
    """
    import yfinance as yf
    t = yf.Ticker(ticker)
    for label, kwargs in (("auto_adjust=False", {"auto_adjust": False}),
                          ("auto_adjust=True", {"auto_adjust": True})):
        df = t.history(start="2015-01-01", end="2016-01-01", interval="1d", **kwargs)
        print(f"\n  {ticker}  {label}")
        print(f"    columns: {list(df.columns)}")
        if df.empty:
            print("    empty")
            continue
        print(f"    first row: " + ", ".join(f"{c}={df.iloc[0][c]:.4f}"
              for c in df.columns if df[c].dtype.kind == "f"))
    acts = t.actions
    if acts is not None and not acts.empty:
        acts = acts[(acts.index >= "2015-01-01") & (acts.index < "2016-01-01")]
        print(f"\n  dividends and splits in that window: {len(acts)}")
        print(acts.to_string() if len(acts) else "    none")
    print()
    print("  **Read the two blocks against each other.** If Close is the same "
          "under both\n  settings then the column already carries the full "
          "adjustment and the dividend\n  wedge between the two legs has been "
          "smoothed away before it reached disk.\n  If it differs, Close is the "
          "rawer of the two and the wedge is still visible.")
    return 0


def split_report() -> int:
    """Every split event on disk, with the price step beside it. No threshold.

    **The first version of this compared the observed step against the split
    factor and called the difference a match or a mismatch. That criterion was
    broken and its output was an artefact of its own shape.** With the price
    already adjusted, the observed step is 1.0 at every event; the old test
    then read `|1/factor - 1| < 0.25`, which passes at 1.1, 1.2 and 1.3 and
    fails at 1.5, 2.0 and 3.0. One fact, sorted into two answers by the size of
    the split. It reported 122 matches and 251 mismatches where there was one
    population.

    So no threshold. The observed step is printed and grouped by split factor,
    and the reader sees at once whether it tracks the factor or sits at one.
    """
    hits = []
    for f in sorted(PX.glob("*.csv")):
        try:
            rs = list(csv.DictReader(f.open(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        if not rs or "Stock Splits" not in rs[0]:
            continue
        prev = None
        for r in rs:
            try:
                sp = float(r.get("Stock Splits") or 0)
                c = float(r["Close"])
            except (TypeError, ValueError):
                continue
            if sp and sp != 1.0 and prev and c:
                hits.append((f.stem, r["Date"], sp, prev / c))
            if c > 0:
                prev = c
    if not hits:
        print("no file on disk carries the column yet. Run --all to refetch.")
        return 0

    print(f"{len(hits)} split events\n")
    print("observed one-day step, grouped by the split factor reported for it")
    print(f"{'factor':>9} {'events':>7} {'step min':>10} {'step med':>10} "
          f"{'step max':>10} {'tracks factor?':>16}")
    by = {}
    for _, _, sp, st in hits:
        by.setdefault(round(sp, 3), []).append(st)
    for sp in sorted(by):
        v = sorted(by[sp])
        med = v[len(v) // 2]
        tracks = "yes" if abs(med / sp - 1) < 0.15 else "no, sits at one"
        print(f"{sp:>9.3f} {len(v):>7} {v[0]:>10.3f} {med:>10.3f} {v[-1]:>10.3f} "
              f"{tracks:>16}")
    allsteps = sorted(st for _, _, _, st in hits)
    print(f"\n  every event together: min {allsteps[0]:.3f}, "
          f"median {allsteps[len(allsteps) // 2]:.3f}, max {allsteps[-1]:.3f}")
    print(f"  split factors present: {min(by):.3f} to {max(by):.3f}")
    print()
    print("  **Read the two ranges against each other.** A step that stays at one\n"
          "  while the factor runs over an order of magnitude means the column is\n"
          "  already split-adjusted and no split needs applying. A step that\n"
          "  tracks the factor means the opposite.")
    return 0


def placeholder_scan() -> int:
    """Look for the pre-listing garbage that sits under the step threshold.

    Five files were caught with a step above 3x, and two of those five began with
    a run of 0.01 placeholders. **A threshold that catches five says nothing
    about how many sit just under it.** This prints the object: the smallest
    close in each series against its own median, and the largest one-day ratio,
    so a series with a milder version of the same defect is visible rather than
    inferred.
    """
    rows = []
    for f in sorted(PX.glob("*.csv")):
        try:
            rs = list(csv.DictReader(f.open(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        px = []
        for r in rs:
            try:
                c = float(r["Close"])
            except (TypeError, ValueError, KeyError):
                continue
            if c > 0:
                px.append((r["Date"], c))
        if len(px) < 20:
            continue
        vals = sorted(c for _, c in px)
        med = vals[len(vals) // 2]
        step = max((max(px[i][1] / px[i - 1][1], px[i - 1][1] / px[i][1]), px[i][0])
                   for i in range(1, len(px)))
        rows.append((f.stem, px[0][0], vals[0], med, vals[0] / med, step[0], step[1]))

    print(f"scanned {len(rows)} series\n")
    print("lowest close against own median, smallest ratio first")
    print(f"{'ticker':>14} {'starts':>12} {'min':>10} {'median':>10} {'min/med':>9} {'first date':>12}")
    for r in sorted(rows, key=lambda r: r[4])[:15]:
        print(f"{r[0]:>14} {r[1]:>12} {r[2]:>10.4f} {r[3]:>10.3f} {r[4]:>9.4f} {r[1]:>12}")
    for cut in (0.01, 0.05, 0.10):
        n = sum(1 for r in rows if r[4] < cut)
        print(f"       min under {cut:>5.0%} of median: {n:>3} of {len(rows)}")
    print()
    print("largest surviving one-day ratio, biggest first (the threshold is "
          f"{MAX_STEP}x)")
    print(f"{'ticker':>14} {'ratio':>9} {'on':>12}")
    for r in sorted(rows, key=lambda r: -r[5])[:15]:
        print(f"{r[0]:>14} {r[5]:>9.2f} {r[6]:>12}")
    return 0


def run(tickers: list[tuple[str, str]], report_only: bool) -> int:
    PX.mkdir(parents=True, exist_ok=True)
    latest = newest_end()
    nodata = set(NODATA.read_text(encoding="utf-8").split()) if NODATA.exists() else set()
    ok = bad = got = skipped = 0
    missing: list[tuple[str, str]] = []
    for label, tk in tickers:
        path = px_path(to_yahoo(tk))
        if tk in nodata:
            skipped += 1
            continue
        if report_only and not path.exists():
            missing.append((label, tk))
            continue
        if path.exists():
            good, why = check(path, latest)
            if good:
                ok += 1
                continue
            quarantine(path, why)
            bad += 1
        if report_only:
            continue
        print(f"  {label:>24} {tk:>12} -> {to_yahoo(tk):>12}  ", end="", flush=True)
        try:
            res = fetch_one(to_yahoo(tk), path)
        except Exception as e:                       # noqa: BLE001
            print(f"error: {type(e).__name__}: {str(e)[:60]}")
            continue
        if res == "no data":
            # A delisted or renamed ticker is not a source failure. Recording it
            # separately keeps a run of them from looking like the source is down.
            nodata.add(tk)
            NODATA.write_text("\n".join(sorted(nodata)) + "\n", encoding="utf-8")
            print("no data, recorded and skipped from now on")
            continue
        good, why = check(path, latest)
        print(why if good else f"REFUSED: {why}")
        if good:
            got += 1
        else:
            quarantine(path, why)
            bad += 1
    print(f"\n  already good {ok}   fetched {got}   refused {bad}   "
          f"known no-data {skipped}   of {len(tickers)}")
    if missing:
        # A summary that reports only totals hides which rows are absent, and
        # which rows they are is the whole question: a pair with one leg on disk
        # cannot form a square at all.
        print(f"\n  **{len(missing)} tickers have no file at all.** Named, not counted:")
        for label, tk in missing:
            print(f"    {label:>26} {tk:>12} -> {to_yahoo(tk):>12}")
    return 0


def audit_pairs(pairs: list[dict]) -> None:
    """Both legs or neither. A pair missing one leg is not a thin pair, it is no pair."""
    latest = newest_end()

    def state(tk: str) -> str:
        path = px_path(to_yahoo(tk))
        if not path.exists():
            stem = to_yahoo(tk).replace("=", "_")
            q = list(PX.glob(f"{stem}.csv.partial*")) + list(PX.glob(f"{to_yahoo(tk)}.csv.partial*"))
            return "quarantined" if q else "absent"
        return "ok" if check(path, latest)[0] else "refused"

    whole, half, none = [], [], []
    for r in pairs:
        sh, sa = state(r["h"]), state(r["a"])
        (whole if sh == sa == "ok" else none if "ok" not in (sh, sa) else half).append(
            (r, sh, sa))
    print()
    print("=" * 78)
    print("B21-3  pairs, not tickers: a square needs both legs")
    print("=" * 78)
    print(f"       both legs usable : {len(whole):>4} of {len(pairs)}")
    print(f"       one leg only     : {len(half):>4}")
    print(f"       neither leg      : {len(none):>4}")
    for title, group in (("one leg only", half), ("neither leg", none)):
        if not group:
            continue
        print(f"\n       {title}, named:")
        print(f"{'name':>26} {'H':>10} {'state':>8} {'A':>12} {'state':>8}")
        for r, sh, sa in group:
            print(f"{r['name']:>26} {r['h']:>10} {sh:>8} {r['a']:>12} {sa:>8}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="every ticker, not the six-ticker probe")
    ap.add_argument("--report", action="store_true", help="check what is on disk, fetch nothing")
    ap.add_argument("--rescue", action="store_true",
                    help="rename quarantined files back if the corrected check accepts them")
    ap.add_argument("--repair", action="store_true",
                    help="cut a quarantined series at its last price step, recording the cut")
    ap.add_argument("--fx", action="store_true",
                    help="try every candidate for the offshore rate and report what each returns")
    ap.add_argument("--scan", action="store_true",
                    help="look for pre-listing placeholders that sit under the step threshold")
    ap.add_argument("--adjcheck", action="store_true",
                    help="print what adjustment the Close column already carries")
    ap.add_argument("--splits", action="store_true",
                    help="list every split event on disk and whether the price step matches it")
    args = ap.parse_args()

    if args.rescue:
        return rescue()
    if args.repair:
        return repair()
    if args.fx:
        return fx_probe()
    if args.scan:
        return placeholder_scan()
    if args.adjcheck:
        return adjust_check()
    if args.splits:
        return split_report()
    pairs = read_pairs()
    print(f"{len(pairs)} pairs on the cached page\n")
    if args.all:
        tickers = [(r["name"], r["h"]) for r in pairs] + \
                  [(r["name"], r["a"]) for r in pairs] + \
                  [(v, k) for k, v in FX.items()]
    else:
        sh = next(r for r in pairs if r["a"].endswith(".SH"))
        sz = next(r for r in pairs if r["a"].endswith(".SZ"))
        tickers = [(sh["name"], sh["h"]), (sh["name"], sh["a"]),
                   (sz["name"], sz["h"]), (sz["name"], sz["a"])] + \
                  [(v, k) for k, v in FX.items()]
        print("probe only: Shanghai, Shenzhen, Hong Kong and all three rates.")
        print("Look at these before running --all.\n")
    rc = run(tickers, args.report)
    if args.report:
        audit_pairs(pairs)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
