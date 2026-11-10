# -*- coding: utf-8 -*-
"""Write data/b139_dated_statements.json: dated statements on the Mexican dollar and the koban at the
Japanese treaty ports, July 1859 to December 1861 (station B139).

The working table sits beside the fetched sources, at data/raw/b139/yokohama/yokohama_dated_prices.tsv. It
is built there from the transcriptions of each group of sources, which stay on the machine that fetched
them; data/SOURCES.md says where every source is. This script copies the table into the one file the
repository carries: each row with its own source line, the way its figure was read, and the holder it
applies to. Nothing is fetched here.

    python data/build_b139_dated_statements.py

Two things are changed in the source lines on the way. The royal style in the titles of British official
papers is abbreviated to H.M., and a remark on which pages of one document had been opened earlier is
dropped, since it describes the order of work and not the source.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "raw" / "b139" / "yokohama" / "yokohama_dated_prices.tsv"
OUT = HERE / "b139_dated_statements.json"

STYLE = re.compile("Her (Britannic )?M" + "ajesty's")  # the long form of H.M. and H.B.M. in titles
WORK_REMARK = re.compile(r"; p\.56-61 were read by the earlier reader")

KINDS = {
    "custom": "ichibu per 100 dollars at the custom house or government counter, for the holders it changed for",
    "treasury_jp": "ichibu per 100 dollars the Treasury or mint gave Japanese holders",
    "street": "ichibu per 100 dollars between merchants or at money changers",
    "posted": "ichibu per 100 dollars on a notice put up by the custom house as the rate of the day",
    "duty": "ichibu per 100 dollars at which the custom house took dollars paid in for duties; 0 where the "
            "statement names no figure",
    "koban": "ichibu per koban at the port, paid by foreigners",
    "koban_jp": "ichibu per koban among Japanese holders, or by decree",
    "cost": "dollars per koban paid at the port",
    "abroad": "dollars per koban at Shanghai",
    "abroad_tael": "Shanghai taels per koban",
    "abroad_fl": "Dutch guilders per koban (Shanghai valuation or Batavia sale)",
    "lot": "one lot of coin bought at the port (low) and sold in China (high), dollars per piece",
    "ship": "a shipment with cost (low) and proceeds (high) in dollars",
    "quota": "dollars per head per day at the custom house (low, high); the wording is in the note",
    "walk": "a statement that a class of holders walked the gap; no figure coded",
    "stated": "the multiple of the ring as an observer states it",
    "dollar_tael": "Shanghai taels per Mexican dollar (a discount of d per cent is 1 - d/100)",
    "sovereign_tael": "Shanghai taels per sovereign",
    "flow": "dollars carried between Shanghai and Japan",
    "other": "a dated statement on money at the port that enters no reading",
}
PORTS = {"Y": "Yokohama, with Kanagawa and Edo", "N": "Nagasaki", "H": "Hakodate", "S": "Shanghai",
         "B": "Batavia", "C": "Canton"}
HOW = {
    "image": "the figure was read on a page image of the source",
    "text": "read in OCR text or in a library's transcription only",
    "ledger": "a firm's books, as McMaster (1960, 1962) prints them",
    "study": "a later compilation or a modern study: printed here, entering no reading",
}
LEVEL = {
    "": "a source of the time",
    "later compilation": "the source is a later compilation or a modern study, however its figure was read: "
                         "printed here, entering no reading",
}
BASIS = {
    "": "not a Shanghai rate",
    "cash quotation": "the coin quoted in taels",
    "bill on Hongkong": "the discount on a bank's bills payable in Hongkong in dollars, turned as 1 - d/100: the "
                        "price of a bill, which carries the remittance as well as the coin",
    "booked in an account": "the rate at which an account turns a sum; the day of the conversion is not stated",
}


def number(s):
    return float(s) if "." in s else int(s)


def clean(s):
    return WORK_REMARK.sub("", STYLE.sub(lambda m: "H.B.M." if m.group(1) else "H.M.", s))


def main():
    rows = []
    with SRC.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if (r["kind"] not in KINDS or r["port"] not in PORTS or r["how"] not in HOW
                    or r["level"] not in LEVEL or r["basis"] not in BASIS):
                raise SystemExit("a value outside the legend: %s" % r)
            if (r["kind"] in ("dollar_tael", "sovereign_tael")) != bool(r["basis"]):
                raise SystemExit("a Shanghai rate without its basis, or a basis on another row: %s" % r)
            rows.append({"date_from": r["date_from"], "date_to": r["date_to"], "port": r["port"],
                         "kind": r["kind"], "low": number(r["low"]), "high": number(r["high"]),
                         "coin": r["coin"], "holder": clean(r["holder"]), "how": r["how"],
                         "level": r["level"], "basis": r["basis"],
                         "note": clean(r["note"]), "source": clean(r["source"]), "ref": r["ref"]})
    doc = {
        "station": "B139",
        "what": "Dated statements of what a Mexican dollar fetched in ichibu, of the price of the koban, and of "
                "the amounts the custom houses changed, at Yokohama, Nagasaki and Hakodate, with the Shanghai "
                "side, July 1859 to December 1861. One row per statement, as the source prints it.",
        "transcribed": "2026-09-28 to 2026-10-01",
        "unit": {"dollar in ichibu": "ichibu per 100 dollars; a rate in momme is turned at 15 momme to the "
                                     "ichibu, a rate in tempo at 16 tempo to the ichibu",
                 "low, high": "the range the statement gives; equal where it gives one figure",
                 "date_from, date_to": "the days the statement covers, Gregorian"},
        "coin": {"new": "Ansei koban", "old": "Tenpo koban", "": "the source does not say"},
        "kinds": KINDS, "ports": PORTS, "how": HOW, "level": LEVEL, "basis": BASIS,
        "ref": "the working transcription and record number the row was built from; the transcriptions are "
               "kept with the fetched sources and are not distributed",
        "counts": {"statements": len(rows),
                   "by_kind": dict(sorted(Counter(r["kind"] for r in rows).items())),
                   "by_how": dict(sorted(Counter(r["how"] for r in rows).items())),
                   "later_compilations": sum(1 for r in rows if r["level"]),
                   "later_compilations_read_on_a_page_image": sum(1 for r in rows if r["level"] and r["how"] != "study"),
                   "by_basis": dict(sorted(Counter(r["basis"] for r in rows if r["basis"]).items())),
                   "by_port": dict(sorted(Counter(r["port"] for r in rows).items()))},
        "statements": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                   newline="\n")
    print("wrote", OUT.name, len(rows), "statements")


if __name__ == "__main__":
    main()
