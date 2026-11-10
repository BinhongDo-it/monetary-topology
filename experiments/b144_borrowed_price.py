"""B144 arm J: how much of an official basket is a price nobody pays.

An owner-occupier pays no rent. Some statistical offices put the rent the dwelling would fetch
into the consumer price index (rental equivalence); the number is borrowed from the rental
market. Two offices publish their index both with and without it, so the share of the borrowed
price can be read off their own tables:

  United Kingdom  the weights of the consumption segments of April 2025 in the CPI and in the
                  CPIH, whose four segments of imputed rents carry a weight only in the second
  Japan           the weights of the 2020-base index, which prints the total and the total
                  without the imputed rent of owner-occupied housing, nationally and for Tokyo

  B144-J0  instrument    the UK file carries the four segments of imputed rents, at zero in the
                         CPI and above zero in the CPIH, and the Japanese table carries its line
  B144-J1  own_reading   one country, two official price levels: the share of the borrowed price
                         is above zero in one index and zero in the other, in both countries

Run from the repo root:
    python experiments/b144_borrowed_price.py
    python experiments/b144_borrowed_price.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UK = ROOT / "data" / "raw" / "b144" / "uk" / "segments_2025_04"
JP = ROOT / "data" / "raw" / "b144" / "weights" / "jp_cpi_2020_weights.pdf"
OUT = ROOT / "results" / "b144_borrowed_price.json"

UK_WORDS = "IMPUTED RENTS"
JP_LINE = "0163 持家の帰属家賃を除く総合 581 8 420 8 000"    # as the table prints it: items, national, Tokyo
JP_TOTAL = 10000


def tight(s: str) -> str:
    return re.sub(r"\s+", "", s)


def load() -> dict:
    f = sorted(p for p in UK.iterdir() if p.suffix == ".csv")[0]
    with open(f, encoding="utf-8-sig", newline="") as h:
        rows = list(csv.DictReader(h))
    import pymupdf
    jp = tight(" ".join(pg.get_text() for pg in pymupdf.open(JP)))
    return {"uk": rows, "jp": jp}


def uk_shares(rows: list) -> dict:
    imp = [r for r in rows if UK_WORDS in r["CS_DESC"].upper()]
    out = {"segments": [r["CS_DESC"].strip() for r in imp]}
    for col in ("CPI_WEIGHT", "CPIH_WEIGHT"):
        tot = sum(float(r[col] or 0) for r in rows)
        part = sum(float(r[col] or 0) for r in imp)
        out[col] = {"imputed": part, "total_in_file": tot, "share": part / tot if tot else float("nan")}
    return out


def jp_shares(text: str):
    m = re.search(r"0163持家の帰属家賃を除く総合(\d{3})(\d)(\d{3})(\d)(\d{3})", text)
    if not m:
        return None
    national, tokyo = int(m.group(2) + m.group(3)), int(m.group(4) + m.group(5))
    return {"without_national": national, "without_tokyo": tokyo,
            "share_national": (JP_TOTAL - national) / JP_TOTAL, "share_tokyo": (JP_TOTAL - tokyo) / JP_TOTAL}


def c_j0(data: dict):
    problems = []
    u = uk_shares(data["uk"])
    if len(u["segments"]) != 4:
        problems.append(f"{len(u['segments'])} segments of imputed rents in the UK file, not four")
    if u["CPI_WEIGHT"]["imputed"] != 0:
        problems.append("imputed rents carry a CPI weight")
    if not u["CPIH_WEIGHT"]["imputed"] > 0:
        problems.append("imputed rents carry no CPIH weight")
    if tight(JP_LINE) not in data["jp"]:
        problems.append("the Japanese table does not carry its line")
    detail = (f"UK segments: {', '.join(u['segments'])}; Japanese line '{JP_LINE}' "
              + ("found" if tight(JP_LINE) in data["jp"] else "missing") + "; "
              + ("; ".join(problems) if problems else "as expected"))
    return not problems, detail, {"problems": problems}


def c_j1(data: dict):
    u, j = uk_shares(data["uk"]), jp_shares(data["jp"])
    ok = (u["CPIH_WEIGHT"]["share"] > 0 and u["CPI_WEIGHT"]["share"] == 0 and j is not None
          and j["share_national"] > 0)
    detail = (f"United Kingdom, April 2025: imputed rents {u['CPIH_WEIGHT']['imputed']:.1f} of the "
              f"{u['CPIH_WEIGHT']['total_in_file']:.1f} parts of the CPIH in the file "
              f"({100 * u['CPIH_WEIGHT']['share']:.1f}%), and 0 in the CPI. Japan, 2020 base: the total without the "
              f"imputed rent of owner-occupied housing weighs "
              + (f"{j['without_national']} of {JP_TOTAL} nationally and {j['without_tokyo']} in Tokyo, so the "
                 f"borrowed price is {100 * j['share_national']:.1f}% and {100 * j['share_tokyo']:.1f}%" if j else "unread"))
    return ok, detail, {"uk": u, "japan": j}


KINDS = {"B144-J0": "instrument", "B144-J1": "own_reading"}
STATEMENTS = {"B144-J0": "The two official tables carry the lines the reading takes from them.",
              "B144-J1": "One country publishes two price levels, with and without a price nobody pays."}


def selftest() -> None:
    rows = [{"CS_DESC": d, "CPI_WEIGHT": c, "CPIH_WEIGHT": h} for d, c, h in
            (("IMPUTED RENTS - ENGLAND", "0", "100"), ("IMPUTED RENTS - WALES", "0", "5"),
             ("IMPUTED RENTS -SCOTLAND", "0", "8"), ("IMPUTED RENTS - N.IRELAND", "0", "2"),
             ("BREAD", "885", "885"), ("RENT", "115", "0"))]
    good = {"uk": rows, "jp": tight("x " + JP_LINE + " y")}
    assert c_j0(good)[0] and c_j1(good)[0]
    j = jp_shares(good["jp"])
    assert j["without_national"] == 8420 and abs(j["share_tokyo"] - 0.2) < 1e-12
    assert abs(uk_shares(rows)["CPIH_WEIGHT"]["share"] - 115 / 1000) < 1e-12
    bad = {"uk": [dict(r, CPI_WEIGHT="3") if "IMPUTED" in r["CS_DESC"] else r for r in rows], "jp": good["jp"]}
    assert not c_j0(bad)[0] and not c_j1(bad)[0]
    assert not c_j0({"uk": rows[1:], "jp": good["jp"]})[0]
    assert not c_j0({"uk": rows, "jp": "nothing"})[0] and not c_j1({"uk": rows, "jp": "nothing"})[0]
    print("selftest ok: the shares come back and every flag fails on its planted input")


def main() -> int:
    data = load()
    res = {"B144-J0": c_j0(data), "B144-J1": c_j1(data)}
    for n, (p, d, _) in res.items():
        print(f"{'PASS' if p else 'FAIL'} {n} [{KINDS[n]}]: {d}")
    rec = {"stage": "B144", "diagnostic_only": True,
           "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
           "criteria": [{"name": n, "kind": KINDS[n], "passed": bool(p), "statement": STATEMENTS[n], "detail": d}
                        for n, (p, d, _) in res.items()],
           "objects": json.loads(json.dumps({n: o for n, (_, _, o) in res.items()}, default=float)),
           "config": {"uk": "data/raw/b144/uk/segments_2025_04", "japan": "data/raw/b144/weights",
                      "fetched_by": "experiments/b144_fetch.py --only uk, --only weights", "japan_line": JP_LINE}}
    for o in rec["objects"].get("B144-J1", {}).get("uk", {}).values():
        if isinstance(o, dict):
            for k in o:
                o[k] = round(o[k], 4)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-J0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        selftest()
    else:
        sys.exit(main())
