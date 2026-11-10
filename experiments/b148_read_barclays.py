"""Read the Barclays core-range customer rate sheet (PDF) into rows for B148. Run with ``python -I``.

The PDF is untrusted data: this script only reads it with pymupdf (text and table geometry)
and writes one JSON file. Nothing in the PDF is executed, followed or opened elsewhere.

Two extraction paths, kept apart so they can be compared row by row (B148-1-Barclays):
  table  pymupdf ``find_tables``: one row per table row, nine columns as the sheet prints them
  text   ``get_text("text")``: the same rows rebuilt from the line stream, a row being a block
         that starts at a product name and ends at its "... APRC" cell

Every table row carries its page and its row number in that page's table (rule 25), and the
coverage table lists every page of the PDF, pages with zero rate rows included.

    python -I -B experiments/b148_read_barclays.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "raw" / "b148" / "barclays"
MANIFEST = DEST / "barclays_manifest.json"
OUT = DEST / "barclays_rows.json"
COLS = ["Product Type", "Initial Interest Rate", "Product Fee", "LTV", "Minimum/Maximum Loan Size",
        "Product/ ERC end date", "Early Repayment Charge", "Follow On Rate", "Overall Cost for Comparison"]
RE_RATE = re.compile(r"^\d\.\d\d%$")
RULE_WORDS = re.compile(r"lower than|higher than|discount|same as|reduction|below|less than|more than|"
                        r"cheaper|premium of|in addition to", re.I)


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def table_rows(doc) -> tuple[list[dict], list[dict], list[str]]:
    rows, cover, headers = [], [], []
    for pno in range(doc.page_count):
        page = doc[pno]
        n_tables, n_rate, n_cols, heads = 0, 0, 0, []
        heading = None
        for ti, t in enumerate(page.find_tables().tables):
            n_tables += 1
            for ri, r in enumerate(t.extract()):
                cells = [norm(c) for c in r] + [""] * (9 - len(r))
                if cells[0] == "Product Type":
                    n_cols += 1
                    headers.append(f"p{pno + 1} r{ri}: " + " | ".join(cells[:9]))
                    continue
                if r[1] is None or not RE_RATE.match(cells[1]):
                    if cells[0]:
                        heading = cells[0]
                        heads.append(f"r{ri}: {cells[0][:160]}")
                    continue
                n_rate += 1
                rows.append({"page": pno + 1, "table": ti, "row": ri, "heading": heading,
                             "cells": dict(zip(COLS, cells[:9]))})
        cover.append({"page": pno + 1, "opened": True, "tables": n_tables, "column_header_rows": n_cols,
                      "rate_rows": n_rate, "headings": heads})
    return rows, cover, headers


def text_rows(doc) -> list[dict]:
    """Rows rebuilt from the plain line stream: a product line, then rate, fee, LTV (one or two lines),
    loan size, end date, ERC, follow-on (two lines) and an APRC line."""
    out = []
    for pno in range(doc.page_count):
        lines = [norm(x) for x in doc[pno].get_text("text").splitlines()]
        lines = [x for x in lines if x]
        i = 0
        while i < len(lines):
            j = i + 1
            name = lines[i]
            # product names may wrap onto a "+0.92%" margin line
            if j < len(lines) and re.match(r"^\+\d\.\d\d%$", lines[j]):
                name += " " + lines[j]
                j += 1
            if j + 3 < len(lines) and RE_RATE.match(lines[j]) and lines[j + 1].startswith("£"):
                rate, fee = lines[j], lines[j + 1]
                k = j + 2
                ltv = lines[k]
                if ltv.startswith("Over"):
                    ltv = ltv + " " + lines[k + 1]
                    k += 1
                loan = lines[k + 1]
                end = lines[k + 2]
                out.append({"page": pno + 1, "product": name, "rate": rate, "fee": fee, "ltv": ltv,
                            "loan": loan, "end": end})
                i = k + 3
                continue
            i += 1
    return out


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    v = man["versions"][-1]
    pdf = DEST / v["file"]
    body = pdf.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    if sha != v["sha256"] or len(body) != v["bytes"]:
        print(f"PDF on disk does not match its manifest: {len(body)} B sha {sha}")
        return 1
    doc = pymupdf.open(stream=body, filetype="pdf")
    trows, cover, headers = table_rows(doc)
    xrows = text_rows(doc)
    full = "\n".join(doc[p].get_text("text") for p in range(doc.page_count))
    rule_lines = [norm(x) for x in full.splitlines() if RULE_WORDS.search(x)]
    m_eff = re.search(r"Rates effective from ([0-9]{1,2} [A-Z][a-z]+ [0-9]{4})", full)
    m_bebr = re.search(r"BEBR is currently (\d\.\d\d)%", full)
    rep = re.search(r"Representative example:\s*(.+?APRC representative\.)", full, re.S)
    out = {
        "source": {"file": v["file"], "bytes": len(body), "sha256": sha, "pages": doc.page_count,
                   "pdf_creation_date": doc.metadata.get("creationDate"),
                   "rates_effective": m_eff.group(1) if m_eff else None,
                   "bebr_printed": m_bebr.group(1) if m_bebr else None},
        "column_header_rows": headers,
        "coverage": cover,
        "rows": trows,
        "text_path_rows": xrows,
        "rule_sentence_candidates": rule_lines,
        "representative_example": norm(rep.group(1)) if rep else None,
        "read_with": "pymupdf find_tables and get_text, python -I",
    }
    fd, tmp = tempfile.mkstemp(dir=DEST, prefix="rows.", suffix=".tmp.expired")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, sort_keys=True, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, OUT)
    print(f"pages {doc.page_count}; table rows {len(trows)}; text-path rows {len(xrows)}; "
          f"rate rows per page {[c['rate_rows'] for c in cover]}; effective {out['source']['rates_effective']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
