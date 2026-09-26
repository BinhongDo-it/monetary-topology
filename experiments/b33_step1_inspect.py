"""B33 step one: describe the table before scoring anything on it.

Discipline 13 says量最坏那一格 and describe the object before jumping to a test,
and criterion-shape rule 11 says print the object rather than a count. This step
does exactly that and nothing else: it opens the workbook, prints the sheets, and
prints every cell that looks like a marital-status label, so the layout is read by
a person before a parser is written against it.

It scores nothing and writes no record.

    python experiments/b33_step1_inspect.py
    python experiments/b33_step1_inspect.py --rows 40
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "b33"

# The five statuses as the code writes them, plus the words a table stub is
# likely to use for each. "surviving" is the one this cut turns on.
# Substrings, chosen so a plural or a reordering still matches. The first
# version of this list wrote "head of household" and the table says "heads of
# households", so that block was missed: a sentinel that cannot see a plural is
# not watching for that block at all.
LABELS = ["surviving", "widow", "joint", "married", "separate",
          "head", "single", "all returns", "total"]
MAGIC = (b"\xd0\xcf\x11\xe0", b"PK\x03\x04")


def check(path):
    with path.open("rb") as f:
        h = f.read(8)
    return any(h.startswith(m) for m in MAGIC)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=25)
    ap.add_argument("--cols", type=int, default=14)
    args = ap.parse_args()

    try:
        import pandas as pd
    except ImportError:
        print("pandas is not importable here. Activate the virtual environment "
              "first, then re-run.")
        return 1

    files = sorted(p for p in SRC.glob("*.xls*") if ".expired" not in p.name)
    if not files:
        print("nothing in %s yet. Run b33_step0_fetch_soi.py first." % SRC)
        return 1

    for path in files:
        print("=" * 78)
        print(path.name, "%d bytes" % path.stat().st_size)
        if not check(path):
            print("  NOT A WORKBOOK. Refusing to parse it. Re-fetch.")
            continue
        try:
            book = pd.ExcelFile(path)
        except Exception as e:
            print("  could not open: %s %s" % (type(e).__name__, e))
            continue
        print("  sheets: %s" % ", ".join(map(str, book.sheet_names)))

        for sheet in book.sheet_names:
            df = book.parse(sheet, header=None, nrows=args.rows)
            print("\n  --- sheet %r, first %d rows x %d cols ---"
                  % (sheet, min(args.rows, len(df)), min(args.cols, df.shape[1])))
            for i in range(min(args.rows, len(df))):
                cells = []
                for j in range(min(args.cols, df.shape[1])):
                    v = df.iat[i, j]
                    s = "" if v is None or (isinstance(v, float) and v != v) else str(v)
                    cells.append(s.replace("\n", " ")[:22])
                if any(cells):
                    print("   r%-3d | %s" % (i, " | ".join(cells)))

            # Every cell anywhere on the sheet that names a status, with its
            # address, so the block structure is visible rather than guessed.
            full = book.parse(sheet, header=None)
            hits = []
            for i in range(full.shape[0]):
                for j in range(full.shape[1]):
                    v = full.iat[i, j]
                    if not isinstance(v, str):
                        continue
                    low = v.lower()
                    for lab in LABELS:
                        if lab in low:
                            hits.append((i, j, lab, re.sub(r"\s+", " ", v)[:70]))
                            break
            print("\n  status-like cells on sheet %r: %d" % (sheet, len(hits)))
            for i, j, lab, v in hits[:60]:
                print("   (r%d,c%d) [%s] %s" % (i, j, lab, v))
            if len(hits) > 60:
                print("   ... %d more" % (len(hits) - 60))
            print("  sheet shape: %d rows x %d cols" % full.shape)

    print("\nNothing was scored and no record was written. Paste this output back "
          "and the parser gets written against the real layout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
