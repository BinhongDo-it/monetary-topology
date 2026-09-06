"""B34 step 2: pull the numbers out of ASHE Table 6.6a and 6.6b, and stop.

Step 0 found the workbooks. This step reads them and writes a tidy record. It
computes no difference and judges nothing. The difference-in-differences and
the verdict are step 3, so that the numbers can be audited before anything is
concluded from them.

Two disciplines are visible in the code rather than assumed:

  * The column headers are DISCOVERED and PRINTED, not hard coded. Step 0 was
    written expecting sub-table 6.5a or 6.7a and the answer was 6.6a; the same
    caution applies to which column holds the tenth percentile.
  * Every age group and every statistic in the sheet is extracted, not only the
    registered ones. B34_design section 8.3 registers which cells carry the
    verdict; this file holds all of them so the record is complete.

Usage
-----
    python b34_step2_extract.py --src D:/data/raw
    python b34_step2_extract.py --src D:/data/raw --sheet All --years 2015 2017

Writes results/b34_ashe_cells.csv and results/b34_ashe_cells.json. Deletes
nothing, unpacks nothing to disk.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path

HOURLY = re.compile(r"hourly", re.I)
EXCL = re.compile(r"exclud\w*\s+overtime", re.I)
IS_CV = re.compile(r"coefficient", re.I)

AGELAB = re.compile(r"^\s*(\d{2}\s*-\s*\d{2}|\d{2}\s*\+|All employees)\s*$")
YEAR = re.compile(r"(20\d{2}|19\d{2})")

def read_sheets(data: bytes, name: str):
    """Yield (sheet_name, rows) for one workbook held in memory."""
    bio = io.BytesIO(data)
    low = name.lower()
    if low.endswith((".xlsx", ".xlsm")):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("openpyxl needed for .xlsx: pip install openpyxl")
        wb = openpyxl.load_workbook(bio, read_only=True, data_only=True)
        for ws in wb.worksheets:
            yield ws.title, [r for r in ws.iter_rows(values_only=True)]
        wb.close()
    elif low.endswith(".xls"):
        try:
            import xlrd
        except ImportError:
            raise SystemExit("xlrd is needed for .xls: pip install 'xlrd<2'")
        book = xlrd.open_workbook(file_contents=data)
        for sh in book.sheets():
            yield sh.name, [sh.row_values(r) for r in range(sh.nrows)]


def title_of(rows):
    """The first non empty cell in the sheet, which is where ONS puts titles."""
    for row in rows[:12]:
        for cell in row:
            if isinstance(cell, str) and cell.strip():
                return cell.strip()
    return ""


# Column labels are built by stacking every non empty header cell above the
# first data row, because the ASHE header spans more than one row: a merged
# "Percentiles" banner sits above the bare numbers 10, 20, 25 and so on. The
# first version of this file picked the single row with the most matches, hit
# the row holding Median and Mean, and returned those two silently. It did not
# error. A detector that returns a subset without complaining is worse than one
# that crashes, so the derived label for every column is now printed.
NUMSTAT = {"10", "20", "25", "30", "40", "60", "70", "75", "80", "90"}


def norm_cell(v):
    """A header cell as text. 10.0 and '10 ' both become '10'."""
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def first_data_row(rows):
    """Index of the first row carrying an age group label in its left columns."""
    for i, row in enumerate(rows):
        for cell in row[:3]:
            if AGELAB.match(norm_cell(cell)):
                return i
    return None


def column_labels(rows, fdr):
    """{col_index: label} built by stacking the header cells above row fdr."""
    ncol = max((len(r) for r in rows[:fdr + 2]), default=0)
    out = {}
    for j in range(ncol):
        parts = []
        for i in range(min(fdr, len(rows))):
            row = rows[i]
            if j >= len(row):
                continue
            t = norm_cell(row[j])
            if t and t not in parts:
                parts.append(t)
        if parts:
            out[j] = " ".join(parts)
    return out


def classify(label):
    """Map a stacked column label to a statistic name, or None to skip it."""
    low = label.lower()
    if "number of jobs" in low:
        return "N"
    if "median" in low:
        return "Median"
    if "mean" in low:
        return "Mean"
    toks = [t for t in re.split(r"[^\d]+", label) if t]
    for t in toks:
        if t in NUMSTAT:
            return t
    return None


def to_num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s or s in ("x", "..", ":", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--sheet", default="All",
                    help="which sheet to extract; design section 8.3 registers All")
    ap.add_argument("--years", nargs="*", default=None,
                    help="restrict to these years; default every zip found")
    ap.add_argument("--dump-head", action="store_true",
                    help="print the header rows verbatim, cell by cell")
    args = ap.parse_args()

    out_dir = (Path(args.out) if args.out
               else Path(__file__).resolve().parent.parent / "results")
    out_dir.mkdir(parents=True, exist_ok=True)

    zips = sorted(p for p in Path(args.src).iterdir() if p.suffix.lower() == ".zip")
    if not zips:
        raise SystemExit("no .zip files in %s" % args.src)

    rows_out = []
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if not m.lower().endswith((".xls", ".xlsx", ".xlsm")):
                    continue
                data = zf.read(m)
                for sheet, rows in read_sheets(data, m):
                    if sheet != args.sheet:
                        continue
                    t = title_of(rows)
                    if not (HOURLY.search(t) and EXCL.search(t)):
                        continue
                    ym = YEAR.search(Path(m).name)
                    year = ym.group(1) if ym else None
                    if args.years and year not in args.years:
                        continue
                    kind = "cv" if IS_CV.search(t) else "value"
                    fdr = first_data_row(rows)
                    print("-" * 74)
                    print("%s | sheet=%s | year=%s | kind=%s" %
                          (Path(m).name[:52], sheet, year, kind))
                    if fdr is None:
                        print("  NO AGE LABEL FOUND; nothing extracted.")
                        continue
                    raw = column_labels(rows, fdr)
                    header = {}
                    for j, lab in sorted(raw.items()):
                        st = classify(lab)
                        print("    col %-3d %-46s -> %s" % (j, lab[:46], st or "skip"))
                        if st:
                            header[j] = st
                    if args.dump_head:
                        for i in range(min(fdr + 2, len(rows))):
                            cells = [(c, norm_cell(v)) for c, v in enumerate(rows[i])
                                     if norm_cell(v)]
                            print("    r%-3d %s" % (i, " | ".join("%d:%s" % x
                                                                 for x in cells)[:200]))
                    if not header:
                        print("  NO STATISTIC COLUMNS RECOGNISED. Nothing extracted.")
                        continue
                    got = 0
                    for row in rows[fdr:]:
                        lab = None
                        for cell in row[:3]:
                            t = norm_cell(cell)
                            if AGELAB.match(t):
                                lab = t
                                break
                        if lab is None:
                            continue
                        for j, stat in header.items():
                            if j >= len(row):
                                continue
                            v = to_num(row[j])
                            if v is None:
                                continue
                            rows_out.append({"year": year, "sheet": sheet,
                                             "kind": kind, "agegroup": lab,
                                             "stat": stat, "value": v,
                                             "workbook": Path(m).name})
                            got += 1
                    print("  extracted %d cells across %s" %
                          (got, ", ".join(sorted({r["agegroup"] for r in rows_out
                                                  if r["workbook"] == Path(m).name}))))

    if not rows_out:
        raise SystemExit("nothing extracted; re-read the header lines printed above")

    cpath = out_dir / "b34_ashe_cells.csv"
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "sheet", "kind", "agegroup",
                                          "stat", "value", "workbook"])
        w.writeheader()
        for r in sorted(rows_out, key=lambda d: (d["year"] or "", d["kind"],
                                                 d["agegroup"], str(d["stat"]))):
            w.writerow(r)
    jpath = out_dir / "b34_ashe_cells.json"
    jpath.write_text(json.dumps(rows_out, ensure_ascii=False, indent=2,
                               sort_keys=True), encoding="utf-8")

    print()
    print("=" * 74)
    print("The registered cells, printed so they can be read before step 3")
    print("design section 8.3: sheet All, 2015 and 2017, groups 18-21 / 22-29 /")
    print("30-39, percentiles 10 and 20 carry the verdict, 60 70 80 are placebo")
    print("=" * 74)
    idx = {}
    for r in rows_out:
        idx[(r["year"], r["kind"], r["agegroup"], str(r["stat"]))] = r["value"]
    groups = ["18-21", "22-29", "30-39"]
    stats = ["10", "20", "60", "70", "80", "Median"]
    years = sorted({r["year"] for r in rows_out if r["year"]})
    for g in groups:
        print("\ngroup %s" % g)
        print("  %-8s %s" % ("stat", "  ".join("%10s" % ("%s val" % y) for y in years)
                             + "  " + "  ".join("%10s" % ("%s cv" % y) for y in years)))
        for st in stats:
            vals = ["%10s" % _fmt(idx.get((y, "value", g, st))) for y in years]
            cvs = ["%10s" % _fmt(idx.get((y, "cv", g, st))) for y in years]
            print("  %-8s %s  %s" % (st, "  ".join(vals), "  ".join(cvs)))

    print()
    print("written: %s" % cpath)
    print("         %s" % jpath)
    print("Step 2 ends here. No difference has been taken, nothing is judged.")


def _fmt(v):
    return "-" if v is None else ("%.4f" % v if abs(v) < 100 else "%.1f" % v)


if __name__ == "__main__":
    sys.exit(main())
