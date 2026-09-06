"""Extract the two price legs from the DAI China spreadsheet PDF.

  domestic leg  template row 20, Pw, wholesale price for the primary good in
                the rural area, LC/MT
  border leg    template row 37 (cif import price Pm) in a year flagged M,
                template row 38 (fob export price Px) in a year flagged X,
                both US$/MT
  trade flag    template row 2

Rows are located by `dai_grid`, which fits the printed row lattice on each page
and checks it against value anchors that are independently known. The earlier
approach, keying rows off the numbered legend pages, is superseded: applying
legend p177 to data page p195 put that page's crop area on template row 2.20,
and the resulting one-row slip read cotton's wholesale price off the row above,
producing 3340 where the sheet says 3381. That file is kept with an .expired
suffix.

Only row 20 is accepted as the domestic leg. Some sheets leave it n.a. and
carry a farm-gate price at row 128 instead; substituting it would put two
different points of the marketing chain into one square, which is the sixth
category error, so those blocks are reported without a domestic leg rather
than filled in.

This writes a table. It scores no criterion and applies no threshold.
"""
import argparse
import json
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dai_grid as G                                    # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "dai"
PDF = ROOT / "dai_china_wp29.pdf"
OUT = ROOT / "dai_china_legs.json"

ROW_FLAG, ROW_PW, ROW_PM, ROW_PX = 2, 20, 37, 38


def run(only=None):
    blocks, refused = [], []
    with pdfplumber.open(PDF) as pdf:
        for i, page in enumerate(pdf.pages):
            if only and i not in only:
                continue
            rows = G.page_rows(page)
            centres = G.year_columns(rows)
            if not centres:
                continue
            row_of, checks = G.fit(rows, centres)
            if row_of is None:
                refused.append({"page": i, **checks})
                continue
            years = [y for y, _ in centres]
            flag = G.read(rows, centres, row_of, ROW_FLAG)
            pw = {y: G.as_float(v) for y, v in
                  G.read(rows, centres, row_of, ROW_PW).items()}
            pm = {y: G.as_float(v) for y, v in
                  G.read(rows, centres, row_of, ROW_PM).items()}
            px = {y: G.as_float(v) for y, v in
                  G.read(rows, centres, row_of, ROW_PX).items()}
            rate_y, _ = G.find_rate_row(rows, centres)
            rate = {}
            if rate_y is not None:
                rate = {y: G.as_float(v)
                        for y, v in G.values(dict(rows)[rate_y], centres).items()}
            legs = {}
            for y in years:
                f = flag.get(y)
                f = f if f in ("M", "X", "H", "HM", "HX") else None
                if f is None:
                    a, b = pm.get(y), px.get(y)
                    f = "M" if (a and not b) else "X" if (b and not a) else None
                legs[y] = {"flag": f,
                           "Pw_LC_per_MT": pw.get(y),
                           "border_USD_per_MT": pm.get(y) if f == "M"
                                                else px.get(y) if f == "X" else None,
                           "border_from": "Pm(37)" if f == "M"
                                          else "Px(38)" if f == "X" else None,
                           "official_rate": rate.get(y)}
            blocks.append({"page": i, "years": years, "grid": checks, "legs": legs})
    return blocks, refused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    a = ap.parse_args()
    only = {int(x) for x in a.pages.split(",") if x.strip()} or None
    blocks, refused = run(only)
    usable = [b for b in blocks
              if any(v["Pw_LC_per_MT"] and v["border_USD_per_MT"]
                     for v in b["legs"].values())]
    print(f"pages with a year header: {len(blocks) + len(refused)}   "
          f"grid fitted: {len(blocks)}   with both legs: {len(usable)}   "
          f"refused: {len(refused)}")
    for b in usable:
        n = sum(1 for v in b["legs"].values()
                if v["Pw_LC_per_MT"] and v["border_USD_per_MT"])
        g = b["grid"]
        print(f"  p{b['page']:4d} {b['years'][0]}-{b['years'][-1]}  both legs "
              f"{n}/{len(b['years'])}  pitch {g['pitch']}  anchors {g['value_anchors']}"
              f"  integral {g['integral_fraction']:.0%}")
    if not only:
        OUT.write_text(json.dumps({"blocks": blocks, "refused": refused},
                                  indent=2, sort_keys=True), encoding="utf-8",
                       newline="\n")
        print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
