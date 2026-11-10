"""B144 arm G: what the right to a place in a public school is attached to.

Arm C read who may buy, hold, sell or rent a dwelling on what terms. This arm reads one right
that a dwelling can carry: a place in the public school nearby. Each row is a provision, with
verbatim passages found on its cached page, and what the provision attaches the place to:

  title      holding the title of a dwelling there
  register   an entry in a household or residents' register, or the address on an identity card
  residence  living there, a tenancy included
  status     citizenship or permanent residence
  tenure     a number of years of renting or working there, asked of those without title

  B144-G0  bookkeeping   every passage is on its cached page and every page carries a row
  B144-G1  own_reading   outside China no provision read asks for title; in the Chinese cities
                         read, title enters the rule
  B144-G2  own_reading   inside one country the rule is written district by district: the
                         districts read attach the place to different things

Passages are compared with all white space removed, because the pages are of several kinds and
a page set in columns breaks a sentence where it likes.

Run from the repo root:
    python experiments/b144_school_place.py
    python experiments/b144_school_place.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import html
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAW = ROOT / "data" / "raw" / "b144" / "law_school"
OUT = ROOT / "results" / "b144_school_place.json"

VOCABULARY = ("title", "register", "residence", "status", "tenure")
LEVELS = ("official text", "official description")
SCALES = ("country", "state or city", "district")
CHINA = ("China",)

ROWS = [
    {"id": "CN-1", "country": "China", "where": "China", "scale": "country", "level": "official text",
     "page": "cn_compulsory_education_law.html", "what": "Compulsory Education Law, article 12",
     "attached_to": ["register"],
     "words": ["地方各级人民政府应当保障适龄儿童、少年在户籍所在地学校就近入学",
               "在其父母或者其他法定监护人工作或者居住地接受义务教育的，当地人民政府应当为其提供平等接受义务教育的条件。具体办法由省、自治区、直辖市规定"]},
    {"id": "CN-2", "country": "China", "where": "Shanghai", "scale": "state or city", "level": "official text",
     "page": "sh_city_2026.pdf", "what": "city education commission, admissions for 2026",
     "attached_to": ["register", "residence"],
     "words": ["区教育行政部门结合本地区实际，制定“人户分离”适龄儿童入学实施细则，先安排户籍地与实际居住地一致的适龄儿童就近入学"]},
    {"id": "CN-3", "country": "China", "where": "Shanghai, Hongkou district", "scale": "district",
     "level": "official text", "page": "sh_hongkou_2026.pdf",
     "what": "rules for children registered in one place and living in another, 2026",
     "attached_to": ["register", "residence", "title"],
     "words": ["按照“人户一致优先”原则，先安排户籍地与实际居住地一致的适龄儿童就近入学",
               "适龄儿童与户主为直系亲属关系，且适龄儿童或父母三人中至少一人为居住地房屋产权所有人"]},
    {"id": "CN-4", "country": "China", "where": "Shanghai, Huangpu district", "scale": "district",
     "level": "official text", "page": "sh_huangpu_2026.pdf", "what": "primary school admissions, 2026",
     "attached_to": ["register", "residence"],
     "words": ["对于本区户籍地（户主为直系亲属或儿童本人）与居住地（产权人或承租人为直系亲属或儿童本人）一致的适龄儿童"]},
    {"id": "CN-5", "country": "China", "where": "Beijing, Huairou district", "scale": "district",
     "level": "official text", "page": "bj_huairou_2026.docx", "what": "primary school admissions, 2026",
     "attached_to": ["register", "title", "tenure"],
     "words": ["具有本市非怀柔区户籍，在怀柔区有房屋产权家庭的适龄儿童",
               "具有本市非怀柔区户籍的无房家庭，符合在怀柔区连续单独承租并实际居住3年以上，其父母在怀柔区合法稳定就业3年以上条件家庭的适龄儿童"]},
    {"id": "JP-1", "country": "Japan", "where": "Japan", "scale": "country", "level": "official text",
     "page": "jp_gakko_rei_1.xml", "what": "Order for Enforcement of the School Education Act, article 1",
     "attached_to": ["residence", "register"],
     "words": ["当該市町村の区域内に住所を有する学齢児童及び学齢生徒",
               "前項の規定による学齢簿の編製は、当該市町村の住民基本台帳に基づいて行なうものとする"]},
    {"id": "DE-1", "country": "Germany", "where": "Bavaria", "scale": "state or city", "level": "official text",
     "page": "de_bayeug_42.html", "what": "Bavarian education act, article 42",
     "attached_to": ["residence"],
     "words": ["erfüllen ihre Schulpflicht in der Schule, in deren Schulsprengel sie ihren gewöhnlichen "
               "Aufenthalt haben"]},
    {"id": "EN-1", "country": "United Kingdom", "where": "England", "scale": "country",
     "level": "official text", "page": "en_admissions_code_2021.pdf", "what": "School Admissions Code 2021, 1.14",
     "attached_to": ["residence"],
     "words": ["Catchment areas must be designed so that they are reasonable and clearly defined",
               "Catchment areas do not prevent parents who live outside the catchment of a particular school "
               "from expressing a preference for the school"]},
    {"id": "US-1", "country": "United States", "where": "New York", "scale": "state or city",
     "level": "official text", "page": "us_ny_edn_3202.html", "what": "Education Law section 3202",
     "attached_to": ["residence"],
     "words": ["is entitled to attend the public schools maintained in the district in which such person "
               "resides without the payment of tuition"]},
    {"id": "SG-1", "country": "Singapore", "where": "Singapore", "scale": "country",
     "level": "official description", "page": "sg_moe_distance.html",
     "what": "primary one registration, how distance affects priority",
     "attached_to": ["status", "register", "residence"],
     "words": ["priority admission will be given based on your child's citizenship and the Home-School Distance "
               "(HSD) category, which is in turn based on the address used for registration",
               "must reside at the address used for registration (which shall continue to be the registering "
               "parent’s NRIC address) for at least 30 months"]},
]


def tight(s: str) -> str:
    return re.sub(r"\s+", "", s)


def page_text(p: Path) -> str:
    raw = p.read_bytes()
    if raw[:4] == b"%PDF":
        import pymupdf
        t = " ".join(pg.get_text() for pg in pymupdf.open(p))
    elif raw[:2] == b"PK":
        t = zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml").decode("utf-8", errors="replace")
        t = html.unescape(re.sub(r"(?s)<[^>]+>", "", t))
    else:
        t = raw.decode("utf-8", errors="replace")
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
        t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    return tight(t)


def load() -> dict:
    pages = {p.name: page_text(p) for p in sorted(LAW.iterdir())
             if p.is_file() and ".partial" not in p.name and not p.name.endswith(".writing")}
    return {"rows": copy.deepcopy(ROWS), "pages": pages}


def faults(data: dict) -> list:
    """Everything wrong with the rows, as sentences. Empty when the rows hold."""
    out, seen = [], Counter(r["id"] for r in data["rows"])
    for r in data["rows"]:
        if seen[r["id"]] > 1:
            out.append(f"{r['id']}: the id is used {seen[r['id']]} times")
        if r["scale"] not in SCALES:
            out.append(f"{r['id']}: unknown scale {r['scale']!r}")
        if r["level"] not in LEVELS:
            out.append(f"{r['id']}: unknown level {r['level']!r}")
        if not r["attached_to"] or any(a not in VOCABULARY for a in r["attached_to"]):
            out.append(f"{r['id']}: attached to something outside the vocabulary")
        text = data["pages"].get(r["page"])
        if text is None:
            out.append(f"{r['id']}: page {r['page']} is not cached")
            continue
        if not r["words"]:
            out.append(f"{r['id']}: no words")
        for w in r["words"]:
            if tight(w) not in text:
                out.append(f"{r['id']}: words not on the page: {w[:40]}")
    used = {r["page"] for r in data["rows"]}
    for name in data["pages"]:
        if name not in used:
            out.append(f"page {name} is cached and no row rests on it")
    return out


def g0(data: dict):
    f = faults(data)
    n = sum(len(r["words"]) for r in data["rows"])
    detail = (f"{len(data['rows'])} rows, {n} passages, {len(data['pages'])} cached pages; "
              + ("; ".join(f[:6]) if f else "every passage is on its page and every page carries a row")
              + ". Levels: " + ", ".join(f"{k} {v}" for k, v in Counter(r["level"] for r in data["rows"]).items()))
    return not f, detail, {"faults": f}


def g1(data: dict):
    inside = [r for r in data["rows"] if r["country"] in CHINA]
    outside = [r for r in data["rows"] if r["country"] not in CHINA]
    with_title_out = [r["id"] for r in outside if "title" in r["attached_to"]]
    with_title_in = [r["id"] for r in inside if "title" in r["attached_to"]]
    passed = bool(outside) and bool(inside) and not with_title_out and bool(with_title_in)
    by = "; ".join(f"{r['where']}: {', '.join(r['attached_to'])}" for r in data["rows"])
    detail = (f"{len(outside)} provisions in {len({r['country'] for r in outside})} countries outside China, "
              f"{len(with_title_out)} of them asking for title; {len(inside)} provisions in China, "
              f"{len(with_title_in)} of them naming title ({', '.join(with_title_in) or 'none'}). {by}")
    return passed, detail, {"title_outside": with_title_out, "title_inside": with_title_in,
                            "tally": dict(Counter(a for r in data["rows"] for a in r["attached_to"]))}


def g2(data: dict):
    by_country = {}
    for r in data["rows"]:
        if r["scale"] == "district":
            by_country.setdefault(r["country"], []).append(r)
    shapes = {c: sorted({",".join(sorted(r["attached_to"])) for r in rows}) for c, rows in by_country.items()}
    many = {c: s for c, s in shapes.items() if len(s) > 1}
    passed = bool(many)
    detail = ("; ".join(f"{c}: {len(rows)} districts read, {len(shapes[c])} different rules ("
                        + " | ".join(f"{r['where']}: {', '.join(r['attached_to'])}" for r in rows) + ")"
                        for c, rows in by_country.items()) if by_country else "no district read")
    return passed, detail, {"shapes": shapes}


KINDS = {"B144-G0": "bookkeeping", "B144-G1": "own_reading", "B144-G2": "own_reading"}
STATEMENTS = {
    "B144-G0": "Every row has its words on a cached page and every cached page carries a row.",
    "B144-G1": "Outside China no provision read attaches the school place to the title of a dwelling; in the "
               "Chinese cities read, title enters the rule.",
    "B144-G2": "Inside one country the rule is written district by district, and the districts read attach the "
               "place to different things.",
}
FUNCS = {"B144-G0": g0, "B144-G1": g1, "B144-G2": g2}


def selftest() -> None:
    assert tight(" a \n b　c ") == "abc"
    data = load()
    assert not faults(data), faults(data)
    base = {n: f(data) for n, f in FUNCS.items()}
    assert all(v[0] for v in base.values()), {k: v[1] for k, v in base.items() if not v[0]}

    def changed(change):
        d = copy.deepcopy(data)
        if change == "letter":
            d["rows"][0]["words"][0] = d["rows"][0]["words"][0][:-1] + "校"
        elif change == "page":
            d["pages"].pop(d["rows"][1]["page"])
        elif change == "idle page":
            d["pages"]["extra.html"] = "words"
        elif change == "vocabulary":
            d["rows"][2]["attached_to"].append("income")
        elif change == "twice":
            d["rows"].append(copy.deepcopy(d["rows"][3]))
        elif change == "scale":
            d["rows"][4]["scale"] = "street"
        elif change == "level":
            d["rows"][5]["level"] = "hearsay"
        elif change == "no words":
            d["rows"][6]["words"] = []
        elif change == "nothing attached":
            d["rows"][7]["attached_to"] = []
        return d
    for change in ("letter", "page", "idle page", "vocabulary", "twice", "scale", "level", "no words",
                   "nothing attached"):
        assert not g0(changed(change))[0], f"G0 must fail on {change}"

    d = copy.deepcopy(data)
    next(r for r in d["rows"] if r["country"] == "Japan")["attached_to"].append("title")
    assert not g1(d)[0], "G1 must fail when a provision outside China asks for title"
    d = copy.deepcopy(data)
    for r in d["rows"]:
        r["attached_to"] = [a for a in r["attached_to"] if a != "title"] or ["register"]
    assert not g1(d)[0], "G1 must fail when no Chinese provision names title"
    d = copy.deepcopy(data)
    d["rows"] = [r for r in d["rows"] if r["country"] in CHINA]
    assert not g1(d)[0], "G1 must fail when nothing outside China was read"
    d = copy.deepcopy(data)
    for r in d["rows"]:
        if r["scale"] == "district":
            r["attached_to"] = ["register", "residence"]
    assert not g2(d)[0], "G2 must fail when every district writes the same rule"
    d = copy.deepcopy(data)
    d["rows"] = [r for r in d["rows"] if r["scale"] != "district"]
    assert not g2(d)[0], "G2 must fail when no district was read"
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
        "objects": {n: o for n, (_, _, o) in res.items()},
        "rows": data["rows"],
        "config": {"pages": "data/raw/b144/law_school", "fetched_by": "experiments/b144_fetch.py --only school",
                   "vocabulary": list(VOCABULARY), "levels": list(LEVELS), "scales": list(SCALES),
                   "compared": "with all white space removed"},
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if res["B144-G0"][0] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
