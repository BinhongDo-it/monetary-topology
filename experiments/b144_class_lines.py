"""B144 arm C: the lines a sovereign writes on buying, holding, selling and renting a dwelling.

A comparison of what a unit of money buys across countries prices housing once per
country. On the edge "buy a dwelling" and on the edge "rent it" each sovereign writes
who may do it and on what terms, by words in a statute or an official rule. This arm
reads those words and counts what the line is drawn on. Nothing here is a price level.

Eleven pages, cached by `b144_fetch.py --only law` under data/raw/b144/law/. Every row
below carries the words that draw the line, exactly as they stand on its page; the
script finds them there or the row fails.

What a line can be drawn on
  status        who the person is to the sovereign: citizen, permanent resident,
                foreigner, holder of the local household registration
  standing      how long the person has paid in locally before the act
  depth         how many dwellings the buyer or the household already holds
  household     who counts as one unit, or whose kin may take the dwelling back
  vintage       when the holder or the tenant came in: date of acquisition, a sitting contract
  legal_person  a company or other holder that is not a natural person
  position      where the dwelling is or how large it is: a property of the thing, not of
                the person, recorded and not counted as a class line

Criteria (each has a planted input in --selftest that must make it fail):
  B144-C0  bookkeeping   every row's words are on its cached page; every cached page has a row
  B144-C1  own_reading   on the buy, hold and sell edges every jurisdiction read draws a
                         line on the person or on what the person already holds
  B144-C2  own_reading   where a provision writes numbers, the classes it names and the
                         different values it writes
  B144-C3  own_reading   on the rent edge, provisions that bind the landlord toward the
                         tenant already in: a class by date of entry
  B144-C4  instrument    the reader of rows on seeded faults

Run from the repo root:
    python experiments/b144_class_lines.py
    python experiments/b144_class_lines.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
LAW = ROOT / "data" / "raw" / "b144" / "law"
OUT = ROOT / "results" / "b144_class_lines.json"

PERSON = ("status", "standing", "depth", "household", "vintage", "legal_person")
VOCABULARY = PERSON + ("position",)
EDGES = ("buy", "hold", "sell", "rent")
LEVELS = ("official text", "official description", "relay of an official notice", "third-party copy of a statute")

ROWS = [
    {"id": "SG-1", "where": "Singapore", "edge": "buy", "what": "Additional Buyer's Stamp Duty, rates on or after 27 Apr 2023",
     "drawn_on": ["status", "depth", "legal_person"], "page": "sg_absd.html", "level": "official text",
     "classes": ["citizen, first", "citizen, second", "citizen, third and more", "permanent resident, first",
                 "permanent resident, second", "permanent resident, third and more", "foreigner", "entity"],
     "values": [0, 20, 30, 5, 30, 35, 60, 65],
     "words": ["SC buying second residential property 1 17% 20%",
               "Singapore Permanent Residents (SPR) buying first residential property 1 5% 5%",
               "Foreigners (FR) buying any residential property 1 30% 60%",
               "Entities 2 buying any residential property 1 35% 65%"]},
    {"id": "CN-1", "where": "China", "edge": "buy", "what": "deed tax, announcement 16 of 2024, in force 2024-12-01",
     "drawn_on": ["depth", "household", "position"], "page": "cn_deedtax.html", "level": "official text",
     "classes": ["only dwelling of the family, 140 m2 or less", "only dwelling, above 140 m2",
                 "second dwelling, 140 m2 or less", "second dwelling, above 140 m2"],
     "values": [1, 1.5, 1, 2],
     "words": ["对个人购买家庭唯一住房（家庭成员范围包括购房人、配偶以及未成年子女，下同），面积为140平方米及以下的，减按1%的税率征收契税",
               "对个人购买家庭第二套住房，面积为140平方米及以下的，减按1%的税率征收契税；面积为140平方米以上的，减按2%的税率征收契税"]},
    {"id": "CN-2", "where": "Shanghai", "edge": "buy", "what": "purchase limits, notice of 2025-08-25",
     "drawn_on": ["status", "standing", "depth", "household", "position"], "page": "cn_sh_xinhua.html",
     "level": "relay of an official notice",
     "words": ["上海户籍居民家庭、在上海市连续缴纳社会保险或个人所得税满1年及以上的非沪籍居民家庭，在外环外购买住房不限套数",
               "成年单身人士按照居民家庭执行住房限购政策",
               "非沪籍居民家庭和非沪籍成年单身人士，自购房之日前在上海市连续缴纳社会保险或个人所得税满3年及以上的，在外环内限购1套住房"]},
    {"id": "KR-1", "where": "Korea", "edge": "buy", "what": "Local Tax Act art. 13-2, heavier acquisition tax",
     "drawn_on": ["depth", "legal_person", "position"], "page": "kr_localtax_13_2.html",
     "level": "third-party copy of a statute",
     "words": ["1세대 3주택 이상에 해당하는 주택으로서 조정대상지역에 있는 주택을 취득하는 경우",
               "중과기준세율의 100분의 400을 합한 세율"]},
    {"id": "US-1", "where": "United States", "edge": "sell", "what": "26 U.S.C. 1445(a), withholding on a disposition",
     "drawn_on": ["status"], "page": "us_1445.html", "level": "official text",
     "classes": ["foreign person", "any other seller"], "values": [15, 0],
     "words": ["the transferee shall be required to deduct and withhold a tax equal to 15 percent of the amount "
               "realized on the disposition"]},
    {"id": "US-2", "where": "California", "edge": "hold", "what": "Proposition 13 as the tax board describes it",
     "drawn_on": ["vintage"], "page": "us_boe_pub29.pdf", "level": "official description",
     "words": ["properties are reassessed to current market value only upon a change in ownership or completion "
               "of new construction",
               "to no more than 2 percent"]},
    {"id": "KR-2", "where": "Korea", "edge": "rent", "what": "Housing Lease Protection Act art. 6-3, renewal",
     "drawn_on": ["vintage", "household"], "page": "kr_lease_6_3.html", "level": "third-party copy of a statute",
     "words": ["임차인은 제1항에 따른 계약갱신요구권을 1회에 한하여 행사할 수 있다. 이 경우 갱신되는 임대차의 존속기간은 2년으로 본다.",
               "임대인(임대인의 직계존속ㆍ직계비속을 포함한다)이 목적 주택에 실제 거주하려는 경우"]},
    {"id": "KR-3", "where": "Korea", "edge": "rent", "what": "Housing Lease Protection Act art. 7, increase",
     "drawn_on": ["vintage"], "page": "kr_lease_7.html", "level": "third-party copy of a statute",
     "words": ["증액청구는 약정한 차임이나 보증금의 20분의 1의 금액을 초과하지 못한다"]},
    {"id": "DE-1", "where": "Germany", "edge": "rent", "what": "BGB 573, ordinary termination by the landlord",
     "drawn_on": ["vintage", "household"], "page": "de_bgb_573.html", "level": "official text",
     "words": ["Vermieter kann nur kündigen, wenn er ein berechtigtes Interesse an der Beendigung des "
               "Mietverhältnisses hat. Die Kündigung zum Zwecke der Mieterhöhung ist ausgeschlossen.",
               "der Vermieter die Räume als Wohnung für sich, seine Familienangehörigen oder Angehörige seines "
               "Haushalts benötigt"]},
    {"id": "DE-2", "where": "Germany", "edge": "rent", "what": "BGB 558, increase up to the local comparative rent",
     "drawn_on": ["vintage", "position"], "page": "de_bgb_558.html", "level": "official text",
     "words": ["nicht um mehr als 20 vom Hundert erhöhen (Kappungsgrenze)",
               "Der Prozentsatz nach Satz 1 beträgt 15 vom Hundert"]},
    {"id": "JP-1", "where": "Japan", "edge": "rent", "what": "Act on Land and Building Leases art. 28",
     "drawn_on": ["vintage"], "page": "jp_shakuchi_28.xml", "level": "official text",
     "words": ["正当の事由があると認められる場合でなければ、することができない"]},
]


def squeeze(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def page_text(p: Path) -> str:
    if p.suffix == ".pdf":
        import pymupdf
        raw = " ".join(pg.get_text() for pg in pymupdf.open(p))
    else:
        raw = p.read_bytes().decode("utf-8", errors="replace")
        raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return squeeze(raw)


def load() -> dict:
    return {"rows": copy.deepcopy(ROWS),
            "pages": {p.name: page_text(p) for p in sorted(LAW.glob("*")) if p.is_file() and ".partial" not in p.name}}


def faults(data) -> list[str]:
    """Everything wrong with the rows as a list of sentences. Empty when the rows hold."""
    out, seen = [], Counter(r["id"] for r in data["rows"])
    for r in data["rows"]:
        if seen[r["id"]] > 1:
            out.append(f"{r['id']}: the id is used {seen[r['id']]} times")
        if r["edge"] not in EDGES:
            out.append(f"{r['id']}: unknown edge {r['edge']!r}")
        if r["level"] not in LEVELS:
            out.append(f"{r['id']}: unknown level {r['level']!r}")
        if not r["drawn_on"] or any(d not in VOCABULARY for d in r["drawn_on"]):
            out.append(f"{r['id']}: drawn on something outside the vocabulary")
        if ("classes" in r) != ("values" in r) or len(r.get("classes", [])) != len(r.get("values", [])):
            out.append(f"{r['id']}: classes and values do not pair")
        text = data["pages"].get(r["page"])
        if text is None:
            out.append(f"{r['id']}: page {r['page']} is not cached")
            continue
        if not r["words"]:
            out.append(f"{r['id']}: no words")
        for w in r["words"]:
            if squeeze(w) not in text:
                out.append(f"{r['id']}: words not on the page: {w[:40]}")
    used = {r["page"] for r in data["rows"]}
    for name in data["pages"]:
        if name not in used:
            out.append(f"page {name} is cached and no row rests on it")
    return out


def c0(data):
    f = faults(data)
    n = sum(len(r["words"]) for r in data["rows"])
    detail = (f"{len(data['rows'])} rows, {n} passages, {len(data['pages'])} cached pages; "
              + ("; ".join(f[:6]) if f else "every passage is on its page and every page carries a row")
              + ". Levels: " + ", ".join(f"{k} {v}" for k, v in Counter(r["level"] for r in data["rows"]).items()))
    return not f, detail, {"faults": f}


def c1(data):
    rows = [r for r in data["rows"] if r["edge"] in ("buy", "hold", "sell")]
    by_place = {}
    for r in rows:
        by_place.setdefault(r["where"], set()).update(d for d in r["drawn_on"] if d in PERSON)
    without = sorted(p for p, s in by_place.items() if not s)
    tally = Counter(d for r in rows for d in r["drawn_on"])
    passed = bool(by_place) and not without
    detail = (f"{len(rows)} provisions on the buy, hold and sell edges in {len(by_place)} jurisdictions: "
              + "; ".join(f"{p}: {', '.join(sorted(s)) or 'none'}" for p, s in by_place.items())
              + ". Provisions drawing on each: " + ", ".join(f"{k} {tally[k]}" for k in VOCABULARY if tally[k])
              + (f". No line on the person: {without}" if without else ""))
    return passed, detail, {"by_jurisdiction": {p: sorted(s) for p, s in by_place.items()},
                            "tally": {k: tally[k] for k in VOCABULARY}}


def c2(data):
    rows = [r for r in data["rows"] if "values" in r]
    out = [{"id": r["id"], "where": r["where"], "classes": len(r["classes"]),
            "distinct_values": len(set(r["values"])), "values": r["values"]} for r in rows]
    passed = any(o["distinct_values"] > 1 for o in out)
    detail = ("; ".join(f"{o['id']} {o['where']}: {o['classes']} classes named, {o['distinct_values']} different "
                        f"values ({', '.join(str(v) for v in o['values'])} percent)" for o in out)
              if out else "no provision with numbers")
    return passed, detail, {"provisions": out}


def c3(data):
    rows = [r for r in data["rows"] if r["edge"] == "rent"]
    sitting = [r for r in rows if "vintage" in r["drawn_on"]]
    passed = bool(sitting)
    detail = (f"{len(rows)} provisions on the rent edge in {len({r['where'] for r in rows})} jurisdictions; "
              f"{len(sitting)} bind the landlord toward the tenant already in ({', '.join(r['id'] for r in sitting)}); "
              f"{sum('household' in r['drawn_on'] for r in rows)} let the landlord's own household take the dwelling back")
    return passed, detail, {"rent_rows": [r["id"] for r in rows], "sitting": [r["id"] for r in sitting]}


def seeded(data):
    """Plant one fault at a time; the reader has to name each."""
    plants = {}

    def plant(name, change):
        d = copy.deepcopy(data)
        change(d)
        plants[name] = bool(faults(d))

    plant("a letter changed in a passage", lambda d: d["rows"][0]["words"].__setitem__(0, d["rows"][0]["words"][0][:-1] + "9"))
    plant("a page gone from the cache", lambda d: d["pages"].pop(d["rows"][1]["page"]))
    plant("a word outside the vocabulary", lambda d: d["rows"][2]["drawn_on"].append("income"))
    plant("an id used twice", lambda d: d["rows"].append(copy.deepcopy(d["rows"][3])))
    plant("a page with no row", lambda d: d["pages"].__setitem__("extra.html", "words"))
    plant("classes without values", lambda d: d["rows"][0].pop("values"))
    plant("an edge that is not one", lambda d: d["rows"][4].__setitem__("edge", "lend"))
    plant("a row with no passage", lambda d: d["rows"][5].__setitem__("words", []))
    return plants


def c4(data):
    plants = seeded(data)
    caught = sum(plants.values())
    detail = f"{caught} of {len(plants)} seeded faults named" + (
        "" if caught == len(plants) else "; missed: " + ", ".join(k for k, v in plants.items() if not v))
    return caught == len(plants) and bool(plants), detail, {"plants": plants}


KINDS = {"B144-C0": "bookkeeping", "B144-C1": "own_reading", "B144-C2": "own_reading", "B144-C3": "own_reading",
         "B144-C4": "instrument"}
STATEMENTS = {
    "B144-C0": "Every row has its words on a cached page and every cached page carries a row.",
    "B144-C1": "On the buy, hold and sell edges every jurisdiction read draws a line on the person or on what "
               "the person already holds.",
    "B144-C2": "A provision that writes numbers writes more than one for one dwelling.",
    "B144-C3": "On the rent edge the rules bind the landlord toward the tenant already in, which is a class by "
               "date of entry.",
    "B144-C4": "The reader of rows names every seeded fault.",
}
FUNCS = {"B144-C0": c0, "B144-C1": c1, "B144-C2": c2, "B144-C3": c3, "B144-C4": c4}


def selftest() -> None:
    data = load()
    assert not faults(data), faults(data)
    assert all(seeded(data).values()), seeded(data)
    base = {n: f(data) for n, f in FUNCS.items()}
    assert all(v[0] for v in base.values()), {k: v[1] for k, v in base.items() if not v[0]}
    bad = copy.deepcopy(data)
    bad["rows"][0]["words"][0] = "words that are not there"
    assert not c0(bad)[0], "C0 must fail when a passage is not on its page"
    bad = copy.deepcopy(data)
    for r in bad["rows"]:
        if r["where"] == "California":
            r["drawn_on"] = ["position"]
    assert not c1(bad)[0], "C1 must fail when a jurisdiction's only line is on the dwelling"
    bad = copy.deepcopy(data)
    for r in bad["rows"]:
        if "values" in r:
            r["values"] = [7] * len(r["values"])
    assert not c2(bad)[0], "C2 must fail when every provision writes one value"
    bad = copy.deepcopy(data)
    for r in bad["rows"]:
        if r["edge"] == "rent":
            r["drawn_on"] = ["position"]
    assert not c3(bad)[0], "C3 must fail when no rent rule looks at who is already in"
    import unittest.mock as mock
    with mock.patch(f"{__name__}.faults", lambda d: []):
        assert not c4(data)[0], "C4 must fail when the reader names nothing"
    assert squeeze(" a \n b ") == "a b"
    print("selftest ok: every passage is on its page, and every flag fails on its planted input")


def main() -> int:
    data = load()
    res = {n: f(data) for n, f in FUNCS.items()}
    for name, (passed, detail, _) in res.items():
        print(f"{'PASS' if passed else 'FAIL'} {name} [{KINDS[name]}]: {detail}")
    record = {
        "stage": "B144",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is open: its arms are read one at a time and it has not been closed",
        "criteria": [{"name": n, "kind": KINDS[n], "passed": bool(p), "statement": STATEMENTS[n], "detail": d}
                     for n, (p, d, _) in res.items()],
        "rows": data["rows"],
        "objects": {n: o for n, (_, _, o) in res.items()},
        "config": {"pages": "data/raw/b144/law", "fetched_by": "experiments/b144_fetch.py --only law",
                   "vocabulary": list(VOCABULARY), "edges": list(EDGES), "levels": list(LEVELS)},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-C0"][0] and res["B144-C4"][0] else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
