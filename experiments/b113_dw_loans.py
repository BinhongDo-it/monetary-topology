"""B113 driver: the Federal Reserve's discount window loans, read under each workbook's own header.

What this is for. B113 reads which depository institutions have an edge to the discount
window. The loan-level workbooks name every borrower by its ABA routing number, the Call
Report's panel of reporters carries the same number, and this driver turns the fifty-six
quarterly workbooks under `data/b59/dw/` into one rebuildable cache of loans.

What each workbook looked like when it was read (2026-09-16). The loan sheet is called
`discount window loan data`, except in 2012Q3 where it is `discount window borrowing data`,
and a definitions sheet carries the same column names down its first column, so the loan
sheet is found by a row that holds every wanted name at once and never by a sheet name or a
first cell. Its header is on the fourth row. The first twelve columns carry the same names in
every workbook; the collateral columns are named four ways, and only their total is read. Dates
are Excel serial numbers in the `.xls` workbooks and date cells in the `.xlsx` ones. From 2018
four note rows follow the loans. A trailing `*` on the type of credit marks loans of one type,
term and rate made to one borrower on one day and reported as their total, and it is read as a
flag. The borrower's ABA number is nine-character text.

Two checks that come with the workbooks. Each has an `interest rates` sheet with the primary,
secondary and seasonal rate for every day of the quarter, so every loan's rate is compared with
the rate its own workbook prints for that type on that day. And a workbook's name claims a
quarter, so a loan dated outside it is counted rather than trusted.

Disciplines: a workbook that does not open, or whose loan sheet lacks a wanted column, is
reported and not read; a row that is not a loan is counted and a sample of it printed; nothing
is fetched, deleted or overwritten here; the cache records each workbook's digest and the
question it was read under, and is re-read when either moves.

    python experiments/b113_dw_loans.py --scan
    python experiments/b113_dw_loans.py --build
    python experiments/b113_dw_loans.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_dw_lending as fetch  # noqa: E402

DW = ROOT / "data" / "b59" / "dw"
CACHE = ROOT / "data" / "cache" / "b113_dw_loans.json"

WANT = ("Loan date", "Maturity date", "Term", "Repayment date", "Lending Federal Reserve district",
        "Borrower", "Borrower city", "Borrower state", "Borrower ABA number", "Type of credit",
        "Interest rate", "Loan amount")
TYPES = {"Primary Credit": "primary", "Secondary Credit": "secondary", "Seasonal Credit": "seasonal"}
RATE_COLUMNS = {"primary credit": "primary", "secondary credit": "secondary", "seasonal credit": "seasonal"}
#: bumped whenever what a workbook is asked for changes, so a cached quarter is read again
VERSION = 1


def norm(x) -> str:
    return re.sub(r"\s+", " ", "" if x is None else str(x)).strip()


def collateral_name(h: str) -> str:
    h = re.sub(r"^Collateral, lendable value, by asset type\s*", "", h)
    return re.sub(r"\d+$", "", h).strip()


def serial_to_iso(v, datemode: int):
    import xlrd
    if isinstance(v, float) and v > 0:
        return xlrd.xldate.xldate_as_datetime(v, datemode).date().isoformat()
    return None


def read_workbook(path: Path):
    """({sheet: rows}, a function turning a date cell into an ISO date or None)."""
    if path.suffix == ".xls":
        import xlrd
        wb = xlrd.open_workbook(str(path))
        mode = wb.datemode
        return ({s.name: [s.row_values(i) for i in range(s.nrows)] for s in wb.sheets()},
                lambda v: serial_to_iso(v, mode))
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return ({ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets},
            lambda v: v.date().isoformat() if isinstance(v, datetime.datetime) else None)


def quarter_of(iso: str) -> str:
    return f"{iso[:4]}Q{(int(iso[5:7]) - 1) // 3 + 1}"


def parse(sheets: dict, to_date, quarter: str) -> dict:
    """One workbook's rows to loans, with everything that was not read counted."""
    found = None
    best = (None, None, [])
    for name, rows in sheets.items():
        for i, r in enumerate(rows[:15]):
            cells = [norm(x) for x in r]
            have = [w for w in WANT if w in cells]
            if len(have) > len(best[2]):
                best = (name, i, have)
            if len(have) == len(WANT):
                found = (name, i, cells)
                break
        if found:
            break
    if not found:
        return {"refused": "no row holds every wanted column",
                "best_sheet": best[0], "missing": [w for w in WANT if w not in best[2]]}
    sheet, hi, cells = found
    col = {}
    for j, h in enumerate(cells):
        col.setdefault(h, j)
    total = next((j for j, h in enumerate(cells) if collateral_name(h) == "Total collateral"), None)
    loans, other, unknown, padded, bad_aba, outside = [], [], collections.Counter(), 0, 0, 0
    for r in sheets[sheet][hi + 1:]:
        r = list(r) + [None] * (len(cells) - len(r))
        day = to_date(r[col["Loan date"]])
        if day is None:
            if any(x not in (None, "") for x in r):
                other.append(norm(next(x for x in r if x not in (None, "")))[:80])
            continue
        raw_type = norm(r[col["Type of credit"]])
        kind = TYPES.get(raw_type.rstrip("*").strip())
        if kind is None:
            unknown[raw_type] += 1
            continue
        a = r[col["Borrower ABA number"]]
        aba = str(int(a)) if isinstance(a, (int, float)) else norm(a)
        if not aba.isdigit():
            bad_aba += 1
            continue
        if len(aba) < 9:
            aba, padded = aba.zfill(9), padded + 1
        outside += quarter_of(day) != quarter
        loans.append({"date": day, "maturity": to_date(r[col["Maturity date"]]),
                      "repaid": to_date(r[col["Repayment date"]]),
                      "term": int(float(r[col["Term"]])) if r[col["Term"]] not in (None, "") else None,
                      "district": norm(r[col["Lending Federal Reserve district"]]),
                      "borrower": norm(r[col["Borrower"]]), "city": norm(r[col["Borrower city"]]),
                      "state": norm(r[col["Borrower state"]]), "aba": aba, "type": kind,
                      "aggregated": raw_type.endswith("*"), "rate": float(r[col["Interest rate"]]),
                      "amount": float(r[col["Loan amount"]]),
                      "collateral": (float(r[total]) if total is not None and r[total] not in (None, "") else None)})
    rates = {}
    for name, rows in sheets.items():
        if name == sheet:
            continue
        for i, r in enumerate(rows[:10]):
            cells2 = [norm(x).lower() for x in r]
            if all(k in cells2 for k in RATE_COLUMNS):
                at = {RATE_COLUMNS[k]: cells2.index(k) for k in RATE_COLUMNS}
                for rr in rows[i + 1:]:
                    d = to_date(rr[0]) if rr else None
                    if d is not None:
                        rates[d] = {k: float(rr[j]) for k, j in at.items() if rr[j] not in (None, "")}
                break
        if rates:
            break
    matched, mismatched, missing = 0, [], 0
    for ln in loans:
        want = rates.get(ln["date"], {}).get(ln["type"])
        if want is None:
            missing += 1
        elif abs(want - ln["rate"]) < 1e-9:
            matched += 1
        else:
            mismatched.append([ln["date"], ln["type"], ln["rate"], want])
    return {"loan_sheet": sheet, "header_row": hi, "loans": loans, "other_rows": len(other),
            "other_sample": other[:4], "unknown_types": dict(unknown), "aba_padded": padded,
            "aba_not_digits": bad_aba, "outside_quarter": outside, "rate_days": len(rates),
            "rate_matched": matched, "rate_mismatched": len(mismatched), "rate_missing": missing,
            "rate_mismatch_sample": mismatched[:5], "total_collateral_column": total is not None}


def signature() -> list:
    return [VERSION, list(WANT), sorted(TYPES)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(budget: float = 150.0, rebuild: bool = False, dw: Path = None, cache: Path = None, out=print) -> dict:
    dw, cache = dw or DW, cache or CACHE
    old = {}
    if cache.exists() and not rebuild:
        try:
            old = json.loads(cache.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
    got, t0 = dict(old), time.time()
    status = collections.Counter()
    for y, q in fetch.quarters():
        key, name = f"{y}Q{q}", fetch.name_of(y, q)
        path, kind = dw / name, name.rsplit(".", 1)[1]
        if not path.exists():
            status["not on disk"] += 1
            got.pop(key, None) if key not in old else None
            continue
        if not fetch.opens(path, kind):
            status["does not open"] += 1
            out(f"  {key} {name} does not open, not read")
            continue
        digest = sha256(path)
        if key in old and old[key].get("sha256") == digest and old[key].get("signature") == signature():
            status["reused"] += 1
            continue
        if time.time() - t0 > budget:
            status["left for the next run"] += 1
            continue
        try:
            sheets, to_date = read_workbook(path)
        except Exception as e:  # a workbook the reader cannot take is named, never skipped quietly
            status["could not be read"] += 1
            out(f"  {key} {name} could not be read: {type(e).__name__}: {e}")
            continue
        rec = parse(sheets, to_date, key)
        rec.update({"file": name, "sha256": digest, "signature": signature()})
        got[key] = rec
        status["read"] += 1
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(got, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(got, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    out(f"  {dict(status)}; cache {cache.name}: {len(got)} quarter(s), "
        f"{sum(len(v.get('loans', [])) for v in got.values()):,} loans")
    return {"status": dict(status), "quarters": got}


def scan(got: dict) -> None:
    print(f"{'quarter':7} {'sheet':<32} {'hdr':>3} {'loans':>6} {'other':>5} {'agg':>4} {'rate ok':>7} {'rate bad':>8} {'no rate':>7} {'outside':>7} {'padded':>6} unknown")
    for key in sorted(got):
        v = got[key]
        if "refused" in v:
            print(f"{key:7} REFUSED: {v['refused']}, missing {v['missing']}")
            continue
        agg = sum(1 for x in v["loans"] if x["aggregated"])
        print(f"{key:7} {v['loan_sheet']:<32} {v['header_row']:>3} {len(v['loans']):>6} {v['other_rows']:>5} {agg:>4} "
              f"{v['rate_matched']:>7} {v['rate_mismatched']:>8} {v['rate_missing']:>7} {v['outside_quarter']:>7} {v['aba_padded']:>6} {v['unknown_types'] or ''}")
    loans = [x for v in got.values() for x in v.get("loans", [])]
    print(f"\n  loans {len(loans):,}; by type {dict(collections.Counter(x['type'] for x in loans))}; "
          f"aggregated {sum(1 for x in loans if x['aggregated'])}; distinct ABA numbers {len({x['aba'] for x in loans}):,}")
    bad = [(k, v["rate_mismatch_sample"]) for k, v in sorted(got.items()) if v.get("rate_mismatched")]
    for k, s in bad[:6]:
        print(f"  rate mismatches in {k}: {s}")


def selftest() -> int:
    import tempfile
    import openpyxl
    fails = []

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    expect(serial_to_iso(40381.0, 0) == "2010-07-22" and serial_to_iso("", 0) is None,
           "an Excel serial number reads as its date under the workbook's own date system")
    head = list(WANT) + ["Other outstanding loans", "Total outstanding loans", "Total collateral1", "Commercial loans1"]
    D = datetime.datetime

    def workbook(path, loan_sheet="discount window loan data", header=head, loans=None, notes=True):
        wb = openpyxl.Workbook()
        ws0 = wb.active
        ws0.title = "definitions and notes"
        ws0.append(["DISCOUNT WINDOW LOAN DATA DEFINITIONS"])
        ws0.append([])
        for w in WANT:
            ws0.append([w, "description"])
        ws = wb.create_sheet(loan_sheet)
        ws.append(["DISCOUNT WINDOW LOAN DATA"])
        ws.append(["April 1, 2024, to June 30, 2024"])
        ws.append([])
        ws.append(header)
        for row in loans or []:
            ws.append(row)
        if notes:
            ws.append([])
            ws.append(["Note:  frequency is each loan, data as-of the loan origination date"])
            ws.append(["1. Collateral, lendable value, by asset type"])
        wr = wb.create_sheet("interest rates")
        wr.append(["DISCOUNT WINDOW LOAN INTEREST RATES"])
        wr.append([])
        wr.append([" ", "Primary credit", "Secondary credit", "Seasonal credit"])
        for d in range(1, 31):
            wr.append([D(2024, 4, d), 5.5, 6.0, 5.35])
        wb.save(path)

    def loan(day, typ, aba, rate, amount=1000.0):
        return [D(2024, 4, day), D(2024, 4, day + 1), 1, D(2024, 4, day + 1), "Boston (1)", "A BK", "TOWN", "ME",
                aba, typ, rate, amount, 0, amount, 5000.0, 5000.0]

    with tempfile.TemporaryDirectory() as tmp:
        T = Path(tmp)
        good = T / "dw_data_2024_q2.xlsx"
        workbook(good, loans=[loan(1, "Primary Credit", "022306847", 5.5),
                              loan(2, "Primary Credit*", 22306848, 5.5, 3000.0),
                              loan(3, "Seasonal Credit", "073911812", 5.35),
                              loan(4, "Secondary Credit", "021114111", 5.5),
                              [D(2024, 7, 1), D(2024, 7, 2), 1, D(2024, 7, 2), "Boston (1)", "B BK", "TOWN", "ME",
                               "011000015", "Primary Credit", 5.5, 1000.0, 0, 1000.0, 1.0, 1.0]])
        sheets, to_date = read_workbook(good)
        p = parse(sheets, to_date, "2024Q2")
        expect(p.get("loan_sheet") == "discount window loan data" and len(p["loans"]) == 5,
               "the loan sheet is the one whose row holds every wanted column, not the definitions "
               "sheet ahead of it that lists the same names down its first column")
        expect(p["other_rows"] == 2, "note rows after the loans are counted and not read as loans")
        l2 = p["loans"][1]
        expect(l2["type"] == "primary" and l2["aggregated"] and l2["amount"] == 3000.0
               and not p["loans"][0]["aggregated"],
               "a trailing star is read as the aggregated flag on the type it follows")
        expect(p["loans"][0]["aba"] == "022306847" and l2["aba"] == "022306848" and p["aba_padded"] == 1,
               "an ABA number keeps its leading zero, and one stored as a number is padded and counted")
        expect(p["loans"][0]["date"] == "2024-04-01" and p["loans"][0]["collateral"] == 5000.0
               and p["total_collateral_column"],
               "dates read as dates, and total collateral is found under its footnoted name")
        expect(p["rate_matched"] == 3 and p["rate_mismatched"] == 1 and p["rate_missing"] == 1
               and p["rate_mismatch_sample"][0][:3] == ["2024-04-04", "secondary", 5.5],
               "a loan whose rate is not its workbook's rate for its type on its day is counted, "
               "apart from one whose day the rate sheet does not print")
        expect(p["outside_quarter"] == 1, "a loan dated outside the quarter the workbook claims is counted")
        borrow = T / "b.xlsx"
        workbook(borrow, loan_sheet="discount window borrowing data", loans=[loan(1, "Primary Credit", "022306847", 5.5)])
        pb = parse(*read_workbook(borrow), "2024Q2")
        expect(pb.get("loan_sheet") == "discount window borrowing data" and len(pb["loans"]) == 1,
               "the 2012Q3 sheet name reads the same way")
        short = T / "s.xlsx"
        workbook(short, header=[h for h in head if h != "Borrower ABA number"],
                 loans=[loan(1, "Primary Credit", "022306847", 5.5)[:8] + loan(1, "Primary Credit", "022306847", 5.5)[9:]])
        ps = parse(*read_workbook(short), "2024Q2")
        expect(ps.get("refused") and ps["missing"] == ["Borrower ABA number"],
               "a loan sheet without a wanted column is refused, naming the column")
        odd = T / "o.xlsx"
        workbook(odd, loans=[loan(1, "Term Credit", "022306847", 5.5), loan(2, "Primary Credit", "02230684X", 5.5)])
        po = parse(*read_workbook(odd), "2024Q2")
        expect(po["unknown_types"] == {"Term Credit": 1} and po["aba_not_digits"] == 1 and not po["loans"],
               "an unknown type and an ABA that is not digits are counted and not read")

        dw = T / "dw"
        dw.mkdir()
        good.rename(dw / "dw_data_2024_q2.xlsx")
        cache = T / "cache.json"
        log = []
        r1 = build(dw=dw, cache=cache, out=log.append)
        r2 = build(dw=dw, cache=cache, out=log.append)
        expect(r1["status"].get("read") == 1 and r2["status"].get("reused") == 1,
               "a workbook read once is reused while its digest and the question are unchanged")
        global VERSION
        saved = VERSION
        VERSION = saved + 1
        try:
            r3 = build(dw=dw, cache=cache, out=log.append)
        finally:
            VERSION = saved
        expect(r3["status"].get("read") == 1, "and read again when the question changes")
        (dw / "dw_data_2024_q1.xlsx").write_bytes(b"PK\x03\x04 cut short")
        r4 = build(dw=dw, cache=cache, out=log.append)
        expect(r4["status"].get("does not open") == 1 and "2024Q1" not in r4["quarters"],
               "a workbook that does not open is reported and not read")
    if fails:
        print("\n  selftest FAILED")
        return 1
    print("\n  selftest passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true", help="read the workbooks into the cache")
    ap.add_argument("--rebuild", action="store_true", help="with --build, read every workbook again")
    ap.add_argument("--scan", action="store_true", help="print what the cache holds, per quarter")
    ap.add_argument("--budget", type=float, default=150.0, help="seconds of reading before a build stops")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.build:
        build(a.budget, a.rebuild)
        return 0
    if a.scan:
        scan(json.loads(CACHE.read_text(encoding="utf-8")))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
