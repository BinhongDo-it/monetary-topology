"""B59 arm: the fed funds price two classes of eligible institution pay, against
the one administered rate they both read.

**What this is for.** `B59-2` records that on one position, a balance at a Federal
Reserve Bank, an eligible institution carries `IORB` and a Federal Home Loan Bank
carries zero, and that is a `D2`: the two classes read no common scalar, so a
single-index object has nowhere to put the question.  Inside the eligible class
there is a second line, and it passes a test the first one fails: **every eligible
institution reads the same `IORB`**, and the Board's own review prints that large
domestic banks pay 13 to 17 basis points less than smaller domestic banks and
foreign banks for the same overnight borrowing.  A common scalar and terms that
differ is the shape `B33`'s filing-status arm scored as a `B`.  Making it a reading
of ours rather than a citation of theirs is what this driver is for.

**The instrument problem, and it is in the source not in the code.**  The balance
sheet separates the two liabilities (`RCON B993` federal funds purchased in
domestic offices, `RCFD`/`RCON B995` securities sold under agreements to
repurchase) while the income statement combines their cost into one line (`RIAD
4180`, which the archive itself labels EXPENSE OF FED FUNDS PUR & SEC SOLD).  So
a rate formed as `4180 / (B993 + B995)` is in general a blend of two prices.

**What the first real archive said about that, 2026Q2.**  Most of the panel is
not a blend.  Of 770 filers borrowing at all with an expense to match, 165 carry
fed funds and no repo and 530 carry repo and no fed funds; only 75 are a genuine
mixture.  At weight exactly zero the expense line is the fed funds bill and
nothing else, so for those 165 the price is read directly and no separation is
needed or assumed.  `--probe` reports those three populations.

**Four things this driver had wrong, all found by that same archive.**  It wanted
`B987` and `B989`, which the archive's own description row calls FEDERAL FNDS
SOLD and SECURS PURCHSD UDR AGRMNTS TO RESELL: the asset legs, what the bank
lent, against an expense on what it borrowed.  It took the first prefix that
matched, so it read `RCON` only and lost the eighty filers who report
consolidated.  It searched for a column instead of naming a schedule, so total
assets for those eighty came off the regulatory-capital schedule, which carries
the same code under the same words for a different object.  And it would have
divided a year-to-date expense by a quarter-end balance.  **Every one of those
produced a full coverage table**: 4,297 of 4,297, nothing missing, nothing to
see.  Asking whether a check could fail would not have found any of them, which
is why the selftest now plants each one.

**The denominator, and where the quarter's average is filed.**  `4180` accrues
over the quarter, while `B993` and `B995` are balances on its last day, so a
ratio of the one to the other is a price only where the balance held still.
Schedule RC-K files the quarter's average of the two liabilities together,
`RCFD`/`RCON 3353`, which the archive's own description row calls QTLY AVG OF
FED FUNDS PCHD&SEC RP: the balance the expense accrued on.  It is read from
RC-K and from nowhere else.  Its asset-leg twin `3365` sits beside it and is
read as the asset leg's average, never as this one.
The one-year product used for 2009 carries no RC-K, so 2009 has no average.

**The asset leg, read as its own leg.**  The codes this driver first wanted by
mistake as the liabilities are wanted again as what they are: `4020`, which the
archive calls INCOME&FEES-FED FUNDS SOLD & SEC PUR, over `3365`, their
quarterly average on RC-K, read where reverse repo `B989` is absent at both
quarter ends.  `LEGS` names which flow goes over which average, and the two
legs share no code, so no reader of the cache can divide one leg's flow by the
other leg's balance.  The fed funds sold balance `B987` stays out: the price
does not need it, and the archive's own description of it changes in 2018Q1,
and in 2012Q4 alone.

**The class an assessment rule names.**  Schedule RC-O carries `K656`, which
the archive calls BANKER'S BANK CERTIFICATION and files as the word true or
false, beside `K657` BNKRS BNK DEDUCTIONS and `K658` BNKR BNK DEDUCTION LIMIT,
from 2011Q2.  12 CFR 327.5(b) lets a banker's bank exclude from its assessment
base the reserve balances it passes through to the Federal Reserve, those it
holds there for its own account and its fed funds sold, up to its deposits of
depository institutions plus its fed funds purchased, and has it certify each
quarter on this report.  The flag reads as one or zero in either case, and a
token that is neither is counted as unreadable rather than dropped.

**Where the data comes from, and what this driver will not do.**  The public bulk
product on the FFIEC's Central Data Repository gives whole reporting periods as
tab-delimited archives, one download per period.  The per-institution web service
is the other route and it is a thousand times more expensive: it is rate limited
at about 2500 calls an hour, and one quarter is about 4,560 institutions, so a
single quarter costs near two hours and a twenty-year history costs days.  **This
driver therefore reads archives already placed on disk and fetches nothing.**  It
does not register an account, does not handle a credential and does not prompt for
one.  Put the archives under `data/raw/CallReport/` and run `--scan`.

Disciplines this driver is built to: downloaded data is irreplaceable, so nothing
here deletes or overwrites an archive and a truncated one is reported rather than
read (discipline 6); the cache is rebuildable and is not the archive; the cost is
multiplied out before anything is pulled rather than guessed (`D38`); a column
that exists but carries no values is a name and not a record (`D37`); and what
gets printed is the object rather than a count of it (discipline 11).
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "CallReport"
CACHE = ROOT / "data" / "cache" / "b59_call_report.json"
RESULTS = ROOT / "results"

#: The items the arm needs, each naming the schedule file it has to be read
#: from and the prefix order to try.  Both halves are load bearing and the first
#: version of this driver got both wrong; the 2026Q2 archive is where that was
#: found, on the first real run of `--scan`.
#:
#: The prefix order is a form split, not a preference.  A filer with foreign
#: offices files the FFIEC 031 and reports consolidated (`RCFD`); a domestic-only
#: filer files the 041 or 051 and reports `RCON`.  At 2026Q2 that partitions the
#: panel exactly: 80 filers carry `RCFD2170` and 4,217 carry `RCON2170`, none
#: carry both and none carry neither.  Taking only `RCON` therefore loses the
#: eighty largest filers, which are the ones this arm is about.
WANT = {
    "B993": {"schedule": "RC",
             "prefixes": ("RCON",),
             "label": "federal funds purchased in domestic offices (RC 14.a)",
             "archive_says": "FEDERAL FNDS PURCD IN DOMESTIC OFFCS"},
    "B995": {"schedule": "RC",
             "prefixes": ("RCFD", "RCON"),
             "label": "securities sold under agreements to repurchase (RC 14.b)",
             "archive_says": "SECURS SOLD UNDR AGRMNTS TO REPURCH"},
    "4180": {"schedule": "RI",
             "prefixes": ("RIAD",),
             "label": "expense of federal funds purchased and securities sold "
                      "under agreements to repurchase (RI, one line for both)",
             "archive_says": "EXPENSE OF FED FUNDS PUR & SEC SOLD"},
    "2170": {"schedule": "RC",
             "prefixes": ("RCFD", "RCON"),
             "label": "total assets, which carries the size label",
             "archive_says": "TOTAL ASSETS"},
    #: The quarter's average balance of the two liabilities `4180` is the
    #: expense on.  Added after the quarter-end balances were found to misstate
    #: the balance a bank borrowed on whenever it started or stopped borrowing
    #: inside the quarter.  The same form split as `2170`: at 2026Q2, 80 filers
    #: carry `RCFD3353` and 4,217 carry `RCON3353`, none both and none neither.
    "3353": {"schedule": "RCK",
             "prefixes": ("RCFD", "RCON"),
             "label": "quarterly average of federal funds purchased and "
                      "securities sold under agreements to repurchase (RC-K)",
             "archive_says": "QTLY AVG OF FED FUNDS PCHD&SEC RP"},
    #: Balances due from Federal Reserve Banks, quarter end.  The Board's own
    #: size classes rank banks by reserve balances, not by assets, and this is
    #: the line that ranks them.  RC-A is filed by the larger filers only (at
    #: 2016Q2, 74 carry RCFD0090 and 2,362 RCON0090), which is enough for a
    #: ranking whose top is the largest banks.  The archive's description is
    #: truncated in its own row and is matched as it stands.
    "0090": {"schedule": "RCA",
             "prefixes": ("RCFD", "RCON"),
             "label": "balances due from Federal Reserve Banks (RC-A)",
             "archive_says": "BALANCES WITH F. R. BKS (COML BK BOO"},
    #: The asset leg, read as its own leg (`LEGS`).  Reverse repo is the repo
    #: half of the asset leg's average and is read only to keep repo out of a
    #: fed funds price, as `B995` is on the other side.
    "B989": {"schedule": "RC",
             "prefixes": ("RCFD", "RCON"),
             "label": "securities purchased under agreements to resell (RC 3.b)",
             "archive_says": "SECURS PURCHSD UDR AGRMNTS TO RESELL"},
    "4020": {"schedule": "RI",
             "prefixes": ("RIAD",),
             "label": "income on federal funds sold and securities purchased "
                      "under agreements to resell (RI, one line for both)",
             "archive_says": "INCOME&FEES-FED FUNDS SOLD & SEC PUR"},
    "3365": {"schedule": "RCK",
             "prefixes": ("RCFD", "RCON"),
             "label": "quarterly average of federal funds sold and securities "
                      "purchased under agreements to resell (RC-K)",
             "archive_says": "QTLY AVG OF FED FUNDS SOLD&SEC RS"},
    #: The class 12 CFR 327.5(b) names, certified each quarter from 2011Q2.
    "K656": {"schedule": "RCO",
             "prefixes": ("RCFD", "RCON"),
             "label": "banker's bank certification (RC-O), a flag",
             "archive_says": "BANKER'S BANK CERTIFICATION",
             "kind": "flag"},
    "K657": {"schedule": "RCO",
             "prefixes": ("RCFD", "RCON"),
             "label": "banker's bank deductions from the assessment base (RC-O)",
             "archive_says": "BNKRS BNK DEDUCTIONS"},
    "K658": {"schedule": "RCO",
             "prefixes": ("RCFD", "RCON"),
             "label": "banker's bank deduction limit (RC-O)",
             "archive_says": "BNKR BNK DEDUCTION LIMIT"},
}

#: Named here so it is not reached for again.  This driver was first written
#: with `B987` and `B989` in `WANT`, described in its own docstring as the
#: liabilities.  The archive's own description row said otherwise, and the
#: archive was right: both are the asset leg, what the bank lent out, while
#: `4180` is what it paid on what it borrowed.  A ratio of the one to the other
#: is not a price of anything, and nothing downstream could have caught it:
#: every count came out full and every criterion would have passed.  The asset
#: leg is wanted now under `LEGS`, as the asset leg, and `B987` alone stays out.
REJECTED = {
    "B987": "FEDERAL FNDS SOLD, the asset leg's balance. The lending price reads "
            "the RC-K average 3365 and needs only reverse repo, B989, to keep "
            "repo out; the archive's own description of this column changes in "
            "2018Q1, and in 2012Q4 alone.",
}

#: The two legs of one line of business.  Each is a year-to-date flow over its
#: own quarterly average, read only where the repo half of that average is
#: absent at both quarter ends.  The legs share no code, so no reader of the
#: cache can form a price out of one leg's flow and the other leg's balance,
#: which is the mistake `REJECTED` records.
LEGS = {
    "borrowed": {"flow": "4180", "average": "3353", "repo": "B995"},
    "lent": {"flow": "4020", "average": "3365", "repo": "B989"},
}

#: `4180` is a calendar-year-to-date flow, which is how the income statement is
#: filed: a Q2 figure covers January to June, and `4020` is filed the same way.
#: A rate formed from one period's flow over that period's balance is therefore
#: a half-year cost over a quarter-end stock, and in Q1 it is a quarter over a
#: stock.  Differencing against the prior quarter is what makes them
#: commensurate, so this driver refuses to form a rate from a lone period rather
#: than quietly forming a wrong one.  `D6`: a proxy is checked at the frequency
#: it will be used at.
YTD_CODES = ("4180", "4020")

#: A flag column is filed as the word true or false, in either case.  It reads
#: as one or zero; any other token raises, is counted as unreadable and is not
#: read, so a flag never falls through to `float`.
FLAG_VALUES = {"TRUE": 1.0, "FALSE": 0.0}


def _value(spec, raw: str) -> float:
    if spec.get("kind") == "flag":
        if raw.upper() not in FLAG_VALUES:
            raise ValueError(raw)
        return FLAG_VALUES[raw.upper()]
    return float(raw)

#: Every prefix that appears on a wanted code anywhere in the archive, kept so
#: the scan can say which ones a period actually used rather than assuming.
PREFIXES = ("RCON", "RCFD", "RCFN", "RCOA", "RCFA", "RIAD")

ID_COLS = ("IDRSSD", "ID RSSD", "IDRSSD ")

#: the one-year product puts the quarter in a column instead of the file name
DATE_COLS = ("Reporting Period End Date", "Reporting Period", "RSSD9999")

#: Rate limit and panel size, both read rather than guessed: the web service
#: help page states about 2500 downloads an hour, and the FDIC financial API
#: returns 4,560 insured institutions for 2024-12-31 with 955 of them carrying a
#: non-zero combined federal-funds-and-repo balance.
PWS_CALLS_PER_HOUR = 2500
PANEL_ALL = 4560
PANEL_NONZERO = 955

#: What the bulk product actually offers, read off its own period dropdown on
#: 2026-09-16 rather than assumed: every quarter end from 2001Q1 to 2026Q2.
#: The page carries no login and the product wanted is the first in its list,
#: `Call Reports -- Single Period`, in the `Tab Delimited` format.
BULK_FIRST = "2001Q1"
BULK_LAST = "2026Q2"
BULK_PAGE = "the Central Data Repository's Public Data Distribution, Bulk Data "\
            "Download page"


def quarters(start: str, end: str):
    """Every quarter-end between two `YYYYQn` labels, inclusive."""
    def parse(s):
        m = re.fullmatch(r"(\d{4})Q([1-4])", s)
        if not m:
            raise SystemExit(f"  a quarter label reads YYYYQn, not {s!r}")
        return int(m.group(1)), int(m.group(2))
    y0, q0 = parse(start)
    y1, q1 = parse(end)
    out = []
    y, q = y0, q0
    while (y, q) <= (y1, q1):
        out.append(f"{y}Q{q}")
        q += 1
        if q == 5:
            y, q = y + 1, 1
    return out


def cost_table(qs):
    """What each route costs, multiplied out before anything is pulled."""
    n = len(qs)
    bulk = n
    pws_all = n * PANEL_ALL
    pws_screened = n * PANEL_NONZERO
    return {
        "quarters": n,
        "bulk_downloads": bulk,
        "pws_calls_whole_panel": pws_all,
        "pws_hours_whole_panel": pws_all / PWS_CALLS_PER_HOUR,
        "pws_calls_screened": pws_screened,
        "pws_hours_screened": pws_screened / PWS_CALLS_PER_HOUR,
        "screen": "a period's panel cut to the institutions carrying a non-zero "
                  "combined balance, which the FDIC financial API answers for "
                  "free; 955 of 4,560 at 2024-12-31",
    }


def archives():
    """Every archive on disk, with whether it opens and what it holds.

    An archive that will not open is reported and not read.  Discipline 6: a
    truncated download has to be visible, because silently reading a short file
    produces a panel that is wrong in a way no later criterion can see.
    """
    if not RAW.is_dir():
        return []
    out = []
    for p in sorted(RAW.iterdir()):
        if p.suffix.lower() != ".zip":
            continue
        rec = {"name": p.name, "bytes": p.stat().st_size}
        try:
            with zipfile.ZipFile(p) as z:
                bad = z.testzip()
                rec["opens"] = bad is None
                rec["first_bad_member"] = bad
                rec["members"] = sorted(i.filename for i in z.infolist())
        except Exception as e:
            rec["opens"] = False
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["members"] = []
        out.append(rec)
    return out


def _sniff(text: str):
    """Header row, description row, delimiter and data rows of one schedule file.

    The bulk files put MDRM codes on the first line and human descriptions on
    the second.  Rather than assume that, find whichever of the first two lines
    carries codes that look like MDRM and say which one it was.  The other line
    is the archive telling you what each column means, and that is not decoration:
    it is the only thing on hand that can catch one code naming two objects.
    """
    sample = text[:8192]
    #: The bulk product is offered tab delimited and the web service returns a
    #: Semicolon Delimited Format, so a driver that only weighs tab against
    #: comma reads an SDF file as one column and reports that nothing matched.
    #: Found 2026-09-16 by the layout printer on a planted archive, before any
    #: real one was opened.
    delim = max(("\t", ",", ";", "|"), key=sample.count)
    if sample.count(delim) == 0:
        delim = "\t"
    rdr = csv.reader(io.StringIO(text), delimiter=delim)
    rows = list(rdr)
    if not rows:
        return None
    def looks_mdrm(hdr):
        hits = sum(1 for h in hdr
                   if re.fullmatch(r"(%s)\s*[A-Z0-9]{4}" % "|".join(PREFIXES),
                                   h.strip()))
        return hits
    best, best_i = -1, 0
    for i in range(min(2, len(rows))):
        n = looks_mdrm(rows[i])
        if n > best:
            best, best_i = n, i
    #: the row after the codes is the descriptions when its identifier cell is
    #: not a number.  Split it off explicitly instead of relying on a later
    #: is-it-a-digit test to drop it.
    desc, at = [], best_i + 1
    if at < len(rows) and rows[at] and not rows[at][0].strip().isdigit():
        desc, at = [c.strip() for c in rows[at]], at + 1
    return {"delimiter": {"\t": "tab", ",": "comma", ";": "semicolon",
                          "|": "pipe"}[delim],
            "header_row": best_i, "mdrm_like": best,
            "header": [h.strip() for h in rows[best_i]],
            "desc": desc,
            "data": rows[at:]}


def schedule_of(member: str):
    """Which schedule a member file is, from its own name.

    `FFIEC CDR Call Schedule RCRII 06302026(2 of 4).txt` is `RCRII`, and that
    matters because `RCON2170` lives in `RC` and in `RCRII` both, under the same
    description, meaning two different objects.  Reading whichever file happened
    to sort last is how the eighty largest filers got a total-assets figure off
    the regulatory-capital schedule while the coverage table read 4,297 of 4,297.
    Pin the schedule; do not search for the column.
    """
    m = re.search(r"Call Schedule ([A-Z]+[A-Z0-9]*)\s", member)
    return m.group(1) if m else None


def period_of(member_or_archive: str):
    """`...06302026...` to `2026Q2`, so a panel row knows which quarter it is."""
    m = re.search(r"(\d{2})(\d{2})(\d{4})", member_or_archive)
    if not m:
        return None
    mm, _dd, yyyy = int(m.group(1)), m.group(2), m.group(3)
    q = {3: 1, 6: 2, 9: 3, 12: 4}.get(mm)
    return f"{yyyy}Q{q}" if q else None



def quarter_expense(this_ytd, prev_ytd, period):
    """The quarter's own expense out of two year-to-date figures.

    Q1's year-to-date figure is already one quarter, so it stands alone.  Every
    later quarter is the difference against the one before it, and without that
    prior figure there is no quarter's expense to be had.  Returning `None` is
    the point: a driver that guessed here would produce a rate roughly double
    the truth at Q2 and nothing downstream would see it.
    """
    if period and period.endswith("Q1"):
        return this_ytd
    if prev_ytd is None or this_ytd is None:
        return None
    return this_ytd - prev_ytd


def read_period(path: Path):
    """One archive to {idrssd: {code: value}}, plus what was found and missed.

    Each code is taken from the schedule file `WANT` names and from nowhere
    else, and within that file the prefixes are tried in the stated order and
    the first one carrying a value for that filer wins.  Before any value is
    read the archive's own description of the column is compared with what this
    driver expects it to be; a mismatch is reported and the column is not read,
    because a code that names a different object here than it did there is the
    one failure that leaves every count looking full.
    """
    found = {}
    sources = collections.defaultdict(collections.Counter)
    values = collections.defaultdict(dict)
    members_read, mismatches = [], []
    with zipfile.ZipFile(path) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if info.is_dir() or not info.filename.lower().endswith(".txt"):
                continue
            sched = schedule_of(info.filename)
            wanted_here = [c for c, w in WANT.items() if w["schedule"] == sched]
            if not wanted_here:
                continue
            with z.open(info) as fh:
                #: encoding pinned at both ends; a bulk file is not guaranteed
                #: to be ASCII and the platform default differs by machine.
                text = fh.read().decode("utf-8", errors="replace")
            s = _sniff(text)
            if not s or s["mdrm_like"] == 0:
                continue
            idx = {h: i for i, h in enumerate(s["header"])}
            id_at = next((idx[c] for c in ID_COLS if c in idx), None)
            if id_at is None:
                continue
            cols = {}
            for code in wanted_here:
                spec = WANT[code]
                order = []
                for pre in spec["prefixes"]:
                    key = f"{pre}{code}"
                    if key not in idx:
                        continue
                    at = idx[key]
                    says = s["desc"][at].strip() if at < len(s["desc"]) else ""
                    if says and says.upper() != spec["archive_says"].upper():
                        mismatches.append(
                            {"member": info.filename, "column": key,
                             "archive_says": says,
                             "driver_expected": spec["archive_says"]})
                        continue
                    order.append((key, at))
                if order:
                    cols[code] = order
                    found[code] = [k for k, _ in order]
            if not cols:
                continue
            members_read.append(info.filename)
            for row in s["data"]:
                if len(row) <= id_at:
                    continue
                rssd = row[id_at].strip()
                if not rssd.isdigit():
                    continue
                for code, order in cols.items():
                    for key, at in order:
                        if at >= len(row):
                            continue
                        raw = row[at].strip()
                        if not raw:
                            continue
                        try:
                            values[rssd][code] = _value(WANT[code], raw)
                        except ValueError:
                            if WANT[code].get("kind") == "flag":
                                sources[code]["(unreadable)"] += 1
                            break
                        sources[code][key] += 1
                        break
    return (dict(values), found, members_read,
            {k: dict(v) for k, v in sources.items()}, mismatches)


def coverage(values, found, sources):
    """`D37`: a column that exists is a name; a column that carries values is a
    record.  Report both, per code, and the per-prefix split as well, because
    a form split hides inside a full-looking total."""
    out = {}
    for code, spec in sorted(WANT.items()):
        present = sum(1 for v in values.values() if code in v)
        nonzero = sum(1 for v in values.values() if v.get(code))
        out[code] = {"columns": found.get(code),
                     "label": spec["label"],
                     "archive_says": spec["archive_says"],
                     "supplied_by": sources.get(code, {}),
                     "filers_with_a_value": present,
                     "filers_with_a_non_zero_value": nonzero}
    return out


def cmd_plan(a) -> int:
    qs = quarters(a.start, a.end)
    c = cost_table(qs)
    print("periods wanted, first and last, and how many:")
    print(f"  {qs[0]} to {qs[-1]}, {c['quarters']} quarters")
    outside = [q for q in (qs[0], qs[-1])
               if not (BULK_FIRST <= q <= BULK_LAST)]
    print(f"  the bulk product offers {BULK_FIRST} to {BULK_LAST}"
          + ("  <-- WANTED PERIODS FALL OUTSIDE IT: %s" % ", ".join(outside)
             if outside else "  (the window asked for is inside it)"))
    print()
    print("what each route costs, multiplied out before anything is pulled:")
    print(f"  bulk archives, one per period          {c['bulk_downloads']:>8,} downloads")
    print(f"  per-institution service, whole panel   {c['pws_calls_whole_panel']:>8,} calls"
          f"   about {c['pws_hours_whole_panel']:,.0f} hours at {PWS_CALLS_PER_HOUR:,}/hour")
    print(f"  per-institution service, screened      {c['pws_calls_screened']:>8,} calls"
          f"   about {c['pws_hours_screened']:,.0f} hours")
    print("\n  the screen is free and is not this driver's job:")
    print(f"  {c['screen']}")
    print("\nthis driver fetches nothing. Put the archives under")
    print(f"  {RAW}")
    print("and run --scan. It registers no account and handles no credential.")
    print("\nthe administered rate the two classes both read is not fetched\n  here either: that is b59_reserve_class_rate.py, which already exists.")
    print("\nthe items this arm needs. The combined expense line is the\n  whole problem, and the split balance sheet is what answers it:")
    for code, label in sorted(WANT.items()):
        print(f"  {code}  {label}")
    return 0


def layout(path: Path):
    """What a period's schedule files actually look like, for the run where
    nothing matched.  Names the file, the delimiter found, which of the first
    two rows looked like codes, and the first handful of column names."""
    out = []
    try:
        with zipfile.ZipFile(path) as z:
            for info in sorted(z.infolist(), key=lambda i: i.filename):
                if info.is_dir() or not info.filename.lower().endswith(".txt"):
                    out.append(f"{info.filename}  (not a .txt, skipped)")
                    continue
                with z.open(info) as fh:
                    head = fh.read(16384).decode("utf-8", errors="replace")
                s = _sniff(head)
                if not s:
                    out.append(f"{info.filename}  (empty)")
                    continue
                cols = ", ".join(s["header"][:8])
                out.append(f"{info.filename}  delim={s['delimiter']} "
                           f"header_row={s['header_row']} "
                           f"mdrm_like={s['mdrm_like']}  [{cols}]")
    except Exception as e:
        out.append(f"could not inspect: {type(e).__name__}: {e}")
    return out



#: The bulk page offers six products and they do not share a shape.  The
#: `Single Period` product gives one quarter per archive, one file per schedule,
#: and the quarter is in the file name.  The `Subset of Schedules` product gives
#: one **year** per archive, two files (balance sheet and income statement), and
#: the quarter is a **column**, `Reporting Period End Date`.  A reader that
#: assumes the first shape reads the second one as a single period and quietly
#: keeps whichever quarter sorted last, which is four quarters collapsed into
#: one with every count still looking full.
#:
#: Both products carry the four items this arm needs, and the subset product
#: carries them for `2009Q2`, which the single-period product serves as a zero
#: byte file (`R16`).  Cross-checked 2026-09-16 on 2009 Q1, Q3 and Q4: the two
#: products agree on the filer set exactly and on all four codes to the digit,
#: 22,234 filer-quarters, zero differences.
YEAR_RE = re.compile(r"Subset of Schedules\s+(\d{4})")


def periods_of(name: str):
    """Which quarters an archive's NAME claims, without opening it.

    A claim, not a reading.  `read_any` checks it against the date column the
    archive actually carries and reports a mismatch rather than trusting either.
    """
    m = YEAR_RE.search(name)
    if m:
        return [f"{m.group(1)}Q{q}" for q in (1, 2, 3, 4)]
    p = period_of(name)
    return [p] if p else []


def read_year_archive(path: Path):
    """A one-year archive to {period: (values, found, members, sources, mism)}.

    Same discipline as `read_period`: the column is checked against the
    archive's own description of it before a value is read (`D54`), the prefixes
    are tried in `WANT`'s order and the first one carrying a value for that
    filer wins, and the period comes from the row rather than from the name.
    """
    found, members = {}, []
    sources = collections.defaultdict(collections.Counter)
    values = collections.defaultdict(lambda: collections.defaultdict(dict))
    mism = []
    with zipfile.ZipFile(path) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if info.is_dir() or not info.filename.lower().endswith(".txt"):
                continue
            with z.open(info) as fh:
                text = fh.read().decode("utf-8", errors="replace")
            s = _sniff(text)
            if not s or s["mdrm_like"] == 0:
                continue
            idx = {h: i for i, h in enumerate(s["header"])}
            id_at = next((idx[c] for c in ID_COLS if c in idx), None)
            dt_at = next((idx[c] for c in DATE_COLS if c in idx), None)
            if id_at is None or dt_at is None:
                continue
            cols = {}
            for code, spec in WANT.items():
                order = []
                for pre in spec["prefixes"]:
                    key = f"{pre}{code}"
                    if key not in idx:
                        continue
                    at = idx[key]
                    says = s["desc"][at].strip() if at < len(s["desc"]) else ""
                    if says and says.upper() != spec["archive_says"].upper():
                        mism.append({"member": info.filename, "column": key,
                                     "archive_says": says,
                                     "driver_expected": spec["archive_says"]})
                        continue
                    order.append((key, at))
                if order:
                    cols[code] = order
                    found[code] = [k for k, _ in order]
            if not cols:
                continue
            members.append(info.filename)
            for row in s["data"]:
                if len(row) <= max(id_at, dt_at):
                    continue
                rssd = row[id_at].strip()
                q = quarter_of_date(row[dt_at].strip())
                if not rssd.isdigit() or not q:
                    continue
                for code, order in cols.items():
                    for key, at in order:
                        if at >= len(row) or not row[at].strip():
                            continue
                        try:
                            values[q][rssd][code] = _value(WANT[code],
                                                           row[at].strip())
                        except ValueError:
                            if WANT[code].get("kind") == "flag":
                                sources[code]["(unreadable)"] += 1
                            break
                        sources[code][key] += 1
                        break
    return {q: (dict(v), found, members,
                {k: dict(c) for k, c in sources.items()}, mism)
            for q, v in values.items()}


def quarter_of_date(s: str):
    """`2009-06-30` or `06/30/2009` to `2009Q2`."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-\d{2}", s or "")
    if m:
        y, mo = m.group(1), int(m.group(2))
    else:
        m = re.fullmatch(r"(\d{2})/\d{2}/(\d{4})", s or "")
        if not m:
            return None
        y, mo = m.group(2), int(m.group(1))
    q = {3: 1, 6: 2, 9: 3, 12: 4}.get(mo)
    return f"{y}Q{q}" if q else None


def read_any(path: Path):
    """Either shape to {period: (values, found, members, sources, mism)}.

    The name says which quarters to expect and the rows say which are there.
    They are compared, because a name is a claim and the rows are the record.
    """
    if YEAR_RE.search(path.name):
        got = read_year_archive(path)
    else:
        p = period_of(path.name)
        got = {p: read_period(path)} if p else {}
    claimed = set(periods_of(path.name))
    actual = set(got)
    if claimed and actual and claimed != actual:
        for q in sorted(actual - claimed):
            got[q][4].append(
                {"member": path.name, "column": "(period)",
                 "archive_says": q,
                 "driver_expected": "one of " + ", ".join(sorted(claimed))})
    return got


def cmd_scan(a) -> int:
    arcs = archives()
    if not arcs:
        print(f"  no archives under {RAW}")
        print("  run --plan to see what to put there.")
        return 1
    print(f"archives on disk, {len(arcs)}:\n")
    broken = []
    for r in arcs:
        mark = "ok " if r.get("opens") else "BAD"
        claims = periods_of(r["name"])
        lab = claims[0] if len(claims) == 1 else (
              f"{claims[0]}-{claims[-1]}" if claims else "?")
        print(f"  {mark} {r['name']}  {r['bytes']:,} bytes  "
              f"{len(r['members'])} members   period {lab}")
        if not r.get("opens"):
            broken.append(r)
            print(f"      {r.get('error') or 'first bad member: %s' % r.get('first_bad_member')}")
    if broken:
        print("\n  an archive that will not open is NOT read. Fetch it again;")
        print("  nothing here deletes or overwrites what is already on disk.")
    print()
    for r in arcs:
        if not r.get("opens"):
            continue
        p = RAW / r["name"]
        got = read_any(p)
        if not got:
            print(f"  {r['name']}: NOTHING MATCHED. What the archive holds:")
            for diag in layout(p)[:8]:
                print(f"        {diag}")
            print("      Change the driver, not the archive.")
            continue
        for per, (values, found, members, sources, mism) in sorted(got.items()):
            cov = coverage(values, found, sources)
            print(f"  {r['name']}   [{per}]")
            print(f"      schedule files the wanted codes came from: {len(members)}")
            for mfile in members:
                print(f"        {mfile}")
            print(f"      filers seen: {len(values):,}")
            for code, c in cov.items():
                cols = "+".join(c["columns"]) if c["columns"] else "NOT FOUND"
                print(f"        {code} as {cols:<18} with a value "
                      f"{c['filers_with_a_value']:>6,}"
                      f"   non-zero {c['filers_with_a_non_zero_value']:>6,}")
                if len(c["supplied_by"]) > 1:
                    split = "  ".join(f"{k} {n:,}"
                                      for k, n in sorted(c["supplied_by"].items()))
                    print(f"             supplied by      {split}"
                          f"      (a form split, not a preference)")
            if mism:
                print("      COLUMNS NOT READ, because the archive calls them")
                print("      something else than this driver expects:")
                for x in mism:
                    print(f"        {x['column']} in {x['member']}")
                    print(f"            archive says   {x['archive_says']}")
                    print(f"            driver expects {x['driver_expected']}")
            borrow = sum(1 for v in values.values()
                         if (v.get("B993") or 0) + (v.get("B995") or 0) > 0
                         and v.get("4180"))
            pure_ff = sum(1 for v in values.values()
                          if v.get("B993") and not v.get("B995") and v.get("4180"))
            pure_rp = sum(1 for v in values.values()
                          if v.get("B995") and not v.get("B993") and v.get("4180"))
            print(f"      borrowing at all, with an expense to match: {borrow:,}")
            print(f"        fed funds and no repo: {pure_ff:>6,}"
                  f"   <- weight exactly zero, so no blend to separate")
            print(f"        repo and no fed funds: {pure_rp:>6,}")
            print(f"        a genuine blend:       {borrow - pure_ff - pure_rp:>6,}")
    return 0 if not broken else 1


def cmd_probe(a) -> int:
    """What population is readable at all, before a history is pulled.

    The design this driver was built to assumed every borrower pays a blend of
    two prices, `4180 / (B993 + B995)`, and that the two separate inside a group
    because the weight `B995 / (B993 + B995)` is observed and moves.  The first
    real period says something better and something worse.  Better: a large part
    of the panel sits at weight exactly zero or exactly one, and there the blend
    is not a blend at all, it is one price read directly.  Worse: the genuine
    blends are few, so the separation route was never going to carry much.

    It also refuses to divide.  `4180` is year to date, so a single period on
    disk cannot form a quarter's expense for anything but Q1, and a rate formed
    anyway would be about twice the truth at Q2 and three times at Q3.
    """
    arcs = [r for r in archives() if r.get("opens")]
    if not arcs:
        print(f"  no readable archive under {RAW}. Run --scan.")
        return 1
    by_period = {}
    for r in arcs:
        per = period_of(r["name"])
        values, _f, _m, _s, _x = read_period(RAW / r["name"])
        by_period[per or r["name"]] = values
    order = sorted(by_period)
    print(f"  periods on disk: {', '.join(order)}\n")
    for per in order:
        values = by_period[per]
        prev = None
        if per and re.fullmatch(r"\d{4}Q[1-4]", per):
            y, q = int(per[:4]), int(per[-1])
            prev = by_period.get(f"{y}Q{q-1}" if q > 1 else f"{y-1}Q4")
        rows, blocked = [], 0
        for rssd, v in values.items():
            ff, repo = v.get("B993") or 0.0, v.get("B995") or 0.0
            tot, ast, ytd = ff + repo, v.get("2170"), v.get("4180")
            if tot <= 0 or ast is None:
                continue
            exp = quarter_expense(ytd, (prev or {}).get(rssd, {}).get("4180"), per)
            if exp is None:
                blocked += 1
                continue
            rows.append({"rssd": rssd, "w": repo / tot, "exp": exp,
                         "tot": tot, "assets": ast})
        print(f"  {per}: {len(values):,} filers, {len(rows):,} with a quarter's "
              f"expense over a balance")
        if blocked:
            print(f"      {blocked:,} blocked: `4180` is year to date and the "
                  f"prior quarter is not on disk.")
            print(f"      That is the guard, not a failure. Put the previous "
                  f"period next to this one.")
        if not rows:
            continue
        pure_ff = [x for x in rows if x["w"] == 0.0]
        pure_repo = [x for x in rows if x["w"] == 1.0]
        blend = [x for x in rows if 0.0 < x["w"] < 1.0]
        for label, sel in (("weight exactly 0, fed funds only", pure_ff),
                           ("weight exactly 1, repo only", pure_repo),
                           ("a genuine blend", blend)):
            if not sel:
                print(f"    {label:<34} {0:>5}")
                continue
            rates = sorted(4.0 * x["exp"] / x["tot"] for x in sel)
            qf = lambda p: rates[min(len(rates) - 1, int(p * (len(rates) - 1)))]
            print(f"    {label:<34} {len(sel):>5} filers   "
                  f"annualised cost p10 {qf(.10):.4f}  median {qf(.50):.4f}  "
                  f"p90 {qf(.90):.4f}")
        if blend:
            ws = sorted(x["w"] for x in blend)
            qw = lambda p: ws[min(len(ws) - 1, int(p * (len(ws) - 1)))]
            print(f"    the blend group's weight: p10 {qw(.10):.3f}  "
                  f"median {qw(.50):.3f}  p90 {qw(.90):.3f}")
        print("    the weight-zero group is the one the arm wants: there the")
        print("    expense line is the fed funds bill and nothing else, so no")
        print("    separation is needed and none is assumed.")
    return 0




MANIFEST = RAW / "MANIFEST.json"


def rel(p: Path) -> str:
    """A path to show: shortened when it sits under the repository, left whole
    when it does not. `relative_to` raises on the second case, which turns a
    line of output into a crash. Found by the selftest, which points these at
    a temporary directory."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    if not MANIFEST.exists():
        return {"archives": {}}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(man):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")


def cmd_verify(a) -> int:
    """Check every archive on disk against what was there last time, and say
    which quarters of the wanted window are still missing.

    Seventy downloads done by hand over some days is seventy chances for one to
    come down short, and a short zip that still opens is the bad case: the
    coverage table would simply show fewer filers and nothing would say why.
    So each archive gets a digest recorded the first time it is seen, and a
    later run that finds a different digest under the same name **reports it and
    keeps both records**.  A digest that changed is either a corrected filing or
    a broken download, and which one it is is not this driver's to decide.

    Nothing here writes to an archive and nothing here removes a manifest entry.
    """
    man = load_manifest()
    known = man["archives"]
    arcs = archives()
    if not arcs:
        print(f"  no archives under {RAW}")
        return 1
    wanted = quarters(a.start, a.end)
    seen, unreadable, fresh, changed, broken = {}, {}, [], [], []
    print(f"archives on disk, {len(arcs)}:\n")
    for r in arcs:
        name = r["name"]
        pers = periods_of(name)
        per = pers[0] if len(pers) == 1 else None
        p = RAW / name
        digest = sha256(p)
        rec = {"period": per, "bytes": r["bytes"], "sha256": digest,
               "opens": bool(r.get("opens")), "members": len(r["members"])}
        if not r.get("opens"):
            broken.append(name)
        prev = known.get(name)
        if prev is None:
            known[name] = dict(rec, first_seen=a.today, history=[])
            fresh.append(name)
            mark = "new"
        elif prev.get("sha256") == digest:
            mark = "same"
        else:
            #: keep the old record rather than replacing it.  Which of the two
            #: is right is a question about the filing, not about this run.
            prev.setdefault("history", []).append(
                {k: prev.get(k) for k in ("bytes", "sha256", "opens", "members")}
                | {"replaced_on": a.today})
            prev.update(rec)
            changed.append(name)
            mark = "CHANGED"
        #: a period counts as present only when an archive that opens supplies
        #: it, and one archive can supply four. Counting files rather than
        #: periods is `D37`, and this very tool has now done it twice: it
        #: reported "present 70, missing 0" on a set whose 2009Q2 was a zero
        #: byte file, and then reported 2009Q2 unreadable after a one-year
        #: archive had supplied it. A name list is not a record.
        for q in pers:
            (seen if r.get("opens") else unreadable).setdefault(q, []).append(name)
        lab = (pers[0] if len(pers) == 1 else
               f"{pers[0]}-{pers[-1]}" if pers else "?")
        print(f"  {mark:<8} {name}")
        print(f"           period {lab}   {r['bytes']:,} bytes   "
              f"{'opens' if r.get('opens') else 'WILL NOT OPEN'}   "
              f"sha {digest[:16]}")
    save_manifest(man)
    print()
    #: three states, and the middle one has to exist (`11c`, rule 23): a
    #: quarter whose archive is on disk but will not open is neither present
    #: nor absent, and the two want opposite responses.
    #: an unreadable archive only leaves a hole when nothing else supplies
    #: that quarter. One product failing where another succeeds is not a gap.
    dead = [q for q in wanted if q not in seen and q in unreadable]
    missing = [q for q in wanted if q not in seen and q not in unreadable]
    dupes = {q: v for q, v in seen.items() if len(v) > 1}
    outside = sorted(q for q in seen if q not in wanted)
    print(f"the window asked for: {wanted[0]} to {wanted[-1]}, "
          f"{len(wanted)} quarters")
    print(f"  readable {len(seen and [q for q in wanted if q in seen]):>3}"
          f"      on disk but unreadable {len(dead):>3}"
          f"      not on disk {len(missing):>3}")
    if dead:
        print("  on disk and will not open, so this quarter has NO reading:")
        for i in range(0, len(dead), 8):
            print("    " + "  ".join(dead[i:i + 8]))
    if missing:
        print("  not on disk at all, still to fetch, in order:")
        for i in range(0, len(missing), 8):
            print("    " + "  ".join(missing[i:i + 8]))
    if dupes:
        print("  more than one archive claims the same quarter, which is a name")
        print("  collision and not a fact about the data:")
        for q, v in sorted(dupes.items()):
            print(f"    {q}: " + ", ".join(v))
    if outside:
        print(f"  on disk but outside the window, kept and not read: "
              + ", ".join(outside))
    if changed:
        print("\n  AN ARCHIVE CHANGED UNDER THE SAME NAME:")
        for n in changed:
            print(f"    {n}")
        print("  the previous digest is kept in the manifest's history. A digest")
        print("  that moved is either a corrected filing or a short download,")
        print("  and those want opposite responses. Check before building.")
    if broken:
        print("\n  WILL NOT OPEN, so not read: " + ", ".join(broken))
        print("  fetch again. Nothing here deletes or overwrites what is on disk.")
    print(f"\n  manifest: {rel(MANIFEST)}  "
          f"({len(known)} archive(s) recorded, {len(fresh)} added this run)")
    return 1 if (broken or changed or dead) else 0


def want_signature():
    """What this driver asks an archive for, in a form that survives a JSON
    round trip.  A cached period is only as good as the question it answered:
    an archive whose bytes have not moved, read under a driver that now wants
    one more code, or reads one of its codes another way, has to be read again."""
    return [[code, spec["schedule"], list(spec["prefixes"]), spec["archive_says"],
             spec.get("kind", "number")]
            for code, spec in sorted(WANT.items())]


def cmd_build(a) -> int:
    arcs = [r for r in archives() if r.get("opens")]
    if not arcs:
        print(f"  no readable archive under {RAW}. Run --scan.")
        return 1
    old = {}
    if CACHE.exists() and not a.rebuild:
        try:
            old = json.loads(CACHE.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
    panel, refused, reused, collided = {}, [], [], []
    for r in arcs:
        digest = sha256(RAW / r["name"])
        claims = periods_of(r["name"])
        #: seventy archives is long enough that re-parsing every one to add the
        #: seventy-first is the difference between a command you run and one you
        #: avoid. The digest says a period has not moved; the file name does not.
        #: and a period is reused only when the driver asks the same question
        #: it asked last time, or a code added to `WANT` would come back absent
        #: from every reused period while every count looked full.
        if (len(claims) == 1 and claims[0] in old
                and old[claims[0]].get("sha256") == digest
                and old[claims[0]].get("want") == want_signature()):
            panel[claims[0]] = old[claims[0]]
            reused.append(claims[0])
            continue
        for per, (values, found, members, sources, mism) in sorted(
                read_any(RAW / r["name"]).items()):
            if per in panel:
                #: two archives claiming one quarter is a name collision, not a
                #: fact about the data. Refuse it rather than let whichever
                #: sorted last win, which is how one source silently replaces
                #: another that was never compared with it.
                collided.append((per, panel[per]["archive"], r["name"]))
                continue
            if mism:
                refused.append({"archive": r["name"], "period": per,
                                "mismatches": mism})
            panel[per] = {
                "archive": r["name"],
                "sha256": digest,
                "want": want_signature(),
                "columns_used": found,
                "supplied_by": sources,
                "schedule_files": members,
                "columns_refused": mism,
                "filers": {k: {c: v[c] for c in sorted(v)}
                           for k, v in sorted(values.items())},
            }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    #: sorted keys and an explicit float format, so two machines write the same
    #: bytes and a real change is not buried under a spurious one.
    CACHE.write_text(json.dumps(panel, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")
    n = sum(len(v["filers"]) for v in panel.values())
    print(f"  wrote {rel(CACHE)}: {len(panel)} period(s), {n:,} filer-period rows")
    if reused:
        print(f"  {len(reused)} period(s) reused from the cache unchanged; "
              f"pass --rebuild to parse them again")
    for x in refused:
        print(f"  {x['archive']} [{x['period']}]: {len(x['mismatches'])} "
              f"column(s) not read, see columns_refused")
    for per, keeper, loser in collided:
        print(f"  {per}: TWO ARCHIVES CLAIM IT. Kept {keeper}, refused {loser}.")
        print(f"      Cross-check them, then take one out of the way by renaming")
        print(f"      it with an .expired suffix. Nothing here deletes anything.")
    print("  the cache is rebuildable from the archives; the archives are not")
    print("  rebuildable from anything, so nothing here writes to them.")
    return 1 if collided else 0


def _fixture(rows_rc, rows_ri, desc_rc=None, extra=None, period="06302026"):
    """An archive shaped like the real one: codes on line 1, the archive's own
    descriptions on line 2, filers after."""
    rc_cols = ["IDRSSD", "RCONB993", "RCFDB995", "RCONB995", "RCFD2170", "RCON2170"]
    rc_desc = desc_rc or ["ID RSSD", "FEDERAL FNDS PURCD IN DOMESTIC OFFCS",
                          "SECURS SOLD UNDR AGRMNTS TO REPURCH",
                          "SECURS SOLD UNDR AGRMNTS TO REPURCH",
                          "TOTAL ASSETS", "TOTAL ASSETS"]
    ri_cols = ["IDRSSD", "RIAD4180"]
    ri_desc = ["ID RSSD", "EXPENSE OF FED FUNDS PUR & SEC SOLD"]
    def tsv(cols, desc, rows):
        return "\n".join(["\t".join(cols), "\t".join(desc)]
                         + ["\t".join(str(c) for c in r) for r in rows])
    out = {f"FFIEC CDR Call Schedule RC {period}.txt": tsv(rc_cols, rc_desc, rows_rc),
           f"FFIEC CDR Call Schedule RI {period}.txt": tsv(ri_cols, ri_desc, rows_ri)}
    out.update(extra or {})
    return out


def _write_zip(path, members):
    with zipfile.ZipFile(path, "w") as z:
        for name, text in members.items():
            z.writestr(name, text)
    return path


def selftest() -> int:
    """Grow the failures this driver has to be able to report.

    Four of these are defects this driver actually had, found by the 2026Q2
    archive on the first real `--scan`.  Every one of them produced a full
    coverage table and would have produced a panel nothing downstream could
    question, so asking whether a check could fail was never going to find them.
    Plant the failure and assert it is caught (`11f`).
    """
    import tempfile
    fails = []

    def quiet(fn, *args):
        """Run a command with its output captured, and hand back both, so the
        selftest reads as a list of checks rather than as a transcript."""
        buf = io.StringIO()
        saved, sys.stdout = sys.stdout, buf
        try:
            rc = fn(*args)
        finally:
            sys.stdout = saved
        return rc, buf.getvalue()

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    expect(quarters("2009Q1", "2009Q4") == ["2009Q1", "2009Q2", "2009Q3", "2009Q4"],
           "a year of quarters comes out in order")
    expect(len(quarters("2009Q1", "2025Q4")) == 68,
           "the era from 2009Q1 to 2025Q4 is 68 quarters")
    c = cost_table(quarters("2009Q1", "2025Q4"))
    expect(c["bulk_downloads"] == 68 and c["pws_calls_whole_panel"] == 68 * PANEL_ALL,
           "the cost table multiplies out rather than describing")
    expect(c["pws_hours_whole_panel"] > 100,
           "and it shows the per-institution route costs over a hundred hours")
    expect(period_of("FFIEC CDR Call Bulk All Schedules 06302026.zip") == "2026Q2"
           and period_of("x 03312001 y") == "2001Q1"
           and period_of("x 12312019 y") == "2019Q4",
           "a period label is read off the archive's own name")
    expect(schedule_of("FFIEC CDR Call Schedule RCRII 06302026(2 of 4).txt") == "RCRII"
           and schedule_of("FFIEC CDR Call Schedule RC 06302026.txt") == "RC",
           "a member file names its own schedule, and RC is not RCRII")

    # --- plant one: the asset legs must stay out ------------------------------
    expect(set(WANT) == {"B993", "B995", "4180", "2170", "3353", "0090",
                         "B989", "4020", "3365", "K656", "K657", "K658"},
           "the wanted codes are both legs with their flows and averages, total "
           "assets, the reserve balance and the banker's bank items")
    leg_codes = {n: set(leg.values()) for n, leg in LEGS.items()}
    expect(all(c in WANT for codes in leg_codes.values() for c in codes)
           and not (leg_codes["borrowed"] & leg_codes["lent"])
           and all(LEGS[n]["flow"] in YTD_CODES for n in LEGS),
           "each leg's flow, average and repo half are wanted, the two legs share "
           "no code, and both flows are differenced from year to date")
    words = {n: " ".join(WANT[c]["archive_says"] for c in LEGS[n].values())
             for n in LEGS}
    expect(not any(w in words["borrowed"] for w in ("RESELL", "SOLD&SEC RS", "INCOME"))
           and not any(w in words["lent"] for w in ("REPURCH", "PCHD&SEC RP", "EXPENSE")),
           "and by the archive's own words each leg holds only its own side")
    expect("B987" in REJECTED and not (set(WANT) & set(REJECTED)),
           "the fed funds sold balance is named as not wanted, and is not also wanted")
    expect(WANT["K656"].get("kind") == "flag"
           and all(WANT[c].get("kind", "number") == "number" for c in WANT if c != "K656"),
           "the certification is the one flag column")

    hdr = "IDRSSD\tRCONB993\tRCFDB995\tRIAD4180\tRCON2170"
    desc = "ID RSSD\tFed funds\tRepo\tExpense\tAssets"
    body = "12345\t100\t900\t7\t50000\n67890\t0\t0\t0\t900"
    text = hdr + "\n" + desc + "\n" + body
    s = _sniff(text)
    expect(s and s["header_row"] == 0 and s["mdrm_like"] == 4,
           "the MDRM row is picked over the description row")
    expect(s and s["desc"][1] == "Fed funds" and len(s["data"]) == 2,
           "the description row is split off and is not left among the data")
    for d, name in (("\t", "tab"), (";", "semicolon"), (",", "comma"),
                    ("|", "pipe")):
        s2 = _sniff(text.replace("\t", d))
        expect(s2 and s2["mdrm_like"] == 4,
               f"a {name} delimited period is read, not reported as unmatched")

    with tempfile.TemporaryDirectory() as tmp:
        T = Path(tmp)

        # --- the well formed case --------------------------------------------
        good = _write_zip(T / "good.zip", _fixture(
            rows_rc=[[111, 100, "", 900, "", 50000],
                     [222, 0, "", 0, "", 900]],
            rows_ri=[[111, 7], [222, 0]]))
        values, found, members, sources, mism = read_period(good)
        expect(len(values) == 2 and values.get("111", {}).get("B993") == 100.0
               and values.get("111", {}).get("B995") == 900.0,
               "a well formed archive reads its filers")
        expect(found["B993"] == ["RCONB993"] and found["4180"] == ["RIAD4180"]
               and not mism,
               "and records which columns the period actually used")
        cov = coverage(values, found, sources)
        expect(cov["B993"]["filers_with_a_value"] == 2
               and cov["B993"]["filers_with_a_non_zero_value"] == 1,
               "a column with a value and a column with a non-zero value are "
               "counted apart (`D37`)")

        # --- plant two: the form split ---------------------------------------
        split = _write_zip(T / "split.zip", _fixture(
            rows_rc=[[111, 100, 900, "", 80000, ""],      # an 031 filer
                     [222, 5, "", 40, "", 900]],          # an 041 filer
            rows_ri=[[111, 7], [222, 1]]))
        v2, f2, _m, s2src, _x = read_period(split)
        expect(v2.get("111", {}).get("2170") == 80000.0
               and v2.get("222", {}).get("2170") == 900.0,
               "both forms' filers get a total-assets figure, not just one form's")
        expect(s2src.get("2170") == {"RCFD2170": 1, "RCON2170": 1},
               "and the scan can say which form supplied each, so an eighty "
               "against four thousand split is visible rather than a full total")

        # --- plant three: one code, two schedules ----------------------------
        rcrii = ("IDRSSD\tRCON2170\n"
                 "ID RSSD\tTOTAL ASSETS\n"
                 "222\t7\n111\t9")
        twofile = _write_zip(T / "two.zip", _fixture(
            rows_rc=[[111, 100, 900, "", "", 50000],
                     [222, 5, "", 40, "", 900]],
            rows_ri=[[111, 7], [222, 1]],
            extra={"FFIEC CDR Call Schedule RCRII 06302026(2 of 4).txt": rcrii}))
        v3, _f, m3, _s, _x = read_period(twofile)
        expect(v3.get("222", {}).get("2170") == 900.0
               and v3.get("111", {}).get("2170") == 50000.0,
               "total assets comes from Schedule RC even when RC-R Part II "
               "carries the same code under the same description")
        expect(all(schedule_of(x) in ("RC", "RI") for x in m3),
               "and the regulatory-capital schedule is not among the files read")

        # --- plant four: the archive calls the column something else ---------
        wrong = _write_zip(T / "wrong.zip", _fixture(
            rows_rc=[[111, 100, 900, "", "", 50000]],
            rows_ri=[[111, 7]],
            desc_rc=["ID RSSD", "FEDERAL FNDS SOLD",     # the asset leg's name
                     "SECURS SOLD UNDR AGRMNTS TO REPURCH",
                     "SECURS SOLD UNDR AGRMNTS TO REPURCH",
                     "TOTAL ASSETS", "TOTAL ASSETS"]))
        v4, f4, _m, _s, mism4 = read_period(wrong)
        expect(any(x["column"] == "RCONB993" for x in mism4),
               "a column the archive names differently is reported")
        expect("B993" not in v4.get("111", {}) and "B993" not in f4,
               "and it is not read, because a code naming a different object "
               "is the one failure that leaves every count looking full")
        expect(v4.get("111", {}).get("B995") == 900.0,
               "while the columns that do match are still read")

        # --- plant eleven: the quarterly average comes from RC-K -------------
        #: RC carries a planted 3353 under the right words and a different
        #: value; RC-K carries the real one under both prefixes, and next to
        #: it the asset legs' average, 3365.
        rc_with_avg = _fixture(
            rows_rc=[[111, 100, 900, "", 80000, ""], [222, 5, "", 40, "", 900]],
            rows_ri=[[111, 7], [222, 1]])
        rc_name = "FFIEC CDR Call Schedule RC 06302026.txt"
        lines = rc_with_avg[rc_name].split("\n")
        lines[0] += "\tRCON3353\tRCON3365"
        lines[1] += "\tQTLY AVG OF FED FUNDS PCHD&SEC RP\tQTLY AVG OF FED FUNDS SOLD&SEC RS"
        lines[2] += "\t1\t3"
        lines[3] += "\t2\t4"
        rc_with_avg[rc_name] = "\n".join(lines)
        rck = ("IDRSSD\tRCFD3353\tRCON3353\tRCON3365\n"
               "ID RSSD\tQTLY AVG OF FED FUNDS PCHD&SEC RP\t"
               "QTLY AVG OF FED FUNDS PCHD&SEC RP\tQTLY AVG OF FED FUNDS SOLD&SEC RS\n"
               "111\t950\t\t40\n222\t\t33\t7")
        rc_with_avg["FFIEC CDR Call Schedule RCK 06302026.txt"] = rck
        avg = _write_zip(T / "avg.zip", rc_with_avg)
        v11, f11, m11, s11, x11 = read_period(avg)
        expect(v11.get("111", {}).get("3353") == 950.0
               and v11.get("222", {}).get("3353") == 33.0,
               "the quarterly average is read from RC-K, under either prefix, and "
               "not from a same-named column planted on RC")
        expect(s11.get("3353") == {"RCFD3353": 1, "RCON3353": 1}
               and any(schedule_of(x) == "RCK" for x in m11) and not x11,
               "and the scan can say which prefix supplied it")
        expect(v11.get("111", {}).get("3365") == 40.0
               and v11.get("222", {}).get("3365") == 7.0,
               "the asset legs' average beside it is read as its own code, from "
               "RC-K and not from the same-named column planted on RC")
        wrong_avg = dict(rc_with_avg)
        wrong_avg["FFIEC CDR Call Schedule RCK 06302026.txt"] = rck.replace(
            "ID RSSD\tQTLY AVG OF FED FUNDS PCHD&SEC RP\tQTLY AVG OF FED FUNDS PCHD&SEC RP",
            "ID RSSD\tQTLY AVG OF FED FUNDS SOLD&SEC RS\tQTLY AVG OF FED FUNDS SOLD&SEC RS")
        v12, f12, _m, _s, x12 = read_period(_write_zip(T / "wrong_avg.zip", wrong_avg))
        expect(any(x["column"] == "RCFD3353" for x in x12)
               and all("3353" not in v for v in v12.values()) and "3353" not in f12,
               "an average column the archive describes as the asset legs' is "
               "reported and not read")

        # --- plant twelve: the certification is a word, read as a flag -------
        #: RC-O carries the flag under both prefixes in both cases and one token
        #: that is neither word.  RC-R Part II, which sorts after RC-O, carries a
        #: same-named column with every answer reversed, so a reader that
        #: searched for the column instead of naming the schedule would end on
        #: the wrong ones.
        rco = ("IDRSSD\tRCFDK656\tRCONK656\tRCONK657\tRCONK658\n"
               "ID RSSD\tBANKER'S BANK CERTIFICATION\tBANKER'S BANK CERTIFICATION\t"
               "BNKRS BNK DEDUCTIONS\tBNKR BNK DEDUCTION LIMIT\n"
               "111\ttrue\t\t500\t1500\n222\t\tFALSE\t0\t0\n"
               "333\t\tTRUE\t10\t20\n444\tyes\t\t0\t0")
        rev = ("IDRSSD\tRCONK656\n"
               "ID RSSD\tBANKER'S BANK CERTIFICATION\n"
               "111\tfalse\n222\ttrue\n333\tfalse\n444\ttrue")
        flags = _fixture(rows_rc=[[111, 100, 900, "", 80000, ""],
                                  [222, 5, "", 40, "", 900],
                                  [333, 1, "", 0, "", 700],
                                  [444, 0, "", 0, "", 600]],
                         rows_ri=[[111, 7], [222, 1], [333, 0], [444, 0]],
                         extra={"FFIEC CDR Call Schedule RCO 06302026.txt": rco,
                                "FFIEC CDR Call Schedule RCRII 06302026(2 of 4).txt": rev})
        v13, f13, m13, s13, x13 = read_period(_write_zip(T / "flags.zip", flags))
        expect(v13["111"].get("K656") == 1.0 and v13["222"].get("K656") == 0.0
               and v13["333"].get("K656") == 1.0,
               "the certification reads as one or zero whatever its case, under "
               "either prefix, from RC-O and not from a same-named column elsewhere")
        expect("K656" not in v13["444"]
               and s13.get("K656", {}).get("(unreadable)") == 1,
               "a token that is neither word is not read, and is counted as "
               "unreadable rather than dropped")
        expect(v13["111"].get("K657") == 500.0 and v13["333"].get("K658") == 20.0
               and not x13,
               "the deduction and its limit read as numbers beside it")

        # --- plant thirteen: the asset leg's flow and its repo half ----------
        lent = _fixture(rows_rc=[[111, 100, "", 0, "", 50000]], rows_ri=[[111, 7]])
        ri_name = "FFIEC CDR Call Schedule RI 06302026.txt"
        ri_lines = lent[ri_name].split("\n")
        ri_lines[0] += "\tRIAD4020"
        ri_lines[1] += "\tINCOME&FEES-FED FUNDS SOLD & SEC PUR"
        ri_lines[2] += "\t9"
        lent[ri_name] = "\n".join(ri_lines)
        rc_l = lent[rc_name].split("\n")
        rc_l[0] += "\tRCFDB989\tRCONB989"
        rc_l[1] += ("\tSECURS PURCHSD UDR AGRMNTS TO RESELL"
                    "\tSECURS PURCHSD UDR AGRMNTS TO RESELL")
        rc_l[2] += "\t\t0"
        lent[rc_name] = "\n".join(rc_l)
        v14, f14, _m, _s, x14 = read_period(_write_zip(T / "lent.zip", lent))
        expect(v14["111"].get("4020") == 9.0 and v14["111"].get("4180") == 7.0
               and v14["111"].get("B989") == 0.0 and not x14,
               "the asset leg's income reads beside the liability leg's expense, "
               "and reverse repo under whichever prefix carries it")
        wrong_ri = dict(lent)
        wrong_ri[ri_name] = lent[ri_name].replace(
            "\tINCOME&FEES-FED FUNDS SOLD & SEC PUR", "\tEXPENSE OF FED FUNDS PUR & SEC SOLD")
        v15, f15, _m, _s, x15 = read_period(_write_zip(T / "wrong_ri.zip", wrong_ri))
        expect(any(x["column"] == "RIAD4020" for x in x15)
               and "4020" not in v15["111"] and v15["111"].get("4180") == 7.0,
               "an income column the archive describes as the expense is reported "
               "and not read, while the expense beside it still is")

        # --- plant five: year to date ----------------------------------------
        expect(quarter_expense(100.0, None, "2026Q1") == 100.0,
               "Q1's year-to-date figure is already a quarter")
        expect(quarter_expense(100.0, None, "2026Q2") is None,
               "Q2 with no prior quarter on disk yields no expense at all, "
               "rather than a figure about twice the truth")
        expect(quarter_expense(100.0, 40.0, "2026Q2") == 60.0,
               "and with the prior quarter it is the difference")


        # --- plant six: the manifest, and an archive that changed under it ----
        import argparse as _ap
        global RAW, MANIFEST, CACHE
        _saved = (RAW, MANIFEST, CACHE)
        try:
            RAW = T / "raw"; RAW.mkdir()
            MANIFEST = RAW / "MANIFEST.json"
            CACHE = T / "cache.json"
            args = _ap.Namespace(start="2026Q1", end="2026Q2",
                                 today="2026-09-16", rebuild=False)
            one = _fixture(rows_rc=[[111, 100, "", 900, "", 50000]],
                           rows_ri=[[111, 7]], period="06302026")
            _write_zip(RAW / "FFIEC CDR Call Bulk All Schedules 06302026.zip", one)
            rc0, _ = quiet(cmd_verify, args)
            man = load_manifest()["archives"]
            key = "FFIEC CDR Call Bulk All Schedules 06302026.zip"
            expect(rc0 == 0 and man[key]["period"] == "2026Q2"
                   and len(man[key]["sha256"]) == 64,
                   "a first sighting is recorded with its digest and its period")

            #: the same name, different bytes.  This is the failure seventy
            #: hand-downloads over some days actually produces, and a short zip
            #: that still opens would otherwise pass every check there is.
            two = dict(one)
            two["FFIEC CDR Call Schedule RC 06302026.txt"] += "\n222\t5\t\t40\t\t900"
            _write_zip(RAW / key, two)
            rc1, _ = quiet(cmd_verify, args)
            man2 = load_manifest()["archives"][key]
            expect(rc1 != 0, "an archive whose digest moved makes --verify fail")
            expect(len(man2.get("history", [])) == 1
                   and man2["history"][0]["sha256"] != man2["sha256"],
                   "and the digest it had before is kept, not replaced")

            #: the window's other quarter is absent and has to be named.
            _, seen_txt = quiet(cmd_verify, args)
            expect("2026Q1" in seen_txt and "not on disk at all" in seen_txt,
                   "a quarter of the window with no archive at all is named")


            #: plant eight: a zero-byte archive is on disk for a quarter of the
            #: window.  The first version of --verify counted the file and
            #: reported that quarter present, which is `D37` committed by the
            #: tool written to catch `D37`.
            (RAW / "FFIEC CDR Call Bulk All Schedules 03312026.zip").write_bytes(b"")
            rc2, txt2 = quiet(cmd_verify, args)
            expect(rc2 != 0, "a zero-byte archive makes --verify fail")
            expect("unreadable   1" in txt2.replace("  ", " ").replace(" ", "  ")
                   or "on disk but unreadable" in txt2,
                   "and the quarter it claims is reported as on disk but unreadable")
            expect("on disk and will not open" in txt2
                   and "2026Q1" in txt2.split("on disk and will not open")[1],
                   "while only the quarter that opens is counted readable")
            expect("not on disk at all" not in txt2,
                   "and the same quarter is not also listed as still to fetch, "
                   "which would be two contradictory instructions for one quarter")
            # --- plant seven: the build reuses what has not moved ------------
            quiet(cmd_build, args)
            first = json.loads(CACHE.read_text(encoding="utf-8"))
            expect(set(first) == {"2026Q2"} and len(first["2026Q2"]["filers"]) == 2
                   and len(first["2026Q2"]["sha256"]) == 64,
                   "the cache is keyed by period and records the digest it came from")
            _, again = quiet(cmd_build, args)
            expect("reused from the cache unchanged" in again,
                   "a second build reuses a period whose digest has not moved")
            three = dict(two)
            three["FFIEC CDR Call Schedule RC 06302026.txt"] += "\n333\t1\t\t2\t\t300"
            _write_zip(RAW / key, three)
            _, third = quiet(cmd_build, args)
            after = json.loads(CACHE.read_text(encoding="utf-8"))
            expect("reused" not in third
                   and len(after["2026Q2"]["filers"]) == 3,
                   "and re-parses one whose digest has moved, rather than "
                   "trusting the name")

            #: plant ten: the archive has not moved and the driver has.  A code
            #: added to `WANT` with the old cache reused would come back absent
            #: from every period while every count looked full.
            _, fourth = quiet(cmd_build, args)
            expect("reused from the cache unchanged" in fourth,
                   "an unmoved archive under an unchanged driver is reused")
            WANT["PLNT"] = {"schedule": "RC", "prefixes": ("RCON",),
                            "label": "planted", "archive_says": "PLANTED"}
            try:
                _, fifth = quiet(cmd_build, args)
            finally:
                del WANT["PLNT"]
            expect("reused" not in fifth,
                   "and parsed again once the wanted codes change, although "
                   "its digest has not moved")
            quiet(cmd_build, args)
            _, settled = quiet(cmd_build, args)
            WANT["K656"]["kind"] = "number"
            try:
                _, toggled = quiet(cmd_build, args)
            finally:
                WANT["K656"]["kind"] = "flag"
            expect("reused from the cache unchanged" in settled
                   and "reused" not in toggled,
                   "and parsed again when a column changes how it is read, "
                   "although no code and no digest moved")
        finally:
            RAW, MANIFEST, CACHE = _saved

        # --- plant nine: one archive, four quarters, period in a column ------
        #: the by-year product. A reader that assumes one archive is one period
        #: keeps whichever quarter sorted last and reports a full count.
        ycols = ["Reporting Period End Date", "IDRSSD", "RCONB993", "RCFDB995",
                 "RCONB995", "RCFD2170", "RCON2170"]
        ydesc = ["", "", "FEDERAL FNDS PURCD IN DOMESTIC OFFCS",
                 "SECURS SOLD UNDR AGRMNTS TO REPURCH",
                 "SECURS SOLD UNDR AGRMNTS TO REPURCH", "TOTAL ASSETS", "TOTAL ASSETS"]
        yrows = [["2009-03-31", 111, 10, "", 20, "", 1000],
                 ["2009-06-30", 111, 11, "", 21, "", 1100],
                 ["2009-09-30", 111, 12, "", 22, "", 1200],
                 ["2009-12-31", 111, 13, "", 23, "", 1300],
                 ["2009-06-30", 222, 90, 95, "", 9000, ""]]
        icols = ["Reporting Period End Date", "IDRSSD", "RIAD4180", "RIAD4020"]
        idesc = ["", "", "EXPENSE OF FED FUNDS PUR & SEC SOLD",
                 "INCOME&FEES-FED FUNDS SOLD & SEC PUR"]
        irows = [["2009-03-31", 111, 1, 5], ["2009-06-30", 111, 2, 6],
                 ["2009-09-30", 111, 3, 7], ["2009-12-31", 111, 4, 8],
                 ["2009-06-30", 222, 7, 0]]
        def tsv(c, d, rs):
            return "\n".join(["\t".join(c), "\t".join(d)]
                             + ["\t".join(str(x) for x in r) for r in rs])
        ypath = _write_zip(T / "FFIEC CDR Call Bulk Subset of Schedules 2009.zip", {
            "FFIEC CDR Call Subset of Schedules 2009(1 of 2).txt": tsv(ycols, ydesc, yrows),
            "FFIEC CDR Call Subset of Schedules 2009(2 of 2).txt": tsv(icols, idesc, irows),
            "Readme.txt": "a note, not a table"})
        got = read_any(ypath)
        expect(sorted(got) == ["2009Q1", "2009Q2", "2009Q3", "2009Q4"],
               "a one-year archive comes back as four quarters, not one")
        expect(got["2009Q2"][0]["111"]["B993"] == 11.0
               and got["2009Q4"][0]["111"]["B993"] == 13.0,
               "and each quarter keeps its own values rather than the last row's")
        expect(got["2009Q2"][0]["111"]["4180"] == 2.0,
               "the income statement file joins on (quarter, filer), not on filer")
        expect(got["2009Q3"][0]["111"]["4020"] == 7.0
               and got["2009Q2"][0]["222"]["4020"] == 0.0,
               "and the asset leg's income joins the same way")
        expect(len(got["2009Q2"][0]) == 2 and len(got["2009Q1"][0]) == 1,
               "a filer present in one quarter only appears in that quarter only")
        expect(got["2009Q2"][0]["222"]["B995"] == 95.0
               and got["2009Q2"][0]["222"]["2170"] == 9000.0,
               "the form split still works inside the one-year shape")
        expect(periods_of("FFIEC CDR Call Bulk Subset of Schedules 2009.zip")
               == ["2009Q1", "2009Q2", "2009Q3", "2009Q4"]
               and periods_of("x 06302009 y.zip") == ["2009Q2"],
               "the name says which quarters to expect, for both shapes")
        expect(quarter_of_date("2009-06-30") == "2009Q2"
               and quarter_of_date("06/30/2009") == "2009Q2"
               and quarter_of_date("") is None,
               "both date spellings read, and a blank reads as no quarter")

        #: the name claims a year and a row carries another: reported, not trusted
        bad_year = _write_zip(T / "FFIEC CDR Call Bulk Subset of Schedules 2011.zip", {
            "FFIEC CDR Call Subset of Schedules 2011(1 of 2).txt": tsv(ycols, ydesc, yrows),
            "FFIEC CDR Call Subset of Schedules 2011(2 of 2).txt": tsv(icols, idesc, irows)})
        gy = read_any(bad_year)
        expect(any(x["column"] == "(period)"
                   for q in gy for x in gy[q][4]),
               "an archive whose rows fall outside the year its name claims is "
               "reported, because the name is a claim and the rows are the record")
        # --- truncation -------------------------------------------------------
        bad = T / "truncated.zip"
        raw = good.read_bytes()
        bad.write_bytes(raw[: len(raw) // 2])
        try:
            with zipfile.ZipFile(bad) as z:
                opened = z.testzip() is None
        except Exception:
            opened = False
        expect(not opened, "a truncated archive does not open, so it is not read")

    if fails:
        print("\n  selftest FAILED")
        for x in fails:
            print("     " + x)
        return 1
    print("\n  selftest passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true",
                    help="print the cost of each route and what to put on disk")
    ap.add_argument("--scan", action="store_true",
                    help="report every archive on disk, what opens, and which "
                         "codes carry values")
    ap.add_argument("--probe", action="store_true",
                    help="does the repo weight move inside a size band, which "
                         "is what decides whether the blend separates at all")
    ap.add_argument("--verify", action="store_true",
                    help="digest every archive against the manifest and say "
                         "which quarters of the window are still missing")
    ap.add_argument("--rebuild", action="store_true",
                    help="with --build, parse every archive again instead of "
                         "reusing cache entries whose digest has not moved")
    ap.add_argument("--build", action="store_true",
                    help="build the rebuildable cache from the archives")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--start", default="2009Q1")
    ap.add_argument("--end", default=BULK_LAST)
    a = ap.parse_args(argv)
    a.today = datetime.date.today().isoformat()
    if a.selftest:
        return selftest()
    if a.scan:
        return cmd_scan(a)
    if a.verify:
        return cmd_verify(a)
    if a.probe:
        return cmd_probe(a)
    if a.build:
        return cmd_build(a)
    return cmd_plan(a)


if __name__ == "__main__":
    sys.exit(main())
