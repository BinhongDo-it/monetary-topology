"""B34 step 0: open the ASHE Table 6 zips and print what is actually in them.

This runs before any arithmetic. It answers three questions by printing objects
rather than counts, which is the only kind of check that has ever paid in this
repository:

  1. Which sub-table inside Table 6 is hourly pay excluding overtime. The
     numbering is not guessed; every sheet's own title line is printed.
  2. What age group labels each year uses, verbatim.
  3. Whether those labels are identical across the years supplied. Arm five in
     B34_design section 7 requires a group whose own boundaries did not move
     while a statutory boundary moved across it. If a year's labels differ, that
     year leaves the arm; the groups are never spliced.

Nothing is computed, nothing is judged, nothing is deleted.

Usage
-----
    python b34_step0_ashe_index.py --src D:/data/ashe_table6
    python b34_step0_ashe_index.py --src D:/data/ashe_table6 --dump-titles

The --src directory holds the zips downloaded from the ONS Table 6 page, for
example table62015revised.zip. Zips are read in memory; nothing is unpacked to
disk.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path

# A sheet is a candidate when its title line says hourly and says excluding
# overtime. Both halves are required; "hourly pay - gross" is a different
# measure and the minimum wage is set on the excluding-overtime one.
HOURLY = re.compile(r"hourly", re.I)
EXCL = re.compile(r"exclud\w*\s+overtime", re.I)

# Age group labels look like "16-17", "18-21", "22-29", "60+", "All".
AGELAB = re.compile(r"^\s*(\d{2}\s*-\s*\d{2}|\d{2}\s*\+|[Aa]ll\b.*)\s*$")


def read_sheets(data: bytes, name: str):
    """Yield (sheet_name, rows) for one workbook held in memory."""
    bio = io.BytesIO(data)
    low = name.lower()
    if low.endswith(".xlsx") or low.endswith(".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("openpyxl needed for .xlsx: pip install openpyxl")
        wb = openpyxl.load_workbook(bio, read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                rows.append(row)
                if i > 60:
                    break
            yield ws.title, rows
        wb.close()
    elif low.endswith(".xls"):
        try:
            import xlrd
        except ImportError:
            raise SystemExit(
                "xlrd is needed for the older .xls files: pip install 'xlrd<2'"
            )
        book = xlrd.open_workbook(file_contents=data)
        for sh in book.sheets():
            rows = [sh.row_values(r) for r in range(min(sh.nrows, 61))]
            yield sh.name, rows
    else:
        return


def title_of(rows):
    """The first non-empty cell in the sheet, which is where ONS puts titles."""
    for row in rows[:12]:
        for cell in row:
            if isinstance(cell, str) and cell.strip():
                return cell.strip()
    return ""


def age_labels(rows):
    """Every distinct label in the sheet that looks like an age group."""
    out = []
    for row in rows:
        for cell in row:
            if isinstance(cell, str):
                m = AGELAB.match(cell)
                if m and cell.strip() not in out:
                    out.append(cell.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="directory holding the Table 6 zips")
    ap.add_argument("--out", default=None,
                    help="where to write the record; default ../results")
    ap.add_argument("--dump-titles", action="store_true",
                    help="print every sheet title, not only the hourly ones")
    args = ap.parse_args()

    zips = sorted(p for p in Path(args.src).iterdir()
                  if p.suffix.lower() == ".zip")
    if not zips:
        raise SystemExit("no .zip files in %s" % args.src)

    out_dir = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    # record[zip][workbook] = {"sheets": [...], "title": str, "labels": [...]}
    record = {}

    for z in zips:
        books = {}
        with zipfile.ZipFile(z) as zf:
            members = [m for m in zf.namelist()
                       if m.lower().endswith((".xls", ".xlsx", ".xlsm"))]
            for m in members:
                data = zf.read(m)
                for sheet, rows in read_sheets(data, m):
                    t = title_of(rows)
                    if args.dump_titles:
                        print("  %-40s %-22s %s" % (Path(m).name[:40], sheet, t[:80]))
                    if not (HOURLY.search(t) and EXCL.search(t)):
                        continue
                    b = books.setdefault(m, {"title": t, "sheets": [], "labels": []})
                    b["sheets"].append(sheet)
                    for lab in age_labels(rows):
                        if lab not in b["labels"]:
                            b["labels"].append(lab)
        record[z.name] = books
        # One line per workbook, not one per sheet. That was the noise.
        print("%s" % z.name)
        for m, b in sorted(books.items()):
            print("   %-58s sheets=%d" % (Path(m).name[:58], len(b["sheets"])))
            print("      labels: %s" % ", ".join(b["labels"]))

    print()
    print("=" * 74)
    print("section 7.5 check: are the age group labels the same every year")
    print("=" * 74)
    sets = {}
    for zname, books in record.items():
        labs = tuple(sorted({l for b in books.values() for l in b["labels"]}))
        sets[zname] = labs
        print("  %-32s %s" % (zname, ", ".join(labs) if labs else "NONE"))
    distinct = {v for v in sets.values() if v}
    same = len(distinct) == 1
    print()
    if not sets or not distinct:
        verdict = "NO MATCH"
        print("No sheet matched both 'hourly' and 'excluding overtime'. Re-run with")
        print("--dump-titles and read the titles. Do not guess a sub-table number.")
    elif same:
        verdict = "SAME"
        print("SAME across every zip supplied. Arm five stands.")
    else:
        verdict = "DIFFER"
        print("NOT THE SAME. A year whose labels differ leaves the arm; groups are")
        print("never spliced to make a series.")

    stamp = {"verdict": verdict,
             "zips": {k: {"workbooks": {Path(m).name: {"title": b["title"],
                                                       "sheets": b["sheets"],
                                                       "labels": b["labels"]}
                                        for m, b in v.items()}}
                      for k, v in record.items()},
             "labels_by_zip": {k: list(v) for k, v in sets.items()}}
    jpath = out_dir / "b34_ashe_index.json"
    jpath.write_text(json.dumps(stamp, ensure_ascii=False, indent=2, sort_keys=True),
                     encoding="utf-8")

    lines = ["# B34 step 0: what is inside the ASHE Table 6 zips", "",
             "Verdict on the section 7.5 check: **%s**" % verdict, "",
             "| zip | workbook | sheets | age group labels |", "|---|---|---|---|"]
    for zname in sorted(record):
        for m, b in sorted(record[zname].items()):
            lines.append("| %s | %s | %d | %s |" % (zname, Path(m).name,
                                                    len(b["sheets"]),
                                                    ", ".join(b["labels"])))
    lines += ["", "Sheets present in each workbook (identical across workbooks",
              "unless stated):", ""]
    seen = set()
    for zname in sorted(record):
        for m, b in sorted(record[zname].items()):
            key = tuple(b["sheets"])
            if key in seen:
                continue
            seen.add(key)
            lines.append("- %s" % ", ".join(b["sheets"]))
    mpath = out_dir / "b34_ashe_index.md"
    mpath.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print()
    print("record written:")
    print("   %s" % jpath)
    print("   %s" % mpath)
    print("Step 0 ends here. Nothing has been computed.")


if __name__ == "__main__":
    sys.exit(main())
